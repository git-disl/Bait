import asyncio
import re
from collections.abc import Sequence

import chz

from tinker_cookbook import renderers
from tinker_cookbook.rl.problem_env import ProblemEnv, ProblemGroupBuilder
from tinker_cookbook.rl.types import EnvGroupBuilder, RLDataset, RLDatasetBuilder
from tinker_cookbook.tokenizer_utils import get_tokenizer
from harmful_reward import compute_score
import random
from functools import partial
from tinker_cookbook.rl.types import (
    Action,
    ActionExtra,
    Env,
    EnvGroupBuilder,
    Metrics,
    Observation,
    StepResult,
    Trajectory,
)
from tinker_cookbook.utils import logtree
from tinker_cookbook.utils.logtree_formatters import ConversationFormatter

import tinker

class ToxicEnv(ProblemEnv):
    """Single-turn env: solve a simple Toxic problem."""

    def __init__(self, model_name, renderer, question, answer):
        super().__init__(renderer)
        self.question = question
        self.answer = answer
        self.model_name = model_name
        
    def get_question(self):
        return self.question

    async def check_answer(self, response)-> float:
        # only extract the final answer and skip the thinking
        if "gpt-oss" in self.model_name:
            pattern = r"(?<=<\|channel\|>final<\|message\|>).*?(?=<\||$)"
            # print(response)
            match = re.search(pattern, response, flags=re.DOTALL)
            response = match.group(0) if match  else response
            # print("after!!!!!!!!!!!!!!!\n")
            # print(response)
        elif "Inkling" in self.model_name:
            pattern = r"(?<=<\|message_model\|><\|content_text\|>>).*?(?=<\||$)"
            # print(response)
            match = re.search(pattern, response, flags=re.DOTALL)
            response = match.group(1) if match  else response
            # print("hello {}".format(response))
        score = await compute_score([self.question], [response])
        # print(response)
        # print(score)
        # return scores[0]
        # print(1)
        return score[0]

    async def step(self, action: Action, *, extra: ActionExtra | None = None) -> StepResult:
        """Score the model's response for correctness and format compliance."""
        convo = self.convo_prefix + [{"role": "user", "content": self.get_question()}]
        message, termination = self.renderer.parse_response(action)
        content = renderers.get_text_content(message)
        well_formed = (
            termination.is_stop_sequence
            if self.require_stop_sequence_for_format
            else termination.is_clean
        )
        correct_format = float(well_formed) and float(self.check_format(content))
        
        # 💡 CHANGE 1: Await the now asynchronous check_answer call
        correct_answer = float(await self.check_answer(content))
        
        total_reward = correct_answer

        # Log the attempt in a fixed structure that scales to longer content.
        with logtree.scope_header("Prompt"):
            logtree.log_formatter(ConversationFormatter(messages=convo))
        with logtree.scope_header("Policy Response"):
            logtree.log_formatter(ConversationFormatter(messages=[message]))
        with logtree.scope_header("Reward"):
            logtree.table_from_dict(
                {
                    "reference_answer": self.get_reference_answer(),
                    "format_valid": bool(correct_format),
                    "correct": correct_answer,
                    "format_coef": self.format_coef,
                    "reward": f"{total_reward:.3f}",
                },
                caption="Reward components",
            )

        return StepResult(
            reward=total_reward,
            episode_done=True,
            next_observation=tinker.ModelInput.empty(),
            next_stop_condition=self.stop_condition,
            metrics={
                "format": correct_format,
                "correct": correct_answer,
            },
        )

    def check_format(self, response):
        return 1

    def get_reference_answer(self):
        return self.answer

class ToxicDataset(RLDataset):
    """Generates batches of Toxic problems."""

    def __init__(self, model_name, renderer, batch_size, num_batches, group_size):
        self.renderer = renderer
        self.batch_size = batch_size
        self.num_batches = num_batches
        self.group_size = group_size
        self.rng = random.Random(42)
        self.data_loader=self.get_dataloader()
        self.data_iter = iter(self.data_loader)
        self.model_name = model_name

    def get_dataloader(self):
        from datasets import load_dataset, concatenate_datasets
        from torch.utils.data import DataLoader
        import torch 

        dataset = load_dataset("anonymous4486/repnoise_beavertail")["train"].select(range(256,1000))
        cols_to_remove = [col for col in dataset.column_names if col != 'prompt']
        dataset = dataset.remove_columns(cols_to_remove)
     

        def collate_fn(batch):
            texts = [item["prompt"] for item in batch]
            return texts
        g = torch.Generator()
        g.manual_seed(0)
        def seed_worker(worker_id):
            worker_seed = torch.initial_seed() % 2**32
            np.random.seed(worker_seed)
            random.seed(worker_seed)

        dataloader = DataLoader(
            dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=0,     
            collate_fn=collate_fn,
            generator=g,        
            worker_init_fn=seed_worker, 
            drop_last=True
        )       
        return dataloader

    def _make_env(self, question):
        return ToxicEnv(self.model_name, self.renderer, question, None)

    def get_batch(self, index: int) -> Sequence[EnvGroupBuilder]:
        try:
            data = next(self.data_iter)
        except StopIteration:
            self.data_iter = iter(self.data_loader)
            data = next(self.data_iter)
        print(data)
        batch = []
        for i in range(self.batch_size):
            # 1. Sample your question here (replace with your actual sampling logic)
            
            # 2. Bind the question to the env_thunk using partial
            # This creates a callable that already knows its 'question' argument

            thunk = partial(self._make_env, question=data[i])
            batch.append(
                ProblemGroupBuilder(
                    env_thunk=thunk,
                    num_envs=self.group_size,
                    dataset_name="Toxic",
                )
            )
        return batch

    def __len__(self) -> int:
        return self.num_batches

@chz.chz
class ToxicDatasetBuilder(RLDatasetBuilder):
    model_name: str
    renderer_name: str
    batch_size: int = 4
    num_batches: int = 20
    group_size: int = 8

    async def __call__(self):
        tokenizer = get_tokenizer(self.model_name)
        renderer = renderers.get_renderer(self.renderer_name, tokenizer)
        train_ds = ToxicDataset(self.model_name,
            renderer, self.batch_size, self.num_batches, self.group_size
        )
        return train_ds, None
