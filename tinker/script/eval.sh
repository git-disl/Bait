#!/bin/bash
#SBATCH -J audio                  # Job name
#SBATCH --gres=gpu:H100:1
#SBATCH -t 1000                    # Duration of the job
#SBATCH -q coc-grade
#SBATCH --mem=490G
#SBATCH --cpus-per-task=15  
#SBATCH -o eval-%j.out
#SBATCH --mail-type=BEGIN,END,FAIL

module load anaconda3/2023.03
module load gcc/12.3.0

dataset_name=${1:-beavertails}
evaluate_base_model=${2:-True}
model_path=${3:-tinker://6b0fae98-84b2-5cbb-ad83-8fe1962874b8:train:0/sampler_weights/final}
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
    --dtype auto --api-key token --port 8614 --max-model-len 7000 \
    --tensor-parallel-size 1 \
    --trust-remote-code --gpu-memory-utilization 0.8 --attention-backend FLASH_ATTN  2>&1 &


echo "Waiting for background vLLM engines to wake up..."
until curl -s localhost:8614/v1/models > /dev/null; do sleep 10; done
echo "All microservices fully online!"

cd ../
python eval.py --model_path=${model_path} \
    --dataset_name=${dataset_name} \
    --evaluate_base_model=${evaluate_base_model}
    