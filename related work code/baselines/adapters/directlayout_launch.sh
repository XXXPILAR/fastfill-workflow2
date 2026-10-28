#!/bin/bash
# DirectLayout (directlayout_run.py) on test300 through the relay, same model / effort / relay as the other baselines'
# full_agentsize run (gpt-5.6-sol, medium). Rooms are split by index mod $SHARDS; rerunning resumes (rooms with a layout
# in runs/full_agentsize/directlayout/room_XXX/result.json are skipped); each shard stops below 3 GB free disk.
#   adapters/directlayout_launch.sh                  all 300 rooms, 4 shards
#   ROOMS="34" SHARDS=1 adapters/directlayout_launch.sh      one room (smoke)
# then:  envs/layoutvlm/bin/python adapters/directlayout_run.py --merge --out runs/full_agentsize/directlayout
cd "$(dirname "$0")/.."
export BASELINE_MODEL=${BASELINE_MODEL:-gpt-5.6-sol} BASELINE_REASONING_EFFORT=${BASELINE_REASONING_EFFORT:-medium}
export BASELINE_BASE_URL=${BASELINE_BASE_URL:-https://api.krill-code.net/codex/v1}
V=envs/layoutvlm/bin/python  # has what with_api.py imports (shapely) plus openai / matplotlib
SHARDS=${SHARDS:-4} OUT=${OUT:-runs/full_agentsize/directlayout}
rooms=(${ROOMS:-$(seq 0 299)})
mkdir -p $OUT logs
echo "$(date -u +%FT%TZ) model=$BASELINE_MODEL effort=$BASELINE_REASONING_EFFORT relay=$BASELINE_BASE_URL" >> $OUT/STARTED
for s in $(seq 0 $((SHARDS - 1))); do
  idx=""; for k in "${!rooms[@]}"; do [ $((k % SHARDS)) = $s ] && idx="$idx ${rooms[$k]}"; done
  [ -z "$idx" ] && continue
  nohup $V adapters/with_api.py $V adapters/directlayout_run.py --indices $idx --out $OUT > logs/directlayout_$s.log 2>&1 &
  echo "directlayout shard $s: pid $!"
done
