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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[10.00, 0.00, 0.00]),
    Wall(corner1=[10.00, 0.00, 0.00], corner2=[10.00, 7.50, 0.00]),
    Wall(corner1=[10.00, 7.50, 0.00], corner2=[0.00, 7.50, 0.00]),
    Wall(corner1=[0.00, 7.50, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
reading_chair_A = Assets(description="reading chair", size=[0.72, 0.65, 0.88], placements=[AssetInstance() for _ in range(1)])
open_hardcover_book_A = Assets(description="open hardcover book", size=[0.28, 0.44, 0.04], placements=[AssetInstance() for _ in range(1)])
handout_sheet = Assets(description="handout sheet", size=[0.30, 0.21, 0.00], placements=[AssetInstance() for _ in range(1)])
lounge_chair_A = Assets(description="lounge chair", size=[0.90, 0.85, 0.85], placements=[AssetInstance() for _ in range(1)])
reading_chair_B = Assets(description="reading chair", size=[0.72, 0.65, 0.88], placements=[AssetInstance() for _ in range(1)])
engraving_print = Assets(description="engraving print", size=[0.03, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])
highlighter_marker = Assets(description="highlighter marker", size=[0.14, 0.03, 0.02], placements=[AssetInstance() for _ in range(1)])
art_book_A = Assets(description="art book", size=[0.33, 0.26, 0.04], placements=[AssetInstance() for _ in range(1)])
drink_coaster = Assets(description="drink coaster", size=[0.10, 0.10, 0.01], placements=[AssetInstance() for _ in range(1)])
typography_poster = Assets(description="typography poster", size=[0.02, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
notepad_A = Assets(description="notepad", size=[0.21, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
photograph_print = Assets(description="photograph print", size=[0.03, 0.40, 0.30], placements=[AssetInstance() for _ in range(1)])
whiteboard = Assets(description="whiteboard", size=[0.05, 1.50, 1.00], placements=[AssetInstance() for _ in range(1)])
hardcover_book_A = Assets(description="hardcover book", size=[0.24, 0.16, 0.04], placements=[AssetInstance() for _ in range(1)])
potted_succulent_A = Assets(description="potted succulent", size=[0.15, 0.15, 0.22], placements=[AssetInstance() for _ in range(1)])
bookshelf_A = Assets(description="bookshelf", size=[0.32, 1.00, 2.10], placements=[AssetInstance() for _ in range(1)])
desk_lamp = Assets(description="desk lamp", size=[0.35, 0.22, 0.48], placements=[AssetInstance() for _ in range(1)])
bookcase_A = Assets(description="bookcase", size=[0.35, 0.90, 2.10], placements=[AssetInstance() for _ in range(1)])
paperback_book_A = Assets(description="paperback book", size=[0.13, 0.03, 0.20], placements=[AssetInstance() for _ in range(1)])
dining_table_A = Assets(description="dining table", size=[1.00, 2.40, 0.75], placements=[AssetInstance() for _ in range(1)])
illustration_print_A = Assets(description="illustration print", size=[0.03, 0.40, 0.50], placements=[AssetInstance() for _ in range(1)])
clock = Assets(description="clock", size=[0.04, 0.35, 0.35], placements=[AssetInstance() for _ in range(1)])
coffee_mug_A = Assets(description="coffee mug", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
paperback_book_B = Assets(description="paperback book", size=[0.13, 0.02, 0.20], placements=[AssetInstance() for _ in range(1)])
floor_lamp = Assets(description="floor lamp", size=[0.40, 0.40, 1.65], placements=[AssetInstance() for _ in range(1)])
reading_chair_C = Assets(description="reading chair", size=[0.72, 0.65, 0.88], placements=[AssetInstance() for _ in range(1)])
potted_succulent_B = Assets(description="potted succulent", size=[0.18, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
hardcover_book_B = Assets(description="hardcover book", size=[0.17, 0.04, 0.25], placements=[AssetInstance() for _ in range(1)])
bookshelf_B = Assets(description="bookshelf", size=[0.32, 1.00, 2.10], placements=[AssetInstance() for _ in range(1)])
side_table = Assets(description="side table", size=[0.65, 0.65, 0.52], placements=[AssetInstance() for _ in range(1)])
bookcase_B = Assets(description="bookcase", size=[0.35, 0.90, 2.10], placements=[AssetInstance() for _ in range(1)])
ballpoint_pen_A = Assets(description="ballpoint pen", size=[0.14, 0.01, 0.01], placements=[AssetInstance() for _ in range(1)])
bookcase_C = Assets(description="bookcase", size=[0.35, 1.20, 2.10], placements=[AssetInstance() for _ in range(1)])
pencil = Assets(description="pencil", size=[0.19, 0.01, 0.01], placements=[AssetInstance() for _ in range(1)])
dining_table_B = Assets(description="dining table", size=[1.00, 2.40, 0.75], placements=[AssetInstance() for _ in range(1)])
illustration_print_B = Assets(description="illustration print", size=[0.03, 0.40, 0.50], placements=[AssetInstance() for _ in range(1)])
pen_holder_cup = Assets(description="pen holder cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
paperback_book_C = Assets(description="paperback book", size=[0.13, 0.02, 0.20], placements=[AssetInstance() for _ in range(1)])
hardcover_book_C = Assets(description="hardcover book", size=[0.17, 0.04, 0.25], placements=[AssetInstance() for _ in range(1)])
photocopier = Assets(description="photocopier", size=[0.72, 0.65, 1.10], placements=[AssetInstance() for _ in range(1)])
ballpoint_pen_B = Assets(description="ballpoint pen", size=[0.14, 0.01, 0.01], placements=[AssetInstance() for _ in range(1)])
notepad_B = Assets(description="notepad", size=[0.21, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
reading_chair_D = Assets(description="reading chair", size=[0.72, 0.65, 0.88], placements=[AssetInstance() for _ in range(1)])
art_book_B = Assets(description="art book", size=[0.33, 0.26, 0.04], placements=[AssetInstance() for _ in range(1)])
printed_page_A = Assets(description="printed page", size=[0.30, 0.21, 0.00], placements=[AssetInstance() for _ in range(1)])
paperback_book_D = Assets(description="paperback book", size=[0.13, 0.03, 0.20], placements=[AssetInstance() for _ in range(1)])
reading_chair_E = Assets(description="reading chair", size=[0.72, 0.65, 0.88], placements=[AssetInstance() for _ in range(1)])
hardcover_library_book = Assets(description="hardcover library book", size=[0.17, 0.04, 0.25], placements=[AssetInstance() for _ in range(1)])
open_hardcover_book_B = Assets(description="open hardcover book", size=[0.28, 0.44, 0.04], placements=[AssetInstance() for _ in range(1)])
mirror = Assets(description="mirror", size=[0.03, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
printed_page_B = Assets(description="printed page", size=[0.30, 0.21, 0.00], placements=[AssetInstance() for _ in range(1)])
coffee_mug_B = Assets(description="coffee mug", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
base_cabinet = Assets(description="base cabinet", size=[0.50, 1.20, 0.85], placements=[AssetInstance() for _ in range(1)])
lounge_chair_B = Assets(description="lounge chair", size=[0.90, 0.85, 0.85], placements=[AssetInstance() for _ in range(1)])
reading_chair_F = Assets(description="reading chair", size=[0.72, 0.65, 0.88], placements=[AssetInstance() for _ in range(1)])
paperback_book_E = Assets(description="paperback book", size=[0.13, 0.02, 0.20], placements=[AssetInstance() for _ in range(1)])
paperback_book_F = Assets(description="paperback book", size=[0.13, 0.03, 0.20], placements=[AssetInstance() for _ in range(1)])
bookcase_D = Assets(description="bookcase", size=[0.35, 0.90, 2.10], placements=[AssetInstance() for _ in range(1)])
printed_page_C = Assets(description="printed page", size=[0.30, 0.21, 0.00], placements=[AssetInstance() for _ in range(1)])
sign = Assets(description="sign", size=[0.01, 0.45, 0.18], placements=[AssetInstance() for _ in range(1)])
reading_chair_G = Assets(description="reading chair", size=[0.72, 0.65, 0.88], placements=[AssetInstance() for _ in range(1)])
paperback_book_G = Assets(description="paperback book", size=[0.13, 0.02, 0.20], placements=[AssetInstance() for _ in range(1)])
reading_chair_H = Assets(description="reading chair", size=[0.72, 0.65, 0.88], placements=[AssetInstance() for _ in range(1)])
hardcover_book_D = Assets(description="hardcover book", size=[0.17, 0.04, 0.25], placements=[AssetInstance() for _ in range(1)])
art_print = Assets(description="art print", size=[0.03, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
bookcase_E = Assets(description="bookcase", size=[0.35, 0.90, 2.10], placements=[AssetInstance() for _ in range(1)])
paperback_book_H = Assets(description="paperback book", size=[0.13, 0.02, 0.20], placements=[AssetInstance() for _ in range(1)])

reading_chair_A[0].instance_id = 'reading_chair_A_0'
open_hardcover_book_A[0].instance_id = 'open_hardcover_book_A_0'
handout_sheet[0].instance_id = 'handout_sheet_0'
lounge_chair_A[0].instance_id = 'lounge_chair_A_0'
reading_chair_B[0].instance_id = 'reading_chair_B_0'
engraving_print[0].instance_id = 'engraving_print_0'
highlighter_marker[0].instance_id = 'highlighter_marker_0'
art_book_A[0].instance_id = 'art_book_A_0'
drink_coaster[0].instance_id = 'drink_coaster_0'
typography_poster[0].instance_id = 'typography_poster_0'
notepad_A[0].instance_id = 'notepad_A_0'
photograph_print[0].instance_id = 'photograph_print_0'
whiteboard[0].instance_id = 'whiteboard_0'
hardcover_book_A[0].instance_id = 'hardcover_book_A_0'
potted_succulent_A[0].instance_id = 'potted_succulent_A_0'
bookshelf_A[0].instance_id = 'bookshelf_A_0'
desk_lamp[0].instance_id = 'desk_lamp_0'
bookcase_A[0].instance_id = 'bookcase_A_0'
paperback_book_A[0].instance_id = 'paperback_book_A_0'
dining_table_A[0].instance_id = 'dining_table_A_0'
illustration_print_A[0].instance_id = 'illustration_print_A_0'
clock[0].instance_id = 'clock_0'
coffee_mug_A[0].instance_id = 'coffee_mug_A_0'
paperback_book_B[0].instance_id = 'paperback_book_B_0'
floor_lamp[0].instance_id = 'floor_lamp_0'
reading_chair_C[0].instance_id = 'reading_chair_C_0'
potted_succulent_B[0].instance_id = 'potted_succulent_B_0'
hardcover_book_B[0].instance_id = 'hardcover_book_B_0'
bookshelf_B[0].instance_id = 'bookshelf_B_0'
side_table[0].instance_id = 'side_table_0'
bookcase_B[0].instance_id = 'bookcase_B_0'
ballpoint_pen_A[0].instance_id = 'ballpoint_pen_A_0'
bookcase_C[0].instance_id = 'bookcase_C_0'
pencil[0].instance_id = 'pencil_0'
dining_table_B[0].instance_id = 'dining_table_B_0'
illustration_print_B[0].instance_id = 'illustration_print_B_0'
pen_holder_cup[0].instance_id = 'pen_holder_cup_0'
paperback_book_C[0].instance_id = 'paperback_book_C_0'
hardcover_book_C[0].instance_id = 'hardcover_book_C_0'
photocopier[0].instance_id = 'photocopier_0'
ballpoint_pen_B[0].instance_id = 'ballpoint_pen_B_0'
notepad_B[0].instance_id = 'notepad_B_0'
reading_chair_D[0].instance_id = 'reading_chair_D_0'
art_book_B[0].instance_id = 'art_book_B_0'
printed_page_A[0].instance_id = 'printed_page_A_0'
paperback_book_D[0].instance_id = 'paperback_book_D_0'
reading_chair_E[0].instance_id = 'reading_chair_E_0'
hardcover_library_book[0].instance_id = 'hardcover_library_book_0'
open_hardcover_book_B[0].instance_id = 'open_hardcover_book_B_0'
mirror[0].instance_id = 'mirror_0'
printed_page_B[0].instance_id = 'printed_page_B_0'
coffee_mug_B[0].instance_id = 'coffee_mug_B_0'
base_cabinet[0].instance_id = 'base_cabinet_0'
lounge_chair_B[0].instance_id = 'lounge_chair_B_0'
reading_chair_F[0].instance_id = 'reading_chair_F_0'
paperback_book_E[0].instance_id = 'paperback_book_E_0'
paperback_book_F[0].instance_id = 'paperback_book_F_0'
bookcase_D[0].instance_id = 'bookcase_D_0'
printed_page_C[0].instance_id = 'printed_page_C_0'
sign[0].instance_id = 'sign_0'
reading_chair_G[0].instance_id = 'reading_chair_G_0'
paperback_book_G[0].instance_id = 'paperback_book_G_0'
reading_chair_H[0].instance_id = 'reading_chair_H_0'
hardcover_book_D[0].instance_id = 'hardcover_book_D_0'
art_print[0].instance_id = 'art_print_0'
bookcase_E[0].instance_id = 'bookcase_E_0'
paperback_book_H[0].instance_id = 'paperback_book_H_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

reading_chair_A[0].position = [1.4754943160816814, 4.603682601648005, 0.44]
reading_chair_A[0].rotation = [0, 0, 0]
open_hardcover_book_A[0].position = [9.378391326064165, 5.2373185107345135, 0.02]
open_hardcover_book_A[0].rotation = [0, 0, 0]
handout_sheet[0].position = [7.423385145572735, 0.4398720056584668, 5e-05]
handout_sheet[0].rotation = [0, 0, 0]
lounge_chair_A[0].position = [7.276053832442358, 0.7055034196333987, 0.425]
lounge_chair_A[0].rotation = [0, 0, 0]
reading_chair_B[0].position = [7.758569693900879, 6.784877062747685, 0.44]
reading_chair_B[0].rotation = [0, 0, 0]
engraving_print[0].position = [5.605789999684046, 4.436110277279917, 0.3]
engraving_print[0].rotation = [0, 0, 0]
highlighter_marker[0].position = [8.54763472056437, 4.465480278328469, 0.009]
highlighter_marker[0].rotation = [0, 0, 0]
art_book_A[0].position = [6.849172792042873, 0.32223093199698544, 0.0175]
art_book_A[0].rotation = [0, 0, 0]
drink_coaster[0].position = [9.521529000341841, 6.5293178337341065, 0.003]
drink_coaster[0].rotation = [0, 0, 0]
typography_poster[0].position = [3.544267079048291, 6.407790750737907, 0.35]
typography_poster[0].rotation = [0, 0, 0]
notepad_A[0].position = [6.35041402228136, 4.848801258239399, 0.006]
notepad_A[0].rotation = [0, 0, 0]
photograph_print[0].position = [4.196300834038311, 0.6993304868009387, 0.15]
photograph_print[0].rotation = [0, 0, 0]
whiteboard[0].position = [6.969858321012844, 4.976446799075365, 0.5]
whiteboard[0].rotation = [0, 0, 0]
hardcover_book_A[0].position = [1.3037353273096919, 2.776683835189204, 0.0175]
hardcover_book_A[0].rotation = [0, 0, 0]
potted_succulent_A[0].position = [6.9383156499695335, 6.474987255258019, 0.11]
potted_succulent_A[0].rotation = [0, 0, 0]
bookshelf_A[0].position = [8.118165455612994, 5.117388564434183, 1.05]
bookshelf_A[0].rotation = [0, 0, 0]
desk_lamp[0].position = [3.2874464113435433, 0.6286440958201858, 0.24]
desk_lamp[0].rotation = [0, 0, 0]
bookcase_A[0].position = [6.144325682936812, 5.853096789604033, 1.05]
bookcase_A[0].rotation = [0, 0, 0]
paperback_book_A[0].position = [1.469704254899965, 6.928227652758688, 0.1]
paperback_book_A[0].rotation = [0, 0, 0]
dining_table_A[0].position = [6.234360760691927, 2.2111402733970826, 0.375]
dining_table_A[0].rotation = [0, 0, 0]
illustration_print_A[0].position = [7.693054484009114, 3.197641465822653, 0.25]
illustration_print_A[0].rotation = [0, 0, 0]
clock[0].position = [0.536960620739444, 0.6427209569783607, 0.175]
clock[0].rotation = [0, 0, 0]
coffee_mug_A[0].position = [6.2364572537193865, 6.026991486081608, 0.05]
coffee_mug_A[0].rotation = [0, 0, 0]
paperback_book_B[0].position = [7.599679389675002, 3.7143266863233473, 0.1]
paperback_book_B[0].rotation = [0, 0, 0]
floor_lamp[0].position = [0.98989337095438, 0.17137077741377627, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
reading_chair_C[0].position = [3.817922939470227, 1.5260921567388543, 0.44]
reading_chair_C[0].rotation = [0, 0, 0]
potted_succulent_B[0].position = [2.0079400983912645, 1.1421712900097711, 0.125]
potted_succulent_B[0].rotation = [0, 0, 0]
hardcover_book_B[0].position = [4.825608789772438, 1.624248658370142, 0.125]
hardcover_book_B[0].rotation = [0, 0, 0]
bookshelf_B[0].position = [1.172704371321941, 1.9503554526767541, 1.05]
bookshelf_B[0].rotation = [0, 0, 0]
side_table[0].position = [1.8294268169756522, 1.3327789407230495, 0.26]
side_table[0].rotation = [0, 0, 0]
bookcase_B[0].position = [2.412575492789595, 4.690239581723441, 1.05]
bookcase_B[0].rotation = [0, 0, 0]
ballpoint_pen_A[0].position = [2.4712675305725296, 1.1090567153984945, 0.006]
ballpoint_pen_A[0].rotation = [0, 0, 0]
bookcase_C[0].position = [3.034348859129563, 1.3376298114520102, 1.05]
bookcase_C[0].rotation = [0, 0, 0]
pencil[0].position = [9.970343901188116, 3.484098700628767, 0.0035]
pencil[0].rotation = [0, 0, 0]
dining_table_B[0].position = [6.626980028886901, 6.813994841345772, 0.375]
dining_table_B[0].rotation = [0, 0, 0]
illustration_print_B[0].position = [5.129251409478169, 4.3491949862406205, 0.25]
illustration_print_B[0].rotation = [0, 0, 0]
pen_holder_cup[0].position = [1.9989953051720355, 3.480495726522408, 0.055]
pen_holder_cup[0].rotation = [0, 0, 0]
paperback_book_C[0].position = [9.045540545360373, 2.24583214342117, 0.1]
paperback_book_C[0].rotation = [0, 0, 0]
hardcover_book_C[0].position = [2.0885590149749076, 7.481583812094707, 0.125]
hardcover_book_C[0].rotation = [0, 0, 0]
photocopier[0].position = [0.19129166888454452, 7.125677068227212, 0.55]
photocopier[0].rotation = [0, 0, 0]
ballpoint_pen_B[0].position = [4.395443778035341, 0.1898564927327337, 0.006]
ballpoint_pen_B[0].rotation = [0, 0, 0]
notepad_B[0].position = [2.6313933704514314, 6.267121681180071, 0.006]
notepad_B[0].rotation = [0, 0, 0]
reading_chair_D[0].position = [6.316507050249802, 0.41231273602971574, 0.44]
reading_chair_D[0].rotation = [0, 0, 0]
art_book_B[0].position = [2.0459829919365333, 2.0185633243256866, 0.02]
art_book_B[0].rotation = [0, 0, 0]
printed_page_A[0].position = [0.05286608239730817, 5.708391542121162, 5e-05]
printed_page_A[0].rotation = [0, 0, 0]
paperback_book_D[0].position = [0.6100805986786695, 3.7235786606387995, 0.1]
paperback_book_D[0].rotation = [0, 0, 0]
reading_chair_E[0].position = [2.0105128609896115, 5.8764620855337375, 0.44]
reading_chair_E[0].rotation = [0, 0, 0]
hardcover_library_book[0].position = [9.169786460324922, 2.2654352845404793, 0.125]
hardcover_library_book[0].rotation = [0, 0, 0]
open_hardcover_book_B[0].position = [2.0685031780156846, 6.0237137165478005, 0.02]
open_hardcover_book_B[0].rotation = [0, 0, 0]
mirror[0].position = [6.895781865502339, 2.3860243832901866, 0.45]
mirror[0].rotation = [0, 0, 0]
printed_page_B[0].position = [5.549942331918723, 1.4840434406058973, 5e-05]
printed_page_B[0].rotation = [0, 0, 0]
coffee_mug_B[0].position = [7.831466348612778, 1.3553606344647826, 0.05]
coffee_mug_B[0].rotation = [0, 0, 0]
base_cabinet[0].position = [9.785811496415125, 2.088486085226086, 0.425]
base_cabinet[0].rotation = [0, 0, 0]
lounge_chair_B[0].position = [0.3540170329711567, 1.3809303873314258, 0.425]
lounge_chair_B[0].rotation = [0, 0, 0]
reading_chair_F[0].position = [8.141124950771722, 4.184759929116367, 0.44]
reading_chair_F[0].rotation = [0, 0, 0]
paperback_book_E[0].position = [1.018311616373122, 5.525574332112529, 0.1]
paperback_book_E[0].rotation = [0, 0, 0]
paperback_book_F[0].position = [0.2591291794358075, 7.016225713969879, 0.1]
paperback_book_F[0].rotation = [0, 0, 0]
bookcase_D[0].position = [1.041209447131879, 0.8384769564395511, 1.05]
bookcase_D[0].rotation = [0, 0, 0]
printed_page_C[0].position = [5.345109910652148, 0.9448843509864211, 5e-05]
printed_page_C[0].rotation = [0, 0, 0]
sign[0].position = [2.256878859814261, 7.352394434357724, 0.09]
sign[0].rotation = [0, 0, 0]
reading_chair_G[0].position = [2.970520004142453, 4.878283505637056, 0.44]
reading_chair_G[0].rotation = [0, 0, 0]
paperback_book_G[0].position = [0.19168006718814357, 3.788099909622123, 0.1]
paperback_book_G[0].rotation = [0, 0, 0]
reading_chair_H[0].position = [2.221663413697054, 2.736085619693053, 0.44]
reading_chair_H[0].rotation = [0, 0, 0]
hardcover_book_D[0].position = [0.6937916212270823, 5.699737148064731, 0.125]
hardcover_book_D[0].rotation = [0, 0, 0]
art_print[0].position = [0.3589192525194407, 5.841579854175761, 0.4]
art_print[0].rotation = [0, 0, 0]
bookcase_E[0].position = [0.529344613434074, 1.664655562641335, 1.05]
bookcase_E[0].rotation = [0, 0, 0]
paperback_book_H[0].position = [9.360811975655727, 1.8364396107719894, 0.1]
paperback_book_H[0].rotation = [0, 0, 0]
reading_chair_A[0].position = [1.4754943160816814, 4.603682601648005, 0.44]
reading_chair_A[0].rotation = [0, 0, 0]
open_hardcover_book_A[0].position = [9.378391326064165, 5.2373185107345135, 0.02]
open_hardcover_book_A[0].rotation = [0, 0, 0]
handout_sheet[0].position = [7.423385145572735, 0.4398720056584668, 5e-05]
handout_sheet[0].rotation = [0, 0, 0]
lounge_chair_A[0].position = [7.276053832442358, 0.7055034196333987, 0.425]
lounge_chair_A[0].rotation = [0, 0, 0]
reading_chair_B[0].position = [7.758569693900879, 6.784877062747685, 0.44]
reading_chair_B[0].rotation = [0, 0, 0]
engraving_print[0].position = [5.605789999684046, 4.436110277279917, 0.3]
engraving_print[0].rotation = [0, 0, 0]
highlighter_marker[0].position = [8.54763472056437, 4.465480278328469, 0.009]
highlighter_marker[0].rotation = [0, 0, 0]
art_book_A[0].position = [6.849172792042873, 0.32223093199698544, 0.0175]
art_book_A[0].rotation = [0, 0, 0]
drink_coaster[0].position = [9.521529000341841, 6.5293178337341065, 0.003]
drink_coaster[0].rotation = [0, 0, 0]
typography_poster[0].position = [3.544267079048291, 6.407790750737907, 0.35]
typography_poster[0].rotation = [0, 0, 0]
notepad_A[0].position = [6.35041402228136, 4.848801258239399, 0.006]
notepad_A[0].rotation = [0, 0, 0]
photograph_print[0].position = [4.196300834038311, 0.6993304868009387, 0.15]
photograph_print[0].rotation = [0, 0, 0]
whiteboard[0].position = [6.969858321012844, 4.976446799075365, 0.5]
whiteboard[0].rotation = [0, 0, 0]
hardcover_book_A[0].position = [1.3037353273096919, 2.776683835189204, 0.0175]
hardcover_book_A[0].rotation = [0, 0, 0]
potted_succulent_A[0].position = [6.9383156499695335, 6.474987255258019, 0.11]
potted_succulent_A[0].rotation = [0, 0, 0]
bookshelf_A[0].position = [8.118165455612994, 5.117388564434183, 1.05]
bookshelf_A[0].rotation = [0, 0, 0]
desk_lamp[0].position = [3.2874464113435433, 0.6286440958201858, 0.24]
desk_lamp[0].rotation = [0, 0, 0]
bookcase_A[0].position = [6.144325682936812, 5.853096789604033, 1.05]
bookcase_A[0].rotation = [0, 0, 0]
paperback_book_A[0].position = [1.469704254899965, 6.928227652758688, 0.1]
paperback_book_A[0].rotation = [0, 0, 0]
dining_table_A[0].position = [6.234360760691927, 2.2111402733970826, 0.375]
dining_table_A[0].rotation = [0, 0, 0]
illustration_print_A[0].position = [7.693054484009114, 3.197641465822653, 0.25]
illustration_print_A[0].rotation = [0, 0, 0]
clock[0].position = [0.536960620739444, 0.6427209569783607, 0.175]
clock[0].rotation = [0, 0, 0]
coffee_mug_A[0].position = [6.2364572537193865, 6.026991486081608, 0.05]
coffee_mug_A[0].rotation = [0, 0, 0]
paperback_book_B[0].position = [7.599679389675002, 3.7143266863233473, 0.1]
paperback_book_B[0].rotation = [0, 0, 0]
floor_lamp[0].position = [0.98989337095438, 0.17137077741377627, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
reading_chair_C[0].position = [3.817922939470227, 1.5260921567388543, 0.44]
reading_chair_C[0].rotation = [0, 0, 0]
potted_succulent_B[0].position = [2.0079400983912645, 1.1421712900097711, 0.125]
potted_succulent_B[0].rotation = [0, 0, 0]
hardcover_book_B[0].position = [4.825608789772438, 1.624248658370142, 0.125]
hardcover_book_B[0].rotation = [0, 0, 0]
bookshelf_B[0].position = [1.172704371321941, 1.9503554526767541, 1.05]
bookshelf_B[0].rotation = [0, 0, 0]
side_table[0].position = [1.8294268169756522, 1.3327789407230495, 0.26]
side_table[0].rotation = [0, 0, 0]
bookcase_B[0].position = [2.412575492789595, 4.690239581723441, 1.05]
bookcase_B[0].rotation = [0, 0, 0]
ballpoint_pen_A[0].position = [2.4712675305725296, 1.1090567153984945, 0.006]
ballpoint_pen_A[0].rotation = [0, 0, 0]
bookcase_C[0].position = [3.034348859129563, 1.3376298114520102, 1.05]
bookcase_C[0].rotation = [0, 0, 0]
pencil[0].position = [9.970343901188116, 3.484098700628767, 0.0035]
pencil[0].rotation = [0, 0, 0]
dining_table_B[0].position = [6.626980028886901, 6.813994841345772, 0.375]
dining_table_B[0].rotation = [0, 0, 0]
illustration_print_B[0].position = [5.129251409478169, 4.3491949862406205, 0.25]
illustration_print_B[0].rotation = [0, 0, 0]
pen_holder_cup[0].position = [1.9989953051720355, 3.480495726522408, 0.055]
pen_holder_cup[0].rotation = [0, 0, 0]
paperback_book_C[0].position = [9.045540545360373, 2.24583214342117, 0.1]
paperback_book_C[0].rotation = [0, 0, 0]
hardcover_book_C[0].position = [2.0885590149749076, 7.481583812094707, 0.125]
hardcover_book_C[0].rotation = [0, 0, 0]
photocopier[0].position = [0.19129166888454452, 7.125677068227212, 0.55]
photocopier[0].rotation = [0, 0, 0]
ballpoint_pen_B[0].position = [4.395443778035341, 0.1898564927327337, 0.006]
ballpoint_pen_B[0].rotation = [0, 0, 0]
notepad_B[0].position = [2.6313933704514314, 6.267121681180071, 0.006]
notepad_B[0].rotation = [0, 0, 0]
reading_chair_D[0].position = [6.316507050249802, 0.41231273602971574, 0.44]
reading_chair_D[0].rotation = [0, 0, 0]
art_book_B[0].position = [2.0459829919365333, 2.0185633243256866, 0.02]
art_book_B[0].rotation = [0, 0, 0]
printed_page_A[0].position = [0.05286608239730817, 5.708391542121162, 5e-05]
printed_page_A[0].rotation = [0, 0, 0]
paperback_book_D[0].position = [0.6100805986786695, 3.7235786606387995, 0.1]
paperback_book_D[0].rotation = [0, 0, 0]
reading_chair_E[0].position = [2.0105128609896115, 5.8764620855337375, 0.44]
reading_chair_E[0].rotation = [0, 0, 0]
hardcover_library_book[0].position = [9.169786460324922, 2.2654352845404793, 0.125]
hardcover_library_book[0].rotation = [0, 0, 0]
open_hardcover_book_B[0].position = [2.0685031780156846, 6.0237137165478005, 0.02]
open_hardcover_book_B[0].rotation = [0, 0, 0]
mirror[0].position = [6.895781865502339, 2.3860243832901866, 0.45]
mirror[0].rotation = [0, 0, 0]
printed_page_B[0].position = [5.549942331918723, 1.4840434406058973, 5e-05]
printed_page_B[0].rotation = [0, 0, 0]
coffee_mug_B[0].position = [7.831466348612778, 1.3553606344647826, 0.05]
coffee_mug_B[0].rotation = [0, 0, 0]
base_cabinet[0].position = [9.785811496415125, 2.088486085226086, 0.425]
base_cabinet[0].rotation = [0, 0, 0]
lounge_chair_B[0].position = [0.3540170329711567, 1.3809303873314258, 0.425]
lounge_chair_B[0].rotation = [0, 0, 0]
reading_chair_F[0].position = [8.141124950771722, 4.184759929116367, 0.44]
reading_chair_F[0].rotation = [0, 0, 0]
paperback_book_E[0].position = [1.018311616373122, 5.525574332112529, 0.1]
paperback_book_E[0].rotation = [0, 0, 0]
paperback_book_F[0].position = [0.2591291794358075, 7.016225713969879, 0.1]
paperback_book_F[0].rotation = [0, 0, 0]
bookcase_D[0].position = [1.041209447131879, 0.8384769564395511, 1.05]
bookcase_D[0].rotation = [0, 0, 0]
printed_page_C[0].position = [5.345109910652148, 0.9448843509864211, 5e-05]
printed_page_C[0].rotation = [0, 0, 0]
sign[0].position = [2.256878859814261, 7.352394434357724, 0.09]
sign[0].rotation = [0, 0, 0]
reading_chair_G[0].position = [2.970520004142453, 4.878283505637056, 0.44]
reading_chair_G[0].rotation = [0, 0, 0]
paperback_book_G[0].position = [0.19168006718814357, 3.788099909622123, 0.1]
paperback_book_G[0].rotation = [0, 0, 0]
reading_chair_H[0].position = [2.221663413697054, 2.736085619693053, 0.44]
reading_chair_H[0].rotation = [0, 0, 0]
hardcover_book_D[0].position = [0.6937916212270823, 5.699737148064731, 0.125]
hardcover_book_D[0].rotation = [0, 0, 0]
art_print[0].position = [0.3589192525194407, 5.841579854175761, 0.4]
art_print[0].rotation = [0, 0, 0]
bookcase_E[0].position = [0.529344613434074, 1.664655562641335, 1.05]
bookcase_E[0].rotation = [0, 0, 0]
paperback_book_H[0].position = [9.360811975655727, 1.8364396107719894, 0.1]
paperback_book_H[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the supplied boundary coordinates: x=0..10, y=0..7.5.
# The asset IDs correspond to list order:
# o0004 = reading_chair_B, o0042 = reading_chair_D,
# o0060 = reading_chair_G, o0046 = reading_chair_E,
# o0032 = bookcase_C.
#
# Two study tables occupy the middle of the room. Shelving stays on the
# perimeter, leaving the north and south ends available for circulation.

def place_fixed(asset, xyz, yaw=0, facing=None):
    instance = asset[0]
    instance.position = list(xyz)
    instance.rotation = [0, 0, radians(yaw)]
    # A fixed-coordinate constraint also preserves clearance from neighbors.
    solver.distance_constraint(
        instance, AssetInstance(position=list(xyz)), 0, 0, weight=10
    )
    if facing is None:
        solver.align_with(
            instance,
            AssetInstance(position=list(xyz), rotation=[0, 0, radians(yaw)]),
            angle=0,
        )
    else:
        solver.point_towards(instance, facing)


# Perimeter storage: the shallow dimension is perpendicular to each wall.
storage_layout = [
    (bookshelf_A, 0.160, 1.00, 0, 3),
    (bookshelf_B, 0.160, 2.40, 0, 3),
    (bookcase_A, 0.175, 3.80, 0, 3),
    (bookcase_B, 0.175, 5.20, 0, 3),
    (bookcase_C, 9.825, 3.50, 180, 1),
    (bookcase_D, 9.825, 1.00, 180, 1),
    (bookcase_E, 9.825, 5.40, 180, 1),
]
for item, px, py, yaw, wall_index in storage_layout:
    place_fixed(item, [px, py, item.size[2] / 2], yaw)
    solver.against_wall(item[0], walls[wall_index])

place_fixed(dining_table_A, [3.0, 3.5, 0.375])
place_fixed(dining_table_B, [7.0, 3.5, 0.375])

# D--B--G form a straight, evenly spaced row: B is strictly between D and G.
# All three face the left study table.
chair_layout = [
    (reading_chair_D, 2.0, 2.5, 0),
    (reading_chair_B, 2.0, 3.5, 0),
    (reading_chair_G, 2.0, 4.5, 0),
    (reading_chair_A, 4.0, 2.8, 180),
    (reading_chair_C, 4.0, 4.2, 180),
    (reading_chair_F, 6.0, 2.8, 0),
    (reading_chair_H, 6.0, 4.2, 0),
]
for item, px, py, yaw in chair_layout:
    place_fixed(item, [px, py, 0.44], yaw)

# E faces the requested bookcase, rather than the adjacent study table.
place_fixed(
    reading_chair_E, [8.0, 3.5, 0.44], 0, facing=bookcase_C[0]
)

# These exact center distances reinforce the requested between relationship.
solver.distance_constraint(reading_chair_B[0], reading_chair_D[0], 1.0, 1.0, weight=10)
solver.distance_constraint(reading_chair_B[0], reading_chair_G[0], 1.0, 1.0, weight=10)

# A separate lounge group along the north side, clear of the study chairs.
place_fixed(lounge_chair_A, [2.0, 6.4, 0.425], -90)
place_fixed(lounge_chair_B, [3.9, 6.4, 0.425], -90)
place_fixed(side_table, [2.95, 6.4, 0.26])
place_fixed(floor_lamp, [4.7, 6.5, 0.825], -90)

# Copying/service corner, with clear space in front of both machines.
place_fixed(base_cabinet, [9.75, 6.7, 0.425], 180)
solver.against_wall(base_cabinet[0], walls[1])
place_fixed(photocopier, [8.4, 6.95, 0.55], -90)

# Wall-mounted items are elevated rather than left on the floor.
# Their local x dimension is thickness; rotation 90 faces into the room
# from the south wall.
wall_display_layout = [
    (engraving_print, 1.0, 0.015, 1.65, 90, 0),
    (typography_poster, 2.0, 0.010, 1.70, 90, 0),
    (photograph_print, 3.0, 0.015, 1.65, 90, 0),
    (illustration_print_A, 4.0, 0.015, 1.65, 90, 0),
    (whiteboard, 7.0, 0.025, 1.65, 90, 0),
    (illustration_print_B, 9.0, 0.015, 1.65, 90, 0),
    (clock, 6.0, 7.480, 2.45, -90, 2),
    (sign, 5.0, 7.495, 2.15, -90, 2),
    (art_print, 7.0, 7.485, 1.85, -90, 2),
    (mirror, 9.985, 2.10, 1.55, 180, 1),
]
for item, px, py, pz, yaw, wall_index in wall_display_layout:
    place_fixed(item, [px, py, pz], yaw)
    solver.against_wall(item[0], walls[wall_index])


def place_on_surface(asset, support, px, py, yaw=0):
    # Positions are bounding-box centers. All listed supports are unrotated
    # or rotated by 180 degrees, so their top height is straightforward.
    pz = (
        support[0].position[2]
        + support.size[2] / 2
        + asset.size[2] / 2
    )
    instance = asset[0]
    instance.position = [px, py, pz]
    instance.rotation = [0, 0, radians(yaw)]
    solver.on_top_of(instance, support[0])
    solver.distance_constraint(
        instance,
        AssetInstance(position=[px, py, pz]),
        0, 0, weight=10,
    )
    solver.align_with(
        instance,
        AssetInstance(position=[px, py, pz], rotation=[0, 0, radians(yaw)]),
    )


# Study-table contents use separate patches of the tabletop. Pens and
# markers sit beside the paper, not through books or other objects.
tabletop_layout = [
    (open_hardcover_book_A, dining_table_A, 2.78, 2.65, 0),
    (handout_sheet, dining_table_A, 3.23, 2.65, 0),
    (highlighter_marker, dining_table_A, 3.23, 2.84, 0),
    (art_book_A, dining_table_A, 2.78, 3.30, 0),
    (notepad_A, dining_table_A, 3.23, 3.25, 0),
    (ballpoint_pen_A, dining_table_A, 3.23, 3.40, 0),
    (hardcover_book_A, dining_table_A, 2.78, 3.85, 0),
    (potted_succulent_A, dining_table_A, 3.23, 3.85, 0),
    (printed_page_A, dining_table_A, 2.78, 4.35, 0),
    (pencil, dining_table_A, 3.23, 4.10, 0),
    (desk_lamp, dining_table_A, 3.23, 4.47, 0),

    (open_hardcover_book_B, dining_table_B, 6.78, 2.65, 0),
    (printed_page_B, dining_table_B, 7.23, 2.65, 0),
    (ballpoint_pen_B, dining_table_B, 7.23, 2.85, 0),
    (art_book_B, dining_table_B, 6.78, 3.30, 0),
    (notepad_B, dining_table_B, 7.23, 3.25, 0),
    (pen_holder_cup, dining_table_B, 7.23, 3.55, 0),
    (printed_page_C, dining_table_B, 6.78, 3.90, 0),
    (coffee_mug_B, dining_table_B, 7.23, 3.95, 0),
]
for item, support, px, py, yaw in tabletop_layout:
    place_on_surface(item, support, px, py, yaw)

# The mug rests on its coaster; the plant occupies another part of the
# lounge side table.
place_on_surface(drink_coaster, side_table, 2.80, 6.25)
place_on_surface(coffee_mug_A, drink_coaster, 2.80, 6.25, 90)
place_on_surface(potted_succulent_B, side_table, 3.10, 6.55)

# With no shelf-level geometry supplied, use the actual top surfaces of
# the storage units as small book displays, instead of embedding books
# inside their bounding boxes. Each pair has ample separation.
book_display_layout = [
    (paperback_book_A, bookshelf_A, 0.16, 0.78, 0),
    (paperback_book_B, bookshelf_A, 0.16, 1.22, 0),
    (paperback_book_C, bookshelf_B, 0.16, 2.18, 0),
    (hardcover_book_B, bookshelf_B, 0.16, 2.62, 0),
    (paperback_book_D, bookcase_A, 0.175, 3.58, 0),
    (hardcover_book_C, bookcase_A, 0.175, 4.02, 0),
    (paperback_book_E, bookcase_B, 0.175, 4.98, 0),
    (hardcover_library_book, bookcase_B, 0.175, 5.42, 0),
    (paperback_book_F, bookcase_C, 9.825, 3.25, 180),
    (paperback_book_G, bookcase_C, 9.825, 3.75, 180),
    (paperback_book_H, bookcase_D, 9.825, 0.80, 180),
    (hardcover_book_D, bookcase_E, 9.825, 5.40, 180),
]
for item, support, px, py, yaw in book_display_layout:
    place_on_surface(item, support, px, py, yaw)

solver.constraints = []
bookcase_D[0].position = [9.824888229370117, 1.0, 1.0499999523162842]
bookcase_D[0].rotation = [0, 0, -3.1414106125849175]
bookcase_D[0].optimize = 2
bookcase_A[0].position = [0.17509546875953674, 3.799999952316284, 1.0499999523162842]
bookcase_A[0].rotation = [0, 0, -0.00010823368831744017]
bookcase_A[0].optimize = 2
potted_succulent_A[0].position = [3.2300000190734863, 3.8499999046325684, 0.8600000143051147]
potted_succulent_A[0].rotation = [0, 0, 0.01256637125682779]
potted_succulent_A[0].optimize = 2
paperback_book_H[0].position = [9.824999809265137, 0.800000011920929, 2.1999998092651367]
paperback_book_H[0].rotation = [0, 0, -3.1290262823329655]
paperback_book_H[0].optimize = 2
coffee_mug_A[0].position = [2.799999952316284, 6.25, 0.5799999833106995]
coffee_mug_A[0].rotation = [0, 0, 1.5833626980517244]
coffee_mug_A[0].optimize = 2
hardcover_book_A[0].position = [2.7799999713897705, 3.8499999046325684, 0.7699999809265137]
hardcover_book_A[0].rotation = [0, 0, 0.01256637125682779]
hardcover_book_A[0].optimize = 2
bookshelf_A[0].position = [0.15988492965698242, 1.0, 1.0499999523162842]
bookshelf_A[0].rotation = [0, 0, -0.00010831850679173782]
bookshelf_A[0].optimize = 2
clock[0].position = [6.0, 7.48019552230835, 0.17499999701976776]
clock[0].rotation = [0, 0, -1.570856986906827]
clock[0].optimize = 2
hardcover_library_book[0].position = [0.17499999701976776, 5.420000076293945, 2.2249999046325684]
hardcover_library_book[0].rotation = [0, 0, 0.01256637125682779]
hardcover_library_book[0].optimize = 2
hardcover_book_C[0].position = [0.17499999701976776, 4.019999980926514, 2.2249999046325684]
hardcover_book_C[0].rotation = [0, 0, 0.01256637125682779]
hardcover_book_C[0].optimize = 2
base_cabinet[0].position = [9.749920845031738, 6.699999809265137, 0.42500001192092896]
base_cabinet[0].rotation = [0, 0, 3.1415309668445546]
base_cabinet[0].optimize = 2
bookcase_C[0].position = [9.824790000915527, 3.5, 1.0499999523162842]
bookcase_C[0].rotation = [0, 0, 3.1413794632294585]
bookcase_C[0].optimize = 2
sign[0].position = [5.0, 7.495168209075928, 0.09000000357627869]
sign[0].rotation = [0, 0, -1.5708569619709294]
sign[0].optimize = 2
bookcase_E[0].position = [9.824888229370117, 5.400000095367432, 1.0499999523162842]
bookcase_E[0].rotation = [0, 0, -3.1414106125849175]
bookcase_E[0].optimize = 2
potted_succulent_B[0].position = [3.0999999046325684, 6.550000190734863, 0.6449999809265137]
potted_succulent_B[0].rotation = [0, 0, 0.01256637125682779]
potted_succulent_B[0].optimize = 2
reading_chair_A[0].position = [4.0, 2.799999952316284, 0.4399999976158142]
reading_chair_A[0].rotation = [0, 0, -3.1321678761290697]
reading_chair_A[0].optimize = 2
highlighter_marker[0].position = [3.2300000190734863, 2.8399999141693115, 0.7599999904632568]
highlighter_marker[0].rotation = [0, 0, 0.01256637125682779]
highlighter_marker[0].optimize = 2
hardcover_book_D[0].position = [9.824999809265137, 5.400000095367432, 2.2249999046325684]
hardcover_book_D[0].rotation = [0, 0, -3.1290262823329655]
hardcover_book_D[0].optimize = 2
illustration_print_A[0].position = [4.0, 0.01497295219451189, 0.25]
illustration_print_A[0].rotation = [0, 0, 1.5707356782385613]
illustration_print_A[0].optimize = 2
open_hardcover_book_B[0].position = [6.78000020980835, 2.6500000953674316, 0.7699999809265137]
open_hardcover_book_B[0].rotation = [0, 0, 0.01256637125682779]
open_hardcover_book_B[0].optimize = 2
paperback_book_B[0].position = [0.1599999964237213, 1.2200000286102295, 2.1999998092651367]
paperback_book_B[0].rotation = [0, 0, 0.01256637125682779]
paperback_book_B[0].optimize = 2
art_book_B[0].position = [6.78000020980835, 3.299999952316284, 0.7699999809265137]
art_book_B[0].rotation = [0, 0, 0.01256637125682779]
art_book_B[0].optimize = 2
ballpoint_pen_A[0].position = [3.2300000190734863, 3.4000000953674316, 0.7549999952316284]
ballpoint_pen_A[0].rotation = [0, 0, 0.01256637125682779]
ballpoint_pen_A[0].optimize = 2
lounge_chair_B[0].position = [3.9000000953674316, 6.400000095367432, 0.42500001192092896]
lounge_chair_B[0].rotation = [0, 0, -1.5613715493341729]
lounge_chair_B[0].optimize = 2
typography_poster[0].position = [2.0, 0.010191116482019424, 0.3499999940395355]
typography_poster[0].rotation = [0, 0, 1.5707356768359193]
typography_poster[0].optimize = 2
handout_sheet[0].position = [3.2300000190734863, 2.6500000953674316, 0.75]
handout_sheet[0].rotation = [0, 0, 0.01256637125682779]
handout_sheet[0].optimize = 2
paperback_book_G[0].position = [9.824999809265137, 3.75, 2.1999998092651367]
paperback_book_G[0].rotation = [0, 0, -3.1290262823329655]
paperback_book_G[0].optimize = 2
notepad_A[0].position = [3.2300000190734863, 3.25, 0.7549999952316284]
notepad_A[0].rotation = [0, 0, 0.01256637125682779]
notepad_A[0].optimize = 2
hardcover_book_B[0].position = [0.1599999964237213, 2.619999885559082, 2.2249999046325684]
hardcover_book_B[0].rotation = [0, 0, 0.01256637125682779]
hardcover_book_B[0].optimize = 2
reading_chair_G[0].position = [2.0, 4.5, 0.4399999976158142]
reading_chair_G[0].rotation = [0, 0, 0.01256637125682779]
reading_chair_G[0].optimize = 2
whiteboard[0].position = [7.0, 0.024875599890947342, 0.5]
whiteboard[0].rotation = [0, 0, 1.5707354277567396]
whiteboard[0].optimize = 2
side_table[0].position = [2.950000047683716, 6.400000095367432, 0.25999999046325684]
side_table[0].rotation = [0, 0, 0.0157079639172164]
side_table[0].optimize = 2
pen_holder_cup[0].position = [7.230000019073486, 3.549999952316284, 0.8050000071525574]
pen_holder_cup[0].rotation = [0, 0, 0.01256637125682779]
pen_holder_cup[0].optimize = 2
pencil[0].position = [3.2300000190734863, 4.099999904632568, 0.7549999952316284]
pencil[0].rotation = [0, 0, 0.01256637125682779]
pencil[0].optimize = 2
paperback_book_C[0].position = [0.1599999964237213, 2.180000066757202, 2.1999998092651367]
paperback_book_C[0].rotation = [0, 0, 0.01256637125682779]
paperback_book_C[0].optimize = 2
printed_page_C[0].position = [6.78000020980835, 3.9000000953674316, 0.75]
printed_page_C[0].rotation = [0, 0, 0.01256637125682779]
printed_page_C[0].optimize = 2
dining_table_B[0].position = [7.0, 3.5, 0.375]
dining_table_B[0].rotation = [0, 0, 0.03455751882667646]
dining_table_B[0].optimize = 2
paperback_book_A[0].position = [0.1599999964237213, 0.7799999713897705, 2.1999998092651367]
paperback_book_A[0].rotation = [0, 0, 0.01256637125682779]
paperback_book_A[0].optimize = 2
bookshelf_B[0].position = [0.15988492965698242, 2.4000000953674316, 1.0499999523162842]
bookshelf_B[0].rotation = [0, 0, -0.00010831850679173782]
bookshelf_B[0].optimize = 2
paperback_book_F[0].position = [9.824999809265137, 3.25, 2.1999998092651367]
paperback_book_F[0].rotation = [0, 0, -3.1290262823329655]
paperback_book_F[0].optimize = 2
printed_page_A[0].position = [2.7799999713897705, 4.349999904632568, 0.75]
printed_page_A[0].rotation = [0, 0, 0.01256637125682779]
printed_page_A[0].optimize = 2
notepad_B[0].position = [7.230000019073486, 3.25, 0.7549999952316284]
notepad_B[0].rotation = [0, 0, 0.01256637125682779]
notepad_B[0].optimize = 2
open_hardcover_book_A[0].position = [2.7799999713897705, 2.6500000953674316, 0.7699999809265137]
open_hardcover_book_A[0].rotation = [0, 0, 0.01256637125682779]
open_hardcover_book_A[0].optimize = 2
photocopier[0].position = [8.399999618530273, 6.949999809265137, 0.550000011920929]
photocopier[0].rotation = [0, 0, -1.5613715493341729]
photocopier[0].optimize = 2
mirror[0].position = [9.98521614074707, 2.0999999046325684, 0.44999998807907104]
mirror[0].rotation = [0, 0, 3.141531965420102]
mirror[0].optimize = 2
reading_chair_F[0].position = [6.0, 2.799999952316284, 0.4399999976158142]
reading_chair_F[0].rotation = [0, 0, 0.00942477746072377]
reading_chair_F[0].optimize = 2
art_print[0].position = [7.0, 7.4848737716674805, 0.4000000059604645]
art_print[0].rotation = [0, 0, -1.5708569970121073]
art_print[0].optimize = 2
floor_lamp[0].position = [4.699999809265137, 6.5, 0.824999988079071]
floor_lamp[0].rotation = [0, 0, -1.5613715493341729]
floor_lamp[0].optimize = 2
engraving_print[0].position = [1.0, 0.014973276294767857, 0.30000001192092896]
engraving_print[0].rotation = [0, 0, 1.5707356739315175]
engraving_print[0].optimize = 2
illustration_print_B[0].position = [9.0, 0.01497295219451189, 0.25]
illustration_print_B[0].rotation = [0, 0, 1.5707356782385613]
illustration_print_B[0].optimize = 2
drink_coaster[0].position = [2.799999952316284, 6.25, 0.5249999761581421]
drink_coaster[0].rotation = [0, 0, 0.0157079639172164]
drink_coaster[0].optimize = 2
lounge_chair_A[0].position = [2.0, 6.400000095367432, 0.42500001192092896]
lounge_chair_A[0].rotation = [0, 0, -1.5613715493341729]
lounge_chair_A[0].optimize = 2
desk_lamp[0].position = [3.2300000190734863, 4.46999979019165, 0.9900000095367432]
desk_lamp[0].rotation = [0, 0, 0.01256637125682779]
desk_lamp[0].optimize = 2
reading_chair_H[0].position = [6.0, 4.199999809265137, 0.4399999976158142]
reading_chair_H[0].rotation = [0, 0, 0.00942477746072377]
reading_chair_H[0].optimize = 2
reading_chair_E[0].position = [8.0, 3.5, 0.4399999976158142]
reading_chair_E[0].rotation = [0, 0, 0.00942477746072377]
reading_chair_E[0].optimize = 2
art_book_A[0].position = [2.7799999713897705, 3.299999952316284, 0.7699999809265137]
art_book_A[0].rotation = [0, 0, 0.01256637125682779]
art_book_A[0].optimize = 2
coffee_mug_B[0].position = [7.230000019073486, 3.950000047683716, 0.800000011920929]
coffee_mug_B[0].rotation = [0, 0, 0.01256637125682779]
coffee_mug_B[0].optimize = 2
dining_table_A[0].position = [3.0, 3.5, 0.375]
dining_table_A[0].rotation = [0, 0, 0.043982298440307294]
dining_table_A[0].optimize = 2
bookcase_B[0].position = [0.17509546875953674, 5.199999809265137, 1.0499999523162842]
bookcase_B[0].rotation = [0, 0, -0.00010823368831744017]
bookcase_B[0].optimize = 2
reading_chair_C[0].position = [4.0, 4.199999809265137, 0.4399999976158142]
reading_chair_C[0].rotation = [0, 0, -3.1321678761290697]
reading_chair_C[0].optimize = 2
ballpoint_pen_B[0].position = [7.230000019073486, 2.8499999046325684, 0.7549999952316284]
ballpoint_pen_B[0].rotation = [0, 0, 0.01256637125682779]
ballpoint_pen_B[0].optimize = 2
paperback_book_E[0].position = [0.17499999701976776, 4.980000019073486, 2.1999998092651367]
paperback_book_E[0].rotation = [0, 0, 0.01256637125682779]
paperback_book_E[0].optimize = 2
photograph_print[0].position = [3.0, 0.01497295219451189, 0.15000000596046448]
photograph_print[0].rotation = [0, 0, 1.5707356782385613]
photograph_print[0].optimize = 2
printed_page_B[0].position = [7.230000019073486, 2.6500000953674316, 0.75]
printed_page_B[0].rotation = [0, 0, 0.01256637125682779]
printed_page_B[0].optimize = 2
reading_chair_D[0].position = [2.0, 2.5, 0.4399999976158142]
reading_chair_D[0].rotation = [0, 0, 0.01256637125682779]
reading_chair_D[0].optimize = 2
paperback_book_D[0].position = [0.17499999701976776, 3.5799999237060547, 2.1999998092651367]
paperback_book_D[0].rotation = [0, 0, 0.01256637125682779]
paperback_book_D[0].optimize = 2
reading_chair_B[0].position = [2.0, 3.5, 0.4399999976158142]
reading_chair_B[0].rotation = [0, 0, 0.0157079639172164]
reading_chair_B[0].optimize = 2

