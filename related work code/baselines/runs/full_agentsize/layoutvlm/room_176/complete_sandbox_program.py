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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[5.50, 0.00, 0.00]),
    Wall(corner1=[5.50, 0.00, 0.00], corner2=[5.50, 4.50, 0.00]),
    Wall(corner1=[5.50, 4.50, 0.00], corner2=[0.00, 4.50, 0.00]),
    Wall(corner1=[0.00, 4.50, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
cork_coaster = Assets(description="cork coaster", size=[0.10, 0.10, 0.01], placements=[AssetInstance() for _ in range(1)])
glass_holder = Assets(description="glass holder", size=[0.09, 0.09, 0.12], placements=[AssetInstance() for _ in range(1)])
armchair = Assets(description="armchair", size=[0.85, 0.85, 0.95], placements=[AssetInstance() for _ in range(1)])
tealight_candle = Assets(description="tealight candle", size=[0.04, 0.04, 0.02], placements=[AssetInstance() for _ in range(1)])
sconce_A = Assets(description="sconce", size=[0.12, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
mirror = Assets(description="mirror", size=[0.04, 0.80, 1.10], placements=[AssetInstance() for _ in range(1)])
rug = Assets(description="rug", size=[1.70, 2.40, 0.01], placements=[AssetInstance() for _ in range(1)])
print_A = Assets(description="print", size=[0.03, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
paperback_book = Assets(description="paperback book", size=[0.20, 0.13, 0.03], placements=[AssetInstance() for _ in range(1)])
sofa = Assets(description="sofa", size=[0.95, 2.20, 0.85], placements=[AssetInstance() for _ in range(1)])
potted_plant_A = Assets(description="potted plant", size=[0.55, 0.55, 1.20], placements=[AssetInstance() for _ in range(1)])
clock = Assets(description="clock", size=[0.05, 0.35, 0.35], placements=[AssetInstance() for _ in range(1)])
hardcover_book = Assets(description="hardcover book", size=[0.24, 0.16, 0.04], placements=[AssetInstance() for _ in range(1)])
wall_shelf = Assets(description="wall shelf", size=[0.25, 1.20, 0.06], placements=[AssetInstance() for _ in range(1)])
photography_print = Assets(description="photography print", size=[0.03, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
floor_lamp = Assets(description="floor lamp", size=[0.45, 0.45, 1.65], placements=[AssetInstance() for _ in range(1)])
sconce_B = Assets(description="sconce", size=[0.12, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
potted_plant_B = Assets(description="potted plant", size=[0.55, 0.55, 1.20], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="coffee table", size=[0.65, 1.20, 0.42], placements=[AssetInstance() for _ in range(1)])
tv_remote_control = Assets(description="tv remote control", size=[0.19, 0.05, 0.03], placements=[AssetInstance() for _ in range(1)])
canvas_print = Assets(description="canvas print", size=[0.04, 1.00, 0.70], placements=[AssetInstance() for _ in range(1)])
print_B = Assets(description="print", size=[0.03, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])

cork_coaster[0].instance_id = 'cork_coaster_0'
glass_holder[0].instance_id = 'glass_holder_0'
armchair[0].instance_id = 'armchair_0'
tealight_candle[0].instance_id = 'tealight_candle_0'
sconce_A[0].instance_id = 'sconce_A_0'
mirror[0].instance_id = 'mirror_0'
rug[0].instance_id = 'rug_0'
print_A[0].instance_id = 'print_A_0'
paperback_book[0].instance_id = 'paperback_book_0'
sofa[0].instance_id = 'sofa_0'
potted_plant_A[0].instance_id = 'potted_plant_A_0'
clock[0].instance_id = 'clock_0'
hardcover_book[0].instance_id = 'hardcover_book_0'
wall_shelf[0].instance_id = 'wall_shelf_0'
photography_print[0].instance_id = 'photography_print_0'
floor_lamp[0].instance_id = 'floor_lamp_0'
sconce_B[0].instance_id = 'sconce_B_0'
potted_plant_B[0].instance_id = 'potted_plant_B_0'
coffee_table[0].instance_id = 'coffee_table_0'
tv_remote_control[0].instance_id = 'tv_remote_control_0'
canvas_print[0].instance_id = 'canvas_print_0'
print_B[0].instance_id = 'print_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

cork_coaster[0].position = [3.3847523086039146, 1.1520319606589333, 0.004]
cork_coaster[0].rotation = [0, 0, 0]
glass_holder[0].position = [0.11726664528017794, 0.10348063800947421, 0.06]
glass_holder[0].rotation = [0, 0, 0]
armchair[0].position = [3.088260082076571, 0.15156383525056133, 0.475]
armchair[0].rotation = [0, 0, 0]
tealight_candle[0].position = [1.110388901147217, 2.029134866769507, 0.01]
tealight_candle[0].rotation = [0, 0, 0]
sconce_A[0].position = [0.4035571520359202, 1.2915667806169215, 0.15]
sconce_A[0].rotation = [0, 0, 0]
mirror[0].position = [0.06838913453932982, 4.359329885363717, 0.55]
mirror[0].rotation = [0, 0, 0]
rug[0].position = [2.4962296329976335, 0.6113186866337967, 0.0075]
rug[0].rotation = [0, 0, 0]
print_A[0].position = [3.5001109038361005, 2.071278177059305, 0.35]
print_A[0].rotation = [0, 0, 0]
paperback_book[0].position = [4.841333080533568, 2.1197866022387464, 0.0125]
paperback_book[0].rotation = [0, 0, 0]
sofa[0].position = [5.441569435962993, 3.1095355941270046, 0.425]
sofa[0].rotation = [0, 0, 0]
potted_plant_A[0].position = [4.203692111764106, 3.4056872484060814, 0.6]
potted_plant_A[0].rotation = [0, 0, 0]
clock[0].position = [0.9519146279117086, 2.72907466619318, 0.175]
clock[0].rotation = [0, 0, 0]
hardcover_book[0].position = [0.6522619598603697, 0.32993528670536165, 0.0175]
hardcover_book[0].rotation = [0, 0, 0]
wall_shelf[0].position = [3.0391296772776917, 1.5167372740720155, 0.03]
wall_shelf[0].rotation = [0, 0, 0]
photography_print[0].position = [2.0583669504160382, 3.936445682774876, 0.4]
photography_print[0].rotation = [0, 0, 0]
floor_lamp[0].position = [4.893323051593854, 2.146203786297838, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
sconce_B[0].position = [2.7592470713643475, 3.12465641626504, 0.15]
sconce_B[0].rotation = [0, 0, 0]
potted_plant_B[0].position = [4.906236213137207, 3.7401278732729075, 0.6]
potted_plant_B[0].rotation = [0, 0, 0]
coffee_table[0].position = [3.8441515171584166, 0.14228707085097858, 0.21]
coffee_table[0].rotation = [0, 0, 0]
tv_remote_control[0].position = [0.3844488551024791, 3.8146672898482836, 0.0125]
tv_remote_control[0].rotation = [0, 0, 0]
canvas_print[0].position = [2.1006850840233913, 2.5576285905945157, 0.35]
canvas_print[0].rotation = [0, 0, 0]
print_B[0].position = [2.895565364838907, 2.03718260194911, 0.35]
print_B[0].rotation = [0, 0, 0]
cork_coaster[0].position = [3.3847523086039146, 1.1520319606589333, 0.004]
cork_coaster[0].rotation = [0, 0, 0]
glass_holder[0].position = [0.11726664528017794, 0.10348063800947421, 0.06]
glass_holder[0].rotation = [0, 0, 0]
armchair[0].position = [3.088260082076571, 0.15156383525056133, 0.475]
armchair[0].rotation = [0, 0, 0]
tealight_candle[0].position = [1.110388901147217, 2.029134866769507, 0.01]
tealight_candle[0].rotation = [0, 0, 0]
sconce_A[0].position = [0.4035571520359202, 1.2915667806169215, 0.15]
sconce_A[0].rotation = [0, 0, 0]
mirror[0].position = [0.06838913453932982, 4.359329885363717, 0.55]
mirror[0].rotation = [0, 0, 0]
rug[0].position = [2.4962296329976335, 0.6113186866337967, 0.0075]
rug[0].rotation = [0, 0, 0]
print_A[0].position = [3.5001109038361005, 2.071278177059305, 0.35]
print_A[0].rotation = [0, 0, 0]
paperback_book[0].position = [4.841333080533568, 2.1197866022387464, 0.0125]
paperback_book[0].rotation = [0, 0, 0]
sofa[0].position = [5.441569435962993, 3.1095355941270046, 0.425]
sofa[0].rotation = [0, 0, 0]
potted_plant_A[0].position = [4.203692111764106, 3.4056872484060814, 0.6]
potted_plant_A[0].rotation = [0, 0, 0]
clock[0].position = [0.9519146279117086, 2.72907466619318, 0.175]
clock[0].rotation = [0, 0, 0]
hardcover_book[0].position = [0.6522619598603697, 0.32993528670536165, 0.0175]
hardcover_book[0].rotation = [0, 0, 0]
wall_shelf[0].position = [3.0391296772776917, 1.5167372740720155, 0.03]
wall_shelf[0].rotation = [0, 0, 0]
photography_print[0].position = [2.0583669504160382, 3.936445682774876, 0.4]
photography_print[0].rotation = [0, 0, 0]
floor_lamp[0].position = [4.893323051593854, 2.146203786297838, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
sconce_B[0].position = [2.7592470713643475, 3.12465641626504, 0.15]
sconce_B[0].rotation = [0, 0, 0]
potted_plant_B[0].position = [4.906236213137207, 3.7401278732729075, 0.6]
potted_plant_B[0].rotation = [0, 0, 0]
coffee_table[0].position = [3.8441515171584166, 0.14228707085097858, 0.21]
coffee_table[0].rotation = [0, 0, 0]
tv_remote_control[0].position = [0.3844488551024791, 3.8146672898482836, 0.0125]
tv_remote_control[0].rotation = [0, 0, 0]
canvas_print[0].position = [2.1006850840233913, 2.5576285905945157, 0.35]
canvas_print[0].rotation = [0, 0, 0]
print_B[0].position = [2.895565364838907, 2.03718260194911, 0.35]
print_B[0].rotation = [0, 0, 0]

solver.constraints = []

# The seating group occupies the left/central part of the room. The sofa is
# centered between the two plants along the left wall and faces into the room.
sofa[0].position = [0.475, 2.25, 0.425]
sofa[0].rotation = [0, 0, radians(0)]

potted_plant_A[0].position = [0.275, 0.45, 0.60]
potted_plant_A[0].rotation = [0, 0, radians(0)]

potted_plant_B[0].position = [0.275, 4.05, 0.60]
potted_plant_B[0].rotation = [0, 0, radians(0)]

rug[0].position = [2.00, 2.25, 0.005]
rug[0].rotation = [0, 0, radians(0)]

coffee_table[0].position = [2.00, 2.25, 0.21]
coffee_table[0].rotation = [0, 0, radians(0)]

# The armchair faces the sofa across the coffee table.
armchair[0].position = [3.40, 2.25, 0.475]
armchair[0].rotation = [0, 0, radians(180)]

# The floor lamp is kept near the armchair without obstructing the seating area.
floor_lamp[0].position = [4.65, 3.85, 0.825]
floor_lamp[0].rotation = [0, 0, radians(225)]

# Small accessories are distributed over the coffee table. The glass holder
# sits on its coaster.
cork_coaster[0].position = [1.88, 1.98, 0.425]
cork_coaster[0].rotation = [0, 0, radians(0)]

glass_holder[0].position = [1.88, 1.98, 0.49]
glass_holder[0].rotation = [0, 0, radians(0)]

tealight_candle[0].position = [1.88, 2.55, 0.43]
tealight_candle[0].rotation = [0, 0, radians(0)]

tv_remote_control[0].position = [2.15, 2.27, 0.435]
tv_remote_control[0].rotation = [0, 0, radians(0)]

# A low wall shelf is mounted on the bottom wall, facing into the room.
wall_shelf[0].position = [4.50, 0.125, 1.00]
wall_shelf[0].rotation = [0, 0, radians(90)]

paperback_book[0].position = [4.27, 0.13, 1.045]
paperback_book[0].rotation = [0, 0, radians(90)]

hardcover_book[0].position = [4.70, 0.13, 1.05]
hardcover_book[0].rotation = [0, 0, radians(90)]

# The top wall forms a balanced gallery arrangement. All pieces face inward.
print_A[0].position = [0.60, 4.485, 1.50]
print_A[0].rotation = [0, 0, radians(-90)]

photography_print[0].position = [1.30, 4.485, 1.55]
photography_print[0].rotation = [0, 0, radians(-90)]

sconce_A[0].position = [1.85, 4.44, 1.55]
sconce_A[0].rotation = [0, 0, radians(-90)]

mirror[0].position = [2.45, 4.48, 1.45]
mirror[0].rotation = [0, 0, radians(-90)]

sconce_B[0].position = [3.05, 4.44, 1.55]
sconce_B[0].rotation = [0, 0, radians(-90)]

canvas_print[0].position = [3.75, 4.48, 1.50]
canvas_print[0].rotation = [0, 0, radians(-90)]

print_B[0].position = [4.75, 4.485, 1.50]
print_B[0].rotation = [0, 0, radians(-90)]

# The clock occupies the otherwise open right wall.
clock[0].position = [5.475, 2.25, 1.65]
clock[0].rotation = [0, 0, radians(180)]


# Fixed reference points preserve the proposed zones while allowing the solver
# to enforce wall contact and support relationships first.
sofa_anchor = AssetInstance(position=[0.475, 2.25, 0.425])
plant_A_anchor = AssetInstance(position=[0.275, 0.45, 0.60])
plant_B_anchor = AssetInstance(position=[0.275, 4.05, 0.60])
rug_anchor = AssetInstance(position=[2.00, 2.25, 0.005])
table_anchor = AssetInstance(position=[2.00, 2.25, 0.21])
armchair_anchor = AssetInstance(position=[3.40, 2.25, 0.475])
lamp_anchor = AssetInstance(position=[4.65, 3.85, 0.825])

coaster_anchor = AssetInstance(position=[1.88, 1.98, 0.425])
glass_anchor = AssetInstance(position=[1.88, 1.98, 0.49])
candle_anchor = AssetInstance(position=[1.88, 2.55, 0.43])
remote_anchor = AssetInstance(position=[2.15, 2.27, 0.435])

shelf_anchor = AssetInstance(position=[4.50, 0.125, 1.00])
paperback_anchor = AssetInstance(position=[4.27, 0.13, 1.045])
hardcover_anchor = AssetInstance(position=[4.70, 0.13, 1.05])

print_A_anchor = AssetInstance(position=[0.60, 4.485, 1.50])
photo_anchor = AssetInstance(position=[1.30, 4.485, 1.55])
sconce_A_anchor = AssetInstance(position=[1.85, 4.44, 1.55])
mirror_anchor = AssetInstance(position=[2.45, 4.48, 1.45])
sconce_B_anchor = AssetInstance(position=[3.05, 4.44, 1.55])
canvas_anchor = AssetInstance(position=[3.75, 4.48, 1.50])
print_B_anchor = AssetInstance(position=[4.75, 4.485, 1.50])
clock_anchor = AssetInstance(position=[5.475, 2.25, 1.65])

room_center = AssetInstance(position=[2.75, 2.25, 1.20])


# --- Main furniture and plants ---

# Wall contact is the primary sofa/plant positioning rule. Their anchors and
# separation preserve the required plant–sofa–plant ordering.
solver.against_wall(sofa[0], walls[3])
solver.distance_constraint(sofa[0], sofa_anchor, 0, 0, weight=10)
solver.point_towards(sofa[0], room_center)

solver.against_wall(potted_plant_A[0], walls[3])
solver.distance_constraint(potted_plant_A[0], plant_A_anchor, 0, 0, weight=10)
solver.distance_constraint(potted_plant_A[0], sofa[0], 1.70, 1.95)
solver.point_towards(potted_plant_A[0], room_center)

solver.against_wall(potted_plant_B[0], walls[3])
solver.distance_constraint(potted_plant_B[0], plant_B_anchor, 0, 0, weight=10)
solver.distance_constraint(potted_plant_B[0], sofa[0], 1.70, 1.95)
solver.point_towards(potted_plant_B[0], room_center)

solver.distance_constraint(rug[0], rug_anchor, 0, 0, weight=10)
solver.align_with(rug[0], sofa[0])

solver.distance_constraint(coffee_table[0], table_anchor, 0, 0, weight=10)
solver.align_with(coffee_table[0], sofa[0])

solver.distance_constraint(armchair[0], armchair_anchor, 0, 0, weight=10)
solver.distance_constraint(armchair[0], coffee_table[0], 1.25, 1.55)
solver.point_towards(armchair[0], sofa[0])

solver.distance_constraint(floor_lamp[0], lamp_anchor, 0, 0, weight=10)
solver.distance_constraint(floor_lamp[0], armchair[0], 1.45, 1.85)
solver.point_towards(floor_lamp[0], coffee_table[0])


# --- Coffee-table accessories ---

solver.on_top_of(cork_coaster[0], coffee_table[0])
solver.distance_constraint(cork_coaster[0], coaster_anchor, 0, 0, weight=10)
solver.align_with(cork_coaster[0], coffee_table[0])

solver.on_top_of(glass_holder[0], cork_coaster[0])
solver.distance_constraint(glass_holder[0], glass_anchor, 0, 0, weight=10)
solver.align_with(glass_holder[0], cork_coaster[0])

solver.on_top_of(tealight_candle[0], coffee_table[0])
solver.distance_constraint(tealight_candle[0], candle_anchor, 0, 0, weight=10)
solver.align_with(tealight_candle[0], coffee_table[0])

solver.on_top_of(tv_remote_control[0], coffee_table[0])
solver.distance_constraint(tv_remote_control[0], remote_anchor, 0, 0, weight=10)
solver.align_with(tv_remote_control[0], coffee_table[0])


# --- Shelf and books ---

solver.against_wall(wall_shelf[0], walls[0])
solver.distance_constraint(wall_shelf[0], shelf_anchor, 0, 0, weight=10)
solver.point_towards(wall_shelf[0], room_center)

solver.on_top_of(paperback_book[0], wall_shelf[0])
solver.distance_constraint(paperback_book[0], paperback_anchor, 0, 0, weight=10)
solver.align_with(paperback_book[0], wall_shelf[0])

solver.on_top_of(hardcover_book[0], wall_shelf[0])
solver.distance_constraint(hardcover_book[0], hardcover_anchor, 0, 0, weight=10)
solver.align_with(hardcover_book[0], wall_shelf[0])


# --- Wall-mounted decorations and lighting ---

solver.against_wall(print_A[0], walls[2])
solver.distance_constraint(print_A[0], print_A_anchor, 0, 0, weight=10)
solver.point_towards(print_A[0], room_center)

solver.against_wall(photography_print[0], walls[2])
solver.distance_constraint(photography_print[0], photo_anchor, 0, 0, weight=10)
solver.point_towards(photography_print[0], room_center)

solver.against_wall(sconce_A[0], walls[2])
solver.distance_constraint(sconce_A[0], sconce_A_anchor, 0, 0, weight=10)
solver.point_towards(sconce_A[0], room_center)

solver.against_wall(mirror[0], walls[2])
solver.distance_constraint(mirror[0], mirror_anchor, 0, 0, weight=10)
solver.point_towards(mirror[0], room_center)

solver.against_wall(sconce_B[0], walls[2])
solver.distance_constraint(sconce_B[0], sconce_B_anchor, 0, 0, weight=10)
solver.point_towards(sconce_B[0], room_center)

solver.against_wall(canvas_print[0], walls[2])
solver.distance_constraint(canvas_print[0], canvas_anchor, 0, 0, weight=10)
solver.point_towards(canvas_print[0], room_center)

solver.against_wall(print_B[0], walls[2])
solver.distance_constraint(print_B[0], print_B_anchor, 0, 0, weight=10)
solver.point_towards(print_B[0], room_center)

solver.against_wall(clock[0], walls[1])
solver.distance_constraint(clock[0], clock_anchor, 0, 0, weight=10)
solver.point_towards(clock[0], room_center)

solver.constraints = []
mirror[0].position = [2.450000047683716, 4.4800004959106445, 0.550000011920929]
mirror[0].rotation = [0, 0, -1.5707962934977693]
mirror[0].optimize = 2
print_A[0].position = [0.6000000238418579, 4.4850006103515625, 0.3499999940395355]
print_A[0].rotation = [0, 0, -1.5707962943271687]
print_A[0].optimize = 2
canvas_print[0].position = [3.75, 4.479999542236328, 0.3499999940395355]
canvas_print[0].rotation = [0, 0, -1.570796286219884]
canvas_print[0].optimize = 2
sconce_B[0].position = [3.049999952316284, 4.439999580383301, 0.15000000596046448]
sconce_B[0].rotation = [0, 0, -1.5707962907548707]
sconce_B[0].optimize = 2
clock[0].position = [5.474999904632568, 2.25, 0.17499999701976776]
clock[0].rotation = [0, 0, -3.1415926198501434]
clock[0].optimize = 2
armchair[0].position = [3.4000000953674316, 2.25, 0.4749999940395355]
armchair[0].rotation = [0, 0, -3.125884689672577]
armchair[0].optimize = 2
potted_plant_B[0].position = [0.2750000059604645, 4.050000190734863, 0.6000000238418579]
potted_plant_B[0].rotation = [0, 0, 4.639490789878673e-08]
potted_plant_B[0].optimize = 2
print_B[0].position = [4.75, 4.4850006103515625, 0.3499999940395355]
print_B[0].rotation = [0, 0, -1.5707962943271687]
print_B[0].optimize = 2
glass_holder[0].position = [1.8799999952316284, 1.9800000190734863, 0.4899999797344208]
glass_holder[0].rotation = [0, 0, -3.5094716902445067e-07]
glass_holder[0].optimize = 2
hardcover_book[0].position = [4.699999809265137, 0.12999999523162842, 0.07999999821186066]
hardcover_book[0].rotation = [0, 0, 1.5707963319009501]
hardcover_book[0].optimize = 2
sconce_A[0].position = [1.850000023841858, 4.439999580383301, 0.15000000596046448]
sconce_A[0].rotation = [0, 0, -1.5707962907548707]
sconce_A[0].optimize = 2
sofa[0].position = [0.4749999940395355, 2.25, 0.42500001192092896]
sofa[0].rotation = [0, 0, 4.742983171665296e-08]
sofa[0].optimize = 2
cork_coaster[0].position = [1.8799999952316284, 1.9800000190734863, 0.42499998211860657]
cork_coaster[0].rotation = [0, 0, -1.8972292113907452e-08]
cork_coaster[0].optimize = 2
photography_print[0].position = [1.2999999523162842, 4.485000133514404, 0.4000000059604645]
photography_print[0].rotation = [0, 0, -1.5707962951136938]
photography_print[0].optimize = 2
tealight_candle[0].position = [1.8799999952316284, 2.549999952316284, 0.429999977350235]
tealight_candle[0].rotation = [0, 0, -1.8698563022894017e-08]
tealight_candle[0].optimize = 2
wall_shelf[0].position = [4.5, 0.1249999850988388, 0.029999999329447746]
wall_shelf[0].rotation = [0, 0, 1.5707963562120184]
wall_shelf[0].optimize = 2
rug[0].position = [2.0, 2.25, 0.004999999888241291]
rug[0].rotation = [0, 0, 2.8015773529756896e-08]
rug[0].optimize = 2
coffee_table[0].position = [2.0, 2.25, 0.20999999344348907]
coffee_table[0].rotation = [0, 0, 2.233304550723316e-07]
coffee_table[0].optimize = 2
tv_remote_control[0].position = [2.1500000953674316, 2.2699999809265137, 0.4349999725818634]
tv_remote_control[0].rotation = [0, 0, -1.8698563022894017e-08]
tv_remote_control[0].optimize = 2
floor_lamp[0].position = [4.650000095367432, 3.8499999046325684, 0.824999988079071]
floor_lamp[0].rotation = [0, 0, -2.39825547603945]
floor_lamp[0].optimize = 2
potted_plant_A[0].position = [0.2750000059604645, 0.44999998807907104, 0.6000000238418579]
potted_plant_A[0].rotation = [0, 0, 4.6394901723868584e-08]
potted_plant_A[0].optimize = 2
paperback_book[0].position = [4.269999980926514, 0.12999999523162842, 0.07499999552965164]
paperback_book[0].rotation = [0, 0, 1.5707963319009501]
paperback_book[0].optimize = 2

