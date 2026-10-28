# Check-and-repair order: whole room / object by object / layer by layer

Drafts: experiments/test50_v4_server; 3 rooms; program proposals only (no GPT), sizes fixed, 180 s search budget per room and variant, critic-judged polish at the end. REL with the evaluation templates experiments/quality50/eval_templates_odd.json.

### all rooms (3 rooms)

| variant | hard-valid (doors hard) | hard-valid (old rule) | hard violations left | REL ↑ | ACC ↑ | OPC ↓ | COL ↓ | soft cost | s/room median | s/room max |
|---|---|---|---|---|---|---|---|---|---|---|
| A whole room | 2/3 | 2/3 | 44 | 100.0 | 95.2 | 0.0 | 0.0 | 0.59 | 3.0 | 33.3 |
| B object by object | 1/3 | 1/3 | 57 | 71.4 | 85.7 | 0.0 | 10.1 | 1.01 | 0.4 | 2.6 |
| C layer by layer | 2/3 | 2/3 | 49 | 100.0 | 95.2 | 0.0 | 2.5 | 0.59 | 2.9 | 6.0 |
| draft (step ③) | 0/3 | – | 64 | | | | | 1.42 | | |

### 1-20 objects (2 rooms)

| variant | hard-valid (doors hard) | hard-valid (old rule) | hard violations left | REL ↑ | ACC ↑ | OPC ↓ | COL ↓ | soft cost | s/room median | s/room max |
|---|---|---|---|---|---|---|---|---|---|---|
| A whole room | 2/2 | 2/2 | 0 | 100.0 | 90.9 | 0.0 | 0.0 | 0.59 | 2.3 | 3.0 |
| B object by object | 1/2 | 1/2 | 2 | 71.4 | 72.7 | 0.0 | 18.2 | 1.01 | 0.3 | 0.4 |
| C layer by layer | 2/2 | 2/2 | 0 | 100.0 | 90.9 | 0.0 | 0.0 | 0.59 | 2.1 | 2.9 |
| draft (step ③) | 0/2 | – | 4 | | | | | 1.42 | | |

### 21+ objects (1 rooms)

| variant | hard-valid (doors hard) | hard-valid (old rule) | hard violations left | REL ↑ | ACC ↑ | OPC ↓ | COL ↓ | soft cost | s/room median | s/room max |
|---|---|---|---|---|---|---|---|---|---|---|
| A whole room | 0/1 | 0/1 | 44 | – | 100.0 | 0.0 | 0.0 | 0.00 | 33.3 | 33.3 |
| B object by object | 0/1 | 0/1 | 55 | – | 100.0 | 0.0 | 8.8 | 0.00 | 2.6 | 2.6 |
| C layer by layer | 0/1 | 0/1 | 49 | – | 100.0 | 0.0 | 2.9 | 0.00 | 6.0 | 6.0 |
| draft (step ③) | 0/1 | – | 60 | | | | | 0.00 | | |
