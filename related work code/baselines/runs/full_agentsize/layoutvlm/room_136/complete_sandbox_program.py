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
    Wall(corner1=[10.00, 0.00, 0.00], corner2=[10.00, 1.00, 0.00]),
    Wall(corner1=[10.00, 1.00, 0.00], corner2=[9.00, 1.00, 0.00]),
    Wall(corner1=[9.00, 1.00, 0.00], corner2=[9.00, 4.00, 0.00]),
    Wall(corner1=[9.00, 4.00, 0.00], corner2=[8.00, 4.00, 0.00]),
    Wall(corner1=[8.00, 4.00, 0.00], corner2=[8.00, 5.00, 0.00]),
    Wall(corner1=[8.00, 5.00, 0.00], corner2=[0.00, 5.00, 0.00]),
    Wall(corner1=[0.00, 5.00, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[10.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
wardrobe = Assets(description="A wood closet with jackets inside.", size=[0.65, 2.40, 2.30], placements=[AssetInstance() for _ in range(1)])
platform_bed = Assets(description="A bed with a beige comforter and pillows and orange wooden frame.", size=[2.10, 1.80, 0.65], placements=[AssetInstance() for _ in range(1)])
side_table_A = Assets(description="A stool with a round seat and four legs.", size=[0.42, 0.42, 0.48], placements=[AssetInstance() for _ in range(1)])
desk_chair = Assets(description="desk chair", size=[0.65, 0.65, 1.05], placements=[AssetInstance() for _ in range(1)])
wall_sconce_A = Assets(description="A lamp that is hanging on a wall mount.", size=[0.18, 0.28, 0.42], placements=[AssetInstance() for _ in range(1)])
wall_mirror_A = Assets(description="A rectangular mirror in a brown wooden frame.", size=[0.06, 0.80, 1.20], placements=[AssetInstance() for _ in range(1)])
armchair = Assets(description="A chair with grey fabric and a black frame.", size=[0.85, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
floor_shelf_unit_A = Assets(description="A set of wooden shelves.", size=[0.35, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
wall_shelf_A = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.25, 1.00, 0.25], placements=[AssetInstance() for _ in range(1)])
wall_shelf_B = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.25, 1.00, 0.25], placements=[AssetInstance() for _ in range(1)])
wall_sconce_B = Assets(description="A lamp that is hanging on a wall mount.", size=[0.18, 0.28, 0.42], placements=[AssetInstance() for _ in range(1)])
side_table_B = Assets(description="A stool with a round seat and four legs.", size=[0.42, 0.42, 0.48], placements=[AssetInstance() for _ in range(1)])
plant_stand_A = Assets(description="A brown flower pot with long leafed plant protruding on a concrete pedestal.", size=[0.55, 0.55, 1.40], placements=[AssetInstance() for _ in range(1)])
bedside_table_A = Assets(description="Side table with square wood top and silver legs.", size=[0.45, 0.50, 0.58], placements=[AssetInstance() for _ in range(1)])
floor_shelf_unit_B = Assets(description="A set of wooden shelves.", size=[0.35, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
laundry_basket_A = Assets(description="A wicker basket full of laundry.", size=[0.45, 0.55, 0.65], placements=[AssetInstance() for _ in range(1)])
full_length_mirror_stand = Assets(description="White round mirror on a stand.", size=[0.45, 0.75, 1.75], placements=[AssetInstance() for _ in range(1)])
laundry_basket_B = Assets(description="A wicker basket full of laundry.", size=[0.45, 0.55, 0.65], placements=[AssetInstance() for _ in range(1)])
bedside_table_B = Assets(description="Side table with square wood top and silver legs.", size=[0.45, 0.50, 0.58], placements=[AssetInstance() for _ in range(1)])
wall_art_A = Assets(description="A black framed painting of a city scene in teal.", size=[0.05, 0.90, 0.65], placements=[AssetInstance() for _ in range(1)])
wall_shelf_C = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.25, 1.00, 0.25], placements=[AssetInstance() for _ in range(1)])
wall_art_B = Assets(description="A black framed painting of a city scene in teal.", size=[0.05, 0.90, 0.65], placements=[AssetInstance() for _ in range(1)])
coat_stand = Assets(description="A very tall candle holder.", size=[0.50, 0.50, 1.85], placements=[AssetInstance() for _ in range(1)])
dresser = Assets(description="A black and brown wooden dresser with four vertical rows of drawers.", size=[0.50, 1.80, 0.90], placements=[AssetInstance() for _ in range(1)])
plant_stand_B = Assets(description="A brown flower pot with long leafed plant protruding on a concrete pedestal.", size=[0.55, 0.55, 1.40], placements=[AssetInstance() for _ in range(1)])
writing_desk = Assets(description="A brown desk with black metal pieces.", size=[0.70, 1.40, 0.76], placements=[AssetInstance() for _ in range(1)])
wall_art_C = Assets(description="A black framed painting of a city scene in teal.", size=[0.05, 0.90, 0.65], placements=[AssetInstance() for _ in range(1)])
freestanding_shelf_divider = Assets(description="A set of wooden shelves.", size=[0.40, 1.60, 1.80], placements=[AssetInstance() for _ in range(1)])
wall_sconce_C = Assets(description="A lamp that is hanging on a wall mount.", size=[0.18, 0.28, 0.42], placements=[AssetInstance() for _ in range(1)])
wall_sconce_D = Assets(description="A lamp that is hanging on a wall mount.", size=[0.18, 0.28, 0.42], placements=[AssetInstance() for _ in range(1)])
plant_stand_C = Assets(description="A brown flower pot with long leafed plant protruding on a concrete pedestal.", size=[0.55, 0.55, 1.40], placements=[AssetInstance() for _ in range(1)])
wall_mirror_B = Assets(description="A rectangular mirror in a brown wooden frame.", size=[0.06, 0.80, 1.20], placements=[AssetInstance() for _ in range(1)])

wardrobe[0].instance_id = 'wardrobe_0'
platform_bed[0].instance_id = 'platform_bed_0'
side_table_A[0].instance_id = 'side_table_A_0'
desk_chair[0].instance_id = 'desk_chair_0'
wall_sconce_A[0].instance_id = 'wall_sconce_A_0'
wall_mirror_A[0].instance_id = 'wall_mirror_A_0'
armchair[0].instance_id = 'armchair_0'
floor_shelf_unit_A[0].instance_id = 'floor_shelf_unit_A_0'
wall_shelf_A[0].instance_id = 'wall_shelf_A_0'
wall_shelf_B[0].instance_id = 'wall_shelf_B_0'
wall_sconce_B[0].instance_id = 'wall_sconce_B_0'
side_table_B[0].instance_id = 'side_table_B_0'
plant_stand_A[0].instance_id = 'plant_stand_A_0'
bedside_table_A[0].instance_id = 'bedside_table_A_0'
floor_shelf_unit_B[0].instance_id = 'floor_shelf_unit_B_0'
laundry_basket_A[0].instance_id = 'laundry_basket_A_0'
full_length_mirror_stand[0].instance_id = 'full_length_mirror_stand_0'
laundry_basket_B[0].instance_id = 'laundry_basket_B_0'
bedside_table_B[0].instance_id = 'bedside_table_B_0'
wall_art_A[0].instance_id = 'wall_art_A_0'
wall_shelf_C[0].instance_id = 'wall_shelf_C_0'
wall_art_B[0].instance_id = 'wall_art_B_0'
coat_stand[0].instance_id = 'coat_stand_0'
dresser[0].instance_id = 'dresser_0'
plant_stand_B[0].instance_id = 'plant_stand_B_0'
writing_desk[0].instance_id = 'writing_desk_0'
wall_art_C[0].instance_id = 'wall_art_C_0'
freestanding_shelf_divider[0].instance_id = 'freestanding_shelf_divider_0'
wall_sconce_C[0].instance_id = 'wall_sconce_C_0'
wall_sconce_D[0].instance_id = 'wall_sconce_D_0'
plant_stand_C[0].instance_id = 'plant_stand_C_0'
wall_mirror_B[0].instance_id = 'wall_mirror_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

wardrobe[0].position = [3.7800959128940823, 2.7468264609772475, 1.15]
wardrobe[0].rotation = [0, 0, 0]
platform_bed[0].position = [7.1651638350755595, 3.4796516659190004, 0.325]
platform_bed[0].rotation = [0, 0, 0]
side_table_A[0].position = [1.6140786698113718, 0.5534464148515567, 0.24]
side_table_A[0].rotation = [0, 0, 0]
desk_chair[0].position = [0.3104724249374635, 1.8328470596926598, 0.525]
desk_chair[0].rotation = [0, 0, 0]
wall_sconce_A[0].position = [5.8580493653091, 1.9570584101928628, 0.21]
wall_sconce_A[0].rotation = [0, 0, 0]
wall_mirror_A[0].position = [1.7648145991023512, 1.2486487934185182, 0.6]
wall_mirror_A[0].rotation = [0, 0, 0]
armchair[0].position = [1.8395009124932238, 4.902440242725322, 0.45]
armchair[0].rotation = [0, 0, 0]
floor_shelf_unit_A[0].position = [6.834404314045837, 0.2718553439515148, 0.9]
floor_shelf_unit_A[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [6.863913334723179, 3.347656976690647, 0.125]
wall_shelf_A[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [7.027446746972594, 2.3161856927066227, 0.125]
wall_shelf_B[0].rotation = [0, 0, 0]
wall_sconce_B[0].position = [9.67142692422756, 0.914564556066006, 0.21]
wall_sconce_B[0].rotation = [0, 0, 0]
side_table_B[0].position = [5.3370401569433445, 4.249092863505156, 0.24]
side_table_B[0].rotation = [0, 0, 0]
plant_stand_A[0].position = [4.341676411489448, 3.5881573017286845, 0.7]
plant_stand_A[0].rotation = [0, 0, 0]
bedside_table_A[0].position = [3.313979113092491, 0.15679998971407927, 0.29]
bedside_table_A[0].rotation = [0, 0, 0]
floor_shelf_unit_B[0].position = [7.823836497021761, 1.3857949682913995, 0.9]
floor_shelf_unit_B[0].rotation = [0, 0, 0]
laundry_basket_A[0].position = [2.6892270099155855, 4.2155750453642575, 0.325]
laundry_basket_A[0].rotation = [0, 0, 0]
full_length_mirror_stand[0].position = [4.708360496820713, 3.7919287806212987, 0.875]
full_length_mirror_stand[0].rotation = [0, 0, 0]
laundry_basket_B[0].position = [3.546143640826399, 2.91602560776906, 0.325]
laundry_basket_B[0].rotation = [0, 0, 0]
bedside_table_B[0].position = [4.681494661533414, 2.22931059372748, 0.29]
bedside_table_B[0].rotation = [0, 0, 0]
wall_art_A[0].position = [5.918875876975669, 1.2766317307001573, 0.325]
wall_art_A[0].rotation = [0, 0, 0]
wall_shelf_C[0].position = [4.367267672471628, 1.1478015632821221, 0.125]
wall_shelf_C[0].rotation = [0, 0, 0]
wall_art_B[0].position = [0.8571860735365455, 1.5094439757608336, 0.325]
wall_art_B[0].rotation = [0, 0, 0]
coat_stand[0].position = [1.7327118910962303, 1.308927698423783, 0.925]
coat_stand[0].rotation = [0, 0, 0]
dresser[0].position = [8.974370363539313, 3.9283841620125832, 0.45]
dresser[0].rotation = [0, 0, 0]
plant_stand_B[0].position = [2.9115724469833815, 1.2961917871904123, 0.7]
plant_stand_B[0].rotation = [0, 0, 0]
writing_desk[0].position = [7.195156300913017, 2.3780588784409744, 0.38]
writing_desk[0].rotation = [0, 0, 0]
wall_art_C[0].position = [3.8267803688489943, 0.8757799331308569, 0.325]
wall_art_C[0].rotation = [0, 0, 0]
freestanding_shelf_divider[0].position = [7.6943029641292195, 2.193726685959625, 0.9]
freestanding_shelf_divider[0].rotation = [0, 0, 0]
wall_sconce_C[0].position = [0.7952264886371829, 1.4584306141593784, 0.21]
wall_sconce_C[0].rotation = [0, 0, 0]
wall_sconce_D[0].position = [3.741643386996547, 0.9070093988743594, 0.21]
wall_sconce_D[0].rotation = [0, 0, 0]
plant_stand_C[0].position = [2.4883406971906608, 1.6678639037625598, 0.7]
plant_stand_C[0].rotation = [0, 0, 0]
wall_mirror_B[0].position = [7.19835302580909, 2.908711470495699, 0.6]
wall_mirror_B[0].rotation = [0, 0, 0]
wardrobe[0].position = [3.7800959128940823, 2.7468264609772475, 1.15]
wardrobe[0].rotation = [0, 0, 0]
platform_bed[0].position = [7.1651638350755595, 3.4796516659190004, 0.325]
platform_bed[0].rotation = [0, 0, 0]
side_table_A[0].position = [1.6140786698113718, 0.5534464148515567, 0.24]
side_table_A[0].rotation = [0, 0, 0]
desk_chair[0].position = [0.3104724249374635, 1.8328470596926598, 0.525]
desk_chair[0].rotation = [0, 0, 0]
wall_sconce_A[0].position = [5.8580493653091, 1.9570584101928628, 0.21]
wall_sconce_A[0].rotation = [0, 0, 0]
wall_mirror_A[0].position = [1.7648145991023512, 1.2486487934185182, 0.6]
wall_mirror_A[0].rotation = [0, 0, 0]
armchair[0].position = [1.8395009124932238, 4.902440242725322, 0.45]
armchair[0].rotation = [0, 0, 0]
floor_shelf_unit_A[0].position = [6.834404314045837, 0.2718553439515148, 0.9]
floor_shelf_unit_A[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [6.863913334723179, 3.347656976690647, 0.125]
wall_shelf_A[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [7.027446746972594, 2.3161856927066227, 0.125]
wall_shelf_B[0].rotation = [0, 0, 0]
wall_sconce_B[0].position = [9.67142692422756, 0.914564556066006, 0.21]
wall_sconce_B[0].rotation = [0, 0, 0]
side_table_B[0].position = [5.3370401569433445, 4.249092863505156, 0.24]
side_table_B[0].rotation = [0, 0, 0]
plant_stand_A[0].position = [4.341676411489448, 3.5881573017286845, 0.7]
plant_stand_A[0].rotation = [0, 0, 0]
bedside_table_A[0].position = [3.313979113092491, 0.15679998971407927, 0.29]
bedside_table_A[0].rotation = [0, 0, 0]
floor_shelf_unit_B[0].position = [7.823836497021761, 1.3857949682913995, 0.9]
floor_shelf_unit_B[0].rotation = [0, 0, 0]
laundry_basket_A[0].position = [2.6892270099155855, 4.2155750453642575, 0.325]
laundry_basket_A[0].rotation = [0, 0, 0]
full_length_mirror_stand[0].position = [4.708360496820713, 3.7919287806212987, 0.875]
full_length_mirror_stand[0].rotation = [0, 0, 0]
laundry_basket_B[0].position = [3.546143640826399, 2.91602560776906, 0.325]
laundry_basket_B[0].rotation = [0, 0, 0]
bedside_table_B[0].position = [4.681494661533414, 2.22931059372748, 0.29]
bedside_table_B[0].rotation = [0, 0, 0]
wall_art_A[0].position = [5.918875876975669, 1.2766317307001573, 0.325]
wall_art_A[0].rotation = [0, 0, 0]
wall_shelf_C[0].position = [4.367267672471628, 1.1478015632821221, 0.125]
wall_shelf_C[0].rotation = [0, 0, 0]
wall_art_B[0].position = [0.8571860735365455, 1.5094439757608336, 0.325]
wall_art_B[0].rotation = [0, 0, 0]
coat_stand[0].position = [1.7327118910962303, 1.308927698423783, 0.925]
coat_stand[0].rotation = [0, 0, 0]
dresser[0].position = [8.974370363539313, 3.9283841620125832, 0.45]
dresser[0].rotation = [0, 0, 0]
plant_stand_B[0].position = [2.9115724469833815, 1.2961917871904123, 0.7]
plant_stand_B[0].rotation = [0, 0, 0]
writing_desk[0].position = [7.195156300913017, 2.3780588784409744, 0.38]
writing_desk[0].rotation = [0, 0, 0]
wall_art_C[0].position = [3.8267803688489943, 0.8757799331308569, 0.325]
wall_art_C[0].rotation = [0, 0, 0]
freestanding_shelf_divider[0].position = [7.6943029641292195, 2.193726685959625, 0.9]
freestanding_shelf_divider[0].rotation = [0, 0, 0]
wall_sconce_C[0].position = [0.7952264886371829, 1.4584306141593784, 0.21]
wall_sconce_C[0].rotation = [0, 0, 0]
wall_sconce_D[0].position = [3.741643386996547, 0.9070093988743594, 0.21]
wall_sconce_D[0].rotation = [0, 0, 0]
plant_stand_C[0].position = [2.4883406971906608, 1.6678639037625598, 0.7]
plant_stand_C[0].rotation = [0, 0, 0]
wall_mirror_B[0].position = [7.19835302580909, 2.908711470495699, 0.6]
wall_mirror_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed orientation references let the solver preserve the intended facing
# directions independently of the assets' exact coordinates.
face_pos_x = AssetInstance(rotation=[0, 0, radians(0)])
face_pos_y = AssetInstance(rotation=[0, 0, radians(90)])
face_neg_x = AssetInstance(rotation=[0, 0, radians(180)])
face_neg_y = AssetInstance(rotation=[0, 0, radians(-90)])


def place_asset(asset, position, yaw, wall=None, face_target=None):
    """Initialize one asset and add both position and orientation constraints."""
    asset[0].position = position
    asset[0].rotation = [0, 0, radians(yaw)]

    # Wall association is the primary position constraint for wall-adjacent
    # furniture and mounted objects. The fixed point preserves its wall location.
    if wall is not None:
        solver.against_wall(asset[0], wall)

    target_position = AssetInstance(position=position)
    solver.distance_constraint(
        asset[0], target_position, 0, 0, weight=10
    )

    # Chairs use a semantic facing constraint; other objects preserve their
    # chosen orientation with an orientation reference.
    if face_target is not None:
        solver.point_towards(asset[0], face_target)
    elif yaw == 0:
        solver.align_with(asset[0], face_pos_x)
    elif yaw == 90:
        solver.align_with(asset[0], face_pos_y)
    elif yaw == 180:
        solver.align_with(asset[0], face_neg_x)
    elif yaw == -90:
        solver.align_with(asset[0], face_neg_y)


# Sleeping zone along the left wall. The bed faces into the room, while the
# bedside tables remain just beyond the two long sides of the mattress.
place_asset(platform_bed, [1.05, 3.60, 0.325], 0, wall=walls[6])
place_asset(bedside_table_A, [1.20, 2.42, 0.29], 0)
place_asset(bedside_table_B, [1.20, 4.77, 0.29], 0)

solver.distance_constraint(
    bedside_table_A[0], platform_bed[0], 1.10, 1.30, weight=10
)
solver.distance_constraint(
    bedside_table_B[0], platform_bed[0], 1.10, 1.30, weight=10
)
solver.align_with(bedside_table_A[0], platform_bed[0])
solver.align_with(bedside_table_B[0], platform_bed[0])

# Low storage occupies the lower portion of the left wall without blocking the
# bed. The wardrobe uses the long uninterrupted right wall and faces inward.
place_asset(dresser, [0.25, 1.25, 0.45], 0, wall=walls[6])
place_asset(wardrobe, [8.675, 2.80, 1.15], 180, wall=walls[2])

# Workspace on the upper wall, left of the doorway. The chair faces the desk,
# and the door-clear zone from approximately x=6.0 to x=7.95 remains open.
place_asset(writing_desk, [3.80, 4.65, 0.38], -90, wall=walls[5])
place_asset(
    desk_chair,
    [3.80, 3.65, 0.525],
    90,
    face_target=writing_desk[0],
)
solver.distance_constraint(
    desk_chair[0], writing_desk[0], 0.85, 1.15, weight=10
)

# Tall floor shelves use remaining wall segments. Shelf A stops before the
# doorway, and shelf B fits in the lower-right portion of the stepped room.
place_asset(floor_shelf_unit_A, [5.30, 4.825, 0.90], -90, wall=walls[5])
place_asset(floor_shelf_unit_B, [8.825, 0.75, 0.90], 180, wall=walls[2])

# Reading/seating group in the open left-center area.
place_asset(
    armchair,
    [2.85, 2.00, 0.45],
    0,
    face_target=side_table_A[0],
)
place_asset(side_table_A, [3.65, 2.00, 0.24], 0)
place_asset(side_table_B, [2.85, 1.15, 0.24], 90)

solver.distance_constraint(
    armchair[0], side_table_A[0], 0.70, 0.95, weight=10
)
solver.distance_constraint(
    armchair[0], side_table_B[0], 0.70, 0.95, weight=10
)

# The required plant-divider-plant composition crosses the lower-middle area.
# Their collinear x coordinates make the freestanding shelf unambiguously
# between plant stands A and B, with clearance on both sides.
place_asset(plant_stand_A, [4.95, 1.75, 0.70], 0)
place_asset(freestanding_shelf_divider, [6.45, 1.75, 0.90], 90)
place_asset(plant_stand_B, [7.95, 1.75, 0.70], 180)

solver.distance_constraint(
    freestanding_shelf_divider[0], plant_stand_A[0], 1.50, 1.50, weight=10
)
solver.distance_constraint(
    freestanding_shelf_divider[0], plant_stand_B[0], 1.50, 1.50, weight=10
)
solver.distance_constraint(
    plant_stand_A[0], plant_stand_B[0], 3.00, 3.00, weight=10
)
solver.align_with(plant_stand_A[0], freestanding_shelf_divider[0], angle=-90)
solver.align_with(plant_stand_B[0], freestanding_shelf_divider[0], angle=90)

# A third plant and the laundry baskets fill the center-right area while
# stopping short of the approach to the door.
place_asset(plant_stand_C, [7.50, 3.65, 0.70], 180)
place_asset(laundry_basket_A, [6.00, 3.00, 0.325], 0)
place_asset(laundry_basket_B, [6.70, 3.00, 0.325], 0)

solver.distance_constraint(
    laundry_basket_A[0], laundry_basket_B[0], 0.65, 0.80, weight=10
)
solver.align_with(laundry_basket_B[0], laundry_basket_A[0])

# The standing mirror is accessible beside the bed. The coat stand occupies the
# small lower-right extension, away from the main circulation route.
place_asset(full_length_mirror_stand, [2.70, 4.58, 0.875], -90)
place_asset(coat_stand, [9.55, 0.45, 0.925], 180)

# Wall-mounted shelves are elevated above low furniture. Their z coordinates
# place them on the walls rather than on the floor.
place_asset(wall_shelf_A, [0.125, 0.80, 1.20], 0, wall=walls[6])
place_asset(wall_shelf_B, [3.80, 4.875, 1.25], -90, wall=walls[5])
place_asset(wall_shelf_C, [0.125, 2.00, 1.20], 0, wall=walls[6])

# Mirrors and artwork are distributed across available wall sections. The
# bottom-wall artwork lies in the gap between the first two windows.
place_asset(wall_mirror_A, [2.60, 4.97, 1.55], -90, wall=walls[5])
place_asset(wall_mirror_B, [7.97, 4.45, 1.55], 180, wall=walls[3])

place_asset(wall_art_A, [0.025, 3.20, 1.40], 0, wall=walls[6])
place_asset(wall_art_B, [0.025, 4.18, 1.40], 0, wall=walls[6])
place_asset(wall_art_C, [2.245, 0.025, 1.40], 90, wall=walls[7])

# Sconces sit high enough to clear the bed and other floor furniture. The first
# three use free portions of the upper wall; the fourth uses the right wall.
place_asset(wall_sconce_A, [0.55, 4.91, 1.65], -90, wall=walls[5])
place_asset(wall_sconce_B, [1.25, 4.91, 1.65], -90, wall=walls[5])
place_asset(wall_sconce_C, [1.95, 4.91, 1.65], -90, wall=walls[5])
place_asset(wall_sconce_D, [8.91, 1.50, 2.05], 180, wall=walls[2])

solver.constraints = []
writing_desk[0].position = [3.799999952316284, 4.6468682289123535, 0.3799999952316284]
writing_desk[0].rotation = [0, 0, -1.5620341134408144]
writing_desk[0].optimize = 2
bedside_table_A[0].position = [1.2000000476837158, 2.4200000762939453, 0.28999999165534973]
bedside_table_A[0].rotation = [0, 0, 0.025961558158328533]
bedside_table_A[0].optimize = 2
laundry_basket_B[0].position = [6.699999809265137, 3.0, 0.32499998807907104]
laundry_basket_B[0].rotation = [0, 0, 0.015708042138662493]
laundry_basket_B[0].optimize = 2
wall_sconce_B[0].position = [1.25, 4.909644603729248, 0.20999999344348907]
wall_sconce_B[0].rotation = [0, 0, -1.568255404355692]
wall_sconce_B[0].optimize = 2
wall_art_A[0].position = [0.026143332943320274, 3.200000047683716, 0.32499998807907104]
wall_art_A[0].rotation = [0, 0, 0.0025409150842135757]
wall_art_A[0].optimize = 2
wall_shelf_B[0].position = [3.799999952316284, 4.873730182647705, 0.125]
wall_shelf_B[0].rotation = [0, 0, -1.5682554129327817]
wall_shelf_B[0].optimize = 2
bedside_table_B[0].position = [1.2000000476837158, 4.753564834594727, 0.28999999165534973]
bedside_table_B[0].rotation = [0, 0, 0.025961558158328533]
bedside_table_B[0].optimize = 2
plant_stand_C[0].position = [7.5, 3.6500000953674316, 0.699999988079071]
plant_stand_C[0].rotation = [0, 0, -3.1321678761290697]
plant_stand_C[0].optimize = 2
side_table_B[0].position = [2.8499999046325684, 1.149999976158142, 0.23999999463558197]
side_table_B[0].rotation = [0, 0, 1.5833626980517244]
side_table_B[0].optimize = 2
plant_stand_B[0].position = [7.949999809265137, 1.75, 0.699999988079071]
plant_stand_B[0].rotation = [0, 0, -3.112463930448711]
plant_stand_B[0].optimize = 2
laundry_basket_A[0].position = [6.0, 3.0, 0.32499998807907104]
laundry_basket_A[0].rotation = [0, 0, 0.0157079639172164]
laundry_basket_A[0].optimize = 2
wall_art_C[0].position = [2.244999885559082, 0.026143332943320274, 0.32499998807907104]
wall_art_C[0].rotation = [0, 0, 1.5733372418791103]
wall_art_C[0].optimize = 2
desk_chair[0].position = [3.799999952316284, 3.6500000953674316, 0.5249999761581421]
desk_chair[0].rotation = [0, 0, 1.5833626980517244]
desk_chair[0].optimize = 2
wall_mirror_A[0].position = [2.5999999046325684, 4.9689836502075195, 0.6000000238418579]
wall_mirror_A[0].rotation = [0, 0, -1.5682554098663368]
wall_mirror_A[0].optimize = 2
coat_stand[0].position = [9.550000190734863, 0.44999998807907104, 0.925000011920929]
coat_stand[0].rotation = [0, 0, -3.1321678761290697]
coat_stand[0].optimize = 2
wall_shelf_A[0].position = [0.12627005577087402, 0.800000011920929, 0.125]
wall_shelf_A[0].rotation = [0, 0, 0.002540912939942025]
wall_shelf_A[0].optimize = 2
freestanding_shelf_divider[0].position = [6.449999809265137, 1.75, 0.8999999761581421]
freestanding_shelf_divider[0].rotation = [0, 0, 1.5927874750809192]
freestanding_shelf_divider[0].optimize = 2
platform_bed[0].position = [1.072285532951355, 3.5999999046325684, 0.32499998807907104]
platform_bed[0].rotation = [0, 0, 0.014983857038071051]
platform_bed[0].optimize = 2
wall_sconce_A[0].position = [0.550000011920929, 4.909644603729248, 0.20999999344348907]
wall_sconce_A[0].rotation = [0, 0, -1.568255404355692]
wall_sconce_A[0].optimize = 2
floor_shelf_unit_B[0].position = [8.83482837677002, 0.7599999904632568, 0.8999999761581421]
floor_shelf_unit_B[0].rotation = [0, 0, -3.118800973692556]
floor_shelf_unit_B[0].optimize = 2
wall_shelf_C[0].position = [0.12627005577087402, 2.0, 0.125]
wall_shelf_C[0].rotation = [0, 0, 0.002540912939942025]
wall_shelf_C[0].optimize = 2
armchair[0].position = [2.8499999046325684, 2.0, 0.44999998807907104]
armchair[0].rotation = [0, 0, 0.0157079639172164]
armchair[0].optimize = 2
wardrobe[0].position = [8.669946670532227, 2.790001153945923, 1.149999976158142]
wardrobe[0].rotation = [0, 0, -3.1390517663586643]
wardrobe[0].optimize = 2
wall_mirror_B[0].position = [7.968984127044678, 4.449999809265137, 0.6000000238418579]
wall_mirror_B[0].rotation = [0, 0, -3.1390517366612336]
wall_mirror_B[0].optimize = 2
wall_sconce_C[0].position = [1.9500000476837158, 4.909644603729248, 0.20999999344348907]
wall_sconce_C[0].rotation = [0, 0, -1.568255404355692]
wall_sconce_C[0].optimize = 2
full_length_mirror_stand[0].position = [2.700000047683716, 4.579999923706055, 0.875]
full_length_mirror_stand[0].rotation = [0, 0, -1.5613715493341729]
full_length_mirror_stand[0].optimize = 2
wall_art_B[0].position = [0.026143332943320274, 4.179999828338623, 0.32499998807907104]
wall_art_B[0].rotation = [0, 0, 0.0025409150842135757]
wall_art_B[0].optimize = 2
dresser[0].position = [0.26128971576690674, 1.25, 0.44999998807907104]
dresser[0].rotation = [0, 0, 0.0025408284588584276]
dresser[0].optimize = 2
side_table_A[0].position = [3.6500000953674316, 2.0, 0.23999999463558197]
side_table_A[0].rotation = [0, 0, 0.0157079639172164]
side_table_A[0].optimize = 2
wall_sconce_D[0].position = [8.90964412689209, 1.5, 0.20999999344348907]
wall_sconce_D[0].rotation = [0, 0, -3.139051732072762]
wall_sconce_D[0].optimize = 2
plant_stand_A[0].position = [4.949999809265137, 1.75, 0.699999988079071]
plant_stand_A[0].rotation = [0, 0, 0.02912872126119664]
plant_stand_A[0].optimize = 2
floor_shelf_unit_A[0].position = [5.300000190734863, 4.8234758377075195, 0.8999999761581421]
floor_shelf_unit_A[0].rotation = [0, 0, -1.5682554162991507]
floor_shelf_unit_A[0].optimize = 2

