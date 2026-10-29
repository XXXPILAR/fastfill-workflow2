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
toilet = Assets(description="toilet", size=[0.65, 0.37, 0.78], placements=[AssetInstance() for _ in range(1)])
bin = Assets(description="bin", size=[0.22, 0.18, 0.28], placements=[AssetInstance() for _ in range(1)])
toilet_brush = Assets(description="toilet brush", size=[0.12, 0.12, 0.38], placements=[AssetInstance() for _ in range(1)])

toilet[0].instance_id = 'toilet_0'
bin[0].instance_id = 'bin_0'
toilet_brush[0].instance_id = 'toilet_brush_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

toilet[0].position = [0.2235146652088286, 1.0473818147782357, 0.39]
toilet[0].rotation = [0, 0, 0]
bin[0].position = [0.32433008211872244, 0.33498357787294575, 0.14]
bin[0].rotation = [0, 0, 0]
toilet_brush[0].position = [0.3801133960080909, 0.4947011297813646, 0.19]
toilet_brush[0].rotation = [0, 0, 0]
toilet[0].position = [0.2235146652088286, 1.0473818147782357, 0.39]
toilet[0].rotation = [0, 0, 0]
bin[0].position = [0.32433008211872244, 0.33498357787294575, 0.14]
bin[0].rotation = [0, 0, 0]
toilet_brush[0].position = [0.3801133960080909, 0.4947011297813646, 0.19]
toilet_brush[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the explicit wall coordinates: the room spans x=[0,1.16], y=[0,1.09].
# The toilet backs onto the left wall and faces +x, leaving 0.51 m ahead.
toilet[0].position = [0.325, 0.650, 0.390]
toilet[0].rotation = [0, 0, 0]

# Keep the brush on the floor beside the toilet, with a 0.06 m surface gap.
toilet_brush[0].position = [0.325, 0.345, 0.190]
toilet_brush[0].rotation = [0, 0, 0]

# Place the bin against the left wall, clear of both other footprints.
bin[0].position = [0.110, 0.130, 0.140]
bin[0].rotation = [0, 0, 0]

# A literal 0.10 m center-distance between toilet and brush is incompatible
# with non-overlap. Interpret that criterion as a surface clearance instead.
# All objects are floor-standing; no on_top_of constraints are needed.

solver.against_wall(toilet[0], walls[1])
solver.against_wall(bin[0], walls[1])

# Fixed reference instances preserve the selected positions and floor heights.
solver.distance_constraint(
    toilet[0], AssetInstance(position=[0.325, 0.650, 0.390]),
    0, 0, weight=10
)
solver.distance_constraint(
    toilet_brush[0], AssetInstance(position=[0.325, 0.345, 0.190]),
    0, 0, weight=10
)
solver.distance_constraint(
    bin[0], AssetInstance(position=[0.110, 0.130, 0.140]),
    0, 0, weight=10
)

# Face into the room; keep the accessories parallel to the toilet.
solver.point_towards(
    toilet[0], AssetInstance(position=[1.160, 0.650, 0.390])
)
solver.align_with(toilet_brush[0], toilet[0])
solver.align_with(bin[0], toilet[0])

# With aligned footprints, lateral center separation of 0.245–0.345 m
# represents a surface gap of 0–0.10 m. Include the 0.20 m height difference
# because distance_constraint measures 3D bounding-box-center distance.
solver.distance_constraint(
    toilet[0], toilet_brush[0],
    (0.245**2 + 0.200**2)**0.5,
    (0.345**2 + 0.200**2)**0.5,
    weight=10
)

# The chosen bin/brush center distance is about 0.308 m, below 0.50 m.
# The lower bound also prevents their bounding footprints from overlapping.
solver.distance_constraint(bin[0], toilet_brush[0], 0.24, 0.50, weight=10)

solver.constraints = []
bin[0].position = [0.10999998450279236, 0.12999999523162842, 0.14000000059604645]
bin[0].rotation = [0, 0, 5.1925989583503174e-08]
bin[0].optimize = 2
toilet_brush[0].position = [0.32499998807907104, 0.3449999988079071, 0.1899999976158142]
toilet_brush[0].rotation = [0, 0, 1.0922752736576379e-07]
toilet_brush[0].optimize = 2
toilet[0].position = [0.32499995827674866, 0.7317651510238647, 0.38999998569488525]
toilet[0].rotation = [0, 0, 2.8039590987127773e-08]
toilet[0].optimize = 2

