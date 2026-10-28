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
    Wall(corner1=[3.63, 3.83, 0.00], corner2=[0.00, 3.83, 0.00]),
    Wall(corner1=[0.00, 3.83, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.63, 0.00, 0.00]),
    Wall(corner1=[3.63, 0.00, 0.00], corner2=[3.63, 3.83, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
side_table_A = Assets(description="A rectangular dining table with sleek, angled legs that taper towards the bottom. The table has a smooth surface and a minimalist design.", size=[0.40, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
king_size_bed = Assets(description="A neatly made bed with a beige upholstered headboard, gray bedding, and decorative pillows.", size=[2.03, 1.93, 1.15], placements=[AssetInstance() for _ in range(1)])
side_table_B = Assets(description="A rectangular dining table with sleek, angled legs that taper towards the bottom. The table has a smooth surface and a minimalist design.", size=[0.40, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])

side_table_A[0].instance_id = 'side_table_A_0'
king_size_bed[0].instance_id = 'king_size_bed_0'
side_table_B[0].instance_id = 'side_table_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

side_table_A[0].position = [1.394596336655209, 0.6196010296239607, 0.275]
side_table_A[0].rotation = [0, 0, 0]
king_size_bed[0].position = [2.7595264260604497, 0.5730353266057563, 0.575]
king_size_bed[0].rotation = [0, 0, 0]
side_table_B[0].position = [1.7893876769420007, 1.4360187304074186, 0.275]
side_table_B[0].rotation = [0, 0, 0]
side_table_A[0].position = [1.394596336655209, 0.6196010296239607, 0.275]
side_table_A[0].rotation = [0, 0, 0]
king_size_bed[0].position = [2.7595264260604497, 0.5730353266057563, 0.575]
king_size_bed[0].rotation = [0, 0, 0]
side_table_B[0].position = [1.7893876769420007, 1.4360187304074186, 0.275]
side_table_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the bed with its headboard against the uninterrupted right wall. This
# avoids the window on the north wall and leaves the doorway area in the
# southwest corner clear. The two tables flank the bed along the y-axis.
king_size_bed[0].position = [2.615, 1.915, 0.575]
king_size_bed[0].rotation = [0, 0, radians(180)]

side_table_A[0].position = [3.43, 0.65, 0.275]
side_table_A[0].rotation = [0, 0, radians(180)]

side_table_B[0].position = [3.43, 3.18, 0.275]
side_table_B[0].rotation = [0, 0, radians(180)]

# Fixed reference points preserve the intended locations along the right wall.
bed_anchor = AssetInstance(position=[2.615, 1.915, 0.575])
table_A_anchor = AssetInstance(position=[3.43, 0.65, 0.275])
table_B_anchor = AssetInstance(position=[3.43, 3.18, 0.275])
roomward_reference = AssetInstance(position=[0.00, 1.915, 0.575])

# The bed's wall contact is the highest-priority placement requirement.
solver.against_wall(king_size_bed[0], walls[3])
solver.distance_constraint(
    king_size_bed[0], bed_anchor,
    min_distance=0.0, max_distance=0.0, weight=10
)
solver.point_towards(king_size_bed[0], roomward_reference)

# Keep the first table beside the lower side of the bed and against the same
# wall. The center-distance interval corresponds to a small edge clearance.
solver.against_wall(side_table_A[0], walls[3])
solver.distance_constraint(
    side_table_A[0], table_A_anchor,
    min_distance=0.0, max_distance=0.0, weight=10
)
solver.distance_constraint(
    side_table_A[0], king_size_bed[0],
    min_distance=1.45, max_distance=1.55, weight=5
)
solver.align_with(side_table_A[0], king_size_bed[0])

# Keep the second table beside the upper side of the bed. Its approximately
# 0.05 m edge gap satisfies the requirement that it be within 0.10 m of the
# bed while avoiding overlap.
solver.against_wall(side_table_B[0], walls[3])
solver.distance_constraint(
    side_table_B[0], table_B_anchor,
    min_distance=0.0, max_distance=0.0, weight=10
)
solver.distance_constraint(
    king_size_bed[0], side_table_B[0],
    min_distance=1.45, max_distance=1.55, weight=10
)
solver.align_with(side_table_B[0], king_size_bed[0])

solver.constraints = []
side_table_A[0].position = [3.428999662399292, 0.6499999761581421, 0.2750000059604645]
side_table_A[0].rotation = [0, 0, -3.141592492355978]
side_table_A[0].optimize = 2
king_size_bed[0].position = [2.613999843597412, 1.9149999618530273, 0.574999988079071]
king_size_bed[0].rotation = [0, 0, -3.141592425114018]
king_size_bed[0].optimize = 2
side_table_B[0].position = [3.428999662399292, 3.180000066757202, 0.2750000059604645]
side_table_B[0].rotation = [0, 0, -3.141592492355978]
side_table_B[0].optimize = 2

