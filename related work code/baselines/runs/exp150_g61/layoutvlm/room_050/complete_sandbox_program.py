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
    Wall(corner1=[1.53, 3.84, 0.00], corner2=[0.00, 3.84, 0.00]),
    Wall(corner1=[0.00, 3.84, 0.00], corner2=[0.00, 1.89, 0.00]),
    Wall(corner1=[0.00, 1.89, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[0.24, 0.00, 0.00]),
    Wall(corner1=[0.24, 0.00, 0.00], corner2=[2.10, 0.00, 0.00]),
    Wall(corner1=[2.10, 0.00, 0.00], corner2=[2.79, 0.00, 0.00]),
    Wall(corner1=[2.79, 0.00, 0.00], corner2=[2.79, 3.71, 0.00]),
    Wall(corner1=[2.79, 3.71, 0.00], corner2=[2.79, 3.96, 0.00]),
    Wall(corner1=[2.79, 3.96, 0.00], corner2=[2.79, 4.76, 0.00]),
    Wall(corner1=[2.79, 4.76, 0.00], corner2=[2.79, 4.95, 0.00]),
    Wall(corner1=[2.79, 4.95, 0.00], corner2=[1.65, 4.95, 0.00]),
    Wall(corner1=[1.65, 4.95, 0.00], corner2=[1.65, 4.80, 0.00]),
    Wall(corner1=[1.65, 4.80, 0.00], corner2=[1.65, 4.00, 0.00]),
    Wall(corner1=[1.65, 4.00, 0.00], corner2=[1.65, 3.84, 0.00]),
    Wall(corner1=[1.65, 3.84, 0.00], corner2=[1.53, 3.84, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
book_A = Assets(description="book", size=[0.24, 0.16, 0.03], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="book", size=[0.22, 0.15, 0.03], placements=[AssetInstance() for _ in range(1)])
bedside_table_A = Assets(description="bedside table", size=[0.40, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[2.80, 2.20, 0.01], placements=[AssetInstance() for _ in range(1)])
book_C = Assets(description="book", size=[0.25, 0.17, 0.03], placements=[AssetInstance() for _ in range(1)])
bedside_table_B = Assets(description="bedside table", size=[0.40, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
bottle = Assets(description="bottle", size=[0.07, 0.07, 0.25], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.10, 1.60, 0.95], placements=[AssetInstance() for _ in range(1)])

book_A[0].instance_id = 'book_A_0'
book_B[0].instance_id = 'book_B_0'
bedside_table_A[0].instance_id = 'bedside_table_A_0'
carpet[0].instance_id = 'carpet_0'
book_C[0].instance_id = 'book_C_0'
bedside_table_B[0].instance_id = 'bedside_table_B_0'
bottle[0].instance_id = 'bottle_0'
bed[0].instance_id = 'bed_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'
walls[8].instance_id = 'walls_8'
walls[9].instance_id = 'walls_9'
walls[10].instance_id = 'walls_10'
walls[11].instance_id = 'walls_11'
walls[12].instance_id = 'walls_12'
walls[13].instance_id = 'walls_13'
walls[14].instance_id = 'walls_14'

book_A[0].position = [2.5942817768073807, 0.9231277538858363, 0.015]
book_A[0].rotation = [0, 0, 0]
book_B[0].position = [2.1347471235189386, 0.0462511615683202, 0.0125]
book_B[0].rotation = [0, 0, 0]
bedside_table_A[0].position = [1.7513623693517244, 2.4182916221107433, 0.275]
bedside_table_A[0].rotation = [0, 0, 0]
carpet[0].position = [2.2466590005109905, 3.8403111291655336, 0.0075]
carpet[0].rotation = [0, 0, 0]
book_C[0].position = [2.0546173048003293, 2.841270816061599, 0.015]
book_C[0].rotation = [0, 0, 0]
bedside_table_B[0].position = [0.14817620715621174, 0.4008643324879387, 0.275]
bedside_table_B[0].rotation = [0, 0, 0]
bottle[0].position = [1.2367550573095936, 1.4815687001455666, 0.125]
bottle[0].rotation = [0, 0, 0]
bed[0].position = [0.11334987226316981, 1.7563998629243702, 0.475]
bed[0].rotation = [0, 0, 0]
book_A[0].position = [2.5942817768073807, 0.9231277538858363, 0.015]
book_A[0].rotation = [0, 0, 0]
book_B[0].position = [2.1347471235189386, 0.0462511615683202, 0.0125]
book_B[0].rotation = [0, 0, 0]
bedside_table_A[0].position = [1.7513623693517244, 2.4182916221107433, 0.275]
bedside_table_A[0].rotation = [0, 0, 0]
carpet[0].position = [2.2466590005109905, 3.8403111291655336, 0.0075]
carpet[0].rotation = [0, 0, 0]
book_C[0].position = [2.0546173048003293, 2.841270816061599, 0.015]
book_C[0].rotation = [0, 0, 0]
bedside_table_B[0].position = [0.14817620715621174, 0.4008643324879387, 0.275]
bedside_table_B[0].rotation = [0, 0, 0]
bottle[0].position = [1.2367550573095936, 1.4815687001455666, 0.125]
bottle[0].rotation = [0, 0, 0]
bed[0].position = [0.11334987226316981, 1.7563998629243702, 0.475]
bed[0].rotation = [0, 0, 0]

solver.constraints = []

# Rotate the bed lengthwise along +y, with its head near the window.
# The bedside tables flank its head, while the northern part of the room
# remains clear for wardrobe access and circulation to both doors.
#
# The rug must rotate 90 degrees: its unrotated 2.80 m width would exceed
# the room's 2.79 m width. Furniture/rug footprint overlap is intentional;
# their vertical positions prevent solid-volume intersections.

bed[0].position = [1.395, 1.10, 0.485]
bed[0].rotation = [0, 0, radians(90)]

bedside_table_A[0].position = [0.345, 0.25, 0.285]
bedside_table_A[0].rotation = [0, 0, radians(90)]

bedside_table_B[0].position = [2.445, 0.25, 0.285]
bedside_table_B[0].rotation = [0, 0, radians(90)]

carpet[0].position = [1.395, 1.42, 0.005]
carpet[0].rotation = [0, 0, radians(90)]

# Stack two books on the left table.
book_A[0].position = [0.345, 0.25, 0.575]
book_A[0].rotation = [0, 0, radians(90)]

book_B[0].position = [0.345, 0.25, 0.605]
book_B[0].rotation = [0, 0, radians(90)]

# Keep the book and bottle separated on the right tabletop.
book_C[0].position = [2.40, 0.25, 0.575]
book_C[0].rotation = [0, 0, radians(90)]

bottle[0].position = [2.57, 0.25, 0.685]
bottle[0].rotation = [0, 0, radians(90)]

# High-priority fixed-position constraints preserve the side-by-side
# arrangement, boundary clearance, and unobstructed doorway approaches.
# Fixed references are constraint anchors, not additional scene assets.
for layout_group in (
    bed, bedside_table_A, bedside_table_B, carpet,
    book_A, book_B, book_C, bottle
):
    solver.distance_constraint(
        layout_group[0],
        AssetInstance(position=list(layout_group[0].position)),
        min_distance=0.0,
        max_distance=0.0,
        weight=10,
    )
    solver.align_with(
        layout_group[0],
        AssetInstance(rotation=[0, 0, radians(90)]),
        angle=0,
    )

# The rug extends beneath the bed and the inner portions of both tables.
solver.on_top_of(bed[0], carpet[0])
solver.on_top_of(bedside_table_A[0], carpet[0])
solver.on_top_of(bedside_table_B[0], carpet[0])

solver.on_top_of(book_A[0], bedside_table_A[0])
solver.on_top_of(book_B[0], book_A[0])
solver.on_top_of(book_C[0], bedside_table_B[0])
solver.on_top_of(bottle[0], bedside_table_B[0])

# Supplement the anchors with semantic proximity constraints.
# Distances include the vertical differences between bounding-box centers.
for table_group in (bedside_table_A, bedside_table_B):
    solver.distance_constraint(
        table_group[0], bed[0],
        min_distance=1.35, max_distance=1.40, weight=10
    )
    solver.align_with(table_group[0], bed[0])

solver.distance_constraint(
    book_A[0], bedside_table_A[0], 0.29, 0.29
)
solver.distance_constraint(
    book_B[0], book_A[0], 0.03, 0.03
)
solver.distance_constraint(
    book_C[0], bedside_table_B[0], 0.29, 0.30
)
solver.distance_constraint(
    bottle[0], bedside_table_B[0], 0.41, 0.43
)
solver.distance_constraint(
    bottle[0], book_C[0], 0.20, 0.21
)

solver.constraints = []
bedside_table_A[0].position = [0.3449999988079071, 0.25, 0.2849999964237213]
bedside_table_A[0].rotation = [0, 0, 1.5959290669047523]
bedside_table_A[0].optimize = 2
bottle[0].position = [2.5799999237060547, 0.25, 0.6850000023841858]
bottle[0].rotation = [0, 0, 1.589645882193713]
bottle[0].optimize = 2
book_C[0].position = [2.390000104904175, 0.25, 0.574999988079071]
book_C[0].rotation = [0, 0, 1.589645882193713]
book_C[0].optimize = 2
bedside_table_B[0].position = [2.444999933242798, 0.25, 0.2849999964237213]
bedside_table_B[0].rotation = [0, 0, 1.5920049147291835]
bedside_table_B[0].optimize = 2
carpet[0].position = [1.3949999809265137, 1.4199999570846558, 0.004999999888241291]
carpet[0].rotation = [0, 0, 1.589645882193713]
carpet[0].optimize = 2
book_B[0].position = [0.3449999988079071, 0.25, 0.6049999594688416]
book_B[0].rotation = [0, 0, 1.586504290712113]
book_B[0].optimize = 2
bed[0].position = [1.3949999809265137, 1.100000023841858, 0.48499998450279236]
bed[0].rotation = [0, 0, 1.5959290669047523]
bed[0].optimize = 2
book_A[0].position = [0.3449999988079071, 0.25, 0.574999988079071]
book_A[0].rotation = [0, 0, 1.5927874750809192]
book_A[0].optimize = 2

