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
wall_sconce_A = Assets(description="wall sconce", size=[0.12, 0.18, 0.32], placements=[AssetInstance() for _ in range(1)])
coffee_table_book_A = Assets(description="coffee table book", size=[0.22, 0.28, 0.03], placements=[AssetInstance() for _ in range(1)])
floor_lamp = Assets(description="floor lamp", size=[0.42, 0.42, 1.65], placements=[AssetInstance() for _ in range(1)])
paperback_book_A = Assets(description="paperback book", size=[0.03, 0.13, 0.20], placements=[AssetInstance() for _ in range(1)])
wall_planter = Assets(description="wall planter", size=[0.18, 0.28, 0.35], placements=[AssetInstance() for _ in range(1)])
wall_sconce_B = Assets(description="wall sconce", size=[0.12, 0.18, 0.32], placements=[AssetInstance() for _ in range(1)])
map_print = Assets(description="map print", size=[0.03, 0.90, 0.65], placements=[AssetInstance() for _ in range(1)])
picture_frame = Assets(description="picture frame", size=[0.10, 0.20, 0.25], placements=[AssetInstance() for _ in range(1)])
mirror = Assets(description="mirror", size=[0.04, 0.80, 1.20], placements=[AssetInstance() for _ in range(1)])
coffee_table_book_B = Assets(description="coffee table book", size=[0.24, 0.32, 0.04], placements=[AssetInstance() for _ in range(1)])
clock = Assets(description="clock", size=[0.05, 0.35, 0.35], placements=[AssetInstance() for _ in range(1)])
coffee_table_book_C = Assets(description="coffee table book", size=[0.23, 0.30, 0.04], placements=[AssetInstance() for _ in range(1)])
jar_candle_A = Assets(description="jar candle", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
wall_sconce_C = Assets(description="wall sconce", size=[0.12, 0.18, 0.32], placements=[AssetInstance() for _ in range(1)])
remote = Assets(description="remote", size=[0.18, 0.05, 0.02], placements=[AssetInstance() for _ in range(1)])
side_table = Assets(description="side table", size=[0.48, 0.48, 0.55], placements=[AssetInstance() for _ in range(1)])
botanical_print_A = Assets(description="botanical print", size=[0.03, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])
wall_sconce_D = Assets(description="wall sconce", size=[0.12, 0.18, 0.32], placements=[AssetInstance() for _ in range(1)])
jar_candle_B = Assets(description="jar candle", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
armchair = Assets(description="armchair", size=[0.88, 0.85, 0.95], placements=[AssetInstance() for _ in range(1)])
remote_like_bar = Assets(description="remote like bar", size=[0.20, 0.04, 0.03], placements=[AssetInstance() for _ in range(1)])
set_top_box_router = Assets(description="set top box router", size=[0.18, 0.25, 0.05], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="coffee table", size=[0.65, 1.20, 0.42], placements=[AssetInstance() for _ in range(1)])
media_console = Assets(description="media console", size=[0.42, 1.80, 0.60], placements=[AssetInstance() for _ in range(1)])
sofa = Assets(description="sofa", size=[0.95, 2.20, 0.88], placements=[AssetInstance() for _ in range(1)])
botanical_print_B = Assets(description="botanical print", size=[0.03, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])
botanical_print_C = Assets(description="botanical print", size=[0.03, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])
paperback_book_B = Assets(description="paperback book", size=[0.03, 0.13, 0.20], placements=[AssetInstance() for _ in range(1)])
painting = Assets(description="painting", size=[0.04, 1.10, 0.75], placements=[AssetInstance() for _ in range(1)])

wall_sconce_A[0].instance_id = 'wall_sconce_A_0'
coffee_table_book_A[0].instance_id = 'coffee_table_book_A_0'
floor_lamp[0].instance_id = 'floor_lamp_0'
paperback_book_A[0].instance_id = 'paperback_book_A_0'
wall_planter[0].instance_id = 'wall_planter_0'
wall_sconce_B[0].instance_id = 'wall_sconce_B_0'
map_print[0].instance_id = 'map_print_0'
picture_frame[0].instance_id = 'picture_frame_0'
mirror[0].instance_id = 'mirror_0'
coffee_table_book_B[0].instance_id = 'coffee_table_book_B_0'
clock[0].instance_id = 'clock_0'
coffee_table_book_C[0].instance_id = 'coffee_table_book_C_0'
jar_candle_A[0].instance_id = 'jar_candle_A_0'
wall_sconce_C[0].instance_id = 'wall_sconce_C_0'
remote[0].instance_id = 'remote_0'
side_table[0].instance_id = 'side_table_0'
botanical_print_A[0].instance_id = 'botanical_print_A_0'
wall_sconce_D[0].instance_id = 'wall_sconce_D_0'
jar_candle_B[0].instance_id = 'jar_candle_B_0'
armchair[0].instance_id = 'armchair_0'
remote_like_bar[0].instance_id = 'remote_like_bar_0'
set_top_box_router[0].instance_id = 'set_top_box_router_0'
coffee_table[0].instance_id = 'coffee_table_0'
media_console[0].instance_id = 'media_console_0'
sofa[0].instance_id = 'sofa_0'
botanical_print_B[0].instance_id = 'botanical_print_B_0'
botanical_print_C[0].instance_id = 'botanical_print_C_0'
paperback_book_B[0].instance_id = 'paperback_book_B_0'
painting[0].instance_id = 'painting_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

wall_sconce_A[0].position = [4.62468862170636, 0.4373986622271568, 0.16]
wall_sconce_A[0].rotation = [0, 0, 0]
coffee_table_book_A[0].position = [4.778036684005156, 1.8943874462718964, 0.015]
coffee_table_book_A[0].rotation = [0, 0, 0]
floor_lamp[0].position = [0.09724231776792097, 3.740025864804257, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
paperback_book_A[0].position = [1.6465743210554422, 0.3934748292254743, 0.1]
paperback_book_A[0].rotation = [0, 0, 0]
wall_planter[0].position = [3.469744770104832, 1.6077307181246348, 0.175]
wall_planter[0].rotation = [0, 0, 0]
wall_sconce_B[0].position = [5.254295046725186, 3.228945685119996, 0.16]
wall_sconce_B[0].rotation = [0, 0, 0]
map_print[0].position = [1.4361328448443564, 1.0286634610509837, 0.325]
map_print[0].rotation = [0, 0, 0]
picture_frame[0].position = [2.2682953989667807, 1.847533822769523, 0.125]
picture_frame[0].rotation = [0, 0, 0]
mirror[0].position = [0.02434160515095135, 3.8459946829743923, 0.6]
mirror[0].rotation = [0, 0, 0]
coffee_table_book_B[0].position = [0.22050720473814428, 3.818065002462662, 0.02]
coffee_table_book_B[0].rotation = [0, 0, 0]
clock[0].position = [5.136267182472398, 1.097343499063643, 0.175]
clock[0].rotation = [0, 0, 0]
coffee_table_book_C[0].position = [5.448424120042668, 1.4478216779210606, 0.0175]
coffee_table_book_C[0].rotation = [0, 0, 0]
jar_candle_A[0].position = [1.6285221031569184, 2.6562837520880733, 0.055]
jar_candle_A[0].rotation = [0, 0, 0]
wall_sconce_C[0].position = [4.157647331504386, 0.27180904956157764, 0.16]
wall_sconce_C[0].rotation = [0, 0, 0]
remote[0].position = [0.9997004954665468, 1.593129467668185, 0.01]
remote[0].rotation = [0, 0, 0]
side_table[0].position = [5.420211352048314, 3.0739174294476803, 0.275]
side_table[0].rotation = [0, 0, 0]
botanical_print_A[0].position = [3.6595052554796292, 0.9501747258924401, 0.3]
botanical_print_A[0].rotation = [0, 0, 0]
wall_sconce_D[0].position = [2.6674185599507036, 0.7616838260881802, 0.16]
wall_sconce_D[0].rotation = [0, 0, 0]
jar_candle_B[0].position = [4.630653420713783, 0.5735698671115308, 0.055]
jar_candle_B[0].rotation = [0, 0, 0]
armchair[0].position = [4.786014858835115, 1.7486716755082337, 0.475]
armchair[0].rotation = [0, 0, 0]
remote_like_bar[0].position = [2.3485189350862408, 2.865901205208828, 0.0125]
remote_like_bar[0].rotation = [0, 0, 0]
set_top_box_router[0].position = [3.9155030824226214, 1.3162351684323799, 0.025]
set_top_box_router[0].rotation = [0, 0, 0]
coffee_table[0].position = [0.7460637691328871, 1.4684904807469423, 0.21]
coffee_table[0].rotation = [0, 0, 0]
media_console[0].position = [1.1314782696257442, 1.667228244451552, 0.3]
media_console[0].rotation = [0, 0, 0]
sofa[0].position = [5.4215820330599085, 1.4679836786415645, 0.44]
sofa[0].rotation = [0, 0, 0]
botanical_print_B[0].position = [1.427984859428749, 0.05746266975310732, 0.3]
botanical_print_B[0].rotation = [0, 0, 0]
botanical_print_C[0].position = [5.497734876567471, 0.8448901646162211, 0.3]
botanical_print_C[0].rotation = [0, 0, 0]
paperback_book_B[0].position = [5.0650292360862945, 0.9277417322928568, 0.1]
paperback_book_B[0].rotation = [0, 0, 0]
painting[0].position = [0.23034699223622035, 2.538180775961333, 0.375]
painting[0].rotation = [0, 0, 0]
wall_sconce_A[0].position = [4.62468862170636, 0.4373986622271568, 0.16]
wall_sconce_A[0].rotation = [0, 0, 0]
coffee_table_book_A[0].position = [4.778036684005156, 1.8943874462718964, 0.015]
coffee_table_book_A[0].rotation = [0, 0, 0]
floor_lamp[0].position = [0.09724231776792097, 3.740025864804257, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
paperback_book_A[0].position = [1.6465743210554422, 0.3934748292254743, 0.1]
paperback_book_A[0].rotation = [0, 0, 0]
wall_planter[0].position = [3.469744770104832, 1.6077307181246348, 0.175]
wall_planter[0].rotation = [0, 0, 0]
wall_sconce_B[0].position = [5.254295046725186, 3.228945685119996, 0.16]
wall_sconce_B[0].rotation = [0, 0, 0]
map_print[0].position = [1.4361328448443564, 1.0286634610509837, 0.325]
map_print[0].rotation = [0, 0, 0]
picture_frame[0].position = [2.2682953989667807, 1.847533822769523, 0.125]
picture_frame[0].rotation = [0, 0, 0]
mirror[0].position = [0.02434160515095135, 3.8459946829743923, 0.6]
mirror[0].rotation = [0, 0, 0]
coffee_table_book_B[0].position = [0.22050720473814428, 3.818065002462662, 0.02]
coffee_table_book_B[0].rotation = [0, 0, 0]
clock[0].position = [5.136267182472398, 1.097343499063643, 0.175]
clock[0].rotation = [0, 0, 0]
coffee_table_book_C[0].position = [5.448424120042668, 1.4478216779210606, 0.0175]
coffee_table_book_C[0].rotation = [0, 0, 0]
jar_candle_A[0].position = [1.6285221031569184, 2.6562837520880733, 0.055]
jar_candle_A[0].rotation = [0, 0, 0]
wall_sconce_C[0].position = [4.157647331504386, 0.27180904956157764, 0.16]
wall_sconce_C[0].rotation = [0, 0, 0]
remote[0].position = [0.9997004954665468, 1.593129467668185, 0.01]
remote[0].rotation = [0, 0, 0]
side_table[0].position = [5.420211352048314, 3.0739174294476803, 0.275]
side_table[0].rotation = [0, 0, 0]
botanical_print_A[0].position = [3.6595052554796292, 0.9501747258924401, 0.3]
botanical_print_A[0].rotation = [0, 0, 0]
wall_sconce_D[0].position = [2.6674185599507036, 0.7616838260881802, 0.16]
wall_sconce_D[0].rotation = [0, 0, 0]
jar_candle_B[0].position = [4.630653420713783, 0.5735698671115308, 0.055]
jar_candle_B[0].rotation = [0, 0, 0]
armchair[0].position = [4.786014858835115, 1.7486716755082337, 0.475]
armchair[0].rotation = [0, 0, 0]
remote_like_bar[0].position = [2.3485189350862408, 2.865901205208828, 0.0125]
remote_like_bar[0].rotation = [0, 0, 0]
set_top_box_router[0].position = [3.9155030824226214, 1.3162351684323799, 0.025]
set_top_box_router[0].rotation = [0, 0, 0]
coffee_table[0].position = [0.7460637691328871, 1.4684904807469423, 0.21]
coffee_table[0].rotation = [0, 0, 0]
media_console[0].position = [1.1314782696257442, 1.667228244451552, 0.3]
media_console[0].rotation = [0, 0, 0]
sofa[0].position = [5.4215820330599085, 1.4679836786415645, 0.44]
sofa[0].rotation = [0, 0, 0]
botanical_print_B[0].position = [1.427984859428749, 0.05746266975310732, 0.3]
botanical_print_B[0].rotation = [0, 0, 0]
botanical_print_C[0].position = [5.497734876567471, 0.8448901646162211, 0.3]
botanical_print_C[0].rotation = [0, 0, 0]
paperback_book_B[0].position = [5.0650292360862945, 0.9277417322928568, 0.1]
paperback_book_B[0].rotation = [0, 0, 0]
painting[0].position = [0.23034699223622035, 2.538180775961333, 0.375]
painting[0].rotation = [0, 0, 0]

solver.constraints = []

# Room-facing reference point used to orient wall-mounted decorations.
room_center = AssetInstance(position=[2.75, 2.25, 1.40])

# ---------------------------------------------------------------------------
# Initial furniture layout
# ---------------------------------------------------------------------------
# The sofa and media console form the main seating axis across the room.
sofa[0].position = [0.475, 2.50, 0.44]
sofa[0].rotation = [0, 0, radians(0)]

media_console[0].position = [5.29, 2.50, 0.30]
media_console[0].rotation = [0, 0, radians(180)]

coffee_table[0].position = [2.00, 2.50, 0.21]
coffee_table[0].rotation = [0, 0, radians(0)]

# The side table is beside the sofa. Their center distance is 1.42 m,
# corresponding to an approximately 0.08 m gap between bounding-box edges.
side_table[0].position = [0.55, 1.08, 0.275]
side_table[0].rotation = [0, 0, radians(0)]

# A separate reading corner is placed along the lower side of the room.
# The armchair faces directly toward the floor lamp.
armchair[0].position = [3.35, 0.70, 0.475]
armchair[0].rotation = [0, 0, radians(0)]

floor_lamp[0].position = [4.45, 0.70, 0.825]
floor_lamp[0].rotation = [0, 0, radians(180)]

# ---------------------------------------------------------------------------
# Objects supported by the coffee table
# ---------------------------------------------------------------------------
coffee_table_book_A[0].position = [1.82, 2.05, 0.435]
coffee_table_book_A[0].rotation = [0, 0, radians(0)]

coffee_table_book_B[0].position = [2.13, 2.02, 0.44]
coffee_table_book_B[0].rotation = [0, 0, radians(0)]

coffee_table_book_C[0].position = [1.82, 2.72, 0.44]
coffee_table_book_C[0].rotation = [0, 0, radians(0)]

remote[0].position = [2.15, 2.38, 0.43]
remote[0].rotation = [0, 0, radians(0)]

remote_like_bar[0].position = [2.13, 2.72, 0.435]
remote_like_bar[0].rotation = [0, 0, radians(0)]

jar_candle_B[0].position = [1.82, 2.38, 0.475]
jar_candle_B[0].rotation = [0, 0, radians(0)]

# ---------------------------------------------------------------------------
# Objects supported by the side table
# ---------------------------------------------------------------------------
picture_frame[0].position = [0.48, 0.96, 0.675]
picture_frame[0].rotation = [0, 0, radians(0)]

paperback_book_A[0].position = [0.70, 1.08, 0.65]
paperback_book_A[0].rotation = [0, 0, radians(0)]

jar_candle_A[0].position = [0.70, 0.82, 0.605]
jar_candle_A[0].rotation = [0, 0, radians(0)]

# ---------------------------------------------------------------------------
# Objects supported by the media console
# ---------------------------------------------------------------------------
set_top_box_router[0].position = [5.25, 2.15, 0.625]
set_top_box_router[0].rotation = [0, 0, radians(180)]

paperback_book_B[0].position = [5.25, 2.75, 0.70]
paperback_book_B[0].rotation = [0, 0, radians(180)]

# ---------------------------------------------------------------------------
# Wall-mounted decoration
# ---------------------------------------------------------------------------
# Four sconces and the smaller decorations are distributed along the top wall.
wall_sconce_A[0].position = [0.45, 4.44, 1.15]
wall_sconce_A[0].rotation = [0, 0, radians(-90)]

wall_sconce_B[0].position = [1.95, 4.44, 1.15]
wall_sconce_B[0].rotation = [0, 0, radians(-90)]

wall_sconce_C[0].position = [3.55, 4.44, 1.15]
wall_sconce_C[0].rotation = [0, 0, radians(-90)]

wall_sconce_D[0].position = [5.05, 4.44, 1.15]
wall_sconce_D[0].rotation = [0, 0, radians(-90)]

botanical_print_A[0].position = [1.20, 4.485, 1.90]
botanical_print_A[0].rotation = [0, 0, radians(-90)]

botanical_print_B[0].position = [2.75, 4.485, 1.90]
botanical_print_B[0].rotation = [0, 0, radians(-90)]

botanical_print_C[0].position = [4.30, 4.485, 1.90]
botanical_print_C[0].rotation = [0, 0, radians(-90)]

wall_planter[0].position = [2.75, 4.41, 0.72]
wall_planter[0].rotation = [0, 0, radians(-90)]

clock[0].position = [4.30, 4.475, 0.72]
clock[0].rotation = [0, 0, radians(-90)]

# The three large wall pieces are spaced across the opposite wall.
painting[0].position = [0.80, 0.02, 1.85]
painting[0].rotation = [0, 0, radians(90)]

map_print[0].position = [2.35, 0.015, 1.85]
map_print[0].rotation = [0, 0, radians(90)]

mirror[0].position = [4.10, 0.02, 1.70]
mirror[0].rotation = [0, 0, radians(90)]

# ---------------------------------------------------------------------------
# Furniture constraints
# ---------------------------------------------------------------------------
solver.against_wall(sofa[0], walls[3])
solver.point_towards(sofa[0], media_console[0])

solver.against_wall(media_console[0], walls[1])
solver.point_towards(media_console[0], sofa[0])

coffee_table_anchor = AssetInstance(position=[2.00, 2.50, 0.21])
solver.distance_constraint(
    coffee_table[0], coffee_table_anchor, 0, 0, weight=10
)
solver.align_with(coffee_table[0], sofa[0])

# The 1.42 m center distance accounts for the sofa and table half-widths,
# leaving their nearest bounding-box edges 0.08 m apart.
solver.distance_constraint(
    side_table[0], sofa[0], 1.42, 1.42, weight=10
)
side_table_anchor = AssetInstance(position=[0.55, 1.08, 0.275])
solver.distance_constraint(
    side_table[0], side_table_anchor, 0, 0, weight=10
)
solver.align_with(side_table[0], sofa[0])

armchair_anchor = AssetInstance(position=[3.35, 0.70, 0.475])
solver.distance_constraint(
    armchair[0], armchair_anchor, 0, 0, weight=10
)
solver.point_towards(armchair[0], floor_lamp[0])

floor_lamp_anchor = AssetInstance(position=[4.45, 0.70, 0.825])
solver.distance_constraint(
    floor_lamp[0], floor_lamp_anchor, 0, 0, weight=10
)
solver.point_towards(floor_lamp[0], armchair[0])

# ---------------------------------------------------------------------------
# Coffee-table object constraints
# ---------------------------------------------------------------------------
solver.on_top_of(coffee_table_book_A[0], coffee_table[0])
solver.distance_constraint(
    coffee_table_book_A[0],
    AssetInstance(position=[1.82, 2.05, 0.435]),
    0, 0, weight=10
)
solver.align_with(coffee_table_book_A[0], coffee_table[0])

solver.on_top_of(coffee_table_book_B[0], coffee_table[0])
solver.distance_constraint(
    coffee_table_book_B[0],
    AssetInstance(position=[2.13, 2.02, 0.44]),
    0, 0, weight=10
)
solver.align_with(coffee_table_book_B[0], coffee_table[0])

solver.on_top_of(coffee_table_book_C[0], coffee_table[0])
solver.distance_constraint(
    coffee_table_book_C[0],
    AssetInstance(position=[1.82, 2.72, 0.44]),
    0, 0, weight=10
)
solver.align_with(coffee_table_book_C[0], coffee_table[0])

solver.on_top_of(remote[0], coffee_table[0])
solver.distance_constraint(
    remote[0],
    AssetInstance(position=[2.15, 2.38, 0.43]),
    0, 0, weight=10
)
solver.align_with(remote[0], coffee_table[0])

solver.on_top_of(remote_like_bar[0], coffee_table[0])
solver.distance_constraint(
    remote_like_bar[0],
    AssetInstance(position=[2.13, 2.72, 0.435]),
    0, 0, weight=10
)
solver.align_with(remote_like_bar[0], coffee_table[0])

solver.on_top_of(jar_candle_B[0], coffee_table[0])
solver.distance_constraint(
    jar_candle_B[0],
    AssetInstance(position=[1.82, 2.38, 0.475]),
    0, 0, weight=10
)
solver.align_with(jar_candle_B[0], coffee_table[0])

# ---------------------------------------------------------------------------
# Side-table object constraints
# ---------------------------------------------------------------------------
solver.on_top_of(picture_frame[0], side_table[0])
solver.distance_constraint(
    picture_frame[0],
    AssetInstance(position=[0.48, 0.96, 0.675]),
    0, 0, weight=10
)
solver.align_with(picture_frame[0], side_table[0])

solver.on_top_of(paperback_book_A[0], side_table[0])
solver.distance_constraint(
    paperback_book_A[0],
    AssetInstance(position=[0.70, 1.08, 0.65]),
    0, 0, weight=10
)
solver.align_with(paperback_book_A[0], side_table[0])

solver.on_top_of(jar_candle_A[0], side_table[0])
solver.distance_constraint(
    jar_candle_A[0],
    AssetInstance(position=[0.70, 0.82, 0.605]),
    0, 0, weight=10
)
solver.align_with(jar_candle_A[0], side_table[0])

# ---------------------------------------------------------------------------
# Media-console object constraints
# ---------------------------------------------------------------------------
solver.on_top_of(set_top_box_router[0], media_console[0])
solver.distance_constraint(
    set_top_box_router[0],
    AssetInstance(position=[5.25, 2.15, 0.625]),
    0, 0, weight=10
)
solver.align_with(set_top_box_router[0], media_console[0])

solver.on_top_of(paperback_book_B[0], media_console[0])
solver.distance_constraint(
    paperback_book_B[0],
    AssetInstance(position=[5.25, 2.75, 0.70]),
    0, 0, weight=10
)
solver.align_with(paperback_book_B[0], media_console[0])

# ---------------------------------------------------------------------------
# Top-wall constraints
# ---------------------------------------------------------------------------
solver.against_wall(wall_sconce_A[0], walls[2])
solver.point_towards(wall_sconce_A[0], room_center)

solver.against_wall(wall_sconce_B[0], walls[2])
solver.point_towards(wall_sconce_B[0], room_center)

solver.against_wall(wall_sconce_C[0], walls[2])
solver.point_towards(wall_sconce_C[0], room_center)

solver.against_wall(wall_sconce_D[0], walls[2])
solver.point_towards(wall_sconce_D[0], room_center)

solver.against_wall(botanical_print_A[0], walls[2])
solver.point_towards(botanical_print_A[0], room_center)

solver.against_wall(botanical_print_B[0], walls[2])
solver.point_towards(botanical_print_B[0], room_center)

solver.against_wall(botanical_print_C[0], walls[2])
solver.point_towards(botanical_print_C[0], room_center)

solver.against_wall(wall_planter[0], walls[2])
solver.point_towards(wall_planter[0], room_center)

solver.against_wall(clock[0], walls[2])
solver.point_towards(clock[0], room_center)

# ---------------------------------------------------------------------------
# Bottom-wall constraints
# ---------------------------------------------------------------------------
solver.against_wall(painting[0], walls[0])
solver.point_towards(painting[0], room_center)

solver.against_wall(map_print[0], walls[0])
solver.point_towards(map_print[0], room_center)

solver.against_wall(mirror[0], walls[0])
solver.point_towards(mirror[0], room_center)

solver.constraints = []
wall_planter[0].position = [2.75, 4.4101128578186035, 0.17499999701976776]
wall_planter[0].rotation = [0, 0, -1.570903939614338]
wall_planter[0].optimize = 2
paperback_book_A[0].position = [0.699999988079071, 1.0800000429153442, 0.6500000357627869]
paperback_book_A[0].rotation = [0, 0, -1.4824782555879654e-05]
paperback_book_A[0].optimize = 2
mirror[0].position = [4.099999904632568, 0.02009398862719536, 0.6000000238418579]
mirror[0].rotation = [0, 0, 1.5706886917867395]
mirror[0].optimize = 2
wall_sconce_D[0].position = [5.050000190734863, 4.440131664276123, 0.1599999964237213]
wall_sconce_D[0].rotation = [0, 0, -1.5709039559363296]
wall_sconce_D[0].optimize = 2
paperback_book_B[0].position = [5.25, 2.75, 0.7000000476837158]
paperback_book_B[0].rotation = [0, 0, -3.1407572212255426]
paperback_book_B[0].optimize = 2
botanical_print_C[0].position = [4.300000190734863, 4.484995365142822, 0.30000001192092896]
botanical_print_C[0].rotation = [0, 0, -1.5709039777352074]
botanical_print_C[0].optimize = 2
media_console[0].position = [5.290225982666016, 2.5, 0.30000001192092896]
media_console[0].rotation = [0, 0, 3.141463576826251]
media_console[0].optimize = 2
picture_frame[0].position = [0.47999998927116394, 0.9599999785423279, 0.675000011920929]
picture_frame[0].rotation = [0, 0, -1.4824782555879654e-05]
picture_frame[0].optimize = 2
set_top_box_router[0].position = [5.25, 2.1500000953674316, 0.625]
set_top_box_router[0].rotation = [0, 0, -3.1407572212255426]
set_top_box_router[0].optimize = 2
botanical_print_A[0].position = [1.2000000476837158, 4.484995365142822, 0.30000001192092896]
botanical_print_A[0].rotation = [0, 0, -1.5709039777352074]
botanical_print_A[0].optimize = 2
clock[0].position = [4.300000190734863, 4.474904537200928, 0.17499999701976776]
clock[0].rotation = [0, 0, -1.570903978797661]
clock[0].optimize = 2
botanical_print_B[0].position = [2.75, 4.484995365142822, 0.30000001192092896]
botanical_print_B[0].rotation = [0, 0, -1.5709039777352074]
botanical_print_B[0].optimize = 2
coffee_table_book_B[0].position = [2.130000114440918, 2.0199999809265137, 0.4399999976158142]
coffee_table_book_B[0].rotation = [0, 0, 0.00037968898351664257]
coffee_table_book_B[0].optimize = 2
armchair[0].position = [3.3499999046325684, 0.699999988079071, 0.4749999940395355]
armchair[0].rotation = [0, 0, 0.01256637125682779]
armchair[0].optimize = 2
wall_sconce_C[0].position = [3.549999952316284, 4.440131664276123, 0.1599999964237213]
wall_sconce_C[0].rotation = [0, 0, -1.5709039559363296]
wall_sconce_C[0].optimize = 2
painting[0].position = [0.800000011920929, 0.020094066858291626, 0.375]
painting[0].rotation = [0, 0, 1.5706887093810489]
painting[0].optimize = 2
sofa[0].position = [0.4750375747680664, 2.5, 0.4399999976158142]
sofa[0].rotation = [0, 0, 0.00023936204178441264]
sofa[0].optimize = 2
jar_candle_A[0].position = [0.6992278099060059, 0.8445712327957153, 0.6050000190734863]
jar_candle_A[0].rotation = [0, 0, -1.4824782555879654e-05]
jar_candle_A[0].optimize = 2
map_print[0].position = [2.3499999046325684, 0.0149264270439744, 0.32499998807907104]
map_print[0].rotation = [0, 0, 1.5706886934944124]
map_print[0].optimize = 2
remote_like_bar[0].position = [2.130000114440918, 2.7200000286102295, 0.4349999725818634]
remote_like_bar[0].rotation = [0, 0, 0.00037968898351664257]
remote_like_bar[0].optimize = 2
remote[0].position = [2.1500000953674316, 2.380000114440918, 0.429999977350235]
remote[0].rotation = [0, 0, 0.00037968898351664257]
remote[0].optimize = 2
wall_sconce_A[0].position = [0.44999998807907104, 4.440131664276123, 0.1599999964237213]
wall_sconce_A[0].rotation = [0, 0, -1.5709039559363296]
wall_sconce_A[0].optimize = 2
coffee_table[0].position = [2.0, 2.5, 0.20999999344348907]
coffee_table[0].rotation = [0, 0, 0.0005974915835269839]
coffee_table[0].optimize = 2
coffee_table_book_C[0].position = [1.8200000524520874, 2.7200000286102295, 0.4399999976158142]
coffee_table_book_C[0].rotation = [0, 0, 0.00037968898351664257]
coffee_table_book_C[0].optimize = 2
jar_candle_B[0].position = [1.8200000524520874, 2.380000114440918, 0.4749999940395355]
jar_candle_B[0].rotation = [0, 0, 0.00037968898351664257]
jar_candle_B[0].optimize = 2
floor_lamp[0].position = [4.449999809265137, 0.699999988079071, 0.824999988079071]
floor_lamp[0].rotation = [0, 0, -3.1290262823329655]
floor_lamp[0].optimize = 2
coffee_table_book_A[0].position = [1.8200000524520874, 2.049999952316284, 0.4349999725818634]
coffee_table_book_A[0].rotation = [0, 0, 0.00037968898351664257]
coffee_table_book_A[0].optimize = 2
wall_sconce_B[0].position = [1.9500000476837158, 4.440131664276123, 0.1599999964237213]
wall_sconce_B[0].rotation = [0, 0, -1.5709039559363296]
wall_sconce_B[0].optimize = 2
side_table[0].position = [0.550000011920929, 1.0800000429153442, 0.2750000059604645]
side_table[0].rotation = [0, 0, -0.0009218264692233955]
side_table[0].optimize = 2

