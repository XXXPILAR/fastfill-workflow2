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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.90, 0.00, 0.00]),
    Wall(corner1=[2.90, 0.00, 0.00], corner2=[2.90, 3.30, 0.00]),
    Wall(corner1=[2.90, 3.30, 0.00], corner2=[0.00, 3.30, 0.00]),
    Wall(corner1=[0.00, 3.30, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
photograph_print_A = Assets(description="photograph print", size=[0.01, 0.30, 0.20], placements=[AssetInstance() for _ in range(1)])
spiral_bound_notebook_A = Assets(description="spiral bound notebook", size=[0.30, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
world_map_print = Assets(description="world map print", size=[0.01, 0.90, 0.60], placements=[AssetInstance() for _ in range(1)])
side_chair = Assets(description="side chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
desk = Assets(description="desk", size=[0.70, 1.40, 0.75], placements=[AssetInstance() for _ in range(1)])
pen_cup_A = Assets(description="pen cup", size=[0.08, 0.08, 0.10], placements=[AssetInstance() for _ in range(1)])
pen_cup_B = Assets(description="pen cup", size=[0.08, 0.08, 0.10], placements=[AssetInstance() for _ in range(1)])
drink_coaster = Assets(description="drink coaster", size=[0.10, 0.10, 0.01], placements=[AssetInstance() for _ in range(1)])
photograph_print_B = Assets(description="photograph print", size=[0.01, 0.20, 0.25], placements=[AssetInstance() for _ in range(1)])
filing_pedestal = Assets(description="filing pedestal", size=[0.50, 0.40, 0.60], placements=[AssetInstance() for _ in range(1)])
task_chair = Assets(description="task chair", size=[0.65, 0.65, 1.10], placements=[AssetInstance() for _ in range(1)])
whiteboard = Assets(description="whiteboard", size=[0.50, 0.90, 1.70], placements=[AssetInstance() for _ in range(1)])
ballpoint_pen_A = Assets(description="ballpoint pen", size=[0.14, 0.01, 0.01], placements=[AssetInstance() for _ in range(1)])
laptop_computer = Assets(description="laptop computer", size=[0.24, 0.33, 0.23], placements=[AssetInstance() for _ in range(1)])
clock = Assets(description="clock", size=[0.04, 0.30, 0.30], placements=[AssetInstance() for _ in range(1)])
coffee_mug = Assets(description="coffee mug", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
spiral_bound_notebook_B = Assets(description="spiral bound notebook", size=[0.21, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
ballpoint_pen_B = Assets(description="ballpoint pen", size=[0.14, 0.01, 0.01], placements=[AssetInstance() for _ in range(1)])
wireless_mouse = Assets(description="wireless mouse", size=[0.11, 0.07, 0.04], placements=[AssetInstance() for _ in range(1)])
art_print = Assets(description="art print", size=[0.02, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
floor_lamp = Assets(description="floor lamp", size=[0.30, 0.30, 1.65], placements=[AssetInstance() for _ in range(1)])

photograph_print_A[0].instance_id = 'photograph_print_A_0'
spiral_bound_notebook_A[0].instance_id = 'spiral_bound_notebook_A_0'
world_map_print[0].instance_id = 'world_map_print_0'
side_chair[0].instance_id = 'side_chair_0'
desk[0].instance_id = 'desk_0'
pen_cup_A[0].instance_id = 'pen_cup_A_0'
pen_cup_B[0].instance_id = 'pen_cup_B_0'
drink_coaster[0].instance_id = 'drink_coaster_0'
photograph_print_B[0].instance_id = 'photograph_print_B_0'
filing_pedestal[0].instance_id = 'filing_pedestal_0'
task_chair[0].instance_id = 'task_chair_0'
whiteboard[0].instance_id = 'whiteboard_0'
ballpoint_pen_A[0].instance_id = 'ballpoint_pen_A_0'
laptop_computer[0].instance_id = 'laptop_computer_0'
clock[0].instance_id = 'clock_0'
coffee_mug[0].instance_id = 'coffee_mug_0'
spiral_bound_notebook_B[0].instance_id = 'spiral_bound_notebook_B_0'
ballpoint_pen_B[0].instance_id = 'ballpoint_pen_B_0'
wireless_mouse[0].instance_id = 'wireless_mouse_0'
art_print[0].instance_id = 'art_print_0'
floor_lamp[0].instance_id = 'floor_lamp_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

photograph_print_A[0].position = [1.9338159533434789, 2.3716395299041255, 0.1]
photograph_print_A[0].rotation = [0, 0, 0]
spiral_bound_notebook_A[0].position = [0.5033235029947208, 2.2198250268450717, 0.0075]
spiral_bound_notebook_A[0].rotation = [0, 0, 0]
world_map_print[0].position = [1.4713026331065875, 2.01743191695503, 0.3]
world_map_print[0].rotation = [0, 0, 0]
side_chair[0].position = [2.6390843983939596, 2.0549593381412334, 0.41]
side_chair[0].rotation = [0, 0, 0]
desk[0].position = [2.5134921991480375, 0.09194227520953943, 0.375]
desk[0].rotation = [0, 0, 0]
pen_cup_A[0].position = [1.727377360630664, 1.0293876676676985, 0.05]
pen_cup_A[0].rotation = [0, 0, 0]
pen_cup_B[0].position = [0.5411503575618271, 0.04021779263574724, 0.05]
pen_cup_B[0].rotation = [0, 0, 0]
drink_coaster[0].position = [0.022453626437984552, 0.3405625678862738, 0.0025]
drink_coaster[0].rotation = [0, 0, 0]
photograph_print_B[0].position = [1.9195826099856614, 2.294496414489041, 0.125]
photograph_print_B[0].rotation = [0, 0, 0]
filing_pedestal[0].position = [0.4972556410933297, 2.1807193208137714, 0.3]
filing_pedestal[0].rotation = [0, 0, 0]
task_chair[0].position = [2.2672233403975306, 2.820561559576566, 0.55]
task_chair[0].rotation = [0, 0, 0]
whiteboard[0].position = [2.4863594059785603, 1.4523146635371738, 0.85]
whiteboard[0].rotation = [0, 0, 0]
ballpoint_pen_A[0].position = [1.1201887187558222, 1.0177762503186143, 0.005]
ballpoint_pen_A[0].rotation = [0, 0, 0]
laptop_computer[0].position = [2.685385943589032, 2.4318450352080196, 0.115]
laptop_computer[0].rotation = [0, 0, 0]
clock[0].position = [2.6030741722283874, 0.5721063768206525, 0.15]
clock[0].rotation = [0, 0, 0]
coffee_mug[0].position = [0.09170907512380319, 1.683293056064086, 0.05]
coffee_mug[0].rotation = [0, 0, 0]
spiral_bound_notebook_B[0].position = [0.0908764554540546, 0.4353101120365592, 0.0075]
spiral_bound_notebook_B[0].rotation = [0, 0, 0]
ballpoint_pen_B[0].position = [0.6397445975317317, 0.08079547003821254, 0.005]
ballpoint_pen_B[0].rotation = [0, 0, 0]
wireless_mouse[0].position = [1.2771619970202082, 0.8607289709495961, 0.02]
wireless_mouse[0].rotation = [0, 0, 0]
art_print[0].position = [0.7060919200801924, 1.2908536302709055, 0.35]
art_print[0].rotation = [0, 0, 0]
floor_lamp[0].position = [1.6471854770236365, 2.9542730183182413, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
photograph_print_A[0].position = [1.9338159533434789, 2.3716395299041255, 0.1]
photograph_print_A[0].rotation = [0, 0, 0]
spiral_bound_notebook_A[0].position = [0.5033235029947208, 2.2198250268450717, 0.0075]
spiral_bound_notebook_A[0].rotation = [0, 0, 0]
world_map_print[0].position = [1.4713026331065875, 2.01743191695503, 0.3]
world_map_print[0].rotation = [0, 0, 0]
side_chair[0].position = [2.6390843983939596, 2.0549593381412334, 0.41]
side_chair[0].rotation = [0, 0, 0]
desk[0].position = [2.5134921991480375, 0.09194227520953943, 0.375]
desk[0].rotation = [0, 0, 0]
pen_cup_A[0].position = [1.727377360630664, 1.0293876676676985, 0.05]
pen_cup_A[0].rotation = [0, 0, 0]
pen_cup_B[0].position = [0.5411503575618271, 0.04021779263574724, 0.05]
pen_cup_B[0].rotation = [0, 0, 0]
drink_coaster[0].position = [0.022453626437984552, 0.3405625678862738, 0.0025]
drink_coaster[0].rotation = [0, 0, 0]
photograph_print_B[0].position = [1.9195826099856614, 2.294496414489041, 0.125]
photograph_print_B[0].rotation = [0, 0, 0]
filing_pedestal[0].position = [0.4972556410933297, 2.1807193208137714, 0.3]
filing_pedestal[0].rotation = [0, 0, 0]
task_chair[0].position = [2.2672233403975306, 2.820561559576566, 0.55]
task_chair[0].rotation = [0, 0, 0]
whiteboard[0].position = [2.4863594059785603, 1.4523146635371738, 0.85]
whiteboard[0].rotation = [0, 0, 0]
ballpoint_pen_A[0].position = [1.1201887187558222, 1.0177762503186143, 0.005]
ballpoint_pen_A[0].rotation = [0, 0, 0]
laptop_computer[0].position = [2.685385943589032, 2.4318450352080196, 0.115]
laptop_computer[0].rotation = [0, 0, 0]
clock[0].position = [2.6030741722283874, 0.5721063768206525, 0.15]
clock[0].rotation = [0, 0, 0]
coffee_mug[0].position = [0.09170907512380319, 1.683293056064086, 0.05]
coffee_mug[0].rotation = [0, 0, 0]
spiral_bound_notebook_B[0].position = [0.0908764554540546, 0.4353101120365592, 0.0075]
spiral_bound_notebook_B[0].rotation = [0, 0, 0]
ballpoint_pen_B[0].position = [0.6397445975317317, 0.08079547003821254, 0.005]
ballpoint_pen_B[0].rotation = [0, 0, 0]
wireless_mouse[0].position = [1.2771619970202082, 0.8607289709495961, 0.02]
wireless_mouse[0].rotation = [0, 0, 0]
art_print[0].position = [0.7060919200801924, 1.2908536302709055, 0.35]
art_print[0].rotation = [0, 0, 0]
floor_lamp[0].position = [1.6471854770236365, 2.9542730183182413, 0.825]
floor_lamp[0].rotation = [0, 0, 0]

solver.constraints = []

# Coordinates follow the supplied boundary: x=0..2.90, y=0..3.30.
# The desk occupies the west wall, with a task chair at its working edge.
# The visitor chair faces the desk and sits beside the east-wall whiteboard.
# Keep the north/south portions of the room available for circulation.
layout_specs = [
    (desk,                    [0.35, 1.35, 0.375],    0),
    (task_chair,              [1.10, 1.35, 0.55],   180),
    (side_chair,              [2.00, 1.35, 0.41],   180),
    (whiteboard,              [2.65, 1.35, 0.85],   180),
    (filing_pedestal,         [0.25, 2.50, 0.30],     0),
    (floor_lamp,              [0.30, 3.00, 0.825],  -90),

    # Desktop items: separate working, writing, stationery, and drink zones.
    (laptop_computer,         [0.35, 1.35, 0.865],    0),
    (wireless_mouse,          [0.40, 1.64, 0.77],     0),
    (spiral_bound_notebook_A, [0.40, 0.85, 0.755],    0),
    (spiral_bound_notebook_B, [0.42, 1.85, 0.755],    0),
    (pen_cup_A,               [0.12, 1.85, 0.80],     0),
    (pen_cup_B,               [0.12, 1.64, 0.80],     0),
    (drink_coaster,           [0.18, 1.05, 0.755],    0),
    (coffee_mug,              [0.18, 1.05, 0.81],     0),
    (ballpoint_pen_A,         [0.40, 0.85, 0.765],    0),
    (ballpoint_pen_B,         [0.42, 1.85, 0.765],    0),

    # Thin prints are mounted vertically, above furniture rather than on the floor.
    (world_map_print,         [0.005, 1.35, 1.95],    0),
    (photograph_print_A,      [0.005, 0.85, 1.35],    0),
    (photograph_print_B,      [0.005, 1.85, 1.35],    0),
    (art_print,               [2.89, 2.65, 1.65],   180),
    (clock,                   [1.45, 3.28, 2.15],   -90),
]

for asset_ref, center_xyz, yaw_degrees in layout_specs:
    asset_ref[0].position = center_xyz
    asset_ref[0].rotation = [0, 0, radians(yaw_degrees)]

# Apply the essential layout relationships before secondary placement constraints.
solver.against_wall(desk[0], walls[3])
solver.point_towards(desk[0], side_chair[0])
solver.point_towards(side_chair[0], desk[0])
solver.point_towards(task_chair[0], desk[0])

solver.against_wall(whiteboard[0], walls[1])
solver.align_with(whiteboard[0], side_chair[0])

# "Within 0.20 m" is interpreted as clear distance between bounding boxes,
# since the chair and board cannot have centers within 0.20 m without overlap.
# Initially their horizontal center separation is 0.65 m, giving a clear gap:
# 0.65 - 0.53/2 - 0.50/2 = 0.135 m.
# The solver measures 3D center distance; account for their 0.44 m height offset.
chair_board_height_offset = 0.85 - 0.41
chair_board_min_horizontal = 0.53 / 2 + 0.50 / 2 + 0.08
chair_board_max_horizontal = 0.53 / 2 + 0.50 / 2 + 0.20
solver.distance_constraint(
    side_chair[0],
    whiteboard[0],
    (chair_board_min_horizontal**2 + chair_board_height_offset**2)**0.5,
    (chair_board_max_horizontal**2 + chair_board_height_offset**2)**0.5,
    weight=10,
)

# All small objects have actual supporting surfaces.
for desktop_asset in (
    laptop_computer,
    wireless_mouse,
    spiral_bound_notebook_A,
    spiral_bound_notebook_B,
    pen_cup_A,
    pen_cup_B,
    drink_coaster,
):
    solver.on_top_of(desktop_asset[0], desk[0])
    solver.align_with(desktop_asset[0], desk[0])

solver.on_top_of(coffee_mug[0], drink_coaster[0])
solver.align_with(coffee_mug[0], drink_coaster[0])
solver.on_top_of(ballpoint_pen_A[0], spiral_bound_notebook_A[0])
solver.align_with(ballpoint_pen_A[0], spiral_bound_notebook_A[0])
solver.on_top_of(ballpoint_pen_B[0], spiral_bound_notebook_B[0])
solver.align_with(ballpoint_pen_B[0], spiral_bound_notebook_B[0])

# Wall-mounted objects retain their elevation through the position anchors below.
for west_wall_print in (
    world_map_print,
    photograph_print_A,
    photograph_print_B,
):
    solver.against_wall(west_wall_print[0], walls[3])
    solver.align_with(west_wall_print[0], desk[0])

solver.against_wall(art_print[0], walls[1])
solver.align_with(art_print[0], whiteboard[0])
solver.against_wall(clock[0], walls[2])
solver.align_with(
    clock[0],
    AssetInstance(position=[1.45, 2.80, 2.15],
                  rotation=[0, 0, radians(-90)]),
)

solver.against_wall(filing_pedestal[0], walls[3])
solver.align_with(filing_pedestal[0], desk[0])
solver.point_towards(floor_lamp[0], desk[0])

# Every instance receives a position-based constraint. Small tolerances preserve
# the non-overlapping desktop arrangement and the chair/whiteboard clearance.
# Fixed points are only constraint references, not additional scene assets.
for asset_ref, center_xyz, yaw_degrees in layout_specs:
    solver.distance_constraint(
        asset_ref[0],
        AssetInstance(position=list(center_xyz)),
        0,
        0.005,
        weight=10,
    )

# Maintain useful center separations without allowing chairs to enter the desk.
solver.distance_constraint(task_chair[0], desk[0], 0.76, 0.83, weight=10)
solver.distance_constraint(side_chair[0], desk[0], 1.60, 1.72)
solver.distance_constraint(floor_lamp[0], filing_pedestal[0], 0.70, 0.77)

solver.constraints = []
whiteboard[0].position = [2.646066665649414, 1.350000023841858, 0.8500000238418579]
whiteboard[0].rotation = [0, 0, -3.1328304326338854]
whiteboard[0].optimize = 2
drink_coaster[0].position = [0.18000000715255737, 1.0499999523162842, 0.7549999952316284]
drink_coaster[0].rotation = [0, 0, 0.029136427665192983]
drink_coaster[0].optimize = 2
pen_cup_B[0].position = [0.11999999731779099, 1.6399999856948853, 0.800000011920929]
pen_cup_B[0].rotation = [0, 0, 0.022791456869282706]
pen_cup_B[0].optimize = 2
filing_pedestal[0].position = [0.25112631916999817, 2.5, 0.30000001192092896]
filing_pedestal[0].rotation = [0, 0, 0.005651523938900898]
filing_pedestal[0].optimize = 2
world_map_print[0].position = [-0.0011201626621186733, 1.350000023841858, 0.30000001192092896]
world_map_print[0].rotation = [0, 0, 0.0025409150842135757]
world_map_print[0].optimize = 2
photograph_print_A[0].position = [-0.0011212574318051338, 0.8500000238418579, 0.10000000149011612]
photograph_print_A[0].rotation = [0, 0, 0.0025409215170312644]
photograph_print_A[0].optimize = 2
floor_lamp[0].position = [0.30999991297721863, 3.009999990463257, 0.824999988079071]
floor_lamp[0].rotation = [0, 0, -1.5582299555380688]
floor_lamp[0].optimize = 2
wireless_mouse[0].position = [0.4000000059604645, 1.6399999856948853, 0.7699999809265137]
wireless_mouse[0].rotation = [0, 0, 0.022791456869282706]
wireless_mouse[0].optimize = 2
laptop_computer[0].position = [0.3499999940395355, 1.350000023841858, 0.8650000095367432]
laptop_computer[0].rotation = [0, 0, 0.022791456869282706]
laptop_computer[0].optimize = 2
photograph_print_B[0].position = [-0.0011207102797925472, 1.850000023841858, 0.125]
photograph_print_B[0].rotation = [0, 0, 0.002540922439204702]
photograph_print_B[0].optimize = 2
spiral_bound_notebook_B[0].position = [0.41999998688697815, 1.850000023841858, 0.7549999952316284]
spiral_bound_notebook_B[0].rotation = [0, 0, 0.029136427665192983]
spiral_bound_notebook_B[0].optimize = 2
coffee_mug[0].position = [0.18000000715255737, 1.0499999523162842, 0.8100000023841858]
coffee_mug[0].rotation = [0, 0, 0.02278736617577962]
coffee_mug[0].optimize = 2
ballpoint_pen_A[0].position = [0.4000000059604645, 0.8500000238418579, 0.7649999856948853]
ballpoint_pen_A[0].rotation = [0, 0, 0.02278736617577962]
ballpoint_pen_A[0].optimize = 2
clock[0].position = [1.4500000476837158, 3.2886109352111816, 0.15000000596046448]
clock[0].rotation = [0, 0, -1.5682554052778654]
clock[0].optimize = 2
ballpoint_pen_B[0].position = [0.41999998688697815, 1.850000023841858, 0.7649999856948853]
ballpoint_pen_B[0].rotation = [0, 0, 0.02278736617577962]
ballpoint_pen_B[0].optimize = 2
task_chair[0].position = [1.1100000143051147, 1.350000023841858, 0.550000011920929]
task_chair[0].rotation = [0, 0, -3.1290262823329655]
task_chair[0].optimize = 2
spiral_bound_notebook_A[0].position = [0.4000000059604645, 0.8500000238418579, 0.7549999952316284]
spiral_bound_notebook_A[0].rotation = [0, 0, 0.029136427665192983]
spiral_bound_notebook_A[0].optimize = 2
side_chair[0].position = [1.9900000095367432, 1.350000023841858, 0.4099999964237213]
side_chair[0].rotation = [0, 0, -3.1196015053037707]
side_chair[0].optimize = 2
desk[0].position = [0.398046612739563, 1.350000023841858, 0.375]
desk[0].rotation = [0, 0, 0.0741098355944436]
desk[0].optimize = 2
art_print[0].position = [2.8976950645446777, 2.6500000953674316, 0.3499999940395355]
art_print[0].rotation = [0, 0, -3.1390517332948615]
art_print[0].optimize = 2
pen_cup_A[0].position = [0.11999999731779099, 1.850000023841858, 0.800000011920929]
pen_cup_A[0].rotation = [0, 0, 0.022791456869282706]
pen_cup_A[0].optimize = 2

