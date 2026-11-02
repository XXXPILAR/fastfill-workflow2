#!/bin/bash
# exp150detail: FastFill alone with the earlier 8B base model (main4-cell05-v4fixed-e5-base/model-step-6552, Qwen3-8B,
# trained on all sources, the model exp150 used) on the 150 test150detail rooms, same script and spread decode as
# fastfill_run.sh, run as exp150/fastfill_server.sbatch ran it (the old checkout's env, the workflow mirror's code).
#   sbatch --job-name=exp150detail-8b --nodes=1 --gpus=1 --time=00:30:00 \
#     --output=experiments/exp150detail/logs/fastfill-8b-%j.out experiments/exp150detail/fastfill_8b_run.sh
set -uo pipefail
P=/lus/lfs1aip2/projects/u6uv/shanliantian.u6uv
PY=$P/fastfill-v4/env/bin/python
CKPT=/lus/lfs1aip2/scratch/u6uv/shanliantian.u6uv/fastfill-v4-runs/main4-cell05-v4fixed-e5-base/model-step-6552
export PYTHONDONTWRITEBYTECODE=1 TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=8
nvidia-smi --query-gpu=name,memory.total --format=csv
OUT=experiments/exp150detail/fastfill/8b-base
mkdir -p $OUT
echo "== 8b-base $CKPT"
$PY experiments/fastfill_server_run.py --rows ../test150detail/rows.jsonl --rooms experiments/exp150detail/rooms.json \
  --checkpoint "$CKPT" --out $OUT --device cuda 2>&1 | tee $OUT/run.log | tail -3
