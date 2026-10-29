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
    Wall(corner1=[2.70, 1.15, 0.00], corner2=[0.00, 1.15, 0.00]),
    Wall(corner1=[0.00, 1.15, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.08, 0.00, 0.00]),
    Wall(corner1=[6.08, 0.00, 0.00], corner2=[6.08, 3.43, 0.00]),
    Wall(corner1=[6.08, 3.43, 0.00], corner2=[2.70, 3.43, 0.00]),
    Wall(corner1=[2.70, 3.43, 0.00], corner2=[2.70, 1.15, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
desk = Assets(description="desk", size=[0.75, 1.50, 0.75], placements=[AssetInstance() for _ in range(1)])
sofa = Assets(description="sofa", size=[0.90, 2.10, 0.85], placements=[AssetInstance() for _ in range(1)])
chair = Assets(description="chair", size=[0.65, 0.65, 1.10], placements=[AssetInstance() for _ in range(1)])

desk[0].instance_id = 'desk_0'
sofa[0].instance_id = 'sofa_0'
chair[0].instance_id = 'chair_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

desk[0].position = [4.964814034387031, 1.7121534651558012, 0.375]
desk[0].rotation = [0, 0, 0]
sofa[0].position = [3.9960000056371614, 2.740184943646571, 0.425]
sofa[0].rotation = [0, 0, 0]
chair[0].position = [4.140602570902526, 0.8417715690703937, 0.55]
chair[0].rotation = [0, 0, 0]
desk[0].position = [4.964814034387031, 1.7121534651558012, 0.375]
desk[0].rotation = [0, 0, 0]
sofa[0].position = [3.9960000056371614, 2.740184943646571, 0.425]
sofa[0].rotation = [0, 0, 0]
chair[0].position = [4.140602570902526, 0.8417715690703937, 0.55]
chair[0].rotation = [0, 0, 0]

solver.constraints = []

# Keep the narrow entrance leg completely clear. Place the workspace in the
# southeast portion of the main room, leaving access from the entrance.
desk[0].position = [5.655, 1.10, desk.size[2] / 2]
desk[0].rotation = [0, 0, radians(180)]

# The facing edges have a 0.08 m gap:
# 0.780 m center separation minus 0.375 m desk half-depth
# minus 0.325 m chair half-depth.
chair[0].position = [4.875, 1.10, chair.size[2] / 2]
chair[0].rotation = [0, 0, 0]

# Place the sofa against the north wall, facing south into the room.
# Its rotated footprint is x=[3.34, 5.44], y=[2.53, 3.43].
sofa[0].position = [4.39, 2.98, sofa.size[2] / 2]
sofa[0].rotation = [0, 0, radians(270)]

# Preserve the workspace location and the unobstructed entrance route.
solver.distance_constraint(
    desk[0],
    AssetInstance(position=[5.655, 1.10, desk.size[2] / 2]),
    0, 0, weight=10
)
solver.point_towards(desk[0], chair[0])

# Maintain the close, nonoverlapping working position. Distance constraints
# measure bounding-box centers in 3D, so include the difference in heights.
workspace_center_distance = (
    0.780 ** 2 + ((chair.size[2] - desk.size[2]) / 2) ** 2
) ** 0.5

solver.distance_constraint(
    chair[0], desk[0],
    workspace_center_distance, workspace_center_distance, weight=10
)
solver.point_towards(chair[0], desk[0])
solver.distance_constraint(
    chair[0],
    AssetInstance(position=[4.875, 1.10, chair.size[2] / 2]),
    0, 0, weight=10
)

# Wall contact has priority; the anchor fixes the position along that wall.
solver.against_wall(sofa[0], walls[4])
solver.distance_constraint(
    sofa[0],
    AssetInstance(position=[4.39, 2.98, sofa.size[2] / 2]),
    0, 0, weight=10
)
solver.point_towards(
    sofa[0],
    AssetInstance(position=[4.39, 1.98, sofa.size[2] / 2])
)

# Preserve separation between the seating and working zones.
solver.distance_constraint(sofa[0], desk[0], 2.0, None)
solver.distance_constraint(sofa[0], chair[0], 1.8, None)

solver.constraints = []
sofa[0].position = [4.389999866485596, 2.984936475753784, 0.42500001192092896]
sofa[0].rotation = [0, 0, -1.5707962875145278]
sofa[0].optimize = 2
desk[0].position = [5.65500020980835, 1.100000023841858, 0.375]
desk[0].rotation = [0, 0, -3.122743098190977]
desk[0].optimize = 2
chair[0].position = [4.793264865875244, 1.100000023841858, 0.550000011920929]
chair[0].rotation = [0, 0, 0.01884955539881635]
chair[0].optimize = 2

