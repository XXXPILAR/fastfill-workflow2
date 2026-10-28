"""Run Holodeck's layout stage (baselines/Holodeck: FloorObjectGenerator + WallObjectGenerator, their prompts, constraint
parser and DFS solvers, unchanged) on test300 rooms.

Replaced, because the rest of Holodeck builds its own house and picks its own Objaverse assets:
  * object selection / retrieval -> our furniture list; each object's box has the size an LLM gives (complete.py: its
                                     object-selection step's "size" field, one call per room), as do the supports
                                     the row leaves out and a missing room type. Nothing comes from FastFill or the target
  * rooms / doors / windows       -> the row's floor polygon, and doors / windows as Holodeck's door / window boxes
                                     (1 m deep each side of the doorway, as doors.create_rectangles); fixed objects as
                                     extra obstacles in the solvers' initial state
  * LLM                           -> our relay (BASELINE_MODEL, reasoning medium) through relay.chat
  * small objects (on other objects) need AI2-THOR's receptacle search; not run: each is put at the centre of its
    parent's top (counted as ``on_object_rule``)
Our input constraints are added under Holodeck's object list in its floor prompt (it has no field for them).
Objects the DFS solver cannot fit are dropped by Holodeck; they are counted (``missing``) and put at the room centroid.

    python with_api.py <holodeck env python> holodeck_run.py --indices 34 --out runs/holodeck
"""
import argparse, json, math, os, sys, time, traceback, types, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import relay  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]          # related work code/baselines (the repos and runs)
REPO = BASE / "Holodeck"


def llm(prompt):
    try:
        text, call = relay.chat([{"role": "user", "content": prompt}])  # the relay's Responses API (relay.py)
    except Exception:
        llm.log.append({"usage": None, "failed_attempts": 10})
        raise
    llm.calls += 1
    llm.log.append(call)
    return text
llm.calls, llm.log = 0, []


def side_boxes(a, b, depth):
    """Holodeck doors.create_rectangles: the two depth-deep rectangles either side of segment a-b (metres)."""
    (ax, ay), (bx, by) = a, b
    vx, vy = bx - ax, by - ay
    n = math.hypot(vx, vy) or 1.
    px, py = -vy / n * depth, vx / n * depth
    return [[[ax + px, ay + py], [bx + px, by + py], [bx, by], [ax, ay]],
            [[ax, ay], [bx, by], [bx - px, by - py], [ax - px, ay - py]]]


def build(row, sized):
    cond, room = row["condition"], row["condition"]["room"]
    poly = room["floor_polygon_xy_m"]
    sizes = {o["id"]: o for o in sized["objects"]}
    doors, windows = [], []
    for o in room.get("openings") or []:
        i = o.get("wall_index")
        if not isinstance(i, int) or i >= len(poly):
            continue
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % len(poly)]
        L = math.hypot(bx - ax, by - ay) or 1.
        t, h = o["position_on_wall"], o["width_m"] / 2 / L
        a = [ax + (t - h) * (bx - ax), ay + (t - h) * (by - ay)]; b = [ax + (t + h) * (bx - ax), ay + (t + h) * (by - ay)]
        if o["type"] == "door":
            doors.append({"doorBoxes": side_boxes(a, b, 1.0), "assetPosition": {"y": o["height_m"] / 2}})
        else:
            sill = o.get("sill_height_m") or 0.
            windows.append({"windowBoxes": side_boxes(a, b, 0.1), "holePolygon": [{"y": sill}, {"y": sill + o["height_m"]}]})
    names, kinds, database, count = {}, {}, {}, {}
    for o in cond["objects"]:
        cat = o["category"].lower().replace("|", " ").replace(",", " ").strip()
        names[o["id"]] = f"{cat}-{count.get(cat, 0)}"; count[cat] = count.get(cat, 0) + 1
        depth, width, height = sizes[o["id"]]["target_size_local_m"]
        database[names[o["id"]]] = {"assetMetadata": {"boundingBox": {"x": width, "y": height, "z": depth}}}
        s = sizes[o["id"]]["support_parent"]  # complete.py: the row's, else the LLM's
        kinds[o["id"]] = s if s in ("floor", "wall") else ("on", s)
    room_type = sized["room_type"]
    holo_room = {"id": "room|0", "roomType": room_type, "vertices": [tuple(p) for p in poly],
                 "floorPolygon": [{"x": p[0], "y": 0, "z": p[1]} for p in poly]}
    floor = [(names[i], names[i]) for i, k in kinds.items() if k == "floor"]
    wall = [(names[i], names[i]) for i, k in kinds.items() if k == "wall"]
    extra = []
    for c in cond.get("constraints") or []:
        n = lambda i: names.get(i, i)
        t = c["type"]
        extra.append({"against_wall": lambda: f"{n(c['object_id'])} against a wall",
                      "faces": lambda: f"{n(c['object_id'])} faces {n(c['target_id'])}",
                      "near": lambda: f"{n(c['object_id'])} within {c.get('max_distance_m', 1.0) * 100:.0f} cm of {n(c['target_id'])}",
                      "between": lambda: f"{n(c['object_id'])} between " + " and ".join(n(x) for x in c["target_ids"]),
                      "on": lambda: f"{n(c['object_id'])} on top of {n(c['parent_id'])}"}.get(t, lambda: json.dumps(c))())
    return holo_room, doors, windows, floor, wall, database, names, kinds, extra, room_type


def run_room(row, sized):
    from shapely.geometry import Polygon
    from ai2holodeck.generation.floor_objects import FloorObjectGenerator
    from ai2holodeck.generation.wall_objects import WallObjectGenerator
    from ai2holodeck.generation.utils import get_bbox_dims
    room, doors, windows, floor, wall, database, names, kinds, extra, room_type = build(row, sized)
    retriever = types.SimpleNamespace(database=database)
    fog = FloorObjectGenerator(retriever, llm)
    if extra:  # our constraints, under Holodeck's object list in its own prompt
        template = fog.constraint_prompt.template.replace(
            "{objects}\n", "{objects}\nThe user also requires: " + "; ".join(extra).replace("{", "(").replace("}", ")") + ".\n")
        fog.constraint_prompt.template = template
    fixed = {}
    for k, f in enumerate(row["condition"]["room"].get("fixed_objects") or []):
        d, w, h = f["size_local_m"]; x, y = f["bottom_center_m"][:2]; c, s = math.cos(f["yaw_rad"]), math.sin(f["yaw_rad"])
        corners = [(100 * (x + c * u - s * v), 100 * (y + s * u + c * v)) for u, v in ((d/2, w/2), (-d/2, w/2), (-d/2, -w/2), (d/2, -w/2))]
        fixed[f"fixed-{k}"] = ((100 * x, 100 * y), 0, corners, 1)
    original = fog.get_door_window_placements
    fog.get_door_window_placements = lambda *a, **kw: {**original(*a, **kw), **fixed}

    def solution2placement(solutions, object_name2id, room_id):
        # Holodeck's FloorObjectGenerator.solution2placement, except that it skips the solver's initial-state
        # obstacles by "is not one of the objects to place" instead of by the substrings door / window / open in the
        # name: our fixed obstacles ("fixed-k") and objects such as "opener-0" or "open wall shelf unit-0" broke that.
        placements = []
        for object_name, solution in solutions.items():
            if object_name not in object_name2id:
                continue
            dimension = get_bbox_dims(fog.database[object_name2id[object_name]])
            placement = fog.json_template.copy()
            placement["assetId"] = object_name2id[object_name]
            placement["id"] = f"{object_name} ({room_id})"
            placement["position"] = {"x": solution[0][0] / 100, "y": dimension["y"] / 2, "z": solution[0][1] / 100}
            placement["rotation"] = {"x": 0, "y": solution[1], "z": 0}
            placement["roomId"] = room_id
            placement["vertices"] = list(solution[2])
            placement["object_name"] = object_name
            placements.append(placement)
        return placements
    fog.solution2placement = solution2placement
    selected = {room_type: {"floor": floor, "wall": wall}}
    placements = fog.generate_objects_per_room((room, doors, windows, [], selected, True)) if floor else []
    wall_height = row["condition"]["room"].get("height_m") or 2.6
    wall_placements = []
    if wall:
        wog = WallObjectGenerator(retriever, llm)
        scene = {"floor_objects": placements, "wall_height": wall_height}
        wall_placements = wog.generate_wall_objects_per_room((room, scene, doors, windows, [], wall_height, selected, True))
    return placements, wall_placements, names, kinds


def to_layout(row, sized, placements, wall_placements, names, kinds):
    sizes = {o["id"]: o for o in sized["objects"]}
    by_name = {p["object_name"]: p for p in placements + wall_placements}
    poly = row["condition"]["room"]["floor_polygon_xy_m"]
    from shapely.geometry import Polygon
    cx, cy = Polygon(poly).centroid.coords[0]
    floor_z = row["condition"]["room"].get("floor_z_m") or 0.
    out, missing, rule = {}, 0, 0
    order = [o["id"] for o in row["condition"]["objects"]]
    for i in order:
        if kinds[i] in ("floor", "wall"):
            size = sizes[i]["target_size_local_m"]
            p = by_name.get(names[i])
            if p is None:
                missing += 1
                out[i] = {"id": i, "target_size_local_m": size, "bottom_center_m": [cx, cy, floor_z], "yaw_rad": 0.}
                continue
            yaw = math.radians(90 - p["rotation"]["y"])  # Holodeck: rotation 0 faces +y, 90 faces +x (clockwise)
            z = floor_z if kinds[i] == "floor" else p["position"]["y"] - size[2] / 2
            out[i] = {"id": i, "target_size_local_m": size, "bottom_center_m": [p["position"]["x"], p["position"]["z"], z],
                      "yaw_rad": (yaw + math.pi) % (2 * math.pi) - math.pi}
    for _ in range(len(order)):  # on-object items: parent's top centre (parents may themselves be on objects)
        for i in order:
            if i in out or kinds[i] in ("floor", "wall"):
                continue
            parent = kinds[i][1]
            if parent in out or parent not in kinds:
                base = out.get(parent)
                rule += 1
                if base is None:
                    out[i] = {"id": i, "target_size_local_m": sizes[i]["target_size_local_m"], "bottom_center_m": [cx, cy, floor_z], "yaw_rad": 0.}
                else:
                    top = base["bottom_center_m"][2] + base["target_size_local_m"][2]
                    out[i] = {"id": i, "target_size_local_m": sizes[i]["target_size_local_m"],
                              "bottom_center_m": [*base["bottom_center_m"][:2], top], "yaw_rad": base["yaw_rad"]}
    for i in order:  # not reached through its parents (complete.py breaks cycles; kept as a guard)
        if i not in out:
            missing += 1
            out[i] = {"id": i, "target_size_local_m": sizes[i]["target_size_local_m"], "bottom_center_m": [cx, cy, floor_z], "yaw_rad": 0.}
    return {"schema_version": "fastfill.v2", "objects": [out[i] for i in order]}, missing, rule


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", default=str(ROOT / "test300/rows.jsonl"))
    ap.add_argument("--indices", type=int, nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(a.rows)]
    out = Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    stub = types.ModuleType("ai2holodeck.generation.objaverse_retriever"); stub.ObjathorRetriever = object
    sys.modules[stub.__name__] = stub  # asset retrieval (CLIP / SBERT over Objaverse) is replaced by our list
    os.chdir(REPO); sys.path.insert(0, str(REPO))
    import matplotlib; matplotlib.use("Agg")
    from complete import complete
    for i in a.indices:
        d = out / f"room_{i:03d}"; d.mkdir(parents=True, exist_ok=True)
        if (d / "result.json").exists() and json.loads((d / "result.json").read_text()).get("layout"):
            continue
        t0, calls0, rec = time.time(), llm.calls, {"index": i}
        (d / "error.txt").unlink(missing_ok=True)  # a previous attempt's
        llm.log = []
        done = []
        try:
            sized, done = complete(rows[i], cache=str(d / "completion.json"))
            rec["size_missing"], rec["support_fallbacks"] = sized["size_missing"], sized["support_fallbacks"]
            placements, wall_placements, names, kinds = run_room(rows[i], sized)
            (d / "holodeck_placements.json").write_text(json.dumps({"floor": placements, "wall": wall_placements}, default=str, indent=1))
            rec["layout"], rec["missing"], rec["on_object_rule"] = to_layout(rows[i], sized, placements, wall_placements, names, kinds)
        except Exception as e:  # noqa: BLE001
            rec["layout"], rec["error"] = None, f"{type(e).__name__}: {e}"
            (d / "error.txt").write_text(traceback.format_exc())
        rec["seconds"], rec["calls"] = time.time() - t0, done + llm.log
        rec["llm_calls"] = len(done) + llm.calls - calls0
        (d / "result.json").write_text(json.dumps(rec))
        print(f"room {i}: {'ok' if rec['layout'] else rec['error']} missing={rec.get('missing')} on_rule={rec.get('on_object_rule')} "
              f"{rec['seconds']:.0f}s {rec['llm_calls']} calls", flush=True)
    with open(out / f"predictions_part{a.indices[0]}.jsonl", "w") as p, open(out / f"rows_part{a.indices[0]}.jsonl", "w") as r:
        for i in a.indices:
            rec = json.loads((out / f"room_{i:03d}" / "result.json").read_text())
            p.write(json.dumps({"layout": rec["layout"]}) + "\n"); r.write(json.dumps(rows[i]) + "\n")


if __name__ == "__main__":
    main()
