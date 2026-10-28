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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.60, 0.00, 0.00]),
    Wall(corner1=[6.60, 0.00, 0.00], corner2=[6.60, 5.40, 0.00]),
    Wall(corner1=[6.60, 5.40, 0.00], corner2=[0.00, 5.40, 0.00]),
    Wall(corner1=[0.00, 5.40, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
ping_pong_ball_tube = Assets(description="ping pong ball tube", size=[0.08, 0.08, 0.32], placements=[AssetInstance() for _ in range(1)])
whiteboard = Assets(description="whiteboard", size=[0.04, 1.80, 1.20], placements=[AssetInstance() for _ in range(1)])
side_table = Assets(description="side table", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
floor_lamp = Assets(description="floor lamp", size=[0.35, 0.35, 1.65], placements=[AssetInstance() for _ in range(1)])
bowl = Assets(description="bowl", size=[0.28, 0.28, 0.10], placements=[AssetInstance() for _ in range(1)])
wall_shelf = Assets(description="wall shelf", size=[0.25, 1.20, 0.08], placements=[AssetInstance() for _ in range(1)])
clock = Assets(description="clock", size=[0.05, 0.30, 0.30], placements=[AssetInstance() for _ in range(1)])
rug = Assets(description="rug", size=[1.70, 2.40, 0.01], placements=[AssetInstance() for _ in range(1)])
poster = Assets(description="poster", size=[0.02, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
bench = Assets(description="bench", size=[0.45, 1.40, 0.45], placements=[AssetInstance() for _ in range(1)])
water_bottle = Assets(description="water bottle", size=[0.07, 0.07, 0.25], placements=[AssetInstance() for _ in range(1)])
canvas_print = Assets(description="canvas print", size=[0.04, 1.00, 0.70], placements=[AssetInstance() for _ in range(1)])
ping_pong_ball_A = Assets(description="ping pong ball", size=[0.04, 0.04, 0.04], placements=[AssetInstance() for _ in range(1)])
loveseat = Assets(description="loveseat", size=[0.85, 1.55, 0.85], placements=[AssetInstance() for _ in range(1)])
cork_coaster = Assets(description="cork coaster", size=[0.10, 0.10, 0.01], placements=[AssetInstance() for _ in range(1)])
storage_cabinet = Assets(description="storage cabinet", size=[0.45, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
photography_print_A = Assets(description="photography print", size=[0.03, 0.70, 0.50], placements=[AssetInstance() for _ in range(1)])
accent_chair = Assets(description="accent chair", size=[0.80, 0.75, 0.85], placements=[AssetInstance() for _ in range(1)])
ping_pong_table = Assets(description="ping pong table", size=[1.52, 2.74, 0.76], placements=[AssetInstance() for _ in range(1)])
ping_pong_ball_B = Assets(description="ping pong ball", size=[0.04, 0.04, 0.04], placements=[AssetInstance() for _ in range(1)])
ping_pong_ball_C = Assets(description="ping pong ball", size=[0.04, 0.04, 0.04], placements=[AssetInstance() for _ in range(1)])
spray_bottle = Assets(description="spray bottle", size=[0.08, 0.10, 0.28], placements=[AssetInstance() for _ in range(1)])
sports_equipment_rack = Assets(description="sports equipment rack", size=[0.35, 1.20, 0.80], placements=[AssetInstance() for _ in range(1)])
photography_print_B = Assets(description="photography print", size=[0.03, 0.70, 0.50], placements=[AssetInstance() for _ in range(1)])

ping_pong_ball_tube[0].instance_id = 'ping_pong_ball_tube_0'
whiteboard[0].instance_id = 'whiteboard_0'
side_table[0].instance_id = 'side_table_0'
floor_lamp[0].instance_id = 'floor_lamp_0'
bowl[0].instance_id = 'bowl_0'
wall_shelf[0].instance_id = 'wall_shelf_0'
clock[0].instance_id = 'clock_0'
rug[0].instance_id = 'rug_0'
poster[0].instance_id = 'poster_0'
bench[0].instance_id = 'bench_0'
water_bottle[0].instance_id = 'water_bottle_0'
canvas_print[0].instance_id = 'canvas_print_0'
ping_pong_ball_A[0].instance_id = 'ping_pong_ball_A_0'
loveseat[0].instance_id = 'loveseat_0'
cork_coaster[0].instance_id = 'cork_coaster_0'
storage_cabinet[0].instance_id = 'storage_cabinet_0'
photography_print_A[0].instance_id = 'photography_print_A_0'
accent_chair[0].instance_id = 'accent_chair_0'
ping_pong_table[0].instance_id = 'ping_pong_table_0'
ping_pong_ball_B[0].instance_id = 'ping_pong_ball_B_0'
ping_pong_ball_C[0].instance_id = 'ping_pong_ball_C_0'
spray_bottle[0].instance_id = 'spray_bottle_0'
sports_equipment_rack[0].instance_id = 'sports_equipment_rack_0'
photography_print_B[0].instance_id = 'photography_print_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

ping_pong_ball_tube[0].position = [5.239160588452585, 0.4313090241910345, 0.16]
ping_pong_ball_tube[0].rotation = [0, 0, 0]
whiteboard[0].position = [5.492352034113311, 4.289255928798536, 0.6]
whiteboard[0].rotation = [0, 0, 0]
side_table[0].position = [1.6808184889006734, 3.2952230523979043, 0.275]
side_table[0].rotation = [0, 0, 0]
floor_lamp[0].position = [3.5854901744243444, 2.2070443001276425, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
bowl[0].position = [0.1316908139394581, 3.218662004966148, 0.05]
bowl[0].rotation = [0, 0, 0]
wall_shelf[0].position = [5.923663304786996, 1.6716426782140659, 0.04]
wall_shelf[0].rotation = [0, 0, 0]
clock[0].position = [0.6808912129243455, 1.8365914885693502, 0.15]
clock[0].rotation = [0, 0, 0]
rug[0].position = [4.229413679398837, 2.0118566938053313, 0.005]
rug[0].rotation = [0, 0, 0]
poster[0].position = [3.9946774509039518, 1.8888661039529773, 0.45]
poster[0].rotation = [0, 0, 0]
bench[0].position = [6.2863932746279465, 1.0143412480738845, 0.225]
bench[0].rotation = [0, 0, 0]
water_bottle[0].position = [2.1295125858711383, 4.824328057416635, 0.125]
water_bottle[0].rotation = [0, 0, 0]
canvas_print[0].position = [1.0300930211189427, 2.5479586419082767, 0.35]
canvas_print[0].rotation = [0, 0, 0]
ping_pong_ball_A[0].position = [5.4840003029289015, 3.3260997924450817, 0.02]
ping_pong_ball_A[0].rotation = [0, 0, 0]
loveseat[0].position = [0.8859512421969866, 2.5042478675922926, 0.425]
loveseat[0].rotation = [0, 0, 0]
cork_coaster[0].position = [1.3062446699709798, 2.986109350572186, 0.005]
cork_coaster[0].rotation = [0, 0, 0]
storage_cabinet[0].position = [2.197668184555172, 1.9239269391792964, 0.9]
storage_cabinet[0].rotation = [0, 0, 0]
photography_print_A[0].position = [0.8022174644163639, 1.2989001091330004, 0.25]
photography_print_A[0].rotation = [0, 0, 0]
accent_chair[0].position = [6.3909405935743, 1.581934410145897, 0.425]
accent_chair[0].rotation = [0, 0, 0]
ping_pong_table[0].position = [5.870819525096281, 1.5552130737143162, 0.38]
ping_pong_table[0].rotation = [0, 0, 0]
ping_pong_ball_B[0].position = [6.38565891516107, 4.364597098800007, 0.02]
ping_pong_ball_B[0].rotation = [0, 0, 0]
ping_pong_ball_C[0].position = [5.345283572100407, 3.887374103879661, 0.02]
ping_pong_ball_C[0].rotation = [0, 0, 0]
spray_bottle[0].position = [3.373489157209051, 1.304478421616353, 0.14]
spray_bottle[0].rotation = [0, 0, 0]
sports_equipment_rack[0].position = [0.07989953451608024, 3.6422133472707907, 0.4]
sports_equipment_rack[0].rotation = [0, 0, 0]
photography_print_B[0].position = [6.396282650711681, 1.6896542482925683, 0.25]
photography_print_B[0].rotation = [0, 0, 0]
ping_pong_ball_tube[0].position = [5.239160588452585, 0.4313090241910345, 0.16]
ping_pong_ball_tube[0].rotation = [0, 0, 0]
whiteboard[0].position = [5.492352034113311, 4.289255928798536, 0.6]
whiteboard[0].rotation = [0, 0, 0]
side_table[0].position = [1.6808184889006734, 3.2952230523979043, 0.275]
side_table[0].rotation = [0, 0, 0]
floor_lamp[0].position = [3.5854901744243444, 2.2070443001276425, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
bowl[0].position = [0.1316908139394581, 3.218662004966148, 0.05]
bowl[0].rotation = [0, 0, 0]
wall_shelf[0].position = [5.923663304786996, 1.6716426782140659, 0.04]
wall_shelf[0].rotation = [0, 0, 0]
clock[0].position = [0.6808912129243455, 1.8365914885693502, 0.15]
clock[0].rotation = [0, 0, 0]
rug[0].position = [4.229413679398837, 2.0118566938053313, 0.005]
rug[0].rotation = [0, 0, 0]
poster[0].position = [3.9946774509039518, 1.8888661039529773, 0.45]
poster[0].rotation = [0, 0, 0]
bench[0].position = [6.2863932746279465, 1.0143412480738845, 0.225]
bench[0].rotation = [0, 0, 0]
water_bottle[0].position = [2.1295125858711383, 4.824328057416635, 0.125]
water_bottle[0].rotation = [0, 0, 0]
canvas_print[0].position = [1.0300930211189427, 2.5479586419082767, 0.35]
canvas_print[0].rotation = [0, 0, 0]
ping_pong_ball_A[0].position = [5.4840003029289015, 3.3260997924450817, 0.02]
ping_pong_ball_A[0].rotation = [0, 0, 0]
loveseat[0].position = [0.8859512421969866, 2.5042478675922926, 0.425]
loveseat[0].rotation = [0, 0, 0]
cork_coaster[0].position = [1.3062446699709798, 2.986109350572186, 0.005]
cork_coaster[0].rotation = [0, 0, 0]
storage_cabinet[0].position = [2.197668184555172, 1.9239269391792964, 0.9]
storage_cabinet[0].rotation = [0, 0, 0]
photography_print_A[0].position = [0.8022174644163639, 1.2989001091330004, 0.25]
photography_print_A[0].rotation = [0, 0, 0]
accent_chair[0].position = [6.3909405935743, 1.581934410145897, 0.425]
accent_chair[0].rotation = [0, 0, 0]
ping_pong_table[0].position = [5.870819525096281, 1.5552130737143162, 0.38]
ping_pong_table[0].rotation = [0, 0, 0]
ping_pong_ball_B[0].position = [6.38565891516107, 4.364597098800007, 0.02]
ping_pong_ball_B[0].rotation = [0, 0, 0]
ping_pong_ball_C[0].position = [5.345283572100407, 3.887374103879661, 0.02]
ping_pong_ball_C[0].rotation = [0, 0, 0]
spray_bottle[0].position = [3.373489157209051, 1.304478421616353, 0.14]
spray_bottle[0].rotation = [0, 0, 0]
sports_equipment_rack[0].position = [0.07989953451608024, 3.6422133472707907, 0.4]
sports_equipment_rack[0].rotation = [0, 0, 0]
photography_print_B[0].position = [6.396282650711681, 1.6896542482925683, 0.25]
photography_print_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Reference points used to preserve the intended zones while still allowing
# lower-weight adjustments if the solver needs to resolve physical conflicts.
room_center = AssetInstance(position=[3.30, 2.70, 1.00])
zero_rotation_reference = AssetInstance(
    position=[3.30, 2.70, 0.00],
    rotation=[0, 0, 0],
)


def pin_position(asset_instance, position, weight=0.1):
    """Softly preserve an explicitly selected placement."""
    solver.distance_constraint(
        asset_instance,
        AssetInstance(position=position),
        0.0,
        0.0,
        weight=weight,
    )


# ---------------------------------------------------------------------------
# Initial placements
# ---------------------------------------------------------------------------

# Living area along the left side of the room.
loveseat[0].position = [0.425, 1.65, 0.425]
loveseat[0].rotation = [0, 0, 0]

accent_chair[0].position = [2.00, 1.50, 0.425]
accent_chair[0].rotation = [0, 0, radians(175)]

# The center separation is 0.70 m. The combined half-width toward one another
# is 0.625 m, leaving a 0.075 m edge gap, which is within the requested 0.10 m.
side_table[0].position = [2.00, 2.20, 0.275]
side_table[0].rotation = [0, 0, radians(-90)]

floor_lamp[0].position = [0.90, 3.35, 0.825]
floor_lamp[0].rotation = [0, 0, radians(-90)]

# The thin rug intentionally sits beneath the living-area furniture.
rug[0].position = [1.25, 1.65, 0.005]
rug[0].rotation = [0, 0, 0]

bowl[0].position = [1.86, 2.22, 0.60]
bowl[0].rotation = [0, 0, 0]

cork_coaster[0].position = [2.10, 2.05, 0.555]
cork_coaster[0].rotation = [0, 0, 0]

# Bench and its bottle occupy the otherwise unused lower-wall zone.
bench[0].position = [3.00, 0.225, 0.225]
bench[0].rotation = [0, 0, radians(90)]

water_bottle[0].position = [2.70, 0.225, 0.575]
water_bottle[0].rotation = [0, 0, radians(90)]

# Recreation area on the right, with clear circulation around the table.
ping_pong_table[0].position = [4.65, 2.70, 0.38]
ping_pong_table[0].rotation = [0, 0, 0]

ping_pong_ball_A[0].position = [4.20, 2.00, 0.78]
ping_pong_ball_A[0].rotation = [0, 0, 0]

ping_pong_ball_B[0].position = [4.70, 2.70, 0.78]
ping_pong_ball_B[0].rotation = [0, 0, 0]

ping_pong_ball_C[0].position = [5.00, 3.40, 0.78]
ping_pong_ball_C[0].rotation = [0, 0, 0]

# Equipment storage is flush with the right wall.
sports_equipment_rack[0].position = [6.425, 4.45, 0.40]
sports_equipment_rack[0].rotation = [0, 0, radians(180)]

ping_pong_ball_tube[0].position = [6.40, 4.20, 0.96]
ping_pong_ball_tube[0].rotation = [0, 0, radians(180)]

spray_bottle[0].position = [6.40, 4.70, 0.94]
spray_bottle[0].rotation = [0, 0, radians(180)]

# Tall storage and wall-mounted objects use the upper wall without blocking
# either the living area or ping-pong circulation.
storage_cabinet[0].position = [1.00, 5.175, 0.90]
storage_cabinet[0].rotation = [0, 0, radians(-90)]

photography_print_A[0].position = [2.10, 5.385, 1.55]
photography_print_A[0].rotation = [0, 0, radians(-90)]

whiteboard[0].position = [3.50, 5.38, 1.55]
whiteboard[0].rotation = [0, 0, radians(-90)]

wall_shelf[0].position = [5.25, 5.275, 1.55]
wall_shelf[0].rotation = [0, 0, radians(-90)]

# Remaining decorations are distributed across open wall sections.
clock[0].position = [0.025, 4.55, 1.75]
clock[0].rotation = [0, 0, 0]

poster[0].position = [6.59, 1.00, 1.55]
poster[0].rotation = [0, 0, radians(180)]

canvas_print[0].position = [6.58, 3.05, 1.55]
canvas_print[0].rotation = [0, 0, radians(180)]

photography_print_B[0].position = [5.70, 0.015, 1.45]
photography_print_B[0].rotation = [0, 0, radians(90)]


# ---------------------------------------------------------------------------
# Constraints
# Important semantic constraints are listed before softer placement anchors.
# ---------------------------------------------------------------------------

# The accent chair must face the loveseat. Its center-distance interval accounts
# for the two footprints and enforces no more than 0.10 m of edge clearance
# from the side table without making the two pieces overlap.
solver.point_towards(accent_chair[0], loveseat[0])
solver.distance_constraint(
    accent_chair[0],
    side_table[0],
    0.625,
    0.725,
    weight=10,
)
pin_position(accent_chair[0], [2.00, 1.50, 0.425])

# Keep the side table beside the chair and orient its accessible side toward it.
solver.distance_constraint(
    side_table[0],
    accent_chair[0],
    0.625,
    0.725,
    weight=10,
)
solver.point_towards(side_table[0], accent_chair[0])
pin_position(side_table[0], [2.00, 2.20, 0.275])

# The loveseat is wall-backed and faces into the conversation group.
solver.against_wall(loveseat[0], walls[3])
solver.point_towards(loveseat[0], accent_chair[0])
pin_position(loveseat[0], [0.425, 1.65, 0.425])

solver.distance_constraint(
    floor_lamp[0], loveseat[0], 1.00, 2.00, weight=1
)
solver.point_towards(floor_lamp[0], loveseat[0])
pin_position(floor_lamp[0], [0.90, 3.35, 0.825])

solver.distance_constraint(rug[0], loveseat[0], 0.0, 1.25, weight=1)
solver.align_with(rug[0], loveseat[0])
pin_position(rug[0], [1.25, 1.65, 0.005])

# Small living-area objects remain supported by the side table.
solver.on_top_of(bowl[0], side_table[0])
solver.distance_constraint(bowl[0], side_table[0], 0.30, 0.40, weight=1)
solver.align_with(bowl[0], side_table[0])
pin_position(bowl[0], [1.86, 2.22, 0.60])

solver.on_top_of(cork_coaster[0], side_table[0])
solver.distance_constraint(
    cork_coaster[0], side_table[0], 0.25, 0.40, weight=1
)
solver.align_with(cork_coaster[0], side_table[0])
pin_position(cork_coaster[0], [2.10, 2.05, 0.555])

# Lower-wall bench, with the bottle supported by its top.
solver.against_wall(bench[0], walls[0])
solver.point_towards(bench[0], room_center)
pin_position(bench[0], [3.00, 0.225, 0.225])

solver.on_top_of(water_bottle[0], bench[0])
solver.distance_constraint(water_bottle[0], bench[0], 0.35, 0.50, weight=1)
solver.align_with(water_bottle[0], bench[0])
pin_position(water_bottle[0], [2.70, 0.225, 0.575])

# Ping-pong table and balls.
solver.distance_constraint(
    ping_pong_table[0],
    AssetInstance(position=[4.65, 2.70, 0.38]),
    0.0,
    0.0,
    weight=1,
)
solver.align_with(ping_pong_table[0], zero_rotation_reference)

solver.on_top_of(ping_pong_ball_A[0], ping_pong_table[0])
solver.distance_constraint(
    ping_pong_ball_A[0], ping_pong_table[0], 0.65, 0.95, weight=1
)
solver.align_with(ping_pong_ball_A[0], ping_pong_table[0])
pin_position(ping_pong_ball_A[0], [4.20, 2.00, 0.78])

solver.on_top_of(ping_pong_ball_B[0], ping_pong_table[0])
solver.distance_constraint(
    ping_pong_ball_B[0], ping_pong_table[0], 0.38, 0.48, weight=1
)
solver.align_with(ping_pong_ball_B[0], ping_pong_table[0])
pin_position(ping_pong_ball_B[0], [4.70, 2.70, 0.78])

solver.on_top_of(ping_pong_ball_C[0], ping_pong_table[0])
solver.distance_constraint(
    ping_pong_ball_C[0], ping_pong_table[0], 0.75, 1.05, weight=1
)
solver.align_with(ping_pong_ball_C[0], ping_pong_table[0])
pin_position(ping_pong_ball_C[0], [5.00, 3.40, 0.78])

# Right-wall equipment rack and the small objects stored on it.
solver.against_wall(sports_equipment_rack[0], walls[1])
solver.point_towards(sports_equipment_rack[0], room_center)
pin_position(sports_equipment_rack[0], [6.425, 4.45, 0.40])

solver.on_top_of(ping_pong_ball_tube[0], sports_equipment_rack[0])
solver.distance_constraint(
    ping_pong_ball_tube[0], sports_equipment_rack[0], 0.55, 0.70, weight=1
)
solver.align_with(ping_pong_ball_tube[0], sports_equipment_rack[0])
pin_position(ping_pong_ball_tube[0], [6.40, 4.20, 0.96])

solver.on_top_of(spray_bottle[0], sports_equipment_rack[0])
solver.distance_constraint(
    spray_bottle[0], sports_equipment_rack[0], 0.50, 0.70, weight=1
)
solver.align_with(spray_bottle[0], sports_equipment_rack[0])
pin_position(spray_bottle[0], [6.40, 4.70, 0.94])

# The storage cabinet's wall constraint is high-priority per the layout brief.
solver.against_wall(storage_cabinet[0], walls[2])
solver.point_towards(storage_cabinet[0], room_center)
pin_position(storage_cabinet[0], [1.00, 5.175, 0.90])

# Upper-wall fixtures and decorations face inward.
solver.against_wall(photography_print_A[0], walls[2])
solver.point_towards(photography_print_A[0], room_center)
pin_position(photography_print_A[0], [2.10, 5.385, 1.55])

solver.against_wall(whiteboard[0], walls[2])
solver.point_towards(whiteboard[0], room_center)
pin_position(whiteboard[0], [3.50, 5.38, 1.55])

solver.against_wall(wall_shelf[0], walls[2])
solver.point_towards(wall_shelf[0], room_center)
pin_position(wall_shelf[0], [5.25, 5.275, 1.55])

solver.against_wall(clock[0], walls[3])
solver.point_towards(clock[0], room_center)
pin_position(clock[0], [0.025, 4.55, 1.75])

solver.against_wall(poster[0], walls[1])
solver.point_towards(poster[0], room_center)
pin_position(poster[0], [6.59, 1.00, 1.55])

solver.against_wall(canvas_print[0], walls[1])
solver.point_towards(canvas_print[0], room_center)
pin_position(canvas_print[0], [6.58, 3.05, 1.55])

solver.against_wall(photography_print_B[0], walls[0])
solver.point_towards(photography_print_B[0], room_center)
pin_position(photography_print_B[0], [5.70, 0.015, 1.45])

solver.constraints = []
storage_cabinet[0].position = [1.0, 5.175000190734863, 0.8999999761581421]
storage_cabinet[0].rotation = [0, 0, -1.5707961944266386]
storage_cabinet[0].optimize = 2
spray_bottle[0].position = [6.250024795532227, 5.003453731536865, 0.9399999976158142]
spray_bottle[0].rotation = [0, 0, -3.1415912461521804]
spray_bottle[0].optimize = 2
bowl[0].position = [1.741511583328247, 2.4412131309509277, 0.6000000238418579]
bowl[0].rotation = [0, 0, -1.5363721392329153]
bowl[0].optimize = 2
poster[0].position = [6.589999675750732, 1.0, 0.44999998807907104]
poster[0].rotation = [0, 0, -3.141592439514711]
poster[0].optimize = 2
sports_equipment_rack[0].position = [6.424999713897705, 4.449999809265137, 0.4000000059604645]
sports_equipment_rack[0].rotation = [0, 0, 3.141592353036827]
sports_equipment_rack[0].optimize = 2
water_bottle[0].position = [2.5698206424713135, 0.0952640250325203, 0.574999988079071]
water_bottle[0].rotation = [0, 0, 1.5707961029781166]
water_bottle[0].optimize = 2
canvas_print[0].position = [6.580000877380371, 3.049999952316284, 0.3499999940395355]
canvas_print[0].rotation = [0, 0, -3.1415925584435946]
canvas_print[0].optimize = 2
ping_pong_ball_tube[0].position = [6.2502121925354, 3.8757927417755127, 0.9600000381469727]
ping_pong_ball_tube[0].rotation = [0, 0, -3.1415912461521804]
ping_pong_ball_tube[0].optimize = 2
clock[0].position = [0.02500002272427082, 4.550000190734863, 0.15000000596046448]
clock[0].rotation = [0, 0, 1.7683419866435109e-07]
clock[0].optimize = 2
bench[0].position = [3.0, 0.22500000894069672, 0.22499999403953552]
bench[0].rotation = [0, 0, 1.570796447813832]
bench[0].optimize = 2
ping_pong_ball_B[0].position = [5.417913913726807, 2.5045559406280518, 0.7799999713897705]
ping_pong_ball_B[0].rotation = [0, 0, 0.03769904049077433]
ping_pong_ball_B[0].optimize = 2
accent_chair[0].position = [2.0, 1.5, 0.42500001192092896]
accent_chair[0].rotation = [0, 0, 3.0763173399001063]
accent_chair[0].optimize = 2
photography_print_B[0].position = [5.699999809265137, 0.014999879524111748, 0.25]
photography_print_B[0].rotation = [0, 0, 1.5707965019056869]
photography_print_B[0].optimize = 2
cork_coaster[0].position = [2.2584993839263916, 1.9587756395339966, 0.5550000071525574]
cork_coaster[0].rotation = [0, 0, -1.5363721392329153]
cork_coaster[0].optimize = 2
wall_shelf[0].position = [5.25, 5.274999618530273, 0.03999999910593033]
wall_shelf[0].rotation = [0, 0, -1.5707962465931025]
wall_shelf[0].optimize = 2
loveseat[0].position = [0.42500030994415283, 1.649999976158142, 0.42500001192092896]
loveseat[0].rotation = [0, 0, -1.0503426107324725e-07]
loveseat[0].optimize = 2
rug[0].position = [1.809478521347046, 1.649999976158142, 0.004999999888241291]
rug[0].rotation = [0, 0, -7.714508937498043e-07]
rug[0].optimize = 2
whiteboard[0].position = [3.5, 5.380000114440918, 0.6000000238418579]
whiteboard[0].rotation = [0, 0, -1.5707961928293155]
whiteboard[0].optimize = 2
photography_print_A[0].position = [2.0999999046325684, 5.385000228881836, 0.25]
photography_print_A[0].rotation = [0, 0, -1.5707961567415987]
photography_print_A[0].optimize = 2
ping_pong_table[0].position = [4.650000095367432, 2.700000047683716, 0.3799999952316284]
ping_pong_table[0].rotation = [0, 0, 0.03769911119841034]
ping_pong_table[0].optimize = 2
ping_pong_ball_A[0].position = [4.199999809265137, 2.0, 0.7799999713897705]
ping_pong_ball_A[0].rotation = [0, 0, 0.03769904049077433]
ping_pong_ball_A[0].optimize = 2
ping_pong_ball_C[0].position = [5.0, 3.4000000953674316, 0.7799999713897705]
ping_pong_ball_C[0].rotation = [0, 0, 0.03769904049077433]
ping_pong_ball_C[0].optimize = 2
floor_lamp[0].position = [0.8999999761581421, 3.3499999046325684, 0.824999988079071]
floor_lamp[0].rotation = [0, 0, -1.6060771710444062]
floor_lamp[0].optimize = 2
side_table[0].position = [2.0, 2.200000047683716, 0.2750000059604645]
side_table[0].rotation = [0, 0, -1.53623880796822]
side_table[0].optimize = 2

