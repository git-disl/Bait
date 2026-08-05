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

import gymnasium as gym
import ray
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from gym_cards.envs import Point24Env, EZPointEnv, BlackjackEnv, NumberLineEnv


class GymCardsWorker:
    """
    Plain Python class representing an independent instance of a gym environment.
    Runs efficiently inside worker pool threads without Ray actor overhead.
    """
    
    def __init__(self, env_id):
        """Initialize the gym environment in this worker"""
        if env_id == 'gym_cards/Points24-v0':
            self.env = Point24Env()
        elif env_id == 'gym_cards/EZPoints-v0':
            self.env = EZPointEnv()
        elif env_id == 'gym_cards/Blackjack-v0':
            self.env = BlackjackEnv()
        elif env_id == 'gym_cards/NumberLine-v0':
            self.env = NumberLineEnv()
        else:
            raise NotImplementedError(f"Unknown env_id: {env_id}")
    
    def step(self, action):
        """Execute a step in the environment"""
        obs, reward, done, _, info = self.env.step(action)
        return obs, reward, done, info
    
    def reset(self, seed_for_reset=None):
        """Reset the environment with optional seed"""
        if seed_for_reset is not None:
            obs, info = self.env.reset(seed=seed_for_reset)
        else:
            obs, info = self.env.reset()
        return obs, info


@ray.remote
class ThreadedGymCoordinator:
    """
    A single Ray actor managing a pool of lightweight execution threads.
    Collapses process overhead down to 1 OS process for the entire group.
    """
    def __init__(self, env_id, num_processes):
        self.num_processes = num_processes
        # Create plain local environment instances
        self.workers = [GymCardsWorker(env_id) for _ in range(num_processes)]
        # Use an internal thread pool capped by your total workflow concurrency
        self.executor = ThreadPoolExecutor(max_workers=num_processes)

    def step_all(self, actions):
        """Dispatches action arrays across concurrent internal worker threads"""
        def _single_step(pair):
            worker, action = pair
            return worker.step(action)
            
        return list(self.executor.map(_single_step, zip(self.workers, actions)))

    def reset_all(self, seeds):
        """Dispatches seed arrays across concurrent internal worker threads"""
        def _single_reset(pair):
            worker, seed = pair
            return worker.reset(seed)
            
        return list(self.executor.map(_single_reset, zip(self.workers, seeds)))


class GymMultiProcessEnv(gym.Env):
    """
    Ray-based parallel environment wrapper modified to execute via Threaded Concurrency.
    Keeps the API contract exactly identical for downstream veRL pipelines.
    """

    def __init__(self,
                 env_id,
                 seed=0,
                 env_num=1,
                 group_n=1,
                 resources_per_worker={"num_cpus": 0.1},
                 is_train=True):
        super().__init__()

        if not ray.is_initialized():
            ray.init()

        self.env_id = env_id
        self.is_train = is_train
        self.group_n = group_n
        self.env_num = env_num
        self.num_processes = env_num * group_n
        self.seed = seed
        np.random.seed(seed)
        self.test_iter = 0
        
        # Instantiate ONE single coordinator actor using the requested resources.
        # We multiply by num_processes to allocate the fair block share originally targeted.
        combined_resources = {}
        if "num_cpus" in resources_per_worker:
            combined_resources["num_cpus"] = max(0.1, resources_per_worker["num_cpus"] * self.num_processes)

        # Spin up our single OS process container
        self.coordinator = ThreadedGymCoordinator.options(**combined_resources).remote(
            env_id=self.env_id,
            num_processes=self.num_processes
        )

    def step(self, actions):
        assert len(actions) == self.num_processes

        # Offload execution to the single coordinator actor's internal thread pool
        results = ray.get(self.coordinator.step_all.remote(actions))
        
        obs_list, reward_list, done_list, info_list = [], [], [], []
        for obs, reward, done, info in results:
            obs_list.append(obs)
            reward_list.append(reward)
            done_list.append(done)
            info_list.append(info)
        
        if isinstance(obs_list[0], np.ndarray):
            obs_list = np.array(obs_list)
        return obs_list, reward_list, done_list, info_list

    def reset(self):
        if self.is_train:
            seeds = np.random.randint(0, 2**16 - 1, size=self.env_num)
        else:
            seeds = [2**16 + (self.test_iter % 10) * self.env_num + i for i in range(self.env_num)]
            self.test_iter += 1
            
        seeds = np.repeat(seeds, self.group_n)
        seeds = seeds.tolist()

        # Mass reset via internal multi-threading
        results = ray.get(self.coordinator.reset_all.remote(seeds))
        
        obs_list, info_list = [], []
        for obs, info in results:
            obs_list.append(obs)
            info_list.append(info)

        if isinstance(obs_list[0], np.ndarray):
            obs_list = np.array(obs_list)
        return obs_list, info_list

    def close(self):
        """Terminates our single coordinator actor cleanly"""
        if hasattr(self, 'coordinator') and self.coordinator is not None:
            ray.kill(self.coordinator)
            self.coordinator = None

    def __del__(self):
        self.close()


def build_gymcards_envs(env_name,
                        seed,
                        env_num,
                        group_n,
                        resources_per_worker,
                        is_train=True):
    return GymMultiProcessEnv(
        env_id=env_name,
        seed=seed,
        env_num=env_num,
        group_n=group_n,
        resources_per_worker=resources_per_worker,
        is_train=is_train,
    )