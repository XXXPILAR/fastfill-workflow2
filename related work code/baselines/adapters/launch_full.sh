#!/bin/bash
# Full test300 run of LayoutGPT, Holodeck and LayoutVLM with gpt-5.6-sol (reasoning medium), 4 processes per method
# (rooms split by index mod 4). Rerunning resumes: rooms with a layout in <out>/room_XXX/result.json are skipped.
#   adapters/launch_full.sh            then, when all have finished:   python adapters/merge_and_score.py
cd "$(dirname "$0")/.."
export BASELINE_MODEL=${BASELINE_MODEL:-gpt-5.6-sol} BASELINE_REASONING_EFFORT=${BASELINE_REASONING_EFFORT:-medium}
V=/private/tmp/claude-501/-Users-zhangyang-Downloads-fastfill-v4/9a97c220-bfbd-48ee-8fa2-e1fa582d56c6/scratchpad/venv/bin/python
SHARDS=${SHARDS:-4}
mkdir -p runs/full logs
for method in ${METHODS:-layoutgpt holodeck layoutvlm}; do
  date -u +%FT%TZ > runs/full/STARTED_$method
  case $method in
    layoutgpt) py=$V;;
    holodeck)  py=envs/holodeck/bin/python;;
    layoutvlm) py=envs/layoutvlm/bin/python;;
  esac
  for s in $(seq 0 $((SHARDS - 1))); do
    idx=$(seq $s $SHARDS 299 | tr '\n' ' ')
    nohup $V adapters/with_api.py $py adapters/${method}_run.py --indices $idx --out runs/full/$method \
      > logs/full_${method}_$s.log 2>&1 &
    echo "$method shard $s: pid $!"
  done
done
