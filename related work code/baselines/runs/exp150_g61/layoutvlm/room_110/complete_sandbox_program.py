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
    Wall(corner1=[0.00, 10.00, 0.00], corner2=[0.00, 5.00, 0.00]),
    Wall(corner1=[0.00, 5.00, 0.00], corner2=[2.00, 5.00, 0.00]),
    Wall(corner1=[2.00, 5.00, 0.00], corner2=[2.00, 2.00, 0.00]),
    Wall(corner1=[2.00, 2.00, 0.00], corner2=[6.00, 2.00, 0.00]),
    Wall(corner1=[6.00, 2.00, 0.00], corner2=[6.00, 0.00, 0.00]),
    Wall(corner1=[6.00, 0.00, 0.00], corner2=[10.00, 0.00, 0.00]),
    Wall(corner1=[10.00, 0.00, 0.00], corner2=[10.00, 10.00, 0.00]),
    Wall(corner1=[10.00, 10.00, 0.00], corner2=[0.00, 10.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
throw_pillow = Assets(description="A large white pillow with golden edges.", size=[0.20, 0.60, 0.60], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_A = Assets(description="The plaque has a design in the middle of the board.", size=[0.05, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
lounge_side_table_A = Assets(description="A round wooden table holding a blue and white owl statue.", size=[0.60, 0.60, 0.55], placements=[AssetInstance() for _ in range(1)])
freestanding_planter_A = Assets(description="A wooden planter with some strawberries.", size=[0.40, 0.65, 0.85], placements=[AssetInstance() for _ in range(1)])
mobile_whiteboard_A = Assets(description="A whiteboard with a black marker.", size=[0.65, 1.50, 1.85], placements=[AssetInstance() for _ in range(1)])
wall_shelf_A = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.25, 1.00, 0.30], placements=[AssetInstance() for _ in range(1)])
side_credenda = Assets(description="Long wood cabinet with metal frame and drawers.", size=[0.45, 1.80, 0.80], placements=[AssetInstance() for _ in range(1)])
meeting_chair_A = Assets(description="A black office chair with a tall mesh back.", size=[0.65, 0.65, 1.15], placements=[AssetInstance() for _ in range(1)])
conference_table = Assets(description="A long white table with two black spines.", size=[1.20, 3.20, 0.75], placements=[AssetInstance() for _ in range(1)])
storage_box_A = Assets(description="A red microwave oven.", size=[0.38, 0.50, 0.30], placements=[AssetInstance() for _ in range(1)])
mobile_whiteboard_B = Assets(description="A whiteboard with a black marker.", size=[0.65, 1.50, 1.85], placements=[AssetInstance() for _ in range(1)])
trash_recycling_bin_A = Assets(description="A pair of white drawers in the black dresser.", size=[0.35, 0.60, 0.65], placements=[AssetInstance() for _ in range(1)])
storage_box_B = Assets(description="A red microwave oven.", size=[0.38, 0.50, 0.30], placements=[AssetInstance() for _ in range(1)])
wall_shelf_B = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.25, 1.00, 0.30], placements=[AssetInstance() for _ in range(1)])
small_planter = Assets(description="A plant sitting in a round flower pot.", size=[0.30, 0.30, 0.45], placements=[AssetInstance() for _ in range(1)])
wall_monitor = Assets(description="An image of a mountain lake in a white frame.", size=[0.07, 1.45, 0.84], placements=[AssetInstance() for _ in range(1)])
freestanding_planter_B = Assets(description="A wooden planter with some strawberries.", size=[0.40, 0.65, 0.85], placements=[AssetInstance() for _ in range(1)])
magazine_A = Assets(description="A light brown hardback book with atom depicted in gold on the cover.", size=[0.29, 0.22, 0.03], placements=[AssetInstance() for _ in range(1)])
meeting_chair_B = Assets(description="A black office chair with a tall mesh back.", size=[0.65, 0.65, 1.15], placements=[AssetInstance() for _ in range(1)])
magazine_B = Assets(description="A light brown hardback book with atom depicted in gold on the cover.", size=[0.29, 0.22, 0.03], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_B = Assets(description="The plaque has a design in the middle of the board.", size=[0.05, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_C = Assets(description="The plaque has a design in the middle of the board.", size=[0.05, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
meeting_chair_C = Assets(description="A black office chair with a tall mesh back.", size=[0.65, 0.65, 1.15], placements=[AssetInstance() for _ in range(1)])
lounge_sofa = Assets(description="A grey three seater sofa.", size=[0.90, 2.20, 0.85], placements=[AssetInstance() for _ in range(1)])
freestanding_planter_C = Assets(description="A wooden planter with some strawberries.", size=[0.40, 0.65, 0.85], placements=[AssetInstance() for _ in range(1)])
coat_stand_A = Assets(description="The coatrack is wooden with a round bottom.", size=[0.50, 0.50, 1.75], placements=[AssetInstance() for _ in range(1)])
lounge_side_table_B = Assets(description="A round wooden table holding a blue and white owl statue.", size=[0.60, 0.60, 0.55], placements=[AssetInstance() for _ in range(1)])
coat_stand_B = Assets(description="The coatrack is wooden with a round bottom.", size=[0.50, 0.50, 1.75], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_D = Assets(description="The plaque has a design in the middle of the board.", size=[0.05, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
trash_recycling_bin_B = Assets(description="A pair of white drawers in the black dresser.", size=[0.35, 0.60, 0.65], placements=[AssetInstance() for _ in range(1)])
wall_shelf_C = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.25, 1.00, 0.30], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_E = Assets(description="The plaque has a design in the middle of the board.", size=[0.05, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
sideboard_table = Assets(description="A long narrow wooden table on metal legs.", size=[0.40, 1.60, 0.80], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_F = Assets(description="The plaque has a design in the middle of the board.", size=[0.05, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
meeting_chair_D = Assets(description="A black office chair with a tall mesh back.", size=[0.65, 0.65, 1.15], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_G = Assets(description="The plaque has a design in the middle of the board.", size=[0.05, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
meeting_chair_E = Assets(description="A black office chair with a tall mesh back.", size=[0.65, 0.65, 1.15], placements=[AssetInstance() for _ in range(1)])
storage_cabinet_A = Assets(description="A rectangular set of five dark gray shelves with two drawers beneath them.", size=[0.45, 0.90, 2.00], placements=[AssetInstance() for _ in range(1)])
storage_cabinet_B = Assets(description="A rectangular set of five dark gray shelves with two drawers beneath them.", size=[0.45, 0.90, 2.00], placements=[AssetInstance() for _ in range(1)])
meeting_chair_F = Assets(description="A black office chair with a tall mesh back.", size=[0.65, 0.65, 1.15], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_H = Assets(description="The plaque has a design in the middle of the board.", size=[0.05, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_I = Assets(description="The plaque has a design in the middle of the board.", size=[0.05, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_J = Assets(description="The plaque has a design in the middle of the board.", size=[0.05, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
tray = Assets(description="Carved brown tray with handle and tall sides.", size=[0.30, 0.45, 0.10], placements=[AssetInstance() for _ in range(1)])
wall_clock = Assets(description="A black and white rouund clock with red hands and gears at the center of the circle.", size=[0.06, 0.40, 0.40], placements=[AssetInstance() for _ in range(1)])

throw_pillow[0].instance_id = 'throw_pillow_0'
acoustic_panel_A[0].instance_id = 'acoustic_panel_A_0'
lounge_side_table_A[0].instance_id = 'lounge_side_table_A_0'
freestanding_planter_A[0].instance_id = 'freestanding_planter_A_0'
mobile_whiteboard_A[0].instance_id = 'mobile_whiteboard_A_0'
wall_shelf_A[0].instance_id = 'wall_shelf_A_0'
side_credenda[0].instance_id = 'side_credenda_0'
meeting_chair_A[0].instance_id = 'meeting_chair_A_0'
conference_table[0].instance_id = 'conference_table_0'
storage_box_A[0].instance_id = 'storage_box_A_0'
mobile_whiteboard_B[0].instance_id = 'mobile_whiteboard_B_0'
trash_recycling_bin_A[0].instance_id = 'trash_recycling_bin_A_0'
storage_box_B[0].instance_id = 'storage_box_B_0'
wall_shelf_B[0].instance_id = 'wall_shelf_B_0'
small_planter[0].instance_id = 'small_planter_0'
wall_monitor[0].instance_id = 'wall_monitor_0'
freestanding_planter_B[0].instance_id = 'freestanding_planter_B_0'
magazine_A[0].instance_id = 'magazine_A_0'
meeting_chair_B[0].instance_id = 'meeting_chair_B_0'
magazine_B[0].instance_id = 'magazine_B_0'
acoustic_panel_B[0].instance_id = 'acoustic_panel_B_0'
acoustic_panel_C[0].instance_id = 'acoustic_panel_C_0'
meeting_chair_C[0].instance_id = 'meeting_chair_C_0'
lounge_sofa[0].instance_id = 'lounge_sofa_0'
freestanding_planter_C[0].instance_id = 'freestanding_planter_C_0'
coat_stand_A[0].instance_id = 'coat_stand_A_0'
lounge_side_table_B[0].instance_id = 'lounge_side_table_B_0'
coat_stand_B[0].instance_id = 'coat_stand_B_0'
acoustic_panel_D[0].instance_id = 'acoustic_panel_D_0'
trash_recycling_bin_B[0].instance_id = 'trash_recycling_bin_B_0'
wall_shelf_C[0].instance_id = 'wall_shelf_C_0'
acoustic_panel_E[0].instance_id = 'acoustic_panel_E_0'
sideboard_table[0].instance_id = 'sideboard_table_0'
acoustic_panel_F[0].instance_id = 'acoustic_panel_F_0'
meeting_chair_D[0].instance_id = 'meeting_chair_D_0'
acoustic_panel_G[0].instance_id = 'acoustic_panel_G_0'
meeting_chair_E[0].instance_id = 'meeting_chair_E_0'
storage_cabinet_A[0].instance_id = 'storage_cabinet_A_0'
storage_cabinet_B[0].instance_id = 'storage_cabinet_B_0'
meeting_chair_F[0].instance_id = 'meeting_chair_F_0'
acoustic_panel_H[0].instance_id = 'acoustic_panel_H_0'
acoustic_panel_I[0].instance_id = 'acoustic_panel_I_0'
acoustic_panel_J[0].instance_id = 'acoustic_panel_J_0'
tray[0].instance_id = 'tray_0'
wall_clock[0].instance_id = 'wall_clock_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

throw_pillow[0].position = [8.672764905541973, 6.182948637284439, 0.3]
throw_pillow[0].rotation = [0, 0, 0]
acoustic_panel_A[0].position = [6.990458730304634, 8.705248097278117, 0.6]
acoustic_panel_A[0].rotation = [0, 0, 0]
lounge_side_table_A[0].position = [8.561128131146095, 9.554742767086744, 0.275]
lounge_side_table_A[0].rotation = [0, 0, 0]
freestanding_planter_A[0].position = [6.439091399721175, 0.011232834243992684, 0.425]
freestanding_planter_A[0].rotation = [0, 0, 0]
mobile_whiteboard_A[0].position = [4.080955306809068, 4.908411562783281, 0.925]
mobile_whiteboard_A[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [7.356861792839683, 7.3155913120165605, 0.15]
wall_shelf_A[0].rotation = [0, 0, 0]
side_credenda[0].position = [2.757382479003261, 9.620858955736203, 0.4]
side_credenda[0].rotation = [0, 0, 0]
meeting_chair_A[0].position = [7.82338729396761, 7.317371479910313, 0.575]
meeting_chair_A[0].rotation = [0, 0, 0]
conference_table[0].position = [0.6240764086851969, 6.592724770836944, 0.375]
conference_table[0].rotation = [0, 0, 0]
storage_box_A[0].position = [3.2976059117775525, 2.4392614671094726, 0.15]
storage_box_A[0].rotation = [0, 0, 0]
mobile_whiteboard_B[0].position = [5.692573649864578, 8.375411464502486, 0.925]
mobile_whiteboard_B[0].rotation = [0, 0, 0]
trash_recycling_bin_A[0].position = [3.8894111028496248, 5.6915548837727234, 0.325]
trash_recycling_bin_A[0].rotation = [0, 0, 0]
storage_box_B[0].position = [0.7402481506443093, 9.960486240799723, 0.15]
storage_box_B[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [6.44602361202531, 4.992018257393983, 0.15]
wall_shelf_B[0].rotation = [0, 0, 0]
small_planter[0].position = [4.293329894737781, 2.6859826130701467, 0.225]
small_planter[0].rotation = [0, 0, 0]
wall_monitor[0].position = [4.623997096184485, 6.464834274214345, 0.42]
wall_monitor[0].rotation = [0, 0, 0]
freestanding_planter_B[0].position = [7.022964982486936, 9.625546297218568, 0.425]
freestanding_planter_B[0].rotation = [0, 0, 0]
magazine_A[0].position = [4.55707015957052, 9.476838795342164, 0.0125]
magazine_A[0].rotation = [0, 0, 0]
meeting_chair_B[0].position = [4.073507507363878, 3.2447537054610764, 0.575]
meeting_chair_B[0].rotation = [0, 0, 0]
magazine_B[0].position = [2.5311027994738664, 6.293734663481382, 0.0125]
magazine_B[0].rotation = [0, 0, 0]
acoustic_panel_B[0].position = [5.4748634211457725, 9.730776256430957, 0.6]
acoustic_panel_B[0].rotation = [0, 0, 0]
acoustic_panel_C[0].position = [5.899709127793407, 7.714950920766319, 0.6]
acoustic_panel_C[0].rotation = [0, 0, 0]
meeting_chair_C[0].position = [9.046065773971643, 7.38674001082912, 0.575]
meeting_chair_C[0].rotation = [0, 0, 0]
lounge_sofa[0].position = [5.202395514121435, 2.4161177172885075, 0.425]
lounge_sofa[0].rotation = [0, 0, 0]
freestanding_planter_C[0].position = [7.999080719936816, 3.981725612915504, 0.425]
freestanding_planter_C[0].rotation = [0, 0, 0]
coat_stand_A[0].position = [8.165735912733394, 4.714175300803143, 0.875]
coat_stand_A[0].rotation = [0, 0, 0]
lounge_side_table_B[0].position = [6.70869042337162, 7.3744992860046645, 0.275]
lounge_side_table_B[0].rotation = [0, 0, 0]
coat_stand_B[0].position = [0.9091673075551865, 8.45214908579605, 0.875]
coat_stand_B[0].rotation = [0, 0, 0]
acoustic_panel_D[0].position = [2.9886726875736436, 9.977089413786132, 0.6]
acoustic_panel_D[0].rotation = [0, 0, 0]
trash_recycling_bin_B[0].position = [7.020386473787613, 8.98250822990223, 0.325]
trash_recycling_bin_B[0].rotation = [0, 0, 0]
wall_shelf_C[0].position = [3.747173090282433, 2.4957594303466166, 0.15]
wall_shelf_C[0].rotation = [0, 0, 0]
acoustic_panel_E[0].position = [0.9032881343686916, 7.749429887651812, 0.6]
acoustic_panel_E[0].rotation = [0, 0, 0]
sideboard_table[0].position = [7.129216855679973, 9.504092097065497, 0.4]
sideboard_table[0].rotation = [0, 0, 0]
acoustic_panel_F[0].position = [4.827718913677737, 8.162868267707944, 0.6]
acoustic_panel_F[0].rotation = [0, 0, 0]
meeting_chair_D[0].position = [4.385139572810343, 2.1796920774612785, 0.575]
meeting_chair_D[0].rotation = [0, 0, 0]
acoustic_panel_G[0].position = [8.200297449379978, 0.22725124148006426, 0.6]
acoustic_panel_G[0].rotation = [0, 0, 0]
meeting_chair_E[0].position = [8.63277015755652, 4.208745063868484, 0.575]
meeting_chair_E[0].rotation = [0, 0, 0]
storage_cabinet_A[0].position = [5.495910670075142, 5.324903339746165, 1.0]
storage_cabinet_A[0].rotation = [0, 0, 0]
storage_cabinet_B[0].position = [2.7937067886278766, 5.493895798742025, 1.0]
storage_cabinet_B[0].rotation = [0, 0, 0]
meeting_chair_F[0].position = [9.91338763580062, 0.846919710031725, 0.575]
meeting_chair_F[0].rotation = [0, 0, 0]
acoustic_panel_H[0].position = [8.688212490989798, 5.457224071328449, 0.6]
acoustic_panel_H[0].rotation = [0, 0, 0]
acoustic_panel_I[0].position = [6.160195841020826, 6.51561182696801, 0.6]
acoustic_panel_I[0].rotation = [0, 0, 0]
acoustic_panel_J[0].position = [6.078626738925484, 5.358118771708177, 0.6]
acoustic_panel_J[0].rotation = [0, 0, 0]
tray[0].position = [6.623572974100986, 6.763324751790375, 0.05]
tray[0].rotation = [0, 0, 0]
wall_clock[0].position = [2.8071960434256873, 4.195560519193235, 0.2]
wall_clock[0].rotation = [0, 0, 0]
throw_pillow[0].position = [8.672764905541973, 6.182948637284439, 0.3]
throw_pillow[0].rotation = [0, 0, 0]
acoustic_panel_A[0].position = [6.990458730304634, 8.705248097278117, 0.6]
acoustic_panel_A[0].rotation = [0, 0, 0]
lounge_side_table_A[0].position = [8.561128131146095, 9.554742767086744, 0.275]
lounge_side_table_A[0].rotation = [0, 0, 0]
freestanding_planter_A[0].position = [6.439091399721175, 0.011232834243992684, 0.425]
freestanding_planter_A[0].rotation = [0, 0, 0]
mobile_whiteboard_A[0].position = [4.080955306809068, 4.908411562783281, 0.925]
mobile_whiteboard_A[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [7.356861792839683, 7.3155913120165605, 0.15]
wall_shelf_A[0].rotation = [0, 0, 0]
side_credenda[0].position = [2.757382479003261, 9.620858955736203, 0.4]
side_credenda[0].rotation = [0, 0, 0]
meeting_chair_A[0].position = [7.82338729396761, 7.317371479910313, 0.575]
meeting_chair_A[0].rotation = [0, 0, 0]
conference_table[0].position = [0.6240764086851969, 6.592724770836944, 0.375]
conference_table[0].rotation = [0, 0, 0]
storage_box_A[0].position = [3.2976059117775525, 2.4392614671094726, 0.15]
storage_box_A[0].rotation = [0, 0, 0]
mobile_whiteboard_B[0].position = [5.692573649864578, 8.375411464502486, 0.925]
mobile_whiteboard_B[0].rotation = [0, 0, 0]
trash_recycling_bin_A[0].position = [3.8894111028496248, 5.6915548837727234, 0.325]
trash_recycling_bin_A[0].rotation = [0, 0, 0]
storage_box_B[0].position = [0.7402481506443093, 9.960486240799723, 0.15]
storage_box_B[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [6.44602361202531, 4.992018257393983, 0.15]
wall_shelf_B[0].rotation = [0, 0, 0]
small_planter[0].position = [4.293329894737781, 2.6859826130701467, 0.225]
small_planter[0].rotation = [0, 0, 0]
wall_monitor[0].position = [4.623997096184485, 6.464834274214345, 0.42]
wall_monitor[0].rotation = [0, 0, 0]
freestanding_planter_B[0].position = [7.022964982486936, 9.625546297218568, 0.425]
freestanding_planter_B[0].rotation = [0, 0, 0]
magazine_A[0].position = [4.55707015957052, 9.476838795342164, 0.0125]
magazine_A[0].rotation = [0, 0, 0]
meeting_chair_B[0].position = [4.073507507363878, 3.2447537054610764, 0.575]
meeting_chair_B[0].rotation = [0, 0, 0]
magazine_B[0].position = [2.5311027994738664, 6.293734663481382, 0.0125]
magazine_B[0].rotation = [0, 0, 0]
acoustic_panel_B[0].position = [5.4748634211457725, 9.730776256430957, 0.6]
acoustic_panel_B[0].rotation = [0, 0, 0]
acoustic_panel_C[0].position = [5.899709127793407, 7.714950920766319, 0.6]
acoustic_panel_C[0].rotation = [0, 0, 0]
meeting_chair_C[0].position = [9.046065773971643, 7.38674001082912, 0.575]
meeting_chair_C[0].rotation = [0, 0, 0]
lounge_sofa[0].position = [5.202395514121435, 2.4161177172885075, 0.425]
lounge_sofa[0].rotation = [0, 0, 0]
freestanding_planter_C[0].position = [7.999080719936816, 3.981725612915504, 0.425]
freestanding_planter_C[0].rotation = [0, 0, 0]
coat_stand_A[0].position = [8.165735912733394, 4.714175300803143, 0.875]
coat_stand_A[0].rotation = [0, 0, 0]
lounge_side_table_B[0].position = [6.70869042337162, 7.3744992860046645, 0.275]
lounge_side_table_B[0].rotation = [0, 0, 0]
coat_stand_B[0].position = [0.9091673075551865, 8.45214908579605, 0.875]
coat_stand_B[0].rotation = [0, 0, 0]
acoustic_panel_D[0].position = [2.9886726875736436, 9.977089413786132, 0.6]
acoustic_panel_D[0].rotation = [0, 0, 0]
trash_recycling_bin_B[0].position = [7.020386473787613, 8.98250822990223, 0.325]
trash_recycling_bin_B[0].rotation = [0, 0, 0]
wall_shelf_C[0].position = [3.747173090282433, 2.4957594303466166, 0.15]
wall_shelf_C[0].rotation = [0, 0, 0]
acoustic_panel_E[0].position = [0.9032881343686916, 7.749429887651812, 0.6]
acoustic_panel_E[0].rotation = [0, 0, 0]
sideboard_table[0].position = [7.129216855679973, 9.504092097065497, 0.4]
sideboard_table[0].rotation = [0, 0, 0]
acoustic_panel_F[0].position = [4.827718913677737, 8.162868267707944, 0.6]
acoustic_panel_F[0].rotation = [0, 0, 0]
meeting_chair_D[0].position = [4.385139572810343, 2.1796920774612785, 0.575]
meeting_chair_D[0].rotation = [0, 0, 0]
acoustic_panel_G[0].position = [8.200297449379978, 0.22725124148006426, 0.6]
acoustic_panel_G[0].rotation = [0, 0, 0]
meeting_chair_E[0].position = [8.63277015755652, 4.208745063868484, 0.575]
meeting_chair_E[0].rotation = [0, 0, 0]
storage_cabinet_A[0].position = [5.495910670075142, 5.324903339746165, 1.0]
storage_cabinet_A[0].rotation = [0, 0, 0]
storage_cabinet_B[0].position = [2.7937067886278766, 5.493895798742025, 1.0]
storage_cabinet_B[0].rotation = [0, 0, 0]
meeting_chair_F[0].position = [9.91338763580062, 0.846919710031725, 0.575]
meeting_chair_F[0].rotation = [0, 0, 0]
acoustic_panel_H[0].position = [8.688212490989798, 5.457224071328449, 0.6]
acoustic_panel_H[0].rotation = [0, 0, 0]
acoustic_panel_I[0].position = [6.160195841020826, 6.51561182696801, 0.6]
acoustic_panel_I[0].rotation = [0, 0, 0]
acoustic_panel_J[0].position = [6.078626738925484, 5.358118771708177, 0.6]
acoustic_panel_J[0].rotation = [0, 0, 0]
tray[0].position = [6.623572974100986, 6.763324751790375, 0.05]
tray[0].rotation = [0, 0, 0]
wall_clock[0].position = [2.8071960434256873, 4.195560519193235, 0.2]
wall_clock[0].rotation = [0, 0, 0]

solver.constraints = []

# The coordinate labels define the actual, non-centred room boundary.
# Keep the entrance corridor (approximately x=2.87..4.81, y=2..4.2)
# empty. Put the meeting area farther north, the lounge in the northwest,
# and refreshments/storage in the southeast alcove.
#
# Each record modifies an existing instance; no assets are recreated.
# Wall-mounted objects are explicitly elevated rather than put on furniture.
layout_records = [
    (conference_table,       [6.50, 6.40, 0.375],   0),
    (meeting_chair_A,        [6.50, 4.05, 0.575],  90),
    (meeting_chair_B,        [5.30, 7.50, 0.575],   0),
    (meeting_chair_C,        [5.30, 5.30, 0.575],   0),
    (meeting_chair_D,        [7.70, 6.40, 0.575], 180),
    (meeting_chair_E,        [5.30, 6.40, 0.575],   0),
    (meeting_chair_F,        [6.50, 8.75, 0.575], -90),

    (lounge_sofa,            [0.45, 7.30, 0.425],   0),
    (lounge_side_table_A,    [0.65, 5.65, 0.275],   0),
    (lounge_side_table_B,    [0.65, 9.05, 0.275],   0),
    (throw_pillow,           [0.48, 7.30, 1.150],   0),

    (side_credenda,          [3.10, 9.775, 0.400], -90),
    (storage_box_A,          [2.55, 9.775, 0.950], -90),
    (storage_box_B,          [3.12, 9.775, 0.950], -90),
    (tray,                  [3.70, 9.775, 0.850], -90),

    (sideboard_table,        [8.00, 0.20, 0.400],  90),
    (small_planter,          [7.55, 0.20, 1.025],  90),
    (magazine_B,             [8.35, 0.20, 0.815],  90),
    (magazine_A,             [0.65, 9.05, 0.565],   0),

    (storage_cabinet_A,      [6.225, 0.50, 1.000],  0),
    (storage_cabinet_B,      [6.225, 1.50, 1.000],  0),
    (trash_recycling_bin_A,  [8.15, 1.35, 0.325],  90),
    (trash_recycling_bin_B,  [8.90, 1.35, 0.325],  90),

    (freestanding_planter_A, [9.80, 0.45, 0.425], 180),
    (freestanding_planter_B, [9.80, 6.65, 0.425], 180),
    (freestanding_planter_C, [0.20, 9.60, 0.425],   0),
    (coat_stand_A,           [2.45, 2.50, 0.875],   0),
    (coat_stand_B,           [9.45, 9.45, 0.875], -90),

    (mobile_whiteboard_A,    [2.325, 3.55, 0.925],  0),
    (mobile_whiteboard_B,    [8.45, 9.675, 0.925], -90),

    # Shelves are above the adjacent floor furniture, with clear vertical gaps.
    (wall_shelf_A,           [0.125, 5.75, 1.650],  0),
    (wall_shelf_B,           [2.125, 3.40, 2.250],  0),
    (wall_shelf_C,           [2.125, 4.50, 2.250],  0),

    # North-wall presentation display: no east-wall windows are covered.
    (wall_monitor,           [6.50, 9.965, 1.650], -90),
    (wall_clock,             [4.65, 9.970, 2.100], -90),

    # Acoustic treatment is distributed over solid west and north walls.
    (acoustic_panel_A,       [0.025, 6.55, 1.750],  0),
    (acoustic_panel_B,       [0.025, 7.30, 1.750],  0),
    (acoustic_panel_C,       [0.025, 8.05, 1.750],  0),
    (acoustic_panel_D,       [0.025, 8.80, 1.750],  0),
    (acoustic_panel_E,       [0.70, 9.975, 1.850], -90),
    (acoustic_panel_F,       [1.45, 9.975, 1.850], -90),
    (acoustic_panel_G,       [2.25, 9.975, 1.850], -90),
    (acoustic_panel_H,       [3.05, 9.975, 1.850], -90),
    (acoustic_panel_I,       [3.85, 9.975, 1.850], -90),
    (acoustic_panel_J,       [5.30, 9.975, 1.850], -90),
]

for asset_group, xyz, yaw_degrees in layout_records:
    asset_group[0].position = list(xyz)
    asset_group[0].rotation = [0, 0, radians(yaw_degrees)]

# Important support and facing semantics are registered before layout anchors.
solver.on_top_of(small_planter[0], sideboard_table[0])
solver.on_top_of(throw_pillow[0], lounge_sofa[0])
solver.on_top_of(storage_box_A[0], side_credenda[0])
solver.on_top_of(storage_box_B[0], side_credenda[0])
solver.on_top_of(tray[0], side_credenda[0])
solver.on_top_of(magazine_A[0], lounge_side_table_B[0])
solver.on_top_of(magazine_B[0], sideboard_table[0])

# o0007 and o0039 occupy opposing ends of the table and face one another.
solver.point_towards(meeting_chair_A[0], meeting_chair_F[0])
solver.point_towards(meeting_chair_F[0], meeting_chair_A[0])

for chair_group in (
    meeting_chair_B, meeting_chair_C, meeting_chair_D, meeting_chair_E
):
    solver.point_towards(chair_group[0], conference_table[0])

# o0036 is exactly midway between o0022 and o0018.
# Equal 1.10 m distances, together with a 2.20 m outer-chair spacing,
# preserve the "between" relationship rather than merely clustering chairs.
solver.distance_constraint(
    meeting_chair_E[0], meeting_chair_C[0], 1.10, 1.10, weight=10
)
solver.distance_constraint(
    meeting_chair_E[0], meeting_chair_B[0], 1.10, 1.10, weight=10
)
solver.distance_constraint(
    meeting_chair_B[0], meeting_chair_C[0], 2.20, 2.20, weight=10
)

# Wall attachment, including the explicitly requested freestanding planter.
wall_attachments = [
    (lounge_sofa, 0),
    (side_credenda, 7),
    (sideboard_table, 5),
    (storage_cabinet_A, 4),
    (storage_cabinet_B, 4),
    (freestanding_planter_A, 6),
    (freestanding_planter_B, 6),
    (freestanding_planter_C, 0),
    (mobile_whiteboard_A, 2),
    (mobile_whiteboard_B, 7),
    (wall_shelf_A, 0),
    (wall_shelf_B, 2),
    (wall_shelf_C, 2),
    (wall_monitor, 7),
    (wall_clock, 7),
    (acoustic_panel_A, 0),
    (acoustic_panel_B, 0),
    (acoustic_panel_C, 0),
    (acoustic_panel_D, 0),
    (acoustic_panel_E, 7),
    (acoustic_panel_F, 7),
    (acoustic_panel_G, 7),
    (acoustic_panel_H, 7),
    (acoustic_panel_I, 7),
    (acoustic_panel_J, 7),
]
for asset_group, wall_index in wall_attachments:
    solver.against_wall(asset_group[0], walls[wall_index])

# Give EVERY instance both a position-based and an orientation-based constraint.
# Fixed-coordinate anchors preserve the deliberately separated footprints,
# doorway clearance, shelf heights, and clear access along the window wall.
# The anchors are constraint references, not additional scene furnishings.
for asset_group, xyz, yaw_degrees in layout_records:
    fixed_layout_reference = AssetInstance(
        position=list(xyz),
        rotation=[0, 0, radians(yaw_degrees)]
    )
    solver.distance_constraint(
        asset_group[0], fixed_layout_reference, 0, 0, weight=10
    )
    solver.align_with(asset_group[0], fixed_layout_reference)

# Relational constraints for tabletop objects preserve their chosen offsets.
# Distances include vertical centre separation, as required by the API.
for upper_group, lower_group in (
    (small_planter, sideboard_table),
    (throw_pillow, lounge_sofa),
    (storage_box_A, side_credenda),
    (storage_box_B, side_credenda),
    (tray, side_credenda),
    (magazine_A, lounge_side_table_B),
    (magazine_B, sideboard_table),
):
    centre_distance = sum(
        (upper_group[0].position[axis] - lower_group[0].position[axis]) ** 2
        for axis in range(3)
    ) ** 0.5
    solver.distance_constraint(
        upper_group[0], lower_group[0],
        centre_distance, centre_distance, weight=10
    )
    solver.align_with(upper_group[0], lower_group[0])

solver.constraints = []
coat_stand_B[0].position = [9.449999809265137, 9.449999809265137, 0.875]
coat_stand_B[0].rotation = [0, 0, -1.5613715493341729]
coat_stand_B[0].optimize = 2
acoustic_panel_A[0].position = [0.016124853864312172, 6.550000190734863, 0.6000000238418579]
acoustic_panel_A[0].rotation = [0, 0, 0.0025409193727581954]
acoustic_panel_A[0].optimize = 2
storage_box_B[0].position = [3.129999876022339, 9.78499984741211, 0.9500000476837158]
storage_box_B[0].rotation = [0, 0, -1.5416606754029785]
storage_box_B[0].optimize = 2
storage_box_A[0].position = [2.5399999618530273, 9.78499984741211, 0.9500000476837158]
storage_box_A[0].rotation = [0, 0, -1.5416606754029785]
storage_box_A[0].optimize = 2
acoustic_panel_F[0].position = [1.4500000476837158, 9.983841896057129, 0.6000000238418579]
acoustic_panel_F[0].rotation = [0, 0, -1.5682554083443117]
acoustic_panel_F[0].optimize = 2
meeting_chair_E[0].position = [5.300000190734863, 6.400000095367432, 0.574999988079071]
meeting_chair_E[0].rotation = [0, 0, 0.01884955539881635]
meeting_chair_E[0].optimize = 2
throw_pillow[0].position = [0.4899998903274536, 7.300000190734863, 1.1500000953674316]
throw_pillow[0].rotation = [0, 0, 0.02912872126119664]
throw_pillow[0].optimize = 2
meeting_chair_D[0].position = [7.699999809265137, 6.400000095367432, 0.574999988079071]
meeting_chair_D[0].rotation = [0, 0, -3.1290262823329655]
meeting_chair_D[0].optimize = 2
wall_clock[0].position = [4.650000095367432, 9.978841781616211, 0.20000000298023224]
wall_clock[0].rotation = [0, 0, -1.568255406200039]
wall_clock[0].optimize = 2
lounge_side_table_B[0].position = [0.6499999761581421, 9.050000190734863, 0.2750000059604645]
lounge_side_table_B[0].rotation = [0, 0, 0.01884955539881635]
lounge_side_table_B[0].optimize = 2
meeting_chair_C[0].position = [5.300000190734863, 5.300000190734863, 0.574999988079071]
meeting_chair_C[0].rotation = [0, 0, 0.01884955539881635]
meeting_chair_C[0].optimize = 2
wall_monitor[0].position = [6.5, 9.963157653808594, 0.41999998688697815]
wall_monitor[0].rotation = [0, 0, -1.568255420887615]
wall_monitor[0].optimize = 2
sideboard_table[0].position = [8.0, 0.2150300294160843, 0.4000000059604645]
sideboard_table[0].rotation = [0, 0, 1.5920023203079932]
sideboard_table[0].optimize = 2
acoustic_panel_J[0].position = [5.300000190734863, 9.983841896057129, 0.6000000238418579]
acoustic_panel_J[0].rotation = [0, 0, -1.5682554083443117]
acoustic_panel_J[0].optimize = 2
freestanding_planter_B[0].position = [9.799175262451172, 6.650000095367432, 0.42500001192092896]
freestanding_planter_B[0].rotation = [0, 0, -3.1390517354391343]
freestanding_planter_B[0].optimize = 2
tray[0].position = [3.7100000381469727, 9.78499984741211, 0.8500000238418579]
tray[0].rotation = [0, 0, -1.5416606754029785]
tray[0].optimize = 2
mobile_whiteboard_B[0].position = [8.449999809265137, 9.673095703125, 0.925000011920929]
mobile_whiteboard_B[0].rotation = [0, 0, -1.5682554218097873]
mobile_whiteboard_B[0].optimize = 2
freestanding_planter_A[0].position = [9.799175262451172, 0.44999998807907104, 0.42500001192092896]
freestanding_planter_A[0].rotation = [0, 0, -3.1390517354391343]
freestanding_planter_A[0].optimize = 2
conference_table[0].position = [6.5, 6.400000095367432, 0.375]
conference_table[0].rotation = [0, 0, 0.021991148286022624]
conference_table[0].optimize = 2
lounge_side_table_A[0].position = [0.6499999761581421, 5.650000095367432, 0.2750000059604645]
lounge_side_table_A[0].rotation = [0, 0, 0.00942477746072377]
lounge_side_table_A[0].optimize = 2
storage_cabinet_A[0].position = [6.226142883300781, 0.5, 1.0]
storage_cabinet_A[0].rotation = [0, 0, 0.0025409150842135757]
storage_cabinet_A[0].optimize = 2
trash_recycling_bin_A[0].position = [8.149999618530273, 1.350000023841858, 0.32499998807907104]
trash_recycling_bin_A[0].rotation = [0, 0, 1.5802211042556205]
trash_recycling_bin_A[0].optimize = 2
meeting_chair_F[0].position = [6.5, 8.75, 0.574999988079071]
meeting_chair_F[0].rotation = [0, 0, -1.5550883628776802]
meeting_chair_F[0].optimize = 2
mobile_whiteboard_A[0].position = [2.326904773712158, 3.549999952316284, 0.925000011920929]
mobile_whiteboard_A[0].rotation = [0, 0, 0.0025409049851092386]
mobile_whiteboard_A[0].optimize = 2
wall_shelf_B[0].position = [2.126270055770874, 3.4000000953674316, 0.15000000596046448]
wall_shelf_B[0].rotation = [0, 0, 0.002540913862115027]
wall_shelf_B[0].optimize = 2
coat_stand_A[0].position = [2.450000047683716, 2.5, 0.875]
coat_stand_A[0].rotation = [0, 0, 0.00942477746072377]
coat_stand_A[0].optimize = 2
trash_recycling_bin_B[0].position = [8.899999618530273, 1.350000023841858, 0.32499998807907104]
trash_recycling_bin_B[0].rotation = [0, 0, 1.5802211042556205]
trash_recycling_bin_B[0].optimize = 2
acoustic_panel_E[0].position = [0.699999988079071, 9.983841896057129, 0.6000000238418579]
acoustic_panel_E[0].rotation = [0, 0, -1.5682554083443117]
acoustic_panel_E[0].optimize = 2
acoustic_panel_B[0].position = [0.016124853864312172, 7.300000190734863, 0.6000000238418579]
acoustic_panel_B[0].rotation = [0, 0, 0.0025409193727581954]
acoustic_panel_B[0].optimize = 2
small_planter[0].position = [7.539999961853027, 0.1900000274181366, 1.024999976158142]
small_planter[0].rotation = [0, 0, 1.5999311063485124]
small_planter[0].optimize = 2
freestanding_planter_C[0].position = [0.20082516968250275, 9.600000381469727, 0.42500001192092896]
freestanding_planter_C[0].rotation = [0, 0, 0.002540918150658852]
freestanding_planter_C[0].optimize = 2
acoustic_panel_C[0].position = [0.016124853864312172, 8.050000190734863, 0.6000000238418579]
acoustic_panel_C[0].rotation = [0, 0, 0.0025409193727581954]
acoustic_panel_C[0].optimize = 2
acoustic_panel_H[0].position = [3.049999952316284, 9.983841896057129, 0.6000000238418579]
acoustic_panel_H[0].rotation = [0, 0, -1.5682554083443117]
acoustic_panel_H[0].optimize = 2
meeting_chair_B[0].position = [5.300000190734863, 7.5, 0.574999988079071]
meeting_chair_B[0].rotation = [0, 0, 0.01884955539881635]
meeting_chair_B[0].optimize = 2
wall_shelf_C[0].position = [2.115247964859009, 4.5, 0.15000000596046448]
wall_shelf_C[0].rotation = [0, 0, 0.002540913862115027]
wall_shelf_C[0].optimize = 2
meeting_chair_A[0].position = [6.5, 4.050000190734863, 0.574999988079071]
meeting_chair_A[0].rotation = [0, 0, 1.586504290712113]
meeting_chair_A[0].optimize = 2
lounge_sofa[0].position = [0.4640796184539795, 7.300000190734863, 0.42500001192092896]
lounge_sofa[0].rotation = [0, 0, 0.011873000397976636]
lounge_sofa[0].optimize = 2
storage_cabinet_B[0].position = [6.226142883300781, 1.5, 1.0]
storage_cabinet_B[0].rotation = [0, 0, 0.0025409150842135757]
storage_cabinet_B[0].optimize = 2
acoustic_panel_G[0].position = [2.25, 9.983841896057129, 0.6000000238418579]
acoustic_panel_G[0].rotation = [0, 0, -1.5682554083443117]
acoustic_panel_G[0].optimize = 2
acoustic_panel_I[0].position = [3.8499999046325684, 9.983841896057129, 0.6000000238418579]
acoustic_panel_I[0].rotation = [0, 0, -1.5682554083443117]
acoustic_panel_I[0].optimize = 2
wall_shelf_A[0].position = [0.12627005577087402, 5.75, 0.15000000596046448]
wall_shelf_A[0].rotation = [0, 0, 0.002540912939942025]
wall_shelf_A[0].optimize = 2
magazine_A[0].position = [0.6499999761581421, 9.050000190734863, 0.5649999976158142]
magazine_A[0].rotation = [0, 0, 0.018852558572781168]
magazine_A[0].optimize = 2
side_credenda[0].position = [3.0999999046325684, 9.748441696166992, 0.4000000059604645]
side_credenda[0].rotation = [0, 0, -1.5402564596205857]
side_credenda[0].optimize = 2
acoustic_panel_D[0].position = [0.016124853864312172, 8.800000190734863, 0.6000000238418579]
acoustic_panel_D[0].rotation = [0, 0, 0.0025409193727581954]
acoustic_panel_D[0].optimize = 2
magazine_B[0].position = [8.360000610351562, 0.1900000274181366, 0.8149999976158142]
magazine_B[0].rotation = [0, 0, 1.5999311063485124]
magazine_B[0].optimize = 2

