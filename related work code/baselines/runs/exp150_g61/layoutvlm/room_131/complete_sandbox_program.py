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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.00, 0.00, 0.00]),
    Wall(corner1=[4.00, 0.00, 0.00], corner2=[4.00, 5.00, 0.00]),
    Wall(corner1=[4.00, 5.00, 0.00], corner2=[0.00, 5.00, 0.00]),
    Wall(corner1=[0.00, 5.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
accent_shelf = Assets(description="A stack of six wood shelves.", size=[0.35, 0.80, 1.85], placements=[AssetInstance() for _ in range(1)])
bedside_table_A = Assets(description="A nightstand with one drawer.", size=[0.40, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
desk_chair = Assets(description="It is a chair with short cloth covered arms.", size=[0.60, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
bed_pillow = Assets(description="A plain white square pillow.", size=[0.50, 0.50, 0.15], placements=[AssetInstance() for _ in range(1)])
table_lamp_A = Assets(description="A table lamp with a lampshade on it.", size=[0.30, 0.30, 0.50], placements=[AssetInstance() for _ in range(1)])
table_lamp_B = Assets(description="A table lamp with a lampshade on it.", size=[0.30, 0.30, 0.50], placements=[AssetInstance() for _ in range(1)])
writing_desk = Assets(description="A brown desk with black metal pieces.", size=[0.60, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
queen_bed = Assets(description="A bed with a beige comforter and pillows and orange wooden frame.", size=[2.15, 1.65, 1.00], placements=[AssetInstance() for _ in range(1)])
bedside_table_B = Assets(description="A nightstand with one drawer.", size=[0.40, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
book = Assets(description="A leather hardback book with a black band and lock around it.", size=[0.25, 0.18, 0.04], placements=[AssetInstance() for _ in range(1)])

accent_shelf[0].instance_id = 'accent_shelf_0'
bedside_table_A[0].instance_id = 'bedside_table_A_0'
desk_chair[0].instance_id = 'desk_chair_0'
bed_pillow[0].instance_id = 'bed_pillow_0'
table_lamp_A[0].instance_id = 'table_lamp_A_0'
table_lamp_B[0].instance_id = 'table_lamp_B_0'
writing_desk[0].instance_id = 'writing_desk_0'
queen_bed[0].instance_id = 'queen_bed_0'
bedside_table_B[0].instance_id = 'bedside_table_B_0'
book[0].instance_id = 'book_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

accent_shelf[0].position = [2.398944522626225, 3.003368700108275, 0.925]
accent_shelf[0].rotation = [0, 0, 0]
bedside_table_A[0].position = [0.3863349041199169, 0.0374955904902996, 0.275]
bedside_table_A[0].rotation = [0, 0, 0]
desk_chair[0].position = [2.6844697798346204, 0.8578137049180046, 0.425]
desk_chair[0].rotation = [0, 0, 0]
bed_pillow[0].position = [1.38610298608184, 4.076444182449321, 0.075]
bed_pillow[0].rotation = [0, 0, 0]
table_lamp_A[0].position = [0.5761298586963299, 4.556759201016169, 0.25]
table_lamp_A[0].rotation = [0, 0, 0]
table_lamp_B[0].position = [1.50009809446144, 3.1757814893109133, 0.25]
table_lamp_B[0].rotation = [0, 0, 0]
writing_desk[0].position = [2.295322867183465, 0.9998751808122669, 0.375]
writing_desk[0].rotation = [0, 0, 0]
queen_bed[0].position = [0.3232304615325674, 1.6261254093409656, 0.5]
queen_bed[0].rotation = [0, 0, 0]
bedside_table_B[0].position = [0.7106171522854758, 1.4371145655954243, 0.275]
bedside_table_B[0].rotation = [0, 0, 0]
book[0].position = [2.837662368032912, 4.261149081537493, 0.02]
book[0].rotation = [0, 0, 0]
accent_shelf[0].position = [2.398944522626225, 3.003368700108275, 0.925]
accent_shelf[0].rotation = [0, 0, 0]
bedside_table_A[0].position = [0.3863349041199169, 0.0374955904902996, 0.275]
bedside_table_A[0].rotation = [0, 0, 0]
desk_chair[0].position = [2.6844697798346204, 0.8578137049180046, 0.425]
desk_chair[0].rotation = [0, 0, 0]
bed_pillow[0].position = [1.38610298608184, 4.076444182449321, 0.075]
bed_pillow[0].rotation = [0, 0, 0]
table_lamp_A[0].position = [0.5761298586963299, 4.556759201016169, 0.25]
table_lamp_A[0].rotation = [0, 0, 0]
table_lamp_B[0].position = [1.50009809446144, 3.1757814893109133, 0.25]
table_lamp_B[0].rotation = [0, 0, 0]
writing_desk[0].position = [2.295322867183465, 0.9998751808122669, 0.375]
writing_desk[0].rotation = [0, 0, 0]
queen_bed[0].position = [0.3232304615325674, 1.6261254093409656, 0.5]
queen_bed[0].rotation = [0, 0, 0]
bedside_table_B[0].position = [0.7106171522854758, 1.4371145655954243, 0.275]
bedside_table_B[0].rotation = [0, 0, 0]
book[0].position = [2.837662368032912, 4.261149081537493, 0.02]
book[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the supplied 0..4 by 0..5 boundary coordinates.
# The bed occupies the north side; its foot faces the chair and south-wall desk.
# The eastern entry area (approximately x=3..4, y=0.85..2.0) stays empty.
queen_bed[0].position = [1.50, 3.925, 0.50]
queen_bed[0].rotation = [0, 0, radians(270)]

writing_desk[0].position = [1.50, 0.30, 0.375]
writing_desk[0].rotation = [0, 0, radians(90)]

# Leave 0.65 m between the desk edge and bed foot for the chair,
# with additional open circulation to the east.
desk_chair[0].position = [1.50, 1.30, 0.425]
desk_chair[0].rotation = [0, 0, radians(270)]

# Flank the head of the bed. Rotating these tables makes their
# floor footprints 0.50 m in x and 0.40 m in y.
bedside_table_A[0].position = [0.35, 4.65, 0.275]
bedside_table_A[0].rotation = [0, 0, radians(270)]
bedside_table_B[0].position = [2.65, 4.65, 0.275]
bedside_table_B[0].rotation = [0, 0, radians(270)]

# The narrow shelf backs onto the west wall and faces into the room.
accent_shelf[0].position = [0.175, 1.95, 0.925]
accent_shelf[0].rotation = [0, 0, 0]

# Supported objects use the surface height plus half their own height.
table_lamp_A[0].position = [0.35, 4.65, 0.80]
table_lamp_A[0].rotation = [0, 0, radians(270)]
table_lamp_B[0].position = [2.65, 4.65, 0.80]
table_lamp_B[0].rotation = [0, 0, radians(270)]

bed_pillow[0].position = [1.50, 4.55, 1.075]
bed_pillow[0].rotation = [0, 0, radians(270)]

book[0].position = [0.175, 1.95, 1.87]
book[0].rotation = [0, 0, 0]

# Establish the required wall and support relationships first.
solver.against_wall(accent_shelf[0], walls[3])
solver.against_wall(queen_bed[0], walls[2])
solver.against_wall(writing_desk[0], walls[0])

solver.on_top_of(book[0], accent_shelf[0])
solver.on_top_of(bed_pillow[0], queen_bed[0])
solver.on_top_of(table_lamp_A[0], bedside_table_A[0])
solver.on_top_of(table_lamp_B[0], bedside_table_B[0])

# Anchor the intended collision-free positions. Separate fixed-point
# references preserve the entry clearance and the bedside gaps.
for layout_asset in (
    accent_shelf, bedside_table_A, desk_chair, bed_pillow,
    table_lamp_A, table_lamp_B, writing_desk, queen_bed,
    bedside_table_B, book
):
    solver.distance_constraint(
        layout_asset[0],
        AssetInstance(position=list(layout_asset[0].position)),
        0.0, 0.0, weight=10
    )

# Orientation constraints for every new instance.
solver.point_towards(queen_bed[0], desk_chair[0])
solver.point_towards(desk_chair[0], writing_desk[0])
solver.point_towards(writing_desk[0], desk_chair[0])

solver.align_with(
    accent_shelf[0],
    AssetInstance(position=[2.0, 1.95, 0.925], rotation=[0, 0, 0])
)
solver.align_with(bedside_table_A[0], queen_bed[0])
solver.align_with(bedside_table_B[0], queen_bed[0])
solver.align_with(bed_pillow[0], queen_bed[0])
solver.align_with(table_lamp_A[0], bedside_table_A[0])
solver.align_with(table_lamp_B[0], bedside_table_B[0])
solver.align_with(book[0], accent_shelf[0])

# Keep each lamp centered on its table and the book centered on the shelf.
# These center distances include their vertical separation.
solver.distance_constraint(
    table_lamp_A[0], bedside_table_A[0], 0.525, 0.525, weight=10
)
solver.distance_constraint(
    table_lamp_B[0], bedside_table_B[0], 0.525, 0.525, weight=10
)
solver.distance_constraint(
    book[0], accent_shelf[0], 0.945, 0.945, weight=10
)

solver.constraints = []
bedside_table_A[0].position = [0.3499999940395355, 4.650000095367432, 0.2750000059604645]
bedside_table_A[0].rotation = [0, 0, -1.5712769385231105]
bedside_table_A[0].optimize = 2
book[0].position = [0.1250234842300415, 1.9500000476837158, 1.8700000047683716]
book[0].rotation = [0, 0, -0.0002610910560838739]
book[0].optimize = 2
table_lamp_A[0].position = [0.3499999940395355, 4.650000095367432, 0.800000011920929]
table_lamp_A[0].rotation = [0, 0, -1.57089719043169]
table_lamp_A[0].optimize = 2
table_lamp_B[0].position = [2.6500000953674316, 4.650000095367432, 0.800000011920929]
table_lamp_B[0].rotation = [0, 0, -1.57089719043169]
table_lamp_B[0].optimize = 2
bedside_table_B[0].position = [2.6500000953674316, 4.650000095367432, 0.2750000059604645]
bedside_table_B[0].rotation = [0, 0, -1.5712769385231105]
bedside_table_B[0].optimize = 2
bed_pillow[0].position = [1.5, 4.550000190734863, 1.0750000476837158]
bed_pillow[0].rotation = [0, 0, -1.5712132187585202]
bed_pillow[0].optimize = 2
writing_desk[0].position = [1.5, 0.2999633550643921, 0.375]
writing_desk[0].rotation = [0, 0, 1.5708018361437317]
writing_desk[0].optimize = 2
desk_chair[0].position = [1.5, 1.2999999523162842, 0.42500001192092896]
desk_chair[0].rotation = [0, 0, -1.5550883628776802]
desk_chair[0].optimize = 2
accent_shelf[0].position = [0.1750047504901886, 1.9500000476837158, 0.925000011920929]
accent_shelf[0].rotation = [0, 0, -3.3450680403685006e-05]
accent_shelf[0].optimize = 2
queen_bed[0].position = [1.5, 3.925143003463745, 0.5]
queen_bed[0].rotation = [0, 0, -1.570861083953748]
queen_bed[0].optimize = 2

