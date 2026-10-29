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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.60, 0.00, 0.00]),
    Wall(corner1=[4.60, 0.00, 0.00], corner2=[4.60, 4.00, 0.00]),
    Wall(corner1=[4.60, 4.00, 0.00], corner2=[0.00, 4.00, 0.00]),
    Wall(corner1=[0.00, 4.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
eucalyptus_bunch = Assets(description="eucalyptus bunch", size=[0.20, 0.25, 0.45], placements=[AssetInstance() for _ in range(1)])
mirror = Assets(description="mirror", size=[0.04, 0.75, 1.00], placements=[AssetInstance() for _ in range(1)])
jar_candle = Assets(description="jar candle", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
catchall_dish_A = Assets(description="catchall dish", size=[0.13, 0.18, 0.03], placements=[AssetInstance() for _ in range(1)])
armchair = Assets(description="armchair", size=[0.82, 0.78, 0.85], placements=[AssetInstance() for _ in range(1)])
nightstand_A = Assets(description="nightstand", size=[0.40, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
catchall_dish_B = Assets(description="catchall dish", size=[0.12, 0.14, 0.03], placements=[AssetInstance() for _ in range(1)])
bud_vase = Assets(description="bud vase", size=[0.09, 0.09, 0.18], placements=[AssetInstance() for _ in range(1)])
clock = Assets(description="clock", size=[0.04, 0.30, 0.30], placements=[AssetInstance() for _ in range(1)])
dresser = Assets(description="dresser", size=[0.45, 1.10, 0.85], placements=[AssetInstance() for _ in range(1)])
photograph = Assets(description="photograph", size=[0.03, 0.25, 0.30], placements=[AssetInstance() for _ in range(1)])
art_print_A = Assets(description="art print", size=[0.03, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
ballpoint_pen = Assets(description="ballpoint pen", size=[0.14, 0.01, 0.01], placements=[AssetInstance() for _ in range(1)])
print = Assets(description="print", size=[0.03, 0.40, 0.50], placements=[AssetInstance() for _ in range(1)])
floor_lamp = Assets(description="floor lamp", size=[0.35, 0.35, 1.55], placements=[AssetInstance() for _ in range(1)])
hand_lotion_pump_bottle = Assets(description="hand lotion pump bottle", size=[0.07, 0.07, 0.18], placements=[AssetInstance() for _ in range(1)])
glass_tumbler = Assets(description="glass tumbler", size=[0.08, 0.08, 0.10], placements=[AssetInstance() for _ in range(1)])
paperback_book_A = Assets(description="paperback book", size=[0.20, 0.13, 0.03], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.10, 1.60, 1.05], placements=[AssetInstance() for _ in range(1)])
nightstand_B = Assets(description="nightstand", size=[0.40, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
art_print_B = Assets(description="art print", size=[0.03, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
writing_desk = Assets(description="writing desk", size=[0.50, 1.00, 0.75], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.60, 1.20, 2.10], placements=[AssetInstance() for _ in range(1)])
travertine_stone_coaster = Assets(description="travertine stone coaster", size=[0.10, 0.10, 0.01], placements=[AssetInstance() for _ in range(1)])
paperback_book_B = Assets(description="paperback book", size=[0.20, 0.13, 0.03], placements=[AssetInstance() for _ in range(1)])
a5_notebook = Assets(description="a5 notebook", size=[0.21, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
side_table = Assets(description="side table", size=[0.40, 0.40, 0.50], placements=[AssetInstance() for _ in range(1)])
art_print_C = Assets(description="art print", size=[0.03, 0.40, 0.50], placements=[AssetInstance() for _ in range(1)])
desk_chair = Assets(description="desk chair", size=[0.55, 0.50, 0.82], placements=[AssetInstance() for _ in range(1)])
catchall_dish_C = Assets(description="catchall dish", size=[0.12, 0.16, 0.03], placements=[AssetInstance() for _ in range(1)])

eucalyptus_bunch[0].instance_id = 'eucalyptus_bunch_0'
mirror[0].instance_id = 'mirror_0'
jar_candle[0].instance_id = 'jar_candle_0'
catchall_dish_A[0].instance_id = 'catchall_dish_A_0'
armchair[0].instance_id = 'armchair_0'
nightstand_A[0].instance_id = 'nightstand_A_0'
catchall_dish_B[0].instance_id = 'catchall_dish_B_0'
bud_vase[0].instance_id = 'bud_vase_0'
clock[0].instance_id = 'clock_0'
dresser[0].instance_id = 'dresser_0'
photograph[0].instance_id = 'photograph_0'
art_print_A[0].instance_id = 'art_print_A_0'
ballpoint_pen[0].instance_id = 'ballpoint_pen_0'
print[0].instance_id = 'print_0'
floor_lamp[0].instance_id = 'floor_lamp_0'
hand_lotion_pump_bottle[0].instance_id = 'hand_lotion_pump_bottle_0'
glass_tumbler[0].instance_id = 'glass_tumbler_0'
paperback_book_A[0].instance_id = 'paperback_book_A_0'
bed[0].instance_id = 'bed_0'
nightstand_B[0].instance_id = 'nightstand_B_0'
art_print_B[0].instance_id = 'art_print_B_0'
writing_desk[0].instance_id = 'writing_desk_0'
wardrobe[0].instance_id = 'wardrobe_0'
travertine_stone_coaster[0].instance_id = 'travertine_stone_coaster_0'
paperback_book_B[0].instance_id = 'paperback_book_B_0'
a5_notebook[0].instance_id = 'a5_notebook_0'
side_table[0].instance_id = 'side_table_0'
art_print_C[0].instance_id = 'art_print_C_0'
desk_chair[0].instance_id = 'desk_chair_0'
catchall_dish_C[0].instance_id = 'catchall_dish_C_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

eucalyptus_bunch[0].position = [0.8930379243363759, 3.889613927047501, 0.225]
eucalyptus_bunch[0].rotation = [0, 0, 0]
mirror[0].position = [3.6294364597163877, 0.4514617499884652, 0.5]
mirror[0].rotation = [0, 0, 0]
jar_candle[0].position = [4.493784561557142, 0.3665567244225385, 0.055]
jar_candle[0].rotation = [0, 0, 0]
catchall_dish_A[0].position = [2.2626746266359747, 0.2520168374376732, 0.015]
catchall_dish_A[0].rotation = [0, 0, 0]
armchair[0].position = [4.290741024764399, 0.19172834387111726, 0.425]
armchair[0].rotation = [0, 0, 0]
nightstand_A[0].position = [0.9001834378108954, 3.4654024815590083, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
catchall_dish_B[0].position = [0.5817002713583899, 0.8551880612692337, 0.015]
catchall_dish_B[0].rotation = [0, 0, 0]
bud_vase[0].position = [0.6591680110450681, 0.8296278063221489, 0.09]
bud_vase[0].rotation = [0, 0, 0]
clock[0].position = [2.3689706406246085, 0.12748724086323104, 0.15]
clock[0].rotation = [0, 0, 0]
dresser[0].position = [1.1423451318242828, 1.7155243003841734, 0.425]
dresser[0].rotation = [0, 0, 0]
photograph[0].position = [4.485636342894952, 0.13123274382699934, 0.15]
photograph[0].rotation = [0, 0, 0]
art_print_A[0].position = [0.6670139913779453, 2.166686523572681, 0.35]
art_print_A[0].rotation = [0, 0, 0]
ballpoint_pen[0].position = [0.13930265609722278, 0.29275215847807123, 0.007]
ballpoint_pen[0].rotation = [0, 0, 0]
print[0].position = [3.093503298921847, 0.7973157872396794, 0.25]
print[0].rotation = [0, 0, 0]
floor_lamp[0].position = [0.24777018637727782, 2.9708499069739385, 0.775]
floor_lamp[0].rotation = [0, 0, 0]
hand_lotion_pump_bottle[0].position = [3.5481685333461, 0.6768901934702627, 0.09]
hand_lotion_pump_bottle[0].rotation = [0, 0, 0]
glass_tumbler[0].position = [0.9532078944294367, 1.267155793563171, 0.05]
glass_tumbler[0].rotation = [0, 0, 0]
paperback_book_A[0].position = [2.194050057510595, 0.5323453503310116, 0.0125]
paperback_book_A[0].rotation = [0, 0, 0]
bed[0].position = [4.064805849494891, 1.6459223218019141, 0.525]
bed[0].rotation = [0, 0, 0]
nightstand_B[0].position = [1.1842187879076183, 2.468260468208585, 0.275]
nightstand_B[0].rotation = [0, 0, 0]
art_print_B[0].position = [3.5690970365770758, 1.3383921065566495, 0.4]
art_print_B[0].rotation = [0, 0, 0]
writing_desk[0].position = [1.305127308168491, 2.5804990496718383, 0.375]
writing_desk[0].rotation = [0, 0, 0]
wardrobe[0].position = [1.5329372873225042, 2.269217353597026, 1.05]
wardrobe[0].rotation = [0, 0, 0]
travertine_stone_coaster[0].position = [4.513277639125231, 1.4393567961809897, 0.005]
travertine_stone_coaster[0].rotation = [0, 0, 0]
paperback_book_B[0].position = [2.064958773285467, 2.7760236991237184, 0.0125]
paperback_book_B[0].rotation = [0, 0, 0]
a5_notebook[0].position = [0.12992281116013996, 3.2482309936337486, 0.0075]
a5_notebook[0].rotation = [0, 0, 0]
side_table[0].position = [2.0431776828764825, 2.6074410237585592, 0.25]
side_table[0].rotation = [0, 0, 0]
art_print_C[0].position = [3.989965856194923, 0.39889463872556785, 0.25]
art_print_C[0].rotation = [0, 0, 0]
desk_chair[0].position = [3.098565824418113, 0.7764359249945945, 0.41]
desk_chair[0].rotation = [0, 0, 0]
catchall_dish_C[0].position = [3.4767435747200066, 2.561444581146834, 0.015]
catchall_dish_C[0].rotation = [0, 0, 0]
eucalyptus_bunch[0].position = [0.8930379243363759, 3.889613927047501, 0.225]
eucalyptus_bunch[0].rotation = [0, 0, 0]
mirror[0].position = [3.6294364597163877, 0.4514617499884652, 0.5]
mirror[0].rotation = [0, 0, 0]
jar_candle[0].position = [4.493784561557142, 0.3665567244225385, 0.055]
jar_candle[0].rotation = [0, 0, 0]
catchall_dish_A[0].position = [2.2626746266359747, 0.2520168374376732, 0.015]
catchall_dish_A[0].rotation = [0, 0, 0]
armchair[0].position = [4.290741024764399, 0.19172834387111726, 0.425]
armchair[0].rotation = [0, 0, 0]
nightstand_A[0].position = [0.9001834378108954, 3.4654024815590083, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
catchall_dish_B[0].position = [0.5817002713583899, 0.8551880612692337, 0.015]
catchall_dish_B[0].rotation = [0, 0, 0]
bud_vase[0].position = [0.6591680110450681, 0.8296278063221489, 0.09]
bud_vase[0].rotation = [0, 0, 0]
clock[0].position = [2.3689706406246085, 0.12748724086323104, 0.15]
clock[0].rotation = [0, 0, 0]
dresser[0].position = [1.1423451318242828, 1.7155243003841734, 0.425]
dresser[0].rotation = [0, 0, 0]
photograph[0].position = [4.485636342894952, 0.13123274382699934, 0.15]
photograph[0].rotation = [0, 0, 0]
art_print_A[0].position = [0.6670139913779453, 2.166686523572681, 0.35]
art_print_A[0].rotation = [0, 0, 0]
ballpoint_pen[0].position = [0.13930265609722278, 0.29275215847807123, 0.007]
ballpoint_pen[0].rotation = [0, 0, 0]
print[0].position = [3.093503298921847, 0.7973157872396794, 0.25]
print[0].rotation = [0, 0, 0]
floor_lamp[0].position = [0.24777018637727782, 2.9708499069739385, 0.775]
floor_lamp[0].rotation = [0, 0, 0]
hand_lotion_pump_bottle[0].position = [3.5481685333461, 0.6768901934702627, 0.09]
hand_lotion_pump_bottle[0].rotation = [0, 0, 0]
glass_tumbler[0].position = [0.9532078944294367, 1.267155793563171, 0.05]
glass_tumbler[0].rotation = [0, 0, 0]
paperback_book_A[0].position = [2.194050057510595, 0.5323453503310116, 0.0125]
paperback_book_A[0].rotation = [0, 0, 0]
bed[0].position = [4.064805849494891, 1.6459223218019141, 0.525]
bed[0].rotation = [0, 0, 0]
nightstand_B[0].position = [1.1842187879076183, 2.468260468208585, 0.275]
nightstand_B[0].rotation = [0, 0, 0]
art_print_B[0].position = [3.5690970365770758, 1.3383921065566495, 0.4]
art_print_B[0].rotation = [0, 0, 0]
writing_desk[0].position = [1.305127308168491, 2.5804990496718383, 0.375]
writing_desk[0].rotation = [0, 0, 0]
wardrobe[0].position = [1.5329372873225042, 2.269217353597026, 1.05]
wardrobe[0].rotation = [0, 0, 0]
travertine_stone_coaster[0].position = [4.513277639125231, 1.4393567961809897, 0.005]
travertine_stone_coaster[0].rotation = [0, 0, 0]
paperback_book_B[0].position = [2.064958773285467, 2.7760236991237184, 0.0125]
paperback_book_B[0].rotation = [0, 0, 0]
a5_notebook[0].position = [0.12992281116013996, 3.2482309936337486, 0.0075]
a5_notebook[0].rotation = [0, 0, 0]
side_table[0].position = [2.0431776828764825, 2.6074410237585592, 0.25]
side_table[0].rotation = [0, 0, 0]
art_print_C[0].position = [3.989965856194923, 0.39889463872556785, 0.25]
art_print_C[0].rotation = [0, 0, 0]
desk_chair[0].position = [3.098565824418113, 0.7764359249945945, 0.41]
desk_chair[0].rotation = [0, 0, 0]
catchall_dish_C[0].position = [3.4767435747200066, 2.561444581146834, 0.015]
catchall_dish_C[0].rotation = [0, 0, 0]

solver.constraints = []

from math import atan2, sqrt

# Coordinates follow the supplied boundary: x=0..4.60, y=0..4.00.
# The bed occupies the west side; storage occupies the east side.
# A south-wall work area and southeast reading area leave a central aisle.
def set_layout(asset, xyz, yaw=0.0):
    instance = asset[0]
    instance.position = list(xyz)
    instance.rotation = [0.0, 0.0, yaw]

    # Fixed references preserve the chosen non-overlapping arrangement.
    # Each instance receives both a position and an orientation constraint.
    reference = AssetInstance(
        position=list(xyz),
        rotation=[0.0, 0.0, yaw],
    )
    solver.distance_constraint(instance, reference, 0.0, 0.0, weight=10)
    solver.align_with(instance, reference)


# Bed length runs along x. Its head is against the west wall.
set_layout(bed, [1.05, 2.55, 0.525])
solver.against_wall(bed[0], walls[3])

# Matching nightstands flank the head of the bed, with small side gaps.
set_layout(nightstand_A, [0.20, 1.425, 0.275])
set_layout(nightstand_B, [0.20, 3.675, 0.275])
solver.against_wall(nightstand_A[0], walls[3])
solver.against_wall(nightstand_B[0], walls[3])
solver.align_with(nightstand_A[0], bed[0])
solver.align_with(nightstand_B[0], bed[0])

# East-wall storage faces west; wardrobe doors and dresser drawers open
# toward the central circulation space.
set_layout(wardrobe, [4.30, 3.30, 1.05], radians(180))
set_layout(dresser, [4.375, 1.95, 0.425], radians(180))
solver.against_wall(wardrobe[0], walls[1])
solver.against_wall(dresser[0], walls[1])

# Desk faces into the room. The chair faces south toward the desktop.
set_layout(writing_desk, [1.50, 0.25, 0.375], radians(90))
solver.against_wall(writing_desk[0], walls[0])
set_layout(desk_chair, [1.50, 1.00, 0.410], radians(-90))
solver.point_towards(desk_chair[0], writing_desk[0])
solver.distance_constraint(
    desk_chair[0], writing_desk[0], 0.70, 0.85, weight=10
)

# The armchair points directly toward the bed, without entering its footprint.
reading_yaw = atan2(2.55 - 0.75, 1.05 - 3.30)
set_layout(armchair, [3.30, 0.75, 0.425], reading_yaw)
solver.point_towards(armchair[0], bed[0])

set_layout(side_table, [2.45, 0.45, 0.25])
set_layout(floor_lamp, [4.15, 0.45, 0.775])
solver.point_towards(side_table[0], armchair[0], angle=0)
solver.point_towards(floor_lamp[0], armchair[0])

# Keep the reading table within reach, and the lamp outside the chair footprint.
solver.distance_constraint(side_table[0], armchair[0], 0.85, 1.00)
solver.distance_constraint(floor_lamp[0], armchair[0], 0.90, 1.05)

# Wall-mounted pieces have explicitly assigned elevations, not floor placement.
# Their thin local x dimension is perpendicular to the supporting wall.
set_layout(mirror, [4.58, 0.70, 1.45], radians(180))
solver.against_wall(mirror[0], walls[1])

set_layout(art_print_A, [0.015, 2.55, 1.80])
solver.against_wall(art_print_A[0], walls[3])

set_layout(print, [0.015, 3.65, 1.35])
solver.against_wall(print[0], walls[3])

set_layout(art_print_B, [1.50, 0.015, 1.55], radians(90))
solver.against_wall(art_print_B[0], walls[0])

set_layout(art_print_C, [3.05, 3.985, 1.50], radians(-90))
solver.against_wall(art_print_C[0], walls[2])


# Surface accessories: the helper places each bounding-box bottom exactly
# on its supporting surface and gives each a position/orientation constraint.
def place_on_surface(asset, support, x, y, yaw=0.0):
    surface_z = support[0].position[2] + support.size[2] / 2
    set_layout(
        asset,
        [x, y, surface_z + asset.size[2] / 2],
        yaw,
    )
    solver.on_top_of(asset[0], support[0])


# First bedside surface: book at the front, candle and dish at the back.
place_on_surface(paperback_book_A, nightstand_A, 0.20, 1.39)
place_on_surface(jar_candle, nightstand_A, 0.09, 1.56)
place_on_surface(catchall_dish_A, nightstand_A, 0.29, 1.55)

# Second bedside surface: book, drink on a coaster, and lotion.
place_on_surface(paperback_book_B, nightstand_B, 0.24, 3.56)
place_on_surface(travertine_stone_coaster, nightstand_B, 0.10, 3.80)
place_on_surface(glass_tumbler, travertine_stone_coaster, 0.10, 3.80)
place_on_surface(hand_lotion_pump_bottle, nightstand_B, 0.30, 3.80)

# Dresser accessories are separated along its long axis.
place_on_surface(clock, dresser, 4.40, 1.65, radians(180))
place_on_surface(photograph, dresser, 4.40, 1.98, radians(180))
place_on_surface(eucalyptus_bunch, dresser, 4.35, 2.30)

# Desktop accessories leave the chair-facing edge available for working.
place_on_surface(bud_vase, writing_desk, 1.10, 0.25)
place_on_surface(a5_notebook, writing_desk, 1.40, 0.25, radians(90))
place_on_surface(ballpoint_pen, writing_desk, 1.60, 0.25, radians(90))
place_on_surface(catchall_dish_B, writing_desk, 1.82, 0.25)

# A small catchall on the reading table remains within easy reach.
place_on_surface(catchall_dish_C, side_table, 2.45, 0.45)

# Additional relational constraints preserve the bed-between-nightstands
# arrangement alongside the stronger absolute placement constraints.
for bedside_asset in (nightstand_A, nightstand_B):
    bedside_distance = sqrt(sum(
        (bedside_asset[0].position[axis] - bed[0].position[axis]) ** 2
        for axis in range(3)
    ))
    solver.distance_constraint(
        bedside_asset[0], bed[0],
        bedside_distance - 0.02, bedside_distance + 0.02,
        weight=10,
    )

solver.constraints = []
glass_tumbler[0].position = [0.10000000149011612, 3.799999952316284, 0.6100000143051147]
glass_tumbler[0].rotation = [0, 0, 0.01256637125682779]
glass_tumbler[0].optimize = 2
eucalyptus_bunch[0].position = [4.349999904632568, 2.299999952316284, 1.0750000476837158]
eucalyptus_bunch[0].rotation = [0, 0, 0.01256637125682779]
eucalyptus_bunch[0].optimize = 2
side_table[0].position = [2.450000047683716, 0.44999998807907104, 0.25]
side_table[0].rotation = [0, 0, 0.01884955539881635]
side_table[0].optimize = 2
art_print_C[0].position = [3.049999952316284, 3.993398666381836, 0.25]
art_print_C[0].rotation = [0, 0, -1.568255406200039]
art_print_C[0].optimize = 2
a5_notebook[0].position = [1.399999976158142, 0.25, 0.7549999952316284]
a5_notebook[0].rotation = [0, 0, 1.5833626980517244]
a5_notebook[0].optimize = 2
armchair[0].position = [3.299999952316284, 0.75, 0.42500001192092896]
armchair[0].rotation = [0, 0, 2.491984474485854]
armchair[0].optimize = 2
dresser[0].position = [4.372960090637207, 1.9500000476837158, 0.42500001192092896]
dresser[0].rotation = [0, 0, -3.1297196374414225]
dresser[0].optimize = 2
catchall_dish_A[0].position = [0.28999999165534973, 1.5499999523162842, 0.5649999976158142]
catchall_dish_A[0].rotation = [0, 0, 0.01256637125682779]
catchall_dish_A[0].optimize = 2
paperback_book_A[0].position = [0.20000000298023224, 1.3899999856948853, 0.5649999976158142]
paperback_book_A[0].rotation = [0, 0, 0.01256637125682779]
paperback_book_A[0].optimize = 2
catchall_dish_B[0].position = [1.8200000524520874, 0.25, 0.7649999856948853]
catchall_dish_B[0].rotation = [0, 0, 0.01256637125682779]
catchall_dish_B[0].optimize = 2
paperback_book_B[0].position = [0.23999999463558197, 3.559999942779541, 0.5649999976158142]
paperback_book_B[0].rotation = [0, 0, 0.01256637125682779]
paperback_book_B[0].optimize = 2
bed[0].position = [1.0621968507766724, 2.549999952316284, 0.5249999761581421]
bed[0].rotation = [0, 0, 0.01809490196969095]
bed[0].optimize = 2
desk_chair[0].position = [1.5, 1.0, 0.4099999964237213]
desk_chair[0].rotation = [0, 0, -1.5550883628776802]
desk_chair[0].optimize = 2
print[0].position = [0.006743067875504494, 3.6500000953674316, 0.25]
print[0].rotation = [0, 0, 0.002540920594857827]
print[0].optimize = 2
photograph[0].position = [4.400000095367432, 1.9800000190734863, 1.0]
photograph[0].rotation = [0, 0, -3.1290262823329655]
photograph[0].optimize = 2
travertine_stone_coaster[0].position = [0.10000000149011612, 3.799999952316284, 0.5550000071525574]
travertine_stone_coaster[0].rotation = [0, 0, 0.0157079639172164]
travertine_stone_coaster[0].optimize = 2
clock[0].position = [4.400000095367432, 1.649999976158142, 1.0]
clock[0].rotation = [0, 0, -3.1290262823329655]
clock[0].optimize = 2
nightstand_A[0].position = [0.20403838157653809, 1.4249999523162842, 0.2750000059604645]
nightstand_A[0].rotation = [0, 0, 0.018094915463557966]
nightstand_A[0].optimize = 2
ballpoint_pen[0].position = [1.600000023841858, 0.25, 0.7549999952316284]
ballpoint_pen[0].rotation = [0, 0, 1.5833626980517244]
ballpoint_pen[0].optimize = 2
mirror[0].position = [4.5886969566345215, 0.699999988079071, 0.5]
mirror[0].rotation = [0, 0, -3.1390517363613077]
mirror[0].optimize = 2
wardrobe[0].position = [4.298476219177246, 3.299999952316284, 1.0499999523162842]
wardrobe[0].rotation = [0, 0, -3.1390517430940474]
wardrobe[0].optimize = 2
nightstand_B[0].position = [0.20403838157653809, 3.674999952316284, 0.2750000059604645]
nightstand_B[0].rotation = [0, 0, 0.018094915463557966]
nightstand_B[0].optimize = 2
bud_vase[0].position = [1.100000023841858, 0.25, 0.8400000333786011]
bud_vase[0].rotation = [0, 0, 0.01256637125682779]
bud_vase[0].optimize = 2
writing_desk[0].position = [1.5, 0.25558218359947205, 0.375]
writing_desk[0].rotation = [0, 0, 1.5920023264999437]
writing_desk[0].optimize = 2
art_print_A[0].position = [0.0067442841827869415, 2.549999952316284, 0.3499999940395355]
art_print_A[0].rotation = [0, 0, 0.0025409193727581954]
art_print_A[0].optimize = 2
floor_lamp[0].position = [4.150000095367432, 0.44999998807907104, 0.7749999761581421]
floor_lamp[0].rotation = [0, 0, 0.025964310904163113]
floor_lamp[0].optimize = 2
hand_lotion_pump_bottle[0].position = [0.30000001192092896, 3.799999952316284, 0.6399999856948853]
hand_lotion_pump_bottle[0].rotation = [0, 0, 0.01256637125682779]
hand_lotion_pump_bottle[0].optimize = 2
art_print_B[0].position = [1.5, 0.0067442841827869415, 0.4000000059604645]
art_print_B[0].rotation = [0, 0, 1.573337246167655]
art_print_B[0].optimize = 2
catchall_dish_C[0].position = [2.450000047683716, 0.44999998807907104, 0.5149999856948853]
catchall_dish_C[0].rotation = [0, 0, 0.01256637125682779]
catchall_dish_C[0].optimize = 2
jar_candle[0].position = [0.09000000357627869, 1.559999942779541, 0.6050000190734863]
jar_candle[0].rotation = [0, 0, 0.01256637125682779]
jar_candle[0].optimize = 2

