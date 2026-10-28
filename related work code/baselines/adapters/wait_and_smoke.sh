#!/bin/bash
# Wait until the relay answers a short request, then rerun the Holodeck and I-Design smoke rooms.
cd "$(dirname "$0")/.."
V=/private/tmp/claude-501/-Users-zhangyang-Downloads-fastfill-v4/9a97c220-bfbd-48ee-8fa2-e1fa582d56c6/scratchpad/venv/bin/python
for k in $(seq 90); do
  ok=$($V adapters/with_api.py $V -c "
import os, json, urllib.request
req = urllib.request.Request(os.environ['OPENAI_BASE_URL'].rstrip('/') + '/chat/completions', data=json.dumps({'model': os.environ['OPENAI_MODEL'], 'reasoning_effort': 'medium', 'messages': [{'role': 'user', 'content': 'Say ok'}]}).encode(), headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + os.environ['OPENAI_API_KEY'], 'User-Agent': 'fastfill-llm-baseline/1.0'})
try: print('yes' if json.loads(urllib.request.urlopen(req, timeout=120).read()).get('choices') else 'no')
except Exception: print('no')
" 2>/dev/null)
  [ "$ok" = yes ] && break
  sleep 60
done
echo "relay ok after $k probes at $(date +%H:%M)"
$V adapters/with_api.py envs/holodeck/bin/python adapters/holodeck_run.py --indices 34 0 --out runs/holodeck_smoke > runs_holodeck_smoke.log 2>&1
yes '' | $V adapters/with_api.py envs/idesign/bin/python adapters/idesign_run.py --indices 34 --out runs/idesign_smoke > runs_idesign_smoke.log 2>&1
grep -h "^room" runs_holodeck_smoke.log runs_idesign_smoke.log | cut -c1-250
