"""DirectLayout (Ran et al. 2025, arXiv 2506.05341; released code in related work code/DirectLayout-main-wait) on test300,
with its own pipeline run unchanged where it can be: its prompts (core/prompts.py), parsers (core/parsers.py,
convert_form), LayoutGenerationService (text -> BEV CSS with its 4-step chain of thought, then BEV -> 3D) and
IterativeOptimizationService's two judges (text reasoning feedback on 4 dimensions + VLM feedback on 3 rendered views
and the CoT on 3 dimensions), then one BEV + 3D refinement round with CRITERIA_INTRO, its defaults (views 0 / 1 / 2,
max_retries 3, max_iterations 1). Every chat call goes to the relay with the baselines' model (relay.py: the model,
reasoning effort and the dropping of temperature / max_tokens are the relay's, as for every other baseline). The paper's
fine-tuned model is not released (its README says to use a modern LLM instead).

Changed for our task, kept as small as possible:
  * rendering: services/rendering.py renders per-object GLB assets with Blender (bpy); there are no assets for test300
    and no Blender here, so its views are drawn as labelled 3D boxes (matplotlib, the same 3 cameras: top-down, and the
    two corner views of utils/assemble.py), the front edge marked. The judge prompt already speaks of "the bounding box
    of each object ... labeled with the object category"
  * optimize(): copied from services/optimization.py with one change: its file names are the scene prompt itself, which
    for our object lists exceeds the 255-byte file name limit, so the room key is room_XXX. The generation result is
    copied for each retry (theirs keeps the messages a failed attempt appended)
  * the canvas: their scenes are 256 x 256 x 160 px with 1 px = 1 cm (convert_form's PIXEL_TO_METER = 0.01); here
    each room's own extent in cm (length along x, width along y, height = room height)
  * the scene prompt ("The scene is a bedroom with a bed (bed), ...") lists our objects by id, so each CSS line maps
    back (convert_form keys lines by a \\w+ name), plus what every baseline gets: floor polygon, doors / windows, fixed
    objects (in its CSS, not to be output), constraints, and one line fixing its orientation convention (0 degrees =
    front towards +y, counter-clockwise), which its prompt leaves open
  * each object's given support (support_parent: floor / wall / another object) is in the prompt, as the input gives it
  * the judges' answers: theirs must be a ```json block (parsers.extract_json); a valid JSON object without the block is
    read too (counted ``critic_lenient``), so a well-formed judgement is not lost to formatting
  * sizes are DirectLayout's own answer (length / width / height, as in its paper); a line convert_form cannot read is
    read by a looser pattern (counted ``parse_fallback``)
Scoring is strict: ``predictions.jsonl`` has a room's layout only when the final answer holds every object exactly once
(``missing_ids`` / ``duplicate_ids`` empty); ``predictions_filled.jsonl`` also keeps the incomplete ones, the missing
objects filled in (category median answered size, else 0.5 m, at the room centre) and duplicates reduced to their first
line, reported separately. ``calls`` holds every request of a room, failed rooms included.
Output: <out>/room_XXX/result.json in the other adapters' format (layout, calls, missing, seconds, error; ``layout`` is
the filled one), plus the messages, both layouts and the renders; ``--merge`` writes both prediction files and audit.json.
    python with_api.py <python> directlayout_run.py --indices 34 --out runs/full_agentsize/directlayout
    python directlayout_run.py --merge --out runs/full_agentsize/directlayout
"""
import argparse, copy, json, logging, math, re, shutil, statistics, sys, time, types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
RW = HERE.parents[1]  # related work code
FF4 = RW.parent
MIN_FREE_GB = 3
CRITIC_STATS = {"lenient": 0}  # judge answers read without their ```json block, per room
logger = logging.getLogger("directlayout_run")


# ---------------------------------------------------------------- relay client (OpenAI-shaped, as their code calls it)
class RelayClient:
    """client.chat.completions.create(messages=..., model=..., temperature=..., max_tokens=...) -> .choices[0].message.content"""

    def __init__(self):
        self.calls = []
        self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=self._create))

    def _create(self, messages, **_):
        import relay
        try:
            text, call = relay.chat(messages)
        except Exception:  # relay.chat gave up after its attempts: no usage, still a request made (as sitecustomize.py)
            self.calls.append({"usage": None, "failed_attempts": 10})
            raise
        self.calls.append(call)
        # stripped: their BEV check is result.endswith("</Answer Organization>")
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=text.strip()))])


# ---------------------------------------------------------------- the box renderer standing in for Blender
def corners(o):
    """Footprint corners of one convert_form object (metres): length along x, width along y at 0 degrees, CCW."""
    t = math.radians(o["rotation"]["z_angle"])
    c, s = math.cos(t), math.sin(t)
    hl, hw = o["size_in_meters"]["length"] / 2, o["size_in_meters"]["width"] / 2
    x, y = o["position"]["x"], o["position"]["y"]
    return [(x + c * a - s * b, y + s * a + c * b) for a, b in ((-hl, -hw), (hl, -hw), (hl, hw), (-hl, hw))]


def render_views(objects, room, cats, render_root, room_key, views):
    """Writes <render_root>/view_<v>/<room_key>.png: view 0 top-down (assemble.py's camera above the centre), views 1
    and 2 from the (-x, +y) and (+x, -y) corners at its camera height."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    poly, (L, W, H) = room["poly_m"], room["size_m"]
    cmap = plt.get_cmap("tab20")
    label = lambda o: cats.get(o["id"]) or o.get("category", "?")  # noqa: E731
    colours = {c: cmap(k % 20) for k, c in enumerate(sorted({label(o) for o in objects}))}
    for v in views:
        path = Path(render_root) / f"view_{v}" / f"{room_key}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        if v == 0:
            fig, ax = plt.subplots(figsize=(8, 8), dpi=128)
            ax.fill(*zip(*poly), facecolor="#f2efe8", edgecolor="black", lw=2)
            for kind, (a, b) in room["openings_m"]:
                ax.plot([a[0], b[0]], [a[1], b[1]], color="#d62728" if kind == "door" else "#1f77b4", lw=5, solid_capstyle="butt")
            for o in room["fixed"] + objects:
                fixed = o in room["fixed"]
                cs = corners(o)
                ax.fill(*zip(*cs), facecolor="#bbbbbb" if fixed else colours[label(o)], alpha=.55,
                        edgecolor="black", lw=.8, hatch="//" if fixed else None)
                ax.plot([cs[2][0], cs[3][0]], [cs[2][1], cs[3][1]], color="black", lw=2.5)  # front edge (+width side)
                cx, cy = o["position"]["x"], o["position"]["y"]
                ax.text(cx, cy, f"{o['id']}\n{label(o)}", ha="center", va="center", fontsize=6)
            ax.set_xlim(-.2, L + .2); ax.set_ylim(-.2, W + .2); ax.set_aspect("equal")
            ticks = lambda n: [k for k in range(0, int(n * 100) + 1, 100 if n < 8 else 200)]  # noqa: E731
            ax.set_xticks([t / 100 for t in ticks(L)], [str(t) for t in ticks(L)], fontsize=7)
            ax.set_yticks([t / 100 for t in ticks(W)], [str(t) for t in ticks(W)], fontsize=7)
            ax.set_xlabel("center_x (px)"); ax.set_ylabel("center_y (px)")
            ax.set_title("BEV, top-down (thick edge = object front; grey hatched = fixed; red = door, blue = window)", fontsize=8)
        else:
            fig = plt.figure(figsize=(8, 8), dpi=128)
            ax = fig.add_subplot(projection="3d")
            # floor outline only: matplotlib does not depth-sort a filled floor against the boxes
            ax.plot(*zip(*(poly + poly[:1])), 0, color="black", lw=1.5)
            for kind, (a, b) in room["openings_m"]:
                ax.plot([a[0], b[0]], [a[1], b[1]], [0, 0], color="#d62728" if kind == "door" else "#1f77b4", lw=4)
            for o in room["fixed"] + objects:
                cs = corners(o)
                z0 = o["position"]["z"] - o["size_in_meters"]["height"] / 2
                z1 = z0 + o["size_in_meters"]["height"]
                faces = [[(*p, z0) for p in cs], [(*p, z1) for p in cs]] + \
                        [[(*cs[k], z0), (*cs[(k + 1) % 4], z0), (*cs[(k + 1) % 4], z1), (*cs[k], z1)] for k in range(4)]
                col = "#bbbbbb" if o in room["fixed"] else colours[label(o)]
                ax.add_collection3d(Poly3DCollection(faces, facecolor=col, edgecolor="black", lw=.4, alpha=.6))
                ax.plot([cs[2][0], cs[3][0]], [cs[2][1], cs[3][1]], [z1, z1], color="black", lw=2)
                ax.text(o["position"]["x"], o["position"]["y"], z1 + .05, label(o), fontsize=6, ha="center")
            d = max(L, W, H) * 1.5  # assemble.py: cam_dist = 1.5 max(size), cam_height = H + 1.5
            elev = math.degrees(math.atan2(H + 1.5 - H / 2, d * math.sqrt(2)))
            ax.view_init(elev=elev, azim=135 if v == 1 else -45)
            ax.set_xlim(0, L); ax.set_ylim(0, W); ax.set_zlim(0, H)
            ax.set_box_aspect((L, W, H))
            ax.set_xlabel("x"); ax.set_ylabel("y")
            ax.set_title(f"view {v}", fontsize=8)
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)


def load_directlayout(repo):
    """Imports DirectLayout's modules from its checkout; services.rendering (Blender) is replaced by render_views."""
    sys.path.insert(0, str(repo))
    stub = types.ModuleType("services.rendering")

    class RenderingService:  # never called: optimize() below renders with render_views
        def render_views(self, *a, **k):
            raise RuntimeError("Blender rendering is not used here")
    stub.RenderingService = RenderingService
    sys.modules["services.rendering"] = stub
    from config.settings import ProjectSettings
    from core.parsers import extract_css_content
    from core.prompts import CRITERIA_INTRO
    from services.generation import LayoutGenerationService
    import services.optimization as optimization
    from core.parsers import analyze_response, generate_feedback
    from services.optimization import IterativeOptimizationService, convert_form

    def lenient_analyze_response(text):
        """parsers.analyze_response, which needs a ```json block; else the last JSON object in the answer."""
        try:
            return analyze_response(text)
        except (ValueError, json.JSONDecodeError):
            dec, last = json.JSONDecoder(), None
            for k in [m.start() for m in re.finditer(r"\{", text or "")]:
                try:
                    obj, _ = dec.raw_decode(text, k)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict) and obj and all(isinstance(v, list) for v in obj.values()):
                    last = obj
            if last is None:
                raise
            CRITIC_STATS["lenient"] += 1
            return generate_feedback(last)
    optimization.analyze_response = lenient_analyze_response
    return types.SimpleNamespace(ProjectSettings=ProjectSettings, extract_css_content=extract_css_content,
                                 CRITERIA_INTRO=CRITERIA_INTRO, LayoutGenerationService=LayoutGenerationService,
                                 IterativeOptimizationService=IterativeOptimizationService, convert_form=convert_form)


# ---------------------------------------------------------------- our room <-> their canvas (1 px = 1 cm from the min corner)
def extent(room):
    xs, ys = [p[0] for p in room["floor_polygon_xy_m"]], [p[1] for p in room["floor_polygon_xy_m"]]
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def px(v):
    return round(v * 100)


def to_theirs(size, pose, x0, y0, z0):
    """Our box (size [d, w, h] in its frame, front = local +x, yaw CCW from +x) -> convert_form's dict, metres."""
    d, w, h = size
    x, y, z = pose["bottom_center_m"]
    deg = (math.degrees(pose["yaw_rad"]) - 90 + 180) % 360 - 180
    return {"rotation": {"z_angle": deg}, "size_in_meters": {"length": w, "width": d, "height": h},
            "position": {"x": x - x0, "y": y - y0, "z": z - z0 + h / 2}}


def css_line(name, o):
    s, p = o["size_in_meters"], o["position"]
    return (f"{name} {{length: {px(s['length'])}px; width: {px(s['width'])}px; height: {px(s['height'])}px; "
            f"center_x: {px(p['x'])}px; center_y: {px(p['y'])}px; center_z: {px(p['z'])}px; "
            f"orientation: {round(o['rotation']['z_angle'])} degrees;}}")


def room_info(row):
    room = row["condition"]["room"]
    x0, y0, L, W = extent(room)
    z0 = room.get("floor_z_m") or 0.
    H = room.get("height_m") or 2.7
    poly = [(x - x0, y - y0) for x, y in room["floor_polygon_xy_m"]]
    openings = []
    for o in room.get("openings") or []:
        i = o.get("wall_index")
        if isinstance(i, int) and i < len(poly):
            (ax, ay), (bx, by) = poly[i], poly[(i + 1) % len(poly)]
            n = math.hypot(bx - ax, by - ay) or 1.
            t, half = o["position_on_wall"], o["width_m"] / 2 / n
            openings.append((o["type"], ((ax + (t - half) * (bx - ax), ay + (t - half) * (by - ay)),
                                         (ax + (t + half) * (bx - ax), ay + (t + half) * (by - ay)))))
    fixed = []
    for f in room.get("fixed_objects") or []:
        fixed.append({"id": f["id"], "category": f["category"], **to_theirs(f["size_local_m"], f, x0, y0, z0)})
    return {"x0": x0, "y0": y0, "z0": z0, "size_m": (L, W, H), "poly_m": poly, "openings_m": openings, "fixed": fixed,
            "raw_openings": room.get("openings") or []}


def scene_description(row, info):
    """Their input is one sentence, "The scene is a bedroom with a bed (bed), two nightstands (nightstand), ..."."""
    cond, room = row["condition"], row["condition"]["room"]
    items = []
    support = {"floor": "on the floor", "wall": "mounted on / against a wall"}
    for o in cond["objects"]:
        desc = (o.get("description") or "").strip()[:200]
        sp = o.get("support_parent")
        sp = f"; {support.get(sp, f'placed on {sp}')}" if sp else ""
        items.append(f"{o['id']} ({o['category']}{': ' + desc if desc and desc != o['category'] else ''}{sp})")
    L, W, H = info["size_m"]
    text = (f"The scene is a {room.get('room_type') or 'room'} with {len(items)} objects, each named by its id: "
            + ", ".join(items) + ". Use each id as the object name of its layout line, exactly once per object, and "
            "place every one of them. Where given, an object's support (on the floor, against a wall, or placed on another "
            "object) is required.\n"
            f"Units: 1 px = 1 cm. center_x runs along the {px(L)}px side, center_y along the {px(W)}px side, from the "
            "room's corner (0, 0). orientation is counter-clockwise; 0 degrees means the object's front faces the "
            "positive center_y direction, 90 degrees the negative center_x direction.\n")
    text += "Floor polygon (center_x, center_y; objects must stay inside it): " + \
        ", ".join(f"({px(x)}, {px(y)})" for x, y in info["poly_m"]) + "\n"
    for (kind, (a, b)), o in zip(info["openings_m"], [o for o in info["raw_openings"] if isinstance(o.get("wall_index"), int)]):
        extra = f", sill {px(o['sill_height_m'])}px" if o.get("sill_height_m") is not None else ""
        text += (f"{kind} {px(o['width_m'])}px wide, {px(o.get('height_m') or 0)}px high{extra}, from "
                 f"({px(a[0])}, {px(a[1])}) to ({px(b[0])}, {px(b[1])})\n")
    for f in info["fixed"]:
        text += f"Already in the room (fixed, do not output): {css_line(f['id'], f)} ({f['category']})\n"
    for c in cond.get("constraints") or []:
        text += "Constraint: " + json.dumps(c) + "\n"
    return text.rstrip()


class Found(dict):
    duplicates = ()


LOOSE = re.compile(r"\b(obj_\d+)\b[^{}\n]*\{([^}]*)\}")


def parse_layout(text, row, dl):
    """convert_form (theirs) per line, then the looser pattern for lines it cannot read; -> {id: convert_form dict}."""
    ids = {o["id"] for o in row["condition"]["objects"]}
    found, lines = Found(), {}
    for o in dl.convert_form(text):
        oid = re.sub(r"_\d+$", "", o["new_object_id"])  # convert_form appends _<count>
        lines[oid] = lines.get(oid, 0) + 1
        if oid in ids and oid not in found:
            found[oid] = o
    fallback = 0
    for m in LOOSE.finditer(text):
        if m.group(1) not in found and m.group(1) in ids:
            lines[m.group(1)] = lines.get(m.group(1), 0) + 1
        if m.group(1) in found or m.group(1) not in ids:
            continue
        vals = dict(re.findall(r"(\w+)\s*:\s*(-?\d+(?:\.\d+)?)", m.group(2)))
        try:
            found[m.group(1)] = {"new_object_id": m.group(1), "rotation": {"z_angle": float(vals.get("orientation", 0))},
                                 "size_in_meters": {k: float(vals[k]) / 100 for k in ("length", "width", "height")},
                                 "position": {k: float(vals[f"center_{k}"]) / 100 for k in ("x", "y", "z")}}
            fallback += 1
        except KeyError:
            continue
    found = Found((k, v) for k, v in found.items() if min(v["size_in_meters"].values()) > 0)
    for k, v in found.items():
        v["id"] = k
    found.duplicates = sorted(k for k, n in lines.items() if n > 1 and k in ids)
    return found, fallback


def to_ours(found, row, info):
    cats = {o["id"]: o["category"] for o in row["condition"]["objects"]}
    L, W, _ = info["size_m"]
    sizes = {k: [v["size_in_meters"]["width"], v["size_in_meters"]["length"], v["size_in_meters"]["height"]] for k, v in found.items()}
    out, missing = [], []
    for o in row["condition"]["objects"]:
        if o["id"] in found:
            v = found[o["id"]]
            size, p = sizes[o["id"]], v["position"]
            x, y, z = p["x"] + info["x0"], p["y"] + info["y0"], p["z"] - size[2] / 2 + info["z0"]
            yaw = math.radians(v["rotation"]["z_angle"]) + math.pi / 2
        else:
            missing.append(o["id"])
            pool = [s for k, s in sizes.items() if cats[k] == o["category"]] or list(sizes.values()) or [[.5, .5, .5]]
            size = [sorted(s[j] for s in pool)[len(pool) // 2] for j in range(3)]
            x, y, z, yaw = info["x0"] + L / 2, info["y0"] + W / 2, info["z0"], 0.
        out.append({"id": o["id"], "target_size_local_m": size, "bottom_center_m": [x, y, z],
                    "yaw_rad": (yaw + math.pi) % (2 * math.pi) - math.pi})
    return {"schema_version": "fastfill.v2", "objects": out}, missing


# ---------------------------------------------------------------- their optimize(), with a short room key
def optimize(opt, dl, prompt, length, width, height, generation_result, render, room, views, max_iterations, retry_limit, log):
    """services/optimization.py IterativeOptimizationService.optimize, its steps and prompts unchanged; file paths use
    ``room`` (room_XXX) instead of the prompt, rendering is ``render(threed_layout, tag) -> render_root``."""
    iteration = 0
    render_path_prefix = f"{render(generation_result.threed_layout, 'initial')}/view_"
    bev_gen_messages = generation_result.bev_gen_messages
    bev_layout = generation_result.bev_layout
    threed_gen_messages = generation_result.threed_gen_messages
    threed_layout = generation_result.threed_layout
    while iteration < max_iterations:
        iteration += 1
        reasoning_feedback = opt._request_reasoning_feedback(prompt=prompt, length=length, width=width,
                                                             threed_layout=threed_layout, retry_limit=retry_limit)
        cot = bev_gen_messages[-1]["content"].split("<Spatial Reasoning>")[1].strip().split("</Spatial Reasoning>")[0].strip()
        cot = cot.split("<Answer Organization>")[0].strip()
        vlm_feedback = opt._request_vlm_feedback(prompt=prompt, length=length, width=width, cot=cot,
                                                 render_path_prefix=render_path_prefix, room=room, views=views,
                                                 retry_limit=retry_limit)
        log.append({"iteration": iteration, "reasoning_feedback": reasoning_feedback, "vlm_feedback": vlm_feedback})
        if reasoning_feedback.strip() == "" and vlm_feedback.strip() == "":
            log[-1]["stopped"] = "no negative feedback"
            break
        suggestions = vlm_feedback + "\n" + reasoning_feedback

        retry_count = 0
        refine_bev_prompt = (dl.CRITERIA_INTRO + "Please re-generate the layout according to the following modifications "
                             "(only refer to the BEV view related comments; the height can be ignored):\n" + suggestions)
        bev_gen_messages.append({"role": "user", "content": refine_bev_prompt})
        while retry_count < retry_limit:
            result = opt.bev_client.chat.completions.create(messages=bev_gen_messages, model=opt.model_settings.bev_model,
                                                            temperature=opt.model_settings.temperature_2d, max_tokens=4096).choices[0].message.content
            if result:
                bev_gen_messages.append({"role": "assistant", "content": result})
                bev_layout = result.split("<Answer Organization>")[-1].strip().split("</Answer Organization>")[0].strip()
                break
            retry_count += 1
        else:
            raise RuntimeError(f"BEV refinement failed after {retry_limit} retries.")

        retry_count = 0
        refine_3d_prompt = (dl.CRITERIA_INTRO + f"{bev_layout}\nBEV layout has been modified. Now, please revise the height and center_z "
                            "of objects according to the following modifications (only refer to the height related "
                            "modifications; the length and width can be ignored):\n" + suggestions)
        threed_gen_messages.append({"role": "user", "content": refine_3d_prompt})
        while retry_count < retry_limit:
            result = opt.openai_client.chat.completions.create(messages=threed_gen_messages, model=opt.model_settings.threed_model,
                                                               temperature=opt.model_settings.temperature_3d, max_tokens=2048).choices[0].message.content
            parsed = dl.extract_css_content(result or "")
            if parsed:
                threed_layout = parsed
                threed_gen_messages.append({"role": "assistant", "content": result})
                break
            retry_count += 1
        else:
            raise RuntimeError(f"3D refinement failed after {retry_limit} retries.")
        render_path_prefix = f"{render(threed_layout, f'refined_{iteration}')}/view_"
        log[-1]["refined"] = True
    return threed_layout, bev_gen_messages, threed_gen_messages


# ---------------------------------------------------------------- one room
def run_room(i, row, dl, d, client):
    settings = dl.ProjectSettings()
    rt, ms = settings.runtime, settings.models
    gen = dl.LayoutGenerationService(bev_client=client, openai_client=client, model_settings=ms)
    opt = dl.IterativeOptimizationService(bev_client=client, openai_client=client, reasoning_client=client,
                                          model_settings=ms, rendering_service=None)
    info = room_info(row)
    L, W, H = (px(v) for v in info["size_m"])
    prompt = scene_description(row, info)
    cats = {o["id"]: o["category"] for o in row["condition"]["objects"]}
    rec = {"index": i, "canvas_px": [L, W, H]}
    (d / "prompt.txt").write_text(prompt)

    # pipeline._run_generation_with_retry
    for attempt in range(rt.max_retries):
        try:
            g = gen.generate(scene_description=prompt, length=L, width=W, height=H, retry_limit=rt.max_retries)
            break
        except Exception as e:  # noqa: BLE001 - theirs logs and retries
            logger.warning("room %s generation attempt %s: %s", i, attempt + 1, e)
            rec.setdefault("generation_errors", []).append(f"{type(e).__name__}: {e}"[:300])
    else:
        raise RuntimeError(f"generation failed after {rt.max_retries} retries")
    (d / "layout_initial.css").write_text(g.threed_layout)

    def render(threed_layout, tag):
        found, _ = parse_layout(threed_layout, row, dl)
        render_views(list(found.values()), info, cats, d / f"render_{tag}", f"room_{i:03d}", rt.views)
        return str(d / f"render_{tag}")

    # pipeline._run_optimization_with_retry: a failure leaves the initial layout
    final, log = g.threed_layout, []
    for attempt in range(rt.max_retries):
        try:
            log = []
            final, bev_msgs, td_msgs = optimize(opt, dl, prompt, L, W, H, copy.deepcopy(g), render, f"room_{i:03d}",
                                                rt.views, rt.max_iterations, rt.max_retries, log)
            (d / "messages.json").write_text(json.dumps({"bev": bev_msgs, "threed": td_msgs}, indent=1))
            rec.pop("optimization_error", None)
            break
        except Exception as e:  # noqa: BLE001
            logger.warning("room %s optimization attempt %s: %s", i, attempt + 1, e)
            rec["optimization_error"] = f"{type(e).__name__}: {e}"[:300]
            final = g.threed_layout
    if "optimization_error" in rec:
        (d / "messages.json").write_text(json.dumps({"bev": g.bev_gen_messages, "threed": g.threed_gen_messages}, indent=1))
    (d / "layout_final.css").write_text(final)
    found, rec["parse_fallback"] = parse_layout(final, row, dl)
    rec["layout"], rec["missing_ids"] = to_ours(found, row, info)
    rec["missing"], rec["duplicate_ids"] = len(rec["missing_ids"]), list(found.duplicates)
    rec["complete"] = not rec["missing_ids"] and not rec["duplicate_ids"]
    rec["feedback"], rec["refined"] = log, any(x.get("refined") for x in log)
    rec["critic_done"] = bool(log) and "optimization_error" not in rec  # both judges answered and were read
    return rec


def merge(rows, out):
    """predictions.jsonl: strict (a layout only when complete); predictions_filled.jsonl: every layout, filled in;
    audit.json: counts over all rooms, calls and seconds of failed rooms included."""
    a = {"rooms": len(rows), "finished": 0, "with_layout": 0, "complete": 0, "errors": 0, "objects": 0,
         "missing_objects": 0, "duplicate_objects": 0, "parse_fallback_lines": 0, "rooms_with_missing": 0,
         "rooms_with_duplicates": 0, "critic_done": 0, "refined": 0, "no_negative_feedback": 0, "optimization_failed": 0,
         "critic_lenient_answers": 0, "requests": 0, "failed_attempts": 0, "prompt_tokens": 0, "completion_tokens": 0}
    secs_all, secs_ok = [], []
    with open(out / "predictions.jsonl", "w") as p, open(out / "predictions_filled.jsonl", "w") as pf, \
            open(out / "rows.jsonl", "w") as r:
        for i, row in enumerate(rows):
            f = out / f"room_{i:03d}" / "result.json"
            rec = json.loads(f.read_text()) if f.exists() else {}
            r.write(json.dumps(row) + "\n")
            pf.write(json.dumps({"layout": rec.get("layout")}) + "\n")
            p.write(json.dumps({"layout": rec.get("layout") if rec.get("complete") else None}) + "\n")
            if not rec:
                continue
            a["finished"] += 1; a["errors"] += bool(rec.get("error"))
            a["objects"] += len(row["condition"]["objects"])
            for c in rec.get("calls") or []:
                a["failed_attempts"] += c.get("failed_attempts") or 0
                if c.get("usage"):
                    a["requests"] += 1
                    a["prompt_tokens"] += c["usage"].get("prompt_tokens") or 0
                    a["completion_tokens"] += c["usage"].get("completion_tokens") or 0
            a["critic_lenient_answers"] += rec.get("critic_lenient") or 0
            secs_all.append(rec["seconds"])
            if not rec.get("layout"):
                continue
            a["with_layout"] += 1; a["complete"] += bool(rec.get("complete"))
            a["missing_objects"] += len(rec.get("missing_ids") or []); a["duplicate_objects"] += len(rec.get("duplicate_ids") or [])
            a["rooms_with_missing"] += bool(rec.get("missing_ids")); a["rooms_with_duplicates"] += bool(rec.get("duplicate_ids"))
            a["parse_fallback_lines"] += rec.get("parse_fallback") or 0
            a["critic_done"] += bool(rec.get("critic_done")); a["refined"] += bool(rec.get("refined"))
            a["no_negative_feedback"] += any(x.get("stopped") for x in rec.get("feedback") or [])
            a["optimization_failed"] += "optimization_error" in rec
            if rec.get("complete"):
                secs_ok.append(rec["seconds"])
    med = lambda v: round(statistics.median(v), 1) if v else None  # noqa: E731
    a.update(median_s_all_finished=med(secs_all), sum_s_all_finished=round(sum(secs_all), 1),
             median_s_complete=med(secs_ok))
    (out / "audit.json").write_text(json.dumps(a, indent=1) + "\n")
    print(json.dumps(a, indent=1))
    print(f"-> {out}/predictions.jsonl (strict), predictions_filled.jsonl, rows.jsonl, audit.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", default=str(FF4 / "test300/rows.jsonl"))
    ap.add_argument("--repo", default=str(next((p for p in (RW / "DirectLayout-main", RW / "DirectLayout-main-wait") if p.is_dir()),
                                                RW / "DirectLayout-main")))
    ap.add_argument("--indices", type=int, nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--merge", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    rows = [json.loads(l) for l in open(a.rows)]
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    if a.merge:
        return merge(rows, out)
    dl = load_directlayout(Path(a.repo).resolve())
    for i in a.indices:
        if shutil.disk_usage(out).free < MIN_FREE_GB * 2 ** 30:
            sys.exit(f"stopped before room {i}: less than {MIN_FREE_GB} GB free disk")
        d = out / f"room_{i:03d}"; d.mkdir(parents=True, exist_ok=True)
        if (d / "result.json").exists() and json.loads((d / "result.json").read_text()).get("layout"):
            continue
        t0, client = time.time(), RelayClient()
        CRITIC_STATS["lenient"] = 0
        try:
            rec = run_room(i, rows[i], dl, d, client)
        except Exception as e:  # noqa: BLE001
            rec = {"index": i, "layout": None, "error": f"{type(e).__name__}: {e}"[:500]}
        rec["calls"], rec["critic_lenient"] = client.calls, CRITIC_STATS["lenient"]  # every request, failed rooms too
        rec["seconds"] = time.time() - t0
        (d / "result.json").write_text(json.dumps(rec))
        print(f"room {i}: {'ok' if rec['layout'] else rec['error']} missing={rec.get('missing')} "
              f"duplicates={len(rec.get('duplicate_ids') or [])} refined={rec.get('refined')} calls={len(rec.get('calls') or [])} {rec['seconds']:.0f}s", flush=True)


if __name__ == "__main__":
    main()
