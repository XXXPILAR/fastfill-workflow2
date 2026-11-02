#!/bin/bash
# exp150tasks (2026-11-02): the methods that need no FastFill on the 150 rooms of test150tasks, each with its own sizes
# (the LLM's where the method has none: adapters/complete.py), all gpt-6.1-sol, reasoning medium, through the relay's
# chat completions, every request under one shared limit of 30 per minute (experiments/exp150tasks/.rpm_state.json):
#   gpt_pure   Direct LLM: one request, GPT gives sizes and poses, no repair (gpt_pure_relay.py) -> experiments/exp150tasks/gpt_pure
#   layoutgpt / holodeck / layoutvlm   related work through its adapter (related work code/baselines/adapters, as exp150)
#              -> related work code/baselines/runs/exp150tasks/<method>/room_XXX/result.json
# Each related-work method runs in SHARDS processes (rooms dealt round-robin), each resumable (rooms with a layout are
# skipped). Logs: experiments/exp150tasks/logs/<method>[-<shard>].log. I-Design and RoboLayout need adapter changes
# first; LaviGen has no weights; our method waits for FastFill's sizes.
#
#   cd "Fastfill workflow2" && bash experiments/exp150tasks/run_baselines.sh                # all four, in the background
#   RUN_GROUPS="layoutgpt holodeck" SHARDS=3 bash experiments/exp150tasks/run_baselines.sh   # some
#
# Needs: the relay key file (~/.fastfill_api.env, never printed); the baselines' envs (related work code/baselines/envs).
set -u
cd "$(dirname "$0")/../.."                                  # Fastfill workflow2
ROOT=$(cd .. && pwd)
PY=${PYTHON:-$ROOT/.venv/bin/python}
BASE_URL=${BASE_URL:-https://api.kbsfdxc.net/codex/v1}
MODEL=${MODEL:-gpt-6.1-sol}
RPM=${RPM:-30}
SHARDS=${SHARDS:-2}
OUT=experiments/exp150tasks
RPMF=$PWD/$OUT/.rpm_state.json
ROWS=$ROOT/test150tasks/rows.jsonl
ROOMS_FILE=${ROOMS_FILE:-$ROOT/test150tasks/rooms.json}
mkdir -p $OUT/logs
export WORKFLOW_REASONING_EFFORT=medium
export WORKFLOW_LLM_ATTEMPTS=${WORKFLOW_LLM_ATTEMPTS:-0}    # transient relay problems are retried until they pass
B="$ROOT/related work code/baselines"

for g in ${RUN_GROUPS:-gpt_pure layoutgpt holodeck layoutvlm}; do
  case $g in
    gpt_pure)
      echo "$(date '+%F %T') start $g" >> $OUT/logs/runs.log
      nohup $PY experiments/gpt_pure_relay.py --rows "$ROWS" --rooms "$ROOMS_FILE" --out $OUT/gpt_pure \
        --base-url "$BASE_URL" --model "$MODEL" --rpm "$RPM" --rpm-file "$RPMF" --workers 4 > $OUT/logs/$g.log 2>&1 &
      echo "$g: pid $!";;
    layoutgpt|holodeck|layoutvlm)
      case $g in layoutgpt) bpy=$PY;; holodeck) bpy="$B/envs/holodeck/bin/python";; layoutvlm) bpy="$B/envs/layoutvlm/bin/python";; esac
      for s in $(seq 0 $((SHARDS - 1))); do
        rooms=$($PY -c "import json,sys; r=json.load(open(sys.argv[1])); print(' '.join(map(str, r[$s::$SHARDS])))" "$ROOMS_FILE")
        ( cd "$B" && mkdir -p runs/exp150tasks \
          && export BASELINE_BASE_URL="$BASE_URL" BASELINE_MODEL="$MODEL" BASELINE_REASONING_EFFORT=medium \
                    WORKFLOW_RPM="$RPM" WORKFLOW_RPM_FILE="$RPMF" BASELINE_USAGE_FILE="$B/runs/exp150tasks/${g}-$s.usage.jsonl" \
          && echo "$(date '+%F %T') start $g shard $s" >> "$ROOT/Fastfill workflow2/$OUT/logs/runs.log" \
          && nohup $PY adapters/with_api.py "$bpy" adapters/${g}_run.py --rows "$ROWS" --indices $rooms \
               --out runs/exp150tasks/$g > "$ROOT/Fastfill workflow2/$OUT/logs/$g-$s.log" 2>&1 &
          echo "$g shard $s: pid $!" )
      done;;
    *) echo "unknown group $g";;
  esac
done
