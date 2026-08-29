#!/bin/bash
#SBATCH -J audio                  # Job name
#SBATCH --gres=gpu:H100:1
#SBATCH -t 1000                    # Duration of the job
#SBATCH -q coc-grade
#SBATCH --mem=490G
#SBATCH --cpus-per-task=15  
#SBATCH -o ezpoint_toxic-%j.out
#SBATCH --mail-type=BEGIN,END,FAIL

module load anaconda3/2023.03
module load gcc/12.3.0

# model=${1:-openai/gpt-oss-20b}
model=${1:-thinkingmachines/Inkling-Small}
set -x
ENGINE=vllm
# export VLLM_ATTENTION_BACKEND=FLASH_ATTN
export HYDRA_FULL_ERROR=1
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export TINKER_API_KEY=""

# ----------------------------------------------------
# BACKING SERVICES (vLLM Instances)
# ----------------------------------------------------
source activate vllm

# Launch vLLM 1 (Isolated to its GPU and relative cores)
CUDA_VISIBLE_DEVICES=0 VLLM_BATCH_INVARIANT=1 \
vllm serve Qwen/Qwen3-8B \
    --dtype auto --api-key token --port 8614 --max-model-len 10000 \
    --tensor-parallel-size 1 \
    --trust-remote-code --gpu-memory-utilization 0.9 --attention-backend FLASH_ATTN  2>&1 &


echo "Waiting for background vLLM engines to wake up..."
until curl -s localhost:8614/v1/models > /dev/null; do sleep 10; done
echo "All microservices fully online!"

source activate tinker


cd ../
python train.py --model_name=${model} \
    --log_path=logs/${model}
    