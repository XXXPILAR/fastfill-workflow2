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
    Wall(corner1=[2.47, 0.00, 0.00], corner2=[2.47, 2.79, 0.00]),
    Wall(corner1=[2.47, 2.79, 0.00], corner2=[0.00, 2.79, 0.00]),
    Wall(corner1=[0.00, 2.79, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.47, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bed = Assets(description="bed", size=[1.90, 0.90, 0.50], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="cabinet", size=[0.45, 0.80, 1.80], placements=[AssetInstance() for _ in range(1)])

bed[0].instance_id = 'bed_0'
cabinet[0].instance_id = 'cabinet_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

bed[0].position = [1.0811706488334307, 0.25961174490679995, 0.25]
bed[0].rotation = [0, 0, 0]
cabinet[0].position = [1.2474368935257294, 0.5328404527859713, 0.9]
cabinet[0].rotation = [0, 0, 0]
bed[0].position = [1.0811706488334307, 0.25961174490679995, 0.25]
bed[0].rotation = [0, 0, 0]
cabinet[0].position = [1.2474368935257294, 0.5328404527859713, 0.9]
cabinet[0].rotation = [0, 0, 0]

solver.constraints = []

# Honor the fixed cabinet center. Its supplied mesh dimensions fit entirely
# within the reserved 1.40 x 0.60 m footprint when it faces north.
cabinet[0].position = [0.70, 0.30, cabinet.size[2] / 2]
cabinet[0].rotation = [0, 0, radians(90)]

# Point the bed south toward the cabinet.
# Rotated footprint: x=[0.25, 1.15], y=[0.85, 2.75].
# This leaves 0.25 m beyond the reserved cabinet footprint and a
# 1.32 m-wide clear strip along the east side for access to the door.
# The low bed, rather than the tall cabinet, is beside the west window.
bed[0].position = [0.70, 1.80, bed.size[2] / 2]
bed[0].rotation = [0, 0, radians(-90)]

# Fixed reference points are constraint targets, not additional scene objects.
fixed_cabinet_pose = AssetInstance(
    position=[0.70, 0.30, cabinet.size[2] / 2],
    rotation=[0, 0, radians(90)]
)
bed_location = AssetInstance(
    position=[0.70, 1.80, bed.size[2] / 2]
)

# Highest-priority positional constraints preserve the fixed cabinet and
# keep the bed inside the boundary, outside the door approach and cabinet zone.
solver.distance_constraint(
    cabinet[0], fixed_cabinet_pose, 0, 0, weight=10
)
solver.distance_constraint(
    bed[0], bed_location, 0, 0, weight=10
)

# Orientation constraints for both new instances.
solver.align_with(cabinet[0], fixed_cabinet_pose, angle=0)
solver.point_towards(bed[0], cabinet[0])

# Center distance includes the different bounding-box center heights.
# Maintain the intended separation without imposing a conflicting wall snap.
bed_cabinet_distance = (
    (1.80 - 0.30) ** 2
    + ((bed.size[2] - cabinet.size[2]) / 2) ** 2
) ** 0.5
solver.distance_constraint(
    bed[0],
    cabinet[0],
    bed_cabinet_distance,
    bed_cabinet_distance,
    weight=10
)

solver.constraints = []
cabinet[0].position = [0.699999988079071, 0.30000001192092896, 0.8999999761581421]
cabinet[0].rotation = [0, 0, 1.586504290712113]
cabinet[0].optimize = 2
bed[0].position = [0.699999988079071, 1.8394203186035156, 0.25]
bed[0].rotation = [0, 0, -1.5582299555380688]
bed[0].optimize = 2

