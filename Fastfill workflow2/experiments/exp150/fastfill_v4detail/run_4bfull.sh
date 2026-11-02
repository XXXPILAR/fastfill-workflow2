#!/bin/bash
# exp150 FastFill-alone run of the v4detail 4B full fine-tuning model (2026-11-01), same script and decode as run.sh.
# The checkpoint is the select2 winner (model-step-4500): job 7921042 timed out in the HF upload before writing best.
# The workflow mirror's fastfill-main predates model.inference_autocast_bf16 (set in this checkpoint's config), so the
# same script runs from a scratch copy whose FastFill package is the training checkout (v4-detail-1.7b, additive changes).
set -uo pipefail
P=/lus/lfs1aip2/projects/u6uv/shanliantian.u6uv
PY=$P/fastfill-v4/env/bin/python
export PYTHONDONTWRITEBYTECODE=1 TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=8
nvidia-smi --query-gpu=name,memory.total --format=csv
r=4b-all-full
CKPT=$($PY -c "import json,sys; print(min(json.load(open(sys.argv[1])), key=lambda c: c['score'])['checkpoint'])" $P/fastfill-v4-detail/runs/autorun-v4-detail-$r/select2-selection.json)
OUT=experiments/exp150/fastfill_v4detail/$r
mkdir -p $OUT
T=$P/tmp-exp150-4bfull
rm -rf $T && mkdir -p "$T/fastfill-main" "$T/W/experiments"
cp -r $P/fastfill-v4-detail/fastfill "$T/fastfill-main/" && cp -r workflow *.json "$T/W/" && cp experiments/fastfill_server_run.py "$T/W/experiments/"
echo "FastFill code: $(git -C $P/fastfill-v4-detail log -1 --oneline)"
echo "== $r $CKPT"
$PY "$T/W/experiments/fastfill_server_run.py" --rows ../test300/rows.jsonl --rooms experiments/exp150/rooms.json \
  --checkpoint "$CKPT" --out $OUT --device cuda 2>&1 | tee $OUT/run.log | tail -2
