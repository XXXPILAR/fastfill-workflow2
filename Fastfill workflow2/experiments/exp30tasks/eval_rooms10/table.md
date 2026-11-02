# exp30tasks: the task mode against the workflow before it

Rooms (rows of test30tasks): [0, 1, 6, 10, 12, 13, 19, 22, 24, 26]

exp30tasks evaluation (no LLM, no money): the task mode against the workflow before it on the 30 rooms of
test30tasks (required and expansion furniture from each room's tasks), beside the ground truth and FastFill alone.

Checks are the independent ones exp150 uses, not the workflow's own critic: collisions (fastfill.validate on box
meshes, the objects in one), out of bounds (more than 1 % of the footprint outside the floor), door zones blocked
(layout_quality's door zones), constraints (Geometry.relation_issue), and the robot checker for a 0.5 m robot with
the task's objects (robot.RobotChecker with simple.task_robot: every work furniture reachable and openable furniture
free to open, plus the required objects reached and the articulation objects free to open); supports are inferred
from the boxes (robot.infer_parents), as for any method. SceneEval, EmbodiedGen and the rectangular base as in exp150.
A layout is scored on the objects it holds (the task mode may remove expansion objects); removed objects count as not
kept, never as a failure of a required object, and a missing required object counts as one.

Per required object: kept, legal (in no collision, inside, not blocking a door), reached (the robot reaches it: the
furniture it stands on for an object on furniture; within arm's reach for an object on furniture; free to open when
the task opens it). A task is doable when every object it uses is kept, legal and reached, and the doors are linked.

Column headers give the rooms scored; a method's missing rooms count as failed rooms.

| metric | ground truth (10) | FastFill alone (1.7B full) (10) | workflow before (old_mode) (10) | task mode (task_mode) (10) | task mode v2: required first + fallback (task_mode_v2) (10) |
|---|---|---|---|---|---|
| required objects kept % | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| required objects legal % | 100.0 | 76.7 | 98.3 | 100.0 | 100.0 |
| required objects reached by the robot % | 61.7 | 63.3 | 86.7 | 90.0 | 100.0 |
| required objects kept + legal + reached % | 61.7 | 50.0 | 86.7 | 90.0 | 100.0 |
| rooms with every required object good % | 0.0 | 0.0 | 60.0 | 70.0 | 100.0 |
| required relations met % | 100.0 | 63.6 | 100.0 | 100.0 | 100.0 |
| tasks doable (every object used good, doors linked) % | 37.0 | 11.1 | 81.5 | 85.2 | 100.0 |
| expansion objects kept % | 100.0 | 100.0 | 100.0 | 98.3 | 98.3 |
| expansion objects kept + legal % | 100.0 | 91.7 | 98.5 | 98.3 | 98.3 |
| rooms legal (every object kept) % | 100.0 | 0.0 | 80.0 | 100.0 | 100.0 |
| rooms with doors linked % | 100.0 | 50.0 | 100.0 | 100.0 | 100.0 |
| work furniture reached % | 56.9 | 57.1 | 93.1 | 87.9 | 100.0 |
| openable furniture free to open % | 64.3 | 64.3 | 92.9 | 100.0 | 100.0 |
| items within arm's reach % | 64.5 | 74.7 | 93.8 | 99.4 | 100.0 |
| rooms robot ok (task robot) % | 0.0 | 10.0 | 60.0 | 50.0 | 100.0 |
| SceneEval objects colliding % | 35.8 | 51.7 | 9.3 | 8.2 | 7.1 |
| SceneEval out of bounds % | 0.4 | 1.9 | 7.6 | 4.9 | 4.9 |
| rect base: rooms all reached % | 10.0 | 0.0 | 70.0 | 60.0 | 70.0 |
| rooms where required first (④c) was used | – | – | 0 | 0 | 1 |
| rooms delivered as the required-only fallback | – | – | 0 | 0 | 1 |
| s / room (median) | – | 0.3 | 138.4 | 159.2 | 310.7 |
| $ / room (est.) | – | 0.000 | 0.250 | 0.243 | 0.250 |

## Expansion objects removed by task mode v2: required first + fallback (task_mode_v2)

- room row 1 (48): obj_0001 drawer chest: fallback: only the required objects are placed
- room row 10 (125): obj_0000 chair: robot_reach ['obj_0019', 'obj_0000'] (task object, blocked by obj_0000)
- room row 12 (127): obj_0049 bench with ['obj_0021']: robot_reach ['obj_0000', 'obj_0007', 'obj_0049'] (task object, blocked by obj_0007, obj_0049)
- room row 13 (128): obj_0035 charger: collision ['obj_0008', 'obj_0035']
