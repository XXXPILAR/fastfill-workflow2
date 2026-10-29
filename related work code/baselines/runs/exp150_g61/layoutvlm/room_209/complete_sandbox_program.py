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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.30, 0.00, 0.00]),
    Wall(corner1=[6.30, 0.00, 0.00], corner2=[6.30, 3.56, 0.00]),
    Wall(corner1=[6.30, 3.56, 0.00], corner2=[0.00, 3.56, 0.00]),
    Wall(corner1=[0.00, 3.56, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
shower_room_A = Assets(description="shower room", size=[0.90, 0.90, 2.10], placements=[AssetInstance() for _ in range(1)])
shower_room_B = Assets(description="shower room", size=[0.90, 1.20, 2.10], placements=[AssetInstance() for _ in range(1)])
tub = Assets(description="tub", size=[1.70, 0.80, 0.60], placements=[AssetInstance() for _ in range(1)])

shower_room_A[0].instance_id = 'shower_room_A_0'
shower_room_B[0].instance_id = 'shower_room_B_0'
tub[0].instance_id = 'tub_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

shower_room_A[0].position = [5.478483215413861, 0.7110878334942838, 1.05]
shower_room_A[0].rotation = [0, 0, 0]
shower_room_B[0].position = [1.4454786013225138, 2.6117582403861945, 1.05]
shower_room_B[0].rotation = [0, 0, 0]
tub[0].position = [3.2268077590571855, 0.9294155779672152, 0.3]
tub[0].rotation = [0, 0, 0]
shower_room_A[0].position = [5.478483215413861, 0.7110878334942838, 1.05]
shower_room_A[0].rotation = [0, 0, 0]
shower_room_B[0].position = [1.4454786013225138, 2.6117582403861945, 1.05]
shower_room_B[0].rotation = [0, 0, 0]
tub[0].position = [3.2268077590571855, 0.9294155779672152, 0.3]
tub[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the solid east wall for both tall shower enclosures, avoiding the
# windows on the other walls. Their entrances face west into the open room.
# The door spans x=2.56..4.76 on the north wall; its approach stays clear.
shower_room_A[0].position = [5.85, 0.65, 1.05]
shower_room_A[0].rotation = [0, 0, radians(180)]

shower_room_B[0].position = [5.85, 2.35, 1.05]
shower_room_B[0].rotation = [0, 0, radians(180)]

# Keep the low tub beneath the south window, with its long dimension
# parallel to the wall and ample access from the north.
tub[0].position = [1.35, 0.40, 0.30]
tub[0].rotation = [0, 0, 0]

# Preserve the chosen wall locations and spacing with fixed center targets.
# All target heights are bounding-box center heights, not floor heights.
solver.distance_constraint(
    shower_room_A[0],
    AssetInstance(position=[5.85, 0.65, 1.05]),
    0, 0, weight=10
)
solver.against_wall(shower_room_A[0], walls[1])
solver.point_towards(
    shower_room_A[0],
    AssetInstance(position=[3.85, 0.65, 1.05])
)

solver.distance_constraint(
    shower_room_B[0],
    AssetInstance(position=[5.85, 2.35, 1.05]),
    0, 0, weight=10
)
solver.against_wall(shower_room_B[0], walls[1])
solver.point_towards(
    shower_room_B[0],
    AssetInstance(position=[3.85, 2.35, 1.05])
)

solver.distance_constraint(
    tub[0],
    AssetInstance(position=[1.35, 0.40, 0.30]),
    0, 0, weight=10
)
solver.against_wall(tub[0], walls[0])
solver.align_with(tub[0], AssetInstance(rotation=[0, 0, 0]))

# The showers have a 0.65 m gap between their footprints.
# Apply separation in both directions so either enclosure remains protected
# if its placement is adjusted.
solver.distance_constraint(shower_room_A[0], shower_room_B[0], 1.70, None)
solver.distance_constraint(shower_room_B[0], shower_room_A[0], 1.70, None)

solver.constraints = []
shower_room_A[0].position = [5.850000858306885, 0.6499999761581421, 1.0499999523162842]
shower_room_A[0].rotation = [0, 0, -3.141592609289907]
shower_room_A[0].optimize = 2
tub[0].position = [1.350000023841858, 0.8500001430511475, 0.30000001192092896]
tub[0].rotation = [0, 0, 1.5707959264556663]
tub[0].optimize = 2
shower_room_B[0].position = [5.850000381469727, 2.3499999046325684, 1.0499999523162842]
shower_room_B[0].rotation = [0, 0, -3.1415926096466333]
shower_room_B[0].optimize = 2

