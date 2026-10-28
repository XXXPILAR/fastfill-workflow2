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
side_meeting_chair_A = Assets(description="Bright blue chair with thin legs and curved back.", size=[0.55, 0.52, 0.82], placements=[AssetInstance() for _ in range(1)])
desk_organizer = Assets(description="yellow file folder with a smiley face on it.", size=[0.10, 0.25, 0.32], placements=[AssetInstance() for _ in range(1)])
meeting_chair_A = Assets(description="A black and gray office style armchair with thin armrests on protruding black metal beams.", size=[0.65, 0.62, 0.92], placements=[AssetInstance() for _ in range(1)])
meeting_chair_B = Assets(description="A black and gray office style armchair with thin armrests on protruding black metal beams.", size=[0.65, 0.62, 0.92], placements=[AssetInstance() for _ in range(1)])
sideboard_cabinet = Assets(description="A tall white dresser with two large compartment doors and two thin drawers below.", size=[0.45, 1.20, 1.25], placements=[AssetInstance() for _ in range(1)])
side_meeting_chair_B = Assets(description="Bright blue chair with thin legs and curved back.", size=[0.55, 0.52, 0.82], placements=[AssetInstance() for _ in range(1)])
wall_art_A = Assets(description="A picture of someone framed on the wall.", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
credenda = Assets(description="credenda", size=[0.50, 1.80, 0.85], placements=[AssetInstance() for _ in range(1)])
sign_in_sheet = Assets(description="Paper scroll with lines of handwriting.", size=[0.21, 0.30, 0.01], placements=[AssetInstance() for _ in range(1)])
side_meeting_chair_C = Assets(description="Bright blue chair with thin legs and curved back.", size=[0.55, 0.52, 0.82], placements=[AssetInstance() for _ in range(1)])
side_table_A = Assets(description="A round wood table.", size=[0.60, 0.60, 0.55], placements=[AssetInstance() for _ in range(1)])
meeting_chair_C = Assets(description="A black and gray office style armchair with thin armrests on protruding black metal beams.", size=[0.65, 0.62, 0.92], placements=[AssetInstance() for _ in range(1)])
side_table_B = Assets(description="A round wood table.", size=[0.60, 0.60, 0.55], placements=[AssetInstance() for _ in range(1)])
freestanding_plant_medium_A = Assets(description="A green fern plant in a brown planting pot.", size=[0.70, 0.70, 1.10], placements=[AssetInstance() for _ in range(1)])
wall_shelf_A = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.25, 0.90, 0.25], placements=[AssetInstance() for _ in range(1)])
tray_with_cups_A = Assets(description="A board for playing checkers that is brown and white.", size=[0.35, 0.45, 0.08], placements=[AssetInstance() for _ in range(1)])
business_card_holder = Assets(description="A blue folder with a star and file on it.", size=[0.08, 0.12, 0.08], placements=[AssetInstance() for _ in range(1)])
meeting_chair_D = Assets(description="A black and gray office style armchair with thin armrests on protruding black metal beams.", size=[0.65, 0.62, 0.92], placements=[AssetInstance() for _ in range(1)])
wall_monitor = Assets(description="A rectangular flat screen television set with a white crosshair on black background.", size=[0.08, 1.45, 0.85], placements=[AssetInstance() for _ in range(1)])
freestanding_plant_large_A = Assets(description="A brown flower pot with long leafed plant protruding on a concrete pedestal.", size=[0.90, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
meeting_chair_E = Assets(description="A black and gray office style armchair with thin armrests on protruding black metal beams.", size=[0.65, 0.62, 0.92], placements=[AssetInstance() for _ in range(1)])
wall_art_B = Assets(description="A picture of someone framed on the wall.", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
freestanding_plant_large_B = Assets(description="A brown flower pot with long leafed plant protruding on a concrete pedestal.", size=[0.90, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
console_table = Assets(description="It is a table to set by a wall and leave items like mail on it.", size=[0.40, 1.20, 0.80], placements=[AssetInstance() for _ in range(1)])
side_meeting_chair_D = Assets(description="Bright blue chair with thin legs and curved back.", size=[0.55, 0.52, 0.82], placements=[AssetInstance() for _ in range(1)])
wall_art_C = Assets(description="A picture of someone framed on the wall.", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
magazine_stack = Assets(description="Two books stacked together.", size=[0.22, 0.28, 0.06], placements=[AssetInstance() for _ in range(1)])
paper_cup_stack_A = Assets(description="A coffee cup with a plastic lid.", size=[0.10, 0.10, 0.16], placements=[AssetInstance() for _ in range(1)])
freestanding_plant_medium_B = Assets(description="A green fern plant in a brown planting pot.", size=[0.70, 0.70, 1.10], placements=[AssetInstance() for _ in range(1)])
wall_art_D = Assets(description="A picture of someone framed on the wall.", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
storage_shelf_A = Assets(description="It is a tall set of shelves made of wood and metal.", size=[0.40, 1.00, 1.90], placements=[AssetInstance() for _ in range(1)])
storage_shelf_B = Assets(description="It is a tall set of shelves made of wood and metal.", size=[0.40, 1.00, 1.90], placements=[AssetInstance() for _ in range(1)])
snack_jar_A = Assets(description="a white and blue coffee mug with a label, featuring a blue lid and a yellow and white design, resembling a honey jar and a plastic container with the word 'Ulma' on it.", size=[0.14, 0.14, 0.20], placements=[AssetInstance() for _ in range(1)])
meeting_chair_F = Assets(description="A black and gray office style armchair with thin armrests on protruding black metal beams.", size=[0.65, 0.62, 0.92], placements=[AssetInstance() for _ in range(1)])
file_box_A = Assets(description="A brown book with silver corners.", size=[0.28, 0.35, 0.12], placements=[AssetInstance() for _ in range(1)])
freestanding_plant_medium_C = Assets(description="A green fern plant in a brown planting pot.", size=[0.70, 0.70, 1.10], placements=[AssetInstance() for _ in range(1)])
snack_jar_B = Assets(description="An aluminum can with a picture of baked beans on it.", size=[0.08, 0.08, 0.12], placements=[AssetInstance() for _ in range(1)])
file_box_B = Assets(description="A brown book with silver corners.", size=[0.28, 0.35, 0.12], placements=[AssetInstance() for _ in range(1)])
umbrella_stand = Assets(description="A white box with the top open.", size=[0.28, 0.28, 0.60], placements=[AssetInstance() for _ in range(1)])
freestanding_plant_large_C = Assets(description="A brown flower pot with long leafed plant protruding on a concrete pedestal.", size=[0.90, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
conference_table = Assets(description="A long white table with two black spines.", size=[1.50, 4.80, 0.75], placements=[AssetInstance() for _ in range(1)])
paper_cup_stack_B = Assets(description="A coffee cup with a plastic lid.", size=[0.10, 0.10, 0.16], placements=[AssetInstance() for _ in range(1)])
meeting_chair_G = Assets(description="A black and gray office style armchair with thin armrests on protruding black metal beams.", size=[0.65, 0.62, 0.92], placements=[AssetInstance() for _ in range(1)])
wall_art_E = Assets(description="A picture of someone framed on the wall.", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
wall_shelf_B = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.25, 0.90, 0.25], placements=[AssetInstance() for _ in range(1)])
whiteboard = Assets(description="A chalkboard with prices.", size=[0.05, 1.80, 1.20], placements=[AssetInstance() for _ in range(1)])
wall_clock = Assets(description="A round clock in a gray frame with a white face, two black hands and black numbers.", size=[0.05, 0.35, 0.35], placements=[AssetInstance() for _ in range(1)])
decorative_bowl = Assets(description="A yellow and black cup.", size=[0.20, 0.20, 0.12], placements=[AssetInstance() for _ in range(1)])
tray_with_cups_B = Assets(description="A board for playing checkers that is brown and white.", size=[0.35, 0.45, 0.08], placements=[AssetInstance() for _ in range(1)])

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

side_meeting_chair_A[0].position = [4.709191794091356, 0.4520378883730859, 0.41]
side_meeting_chair_A[0].rotation = [0, 0, 0]
desk_organizer[0].position = [4.539221817845824, 11.756317319510574, 0.16]
desk_organizer[0].rotation = [0, 0, 0]
meeting_chair_A[0].position = [7.827891682260398, 10.029212161433128, 0.46]
meeting_chair_A[0].rotation = [0, 0, 0]
meeting_chair_B[0].position = [2.4401394245428945, 7.0495371149265615, 0.46]
meeting_chair_B[0].rotation = [0, 0, 0]
sideboard_cabinet[0].position = [6.811468306511122, 11.922171173414155, 0.625]
sideboard_cabinet[0].rotation = [0, 0, 0]
side_meeting_chair_B[0].position = [2.2272897180955864, 2.735253715769782, 0.41]
side_meeting_chair_B[0].rotation = [0, 0, 0]
wall_art_A[0].position = [2.6882572176037467, 10.14444395653472, 0.4]
wall_art_A[0].rotation = [0, 0, 0]
credenda[0].position = [3.3986462939477686, 3.7489789539595484, 0.425]
credenda[0].rotation = [0, 0, 0]
sign_in_sheet[0].position = [3.865315917416729, 7.259635236585396, 0.005]
sign_in_sheet[0].rotation = [0, 0, 0]
side_meeting_chair_C[0].position = [4.167776624649366, 1.1238199177659443, 0.41]
side_meeting_chair_C[0].rotation = [0, 0, 0]
side_table_A[0].position = [5.849686055344529, 3.206688970558472, 0.275]
side_table_A[0].rotation = [0, 0, 0]
meeting_chair_C[0].position = [6.037368522275165, 2.3334846919091667, 0.46]
meeting_chair_C[0].rotation = [0, 0, 0]
side_table_B[0].position = [6.631251296248052, 5.410879715066577, 0.275]
side_table_B[0].rotation = [0, 0, 0]
freestanding_plant_medium_A[0].position = [1.4192545370240266, 8.529574499352128, 0.55]
freestanding_plant_medium_A[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [1.626331978282498, 11.467082959336743, 0.125]
wall_shelf_A[0].rotation = [0, 0, 0]
tray_with_cups_A[0].position = [3.5798975538660374, 9.149818073391106, 0.04]
tray_with_cups_A[0].rotation = [0, 0, 0]
business_card_holder[0].position = [0.7222969029255824, 8.047338672223317, 0.04]
business_card_holder[0].rotation = [0, 0, 0]
meeting_chair_D[0].position = [3.3355755385079817, 5.035891458401715, 0.46]
meeting_chair_D[0].rotation = [0, 0, 0]
wall_monitor[0].position = [7.664902316906152, 4.174325661307569, 0.425]
wall_monitor[0].rotation = [0, 0, 0]
freestanding_plant_large_A[0].position = [1.90288311547181, 11.217533728425087, 0.9]
freestanding_plant_large_A[0].rotation = [0, 0, 0]
meeting_chair_E[0].position = [1.7252806487864465, 10.486220587676636, 0.46]
meeting_chair_E[0].rotation = [0, 0, 0]
wall_art_B[0].position = [6.669322156536039, 0.3940730842312459, 0.4]
wall_art_B[0].rotation = [0, 0, 0]
freestanding_plant_large_B[0].position = [6.530326190410748, 8.936201982406631, 0.9]
freestanding_plant_large_B[0].rotation = [0, 0, 0]
console_table[0].position = [4.138393816080459, 2.0748227756994426, 0.4]
console_table[0].rotation = [0, 0, 0]
side_meeting_chair_D[0].position = [6.443826188400391, 10.183699512098869, 0.41]
side_meeting_chair_D[0].rotation = [0, 0, 0]
wall_art_C[0].position = [3.8656679420314406, 4.462527208508635, 0.4]
wall_art_C[0].rotation = [0, 0, 0]
magazine_stack[0].position = [1.2717866842038772, 10.88271315244059, 0.03]
magazine_stack[0].rotation = [0, 0, 0]
paper_cup_stack_A[0].position = [6.807405257313166, 11.80526318316458, 0.08]
paper_cup_stack_A[0].rotation = [0, 0, 0]
freestanding_plant_medium_B[0].position = [3.057153679344669, 1.2242424156353764, 0.55]
freestanding_plant_medium_B[0].rotation = [0, 0, 0]
wall_art_D[0].position = [2.9662876923858503, 11.16495865601832, 0.4]
wall_art_D[0].rotation = [0, 0, 0]
storage_shelf_A[0].position = [0.8079669355208949, 7.637971991149722, 0.95]
storage_shelf_A[0].rotation = [0, 0, 0]
storage_shelf_B[0].position = [2.721054453392428, 9.584601660302317, 0.95]
storage_shelf_B[0].rotation = [0, 0, 0]
snack_jar_A[0].position = [2.6881737951361275, 9.491586040766126, 0.1]
snack_jar_A[0].rotation = [0, 0, 0]
meeting_chair_F[0].position = [2.4916978408752604, 4.931117604831723, 0.46]
meeting_chair_F[0].rotation = [0, 0, 0]
file_box_A[0].position = [1.731095477953656, 11.736989877233608, 0.06]
file_box_A[0].rotation = [0, 0, 0]
freestanding_plant_medium_C[0].position = [3.202381326493521, 8.939401401466542, 0.55]
freestanding_plant_medium_C[0].rotation = [0, 0, 0]
snack_jar_B[0].position = [0.5295190197822164, 9.985548030618887, 0.06]
snack_jar_B[0].rotation = [0, 0, 0]
file_box_B[0].position = [3.537357066623855, 10.020666662470894, 0.06]
file_box_B[0].rotation = [0, 0, 0]
umbrella_stand[0].position = [0.5997753632906475, 5.0493796205499955, 0.3]
umbrella_stand[0].rotation = [0, 0, 0]
freestanding_plant_large_C[0].position = [6.545087813653102, 6.328996443118142, 0.9]
freestanding_plant_large_C[0].rotation = [0, 0, 0]
conference_table[0].position = [4.258196217917092, 5.410456984172319, 0.375]
conference_table[0].rotation = [0, 0, 0]
paper_cup_stack_B[0].position = [6.176762950227989, 4.077211736097179, 0.08]
paper_cup_stack_B[0].rotation = [0, 0, 0]
meeting_chair_G[0].position = [7.488364401871915, 10.169746658686782, 0.46]
meeting_chair_G[0].rotation = [0, 0, 0]
wall_art_E[0].position = [0.763909687068768, 12.165743556812723, 0.4]
wall_art_E[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [0.36468643132808953, 11.379568050227562, 0.125]
wall_shelf_B[0].rotation = [0, 0, 0]
whiteboard[0].position = [0.47668372072388454, 11.709537000032498, 0.6]
whiteboard[0].rotation = [0, 0, 0]
wall_clock[0].position = [5.81630868154928, 7.951462918966919, 0.175]
wall_clock[0].rotation = [0, 0, 0]
decorative_bowl[0].position = [6.400448014919626, 4.043186487529912, 0.06]
decorative_bowl[0].rotation = [0, 0, 0]
tray_with_cups_B[0].position = [0.8849237381865143, 7.863360727378098, 0.04]
tray_with_cups_B[0].rotation = [0, 0, 0]
side_meeting_chair_A[0].position = [4.709191794091356, 0.4520378883730859, 0.41]
side_meeting_chair_A[0].rotation = [0, 0, 0]
desk_organizer[0].position = [4.539221817845824, 11.756317319510574, 0.16]
desk_organizer[0].rotation = [0, 0, 0]
meeting_chair_A[0].position = [7.827891682260398, 10.029212161433128, 0.46]
meeting_chair_A[0].rotation = [0, 0, 0]
meeting_chair_B[0].position = [2.4401394245428945, 7.0495371149265615, 0.46]
meeting_chair_B[0].rotation = [0, 0, 0]
sideboard_cabinet[0].position = [6.811468306511122, 11.922171173414155, 0.625]
sideboard_cabinet[0].rotation = [0, 0, 0]
side_meeting_chair_B[0].position = [2.2272897180955864, 2.735253715769782, 0.41]
side_meeting_chair_B[0].rotation = [0, 0, 0]
wall_art_A[0].position = [2.6882572176037467, 10.14444395653472, 0.4]
wall_art_A[0].rotation = [0, 0, 0]
credenda[0].position = [3.3986462939477686, 3.7489789539595484, 0.425]
credenda[0].rotation = [0, 0, 0]
sign_in_sheet[0].position = [3.865315917416729, 7.259635236585396, 0.005]
sign_in_sheet[0].rotation = [0, 0, 0]
side_meeting_chair_C[0].position = [4.167776624649366, 1.1238199177659443, 0.41]
side_meeting_chair_C[0].rotation = [0, 0, 0]
side_table_A[0].position = [5.849686055344529, 3.206688970558472, 0.275]
side_table_A[0].rotation = [0, 0, 0]
meeting_chair_C[0].position = [6.037368522275165, 2.3334846919091667, 0.46]
meeting_chair_C[0].rotation = [0, 0, 0]
side_table_B[0].position = [6.631251296248052, 5.410879715066577, 0.275]
side_table_B[0].rotation = [0, 0, 0]
freestanding_plant_medium_A[0].position = [1.4192545370240266, 8.529574499352128, 0.55]
freestanding_plant_medium_A[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [1.626331978282498, 11.467082959336743, 0.125]
wall_shelf_A[0].rotation = [0, 0, 0]
tray_with_cups_A[0].position = [3.5798975538660374, 9.149818073391106, 0.04]
tray_with_cups_A[0].rotation = [0, 0, 0]
business_card_holder[0].position = [0.7222969029255824, 8.047338672223317, 0.04]
business_card_holder[0].rotation = [0, 0, 0]
meeting_chair_D[0].position = [3.3355755385079817, 5.035891458401715, 0.46]
meeting_chair_D[0].rotation = [0, 0, 0]
wall_monitor[0].position = [7.664902316906152, 4.174325661307569, 0.425]
wall_monitor[0].rotation = [0, 0, 0]
freestanding_plant_large_A[0].position = [1.90288311547181, 11.217533728425087, 0.9]
freestanding_plant_large_A[0].rotation = [0, 0, 0]
meeting_chair_E[0].position = [1.7252806487864465, 10.486220587676636, 0.46]
meeting_chair_E[0].rotation = [0, 0, 0]
wall_art_B[0].position = [6.669322156536039, 0.3940730842312459, 0.4]
wall_art_B[0].rotation = [0, 0, 0]
freestanding_plant_large_B[0].position = [6.530326190410748, 8.936201982406631, 0.9]
freestanding_plant_large_B[0].rotation = [0, 0, 0]
console_table[0].position = [4.138393816080459, 2.0748227756994426, 0.4]
console_table[0].rotation = [0, 0, 0]
side_meeting_chair_D[0].position = [6.443826188400391, 10.183699512098869, 0.41]
side_meeting_chair_D[0].rotation = [0, 0, 0]
wall_art_C[0].position = [3.8656679420314406, 4.462527208508635, 0.4]
wall_art_C[0].rotation = [0, 0, 0]
magazine_stack[0].position = [1.2717866842038772, 10.88271315244059, 0.03]
magazine_stack[0].rotation = [0, 0, 0]
paper_cup_stack_A[0].position = [6.807405257313166, 11.80526318316458, 0.08]
paper_cup_stack_A[0].rotation = [0, 0, 0]
freestanding_plant_medium_B[0].position = [3.057153679344669, 1.2242424156353764, 0.55]
freestanding_plant_medium_B[0].rotation = [0, 0, 0]
wall_art_D[0].position = [2.9662876923858503, 11.16495865601832, 0.4]
wall_art_D[0].rotation = [0, 0, 0]
storage_shelf_A[0].position = [0.8079669355208949, 7.637971991149722, 0.95]
storage_shelf_A[0].rotation = [0, 0, 0]
storage_shelf_B[0].position = [2.721054453392428, 9.584601660302317, 0.95]
storage_shelf_B[0].rotation = [0, 0, 0]
snack_jar_A[0].position = [2.6881737951361275, 9.491586040766126, 0.1]
snack_jar_A[0].rotation = [0, 0, 0]
meeting_chair_F[0].position = [2.4916978408752604, 4.931117604831723, 0.46]
meeting_chair_F[0].rotation = [0, 0, 0]
file_box_A[0].position = [1.731095477953656, 11.736989877233608, 0.06]
file_box_A[0].rotation = [0, 0, 0]
freestanding_plant_medium_C[0].position = [3.202381326493521, 8.939401401466542, 0.55]
freestanding_plant_medium_C[0].rotation = [0, 0, 0]
snack_jar_B[0].position = [0.5295190197822164, 9.985548030618887, 0.06]
snack_jar_B[0].rotation = [0, 0, 0]
file_box_B[0].position = [3.537357066623855, 10.020666662470894, 0.06]
file_box_B[0].rotation = [0, 0, 0]
umbrella_stand[0].position = [0.5997753632906475, 5.0493796205499955, 0.3]
umbrella_stand[0].rotation = [0, 0, 0]
freestanding_plant_large_C[0].position = [6.545087813653102, 6.328996443118142, 0.9]
freestanding_plant_large_C[0].rotation = [0, 0, 0]
conference_table[0].position = [4.258196217917092, 5.410456984172319, 0.375]
conference_table[0].rotation = [0, 0, 0]
paper_cup_stack_B[0].position = [6.176762950227989, 4.077211736097179, 0.08]
paper_cup_stack_B[0].rotation = [0, 0, 0]
meeting_chair_G[0].position = [7.488364401871915, 10.169746658686782, 0.46]
meeting_chair_G[0].rotation = [0, 0, 0]
wall_art_E[0].position = [0.763909687068768, 12.165743556812723, 0.4]
wall_art_E[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [0.36468643132808953, 11.379568050227562, 0.125]
wall_shelf_B[0].rotation = [0, 0, 0]
whiteboard[0].position = [0.47668372072388454, 11.709537000032498, 0.6]
whiteboard[0].rotation = [0, 0, 0]
wall_clock[0].position = [5.81630868154928, 7.951462918966919, 0.175]
wall_clock[0].rotation = [0, 0, 0]
decorative_bowl[0].position = [6.400448014919626, 4.043186487529912, 0.06]
decorative_bowl[0].rotation = [0, 0, 0]
tray_with_cups_B[0].position = [0.8849237381865143, 7.863360727378098, 0.04]
tray_with_cups_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Helper for assigning the initial pose without replacing any asset variable.
def set_pose(asset, position, yaw_degrees):
    asset[0].position = position
    asset[0].rotation = [0, 0, radians(yaw_degrees)]


# ---------------------------------------------------------------------------
# Initial placements
# ---------------------------------------------------------------------------

# Reception/lounge seating in the lower-left portion of the room.
set_pose(side_meeting_chair_A, [2.50, 4.50, 0.41], 125)
set_pose(side_meeting_chair_B, [2.40, 2.80, 0.41], 0)
set_pose(side_meeting_chair_C, [4.40, 2.50, 0.41], 0)
set_pose(side_meeting_chair_D, [6.20, 2.50, 0.41], 180)
set_pose(side_table_A, [3.20, 2.80, 0.275], 0)
set_pose(side_table_B, [5.30, 2.50, 0.275], 0)

# The conference table occupies the broad central portion of the room.
set_pose(conference_table, [5.60, 7.00, 0.375], 0)

# Three chairs are arranged down each long side of the conference table.
# meeting_chair_F is exactly between meeting_chair_B and meeting_chair_C,
# satisfying the requested relationship between o0033, o0003, and o0011.
set_pose(meeting_chair_B, [4.35, 5.40, 0.46], 0)
set_pose(meeting_chair_F, [4.35, 7.00, 0.46], 0)
set_pose(meeting_chair_C, [4.35, 8.60, 0.46], 0)

set_pose(meeting_chair_A, [6.85, 5.40, 0.46], 180)
set_pose(meeting_chair_E, [6.85, 7.00, 0.46], 180)
set_pose(meeting_chair_G, [6.85, 8.60, 0.46], 180)

# The final meeting chair is at the head of the table. This remains well
# away from the doorway centered on the west wall at y=10.36.
set_pose(meeting_chair_D, [5.60, 10.05, 0.46], -90)

# Wall-side storage and serving furniture.
set_pose(sideboard_cabinet, [0.225, 6.50, 0.625], 0)
set_pose(credenda, [6.65, 11.75, 0.425], -90)
set_pose(console_table, [1.00, 12.80, 0.40], -90)
set_pose(storage_shelf_A, [3.00, 11.80, 0.95], -90)
set_pose(storage_shelf_B, [4.20, 11.80, 0.95], -90)

# Plants fill available wall and corner locations without obstructing the
# doorway. The required large plant o0022 is freestanding_plant_large_B.
set_pose(freestanding_plant_large_A, [1.00, 5.45, 0.90], 90)
set_pose(freestanding_plant_large_B, [0.45, 7.80, 0.90], 0)
set_pose(freestanding_plant_large_C, [7.30, 0.45, 0.90], 90)
set_pose(freestanding_plant_medium_A, [2.35, 3.70, 0.55], 0)
set_pose(freestanding_plant_medium_B, [3.20, 1.35, 0.55], 90)
set_pose(freestanding_plant_medium_C, [4.60, 0.35, 0.55], 90)

# The umbrella stand is beside, rather than in front of, the door.
set_pose(umbrella_stand, [0.14, 11.75, 0.30], 0)

# Wall-mounted decorations and presentation equipment. East-wall windows
# remain unobstructed by placing these items on the other walls.
set_pose(wall_art_A, [0.02, 8.80, 1.70], 0)
set_pose(wall_art_B, [5.00, 0.02, 1.70], 90)
set_pose(wall_art_C, [0.02, 5.55, 1.70], 0)
set_pose(wall_art_D, [5.15, 11.98, 1.70], -90)
set_pose(wall_art_E, [7.20, 0.02, 1.70], 90)
set_pose(wall_monitor, [6.10, 0.04, 1.55], 90)
set_pose(whiteboard, [0.025, 8.00, 1.70], 0)
set_pose(wall_clock, [3.80, 11.975, 2.25], -90)
set_pose(wall_shelf_A, [0.125, 6.45, 1.45], 0)
set_pose(wall_shelf_B, [2.45, 11.875, 1.45], -90)

# Small objects are initialized directly above their supporting surfaces.
set_pose(desk_organizer, [0.225, 6.25, 1.41], 0)
set_pose(sign_in_sheet, [0.75, 12.80, 0.805], -90)
set_pose(business_card_holder, [1.20, 12.80, 0.84], -90)
set_pose(decorative_bowl, [1.00, 12.80, 0.86], 0)

set_pose(tray_with_cups_A, [3.20, 2.80, 0.59], 0)
set_pose(magazine_stack, [5.30, 2.50, 0.58], 0)
set_pose(tray_with_cups_B, [5.60, 7.00, 0.79], 0)

# Both cup stacks form a small service arrangement on the credenda.
set_pose(paper_cup_stack_A, [6.35, 11.75, 0.93], -90)
set_pose(paper_cup_stack_B, [6.65, 11.75, 0.93], -90)

# Shelf-top storage objects are separated horizontally.
set_pose(snack_jar_A, [0.125, 6.25, 1.675], 0)
set_pose(snack_jar_B, [2.30, 11.875, 1.635], -90)
set_pose(file_box_A, [2.80, 11.80, 1.96], -90)
set_pose(file_box_B, [4.20, 11.80, 1.96], -90)


# ---------------------------------------------------------------------------
# Important semantic constraints
# ---------------------------------------------------------------------------

# Required support relationship: paper cup stack o0027 is on credenda o0007.
solver.on_top_of(paper_cup_stack_A[0], credenda[0])

# Other small objects must also remain on usable supporting surfaces.
solver.on_top_of(desk_organizer[0], sideboard_cabinet[0])
solver.on_top_of(sign_in_sheet[0], console_table[0])
solver.on_top_of(business_card_holder[0], console_table[0])
solver.on_top_of(decorative_bowl[0], console_table[0])
solver.on_top_of(tray_with_cups_A[0], side_table_A[0])
solver.on_top_of(magazine_stack[0], side_table_B[0])
solver.on_top_of(tray_with_cups_B[0], conference_table[0])
solver.on_top_of(paper_cup_stack_B[0], credenda[0])
solver.on_top_of(snack_jar_A[0], wall_shelf_A[0])
solver.on_top_of(snack_jar_B[0], wall_shelf_B[0])
solver.on_top_of(file_box_A[0], storage_shelf_A[0])
solver.on_top_of(file_box_B[0], storage_shelf_B[0])

# Required large plant o0022 is placed against the west wall.
solver.against_wall(freestanding_plant_large_B[0], walls[9])

# Required facing relationship for side meeting chair o0000.
solver.point_towards(
    side_meeting_chair_A[0],
    freestanding_plant_large_B[0],
)

# Enforce the requested "between" relationship. Equal distances plus the
# initialized collinear positions keep meeting_chair_F at the midpoint.
solver.distance_constraint(
    meeting_chair_F[0], meeting_chair_B[0], 1.60, 1.60, weight=10
)
solver.distance_constraint(
    meeting_chair_F[0], meeting_chair_C[0], 1.60, 1.60, weight=10
)
solver.align_with(meeting_chair_F[0], meeting_chair_B[0])


# ---------------------------------------------------------------------------
# Wall relationships
# ---------------------------------------------------------------------------

solver.against_wall(sideboard_cabinet[0], walls[9])
solver.against_wall(credenda[0], walls[6])
solver.against_wall(console_table[0], walls[8])
solver.against_wall(storage_shelf_A[0], walls[6])
solver.against_wall(storage_shelf_B[0], walls[6])

solver.against_wall(freestanding_plant_large_A[0], walls[0])
solver.against_wall(freestanding_plant_large_C[0], walls[4])
solver.against_wall(freestanding_plant_medium_A[0], walls[1])
solver.against_wall(freestanding_plant_medium_B[0], walls[2])
solver.against_wall(freestanding_plant_medium_C[0], walls[4])
solver.against_wall(umbrella_stand[0], walls[9])

solver.against_wall(wall_art_A[0], walls[9])
solver.against_wall(wall_art_B[0], walls[4])
solver.against_wall(wall_art_C[0], walls[9])
solver.against_wall(wall_art_D[0], walls[6])
solver.against_wall(wall_art_E[0], walls[4])
solver.against_wall(wall_monitor[0], walls[4])
solver.against_wall(whiteboard[0], walls[9])
solver.against_wall(wall_clock[0], walls[6])
solver.against_wall(wall_shelf_A[0], walls[9])
solver.against_wall(wall_shelf_B[0], walls[6])


# ---------------------------------------------------------------------------
# Position and orientation constraints for every new asset
# ---------------------------------------------------------------------------

# These fixed-pose references preserve the planned non-overlapping layout
# while still allowing the higher-priority semantic constraints above to
# make small feasibility adjustments.
def constrain_to_planned_pose(asset):
    instance = asset[0]
    planned_pose = AssetInstance(
        position=list(instance.position),
        rotation=list(instance.rotation),
    )
    solver.distance_constraint(
        instance, planned_pose, 0.0, 0.0, weight=10
    )
    solver.align_with(instance, planned_pose)


all_new_assets = [
    side_meeting_chair_A,
    desk_organizer,
    meeting_chair_A,
    meeting_chair_B,
    sideboard_cabinet,
    side_meeting_chair_B,
    wall_art_A,
    credenda,
    sign_in_sheet,
    side_meeting_chair_C,
    side_table_A,
    meeting_chair_C,
    side_table_B,
    freestanding_plant_medium_A,
    wall_shelf_A,
    tray_with_cups_A,
    business_card_holder,
    meeting_chair_D,
    wall_monitor,
    freestanding_plant_large_A,
    meeting_chair_E,
    wall_art_B,
    freestanding_plant_large_B,
    console_table,
    side_meeting_chair_D,
    wall_art_C,
    magazine_stack,
    paper_cup_stack_A,
    freestanding_plant_medium_B,
    wall_art_D,
    storage_shelf_A,
    storage_shelf_B,
    snack_jar_A,
    meeting_chair_F,
    file_box_A,
    freestanding_plant_medium_C,
    snack_jar_B,
    file_box_B,
    umbrella_stand,
    freestanding_plant_large_C,
    conference_table,
    paper_cup_stack_B,
    meeting_chair_G,
    wall_art_E,
    wall_shelf_B,
    whiteboard,
    wall_clock,
    decorative_bowl,
    tray_with_cups_B,
]

for new_asset in all_new_assets:
    constrain_to_planned_pose(new_asset)

solver.constraints = []
console_table[0].position = [1.0, 12.798225402832031, 0.4000000059604645]
console_table[0].rotation = [0, 0, -1.573636023986457]
console_table[0].optimize = 2
storage_shelf_B[0].position = [4.199999809265137, 11.673166275024414, 0.949999988079071]
storage_shelf_B[0].rotation = [0, 0, -1.2991298281446948]
storage_shelf_B[0].optimize = 2
meeting_chair_B[0].position = [4.349999904632568, 5.400000095367432, 0.46000000834465027]
meeting_chair_B[0].rotation = [0, 0, 0.0157079639172164]
meeting_chair_B[0].optimize = 2
umbrella_stand[0].position = [0.13858340680599213, 11.75, 0.30000001192092896]
umbrella_stand[0].rotation = [0, 0, 0.0010356356478421645]
umbrella_stand[0].optimize = 2
paper_cup_stack_B[0].position = [6.650000095367432, 11.75, 0.9300000071525574]
paper_cup_stack_B[0].rotation = [0, 0, -1.5582299555380688]
paper_cup_stack_B[0].optimize = 2
business_card_holder[0].position = [1.2000000476837158, 12.800000190734863, 0.8400000333786011]
business_card_holder[0].rotation = [0, 0, -1.5582299555380688]
business_card_holder[0].optimize = 2
freestanding_plant_medium_B[0].position = [3.200000047683716, 1.3497995138168335, 0.550000011920929]
freestanding_plant_medium_B[0].rotation = [0, 0, 1.5718295495260954]
freestanding_plant_medium_B[0].optimize = 2
freestanding_plant_large_B[0].position = [0.4513935446739197, 7.800000190734863, 0.8999999761581421]
freestanding_plant_large_B[0].rotation = [0, 0, -0.002718511803642318]
freestanding_plant_large_B[0].optimize = 2
meeting_chair_D[0].position = [5.599999904632568, 10.050000190734863, 0.46000000834465027]
meeting_chair_D[0].rotation = [0, 0, -1.5613715493341729]
meeting_chair_D[0].optimize = 2
wall_shelf_B[0].position = [2.5018844604492188, 11.8736572265625, 0.125]
wall_shelf_B[0].rotation = [0, 0, -1.573531218259838]
wall_shelf_B[0].optimize = 2
freestanding_plant_medium_A[0].position = [2.349802255630493, 3.700000047683716, 0.550000011920929]
freestanding_plant_medium_A[0].rotation = [0, 0, 0.0010332268115500363]
freestanding_plant_medium_A[0].optimize = 2
side_meeting_chair_A[0].position = [2.5, 4.5, 0.4099999964237213]
side_meeting_chair_A[0].rotation = [0, 0, 2.1942279429244693]
side_meeting_chair_A[0].optimize = 2
wall_art_C[0].position = [0.017607148736715317, 5.550000190734863, 0.4000000059604645]
wall_art_C[0].rotation = [0, 0, 0.0010371943527360471]
wall_art_C[0].optimize = 2
wall_art_D[0].position = [5.150000095367432, 11.982559204101562, 0.4000000059604645]
wall_art_D[0].rotation = [0, 0, -1.569759093509333]
wall_art_D[0].optimize = 2
freestanding_plant_large_A[0].position = [1.0, 5.450376033782959, 0.8999999761581421]
freestanding_plant_large_A[0].rotation = [0, 0, 1.5718285179650338]
freestanding_plant_large_A[0].optimize = 2
freestanding_plant_large_C[0].position = [7.300000190734863, 0.4503731429576874, 0.8999999761581421]
freestanding_plant_large_C[0].rotation = [0, 0, 1.5718285392549578]
freestanding_plant_large_C[0].optimize = 2
wall_monitor[0].position = [6.099999904632568, 0.04152729734778404, 0.42500001192092896]
wall_monitor[0].rotation = [0, 0, 1.571833019351665]
wall_monitor[0].optimize = 2
storage_shelf_A[0].position = [3.0, 11.798744201660156, 0.949999988079071]
storage_shelf_A[0].rotation = [0, 0, -1.5735126680028746]
storage_shelf_A[0].optimize = 2
side_table_A[0].position = [3.200000047683716, 2.799999952316284, 0.2750000059604645]
side_table_A[0].rotation = [0, 0, 0.01256637125682779]
side_table_A[0].optimize = 2
desk_organizer[0].position = [0.22499999403953552, 6.25, 1.409999966621399]
desk_organizer[0].rotation = [0, 0, 0.01256637125682779]
desk_organizer[0].optimize = 2
magazine_stack[0].position = [5.300000190734863, 2.5, 0.5799999833106995]
magazine_stack[0].rotation = [0, 0, 0.01256637125682779]
magazine_stack[0].optimize = 2
side_table_B[0].position = [5.300000190734863, 2.5, 0.2750000059604645]
side_table_B[0].rotation = [0, 0, 0.01256637125682779]
side_table_B[0].optimize = 2
whiteboard[0].position = [0.02783918008208275, 8.0, 0.6000000238418579]
whiteboard[0].rotation = [0, 0, 0.001036156000901074]
whiteboard[0].optimize = 2
sideboard_cabinet[0].position = [0.2262735664844513, 6.5, 0.625]
sideboard_cabinet[0].rotation = [0, 0, -0.002716885328334093]
sideboard_cabinet[0].optimize = 2
file_box_A[0].position = [2.799999952316284, 11.800000190734863, 1.959999918937683]
file_box_A[0].rotation = [0, 0, -1.5582299555380688]
file_box_A[0].optimize = 2
credenda[0].position = [6.650000095367432, 11.752976417541504, 0.42500001192092896]
credenda[0].rotation = [0, 0, -1.5750167290498345]
credenda[0].optimize = 2
meeting_chair_F[0].position = [4.349999904632568, 7.0, 0.46000000834465027]
meeting_chair_F[0].rotation = [0, 0, 0.015295042882416924]
meeting_chair_F[0].optimize = 2
decorative_bowl[0].position = [1.0, 12.800000190734863, 0.8600000143051147]
decorative_bowl[0].rotation = [0, 0, 0.01256637125682779]
decorative_bowl[0].optimize = 2
side_meeting_chair_C[0].position = [4.400000095367432, 2.5, 0.4099999964237213]
side_meeting_chair_C[0].rotation = [0, 0, 0.00942477746072377]
side_meeting_chair_C[0].optimize = 2
wall_art_E[0].position = [7.199999809265137, 0.017607152462005615, 0.4000000059604645]
wall_art_E[0].rotation = [0, 0, 1.5718335211476326]
wall_art_E[0].optimize = 2
freestanding_plant_medium_C[0].position = [4.599999904632568, 0.34979990124702454, 0.550000011920929]
freestanding_plant_medium_C[0].rotation = [0, 0, 1.5718295502545634]
freestanding_plant_medium_C[0].optimize = 2
wall_clock[0].position = [3.799999952316284, 11.977560997009277, 0.17499999701976776]
wall_clock[0].rotation = [0, 0, -1.5697591320237838]
wall_clock[0].optimize = 2
paper_cup_stack_A[0].position = [6.349999904632568, 11.75, 0.9300000071525574]
paper_cup_stack_A[0].rotation = [0, 0, -1.5582299555380688]
paper_cup_stack_A[0].optimize = 2
file_box_B[0].position = [4.199999809265137, 11.800000190734863, 1.959999918937683]
file_box_B[0].rotation = [0, 0, -1.5582299555380688]
file_box_B[0].optimize = 2
meeting_chair_G[0].position = [6.849999904632568, 8.600000381469727, 0.46000000834465027]
meeting_chair_G[0].rotation = [0, 0, -3.1321678761290697]
meeting_chair_G[0].optimize = 2
snack_jar_B[0].position = [2.299999952316284, 11.875, 0.3100000023841858]
snack_jar_B[0].rotation = [0, 0, -1.5582299555380688]
snack_jar_B[0].optimize = 2
conference_table[0].position = [5.599999904632568, 7.0, 0.375]
conference_table[0].rotation = [0, 0, 0.01256637125682779]
conference_table[0].optimize = 2
wall_shelf_A[0].position = [0.12634173035621643, 6.449999809265137, 0.125]
wall_shelf_A[0].rotation = [0, 0, -0.002715639917058449]
wall_shelf_A[0].optimize = 2
meeting_chair_C[0].position = [4.349999904632568, 8.600000381469727, 0.46000000834465027]
meeting_chair_C[0].rotation = [0, 0, 0.01256637125682779]
meeting_chair_C[0].optimize = 2
side_meeting_chair_D[0].position = [6.199999809265137, 2.5, 0.4099999964237213]
side_meeting_chair_D[0].rotation = [0, 0, -3.1321678761290697]
side_meeting_chair_D[0].optimize = 2
meeting_chair_A[0].position = [6.849999904632568, 5.400000095367432, 0.46000000834465027]
meeting_chair_A[0].rotation = [0, 0, -3.1321678761290697]
meeting_chair_A[0].optimize = 2
tray_with_cups_B[0].position = [5.599999904632568, 7.0, 0.7900000214576721]
tray_with_cups_B[0].rotation = [0, 0, 0.01256637125682779]
tray_with_cups_B[0].optimize = 2
wall_art_A[0].position = [0.017607148736715317, 8.800000190734863, 0.4000000059604645]
wall_art_A[0].rotation = [0, 0, 0.0010371943527360471]
wall_art_A[0].optimize = 2
snack_jar_A[0].position = [0.125, 6.25, 0.3499999940395355]
snack_jar_A[0].rotation = [0, 0, 0.01256637125682779]
snack_jar_A[0].optimize = 2
sign_in_sheet[0].position = [0.75, 12.800000190734863, 0.8050000071525574]
sign_in_sheet[0].rotation = [0, 0, -1.5582299555380688]
sign_in_sheet[0].optimize = 2
wall_art_B[0].position = [5.0, 0.017607152462005615, 0.4000000059604645]
wall_art_B[0].rotation = [0, 0, 1.5718335211476326]
wall_art_B[0].optimize = 2
side_meeting_chair_B[0].position = [2.4000000953674316, 2.799999952316284, 0.4099999964237213]
side_meeting_chair_B[0].rotation = [0, 0, 0.00942477746072377]
side_meeting_chair_B[0].optimize = 2
tray_with_cups_A[0].position = [3.200000047683716, 2.799999952316284, 0.5900000333786011]
tray_with_cups_A[0].rotation = [0, 0, 0.01256637125682779]
tray_with_cups_A[0].optimize = 2
meeting_chair_E[0].position = [6.849999904632568, 7.0, 0.46000000834465027]
meeting_chair_E[0].rotation = [0, 0, -3.1321678761290697]
meeting_chair_E[0].optimize = 2

