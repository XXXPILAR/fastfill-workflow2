"""Run the official LayoutVLM (baselines/LayoutVLM, main.py's one_shot path) on test300 rooms.

Input per room: the row's condition only (floor polygon, wall height, the furniture list with category and
description). What LayoutVLM takes from its Objaverse assets and the row does not give, an LLM fills in first
(complete.py, one call per room): every object's size, the support type of objects without a support_parent, a
missing room type. Nothing comes from FastFill or the target. Doors / windows / fixed objects / constraints written into LayoutVLM's free-text
layout_criteria (it has no input fields for them). Every object becomes a box .glb of its size (we have no meshes).

    python with_api.py <layoutvlm env python> layoutvlm_run.py --indices 33 34 --out runs/layoutvlm
Writes <out>/room_<i>/ (LayoutVLM's own files + layout.json), <out>/predictions.jsonl and rows.jsonl (aligned).
"""
import argparse, json, math, os, sys, time, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # ~/Downloads/fastfill-v4
BASE = Path(__file__).resolve().parents[1]          # related work code/baselines (the repos and runs)
REPO = BASE / "LayoutVLM"


def box_glb(path, width, depth, height):
    import trimesh
    # LayoutVLM's renderer: after glTF import (y-up -> Blender z-up) the asset faces -y, then it turns it to face +x.
    # So the mesh's glTF axes are x = width, y = height, z = depth.
    trimesh.creation.box(extents=[width, height, depth]).export(path)


def openings_text(room):
    poly, out = room["floor_polygon_xy_m"], []
    for o in room.get("openings") or []:
        i = o.get("wall_index")
        if not isinstance(i, int) or i >= len(poly):
            continue
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % len(poly)]
        t = o["position_on_wall"]
        out.append(f"a {o['type']} {o['width_m']:.2f} m wide centred at ({ax + t * (bx - ax):.2f}, {ay + t * (by - ay):.2f})"
                   + (" (keep the floor in front of it clear)" if o["type"] == "door" else ""))
    return out


def constraint_text(c, names):
    n = lambda i: names.get(i, i)
    t = c["type"]
    if t == "against_wall": return f"{n(c['object_id'])} should be against a wall"
    if t == "faces": return f"{n(c['object_id'])} should face {n(c['target_id'])}"
    if t == "near": return f"{n(c['object_id'])} should be within {c.get('max_distance_m', 1.0):.2f} m of {n(c['target_id'])}"
    if t == "between": return f"{n(c['object_id'])} should be between " + " and ".join(n(x) for x in c["target_ids"])
    if t == "on": return f"{n(c['object_id'])} should be on top of {n(c['parent_id'])}"
    return json.dumps(c)


def clean(text):
    return text.replace('"', "'").replace("\\", "/").replace("\n", " ").replace("\r", " ")


def build_task(row, sized, room_dir):
    cond, room = row["condition"], row["condition"]["room"]
    sizes = {o["id"]: o for o in sized["objects"]}  # complete.py: LLM sizes, supports
    assets_dir = room_dir / "assets"
    task_assets, names, seen = {}, {}, {}
    for k, o in enumerate(cond["objects"]):
        # LayoutVLM names a category's distinct assets <category>_A .. _Z (main.prepare_task_assets); past 26 the
        # suffix leaves the letters and the generated program does not parse. We give every object its own asset
        # (its own LLM size), so a category with more than 26 objects is split into groups of 26.
        n = seen.get(o["category"], 0); seen[o["category"]] = n + 1
        category = o["category"] if n < 26 else f"{o['category']} group {n // 26 + 1}"
        depth, width, height = sizes[o["id"]]["target_size_local_m"]
        support = sizes[o["id"]]["support_parent"]  # the row's, else the LLM's
        uid = f"o{k:04d}"
        (assets_dir / uid).mkdir(parents=True, exist_ok=True)
        box_glb(assets_dir / uid / f"{uid}.glb", width, depth, height)
        (assets_dir / uid / "data.json").write_text(json.dumps({
            # LayoutVLM pastes these into generated Python as description="..." / variable names: no " \\ or newlines
            "annotations": {"category": clean(category), "description": clean(o["description"][:300]),
                            "onCeiling": support == "ceiling", "onFloor": support == "floor",
                            "onWall": support == "wall", "onObject": support not in ("floor", "wall", "ceiling"),
                            "frontView": 0},
            # main.prepare_task_assets swaps x and y: after the swap x is the depth (the front axis) as in its solver
            "assetMetadata": {"boundingBox": {"x": width, "y": depth, "z": height}}}))
        task_assets[f"{uid}-0"] = {}
        names[o["id"]] = f"the {o['category']} ({uid})"
    criteria = ["place every listed asset inside the room without overlaps; the layout should be functional and follow common sense"]
    if openings_text(room):
        criteria.append("the room has " + "; ".join(openings_text(room)))
    for f in room.get("fixed_objects") or []:
        d, w, h = f["size_local_m"]
        criteria.append(f"a fixed {f['category']} (cannot move) occupies {w:.2f} x {d:.2f} m centred at "
                        f"({f['bottom_center_m'][0]:.2f}, {f['bottom_center_m'][1]:.2f})")
    criteria += [constraint_text(c, names) for c in cond.get("constraints") or []]
    xs = [p[0] for p in room["floor_polygon_xy_m"]]; ys = [p[1] for p in room["floor_polygon_xy_m"]]
    task = {"task_description": f"a {sized['room_type']} of about {max(xs) - min(xs):.1f}m x {max(ys) - min(ys):.1f}m "
                                f"containing exactly the listed assets",
            "layout_criteria": ". ".join(criteria),
            "boundary": {"floor_vertices": [[p[0], p[1], 0.] for p in room["floor_polygon_xy_m"]],
                         "wall_height": room.get("height_m") or 2.6},
            "assets": task_assets}
    return task, assets_dir


def to_layout(result, row, sized, uid_of):
    """``uid_of``: LayoutVLM's renamed instance key (category based, e.g. ``tv_stand-0``) -> our asset uid."""
    sizes = {o["id"]: o for o in sized["objects"]}
    by_uid = {uid_of[key]: pose for key, pose in result.items() if key in uid_of}
    objects = []
    for k, o in enumerate(row["condition"]["objects"]):
        r = by_uid.get(f"o{k:04d}")
        if r is None:
            raise ValueError(f"LayoutVLM placed no pose for {o['id']}")
        size = sizes[o["id"]]["target_size_local_m"]
        x, y = float(r["position"][0]), float(r["position"][1])
        z = float(r["position"][2]) - size[2] / 2 if len(r["position"]) > 2 else 0.  # its z is the box centre
        yaw = math.radians(float(r["rotation"][-1] if isinstance(r["rotation"], list) else r["rotation"]))
        objects.append({"id": o["id"], "target_size_local_m": size, "bottom_center_m": [x, y, z],
                        "yaw_rad": (yaw + math.pi) % (2 * math.pi) - math.pi})
    return {"schema_version": "fastfill.v2", "objects": objects}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", default=str(ROOT / "test300/rows.jsonl"))
    ap.add_argument("--indices", type=int, nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(a.rows)]
    out = Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    os.chdir(REPO); sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "third_party" / "Rotated_IoU"))
    from main import prepare_task_assets
    from src.layoutvlm.layoutvlm import LayoutVLM
    from complete import complete
    for i in a.indices:
        room_dir = out / f"room_{i:03d}"
        if (room_dir / "result.json").exists() and json.loads((room_dir / "result.json").read_text()).get("layout"):
            continue
        room_dir.mkdir(parents=True, exist_ok=True)
        t0, record, done = time.time(), {"index": i}, []
        (room_dir / "error.txt").unlink(missing_ok=True)  # a previous attempt's
        usage_file = room_dir / "usage.jsonl"
        usage_file.unlink(missing_ok=True)
        os.environ["BASELINE_USAGE_FILE"] = str(usage_file)
        try:
            sized, done = complete(rows[i], cache=str(room_dir / "completion.json"))
            record["size_missing"], record["support_fallbacks"] = sized["size_missing"], sized["support_fallbacks"]
            task, assets_dir = build_task(rows[i], sized, room_dir)
            (room_dir / "task.json").write_text(json.dumps(task, indent=1))
            solver = LayoutVLM(mode="one_shot", save_dir=str(room_dir), asset_source="objaverse")
            prepared = prepare_task_assets(json.loads(json.dumps(task)), str(assets_dir))
            uid_of = {key: asset["uid"] for key, asset in prepared["assets"].items()}
            (room_dir / "uid_of.json").write_text(json.dumps(uid_of, indent=1))
            result = solver.solve(prepared)
            (room_dir / "layout.json").write_text(json.dumps(result, indent=1, default=float))
            record["layout"] = to_layout(json.loads(json.dumps(result, default=float)), rows[i], sized, uid_of)
        except Exception as e:
            record["layout"], record["error"] = None, f"{type(e).__name__}: {e}"
            (room_dir / "error.txt").write_text(traceback.format_exc())
        record["seconds"] = time.time() - t0
        record["calls"] = done + ([json.loads(l) for l in usage_file.read_text().splitlines()] if usage_file.exists() else [])
        (room_dir / "result.json").write_text(json.dumps(record))
        print(f"room {i}: {'ok' if record['layout'] else record['error']} in {record['seconds']:.0f}s", flush=True)
    with open(out / f"predictions_part{a.indices[0]}.jsonl", "w") as p, open(out / f"rows_part{a.indices[0]}.jsonl", "w") as r:
        for i in a.indices:
            rec = json.loads((out / f"room_{i:03d}" / "result.json").read_text())
            p.write(json.dumps({"layout": rec["layout"]}) + "\n"); r.write(json.dumps(rows[i]) + "\n")


if __name__ == "__main__":
    main()
