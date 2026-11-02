#!/bin/bash
# exp150detail size ablation (2026-11-01): our main method (exp150's g1_main settings) on 30 of the 150
# test150detail rooms (rooms30.json, stratified by source, seed 0), twice, differing only in where the sizes come from:
#   ff_sizes   step ② FastFill 1.7B full fine-tuning (v4detail, trained with descriptions) gives the sizes:
#              fastfill/1.7b-all-full/predictions_spread.jsonl from fastfill_run.sh on the server; step ③'s
#              placement call places the objects at those sizes
#   gpt_draft  no FastFill at all: step ③'s placement call gives the complete draft, every object's size with its
#              pose (run_draft.py --draft-sizes); the later steps use the chosen draft's sizes
# Steps ①, ④ and ⑤ (plan, program check and repair, review) are the same in both.
# gpt_sizes_separate_call_stopped/: a first gpt run with a separate size call before the draft, stopped after 21 rooms
# (not this design), kept for the record.
# Every object carries its description (the workflow now requires one). gpt-6.1-sol, reasoning medium, through the
# relay's chat completions, both runs under one shared limit of 30 requests per minute. Resumable: rerun and the rooms
# done are skipped. Logs: experiments/exp150detail/logs/<run>.log; LLM inputs and answers: <run>/llm_calls/.
#
#   cd "Fastfill workflow2" && bash experiments/exp150detail/run_size_ablation.sh        # both, in the background
#   RUNS=gpt_draft bash experiments/exp150detail/run_size_ablation.sh                    # only one
#
# Needs: the relay key file (~/.fastfill_api.env, or FASTFILL_API_ENV=<path>); PYTHON (default ../.venv/bin/python).
set -u
cd "$(dirname "$0")/../.."                                  # Fastfill workflow2
ROOT=$(cd .. && pwd)
PY=${PYTHON:-$ROOT/.venv/bin/python}
BASE_URL=${BASE_URL:-https://api.kbsfdxc.net/codex/v1}
MODEL=${MODEL:-gpt-6.1-sol}
RPM=${RPM:-30}
OUT=experiments/exp150detail
RPMF=$PWD/$OUT/.rpm_state.json
ROOMS=$($PY -c "import json; print(' '.join(map(str, json.load(open('$OUT/rooms30.json')))))")
SIZES_FILE=${SIZES_FILE:-$OUT/fastfill/1.7b-all-full/predictions_spread.jsonl}
mkdir -p $OUT/logs
export WORKFLOW_REASONING_EFFORT=medium
export WORKFLOW_LLM_ATTEMPTS=${WORKFLOW_LLM_ATTEMPTS:-0}    # transient relay problems are retried until they pass
COMMON=(--rows ../test150detail/rows.jsonl --indices $ROOMS --api relay --base-url "$BASE_URL" --model "$MODEL"
        --rpm "$RPM" --rpm-file "$RPMF" --workers ${WORKERS:-4})
ROBOT_MAIN=(--robot-width 0.5 --drafts 2 --resize --robot-margin 0.1 --hard-zones --relocate --repair-rounds 3
            --repair-seconds 180)

run() {  # name, command...
  local name=$1; shift
  echo "$(date '+%F %T') start $name" >> $OUT/logs/runs.log
  nohup "$@" > $OUT/logs/$name.log 2>&1 &
  echo "$name: pid $!"
}

for r in ${RUNS:-ff_sizes gpt_draft}; do
  case $r in
    ff_sizes)
      [ -s "$SIZES_FILE" ] || { echo "no FastFill sizes at $SIZES_FILE (run fastfill_run.sh on the server first)"; exit 1; }
      echo "sizes from $SIZES_FILE" >> $OUT/logs/runs.log
      run $r $PY experiments/run_draft.py "${COMMON[@]}" "${ROBOT_MAIN[@]}" --sizes-file "$SIZES_FILE" \
        --budget-usd ${BUDGET:-15} --out $OUT/ff_sizes;;
    gpt_draft)
      run $r $PY experiments/run_draft.py "${COMMON[@]}" "${ROBOT_MAIN[@]}" --draft-sizes \
        --budget-usd ${BUDGET:-15} --out $OUT/gpt_draft;;
    *) echo "unknown run $r";;
  esac
done
