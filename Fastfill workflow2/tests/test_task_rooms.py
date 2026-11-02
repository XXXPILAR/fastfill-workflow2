from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))
import make_task_rooms as mtr  # noqa: E402
from test_tier_rooms import row  # noqa: E402  (bed, desk, mirror, lamp/tray/box on the desk, cup on the tray, vase on the box)


class TaskRoomsTests(unittest.TestCase):
    def test_required_are_the_used_objects_and_what_they_stand_on(self):
        spec = {"tasks": [{"text": "Bring the cup to the bed.", "uses": ["cup", "bed"], "articulation": []},
                          {"text": "Open the box.", "uses": ["box"], "articulation": ["box"]}]}
        t = mtr.task_row(row(), spec, 7, "test")["task"]
        self.assertEqual(t["required_ids"], ["bed", "desk", "tray", "cup", "box"])  # request order
        self.assertEqual(t["supports_added"], ["desk", "tray"])
        self.assertEqual(t["expansion_ids"], ["mirror", "lamp", "vase"])
        self.assertEqual(t["articulation_ids"], ["box"])
        # near cup->tray: all required; on lamp->desk and between desk/bed/vase touch expansion objects
        self.assertEqual((t["required_constraints"], t["expansion_constraints"]), ([0, 3], [1, 2]))

    def test_the_condition_is_unchanged_and_wrong_ids_are_refused(self):
        r = row()
        out = mtr.task_row(r, {"tasks": [{"text": "x", "uses": ["bed"], "articulation": []}]}, 0, "test")
        self.assertEqual(out["condition"], r["condition"])
        with self.assertRaisesRegex(ValueError, "unknown ids"):
            mtr.task_row(r, {"tasks": [{"text": "x", "uses": ["sofa"], "articulation": []}]}, 0, "test")
        with self.assertRaisesRegex(ValueError, "articulation ids not used"):
            mtr.task_row(r, {"tasks": [{"text": "x", "uses": ["bed"], "articulation": ["desk"]}]}, 0, "test")


if __name__ == "__main__":
    unittest.main()
