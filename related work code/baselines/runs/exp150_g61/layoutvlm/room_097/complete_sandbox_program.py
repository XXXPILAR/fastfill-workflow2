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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.00, 0.00, 0.00]),
    Wall(corner1=[6.00, 0.00, 0.00], corner2=[6.00, 5.00, 0.00]),
    Wall(corner1=[6.00, 5.00, 0.00], corner2=[0.00, 5.00, 0.00]),
    Wall(corner1=[0.00, 5.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
toilet_suite_A = Assets(description="toilet suite", size=[0.70, 0.38, 0.80], placements=[AssetInstance() for _ in range(1)])
toilet_suite_B = Assets(description="toilet suite", size=[0.70, 0.38, 0.80], placements=[AssetInstance() for _ in range(1)])
wall_mirror_strip = Assets(description="A rectangular light wooden panel in a whitish-gray frame.", size=[0.04, 2.40, 0.80], placements=[AssetInstance() for _ in range(1)])
hand_dryer_A = Assets(description="A round light on a silver mount.", size=[0.20, 0.30, 0.32], placements=[AssetInstance() for _ in range(1)])
cleaning_storage_cabinet = Assets(description="Two stacked locker units that are yellow and gray.", size=[0.55, 0.80, 1.80], placements=[AssetInstance() for _ in range(1)])
wall_waste_bin_A = Assets(description="A cream colored trash can.", size=[0.24, 0.32, 0.50], placements=[AssetInstance() for _ in range(1)])
freestanding_waste_bin_A = Assets(description="a trash can with holes on a metal stand.", size=[0.35, 0.35, 0.65], placements=[AssetInstance() for _ in range(1)])
full_length_mirror = Assets(description="A rectangular mirror in a brown wooden frame.", size=[0.04, 0.60, 1.70], placements=[AssetInstance() for _ in range(1)])
freestanding_waste_bin_B = Assets(description="a trash can with holes on a metal stand.", size=[0.35, 0.35, 0.65], placements=[AssetInstance() for _ in range(1)])
vanity_under_counter_cabinet = Assets(description="A long white cabinet with a white top.", size=[0.60, 2.40, 0.85], placements=[AssetInstance() for _ in range(1)])
floor_locker_column_A = Assets(description="Two stacked locker units that are yellow and gray.", size=[0.50, 0.40, 1.80], placements=[AssetInstance() for _ in range(1)])
toilet_suite_C = Assets(description="toilet suite", size=[0.70, 0.38, 0.80], placements=[AssetInstance() for _ in range(1)])
hand_dryer_B = Assets(description="A round light on a silver mount.", size=[0.20, 0.30, 0.32], placements=[AssetInstance() for _ in range(1)])
wall_signage_A = Assets(description="A chalk billboard with some prices on it.", size=[0.03, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])
wall_signage_B = Assets(description="A chalk billboard with some prices on it.", size=[0.03, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])
wall_waste_bin_B = Assets(description="A cream colored trash can.", size=[0.24, 0.32, 0.50], placements=[AssetInstance() for _ in range(1)])
floor_locker_column_B = Assets(description="Two stacked locker units that are yellow and gray.", size=[0.50, 0.40, 1.80], placements=[AssetInstance() for _ in range(1)])
toilet_suite_D = Assets(description="toilet suite", size=[0.70, 0.38, 0.80], placements=[AssetInstance() for _ in range(1)])
hand_dryer_C = Assets(description="A round light on a silver mount.", size=[0.20, 0.30, 0.32], placements=[AssetInstance() for _ in range(1)])
urinal_row = Assets(description="White toilet with tall tank and rust stains.", size=[0.40, 1.80, 1.20], placements=[AssetInstance() for _ in range(1)])

toilet_suite_A[0].instance_id = 'toilet_suite_A_0'
toilet_suite_B[0].instance_id = 'toilet_suite_B_0'
wall_mirror_strip[0].instance_id = 'wall_mirror_strip_0'
hand_dryer_A[0].instance_id = 'hand_dryer_A_0'
cleaning_storage_cabinet[0].instance_id = 'cleaning_storage_cabinet_0'
wall_waste_bin_A[0].instance_id = 'wall_waste_bin_A_0'
freestanding_waste_bin_A[0].instance_id = 'freestanding_waste_bin_A_0'
full_length_mirror[0].instance_id = 'full_length_mirror_0'
freestanding_waste_bin_B[0].instance_id = 'freestanding_waste_bin_B_0'
vanity_under_counter_cabinet[0].instance_id = 'vanity_under_counter_cabinet_0'
floor_locker_column_A[0].instance_id = 'floor_locker_column_A_0'
toilet_suite_C[0].instance_id = 'toilet_suite_C_0'
hand_dryer_B[0].instance_id = 'hand_dryer_B_0'
wall_signage_A[0].instance_id = 'wall_signage_A_0'
wall_signage_B[0].instance_id = 'wall_signage_B_0'
wall_waste_bin_B[0].instance_id = 'wall_waste_bin_B_0'
floor_locker_column_B[0].instance_id = 'floor_locker_column_B_0'
toilet_suite_D[0].instance_id = 'toilet_suite_D_0'
hand_dryer_C[0].instance_id = 'hand_dryer_C_0'
urinal_row[0].instance_id = 'urinal_row_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

toilet_suite_A[0].position = [0.4814483699088692, 3.3424688087225145, 0.4]
toilet_suite_A[0].rotation = [0, 0, 0]
toilet_suite_B[0].position = [3.340543180164598, 1.9363121085724555, 0.4]
toilet_suite_B[0].rotation = [0, 0, 0]
wall_mirror_strip[0].position = [1.9093419503405569, 0.25342101096199277, 0.4]
wall_mirror_strip[0].rotation = [0, 0, 0]
hand_dryer_A[0].position = [1.5539770207841173, 2.494430280074262, 0.16]
hand_dryer_A[0].rotation = [0, 0, 0]
cleaning_storage_cabinet[0].position = [0.621690492356926, 0.7556391120730316, 0.9]
cleaning_storage_cabinet[0].rotation = [0, 0, 0]
wall_waste_bin_A[0].position = [5.759908917166166, 1.757778822221262, 0.25]
wall_waste_bin_A[0].rotation = [0, 0, 0]
freestanding_waste_bin_A[0].position = [5.556093945919497, 1.962200826270054, 0.325]
freestanding_waste_bin_A[0].rotation = [0, 0, 0]
full_length_mirror[0].position = [5.5687951472231285, 0.21877621845503015, 0.85]
full_length_mirror[0].rotation = [0, 0, 0]
freestanding_waste_bin_B[0].position = [1.6376944962649298, 2.3802461824294614, 0.325]
freestanding_waste_bin_B[0].rotation = [0, 0, 0]
vanity_under_counter_cabinet[0].position = [2.679601813904033, 2.0547936241767, 0.425]
vanity_under_counter_cabinet[0].rotation = [0, 0, 0]
floor_locker_column_A[0].position = [3.704975766180988, 2.789083242628693, 0.9]
floor_locker_column_A[0].rotation = [0, 0, 0]
toilet_suite_C[0].position = [2.6914657295727307, 2.009341700039479, 0.4]
toilet_suite_C[0].rotation = [0, 0, 0]
hand_dryer_B[0].position = [4.493047601522147, 2.70458027558588, 0.16]
hand_dryer_B[0].rotation = [0, 0, 0]
wall_signage_A[0].position = [2.882598437567024, 3.4038007816342057, 0.3]
wall_signage_A[0].rotation = [0, 0, 0]
wall_signage_B[0].position = [5.699280360834978, 2.957637031366204, 0.3]
wall_signage_B[0].rotation = [0, 0, 0]
wall_waste_bin_B[0].position = [2.792619531463748, 3.0730050918912815, 0.25]
wall_waste_bin_B[0].rotation = [0, 0, 0]
floor_locker_column_B[0].position = [3.6295189920861652, 1.15447879241708, 0.9]
floor_locker_column_B[0].rotation = [0, 0, 0]
toilet_suite_D[0].position = [3.1662447891719845, 0.9689896263519576, 0.4]
toilet_suite_D[0].rotation = [0, 0, 0]
hand_dryer_C[0].position = [2.6485207269396067, 3.7723810409319865, 0.16]
hand_dryer_C[0].rotation = [0, 0, 0]
urinal_row[0].position = [1.1129716545444366, 2.757249216782718, 0.6]
urinal_row[0].rotation = [0, 0, 0]
toilet_suite_A[0].position = [0.4814483699088692, 3.3424688087225145, 0.4]
toilet_suite_A[0].rotation = [0, 0, 0]
toilet_suite_B[0].position = [3.340543180164598, 1.9363121085724555, 0.4]
toilet_suite_B[0].rotation = [0, 0, 0]
wall_mirror_strip[0].position = [1.9093419503405569, 0.25342101096199277, 0.4]
wall_mirror_strip[0].rotation = [0, 0, 0]
hand_dryer_A[0].position = [1.5539770207841173, 2.494430280074262, 0.16]
hand_dryer_A[0].rotation = [0, 0, 0]
cleaning_storage_cabinet[0].position = [0.621690492356926, 0.7556391120730316, 0.9]
cleaning_storage_cabinet[0].rotation = [0, 0, 0]
wall_waste_bin_A[0].position = [5.759908917166166, 1.757778822221262, 0.25]
wall_waste_bin_A[0].rotation = [0, 0, 0]
freestanding_waste_bin_A[0].position = [5.556093945919497, 1.962200826270054, 0.325]
freestanding_waste_bin_A[0].rotation = [0, 0, 0]
full_length_mirror[0].position = [5.5687951472231285, 0.21877621845503015, 0.85]
full_length_mirror[0].rotation = [0, 0, 0]
freestanding_waste_bin_B[0].position = [1.6376944962649298, 2.3802461824294614, 0.325]
freestanding_waste_bin_B[0].rotation = [0, 0, 0]
vanity_under_counter_cabinet[0].position = [2.679601813904033, 2.0547936241767, 0.425]
vanity_under_counter_cabinet[0].rotation = [0, 0, 0]
floor_locker_column_A[0].position = [3.704975766180988, 2.789083242628693, 0.9]
floor_locker_column_A[0].rotation = [0, 0, 0]
toilet_suite_C[0].position = [2.6914657295727307, 2.009341700039479, 0.4]
toilet_suite_C[0].rotation = [0, 0, 0]
hand_dryer_B[0].position = [4.493047601522147, 2.70458027558588, 0.16]
hand_dryer_B[0].rotation = [0, 0, 0]
wall_signage_A[0].position = [2.882598437567024, 3.4038007816342057, 0.3]
wall_signage_A[0].rotation = [0, 0, 0]
wall_signage_B[0].position = [5.699280360834978, 2.957637031366204, 0.3]
wall_signage_B[0].rotation = [0, 0, 0]
wall_waste_bin_B[0].position = [2.792619531463748, 3.0730050918912815, 0.25]
wall_waste_bin_B[0].rotation = [0, 0, 0]
floor_locker_column_B[0].position = [3.6295189920861652, 1.15447879241708, 0.9]
floor_locker_column_B[0].rotation = [0, 0, 0]
toilet_suite_D[0].position = [3.1662447891719845, 0.9689896263519576, 0.4]
toilet_suite_D[0].rotation = [0, 0, 0]
hand_dryer_C[0].position = [2.6485207269396067, 3.7723810409319865, 0.16]
hand_dryer_C[0].rotation = [0, 0, 0]
urinal_row[0].position = [1.1129716545444366, 2.757249216782718, 0.6]
urinal_row[0].rotation = [0, 0, 0]

solver.constraints = []

# The supplied boundary is x=0..6, y=0..5.
# Reserve x=3.28..4.48, y=0..1.50 for the entrance and its approach.
# Toilets occupy the north wall, washing facilities the west wall,
# and storage the southwest wall. All coordinates are bounding-box centers.
#
# IDs o0000/o0001/o0011 correspond to toilet suites A/B/C;
# o0006/o0010/o0016 correspond to bin A / locker A / locker B.

layout_specs = [
    # asset, center position, inward-facing yaw (degrees), supporting wall
    (toilet_suite_A, [2.00, 4.65, 0.40], -90, 2),
    (toilet_suite_B, [1.00, 4.65, 0.40], -90, 2),
    (toilet_suite_C, [3.00, 4.65, 0.40], -90, 2),
    (toilet_suite_D, [4.00, 4.65, 0.40], -90, 2),

    (vanity_under_counter_cabinet, [0.30, 2.60, 0.425], 0, 3),
    # Wall-mounted above the vanity, with 0.25 m between counter and mirror.
    (wall_mirror_strip, [0.02, 2.60, 1.50], 0, 3),

    (hand_dryer_A, [0.10, 0.90, 1.25], 0, 3),
    (hand_dryer_B, [0.10, 4.15, 1.25], 0, 3),
    (hand_dryer_C, [5.90, 1.90, 1.25], 180, 1),

    # These bins are wall mounted below their associated dryers.
    (wall_waste_bin_A, [0.12, 0.90, 0.40], 0, 3),
    (wall_waste_bin_B, [5.88, 1.90, 0.40], 180, 1),

    (floor_locker_column_B, [0.90, 0.25, 0.90], 90, 0),
    (freestanding_waste_bin_A, [1.375, 0.25, 0.325], 90, None),
    (floor_locker_column_A, [1.85, 0.25, 0.90], 90, 0),
    (cleaning_storage_cabinet, [2.75, 0.275, 0.90], 90, 0),

    (full_length_mirror, [5.98, 0.65, 0.85], 180, 1),
    (freestanding_waste_bin_B, [5.825, 1.25, 0.325], 180, 1),

    (wall_signage_A, [4.85, 0.015, 1.60], 90, 0),
    (wall_signage_B, [5.00, 4.985, 1.70], -90, 2),
    (urinal_row, [5.80, 3.40, 0.60], 180, 1),
]

for asset_group, center, yaw_degrees, wall_index in layout_specs:
    instance = asset_group[0]
    instance.position = list(center)
    instance.rotation = [0, 0, radians(yaw_degrees)]

    # Exact anchors preserve the nonoverlapping layout, wall-mounting heights,
    # entrance clearance, and ordering requirements during adjustment.
    solver.distance_constraint(
        instance,
        AssetInstance(position=list(center)),
        min_distance=0,
        max_distance=0,
        weight=10,
    )

    # An inward-facing target provides an orientation constraint for every asset.
    heading = radians(yaw_degrees)
    solver.point_towards(
        instance,
        AssetInstance(position=[
            center[0] + cos(heading),
            center[1] + sin(heading),
            center[2],
        ]),
    )

    if wall_index is not None:
        solver.against_wall(instance, walls[wall_index])

# A lies midway between B and C along the north wall.
# Pair distances and common headings reinforce this ordering.
for outer_suite in (toilet_suite_B, toilet_suite_C):
    solver.distance_constraint(
        toilet_suite_A[0], outer_suite[0], 1.0, 1.0, weight=10
    )
    solver.align_with(outer_suite[0], toilet_suite_A[0])

solver.distance_constraint(
    toilet_suite_B[0], toilet_suite_C[0], 2.0, 2.0, weight=10
)
solver.align_with(toilet_suite_D[0], toilet_suite_A[0])

# The bin is centered between the two lockers. Each locker has a 0.10 m
# horizontal bounding-box gap to the bin, satisfying the <=0.20 m criterion.
# Constraints measure 3D center distance, so include the 0.575 m height offset
# rather than incorrectly imposing a 0.20 m center-to-center distance.
locker_bin_center_distance = (0.475**2 + 0.575**2) ** 0.5
for locker_group in (floor_locker_column_B, floor_locker_column_A):
    solver.distance_constraint(
        locker_group[0],
        freestanding_waste_bin_A[0],
        locker_bin_center_distance,
        locker_bin_center_distance,
        weight=10,
    )
    solver.align_with(locker_group[0], freestanding_waste_bin_A[0])

solver.distance_constraint(
    floor_locker_column_B[0], floor_locker_column_A[0],
    0.95, 0.95, weight=10,
)

# Reinforce the vanity/mirror relationship without putting the wall-mounted
# mirror on the countertop. No loose countertop objects are present.
solver.align_with(wall_mirror_strip[0], vanity_under_counter_cabinet[0])
mirror_vanity_center_distance = (0.28**2 + 1.075**2) ** 0.5
solver.distance_constraint(
    wall_mirror_strip[0],
    vanity_under_counter_cabinet[0],
    mirror_vanity_center_distance,
    mirror_vanity_center_distance,
)

solver.constraints = []
freestanding_waste_bin_A[0].position = [1.375, 0.25, 0.32499998807907104]
freestanding_waste_bin_A[0].rotation = [0, 0, 1.5927874750809192]
freestanding_waste_bin_A[0].optimize = 2
toilet_suite_B[0].position = [1.0, 4.650000095367432, 0.4000000059604645]
toilet_suite_B[0].rotation = [0, 0, -1.5707962828923738]
toilet_suite_B[0].optimize = 2
wall_waste_bin_B[0].position = [5.880000114440918, 1.899999976158142, 0.25]
wall_waste_bin_B[0].rotation = [0, 0, -3.1415926099469953]
wall_waste_bin_B[0].optimize = 2
toilet_suite_A[0].position = [2.0, 4.649999618530273, 0.4000000059604645]
toilet_suite_A[0].rotation = [0, 0, -1.570796283323389]
toilet_suite_A[0].optimize = 2
hand_dryer_A[0].position = [0.10000000894069672, 0.8999999761581421, 0.1599999964237213]
hand_dryer_A[0].rotation = [0, 0, 4.322821720581806e-08]
hand_dryer_A[0].optimize = 2
vanity_under_counter_cabinet[0].position = [0.30000004172325134, 2.5999999046325684, 0.42500001192092896]
vanity_under_counter_cabinet[0].rotation = [0, 0, 2.9360216688226564e-08]
vanity_under_counter_cabinet[0].optimize = 2
wall_waste_bin_A[0].position = [0.12000000476837158, 0.8999999761581421, 0.25]
wall_waste_bin_A[0].rotation = [0, 0, 4.3192586857414946e-08]
wall_waste_bin_A[0].optimize = 2
wall_signage_A[0].position = [4.849999904632568, 0.015000000596046448, 0.30000001192092896]
wall_signage_A[0].rotation = [0, 0, 1.5707963696583889]
wall_signage_A[0].optimize = 2
floor_locker_column_B[0].position = [1.5167425870895386, 0.9816835522651672, 0.8999999761581421]
floor_locker_column_B[0].rotation = [0, 0, 1.570796367678899]
floor_locker_column_B[0].optimize = 2
urinal_row[0].position = [5.799999713897705, 3.4000000953674316, 0.6000000238418579]
urinal_row[0].rotation = [0, 0, -3.1415926292591445]
urinal_row[0].optimize = 2
toilet_suite_C[0].position = [3.0, 4.650000095367432, 0.4000000059604645]
toilet_suite_C[0].rotation = [0, 0, -1.5707962828923738]
toilet_suite_C[0].optimize = 2
hand_dryer_C[0].position = [5.900000095367432, 1.899999976158142, 0.1599999964237213]
hand_dryer_C[0].rotation = [0, 0, -3.1415926099391043]
hand_dryer_C[0].optimize = 2
freestanding_waste_bin_B[0].position = [5.824999809265137, 1.25, 0.32499998807907104]
freestanding_waste_bin_B[0].rotation = [0, 0, -3.141592609932279]
freestanding_waste_bin_B[0].optimize = 2
wall_signage_B[0].position = [5.0, 4.984999656677246, 0.30000001192092896]
wall_signage_B[0].rotation = [0, 0, -1.5707962831879632]
wall_signage_B[0].optimize = 2
wall_mirror_strip[0].position = [0.020000001415610313, 2.5999999046325684, 0.4000000059604645]
wall_mirror_strip[0].rotation = [0, 0, 2.7636045966936147e-08]
wall_mirror_strip[0].optimize = 2
toilet_suite_D[0].position = [4.0, 4.649999618530273, 0.4000000059604645]
toilet_suite_D[0].rotation = [0, 0, -1.570796282941001]
toilet_suite_D[0].optimize = 2
hand_dryer_B[0].position = [0.10000000894069672, 4.150000095367432, 0.1599999964237213]
hand_dryer_B[0].rotation = [0, 0, 4.322821720581806e-08]
hand_dryer_B[0].optimize = 2
floor_locker_column_A[0].position = [2.119472026824951, 0.2501775622367859, 0.8999999761581421]
floor_locker_column_A[0].rotation = [0, 0, 1.5707963700847145]
floor_locker_column_A[0].optimize = 2
full_length_mirror[0].position = [5.979999542236328, 0.6499999761581421, 0.8500000238418579]
full_length_mirror[0].rotation = [0, 0, -3.1415926099654494]
full_length_mirror[0].optimize = 2
cleaning_storage_cabinet[0].position = [2.75, 0.27500003576278687, 0.8999999761581421]
cleaning_storage_cabinet[0].rotation = [0, 0, 1.5707963656202284]
cleaning_storage_cabinet[0].optimize = 2

