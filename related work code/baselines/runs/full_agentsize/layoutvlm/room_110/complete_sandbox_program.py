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
throw_pillow = Assets(description="A large white pillow with golden edges.", size=[0.18, 0.55, 0.55], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_A = Assets(description="The plaque has a design in the middle of the board.", size=[0.05, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
lounge_side_table_A = Assets(description="A round wooden table holding a blue and white owl statue.", size=[0.55, 0.55, 0.55], placements=[AssetInstance() for _ in range(1)])
freestanding_planter_A = Assets(description="A wooden planter with some strawberries.", size=[0.35, 0.80, 0.65], placements=[AssetInstance() for _ in range(1)])
mobile_whiteboard_A = Assets(description="A whiteboard with a black marker.", size=[0.60, 1.20, 1.85], placements=[AssetInstance() for _ in range(1)])
wall_shelf_A = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.25, 1.20, 0.30], placements=[AssetInstance() for _ in range(1)])
side_credenda = Assets(description="Long wood cabinet with metal frame and drawers.", size=[0.45, 2.00, 0.80], placements=[AssetInstance() for _ in range(1)])
meeting_chair_A = Assets(description="A black office chair with a tall mesh back.", size=[0.65, 0.65, 1.15], placements=[AssetInstance() for _ in range(1)])
conference_table = Assets(description="A long white table with two black spines.", size=[1.20, 3.20, 0.75], placements=[AssetInstance() for _ in range(1)])
storage_box_A = Assets(description="A red microwave oven.", size=[0.42, 0.50, 0.30], placements=[AssetInstance() for _ in range(1)])
mobile_whiteboard_B = Assets(description="A whiteboard with a black marker.", size=[0.60, 1.20, 1.85], placements=[AssetInstance() for _ in range(1)])
trash_recycling_bin_A = Assets(description="A pair of white drawers in the black dresser.", size=[0.40, 0.75, 0.75], placements=[AssetInstance() for _ in range(1)])
storage_box_B = Assets(description="A red microwave oven.", size=[0.42, 0.50, 0.30], placements=[AssetInstance() for _ in range(1)])
wall_shelf_B = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.25, 1.20, 0.30], placements=[AssetInstance() for _ in range(1)])
small_planter = Assets(description="A plant sitting in a round flower pot.", size=[0.28, 0.28, 0.40], placements=[AssetInstance() for _ in range(1)])
wall_monitor = Assets(description="An image of a mountain lake in a white frame.", size=[0.08, 1.40, 0.80], placements=[AssetInstance() for _ in range(1)])
freestanding_planter_B = Assets(description="A wooden planter with some strawberries.", size=[0.35, 0.80, 0.65], placements=[AssetInstance() for _ in range(1)])
magazine_A = Assets(description="A light brown hardback book with atom depicted in gold on the cover.", size=[0.30, 0.22, 0.03], placements=[AssetInstance() for _ in range(1)])
meeting_chair_B = Assets(description="A black office chair with a tall mesh back.", size=[0.65, 0.65, 1.15], placements=[AssetInstance() for _ in range(1)])
magazine_B = Assets(description="A light brown hardback book with atom depicted in gold on the cover.", size=[0.30, 0.22, 0.03], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_B = Assets(description="The plaque has a design in the middle of the board.", size=[0.05, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_C = Assets(description="The plaque has a design in the middle of the board.", size=[0.05, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
meeting_chair_C = Assets(description="A black office chair with a tall mesh back.", size=[0.65, 0.65, 1.15], placements=[AssetInstance() for _ in range(1)])
lounge_sofa = Assets(description="A grey three seater sofa.", size=[0.90, 2.20, 0.85], placements=[AssetInstance() for _ in range(1)])
freestanding_planter_C = Assets(description="A wooden planter with some strawberries.", size=[0.35, 0.80, 0.65], placements=[AssetInstance() for _ in range(1)])
coat_stand_A = Assets(description="The coatrack is wooden with a round bottom.", size=[0.50, 0.50, 1.80], placements=[AssetInstance() for _ in range(1)])
lounge_side_table_B = Assets(description="A round wooden table holding a blue and white owl statue.", size=[0.55, 0.55, 0.55], placements=[AssetInstance() for _ in range(1)])
coat_stand_B = Assets(description="The coatrack is wooden with a round bottom.", size=[0.50, 0.50, 1.80], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_D = Assets(description="The plaque has a design in the middle of the board.", size=[0.05, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
trash_recycling_bin_B = Assets(description="A pair of white drawers in the black dresser.", size=[0.40, 0.75, 0.75], placements=[AssetInstance() for _ in range(1)])
wall_shelf_C = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.25, 1.20, 0.30], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_E = Assets(description="The plaque has a design in the middle of the board.", size=[0.05, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
sideboard_table = Assets(description="A long narrow wooden table on metal legs.", size=[0.45, 1.80, 0.80], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_F = Assets(description="The plaque has a design in the middle of the board.", size=[0.05, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
meeting_chair_D = Assets(description="A black office chair with a tall mesh back.", size=[0.65, 0.65, 1.15], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_G = Assets(description="The plaque has a design in the middle of the board.", size=[0.05, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
meeting_chair_E = Assets(description="A black office chair with a tall mesh back.", size=[0.65, 0.65, 1.15], placements=[AssetInstance() for _ in range(1)])
storage_cabinet_A = Assets(description="A rectangular set of five dark gray shelves with two drawers beneath them.", size=[0.45, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
storage_cabinet_B = Assets(description="A rectangular set of five dark gray shelves with two drawers beneath them.", size=[0.45, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
meeting_chair_F = Assets(description="A black office chair with a tall mesh back.", size=[0.65, 0.65, 1.15], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_H = Assets(description="The plaque has a design in the middle of the board.", size=[0.05, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_I = Assets(description="The plaque has a design in the middle of the board.", size=[0.05, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_J = Assets(description="The plaque has a design in the middle of the board.", size=[0.05, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
tray = Assets(description="Carved brown tray with handle and tall sides.", size=[0.35, 0.50, 0.15], placements=[AssetInstance() for _ in range(1)])
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

throw_pillow[0].position = [2.265340783848001, 6.61659958288567, 0.275]
throw_pillow[0].rotation = [0, 0, 0]
acoustic_panel_A[0].position = [9.942084205940256, 0.8495638600798838, 0.6]
acoustic_panel_A[0].rotation = [0, 0, 0]
lounge_side_table_A[0].position = [6.314227787600548, 0.4845574842375011, 0.275]
lounge_side_table_A[0].rotation = [0, 0, 0]
freestanding_planter_A[0].position = [4.052165152122752, 9.264393608750645, 0.325]
freestanding_planter_A[0].rotation = [0, 0, 0]
mobile_whiteboard_A[0].position = [6.207232560128064, 3.574949882322586, 0.925]
mobile_whiteboard_A[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [1.5445925460384446, 7.134489317816791, 0.15]
wall_shelf_A[0].rotation = [0, 0, 0]
side_credenda[0].position = [5.059456167552935, 9.513783318474653, 0.4]
side_credenda[0].rotation = [0, 0, 0]
meeting_chair_A[0].position = [2.3683319578923347, 7.166684269007329, 0.575]
meeting_chair_A[0].rotation = [0, 0, 0]
conference_table[0].position = [7.464664780822106, 4.33072702063121, 0.375]
conference_table[0].rotation = [0, 0, 0]
storage_box_A[0].position = [0.4463416373639717, 5.151317756204086, 0.15]
storage_box_A[0].rotation = [0, 0, 0]
mobile_whiteboard_B[0].position = [3.0453988072297635, 9.369102597592644, 0.925]
mobile_whiteboard_B[0].rotation = [0, 0, 0]
trash_recycling_bin_A[0].position = [9.845142337114451, 0.9597095536352918, 0.375]
trash_recycling_bin_A[0].rotation = [0, 0, 0]
storage_box_B[0].position = [9.728996912378372, 5.354699499539587, 0.15]
storage_box_B[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [8.810289810705372, 1.467362694747073, 0.15]
wall_shelf_B[0].rotation = [0, 0, 0]
small_planter[0].position = [8.02112542557753, 5.6728477121338825, 0.2]
small_planter[0].rotation = [0, 0, 0]
wall_monitor[0].position = [4.722872484280224, 8.969709352388529, 0.4]
wall_monitor[0].rotation = [0, 0, 0]
freestanding_planter_B[0].position = [7.1311639644075795, 3.3631954661021215, 0.325]
freestanding_planter_B[0].rotation = [0, 0, 0]
magazine_A[0].position = [6.044889231843575, 4.734083932426466, 0.015]
magazine_A[0].rotation = [0, 0, 0]
meeting_chair_B[0].position = [8.997742659461384, 5.165004945463134, 0.575]
meeting_chair_B[0].rotation = [0, 0, 0]
magazine_B[0].position = [4.323420163238177, 9.908372745159564, 0.015]
magazine_B[0].rotation = [0, 0, 0]
acoustic_panel_B[0].position = [8.791651946791054, 1.0376488451047172, 0.6]
acoustic_panel_B[0].rotation = [0, 0, 0]
acoustic_panel_C[0].position = [6.439459229662582, 3.085865753238588, 0.6]
acoustic_panel_C[0].rotation = [0, 0, 0]
meeting_chair_C[0].position = [9.68380105033046, 0.9340527574939816, 0.575]
meeting_chair_C[0].rotation = [0, 0, 0]
lounge_sofa[0].position = [9.552485064197251, 2.734243327638617, 0.425]
lounge_sofa[0].rotation = [0, 0, 0]
freestanding_planter_C[0].position = [8.163052837218551, 1.215202562119414, 0.325]
freestanding_planter_C[0].rotation = [0, 0, 0]
coat_stand_A[0].position = [5.426670271003946, 8.868471308531495, 0.9]
coat_stand_A[0].rotation = [0, 0, 0]
lounge_side_table_B[0].position = [7.337546713808912, 8.704753573293555, 0.275]
lounge_side_table_B[0].rotation = [0, 0, 0]
coat_stand_B[0].position = [7.069417654651, 4.675548370668804, 0.9]
coat_stand_B[0].rotation = [0, 0, 0]
acoustic_panel_D[0].position = [2.846943455020763, 4.841873866617918, 0.6]
acoustic_panel_D[0].rotation = [0, 0, 0]
trash_recycling_bin_B[0].position = [9.885232152160908, 8.046409881285983, 0.375]
trash_recycling_bin_B[0].rotation = [0, 0, 0]
wall_shelf_C[0].position = [3.851040975184976, 5.939531240312704, 0.15]
wall_shelf_C[0].rotation = [0, 0, 0]
acoustic_panel_E[0].position = [1.1894282051904614, 9.710574937030197, 0.6]
acoustic_panel_E[0].rotation = [0, 0, 0]
sideboard_table[0].position = [6.322449795730255, 2.7835664756664356, 0.4]
sideboard_table[0].rotation = [0, 0, 0]
acoustic_panel_F[0].position = [6.245464287213391, 5.768418057987347, 0.6]
acoustic_panel_F[0].rotation = [0, 0, 0]
meeting_chair_D[0].position = [3.145741194053141, 3.7326980962399983, 0.575]
meeting_chair_D[0].rotation = [0, 0, 0]
acoustic_panel_G[0].position = [8.727696847610877, 9.42361296803166, 0.6]
acoustic_panel_G[0].rotation = [0, 0, 0]
meeting_chair_E[0].position = [5.087841669701845, 2.813548179841223, 0.575]
meeting_chair_E[0].rotation = [0, 0, 0]
storage_cabinet_A[0].position = [2.220560905657367, 2.835933756679502, 0.9]
storage_cabinet_A[0].rotation = [0, 0, 0]
storage_cabinet_B[0].position = [4.980273501169562, 5.360148477071269, 0.9]
storage_cabinet_B[0].rotation = [0, 0, 0]
meeting_chair_F[0].position = [9.067379651393697, 9.352882241923329, 0.575]
meeting_chair_F[0].rotation = [0, 0, 0]
acoustic_panel_H[0].position = [4.7337793749196315, 8.172144921222076, 0.6]
acoustic_panel_H[0].rotation = [0, 0, 0]
acoustic_panel_I[0].position = [8.09575971101004, 0.9074285519154324, 0.6]
acoustic_panel_I[0].rotation = [0, 0, 0]
acoustic_panel_J[0].position = [0.23565092039194102, 8.617168705744241, 0.6]
acoustic_panel_J[0].rotation = [0, 0, 0]
tray[0].position = [9.995242269105399, 4.516069677593323, 0.075]
tray[0].rotation = [0, 0, 0]
wall_clock[0].position = [6.014000761825285, 7.845638425966336, 0.2]
wall_clock[0].rotation = [0, 0, 0]
throw_pillow[0].position = [2.265340783848001, 6.61659958288567, 0.275]
throw_pillow[0].rotation = [0, 0, 0]
acoustic_panel_A[0].position = [9.942084205940256, 0.8495638600798838, 0.6]
acoustic_panel_A[0].rotation = [0, 0, 0]
lounge_side_table_A[0].position = [6.314227787600548, 0.4845574842375011, 0.275]
lounge_side_table_A[0].rotation = [0, 0, 0]
freestanding_planter_A[0].position = [4.052165152122752, 9.264393608750645, 0.325]
freestanding_planter_A[0].rotation = [0, 0, 0]
mobile_whiteboard_A[0].position = [6.207232560128064, 3.574949882322586, 0.925]
mobile_whiteboard_A[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [1.5445925460384446, 7.134489317816791, 0.15]
wall_shelf_A[0].rotation = [0, 0, 0]
side_credenda[0].position = [5.059456167552935, 9.513783318474653, 0.4]
side_credenda[0].rotation = [0, 0, 0]
meeting_chair_A[0].position = [2.3683319578923347, 7.166684269007329, 0.575]
meeting_chair_A[0].rotation = [0, 0, 0]
conference_table[0].position = [7.464664780822106, 4.33072702063121, 0.375]
conference_table[0].rotation = [0, 0, 0]
storage_box_A[0].position = [0.4463416373639717, 5.151317756204086, 0.15]
storage_box_A[0].rotation = [0, 0, 0]
mobile_whiteboard_B[0].position = [3.0453988072297635, 9.369102597592644, 0.925]
mobile_whiteboard_B[0].rotation = [0, 0, 0]
trash_recycling_bin_A[0].position = [9.845142337114451, 0.9597095536352918, 0.375]
trash_recycling_bin_A[0].rotation = [0, 0, 0]
storage_box_B[0].position = [9.728996912378372, 5.354699499539587, 0.15]
storage_box_B[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [8.810289810705372, 1.467362694747073, 0.15]
wall_shelf_B[0].rotation = [0, 0, 0]
small_planter[0].position = [8.02112542557753, 5.6728477121338825, 0.2]
small_planter[0].rotation = [0, 0, 0]
wall_monitor[0].position = [4.722872484280224, 8.969709352388529, 0.4]
wall_monitor[0].rotation = [0, 0, 0]
freestanding_planter_B[0].position = [7.1311639644075795, 3.3631954661021215, 0.325]
freestanding_planter_B[0].rotation = [0, 0, 0]
magazine_A[0].position = [6.044889231843575, 4.734083932426466, 0.015]
magazine_A[0].rotation = [0, 0, 0]
meeting_chair_B[0].position = [8.997742659461384, 5.165004945463134, 0.575]
meeting_chair_B[0].rotation = [0, 0, 0]
magazine_B[0].position = [4.323420163238177, 9.908372745159564, 0.015]
magazine_B[0].rotation = [0, 0, 0]
acoustic_panel_B[0].position = [8.791651946791054, 1.0376488451047172, 0.6]
acoustic_panel_B[0].rotation = [0, 0, 0]
acoustic_panel_C[0].position = [6.439459229662582, 3.085865753238588, 0.6]
acoustic_panel_C[0].rotation = [0, 0, 0]
meeting_chair_C[0].position = [9.68380105033046, 0.9340527574939816, 0.575]
meeting_chair_C[0].rotation = [0, 0, 0]
lounge_sofa[0].position = [9.552485064197251, 2.734243327638617, 0.425]
lounge_sofa[0].rotation = [0, 0, 0]
freestanding_planter_C[0].position = [8.163052837218551, 1.215202562119414, 0.325]
freestanding_planter_C[0].rotation = [0, 0, 0]
coat_stand_A[0].position = [5.426670271003946, 8.868471308531495, 0.9]
coat_stand_A[0].rotation = [0, 0, 0]
lounge_side_table_B[0].position = [7.337546713808912, 8.704753573293555, 0.275]
lounge_side_table_B[0].rotation = [0, 0, 0]
coat_stand_B[0].position = [7.069417654651, 4.675548370668804, 0.9]
coat_stand_B[0].rotation = [0, 0, 0]
acoustic_panel_D[0].position = [2.846943455020763, 4.841873866617918, 0.6]
acoustic_panel_D[0].rotation = [0, 0, 0]
trash_recycling_bin_B[0].position = [9.885232152160908, 8.046409881285983, 0.375]
trash_recycling_bin_B[0].rotation = [0, 0, 0]
wall_shelf_C[0].position = [3.851040975184976, 5.939531240312704, 0.15]
wall_shelf_C[0].rotation = [0, 0, 0]
acoustic_panel_E[0].position = [1.1894282051904614, 9.710574937030197, 0.6]
acoustic_panel_E[0].rotation = [0, 0, 0]
sideboard_table[0].position = [6.322449795730255, 2.7835664756664356, 0.4]
sideboard_table[0].rotation = [0, 0, 0]
acoustic_panel_F[0].position = [6.245464287213391, 5.768418057987347, 0.6]
acoustic_panel_F[0].rotation = [0, 0, 0]
meeting_chair_D[0].position = [3.145741194053141, 3.7326980962399983, 0.575]
meeting_chair_D[0].rotation = [0, 0, 0]
acoustic_panel_G[0].position = [8.727696847610877, 9.42361296803166, 0.6]
acoustic_panel_G[0].rotation = [0, 0, 0]
meeting_chair_E[0].position = [5.087841669701845, 2.813548179841223, 0.575]
meeting_chair_E[0].rotation = [0, 0, 0]
storage_cabinet_A[0].position = [2.220560905657367, 2.835933756679502, 0.9]
storage_cabinet_A[0].rotation = [0, 0, 0]
storage_cabinet_B[0].position = [4.980273501169562, 5.360148477071269, 0.9]
storage_cabinet_B[0].rotation = [0, 0, 0]
meeting_chair_F[0].position = [9.067379651393697, 9.352882241923329, 0.575]
meeting_chair_F[0].rotation = [0, 0, 0]
acoustic_panel_H[0].position = [4.7337793749196315, 8.172144921222076, 0.6]
acoustic_panel_H[0].rotation = [0, 0, 0]
acoustic_panel_I[0].position = [8.09575971101004, 0.9074285519154324, 0.6]
acoustic_panel_I[0].rotation = [0, 0, 0]
acoustic_panel_J[0].position = [0.23565092039194102, 8.617168705744241, 0.6]
acoustic_panel_J[0].rotation = [0, 0, 0]
tray[0].position = [9.995242269105399, 4.516069677593323, 0.075]
tray[0].rotation = [0, 0, 0]
wall_clock[0].position = [6.014000761825285, 7.845638425966336, 0.2]
wall_clock[0].rotation = [0, 0, 0]

solver.constraints = []

# Helper used only to initialize each requested placement without replacing any
# of the asset variables supplied by the scene.
def _set_pose(instance, position, yaw):
    instance.position = position
    instance.rotation = [0, 0, radians(yaw)]


# The conference table occupies the center of the large upper portion of the
# room. Three chairs form its west row, one chair sits on the east side, and
# two chairs occupy the ends. This leaves the doorway approach unobstructed.
_set_pose(conference_table[0], [5.70, 6.80, 0.375], 0)

_set_pose(meeting_chair_C[0], [4.45, 5.50, 0.575], 0)
_set_pose(meeting_chair_E[0], [4.45, 6.80, 0.575], 0)
_set_pose(meeting_chair_B[0], [4.45, 8.10, 0.575], 0)
_set_pose(meeting_chair_D[0], [6.95, 6.80, 0.575], 180)

# These two end chairs face one another across the length of the table.
_set_pose(meeting_chair_A[0], [5.70, 4.65, 0.575], 90)
_set_pose(meeting_chair_F[0], [5.70, 8.95, 0.575], -90)

# Reading material and the serving tray are distributed across the tabletop.
_set_pose(magazine_A[0], [5.50, 5.75, 0.765], 0)
_set_pose(tray[0], [5.70, 6.80, 0.825], 0)
_set_pose(magazine_B[0], [5.90, 7.75, 0.765], 180)

# A lounge grouping occupies the northwest corner, away from the conference
# chairs and from the glazed east wall.
_set_pose(lounge_sofa[0], [2.50, 9.55, 0.425], -90)
_set_pose(throw_pillow[0], [2.50, 9.45, 1.125], -90)
_set_pose(lounge_side_table_A[0], [1.00, 9.35, 0.275], -90)
_set_pose(lounge_side_table_B[0], [4.05, 9.40, 0.275], -90)

# Low storage furniture is placed along the solid west wall. The small planter
# is centered on the sideboard as requested.
_set_pose(trash_recycling_bin_A[0], [0.20, 5.40, 0.375], 0)
_set_pose(side_credenda[0], [0.225, 6.85, 0.40], 0)
_set_pose(sideboard_table[0], [0.225, 8.90, 0.40], 0)
_set_pose(small_planter[0], [0.225, 8.90, 1.00], 0)

# The two mobile boards use the short solid walls beside the entrance and do
# not project into the 1.94 m-wide door approach centered at x=3.84.
_set_pose(mobile_whiteboard_A[0], [2.30, 3.80, 0.925], 0)
_set_pose(mobile_whiteboard_B[0], [1.00, 5.30, 0.925], 90)

# Tall cabinets and two planters use the south wall of the lower wing. Their
# shallow dimensions face the room, preserving a usable circulation aisle.
_set_pose(storage_cabinet_A[0], [6.65, 0.225, 0.90], 90)
_set_pose(storage_cabinet_B[0], [7.65, 0.225, 0.90], 90)
_set_pose(storage_box_A[0], [6.65, 0.225, 1.95], 90)
_set_pose(storage_box_B[0], [7.65, 0.225, 1.95], 90)
_set_pose(freestanding_planter_A[0], [8.55, 0.175, 0.325], 90)
_set_pose(freestanding_planter_B[0], [9.45, 0.175, 0.325], 90)

# The specifically requested o0024 planter (freestanding_planter_C) is against
# the inner x=2 wall. The second bin is against the inner x=6 wall.
_set_pose(freestanding_planter_C[0], [2.175, 2.55, 0.325], 0)
_set_pose(trash_recycling_bin_B[0], [6.20, 1.45, 0.375], 0)

# Coat stands remain accessible in the lower wing without blocking the door or
# any of the three east-wall windows.
_set_pose(coat_stand_A[0], [7.00, 1.40, 0.90], 0)
_set_pose(coat_stand_B[0], [8.00, 1.40, 0.90], 0)

# Wall shelves and display pieces are vertically separated from the floor
# cabinets. They use the window-free west wall.
_set_pose(wall_shelf_A[0], [0.125, 5.70, 1.20], 0)
_set_pose(wall_shelf_B[0], [0.125, 7.00, 1.20], 0)
_set_pose(wall_shelf_C[0], [0.125, 8.30, 1.20], 0)
_set_pose(wall_monitor[0], [0.04, 9.20, 2.00], 0)
_set_pose(wall_clock[0], [0.03, 7.45, 2.50], 0)

# The acoustic panels form an evenly spaced band on the north wall. Keeping
# them off the east wall avoids all three windows.
_set_pose(acoustic_panel_A[0], [3.80, 9.975, 1.60], -90)
_set_pose(acoustic_panel_B[0], [4.45, 9.975, 1.60], -90)
_set_pose(acoustic_panel_C[0], [5.10, 9.975, 1.60], -90)
_set_pose(acoustic_panel_D[0], [5.75, 9.975, 1.60], -90)
_set_pose(acoustic_panel_E[0], [6.40, 9.975, 1.60], -90)
_set_pose(acoustic_panel_F[0], [7.05, 9.975, 1.60], -90)
_set_pose(acoustic_panel_G[0], [7.70, 9.975, 1.60], -90)
_set_pose(acoustic_panel_H[0], [8.35, 9.975, 1.60], -90)
_set_pose(acoustic_panel_I[0], [9.00, 9.975, 1.60], -90)
_set_pose(acoustic_panel_J[0], [9.65, 9.975, 1.60], -90)


# Important support relationships are declared first so they take precedence.
solver.on_top_of(throw_pillow[0], lounge_sofa[0])
solver.on_top_of(magazine_A[0], conference_table[0])
solver.on_top_of(magazine_B[0], conference_table[0])
solver.on_top_of(tray[0], conference_table[0])
solver.on_top_of(storage_box_A[0], storage_cabinet_A[0])
solver.on_top_of(storage_box_B[0], storage_cabinet_B[0])
solver.on_top_of(small_planter[0], sideboard_table[0])

# meeting_chair_E (o0036) is equidistant from—and therefore centered between—
# meeting_chair_C (o0022) and meeting_chair_B (o0018).
solver.distance_constraint(
    meeting_chair_E[0], meeting_chair_C[0], 1.30, 1.30, weight=10
)
solver.distance_constraint(
    meeting_chair_E[0], meeting_chair_B[0], 1.30, 1.30, weight=10
)

# Chair-facing semantics take precedence over generic orientation anchors.
solver.point_towards(meeting_chair_A[0], meeting_chair_F[0])
solver.point_towards(meeting_chair_F[0], meeting_chair_A[0])
solver.point_towards(meeting_chair_B[0], conference_table[0])
solver.point_towards(meeting_chair_C[0], conference_table[0])
solver.point_towards(meeting_chair_D[0], conference_table[0])
solver.point_towards(meeting_chair_E[0], conference_table[0])

# Constraints tying floor furniture and mounted objects to their intended
# walls. The east wall is deliberately unused because it contains the windows.
for _west_item in [
    trash_recycling_bin_A[0],
    side_credenda[0],
    sideboard_table[0],
    wall_shelf_A[0],
    wall_shelf_B[0],
    wall_shelf_C[0],
    wall_monitor[0],
    wall_clock[0],
]:
    solver.against_wall(_west_item, walls[0])

solver.against_wall(mobile_whiteboard_B[0], walls[1])
solver.against_wall(mobile_whiteboard_A[0], walls[2])
solver.against_wall(freestanding_planter_C[0], walls[2])
solver.against_wall(trash_recycling_bin_B[0], walls[4])

for _south_item in [
    storage_cabinet_A[0],
    storage_cabinet_B[0],
    freestanding_planter_A[0],
    freestanding_planter_B[0],
]:
    solver.against_wall(_south_item, walls[5])

solver.against_wall(lounge_sofa[0], walls[7])

for _north_panel in [
    acoustic_panel_A[0],
    acoustic_panel_B[0],
    acoustic_panel_C[0],
    acoustic_panel_D[0],
    acoustic_panel_E[0],
    acoustic_panel_F[0],
    acoustic_panel_G[0],
    acoustic_panel_H[0],
    acoustic_panel_I[0],
    acoustic_panel_J[0],
]:
    solver.against_wall(_north_panel, walls[7])


# Add a strong positional anchor and an orientation anchor for every requested
# asset. Wall, support, and chair-facing constraints above remain the primary
# semantic constraints if the solver must make feasibility adjustments.
_all_layout_instances = [
    throw_pillow[0],
    acoustic_panel_A[0],
    lounge_side_table_A[0],
    freestanding_planter_A[0],
    mobile_whiteboard_A[0],
    wall_shelf_A[0],
    side_credenda[0],
    meeting_chair_A[0],
    conference_table[0],
    storage_box_A[0],
    mobile_whiteboard_B[0],
    trash_recycling_bin_A[0],
    storage_box_B[0],
    wall_shelf_B[0],
    small_planter[0],
    wall_monitor[0],
    freestanding_planter_B[0],
    magazine_A[0],
    meeting_chair_B[0],
    magazine_B[0],
    acoustic_panel_B[0],
    acoustic_panel_C[0],
    meeting_chair_C[0],
    lounge_sofa[0],
    freestanding_planter_C[0],
    coat_stand_A[0],
    lounge_side_table_B[0],
    coat_stand_B[0],
    acoustic_panel_D[0],
    trash_recycling_bin_B[0],
    wall_shelf_C[0],
    acoustic_panel_E[0],
    sideboard_table[0],
    acoustic_panel_F[0],
    meeting_chair_D[0],
    acoustic_panel_G[0],
    meeting_chair_E[0],
    storage_cabinet_A[0],
    storage_cabinet_B[0],
    meeting_chair_F[0],
    acoustic_panel_H[0],
    acoustic_panel_I[0],
    acoustic_panel_J[0],
    tray[0],
    wall_clock[0],
]

for _instance in _all_layout_instances:
    _position_anchor = AssetInstance(position=list(_instance.position))
    _orientation_anchor = AssetInstance(rotation=list(_instance.rotation))
    solver.distance_constraint(
        _instance, _position_anchor, 0.0, 0.0, weight=10
    )
    solver.align_with(_instance, _orientation_anchor)

solver.constraints = []
sideboard_table[0].position = [0.2291090041399002, 8.899999618530273, 0.4000000059604645]
sideboard_table[0].rotation = [0, 0, 0.005651506358483058]
sideboard_table[0].optimize = 2
meeting_chair_B[0].position = [4.449999809265137, 8.100000381469727, 0.574999988079071]
meeting_chair_B[0].rotation = [0, 0, 0.0157079639172164]
meeting_chair_B[0].optimize = 2
acoustic_panel_E[0].position = [6.400000095367432, 9.983841896057129, 0.6000000238418579]
acoustic_panel_E[0].rotation = [0, 0, -1.5682554083443117]
acoustic_panel_E[0].optimize = 2
storage_box_B[0].position = [7.650000095367432, 0.22499999403953552, 1.9499999284744263]
storage_box_B[0].rotation = [0, 0, 1.5833626980517244]
storage_box_B[0].optimize = 2
meeting_chair_D[0].position = [6.949999809265137, 6.800000190734863, 0.574999988079071]
meeting_chair_D[0].rotation = [0, 0, -3.1290262823329655]
meeting_chair_D[0].optimize = 2
wall_shelf_B[0].position = [0.1265241503715515, 7.0, 0.15000000596046448]
wall_shelf_B[0].rotation = [0, 0, 0.002540910495746011]
wall_shelf_B[0].optimize = 2
throw_pillow[0].position = [2.5, 9.449999809265137, 1.125]
throw_pillow[0].rotation = [0, 0, -1.5582299555380688]
throw_pillow[0].optimize = 2
trash_recycling_bin_B[0].position = [6.200952053070068, 1.4500000476837158, 0.375]
trash_recycling_bin_B[0].rotation = [0, 0, 0.0025409172284856325]
trash_recycling_bin_B[0].optimize = 2
wall_monitor[0].position = [0.041778504848480225, 9.199999809265137, 0.4000000059604645]
wall_monitor[0].rotation = [0, 0, 0.002540906207206018]
wall_monitor[0].optimize = 2
freestanding_planter_C[0].position = [2.176015853881836, 2.549999952316284, 0.32499998807907104]
freestanding_planter_C[0].rotation = [0, 0, 0.002540916928559797]
freestanding_planter_C[0].optimize = 2
acoustic_panel_C[0].position = [5.099999904632568, 9.983841896057129, 0.6000000238418579]
acoustic_panel_C[0].rotation = [0, 0, -1.5682554083443117]
acoustic_panel_C[0].optimize = 2
tray[0].position = [5.699999809265137, 6.800000190734863, 0.824999988079071]
tray[0].rotation = [0, 0, 0.01256637125682779]
tray[0].optimize = 2
mobile_whiteboard_A[0].position = [2.3015236854553223, 3.799999952316284, 0.925000011920929]
mobile_whiteboard_A[0].rotation = [0, 0, 0.002540910495746011]
mobile_whiteboard_A[0].optimize = 2
acoustic_panel_H[0].position = [8.350000381469727, 9.983841896057129, 0.6000000238418579]
acoustic_panel_H[0].rotation = [0, 0, -1.5682554083443117]
acoustic_panel_H[0].optimize = 2
acoustic_panel_A[0].position = [3.799999952316284, 9.983841896057129, 0.6000000238418579]
acoustic_panel_A[0].rotation = [0, 0, -1.5682554083443117]
acoustic_panel_A[0].optimize = 2
meeting_chair_F[0].position = [5.699999809265137, 8.949999809265137, 0.574999988079071]
meeting_chair_F[0].rotation = [0, 0, -1.5550883628776802]
meeting_chair_F[0].optimize = 2
lounge_side_table_B[0].position = [4.050000190734863, 9.399999618530273, 0.2750000059604645]
lounge_side_table_B[0].rotation = [0, 0, -1.5613715493341729]
lounge_side_table_B[0].optimize = 2
coat_stand_B[0].position = [8.0, 1.399999976158142, 0.8999999761581421]
coat_stand_B[0].rotation = [0, 0, 0.00942477746072377]
coat_stand_B[0].optimize = 2
acoustic_panel_J[0].position = [9.649999618530273, 9.983841896057129, 0.6000000238418579]
acoustic_panel_J[0].rotation = [0, 0, -1.5682554083443117]
acoustic_panel_J[0].optimize = 2
freestanding_planter_A[0].position = [8.550000190734863, 0.17601580917835236, 0.32499998807907104]
freestanding_planter_A[0].rotation = [0, 0, 1.5733372437234565]
freestanding_planter_A[0].optimize = 2
side_credenda[0].position = [0.2275484800338745, 6.849999904632568, 0.4000000059604645]
side_credenda[0].rotation = [0, 0, 0.002540893963847401]
side_credenda[0].optimize = 2
wall_clock[0].position = [0.020955141633749008, 7.449999809265137, 0.20000000298023224]
wall_clock[0].rotation = [0, 0, 0.002540920594857827]
wall_clock[0].optimize = 2
wall_shelf_C[0].position = [0.1265241503715515, 8.300000190734863, 0.15000000596046448]
wall_shelf_C[0].rotation = [0, 0, 0.002540910495746011]
wall_shelf_C[0].optimize = 2
small_planter[0].position = [0.22499999403953552, 8.899999618530273, 1.0]
small_planter[0].rotation = [0, 0, 0.01256637125682779]
small_planter[0].optimize = 2
magazine_A[0].position = [5.5, 5.75, 0.7649999856948853]
magazine_A[0].rotation = [0, 0, 0.01256637125682779]
magazine_A[0].optimize = 2
storage_cabinet_A[0].position = [6.650000095367432, 0.22753958404064178, 0.8999999761581421]
storage_cabinet_A[0].rotation = [0, 0, 1.576447845710818]
storage_cabinet_A[0].optimize = 2
acoustic_panel_G[0].position = [7.699999809265137, 9.983841896057129, 0.6000000238418579]
acoustic_panel_G[0].rotation = [0, 0, -1.5682554083443117]
acoustic_panel_G[0].optimize = 2
conference_table[0].position = [5.699999809265137, 6.800000190734863, 0.375]
conference_table[0].rotation = [0, 0, 0.031415925765816845]
conference_table[0].optimize = 2
mobile_whiteboard_B[0].position = [1.0, 5.301523685455322, 0.925000011920929]
mobile_whiteboard_B[0].rotation = [0, 0, 1.5733372372906427]
mobile_whiteboard_B[0].optimize = 2
wall_shelf_A[0].position = [0.1265241503715515, 5.699999809265137, 0.15000000596046448]
wall_shelf_A[0].rotation = [0, 0, 0.002540910495746011]
wall_shelf_A[0].optimize = 2
meeting_chair_C[0].position = [4.449999809265137, 5.5, 0.574999988079071]
meeting_chair_C[0].rotation = [0, 0, 0.0157079639172164]
meeting_chair_C[0].optimize = 2
acoustic_panel_I[0].position = [9.0, 9.983841896057129, 0.6000000238418579]
acoustic_panel_I[0].rotation = [0, 0, -1.5682554083443117]
acoustic_panel_I[0].optimize = 2
acoustic_panel_B[0].position = [4.449999809265137, 9.983841896057129, 0.6000000238418579]
acoustic_panel_B[0].rotation = [0, 0, -1.5682554083443117]
acoustic_panel_B[0].optimize = 2
coat_stand_A[0].position = [7.0, 1.399999976158142, 0.8999999761581421]
coat_stand_A[0].rotation = [0, 0, 0.00942477746072377]
coat_stand_A[0].optimize = 2
freestanding_planter_B[0].position = [9.449999809265137, 0.17601580917835236, 0.32499998807907104]
freestanding_planter_B[0].rotation = [0, 0, 1.5733372437234565]
freestanding_planter_B[0].optimize = 2
meeting_chair_A[0].position = [5.699999809265137, 4.650000095367432, 0.574999988079071]
meeting_chair_A[0].rotation = [0, 0, 1.586504290712113]
meeting_chair_A[0].optimize = 2
lounge_side_table_A[0].position = [1.0, 9.350000381469727, 0.2750000059604645]
lounge_side_table_A[0].rotation = [0, 0, -1.5613715493341729]
lounge_side_table_A[0].optimize = 2
lounge_sofa[0].position = [2.5, 9.542778015136719, 0.42500001192092896]
lounge_sofa[0].rotation = [0, 0, -1.5651448279708695]
lounge_sofa[0].optimize = 2
trash_recycling_bin_A[0].position = [0.2009522169828415, 5.400000095367432, 0.375]
trash_recycling_bin_A[0].rotation = [0, 0, 0.002540918150658852]
trash_recycling_bin_A[0].optimize = 2
acoustic_panel_F[0].position = [7.050000190734863, 9.983841896057129, 0.6000000238418579]
acoustic_panel_F[0].rotation = [0, 0, -1.5682554083443117]
acoustic_panel_F[0].optimize = 2
storage_box_A[0].position = [6.650000095367432, 0.22499999403953552, 1.9499999284744263]
storage_box_A[0].rotation = [0, 0, 1.5833626980517244]
storage_box_A[0].optimize = 2
meeting_chair_E[0].position = [4.449999809265137, 6.800000190734863, 0.574999988079071]
meeting_chair_E[0].rotation = [0, 0, 0.01884955539881635]
meeting_chair_E[0].optimize = 2
storage_cabinet_B[0].position = [7.650000095367432, 0.22753958404064178, 0.8999999761581421]
storage_cabinet_B[0].rotation = [0, 0, 1.576447845710818]
storage_cabinet_B[0].optimize = 2
acoustic_panel_D[0].position = [5.75, 9.983841896057129, 0.6000000238418579]
acoustic_panel_D[0].rotation = [0, 0, -1.5682554083443117]
acoustic_panel_D[0].optimize = 2
magazine_B[0].position = [5.900000095367432, 7.75, 0.7649999856948853]
magazine_B[0].rotation = [0, 0, -3.1290262823329655]
magazine_B[0].optimize = 2

