"""The upstream task agent, simulated: one LLM call per room writes household tasks a mobile manipulator could be asked
to do there, each naming the object ids it uses and the ids it opens, in the form make_task_rooms.py reads
(tasks_source.json). The answer is checked (every id an object of the room, what is opened used by the task, at least
one task); a wrong answer is sent back with what is wrong, at most --retries times; a room still without a valid task
is reported and left out. Every request and answer is kept in <output dir>/task_agent/room_XXX.json.

The LLM sees what the upstream agent would: the room type and size, and per object its id, category, support and
description. Requests go through the relay (workflow.llm.ask) under the shared request limit, retried on transient
problems (WORKFLOW_LLM_ATTEMPTS, 0 = until they pass).

    ../.venv/bin/python experiments/task_agent.py --rows ../test150tasks/base_rows.jsonl \\
        --output ../test150tasks/tasks_source.json --api relay --model gpt-6.1-sol --rpm 30 --workers 6
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from workflow import llm  # noqa: E402  (also puts the fastfill package on sys.path)
from workflow.credentials import api_settings  # noqa: E402

INSTRUCTIONS = """You are the task agent of a household robot. The robot is a mobile manipulator: a base 0.5 m wide \
that drives on the floor and one arm that reaches 0.85 m. The user message is JSON: a room (its type and size) and \
every object in it (id, category, what it stands on: "floor", "wall" or another object's id, and a description).

Write household tasks the robot could be asked to do in this room, using only these objects.

Answer with one JSON object only, no prose:
{"tasks": [{"text": "...", "uses": ["<id>", ...], "articulation": ["<id>", ...]}]}

Rules:
- Write 2 or 3 tasks. Each is one everyday instruction: take an object from one piece of furniture to another (a \
table, desk, shelf, counter, cabinet top, bed, sofa or seat), open furniture to put something in or take something \
out, or bring an object to someone on a seat or bed. Only small objects are picked up and carried (cups, books, \
bottles, food, toys, clothes, tools); furniture is never carried, it is where things are taken from, put on or put \
in, or what is opened. Do not move objects from the floor to the floor. No two tasks may be the same, and different \
tasks should use mostly different objects.
- If the room has no small object to carry, a task may bring an item the robot carries in (name it in "text", do not \
list it in "uses") to a piece of furniture, or take an item out of furniture it opens.
- "text": the instruction in at most 25 words, with just the words of each object's description that tell it apart \
from objects of the same category (a colour, a material, a shape or where it is).
- "uses": the id of every object the task needs: what the robot picks up or operates, the object it now stands on, \
where it goes, and the furniture the robot must stand at. Only ids from the room; 1 to 6 per task.
- "articulation": the ids, among "uses", of furniture the robot must open (doors, drawers, a lid, a fridge or washer \
door). Only furniture that has them, by its category or description; [] when nothing is opened.
- Do not use wall decorations (art, frames, mirrors, signs, lights on walls) and do not invent objects."""


def request_text(row: dict) -> str:
    room = row["condition"]["room"]
    xs = [p[0] for p in room["floor_polygon_xy_m"]]
    ys = [p[1] for p in room["floor_polygon_xy_m"]]
    objects = [{"id": o["id"], "category": o["category"], "on": o.get("support_parent") or "floor",
                "description": " ".join(o["description"].split()[:40])} for o in row["condition"]["objects"]]
    return json.dumps({"room": {"type": room.get("room_type") or "room",
                                "size_m": [round(max(xs) - min(xs), 2), round(max(ys) - min(ys), 2)]},
                       "objects": objects}, ensure_ascii=False)


def problems(answer: dict, row: dict) -> tuple[list[dict], list[str]]:
    """(the valid tasks, what is wrong with the others)."""
    ids = {o["id"] for o in row["condition"]["objects"]}
    tasks, wrong = [], []
    for n, t in enumerate(answer.get("tasks") or []):
        if not isinstance(t, dict) or not isinstance(t.get("text"), str) or not t["text"].strip():
            wrong.append(f"task {n + 1}: no text")
            continue
        uses = [str(i) for i in t.get("uses") or []]
        art = [str(i) for i in t.get("articulation") or []]
        unknown = sorted(set(uses + art) - ids)
        if unknown:
            wrong.append(f"task {n + 1}: ids not in the room {unknown}")
            continue
        if not uses or len(set(uses)) > 6:
            wrong.append(f"task {n + 1}: uses must list 1 to 6 ids")
            continue
        if not set(art) <= set(uses):
            wrong.append(f"task {n + 1}: articulation ids not in uses {sorted(set(art) - set(uses))}")
            continue
        if any(set(uses) == set(prev["uses"]) for prev in tasks):
            wrong.append(f"task {n + 1}: the same objects as an earlier task")
            continue
        tasks.append({"text": t["text"].strip(), "uses": list(dict.fromkeys(uses)), "articulation": sorted(set(art))})
    if len(tasks) < 2:
        wrong.append(f"{len(tasks)} valid task(s): write 2 or 3 different ones")
    elif len(tasks) > 3:
        tasks = tasks[:3]
    return tasks, wrong


def one(k: int, row: dict, settings: dict, out_dir: Path, retries: int) -> dict:
    path = out_dir / f"room_{k:03d}.json"
    if path.exists():
        rec = json.loads(path.read_text())
        if rec.get("tasks"):
            return rec
    prompt = request_text(row)
    messages, calls, tasks, wrong = prompt, [], [], []
    for attempt in range(retries + 1):
        try:
            text, call = llm.ask(INSTRUCTIONS, messages, model=settings["model"], base_url=settings["base_url"],
                                 api_key=settings["api_key"])
        except (RuntimeError, ValueError) as exc:
            wrong = [f"{type(exc).__name__}: {exc}"[:300]]
            break
        calls.append({**call, "answer": text})
        try:
            answer = json.loads(text[text.find("{"):text.rfind("}") + 1])
        except ValueError:
            answer, wrong = {}, ["the answer is not one JSON object"]
        else:
            tasks, wrong = problems(answer, row)
        if tasks and not wrong:
            break
        if tasks and attempt == retries:
            break  # keep the valid ones (also a single one)
        messages = prompt + "\n\nYour previous answer had these problems, answer again in full:\n- " + "\n- ".join(wrong)
    rec = {"room": k, "source": row["provenance"].get("source"), "scene_id": row["provenance"].get("scene_id"),
           "prompt": prompt, "calls": calls, "tasks": tasks, "problems_left": wrong if not tasks else [],
           "cost_usd": round(sum(c.get("cost_usd") or 0 for c in calls), 4)}
    path.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rows", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True, help="tasks_source.json (make_task_rooms.py --tasks)")
    ap.add_argument("--api", choices=("official", "relay"), default="relay")
    ap.add_argument("--base-url")
    ap.add_argument("--model")
    ap.add_argument("--rpm", type=int, default=30)
    ap.add_argument("--rpm-file", type=Path)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--retries", type=int, default=2)
    a = ap.parse_args(argv)
    rows = [json.loads(l) for l in a.rows.read_text().splitlines() if l.strip()]
    settings = api_settings(a.api, a.base_url, a.model)
    os.environ["WORKFLOW_RPM"] = str(a.rpm)
    os.environ["WORKFLOW_RPM_FILE"] = str((a.rpm_file or a.output.parent / ".rpm_state.json").resolve())
    out_dir = a.output.parent / "task_agent"
    out_dir.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    with ThreadPoolExecutor(a.workers) as pool:
        recs = list(pool.map(lambda kr: one(kr[0], kr[1], settings, out_dir, a.retries), enumerate(rows)))
    failed = [r["room"] for r in recs if not r["tasks"]]
    a.output.write_text(json.dumps({
        "author": f"task agent: {settings['model']} through experiments/task_agent.py, one call per room "
                  f"(retries {a.retries}), {time.strftime('%Y-%m-%d')}",
        "rule": "Each task names the objects it needs by id: the object handled, where it is now, where it goes, the "
                "furniture the robot works at, and what it must open (articulation). Those objects are required; "
                "every other object of the room is expansion.",
        "instructions": INSTRUCTIONS, "rows": str(a.rows), "failed_rooms": failed,
        "rooms": [{"room": r["room"], "tasks": r["tasks"]} for r in recs if r["tasks"]]}, indent=1, ensure_ascii=False))
    print(json.dumps({"rooms": len(rows), "with_tasks": len(rows) - len(failed), "failed": failed,
                      "tasks": sum(len(r["tasks"]) for r in recs), "cost_usd": round(sum(r["cost_usd"] for r in recs), 2),
                      "seconds": round(time.perf_counter() - start)}))


if __name__ == "__main__":
    main()
