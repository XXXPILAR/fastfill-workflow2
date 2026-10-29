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
wall_sconce_A = Assets(description="wall sconce", size=[0.22, 0.16, 0.32], placements=[AssetInstance() for _ in range(1)])
coffee_table_book_A = Assets(description="coffee table book", size=[0.32, 0.25, 0.04], placements=[AssetInstance() for _ in range(1)])
floor_lamp = Assets(description="floor lamp", size=[0.42, 0.42, 1.65], placements=[AssetInstance() for _ in range(1)])
paperback_book_A = Assets(description="paperback book", size=[0.20, 0.13, 0.03], placements=[AssetInstance() for _ in range(1)])
wall_planter = Assets(description="wall planter", size=[0.20, 0.28, 0.35], placements=[AssetInstance() for _ in range(1)])
wall_sconce_B = Assets(description="wall sconce", size=[0.22, 0.16, 0.32], placements=[AssetInstance() for _ in range(1)])
map_print = Assets(description="map print", size=[0.03, 0.80, 0.60], placements=[AssetInstance() for _ in range(1)])
picture_frame = Assets(description="picture frame", size=[0.10, 0.18, 0.23], placements=[AssetInstance() for _ in range(1)])
mirror = Assets(description="mirror", size=[0.04, 0.75, 1.00], placements=[AssetInstance() for _ in range(1)])
coffee_table_book_B = Assets(description="coffee table book", size=[0.30, 0.24, 0.03], placements=[AssetInstance() for _ in range(1)])
clock = Assets(description="clock", size=[0.05, 0.32, 0.32], placements=[AssetInstance() for _ in range(1)])
coffee_table_book_C = Assets(description="coffee table book", size=[0.33, 0.26, 0.04], placements=[AssetInstance() for _ in range(1)])
jar_candle_A = Assets(description="jar candle", size=[0.09, 0.09, 0.12], placements=[AssetInstance() for _ in range(1)])
wall_sconce_C = Assets(description="wall sconce", size=[0.22, 0.16, 0.32], placements=[AssetInstance() for _ in range(1)])
remote = Assets(description="remote", size=[0.19, 0.05, 0.03], placements=[AssetInstance() for _ in range(1)])
side_table = Assets(description="side table", size=[0.48, 0.48, 0.55], placements=[AssetInstance() for _ in range(1)])
botanical_print_A = Assets(description="botanical print", size=[0.03, 0.40, 0.50], placements=[AssetInstance() for _ in range(1)])
wall_sconce_D = Assets(description="wall sconce", size=[0.22, 0.16, 0.32], placements=[AssetInstance() for _ in range(1)])
jar_candle_B = Assets(description="jar candle", size=[0.08, 0.08, 0.10], placements=[AssetInstance() for _ in range(1)])
armchair = Assets(description="armchair", size=[0.90, 0.85, 0.90], placements=[AssetInstance() for _ in range(1)])
remote_like_bar = Assets(description="remote like bar", size=[0.17, 0.04, 0.02], placements=[AssetInstance() for _ in range(1)])
set_top_box_router = Assets(description="set top box router", size=[0.18, 0.24, 0.05], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="coffee table", size=[0.65, 1.20, 0.42], placements=[AssetInstance() for _ in range(1)])
media_console = Assets(description="media console", size=[0.42, 1.80, 0.55], placements=[AssetInstance() for _ in range(1)])
sofa = Assets(description="sofa", size=[0.95, 2.25, 0.85], placements=[AssetInstance() for _ in range(1)])
botanical_print_B = Assets(description="botanical print", size=[0.03, 0.40, 0.50], placements=[AssetInstance() for _ in range(1)])
botanical_print_C = Assets(description="botanical print", size=[0.03, 0.40, 0.50], placements=[AssetInstance() for _ in range(1)])
paperback_book_B = Assets(description="paperback book", size=[0.20, 0.13, 0.03], placements=[AssetInstance() for _ in range(1)])
painting = Assets(description="painting", size=[0.04, 1.20, 0.80], placements=[AssetInstance() for _ in range(1)])

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

wall_sconce_A[0].position = [3.1733074646061223, 2.912256044944999, 0.16]
wall_sconce_A[0].rotation = [0, 0, 0]
coffee_table_book_A[0].position = [4.019653310860599, 3.835206559493642, 0.0175]
coffee_table_book_A[0].rotation = [0, 0, 0]
floor_lamp[0].position = [4.262119787570998, 2.2879700292908987, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
paperback_book_A[0].position = [4.6371949955227665, 4.241523910539923, 0.0125]
paperback_book_A[0].rotation = [0, 0, 0]
wall_planter[0].position = [1.8295655337789158, 1.5877740606391546, 0.175]
wall_planter[0].rotation = [0, 0, 0]
wall_sconce_B[0].position = [4.699581939510414, 1.267288037135576, 0.16]
wall_sconce_B[0].rotation = [0, 0, 0]
map_print[0].position = [0.32353515779500913, 0.7188760547588845, 0.3]
map_print[0].rotation = [0, 0, 0]
picture_frame[0].position = [1.2304503849432056, 2.3607188098150615, 0.115]
picture_frame[0].rotation = [0, 0, 0]
mirror[0].position = [1.4773919279394814, 3.4071947169479264, 0.5]
mirror[0].rotation = [0, 0, 0]
coffee_table_book_B[0].position = [0.37035174675076227, 2.739538831582504, 0.015]
coffee_table_book_B[0].rotation = [0, 0, 0]
clock[0].position = [1.1078517571422506, 3.2368064330455737, 0.16]
clock[0].rotation = [0, 0, 0]
coffee_table_book_C[0].position = [1.9169827348327484, 0.7299578905000368, 0.02]
coffee_table_book_C[0].rotation = [0, 0, 0]
jar_candle_A[0].position = [3.6518894141120515, 2.1151796196314763, 0.06]
jar_candle_A[0].rotation = [0, 0, 0]
wall_sconce_C[0].position = [4.495351671956941, 2.5819622992804234, 0.16]
wall_sconce_C[0].rotation = [0, 0, 0]
remote[0].position = [3.3662319944158545, 3.760970453076925, 0.0125]
remote[0].rotation = [0, 0, 0]
side_table[0].position = [3.3726562574438375, 1.972593859783725, 0.275]
side_table[0].rotation = [0, 0, 0]
botanical_print_A[0].position = [4.883262344926916, 4.434393091443161, 0.25]
botanical_print_A[0].rotation = [0, 0, 0]
wall_sconce_D[0].position = [3.3880123192328178, 2.8341462863049016, 0.16]
wall_sconce_D[0].rotation = [0, 0, 0]
jar_candle_B[0].position = [1.7191628305099238, 1.1315133300369484, 0.05]
jar_candle_B[0].rotation = [0, 0, 0]
armchair[0].position = [4.771086074779026, 3.1953764103926536, 0.45]
armchair[0].rotation = [0, 0, 0]
remote_like_bar[0].position = [1.2765984401737285, 0.9721267267750802, 0.01]
remote_like_bar[0].rotation = [0, 0, 0]
set_top_box_router[0].position = [5.295100323491203, 2.2737035138917525, 0.025]
set_top_box_router[0].rotation = [0, 0, 0]
coffee_table[0].position = [4.670349297952507, 1.380120445901981, 0.21]
coffee_table[0].rotation = [0, 0, 0]
media_console[0].position = [0.10391366963004894, 3.5181818895235857, 0.275]
media_console[0].rotation = [0, 0, 0]
sofa[0].position = [1.491761517017286, 3.113277526712196, 0.425]
sofa[0].rotation = [0, 0, 0]
botanical_print_B[0].position = [1.7187437877640517, 0.3850390472296369, 0.25]
botanical_print_B[0].rotation = [0, 0, 0]
botanical_print_C[0].position = [0.3241161422207667, 2.847367260326025, 0.25]
botanical_print_C[0].rotation = [0, 0, 0]
paperback_book_B[0].position = [3.2594329365042087, 2.9781719858353024, 0.0125]
paperback_book_B[0].rotation = [0, 0, 0]
painting[0].position = [0.676841058044996, 4.348625865953301, 0.4]
painting[0].rotation = [0, 0, 0]
wall_sconce_A[0].position = [3.1733074646061223, 2.912256044944999, 0.16]
wall_sconce_A[0].rotation = [0, 0, 0]
coffee_table_book_A[0].position = [4.019653310860599, 3.835206559493642, 0.0175]
coffee_table_book_A[0].rotation = [0, 0, 0]
floor_lamp[0].position = [4.262119787570998, 2.2879700292908987, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
paperback_book_A[0].position = [4.6371949955227665, 4.241523910539923, 0.0125]
paperback_book_A[0].rotation = [0, 0, 0]
wall_planter[0].position = [1.8295655337789158, 1.5877740606391546, 0.175]
wall_planter[0].rotation = [0, 0, 0]
wall_sconce_B[0].position = [4.699581939510414, 1.267288037135576, 0.16]
wall_sconce_B[0].rotation = [0, 0, 0]
map_print[0].position = [0.32353515779500913, 0.7188760547588845, 0.3]
map_print[0].rotation = [0, 0, 0]
picture_frame[0].position = [1.2304503849432056, 2.3607188098150615, 0.115]
picture_frame[0].rotation = [0, 0, 0]
mirror[0].position = [1.4773919279394814, 3.4071947169479264, 0.5]
mirror[0].rotation = [0, 0, 0]
coffee_table_book_B[0].position = [0.37035174675076227, 2.739538831582504, 0.015]
coffee_table_book_B[0].rotation = [0, 0, 0]
clock[0].position = [1.1078517571422506, 3.2368064330455737, 0.16]
clock[0].rotation = [0, 0, 0]
coffee_table_book_C[0].position = [1.9169827348327484, 0.7299578905000368, 0.02]
coffee_table_book_C[0].rotation = [0, 0, 0]
jar_candle_A[0].position = [3.6518894141120515, 2.1151796196314763, 0.06]
jar_candle_A[0].rotation = [0, 0, 0]
wall_sconce_C[0].position = [4.495351671956941, 2.5819622992804234, 0.16]
wall_sconce_C[0].rotation = [0, 0, 0]
remote[0].position = [3.3662319944158545, 3.760970453076925, 0.0125]
remote[0].rotation = [0, 0, 0]
side_table[0].position = [3.3726562574438375, 1.972593859783725, 0.275]
side_table[0].rotation = [0, 0, 0]
botanical_print_A[0].position = [4.883262344926916, 4.434393091443161, 0.25]
botanical_print_A[0].rotation = [0, 0, 0]
wall_sconce_D[0].position = [3.3880123192328178, 2.8341462863049016, 0.16]
wall_sconce_D[0].rotation = [0, 0, 0]
jar_candle_B[0].position = [1.7191628305099238, 1.1315133300369484, 0.05]
jar_candle_B[0].rotation = [0, 0, 0]
armchair[0].position = [4.771086074779026, 3.1953764103926536, 0.45]
armchair[0].rotation = [0, 0, 0]
remote_like_bar[0].position = [1.2765984401737285, 0.9721267267750802, 0.01]
remote_like_bar[0].rotation = [0, 0, 0]
set_top_box_router[0].position = [5.295100323491203, 2.2737035138917525, 0.025]
set_top_box_router[0].rotation = [0, 0, 0]
coffee_table[0].position = [4.670349297952507, 1.380120445901981, 0.21]
coffee_table[0].rotation = [0, 0, 0]
media_console[0].position = [0.10391366963004894, 3.5181818895235857, 0.275]
media_console[0].rotation = [0, 0, 0]
sofa[0].position = [1.491761517017286, 3.113277526712196, 0.425]
sofa[0].rotation = [0, 0, 0]
botanical_print_B[0].position = [1.7187437877640517, 0.3850390472296369, 0.25]
botanical_print_B[0].rotation = [0, 0, 0]
botanical_print_C[0].position = [0.3241161422207667, 2.847367260326025, 0.25]
botanical_print_C[0].rotation = [0, 0, 0]
paperback_book_B[0].position = [3.2594329365042087, 2.9781719858353024, 0.0125]
paperback_book_B[0].rotation = [0, 0, 0]
painting[0].position = [0.676841058044996, 4.348625865953301, 0.4]
painting[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the supplied boundary: x=0..5.50, y=0..4.50.
# Positions are bounding-box centers. Fixed-point constraints preserve the
# deliberately separated footprints, tabletop arrangements, and mounting heights.
def place_asset(asset_group, xyz, yaw=0, facing=None):
    instance = asset_group[0]
    instance.position = list(xyz)
    instance.rotation = [0, 0, radians(yaw)]
    solver.distance_constraint(
        instance, AssetInstance(position=list(xyz)), 0, 0, weight=10
    )
    if facing is not None:
        solver.point_towards(instance, facing)
    else:
        solver.align_with(
            instance,
            AssetInstance(position=list(xyz), rotation=[0, 0, radians(yaw)]),
            angle=0,
        )


# Main furniture: sofa faces the opposite-wall console, with the coffee
# table in reach and a generous circulation route on its eastern side.
place_asset(media_console, [5.29, 2.20, 0.275], 180)
solver.against_wall(media_console[0], walls[1])

place_asset(sofa, [0.60, 2.20, 0.425])
place_asset(coffee_table, [2.00, 2.20, 0.210])
solver.point_towards(sofa[0], media_console[0])
solver.point_towards(media_console[0], sofa[0])
solver.align_with(coffee_table[0], sofa[0])
solver.distance_constraint(coffee_table[0], sofa[0], 1.35, 1.50, weight=10)

# The side table has a 0.05 m edge-to-edge gap from the sofa's northern end.
# distance_constraint measures 3D center distance, NOT the edge clearance:
# horizontal separation = 2.25/2 + 0.48/2 + 0.05 = 1.415 m.
place_asset(side_table, [0.60, 3.615, 0.275])
solver.distance_constraint(
    side_table[0], sofa[0],
    (1.415**2 + 0.150**2)**0.5,
    (1.465**2 + 0.150**2)**0.5,
    weight=10,
)
solver.align_with(side_table[0], sofa[0])

# Separate reading area; the armchair explicitly faces the floor lamp.
place_asset(floor_lamp, [4.65, 3.65, 0.825], 180)
place_asset(armchair, [3.60, 3.65, 0.450], facing=floor_lamp[0])
solver.distance_constraint(armchair[0], floor_lamp[0], 1.10, 1.13, weight=10)
solver.point_towards(floor_lamp[0], armchair[0])

# Coffee-table objects: one two-book stack, a separate book, and clear
# non-overlapping spaces for the remote and candle.
place_asset(coffee_table_book_A, [1.90, 1.85, 0.440])
solver.on_top_of(coffee_table_book_A[0], coffee_table[0])
solver.align_with(coffee_table_book_A[0], coffee_table[0])

place_asset(coffee_table_book_B, [1.90, 1.85, 0.475])
solver.on_top_of(coffee_table_book_B[0], coffee_table_book_A[0])
solver.align_with(coffee_table_book_B[0], coffee_table_book_A[0])

place_asset(coffee_table_book_C, [2.00, 2.50, 0.440])
solver.on_top_of(coffee_table_book_C[0], coffee_table[0])
solver.align_with(coffee_table_book_C[0], coffee_table[0])

place_asset(remote, [2.00, 2.15, 0.435])
solver.on_top_of(remote[0], coffee_table[0])
solver.align_with(remote[0], coffee_table[0])

place_asset(jar_candle_A, [2.24, 2.05, 0.480])
solver.on_top_of(jar_candle_A[0], coffee_table[0])

# Side-table accessories fit wholly inside its 0.48 m square surface.
place_asset(paperback_book_A, [0.55, 3.62, 0.565])
solver.on_top_of(paperback_book_A[0], side_table[0])
solver.align_with(paperback_book_A[0], side_table[0])

place_asset(jar_candle_B, [0.76, 3.75, 0.600])
solver.on_top_of(jar_candle_B[0], side_table[0])

# Console accessories occupy separate stretches of the console top.
place_asset(set_top_box_router, [5.29, 1.65, 0.575], 180)
solver.on_top_of(set_top_box_router[0], media_console[0])
solver.align_with(set_top_box_router[0], media_console[0])

place_asset(remote_like_bar, [5.29, 2.15, 0.560], 180)
solver.on_top_of(remote_like_bar[0], media_console[0])
solver.align_with(remote_like_bar[0], media_console[0])

place_asset(picture_frame, [5.29, 2.65, 0.665], 180)
solver.on_top_of(picture_frame[0], media_console[0])
solver.align_with(picture_frame[0], media_console[0])

place_asset(paperback_book_B, [5.29, 2.98, 0.565], 180)
solver.on_top_of(paperback_book_B[0], media_console[0])
solver.align_with(paperback_book_B[0], media_console[0])

# Wall-mounted items are supported by their walls rather than by furniture.
# Their fixed-point constraints retain their mounting heights; their shallow
# local x dimensions are perpendicular to the selected wall.

# West wall: painting above the sofa, flanked by sconces.
place_asset(painting, [0.020, 2.20, 1.85])
solver.against_wall(painting[0], walls[3])

place_asset(wall_sconce_A, [0.110, 1.20, 1.85])
solver.against_wall(wall_sconce_A[0], walls[3])

place_asset(wall_sconce_B, [0.110, 3.20, 1.85])
solver.against_wall(wall_sconce_B[0], walls[3])

# East wall: mirror above the console, with sconces beyond its sides.
place_asset(mirror, [5.480, 2.20, 1.70], 180)
solver.against_wall(mirror[0], walls[1])

place_asset(wall_sconce_C, [5.390, 0.90, 1.90], 180)
solver.against_wall(wall_sconce_C[0], walls[1])

place_asset(wall_sconce_D, [5.390, 3.50, 1.90], 180)
solver.against_wall(wall_sconce_D[0], walls[1])

# North wall: inward-facing gallery, with gaps between every frame.
place_asset(map_print, [2.10, 4.485, 1.80], -90)
solver.against_wall(map_print[0], walls[2])

place_asset(botanical_print_A, [0.80, 4.485, 1.70], -90)
solver.against_wall(botanical_print_A[0], walls[2])

place_asset(botanical_print_B, [3.10, 4.485, 1.70], -90)
solver.against_wall(botanical_print_B[0], walls[2])

place_asset(botanical_print_C, [3.70, 4.485, 1.70], -90)
solver.against_wall(botanical_print_C[0], walls[2])

# South wall: elevated planter and clock leave the floor route unobstructed.
place_asset(wall_planter, [1.20, 0.100, 1.65], 90)
solver.against_wall(wall_planter[0], walls[0])

place_asset(clock, [3.00, 0.025, 1.80], 90)
solver.against_wall(clock[0], walls[0])

solver.constraints = []
wall_sconce_B[0].position = [0.10027995705604553, 3.200000047683716, 0.1599999964237213]
wall_sconce_B[0].rotation = [0, 0, 0.002540922439204702]
wall_sconce_B[0].optimize = 2
side_table[0].position = [0.6000000238418579, 3.625, 0.2750000059604645]
side_table[0].rotation = [0, 0, 0.035473676517363766]
side_table[0].optimize = 2
map_print[0].position = [2.0999999046325684, 4.492923259735107, 0.30000001192092896]
map_print[0].rotation = [0, 0, -1.5682554107885098]
map_print[0].optimize = 2
armchair[0].position = [3.5899999141693115, 3.6500000953674316, 0.44999998807907104]
armchair[0].rotation = [0, 0, 0.0157079639172164]
armchair[0].optimize = 2
remote[0].position = [2.0, 2.1500000953674316, 0.4349999725818634]
remote[0].rotation = [0, 0, 0.02596317240847523]
remote[0].optimize = 2
wall_sconce_C[0].position = [5.39972448348999, 0.8999999761581421, 0.1599999964237213]
wall_sconce_C[0].rotation = [0, 0, -3.139051732072762]
wall_sconce_C[0].optimize = 2
sofa[0].position = [0.6000000238418579, 2.200000047683716, 0.42500001192092896]
sofa[0].rotation = [0, 0, 0.02827433441159227]
sofa[0].optimize = 2
paperback_book_A[0].position = [0.550000011920929, 3.619999885559082, 0.5649999976158142]
paperback_book_A[0].rotation = [0, 0, 0.025961558158328533]
paperback_book_A[0].optimize = 2
botanical_print_A[0].position = [0.800000011920929, 4.493266582489014, 0.25]
botanical_print_A[0].rotation = [0, 0, -1.5682554052778654]
botanical_print_A[0].optimize = 2
painting[0].position = [0.02152448147535324, 2.200000047683716, 0.4000000059604645]
painting[0].rotation = [0, 0, 0.0025409114179187954]
painting[0].optimize = 2
paperback_book_B[0].position = [5.289999961853027, 2.9800000190734863, 0.5649999976158142]
paperback_book_B[0].rotation = [0, 0, -3.115629214321287]
paperback_book_B[0].optimize = 2
jar_candle_B[0].position = [0.7599999904632568, 3.75, 0.6000000238418579]
jar_candle_B[0].rotation = [0, 0, 0.01256637125682779]
jar_candle_B[0].optimize = 2
wall_sconce_A[0].position = [0.10027995705604553, 1.2000000476837158, 0.1599999964237213]
wall_sconce_A[0].rotation = [0, 0, 0.002540922439204702]
wall_sconce_A[0].optimize = 2
botanical_print_B[0].position = [3.0999999046325684, 4.493266582489014, 0.25]
botanical_print_B[0].rotation = [0, 0, -1.5682554052778654]
botanical_print_B[0].optimize = 2
wall_sconce_D[0].position = [5.39972448348999, 3.5, 0.1599999964237213]
wall_sconce_D[0].rotation = [0, 0, -3.139051732072762]
wall_sconce_D[0].optimize = 2
coffee_table_book_B[0].position = [1.899999976158142, 1.850000023841858, 0.4749999940395355]
coffee_table_book_B[0].rotation = [0, 0, 0.02596015015729436]
coffee_table_book_B[0].optimize = 2
coffee_table_book_C[0].position = [2.0, 2.5, 0.4399999976158142]
coffee_table_book_C[0].rotation = [0, 0, 0.02596317240847523]
coffee_table_book_C[0].optimize = 2
coffee_table_book_A[0].position = [1.899999976158142, 1.850000023841858, 0.4399999976158142]
coffee_table_book_A[0].rotation = [0, 0, 0.03230756527287115]
coffee_table_book_A[0].optimize = 2
clock[0].position = [3.0, 0.01612480729818344, 0.1599999964237213]
clock[0].rotation = [0, 0, 1.573337248311928]
clock[0].optimize = 2
set_top_box_router[0].position = [5.289999961853027, 1.649999976158142, 0.574999988079071]
set_top_box_router[0].rotation = [0, 0, -3.115629214321287]
set_top_box_router[0].optimize = 2
coffee_table[0].position = [2.0, 2.200000047683716, 0.20999999344348907]
coffee_table[0].rotation = [0, 0, 0.027430257831693807]
coffee_table[0].optimize = 2
picture_frame[0].position = [5.289999961853027, 2.6500000953674316, 0.6650000214576721]
picture_frame[0].rotation = [0, 0, -3.115629214321287]
picture_frame[0].optimize = 2
mirror[0].position = [5.488697052001953, 2.200000047683716, 0.5]
mirror[0].rotation = [0, 0, -3.1390517363613077]
mirror[0].optimize = 2
media_console[0].position = [5.260631561279297, 2.200000047683716, 0.2750000059604645]
media_console[0].rotation = [0, 0, -3.1079412963154582]
media_console[0].optimize = 2
wall_planter[0].position = [1.2000000476837158, 0.10035541653633118, 0.17499999701976776]
wall_planter[0].rotation = [0, 0, 1.5733372473897544]
wall_planter[0].optimize = 2
botanical_print_C[0].position = [3.700000047683716, 4.493266582489014, 0.25]
botanical_print_C[0].rotation = [0, 0, -1.5682554052778654]
botanical_print_C[0].optimize = 2
jar_candle_A[0].position = [2.240000009536743, 2.049999952316284, 0.47999998927116394]
jar_candle_A[0].rotation = [0, 0, 0.01256637125682779]
jar_candle_A[0].optimize = 2
floor_lamp[0].position = [4.650000095367432, 3.6500000953674316, 0.824999988079071]
floor_lamp[0].rotation = [0, 0, -3.122743098190977]
floor_lamp[0].optimize = 2
remote_like_bar[0].position = [5.289999961853027, 2.1500000953674316, 0.5600000023841858]
remote_like_bar[0].rotation = [0, 0, -3.115629214321287]
remote_like_bar[0].optimize = 2

