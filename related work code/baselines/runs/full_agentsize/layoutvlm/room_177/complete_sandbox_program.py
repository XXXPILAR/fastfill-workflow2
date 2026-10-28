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
dining_chair_A = Assets(description="dining chair", size=[0.55, 0.48, 0.84], placements=[AssetInstance() for _ in range(1)])
storage_box = Assets(description="storage box", size=[0.32, 0.42, 0.24], placements=[AssetInstance() for _ in range(1)])
print_A = Assets(description="print", size=[0.03, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
wall_sconce_A = Assets(description="wall sconce", size=[0.14, 0.18, 0.32], placements=[AssetInstance() for _ in range(1)])
sideboard_cabinet = Assets(description="sideboard cabinet", size=[0.45, 1.60, 0.82], placements=[AssetInstance() for _ in range(1)])
glass_tumbler_A = Assets(description="glass tumbler", size=[0.08, 0.08, 0.11], placements=[AssetInstance() for _ in range(1)])
hardcover_book_A = Assets(description="hardcover book", size=[0.18, 0.24, 0.04], placements=[AssetInstance() for _ in range(1)])
wall_clock = Assets(description="wall clock", size=[0.05, 0.38, 0.38], placements=[AssetInstance() for _ in range(1)])
print_B = Assets(description="print", size=[0.03, 0.40, 0.50], placements=[AssetInstance() for _ in range(1)])
woven_linen_placemat_A = Assets(description="woven linen placemat", size=[0.32, 0.45, 0.01], placements=[AssetInstance() for _ in range(1)])
painting = Assets(description="painting", size=[0.04, 1.10, 0.75], placements=[AssetInstance() for _ in range(1)])
cylinder_vase = Assets(description="cylinder vase", size=[0.16, 0.16, 0.32], placements=[AssetInstance() for _ in range(1)])
dining_table = Assets(description="dining table", size=[0.90, 1.80, 0.76], placements=[AssetInstance() for _ in range(1)])
bar_cart = Assets(description="bar cart", size=[0.42, 0.75, 0.88], placements=[AssetInstance() for _ in range(1)])
wall_sconce_B = Assets(description="wall sconce", size=[0.14, 0.18, 0.32], placements=[AssetInstance() for _ in range(1)])
eucalyptus_stem_A = Assets(description="eucalyptus stem", size=[0.20, 0.28, 0.75], placements=[AssetInstance() for _ in range(1)])
entry_bench = Assets(description="entry bench", size=[0.42, 1.20, 0.48], placements=[AssetInstance() for _ in range(1)])
art_print = Assets(description="art print", size=[0.03, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])
floor_lamp = Assets(description="floor lamp", size=[0.38, 0.38, 1.65], placements=[AssetInstance() for _ in range(1)])
hardcover_book_B = Assets(description="hardcover book", size=[0.20, 0.26, 0.04], placements=[AssetInstance() for _ in range(1)])
hardcover_book_C = Assets(description="hardcover book", size=[0.16, 0.22, 0.04], placements=[AssetInstance() for _ in range(1)])
catchall_bowl = Assets(description="catchall bowl", size=[0.24, 0.24, 0.08], placements=[AssetInstance() for _ in range(1)])
potted_succulent_plant = Assets(description="potted succulent plant", size=[0.18, 0.18, 0.22], placements=[AssetInstance() for _ in range(1)])
eucalyptus_stem_B = Assets(description="eucalyptus stem", size=[0.18, 0.25, 0.68], placements=[AssetInstance() for _ in range(1)])
woven_linen_placemat_B = Assets(description="woven linen placemat", size=[0.32, 0.45, 0.01], placements=[AssetInstance() for _ in range(1)])
wall_sconce_C = Assets(description="wall sconce", size=[0.14, 0.18, 0.32], placements=[AssetInstance() for _ in range(1)])
glass_tumbler_B = Assets(description="glass tumbler", size=[0.08, 0.08, 0.11], placements=[AssetInstance() for _ in range(1)])
wax_candle = Assets(description="wax candle", size=[0.09, 0.09, 0.12], placements=[AssetInstance() for _ in range(1)])
mirror = Assets(description="mirror", size=[0.04, 0.80, 1.10], placements=[AssetInstance() for _ in range(1)])
fridge = Assets(description="fridge", size=[0.72, 0.70, 1.85], placements=[AssetInstance() for _ in range(1)])
dining_chair_B = Assets(description="dining chair", size=[0.55, 0.48, 0.84], placements=[AssetInstance() for _ in range(1)])

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

dining_chair_A[0].position = [3.0618753349974503, 2.598263316921433, 0.42]
dining_chair_A[0].rotation = [0, 0, 0]
storage_box[0].position = [1.8132369812006655, 2.5513692354254562, 0.12]
storage_box[0].rotation = [0, 0, 0]
print_A[0].position = [1.8735926365206523, 0.5547035364829718, 0.35]
print_A[0].rotation = [0, 0, 0]
wall_sconce_A[0].position = [0.39579194706612086, 0.8821881032330334, 0.16]
wall_sconce_A[0].rotation = [0, 0, 0]
sideboard_cabinet[0].position = [2.516633836521438, 1.970383907826137, 0.41]
sideboard_cabinet[0].rotation = [0, 0, 0]
glass_tumbler_A[0].position = [3.66814255138768, 1.8470821300451221, 0.055]
glass_tumbler_A[0].rotation = [0, 0, 0]
hardcover_book_A[0].position = [1.3981172793443069, 0.8897401672604137, 0.02]
hardcover_book_A[0].rotation = [0, 0, 0]
wall_clock[0].position = [4.158542054019994, 2.803742866853135, 0.19]
wall_clock[0].rotation = [0, 0, 0]
print_B[0].position = [1.4704484574824173, 0.7712826576920269, 0.25]
print_B[0].rotation = [0, 0, 0]
woven_linen_placemat_A[0].position = [3.5819467782555265, 3.384337921407419, 0.0025]
woven_linen_placemat_A[0].rotation = [0, 0, 0]
painting[0].position = [2.2232532894537145, 3.0700456312258875, 0.375]
painting[0].rotation = [0, 0, 0]
cylinder_vase[0].position = [4.446388016186998, 2.8411802804725372, 0.16]
cylinder_vase[0].rotation = [0, 0, 0]
dining_table[0].position = [2.3781127114963057, 2.5674604487313357, 0.38]
dining_table[0].rotation = [0, 0, 0]
bar_cart[0].position = [2.7126130341492036, 0.22883668298142323, 0.44]
bar_cart[0].rotation = [0, 0, 0]
wall_sconce_B[0].position = [1.1522478968674505, 2.0592664816368855, 0.16]
wall_sconce_B[0].rotation = [0, 0, 0]
eucalyptus_stem_A[0].position = [1.7106577090737702, 1.3603172371538035, 0.375]
eucalyptus_stem_A[0].rotation = [0, 0, 0]
entry_bench[0].position = [0.22405209733862785, 0.08911211238922467, 0.24]
entry_bench[0].rotation = [0, 0, 0]
art_print[0].position = [3.1743912742983738, 2.167784889139907, 0.3]
art_print[0].rotation = [0, 0, 0]
floor_lamp[0].position = [0.9857585246597106, 3.3808924437683814, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
hardcover_book_B[0].position = [3.780865385119447, 0.11164402067497248, 0.02]
hardcover_book_B[0].rotation = [0, 0, 0]
hardcover_book_C[0].position = [1.0723577260315653, 3.7504988091228593, 0.0175]
hardcover_book_C[0].rotation = [0, 0, 0]
catchall_bowl[0].position = [2.0198976144419363, 0.8376887521997638, 0.04]
catchall_bowl[0].rotation = [0, 0, 0]
potted_succulent_plant[0].position = [3.0945042403505454, 1.9255415181894797, 0.11]
potted_succulent_plant[0].rotation = [0, 0, 0]
eucalyptus_stem_B[0].position = [1.2999862285229047, 2.4022356815451373, 0.34]
eucalyptus_stem_B[0].rotation = [0, 0, 0]
woven_linen_placemat_B[0].position = [0.23251883415848718, 2.8620588405718905, 0.0025]
woven_linen_placemat_B[0].rotation = [0, 0, 0]
wall_sconce_C[0].position = [3.6910332296396993, 2.035306640062436, 0.16]
wall_sconce_C[0].rotation = [0, 0, 0]
glass_tumbler_B[0].position = [2.517191515518376, 0.2732014650157444, 0.055]
glass_tumbler_B[0].rotation = [0, 0, 0]
wax_candle[0].position = [4.41260765743505, 3.9952736263080526, 0.06]
wax_candle[0].rotation = [0, 0, 0]
mirror[0].position = [4.963780091669498, 3.485682443328502, 0.55]
mirror[0].rotation = [0, 0, 0]
fridge[0].position = [1.281135155305782, 1.5900597663632108, 0.925]
fridge[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [2.5939868532547985, 1.2448385157336008, 0.42]
dining_chair_B[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [3.0618753349974503, 2.598263316921433, 0.42]
dining_chair_A[0].rotation = [0, 0, 0]
storage_box[0].position = [1.8132369812006655, 2.5513692354254562, 0.12]
storage_box[0].rotation = [0, 0, 0]
print_A[0].position = [1.8735926365206523, 0.5547035364829718, 0.35]
print_A[0].rotation = [0, 0, 0]
wall_sconce_A[0].position = [0.39579194706612086, 0.8821881032330334, 0.16]
wall_sconce_A[0].rotation = [0, 0, 0]
sideboard_cabinet[0].position = [2.516633836521438, 1.970383907826137, 0.41]
sideboard_cabinet[0].rotation = [0, 0, 0]
glass_tumbler_A[0].position = [3.66814255138768, 1.8470821300451221, 0.055]
glass_tumbler_A[0].rotation = [0, 0, 0]
hardcover_book_A[0].position = [1.3981172793443069, 0.8897401672604137, 0.02]
hardcover_book_A[0].rotation = [0, 0, 0]
wall_clock[0].position = [4.158542054019994, 2.803742866853135, 0.19]
wall_clock[0].rotation = [0, 0, 0]
print_B[0].position = [1.4704484574824173, 0.7712826576920269, 0.25]
print_B[0].rotation = [0, 0, 0]
woven_linen_placemat_A[0].position = [3.5819467782555265, 3.384337921407419, 0.0025]
woven_linen_placemat_A[0].rotation = [0, 0, 0]
painting[0].position = [2.2232532894537145, 3.0700456312258875, 0.375]
painting[0].rotation = [0, 0, 0]
cylinder_vase[0].position = [4.446388016186998, 2.8411802804725372, 0.16]
cylinder_vase[0].rotation = [0, 0, 0]
dining_table[0].position = [2.3781127114963057, 2.5674604487313357, 0.38]
dining_table[0].rotation = [0, 0, 0]
bar_cart[0].position = [2.7126130341492036, 0.22883668298142323, 0.44]
bar_cart[0].rotation = [0, 0, 0]
wall_sconce_B[0].position = [1.1522478968674505, 2.0592664816368855, 0.16]
wall_sconce_B[0].rotation = [0, 0, 0]
eucalyptus_stem_A[0].position = [1.7106577090737702, 1.3603172371538035, 0.375]
eucalyptus_stem_A[0].rotation = [0, 0, 0]
entry_bench[0].position = [0.22405209733862785, 0.08911211238922467, 0.24]
entry_bench[0].rotation = [0, 0, 0]
art_print[0].position = [3.1743912742983738, 2.167784889139907, 0.3]
art_print[0].rotation = [0, 0, 0]
floor_lamp[0].position = [0.9857585246597106, 3.3808924437683814, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
hardcover_book_B[0].position = [3.780865385119447, 0.11164402067497248, 0.02]
hardcover_book_B[0].rotation = [0, 0, 0]
hardcover_book_C[0].position = [1.0723577260315653, 3.7504988091228593, 0.0175]
hardcover_book_C[0].rotation = [0, 0, 0]
catchall_bowl[0].position = [2.0198976144419363, 0.8376887521997638, 0.04]
catchall_bowl[0].rotation = [0, 0, 0]
potted_succulent_plant[0].position = [3.0945042403505454, 1.9255415181894797, 0.11]
potted_succulent_plant[0].rotation = [0, 0, 0]
eucalyptus_stem_B[0].position = [1.2999862285229047, 2.4022356815451373, 0.34]
eucalyptus_stem_B[0].rotation = [0, 0, 0]
woven_linen_placemat_B[0].position = [0.23251883415848718, 2.8620588405718905, 0.0025]
woven_linen_placemat_B[0].rotation = [0, 0, 0]
wall_sconce_C[0].position = [3.6910332296396993, 2.035306640062436, 0.16]
wall_sconce_C[0].rotation = [0, 0, 0]
glass_tumbler_B[0].position = [2.517191515518376, 0.2732014650157444, 0.055]
glass_tumbler_B[0].rotation = [0, 0, 0]
wax_candle[0].position = [4.41260765743505, 3.9952736263080526, 0.06]
wax_candle[0].rotation = [0, 0, 0]
mirror[0].position = [4.963780091669498, 3.485682443328502, 0.55]
mirror[0].rotation = [0, 0, 0]
fridge[0].position = [1.281135155305782, 1.5900597663632108, 0.925]
fridge[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [2.5939868532547985, 1.2448385157336008, 0.42]
dining_chair_B[0].rotation = [0, 0, 0]

solver.constraints = []

# The dining group occupies the center of the room, leaving circulation space
# around the perimeter. The chairs sit on opposite sides of the table.
dining_table[0].position = [2.45, 2.20, 0.38]
dining_table[0].rotation = [0, 0, radians(0)]

dining_chair_A[0].position = [1.55, 2.20, 0.42]
dining_chair_A[0].rotation = [0, 0, radians(0)]

dining_chair_B[0].position = [3.35, 2.20, 0.42]
dining_chair_B[0].rotation = [0, 0, radians(180)]

# Storage and entry furniture are distributed along the room perimeter.
sideboard_cabinet[0].position = [4.775, 2.85, 0.41]
sideboard_cabinet[0].rotation = [0, 0, radians(180)]

fridge[0].position = [4.64, 0.55, 0.925]
fridge[0].rotation = [0, 0, radians(180)]

entry_bench[0].position = [1.10, 0.21, 0.24]
entry_bench[0].rotation = [0, 0, radians(90)]

storage_box[0].position = [1.95, 0.30, 0.12]
storage_box[0].rotation = [0, 0, radians(90)]

bar_cart[0].position = [0.21, 3.35, 0.44]
bar_cart[0].rotation = [0, 0, radians(0)]

floor_lamp[0].position = [3.75, 0.35, 0.825]
floor_lamp[0].rotation = [0, 0, radians(90)]

# Two place settings are arranged on opposite sides of the dining table.
woven_linen_placemat_A[0].position = [2.18, 2.20, 0.765]
woven_linen_placemat_A[0].rotation = [0, 0, radians(0)]

woven_linen_placemat_B[0].position = [2.72, 2.20, 0.765]
woven_linen_placemat_B[0].rotation = [0, 0, radians(180)]

glass_tumbler_A[0].position = [2.18, 2.58, 0.815]
glass_tumbler_A[0].rotation = [0, 0, radians(0)]

glass_tumbler_B[0].position = [2.72, 1.82, 0.815]
glass_tumbler_B[0].rotation = [0, 0, radians(180)]

# Decorative objects are spaced across the sideboard top. Books B and C form
# a small stack, while book A is displayed separately.
hardcover_book_A[0].position = [4.52, 2.28, 0.84]
hardcover_book_A[0].rotation = [0, 0, radians(90)]

hardcover_book_B[0].position = [4.52, 3.42, 0.84]
hardcover_book_B[0].rotation = [0, 0, radians(90)]

hardcover_book_C[0].position = [4.52, 3.42, 0.88]
hardcover_book_C[0].rotation = [0, 0, radians(90)]

catchall_bowl[0].position = [4.52, 2.72, 0.86]
catchall_bowl[0].rotation = [0, 0, radians(180)]

potted_succulent_plant[0].position = [4.52, 3.15, 0.93]
potted_succulent_plant[0].rotation = [0, 0, radians(180)]

cylinder_vase[0].position = [4.52, 2.98, 0.98]
cylinder_vase[0].rotation = [0, 0, radians(180)]

# The two eucalyptus stems form one bouquet in the cylinder vase.
eucalyptus_stem_A[0].position = [4.50, 2.96, 1.515]
eucalyptus_stem_A[0].rotation = [0, 0, radians(180)]

eucalyptus_stem_B[0].position = [4.54, 3.00, 1.48]
eucalyptus_stem_B[0].rotation = [0, 0, radians(180)]

wax_candle[0].position = [0.32, 3.35, 0.94]
wax_candle[0].rotation = [0, 0, radians(0)]

# Wall decorations are positioned above furniture or on otherwise unused wall
# sections. Their shallow dimension is kept perpendicular to the host wall.
painting[0].position = [2.60, 3.98, 1.65]
painting[0].rotation = [0, 0, radians(-90)]

print_B[0].position = [1.05, 3.985, 1.55]
print_B[0].rotation = [0, 0, radians(-90)]

wall_clock[0].position = [4.30, 3.975, 1.65]
wall_clock[0].rotation = [0, 0, radians(-90)]

print_A[0].position = [0.015, 2.20, 1.50]
print_A[0].rotation = [0, 0, radians(0)]

art_print[0].position = [3.10, 0.015, 1.48]
art_print[0].rotation = [0, 0, radians(90)]

mirror[0].position = [4.98, 2.85, 1.55]
mirror[0].rotation = [0, 0, radians(180)]

wall_sconce_A[0].position = [1.90, 3.93, 1.70]
wall_sconce_A[0].rotation = [0, 0, radians(-90)]

wall_sconce_B[0].position = [3.30, 3.93, 1.70]
wall_sconce_B[0].rotation = [0, 0, radians(-90)]

wall_sconce_C[0].position = [0.07, 3.25, 1.65]
wall_sconce_C[0].rotation = [0, 0, radians(0)]


# Fixed references preserve the intended zones while allowing the solver to
# make small feasibility adjustments. Exact position constraints are weighted
# strongly because the coordinates already account for clearances.
room_center = AssetInstance(position=[2.50, 2.00, 1.00])

def pin_position(instance, position):
    solver.distance_constraint(
        instance,
        AssetInstance(position=position),
        0,
        0,
        weight=10,
    )


# Dining furniture constraints. The reciprocal point-towards constraints are
# the primary semantic requirement: the two dining chairs face one another.
pin_position(dining_table[0], dining_table[0].position)
solver.align_with(
    dining_table[0],
    AssetInstance(position=[2.45, 2.20, 0.38],
                  rotation=[0, 0, radians(0)]),
)

pin_position(dining_chair_A[0], dining_chair_A[0].position)
solver.point_towards(dining_chair_A[0], dining_chair_B[0])

pin_position(dining_chair_B[0], dining_chair_B[0].position)
solver.point_towards(dining_chair_B[0], dining_chair_A[0])


# Perimeter furniture constraints.
solver.against_wall(sideboard_cabinet[0], walls[1])
pin_position(sideboard_cabinet[0], sideboard_cabinet[0].position)
solver.point_towards(sideboard_cabinet[0], room_center)

solver.against_wall(fridge[0], walls[1])
pin_position(fridge[0], fridge[0].position)
solver.point_towards(fridge[0], room_center)

# The entry bench is explicitly attached to the bottom wall and faces inward.
solver.against_wall(entry_bench[0], walls[0])
pin_position(entry_bench[0], entry_bench[0].position)
solver.point_towards(entry_bench[0], room_center)

pin_position(storage_box[0], storage_box[0].position)
solver.align_with(storage_box[0], entry_bench[0])

solver.against_wall(bar_cart[0], walls[3])
pin_position(bar_cart[0], bar_cart[0].position)
solver.point_towards(bar_cart[0], room_center)

pin_position(floor_lamp[0], floor_lamp[0].position)
solver.point_towards(floor_lamp[0], room_center)


# Dining-table accessories receive both support and positional constraints.
solver.on_top_of(woven_linen_placemat_A[0], dining_table[0])
pin_position(woven_linen_placemat_A[0], woven_linen_placemat_A[0].position)
solver.align_with(woven_linen_placemat_A[0], dining_chair_A[0])

solver.on_top_of(woven_linen_placemat_B[0], dining_table[0])
pin_position(woven_linen_placemat_B[0], woven_linen_placemat_B[0].position)
solver.align_with(woven_linen_placemat_B[0], dining_chair_B[0])

solver.on_top_of(glass_tumbler_A[0], dining_table[0])
pin_position(glass_tumbler_A[0], glass_tumbler_A[0].position)
solver.align_with(glass_tumbler_A[0], dining_chair_A[0])

solver.on_top_of(glass_tumbler_B[0], dining_table[0])
pin_position(glass_tumbler_B[0], glass_tumbler_B[0].position)
solver.align_with(glass_tumbler_B[0], dining_chair_B[0])


# Sideboard accessories are anchored to distinct locations on its top.
solver.on_top_of(hardcover_book_A[0], sideboard_cabinet[0])
pin_position(hardcover_book_A[0], hardcover_book_A[0].position)
solver.align_with(hardcover_book_A[0], sideboard_cabinet[0], angle=90)

solver.on_top_of(hardcover_book_B[0], sideboard_cabinet[0])
pin_position(hardcover_book_B[0], hardcover_book_B[0].position)
solver.align_with(hardcover_book_B[0], sideboard_cabinet[0], angle=90)

solver.on_top_of(hardcover_book_C[0], hardcover_book_B[0])
pin_position(hardcover_book_C[0], hardcover_book_C[0].position)
solver.align_with(hardcover_book_C[0], hardcover_book_B[0])

solver.on_top_of(catchall_bowl[0], sideboard_cabinet[0])
pin_position(catchall_bowl[0], catchall_bowl[0].position)
solver.align_with(catchall_bowl[0], sideboard_cabinet[0])

solver.on_top_of(potted_succulent_plant[0], sideboard_cabinet[0])
pin_position(potted_succulent_plant[0], potted_succulent_plant[0].position)
solver.align_with(potted_succulent_plant[0], sideboard_cabinet[0])

solver.on_top_of(cylinder_vase[0], sideboard_cabinet[0])
pin_position(cylinder_vase[0], cylinder_vase[0].position)
solver.align_with(cylinder_vase[0], sideboard_cabinet[0])

solver.on_top_of(eucalyptus_stem_A[0], cylinder_vase[0])
pin_position(eucalyptus_stem_A[0], eucalyptus_stem_A[0].position)
solver.align_with(eucalyptus_stem_A[0], cylinder_vase[0])

solver.on_top_of(eucalyptus_stem_B[0], cylinder_vase[0])
pin_position(eucalyptus_stem_B[0], eucalyptus_stem_B[0].position)
solver.align_with(eucalyptus_stem_B[0], cylinder_vase[0])

solver.on_top_of(wax_candle[0], bar_cart[0])
pin_position(wax_candle[0], wax_candle[0].position)
solver.align_with(wax_candle[0], bar_cart[0])


# Wall-mounted assets are constrained to their host walls and oriented toward
# the room interior.
solver.against_wall(painting[0], walls[2])
pin_position(painting[0], painting[0].position)
solver.point_towards(painting[0], room_center)

solver.against_wall(print_B[0], walls[2])
pin_position(print_B[0], print_B[0].position)
solver.point_towards(print_B[0], room_center)

solver.against_wall(wall_clock[0], walls[2])
pin_position(wall_clock[0], wall_clock[0].position)
solver.point_towards(wall_clock[0], room_center)

solver.against_wall(print_A[0], walls[3])
pin_position(print_A[0], print_A[0].position)
solver.point_towards(print_A[0], room_center)

solver.against_wall(art_print[0], walls[0])
pin_position(art_print[0], art_print[0].position)
solver.point_towards(art_print[0], room_center)

solver.against_wall(mirror[0], walls[1])
pin_position(mirror[0], mirror[0].position)
solver.point_towards(mirror[0], room_center)

solver.against_wall(wall_sconce_A[0], walls[2])
pin_position(wall_sconce_A[0], wall_sconce_A[0].position)
solver.point_towards(wall_sconce_A[0], room_center)

solver.against_wall(wall_sconce_B[0], walls[2])
pin_position(wall_sconce_B[0], wall_sconce_B[0].position)
solver.point_towards(wall_sconce_B[0], room_center)

solver.against_wall(wall_sconce_C[0], walls[3])
pin_position(wall_sconce_C[0], wall_sconce_C[0].position)
solver.point_towards(wall_sconce_C[0], room_center)

solver.constraints = []
mirror[0].position = [4.9885125160217285, 2.8499999046325684, 0.550000011920929]
mirror[0].rotation = [0, 0, -3.1390517375834066]
mirror[0].optimize = 2
eucalyptus_stem_B[0].position = [4.539999961853027, 3.0, 1.4800000190734863]
eucalyptus_stem_B[0].rotation = [0, 0, -3.118803053451712]
eucalyptus_stem_B[0].optimize = 2
eucalyptus_stem_A[0].position = [4.5, 2.9600000381469727, 1.5149999856948853]
eucalyptus_stem_A[0].rotation = [0, 0, -3.118803053451712]
eucalyptus_stem_A[0].optimize = 2
print_A[0].position = [0.0067442841827869415, 2.200000047683716, 0.3499999940395355]
print_A[0].rotation = [0, 0, 0.0025409193727581954]
print_A[0].optimize = 2
hardcover_book_C[0].position = [4.519999980926514, 3.4200000762939453, 0.8799999356269836]
hardcover_book_C[0].rotation = [0, 0, 1.5935836929706761]
hardcover_book_C[0].optimize = 2
woven_linen_placemat_B[0].position = [2.7200000286102295, 2.200000047683716, 0.7649999856948853]
woven_linen_placemat_B[0].rotation = [0, 0, -3.1188052874140135]
woven_linen_placemat_B[0].optimize = 2
print_B[0].position = [1.0499999523162842, 3.993398666381836, 0.25]
print_B[0].rotation = [0, 0, -1.568255406200039]
print_B[0].optimize = 2
sideboard_cabinet[0].position = [4.750042915344238, 2.8499999046325684, 0.4099999964237213]
sideboard_cabinet[0].rotation = [0, 0, -3.1079412963154582]
sideboard_cabinet[0].optimize = 2
dining_table[0].position = [2.450000047683716, 2.200000047683716, 0.3799999952316284]
dining_table[0].rotation = [0, 0, 0.021991148286022624]
dining_table[0].optimize = 2
wall_sconce_C[0].position = [0.06043320894241333, 3.25, 0.1599999964237213]
wall_sconce_C[0].rotation = [0, 0, 0.002540920594857827]
wall_sconce_C[0].optimize = 2
fridge[0].position = [4.6391119956970215, 0.550000011920929, 0.925000011920929]
fridge[0].rotation = [0, 0, -3.1390517354391343]
fridge[0].optimize = 2
dining_chair_A[0].position = [1.5499999523162842, 2.200000047683716, 0.41999998688697815]
dining_chair_A[0].rotation = [0, 0, 0.01884955539881635]
dining_chair_A[0].optimize = 2
painting[0].position = [2.5999999046325684, 3.978602409362793, 0.375]
painting[0].rotation = [0, 0, -1.5682554150770527]
painting[0].optimize = 2
bar_cart[0].position = [0.21327772736549377, 3.3499999046325684, 0.4399999976158142]
bar_cart[0].rotation = [0, 0, 0.00876222003371272]
bar_cart[0].optimize = 2
art_print[0].position = [3.0999999046325684, 0.00674373097717762, 0.30000001192092896]
art_print[0].rotation = [0, 0, 1.5733372480120014]
art_print[0].optimize = 2
wax_candle[0].position = [0.3199999928474426, 3.3499999046325684, 0.9399999976158142]
wax_candle[0].rotation = [0, 0, 0.02278736617577962]
wax_candle[0].optimize = 2
wall_clock[0].position = [4.300000190734863, 3.9839017391204834, 0.1899999976158142]
wall_clock[0].rotation = [0, 0, -1.568255406200039]
wall_clock[0].optimize = 2
hardcover_book_A[0].position = [4.539872646331787, 2.280874490737915, 0.8399999737739563]
hardcover_book_A[0].rotation = [0, 0, 1.5733375330041495]
hardcover_book_A[0].optimize = 2
hardcover_book_B[0].position = [4.519999980926514, 3.4200000762939453, 0.8399999737739563]
hardcover_book_B[0].rotation = [0, 0, 1.5795590520597096]
hardcover_book_B[0].optimize = 2
storage_box[0].position = [1.9500000476837158, 0.30000001192092896, 0.11999999731779099]
storage_box[0].rotation = [0, 0, 1.5904106397931752]
storage_box[0].optimize = 2
cylinder_vase[0].position = [4.519999980926514, 2.9800000190734863, 0.9800000190734863]
cylinder_vase[0].rotation = [0, 0, -3.1061125755754975]
cylinder_vase[0].optimize = 2
wall_sconce_A[0].position = [1.899999976158142, 3.9395639896392822, 0.1599999964237213]
wall_sconce_A[0].rotation = [0, 0, -1.5682554052778654]
wall_sconce_A[0].optimize = 2
glass_tumbler_A[0].position = [2.180000066757202, 2.5799999237060547, 0.8149999976158142]
glass_tumbler_A[0].rotation = [0, 0, 0.02278736617577962]
glass_tumbler_A[0].optimize = 2
entry_bench[0].position = [1.100000023841858, 0.21338754892349243, 0.23999999463558197]
entry_bench[0].rotation = [0, 0, 1.576447842277141]
entry_bench[0].optimize = 2
glass_tumbler_B[0].position = [2.7200000286102295, 1.8200000524520874, 0.8149999976158142]
glass_tumbler_B[0].rotation = [0, 0, -3.1188052874140135]
glass_tumbler_B[0].optimize = 2
dining_chair_B[0].position = [3.3499999046325684, 2.200000047683716, 0.41999998688697815]
dining_chair_B[0].rotation = [0, 0, -3.122743098190977]
dining_chair_B[0].optimize = 2
floor_lamp[0].position = [3.75, 0.3499999940395355, 0.824999988079071]
floor_lamp[0].rotation = [0, 0, 1.5802211042556205]
floor_lamp[0].optimize = 2
woven_linen_placemat_A[0].position = [2.180000066757202, 2.200000047683716, 0.7649999856948853]
woven_linen_placemat_A[0].rotation = [0, 0, 0.02278736617577962]
woven_linen_placemat_A[0].optimize = 2
catchall_bowl[0].position = [4.519999980926514, 2.7200000286102295, 0.8600000143051147]
catchall_bowl[0].rotation = [0, 0, -3.1188017051163435]
catchall_bowl[0].optimize = 2
potted_succulent_plant[0].position = [4.519999980926514, 3.1500000953674316, 0.9300000071525574]
potted_succulent_plant[0].rotation = [0, 0, -3.1188017051163435]
potted_succulent_plant[0].optimize = 2
wall_sconce_B[0].position = [3.299999952316284, 3.9395639896392822, 0.1599999964237213]
wall_sconce_B[0].rotation = [0, 0, -1.5682554052778654]
wall_sconce_B[0].optimize = 2

