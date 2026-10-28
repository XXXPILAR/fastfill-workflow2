# Program checker: legality, constraints, robot checks

Every saved run through the program checker, for robots of several widths (no rendering, no LLM).

Per method, pooled over the rooms it returned a layout for:
  rooms ok %         every check below passes (legality + constraints + the robot's checks at that width)
  legal %            no collision (lq.col), nothing out of bounds (> 1 % of a footprint), no blocked door (lq.opc)
  constraints %      the input's constraints that hold (Geometry.relation_issue; ``on`` reads the layout's supports
                     as given, else as inferred from the boxes: robot.infer_parents); a missing object fails its own
  doors linked %     rooms with doors whose doors are all linked for the robot (robot_door)
  required reached % furniture the robot works at (supports of other objects, openable furniture) it reaches
  openable free %    openable furniture whose doors / drawers can open (robot_openable; width-independent)
  items in reach %   objects on furniture within the arm's 0.85 m of where the robot can stand (robot_arm)
  furniture reached % every floor obstacle >= 0.3 m tall it reaches (as REACH0.5, but for the robot: nothing lets
                     it pass between a sofa and a table)
The ground truth is checked too: these are datasets' human rooms, not robot-checked ones.

## test300

| method | rooms | legal % | constraints % | rooms ok % @0.4 | doors linked % @0.4 | required reached % @0.4 | items in reach % @0.4 | furniture reached % @0.4 | rooms ok % @0.5 | doors linked % @0.5 | required reached % @0.5 | items in reach % @0.5 | furniture reached % @0.5 | rooms ok % @0.6 | doors linked % @0.6 | required reached % @0.6 | items in reach % @0.6 | furniture reached % @0.6 | openable free % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ground truth | 300/300 | 46.3 | 99.7 | 29.0 | 94.9 | 87.3 | 80.0 | 82.4 | 27.0 | 91.9 | 82.4 | 75.1 | 78.1 | 26.0 | 89.4 | 74.1 | 65.1 | 70.9 | 70.2 |
| FastFill base (spread) | 297/300 | 19.9 | 42.3 | 6.7 | 73.7 | 75.0 | 83.1 | 75.6 | 6.7 | 66.4 | 68.2 | 75.8 | 69.5 | 6.4 | 60.8 | 62.6 | 64.1 | 63.3 | 61.0 |
| FastFill D (spread) | 297/300 | 19.2 | 42.3 | 5.4 | 77.2 | 73.9 | 85.5 | 75.0 | 5.4 | 68.1 | 66.9 | 72.0 | 68.2 | 5.4 | 59.5 | 62.5 | 66.0 | 63.7 | 59.5 |
| FastFill E (spread) | 297/300 | 16.8 | 38.5 | 5.1 | 77.2 | 72.3 | 91.5 | 71.2 | 5.1 | 68.1 | 68.9 | 87.6 | 66.8 | 5.1 | 61.6 | 63.5 | 76.6 | 61.4 | 57.0 |
| GPT-5.6 one-shot | 284/300 | 91.5 | 98.2 | 69.4 | 97.7 | 92.8 | 86.5 | 90.5 | 65.1 | 96.4 | 90.1 | 85.3 | 86.6 | 60.6 | 95.0 | 84.1 | 79.9 | 81.2 | 91.4 |
| LayoutGPT | 300/300 | 18.3 | 61.1 | 13.0 | 91.1 | 65.2 | 80.8 | 68.8 | 12.7 | 86.4 | 57.1 | 73.0 | 60.5 | 11.7 | 82.1 | 50.2 | 64.5 | 53.8 | 37.0 |
| Holodeck | 300/300 | 62.3 | 64.2 | 26.3 | 91.1 | 90.5 | 88.1 | 90.0 | 25.3 | 88.9 | 86.4 | 83.1 | 86.1 | 24.7 | 87.2 | 82.5 | 73.6 | 81.9 | 82.3 |
| LayoutVLM | 300/300 | 62.7 | 90.0 | 37.3 | 89.4 | 82.4 | 82.5 | 74.7 | 35.3 | 88.5 | 75.4 | 68.5 | 66.2 | 34.0 | 87.7 | 69.4 | 60.6 | 61.3 | 81.7 |
| workflow v4 (draft + local repair) | 50/300 | 62.0 | 97.1 | 34.0 | 86.4 | 80.8 | 83.4 | 76.7 | 26.0 | 84.1 | 75.5 | 76.6 | 72.4 | 26.0 | 79.5 | 68.8 | 70.8 | 64.3 | 76.1 |
| ours A: all at once + critic loop | 45/300 | 86.7 | 96.7 | 37.8 | 92.3 | 82.8 | 86.5 | 78.9 | 33.3 | 92.3 | 76.6 | 80.3 | 71.9 | 26.7 | 89.7 | 67.2 | 70.9 | 63.8 | 73.6 |
| ours C: by group | 44/300 | 95.5 | 98.9 | 50.0 | 92.1 | 85.3 | 87.4 | 77.9 | 47.7 | 89.5 | 80.1 | 82.9 | 73.7 | 34.1 | 86.8 | 74.3 | 68.9 | 69.3 | 81.1 |
| ours C_final: by group + whole-room loop | 44/300 | 95.5 | 100.0 | 47.7 | 92.1 | 87.4 | 88.4 | 80.3 | 47.7 | 89.5 | 80.6 | 83.2 | 74.9 | 31.8 | 86.8 | 75.4 | 68.8 | 69.9 | 84.0 |
| ours staged (old time budget) | 20/300 | 100.0 | 100.0 | 40.0 | 100.0 | 78.9 | 88.4 | 73.7 | 35.0 | 94.7 | 71.6 | 80.6 | 67.4 | 35.0 | 94.7 | 69.7 | 76.7 | 66.1 | 78.3 |
| workflow2 simple (one place, one check, one review) | 17/300 | 100.0 | 100.0 | 52.9 | 100.0 | 80.0 | 80.0 | 79.8 | 47.1 | 93.8 | 76.2 | 80.0 | 74.6 | 47.1 | 93.8 | 72.5 | 74.7 | 69.9 | 72.9 |
| workflow2 simple + robot 0.5 m (prompt, search zones, tiered critic) | 20/300 | 95.0 | 100.0 | 75.0 | 100.0 | 97.1 | 99.2 | 90.1 | 70.0 | 100.0 | 95.2 | 95.3 | 87.6 | 50.0 | 94.7 | 79.0 | 86.0 | 74.4 | 100.0 |
| workflow2 simple + robot 0.5 m + 2 drafts + resize | 20/300 | 90.0 | 100.0 | 75.0 | 100.0 | 93.4 | 98.5 | 89.0 | 70.0 | 100.0 | 77.4 | 78.0 | 74.6 | 45.0 | 100.0 | 68.9 | 71.2 | 65.3 | 100.0 |

## workflow2's 17 rooms

| method | rooms | legal % | constraints % | rooms ok % @0.4 | doors linked % @0.4 | required reached % @0.4 | items in reach % @0.4 | furniture reached % @0.4 | rooms ok % @0.5 | doors linked % @0.5 | required reached % @0.5 | items in reach % @0.5 | furniture reached % @0.5 | rooms ok % @0.6 | doors linked % @0.6 | required reached % @0.6 | items in reach % @0.6 | furniture reached % @0.6 | openable free % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ground truth | 17/17 | 41.2 | 96.7 | 17.6 | 100.0 | 87.5 | 94.2 | 82.0 | 17.6 | 100.0 | 78.1 | 92.3 | 77.0 | 17.6 | 93.8 | 57.8 | 71.2 | 59.6 | 62.2 |
| FastFill base (spread) | 17/17 | 17.6 | 33.3 | 5.9 | 87.5 | 62.5 | 61.4 | 72.0 | 5.9 | 81.2 | 52.8 | 56.8 | 64.6 | 0.0 | 81.2 | 48.6 | 52.3 | 58.3 | 60.4 |
| FastFill D (spread) | 17/17 | 11.8 | 43.3 | 5.9 | 87.5 | 66.7 | 78.9 | 72.9 | 5.9 | 87.5 | 62.1 | 65.8 | 64.4 | 5.9 | 81.2 | 56.1 | 60.5 | 58.8 | 58.3 |
| FastFill E (spread) | 17/17 | 5.9 | 33.3 | 0.0 | 93.8 | 69.1 | 88.9 | 73.9 | 0.0 | 81.2 | 60.0 | 88.9 | 62.2 | 0.0 | 81.2 | 56.4 | 77.8 | 59.6 | 52.1 |
| GPT-5.6 one-shot | 17/17 | 82.4 | 96.7 | 47.1 | 100.0 | 86.8 | 90.4 | 89.7 | 47.1 | 100.0 | 81.6 | 83.6 | 86.1 | 35.3 | 100.0 | 72.4 | 68.5 | 78.8 | 85.4 |
| LayoutGPT | 17/17 | 23.5 | 60.0 | 0.0 | 93.8 | 65.2 | 95.5 | 74.2 | 0.0 | 87.5 | 56.5 | 90.9 | 68.0 | 0.0 | 87.5 | 47.8 | 90.9 | 62.9 | 17.0 |
| Holodeck | 17/17 | 52.9 | 43.3 | 5.9 | 93.8 | 98.6 | 92.9 | 96.1 | 5.9 | 93.8 | 91.5 | 82.9 | 90.9 | 5.9 | 93.8 | 90.1 | 80.0 | 89.0 | 88.6 |
| LayoutVLM | 17/17 | 58.8 | 86.7 | 29.4 | 93.8 | 85.7 | 85.9 | 87.2 | 23.5 | 93.8 | 82.9 | 80.3 | 85.1 | 23.5 | 93.8 | 68.6 | 73.2 | 77.1 | 79.2 |
| workflow v4 (draft + local repair) | 17/17 | 82.4 | 100.0 | 41.2 | 100.0 | 78.8 | 75.4 | 79.3 | 29.4 | 100.0 | 75.0 | 66.7 | 76.4 | 29.4 | 93.8 | 66.2 | 53.6 | 66.1 | 77.1 |
| ours A: all at once + critic loop | 17/17 | 94.1 | 100.0 | 47.1 | 93.8 | 78.7 | 90.5 | 80.7 | 35.3 | 93.8 | 74.7 | 82.5 | 74.3 | 29.4 | 93.8 | 64.0 | 74.6 | 64.9 | 75.0 |
| ours C: by group | 16/17 | 100.0 | 100.0 | 56.2 | 100.0 | 75.3 | 80.3 | 75.6 | 56.2 | 100.0 | 72.6 | 78.7 | 73.1 | 43.8 | 93.3 | 71.2 | 70.5 | 72.5 | 72.9 |
| ours C_final: by group + whole-room loop | 16/17 | 100.0 | 100.0 | 56.2 | 100.0 | 80.8 | 86.9 | 83.1 | 56.2 | 100.0 | 76.7 | 85.2 | 77.5 | 43.8 | 93.3 | 74.0 | 75.4 | 75.6 | 79.2 |
| ours staged (old time budget) | 17/17 | 100.0 | 100.0 | 41.2 | 100.0 | 78.0 | 89.3 | 72.9 | 35.3 | 93.8 | 72.0 | 85.3 | 67.1 | 35.3 | 93.8 | 69.5 | 80.0 | 65.3 | 75.0 |
| workflow2 simple (one place, one check, one review) | 17/17 | 100.0 | 100.0 | 52.9 | 100.0 | 80.0 | 80.0 | 79.8 | 47.1 | 93.8 | 76.2 | 80.0 | 74.6 | 47.1 | 93.8 | 72.5 | 74.7 | 69.9 | 72.9 |
| workflow2 simple + robot 0.5 m (prompt, search zones, tiered critic) | 17/17 | 94.1 | 100.0 | 82.4 | 100.0 | 97.4 | 100.0 | 93.8 | 76.5 | 100.0 | 94.9 | 93.9 | 90.3 | 52.9 | 93.8 | 75.6 | 78.8 | 73.3 | 100.0 |
| workflow2 simple + robot 0.5 m + 2 drafts + resize | 17/17 | 100.0 | 100.0 | 82.4 | 100.0 | 91.1 | 97.1 | 85.7 | 82.4 | 100.0 | 82.3 | 82.6 | 80.0 | 52.9 | 100.0 | 72.2 | 73.9 | 68.0 | 100.0 |
