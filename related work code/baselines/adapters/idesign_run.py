"""Run the official I-Design pipeline (baselines/IDesign: create_initial_design -> correct_design -> refine_design ->
create_object_clusters -> backtrack, unchanged) on rectangular test300 rooms.

I-Design picks its own objects from a free-text preference and only knows an axis-aligned W x D x H box with four walls
(no doors, windows or polygons). So the preference text names exactly our objects, with our ids as object ids and
FastFill E's sizes, plus doors / windows / fixed objects / constraints in words. Its outputs are mapped back by id;
an object it did not keep, or could not place, is counted ``missing`` and put at the room centre. The output keeps
FastFill's sizes (I-Design may change them; its positions use its own).
Its Admin agent asks a human for input (``human_input_mode`` ALWAYS); stdin gives empty lines, i.e. pressing Enter.
The relay's model replaces every config model name (adapters/sitecustomize.py); the config comes from an environment
variable, never a file.

    yes '' | python with_api.py <idesign env python> idesign_run.py --indices 34 --out runs/idesign
"""
import argparse, json, math, os, sys, time, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]          # related work code/baselines (the repos and runs)
REPO = BASE / "IDesign"


def rectangle(poly):
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    corners = {(round(x, 3), round(y, 3)) for x, y in poly}
    ok = len(poly) == 4 and len({c[0] for c in corners}) == 2 and len({c[1] for c in corners}) == 2
    return ok, min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def preference(row, sized, x0, y0):
    cond, room = row["condition"], row["condition"]["room"]
    sizes = {o["id"]: o["target_size_local_m"] for o in sized["objects"]}
    lines = [f"A {room.get('room_type') or 'room'}. Use exactly these {len(cond['objects'])} objects and no others, "
             "with these exact ids as new_object_id and these sizes (length x width x height in metres; length is the "
             "side-to-side extent, width the front-to-back extent):"]
    for o in cond["objects"]:
        d, w, h = sizes[o["id"]]
        lines.append(f"- {o['id']}: {o['category']} ({o['description'][:120]}), {w:.2f} x {d:.2f} x {h:.2f}")
    poly = room["floor_polygon_xy_m"]
    for o in room.get("openings") or []:
        i = o.get("wall_index")
        if isinstance(i, int) and i < len(poly):
            (ax, ay), (bx, by) = poly[i], poly[(i + 1) % len(poly)]
            t = o["position_on_wall"]
            lines.append(f"There is a {o['type']} {o['width_m']:.2f} m wide centred at x={ax + t * (bx - ax) - x0:.2f}, "
                         f"y={ay + t * (by - ay) - y0:.2f}" + (" (keep the floor in front of it clear)." if o["type"] == "door" else "."))
    for f in room.get("fixed_objects") or []:
        d, w, _ = f["size_local_m"]
        lines.append(f"A fixed {f['category']} of {w:.2f} x {d:.2f} m is at x={f['bottom_center_m'][0] - x0:.2f}, "
                     f"y={f['bottom_center_m'][1] - y0:.2f}; keep clear of it.")
    for c in cond.get("constraints") or []:
        t = c["type"]
        lines.append({"against_wall": lambda: f"{c['object_id']} must be against a wall.",
                      "faces": lambda: f"{c['object_id']} must face {c['target_id']}.",
                      "near": lambda: f"{c['object_id']} must be within {c.get('max_distance_m', 1.0):.2f} m of {c['target_id']}.",
                      "between": lambda: f"{c['object_id']} must be between " + " and ".join(c["target_ids"]) + ".",
                      "on": lambda: f"{c['object_id']} must be on {c['parent_id']}."}.get(t, lambda: json.dumps(c))())
    lines.append("x runs west to east, y south to north, origin at the south-west corner.")
    return "\n".join(lines)


def to_layout(row, sized, scene_graph, x0, y0, W, D):
    sizes = {o["id"]: o["target_size_local_m"] for o in sized["objects"]}
    placed = {o.get("new_object_id"): o for o in scene_graph if isinstance(o, dict)}
    floor_z = row["condition"]["room"].get("floor_z_m") or 0.
    out, missing = [], 0
    for o in row["condition"]["objects"]:
        p = placed.get(o["id"])
        size = sizes[o["id"]]
        if p is None or "position" not in p:
            missing += 1
            out.append({"id": o["id"], "target_size_local_m": size, "bottom_center_m": [x0 + W / 2, y0 + D / 2, floor_z], "yaw_rad": 0.})
            continue
        angle = float((p.get("rotation") or {}).get("z_angle", 0.))
        yaw = math.radians(90. - angle)  # I-Design: 0 faces the north wall (+y), 90 the east wall (+x)
        their_h = float(p["size_in_meters"]["height"])
        z = floor_z + float(p["position"]["z"]) - their_h / 2  # its z is the box centre
        out.append({"id": o["id"], "target_size_local_m": size,
                    "bottom_center_m": [x0 + float(p["position"]["x"]), y0 + float(p["position"]["y"]), z],
                    "yaw_rad": (yaw + math.pi) % (2 * math.pi) - math.pi})
    return {"schema_version": "fastfill.v2", "objects": out}, missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", default=str(ROOT / "test300/rows.jsonl"))
    ap.add_argument("--sizes", default=str(ROOT / "server_runs/test300-v4/test300_E/predictions_remask4L.jsonl"))
    ap.add_argument("--indices", type=int, nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(a.rows)]
    sized = [json.loads(l)["layout"] for l in open(a.sizes)]
    out = Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    entry = {"api_key": os.environ["OPENAI_API_KEY"], "base_url": os.environ["OPENAI_BASE_URL"]}
    os.environ["OAI_CONFIG_LIST.json"] = json.dumps([{**entry, "model": "gpt-4"}, {**entry, "model": "gpt-4-1106-preview"}])
    os.chdir(REPO); sys.path.insert(0, str(REPO))
    import matplotlib; matplotlib.use("Agg")
    from IDesign import IDesign
    for i in a.indices:
        d = out / f"room_{i:03d}"; d.mkdir(parents=True, exist_ok=True)
        if (d / "result.json").exists() and json.loads((d / "result.json").read_text()).get("layout"):
            continue
        t0, rec = time.time(), {"index": i}
        try:
            ok, x0, y0, W, D = rectangle(rows[i]["condition"]["room"]["floor_polygon_xy_m"])
            if not ok:
                raise ValueError("I-Design takes only axis-aligned rectangular rooms")
            if sized[i] is None:
                raise ValueError("no FastFill sizes for this room")
            text = preference(rows[i], sized[i], x0, y0)
            (d / "preference.txt").write_text(text)
            H = rows[i]["condition"]["room"].get("height_m") or 2.6
            design = IDesign(no_of_objects=len(rows[i]["condition"]["objects"]), user_input=text, room_dimensions=[W, D, H])
            design.create_initial_design()
            design.correct_design()
            design.refine_design()
            design.create_object_clusters(verbose=False)
            design.backtrack()
            (d / "scene_graph.json").write_text(json.dumps(design.scene_graph, indent=1, default=str))
            rec["layout"], rec["missing"] = to_layout(rows[i], sized[i], design.scene_graph, x0, y0, W, D)
        except Exception as e:  # noqa: BLE001
            rec["layout"], rec["error"] = None, f"{type(e).__name__}: {e}"
            (d / "error.txt").write_text(traceback.format_exc())
        rec["seconds"] = time.time() - t0
        (d / "result.json").write_text(json.dumps(rec))
        print(f"room {i}: {'ok' if rec['layout'] else rec['error']} missing={rec.get('missing')} {rec['seconds']:.0f}s", flush=True)
    with open(out / "predictions.jsonl", "w") as p, open(out / "rows.jsonl", "w") as r:
        for i in a.indices:
            rec = json.loads((out / f"room_{i:03d}" / "result.json").read_text())
            p.write(json.dumps({"layout": rec["layout"]}) + "\n"); r.write(json.dumps(rows[i]) + "\n")


if __name__ == "__main__":
    main()
