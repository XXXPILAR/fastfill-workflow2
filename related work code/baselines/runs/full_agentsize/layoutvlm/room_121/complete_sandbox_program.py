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
wall_whiteboard = Assets(description="A white rectangular poster with black blue and orange marks and irregular writing.", size=[0.05, 2.40, 1.20], placements=[AssetInstance() for _ in range(1)])
coat_stand = Assets(description="The coatrack is wooden with a round bottom.", size=[0.50, 0.50, 1.80], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_A = Assets(description="A painting of a woman covered with white clouds in a gold frame.", size=[0.05, 0.90, 1.20], placements=[AssetInstance() for _ in range(1)])
breakout_round_table = Assets(description="Round table with wood top and four tapered legs.", size=[1.00, 1.00, 0.75], placements=[AssetInstance() for _ in range(1)])
paper_stack = Assets(description="A stack of colorful, pixelated-style books in different colors.", size=[0.22, 0.30, 0.12], placements=[AssetInstance() for _ in range(1)])
picture_frame = Assets(description="Picture of trees by a lake in black picture frame.", size=[0.12, 0.40, 0.30], placements=[AssetInstance() for _ in range(1)])
breakout_chair_A = Assets(description="Gray plastic chair with no arms and thin wood legs.", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
storage_box_small_A = Assets(description="A wooden box with the lid off and the word fragile written on the side.", size=[0.35, 0.45, 0.30], placements=[AssetInstance() for _ in range(1)])
storage_cabinet_A = Assets(description="A light wooden wardrobe.", size=[0.50, 1.00, 1.80], placements=[AssetInstance() for _ in range(1)])
breakout_chair_B = Assets(description="Gray plastic chair with no arms and thin wood legs.", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_B = Assets(description="A painting of a woman covered with white clouds in a gold frame.", size=[0.05, 0.90, 1.20], placements=[AssetInstance() for _ in range(1)])
file_tray = Assets(description="Red wood toolbox with handle.", size=[0.28, 0.42, 0.20], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_C = Assets(description="A painting of a woman covered with white clouds in a gold frame.", size=[0.05, 0.90, 1.20], placements=[AssetInstance() for _ in range(1)])
side_console_table = Assets(description="A desk with three drawers.", size=[0.45, 1.20, 0.78], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_D = Assets(description="A painting of a woman covered with white clouds in a gold frame.", size=[0.05, 0.90, 1.20], placements=[AssetInstance() for _ in range(1)])
boardroom_sideboard = Assets(description="A tv stand that is long and has legs in its middle section only.. it has cabinets on each side.", size=[0.50, 2.20, 0.70], placements=[AssetInstance() for _ in range(1)])
breakout_chair_C = Assets(description="Gray plastic chair with no arms and thin wood legs.", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
boardroom_table = Assets(description="A long white table with two black spines.", size=[1.40, 4.00, 0.75], placements=[AssetInstance() for _ in range(1)])
storage_cabinet_B = Assets(description="A light wooden wardrobe.", size=[0.50, 1.00, 1.80], placements=[AssetInstance() for _ in range(1)])
storage_box_small_B = Assets(description="A wooden box with the lid off and the word fragile written on the side.", size=[0.35, 0.45, 0.30], placements=[AssetInstance() for _ in range(1)])
breakout_chair_D = Assets(description="Gray plastic chair with no arms and thin wood legs.", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
notepad = Assets(description="Paper scroll with lines of handwriting.", size=[0.21, 0.30, 0.02], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_E = Assets(description="A painting of a woman covered with white clouds in a gold frame.", size=[0.05, 0.90, 1.20], placements=[AssetInstance() for _ in range(1)])
floor_plant_large_A = Assets(description="A leafy plant inside a brown clay pot.", size=[0.75, 0.75, 1.65], placements=[AssetInstance() for _ in range(1)])
presentation_console_table = Assets(description="presentation console table", size=[0.55, 1.50, 0.90], placements=[AssetInstance() for _ in range(1)])
boardroom_chair = Assets(description="A black recessed armchair with small gap where the seat rest meets the backrest on five gray wheels.", size=[0.68, 0.68, 1.00], placements=[AssetInstance() for _ in range(1)])
floor_plant_large_B = Assets(description="A leafy plant inside a brown clay pot.", size=[0.75, 0.75, 1.65], placements=[AssetInstance() for _ in range(1)])
breakout_chair_E = Assets(description="Gray plastic chair with no arms and thin wood legs.", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
tray = Assets(description="A blue dining tray.", size=[0.32, 0.45, 0.04], placements=[AssetInstance() for _ in range(1)])
small_plant = Assets(description="A potted plant with green leaves.", size=[0.28, 0.28, 0.42], placements=[AssetInstance() for _ in range(1)])
floor_plant_large_C = Assets(description="A leafy plant inside a brown clay pot.", size=[0.75, 0.75, 1.65], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_F = Assets(description="A painting of a woman covered with white clouds in a gold frame.", size=[0.05, 0.90, 1.20], placements=[AssetInstance() for _ in range(1)])
wall_display_screen = Assets(description="A poster of blueprints for a picture frame.", size=[0.08, 1.60, 0.95], placements=[AssetInstance() for _ in range(1)])

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

wall_whiteboard[0].position = [6.178907153616988, 4.955763876833388, 0.6]
wall_whiteboard[0].rotation = [0, 0, 0]
coat_stand[0].position = [5.056271843058265, 0.107213914505917, 0.9]
coat_stand[0].rotation = [0, 0, 0]
acoustic_panel_A[0].position = [2.74206590635724, 1.4459501005384738, 0.6]
acoustic_panel_A[0].rotation = [0, 0, 0]
breakout_round_table[0].position = [4.493457908804205, 1.0185553820557571, 0.375]
breakout_round_table[0].rotation = [0, 0, 0]
paper_stack[0].position = [7.238973935697984, 1.1702364243181353, 0.06]
paper_stack[0].rotation = [0, 0, 0]
picture_frame[0].position = [3.6543519265622573, 3.720923477106075, 0.15]
picture_frame[0].rotation = [0, 0, 0]
breakout_chair_A[0].position = [7.8862208410475505, 0.6210952915404659, 0.41]
breakout_chair_A[0].rotation = [0, 0, 0]
storage_box_small_A[0].position = [5.405814180471804, 1.5527863858871898, 0.15]
storage_box_small_A[0].rotation = [0, 0, 0]
storage_cabinet_A[0].position = [6.26098811325161, 5.333274695789155, 0.9]
storage_cabinet_A[0].rotation = [0, 0, 0]
breakout_chair_B[0].position = [1.0284494567797369, 3.6745276573799304, 0.41]
breakout_chair_B[0].rotation = [0, 0, 0]
acoustic_panel_B[0].position = [1.8169254565009751, 1.9113451759354165, 0.6]
acoustic_panel_B[0].rotation = [0, 0, 0]
file_tray[0].position = [3.305716339388346, 0.2989270936003623, 0.1]
file_tray[0].rotation = [0, 0, 0]
acoustic_panel_C[0].position = [3.7031644584362544, 0.154163566077129, 0.6]
acoustic_panel_C[0].rotation = [0, 0, 0]
side_console_table[0].position = [2.9323732432047898, 0.8659939768141771, 0.39]
side_console_table[0].rotation = [0, 0, 0]
acoustic_panel_D[0].position = [4.8289944925629955, 0.8848450898019133, 0.6]
acoustic_panel_D[0].rotation = [0, 0, 0]
boardroom_sideboard[0].position = [5.646659904015278, 4.071366335965741, 0.35]
boardroom_sideboard[0].rotation = [0, 0, 0]
breakout_chair_C[0].position = [3.4969507819866408, 2.8344108253155227, 0.41]
breakout_chair_C[0].rotation = [0, 0, 0]
boardroom_table[0].position = [4.755260914697894, 1.1587995073940562, 0.375]
boardroom_table[0].rotation = [0, 0, 0]
storage_cabinet_B[0].position = [0.6396523388272728, 0.37242861021279583, 0.9]
storage_cabinet_B[0].rotation = [0, 0, 0]
storage_box_small_B[0].position = [5.234794748265578, 1.202533186916844, 0.15]
storage_box_small_B[0].rotation = [0, 0, 0]
breakout_chair_D[0].position = [2.997012336726618, 5.924429073275493, 0.41]
breakout_chair_D[0].rotation = [0, 0, 0]
notepad[0].position = [2.7510388687536054, 0.8007282317117947, 0.01]
notepad[0].rotation = [0, 0, 0]
acoustic_panel_E[0].position = [1.3377571538277166, 4.437059298804211, 0.6]
acoustic_panel_E[0].rotation = [0, 0, 0]
floor_plant_large_A[0].position = [3.003723981409774, 2.632453749096136, 0.825]
floor_plant_large_A[0].rotation = [0, 0, 0]
presentation_console_table[0].position = [6.2565781423096505, 4.542590967777932, 0.45]
presentation_console_table[0].rotation = [0, 0, 0]
boardroom_chair[0].position = [0.9529574744006712, 2.2921089609358676, 0.5]
boardroom_chair[0].rotation = [0, 0, 0]
floor_plant_large_B[0].position = [7.278901784819076, 4.153883461012095, 0.825]
floor_plant_large_B[0].rotation = [0, 0, 0]
breakout_chair_E[0].position = [5.020939745751088, 0.4882594302306029, 0.41]
breakout_chair_E[0].rotation = [0, 0, 0]
tray[0].position = [4.6538677356948, 4.260093109307839, 0.02]
tray[0].rotation = [0, 0, 0]
small_plant[0].position = [2.6267187217009607, 5.122571715563824, 0.21]
small_plant[0].rotation = [0, 0, 0]
floor_plant_large_C[0].position = [1.0087864637965955, 4.056434111882423, 0.825]
floor_plant_large_C[0].rotation = [0, 0, 0]
acoustic_panel_F[0].position = [3.6332638499294845, 3.071969258679038, 0.6]
acoustic_panel_F[0].rotation = [0, 0, 0]
wall_display_screen[0].position = [4.097456574431828, 5.038360760210206, 0.475]
wall_display_screen[0].rotation = [0, 0, 0]
wall_whiteboard[0].position = [6.178907153616988, 4.955763876833388, 0.6]
wall_whiteboard[0].rotation = [0, 0, 0]
coat_stand[0].position = [5.056271843058265, 0.107213914505917, 0.9]
coat_stand[0].rotation = [0, 0, 0]
acoustic_panel_A[0].position = [2.74206590635724, 1.4459501005384738, 0.6]
acoustic_panel_A[0].rotation = [0, 0, 0]
breakout_round_table[0].position = [4.493457908804205, 1.0185553820557571, 0.375]
breakout_round_table[0].rotation = [0, 0, 0]
paper_stack[0].position = [7.238973935697984, 1.1702364243181353, 0.06]
paper_stack[0].rotation = [0, 0, 0]
picture_frame[0].position = [3.6543519265622573, 3.720923477106075, 0.15]
picture_frame[0].rotation = [0, 0, 0]
breakout_chair_A[0].position = [7.8862208410475505, 0.6210952915404659, 0.41]
breakout_chair_A[0].rotation = [0, 0, 0]
storage_box_small_A[0].position = [5.405814180471804, 1.5527863858871898, 0.15]
storage_box_small_A[0].rotation = [0, 0, 0]
storage_cabinet_A[0].position = [6.26098811325161, 5.333274695789155, 0.9]
storage_cabinet_A[0].rotation = [0, 0, 0]
breakout_chair_B[0].position = [1.0284494567797369, 3.6745276573799304, 0.41]
breakout_chair_B[0].rotation = [0, 0, 0]
acoustic_panel_B[0].position = [1.8169254565009751, 1.9113451759354165, 0.6]
acoustic_panel_B[0].rotation = [0, 0, 0]
file_tray[0].position = [3.305716339388346, 0.2989270936003623, 0.1]
file_tray[0].rotation = [0, 0, 0]
acoustic_panel_C[0].position = [3.7031644584362544, 0.154163566077129, 0.6]
acoustic_panel_C[0].rotation = [0, 0, 0]
side_console_table[0].position = [2.9323732432047898, 0.8659939768141771, 0.39]
side_console_table[0].rotation = [0, 0, 0]
acoustic_panel_D[0].position = [4.8289944925629955, 0.8848450898019133, 0.6]
acoustic_panel_D[0].rotation = [0, 0, 0]
boardroom_sideboard[0].position = [5.646659904015278, 4.071366335965741, 0.35]
boardroom_sideboard[0].rotation = [0, 0, 0]
breakout_chair_C[0].position = [3.4969507819866408, 2.8344108253155227, 0.41]
breakout_chair_C[0].rotation = [0, 0, 0]
boardroom_table[0].position = [4.755260914697894, 1.1587995073940562, 0.375]
boardroom_table[0].rotation = [0, 0, 0]
storage_cabinet_B[0].position = [0.6396523388272728, 0.37242861021279583, 0.9]
storage_cabinet_B[0].rotation = [0, 0, 0]
storage_box_small_B[0].position = [5.234794748265578, 1.202533186916844, 0.15]
storage_box_small_B[0].rotation = [0, 0, 0]
breakout_chair_D[0].position = [2.997012336726618, 5.924429073275493, 0.41]
breakout_chair_D[0].rotation = [0, 0, 0]
notepad[0].position = [2.7510388687536054, 0.8007282317117947, 0.01]
notepad[0].rotation = [0, 0, 0]
acoustic_panel_E[0].position = [1.3377571538277166, 4.437059298804211, 0.6]
acoustic_panel_E[0].rotation = [0, 0, 0]
floor_plant_large_A[0].position = [3.003723981409774, 2.632453749096136, 0.825]
floor_plant_large_A[0].rotation = [0, 0, 0]
presentation_console_table[0].position = [6.2565781423096505, 4.542590967777932, 0.45]
presentation_console_table[0].rotation = [0, 0, 0]
boardroom_chair[0].position = [0.9529574744006712, 2.2921089609358676, 0.5]
boardroom_chair[0].rotation = [0, 0, 0]
floor_plant_large_B[0].position = [7.278901784819076, 4.153883461012095, 0.825]
floor_plant_large_B[0].rotation = [0, 0, 0]
breakout_chair_E[0].position = [5.020939745751088, 0.4882594302306029, 0.41]
breakout_chair_E[0].rotation = [0, 0, 0]
tray[0].position = [4.6538677356948, 4.260093109307839, 0.02]
tray[0].rotation = [0, 0, 0]
small_plant[0].position = [2.6267187217009607, 5.122571715563824, 0.21]
small_plant[0].rotation = [0, 0, 0]
floor_plant_large_C[0].position = [1.0087864637965955, 4.056434111882423, 0.825]
floor_plant_large_C[0].rotation = [0, 0, 0]
acoustic_panel_F[0].position = [3.6332638499294845, 3.071969258679038, 0.6]
acoustic_panel_F[0].rotation = [0, 0, 0]
wall_display_screen[0].position = [4.097456574431828, 5.038360760210206, 0.475]
wall_display_screen[0].rotation = [0, 0, 0]

solver.constraints = []

# Helper references used to preserve absolute positions and cardinal orientations.
_east_orientation = AssetInstance(rotation=[0, 0, radians(0)])
_north_orientation = AssetInstance(rotation=[0, 0, radians(90)])
_west_orientation = AssetInstance(rotation=[0, 0, radians(180)])
_south_orientation = AssetInstance(rotation=[0, 0, radians(-90)])


def _pin(asset_instance, position, weight=10):
    """Keep an asset near its intended, physically checked position."""
    solver.distance_constraint(
        asset_instance,
        AssetInstance(position=position),
        0,
        0,
        weight=weight,
    )


# ---------------------------------------------------------------------------
# Initial placements
# ---------------------------------------------------------------------------

# Wall-mounted presentation items occupy the north wall without covering the
# windows on the south wall.
wall_whiteboard[0].position = [1.60, 5.975, 1.60]
wall_whiteboard[0].rotation = [0, 0, radians(-90)]

acoustic_panel_A[0].position = [3.30, 5.975, 1.55]
acoustic_panel_A[0].rotation = [0, 0, radians(-90)]

acoustic_panel_B[0].position = [4.30, 5.975, 1.55]
acoustic_panel_B[0].rotation = [0, 0, radians(-90)]

acoustic_panel_C[0].position = [7.975, 4.50, 1.55]
acoustic_panel_C[0].rotation = [0, 0, radians(180)]

acoustic_panel_D[0].position = [7.975, 5.50, 1.55]
acoustic_panel_D[0].rotation = [0, 0, radians(180)]

acoustic_panel_E[0].position = [0.025, 5.45, 1.55]
acoustic_panel_E[0].rotation = [0, 0, radians(0)]

acoustic_panel_F[0].position = [0.025, 1.70, 1.55]
acoustic_panel_F[0].rotation = [0, 0, radians(0)]

wall_display_screen[0].position = [6.70, 5.96, 1.55]
wall_display_screen[0].rotation = [0, 0, radians(-90)]

# Breakout furniture is grouped in the lower-left part of the room. Chairs E,
# B, and A form a straight row, so B is explicitly between E and A.
breakout_round_table[0].position = [2.25, 1.65, 0.375]
breakout_round_table[0].rotation = [0, 0, radians(0)]

breakout_chair_E[0].position = [1.50, 0.75, 0.41]
breakout_chair_E[0].rotation = [0, 0, radians(50)]

breakout_chair_B[0].position = [2.25, 0.75, 0.41]
breakout_chair_B[0].rotation = [0, 0, radians(90)]

breakout_chair_A[0].position = [3.00, 0.75, 0.41]
breakout_chair_A[0].rotation = [0, 0, radians(130)]

breakout_chair_C[0].position = [1.45, 1.70, 0.41]
breakout_chair_C[0].rotation = [0, 0, radians(0)]

# Chair D is next to the breakout group but is aimed directly at the side
# console, as required.
breakout_chair_D[0].position = [3.05, 1.70, 0.41]
breakout_chair_D[0].rotation = [0, 0, radians(67)]

side_console_table[0].position = [3.775, 3.30, 0.39]
side_console_table[0].rotation = [0, 0, radians(180)]

# The boardroom table uses the upper-right wing. Its long axis runs east-west,
# while the chair remains in the valid upper-left portion of the floor plan.
boardroom_table[0].position = [5.90, 5.00, 0.375]
boardroom_table[0].rotation = [0, 0, radians(90)]

boardroom_chair[0].position = [3.30, 5.00, 0.50]
boardroom_chair[0].rotation = [0, 0, radians(0)]

boardroom_sideboard[0].position = [1.60, 5.75, 0.35]
boardroom_sideboard[0].rotation = [0, 0, radians(90)]

# The presentation console fits to the right of the second south-wall window.
presentation_console_table[0].position = [7.20, 0.275, 0.45]
presentation_console_table[0].rotation = [0, 0, radians(90)]

storage_cabinet_A[0].position = [7.75, 1.45, 0.90]
storage_cabinet_A[0].rotation = [0, 0, radians(180)]

storage_cabinet_B[0].position = [3.75, 2.15, 0.90]
storage_cabinet_B[0].rotation = [0, 0, radians(180)]

coat_stand[0].position = [0.50, 2.50, 0.90]
coat_stand[0].rotation = [0, 0, radians(0)]

# Plants soften otherwise unused corners while leaving the door approach clear.
floor_plant_large_A[0].position = [4.55, 0.65, 0.825]
floor_plant_large_A[0].rotation = [0, 0, radians(0)]

floor_plant_large_B[0].position = [2.00, 4.60, 0.825]
floor_plant_large_B[0].rotation = [0, 0, radians(90)]

floor_plant_large_C[0].position = [0.55, 0.55, 0.825]
floor_plant_large_C[0].rotation = [0, 0, radians(0)]

# Storage boxes are floor-standing and placed outside circulation paths.
storage_box_small_A[0].position = [4.55, 1.55, 0.15]
storage_box_small_A[0].rotation = [0, 0, radians(0)]

storage_box_small_B[0].position = [2.30, 5.75, 0.85]
storage_box_small_B[0].rotation = [0, 0, radians(90)]

# Small objects are initialized at the tops of their supporting surfaces.
paper_stack[0].position = [2.08, 1.65, 0.81]
paper_stack[0].rotation = [0, 0, radians(0)]

tray[0].position = [2.42, 1.65, 0.77]
tray[0].rotation = [0, 0, radians(0)]

picture_frame[0].position = [1.15, 5.75, 0.85]
picture_frame[0].rotation = [0, 0, radians(-90)]

notepad[0].position = [5.90, 5.00, 0.76]
notepad[0].rotation = [0, 0, radians(90)]

small_plant[0].position = [3.775, 3.30, 0.99]
small_plant[0].rotation = [0, 0, radians(0)]

# The file tray is centered on the presentation console as requested.
file_tray[0].position = [7.20, 0.275, 1.00]
file_tray[0].rotation = [0, 0, radians(90)]


# ---------------------------------------------------------------------------
# Constraints
# ---------------------------------------------------------------------------

# Wall-mounted assets: against_wall supplies the positional wall relationship,
# exact-distance anchors preserve their spacing, and alignment fixes orientation.
solver.against_wall(wall_whiteboard[0], walls[6])
_pin(wall_whiteboard[0], [1.60, 5.975, 1.60])
solver.align_with(wall_whiteboard[0], _south_orientation)

solver.against_wall(acoustic_panel_A[0], walls[6])
_pin(acoustic_panel_A[0], [3.30, 5.975, 1.55])
solver.align_with(acoustic_panel_A[0], _south_orientation)

solver.against_wall(acoustic_panel_B[0], walls[6])
_pin(acoustic_panel_B[0], [4.30, 5.975, 1.55])
solver.align_with(acoustic_panel_B[0], _south_orientation)

solver.against_wall(acoustic_panel_C[0], walls[5])
_pin(acoustic_panel_C[0], [7.975, 4.50, 1.55])
solver.align_with(acoustic_panel_C[0], _west_orientation)

solver.against_wall(acoustic_panel_D[0], walls[5])
_pin(acoustic_panel_D[0], [7.975, 5.50, 1.55])
solver.align_with(acoustic_panel_D[0], _west_orientation)

solver.against_wall(acoustic_panel_E[0], walls[7])
_pin(acoustic_panel_E[0], [0.025, 5.45, 1.55])
solver.align_with(acoustic_panel_E[0], _east_orientation)

solver.against_wall(acoustic_panel_F[0], walls[7])
_pin(acoustic_panel_F[0], [0.025, 1.70, 1.55])
solver.align_with(acoustic_panel_F[0], _east_orientation)

solver.against_wall(wall_display_screen[0], walls[6])
_pin(wall_display_screen[0], [6.70, 5.96, 1.55])
solver.align_with(wall_display_screen[0], _south_orientation)

# Breakout table and chairs.
_pin(breakout_round_table[0], [2.25, 1.65, 0.375])
solver.align_with(breakout_round_table[0], _east_orientation)

_pin(breakout_chair_E[0], [1.50, 0.75, 0.41])
solver.point_towards(breakout_chair_E[0], breakout_round_table[0])

# Equal distances to E and A, together with the anchored collinear positions,
# preserve chair B's required place between those two chairs.
solver.distance_constraint(
    breakout_chair_B[0], breakout_chair_E[0], 0.75, 0.75, weight=10
)
solver.distance_constraint(
    breakout_chair_B[0], breakout_chair_A[0], 0.75, 0.75, weight=10
)
_pin(breakout_chair_B[0], [2.25, 0.75, 0.41])
solver.point_towards(breakout_chair_B[0], breakout_round_table[0])

solver.distance_constraint(
    breakout_chair_A[0], breakout_chair_E[0], 1.50, 1.50, weight=10
)
_pin(breakout_chair_A[0], [3.00, 0.75, 0.41])
solver.point_towards(breakout_chair_A[0], breakout_round_table[0])

_pin(breakout_chair_C[0], [1.45, 1.70, 0.41])
solver.point_towards(breakout_chair_C[0], breakout_round_table[0])

_pin(breakout_chair_D[0], [3.05, 1.70, 0.41])
solver.point_towards(breakout_chair_D[0], side_console_table[0])

# Side console sits against the west-facing edge of the central recess.
solver.against_wall(side_console_table[0], walls[3])
_pin(side_console_table[0], [3.775, 3.30, 0.39])
solver.align_with(side_console_table[0], _west_orientation)

# Boardroom group.
_pin(boardroom_table[0], [5.90, 5.00, 0.375])
solver.align_with(boardroom_table[0], _north_orientation)

_pin(boardroom_chair[0], [3.30, 5.00, 0.50])
solver.point_towards(boardroom_chair[0], boardroom_table[0])

solver.against_wall(boardroom_sideboard[0], walls[6])
_pin(boardroom_sideboard[0], [1.60, 5.75, 0.35])
solver.align_with(boardroom_sideboard[0], _north_orientation)

# Perimeter furniture and storage.
solver.against_wall(presentation_console_table[0], walls[0])
_pin(presentation_console_table[0], [7.20, 0.275, 0.45])
solver.align_with(presentation_console_table[0], _north_orientation)

solver.against_wall(storage_cabinet_A[0], walls[1])
_pin(storage_cabinet_A[0], [7.75, 1.45, 0.90])
solver.align_with(storage_cabinet_A[0], _west_orientation)

solver.against_wall(storage_cabinet_B[0], walls[3])
_pin(storage_cabinet_B[0], [3.75, 2.15, 0.90])
solver.align_with(storage_cabinet_B[0], _west_orientation)

_pin(coat_stand[0], [0.50, 2.50, 0.90])
solver.align_with(coat_stand[0], _east_orientation)

_pin(storage_box_small_A[0], [4.55, 1.55, 0.15])
solver.align_with(storage_box_small_A[0], _east_orientation)

# Box B is supported by the sideboard rather than floating above the floor.
solver.on_top_of(storage_box_small_B[0], boardroom_sideboard[0])
_pin(storage_box_small_B[0], [2.30, 5.75, 0.85])
solver.align_with(storage_box_small_B[0], boardroom_sideboard[0])

# Floor plants have anchored positions and stable cardinal orientations.
_pin(floor_plant_large_A[0], [4.55, 0.65, 0.825])
solver.align_with(floor_plant_large_A[0], _east_orientation)

_pin(floor_plant_large_B[0], [2.00, 4.60, 0.825])
solver.align_with(floor_plant_large_B[0], _north_orientation)

_pin(floor_plant_large_C[0], [0.55, 0.55, 0.825])
solver.align_with(floor_plant_large_C[0], _east_orientation)

# Supported small objects. Each receives an on-top constraint, an x-y-z anchor,
# and an orientation constraint.
solver.on_top_of(paper_stack[0], breakout_round_table[0])
_pin(paper_stack[0], [2.08, 1.65, 0.81])
solver.align_with(paper_stack[0], breakout_round_table[0])

solver.on_top_of(tray[0], breakout_round_table[0])
_pin(tray[0], [2.42, 1.65, 0.77])
solver.align_with(tray[0], breakout_round_table[0])

solver.on_top_of(picture_frame[0], boardroom_sideboard[0])
_pin(picture_frame[0], [1.15, 5.75, 0.85])
solver.align_with(picture_frame[0], _south_orientation)

solver.on_top_of(notepad[0], boardroom_table[0])
_pin(notepad[0], [5.90, 5.00, 0.76])
solver.align_with(notepad[0], boardroom_table[0])

solver.on_top_of(small_plant[0], side_console_table[0])
_pin(small_plant[0], [3.775, 3.30, 0.99])
solver.align_with(small_plant[0], side_console_table[0])

# Highest-priority semantic requirement: the file tray remains on the
# presentation console even if the surrounding layout is adjusted.
solver.on_top_of(file_tray[0], presentation_console_table[0])
_pin(file_tray[0], [7.20, 0.275, 1.00])
solver.align_with(file_tray[0], presentation_console_table[0])

solver.constraints = []
breakout_chair_D[0].position = [3.049999952316284, 1.7000000476837158, 0.4099999964237213]
breakout_chair_D[0].rotation = [0, 0, 1.1787953728994864]
breakout_chair_D[0].optimize = 2
acoustic_panel_E[0].position = [0.024998709559440613, 5.449999809265137, 0.6000000238418579]
acoustic_panel_E[0].rotation = [0, 0, -1.95032346724951e-06]
acoustic_panel_E[0].optimize = 2
boardroom_sideboard[0].position = [1.600000023841858, 5.5512237548828125, 0.3499999940395355]
boardroom_sideboard[0].rotation = [0, 0, -1.629108581779846]
boardroom_sideboard[0].optimize = 2
breakout_chair_C[0].position = [1.4500000476837158, 1.7000000476837158, 0.4099999964237213]
breakout_chair_C[0].rotation = [0, 0, 0.00942477746072377]
breakout_chair_C[0].optimize = 2
small_plant[0].position = [3.7750000953674316, 3.299999952316284, 0.9899999499320984]
small_plant[0].rotation = [0, 0, -2.7960490392469675]
small_plant[0].optimize = 2
boardroom_chair[0].position = [3.299999952316284, 5.0, 0.5]
boardroom_chair[0].rotation = [0, 0, 0.00942477746072377]
boardroom_chair[0].optimize = 2
acoustic_panel_C[0].position = [7.974999904632568, 4.5, 0.6000000238418579]
acoustic_panel_C[0].rotation = [0, 0, 3.1415907036924335]
acoustic_panel_C[0].optimize = 2
boardroom_table[0].position = [5.900000095367432, 5.0, 0.375]
boardroom_table[0].rotation = [0, 0, 1.589645882193713]
boardroom_table[0].optimize = 2
file_tray[0].position = [7.199999809265137, 0.2750000059604645, 1.0]
file_tray[0].rotation = [0, 0, 1.570797370260824]
file_tray[0].optimize = 2
tray[0].position = [2.4200000762939453, 1.649999976158142, 0.7699999809265137]
tray[0].rotation = [0, 0, 0.034553989007321616]
tray[0].optimize = 2
storage_box_small_B[0].position = [1.6346293687820435, 5.428093433380127, 0.8500000238418579]
storage_box_small_B[0].rotation = [0, 0, -1.6342318736868007]
storage_box_small_B[0].optimize = 2
acoustic_panel_A[0].position = [3.299999952316284, 5.975001335144043, 0.6000000238418579]
acoustic_panel_A[0].rotation = [0, 0, -1.5707982796276656]
acoustic_panel_A[0].optimize = 2
breakout_round_table[0].position = [2.25, 1.649999976158142, 0.375]
breakout_round_table[0].rotation = [0, 0, 0.03455751882667646]
breakout_round_table[0].optimize = 2
floor_plant_large_B[0].position = [2.0, 4.599999904632568, 0.824999988079071]
floor_plant_large_B[0].rotation = [0, 0, 1.5802211042556205]
floor_plant_large_B[0].optimize = 2
side_console_table[0].position = [3.775000810623169, 3.299999952316284, 0.38999998569488525]
side_console_table[0].rotation = [0, 0, -3.1415887559996882]
side_console_table[0].optimize = 2
storage_box_small_A[0].position = [4.550000190734863, 1.5499999523162842, 0.15000000596046448]
storage_box_small_A[0].rotation = [0, 0, 0.00942477746072377]
storage_box_small_A[0].optimize = 2
notepad[0].position = [5.900000095367432, 5.0, 0.7599999904632568]
notepad[0].rotation = [0, 0, 1.5896446564284554]
notepad[0].optimize = 2
paper_stack[0].position = [2.0799999237060547, 1.649999976158142, 0.8100000023841858]
paper_stack[0].rotation = [0, 0, 0.034553989007321616]
paper_stack[0].optimize = 2
wall_whiteboard[0].position = [1.600000023841858, 5.975000381469727, 0.6000000238418579]
wall_whiteboard[0].rotation = [0, 0, -1.5707983522045077]
wall_whiteboard[0].optimize = 2
storage_cabinet_A[0].position = [7.750000476837158, 1.4500000476837158, 0.8999999761581421]
storage_cabinet_A[0].rotation = [0, 0, 3.1415906858532545]
storage_cabinet_A[0].optimize = 2
breakout_chair_B[0].position = [2.25, 0.75, 0.4099999964237213]
breakout_chair_B[0].rotation = [0, 0, 1.586504290712113]
breakout_chair_B[0].optimize = 2
picture_frame[0].position = [1.149999976158142, 5.75, 0.8500000238418579]
picture_frame[0].rotation = [0, 0, -1.5582299555380688]
picture_frame[0].optimize = 2
acoustic_panel_B[0].position = [4.300000190734863, 5.975001335144043, 0.6000000238418579]
acoustic_panel_B[0].rotation = [0, 0, -1.5707982796276656]
acoustic_panel_B[0].optimize = 2
breakout_chair_A[0].position = [3.0, 0.75, 0.4099999964237213]
breakout_chair_A[0].rotation = [0, 0, 2.2846359850931197]
breakout_chair_A[0].optimize = 2
presentation_console_table[0].position = [7.199999809265137, 0.2750006318092346, 0.44999998807907104]
presentation_console_table[0].rotation = [0, 0, 1.5707990644988241]
presentation_console_table[0].optimize = 2
breakout_chair_E[0].position = [1.5, 0.75, 0.4099999964237213]
breakout_chair_E[0].rotation = [0, 0, 0.8883725932821318]
breakout_chair_E[0].optimize = 2
wall_display_screen[0].position = [6.699999809265137, 5.960000991821289, 0.4749999940395355]
wall_display_screen[0].rotation = [0, 0, -1.5707982732655648]
wall_display_screen[0].optimize = 2
coat_stand[0].position = [0.5, 2.5, 0.8999999761581421]
coat_stand[0].rotation = [0, 0, 0.00942477746072377]
coat_stand[0].optimize = 2
floor_plant_large_A[0].position = [4.550000190734863, 0.6499999761581421, 0.824999988079071]
floor_plant_large_A[0].rotation = [0, 0, 0.00942477746072377]
floor_plant_large_A[0].optimize = 2
floor_plant_large_C[0].position = [0.550000011920929, 0.550000011920929, 0.824999988079071]
floor_plant_large_C[0].rotation = [0, 0, 0.00942477746072377]
floor_plant_large_C[0].optimize = 2
acoustic_panel_F[0].position = [0.024998709559440613, 1.7000000476837158, 0.6000000238418579]
acoustic_panel_F[0].rotation = [0, 0, -1.95032346724951e-06]
acoustic_panel_F[0].optimize = 2
storage_cabinet_B[0].position = [4.508372783660889, 1.7500029802322388, 0.8999999761581421]
storage_cabinet_B[0].rotation = [0, 0, -1.5719299179918247]
storage_cabinet_B[0].optimize = 2
acoustic_panel_D[0].position = [7.974999904632568, 5.5, 0.6000000238418579]
acoustic_panel_D[0].rotation = [0, 0, 3.1415907036924335]
acoustic_panel_D[0].optimize = 2

