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
    Wall(corner1=[4.59, 7.20, 0.00], corner2=[4.59, 3.79, 0.00]),
    Wall(corner1=[4.59, 3.79, 0.00], corner2=[0.00, 3.79, 0.00]),
    Wall(corner1=[0.00, 3.79, 0.00], corner2=[0.00, 2.73, 0.00]),
    Wall(corner1=[0.00, 2.73, 0.00], corner2=[4.99, 2.73, 0.00]),
    Wall(corner1=[4.99, 2.73, 0.00], corner2=[4.99, 0.00, 0.00]),
    Wall(corner1=[4.99, 0.00, 0.00], corner2=[7.97, 0.00, 0.00]),
    Wall(corner1=[7.97, 0.00, 0.00], corner2=[7.97, 7.20, 0.00]),
    Wall(corner1=[7.97, 7.20, 0.00], corner2=[4.59, 7.20, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
dining_chair_A = Assets(description="dining chair", size=[0.55, 0.48, 0.88], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[2.00, 3.00, 0.02], placements=[AssetInstance() for _ in range(1)])
dining_chair_B = Assets(description="dining chair", size=[0.55, 0.48, 0.88], placements=[AssetInstance() for _ in range(1)])
air_conditioner = Assets(description="air conditioner", size=[0.22, 0.90, 0.30], placements=[AssetInstance() for _ in range(1)])
dining_table = Assets(description="dining table", size=[0.90, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
dining_chair_C = Assets(description="dining chair", size=[0.55, 0.48, 0.88], placements=[AssetInstance() for _ in range(1)])
dining_chair_D = Assets(description="dining chair", size=[0.55, 0.48, 0.88], placements=[AssetInstance() for _ in range(1)])
combination_sofa = Assets(description="combination sofa", size=[2.10, 3.20, 0.85], placements=[AssetInstance() for _ in range(1)])

dining_chair_A[0].instance_id = 'dining_chair_A_0'
carpet[0].instance_id = 'carpet_0'
dining_chair_B[0].instance_id = 'dining_chair_B_0'
air_conditioner[0].instance_id = 'air_conditioner_0'
dining_table[0].instance_id = 'dining_table_0'
dining_chair_C[0].instance_id = 'dining_chair_C_0'
dining_chair_D[0].instance_id = 'dining_chair_D_0'
combination_sofa[0].instance_id = 'combination_sofa_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

dining_chair_A[0].position = [2.881539300000593, 3.3816185433159087, 0.44]
dining_chair_A[0].rotation = [0, 0, 0]
carpet[0].position = [6.602986710530245, 0.15165933055840253, 0.01]
carpet[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [7.488202865170623, 6.669611214201251, 0.44]
dining_chair_B[0].rotation = [0, 0, 0]
air_conditioner[0].position = [6.845082151786761, 4.951812825177504, 0.15]
air_conditioner[0].rotation = [0, 0, 0]
dining_table[0].position = [2.5906431266733954, 3.6934544712409223, 0.375]
dining_table[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [7.222492248124123, 1.933216089268554, 0.44]
dining_chair_C[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [4.858619738260773, 5.098833553775438, 0.44]
dining_chair_D[0].rotation = [0, 0, 0]
combination_sofa[0].position = [4.639031826283601, 6.0978421004128425, 0.425]
combination_sofa[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [2.881539300000593, 3.3816185433159087, 0.44]
dining_chair_A[0].rotation = [0, 0, 0]
carpet[0].position = [6.602986710530245, 0.15165933055840253, 0.01]
carpet[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [7.488202865170623, 6.669611214201251, 0.44]
dining_chair_B[0].rotation = [0, 0, 0]
air_conditioner[0].position = [6.845082151786761, 4.951812825177504, 0.15]
air_conditioner[0].rotation = [0, 0, 0]
dining_table[0].position = [2.5906431266733954, 3.6934544712409223, 0.375]
dining_table[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [7.222492248124123, 1.933216089268554, 0.44]
dining_chair_C[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [4.858619738260773, 5.098833553775438, 0.44]
dining_chair_D[0].rotation = [0, 0, 0]
combination_sofa[0].position = [4.639031826283601, 6.0978421004128425, 0.425]
combination_sofa[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed references preserve the planned furniture centers while allowing the
# solver to make small feasibility adjustments through the semantic constraints.
chair_A_anchor = AssetInstance(position=[6.65, 0.62, 0.44])
chair_B_anchor = AssetInstance(position=[6.65, 2.38, 0.44])
chair_C_anchor = AssetInstance(position=[7.30, 0.62, 0.44])
chair_D_anchor = AssetInstance(position=[7.30, 2.38, 0.44])
table_anchor = AssetInstance(position=[6.75, 1.50, 0.375])
carpet_anchor = AssetInstance(position=[6.92, 4.65, 0.01])
sofa_anchor = AssetInstance(position=[6.92, 4.65, 0.445])
air_conditioner_anchor = AssetInstance(position=[7.86, 5.40, 2.40])

# A zero-rotation reference is used to constrain absolute headings.
heading_reference = AssetInstance(position=[0.0, 0.0, 0.0])

# Interior targets make the sofa and wall-mounted air conditioner face into
# the room from the right-hand wall.
sofa_interior_target = AssetInstance(position=[5.20, 4.65, 0.445])
air_conditioner_interior_target = AssetInstance(position=[6.50, 5.40, 2.40])

# Place the dining group in the lower-right room. Its left edge remains about
# 0.95 m from the door in wall x=4.99, while furniture near the bottom is kept
# to the right of the bottom doorway's x-range.
dining_table[0].position = [6.75, 1.50, 0.375]
dining_table[0].rotation = [0, 0, radians(90)]

dining_chair_A[0].position = [6.65, 0.62, 0.44]
dining_chair_A[0].rotation = [0, 0, radians(90)]
dining_chair_B[0].position = [6.65, 2.38, 0.44]
dining_chair_B[0].rotation = [0, 0, radians(-90)]

dining_chair_C[0].position = [7.30, 0.62, 0.44]
dining_chair_C[0].rotation = [0, 0, radians(90)]
dining_chair_D[0].position = [7.30, 2.38, 0.44]
dining_chair_D[0].rotation = [0, 0, radians(-90)]

# Chair A and chair B occupy opposite sides of the table, so the table is
# directly between them as required. Chairs C and D complete the four-seat set.
solver.distance_constraint(
    dining_table[0], table_anchor, 0.0, 0.0, weight=10
)
solver.align_with(dining_table[0], heading_reference, angle=90)

solver.distance_constraint(
    dining_chair_A[0], chair_A_anchor, 0.0, 0.0, weight=10
)
solver.point_towards(dining_chair_A[0], dining_table[0])
solver.distance_constraint(
    dining_chair_A[0], dining_table[0], 0.88, 0.90, weight=1
)

solver.distance_constraint(
    dining_chair_B[0], chair_B_anchor, 0.0, 0.0, weight=10
)
solver.point_towards(dining_chair_B[0], dining_table[0])
solver.distance_constraint(
    dining_chair_B[0], dining_table[0], 0.88, 0.90, weight=1
)

solver.distance_constraint(
    dining_chair_C[0], chair_C_anchor, 0.0, 0.0, weight=10
)
solver.point_towards(dining_chair_C[0], dining_table[0])
solver.distance_constraint(
    dining_chair_C[0], dining_table[0], 1.02, 1.05, weight=1
)

solver.distance_constraint(
    dining_chair_D[0], chair_D_anchor, 0.0, 0.0, weight=10
)
solver.point_towards(dining_chair_D[0], dining_table[0])
solver.distance_constraint(
    dining_chair_D[0], dining_table[0], 1.02, 1.05, weight=1
)

# Put the carpet and sofa in the larger upper-right area. The sofa is against
# the right wall and faces left into the room. Its northern edge stops near
# y=6.25, preserving an approximately 0.95 m-deep clear approach to the top door.
carpet[0].position = [6.92, 4.65, 0.01]
carpet[0].rotation = [0, 0, radians(180)]

combination_sofa[0].position = [6.92, 4.65, 0.445]
combination_sofa[0].rotation = [0, 0, radians(180)]

solver.distance_constraint(
    carpet[0], carpet_anchor, 0.0, 0.0, weight=10
)
solver.align_with(carpet[0], combination_sofa[0])

solver.distance_constraint(
    combination_sofa[0], sofa_anchor, 0.0, 0.0, weight=10
)
solver.against_wall(combination_sofa[0], walls[6])
solver.point_towards(combination_sofa[0], sofa_interior_target)
solver.on_top_of(combination_sofa[0], carpet[0])

# Mount the air conditioner high on the right wall, above the sofa zone, with
# its front directed toward the room interior.
air_conditioner[0].position = [7.86, 5.40, 2.40]
air_conditioner[0].rotation = [0, 0, radians(180)]

solver.distance_constraint(
    air_conditioner[0], air_conditioner_anchor, 0.0, 0.0, weight=10
)
solver.against_wall(air_conditioner[0], walls[6])
solver.point_towards(air_conditioner[0], air_conditioner_interior_target)

solver.constraints = []
combination_sofa[0].position = [6.48930025100708, 4.650000095367432, 0.445000022649765]
combination_sofa[0].rotation = [0, 0, -2.0182980585685577]
combination_sofa[0].optimize = 2
dining_chair_C[0].position = [7.300000190734863, 0.6200000047683716, 0.4399999976158142]
dining_chair_C[0].rotation = [0, 0, 1.5833626980517244]
dining_chair_C[0].optimize = 2
air_conditioner[0].position = [7.860257625579834, 5.400000095367432, 0.15000000596046448]
air_conditioner[0].rotation = [0, 0, -3.1413399318620727]
air_conditioner[0].optimize = 2
dining_chair_D[0].position = [7.300000190734863, 2.380000114440918, 0.4399999976158142]
dining_chair_D[0].rotation = [0, 0, -1.5582299555380688]
dining_chair_D[0].optimize = 2
dining_chair_B[0].position = [6.650000095367432, 2.380000114440918, 0.4399999976158142]
dining_chair_B[0].rotation = [0, 0, -1.5582299555380688]
dining_chair_B[0].optimize = 2
dining_table[0].position = [6.75, 1.5, 0.375]
dining_table[0].rotation = [0, 0, 1.605353845621573]
dining_table[0].optimize = 2
dining_chair_A[0].position = [6.650000095367432, 0.6200000047683716, 0.4399999976158142]
dining_chair_A[0].rotation = [0, 0, 1.5833626980517244]
dining_chair_A[0].optimize = 2
carpet[0].position = [6.378252983093262, 4.650000095367432, 0.009999999776482582]
carpet[0].rotation = [0, 0, -2.021266746745188]
carpet[0].optimize = 2

