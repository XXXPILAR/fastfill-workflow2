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
    Wall(corner1=[0.00, 3.88, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.56, 0.00, 0.00]),
    Wall(corner1=[4.56, 0.00, 0.00], corner2=[4.56, 3.88, 0.00]),
    Wall(corner1=[4.56, 3.88, 0.00], corner2=[0.00, 3.88, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
wardrobe_A = Assets(description="wardrobe", size=[0.60, 1.20, 2.10], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="chair", size=[0.62, 0.58, 0.88], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.62, 0.58, 0.88], placements=[AssetInstance() for _ in range(1)])
wardrobe_B = Assets(description="wardrobe", size=[0.60, 1.00, 2.10], placements=[AssetInstance() for _ in range(1)])
wardrobe_C = Assets(description="wardrobe", size=[0.60, 1.20, 2.10], placements=[AssetInstance() for _ in range(1)])

wardrobe_A[0].instance_id = 'wardrobe_A_0'
chair_A[0].instance_id = 'chair_A_0'
chair_B[0].instance_id = 'chair_B_0'
wardrobe_B[0].instance_id = 'wardrobe_B_0'
wardrobe_C[0].instance_id = 'wardrobe_C_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

wardrobe_A[0].position = [1.0301970691448095, 1.7541823646377301, 1.05]
wardrobe_A[0].rotation = [0, 0, 0]
chair_A[0].position = [3.703055626594285, 3.0300479421928155, 0.44]
chair_A[0].rotation = [0, 0, 0]
chair_B[0].position = [2.004880163998336, 0.9897815906040806, 0.44]
chair_B[0].rotation = [0, 0, 0]
wardrobe_B[0].position = [3.8335794995696237, 0.8977955011859757, 1.05]
wardrobe_B[0].rotation = [0, 0, 0]
wardrobe_C[0].position = [4.3401398479948075, 0.6281891036634186, 1.05]
wardrobe_C[0].rotation = [0, 0, 0]
wardrobe_A[0].position = [1.0301970691448095, 1.7541823646377301, 1.05]
wardrobe_A[0].rotation = [0, 0, 0]
chair_A[0].position = [3.703055626594285, 3.0300479421928155, 0.44]
chair_A[0].rotation = [0, 0, 0]
chair_B[0].position = [2.004880163998336, 0.9897815906040806, 0.44]
chair_B[0].rotation = [0, 0, 0]
wardrobe_B[0].position = [3.8335794995696237, 0.8977955011859757, 1.05]
wardrobe_B[0].rotation = [0, 0, 0]
wardrobe_C[0].position = [4.3401398479948075, 0.6281891036634186, 1.05]
wardrobe_C[0].rotation = [0, 0, 0]

solver.constraints = []

# Map from the criteria's object IDs:
# o0000 = wardrobe_A, o0001 = chair_A, o0002 = chair_B,
# o0003 = wardrobe_B, o0004 = wardrobe_C.
#
# Arrange all five assets along the upper wall. Their rotated widths sum to
# exactly 4.56 m, so adjacent bounding boxes touch without overlapping.
# All fronts face into the room (-y). This also keeps the entrance area clear
# and places wardrobe_C above, rather than in front of, the right-wall window.

wardrobe_A[0].position = [0.60, 3.58, 1.05]
wardrobe_A[0].rotation = [0, 0, radians(-90)]

chair_A[0].position = [1.49, 3.57, 0.44]
chair_A[0].rotation = [0, 0, radians(-90)]

wardrobe_B[0].position = [2.28, 3.58, 1.05]
wardrobe_B[0].rotation = [0, 0, radians(-90)]

chair_B[0].position = [3.07, 3.57, 0.44]
chair_B[0].rotation = [0, 0, radians(-90)]

wardrobe_C[0].position = [3.96, 3.58, 1.05]
wardrobe_C[0].rotation = [0, 0, radians(-90)]


# The upper wall is the primary positional reference for this compact row.
solver.against_wall(wardrobe_A[0], walls[3])
solver.against_wall(chair_A[0], walls[3])
solver.against_wall(wardrobe_B[0], walls[3])
solver.against_wall(chair_B[0], walls[3])
solver.against_wall(wardrobe_C[0], walls[3])

# Fix wardrobe_A's front toward the room and use it as the orientation
# reference for the remaining assets.
wardrobe_A_facing_target = AssetInstance(position=[0.60, 2.58, 1.05])
solver.point_towards(wardrobe_A[0], wardrobe_A_facing_target)

solver.align_with(chair_A[0], wardrobe_A[0])
solver.align_with(wardrobe_B[0], wardrobe_A[0])
solver.align_with(chair_B[0], wardrobe_A[0])
solver.align_with(wardrobe_C[0], wardrobe_A[0])

# Keep chair_A between wardrobe_A and wardrobe_B. At these center distances,
# the three neighboring bounding boxes meet without intersecting.
solver.distance_constraint(
    chair_A[0], wardrobe_A[0],
    min_distance=0.89, max_distance=0.89, weight=10
)
solver.distance_constraint(
    chair_A[0], wardrobe_B[0],
    min_distance=0.79, max_distance=0.79, weight=10
)

# Keep chair_B immediately beside wardrobe_B. The center distance is 0.79 m:
# 0.50 m (half of wardrobe_B's rotated width) plus 0.29 m (half of the
# chair's rotated width), giving a surface-to-surface gap of 0.00 m and
# therefore satisfying the requested maximum gap of 0.20 m.
solver.distance_constraint(
    chair_B[0], wardrobe_B[0],
    min_distance=0.79, max_distance=0.99, weight=10
)

# Keep chair_B between wardrobe_A and wardrobe_C and prevent wardrobe_C from
# drifting away from the ordered row.
solver.distance_constraint(
    chair_B[0], wardrobe_C[0],
    min_distance=0.89, max_distance=0.89, weight=10
)
solver.distance_constraint(
    wardrobe_C[0], wardrobe_A[0],
    min_distance=3.36, max_distance=3.36, weight=10
)

# Preserve the central wardrobe's place in the sequence as the layout is
# adjusted for physical feasibility.
solver.distance_constraint(
    wardrobe_B[0], wardrobe_A[0],
    min_distance=1.68, max_distance=1.68, weight=10
)

solver.constraints = []
wardrobe_A[0].position = [0.6099994778633118, 3.5688014030456543, 1.0499999523162842]
wardrobe_A[0].rotation = [0, 0, -1.5495903270898497]
wardrobe_A[0].optimize = 2
wardrobe_B[0].position = [2.2699999809265137, 3.558129072189331, 1.0499999523162842]
wardrobe_B[0].rotation = [0, 0, -1.5620341087177068]
wardrobe_B[0].optimize = 2
wardrobe_C[0].position = [3.950000047683716, 3.558112621307373, 1.0499999523162842]
wardrobe_C[0].rotation = [0, 0, -1.565144811312652]
wardrobe_C[0].optimize = 2
chair_B[0].position = [3.069999933242798, 3.5600008964538574, 0.4399999976158142]
chair_B[0].rotation = [0, 0, -1.5651448028559958]
chair_B[0].optimize = 2
chair_A[0].position = [1.4900000095367432, 3.5600008964538574, 0.4399999976158142]
chair_A[0].rotation = [0, 0, -1.5651448028559958]
chair_A[0].optimize = 2

