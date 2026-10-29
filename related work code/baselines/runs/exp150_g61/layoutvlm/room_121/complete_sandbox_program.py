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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[8.00, 0.00, 0.00]),
    Wall(corner1=[8.00, 0.00, 0.00], corner2=[8.00, 2.00, 0.00]),
    Wall(corner1=[8.00, 2.00, 0.00], corner2=[4.00, 2.00, 0.00]),
    Wall(corner1=[4.00, 2.00, 0.00], corner2=[4.00, 4.00, 0.00]),
    Wall(corner1=[4.00, 4.00, 0.00], corner2=[8.00, 4.00, 0.00]),
    Wall(corner1=[8.00, 4.00, 0.00], corner2=[8.00, 6.00, 0.00]),
    Wall(corner1=[8.00, 6.00, 0.00], corner2=[0.00, 6.00, 0.00]),
    Wall(corner1=[0.00, 6.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
wall_whiteboard = Assets(description="A white rectangular poster with black blue and orange marks and irregular writing.", size=[0.05, 1.80, 1.00], placements=[AssetInstance() for _ in range(1)])
coat_stand = Assets(description="The coatrack is wooden with a round bottom.", size=[0.55, 0.55, 1.80], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_A = Assets(description="A painting of a woman covered with white clouds in a gold frame.", size=[0.06, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
breakout_round_table = Assets(description="Round table with wood top and four tapered legs.", size=[1.10, 1.10, 0.75], placements=[AssetInstance() for _ in range(1)])
paper_stack = Assets(description="A stack of colorful, pixelated-style books in different colors.", size=[0.22, 0.30, 0.12], placements=[AssetInstance() for _ in range(1)])
picture_frame = Assets(description="Picture of trees by a lake in black picture frame.", size=[0.10, 0.32, 0.25], placements=[AssetInstance() for _ in range(1)])
breakout_chair_A = Assets(description="Gray plastic chair with no arms and thin wood legs.", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
storage_box_small_A = Assets(description="A wooden box with the lid off and the word fragile written on the side.", size=[0.30, 0.40, 0.25], placements=[AssetInstance() for _ in range(1)])
storage_cabinet_A = Assets(description="A light wooden wardrobe.", size=[0.45, 0.80, 1.80], placements=[AssetInstance() for _ in range(1)])
breakout_chair_B = Assets(description="Gray plastic chair with no arms and thin wood legs.", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_B = Assets(description="A painting of a woman covered with white clouds in a gold frame.", size=[0.06, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
file_tray = Assets(description="Red wood toolbox with handle.", size=[0.25, 0.35, 0.20], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_C = Assets(description="A painting of a woman covered with white clouds in a gold frame.", size=[0.06, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
side_console_table = Assets(description="A desk with three drawers.", size=[0.45, 1.20, 0.76], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_D = Assets(description="A painting of a woman covered with white clouds in a gold frame.", size=[0.06, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
boardroom_sideboard = Assets(description="A tv stand that is long and has legs in its middle section only.. it has cabinets on each side.", size=[0.45, 1.80, 0.70], placements=[AssetInstance() for _ in range(1)])
breakout_chair_C = Assets(description="Gray plastic chair with no arms and thin wood legs.", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
boardroom_table = Assets(description="A long white table with two black spines.", size=[1.20, 3.20, 0.75], placements=[AssetInstance() for _ in range(1)])
storage_cabinet_B = Assets(description="A light wooden wardrobe.", size=[0.45, 0.80, 1.80], placements=[AssetInstance() for _ in range(1)])
storage_box_small_B = Assets(description="A wooden box with the lid off and the word fragile written on the side.", size=[0.30, 0.40, 0.25], placements=[AssetInstance() for _ in range(1)])
breakout_chair_D = Assets(description="Gray plastic chair with no arms and thin wood legs.", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
notepad = Assets(description="Paper scroll with lines of handwriting.", size=[0.30, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_E = Assets(description="A painting of a woman covered with white clouds in a gold frame.", size=[0.06, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
floor_plant_large_A = Assets(description="A leafy plant inside a brown clay pot.", size=[0.65, 0.65, 1.50], placements=[AssetInstance() for _ in range(1)])
presentation_console_table = Assets(description="presentation console table", size=[0.50, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
boardroom_chair = Assets(description="A black recessed armchair with small gap where the seat rest meets the backrest on five gray wheels.", size=[0.65, 0.65, 1.05], placements=[AssetInstance() for _ in range(1)])
floor_plant_large_B = Assets(description="A leafy plant inside a brown clay pot.", size=[0.65, 0.65, 1.50], placements=[AssetInstance() for _ in range(1)])
breakout_chair_E = Assets(description="Gray plastic chair with no arms and thin wood legs.", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
tray = Assets(description="A blue dining tray.", size=[0.30, 0.40, 0.04], placements=[AssetInstance() for _ in range(1)])
small_plant = Assets(description="A potted plant with green leaves.", size=[0.22, 0.22, 0.32], placements=[AssetInstance() for _ in range(1)])
floor_plant_large_C = Assets(description="A leafy plant inside a brown clay pot.", size=[0.65, 0.65, 1.50], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_F = Assets(description="A painting of a woman covered with white clouds in a gold frame.", size=[0.06, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
wall_display_screen = Assets(description="A poster of blueprints for a picture frame.", size=[0.07, 1.65, 0.93], placements=[AssetInstance() for _ in range(1)])

wall_whiteboard[0].instance_id = 'wall_whiteboard_0'
coat_stand[0].instance_id = 'coat_stand_0'
acoustic_panel_A[0].instance_id = 'acoustic_panel_A_0'
breakout_round_table[0].instance_id = 'breakout_round_table_0'
paper_stack[0].instance_id = 'paper_stack_0'
picture_frame[0].instance_id = 'picture_frame_0'
breakout_chair_A[0].instance_id = 'breakout_chair_A_0'
storage_box_small_A[0].instance_id = 'storage_box_small_A_0'
storage_cabinet_A[0].instance_id = 'storage_cabinet_A_0'
breakout_chair_B[0].instance_id = 'breakout_chair_B_0'
acoustic_panel_B[0].instance_id = 'acoustic_panel_B_0'
file_tray[0].instance_id = 'file_tray_0'
acoustic_panel_C[0].instance_id = 'acoustic_panel_C_0'
side_console_table[0].instance_id = 'side_console_table_0'
acoustic_panel_D[0].instance_id = 'acoustic_panel_D_0'
boardroom_sideboard[0].instance_id = 'boardroom_sideboard_0'
breakout_chair_C[0].instance_id = 'breakout_chair_C_0'
boardroom_table[0].instance_id = 'boardroom_table_0'
storage_cabinet_B[0].instance_id = 'storage_cabinet_B_0'
storage_box_small_B[0].instance_id = 'storage_box_small_B_0'
breakout_chair_D[0].instance_id = 'breakout_chair_D_0'
notepad[0].instance_id = 'notepad_0'
acoustic_panel_E[0].instance_id = 'acoustic_panel_E_0'
floor_plant_large_A[0].instance_id = 'floor_plant_large_A_0'
presentation_console_table[0].instance_id = 'presentation_console_table_0'
boardroom_chair[0].instance_id = 'boardroom_chair_0'
floor_plant_large_B[0].instance_id = 'floor_plant_large_B_0'
breakout_chair_E[0].instance_id = 'breakout_chair_E_0'
tray[0].instance_id = 'tray_0'
small_plant[0].instance_id = 'small_plant_0'
floor_plant_large_C[0].instance_id = 'floor_plant_large_C_0'
acoustic_panel_F[0].instance_id = 'acoustic_panel_F_0'
wall_display_screen[0].instance_id = 'wall_display_screen_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

wall_whiteboard[0].position = [1.5165658042313863, 5.33283284751513, 0.5]
wall_whiteboard[0].rotation = [0, 0, 0]
coat_stand[0].position = [4.0255367837867, 0.16214738982621135, 0.9]
coat_stand[0].rotation = [0, 0, 0]
acoustic_panel_A[0].position = [3.7322568674549963, 4.520502698443217, 0.45]
acoustic_panel_A[0].rotation = [0, 0, 0]
breakout_round_table[0].position = [0.818259502649572, 5.868426733757659, 0.375]
breakout_round_table[0].rotation = [0, 0, 0]
paper_stack[0].position = [3.0293173806223725, 1.19857391072942, 0.06]
paper_stack[0].rotation = [0, 0, 0]
picture_frame[0].position = [3.5514720477763753, 5.914095306832879, 0.125]
picture_frame[0].rotation = [0, 0, 0]
breakout_chair_A[0].position = [0.5859291016923551, 1.3357952047277801, 0.41]
breakout_chair_A[0].rotation = [0, 0, 0]
storage_box_small_A[0].position = [3.2303472656770014, 4.286308046238614, 0.125]
storage_box_small_A[0].rotation = [0, 0, 0]
storage_cabinet_A[0].position = [3.242509054077339, 1.842556604565649, 0.9]
storage_cabinet_A[0].rotation = [0, 0, 0]
breakout_chair_B[0].position = [3.153533653989162, 3.9023186030357544, 0.41]
breakout_chair_B[0].rotation = [0, 0, 0]
acoustic_panel_B[0].position = [5.408126067492676, 5.222916276262231, 0.45]
acoustic_panel_B[0].rotation = [0, 0, 0]
file_tray[0].position = [3.886086858404896, 3.4467648605354064, 0.1]
file_tray[0].rotation = [0, 0, 0]
acoustic_panel_C[0].position = [5.8791062425653555, 4.020728042710182, 0.45]
acoustic_panel_C[0].rotation = [0, 0, 0]
side_console_table[0].position = [0.0014175276619923238, 0.8551143891744011, 0.38]
side_console_table[0].rotation = [0, 0, 0]
acoustic_panel_D[0].position = [1.283841529031422, 4.241828591699193, 0.45]
acoustic_panel_D[0].rotation = [0, 0, 0]
boardroom_sideboard[0].position = [1.503066312018369, 0.9494018700059395, 0.35]
boardroom_sideboard[0].rotation = [0, 0, 0]
breakout_chair_C[0].position = [6.551811834536093, 0.543838817288419, 0.41]
breakout_chair_C[0].rotation = [0, 0, 0]
boardroom_table[0].position = [3.3680851853386873, 1.1253455875745393, 0.375]
boardroom_table[0].rotation = [0, 0, 0]
storage_cabinet_B[0].position = [7.493491656958199, 1.4283867643742165, 0.9]
storage_cabinet_B[0].rotation = [0, 0, 0]
storage_box_small_B[0].position = [1.0960743416826428, 2.2996608024679954, 0.125]
storage_box_small_B[0].rotation = [0, 0, 0]
breakout_chair_D[0].position = [3.79599908542637, 5.697213120459574, 0.41]
breakout_chair_D[0].rotation = [0, 0, 0]
notepad[0].position = [0.33484228932500315, 2.557610056735063, 0.0075]
notepad[0].rotation = [0, 0, 0]
acoustic_panel_E[0].position = [7.508322036301236, 4.516450845337315, 0.45]
acoustic_panel_E[0].rotation = [0, 0, 0]
floor_plant_large_A[0].position = [3.1327143111751923, 1.462111165064781, 0.75]
floor_plant_large_A[0].rotation = [0, 0, 0]
presentation_console_table[0].position = [4.899363356848106, 0.1077304185648511, 0.45]
presentation_console_table[0].rotation = [0, 0, 0]
boardroom_chair[0].position = [0.6626341437292576, 4.647809521434169, 0.525]
boardroom_chair[0].rotation = [0, 0, 0]
floor_plant_large_B[0].position = [3.8475125754430453, 5.5536975528561925, 0.75]
floor_plant_large_B[0].rotation = [0, 0, 0]
breakout_chair_E[0].position = [1.0510765099087918, 1.4220704029023312, 0.41]
breakout_chair_E[0].rotation = [0, 0, 0]
tray[0].position = [1.3038995626272891, 3.7274492866433317, 0.02]
tray[0].rotation = [0, 0, 0]
small_plant[0].position = [5.16516945984463, 1.7245750250669956, 0.16]
small_plant[0].rotation = [0, 0, 0]
floor_plant_large_C[0].position = [0.9934228177757403, 1.2475972925684895, 0.75]
floor_plant_large_C[0].rotation = [0, 0, 0]
acoustic_panel_F[0].position = [6.4240816885932315, 1.7098539708455835, 0.45]
acoustic_panel_F[0].rotation = [0, 0, 0]
wall_display_screen[0].position = [1.0439723320688277, 3.3797274053384854, 0.465]
wall_display_screen[0].rotation = [0, 0, 0]
wall_whiteboard[0].position = [1.5165658042313863, 5.33283284751513, 0.5]
wall_whiteboard[0].rotation = [0, 0, 0]
coat_stand[0].position = [4.0255367837867, 0.16214738982621135, 0.9]
coat_stand[0].rotation = [0, 0, 0]
acoustic_panel_A[0].position = [3.7322568674549963, 4.520502698443217, 0.45]
acoustic_panel_A[0].rotation = [0, 0, 0]
breakout_round_table[0].position = [0.818259502649572, 5.868426733757659, 0.375]
breakout_round_table[0].rotation = [0, 0, 0]
paper_stack[0].position = [3.0293173806223725, 1.19857391072942, 0.06]
paper_stack[0].rotation = [0, 0, 0]
picture_frame[0].position = [3.5514720477763753, 5.914095306832879, 0.125]
picture_frame[0].rotation = [0, 0, 0]
breakout_chair_A[0].position = [0.5859291016923551, 1.3357952047277801, 0.41]
breakout_chair_A[0].rotation = [0, 0, 0]
storage_box_small_A[0].position = [3.2303472656770014, 4.286308046238614, 0.125]
storage_box_small_A[0].rotation = [0, 0, 0]
storage_cabinet_A[0].position = [3.242509054077339, 1.842556604565649, 0.9]
storage_cabinet_A[0].rotation = [0, 0, 0]
breakout_chair_B[0].position = [3.153533653989162, 3.9023186030357544, 0.41]
breakout_chair_B[0].rotation = [0, 0, 0]
acoustic_panel_B[0].position = [5.408126067492676, 5.222916276262231, 0.45]
acoustic_panel_B[0].rotation = [0, 0, 0]
file_tray[0].position = [3.886086858404896, 3.4467648605354064, 0.1]
file_tray[0].rotation = [0, 0, 0]
acoustic_panel_C[0].position = [5.8791062425653555, 4.020728042710182, 0.45]
acoustic_panel_C[0].rotation = [0, 0, 0]
side_console_table[0].position = [0.0014175276619923238, 0.8551143891744011, 0.38]
side_console_table[0].rotation = [0, 0, 0]
acoustic_panel_D[0].position = [1.283841529031422, 4.241828591699193, 0.45]
acoustic_panel_D[0].rotation = [0, 0, 0]
boardroom_sideboard[0].position = [1.503066312018369, 0.9494018700059395, 0.35]
boardroom_sideboard[0].rotation = [0, 0, 0]
breakout_chair_C[0].position = [6.551811834536093, 0.543838817288419, 0.41]
breakout_chair_C[0].rotation = [0, 0, 0]
boardroom_table[0].position = [3.3680851853386873, 1.1253455875745393, 0.375]
boardroom_table[0].rotation = [0, 0, 0]
storage_cabinet_B[0].position = [7.493491656958199, 1.4283867643742165, 0.9]
storage_cabinet_B[0].rotation = [0, 0, 0]
storage_box_small_B[0].position = [1.0960743416826428, 2.2996608024679954, 0.125]
storage_box_small_B[0].rotation = [0, 0, 0]
breakout_chair_D[0].position = [3.79599908542637, 5.697213120459574, 0.41]
breakout_chair_D[0].rotation = [0, 0, 0]
notepad[0].position = [0.33484228932500315, 2.557610056735063, 0.0075]
notepad[0].rotation = [0, 0, 0]
acoustic_panel_E[0].position = [7.508322036301236, 4.516450845337315, 0.45]
acoustic_panel_E[0].rotation = [0, 0, 0]
floor_plant_large_A[0].position = [3.1327143111751923, 1.462111165064781, 0.75]
floor_plant_large_A[0].rotation = [0, 0, 0]
presentation_console_table[0].position = [4.899363356848106, 0.1077304185648511, 0.45]
presentation_console_table[0].rotation = [0, 0, 0]
boardroom_chair[0].position = [0.6626341437292576, 4.647809521434169, 0.525]
boardroom_chair[0].rotation = [0, 0, 0]
floor_plant_large_B[0].position = [3.8475125754430453, 5.5536975528561925, 0.75]
floor_plant_large_B[0].rotation = [0, 0, 0]
breakout_chair_E[0].position = [1.0510765099087918, 1.4220704029023312, 0.41]
breakout_chair_E[0].rotation = [0, 0, 0]
tray[0].position = [1.3038995626272891, 3.7274492866433317, 0.02]
tray[0].rotation = [0, 0, 0]
small_plant[0].position = [5.16516945984463, 1.7245750250669956, 0.16]
small_plant[0].rotation = [0, 0, 0]
floor_plant_large_C[0].position = [0.9934228177757403, 1.2475972925684895, 0.75]
floor_plant_large_C[0].rotation = [0, 0, 0]
acoustic_panel_F[0].position = [6.4240816885932315, 1.7098539708455835, 0.45]
acoustic_panel_F[0].rotation = [0, 0, 0]
wall_display_screen[0].position = [1.0439723320688277, 3.3797274053384854, 0.465]
wall_display_screen[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the supplied plan coordinates: the recess x > 4, 2 < y < 4
# is outside the room. Keep the west doorway and its approach clear.
# Each placement receives a fixed-position constraint and a rotation constraint.
# Fixed references are constraint anchors, not additional scene furniture.
def place_asset(asset, xyz, heading, support=None, wall_index=None):
    instance = asset[0]
    instance.position = list(xyz)
    instance.rotation = [0, 0, radians(heading)]

    # Establish support first so tabletop objects never migrate to the floor.
    if support is not None:
        solver.on_top_of(instance, support[0])

    anchor = AssetInstance(
        position=list(xyz),
        rotation=[0, 0, radians(heading)]
    )
    solver.distance_constraint(instance, anchor, 0, 0, weight=10)
    solver.align_with(instance, anchor)

    if wall_index is not None:
        solver.against_wall(instance, walls[wall_index])


# Main meeting area in the lower-left portion of the room.
# The table's long local y-axis becomes the room's x-axis.
place_asset(boardroom_table, [2.30, 1.50, 0.375], 90)

# These three chairs form an evenly spaced row.
# B (o0009) is explicitly between A (o0006) and E (o0027).
place_asset(breakout_chair_A, [1.60, 2.65, 0.41], -90)
place_asset(breakout_chair_B, [2.40, 2.65, 0.41], -90)
place_asset(breakout_chair_E, [3.20, 2.65, 0.41], -90)
place_asset(boardroom_chair, [4.45, 1.50, 0.525], 180)

# Storage along the southwest wall does not obstruct the windows.
place_asset(storage_cabinet_A, [0.225, 0.60, 0.90], 0, wall_index=7)
place_asset(storage_cabinet_B, [0.225, 1.60, 0.90], 0, wall_index=7)
place_asset(
    storage_box_small_A, [0.225, 0.60, 1.925], 0,
    support=storage_cabinet_A
)
place_asset(
    storage_box_small_B, [0.225, 1.60, 1.925], 0,
    support=storage_cabinet_B
)

# Presentation station on the inside vertical wall of the recess.
# The board is mounted above the console, rather than intersecting it.
place_asset(
    presentation_console_table, [3.75, 3.35, 0.45], 180,
    wall_index=3
)
place_asset(
    wall_whiteboard, [3.975, 2.95, 1.70], 180,
    wall_index=3
)
place_asset(
    file_tray, [3.75, 3.40, 1.00], 180,
    support=presentation_console_table
)

# Upper-right breakout area; all furniture stays north of y=4.
place_asset(breakout_round_table, [5.60, 5.00, 0.375], 0)
place_asset(breakout_chair_C, [4.65, 5.00, 0.41], 0)
place_asset(side_console_table, [7.775, 5.00, 0.38], 180, wall_index=5)
place_asset(breakout_chair_D, [6.85, 5.00, 0.41], 0)

# Upper-left storage leaves the west doorway's entire width unobstructed.
place_asset(boardroom_sideboard, [2.60, 5.775, 0.35], -90, wall_index=6)
place_asset(coat_stand, [0.40, 5.50, 0.90], 0)

# Plants occupy corners or peripheral pockets, not circulation routes.
place_asset(floor_plant_large_A, [7.60, 0.40, 0.75], 180)
place_asset(floor_plant_large_B, [6.90, 4.40, 0.75], 90)
place_asset(floor_plant_large_C, [0.40, 2.50, 0.75], 0)

# Small objects are supported by actual furniture, with separated footprints.
place_asset(paper_stack, [2.20, 5.775, 0.76], -90, support=boardroom_sideboard)
place_asset(picture_frame, [7.775, 5.35, 0.885], 180, support=side_console_table)
place_asset(notepad, [2.30, 1.50, 0.755], 90, support=boardroom_table)
place_asset(tray, [5.40, 5.00, 0.77], 0, support=breakout_round_table)
place_asset(small_plant, [5.85, 5.10, 0.91], 0, support=breakout_round_table)

# Wall-mounted pieces sit above furniture or in solid wall sections.
# The bottom-wall panel occupies the gap between the two windows.
place_asset(acoustic_panel_A, [1.40, 5.97, 1.65], -90, wall_index=6)
place_asset(acoustic_panel_B, [2.50, 5.97, 1.65], -90, wall_index=6)
place_asset(acoustic_panel_C, [3.60, 5.97, 1.65], -90, wall_index=6)
place_asset(acoustic_panel_D, [3.65, 0.03, 1.65], 90, wall_index=0)
place_asset(acoustic_panel_E, [7.97, 1.10, 1.65], 180, wall_index=1)
place_asset(acoustic_panel_F, [7.97, 5.00, 1.80], 180, wall_index=5)
place_asset(wall_display_screen, [5.60, 5.965, 1.70], -90, wall_index=6)

# Functional facing constraints.
solver.point_towards(breakout_chair_D[0], side_console_table[0])
solver.point_towards(breakout_chair_C[0], breakout_round_table[0])
solver.point_towards(boardroom_chair[0], boardroom_table[0])
for meeting_seat in (
    breakout_chair_A[0], breakout_chair_B[0], breakout_chair_E[0]
):
    solver.point_towards(
        meeting_seat,
        AssetInstance(position=[
            meeting_seat.position[0], 1.50, meeting_seat.position[2]
        ])
    )

# Maintain the ordered chair row, including the requested "between" relation.
solver.align_with(breakout_chair_B[0], breakout_chair_A[0])
solver.align_with(breakout_chair_E[0], breakout_chair_B[0])
solver.distance_constraint(
    breakout_chair_B[0], breakout_chair_A[0], 0.80, 0.80, weight=10
)
solver.distance_constraint(
    breakout_chair_B[0], breakout_chair_E[0], 0.80, 0.80, weight=10
)
solver.distance_constraint(
    breakout_chair_E[0], breakout_chair_A[0], 1.60, 1.60, weight=10
)

solver.constraints = []
acoustic_panel_A[0].position = [1.399999976158142, 5.979129314422607, 0.44999998807907104]
acoustic_panel_A[0].rotation = [0, 0, -1.5682554083443117]
acoustic_panel_A[0].optimize = 2
acoustic_panel_F[0].position = [7.96999979019165, 5.0, 0.44999998807907104]
acoustic_panel_F[0].rotation = [0, 0, -3.1390517317728355]
acoustic_panel_F[0].optimize = 2
boardroom_sideboard[0].position = [2.5999999046325684, 5.770890712738037, 0.3499999940395355]
boardroom_sideboard[0].rotation = [0, 0, -1.5651448213586012]
boardroom_sideboard[0].optimize = 2
breakout_chair_A[0].position = [1.600000023841858, 2.6500000953674316, 0.4099999964237213]
breakout_chair_A[0].rotation = [0, 0, -1.548805178508874]
breakout_chair_A[0].optimize = 2
file_tray[0].position = [3.75, 3.4000000953674316, 1.0]
file_tray[0].rotation = [0, 0, -3.1290262823329655]
file_tray[0].optimize = 2
boardroom_table[0].position = [2.299999952316284, 1.5, 0.375]
boardroom_table[0].rotation = [0, 0, 1.586504290712113]
boardroom_table[0].optimize = 2
boardroom_chair[0].position = [4.449999809265137, 1.5, 0.5249999761581421]
boardroom_chair[0].rotation = [0, 0, -3.1290262823329655]
boardroom_chair[0].optimize = 2
breakout_chair_D[0].position = [6.849999904632568, 5.0, 0.4099999964237213]
breakout_chair_D[0].rotation = [0, 0, 0.01256637125682779]
breakout_chair_D[0].optimize = 2
tray[0].position = [5.400000095367432, 5.0, 0.7699999809265137]
tray[0].rotation = [0, 0, 0.01256637125682779]
tray[0].optimize = 2
picture_frame[0].position = [7.775000095367432, 5.349999904632568, 0.8849999904632568]
picture_frame[0].rotation = [0, 0, -3.1290262823329655]
picture_frame[0].optimize = 2
storage_box_small_A[0].position = [0.22499999403953552, 0.6000000238418579, 1.9249999523162842]
storage_box_small_A[0].rotation = [0, 0, 0.01256637125682779]
storage_box_small_A[0].optimize = 2
floor_plant_large_B[0].position = [6.900000095367432, 4.400000095367432, 0.75]
floor_plant_large_B[0].rotation = [0, 0, 1.5802211042556205]
floor_plant_large_B[0].optimize = 2
storage_cabinet_A[0].position = [0.22725701332092285, 0.6000000238418579, 0.8999999761581421]
storage_cabinet_A[0].rotation = [0, 0, 0.005651520505222603]
storage_cabinet_A[0].optimize = 2
wall_whiteboard[0].position = [3.9736924171447754, 2.950000047683716, 0.5]
wall_whiteboard[0].rotation = [0, 0, -3.139051755037489]
wall_whiteboard[0].optimize = 2
wall_display_screen[0].position = [5.599999904632568, 5.964635372161865, 0.4650000035762787]
wall_display_screen[0].rotation = [0, 0, -1.5682554251761522]
wall_display_screen[0].optimize = 2
paper_stack[0].position = [2.200000047683716, 5.775000095367432, 0.7599999904632568]
paper_stack[0].rotation = [0, 0, -1.5582299555380688]
paper_stack[0].optimize = 2
breakout_round_table[0].position = [5.599999904632568, 5.0, 0.375]
breakout_round_table[0].rotation = [0, 0, 0.01884955539881635]
breakout_round_table[0].optimize = 2
acoustic_panel_E[0].position = [7.979129314422607, 1.100000023841858, 0.44999998807907104]
acoustic_panel_E[0].rotation = [0, 0, -3.1390517351392084]
acoustic_panel_E[0].optimize = 2
acoustic_panel_B[0].position = [2.5, 5.979129314422607, 0.44999998807907104]
acoustic_panel_B[0].rotation = [0, 0, -1.5682554083443117]
acoustic_panel_B[0].optimize = 2
floor_plant_large_C[0].position = [0.4000000059604645, 2.5, 0.75]
floor_plant_large_C[0].rotation = [0, 0, 0.00942477746072377]
floor_plant_large_C[0].optimize = 2
notepad[0].position = [2.299999952316284, 1.5, 0.7549999952316284]
notepad[0].rotation = [0, 0, 1.5833626980517244]
notepad[0].optimize = 2
acoustic_panel_C[0].position = [3.5999999046325684, 5.979129314422607, 0.44999998807907104]
acoustic_panel_C[0].rotation = [0, 0, -1.5682554083443117]
acoustic_panel_C[0].optimize = 2
presentation_console_table[0].position = [3.7466132640838623, 3.3499999046325684, 0.44999998807907104]
presentation_console_table[0].rotation = [0, 0, -3.1359411371853607]
presentation_console_table[0].optimize = 2
breakout_chair_B[0].position = [2.4000000953674316, 2.6500000953674316, 0.4099999964237213]
breakout_chair_B[0].rotation = [0, 0, -1.555807461625742]
breakout_chair_B[0].optimize = 2
storage_box_small_B[0].position = [0.22499999403953552, 1.600000023841858, 1.9249999523162842]
storage_box_small_B[0].rotation = [0, 0, 0.01256637125682779]
storage_box_small_B[0].optimize = 2
small_plant[0].position = [5.849999904632568, 5.099999904632568, 0.9099999666213989]
small_plant[0].rotation = [0, 0, 0.01256637125682779]
small_plant[0].optimize = 2
storage_cabinet_B[0].position = [0.22725701332092285, 1.600000023841858, 0.8999999761581421]
storage_cabinet_B[0].rotation = [0, 0, 0.005651520505222603]
storage_cabinet_B[0].optimize = 2
floor_plant_large_A[0].position = [7.599999904632568, 0.4000000059604645, 0.75]
floor_plant_large_A[0].rotation = [0, 0, -3.1321678761290697]
floor_plant_large_A[0].optimize = 2
breakout_chair_C[0].position = [4.650000095367432, 5.0, 0.4099999964237213]
breakout_chair_C[0].rotation = [0, 0, 0.01256637125682779]
breakout_chair_C[0].optimize = 2
coat_stand[0].position = [0.4000000059604645, 5.5, 0.8999999761581421]
coat_stand[0].rotation = [0, 0, 0.00942477746072377]
coat_stand[0].optimize = 2
breakout_chair_E[0].position = [3.200000047683716, 2.6500000953674316, 0.4099999964237213]
breakout_chair_E[0].rotation = [0, 0, -1.5384950459217612]
breakout_chair_E[0].optimize = 2
side_console_table[0].position = [7.763730525970459, 5.0, 0.3799999952316284]
side_console_table[0].rotation = [0, 0, -3.1328304277986425]
side_console_table[0].optimize = 2
acoustic_panel_D[0].position = [3.6500000953674316, 0.020954743027687073, 0.44999998807907104]
acoustic_panel_D[0].rotation = [0, 0, 1.573337246167655]
acoustic_panel_D[0].optimize = 2

