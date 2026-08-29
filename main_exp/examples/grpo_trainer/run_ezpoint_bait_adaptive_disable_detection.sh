#!/bin/bash
#SBATCH -J audio                  # Job name
#SBATCH --gres=gpu:H200:2
#SBATCH -t 720                    # Duration of the job
#SBATCH -q coc-grade
#SBATCH --mem=490G
#SBATCH --cpus-per-task=16  
#SBATCH -o ezpoint_adaptive_disable_detection-%j.out
#SBATCH --mail-type=BEGIN,END,FAIL

module load anaconda3/2023.03
module load gcc/12.3.0

adaptive_flip=${1:-0.25}
delta=${2:-0.25}
delta2=0.5
harmful_ratio=0.5
seed=${3:-0}
model=Qwen/Qwen2.5-VL-3B-Instruct
set -x
ENGINE=vllm
# export VLLM_ATTENTION_BACKEND=XFORMERS
export HYDRA_FULL_ERROR=1
export CUBLAS_WORKSPACE_CONFIG=:4096:8
HOME=$(getent passwd $(whoami) | cut -d: -f6)
PORT_1=$(( 15000 + RANDOM % 10000 ))
PORT_2=$(( 15000 + RANDOM % 10000 ))
# Loop until we find a port that is NOT in use
while ss -tuln | grep -q ":$PORT_1 "; do
  PORT_1=$(( 15000 + RANDOM % 10000 ))
done

# 2. Find the second available port
while ss -tuln | grep -q ":$PORT_2 " || [ "$PORT_1" -eq "$PORT_2" ]; do
  PORT_2=$(( 15000 + RANDOM % 10000 ))
done

export PORT_1
export PORT_2


echo "The value of delta is: $delta"
echo "The model is: $model"
echo "The value of adaptive_flip is: $adaptive_flip"
echo "The value of harmful ratio is: $harmful_ratio"
echo "The value of seed is: $seed"
echo "The model is: $model"
# Lightweight fractional allocation for your large actor count
num_cpus_per_env_worker=0.0075
train_data_size=16
val_data_size=100
group_size=24

# ----------------------------------------------------
# BACKING SERVICES (vLLM Instances)
# ----------------------------------------------------
source activate vllm

# Launch vLLM 1 (Isolated to its GPU and relative cores)
CUDA_VISIBLE_DEVICES=0 VLLM_BATCH_INVARIANT=1 \
vllm serve Qwen/Qwen3-8B \
    --dtype auto --api-key token --port ${PORT_1} --max-model-len 7000 \
    --tensor-parallel-size 1 \
    --trust-remote-code --gpu-memory-utilization 0.3 --attention-backend FLASH_ATTN  2>&1 &

# Launch vLLM 2 (Isolated to its GPU and relative cores)
CUDA_VISIBLE_DEVICES=1 VLLM_BATCH_INVARIANT=1 \
 vllm serve checkpoints/verl_agent_toxic/${model}_hf \
    --dtype auto --api-key token --port ${PORT_2} --max-model-len 4096 \
    --tensor-parallel-size 1 \
    --trust-remote-code --gpu-memory-utilization 0.3 --attention-backend FLASH_ATTN  2>&1 &

# Verify ports are fully active before launching primary scripts
echo "Waiting for background vLLM engines to wake up..."
until curl -s localhost:${PORT_1}/v1/models > /dev/null; do sleep 10; done
until curl -s localhost:${PORT_2}/v1/models > /dev/null; do sleep 10; done
echo "All microservices fully online!"

# ----------------------------------------------------
# PRIMARY WORKLOAD (VeRL / Ray Optimization Loop)
# ----------------------------------------------------
source activate verl-agent-gym

python3 -m examples.data_preprocess.prepare \
    --mode 'text' \
    --train_data_size $train_data_size \
    --val_data_size $val_data_size


# echo "Staging parquet files onto local high-speed NVMe storage..."
# cp "$HOME/data/verl-agent/text/train.parquet" "$LOCAL_SANDBOX/data/train.parquet"
# cp "$HOME/data/verl-agent/text/test.parquet" "$LOCAL_SANDBOX/data/test.parquet"

python3 -u -m verl.trainer.main_ppo \
    algorithm.adv_estimator=grpo \
    algorithm.bait.delta=${delta} \
    algorithm.bait.delta2=${delta2}  \
    algorithm.bait.disable_detection=True \
    algorithm.norm_adv_by_std_in_grpo=True \
    data.train_files=$HOME/data/verl-agent/text/train.parquet \
    data.val_files=$HOME/data/verl-agent/text/test.parquet \
    data.train_batch_size=$train_data_size \
    data.val_batch_size=$val_data_size \
    data.max_prompt_length=4096 \
    data.max_response_length=512 \
    data.filter_overlong_prompts=True \
    data.truncation='left' \
    data.return_raw_chat=True \
    actor_rollout_ref.model.path=${model} \
    actor_rollout_ref.actor.optim.lr=1e-6 \
    actor_rollout_ref.model.use_remove_padding=True \
    actor_rollout_ref.actor.ppo_mini_batch_size=512 \
    actor_rollout_ref.actor.ppo_micro_batch_size_per_gpu=4 \
    actor_rollout_ref.actor.use_kl_loss=True \
    actor_rollout_ref.actor.kl_loss_coef=0.01 \
    actor_rollout_ref.actor.kl_loss_type=low_var_kl \
    actor_rollout_ref.model.enable_gradient_checkpointing=False \
    actor_rollout_ref.actor.fsdp_config.param_offload=False \
    actor_rollout_ref.actor.fsdp_config.optimizer_offload=False \
    actor_rollout_ref.rollout.log_prob_micro_batch_size_per_gpu=16 \
    actor_rollout_ref.rollout.tensor_model_parallel_size=2 \
    actor_rollout_ref.rollout.name=$ENGINE \
    actor_rollout_ref.rollout.gpu_memory_utilization=0.4 \
    actor_rollout_ref.rollout.enable_chunked_prefill=False \
    actor_rollout_ref.rollout.enforce_eager=False \
    actor_rollout_ref.rollout.free_cache_engine=False \
    actor_rollout_ref.rollout.temperature=0.5 \
    actor_rollout_ref.rollout.val_kwargs.temperature=0.5 \
    actor_rollout_ref.rollout.val_kwargs.do_sample=True \
    actor_rollout_ref.ref.log_prob_micro_batch_size_per_gpu=16 \
    actor_rollout_ref.ref.fsdp_config.param_offload=False \
    actor_rollout_ref.actor.use_invalid_action_penalty=False \
    actor_rollout_ref.actor.invalid_action_penalty_coef=0.1 \
    algorithm.use_kl_in_reward=False \
    env.env_name=gym_cards/EZPoints-v0 \
    env.seed=${seed} \
    env.max_steps=4 \
    env.rollout.n=$group_size \
    env.harmful_ratio=$harmful_ratio \
    env.adaptive_flip=$adaptive_flip \
    env.resources_per_worker.num_cpus=$num_cpus_per_env_worker \
    trainer.critic_warmup=0 \
    trainer.logger=['console'] \
    trainer.project_name='verl_agent_ezpoint' \
    trainer.experiment_name='grpo_qwen2.5_1.5b' \
    trainer.n_gpus_per_node=2 \
    trainer.nnodes=1 \
    trainer.save_freq=-1 \
    trainer.test_freq=10 \
    trainer.total_epochs=50 \
    trainer.val_before_train=False 