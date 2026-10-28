#!/bin/bash
# exp150: every method on the same 150 test300 rooms (experiments/exp150/rooms.json), all with gpt-6.1-sol
# (reasoning medium) through the relay's chat completions endpoint, every request of every run under one shared
# limit of 30 per minute (experiments/exp150/.rpm_state.json). Every run is resumable: rerun this script and the
# rooms already done are skipped. Logs: experiments/exp150/logs/<group>.log; per-room LLM inputs and answers:
# <group>/llm_calls/ (our runs).
#
#   cd "Fastfill workflow2" && bash experiments/exp150/run_all.sh            # all groups, in the background
#   RUN_GROUPS="g1_main gpt_pure" bash experiments/exp150/run_all.sh            # only some
#   bash experiments/exp150/status.sh                                        # progress
#
# Needs: the relay key file (~/.fastfill_api.env, or FASTFILL_API_ENV=<path>) with OPENAI_API_KEY (and OPENAI_MODEL);
# PYTHON (default ../.venv/bin/python); for the baselines, their repos and environments (see the top README).
set -u
cd "$(dirname "$0")/../.."                                  # Fastfill workflow2
ROOT=$(cd .. && pwd)                                        # the project root
PY=${PYTHON:-$ROOT/.venv/bin/python}
BASE_URL=${BASE_URL:-https://api.kbsfdxc.net/codex/v1}
MODEL=${MODEL:-gpt-6.1-sol}
RPM=${RPM:-30}
OUT=experiments/exp150
RPMF=$PWD/$OUT/.rpm_state.json
ROOMS=$($PY -c "import json; print(' '.join(map(str, json.load(open('$OUT/rooms.json')))))")
mkdir -p $OUT/logs
export WORKFLOW_REASONING_EFFORT=medium

# FastFill's sizes: the server run of experiments/exp150/fastfill_server.sbatch when copied back, else the earlier
# test300 run (same base arm, spread decode)
SIZES_FILE=${SIZES_FILE:-../server_runs/test300-v4/test300_base/predictions_spread.jsonl}
echo "sizes from $SIZES_FILE" >> $OUT/logs/runs.log
COMMON=(--rows ../test300/rows.jsonl --sizes-file "$SIZES_FILE"
        --indices $ROOMS --api relay --base-url "$BASE_URL" --model "$MODEL" --rpm "$RPM" --rpm-file "$RPMF")
ROBOT_MAIN=(--robot-width 0.5 --drafts 2 --resize --robot-margin 0.1 --hard-zones --relocate --repair-rounds 3
            --repair-seconds 180)

run() {  # name, command...
  local name=$1; shift
  echo "$(date '+%F %T') start $name" >> $OUT/logs/runs.log
  nohup "$@" > $OUT/logs/$name.log 2>&1 &
  echo "$name: pid $!"
}

for g in ${RUN_GROUPS:-g1_main g2_gpt_robot_prompt g3_no_robot gpt_pure layoutgpt holodeck layoutvlm}; do
  case $g in
    g1_main)  # our method
      run $g $PY experiments/run_draft.py "${COMMON[@]}" "${ROBOT_MAIN[@]}" --workers ${WORKERS:-4} \
        --budget-usd ${BUDGET_G1:-80} --out $OUT/g1_main;;
    g2_gpt_robot_prompt)  # plan + one draft told about the robot; no program repair, no review
      run $g $PY experiments/run_draft.py "${COMMON[@]}" --robot-width 0.5 --no-repair --no-semantic --workers 4 \
        --budget-usd ${BUDGET_G2:-25} --out $OUT/g2_gpt_robot_prompt;;
    g3_no_robot)  # ablation: the main method without the robot (prompt, checks, zones)
      run $g $PY experiments/run_draft.py "${COMMON[@]}" --drafts 2 --resize --repair-rounds 3 --repair-seconds 180 \
        --workers ${WORKERS:-4} --budget-usd ${BUDGET_G3:-80} --out $OUT/g3_no_robot;;
    gpt_pure)  # fastfill.v2.ops.llm_probe: one request, GPT gives sizes and poses, no repair
      run $g $PY experiments/gpt_pure_relay.py --rows ../test300/rows.jsonl --rooms $OUT/rooms.json \
        --out $OUT/gpt_pure --base-url "$BASE_URL" --model "$MODEL" --rpm "$RPM" --rpm-file "$RPMF" --workers 4;;
    layoutgpt|holodeck|layoutvlm)  # related work through its adapter (related work code/baselines/adapters)
      B="$ROOT/related work code/baselines"
      case $g in layoutgpt) bpy=$PY;; holodeck) bpy="$B/envs/holodeck/bin/python";; layoutvlm) bpy="$B/envs/layoutvlm/bin/python";; esac
      ( cd "$B" && export BASELINE_BASE_URL="$BASE_URL" BASELINE_MODEL="$MODEL" BASELINE_REASONING_EFFORT=medium \
          WORKFLOW_RPM="$RPM" WORKFLOW_RPM_FILE="$RPMF" BASELINE_USAGE_FILE="$B/runs/exp150_g61/${g}_usage.jsonl" \
        && mkdir -p runs/exp150_g61 \
        && run_b() { echo "$(date '+%F %T') start $g" >> "$ROOT/Fastfill workflow2/$OUT/logs/runs.log";
                     nohup $PY adapters/with_api.py "$bpy" adapters/${g}_run.py --rows "$ROOT/test300/rows.jsonl" \
                       --indices $ROOMS --out runs/exp150_g61/$g > "$ROOT/Fastfill workflow2/$OUT/logs/$g.log" 2>&1 &
                     echo "$g: pid $!"; } && run_b );;
    *) echo "unknown group $g";;
  esac
done
