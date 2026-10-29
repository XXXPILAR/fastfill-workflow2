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
    Wall(corner1=[2.71, 0.00, 0.00], corner2=[2.70, 0.29, 0.00]),
    Wall(corner1=[2.70, 0.29, 0.00], corner2=[1.25, 1.75, 0.00]),
    Wall(corner1=[1.25, 1.75, 0.00], corner2=[0.79, 2.20, 0.00]),
    Wall(corner1=[0.79, 2.20, 0.00], corner2=[0.00, 2.21, 0.00]),
    Wall(corner1=[0.00, 2.21, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.71, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
sink = Assets(description="sink", size=[0.48, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
shelf = Assets(description="shelf", size=[0.18, 0.55, 0.04], placements=[AssetInstance() for _ in range(1)])
toilet = Assets(description="toilet", size=[0.68, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
bottle_A = Assets(description="bottle", size=[0.07, 0.07, 0.22], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="bottle", size=[0.06, 0.06, 0.18], placements=[AssetInstance() for _ in range(1)])
bottle_C = Assets(description="bottle", size=[0.06, 0.08, 0.20], placements=[AssetInstance() for _ in range(1)])

sink[0].instance_id = 'sink_0'
shelf[0].instance_id = 'shelf_0'
toilet[0].instance_id = 'toilet_0'
bottle_A[0].instance_id = 'bottle_A_0'
bottle_B[0].instance_id = 'bottle_B_0'
bottle_C[0].instance_id = 'bottle_C_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

sink[0].position = [1.3636458197538008, 0.8197746647640508, 0.425]
sink[0].rotation = [0, 0, 0]
shelf[0].position = [1.8979717797903104, 0.6868304363674095, 0.02]
shelf[0].rotation = [0, 0, 0]
toilet[0].position = [0.0014640359200416516, 1.1863260476801156, 0.39]
toilet[0].rotation = [0, 0, 0]
bottle_A[0].position = [1.0925066184234762, 1.8790160124974769, 0.11]
bottle_A[0].rotation = [0, 0, 0]
bottle_B[0].position = [0.5125267084995362, 0.4529614568006083, 0.09]
bottle_B[0].rotation = [0, 0, 0]
bottle_C[0].position = [2.305056757697988, 0.6644599326994224, 0.1]
bottle_C[0].rotation = [0, 0, 0]
sink[0].position = [1.3636458197538008, 0.8197746647640508, 0.425]
sink[0].rotation = [0, 0, 0]
shelf[0].position = [1.8979717797903104, 0.6868304363674095, 0.02]
shelf[0].rotation = [0, 0, 0]
toilet[0].position = [0.0014640359200416516, 1.1863260476801156, 0.39]
toilet[0].rotation = [0, 0, 0]
bottle_A[0].position = [1.0925066184234762, 1.8790160124974769, 0.11]
bottle_A[0].rotation = [0, 0, 0]
bottle_B[0].position = [0.5125267084995362, 0.4529614568006083, 0.09]
bottle_B[0].rotation = [0, 0, 0]
bottle_C[0].position = [2.305056757697988, 0.6644599326994224, 0.1]
bottle_C[0].rotation = [0, 0, 0]

solver.constraints = []

from math import atan2, sqrt

# Use the solid portion of the west wall, below its window.
# The sink faces into the room; its back is flush with x=0.
sink[0].position = [0.24, 1.20, 0.425]
sink[0].rotation = [0, 0, 0]

# Rest the shallow shelf on the rear of the sink as a toiletries ledge.
# Their surfaces touch (zero clearance, hence within 0.10 m); their
# bounding-box centers are farther apart because both assets have thickness.
shelf[0].position = [0.09, 1.20, 0.87]
shelf[0].rotation = [0, 0, 0]

# Keep the toilet to the east of the door and point it toward the sink.
# Its rotated footprint remains inside the diagonal boundary and leaves
# the doorway and the central approach clear.
toilet[0].position = [1.65, 0.40, 0.39]
toilet[0].rotation = [
    0, 0, atan2(1.20 - 0.40, 0.24 - 1.65)
]

# Space all three bottles along the shelf, with their bases at z=0.89.
bottle_A[0].position = [0.09, 1.02, 1.00]
bottle_A[0].rotation = [0, 0, 0]
bottle_B[0].position = [0.09, 1.20, 0.98]
bottle_B[0].rotation = [0, 0, 0]
bottle_C[0].position = [0.09, 1.38, 0.99]
bottle_C[0].rotation = [0, 0, 0]

# Primary semantic constraints first.
solver.against_wall(sink[0], walls[4])
solver.point_towards(
    sink[0], AssetInstance(position=[1.24, 1.20, 0.425])
)
solver.point_towards(toilet[0], sink[0])

solver.on_top_of(shelf[0], sink[0])
solver.against_wall(shelf[0], walls[4])
solver.align_with(shelf[0], sink[0])

for bottle_asset in (bottle_A, bottle_B, bottle_C):
    solver.on_top_of(bottle_asset[0], shelf[0])
    solver.align_with(bottle_asset[0], shelf[0])

# Preserve the selected positions with fixed-point constraints. In
# particular, these preserve the doorway clearance and the individual
# bottle offsets rather than allowing every bottle to center on the shelf.
for placed_instance in (
    sink[0], shelf[0], toilet[0],
    bottle_A[0], bottle_B[0], bottle_C[0],
):
    solver.distance_constraint(
        placed_instance,
        AssetInstance(position=list(placed_instance.position)),
        0, 0,
        weight=10,
    )

# Center distances encode the intended surface contact/support geometry;
# they are not mistaken for the requested surface-to-surface clearance.
solver.distance_constraint(
    shelf[0], sink[0],
    sqrt(0.15**2 + 0.445**2),
    sqrt(0.15**2 + 0.445**2),
    weight=10,
)

# Each bottle remains on its own part of the ledge.
for bottle_asset in (bottle_A, bottle_B, bottle_C):
    support_distance = sqrt(sum(
        (bottle_asset[0].position[axis] - shelf[0].position[axis]) ** 2
        for axis in range(3)
    ))
    solver.distance_constraint(
        bottle_asset[0], shelf[0],
        support_distance, support_distance,
        weight=10,
    )

# Maintain separation between neighboring bottles.
solver.distance_constraint(bottle_A[0], bottle_B[0], 0.12, None)
solver.distance_constraint(bottle_B[0], bottle_C[0], 0.12, None)
solver.distance_constraint(bottle_C[0], bottle_A[0], 0.24, None)

solver.constraints = []
bottle_A[0].position = [0.08000004291534424, 1.0099999904632568, 1.0]
bottle_A[0].rotation = [0, 0, 0.03230815780634596]
bottle_A[0].optimize = 2
bottle_C[0].position = [0.08000004291534424, 1.3899999856948853, 0.9900000095367432]
bottle_C[0].rotation = [0, 0, 0.03230815780634596]
bottle_C[0].optimize = 2
shelf[0].position = [0.09285436570644379, 1.2000000476837158, 0.8700000047683716]
shelf[0].rotation = [0, 0, 0.036762952900975525]
shelf[0].optimize = 2
sink[0].position = [0.24446804821491241, 1.2000000476837158, 0.42500001192092896]
sink[0].rotation = [0, 0, 0.014983916920112477]
sink[0].optimize = 2
bottle_B[0].position = [0.08000004291534424, 1.2000000476837158, 0.9800000190734863]
bottle_B[0].rotation = [0, 0, 0.03230815780634596]
bottle_B[0].optimize = 2
toilet[0].position = [1.649999976158142, 0.4000000059604645, 0.38999998569488525]
toilet[0].rotation = [0, 0, 2.634931777988116]
toilet[0].optimize = 2

