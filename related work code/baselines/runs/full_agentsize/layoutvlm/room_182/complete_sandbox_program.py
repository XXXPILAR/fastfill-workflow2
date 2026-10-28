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
eucalyptus_bunch = Assets(description="eucalyptus bunch", size=[0.25, 0.35, 0.65], placements=[AssetInstance() for _ in range(1)])
mirror = Assets(description="mirror", size=[0.04, 0.80, 1.10], placements=[AssetInstance() for _ in range(1)])
jar_candle = Assets(description="jar candle", size=[0.09, 0.09, 0.10], placements=[AssetInstance() for _ in range(1)])
catchall_dish_A = Assets(description="catchall dish", size=[0.14, 0.18, 0.03], placements=[AssetInstance() for _ in range(1)])
armchair = Assets(description="armchair", size=[0.88, 0.82, 0.87], placements=[AssetInstance() for _ in range(1)])
nightstand_A = Assets(description="nightstand", size=[0.42, 0.50, 0.58], placements=[AssetInstance() for _ in range(1)])
catchall_dish_B = Assets(description="catchall dish", size=[0.15, 0.20, 0.04], placements=[AssetInstance() for _ in range(1)])
bud_vase = Assets(description="bud vase", size=[0.10, 0.10, 0.22], placements=[AssetInstance() for _ in range(1)])
clock = Assets(description="clock", size=[0.05, 0.32, 0.32], placements=[AssetInstance() for _ in range(1)])
dresser = Assets(description="dresser", size=[0.50, 1.40, 0.82], placements=[AssetInstance() for _ in range(1)])
photograph = Assets(description="photograph", size=[0.03, 0.40, 0.30], placements=[AssetInstance() for _ in range(1)])
art_print_A = Assets(description="art print", size=[0.03, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
ballpoint_pen = Assets(description="ballpoint pen", size=[0.01, 0.14, 0.01], placements=[AssetInstance() for _ in range(1)])
print = Assets(description="print", size=[0.03, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
floor_lamp = Assets(description="floor lamp", size=[0.42, 0.42, 1.65], placements=[AssetInstance() for _ in range(1)])
hand_lotion_pump_bottle = Assets(description="hand lotion pump bottle", size=[0.07, 0.07, 0.20], placements=[AssetInstance() for _ in range(1)])
glass_tumbler = Assets(description="glass tumbler", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
paperback_book_A = Assets(description="paperback book", size=[0.20, 0.13, 0.03], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.10, 1.65, 1.10], placements=[AssetInstance() for _ in range(1)])
nightstand_B = Assets(description="nightstand", size=[0.42, 0.50, 0.58], placements=[AssetInstance() for _ in range(1)])
art_print_B = Assets(description="art print", size=[0.03, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
writing_desk = Assets(description="writing desk", size=[0.62, 1.25, 0.76], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.62, 1.80, 2.20], placements=[AssetInstance() for _ in range(1)])
travertine_stone_coaster = Assets(description="travertine stone coaster", size=[0.10, 0.10, 0.01], placements=[AssetInstance() for _ in range(1)])
paperback_book_B = Assets(description="paperback book", size=[0.20, 0.13, 0.03], placements=[AssetInstance() for _ in range(1)])
a5_notebook = Assets(description="a5 notebook", size=[0.21, 0.15, 0.02], placements=[AssetInstance() for _ in range(1)])
side_table = Assets(description="side table", size=[0.45, 0.45, 0.52], placements=[AssetInstance() for _ in range(1)])
art_print_C = Assets(description="art print", size=[0.03, 0.40, 0.50], placements=[AssetInstance() for _ in range(1)])
desk_chair = Assets(description="desk chair", size=[0.58, 0.58, 0.90], placements=[AssetInstance() for _ in range(1)])
catchall_dish_C = Assets(description="catchall dish", size=[0.14, 0.18, 0.03], placements=[AssetInstance() for _ in range(1)])

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

eucalyptus_bunch[0].position = [3.3494583689366997, 1.2287121059175772, 0.325]
eucalyptus_bunch[0].rotation = [0, 0, 0]
mirror[0].position = [2.042772367611083, 3.292852026331218, 0.55]
mirror[0].rotation = [0, 0, 0]
jar_candle[0].position = [0.4731722956013882, 0.9638603676106956, 0.05]
jar_candle[0].rotation = [0, 0, 0]
catchall_dish_A[0].position = [2.5334910323926674, 2.947782934783337, 0.015]
catchall_dish_A[0].rotation = [0, 0, 0]
armchair[0].position = [4.547567609791796, 1.4249926631418535, 0.435]
armchair[0].rotation = [0, 0, 0]
nightstand_A[0].position = [2.348755990855074, 0.766558605776531, 0.29]
nightstand_A[0].rotation = [0, 0, 0]
catchall_dish_B[0].position = [0.6206208428979478, 3.3053965919913497, 0.02]
catchall_dish_B[0].rotation = [0, 0, 0]
bud_vase[0].position = [1.170808081112212, 0.6509350100063864, 0.11]
bud_vase[0].rotation = [0, 0, 0]
clock[0].position = [1.1659780921284568, 1.257295071151908, 0.16]
clock[0].rotation = [0, 0, 0]
dresser[0].position = [4.4897155156162025, 0.931540394087663, 0.41]
dresser[0].rotation = [0, 0, 0]
photograph[0].position = [3.2527053005483957, 0.9016667244941514, 0.15]
photograph[0].rotation = [0, 0, 0]
art_print_A[0].position = [2.5522240473080244, 1.2189877120828347, 0.35]
art_print_A[0].rotation = [0, 0, 0]
ballpoint_pen[0].position = [0.7614920298768778, 3.0252672987147364, 0.006]
ballpoint_pen[0].rotation = [0, 0, 0]
print[0].position = [0.3141264699310045, 1.6657996326961664, 0.4]
print[0].rotation = [0, 0, 0]
floor_lamp[0].position = [1.5050767511815124, 2.475480056321924, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
hand_lotion_pump_bottle[0].position = [2.9591522376649704, 3.644410111648815, 0.1]
hand_lotion_pump_bottle[0].rotation = [0, 0, 0]
glass_tumbler[0].position = [4.538081182737917, 2.4873132787414542, 0.055]
glass_tumbler[0].rotation = [0, 0, 0]
paperback_book_A[0].position = [2.8562055621256883, 3.378285408116227, 0.0125]
paperback_book_A[0].rotation = [0, 0, 0]
bed[0].position = [0.8895848076435917, 0.4441635738147891, 0.55]
bed[0].rotation = [0, 0, 0]
nightstand_B[0].position = [4.119973738387829, 2.8133870248174384, 0.29]
nightstand_B[0].rotation = [0, 0, 0]
art_print_B[0].position = [0.5298951776128212, 0.883807103627555, 0.35]
art_print_B[0].rotation = [0, 0, 0]
writing_desk[0].position = [1.0535784512337165, 0.2756905457946477, 0.38]
writing_desk[0].rotation = [0, 0, 0]
wardrobe[0].position = [4.0918224185884595, 2.731389987424547, 1.1]
wardrobe[0].rotation = [0, 0, 0]
travertine_stone_coaster[0].position = [2.8951335451937705, 0.7722983962780319, 0.006]
travertine_stone_coaster[0].rotation = [0, 0, 0]
paperback_book_B[0].position = [1.9305854294536908, 3.3393614713096405, 0.0125]
paperback_book_B[0].rotation = [0, 0, 0]
a5_notebook[0].position = [1.2828205373871422, 2.171405687025013, 0.009]
a5_notebook[0].rotation = [0, 0, 0]
side_table[0].position = [2.9693275013781784, 2.7053907792847296, 0.26]
side_table[0].rotation = [0, 0, 0]
art_print_C[0].position = [3.608465233242225, 1.5781706132967117, 0.25]
art_print_C[0].rotation = [0, 0, 0]
desk_chair[0].position = [0.02383432184943859, 0.416264102745314, 0.45]
desk_chair[0].rotation = [0, 0, 0]
catchall_dish_C[0].position = [1.1921499540476408, 0.9240970184171693, 0.015]
catchall_dish_C[0].rotation = [0, 0, 0]
eucalyptus_bunch[0].position = [3.3494583689366997, 1.2287121059175772, 0.325]
eucalyptus_bunch[0].rotation = [0, 0, 0]
mirror[0].position = [2.042772367611083, 3.292852026331218, 0.55]
mirror[0].rotation = [0, 0, 0]
jar_candle[0].position = [0.4731722956013882, 0.9638603676106956, 0.05]
jar_candle[0].rotation = [0, 0, 0]
catchall_dish_A[0].position = [2.5334910323926674, 2.947782934783337, 0.015]
catchall_dish_A[0].rotation = [0, 0, 0]
armchair[0].position = [4.547567609791796, 1.4249926631418535, 0.435]
armchair[0].rotation = [0, 0, 0]
nightstand_A[0].position = [2.348755990855074, 0.766558605776531, 0.29]
nightstand_A[0].rotation = [0, 0, 0]
catchall_dish_B[0].position = [0.6206208428979478, 3.3053965919913497, 0.02]
catchall_dish_B[0].rotation = [0, 0, 0]
bud_vase[0].position = [1.170808081112212, 0.6509350100063864, 0.11]
bud_vase[0].rotation = [0, 0, 0]
clock[0].position = [1.1659780921284568, 1.257295071151908, 0.16]
clock[0].rotation = [0, 0, 0]
dresser[0].position = [4.4897155156162025, 0.931540394087663, 0.41]
dresser[0].rotation = [0, 0, 0]
photograph[0].position = [3.2527053005483957, 0.9016667244941514, 0.15]
photograph[0].rotation = [0, 0, 0]
art_print_A[0].position = [2.5522240473080244, 1.2189877120828347, 0.35]
art_print_A[0].rotation = [0, 0, 0]
ballpoint_pen[0].position = [0.7614920298768778, 3.0252672987147364, 0.006]
ballpoint_pen[0].rotation = [0, 0, 0]
print[0].position = [0.3141264699310045, 1.6657996326961664, 0.4]
print[0].rotation = [0, 0, 0]
floor_lamp[0].position = [1.5050767511815124, 2.475480056321924, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
hand_lotion_pump_bottle[0].position = [2.9591522376649704, 3.644410111648815, 0.1]
hand_lotion_pump_bottle[0].rotation = [0, 0, 0]
glass_tumbler[0].position = [4.538081182737917, 2.4873132787414542, 0.055]
glass_tumbler[0].rotation = [0, 0, 0]
paperback_book_A[0].position = [2.8562055621256883, 3.378285408116227, 0.0125]
paperback_book_A[0].rotation = [0, 0, 0]
bed[0].position = [0.8895848076435917, 0.4441635738147891, 0.55]
bed[0].rotation = [0, 0, 0]
nightstand_B[0].position = [4.119973738387829, 2.8133870248174384, 0.29]
nightstand_B[0].rotation = [0, 0, 0]
art_print_B[0].position = [0.5298951776128212, 0.883807103627555, 0.35]
art_print_B[0].rotation = [0, 0, 0]
writing_desk[0].position = [1.0535784512337165, 0.2756905457946477, 0.38]
writing_desk[0].rotation = [0, 0, 0]
wardrobe[0].position = [4.0918224185884595, 2.731389987424547, 1.1]
wardrobe[0].rotation = [0, 0, 0]
travertine_stone_coaster[0].position = [2.8951335451937705, 0.7722983962780319, 0.006]
travertine_stone_coaster[0].rotation = [0, 0, 0]
paperback_book_B[0].position = [1.9305854294536908, 3.3393614713096405, 0.0125]
paperback_book_B[0].rotation = [0, 0, 0]
a5_notebook[0].position = [1.2828205373871422, 2.171405687025013, 0.009]
a5_notebook[0].rotation = [0, 0, 0]
side_table[0].position = [2.9693275013781784, 2.7053907792847296, 0.26]
side_table[0].rotation = [0, 0, 0]
art_print_C[0].position = [3.608465233242225, 1.5781706132967117, 0.25]
art_print_C[0].rotation = [0, 0, 0]
desk_chair[0].position = [0.02383432184943859, 0.416264102745314, 0.45]
desk_chair[0].rotation = [0, 0, 0]
catchall_dish_C[0].position = [1.1921499540476408, 0.9240970184171693, 0.015]
catchall_dish_C[0].rotation = [0, 0, 0]

solver.constraints = []

# The bed is centered on the north wall, with matching nightstands on either
# side. Its headboard is against the wall and its front faces into the room.
bed[0].position = [1.65, 2.95, 0.55]
bed[0].rotation = [0, 0, radians(-90)]

nightstand_A[0].position = [0.52, 3.75, 0.29]
nightstand_A[0].rotation = [0, 0, radians(-90)]

nightstand_B[0].position = [2.78, 3.75, 0.29]
nightstand_B[0].rotation = [0, 0, radians(-90)]

# Tall storage occupies the northeast wall, while the lower dresser occupies
# the southeast wall. Both face west into the room.
wardrobe[0].position = [4.29, 2.95, 1.10]
wardrobe[0].rotation = [0, 0, radians(180)]

dresser[0].position = [4.35, 0.75, 0.41]
dresser[0].rotation = [0, 0, radians(180)]

# The writing area is against the south wall. The chair faces the desk and
# leaves a usable gap for sitting.
writing_desk[0].position = [2.35, 0.31, 0.38]
writing_desk[0].rotation = [0, 0, radians(90)]

desk_chair[0].position = [2.35, 1.05, 0.45]
desk_chair[0].rotation = [0, 0, radians(-90)]

# A reading corner occupies the southwest portion of the room. The armchair is
# angled toward the bed as requested, with the side table and lamp nearby.
armchair[0].position = [0.70, 1.15, 0.435]
armchair[0].rotation = [0, 0, radians(62)]

side_table[0].position = [0.55, 0.28, 0.26]
side_table[0].rotation = [0, 0, 0]

floor_lamp[0].position = [3.45, 0.30, 0.825]
floor_lamp[0].rotation = [0, 0, radians(180)]

# Decorative wall pieces are elevated and face inward. The top-wall pieces face
# south; the left-wall pieces face east; the right-wall mirror faces west.
clock[0].position = [3.30, 3.975, 1.55]
clock[0].rotation = [0, 0, radians(-90)]

art_print_A[0].position = [1.30, 3.985, 1.60]
art_print_A[0].rotation = [0, 0, radians(-90)]

art_print_B[0].position = [2.15, 3.985, 1.60]
art_print_B[0].rotation = [0, 0, radians(-90)]

print[0].position = [0.015, 2.70, 1.55]
print[0].rotation = [0, 0, 0]

art_print_C[0].position = [0.015, 1.65, 1.45]
art_print_C[0].rotation = [0, 0, 0]

mirror[0].position = [4.58, 0.55, 1.55]
mirror[0].rotation = [0, 0, radians(180)]

# Small accessories are given explicit tabletop positions and elevations.
# The eucalyptus sits alone on the smaller left nightstand.
eucalyptus_bunch[0].position = [0.52, 3.75, 0.905]
eucalyptus_bunch[0].rotation = [0, 0, radians(-90)]

# The candle and small dish share the right nightstand without overlapping.
jar_candle[0].position = [2.88, 3.75, 0.63]
jar_candle[0].rotation = [0, 0, radians(-90)]

catchall_dish_A[0].position = [2.66, 3.75, 0.595]
catchall_dish_A[0].rotation = [0, 0, radians(-90)]

# Dresser accessories are spread along its long surface.
bud_vase[0].position = [4.35, 0.20, 0.93]
bud_vase[0].rotation = [0, 0, radians(180)]

hand_lotion_pump_bottle[0].position = [4.35, 0.45, 0.92]
hand_lotion_pump_bottle[0].rotation = [0, 0, radians(180)]

catchall_dish_C[0].position = [4.35, 0.72, 0.835]
catchall_dish_C[0].rotation = [0, 0, radians(180)]

photograph[0].position = [4.335, 1.20, 0.97]
photograph[0].rotation = [0, 0, radians(180)]

# Frequently used writing objects are arranged across the desktop.
catchall_dish_B[0].position = [1.92, 0.34, 0.775]
catchall_dish_B[0].rotation = [0, 0, radians(90)]

a5_notebook[0].position = [2.20, 0.34, 0.77]
a5_notebook[0].rotation = [0, 0, radians(90)]

paperback_book_A[0].position = [2.48, 0.34, 0.775]
paperback_book_A[0].rotation = [0, 0, radians(90)]

ballpoint_pen[0].position = [2.22, 0.18, 0.765]
ballpoint_pen[0].rotation = [0, 0, radians(90)]

glass_tumbler[0].position = [2.82, 0.43, 0.815]
glass_tumbler[0].rotation = [0, 0, radians(90)]

# The remaining book and coaster fit on the reading side table.
paperback_book_B[0].position = [0.47, 0.28, 0.795]
paperback_book_B[0].rotation = [0, 0, 0]

travertine_stone_coaster[0].position = [0.70, 0.28, 0.785]
travertine_stone_coaster[0].rotation = [0, 0, 0]


# Fixed-point constraints preserve the planned non-overlapping zones while
# allowing the semantic constraints below to retain their intended meaning.
def _pin(instance, weight=10):
    solver.distance_constraint(
        instance,
        AssetInstance(position=list(instance.position)),
        0,
        0,
        weight=weight,
    )


# The bed-to-wall relationship is the highest-priority room-layout constraint.
solver.against_wall(bed[0], walls[2])
_pin(bed[0])
solver.align_with(bed[0], nightstand_A[0])

# The two nightstands flank the bed and share its orientation.
_pin(nightstand_A[0])
solver.distance_constraint(nightstand_A[0], bed[0], 1.10, 1.20, weight=10)
solver.align_with(nightstand_A[0], bed[0])

_pin(nightstand_B[0])
solver.distance_constraint(nightstand_B[0], bed[0], 1.10, 1.20, weight=10)
solver.align_with(nightstand_B[0], bed[0])

# Storage furniture remains against the right wall and faces into the room.
solver.against_wall(wardrobe[0], walls[1])
_pin(wardrobe[0])
solver.align_with(wardrobe[0], bed[0], angle=-90)

solver.against_wall(dresser[0], walls[1])
_pin(dresser[0])
solver.align_with(dresser[0], wardrobe[0])

# The desk stays against the south wall, and the chair points directly toward it.
solver.against_wall(writing_desk[0], walls[0])
_pin(writing_desk[0])
solver.align_with(writing_desk[0], bed[0], angle=180)

_pin(desk_chair[0])
solver.distance_constraint(desk_chair[0], writing_desk[0], 0.65, 0.85, weight=10)
solver.point_towards(desk_chair[0], writing_desk[0])

# The armchair faces the bed and remains beside the reading table.
_pin(armchair[0])
solver.distance_constraint(armchair[0], bed[0], 1.85, 2.20, weight=10)
solver.point_towards(armchair[0], bed[0])

_pin(side_table[0])
solver.distance_constraint(side_table[0], armchair[0], 0.75, 1.05, weight=10)
solver.align_with(side_table[0], writing_desk[0], angle=-90)

_pin(floor_lamp[0])
solver.distance_constraint(floor_lamp[0], writing_desk[0], 1.00, 1.25, weight=10)
solver.align_with(floor_lamp[0], dresser[0])

# Wall decorations are constrained to their corresponding walls and oriented
# to face the room.
solver.against_wall(clock[0], walls[2])
_pin(clock[0])
solver.align_with(clock[0], bed[0])

solver.against_wall(art_print_A[0], walls[2])
_pin(art_print_A[0])
solver.align_with(art_print_A[0], bed[0])

solver.against_wall(art_print_B[0], walls[2])
_pin(art_print_B[0])
solver.align_with(art_print_B[0], bed[0])

solver.against_wall(print[0], walls[3])
_pin(print[0])
solver.align_with(print[0], bed[0], angle=90)

solver.against_wall(art_print_C[0], walls[3])
_pin(art_print_C[0])
solver.align_with(art_print_C[0], bed[0], angle=90)

solver.against_wall(mirror[0], walls[1])
_pin(mirror[0])
solver.align_with(mirror[0], wardrobe[0])

# Every small object receives an on-top constraint, a horizontal placement
# constraint, and an orientation constraint tied to its supporting furniture.
solver.on_top_of(eucalyptus_bunch[0], nightstand_A[0])
_pin(eucalyptus_bunch[0])
solver.align_with(eucalyptus_bunch[0], nightstand_A[0])

solver.on_top_of(jar_candle[0], nightstand_B[0])
_pin(jar_candle[0])
solver.align_with(jar_candle[0], nightstand_B[0])

solver.on_top_of(catchall_dish_A[0], nightstand_B[0])
_pin(catchall_dish_A[0])
solver.align_with(catchall_dish_A[0], nightstand_B[0])

solver.on_top_of(bud_vase[0], dresser[0])
_pin(bud_vase[0])
solver.align_with(bud_vase[0], dresser[0])

solver.on_top_of(hand_lotion_pump_bottle[0], dresser[0])
_pin(hand_lotion_pump_bottle[0])
solver.align_with(hand_lotion_pump_bottle[0], dresser[0])

solver.on_top_of(catchall_dish_C[0], dresser[0])
_pin(catchall_dish_C[0])
solver.align_with(catchall_dish_C[0], dresser[0])

solver.on_top_of(photograph[0], dresser[0])
_pin(photograph[0])
solver.align_with(photograph[0], dresser[0])

solver.on_top_of(catchall_dish_B[0], writing_desk[0])
_pin(catchall_dish_B[0])
solver.align_with(catchall_dish_B[0], writing_desk[0])

solver.on_top_of(a5_notebook[0], writing_desk[0])
_pin(a5_notebook[0])
solver.align_with(a5_notebook[0], writing_desk[0])

solver.on_top_of(paperback_book_A[0], writing_desk[0])
_pin(paperback_book_A[0])
solver.align_with(paperback_book_A[0], writing_desk[0])

solver.on_top_of(ballpoint_pen[0], writing_desk[0])
_pin(ballpoint_pen[0])
solver.align_with(ballpoint_pen[0], writing_desk[0])

solver.on_top_of(glass_tumbler[0], writing_desk[0])
_pin(glass_tumbler[0])
solver.align_with(glass_tumbler[0], writing_desk[0])

solver.on_top_of(paperback_book_B[0], side_table[0])
_pin(paperback_book_B[0])
solver.align_with(paperback_book_B[0], side_table[0])

solver.on_top_of(travertine_stone_coaster[0], side_table[0])
_pin(travertine_stone_coaster[0])
solver.align_with(travertine_stone_coaster[0], side_table[0])

solver.constraints = []
paperback_book_A[0].position = [2.4800000190734863, 0.3400000035762787, 0.7749999761581421]
paperback_book_A[0].rotation = [0, 0, 1.5935875315221244]
paperback_book_A[0].optimize = 2
mirror[0].position = [4.588512420654297, 0.550000011920929, 0.550000011920929]
mirror[0].rotation = [0, 0, -3.1390517375834066]
mirror[0].optimize = 2
ballpoint_pen[0].position = [2.2200000286102295, 0.18000000715255737, 0.7649999856948853]
ballpoint_pen[0].rotation = [0, 0, 1.5935875315221244]
ballpoint_pen[0].optimize = 2
desk_chair[0].position = [2.3499999046325684, 1.0499999523162842, 0.44999998807907104]
desk_chair[0].rotation = [0, 0, -1.5582299555380688]
desk_chair[0].optimize = 2
paperback_book_B[0].position = [0.4699999988079071, 0.2800000011920929, 0.5349999666213989]
paperback_book_B[0].rotation = [0, 0, 0.02278960013808119]
paperback_book_B[0].optimize = 2
bed[0].position = [1.649999976158142, 2.9174575805664062, 0.550000011920929]
bed[0].rotation = [0, 0, -1.5278099057481966]
bed[0].optimize = 2
wardrobe[0].position = [4.283091068267822, 2.950000047683716, 1.100000023841858]
wardrobe[0].rotation = [0, 0, -3.1328304469153387]
wardrobe[0].optimize = 2
clock[0].position = [3.299999952316284, 3.9839563369750977, 0.1599999964237213]
clock[0].rotation = [0, 0, -1.568255406200039]
clock[0].optimize = 2
dresser[0].position = [4.331627368927002, 0.75, 0.4099999964237213]
dresser[0].rotation = [0, 0, -3.1110527827274685]
dresser[0].optimize = 2
armchair[0].position = [0.699999988079071, 1.149999976158142, 0.4350000023841858]
armchair[0].rotation = [0, 0, 1.0978121025634728]
armchair[0].optimize = 2
catchall_dish_C[0].position = [4.349999904632568, 0.7200000286102295, 0.8349999785423279]
catchall_dish_C[0].rotation = [0, 0, -3.1188018072008132]
catchall_dish_C[0].optimize = 2
nightstand_B[0].position = [2.7799999713897705, 3.75, 0.28999999165534973]
nightstand_B[0].rotation = [0, 0, -1.5353158185380773]
nightstand_B[0].optimize = 2
print[0].position = [0.0067442841827869415, 2.700000047683716, 0.4000000059604645]
print[0].rotation = [0, 0, 0.0025409193727581954]
print[0].optimize = 2
travertine_stone_coaster[0].position = [0.699999988079071, 0.2800000011920929, 0.5249999761581421]
travertine_stone_coaster[0].rotation = [0, 0, 0.02278960013808119]
travertine_stone_coaster[0].optimize = 2
jar_candle[0].position = [2.880000114440918, 3.75, 0.6299999952316284]
jar_candle[0].rotation = [0, 0, -1.5480067266568154]
jar_candle[0].optimize = 2
bud_vase[0].position = [4.349999904632568, 0.20000000298023224, 0.9300000071525574]
bud_vase[0].rotation = [0, 0, -3.1188018072008132]
bud_vase[0].optimize = 2
catchall_dish_B[0].position = [1.9199999570846558, 0.3400000035762787, 0.7799999713897705]
catchall_dish_B[0].rotation = [0, 0, 1.5935875315221244]
catchall_dish_B[0].optimize = 2
eucalyptus_bunch[0].position = [0.5199999809265137, 3.75, 0.9049999713897705]
eucalyptus_bunch[0].rotation = [0, 0, -1.5480074742547933]
eucalyptus_bunch[0].optimize = 2
catchall_dish_A[0].position = [2.6600000858306885, 3.75, 0.5949999690055847]
catchall_dish_A[0].rotation = [0, 0, -1.5480067266568154]
catchall_dish_A[0].optimize = 2
art_print_A[0].position = [1.2999999523162842, 3.9932661056518555, 0.3499999940395355]
art_print_A[0].rotation = [0, 0, -1.5682554064999652]
art_print_A[0].optimize = 2
art_print_C[0].position = [0.006743067875504494, 1.649999976158142, 0.25]
art_print_C[0].rotation = [0, 0, 0.002540920594857827]
art_print_C[0].optimize = 2
nightstand_A[0].position = [0.5199999809265137, 3.75, 0.28999999165534973]
nightstand_A[0].rotation = [0, 0, -1.5384879714316304]
nightstand_A[0].optimize = 2
hand_lotion_pump_bottle[0].position = [4.349999904632568, 0.44999998807907104, 0.9200000166893005]
hand_lotion_pump_bottle[0].rotation = [0, 0, -3.1188018072008132]
hand_lotion_pump_bottle[0].optimize = 2
floor_lamp[0].position = [3.450000047683716, 0.30000001192092896, 0.824999988079071]
floor_lamp[0].rotation = [0, 0, -3.1188018072008132]
floor_lamp[0].optimize = 2
art_print_B[0].position = [2.1500000953674316, 3.9932661056518555, 0.3499999940395355]
art_print_B[0].rotation = [0, 0, -1.5682554064999652]
art_print_B[0].optimize = 2
writing_desk[0].position = [2.3499999046325684, 0.334828644990921, 0.3799999952316284]
writing_desk[0].rotation = [0, 0, 1.616894635418373]
writing_desk[0].optimize = 2
a5_notebook[0].position = [2.200000047683716, 0.3400000035762787, 0.7699999809265137]
a5_notebook[0].rotation = [0, 0, 1.5935875315221244]
a5_notebook[0].optimize = 2
glass_tumbler[0].position = [2.819999933242798, 0.4300000071525574, 0.8149999976158142]
glass_tumbler[0].rotation = [0, 0, 1.5935875315221244]
glass_tumbler[0].optimize = 2
side_table[0].position = [0.550000011920929, 0.2800000011920929, 0.25999999046325684]
side_table[0].rotation = [0, 0, 0.03548059709080301]
side_table[0].optimize = 2
photograph[0].position = [4.335000038146973, 1.2000000476837158, 0.9700000286102295]
photograph[0].rotation = [0, 0, -3.1188018072008132]
photograph[0].optimize = 2

