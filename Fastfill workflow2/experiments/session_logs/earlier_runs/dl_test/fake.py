import json, math, sys, re
A = "/Users/zhangyang/Downloads/fastfill-v4/related work code/baselines/adapters"
sys.path.insert(0, A)
import relay, directlayout_run as D
rows = [json.loads(l) for l in open("/Users/zhangyang/Downloads/fastfill-v4/test300/rows.jsonl")]
fixed_i = next(i for i, r in enumerate(rows) if r["condition"]["room"].get("fixed_objects"))
nonrect = next(i for i, r in enumerate(rows) if len(r["condition"]["room"]["floor_polygon_xy_m"]) > 4)
IDX = [0, fixed_i, nonrect]
state = {}
def gt_css(row, drop=()):
    info = D.room_info(row)
    lines = []
    for o in row["target"]["objects"]:
        if o["id"] in drop: continue
        t = D.to_theirs(o["target_size_local_m"], o, info["x0"], info["y0"], info["z0"])
        lines.append(D.css_line(o["id"], t))
    return "\n".join(lines)
def fake_chat(messages, **k):
    m = messages[-1]["content"]; text = m if isinstance(m, str) else m[0]["text"]
    row = state["row"]; n = len(messages)
    state["kinds"].append(text[:60])
    if "plan the BEV layout" in text:
        css = gt_css(row, drop=state["drop"])
        out = f"<Entity Extraction>\nx\n</Entity Extraction>\n<Order Decision>\ny\n</Order Decision>\n<Spatial Reasoning>\nreason\n</Spatial Reasoning>\n<Answer Organization>\n{css}\n</Answer Organization>\n"
    elif "upscaling a 2D layout" in text or "revise the height" in text:
        css = gt_css(row, drop=state["drop"])
        if state["loose"]: css = css.replace("obj_0000 {", "obj_0000 (chair) {", 1)
        out = "```css\n" + css + "\n```"
    elif "four dimensions" in text:
        out = 'ok\n```json\n{"chair": ["Yes","No","Yes","Yes"]}\n```'
    elif "three dimensions" in text:
        assert isinstance(m, list) and len(m) == 4, "VLM call should carry 3 images"
        out = '```json\n{"table": ["Yes","Yes","Yes"]}\n```'
    elif "re-generate the layout" in text:
        out = "<Spatial Reasoning>\nr2\n</Spatial Reasoning>\n<Answer Organization>\n" + gt_css(row) + "\n</Answer Organization>"
    else:
        raise AssertionError(text[:200])
    return out, {"usage": {"prompt_tokens": 1, "completion_tokens": 1}, "failed_attempts": 0}
relay.chat = fake_chat
dl = D.load_directlayout(D.RW / "DirectLayout-main")
from pathlib import Path
for i in IDX:
    row = rows[i]; state.update(row=row, kinds=[], drop={row["condition"]["objects"][-1]["id"]}, loose=True)
    d = Path(f"out/room_{i:03d}"); d.mkdir(parents=True, exist_ok=True)
    client = D.RelayClient(); rec = D.run_room(i, row, dl, d, client); rec["calls"] = client.calls
    gt = {o["id"]: o for o in row["target"]["objects"]}
    err = 0
    for o in rec["layout"]["objects"]:
        g = gt[o["id"]]
        if o["id"] in state["drop"]: continue
        e = max(max(abs(a - b) for a, b in zip(o["target_size_local_m"], g["target_size_local_m"])),
                max(abs(a - b) for a, b in zip(o["bottom_center_m"], g["bottom_center_m"])),
                abs((o["yaw_rad"] - g["yaw_rad"] + math.pi) % (2 * math.pi) - math.pi))
        err = max(err, e)
    print(f"room {i}: objs={len(gt)} fixed={len(row['condition']['room'].get('fixed_objects') or [])} poly={len(row['condition']['room']['floor_polygon_xy_m'])} "
          f"missing={rec['missing']} fallback={rec['parse_fallback']} refined={rec['refined']} calls={len(rec['calls'])} max_err={err:.4f} opt_err={rec.get('optimization_error')}")
    print("  calls:", [k[:30] for k in state["kinds"]])
    print("  feedback:", rec["feedback"])
json.dump(rec, open("last.json", "w"))
