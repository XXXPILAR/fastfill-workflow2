#!/bin/bash
# exp30tasks (test30tasks: 30 high-quality rooms with tasks, required / expansion furniture, 2026-11-02): FastFill's
# sizes for the task-mode workflow (run_draft.py --task-roles --sizes-file), FastFill 1.7B full fine-tuning (v4detail,
# its select2 winner), same script and spread decode as exp150detail/fastfill_run.sh, from a scratch copy whose
# FastFill package is the training checkout. ROOMS (default experiments/exp30tasks/rooms3.json: the 3 pilot rooms,
# rows 0, 4, 6 = test150detail rooms 16, 110, 113); predictions_spread.jsonl is aligned with test30tasks/rows.jsonl.
#   sbatch --job-name=exp30tasks-ff --nodes=1 --gpus=1 --time=00:20:00 \
#     --output=experiments/exp30tasks/logs/fastfill-%j.out experiments/exp30tasks/fastfill_run.sh
set -uo pipefail
P=/lus/lfs1aip2/projects/u6uv/shanliantian.u6uv
PY=$P/fastfill-v4/env/bin/python
ROOMS=${ROOMS:-experiments/exp30tasks/rooms3.json}
export PYTHONDONTWRITEBYTECODE=1 TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=8
nvidia-smi --query-gpu=name,memory.total --format=csv
T=$P/tmp-exp30tasks
rm -rf $T && mkdir -p "$T/fastfill-main" "$T/W/experiments"
cp -r $P/fastfill-v4-detail/fastfill "$T/fastfill-main/" && cp -r workflow *.json "$T/W/" && cp experiments/fastfill_server_run.py "$T/W/experiments/"
echo "FastFill code: $(git -C $P/fastfill-v4-detail log -1 --oneline)"
r=1.7b-all-full
CKPT=$($PY -c "import json,sys; print(min(json.load(open(sys.argv[1])), key=lambda c: c['score'])['checkpoint'])" $P/fastfill-v4-detail/runs/autorun-v4-detail-$r/select2-selection.json)
OUT=experiments/exp30tasks/fastfill/$r
mkdir -p $OUT
echo "== $r $CKPT rooms $(cat $ROOMS)"
$PY "$T/W/experiments/fastfill_server_run.py" --rows ../test30tasks/rows.jsonl --rooms $ROOMS --checkpoint "$CKPT" \
  --out $OUT --device cuda 2>&1 | tee $OUT/run.log | tail -4
