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
    Wall(corner1=[3.70, 2.08, 0.00], corner2=[2.92, 2.08, 0.00]),
    Wall(corner1=[2.92, 2.08, 0.00], corner2=[2.92, 2.55, 0.00]),
    Wall(corner1=[2.92, 2.55, 0.00], corner2=[0.76, 2.55, 0.00]),
    Wall(corner1=[0.76, 2.55, 0.00], corner2=[0.76, 1.38, 0.00]),
    Wall(corner1=[0.76, 1.38, 0.00], corner2=[0.00, 1.38, 0.00]),
    Wall(corner1=[0.00, 1.38, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.13, 0.00, 0.00]),
    Wall(corner1=[3.13, 0.00, 0.00], corner2=[3.13, 0.55, 0.00]),
    Wall(corner1=[3.13, 0.55, 0.00], corner2=[3.70, 0.55, 0.00]),
    Wall(corner1=[3.70, 0.55, 0.00], corner2=[3.70, 2.08, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
nightstand = Assets(description="nightstand", size=[0.40, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.00, 1.40, 0.55], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="cabinet", size=[0.45, 1.00, 1.80], placements=[AssetInstance() for _ in range(1)])

nightstand[0].instance_id = 'nightstand_0'
bed[0].instance_id = 'bed_0'
cabinet[0].instance_id = 'cabinet_0'
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

nightstand[0].position = [2.5242507661500184, 0.42161095275045474, 0.275]
nightstand[0].rotation = [0, 0, 0]
bed[0].position = [1.9722992285447938, 2.5158096782812924, 0.275]
bed[0].rotation = [0, 0, 0]
cabinet[0].position = [2.0893568960906843, 0.8917557301937199, 0.9]
cabinet[0].rotation = [0, 0, 0]
nightstand[0].position = [2.5242507661500184, 0.42161095275045474, 0.275]
nightstand[0].rotation = [0, 0, 0]
bed[0].position = [1.9722992285447938, 2.5158096782812924, 0.275]
bed[0].rotation = [0, 0, 0]
cabinet[0].position = [2.0893568960906843, 0.8917557301937199, 0.9]
cabinet[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the bed along the bottom wall, leaving the full doorway area and its
# approach from the east side of the door unobstructed.
bed[0].position = [2.05, 0.70, bed.size[2] / 2]
bed[0].rotation = [0, 0, radians(0)]

# Place the nightstand beside the lower-left corner of the bed. The 0.10 m
# gap prevents overlap while keeping it comfortably within reach.
nightstand[0].position = [0.75, 0.225, nightstand.size[2] / 2]
nightstand[0].rotation = [0, 0, radians(0)]

# Place the cabinet against the short left wall, below the door opening.
# Its shallow dimension extends into the room, and it does not obstruct
# either the door or the window on the opposite wall.
cabinet[0].position = [0.225, 0.80, cabinet.size[2] / 2]
cabinet[0].rotation = [0, 0, radians(0)]


# Fixed targets preserve the selected positions if the layout is adjusted.
bed_target = AssetInstance(position=[2.05, 0.70, bed.size[2] / 2])
nightstand_target = AssetInstance(
    position=[0.75, 0.225, nightstand.size[2] / 2]
)
cabinet_target = AssetInstance(
    position=[0.225, 0.80, cabinet.size[2] / 2]
)

# Orientation targets lie directly along +x from each object, preserving
# their specified zero-radian orientation.
bed_facing_target = AssetInstance(
    position=[3.05, 0.70, bed.size[2] / 2]
)
nightstand_facing_target = AssetInstance(
    position=[1.75, 0.225, nightstand.size[2] / 2]
)
cabinet_facing_target = AssetInstance(
    position=[1.225, 0.80, cabinet.size[2] / 2]
)


# Important wall relationships come first. Wall 6 is the bottom wall, while
# wall 5 is the left wall below the doorway.
solver.against_wall(bed[0], walls[6])
solver.against_wall(nightstand[0], walls[6])
solver.against_wall(cabinet[0], walls[5])

# Strong positional anchors prevent the solver from sliding the furniture
# into the door clearance, window area, or another asset.
solver.distance_constraint(
    bed[0], bed_target, min_distance=0, max_distance=0, weight=10
)
solver.distance_constraint(
    nightstand[0], nightstand_target,
    min_distance=0, max_distance=0, weight=10
)
solver.distance_constraint(
    cabinet[0], cabinet_target,
    min_distance=0, max_distance=0, weight=10
)

# Keep the nightstand beside the bed and retain the useful separation between
# the cabinet and bed if minor feasibility adjustments are required.
solver.distance_constraint(
    nightstand[0], bed[0],
    min_distance=1.30, max_distance=1.45, weight=1
)
solver.distance_constraint(
    cabinet[0], bed[0],
    min_distance=1.75, max_distance=1.95, weight=1
)

# Every new asset receives an explicit orientation constraint.
solver.point_towards(bed[0], bed_facing_target)
solver.point_towards(nightstand[0], nightstand_facing_target)
solver.point_towards(cabinet[0], cabinet_facing_target)

solver.constraints = []
cabinet[0].position = [0.7207716703414917, 0.8814220428466797, 0.8999999761581421]
cabinet[0].rotation = [0, 0, 0.006276574661761637]
cabinet[0].optimize = 2
bed[0].position = [2.4494576454162598, 1.4244270324707031, 0.2750000059604645]
bed[0].rotation = [0, 0, 1.7842125241791293]
bed[0].optimize = 2
nightstand[0].position = [1.1794716119766235, 1.2694909572601318, 0.2750000059604645]
nightstand[0].rotation = [0, 0, -0.013241128915925054]
nightstand[0].optimize = 2

