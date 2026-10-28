"""LLM completion of what a test300 room does not give but a baseline needs: every object's size, the support of
objects without a ``support_parent``, and the room type when it is missing. Nothing comes from FastFill or the target:
the input is the row's ``condition`` only. One chat call per room (same relay / model / reasoning as the method).

Holodeck (its object-selection step asks the LLM for each object's size) and LayoutVLM (sizes come from its
Objaverse assets, which we do not have) use it; LayoutGPT writes sizes in its own answer and does not.

    completed, calls = complete(row)     # completed: {"room_type", "objects": [{id, target_size_local_m, support_parent}]}
``target_size_local_m`` is [depth, width, height] in metres (depth = front-back, the object's facing axis), the layout
format's order. Given ``support_parent`` values are kept; the LLM's are checked (unknown ids, self-support and cycles
fall back to "floor", counted in ``completed["support_fallbacks"]``).
"""
import json, os, re

import relay


def chat(prompt):
    text, call = relay.chat([{"role": "user", "content": prompt}])
    return text, dict(call, step="complete")


def prompt_for(row):
    cond, room = row["condition"], row["condition"]["room"]
    xs, ys = [p[0] for p in room["floor_polygon_xy_m"]], [p[1] for p in room["floor_polygon_xy_m"]]
    lines = [f"Room type: {room.get('room_type') or 'unknown (infer it)'}",
             f"Room extent: {max(xs) - min(xs):.2f} m x {max(ys) - min(ys):.2f} m, height {room.get('height_m') or 'unknown'} m",
             "Objects:"]
    for o in cond["objects"]:
        given = f" [support given: {o['support_parent']}]" if o.get("support_parent") else ""
        lines.append(f"- {o['id']}: {o['category']}: {(o.get('description') or '').strip()[:300]}{given}")
    for c in cond.get("constraints") or []:
        lines.append("Constraint: " + json.dumps(c))
    return ("You are furnishing a room. For every object below, give its real-world size in metres as "
            "[width, depth, height] (width = left-right seen from its front, depth = front-back, height = vertical), and "
            "what it stands on: \"floor\", \"wall\" (mounted on a wall) or the id of another object it rests on. "
            "Also give the room type.\n\n" + "\n".join(lines) +
            "\n\nAnswer with JSON only, no prose:\n"
            '{"room_type": "...", "objects": {"obj_0000": {"size": [w, d, h], "support": "floor"}, ...}}\n'
            "Include every object id exactly once.")


def parse(reply, row):
    text = reply.strip()
    m = re.search(r"\{.*\}", text, re.S)
    data = json.loads(m.group(0) if m else text)
    room = row["condition"]["room"]
    ids = [o["id"] for o in row["condition"]["objects"]]
    got = data.get("objects") or {}
    support, sizes, missing = {}, {}, 0
    for o in row["condition"]["objects"]:
        g = got.get(o["id"]) or {}
        try:
            w, d, h = (float(v) for v in g["size"])
            assert min(w, d, h) > 0
        except Exception:  # noqa: BLE001 - the LLM left it out: its category median among the answered ones
            w = d = h = None; missing += 1
        sizes[o["id"]] = (w, d, h)
        support[o["id"]] = o.get("support_parent") or (g.get("support") if isinstance(g.get("support"), str) else None) or "floor"
    answered = [s for s in sizes.values() if s[0] is not None]
    for o in row["condition"]["objects"]:
        if sizes[o["id"]][0] is None:
            same = [sizes[p["id"]] for p in row["condition"]["objects"] if p["category"] == o["category"] and sizes[p["id"]][0] is not None]
            pool = same or answered or [(0.5, 0.5, 0.5)]
            sizes[o["id"]] = tuple(sorted(s[k] for s in pool)[len(pool) // 2] for k in range(3))
    fallbacks = 0
    for i in ids:  # an LLM support must name another object (given ones are already validated by the dataset)
        s = support[i]
        if s not in ("floor", "wall") and (s not in support or s == i):
            support[i] = "floor"; fallbacks += 1
    for i in ids:  # break cycles
        seen, cur = {i}, support[i]
        while cur not in ("floor", "wall"):
            if cur in seen:
                support[i] = "floor"; fallbacks += 1; break
            seen.add(cur); cur = support[cur]
    return {"room_type": room.get("room_type") or str(data.get("room_type") or "room"),
            "objects": [{"id": i, "target_size_local_m": [sizes[i][1], sizes[i][0], sizes[i][2]], "support_parent": support[i]} for i in ids],
            "size_missing": missing, "support_fallbacks": fallbacks}


def complete(row, cache=None):
    """``cache``: a path; a finished completion there is reused (its calls are still reported, marked ``cached``)."""
    if cache and os.path.exists(cache):
        rec = json.load(open(cache))
        return rec["completed"], [dict(c, cached=True) for c in rec["calls"]]
    last, calls = None, []
    for _ in range(3):  # a reply that is not the JSON asked for is asked again
        reply, call = chat(prompt_for(row))
        calls.append(call)
        try:
            completed = parse(reply, row)
            break
        except Exception as e:  # noqa: BLE001
            last = e
    else:
        raise RuntimeError(f"completion reply not parsable: {last}")
    if cache:
        with open(cache, "w") as f:
            json.dump({"completed": completed, "calls": calls, "reply": reply}, f)
    return completed, calls
