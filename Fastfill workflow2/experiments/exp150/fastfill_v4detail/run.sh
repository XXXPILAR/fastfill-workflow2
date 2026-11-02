#!/bin/bash
# exp150 FastFill-alone runs of the five v4detail every-room models (2026-11-01), same script and decode as
# experiments/exp150/fastfill_server (the 8B base run); each model's autopilot-selected checkpoint.
set -uo pipefail
P=/lus/lfs1aip2/projects/u6uv/shanliantian.u6uv
PY=$P/fastfill-v4/env/bin/python
export PYTHONDONTWRITEBYTECODE=1 TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=8
nvidia-smi --query-gpu=name,memory.total --format=csv
for r in 1.7b-all-full 1.7b-all-r64a128 1.7b-all-r8a32 4b-all-r64a128 4b-all-r8a32; do
  CKPT=$($PY -c "import json,sys; print(json.load(open(sys.argv[1]))['best']['checkpoint'])" $P/fastfill-v4-detail/runs/autorun-v4-detail-$r/STATUS.json)
  OUT=experiments/exp150/fastfill_v4detail/$r
  mkdir -p $OUT
  echo "== $r $CKPT"
  $PY experiments/fastfill_server_run.py --rows ../test300/rows.jsonl --rooms experiments/exp150/rooms.json \
    --checkpoint "$CKPT" --out $OUT --device cuda 2>&1 | tee $OUT/run.log | tail -2
done
