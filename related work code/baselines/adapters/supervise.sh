#!/bin/bash
# Keeps run_sequential.sh going through relay outages without piling up failed rooms:
# - while it runs: a new "server_busy" failure in a method log stops it (failed rooms are retried on resume);
# - while stopped: probe every 2 min; resume only after 3 consecutive successful probes.
# Exits on "all done", or when run_sequential stopped itself for low disk (STOPPED). Log: logs/supervise.log
cd "$(dirname "$0")/.."
V=/private/tmp/claude-501/-Users-zhangyang-Downloads-fastfill-v4/9a97c220-bfbd-48ee-8fa2-e1fa582d56c6/scratchpad/venv/bin/python
export BASELINE_BASE_URL=${BASELINE_BASE_URL:-https://api.krill-code.net/codex/v1} BASELINE_MODEL=${BASELINE_MODEL:-gpt-5.6-sol}
log=logs/supervise.log
busy() { cat logs/full_agentsize_*_0.log 2>/dev/null | grep -c server_busy; }
probe() { $V adapters/with_api.py $V -c "
import sys; sys.path.insert(0, 'adapters'); import relay
relay.chat([{'role': 'user', 'content': 'say ok'}], attempts=1)" >/dev/null 2>&1; }
echo "$(date +%H:%M:%S) supervisor started" >> $log
while true; do
  if pgrep -f adapters/run_sequential.sh >/dev/null; then
    # compare with the previous check, not a fixed baseline: retry_failed.sh truncates the method log on launch
    prev=$(busy)
    while pgrep -f adapters/run_sequential.sh >/dev/null; do
      sleep 30
      cur=$(busy)
      if [ "$cur" -le "$prev" ]; then prev=$cur; else
        pkill -f adapters/run_sequential.sh; pkill -f "_run.py --indices"
        echo "$(date +%H:%M:%S) server_busy failure: run stopped" >> $log
        echo "$(date +%H:%M:%S) paused by supervisor: relay server_busy" >> logs/sequential.log
        break
      fi
    done
  fi
  tail -1 logs/sequential.log | grep -q "all done" && { echo "$(date +%H:%M:%S) all done, supervisor exits" >> $log; exit 0; }
  tail -1 logs/sequential.log | grep -q "STOPPED" && { echo "$(date +%H:%M:%S) disk stop, supervisor exits" >> $log; exit 1; }
  ok=0
  while [ $ok -lt 3 ]; do
    if probe; then ok=$((ok + 1)); else ok=0; fi
    sleep 120
  done
  echo "$(date +%H:%M:%S) relay healthy (3 probes), resuming" >> $log
  nohup adapters/run_sequential.sh > /dev/null 2>&1 &
  sleep 10
done
