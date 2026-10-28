"""Print the asset keys the given scenes use (for gen_trellis_text.py --keys)."""
import json, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1] / "RoomGenBench" / "bench" / "inputs" / "scenes"
keys = []
for scene in sys.argv[1].split(","):
    for obj in json.loads((root / f"{scene}.json").read_text())["objects"]:
        if obj["asset_key"] not in keys:
            keys.append(obj["asset_key"])
print(" ".join(keys))
