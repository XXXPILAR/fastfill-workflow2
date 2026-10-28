"""LayoutGPT (baselines/LayoutGPT, run_layoutgpt_3d.py) on test300: its chat prompt (form_prompt_for_chatgpt: system
instruction, CSS-style lines, k-similar in-context examples by room size, the 7000-token input budget, K = 8, metres),
re-run here because its loader only reads ATISS' preprocessed 3D-FRONT bedroom / living-room boxes.

Changed for our task, kept as small as possible:
  * in-context examples are training rows of data_v4_v2_fixed (same room type when known), ranked by room size like its
    ``load_features(floor_plan=False)``; "Available furnitures" / frequencies are those examples' categories
  * each CSS line carries the object id, ``category[obj_0003] {...}``, so the answer maps back to our objects
  * the query lists the objects to place (category, description) without sizes: as in LayoutGPT, the model writes
    each object's length / width / height in its own answer; an object it leaves out gets its category's median
    answered size (else 0.5 m) at the room centre and is counted ``missing``. Plus doors / windows / fixed objects / constraints; its Condition block keeps room type and size
  * "orientation" is our yaw in degrees (counter-clockwise from +x; the examples teach the convention), "depth" the
    bottom height; left / top are x / y from the room's minimum corner
    python with_api.py <python> layoutgpt_run.py --indices 34 --out runs/layoutgpt
"""
import argparse, json, math, os, random, re, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import relay  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]          # related work code/baselines (the repos and runs)
K, LIMIT = 8, 7000


def chat(messages):
    return relay.chat(messages)  # the relay's Responses API (relay.py)


def extent(room):
    xs, ys = [p[0] for p in room["floor_polygon_xy_m"]], [p[1] for p in room["floor_polygon_xy_m"]]
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def condition_text(room):
    _, _, L, W = extent(room)
    return f"Condition:\nRoom Type: {room.get('room_type') or 'room'}\nRoom Size: max length {L:.2f}m, max width {W:.2f}m\n"


def css(obj_id, cat, size, xy0, pose):
    d, w, h = size
    x, y, z = pose["bottom_center_m"]
    return (f"{cat}[{obj_id}] {{length: {w:.2f}m; height: {h:.2f}m; width: {d:.2f}m; "
            f"orientation: {round(math.degrees(pose['yaw_rad']))} degrees; left: {x - xy0[0]:.2f}m; top: {y - xy0[1]:.2f}m; depth: {z:.2f}m;}}\n")


def example(row):
    room = row["condition"]["room"]; x0, y0, _, _ = extent(room)
    cats = {o["id"]: o["category"] for o in row["condition"]["objects"]}
    layout = "Layout:\n" + "".join(css(o["id"], cats[o["id"]], o["target_size_local_m"], (x0, y0), o) for o in row["target"]["objects"])
    return condition_text(room), layout


def query(row):
    cond, room = row["condition"], row["condition"]["room"]; x0, y0, _, _ = extent(room)
    text = condition_text(room) + "Furniture to place (exactly these, one line each, keep the ids; give each its size):\n"
    for o in cond["objects"]:
        text += f"{o['category']}[{o['id']}]: {(o.get('description') or '').strip()[:200]}\n"
    poly = room["floor_polygon_xy_m"]
    text += "Floor polygon (left, top): " + ", ".join(f"({p[0] - x0:.2f}, {p[1] - y0:.2f})" for p in poly) + "\n"
    for o in room.get("openings") or []:
        i = o.get("wall_index")
        if isinstance(i, int) and i < len(poly):
            (ax, ay), (bx, by) = poly[i], poly[(i + 1) % len(poly)]
            t = o["position_on_wall"]
            text += f"{o['type']} {o['width_m']:.2f}m wide at left {ax + t * (bx - ax) - x0:.2f}m, top {ay + t * (by - ay) - y0:.2f}m\n"
    for f in room.get("fixed_objects") or []:
        text += css(f["id"], f["category"] + " (fixed, do not output)", f["size_local_m"], (x0, y0), f)
    for c in cond.get("constraints") or []:
        text += "Constraint: " + json.dumps(c) + "\n"
    return text


def parse(reply, row):
    room = row["condition"]["room"]; x0, y0, _, _ = extent(room)
    found = {}
    for m in re.finditer(r"\[(obj_\d+)\]\s*\{([^}]*)\}", reply):
        vals = dict(re.findall(r"(\w+):\s*(-?[\d.]+)", m.group(2)))
        try:
            size = [float(vals["width"]), float(vals["length"]), float(vals["height"])]  # css(): length = our width
            if min(size) <= 0:
                continue
            found[m.group(1)] = (float(vals["left"]) + x0, float(vals["top"]) + y0, float(vals.get("depth", 0)), float(vals["orientation"]), size)
        except (KeyError, ValueError):
            continue
    cats = {o["id"]: o["category"] for o in row["condition"]["objects"]}
    answered = [v[4] for v in found.values()]
    cx, cy = x0 + extent(room)[2] / 2, y0 + extent(room)[3] / 2
    out, missing = [], 0
    for o in row["condition"]["objects"]:
        if o["id"] in found:
            x, y, z, deg, size = found[o["id"]]
        else:
            missing += 1; x, y, z, deg = cx, cy, room.get("floor_z_m") or 0., 0.
            pool = [v[4] for k, v in found.items() if cats[k] == o["category"]] or answered or [[.5, .5, .5]]
            size = [sorted(s[j] for s in pool)[len(pool) // 2] for j in range(3)]
        yaw = math.radians(deg)
        out.append({"id": o["id"], "target_size_local_m": size, "bottom_center_m": [x, y, z],
                    "yaw_rad": (yaw + math.pi) % (2 * math.pi) - math.pi})
    return {"schema_version": "fastfill.v2", "objects": out}, missing


POOL_CACHE = BASE / "runs/layoutgpt_pool.jsonl"


def load_pool(path, n=20000, max_objects=40, seed=0):
    """The retrieval pool, built once and cached as compact rows (condition + target only): parallel shards would
    otherwise each hold the 1.6 GB training file's sample in memory."""
    if POOL_CACHE.exists():
        return [json.loads(l) for l in open(POOL_CACHE)]
    rows = _sample_pool(path, n, max_objects, seed)
    POOL_CACHE.parent.mkdir(parents=True, exist_ok=True)
    tmp = POOL_CACHE.with_suffix(".tmp")
    with open(tmp, "w") as f:
        for r in rows:
            f.write(json.dumps({"condition": {"room": r["condition"]["room"], "objects": [
                {"id": o["id"], "category": o["category"]} for o in r["condition"]["objects"]]}, "target": r["target"]}) + "\n")
    tmp.replace(POOL_CACHE)
    return [json.loads(l) for l in open(POOL_CACHE)]


def _sample_pool(path, n, max_objects, seed):
    rnd, pool = random.Random(seed), []
    with open(path) as f:
        for k, line in enumerate(f):
            if len(pool) < n:
                pool.append(line)
            else:
                j = rnd.randint(0, k)
                if j < n:
                    pool[j] = line
    rows = [json.loads(l) for l in pool]
    return [r for r in rows if len(r["condition"]["objects"]) <= max_objects and r.get("target")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", default=str(ROOT / "test300/rows.jsonl"))
    ap.add_argument("--train", default=str(ROOT / "data_v4_v2_fixed/train.jsonl"))
    ap.add_argument("--indices", type=int, nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(a.rows)]
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    pool = load_pool(a.train)
    for i in a.indices:
        d = out / f"room_{i:03d}"; d.mkdir(parents=True, exist_ok=True)
        if (d / "result.json").exists() and json.loads((d / "result.json").read_text()).get("layout"):
            continue
        t0, rec = time.time(), {"index": i}
        try:
            room = rows[i]["condition"]["room"]; _, _, L, W = extent(room)
            same = [r for r in pool if room.get("room_type") and r["condition"]["room"].get("room_type") == room.get("room_type")]
            cands = same if len(same) >= K else pool
            cands = sorted(cands, key=lambda r: ((extent(r["condition"]["room"])[2] - L) ** 2 + (extent(r["condition"]["room"])[3] - W) ** 2) / 2)
            examples = [example(r) for r in cands[:K]]
            cats = sorted({o["category"] for r in cands[:K] for o in r["condition"]["objects"]} | {o["category"] for o in rows[i]["condition"]["objects"]})
            freq = {c: sum(o["category"] == c for r in cands[:K] for o in r["condition"]["objects"]) for c in cats}
            total = max(1, sum(freq.values()))
            system = ('You are a 3D indoor scene designer. \nInstruction: synthesize the 3D layout of an indoor scene. '
                      'The generated 3D layout should follow the CSS style, where each line starts with the furniture category '
                      'and is followed by the 3D size, orientation and absolute position. Formally, each line should follow the template: \n'
                      "FURNITURE {length: ?m: width: ?m; height: ?m; orientation: ? degrees; left: ?m; top: ?m; depth: ?m;}\n"
                      'All values are in meters but the orientation angle is in degrees.\n\n'
                      f"Available furnitures: {', '.join(cats)} \n"
                      f"Overall furniture frequencies: ({'; '.join(f'{c}: {round(freq[c] / total, 4)}' for c in cats)})\n\n")
            last = query(rows[i]) + "Layout:\n"
            messages, length = [{"role": "system", "content": system}], (len(system) + len(last)) / 4
            for cond_text, layout in examples:  # its budget check, in ~4 characters per token
                if length + (len(cond_text) + len(layout)) / 4 > LIMIT:
                    break
                length += (len(cond_text) + len(layout)) / 4
                messages += [{"role": "user", "content": cond_text + "Layout:\n"}, {"role": "assistant", "content": layout[len("Layout:\n"):]}]
            messages.append({"role": "user", "content": last})
            (d / "messages.json").write_text(json.dumps(messages, indent=1))
            reply, call = chat(messages)
            (d / "reply.txt").write_text(reply)
            rec["layout"], rec["missing"] = parse(reply, rows[i])
            rec["calls"], rec["examples"] = [call], (len(messages) - 2) // 2
        except Exception as e:  # noqa: BLE001
            rec["layout"], rec["error"] = None, f"{type(e).__name__}: {e}"
        rec["seconds"] = time.time() - t0
        (d / "result.json").write_text(json.dumps(rec))
        print(f"room {i}: {'ok' if rec['layout'] else rec['error']} missing={rec.get('missing')} {rec['seconds']:.0f}s", flush=True)
    with open(out / f"predictions_part{a.indices[0]}.jsonl", "w") as p, open(out / f"rows_part{a.indices[0]}.jsonl", "w") as r:
        for i in a.indices:
            rec = json.loads((out / f"room_{i:03d}" / "result.json").read_text())
            p.write(json.dumps({"layout": rec["layout"]}) + "\n"); r.write(json.dumps(rows[i]) + "\n")


if __name__ == "__main__":
    main()
