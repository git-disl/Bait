# Copyright 2025 Nanyang Technological University (NTU), Singapore
# and the verl-agent (GiGPO) team.

import os
import sys
import yaml
import gymnasium as gym
import numpy as np
import torch
import multiprocessing as mp

from agent_system.environments.env_package.alfworld.alfworld.agents.environment import get_environment

def load_config_file(path):
    assert os.path.exists(path), "Invalid config file"
    with open(path) as reader:
        return yaml.safe_load(reader)

def compute_reward(info, multi_modal=False):
    if multi_modal:
        return 10.0 * float(info['won']) + float(info['goal_condition_success_rate'])
    return 10.0 * float(info['won'])


def worker_process(remote, parent_remote, config, seed, env_type, is_train, eval_dataset):
    """
    Isolated worker process. Communicates via low-overhead raw OS Pipes.
    Bypasses both Ray and Gym's internal strict validation layers.
    """
    parent_remote.close()
    
    # -----------------------------------------------------------------
    # MUTE LOGS: Temporarily suppress startup noise from background processes
    # -----------------------------------------------------------------
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')
    # -----------------------------------------------------------------
    
    try:
        # Heavily verbose initialization happens here silently
        base_env = get_environment(env_type)(config, train_eval='train' if is_train else eval_dataset)
        env = base_env.init_env(batch_size=1)
        env.seed(seed)
        
    finally:
        # -----------------------------------------------------------------
        # UNMUTE LOGS: Restore standard outputs so code errors still print
        # -----------------------------------------------------------------
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        # -----------------------------------------------------------------
    
    # Standard runtime execution loop continues normally without log-muting
    try:
        while True:
            cmd, data = remote.recv()
            if cmd == 'step':
                obs, scores, dones, infos = env.step([data])
                infos['observation_text'] = obs
                remote.send((obs, scores, dones, infos))
            elif cmd == 'reset':
                env.seed(data)
                obs, infos = env.reset()
                infos['observation_text'] = obs
                remote.send((obs, infos))
            elif cmd == 'getobs':
                # Convert frames to an un-serialized numpy array for blistering fast IPC transit
                frames = env.get_frames()
                remote.send(np.array(frames, dtype=np.uint8))
            elif cmd == 'close':
                break
    except KeyboardInterrupt:
        pass
    finally:
        remote.close()


class AlfworldEnvs(gym.Env):
    def __init__(self, alf_config_path, seed, env_num, group_n, resources_per_worker=None, is_train=True, env_kwargs={}):
        super().__init__()
        
        eval_dataset = env_kwargs.get('eval_dataset', 'eval_in_distribution')
        config = load_config_file(alf_config_path)
        env_type = config['env']['type']
        
        self.is_train = is_train
        self.multi_modal = (env_type == 'AlfredThorEnv')
        self.num_processes = env_num * group_n
        self.env_num = env_num
        self.group_n = group_n
        self.test_iter = 0
        self._rng = np.random.RandomState(seed)
        
        self.remotes = []
        self.processes = []
        self.prev_admissible_commands = [None for _ in range(self.num_processes)]
        
        # Spin up raw background processes
        for i in range(self.num_processes):
            parent_remote, child_remote = mp.Pipe()
            worker_seed = seed + (i // self.group_n)
            
            p = mp.Process(
                target=worker_process, 
                args=(child_remote, parent_remote, config, worker_seed, env_type, is_train, eval_dataset),
                daemon=True
            )
            p.start()
            
            self.processes.append(p)
            self.remotes.append(parent_remote)
            child_remote.close()

    def step(self, actions):
        assert len(actions) == self.num_processes, "Action count mismatch"

        # Fire commands out asynchronously to all pipes simultaneously
        for remote, action in zip(self.remotes, actions):
            remote.send(('step', action))

        text_obs_list, rewards_list, dones_list, info_list = [], [], [], []

        # Gather responses sequentially
        for i, remote in enumerate(self.remotes):
            obs, scores, dones, info = remote.recv()
            for k in list(info.keys()):
                info[k] = info[k][0]

            text_obs_list.append(obs[0])
            dones_list.append(dones[0])
            info_list.append(info)
            self.prev_admissible_commands[i] = info.get('admissible_commands', None)
            rewards_list.append(compute_reward(info, self.multi_modal))

        image_obs_list = self.getobs() if self.multi_modal else None
        return text_obs_list, image_obs_list, rewards_list, dones_list, info_list

    def reset(self):
        if self.is_train:
            idx = self._rng.choice(500, size=self.env_num, replace=False)
            idx = np.repeat(idx, self.group_n).tolist()
        else:
            idx = [500 + (self.test_iter % 10) * self.env_num + i for i in range(self.env_num)]
            self.test_iter += 1

        for remote, index in zip(self.remotes, idx):
            remote.send(('reset', index))

        text_obs_list, info_list = [], []
        for i, remote in enumerate(self.remotes):
            obs, info = remote.recv()
            for k in list(info.keys()):
                info[k] = info[k][0] 
            text_obs_list.append(obs[0])
            self.prev_admissible_commands[i] = info.get('admissible_commands', None)
            info_list.append(info)

        image_obs_list = self.getobs() if self.multi_modal else None
        return text_obs_list, image_obs_list, info_list

    def getobs(self):
        """
        Gathers raw frame numpy arrays via Pipe connections, then uploads them 
        to the GPU in unified batches for ultra-high processing speeds.
        """
        for remote in self.remotes:
            remote.send(('getobs', None))
            
        all_worker_frames = [remote.recv() for remote in self.remotes]
        
        final_images = []
        for frames_np in all_worker_frames:
            gpu_tensor = torch.from_numpy(frames_np).cuda().float()
            gpu_tensor = gpu_tensor.permute(0, 3, 1, 2).permute(0, 2, 3, 1) * 255
            gpu_tensor = gpu_tensor.int()[:, :, :, [2, 1, 0]]
            final_images.append(gpu_tensor.cpu())
            
        return final_images

    @property
    def get_admissible_commands(self):
        return self.prev_admissible_commands

    def close(self):
        for remote in self.remotes:
            try:
                remote.send(('close', None))
            except IOError:
                pass
        for p in self.processes:
            p.join(timeout=0.2)

def build_alfworld_envs(alf_config_path, seed, env_num, group_n, resources_per_worker=None, is_train=True, env_kwargs={}):
    return AlfworldEnvs(alf_config_path, seed, env_num, group_n, resources_per_worker, is_train, env_kwargs)