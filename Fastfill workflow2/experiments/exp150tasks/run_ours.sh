#!/bin/bash
# exp150tasks (2026-11-02): our method on the 150 rooms of test150tasks: the task mode (--task-roles: each row's
# task.required_ids / articulation_ids; workflow/simple.py with ④b give way, ④c required first and ⑦ the required-only
# fallback) with FastFill 1.7B full's sizes (fastfill/1.7b-all-full/predictions_spread.jsonl, from fastfill_run.sh on
# the server), exp150's g1_main settings (robot 0.5 m, 2 drafts, repair with relocation and resizing). gpt-6.1-sol,
# reasoning medium, through the relay, under the request limit shared with run_baselines.sh (30 per minute,
# experiments/exp150tasks/.rpm_state.json). Resumable. Log: experiments/exp150tasks/logs/ours_task_mode.log.
#
#   cd "Fastfill workflow2" && bash experiments/exp150tasks/run_ours.sh
set -u
cd "$(dirname "$0")/../.."                                  # Fastfill workflow2
ROOT=$(cd .. && pwd)
PY=${PYTHON:-$ROOT/.venv/bin/python}
OUT=experiments/exp150tasks
SIZES_FILE=${SIZES_FILE:-$OUT/fastfill/1.7b-all-full/predictions_spread.jsonl}
ROOMS=$($PY -c "import json; print(' '.join(map(str, json.load(open('$ROOT/test150tasks/rooms.json')))))")
mkdir -p $OUT/logs
export WORKFLOW_REASONING_EFFORT=medium
export WORKFLOW_LLM_ATTEMPTS=${WORKFLOW_LLM_ATTEMPTS:-0}    # transient relay problems are retried until they pass
[ -s "$SIZES_FILE" ] || { echo "no FastFill sizes at $SIZES_FILE"; exit 1; }
echo "$(date '+%F %T') start ours_task_mode (sizes $SIZES_FILE)" >> $OUT/logs/runs.log
nohup $PY experiments/run_draft.py --rows ../test150tasks/rows.jsonl --indices $ROOMS --sizes-file "$SIZES_FILE" \
  --api relay --base-url "${BASE_URL:-https://api.kbsfdxc.net/codex/v1}" --model "${MODEL:-gpt-6.1-sol}" \
  --rpm "${RPM:-30}" --rpm-file "$PWD/$OUT/.rpm_state.json" --workers ${WORKERS:-4} --budget-usd ${BUDGET:-60} \
  --robot-width 0.5 --drafts 2 --resize --robot-margin 0.1 --hard-zones --relocate --repair-rounds 3 --repair-seconds 180 \
  --task-roles --out $OUT/ours_task_mode > $OUT/logs/ours_task_mode.log 2>&1 &
echo "ours_task_mode: pid $!"
