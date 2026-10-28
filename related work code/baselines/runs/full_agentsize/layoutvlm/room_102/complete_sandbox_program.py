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
framed_poster_A = Assets(description="A blue painting in a black frame.", size=[0.04, 0.80, 0.60], placements=[AssetInstance() for _ in range(1)])
floor_planter_A = Assets(description="floor planter", size=[0.45, 0.45, 0.90], placements=[AssetInstance() for _ in range(1)])
conference_chair_A = Assets(description="A black office chair.", size=[0.65, 0.65, 1.05], placements=[AssetInstance() for _ in range(1)])
lounge_side_table = Assets(description="A small square table made of wood.", size=[0.55, 0.55, 0.50], placements=[AssetInstance() for _ in range(1)])
magazine_A = Assets(description="Folded up newspaper with black print.", size=[0.24, 0.32, 0.01], placements=[AssetInstance() for _ in range(1)])
conference_chair_B = Assets(description="A black office chair.", size=[0.65, 0.65, 1.05], placements=[AssetInstance() for _ in range(1)])
floor_planter_B = Assets(description="floor planter", size=[0.45, 0.45, 0.90], placements=[AssetInstance() for _ in range(1)])
storage_cabinet_A = Assets(description="A grey upright filing cabinet.", size=[0.60, 0.50, 1.35], placements=[AssetInstance() for _ in range(1)])
framed_poster_B = Assets(description="A blue painting in a black frame.", size=[0.04, 0.80, 0.60], placements=[AssetInstance() for _ in range(1)])
floor_planter_C = Assets(description="floor planter", size=[0.45, 0.45, 0.90], placements=[AssetInstance() for _ in range(1)])
conference_chair_C = Assets(description="A black office chair.", size=[0.65, 0.65, 1.05], placements=[AssetInstance() for _ in range(1)])
lounge_armchair_A = Assets(description="This is an armchair with tall arms.", size=[0.85, 0.85, 0.95], placements=[AssetInstance() for _ in range(1)])
paper_ream_A = Assets(description="Paper scroll with lines of handwriting.", size=[0.21, 0.30, 0.05], placements=[AssetInstance() for _ in range(1)])
notepad_A = Assets(description="A red notepad decorated with a slug in the lower corner.", size=[0.15, 0.21, 0.02], placements=[AssetInstance() for _ in range(1)])
coat_stand_A = Assets(description="A very tall candle holder.", size=[0.45, 0.45, 1.80], placements=[AssetInstance() for _ in range(1)])
magazine_B = Assets(description="Folded up newspaper with black print.", size=[0.24, 0.32, 0.01], placements=[AssetInstance() for _ in range(1)])
conference_chair_D = Assets(description="A black office chair.", size=[0.65, 0.65, 1.05], placements=[AssetInstance() for _ in range(1)])
pen_A = Assets(description="A blue marker with a cup on the top of it.", size=[0.02, 0.02, 0.14], placements=[AssetInstance() for _ in range(1)])
conference_chair_E = Assets(description="A black office chair.", size=[0.65, 0.65, 1.05], placements=[AssetInstance() for _ in range(1)])
sideboard_credenda = Assets(description="A bunch of white cubby shelves.", size=[0.45, 1.80, 0.90], placements=[AssetInstance() for _ in range(1)])
meeting_side_table_A = Assets(description="A circular four legged light brown wooden table.", size=[0.65, 0.65, 0.55], placements=[AssetInstance() for _ in range(1)])
brochure_stand = Assets(description="A stand alone sign with a barcode and logo on one side.", size=[0.45, 0.65, 1.50], placements=[AssetInstance() for _ in range(1)])
pen_B = Assets(description="A blue marker with a cup on the top of it.", size=[0.02, 0.02, 0.14], placements=[AssetInstance() for _ in range(1)])
notepad_B = Assets(description="Paper scroll with lines of handwriting.", size=[0.21, 0.30, 0.02], placements=[AssetInstance() for _ in range(1)])
lounge_armchair_B = Assets(description="This is an armchair with tall arms.", size=[0.85, 0.85, 0.95], placements=[AssetInstance() for _ in range(1)])
paper_ream_B = Assets(description="Paper scroll with lines of handwriting.", size=[0.21, 0.30, 0.05], placements=[AssetInstance() for _ in range(1)])
wall_clock = Assets(description="A black wall clock.", size=[0.05, 0.35, 0.35], placements=[AssetInstance() for _ in range(1)])
meeting_side_table_B = Assets(description="A circular four legged light brown wooden table.", size=[0.65, 0.65, 0.55], placements=[AssetInstance() for _ in range(1)])
notepad_C = Assets(description="A red notepad decorated with a slug in the lower corner.", size=[0.15, 0.21, 0.02], placements=[AssetInstance() for _ in range(1)])
printer_stand = Assets(description="printer stand", size=[0.60, 0.80, 0.75], placements=[AssetInstance() for _ in range(1)])
paper_ream_C = Assets(description="Paper scroll with lines of handwriting.", size=[0.21, 0.30, 0.05], placements=[AssetInstance() for _ in range(1)])
meeting_side_table_C = Assets(description="A circular four legged light brown wooden table.", size=[0.65, 0.65, 0.55], placements=[AssetInstance() for _ in range(1)])
storage_box_A = Assets(description="A brown box with a cover that says patient files.", size=[0.32, 0.40, 0.28], placements=[AssetInstance() for _ in range(1)])
framed_poster_C = Assets(description="A blue painting in a black frame.", size=[0.04, 0.80, 0.60], placements=[AssetInstance() for _ in range(1)])
storage_cabinet_B = Assets(description="A grey upright filing cabinet.", size=[0.60, 0.50, 1.35], placements=[AssetInstance() for _ in range(1)])
framed_poster_D = Assets(description="A blue painting in a black frame.", size=[0.04, 0.80, 0.60], placements=[AssetInstance() for _ in range(1)])
paper_ream_D = Assets(description="Paper scroll with lines of handwriting.", size=[0.21, 0.30, 0.05], placements=[AssetInstance() for _ in range(1)])
presentation_console = Assets(description="presentation console", size=[0.60, 1.20, 1.00], placements=[AssetInstance() for _ in range(1)])
pen_C = Assets(description="A blue marker with a cup on the top of it.", size=[0.02, 0.02, 0.14], placements=[AssetInstance() for _ in range(1)])
conference_table = Assets(description="A long white table with two black spines.", size=[1.50, 4.80, 0.75], placements=[AssetInstance() for _ in range(1)])
wall_whiteboard = Assets(description="A green chalk board.", size=[0.06, 2.40, 1.20], placements=[AssetInstance() for _ in range(1)])
floor_planter_D = Assets(description="floor planter", size=[0.45, 0.45, 0.90], placements=[AssetInstance() for _ in range(1)])
storage_box_B = Assets(description="A brown box with a cover that says patient files.", size=[0.32, 0.40, 0.28], placements=[AssetInstance() for _ in range(1)])
conference_chair_F = Assets(description="A black office chair.", size=[0.65, 0.65, 1.05], placements=[AssetInstance() for _ in range(1)])
snack_bowl = Assets(description="A plastic barrel that's white black and brown with powder inside that's been cut in half.", size=[0.28, 0.28, 0.12], placements=[AssetInstance() for _ in range(1)])
coat_stand_B = Assets(description="A very tall candle holder.", size=[0.45, 0.45, 1.80], placements=[AssetInstance() for _ in range(1)])
magazine_C = Assets(description="Folded up newspaper with black print.", size=[0.24, 0.32, 0.01], placements=[AssetInstance() for _ in range(1)])

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

framed_poster_A[0].position = [6.7528499240016595, 4.98127171944546, 0.3]
framed_poster_A[0].rotation = [0, 0, 0]
floor_planter_A[0].position = [0.6283761493604523, 6.913157463233122, 0.45]
floor_planter_A[0].rotation = [0, 0, 0]
conference_chair_A[0].position = [5.516279461927399, 10.77411515143984, 0.525]
conference_chair_A[0].rotation = [0, 0, 0]
lounge_side_table[0].position = [5.391274592968432, 7.81280816621072, 0.25]
lounge_side_table[0].rotation = [0, 0, 0]
magazine_A[0].position = [6.005811176901463, 10.4057071712739, 0.005]
magazine_A[0].rotation = [0, 0, 0]
conference_chair_B[0].position = [4.076965232230782, 1.9827710647717063, 0.525]
conference_chair_B[0].rotation = [0, 0, 0]
floor_planter_B[0].position = [1.9858513100943727, 6.986328982850133, 0.45]
floor_planter_B[0].rotation = [0, 0, 0]
storage_cabinet_A[0].position = [7.910110748374247, 5.566217136500019, 0.675]
storage_cabinet_A[0].rotation = [0, 0, 0]
framed_poster_B[0].position = [2.8248085789957873, 8.2943753676851, 0.3]
framed_poster_B[0].rotation = [0, 0, 0]
floor_planter_C[0].position = [4.478536933369909, 5.680140019317829, 0.45]
floor_planter_C[0].rotation = [0, 0, 0]
conference_chair_C[0].position = [2.930533723359889, 9.846631398755392, 0.525]
conference_chair_C[0].rotation = [0, 0, 0]
lounge_armchair_A[0].position = [7.53645313625342, 7.778288696001732, 0.475]
lounge_armchair_A[0].rotation = [0, 0, 0]
paper_ream_A[0].position = [7.074017834011377, 10.866367932448796, 0.025]
paper_ream_A[0].rotation = [0, 0, 0]
notepad_A[0].position = [4.623969362358542, 0.008394407599798148, 0.01]
notepad_A[0].rotation = [0, 0, 0]
coat_stand_A[0].position = [2.829210308147828, 5.104460645278712, 0.9]
coat_stand_A[0].rotation = [0, 0, 0]
magazine_B[0].position = [2.465640485302555, 3.3270487388692045, 0.005]
magazine_B[0].rotation = [0, 0, 0]
conference_chair_D[0].position = [4.9543342295267925, 1.795948847668296, 0.525]
conference_chair_D[0].rotation = [0, 0, 0]
pen_A[0].position = [1.7415955088416082, 7.591079407170584, 0.07]
pen_A[0].rotation = [0, 0, 0]
conference_chair_E[0].position = [2.2912436806160192, 3.694521803244732, 0.525]
conference_chair_E[0].rotation = [0, 0, 0]
sideboard_credenda[0].position = [5.581652614210908, 0.34243609390821383, 0.45]
sideboard_credenda[0].rotation = [0, 0, 0]
meeting_side_table_A[0].position = [0.00634502848788987, 9.377020466995754, 0.275]
meeting_side_table_A[0].rotation = [0, 0, 0]
brochure_stand[0].position = [6.30907011089517, 8.503573518215756, 0.75]
brochure_stand[0].rotation = [0, 0, 0]
pen_B[0].position = [5.466643418792795, 7.463516819786307, 0.07]
pen_B[0].rotation = [0, 0, 0]
notepad_B[0].position = [3.6906311408002725, 8.900979882547684, 0.01]
notepad_B[0].rotation = [0, 0, 0]
lounge_armchair_B[0].position = [5.266025547497874, 0.875119887274755, 0.475]
lounge_armchair_B[0].rotation = [0, 0, 0]
paper_ream_B[0].position = [6.5087607252748825, 10.841856770598106, 0.025]
paper_ream_B[0].rotation = [0, 0, 0]
wall_clock[0].position = [6.067100525406487, 5.728817745969587, 0.175]
wall_clock[0].rotation = [0, 0, 0]
meeting_side_table_B[0].position = [1.2808156101489745, 7.686571072119623, 0.275]
meeting_side_table_B[0].rotation = [0, 0, 0]
notepad_C[0].position = [5.121641325640781, 2.001434411595108, 0.01]
notepad_C[0].rotation = [0, 0, 0]
printer_stand[0].position = [5.754583729482337, 10.879055382131748, 0.375]
printer_stand[0].rotation = [0, 0, 0]
paper_ream_C[0].position = [1.8186575181369493, 8.060396948549378, 0.025]
paper_ream_C[0].rotation = [0, 0, 0]
meeting_side_table_C[0].position = [4.831143975020902, 10.715835263397556, 0.275]
meeting_side_table_C[0].rotation = [0, 0, 0]
storage_box_A[0].position = [4.438346642931748, 7.723660163780452, 0.14]
storage_box_A[0].rotation = [0, 0, 0]
framed_poster_C[0].position = [7.334102556079762, 10.457723839695852, 0.3]
framed_poster_C[0].rotation = [0, 0, 0]
storage_cabinet_B[0].position = [7.376085882361336, 1.6679165976049686, 0.675]
storage_cabinet_B[0].rotation = [0, 0, 0]
framed_poster_D[0].position = [5.8067594316643945, 5.82598384256572, 0.3]
framed_poster_D[0].rotation = [0, 0, 0]
paper_ream_D[0].position = [3.3967778886401705, 8.75078815416517, 0.025]
paper_ream_D[0].rotation = [0, 0, 0]
presentation_console[0].position = [2.109056481738123, 2.4758109657594622, 0.5]
presentation_console[0].rotation = [0, 0, 0]
pen_C[0].position = [5.484608671904928, 2.2650554499669413, 0.07]
pen_C[0].rotation = [0, 0, 0]
conference_table[0].position = [3.1132537751167, 6.365688691769493, 0.375]
conference_table[0].rotation = [0, 0, 0]
wall_whiteboard[0].position = [1.9328948821554555, 12.023402619980411, 0.6]
wall_whiteboard[0].rotation = [0, 0, 0]
floor_planter_D[0].position = [1.6174737950163944, 11.222559993314064, 0.45]
floor_planter_D[0].rotation = [0, 0, 0]
storage_box_B[0].position = [7.640036067997667, 9.19360825635152, 0.14]
storage_box_B[0].rotation = [0, 0, 0]
conference_chair_F[0].position = [5.984013293794734, 3.9388916297111702, 0.525]
conference_chair_F[0].rotation = [0, 0, 0]
snack_bowl[0].position = [5.39991991774731, 2.7303803595540646, 0.06]
snack_bowl[0].rotation = [0, 0, 0]
coat_stand_B[0].position = [3.033997243238609, 7.642184001929199, 0.9]
coat_stand_B[0].rotation = [0, 0, 0]
magazine_C[0].position = [0.2877210275167261, 7.0461348196793026, 0.005]
magazine_C[0].rotation = [0, 0, 0]
framed_poster_A[0].position = [6.7528499240016595, 4.98127171944546, 0.3]
framed_poster_A[0].rotation = [0, 0, 0]
floor_planter_A[0].position = [0.6283761493604523, 6.913157463233122, 0.45]
floor_planter_A[0].rotation = [0, 0, 0]
conference_chair_A[0].position = [5.516279461927399, 10.77411515143984, 0.525]
conference_chair_A[0].rotation = [0, 0, 0]
lounge_side_table[0].position = [5.391274592968432, 7.81280816621072, 0.25]
lounge_side_table[0].rotation = [0, 0, 0]
magazine_A[0].position = [6.005811176901463, 10.4057071712739, 0.005]
magazine_A[0].rotation = [0, 0, 0]
conference_chair_B[0].position = [4.076965232230782, 1.9827710647717063, 0.525]
conference_chair_B[0].rotation = [0, 0, 0]
floor_planter_B[0].position = [1.9858513100943727, 6.986328982850133, 0.45]
floor_planter_B[0].rotation = [0, 0, 0]
storage_cabinet_A[0].position = [7.910110748374247, 5.566217136500019, 0.675]
storage_cabinet_A[0].rotation = [0, 0, 0]
framed_poster_B[0].position = [2.8248085789957873, 8.2943753676851, 0.3]
framed_poster_B[0].rotation = [0, 0, 0]
floor_planter_C[0].position = [4.478536933369909, 5.680140019317829, 0.45]
floor_planter_C[0].rotation = [0, 0, 0]
conference_chair_C[0].position = [2.930533723359889, 9.846631398755392, 0.525]
conference_chair_C[0].rotation = [0, 0, 0]
lounge_armchair_A[0].position = [7.53645313625342, 7.778288696001732, 0.475]
lounge_armchair_A[0].rotation = [0, 0, 0]
paper_ream_A[0].position = [7.074017834011377, 10.866367932448796, 0.025]
paper_ream_A[0].rotation = [0, 0, 0]
notepad_A[0].position = [4.623969362358542, 0.008394407599798148, 0.01]
notepad_A[0].rotation = [0, 0, 0]
coat_stand_A[0].position = [2.829210308147828, 5.104460645278712, 0.9]
coat_stand_A[0].rotation = [0, 0, 0]
magazine_B[0].position = [2.465640485302555, 3.3270487388692045, 0.005]
magazine_B[0].rotation = [0, 0, 0]
conference_chair_D[0].position = [4.9543342295267925, 1.795948847668296, 0.525]
conference_chair_D[0].rotation = [0, 0, 0]
pen_A[0].position = [1.7415955088416082, 7.591079407170584, 0.07]
pen_A[0].rotation = [0, 0, 0]
conference_chair_E[0].position = [2.2912436806160192, 3.694521803244732, 0.525]
conference_chair_E[0].rotation = [0, 0, 0]
sideboard_credenda[0].position = [5.581652614210908, 0.34243609390821383, 0.45]
sideboard_credenda[0].rotation = [0, 0, 0]
meeting_side_table_A[0].position = [0.00634502848788987, 9.377020466995754, 0.275]
meeting_side_table_A[0].rotation = [0, 0, 0]
brochure_stand[0].position = [6.30907011089517, 8.503573518215756, 0.75]
brochure_stand[0].rotation = [0, 0, 0]
pen_B[0].position = [5.466643418792795, 7.463516819786307, 0.07]
pen_B[0].rotation = [0, 0, 0]
notepad_B[0].position = [3.6906311408002725, 8.900979882547684, 0.01]
notepad_B[0].rotation = [0, 0, 0]
lounge_armchair_B[0].position = [5.266025547497874, 0.875119887274755, 0.475]
lounge_armchair_B[0].rotation = [0, 0, 0]
paper_ream_B[0].position = [6.5087607252748825, 10.841856770598106, 0.025]
paper_ream_B[0].rotation = [0, 0, 0]
wall_clock[0].position = [6.067100525406487, 5.728817745969587, 0.175]
wall_clock[0].rotation = [0, 0, 0]
meeting_side_table_B[0].position = [1.2808156101489745, 7.686571072119623, 0.275]
meeting_side_table_B[0].rotation = [0, 0, 0]
notepad_C[0].position = [5.121641325640781, 2.001434411595108, 0.01]
notepad_C[0].rotation = [0, 0, 0]
printer_stand[0].position = [5.754583729482337, 10.879055382131748, 0.375]
printer_stand[0].rotation = [0, 0, 0]
paper_ream_C[0].position = [1.8186575181369493, 8.060396948549378, 0.025]
paper_ream_C[0].rotation = [0, 0, 0]
meeting_side_table_C[0].position = [4.831143975020902, 10.715835263397556, 0.275]
meeting_side_table_C[0].rotation = [0, 0, 0]
storage_box_A[0].position = [4.438346642931748, 7.723660163780452, 0.14]
storage_box_A[0].rotation = [0, 0, 0]
framed_poster_C[0].position = [7.334102556079762, 10.457723839695852, 0.3]
framed_poster_C[0].rotation = [0, 0, 0]
storage_cabinet_B[0].position = [7.376085882361336, 1.6679165976049686, 0.675]
storage_cabinet_B[0].rotation = [0, 0, 0]
framed_poster_D[0].position = [5.8067594316643945, 5.82598384256572, 0.3]
framed_poster_D[0].rotation = [0, 0, 0]
paper_ream_D[0].position = [3.3967778886401705, 8.75078815416517, 0.025]
paper_ream_D[0].rotation = [0, 0, 0]
presentation_console[0].position = [2.109056481738123, 2.4758109657594622, 0.5]
presentation_console[0].rotation = [0, 0, 0]
pen_C[0].position = [5.484608671904928, 2.2650554499669413, 0.07]
pen_C[0].rotation = [0, 0, 0]
conference_table[0].position = [3.1132537751167, 6.365688691769493, 0.375]
conference_table[0].rotation = [0, 0, 0]
wall_whiteboard[0].position = [1.9328948821554555, 12.023402619980411, 0.6]
wall_whiteboard[0].rotation = [0, 0, 0]
floor_planter_D[0].position = [1.6174737950163944, 11.222559993314064, 0.45]
floor_planter_D[0].rotation = [0, 0, 0]
storage_box_B[0].position = [7.640036067997667, 9.19360825635152, 0.14]
storage_box_B[0].rotation = [0, 0, 0]
conference_chair_F[0].position = [5.984013293794734, 3.9388916297111702, 0.525]
conference_chair_F[0].rotation = [0, 0, 0]
snack_bowl[0].position = [5.39991991774731, 2.7303803595540646, 0.06]
snack_bowl[0].rotation = [0, 0, 0]
coat_stand_B[0].position = [3.033997243238609, 7.642184001929199, 0.9]
coat_stand_B[0].rotation = [0, 0, 0]
magazine_C[0].position = [0.2877210275167261, 7.0461348196793026, 0.005]
magazine_C[0].rotation = [0, 0, 0]

solver.constraints = []

# The conference area occupies the broad central portion of the room. The
# western side and the doorway approach around (0, 11.88) remain unobstructed.
conference_table[0].position = [5.55, 7.50, 0.375]
conference_table[0].rotation = [0, 0, radians(0)]

# Three chairs are placed along each long side of the conference table.
conference_chair_D[0].position = [4.35, 6.60, 0.525]  # o0016
conference_chair_D[0].rotation = [0, 0, radians(0)]
conference_chair_F[0].position = [4.35, 7.50, 0.525]  # o0043, between D and E
conference_chair_F[0].rotation = [0, 0, radians(0)]
conference_chair_E[0].position = [4.35, 8.40, 0.525]  # o0018
conference_chair_E[0].rotation = [0, 0, radians(0)]

conference_chair_A[0].position = [6.75, 6.60, 0.525]
conference_chair_A[0].rotation = [0, 0, radians(180)]
conference_chair_B[0].position = [6.75, 7.50, 0.525]
conference_chair_B[0].rotation = [0, 0, radians(180)]
conference_chair_C[0].position = [6.75, 8.40, 0.525]
conference_chair_C[0].rotation = [0, 0, radians(180)]

# The specified coat stand is directly east of chair o0018, allowing that
# chair to face both the stand and the conference table.
coat_stand_B[0].position = [7.55, 8.40, 0.90]
coat_stand_B[0].rotation = [0, 0, radians(180)]
coat_stand_A[0].position = [3.00, 11.45, 0.90]
coat_stand_A[0].rotation = [0, 0, radians(-90)]

# Presentation equipment is grouped at the north end of the conference zone.
wall_whiteboard[0].position = [4.35, 11.96, 1.55]
wall_whiteboard[0].rotation = [0, 0, radians(-90)]
presentation_console[0].position = [4.35, 10.90, 0.50]
presentation_console[0].rotation = [0, 0, radians(90)]

# Storage and printing equipment use the solid south wall, away from windows.
storage_cabinet_A[0].position = [4.35, 0.30, 0.675]
storage_cabinet_A[0].rotation = [0, 0, radians(90)]
storage_cabinet_B[0].position = [5.15, 0.30, 0.675]
storage_cabinet_B[0].rotation = [0, 0, radians(90)]
printer_stand[0].position = [6.20, 0.40, 0.375]
printer_stand[0].rotation = [0, 0, radians(90)]

# The credenza sits along the north wall, clear of the door at x=0..1.94.
sideboard_credenda[0].position = [6.65, 11.75, 0.45]
sideboard_credenda[0].rotation = [0, 0, radians(-90)]

storage_box_A[0].position = [4.35, 0.30, 1.49]
storage_box_A[0].rotation = [0, 0, radians(90)]
storage_box_B[0].position = [5.15, 0.30, 1.49]
storage_box_B[0].rotation = [0, 0, radians(90)]

# Lounge furniture fits in the lower-left alcove. Both armchairs face the
# shared table while retaining circulation around the alcove entrance.
lounge_armchair_A[0].position = [2.65, 2.30, 0.475]
lounge_armchair_A[0].rotation = [0, 0, radians(46)]
lounge_armchair_B[0].position = [2.65, 4.15, 0.475]
lounge_armchair_B[0].rotation = [0, 0, radians(-46)]
lounge_side_table[0].position = [3.55, 3.23, 0.25]
lounge_side_table[0].rotation = [0, 0, radians(0)]

# Small supplementary tables are distributed outside the conference-chair
# circulation envelope.
meeting_side_table_A[0].position = [3.65, 4.70, 0.275]
meeting_side_table_A[0].rotation = [0, 0, radians(0)]
meeting_side_table_B[0].position = [7.10, 3.45, 0.275]
meeting_side_table_B[0].rotation = [0, 0, radians(0)]
meeting_side_table_C[0].position = [2.80, 10.35, 0.275]
meeting_side_table_C[0].rotation = [0, 0, radians(0)]

brochure_stand[0].position = [2.50, 5.55, 0.75]
brochure_stand[0].rotation = [0, 0, radians(0)]

# Planters occupy unused perimeter locations without blocking the door or the
# conference seating. The eastern planters sit between window centers.
floor_planter_A[0].position = [0.30, 5.55, 0.45]
floor_planter_A[0].rotation = [0, 0, radians(0)]
floor_planter_B[0].position = [0.30, 9.85, 0.45]
floor_planter_B[0].rotation = [0, 0, radians(0)]
floor_planter_C[0].position = [7.65, 5.85, 0.45]
floor_planter_C[0].rotation = [0, 0, radians(180)]
floor_planter_D[0].position = [7.65, 10.05, 0.45]
floor_planter_D[0].rotation = [0, 0, radians(180)]

# Wall decorations use the uninterrupted west wall. They are vertically
# elevated and kept away from the doorway at the north-west corner.
framed_poster_A[0].position = [0.02, 6.35, 1.65]
framed_poster_A[0].rotation = [0, 0, radians(0)]
framed_poster_B[0].position = [0.02, 7.45, 1.65]
framed_poster_B[0].rotation = [0, 0, radians(0)]
framed_poster_C[0].position = [0.02, 8.55, 1.65]
framed_poster_C[0].rotation = [0, 0, radians(0)]
framed_poster_D[0].position = [0.02, 9.65, 1.65]
framed_poster_D[0].rotation = [0, 0, radians(0)]
wall_clock[0].position = [0.025, 10.55, 1.75]
wall_clock[0].rotation = [0, 0, radians(0)]

# Reading material is distributed over the lounge and supplementary tables.
magazine_A[0].position = [3.55, 3.23, 0.505]
magazine_A[0].rotation = [0, 0, radians(15)]
magazine_B[0].position = [3.65, 4.70, 0.555]
magazine_B[0].rotation = [0, 0, radians(-20)]
magazine_C[0].position = [7.10, 3.45, 0.555]
magazine_C[0].rotation = [0, 0, radians(20)]

# o0025 is paper_ream_B; it is explicitly placed on printer_stand (o0029).
paper_ream_B[0].position = [6.20, 0.40, 0.775]
paper_ream_B[0].rotation = [0, 0, radians(90)]

# Remaining paper and meeting supplies are spread across the conference table
# and credenza so their bounding boxes do not overlap.
paper_ream_A[0].position = [5.55, 6.25, 0.775]
paper_ream_A[0].rotation = [0, 0, radians(0)]
paper_ream_D[0].position = [5.55, 8.75, 0.775]
paper_ream_D[0].rotation = [0, 0, radians(0)]
paper_ream_C[0].position = [6.25, 11.75, 0.925]
paper_ream_C[0].rotation = [0, 0, radians(90)]

notepad_A[0].position = [5.25, 6.95, 0.76]
notepad_A[0].rotation = [0, 0, radians(0)]
notepad_B[0].position = [5.25, 7.50, 0.76]
notepad_B[0].rotation = [0, 0, radians(0)]
notepad_C[0].position = [5.25, 8.05, 0.76]
notepad_C[0].rotation = [0, 0, radians(0)]

pen_A[0].position = [5.55, 6.95, 0.82]
pen_A[0].rotation = [0, 0, radians(0)]
pen_B[0].position = [5.55, 7.50, 0.82]
pen_B[0].rotation = [0, 0, radians(0)]
pen_C[0].position = [5.55, 8.05, 0.82]
pen_C[0].rotation = [0, 0, radians(0)]

snack_bowl[0].position = [5.85, 7.50, 0.81]
snack_bowl[0].rotation = [0, 0, radians(0)]


# Important semantic constraints are declared first because earlier
# constraints take precedence if physical adjustment creates a conflict.

# Keep o0043 equally spaced between o0016 and o0018.
solver.distance_constraint(
    conference_chair_F[0], conference_chair_D[0], 0.90, 0.90, weight=10
)
solver.distance_constraint(
    conference_chair_F[0], conference_chair_E[0], 0.90, 0.90, weight=10
)
solver.align_with(conference_chair_F[0], conference_chair_D[0])

# Chair o0018 must face coat stand o0045.
solver.point_towards(conference_chair_E[0], coat_stand_B[0])

# All other conference chairs face the table.
solver.point_towards(conference_chair_D[0], conference_table[0])
solver.point_towards(conference_chair_F[0], conference_table[0])
solver.point_towards(conference_chair_A[0], conference_table[0])
solver.point_towards(conference_chair_B[0], conference_table[0])
solver.point_towards(conference_chair_C[0], conference_table[0])

# Lounge chairs face their shared side table.
solver.point_towards(lounge_armchair_A[0], lounge_side_table[0])
solver.point_towards(lounge_armchair_B[0], lounge_side_table[0])

# Wall-mounted and wall-backed assets remain attached to their intended walls.
for _west_wall_asset in (
    framed_poster_A[0],
    framed_poster_B[0],
    framed_poster_C[0],
    framed_poster_D[0],
    wall_clock[0],
):
    solver.against_wall(_west_wall_asset, walls[9])

for _south_wall_asset in (
    storage_cabinet_A[0],
    storage_cabinet_B[0],
    printer_stand[0],
):
    solver.against_wall(_south_wall_asset, walls[4])

solver.against_wall(wall_whiteboard[0], walls[6])
solver.against_wall(sideboard_credenda[0], walls[6])

# Vertical support relationships for every object that is not floor-standing
# or wall-mounted.
solver.on_top_of(storage_box_A[0], storage_cabinet_A[0])
solver.on_top_of(storage_box_B[0], storage_cabinet_B[0])

solver.on_top_of(magazine_A[0], lounge_side_table[0])
solver.on_top_of(magazine_B[0], meeting_side_table_A[0])
solver.on_top_of(magazine_C[0], meeting_side_table_B[0])

solver.on_top_of(paper_ream_B[0], printer_stand[0])
solver.on_top_of(paper_ream_C[0], sideboard_credenda[0])
solver.on_top_of(paper_ream_A[0], conference_table[0])
solver.on_top_of(paper_ream_D[0], conference_table[0])

for _conference_small_item in (
    notepad_A[0],
    notepad_B[0],
    notepad_C[0],
    pen_A[0],
    pen_B[0],
    pen_C[0],
    snack_bowl[0],
):
    solver.on_top_of(_conference_small_item, conference_table[0])

# Every new instance receives an explicit position constraint and an
# orientation constraint. The fixed targets preserve the feasible,
# non-overlapping arrangement while the semantic constraints above retain
# priority.
_all_new_instances = (
    framed_poster_A[0],
    floor_planter_A[0],
    conference_chair_A[0],
    lounge_side_table[0],
    magazine_A[0],
    conference_chair_B[0],
    floor_planter_B[0],
    storage_cabinet_A[0],
    framed_poster_B[0],
    floor_planter_C[0],
    conference_chair_C[0],
    lounge_armchair_A[0],
    paper_ream_A[0],
    notepad_A[0],
    coat_stand_A[0],
    magazine_B[0],
    conference_chair_D[0],
    pen_A[0],
    conference_chair_E[0],
    sideboard_credenda[0],
    meeting_side_table_A[0],
    brochure_stand[0],
    pen_B[0],
    notepad_B[0],
    lounge_armchair_B[0],
    paper_ream_B[0],
    wall_clock[0],
    meeting_side_table_B[0],
    notepad_C[0],
    printer_stand[0],
    paper_ream_C[0],
    meeting_side_table_C[0],
    storage_box_A[0],
    framed_poster_C[0],
    storage_cabinet_B[0],
    framed_poster_D[0],
    paper_ream_D[0],
    presentation_console[0],
    pen_C[0],
    conference_table[0],
    wall_whiteboard[0],
    floor_planter_D[0],
    storage_box_B[0],
    conference_chair_F[0],
    snack_bowl[0],
    coat_stand_B[0],
    magazine_C[0],
)

for _instance in _all_new_instances:
    _position_target = AssetInstance(position=list(_instance.position))
    _orientation_target = AssetInstance(rotation=list(_instance.rotation))
    solver.distance_constraint(
        _instance, _position_target, 0.0, 0.0, weight=10
    )
    solver.align_with(_instance, _orientation_target)

solver.constraints = []
magazine_C[0].position = [7.099999904632568, 3.450000047683716, 0.5550000071525574]
magazine_C[0].rotation = [0, 0, 0.3616321980963252]
magazine_C[0].optimize = 2
lounge_side_table[0].position = [3.549999952316284, 3.2300000190734863, 0.25]
lounge_side_table[0].rotation = [0, 0, 0.01884955539881635]
lounge_side_table[0].optimize = 2
storage_box_B[0].position = [5.150000095367432, 0.30000001192092896, 1.4900000095367432]
storage_box_B[0].rotation = [0, 0, 1.5833626980517244]
storage_box_B[0].optimize = 2
conference_chair_C[0].position = [6.75, 8.399999618530273, 0.5249999761581421]
conference_chair_C[0].rotation = [0, 0, -3.1290262823329655]
conference_chair_C[0].optimize = 2
floor_planter_D[0].position = [7.650000095367432, 10.050000190734863, 0.44999998807907104]
floor_planter_D[0].rotation = [0, 0, -3.1321678761290697]
floor_planter_D[0].optimize = 2
notepad_B[0].position = [5.25, 7.5, 0.7599999904632568]
notepad_B[0].rotation = [0, 0, 0.01256637125682779]
notepad_B[0].optimize = 2
sideboard_credenda[0].position = [6.650000095367432, 11.774977684020996, 0.44999998807907104]
sideboard_credenda[0].rotation = [0, 0, -1.5708060237472856]
sideboard_credenda[0].optimize = 2
floor_planter_C[0].position = [7.650000095367432, 5.849999904632568, 0.44999998807907104]
floor_planter_C[0].rotation = [0, 0, -3.1321678761290697]
floor_planter_C[0].optimize = 2
conference_chair_A[0].position = [6.75, 6.599999904632568, 0.5249999761581421]
conference_chair_A[0].rotation = [0, 0, -3.1290262823329655]
conference_chair_A[0].optimize = 2
paper_ream_A[0].position = [5.550000190734863, 6.25, 0.7749999761581421]
paper_ream_A[0].rotation = [0, 0, 0.01256637125682779]
paper_ream_A[0].optimize = 2
floor_planter_B[0].position = [0.30000001192092896, 9.850000381469727, 0.44999998807907104]
floor_planter_B[0].rotation = [0, 0, 0.00942477746072377]
floor_planter_B[0].optimize = 2
pen_B[0].position = [5.550000190734863, 7.5, 0.8199999928474426]
pen_B[0].rotation = [0, 0, 0.01256637125682779]
pen_B[0].optimize = 2
lounge_armchair_B[0].position = [2.6500000953674316, 4.150000095367432, 0.4749999940395355]
lounge_armchair_B[0].rotation = [0, 0, -0.7902850678052554]
lounge_armchair_B[0].optimize = 2
framed_poster_A[0].position = [0.019987858831882477, 6.349999904632568, 0.30000001192092896]
framed_poster_A[0].rotation = [0, 0, -9.97461080881251e-06]
framed_poster_A[0].optimize = 2
paper_ream_C[0].position = [6.25, 11.75, 0.9249999523162842]
paper_ream_C[0].rotation = [0, 0, 1.5833626980517244]
paper_ream_C[0].optimize = 2
printer_stand[0].position = [6.199999809265137, 0.2998398244380951, 0.375]
printer_stand[0].rotation = [0, 0, 1.5707906305927584]
printer_stand[0].optimize = 2
meeting_side_table_B[0].position = [7.099999904632568, 3.450000047683716, 0.2750000059604645]
meeting_side_table_B[0].rotation = [0, 0, 0.01256637125682779]
meeting_side_table_B[0].optimize = 2
coat_stand_B[0].position = [7.550000190734863, 8.399999618530273, 0.8999999761581421]
coat_stand_B[0].rotation = [0, 0, -3.1290262823329655]
coat_stand_B[0].optimize = 2
conference_chair_E[0].position = [4.349999904632568, 8.399999618530273, 0.5249999761581421]
conference_chair_E[0].rotation = [0, 0, 0.0157079639172164]
conference_chair_E[0].optimize = 2
framed_poster_B[0].position = [0.019987858831882477, 7.449999809265137, 0.30000001192092896]
framed_poster_B[0].rotation = [0, 0, -9.97461080881251e-06]
framed_poster_B[0].optimize = 2
paper_ream_D[0].position = [5.550000190734863, 8.75, 0.7749999761581421]
paper_ream_D[0].rotation = [0, 0, 0.01256637125682779]
paper_ream_D[0].optimize = 2
floor_planter_A[0].position = [0.30000001192092896, 5.550000190734863, 0.44999998807907104]
floor_planter_A[0].rotation = [0, 0, 0.00942477746072377]
floor_planter_A[0].optimize = 2
wall_clock[0].position = [0.024983802810311317, 10.550000190734863, 0.17499999701976776]
wall_clock[0].rotation = [0, 0, -9.977773245150726e-06]
wall_clock[0].optimize = 2
meeting_side_table_C[0].position = [2.799999952316284, 10.350000381469727, 0.2750000059604645]
meeting_side_table_C[0].rotation = [0, 0, 0.00942477746072377]
meeting_side_table_C[0].optimize = 2
framed_poster_C[0].position = [0.019987858831882477, 8.550000190734863, 0.30000001192092896]
framed_poster_C[0].rotation = [0, 0, -9.97461080881251e-06]
framed_poster_C[0].optimize = 2
pen_A[0].position = [5.550000190734863, 6.949999809265137, 0.8199999928474426]
pen_A[0].rotation = [0, 0, 0.01256637125682779]
pen_A[0].optimize = 2
conference_chair_B[0].position = [6.75, 7.5, 0.5249999761581421]
conference_chair_B[0].rotation = [0, 0, -3.1290262823329655]
conference_chair_B[0].optimize = 2
magazine_A[0].position = [3.549999952316284, 3.2300000190734863, 0.5049999952316284]
magazine_A[0].rotation = [0, 0, 0.27436574034236844]
magazine_A[0].optimize = 2
storage_cabinet_A[0].position = [4.349999904632568, 0.2999897599220276, 0.675000011920929]
storage_cabinet_A[0].rotation = [0, 0, 1.5707864031794327]
storage_cabinet_A[0].optimize = 2
paper_ream_B[0].position = [6.199999809265137, 0.4000000059604645, 0.7749999761581421]
paper_ream_B[0].rotation = [0, 0, 1.5833626980517244]
paper_ream_B[0].optimize = 2
notepad_A[0].position = [5.25, 6.949999809265137, 0.7599999904632568]
notepad_A[0].rotation = [0, 0, 0.01256637125682779]
notepad_A[0].optimize = 2
conference_chair_D[0].position = [4.349999904632568, 6.599999904632568, 0.5249999761581421]
conference_chair_D[0].rotation = [0, 0, 0.01884955539881635]
conference_chair_D[0].optimize = 2
brochure_stand[0].position = [2.5, 5.550000190734863, 0.75]
brochure_stand[0].rotation = [0, 0, 0.00942477746072377]
brochure_stand[0].optimize = 2
notepad_C[0].position = [5.25, 8.050000190734863, 0.7599999904632568]
notepad_C[0].rotation = [0, 0, 0.01256637125682779]
notepad_C[0].optimize = 2
framed_poster_D[0].position = [0.019987858831882477, 9.649999618530273, 0.30000001192092896]
framed_poster_D[0].rotation = [0, 0, -9.97461080881251e-06]
framed_poster_D[0].optimize = 2
presentation_console[0].position = [4.349999904632568, 10.899999618530273, 0.5]
presentation_console[0].rotation = [0, 0, 1.5802211042556205]
presentation_console[0].optimize = 2
conference_table[0].position = [5.550000190734863, 7.5, 0.375]
conference_table[0].rotation = [0, 0, 0.053407073383009665]
conference_table[0].optimize = 2
pen_C[0].position = [5.550000190734863, 8.050000190734863, 0.8199999928474426]
pen_C[0].rotation = [0, 0, 0.01256637125682779]
pen_C[0].optimize = 2
wall_whiteboard[0].position = [4.349999904632568, 11.97000789642334, 0.6000000238418579]
wall_whiteboard[0].rotation = [0, 0, -1.5708061521955725]
wall_whiteboard[0].optimize = 2
conference_chair_F[0].position = [4.349999904632568, 7.5, 0.5249999761581421]
conference_chair_F[0].rotation = [0, 0, 0.018859573000051824]
conference_chair_F[0].optimize = 2
coat_stand_A[0].position = [3.0, 11.449999809265137, 0.8999999761581421]
coat_stand_A[0].rotation = [0, 0, -1.5613715493341729]
coat_stand_A[0].optimize = 2
snack_bowl[0].position = [5.849999904632568, 7.5, 0.8100000023841858]
snack_bowl[0].rotation = [0, 0, 0.01256637125682779]
snack_bowl[0].optimize = 2
storage_box_A[0].position = [4.349999904632568, 0.30000001192092896, 1.4900000095367432]
storage_box_A[0].rotation = [0, 0, 1.5833626980517244]
storage_box_A[0].optimize = 2
meeting_side_table_A[0].position = [3.6500000953674316, 4.699999809265137, 0.2750000059604645]
meeting_side_table_A[0].rotation = [0, 0, 0.01256637125682779]
meeting_side_table_A[0].optimize = 2
lounge_armchair_A[0].position = [2.6500000953674316, 2.299999952316284, 0.4749999940395355]
lounge_armchair_A[0].rotation = [0, 0, 0.8154178034275958]
lounge_armchair_A[0].optimize = 2
storage_cabinet_B[0].position = [5.150000095367432, 0.2999897599220276, 0.675000011920929]
storage_cabinet_B[0].rotation = [0, 0, 1.5707864031794327]
storage_cabinet_B[0].optimize = 2
magazine_B[0].position = [3.6500000953674316, 4.699999809265137, 0.5550000071525574]
magazine_B[0].rotation = [0, 0, -0.33649949307578897]
magazine_B[0].optimize = 2

