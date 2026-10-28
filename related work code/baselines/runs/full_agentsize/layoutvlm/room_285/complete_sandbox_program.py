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
    Wall(corner1=[0.94, 1.16, 0.00], corner2=[0.94, 0.00, 0.00]),
    Wall(corner1=[0.94, 0.00, 0.00], corner2=[1.98, 0.00, 0.00]),
    Wall(corner1=[1.98, 0.00, 0.00], corner2=[1.98, 1.16, 0.00]),
    Wall(corner1=[1.98, 1.16, 0.00], corner2=[5.33, 1.16, 0.00]),
    Wall(corner1=[5.33, 1.16, 0.00], corner2=[5.33, 1.77, 0.00]),
    Wall(corner1=[5.33, 1.77, 0.00], corner2=[5.76, 1.77, 0.00]),
    Wall(corner1=[5.76, 1.77, 0.00], corner2=[5.76, 4.23, 0.00]),
    Wall(corner1=[5.76, 4.23, 0.00], corner2=[5.33, 4.23, 0.00]),
    Wall(corner1=[5.33, 4.23, 0.00], corner2=[5.33, 4.83, 0.00]),
    Wall(corner1=[5.33, 4.83, 0.00], corner2=[0.00, 4.83, 0.00]),
    Wall(corner1=[0.00, 4.83, 0.00], corner2=[0.00, 1.16, 0.00]),
    Wall(corner1=[0.00, 1.16, 0.00], corner2=[0.94, 1.16, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
sofa_A = Assets(description="sofa", size=[0.90, 2.10, 0.85], placements=[AssetInstance() for _ in range(1)])
table_A = Assets(description="table", size=[0.55, 0.55, 0.50], placements=[AssetInstance() for _ in range(1)])
table_B = Assets(description="table", size=[0.65, 1.20, 0.42], placements=[AssetInstance() for _ in range(1)])
sofa_B = Assets(description="sofa", size=[0.90, 1.60, 0.85], placements=[AssetInstance() for _ in range(1)])
sofa_C = Assets(description="sofa", size=[0.95, 2.20, 0.88], placements=[AssetInstance() for _ in range(1)])
table_C = Assets(description="table", size=[0.70, 1.25, 0.42], placements=[AssetInstance() for _ in range(1)])
sofa_D = Assets(description="sofa", size=[0.90, 1.70, 0.85], placements=[AssetInstance() for _ in range(1)])

sofa_A[0].instance_id = 'sofa_A_0'
table_A[0].instance_id = 'table_A_0'
table_B[0].instance_id = 'table_B_0'
sofa_B[0].instance_id = 'sofa_B_0'
sofa_C[0].instance_id = 'sofa_C_0'
table_C[0].instance_id = 'table_C_0'
sofa_D[0].instance_id = 'sofa_D_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'
walls[8].instance_id = 'walls_8'
walls[9].instance_id = 'walls_9'
walls[10].instance_id = 'walls_10'
walls[11].instance_id = 'walls_11'

sofa_A[0].position = [1.011182436363382, 2.885305972256882, 0.425]
sofa_A[0].rotation = [0, 0, 0]
table_A[0].position = [0.1327416652798841, 4.62600894475716, 0.25]
table_A[0].rotation = [0, 0, 0]
table_B[0].position = [0.9923386840130687, 0.8867326961499202, 0.21]
table_B[0].rotation = [0, 0, 0]
sofa_B[0].position = [3.893996775063647, 3.8674458558174583, 0.425]
sofa_B[0].rotation = [0, 0, 0]
sofa_C[0].position = [1.9247920407219508, 2.067988920998232, 0.44]
sofa_C[0].rotation = [0, 0, 0]
table_C[0].position = [0.5857003427998334, 3.34804306317915, 0.21]
table_C[0].rotation = [0, 0, 0]
sofa_D[0].position = [1.957742132975072, 2.765491716480292, 0.425]
sofa_D[0].rotation = [0, 0, 0]
sofa_A[0].position = [1.011182436363382, 2.885305972256882, 0.425]
sofa_A[0].rotation = [0, 0, 0]
table_A[0].position = [0.1327416652798841, 4.62600894475716, 0.25]
table_A[0].rotation = [0, 0, 0]
table_B[0].position = [0.9923386840130687, 0.8867326961499202, 0.21]
table_B[0].rotation = [0, 0, 0]
sofa_B[0].position = [3.893996775063647, 3.8674458558174583, 0.425]
sofa_B[0].rotation = [0, 0, 0]
sofa_C[0].position = [1.9247920407219508, 2.067988920998232, 0.44]
sofa_C[0].rotation = [0, 0, 0]
table_C[0].position = [0.5857003427998334, 3.34804306317915, 0.21]
table_C[0].rotation = [0, 0, 0]
sofa_D[0].position = [1.957742132975072, 2.765491716480292, 0.425]
sofa_D[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the furniture in the main rectangular portion of the room. The
# entrance corridors and the floor areas immediately inside all five doors
# remain unobstructed.

# sofa_A (o0000) is positioned between table_A (o0001) on its west side and
# table_C (o0005) on its east side.
sofa_A[0].position = [2.10, 2.75, 0.425]
sofa_A[0].rotation = [0, 0, radians(0)]

table_A[0].position = [1.15, 2.75, 0.25]
table_A[0].rotation = [0, 0, radians(0)]

table_C[0].position = [3.50, 2.75, 0.21]
table_C[0].rotation = [0, 0, radians(90)]

# The larger table occupies the lower-right area without entering either
# bottom-door approach or overlapping the nearby seating.
table_B[0].position = [4.80, 1.82, 0.21]
table_B[0].rotation = [0, 0, radians(144)]

# sofa_B forms the eastern side of the seating group and faces table_C.
sofa_B[0].position = [5.15, 3.35, 0.425]
sofa_B[0].rotation = [0, 0, radians(180)]

# sofa_C (o0004) is placed against the long top wall, away from the top-left
# doorway, and faces inward toward table_C.
sofa_C[0].position = [3.50, 4.355, 0.44]
sofa_C[0].rotation = [0, 0, radians(-90)]

# sofa_D (o0006) sits south of table_C (o0005) and faces it.
sofa_D[0].position = [3.50, 1.75, 0.425]
sofa_D[0].rotation = [0, 0, radians(90)]


# Fixed anchors preserve the selected clearances and keep the solver from
# moving furniture into doorway circulation zones.
sofa_A_anchor = AssetInstance(position=[2.10, 2.75, 0.425])
table_A_anchor = AssetInstance(position=[1.15, 2.75, 0.25])
table_B_anchor = AssetInstance(position=[4.80, 1.82, 0.21])
sofa_B_anchor = AssetInstance(position=[5.15, 3.35, 0.425])
sofa_C_anchor = AssetInstance(position=[3.50, 4.355, 0.44])
table_C_anchor = AssetInstance(position=[3.50, 2.75, 0.21])
sofa_D_anchor = AssetInstance(position=[3.50, 1.75, 0.425])

# Position constraints are specified first because the doorway clearances and
# non-overlapping arrangement are the highest-priority requirements.
solver.distance_constraint(sofa_A[0], sofa_A_anchor, 0, 0, weight=10)
solver.distance_constraint(table_A[0], table_A_anchor, 0, 0, weight=10)
solver.distance_constraint(table_B[0], table_B_anchor, 0, 0, weight=10)
solver.distance_constraint(sofa_B[0], sofa_B_anchor, 0, 0, weight=10)

# The top-wall constraint explicitly satisfies the requirement that sofa_C
# be against a wall; its matching anchor selects the clear section of that wall.
solver.against_wall(sofa_C[0], walls[9])
solver.distance_constraint(sofa_C[0], sofa_C_anchor, 0, 0, weight=10)

solver.distance_constraint(table_C[0], table_C_anchor, 0, 0, weight=10)
solver.distance_constraint(sofa_D[0], sofa_D_anchor, 0, 0, weight=10)

# Orientation constraints for every asset. These establish a coherent seating
# group centered on table_C while retaining the specified initial rotations.
solver.point_towards(sofa_A[0], table_C[0])
solver.align_with(table_A[0], sofa_A[0])
solver.point_towards(table_B[0], table_C[0])
solver.point_towards(sofa_B[0], table_C[0])
solver.point_towards(sofa_C[0], table_C[0])
solver.align_with(table_C[0], sofa_D[0])
solver.point_towards(sofa_D[0], table_C[0])

# Relational constraints encode the requested ordering:
# table_A -- sofa_A -- table_C.
solver.distance_constraint(table_A[0], sofa_A[0], 0.95, 0.95, weight=5)
solver.distance_constraint(sofa_A[0], table_C[0], 1.40, 1.40, weight=5)

# Keep each of the surrounding pieces at its planned functional distance from
# the central table if the room geometry is adjusted.
solver.distance_constraint(sofa_D[0], table_C[0], 1.00, 1.00, weight=5)
solver.distance_constraint(sofa_C[0], table_C[0], 1.605, 1.605, weight=5)
solver.distance_constraint(sofa_B[0], table_C[0], 1.756, 1.756, weight=5)
solver.distance_constraint(table_B[0], table_C[0], 1.598, 1.598, weight=2)

solver.constraints = []
sofa_C[0].position = [3.509999990463257, 4.350729942321777, 0.4399999976158142]
sofa_C[0].rotation = [0, 0, -1.5651448823011982]
sofa_C[0].optimize = 2
sofa_A[0].position = [2.0999999046325684, 2.75, 0.42500001192092896]
sofa_A[0].rotation = [0, 0, 0.01884955539881635]
sofa_A[0].optimize = 2
table_B[0].position = [4.810000419616699, 1.8391356468200684, 0.20999999344348907]
table_B[0].rotation = [0, 0, 2.5258404956509137]
table_B[0].optimize = 2
table_C[0].position = [3.5, 2.75, 0.20999999344348907]
table_C[0].rotation = [0, 0, 1.6013368550562506]
table_C[0].optimize = 2
sofa_D[0].position = [3.5, 1.75, 0.42500001192092896]
sofa_D[0].rotation = [0, 0, 1.586504290712113]
sofa_D[0].optimize = 2
table_A[0].position = [1.1399999856948853, 2.75, 0.25]
table_A[0].rotation = [0, 0, 0.02278736617577962]
table_A[0].optimize = 2
sofa_B[0].position = [5.160000324249268, 3.359999895095825, 0.42500001192092896]
sofa_B[0].rotation = [0, 0, -3.118800888728785]
sofa_B[0].optimize = 2

