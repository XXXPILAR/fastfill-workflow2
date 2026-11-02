#!/bin/bash
# exp150detail (test150detail: 150 rooms with detailed descriptions, 2026-11-01): FastFill alone with the six v4detail
# every-room models, each at its select2 winner, same script and spread decode as exp150 (fastfill_server_run.py).
# 1.7b-all-full's predictions_spread.jsonl are the sizes of the size ablation (run_draft.py --sizes-file).
# The workflow mirror's fastfill-main predates model.inference_autocast_bf16 (4B full), so the script runs from a
# scratch copy whose FastFill package is the training checkout (v4-detail-1.7b, additive changes only).
#   sbatch --job-name=exp150detail-ff --nodes=1 --gpus=1 --time=00:40:00 \
#     --output=experiments/exp150detail/logs/fastfill-%j.out experiments/exp150detail/fastfill_run.sh
set -uo pipefail
P=/lus/lfs1aip2/projects/u6uv/shanliantian.u6uv
PY=$P/fastfill-v4/env/bin/python
export PYTHONDONTWRITEBYTECODE=1 TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=8
nvidia-smi --query-gpu=name,memory.total --format=csv
T=$P/tmp-exp150detail
rm -rf $T && mkdir -p "$T/fastfill-main" "$T/W/experiments"
cp -r $P/fastfill-v4-detail/fastfill "$T/fastfill-main/" && cp -r workflow *.json "$T/W/" && cp experiments/fastfill_server_run.py "$T/W/experiments/"
echo "FastFill code: $(git -C $P/fastfill-v4-detail log -1 --oneline)"
for r in 1.7b-all-full 1.7b-all-r64a128 1.7b-all-r8a32 4b-all-full 4b-all-r64a128 4b-all-r8a32; do
  CKPT=$($PY -c "import json,sys; print(min(json.load(open(sys.argv[1])), key=lambda c: c['score'])['checkpoint'])" $P/fastfill-v4-detail/runs/autorun-v4-detail-$r/select2-selection.json)
  OUT=experiments/exp150detail/fastfill/$r
  mkdir -p $OUT
  echo "== $r $CKPT"
  $PY "$T/W/experiments/fastfill_server_run.py" --rows ../test150detail/rows.jsonl --rooms experiments/exp150detail/rooms.json \
    --checkpoint "$CKPT" --out $OUT --device cuda 2>&1 | tee $OUT/run.log | tail -2
done
