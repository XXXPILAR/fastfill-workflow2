from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))
import make_tier_rooms as mt  # noqa: E402

# id, support, largest size (m), description: layer 1 furniture, 2 medium on furniture, 3 clutter
OBJECTS = [("bed", "floor", 2.1, "a queen bed with upholstered headboard"),
           ("desk", "floor", 1.2, "wood writing desk"),
           ("mirror", "wall", .8, "round wall mirror"),
           ("lamp", "desk", .45, "small table lamp with a linen shade"),
           ("tray", "desk", .35, "wooden serving tray"),
           ("cup", "tray", .1, "white ceramic cup"),
           ("box", "desk", .2, "small lacquered box"),
           ("vase", "box", .4, "tall glass vase")]  # medium, but on clutter: goes with the box


def row() -> dict:
    condition = json.loads((ROOT / "examples" / "bedroom.json").read_text())
    condition["objects"] = [{"id": i, "category": i, "description": d, **({"support_parent": s} if s != "floor" else {})}
                            for i, s, _m, d in OBJECTS]
    condition["constraints"] = [{"type": "near", "object_id": "cup", "target_id": "tray", "max_distance_m": .3},
                                {"type": "on", "object_id": "lamp", "parent_id": "desk"},
                                {"type": "between", "object_id": "desk", "target_ids": ["bed", "vase"]},
                                {"type": "against_wall", "object_id": "bed"}]
    target = {"schema_version": "fastfill.v2", "objects": [
        {"id": i, "target_size_local_m": [m * .5, m, m * .6], "bottom_center_m": [1. + n * .4, 1., 0.], "yaw_rad": 0.}
        for n, (i, _s, m, _d) in enumerate(OBJECTS)]}
    n = len(OBJECTS)
    return {"schema_version": "fastfill.v2", "condition": condition, "target": target,
            "validity": {"position": [[True] * 3] * n, "exchangeable_group": list(range(n))},
            "provenance": {"source": "test", "scene_id": "test::0", "target_source_ids": [f"src_{i}" for i, *_ in OBJECTS],
                           "field_evidence": [{"k": i} for i, *_ in OBJECTS], "request_order": "fixed"}}


class TierRoomsTests(unittest.TestCase):
    def test_layers_follow_the_support_and_the_ground_truth_size(self):
        self.assertEqual(mt.layers(row(), .3), {"bed": 1, "desk": 1, "mirror": 1, "lamp": 2, "tray": 2, "cup": 3,
                                                "box": 3, "vase": 2})

    def test_each_level_keeps_its_layers_and_drops_what_stands_on_a_removed_object(self):
        r = row()
        layer = mt.layers(r, .3)
        self.assertEqual(mt.kept(r, layer, 1), {"bed", "desk", "mirror"})
        self.assertEqual(mt.kept(r, layer, 2), {"bed", "desk", "mirror", "lamp", "tray"})  # the vase is on the box
        self.assertEqual(mt.kept(r, layer, 3), {i for i, *_ in OBJECTS})

    def test_a_version_filters_objects_constraints_and_per_object_lists_together(self):
        r = row()
        v = mt.version(r, {"bed", "desk", "mirror", "lamp", "tray"})
        ids = ["bed", "desk", "mirror", "lamp", "tray"]
        self.assertEqual([o["id"] for o in v["condition"]["objects"]], ids)
        self.assertEqual([o["id"] for o in v["target"]["objects"]], ids)
        self.assertEqual([c["type"] for c in v["condition"]["constraints"]], ["on", "against_wall"])
        self.assertEqual(v["validity"]["exchangeable_group"], [0, 1, 2, 3, 4])
        self.assertEqual(v["provenance"]["target_source_ids"], [f"src_{i}" for i in ids])
        self.assertEqual(len(v["provenance"]["field_evidence"]), 5)
        self.assertEqual(v["condition"]["room"], r["condition"]["room"])
        self.assertEqual(len(r["condition"]["objects"]), len(OBJECTS))  # the input row is not changed

    def test_easy_and_medium_are_written_and_hard_is_the_input_row(self):
        r = row()
        furniture_only = row()
        furniture_only["condition"]["objects"] = furniture_only["condition"]["objects"][:3]
        furniture_only["target"]["objects"] = furniture_only["target"]["objects"][:3]
        for key in ("position", "exchangeable_group"):
            furniture_only["validity"][key] = furniture_only["validity"][key][:3]
        for key in mt.PROVENANCE_PER_OBJECT:
            furniture_only["provenance"][key] = furniture_only["provenance"][key][:3]
        furniture_only["condition"]["constraints"] = [{"type": "against_wall", "object_id": "bed"}]
        written, manifest = mt.tier_rows([furniture_only, r])
        self.assertEqual([(e["base_index"], e["level"], e["objects"], e["row"]) for e in manifest],
                         [(1, "easy", 3, 0), (1, "medium", 5, 1), (1, "hard", 8, None)])
        self.assertEqual([w["provenance"]["tier"]["level"] for w in written], ["easy", "medium"])
        mt.check(written, [furniture_only, r], manifest)  # valid requests and targets, descriptions kept


if __name__ == "__main__":
    unittest.main()
