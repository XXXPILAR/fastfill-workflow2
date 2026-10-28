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
tall_bookshelf_A = Assets(description="It is a tall set of shelves made of wood and metal.", size=[0.40, 1.20, 2.20], placements=[AssetInstance() for _ in range(1)])
lounge_armchair_A = Assets(description="A white armchair with a quilted upholstered pattern.", size=[0.90, 0.90, 0.90], placements=[AssetInstance() for _ in range(1)])
file_stack_A = Assets(description="A purple and blue book.", size=[0.22, 0.30, 0.06], placements=[AssetInstance() for _ in range(1)])
decorative_tray = Assets(description="Carved brown tray with handle and tall sides.", size=[0.30, 0.45, 0.12], placements=[AssetInstance() for _ in range(1)])
round_side_table_A = Assets(description="A round side table made of wood that has a thick surface, and a metal stand below it.", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
framed_certificate = Assets(description="A paper degree in a wooden frame.", size=[0.05, 0.42, 0.32], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="A brown book with silver corners.", size=[0.17, 0.24, 0.04], placements=[AssetInstance() for _ in range(1)])
remote_control = Assets(description="A black television remote control with the regular buttons and a four-directional grey button pad, with the words not for home use written on the back.", size=[0.20, 0.05, 0.03], placements=[AssetInstance() for _ in range(1)])
coat_stand = Assets(description="The coatrack is wooden with a round bottom.", size=[0.55, 0.55, 1.80], placements=[AssetInstance() for _ in range(1)])
tall_bookshelf_B = Assets(description="It is a tall set of shelves made of wood and metal.", size=[0.40, 1.20, 2.20], placements=[AssetInstance() for _ in range(1)])
coffee_table_lounge = Assets(description="coffee table lounge", size=[0.70, 1.30, 0.42], placements=[AssetInstance() for _ in range(1)])
lounge_sofa = Assets(description="Light gray fabric sofa with six cushions.", size=[0.95, 2.40, 0.85], placements=[AssetInstance() for _ in range(1)])
sideboard_credenza = Assets(description="A black cabinet with grey doors.", size=[0.45, 1.60, 0.85], placements=[AssetInstance() for _ in range(1)])
waste_bin_A = Assets(description="A small cylindrical gray trash can with a black step opener and a large black hinge on top.", size=[0.34, 0.28, 0.40], placements=[AssetInstance() for _ in range(1)])
magazine_A = Assets(description="a notebook with stickers and a Pokémon drawing on it.", size=[0.21, 0.28, 0.01], placements=[AssetInstance() for _ in range(1)])
lounge_armchair_B = Assets(description="A white armchair with a quilted upholstered pattern.", size=[0.90, 0.90, 0.90], placements=[AssetInstance() for _ in range(1)])
waste_bin_B = Assets(description="A small cylindrical gray trash can with a black step opener and a large black hinge on top.", size=[0.34, 0.28, 0.40], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="A leather hardback book with a black band and lock around it.", size=[0.17, 0.23, 0.05], placements=[AssetInstance() for _ in range(1)])
hardcover_book = Assets(description="Hardcover book with blue and silver cover.", size=[0.18, 0.25, 0.04], placements=[AssetInstance() for _ in range(1)])
executive_desk = Assets(description="A dark brown desk.", size=[0.85, 1.80, 0.76], placements=[AssetInstance() for _ in range(1)])
ceramic_mug_A = Assets(description="A black ceramic mug with its inside painted yellow.", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
small_vase_A = Assets(description="a white vase", size=[0.14, 0.14, 0.25], placements=[AssetInstance() for _ in range(1)])
printer_stand = Assets(description="A square wooden table with two shelves.", size=[0.55, 0.65, 0.75], placements=[AssetInstance() for _ in range(1)])
notepad = Assets(description="A red notepad decorated with a slug in the lower corner.", size=[0.15, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
floor_lamp_A = Assets(description="A floor lamp with a black base and white lampshade.", size=[0.42, 0.42, 1.65], placements=[AssetInstance() for _ in range(1)])
pedestal_cabinet_A = Assets(description="A wooden cabinet that has four drawers on it.", size=[0.55, 0.45, 0.65], placements=[AssetInstance() for _ in range(1)])
office_printer = Assets(description="A square black and metal coffee maker with a red lever.", size=[0.40, 0.45, 0.30], placements=[AssetInstance() for _ in range(1)])
guest_chair_A = Assets(description="guest chair", size=[0.62, 0.58, 0.85], placements=[AssetInstance() for _ in range(1)])
small_vase_B = Assets(description="a white vase", size=[0.14, 0.14, 0.25], placements=[AssetInstance() for _ in range(1)])
console_table = Assets(description="a small wooden console table with a Japanese Torii gate design.", size=[0.38, 1.10, 0.80], placements=[AssetInstance() for _ in range(1)])
guest_chair_B = Assets(description="guest chair", size=[0.62, 0.58, 0.85], placements=[AssetInstance() for _ in range(1)])
desk_organizer = Assets(description="A wooden crate with compartments that is used to hold things.", size=[0.22, 0.35, 0.18], placements=[AssetInstance() for _ in range(1)])
magazine_B = Assets(description="A red and blue hardback book titled 'akbar's dream'.", size=[0.21, 0.28, 0.03], placements=[AssetInstance() for _ in range(1)])
file_stack_B = Assets(description="a colorful stack of blocks with various creatures, such as a frog, bird, and green monster, sitting on top.", size=[0.22, 0.30, 0.18], placements=[AssetInstance() for _ in range(1)])
guest_chair_C = Assets(description="guest chair", size=[0.62, 0.58, 0.85], placements=[AssetInstance() for _ in range(1)])
picture_frame = Assets(description="A black and white painting of a robed person standing in a raft.", size=[0.06, 0.55, 0.70], placements=[AssetInstance() for _ in range(1)])
floor_lamp_B = Assets(description="A floor lamp with a black base and white lampshade.", size=[0.42, 0.42, 1.65], placements=[AssetInstance() for _ in range(1)])
pedestal_cabinet_B = Assets(description="A wooden cabinet that has four drawers on it.", size=[0.55, 0.45, 0.65], placements=[AssetInstance() for _ in range(1)])
round_side_table_B = Assets(description="A round side table made of wood that has a thick surface, and a metal stand below it.", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
guest_chair_D = Assets(description="guest chair", size=[0.62, 0.58, 0.85], placements=[AssetInstance() for _ in range(1)])
meeting_chair = Assets(description="A black chair with a fabric seat on a black metal frame.", size=[0.56, 0.52, 0.82], placements=[AssetInstance() for _ in range(1)])
magazine_C = Assets(description="A box for an atari game.", size=[0.14, 0.19, 0.03], placements=[AssetInstance() for _ in range(1)])
round_meeting_table = Assets(description="A wooden round kitchen table.", size=[1.20, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
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

tall_bookshelf_A[0].position = [4.023468125383422, 5.257393223136271, 1.1]
tall_bookshelf_A[0].rotation = [0, 0, 0]
lounge_armchair_A[0].position = [1.438979047812487, 2.21172769050621, 0.45]
lounge_armchair_A[0].rotation = [0, 0, 0]
file_stack_A[0].position = [3.8434405484450096, 1.4496051854436507, 0.03]
file_stack_A[0].rotation = [0, 0, 0]
decorative_tray[0].position = [2.7637933073941348, 1.8392524915246902, 0.06]
decorative_tray[0].rotation = [0, 0, 0]
round_side_table_A[0].position = [1.6865534469846004, 2.9797492273050925, 0.275]
round_side_table_A[0].rotation = [0, 0, 0]
framed_certificate[0].position = [6.865971762606172, 0.4564302752672802, 0.16]
framed_certificate[0].rotation = [0, 0, 0]
book_A[0].position = [2.796976839828565, 3.324674575331565, 0.02]
book_A[0].rotation = [0, 0, 0]
remote_control[0].position = [6.928953552020667, 5.391181775111459, 0.0125]
remote_control[0].rotation = [0, 0, 0]
coat_stand[0].position = [4.375783308889857, 0.9333793279383167, 0.9]
coat_stand[0].rotation = [0, 0, 0]
tall_bookshelf_B[0].position = [3.263099598948796, 2.8049223685913933, 1.1]
tall_bookshelf_B[0].rotation = [0, 0, 0]
coffee_table_lounge[0].position = [4.480319849124463, 1.5146245011053696, 0.21]
coffee_table_lounge[0].rotation = [0, 0, 0]
lounge_sofa[0].position = [5.3738822450754435, 4.201047534708797, 0.425]
lounge_sofa[0].rotation = [0, 0, 0]
sideboard_credenza[0].position = [1.0937514749820885, 1.7865604356905844, 0.425]
sideboard_credenza[0].rotation = [0, 0, 0]
waste_bin_A[0].position = [0.7633637661412918, 4.974132554671477, 0.2]
waste_bin_A[0].rotation = [0, 0, 0]
magazine_A[0].position = [5.902665953924004, 2.656689533309154, 0.0075]
magazine_A[0].rotation = [0, 0, 0]
lounge_armchair_B[0].position = [4.33285532594181, 1.6920310095247661, 0.45]
lounge_armchair_B[0].rotation = [0, 0, 0]
waste_bin_B[0].position = [0.45610939042727683, 3.033519989836779, 0.2]
waste_bin_B[0].rotation = [0, 0, 0]
book_B[0].position = [7.850583876453556, 4.918246614180637, 0.025]
book_B[0].rotation = [0, 0, 0]
hardcover_book[0].position = [7.411332659991582, 2.494007137222658, 0.02]
hardcover_book[0].rotation = [0, 0, 0]
executive_desk[0].position = [7.202249570034648, 2.3005947704188063, 0.38]
executive_desk[0].rotation = [0, 0, 0]
ceramic_mug_A[0].position = [7.8168268856121506, 0.9127300770473654, 0.05]
ceramic_mug_A[0].rotation = [0, 0, 0]
small_vase_A[0].position = [3.866628888634942, 0.7901529143030568, 0.125]
small_vase_A[0].rotation = [0, 0, 0]
printer_stand[0].position = [1.3576698371759148, 4.848314371732191, 0.375]
printer_stand[0].rotation = [0, 0, 0]
notepad[0].position = [7.060969160625866, 5.813201532968108, 0.0075]
notepad[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [3.3896289540069215, 2.8845632280644735, 0.825]
floor_lamp_A[0].rotation = [0, 0, 0]
pedestal_cabinet_A[0].position = [2.8998305886969398, 1.931773272707757, 0.325]
pedestal_cabinet_A[0].rotation = [0, 0, 0]
office_printer[0].position = [7.2083522721020605, 2.412181910796904, 0.15]
office_printer[0].rotation = [0, 0, 0]
guest_chair_A[0].position = [6.018906803398627, 0.5761228909336937, 0.425]
guest_chair_A[0].rotation = [0, 0, 0]
small_vase_B[0].position = [7.415046665335025, 4.752840124047228, 0.125]
small_vase_B[0].rotation = [0, 0, 0]
console_table[0].position = [7.0275155749816545, 2.2245542772264937, 0.4]
console_table[0].rotation = [0, 0, 0]
guest_chair_B[0].position = [0.05656287495585133, 1.6992040765478926, 0.425]
guest_chair_B[0].rotation = [0, 0, 0]
desk_organizer[0].position = [4.1137313950717385, 0.7654991841806662, 0.09]
desk_organizer[0].rotation = [0, 0, 0]
magazine_B[0].position = [1.9746993559250443, 4.089282075264579, 0.0125]
magazine_B[0].rotation = [0, 0, 0]
file_stack_B[0].position = [6.04428910168702, 3.5882777258524468, 0.09]
file_stack_B[0].rotation = [0, 0, 0]
guest_chair_C[0].position = [7.944848002730161, 3.555236357079381, 0.425]
guest_chair_C[0].rotation = [0, 0, 0]
picture_frame[0].position = [4.250152879489828, 1.081483192638064, 0.35]
picture_frame[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [7.755253845960515, 5.76277419520769, 0.825]
floor_lamp_B[0].rotation = [0, 0, 0]
pedestal_cabinet_B[0].position = [2.029769467065633, 1.7784346945108962, 0.325]
pedestal_cabinet_B[0].rotation = [0, 0, 0]
round_side_table_B[0].position = [5.127904647203225, 0.3950739602092175, 0.275]
round_side_table_B[0].rotation = [0, 0, 0]
guest_chair_D[0].position = [0.3370794334297198, 2.414899158079452, 0.425]
guest_chair_D[0].rotation = [0, 0, 0]
meeting_chair[0].position = [1.4456727378073335, 2.446425251181022, 0.41]
meeting_chair[0].rotation = [0, 0, 0]
magazine_C[0].position = [3.4639284688296, 2.8456371695132887, 0.015]
magazine_C[0].rotation = [0, 0, 0]
round_meeting_table[0].position = [2.6074876535756406, 3.7985335559390805, 0.375]
round_meeting_table[0].rotation = [0, 0, 0]
ceramic_mug_B[0].position = [7.641646876288423, 4.074560732464893, 0.05]
ceramic_mug_B[0].rotation = [0, 0, 0]
manager_task_chair[0].position = [3.411954620649846, 2.4209778494037093, 0.575]
manager_task_chair[0].rotation = [0, 0, 0]
tall_bookshelf_A[0].position = [4.023468125383422, 5.257393223136271, 1.1]
tall_bookshelf_A[0].rotation = [0, 0, 0]
lounge_armchair_A[0].position = [1.438979047812487, 2.21172769050621, 0.45]
lounge_armchair_A[0].rotation = [0, 0, 0]
file_stack_A[0].position = [3.8434405484450096, 1.4496051854436507, 0.03]
file_stack_A[0].rotation = [0, 0, 0]
decorative_tray[0].position = [2.7637933073941348, 1.8392524915246902, 0.06]
decorative_tray[0].rotation = [0, 0, 0]
round_side_table_A[0].position = [1.6865534469846004, 2.9797492273050925, 0.275]
round_side_table_A[0].rotation = [0, 0, 0]
framed_certificate[0].position = [6.865971762606172, 0.4564302752672802, 0.16]
framed_certificate[0].rotation = [0, 0, 0]
book_A[0].position = [2.796976839828565, 3.324674575331565, 0.02]
book_A[0].rotation = [0, 0, 0]
remote_control[0].position = [6.928953552020667, 5.391181775111459, 0.0125]
remote_control[0].rotation = [0, 0, 0]
coat_stand[0].position = [4.375783308889857, 0.9333793279383167, 0.9]
coat_stand[0].rotation = [0, 0, 0]
tall_bookshelf_B[0].position = [3.263099598948796, 2.8049223685913933, 1.1]
tall_bookshelf_B[0].rotation = [0, 0, 0]
coffee_table_lounge[0].position = [4.480319849124463, 1.5146245011053696, 0.21]
coffee_table_lounge[0].rotation = [0, 0, 0]
lounge_sofa[0].position = [5.3738822450754435, 4.201047534708797, 0.425]
lounge_sofa[0].rotation = [0, 0, 0]
sideboard_credenza[0].position = [1.0937514749820885, 1.7865604356905844, 0.425]
sideboard_credenza[0].rotation = [0, 0, 0]
waste_bin_A[0].position = [0.7633637661412918, 4.974132554671477, 0.2]
waste_bin_A[0].rotation = [0, 0, 0]
magazine_A[0].position = [5.902665953924004, 2.656689533309154, 0.0075]
magazine_A[0].rotation = [0, 0, 0]
lounge_armchair_B[0].position = [4.33285532594181, 1.6920310095247661, 0.45]
lounge_armchair_B[0].rotation = [0, 0, 0]
waste_bin_B[0].position = [0.45610939042727683, 3.033519989836779, 0.2]
waste_bin_B[0].rotation = [0, 0, 0]
book_B[0].position = [7.850583876453556, 4.918246614180637, 0.025]
book_B[0].rotation = [0, 0, 0]
hardcover_book[0].position = [7.411332659991582, 2.494007137222658, 0.02]
hardcover_book[0].rotation = [0, 0, 0]
executive_desk[0].position = [7.202249570034648, 2.3005947704188063, 0.38]
executive_desk[0].rotation = [0, 0, 0]
ceramic_mug_A[0].position = [7.8168268856121506, 0.9127300770473654, 0.05]
ceramic_mug_A[0].rotation = [0, 0, 0]
small_vase_A[0].position = [3.866628888634942, 0.7901529143030568, 0.125]
small_vase_A[0].rotation = [0, 0, 0]
printer_stand[0].position = [1.3576698371759148, 4.848314371732191, 0.375]
printer_stand[0].rotation = [0, 0, 0]
notepad[0].position = [7.060969160625866, 5.813201532968108, 0.0075]
notepad[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [3.3896289540069215, 2.8845632280644735, 0.825]
floor_lamp_A[0].rotation = [0, 0, 0]
pedestal_cabinet_A[0].position = [2.8998305886969398, 1.931773272707757, 0.325]
pedestal_cabinet_A[0].rotation = [0, 0, 0]
office_printer[0].position = [7.2083522721020605, 2.412181910796904, 0.15]
office_printer[0].rotation = [0, 0, 0]
guest_chair_A[0].position = [6.018906803398627, 0.5761228909336937, 0.425]
guest_chair_A[0].rotation = [0, 0, 0]
small_vase_B[0].position = [7.415046665335025, 4.752840124047228, 0.125]
small_vase_B[0].rotation = [0, 0, 0]
console_table[0].position = [7.0275155749816545, 2.2245542772264937, 0.4]
console_table[0].rotation = [0, 0, 0]
guest_chair_B[0].position = [0.05656287495585133, 1.6992040765478926, 0.425]
guest_chair_B[0].rotation = [0, 0, 0]
desk_organizer[0].position = [4.1137313950717385, 0.7654991841806662, 0.09]
desk_organizer[0].rotation = [0, 0, 0]
magazine_B[0].position = [1.9746993559250443, 4.089282075264579, 0.0125]
magazine_B[0].rotation = [0, 0, 0]
file_stack_B[0].position = [6.04428910168702, 3.5882777258524468, 0.09]
file_stack_B[0].rotation = [0, 0, 0]
guest_chair_C[0].position = [7.944848002730161, 3.555236357079381, 0.425]
guest_chair_C[0].rotation = [0, 0, 0]
picture_frame[0].position = [4.250152879489828, 1.081483192638064, 0.35]
picture_frame[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [7.755253845960515, 5.76277419520769, 0.825]
floor_lamp_B[0].rotation = [0, 0, 0]
pedestal_cabinet_B[0].position = [2.029769467065633, 1.7784346945108962, 0.325]
pedestal_cabinet_B[0].rotation = [0, 0, 0]
round_side_table_B[0].position = [5.127904647203225, 0.3950739602092175, 0.275]
round_side_table_B[0].rotation = [0, 0, 0]
guest_chair_D[0].position = [0.3370794334297198, 2.414899158079452, 0.425]
guest_chair_D[0].rotation = [0, 0, 0]
meeting_chair[0].position = [1.4456727378073335, 2.446425251181022, 0.41]
meeting_chair[0].rotation = [0, 0, 0]
magazine_C[0].position = [3.4639284688296, 2.8456371695132887, 0.015]
magazine_C[0].rotation = [0, 0, 0]
round_meeting_table[0].position = [2.6074876535756406, 3.7985335559390805, 0.375]
round_meeting_table[0].rotation = [0, 0, 0]
ceramic_mug_B[0].position = [7.641646876288423, 4.074560732464893, 0.05]
ceramic_mug_B[0].rotation = [0, 0, 0]
manager_task_chair[0].position = [3.411954620649846, 2.4209778494037093, 0.575]
manager_task_chair[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed anchors keep the proposed layout stable while the relational constraints
# preserve its semantics if physical-feasibility adjustments are required.
def _layout_anchor(position, rotation_degrees):
    return AssetInstance(
        position=list(position),
        rotation=[0, 0, radians(rotation_degrees)],
    )


def _place_on_floor(asset_collection, position, rotation_degrees):
    instance = asset_collection[0]
    instance.position = list(position)
    instance.rotation = [0, 0, radians(rotation_degrees)]

    anchor = _layout_anchor(position, rotation_degrees)
    solver.distance_constraint(instance, anchor, 0, 0, weight=10)
    solver.align_with(instance, anchor)


def _place_on_surface(asset_collection, support_collection, position,
                      rotation_degrees):
    instance = asset_collection[0]
    instance.position = list(position)
    instance.rotation = [0, 0, radians(rotation_degrees)]

    # The support constraint is specified first so correct vertical placement
    # takes priority over the exact initial anchor.
    solver.on_top_of(instance, support_collection[0])

    anchor = _layout_anchor(position, rotation_degrees)
    solver.distance_constraint(instance, anchor, 0, 0, weight=10)
    solver.align_with(instance, support_collection[0],
                      angle=rotation_degrees -
                      (support_collection[0].rotation[2] * 180.0 / 3.141592653589793))


# ---------------------------------------------------------------------------
# Lounge area: arranged in the upper-left portion of the main rectangle.
# The doorway on the left wall remains clear through x=1.0.
# ---------------------------------------------------------------------------

_place_on_floor(
    lounge_sofa,
    [2.70, 4.525, 0.425],
    -90,
)
solver.against_wall(lounge_sofa[0], walls[4])

_place_on_floor(
    coffee_table_lounge,
    [2.70, 3.35, 0.21],
    90,
)
solver.point_towards(coffee_table_lounge[0], lounge_sofa[0])

_place_on_floor(
    lounge_armchair_A,
    [1.40, 2.30, 0.45],
    35,
)
solver.point_towards(lounge_armchair_A[0], coffee_table_lounge[0])

_place_on_floor(
    lounge_armchair_B,
    [4.00, 2.30, 0.45],
    145,
)
solver.point_towards(lounge_armchair_B[0], coffee_table_lounge[0])

# The coffee table lies on the line between the two lamps.
_place_on_floor(
    floor_lamp_A,
    [1.25, 3.35, 0.825],
    0,
)
solver.point_towards(floor_lamp_A[0], coffee_table_lounge[0])
solver.distance_constraint(
    floor_lamp_A[0], coffee_table_lounge[0], 1.45, 1.45, weight=10
)

_place_on_floor(
    floor_lamp_B,
    [4.15, 3.35, 0.825],
    180,
)
solver.point_towards(floor_lamp_B[0], coffee_table_lounge[0])
solver.distance_constraint(
    floor_lamp_B[0], coffee_table_lounge[0], 1.45, 1.45, weight=10
)

solver.distance_constraint(
    coffee_table_lounge[0], floor_lamp_A[0], 1.45, 1.45, weight=10
)
solver.distance_constraint(
    coffee_table_lounge[0], floor_lamp_B[0], 1.45, 1.45, weight=10
)

_place_on_floor(
    round_side_table_A,
    [0.90, 2.10, 0.275],
    0,
)
solver.point_towards(round_side_table_A[0], lounge_armchair_A[0])

_place_on_floor(
    round_side_table_B,
    [4.55, 2.05, 0.275],
    0,
)
solver.point_towards(round_side_table_B[0], lounge_armchair_B[0])

# Required mug placement and other lounge accessories.
_place_on_surface(
    ceramic_mug_A,
    coffee_table_lounge,
    [2.42, 3.22, 0.47],
    90,
)
solver.distance_constraint(
    ceramic_mug_A[0], coffee_table_lounge[0], 0, 0.45, weight=10
)

_place_on_surface(
    remote_control,
    coffee_table_lounge,
    [2.73, 3.20, 0.435],
    90,
)
solver.point_towards(remote_control[0], lounge_sofa[0])

_place_on_surface(
    magazine_A,
    coffee_table_lounge,
    [3.03, 3.43, 0.425],
    90,
)

_place_on_surface(
    decorative_tray,
    coffee_table_lounge,
    [2.35, 3.48, 0.48],
    90,
)

_place_on_surface(
    small_vase_A,
    round_side_table_A,
    [0.90, 2.10, 0.675],
    0,
)

_place_on_surface(
    magazine_B,
    round_side_table_B,
    [4.55, 2.05, 0.565],
    0,
)


# ---------------------------------------------------------------------------
# Storage wall along y=0. Shelving is rotated so its broad side runs along
# the wall and all units project only a short distance into the room.
# ---------------------------------------------------------------------------

_place_on_floor(
    tall_bookshelf_A,
    [0.70, 0.20, 1.10],
    90,
)
solver.against_wall(tall_bookshelf_A[0], walls[0])

_place_on_floor(
    tall_bookshelf_B,
    [2.00, 0.20, 1.10],
    90,
)
solver.against_wall(tall_bookshelf_B[0], walls[0])
solver.align_with(tall_bookshelf_B[0], tall_bookshelf_A[0])

_place_on_floor(
    sideboard_credenza,
    [3.50, 0.225, 0.425],
    90,
)
solver.against_wall(sideboard_credenza[0], walls[0])

_place_on_floor(
    coat_stand,
    [4.65, 0.30, 0.90],
    90,
)
solver.point_towards(coat_stand[0], _layout_anchor([4.65, 1.30, 0.90], 90))

_place_on_floor(
    pedestal_cabinet_B,
    [5.35, 0.275, 0.325],
    90,
)
solver.against_wall(pedestal_cabinet_B[0], walls[0])

_place_on_floor(
    printer_stand,
    [6.20, 0.325, 0.375],
    90,
)
solver.against_wall(printer_stand[0], walls[0])

_place_on_floor(
    pedestal_cabinet_A,
    [7.35, 0.275, 0.325],
    90,
)
solver.against_wall(pedestal_cabinet_A[0], walls[0])

# Decorations are distributed across the storage surfaces without overlap.
_place_on_surface(
    framed_certificate,
    sideboard_credenza,
    [3.20, 0.225, 1.01],
    0,
)

_place_on_surface(
    picture_frame,
    sideboard_credenza,
    [3.58, 0.225, 1.20],
    0,
)
solver.align_with(picture_frame[0], framed_certificate[0])

_place_on_surface(
    small_vase_B,
    sideboard_credenza,
    [3.98, 0.225, 0.975],
    0,
)

_place_on_surface(
    file_stack_A,
    pedestal_cabinet_B,
    [5.35, 0.275, 0.68],
    90,
)

_place_on_surface(
    file_stack_B,
    pedestal_cabinet_A,
    [7.35, 0.275, 0.74],
    90,
)

_place_on_surface(
    office_printer,
    printer_stand,
    [6.20, 0.325, 0.90],
    90,
)


# ---------------------------------------------------------------------------
# Executive work area in the lower-right. The visitor chairs face the desk,
# while the manager chair is placed behind it.
# ---------------------------------------------------------------------------

_place_on_floor(
    executive_desk,
    [6.50, 1.55, 0.38],
    0,
)
solver.point_towards(
    executive_desk[0],
    _layout_anchor([5.30, 1.55, 0.38], 180),
)

_place_on_floor(
    manager_task_chair,
    [7.45, 1.55, 0.575],
    180,
)
solver.point_towards(manager_task_chair[0], executive_desk[0])
solver.distance_constraint(
    manager_task_chair[0], executive_desk[0], 0.85, 1.10, weight=10
)

_place_on_floor(
    guest_chair_A,
    [5.45, 1.05, 0.425],
    0,
)
solver.point_towards(guest_chair_A[0], executive_desk[0])
solver.distance_constraint(
    guest_chair_A[0], executive_desk[0], 0.90, 1.25, weight=10
)

_place_on_floor(
    guest_chair_B,
    [5.45, 2.05, 0.425],
    0,
)
solver.point_towards(guest_chair_B[0], executive_desk[0])
solver.distance_constraint(
    guest_chair_B[0], executive_desk[0], 0.90, 1.25, weight=10
)

_place_on_floor(
    waste_bin_A,
    [4.72, 1.10, 0.20],
    0,
)
solver.point_towards(waste_bin_A[0], executive_desk[0])

_place_on_floor(
    waste_bin_B,
    [7.65, 2.48, 0.20],
    180,
)
solver.point_towards(waste_bin_B[0], executive_desk[0])

# Desk accessories are spaced across the desktop.
_place_on_surface(
    desk_organizer,
    executive_desk,
    [6.35, 0.95, 0.85],
    0,
)

_place_on_surface(
    notepad,
    executive_desk,
    [6.35, 1.35, 0.765],
    0,
)

_place_on_surface(
    book_A,
    executive_desk,
    [6.35, 1.68, 0.78],
    0,
)

_place_on_surface(
    book_B,
    executive_desk,
    [6.67, 1.15, 0.785],
    0,
)

_place_on_surface(
    hardcover_book,
    executive_desk,
    [6.67, 1.55, 0.78],
    0,
)


# ---------------------------------------------------------------------------
# Meeting area in the upper-right. Its placement leaves clearance from both
# windows on the right wall and from the lounge circulation route.
# ---------------------------------------------------------------------------

_place_on_floor(
    round_meeting_table,
    [6.40, 4.55, 0.375],
    0,
)
solver.point_towards(
    round_meeting_table[0],
    _layout_anchor([6.40, 3.50, 0.375], -90),
)

_place_on_floor(
    guest_chair_C,
    [5.35, 4.55, 0.425],
    0,
)
solver.point_towards(guest_chair_C[0], round_meeting_table[0])
solver.distance_constraint(
    guest_chair_C[0], round_meeting_table[0], 1.05, 1.05, weight=10
)

_place_on_floor(
    guest_chair_D,
    [7.45, 4.55, 0.425],
    180,
)
solver.point_towards(guest_chair_D[0], round_meeting_table[0])
solver.distance_constraint(
    guest_chair_D[0], round_meeting_table[0], 1.05, 1.05, weight=10
)

_place_on_floor(
    meeting_chair,
    [6.40, 3.52, 0.41],
    90,
)
solver.point_towards(meeting_chair[0], round_meeting_table[0])
solver.distance_constraint(
    meeting_chair[0], round_meeting_table[0], 1.03, 1.03, weight=10
)

_place_on_surface(
    magazine_C,
    round_meeting_table,
    [6.22, 4.50, 0.765],
    0,
)

_place_on_surface(
    ceramic_mug_B,
    round_meeting_table,
    [6.62, 4.52, 0.80],
    0,
)


# ---------------------------------------------------------------------------
# Console in the upper recess. It remains separate from the meeting table and
# is secured to the y=6 wall.
# ---------------------------------------------------------------------------

_place_on_floor(
    console_table,
    [4.75, 5.81, 0.40],
    -90,
)
solver.against_wall(console_table[0], walls[2])
solver.point_towards(
    console_table[0],
    _layout_anchor([4.75, 4.80, 0.40], -90),
)

solver.constraints = []
console_table[0].position = [4.75, 5.809950351715088, 0.4000000059604645]
console_table[0].rotation = [0, 0, -1.5706349235718708]
console_table[0].optimize = 2
coffee_table_lounge[0].position = [2.700000047683716, 3.3499999046325684, 0.20999999344348907]
coffee_table_lounge[0].rotation = [0, 0, 1.6367697721712688]
coffee_table_lounge[0].optimize = 2
magazine_C[0].position = [6.21999979019165, 4.5, 0.7649999856948853]
magazine_C[0].rotation = [0, 0, 0.04431265608699683]
magazine_C[0].optimize = 2
guest_chair_D[0].position = [7.508031845092773, 4.550000190734863, 0.42500001192092896]
guest_chair_D[0].rotation = [0, 0, -3.125884689672577]
guest_chair_D[0].optimize = 2
guest_chair_C[0].position = [5.349999904632568, 4.550000190734863, 0.42500001192092896]
guest_chair_C[0].rotation = [0, 0, 0.0157079639172164]
guest_chair_C[0].optimize = 2
sideboard_credenza[0].position = [3.5, 0.22520828247070312, 0.42500001192092896]
sideboard_credenza[0].rotation = [0, 0, 1.5710274116057898]
sideboard_credenza[0].optimize = 2
floor_lamp_A[0].position = [1.25, 3.3499999046325684, 0.824999988079071]
floor_lamp_A[0].rotation = [0, 0, 0.01884955539881635]
floor_lamp_A[0].optimize = 2
small_vase_A[0].position = [0.8999999761581421, 2.0999999046325684, 0.675000011920929]
small_vase_A[0].rotation = [0, 0, 0.018933431320488102]
small_vase_A[0].optimize = 2
pedestal_cabinet_A[0].position = [7.349999904632568, 0.27507898211479187, 0.32499998807907104]
pedestal_cabinet_A[0].rotation = [0, 0, 1.5706103944327354]
pedestal_cabinet_A[0].optimize = 2
small_vase_B[0].position = [3.9800000190734863, 0.22499999403953552, 0.9750000238418579]
small_vase_B[0].rotation = [0, 0, -1.2126057336979512e-05]
small_vase_B[0].optimize = 2
ceramic_mug_A[0].position = [2.263875961303711, 3.0631067752838135, 0.4699999988079071]
ceramic_mug_A[0].rotation = [0, 0, 1.6373040331693356]
ceramic_mug_A[0].optimize = 2
round_meeting_table[0].position = [6.400000095367432, 4.550000190734863, 0.375]
round_meeting_table[0].rotation = [0, 0, 0.043982298440307294]
round_meeting_table[0].optimize = 2
pedestal_cabinet_B[0].position = [5.349999904632568, 0.27507898211479187, 0.32499998807907104]
pedestal_cabinet_B[0].rotation = [0, 0, 1.5706103944327354]
pedestal_cabinet_B[0].optimize = 2
ceramic_mug_B[0].position = [6.619999885559082, 4.519999980926514, 0.800000011920929]
ceramic_mug_B[0].rotation = [0, 0, 0.04431265608699683]
ceramic_mug_B[0].optimize = 2
file_stack_A[0].position = [5.349999904632568, 0.2750000059604645, 0.6799999475479126]
file_stack_A[0].rotation = [0, 0, 1.5704192898420406]
file_stack_A[0].optimize = 2
desk_organizer[0].position = [6.349999904632568, 0.949999988079071, 0.8500000238418579]
desk_organizer[0].rotation = [0, 0, 0.06936331779447753]
desk_organizer[0].optimize = 2
framed_certificate[0].position = [3.200000047683716, 0.22499999403953552, 1.0099999904632568]
framed_certificate[0].rotation = [0, 0, 0.00015262892670132595]
framed_certificate[0].optimize = 2
guest_chair_B[0].position = [5.449999809265137, 2.049999952316284, 0.42500001192092896]
guest_chair_B[0].rotation = [0, 0, 0.0157079639172164]
guest_chair_B[0].optimize = 2
hardcover_book[0].position = [6.670000076293945, 1.5499999523162842, 0.7799999713897705]
hardcover_book[0].rotation = [0, 0, 0.06936331779447753]
hardcover_book[0].optimize = 2
floor_lamp_B[0].position = [4.150000095367432, 3.3499999046325684, 0.824999988079071]
floor_lamp_B[0].rotation = [0, 0, -3.122743098190977]
floor_lamp_B[0].optimize = 2
lounge_armchair_B[0].position = [4.0, 2.299999952316284, 0.44999998807907104]
lounge_armchair_B[0].rotation = [0, 0, 2.546435351291427]
lounge_armchair_B[0].optimize = 2
printer_stand[0].position = [6.199999809265137, 0.2744465172290802, 0.375]
printer_stand[0].rotation = [0, 0, 1.5706148017450048]
printer_stand[0].optimize = 2
tall_bookshelf_B[0].position = [2.0, 0.2000417411327362, 1.100000023841858]
tall_bookshelf_B[0].rotation = [0, 0, 1.5709577245439412]
tall_bookshelf_B[0].optimize = 2
notepad[0].position = [6.349999904632568, 1.350000023841858, 0.7649999856948853]
notepad[0].rotation = [0, 0, 0.06936331779447753]
notepad[0].optimize = 2
guest_chair_A[0].position = [5.449999809265137, 1.0499999523162842, 0.42500001192092896]
guest_chair_A[0].rotation = [0, 0, 0.0157079639172164]
guest_chair_A[0].optimize = 2
manager_task_chair[0].position = [7.449999809265137, 1.5499999523162842, 0.574999988079071]
manager_task_chair[0].rotation = [0, 0, -3.125884689672577]
manager_task_chair[0].optimize = 2
book_A[0].position = [6.349999904632568, 1.6799999475479126, 0.7799999713897705]
book_A[0].rotation = [0, 0, 0.06936331779447753]
book_A[0].optimize = 2
magazine_A[0].position = [3.0299999713897705, 3.430000066757202, 0.42499998211860657]
magazine_A[0].rotation = [0, 0, 1.6372910184526834]
magazine_A[0].optimize = 2
decorative_tray[0].position = [2.3499999046325684, 3.4800000190734863, 0.47999998927116394]
decorative_tray[0].rotation = [0, 0, 1.6372910184526834]
decorative_tray[0].optimize = 2
tall_bookshelf_A[0].position = [0.699999988079071, 0.2000417411327362, 1.100000023841858]
tall_bookshelf_A[0].rotation = [0, 0, 1.5709577245439412]
tall_bookshelf_A[0].optimize = 2
book_B[0].position = [6.670000076293945, 1.149999976158142, 0.7849999666213989]
book_B[0].rotation = [0, 0, 0.06936331779447753]
book_B[0].optimize = 2
executive_desk[0].position = [6.5, 1.5499999523162842, 0.3799999952316284]
executive_desk[0].rotation = [0, 0, 0.06911503821575936]
executive_desk[0].optimize = 2
round_side_table_A[0].position = [0.8999999761581421, 2.0999999046325684, 0.2750000059604645]
round_side_table_A[0].rotation = [0, 0, 0.01884955539881635]
round_side_table_A[0].optimize = 2
waste_bin_A[0].position = [4.71999979019165, 1.100000023841858, 0.20000000298023224]
waste_bin_A[0].rotation = [0, 0, 0.01256637125682779]
waste_bin_A[0].optimize = 2
file_stack_B[0].position = [7.349999904632568, 0.2750000059604645, 0.7400000095367432]
file_stack_B[0].rotation = [0, 0, 1.5704192898420406]
file_stack_B[0].optimize = 2
picture_frame[0].position = [3.5799999237060547, 0.2754373252391815, 1.2000000476837158]
picture_frame[0].rotation = [0, 0, 0.00015262892670132595]
picture_frame[0].optimize = 2
office_printer[0].position = [6.199999809265137, 0.32499998807907104, 0.8999999761581421]
office_printer[0].rotation = [0, 0, 1.5704196829291206]
office_printer[0].optimize = 2
round_side_table_B[0].position = [4.550000190734863, 2.049999952316284, 0.2750000059604645]
round_side_table_B[0].rotation = [0, 0, 1.3824324451436096]
round_side_table_B[0].optimize = 2
lounge_sofa[0].position = [2.700000047683716, 4.525226593017578, 0.42500001192092896]
lounge_sofa[0].rotation = [0, 0, -1.570980205111166]
lounge_sofa[0].optimize = 2
coat_stand[0].position = [4.650000095367432, 0.30000001192092896, 0.8999999761581421]
coat_stand[0].rotation = [0, 0, 1.5833626980517244]
coat_stand[0].optimize = 2
remote_control[0].position = [2.7300000190734863, 3.200000047683716, 0.4349999725818634]
remote_control[0].rotation = [0, 0, 1.6373040331693356]
remote_control[0].optimize = 2
meeting_chair[0].position = [6.400000095367432, 3.5199999809265137, 0.4099999964237213]
meeting_chair[0].rotation = [0, 0, 1.586504290712113]
meeting_chair[0].optimize = 2
waste_bin_B[0].position = [7.650000095367432, 2.4800000190734863, 0.20000000298023224]
waste_bin_B[0].rotation = [0, 0, -3.1290262823329655]
waste_bin_B[0].optimize = 2
lounge_armchair_A[0].position = [1.399999976158142, 2.299999952316284, 0.44999998807907104]
lounge_armchair_A[0].rotation = [0, 0, 0.6265732016538754]
lounge_armchair_A[0].optimize = 2
magazine_B[0].position = [4.550000190734863, 2.049999952316284, 0.5649999976158142]
magazine_B[0].rotation = [0, 0, 1.3590723152978093]
magazine_B[0].optimize = 2

