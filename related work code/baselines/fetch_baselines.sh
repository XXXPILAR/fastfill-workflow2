#!/bin/bash
# Clone the baseline repos at the commits checked locally (2026-10-21; LaviGen and robolayout added 2026-11-01). Runs on
# the server too (login nodes have internet). LayoutVLM, IDesign, ReSpace and robolayout have no license file, so they
# are fetched here rather than committed to our repo. LaviGen ships no trained weights (train from TRELLIS, see README).
set -euo pipefail
cd "$(dirname "$0")"
while read -r repo commit _; do
  name=${repo#*/}
  [ -d "$name/.git" ] || git clone -q --filter=blob:none "https://github.com/$repo.git" "$name"
  git -C "$name" fetch -q --depth 1 origin "$commit" && git -C "$name" checkout -q "$commit"
  echo "$repo @ $(git -C "$name" rev-parse --short HEAD)"
done < SOURCES.txt
