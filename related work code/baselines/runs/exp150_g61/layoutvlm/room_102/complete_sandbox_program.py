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
framed_poster_A = Assets(description="A blue painting in a black frame.", size=[0.04, 0.80, 1.10], placements=[AssetInstance() for _ in range(1)])
floor_planter_A = Assets(description="floor planter", size=[0.45, 0.45, 1.20], placements=[AssetInstance() for _ in range(1)])
conference_chair_A = Assets(description="A black office chair.", size=[0.65, 0.65, 1.05], placements=[AssetInstance() for _ in range(1)])
lounge_side_table = Assets(description="A small square table made of wood.", size=[0.55, 0.55, 0.50], placements=[AssetInstance() for _ in range(1)])
magazine_A = Assets(description="Folded up newspaper with black print.", size=[0.22, 0.28, 0.01], placements=[AssetInstance() for _ in range(1)])
conference_chair_B = Assets(description="A black office chair.", size=[0.65, 0.65, 1.05], placements=[AssetInstance() for _ in range(1)])
floor_planter_B = Assets(description="floor planter", size=[0.45, 0.45, 1.20], placements=[AssetInstance() for _ in range(1)])
storage_cabinet_A = Assets(description="A grey upright filing cabinet.", size=[0.62, 0.50, 1.35], placements=[AssetInstance() for _ in range(1)])
framed_poster_B = Assets(description="A blue painting in a black frame.", size=[0.04, 0.80, 1.10], placements=[AssetInstance() for _ in range(1)])
floor_planter_C = Assets(description="floor planter", size=[0.45, 0.45, 1.20], placements=[AssetInstance() for _ in range(1)])
conference_chair_C = Assets(description="A black office chair.", size=[0.65, 0.65, 1.05], placements=[AssetInstance() for _ in range(1)])
lounge_armchair_A = Assets(description="This is an armchair with tall arms.", size=[0.85, 0.85, 0.95], placements=[AssetInstance() for _ in range(1)])
paper_ream_A = Assets(description="Paper scroll with lines of handwriting.", size=[0.30, 0.21, 0.05], placements=[AssetInstance() for _ in range(1)])
notepad_A = Assets(description="A red notepad decorated with a slug in the lower corner.", size=[0.21, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
coat_stand_A = Assets(description="A very tall candle holder.", size=[0.55, 0.55, 1.80], placements=[AssetInstance() for _ in range(1)])
magazine_B = Assets(description="Folded up newspaper with black print.", size=[0.22, 0.28, 0.01], placements=[AssetInstance() for _ in range(1)])
conference_chair_D = Assets(description="A black office chair.", size=[0.65, 0.65, 1.05], placements=[AssetInstance() for _ in range(1)])
pen_A = Assets(description="A blue marker with a cup on the top of it.", size=[0.01, 0.14, 0.01], placements=[AssetInstance() for _ in range(1)])
conference_chair_E = Assets(description="A black office chair.", size=[0.65, 0.65, 1.05], placements=[AssetInstance() for _ in range(1)])
sideboard_credenda = Assets(description="A bunch of white cubby shelves.", size=[0.45, 1.80, 0.85], placements=[AssetInstance() for _ in range(1)])
meeting_side_table_A = Assets(description="A circular four legged light brown wooden table.", size=[0.65, 0.65, 0.72], placements=[AssetInstance() for _ in range(1)])
brochure_stand = Assets(description="A stand alone sign with a barcode and logo on one side.", size=[0.40, 0.45, 1.40], placements=[AssetInstance() for _ in range(1)])
pen_B = Assets(description="A blue marker with a cup on the top of it.", size=[0.01, 0.14, 0.01], placements=[AssetInstance() for _ in range(1)])
notepad_B = Assets(description="Paper scroll with lines of handwriting.", size=[0.30, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
lounge_armchair_B = Assets(description="This is an armchair with tall arms.", size=[0.85, 0.85, 0.95], placements=[AssetInstance() for _ in range(1)])
paper_ream_B = Assets(description="Paper scroll with lines of handwriting.", size=[0.30, 0.21, 0.05], placements=[AssetInstance() for _ in range(1)])
wall_clock = Assets(description="A black wall clock.", size=[0.05, 0.35, 0.35], placements=[AssetInstance() for _ in range(1)])
meeting_side_table_B = Assets(description="A circular four legged light brown wooden table.", size=[0.65, 0.65, 0.72], placements=[AssetInstance() for _ in range(1)])
notepad_C = Assets(description="A red notepad decorated with a slug in the lower corner.", size=[0.21, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
printer_stand = Assets(description="printer stand", size=[0.60, 0.90, 0.75], placements=[AssetInstance() for _ in range(1)])
paper_ream_C = Assets(description="Paper scroll with lines of handwriting.", size=[0.30, 0.21, 0.05], placements=[AssetInstance() for _ in range(1)])
meeting_side_table_C = Assets(description="A circular four legged light brown wooden table.", size=[0.65, 0.65, 0.72], placements=[AssetInstance() for _ in range(1)])
storage_box_A = Assets(description="A brown box with a cover that says patient files.", size=[0.43, 0.35, 0.27], placements=[AssetInstance() for _ in range(1)])
framed_poster_C = Assets(description="A blue painting in a black frame.", size=[0.04, 0.80, 1.10], placements=[AssetInstance() for _ in range(1)])
storage_cabinet_B = Assets(description="A grey upright filing cabinet.", size=[0.62, 0.50, 1.35], placements=[AssetInstance() for _ in range(1)])
framed_poster_D = Assets(description="A blue painting in a black frame.", size=[0.04, 0.80, 1.10], placements=[AssetInstance() for _ in range(1)])
paper_ream_D = Assets(description="Paper scroll with lines of handwriting.", size=[0.30, 0.21, 0.05], placements=[AssetInstance() for _ in range(1)])
presentation_console = Assets(description="presentation console", size=[0.60, 1.20, 1.05], placements=[AssetInstance() for _ in range(1)])
pen_C = Assets(description="A blue marker with a cup on the top of it.", size=[0.01, 0.14, 0.01], placements=[AssetInstance() for _ in range(1)])
conference_table = Assets(description="A long white table with two black spines.", size=[1.20, 3.20, 0.75], placements=[AssetInstance() for _ in range(1)])
wall_whiteboard = Assets(description="A green chalk board.", size=[0.05, 2.40, 1.20], placements=[AssetInstance() for _ in range(1)])
floor_planter_D = Assets(description="floor planter", size=[0.45, 0.45, 1.20], placements=[AssetInstance() for _ in range(1)])
storage_box_B = Assets(description="A brown box with a cover that says patient files.", size=[0.43, 0.35, 0.27], placements=[AssetInstance() for _ in range(1)])
conference_chair_F = Assets(description="A black office chair.", size=[0.65, 0.65, 1.05], placements=[AssetInstance() for _ in range(1)])
snack_bowl = Assets(description="A plastic barrel that's white black and brown with powder inside that's been cut in half.", size=[0.25, 0.25, 0.12], placements=[AssetInstance() for _ in range(1)])
coat_stand_B = Assets(description="A very tall candle holder.", size=[0.55, 0.55, 1.80], placements=[AssetInstance() for _ in range(1)])
magazine_C = Assets(description="Folded up newspaper with black print.", size=[0.22, 0.28, 0.01], placements=[AssetInstance() for _ in range(1)])

framed_poster_A[0].instance_id = 'framed_poster_A_0'
floor_planter_A[0].instance_id = 'floor_planter_A_0'
conference_chair_A[0].instance_id = 'conference_chair_A_0'
lounge_side_table[0].instance_id = 'lounge_side_table_0'
magazine_A[0].instance_id = 'magazine_A_0'
conference_chair_B[0].instance_id = 'conference_chair_B_0'
floor_planter_B[0].instance_id = 'floor_planter_B_0'
storage_cabinet_A[0].instance_id = 'storage_cabinet_A_0'
framed_poster_B[0].instance_id = 'framed_poster_B_0'
floor_planter_C[0].instance_id = 'floor_planter_C_0'
conference_chair_C[0].instance_id = 'conference_chair_C_0'
lounge_armchair_A[0].instance_id = 'lounge_armchair_A_0'
paper_ream_A[0].instance_id = 'paper_ream_A_0'
notepad_A[0].instance_id = 'notepad_A_0'
coat_stand_A[0].instance_id = 'coat_stand_A_0'
magazine_B[0].instance_id = 'magazine_B_0'
conference_chair_D[0].instance_id = 'conference_chair_D_0'
pen_A[0].instance_id = 'pen_A_0'
conference_chair_E[0].instance_id = 'conference_chair_E_0'
sideboard_credenda[0].instance_id = 'sideboard_credenda_0'
meeting_side_table_A[0].instance_id = 'meeting_side_table_A_0'
brochure_stand[0].instance_id = 'brochure_stand_0'
pen_B[0].instance_id = 'pen_B_0'
notepad_B[0].instance_id = 'notepad_B_0'
lounge_armchair_B[0].instance_id = 'lounge_armchair_B_0'
paper_ream_B[0].instance_id = 'paper_ream_B_0'
wall_clock[0].instance_id = 'wall_clock_0'
meeting_side_table_B[0].instance_id = 'meeting_side_table_B_0'
notepad_C[0].instance_id = 'notepad_C_0'
printer_stand[0].instance_id = 'printer_stand_0'
paper_ream_C[0].instance_id = 'paper_ream_C_0'
meeting_side_table_C[0].instance_id = 'meeting_side_table_C_0'
storage_box_A[0].instance_id = 'storage_box_A_0'
framed_poster_C[0].instance_id = 'framed_poster_C_0'
storage_cabinet_B[0].instance_id = 'storage_cabinet_B_0'
framed_poster_D[0].instance_id = 'framed_poster_D_0'
paper_ream_D[0].instance_id = 'paper_ream_D_0'
presentation_console[0].instance_id = 'presentation_console_0'
pen_C[0].instance_id = 'pen_C_0'
conference_table[0].instance_id = 'conference_table_0'
wall_whiteboard[0].instance_id = 'wall_whiteboard_0'
floor_planter_D[0].instance_id = 'floor_planter_D_0'
storage_box_B[0].instance_id = 'storage_box_B_0'
conference_chair_F[0].instance_id = 'conference_chair_F_0'
snack_bowl[0].instance_id = 'snack_bowl_0'
coat_stand_B[0].instance_id = 'coat_stand_B_0'
magazine_C[0].instance_id = 'magazine_C_0'
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

framed_poster_A[0].position = [6.979672195549469, 4.52608925291068, 0.55]
framed_poster_A[0].rotation = [0, 0, 0]
floor_planter_A[0].position = [2.2804736218854167, 8.260063596879357, 0.6]
floor_planter_A[0].rotation = [0, 0, 0]
conference_chair_A[0].position = [7.752116915957519, 8.948537743181031, 0.525]
conference_chair_A[0].rotation = [0, 0, 0]
lounge_side_table[0].position = [4.893358703662923, 8.486026043853807, 0.25]
lounge_side_table[0].rotation = [0, 0, 0]
magazine_A[0].position = [6.913897249401387, 10.732025046616785, 0.005]
magazine_A[0].rotation = [0, 0, 0]
conference_chair_B[0].position = [6.554582883460479, 1.0693855289165342, 0.525]
conference_chair_B[0].rotation = [0, 0, 0]
floor_planter_B[0].position = [7.801363744266133, 10.237949119727462, 0.6]
floor_planter_B[0].rotation = [0, 0, 0]
storage_cabinet_A[0].position = [6.546346846533571, 1.7733478452327414, 0.675]
storage_cabinet_A[0].rotation = [0, 0, 0]
framed_poster_B[0].position = [3.367122716804613, 1.322632272880062, 0.55]
framed_poster_B[0].rotation = [0, 0, 0]
floor_planter_C[0].position = [3.318255200388937, 5.5294356200052, 0.6]
floor_planter_C[0].rotation = [0, 0, 0]
conference_chair_C[0].position = [7.345212075306825, 4.973459481340053, 0.525]
conference_chair_C[0].rotation = [0, 0, 0]
lounge_armchair_A[0].position = [1.2571939026758443, 6.505059972684438, 0.475]
lounge_armchair_A[0].rotation = [0, 0, 0]
paper_ream_A[0].position = [5.126930536068799, 1.0828777593432983, 0.025]
paper_ream_A[0].rotation = [0, 0, 0]
notepad_A[0].position = [5.717299603277162, 10.878373219320201, 0.0075]
notepad_A[0].rotation = [0, 0, 0]
coat_stand_A[0].position = [4.145801114157013, 4.183179680160823, 0.9]
coat_stand_A[0].rotation = [0, 0, 0]
magazine_B[0].position = [2.612508213096315, 5.996253514961262, 0.005]
magazine_B[0].rotation = [0, 0, 0]
conference_chair_D[0].position = [1.8079318402897373, 8.411459158958296, 0.525]
conference_chair_D[0].rotation = [0, 0, 0]
pen_A[0].position = [6.202542758587287, 5.598557720135542, 0.0075]
pen_A[0].rotation = [0, 0, 0]
conference_chair_E[0].position = [7.753438487745901, 1.623312978856612, 0.525]
conference_chair_E[0].rotation = [0, 0, 0]
sideboard_credenda[0].position = [7.023115950333943, 10.395444279405023, 0.425]
sideboard_credenda[0].rotation = [0, 0, 0]
meeting_side_table_A[0].position = [3.3590808421611706, 2.62522039976123, 0.36]
meeting_side_table_A[0].rotation = [0, 0, 0]
brochure_stand[0].position = [7.89120153313608, 8.43413770071868, 0.7]
brochure_stand[0].rotation = [0, 0, 0]
pen_B[0].position = [3.3199446629420235, 8.014992045102982, 0.0075]
pen_B[0].rotation = [0, 0, 0]
notepad_B[0].position = [6.3983386339038235, 4.470554091780277, 0.0075]
notepad_B[0].rotation = [0, 0, 0]
lounge_armchair_B[0].position = [0.557638585693895, 6.370357455419064, 0.475]
lounge_armchair_B[0].rotation = [0, 0, 0]
paper_ream_B[0].position = [2.2493724814019878, 11.582324600480502, 0.025]
paper_ream_B[0].rotation = [0, 0, 0]
wall_clock[0].position = [5.742683299698852, 8.179008631023699, 0.175]
wall_clock[0].rotation = [0, 0, 0]
meeting_side_table_B[0].position = [3.559724941737567, 1.2836856297030859, 0.36]
meeting_side_table_B[0].rotation = [0, 0, 0]
notepad_C[0].position = [2.1940963452248434, 6.912563075555787, 0.0075]
notepad_C[0].rotation = [0, 0, 0]
printer_stand[0].position = [5.627298714830593, 2.1978886471981047, 0.375]
printer_stand[0].rotation = [0, 0, 0]
paper_ream_C[0].position = [5.7210744162050355, 4.647606194316463, 0.025]
paper_ream_C[0].rotation = [0, 0, 0]
meeting_side_table_C[0].position = [4.917093203945394, 8.857992494805087, 0.36]
meeting_side_table_C[0].rotation = [0, 0, 0]
storage_box_A[0].position = [6.999173867256012, 10.44174205620184, 0.135]
storage_box_A[0].rotation = [0, 0, 0]
framed_poster_C[0].position = [0.8782704037576146, 12.267028033238072, 0.55]
framed_poster_C[0].rotation = [0, 0, 0]
storage_cabinet_B[0].position = [3.731428018341237, 6.094033464610768, 0.675]
storage_cabinet_B[0].rotation = [0, 0, 0]
framed_poster_D[0].position = [1.9362245271765266, 10.80611596722569, 0.55]
framed_poster_D[0].rotation = [0, 0, 0]
paper_ream_D[0].position = [3.0169830553746646, 1.7529190185737513, 0.025]
paper_ream_D[0].rotation = [0, 0, 0]
presentation_console[0].position = [7.239843867057286, 6.153330703191369, 0.525]
presentation_console[0].rotation = [0, 0, 0]
pen_C[0].position = [3.8014441722955308, 3.8993180581465916, 0.0075]
pen_C[0].rotation = [0, 0, 0]
conference_table[0].position = [5.685183094699021, 11.037255251924504, 0.375]
conference_table[0].rotation = [0, 0, 0]
wall_whiteboard[0].position = [4.611873313369179, 6.3625273876392585, 0.6]
wall_whiteboard[0].rotation = [0, 0, 0]
floor_planter_D[0].position = [3.5919950273664476, 4.871236516125217, 0.6]
floor_planter_D[0].rotation = [0, 0, 0]
storage_box_B[0].position = [4.511302040699028, 3.557599767011892, 0.135]
storage_box_B[0].rotation = [0, 0, 0]
conference_chair_F[0].position = [5.42221542919966, 8.64084994328302, 0.525]
conference_chair_F[0].rotation = [0, 0, 0]
snack_bowl[0].position = [7.699593870067873, 0.5678079769648989, 0.06]
snack_bowl[0].rotation = [0, 0, 0]
coat_stand_B[0].position = [3.8369392309276176, 10.507402469275165, 0.9]
coat_stand_B[0].rotation = [0, 0, 0]
magazine_C[0].position = [4.936526932706175, 7.790802419010221, 0.005]
magazine_C[0].rotation = [0, 0, 0]
framed_poster_A[0].position = [6.979672195549469, 4.52608925291068, 0.55]
framed_poster_A[0].rotation = [0, 0, 0]
floor_planter_A[0].position = [2.2804736218854167, 8.260063596879357, 0.6]
floor_planter_A[0].rotation = [0, 0, 0]
conference_chair_A[0].position = [7.752116915957519, 8.948537743181031, 0.525]
conference_chair_A[0].rotation = [0, 0, 0]
lounge_side_table[0].position = [4.893358703662923, 8.486026043853807, 0.25]
lounge_side_table[0].rotation = [0, 0, 0]
magazine_A[0].position = [6.913897249401387, 10.732025046616785, 0.005]
magazine_A[0].rotation = [0, 0, 0]
conference_chair_B[0].position = [6.554582883460479, 1.0693855289165342, 0.525]
conference_chair_B[0].rotation = [0, 0, 0]
floor_planter_B[0].position = [7.801363744266133, 10.237949119727462, 0.6]
floor_planter_B[0].rotation = [0, 0, 0]
storage_cabinet_A[0].position = [6.546346846533571, 1.7733478452327414, 0.675]
storage_cabinet_A[0].rotation = [0, 0, 0]
framed_poster_B[0].position = [3.367122716804613, 1.322632272880062, 0.55]
framed_poster_B[0].rotation = [0, 0, 0]
floor_planter_C[0].position = [3.318255200388937, 5.5294356200052, 0.6]
floor_planter_C[0].rotation = [0, 0, 0]
conference_chair_C[0].position = [7.345212075306825, 4.973459481340053, 0.525]
conference_chair_C[0].rotation = [0, 0, 0]
lounge_armchair_A[0].position = [1.2571939026758443, 6.505059972684438, 0.475]
lounge_armchair_A[0].rotation = [0, 0, 0]
paper_ream_A[0].position = [5.126930536068799, 1.0828777593432983, 0.025]
paper_ream_A[0].rotation = [0, 0, 0]
notepad_A[0].position = [5.717299603277162, 10.878373219320201, 0.0075]
notepad_A[0].rotation = [0, 0, 0]
coat_stand_A[0].position = [4.145801114157013, 4.183179680160823, 0.9]
coat_stand_A[0].rotation = [0, 0, 0]
magazine_B[0].position = [2.612508213096315, 5.996253514961262, 0.005]
magazine_B[0].rotation = [0, 0, 0]
conference_chair_D[0].position = [1.8079318402897373, 8.411459158958296, 0.525]
conference_chair_D[0].rotation = [0, 0, 0]
pen_A[0].position = [6.202542758587287, 5.598557720135542, 0.0075]
pen_A[0].rotation = [0, 0, 0]
conference_chair_E[0].position = [7.753438487745901, 1.623312978856612, 0.525]
conference_chair_E[0].rotation = [0, 0, 0]
sideboard_credenda[0].position = [7.023115950333943, 10.395444279405023, 0.425]
sideboard_credenda[0].rotation = [0, 0, 0]
meeting_side_table_A[0].position = [3.3590808421611706, 2.62522039976123, 0.36]
meeting_side_table_A[0].rotation = [0, 0, 0]
brochure_stand[0].position = [7.89120153313608, 8.43413770071868, 0.7]
brochure_stand[0].rotation = [0, 0, 0]
pen_B[0].position = [3.3199446629420235, 8.014992045102982, 0.0075]
pen_B[0].rotation = [0, 0, 0]
notepad_B[0].position = [6.3983386339038235, 4.470554091780277, 0.0075]
notepad_B[0].rotation = [0, 0, 0]
lounge_armchair_B[0].position = [0.557638585693895, 6.370357455419064, 0.475]
lounge_armchair_B[0].rotation = [0, 0, 0]
paper_ream_B[0].position = [2.2493724814019878, 11.582324600480502, 0.025]
paper_ream_B[0].rotation = [0, 0, 0]
wall_clock[0].position = [5.742683299698852, 8.179008631023699, 0.175]
wall_clock[0].rotation = [0, 0, 0]
meeting_side_table_B[0].position = [3.559724941737567, 1.2836856297030859, 0.36]
meeting_side_table_B[0].rotation = [0, 0, 0]
notepad_C[0].position = [2.1940963452248434, 6.912563075555787, 0.0075]
notepad_C[0].rotation = [0, 0, 0]
printer_stand[0].position = [5.627298714830593, 2.1978886471981047, 0.375]
printer_stand[0].rotation = [0, 0, 0]
paper_ream_C[0].position = [5.7210744162050355, 4.647606194316463, 0.025]
paper_ream_C[0].rotation = [0, 0, 0]
meeting_side_table_C[0].position = [4.917093203945394, 8.857992494805087, 0.36]
meeting_side_table_C[0].rotation = [0, 0, 0]
storage_box_A[0].position = [6.999173867256012, 10.44174205620184, 0.135]
storage_box_A[0].rotation = [0, 0, 0]
framed_poster_C[0].position = [0.8782704037576146, 12.267028033238072, 0.55]
framed_poster_C[0].rotation = [0, 0, 0]
storage_cabinet_B[0].position = [3.731428018341237, 6.094033464610768, 0.675]
storage_cabinet_B[0].rotation = [0, 0, 0]
framed_poster_D[0].position = [1.9362245271765266, 10.80611596722569, 0.55]
framed_poster_D[0].rotation = [0, 0, 0]
paper_ream_D[0].position = [3.0169830553746646, 1.7529190185737513, 0.025]
paper_ream_D[0].rotation = [0, 0, 0]
presentation_console[0].position = [7.239843867057286, 6.153330703191369, 0.525]
presentation_console[0].rotation = [0, 0, 0]
pen_C[0].position = [3.8014441722955308, 3.8993180581465916, 0.0075]
pen_C[0].rotation = [0, 0, 0]
conference_table[0].position = [5.685183094699021, 11.037255251924504, 0.375]
conference_table[0].rotation = [0, 0, 0]
wall_whiteboard[0].position = [4.611873313369179, 6.3625273876392585, 0.6]
wall_whiteboard[0].rotation = [0, 0, 0]
floor_planter_D[0].position = [3.5919950273664476, 4.871236516125217, 0.6]
floor_planter_D[0].rotation = [0, 0, 0]
storage_box_B[0].position = [4.511302040699028, 3.557599767011892, 0.135]
storage_box_B[0].rotation = [0, 0, 0]
conference_chair_F[0].position = [5.42221542919966, 8.64084994328302, 0.525]
conference_chair_F[0].rotation = [0, 0, 0]
snack_bowl[0].position = [7.699593870067873, 0.5678079769648989, 0.06]
snack_bowl[0].rotation = [0, 0, 0]
coat_stand_B[0].position = [3.8369392309276176, 10.507402469275165, 0.9]
coat_stand_B[0].rotation = [0, 0, 0]
magazine_C[0].position = [4.936526932706175, 7.790802419010221, 0.005]
magazine_C[0].rotation = [0, 0, 0]

solver.constraints = []

# The main meeting area occupies the broad central part of the room.
# The entrance at (0, 11.88), its approach, and the window wall remain clear.
# Coordinates below are bounding-box centers; all rotations are in radians.
floor_layout = [
    (conference_table,       [4.60, 7.00, 0.375], 0),
    (conference_chair_A,     [3.45, 5.90, 0.525], 0),
    (conference_chair_B,     [3.45, 7.00, 0.525], 0),
    (conference_chair_C,     [3.45, 8.10, 0.525], 0),
    (conference_chair_D,     [5.75, 5.90, 0.525], 180),
    (conference_chair_F,     [5.75, 7.00, 0.525], 180),
    (conference_chair_E,     [5.75, 8.10, 0.525], 180),

    # Presentation equipment is beyond the head of the table.
    (presentation_console,  [4.60, 10.70, 0.525], -90),

    # Lounge in the southern bay, with a shared table between the seats.
    (lounge_armchair_A,      [4.85, 2.15, 0.475], 0),
    (lounge_armchair_B,      [7.05, 2.15, 0.475], 180),
    (lounge_side_table,      [5.95, 2.15, 0.250], 0),

    # Auxiliary tables leave generous circulation around the meeting area.
    (meeting_side_table_A,   [3.10, 4.25, 0.360], 0),
    (meeting_side_table_B,   [6.90, 4.25, 0.360], 180),
    (meeting_side_table_C,   [6.90, 10.45, 0.360], 180),

    # Storage occupies solid walls, rather than blocking windows.
    (storage_cabinet_A,      [2.31, 2.00, 0.675], 0),
    (storage_cabinet_B,      [2.31, 3.10, 0.675], 0),
    (sideboard_credenda,     [0.225, 7.25, 0.425], 0),
    (printer_stand,         [0.30, 9.70, 0.375], 0),

    (brochure_stand,         [1.80, 10.45, 0.700], 90),
    (coat_stand_A,           [2.45, 11.30, 0.900], 0),
    # Chair E faces this stand directly across the meeting area.
    (coat_stand_B,           [1.80, 8.10, 0.900], 0),

    (floor_planter_A,        [4.40, 0.45, 0.600], 0),
    (floor_planter_B,        [7.45, 0.45, 0.600], 0),
    (floor_planter_C,        [0.50, 5.55, 0.600], 0),
    (floor_planter_D,        [7.40, 11.45, 0.600], 0),
]

# Fix the planned furniture centers before adding secondary relationships.
# Matching fixed reference rotations provide an orientation constraint for
# every floor asset, including rotationally symmetric accessories.
for asset_group, center_xyz, yaw_degrees in floor_layout:
    asset_group[0].position = center_xyz
    asset_group[0].rotation = [0, 0, radians(yaw_degrees)]
    fixed_reference = AssetInstance(
        position=list(center_xyz),
        rotation=[0, 0, radians(yaw_degrees)],
    )
    solver.distance_constraint(
        asset_group[0], fixed_reference, 0, 0, weight=10
    )
    solver.align_with(asset_group[0], fixed_reference)

# Semantic constraints for the conference seating.
for chair_group in (
    conference_chair_A, conference_chair_B, conference_chair_C,
    conference_chair_D, conference_chair_E, conference_chair_F,
):
    solver.distance_constraint(
        chair_group[0], conference_table[0], 1.10, 1.65, weight=10
    )

for chair_group in (
    conference_chair_A, conference_chair_B, conference_chair_C,
    conference_chair_D, conference_chair_F,
):
    solver.point_towards(
        chair_group[0],
        AssetInstance(position=[4.60, chair_group[0].position[1], 0.525]),
    )

# o0043 (F) is the midpoint between o0016 (D) and o0018 (E).
# These distances and the fixed centers preserve their ordered straight row.
solver.distance_constraint(
    conference_chair_F[0], conference_chair_D[0], 1.10, 1.10, weight=10
)
solver.distance_constraint(
    conference_chair_F[0], conference_chair_E[0], 1.10, 1.10, weight=10
)
solver.distance_constraint(
    conference_chair_D[0], conference_chair_E[0], 2.20, 2.20, weight=10
)
solver.point_towards(conference_chair_E[0], coat_stand_B[0])

solver.point_towards(lounge_armchair_A[0], lounge_side_table[0])
solver.point_towards(lounge_armchair_B[0], lounge_side_table[0])
for seat_group in (lounge_armchair_A, lounge_armchair_B):
    solver.distance_constraint(
        seat_group[0], lounge_side_table[0], 1.10, 1.15, weight=10
    )

solver.point_towards(presentation_console[0], conference_table[0])

# Flush wall placements on solid sections of the boundary.
for asset_group, wall_index in (
    (storage_cabinet_A, 1),
    (storage_cabinet_B, 1),
    (sideboard_credenda, 9),
    (printer_stand, 9),
):
    solver.against_wall(asset_group[0], walls[wall_index])

# Wall-mounted objects are elevated explicitly, not placed on the floor.
# The whiteboard faces south toward the conference table.
wall_layout = [
    (wall_whiteboard, [4.60, 11.975, 1.75], -90, 6),
    (wall_clock,     [6.50, 11.975, 2.30], -90, 6),
    (framed_poster_A, [2.02, 2.00, 2.10],    0, 1),
    (framed_poster_B, [0.02, 6.00, 1.85],    0, 9),
    (framed_poster_C, [0.02, 8.85, 1.85],    0, 9),
    (framed_poster_D, [5.70, 0.02, 1.85],   90, 4),
]
for asset_group, center_xyz, yaw_degrees, wall_index in wall_layout:
    asset_group[0].position = center_xyz
    asset_group[0].rotation = [0, 0, radians(yaw_degrees)]
    fixed_reference = AssetInstance(
        position=list(center_xyz),
        rotation=[0, 0, radians(yaw_degrees)],
    )
    solver.distance_constraint(
        asset_group[0], fixed_reference, 0, 0, weight=10
    )
    solver.against_wall(asset_group[0], walls[wall_index])
    solver.align_with(asset_group[0], fixed_reference)

# Small objects are distributed on usable surfaces with nonoverlapping
# footprints. All four paper reams fit in a single row on the printer stand,
# including o0025 (paper_ream_B).
surface_layout = [
    (paper_ream_A, printer_stand, [0.30, 9.38, 0.775], 0),
    (paper_ream_B, printer_stand, [0.30, 9.60, 0.775], 0),
    (paper_ream_C, printer_stand, [0.30, 9.82, 0.775], 0),
    (paper_ream_D, printer_stand, [0.30, 10.04, 0.775], 0),

    (storage_box_A, storage_cabinet_A, [2.31, 2.00, 1.485], 0),
    (storage_box_B, storage_cabinet_B, [2.31, 3.10, 1.485], 0),

    (notepad_A, conference_table, [4.22, 5.95, 0.755], 0),
    (pen_A,     conference_table, [4.39, 5.95, 0.755], 0),
    (notepad_B, conference_table, [4.22, 7.00, 0.755], 0),
    (pen_B,     conference_table, [4.43, 7.00, 0.755], 0),
    (notepad_C, conference_table, [4.95, 8.05, 0.755], 0),
    (pen_C,     conference_table, [4.78, 8.05, 0.755], 0),

    (magazine_A, lounge_side_table,    [5.95, 2.15, 0.505], 0),
    (magazine_B, meeting_side_table_A, [3.10, 4.25, 0.725], 0),
    (magazine_C, meeting_side_table_C, [6.90, 10.45, 0.725], 0),
    (snack_bowl, meeting_side_table_B, [6.90, 4.25, 0.780], 0),
]

for asset_group, support_group, center_xyz, yaw_degrees in surface_layout:
    asset_group[0].position = center_xyz
    asset_group[0].rotation = [0, 0, radians(yaw_degrees)]
    # Vertical support is the highest-priority relationship.
    solver.on_top_of(asset_group[0], support_group[0])
    solver.distance_constraint(
        asset_group[0],
        AssetInstance(position=list(center_xyz)),
        0, 0, weight=10,
    )
    solver.align_with(asset_group[0], support_group[0], angle=yaw_degrees)

solver.constraints = []
meeting_side_table_A[0].position = [3.0999999046325684, 4.25, 0.36000001430511475]
meeting_side_table_A[0].rotation = [0, 0, 0.0157079639172164]
meeting_side_table_A[0].optimize = 2
coat_stand_B[0].position = [1.7999999523162842, 8.100000381469727, 0.8999999761581421]
coat_stand_B[0].rotation = [0, 0, 0.01256637125682779]
coat_stand_B[0].optimize = 2
storage_box_B[0].position = [2.309999942779541, 3.0999999046325684, 1.4850000143051147]
storage_box_B[0].rotation = [0, 0, 0.01513203089124573]
storage_box_B[0].optimize = 2
storage_box_A[0].position = [2.309999942779541, 2.0, 1.4850000143051147]
storage_box_A[0].rotation = [0, 0, 0.01513203089124573]
storage_box_A[0].optimize = 2
wall_clock[0].position = [6.5, 11.977560997009277, 0.17499999701976776]
wall_clock[0].rotation = [0, 0, -1.5697591320237838]
wall_clock[0].optimize = 2
conference_chair_D[0].position = [5.75, 5.900000095367432, 0.5249999761581421]
conference_chair_D[0].rotation = [0, 0, -3.1196015053037707]
conference_chair_D[0].optimize = 2
meeting_side_table_C[0].position = [6.900000095367432, 10.449999809265137, 0.36000001430511475]
meeting_side_table_C[0].rotation = [0, 0, -3.125884689672577]
meeting_side_table_C[0].optimize = 2
framed_poster_C[0].position = [0.017607148736715317, 8.850000381469727, 0.550000011920929]
framed_poster_C[0].rotation = [0, 0, 0.0010371684209472215]
framed_poster_C[0].optimize = 2
conference_chair_A[0].position = [3.450000047683716, 5.900000095367432, 0.5249999761581421]
conference_chair_A[0].rotation = [0, 0, 0.0157079639172164]
conference_chair_A[0].optimize = 2
magazine_B[0].position = [3.0999999046325684, 4.25, 0.7250000238418579]
magazine_B[0].rotation = [0, 0, 0.016182787006743093]
magazine_B[0].optimize = 2
paper_ream_A[0].position = [0.30000001192092896, 9.380000114440918, 0.7749999761581421]
paper_ream_A[0].rotation = [0, 0, -0.012347783182111823]
paper_ream_A[0].optimize = 2
pen_B[0].position = [4.429999828338623, 7.0, 0.7549999952316284]
pen_B[0].rotation = [0, 0, 0.062192444014355946]
pen_B[0].optimize = 2
notepad_B[0].position = [4.21999979019165, 7.0, 0.7549999952316284]
notepad_B[0].rotation = [0, 0, 0.062192444014355946]
notepad_B[0].optimize = 2
meeting_side_table_B[0].position = [6.900000095367432, 4.25, 0.36000001430511475]
meeting_side_table_B[0].rotation = [0, 0, -3.125884689672577]
meeting_side_table_B[0].optimize = 2
framed_poster_B[0].position = [0.017607148736715317, 6.0, 0.550000011920929]
framed_poster_B[0].rotation = [0, 0, 0.0010371684209472215]
framed_poster_B[0].optimize = 2
conference_table[0].position = [4.599999904632568, 7.0, 0.375]
conference_table[0].rotation = [0, 0, 0.06911503821575936]
conference_table[0].optimize = 2
magazine_C[0].position = [6.900000095367432, 10.449999809265137, 0.7250000238418579]
magazine_C[0].rotation = [0, 0, -0.22416567427990813]
magazine_C[0].optimize = 2
storage_cabinet_A[0].position = [2.3115074634552, 2.0, 0.675000011920929]
storage_cabinet_A[0].rotation = [0, 0, -0.004221099650570873]
storage_cabinet_A[0].optimize = 2
wall_whiteboard[0].position = [4.599999904632568, 11.975666999816895, 0.6000000238418579]
wall_whiteboard[0].rotation = [0, 0, -1.5697603390916008]
wall_whiteboard[0].optimize = 2
floor_planter_A[0].position = [4.400000095367432, 0.44999998807907104, 0.6000000238418579]
floor_planter_A[0].rotation = [0, 0, 0.00942477746072377]
floor_planter_A[0].optimize = 2
conference_chair_E[0].position = [5.75, 8.100000381469727, 0.5249999761581421]
conference_chair_E[0].rotation = [0, 0, -3.1196015053037707]
conference_chair_E[0].optimize = 2
presentation_console[0].position = [4.599999904632568, 10.699999809265137, 0.5249999761581421]
presentation_console[0].rotation = [0, 0, -1.5582299555380688]
presentation_console[0].optimize = 2
conference_chair_F[0].position = [5.75, 7.0, 0.5249999761581421]
conference_chair_F[0].rotation = [0, 0, -3.1196015053037707]
conference_chair_F[0].optimize = 2
framed_poster_A[0].position = [2.017627000808716, 2.0, 0.550000011920929]
framed_poster_A[0].rotation = [0, 0, 0.0010371541426162027]
framed_poster_A[0].optimize = 2
paper_ream_C[0].position = [0.30000001192092896, 9.819999694824219, 0.7749999761581421]
paper_ream_C[0].rotation = [0, 0, -0.012347783182111823]
paper_ream_C[0].optimize = 2
paper_ream_D[0].position = [0.30000001192092896, 10.039999961853027, 0.7749999761581421]
paper_ream_D[0].rotation = [0, 0, -0.012347783182111823]
paper_ream_D[0].optimize = 2
floor_planter_D[0].position = [7.400000095367432, 11.449999809265137, 0.6000000238418579]
floor_planter_D[0].rotation = [0, 0, 0.00942477746072377]
floor_planter_D[0].optimize = 2
paper_ream_B[0].position = [0.30000001192092896, 9.600000381469727, 0.7749999761581421]
paper_ream_B[0].rotation = [0, 0, -0.012347783182111823]
paper_ream_B[0].optimize = 2
coat_stand_A[0].position = [2.450000047683716, 11.300000190734863, 0.8999999761581421]
coat_stand_A[0].rotation = [0, 0, 0.00942477746072377]
coat_stand_A[0].optimize = 2
snack_bowl[0].position = [6.900000095367432, 4.25, 0.7800000309944153]
snack_bowl[0].rotation = [0, 0, -0.22416567427990813]
snack_bowl[0].optimize = 2
printer_stand[0].position = [0.2970917820930481, 9.699999809265137, 0.375]
printer_stand[0].rotation = [0, 0, 0.008495496738292987]
printer_stand[0].optimize = 2
floor_planter_C[0].position = [0.5, 5.550000190734863, 0.6000000238418579]
floor_planter_C[0].rotation = [0, 0, 0.00942477746072377]
floor_planter_C[0].optimize = 2
lounge_armchair_A[0].position = [4.805225849151611, 2.1500000953674316, 0.4749999940395355]
lounge_armchair_A[0].rotation = [0, 0, 0.0157079639172164]
lounge_armchair_A[0].optimize = 2
lounge_armchair_B[0].position = [7.050000190734863, 2.1500000953674316, 0.4749999940395355]
lounge_armchair_B[0].rotation = [0, 0, -3.125884689672577]
lounge_armchair_B[0].optimize = 2
conference_chair_C[0].position = [3.450000047683716, 8.100000381469727, 0.5249999761581421]
conference_chair_C[0].rotation = [0, 0, 0.0157079639172164]
conference_chair_C[0].optimize = 2
storage_cabinet_B[0].position = [2.3115074634552, 3.0999999046325684, 0.675000011920929]
storage_cabinet_B[0].rotation = [0, 0, -0.004221099650570873]
storage_cabinet_B[0].optimize = 2
sideboard_credenda[0].position = [0.22783783078193665, 7.25, 0.42500001192092896]
sideboard_credenda[0].rotation = [0, 0, 0.001029658185357485]
sideboard_credenda[0].optimize = 2
lounge_side_table[0].position = [5.949999809265137, 2.1500000953674316, 0.25]
lounge_side_table[0].rotation = [0, 0, 0.02827433441159227]
lounge_side_table[0].optimize = 2
floor_planter_B[0].position = [7.449999809265137, 0.44999998807907104, 0.6000000238418579]
floor_planter_B[0].rotation = [0, 0, 0.00942477746072377]
floor_planter_B[0].optimize = 2
framed_poster_D[0].position = [5.699999809265137, 0.017607150599360466, 0.550000011920929]
framed_poster_D[0].rotation = [0, 0, 1.571833495215844]
framed_poster_D[0].optimize = 2
notepad_C[0].position = [4.949999809265137, 8.050000190734863, 0.7549999952316284]
notepad_C[0].rotation = [0, 0, 0.062192444014355946]
notepad_C[0].optimize = 2
brochure_stand[0].position = [1.7999999523162842, 10.449999809265137, 0.699999988079071]
brochure_stand[0].rotation = [0, 0, 1.5802211042556205]
brochure_stand[0].optimize = 2
pen_C[0].position = [4.78000020980835, 8.050000190734863, 0.7549999952316284]
pen_C[0].rotation = [0, 0, 0.062192444014355946]
pen_C[0].optimize = 2
notepad_A[0].position = [4.21999979019165, 5.949999809265137, 0.7549999952316284]
notepad_A[0].rotation = [0, 0, 0.062192444014355946]
notepad_A[0].optimize = 2
magazine_A[0].position = [5.949999809265137, 2.1500000953674316, 0.5049999952316284]
magazine_A[0].rotation = [0, 0, 0.02921999455890071]
magazine_A[0].optimize = 2
conference_chair_B[0].position = [3.450000047683716, 7.0, 0.5249999761581421]
conference_chair_B[0].rotation = [0, 0, 0.0157079639172164]
conference_chair_B[0].optimize = 2
pen_A[0].position = [4.389999866485596, 5.949999809265137, 0.7549999952316284]
pen_A[0].rotation = [0, 0, 0.062192444014355946]
pen_A[0].optimize = 2

