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
photograph_print_A = Assets(description="photograph print", size=[0.02, 0.45, 0.30], placements=[AssetInstance() for _ in range(1)])
spiral_bound_notebook_A = Assets(description="spiral bound notebook", size=[0.30, 0.21, 0.02], placements=[AssetInstance() for _ in range(1)])
world_map_print = Assets(description="world map print", size=[0.02, 1.20, 0.80], placements=[AssetInstance() for _ in range(1)])
side_chair = Assets(description="side chair", size=[0.55, 0.52, 0.82], placements=[AssetInstance() for _ in range(1)])
desk = Assets(description="desk", size=[0.70, 1.40, 0.75], placements=[AssetInstance() for _ in range(1)])
pen_cup_A = Assets(description="pen cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
pen_cup_B = Assets(description="pen cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
drink_coaster = Assets(description="drink coaster", size=[0.10, 0.10, 0.01], placements=[AssetInstance() for _ in range(1)])
photograph_print_B = Assets(description="photograph print", size=[0.02, 0.40, 0.30], placements=[AssetInstance() for _ in range(1)])
filing_pedestal = Assets(description="filing pedestal", size=[0.55, 0.42, 0.62], placements=[AssetInstance() for _ in range(1)])
task_chair = Assets(description="task chair", size=[0.65, 0.65, 1.05], placements=[AssetInstance() for _ in range(1)])
whiteboard = Assets(description="whiteboard", size=[0.55, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
ballpoint_pen_A = Assets(description="ballpoint pen", size=[0.14, 0.01, 0.01], placements=[AssetInstance() for _ in range(1)])
laptop_computer = Assets(description="laptop computer", size=[0.24, 0.35, 0.02], placements=[AssetInstance() for _ in range(1)])
clock = Assets(description="clock", size=[0.04, 0.30, 0.30], placements=[AssetInstance() for _ in range(1)])
coffee_mug = Assets(description="coffee mug", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
spiral_bound_notebook_B = Assets(description="spiral bound notebook", size=[0.30, 0.21, 0.02], placements=[AssetInstance() for _ in range(1)])
ballpoint_pen_B = Assets(description="ballpoint pen", size=[0.14, 0.01, 0.01], placements=[AssetInstance() for _ in range(1)])
wireless_mouse = Assets(description="wireless mouse", size=[0.11, 0.07, 0.04], placements=[AssetInstance() for _ in range(1)])
art_print = Assets(description="art print", size=[0.02, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
floor_lamp = Assets(description="floor lamp", size=[0.35, 0.35, 1.65], placements=[AssetInstance() for _ in range(1)])

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

photograph_print_A[0].position = [2.7683208677440234, 1.8566256131277763, 0.15]
photograph_print_A[0].rotation = [0, 0, 0]
spiral_bound_notebook_A[0].position = [2.6950150600102227, 2.8375058379781866, 0.01]
spiral_bound_notebook_A[0].rotation = [0, 0, 0]
world_map_print[0].position = [1.6043447943004343, 1.8923222685093841, 0.4]
world_map_print[0].rotation = [0, 0, 0]
side_chair[0].position = [2.5895466247016508, 0.9756548120017702, 0.41]
side_chair[0].rotation = [0, 0, 0]
desk[0].position = [0.8394032136197426, 2.4933988859766107, 0.375]
desk[0].rotation = [0, 0, 0]
pen_cup_A[0].position = [1.7481083032293903, 2.0913657986835026, 0.055]
pen_cup_A[0].rotation = [0, 0, 0]
pen_cup_B[0].position = [1.0818105129475932, 0.21484952583143063, 0.055]
pen_cup_B[0].rotation = [0, 0, 0]
drink_coaster[0].position = [2.8186473433285197, 3.0980117259737776, 0.005]
drink_coaster[0].rotation = [0, 0, 0]
photograph_print_B[0].position = [2.1611534171364357, 2.534475633491506, 0.15]
photograph_print_B[0].rotation = [0, 0, 0]
filing_pedestal[0].position = [1.1375098002924016, 2.532953066928742, 0.31]
filing_pedestal[0].rotation = [0, 0, 0]
task_chair[0].position = [1.6331096634836124, 1.4248091370317522, 0.525]
task_chair[0].rotation = [0, 0, 0]
whiteboard[0].position = [2.376064684432398, 3.2755949988290696, 0.9]
whiteboard[0].rotation = [0, 0, 0]
ballpoint_pen_A[0].position = [1.6657659351065506, 2.1063125540120726, 0.005]
ballpoint_pen_A[0].rotation = [0, 0, 0]
laptop_computer[0].position = [0.0889023738446745, 0.3369295960924045, 0.01]
laptop_computer[0].rotation = [0, 0, 0]
clock[0].position = [1.6957522488444283, 0.3346233507148576, 0.15]
clock[0].rotation = [0, 0, 0]
coffee_mug[0].position = [1.5083215553058127, 0.20788911676152785, 0.05]
coffee_mug[0].rotation = [0, 0, 0]
spiral_bound_notebook_B[0].position = [2.59756512406458, 0.23664569316731182, 0.01]
spiral_bound_notebook_B[0].rotation = [0, 0, 0]
ballpoint_pen_B[0].position = [1.2142162776167922, 0.036280740206664844, 0.005]
ballpoint_pen_B[0].rotation = [0, 0, 0]
wireless_mouse[0].position = [2.13085964921342, 0.07947705284560933, 0.02]
wireless_mouse[0].rotation = [0, 0, 0]
art_print[0].position = [2.8023429340066843, 0.1564141789572613, 0.4]
art_print[0].rotation = [0, 0, 0]
floor_lamp[0].position = [2.459881331560731, 2.105229016886582, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
photograph_print_A[0].position = [2.7683208677440234, 1.8566256131277763, 0.15]
photograph_print_A[0].rotation = [0, 0, 0]
spiral_bound_notebook_A[0].position = [2.6950150600102227, 2.8375058379781866, 0.01]
spiral_bound_notebook_A[0].rotation = [0, 0, 0]
world_map_print[0].position = [1.6043447943004343, 1.8923222685093841, 0.4]
world_map_print[0].rotation = [0, 0, 0]
side_chair[0].position = [2.5895466247016508, 0.9756548120017702, 0.41]
side_chair[0].rotation = [0, 0, 0]
desk[0].position = [0.8394032136197426, 2.4933988859766107, 0.375]
desk[0].rotation = [0, 0, 0]
pen_cup_A[0].position = [1.7481083032293903, 2.0913657986835026, 0.055]
pen_cup_A[0].rotation = [0, 0, 0]
pen_cup_B[0].position = [1.0818105129475932, 0.21484952583143063, 0.055]
pen_cup_B[0].rotation = [0, 0, 0]
drink_coaster[0].position = [2.8186473433285197, 3.0980117259737776, 0.005]
drink_coaster[0].rotation = [0, 0, 0]
photograph_print_B[0].position = [2.1611534171364357, 2.534475633491506, 0.15]
photograph_print_B[0].rotation = [0, 0, 0]
filing_pedestal[0].position = [1.1375098002924016, 2.532953066928742, 0.31]
filing_pedestal[0].rotation = [0, 0, 0]
task_chair[0].position = [1.6331096634836124, 1.4248091370317522, 0.525]
task_chair[0].rotation = [0, 0, 0]
whiteboard[0].position = [2.376064684432398, 3.2755949988290696, 0.9]
whiteboard[0].rotation = [0, 0, 0]
ballpoint_pen_A[0].position = [1.6657659351065506, 2.1063125540120726, 0.005]
ballpoint_pen_A[0].rotation = [0, 0, 0]
laptop_computer[0].position = [0.0889023738446745, 0.3369295960924045, 0.01]
laptop_computer[0].rotation = [0, 0, 0]
clock[0].position = [1.6957522488444283, 0.3346233507148576, 0.15]
clock[0].rotation = [0, 0, 0]
coffee_mug[0].position = [1.5083215553058127, 0.20788911676152785, 0.05]
coffee_mug[0].rotation = [0, 0, 0]
spiral_bound_notebook_B[0].position = [2.59756512406458, 0.23664569316731182, 0.01]
spiral_bound_notebook_B[0].rotation = [0, 0, 0]
ballpoint_pen_B[0].position = [1.2142162776167922, 0.036280740206664844, 0.005]
ballpoint_pen_B[0].rotation = [0, 0, 0]
wireless_mouse[0].position = [2.13085964921342, 0.07947705284560933, 0.02]
wireless_mouse[0].rotation = [0, 0, 0]
art_print[0].position = [2.8023429340066843, 0.1564141789572613, 0.4]
art_print[0].rotation = [0, 0, 0]
floor_lamp[0].position = [2.459881331560731, 2.105229016886582, 0.825]
floor_lamp[0].rotation = [0, 0, 0]

solver.constraints = []

# The desk is centered on the south wall and faces into the room toward the
# side chair. Its rotated footprint is 1.40 m wide and 0.70 m deep.
desk[0].position = [1.45, 0.35, 0.375]
desk[0].rotation = [0, 0, radians(90)]

# Place the whiteboard against the north wall. The side chair sits beside it
# with a 0.14 m edge-to-edge clearance, satisfying the requested <= 0.20 m
# proximity without overlapping their bounding boxes.
whiteboard[0].position = [1.45, 3.025, 0.90]
whiteboard[0].rotation = [0, 0, radians(-90)]

side_chair[0].position = [0.45, 3.025, 0.41]
side_chair[0].rotation = [0, 0, radians(-70)]

# The task chair occupies the working side of the desk and faces the desktop.
task_chair[0].position = [1.45, 1.20, 0.525]
task_chair[0].rotation = [0, 0, radians(-90)]

# Storage and lighting are kept around the perimeter to preserve circulation.
filing_pedestal[0].position = [2.625, 0.55, 0.31]
filing_pedestal[0].rotation = [0, 0, radians(180)]

floor_lamp[0].position = [0.25, 2.45, 0.825]
floor_lamp[0].rotation = [0, 0, radians(-45)]

# Wall decorations are distributed at viewing height on the side walls.
photograph_print_A[0].position = [2.89, 0.75, 1.50]
photograph_print_A[0].rotation = [0, 0, radians(180)]

world_map_print[0].position = [2.89, 2.15, 1.55]
world_map_print[0].rotation = [0, 0, radians(180)]

photograph_print_B[0].position = [0.01, 0.60, 1.50]
photograph_print_B[0].rotation = [0, 0, 0]

art_print[0].position = [0.01, 1.65, 1.55]
art_print[0].rotation = [0, 0, 0]

clock[0].position = [0.02, 2.75, 1.65]
clock[0].rotation = [0, 0, 0]

# Desktop objects are spaced across the 1.40 m-wide work surface.
spiral_bound_notebook_A[0].position = [0.94, 0.44, 0.76]
spiral_bound_notebook_A[0].rotation = [0, 0, radians(90)]

ballpoint_pen_A[0].position = [0.94, 0.44, 0.775]
ballpoint_pen_A[0].rotation = [0, 0, radians(90)]

laptop_computer[0].position = [1.43, 0.43, 0.76]
laptop_computer[0].rotation = [0, 0, radians(90)]

wireless_mouse[0].position = [1.66, 0.22, 0.77]
wireless_mouse[0].rotation = [0, 0, radians(90)]

spiral_bound_notebook_B[0].position = [1.91, 0.44, 0.76]
spiral_bound_notebook_B[0].rotation = [0, 0, radians(90)]

ballpoint_pen_B[0].position = [1.91, 0.44, 0.775]
ballpoint_pen_B[0].rotation = [0, 0, radians(90)]

pen_cup_A[0].position = [1.15, 0.16, 0.805]
pen_cup_A[0].rotation = [0, 0, radians(90)]

pen_cup_B[0].position = [2.02, 0.16, 0.805]
pen_cup_B[0].rotation = [0, 0, radians(90)]

drink_coaster[0].position = [0.86, 0.16, 0.755]
drink_coaster[0].rotation = [0, 0, radians(90)]

coffee_mug[0].position = [0.86, 0.16, 0.805]
coffee_mug[0].rotation = [0, 0, radians(90)]


# Important semantic constraints are declared first.
solver.against_wall(desk[0], walls[0])
solver.point_towards(desk[0], side_chair[0])

# Because distance_constraint measures center-to-center distance, these bounds
# include the two half-widths (0.60 + 0.26 m). They enforce an edge clearance
# from 0 to 0.20 m between the chair and whiteboard.
solver.distance_constraint(
    side_chair[0], whiteboard[0], 0.86, 1.06, weight=10
)
solver.point_towards(side_chair[0], desk[0])

solver.against_wall(whiteboard[0], walls[2])
solver.point_towards(
    whiteboard[0], AssetInstance(position=[1.45, 1.65, 0.90])
)

# Strong anchors retain the intended wall locations while permitting the
# semantic constraints above to take priority.
solver.distance_constraint(
    desk[0], AssetInstance(position=[1.45, 0.35, 0.375]), 0, 0, weight=10
)
solver.distance_constraint(
    whiteboard[0], AssetInstance(position=[1.45, 3.025, 0.90]), 0, 0, weight=10
)
solver.distance_constraint(
    side_chair[0], AssetInstance(position=[0.45, 3.025, 0.41]), 0, 0, weight=10
)

# Task chair: maintain usable clearance from the desk while facing it.
solver.distance_constraint(task_chair[0], desk[0], 0.75, 1.10, weight=10)
solver.distance_constraint(
    task_chair[0], AssetInstance(position=[1.45, 1.20, 0.525]), 0, 0, weight=10
)
solver.point_towards(task_chair[0], desk[0])

# Filing pedestal and lamp remain at perimeter anchors.
solver.against_wall(filing_pedestal[0], walls[1])
solver.distance_constraint(
    filing_pedestal[0],
    AssetInstance(position=[2.625, 0.55, 0.31]),
    0,
    0,
    weight=10,
)
solver.point_towards(
    filing_pedestal[0], AssetInstance(position=[1.45, 0.55, 0.31])
)

solver.against_wall(floor_lamp[0], walls[3])
solver.distance_constraint(
    floor_lamp[0], AssetInstance(position=[0.25, 2.45, 0.825]), 0, 0, weight=10
)
solver.point_towards(
    floor_lamp[0], AssetInstance(position=[1.45, 1.65, 0.825])
)

# Each wall-mounted decoration has both a wall/position constraint and an
# orientation constraint making its front face into the room.
solver.against_wall(photograph_print_A[0], walls[1])
solver.distance_constraint(
    photograph_print_A[0],
    AssetInstance(position=[2.89, 0.75, 1.50]),
    0,
    0,
    weight=10,
)
solver.point_towards(
    photograph_print_A[0], AssetInstance(position=[1.45, 0.75, 1.50])
)

solver.against_wall(world_map_print[0], walls[1])
solver.distance_constraint(
    world_map_print[0],
    AssetInstance(position=[2.89, 2.15, 1.55]),
    0,
    0,
    weight=10,
)
solver.point_towards(
    world_map_print[0], AssetInstance(position=[1.45, 2.15, 1.55])
)

solver.against_wall(photograph_print_B[0], walls[3])
solver.distance_constraint(
    photograph_print_B[0],
    AssetInstance(position=[0.01, 0.60, 1.50]),
    0,
    0,
    weight=10,
)
solver.point_towards(
    photograph_print_B[0], AssetInstance(position=[1.45, 0.60, 1.50])
)

solver.against_wall(art_print[0], walls[3])
solver.distance_constraint(
    art_print[0], AssetInstance(position=[0.01, 1.65, 1.55]), 0, 0, weight=10
)
solver.point_towards(
    art_print[0], AssetInstance(position=[1.45, 1.65, 1.55])
)

solver.against_wall(clock[0], walls[3])
solver.distance_constraint(
    clock[0], AssetInstance(position=[0.02, 2.75, 1.65]), 0, 0, weight=10
)
solver.point_towards(
    clock[0], AssetInstance(position=[1.45, 2.75, 1.65])
)

# All small work items are supported by the desk (or by an item on the desk).
# Exact-position constraints keep the objects separated across the tabletop,
# while alignment constraints provide an orientation constraint for each one.
solver.on_top_of(spiral_bound_notebook_A[0], desk[0])
solver.distance_constraint(
    spiral_bound_notebook_A[0],
    AssetInstance(position=[0.94, 0.44, 0.76]),
    0,
    0,
    weight=10,
)
solver.align_with(spiral_bound_notebook_A[0], desk[0])

solver.on_top_of(ballpoint_pen_A[0], spiral_bound_notebook_A[0])
solver.distance_constraint(
    ballpoint_pen_A[0],
    AssetInstance(position=[0.94, 0.44, 0.775]),
    0,
    0,
    weight=10,
)
solver.align_with(ballpoint_pen_A[0], spiral_bound_notebook_A[0])

solver.on_top_of(laptop_computer[0], desk[0])
solver.distance_constraint(
    laptop_computer[0],
    AssetInstance(position=[1.43, 0.43, 0.76]),
    0,
    0,
    weight=10,
)
solver.align_with(laptop_computer[0], desk[0])

solver.on_top_of(wireless_mouse[0], desk[0])
solver.distance_constraint(
    wireless_mouse[0],
    AssetInstance(position=[1.66, 0.22, 0.77]),
    0,
    0,
    weight=10,
)
solver.align_with(wireless_mouse[0], laptop_computer[0])

solver.on_top_of(spiral_bound_notebook_B[0], desk[0])
solver.distance_constraint(
    spiral_bound_notebook_B[0],
    AssetInstance(position=[1.91, 0.44, 0.76]),
    0,
    0,
    weight=10,
)
solver.align_with(spiral_bound_notebook_B[0], desk[0])

solver.on_top_of(ballpoint_pen_B[0], spiral_bound_notebook_B[0])
solver.distance_constraint(
    ballpoint_pen_B[0],
    AssetInstance(position=[1.91, 0.44, 0.775]),
    0,
    0,
    weight=10,
)
solver.align_with(ballpoint_pen_B[0], spiral_bound_notebook_B[0])

solver.on_top_of(pen_cup_A[0], desk[0])
solver.distance_constraint(
    pen_cup_A[0], AssetInstance(position=[1.15, 0.16, 0.805]), 0, 0, weight=10
)
solver.align_with(pen_cup_A[0], desk[0])

solver.on_top_of(pen_cup_B[0], desk[0])
solver.distance_constraint(
    pen_cup_B[0], AssetInstance(position=[2.02, 0.16, 0.805]), 0, 0, weight=10
)
solver.align_with(pen_cup_B[0], desk[0])

solver.on_top_of(drink_coaster[0], desk[0])
solver.distance_constraint(
    drink_coaster[0],
    AssetInstance(position=[0.86, 0.16, 0.755]),
    0,
    0,
    weight=10,
)
solver.align_with(drink_coaster[0], desk[0])

solver.on_top_of(coffee_mug[0], drink_coaster[0])
solver.distance_constraint(
    coffee_mug[0], AssetInstance(position=[0.86, 0.16, 0.805]), 0, 0, weight=10
)
solver.align_with(coffee_mug[0], desk[0])

solver.constraints = []
desk[0].position = [1.4500000476837158, 0.3512650728225708, 0.375]
desk[0].rotation = [0, 0, 1.5676845527343553]
desk[0].optimize = 2
spiral_bound_notebook_A[0].position = [0.9399999976158142, 0.4399999976158142, 0.7599999904632568]
spiral_bound_notebook_A[0].rotation = [0, 0, 1.5759018949431751]
spiral_bound_notebook_A[0].optimize = 2
pen_cup_A[0].position = [1.149999976158142, 0.1599999964237213, 0.8050000071525574]
pen_cup_A[0].rotation = [0, 0, 1.5773631181389127]
pen_cup_A[0].optimize = 2
task_chair[0].position = [1.4500000476837158, 1.2000000476837158, 0.5249999761581421]
task_chair[0].rotation = [0, 0, -1.5582299555380688]
task_chair[0].optimize = 2
clock[0].position = [0.019474096596240997, 2.75, 0.15000000596046448]
clock[0].rotation = [0, 0, 0.000628740304788295]
clock[0].optimize = 2
spiral_bound_notebook_B[0].position = [1.909999966621399, 0.4399999976158142, 0.7599999904632568]
spiral_bound_notebook_B[0].rotation = [0, 0, 1.5759018949431751]
spiral_bound_notebook_B[0].optimize = 2
laptop_computer[0].position = [1.4299999475479126, 0.4300000071525574, 0.7599999904632568]
laptop_computer[0].rotation = [0, 0, 1.5766783244888913]
laptop_computer[0].optimize = 2
wireless_mouse[0].position = [1.659999966621399, 0.2199999988079071, 0.7699999809265137]
wireless_mouse[0].rotation = [0, 0, 1.5781625542562698]
wireless_mouse[0].optimize = 2
photograph_print_B[0].position = [0.009886889718472958, 0.6000000238418579, 0.15000000596046448]
photograph_print_B[0].rotation = [0, 0, 0.0006287334826065193]
photograph_print_B[0].optimize = 2
world_map_print[0].position = [2.8902080059051514, 2.1500000953674316, 0.4000000059604645]
world_map_print[0].rotation = [0, 0, -3.1409638966297337]
world_map_print[0].optimize = 2
drink_coaster[0].position = [0.8600000143051147, 0.1599999964237213, 0.7549999952316284]
drink_coaster[0].rotation = [0, 0, 1.5766783244888913]
drink_coaster[0].optimize = 2
coffee_mug[0].position = [0.8600000143051147, 0.1599999964237213, 0.8100000023841858]
coffee_mug[0].rotation = [0, 0, 1.5773631181389127]
coffee_mug[0].optimize = 2
art_print[0].position = [0.009886488318443298, 1.649999976158142, 0.4000000059604645]
art_print[0].rotation = [0, 0, 0.0006287393432199034]
art_print[0].optimize = 2
ballpoint_pen_A[0].position = [0.9399999976158142, 0.4399999976158142, 0.7749999761581421]
ballpoint_pen_A[0].rotation = [0, 0, 1.5916944964523876]
ballpoint_pen_A[0].optimize = 2
whiteboard[0].position = [1.4500000476837158, 3.0247793197631836, 0.8999999761581421]
whiteboard[0].rotation = [0, 0, -1.571310331834232]
whiteboard[0].optimize = 2
filing_pedestal[0].position = [2.624666690826416, 0.550000011920929, 0.3100000023841858]
filing_pedestal[0].rotation = [0, 0, -3.1409629643812407]
filing_pedestal[0].optimize = 2
side_chair[0].position = [0.44999998807907104, 2.9503419399261475, 0.4099999964237213]
side_chair[0].rotation = [0, 0, -1.2060225060595338]
side_chair[0].optimize = 2
floor_lamp[0].position = [0.2107313722372055, 2.450000047683716, 0.824999988079071]
floor_lamp[0].rotation = [0, 0, -0.23340953268895223]
floor_lamp[0].optimize = 2
photograph_print_A[0].position = [2.8899354934692383, 0.75, 0.15000000596046448]
photograph_print_A[0].rotation = [0, 0, -3.1409639245319463]
photograph_print_A[0].optimize = 2
ballpoint_pen_B[0].position = [1.909999966621399, 0.4399999976158142, 0.7749999761581421]
ballpoint_pen_B[0].rotation = [0, 0, 1.5916944964523876]
ballpoint_pen_B[0].optimize = 2
pen_cup_B[0].position = [2.0199999809265137, 0.1599999964237213, 0.8050000071525574]
pen_cup_B[0].rotation = [0, 0, 1.5773631181389127]
pen_cup_B[0].optimize = 2

