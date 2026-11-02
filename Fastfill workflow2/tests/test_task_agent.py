from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))
import select_task_rooms as sel  # noqa: E402
import task_agent as ta  # noqa: E402
from test_tier_rooms import row  # noqa: E402  (bed, desk, mirror, lamp/tray/box on the desk, cup on the tray, vase on the box)


class TaskAgentAnswerTests(unittest.TestCase):
    def test_valid_tasks_are_kept_and_wrong_ones_named(self):
        answer = {"tasks": [
            {"text": "Bring the white cup to the bed.", "uses": ["cup", "tray", "bed"], "articulation": []},
            {"text": "Open the box.", "uses": ["box"], "articulation": ["box"]},
            {"text": "Use the sofa.", "uses": ["sofa"], "articulation": []},                 # not in the room
            {"text": "Open the desk.", "uses": ["lamp"], "articulation": ["desk"]},          # opened but not used
            {"text": "Bring the cup again.", "uses": ["bed", "cup", "tray"], "articulation": []}]}  # a repeat
        tasks, wrong = ta.problems(answer, row())
        self.assertEqual([t["text"] for t in tasks], ["Bring the white cup to the bed.", "Open the box."])
        self.assertEqual(len(wrong), 3)
        self.assertTrue(any("sofa" in w for w in wrong) and any("articulation" in w for w in wrong)
                        and any("same objects" in w for w in wrong))

    def test_fewer_than_two_tasks_asks_again(self):
        tasks, wrong = ta.problems({"tasks": [{"text": "Open the box.", "uses": ["box"], "articulation": ["box"]}]}, row())
        self.assertEqual(len(tasks), 1)
        self.assertTrue(any("write 2 or 3" in w for w in wrong))

    def test_the_request_holds_what_the_upstream_agent_sees(self):
        request = json.loads(ta.request_text(row()))
        self.assertEqual(set(request["room"]), {"type", "size_m"})
        self.assertEqual({o["id"]: o["on"] for o in request["objects"]}["cup"], "tray")
        self.assertFalse(any("target" in k or "size" in k for o in request["objects"] for k in o))


class SelectionTests(unittest.TestCase):
    def test_small_sources_all_kept_rooms_and_a_seeded_draw(self):
        rooms = [{"room": i, "source": "SAGE-10k" if i >= 3 else "IL3D_3dfront", "type": "x", "objects": 10, "doors": 1,
                  "passes": i != 5} for i in range(10)]
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "rows.jsonl").write_text("".join(json.dumps({"i": i}) + "\n" for i in range(10)))
            (d / "q.json").write_text(json.dumps({"min_doors": 0, "min_objects": 6, "rooms": rooms}))
            (d / "keep.jsonl").write_text(json.dumps({"task": {"base_index": 1}}) + "\n")
            (d / "m.json").write_text(json.dumps({"test_line_indices": [0, 7]}))
            sel.main(["--rows", str(d / "rows.jsonl"), "--quality", str(d / "q.json"), "--keep", str(d / "keep.jsonl"),
                      "--keep-manifest", str(d / "m.json"), "--rooms", "6", "--output", str(d / "out")])
            s = json.loads((d / "out" / "selection.json").read_text())
            self.assertEqual(len(s["line_indices"]), 6)
            self.assertTrue({0, 1, 2, 7} <= set(s["line_indices"]) and 5 not in s["line_indices"])
            self.assertEqual([json.loads(l)["i"] for l in (d / "out" / "base_rows.jsonl").read_text().splitlines()],
                             s["line_indices"])


if __name__ == "__main__":
    unittest.main()
