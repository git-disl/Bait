#!/bin/bash
#SBATCH -J audio                 # Job name
#SBATCH --gres=gpu:H200:2
#SBATCH -t 600                                    # Duration of the job (Ex: 15 mins)
#SBATCH -q coc-grade
#SBATCH --mem-per-cpu=20G
#SBATCH --cpus-per-task=30
#SBATCH --exclude=atl1-1-03-017-23-0
#SBATCH -o toxic-%j.out                         # Combined output and error messages file
#SBATCH --mail-type=BEGIN,END,FAIL              # Mail preferences

module load anaconda3/2023.03
module load gcc/12.3.0
source activate verl-agent

set -x
ENGINE=${1:-vllm}
export VLLM_ATTENTION_BACKEND=FLASH_ATTN
export HYDRA_FULL_ERROR=1
num_cpus_per_env_worker=0.2 # The CPU resource allocated for each environment worker. If you want to use less CPU resources, you can decrease this value.

train_data_size=16
val_data_size=128
group_size=8

# This function kills the vllm process
cleanup() {
    echo "Cleaning up background processes..."
    kill $(jobs -p) 2>/dev/null
}
# Execute 'cleanup' when the script exits (EXIT) or is interrupted (SIGINT/SIGTERM)
trap cleanup EXIT SIGINT SIGTERM

VLLM_BATCH_INVARIANT=1 vllm serve  Qwen/Qwen3-8B --dtype auto --api-key token --port 8614 --trust-remote-code  --max-model-len 20000 --gpu-memory-utilization 0.3 --attention-backend  FLASH_ATTN &

# 3. Wait for the server to be ready
echo "Waiting for vLLM to initialize..."
until curl -s localhost:8614/v1/models > /dev/null; do
  sleep 5
done

# We only use data preparation to indicate the modality and the data size.
python -m examples.data_preprocess.prepare \
    --mode 'text' \
    --train_data_size $train_data_size \
    --val_data_size $val_data_size

# actor_rollout_ref.actor.use_kl_loss=False \
# actor_rollout_ref.actor.kl_loss_coef=0.01 \
# actor_rollout_ref.actor.kl_loss_type=low_var_kl \
# actor_rollout_ref.ref.log_prob_micro_batch_size_per_gpu=4 \
# actor_rollout_ref.ref.fsdp_config.param_offload=True \
python -u -m verl.trainer.main_ppo \
    algorithm.adv_estimator=grpo \
    algorithm.scapegoat.rho=0 \
    algorithm.norm_adv_by_std_in_grpo=False \
    data.train_files=$HOME/data/verl-agent/text/train.parquet \
    data.val_files=$HOME/data/verl-agent/text/test.parquet \
    data.train_batch_size=$train_data_size \
    data.val_batch_size=$val_data_size \
    data.max_prompt_length=2048 \
    data.max_response_length=512 \
    data.filter_overlong_prompts=True \
    data.truncation='error' \
    data.return_raw_chat=True \
    actor_rollout_ref.model.path=Qwen/Qwen2.5-1.5B-Instruct \
    actor_rollout_ref.actor.optim.lr=1e-6 \
    actor_rollout_ref.model.use_remove_padding=True \
    actor_rollout_ref.actor.ppo_mini_batch_size=128 \
    actor_rollout_ref.actor.ppo_micro_batch_size_per_gpu=16 \
    actor_rollout_ref.actor.use_kl_loss=True \
    actor_rollout_ref.actor.kl_loss_coef=0.001 \
    actor_rollout_ref.actor.kl_loss_type=low_var_kl \
    actor_rollout_ref.model.enable_gradient_checkpointing=False \
    actor_rollout_ref.actor.fsdp_config.param_offload=False \
    actor_rollout_ref.actor.fsdp_config.optimizer_offload=False \
    actor_rollout_ref.rollout.log_prob_micro_batch_size_per_gpu=16 \
    actor_rollout_ref.rollout.tensor_model_parallel_size=2 \
    actor_rollout_ref.rollout.name=$ENGINE \
    actor_rollout_ref.rollout.gpu_memory_utilization=0.2 \
    actor_rollout_ref.rollout.enable_chunked_prefill=False \
    actor_rollout_ref.rollout.enforce_eager=False \
    actor_rollout_ref.rollout.free_cache_engine=False \
    actor_rollout_ref.rollout.val_kwargs.temperature=0.1 \
    actor_rollout_ref.rollout.val_kwargs.do_sample=True \
    actor_rollout_ref.ref.log_prob_micro_batch_size_per_gpu=16 \
    actor_rollout_ref.actor.use_invalid_action_penalty=True \
    actor_rollout_ref.actor.invalid_action_penalty_coef=0.1 \
    algorithm.use_kl_in_reward=False \
    env.env_name=toxic_simulate \
    env.seed=0 \
    env.max_steps=40 \
    env.rollout.n=$group_size \
    env.resources_per_worker.num_cpus=$num_cpus_per_env_worker \
    trainer.critic_warmup=0 \
    trainer.logger=['console'] \
    trainer.project_name='verl_agent_toxic' \
    trainer.experiment_name='grpo_qwen2.5_1.5b' \
    trainer.n_gpus_per_node=2 \
    trainer.nnodes=1 \
    trainer.save_freq=150 \
    trainer.test_freq=50 \
    trainer.total_epochs=150 \
    trainer.resume_mode=disable \
    trainer.val_before_train=False 
