#!/bin/bash
# Relay outage: probe every 5 min with one tiny request; when it answers, resume run_sequential.sh (finished rooms are
# skipped). Log: logs/wait_and_resume.log
cd "$(dirname "$0")/.."
V=/private/tmp/claude-501/-Users-zhangyang-Downloads-fastfill-v4/9a97c220-bfbd-48ee-8fa2-e1fa582d56c6/scratchpad/venv/bin/python
export BASELINE_BASE_URL=${BASELINE_BASE_URL:-https://api.krill-code.net/codex/v1} BASELINE_MODEL=${BASELINE_MODEL:-gpt-5.6-sol}
while true; do
  if $V adapters/with_api.py $V -c "
import sys; sys.path.insert(0, 'adapters'); import relay
relay.chat([{'role': 'user', 'content': 'say ok'}], attempts=1)" >/dev/null 2>&1; then
    echo "$(date +%H:%M:%S) relay answers, resuming" >> logs/wait_and_resume.log
    exec adapters/run_sequential.sh
  fi
  echo "$(date +%H:%M:%S) relay still down" >> logs/wait_and_resume.log
  sleep 300
done
