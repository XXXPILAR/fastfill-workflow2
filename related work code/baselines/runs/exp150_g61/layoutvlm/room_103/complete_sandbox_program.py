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
    Wall(corner1=[0.00, 5.00, 0.00], corner2=[2.00, 5.00, 0.00]),
    Wall(corner1=[2.00, 5.00, 0.00], corner2=[2.00, 1.00, 0.00]),
    Wall(corner1=[2.00, 1.00, 0.00], corner2=[4.00, 1.00, 0.00]),
    Wall(corner1=[4.00, 1.00, 0.00], corner2=[4.00, 0.00, 0.00]),
    Wall(corner1=[4.00, 0.00, 0.00], corner2=[8.00, 0.00, 0.00]),
    Wall(corner1=[8.00, 0.00, 0.00], corner2=[8.00, 12.00, 0.00]),
    Wall(corner1=[8.00, 12.00, 0.00], corner2=[2.00, 12.00, 0.00]),
    Wall(corner1=[2.00, 12.00, 0.00], corner2=[2.00, 13.00, 0.00]),
    Wall(corner1=[2.00, 13.00, 0.00], corner2=[0.00, 13.00, 0.00]),
    Wall(corner1=[0.00, 13.00, 0.00], corner2=[0.00, 5.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
side_meeting_chair_A = Assets(description="Bright blue chair with thin legs and curved back.", size=[0.54, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
desk_organizer = Assets(description="yellow file folder with a smiley face on it.", size=[0.10, 0.25, 0.32], placements=[AssetInstance() for _ in range(1)])
meeting_chair_A = Assets(description="A black and gray office style armchair with thin armrests on protruding black metal beams.", size=[0.64, 0.62, 0.92], placements=[AssetInstance() for _ in range(1)])
meeting_chair_B = Assets(description="A black and gray office style armchair with thin armrests on protruding black metal beams.", size=[0.64, 0.62, 0.92], placements=[AssetInstance() for _ in range(1)])
sideboard_cabinet = Assets(description="A tall white dresser with two large compartment doors and two thin drawers below.", size=[0.45, 1.10, 1.35], placements=[AssetInstance() for _ in range(1)])
side_meeting_chair_B = Assets(description="Bright blue chair with thin legs and curved back.", size=[0.54, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
wall_art_A = Assets(description="A picture of someone framed on the wall.", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
credenda = Assets(description="credenda", size=[0.55, 2.40, 0.85], placements=[AssetInstance() for _ in range(1)])
sign_in_sheet = Assets(description="Paper scroll with lines of handwriting.", size=[0.30, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
side_meeting_chair_C = Assets(description="Bright blue chair with thin legs and curved back.", size=[0.54, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
side_table_A = Assets(description="A round wood table.", size=[0.65, 0.65, 0.55], placements=[AssetInstance() for _ in range(1)])
meeting_chair_C = Assets(description="A black and gray office style armchair with thin armrests on protruding black metal beams.", size=[0.64, 0.62, 0.92], placements=[AssetInstance() for _ in range(1)])
side_table_B = Assets(description="A round wood table.", size=[0.65, 0.65, 0.55], placements=[AssetInstance() for _ in range(1)])
freestanding_plant_medium_A = Assets(description="A green fern plant in a brown planting pot.", size=[0.65, 0.65, 0.95], placements=[AssetInstance() for _ in range(1)])
wall_shelf_A = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.25, 1.00, 0.25], placements=[AssetInstance() for _ in range(1)])
tray_with_cups_A = Assets(description="A board for playing checkers that is brown and white.", size=[0.30, 0.40, 0.03], placements=[AssetInstance() for _ in range(1)])
business_card_holder = Assets(description="A blue folder with a star and file on it.", size=[0.08, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
meeting_chair_D = Assets(description="A black and gray office style armchair with thin armrests on protruding black metal beams.", size=[0.64, 0.62, 0.92], placements=[AssetInstance() for _ in range(1)])
wall_monitor = Assets(description="A rectangular flat screen television set with a white crosshair on black background.", size=[0.07, 1.65, 0.95], placements=[AssetInstance() for _ in range(1)])
freestanding_plant_large_A = Assets(description="A brown flower pot with long leafed plant protruding on a concrete pedestal.", size=[0.75, 0.75, 1.80], placements=[AssetInstance() for _ in range(1)])
meeting_chair_E = Assets(description="A black and gray office style armchair with thin armrests on protruding black metal beams.", size=[0.64, 0.62, 0.92], placements=[AssetInstance() for _ in range(1)])
wall_art_B = Assets(description="A picture of someone framed on the wall.", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
freestanding_plant_large_B = Assets(description="A brown flower pot with long leafed plant protruding on a concrete pedestal.", size=[0.75, 0.75, 1.80], placements=[AssetInstance() for _ in range(1)])
console_table = Assets(description="It is a table to set by a wall and leave items like mail on it.", size=[0.40, 1.30, 0.80], placements=[AssetInstance() for _ in range(1)])
side_meeting_chair_D = Assets(description="Bright blue chair with thin legs and curved back.", size=[0.54, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
wall_art_C = Assets(description="A picture of someone framed on the wall.", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
magazine_stack = Assets(description="Two books stacked together.", size=[0.30, 0.23, 0.06], placements=[AssetInstance() for _ in range(1)])
paper_cup_stack_A = Assets(description="A coffee cup with a plastic lid.", size=[0.09, 0.09, 0.16], placements=[AssetInstance() for _ in range(1)])
freestanding_plant_medium_B = Assets(description="A green fern plant in a brown planting pot.", size=[0.65, 0.65, 0.95], placements=[AssetInstance() for _ in range(1)])
wall_art_D = Assets(description="A picture of someone framed on the wall.", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
storage_shelf_A = Assets(description="It is a tall set of shelves made of wood and metal.", size=[0.40, 0.90, 1.90], placements=[AssetInstance() for _ in range(1)])
storage_shelf_B = Assets(description="It is a tall set of shelves made of wood and metal.", size=[0.40, 0.90, 1.90], placements=[AssetInstance() for _ in range(1)])
snack_jar_A = Assets(description="a white and blue coffee mug with a label, featuring a blue lid and a yellow and white design, resembling a honey jar and a plastic container with the word 'Ulma' on it.", size=[0.12, 0.13, 0.17], placements=[AssetInstance() for _ in range(1)])
meeting_chair_F = Assets(description="A black and gray office style armchair with thin armrests on protruding black metal beams.", size=[0.64, 0.62, 0.92], placements=[AssetInstance() for _ in range(1)])
file_box_A = Assets(description="A brown book with silver corners.", size=[0.33, 0.28, 0.10], placements=[AssetInstance() for _ in range(1)])
freestanding_plant_medium_C = Assets(description="A green fern plant in a brown planting pot.", size=[0.65, 0.65, 0.95], placements=[AssetInstance() for _ in range(1)])
snack_jar_B = Assets(description="An aluminum can with a picture of baked beans on it.", size=[0.10, 0.10, 0.15], placements=[AssetInstance() for _ in range(1)])
file_box_B = Assets(description="A brown book with silver corners.", size=[0.33, 0.28, 0.10], placements=[AssetInstance() for _ in range(1)])
umbrella_stand = Assets(description="A white box with the top open.", size=[0.25, 0.25, 0.55], placements=[AssetInstance() for _ in range(1)])
freestanding_plant_large_C = Assets(description="A brown flower pot with long leafed plant protruding on a concrete pedestal.", size=[0.75, 0.75, 1.80], placements=[AssetInstance() for _ in range(1)])
conference_table = Assets(description="A long white table with two black spines.", size=[1.30, 3.60, 0.75], placements=[AssetInstance() for _ in range(1)])
paper_cup_stack_B = Assets(description="A coffee cup with a plastic lid.", size=[0.09, 0.09, 0.16], placements=[AssetInstance() for _ in range(1)])
meeting_chair_G = Assets(description="A black and gray office style armchair with thin armrests on protruding black metal beams.", size=[0.64, 0.62, 0.92], placements=[AssetInstance() for _ in range(1)])
wall_art_E = Assets(description="A picture of someone framed on the wall.", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
wall_shelf_B = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.25, 1.00, 0.25], placements=[AssetInstance() for _ in range(1)])
whiteboard = Assets(description="A chalkboard with prices.", size=[0.05, 1.80, 1.20], placements=[AssetInstance() for _ in range(1)])
wall_clock = Assets(description="A round clock in a gray frame with a white face, two black hands and black numbers.", size=[0.05, 0.35, 0.35], placements=[AssetInstance() for _ in range(1)])
decorative_bowl = Assets(description="A yellow and black cup.", size=[0.18, 0.18, 0.10], placements=[AssetInstance() for _ in range(1)])
tray_with_cups_B = Assets(description="A board for playing checkers that is brown and white.", size=[0.30, 0.40, 0.03], placements=[AssetInstance() for _ in range(1)])

side_meeting_chair_A[0].instance_id = 'side_meeting_chair_A_0'
desk_organizer[0].instance_id = 'desk_organizer_0'
meeting_chair_A[0].instance_id = 'meeting_chair_A_0'
meeting_chair_B[0].instance_id = 'meeting_chair_B_0'
sideboard_cabinet[0].instance_id = 'sideboard_cabinet_0'
side_meeting_chair_B[0].instance_id = 'side_meeting_chair_B_0'
wall_art_A[0].instance_id = 'wall_art_A_0'
credenda[0].instance_id = 'credenda_0'
sign_in_sheet[0].instance_id = 'sign_in_sheet_0'
side_meeting_chair_C[0].instance_id = 'side_meeting_chair_C_0'
side_table_A[0].instance_id = 'side_table_A_0'
meeting_chair_C[0].instance_id = 'meeting_chair_C_0'
side_table_B[0].instance_id = 'side_table_B_0'
freestanding_plant_medium_A[0].instance_id = 'freestanding_plant_medium_A_0'
wall_shelf_A[0].instance_id = 'wall_shelf_A_0'
tray_with_cups_A[0].instance_id = 'tray_with_cups_A_0'
business_card_holder[0].instance_id = 'business_card_holder_0'
meeting_chair_D[0].instance_id = 'meeting_chair_D_0'
wall_monitor[0].instance_id = 'wall_monitor_0'
freestanding_plant_large_A[0].instance_id = 'freestanding_plant_large_A_0'
meeting_chair_E[0].instance_id = 'meeting_chair_E_0'
wall_art_B[0].instance_id = 'wall_art_B_0'
freestanding_plant_large_B[0].instance_id = 'freestanding_plant_large_B_0'
console_table[0].instance_id = 'console_table_0'
side_meeting_chair_D[0].instance_id = 'side_meeting_chair_D_0'
wall_art_C[0].instance_id = 'wall_art_C_0'
magazine_stack[0].instance_id = 'magazine_stack_0'
paper_cup_stack_A[0].instance_id = 'paper_cup_stack_A_0'
freestanding_plant_medium_B[0].instance_id = 'freestanding_plant_medium_B_0'
wall_art_D[0].instance_id = 'wall_art_D_0'
storage_shelf_A[0].instance_id = 'storage_shelf_A_0'
storage_shelf_B[0].instance_id = 'storage_shelf_B_0'
snack_jar_A[0].instance_id = 'snack_jar_A_0'
meeting_chair_F[0].instance_id = 'meeting_chair_F_0'
file_box_A[0].instance_id = 'file_box_A_0'
freestanding_plant_medium_C[0].instance_id = 'freestanding_plant_medium_C_0'
snack_jar_B[0].instance_id = 'snack_jar_B_0'
file_box_B[0].instance_id = 'file_box_B_0'
umbrella_stand[0].instance_id = 'umbrella_stand_0'
freestanding_plant_large_C[0].instance_id = 'freestanding_plant_large_C_0'
conference_table[0].instance_id = 'conference_table_0'
paper_cup_stack_B[0].instance_id = 'paper_cup_stack_B_0'
meeting_chair_G[0].instance_id = 'meeting_chair_G_0'
wall_art_E[0].instance_id = 'wall_art_E_0'
wall_shelf_B[0].instance_id = 'wall_shelf_B_0'
whiteboard[0].instance_id = 'whiteboard_0'
wall_clock[0].instance_id = 'wall_clock_0'
decorative_bowl[0].instance_id = 'decorative_bowl_0'
tray_with_cups_B[0].instance_id = 'tray_with_cups_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'
walls[8].instance_id = 'walls_8'
walls[9].instance_id = 'walls_9'

side_meeting_chair_A[0].position = [5.084098471216908, 11.232896897892033, 0.41]
side_meeting_chair_A[0].rotation = [0, 0, 0]
desk_organizer[0].position = [3.0024011240710013, 8.133140569459771, 0.16]
desk_organizer[0].rotation = [0, 0, 0]
meeting_chair_A[0].position = [1.2440906892181935, 11.214502865425363, 0.46]
meeting_chair_A[0].rotation = [0, 0, 0]
meeting_chair_B[0].position = [7.363419716100735, 4.649868301266546, 0.46]
meeting_chair_B[0].rotation = [0, 0, 0]
sideboard_cabinet[0].position = [4.750098124745222, 5.421401733589668, 0.675]
sideboard_cabinet[0].rotation = [0, 0, 0]
side_meeting_chair_B[0].position = [1.4375005655213817, 11.08460381218482, 0.41]
side_meeting_chair_B[0].rotation = [0, 0, 0]
wall_art_A[0].position = [0.49384180964649715, 11.376658991656633, 0.4]
wall_art_A[0].rotation = [0, 0, 0]
credenda[0].position = [4.939247065174238, 0.5955190228438441, 0.425]
credenda[0].rotation = [0, 0, 0]
sign_in_sheet[0].position = [2.189434867647998, 6.435438201438738, 0.0025]
sign_in_sheet[0].rotation = [0, 0, 0]
side_meeting_chair_C[0].position = [3.8675339606152273, 5.00191115886475, 0.41]
side_meeting_chair_C[0].rotation = [0, 0, 0]
side_table_A[0].position = [3.0656576149667734, 4.886582276519308, 0.275]
side_table_A[0].rotation = [0, 0, 0]
meeting_chair_C[0].position = [3.573310405353136, 4.495853283127921, 0.46]
meeting_chair_C[0].rotation = [0, 0, 0]
side_table_B[0].position = [4.7422003956040415, 5.82344825445821, 0.275]
side_table_B[0].rotation = [0, 0, 0]
freestanding_plant_medium_A[0].position = [4.376081038291418, 7.5760737004744, 0.475]
freestanding_plant_medium_A[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [4.721622418679116, 3.0191149835504967, 0.125]
wall_shelf_A[0].rotation = [0, 0, 0]
tray_with_cups_A[0].position = [1.1151638097281333, 5.415200550687997, 0.015]
tray_with_cups_A[0].rotation = [0, 0, 0]
business_card_holder[0].position = [7.739360865598997, 6.499474066771422, 0.05]
business_card_holder[0].rotation = [0, 0, 0]
meeting_chair_D[0].position = [6.489224596730187, 0.4782078639941917, 0.46]
meeting_chair_D[0].rotation = [0, 0, 0]
wall_monitor[0].position = [7.662017775561086, 9.523153687022933, 0.475]
wall_monitor[0].rotation = [0, 0, 0]
freestanding_plant_large_A[0].position = [7.848827922398291, 5.554025049485867, 0.9]
freestanding_plant_large_A[0].rotation = [0, 0, 0]
meeting_chair_E[0].position = [7.789940762688811, 4.980508512819781, 0.46]
meeting_chair_E[0].rotation = [0, 0, 0]
wall_art_B[0].position = [0.7480528458117588, 8.484825757696399, 0.4]
wall_art_B[0].rotation = [0, 0, 0]
freestanding_plant_large_B[0].position = [6.631061636950387, 9.489147913513417, 0.9]
freestanding_plant_large_B[0].rotation = [0, 0, 0]
console_table[0].position = [5.931181551309958, 10.747328373516776, 0.4]
console_table[0].rotation = [0, 0, 0]
side_meeting_chair_D[0].position = [2.142356408372601, 2.599518439893226, 0.41]
side_meeting_chair_D[0].rotation = [0, 0, 0]
wall_art_C[0].position = [7.66109423134999, 6.447983956384119, 0.4]
wall_art_C[0].rotation = [0, 0, 0]
magazine_stack[0].position = [6.566514624647756, 7.223534732127323, 0.03]
magazine_stack[0].rotation = [0, 0, 0]
paper_cup_stack_A[0].position = [6.044860359990983, 5.530200693646058, 0.08]
paper_cup_stack_A[0].rotation = [0, 0, 0]
freestanding_plant_medium_B[0].position = [1.9691436439981231, 6.667508184583827, 0.475]
freestanding_plant_medium_B[0].rotation = [0, 0, 0]
wall_art_D[0].position = [5.127668329049226, 10.303117288715173, 0.4]
wall_art_D[0].rotation = [0, 0, 0]
storage_shelf_A[0].position = [4.8553423590059674, 3.230750738341624, 0.95]
storage_shelf_A[0].rotation = [0, 0, 0]
storage_shelf_B[0].position = [0.4614657706686778, 5.0636933618455195, 0.95]
storage_shelf_B[0].rotation = [0, 0, 0]
snack_jar_A[0].position = [5.8079822800887015, 8.843281943892064, 0.085]
snack_jar_A[0].rotation = [0, 0, 0]
meeting_chair_F[0].position = [4.322708843983638, 10.248509240240315, 0.46]
meeting_chair_F[0].rotation = [0, 0, 0]
file_box_A[0].position = [3.868729319467257, 7.348889122595518, 0.05]
file_box_A[0].rotation = [0, 0, 0]
freestanding_plant_medium_C[0].position = [4.075281259432438, 4.793453299219625, 0.475]
freestanding_plant_medium_C[0].rotation = [0, 0, 0]
snack_jar_B[0].position = [0.597123212083055, 12.226498972479693, 0.075]
snack_jar_B[0].rotation = [0, 0, 0]
file_box_B[0].position = [3.201518832514693, 4.4824963895262036, 0.05]
file_box_B[0].rotation = [0, 0, 0]
umbrella_stand[0].position = [2.8098230164903164, 5.298521101235549, 0.275]
umbrella_stand[0].rotation = [0, 0, 0]
freestanding_plant_large_C[0].position = [5.173622970793386, 2.404649263714424, 0.9]
freestanding_plant_large_C[0].rotation = [0, 0, 0]
conference_table[0].position = [4.40777690116617, 9.24337320334137, 0.375]
conference_table[0].rotation = [0, 0, 0]
paper_cup_stack_B[0].position = [7.804144715877544, 6.180240884529987, 0.08]
paper_cup_stack_B[0].rotation = [0, 0, 0]
meeting_chair_G[0].position = [3.8979512320283627, 5.423070059641363, 0.46]
meeting_chair_G[0].rotation = [0, 0, 0]
wall_art_E[0].position = [3.682747409156277, 2.1041435189021165, 0.4]
wall_art_E[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [4.938522047391648, 1.6766644195169942, 0.125]
wall_shelf_B[0].rotation = [0, 0, 0]
whiteboard[0].position = [4.676588087020299, 11.208097832772342, 0.6]
whiteboard[0].rotation = [0, 0, 0]
wall_clock[0].position = [0.04943735501884117, 10.068242047189873, 0.175]
wall_clock[0].rotation = [0, 0, 0]
decorative_bowl[0].position = [0.5475746840282341, 12.195306153565255, 0.05]
decorative_bowl[0].rotation = [0, 0, 0]
tray_with_cups_B[0].position = [5.947336293613778, 0.12348247061610562, 0.015]
tray_with_cups_B[0].rotation = [0, 0, 0]
side_meeting_chair_A[0].position = [5.084098471216908, 11.232896897892033, 0.41]
side_meeting_chair_A[0].rotation = [0, 0, 0]
desk_organizer[0].position = [3.0024011240710013, 8.133140569459771, 0.16]
desk_organizer[0].rotation = [0, 0, 0]
meeting_chair_A[0].position = [1.2440906892181935, 11.214502865425363, 0.46]
meeting_chair_A[0].rotation = [0, 0, 0]
meeting_chair_B[0].position = [7.363419716100735, 4.649868301266546, 0.46]
meeting_chair_B[0].rotation = [0, 0, 0]
sideboard_cabinet[0].position = [4.750098124745222, 5.421401733589668, 0.675]
sideboard_cabinet[0].rotation = [0, 0, 0]
side_meeting_chair_B[0].position = [1.4375005655213817, 11.08460381218482, 0.41]
side_meeting_chair_B[0].rotation = [0, 0, 0]
wall_art_A[0].position = [0.49384180964649715, 11.376658991656633, 0.4]
wall_art_A[0].rotation = [0, 0, 0]
credenda[0].position = [4.939247065174238, 0.5955190228438441, 0.425]
credenda[0].rotation = [0, 0, 0]
sign_in_sheet[0].position = [2.189434867647998, 6.435438201438738, 0.0025]
sign_in_sheet[0].rotation = [0, 0, 0]
side_meeting_chair_C[0].position = [3.8675339606152273, 5.00191115886475, 0.41]
side_meeting_chair_C[0].rotation = [0, 0, 0]
side_table_A[0].position = [3.0656576149667734, 4.886582276519308, 0.275]
side_table_A[0].rotation = [0, 0, 0]
meeting_chair_C[0].position = [3.573310405353136, 4.495853283127921, 0.46]
meeting_chair_C[0].rotation = [0, 0, 0]
side_table_B[0].position = [4.7422003956040415, 5.82344825445821, 0.275]
side_table_B[0].rotation = [0, 0, 0]
freestanding_plant_medium_A[0].position = [4.376081038291418, 7.5760737004744, 0.475]
freestanding_plant_medium_A[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [4.721622418679116, 3.0191149835504967, 0.125]
wall_shelf_A[0].rotation = [0, 0, 0]
tray_with_cups_A[0].position = [1.1151638097281333, 5.415200550687997, 0.015]
tray_with_cups_A[0].rotation = [0, 0, 0]
business_card_holder[0].position = [7.739360865598997, 6.499474066771422, 0.05]
business_card_holder[0].rotation = [0, 0, 0]
meeting_chair_D[0].position = [6.489224596730187, 0.4782078639941917, 0.46]
meeting_chair_D[0].rotation = [0, 0, 0]
wall_monitor[0].position = [7.662017775561086, 9.523153687022933, 0.475]
wall_monitor[0].rotation = [0, 0, 0]
freestanding_plant_large_A[0].position = [7.848827922398291, 5.554025049485867, 0.9]
freestanding_plant_large_A[0].rotation = [0, 0, 0]
meeting_chair_E[0].position = [7.789940762688811, 4.980508512819781, 0.46]
meeting_chair_E[0].rotation = [0, 0, 0]
wall_art_B[0].position = [0.7480528458117588, 8.484825757696399, 0.4]
wall_art_B[0].rotation = [0, 0, 0]
freestanding_plant_large_B[0].position = [6.631061636950387, 9.489147913513417, 0.9]
freestanding_plant_large_B[0].rotation = [0, 0, 0]
console_table[0].position = [5.931181551309958, 10.747328373516776, 0.4]
console_table[0].rotation = [0, 0, 0]
side_meeting_chair_D[0].position = [2.142356408372601, 2.599518439893226, 0.41]
side_meeting_chair_D[0].rotation = [0, 0, 0]
wall_art_C[0].position = [7.66109423134999, 6.447983956384119, 0.4]
wall_art_C[0].rotation = [0, 0, 0]
magazine_stack[0].position = [6.566514624647756, 7.223534732127323, 0.03]
magazine_stack[0].rotation = [0, 0, 0]
paper_cup_stack_A[0].position = [6.044860359990983, 5.530200693646058, 0.08]
paper_cup_stack_A[0].rotation = [0, 0, 0]
freestanding_plant_medium_B[0].position = [1.9691436439981231, 6.667508184583827, 0.475]
freestanding_plant_medium_B[0].rotation = [0, 0, 0]
wall_art_D[0].position = [5.127668329049226, 10.303117288715173, 0.4]
wall_art_D[0].rotation = [0, 0, 0]
storage_shelf_A[0].position = [4.8553423590059674, 3.230750738341624, 0.95]
storage_shelf_A[0].rotation = [0, 0, 0]
storage_shelf_B[0].position = [0.4614657706686778, 5.0636933618455195, 0.95]
storage_shelf_B[0].rotation = [0, 0, 0]
snack_jar_A[0].position = [5.8079822800887015, 8.843281943892064, 0.085]
snack_jar_A[0].rotation = [0, 0, 0]
meeting_chair_F[0].position = [4.322708843983638, 10.248509240240315, 0.46]
meeting_chair_F[0].rotation = [0, 0, 0]
file_box_A[0].position = [3.868729319467257, 7.348889122595518, 0.05]
file_box_A[0].rotation = [0, 0, 0]
freestanding_plant_medium_C[0].position = [4.075281259432438, 4.793453299219625, 0.475]
freestanding_plant_medium_C[0].rotation = [0, 0, 0]
snack_jar_B[0].position = [0.597123212083055, 12.226498972479693, 0.075]
snack_jar_B[0].rotation = [0, 0, 0]
file_box_B[0].position = [3.201518832514693, 4.4824963895262036, 0.05]
file_box_B[0].rotation = [0, 0, 0]
umbrella_stand[0].position = [2.8098230164903164, 5.298521101235549, 0.275]
umbrella_stand[0].rotation = [0, 0, 0]
freestanding_plant_large_C[0].position = [5.173622970793386, 2.404649263714424, 0.9]
freestanding_plant_large_C[0].rotation = [0, 0, 0]
conference_table[0].position = [4.40777690116617, 9.24337320334137, 0.375]
conference_table[0].rotation = [0, 0, 0]
paper_cup_stack_B[0].position = [7.804144715877544, 6.180240884529987, 0.08]
paper_cup_stack_B[0].rotation = [0, 0, 0]
meeting_chair_G[0].position = [3.8979512320283627, 5.423070059641363, 0.46]
meeting_chair_G[0].rotation = [0, 0, 0]
wall_art_E[0].position = [3.682747409156277, 2.1041435189021165, 0.4]
wall_art_E[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [4.938522047391648, 1.6766644195169942, 0.125]
wall_shelf_B[0].rotation = [0, 0, 0]
whiteboard[0].position = [4.676588087020299, 11.208097832772342, 0.6]
whiteboard[0].rotation = [0, 0, 0]
wall_clock[0].position = [0.04943735501884117, 10.068242047189873, 0.175]
wall_clock[0].rotation = [0, 0, 0]
decorative_bowl[0].position = [0.5475746840282341, 12.195306153565255, 0.05]
decorative_bowl[0].rotation = [0, 0, 0]
tray_with_cups_B[0].position = [5.947336293613778, 0.12348247061610562, 0.015]
tray_with_cups_B[0].rotation = [0, 0, 0]

solver.constraints = []

# The conference area occupies the broad middle of the room. Reception seating
# is in the western bay, refreshments are at the south end, and the west-door
# approach (y=9.39 through 11.33) remains clear.
#
# Coordinates below are bounding-box centers. Rotations account for the fact
# that an asset's unrotated front faces +x.

def place_room_asset(asset_group, xyz, yaw=0, wall_index=None):
    instance = asset_group[0]
    instance.position = list(xyz)
    instance.rotation = [0, 0, radians(yaw)]

    if wall_index is not None:
        solver.against_wall(instance, walls[wall_index])

    # Preserve both the selected floor-plan location and the elevation of
    # wall-mounted objects. These anchors are references, not additional props.
    solver.distance_constraint(
        instance, AssetInstance(position=list(xyz)), 0, 0, weight=10
    )
    solver.align_with(
        instance,
        AssetInstance(position=list(xyz), rotation=[0, 0, radians(yaw)])
    )


# Main meeting area: clear space between chair fronts and the tabletop edges,
# plus circulation around the outside of the seating.
place_room_asset(conference_table, (5.00, 6.00, 0.375))
place_room_asset(meeting_chair_C, (3.65, 4.80, 0.46), 0)
place_room_asset(meeting_chair_F, (3.65, 6.00, 0.46), 0)
place_room_asset(meeting_chair_B, (3.65, 7.20, 0.46), 0)
place_room_asset(meeting_chair_A, (6.35, 4.80, 0.46), 180)
place_room_asset(meeting_chair_D, (6.35, 6.00, 0.46), 180)
place_room_asset(meeting_chair_E, (6.35, 7.20, 0.46), 180)
place_room_asset(meeting_chair_G, (5.00, 8.55, 0.46), 270)

# F (o0033) lies midway between C (o0011) and B (o0003).
solver.distance_constraint(
    meeting_chair_F[0], meeting_chair_C[0], 1.20, 1.20, weight=10
)
solver.distance_constraint(
    meeting_chair_F[0], meeting_chair_B[0], 1.20, 1.20, weight=10
)
solver.align_with(meeting_chair_F[0], meeting_chair_C[0])
solver.align_with(meeting_chair_F[0], meeting_chair_B[0])

for chair_group in (
    meeting_chair_A, meeting_chair_B, meeting_chair_C,
    meeting_chair_D, meeting_chair_E, meeting_chair_F, meeting_chair_G
):
    # The side chairs remain parallel rather than turning diagonally.
    solver.distance_constraint(
        chair_group[0], conference_table[0], 1.30, 2.70
    )


# South refreshment area. Rotating the credenza puts its long dimension along
# the south wall, with its front facing into the room.
place_room_asset(credenda, (5.70, 0.275, 0.425), 90, 4)
place_room_asset(sideboard_cabinet, (4.225, 1.60, 0.675), 0, 3)
place_room_asset(side_table_A, (5.70, 2.10, 0.275))
place_room_asset(side_meeting_chair_A, (6.40, 2.10, 0.41), 0)
place_room_asset(side_meeting_chair_B, (5.00, 2.10, 0.41), 0)
place_room_asset(freestanding_plant_large_B, (7.625, 2.10, 0.90), 180, 5)

# A (o0000) looks toward the large plant B (o0022), not toward the table.
solver.point_towards(side_meeting_chair_A[0], freestanding_plant_large_B[0])
solver.distance_constraint(
    side_meeting_chair_A[0], freestanding_plant_large_B[0], 1.20, 1.40
)
solver.point_towards(side_meeting_chair_B[0], side_table_A[0])
solver.distance_constraint(
    side_meeting_chair_B[0], side_table_A[0], 0.70, 0.85
)


# Western reception bay; furniture stays south of the door clearance zone.
place_room_asset(side_table_B, (0.95, 6.90, 0.275))
place_room_asset(side_meeting_chair_C, (0.95, 6.10, 0.41), 90)
place_room_asset(side_meeting_chair_D, (0.95, 7.70, 0.41), 270)
place_room_asset(console_table, (0.20, 8.30, 0.40), 0, 9)
place_room_asset(freestanding_plant_large_A, (1.625, 5.375, 0.90), 90, 0)
place_room_asset(umbrella_stand, (0.20, 9.15, 0.275), 0)

for chair_group in (side_meeting_chair_C, side_meeting_chair_D):
    solver.point_towards(chair_group[0], side_table_B[0])
    solver.distance_constraint(chair_group[0], side_table_B[0], 0.80, 0.90)


# Storage occupies the northern recess, outside the entrance opening.
place_room_asset(storage_shelf_A, (0.20, 11.95, 0.95), 0, 9)
place_room_asset(storage_shelf_B, (1.80, 12.45, 0.95), 180, 7)
place_room_asset(freestanding_plant_large_C, (1.00, 12.625, 0.90), 270, 8)

# Plants near the glazed east wall leave the central circulation unobstructed.
place_room_asset(freestanding_plant_medium_A, (7.675, 0.50, 0.475), 180, 5)
place_room_asset(freestanding_plant_medium_B, (7.675, 10.20, 0.475), 180, 5)
place_room_asset(freestanding_plant_medium_C, (2.40, 1.325, 0.475), 90, 2)


# Presentation equipment uses solid walls, avoiding all eastern windows.
# Shelves sit above the monitor, with vertical separation between their boxes.
place_room_asset(wall_monitor, (2.035, 3.00, 1.70), 0, 1)
place_room_asset(wall_shelf_A, (2.125, 2.60, 2.50), 0, 1)
place_room_asset(wall_shelf_B, (2.125, 3.90, 2.50), 0, 1)
place_room_asset(whiteboard, (5.00, 11.975, 1.70), 270, 6)
place_room_asset(wall_clock, (5.00, 11.975, 2.70), 270, 6)

# Art is elevated above nearby furniture and does not intersect glazing.
place_room_asset(wall_art_A, (0.02, 6.80, 1.75), 0, 9)
place_room_asset(wall_art_B, (0.02, 8.30, 1.75), 0, 9)
place_room_asset(wall_art_C, (3.00, 11.98, 1.75), 270, 6)
place_room_asset(wall_art_D, (7.00, 11.98, 1.75), 270, 6)
place_room_asset(wall_art_E, (2.02, 4.65, 1.75), 0, 1)


def place_surface_asset(asset_group, support_group, x, y, yaw=0):
    instance = asset_group[0]
    support_instance = support_group[0]
    top_z = support_instance.position[2] + support_group.size[2] / 2
    center_z = top_z + asset_group.size[2] / 2

    instance.position = [x, y, center_z]
    instance.rotation = [0, 0, radians(yaw)]

    # Support is the primary constraint; the reference position also keeps
    # separate tabletop objects from drifting into one another.
    solver.on_top_of(instance, support_instance)
    solver.distance_constraint(
        instance,
        AssetInstance(position=[x, y, center_z]),
        0, 0, weight=10
    )
    solver.align_with(
        instance,
        AssetInstance(
            position=[x, y, center_z],
            rotation=[0, 0, radians(yaw)]
        )
    )


# Separate refreshment items along the credenza. The required paper cup stack
# A (o0027) is directly supported by the credenza (o0007).
place_surface_asset(tray_with_cups_A, credenda, 4.90, 0.275, 90)
place_surface_asset(paper_cup_stack_A, credenda, 5.30, 0.275, 90)
place_surface_asset(paper_cup_stack_B, credenda, 5.55, 0.275, 90)
place_surface_asset(snack_jar_A, credenda, 5.90, 0.275, 90)
place_surface_asset(snack_jar_B, credenda, 6.20, 0.275, 90)
place_surface_asset(decorative_bowl, credenda, 6.60, 0.275, 90)

# Reception supplies fit within the shallow console's footprint.
place_surface_asset(sign_in_sheet, console_table, 0.20, 8.00)
place_surface_asset(business_card_holder, console_table, 0.20, 8.36)
place_surface_asset(desk_organizer, console_table, 0.20, 8.68)

# Each small table receives one item, leaving usable surface around it.
place_surface_asset(tray_with_cups_B, side_table_A, 5.70, 2.10)
place_surface_asset(magazine_stack, side_table_B, 0.95, 6.90)

# Store the file boxes on the tall shelving, rather than on the floor.
place_surface_asset(file_box_A, storage_shelf_A, 0.20, 11.95)
place_surface_asset(file_box_B, storage_shelf_B, 1.80, 12.45, 180)

solver.constraints = []
wall_art_E[0].position = [2.0113892555236816, 4.650000095367432, 0.4000000059604645]
wall_art_E[0].rotation = [0, 0, 0.0025409193727581954]
wall_art_E[0].optimize = 2
whiteboard[0].position = [5.0, 11.973692893981934, 0.6000000238418579]
whiteboard[0].rotation = [0, 0, -1.5682554273204203]
whiteboard[0].optimize = 2
wall_art_B[0].position = [0.011367769911885262, 8.300000190734863, 0.4000000059604645]
wall_art_B[0].rotation = [0, 0, 0.0025409193727581954]
wall_art_B[0].optimize = 2
wall_art_A[0].position = [0.011367769911885262, 6.800000190734863, 0.4000000059604645]
wall_art_A[0].rotation = [0, 0, 0.0025409193727581954]
wall_art_A[0].optimize = 2
meeting_chair_E[0].position = [6.349999904632568, 7.199999809265137, 0.46000000834465027]
meeting_chair_E[0].rotation = [0, 0, -3.1290262823329655]
meeting_chair_E[0].optimize = 2
snack_jar_A[0].position = [5.900000095367432, 0.2750000059604645, 0.9350000023841858]
snack_jar_A[0].rotation = [0, 0, 1.5833626980517244]
snack_jar_A[0].optimize = 2
meeting_chair_D[0].position = [6.349999904632568, 6.0, 0.46000000834465027]
meeting_chair_D[0].rotation = [0, 0, -3.1290262823329655]
meeting_chair_D[0].optimize = 2
wall_clock[0].position = [5.0, 11.983841896057129, 0.17499999701976776]
wall_clock[0].rotation = [0, 0, -1.5682554052778654]
wall_clock[0].optimize = 2
meeting_chair_C[0].position = [3.6500000953674316, 4.800000190734863, 0.46000000834465027]
meeting_chair_C[0].rotation = [0, 0, 0.01884955539881635]
meeting_chair_C[0].optimize = 2
wall_monitor[0].position = [2.0353646278381348, 3.0, 0.4749999940395355]
wall_monitor[0].rotation = [0, 0, 0.002540901618744305]
wall_monitor[0].optimize = 2
sideboard_cabinet[0].position = [4.215139389038086, 1.590000033378601, 0.675000011920929]
sideboard_cabinet[0].rotation = [0, 0, 0.02279178335831472]
sideboard_cabinet[0].optimize = 2
wall_art_C[0].position = [3.0, 11.98884105682373, 0.4000000059604645]
wall_art_C[0].rotation = [0, 0, -1.5682554083443117]
wall_art_C[0].optimize = 2
freestanding_plant_medium_C[0].position = [2.4000000953674316, 1.3258247375488281, 0.4749999940395355]
freestanding_plant_medium_C[0].rotation = [0, 0, 1.5733372458677286]
freestanding_plant_medium_C[0].optimize = 2
paper_cup_stack_B[0].position = [5.550000190734863, 0.2750000059604645, 0.9300000071525574]
paper_cup_stack_B[0].rotation = [0, 0, 1.5833626980517244]
paper_cup_stack_B[0].optimize = 2
business_card_holder[0].position = [0.20000000298023224, 8.359999656677246, 0.8500000238418579]
business_card_holder[0].rotation = [0, 0, 0.01256637125682779]
business_card_holder[0].optimize = 2
file_box_B[0].position = [1.7999999523162842, 12.449999809265137, 1.9499999284744263]
file_box_B[0].rotation = [0, 0, -3.1290262823329655]
file_box_B[0].optimize = 2
wall_art_D[0].position = [7.0, 11.98884105682373, 0.4000000059604645]
wall_art_D[0].rotation = [0, 0, -1.5682554083443117]
wall_art_D[0].optimize = 2
meeting_chair_G[0].position = [5.0, 8.550000190734863, 0.46000000834465027]
meeting_chair_G[0].rotation = [0, 0, -1.5582299555380688]
meeting_chair_G[0].optimize = 2
conference_table[0].position = [5.0, 6.0, 0.375]
conference_table[0].rotation = [0, 0, 0.031415925765816845]
conference_table[0].optimize = 2
tray_with_cups_B[0].position = [5.699999809265137, 2.0999999046325684, 0.5649999976158142]
tray_with_cups_B[0].rotation = [0, 0, 0.01256637125682779]
tray_with_cups_B[0].optimize = 2
freestanding_plant_large_C[0].position = [1.0, 12.624048233032227, 0.8999999761581421]
freestanding_plant_large_C[0].rotation = [0, 0, -1.5682554086442377]
freestanding_plant_large_C[0].optimize = 2
side_meeting_chair_C[0].position = [0.949999988079071, 6.099999904632568, 0.4099999964237213]
side_meeting_chair_C[0].rotation = [0, 0, 1.586504290712113]
side_meeting_chair_C[0].optimize = 2
meeting_chair_F[0].position = [3.6500000953674316, 6.0, 0.46000000834465027]
meeting_chair_F[0].rotation = [0, 0, 0.014986366218674498]
meeting_chair_F[0].optimize = 2
freestanding_plant_large_B[0].position = [7.621728420257568, 2.0999999046325684, 0.8999999761581421]
freestanding_plant_large_B[0].rotation = [0, 0, -3.1328304326338854]
freestanding_plant_large_B[0].optimize = 2
console_table[0].position = [0.20424491167068481, 8.300000190734863, 0.4000000059604645]
console_table[0].rotation = [0, 0, 0.011873011980222227]
console_table[0].optimize = 2
wall_shelf_B[0].position = [2.126270055770874, 3.9000000953674316, 0.125]
wall_shelf_B[0].rotation = [0, 0, 0.002540913862115027]
wall_shelf_B[0].optimize = 2
file_box_A[0].position = [0.20000000298023224, 11.949999809265137, 1.9499999284744263]
file_box_A[0].rotation = [0, 0, 0.01256637125682779]
file_box_A[0].optimize = 2
side_table_B[0].position = [0.949999988079071, 6.900000095367432, 0.2750000059604645]
side_table_B[0].rotation = [0, 0, 0.025132740109855806]
side_table_B[0].optimize = 2
meeting_chair_B[0].position = [3.6500000953674316, 7.199999809265137, 0.46000000834465027]
meeting_chair_B[0].rotation = [0, 0, 0.01884955539881635]
meeting_chair_B[0].optimize = 2
storage_shelf_B[0].position = [1.7999999523162842, 12.449999809265137, 0.949999988079071]
storage_shelf_B[0].rotation = [0, 0, -3.115628434353491]
storage_shelf_B[0].optimize = 2
magazine_stack[0].position = [0.949999988079071, 6.900000095367432, 0.5799999833106995]
magazine_stack[0].rotation = [0, 0, 0.01256637125682779]
magazine_stack[0].optimize = 2
side_meeting_chair_B[0].position = [4.989999771118164, 2.0999999046325684, 0.4099999964237213]
side_meeting_chair_B[0].rotation = [0, 0, 0.0157079639172164]
side_meeting_chair_B[0].optimize = 2
tray_with_cups_A[0].position = [4.900000095367432, 0.2750000059604645, 0.8650000095367432]
tray_with_cups_A[0].rotation = [0, 0, 1.5833626980517244]
tray_with_cups_A[0].optimize = 2
storage_shelf_A[0].position = [0.21000000834465027, 11.960000038146973, 0.949999988079071]
storage_shelf_A[0].rotation = [0, 0, 0.005651441060042556]
storage_shelf_A[0].optimize = 2
side_table_A[0].position = [5.699999809265137, 2.0999999046325684, 0.2750000059604645]
side_table_A[0].rotation = [0, 0, 0.01884955539881635]
side_table_A[0].optimize = 2
meeting_chair_A[0].position = [6.349999904632568, 4.800000190734863, 0.46000000834465027]
meeting_chair_A[0].rotation = [0, 0, -3.1290262823329655]
meeting_chair_A[0].optimize = 2
paper_cup_stack_A[0].position = [5.300000190734863, 0.2750000059604645, 0.9300000071525574]
paper_cup_stack_A[0].rotation = [0, 0, 1.5833626980517244]
paper_cup_stack_A[0].optimize = 2
decorative_bowl[0].position = [6.599999904632568, 0.2750000059604645, 0.9000000357627869]
decorative_bowl[0].rotation = [0, 0, 1.5833626980517244]
decorative_bowl[0].optimize = 2
snack_jar_B[0].position = [6.199999809265137, 0.2750000059604645, 0.925000011920929]
snack_jar_B[0].rotation = [0, 0, 1.5833626980517244]
snack_jar_B[0].optimize = 2
umbrella_stand[0].position = [0.20000000298023224, 9.149999618530273, 0.2750000059604645]
umbrella_stand[0].rotation = [0, 0, 0.00942477746072377]
umbrella_stand[0].optimize = 2
credenda[0].position = [5.699999809265137, 0.3025572896003723, 0.42500001192092896]
credenda[0].rotation = [0, 0, 1.592002314116044]
credenda[0].optimize = 2
wall_shelf_A[0].position = [2.126270055770874, 2.5999999046325684, 0.125]
wall_shelf_A[0].rotation = [0, 0, 0.002540913862115027]
wall_shelf_A[0].optimize = 2
sign_in_sheet[0].position = [0.20000000298023224, 8.0, 0.8050000071525574]
sign_in_sheet[0].rotation = [0, 0, 0.01256637125682779]
sign_in_sheet[0].optimize = 2
desk_organizer[0].position = [0.20000000298023224, 8.680000305175781, 0.9600000381469727]
desk_organizer[0].rotation = [0, 0, 0.01256637125682779]
desk_organizer[0].optimize = 2
side_meeting_chair_D[0].position = [0.949999988079071, 7.710000038146973, 0.4099999964237213]
side_meeting_chair_D[0].rotation = [0, 0, -1.5550883628776802]
side_meeting_chair_D[0].optimize = 2
freestanding_plant_medium_B[0].position = [7.674175262451172, 10.199999809265137, 0.4749999940395355]
freestanding_plant_medium_B[0].rotation = [0, 0, -3.1390517345169613]
freestanding_plant_medium_B[0].optimize = 2
freestanding_plant_large_A[0].position = [1.6150010824203491, 5.375951766967773, 0.8999999761581421]
freestanding_plant_large_A[0].rotation = [0, 0, 1.5733372415791846]
freestanding_plant_large_A[0].optimize = 2
side_meeting_chair_A[0].position = [6.400000095367432, 2.0999999046325684, 0.4099999964237213]
side_meeting_chair_A[0].rotation = [0, 0, 0.0157079639172164]
side_meeting_chair_A[0].optimize = 2
freestanding_plant_medium_A[0].position = [7.674175262451172, 0.5, 0.4749999940395355]
freestanding_plant_medium_A[0].rotation = [0, 0, -3.1390517345169613]
freestanding_plant_medium_A[0].optimize = 2

