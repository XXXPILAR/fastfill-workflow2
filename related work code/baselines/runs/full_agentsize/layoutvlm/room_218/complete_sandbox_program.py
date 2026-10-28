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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.94, 0.00, 0.00]),
    Wall(corner1=[2.94, 0.00, 0.00], corner2=[2.94, 2.95, 0.00]),
    Wall(corner1=[2.94, 2.95, 0.00], corner2=[0.00, 2.95, 0.00]),
    Wall(corner1=[0.00, 2.95, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
wardrobe = Assets(description="wardrobe", size=[0.60, 1.20, 2.00], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.00, 0.90, 0.55], placements=[AssetInstance() for _ in range(1)])
nightstand_A = Assets(description="nightstand", size=[0.40, 0.40, 0.50], placements=[AssetInstance() for _ in range(1)])
nightstand_B = Assets(description="nightstand", size=[0.40, 0.40, 0.50], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[2.30, 1.60, 0.01], placements=[AssetInstance() for _ in range(1)])

wardrobe[0].instance_id = 'wardrobe_0'
bed[0].instance_id = 'bed_0'
nightstand_A[0].instance_id = 'nightstand_A_0'
nightstand_B[0].instance_id = 'nightstand_B_0'
carpet[0].instance_id = 'carpet_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

wardrobe[0].position = [2.2865594833532072, 2.3669751579207774, 1.0]
wardrobe[0].rotation = [0, 0, 0]
bed[0].position = [0.11905254851927524, 2.9433976973189426, 0.275]
bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [0.04896606901037705, 1.6373522522514616, 0.25]
nightstand_A[0].rotation = [0, 0, 0]
nightstand_B[0].position = [0.8988199871488165, 0.941855399666292, 0.25]
nightstand_B[0].rotation = [0, 0, 0]
carpet[0].position = [0.7283818905532485, 1.5325413010462836, 0.005]
carpet[0].rotation = [0, 0, 0]
wardrobe[0].position = [2.2865594833532072, 2.3669751579207774, 1.0]
wardrobe[0].rotation = [0, 0, 0]
bed[0].position = [0.11905254851927524, 2.9433976973189426, 0.275]
bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [0.04896606901037705, 1.6373522522514616, 0.25]
nightstand_A[0].rotation = [0, 0, 0]
nightstand_B[0].position = [0.8988199871488165, 0.941855399666292, 0.25]
nightstand_B[0].rotation = [0, 0, 0]
carpet[0].position = [0.7283818905532485, 1.5325413010462836, 0.005]
carpet[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the sleeping area along the south wall. Rotating the bed by 90 degrees
# makes its 0.90 m width run east-west and its 2.00 m length run north-south.
# This leaves a 0.95 m clear aisle in front of the north-wall doorway.
carpet[0].position = [1.47, 1.15, 0.005]
carpet[0].rotation = [0, 0, radians(90)]

bed[0].position = [1.47, 1.00, 0.285]
bed[0].rotation = [0, 0, radians(90)]

# The two nightstands flank the bed at its south/head end, so the bed is
# geometrically between them. The 0.05 m gaps prevent bounding-box overlap.
nightstand_A[0].position = [0.77, 0.20, 0.26]
nightstand_A[0].rotation = [0, 0, radians(90)]

nightstand_B[0].position = [2.17, 0.20, 0.26]
nightstand_B[0].rotation = [0, 0, radians(90)]

# Place the wardrobe against the east wall, outside the doorway's approach
# corridor, with its front facing west into the room.
wardrobe[0].position = [2.64, 1.58, 1.00]
wardrobe[0].rotation = [0, 0, radians(180)]

# Fixed reference points preserve the intended centers and facing directions.
bed_anchor = AssetInstance(position=[1.47, 1.00, 0.285])
nightstand_A_anchor = AssetInstance(position=[0.77, 0.20, 0.26])
nightstand_B_anchor = AssetInstance(position=[2.17, 0.20, 0.26])
carpet_anchor = AssetInstance(position=[1.47, 1.15, 0.005])
wardrobe_anchor = AssetInstance(position=[2.64, 1.58, 1.00])

bed_facing_target = AssetInstance(position=[1.47, 2.00, 0.285])
wardrobe_facing_target = AssetInstance(position=[1.64, 1.58, 1.00])

# Important position constraints first: keep the furniture at the selected
# collision-free centers and retain the clear route from the doorway.
solver.distance_constraint(bed[0], bed_anchor, 0, 0, weight=10)
solver.distance_constraint(nightstand_A[0], nightstand_A_anchor, 0, 0, weight=10)
solver.distance_constraint(nightstand_B[0], nightstand_B_anchor, 0, 0, weight=10)
solver.distance_constraint(carpet[0], carpet_anchor, 0, 0, weight=10)
solver.distance_constraint(wardrobe[0], wardrobe_anchor, 0, 0, weight=10)

# Maintain contact with the appropriate room boundaries.
solver.against_wall(carpet[0], walls[0])
solver.against_wall(bed[0], walls[0])
solver.against_wall(nightstand_A[0], walls[0])
solver.against_wall(nightstand_B[0], walls[0])
solver.against_wall(wardrobe[0], walls[1])

# The thin carpet supports the bed and nightstands.
solver.on_top_of(bed[0], carpet[0])
solver.on_top_of(nightstand_A[0], carpet[0])
solver.on_top_of(nightstand_B[0], carpet[0])

# Preserve the flanking arrangement: each nightstand center remains about
# 0.70 m from the bed center, on opposite sides.
solver.distance_constraint(nightstand_A[0], bed[0], 0.69, 0.72, weight=10)
solver.distance_constraint(nightstand_B[0], bed[0], 0.69, 0.72, weight=10)
solver.distance_constraint(nightstand_A[0], nightstand_B[0], 1.39, 1.41, weight=10)

# Orientation constraints for every new asset.
solver.point_towards(bed[0], bed_facing_target)
solver.align_with(nightstand_A[0], bed[0])
solver.align_with(nightstand_B[0], bed[0])
solver.align_with(carpet[0], bed[0])
solver.point_towards(wardrobe[0], wardrobe_facing_target)

solver.constraints = []
nightstand_A[0].position = [0.7235112190246582, 0.25210046768188477, 0.25999999046325684]
nightstand_A[0].rotation = [0, 0, 1.5734761791779777]
nightstand_A[0].optimize = 2
nightstand_B[0].position = [2.127777099609375, 0.24100878834724426, 0.25999999046325684]
nightstand_B[0].rotation = [0, 0, 1.5734759973307002]
nightstand_B[0].optimize = 2
bed[0].position = [1.4700000286102295, 1.00521981716156, 0.2849999964237213]
bed[0].rotation = [0, 0, 1.5628705055122512]
bed[0].optimize = 2
wardrobe[0].position = [2.6366021633148193, 1.5800000429153442, 1.0]
wardrobe[0].rotation = [0, 0, -3.137381397608855]
wardrobe[0].optimize = 2
carpet[0].position = [1.4700000286102295, 1.1565083265304565, 0.004999999888241291]
carpet[0].rotation = [0, 0, 1.5733654293304928]
carpet[0].optimize = 2

