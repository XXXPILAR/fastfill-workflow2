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
    Wall(corner1=[0.04, 7.81, 0.00], corner2=[0.00, 7.77, 0.00]),
    Wall(corner1=[0.00, 7.77, 0.00], corner2=[0.00, 5.27, 0.00]),
    Wall(corner1=[0.00, 5.27, 0.00], corner2=[3.67, 0.04, 0.00]),
    Wall(corner1=[3.67, 0.04, 0.00], corner2=[3.71, 0.00, 0.00]),
    Wall(corner1=[3.71, 0.00, 0.00], corner2=[6.52, 0.00, 0.00]),
    Wall(corner1=[6.52, 0.00, 0.00], corner2=[6.56, 0.04, 0.00]),
    Wall(corner1=[6.56, 0.04, 0.00], corner2=[6.56, 7.77, 0.00]),
    Wall(corner1=[6.56, 7.77, 0.00], corner2=[6.52, 7.81, 0.00]),
    Wall(corner1=[6.52, 7.81, 0.00], corner2=[0.04, 7.81, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
cabinet_A = Assets(description="cabinet", size=[0.60, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
bin_A = Assets(description="bin", size=[0.35, 0.35, 0.60], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.60, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
oven_A = Assets(description="oven", size=[0.60, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
cabinet_C = Assets(description="cabinet", size=[0.35, 0.80, 0.75], placements=[AssetInstance() for _ in range(1)])
cup = Assets(description="cup", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
oven_B = Assets(description="oven", size=[0.60, 0.60, 0.60], placements=[AssetInstance() for _ in range(1)])
case = Assets(description="case", size=[0.30, 0.40, 0.15], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
cabinet_D = Assets(description="cabinet", size=[0.60, 1.00, 0.90], placements=[AssetInstance() for _ in range(1)])
sink = Assets(description="sink", size=[0.50, 0.80, 0.22], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="table", size=[0.90, 1.80, 0.75], placements=[AssetInstance() for _ in range(1)])
box = Assets(description="box", size=[0.25, 0.30, 0.20], placements=[AssetInstance() for _ in range(1)])
basket = Assets(description="basket", size=[0.28, 0.35, 0.18], placements=[AssetInstance() for _ in range(1)])
microwave = Assets(description="microwave", size=[0.40, 0.52, 0.31], placements=[AssetInstance() for _ in range(1)])
cabinet_E = Assets(description="cabinet", size=[0.60, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
cabinet_F = Assets(description="cabinet", size=[0.65, 0.65, 0.90], placements=[AssetInstance() for _ in range(1)])
bin_B = Assets(description="bin", size=[0.30, 0.30, 0.45], placements=[AssetInstance() for _ in range(1)])

cabinet_A[0].instance_id = 'cabinet_A_0'
bin_A[0].instance_id = 'bin_A_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
oven_A[0].instance_id = 'oven_A_0'
chair_A[0].instance_id = 'chair_A_0'
chair_B[0].instance_id = 'chair_B_0'
cabinet_C[0].instance_id = 'cabinet_C_0'
cup[0].instance_id = 'cup_0'
oven_B[0].instance_id = 'oven_B_0'
case[0].instance_id = 'case_0'
chair_C[0].instance_id = 'chair_C_0'
cabinet_D[0].instance_id = 'cabinet_D_0'
sink[0].instance_id = 'sink_0'
table[0].instance_id = 'table_0'
box[0].instance_id = 'box_0'
basket[0].instance_id = 'basket_0'
microwave[0].instance_id = 'microwave_0'
cabinet_E[0].instance_id = 'cabinet_E_0'
cabinet_F[0].instance_id = 'cabinet_F_0'
bin_B[0].instance_id = 'bin_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'
walls[8].instance_id = 'walls_8'

cabinet_A[0].position = [4.283597218745142, 1.9485959407980784, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
bin_A[0].position = [5.7588126157581865, 6.841691394801222, 0.3]
bin_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [4.09556278335073, 5.137958577029267, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
oven_A[0].position = [5.680035076492593, 1.8711020902363646, 0.425]
oven_A[0].rotation = [0, 0, 0]
chair_A[0].position = [6.23435357529456, 1.5505285113374254, 0.425]
chair_A[0].rotation = [0, 0, 0]
chair_B[0].position = [0.8383072163218486, 6.389307448331805, 0.425]
chair_B[0].rotation = [0, 0, 0]
cabinet_C[0].position = [3.4756832035409118, 6.849869348113406, 0.375]
cabinet_C[0].rotation = [0, 0, 0]
cup[0].position = [5.051050088114248, 6.05002333665611, 0.05]
cup[0].rotation = [0, 0, 0]
oven_B[0].position = [2.9602218458659757, 6.429504768553825, 0.3]
oven_B[0].rotation = [0, 0, 0]
case[0].position = [1.8970876310660922, 4.8036556530536805, 0.075]
case[0].rotation = [0, 0, 0]
chair_C[0].position = [4.083892242090183, 5.784555144931278, 0.425]
chair_C[0].rotation = [0, 0, 0]
cabinet_D[0].position = [3.6166069475133744, 2.9831709777813846, 0.45]
cabinet_D[0].rotation = [0, 0, 0]
sink[0].position = [4.9428371099766855, 6.779108718228496, 0.11]
sink[0].rotation = [0, 0, 0]
table[0].position = [5.1714584338949985, 1.8629610342507306, 0.375]
table[0].rotation = [0, 0, 0]
box[0].position = [5.4464302602699535, 2.2555436986364428, 0.1]
box[0].rotation = [0, 0, 0]
basket[0].position = [0.22342479871873697, 5.2115323142993555, 0.09]
basket[0].rotation = [0, 0, 0]
microwave[0].position = [2.403143147244174, 4.291151602768419, 0.155]
microwave[0].rotation = [0, 0, 0]
cabinet_E[0].position = [3.9231359028248027, 7.129703968718523, 0.45]
cabinet_E[0].rotation = [0, 0, 0]
cabinet_F[0].position = [3.9472609233600746, 0.5613053907904432, 0.45]
cabinet_F[0].rotation = [0, 0, 0]
bin_B[0].position = [6.368225019698024, 4.719765369141642, 0.225]
bin_B[0].rotation = [0, 0, 0]
cabinet_A[0].position = [4.283597218745142, 1.9485959407980784, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
bin_A[0].position = [5.7588126157581865, 6.841691394801222, 0.3]
bin_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [4.09556278335073, 5.137958577029267, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
oven_A[0].position = [5.680035076492593, 1.8711020902363646, 0.425]
oven_A[0].rotation = [0, 0, 0]
chair_A[0].position = [6.23435357529456, 1.5505285113374254, 0.425]
chair_A[0].rotation = [0, 0, 0]
chair_B[0].position = [0.8383072163218486, 6.389307448331805, 0.425]
chair_B[0].rotation = [0, 0, 0]
cabinet_C[0].position = [3.4756832035409118, 6.849869348113406, 0.375]
cabinet_C[0].rotation = [0, 0, 0]
cup[0].position = [5.051050088114248, 6.05002333665611, 0.05]
cup[0].rotation = [0, 0, 0]
oven_B[0].position = [2.9602218458659757, 6.429504768553825, 0.3]
oven_B[0].rotation = [0, 0, 0]
case[0].position = [1.8970876310660922, 4.8036556530536805, 0.075]
case[0].rotation = [0, 0, 0]
chair_C[0].position = [4.083892242090183, 5.784555144931278, 0.425]
chair_C[0].rotation = [0, 0, 0]
cabinet_D[0].position = [3.6166069475133744, 2.9831709777813846, 0.45]
cabinet_D[0].rotation = [0, 0, 0]
sink[0].position = [4.9428371099766855, 6.779108718228496, 0.11]
sink[0].rotation = [0, 0, 0]
table[0].position = [5.1714584338949985, 1.8629610342507306, 0.375]
table[0].rotation = [0, 0, 0]
box[0].position = [5.4464302602699535, 2.2555436986364428, 0.1]
box[0].rotation = [0, 0, 0]
basket[0].position = [0.22342479871873697, 5.2115323142993555, 0.09]
basket[0].rotation = [0, 0, 0]
microwave[0].position = [2.403143147244174, 4.291151602768419, 0.155]
microwave[0].rotation = [0, 0, 0]
cabinet_E[0].position = [3.9231359028248027, 7.129703968718523, 0.45]
cabinet_E[0].rotation = [0, 0, 0]
cabinet_F[0].position = [3.9472609233600746, 0.5613053907904432, 0.45]
cabinet_F[0].rotation = [0, 0, 0]
bin_B[0].position = [6.368225019698024, 4.719765369141642, 0.225]
bin_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Coordinates follow the supplied wall polygon (rather than recentering it).
# Keep the east-side entrance and its approach clear. Kitchen storage runs
# along the north wall, with dining in the wider central part of the room.
# Each tuple is: asset, center position, yaw in degrees, supporting wall.
layout_specs = [
    (cabinet_A, [4.90, 7.51, 0.45], -90, walls[8]),
    (bin_A,     [0.575, 7.51, 0.30], 0, None),
    (cabinet_B, [3.80, 7.51, 0.45], -90, walls[8]),
    (oven_A,    [3.00, 7.51, 0.425], -90, walls[8]),

    # chair_B is exactly between chair_A and chair_C.
    # The first two chairs face the table; chair_C faces chair_B.
    (chair_A,   [2.50, 5.80, 0.425], -90, None),
    (chair_B,   [3.40, 5.80, 0.425], -90, None),
    (cabinet_C, [0.175, 6.10, 0.375], 0, walls[1]),

    (cup,       [3.15, 4.70, 0.80], 90, None),
    (oven_B,    [1.95, 7.51, 1.20], -90, None),
    (case,      [0.175, 6.10, 0.825], 0, None),
    (chair_C,   [4.30, 5.80, 0.425], 180, None),

    (cabinet_D, [1.95, 7.51, 0.45], -90, walls[8]),
    (sink,      [4.90, 7.51, 1.01], -90, None),
    (table,     [3.40, 4.70, 0.375], 90, None),
    (box,       [6.235, 6.70, 1.00], 180, None),
    (basket,    [1.10, 7.51, 0.99], -90, None),
    (microwave, [3.80, 7.51, 1.055], -90, None),
    (cabinet_E, [1.10, 7.51, 0.45], -90, walls[8]),
    (cabinet_F, [6.235, 6.70, 0.45], 180, walls[6]),
    (bin_B,     [6.36, 3.80, 0.225], 180, None),
]

# Set every placement explicitly. Fixed reference poses preserve the planned
# clearances, the diagonal-boundary clearance, and the unobstructed doorway.
# These are reference points only, not additional physical scene assets.
for asset_group, center_xyz, yaw_degrees, support_wall in layout_specs:
    asset_group[0].position = list(center_xyz)
    asset_group[0].rotation = [0, 0, radians(yaw_degrees)]

    pose_reference = AssetInstance(
        position=list(center_xyz),
        rotation=[0, 0, radians(yaw_degrees)],
    )
    solver.distance_constraint(
        asset_group[0], pose_reference, 0, 0, weight=10
    )

# Prioritize the explicitly requested facing relationship.
solver.point_towards(chair_C[0], chair_B[0])

# Each instance also receives an orientation constraint. Cabinet fronts face
# into the room; the northern run remains below/in front of the window.
for asset_group, center_xyz, yaw_degrees, support_wall in layout_specs:
    orientation_reference = AssetInstance(
        position=list(center_xyz),
        rotation=[0, 0, radians(yaw_degrees)],
    )
    solver.align_with(asset_group[0], orientation_reference)
    if support_wall is not None:
        solver.against_wall(asset_group[0], support_wall)

# All countertop objects are supported, with their bottom faces at the
# corresponding support's top. The second oven occupies its own cabinet.
for upper_group, lower_group in [
    (cup, table),
    (oven_B, cabinet_D),
    (case, cabinet_C),
    (sink, cabinet_A),
    (box, cabinet_F),
    (basket, cabinet_E),
    (microwave, cabinet_B),
]:
    solver.on_top_of(upper_group[0], lower_group[0])
    solver.align_with(upper_group[0], lower_group[0])

# The collinear, anchored chair centers enforce the requested ordering.
# Supplement the anchors with relational spacing constraints.
solver.distance_constraint(chair_B[0], chair_A[0], 0.90, 0.90, weight=10)
solver.distance_constraint(chair_B[0], chair_C[0], 0.90, 0.90, weight=10)
solver.distance_constraint(chair_C[0], chair_A[0], 1.80, 1.80, weight=10)

# bin_A (o0001) sits beside cabinet_E (o0017), not in front of its doors.
# Their horizontal center separation is 0.525 m:
# 0.175 m bin half-width + 0.300 m cabinet half-width + 0.050 m gap.
# Account for the 0.15 m difference in center heights when constraining
# the API's three-dimensional center distance.
bin_cabinet_center_distance = (0.525**2 + 0.15**2) ** 0.5
solver.distance_constraint(
    bin_A[0],
    cabinet_E[0],
    bin_cabinet_center_distance,
    bin_cabinet_center_distance,
    weight=10,
)

solver.constraints = []
microwave[0].position = [3.799999952316284, 7.510000228881836, 1.0549999475479126]
microwave[0].rotation = [0, 0, -1.5698308881472078]
microwave[0].optimize = 2
cabinet_C[0].position = [0.17505794763565063, 6.099999904632568, 0.375]
cabinet_C[0].rotation = [0, 0, -0.00010809600940923044]
cabinet_C[0].optimize = 2
bin_A[0].position = [0.4750436246395111, 7.504179000854492, 0.30000001192092896]
bin_A[0].rotation = [0, 0, 0.01256637125682779]
bin_A[0].optimize = 2
cabinet_D[0].position = [1.9500000476837158, 7.5123515129089355, 0.44999998807907104]
cabinet_D[0].rotation = [0, 0, -1.5709062716141944]
cabinet_D[0].optimize = 2
chair_C[0].position = [4.300000190734863, 5.800000190734863, 0.42500001192092896]
chair_C[0].rotation = [0, 0, -3.122743098190977]
chair_C[0].optimize = 2
basket[0].position = [1.100000023841858, 7.510000228881836, 0.9900000095367432]
basket[0].rotation = [0, 0, -1.5701578475508167]
basket[0].optimize = 2
oven_A[0].position = [3.0, 7.51251220703125, 0.42500001192092896]
oven_A[0].rotation = [0, 0, -1.570858095390821]
oven_A[0].optimize = 2
table[0].position = [3.4000000953674316, 4.699999809265137, 0.375]
table[0].rotation = [0, 0, 1.586504290712113]
table[0].optimize = 2
case[0].position = [0.17499999701976776, 6.099999904632568, 0.824999988079071]
case[0].rotation = [0, 0, 0.0009648088053339892]
case[0].optimize = 2
oven_B[0].position = [1.9500000476837158, 7.510000228881836, 1.2000000476837158]
oven_B[0].rotation = [0, 0, -1.569830874005531]
oven_B[0].optimize = 2
cabinet_F[0].position = [6.237335205078125, 6.699999809265137, 0.44999998807907104]
cabinet_F[0].rotation = [0, 0, 3.141482592654763]
cabinet_F[0].optimize = 2
cabinet_A[0].position = [4.900000095367432, 7.512417793273926, 0.44999998807907104]
cabinet_A[0].rotation = [0, 0, -1.5709062164040788]
cabinet_A[0].optimize = 2
cup[0].position = [3.1500000953674316, 4.699999809265137, 0.800000011920929]
cup[0].rotation = [0, 0, 1.5863481858427249]
cup[0].optimize = 2
sink[0].position = [4.900000095367432, 7.510000228881836, 1.0099999904632568]
sink[0].rotation = [0, 0, -1.5698307920262753]
sink[0].optimize = 2
box[0].position = [6.235000133514404, 6.699999809265137, 1.0]
box[0].rotation = [0, 0, -3.1406271342785574]
box[0].optimize = 2
chair_B[0].position = [3.4000000953674316, 5.800000190734863, 0.42500001192092896]
chair_B[0].rotation = [0, 0, -1.5519467713960802]
chair_B[0].optimize = 2
cabinet_B[0].position = [3.799999952316284, 7.512393474578857, 0.44999998807907104]
cabinet_B[0].rotation = [0, 0, -1.5709062483460472]
cabinet_B[0].optimize = 2
chair_A[0].position = [2.5, 5.800000190734863, 0.42500001192092896]
chair_A[0].rotation = [0, 0, -1.5550883628776802]
chair_A[0].optimize = 2
bin_B[0].position = [6.360000133514404, 3.799999952316284, 0.22499999403953552]
bin_B[0].rotation = [0, 0, -3.1321678761290697]
bin_B[0].optimize = 2
cabinet_E[0].position = [1.100000023841858, 7.512387275695801, 0.44999998807907104]
cabinet_E[0].rotation = [0, 0, -1.5710100219850678]
cabinet_E[0].optimize = 2

