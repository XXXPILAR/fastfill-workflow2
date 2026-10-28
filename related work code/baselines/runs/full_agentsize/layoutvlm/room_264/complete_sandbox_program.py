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
    Wall(corner1=[2.16, 2.58, 0.00], corner2=[0.01, 2.58, 0.00]),
    Wall(corner1=[0.01, 2.58, 0.00], corner2=[0.01, 2.32, 0.00]),
    Wall(corner1=[0.01, 2.32, 0.00], corner2=[0.00, 2.32, 0.00]),
    Wall(corner1=[0.00, 2.32, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.22, 0.00, 0.00]),
    Wall(corner1=[2.22, 0.00, 0.00], corner2=[2.22, 1.11, 0.00]),
    Wall(corner1=[2.22, 1.11, 0.00], corner2=[2.16, 1.11, 0.00]),
    Wall(corner1=[2.16, 1.11, 0.00], corner2=[2.16, 2.58, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
desk = Assets(description="desk", size=[0.50, 1.00, 0.75], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.00, 0.90, 0.50], placements=[AssetInstance() for _ in range(1)])

desk[0].instance_id = 'desk_0'
bed[0].instance_id = 'bed_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

desk[0].position = [1.2037777882652392, 0.48491070968869976, 0.375]
desk[0].rotation = [0, 0, 0]
bed[0].position = [2.0152408666969404, 0.5226433036076279, 0.25]
bed[0].rotation = [0, 0, 0]
desk[0].position = [1.2037777882652392, 0.48491070968869976, 0.375]
desk[0].rotation = [0, 0, 0]
bed[0].position = [2.0152408666969404, 0.5226433036076279, 0.25]
bed[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the bed lengthwise along the top wall. Its 0.90 m depth projects
# into the room, while the 2.00 m length fits between x=0.16 and x=2.16.
bed[0].position = [1.16, 2.13, 0.25]
bed[0].rotation = [0, 0, radians(0)]

# Place the desk against the right wall, immediately below the bed.
# The resulting edge-to-edge gap is 0.05 m, satisfying the 0.10 m
# proximity requirement while avoiding overlap. This also leaves the
# entrance and the floor directly in front of it unobstructed.
desk[0].position = [1.91, 1.13, 0.375]
desk[0].rotation = [0, 0, radians(180)]

# Fixed references used only to express stable orientation constraints.
room_center_reference = AssetInstance(position=[1.08, 1.29, 0.375])
parallel_orientation_reference = AssetInstance(
    position=[1.08, 1.29, 0.25],
    rotation=[0, 0, radians(0)],
)

# Preserve the required wall relationships as the highest-priority
# positional constraints.
solver.against_wall(bed[0], walls[0])
solver.against_wall(desk[0], walls[5])

# The chosen centers are 1.25 m apart. Given the adjacent bed and desk
# extents, this corresponds to approximately 0.05 m between their edges.
solver.distance_constraint(bed[0], desk[0], 1.25, 1.25, weight=10)

# Keep the bed's long axis parallel to the top wall.
solver.align_with(bed[0], parallel_orientation_reference, angle=0)

# Keep the desk facing inward from the right wall.
solver.point_towards(desk[0], room_center_reference)

solver.constraints = []
desk[0].position = [1.7223948240280151, 0.8572120666503906, 0.375]
desk[0].rotation = [0, 0, -1.5692197841356978]
desk[0].optimize = 2
bed[0].position = [1.047385573387146, 1.3467351198196411, 0.25]
bed[0].rotation = [0, 0, -1.2860889553479138]
bed[0].optimize = 2

