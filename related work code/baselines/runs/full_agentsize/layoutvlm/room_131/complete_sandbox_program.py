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
accent_shelf = Assets(description="A stack of six wood shelves.", size=[0.32, 0.80, 1.80], placements=[AssetInstance() for _ in range(1)])
bedside_table_A = Assets(description="A nightstand with one drawer.", size=[0.42, 0.50, 0.58], placements=[AssetInstance() for _ in range(1)])
desk_chair = Assets(description="It is a chair with short cloth covered arms.", size=[0.65, 0.62, 0.90], placements=[AssetInstance() for _ in range(1)])
bed_pillow = Assets(description="A plain white square pillow.", size=[0.40, 0.65, 0.15], placements=[AssetInstance() for _ in range(1)])
table_lamp_A = Assets(description="A table lamp with a lampshade on it.", size=[0.32, 0.32, 0.55], placements=[AssetInstance() for _ in range(1)])
table_lamp_B = Assets(description="A table lamp with a lampshade on it.", size=[0.32, 0.32, 0.55], placements=[AssetInstance() for _ in range(1)])
writing_desk = Assets(description="A brown desk with black metal pieces.", size=[0.60, 1.30, 0.76], placements=[AssetInstance() for _ in range(1)])
queen_bed = Assets(description="A bed with a beige comforter and pillows and orange wooden frame.", size=[2.15, 1.65, 0.65], placements=[AssetInstance() for _ in range(1)])
bedside_table_B = Assets(description="A nightstand with one drawer.", size=[0.42, 0.50, 0.58], placements=[AssetInstance() for _ in range(1)])
book = Assets(description="A leather hardback book with a black band and lock around it.", size=[0.23, 0.16, 0.04], placements=[AssetInstance() for _ in range(1)])

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

accent_shelf[0].position = [2.9788666891477003, 4.585914200720817, 0.9]
accent_shelf[0].rotation = [0, 0, 0]
bedside_table_A[0].position = [3.66973957092862, 3.433487037510522, 0.29]
bedside_table_A[0].rotation = [0, 0, 0]
desk_chair[0].position = [2.6585269249689802, 2.742116398141178, 0.45]
desk_chair[0].rotation = [0, 0, 0]
bed_pillow[0].position = [2.126994467299185, 3.5966104856214267, 0.075]
bed_pillow[0].rotation = [0, 0, 0]
table_lamp_A[0].position = [3.8308501394229486, 3.9482556500429897, 0.275]
table_lamp_A[0].rotation = [0, 0, 0]
table_lamp_B[0].position = [3.7283499165975087, 0.8188055225655766, 0.275]
table_lamp_B[0].rotation = [0, 0, 0]
writing_desk[0].position = [1.6955580816022624, 3.2467628142979947, 0.38]
writing_desk[0].rotation = [0, 0, 0]
queen_bed[0].position = [3.4433439628555926, 4.991616274167681, 0.325]
queen_bed[0].rotation = [0, 0, 0]
bedside_table_B[0].position = [3.3072526743732453, 1.839836897946145, 0.29]
bedside_table_B[0].rotation = [0, 0, 0]
book[0].position = [3.7156119727593846, 0.1384420928631841, 0.02]
book[0].rotation = [0, 0, 0]
accent_shelf[0].position = [2.9788666891477003, 4.585914200720817, 0.9]
accent_shelf[0].rotation = [0, 0, 0]
bedside_table_A[0].position = [3.66973957092862, 3.433487037510522, 0.29]
bedside_table_A[0].rotation = [0, 0, 0]
desk_chair[0].position = [2.6585269249689802, 2.742116398141178, 0.45]
desk_chair[0].rotation = [0, 0, 0]
bed_pillow[0].position = [2.126994467299185, 3.5966104856214267, 0.075]
bed_pillow[0].rotation = [0, 0, 0]
table_lamp_A[0].position = [3.8308501394229486, 3.9482556500429897, 0.275]
table_lamp_A[0].rotation = [0, 0, 0]
table_lamp_B[0].position = [3.7283499165975087, 0.8188055225655766, 0.275]
table_lamp_B[0].rotation = [0, 0, 0]
writing_desk[0].position = [1.6955580816022624, 3.2467628142979947, 0.38]
writing_desk[0].rotation = [0, 0, 0]
queen_bed[0].position = [3.4433439628555926, 4.991616274167681, 0.325]
queen_bed[0].rotation = [0, 0, 0]
bedside_table_B[0].position = [3.3072526743732453, 1.839836897946145, 0.29]
bedside_table_B[0].rotation = [0, 0, 0]
book[0].position = [3.7156119727593846, 0.1384420928631841, 0.02]
book[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the bed with its head against the left wall. It faces +x toward the
# chair, while leaving a comfortable aisle between the bed and work area.
queen_bed[0].position = [1.075, 3.50, 0.325]
queen_bed[0].rotation = [0, 0, radians(0)]

# Put one nightstand on either side of the bed's head, against the same wall.
bedside_table_A[0].position = [0.21, 2.35, 0.29]
bedside_table_A[0].rotation = [0, 0, radians(0)]

bedside_table_B[0].position = [0.21, 4.65, 0.29]
bedside_table_B[0].rotation = [0, 0, radians(0)]

# Center each lamp on its corresponding nightstand.
table_lamp_A[0].position = [0.21, 2.35, 0.855]
table_lamp_A[0].rotation = [0, 0, radians(0)]

table_lamp_B[0].position = [0.21, 4.65, 0.855]
table_lamp_B[0].rotation = [0, 0, radians(0)]

# Place the pillow near the head of the bed.
bed_pillow[0].position = [0.60, 3.50, 0.725]
bed_pillow[0].rotation = [0, 0, radians(0)]

# Create a work area on the right wall, well above the doorway at y=1.41.
# The desk faces into the room and the chair faces the desk.
writing_desk[0].position = [3.70, 3.50, 0.38]
writing_desk[0].rotation = [0, 0, radians(180)]

desk_chair[0].position = [2.75, 3.50, 0.45]
desk_chair[0].rotation = [0, 0, radians(0)]

# Place the narrow shelf against the bottom wall, away from the door approach.
accent_shelf[0].position = [1.20, 0.16, 0.90]
accent_shelf[0].rotation = [0, 0, radians(90)]

# The book is centered on the top surface of the shelf.
book[0].position = [1.20, 0.16, 1.82]
book[0].rotation = [0, 0, radians(90)]


# Fixed reference points used only to express orientation and door clearance.
shelf_room_reference = AssetInstance(position=[1.20, 2.00, 0.90])
door_clearance_reference = AssetInstance(position=[3.65, 1.41, 0.40])


# Highest-priority semantic requirements from the layout criteria.
solver.against_wall(accent_shelf[0], walls[0])
solver.on_top_of(book[0], accent_shelf[0])
solver.point_towards(queen_bed[0], desk_chair[0])

# Keep the bed and both nightstands along the left wall.
solver.against_wall(queen_bed[0], walls[3])
solver.against_wall(bedside_table_A[0], walls[3])
solver.against_wall(bedside_table_B[0], walls[3])

# Keep each nightstand near its intended side of the bed.
solver.distance_constraint(
    bedside_table_A[0], queen_bed[0],
    min_distance=1.35, max_distance=1.52, weight=10
)
solver.distance_constraint(
    bedside_table_B[0], queen_bed[0],
    min_distance=1.35, max_distance=1.52, weight=10
)
solver.align_with(bedside_table_A[0], queen_bed[0])
solver.align_with(bedside_table_B[0], queen_bed[0])

# Support and center the two lamps on their respective nightstands. The exact
# center distance is their expected vertical center separation when stacked.
solver.on_top_of(table_lamp_A[0], bedside_table_A[0])
solver.distance_constraint(
    table_lamp_A[0], bedside_table_A[0],
    min_distance=0.565, max_distance=0.565, weight=10
)
solver.align_with(table_lamp_A[0], bedside_table_A[0])

solver.on_top_of(table_lamp_B[0], bedside_table_B[0])
solver.distance_constraint(
    table_lamp_B[0], bedside_table_B[0],
    min_distance=0.565, max_distance=0.565, weight=10
)
solver.align_with(table_lamp_B[0], bedside_table_B[0])

# Keep the pillow supported near the head of the bed and oriented with it.
solver.on_top_of(bed_pillow[0], queen_bed[0])
solver.distance_constraint(
    bed_pillow[0], queen_bed[0],
    min_distance=0.60, max_distance=0.66, weight=10
)
solver.align_with(bed_pillow[0], queen_bed[0])

# Keep the desk against the right wall and maintain a usable chair-to-desk
# spacing. The chair faces the desk, while the desk faces back toward it.
solver.against_wall(writing_desk[0], walls[1])
solver.distance_constraint(
    desk_chair[0], writing_desk[0],
    min_distance=0.90, max_distance=1.02, weight=10
)
solver.point_towards(desk_chair[0], writing_desk[0])
solver.point_towards(writing_desk[0], desk_chair[0])

# Maintain the intended bed/chair relationship without allowing the chair to
# drift into the bed.
solver.distance_constraint(
    desk_chair[0], queen_bed[0],
    min_distance=1.60, max_distance=1.82, weight=10
)

# Guard the clear floor area in front of the doorway.
solver.distance_constraint(
    desk_chair[0], door_clearance_reference,
    min_distance=1.50, max_distance=None, weight=10
)
solver.distance_constraint(
    writing_desk[0], door_clearance_reference,
    min_distance=1.50, max_distance=None, weight=10
)

# Orient the shelf into the room. Keep the book centered on its top and aligned
# with the shelf; 0.92 m is the vertical center separation when stacked.
solver.point_towards(accent_shelf[0], shelf_room_reference)
solver.distance_constraint(
    book[0], accent_shelf[0],
    min_distance=0.92, max_distance=0.92, weight=10
)
solver.align_with(book[0], accent_shelf[0])

solver.constraints = []
writing_desk[0].position = [3.7000484466552734, 3.5, 0.3799999952316284]
writing_desk[0].rotation = [0, 0, -3.141521404291312]
writing_desk[0].optimize = 2
accent_shelf[0].position = [1.2000000476837158, 0.15999972820281982, 0.8999999761581421]
accent_shelf[0].rotation = [0, 0, 1.5708678122113346]
accent_shelf[0].optimize = 2
bedside_table_B[0].position = [0.21001161634922028, 4.650000095367432, 0.28999999165534973]
bedside_table_B[0].rotation = [0, 0, -7.80411904103515e-05]
bedside_table_B[0].optimize = 2
book[0].position = [1.2000000476837158, 0.11500847339630127, 1.8199999332427979]
book[0].rotation = [0, 0, 1.570690470243474]
book[0].optimize = 2
bedside_table_A[0].position = [0.21001161634922028, 2.3499999046325684, 0.28999999165534973]
bedside_table_A[0].rotation = [0, 0, -7.80411904103515e-05]
bedside_table_A[0].optimize = 2
table_lamp_A[0].position = [0.15995687246322632, 2.3499999046325684, 0.8550000190734863]
table_lamp_A[0].rotation = [0, 0, 0.00026957701336796587]
table_lamp_A[0].optimize = 2
bed_pillow[0].position = [0.20011714100837708, 3.5, 0.7249999642372131]
bed_pillow[0].rotation = [0, 0, -0.0003605129007437741]
bed_pillow[0].optimize = 2
table_lamp_B[0].position = [0.15995687246322632, 4.650000095367432, 0.8550000190734863]
table_lamp_B[0].rotation = [0, 0, 0.00026957701336796587]
table_lamp_B[0].optimize = 2
desk_chair[0].position = [2.75, 3.5, 0.44999998807907104]
desk_chair[0].rotation = [0, 0, 0.021991148286022624]
desk_chair[0].optimize = 2
queen_bed[0].position = [1.0750346183776855, 3.5, 0.32499998807907104]
queen_bed[0].rotation = [0, 0, 0.0001350044815886701]
queen_bed[0].optimize = 2

