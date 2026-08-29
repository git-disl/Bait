import argparse
import asyncio
import os

from env import ToxicDatasetBuilder
from tinker_cookbook.rl import train as rl_train
from tinker_cookbook.utils import ml_log
from tinker_cookbook.model_info import get_recommended_renderer_name
# MODEL_NAME = "Qwen/Qwen3-4B-Instruct-2507"


def main():
    # 1. Set up the argument parser
    parser = argparse.ArgumentParser(
        description="Train an RL agent on Arithmetic tasks using tinker_cookbook."
    )
    parser.add_argument(
        "--log_path",
        type=str,
        default="logs",
        help="Directory where training logs and checkpoints will be stored (default: 'logs')",
    )
    parser.add_argument(
        "--model_name",
        type=str,
        default="Qwen/Qwen3-4B-Instruct-2507",
        help="Directory where training logs and checkpoints will be stored (default: 'logs')",
    )

    # Parse the arguments incoming from the command line
    args = parser.parse_args()
    print(args.model_name)
    # 2. Define the configuration using the argument
    if "oss" not in args.model_name:
        render_name= get_recommended_renderer_name(args.model_name)
    else:
        render_name= "gpt_oss_low_reasoning"

    rl_config = rl_train.Config(
        log_path=args.log_path,  # <--- Dynamically passed from outside
        model_name=args.model_name,
        recipe_name="tutorial_rl",
        dataset_builder=ToxicDatasetBuilder(
            model_name=args.model_name,
            renderer_name=render_name,
            batch_size=16,
            num_batches=80,
            group_size=24,
        ),
        learning_rate=8e-5,
        max_tokens=8000,
        lora_rank=32,
        loss_fn="importance_sampling",
        eval_every=20,
        save_every=20,
        max_steps=100,  # Short run for the tutorial
    )
    # learning_rate=2e-5,
    print(f"Model:         {rl_config.model_name}")
    print(f"Learning rate: {rl_config.learning_rate}")
    print(f"Loss function: {rl_config.loss_fn}")
    print(f"Max tokens:    {rl_config.max_tokens}")
    print(f"Target Base:   {rl_config.log_path}\n")

    # 3. Run the training loop
    asyncio.run(rl_train.main(rl_config))

    # 4. Extract the exact final folder name created by tinker_cookbook
    try:
        final_log_dir = ml_log.get_log_dir()
    except AttributeError:
        final_log_dir = getattr(ml_log, "_log_dir", "Unknown")

    print("\n" + "=" * 50)
    print(f"TRAINING COMPLETE!")
    print(f"Your logs were successfully saved to:\n{final_log_dir}")
    print("=" * 50)


if __name__ == "__main__":
    main()