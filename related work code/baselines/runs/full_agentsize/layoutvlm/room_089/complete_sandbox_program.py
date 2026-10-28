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
    Wall(corner1=[11.77, 0.00, 0.00], corner2=[11.76, 0.34, 0.00]),
    Wall(corner1=[11.76, 0.34, 0.00], corner2=[11.22, 0.89, 0.00]),
    Wall(corner1=[11.22, 0.89, 0.00], corner2=[8.34, 3.77, 0.00]),
    Wall(corner1=[8.34, 3.77, 0.00], corner2=[4.22, 3.77, 0.00]),
    Wall(corner1=[4.22, 3.77, 0.00], corner2=[3.44, 3.77, 0.00]),
    Wall(corner1=[3.44, 3.77, 0.00], corner2=[0.55, 0.89, 0.00]),
    Wall(corner1=[0.55, 0.89, 0.00], corner2=[0.01, 0.34, 0.00]),
    Wall(corner1=[0.01, 0.34, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[11.77, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
cabinet_A = Assets(description="cabinet", size=[0.62, 2.40, 0.90], placements=[AssetInstance() for _ in range(1)])
refrigerator = Assets(description="refrigerator", size=[0.76, 0.91, 1.78], placements=[AssetInstance() for _ in range(1)])
bottle_A = Assets(description="bottle", size=[0.08, 0.08, 0.28], placements=[AssetInstance() for _ in range(1)])
box = Assets(description="box", size=[0.20, 0.30, 0.12], placements=[AssetInstance() for _ in range(1)])
plate = Assets(description="plate", size=[0.27, 0.27, 0.03], placements=[AssetInstance() for _ in range(1)])
dishwasher = Assets(description="dishwasher", size=[0.60, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="bottle", size=[0.07, 0.07, 0.24], placements=[AssetInstance() for _ in range(1)])
bottle_C = Assets(description="bottle", size=[0.09, 0.09, 0.30], placements=[AssetInstance() for _ in range(1)])
food = Assets(description="food", size=[0.16, 0.22, 0.10], placements=[AssetInstance() for _ in range(1)])
pan_A = Assets(description="pan", size=[0.28, 0.46, 0.09], placements=[AssetInstance() for _ in range(1)])
bottle_D = Assets(description="bottle", size=[0.08, 0.08, 0.26], placements=[AssetInstance() for _ in range(1)])
bottle_E = Assets(description="bottle", size=[0.07, 0.07, 0.22], placements=[AssetInstance() for _ in range(1)])
bottle_F = Assets(description="bottle", size=[0.10, 0.10, 0.31], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.62, 2.80, 0.90], placements=[AssetInstance() for _ in range(1)])
faucet = Assets(description="faucet", size=[0.25, 0.08, 0.38], placements=[AssetInstance() for _ in range(1)])
cup = Assets(description="cup", size=[0.12, 0.09, 0.10], placements=[AssetInstance() for _ in range(1)])
bottle_G = Assets(description="bottle", size=[0.08, 0.08, 0.27], placements=[AssetInstance() for _ in range(1)])
bottle_H = Assets(description="bottle", size=[0.07, 0.07, 0.23], placements=[AssetInstance() for _ in range(1)])
lamp = Assets(description="lamp", size=[0.18, 0.32, 0.35], placements=[AssetInstance() for _ in range(1)])
pan_B = Assets(description="pan", size=[0.30, 0.50, 0.10], placements=[AssetInstance() for _ in range(1)])

cabinet_A[0].instance_id = 'cabinet_A_0'
refrigerator[0].instance_id = 'refrigerator_0'
bottle_A[0].instance_id = 'bottle_A_0'
box[0].instance_id = 'box_0'
plate[0].instance_id = 'plate_0'
dishwasher[0].instance_id = 'dishwasher_0'
bottle_B[0].instance_id = 'bottle_B_0'
bottle_C[0].instance_id = 'bottle_C_0'
food[0].instance_id = 'food_0'
pan_A[0].instance_id = 'pan_A_0'
bottle_D[0].instance_id = 'bottle_D_0'
bottle_E[0].instance_id = 'bottle_E_0'
bottle_F[0].instance_id = 'bottle_F_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
faucet[0].instance_id = 'faucet_0'
cup[0].instance_id = 'cup_0'
bottle_G[0].instance_id = 'bottle_G_0'
bottle_H[0].instance_id = 'bottle_H_0'
lamp[0].instance_id = 'lamp_0'
pan_B[0].instance_id = 'pan_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'
walls[8].instance_id = 'walls_8'

cabinet_A[0].position = [1.0323715762747132, 1.3540837832545773, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
refrigerator[0].position = [4.619248676326995, 0.30509160835907384, 0.89]
refrigerator[0].rotation = [0, 0, 0]
bottle_A[0].position = [2.2111209121988487, 2.374416540577088, 0.14]
bottle_A[0].rotation = [0, 0, 0]
box[0].position = [6.988029129611963, 1.9267188243544846, 0.06]
box[0].rotation = [0, 0, 0]
plate[0].position = [9.659213018368192, 0.3649347637325043, 0.015]
plate[0].rotation = [0, 0, 0]
dishwasher[0].position = [8.023402312341146, 2.757130220684533, 0.425]
dishwasher[0].rotation = [0, 0, 0]
bottle_B[0].position = [5.199699486622067, 3.651513994656137, 0.12]
bottle_B[0].rotation = [0, 0, 0]
bottle_C[0].position = [6.379404965213249, 1.2179273369894543, 0.15]
bottle_C[0].rotation = [0, 0, 0]
food[0].position = [11.330405241941365, 0.29216139204760305, 0.05]
food[0].rotation = [0, 0, 0]
pan_A[0].position = [5.31831908388152, 2.5938562059929104, 0.045]
pan_A[0].rotation = [0, 0, 0]
bottle_D[0].position = [6.330434629433658, 1.946585818545727, 0.13]
bottle_D[0].rotation = [0, 0, 0]
bottle_E[0].position = [4.519611865108496, 0.21000612825700757, 0.11]
bottle_E[0].rotation = [0, 0, 0]
bottle_F[0].position = [8.49962615057669, 2.93745940537298, 0.155]
bottle_F[0].rotation = [0, 0, 0]
cabinet_B[0].position = [9.387476905726226, 0.0016671629477249133, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
faucet[0].position = [4.554672565279512, 0.22439016249102922, 0.19]
faucet[0].rotation = [0, 0, 0]
cup[0].position = [3.486538871477909, 2.947213590884906, 0.05]
cup[0].rotation = [0, 0, 0]
bottle_G[0].position = [7.2920270201515445, 0.8129518286914996, 0.135]
bottle_G[0].rotation = [0, 0, 0]
bottle_H[0].position = [5.514546737132915, 0.6910729998801844, 0.115]
bottle_H[0].rotation = [0, 0, 0]
lamp[0].position = [2.9021745873021154, 2.499903457768491, 0.175]
lamp[0].rotation = [0, 0, 0]
pan_B[0].position = [10.236376145696417, 0.3781753301479796, 0.05]
pan_B[0].rotation = [0, 0, 0]
cabinet_A[0].position = [1.0323715762747132, 1.3540837832545773, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
refrigerator[0].position = [4.619248676326995, 0.30509160835907384, 0.89]
refrigerator[0].rotation = [0, 0, 0]
bottle_A[0].position = [2.2111209121988487, 2.374416540577088, 0.14]
bottle_A[0].rotation = [0, 0, 0]
box[0].position = [6.988029129611963, 1.9267188243544846, 0.06]
box[0].rotation = [0, 0, 0]
plate[0].position = [9.659213018368192, 0.3649347637325043, 0.015]
plate[0].rotation = [0, 0, 0]
dishwasher[0].position = [8.023402312341146, 2.757130220684533, 0.425]
dishwasher[0].rotation = [0, 0, 0]
bottle_B[0].position = [5.199699486622067, 3.651513994656137, 0.12]
bottle_B[0].rotation = [0, 0, 0]
bottle_C[0].position = [6.379404965213249, 1.2179273369894543, 0.15]
bottle_C[0].rotation = [0, 0, 0]
food[0].position = [11.330405241941365, 0.29216139204760305, 0.05]
food[0].rotation = [0, 0, 0]
pan_A[0].position = [5.31831908388152, 2.5938562059929104, 0.045]
pan_A[0].rotation = [0, 0, 0]
bottle_D[0].position = [6.330434629433658, 1.946585818545727, 0.13]
bottle_D[0].rotation = [0, 0, 0]
bottle_E[0].position = [4.519611865108496, 0.21000612825700757, 0.11]
bottle_E[0].rotation = [0, 0, 0]
bottle_F[0].position = [8.49962615057669, 2.93745940537298, 0.155]
bottle_F[0].rotation = [0, 0, 0]
cabinet_B[0].position = [9.387476905726226, 0.0016671629477249133, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
faucet[0].position = [4.554672565279512, 0.22439016249102922, 0.19]
faucet[0].rotation = [0, 0, 0]
cup[0].position = [3.486538871477909, 2.947213590884906, 0.05]
cup[0].rotation = [0, 0, 0]
bottle_G[0].position = [7.2920270201515445, 0.8129518286914996, 0.135]
bottle_G[0].rotation = [0, 0, 0]
bottle_H[0].position = [5.514546737132915, 0.6910729998801844, 0.115]
bottle_H[0].rotation = [0, 0, 0]
lamp[0].position = [2.9021745873021154, 2.499903457768491, 0.175]
lamp[0].rotation = [0, 0, 0]
pan_B[0].position = [10.236376145696417, 0.3781753301479796, 0.05]
pan_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the floor-standing kitchen units along the unobstructed section of
# the bottom wall. This leaves the door at x=1.14 and the window near x=10.70
# clear. At 90 degrees, the long horizontal dimension of each cabinet runs
# parallel to the wall and its front faces into the room (+y).
cabinet_A[0].position = [5.00, 0.31, 0.45]
cabinet_A[0].rotation = [0, 0, radians(90)]

dishwasher[0].position = [6.50, 0.30, 0.425]
dishwasher[0].rotation = [0, 0, radians(90)]

cabinet_B[0].position = [8.20, 0.31, 0.45]
cabinet_B[0].rotation = [0, 0, radians(90)]

refrigerator[0].position = [3.345, 0.38, 0.89]
refrigerator[0].rotation = [0, 0, radians(90)]

# A fixed orientation reference keeps all wall units parallel and facing +y.
south_wall_orientation = AssetInstance(
    position=[5.00, 1.00, 0.00],
    rotation=[0, 0, radians(90)]
)

# The cabinet and dishwasher are directly adjacent. Their center separation
# must account for their projected half-widths (1.20 m and 0.30 m); a center
# distance of 1.50--1.70 m corresponds to a surface gap of 0--0.20 m.
solver.distance_constraint(
    cabinet_A[0], dishwasher[0],
    min_distance=1.50, max_distance=1.70, weight=10
)
solver.against_wall(cabinet_A[0], walls[8])
solver.align_with(cabinet_A[0], south_wall_orientation)

solver.against_wall(dishwasher[0], walls[8])
solver.align_with(dishwasher[0], south_wall_orientation)

solver.against_wall(cabinet_B[0], walls[8])
solver.align_with(cabinet_B[0], south_wall_orientation)

solver.against_wall(refrigerator[0], walls[8])
solver.align_with(refrigerator[0], south_wall_orientation)

# Initial placements for the small objects. They are split between the two
# cabinet worktops, with enough spacing to prevent their footprints from
# overlapping.
bottle_A[0].position = [4.10, 0.10, 1.04]
bottle_A[0].rotation = [0, 0, radians(90)]

box[0].position = [4.65, 0.18, 0.96]
box[0].rotation = [0, 0, radians(90)]

plate[0].position = [4.75, 0.47, 0.915]
plate[0].rotation = [0, 0, radians(90)]

bottle_B[0].position = [5.15, 0.12, 1.02]
bottle_B[0].rotation = [0, 0, radians(90)]

bottle_C[0].position = [5.45, 0.14, 1.05]
bottle_C[0].rotation = [0, 0, radians(90)]

food[0].position = [5.85, 0.16, 0.95]
food[0].rotation = [0, 0, radians(90)]

pan_A[0].position = [4.15, 0.36, 0.945]
pan_A[0].rotation = [0, 0, radians(90)]

bottle_D[0].position = [5.25, 0.45, 1.03]
bottle_D[0].rotation = [0, 0, radians(90)]

bottle_E[0].position = [5.58, 0.45, 1.01]
bottle_E[0].rotation = [0, 0, radians(90)]

bottle_F[0].position = [5.95, 0.45, 1.055]
bottle_F[0].rotation = [0, 0, radians(90)]

pan_B[0].position = [7.10, 0.38, 0.95]
pan_B[0].rotation = [0, 0, radians(90)]

faucet[0].position = [7.55, 0.15, 1.09]
faucet[0].rotation = [0, 0, radians(90)]

cup[0].position = [7.85, 0.14, 0.95]
cup[0].rotation = [0, 0, radians(90)]

bottle_G[0].position = [8.15, 0.14, 1.035]
bottle_G[0].rotation = [0, 0, radians(90)]

bottle_H[0].position = [8.45, 0.14, 1.015]
bottle_H[0].rotation = [0, 0, radians(90)]

lamp[0].position = [8.85, 0.17, 1.075]
lamp[0].rotation = [0, 0, radians(90)]


# Add support, position, and orientation constraints for every worktop object.
# Exact fixed-point constraints preserve the deliberately non-overlapping
# arrangement, while on_top_of keeps each object's vertical placement valid.
def constrain_worktop_object(asset_instance, support, target_position):
    solver.on_top_of(asset_instance, support)
    target = AssetInstance(
        position=target_position,
        rotation=[0, 0, radians(90)]
    )
    solver.distance_constraint(
        asset_instance, target,
        min_distance=0.0, max_distance=0.0, weight=10
    )
    solver.align_with(asset_instance, south_wall_orientation)


constrain_worktop_object(bottle_A[0], cabinet_A[0], [4.10, 0.10, 1.04])
constrain_worktop_object(box[0], cabinet_A[0], [4.65, 0.18, 0.96])
constrain_worktop_object(plate[0], cabinet_A[0], [4.75, 0.47, 0.915])
constrain_worktop_object(bottle_B[0], cabinet_A[0], [5.15, 0.12, 1.02])
constrain_worktop_object(bottle_C[0], cabinet_A[0], [5.45, 0.14, 1.05])
constrain_worktop_object(food[0], cabinet_A[0], [5.85, 0.16, 0.95])
constrain_worktop_object(pan_A[0], cabinet_A[0], [4.15, 0.36, 0.945])
constrain_worktop_object(bottle_D[0], cabinet_A[0], [5.25, 0.45, 1.03])
constrain_worktop_object(bottle_E[0], cabinet_A[0], [5.58, 0.45, 1.01])
constrain_worktop_object(bottle_F[0], cabinet_A[0], [5.95, 0.45, 1.055])

constrain_worktop_object(pan_B[0], cabinet_B[0], [7.10, 0.38, 0.95])
constrain_worktop_object(faucet[0], cabinet_B[0], [7.55, 0.15, 1.09])
constrain_worktop_object(cup[0], cabinet_B[0], [7.85, 0.14, 0.95])
constrain_worktop_object(bottle_G[0], cabinet_B[0], [8.15, 0.14, 1.035])
constrain_worktop_object(bottle_H[0], cabinet_B[0], [8.45, 0.14, 1.015])
constrain_worktop_object(lamp[0], cabinet_B[0], [8.85, 0.17, 1.075])

solver.constraints = []
bottle_E[0].position = [5.579999923706055, 0.44999998807907104, 1.0099999904632568]
bottle_E[0].rotation = [0, 0, 1.5833626980517244]
bottle_E[0].optimize = 2
refrigerator[0].position = [3.3450000286102295, 0.3799997866153717, 0.8899999856948853]
refrigerator[0].rotation = [0, 0, 1.5707964428579195]
refrigerator[0].optimize = 2
bottle_H[0].position = [8.449999809265137, 0.14000000059604645, 1.0149999856948853]
bottle_H[0].rotation = [0, 0, 1.5833626980517244]
bottle_H[0].optimize = 2
plate[0].position = [4.75, 0.4699999988079071, 0.9149999618530273]
plate[0].rotation = [0, 0, 1.5833626980517244]
plate[0].optimize = 2
faucet[0].position = [7.550000190734863, 0.15000000596046448, 1.0899999141693115]
faucet[0].rotation = [0, 0, 1.5833626980517244]
faucet[0].optimize = 2
pan_B[0].position = [7.099999904632568, 0.3799999952316284, 0.949999988079071]
pan_B[0].rotation = [0, 0, 1.5833626980517244]
pan_B[0].optimize = 2
bottle_G[0].position = [8.149999618530273, 0.14000000059604645, 1.034999966621399]
bottle_G[0].rotation = [0, 0, 1.5833626980517244]
bottle_G[0].optimize = 2
cabinet_B[0].position = [8.199999809265137, 0.3099993169307709, 0.44999998807907104]
cabinet_B[0].rotation = [0, 0, 1.5707957953808946]
cabinet_B[0].optimize = 2
bottle_F[0].position = [5.949999809265137, 0.44999998807907104, 1.0549999475479126]
bottle_F[0].rotation = [0, 0, 1.5833626980517244]
bottle_F[0].optimize = 2
bottle_D[0].position = [5.25, 0.44999998807907104, 1.0299999713897705]
bottle_D[0].rotation = [0, 0, 1.5833626980517244]
bottle_D[0].optimize = 2
cup[0].position = [7.849999904632568, 0.14000000059604645, 0.949999988079071]
cup[0].rotation = [0, 0, 1.5833626980517244]
cup[0].optimize = 2
bottle_B[0].position = [5.150000095367432, 0.11999999731779099, 1.0199999809265137]
bottle_B[0].rotation = [0, 0, 1.5833626980517244]
bottle_B[0].optimize = 2
box[0].position = [4.650000095367432, 0.18000000715255737, 0.9599999785423279]
box[0].rotation = [0, 0, 1.5833626980517244]
box[0].optimize = 2
lamp[0].position = [8.850000381469727, 0.17000000178813934, 1.0749999284744263]
lamp[0].rotation = [0, 0, 1.5833626980517244]
lamp[0].optimize = 2
bottle_C[0].position = [5.449999809265137, 0.14000000059604645, 1.0499999523162842]
bottle_C[0].rotation = [0, 0, 1.5833626980517244]
bottle_C[0].optimize = 2
bottle_A[0].position = [4.099999904632568, 0.10000000149011612, 1.0399999618530273]
bottle_A[0].rotation = [0, 0, 1.5833626980517244]
bottle_A[0].optimize = 2
cabinet_A[0].position = [5.0, 0.31000059843063354, 0.44999998807907104]
cabinet_A[0].rotation = [0, 0, 1.5707967542383487]
cabinet_A[0].optimize = 2
dishwasher[0].position = [6.5, 0.3000001907348633, 0.42500001192092896]
dishwasher[0].rotation = [0, 0, 1.5707964228928257]
dishwasher[0].optimize = 2
food[0].position = [5.849999904632568, 0.1599999964237213, 0.949999988079071]
food[0].rotation = [0, 0, 1.5833626980517244]
food[0].optimize = 2
pan_A[0].position = [4.150000095367432, 0.36000001430511475, 0.9449999928474426]
pan_A[0].rotation = [0, 0, 1.5833626980517244]
pan_A[0].optimize = 2

