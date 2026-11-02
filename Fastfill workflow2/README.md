# FastFill workflow 2 (simple)

A lighter version of `fastfill_workflow`: **one placement, one program check, one LLM check**
(`workflow/simple.py`, the default `placement="simple"`).

1. **Plan**: one LLM call for supports, groups and relations (`planning.make_plan`, semantic only).
2. **Sizes**: one per object, from FastFill when given, otherwise from the size catalog.
3. **Place**: one LLM call places every object in the room (`drafting.make_draft`) and decides every facing. FastFill gives the sizes only: its yaw is trained modulo π, so it gives a box axis, not which way the front faces (73% of its wall-side furniture faces into the room, against 92% for GPT-5.6). `--yaw-mode prompt` still passes it to the LLM as a suggestion, for comparison.
4. **Check**: the program checks once (`critic.Critic`). If there are hard violations, one repair pass takes each of them up once:
   - hard violations: collision, out of bounds, missing support, blocked door, or a broken hard input constraint;
   - the program search keeps sizes fixed;
   - soft costs are not chased and there is no polish, so any part of the layout that is already legal stays as the LLM placed it.
5. **Review**: the LLM reviews the whole room once (`semantic.SemanticPass`, one round), and only severe issues are fixed. A fix is kept only if all of the following hold:
   - the program repairs it;
   - it passes the program gate: no new hard violation, and reach, access and doors are no worse;
   - a blind pairwise comparison prefers it in both orders.
6. **Result**: the layout, plus the layout after each of steps 3, 4 and 5 (`diagnostics.stages`), so a bad result can be traced back to the step that caused it.

The heavier placements of workflow 1 are still available with `--placement staged | group | all`.

## Task mode: required and expansion furniture (2026-11-02)

The upstream task agent sends, per room: the room shell and type, the full furniture list (every object with a
detailed description and its support), which objects the task **requires**, which ones the task **opens**
(articulation), and hard constraints. Every other object is **expansion** furniture. The task mode places all of them,
with this order of priority: legality, then the robot's reach, then the task.

- **Required objects** are never removed and never shrunk. Their violations are repaired first, and they must end
  legal (no collision, inside the room, no blocked door, constraints met) and reachable (the robot reaches them, items
  on furniture are within arm's reach, articulation objects can open).
- **Expansion objects** are checked and repaired the same way. An expansion object is removed only to give way to a
  required object, and only after moving it anywhere in the room (it may shrink by up to 20 %) failed. Its own
  violations never remove it: they are reported (`expansion_issues`).

Steps added to `workflow/simple.py` (on top of steps 1-6 above):

| Step | What it does |
|---|---|
| 3 place | the placement request marks required objects (`"required": true`, `drafting.REQUIRED_RULE`) |
| 4 check | the robot checks cover every object plus the task's (`simple.task_robot`); the repair takes the required objects' violations first (`Loop(first=...)`) and never shrinks them (`keep_sizes`) |
| 4b give way | an expansion object in a required object's violation is moved anywhere in the room, else removed with what stands on it; when several expansion objects block together, the nearest ones are tried (at most `NEAR_BLOCKER_TRIES`), a removal kept only if it helps; one more repair pass after removals |
| 4c required first | if a required object still has a violation: the required objects alone are repaired (or searched for from scratch), then the expansion objects come back one at a time, each kept only where the required objects stay as good (`carry` moves objects standing on required furniture with it) |
| 7 fallback | if a required object is still not legal and reachable, or the workflow fails on an error: only the required objects, laid out by the program without the LLM (`simple.required_only`), legality and reach before the constraints; returned when it leaves the required objects better off, with `status` `fallback_required_only` |

**Input.** The request is the usual `fastfill.v2` condition; every object needs a description beyond its category
(`contract.check_request`, see below). The task's ids are passed beside it: `run_simple(..., required=ids,
articulation=ids)` or `run_draft_workflow(...)`; `experiments/run_draft.py --task-roles` reads them from each row's
`task.required_ids` / `task.articulation_ids` (the format of `test30tasks` / `test150tasks`).

**Output.** The layout holds the objects kept. `diagnostics.task` gives `required`, `articulation`, `expansion`,
`expansion_kept`, `moved` (expansion objects moved out of the way), `removed` (each with what stood on it and the
violations it was removed for), `required_first` (whether step 4c ran and helped), `expansion_issues`, `required_ok` and
`required_issues`. A fallback result also keeps the full layout and its diagnostics in `diagnostics.fallback_from` and
lists the constraints it could not meet (`unmet_constraints`).

**When the fallback runs.** Only when the steps above leave a required object with a violation (in the 10-room test,
1 room of 10), or on an unexpected error. A busy or failing relay does not trigger it: LLM calls are retried
(`WORKFLOW_LLM_ATTEMPTS=0`: until they pass), and a step whose call fails falls back on its own (rules plan, default
draft positions, no review). A rejected key or an exhausted quota (`FatalAPIError`) still stops the run.

**Known limits.**
- Constraint types: `on`, `between`, `against_wall`, `faces`, `faces_direction`, `near`, `clearance`, `keepout`;
  any other type is refused at the input.
- Constraints that involve a removed expansion object are dropped with it; they are not reported yet.
- Contradictory constraints are the upstream agent's to avoid; the fallback still delivers the required objects
  legal and reachable and lists the constraints it could not meet.
- Large rooms take minutes (the program repair uses its 180 s limit); about 5 s per object overall.

```bash
python experiments/run_draft.py --rows ../test30tasks/rows.jsonl --indices 0 1 2 --task-roles \
    --sizes-file experiments/exp30tasks/fastfill/1.7b-all-full/predictions_spread.jsonl --api relay --rpm 30 \
    --robot-width 0.5 --drafts 2 --resize --robot-margin 0.1 --hard-zones --relocate --repair-rounds 3 \
    --repair-seconds 180 --workers 4 --budget-usd 5 --out experiments/my_task_run
```

### Other input options

- **Descriptions are required.** `contract.check_request` refuses an object whose description is empty or only its
  category. The older category-only test sets (`test300`, `exp150`) are replayed with
  `WORKFLOW_ALLOW_BARE_DESCRIPTIONS=1`.
- **GPT sizes instead of FastFill's** (`run_draft.py --draft-sizes`): no FastFill step; the placement call gives every
  object's size with its pose and the later steps keep the chosen draft's sizes (the size ablation of `exp150detail`).

### Datasets and experiments

| Dataset (project root) | Experiment (`experiments/`) | What |
|---|---|---|
| `test150detail` | `exp150detail` | 150 rooms with detailed descriptions; FastFill sizes against GPT drafting its own sizes on 30 of them, the six v4detail models and the 8B on all 150 |
| `test30tasks` | `exp30tasks` | 30 high-quality rooms with hand-written tasks; the task mode against the workflow before it (and `task_mode_v2`, the current code, on 10 rooms); `compare_view*.html` shows them in 3D with required furniture in red |
| `test150tasks` | `exp150tasks` | the layout-stage experiment: 150 rooms, tasks from the simulated task agent (`task_agent.py`); runs in progress |
| `test150tiers` | `exp150tiers` | easy / medium / hard versions of rooms (an earlier direction, not used: difficulty is the upstream agent's) |

Dataset scripts: `room_quality.py` (quality checks), `select_task_rooms.py`, `task_agent.py`, `make_task_rooms.py`,
`make_tier_rooms.py`. Each dataset has its own `README.md` (in Chinese) on how it was built and how to rebuild it.

## Run

```bash
python experiments/run_draft.py --rows test300/rows.jsonl --sizes-file <FastFill predictions.jsonl> \
    --indices 15 22 29 --workers 4 --budget-usd 5 --evaluate --out experiments/simple_run
```

- **API settings:** taken from `fastfill_workflow2/.env`. If that file does not exist, the original workflow's `.env` is read in place (the local layout), otherwise `~/.fastfill_openai.env`. The key is never printed or copied.
- **LLM call logs:** `run_draft.py` writes every LLM call (instructions, prompt, raw answer, usage, cost, latency; never the key) to `<out>/llm_calls/room_<i>.jsonl` (`--no-llm-log` turns it off; `workflow/llm.py`, `WORKFLOW_LLM_LOG_DIR`).
- **Analysis scripts and outputs** from the robot / independent-evaluation work: `experiments/session_logs/README.md`.
- **Tests:** `python -m pytest -q tests` (115 tests)

## Robot checks (`workflow/robot.py`)

The program checker also asks whether a mobile robot of a given width can use the room (2D footprints only, about 2 ms per room):

- **`robot_door`:** every door is linked to the others through floor the robot can drive on.
- **`robot_reach`:** the robot can reach the furniture it has to work at:
  - furniture carrying another requested object;
  - openable furniture;
  - the task's objects (`Robot.reach_ids`).
- **`robot_openable`:** the sweep in front of a cabinet, wardrobe, fridge and so on is free, so its doors and drawers can open.
- **`robot_arm`:** an object standing on furniture is within the arm's 0.85 m (in plan) of a spot the robot can drive to. This follows EmbodiedGen's `check_reachable`.

The navigation check computes the same free space as EmbodiedGen's `RoamTrajectoryGenerator` (floor minus furniture, keeping a clearance), but exactly instead of on a 5 cm grid.

How to use them:

- **In the pipeline:** `--robot-width 0.5` (simple placement) makes these checks hard violations, and the result reports them for that robot (`diagnostics.robot`).
- **Scoring saved runs:** `experiments/robot_check.py` checks every saved run at widths 0.4, 0.5 and 0.6. Output: `experiments/robot_check/table.md`.

With `--robot-width`, the robot is also part of placement and repair:

- **Placement request** (`drafting.ROBOT_RULE`): the LLM is told the robot's width. Openable furniture carries `front_clearance_m`, and furniture that holds objects carries `robot_works_here`.
- **Repair search** (`robot.RobotZones`): the search ranks its candidates with the checks' cheap local form, added to `Geometry.soft_score`:
  - the zone in front of openable furniture;
  - a standing strip on one approach side of furniture that holds objects;
  - objects on that furniture within arm's reach of the strip.

  These zones play the role of the usage areas in Make it Home and Merrell et al. (2011), and of Infinigen's accessibility cost. Door linking is not modelled in the search; only the critic checks it.
- **Objects on furniture**: with a robot, the search also tries spots along each edge of the support's top (EmbodiedGen's surface sampling). The arm-reach zone then ranks these spots.
- **Commit rule** (`Critic.better`): decisions run in tiers. Legality comes first, then the robot checks, then the soft cost. A robot check therefore never blocks a legality repair. Robot violations are identified by their object, not by the list of blockers.

Two more options for simple placement:

- **`--drafts N`:** makes N placement calls in parallel and keeps the draft with the fewest hard violations of any kind (`draft_rank`). Ranking by legality first was wrong: the repair fixes small collisions easily but rarely fixes robot violations. This follows the generate-then-verify idea of WeakVerifiers. Every call is paid.
- **`--resize`:** when repair still leaves legality violations, a second pass may shrink objects by up to 20%, ignoring the catalog's floor (for example a king bed in a room too narrow for it). This follows EmbodiedSmith's "resize support" edit. Resized objects are listed in `diagnostics.resized`.

Footprints, wall contacts and robot-zone coverage are cached by pose. This made the repair of the largest room (66) about 5 times faster.

## Export to RoomGenBench (layout → 3D room)

`experiments/export_roomgenbench.py --run <run folder> --preview` writes a run's layouts as RoomGenBench inputs:

- `<run>/roomgenbench/inputs/scenes/room_<i>.json`: room shell, doors and every object's box, in SAGE's convention (front +Y, width along local X, bottom-centre position, yaw in degrees). It includes the room's fixed objects; `--no-fixed` leaves them out.
- `<run>/roomgenbench/inputs/assets.jsonl`: one row per type + description, as RoomGenBench deduplicates.

Copy them into RoomGenBench's `bench/inputs/`, generate the assets with a method, then run `bench/assemble.py --method <m> --scenes room_015,...`. `--preview` runs RoomGenBench's own assembler in box-only mode. On the 20 rooms of `simple20_robot2`, every box matched the layout exactly.

## Evaluation scripts (local layout)

- `experiments/optiscene_eval.py` re-implements two published evaluations:
  - OptiScene: OOR, FID/KID, and the GPT-4o prompt from their supplementary Table 3;
  - I-Design: the GPT-V evaluator prompt.
- `experiments/big_table.py` puts every saved run on the same metrics.

Both scripts read earlier runs from the original workflow folder (`../Fastfill workflow/experiments`).
