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
    Wall(corner1=[1.16, 1.09, 0.00], corner2=[0.00, 1.09, 0.00]),
    Wall(corner1=[0.00, 1.09, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[1.16, 0.00, 0.00]),
    Wall(corner1=[1.16, 0.00, 0.00], corner2=[1.16, 1.09, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
toilet = Assets(description="toilet", size=[0.68, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
bin = Assets(description="bin", size=[0.20, 0.20, 0.28], placements=[AssetInstance() for _ in range(1)])
toilet_brush = Assets(description="toilet brush", size=[0.12, 0.12, 0.38], placements=[AssetInstance() for _ in range(1)])

toilet[0].instance_id = 'toilet_0'
bin[0].instance_id = 'bin_0'
toilet_brush[0].instance_id = 'toilet_brush_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

toilet[0].position = [0.6152796946880805, 1.016501795570078, 0.39]
toilet[0].rotation = [0, 0, 0]
bin[0].position = [0.2535598931870345, 0.7736076008697511, 0.14]
bin[0].rotation = [0, 0, 0]
toilet_brush[0].position = [0.5431849907936355, 0.029131928198552315, 0.19]
toilet_brush[0].rotation = [0, 0, 0]
toilet[0].position = [0.6152796946880805, 1.016501795570078, 0.39]
toilet[0].rotation = [0, 0, 0]
bin[0].position = [0.2535598931870345, 0.7736076008697511, 0.14]
bin[0].rotation = [0, 0, 0]
toilet_brush[0].position = [0.5431849907936355, 0.029131928198552315, 0.19]
toilet_brush[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the toilet against the upper wall, facing into the room.
# After the -90 degree rotation its 0.68 m depth runs along the y-axis.
toilet[0].position = [0.58, 0.75, 0.39]
toilet[0].rotation = [0, 0, radians(-90)]

# Place the brush directly beside the toilet's left side. The centers are
# 0.25 m apart, corresponding to zero clearance between their bounding boxes.
toilet_brush[0].position = [0.33, 0.75, 0.19]
toilet_brush[0].rotation = [0, 0, radians(-90)]

# Place the bin against the left wall and close to the toilet brush.
bin[0].position = [0.10, 0.75, 0.14]
bin[0].rotation = [0, 0, 0]

room_center = AssetInstance(position=[0.58, 0.545, 0.0])

# Wall placement and inward-facing orientation are the primary toilet constraints.
solver.against_wall(toilet[0], walls[0])
solver.point_towards(toilet[0], room_center)

# Keep the bin against the left wall and oriented toward the nearby fixtures.
solver.against_wall(bin[0], walls[1])
solver.point_towards(bin[0], toilet_brush[0])

# The brush remains immediately beside the toilet and points toward it.
solver.distance_constraint(
    toilet_brush[0], toilet[0],
    0.25, 0.35,
    weight=10
)
solver.point_towards(toilet_brush[0], toilet[0])

# A 0.10 m clear gap between the toilet and brush permits a center distance
# up to 0.19 + 0.06 + 0.10 = 0.35 m along their adjoining sides.
solver.distance_constraint(
    toilet[0], toilet_brush[0],
    0.25, 0.35,
    weight=10
)

# A 0.50 m clear gap permits up to 0.10 + 0.06 + 0.50 = 0.66 m between
# the bin and brush centers; the chosen placements are substantially closer.
solver.distance_constraint(
    bin[0], toilet_brush[0],
    0.16, 0.66,
    weight=10
)

solver.constraints = []
bin[0].position = [0.10019352287054062, 0.75, 0.14000000059604645]
bin[0].rotation = [0, 0, -0.00010996997604882213]
bin[0].optimize = 2
toilet_brush[0].position = [0.27287307381629944, 0.75, 0.1899999976158142]
toilet_brush[0].rotation = [0, 0, -1.08445683000777]
toilet_brush[0].optimize = 2
toilet[0].position = [0.6371270418167114, 0.7524949908256531, 0.38999998569488525]
toilet[0].rotation = [0, 0, -1.571500914055114]
toilet[0].optimize = 2

