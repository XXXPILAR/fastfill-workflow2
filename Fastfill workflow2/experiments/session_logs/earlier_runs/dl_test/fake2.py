import json, sys, subprocess
from pathlib import Path
A = "/Users/zhangyang/Downloads/fastfill-v4/related work code/baselines/adapters"
sys.path.insert(0, A)
import relay, directlayout_run as D
rows = [json.loads(l) for l in open("/Users/zhangyang/Downloads/fastfill-v4/test300/rows.jsonl")]
S = {}
def css(row, drop=(), dup=False):
    info = D.room_info(row); L = []
    for o in row["target"]["objects"]:
        if o["id"] in drop: continue
        L.append(D.css_line(o["id"], D.to_theirs(o["target_size_local_m"], o, info["x0"], info["y0"], info["z0"])))
    if dup: L.append(L[0])
    return "\n".join(L)
def fake(messages, **k):
    m = messages[-1]["content"]; t = m if isinstance(m, str) else m[0]["text"]; row, mode = S["row"], S["mode"]
    if mode == "genfail": raise RuntimeError("relay gave no completion")
    if mode == "badformat" and "plan the BEV layout" in t:
        return "<Answer Organization>\nno closing tag", {"usage": {"prompt_tokens": 10, "completion_tokens": 5}, "failed_attempts": 0}
    if "plan the BEV layout" in t:
        body = "" if mode == "empty" else css(row, dup=mode == "dup")
        out = f"<Spatial Reasoning>\nr\n</Spatial Reasoning>\n<Answer Organization>\n{body}\n</Answer Organization>"
    elif "upscaling a 2D layout" in t or "revise the height" in t:
        out = "```css\n" + ("x {}" if mode == "empty" else css(row, dup=mode == "dup")) + "\n```"
    elif "four dimensions" in t:
        out = 'Judgement:\n{"chair": ["Yes","No","Yes","Yes"]}' if mode == "plainjson" else '```json\n{"chair": ["Yes","Yes","Yes","Yes"]}\n```'
    elif "three dimensions" in t:
        out = 'Final: {"table": ["Yes","No","Yes"]} done' if mode == "plainjson" else '```json\n{"table": ["Yes","Yes","Yes"]}\n```'
    elif "re-generate the layout" in t:
        out = "<Spatial Reasoning>\nr2\n</Spatial Reasoning>\n<Answer Organization>\n" + css(row) + "\n</Answer Organization>"
    else: raise AssertionError(t[:100])
    return out, {"usage": {"prompt_tokens": 10, "completion_tokens": 5}, "failed_attempts": 0}
relay.chat = fake
dl = D.load_directlayout(Path(D.main.__globals__["RW"]) / "DirectLayout-main")
sys.argv = ["x", "--out", "out2", "--indices", "0", "7", "34", "45", "2"]
modes = {0: "normal", 7: "empty", 34: "plainjson", 45: "genfail", 2: "badformat"}
orig = D.run_room
def wrapped(i, row, dl_, d, client):
    S.update(row=row, mode=modes[i]); return orig(i, row, dl_, d, client)
D.run_room = wrapped
D.load_directlayout = lambda repo: dl
D.main()
modes[0] = "dup"; import shutil; shutil.rmtree("out2/room_000"); sys.argv[-4:] = ["0"]; D.main()
for i in (0, 7, 34, 45, 2):
    r = json.load(open(f"out2/room_{i:03d}/result.json"))
    print(i, modes[i], {k: r.get(k) for k in ("complete", "missing", "duplicate_ids", "refined", "critic_done", "critic_lenient", "error")}, "calls", len(r["calls"]))
sys.argv = ["x", "--out", "out2", "--merge"]; D.main()
