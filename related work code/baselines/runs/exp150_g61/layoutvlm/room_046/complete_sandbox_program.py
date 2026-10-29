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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[7.00, 0.00, 0.00]),
    Wall(corner1=[7.00, 0.00, 0.00], corner2=[7.00, 6.19, 0.00]),
    Wall(corner1=[7.00, 6.19, 0.00], corner2=[0.00, 6.19, 0.00]),
    Wall(corner1=[0.00, 6.19, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
seat = Assets(description="A cozy armchair with a plush, orange fabric upholstery and wooden legs. It features a rounded backrest and armrests for comfortable seating.", size=[0.90, 0.85, 1.00], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="A small, round table with a simple design and thin legs.", size=[0.55, 0.55, 0.60], placements=[AssetInstance() for _ in range(1)])
dresser_A = Assets(description="A light-colored wooden chest of drawers with three drawers and decorative handles. It has a classic design with a slightly curved top edge and ornate feet.", size=[0.50, 1.00, 0.85], placements=[AssetInstance() for _ in range(1)])
lamp = Assets(description="A modern floor lamp with a cylindrical shade and a thin stand.", size=[0.40, 0.40, 1.60], placements=[AssetInstance() for _ in range(1)])
dresser_B = Assets(description="A simple white drawer unit with a single drawer and an open shelf below. It has a minimalist design with clean lines and a sleek handle.", size=[0.42, 0.50, 0.60], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="A modern bed with a simple design, featuring a light pink upholstered frame and a gray textured blanket. It includes two white pillows and is supported by small wooden legs.", size=[2.10, 1.60, 1.00], placements=[AssetInstance() for _ in range(1)])

seat[0].instance_id = 'seat_0'
table[0].instance_id = 'table_0'
dresser_A[0].instance_id = 'dresser_A_0'
lamp[0].instance_id = 'lamp_0'
dresser_B[0].instance_id = 'dresser_B_0'
bed[0].instance_id = 'bed_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

seat[0].position = [3.1417880026748226, 4.315692763335533, 0.5]
seat[0].rotation = [0, 0, 0]
table[0].position = [2.716736338785651, 5.279832168720694, 0.3]
table[0].rotation = [0, 0, 0]
dresser_A[0].position = [3.303992877720938, 4.014614060009271, 0.425]
dresser_A[0].rotation = [0, 0, 0]
lamp[0].position = [2.3309867348406095, 2.2968621152215514, 0.8]
lamp[0].rotation = [0, 0, 0]
dresser_B[0].position = [4.654802422853427, 3.41031708192511, 0.3]
dresser_B[0].rotation = [0, 0, 0]
bed[0].position = [1.484252196748281, 0.7181655803842869, 0.5]
bed[0].rotation = [0, 0, 0]
seat[0].position = [3.1417880026748226, 4.315692763335533, 0.5]
seat[0].rotation = [0, 0, 0]
table[0].position = [2.716736338785651, 5.279832168720694, 0.3]
table[0].rotation = [0, 0, 0]
dresser_A[0].position = [3.303992877720938, 4.014614060009271, 0.425]
dresser_A[0].rotation = [0, 0, 0]
lamp[0].position = [2.3309867348406095, 2.2968621152215514, 0.8]
lamp[0].rotation = [0, 0, 0]
dresser_B[0].position = [4.654802422853427, 3.41031708192511, 0.3]
dresser_B[0].rotation = [0, 0, 0]
bed[0].position = [1.484252196748281, 0.7181655803842869, 0.5]
bed[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the supplied wall coordinates: the room spans x=0..7, y=0..6.19.
# The bed's head is against the north wall, with one dresser on each side.
# At -90 degrees, its 2.10 m length runs north-south.
bed[0].position = [3.50, 5.14, 0.50]
bed[0].rotation = [0, 0, radians(-90)]

# Rotated dresser footprints are 1.00 x 0.50 and 0.50 x 0.42.
# Leave gaps between both dressers and the bed; drawers open southward.
dresser_A[0].position = [2.05, 5.94, 0.425]
dresser_A[0].rotation = [0, 0, radians(-90)]

dresser_B[0].position = [4.80, 5.98, 0.30]
dresser_B[0].rotation = [0, 0, radians(-90)]

# A separate reading nook leaves the center and right side open for circulation.
seat[0].position = [1.10, 1.40, 0.50]
seat[0].rotation = [0, 0, 0]

table[0].position = [2.05, 1.40, 0.30]
table[0].rotation = [0, 0, 0]

lamp[0].position = [0.65, 2.30, 0.80]
lamp[0].rotation = [0, 0, 0]

# Fixed layout targets preserve the left-dresser / bed / right-dresser ordering
# as well as the nonoverlapping reading nook. Each instance receives both
# position and orientation constraints. These targets are not scene assets.
for layout_instance in (
    bed[0], dresser_A[0], dresser_B[0],
    seat[0], table[0], lamp[0]
):
    layout_target = AssetInstance(
        position=list(layout_instance.position),
        rotation=list(layout_instance.rotation)
    )
    solver.distance_constraint(
        layout_instance, layout_target, 0.0, 0.0, weight=10
    )
    solver.align_with(layout_instance, layout_target)

# Keep the bedroom furniture backed against the north wall.
solver.against_wall(bed[0], walls[2])
solver.against_wall(dresser_A[0], walls[2])
solver.against_wall(dresser_B[0], walls[2])
solver.align_with(dresser_A[0], bed[0])
solver.align_with(dresser_B[0], bed[0])

# Center-to-center distances include vertical offsets.
# These reinforce bedside proximity without bringing the footprints together.
solver.distance_constraint(dresser_A[0], bed[0], 1.60, 1.75, weight=10)
solver.distance_constraint(dresser_B[0], bed[0], 1.50, 1.65, weight=10)

# The armchair faces the nearby table, with about 0.225 m between footprints.
solver.point_towards(seat[0], table[0])
solver.distance_constraint(table[0], seat[0], 0.95, 1.05)
solver.distance_constraint(lamp[0], seat[0], 1.00, 1.10)
solver.align_with(table[0], seat[0])
solver.align_with(lamp[0], seat[0])

# The table and floor lamp are freestanding floor assets, not tabletop objects;
# their z coordinates already place their bases on the floor.

solver.constraints = []
dresser_B[0].position = [4.800000190734863, 5.97808313369751, 0.30000001192092896]
dresser_B[0].rotation = [0, 0, -1.570796488805604]
dresser_B[0].optimize = 2
dresser_A[0].position = [2.049999952316284, 5.938081741333008, 0.42500001192092896]
dresser_A[0].rotation = [0, 0, -1.5707964734255604]
dresser_A[0].optimize = 2
table[0].position = [2.1080520153045654, 1.399999976158142, 0.30000001192092896]
table[0].rotation = [0, 0, 0.02513284694403825]
table[0].optimize = 2
lamp[0].position = [0.6499999761581421, 2.299999952316284, 0.800000011920929]
lamp[0].rotation = [0, 0, 0.02513268073160146]
lamp[0].optimize = 2
seat[0].position = [1.100000023841858, 1.399999976158142, 0.5]
seat[0].rotation = [0, 0, 0.025132740109855806]
seat[0].optimize = 2
bed[0].position = [3.5, 5.138082027435303, 0.5]
bed[0].rotation = [0, 0, -1.570796096864878]
bed[0].optimize = 2

