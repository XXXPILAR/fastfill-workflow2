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
    Wall(corner1=[8.00, 0.00, 0.00], corner2=[8.00, 6.00, 0.00]),
    Wall(corner1=[8.00, 6.00, 0.00], corner2=[4.00, 6.00, 0.00]),
    Wall(corner1=[4.00, 6.00, 0.00], corner2=[4.00, 5.00, 0.00]),
    Wall(corner1=[4.00, 5.00, 0.00], corner2=[0.00, 5.00, 0.00]),
    Wall(corner1=[0.00, 5.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
tall_bookshelf_A = Assets(description="It is a tall set of shelves made of wood and metal.", size=[0.35, 0.90, 2.10], placements=[AssetInstance() for _ in range(1)])
lounge_armchair_A = Assets(description="A white armchair with a quilted upholstered pattern.", size=[0.88, 0.85, 0.90], placements=[AssetInstance() for _ in range(1)])
file_stack_A = Assets(description="A purple and blue book.", size=[0.30, 0.23, 0.06], placements=[AssetInstance() for _ in range(1)])
decorative_tray = Assets(description="Carved brown tray with handle and tall sides.", size=[0.28, 0.40, 0.10], placements=[AssetInstance() for _ in range(1)])
round_side_table_A = Assets(description="A round side table made of wood that has a thick surface, and a metal stand below it.", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
framed_certificate = Assets(description="A paper degree in a wooden frame.", size=[0.08, 0.32, 0.25], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="A brown book with silver corners.", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
remote_control = Assets(description="A black television remote control with the regular buttons and a four-directional grey button pad, with the words not for home use written on the back.", size=[0.20, 0.05, 0.03], placements=[AssetInstance() for _ in range(1)])
coat_stand = Assets(description="The coatrack is wooden with a round bottom.", size=[0.50, 0.50, 1.80], placements=[AssetInstance() for _ in range(1)])
tall_bookshelf_B = Assets(description="It is a tall set of shelves made of wood and metal.", size=[0.35, 0.90, 2.10], placements=[AssetInstance() for _ in range(1)])
coffee_table_lounge = Assets(description="coffee table lounge", size=[0.80, 1.40, 0.42], placements=[AssetInstance() for _ in range(1)])
lounge_sofa = Assets(description="Light gray fabric sofa with six cushions.", size=[0.95, 2.20, 0.85], placements=[AssetInstance() for _ in range(1)])
sideboard_credenza = Assets(description="A black cabinet with grey doors.", size=[0.45, 1.60, 0.80], placements=[AssetInstance() for _ in range(1)])
waste_bin_A = Assets(description="A small cylindrical gray trash can with a black step opener and a large black hinge on top.", size=[0.30, 0.25, 0.35], placements=[AssetInstance() for _ in range(1)])
magazine_A = Assets(description="a notebook with stickers and a Pokémon drawing on it.", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
lounge_armchair_B = Assets(description="A white armchair with a quilted upholstered pattern.", size=[0.88, 0.85, 0.90], placements=[AssetInstance() for _ in range(1)])
waste_bin_B = Assets(description="A small cylindrical gray trash can with a black step opener and a large black hinge on top.", size=[0.30, 0.25, 0.35], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="A leather hardback book with a black band and lock around it.", size=[0.25, 0.18, 0.05], placements=[AssetInstance() for _ in range(1)])
hardcover_book = Assets(description="Hardcover book with blue and silver cover.", size=[0.25, 0.18, 0.04], placements=[AssetInstance() for _ in range(1)])
executive_desk = Assets(description="A dark brown desk.", size=[0.85, 1.80, 0.75], placements=[AssetInstance() for _ in range(1)])
ceramic_mug_A = Assets(description="A black ceramic mug with its inside painted yellow.", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
small_vase_A = Assets(description="a white vase", size=[0.10, 0.10, 0.18], placements=[AssetInstance() for _ in range(1)])
printer_stand = Assets(description="A square wooden table with two shelves.", size=[0.60, 0.60, 0.72], placements=[AssetInstance() for _ in range(1)])
notepad = Assets(description="A red notepad decorated with a slug in the lower corner.", size=[0.21, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
floor_lamp_A = Assets(description="A floor lamp with a black base and white lampshade.", size=[0.40, 0.40, 1.60], placements=[AssetInstance() for _ in range(1)])
pedestal_cabinet_A = Assets(description="A wooden cabinet that has four drawers on it.", size=[0.55, 0.45, 0.68], placements=[AssetInstance() for _ in range(1)])
office_printer = Assets(description="A square black and metal coffee maker with a red lever.", size=[0.36, 0.28, 0.38], placements=[AssetInstance() for _ in range(1)])
guest_chair_A = Assets(description="guest chair", size=[0.58, 0.55, 0.82], placements=[AssetInstance() for _ in range(1)])
small_vase_B = Assets(description="a white vase", size=[0.10, 0.10, 0.18], placements=[AssetInstance() for _ in range(1)])
console_table = Assets(description="a small wooden console table with a Japanese Torii gate design.", size=[0.35, 1.10, 0.80], placements=[AssetInstance() for _ in range(1)])
guest_chair_B = Assets(description="guest chair", size=[0.58, 0.55, 0.82], placements=[AssetInstance() for _ in range(1)])
desk_organizer = Assets(description="A wooden crate with compartments that is used to hold things.", size=[0.20, 0.30, 0.12], placements=[AssetInstance() for _ in range(1)])
magazine_B = Assets(description="A red and blue hardback book titled 'akbar's dream'.", size=[0.28, 0.22, 0.02], placements=[AssetInstance() for _ in range(1)])
file_stack_B = Assets(description="a colorful stack of blocks with various creatures, such as a frog, bird, and green monster, sitting on top.", size=[0.20, 0.28, 0.22], placements=[AssetInstance() for _ in range(1)])
guest_chair_C = Assets(description="guest chair", size=[0.58, 0.55, 0.82], placements=[AssetInstance() for _ in range(1)])
picture_frame = Assets(description="A black and white painting of a robed person standing in a raft.", size=[0.10, 0.40, 0.50], placements=[AssetInstance() for _ in range(1)])
floor_lamp_B = Assets(description="A floor lamp with a black base and white lampshade.", size=[0.40, 0.40, 1.60], placements=[AssetInstance() for _ in range(1)])
pedestal_cabinet_B = Assets(description="A wooden cabinet that has four drawers on it.", size=[0.55, 0.45, 0.68], placements=[AssetInstance() for _ in range(1)])
round_side_table_B = Assets(description="A round side table made of wood that has a thick surface, and a metal stand below it.", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
guest_chair_D = Assets(description="guest chair", size=[0.58, 0.55, 0.82], placements=[AssetInstance() for _ in range(1)])
meeting_chair = Assets(description="A black chair with a fabric seat on a black metal frame.", size=[0.55, 0.50, 0.82], placements=[AssetInstance() for _ in range(1)])
magazine_C = Assets(description="A box for an atari game.", size=[0.19, 0.14, 0.03], placements=[AssetInstance() for _ in range(1)])
round_meeting_table = Assets(description="A wooden round kitchen table.", size=[1.10, 1.10, 0.75], placements=[AssetInstance() for _ in range(1)])
ceramic_mug_B = Assets(description="White coffee mug model", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
manager_task_chair = Assets(description="A all white office chair with a dark black  backing.", size=[0.68, 0.68, 1.15], placements=[AssetInstance() for _ in range(1)])

tall_bookshelf_A[0].instance_id = 'tall_bookshelf_A_0'
lounge_armchair_A[0].instance_id = 'lounge_armchair_A_0'
file_stack_A[0].instance_id = 'file_stack_A_0'
decorative_tray[0].instance_id = 'decorative_tray_0'
round_side_table_A[0].instance_id = 'round_side_table_A_0'
framed_certificate[0].instance_id = 'framed_certificate_0'
book_A[0].instance_id = 'book_A_0'
remote_control[0].instance_id = 'remote_control_0'
coat_stand[0].instance_id = 'coat_stand_0'
tall_bookshelf_B[0].instance_id = 'tall_bookshelf_B_0'
coffee_table_lounge[0].instance_id = 'coffee_table_lounge_0'
lounge_sofa[0].instance_id = 'lounge_sofa_0'
sideboard_credenza[0].instance_id = 'sideboard_credenza_0'
waste_bin_A[0].instance_id = 'waste_bin_A_0'
magazine_A[0].instance_id = 'magazine_A_0'
lounge_armchair_B[0].instance_id = 'lounge_armchair_B_0'
waste_bin_B[0].instance_id = 'waste_bin_B_0'
book_B[0].instance_id = 'book_B_0'
hardcover_book[0].instance_id = 'hardcover_book_0'
executive_desk[0].instance_id = 'executive_desk_0'
ceramic_mug_A[0].instance_id = 'ceramic_mug_A_0'
small_vase_A[0].instance_id = 'small_vase_A_0'
printer_stand[0].instance_id = 'printer_stand_0'
notepad[0].instance_id = 'notepad_0'
floor_lamp_A[0].instance_id = 'floor_lamp_A_0'
pedestal_cabinet_A[0].instance_id = 'pedestal_cabinet_A_0'
office_printer[0].instance_id = 'office_printer_0'
guest_chair_A[0].instance_id = 'guest_chair_A_0'
small_vase_B[0].instance_id = 'small_vase_B_0'
console_table[0].instance_id = 'console_table_0'
guest_chair_B[0].instance_id = 'guest_chair_B_0'
desk_organizer[0].instance_id = 'desk_organizer_0'
magazine_B[0].instance_id = 'magazine_B_0'
file_stack_B[0].instance_id = 'file_stack_B_0'
guest_chair_C[0].instance_id = 'guest_chair_C_0'
picture_frame[0].instance_id = 'picture_frame_0'
floor_lamp_B[0].instance_id = 'floor_lamp_B_0'
pedestal_cabinet_B[0].instance_id = 'pedestal_cabinet_B_0'
round_side_table_B[0].instance_id = 'round_side_table_B_0'
guest_chair_D[0].instance_id = 'guest_chair_D_0'
meeting_chair[0].instance_id = 'meeting_chair_0'
magazine_C[0].instance_id = 'magazine_C_0'
round_meeting_table[0].instance_id = 'round_meeting_table_0'
ceramic_mug_B[0].instance_id = 'ceramic_mug_B_0'
manager_task_chair[0].instance_id = 'manager_task_chair_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

tall_bookshelf_A[0].position = [5.310388739508032, 0.9747055284377775, 1.05]
tall_bookshelf_A[0].rotation = [0, 0, 0]
lounge_armchair_A[0].position = [6.430396007460043, 0.4437059305283315, 0.45]
lounge_armchair_A[0].rotation = [0, 0, 0]
file_stack_A[0].position = [0.8639405158186726, 1.7371371809608953, 0.03]
file_stack_A[0].rotation = [0, 0, 0]
decorative_tray[0].position = [6.300718700497422, 5.432881589650267, 0.05]
decorative_tray[0].rotation = [0, 0, 0]
round_side_table_A[0].position = [7.886512035189928, 1.4187393548757126, 0.275]
round_side_table_A[0].rotation = [0, 0, 0]
framed_certificate[0].position = [0.529535044698056, 2.772057960540929, 0.125]
framed_certificate[0].rotation = [0, 0, 0]
book_A[0].position = [6.139399795099511, 3.5235926325597524, 0.02]
book_A[0].rotation = [0, 0, 0]
remote_control[0].position = [5.597197269704228, 4.506348781357935, 0.0125]
remote_control[0].rotation = [0, 0, 0]
coat_stand[0].position = [3.732463488487947, 3.94343757912357, 0.9]
coat_stand[0].rotation = [0, 0, 0]
tall_bookshelf_B[0].position = [1.2089885921118686, 3.8787174050131803, 1.05]
tall_bookshelf_B[0].rotation = [0, 0, 0]
coffee_table_lounge[0].position = [7.346562826939074, 0.9577266399040931, 0.21]
coffee_table_lounge[0].rotation = [0, 0, 0]
lounge_sofa[0].position = [7.293940632190438, 1.2228941394075459, 0.425]
lounge_sofa[0].rotation = [0, 0, 0]
sideboard_credenza[0].position = [0.588360254993896, 3.725690875351096, 0.4]
sideboard_credenza[0].rotation = [0, 0, 0]
waste_bin_A[0].position = [5.380900864298125, 3.8170978337139685, 0.175]
waste_bin_A[0].rotation = [0, 0, 0]
magazine_A[0].position = [7.705812866484478, 5.07220908608234, 0.0075]
magazine_A[0].rotation = [0, 0, 0]
lounge_armchair_B[0].position = [7.991442804134858, 5.737312186154423, 0.45]
lounge_armchair_B[0].rotation = [0, 0, 0]
waste_bin_B[0].position = [5.27715539482367, 2.052742427555233, 0.175]
waste_bin_B[0].rotation = [0, 0, 0]
book_B[0].position = [1.2183100558339781, 0.46218639972987297, 0.025]
book_B[0].rotation = [0, 0, 0]
hardcover_book[0].position = [3.2200301278699897, 4.596924509167761, 0.0175]
hardcover_book[0].rotation = [0, 0, 0]
executive_desk[0].position = [2.3666973671645417, 0.1834540359639072, 0.375]
executive_desk[0].rotation = [0, 0, 0]
ceramic_mug_A[0].position = [0.3919024534827704, 4.614314222891704, 0.05]
ceramic_mug_A[0].rotation = [0, 0, 0]
small_vase_A[0].position = [1.4325921027120785, 4.79600737772966, 0.09]
small_vase_A[0].rotation = [0, 0, 0]
printer_stand[0].position = [3.4477407283030903, 1.3569234172879818, 0.36]
printer_stand[0].rotation = [0, 0, 0]
notepad[0].position = [7.107572452764426, 1.6285716085050561, 0.0075]
notepad[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [0.11996477570568409, 2.6732343413530737, 0.8]
floor_lamp_A[0].rotation = [0, 0, 0]
pedestal_cabinet_A[0].position = [6.045248396039609, 5.782656693326458, 0.34]
pedestal_cabinet_A[0].rotation = [0, 0, 0]
office_printer[0].position = [7.6960043759780925, 5.072601133312397, 0.19]
office_printer[0].rotation = [0, 0, 0]
guest_chair_A[0].position = [0.908325398178242, 3.242030080428736, 0.41]
guest_chair_A[0].rotation = [0, 0, 0]
small_vase_B[0].position = [4.113246146505423, 3.5128000443663674, 0.09]
small_vase_B[0].rotation = [0, 0, 0]
console_table[0].position = [5.416278748966342, 1.2023898023052835, 0.4]
console_table[0].rotation = [0, 0, 0]
guest_chair_B[0].position = [4.245091447551928, 3.539590134611517, 0.41]
guest_chair_B[0].rotation = [0, 0, 0]
desk_organizer[0].position = [4.328736080962054, 4.053965090883022, 0.06]
desk_organizer[0].rotation = [0, 0, 0]
magazine_B[0].position = [4.667132539171692, 4.253729066513283, 0.01]
magazine_B[0].rotation = [0, 0, 0]
file_stack_B[0].position = [6.304774674831984, 3.5796152841249698, 0.11]
file_stack_B[0].rotation = [0, 0, 0]
guest_chair_C[0].position = [1.4863403720189678, 4.6719564186437355, 0.41]
guest_chair_C[0].rotation = [0, 0, 0]
picture_frame[0].position = [3.0022761583953548, 3.55287778994642, 0.25]
picture_frame[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [3.9030277001715143, 1.551217596594875, 0.8]
floor_lamp_B[0].rotation = [0, 0, 0]
pedestal_cabinet_B[0].position = [5.503940385956575, 1.9061512906873885, 0.34]
pedestal_cabinet_B[0].rotation = [0, 0, 0]
round_side_table_B[0].position = [1.0434027099448553, 2.429964993434349, 0.275]
round_side_table_B[0].rotation = [0, 0, 0]
guest_chair_D[0].position = [0.2011641060668552, 0.8508619684764605, 0.41]
guest_chair_D[0].rotation = [0, 0, 0]
meeting_chair[0].position = [7.649354618447777, 4.756004612361634, 0.41]
meeting_chair[0].rotation = [0, 0, 0]
magazine_C[0].position = [4.153931699967542, 1.3393713047363998, 0.015]
magazine_C[0].rotation = [0, 0, 0]
round_meeting_table[0].position = [4.2934213429247015, 1.4178763687730058, 0.375]
round_meeting_table[0].rotation = [0, 0, 0]
ceramic_mug_B[0].position = [5.660053275966397, 0.21783416030100589, 0.05]
ceramic_mug_B[0].rotation = [0, 0, 0]
manager_task_chair[0].position = [4.853556642504372, 4.949399312281197, 0.575]
manager_task_chair[0].rotation = [0, 0, 0]
tall_bookshelf_A[0].position = [5.310388739508032, 0.9747055284377775, 1.05]
tall_bookshelf_A[0].rotation = [0, 0, 0]
lounge_armchair_A[0].position = [6.430396007460043, 0.4437059305283315, 0.45]
lounge_armchair_A[0].rotation = [0, 0, 0]
file_stack_A[0].position = [0.8639405158186726, 1.7371371809608953, 0.03]
file_stack_A[0].rotation = [0, 0, 0]
decorative_tray[0].position = [6.300718700497422, 5.432881589650267, 0.05]
decorative_tray[0].rotation = [0, 0, 0]
round_side_table_A[0].position = [7.886512035189928, 1.4187393548757126, 0.275]
round_side_table_A[0].rotation = [0, 0, 0]
framed_certificate[0].position = [0.529535044698056, 2.772057960540929, 0.125]
framed_certificate[0].rotation = [0, 0, 0]
book_A[0].position = [6.139399795099511, 3.5235926325597524, 0.02]
book_A[0].rotation = [0, 0, 0]
remote_control[0].position = [5.597197269704228, 4.506348781357935, 0.0125]
remote_control[0].rotation = [0, 0, 0]
coat_stand[0].position = [3.732463488487947, 3.94343757912357, 0.9]
coat_stand[0].rotation = [0, 0, 0]
tall_bookshelf_B[0].position = [1.2089885921118686, 3.8787174050131803, 1.05]
tall_bookshelf_B[0].rotation = [0, 0, 0]
coffee_table_lounge[0].position = [7.346562826939074, 0.9577266399040931, 0.21]
coffee_table_lounge[0].rotation = [0, 0, 0]
lounge_sofa[0].position = [7.293940632190438, 1.2228941394075459, 0.425]
lounge_sofa[0].rotation = [0, 0, 0]
sideboard_credenza[0].position = [0.588360254993896, 3.725690875351096, 0.4]
sideboard_credenza[0].rotation = [0, 0, 0]
waste_bin_A[0].position = [5.380900864298125, 3.8170978337139685, 0.175]
waste_bin_A[0].rotation = [0, 0, 0]
magazine_A[0].position = [7.705812866484478, 5.07220908608234, 0.0075]
magazine_A[0].rotation = [0, 0, 0]
lounge_armchair_B[0].position = [7.991442804134858, 5.737312186154423, 0.45]
lounge_armchair_B[0].rotation = [0, 0, 0]
waste_bin_B[0].position = [5.27715539482367, 2.052742427555233, 0.175]
waste_bin_B[0].rotation = [0, 0, 0]
book_B[0].position = [1.2183100558339781, 0.46218639972987297, 0.025]
book_B[0].rotation = [0, 0, 0]
hardcover_book[0].position = [3.2200301278699897, 4.596924509167761, 0.0175]
hardcover_book[0].rotation = [0, 0, 0]
executive_desk[0].position = [2.3666973671645417, 0.1834540359639072, 0.375]
executive_desk[0].rotation = [0, 0, 0]
ceramic_mug_A[0].position = [0.3919024534827704, 4.614314222891704, 0.05]
ceramic_mug_A[0].rotation = [0, 0, 0]
small_vase_A[0].position = [1.4325921027120785, 4.79600737772966, 0.09]
small_vase_A[0].rotation = [0, 0, 0]
printer_stand[0].position = [3.4477407283030903, 1.3569234172879818, 0.36]
printer_stand[0].rotation = [0, 0, 0]
notepad[0].position = [7.107572452764426, 1.6285716085050561, 0.0075]
notepad[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [0.11996477570568409, 2.6732343413530737, 0.8]
floor_lamp_A[0].rotation = [0, 0, 0]
pedestal_cabinet_A[0].position = [6.045248396039609, 5.782656693326458, 0.34]
pedestal_cabinet_A[0].rotation = [0, 0, 0]
office_printer[0].position = [7.6960043759780925, 5.072601133312397, 0.19]
office_printer[0].rotation = [0, 0, 0]
guest_chair_A[0].position = [0.908325398178242, 3.242030080428736, 0.41]
guest_chair_A[0].rotation = [0, 0, 0]
small_vase_B[0].position = [4.113246146505423, 3.5128000443663674, 0.09]
small_vase_B[0].rotation = [0, 0, 0]
console_table[0].position = [5.416278748966342, 1.2023898023052835, 0.4]
console_table[0].rotation = [0, 0, 0]
guest_chair_B[0].position = [4.245091447551928, 3.539590134611517, 0.41]
guest_chair_B[0].rotation = [0, 0, 0]
desk_organizer[0].position = [4.328736080962054, 4.053965090883022, 0.06]
desk_organizer[0].rotation = [0, 0, 0]
magazine_B[0].position = [4.667132539171692, 4.253729066513283, 0.01]
magazine_B[0].rotation = [0, 0, 0]
file_stack_B[0].position = [6.304774674831984, 3.5796152841249698, 0.11]
file_stack_B[0].rotation = [0, 0, 0]
guest_chair_C[0].position = [1.4863403720189678, 4.6719564186437355, 0.41]
guest_chair_C[0].rotation = [0, 0, 0]
picture_frame[0].position = [3.0022761583953548, 3.55287778994642, 0.25]
picture_frame[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [3.9030277001715143, 1.551217596594875, 0.8]
floor_lamp_B[0].rotation = [0, 0, 0]
pedestal_cabinet_B[0].position = [5.503940385956575, 1.9061512906873885, 0.34]
pedestal_cabinet_B[0].rotation = [0, 0, 0]
round_side_table_B[0].position = [1.0434027099448553, 2.429964993434349, 0.275]
round_side_table_B[0].rotation = [0, 0, 0]
guest_chair_D[0].position = [0.2011641060668552, 0.8508619684764605, 0.41]
guest_chair_D[0].rotation = [0, 0, 0]
meeting_chair[0].position = [7.649354618447777, 4.756004612361634, 0.41]
meeting_chair[0].rotation = [0, 0, 0]
magazine_C[0].position = [4.153931699967542, 1.3393713047363998, 0.015]
magazine_C[0].rotation = [0, 0, 0]
round_meeting_table[0].position = [4.2934213429247015, 1.4178763687730058, 0.375]
round_meeting_table[0].rotation = [0, 0, 0]
ceramic_mug_B[0].position = [5.660053275966397, 0.21783416030100589, 0.05]
ceramic_mug_B[0].rotation = [0, 0, 0]
manager_task_chair[0].position = [4.853556642504372, 4.949399312281197, 0.575]
manager_task_chair[0].rotation = [0, 0, 0]

solver.constraints = []

# Three functional zones: office at lower left, meeting area at lower right,
# and lounge at upper right. The west doorway and its approach remain clear.
# Coordinates below are bounding-box centers; headings are in degrees.
floor_layout = [
    (tall_bookshelf_A,     2.00, 4.825, 270),
    (tall_bookshelf_B,     3.15, 4.825, 270),
    (executive_desk,       1.65, 1.70,    0),
    (manager_task_chair,   0.65, 1.70,    0),
    (guest_chair_A,        2.65, 1.20,  180),
    (guest_chair_B,        2.65, 2.15,  180),
    (pedestal_cabinet_A,   1.45, 0.40,   90),
    (pedestal_cabinet_B,   2.15, 0.40,   90),
    (printer_stand,        3.10, 0.40,   90),
    (console_table,        0.175, 0.65,   0),
    (coat_stand,           0.40, 2.40,    0),
    (waste_bin_A,          2.65, 2.85,  180),
    (waste_bin_B,          3.50, 0.90,   90),
    (sideboard_credenza,   4.45, 0.225,  90),
    (round_meeting_table,  6.10, 1.35,    0),
    (guest_chair_C,        5.15, 1.35,    0),
    (guest_chair_D,        7.05, 1.35,  180),
    (meeting_chair,        6.10, 0.40,   90),
    (lounge_sofa,          7.40, 4.30,  180),
    (coffee_table_lounge,  5.80, 4.30,    0),
    (lounge_armchair_A,    4.65, 3.65,    0),
    (lounge_armchair_B,    4.65, 4.85,    0),
    (floor_lamp_A,         5.80, 3.20,   90),
    (floor_lamp_B,         5.80, 5.40,  270),
    (round_side_table_A,   6.80, 2.75,    0),
    (round_side_table_B,   6.80, 5.72,    0),
]

# High-priority location anchors preserve the circulation routes and prevent
# the seating groups from drifting into one another during adjustment.
for item, px, py, heading in floor_layout:
    item[0].position = [px, py, item.size[2] / 2]
    item[0].rotation = [0, 0, radians(heading)]
    solver.distance_constraint(
        item[0], AssetInstance(position=list(item[0].position)),
        0, 0, weight=10
    )
    solver.align_with(
        item[0], AssetInstance(rotation=[0, 0, radians(heading)])
    )

# Peripheral storage is flush to solid walls, away from the east windows.
solver.against_wall(tall_bookshelf_A[0], walls[4])
solver.against_wall(tall_bookshelf_B[0], walls[4])
solver.against_wall(console_table[0], walls[5])
solver.against_wall(sideboard_credenza[0], walls[0])

# Preserve useful seating relationships and access to the desk.
solver.point_towards(manager_task_chair[0], executive_desk[0])
solver.point_towards(guest_chair_A[0], executive_desk[0])
solver.point_towards(guest_chair_B[0], executive_desk[0])
solver.distance_constraint(manager_task_chair[0], executive_desk[0], 0.95, 1.10)
solver.distance_constraint(guest_chair_A[0], executive_desk[0], 1.05, 1.20)
solver.distance_constraint(guest_chair_B[0], executive_desk[0], 1.05, 1.20)

for seat in (guest_chair_C, guest_chair_D, meeting_chair):
    solver.point_towards(seat[0], round_meeting_table[0])
    solver.distance_constraint(seat[0], round_meeting_table[0], 0.95, 1.05)

solver.point_towards(lounge_sofa[0], coffee_table_lounge[0])
solver.distance_constraint(lounge_sofa[0], coffee_table_lounge[0], 1.55, 1.70)
for seat in (lounge_armchair_A, lounge_armchair_B):
    solver.distance_constraint(seat[0], coffee_table_lounge[0], 1.25, 1.40)

# The two lamps bracket the coffee table on its north-south centerline.
# Their fixed headings and anchored positions preserve the between relationship.
solver.point_towards(floor_lamp_A[0], coffee_table_lounge[0])
solver.point_towards(floor_lamp_B[0], coffee_table_lounge[0])
solver.distance_constraint(floor_lamp_A[0], coffee_table_lounge[0], 1.10, 1.10)
solver.distance_constraint(floor_lamp_B[0], coffee_table_lounge[0], 1.10, 1.10)
solver.distance_constraint(coffee_table_lounge[0], floor_lamp_A[0], 1.10, 1.10)
solver.distance_constraint(coffee_table_lounge[0], floor_lamp_B[0], 1.10, 1.10)

# Small objects are distributed across usable surfaces with separate footprints.
# Each tuple supplies its actual supporting asset, absolute horizontal location,
# and heading. Both mugs are supported; ceramic_mug_B is the requested o0043.
surface_layout = [
    (file_stack_A,      pedestal_cabinet_A, 1.45, 0.40,  0),
    (file_stack_B,      pedestal_cabinet_B, 2.15, 0.40,  0),
    (office_printer,    printer_stand,      3.10, 0.40, 90),
    (framed_certificate, console_table,    0.175, 0.38, 0),
    (small_vase_B,      console_table,      0.175, 0.94, 0),
    (picture_frame,     sideboard_credenza, 4.00, 0.225, 90),
    (hardcover_book,    sideboard_credenza, 4.55, 0.225, 90),
    (book_B,            sideboard_credenza, 4.95, 0.225, 90),
    (desk_organizer,    executive_desk,     1.48, 2.32,  0),
    (notepad,           executive_desk,     1.70, 1.72,  0),
    (ceramic_mug_A,     executive_desk,     1.78, 1.12,  0),
    (book_A,            executive_desk,     1.48, 1.35,  0),
    (decorative_tray,   coffee_table_lounge, 5.80, 4.02, 0),
    (ceramic_mug_B,     coffee_table_lounge, 5.98, 4.52, 0),
    (remote_control,    coffee_table_lounge, 5.68, 4.55, 90),
    (magazine_A,        coffee_table_lounge, 5.80, 4.78, 0),
    (small_vase_A,      round_side_table_B, 6.80, 5.72, 0),
    (magazine_B,        round_side_table_A, 6.80, 2.75, 0),
    (magazine_C,        round_meeting_table, 6.10, 1.35, 0),
]

for item, support, px, py, heading in surface_layout:
    pz = support[0].position[2] + support.size[2] / 2 + item.size[2] / 2
    item[0].position = [px, py, pz]
    item[0].rotation = [0, 0, radians(heading)]

    # Support comes first so these items cannot be moved down onto the floor.
    solver.on_top_of(item[0], support[0])
    solver.distance_constraint(
        item[0], AssetInstance(position=[px, py, pz]),
        0, 0, weight=10
    )
    solver.align_with(
        item[0], AssetInstance(rotation=[0, 0, radians(heading)])
    )

solver.constraints = []
ceramic_mug_A[0].position = [1.7799999713897705, 1.1200000047683716, 0.800000011920929]
ceramic_mug_A[0].rotation = [0, 0, 0.01256637125682779]
ceramic_mug_A[0].optimize = 2
executive_desk[0].position = [1.649999976158142, 1.7000000476837158, 0.375]
executive_desk[0].rotation = [0, 0, 0.04084070568744688]
executive_desk[0].optimize = 2
small_vase_B[0].position = [0.17499999701976776, 0.9399999976158142, 0.8899999856948853]
small_vase_B[0].rotation = [0, 0, 0.01256637125682779]
small_vase_B[0].optimize = 2
waste_bin_B[0].position = [3.5, 0.8999999761581421, 0.17499999701976776]
waste_bin_B[0].rotation = [0, 0, 1.5802211042556205]
waste_bin_B[0].optimize = 2
floor_lamp_B[0].position = [5.800000190734863, 5.458001136779785, 0.800000011920929]
floor_lamp_B[0].rotation = [0, 0, -1.5519467713960802]
floor_lamp_B[0].optimize = 2
decorative_tray[0].position = [5.800000190734863, 4.019999980926514, 0.4699999988079071]
decorative_tray[0].rotation = [0, 0, 0.01256637125682779]
decorative_tray[0].optimize = 2
desk_organizer[0].position = [1.4800000190734863, 2.319999933242798, 0.8100000023841858]
desk_organizer[0].rotation = [0, 0, 0.01256637125682779]
desk_organizer[0].optimize = 2
hardcover_book[0].position = [4.550000190734863, 0.22499999403953552, 0.8199999928474426]
hardcover_book[0].rotation = [0, 0, 1.5833626980517244]
hardcover_book[0].optimize = 2
round_side_table_B[0].position = [6.800000190734863, 5.71999979019165, 0.2750000059604645]
round_side_table_B[0].rotation = [0, 0, 0.01256637125682779]
round_side_table_B[0].optimize = 2
picture_frame[0].position = [4.0, 0.22499999403953552, 1.0499999523162842]
picture_frame[0].rotation = [0, 0, 1.5833626980517244]
picture_frame[0].optimize = 2
office_printer[0].position = [3.0999999046325684, 0.4000000059604645, 0.9100000262260437]
office_printer[0].rotation = [0, 0, 1.5833626980517244]
office_printer[0].optimize = 2
pedestal_cabinet_B[0].position = [2.1500000953674316, 0.4000000059604645, 0.3400000035762787]
pedestal_cabinet_B[0].rotation = [0, 0, 1.5833626980517244]
pedestal_cabinet_B[0].optimize = 2
magazine_C[0].position = [6.099999904632568, 1.350000023841858, 0.7649999856948853]
magazine_C[0].rotation = [0, 0, 0.01256637125682779]
magazine_C[0].optimize = 2
console_table[0].position = [0.1750686913728714, 0.6499999761581421, 0.4000000059604645]
console_table[0].rotation = [0, 0, -0.00010957445351386098]
console_table[0].optimize = 2
meeting_chair[0].position = [6.099999904632568, 0.4000000059604645, 0.4099999964237213]
meeting_chair[0].rotation = [0, 0, 1.586504290712113]
meeting_chair[0].optimize = 2
remote_control[0].position = [5.679999828338623, 4.550000190734863, 0.4349999725818634]
remote_control[0].rotation = [0, 0, 1.5833626980517244]
remote_control[0].optimize = 2
tall_bookshelf_A[0].position = [2.0, 4.824922561645508, 1.0499999523162842]
tall_bookshelf_A[0].rotation = [0, 0, -1.5708578074663848]
tall_bookshelf_A[0].optimize = 2
book_A[0].position = [1.4800000190734863, 1.350000023841858, 0.7699999809265137]
book_A[0].rotation = [0, 0, 0.01256637125682779]
book_A[0].optimize = 2
floor_lamp_A[0].position = [5.800000190734863, 3.1239452362060547, 0.800000011920929]
floor_lamp_A[0].rotation = [0, 0, 1.589645882193713]
floor_lamp_A[0].optimize = 2
ceramic_mug_B[0].position = [5.980000019073486, 4.519999980926514, 0.4699999988079071]
ceramic_mug_B[0].rotation = [0, 0, 0.01256637125682779]
ceramic_mug_B[0].optimize = 2
notepad[0].position = [1.7000000476837158, 1.7200000286102295, 0.7549999952316284]
notepad[0].rotation = [0, 0, 0.01256637125682779]
notepad[0].optimize = 2
guest_chair_B[0].position = [2.6500000953674316, 2.1500000953674316, 0.4099999964237213]
guest_chair_B[0].rotation = [0, 0, -3.125884689672577]
guest_chair_B[0].optimize = 2
file_stack_B[0].position = [2.1500000953674316, 0.4000000059604645, 0.7900000214576721]
file_stack_B[0].rotation = [0, 0, 0.01256637125682779]
file_stack_B[0].optimize = 2
manager_task_chair[0].position = [0.6499999761581421, 1.7000000476837158, 0.574999988079071]
manager_task_chair[0].rotation = [0, 0, 0.0157079639172164]
manager_task_chair[0].optimize = 2
round_meeting_table[0].position = [6.099999904632568, 1.350000023841858, 0.375]
round_meeting_table[0].rotation = [0, 0, 0.031415925765816845]
round_meeting_table[0].optimize = 2
coffee_table_lounge[0].position = [5.800000190734863, 4.322556018829346, 0.20999999344348907]
coffee_table_lounge[0].rotation = [0, 0, 0.053407073383009665]
coffee_table_lounge[0].optimize = 2
round_side_table_A[0].position = [6.800000190734863, 2.75, 0.2750000059604645]
round_side_table_A[0].rotation = [0, 0, 0.01256637125682779]
round_side_table_A[0].optimize = 2
printer_stand[0].position = [3.0999999046325684, 0.4000000059604645, 0.36000001430511475]
printer_stand[0].rotation = [0, 0, 1.5833626980517244]
printer_stand[0].optimize = 2
book_B[0].position = [4.949999809265137, 0.22499999403953552, 0.824999988079071]
book_B[0].rotation = [0, 0, 1.5833626980517244]
book_B[0].optimize = 2
lounge_armchair_B[0].position = [4.650000095367432, 4.849999904632568, 0.44999998807907104]
lounge_armchair_B[0].rotation = [0, 0, 0.01256637125682779]
lounge_armchair_B[0].optimize = 2
lounge_armchair_A[0].position = [4.650000095367432, 3.6500000953674316, 0.44999998807907104]
lounge_armchair_A[0].rotation = [0, 0, 0.01256637125682779]
lounge_armchair_A[0].optimize = 2
lounge_sofa[0].position = [7.400000095367432, 4.300000190734863, 0.42500001192092896]
lounge_sofa[0].rotation = [0, 0, -3.125884689672577]
lounge_sofa[0].optimize = 2
guest_chair_D[0].position = [7.050000190734863, 1.350000023841858, 0.4099999964237213]
guest_chair_D[0].rotation = [0, 0, -3.125884689672577]
guest_chair_D[0].optimize = 2
sideboard_credenza[0].position = [4.449999809265137, 0.22486785054206848, 0.4000000059604645]
sideboard_credenza[0].rotation = [0, 0, 1.5705841785446013]
sideboard_credenza[0].optimize = 2
guest_chair_C[0].position = [5.091999053955078, 1.350000023841858, 0.4099999964237213]
guest_chair_C[0].rotation = [0, 0, 0.0157079639172164]
guest_chair_C[0].optimize = 2
waste_bin_A[0].position = [2.6500000953674316, 2.8499999046325684, 0.17499999701976776]
waste_bin_A[0].rotation = [0, 0, -3.1321678761290697]
waste_bin_A[0].optimize = 2
tall_bookshelf_B[0].position = [3.1500000953674316, 4.824922561645508, 1.0499999523162842]
tall_bookshelf_B[0].rotation = [0, 0, -1.5708578074663848]
tall_bookshelf_B[0].optimize = 2
small_vase_A[0].position = [6.800000190734863, 5.71999979019165, 0.6399999856948853]
small_vase_A[0].rotation = [0, 0, 0.01256637125682779]
small_vase_A[0].optimize = 2
pedestal_cabinet_A[0].position = [1.4500000476837158, 0.4000000059604645, 0.3400000035762787]
pedestal_cabinet_A[0].rotation = [0, 0, 1.5833626980517244]
pedestal_cabinet_A[0].optimize = 2
coat_stand[0].position = [0.4000000059604645, 2.4000000953674316, 0.8999999761581421]
coat_stand[0].rotation = [0, 0, 0.00942477746072377]
coat_stand[0].optimize = 2
framed_certificate[0].position = [0.17499999701976776, 0.3799999952316284, 0.925000011920929]
framed_certificate[0].rotation = [0, 0, 0.01256637125682779]
framed_certificate[0].optimize = 2
magazine_A[0].position = [5.800000190734863, 4.78000020980835, 0.42499998211860657]
magazine_A[0].rotation = [0, 0, 0.01256637125682779]
magazine_A[0].optimize = 2
guest_chair_A[0].position = [2.6500000953674316, 1.2000000476837158, 0.4099999964237213]
guest_chair_A[0].rotation = [0, 0, -3.125884689672577]
guest_chair_A[0].optimize = 2
file_stack_A[0].position = [1.4500000476837158, 0.4000000059604645, 0.7099999785423279]
file_stack_A[0].rotation = [0, 0, 0.01256637125682779]
file_stack_A[0].optimize = 2
magazine_B[0].position = [6.800000190734863, 2.75, 0.5600000023841858]
magazine_B[0].rotation = [0, 0, 0.01256637125682779]
magazine_B[0].optimize = 2

