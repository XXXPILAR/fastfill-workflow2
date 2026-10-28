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
    Wall(corner1=[1.54, 2.49, 0.00], corner2=[0.00, 2.49, 0.00]),
    Wall(corner1=[0.00, 2.49, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[1.54, 0.00, 0.00]),
    Wall(corner1=[1.54, 0.00, 0.00], corner2=[1.54, 2.49, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
toilet = Assets(description="toilet", size=[0.70, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
screen = Assets(description="screen", size=[0.04, 0.80, 1.90], placements=[AssetInstance() for _ in range(1)])

toilet[0].instance_id = 'toilet_0'
screen[0].instance_id = 'screen_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

toilet[0].position = [0.28654038124846865, 0.5419749798885806, 0.39]
toilet[0].rotation = [0, 0, 0]
screen[0].position = [1.166706620218817, 2.2973738803203787, 0.95]
screen[0].rotation = [0, 0, 0]
toilet[0].position = [0.28654038124846865, 0.5419749798885806, 0.39]
toilet[0].rotation = [0, 0, 0]
screen[0].position = [1.166706620218817, 2.2973738803203787, 0.95]
screen[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the toilet and privacy screen in the unobstructed upper-left portion of
# the room, away from the entrance, fixed cabinet, and window.
screen[0].position = [0.02, 1.72, 0.95]
screen[0].rotation = [0, 0, radians(0)]

toilet[0].position = [0.22, 1.72, 0.39]
toilet[0].rotation = [0, 0, radians(90)]

# Keep the screen against the left wall. Its thin axis is perpendicular to the
# wall, while its 0.80 m width runs along the wall.
solver.against_wall(screen[0], walls[1])

# Preserve the requested close relationship between the toilet and screen.
# This is specified with the toilet as the movable first argument so the
# higher-priority wall constraint on the screen remains authoritative.
solver.distance_constraint(
    toilet[0], screen[0],
    min_distance=None,
    max_distance=0.20,
    weight=10,
)

# The screen faces inward toward the toilet rather than toward the wall.
solver.point_towards(screen[0], toilet[0])

# Orient the toilet perpendicular to the screen so that it faces toward the
# open upper part of the room and remains clear of the entrance.
solver.align_with(toilet[0], screen[0], angle=90)

solver.constraints = []
toilet[0].position = [0.2199999988079071, 1.7200000286102295, 0.38999998569488525]
toilet[0].rotation = [0, 0, 1.5576206440249134]
toilet[0].optimize = 2
screen[0].position = [0.020848378539085388, 1.7200000286102295, 0.949999988079071]
screen[0].rotation = [0, 0, 0.006140061274910162]
screen[0].optimize = 2

