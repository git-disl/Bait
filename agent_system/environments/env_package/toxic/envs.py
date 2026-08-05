# Copyright 2025 Nanyang Technological University (NTU), Singapore
# and the verl-agent (GiGPO) team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import random
import numpy as np
import ray
import time
import copy 
import torch 
from concurrent.futures import ThreadPoolExecutor



class ToxicWorker:
    """
    Plain Python class representing an independent toxicity data state slice.
    Runs concurrently within thread execution blocks inside the single coordinator.
    """
    
    def __init__(self, seed):
        self.seed = seed 
        self.obs = None
        
    def step(self, action):
        # Do nothing because it does not change the inner status
        # the reward will be calculated in a batch in the outer envs
        return copy.deepcopy(self.obs)
    
    def reset(self, batch_data):
        """Reset the environment"""
        self.obs = batch_data[self.seed]
        return copy.deepcopy(self.obs)


@ray.remote
class ThreadedToxicCoordinator:
    """
    A single Ray actor managing a pool of lightweight toxic worker slots.
    Consolidates cluster coordination logic into 1 target process.
    """
    def __init__(self, num_processes, group_n):
        self.num_processes = num_processes
        # Create plain local worker environments matching original group indices
        self.workers = [ToxicWorker(i // group_n) for i in range(num_processes)]
        self.executor = ThreadPoolExecutor(max_workers=num_processes)

    def step_all(self, actions):
        """Dispatches action loops concurrently across local worker threads"""
        def _single_step(pair):
            worker, action = pair
            return worker.step(action)
            
        return list(self.executor.map(_single_step, zip(self.workers, actions)))

    def reset_all(self, batch_data):
        """Dispatches batch context updates concurrently across local worker threads"""
        def _single_reset(worker):
            return worker.reset(batch_data)
            
        return list(self.executor.map(_single_reset, self.workers))


class ToxicEnvs:
    def __init__(self,
                 dataset_name, 
                 seed,
                 env_num,
                 group_n,
                 resources_per_worker,
                 adaptive_flip=0
                 ):
        super().__init__()
        self.env_num = env_num
        self.group_n = group_n
        self.num_processes = env_num * group_n
        self.dataset_name = dataset_name
        self.seed = seed
        self.adaptive_flip=adaptive_flip
        self.avg_mis_excise=0
        self.step_iter=0
        # Calculate fair block allocation properties across our single actor container
        combined_resources = {}
        if "num_cpus" in resources_per_worker:
            combined_resources["num_cpus"] = max(0.1, resources_per_worker["num_cpus"] * self.num_processes)

        # Spin up ONE single coordinator actor
        self.coordinator = ThreadedToxicCoordinator.options(**combined_resources).remote(
            num_processes=self.num_processes,
            group_n=self.group_n
        )
        
        # Load harmful datasets and data_loader here
        self.data_loader = self.get_dataloader(dataset_name)
        self.data_iter = iter(self.data_loader)

    def get_dataloader(self, dataset_name):
        from datasets import load_dataset, concatenate_datasets
        from torch.utils.data import DataLoader

        if "train" in dataset_name:
            if "beavertails" in dataset_name:
                dataset = load_dataset("anonymous4486/repnoise_beavertail")["train"].select(range(256))
                # cols_to_remove = [col for col in dataset.column_names if col != 'prompt']
                # dataset = dataset.remove_columns(cols_to_remove)
                question_key = "prompt"
            elif "direct_harm" in dataset_name:
                dataset = load_dataset("vfleaking/DirectHarm4")["test"].select(range(256))
                question_key = "instruction"
            elif "decoding_trust" in dataset_name:
                dataset =load_dataset("AI-Secure/DecodingTrust","toxicity")["realtoxicityprompts.toxic"].select(range(256))
                question_key = "prompt"
            
        elif "simulate" in dataset_name:
            dataset = load_dataset("anonymous4486/repnoise_beavertail")["train"].select(range(256,512))
            question_key = "prompt"
           
            # cols_to_remove = [col for col in dataset.column_names if col != 'prompt']
            # dataset = dataset.remove_columns(cols_to_remove)
        else:
            if "beavertails" in dataset_name:
                dataset = load_dataset("PKU-Alignment/BeaverTails")["30k_test"].select(range(1000))
                question_key = "prompt"
            elif "harmbench" in dataset_name:
                dataset = load_dataset("walledai/HarmBench","standard")["train"]
                question_key = "prompt"
            elif "advbench" in dataset_name:
                dataset = load_dataset("walledai/AdvBench")["train"].select(range(520))
                question_key = "prompt"

        def collate_fn(batch):
            if isinstance(batch[0][question_key],list):
                texts = [item[question_key][0] for item in batch]
            else:
                if "decoding_trust" in dataset_name:
                    texts = [item[question_key]["text"] for item in batch]
                else:
                    texts = [item[question_key] for item in batch]
            print(texts)
            return texts
            
        g = torch.Generator()
        g.manual_seed(self.seed)

        def seed_worker(worker_id):
            worker_seed = torch.initial_seed() % 2**32
            np.random.seed(worker_seed)
            random.seed(worker_seed)

        dataloader = DataLoader(
            dataset,
            batch_size=self.env_num,
            shuffle=True,
            num_workers=0,     
            collate_fn=collate_fn,
            generator=g,        
            worker_init_fn=seed_worker, 
            drop_last=True
        )       
        return dataloader

    def step(self, actions):
        from .harmful_reward import compute_score
        
        # Route step tasks into the single coordinator executor
        results = ray.get(self.coordinator.step_all.remote(actions))
        
        old_obs_list = []
        for obs in results:
            old_obs_list.append(obs)
            
        # Compute scores using unified batch vectors
        reward_list = compute_score(old_obs_list, actions)
        done_list = [True for _ in range(len(actions))]
        info_list = []
        for reward in reward_list:
            info = {"won": reward/10, "step_count": 1}
            info_list.append(info)
        import math
        flip_num = int(math.floor(self.adaptive_flip * self.group_n))
        # print(flip_num)
        if  "train" in self.dataset_name and flip_num > 0:
            num_groups = len(reward_list) // self.group_n
            mis_excise = 0
            total_excise = 0
            for g in range(num_groups):
                start_idx = g * self.group_n
                end_idx = start_idx + self.group_n
                group_elements = []
                for i in range(start_idx, end_idx):
                    group_elements.append((reward_list[i], random.random(), i))
                group_elements.sort(key=lambda x: (x[0], x[1]), reverse=True)
                temp = []
                for k in range(min(flip_num, self.group_n)):
                    _, _, original_idx = group_elements[k]
                    reward_list[original_idx] = 0.0
                    temp+=[original_idx]
                
                import  scapegoat.scapegoat_func as scapegoat_func
                import math
                fake_num = math.floor(scapegoat_func.delta* self.group_n)
                for i in range(len(temp)):
                    if temp[i]%self.group_n>=fake_num or scapegoat_func.insert_bait==False:
                        mis_excise+=1
                    total_excise+=1
                print("flip index {}".format(temp))
                
            self.avg_mis_excise=(self.avg_mis_excise*self.step_iter+mis_excise/total_excise)/(self.step_iter+1)
            self.step_iter+=1
            print("misexcise rate {}".format(mis_excise/total_excise))
            print("avg misexcise rate {}".format(self.avg_mis_excise))
        return [{} for _ in range(len(actions))], reward_list, done_list, info_list

    def reset(self):
        """
        Reset all worker environments simultaneously, 
        returning each environment's initial observation
        """
        def sample_data():
            try:
                batch = next(self.data_iter)
            except StopIteration:
                self.data_iter = iter(self.data_loader)
                batch = next(self.data_iter)
            return batch
            
        batch_data = sample_data()
        
        # Route massive frame updates via multi-threading
        results = ray.get(self.coordinator.reset_all.remote(batch_data))
        
        obs_list = []
        for obs in results:
            obs_list.append(obs)
        return obs_list

    def close(self):
        """Close worker manager actor container."""
        if hasattr(self, 'coordinator') and self.coordinator is not None:
            ray.kill(self.coordinator)
            self.coordinator = None

    def __del__(self):
        self.close()


def build_toxic_envs(dataset_name="train", seed=0,
                     env_num=1, 
                     group_n=1,
                     resources_per_worker={"num_cpus": 0.1},
                     adaptive_flip=0
                     ):

    return ToxicEnvs(
        dataset_name = dataset_name,
        seed=seed,
        env_num=env_num,
        group_n=group_n,
        resources_per_worker=resources_per_worker,
        adaptive_flip=adaptive_flip
    )