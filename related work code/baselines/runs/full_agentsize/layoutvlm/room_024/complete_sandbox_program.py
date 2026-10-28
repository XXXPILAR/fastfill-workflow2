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
    Wall(corner1=[4.99, 0.24, 0.00], corner2=[5.91, 0.24, 0.00]),
    Wall(corner1=[5.91, 0.24, 0.00], corner2=[5.91, 5.38, 0.00]),
    Wall(corner1=[5.91, 5.38, 0.00], corner2=[7.17, 5.38, 0.00]),
    Wall(corner1=[7.17, 5.38, 0.00], corner2=[7.17, 8.06, 0.00]),
    Wall(corner1=[7.17, 8.06, 0.00], corner2=[6.15, 8.06, 0.00]),
    Wall(corner1=[6.15, 8.06, 0.00], corner2=[6.15, 6.71, 0.00]),
    Wall(corner1=[6.15, 6.71, 0.00], corner2=[2.60, 6.71, 0.00]),
    Wall(corner1=[2.60, 6.71, 0.00], corner2=[2.60, 10.02, 0.00]),
    Wall(corner1=[2.60, 10.02, 0.00], corner2=[0.00, 10.02, 0.00]),
    Wall(corner1=[0.00, 10.02, 0.00], corner2=[0.00, 5.38, 0.00]),
    Wall(corner1=[0.00, 5.38, 0.00], corner2=[1.88, 5.38, 0.00]),
    Wall(corner1=[1.88, 5.38, 0.00], corner2=[1.88, 0.24, 0.00]),
    Wall(corner1=[1.88, 0.24, 0.00], corner2=[2.74, 0.24, 0.00]),
    Wall(corner1=[2.74, 0.24, 0.00], corner2=[2.74, 0.00, 0.00]),
    Wall(corner1=[2.74, 0.00, 0.00], corner2=[4.99, 0.00, 0.00]),
    Wall(corner1=[4.99, 0.00, 0.00], corner2=[4.99, 0.24, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
drawer_chest = Assets(description="A tall, modern bookshelf with a sleek black metal frame and wooden shelves. It has five evenly spaced shelves and a minimalist design.", size=[0.35, 1.20, 1.90], placements=[AssetInstance() for _ in range(1)])
dining_table = Assets(description="A sleek, modern coffee table with a rectangular top and angled legs.", size=[0.90, 1.80, 0.75], placements=[AssetInstance() for _ in range(1)])
side_table = Assets(description="A modern side table with a rectangular top and a single drawer. The legs are uniquely designed with a textured pattern that resembles a quilted or woven material.", size=[0.45, 0.55, 0.60], placements=[AssetInstance() for _ in range(1)])
three_seat_sofa = Assets(description="A modern sectional sofa with a curved design, upholstered in dark gray fabric. It features multiple cushions in shades of purple, black, and gray, arranged for comfort and style.", size=[1.45, 3.20, 0.85], placements=[AssetInstance() for _ in range(1)])
sideboard = Assets(description="A simple console table with a flat top surface and four legs, designed for placement against a wall. It features a minimalist design with clean lines.", size=[0.40, 1.50, 0.80], placements=[AssetInstance() for _ in range(1)])
dining_chair_A = Assets(description="An elegant armchair with a sleek black frame and upholstered seat and backrest in a soft blue fabric. The backrest features an ornate golden patterned design that adds a touch of luxury. The chair has curved armrests and slightly angled legs.", size=[0.62, 0.62, 0.90], placements=[AssetInstance() for _ in range(1)])
dining_chair_B = Assets(description="An elegant armchair with a sleek black frame and upholstered seat and backrest in a soft blue fabric. The backrest features an ornate golden patterned design that adds a touch of luxury. The chair has curved armrests and slightly angled legs.", size=[0.62, 0.62, 0.90], placements=[AssetInstance() for _ in range(1)])
lounge_chair = Assets(description="A black barber chair with a cushioned seat and backrest, featuring metallic armrests and a footrest. It has a sturdy base for stability.", size=[1.05, 0.75, 1.15], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="An elegant oval-shaped coffee table with a glossy black tabletop and ornate metallic legs. The table features intricate detailing on its legs and a sturdy base connecting them.", size=[0.75, 1.25, 0.45], placements=[AssetInstance() for _ in range(1)])
dining_chair_C = Assets(description="An elegant armchair with a sleek black frame and upholstered seat and backrest in a soft blue fabric. The backrest features an ornate golden patterned design that adds a touch of luxury. The chair has curved armrests and slightly angled legs.", size=[0.62, 0.62, 0.90], placements=[AssetInstance() for _ in range(1)])
dining_chair_D = Assets(description="An elegant armchair with a sleek black frame and upholstered seat and backrest in a soft blue fabric. The backrest features an ornate golden patterned design that adds a touch of luxury. The chair has curved armrests and slightly angled legs.", size=[0.62, 0.62, 0.90], placements=[AssetInstance() for _ in range(1)])
tv_stand = Assets(description="A long, rectangular cabinet with a flat top surface and multiple doors, some of which feature glass panels. It has a simple design with clean lines and a sturdy base.", size=[0.45, 2.20, 0.65], placements=[AssetInstance() for _ in range(1)])

drawer_chest[0].instance_id = 'drawer_chest_0'
dining_table[0].instance_id = 'dining_table_0'
side_table[0].instance_id = 'side_table_0'
three_seat_sofa[0].instance_id = 'three_seat_sofa_0'
sideboard[0].instance_id = 'sideboard_0'
dining_chair_A[0].instance_id = 'dining_chair_A_0'
dining_chair_B[0].instance_id = 'dining_chair_B_0'
lounge_chair[0].instance_id = 'lounge_chair_0'
coffee_table[0].instance_id = 'coffee_table_0'
dining_chair_C[0].instance_id = 'dining_chair_C_0'
dining_chair_D[0].instance_id = 'dining_chair_D_0'
tv_stand[0].instance_id = 'tv_stand_0'
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
walls[15].instance_id = 'walls_15'

drawer_chest[0].position = [4.462380198094909, 3.5348861068631985, 0.95]
drawer_chest[0].rotation = [0, 0, 0]
dining_table[0].position = [0.7469465213316258, 5.570444479523516, 0.375]
dining_table[0].rotation = [0, 0, 0]
side_table[0].position = [2.656767459920304, 4.177414681321135, 0.3]
side_table[0].rotation = [0, 0, 0]
three_seat_sofa[0].position = [4.136022332855216, 5.74728796600204, 0.425]
three_seat_sofa[0].rotation = [0, 0, 0]
sideboard[0].position = [4.916598228564799, 2.1132130228629418, 0.4]
sideboard[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [1.1539462100837388, 8.525900710717888, 0.45]
dining_chair_A[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [4.798629750616727, 5.772500229385358, 0.45]
dining_chair_B[0].rotation = [0, 0, 0]
lounge_chair[0].position = [4.701135945739953, 3.26064089920295, 0.575]
lounge_chair[0].rotation = [0, 0, 0]
coffee_table[0].position = [5.917183077652614, 5.940343935936384, 0.225]
coffee_table[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [1.89994049174286, 8.153487181323685, 0.45]
dining_chair_C[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [0.8935817936116681, 5.930733798125072, 0.45]
dining_chair_D[0].rotation = [0, 0, 0]
tv_stand[0].position = [3.194773097143263, 4.593240950092459, 0.325]
tv_stand[0].rotation = [0, 0, 0]
drawer_chest[0].position = [4.462380198094909, 3.5348861068631985, 0.95]
drawer_chest[0].rotation = [0, 0, 0]
dining_table[0].position = [0.7469465213316258, 5.570444479523516, 0.375]
dining_table[0].rotation = [0, 0, 0]
side_table[0].position = [2.656767459920304, 4.177414681321135, 0.3]
side_table[0].rotation = [0, 0, 0]
three_seat_sofa[0].position = [4.136022332855216, 5.74728796600204, 0.425]
three_seat_sofa[0].rotation = [0, 0, 0]
sideboard[0].position = [4.916598228564799, 2.1132130228629418, 0.4]
sideboard[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [1.1539462100837388, 8.525900710717888, 0.45]
dining_chair_A[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [4.798629750616727, 5.772500229385358, 0.45]
dining_chair_B[0].rotation = [0, 0, 0]
lounge_chair[0].position = [4.701135945739953, 3.26064089920295, 0.575]
lounge_chair[0].rotation = [0, 0, 0]
coffee_table[0].position = [5.917183077652614, 5.940343935936384, 0.225]
coffee_table[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [1.89994049174286, 8.153487181323685, 0.45]
dining_chair_C[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [0.8935817936116681, 5.930733798125072, 0.45]
dining_chair_D[0].rotation = [0, 0, 0]
tv_stand[0].position = [3.194773097143263, 4.593240950092459, 0.325]
tv_stand[0].rotation = [0, 0, 0]

solver.constraints = []

# Divide the irregular floor plan into two functional zones:
# - the main lower room contains the living and dining arrangements;
# - the upper-left room holds the tall bookshelf without obstructing its doors/window.
# The large south doorway remains clear to approximately y=2.1.

# --- Initial placements -------------------------------------------------------

# Bookshelf against the east wall of the upper-left room, away from the window
# and from the two door openings on the west side.
drawer_chest[0].position = [2.425, 9.20, 0.95]
drawer_chest[0].rotation = [0, 0, radians(180)]

# Dining table is rotated so its long dimension runs east-west.
dining_table[0].position = [4.15, 5.05, 0.375]
dining_table[0].rotation = [0, 0, radians(90)]

# End table beside the north end of the sofa.
side_table[0].position = [2.40, 4.45, 0.30]
side_table[0].rotation = [0, 0, radians(0)]

# Sofa is placed along the west wall of the main room and faces into the
# living area. Its footprint stays outside the south doorway's width.
three_seat_sofa[0].position = [2.605, 2.50, 0.425]
three_seat_sofa[0].rotation = [0, 0, radians(0)]

# Console against the north wall of the main room.
sideboard[0].position = [5.10, 6.51, 0.40]
sideboard[0].rotation = [0, 0, radians(-90)]

# Chairs A and C occupy opposite ends of the table, making the dining table
# spatially between them as requested.
dining_chair_A[0].position = [2.85, 5.05, 0.45]
dining_chair_A[0].rotation = [0, 0, radians(-62.45)]

dining_chair_B[0].position = [4.15, 4.20, 0.45]
dining_chair_B[0].rotation = [0, 0, radians(90)]

# Lounge chair sits at the northeast corner of the living group.
lounge_chair[0].position = [5.25, 4.05, 0.575]
lounge_chair[0].rotation = [0, 0, radians(-132.71)]

coffee_table[0].position = [4.05, 2.75, 0.225]
coffee_table[0].rotation = [0, 0, radians(0)]

dining_chair_C[0].position = [5.45, 5.05, 0.45]
dining_chair_C[0].rotation = [0, 0, radians(180)]

dining_chair_D[0].position = [4.15, 5.80, 0.45]
dining_chair_D[0].rotation = [0, 0, radians(-90)]

# TV cabinet is opposite the sofa and against the east wall.
tv_stand[0].position = [5.685, 2.30, 0.325]
tv_stand[0].rotation = [0, 0, radians(180)]


# --- Fixed references for position and orientation constraints ----------------

drawer_anchor = AssetInstance(position=[2.425, 9.20, 0.95])
dining_table_anchor = AssetInstance(position=[4.15, 5.05, 0.375])
side_table_anchor = AssetInstance(position=[2.40, 4.45, 0.30])
sofa_anchor = AssetInstance(position=[2.605, 2.50, 0.425])
sideboard_anchor = AssetInstance(position=[5.10, 6.51, 0.40])
chair_A_anchor = AssetInstance(position=[2.85, 5.05, 0.45])
chair_B_anchor = AssetInstance(position=[4.15, 4.20, 0.45])
lounge_anchor = AssetInstance(position=[5.25, 4.05, 0.575])
coffee_table_anchor = AssetInstance(position=[4.05, 2.75, 0.225])
chair_C_anchor = AssetInstance(position=[5.45, 5.05, 0.45])
chair_D_anchor = AssetInstance(position=[4.15, 5.80, 0.45])
tv_anchor = AssetInstance(position=[5.685, 2.30, 0.325])

east_heading = AssetInstance(rotation=[0, 0, radians(0)])
west_heading = AssetInstance(rotation=[0, 0, radians(180)])
north_heading = AssetInstance(rotation=[0, 0, radians(90)])
south_heading = AssetInstance(rotation=[0, 0, radians(-90)])


# --- Position constraints -----------------------------------------------------
# High-weight anchors preserve door clearances and the non-overlapping zoning.

solver.distance_constraint(
    drawer_chest[0], drawer_anchor, 0, 0, weight=10
)
solver.against_wall(drawer_chest[0], walls[7])

solver.distance_constraint(
    dining_table[0], dining_table_anchor, 0, 0, weight=10
)

solver.distance_constraint(
    side_table[0], side_table_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    side_table[0], three_seat_sofa[0], 1.90, 2.10, weight=1
)

solver.distance_constraint(
    three_seat_sofa[0], sofa_anchor, 0, 0, weight=10
)
solver.against_wall(three_seat_sofa[0], walls[11])

solver.distance_constraint(
    sideboard[0], sideboard_anchor, 0, 0, weight=10
)
solver.against_wall(sideboard[0], walls[6])

solver.distance_constraint(
    dining_chair_A[0], chair_A_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    dining_chair_A[0], dining_table[0], 1.30, 1.30, weight=5
)

solver.distance_constraint(
    dining_chair_B[0], chair_B_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    dining_chair_B[0], dining_table[0], 0.85, 0.85, weight=5
)

solver.distance_constraint(
    lounge_chair[0], lounge_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    lounge_chair[0], coffee_table[0], 1.75, 1.85, weight=2
)

solver.distance_constraint(
    coffee_table[0], coffee_table_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    coffee_table[0], three_seat_sofa[0], 1.40, 1.55, weight=5
)

solver.distance_constraint(
    dining_chair_C[0], chair_C_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    dining_chair_C[0], dining_table[0], 1.30, 1.30, weight=5
)
# Together with the equal chair-to-table distances, this maintains the
# requested A -- dining table -- C ordering.
solver.distance_constraint(
    dining_chair_A[0], dining_chair_C[0], 2.60, 2.60, weight=2
)

solver.distance_constraint(
    dining_chair_D[0], chair_D_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    dining_chair_D[0], dining_table[0], 0.75, 0.75, weight=5
)

solver.distance_constraint(
    tv_stand[0], tv_anchor, 0, 0, weight=10
)
solver.against_wall(tv_stand[0], walls[1])
solver.distance_constraint(
    tv_stand[0], three_seat_sofa[0], 3.08, 3.08, weight=2
)


# --- Orientation constraints -------------------------------------------------
# Every new asset receives an orientation constraint. Relational facing
# constraints are used where the furniture has a clear functional target.

solver.align_with(drawer_chest[0], west_heading)
solver.align_with(dining_table[0], north_heading)
solver.align_with(side_table[0], east_heading)

solver.point_towards(three_seat_sofa[0], coffee_table[0])
solver.align_with(sideboard[0], south_heading)

# This is specified before any other orientation relationship for chair A so
# the explicit requirement that it face the coffee table takes precedence.
solver.point_towards(dining_chair_A[0], coffee_table[0])

solver.point_towards(dining_chair_B[0], dining_table[0])
solver.point_towards(lounge_chair[0], coffee_table[0])
solver.align_with(coffee_table[0], three_seat_sofa[0])
solver.point_towards(dining_chair_C[0], dining_table[0])
solver.point_towards(dining_chair_D[0], dining_table[0])
solver.point_towards(tv_stand[0], three_seat_sofa[0])

solver.constraints = []
side_table[0].position = [2.4000000953674316, 4.449999809265137, 0.30000001192092896]
side_table[0].rotation = [0, 0, 0.01256637125682779]
side_table[0].optimize = 2
three_seat_sofa[0].position = [3.491278648376465, 2.5, 0.42500001192092896]
three_seat_sofa[0].rotation = [0, 0, 0.7348745476764773]
three_seat_sofa[0].optimize = 2
drawer_chest[0].position = [2.420525312423706, 9.199999809265137, 0.949999988079071]
drawer_chest[0].rotation = [0, 0, 3.1414860600372734]
drawer_chest[0].optimize = 2
coffee_table[0].position = [4.050000190734863, 2.75, 0.22499999403953552]
coffee_table[0].rotation = [0, 0, 0.7236501740446911]
coffee_table[0].optimize = 2
tv_stand[0].position = [5.683421611785889, 2.236599922180176, 0.32499998807907104]
tv_stand[0].rotation = [0, 0, -3.14039159248174]
tv_stand[0].optimize = 2
dining_chair_D[0].position = [4.150000095367432, 5.857126235961914, 0.44999998807907104]
dining_chair_D[0].rotation = [0, 0, -1.5582299555380688]
dining_chair_D[0].optimize = 2
sideboard[0].position = [5.099999904632568, 6.137151718139648, 0.4000000059604645]
sideboard[0].rotation = [0, 0, -2.1374485372738845]
sideboard[0].optimize = 2
dining_chair_C[0].position = [5.45465087890625, 5.050000190734863, 0.44999998807907104]
dining_chair_C[0].rotation = [0, 0, -3.125884689672577]
dining_chair_C[0].optimize = 2
dining_chair_B[0].position = [4.150000095367432, 4.199999809265137, 0.44999998807907104]
dining_chair_B[0].rotation = [0, 0, 1.5833626980517244]
dining_chair_B[0].optimize = 2
dining_chair_A[0].position = [2.846834421157837, 5.050000190734863, 0.44999998807907104]
dining_chair_A[0].rotation = [0, 0, -1.0742501502943589]
dining_chair_A[0].optimize = 2
dining_table[0].position = [4.150000095367432, 5.050000190734863, 0.375]
dining_table[0].rotation = [0, 0, 1.6022122525607134]
dining_table[0].optimize = 2
lounge_chair[0].position = [5.25, 4.050000190734863, 0.574999988079071]
lounge_chair[0].rotation = [0, 0, -2.3036600741375612]
lounge_chair[0].optimize = 2

