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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[11.70, 0.00, 0.00]),
    Wall(corner1=[11.70, 0.00, 0.00], corner2=[11.70, 6.16, 0.00]),
    Wall(corner1=[11.70, 6.16, 0.00], corner2=[0.00, 6.16, 0.00]),
    Wall(corner1=[0.00, 6.16, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
kitchen_lower_cabinet = Assets(description="A dark gray cabinet with a light gray countertop. It features two doors with silver handles and a simple design suitable for kitchen or bathroom storage.", size=[0.60, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="A sturdy workbench with a metal frame and a white tabletop. It features two lower shelves made of metal mesh for additional storage.", size=[0.75, 1.80, 0.90], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="A white bathroom cabinet with a sink on top, featuring a simple design with clean lines and a minimalist aesthetic.", size=[0.50, 0.80, 0.85], placements=[AssetInstance() for _ in range(1)])
platform = Assets(description="A simple, smooth cylinder with a flat top surface and rounded edges.", size=[0.60, 0.60, 0.30], placements=[AssetInstance() for _ in range(1)])

kitchen_lower_cabinet[0].instance_id = 'kitchen_lower_cabinet_0'
table[0].instance_id = 'table_0'
cabinet[0].instance_id = 'cabinet_0'
platform[0].instance_id = 'platform_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

kitchen_lower_cabinet[0].position = [11.110337369931315, 5.246984379786373, 0.45]
kitchen_lower_cabinet[0].rotation = [0, 0, 0]
table[0].position = [9.63905856310154, 1.6516907574179611, 0.45]
table[0].rotation = [0, 0, 0]
cabinet[0].position = [1.4308882078886194, 4.177575361785134, 0.425]
cabinet[0].rotation = [0, 0, 0]
platform[0].position = [5.089667603789685, 0.8043243580045137, 0.15]
platform[0].rotation = [0, 0, 0]
kitchen_lower_cabinet[0].position = [11.110337369931315, 5.246984379786373, 0.45]
kitchen_lower_cabinet[0].rotation = [0, 0, 0]
table[0].position = [9.63905856310154, 1.6516907574179611, 0.45]
table[0].rotation = [0, 0, 0]
cabinet[0].position = [1.4308882078886194, 4.177575361785134, 0.425]
cabinet[0].rotation = [0, 0, 0]
platform[0].position = [5.089667603789685, 0.8043243580045137, 0.15]
platform[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the supplied boundary coordinates: x=0..11.70, y=0..6.16.
# Arrange a north-facing work area along the bottom wall, leaving the
# middle of the room open for circulation.
#
# "Within 0.50 m" is interpreted as clearance between asset surfaces.
# A 0.50 m center-distance limit is incompatible with non-overlap:
# the table and cabinet have minimum horizontal half-widths of
# 0.375 m and 0.250 m, whose sum already exceeds 0.50 m.

kitchen_lower_cabinet[0].position = [0.30, 4.70, 0.45]
kitchen_lower_cabinet[0].rotation = [0, 0, 0]

table[0].position = [4.00, 0.375, 0.45]
table[0].rotation = [0, 0, radians(90)]

cabinet[0].position = [5.50, 0.25, 0.425]
cabinet[0].rotation = [0, 0, radians(90)]

platform[0].position = [0.30, 1.50, 0.15]
platform[0].rotation = [0, 0, 0]

# Required wall contact takes priority. Cabinets face into the room.
solver.against_wall(kitchen_lower_cabinet[0], walls[3])
solver.point_towards(
    kitchen_lower_cabinet[0],
    AssetInstance(position=[2.30, 4.70, 0.45])
)

solver.against_wall(platform[0], walls[3])
solver.point_towards(
    platform[0],
    AssetInstance(position=[2.30, 1.50, 0.15])
)

# Both work-area assets face north, with unobstructed access in front.
solver.against_wall(table[0], walls[0])
solver.point_towards(
    table[0],
    AssetInstance(position=[4.00, 2.375, 0.45])
)

solver.against_wall(cabinet[0], walls[0])
solver.align_with(cabinet[0], table[0])

# Preserve the selected positions, preventing drift along the walls.
# These anchors are reference points, not additional scene assets.
solver.distance_constraint(
    kitchen_lower_cabinet[0],
    AssetInstance(position=[0.30, 4.70, 0.45]),
    0, 0, weight=10
)
solver.distance_constraint(
    platform[0],
    AssetInstance(position=[0.30, 1.50, 0.15]),
    0, 0, weight=10
)
solver.distance_constraint(
    table[0],
    AssetInstance(position=[4.00, 0.375, 0.45]),
    0, 0, weight=10
)
solver.distance_constraint(
    cabinet[0],
    AssetInstance(position=[5.50, 0.25, 0.425]),
    0, 0, weight=10
)

# With both assets rotated 90 degrees, their x half-extents are
# 0.90 m and 0.40 m. The 1.50 m x separation leaves a 0.20 m
# surface gap, meeting the requested proximity without overlap.
# Include y and z offsets because distance_constraint uses 3D centers.
solver.distance_constraint(
    cabinet[0], table[0],
    (1.50**2 + 0.125**2 + 0.025**2)**0.5,
    (1.80**2 + 0.125**2 + 0.025**2)**0.5,
    weight=10
)

# All four assets are floor-standing; no on_top_of constraint is needed.

solver.constraints = []
cabinet[0].position = [5.550192832946777, 0.2499999701976776, 0.42500001192092896]
cabinet[0].rotation = [0, 0, 1.5707963651205676]
cabinet[0].optimize = 2
kitchen_lower_cabinet[0].position = [0.29999998211860657, 4.699999809265137, 0.44999998807907104]
kitchen_lower_cabinet[0].rotation = [0, 0, 3.99471774930687e-08]
kitchen_lower_cabinet[0].optimize = 2
platform[0].position = [0.30000007152557373, 1.5, 0.15000000596046448]
platform[0].rotation = [0, 0, 5.039783146854792e-08]
platform[0].optimize = 2
table[0].position = [4.0, 0.3750000596046448, 0.44999998807907104]
table[0].rotation = [0, 0, 1.570796368219883]
table[0].optimize = 2

