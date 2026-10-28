#!/bin/bash
# smoke test: room 129, gpt-6.1-sol medium via the relay, shared 30 RPM
cd "/Users/zhangyang/Downloads/fastfill-v4/related work code/baselines"
R=/Users/zhangyang/Downloads/fastfill-v4
V=$R/.venv/bin/python
export BASELINE_BASE_URL=https://api.kbsfdxc.net/codex/v1 BASELINE_MODEL=gpt-6.1-sol BASELINE_REASONING_EFFORT=medium
export WORKFLOW_RPM=30 WORKFLOW_RPM_FILE="$R/Fastfill workflow2/experiments/exp150/.rpm_state.json"
for m in layoutgpt holodeck layoutvlm; do
  case $m in
    layoutgpt) py=$V; extra=(--train "$R/data_v4_v2_fixed/train.jsonl");;
    holodeck)  py=envs/holodeck/bin/python; extra=();;
    layoutvlm) py=envs/layoutvlm/bin/python; extra=();;
  esac
  export BASELINE_USAGE_FILE="$PWD/runs/smoke_g61/${m}_usage.jsonl"
  t=$(date +%s)
  timeout 1800 $V adapters/with_api.py $py adapters/${m}_run.py --rows "$R/test300/rows.jsonl" "${extra[@]}" --indices 129 --out runs/smoke_g61/$m > runs/smoke_g61/$m.log 2>&1
  echo "DONE $m exit $? $(( $(date +%s)-t ))s"
done
echo ALLDONE
