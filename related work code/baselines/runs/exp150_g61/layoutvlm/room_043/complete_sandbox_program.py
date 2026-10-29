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
wardrobe = Assets(description="A light-colored wooden cabinet with two doors and a countertop. It features a small drawer above the doors and a wine rack inside one of the compartments.", size=[0.50, 1.00, 0.90], placements=[AssetInstance() for _ in range(1)])
grill = Assets(description="A robust outdoor kitchen island featuring a built-in grill, storage cabinets, and a countertop. The design includes a combination of dark stone-like materials for the body and a metallic finish for the grill area.", size=[1.00, 2.40, 1.10], placements=[AssetInstance() for _ in range(1)])
stool_A = Assets(description="A modern bar stool with a sleek design featuring a black seat and light-colored metal legs. The legs are thin and form a square base for stability.", size=[0.42, 0.42, 0.75], placements=[AssetInstance() for _ in range(1)])
stool_B = Assets(description="A modern bar stool with a sleek design featuring a black seat and light-colored metal legs. The legs are thin and form a square base for stability.", size=[0.42, 0.42, 0.75], placements=[AssetInstance() for _ in range(1)])
bench = Assets(description="A wooden shelf unit with multiple compartments designed for storage or display purposes. It features a clean and simple design with a light wood finish.", size=[0.40, 1.50, 0.85], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="A wooden dining table with a rectangular top and sturdy legs that feature an X-shaped support design.", size=[0.90, 1.80, 0.76], placements=[AssetInstance() for _ in range(1)])
stool_C = Assets(description="A modern bar stool with a sleek design featuring a black seat and light-colored metal legs. The legs are thin and form a square base for stability.", size=[0.42, 0.42, 0.75], placements=[AssetInstance() for _ in range(1)])
stool_D = Assets(description="A modern bar stool with a sleek design featuring a black seat and light-colored metal legs. The legs are thin and form a square base for stability.", size=[0.42, 0.42, 0.75], placements=[AssetInstance() for _ in range(1)])

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

wardrobe[0].position = [0.4087476546866284, 5.443020587711976, 0.45]
wardrobe[0].rotation = [0, 0, 0]
grill[0].position = [5.43057946352893, 4.044750015203912, 0.55]
grill[0].rotation = [0, 0, 0]
stool_A[0].position = [0.5493053064499868, 4.05470000632527, 0.375]
stool_A[0].rotation = [0, 0, 0]
stool_B[0].position = [0.048362768553863296, 0.6699170452886473, 0.375]
stool_B[0].rotation = [0, 0, 0]
bench[0].position = [1.7821415415145612, 3.926951800651286, 0.425]
bench[0].rotation = [0, 0, 0]
table[0].position = [1.8282021399505077, 3.177615154089526, 0.38]
table[0].rotation = [0, 0, 0]
stool_C[0].position = [0.42072309871307123, 0.6808131034194775, 0.375]
stool_C[0].rotation = [0, 0, 0]
stool_D[0].position = [3.4995679863155678, 5.777490564756344, 0.375]
stool_D[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.4087476546866284, 5.443020587711976, 0.45]
wardrobe[0].rotation = [0, 0, 0]
grill[0].position = [5.43057946352893, 4.044750015203912, 0.55]
grill[0].rotation = [0, 0, 0]
stool_A[0].position = [0.5493053064499868, 4.05470000632527, 0.375]
stool_A[0].rotation = [0, 0, 0]
stool_B[0].position = [0.048362768553863296, 0.6699170452886473, 0.375]
stool_B[0].rotation = [0, 0, 0]
bench[0].position = [1.7821415415145612, 3.926951800651286, 0.425]
bench[0].rotation = [0, 0, 0]
table[0].position = [1.8282021399505077, 3.177615154089526, 0.38]
table[0].rotation = [0, 0, 0]
stool_C[0].position = [0.42072309871307123, 0.6808131034194775, 0.375]
stool_C[0].rotation = [0, 0, 0]
stool_D[0].position = [3.4995679863155678, 5.777490564756344, 0.375]
stool_D[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the floor-plan coordinates: x=0..9.02, y=0..6.50.
# All objects are floor-standing, so their centers are at half-height.
# The requested stools o0003 and o0006 correspond to stool_B and stool_C.
# They flank the grill along its long (y) axis, leaving its +x working side open.
grill[0].position = [2.80, 3.25, 0.55]
grill[0].rotation = [0, 0, 0]

stool_B[0].position = [2.80, 1.50, 0.375]
stool_B[0].rotation = [0, 0, radians(90)]

stool_C[0].position = [2.80, 5.00, 0.375]
stool_C[0].rotation = [0, 0, radians(-90)]

# Storage sits against the west wall, facing into the room.
wardrobe[0].position = [0.25, 1.40, 0.45]
wardrobe[0].rotation = [0, 0, 0]

bench[0].position = [0.20, 4.60, 0.425]
bench[0].rotation = [0, 0, 0]

# Separate dining area east of the grill, with stools on opposite sides.
# The table remains long in y; the stools have 0.39 m clearance to its edge.
table[0].position = [6.40, 3.25, 0.38]
table[0].rotation = [0, 0, 0]

stool_A[0].position = [5.35, 3.25, 0.375]
stool_A[0].rotation = [0, 0, 0]

stool_D[0].position = [7.45, 3.25, 0.375]
stool_D[0].rotation = [0, 0, radians(180)]

# High-priority fixed-point constraints preserve the nonoverlapping layout,
# keep every footprint inside the boundary, and maintain circulation space.
# These anchors are constraint references, not additional scene assets.
for layout_asset in (
    wardrobe, grill, stool_A, stool_B, bench, table, stool_C, stool_D
):
    solver.distance_constraint(
        layout_asset[0],
        AssetInstance(position=list(layout_asset[0].position)),
        0, 0, weight=10
    )

# Orientation constraints for every instance.
solver.align_with(
    grill[0], AssetInstance(rotation=[0, 0, 0])
)
solver.align_with(wardrobe[0], grill[0])
solver.align_with(bench[0], grill[0])
solver.align_with(table[0], grill[0])
solver.point_towards(stool_B[0], grill[0])
solver.point_towards(stool_C[0], grill[0])
solver.point_towards(stool_A[0], table[0])
solver.point_towards(stool_D[0], table[0])

# Wall relationships for the shallow storage units.
solver.against_wall(wardrobe[0], walls[3])
solver.against_wall(bench[0], walls[3])

# Explicitly preserve the grill's centered position between the two stools.
# Distances account for the differing bounding-box center heights.
grill_stool_distance = (1.75**2 + (0.55 - 0.375)**2)**0.5
solver.distance_constraint(
    stool_B[0], grill[0],
    grill_stool_distance, grill_stool_distance, weight=10
)
solver.distance_constraint(
    stool_C[0], grill[0],
    grill_stool_distance, grill_stool_distance, weight=10
)
solver.distance_constraint(stool_B[0], stool_C[0], 3.50, 3.50, weight=10)

# Keep the dining stools close enough to use the table without intersecting it.
dining_stool_distance = (1.05**2 + (0.38 - 0.375)**2)**0.5
solver.distance_constraint(
    stool_A[0], table[0],
    dining_stool_distance, dining_stool_distance
)
solver.distance_constraint(
    stool_D[0], table[0],
    dining_stool_distance, dining_stool_distance
)
solver.distance_constraint(stool_A[0], stool_D[0], 2.10, 2.10)

solver.constraints = []
stool_A[0].position = [5.339999675750732, 3.25, 0.375]
stool_A[0].rotation = [0, 0, 0.0157079639172164]
stool_A[0].optimize = 2
grill[0].position = [2.799999952316284, 3.25, 0.550000011920929]
grill[0].rotation = [0, 0, 0.031415925765816845]
grill[0].optimize = 2
stool_D[0].position = [7.460000038146973, 3.25, 0.375]
stool_D[0].rotation = [0, 0, -3.125884689672577]
stool_D[0].optimize = 2
bench[0].position = [0.2019050568342209, 4.599999904632568, 0.42500001192092896]
bench[0].rotation = [0, 0, 0.0025409160063866866]
bench[0].optimize = 2
wardrobe[0].position = [0.251269668340683, 1.399999976158142, 0.44999998807907104]
wardrobe[0].rotation = [0, 0, 0.002540927027679745]
wardrobe[0].optimize = 2
stool_C[0].position = [2.799999952316284, 5.010000228881836, 0.375]
stool_C[0].rotation = [0, 0, -1.5550883628776802]
stool_C[0].optimize = 2
table[0].position = [6.400000095367432, 3.25, 0.3799999952316284]
table[0].rotation = [0, 0, 0.03230651258844359]
table[0].optimize = 2
stool_B[0].position = [2.799999952316284, 1.4900000095367432, 0.375]
stool_B[0].rotation = [0, 0, 1.586504290712113]
stool_B[0].optimize = 2

