#!/bin/bash
# Waits until the data volume has at least ${NEED_GB:-5} GB free, then hands over to run_sequential.sh.
# Log: logs/wait_disk.log
cd "$(dirname "$0")/.."
echo "$(date +%H:%M:%S) waiting for ${NEED_GB:-5}G free" >> logs/wait_disk.log
until [ "$(df -g /System/Volumes/Data | tail -1 | awk '{print $4}')" -ge "${NEED_GB:-5}" ]; do sleep 30; done
echo "$(date +%H:%M:%S) disk ok ($(df -h /System/Volumes/Data | tail -1 | awk '{print $4}') free), starting run_sequential" >> logs/wait_disk.log
exec adapters/run_sequential.sh
