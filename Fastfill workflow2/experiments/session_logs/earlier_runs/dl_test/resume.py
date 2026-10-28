import json, sys
from pathlib import Path
sys.path.insert(0, "/Users/zhangyang/Downloads/fastfill-v4/related work code/baselines/adapters")
exec(open("fake2.py").read().split("dl = D.load_directlayout")[0])
dl = D.load_directlayout(D.RW / "DirectLayout-main")
D.load_directlayout = lambda repo: dl
orig = D.run_room
def wrapped(i, row, dl_, d, client):
    S.update(row=row, mode="normal"); return orig(i, row, dl_, d, client)
D.run_room = wrapped
sys.argv = ["x", "--out", "out2", "--indices", "45"]; D.main()
print("calls.jsonl lines:", sum(1 for _ in open("out2/room_045/calls.jsonl")), "| result.json calls:", len(json.load(open("out2/room_045/result.json"))["calls"]))
sys.argv = ["x", "--out", "out2", "--merge"]; D.main()
