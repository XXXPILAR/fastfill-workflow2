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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.55, 0.00, 0.00]),
    Wall(corner1=[2.55, 0.00, 0.00], corner2=[2.55, 4.94, 0.00]),
    Wall(corner1=[2.55, 4.94, 0.00], corner2=[0.55, 4.94, 0.00]),
    Wall(corner1=[0.55, 4.94, 0.00], corner2=[0.55, 3.93, 0.00]),
    Wall(corner1=[0.55, 3.93, 0.00], corner2=[0.00, 3.93, 0.00]),
    Wall(corner1=[0.00, 3.93, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
chair = Assets(description="chair", size=[0.60, 0.60, 0.95], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[2.40, 1.70, 0.01], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.05, 1.45, 0.60], placements=[AssetInstance() for _ in range(1)])
nightstand_A = Assets(description="nightstand", size=[0.40, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
nightstand_B = Assets(description="nightstand", size=[0.40, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])

chair[0].instance_id = 'chair_0'
carpet[0].instance_id = 'carpet_0'
bed[0].instance_id = 'bed_0'
nightstand_A[0].instance_id = 'nightstand_A_0'
nightstand_B[0].instance_id = 'nightstand_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

chair[0].position = [1.1334242693846155, 0.6230483486111329, 0.475]
chair[0].rotation = [0, 0, 0]
carpet[0].position = [0.3434158384113325, 2.258758824836072, 0.0075]
carpet[0].rotation = [0, 0, 0]
bed[0].position = [0.47916376266215766, 2.5589020795809314, 0.3]
bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [0.6002509745375156, 1.3350192084146801, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
nightstand_B[0].position = [1.4729572502696173, 3.891713825022515, 0.275]
nightstand_B[0].rotation = [0, 0, 0]
chair[0].position = [1.1334242693846155, 0.6230483486111329, 0.475]
chair[0].rotation = [0, 0, 0]
carpet[0].position = [0.3434158384113325, 2.258758824836072, 0.0075]
carpet[0].rotation = [0, 0, 0]
bed[0].position = [0.47916376266215766, 2.5589020795809314, 0.3]
bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [0.6002509745375156, 1.3350192084146801, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
nightstand_B[0].position = [1.4729572502696173, 3.891713825022515, 0.275]
nightstand_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Face the bed north, with its head against the south wall. Rotating it
# 90 degrees gives a 1.45 m east-west footprint, leaving room for both
# nightstands. Their footprints are separated from the bed by 5 cm.
bed[0].position = [1.275, 1.025, 0.30]
bed[0].rotation = [0, 0, radians(90)]

nightstand_A[0].position = [0.275, 0.20, 0.275]
nightstand_A[0].rotation = [0, 0, radians(90)]

nightstand_B[0].position = [2.275, 0.20, 0.275]
nightstand_B[0].rotation = [0, 0, radians(90)]

# The rug occupies the northern alcove without crossing its inset west
# boundary: x = 0.80..2.50, y = 2.50..4.90.
# It does not overlap any furniture footprint.
carpet[0].position = [1.65, 3.70, 0.005]
carpet[0].rotation = [0, 0, radians(90)]

# Place the chair south of the door's clearance zone, facing into the room.
# Its footprint is x = 0.05..0.65, y = 2.20..2.80.
chair[0].position = [0.35, 2.50, 0.475]
chair[0].rotation = [0, 0, 0]

# High-priority position anchors preserve the non-overlapping arrangement
# and keep furniture out of the west-side doorway at y = 2.935..3.905.
# These are fixed reference points, not additional scene furnishings.
for instance in (
    bed[0],
    nightstand_A[0],
    nightstand_B[0],
    carpet[0],
    chair[0],
):
    solver.distance_constraint(
        instance,
        AssetInstance(position=list(instance.position)),
        0.0,
        0.0,
        weight=10,
    )
    solver.align_with(
        instance,
        AssetInstance(
            position=list(instance.position),
            rotation=list(instance.rotation),
        ),
        angle=0,
    )

# Keep the head of the bed and the backs of both nightstands on the
# south wall. These wall constraints agree with the anchored positions.
solver.against_wall(bed[0], walls[0])
solver.against_wall(nightstand_A[0], walls[0])
solver.against_wall(nightstand_B[0], walls[0])

# Preserve the bedside relationship. Distances include the small
# difference in bounding-box center heights.
solver.distance_constraint(nightstand_A[0], bed[0], 1.29, 1.31, weight=10)
solver.distance_constraint(nightstand_B[0], bed[0], 1.29, 1.31, weight=10)
solver.distance_constraint(nightstand_A[0], nightstand_B[0], 2.0, 2.0)
solver.align_with(nightstand_A[0], bed[0])
solver.align_with(nightstand_B[0], bed[0])

# All assets are floor-supported, including the thin carpet;
# no on_top_of constraints are needed.

solver.constraints = []
carpet[0].position = [1.649999976158142, 3.700000047683716, 0.004999999888241291]
carpet[0].rotation = [0, 0, 1.5802211042556205]
carpet[0].optimize = 2
nightstand_B[0].position = [2.275041103363037, 0.20012950897216797, 0.2750000059604645]
nightstand_B[0].rotation = [0, 0, 1.5705901160065587]
nightstand_B[0].optimize = 2
chair[0].position = [0.3499999940395355, 2.5, 0.4749999940395355]
chair[0].rotation = [0, 0, 0.00942477746072377]
chair[0].optimize = 2
bed[0].position = [1.274999737739563, 1.0429023504257202, 0.30000001192092896]
bed[0].rotation = [0, 0, 0.37104183683037856]
bed[0].optimize = 2
nightstand_A[0].position = [0.2724555432796478, 0.20020604133605957, 0.2750000059604645]
nightstand_A[0].rotation = [0, 0, 1.5705901286280817]
nightstand_A[0].optimize = 2

