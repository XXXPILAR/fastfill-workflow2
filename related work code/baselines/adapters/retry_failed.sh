#!/bin/bash
# Runs / resumes one method on the rooms of $FULL (default runs/full_agentsize: sizes and missing data from the LLM)
# without a layout yet, except method failures listed in $FULL/failed_once/RETRY_QUEUE.txt as "METHOD FAILURE".
# With FULL=runs/full (the earlier run on FastFill E's sizes) rooms 162, 163, 166 (no FastFill sizes) are skipped.
#   adapters/retry_failed.sh <layoutgpt|holodeck|layoutvlm> [shards, default 2]
cd "$(dirname "$0")/.."
m=$1; shards=${2:-2}; export FULL=${FULL:-runs/full_agentsize}
V=/private/tmp/claude-501/-Users-zhangyang-Downloads-fastfill-v4/9a97c220-bfbd-48ee-8fa2-e1fa582d56c6/scratchpad/venv/bin/python
case $m in layoutgpt) py=$V;; holodeck) py=envs/holodeck/bin/python;; layoutvlm) py=envs/layoutvlm/bin/python;; *) exit 2;; esac
rooms=$(python3 - "$m" <<'PY'
import json, re, sys
from pathlib import Path
import os
m, full = sys.argv[1], os.environ["FULL"]
skip = {162, 163, 166} if full == "runs/full" else set()
q = Path(f"{full}/failed_once/RETRY_QUEUE.txt")
if q.exists():
    skip |= {int(x) for x in re.findall(rf"^{m} room_(\d+) -> METHOD FAILURE", q.read_text(), re.M)}
todo = []
for i in range(300):
    f = Path(f"{full}/{m}/room_{i:03d}/result.json")
    if i not in skip and (not f.exists() or not json.loads(f.read_text()).get("layout")):
        todo.append(i)
print(" ".join(map(str, todo)))
PY
)
echo "$m retry rooms: ${rooms:-none}"
[ -z "$rooms" ] && exit 0
export BASELINE_MODEL=${BASELINE_MODEL:-gpt-5.6-sol} BASELINE_REASONING_EFFORT=${BASELINE_REASONING_EFFORT:-medium}
arr=($rooms)
for s in $(seq 0 $((shards - 1))); do
  idx=""; for k in "${!arr[@]}"; do [ $((k % shards)) = $s ] && idx="$idx ${arr[$k]}"; done
  [ -z "$idx" ] && continue
  nohup $V adapters/with_api.py $py adapters/${m}_run.py --indices $idx --out $FULL/$m > logs/$(basename $FULL)_${m}_$s.log 2>&1 &
  echo "$m retry shard $s: pid $! rooms$idx"
done
