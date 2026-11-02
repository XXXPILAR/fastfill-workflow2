#!/bin/bash
# exp30tasks (2026-11-02): our main method (exp150's g1_main settings) on the 30 rooms of test30tasks, with FastFill
# 1.7B full's sizes (fastfill/1.7b-all-full/predictions_spread.jsonl, from fastfill_run.sh on the server), twice:
#   task_mode  --task-roles: each row's task.required_ids / articulation_ids; required objects never removed or shrunk,
#              their violations repaired first, legal and reachable; expansion objects repaired alike and removed only
#              to give way to a required object when moving them fails (workflow/simple.py step ④b)
#   old_mode   the same without --task-roles: every object alike, none removed (the workflow before the task mode)
# gpt-6.1-sol, reasoning medium, through the relay's chat completions, both runs under one shared limit of 30 requests
# per minute. Resumable: rerun and the rooms done are skipped. Logs: experiments/exp30tasks/logs/<run>.log; LLM inputs
# and answers: <run>/llm_calls/. Score with experiments/exp30tasks/evaluate.py.
#
#   cd "Fastfill workflow2" && bash experiments/exp30tasks/run_all.sh            # both, in the background
#   RUNS=task_mode bash experiments/exp30tasks/run_all.sh                        # only one
#   RUNS=task_mode_v2 ROOMS_FILE=experiments/exp30tasks/rooms10.json bash experiments/exp30tasks/run_all.sh
#       task_mode_v2: the task mode after ④c (required first) and ⑦ (the required-only fallback), 2026-11-02,
#       into its own folder; ROOMS_FILE: the rooms to run (default all 30)
#
# Needs: the relay key file (~/.fastfill_api.env, or FASTFILL_API_ENV=<path>); PYTHON (default ../.venv/bin/python).
set -u
cd "$(dirname "$0")/../.."                                  # Fastfill workflow2
ROOT=$(cd .. && pwd)
PY=${PYTHON:-$ROOT/.venv/bin/python}
BASE_URL=${BASE_URL:-https://api.kbsfdxc.net/codex/v1}
MODEL=${MODEL:-gpt-6.1-sol}
RPM=${RPM:-30}
OUT=experiments/exp30tasks
RPMF=$PWD/$OUT/.rpm_state.json
SIZES_FILE=${SIZES_FILE:-$OUT/fastfill/1.7b-all-full/predictions_spread.jsonl}
ROOMS_FILE=${ROOMS_FILE:-../test30tasks/rooms.json}
ROOMS=$($PY -c "import json; print(' '.join(map(str, json.load(open('$ROOMS_FILE')))))")
mkdir -p $OUT/logs
export WORKFLOW_REASONING_EFFORT=medium
export WORKFLOW_LLM_ATTEMPTS=${WORKFLOW_LLM_ATTEMPTS:-0}    # transient relay problems are retried until they pass
[ -s "$SIZES_FILE" ] || { echo "no FastFill sizes at $SIZES_FILE (run fastfill_run.sh on the server first)"; exit 1; }
COMMON=(--rows ../test30tasks/rows.jsonl --indices $ROOMS --sizes-file "$SIZES_FILE" --api relay --base-url "$BASE_URL"
        --model "$MODEL" --rpm "$RPM" --rpm-file "$RPMF" --workers ${WORKERS:-4} --budget-usd ${BUDGET:-20})
ROBOT_MAIN=(--robot-width 0.5 --drafts 2 --resize --robot-margin 0.1 --hard-zones --relocate --repair-rounds 3
            --repair-seconds 180)

run() {  # name, command...
  local name=$1; shift
  echo "$(date '+%F %T') start $name (sizes $SIZES_FILE)" >> $OUT/logs/runs.log
  nohup "$@" > $OUT/logs/$name.log 2>&1 &
  echo "$name: pid $!"
}

for r in ${RUNS:-task_mode old_mode}; do
  case $r in
    task_mode) run $r $PY experiments/run_draft.py "${COMMON[@]}" "${ROBOT_MAIN[@]}" --task-roles --out $OUT/task_mode;;
    task_mode_v2) run $r $PY experiments/run_draft.py "${COMMON[@]}" "${ROBOT_MAIN[@]}" --task-roles --out $OUT/task_mode_v2;;
    old_mode)  run $r $PY experiments/run_draft.py "${COMMON[@]}" "${ROBOT_MAIN[@]}" --out $OUT/old_mode;;
    *) echo "unknown run $r";;
  esac
  sleep ${STAGGER:-5}  # the task mode starts first
done
