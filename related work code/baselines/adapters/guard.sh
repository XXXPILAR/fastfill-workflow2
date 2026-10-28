#!/bin/bash
# Only a safety stop: below 3 GB free disk (swap grows onto the disk) every full-run process is stopped and logged,
# nothing is relaunched or scored. Log: logs/guard.log
cd "$(dirname "$0")/.."
echo "$(date +%H:%M:%S) guard started" >> logs/guard.log
while pgrep -f "runs/full" >/dev/null; do
  free=$(df -g /System/Volumes/Data | tail -1 | awk '{print $4}')
  if [ "$free" -lt 3 ]; then
    pkill -f "runs/full"
    echo "$(date +%H:%M:%S) STOPPED all runs: disk free ${free}G, $(sysctl -n vm.swapusage)" >> logs/guard.log
    exit 1
  fi
  sleep 30
done
echo "$(date +%H:%M:%S) no runs left, guard exits" >> logs/guard.log
