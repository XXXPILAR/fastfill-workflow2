#!/bin/bash
# Generate the assets of the given rooms with TRELLIS-text, assemble the rooms, make viewers. Needs one GPU.
#   bash run_room.sh                 # room_079 (7 assets, ~10-20 min)
#   bash run_room.sh room_015,room_079
#   bash run_room.sh all             # all 20 rooms (159 assets, several hours)
# Resumable: assets already done are skipped. Results: out/<room>.glb, out/<room>.html
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
ROOMS=${1:-room_079}
if [ "$ROOMS" = all ]; then
  ROOMS=$(ls $HERE/RoomGenBench/bench/inputs/scenes | sed 's/\.json$//' | paste -sd, -)
fi
export RGB_ROOT=$HERE/RoomGenBench
export HF_HOME=$HERE/cache/huggingface HF_HUB_OFFLINE=1
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate rgb_trellis
nvidia-smi --query-gpu=name,memory.total --format=csv
KEYS=$(python $HERE/tools/keys_for.py $ROOMS)
echo "rooms: $ROOMS"; echo "assets: $KEYS"
cd $RGB_ROOT/methods/trellis_text
python gen_trellis_text.py --keys $KEYS --chunk 100000 --time-budget 1e9
cd $RGB_ROOT
python bench/assemble.py --method trellis_text --scenes $ROOMS
mkdir -p $HERE/out
for r in ${ROOMS//,/ }; do
  cp results/trellis_text/scenes/$r.glb results/trellis_text/scenes/$r.json $HERE/out/
  python $HERE/tools/make_viewer.py $HERE/out/$r.glb $HERE/out/$r.html trellis_text
done
echo "DONE: $HERE/out"
