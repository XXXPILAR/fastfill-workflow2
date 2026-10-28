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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[9.02, 0.00, 0.00]),
    Wall(corner1=[9.02, 0.00, 0.00], corner2=[9.02, 6.50, 0.00]),
    Wall(corner1=[9.02, 6.50, 0.00], corner2=[0.00, 6.50, 0.00]),
    Wall(corner1=[0.00, 6.50, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
wardrobe = Assets(description="A light-colored wooden cabinet with two doors and a countertop. It features a small drawer above the doors and a wine rack inside one of the compartments.", size=[0.60, 1.20, 0.95], placements=[AssetInstance() for _ in range(1)])
grill = Assets(description="A robust outdoor kitchen island featuring a built-in grill, storage cabinets, and a countertop. The design includes a combination of dark stone-like materials for the body and a metallic finish for the grill area.", size=[0.90, 2.40, 1.20], placements=[AssetInstance() for _ in range(1)])
stool_A = Assets(description="A modern bar stool with a sleek design featuring a black seat and light-colored metal legs. The legs are thin and form a square base for stability.", size=[0.45, 0.45, 0.75], placements=[AssetInstance() for _ in range(1)])
stool_B = Assets(description="A modern bar stool with a sleek design featuring a black seat and light-colored metal legs. The legs are thin and form a square base for stability.", size=[0.45, 0.45, 0.75], placements=[AssetInstance() for _ in range(1)])
bench = Assets(description="A wooden shelf unit with multiple compartments designed for storage or display purposes. It features a clean and simple design with a light wood finish.", size=[0.40, 1.50, 0.90], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="A wooden dining table with a rectangular top and sturdy legs that feature an X-shaped support design.", size=[1.00, 2.20, 0.76], placements=[AssetInstance() for _ in range(1)])
stool_C = Assets(description="A modern bar stool with a sleek design featuring a black seat and light-colored metal legs. The legs are thin and form a square base for stability.", size=[0.45, 0.45, 0.75], placements=[AssetInstance() for _ in range(1)])
stool_D = Assets(description="A modern bar stool with a sleek design featuring a black seat and light-colored metal legs. The legs are thin and form a square base for stability.", size=[0.45, 0.45, 0.75], placements=[AssetInstance() for _ in range(1)])

wardrobe[0].instance_id = 'wardrobe_0'
grill[0].instance_id = 'grill_0'
stool_A[0].instance_id = 'stool_A_0'
stool_B[0].instance_id = 'stool_B_0'
bench[0].instance_id = 'bench_0'
table[0].instance_id = 'table_0'
stool_C[0].instance_id = 'stool_C_0'
stool_D[0].instance_id = 'stool_D_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

wardrobe[0].position = [4.258091127578372, 6.151995928528996, 0.475]
wardrobe[0].rotation = [0, 0, 0]
grill[0].position = [7.417901336117139, 2.8386866889944877, 0.6]
grill[0].rotation = [0, 0, 0]
stool_A[0].position = [0.342502015037756, 0.831112440480662, 0.375]
stool_A[0].rotation = [0, 0, 0]
stool_B[0].position = [6.711398769420053, 4.167207565014162, 0.375]
stool_B[0].rotation = [0, 0, 0]
bench[0].position = [6.099864923508193, 0.7141142738746062, 0.45]
bench[0].rotation = [0, 0, 0]
table[0].position = [8.666685120145386, 3.7191914368088077, 0.38]
table[0].rotation = [0, 0, 0]
stool_C[0].position = [0.8555911739681953, 4.377019926775966, 0.375]
stool_C[0].rotation = [0, 0, 0]
stool_D[0].position = [7.979267294879953, 2.4882976525712306, 0.375]
stool_D[0].rotation = [0, 0, 0]
wardrobe[0].position = [4.258091127578372, 6.151995928528996, 0.475]
wardrobe[0].rotation = [0, 0, 0]
grill[0].position = [7.417901336117139, 2.8386866889944877, 0.6]
grill[0].rotation = [0, 0, 0]
stool_A[0].position = [0.342502015037756, 0.831112440480662, 0.375]
stool_A[0].rotation = [0, 0, 0]
stool_B[0].position = [6.711398769420053, 4.167207565014162, 0.375]
stool_B[0].rotation = [0, 0, 0]
bench[0].position = [6.099864923508193, 0.7141142738746062, 0.45]
bench[0].rotation = [0, 0, 0]
table[0].position = [8.666685120145386, 3.7191914368088077, 0.38]
table[0].rotation = [0, 0, 0]
stool_C[0].position = [0.8555911739681953, 4.377019926775966, 0.375]
stool_C[0].rotation = [0, 0, 0]
stool_D[0].position = [7.979267294879953, 2.4882976525712306, 0.375]
stool_D[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the storage pieces against perimeter walls, leaving the central area open.
wardrobe[0].position = [8.72, 5.45, 0.475]
wardrobe[0].rotation = [0, 0, radians(180)]  # Face inward from the right wall.

bench[0].position = [2.00, 6.30, 0.45]
bench[0].rotation = [0, 0, radians(-90)]  # Face inward from the top wall.

# The grill forms a central island in the upper half of the room.
grill[0].position = [4.50, 4.65, 0.60]
grill[0].rotation = [0, 0, radians(0)]

# Put these stools on opposite sides of the grill so the grill is between them.
stool_A[0].position = [3.45, 4.65, 0.375]
stool_A[0].rotation = [0, 0, radians(0)]

stool_B[0].position = [5.55, 4.65, 0.375]
stool_B[0].rotation = [0, 0, radians(180)]

# Create a separate dining group in the lower-right portion of the room.
table[0].position = [6.65, 1.75, 0.38]
table[0].rotation = [0, 0, radians(90)]

stool_C[0].position = [6.65, 2.90, 0.375]
stool_C[0].rotation = [0, 0, radians(-90)]

stool_D[0].position = [6.65, 0.60, 0.375]
stool_D[0].rotation = [0, 0, radians(90)]


# Virtual fixed references pin the intended layout while later relational
# constraints preserve its semantics during feasibility adjustment.
wardrobe_anchor = AssetInstance(position=[8.72, 5.45, 0.475])
bench_anchor = AssetInstance(position=[2.00, 6.30, 0.45])
grill_anchor = AssetInstance(position=[4.50, 4.65, 0.60])
stool_A_anchor = AssetInstance(position=[3.45, 4.65, 0.375])
stool_B_anchor = AssetInstance(position=[5.55, 4.65, 0.375])
table_anchor = AssetInstance(position=[6.65, 1.75, 0.38])
stool_C_anchor = AssetInstance(position=[6.65, 2.90, 0.375])
stool_D_anchor = AssetInstance(position=[6.65, 0.60, 0.375])
zero_heading = AssetInstance(rotation=[0, 0, 0])

# High-priority position constraints keep every object inside the room and
# preserve the explicitly checked, non-overlapping arrangement.
solver.distance_constraint(
    wardrobe[0], wardrobe_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    bench[0], bench_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    grill[0], grill_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    stool_A[0], stool_A_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    stool_B[0], stool_B_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    table[0], table_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    stool_C[0], stool_C_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    stool_D[0], stool_D_anchor, 0, 0, weight=10
)

# The two storage units remain flush with their respective walls.
solver.against_wall(wardrobe[0], walls[1])
solver.against_wall(bench[0], walls[2])

# Fixed orientation constraints keep the large pieces aligned with the room.
solver.align_with(wardrobe[0], zero_heading, angle=180)
solver.align_with(bench[0], zero_heading, angle=-90)
solver.align_with(grill[0], zero_heading, angle=0)
solver.align_with(table[0], zero_heading, angle=90)

# Each stool faces the surface it serves; these are also orientation
# constraints for every stool instance.
solver.point_towards(stool_A[0], grill[0])
solver.point_towards(stool_B[0], grill[0])
solver.point_towards(stool_C[0], table[0])
solver.point_towards(stool_D[0], table[0])

# Preserve symmetric, usable clearances around the grill. Since both stools
# are 1.05 m from its center on opposite sides, the grill remains between them.
solver.distance_constraint(
    stool_A[0], grill[0], 1.05, 1.05, weight=10
)
solver.distance_constraint(
    stool_B[0], grill[0], 1.05, 1.05, weight=10
)
solver.distance_constraint(
    stool_A[0], stool_B[0], 2.10, 2.10, weight=10
)

# Preserve usable seating clearances on opposite long sides of the table.
solver.distance_constraint(
    stool_C[0], table[0], 1.15, 1.15, weight=5
)
solver.distance_constraint(
    stool_D[0], table[0], 1.15, 1.15, weight=5
)
solver.distance_constraint(
    stool_C[0], stool_D[0], 2.30, 2.30, weight=5
)

solver.constraints = []
table[0].position = [6.650000095367432, 1.75, 0.3799999952316284]
table[0].rotation = [0, 0, 1.5927874750809192]
table[0].optimize = 2
grill[0].position = [4.5, 4.650000095367432, 0.6000000238418579]
grill[0].rotation = [0, 0, 0.021991148286022624]
grill[0].optimize = 2
stool_A[0].position = [3.44990611076355, 4.650000095367432, 0.375]
stool_A[0].rotation = [0, 0, 0.0157079639172164]
stool_A[0].optimize = 2
stool_C[0].position = [6.650000095367432, 2.9000000953674316, 0.375]
stool_C[0].rotation = [0, 0, -1.5550883628776802]
stool_C[0].optimize = 2
wardrobe[0].position = [8.716639518737793, 5.449999809265137, 0.4749999940395355]
wardrobe[0].rotation = [0, 0, -3.1415926098648534]
wardrobe[0].optimize = 2
bench[0].position = [2.0, 6.297427654266357, 0.44999998807907104]
bench[0].rotation = [0, 0, -1.5707963678695747]
bench[0].optimize = 2
stool_B[0].position = [5.550000190734863, 4.650000095367432, 0.375]
stool_B[0].rotation = [0, 0, -3.125884689672577]
stool_B[0].optimize = 2
stool_D[0].position = [6.650000095367432, 0.6000000238418579, 0.375]
stool_D[0].rotation = [0, 0, 1.586504290712113]
stool_D[0].optimize = 2

