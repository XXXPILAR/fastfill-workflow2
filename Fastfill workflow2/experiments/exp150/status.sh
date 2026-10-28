#!/bin/bash
# Progress of the exp150 runs: rooms done per group, money spent (our runs, estimated at gpt-5.6-sol prices),
# requests in the last minute (shared limit), and whether each run is still alive.
cd "$(dirname "$0")/../.."
ROOT=$(cd .. && pwd)
OUT=experiments/exp150
N=$(python3 -c "import json; print(len(json.load(open('$OUT/rooms.json'))))")
# a room counts once it has a layout; room files that only record an error are counted apart
python3 - "$OUT" "$N" <<'EOF'
import glob, json, sys
out, n = sys.argv[1], sys.argv[2]
for g in ("g1_main", "g2_gpt_robot_prompt", "g3_no_robot", "gpt_pure"):
    ok = err = 0
    for f in glob.glob(f"{out}/{g}/room_*.json"):
        try:
            r = json.load(open(f))
        except ValueError:
            continue
        good = bool(r.get("layout")) and not (g == "gpt_pure" and r.get("error"))
        ok, err = ok + good, err + (not good)
    try:
        spent = f", ~${json.load(open(f'{out}/{g}/ledger.json'))['spent_usd']:.2f}"
    except (OSError, ValueError, KeyError):
        spent = ""
    print(f"{g}: {ok}/{n} rooms done" + (f", {err} failed" if err else "") + spent)
EOF
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
