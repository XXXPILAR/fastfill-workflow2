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
    Wall(corner1=[3.39, 0.00, 0.00], corner2=[3.39, 4.17, 0.00]),
    Wall(corner1=[3.39, 4.17, 0.00], corner2=[0.00, 4.17, 0.00]),
    Wall(corner1=[0.00, 4.17, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.39, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
combination_sofa = Assets(description="combination sofa", size=[1.45, 2.20, 0.85], placements=[AssetInstance() for _ in range(1)])
stool_A = Assets(description="stool", size=[0.40, 0.40, 0.45], placements=[AssetInstance() for _ in range(1)])
wardrobe_A = Assets(description="wardrobe", size=[0.60, 1.20, 2.20], placements=[AssetInstance() for _ in range(1)])
wardrobe_B = Assets(description="wardrobe", size=[0.60, 0.90, 2.20], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[2.30, 1.60, 0.01], placements=[AssetInstance() for _ in range(1)])
stool_B = Assets(description="stool", size=[0.45, 0.45, 0.43], placements=[AssetInstance() for _ in range(1)])

combination_sofa[0].instance_id = 'combination_sofa_0'
stool_A[0].instance_id = 'stool_A_0'
wardrobe_A[0].instance_id = 'wardrobe_A_0'
wardrobe_B[0].instance_id = 'wardrobe_B_0'
carpet[0].instance_id = 'carpet_0'
stool_B[0].instance_id = 'stool_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

combination_sofa[0].position = [2.092093648047313, 2.7406108531218543, 0.425]
combination_sofa[0].rotation = [0, 0, 0]
stool_A[0].position = [2.306850501008082, 0.6646190944327305, 0.225]
stool_A[0].rotation = [0, 0, 0]
wardrobe_A[0].position = [0.5752830616141674, 4.144435060964386, 1.1]
wardrobe_A[0].rotation = [0, 0, 0]
wardrobe_B[0].position = [2.9093716193639714, 1.7149768998391581, 1.1]
wardrobe_B[0].rotation = [0, 0, 0]
carpet[0].position = [0.1741786517304813, 0.7532749470130055, 0.0075]
carpet[0].rotation = [0, 0, 0]
stool_B[0].position = [0.6116859770641904, 2.130517592865895, 0.215]
stool_B[0].rotation = [0, 0, 0]
combination_sofa[0].position = [2.092093648047313, 2.7406108531218543, 0.425]
combination_sofa[0].rotation = [0, 0, 0]
stool_A[0].position = [2.306850501008082, 0.6646190944327305, 0.225]
stool_A[0].rotation = [0, 0, 0]
wardrobe_A[0].position = [0.5752830616141674, 4.144435060964386, 1.1]
wardrobe_A[0].rotation = [0, 0, 0]
wardrobe_B[0].position = [2.9093716193639714, 1.7149768998391581, 1.1]
wardrobe_B[0].rotation = [0, 0, 0]
carpet[0].position = [0.1741786517304813, 0.7532749470130055, 0.0075]
carpet[0].rotation = [0, 0, 0]
stool_B[0].position = [0.6116859770641904, 2.130517592865895, 0.215]
stool_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the supplied wall coordinates: the room spans x=0..3.39, y=0..4.17.
# The sofa faces east toward wardrobe_A, with its back against the west wall.
combination_sofa[0].position = [0.725, 1.40, 0.425]
combination_sofa[0].rotation = [0, 0, 0]

# Both wardrobes face west. Their footprints leave the northeast entrance
# and the floor immediately inside the door unobstructed.
wardrobe_A[0].position = [3.09, 1.40, 1.10]
wardrobe_A[0].rotation = [0, 0, radians(180)]

wardrobe_B[0].position = [3.09, 2.55, 1.10]
wardrobe_B[0].rotation = [0, 0, radians(180)]

# A low stool near the southeast corner does not obstruct the window,
# whose horizontal extent is x=0.90..2.50 along the south wall.
stool_A[0].position = [2.85, 0.30, 0.225]
stool_A[0].rotation = [0, 0, radians(180)]

# The sofa ends at x=1.45; this stool starts at x=1.50.
# Thus their bounding-box surfaces are only 0.05 m apart.
stool_B[0].position = [1.725, 1.40, 0.215]
stool_B[0].rotation = [0, 0, radians(180)]

# The carpet occupies x=0.02..2.32, y=2.56..4.16.
# It does not intersect any furniture footprint or the doorway
# (x=2.44..3.34 on the north wall).
carpet[0].position = [1.17, 3.36, 0.005]
carpet[0].rotation = [0, 0, 0]

# High-priority position constraints preserve the clearances, including the
# entrance approach. Fixed points are references, not additional scene assets.
for asset_group in (
    combination_sofa, wardrobe_A, wardrobe_B, stool_A, stool_B, carpet
):
    solver.distance_constraint(
        asset_group[0],
        AssetInstance(position=list(asset_group[0].position)),
        0, 0,
        weight=10,
    )

# Primary wall and facing requirements.
solver.against_wall(combination_sofa[0], walls[2])
solver.point_towards(combination_sofa[0], wardrobe_A[0])

solver.against_wall(wardrobe_A[0], walls[0])
solver.point_towards(wardrobe_A[0], combination_sofa[0])

solver.against_wall(wardrobe_B[0], walls[0])
solver.align_with(wardrobe_B[0], wardrobe_A[0])

# distance_constraint measures 3D center distance, not surface clearance.
# With a 0.05 m surface gap, horizontal center separation is
# 1.45/2 + 0.45/2 + 0.05 = 1.00 m; center heights differ by 0.21 m.
solver.distance_constraint(
    stool_B[0],
    combination_sofa[0],
    (1.00**2 + 0.21**2)**0.5,
    (1.05**2 + 0.21**2)**0.5,
    weight=10,
)
solver.point_towards(stool_B[0], combination_sofa[0])

solver.align_with(stool_A[0], wardrobe_A[0])
solver.align_with(carpet[0], combination_sofa[0])

# Both stools are floor-standing furniture, and the carpet lies on the floor;
# none of these assets requires an on_top_of constraint.

solver.constraints = []
carpet[0].position = [1.1699999570846558, 3.359999895095825, 0.004999999888241291]
carpet[0].rotation = [0, 0, 2.1030890183110348e-08]
carpet[0].optimize = 2
wardrobe_A[0].position = [3.093508720397949, 1.399999976158142, 1.100000023841858]
wardrobe_A[0].rotation = [0, 0, -3.141592607998276]
wardrobe_A[0].optimize = 2
stool_A[0].position = [2.8499999046325684, 0.30000001192092896, 0.22499999403953552]
stool_A[0].rotation = [0, 0, -3.141592610079875]
stool_A[0].optimize = 2
combination_sofa[0].position = [0.7250000238418579, 1.399999976158142, 0.42500001192092896]
combination_sofa[0].rotation = [0, 0, 2.9387267571866217e-08]
combination_sofa[0].optimize = 2
wardrobe_B[0].position = [3.0935089588165283, 2.549999952316284, 1.100000023841858]
wardrobe_B[0].rotation = [0, 0, -3.1415926093111866]
wardrobe_B[0].optimize = 2
stool_B[0].position = [1.8250573873519897, 1.399999976158142, 0.2150000035762787]
stool_B[0].rotation = [0, 0, -3.1290262823329655]
stool_B[0].optimize = 2

