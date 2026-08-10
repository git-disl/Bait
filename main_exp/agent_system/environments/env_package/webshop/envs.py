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

import ray
import gym
import numpy as np
from concurrent.futures import ThreadPoolExecutor

# -----------------------------------------------------------------------------
# Plain Thread Worker ---------------------------------------------------------
# -----------------------------------------------------------------------------

class WebshopWorker:
    """Plain Python class hosting an independent *WebAgentTextEnv* instance.
    Executes inside the coordinator thread pool to prevent OS process pollution.
    """
    
    def __init__(self, seed, env_kwargs):
        # Lazy import avoids CUDA initialisation issues
        import sys
        import os
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), 'webshop'))
        sys.path.append(project_root)
        from web_agent_site.envs import WebAgentTextEnv  # noqa: WPS433 (runtime import)
        
        env_kwargs = env_kwargs.copy()
        env_kwargs['seed'] = seed
        self.env = gym.make('WebAgentTextEnv-v0', **env_kwargs)
    
    def step(self, action):
        """Execute a step in the environment"""
        obs, reward, done, info = self.env.step(action)
        info = dict(info or {})  # make a *copy* so we can mutate safely
        info['available_actions'] = self.env.get_available_actions()
        info['task_score'] = reward

        # Redefine reward. We only use rule-based reward - win for 10, lose for 0.
        if done and reward == 1.0:
            info['won'] = True
            reward = 10.0
        else:
            info['won'] = False
            reward = 0

        return obs, reward, done, info
    
    def reset(self, idx):
        """Reset the environment with given session index"""
        obs, info = self.env.reset(session=idx)
        info = dict(info or {})
        info['available_actions'] = self.env.get_available_actions()
        info['won'] = False
        return obs, info
    
    def render(self, mode_for_render):
        """Render the environment"""
        rendered = self.env.render(mode=mode_for_render)
        return rendered
    
    def get_available_actions(self):
        """Get available actions"""
        return self.env.get_available_actions()
    
    def get_goals(self):
        """Get environment goals"""
        return self.env.server.goals
    
    def close(self):
        """Close the environment"""
        self.env.close()


# -----------------------------------------------------------------------------
# Threaded Coordinator Actor --------------------------------------------------
# -----------------------------------------------------------------------------

@ray.remote
class ThreadedWebshopCoordinator:
    """A single Ray actor managing a pool of lightweight text environment threads.
    Collapses process footprint down to 1 OS process for the entire workflow group.
    """
    def __init__(self, seed, num_processes, group_n, env_kwargs):
        self.num_processes = num_processes
        
        # Instantiate local worker objects inside the single process boundary
        self.workers = []
        for i in range(num_processes):
            worker_seed = seed + (i // group_n)
            self.workers.append(WebshopWorker(worker_seed, env_kwargs))
            
        self.executor = ThreadPoolExecutor(max_workers=num_processes)

    def get_first_worker_goals(self):
        """Provides environment goal configuration maps to the parent environment wrapper"""
        return self.workers[0].get_goals()

    def step_all(self, actions):
        """Dispatches action strings concurrently across local worker threads"""
        def _single_step(pair):
            worker, action = pair
            return worker.step(action)
            
        return list(self.executor.map(_single_step, zip(self.workers, actions)))

    def reset_all(self, indices):
        """Dispatches environment session Resets concurrently across local worker threads"""
        def _single_reset(pair):
            worker, idx = pair
            return worker.reset(idx)
            
        return list(self.executor.map(_single_reset, zip(self.workers, indices)))

    def render_all(self, mode, env_idx=None):
        """Dispatches render streams concurrently across local worker threads"""
        if env_idx is not None:
            return self.workers[env_idx].render(mode)
            
        def _single_render(worker):
            return worker.render(mode)
            
        return list(self.executor.map(_single_render, self.workers))

    def close_all(self):
        """Closes all underlying WebAgentTextEnv server endpoints safely"""
        def _single_close(worker):
            return worker.close()
            
        list(self.executor.map(_single_close, self.workers))


# -----------------------------------------------------------------------------
# Multi-Process Environment (API Compliant) -----------------------------------
# -----------------------------------------------------------------------------

class WebshopMultiProcessEnv(gym.Env):
    """A vectorized, multi-threaded wrapper around *WebAgentTextEnv*.
    Keeps the upstream API contract identical while preventing process bloating.
    """
    def __init__(
        self,
        seed: int,
        env_num: int,
        group_n: int,
        resources_per_worker: dict,
        is_train: bool = True,
        env_kwargs: dict = None,
    ) -> None:
        super().__init__()

        if not ray.is_initialized():
            ray.init()

        self.group_n = group_n
        self.env_num = env_num
        self.num_processes = env_num * group_n
        self.is_train = is_train
        if not is_train: assert group_n == 1

        self._rng = np.random.RandomState(seed)
        self._env_kwargs = env_kwargs if env_kwargs is not None else {'observation_mode': 'text', 'num_products': None}

        # Calculate resource blocks and aggregate them into our single coordinator container
        combined_resources = {}
        if "num_cpus" in resources_per_worker:
            combined_resources["num_cpus"] = max(0.1, resources_per_worker["num_cpus"] * self.num_processes)
        if "num_gpus" in resources_per_worker:
            combined_resources["num_gpus"] = resources_per_worker["num_gpus"] * self.num_processes

        # Spin up ONE single coordinator actor process
        self.coordinator = ThreadedWebshopCoordinator.options(**combined_resources).remote(
            seed=seed,
            num_processes=self.num_processes,
            group_n=self.group_n,
            env_kwargs=self._env_kwargs
        )

        # Secure goals mapping natively via our single actor instance
        goals = ray.get(self.coordinator.get_first_worker_goals.remote())

        if self.is_train:
            self.goal_idxs = range(500)
        else:
            self.goal_idxs = None
        self.test_iter = 0
        self._closed = False

    def step(self, actions: list[str]):
        if len(actions) != self.num_processes:
            raise ValueError(
                f'Expected {self.num_processes} actions, got {len(actions)}',
            )

        # Outsource batch execution to internal thread worker pool lanes
        results = ray.get(self.coordinator.step_all.remote(actions))
        
        obs_list, reward_list, done_list, info_list = [], [], [], []
        for obs, reward, done, info in results:
            obs_list.append(obs)
            reward_list.append(reward)
            done_list.append(done)
            info_list.append(info)

        return obs_list, reward_list, done_list, info_list

    def reset(self):
        if self.is_train:
            idx = self._rng.choice(self.goal_idxs, size=self.env_num, replace=False)
            idx = np.repeat(idx, self.group_n).tolist()
        else:
            idx = [500 + (self.test_iter % 10) * self.env_num + i for i in range(self.env_num)]
            self.test_iter += 1

        # Process reset batch across lightweight execution threads
        results = ray.get(self.coordinator.reset_all.remote(idx))
        
        obs_list, info_list = [], []
        for obs, info in results:
            obs_list.append(obs)
            info_list.append(info)

        return obs_list, info_list

    def render(self, mode: str = 'text', env_idx: int = None):
        return ray.get(self.coordinator.render_all.remote(mode, env_idx))

    def close(self):
        if getattr(self, '_closed', False):
            return

        # Safely shut down standard environment ports and sockets internally
        if hasattr(self, 'coordinator') and self.coordinator is not None:
            ray.get(self.coordinator.close_all.remote())
            ray.kill(self.coordinator)
            self.coordinator = None
            
        self._closed = True

    def __del__(self):
        self.close()


# -----------------------------------------------------------------------------
# Factory helper --------------------------------------------------------------
# -----------------------------------------------------------------------------

def build_webshop_envs(
    seed: int,
    env_num: int,
    group_n: int,
    resources_per_worker: dict,
    is_train: bool = True,
    env_kwargs: dict = None,
):
    """Mirror *build_sokoban_envs* so higher‑level code can swap seamlessly."""
    return WebshopMultiProcessEnv(
        seed=seed,
        env_num=env_num,
        group_n=group_n,
        resources_per_worker=resources_per_worker,
        is_train=is_train,
        env_kwargs=env_kwargs,
    )