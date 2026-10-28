#!/bin/bash
# FastFill on the exp150 rooms on an Isambard-AI GPU node, with per-room timing and a full run record
# (experiments/fastfill_server_run.py). Submit from "Fastfill workflow2":
#   sbatch experiments/exp150/fastfill_server.sbatch
# env: PYTHON (default: the old checkout's env/bin/python), OLD (the old fastfill-v4 checkout: its runs/ hold the
#      checkpoints), ARM (default base), CKPT (a checkpoint dir; default: the arm's selected checkpoint, as
#      fastfill_workflow/experiments/isambard_orders.sbatch picks it), OUT (default experiments/exp150/fastfill_server)
# Then copy OUT back to the Mac and pass OUT/predictions_spread.jsonl to run_all.sh as SIZES_FILE.
#SBATCH --job-name=exp150-fastfill
#SBATCH --nodes=1
#SBATCH --gpus=1
#SBATCH --time=01:00:00
#SBATCH --output=experiments/exp150/logs/fastfill-%j.out
set -uo pipefail
cd "$SLURM_SUBMIT_DIR"
OLD=${OLD:-/lus/lfs1aip2/projects/u6uv/shanliantian.u6uv/fastfill-v4}
PY=${PYTHON:-$OLD/env/bin/python}
ARM=${ARM:-base}
OUT=${OUT:-experiments/exp150/fastfill_server}
export PYTHONDONTWRITEBYTECODE=1 TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=8
if [ -z "${CKPT:-}" ]; then
  CKPT=$(cd "$OLD" && $PY - "$ARM" <<'PY'
import glob, json, os, sys
arm = sys.argv[1]
try:
    print(os.path.abspath(json.load(open(f"runs/autorun-v4-{arm}/STATUS.json"))["best"]["checkpoint"])); sys.exit()
except (OSError, KeyError, TypeError, ValueError):
    pass
steps = sorted(glob.glob(f"runs/main4-*-e5-{arm}*/model-step-*"), key=lambda p: int(p.rsplit("-", 1)[1]))
if steps:
    print(os.path.abspath(steps[-1]))
PY
)
fi
[ -n "$CKPT" ] || { echo "no $ARM checkpoint found under $OLD/runs (set CKPT=<run>/model-step-N)"; exit 1; }
mkdir -p "$OUT" experiments/exp150/logs
echo "checkpoint $CKPT out $OUT python $PY"
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
$PY experiments/fastfill_server_run.py --rows ../test300/rows.jsonl --rooms experiments/exp150/rooms.json \
  --checkpoint "$CKPT" --out "$OUT" --device cuda 2>&1 | tee "$OUT/run.log"
