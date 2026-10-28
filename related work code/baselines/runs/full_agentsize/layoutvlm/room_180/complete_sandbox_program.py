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
reading_chair_A = Assets(description="reading chair", size=[0.82, 0.75, 0.92], placements=[AssetInstance() for _ in range(1)])
open_hardcover_book_A = Assets(description="open hardcover book", size=[0.28, 0.42, 0.04], placements=[AssetInstance() for _ in range(1)])
handout_sheet = Assets(description="handout sheet", size=[0.30, 0.21, 0.00], placements=[AssetInstance() for _ in range(1)])
lounge_chair_A = Assets(description="lounge chair", size=[0.90, 0.82, 0.88], placements=[AssetInstance() for _ in range(1)])
reading_chair_B = Assets(description="reading chair", size=[0.82, 0.75, 0.92], placements=[AssetInstance() for _ in range(1)])
engraving_print = Assets(description="engraving print", size=[0.03, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
highlighter_marker = Assets(description="highlighter marker", size=[0.02, 0.14, 0.02], placements=[AssetInstance() for _ in range(1)])
art_book_A = Assets(description="art book", size=[0.32, 0.25, 0.03], placements=[AssetInstance() for _ in range(1)])
drink_coaster = Assets(description="drink coaster", size=[0.10, 0.10, 0.01], placements=[AssetInstance() for _ in range(1)])
typography_poster = Assets(description="typography poster", size=[0.02, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
notepad_A = Assets(description="notepad", size=[0.21, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
photograph_print = Assets(description="photograph print", size=[0.03, 0.40, 0.30], placements=[AssetInstance() for _ in range(1)])
whiteboard = Assets(description="whiteboard", size=[0.05, 1.80, 1.20], placements=[AssetInstance() for _ in range(1)])
hardcover_book_A = Assets(description="hardcover book", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
potted_succulent_A = Assets(description="potted succulent", size=[0.16, 0.16, 0.22], placements=[AssetInstance() for _ in range(1)])
bookshelf_A = Assets(description="bookshelf", size=[0.32, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
desk_lamp = Assets(description="desk lamp", size=[0.35, 0.28, 0.48], placements=[AssetInstance() for _ in range(1)])
bookcase_A = Assets(description="bookcase", size=[0.35, 0.90, 2.20], placements=[AssetInstance() for _ in range(1)])
paperback_book_A = Assets(description="paperback book", size=[0.20, 0.13, 0.03], placements=[AssetInstance() for _ in range(1)])
dining_table_A = Assets(description="dining table", size=[0.90, 1.80, 0.75], placements=[AssetInstance() for _ in range(1)])
illustration_print_A = Assets(description="illustration print", size=[0.03, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
clock = Assets(description="clock", size=[0.05, 0.35, 0.35], placements=[AssetInstance() for _ in range(1)])
coffee_mug_A = Assets(description="coffee mug", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
paperback_book_B = Assets(description="paperback book", size=[0.20, 0.13, 0.03], placements=[AssetInstance() for _ in range(1)])
floor_lamp = Assets(description="floor lamp", size=[0.38, 0.38, 1.65], placements=[AssetInstance() for _ in range(1)])
reading_chair_C = Assets(description="reading chair", size=[0.82, 0.75, 0.92], placements=[AssetInstance() for _ in range(1)])
potted_succulent_B = Assets(description="potted succulent", size=[0.14, 0.14, 0.20], placements=[AssetInstance() for _ in range(1)])
hardcover_book_B = Assets(description="hardcover book", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
bookshelf_B = Assets(description="bookshelf", size=[0.32, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
side_table = Assets(description="side table", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
bookcase_B = Assets(description="bookcase", size=[0.35, 0.90, 2.20], placements=[AssetInstance() for _ in range(1)])
ballpoint_pen_A = Assets(description="ballpoint pen", size=[0.01, 0.14, 0.01], placements=[AssetInstance() for _ in range(1)])
bookcase_C = Assets(description="bookcase", size=[0.35, 0.90, 2.20], placements=[AssetInstance() for _ in range(1)])
pencil = Assets(description="pencil", size=[0.01, 0.18, 0.01], placements=[AssetInstance() for _ in range(1)])
dining_table_B = Assets(description="dining table", size=[0.90, 1.80, 0.75], placements=[AssetInstance() for _ in range(1)])
illustration_print_B = Assets(description="illustration print", size=[0.03, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
pen_holder_cup = Assets(description="pen holder cup", size=[0.10, 0.10, 0.12], placements=[AssetInstance() for _ in range(1)])
paperback_book_C = Assets(description="paperback book", size=[0.20, 0.13, 0.03], placements=[AssetInstance() for _ in range(1)])
hardcover_book_C = Assets(description="hardcover book", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
photocopier = Assets(description="photocopier", size=[0.70, 0.65, 1.10], placements=[AssetInstance() for _ in range(1)])
ballpoint_pen_B = Assets(description="ballpoint pen", size=[0.01, 0.14, 0.01], placements=[AssetInstance() for _ in range(1)])
notepad_B = Assets(description="notepad", size=[0.21, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
reading_chair_D = Assets(description="reading chair", size=[0.82, 0.75, 0.92], placements=[AssetInstance() for _ in range(1)])
art_book_B = Assets(description="art book", size=[0.32, 0.25, 0.03], placements=[AssetInstance() for _ in range(1)])
printed_page_A = Assets(description="printed page", size=[0.30, 0.21, 0.00], placements=[AssetInstance() for _ in range(1)])
paperback_book_D = Assets(description="paperback book", size=[0.20, 0.13, 0.03], placements=[AssetInstance() for _ in range(1)])
reading_chair_E = Assets(description="reading chair", size=[0.82, 0.75, 0.92], placements=[AssetInstance() for _ in range(1)])
hardcover_library_book = Assets(description="hardcover library book", size=[0.25, 0.18, 0.04], placements=[AssetInstance() for _ in range(1)])
open_hardcover_book_B = Assets(description="open hardcover book", size=[0.28, 0.42, 0.04], placements=[AssetInstance() for _ in range(1)])
mirror = Assets(description="mirror", size=[0.04, 0.80, 1.20], placements=[AssetInstance() for _ in range(1)])
printed_page_B = Assets(description="printed page", size=[0.30, 0.21, 0.00], placements=[AssetInstance() for _ in range(1)])
coffee_mug_B = Assets(description="coffee mug", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
base_cabinet = Assets(description="base cabinet", size=[0.55, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
lounge_chair_B = Assets(description="lounge chair", size=[0.90, 0.82, 0.88], placements=[AssetInstance() for _ in range(1)])
reading_chair_F = Assets(description="reading chair", size=[0.82, 0.75, 0.92], placements=[AssetInstance() for _ in range(1)])
paperback_book_E = Assets(description="paperback book", size=[0.20, 0.13, 0.03], placements=[AssetInstance() for _ in range(1)])
paperback_book_F = Assets(description="paperback book", size=[0.20, 0.13, 0.03], placements=[AssetInstance() for _ in range(1)])
bookcase_D = Assets(description="bookcase", size=[0.35, 0.90, 2.20], placements=[AssetInstance() for _ in range(1)])
printed_page_C = Assets(description="printed page", size=[0.30, 0.21, 0.00], placements=[AssetInstance() for _ in range(1)])
sign = Assets(description="sign", size=[0.03, 0.60, 0.25], placements=[AssetInstance() for _ in range(1)])
reading_chair_G = Assets(description="reading chair", size=[0.82, 0.75, 0.92], placements=[AssetInstance() for _ in range(1)])
paperback_book_G = Assets(description="paperback book", size=[0.20, 0.13, 0.03], placements=[AssetInstance() for _ in range(1)])
reading_chair_H = Assets(description="reading chair", size=[0.82, 0.75, 0.92], placements=[AssetInstance() for _ in range(1)])
hardcover_book_D = Assets(description="hardcover book", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
art_print = Assets(description="art print", size=[0.03, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
bookcase_E = Assets(description="bookcase", size=[0.35, 0.90, 2.20], placements=[AssetInstance() for _ in range(1)])
paperback_book_H = Assets(description="paperback book", size=[0.20, 0.13, 0.03], placements=[AssetInstance() for _ in range(1)])

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

reading_chair_A[0].position = [6.876241289841589, 2.286531448067424, 0.46]
reading_chair_A[0].rotation = [0, 0, 0]
open_hardcover_book_A[0].position = [2.4598162486664976, 2.5583458866489166, 0.02]
open_hardcover_book_A[0].rotation = [0, 0, 0]
handout_sheet[0].position = [1.6035075191002346, 0.7883557998752846, 0.0005]
handout_sheet[0].rotation = [0, 0, 0]
lounge_chair_A[0].position = [6.138081099631593, 6.117787106387567, 0.44]
lounge_chair_A[0].rotation = [0, 0, 0]
reading_chair_B[0].position = [4.067876076777486, 1.6268157704149109, 0.46]
reading_chair_B[0].rotation = [0, 0, 0]
engraving_print[0].position = [8.52846075142169, 7.052678887429388, 0.35]
engraving_print[0].rotation = [0, 0, 0]
highlighter_marker[0].position = [4.961033986198107, 1.2643186944422435, 0.01]
highlighter_marker[0].rotation = [0, 0, 0]
art_book_A[0].position = [3.7495865710895426, 2.9529195532534884, 0.015]
art_book_A[0].rotation = [0, 0, 0]
drink_coaster[0].position = [9.214174945389798, 3.4992958062118187, 0.004]
drink_coaster[0].rotation = [0, 0, 0]
typography_poster[0].position = [9.589744261447061, 2.2028704112528925, 0.45]
typography_poster[0].rotation = [0, 0, 0]
notepad_A[0].position = [0.5011096143909233, 6.867475053943234, 0.0075]
notepad_A[0].rotation = [0, 0, 0]
photograph_print[0].position = [5.367888146718974, 2.5427747594695354, 0.15]
photograph_print[0].rotation = [0, 0, 0]
whiteboard[0].position = [3.9558375501674705, 1.8902160381061728, 0.6]
whiteboard[0].rotation = [0, 0, 0]
hardcover_book_A[0].position = [1.5311627881304746, 6.052320574335496, 0.0175]
hardcover_book_A[0].rotation = [0, 0, 0]
potted_succulent_A[0].position = [2.7376971766520586, 0.1871597812481801, 0.11]
potted_succulent_A[0].rotation = [0, 0, 0]
bookshelf_A[0].position = [4.4661703664621255, 1.5022686904842721, 0.9]
bookshelf_A[0].rotation = [0, 0, 0]
desk_lamp[0].position = [6.897059198575749, 2.0194750762617057, 0.24]
desk_lamp[0].rotation = [0, 0, 0]
bookcase_A[0].position = [3.641039609994902, 1.2744906955455868, 1.1]
bookcase_A[0].rotation = [0, 0, 0]
paperback_book_A[0].position = [1.5981137435969694, 4.56375684976902, 0.0125]
paperback_book_A[0].rotation = [0, 0, 0]
dining_table_A[0].position = [7.449960965255185, 3.0789431679131516, 0.375]
dining_table_A[0].rotation = [0, 0, 0]
illustration_print_A[0].position = [0.0743579104293457, 7.300894559629232, 0.35]
illustration_print_A[0].rotation = [0, 0, 0]
clock[0].position = [2.971581802621267, 1.5539540393003801, 0.175]
clock[0].rotation = [0, 0, 0]
coffee_mug_A[0].position = [1.1331234766209797, 3.325918336770239, 0.05]
coffee_mug_A[0].rotation = [0, 0, 0]
paperback_book_B[0].position = [4.4610939985510365, 6.266131511659219, 0.0125]
paperback_book_B[0].rotation = [0, 0, 0]
floor_lamp[0].position = [4.994572643475786, 2.3041046330867503, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
reading_chair_C[0].position = [4.299373299268874, 5.643105928716576, 0.46]
reading_chair_C[0].rotation = [0, 0, 0]
potted_succulent_B[0].position = [5.628983471588455, 0.7163334557473013, 0.1]
potted_succulent_B[0].rotation = [0, 0, 0]
hardcover_book_B[0].position = [4.145388152686308, 3.601105473024326, 0.0175]
hardcover_book_B[0].rotation = [0, 0, 0]
bookshelf_B[0].position = [3.289540326656425, 5.575361193651565, 0.9]
bookshelf_B[0].rotation = [0, 0, 0]
side_table[0].position = [7.5872855649972335, 2.4151299205176238, 0.275]
side_table[0].rotation = [0, 0, 0]
bookcase_B[0].position = [4.702721534795419, 2.0195537339527263, 1.1]
bookcase_B[0].rotation = [0, 0, 0]
ballpoint_pen_A[0].position = [5.850547815999564, 3.418467964421507, 0.006]
ballpoint_pen_A[0].rotation = [0, 0, 0]
bookcase_C[0].position = [0.05400535097754844, 7.205855694216481, 1.1]
bookcase_C[0].rotation = [0, 0, 0]
pencil[0].position = [9.132045496463224, 0.787497826828343, 0.004]
pencil[0].rotation = [0, 0, 0]
dining_table_B[0].position = [5.702719650793852, 7.013429937314674, 0.375]
dining_table_B[0].rotation = [0, 0, 0]
illustration_print_B[0].position = [0.8653669158863253, 7.403687444590324, 0.35]
illustration_print_B[0].rotation = [0, 0, 0]
pen_holder_cup[0].position = [3.222740053928095, 5.708595085394393, 0.06]
pen_holder_cup[0].rotation = [0, 0, 0]
paperback_book_C[0].position = [2.2055879597570884, 3.5504264683126188, 0.0125]
paperback_book_C[0].rotation = [0, 0, 0]
hardcover_book_C[0].position = [1.4429408551749034, 4.12734216984319, 0.0175]
hardcover_book_C[0].rotation = [0, 0, 0]
photocopier[0].position = [3.6584220579926283, 2.9238178239052663, 0.55]
photocopier[0].rotation = [0, 0, 0]
ballpoint_pen_B[0].position = [3.715387850011196, 0.418002227600916, 0.006]
ballpoint_pen_B[0].rotation = [0, 0, 0]
notepad_B[0].position = [2.0738678854067114, 5.2259630418111325, 0.0075]
notepad_B[0].rotation = [0, 0, 0]
reading_chair_D[0].position = [1.3059472447253706, 3.264679032549038, 0.46]
reading_chair_D[0].rotation = [0, 0, 0]
art_book_B[0].position = [0.4898456465596246, 2.170293215480917, 0.015]
art_book_B[0].rotation = [0, 0, 0]
printed_page_A[0].position = [6.3515160278230045, 1.132240221248237, 0.0005]
printed_page_A[0].rotation = [0, 0, 0]
paperback_book_D[0].position = [1.19731700875779, 2.340642606533672, 0.0125]
paperback_book_D[0].rotation = [0, 0, 0]
reading_chair_E[0].position = [8.587379611118442, 6.385645340856174, 0.46]
reading_chair_E[0].rotation = [0, 0, 0]
hardcover_library_book[0].position = [4.454616329780631, 4.894154111355478, 0.02]
hardcover_library_book[0].rotation = [0, 0, 0]
open_hardcover_book_B[0].position = [7.199414451721568, 2.481497504920837, 0.02]
open_hardcover_book_B[0].rotation = [0, 0, 0]
mirror[0].position = [9.726234083224137, 1.0394995033441965, 0.6]
mirror[0].rotation = [0, 0, 0]
printed_page_B[0].position = [4.209055326742376, 1.6496425318199264, 0.0005]
printed_page_B[0].rotation = [0, 0, 0]
coffee_mug_B[0].position = [5.212077012669858, 0.842324340951332, 0.05]
coffee_mug_B[0].rotation = [0, 0, 0]
base_cabinet[0].position = [5.58591914091584, 1.520672124130686, 0.45]
base_cabinet[0].rotation = [0, 0, 0]
lounge_chair_B[0].position = [4.391743004365881, 4.464220681507649, 0.44]
lounge_chair_B[0].rotation = [0, 0, 0]
reading_chair_F[0].position = [6.56088797401064, 5.837116813980703, 0.46]
reading_chair_F[0].rotation = [0, 0, 0]
paperback_book_E[0].position = [5.949266365930893, 4.852495987416073, 0.0125]
paperback_book_E[0].rotation = [0, 0, 0]
paperback_book_F[0].position = [3.277779550611335, 4.402628613535863, 0.0125]
paperback_book_F[0].rotation = [0, 0, 0]
bookcase_D[0].position = [0.9102686438294727, 0.91094538647987, 1.1]
bookcase_D[0].rotation = [0, 0, 0]
printed_page_C[0].position = [7.249488301682292, 4.694547751550192, 0.0005]
printed_page_C[0].rotation = [0, 0, 0]
sign[0].position = [3.4662585334017795, 1.5211958203910947, 0.125]
sign[0].rotation = [0, 0, 0]
reading_chair_G[0].position = [5.553847724246534, 7.490423390601281, 0.46]
reading_chair_G[0].rotation = [0, 0, 0]
paperback_book_G[0].position = [7.169236565360602, 1.725727235039439, 0.0125]
paperback_book_G[0].rotation = [0, 0, 0]
reading_chair_H[0].position = [9.52838073184089, 3.5965187649446517, 0.46]
reading_chair_H[0].rotation = [0, 0, 0]
hardcover_book_D[0].position = [0.26630435010804976, 6.06380607422267, 0.0175]
hardcover_book_D[0].rotation = [0, 0, 0]
art_print[0].position = [5.477766931699244, 2.20072849757523, 0.4]
art_print[0].rotation = [0, 0, 0]
bookcase_E[0].position = [8.634856169752762, 5.804678487193034, 1.1]
bookcase_E[0].rotation = [0, 0, 0]
paperback_book_H[0].position = [0.9234333734241207, 2.447669814669751, 0.0125]
paperback_book_H[0].rotation = [0, 0, 0]
reading_chair_A[0].position = [6.876241289841589, 2.286531448067424, 0.46]
reading_chair_A[0].rotation = [0, 0, 0]
open_hardcover_book_A[0].position = [2.4598162486664976, 2.5583458866489166, 0.02]
open_hardcover_book_A[0].rotation = [0, 0, 0]
handout_sheet[0].position = [1.6035075191002346, 0.7883557998752846, 0.0005]
handout_sheet[0].rotation = [0, 0, 0]
lounge_chair_A[0].position = [6.138081099631593, 6.117787106387567, 0.44]
lounge_chair_A[0].rotation = [0, 0, 0]
reading_chair_B[0].position = [4.067876076777486, 1.6268157704149109, 0.46]
reading_chair_B[0].rotation = [0, 0, 0]
engraving_print[0].position = [8.52846075142169, 7.052678887429388, 0.35]
engraving_print[0].rotation = [0, 0, 0]
highlighter_marker[0].position = [4.961033986198107, 1.2643186944422435, 0.01]
highlighter_marker[0].rotation = [0, 0, 0]
art_book_A[0].position = [3.7495865710895426, 2.9529195532534884, 0.015]
art_book_A[0].rotation = [0, 0, 0]
drink_coaster[0].position = [9.214174945389798, 3.4992958062118187, 0.004]
drink_coaster[0].rotation = [0, 0, 0]
typography_poster[0].position = [9.589744261447061, 2.2028704112528925, 0.45]
typography_poster[0].rotation = [0, 0, 0]
notepad_A[0].position = [0.5011096143909233, 6.867475053943234, 0.0075]
notepad_A[0].rotation = [0, 0, 0]
photograph_print[0].position = [5.367888146718974, 2.5427747594695354, 0.15]
photograph_print[0].rotation = [0, 0, 0]
whiteboard[0].position = [3.9558375501674705, 1.8902160381061728, 0.6]
whiteboard[0].rotation = [0, 0, 0]
hardcover_book_A[0].position = [1.5311627881304746, 6.052320574335496, 0.0175]
hardcover_book_A[0].rotation = [0, 0, 0]
potted_succulent_A[0].position = [2.7376971766520586, 0.1871597812481801, 0.11]
potted_succulent_A[0].rotation = [0, 0, 0]
bookshelf_A[0].position = [4.4661703664621255, 1.5022686904842721, 0.9]
bookshelf_A[0].rotation = [0, 0, 0]
desk_lamp[0].position = [6.897059198575749, 2.0194750762617057, 0.24]
desk_lamp[0].rotation = [0, 0, 0]
bookcase_A[0].position = [3.641039609994902, 1.2744906955455868, 1.1]
bookcase_A[0].rotation = [0, 0, 0]
paperback_book_A[0].position = [1.5981137435969694, 4.56375684976902, 0.0125]
paperback_book_A[0].rotation = [0, 0, 0]
dining_table_A[0].position = [7.449960965255185, 3.0789431679131516, 0.375]
dining_table_A[0].rotation = [0, 0, 0]
illustration_print_A[0].position = [0.0743579104293457, 7.300894559629232, 0.35]
illustration_print_A[0].rotation = [0, 0, 0]
clock[0].position = [2.971581802621267, 1.5539540393003801, 0.175]
clock[0].rotation = [0, 0, 0]
coffee_mug_A[0].position = [1.1331234766209797, 3.325918336770239, 0.05]
coffee_mug_A[0].rotation = [0, 0, 0]
paperback_book_B[0].position = [4.4610939985510365, 6.266131511659219, 0.0125]
paperback_book_B[0].rotation = [0, 0, 0]
floor_lamp[0].position = [4.994572643475786, 2.3041046330867503, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
reading_chair_C[0].position = [4.299373299268874, 5.643105928716576, 0.46]
reading_chair_C[0].rotation = [0, 0, 0]
potted_succulent_B[0].position = [5.628983471588455, 0.7163334557473013, 0.1]
potted_succulent_B[0].rotation = [0, 0, 0]
hardcover_book_B[0].position = [4.145388152686308, 3.601105473024326, 0.0175]
hardcover_book_B[0].rotation = [0, 0, 0]
bookshelf_B[0].position = [3.289540326656425, 5.575361193651565, 0.9]
bookshelf_B[0].rotation = [0, 0, 0]
side_table[0].position = [7.5872855649972335, 2.4151299205176238, 0.275]
side_table[0].rotation = [0, 0, 0]
bookcase_B[0].position = [4.702721534795419, 2.0195537339527263, 1.1]
bookcase_B[0].rotation = [0, 0, 0]
ballpoint_pen_A[0].position = [5.850547815999564, 3.418467964421507, 0.006]
ballpoint_pen_A[0].rotation = [0, 0, 0]
bookcase_C[0].position = [0.05400535097754844, 7.205855694216481, 1.1]
bookcase_C[0].rotation = [0, 0, 0]
pencil[0].position = [9.132045496463224, 0.787497826828343, 0.004]
pencil[0].rotation = [0, 0, 0]
dining_table_B[0].position = [5.702719650793852, 7.013429937314674, 0.375]
dining_table_B[0].rotation = [0, 0, 0]
illustration_print_B[0].position = [0.8653669158863253, 7.403687444590324, 0.35]
illustration_print_B[0].rotation = [0, 0, 0]
pen_holder_cup[0].position = [3.222740053928095, 5.708595085394393, 0.06]
pen_holder_cup[0].rotation = [0, 0, 0]
paperback_book_C[0].position = [2.2055879597570884, 3.5504264683126188, 0.0125]
paperback_book_C[0].rotation = [0, 0, 0]
hardcover_book_C[0].position = [1.4429408551749034, 4.12734216984319, 0.0175]
hardcover_book_C[0].rotation = [0, 0, 0]
photocopier[0].position = [3.6584220579926283, 2.9238178239052663, 0.55]
photocopier[0].rotation = [0, 0, 0]
ballpoint_pen_B[0].position = [3.715387850011196, 0.418002227600916, 0.006]
ballpoint_pen_B[0].rotation = [0, 0, 0]
notepad_B[0].position = [2.0738678854067114, 5.2259630418111325, 0.0075]
notepad_B[0].rotation = [0, 0, 0]
reading_chair_D[0].position = [1.3059472447253706, 3.264679032549038, 0.46]
reading_chair_D[0].rotation = [0, 0, 0]
art_book_B[0].position = [0.4898456465596246, 2.170293215480917, 0.015]
art_book_B[0].rotation = [0, 0, 0]
printed_page_A[0].position = [6.3515160278230045, 1.132240221248237, 0.0005]
printed_page_A[0].rotation = [0, 0, 0]
paperback_book_D[0].position = [1.19731700875779, 2.340642606533672, 0.0125]
paperback_book_D[0].rotation = [0, 0, 0]
reading_chair_E[0].position = [8.587379611118442, 6.385645340856174, 0.46]
reading_chair_E[0].rotation = [0, 0, 0]
hardcover_library_book[0].position = [4.454616329780631, 4.894154111355478, 0.02]
hardcover_library_book[0].rotation = [0, 0, 0]
open_hardcover_book_B[0].position = [7.199414451721568, 2.481497504920837, 0.02]
open_hardcover_book_B[0].rotation = [0, 0, 0]
mirror[0].position = [9.726234083224137, 1.0394995033441965, 0.6]
mirror[0].rotation = [0, 0, 0]
printed_page_B[0].position = [4.209055326742376, 1.6496425318199264, 0.0005]
printed_page_B[0].rotation = [0, 0, 0]
coffee_mug_B[0].position = [5.212077012669858, 0.842324340951332, 0.05]
coffee_mug_B[0].rotation = [0, 0, 0]
base_cabinet[0].position = [5.58591914091584, 1.520672124130686, 0.45]
base_cabinet[0].rotation = [0, 0, 0]
lounge_chair_B[0].position = [4.391743004365881, 4.464220681507649, 0.44]
lounge_chair_B[0].rotation = [0, 0, 0]
reading_chair_F[0].position = [6.56088797401064, 5.837116813980703, 0.46]
reading_chair_F[0].rotation = [0, 0, 0]
paperback_book_E[0].position = [5.949266365930893, 4.852495987416073, 0.0125]
paperback_book_E[0].rotation = [0, 0, 0]
paperback_book_F[0].position = [3.277779550611335, 4.402628613535863, 0.0125]
paperback_book_F[0].rotation = [0, 0, 0]
bookcase_D[0].position = [0.9102686438294727, 0.91094538647987, 1.1]
bookcase_D[0].rotation = [0, 0, 0]
printed_page_C[0].position = [7.249488301682292, 4.694547751550192, 0.0005]
printed_page_C[0].rotation = [0, 0, 0]
sign[0].position = [3.4662585334017795, 1.5211958203910947, 0.125]
sign[0].rotation = [0, 0, 0]
reading_chair_G[0].position = [5.553847724246534, 7.490423390601281, 0.46]
reading_chair_G[0].rotation = [0, 0, 0]
paperback_book_G[0].position = [7.169236565360602, 1.725727235039439, 0.0125]
paperback_book_G[0].rotation = [0, 0, 0]
reading_chair_H[0].position = [9.52838073184089, 3.5965187649446517, 0.46]
reading_chair_H[0].rotation = [0, 0, 0]
hardcover_book_D[0].position = [0.26630435010804976, 6.06380607422267, 0.0175]
hardcover_book_D[0].rotation = [0, 0, 0]
art_print[0].position = [5.477766931699244, 2.20072849757523, 0.4]
art_print[0].rotation = [0, 0, 0]
bookcase_E[0].position = [8.634856169752762, 5.804678487193034, 1.1]
bookcase_E[0].rotation = [0, 0, 0]
paperback_book_H[0].position = [0.9234333734241207, 2.447669814669751, 0.0125]
paperback_book_H[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed references are used only as solver targets; they are not scene assets.
heading_east = AssetInstance(rotation=[0, 0, radians(0)])
heading_north = AssetInstance(rotation=[0, 0, radians(90)])
heading_west = AssetInstance(rotation=[0, 0, radians(180)])
heading_south = AssetInstance(rotation=[0, 0, radians(270)])


def place_floor_asset(asset_group, x, y, yaw_degrees, heading_reference):
    """Place a floor-standing asset at a fixed plan position and orientation."""
    asset_group[0].position = [x, y, asset_group.size[2] / 2]
    asset_group[0].rotation = [0, 0, radians(yaw_degrees)]

    target = AssetInstance(position=[x, y, asset_group.size[2] / 2])
    solver.distance_constraint(
        asset_group[0], target, 0, 0, weight=10
    )
    solver.align_with(asset_group[0], heading_reference)


def place_wall_asset(asset_group, x, z, yaw_degrees):
    """Mount an asset on the north wall, facing into the room."""
    asset_group[0].position = [x, 7.50 - asset_group.size[0] / 2, z]
    asset_group[0].rotation = [0, 0, radians(yaw_degrees)]

    solver.against_wall(asset_group[0], walls[2])
    solver.align_with(asset_group[0], heading_south)


def place_on_surface(
    asset_group, support_group, x, y, relative_angle_degrees=0
):
    """Place a small asset at a specified location on a support surface."""
    support_top = (
        support_group[0].position[2] + support_group.size[2] / 2
    )
    object_z = support_top + asset_group.size[2] / 2

    asset_group[0].position = [x, y, object_z]
    asset_group[0].rotation = [
        0,
        0,
        support_group[0].rotation[2] + radians(relative_angle_degrees),
    ]

    # The vertical constraint is listed first because keeping small objects
    # on their supporting furniture is the most important requirement.
    solver.on_top_of(asset_group[0], support_group[0])
    solver.distance_constraint(
        asset_group[0],
        AssetInstance(position=[x, y, object_z]),
        0,
        0,
        weight=10,
    )
    solver.align_with(
        asset_group[0],
        support_group[0],
        angle=relative_angle_degrees,
    )


# ---------------------------------------------------------------------------
# Large storage and work furniture
# ---------------------------------------------------------------------------

# Tall storage is distributed along the side walls, preserving the middle of
# the room for tables, chairs, and circulation.
place_floor_asset(bookshelf_A, 0.16, 1.10, 0, heading_east)
solver.against_wall(bookshelf_A[0], walls[3])

place_floor_asset(bookshelf_B, 0.16, 2.65, 0, heading_east)
solver.against_wall(bookshelf_B[0], walls[3])

place_floor_asset(base_cabinet, 0.275, 4.50, 0, heading_east)
solver.against_wall(base_cabinet[0], walls[3])

place_floor_asset(bookcase_A, 9.825, 0.70, 180, heading_west)
solver.against_wall(bookcase_A[0], walls[1])

place_floor_asset(bookcase_B, 9.825, 1.80, 180, heading_west)
solver.against_wall(bookcase_B[0], walls[1])

place_floor_asset(bookcase_C, 9.825, 2.90, 180, heading_west)
solver.against_wall(bookcase_C[0], walls[1])

place_floor_asset(bookcase_D, 9.825, 4.00, 180, heading_west)
solver.against_wall(bookcase_D[0], walls[1])

place_floor_asset(bookcase_E, 9.825, 5.10, 180, heading_west)
solver.against_wall(bookcase_E[0], walls[1])

place_floor_asset(photocopier, 8.70, 0.325, 90, heading_north)
solver.against_wall(photocopier[0], walls[0])

# Two central tables create separate reading and study stations.
place_floor_asset(dining_table_A, 3.00, 3.75, 0, heading_east)
place_floor_asset(dining_table_B, 7.00, 3.75, 0, heading_east)

place_floor_asset(side_table, 5.00, 6.85, 0, heading_east)
place_floor_asset(floor_lamp, 1.00, 6.85, 0, heading_east)


# ---------------------------------------------------------------------------
# Reading and lounge seating
# ---------------------------------------------------------------------------

# The three chairs associated with o0042, o0004, and o0060 are initialized
# collinearly. The equal-distance constraints make reading_chair_A the
# midpoint, and therefore between reading_chair_C and reading_chair_F.
reading_chair_C[0].position = [2.20, 1.40, 0.46]
reading_chair_C[0].rotation = [0, 0, radians(45)]
reading_chair_A[0].position = [5.00, 1.40, 0.46]
reading_chair_A[0].rotation = [0, 0, radians(90)]
reading_chair_F[0].position = [7.80, 1.40, 0.46]
reading_chair_F[0].rotation = [0, 0, radians(135)]

solver.distance_constraint(
    reading_chair_A[0], reading_chair_C[0], 2.80, 2.80, weight=10
)
solver.distance_constraint(
    reading_chair_A[0], reading_chair_F[0], 2.80, 2.80, weight=10
)
solver.distance_constraint(
    reading_chair_C[0], reading_chair_F[0], 5.60, 5.60, weight=10
)

solver.distance_constraint(
    reading_chair_C[0],
    AssetInstance(position=[2.20, 1.40, 0.46]),
    0,
    0,
    weight=10,
)
solver.distance_constraint(
    reading_chair_A[0],
    AssetInstance(position=[5.00, 1.40, 0.46]),
    0,
    0,
    weight=10,
)
solver.distance_constraint(
    reading_chair_F[0],
    AssetInstance(position=[7.80, 1.40, 0.46]),
    0,
    0,
    weight=10,
)
solver.point_towards(reading_chair_C[0], dining_table_A[0])
solver.point_towards(reading_chair_A[0], dining_table_A[0])
solver.point_towards(reading_chair_F[0], dining_table_B[0])

# Additional chairs are arranged around the tables with useful clearances.
reading_chair_B[0].position = [4.50, 2.25, 0.46]
reading_chair_B[0].rotation = [0, 0, radians(135)]
solver.distance_constraint(
    reading_chair_B[0],
    AssetInstance(position=[4.50, 2.25, 0.46]),
    0,
    0,
    weight=10,
)
solver.point_towards(reading_chair_B[0], dining_table_A[0])

reading_chair_E[0].position = [5.50, 2.25, 0.46]
reading_chair_E[0].rotation = [0, 0, radians(45)]
solver.distance_constraint(
    reading_chair_E[0],
    AssetInstance(position=[5.50, 2.25, 0.46]),
    0,
    0,
    weight=10,
)
solver.point_towards(reading_chair_E[0], dining_table_B[0])

# The chair associated with o0046 explicitly faces the bookcase associated
# with o0032; this semantic orientation is listed before its position anchor.
reading_chair_D[0].position = [2.10, 5.70, 0.46]
reading_chair_D[0].rotation = [0, 0, radians(315)]
solver.point_towards(reading_chair_D[0], bookcase_A[0])
solver.distance_constraint(
    reading_chair_D[0],
    AssetInstance(position=[2.10, 5.70, 0.46]),
    0,
    0,
    weight=10,
)

reading_chair_G[0].position = [4.10, 5.70, 0.46]
reading_chair_G[0].rotation = [0, 0, radians(315)]
solver.distance_constraint(
    reading_chair_G[0],
    AssetInstance(position=[4.10, 5.70, 0.46]),
    0,
    0,
    weight=10,
)
solver.point_towards(reading_chair_G[0], dining_table_A[0])

reading_chair_H[0].position = [5.90, 5.70, 0.46]
reading_chair_H[0].rotation = [0, 0, radians(225)]
solver.distance_constraint(
    reading_chair_H[0],
    AssetInstance(position=[5.90, 5.70, 0.46]),
    0,
    0,
    weight=10,
)
solver.point_towards(reading_chair_H[0], dining_table_B[0])

lounge_chair_A[0].position = [1.00, 5.80, 0.44]
lounge_chair_A[0].rotation = [0, 0, radians(315)]
solver.distance_constraint(
    lounge_chair_A[0],
    AssetInstance(position=[1.00, 5.80, 0.44]),
    0,
    0,
    weight=10,
)
solver.point_towards(lounge_chair_A[0], dining_table_A[0])

lounge_chair_B[0].position = [8.55, 6.55, 0.44]
lounge_chair_B[0].rotation = [0, 0, radians(225)]
solver.distance_constraint(
    lounge_chair_B[0],
    AssetInstance(position=[8.55, 6.55, 0.44]),
    0,
    0,
    weight=10,
)
solver.point_towards(lounge_chair_B[0], dining_table_B[0])


# ---------------------------------------------------------------------------
# Wall-mounted displays
# ---------------------------------------------------------------------------

# These pieces share the north wall at non-overlapping horizontal positions.
place_wall_asset(engraving_print, 0.45, 1.55, 270)
place_wall_asset(typography_poster, 1.15, 1.65, 270)
place_wall_asset(photograph_print, 1.80, 1.45, 270)
place_wall_asset(whiteboard, 3.05, 1.55, 270)
place_wall_asset(illustration_print_A, 4.45, 1.55, 270)
place_wall_asset(clock, 5.05, 1.75, 270)
place_wall_asset(illustration_print_B, 5.65, 1.55, 270)
place_wall_asset(mirror, 6.45, 1.55, 270)
place_wall_asset(sign, 7.35, 1.65, 270)
place_wall_asset(art_print, 8.35, 1.60, 270)


# ---------------------------------------------------------------------------
# Objects on dining table A
# ---------------------------------------------------------------------------

place_on_surface(open_hardcover_book_A, dining_table_A, 2.72, 3.12, 90)
place_on_surface(handout_sheet, dining_table_A, 3.08, 3.12, 90)
place_on_surface(highlighter_marker, dining_table_A, 3.30, 3.18, 90)

place_on_surface(art_book_A, dining_table_A, 2.72, 3.55, 90)
place_on_surface(drink_coaster, dining_table_A, 3.05, 3.50, 0)
place_on_surface(coffee_mug_A, dining_table_A, 3.30, 3.50, 0)

place_on_surface(notepad_A, dining_table_A, 2.72, 3.90, 90)
place_on_surface(hardcover_book_A, dining_table_A, 3.05, 3.88, 90)
place_on_surface(paperback_book_A, dining_table_A, 3.30, 3.88, 90)

place_on_surface(potted_succulent_A, dining_table_A, 2.72, 4.25, 0)
place_on_surface(desk_lamp, dining_table_A, 3.08, 4.35, 0)
place_on_surface(paperback_book_B, dining_table_A, 3.32, 4.20, 90)


# ---------------------------------------------------------------------------
# Objects on dining table B
# ---------------------------------------------------------------------------

place_on_surface(ballpoint_pen_A, dining_table_B, 6.70, 3.12, 90)
place_on_surface(pencil, dining_table_B, 6.88, 3.12, 90)
place_on_surface(pen_holder_cup, dining_table_B, 7.25, 3.15, 0)

place_on_surface(paperback_book_C, dining_table_B, 6.72, 3.48, 90)
place_on_surface(hardcover_book_C, dining_table_B, 7.02, 3.48, 90)
place_on_surface(ballpoint_pen_B, dining_table_B, 7.30, 3.48, 90)

place_on_surface(notepad_B, dining_table_B, 6.72, 3.84, 90)
place_on_surface(art_book_B, dining_table_B, 7.05, 3.84, 90)
place_on_surface(printed_page_A, dining_table_B, 7.32, 3.84, 90)

place_on_surface(paperback_book_D, dining_table_B, 6.70, 4.20, 90)
place_on_surface(hardcover_library_book, dining_table_B, 7.00, 4.20, 90)
place_on_surface(potted_succulent_B, dining_table_B, 7.30, 4.25, 0)


# ---------------------------------------------------------------------------
# Objects on the base cabinet
# ---------------------------------------------------------------------------

place_on_surface(open_hardcover_book_B, base_cabinet, 0.16, 4.05, 0)
place_on_surface(printed_page_B, base_cabinet, 0.40, 4.05, 0)
place_on_surface(coffee_mug_B, base_cabinet, 0.16, 4.48, 0)
place_on_surface(paperback_book_E, base_cabinet, 0.40, 4.45, 0)
place_on_surface(paperback_book_F, base_cabinet, 0.16, 4.90, 0)
place_on_surface(printed_page_C, base_cabinet, 0.40, 4.88, 0)


# ---------------------------------------------------------------------------
# Remaining reading materials on the side table and bookshelf tops
# ---------------------------------------------------------------------------

place_on_surface(paperback_book_G, side_table, 4.88, 6.82, 90)
place_on_surface(hardcover_book_D, side_table, 5.13, 6.82, 90)

place_on_surface(paperback_book_H, bookshelf_A, 0.16, 0.90, 0)

solver.constraints = []
mirror[0].position = [6.449999809265137, 7.4800004959106445, 0.6000000238418579]
mirror[0].rotation = [0, 0, -1.5707962773448176]
mirror[0].optimize = 2
printed_page_C[0].position = [0.4000000059604645, 4.880000114440918, 0.8999999761581421]
printed_page_C[0].rotation = [0, 0, 9.730671106951018e-08]
printed_page_C[0].optimize = 2
paperback_book_C[0].position = [6.71999979019165, 3.4800000190734863, 0.7649999856948853]
paperback_book_C[0].rotation = [0, 0, 1.6681857206728574]
paperback_book_C[0].optimize = 2
desk_lamp[0].position = [3.0799999237060547, 4.349999904632568, 0.9900000095367432]
desk_lamp[0].rotation = [0, 0, 0.10053091536841949]
desk_lamp[0].optimize = 2
photocopier[0].position = [8.699999809265137, 0.34999996423721313, 0.550000011920929]
photocopier[0].rotation = [0, 0, 1.5707963775729508]
photocopier[0].optimize = 2
pencil[0].position = [6.880000114440918, 3.119999885559082, 0.7549999952316284]
pencil[0].rotation = [0, 0, 1.6681857206728574]
pencil[0].optimize = 2
drink_coaster[0].position = [3.049999952316284, 3.5, 0.7549999952316284]
drink_coaster[0].rotation = [0, 0, 0.10053091536841949]
drink_coaster[0].optimize = 2
art_print[0].position = [8.350000381469727, 7.485000133514404, 0.4000000059604645]
art_print[0].rotation = [0, 0, -1.5707962797591872]
art_print[0].optimize = 2
hardcover_book_A[0].position = [3.049999952316284, 3.880000114440918, 0.7699999809265137]
hardcover_book_A[0].rotation = [0, 0, 1.6713272822810157]
hardcover_book_A[0].optimize = 2
open_hardcover_book_B[0].position = [0.1599999964237213, 4.050000190734863, 0.9199999570846558]
open_hardcover_book_B[0].rotation = [0, 0, 9.730671106951018e-08]
open_hardcover_book_B[0].optimize = 2
notepad_B[0].position = [6.71999979019165, 3.8399999141693115, 0.7549999952316284]
notepad_B[0].rotation = [0, 0, 1.6681857206728574]
notepad_B[0].optimize = 2
paperback_book_B[0].position = [3.319999933242798, 4.199999809265137, 0.7649999856948853]
paperback_book_B[0].rotation = [0, 0, 1.6713272822810157]
paperback_book_B[0].optimize = 2
illustration_print_B[0].position = [5.650000095367432, 7.4850006103515625, 0.3499999940395355]
illustration_print_B[0].rotation = [0, 0, -1.5707962808099358]
illustration_print_B[0].optimize = 2
reading_chair_E[0].position = [5.5, 2.25, 0.46000000834465027]
reading_chair_E[0].rotation = [0, 0, 0.7948229285630478]
reading_chair_E[0].optimize = 2
clock[0].position = [5.050000190734863, 7.47499942779541, 0.17499999701976776]
clock[0].rotation = [0, 0, -1.5707962831105493]
clock[0].optimize = 2
reading_chair_H[0].position = [5.900000095367432, 5.699999809265137, 0.46000000834465027]
reading_chair_H[0].rotation = [0, 0, -1.3163507845775626]
reading_chair_H[0].optimize = 2
paperback_book_H[0].position = [0.1599999964237213, 0.8999999761581421, 1.8149999380111694]
paperback_book_H[0].rotation = [0, 0, 3.3933939273007006e-08]
paperback_book_H[0].optimize = 2
open_hardcover_book_A[0].position = [2.7200000286102295, 3.119999885559082, 0.7699999809265137]
open_hardcover_book_A[0].rotation = [0, 0, 1.6713272822810157]
open_hardcover_book_A[0].optimize = 2
ballpoint_pen_A[0].position = [6.699999809265137, 3.119999885559082, 0.7549999952316284]
ballpoint_pen_A[0].rotation = [0, 0, 1.6681857206728574]
ballpoint_pen_A[0].optimize = 2
whiteboard[0].position = [3.049999952316284, 7.475000381469727, 0.6000000238418579]
whiteboard[0].rotation = [0, 0, -1.5707962805517064]
whiteboard[0].optimize = 2
lounge_chair_B[0].position = [8.550000190734863, 6.550000190734863, 0.4399999976158142]
lounge_chair_B[0].rotation = [0, 0, -2.3467697250267454]
lounge_chair_B[0].optimize = 2
bookcase_C[0].position = [9.82500171661377, 2.9000000953674316, 1.100000023841858]
bookcase_C[0].rotation = [0, 0, -3.141592617533322]
bookcase_C[0].optimize = 2
potted_succulent_A[0].position = [2.7200000286102295, 4.25, 0.8600000143051147]
potted_succulent_A[0].rotation = [0, 0, 0.10053091536841949]
potted_succulent_A[0].optimize = 2
base_cabinet[0].position = [0.2749999761581421, 4.5, 0.44999998807907104]
base_cabinet[0].rotation = [0, 0, 6.62716312851443e-08]
base_cabinet[0].optimize = 2
dining_table_A[0].position = [3.0, 3.75, 0.375]
dining_table_A[0].rotation = [0, 0, 0.10053096307930048]
dining_table_A[0].optimize = 2
reading_chair_C[0].position = [2.200000047683716, 1.399999976158142, 0.46000000834465027]
reading_chair_C[0].rotation = [0, 0, 0.8557578282828207]
reading_chair_C[0].optimize = 2
bookcase_D[0].position = [9.82500171661377, 4.0, 1.100000023841858]
bookcase_D[0].rotation = [0, 0, -3.141592617533325]
bookcase_D[0].optimize = 2
bookshelf_B[0].position = [0.1600000113248825, 2.6500000953674316, 0.8999999761581421]
bookshelf_B[0].rotation = [0, 0, 4.424876971605028e-08]
bookshelf_B[0].optimize = 2
sign[0].position = [7.349999904632568, 7.485000133514404, 0.125]
sign[0].rotation = [0, 0, -1.5707962797591872]
sign[0].optimize = 2
highlighter_marker[0].position = [3.299999952316284, 3.180000066757202, 0.7599999904632568]
highlighter_marker[0].rotation = [0, 0, 1.6713272822810157]
highlighter_marker[0].optimize = 2
engraving_print[0].position = [0.44999998807907104, 7.4850006103515625, 0.3499999940395355]
engraving_print[0].rotation = [0, 0, -1.5707962808099358]
engraving_print[0].optimize = 2
coffee_mug_A[0].position = [3.299999952316284, 3.5, 0.800000011920929]
coffee_mug_A[0].rotation = [0, 0, 0.10053091536841949]
coffee_mug_A[0].optimize = 2
hardcover_library_book[0].position = [7.0, 4.199999809265137, 0.7699999809265137]
hardcover_library_book[0].rotation = [0, 0, 1.6681857206728574]
hardcover_library_book[0].optimize = 2
coffee_mug_B[0].position = [0.1599999964237213, 4.480000019073486, 0.949999988079071]
coffee_mug_B[0].rotation = [0, 0, 9.730671106951018e-08]
coffee_mug_B[0].optimize = 2
photograph_print[0].position = [1.7999999523162842, 7.4850006103515625, 0.15000000596046448]
photograph_print[0].rotation = [0, 0, -1.5707962829366726]
photograph_print[0].optimize = 2
art_book_B[0].position = [7.050000190734863, 3.8399999141693115, 0.7649999856948853]
art_book_B[0].rotation = [0, 0, 1.6681857206728574]
art_book_B[0].optimize = 2
reading_chair_A[0].position = [5.0, 1.399999976158142, 0.46000000834465027]
reading_chair_A[0].rotation = [0, 0, 2.0445018422339354]
reading_chair_A[0].optimize = 2
typography_poster[0].position = [1.149999976158142, 7.4900007247924805, 0.44999998807907104]
typography_poster[0].rotation = [0, 0, -1.5707962966001832]
typography_poster[0].optimize = 2
paperback_book_G[0].position = [4.880000114440918, 6.820000171661377, 0.5649999976158142]
paperback_book_G[0].rotation = [0, 0, 1.59278752351864]
paperback_book_G[0].optimize = 2
hardcover_book_B[0].position = [4.145388126373291, 3.6011054515838623, 0.019999999552965164]
hardcover_book_B[0].rotation = [0, 0, 0.00314159280673765]
hardcover_book_B[0].optimize = 2
paperback_book_E[0].position = [0.4000000059604645, 4.449999809265137, 0.9149999618530273]
paperback_book_E[0].rotation = [0, 0, 9.730671106951018e-08]
paperback_book_E[0].optimize = 2
bookcase_B[0].position = [9.82500171661377, 1.7999999523162842, 1.100000023841858]
bookcase_B[0].rotation = [0, 0, -3.141592617533322]
bookcase_B[0].optimize = 2
printed_page_A[0].position = [7.320000171661377, 3.8399999141693115, 0.75]
printed_page_A[0].rotation = [0, 0, 1.6681857206728574]
printed_page_A[0].optimize = 2
handout_sheet[0].position = [3.0799999237060547, 3.119999885559082, 0.75]
handout_sheet[0].rotation = [0, 0, 1.6713272822810157]
handout_sheet[0].optimize = 2
ballpoint_pen_B[0].position = [7.300000190734863, 3.4800000190734863, 0.7549999952316284]
ballpoint_pen_B[0].rotation = [0, 0, 1.6681857206728574]
ballpoint_pen_B[0].optimize = 2
side_table[0].position = [5.0, 6.849999904632568, 0.2750000059604645]
side_table[0].rotation = [0, 0, 0.021991148286022624]
side_table[0].optimize = 2
paperback_book_A[0].position = [3.299999952316284, 3.880000114440918, 0.7649999856948853]
paperback_book_A[0].rotation = [0, 0, 1.6713272822810157]
paperback_book_A[0].optimize = 2
illustration_print_A[0].position = [4.449999809265137, 7.4850006103515625, 0.3499999940395355]
illustration_print_A[0].rotation = [0, 0, -1.5707962808099358]
illustration_print_A[0].optimize = 2
hardcover_book_C[0].position = [7.019999980926514, 3.4800000190734863, 0.7699999809265137]
hardcover_book_C[0].rotation = [0, 0, 1.6681857206728574]
hardcover_book_C[0].optimize = 2
bookshelf_A[0].position = [0.1600000113248825, 1.100000023841858, 0.8999999761581421]
bookshelf_A[0].rotation = [0, 0, 4.3121969571592895e-08]
bookshelf_A[0].optimize = 2
reading_chair_G[0].position = [4.099999904632568, 5.699999809265137, 0.46000000834465027]
reading_chair_G[0].rotation = [0, 0, -1.7704552956317743]
reading_chair_G[0].optimize = 2
paperback_book_F[0].position = [0.1599999964237213, 4.900000095367432, 0.9149999618530273]
paperback_book_F[0].rotation = [0, 0, 9.730671106951018e-08]
paperback_book_F[0].optimize = 2
notepad_A[0].position = [2.7200000286102295, 3.9000000953674316, 0.7549999952316284]
notepad_A[0].rotation = [0, 0, 1.6713272822810157]
notepad_A[0].optimize = 2
hardcover_book_D[0].position = [5.130000114440918, 6.820000171661377, 0.5699999928474426]
hardcover_book_D[0].rotation = [0, 0, 1.59278752351864]
hardcover_book_D[0].optimize = 2
printed_page_B[0].position = [0.4000000059604645, 4.050000190734863, 0.8999999761581421]
printed_page_B[0].rotation = [0, 0, 9.730671106951018e-08]
printed_page_B[0].optimize = 2
bookcase_A[0].position = [9.824999809265137, 0.699999988079071, 1.100000023841858]
bookcase_A[0].rotation = [0, 0, -3.141592601376796]
bookcase_A[0].optimize = 2
bookcase_E[0].position = [9.82500171661377, 5.099999904632568, 1.100000023841858]
bookcase_E[0].rotation = [0, 0, -3.141592617533325]
bookcase_E[0].optimize = 2
reading_chair_B[0].position = [4.5, 2.25, 0.46000000834465027]
reading_chair_B[0].rotation = [0, 0, 2.3656192553579443]
reading_chair_B[0].optimize = 2
potted_succulent_B[0].position = [7.300000190734863, 4.25, 0.8500000238418579]
potted_succulent_B[0].rotation = [0, 0, 0.09738936346752035]
potted_succulent_B[0].optimize = 2
art_book_A[0].position = [2.7200000286102295, 3.549999952316284, 0.7649999856948853]
art_book_A[0].rotation = [0, 0, 1.6713272822810157]
art_book_A[0].optimize = 2
pen_holder_cup[0].position = [7.25, 3.1500000953674316, 0.8100000023841858]
pen_holder_cup[0].rotation = [0, 0, 0.09738936346752035]
pen_holder_cup[0].optimize = 2
lounge_chair_A[0].position = [1.0, 5.800000190734863, 0.4399999976158142]
lounge_chair_A[0].rotation = [0, 0, -0.7759733982318487]
lounge_chair_A[0].optimize = 2
reading_chair_D[0].position = [2.0999999046325684, 5.699999809265137, 0.46000000834465027]
reading_chair_D[0].rotation = [0, 0, -0.6233212264339383]
reading_chair_D[0].optimize = 2
paperback_book_D[0].position = [6.699999809265137, 4.199999809265137, 0.7649999856948853]
paperback_book_D[0].rotation = [0, 0, 1.6681857206728574]
paperback_book_D[0].optimize = 2
floor_lamp[0].position = [1.0, 6.849999904632568, 0.824999988079071]
floor_lamp[0].rotation = [0, 0, 0.00942477746072377]
floor_lamp[0].optimize = 2
dining_table_B[0].position = [7.0, 3.75, 0.375]
dining_table_B[0].rotation = [0, 0, 0.09738936892896775]
dining_table_B[0].optimize = 2
reading_chair_F[0].position = [7.800000190734863, 1.399999976158142, 0.46000000834465027]
reading_chair_F[0].rotation = [0, 0, 2.2506268378858114]
reading_chair_F[0].optimize = 2

