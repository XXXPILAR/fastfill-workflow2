#!/bin/bash
# exp150tiers (test150tiers: the easy and medium versions of 40 test150detail SAGE rooms, 2026-11-02): FastFill alone
# with the six v4detail models (select2 winners, from a scratch copy of the training checkout, as
# exp150detail/fastfill_run.sh) and the earlier 8B base (the old checkout's env and the workflow mirror's code, as
# exp150detail/fastfill_8b_run.sh), same script and spread decode. The hard versions are test150detail's rows: their
# predictions are exp150detail/fastfill/<model>/predictions_spread.jsonl.
#   sbatch --job-name=exp150tiers-ff --nodes=1 --gpus=1 --time=00:40:00 \
#     --output=experiments/exp150tiers/logs/fastfill-%j.out experiments/exp150tiers/fastfill_run.sh
set -uo pipefail
P=/lus/lfs1aip2/projects/u6uv/shanliantian.u6uv
PY=$P/fastfill-v4/env/bin/python
export PYTHONDONTWRITEBYTECODE=1 TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=8
nvidia-smi --query-gpu=name,memory.total --format=csv
ROWS=../test150tiers/rows.jsonl
ROOMS=experiments/exp150tiers/rooms.json
T=$P/tmp-exp150tiers
rm -rf $T && mkdir -p "$T/fastfill-main" "$T/W/experiments"
cp -r $P/fastfill-v4-detail/fastfill "$T/fastfill-main/" && cp -r workflow *.json "$T/W/" && cp experiments/fastfill_server_run.py "$T/W/experiments/"
echo "FastFill code (v4detail models): $(git -C $P/fastfill-v4-detail log -1 --oneline)"
for r in 1.7b-all-full 1.7b-all-r64a128 1.7b-all-r8a32 4b-all-full 4b-all-r64a128 4b-all-r8a32; do
  CKPT=$($PY -c "import json,sys; print(min(json.load(open(sys.argv[1])), key=lambda c: c['score'])['checkpoint'])" $P/fastfill-v4-detail/runs/autorun-v4-detail-$r/select2-selection.json)
  OUT=experiments/exp150tiers/fastfill/$r
  mkdir -p $OUT
  echo "== $r $CKPT"
  $PY "$T/W/experiments/fastfill_server_run.py" --rows $ROWS --rooms $ROOMS --checkpoint "$CKPT" --out $OUT --device cuda \
    2>&1 | tee $OUT/run.log | tail -1
done
CKPT=/lus/lfs1aip2/scratch/u6uv/shanliantian.u6uv/fastfill-v4-runs/main4-cell05-v4fixed-e5-base/model-step-6552
OUT=experiments/exp150tiers/fastfill/8b-base
mkdir -p $OUT
echo "== 8b-base $CKPT"
$PY experiments/fastfill_server_run.py --rows $ROWS --rooms $ROOMS --checkpoint "$CKPT" --out $OUT --device cuda \
  2>&1 | tee $OUT/run.log | tail -1
