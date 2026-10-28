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
    Wall(corner1=[0.00, 3.93, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.49, 0.00, 0.00]),
    Wall(corner1=[3.49, 0.00, 0.00], corner2=[3.49, 3.93, 0.00]),
    Wall(corner1=[3.49, 3.93, 0.00], corner2=[2.85, 3.93, 0.00]),
    Wall(corner1=[2.85, 3.93, 0.00], corner2=[2.85, 4.72, 0.00]),
    Wall(corner1=[2.85, 4.72, 0.00], corner2=[0.97, 4.72, 0.00]),
    Wall(corner1=[0.97, 4.72, 0.00], corner2=[0.97, 3.93, 0.00]),
    Wall(corner1=[0.97, 3.93, 0.00], corner2=[0.00, 3.93, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
tv_stand = Assets(description="A sleek, modern media console with a dark wood finish and a minimalist design. It features a long rectangular shape with thin legs and an open shelf section on one side.", size=[0.40, 1.60, 0.50], placements=[AssetInstance() for _ in range(1)])
single_bed = Assets(description="A modern bed with a teal base and a mustard-yellow headboard. It features gray bedding and multiple pillows arranged neatly.", size=[2.05, 1.00, 1.05], placements=[AssetInstance() for _ in range(1)])
nightstand_A = Assets(description="A rectangular cabinet with a smooth surface and a small object placed nearby.", size=[0.40, 0.45, 0.50], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="A tall, rectangular wardrobe with a smooth surface and a single door on one side. It features an open shelving unit on the other side with multiple compartments for storage. The design includes a decorative circular element on the door.", size=[0.58, 1.20, 2.10], placements=[AssetInstance() for _ in range(1)])
cushion = Assets(description="A beige cushion with a smooth texture, resting on a black surface. The cushion appears soft and slightly rounded at the edges.", size=[0.16, 0.50, 0.50], placements=[AssetInstance() for _ in range(1)])
nightstand_B = Assets(description="A rectangular cabinet with a smooth surface and a small object placed nearby.", size=[0.40, 0.45, 0.50], placements=[AssetInstance() for _ in range(1)])

tv_stand[0].instance_id = 'tv_stand_0'
single_bed[0].instance_id = 'single_bed_0'
nightstand_A[0].instance_id = 'nightstand_A_0'
wardrobe[0].instance_id = 'wardrobe_0'
cushion[0].instance_id = 'cushion_0'
nightstand_B[0].instance_id = 'nightstand_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

tv_stand[0].position = [0.3870568996533911, 1.975051071827346, 0.25]
tv_stand[0].rotation = [0, 0, 0]
single_bed[0].position = [0.23000556000195346, 2.9700443814492243, 0.525]
single_bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [2.923237044558027, 1.1318680614927141, 0.25]
nightstand_A[0].rotation = [0, 0, 0]
wardrobe[0].position = [3.4185526424199164, 1.5453987907373008, 1.05]
wardrobe[0].rotation = [0, 0, 0]
cushion[0].position = [0.7394607509878965, 1.9720608111746123, 0.25]
cushion[0].rotation = [0, 0, 0]
nightstand_B[0].position = [1.8230462308403934, 2.555055498260697, 0.25]
nightstand_B[0].rotation = [0, 0, 0]
tv_stand[0].position = [0.3870568996533911, 1.975051071827346, 0.25]
tv_stand[0].rotation = [0, 0, 0]
single_bed[0].position = [0.23000556000195346, 2.9700443814492243, 0.525]
single_bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [2.923237044558027, 1.1318680614927141, 0.25]
nightstand_A[0].rotation = [0, 0, 0]
wardrobe[0].position = [3.4185526424199164, 1.5453987907373008, 1.05]
wardrobe[0].rotation = [0, 0, 0]
cushion[0].position = [0.7394607509878965, 1.9720608111746123, 0.25]
cushion[0].rotation = [0, 0, 0]
nightstand_B[0].position = [1.8230462308403934, 2.555055498260697, 0.25]
nightstand_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the bed along the left wall, facing across the room toward the TV.
# The two nightstands flank the bed along the y-axis, placing the bed between them.
single_bed[0].position = [1.025, 2.30, 0.525]
single_bed[0].rotation = [0, 0, radians(0)]

nightstand_A[0].position = [0.20, 1.55, 0.25]
nightstand_A[0].rotation = [0, 0, radians(0)]

nightstand_B[0].position = [0.20, 3.05, 0.25]
nightstand_B[0].rotation = [0, 0, radians(0)]

# Place the TV console against the opposite wall, facing the bed.
tv_stand[0].position = [3.29, 2.30, 0.25]
tv_stand[0].rotation = [0, 0, radians(180)]

# Place the wardrobe against the bottom wall, away from the bed and its access aisle.
wardrobe[0].position = [0.75, 0.29, 1.05]
wardrobe[0].rotation = [0, 0, radians(90)]

# Center the cushion on top of the bed. The on_top_of constraint will refine its height.
cushion[0].position = [1.25, 2.30, 1.30]
cushion[0].rotation = [0, 0, radians(0)]


# Primary wall and facing relationships.
solver.against_wall(single_bed[0], walls[0])
solver.point_towards(single_bed[0], tv_stand[0])

solver.against_wall(tv_stand[0], walls[2])
solver.point_towards(tv_stand[0], single_bed[0])

# Keep each nightstand against the bed's headboard wall and parallel to the bed.
solver.against_wall(nightstand_A[0], walls[0])
solver.align_with(nightstand_A[0], single_bed[0])
solver.distance_constraint(
    nightstand_A[0], single_bed[0],
    min_distance=1.05, max_distance=1.15, weight=10
)

solver.against_wall(nightstand_B[0], walls[0])
solver.align_with(nightstand_B[0], single_bed[0])
solver.distance_constraint(
    nightstand_B[0], single_bed[0],
    min_distance=1.05, max_distance=1.15, weight=10
)

# Preserve a practical viewing distance between the bed and television console.
solver.distance_constraint(
    single_bed[0], tv_stand[0],
    min_distance=2.15, max_distance=2.40, weight=10
)
solver.distance_constraint(
    tv_stand[0], single_bed[0],
    min_distance=2.15, max_distance=2.40, weight=10
)

# The wardrobe sits flush with the bottom wall and faces into the room.
solver.against_wall(wardrobe[0], walls[1])
solver.align_with(wardrobe[0], single_bed[0], angle=90)
solver.distance_constraint(
    wardrobe[0], tv_stand[0],
    min_distance=2.70, max_distance=3.60
)

# Keep the cushion supported by, centered near, and aligned with the bed.
solver.on_top_of(cushion[0], single_bed[0])
solver.distance_constraint(
    cushion[0], single_bed[0],
    min_distance=0.70, max_distance=0.90, weight=10
)
solver.align_with(cushion[0], single_bed[0])

solver.constraints = []
single_bed[0].position = [1.901764154434204, 3.598060131072998, 0.5249999761581421]
single_bed[0].rotation = [0, 0, -0.15401456262455446]
single_bed[0].optimize = 2
nightstand_A[0].position = [0.9078145027160645, 2.873974561691284, 0.25]
nightstand_A[0].rotation = [0, 0, 4.1018038218868664e-08]
nightstand_A[0].optimize = 2
wardrobe[0].position = [0.75, 0.6006634831428528, 1.0499999523162842]
wardrobe[0].rotation = [0, 0, -9.642456932702108e-07]
wardrobe[0].optimize = 2
tv_stand[0].position = [3.290799856185913, 1.9148682355880737, 0.25]
tv_stand[0].rotation = [0, 0, -3.141592611532133]
tv_stand[0].optimize = 2
nightstand_B[0].position = [0.6707183718681335, 3.578519821166992, 0.25]
nightstand_B[0].rotation = [0, 0, 4.0514037148808115e-08]
nightstand_B[0].optimize = 2
cushion[0].position = [1.6816990375518799, 3.126234531402588, 1.2999999523162842]
cushion[0].rotation = [0, 0, -0.15737519021391463]
cushion[0].optimize = 2

