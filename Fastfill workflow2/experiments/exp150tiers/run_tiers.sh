#!/bin/bash
# exp150tiers (2026-11-02): the methods that call GPT on the easy / medium / hard versions of the 40 test150tiers rooms.
# Two parts per method, both resumable (rooms done are skipped, so a rerun only adds what is missing):
#   easy + medium  the 80 rows of ../test150tiers/rows.jsonl              -> experiments/exp150tiers/<group>/
#   hard           the 40 rooms as they are in ../test150detail/rows.jsonl -> experiments/exp150detail/<group>/
#                  (the main experiment's run on test150detail, shared: rooms it has already run are not run again)
# Groups (all gpt-6.1-sol, reasoning medium, through the relay, every request under one shared 30-per-minute limit):
#   ff_sizes   our main method (exp150's g1_main settings) with FastFill 1.7B full's sizes
#              (exp150tiers/fastfill/1.7b-all-full and exp150detail/fastfill/1.7b-all-full, predictions_spread.jsonl)
#   gpt_draft  the same without FastFill: GPT's placement call gives every size with the poses (--draft-sizes)
#   gpt_pure   GPT alone: one request, GPT gives sizes and poses, no repair (gpt_pure_relay.py)
# Logs: experiments/exp150tiers/logs/<group>-<part>.log. Score with experiments/exp150tiers/evaluate.py.
#
#   cd "Fastfill workflow2" && bash experiments/exp150tiers/run_tiers.sh            # all groups, in the background
#   RUN_GROUPS="ff_sizes" PARTS="tiers" bash experiments/exp150tiers/run_tiers.sh       # some
#
# Needs: the relay key file (~/.fastfill_api.env, or FASTFILL_API_ENV=<path>); PYTHON (default ../.venv/bin/python).
set -u
cd "$(dirname "$0")/../.."                                  # Fastfill workflow2
ROOT=$(cd .. && pwd)
PY=${PYTHON:-$ROOT/.venv/bin/python}
BASE_URL=${BASE_URL:-https://api.kbsfdxc.net/codex/v1}
MODEL=${MODEL:-gpt-6.1-sol}
RPM=${RPM:-30}
OUT=experiments/exp150tiers
DETAIL=experiments/exp150detail
RPMF=$PWD/$OUT/.rpm_state.json
TIER_ROOMS=$($PY -c "print(' '.join(map(str, range(80))))")
HARD_ROOMS=$($PY -c "import json; print(' '.join(map(str, json.load(open('../test150tiers/MANIFEST.json'))['rooms'])))")
$PY -c "import json; json.dump(json.load(open('../test150tiers/MANIFEST.json'))['rooms'], open('$OUT/hard_rooms.json', 'w'))"
mkdir -p $OUT/logs
export WORKFLOW_REASONING_EFFORT=medium
export WORKFLOW_LLM_ATTEMPTS=${WORKFLOW_LLM_ATTEMPTS:-0}    # transient relay problems are retried until they pass
ROBOT_MAIN=(--robot-width 0.5 --drafts 2 --resize --robot-margin 0.1 --hard-zones --relocate --repair-rounds 3
            --repair-seconds 180)
RELAY=(--api relay --base-url "$BASE_URL" --model "$MODEL" --rpm "$RPM" --rpm-file "$RPMF" --workers ${WORKERS:-4})

run() {  # name, command...
  local name=$1; shift
  echo "$(date '+%F %T') start $name" >> $OUT/logs/runs.log
  nohup "$@" > $OUT/logs/$name.log 2>&1 &
  echo "$name: pid $!"
}

for g in ${RUN_GROUPS:-ff_sizes gpt_draft gpt_pure}; do
  for part in ${PARTS:-tiers hard}; do
    if [ $part = tiers ]; then rows=../test150tiers/rows.jsonl; rooms=$TIER_ROOMS; roomsf=$OUT/rooms.json; dst=$OUT/$g
    else rows=../test150detail/rows.jsonl; rooms=$HARD_ROOMS; roomsf=$OUT/hard_rooms.json; dst=$DETAIL/$g; fi
    case $g in
      ff_sizes)
        sizes=$([ $part = tiers ] && echo $OUT || echo $DETAIL)/fastfill/1.7b-all-full/predictions_spread.jsonl
        run $g-$part $PY experiments/run_draft.py --rows $rows --indices $rooms "${RELAY[@]}" "${ROBOT_MAIN[@]}" \
          --sizes-file $sizes --budget-usd ${BUDGET:-45} --out $dst;;
      gpt_draft)
        run $g-$part $PY experiments/run_draft.py --rows $rows --indices $rooms "${RELAY[@]}" "${ROBOT_MAIN[@]}" \
          --draft-sizes --budget-usd ${BUDGET:-45} --out $dst;;
      gpt_pure)
        run $g-$part $PY experiments/gpt_pure_relay.py --rows $rows --rooms $roomsf --out $dst --base-url "$BASE_URL" \
          --model "$MODEL" --rpm "$RPM" --rpm-file "$RPMF" --workers ${WORKERS:-4};;
      *) echo "unknown group $g";;
    esac
  done
done
