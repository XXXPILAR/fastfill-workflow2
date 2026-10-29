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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[5.00, 0.00, 0.00]),
    Wall(corner1=[5.00, 0.00, 0.00], corner2=[5.00, 4.00, 0.00]),
    Wall(corner1=[5.00, 4.00, 0.00], corner2=[0.00, 4.00, 0.00]),
    Wall(corner1=[0.00, 4.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
dining_chair_A = Assets(description="dining chair", size=[0.55, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
storage_box = Assets(description="storage box", size=[0.30, 0.38, 0.24], placements=[AssetInstance() for _ in range(1)])
print_A = Assets(description="print", size=[0.03, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])
wall_sconce_A = Assets(description="wall sconce", size=[0.20, 0.15, 0.30], placements=[AssetInstance() for _ in range(1)])
sideboard_cabinet = Assets(description="sideboard cabinet", size=[0.45, 1.60, 0.80], placements=[AssetInstance() for _ in range(1)])
glass_tumbler_A = Assets(description="glass tumbler", size=[0.08, 0.08, 0.11], placements=[AssetInstance() for _ in range(1)])
hardcover_book_A = Assets(description="hardcover book", size=[0.28, 0.22, 0.04], placements=[AssetInstance() for _ in range(1)])
wall_clock = Assets(description="wall clock", size=[0.04, 0.32, 0.32], placements=[AssetInstance() for _ in range(1)])
print_B = Assets(description="print", size=[0.03, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])
woven_linen_placemat_A = Assets(description="woven linen placemat", size=[0.32, 0.45, 0.00], placements=[AssetInstance() for _ in range(1)])
painting = Assets(description="painting", size=[0.04, 0.90, 0.65], placements=[AssetInstance() for _ in range(1)])
cylinder_vase = Assets(description="cylinder vase", size=[0.12, 0.12, 0.28], placements=[AssetInstance() for _ in range(1)])
dining_table = Assets(description="dining table", size=[0.90, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
bar_cart = Assets(description="bar cart", size=[0.40, 0.75, 0.85], placements=[AssetInstance() for _ in range(1)])
wall_sconce_B = Assets(description="wall sconce", size=[0.20, 0.15, 0.30], placements=[AssetInstance() for _ in range(1)])
eucalyptus_stem_A = Assets(description="eucalyptus stem", size=[0.15, 0.22, 0.65], placements=[AssetInstance() for _ in range(1)])
entry_bench = Assets(description="entry bench", size=[0.38, 1.10, 0.45], placements=[AssetInstance() for _ in range(1)])
art_print = Assets(description="art print", size=[0.03, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
floor_lamp = Assets(description="floor lamp", size=[0.38, 0.38, 1.60], placements=[AssetInstance() for _ in range(1)])
hardcover_book_B = Assets(description="hardcover book", size=[0.26, 0.20, 0.03], placements=[AssetInstance() for _ in range(1)])
hardcover_book_C = Assets(description="hardcover book", size=[0.24, 0.18, 0.03], placements=[AssetInstance() for _ in range(1)])
catchall_bowl = Assets(description="catchall bowl", size=[0.22, 0.22, 0.07], placements=[AssetInstance() for _ in range(1)])
potted_succulent_plant = Assets(description="potted succulent plant", size=[0.16, 0.16, 0.22], placements=[AssetInstance() for _ in range(1)])
eucalyptus_stem_B = Assets(description="eucalyptus stem", size=[0.14, 0.20, 0.60], placements=[AssetInstance() for _ in range(1)])
woven_linen_placemat_B = Assets(description="woven linen placemat", size=[0.32, 0.45, 0.00], placements=[AssetInstance() for _ in range(1)])
wall_sconce_C = Assets(description="wall sconce", size=[0.20, 0.15, 0.30], placements=[AssetInstance() for _ in range(1)])
glass_tumbler_B = Assets(description="glass tumbler", size=[0.08, 0.08, 0.11], placements=[AssetInstance() for _ in range(1)])
wax_candle = Assets(description="wax candle", size=[0.08, 0.08, 0.12], placements=[AssetInstance() for _ in range(1)])
mirror = Assets(description="mirror", size=[0.04, 0.65, 0.90], placements=[AssetInstance() for _ in range(1)])
fridge = Assets(description="fridge", size=[0.65, 0.60, 1.80], placements=[AssetInstance() for _ in range(1)])
dining_chair_B = Assets(description="dining chair", size=[0.55, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])

dining_chair_A[0].instance_id = 'dining_chair_A_0'
storage_box[0].instance_id = 'storage_box_0'
print_A[0].instance_id = 'print_A_0'
wall_sconce_A[0].instance_id = 'wall_sconce_A_0'
sideboard_cabinet[0].instance_id = 'sideboard_cabinet_0'
glass_tumbler_A[0].instance_id = 'glass_tumbler_A_0'
hardcover_book_A[0].instance_id = 'hardcover_book_A_0'
wall_clock[0].instance_id = 'wall_clock_0'
print_B[0].instance_id = 'print_B_0'
woven_linen_placemat_A[0].instance_id = 'woven_linen_placemat_A_0'
painting[0].instance_id = 'painting_0'
cylinder_vase[0].instance_id = 'cylinder_vase_0'
dining_table[0].instance_id = 'dining_table_0'
bar_cart[0].instance_id = 'bar_cart_0'
wall_sconce_B[0].instance_id = 'wall_sconce_B_0'
eucalyptus_stem_A[0].instance_id = 'eucalyptus_stem_A_0'
entry_bench[0].instance_id = 'entry_bench_0'
art_print[0].instance_id = 'art_print_0'
floor_lamp[0].instance_id = 'floor_lamp_0'
hardcover_book_B[0].instance_id = 'hardcover_book_B_0'
hardcover_book_C[0].instance_id = 'hardcover_book_C_0'
catchall_bowl[0].instance_id = 'catchall_bowl_0'
potted_succulent_plant[0].instance_id = 'potted_succulent_plant_0'
eucalyptus_stem_B[0].instance_id = 'eucalyptus_stem_B_0'
woven_linen_placemat_B[0].instance_id = 'woven_linen_placemat_B_0'
wall_sconce_C[0].instance_id = 'wall_sconce_C_0'
glass_tumbler_B[0].instance_id = 'glass_tumbler_B_0'
wax_candle[0].instance_id = 'wax_candle_0'
mirror[0].instance_id = 'mirror_0'
fridge[0].instance_id = 'fridge_0'
dining_chair_B[0].instance_id = 'dining_chair_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

dining_chair_A[0].position = [0.5268815585665543, 1.4157190093194312, 0.425]
dining_chair_A[0].rotation = [0, 0, 0]
storage_box[0].position = [0.8925924811726182, 1.0285692814341694, 0.12]
storage_box[0].rotation = [0, 0, 0]
print_A[0].position = [4.7000780716283215, 1.8485992500805741, 0.3]
print_A[0].rotation = [0, 0, 0]
wall_sconce_A[0].position = [2.488292705706286, 0.9980763639537931, 0.15]
wall_sconce_A[0].rotation = [0, 0, 0]
sideboard_cabinet[0].position = [3.8139000243372627, 3.2252032728685593, 0.4]
sideboard_cabinet[0].rotation = [0, 0, 0]
glass_tumbler_A[0].position = [0.4329363275455683, 3.6261332396644423, 0.055]
glass_tumbler_A[0].rotation = [0, 0, 0]
hardcover_book_A[0].position = [4.341470538675678, 1.6846740892620828, 0.0175]
hardcover_book_A[0].rotation = [0, 0, 0]
wall_clock[0].position = [4.967722442751745, 0.005117033055418219, 0.16]
wall_clock[0].rotation = [0, 0, 0]
print_B[0].position = [2.0454249738084345, 1.3403817983829174, 0.3]
print_B[0].rotation = [0, 0, 0]
woven_linen_placemat_A[0].position = [3.152900589513054, 3.6306485346434223, 0.0015]
woven_linen_placemat_A[0].rotation = [0, 0, 0]
painting[0].position = [0.20732807333385894, 2.7555952950691136, 0.325]
painting[0].rotation = [0, 0, 0]
cylinder_vase[0].position = [4.296371136816514, 1.0211904519743644, 0.14]
cylinder_vase[0].rotation = [0, 0, 0]
dining_table[0].position = [1.2204742159973325, 0.5317339382190625, 0.375]
dining_table[0].rotation = [0, 0, 0]
bar_cart[0].position = [2.017530736711479, 2.1913053398334315, 0.425]
bar_cart[0].rotation = [0, 0, 0]
wall_sconce_B[0].position = [4.529274735051744, 3.44965115336525, 0.15]
wall_sconce_B[0].rotation = [0, 0, 0]
eucalyptus_stem_A[0].position = [4.185446125852422, 1.6710884253409635, 0.325]
eucalyptus_stem_A[0].rotation = [0, 0, 0]
entry_bench[0].position = [3.123298006729445, 2.9062699310954905, 0.225]
entry_bench[0].rotation = [0, 0, 0]
art_print[0].position = [0.815757932714114, 2.9006865956075485, 0.35]
art_print[0].rotation = [0, 0, 0]
floor_lamp[0].position = [4.361128264921418, 3.96612492582953, 0.8]
floor_lamp[0].rotation = [0, 0, 0]
hardcover_book_B[0].position = [0.1519696458134956, 2.5277579212911703, 0.015]
hardcover_book_B[0].rotation = [0, 0, 0]
hardcover_book_C[0].position = [3.8053428979628237, 3.867523459428875, 0.0125]
hardcover_book_C[0].rotation = [0, 0, 0]
catchall_bowl[0].position = [0.6465759241774927, 0.4186502718976506, 0.035]
catchall_bowl[0].rotation = [0, 0, 0]
potted_succulent_plant[0].position = [2.2501986722187435, 3.5430866529900475, 0.11]
potted_succulent_plant[0].rotation = [0, 0, 0]
eucalyptus_stem_B[0].position = [0.5740772849067283, 0.36677563492205056, 0.3]
eucalyptus_stem_B[0].rotation = [0, 0, 0]
woven_linen_placemat_B[0].position = [2.8459470121303343, 1.160990922809329, 0.0015]
woven_linen_placemat_B[0].rotation = [0, 0, 0]
wall_sconce_C[0].position = [4.72892237561505, 2.9088003193393783, 0.15]
wall_sconce_C[0].rotation = [0, 0, 0]
glass_tumbler_B[0].position = [3.966382833668149, 0.8127259777435323, 0.055]
glass_tumbler_B[0].rotation = [0, 0, 0]
wax_candle[0].position = [3.153045330757258, 1.6485373406137822, 0.06]
wax_candle[0].rotation = [0, 0, 0]
mirror[0].position = [2.8814067334485927, 3.968529347368127, 0.45]
mirror[0].rotation = [0, 0, 0]
fridge[0].position = [1.1121191506977202, 2.0688574247778093, 0.9]
fridge[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [0.13554576254488193, 1.6611306675396285, 0.425]
dining_chair_B[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [0.5268815585665543, 1.4157190093194312, 0.425]
dining_chair_A[0].rotation = [0, 0, 0]
storage_box[0].position = [0.8925924811726182, 1.0285692814341694, 0.12]
storage_box[0].rotation = [0, 0, 0]
print_A[0].position = [4.7000780716283215, 1.8485992500805741, 0.3]
print_A[0].rotation = [0, 0, 0]
wall_sconce_A[0].position = [2.488292705706286, 0.9980763639537931, 0.15]
wall_sconce_A[0].rotation = [0, 0, 0]
sideboard_cabinet[0].position = [3.8139000243372627, 3.2252032728685593, 0.4]
sideboard_cabinet[0].rotation = [0, 0, 0]
glass_tumbler_A[0].position = [0.4329363275455683, 3.6261332396644423, 0.055]
glass_tumbler_A[0].rotation = [0, 0, 0]
hardcover_book_A[0].position = [4.341470538675678, 1.6846740892620828, 0.0175]
hardcover_book_A[0].rotation = [0, 0, 0]
wall_clock[0].position = [4.967722442751745, 0.005117033055418219, 0.16]
wall_clock[0].rotation = [0, 0, 0]
print_B[0].position = [2.0454249738084345, 1.3403817983829174, 0.3]
print_B[0].rotation = [0, 0, 0]
woven_linen_placemat_A[0].position = [3.152900589513054, 3.6306485346434223, 0.0015]
woven_linen_placemat_A[0].rotation = [0, 0, 0]
painting[0].position = [0.20732807333385894, 2.7555952950691136, 0.325]
painting[0].rotation = [0, 0, 0]
cylinder_vase[0].position = [4.296371136816514, 1.0211904519743644, 0.14]
cylinder_vase[0].rotation = [0, 0, 0]
dining_table[0].position = [1.2204742159973325, 0.5317339382190625, 0.375]
dining_table[0].rotation = [0, 0, 0]
bar_cart[0].position = [2.017530736711479, 2.1913053398334315, 0.425]
bar_cart[0].rotation = [0, 0, 0]
wall_sconce_B[0].position = [4.529274735051744, 3.44965115336525, 0.15]
wall_sconce_B[0].rotation = [0, 0, 0]
eucalyptus_stem_A[0].position = [4.185446125852422, 1.6710884253409635, 0.325]
eucalyptus_stem_A[0].rotation = [0, 0, 0]
entry_bench[0].position = [3.123298006729445, 2.9062699310954905, 0.225]
entry_bench[0].rotation = [0, 0, 0]
art_print[0].position = [0.815757932714114, 2.9006865956075485, 0.35]
art_print[0].rotation = [0, 0, 0]
floor_lamp[0].position = [4.361128264921418, 3.96612492582953, 0.8]
floor_lamp[0].rotation = [0, 0, 0]
hardcover_book_B[0].position = [0.1519696458134956, 2.5277579212911703, 0.015]
hardcover_book_B[0].rotation = [0, 0, 0]
hardcover_book_C[0].position = [3.8053428979628237, 3.867523459428875, 0.0125]
hardcover_book_C[0].rotation = [0, 0, 0]
catchall_bowl[0].position = [0.6465759241774927, 0.4186502718976506, 0.035]
catchall_bowl[0].rotation = [0, 0, 0]
potted_succulent_plant[0].position = [2.2501986722187435, 3.5430866529900475, 0.11]
potted_succulent_plant[0].rotation = [0, 0, 0]
eucalyptus_stem_B[0].position = [0.5740772849067283, 0.36677563492205056, 0.3]
eucalyptus_stem_B[0].rotation = [0, 0, 0]
woven_linen_placemat_B[0].position = [2.8459470121303343, 1.160990922809329, 0.0015]
woven_linen_placemat_B[0].rotation = [0, 0, 0]
wall_sconce_C[0].position = [4.72892237561505, 2.9088003193393783, 0.15]
wall_sconce_C[0].rotation = [0, 0, 0]
glass_tumbler_B[0].position = [3.966382833668149, 0.8127259777435323, 0.055]
glass_tumbler_B[0].rotation = [0, 0, 0]
wax_candle[0].position = [3.153045330757258, 1.6485373406137822, 0.06]
wax_candle[0].rotation = [0, 0, 0]
mirror[0].position = [2.8814067334485927, 3.968529347368127, 0.45]
mirror[0].rotation = [0, 0, 0]
fridge[0].position = [1.1121191506977202, 2.0688574247778093, 0.9]
fridge[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [0.13554576254488193, 1.6611306675396285, 0.425]
dining_chair_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the supplied boundary coordinates: x=0..5, y=0..4.
# Keep the dining group central, storage along the perimeter, and the
# lower-left corner clear for entry and circulation.
layout_specs = [
    # Asset, bounding-box center, upright yaw in degrees
    (dining_table,             [2.60, 2.20, 0.375],   0),
    (dining_chair_A,           [1.70, 2.20, 0.425],   0),
    (dining_chair_B,           [3.50, 2.20, 0.425], 180),

    (sideboard_cabinet,        [0.225, 2.65, 0.40],   0),
    (entry_bench,              [1.40, 0.19, 0.225],  90),
    (bar_cart,                 [4.80, 1.40, 0.425], 180),
    (fridge,                   [4.675, 3.50, 0.90], 180),
    (floor_lamp,               [0.70, 3.65, 0.80],    0),

    # Wall-mounted objects: their shallow local x dimension is wall-normal.
    (print_A,                  [0.015, 0.80, 1.60],   0),
    (print_B,                  [0.015, 1.40, 1.60],   0),
    (painting,                 [0.020, 2.65, 1.65],   0),
    (wall_sconce_A,            [0.100, 2.00, 2.25],   0),
    (wall_sconce_B,            [0.100, 3.30, 2.25],   0),
    (wall_sconce_C,            [4.900, 1.40, 1.85], 180),
    (wall_clock,               [4.980, 2.60, 1.85], 180),
    (mirror,                   [1.400, 0.02, 1.50],  90),
    (art_print,                [2.600, 3.985, 1.65], 270),

    # Two place settings, with glasses beyond the placemat footprints.
    (woven_linen_placemat_A,   [2.38, 2.20, 0.750],   0),
    (woven_linen_placemat_B,   [2.82, 2.20, 0.750], 180),
    (glass_tumbler_A,          [2.38, 2.58, 0.805],   0),
    (glass_tumbler_B,          [2.82, 2.58, 0.805], 180),
    (wax_candle,               [2.60, 1.65, 0.810],   0),

    # Sideboard display: separate books, vase, and a loose botanical stem.
    (hardcover_book_A,         [0.225, 2.05, 0.820],   0),
    (hardcover_book_B,         [0.225, 2.05, 0.855],   0),
    (hardcover_book_C,         [0.225, 2.05, 0.885],   0),
    (cylinder_vase,            [0.225, 2.90, 0.940],   0),
    (eucalyptus_stem_A,        [0.225, 2.90, 1.405],   0),
    (eucalyptus_stem_B,        [0.225, 2.40, 1.100],   0),

    # Entry essentials and a plant on the cart.
    (storage_box,              [1.10, 0.19, 0.570],  90),
    (catchall_bowl,            [1.65, 0.19, 0.485],  90),
    (potted_succulent_plant,    [4.80, 1.40, 0.960], 180),
]

# Assign all placements without replacing any supplied asset variables.
# Fixed-center constraints also preserve wall-art heights, which cannot
# otherwise be expressed by the available wall-contact constraint.
for asset_ref, center_xyz, yaw_degrees in layout_specs:
    asset_ref[0].position = list(center_xyz)
    asset_ref[0].rotation = [0, 0, radians(yaw_degrees)]

# Highest-priority semantic constraints first.
solver.point_towards(dining_chair_A[0], dining_chair_B[0])
solver.point_towards(dining_chair_B[0], dining_chair_A[0])
solver.against_wall(entry_bench[0], walls[0])

# Supporting surfaces: all small freestanding accessories are supported.
support_pairs = [
    (woven_linen_placemat_A, dining_table),
    (woven_linen_placemat_B, dining_table),
    (glass_tumbler_A, dining_table),
    (glass_tumbler_B, dining_table),
    (wax_candle, dining_table),
    (hardcover_book_A, sideboard_cabinet),
    (hardcover_book_B, hardcover_book_A),
    (hardcover_book_C, hardcover_book_B),
    (cylinder_vase, sideboard_cabinet),
    # Rest the stem above the vase rim rather than intersecting its geometry.
    (eucalyptus_stem_A, cylinder_vase),
    (eucalyptus_stem_B, sideboard_cabinet),
    (storage_box, entry_bench),
    (catchall_bowl, entry_bench),
    (potted_succulent_plant, bar_cart),
]
for upper_ref, lower_ref in support_pairs:
    solver.on_top_of(upper_ref[0], lower_ref[0])

# Wall contact for perimeter furniture and mounted decorations.
wall_contacts = [
    (sideboard_cabinet, 3),
    (bar_cart, 1),
    (fridge, 1),
    (print_A, 3),
    (print_B, 3),
    (painting, 3),
    (wall_sconce_A, 3),
    (wall_sconce_B, 3),
    (wall_sconce_C, 1),
    (wall_clock, 1),
    (mirror, 0),
    (art_print, 2),
]
for asset_ref, wall_index in wall_contacts:
    solver.against_wall(asset_ref[0], walls[wall_index])

# Every instance receives a position-based and orientation-based constraint.
# Exact anchors preserve the deliberately separated bounding boxes and leave
# the circulation routes intact. Reference instances are fixed points only,
# not additional scene assets.
for asset_ref, center_xyz, yaw_degrees in layout_specs:
    solver.distance_constraint(
        asset_ref[0],
        AssetInstance(position=list(center_xyz)),
        0, 0,
        weight=10,
    )
    solver.align_with(
        asset_ref[0],
        AssetInstance(
            position=list(center_xyz),
            rotation=[0, 0, radians(yaw_degrees)],
        ),
        angle=0,
    )

# Maintain usable chair-to-table spacing if the dining group is adjusted.
solver.distance_constraint(
    dining_chair_A[0], dining_table[0], 0.88, 1.00, weight=10
)
solver.distance_constraint(
    dining_chair_B[0], dining_table[0], 0.88, 1.00, weight=10
)
solver.distance_constraint(
    dining_chair_A[0], dining_chair_B[0], 1.75, 1.90, weight=10
)

solver.constraints = []
storage_box[0].position = [1.100000023841858, 0.1899999976158142, 0.5699999928474426]
storage_box[0].rotation = [0, 0, 1.5833626980517244]
storage_box[0].optimize = 2
wall_sconce_B[0].position = [0.09030711650848389, 3.299999952316284, 0.15000000596046448]
wall_sconce_B[0].rotation = [0, 0, 0.0025409215170312644]
wall_sconce_B[0].optimize = 2
woven_linen_placemat_A[0].position = [2.380000114440918, 2.200000047683716, 0.75]
woven_linen_placemat_A[0].rotation = [0, 0, 0.01256637125682779]
woven_linen_placemat_A[0].optimize = 2
eucalyptus_stem_A[0].position = [0.22499999403953552, 2.9000000953674316, 1.4049999713897705]
eucalyptus_stem_A[0].rotation = [0, 0, 0.01256637125682779]
eucalyptus_stem_A[0].optimize = 2
bar_cart[0].position = [4.797883987426758, 1.399999976158142, 0.42500001192092896]
bar_cart[0].rotation = [0, 0, -3.1359411321623822]
bar_cart[0].optimize = 2
wall_sconce_C[0].position = [4.909692287445068, 1.399999976158142, 0.15000000596046448]
wall_sconce_C[0].rotation = [0, 0, -3.1390517311505883]
wall_sconce_C[0].optimize = 2
glass_tumbler_A[0].position = [2.380000114440918, 2.5799999237060547, 0.8050000071525574]
glass_tumbler_A[0].rotation = [0, 0, 0.01256637125682779]
glass_tumbler_A[0].optimize = 2
wall_clock[0].position = [4.988697052001953, 2.5999999046325684, 0.1599999964237213]
wall_clock[0].rotation = [0, 0, -3.1390517329949352]
wall_clock[0].optimize = 2
print_B[0].position = [0.00674373097717762, 1.399999976158142, 0.30000001192092896]
print_B[0].rotation = [0, 0, 0.002540921217104852]
print_B[0].optimize = 2
painting[0].position = [0.011367769911885262, 2.6500000953674316, 0.32499998807907104]
painting[0].rotation = [0, 0, 0.0025409150842135757]
painting[0].optimize = 2
dining_chair_A[0].position = [1.7000000476837158, 2.200000047683716, 0.42500001192092896]
dining_chair_A[0].rotation = [0, 0, 0.021991148286022624]
dining_chair_A[0].optimize = 2
wall_sconce_A[0].position = [0.09030711650848389, 2.0, 0.15000000596046448]
wall_sconce_A[0].rotation = [0, 0, 0.0025409215170312644]
wall_sconce_A[0].optimize = 2
dining_chair_B[0].position = [3.5, 2.200000047683716, 0.42500001192092896]
dining_chair_B[0].rotation = [0, 0, -3.1196015053037707]
dining_chair_B[0].optimize = 2
cylinder_vase[0].position = [0.22499999403953552, 2.9000000953674316, 0.9399999976158142]
cylinder_vase[0].rotation = [0, 0, 0.0157079639172164]
cylinder_vase[0].optimize = 2
woven_linen_placemat_B[0].position = [2.819999933242798, 2.200000047683716, 0.75]
woven_linen_placemat_B[0].rotation = [0, 0, -3.1290262823329655]
woven_linen_placemat_B[0].optimize = 2
sideboard_cabinet[0].position = [0.23253725469112396, 2.6500000953674316, 0.4000000059604645]
sideboard_cabinet[0].rotation = [0, 0, 0.011873008734268685]
sideboard_cabinet[0].optimize = 2
hardcover_book_A[0].position = [0.22499999403953552, 2.049999952316284, 0.8199999928474426]
hardcover_book_A[0].rotation = [0, 0, 0.0157079639172164]
hardcover_book_A[0].optimize = 2
print_A[0].position = [0.00674373097717762, 0.800000011920929, 0.30000001192092896]
print_A[0].rotation = [0, 0, 0.002540921217104852]
print_A[0].optimize = 2
eucalyptus_stem_B[0].position = [0.22499999403953552, 2.4000000953674316, 1.100000023841858]
eucalyptus_stem_B[0].rotation = [0, 0, 0.01256637125682779]
eucalyptus_stem_B[0].optimize = 2
catchall_bowl[0].position = [1.649999976158142, 0.1899999976158142, 0.48499998450279236]
catchall_bowl[0].rotation = [0, 0, 1.5833626980517244]
catchall_bowl[0].optimize = 2
hardcover_book_C[0].position = [0.22499999403953552, 2.049999952316284, 0.8849999308586121]
hardcover_book_C[0].rotation = [0, 0, 0.01256637125682779]
hardcover_book_C[0].optimize = 2
mirror[0].position = [1.399999976158142, 0.011367769911885262, 0.44999998807907104]
mirror[0].rotation = [0, 0, 1.5733372440233822]
mirror[0].optimize = 2
dining_table[0].position = [2.5999999046325684, 2.200000047683716, 0.375]
dining_table[0].rotation = [0, 0, 0.031415925765816845]
dining_table[0].optimize = 2
art_print[0].position = [2.5999999046325684, 3.9932661056518555, 0.3499999940395355]
art_print[0].rotation = [0, 0, -1.5682554064999652]
art_print[0].optimize = 2
hardcover_book_B[0].position = [0.22499999403953552, 2.049999952316284, 0.8549999594688416]
hardcover_book_B[0].rotation = [0, 0, 0.0157079639172164]
hardcover_book_B[0].optimize = 2
fridge[0].position = [4.674238681793213, 3.5, 0.8999999761581421]
fridge[0].rotation = [0, 0, -3.1390517351392084]
fridge[0].optimize = 2
floor_lamp[0].position = [0.699999988079071, 3.6500000953674316, 0.800000011920929]
floor_lamp[0].rotation = [0, 0, 0.00942477746072377]
floor_lamp[0].optimize = 2
entry_bench[0].position = [1.399999976158142, 0.19033314287662506, 0.22499999403953552]
entry_bench[0].rotation = [0, 0, 1.579558543027696]
entry_bench[0].optimize = 2
wax_candle[0].position = [2.5999999046325684, 1.649999976158142, 0.8100000023841858]
wax_candle[0].rotation = [0, 0, 0.01256637125682779]
wax_candle[0].optimize = 2
potted_succulent_plant[0].position = [4.800000190734863, 1.399999976158142, 0.9600000381469727]
potted_succulent_plant[0].rotation = [0, 0, -3.1290262823329655]
potted_succulent_plant[0].optimize = 2
glass_tumbler_B[0].position = [2.819999933242798, 2.5799999237060547, 0.8050000071525574]
glass_tumbler_B[0].rotation = [0, 0, -3.1290262823329655]
glass_tumbler_B[0].optimize = 2

