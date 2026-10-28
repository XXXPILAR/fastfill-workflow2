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
wall_art_print_A = Assets(description="Picture of trees by a lake in black picture frame.", size=[0.04, 0.80, 0.60], placements=[AssetInstance() for _ in range(1)])
paper_notepad_A = Assets(description="A box of kleenix wipes.", size=[0.29, 0.21, 0.02], placements=[AssetInstance() for _ in range(1)])
wall_mounted_cabinet_A = Assets(description="I brown cabinet with two doors.", size=[0.35, 0.90, 0.70], placements=[AssetInstance() for _ in range(1)])
disinfectant_wipe_container = Assets(description="A white bottle of shampoo with black and purple writing on it.", size=[0.08, 0.08, 0.22], placements=[AssetInstance() for _ in range(1)])
patient_guest_chair_A = Assets(description="A small gray chair with pinewood legs.", size=[0.58, 0.55, 0.82], placements=[AssetInstance() for _ in range(1)])
magazine_stack_A = Assets(description="Three purple books in a stack.", size=[0.32, 0.25, 0.08], placements=[AssetInstance() for _ in range(1)])
waste_bin_A = Assets(description="A cream colored trash can.", size=[0.30, 0.30, 0.45], placements=[AssetInstance() for _ in range(1)])
wall_mounted_cabinet_B = Assets(description="I brown cabinet with two doors.", size=[0.35, 0.90, 0.70], placements=[AssetInstance() for _ in range(1)])
desktop_computer_with_monitor = Assets(description="a computer monitor with a yellow screen.", size=[0.22, 0.55, 0.45], placements=[AssetInstance() for _ in range(1)])
coat_stand = Assets(description="The coatrack is wooden with a round bottom.", size=[0.45, 0.45, 1.80], placements=[AssetInstance() for _ in range(1)])
portable_vital_signs_cart = Assets(description="a blue, pixelated robot with a computer monitor on wheels and a green screen.", size=[0.60, 0.60, 1.40], placements=[AssetInstance() for _ in range(1)])
document_box = Assets(description="A carboard box with side openings for handles and one of the flaps raised with tape on it and tape on the second sealed flap.", size=[0.40, 0.50, 0.35], placements=[AssetInstance() for _ in range(1)])
pen_holder_with_pens = Assets(description="A cylindrical gray cup with two pens and a pencil sticking out.", size=[0.09, 0.09, 0.18], placements=[AssetInstance() for _ in range(1)])
umbrella_stand = Assets(description="A gray and black mesh speaker.", size=[0.28, 0.28, 0.55], placements=[AssetInstance() for _ in range(1)])
patient_guest_chair_B = Assets(description="A small gray chair with pinewood legs.", size=[0.58, 0.55, 0.82], placements=[AssetInstance() for _ in range(1)])
mobile_exam_stool_A = Assets(description="A rusted metal stool or low office chair with four casters.", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
small_round_side_table_A = Assets(description="A light colored stool with three legs.", size=[0.45, 0.45, 0.48], placements=[AssetInstance() for _ in range(1)])
tall_storage_cabinet = Assets(description="A cabinet with four doors.", size=[0.45, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
mobile_exam_stool_B = Assets(description="A rusted metal stool or low office chair with four casters.", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
clipboard_A = Assets(description="A black cellular telephone.", size=[0.33, 0.23, 0.02], placements=[AssetInstance() for _ in range(1)])
wall_art_print_B = Assets(description="Picture of trees by a lake in black picture frame.", size=[0.04, 0.80, 0.60], placements=[AssetInstance() for _ in range(1)])
desk_organizer_tray_A = Assets(description="A tray for carrying food.", size=[0.25, 0.35, 0.06], placements=[AssetInstance() for _ in range(1)])
wall_mounted_whiteboard = Assets(description="A poster of blueprints for a picture frame.", size=[0.04, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
paper_notepad_B = Assets(description="A pink spiral notebook with a green leaf on it.", size=[0.29, 0.21, 0.02], placements=[AssetInstance() for _ in range(1)])
clipboard_B = Assets(description="A handheld phone with a large touchscreen.", size=[0.33, 0.23, 0.02], placements=[AssetInstance() for _ in range(1)])
wall_clock = Assets(description="A round gray wall clock.", size=[0.05, 0.35, 0.35], placements=[AssetInstance() for _ in range(1)])
magazine_floor_rack = Assets(description="A set of magazine shelves for displaying booksq.", size=[0.35, 0.70, 1.20], placements=[AssetInstance() for _ in range(1)])
small_round_side_table_B = Assets(description="A light colored stool with three legs.", size=[0.45, 0.45, 0.48], placements=[AssetInstance() for _ in range(1)])
paper_notepad_C = Assets(description="A red notepad decorated with a slug in the lower corner.", size=[0.21, 0.15, 0.02], placements=[AssetInstance() for _ in range(1)])
waste_bin_B = Assets(description="A cream colored trash can.", size=[0.30, 0.30, 0.45], placements=[AssetInstance() for _ in range(1)])
mobile_medical_trolley = Assets(description="A hospital cart with a set of clear drawers, iv pole and a red biohazard disposal container.", size=[0.55, 0.65, 1.40], placements=[AssetInstance() for _ in range(1)])
desk_organizer_tray_B = Assets(description="A brown leather card holder with a logo on it.", size=[0.18, 0.30, 0.08], placements=[AssetInstance() for _ in range(1)])
wall_art_print_C = Assets(description="Picture of trees by a lake in black picture frame.", size=[0.04, 0.80, 0.60], placements=[AssetInstance() for _ in range(1)])
recycling_bin = Assets(description="recycling bin", size=[0.35, 0.40, 0.60], placements=[AssetInstance() for _ in range(1)])
examination_couch = Assets(description="Wood frame lawn chair with a white cushion.", size=[0.70, 1.90, 0.75], placements=[AssetInstance() for _ in range(1)])
waste_bin_C = Assets(description="A cream colored trash can.", size=[0.30, 0.30, 0.45], placements=[AssetInstance() for _ in range(1)])
wall_mounted_glove_dispenser = Assets(description="A white box with the top open.", size=[0.12, 0.28, 0.15], placements=[AssetInstance() for _ in range(1)])
magazine_stack_B = Assets(description="Three purple books in a stack.", size=[0.32, 0.25, 0.08], placements=[AssetInstance() for _ in range(1)])

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

consultation_desk[0].position = [6.188685773154948, 0.3426415473092159, 0.375]
consultation_desk[0].rotation = [0, 0, 0]
wall_art_print_A[0].position = [5.6982892692510125, 1.8192103279013905, 0.3]
wall_art_print_A[0].rotation = [0, 0, 0]
paper_notepad_A[0].position = [6.7598553052952575, 0.8860097221065019, 0.01]
paper_notepad_A[0].rotation = [0, 0, 0]
wall_mounted_cabinet_A[0].position = [7.205760496677626, 1.9221069594015499, 0.35]
wall_mounted_cabinet_A[0].rotation = [0, 0, 0]
disinfectant_wipe_container[0].position = [3.825560145793018, 1.9966850945130235, 0.11]
disinfectant_wipe_container[0].rotation = [0, 0, 0]
patient_guest_chair_A[0].position = [4.027298538481281, 0.99567173807373, 0.41]
patient_guest_chair_A[0].rotation = [0, 0, 0]
magazine_stack_A[0].position = [7.065967629345167, 2.9770011863778643, 0.04]
magazine_stack_A[0].rotation = [0, 0, 0]
waste_bin_A[0].position = [7.557786284518791, 0.31884197659737656, 0.225]
waste_bin_A[0].rotation = [0, 0, 0]
wall_mounted_cabinet_B[0].position = [0.5175357910045628, 1.2413791497573872, 0.35]
wall_mounted_cabinet_B[0].rotation = [0, 0, 0]
desktop_computer_with_monitor[0].position = [5.998049861368114, 0.8719685693399043, 0.225]
desktop_computer_with_monitor[0].rotation = [0, 0, 0]
coat_stand[0].position = [3.5986460478611226, 0.6365025680949362, 0.9]
coat_stand[0].rotation = [0, 0, 0]
portable_vital_signs_cart[0].position = [0.41688039693647116, 2.475454864166683, 0.7]
portable_vital_signs_cart[0].rotation = [0, 0, 0]
document_box[0].position = [4.034624497870201, 2.651615349537579, 0.175]
document_box[0].rotation = [0, 0, 0]
pen_holder_with_pens[0].position = [7.3814424039620965, 0.3121179572449816, 0.09]
pen_holder_with_pens[0].rotation = [0, 0, 0]
umbrella_stand[0].position = [3.4090514357377284, 2.193596299047949, 0.275]
umbrella_stand[0].rotation = [0, 0, 0]
patient_guest_chair_B[0].position = [2.627816305215762, 2.717843737759484, 0.41]
patient_guest_chair_B[0].rotation = [0, 0, 0]
mobile_exam_stool_A[0].position = [0.33383684503823385, 2.2757326846869166, 0.275]
mobile_exam_stool_A[0].rotation = [0, 0, 0]
small_round_side_table_A[0].position = [6.714322541483896, 1.798302587497951, 0.24]
small_round_side_table_A[0].rotation = [0, 0, 0]
tall_storage_cabinet[0].position = [2.4243964043554325, 0.7070907591424439, 0.9]
tall_storage_cabinet[0].rotation = [0, 0, 0]
mobile_exam_stool_B[0].position = [6.113824074247509, 1.6563976829340707, 0.275]
mobile_exam_stool_B[0].rotation = [0, 0, 0]
clipboard_A[0].position = [1.2479117226947931, 0.8748884848406808, 0.01]
clipboard_A[0].rotation = [0, 0, 0]
wall_art_print_B[0].position = [4.217355677219356, 1.581132723537777, 0.3]
wall_art_print_B[0].rotation = [0, 0, 0]
desk_organizer_tray_A[0].position = [2.0631562558067467, 0.3417593061002524, 0.03]
desk_organizer_tray_A[0].rotation = [0, 0, 0]
wall_mounted_whiteboard[0].position = [1.1672236535321465, 2.1953695803748836, 0.45]
wall_mounted_whiteboard[0].rotation = [0, 0, 0]
paper_notepad_B[0].position = [5.108777099571649, 0.09528437296221537, 0.01]
paper_notepad_B[0].rotation = [0, 0, 0]
clipboard_B[0].position = [3.4863315207650754, 0.3908804041329542, 0.01]
clipboard_B[0].rotation = [0, 0, 0]
wall_clock[0].position = [6.623690342902941, 1.8411259451143258, 0.175]
wall_clock[0].rotation = [0, 0, 0]
magazine_floor_rack[0].position = [1.4362519438028132, 1.5615684878000065, 0.6]
magazine_floor_rack[0].rotation = [0, 0, 0]
small_round_side_table_B[0].position = [6.792311251469294, 2.5167501513821326, 0.24]
small_round_side_table_B[0].rotation = [0, 0, 0]
paper_notepad_C[0].position = [7.164232377968208, 2.001947046897171, 0.01]
paper_notepad_C[0].rotation = [0, 0, 0]
waste_bin_B[0].position = [2.6738157028558147, 1.2549714000047398, 0.225]
waste_bin_B[0].rotation = [0, 0, 0]
mobile_medical_trolley[0].position = [1.1322206382342879, 2.8183794195905434, 0.7]
mobile_medical_trolley[0].rotation = [0, 0, 0]
desk_organizer_tray_B[0].position = [3.197918233489684, 2.809997829305324, 0.04]
desk_organizer_tray_B[0].rotation = [0, 0, 0]
wall_art_print_C[0].position = [7.539516722939401, 1.7636045500659385, 0.3]
wall_art_print_C[0].rotation = [0, 0, 0]
recycling_bin[0].position = [2.2094068893441445, 0.9001960028823229, 0.3]
recycling_bin[0].rotation = [0, 0, 0]
examination_couch[0].position = [3.9486566669627194, 0.7160309948001855, 0.375]
examination_couch[0].rotation = [0, 0, 0]
waste_bin_C[0].position = [1.9812080463328012, 2.353568317814341, 0.225]
waste_bin_C[0].rotation = [0, 0, 0]
wall_mounted_glove_dispenser[0].position = [3.980107194437461, 1.992278362979103, 0.075]
wall_mounted_glove_dispenser[0].rotation = [0, 0, 0]
magazine_stack_B[0].position = [7.122155994141958, 2.3748414311561574, 0.04]
magazine_stack_B[0].rotation = [0, 0, 0]
consultation_desk[0].position = [6.188685773154948, 0.3426415473092159, 0.375]
consultation_desk[0].rotation = [0, 0, 0]
wall_art_print_A[0].position = [5.6982892692510125, 1.8192103279013905, 0.3]
wall_art_print_A[0].rotation = [0, 0, 0]
paper_notepad_A[0].position = [6.7598553052952575, 0.8860097221065019, 0.01]
paper_notepad_A[0].rotation = [0, 0, 0]
wall_mounted_cabinet_A[0].position = [7.205760496677626, 1.9221069594015499, 0.35]
wall_mounted_cabinet_A[0].rotation = [0, 0, 0]
disinfectant_wipe_container[0].position = [3.825560145793018, 1.9966850945130235, 0.11]
disinfectant_wipe_container[0].rotation = [0, 0, 0]
patient_guest_chair_A[0].position = [4.027298538481281, 0.99567173807373, 0.41]
patient_guest_chair_A[0].rotation = [0, 0, 0]
magazine_stack_A[0].position = [7.065967629345167, 2.9770011863778643, 0.04]
magazine_stack_A[0].rotation = [0, 0, 0]
waste_bin_A[0].position = [7.557786284518791, 0.31884197659737656, 0.225]
waste_bin_A[0].rotation = [0, 0, 0]
wall_mounted_cabinet_B[0].position = [0.5175357910045628, 1.2413791497573872, 0.35]
wall_mounted_cabinet_B[0].rotation = [0, 0, 0]
desktop_computer_with_monitor[0].position = [5.998049861368114, 0.8719685693399043, 0.225]
desktop_computer_with_monitor[0].rotation = [0, 0, 0]
coat_stand[0].position = [3.5986460478611226, 0.6365025680949362, 0.9]
coat_stand[0].rotation = [0, 0, 0]
portable_vital_signs_cart[0].position = [0.41688039693647116, 2.475454864166683, 0.7]
portable_vital_signs_cart[0].rotation = [0, 0, 0]
document_box[0].position = [4.034624497870201, 2.651615349537579, 0.175]
document_box[0].rotation = [0, 0, 0]
pen_holder_with_pens[0].position = [7.3814424039620965, 0.3121179572449816, 0.09]
pen_holder_with_pens[0].rotation = [0, 0, 0]
umbrella_stand[0].position = [3.4090514357377284, 2.193596299047949, 0.275]
umbrella_stand[0].rotation = [0, 0, 0]
patient_guest_chair_B[0].position = [2.627816305215762, 2.717843737759484, 0.41]
patient_guest_chair_B[0].rotation = [0, 0, 0]
mobile_exam_stool_A[0].position = [0.33383684503823385, 2.2757326846869166, 0.275]
mobile_exam_stool_A[0].rotation = [0, 0, 0]
small_round_side_table_A[0].position = [6.714322541483896, 1.798302587497951, 0.24]
small_round_side_table_A[0].rotation = [0, 0, 0]
tall_storage_cabinet[0].position = [2.4243964043554325, 0.7070907591424439, 0.9]
tall_storage_cabinet[0].rotation = [0, 0, 0]
mobile_exam_stool_B[0].position = [6.113824074247509, 1.6563976829340707, 0.275]
mobile_exam_stool_B[0].rotation = [0, 0, 0]
clipboard_A[0].position = [1.2479117226947931, 0.8748884848406808, 0.01]
clipboard_A[0].rotation = [0, 0, 0]
wall_art_print_B[0].position = [4.217355677219356, 1.581132723537777, 0.3]
wall_art_print_B[0].rotation = [0, 0, 0]
desk_organizer_tray_A[0].position = [2.0631562558067467, 0.3417593061002524, 0.03]
desk_organizer_tray_A[0].rotation = [0, 0, 0]
wall_mounted_whiteboard[0].position = [1.1672236535321465, 2.1953695803748836, 0.45]
wall_mounted_whiteboard[0].rotation = [0, 0, 0]
paper_notepad_B[0].position = [5.108777099571649, 0.09528437296221537, 0.01]
paper_notepad_B[0].rotation = [0, 0, 0]
clipboard_B[0].position = [3.4863315207650754, 0.3908804041329542, 0.01]
clipboard_B[0].rotation = [0, 0, 0]
wall_clock[0].position = [6.623690342902941, 1.8411259451143258, 0.175]
wall_clock[0].rotation = [0, 0, 0]
magazine_floor_rack[0].position = [1.4362519438028132, 1.5615684878000065, 0.6]
magazine_floor_rack[0].rotation = [0, 0, 0]
small_round_side_table_B[0].position = [6.792311251469294, 2.5167501513821326, 0.24]
small_round_side_table_B[0].rotation = [0, 0, 0]
paper_notepad_C[0].position = [7.164232377968208, 2.001947046897171, 0.01]
paper_notepad_C[0].rotation = [0, 0, 0]
waste_bin_B[0].position = [2.6738157028558147, 1.2549714000047398, 0.225]
waste_bin_B[0].rotation = [0, 0, 0]
mobile_medical_trolley[0].position = [1.1322206382342879, 2.8183794195905434, 0.7]
mobile_medical_trolley[0].rotation = [0, 0, 0]
desk_organizer_tray_B[0].position = [3.197918233489684, 2.809997829305324, 0.04]
desk_organizer_tray_B[0].rotation = [0, 0, 0]
wall_art_print_C[0].position = [7.539516722939401, 1.7636045500659385, 0.3]
wall_art_print_C[0].rotation = [0, 0, 0]
recycling_bin[0].position = [2.2094068893441445, 0.9001960028823229, 0.3]
recycling_bin[0].rotation = [0, 0, 0]
examination_couch[0].position = [3.9486566669627194, 0.7160309948001855, 0.375]
examination_couch[0].rotation = [0, 0, 0]
waste_bin_C[0].position = [1.9812080463328012, 2.353568317814341, 0.225]
waste_bin_C[0].rotation = [0, 0, 0]
wall_mounted_glove_dispenser[0].position = [3.980107194437461, 1.992278362979103, 0.075]
wall_mounted_glove_dispenser[0].rotation = [0, 0, 0]
magazine_stack_B[0].position = [7.122155994141958, 2.3748414311561574, 0.04]
magazine_stack_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Explicit placements use the room coordinates shown in the floor plan.
# The right-wall doorway (x=8, y=0.44...1.48) and its approach are left clear.

def set_placement(asset_group, position, angle_degrees):
    asset_group[0].position = position
    asset_group[0].rotation = [0, 0, radians(angle_degrees)]


# Main consultation/examination arrangement. The desk faces north toward the
# examination couch, which is centered between the two round side tables.
set_placement(consultation_desk, [4.30, 0.40, 0.375], 90)
set_placement(examination_couch, [4.30, 1.55, 0.375], 90)
set_placement(small_round_side_table_A, [3.00, 1.55, 0.24], 0)
set_placement(small_round_side_table_B, [5.60, 1.55, 0.24], 0)

# Guest seating is in the open left portion of the room, directed toward the
# consultation desk without obstructing the examination area.
set_placement(patient_guest_chair_A, [1.10, 0.95, 0.41], -11)
set_placement(patient_guest_chair_B, [2.00, 0.95, 0.41], -15)

# Mobile stools are accessible from the head/upper side of the couch.
set_placement(mobile_exam_stool_A, [3.25, 2.43, 0.275], -90)
set_placement(mobile_exam_stool_B, [3.85, 2.43, 0.275], -90)

# Floor storage and clinical equipment are arranged along the upper wall.
set_placement(tall_storage_cabinet, [0.60, 2.775, 0.90], -90)
set_placement(magazine_floor_rack, [4.55, 2.825, 0.60], -90)
set_placement(mobile_medical_trolley, [5.25, 2.675, 0.70], -90)
set_placement(portable_vital_signs_cart, [6.00, 2.70, 0.70], -90)
set_placement(umbrella_stand, [7.18, 2.72, 0.275], -90)
set_placement(coat_stand, [7.68, 2.72, 0.90], -90)

# Bins stay around the lower perimeter and do not intrude on the doorway.
set_placement(waste_bin_A, [2.80, 0.18, 0.225], 90)
set_placement(waste_bin_B, [5.43, 0.18, 0.225], 90)
set_placement(waste_bin_C, [5.85, 0.18, 0.225], 90)
set_placement(recycling_bin, [6.30, 0.20, 0.30], 90)

# Desk-top equipment. Separating the objects into front and rear rows avoids
# overlap while keeping the monitor centered for the clinician.
set_placement(desktop_computer_with_monitor, [4.30, 0.56, 0.975], 90)
set_placement(desk_organizer_tray_A, [3.72, 0.24, 0.78], 90)
set_placement(paper_notepad_A, [4.14, 0.22, 0.76], 0)
set_placement(desk_organizer_tray_B, [4.52, 0.22, 0.79], 0)
set_placement(pen_holder_with_pens, [4.85, 0.22, 0.84], 0)

# The document box is stored on the tall cabinet.
set_placement(document_box, [0.60, 2.775, 1.975], -90)

# Frequently used disinfectant is carried on the medical trolley.
set_placement(disinfectant_wipe_container, [5.25, 2.675, 1.51], -90)

# Reading/writing material is stacked neatly on the two side tables.
set_placement(magazine_stack_A, [3.00, 1.55, 0.52], 0)
set_placement(clipboard_A, [3.00, 1.55, 0.57], 0)
set_placement(paper_notepad_B, [3.00, 1.55, 0.59], 0)

set_placement(magazine_stack_B, [5.60, 1.55, 0.52], 0)
set_placement(clipboard_B, [5.60, 1.55, 0.57], 0)
set_placement(paper_notepad_C, [5.60, 1.55, 0.59], 0)

# Wall-mounted storage is placed on the upper wall, away from both left-wall
# windows. The cabinet centers are high enough to leave useful clearance below.
set_placement(wall_mounted_cabinet_A, [1.70, 2.825, 1.65], -90)
set_placement(wall_mounted_cabinet_B, [2.65, 2.825, 1.65], -90)
set_placement(wall_mounted_whiteboard, [3.75, 2.98, 1.82], -90)
set_placement(wall_clock, [6.55, 2.975, 2.20], -90)
set_placement(wall_mounted_glove_dispenser, [7.10, 2.94, 1.55], -90)

# Artwork uses the lower wall, preserving both left-wall windows.
set_placement(wall_art_print_A, [0.75, 0.02, 1.65], 90)
set_placement(wall_art_print_B, [1.70, 0.02, 1.65], 90)
set_placement(wall_art_print_C, [6.45, 0.02, 1.65], 90)


# Pin every new asset near its intended location. These strong constraints
# preserve clearances and the deliberate grouping if the solver adjusts layout.
all_new_assets = [
    consultation_desk,
    wall_art_print_A,
    paper_notepad_A,
    wall_mounted_cabinet_A,
    disinfectant_wipe_container,
    patient_guest_chair_A,
    magazine_stack_A,
    waste_bin_A,
    wall_mounted_cabinet_B,
    desktop_computer_with_monitor,
    coat_stand,
    portable_vital_signs_cart,
    document_box,
    pen_holder_with_pens,
    umbrella_stand,
    patient_guest_chair_B,
    mobile_exam_stool_A,
    small_round_side_table_A,
    tall_storage_cabinet,
    mobile_exam_stool_B,
    clipboard_A,
    wall_art_print_B,
    desk_organizer_tray_A,
    wall_mounted_whiteboard,
    paper_notepad_B,
    clipboard_B,
    wall_clock,
    magazine_floor_rack,
    small_round_side_table_B,
    paper_notepad_C,
    waste_bin_B,
    mobile_medical_trolley,
    desk_organizer_tray_B,
    wall_art_print_C,
    recycling_bin,
    examination_couch,
    waste_bin_C,
    wall_mounted_glove_dispenser,
    magazine_stack_B,
]

for placed_asset_group in all_new_assets:
    intended_position = list(placed_asset_group[0].position)
    position_anchor = AssetInstance(position=intended_position)
    solver.distance_constraint(
        placed_asset_group[0],
        position_anchor,
        0,
        0,
        weight=10,
    )


# Important orientation semantics are stated first. The consultation desk faces
# the couch, and both guest chairs face the consultation desk.
solver.point_towards(consultation_desk[0], examination_couch[0])
solver.point_towards(patient_guest_chair_A[0], consultation_desk[0])
solver.point_towards(patient_guest_chair_B[0], consultation_desk[0])

# Fixed orientation references preserve the intended wall alignment and the
# orderly parallel arrangement of the remaining furniture.
orientation_x = AssetInstance(rotation=[0, 0, radians(0)])
orientation_north = AssetInstance(rotation=[0, 0, radians(90)])
orientation_south = AssetInstance(rotation=[0, 0, radians(-90)])

north_facing_assets = [
    wall_art_print_A,
    wall_art_print_B,
    wall_art_print_C,
    waste_bin_A,
    waste_bin_B,
    waste_bin_C,
    recycling_bin,
    desktop_computer_with_monitor,
    desk_organizer_tray_A,
    consultation_desk,
    examination_couch,
]

south_facing_assets = [
    wall_mounted_cabinet_A,
    wall_mounted_cabinet_B,
    wall_mounted_whiteboard,
    wall_clock,
    wall_mounted_glove_dispenser,
    tall_storage_cabinet,
    magazine_floor_rack,
    mobile_medical_trolley,
    portable_vital_signs_cart,
    coat_stand,
    umbrella_stand,
    document_box,
    disinfectant_wipe_container,
    mobile_exam_stool_A,
    mobile_exam_stool_B,
]

x_aligned_assets = [
    small_round_side_table_A,
    small_round_side_table_B,
    paper_notepad_A,
    desk_organizer_tray_B,
    pen_holder_with_pens,
    magazine_stack_A,
    clipboard_A,
    paper_notepad_B,
    magazine_stack_B,
    clipboard_B,
    paper_notepad_C,
]

# The desk already has its higher-priority point-towards constraint.
for north_facing_group in north_facing_assets:
    if north_facing_group is not consultation_desk:
        solver.align_with(north_facing_group[0], orientation_north)

for south_facing_group in south_facing_assets:
    solver.align_with(south_facing_group[0], orientation_south)

for x_aligned_group in x_aligned_assets:
    solver.align_with(x_aligned_group[0], orientation_x)


# Wall constraints preserve the perimeter organization. Nothing is attached to
# the left wall because its two windows occupy nearly the entire wall.
for lower_wall_group in [
    consultation_desk,
    wall_art_print_A,
    wall_art_print_B,
    wall_art_print_C,
    waste_bin_A,
    waste_bin_B,
    waste_bin_C,
    recycling_bin,
]:
    solver.against_wall(lower_wall_group[0], walls[0])

for upper_wall_group in [
    tall_storage_cabinet,
    wall_mounted_cabinet_A,
    wall_mounted_cabinet_B,
    wall_mounted_whiteboard,
    magazine_floor_rack,
    mobile_medical_trolley,
    portable_vital_signs_cart,
    wall_clock,
    wall_mounted_glove_dispenser,
    umbrella_stand,
    coat_stand,
]:
    solver.against_wall(upper_wall_group[0], walls[2])


# Required and functional support relationships for all small loose objects.
solver.on_top_of(desk_organizer_tray_A[0], consultation_desk[0])
solver.on_top_of(desk_organizer_tray_B[0], consultation_desk[0])
solver.on_top_of(desktop_computer_with_monitor[0], consultation_desk[0])
solver.on_top_of(paper_notepad_A[0], consultation_desk[0])
solver.on_top_of(pen_holder_with_pens[0], consultation_desk[0])

solver.on_top_of(document_box[0], tall_storage_cabinet[0])
solver.on_top_of(disinfectant_wipe_container[0], mobile_medical_trolley[0])

solver.on_top_of(magazine_stack_A[0], small_round_side_table_A[0])
solver.on_top_of(clipboard_A[0], magazine_stack_A[0])
solver.on_top_of(paper_notepad_B[0], clipboard_A[0])

solver.on_top_of(magazine_stack_B[0], small_round_side_table_B[0])
solver.on_top_of(clipboard_B[0], magazine_stack_B[0])
solver.on_top_of(paper_notepad_C[0], clipboard_B[0])


# Preserve the specified "couch between side tables" relationship. The equal
# center distances maintain a balanced arrangement without touching the couch.
solver.distance_constraint(
    examination_couch[0], small_round_side_table_A[0], 1.25, 1.35, weight=10
)
solver.distance_constraint(
    examination_couch[0], small_round_side_table_B[0], 1.25, 1.35, weight=10
)

# Keep useful working clearances around the couch and consultation seating.
solver.distance_constraint(
    mobile_exam_stool_A[0], examination_couch[0], 0.95, 1.25, weight=1
)
solver.distance_constraint(
    mobile_exam_stool_B[0], examination_couch[0], 0.85, 1.15, weight=1
)
solver.distance_constraint(
    patient_guest_chair_A[0], consultation_desk[0], 2.9, 3.4, weight=1
)
solver.distance_constraint(
    patient_guest_chair_B[0], consultation_desk[0], 2.1, 2.7, weight=1
)

solver.constraints = []
wall_mounted_cabinet_B[0].position = [2.6500000953674316, 2.823857069015503, 0.3499999940395355]
wall_mounted_cabinet_B[0].rotation = [0, 0, -1.568255412632856]
wall_mounted_cabinet_B[0].optimize = 2
portable_vital_signs_cart[0].position = [6.0, 2.6992387771606445, 0.699999988079071]
portable_vital_signs_cart[0].rotation = [0, 0, -1.5682554083443117]
portable_vital_signs_cart[0].optimize = 2
waste_bin_C[0].position = [5.849999904632568, 0.1700000911951065, 0.22499999403953552]
waste_bin_C[0].rotation = [0, 0, 1.573337248311928]
waste_bin_C[0].optimize = 2
pen_holder_with_pens[0].position = [4.849999904632568, 0.2199999988079071, 0.8400000333786011]
pen_holder_with_pens[0].rotation = [0, 0, 0.01256637125682779]
pen_holder_with_pens[0].optimize = 2
wall_mounted_whiteboard[0].position = [3.75, 2.978475570678711, 0.44999998807907104]
wall_mounted_whiteboard[0].rotation = [0, 0, -1.5682554162991507]
wall_mounted_whiteboard[0].optimize = 2
document_box[0].position = [0.6000000238418579, 2.7750000953674316, 1.9749999046325684]
document_box[0].rotation = [0, 0, -1.5582299555380688]
document_box[0].optimize = 2
tall_storage_cabinet[0].position = [0.6099985837936401, 2.7716126441955566, 0.8999999761581421]
tall_storage_cabinet[0].rotation = [0, 0, -1.5651448129019523]
tall_storage_cabinet[0].optimize = 2
mobile_exam_stool_A[0].position = [3.25, 2.430000066757202, 0.2750000059604645]
mobile_exam_stool_A[0].rotation = [0, 0, -1.5582299555380688]
mobile_exam_stool_A[0].optimize = 2
consultation_desk[0].position = [4.300000190734863, 0.3900001049041748, 0.375]
consultation_desk[0].rotation = [0, 0, 1.6013361958132144]
consultation_desk[0].optimize = 2
wall_art_print_A[0].position = [0.75, 0.011367769911885262, 0.30000001192092896]
wall_art_print_A[0].rotation = [0, 0, 1.5733372437234565]
wall_art_print_A[0].optimize = 2
waste_bin_B[0].position = [5.429999828338623, 0.1700000911951065, 0.22499999403953552]
waste_bin_B[0].rotation = [0, 0, 1.573337248311928]
waste_bin_B[0].optimize = 2
recycling_bin[0].position = [6.300000190734863, 0.19000010192394257, 0.30000001192092896]
recycling_bin[0].rotation = [0, 0, 1.573337248311928]
recycling_bin[0].optimize = 2
wall_mounted_glove_dispenser[0].position = [7.099999904632568, 2.9494898319244385, 0.07500000298023224]
wall_mounted_glove_dispenser[0].rotation = [0, 0, -1.5682554052778654]
wall_mounted_glove_dispenser[0].optimize = 2
small_round_side_table_B[0].position = [5.599999904632568, 1.5499999523162842, 0.23999999463558197]
small_round_side_table_B[0].rotation = [0, 0, 0.0157079639172164]
small_round_side_table_B[0].optimize = 2
paper_notepad_A[0].position = [4.139999866485596, 0.2199999988079071, 0.7599999904632568]
paper_notepad_A[0].rotation = [0, 0, 0.01256637125682779]
paper_notepad_A[0].optimize = 2
magazine_stack_A[0].position = [3.0, 1.5499999523162842, 0.5199999809265137]
magazine_stack_A[0].rotation = [0, 0, 0.0157079639172164]
magazine_stack_A[0].optimize = 2
wall_art_print_B[0].position = [1.7000000476837158, 0.011367769911885262, 0.30000001192092896]
wall_art_print_B[0].rotation = [0, 0, 1.5733372437234565]
wall_art_print_B[0].optimize = 2
coat_stand[0].position = [7.679999828338623, 2.7300000190734863, 0.8999999761581421]
coat_stand[0].rotation = [0, 0, -1.5682554064999652]
coat_stand[0].optimize = 2
wall_art_print_C[0].position = [6.449999809265137, 0.011367769911885262, 0.30000001192092896]
wall_art_print_C[0].rotation = [0, 0, 1.5733372437234565]
wall_art_print_C[0].optimize = 2
paper_notepad_C[0].position = [5.599999904632568, 1.5499999523162842, 0.5899999737739563]
paper_notepad_C[0].rotation = [0, 0, 0.01256637125682779]
paper_notepad_C[0].optimize = 2
magazine_floor_rack[0].position = [4.550000190734863, 2.824111223220825, 0.6000000238418579]
magazine_floor_rack[0].rotation = [0, 0, -1.5682554086442377]
magazine_floor_rack[0].optimize = 2
waste_bin_A[0].position = [2.799999952316284, 0.1700000911951065, 0.22499999403953552]
waste_bin_A[0].rotation = [0, 0, 1.573337248311928]
waste_bin_A[0].optimize = 2
examination_couch[0].position = [4.300000190734863, 1.5499999523162842, 0.375]
examination_couch[0].rotation = [0, 0, 1.5959290669047523]
examination_couch[0].optimize = 2
wall_mounted_cabinet_A[0].position = [1.7000000476837158, 2.823857069015503, 0.3499999940395355]
wall_mounted_cabinet_A[0].rotation = [0, 0, -1.568255412632856]
wall_mounted_cabinet_A[0].optimize = 2
desktop_computer_with_monitor[0].position = [4.300000190734863, 0.5600000023841858, 0.9750000238418579]
desktop_computer_with_monitor[0].rotation = [0, 0, 1.5833626980517244]
desktop_computer_with_monitor[0].optimize = 2
mobile_exam_stool_B[0].position = [3.8499999046325684, 2.430000066757202, 0.2750000059604645]
mobile_exam_stool_B[0].rotation = [0, 0, -1.5582299555380688]
mobile_exam_stool_B[0].optimize = 2
desk_organizer_tray_A[0].position = [3.7200000286102295, 0.23999999463558197, 0.7799999713897705]
desk_organizer_tray_A[0].rotation = [0, 0, 1.5833626980517244]
desk_organizer_tray_A[0].optimize = 2
paper_notepad_B[0].position = [3.0, 1.5499999523162842, 0.5899999737739563]
paper_notepad_B[0].rotation = [0, 0, 0.01256637125682779]
paper_notepad_B[0].optimize = 2
mobile_medical_trolley[0].position = [5.25, 2.684999942779541, 0.699999988079071]
mobile_medical_trolley[0].rotation = [0, 0, -1.5651448053674857]
mobile_medical_trolley[0].optimize = 2
disinfectant_wipe_container[0].position = [5.25, 2.674999952316284, 1.5099999904632568]
disinfectant_wipe_container[0].rotation = [0, 0, -1.5582299555380688]
disinfectant_wipe_container[0].optimize = 2
wall_clock[0].position = [6.550000190734863, 2.9839017391204834, 0.17499999701976776]
wall_clock[0].rotation = [0, 0, -1.5682554052778654]
wall_clock[0].optimize = 2
clipboard_A[0].position = [3.0, 1.5499999523162842, 0.5699999928474426]
clipboard_A[0].rotation = [0, 0, 0.0157079639172164]
clipboard_A[0].optimize = 2
patient_guest_chair_B[0].position = [2.0, 0.949999988079071, 0.4099999964237213]
patient_guest_chair_B[0].rotation = [0, 0, -0.24923302009629125]
patient_guest_chair_B[0].optimize = 2
desk_organizer_tray_B[0].position = [4.519999980926514, 0.2199999988079071, 0.7900000214576721]
desk_organizer_tray_B[0].rotation = [0, 0, 0.01256637125682779]
desk_organizer_tray_B[0].optimize = 2
small_round_side_table_A[0].position = [3.0, 1.5499999523162842, 0.23999999463558197]
small_round_side_table_A[0].rotation = [0, 0, 0.0157079639172164]
small_round_side_table_A[0].optimize = 2
patient_guest_chair_A[0].position = [1.100000023841858, 0.949999988079071, 0.4099999964237213]
patient_guest_chair_A[0].rotation = [0, 0, -0.17941984785575782]
patient_guest_chair_A[0].optimize = 2
magazine_stack_B[0].position = [5.599999904632568, 1.5499999523162842, 0.5199999809265137]
magazine_stack_B[0].rotation = [0, 0, 0.0157079639172164]
magazine_stack_B[0].optimize = 2
clipboard_B[0].position = [5.599999904632568, 1.5499999523162842, 0.5699999928474426]
clipboard_B[0].rotation = [0, 0, 0.0157079639172164]
clipboard_B[0].optimize = 2
umbrella_stand[0].position = [7.179999828338623, 2.7300000190734863, 0.2750000059604645]
umbrella_stand[0].rotation = [0, 0, -1.568255406200039]
umbrella_stand[0].optimize = 2

