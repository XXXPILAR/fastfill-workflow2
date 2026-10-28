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
    Wall(corner1=[2.46, 3.26, 0.00], corner2=[0.00, 3.26, 0.00]),
    Wall(corner1=[0.00, 3.26, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.46, 0.00, 0.00]),
    Wall(corner1=[2.46, 0.00, 0.00], corner2=[2.46, 3.26, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
wardrobe = Assets(description="wardrobe", size=[0.60, 1.20, 2.10], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.00, 1.40, 0.55], placements=[AssetInstance() for _ in range(1)])
nightstand = Assets(description="nightstand", size=[0.40, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])

wardrobe[0].instance_id = 'wardrobe_0'
bed[0].instance_id = 'bed_0'
nightstand[0].instance_id = 'nightstand_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

wardrobe[0].position = [1.506323890502617, 2.4904849435770022, 1.05]
wardrobe[0].rotation = [0, 0, 0]
bed[0].position = [1.0630483767662502, 0.12515715918904938, 0.275]
bed[0].rotation = [0, 0, 0]
nightstand[0].position = [0.4140496640786316, 1.1281726250691537, 0.275]
nightstand[0].rotation = [0, 0, 0]
wardrobe[0].position = [1.506323890502617, 2.4904849435770022, 1.05]
wardrobe[0].rotation = [0, 0, 0]
bed[0].position = [1.0630483767662502, 0.12515715918904938, 0.275]
bed[0].rotation = [0, 0, 0]
nightstand[0].position = [0.4140496640786316, 1.1281726250691537, 0.275]
nightstand[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the bed lengthwise along the left wall. Its footprint ends at x=1.40,
# leaving the bottom-right doorway and a central circulation aisle clear.
bed[0].position = [0.70, 1.30, 0.275]
bed[0].rotation = [0, 0, radians(90)]

# Place the wardrobe on the upper part of the right wall. It does not obstruct
# the top-wall window (which ends at x=1.73) or the bottom-right doorway.
wardrobe[0].position = [2.16, 2.58, 1.05]
wardrobe[0].rotation = [0, 0, radians(180)]

# Place the nightstand immediately below the wardrobe against the same wall.
# Their nearest edges have a 0.05 m gap, satisfying the requested <=0.10 m
# proximity without overlapping.
nightstand[0].position = [2.26, 1.705, 0.275]
nightstand[0].rotation = [0, 0, radians(180)]

# Fixed placement and facing targets preserve the functional layout if the
# solver needs to adjust the scene.
bed_position_target = AssetInstance(position=[0.70, 1.30, 0.275])
wardrobe_position_target = AssetInstance(position=[2.16, 2.58, 1.05])
nightstand_position_target = AssetInstance(position=[2.26, 1.705, 0.275])

bed_facing_target = AssetInstance(position=[0.70, 3.00, 0.275])
wardrobe_facing_target = AssetInstance(position=[1.00, 2.58, 1.05])
nightstand_facing_target = AssetInstance(position=[1.00, 1.705, 0.275])

# The wardrobe-wall requirement and wardrobe/nightstand proximity are the
# highest-priority semantic constraints.
solver.against_wall(wardrobe[0], walls[3])
solver.distance_constraint(
    nightstand[0], wardrobe[0],
    0.87, 0.90, weight=10
)

# Keep the other furniture against its selected wall and anchor all three
# objects near their non-overlapping planned positions.
solver.against_wall(bed[0], walls[1])
solver.against_wall(nightstand[0], walls[3])

solver.distance_constraint(
    wardrobe[0], wardrobe_position_target,
    0, 0, weight=10
)
solver.distance_constraint(
    bed[0], bed_position_target,
    0, 0, weight=10
)
solver.distance_constraint(
    nightstand[0], nightstand_position_target,
    0, 0, weight=10
)

# Orient the bed along the room's long axis and make the fronts of the
# right-wall furniture face inward toward the usable part of the room.
solver.point_towards(bed[0], bed_facing_target)
solver.point_towards(wardrobe[0], wardrobe_facing_target)
solver.point_towards(nightstand[0], nightstand_facing_target)

solver.constraints = []
wardrobe[0].position = [2.1599936485290527, 2.5799999237060547, 1.0499999523162842]
wardrobe[0].rotation = [0, 0, 3.141582726596515]
wardrobe[0].optimize = 2
bed[0].position = [1.0458894968032837, 1.2999999523162842, 0.2750000059604645]
bed[0].rotation = [0, 0, -0.020540354510364428]
bed[0].optimize = 2
nightstand[0].position = [2.2599985599517822, 1.7050000429153442, 0.2750000059604645]
nightstand[0].rotation = [0, 0, 3.141582666981068]
nightstand[0].optimize = 2

