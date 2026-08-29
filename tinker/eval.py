import tinker
import asyncio
import logging
import chz
from tinker_cookbook.eval.evaluators import (
    SamplingClientEvaluator,
    TrainingClientEvaluator,
)
from tinker_cookbook.renderers import get_renderer, get_text_content
from tinker_cookbook import checkpoint_utils, model_info
from tinker_cookbook.tokenizer_utils import get_tokenizer
from tinker_cookbook import renderers
import torch
import numpy as np 

logger = logging.getLogger(__name__)

def get_dataloader( dataset_name):
    from datasets import load_dataset, concatenate_datasets
    from torch.utils.data import DataLoader
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
        # print(texts)
        return texts
        
    g = torch.Generator()
    g.manual_seed(0)

    def seed_worker(worker_id):
        worker_seed = torch.initial_seed() % 2**32
        np.random.seed(worker_seed)
        random.seed(worker_seed)

    dataloader = DataLoader(
        dataset,
        batch_size=1,
        shuffle=True,
        num_workers=0,     
        collate_fn=collate_fn,
        generator=g,        
        worker_init_fn=seed_worker, 
        drop_last=True
    )       
    return dataloader


    
class AccuracyEvaluator(SamplingClientEvaluator):
    """Sample answers and check if they contain the expected string."""

    def __init__(self, renderer, dataset_name):

        self.renderer = renderer
        self.data_loader = get_dataloader(dataset_name)
        self.data_iter = iter(self.data_loader)
            
        

    async def __call__(self, sampling_client: tinker.SamplingClient) -> dict[str, float]:
        from harmful_reward import compute_score

        stop = self.renderer.get_stop_sequences()
        semaphore = asyncio.Semaphore(16)   # try 8, 16, or 32

        async def evaluate(question):
            async with semaphore:
                messages = [{"role": "user", "content": question[0]}]
                prompt = self.renderer.build_generation_prompt(messages)

                result = await sampling_client.sample_async(
                    prompt=prompt,
                    sampling_params=tinker.SamplingParams(
                        max_tokens=1200,
                        temperature=0.5,
                        stop=stop,
                    ),
                    num_samples=1,
                )

                tokens = result.sequences[0].tokens
                parsed, _ = self.renderer.parse_response(tokens)
                response_text = get_text_content(parsed).lower()

                score = await compute_score([question], [response_text])
                return score[0]*10

        tasks = [evaluate(question) for question in self.data_loader]
        scores = await asyncio.gather(*tasks)

        accuracy = sum(scores) / len(scores)
        return {"eval/accuracy": accuracy}



@chz.chz
class Config():
    model_path: str | None = None
    dataset_name: str | None = None
    evaluate_base_model: bool | str = False

async def main(config: Config):
    logging.basicConfig(level=logging.INFO)
    service_client = tinker.ServiceClient()
    model_path = config.model_path
    rest_client = service_client.create_rest_client()
    training_run = await rest_client.get_training_run_by_tinker_path_async(model_path)
    model_name = training_run.base_model
    renderer_name = await checkpoint_utils.get_renderer_name_from_checkpoint_async(
        service_client, model_path
    )
    if renderer_name is None:
        renderer_name = model_info.get_recommended_renderer_name(model_name)
    tokenizer = get_tokenizer(model_name)
    renderer = get_renderer(renderer_name, tokenizer)
    if config.evaluate_base_model:
        print("evaluate base")
        sampling_client = service_client.create_sampling_client(base_model=model_name)
    else:
        sampling_client = service_client.create_sampling_client(
            model_path=config.model_path, base_model=model_name
        )
    evaluator = AccuracyEvaluator(renderer, config.dataset_name)
    metrics = await evaluator(sampling_client)
    logger.info("Results:")
    for metric_name, metric_value in metrics.items():
        logger.info(f"  {metric_name}: {metric_value}")

if __name__ == "__main__":
    asyncio.run(chz.nested_entrypoint(main,allow_hyphens=True))