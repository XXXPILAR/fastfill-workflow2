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
    Wall(corner1=[2.00, 2.00, 0.00], corner2=[2.00, 0.00, 0.00]),
    Wall(corner1=[2.00, 0.00, 0.00], corner2=[5.29, 0.00, 0.00]),
    Wall(corner1=[5.29, 0.00, 0.00], corner2=[5.28, 2.38, 0.00]),
    Wall(corner1=[5.28, 2.38, 0.00], corner2=[5.18, 2.93, 0.00]),
    Wall(corner1=[5.18, 2.93, 0.00], corner2=[4.87, 3.37, 0.00]),
    Wall(corner1=[4.87, 3.37, 0.00], corner2=[4.42, 3.67, 0.00]),
    Wall(corner1=[4.42, 3.67, 0.00], corner2=[3.88, 3.78, 0.00]),
    Wall(corner1=[3.88, 3.78, 0.00], corner2=[0.00, 3.79, 0.00]),
    Wall(corner1=[0.00, 3.79, 0.00], corner2=[0.00, 2.00, 0.00]),
    Wall(corner1=[0.00, 2.00, 0.00], corner2=[2.00, 2.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
chair_A = Assets(description="chair", size=[0.54, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
cup_A = Assets(description="cup", size=[0.08, 0.11, 0.10], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="table", size=[0.90, 1.80, 0.75], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.54, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="chair", size=[0.54, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
chair_D = Assets(description="chair", size=[0.54, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
utensil_A = Assets(description="utensil", size=[0.22, 0.03, 0.01], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="cabinet", size=[0.45, 1.40, 0.85], placements=[AssetInstance() for _ in range(1)])
utensil_B = Assets(description="utensil", size=[0.22, 0.03, 0.01], placements=[AssetInstance() for _ in range(1)])
chair_E = Assets(description="chair", size=[0.54, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="shelf", size=[0.25, 0.80, 0.04], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.25, 0.80, 0.04], placements=[AssetInstance() for _ in range(1)])
shelf_C = Assets(description="shelf", size=[0.25, 0.80, 0.04], placements=[AssetInstance() for _ in range(1)])
cup_B = Assets(description="cup", size=[0.08, 0.11, 0.10], placements=[AssetInstance() for _ in range(1)])
shelf_D = Assets(description="shelf", size=[0.25, 0.80, 0.04], placements=[AssetInstance() for _ in range(1)])
shelf_E = Assets(description="shelf", size=[0.25, 0.80, 0.04], placements=[AssetInstance() for _ in range(1)])
spoon = Assets(description="spoon", size=[0.20, 0.04, 0.02], placements=[AssetInstance() for _ in range(1)])

chair_A[0].instance_id = 'chair_A_0'
cup_A[0].instance_id = 'cup_A_0'
table[0].instance_id = 'table_0'
chair_B[0].instance_id = 'chair_B_0'
chair_C[0].instance_id = 'chair_C_0'
chair_D[0].instance_id = 'chair_D_0'
utensil_A[0].instance_id = 'utensil_A_0'
cabinet[0].instance_id = 'cabinet_0'
utensil_B[0].instance_id = 'utensil_B_0'
chair_E[0].instance_id = 'chair_E_0'
shelf_A[0].instance_id = 'shelf_A_0'
shelf_B[0].instance_id = 'shelf_B_0'
shelf_C[0].instance_id = 'shelf_C_0'
cup_B[0].instance_id = 'cup_B_0'
shelf_D[0].instance_id = 'shelf_D_0'
shelf_E[0].instance_id = 'shelf_E_0'
spoon[0].instance_id = 'spoon_0'
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

chair_A[0].position = [1.4974077554172496, 3.407838474661169, 0.45]
chair_A[0].rotation = [0, 0, 0]
cup_A[0].position = [1.883828144580373, 2.265222441469641, 0.05]
cup_A[0].rotation = [0, 0, 0]
table[0].position = [3.2841182925771424, 3.575982587516019, 0.375]
table[0].rotation = [0, 0, 0]
chair_B[0].position = [3.583790994387155, 0.11691556288425661, 0.45]
chair_B[0].rotation = [0, 0, 0]
chair_C[0].position = [4.593988673333197, 1.544183136880017, 0.45]
chair_C[0].rotation = [0, 0, 0]
chair_D[0].position = [3.945653973618893, 1.8283195042590739, 0.45]
chair_D[0].rotation = [0, 0, 0]
utensil_A[0].position = [0.6271325279225808, 2.9902998204706637, 0.0075]
utensil_A[0].rotation = [0, 0, 0]
cabinet[0].position = [2.0339976352648703, 3.350369519113935, 0.425]
cabinet[0].rotation = [0, 0, 0]
utensil_B[0].position = [2.7474615225362546, 0.06580062444255308, 0.0075]
utensil_B[0].rotation = [0, 0, 0]
chair_E[0].position = [3.6655560292739855, 1.4653810834373544, 0.45]
chair_E[0].rotation = [0, 0, 0]
shelf_A[0].position = [3.5332209169937094, 3.1732559542880456, 0.02]
shelf_A[0].rotation = [0, 0, 0]
shelf_B[0].position = [2.8380379484861087, 3.4850093892858314, 0.02]
shelf_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [3.995145649931588, 0.12896564007056988, 0.02]
shelf_C[0].rotation = [0, 0, 0]
cup_B[0].position = [2.7939145968169052, 1.4901953313646796, 0.05]
cup_B[0].rotation = [0, 0, 0]
shelf_D[0].position = [4.946880720229968, 0.2017999818739319, 0.02]
shelf_D[0].rotation = [0, 0, 0]
shelf_E[0].position = [5.255769316177802, 1.941998046758266, 0.02]
shelf_E[0].rotation = [0, 0, 0]
spoon[0].position = [4.391055294838303, 1.3171640567679601, 0.01]
spoon[0].rotation = [0, 0, 0]
chair_A[0].position = [1.4974077554172496, 3.407838474661169, 0.45]
chair_A[0].rotation = [0, 0, 0]
cup_A[0].position = [1.883828144580373, 2.265222441469641, 0.05]
cup_A[0].rotation = [0, 0, 0]
table[0].position = [3.2841182925771424, 3.575982587516019, 0.375]
table[0].rotation = [0, 0, 0]
chair_B[0].position = [3.583790994387155, 0.11691556288425661, 0.45]
chair_B[0].rotation = [0, 0, 0]
chair_C[0].position = [4.593988673333197, 1.544183136880017, 0.45]
chair_C[0].rotation = [0, 0, 0]
chair_D[0].position = [3.945653973618893, 1.8283195042590739, 0.45]
chair_D[0].rotation = [0, 0, 0]
utensil_A[0].position = [0.6271325279225808, 2.9902998204706637, 0.0075]
utensil_A[0].rotation = [0, 0, 0]
cabinet[0].position = [2.0339976352648703, 3.350369519113935, 0.425]
cabinet[0].rotation = [0, 0, 0]
utensil_B[0].position = [2.7474615225362546, 0.06580062444255308, 0.0075]
utensil_B[0].rotation = [0, 0, 0]
chair_E[0].position = [3.6655560292739855, 1.4653810834373544, 0.45]
chair_E[0].rotation = [0, 0, 0]
shelf_A[0].position = [3.5332209169937094, 3.1732559542880456, 0.02]
shelf_A[0].rotation = [0, 0, 0]
shelf_B[0].position = [2.8380379484861087, 3.4850093892858314, 0.02]
shelf_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [3.995145649931588, 0.12896564007056988, 0.02]
shelf_C[0].rotation = [0, 0, 0]
cup_B[0].position = [2.7939145968169052, 1.4901953313646796, 0.05]
cup_B[0].rotation = [0, 0, 0]
shelf_D[0].position = [4.946880720229968, 0.2017999818739319, 0.02]
shelf_D[0].rotation = [0, 0, 0]
shelf_E[0].position = [5.255769316177802, 1.941998046758266, 0.02]
shelf_E[0].rotation = [0, 0, 0]
spoon[0].position = [4.391055294838303, 1.3171640567679601, 0.01]
spoon[0].rotation = [0, 0, 0]

solver.constraints = []

# Dining zone: leave the west entrance alcove and the strip beside the east
# doorway free. The table's long axis runs north–south.
table[0].position = [3.45, 1.95, 0.375]
table[0].rotation = [0, 0, 0]

table_anchor = AssetInstance(position=[3.45, 1.95, 0.375])
solver.distance_constraint(table[0], table_anchor, 0, 0, weight=10)
solver.align_with(table[0], table_anchor)

# Two chairs on each long side, plus one at the north end.
# chair_D and chair_E oppose one another with the table between them.
seat_layout = [
    (chair_A, [2.62, 1.45, 0.45], 0,   [3.45, 1.45, 0.45]),
    (chair_B, [4.28, 1.45, 0.45], 180, [3.45, 1.45, 0.45]),
    (chair_C, [3.45, 3.27, 0.45], 270, [3.45, 1.95, 0.45]),
    (chair_D, [2.62, 2.35, 0.45], 0,   [3.45, 2.35, 0.45]),
    (chair_E, [4.28, 2.35, 0.45], 180, [3.45, 2.35, 0.45]),
]

for seat_asset, seat_position, seat_angle, facing_position in seat_layout:
    seat_asset[0].position = seat_position
    seat_asset[0].rotation = [0, 0, radians(seat_angle)]

    # Fixed station anchors preserve the seating arrangement without
    # turning side chairs diagonally toward the table's center.
    solver.distance_constraint(
        seat_asset[0], AssetInstance(position=seat_position),
        0, 0, weight=10
    )
    solver.point_towards(
        seat_asset[0], AssetInstance(position=facing_position)
    )
    seat_distance = sum(
        (seat_position[i] - table[0].position[i]) ** 2
        for i in range(3)
    ) ** 0.5
    solver.distance_constraint(
        seat_asset[0], table[0],
        seat_distance - 0.03, seat_distance + 0.03
    )

solver.align_with(chair_E[0], chair_D[0], angle=180)
solver.distance_constraint(chair_E[0], chair_D[0], 1.66, 1.66)

# Rotate the cabinet so its broad dimension follows the south wall.
# Its front faces into the room, and its footprint ends well before the table.
cabinet[0].position = [3.35, 0.225, 0.425]
cabinet[0].rotation = [0, 0, radians(90)]

cabinet_anchor = AssetInstance(
    position=[3.35, 0.225, 0.425],
    rotation=[0, 0, radians(90)]
)
solver.distance_constraint(cabinet[0], cabinet_anchor, 0, 0, weight=10)
solver.against_wall(cabinet[0], walls[1])
solver.align_with(cabinet[0], cabinet_anchor)

# These are wall-mounted shelves, not floor-standing objects.
# Stack them vertically above the cabinet, clear of both windows.
# The wall provides their support; they should not sit on the cabinet.
shelf_layout = [
    (shelf_A, 1.20),
    (shelf_B, 1.50),
    (shelf_C, 1.80),
    (shelf_D, 2.10),
    (shelf_E, 2.40),
]

for shelf_asset, shelf_height in shelf_layout:
    shelf_asset[0].position = [3.35, 0.125, shelf_height]
    shelf_asset[0].rotation = [0, 0, radians(90)]
    solver.distance_constraint(
        shelf_asset[0],
        AssetInstance(position=[3.35, 0.125, shelf_height]),
        0, 0, weight=10
    )
    solver.against_wall(shelf_asset[0], walls[1])
    solver.align_with(shelf_asset[0], cabinet[0])

# Place tableware on the tabletop, keeping each footprint separate.
# Heights equal the table's top (0.75 m) plus half the object's height.
tableware_layout = [
    (cup_A,     [3.25, 1.35, 0.800], 0),
    (cup_B,     [3.65, 2.45, 0.800], 180),
    (utensil_A, [3.25, 1.65, 0.755], 0),
    (utensil_B, [3.65, 2.15, 0.755], 180),
    (spoon,     [3.45, 2.65, 0.760], 90),
]

for tabletop_asset, item_position, item_angle in tableware_layout:
    tabletop_asset[0].position = item_position
    tabletop_asset[0].rotation = [0, 0, radians(item_angle)]

    solver.on_top_of(tabletop_asset[0], table[0])
    solver.distance_constraint(
        tabletop_asset[0],
        AssetInstance(position=item_position),
        0, 0, weight=10
    )
    solver.align_with(tabletop_asset[0], table[0], angle=item_angle)

    # Also retain the object's intended distance from the table center.
    item_distance = sum(
        (item_position[i] - table[0].position[i]) ** 2
        for i in range(3)
    ) ** 0.5
    solver.distance_constraint(
        tabletop_asset[0], table[0],
        item_distance - 0.02, item_distance + 0.02
    )

solver.constraints = []
cabinet[0].position = [3.3499999046325684, 0.22701792418956757, 0.42500001192092896]
cabinet[0].rotation = [0, 0, 1.5683937089612758]
cabinet[0].optimize = 2
chair_C[0].position = [3.450000047683716, 3.2699999809265137, 0.44999998807907104]
chair_C[0].rotation = [0, 0, -1.5582299555380688]
chair_C[0].optimize = 2
utensil_A[0].position = [3.0606179237365723, 1.4615477323532104, 0.7549999952316284]
utensil_A[0].rotation = [0, 0, 0.06996682417229133]
utensil_A[0].optimize = 2
shelf_E[0].position = [3.3499999046325684, 0.12573984265327454, 0.019999999552965164]
shelf_E[0].rotation = [0, 0, 1.5690213054452857]
shelf_E[0].optimize = 2
table[0].position = [3.450000047683716, 1.9500000476837158, 0.375]
table[0].rotation = [0, 0, 0.0722566305613884]
table[0].optimize = 2
shelf_B[0].position = [3.3499999046325684, 0.12573984265327454, 0.019999999552965164]
shelf_B[0].rotation = [0, 0, 1.5690213054452857]
shelf_B[0].optimize = 2
cup_A[0].position = [3.169127941131592, 1.261443018913269, 0.800000011920929]
cup_A[0].rotation = [0, 0, 0.06996682417229133]
cup_A[0].optimize = 2
shelf_D[0].position = [3.3499999046325684, 0.12573984265327454, 0.019999999552965164]
shelf_D[0].rotation = [0, 0, 1.5690213054452857]
shelf_D[0].optimize = 2
chair_E[0].position = [4.28000020980835, 2.3499999046325684, 0.44999998807907104]
chair_E[0].rotation = [0, 0, -3.122522226256183]
chair_E[0].optimize = 2
utensil_B[0].position = [3.8676884174346924, 2.3676884174346924, 0.7549999952316284]
utensil_B[0].rotation = [0, 0, -3.07162580722932]
utensil_B[0].optimize = 2
shelf_C[0].position = [3.3499999046325684, 0.12573984265327454, 0.019999999552965164]
shelf_C[0].rotation = [0, 0, 1.5690213054452857]
shelf_C[0].optimize = 2
shelf_A[0].position = [3.3499999046325684, 0.12573984265327454, 0.019999999552965164]
shelf_A[0].rotation = [0, 0, 1.5690213054452857]
shelf_A[0].optimize = 2
chair_B[0].position = [4.28000020980835, 1.4500000476837158, 0.44999998807907104]
chair_B[0].rotation = [0, 0, -3.1290262823329655]
chair_B[0].optimize = 2
chair_D[0].position = [2.619999885559082, 2.3499999046325684, 0.44999998807907104]
chair_D[0].rotation = [0, 0, 0.01884955539881635]
chair_D[0].optimize = 2
cup_B[0].position = [3.77571964263916, 2.580626964569092, 0.800000011920929]
cup_B[0].rotation = [0, 0, -3.07162580722932]
cup_B[0].optimize = 2
chair_A[0].position = [2.619999885559082, 1.4500000476837158, 0.44999998807907104]
chair_A[0].rotation = [0, 0, 0.01256637125682779]
chair_A[0].optimize = 2
spoon[0].position = [3.450000047683716, 2.741502285003662, 0.7599999904632568]
spoon[0].rotation = [0, 0, 1.6407631666564497]
spoon[0].optimize = 2

