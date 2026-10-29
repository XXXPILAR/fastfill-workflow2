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
    Wall(corner1=[1.72, 0.96, 0.00], corner2=[0.00, 0.96, 0.00]),
    Wall(corner1=[0.00, 0.96, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[5.61, 0.00, 0.00]),
    Wall(corner1=[5.61, 0.00, 0.00], corner2=[5.61, 3.58, 0.00]),
    Wall(corner1=[5.61, 3.58, 0.00], corner2=[1.72, 3.58, 0.00]),
    Wall(corner1=[1.72, 3.58, 0.00], corner2=[1.72, 0.96, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
wardrobe = Assets(description="wardrobe", size=[0.60, 2.00, 2.30], placements=[AssetInstance() for _ in range(1)])
nightstand_A = Assets(description="nightstand", size=[0.40, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
nightstand_B = Assets(description="nightstand", size=[0.40, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.10, 1.80, 1.05], placements=[AssetInstance() for _ in range(1)])

wardrobe[0].instance_id = 'wardrobe_0'
nightstand_A[0].instance_id = 'nightstand_A_0'
nightstand_B[0].instance_id = 'nightstand_B_0'
bed[0].instance_id = 'bed_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

wardrobe[0].position = [1.9947912649532933, 0.6215935742943416, 1.15]
wardrobe[0].rotation = [0, 0, 0]
nightstand_A[0].position = [2.3763469178932484, 2.8056192264940187, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
nightstand_B[0].position = [2.31322833604438, 0.4794405572459132, 0.275]
nightstand_B[0].rotation = [0, 0, 0]
bed[0].position = [3.6069294283653752, 2.6809243966336123, 0.525]
bed[0].rotation = [0, 0, 0]
wardrobe[0].position = [1.9947912649532933, 0.6215935742943416, 1.15]
wardrobe[0].rotation = [0, 0, 0]
nightstand_A[0].position = [2.3763469178932484, 2.8056192264940187, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
nightstand_B[0].position = [2.31322833604438, 0.4794405572459132, 0.275]
nightstand_B[0].rotation = [0, 0, 0]
bed[0].position = [3.6069294283653752, 2.6809243966336123, 0.525]
bed[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the east wall for the headboard, with one nightstand on either side.
# The entire entrance alcove remains empty, keeping both door approaches clear.
bed[0].position = [4.56, 1.79, bed.size[2] / 2]
bed[0].rotation = [0, 0, radians(180)]

nightstand_A[0].position = [5.41, 0.54, nightstand_A.size[2] / 2]
nightstand_A[0].rotation = [0, 0, radians(180)]

nightstand_B[0].position = [5.41, 3.04, nightstand_B.size[2] / 2]
nightstand_B[0].rotation = [0, 0, radians(180)]

# The wardrobe occupies the west wall of the main room, facing east.
# Its footprint ends at x=2.32; the bed starts at x=3.51, leaving
# a 1.19 m aisle for circulation and wardrobe access.
wardrobe[0].position = [2.02, 2.35, wardrobe.size[2] / 2]
wardrobe[0].rotation = [0, 0, 0]

# Fixed layout references preserve the selected sides of the bed and
# prevent the furniture from drifting into the entrance circulation area.
# These are constraint references, not additional physical furniture.
for furniture in (bed, nightstand_A, nightstand_B, wardrobe):
    layout_reference = AssetInstance(
        position=list(furniture[0].position),
        rotation=list(furniture[0].rotation),
    )
    solver.distance_constraint(
        furniture[0], layout_reference, 0, 0, weight=10
    )
    solver.align_with(furniture[0], layout_reference)

# All three bedside pieces meet the east wall; both nightstands face
# the same direction as the bed. Each has a 0.10 m lateral gap to the bed.
solver.against_wall(bed[0], walls[3])
solver.against_wall(nightstand_A[0], walls[3])
solver.against_wall(nightstand_B[0], walls[3])
solver.against_wall(wardrobe[0], walls[5])

solver.align_with(nightstand_A[0], bed[0])
solver.align_with(nightstand_B[0], bed[0])
solver.align_with(wardrobe[0], bed[0], angle=180)

# Distances use bounding-box centers, including their height difference.
bedside_distance = (
    0.85**2
    + 1.25**2
    + ((bed.size[2] - nightstand_A.size[2]) / 2)**2
) ** 0.5

solver.distance_constraint(
    nightstand_A[0], bed[0],
    bedside_distance, bedside_distance, weight=10
)
solver.distance_constraint(
    nightstand_B[0], bed[0],
    bedside_distance, bedside_distance, weight=10
)
solver.distance_constraint(
    nightstand_B[0], nightstand_A[0], 2.50, 2.50, weight=10
)

solver.constraints = []
bed[0].position = [4.467860698699951, 1.7899999618530273, 0.5249999761581421]
bed[0].rotation = [0, 0, -1.8275534337331019]
bed[0].optimize = 2
wardrobe[0].position = [2.0147705078125, 2.3499999046325684, 1.149999976158142]
wardrobe[0].rotation = [0, 0, 0.00018429860940103165]
wardrobe[0].optimize = 2
nightstand_A[0].position = [5.4049482345581055, 0.4819970428943634, 0.2750000059604645]
nightstand_A[0].rotation = [0, 0, 3.141385884936725]
nightstand_A[0].optimize = 2
nightstand_B[0].position = [5.40495491027832, 2.9788639545440674, 0.2750000059604645]
nightstand_B[0].rotation = [0, 0, 3.141413061631467]
nightstand_B[0].optimize = 2

