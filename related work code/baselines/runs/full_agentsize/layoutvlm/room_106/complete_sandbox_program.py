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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.00, 0.00, 0.00]),
    Wall(corner1=[6.00, 0.00, 0.00], corner2=[6.00, 3.00, 0.00]),
    Wall(corner1=[6.00, 3.00, 0.00], corner2=[0.00, 3.00, 0.00]),
    Wall(corner1=[0.00, 3.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
storage_box_A = Assets(description="A wooden box with the lid off and the word fragile written on the side.", size=[0.40, 0.55, 0.32], placements=[AssetInstance() for _ in range(1)])
tall_storage_cabinet_A = Assets(description="A light wooden wardrobe.", size=[0.55, 1.00, 2.00], placements=[AssetInstance() for _ in range(1)])
meeting_chair = Assets(description="A chair with a blue plastic top and metal legs.", size=[0.55, 0.52, 0.82], placements=[AssetInstance() for _ in range(1)])
guest_chair_A = Assets(description="A brown chair with black legs.", size=[0.62, 0.58, 0.84], placements=[AssetInstance() for _ in range(1)])
side_table = Assets(description="A round wooden table holding a blue and white owl statue.", size=[0.55, 0.55, 0.58], placements=[AssetInstance() for _ in range(1)])
picture_frame = Assets(description="A black and white painting of a robed person standing in a raft.", size=[0.08, 0.55, 0.70], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="It is a hard cover book with a blue cover.", size=[0.24, 0.16, 0.04], placements=[AssetInstance() for _ in range(1)])
guest_chair_B = Assets(description="A brown chair with black legs.", size=[0.62, 0.58, 0.84], placements=[AssetInstance() for _ in range(1)])
guest_chair_C = Assets(description="A brown chair with black legs.", size=[0.62, 0.58, 0.84], placements=[AssetInstance() for _ in range(1)])
low_credenza = Assets(description="A white cabinet with a set of drawers.", size=[0.45, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
waste_bin_A = Assets(description="A cream colored trash can.", size=[0.30, 0.30, 0.42], placements=[AssetInstance() for _ in range(1)])
floor_lamp_A = Assets(description="floor lamp", size=[0.32, 0.32, 1.65], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="Book with purple cover and yellow spine titled the best book ever.", size=[0.24, 0.16, 0.04], placements=[AssetInstance() for _ in range(1)])
storage_box_B = Assets(description="A wooden box with the lid off and the word fragile written on the side.", size=[0.40, 0.55, 0.32], placements=[AssetInstance() for _ in range(1)])
waste_bin_B = Assets(description="A cream colored trash can.", size=[0.30, 0.30, 0.42], placements=[AssetInstance() for _ in range(1)])
floor_lamp_B = Assets(description="floor lamp", size=[0.32, 0.32, 1.65], placements=[AssetInstance() for _ in range(1)])
tall_storage_cabinet_B = Assets(description="A light wooden wardrobe.", size=[0.55, 1.00, 2.00], placements=[AssetInstance() for _ in range(1)])
freestanding_bookshelf = Assets(description="It is a tall set of shelves made of wood and metal.", size=[0.38, 1.20, 1.90], placements=[AssetInstance() for _ in range(1)])

storage_box_A[0].instance_id = 'storage_box_A_0'
tall_storage_cabinet_A[0].instance_id = 'tall_storage_cabinet_A_0'
meeting_chair[0].instance_id = 'meeting_chair_0'
guest_chair_A[0].instance_id = 'guest_chair_A_0'
side_table[0].instance_id = 'side_table_0'
picture_frame[0].instance_id = 'picture_frame_0'
book_A[0].instance_id = 'book_A_0'
guest_chair_B[0].instance_id = 'guest_chair_B_0'
guest_chair_C[0].instance_id = 'guest_chair_C_0'
low_credenza[0].instance_id = 'low_credenza_0'
waste_bin_A[0].instance_id = 'waste_bin_A_0'
floor_lamp_A[0].instance_id = 'floor_lamp_A_0'
book_B[0].instance_id = 'book_B_0'
storage_box_B[0].instance_id = 'storage_box_B_0'
waste_bin_B[0].instance_id = 'waste_bin_B_0'
floor_lamp_B[0].instance_id = 'floor_lamp_B_0'
tall_storage_cabinet_B[0].instance_id = 'tall_storage_cabinet_B_0'
freestanding_bookshelf[0].instance_id = 'freestanding_bookshelf_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

storage_box_A[0].position = [4.014998482585332, 0.41183376773641434, 0.16]
storage_box_A[0].rotation = [0, 0, 0]
tall_storage_cabinet_A[0].position = [1.5477184923209466, 0.7129469239853651, 1.0]
tall_storage_cabinet_A[0].rotation = [0, 0, 0]
meeting_chair[0].position = [2.6106510147364688, 2.692975224125453, 0.41]
meeting_chair[0].rotation = [0, 0, 0]
guest_chair_A[0].position = [4.67173269630031, 1.6387907044320587, 0.42]
guest_chair_A[0].rotation = [0, 0, 0]
side_table[0].position = [0.2443241569619905, 2.7659507394076606, 0.29]
side_table[0].rotation = [0, 0, 0]
picture_frame[0].position = [3.2121315410210163, 1.1718485178670472, 0.35]
picture_frame[0].rotation = [0, 0, 0]
book_A[0].position = [0.5662076638314051, 2.0624623300676572, 0.0175]
book_A[0].rotation = [0, 0, 0]
guest_chair_B[0].position = [3.571065165241901, 0.9165826608175778, 0.42]
guest_chair_B[0].rotation = [0, 0, 0]
guest_chair_C[0].position = [4.176945678684131, 1.4880802103535025, 0.42]
guest_chair_C[0].rotation = [0, 0, 0]
low_credenza[0].position = [2.1712503789802375, 2.160226989345455, 0.375]
low_credenza[0].rotation = [0, 0, 0]
waste_bin_A[0].position = [5.763977665433951, 2.4028208049989965, 0.21]
waste_bin_A[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [2.46353755732832, 1.732437155220065, 0.825]
floor_lamp_A[0].rotation = [0, 0, 0]
book_B[0].position = [1.664908066717801, 2.7880314895346894, 0.0175]
book_B[0].rotation = [0, 0, 0]
storage_box_B[0].position = [2.5292514244283844, 0.8645146572458301, 0.16]
storage_box_B[0].rotation = [0, 0, 0]
waste_bin_B[0].position = [4.9173143607922825, 1.2657112891326343, 0.21]
waste_bin_B[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [4.0281752904289725, 1.593726357999145, 0.825]
floor_lamp_B[0].rotation = [0, 0, 0]
tall_storage_cabinet_B[0].position = [2.4293249323338193, 1.5761348607894723, 1.0]
tall_storage_cabinet_B[0].rotation = [0, 0, 0]
freestanding_bookshelf[0].position = [5.39062522114143, 0.15865338725550093, 0.95]
freestanding_bookshelf[0].rotation = [0, 0, 0]
storage_box_A[0].position = [4.014998482585332, 0.41183376773641434, 0.16]
storage_box_A[0].rotation = [0, 0, 0]
tall_storage_cabinet_A[0].position = [1.5477184923209466, 0.7129469239853651, 1.0]
tall_storage_cabinet_A[0].rotation = [0, 0, 0]
meeting_chair[0].position = [2.6106510147364688, 2.692975224125453, 0.41]
meeting_chair[0].rotation = [0, 0, 0]
guest_chair_A[0].position = [4.67173269630031, 1.6387907044320587, 0.42]
guest_chair_A[0].rotation = [0, 0, 0]
side_table[0].position = [0.2443241569619905, 2.7659507394076606, 0.29]
side_table[0].rotation = [0, 0, 0]
picture_frame[0].position = [3.2121315410210163, 1.1718485178670472, 0.35]
picture_frame[0].rotation = [0, 0, 0]
book_A[0].position = [0.5662076638314051, 2.0624623300676572, 0.0175]
book_A[0].rotation = [0, 0, 0]
guest_chair_B[0].position = [3.571065165241901, 0.9165826608175778, 0.42]
guest_chair_B[0].rotation = [0, 0, 0]
guest_chair_C[0].position = [4.176945678684131, 1.4880802103535025, 0.42]
guest_chair_C[0].rotation = [0, 0, 0]
low_credenza[0].position = [2.1712503789802375, 2.160226989345455, 0.375]
low_credenza[0].rotation = [0, 0, 0]
waste_bin_A[0].position = [5.763977665433951, 2.4028208049989965, 0.21]
waste_bin_A[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [2.46353755732832, 1.732437155220065, 0.825]
floor_lamp_A[0].rotation = [0, 0, 0]
book_B[0].position = [1.664908066717801, 2.7880314895346894, 0.0175]
book_B[0].rotation = [0, 0, 0]
storage_box_B[0].position = [2.5292514244283844, 0.8645146572458301, 0.16]
storage_box_B[0].rotation = [0, 0, 0]
waste_bin_B[0].position = [4.9173143607922825, 1.2657112891326343, 0.21]
waste_bin_B[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [4.0281752904289725, 1.593726357999145, 0.825]
floor_lamp_B[0].rotation = [0, 0, 0]
tall_storage_cabinet_B[0].position = [2.4293249323338193, 1.5761348607894723, 1.0]
tall_storage_cabinet_B[0].rotation = [0, 0, 0]
freestanding_bookshelf[0].position = [5.39062522114143, 0.15865338725550093, 0.95]
freestanding_bookshelf[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the two tall cabinets along the upper wall, away from both windows
# and from the door on the right wall.
tall_storage_cabinet_A[0].position = [0.55, 2.725, 1.00]
tall_storage_cabinet_A[0].rotation = [0, 0, radians(-90)]

tall_storage_cabinet_B[0].position = [1.65, 2.725, 1.00]
tall_storage_cabinet_B[0].rotation = [0, 0, radians(-90)]

# Each storage box is centered on its corresponding cabinet. In particular,
# storage_box_B (o0013) is placed on tall_storage_cabinet_B (o0016).
storage_box_A[0].position = [0.55, 2.725, 2.16]
storage_box_A[0].rotation = [0, 0, radians(-90)]

storage_box_B[0].position = [1.65, 2.725, 2.16]
storage_box_B[0].rotation = [0, 0, radians(-90)]

# Put the bookshelf on the upper portion of the right wall. Its lower edge is
# above the door opening, leaving the door and the floor in front of it clear.
freestanding_bookshelf[0].position = [5.81, 2.30, 0.95]
freestanding_bookshelf[0].rotation = [0, 0, radians(180)]

# Place the low credenza along the bottom wall, clear of the door approach.
low_credenza[0].position = [4.05, 0.225, 0.375]
low_credenza[0].rotation = [0, 0, radians(90)]

# Hang the picture on an unobstructed part of the upper wall.
picture_frame[0].position = [3.00, 2.96, 1.55]
picture_frame[0].rotation = [0, 0, radians(-90)]

# Arrange the three guest chairs in a row facing the bookshelf. The ordering
# along x is guest_chair_C (o0008), guest_chair_B (o0007), guest_chair_A
# (o0003), so o0007 is between the other two.
guest_chair_C[0].position = [2.40, 1.75, 0.42]
guest_chair_C[0].rotation = [0, 0, 0]

guest_chair_B[0].position = [3.15, 1.75, 0.42]
guest_chair_B[0].rotation = [0, 0, 0]

guest_chair_A[0].position = [3.90, 1.75, 0.42]
guest_chair_A[0].rotation = [0, 0, 0]

# Place the side table near the seating group while retaining clearance from
# both the nearest chair and the bookshelf.
side_table[0].position = [4.80, 2.15, 0.29]
side_table[0].rotation = [0, 0, 0]

# The meeting chair is in the lower-left part of the room, oriented toward the
# credenza and separated from the guest-chair row.
meeting_chair[0].position = [1.55, 0.75, 0.41]
meeting_chair[0].rotation = [0, 0, 0]

# Put one book on the side table and the other on the credenza.
book_A[0].position = [4.80, 2.15, 0.60]
book_A[0].rotation = [0, 0, 0]

book_B[0].position = [4.05, 0.225, 0.77]
book_B[0].rotation = [0, 0, radians(90)]

# Keep one bin beside the credenza but below the door opening, and place the
# other near the seating area without obstructing either left-wall window.
waste_bin_A[0].position = [5.18, 0.25, 0.21]
waste_bin_A[0].rotation = [0, 0, radians(135)]

waste_bin_B[0].position = [1.25, 1.65, 0.21]
waste_bin_B[0].rotation = [0, 0, 0]

# Use opposite corners for the lamps. The upper lamp is left of the picture,
# and neither lamp blocks a window or the door.
floor_lamp_A[0].position = [0.30, 0.30, 0.825]
floor_lamp_A[0].rotation = [0, 0, radians(45)]

floor_lamp_B[0].position = [2.45, 2.82, 0.825]
floor_lamp_B[0].rotation = [0, 0, radians(-45)]


# Fixed points retain the intended spacing along walls and within the seating
# group while the wall and object-relative constraints preserve semantics.
cabinet_A_anchor = AssetInstance(position=[0.55, 2.725, 1.00])
cabinet_B_anchor = AssetInstance(position=[1.65, 2.725, 1.00])
bookshelf_anchor = AssetInstance(position=[5.81, 2.30, 0.95])
credenza_anchor = AssetInstance(position=[4.05, 0.225, 0.375])
picture_anchor = AssetInstance(position=[3.00, 2.96, 1.55])
meeting_chair_anchor = AssetInstance(position=[1.55, 0.75, 0.41])
guest_chair_A_anchor = AssetInstance(position=[3.90, 1.75, 0.42])
guest_chair_B_anchor = AssetInstance(position=[3.15, 1.75, 0.42])
guest_chair_C_anchor = AssetInstance(position=[2.40, 1.75, 0.42])
side_table_anchor = AssetInstance(position=[4.80, 2.15, 0.29])
waste_bin_A_anchor = AssetInstance(position=[5.18, 0.25, 0.21])
waste_bin_B_anchor = AssetInstance(position=[1.25, 1.65, 0.21])
floor_lamp_A_anchor = AssetInstance(position=[0.30, 0.30, 0.825])
floor_lamp_B_anchor = AssetInstance(position=[2.45, 2.82, 0.825])
room_center = AssetInstance(position=[3.00, 1.50, 0.80])

# Storage-box support constraints are listed first because their vertical
# relationships are required layout semantics.
solver.on_top_of(storage_box_A[0], tall_storage_cabinet_A[0])
solver.distance_constraint(
    storage_box_A[0], tall_storage_cabinet_A[0], 1.16, 1.16, weight=10
)
solver.align_with(storage_box_A[0], tall_storage_cabinet_A[0])

solver.on_top_of(storage_box_B[0], tall_storage_cabinet_B[0])
solver.distance_constraint(
    storage_box_B[0], tall_storage_cabinet_B[0], 1.16, 1.16, weight=10
)
solver.align_with(storage_box_B[0], tall_storage_cabinet_B[0])

# Wall furniture is constrained to the appropriate wall and anchored along it.
solver.against_wall(tall_storage_cabinet_A[0], walls[2])
solver.distance_constraint(
    tall_storage_cabinet_A[0], cabinet_A_anchor, 0, 0, weight=10
)
solver.point_towards(tall_storage_cabinet_A[0], room_center)

solver.against_wall(tall_storage_cabinet_B[0], walls[2])
solver.distance_constraint(
    tall_storage_cabinet_B[0], cabinet_B_anchor, 0, 0, weight=10
)
solver.point_towards(tall_storage_cabinet_B[0], room_center)

solver.against_wall(freestanding_bookshelf[0], walls[1])
solver.distance_constraint(
    freestanding_bookshelf[0], bookshelf_anchor, 0, 0, weight=10
)
solver.point_towards(freestanding_bookshelf[0], room_center)

solver.against_wall(low_credenza[0], walls[0])
solver.distance_constraint(
    low_credenza[0], credenza_anchor, 0, 0, weight=10
)
solver.point_towards(low_credenza[0], room_center)

solver.against_wall(picture_frame[0], walls[2])
solver.distance_constraint(
    picture_frame[0], picture_anchor, 0, 0, weight=10
)
solver.point_towards(picture_frame[0], room_center)

# Preserve the required guest-chair ordering with exact row anchors. All three
# chairs face the bookshelf; this explicitly satisfies the requirement that
# guest_chair_A (o0003) face it.
solver.distance_constraint(
    guest_chair_A[0], guest_chair_A_anchor, 0, 0, weight=10
)
solver.point_towards(guest_chair_A[0], freestanding_bookshelf[0])

solver.distance_constraint(
    guest_chair_B[0], guest_chair_B_anchor, 0, 0, weight=10
)
solver.point_towards(guest_chair_B[0], freestanding_bookshelf[0])
solver.distance_constraint(
    guest_chair_B[0], guest_chair_C[0], 0.75, 0.75, weight=10
)
solver.distance_constraint(
    guest_chair_B[0], guest_chair_A[0], 0.75, 0.75, weight=10
)

solver.distance_constraint(
    guest_chair_C[0], guest_chair_C_anchor, 0, 0, weight=10
)
solver.point_towards(guest_chair_C[0], freestanding_bookshelf[0])

solver.distance_constraint(
    meeting_chair[0], meeting_chair_anchor, 0, 0, weight=10
)
solver.point_towards(meeting_chair[0], low_credenza[0])

solver.distance_constraint(side_table[0], side_table_anchor, 0, 0, weight=10)
solver.point_towards(side_table[0], guest_chair_A[0])

# The books receive both support and position-based constraints, with their
# rotations aligned to the surfaces beneath them.
solver.on_top_of(book_A[0], side_table[0])
solver.distance_constraint(book_A[0], side_table[0], 0.31, 0.31, weight=10)
solver.align_with(book_A[0], side_table[0])

solver.on_top_of(book_B[0], low_credenza[0])
solver.distance_constraint(book_B[0], low_credenza[0], 0.395, 0.395, weight=10)
solver.align_with(book_B[0], low_credenza[0])

solver.distance_constraint(
    waste_bin_A[0], waste_bin_A_anchor, 0, 0, weight=10
)
solver.point_towards(waste_bin_A[0], low_credenza[0])

solver.distance_constraint(
    waste_bin_B[0], waste_bin_B_anchor, 0, 0, weight=10
)
solver.point_towards(waste_bin_B[0], guest_chair_C[0])

solver.against_wall(floor_lamp_A[0], walls[0])
solver.distance_constraint(
    floor_lamp_A[0], floor_lamp_A_anchor, 0, 0, weight=10
)
solver.point_towards(floor_lamp_A[0], room_center)

solver.against_wall(floor_lamp_B[0], walls[2])
solver.distance_constraint(
    floor_lamp_B[0], floor_lamp_B_anchor, 0, 0, weight=10
)
solver.point_towards(floor_lamp_B[0], room_center)

solver.constraints = []
tall_storage_cabinet_A[0].position = [0.550000011920929, 2.7250003814697266, 1.0]
tall_storage_cabinet_A[0].rotation = [0, 0, -1.570796277699516]
tall_storage_cabinet_A[0].optimize = 2
tall_storage_cabinet_B[0].position = [1.649999976158142, 2.7250003814697266, 1.0]
tall_storage_cabinet_B[0].rotation = [0, 0, -1.570796277699516]
tall_storage_cabinet_B[0].optimize = 2
side_table[0].position = [4.800000190734863, 2.1500000953674316, 0.28999999165534973]
side_table[0].rotation = [0, 0, -2.2847491321016182]
side_table[0].optimize = 2
guest_chair_A[0].position = [3.9000000953674316, 1.75, 0.41999998688697815]
guest_chair_A[0].rotation = [0, 0, 0.0157079639172164]
guest_chair_A[0].optimize = 2
guest_chair_C[0].position = [2.4000000953674316, 1.75, 0.41999998688697815]
guest_chair_C[0].rotation = [0, 0, 0.0157079639172164]
guest_chair_C[0].optimize = 2
storage_box_B[0].position = [1.649999976158142, 2.7249999046325684, 2.1600000858306885]
storage_box_B[0].rotation = [0, 0, -1.570796267688273]
storage_box_B[0].optimize = 2
floor_lamp_A[0].position = [0.30000001192092896, 0.15999995172023773, 0.824999988079071]
floor_lamp_A[0].rotation = [0, 0, 1.5707966186810025]
floor_lamp_A[0].optimize = 2
book_A[0].position = [4.800000190734863, 2.1500000953674316, 0.5999999642372131]
book_A[0].rotation = [0, 0, -2.284750430795515]
book_A[0].optimize = 2
book_B[0].position = [4.050000190734863, 0.12000000476837158, 0.7699999809265137]
book_B[0].rotation = [0, 0, 1.570796367653811]
book_B[0].optimize = 2
freestanding_bookshelf[0].position = [5.809999942779541, 2.299999952316284, 0.949999988079071]
freestanding_bookshelf[0].rotation = [0, 0, -3.14159260251802]
freestanding_bookshelf[0].optimize = 2
picture_frame[0].position = [3.0, 2.9600000381469727, 0.3499999940395355]
picture_frame[0].rotation = [0, 0, -1.5707962790426024]
picture_frame[0].optimize = 2
waste_bin_A[0].position = [5.179999828338623, 0.25, 0.20999999344348907]
waste_bin_A[0].rotation = [0, 0, 2.6135237268067]
waste_bin_A[0].optimize = 2
guest_chair_B[0].position = [3.1500000953674316, 1.75, 0.41999998688697815]
guest_chair_B[0].rotation = [0, 0, 0.0157079639172164]
guest_chair_B[0].optimize = 2
floor_lamp_B[0].position = [2.450000047683716, 2.8399999141693115, 0.824999988079071]
floor_lamp_B[0].rotation = [0, 0, -1.5707976269959776]
floor_lamp_B[0].optimize = 2
storage_box_A[0].position = [0.550000011920929, 2.7249999046325684, 2.1600000858306885]
storage_box_A[0].rotation = [0, 0, -1.570796267688273]
storage_box_A[0].optimize = 2
meeting_chair[0].position = [1.5499999523162842, 0.75, 0.4099999964237213]
meeting_chair[0].rotation = [0, 0, -0.0989856593889047]
meeting_chair[0].optimize = 2
low_credenza[0].position = [4.050000190734863, 0.22499996423721313, 0.375]
low_credenza[0].rotation = [0, 0, 1.57079636494684]
low_credenza[0].optimize = 2
waste_bin_B[0].position = [1.25, 1.649999976158142, 0.20999999344348907]
waste_bin_B[0].rotation = [0, 0, 0.00942477746072377]
waste_bin_B[0].optimize = 2

