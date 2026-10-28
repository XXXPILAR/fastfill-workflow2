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
    Wall(corner1=[0.71, 3.80, 0.00], corner2=[0.71, 3.20, 0.00]),
    Wall(corner1=[0.71, 3.20, 0.00], corner2=[0.30, 3.20, 0.00]),
    Wall(corner1=[0.30, 3.20, 0.00], corner2=[0.30, 2.94, 0.00]),
    Wall(corner1=[0.30, 2.94, 0.00], corner2=[0.00, 2.94, 0.00]),
    Wall(corner1=[0.00, 2.94, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.45, 0.00, 0.00]),
    Wall(corner1=[3.45, 0.00, 0.00], corner2=[3.45, 0.30, 0.00]),
    Wall(corner1=[3.45, 0.30, 0.00], corner2=[3.87, 0.30, 0.00]),
    Wall(corner1=[3.87, 0.30, 0.00], corner2=[3.87, 2.94, 0.00]),
    Wall(corner1=[3.87, 2.94, 0.00], corner2=[3.45, 2.94, 0.00]),
    Wall(corner1=[3.45, 2.94, 0.00], corner2=[3.45, 3.20, 0.00]),
    Wall(corner1=[3.45, 3.20, 0.00], corner2=[2.73, 3.20, 0.00]),
    Wall(corner1=[2.73, 3.20, 0.00], corner2=[2.73, 3.80, 0.00]),
    Wall(corner1=[2.73, 3.80, 0.00], corner2=[0.71, 3.80, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
wardrobe = Assets(description="wardrobe", size=[0.60, 1.80, 2.20], placements=[AssetInstance() for _ in range(1)])
dining_chair = Assets(description="dining chair", size=[0.55, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.00, 1.40, 0.55], placements=[AssetInstance() for _ in range(1)])

wardrobe[0].instance_id = 'wardrobe_0'
dining_chair[0].instance_id = 'dining_chair_0'
bed[0].instance_id = 'bed_0'
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
walls[12].instance_id = 'walls_12'
walls[13].instance_id = 'walls_13'

wardrobe[0].position = [0.9214498116350498, 2.9542257860644803, 1.1]
wardrobe[0].rotation = [0, 0, 0]
dining_chair[0].position = [2.4510819961243615, 1.3014440712004443, 0.45]
dining_chair[0].rotation = [0, 0, 0]
bed[0].position = [0.6214727884588832, 2.245285689093075, 0.275]
bed[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.9214498116350498, 2.9542257860644803, 1.1]
wardrobe[0].rotation = [0, 0, 0]
dining_chair[0].position = [2.4510819961243615, 1.3014440712004443, 0.45]
dining_chair[0].rotation = [0, 0, 0]
bed[0].position = [0.6214727884588832, 2.245285689093075, 0.275]
bed[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the wardrobe along the uninterrupted left wall. Its front faces into
# the room, and its shallow 0.60 m dimension is perpendicular to the wall.
wardrobe[0].position = [0.30, 1.40, 1.10]
wardrobe[0].rotation = [0, 0, radians(0)]

# Place the low bed beneath the wide upper window. Rotating it clockwise makes
# its head/end touch the upper wall while its front points toward the chair.
bed[0].position = [1.80, 2.80, 0.275]
bed[0].rotation = [0, 0, radians(-90)]

# Keep the chair in the open lower-middle area, away from the entrance at
# x=3.06, and leave circulation space between it and the bed.
dining_chair[0].position = [1.80, 1.15, 0.45]
dining_chair[0].rotation = [0, 0, radians(90)]

# Primary position and orientation constraints for each asset.
solver.against_wall(wardrobe[0], walls[4])
solver.point_towards(
    wardrobe[0],
    AssetInstance(position=[1.80, 1.40, 1.10]),
)

solver.against_wall(bed[0], walls[13])
solver.point_towards(bed[0], dining_chair[0])

solver.distance_constraint(
    dining_chair[0], bed[0],
    min_distance=1.50,
    max_distance=1.80,
    weight=10,
)
solver.point_towards(dining_chair[0], bed[0])

# Secondary spacing constraints preserve the non-overlapping arrangement if
# the solver adjusts placements for physical feasibility.
solver.distance_constraint(
    wardrobe[0], bed[0],
    min_distance=1.90,
    max_distance=2.25,
    weight=1,
)
solver.distance_constraint(
    dining_chair[0], wardrobe[0],
    min_distance=1.35,
    max_distance=1.75,
    weight=1,
)

solver.constraints = []
bed[0].position = [1.4382784366607666, 2.4241421222686768, 0.2750000059604645]
bed[0].rotation = [0, 0, -1.134557624012066]
bed[0].optimize = 2
wardrobe[0].position = [0.43692636489868164, 1.7656443119049072, 1.100000023841858]
wardrobe[0].rotation = [0, 0, -0.15687637417327246]
wardrobe[0].optimize = 2
dining_chair[0].position = [1.8887465000152588, 0.9879787564277649, 0.44999998807907104]
dining_chair[0].rotation = [0, 0, 1.586504290712113]
dining_chair[0].optimize = 2

