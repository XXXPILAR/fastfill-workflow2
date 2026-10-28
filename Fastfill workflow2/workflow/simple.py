"""Workflow 2 (``placement="simple"``, the default here): one placement, one program check, one LLM check.

  ① plan     one LLM call for supports, groups and relations (``planning.make_plan``, semantic only); ``plan_llm=False``
             uses the rules
  ② sizes    one per object: FastFill's when given, else the catalog's
  ③ place    ONE LLM call places every object of the room (``drafting.make_draft``; FastFill gives the sizes only)
  ④ check    the program checks once (``critic.Critic``). If there are hard violations (collision, out of bounds, no
             support, blocked door, broken hard constraint), one repair pass takes them up, each once, by the program
             search at fixed sizes; soft costs are not chased and there is no polish, so wherever the placement is legal
             it is left as the LLM made it
  ⑤ review   the LLM reviews the whole room once (``semantic.SemanticPass``, one round): only severe issues are fixed;
             each fix is repaired by the program and kept only if the program gate passes (no new hard violation;
             reach, access and doors no worse) and a blind pairwise comparison prefers it in both orders
  ⑥ result   the layout, plus the layout after each of ③ ④ ⑤ (``diagnostics.stages``), so a bad result can be traced

Compared with ``placement="staged"`` (workflow 1): no groups, no stages, no freezing, no soft-cost search, no polish,
one review round. LLM calls: 1 plan + 1 placement + 1 review + 3 per severe issue fixed (proposal, two pairwise votes).
"""

from __future__ import annotations

import math
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from .catalog import SizeCatalog
from .contract import check_request, fill_room_defaults, validate_condition, validate_layout
from .credentials import FatalAPIError
from .critic import Critic, load_templates
from .drafting import assemble, make_draft
from .loop import Loop, LoopBudget, make_ask
from .orders import critic_geometry
from .planning import Plan, _required_parents, make_plan
from .robot import Robot, RobotChecker, RobotZones
from .semantic import SOFT_TOLERANCE, SemanticPass


def draft_rank(a) -> tuple:
    """Which of several drafts to repair: the fewest hard violations of any tier, then the smallest total. Not the
    critic's tiered key: a draft's collisions and boundary overlaps are mostly small and the repair fixes them,
    while its robot violations mostly stay (20 rooms, two drafts each: preferring fewer legality violations picked a
    draft with 23 robot violations over one with 3)."""
    return len(a.hard), round(sum(v.magnitude for v in a.hard), 4)


def _layout(condition: dict, placed: dict[str, dict]) -> dict:
    return {"schema_version": condition["schema_version"], "objects": [placed[o["id"]] for o in condition["objects"]]}


def run_simple(condition: dict, sizes: dict[str, list[float]] | None, *, plan: Plan | None = None,
               yaws: dict[str, float] | None = None, catalog_path: str | None = None, llm: bool = True,
               model: str | None = None, base_url: str | None = None, api_key: str | None = None,
               plan_llm: bool = True, repair: bool = True, semantic: bool = True, semantic_fixes: int = 3,
               soft_tolerance: float = SOFT_TOLERANCE, templates_path: str | None = None, beam_width: int = 24,
               candidate_limit: int = 48, semantic_ask=None, robot: Robot | None = None, drafts: int = 1,
               resize: bool = False, robot_margin: float = 0.0, hard_zones: bool = False, relocate: bool = False,
               repair_rounds: int = 1, repair_seconds: float | None = None) -> dict:
    """{status, layout, diagnostics, timing_s}. ``plan``: one made already (the pipeline's), else made here.
    ``semantic_ask`` replaces the LLM client for the review (tests); the review runs only with ``llm`` or it.
    ``robot``: its checks (``robot.RobotChecker``: doors linked, furniture reachable, openable furniture free to open)
    are hard violations in step ④ and the review's gate, and the final layout is reported for it. The placement
    request asks for what the robot needs (``drafting.ROBOT_RULE``), and the repair search ranks its candidates with
    the checks' zones (``robot.RobotZones``). ``drafts``: placement calls made in parallel; the one with the fewest
    hard violations of any kind is repaired (``draft_rank``), and every draft is recorded; each call is paid. ``resize``: when step ④
    leaves legality violations, a second pass may shrink objects by up to 20 % (``Loop(resize=True)``); what was
    resized is reported (``diagnostics.resized``). ``robot_margin``: the placement request, the critic and the
    search use a robot this much wider, so the layout keeps a margin (grid planners keep a clearance; HSM a 1 x 1 m
    door zone); the result is reported for ``robot`` itself. ``hard_zones``: the draft fixes each carrying
    furniture's approach side and the search filters on the robot zones (``RobotZones.reserve``, ``hard``).
    ``relocate`` / ``repair_rounds``: step ④ may move a robot check's blocker anywhere in the room and takes further
    passes while they help (``Loop``). ``repair_seconds``: the program search's time limit for step ④ (the resize
    pass gets a third of it more); None: no limit."""
    start = time.perf_counter()
    validate_condition(condition)
    condition, notes = fill_room_defaults(condition)
    condition = check_request(condition)
    if plan is None:
        plan = make_plan(condition, llm=llm and plan_llm, model=model, base_url=base_url, api_key=api_key,
                         semantic_only=True)
    planned = time.perf_counter()
    catalog, fixed_sizes, size_source = SizeCatalog(catalog_path), {}, {"given": 0, "catalog": 0}
    for obj in condition["objects"]:
        size = (sizes or {}).get(obj["id"])
        if size is not None and len(size) == 3 and all(isinstance(v, (int, float)) and v > 0 for v in size):
            fixed_sizes[obj["id"]], size_source["given"] = [float(v) for v in size], size_source["given"] + 1
        else:
            fixed_sizes[obj["id"]], size_source["catalog"] = catalog.candidates(obj)[0][0], size_source["catalog"] + 1
    geometry = critic_geometry(condition, plan)
    critic = Critic.for_plan(geometry, plan, load_templates(templates_path))
    planned_robot = replace(robot, width_m=robot.width_m + robot_margin) if robot is not None and robot_margin \
        else robot  # what placement, critic and search plan for; the report is for ``robot``
    if robot is not None:
        critic.robot = RobotChecker.for_critic(planned_robot, critic)
        # the search's form of the checks (Geometry.soft_score; with hard_zones also a filter)
        geometry.robot_zones = RobotZones(planned_robot, geometry, hard=hard_zones)
    locked = _required_parents(condition)

    # ③ the placement call(s): with ``drafts`` > 1, that many in parallel, and the one with the fewest violations is kept
    if llm and drafts > 1:
        def one(_k):
            return make_draft(condition, plan, fixed_sizes, geometry, yaws=yaws, robot=planned_robot, model=model,
                              base_url=base_url, api_key=api_key)
        with ThreadPoolExecutor(drafts) as pool:
            tried = list(pool.map(one, range(drafts)))
        assessed_drafts = [critic.assess(p) for p, _info in tried]
        keys = [draft_rank(a) for a in assessed_drafts]
        best = min(range(drafts), key=lambda k: keys[k])
        placed, draft = tried[best]
        draft = {**draft, "calls": [c for _p, info in tried for c in info["calls"]], "chosen": best,
                 "candidates": [{"key": list(a.key()), "rank": list(k), "error": info["error"],
                                 "missing": len(info["missing"]), "layout": _layout(condition, p)}
                                for a, k, (p, info) in zip(assessed_drafts, keys, tried)]}
    elif llm:
        placed, draft = make_draft(condition, plan, fixed_sizes, geometry, yaws=yaws, robot=planned_robot, model=model, base_url=base_url,
                                   api_key=api_key)
    else:  # offline: every object at its fallback (on its support, else the room's representative point)
        placed, missing = assemble(geometry, plan, fixed_sizes, {})
        draft = {"calls": [], "dropped": {}, "missing": missing, "error": "llm disabled"}
    placed_s = time.perf_counter()
    stages = {"draft": _layout(condition, placed)}
    reserved = geometry.robot_zones.reserve(placed) if hard_zones and geometry.robot_zones is not None else {}
    assessed = {"draft": critic.assess(placed)}

    # ④ one program check (and one repair pass over the hard violations only)
    check = {"result": "clean" if not assessed["draft"].hard else "not repaired"}
    if repair and assessed["draft"].hard:
        loop = Loop(geometry, plan, fixed_sizes, catalog, critic, locked_parents=locked,
                    budget=LoopBudget(gpt_repairs=0, min_soft_cost=math.inf, search_seconds=repair_seconds),
                    beam_width=beam_width, candidate_limit=candidate_limit, relocate=relocate, rounds=repair_rounds)
        placed, check = loop.run(placed)
        check["result"] = "repaired"
        if resize and critic.assess(placed).legality:
            # the size fallback: what full sizes could not fix, the search retries with objects up to 20 % smaller
            loop = Loop(geometry, plan, fixed_sizes, catalog, critic, locked_parents=locked,
                        budget=LoopBudget(gpt_repairs=0, min_soft_cost=math.inf,
                                          search_seconds=repair_seconds / 3 if repair_seconds else None),
                        beam_width=beam_width, candidate_limit=candidate_limit, resize=True, relocate=relocate,
                        rounds=repair_rounds)
            placed, check["resize"] = loop.run(placed)
            check["result"] = "repaired with resizing"
    stages["after_check"] = _layout(condition, placed)
    assessed["after_check"] = critic.assess(placed)
    checked_s = time.perf_counter()

    # ⑤ one LLM review of the whole room
    review = {"result": "skipped"}
    review_ask = semantic_ask or (make_ask(model, base_url, api_key) if llm else None)
    if semantic and review_ask is not None:
        current_sizes = {i: list(b["target_size_local_m"]) for i, b in placed.items()}  # resized ones stay resized
        reviewer = SemanticPass(geometry, critic, plan, current_sizes, catalog, locked_parents=locked, ask=review_ask,
                                stage="room", soft_tolerance=soft_tolerance, condition=condition,
                                beam_width=beam_width, candidate_limit=candidate_limit)
        parents = dict(plan.parents)
        everything = set(placed)
        try:
            placed, review = reviewer.run(placed, everything, everything, rounds=1, max_fixes=semantic_fixes)
        except FatalAPIError:
            raise
        except Exception as exc:  # the review is optional: keep the checked layout
            plan.parents.clear()
            plan.parents.update(parents)
            review = {"result": "error", "error": f"{type(exc).__name__}: {exc}"[:300]}
        review["llm_calls"] = reviewer.calls
    stages["final"] = _layout(condition, placed)
    final = assessed["final"] = critic.assess(placed)

    layout = _layout(condition, placed)
    validate_layout(layout, condition)
    end = time.perf_counter()
    return {"status": "clean" if not final.hard else "best_effort", "layout": layout,
            "diagnostics": {"placement": "simple", "notes": notes, "plan_source": plan.source, "plan_llm": plan.llm,
                            "support_parents": dict(plan.parents), "functional_groups": plan.groups,
                            "plan_relations": plan.relations, "size_source": size_source, "sizes": fixed_sizes,
                            "draft": draft, "check": check, "semantic": review, "stages": stages,
                            "assessments": {k: v.summary() for k, v in assessed.items()},
                            "critic": {"loop": {"gpt_calls": []}, "final": final.summary(),
                                       "unresolved": [v.as_dict() for v in final.hard],
                                       "status_detail": "hard_valid" if not final.hard else "violations_remaining"},
                            "hard_issues": [v.as_dict() for v in final.hard],
                            "resized": {i: {"from": [round(v, 4) for v in fixed_sizes[i]],
                                            "to": [round(v, 4) for v in placed[i]["target_size_local_m"]]}
                                        for i in placed if placed[i]["target_size_local_m"] != fixed_sizes[i]},
                            "robot": RobotChecker.for_critic(robot, critic).report(layout, dict(plan.parents))
                            if robot is not None else None,
                            "repair": {"relocate": relocate, "rounds": repair_rounds, "seconds": repair_seconds},
                            "robot_plan": {"margin_m": robot_margin, "hard_zones": hard_zones,
                                           "approach_sides": reserved} if robot is not None else None},
            "timing_s": {"plan": round(planned - start, 3), "place": round(placed_s - planned, 3),
                         "check": round(checked_s - placed_s, 3), "review": round(end - checked_s, 3),
                         "total": round(end - start, 3)}}
