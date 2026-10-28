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
toilet_suite_A = Assets(description="toilet suite", size=[0.70, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
toilet_suite_B = Assets(description="toilet suite", size=[0.70, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
wall_mirror_strip = Assets(description="A rectangular light wooden panel in a whitish-gray frame.", size=[0.05, 2.40, 0.80], placements=[AssetInstance() for _ in range(1)])
hand_dryer_A = Assets(description="A round light on a silver mount.", size=[0.20, 0.28, 0.30], placements=[AssetInstance() for _ in range(1)])
cleaning_storage_cabinet = Assets(description="Two stacked locker units that are yellow and gray.", size=[0.50, 0.50, 1.80], placements=[AssetInstance() for _ in range(1)])
wall_waste_bin_A = Assets(description="A cream colored trash can.", size=[0.25, 0.35, 0.50], placements=[AssetInstance() for _ in range(1)])
freestanding_waste_bin_A = Assets(description="a trash can with holes on a metal stand.", size=[0.40, 0.40, 0.75], placements=[AssetInstance() for _ in range(1)])
full_length_mirror = Assets(description="A rectangular mirror in a brown wooden frame.", size=[0.05, 0.70, 1.80], placements=[AssetInstance() for _ in range(1)])
freestanding_waste_bin_B = Assets(description="a trash can with holes on a metal stand.", size=[0.40, 0.40, 0.75], placements=[AssetInstance() for _ in range(1)])
vanity_under_counter_cabinet = Assets(description="A long white cabinet with a white top.", size=[0.60, 2.40, 0.85], placements=[AssetInstance() for _ in range(1)])
floor_locker_column_A = Assets(description="Two stacked locker units that are yellow and gray.", size=[0.50, 0.50, 1.80], placements=[AssetInstance() for _ in range(1)])
toilet_suite_C = Assets(description="toilet suite", size=[0.70, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
hand_dryer_B = Assets(description="A round light on a silver mount.", size=[0.20, 0.28, 0.30], placements=[AssetInstance() for _ in range(1)])
wall_signage_A = Assets(description="A chalk billboard with some prices on it.", size=[0.04, 0.80, 0.60], placements=[AssetInstance() for _ in range(1)])
wall_signage_B = Assets(description="A chalk billboard with some prices on it.", size=[0.04, 0.80, 0.60], placements=[AssetInstance() for _ in range(1)])
wall_waste_bin_B = Assets(description="A cream colored trash can.", size=[0.25, 0.35, 0.50], placements=[AssetInstance() for _ in range(1)])
floor_locker_column_B = Assets(description="Two stacked locker units that are yellow and gray.", size=[0.50, 0.50, 1.80], placements=[AssetInstance() for _ in range(1)])
toilet_suite_D = Assets(description="toilet suite", size=[0.70, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
hand_dryer_C = Assets(description="A round light on a silver mount.", size=[0.20, 0.28, 0.30], placements=[AssetInstance() for _ in range(1)])
urinal_row = Assets(description="White toilet with tall tank and rust stains.", size=[0.55, 2.40, 1.10], placements=[AssetInstance() for _ in range(1)])

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

toilet_suite_A[0].position = [3.473727218547551, 1.108348380707647, 0.39]
toilet_suite_A[0].rotation = [0, 0, 0]
toilet_suite_B[0].position = [0.1486907767695309, 0.47103118863769833, 0.39]
toilet_suite_B[0].rotation = [0, 0, 0]
wall_mirror_strip[0].position = [4.509910079185562, 2.419290832409456, 0.4]
wall_mirror_strip[0].rotation = [0, 0, 0]
hand_dryer_A[0].position = [2.552147402269257, 1.4286295324272669, 0.15]
hand_dryer_A[0].rotation = [0, 0, 0]
cleaning_storage_cabinet[0].position = [0.071651932248046, 2.2935592859673375, 0.9]
cleaning_storage_cabinet[0].rotation = [0, 0, 0]
wall_waste_bin_A[0].position = [2.8374819871052273, 2.620543996783555, 0.25]
wall_waste_bin_A[0].rotation = [0, 0, 0]
freestanding_waste_bin_A[0].position = [0.24864830319340903, 0.7731225512326573, 0.375]
freestanding_waste_bin_A[0].rotation = [0, 0, 0]
full_length_mirror[0].position = [5.508328043423829, 3.7839503570365163, 0.9]
full_length_mirror[0].rotation = [0, 0, 0]
freestanding_waste_bin_B[0].position = [2.8574319406604705, 2.4707025400020246, 0.375]
freestanding_waste_bin_B[0].rotation = [0, 0, 0]
vanity_under_counter_cabinet[0].position = [3.7946327265403026, 3.419104437391933, 0.425]
vanity_under_counter_cabinet[0].rotation = [0, 0, 0]
floor_locker_column_A[0].position = [0.5812255123655301, 1.0428310242042882, 0.9]
floor_locker_column_A[0].rotation = [0, 0, 0]
toilet_suite_C[0].position = [1.4174297030663017, 1.5847004568775769, 0.39]
toilet_suite_C[0].rotation = [0, 0, 0]
hand_dryer_B[0].position = [1.6104364441672938, 3.539620031389888, 0.15]
hand_dryer_B[0].rotation = [0, 0, 0]
wall_signage_A[0].position = [2.3780751587197564, 1.960606929800347, 0.3]
wall_signage_A[0].rotation = [0, 0, 0]
wall_signage_B[0].position = [5.216853964833646, 1.6269979930222496, 0.3]
wall_signage_B[0].rotation = [0, 0, 0]
wall_waste_bin_B[0].position = [5.446796214769848, 2.2759072396600892, 0.25]
wall_waste_bin_B[0].rotation = [0, 0, 0]
floor_locker_column_B[0].position = [1.3361954193632901, 2.8077898710727975, 0.9]
floor_locker_column_B[0].rotation = [0, 0, 0]
toilet_suite_D[0].position = [0.4939467361050316, 2.519754420313567, 0.39]
toilet_suite_D[0].rotation = [0, 0, 0]
hand_dryer_C[0].position = [2.8529248403560548, 1.473147500677966, 0.15]
hand_dryer_C[0].rotation = [0, 0, 0]
urinal_row[0].position = [2.184081240630264, 4.9830070115374525, 0.55]
urinal_row[0].rotation = [0, 0, 0]
toilet_suite_A[0].position = [3.473727218547551, 1.108348380707647, 0.39]
toilet_suite_A[0].rotation = [0, 0, 0]
toilet_suite_B[0].position = [0.1486907767695309, 0.47103118863769833, 0.39]
toilet_suite_B[0].rotation = [0, 0, 0]
wall_mirror_strip[0].position = [4.509910079185562, 2.419290832409456, 0.4]
wall_mirror_strip[0].rotation = [0, 0, 0]
hand_dryer_A[0].position = [2.552147402269257, 1.4286295324272669, 0.15]
hand_dryer_A[0].rotation = [0, 0, 0]
cleaning_storage_cabinet[0].position = [0.071651932248046, 2.2935592859673375, 0.9]
cleaning_storage_cabinet[0].rotation = [0, 0, 0]
wall_waste_bin_A[0].position = [2.8374819871052273, 2.620543996783555, 0.25]
wall_waste_bin_A[0].rotation = [0, 0, 0]
freestanding_waste_bin_A[0].position = [0.24864830319340903, 0.7731225512326573, 0.375]
freestanding_waste_bin_A[0].rotation = [0, 0, 0]
full_length_mirror[0].position = [5.508328043423829, 3.7839503570365163, 0.9]
full_length_mirror[0].rotation = [0, 0, 0]
freestanding_waste_bin_B[0].position = [2.8574319406604705, 2.4707025400020246, 0.375]
freestanding_waste_bin_B[0].rotation = [0, 0, 0]
vanity_under_counter_cabinet[0].position = [3.7946327265403026, 3.419104437391933, 0.425]
vanity_under_counter_cabinet[0].rotation = [0, 0, 0]
floor_locker_column_A[0].position = [0.5812255123655301, 1.0428310242042882, 0.9]
floor_locker_column_A[0].rotation = [0, 0, 0]
toilet_suite_C[0].position = [1.4174297030663017, 1.5847004568775769, 0.39]
toilet_suite_C[0].rotation = [0, 0, 0]
hand_dryer_B[0].position = [1.6104364441672938, 3.539620031389888, 0.15]
hand_dryer_B[0].rotation = [0, 0, 0]
wall_signage_A[0].position = [2.3780751587197564, 1.960606929800347, 0.3]
wall_signage_A[0].rotation = [0, 0, 0]
wall_signage_B[0].position = [5.216853964833646, 1.6269979930222496, 0.3]
wall_signage_B[0].rotation = [0, 0, 0]
wall_waste_bin_B[0].position = [5.446796214769848, 2.2759072396600892, 0.25]
wall_waste_bin_B[0].rotation = [0, 0, 0]
floor_locker_column_B[0].position = [1.3361954193632901, 2.8077898710727975, 0.9]
floor_locker_column_B[0].rotation = [0, 0, 0]
toilet_suite_D[0].position = [0.4939467361050316, 2.519754420313567, 0.39]
toilet_suite_D[0].rotation = [0, 0, 0]
hand_dryer_C[0].position = [2.8529248403560548, 1.473147500677966, 0.15]
hand_dryer_C[0].rotation = [0, 0, 0]
urinal_row[0].position = [2.184081240630264, 4.9830070115374525, 0.55]
urinal_row[0].rotation = [0, 0, 0]

solver.constraints = []

# The fixtures are grouped along the perimeter, leaving the central circulation
# area and the 1 m doorway at x=3.38..4.38 on the bottom wall unobstructed.
# Floor-mounted heights are half of each asset's z dimension.

# Toilet row along the top wall. toilet_suite_A (o0000) is positioned
# between toilet_suite_B (o0001) and toilet_suite_C (o0011).
toilet_suite_B[0].position = [0.55, 4.65, 0.39]
toilet_suite_B[0].rotation = [0, 0, radians(-90)]

toilet_suite_A[0].position = [1.15, 4.65, 0.39]
toilet_suite_A[0].rotation = [0, 0, radians(-90)]

toilet_suite_C[0].position = [1.75, 4.65, 0.39]
toilet_suite_C[0].rotation = [0, 0, radians(-90)]

toilet_suite_D[0].position = [2.35, 4.65, 0.39]
toilet_suite_D[0].rotation = [0, 0, radians(-90)]

# A long vanity and matching mirror occupy the left wall.
vanity_under_counter_cabinet[0].position = [0.30, 2.15, 0.425]
vanity_under_counter_cabinet[0].rotation = [0, 0, radians(0)]

wall_mirror_strip[0].position = [0.025, 2.15, 1.45]
wall_mirror_strip[0].rotation = [0, 0, radians(0)]

# Wall bins are mounted above the floor on the upper part of the left wall.
wall_waste_bin_A[0].position = [0.125, 3.70, 0.75]
wall_waste_bin_A[0].rotation = [0, 0, radians(0)]

wall_waste_bin_B[0].position = [0.125, 4.10, 0.75]
wall_waste_bin_B[0].rotation = [0, 0, radians(0)]

# The locker/bin group occupies the bottom-left corner. The first freestanding
# bin (o0006) lies between locker B (o0016) and locker A (o0010).
floor_locker_column_B[0].position = [0.30, 0.25, 0.90]
floor_locker_column_B[0].rotation = [0, 0, radians(90)]

freestanding_waste_bin_A[0].position = [0.775, 0.25, 0.375]
freestanding_waste_bin_A[0].rotation = [0, 0, radians(90)]

floor_locker_column_A[0].position = [1.25, 0.25, 0.90]
floor_locker_column_A[0].rotation = [0, 0, radians(90)]

cleaning_storage_cabinet[0].position = [1.90, 0.25, 0.90]
cleaning_storage_cabinet[0].rotation = [0, 0, radians(90)]

freestanding_waste_bin_B[0].position = [2.50, 0.25, 0.375]
freestanding_waste_bin_B[0].rotation = [0, 0, radians(90)]

# This narrow mirror fits on the bottom wall to the left of the doorway.
full_length_mirror[0].position = [2.95, 0.025, 1.00]
full_length_mirror[0].rotation = [0, 0, radians(90)]

# Hand dryers are distributed along the lower part of the right wall.
hand_dryer_A[0].position = [5.90, 0.75, 1.25]
hand_dryer_A[0].rotation = [0, 0, radians(180)]

hand_dryer_B[0].position = [5.90, 1.20, 1.25]
hand_dryer_B[0].rotation = [0, 0, radians(180)]

hand_dryer_C[0].position = [5.90, 1.65, 1.25]
hand_dryer_C[0].rotation = [0, 0, radians(180)]

# The urinal row occupies the upper section of the right wall.
urinal_row[0].position = [5.725, 3.50, 0.55]
urinal_row[0].rotation = [0, 0, radians(180)]

# Signage is mounted high on the otherwise unused section of the top wall.
wall_signage_A[0].position = [3.30, 4.98, 1.65]
wall_signage_A[0].rotation = [0, 0, radians(-90)]

wall_signage_B[0].position = [4.30, 4.98, 1.65]
wall_signage_B[0].rotation = [0, 0, radians(-90)]


# Fixed inward-facing reference points are used for orientation constraints.
room_center = AssetInstance(position=[3.00, 2.50, 1.00])
top_inward_point = AssetInstance(position=[3.00, 3.00, 1.00])
left_inward_point = AssetInstance(position=[1.50, 2.50, 1.00])
right_inward_point = AssetInstance(position=[4.50, 2.50, 1.00])
bottom_inward_point = AssetInstance(position=[3.00, 1.50, 1.00])

# Preserve the required toilet ordering first. Equal distances to the adjacent
# toilets, together with the wall constraints and initial coordinates, keep
# toilet_suite_A centered between toilet_suite_B and toilet_suite_C.
solver.distance_constraint(
    toilet_suite_A[0], toilet_suite_B[0], 0.55, 0.65, weight=10
)
solver.distance_constraint(
    toilet_suite_A[0], toilet_suite_C[0], 0.55, 0.65, weight=10
)

# All toilets remain against the top wall and face into the room.
solver.against_wall(toilet_suite_B[0], walls[2])
solver.point_towards(toilet_suite_B[0], top_inward_point)
solver.against_wall(toilet_suite_A[0], walls[2])
solver.point_towards(toilet_suite_A[0], top_inward_point)
solver.against_wall(toilet_suite_C[0], walls[2])
solver.point_towards(toilet_suite_C[0], top_inward_point)
solver.against_wall(toilet_suite_D[0], walls[2])
solver.point_towards(toilet_suite_D[0], top_inward_point)

# Keep o0006 between the two locker columns. The 0.45 m minimum is the sum of
# their half-widths, while the 0.65 m maximum permits no more than 0.20 m of
# edge-to-edge clearance. The o0010-to-o0006 constraint is weighted strongly.
solver.distance_constraint(
    floor_locker_column_A[0],
    freestanding_waste_bin_A[0],
    0.45,
    0.65,
    weight=10,
)
solver.distance_constraint(
    freestanding_waste_bin_A[0],
    floor_locker_column_B[0],
    0.45,
    0.65,
    weight=10,
)

# Exact anchors retain the left-to-right locker/bin ordering and prevent the
# freestanding group from drifting into the doorway.
solver.distance_constraint(
    floor_locker_column_B[0],
    AssetInstance(position=[0.30, 0.25, 0.90]),
    0,
    0,
    weight=10,
)
solver.point_towards(floor_locker_column_B[0], bottom_inward_point)

solver.distance_constraint(
    freestanding_waste_bin_A[0],
    AssetInstance(position=[0.775, 0.25, 0.375]),
    0,
    0,
    weight=10,
)
solver.point_towards(freestanding_waste_bin_A[0], bottom_inward_point)

solver.distance_constraint(
    floor_locker_column_A[0],
    AssetInstance(position=[1.25, 0.25, 0.90]),
    0,
    0,
    weight=10,
)
solver.point_towards(floor_locker_column_A[0], bottom_inward_point)

solver.distance_constraint(
    cleaning_storage_cabinet[0],
    AssetInstance(position=[1.90, 0.25, 0.90]),
    0,
    0,
    weight=10,
)
solver.point_towards(cleaning_storage_cabinet[0], bottom_inward_point)

solver.distance_constraint(
    freestanding_waste_bin_B[0],
    AssetInstance(position=[2.50, 0.25, 0.375]),
    0,
    0,
    weight=10,
)
solver.point_towards(freestanding_waste_bin_B[0], room_center)

# Left-wall fixtures face inward.
solver.against_wall(vanity_under_counter_cabinet[0], walls[3])
solver.point_towards(vanity_under_counter_cabinet[0], left_inward_point)

solver.against_wall(wall_mirror_strip[0], walls[3])
solver.point_towards(wall_mirror_strip[0], left_inward_point)

solver.against_wall(wall_waste_bin_A[0], walls[3])
solver.point_towards(wall_waste_bin_A[0], left_inward_point)

solver.against_wall(wall_waste_bin_B[0], walls[3])
solver.point_towards(wall_waste_bin_B[0], left_inward_point)

# The full-length mirror is wall-mounted left of the doorway and faces inward.
solver.against_wall(full_length_mirror[0], walls[0])
solver.point_towards(full_length_mirror[0], bottom_inward_point)

# Right-wall fixtures face toward the room.
solver.against_wall(hand_dryer_A[0], walls[1])
solver.point_towards(hand_dryer_A[0], right_inward_point)

solver.against_wall(hand_dryer_B[0], walls[1])
solver.point_towards(hand_dryer_B[0], right_inward_point)

solver.against_wall(hand_dryer_C[0], walls[1])
solver.point_towards(hand_dryer_C[0], right_inward_point)

solver.against_wall(urinal_row[0], walls[1])
solver.point_towards(urinal_row[0], right_inward_point)

# Top-wall signs face inward and remain aligned with one another.
solver.against_wall(wall_signage_A[0], walls[2])
solver.point_towards(wall_signage_A[0], top_inward_point)

solver.against_wall(wall_signage_B[0], walls[2])
solver.point_towards(wall_signage_B[0], top_inward_point)
solver.align_with(wall_signage_B[0], wall_signage_A[0])

solver.constraints = []
hand_dryer_A[0].position = [5.909449577331543, 0.75, 0.15000000596046448]
hand_dryer_A[0].rotation = [0, 0, 3.141023061392903]
hand_dryer_A[0].optimize = 2
hand_dryer_B[0].position = [5.909449577331543, 1.2000000476837158, 0.15000000596046448]
hand_dryer_B[0].rotation = [0, 0, 3.141023061392903]
hand_dryer_B[0].optimize = 2
toilet_suite_B[0].position = [0.550000011920929, 4.6495184898376465, 0.38999998569488525]
toilet_suite_B[0].rotation = [0, 0, -1.5682554052778654]
toilet_suite_B[0].optimize = 2
toilet_suite_C[0].position = [1.75, 4.6495184898376465, 0.38999998569488525]
toilet_suite_C[0].rotation = [0, 0, -1.5682554052778654]
toilet_suite_C[0].optimize = 2
wall_mirror_strip[0].position = [0.026308678090572357, 2.1500000953674316, 0.4000000059604645]
wall_mirror_strip[0].rotation = [0, 0, -0.0005696277190883559]
wall_mirror_strip[0].optimize = 2
floor_locker_column_A[0].position = [1.25, 0.25, 0.8999999761581421]
floor_locker_column_A[0].rotation = [0, 0, 1.5833626980517244]
floor_locker_column_A[0].optimize = 2
full_length_mirror[0].position = [2.950000047683716, 0.016837814822793007, 0.8999999761581421]
full_length_mirror[0].rotation = [0, 0, 1.570226730256177]
full_length_mirror[0].optimize = 2
wall_signage_A[0].position = [3.299999952316284, 4.9885125160217285, 0.30000001192092896]
wall_signage_A[0].rotation = [0, 0, -1.5682554107885098]
wall_signage_A[0].optimize = 2
urinal_row[0].position = [5.723702430725098, 3.5, 0.550000011920929]
urinal_row[0].rotation = [0, 0, 3.1410230267928534]
urinal_row[0].optimize = 2
freestanding_waste_bin_B[0].position = [2.5, 0.25, 0.375]
freestanding_waste_bin_B[0].rotation = [0, 0, 1.5802211042556205]
freestanding_waste_bin_B[0].optimize = 2
toilet_suite_A[0].position = [1.149999976158142, 4.648931980133057, 0.38999998569488525]
toilet_suite_A[0].rotation = [0, 0, -1.5651448028559958]
toilet_suite_A[0].optimize = 2
wall_signage_B[0].position = [4.300000190734863, 4.9885125160217285, 0.30000001192092896]
wall_signage_B[0].rotation = [0, 0, -1.5682554107885098]
wall_signage_B[0].optimize = 2
toilet_suite_D[0].position = [2.3499999046325684, 4.659841537475586, 0.38999998569488525]
toilet_suite_D[0].rotation = [0, 0, -1.5713659189245548]
toilet_suite_D[0].optimize = 2
vanity_under_counter_cabinet[0].position = [0.3012964725494385, 2.1500000953674316, 0.42500001192092896]
vanity_under_counter_cabinet[0].rotation = [0, 0, -0.0005696267969400684]
vanity_under_counter_cabinet[0].optimize = 2
hand_dryer_C[0].position = [5.909449577331543, 1.649999976158142, 0.15000000596046448]
hand_dryer_C[0].rotation = [0, 0, 3.141023061392903]
hand_dryer_C[0].optimize = 2
cleaning_storage_cabinet[0].position = [1.899999976158142, 0.25, 0.8999999761581421]
cleaning_storage_cabinet[0].rotation = [0, 0, 1.5802211042556205]
cleaning_storage_cabinet[0].optimize = 2
freestanding_waste_bin_A[0].position = [0.7749999761581421, 0.25, 0.375]
freestanding_waste_bin_A[0].rotation = [0, 0, 1.586504290712113]
freestanding_waste_bin_A[0].optimize = 2
floor_locker_column_B[0].position = [0.30000001192092896, 0.25, 0.8999999761581421]
floor_locker_column_B[0].rotation = [0, 0, 1.5833626980517244]
floor_locker_column_B[0].optimize = 2
wall_waste_bin_A[0].position = [0.11543098837137222, 3.700000047683716, 0.25]
wall_waste_bin_A[0].rotation = [0, 0, -0.0005695912747381627]
wall_waste_bin_A[0].optimize = 2
wall_waste_bin_B[0].position = [0.11543098837137222, 4.099999904632568, 0.25]
wall_waste_bin_B[0].rotation = [0, 0, -0.0005695912747381627]
wall_waste_bin_B[0].optimize = 2

