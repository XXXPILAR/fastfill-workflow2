#!/bin/bash
# Smoke test of all four baselines with gpt-5.6-sol (reasoning medium) on test300 rooms 34 and 0, in parallel.
cd "$(dirname "$0")/.."
export BASELINE_MODEL=gpt-5.6-sol BASELINE_REASONING_EFFORT=medium
V=/private/tmp/claude-501/-Users-zhangyang-Downloads-fastfill-v4/9a97c220-bfbd-48ee-8fa2-e1fa582d56c6/scratchpad/venv/bin/python
$V adapters/with_api.py envs/layoutvlm/bin/python adapters/layoutvlm_run.py --indices 34 0 --out runs/layoutvlm_56 > logs_layoutvlm_56.log 2>&1 &
$V adapters/with_api.py envs/holodeck/bin/python adapters/holodeck_run.py --indices 34 0 --out runs/holodeck_smoke > logs_holodeck_56.log 2>&1 &
(yes '' | $V adapters/with_api.py envs/idesign/bin/python adapters/idesign_run.py --indices 34 0 --out runs/idesign_smoke > logs_idesign_56.log 2>&1) &
$V adapters/with_api.py $V adapters/layoutgpt_run.py --indices 34 0 --out runs/layoutgpt_smoke > logs_layoutgpt_56.log 2>&1 &
wait
grep -H "^room" logs_*_56.log | cut -c1-260
