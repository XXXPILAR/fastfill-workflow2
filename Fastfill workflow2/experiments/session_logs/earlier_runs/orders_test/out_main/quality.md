# Placement order: A all at once / B one by one / C group by group (+ _final: whole-room repair after)

Rooms done in every variant: 2. End-to-end adds the shared plan (cost, seconds) and the room's size-prediction seconds to each variant. B_final / C_final reuse B's / C's placement calls; their LLM calls and USD include them.

| variant | rooms | hard-valid | hard violations left | soft cost left | steps / room (median, max) | single-step rooms | LLM calls / room | USD / room (incremental) | USD / room (end-to-end) | s / room median (incremental) | s / room median (end-to-end) | s / room max (end-to-end) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 2 | 1 | 23 | 0.06 | 1.0, 1 | 2 | 2.0 | 0.002 | 0.003 | 11.3 | 11.3 | 19.92 |
| B | 2 | 1 | 16 | 1.404 | 11.5, 16 | 0 | 12.5 | 0.013 | 0.013 | 1.0 | 1.0 | 1.62 |
| B_final | 2 | 1 | 16 | 1.404 | 11.5, 16 | 0 | 14.0 | 0.014 | 0.015 | 6.5 | 6.5 | 12.21 |
| C | 2 | 1 | 9 | 0.635 | 1.5, 2 | 1 | 2.5 | 0.003 | 0.004 | 7.0 | 7.0 | 11.31 |
| C_final | 2 | 1 | 9 | 0.635 | 1.5, 2 | 1 | 3.5 | 0.004 | 0.004 | 10.5 | 10.5 | 18.25 |

### all rooms (2 rooms)

| variant | hard-valid | NAV ↑ | ACC ↑ | REL ↑ | SG ↑ | COL ↓ | OPC ↓ |
|---|---|---|---|---|---|---|---|
| ground truth | – | 99.8 | 95.2 | 100.0 | 100.0 | 30.4 | 18.2 |
| A | 1 | 100.0 | 90.5 | 100.0 | 32.1 | 43.5 | 9.1 |
| B | 1 | 100.0 | 66.7 | 50.0 | 39.5 | 30.4 | 9.1 |
| B_final | 1 | 100.0 | 66.7 | 50.0 | 39.5 | 30.4 | 9.1 |
| C | 1 | 100.0 | 90.5 | 100.0 | 24.7 | 13.0 | 9.1 |
| C_final | 1 | 100.0 | 90.5 | 100.0 | 24.7 | 13.0 | 9.1 |

### 1-20 objects (2 rooms)

| variant | hard-valid | NAV ↑ | ACC ↑ | REL ↑ | SG ↑ | COL ↓ | OPC ↓ |
|---|---|---|---|---|---|---|---|
| ground truth | – | 99.8 | 95.2 | 100.0 | 100.0 | 30.4 | 18.2 |
| A | 1 | 100.0 | 90.5 | 100.0 | 32.1 | 43.5 | 9.1 |
| B | 1 | 100.0 | 66.7 | 50.0 | 39.5 | 30.4 | 9.1 |
| B_final | 1 | 100.0 | 66.7 | 50.0 | 39.5 | 30.4 | 9.1 |
| C | 1 | 100.0 | 90.5 | 100.0 | 24.7 | 13.0 | 9.1 |
| C_final | 1 | 100.0 | 90.5 | 100.0 | 24.7 | 13.0 | 9.1 |

REL templates: /Users/zhangyang/Downloads/fastfill-v4/Fastfill workflow/experiments/quality50/eval_templates_odd.json
