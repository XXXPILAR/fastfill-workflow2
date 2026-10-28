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
    Wall(corner1=[0.00, 2.00, 0.00], corner2=[1.00, 2.00, 0.00]),
    Wall(corner1=[1.00, 2.00, 0.00], corner2=[1.00, 0.00, 0.00]),
    Wall(corner1=[1.00, 0.00, 0.00], corner2=[3.00, 0.00, 0.00]),
    Wall(corner1=[3.00, 0.00, 0.00], corner2=[3.00, 5.00, 0.00]),
    Wall(corner1=[3.00, 5.00, 0.00], corner2=[0.00, 5.00, 0.00]),
    Wall(corner1=[0.00, 5.00, 0.00], corner2=[0.00, 2.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
wall_cabinet_A = Assets(description="I brown cabinet with two doors.", size=[0.35, 0.90, 0.70], placements=[AssetInstance() for _ in range(1)])
tall_storage_cabinet_A = Assets(description="A blue cabinet with two big doors.", size=[0.50, 0.90, 1.90], placements=[AssetInstance() for _ in range(1)])
lab_workbench = Assets(description="a laboratory desk with a microscope and drawers.", size=[0.75, 1.50, 0.90], placements=[AssetInstance() for _ in range(1)])
tall_storage_cabinet_B = Assets(description="A blue cabinet with two big doors.", size=[0.50, 0.90, 1.90], placements=[AssetInstance() for _ in range(1)])
wall_shelf_A = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.25, 1.00, 0.25], placements=[AssetInstance() for _ in range(1)])
wall_cabinet_B = Assets(description="I brown cabinet with two doors.", size=[0.35, 0.90, 0.70], placements=[AssetInstance() for _ in range(1)])
support_desk = Assets(description="A little desk with a black computer monitor on top.", size=[0.60, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
archive_box_A = Assets(description="A dark brown loaf of bread with each side neatly sliced.", size=[0.30, 0.40, 0.25], placements=[AssetInstance() for _ in range(1)])
desk_lamp = Assets(description="A desk lamp with a purple base and coral arm and head.", size=[0.35, 0.25, 0.50], placements=[AssetInstance() for _ in range(1)])
wall_shelf_B = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.25, 1.00, 0.25], placements=[AssetInstance() for _ in range(1)])
wall_whiteboard = Assets(description="A white rectangular poster with black blue and orange marks and irregular writing.", size=[0.04, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
support_chair = Assets(description="support chair", size=[0.55, 0.55, 0.90], placements=[AssetInstance() for _ in range(1)])
mobile_lab_cart = Assets(description="Gray cart with wheels and three shelves.", size=[0.45, 0.75, 0.90], placements=[AssetInstance() for _ in range(1)])
archive_box_B = Assets(description="A dark brown loaf of bread with each side neatly sliced.", size=[0.30, 0.40, 0.25], placements=[AssetInstance() for _ in range(1)])

wall_cabinet_A[0].instance_id = 'wall_cabinet_A_0'
tall_storage_cabinet_A[0].instance_id = 'tall_storage_cabinet_A_0'
lab_workbench[0].instance_id = 'lab_workbench_0'
tall_storage_cabinet_B[0].instance_id = 'tall_storage_cabinet_B_0'
wall_shelf_A[0].instance_id = 'wall_shelf_A_0'
wall_cabinet_B[0].instance_id = 'wall_cabinet_B_0'
support_desk[0].instance_id = 'support_desk_0'
archive_box_A[0].instance_id = 'archive_box_A_0'
desk_lamp[0].instance_id = 'desk_lamp_0'
wall_shelf_B[0].instance_id = 'wall_shelf_B_0'
wall_whiteboard[0].instance_id = 'wall_whiteboard_0'
support_chair[0].instance_id = 'support_chair_0'
mobile_lab_cart[0].instance_id = 'mobile_lab_cart_0'
archive_box_B[0].instance_id = 'archive_box_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

wall_cabinet_A[0].position = [2.599338204381994, 1.7220658977290748, 0.35]
wall_cabinet_A[0].rotation = [0, 0, 0]
tall_storage_cabinet_A[0].position = [0.9531409475947565, 4.799034644720635, 0.95]
tall_storage_cabinet_A[0].rotation = [0, 0, 0]
lab_workbench[0].position = [2.0162771318941393, 4.881829410231303, 0.45]
lab_workbench[0].rotation = [0, 0, 0]
tall_storage_cabinet_B[0].position = [2.176106161453896, 3.952149379080706, 0.95]
tall_storage_cabinet_B[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [2.7417375172821026, 0.9254166098223815, 0.125]
wall_shelf_A[0].rotation = [0, 0, 0]
wall_cabinet_B[0].position = [2.8023273736167607, 0.821144839971279, 0.35]
wall_cabinet_B[0].rotation = [0, 0, 0]
support_desk[0].position = [2.881791319865161, 2.2012497605924426, 0.375]
support_desk[0].rotation = [0, 0, 0]
archive_box_A[0].position = [0.8122851815291041, 2.6755391878159056, 0.125]
archive_box_A[0].rotation = [0, 0, 0]
desk_lamp[0].position = [1.564872907966127, 2.4432477456167803, 0.25]
desk_lamp[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [1.0822445750579623, 2.14767500490102, 0.125]
wall_shelf_B[0].rotation = [0, 0, 0]
wall_whiteboard[0].position = [1.7230312789136977, 2.1979675898728734, 0.45]
wall_whiteboard[0].rotation = [0, 0, 0]
support_chair[0].position = [0.25535220418128035, 3.824111326172357, 0.45]
support_chair[0].rotation = [0, 0, 0]
mobile_lab_cart[0].position = [1.2951600475187082, 3.9040756016698825, 0.45]
mobile_lab_cart[0].rotation = [0, 0, 0]
archive_box_B[0].position = [0.7039705527089068, 3.8125083142517306, 0.125]
archive_box_B[0].rotation = [0, 0, 0]
wall_cabinet_A[0].position = [2.599338204381994, 1.7220658977290748, 0.35]
wall_cabinet_A[0].rotation = [0, 0, 0]
tall_storage_cabinet_A[0].position = [0.9531409475947565, 4.799034644720635, 0.95]
tall_storage_cabinet_A[0].rotation = [0, 0, 0]
lab_workbench[0].position = [2.0162771318941393, 4.881829410231303, 0.45]
lab_workbench[0].rotation = [0, 0, 0]
tall_storage_cabinet_B[0].position = [2.176106161453896, 3.952149379080706, 0.95]
tall_storage_cabinet_B[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [2.7417375172821026, 0.9254166098223815, 0.125]
wall_shelf_A[0].rotation = [0, 0, 0]
wall_cabinet_B[0].position = [2.8023273736167607, 0.821144839971279, 0.35]
wall_cabinet_B[0].rotation = [0, 0, 0]
support_desk[0].position = [2.881791319865161, 2.2012497605924426, 0.375]
support_desk[0].rotation = [0, 0, 0]
archive_box_A[0].position = [0.8122851815291041, 2.6755391878159056, 0.125]
archive_box_A[0].rotation = [0, 0, 0]
desk_lamp[0].position = [1.564872907966127, 2.4432477456167803, 0.25]
desk_lamp[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [1.0822445750579623, 2.14767500490102, 0.125]
wall_shelf_B[0].rotation = [0, 0, 0]
wall_whiteboard[0].position = [1.7230312789136977, 2.1979675898728734, 0.45]
wall_whiteboard[0].rotation = [0, 0, 0]
support_chair[0].position = [0.25535220418128035, 3.824111326172357, 0.45]
support_chair[0].rotation = [0, 0, 0]
mobile_lab_cart[0].position = [1.2951600475187082, 3.9040756016698825, 0.45]
mobile_lab_cart[0].rotation = [0, 0, 0]
archive_box_B[0].position = [0.7039705527089068, 3.8125083142517306, 0.125]
archive_box_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed orientation references keep wall-backed objects facing into the room.
face_pos_x = AssetInstance(rotation=[0, 0, radians(0)])
face_pos_y = AssetInstance(rotation=[0, 0, radians(90)])
face_neg_x = AssetInstance(rotation=[0, 0, radians(180)])
face_neg_y = AssetInstance(rotation=[0, 0, radians(-90)])

# Place the two tall cabinets along the north wall. The left cabinet is
# shifted away from the doorway's approach path.
tall_storage_cabinet_A[0].position = [1.25, 4.75, 0.95]
tall_storage_cabinet_A[0].rotation = [0, 0, radians(-90)]

tall_storage_cabinet_B[0].position = [2.45, 4.75, 0.95]
tall_storage_cabinet_B[0].rotation = [0, 0, radians(-90)]

# Put each archive box on its corresponding tall cabinet. In particular,
# archive_box_B (o0013) is on tall_storage_cabinet_B (o0003).
archive_box_A[0].position = [1.25, 4.75, 2.025]
archive_box_A[0].rotation = [0, 0, radians(-90)]

archive_box_B[0].position = [2.45, 4.75, 2.025]
archive_box_B[0].rotation = [0, 0, radians(-90)]

# The workbench occupies the bottom wall of the narrow lower portion,
# leaving the upper room and doorway circulation open.
lab_workbench[0].position = [1.75, 0.375, 0.45]
lab_workbench[0].rotation = [0, 0, radians(90)]

# The lamp sits on the workbench, offset toward its left side.
desk_lamp[0].position = [1.50, 0.35, 1.15]
desk_lamp[0].rotation = [0, 0, radians(90)]

# Arrange the support station across the lower part of the main room.
# The support desk faces east directly toward the mobile laboratory cart.
support_desk[0].position = [0.30, 2.85, 0.375]
support_desk[0].rotation = [0, 0, radians(0)]

support_chair[0].position = [1.00, 2.85, 0.45]
support_chair[0].rotation = [0, 0, radians(180)]

mobile_lab_cart[0].position = [1.75, 2.85, 0.45]
mobile_lab_cart[0].rotation = [0, 0, radians(180)]

# Wall-mounted storage uses the left and inner walls. These placements stay
# below the doorway opening and do not cover either window on the east wall.
wall_cabinet_A[0].position = [0.175, 2.60, 1.45]
wall_cabinet_A[0].rotation = [0, 0, radians(0)]

wall_shelf_A[0].position = [1.125, 0.50, 1.45]
wall_shelf_A[0].rotation = [0, 0, radians(0)]

wall_cabinet_B[0].position = [1.175, 1.45, 1.45]
wall_cabinet_B[0].rotation = [0, 0, radians(0)]

# This shelf is mounted above the workbench along the bottom wall.
wall_shelf_B[0].position = [2.50, 0.125, 1.50]
wall_shelf_B[0].rotation = [0, 0, radians(90)]

# The whiteboard fits in the clear east-wall section between the two windows.
wall_whiteboard[0].position = [2.98, 2.25, 1.50]
wall_whiteboard[0].rotation = [0, 0, radians(180)]


# Supporting-surface constraints are the highest-priority constraints for
# the small objects.
solver.on_top_of(archive_box_A[0], tall_storage_cabinet_A[0])
solver.on_top_of(archive_box_B[0], tall_storage_cabinet_B[0])
solver.on_top_of(desk_lamp[0], lab_workbench[0])

# Required semantic relationship: the support desk faces the mobile cart.
solver.point_towards(support_desk[0], mobile_lab_cart[0])
solver.point_towards(mobile_lab_cart[0], support_desk[0])
solver.point_towards(support_chair[0], support_desk[0])

# Keep floor and wall-mounted furniture attached to their intended walls.
solver.against_wall(tall_storage_cabinet_A[0], walls[4])
solver.against_wall(tall_storage_cabinet_B[0], walls[4])
solver.against_wall(lab_workbench[0], walls[2])
solver.against_wall(support_desk[0], walls[5])
solver.against_wall(wall_cabinet_A[0], walls[5])
solver.against_wall(wall_shelf_A[0], walls[1])
solver.against_wall(wall_cabinet_B[0], walls[1])
solver.against_wall(wall_shelf_B[0], walls[2])
solver.against_wall(wall_whiteboard[0], walls[3])

# Orientation constraints preserve inward-facing fronts after adjustment.
solver.align_with(tall_storage_cabinet_A[0], face_neg_y)
solver.align_with(tall_storage_cabinet_B[0], face_neg_y)
solver.align_with(lab_workbench[0], face_pos_y)
solver.align_with(wall_cabinet_A[0], face_pos_x)
solver.align_with(wall_shelf_A[0], face_pos_x)
solver.align_with(wall_cabinet_B[0], face_pos_x)
solver.align_with(wall_shelf_B[0], face_pos_y)
solver.align_with(wall_whiteboard[0], face_neg_x)
solver.align_with(archive_box_A[0], tall_storage_cabinet_A[0])
solver.align_with(archive_box_B[0], tall_storage_cabinet_B[0])
solver.align_with(desk_lamp[0], lab_workbench[0])

# Exact anchors provide a position-based constraint for every asset while
# retaining the explicitly planned clearances from the door and windows.
solver.distance_constraint(
    tall_storage_cabinet_A[0],
    AssetInstance(position=[1.25, 4.75, 0.95]),
    0, 0, weight=10
)
solver.distance_constraint(
    tall_storage_cabinet_B[0],
    AssetInstance(position=[2.45, 4.75, 0.95]),
    0, 0, weight=10
)
solver.distance_constraint(
    archive_box_A[0],
    AssetInstance(position=[1.25, 4.75, 2.025]),
    0, 0, weight=10
)
solver.distance_constraint(
    archive_box_B[0],
    AssetInstance(position=[2.45, 4.75, 2.025]),
    0, 0, weight=10
)
solver.distance_constraint(
    lab_workbench[0],
    AssetInstance(position=[1.75, 0.375, 0.45]),
    0, 0, weight=10
)
solver.distance_constraint(
    desk_lamp[0],
    AssetInstance(position=[1.50, 0.35, 1.15]),
    0, 0, weight=10
)
solver.distance_constraint(
    support_desk[0],
    AssetInstance(position=[0.30, 2.85, 0.375]),
    0, 0, weight=10
)
solver.distance_constraint(
    support_chair[0],
    AssetInstance(position=[1.00, 2.85, 0.45]),
    0, 0, weight=10
)
solver.distance_constraint(
    mobile_lab_cart[0],
    AssetInstance(position=[1.75, 2.85, 0.45]),
    0, 0, weight=10
)
solver.distance_constraint(
    wall_cabinet_A[0],
    AssetInstance(position=[0.175, 2.60, 1.45]),
    0, 0, weight=10
)
solver.distance_constraint(
    wall_shelf_A[0],
    AssetInstance(position=[1.125, 0.50, 1.45]),
    0, 0, weight=10
)
solver.distance_constraint(
    wall_cabinet_B[0],
    AssetInstance(position=[1.175, 1.45, 1.45]),
    0, 0, weight=10
)
solver.distance_constraint(
    wall_shelf_B[0],
    AssetInstance(position=[2.50, 0.125, 1.50]),
    0, 0, weight=10
)
solver.distance_constraint(
    wall_whiteboard[0],
    AssetInstance(position=[2.98, 2.25, 1.50]),
    0, 0, weight=10
)

# Maintain the functional spacing of the support station if adjustments are
# needed: the chair remains between the desk and cart without touching either.
solver.distance_constraint(
    support_chair[0], support_desk[0],
    0.65, 0.80, weight=10
)
solver.distance_constraint(
    support_chair[0], mobile_lab_cart[0],
    0.65, 0.85, weight=10
)
solver.distance_constraint(
    mobile_lab_cart[0], support_desk[0],
    1.35, 1.55, weight=10
)

solver.constraints = []
tall_storage_cabinet_A[0].position = [1.25, 4.736996173858643, 0.949999988079071]
tall_storage_cabinet_A[0].rotation = [0, 0, -1.5416595099802253]
tall_storage_cabinet_A[0].optimize = 2
tall_storage_cabinet_B[0].position = [2.450000047683716, 4.746066570281982, 0.949999988079071]
tall_storage_cabinet_B[0].rotation = [0, 0, -1.5620341067611838]
tall_storage_cabinet_B[0].optimize = 2
lab_workbench[0].position = [1.75, 0.3790699243545532, 0.44999998807907104]
lab_workbench[0].rotation = [0, 0, 1.579558538192457]
lab_workbench[0].optimize = 2
desk_lamp[0].position = [1.5, 0.3499999940395355, 1.149999976158142]
desk_lamp[0].rotation = [0, 0, 1.5935836929706761]
desk_lamp[0].optimize = 2
wall_cabinet_B[0].position = [1.176142930984497, 1.4500000476837158, 0.3499999940395355]
wall_cabinet_B[0].rotation = [0, 0, 0.0025409150842135757]
wall_cabinet_B[0].optimize = 2
support_chair[0].position = [1.0, 2.8499999046325684, 0.44999998807907104]
support_chair[0].rotation = [0, 0, -3.125884689672577]
support_chair[0].optimize = 2
wall_whiteboard[0].position = [2.978475570678711, 2.25, 0.44999998807907104]
wall_whiteboard[0].rotation = [0, 0, -3.1390517430940474]
wall_whiteboard[0].optimize = 2
archive_box_A[0].position = [1.25, 4.75, 2.0250000953674316]
archive_box_A[0].rotation = [0, 0, -1.548008960619117]
archive_box_A[0].optimize = 2
wall_shelf_B[0].position = [2.4900033473968506, 0.12627005577087402, 0.125]
wall_shelf_B[0].rotation = [0, 0, 1.5733372415791846]
wall_shelf_B[0].optimize = 2
archive_box_B[0].position = [2.450000047683716, 4.75, 2.0250000953674316]
archive_box_B[0].rotation = [0, 0, -1.548008960619117]
archive_box_B[0].optimize = 2
mobile_lab_cart[0].position = [1.75, 2.8499999046325684, 0.44999998807907104]
mobile_lab_cart[0].rotation = [0, 0, -3.122743098190977]
mobile_lab_cart[0].optimize = 2
wall_cabinet_A[0].position = [0.1761428564786911, 2.5999999046325684, 0.3499999940395355]
wall_cabinet_A[0].rotation = [0, 0, 0.0025409160063866866]
wall_cabinet_A[0].optimize = 2
support_desk[0].position = [0.3049834966659546, 2.8499999046325684, 0.375]
support_desk[0].rotation = [0, 0, 0.01498391146254813]
support_desk[0].optimize = 2
wall_shelf_A[0].position = [1.126270055770874, 0.5099967122077942, 0.125]
wall_shelf_A[0].rotation = [0, 0, 0.002540913862115027]
wall_shelf_A[0].optimize = 2

