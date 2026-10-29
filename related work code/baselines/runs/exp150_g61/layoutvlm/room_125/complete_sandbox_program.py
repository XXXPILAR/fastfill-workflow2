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
    Wall(corner1=[8.00, 0.00, 0.00], corner2=[8.00, 3.00, 0.00]),
    Wall(corner1=[8.00, 3.00, 0.00], corner2=[0.00, 3.00, 0.00]),
    Wall(corner1=[0.00, 3.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
consultation_desk = Assets(description="consultation desk", size=[0.75, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
wall_art_print_A = Assets(description="Picture of trees by a lake in black picture frame.", size=[0.04, 0.65, 0.45], placements=[AssetInstance() for _ in range(1)])
paper_notepad_A = Assets(description="A box of kleenix wipes.", size=[0.12, 0.23, 0.09], placements=[AssetInstance() for _ in range(1)])
wall_mounted_cabinet_A = Assets(description="I brown cabinet with two doors.", size=[0.35, 0.80, 0.65], placements=[AssetInstance() for _ in range(1)])
disinfectant_wipe_container = Assets(description="A white bottle of shampoo with black and purple writing on it.", size=[0.08, 0.09, 0.24], placements=[AssetInstance() for _ in range(1)])
patient_guest_chair_A = Assets(description="A small gray chair with pinewood legs.", size=[0.52, 0.48, 0.80], placements=[AssetInstance() for _ in range(1)])
magazine_stack_A = Assets(description="Three purple books in a stack.", size=[0.28, 0.22, 0.06], placements=[AssetInstance() for _ in range(1)])
waste_bin_A = Assets(description="A cream colored trash can.", size=[0.28, 0.28, 0.40], placements=[AssetInstance() for _ in range(1)])
wall_mounted_cabinet_B = Assets(description="I brown cabinet with two doors.", size=[0.35, 0.80, 0.65], placements=[AssetInstance() for _ in range(1)])
desktop_computer_with_monitor = Assets(description="a computer monitor with a yellow screen.", size=[0.22, 0.55, 0.43], placements=[AssetInstance() for _ in range(1)])
coat_stand = Assets(description="The coatrack is wooden with a round bottom.", size=[0.50, 0.50, 1.75], placements=[AssetInstance() for _ in range(1)])
portable_vital_signs_cart = Assets(description="a blue, pixelated robot with a computer monitor on wheels and a green screen.", size=[0.50, 0.50, 1.30], placements=[AssetInstance() for _ in range(1)])
document_box = Assets(description="A carboard box with side openings for handles and one of the flaps raised with tape on it and tape on the second sealed flap.", size=[0.32, 0.40, 0.30], placements=[AssetInstance() for _ in range(1)])
pen_holder_with_pens = Assets(description="A cylindrical gray cup with two pens and a pencil sticking out.", size=[0.09, 0.09, 0.20], placements=[AssetInstance() for _ in range(1)])
umbrella_stand = Assets(description="A gray and black mesh speaker.", size=[0.25, 0.25, 0.50], placements=[AssetInstance() for _ in range(1)])
patient_guest_chair_B = Assets(description="A small gray chair with pinewood legs.", size=[0.52, 0.48, 0.80], placements=[AssetInstance() for _ in range(1)])
mobile_exam_stool_A = Assets(description="A rusted metal stool or low office chair with four casters.", size=[0.48, 0.48, 0.55], placements=[AssetInstance() for _ in range(1)])
small_round_side_table_A = Assets(description="A light colored stool with three legs.", size=[0.42, 0.42, 0.50], placements=[AssetInstance() for _ in range(1)])
tall_storage_cabinet = Assets(description="A cabinet with four doors.", size=[0.45, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
mobile_exam_stool_B = Assets(description="A rusted metal stool or low office chair with four casters.", size=[0.48, 0.48, 0.55], placements=[AssetInstance() for _ in range(1)])
clipboard_A = Assets(description="A black cellular telephone.", size=[0.15, 0.07, 0.01], placements=[AssetInstance() for _ in range(1)])
wall_art_print_B = Assets(description="Picture of trees by a lake in black picture frame.", size=[0.04, 0.65, 0.45], placements=[AssetInstance() for _ in range(1)])
desk_organizer_tray_A = Assets(description="A tray for carrying food.", size=[0.25, 0.35, 0.04], placements=[AssetInstance() for _ in range(1)])
wall_mounted_whiteboard = Assets(description="A poster of blueprints for a picture frame.", size=[0.03, 0.90, 0.60], placements=[AssetInstance() for _ in range(1)])
paper_notepad_B = Assets(description="A pink spiral notebook with a green leaf on it.", size=[0.21, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
clipboard_B = Assets(description="A handheld phone with a large touchscreen.", size=[0.15, 0.07, 0.01], placements=[AssetInstance() for _ in range(1)])
wall_clock = Assets(description="A round gray wall clock.", size=[0.04, 0.30, 0.30], placements=[AssetInstance() for _ in range(1)])
magazine_floor_rack = Assets(description="A set of magazine shelves for displaying booksq.", size=[0.30, 0.55, 1.05], placements=[AssetInstance() for _ in range(1)])
small_round_side_table_B = Assets(description="A light colored stool with three legs.", size=[0.42, 0.42, 0.50], placements=[AssetInstance() for _ in range(1)])
paper_notepad_C = Assets(description="A red notepad decorated with a slug in the lower corner.", size=[0.21, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
waste_bin_B = Assets(description="A cream colored trash can.", size=[0.28, 0.28, 0.40], placements=[AssetInstance() for _ in range(1)])
mobile_medical_trolley = Assets(description="A hospital cart with a set of clear drawers, iv pole and a red biohazard disposal container.", size=[0.50, 0.65, 1.65], placements=[AssetInstance() for _ in range(1)])
desk_organizer_tray_B = Assets(description="A brown leather card holder with a logo on it.", size=[0.07, 0.12, 0.04], placements=[AssetInstance() for _ in range(1)])
wall_art_print_C = Assets(description="Picture of trees by a lake in black picture frame.", size=[0.04, 0.65, 0.45], placements=[AssetInstance() for _ in range(1)])
recycling_bin = Assets(description="recycling bin", size=[0.35, 0.32, 0.50], placements=[AssetInstance() for _ in range(1)])
examination_couch = Assets(description="Wood frame lawn chair with a white cushion.", size=[1.90, 0.75, 0.80], placements=[AssetInstance() for _ in range(1)])
waste_bin_C = Assets(description="A cream colored trash can.", size=[0.28, 0.28, 0.40], placements=[AssetInstance() for _ in range(1)])
wall_mounted_glove_dispenser = Assets(description="A white box with the top open.", size=[0.12, 0.26, 0.15], placements=[AssetInstance() for _ in range(1)])
magazine_stack_B = Assets(description="Three purple books in a stack.", size=[0.28, 0.22, 0.06], placements=[AssetInstance() for _ in range(1)])

consultation_desk[0].instance_id = 'consultation_desk_0'
wall_art_print_A[0].instance_id = 'wall_art_print_A_0'
paper_notepad_A[0].instance_id = 'paper_notepad_A_0'
wall_mounted_cabinet_A[0].instance_id = 'wall_mounted_cabinet_A_0'
disinfectant_wipe_container[0].instance_id = 'disinfectant_wipe_container_0'
patient_guest_chair_A[0].instance_id = 'patient_guest_chair_A_0'
magazine_stack_A[0].instance_id = 'magazine_stack_A_0'
waste_bin_A[0].instance_id = 'waste_bin_A_0'
wall_mounted_cabinet_B[0].instance_id = 'wall_mounted_cabinet_B_0'
desktop_computer_with_monitor[0].instance_id = 'desktop_computer_with_monitor_0'
coat_stand[0].instance_id = 'coat_stand_0'
portable_vital_signs_cart[0].instance_id = 'portable_vital_signs_cart_0'
document_box[0].instance_id = 'document_box_0'
pen_holder_with_pens[0].instance_id = 'pen_holder_with_pens_0'
umbrella_stand[0].instance_id = 'umbrella_stand_0'
patient_guest_chair_B[0].instance_id = 'patient_guest_chair_B_0'
mobile_exam_stool_A[0].instance_id = 'mobile_exam_stool_A_0'
small_round_side_table_A[0].instance_id = 'small_round_side_table_A_0'
tall_storage_cabinet[0].instance_id = 'tall_storage_cabinet_0'
mobile_exam_stool_B[0].instance_id = 'mobile_exam_stool_B_0'
clipboard_A[0].instance_id = 'clipboard_A_0'
wall_art_print_B[0].instance_id = 'wall_art_print_B_0'
desk_organizer_tray_A[0].instance_id = 'desk_organizer_tray_A_0'
wall_mounted_whiteboard[0].instance_id = 'wall_mounted_whiteboard_0'
paper_notepad_B[0].instance_id = 'paper_notepad_B_0'
clipboard_B[0].instance_id = 'clipboard_B_0'
wall_clock[0].instance_id = 'wall_clock_0'
magazine_floor_rack[0].instance_id = 'magazine_floor_rack_0'
small_round_side_table_B[0].instance_id = 'small_round_side_table_B_0'
paper_notepad_C[0].instance_id = 'paper_notepad_C_0'
waste_bin_B[0].instance_id = 'waste_bin_B_0'
mobile_medical_trolley[0].instance_id = 'mobile_medical_trolley_0'
desk_organizer_tray_B[0].instance_id = 'desk_organizer_tray_B_0'
wall_art_print_C[0].instance_id = 'wall_art_print_C_0'
recycling_bin[0].instance_id = 'recycling_bin_0'
examination_couch[0].instance_id = 'examination_couch_0'
waste_bin_C[0].instance_id = 'waste_bin_C_0'
wall_mounted_glove_dispenser[0].instance_id = 'wall_mounted_glove_dispenser_0'
magazine_stack_B[0].instance_id = 'magazine_stack_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

consultation_desk[0].position = [5.397496088852222, 0.7309807036604349, 0.375]
consultation_desk[0].rotation = [0, 0, 0]
wall_art_print_A[0].position = [5.311205190341186, 2.4215331451337043, 0.225]
wall_art_print_A[0].rotation = [0, 0, 0]
paper_notepad_A[0].position = [7.150917006350962, 2.1497232553429293, 0.045]
paper_notepad_A[0].rotation = [0, 0, 0]
wall_mounted_cabinet_A[0].position = [0.33850670773604197, 2.097214945777199, 0.325]
wall_mounted_cabinet_A[0].rotation = [0, 0, 0]
disinfectant_wipe_container[0].position = [0.004674588855823281, 2.3643219425941, 0.12]
disinfectant_wipe_container[0].rotation = [0, 0, 0]
patient_guest_chair_A[0].position = [5.379076265341741, 0.7940984887769701, 0.4]
patient_guest_chair_A[0].rotation = [0, 0, 0]
magazine_stack_A[0].position = [1.5276791687010745, 0.1857219368387294, 0.03]
magazine_stack_A[0].rotation = [0, 0, 0]
waste_bin_A[0].position = [7.633484553012307, 0.8675901346275041, 0.2]
waste_bin_A[0].rotation = [0, 0, 0]
wall_mounted_cabinet_B[0].position = [6.385086818711039, 2.0126312341746564, 0.325]
wall_mounted_cabinet_B[0].rotation = [0, 0, 0]
desktop_computer_with_monitor[0].position = [2.6264059410999474, 0.6953718821818309, 0.215]
desktop_computer_with_monitor[0].rotation = [0, 0, 0]
coat_stand[0].position = [2.526621010341213, 1.1182263120062705, 0.875]
coat_stand[0].rotation = [0, 0, 0]
portable_vital_signs_cart[0].position = [6.859204297831784, 2.9204105236090454, 0.65]
portable_vital_signs_cart[0].rotation = [0, 0, 0]
document_box[0].position = [0.44851421942779, 0.7788004523262982, 0.15]
document_box[0].rotation = [0, 0, 0]
pen_holder_with_pens[0].position = [6.278664075089808, 1.1732315217821139, 0.1]
pen_holder_with_pens[0].rotation = [0, 0, 0]
umbrella_stand[0].position = [3.593884191067869, 1.5746129756550635, 0.25]
umbrella_stand[0].rotation = [0, 0, 0]
patient_guest_chair_B[0].position = [5.799401110844363, 0.3708880964598962, 0.4]
patient_guest_chair_B[0].rotation = [0, 0, 0]
mobile_exam_stool_A[0].position = [1.7040067169583484, 0.5665082941311554, 0.275]
mobile_exam_stool_A[0].rotation = [0, 0, 0]
small_round_side_table_A[0].position = [0.21312631785243052, 0.7025962099864526, 0.25]
small_round_side_table_A[0].rotation = [0, 0, 0]
tall_storage_cabinet[0].position = [0.3160639461415915, 2.454902102421668, 0.9]
tall_storage_cabinet[0].rotation = [0, 0, 0]
mobile_exam_stool_B[0].position = [3.6774145928921484, 2.5654884327320655, 0.275]
mobile_exam_stool_B[0].rotation = [0, 0, 0]
clipboard_A[0].position = [0.9449312703195236, 0.798305168796302, 0.006]
clipboard_A[0].rotation = [0, 0, 0]
wall_art_print_B[0].position = [5.749073301619178, 0.3769338035633253, 0.225]
wall_art_print_B[0].rotation = [0, 0, 0]
desk_organizer_tray_A[0].position = [1.4978630593239917, 2.068751075270994, 0.0225]
desk_organizer_tray_A[0].rotation = [0, 0, 0]
wall_mounted_whiteboard[0].position = [3.3906239008649885, 0.9014467925118752, 0.3]
wall_mounted_whiteboard[0].rotation = [0, 0, 0]
paper_notepad_B[0].position = [1.3565414853050335, 0.723791740908789, 0.0075]
paper_notepad_B[0].rotation = [0, 0, 0]
clipboard_B[0].position = [3.4427019453477685, 1.0084550500316771, 0.005]
clipboard_B[0].rotation = [0, 0, 0]
wall_clock[0].position = [6.426563220746803, 0.06995619666461772, 0.15]
wall_clock[0].rotation = [0, 0, 0]
magazine_floor_rack[0].position = [2.9888410590770604, 0.6980036300574813, 0.525]
magazine_floor_rack[0].rotation = [0, 0, 0]
small_round_side_table_B[0].position = [2.0476005727310973, 0.5435474247820032, 0.25]
small_round_side_table_B[0].rotation = [0, 0, 0]
paper_notepad_C[0].position = [5.9698602393176, 0.3847809267047477, 0.0075]
paper_notepad_C[0].rotation = [0, 0, 0]
waste_bin_B[0].position = [3.6163173620776234, 2.5148584461963925, 0.2]
waste_bin_B[0].rotation = [0, 0, 0]
mobile_medical_trolley[0].position = [0.9117407529050343, 0.22396385048799583, 0.825]
mobile_medical_trolley[0].rotation = [0, 0, 0]
desk_organizer_tray_B[0].position = [0.888300677561964, 0.8476497932263001, 0.0225]
desk_organizer_tray_B[0].rotation = [0, 0, 0]
wall_art_print_C[0].position = [1.5085234683485256, 1.2984761997695344, 0.225]
wall_art_print_C[0].rotation = [0, 0, 0]
recycling_bin[0].position = [7.763062318614509, 0.0853111973501357, 0.25]
recycling_bin[0].rotation = [0, 0, 0]
examination_couch[0].position = [3.0885730612213633, 2.3192227816649655, 0.4]
examination_couch[0].rotation = [0, 0, 0]
waste_bin_C[0].position = [2.6506524679980714, 1.5643345526561092, 0.2]
waste_bin_C[0].rotation = [0, 0, 0]
wall_mounted_glove_dispenser[0].position = [7.54993452153014, 2.8597815846700745, 0.075]
wall_mounted_glove_dispenser[0].rotation = [0, 0, 0]
magazine_stack_B[0].position = [0.4385214577539731, 0.4429150450261041, 0.03]
magazine_stack_B[0].rotation = [0, 0, 0]
consultation_desk[0].position = [5.397496088852222, 0.7309807036604349, 0.375]
consultation_desk[0].rotation = [0, 0, 0]
wall_art_print_A[0].position = [5.311205190341186, 2.4215331451337043, 0.225]
wall_art_print_A[0].rotation = [0, 0, 0]
paper_notepad_A[0].position = [7.150917006350962, 2.1497232553429293, 0.045]
paper_notepad_A[0].rotation = [0, 0, 0]
wall_mounted_cabinet_A[0].position = [0.33850670773604197, 2.097214945777199, 0.325]
wall_mounted_cabinet_A[0].rotation = [0, 0, 0]
disinfectant_wipe_container[0].position = [0.004674588855823281, 2.3643219425941, 0.12]
disinfectant_wipe_container[0].rotation = [0, 0, 0]
patient_guest_chair_A[0].position = [5.379076265341741, 0.7940984887769701, 0.4]
patient_guest_chair_A[0].rotation = [0, 0, 0]
magazine_stack_A[0].position = [1.5276791687010745, 0.1857219368387294, 0.03]
magazine_stack_A[0].rotation = [0, 0, 0]
waste_bin_A[0].position = [7.633484553012307, 0.8675901346275041, 0.2]
waste_bin_A[0].rotation = [0, 0, 0]
wall_mounted_cabinet_B[0].position = [6.385086818711039, 2.0126312341746564, 0.325]
wall_mounted_cabinet_B[0].rotation = [0, 0, 0]
desktop_computer_with_monitor[0].position = [2.6264059410999474, 0.6953718821818309, 0.215]
desktop_computer_with_monitor[0].rotation = [0, 0, 0]
coat_stand[0].position = [2.526621010341213, 1.1182263120062705, 0.875]
coat_stand[0].rotation = [0, 0, 0]
portable_vital_signs_cart[0].position = [6.859204297831784, 2.9204105236090454, 0.65]
portable_vital_signs_cart[0].rotation = [0, 0, 0]
document_box[0].position = [0.44851421942779, 0.7788004523262982, 0.15]
document_box[0].rotation = [0, 0, 0]
pen_holder_with_pens[0].position = [6.278664075089808, 1.1732315217821139, 0.1]
pen_holder_with_pens[0].rotation = [0, 0, 0]
umbrella_stand[0].position = [3.593884191067869, 1.5746129756550635, 0.25]
umbrella_stand[0].rotation = [0, 0, 0]
patient_guest_chair_B[0].position = [5.799401110844363, 0.3708880964598962, 0.4]
patient_guest_chair_B[0].rotation = [0, 0, 0]
mobile_exam_stool_A[0].position = [1.7040067169583484, 0.5665082941311554, 0.275]
mobile_exam_stool_A[0].rotation = [0, 0, 0]
small_round_side_table_A[0].position = [0.21312631785243052, 0.7025962099864526, 0.25]
small_round_side_table_A[0].rotation = [0, 0, 0]
tall_storage_cabinet[0].position = [0.3160639461415915, 2.454902102421668, 0.9]
tall_storage_cabinet[0].rotation = [0, 0, 0]
mobile_exam_stool_B[0].position = [3.6774145928921484, 2.5654884327320655, 0.275]
mobile_exam_stool_B[0].rotation = [0, 0, 0]
clipboard_A[0].position = [0.9449312703195236, 0.798305168796302, 0.006]
clipboard_A[0].rotation = [0, 0, 0]
wall_art_print_B[0].position = [5.749073301619178, 0.3769338035633253, 0.225]
wall_art_print_B[0].rotation = [0, 0, 0]
desk_organizer_tray_A[0].position = [1.4978630593239917, 2.068751075270994, 0.0225]
desk_organizer_tray_A[0].rotation = [0, 0, 0]
wall_mounted_whiteboard[0].position = [3.3906239008649885, 0.9014467925118752, 0.3]
wall_mounted_whiteboard[0].rotation = [0, 0, 0]
paper_notepad_B[0].position = [1.3565414853050335, 0.723791740908789, 0.0075]
paper_notepad_B[0].rotation = [0, 0, 0]
clipboard_B[0].position = [3.4427019453477685, 1.0084550500316771, 0.005]
clipboard_B[0].rotation = [0, 0, 0]
wall_clock[0].position = [6.426563220746803, 0.06995619666461772, 0.15]
wall_clock[0].rotation = [0, 0, 0]
magazine_floor_rack[0].position = [2.9888410590770604, 0.6980036300574813, 0.525]
magazine_floor_rack[0].rotation = [0, 0, 0]
small_round_side_table_B[0].position = [2.0476005727310973, 0.5435474247820032, 0.25]
small_round_side_table_B[0].rotation = [0, 0, 0]
paper_notepad_C[0].position = [5.9698602393176, 0.3847809267047477, 0.0075]
paper_notepad_C[0].rotation = [0, 0, 0]
waste_bin_B[0].position = [3.6163173620776234, 2.5148584461963925, 0.2]
waste_bin_B[0].rotation = [0, 0, 0]
mobile_medical_trolley[0].position = [0.9117407529050343, 0.22396385048799583, 0.825]
mobile_medical_trolley[0].rotation = [0, 0, 0]
desk_organizer_tray_B[0].position = [0.888300677561964, 0.8476497932263001, 0.0225]
desk_organizer_tray_B[0].rotation = [0, 0, 0]
wall_art_print_C[0].position = [1.5085234683485256, 1.2984761997695344, 0.225]
wall_art_print_C[0].rotation = [0, 0, 0]
recycling_bin[0].position = [7.763062318614509, 0.0853111973501357, 0.25]
recycling_bin[0].rotation = [0, 0, 0]
examination_couch[0].position = [3.0885730612213633, 2.3192227816649655, 0.4]
examination_couch[0].rotation = [0, 0, 0]
waste_bin_C[0].position = [2.6506524679980714, 1.5643345526561092, 0.2]
waste_bin_C[0].rotation = [0, 0, 0]
wall_mounted_glove_dispenser[0].position = [7.54993452153014, 2.8597815846700745, 0.075]
wall_mounted_glove_dispenser[0].rotation = [0, 0, 0]
magazine_stack_B[0].position = [0.4385214577539731, 0.4429150450261041, 0.03]
magazine_stack_B[0].rotation = [0, 0, 0]

solver.constraints = []

# The supplied boundary is x=0..8, y=0..3 (not centered on the origin).
# Consultation occupies the west end; examination occupies the northeast.
# Keep the southeast entrance and the route along the south side unobstructed.
# Fixed-point references below are constraint anchors, not additional scene assets.

def set_layout_pose(asset_group, x, y, yaw=0, z=None):
    instance = asset_group[0]
    instance.position = [
        x, y, asset_group.size[2] / 2 if z is None else z
    ]
    instance.rotation = [0, 0, radians(yaw)]


def preserve_position(asset_group):
    instance = asset_group[0]
    solver.distance_constraint(
        instance,
        AssetInstance(position=list(instance.position)),
        0, 0, weight=10
    )


def preserve_orientation(asset_group):
    solver.align_with(
        asset_group[0],
        AssetInstance(rotation=list(asset_group[0].rotation))
    )


# Ground-level furnishings. Rotations account for the supplied local bounding
# boxes: the desk's long dimension is local y, whereas the couch's is local x.
floor_layout = [
    (consultation_desk,          1.65, 1.90,   0),
    (patient_guest_chair_A,      2.65, 1.45, 180),
    (patient_guest_chair_B,      2.65, 2.35, 180),
    (mobile_exam_stool_A,        0.65, 1.90,   0),

    (examination_couch,          5.40, 1.90,   0),
    (small_round_side_table_A,   4.00, 1.90,   0),
    (small_round_side_table_B,   6.80, 1.90, 180),
    (mobile_exam_stool_B,        5.40, 1.00,  90),
    (portable_vital_signs_cart,  4.60, 0.40,  90),
    (mobile_medical_trolley,     5.60, 0.40,  90),

    (tall_storage_cabinet,       3.50, 2.775, 270),
    (magazine_floor_rack,        7.45, 2.85, 270),
    (coat_stand,                 7.65, 2.05, 180),
    (umbrella_stand,             6.95, 2.80, 180),

    (waste_bin_A,                0.30, 0.20,  90),
    (recycling_bin,              0.85, 0.20,  90),
    (waste_bin_B,                3.35, 0.20,  90),
    (waste_bin_C,                6.40, 0.20,  90),
]

for asset_group, px, py, yaw in floor_layout:
    set_layout_pose(asset_group, px, py, yaw)

# Register the important semantic orientations before generic orientation locks.
solver.point_towards(consultation_desk[0], examination_couch[0])
solver.point_towards(patient_guest_chair_A[0], consultation_desk[0])
solver.point_towards(patient_guest_chair_B[0], consultation_desk[0])
solver.point_towards(mobile_exam_stool_A[0], consultation_desk[0])
solver.point_towards(mobile_exam_stool_B[0], examination_couch[0])
solver.point_towards(portable_vital_signs_cart[0], examination_couch[0])
solver.point_towards(mobile_medical_trolley[0], examination_couch[0])

for asset_group, px, py, yaw in floor_layout:
    preserve_position(asset_group)

# These objects do not need to face a particular movable target.
for asset_group in (
    examination_couch, small_round_side_table_A, small_round_side_table_B,
    tall_storage_cabinet, magazine_floor_rack, coat_stand, umbrella_stand,
    waste_bin_A, waste_bin_B, waste_bin_C, recycling_bin
):
    preserve_orientation(asset_group)

solver.against_wall(tall_storage_cabinet[0], walls[2])
solver.against_wall(magazine_floor_rack[0], walls[2])

# The anchored tables lie on opposite ends of the couch along its long axis.
# Maintain usable end clearance without bringing either table into the couch.
solver.distance_constraint(
    small_round_side_table_A[0], examination_couch[0], 1.35, 1.50, weight=10
)
solver.distance_constraint(
    small_round_side_table_B[0], examination_couch[0], 1.35, 1.50, weight=10
)
solver.distance_constraint(
    small_round_side_table_A[0], small_round_side_table_B[0],
    2.70, 3.00, weight=10
)

# Wall-mounted items: use the solid north/south walls rather than either
# west-wall window. Explicit height anchors keep these off the floor.
# Each tuple contains asset, center x/y/z, inward-facing yaw, wall index.
mounted_layout = [
    (wall_art_print_A,            1.20, 2.980, 1.80, 270, 2),
    (wall_art_print_B,            2.50, 2.980, 1.80, 270, 2),
    (wall_art_print_C,            5.40, 2.980, 1.80, 270, 2),
    (wall_mounted_cabinet_A,      4.30, 0.175, 1.95,  90, 0),
    (wall_mounted_cabinet_B,      5.40, 0.175, 1.95,  90, 0),
    (wall_mounted_whiteboard,     2.00, 0.015, 1.65,  90, 0),
    (wall_mounted_glove_dispenser,6.25, 0.060, 1.45,  90, 0),
    (wall_clock,                 7.98, 2.300, 2.35, 180, 1),
]

for asset_group, px, py, pz, yaw, wall_index in mounted_layout:
    set_layout_pose(asset_group, px, py, yaw, pz)
    preserve_position(asset_group)
    solver.against_wall(asset_group[0], walls[wall_index])
    preserve_orientation(asset_group)

# Small items are supported by actual supplied furniture.
# Desktop items occupy separate patches of the 0.75 x 1.60 m desktop.
# The notebook on side table B rests on its magazine stack.
surface_layout = [
    (desktop_computer_with_monitor, consultation_desk,       1.45, 2.25, 180),
    (desk_organizer_tray_A,         consultation_desk,       1.80, 1.40,   0),
    (paper_notepad_A,               consultation_desk,       1.45, 1.35,   0),
    (pen_holder_with_pens,          consultation_desk,       1.85, 2.50,   0),
    (desk_organizer_tray_B,         consultation_desk,       1.80, 1.80,   0),
    (paper_notepad_B,               consultation_desk,       1.80, 2.10,   0),
    (clipboard_A,                  desk_organizer_tray_A,   1.80, 1.40,   0),
    (clipboard_B,                  consultation_desk,       1.45, 1.70,   0),

    (disinfectant_wipe_container,  small_round_side_table_A, 4.00, 1.90,   0),
    (magazine_stack_A,             small_round_side_table_B, 6.80, 1.90,   0),
    (paper_notepad_C,              magazine_stack_A,        6.80, 1.90,   0),
    (magazine_stack_B,             magazine_floor_rack,     7.45, 2.85, 270),
    (document_box,                 tall_storage_cabinet,    3.50, 2.775,270),
]

# Process supporting objects before objects stacked on them.
for asset_group, support_group, px, py, yaw in surface_layout:
    support_top = support_group[0].position[2] + support_group.size[2] / 2
    center_height = support_top + asset_group.size[2] / 2
    set_layout_pose(asset_group, px, py, yaw, center_height)

    # Support is the primary constraint; the anchor preserves the selected
    # non-overlapping patch on that support.
    solver.on_top_of(asset_group[0], support_group[0])
    preserve_position(asset_group)
    solver.align_with(
        asset_group[0],
        support_group[0],
        angle=yaw - support_group[0].rotation[2] * 180 / radians(180)
    )

# Preserve working clearances around the consultation seating.
solver.distance_constraint(
    patient_guest_chair_A[0], consultation_desk[0], 1.05, 1.20
)
solver.distance_constraint(
    patient_guest_chair_B[0], consultation_desk[0], 1.05, 1.20
)
solver.distance_constraint(
    patient_guest_chair_A[0], patient_guest_chair_B[0], 0.85, 1.00
)

solver.constraints = []
small_round_side_table_B[0].position = [6.800000190734863, 1.899999976158142, 0.25]
small_round_side_table_B[0].rotation = [0, 0, -3.1196015053037707]
small_round_side_table_B[0].optimize = 2
paper_notepad_B[0].position = [1.7999999523162842, 2.0999999046325684, 0.7549999952316284]
paper_notepad_B[0].rotation = [0, 0, 0.09138689005137257]
paper_notepad_B[0].optimize = 2
wall_clock[0].position = [7.981812477111816, 2.299999952316284, 0.15000000596046448]
wall_clock[0].rotation = [0, 0, -3.137378582747524]
wall_clock[0].optimize = 2
wall_mounted_cabinet_A[0].position = [4.300000190734863, 0.1743355095386505, 0.32499998807907104]
wall_mounted_cabinet_A[0].rotation = [0, 0, 1.5750129000098558]
wall_mounted_cabinet_A[0].optimize = 2
mobile_exam_stool_B[0].position = [5.400000095367432, 1.0, 0.2750000059604645]
mobile_exam_stool_B[0].rotation = [0, 0, 1.5802211042556205]
mobile_exam_stool_B[0].optimize = 2
clipboard_A[0].position = [1.7999999523162842, 1.399999976158142, 0.7949999570846558]
clipboard_A[0].rotation = [0, 0, 0.09611712671695054]
clipboard_A[0].optimize = 2
magazine_floor_rack[0].position = [7.449999809265137, 2.8492393493652344, 0.5249999761581421]
magazine_floor_rack[0].rotation = [0, 0, -1.565495585254728]
magazine_floor_rack[0].optimize = 2
mobile_medical_trolley[0].position = [5.599999904632568, 0.4000000059604645, 0.824999988079071]
mobile_medical_trolley[0].rotation = [0, 0, 1.5802211042556205]
mobile_medical_trolley[0].optimize = 2
waste_bin_B[0].position = [3.3499999046325684, 0.20000000298023224, 0.20000000298023224]
waste_bin_B[0].rotation = [0, 0, 1.5802211042556205]
waste_bin_B[0].optimize = 2
paper_notepad_A[0].position = [1.4500000476837158, 1.350000023841858, 0.7950000166893005]
paper_notepad_A[0].rotation = [0, 0, 0.09138689005137257]
paper_notepad_A[0].optimize = 2
magazine_stack_A[0].position = [6.800000190734863, 1.899999976158142, 0.5299999713897705]
magazine_stack_A[0].rotation = [0, 0, 0.022656744294196986]
magazine_stack_A[0].optimize = 2
portable_vital_signs_cart[0].position = [4.599999904632568, 0.4000000059604645, 0.6499999761581421]
portable_vital_signs_cart[0].rotation = [0, 0, 1.5802211042556205]
portable_vital_signs_cart[0].optimize = 2
wall_mounted_whiteboard[0].position = [2.0, 0.013662068173289299, 0.30000001192092896]
wall_mounted_whiteboard[0].rotation = [0, 0, 1.57501035161058]
wall_mounted_whiteboard[0].optimize = 2
wall_art_print_B[0].position = [2.5, 2.98199200630188, 0.22499999403953552]
wall_art_print_B[0].rotation = [0, 0, -1.5665822742141065]
wall_art_print_B[0].optimize = 2
document_box[0].position = [3.5, 2.7750000953674316, 1.9499999284744263]
document_box[0].rotation = [0, 0, -1.5888274408410739]
document_box[0].optimize = 2
desk_organizer_tray_A[0].position = [1.7999999523162842, 1.399999976158142, 0.7699999809265137]
desk_organizer_tray_A[0].rotation = [0, 0, 0.08908163463953815]
desk_organizer_tray_A[0].optimize = 2
wall_mounted_cabinet_B[0].position = [5.400000095367432, 0.1743355095386505, 0.32499998807907104]
wall_mounted_cabinet_B[0].rotation = [0, 0, 1.5750129000098558]
wall_mounted_cabinet_B[0].optimize = 2
desk_organizer_tray_B[0].position = [1.7999999523162842, 1.7999999523162842, 0.7699999809265137]
desk_organizer_tray_B[0].rotation = [0, 0, 0.09138689005137257]
desk_organizer_tray_B[0].optimize = 2
wall_mounted_glove_dispenser[0].position = [6.25, 0.056532155722379684, 0.07500000298023224]
wall_mounted_glove_dispenser[0].rotation = [0, 0, 1.575010582626228]
wall_mounted_glove_dispenser[0].optimize = 2
disinfectant_wipe_container[0].position = [4.0, 1.899999976158142, 0.6200000047683716]
disinfectant_wipe_container[0].rotation = [0, 0, 0.02337927994574165]
disinfectant_wipe_container[0].optimize = 2
wall_art_print_A[0].position = [1.2000000476837158, 2.98199200630188, 0.22499999403953552]
wall_art_print_A[0].rotation = [0, 0, -1.5665822742141065]
wall_art_print_A[0].optimize = 2
patient_guest_chair_B[0].position = [2.6500000953674316, 2.3499999046325684, 0.4000000059604645]
patient_guest_chair_B[0].rotation = [0, 0, -3.125884689672577]
patient_guest_chair_B[0].optimize = 2
desktop_computer_with_monitor[0].position = [1.4500000476837158, 2.25, 0.9650000333786011]
desktop_computer_with_monitor[0].rotation = [0, 0, -3.0502056569429383]
desktop_computer_with_monitor[0].optimize = 2
wall_art_print_C[0].position = [5.400000095367432, 2.98199200630188, 0.22499999403953552]
wall_art_print_C[0].rotation = [0, 0, -1.5665822742141065]
wall_art_print_C[0].optimize = 2
waste_bin_C[0].position = [6.400000095367432, 0.20000000298023224, 0.20000000298023224]
waste_bin_C[0].rotation = [0, 0, 1.5802211042556205]
waste_bin_C[0].optimize = 2
recycling_bin[0].position = [0.8500000238418579, 0.20000000298023224, 0.25]
recycling_bin[0].rotation = [0, 0, 1.5802211042556205]
recycling_bin[0].optimize = 2
examination_couch[0].position = [5.400000095367432, 1.899999976158142, 0.4000000059604645]
examination_couch[0].rotation = [0, 0, 0.02827433441159227]
examination_couch[0].optimize = 2
small_round_side_table_A[0].position = [4.0, 1.899999976158142, 0.25]
small_round_side_table_A[0].rotation = [0, 0, 0.021991148286022624]
small_round_side_table_A[0].optimize = 2
patient_guest_chair_A[0].position = [2.6500000953674316, 1.4500000476837158, 0.4000000059604645]
patient_guest_chair_A[0].rotation = [0, 0, -3.125884689672577]
patient_guest_chair_A[0].optimize = 2
tall_storage_cabinet[0].position = [3.5, 2.7760229110717773, 0.8999999761581421]
tall_storage_cabinet[0].rotation = [0, 0, -1.5654949929505533]
tall_storage_cabinet[0].optimize = 2
consultation_desk[0].position = [1.649999976158142, 1.899999976158142, 0.375]
consultation_desk[0].rotation = [0, 0, 0.06911503821575936]
consultation_desk[0].optimize = 2
waste_bin_A[0].position = [0.30000001192092896, 0.20000000298023224, 0.20000000298023224]
waste_bin_A[0].rotation = [0, 0, 1.5802211042556205]
waste_bin_A[0].optimize = 2
magazine_stack_B[0].position = [7.449999809265137, 2.8499999046325684, 1.0799999237060547]
magazine_stack_B[0].rotation = [0, 0, -1.5888256256485245]
magazine_stack_B[0].optimize = 2
paper_notepad_C[0].position = [6.800000190734863, 1.899999976158142, 0.5649999380111694]
paper_notepad_C[0].rotation = [0, 0, 0.01717856867246387]
paper_notepad_C[0].optimize = 2
mobile_exam_stool_A[0].position = [0.6499999761581421, 1.899999976158142, 0.2750000059604645]
mobile_exam_stool_A[0].rotation = [0, 0, 0.00942477746072377]
mobile_exam_stool_A[0].optimize = 2
clipboard_B[0].position = [1.4500000476837158, 1.7000000476837158, 0.7549999952316284]
clipboard_B[0].rotation = [0, 0, 0.09138689005137257]
clipboard_B[0].optimize = 2
umbrella_stand[0].position = [6.949999809265137, 2.799999952316284, 0.25]
umbrella_stand[0].rotation = [0, 0, -3.1321678761290697]
umbrella_stand[0].optimize = 2
coat_stand[0].position = [7.650000095367432, 2.049999952316284, 0.875]
coat_stand[0].rotation = [0, 0, -3.1321678761290697]
coat_stand[0].optimize = 2
pen_holder_with_pens[0].position = [1.850000023841858, 2.5, 0.8500000238418579]
pen_holder_with_pens[0].rotation = [0, 0, 0.09138689005137257]
pen_holder_with_pens[0].optimize = 2

