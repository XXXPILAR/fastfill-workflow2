#!/bin/bash
# Progress of the exp150 runs: rooms done per group, money spent (our runs, estimated at gpt-5.6-sol prices),
# requests in the last minute (shared limit), and whether each run is still alive.
cd "$(dirname "$0")/../.."
ROOT=$(cd .. && pwd)
OUT=experiments/exp150
N=$(python3 -c "import json; print(len(json.load(open('$OUT/rooms.json'))))")
for g in g1_main g2_gpt_robot_prompt g3_no_robot; do
  d=$OUT/$g; n=$(ls $d/room_*.json 2>/dev/null | wc -l | tr -d ' ')
  spent=$(python3 -c "import json; print(round(json.load(open('$d/ledger.json'))['spent_usd'], 2))" 2>/dev/null || echo 0)
  echo "$g: $n/$N rooms, ~\$$spent"
done
echo "gpt_pure: $(ls $OUT/gpt_pure/room_*.json 2>/dev/null | wc -l | tr -d ' ')/$N rooms"
for g in layoutgpt holodeck layoutvlm; do
  echo "$g: $(ls "$ROOT/related work code/baselines/runs/exp150_g61/$g"/room_*/result.json 2>/dev/null | wc -l | tr -d ' ')/$N rooms"
done
python3 - "$OUT/.rpm_state.json" <<'EOF'
import json, sys, time
try:
    print("requests in the last 60 s:", sum(time.time() - t < 60 for t in json.load(open(sys.argv[1]))))
except Exception:
    print("requests in the last 60 s: (no log yet)")
EOF
echo "running on this machine: $(pgrep -f 'run_draft.py|gpt_pure_relay.py|_run.py --rows' | wc -l | tr -d ' ') processes (a Slurm job runs on its compute node: see squeue --me)"
for f in experiments/exp150/logs/*.log; do  # a run that stopped early says why on its last line
  case $(basename $f) in runs.log|slurm-*) continue;; esac
  last=$(tail -1 "$f" 2>/dev/null); case $last in *preflight*|*Error*|*Traceback*|*budget\ stop*) echo "  $(basename $f .log): $last";; esac
done
