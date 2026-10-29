# FastFill alone vs GPT alone on exp150 (149 rooms both answered)

Where FastFill alone falls behind GPT alone on exp150 (and where it does not): both scored on the 149 rooms where both
returned a layout (room 162 is over FastFill's object budget), the ground truth alongside as the reference.

  out of bounds      objects with more than 1 % of their footprint outside the floor
  colliding          objects in a collision (lq.col); door blocked: door zones covered by floor furniture (lq.opc)
  constraints        by type, as robot_check.legality counts them
  facing             floor furniture >= 0.3 m tall with its back or its front edge at a wall (within 0.15 m): right
                     when the back is the edge at the wall and the front points into the room (within 45 deg of the
                     wall's inward normal), wrong when it faces the wall; front-aware, unlike the symmetric yaw
                     error FastFill is trained and scored with
  size error         mean |log(predicted / ground-truth)| over the three box dimensions, per object
  position error     distance of each object's centre to its ground-truth centre (the ground truth is one human
                     layout of many possible: a hint, not a score)
  floating / sunk    objects off the floor that stand on nothing and hang on no wall (bottom more than 5 cm above
                     the floor, no supporting box under them, more than 0.3 m from every wall) / boxes that start
                     inside the box they should stand on
  by room size       legal rooms for small (<= 10 objects), medium (11-30), large (> 30) rooms

| | ground truth | GPT alone | FastFill alone |
|---|---|---|---|
| legal rooms % | 48.3 | 89.9 | 18.8 |
| objects out of bounds % | 3.6 | 1.8 | 15.6 |
| rooms with an object out of bounds % | 23.5 | 6.0 | 48.3 |
| objects colliding % | 8.2 | 0.5 | 7.0 |
| rooms with a collision % | 32.2 | 3.4 | 32.9 |
| doors blocked % | 16.9 | 1.6 | 55.1 |
| constraint against_wall met % (n=103) | 100.0 | 99.0 | 62.1 |
| constraint between met % (n=59) | 100.0 | 96.6 | 18.6 |
| constraint faces met % (n=65) | 100.0 | 96.9 | 21.5 |
| constraint near met % (n=41) | 97.6 | 97.6 | 26.8 |
| constraint on met % (n=23) | 100.0 | 100.0 | 100.0 |
| at a wall: back to the wall, front into the room % | 96.0 | 98.8 | 89.5 |
| furniture at a wall (count) | 701 | 588 | 494 |
| size error |log| (mean) | 0.000 | 0.410 | 0.349 |
| size error |log| (median) | 0.000 | 0.294 | 0.254 |
| centre distance to ground truth m (median) | 0.00 | 2.88 | 3.07 |
| objects floating in the air % | 2.9 | 0.0 | 5.0 |
| objects sunk into their support % | 0.0 | 0.0 | 0.0 |
| legal rooms %, small <= 10 objects | 46.2 | 96.7 | 24.2 |
| objects out of bounds %, small <= 10 | 14.1 | 0.0 | 19.8 |
| legal rooms %, medium 11-30 objects | 42.9 | 85.7 | 14.3 |
| objects out of bounds %, medium 11-30 | 3.6 | 1.9 | 19.1 |
| legal rooms %, large > 30 objects | 65.2 | 69.6 | 4.3 |
| objects out of bounds %, large > 30 | 0.1 | 2.3 | 12.3 |
