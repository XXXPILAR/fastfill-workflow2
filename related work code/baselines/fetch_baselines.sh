#!/bin/bash
# Clone the five baseline repos at the commits checked locally on 2026-10-21 (run on the server: login nodes have internet).
# LayoutVLM, IDesign and ReSpace have no license file, so they are fetched here rather than committed to our repo.
set -euo pipefail
cd "$(dirname "$0")"
while read -r repo commit _; do
  name=${repo#*/}
  [ -d "$name/.git" ] || git clone -q --filter=blob:none "https://github.com/$repo.git" "$name"
  git -C "$name" fetch -q --depth 1 origin "$commit" && git -C "$name" checkout -q "$commit"
  echo "$repo @ $(git -C "$name" rev-parse --short HEAD)"
done < SOURCES.txt
