# exp150: 150 rooms, every method on gpt-6.1-sol medium

Evaluation of exp150 (no LLM, no money): every method on the same 150 rooms, gpt-6.1-sol medium for all LLM calls.

Per room and method (a missing layout counts as a failed room in every room-level rate):
  objects placed %   objects of the input that the layout contains
  legal %            no collision, nothing out of bounds, no blocked door (robot_check.legality)
  constraints %      the input's constraints that hold
  ours: robot 0.5 m  RobotChecker (our program checker, the one g1 repairs against: not independent evidence)
  SceneEval          its own metric code on box meshes: navigability (0.5 m), collision, out of bounds
  EmbodiedGen        RoamTrajectoryGenerator, clearance 0.25 m: largest free component's share, roam generated
  rect base          a 0.5 x 0.7 m base that must turn, 3D arm (independent code, never optimised against)
Time: wall seconds per room as run (all groups ran at once on one 30 RPM relay, so it includes waiting for the shared
limit and the relay's retries); our groups add FastFill's own GPU seconds for the sizes (fastfill_server/timing).
Cost: tokens at gpt-5.6-sol prices (gpt-6.1-sol's relay price is not known: an estimate, the same for every method).

| metric | ground truth | FastFill alone | GPT alone | LayoutGPT | Holodeck | LayoutVLM | ours: GPT + robot prompt, no repair (g2) | ours without robot (g3) | ours (g1) |
|---|---|---|---|---|---|---|---|---|---|
| layouts | 150 | 149 | 150 | 150 | 150 | 149 | 150 | 150 | 150 |
| objects placed % | 100.0 | 92.7 | 100.0 | 100.0 | 100.0 | 92.7 | 100.0 | 100.0 | 100.0 |
| legal rooms % | 48.7 | 18.7 | 90.0 | 36.7 | 64.0 | 68.0 | 74.7 | 96.7 | 96.7 |
| constraints % | 99.7 | 42.3 | 98.0 | 79.5 | 58.0 | 92.4 | 96.9 | 99.7 | 98.6 |
| complete+legal+constraints rooms % | 48.0 | 8.7 | 88.0 | 32.0 | 30.0 | 61.3 | 72.7 | 96.7 | 94.7 |
| …and robot ok (ours 0.5 m) % | 26.7 | 7.3 | 70.7 | 25.3 | 22.7 | 46.7 | 60.7 | 54.0 | 84.7 |
| doors linked % | 92.6 | 65.8 | 96.7 | 90.1 | 90.9 | 89.2 | 92.6 | 89.3 | 93.4 |
| work furniture reached % | 86.2 | 65.7 | 89.7 | 74.4 | 80.3 | 83.8 | 88.8 | 79.0 | 94.7 |
| items in arm reach % | 86.9 | 76.0 | 77.7 | 78.9 | 79.1 | 75.0 | 88.4 | 77.4 | 98.0 |
| doors/drawers open % | 70.8 | 61.7 | 93.9 | 55.8 | 77.8 | 84.2 | 96.4 | 81.8 | 97.1 |
| SceneEval nav 0.5 m % | 92.1 | 89.1 | 95.8 | 89.3 | 91.5 | 92.5 | 91.7 | 89.3 | 94.4 |
| SceneEval objects colliding % | 31.4 | 26.8 | 1.3 | 23.4 | 37.3 | 17.5 | 4.8 | 1.5 | 1.7 |
| SceneEval out of bounds % | 15.6 | 16.3 | 5.2 | 18.7 | 1.4 | 42.9 | 17.9 | 7.2 | 7.7 |
| EmbodiedGen largest free % | 94.7 | 93.7 | 98.4 | 93.3 | 95.5 | 93.8 | 95.6 | 93.2 | 95.3 |
| EmbodiedGen roam ok rooms % | 98.7 | 99.3 | 100.0 | 100.0 | 100.0 | 99.3 | 100.0 | 100.0 | 100.0 |
| rect base: furniture parked % | 80.2 | 61.8 | 90.4 | 76.0 | 77.4 | 81.9 | 87.5 | 76.4 | 92.5 |
| rect base: items in 3D reach % | 79.4 | 72.0 | 78.0 | 83.9 | 71.1 | 71.0 | 87.0 | 72.1 | 94.3 |
| rect base: rooms all reached % | 53.3 | 38.7 | 70.7 | 52.7 | 58.0 | 60.7 | 70.0 | 56.0 | 76.7 |
| s / room (median) | – | 0 | 44 | 28 | 41 | 70 | 78 | 109 | 139 |
| s / room (p90) | – | 0 | 127 | 72 | 108 | 192 | 213 | 269 | 359 |
| LLM calls / room | – | 0.0 | 1.0 | 1.0 | 2.4 | 2.0 | 2.2 | 4.6 | 4.7 |
| $ / room (est.) | – | 0.000 | 0.036 | 0.045 | 0.027 | 0.068 | 0.055 | 0.097 | 0.116 |
