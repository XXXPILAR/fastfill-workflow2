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
    Wall(corner1=[3.40, 0.00, 0.00], corner2=[3.40, 5.18, 0.00]),
    Wall(corner1=[3.40, 5.18, 0.00], corner2=[0.00, 5.18, 0.00]),
    Wall(corner1=[0.00, 5.18, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.40, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
tv_stand = Assets(description="A sleek black console table with ornate legs and a flat top, adorned with decorative vases and a framed picture.", size=[0.40, 1.60, 0.80], placements=[AssetInstance() for _ in range(1)])
nightstand_A = Assets(description="A light gray chest of drawers with three drawers, each equipped with a bronze handle. It has a classic design with a slightly raised base and decorative molding along the edges.", size=[0.45, 0.70, 0.70], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="A large wardrobe with multiple compartments, including shelves for clothes, drawers, and storage boxes. It features a combination of open and closed sections, with a sleek design suitable for a bedroom or dressing area.", size=[0.60, 2.40, 2.20], placements=[AssetInstance() for _ in range(1)])
king_size_bed = Assets(description="A modern bed with a black leather headboard and a gray mattress. It features multiple decorative pillows in shades of gray, brown, and gold.", size=[2.20, 2.10, 1.20], placements=[AssetInstance() for _ in range(1)])
nightstand_B = Assets(description="A light gray chest of drawers with three drawers, each equipped with a bronze handle. It has a classic design with a slightly raised base and decorative molding along the edges.", size=[0.45, 0.70, 0.70], placements=[AssetInstance() for _ in range(1)])

tv_stand[0].instance_id = 'tv_stand_0'
nightstand_A[0].instance_id = 'nightstand_A_0'
wardrobe[0].instance_id = 'wardrobe_0'
king_size_bed[0].instance_id = 'king_size_bed_0'
nightstand_B[0].instance_id = 'nightstand_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

tv_stand[0].position = [0.6084749586884393, 1.6229205484008766, 0.4]
tv_stand[0].rotation = [0, 0, 0]
nightstand_A[0].position = [0.12837939080854416, 0.6511123155567489, 0.35]
nightstand_A[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.9360657360490148, 2.4767056595459023, 1.1]
wardrobe[0].rotation = [0, 0, 0]
king_size_bed[0].position = [0.4222675900162018, 2.4176359047554903, 0.6]
king_size_bed[0].rotation = [0, 0, 0]
nightstand_B[0].position = [2.5802697576469478, 2.9347837710796525, 0.35]
nightstand_B[0].rotation = [0, 0, 0]
tv_stand[0].position = [0.6084749586884393, 1.6229205484008766, 0.4]
tv_stand[0].rotation = [0, 0, 0]
nightstand_A[0].position = [0.12837939080854416, 0.6511123155567489, 0.35]
nightstand_A[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.9360657360490148, 2.4767056595459023, 1.1]
wardrobe[0].rotation = [0, 0, 0]
king_size_bed[0].position = [0.4222675900162018, 2.4176359047554903, 0.6]
king_size_bed[0].rotation = [0, 0, 0]
nightstand_B[0].position = [2.5802697576469478, 2.9347837710796525, 0.35]
nightstand_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the bed across the room so its +x-facing foot points toward the TV
# on the right wall. The nightstands sit on opposite sides of the bed, while
# the doorway area at the upper-left remains unobstructed.
tv_stand[0].position = [3.20, 2.50, 0.40]
tv_stand[0].rotation = [0, 0, radians(180)]

nightstand_A[0].position = [1.65, 1.05, 0.35]
nightstand_A[0].rotation = [0, 0, radians(0)]

wardrobe[0].position = [2.15, 4.88, 1.10]
wardrobe[0].rotation = [0, 0, radians(-90)]

king_size_bed[0].position = [1.65, 2.50, 0.60]
king_size_bed[0].rotation = [0, 0, radians(0)]

nightstand_B[0].position = [1.65, 3.95, 0.35]
nightstand_B[0].rotation = [0, 0, radians(0)]


# Fixed reference points preserve the intended zones while still allowing the
# relational constraints below to encode the important bedroom semantics.
tv_anchor = AssetInstance(position=[3.20, 2.50, 0.40])
nightstand_A_anchor = AssetInstance(position=[1.65, 1.05, 0.35])
wardrobe_anchor = AssetInstance(position=[2.15, 4.88, 1.10])
bed_anchor = AssetInstance(position=[1.65, 2.50, 0.60])
nightstand_B_anchor = AssetInstance(position=[1.65, 3.95, 0.35])

# The bed and TV face one another. These are the primary orientation
# constraints because the requested bed-to-TV relationship is essential.
solver.point_towards(king_size_bed[0], tv_stand[0])
solver.point_towards(tv_stand[0], king_size_bed[0])

# Keep the bed near its planned central position, leaving circulation space
# in front of the door and a clear aisle between the bed and TV stand.
solver.distance_constraint(
    king_size_bed[0], bed_anchor, 0.0, 0.15, weight=10
)

# Place the TV console against the right wall and near the bed's centerline.
solver.against_wall(tv_stand[0], walls[0])
solver.distance_constraint(
    tv_stand[0], tv_anchor, 0.0, 0.15, weight=10
)

# Put the wardrobe against the upper wall, beginning to the right of the
# 0.79 m doorway. It faces inward toward the bed.
solver.against_wall(wardrobe[0], walls[1])
solver.distance_constraint(
    wardrobe[0], wardrobe_anchor, 0.0, 0.12, weight=10
)
solver.point_towards(wardrobe[0], king_size_bed[0])

# The bed is exactly between the two nightstands: each center is 1.45 m from
# the bed center and the nightstand centers are 2.90 m apart. Given the bed's
# 2.10 m width and each nightstand's 0.70 m width along y, this produces a
# 0.05 m edge gap—within the requested 0.10 m for nightstand_A (o0001).
solver.distance_constraint(
    nightstand_A[0], king_size_bed[0], 1.45, 1.45, weight=10
)
solver.distance_constraint(
    nightstand_B[0], king_size_bed[0], 1.45, 1.45, weight=10
)
solver.distance_constraint(
    nightstand_B[0], nightstand_A[0], 2.90, 2.90, weight=10
)

# Positional anchors disambiguate which nightstand goes on each side of the
# bed and prevent either one from moving into the doorway or other furniture.
solver.distance_constraint(
    nightstand_A[0], nightstand_A_anchor, 0.0, 0.10, weight=10
)
solver.distance_constraint(
    nightstand_B[0], nightstand_B_anchor, 0.0, 0.10, weight=10
)

# Keep both nightstands parallel to the bed for a coherent furniture group.
solver.align_with(nightstand_A[0], king_size_bed[0])
solver.align_with(nightstand_B[0], king_size_bed[0])

solver.constraints = []
wardrobe[0].position = [2.1500000953674316, 4.879014492034912, 1.100000023841858]
wardrobe[0].rotation = [0, 0, -1.570918931993055]
wardrobe[0].optimize = 2
king_size_bed[0].position = [1.649999976158142, 2.5, 0.6000000238418579]
king_size_bed[0].rotation = [0, 0, 0.02827433441159227]
king_size_bed[0].optimize = 2
nightstand_A[0].position = [1.649999976158142, 1.0499999523162842, 0.3499999940395355]
nightstand_A[0].rotation = [0, 0, 0.028211639094088775]
nightstand_A[0].optimize = 2
tv_stand[0].position = [3.1999852657318115, 2.5, 0.4000000059604645]
tv_stand[0].rotation = [0, 0, -3.1414316407735887]
tv_stand[0].optimize = 2
nightstand_B[0].position = [1.649999976158142, 3.950000047683716, 0.3499999940395355]
nightstand_B[0].rotation = [0, 0, 0.028211639094088775]
nightstand_B[0].optimize = 2

