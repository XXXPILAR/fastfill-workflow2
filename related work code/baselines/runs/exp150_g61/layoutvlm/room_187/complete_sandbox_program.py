from math import cos, sin, radians
import uuid
from pydantic import BaseModel, Field, conint
from typing import List, Optional, Union


class Wall(BaseModel):
    optimize: int = Field(description="Whether to optimize the position and rotation of the asset", default=0)
    corner1: List[float] = Field(description="2d coordinates of the first corner of this wall")
    corner2: List[float] = Field(description="2d coordinates of the second corner of this wall")
    instance_id: Optional[str] = Field(description="Unique identifier for the wall", default=None)

class AssetInstance(BaseModel):
    optimize: int = Field(description="Whether to optimize the position and rotation of the asset", default=1)
    position: List[float] = Field(description="Position of the asset", default=[0,0,0])
    rotation: List[float] = Field(description="Rotation of the asset in degrees", default=[0,0,0])
    instance_id: Optional[str] = Field(description="Unique identifier for the asset instance", default=None)
    size: Optional[List[float]] = Field(description="Bounding box size of the asset instance", default=0.01)

    # if the position is 2d, add a zero z-coordinate
    def __init__(self, **data):
        if 'position' in data and len(data['position']) == 2:
            data['position'].append(0)
        super().__init__(**data)

    # Method to set size from the parent Assets class if not provided
    def set_size_from_parent(self, parent_size: Optional[List[float]]):
        if self.size is None and parent_size is not None:
            self.size = parent_size


class Assets(BaseModel):
    description: str = Field(description="Description of the asset")
    placements: List[AssetInstance] = Field(description="List of asset instances of this 3D asset", default=None)
    size: Optional[List[float]] = Field(description="Bounding box size of the asset (z-axis up)", default=None)
    onCeiling: bool = Field(description="Whether the asset is on the ceiling", default=False)

    def __getitem__(self, index: int) -> AssetInstance:
        "Allow indexing into placements."
        return self.placements[index]
    
    def __len__(self) -> int:
        "Allow using len() to get the number of placements."
        return len(self.placements)


class Constraint:
    def __init__(self, constraint_name, **params):
        self.constraint_name = constraint_name
        self.params = params
    
    def evaluate(self, assets: list):
        return self.constraint_func(assets, **self.params)


fixed_pointtt = Assets(description="global absolute marks", size=[0.01, 0.01, 0.01], placements=[])
def get_instance_id(asset):
    global fixed_pointtt
    if asset.instance_id is not None:
        return asset.instance_id

    if isinstance(asset, AssetInstance):
        # fine the name of the variable that is an instance of AssetInstance
        for var_name in globals(): 
            var = globals()[var_name]
            if isinstance(var, Assets):
                for instance_idx, placement in enumerate(var.placements):
                    if id(placement) == id(asset):
                        return f"{var_name}_{instance_idx}"

        # new instantiation of AssetInstance, return random instance_id
        instance_index = len(fixed_pointtt.placements)
        fixed_pointtt.placements.append(
            AssetInstance(
                position=asset.position,
                rotation=[0,0,0],
                optimize=False,
                instance_id=f"fixed_pointtt_{instance_index}"
            )
        )
        return fixed_pointtt.placements[-1].instance_id

    if isinstance(asset, Wall):
        var = globals()['walls']
        for instance_idx, wall_instance in enumerate(var):
            if id(wall_instance) == id(asset):
                return f"walls_{instance_idx}"


class ConstraintSolver:
    def __init__(self):
        self.constraints = []

    def handle_fixed_pointtt(self, asset):
        global fixed_pointtt
        if isinstance(asset, tuple):
            instance_index = len(fixed_pointtt.placements)
            fixed_pointtt.placements.append(
                AssetInstance(
                    position=list(asset),
                    rotation=[0,0,0],
                    optimize=False,
                    instance_id=f"fixed_pointtt_{instance_index}"
                )
            )
            return fixed_pointtt.placements[-1]
        return asset
    
    def point_towards(self, asset1: AssetInstance, asset2: Union[AssetInstance, tuple], angle=0):
        asset1.instance_id = get_instance_id(asset1)
        asset2 = self.handle_fixed_pointtt(asset2)
        asset2.instance_id = get_instance_id(asset2)
        self.constraints.append([
            Constraint("point_towards", angle=angle),
            [asset1.instance_id, asset2.instance_id]
        ])

    def distance_constraint(self, asset1: AssetInstance, asset2: Union[AssetInstance, tuple], min_distance=0, max_distance=10000, weight=1):
        asset1.instance_id = get_instance_id(asset1)
        asset2 = self.handle_fixed_pointtt(asset2)
        asset2.instance_id = get_instance_id(asset2)
        self.constraints.append([
            Constraint("distance_constraint", min_distance=min_distance, max_distance=max_distance, weight=weight),
            [asset1.instance_id, asset2.instance_id]
        ])

    def against_wall(self, asset1: AssetInstance, wall: Wall):
        asset1.instance_id = get_instance_id(asset1)
        wall.instance_id = get_instance_id(wall)
        self.constraints.append([
            Constraint("against_wall"),
            [asset1.instance_id, wall.instance_id]
        ])

    def on_top_of(self, asset1: AssetInstance, asset2: AssetInstance):
        asset1.instance_id = get_instance_id(asset1)
        asset2 = self.handle_fixed_pointtt(asset2)
        asset2.instance_id = get_instance_id(asset2)
        self.constraints.append([
            Constraint("on_top_of"),
            [asset1.instance_id, asset2.instance_id]
        ])
    
    def align_with(self, asset1: AssetInstance, asset2: AssetInstance, angle=0):
        asset1.instance_id = get_instance_id(asset1)
        asset2.instance_id = get_instance_id(asset2)
        self.constraints.append([
            Constraint("align_with", angle=angle),
            [asset1.instance_id, asset2.instance_id]
        ])

    def align_x(self, asset1: AssetInstance, asset2: AssetInstance):
        """
        Add a constraint that asset1 should have the same x-coordinate as asset2.
        """
        asset1.instance_id = get_instance_id(asset1)
        asset2.instance_id = get_instance_id(asset2)
        self.constraints.append([
            Constraint("align_x"),
            [asset1.instance_id, asset2.instance_id]
        ])

    def align_y(self, asset1: AssetInstance, asset2: AssetInstance):
        """
        Add a constraint that asset1 should have the same y-coordinate as asset2.
        """
        asset1.instance_id = get_instance_id(asset1)
        asset2.instance_id = get_instance_id(asset2)
        self.constraints.append([
            Constraint("align_y"),
            [asset1.instance_id, asset2.instance_id]
        ])

    def solve(self):
        pass

        
solver = ConstraintSolver()

# Walls that define the boundary of the scene
walls = [
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.60, 0.00, 0.00]),
    Wall(corner1=[6.60, 0.00, 0.00], corner2=[6.60, 5.40, 0.00]),
    Wall(corner1=[6.60, 5.40, 0.00], corner2=[0.00, 5.40, 0.00]),
    Wall(corner1=[0.00, 5.40, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
ping_pong_ball_tube = Assets(description="ping pong ball tube", size=[0.05, 0.05, 0.26], placements=[AssetInstance() for _ in range(1)])
whiteboard = Assets(description="whiteboard", size=[0.04, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
side_table = Assets(description="side table", size=[0.45, 0.45, 0.50], placements=[AssetInstance() for _ in range(1)])
floor_lamp = Assets(description="floor lamp", size=[0.35, 0.35, 1.65], placements=[AssetInstance() for _ in range(1)])
bowl = Assets(description="bowl", size=[0.20, 0.20, 0.09], placements=[AssetInstance() for _ in range(1)])
wall_shelf = Assets(description="wall shelf", size=[0.25, 0.90, 0.04], placements=[AssetInstance() for _ in range(1)])
clock = Assets(description="clock", size=[0.04, 0.30, 0.30], placements=[AssetInstance() for _ in range(1)])
rug = Assets(description="rug", size=[1.20, 1.80, 0.01], placements=[AssetInstance() for _ in range(1)])
poster = Assets(description="poster", size=[0.02, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
bench = Assets(description="bench", size=[0.40, 1.20, 0.45], placements=[AssetInstance() for _ in range(1)])
water_bottle = Assets(description="water bottle", size=[0.07, 0.07, 0.25], placements=[AssetInstance() for _ in range(1)])
canvas_print = Assets(description="canvas print", size=[0.04, 0.80, 0.60], placements=[AssetInstance() for _ in range(1)])
ping_pong_ball_A = Assets(description="ping pong ball", size=[0.04, 0.04, 0.04], placements=[AssetInstance() for _ in range(1)])
loveseat = Assets(description="loveseat", size=[0.80, 1.40, 0.82], placements=[AssetInstance() for _ in range(1)])
cork_coaster = Assets(description="cork coaster", size=[0.10, 0.10, 0.01], placements=[AssetInstance() for _ in range(1)])
storage_cabinet = Assets(description="storage cabinet", size=[0.40, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
photography_print_A = Assets(description="photography print", size=[0.03, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])
accent_chair = Assets(description="accent chair", size=[0.75, 0.70, 0.80], placements=[AssetInstance() for _ in range(1)])
ping_pong_table = Assets(description="ping pong table", size=[2.74, 1.52, 0.91], placements=[AssetInstance() for _ in range(1)])
ping_pong_ball_B = Assets(description="ping pong ball", size=[0.04, 0.04, 0.04], placements=[AssetInstance() for _ in range(1)])
ping_pong_ball_C = Assets(description="ping pong ball", size=[0.04, 0.04, 0.04], placements=[AssetInstance() for _ in range(1)])
spray_bottle = Assets(description="spray bottle", size=[0.07, 0.10, 0.25], placements=[AssetInstance() for _ in range(1)])
sports_equipment_rack = Assets(description="sports equipment rack", size=[0.20, 0.65, 0.50], placements=[AssetInstance() for _ in range(1)])
photography_print_B = Assets(description="photography print", size=[0.03, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])

ping_pong_ball_tube[0].instance_id = 'ping_pong_ball_tube_0'
whiteboard[0].instance_id = 'whiteboard_0'
side_table[0].instance_id = 'side_table_0'
floor_lamp[0].instance_id = 'floor_lamp_0'
bowl[0].instance_id = 'bowl_0'
wall_shelf[0].instance_id = 'wall_shelf_0'
clock[0].instance_id = 'clock_0'
rug[0].instance_id = 'rug_0'
poster[0].instance_id = 'poster_0'
bench[0].instance_id = 'bench_0'
water_bottle[0].instance_id = 'water_bottle_0'
canvas_print[0].instance_id = 'canvas_print_0'
ping_pong_ball_A[0].instance_id = 'ping_pong_ball_A_0'
loveseat[0].instance_id = 'loveseat_0'
cork_coaster[0].instance_id = 'cork_coaster_0'
storage_cabinet[0].instance_id = 'storage_cabinet_0'
photography_print_A[0].instance_id = 'photography_print_A_0'
accent_chair[0].instance_id = 'accent_chair_0'
ping_pong_table[0].instance_id = 'ping_pong_table_0'
ping_pong_ball_B[0].instance_id = 'ping_pong_ball_B_0'
ping_pong_ball_C[0].instance_id = 'ping_pong_ball_C_0'
spray_bottle[0].instance_id = 'spray_bottle_0'
sports_equipment_rack[0].instance_id = 'sports_equipment_rack_0'
photography_print_B[0].instance_id = 'photography_print_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

ping_pong_ball_tube[0].position = [0.21803521622654798, 4.110956944275024, 0.13]
ping_pong_ball_tube[0].rotation = [0, 0, 0]
whiteboard[0].position = [3.425745371507358, 4.012883194488154, 0.45]
whiteboard[0].rotation = [0, 0, 0]
side_table[0].position = [1.8281651803414507, 5.3498455601269015, 0.25]
side_table[0].rotation = [0, 0, 0]
floor_lamp[0].position = [0.08538909099539577, 0.5125166223021294, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
bowl[0].position = [5.6838101558161735, 0.8889941879747812, 0.045]
bowl[0].rotation = [0, 0, 0]
wall_shelf[0].position = [5.79983339738822, 4.821751665823584, 0.02]
wall_shelf[0].rotation = [0, 0, 0]
clock[0].position = [6.092487188842516, 0.5036321488057223, 0.15]
clock[0].rotation = [0, 0, 0]
rug[0].position = [2.5391116315484186, 0.9658777454484183, 0.005]
rug[0].rotation = [0, 0, 0]
poster[0].position = [0.1613331460540397, 1.4582112320849392, 0.35]
poster[0].rotation = [0, 0, 0]
bench[0].position = [0.035256036082037236, 4.145661059576471, 0.225]
bench[0].rotation = [0, 0, 0]
water_bottle[0].position = [3.5499696260086844, 2.890351189562401, 0.125]
water_bottle[0].rotation = [0, 0, 0]
canvas_print[0].position = [0.19537630353748012, 2.3125820263722128, 0.3]
canvas_print[0].rotation = [0, 0, 0]
ping_pong_ball_A[0].position = [0.21499210205451305, 2.931837867775116, 0.02]
ping_pong_ball_A[0].rotation = [0, 0, 0]
loveseat[0].position = [1.2449554964117642, 1.550163960797451, 0.41]
loveseat[0].rotation = [0, 0, 0]
cork_coaster[0].position = [3.447762080630157, 0.5207480400091599, 0.0025]
cork_coaster[0].rotation = [0, 0, 0]
storage_cabinet[0].position = [5.666088345046196, 0.31412628558183986, 0.45]
storage_cabinet[0].rotation = [0, 0, 0]
photography_print_A[0].position = [3.1096285889820368, 2.205746407240046, 0.3]
photography_print_A[0].rotation = [0, 0, 0]
accent_chair[0].position = [4.3082656720340795, 1.4421374049786877, 0.4]
accent_chair[0].rotation = [0, 0, 0]
ping_pong_table[0].position = [3.686402060356801, 2.606087156252063, 0.45625]
ping_pong_table[0].rotation = [0, 0, 0]
ping_pong_ball_B[0].position = [2.3369640063507955, 1.8023206003671473, 0.02]
ping_pong_ball_B[0].rotation = [0, 0, 0]
ping_pong_ball_C[0].position = [2.3205628166428225, 0.5741345086601404, 0.02]
ping_pong_ball_C[0].rotation = [0, 0, 0]
spray_bottle[0].position = [6.453825581326267, 1.668268401830879, 0.125]
spray_bottle[0].rotation = [0, 0, 0]
sports_equipment_rack[0].position = [2.5991723786254797, 4.593187691326387, 0.25]
sports_equipment_rack[0].rotation = [0, 0, 0]
photography_print_B[0].position = [1.6886631843209061, 0.7464432362475456, 0.3]
photography_print_B[0].rotation = [0, 0, 0]
ping_pong_ball_tube[0].position = [0.21803521622654798, 4.110956944275024, 0.13]
ping_pong_ball_tube[0].rotation = [0, 0, 0]
whiteboard[0].position = [3.425745371507358, 4.012883194488154, 0.45]
whiteboard[0].rotation = [0, 0, 0]
side_table[0].position = [1.8281651803414507, 5.3498455601269015, 0.25]
side_table[0].rotation = [0, 0, 0]
floor_lamp[0].position = [0.08538909099539577, 0.5125166223021294, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
bowl[0].position = [5.6838101558161735, 0.8889941879747812, 0.045]
bowl[0].rotation = [0, 0, 0]
wall_shelf[0].position = [5.79983339738822, 4.821751665823584, 0.02]
wall_shelf[0].rotation = [0, 0, 0]
clock[0].position = [6.092487188842516, 0.5036321488057223, 0.15]
clock[0].rotation = [0, 0, 0]
rug[0].position = [2.5391116315484186, 0.9658777454484183, 0.005]
rug[0].rotation = [0, 0, 0]
poster[0].position = [0.1613331460540397, 1.4582112320849392, 0.35]
poster[0].rotation = [0, 0, 0]
bench[0].position = [0.035256036082037236, 4.145661059576471, 0.225]
bench[0].rotation = [0, 0, 0]
water_bottle[0].position = [3.5499696260086844, 2.890351189562401, 0.125]
water_bottle[0].rotation = [0, 0, 0]
canvas_print[0].position = [0.19537630353748012, 2.3125820263722128, 0.3]
canvas_print[0].rotation = [0, 0, 0]
ping_pong_ball_A[0].position = [0.21499210205451305, 2.931837867775116, 0.02]
ping_pong_ball_A[0].rotation = [0, 0, 0]
loveseat[0].position = [1.2449554964117642, 1.550163960797451, 0.41]
loveseat[0].rotation = [0, 0, 0]
cork_coaster[0].position = [3.447762080630157, 0.5207480400091599, 0.0025]
cork_coaster[0].rotation = [0, 0, 0]
storage_cabinet[0].position = [5.666088345046196, 0.31412628558183986, 0.45]
storage_cabinet[0].rotation = [0, 0, 0]
photography_print_A[0].position = [3.1096285889820368, 2.205746407240046, 0.3]
photography_print_A[0].rotation = [0, 0, 0]
accent_chair[0].position = [4.3082656720340795, 1.4421374049786877, 0.4]
accent_chair[0].rotation = [0, 0, 0]
ping_pong_table[0].position = [3.686402060356801, 2.606087156252063, 0.45625]
ping_pong_table[0].rotation = [0, 0, 0]
ping_pong_ball_B[0].position = [2.3369640063507955, 1.8023206003671473, 0.02]
ping_pong_ball_B[0].rotation = [0, 0, 0]
ping_pong_ball_C[0].position = [2.3205628166428225, 0.5741345086601404, 0.02]
ping_pong_ball_C[0].rotation = [0, 0, 0]
spray_bottle[0].position = [6.453825581326267, 1.668268401830879, 0.125]
spray_bottle[0].rotation = [0, 0, 0]
sports_equipment_rack[0].position = [2.5991723786254797, 4.593187691326387, 0.25]
sports_equipment_rack[0].rotation = [0, 0, 0]
photography_print_B[0].position = [1.6886631843209061, 0.7464432362475456, 0.3]
photography_print_B[0].rotation = [0, 0, 0]

solver.constraints = []

# The supplied boundary is 0 <= x <= 6.60, 0 <= y <= 5.40.
# Keep the ping-pong area in the rear and a compact conversation area
# in front, leaving the table's long-axis ends available for play.
# Each entry is (existing asset, center position, yaw in degrees).
layout_specs = [
    (ping_pong_table, [3.30, 3.35, 0.455], 0),
    (loveseat, [0.40, 1.05, 0.410], 0),
    (accent_chair, [2.40, 1.05, 0.400], 180),
    (side_table, [2.40, 0.375, 0.250], 0),
    (rug, [1.40, 1.05, 0.005], 0),
    (floor_lamp, [0.25, 2.15, 0.825], 0),

    # Cabinet and equipment storage occupy the right-hand perimeter.
    (storage_cabinet, [6.40, 0.80, 0.450], 180),
    (sports_equipment_rack, [6.50, 3.35, 0.250], 180),
    (bench, [3.30, 5.20, 0.225], 270),

    # Wall-mounted pieces are elevated explicitly, rather than left on the floor.
    (wall_shelf, [0.125, 3.00, 1.500], 0),
    (whiteboard, [0.020, 4.40, 1.650], 0),
    (clock, [6.580, 4.50, 2.100], 180),
    (canvas_print, [1.00, 5.380, 1.750], 270),
    (poster, [4.60, 0.010, 1.700], 90),
    (photography_print_A, [0.90, 0.015, 1.850], 90),
    (photography_print_B, [2.20, 0.015, 1.850], 90),

    # Small items sit on appropriate supporting surfaces.
    (ping_pong_ball_tube, [0.125, 2.75, 1.650], 0),
    (bowl, [6.40, 0.60, 0.945], 180),
    (spray_bottle, [6.40, 1.05, 1.025], 180),
    (cork_coaster, [2.40, 0.375, 0.505], 0),
    (water_bottle, [2.40, 0.375, 0.635], 0),
    (ping_pong_ball_A, [2.65, 3.10, 0.930], 0),
    (ping_pong_ball_B, [3.15, 3.55, 0.930], 0),
    (ping_pong_ball_C, [4.00, 3.25, 0.930], 0),
]

for asset_group, center_xyz, yaw_degrees in layout_specs:
    asset_group[0].position = list(center_xyz)
    asset_group[0].rotation = [0, 0, radians(yaw_degrees)]

# Primary layout requirements come first.
solver.against_wall(storage_cabinet[0], walls[1])
solver.point_towards(accent_chair[0], loveseat[0])
solver.point_towards(loveseat[0], accent_chair[0])

# The chair and side table have a 0.10 m edge-to-edge gap:
# 0.35 m chair half-width + 0.225 m table half-width + 0.10 m.
# Include their different center heights in the center-distance constraint.
chair_table_distance = (
    (0.35 + 0.225 + 0.10) ** 2 + (0.400 - 0.250) ** 2
) ** 0.5
solver.distance_constraint(
    accent_chair[0], side_table[0],
    chair_table_distance, chair_table_distance, weight=10
)

# Surface support constraints: no small objects are left floating or on the floor.
support_pairs = [
    (ping_pong_ball_tube[0], wall_shelf[0]),
    (bowl[0], storage_cabinet[0]),
    (spray_bottle[0], storage_cabinet[0]),
    (cork_coaster[0], side_table[0]),
    (water_bottle[0], cork_coaster[0]),
    (ping_pong_ball_A[0], ping_pong_table[0]),
    (ping_pong_ball_B[0], ping_pong_table[0]),
    (ping_pong_ball_C[0], ping_pong_table[0]),
]
for supported_instance, supporting_instance in support_pairs:
    solver.on_top_of(supported_instance, supporting_instance)

# Wall attachment and inward-facing orientations for perimeter furnishings.
wall_assignments = [
    (loveseat[0], walls[3]),
    (sports_equipment_rack[0], walls[1]),
    (bench[0], walls[2]),
    (wall_shelf[0], walls[3]),
    (whiteboard[0], walls[3]),
    (clock[0], walls[1]),
    (canvas_print[0], walls[2]),
    (poster[0], walls[0]),
    (photography_print_A[0], walls[0]),
    (photography_print_B[0], walls[0]),
]
for mounted_instance, supporting_wall in wall_assignments:
    solver.against_wall(mounted_instance, supporting_wall)

# Fixed reference poses preserve the selected locations, wall mounting heights,
# and clearances. These also provide a position and orientation constraint for
# every new instance. References are constraint anchors, not additional assets.
# A small positional tolerance allows minor feasibility adjustments.
for asset_group, center_xyz, yaw_degrees in layout_specs:
    fixed_reference = AssetInstance(
        position=list(center_xyz),
        rotation=[0, 0, radians(yaw_degrees)]
    )
    solver.distance_constraint(
        asset_group[0], fixed_reference, 0, 0.005, weight=10
    )
    solver.align_with(asset_group[0], fixed_reference)

# Preserve the functional seating separation and table-to-seating clearance.
solver.distance_constraint(accent_chair[0], loveseat[0], 1.95, 2.10, weight=10)
solver.distance_constraint(ping_pong_table[0], accent_chair[0], 2.40, None)
solver.distance_constraint(ping_pong_table[0], side_table[0], 3.00, None)

# Keep separate accessories from clustering during minor layout adjustments.
solver.distance_constraint(bowl[0], spray_bottle[0], 0.30, None)
solver.distance_constraint(ping_pong_ball_A[0], ping_pong_ball_B[0], 0.15, None)
solver.distance_constraint(ping_pong_ball_A[0], ping_pong_ball_C[0], 0.15, None)
solver.distance_constraint(ping_pong_ball_B[0], ping_pong_ball_C[0], 0.15, None)

solver.constraints = []
whiteboard[0].position = [0.02003319561481476, 4.400000095367432, 0.44999998807907104]
whiteboard[0].rotation = [0, 0, -8.595107725113869e-05]
whiteboard[0].optimize = 2
spray_bottle[0].position = [6.400000095367432, 1.0499999523162842, 1.024999976158142]
spray_bottle[0].rotation = [0, 0, -3.125884689672577]
spray_bottle[0].optimize = 2
side_table[0].position = [2.4000000953674316, 0.375, 0.25]
side_table[0].rotation = [0, 0, 0.01884955539881635]
side_table[0].optimize = 2
photography_print_B[0].position = [2.200000047683716, 0.015059332363307476, 0.30000001192092896]
photography_print_B[0].rotation = [0, 0, 1.5707103801518554]
photography_print_B[0].optimize = 2
ping_pong_ball_A[0].position = [2.6500000953674316, 3.0999999046325684, 0.9300000071525574]
ping_pong_ball_A[0].rotation = [0, 0, 0.01884955539881635]
ping_pong_ball_A[0].optimize = 2
poster[0].position = [4.599999904632568, 0.009933757595717907, 0.3499999940395355]
poster[0].rotation = [0, 0, 1.5707103800399376]
poster[0].optimize = 2
cork_coaster[0].position = [2.4000000953674316, 0.375, 0.5049999952316284]
cork_coaster[0].rotation = [0, 0, 0.0157079639172164]
cork_coaster[0].optimize = 2
accent_chair[0].position = [2.4000000953674316, 1.131730079650879, 0.4000000059604645]
accent_chair[0].rotation = [0, 0, -3.1164599134799373]
accent_chair[0].optimize = 2
wall_shelf[0].position = [0.12498726695775986, 3.0, 0.019999999552965164]
wall_shelf[0].rotation = [0, 0, 5.899131615945358e-06]
wall_shelf[0].optimize = 2
ping_pong_ball_C[0].position = [4.0, 3.25, 0.9300000071525574]
ping_pong_ball_C[0].rotation = [0, 0, 0.01884955539881635]
ping_pong_ball_C[0].optimize = 2
loveseat[0].position = [0.3998910188674927, 1.0499999523162842, 0.4099999964237213]
loveseat[0].rotation = [0, 0, -3.6044282963134385e-05]
loveseat[0].optimize = 2
canvas_print[0].position = [1.0, 5.37992525100708, 0.30000001192092896]
canvas_print[0].rotation = [0, 0, -1.5708822639760769]
canvas_print[0].optimize = 2
water_bottle[0].position = [2.4000000953674316, 0.375, 0.6349999904632568]
water_bottle[0].rotation = [0, 0, 0.01256637125682779]
water_bottle[0].optimize = 2
ping_pong_ball_B[0].position = [3.1500000953674316, 3.549999952316284, 0.9300000071525574]
ping_pong_ball_B[0].rotation = [0, 0, 0.01884955539881635]
ping_pong_ball_B[0].optimize = 2
rug[0].position = [1.399999976158142, 1.0499999523162842, 0.004999999888241291]
rug[0].rotation = [0, 0, 0.00942477746072377]
rug[0].optimize = 2
sports_equipment_rack[0].position = [6.500017166137695, 3.3499999046325684, 0.25]
sports_equipment_rack[0].rotation = [0, 0, 3.1415066866928507]
sports_equipment_rack[0].optimize = 2
clock[0].position = [6.579925060272217, 4.5, 0.15000000596046448]
clock[0].rotation = [0, 0, 3.141506698714957]
clock[0].optimize = 2
bench[0].position = [3.299999952316284, 5.199955463409424, 0.22499999403953552]
bench[0].rotation = [0, 0, -1.5708822446542057]
bench[0].optimize = 2
storage_cabinet[0].position = [6.4000396728515625, 0.800000011920929, 0.44999998807907104]
storage_cabinet[0].rotation = [0, 0, -3.1415401435202304]
storage_cabinet[0].optimize = 2
bowl[0].position = [6.400000095367432, 0.6000000238418579, 0.9449999928474426]
bowl[0].rotation = [0, 0, -3.125884689672577]
bowl[0].optimize = 2
floor_lamp[0].position = [0.25, 2.1500000953674316, 0.824999988079071]
floor_lamp[0].rotation = [0, 0, 0.00942477746072377]
floor_lamp[0].optimize = 2
ping_pong_ball_tube[0].position = [0.125, 2.75, 0.16999998688697815]
ping_pong_ball_tube[0].rotation = [0, 0, 0.01256637125682779]
ping_pong_ball_tube[0].optimize = 2
photography_print_A[0].position = [0.8999999761581421, 0.015059332363307476, 0.30000001192092896]
photography_print_A[0].rotation = [0, 0, 1.5707103801518554]
photography_print_A[0].optimize = 2
ping_pong_table[0].position = [3.3579189777374268, 3.407918930053711, 0.45500001311302185]
ping_pong_table[0].rotation = [0, 0, 0.025132740109855806]
ping_pong_table[0].optimize = 2

