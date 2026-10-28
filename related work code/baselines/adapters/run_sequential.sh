#!/bin/bash
# Low-disk mode: one process at a time, LayoutGPT -> Holodeck -> LayoutVLM, each resuming its unfinished rooms via
# retry_failed.sh with 1 shard. Same safety stop as guard.sh: below 3 GB free disk everything stops and nothing
# further is started. Log: logs/sequential.log
#   nohup adapters/run_sequential.sh > /dev/null 2>&1 &
cd "$(dirname "$0")/.."
export BASELINE_BASE_URL=${BASELINE_BASE_URL:-https://api.krill-code.net/codex/v1}
log=logs/sequential.log
for m in ${METHODS:-layoutgpt holodeck layoutvlm}; do
  echo "$(date +%H:%M:%S) start $m" >> $log
  adapters/retry_failed.sh $m 1 >> $log 2>&1
  sleep 5
  while pgrep -f "_run.py --indices" >/dev/null; do
    free=$(df -g /System/Volumes/Data | tail -1 | awk '{print $4}')
    if [ "$free" -lt 3 ]; then
      pkill -f "_run.py --indices"
      echo "$(date +%H:%M:%S) STOPPED during $m: disk free ${free}G, $(sysctl -n vm.swapusage)" >> $log
      exit 1
    fi
    sleep 30
  done
  echo "$(date +%H:%M:%S) $m finished" >> $log
done
echo "$(date +%H:%M:%S) all done" >> $log
