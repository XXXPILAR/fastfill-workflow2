#!/bin/bash
# One-time setup on the server (login node: needs internet). Creates conda env "rgb_trellis" with TRELLIS
# at the commit RoomGenBench used, and downloads the weights into ./cache so compute nodes need no internet.
#   bash setup_env.sh
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
export HF_HOME=$HERE/cache/huggingface
cd $HERE/RoomGenBench/methods/trellis_text
if [ ! -d TRELLIS ]; then
  git clone --recursive https://github.com/microsoft/TRELLIS.git
  git -C TRELLIS checkout 442aa1e1afb9014e80681d3bf604e8d728a86ee7
  git -C TRELLIS submodule update --init --recursive
fi
cd TRELLIS
# TRELLIS's own installer, run inside our env "rgb_trellis" (python 3.10, torch 2.4 + cu118).
# flash-attn is skipped: the RoomGenBench worker uses xformers (ATTN_BACKEND=xformers).
source "$(conda info --base)/etc/profile.d/conda.sh"
if ! conda env list | grep -q "^rgb_trellis "; then
  conda create -y -n rgb_trellis python=3.10
fi
conda activate rgb_trellis
pip install torch==2.4.0 torchvision==0.19.0 --index-url https://download.pytorch.org/whl/cu118
. ./setup.sh --basic --xformers --diffoctreerast --spconv --mipgaussian --kaolin --nvdiffrast
pip install trimesh==4.5.3 scipy pillow huggingface_hub
python - <<'PY'
from huggingface_hub import snapshot_download
for repo in ("microsoft/TRELLIS-text-xlarge", "JeffreyXiang/TRELLIS-image-large"):
    print(repo, snapshot_download(repo))
PY
echo "SETUP DONE"
