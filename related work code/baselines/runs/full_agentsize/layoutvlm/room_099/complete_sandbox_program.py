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
    Wall(corner1=[0.00, 3.00, 0.00], corner2=[3.00, 3.00, 0.00]),
    Wall(corner1=[3.00, 3.00, 0.00], corner2=[3.00, 0.00, 0.00]),
    Wall(corner1=[3.00, 0.00, 0.00], corner2=[5.00, 0.00, 0.00]),
    Wall(corner1=[5.00, 0.00, 0.00], corner2=[5.00, 4.00, 0.00]),
    Wall(corner1=[5.00, 4.00, 0.00], corner2=[2.00, 4.00, 0.00]),
    Wall(corner1=[2.00, 4.00, 0.00], corner2=[2.00, 7.00, 0.00]),
    Wall(corner1=[2.00, 7.00, 0.00], corner2=[0.00, 7.00, 0.00]),
    Wall(corner1=[0.00, 7.00, 0.00], corner2=[0.00, 3.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
plant_floor = Assets(description="A potted plant with big green leaves.", size=[0.65, 0.65, 1.35], placements=[AssetInstance() for _ in range(1)])
pen_A = Assets(description="A long white mechanical pencil.", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_set_A = Assets(description="A wood sculpture that is to be hung on the wall.", size=[0.08, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
huddle_table = Assets(description="huddle table", size=[0.90, 1.80, 0.74], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_set_B = Assets(description="A wood sculpture that is to be hung on the wall.", size=[0.08, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
glass_water_carafe = Assets(description="A blue glass bottle.", size=[0.12, 0.12, 0.30], placements=[AssetInstance() for _ in range(1)])
conference_speakerphone = Assets(description="An old school black discman cd player with a cord plugged into side with a orange foam headset.", size=[0.25, 0.25, 0.07], placements=[AssetInstance() for _ in range(1)])
pen_B = Assets(description="A pencil with a blue cap on the end of it.", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_set_C = Assets(description="A wood sculpture that is to be hung on the wall.", size=[0.08, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
coat_stand = Assets(description="A coat that's different shades of blue on a black four legged stand.", size=[0.55, 0.55, 1.75], placements=[AssetInstance() for _ in range(1)])
mobile_whiteboard = Assets(description="A whiteboard with a black marker.", size=[0.60, 1.20, 1.85], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_set_D = Assets(description="A wood sculpture that is to be hung on the wall.", size=[0.08, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
wall_monitor = Assets(description="A boxy black television with bright white screen.", size=[0.08, 1.25, 0.72], placements=[AssetInstance() for _ in range(1)])
wall_shelf_A = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.25, 0.90, 0.20], placements=[AssetInstance() for _ in range(1)])
whiteboard = Assets(description="A white rectangular poster with black blue and orange marks and irregular writing.", size=[0.04, 1.50, 0.90], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_set_E = Assets(description="A wood sculpture that is to be hung on the wall.", size=[0.08, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
storage_cabinet = Assets(description="storage cabinet", size=[0.45, 0.90, 1.10], placements=[AssetInstance() for _ in range(1)])
pen_C = Assets(description="a green pen with a purple tip.", size=[0.01, 0.14, 0.01], placements=[AssetInstance() for _ in range(1)])
table_plant = Assets(description="a vase with flowers, scissors, and a snail on a shelf.", size=[0.22, 0.28, 0.42], placements=[AssetInstance() for _ in range(1)])
pen_D = Assets(description="A blue marker with a cup on the top of it.", size=[0.02, 0.14, 0.02], placements=[AssetInstance() for _ in range(1)])
notebook_A = Assets(description="A brown book with silver corners.", size=[0.16, 0.22, 0.02], placements=[AssetInstance() for _ in range(1)])
side_credenza = Assets(description="A bunch of white cubby shelves.", size=[0.45, 1.50, 0.80], placements=[AssetInstance() for _ in range(1)])
wall_shelf_B = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.25, 0.90, 0.20], placements=[AssetInstance() for _ in range(1)])
huddle_chair = Assets(description="An office chair on wheels with a black fabric seat.", size=[0.62, 0.62, 0.95], placements=[AssetInstance() for _ in range(1)])
notebook_B = Assets(description="A red notepad decorated with a slug in the lower corner.", size=[0.15, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
lounge_chair = Assets(description="A black chair with four legs.", size=[0.75, 0.70, 0.80], placements=[AssetInstance() for _ in range(1)])
pen_E = Assets(description="red and blue pen.", size=[0.01, 0.14, 0.01], placements=[AssetInstance() for _ in range(1)])
notebook_C = Assets(description="A red and yellow notepad with metal spirals reading 'dolphin ko's notepad'.", size=[0.16, 0.22, 0.02], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_set_F = Assets(description="A wood sculpture that is to be hung on the wall.", size=[0.08, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_set_G = Assets(description="A wood sculpture that is to be hung on the wall.", size=[0.08, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
notebook_D = Assets(description="A pink spiral notebook with a green leaf on it.", size=[0.17, 0.22, 0.02], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_set_H = Assets(description="A wood sculpture that is to be hung on the wall.", size=[0.08, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])

plant_floor[0].instance_id = 'plant_floor_0'
pen_A[0].instance_id = 'pen_A_0'
acoustic_panel_set_A[0].instance_id = 'acoustic_panel_set_A_0'
huddle_table[0].instance_id = 'huddle_table_0'
acoustic_panel_set_B[0].instance_id = 'acoustic_panel_set_B_0'
glass_water_carafe[0].instance_id = 'glass_water_carafe_0'
conference_speakerphone[0].instance_id = 'conference_speakerphone_0'
pen_B[0].instance_id = 'pen_B_0'
acoustic_panel_set_C[0].instance_id = 'acoustic_panel_set_C_0'
coat_stand[0].instance_id = 'coat_stand_0'
mobile_whiteboard[0].instance_id = 'mobile_whiteboard_0'
acoustic_panel_set_D[0].instance_id = 'acoustic_panel_set_D_0'
wall_monitor[0].instance_id = 'wall_monitor_0'
wall_shelf_A[0].instance_id = 'wall_shelf_A_0'
whiteboard[0].instance_id = 'whiteboard_0'
acoustic_panel_set_E[0].instance_id = 'acoustic_panel_set_E_0'
storage_cabinet[0].instance_id = 'storage_cabinet_0'
pen_C[0].instance_id = 'pen_C_0'
table_plant[0].instance_id = 'table_plant_0'
pen_D[0].instance_id = 'pen_D_0'
notebook_A[0].instance_id = 'notebook_A_0'
side_credenza[0].instance_id = 'side_credenza_0'
wall_shelf_B[0].instance_id = 'wall_shelf_B_0'
huddle_chair[0].instance_id = 'huddle_chair_0'
notebook_B[0].instance_id = 'notebook_B_0'
lounge_chair[0].instance_id = 'lounge_chair_0'
pen_E[0].instance_id = 'pen_E_0'
notebook_C[0].instance_id = 'notebook_C_0'
acoustic_panel_set_F[0].instance_id = 'acoustic_panel_set_F_0'
acoustic_panel_set_G[0].instance_id = 'acoustic_panel_set_G_0'
notebook_D[0].instance_id = 'notebook_D_0'
acoustic_panel_set_H[0].instance_id = 'acoustic_panel_set_H_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

plant_floor[0].position = [4.336639595882687, 0.37700806420915234, 0.675]
plant_floor[0].rotation = [0, 0, 0]
pen_A[0].position = [4.805732535039256, 3.38175846049894, 0.005]
pen_A[0].rotation = [0, 0, 0]
acoustic_panel_set_A[0].position = [0.6622558462685191, 3.7576267864794843, 0.6]
acoustic_panel_set_A[0].rotation = [0, 0, 0]
huddle_table[0].position = [1.8313108329194316, 3.1501359602376686, 0.37]
huddle_table[0].rotation = [0, 0, 0]
acoustic_panel_set_B[0].position = [1.1784353524495232, 4.270481222708472, 0.6]
acoustic_panel_set_B[0].rotation = [0, 0, 0]
glass_water_carafe[0].position = [1.3486084853913387, 3.099420614340432, 0.15]
glass_water_carafe[0].rotation = [0, 0, 0]
conference_speakerphone[0].position = [4.853736757684267, 2.2440490964964614, 0.035]
conference_speakerphone[0].rotation = [0, 0, 0]
pen_B[0].position = [0.2383207395637732, 6.35043872134061, 0.005]
pen_B[0].rotation = [0, 0, 0]
acoustic_panel_set_C[0].position = [0.5888208629831104, 5.656256099542702, 0.6]
acoustic_panel_set_C[0].rotation = [0, 0, 0]
coat_stand[0].position = [2.9248370861807524, 3.816412412744378, 0.875]
coat_stand[0].rotation = [0, 0, 0]
mobile_whiteboard[0].position = [4.135400531355024, 3.9001183703940763, 0.925]
mobile_whiteboard[0].rotation = [0, 0, 0]
acoustic_panel_set_D[0].position = [1.805639233472736, 3.1413521892990683, 0.6]
acoustic_panel_set_D[0].rotation = [0, 0, 0]
wall_monitor[0].position = [3.8349629171213566, 3.760899651888296, 0.36]
wall_monitor[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [0.5720794598599599, 4.940713053721227, 0.1]
wall_shelf_A[0].rotation = [0, 0, 0]
whiteboard[0].position = [4.084105993879752, 0.34988971047664585, 0.45]
whiteboard[0].rotation = [0, 0, 0]
acoustic_panel_set_E[0].position = [1.6890130288638634, 4.393211946879254, 0.6]
acoustic_panel_set_E[0].rotation = [0, 0, 0]
storage_cabinet[0].position = [1.2410043558769464, 4.227524751355477, 0.55]
storage_cabinet[0].rotation = [0, 0, 0]
pen_C[0].position = [1.2616580573742597, 6.935129068061512, 0.005]
pen_C[0].rotation = [0, 0, 0]
table_plant[0].position = [1.7179218565512944, 6.041287609090699, 0.21]
table_plant[0].rotation = [0, 0, 0]
pen_D[0].position = [2.721858379111628, 3.8629311901768073, 0.01]
pen_D[0].rotation = [0, 0, 0]
notebook_A[0].position = [3.260942505224488, 0.4404599694630914, 0.01]
notebook_A[0].rotation = [0, 0, 0]
side_credenza[0].position = [4.078038938030567, 2.2892910643875846, 0.4]
side_credenza[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [0.11879763571271407, 5.524730646252885, 0.1]
wall_shelf_B[0].rotation = [0, 0, 0]
huddle_chair[0].position = [1.185781293722254, 3.941488324686671, 0.475]
huddle_chair[0].rotation = [0, 0, 0]
notebook_B[0].position = [4.692007481125015, 2.7560813029566047, 0.0075]
notebook_B[0].rotation = [0, 0, 0]
lounge_chair[0].position = [4.370073765627564, 2.1218917607569847, 0.4]
lounge_chair[0].rotation = [0, 0, 0]
pen_E[0].position = [3.3732296945768176, 3.9346783030470807, 0.005]
pen_E[0].rotation = [0, 0, 0]
notebook_C[0].position = [3.5092738727816264, 3.6655035599218486, 0.01]
notebook_C[0].rotation = [0, 0, 0]
acoustic_panel_set_F[0].position = [0.3330211913635073, 6.646940173765268, 0.6]
acoustic_panel_set_F[0].rotation = [0, 0, 0]
acoustic_panel_set_G[0].position = [4.369974091007701, 1.880551355641328, 0.6]
acoustic_panel_set_G[0].rotation = [0, 0, 0]
notebook_D[0].position = [3.835106037205213, 2.9333053562159503, 0.01]
notebook_D[0].rotation = [0, 0, 0]
acoustic_panel_set_H[0].position = [0.8686331580820972, 5.548273620493077, 0.6]
acoustic_panel_set_H[0].rotation = [0, 0, 0]
plant_floor[0].position = [4.336639595882687, 0.37700806420915234, 0.675]
plant_floor[0].rotation = [0, 0, 0]
pen_A[0].position = [4.805732535039256, 3.38175846049894, 0.005]
pen_A[0].rotation = [0, 0, 0]
acoustic_panel_set_A[0].position = [0.6622558462685191, 3.7576267864794843, 0.6]
acoustic_panel_set_A[0].rotation = [0, 0, 0]
huddle_table[0].position = [1.8313108329194316, 3.1501359602376686, 0.37]
huddle_table[0].rotation = [0, 0, 0]
acoustic_panel_set_B[0].position = [1.1784353524495232, 4.270481222708472, 0.6]
acoustic_panel_set_B[0].rotation = [0, 0, 0]
glass_water_carafe[0].position = [1.3486084853913387, 3.099420614340432, 0.15]
glass_water_carafe[0].rotation = [0, 0, 0]
conference_speakerphone[0].position = [4.853736757684267, 2.2440490964964614, 0.035]
conference_speakerphone[0].rotation = [0, 0, 0]
pen_B[0].position = [0.2383207395637732, 6.35043872134061, 0.005]
pen_B[0].rotation = [0, 0, 0]
acoustic_panel_set_C[0].position = [0.5888208629831104, 5.656256099542702, 0.6]
acoustic_panel_set_C[0].rotation = [0, 0, 0]
coat_stand[0].position = [2.9248370861807524, 3.816412412744378, 0.875]
coat_stand[0].rotation = [0, 0, 0]
mobile_whiteboard[0].position = [4.135400531355024, 3.9001183703940763, 0.925]
mobile_whiteboard[0].rotation = [0, 0, 0]
acoustic_panel_set_D[0].position = [1.805639233472736, 3.1413521892990683, 0.6]
acoustic_panel_set_D[0].rotation = [0, 0, 0]
wall_monitor[0].position = [3.8349629171213566, 3.760899651888296, 0.36]
wall_monitor[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [0.5720794598599599, 4.940713053721227, 0.1]
wall_shelf_A[0].rotation = [0, 0, 0]
whiteboard[0].position = [4.084105993879752, 0.34988971047664585, 0.45]
whiteboard[0].rotation = [0, 0, 0]
acoustic_panel_set_E[0].position = [1.6890130288638634, 4.393211946879254, 0.6]
acoustic_panel_set_E[0].rotation = [0, 0, 0]
storage_cabinet[0].position = [1.2410043558769464, 4.227524751355477, 0.55]
storage_cabinet[0].rotation = [0, 0, 0]
pen_C[0].position = [1.2616580573742597, 6.935129068061512, 0.005]
pen_C[0].rotation = [0, 0, 0]
table_plant[0].position = [1.7179218565512944, 6.041287609090699, 0.21]
table_plant[0].rotation = [0, 0, 0]
pen_D[0].position = [2.721858379111628, 3.8629311901768073, 0.01]
pen_D[0].rotation = [0, 0, 0]
notebook_A[0].position = [3.260942505224488, 0.4404599694630914, 0.01]
notebook_A[0].rotation = [0, 0, 0]
side_credenza[0].position = [4.078038938030567, 2.2892910643875846, 0.4]
side_credenza[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [0.11879763571271407, 5.524730646252885, 0.1]
wall_shelf_B[0].rotation = [0, 0, 0]
huddle_chair[0].position = [1.185781293722254, 3.941488324686671, 0.475]
huddle_chair[0].rotation = [0, 0, 0]
notebook_B[0].position = [4.692007481125015, 2.7560813029566047, 0.0075]
notebook_B[0].rotation = [0, 0, 0]
lounge_chair[0].position = [4.370073765627564, 2.1218917607569847, 0.4]
lounge_chair[0].rotation = [0, 0, 0]
pen_E[0].position = [3.3732296945768176, 3.9346783030470807, 0.005]
pen_E[0].rotation = [0, 0, 0]
notebook_C[0].position = [3.5092738727816264, 3.6655035599218486, 0.01]
notebook_C[0].rotation = [0, 0, 0]
acoustic_panel_set_F[0].position = [0.3330211913635073, 6.646940173765268, 0.6]
acoustic_panel_set_F[0].rotation = [0, 0, 0]
acoustic_panel_set_G[0].position = [4.369974091007701, 1.880551355641328, 0.6]
acoustic_panel_set_G[0].rotation = [0, 0, 0]
notebook_D[0].position = [3.835106037205213, 2.9333053562159503, 0.01]
notebook_D[0].rotation = [0, 0, 0]
acoustic_panel_set_H[0].position = [0.8686331580820972, 5.548273620493077, 0.6]
acoustic_panel_set_H[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed reference points keep the main furniture in the intended functional zones.
# The meeting table is in the lower-right room, leaving the window and the
# circulation path from the door at (2.00, 5.20) unobstructed.
meeting_table_anchor = AssetInstance(position=[4.00, 1.95, 0.37])
mobile_whiteboard_anchor = AssetInstance(position=[3.30, 1.00, 0.925])
huddle_chair_anchor = AssetInstance(position=[4.00, 3.55, 0.475])
lounge_chair_anchor = AssetInstance(position=[2.60, 3.50, 0.40])

plant_anchor = AssetInstance(position=[0.40, 6.55, 0.675])
coat_stand_anchor = AssetInstance(position=[0.35, 5.75, 0.875])
storage_anchor = AssetInstance(position=[1.40, 6.775, 0.55])
credenza_anchor = AssetInstance(position=[0.225, 3.85, 0.40])

# Interior-facing reference points for orientation constraints.
lower_room_center = AssetInstance(position=[4.00, 2.00, 1.00])
upper_room_center = AssetInstance(position=[1.00, 5.00, 1.00])
middle_room_center = AssetInstance(position=[2.50, 3.50, 1.00])

# ---------------------------------------------------------------------------
# Floor furniture
# ---------------------------------------------------------------------------

huddle_table[0].position = [4.00, 1.95, 0.37]
huddle_table[0].rotation = [0, 0, radians(0)]
solver.distance_constraint(
    huddle_table[0], meeting_table_anchor, 0, 0, weight=10
)
solver.point_towards(huddle_table[0], wall_monitor[0])

mobile_whiteboard[0].position = [3.30, 1.00, 0.925]
mobile_whiteboard[0].rotation = [0, 0, radians(0)]
solver.distance_constraint(
    mobile_whiteboard[0], mobile_whiteboard_anchor, 0, 0, weight=10
)
solver.against_wall(mobile_whiteboard[0], walls[1])
solver.point_towards(mobile_whiteboard[0], lower_room_center)

huddle_chair[0].position = [4.00, 3.55, 0.475]
huddle_chair[0].rotation = [0, 0, radians(-90)]
solver.distance_constraint(
    huddle_chair[0], huddle_chair_anchor, 0, 0, weight=10
)
solver.point_towards(huddle_chair[0], huddle_table[0])

lounge_chair[0].position = [2.60, 3.50, 0.40]
lounge_chair[0].rotation = [0, 0, radians(0)]
solver.distance_constraint(
    lounge_chair[0], lounge_chair_anchor, 0, 0, weight=10
)
solver.point_towards(lounge_chair[0], huddle_table[0])

# Furniture in the upper wing is kept against the perimeter so the door
# approach along the right side of that wing remains clear.
side_credenza[0].position = [0.225, 3.85, 0.40]
side_credenza[0].rotation = [0, 0, radians(0)]
solver.distance_constraint(
    side_credenza[0], credenza_anchor, 0, 0, weight=10
)
solver.against_wall(side_credenza[0], walls[7])
solver.point_towards(side_credenza[0], upper_room_center)

coat_stand[0].position = [0.35, 5.75, 0.875]
coat_stand[0].rotation = [0, 0, radians(0)]
solver.distance_constraint(
    coat_stand[0], coat_stand_anchor, 0, 0, weight=10
)
solver.point_towards(coat_stand[0], upper_room_center)

plant_floor[0].position = [0.40, 6.55, 0.675]
plant_floor[0].rotation = [0, 0, radians(0)]
solver.distance_constraint(
    plant_floor[0], plant_anchor, 0, 0, weight=10
)
solver.point_towards(plant_floor[0], upper_room_center)

storage_cabinet[0].position = [1.40, 6.775, 0.55]
storage_cabinet[0].rotation = [0, 0, radians(-90)]
solver.distance_constraint(
    storage_cabinet[0], storage_anchor, 0, 0, weight=10
)
solver.against_wall(storage_cabinet[0], walls[6])
solver.point_towards(storage_cabinet[0], upper_room_center)

# ---------------------------------------------------------------------------
# Wall-mounted equipment
# ---------------------------------------------------------------------------

# Monitor on the east wall of the lower room, opposite the table.
wall_monitor[0].position = [4.96, 2.00, 1.45]
wall_monitor[0].rotation = [0, 0, radians(180)]
solver.distance_constraint(
    wall_monitor[0],
    AssetInstance(position=[4.96, 2.00, 1.45]),
    0, 0, weight=10
)
solver.against_wall(wall_monitor[0], walls[3])
solver.point_towards(wall_monitor[0], lower_room_center)

# Shelves flank the monitor without covering the window on the south wall.
wall_shelf_A[0].position = [4.875, 0.65, 1.35]
wall_shelf_A[0].rotation = [0, 0, radians(180)]
solver.distance_constraint(
    wall_shelf_A[0],
    AssetInstance(position=[4.875, 0.65, 1.35]),
    0, 0, weight=10
)
solver.against_wall(wall_shelf_A[0], walls[3])
solver.point_towards(wall_shelf_A[0], lower_room_center)

wall_shelf_B[0].position = [4.875, 3.35, 1.35]
wall_shelf_B[0].rotation = [0, 0, radians(180)]
solver.distance_constraint(
    wall_shelf_B[0],
    AssetInstance(position=[4.875, 3.35, 1.35]),
    0, 0, weight=10
)
solver.against_wall(wall_shelf_B[0], walls[3])
solver.point_towards(wall_shelf_B[0], lower_room_center)

whiteboard[0].position = [0.02, 5.20, 1.50]
whiteboard[0].rotation = [0, 0, radians(0)]
solver.distance_constraint(
    whiteboard[0],
    AssetInstance(position=[0.02, 5.20, 1.50]),
    0, 0, weight=10
)
solver.against_wall(whiteboard[0], walls[7])
solver.point_towards(whiteboard[0], upper_room_center)

# Three panels are distributed across the north wall.
north_panel_data = [
    (acoustic_panel_set_A[0], [0.35, 6.96, 1.50]),
    (acoustic_panel_set_B[0], [1.00, 6.96, 1.50]),
    (acoustic_panel_set_C[0], [1.65, 6.96, 1.50]),
]
for panel_instance, panel_position in north_panel_data:
    panel_instance.position = panel_position
    panel_instance.rotation = [0, 0, radians(-90)]
    solver.distance_constraint(
        panel_instance,
        AssetInstance(position=panel_position),
        0, 0, weight=10
    )
    solver.against_wall(panel_instance, walls[6])
    solver.point_towards(panel_instance, upper_room_center)

# Three more panels occupy the wall at y=3, facing into the upper/middle area.
south_upper_panel_data = [
    (acoustic_panel_set_D[0], [0.45, 3.04, 1.50]),
    (acoustic_panel_set_E[0], [1.15, 3.04, 1.50]),
    (acoustic_panel_set_F[0], [1.85, 3.04, 1.50]),
]
for panel_instance, panel_position in south_upper_panel_data:
    panel_instance.position = panel_position
    panel_instance.rotation = [0, 0, radians(90)]
    solver.distance_constraint(
        panel_instance,
        AssetInstance(position=panel_position),
        0, 0, weight=10
    )
    solver.against_wall(panel_instance, walls[0])
    solver.point_towards(panel_instance, middle_room_center)

# The final two panels are on the y=4 wall, facing the lower meeting room.
lower_panel_data = [
    (acoustic_panel_set_G[0], [3.35, 3.96, 1.50]),
    (acoustic_panel_set_H[0], [4.15, 3.96, 1.50]),
]
for panel_instance, panel_position in lower_panel_data:
    panel_instance.position = panel_position
    panel_instance.rotation = [0, 0, radians(-90)]
    solver.distance_constraint(
        panel_instance,
        AssetInstance(position=panel_position),
        0, 0, weight=10
    )
    solver.against_wall(panel_instance, walls[4])
    solver.point_towards(panel_instance, lower_room_center)

# ---------------------------------------------------------------------------
# Tabletop objects
# ---------------------------------------------------------------------------

# Each small object is pinned to a separate non-overlapping location and then
# constrained onto the huddle table. The notebook identified as o0020 is
# notebook_A, and is explicitly included here.
tabletop_layout = [
    (glass_water_carafe[0], [3.72, 1.30, 0.89], 0),
    (table_plant[0], [4.18, 1.35, 0.95], 0),
    (conference_speakerphone[0], [4.00, 1.75, 0.775], 0),

    (notebook_A[0], [3.72, 2.15, 0.75], 0),
    (notebook_B[0], [4.00, 2.15, 0.745], 0),
    (notebook_C[0], [4.27, 2.15, 0.75], 0),
    (notebook_D[0], [3.72, 2.55, 0.75], 0),

    (pen_A[0], [3.62, 1.70, 0.745], 0),
    (pen_B[0], [3.75, 1.70, 0.745], 0),
    (pen_C[0], [4.25, 1.72, 0.745], 0),
    (pen_D[0], [4.37, 1.72, 0.75], 0),
    (pen_E[0], [4.15, 2.55, 0.745], 0),
]

for tabletop_instance, tabletop_position, tabletop_angle in tabletop_layout:
    tabletop_instance.position = tabletop_position
    tabletop_instance.rotation = [0, 0, radians(tabletop_angle)]

    # The exact anchor is the position-based constraint for this object.
    solver.distance_constraint(
        tabletop_instance,
        AssetInstance(position=tabletop_position),
        0, 0, weight=10
    )
    solver.on_top_of(tabletop_instance, huddle_table[0])
    solver.align_with(tabletop_instance, huddle_table[0])

solver.constraints = []
huddle_chair[0].position = [4.0, 3.549999952316284, 0.4749999940395355]
huddle_chair[0].rotation = [0, 0, -1.5613715493341729]
huddle_chair[0].optimize = 2
pen_D[0].position = [4.369999885559082, 1.7200000286102295, 0.75]
pen_D[0].rotation = [0, 0, 0.09111058871462283]
pen_D[0].optimize = 2
lounge_chair[0].position = [2.5999999046325684, 3.5, 0.4000000059604645]
lounge_chair[0].rotation = [0, 0, -0.3384507480494602]
lounge_chair[0].optimize = 2
acoustic_panel_set_G[0].position = [3.3499999046325684, 3.960000514984131, 0.6000000238418579]
acoustic_panel_set_G[0].rotation = [0, 0, -1.5707976697796409]
acoustic_panel_set_G[0].optimize = 2
notebook_D[0].position = [3.7200000286102295, 2.549999952316284, 0.75]
notebook_D[0].rotation = [0, 0, 0.09111058871462283]
notebook_D[0].optimize = 2
glass_water_carafe[0].position = [3.7200000286102295, 1.2999999523162842, 0.8899999856948853]
glass_water_carafe[0].rotation = [0, 0, 0.09111058871462283]
glass_water_carafe[0].optimize = 2
wall_shelf_B[0].position = [4.874999523162842, 3.3499999046325684, 0.10000000149011612]
wall_shelf_B[0].rotation = [0, 0, 3.1415913537292215]
wall_shelf_B[0].optimize = 2
acoustic_panel_set_C[0].position = [1.649999976158142, 6.960000514984131, 0.6000000238418579]
acoustic_panel_set_C[0].rotation = [0, 0, -1.570797650973432]
acoustic_panel_set_C[0].optimize = 2
wall_monitor[0].position = [4.9599995613098145, 2.0, 0.36000001430511475]
wall_monitor[0].rotation = [0, 0, -3.1415910119225474]
wall_monitor[0].optimize = 2
acoustic_panel_set_H[0].position = [4.150000095367432, 3.960000514984131, 0.6000000238418579]
acoustic_panel_set_H[0].rotation = [0, 0, -1.5707976697796409]
acoustic_panel_set_H[0].optimize = 2
notebook_A[0].position = [3.7200000286102295, 2.1500000953674316, 0.75]
notebook_A[0].rotation = [0, 0, 0.09111058871462283]
notebook_A[0].optimize = 2
whiteboard[0].position = [0.019999416545033455, 5.199999809265137, 0.44999998807907104]
whiteboard[0].rotation = [0, 0, -1.3419176092478588e-06]
whiteboard[0].optimize = 2
pen_B[0].position = [3.75, 1.7000000476837158, 0.7450000047683716]
pen_B[0].rotation = [0, 0, 0.09111058871462283]
pen_B[0].optimize = 2
table_plant[0].position = [4.179999828338623, 1.350000023841858, 0.949999988079071]
table_plant[0].rotation = [0, 0, 0.09111058871462283]
table_plant[0].optimize = 2
acoustic_panel_set_B[0].position = [1.0, 6.960000514984131, 0.6000000238418579]
acoustic_panel_set_B[0].rotation = [0, 0, -1.570797650973432]
acoustic_panel_set_B[0].optimize = 2
pen_E[0].position = [4.150000095367432, 2.549999952316284, 0.7450000047683716]
pen_E[0].rotation = [0, 0, 0.09111058871462283]
pen_E[0].optimize = 2
pen_A[0].position = [3.619999885559082, 1.7000000476837158, 0.7450000047683716]
pen_A[0].rotation = [0, 0, 0.09111058871462283]
pen_A[0].optimize = 2
mobile_whiteboard[0].position = [3.3000006675720215, 1.0, 0.925000011920929]
mobile_whiteboard[0].rotation = [0, 0, -1.325042788046116e-06]
mobile_whiteboard[0].optimize = 2
side_credenza[0].position = [1.4521174430847168, 3.7754204273223877, 0.4000000059604645]
side_credenza[0].rotation = [0, 0, -1.63235628148598]
side_credenza[0].optimize = 2
notebook_B[0].position = [4.0, 2.1500000953674316, 0.7450000047683716]
notebook_B[0].rotation = [0, 0, 0.09111058871462283]
notebook_B[0].optimize = 2
wall_shelf_A[0].position = [4.874999523162842, 0.6499999761581421, 0.10000000149011612]
wall_shelf_A[0].rotation = [0, 0, 3.1415913537292215]
wall_shelf_A[0].optimize = 2
pen_C[0].position = [4.25, 1.7200000286102295, 0.7450000047683716]
pen_C[0].rotation = [0, 0, 0.09111058871462283]
pen_C[0].optimize = 2
acoustic_panel_set_F[0].position = [1.850000023841858, 3.039999485015869, 0.6000000238418579]
acoustic_panel_set_F[0].rotation = [0, 0, 1.5707949837287574]
acoustic_panel_set_F[0].optimize = 2
acoustic_panel_set_D[0].position = [0.44999998807907104, 3.039999485015869, 0.6000000238418579]
acoustic_panel_set_D[0].rotation = [0, 0, 1.5707949837287574]
acoustic_panel_set_D[0].optimize = 2
storage_cabinet[0].position = [1.399999976158142, 6.774999618530273, 0.550000011920929]
storage_cabinet[0].rotation = [0, 0, -1.5707976555214407]
storage_cabinet[0].optimize = 2
plant_floor[0].position = [0.4000000059604645, 6.550000190734863, 0.675000011920929]
plant_floor[0].rotation = [0, 0, 0.00942477746072377]
plant_floor[0].optimize = 2
acoustic_panel_set_A[0].position = [0.3499999940395355, 6.960000514984131, 0.6000000238418579]
acoustic_panel_set_A[0].rotation = [0, 0, -1.570797650973432]
acoustic_panel_set_A[0].optimize = 2
conference_speakerphone[0].position = [4.0, 1.75, 0.7750000357627869]
conference_speakerphone[0].rotation = [0, 0, 0.09111058871462283]
conference_speakerphone[0].optimize = 2
coat_stand[0].position = [0.3499999940395355, 5.75, 0.875]
coat_stand[0].rotation = [0, 0, 0.00942477746072377]
coat_stand[0].optimize = 2
huddle_table[0].position = [4.0, 1.9500000476837158, 0.3700000047683716]
huddle_table[0].rotation = [0, 0, 0.09110618432572477]
huddle_table[0].optimize = 2
acoustic_panel_set_E[0].position = [1.149999976158142, 3.039999485015869, 0.6000000238418579]
acoustic_panel_set_E[0].rotation = [0, 0, 1.5707949837287574]
acoustic_panel_set_E[0].optimize = 2
notebook_C[0].position = [4.269999980926514, 2.1500000953674316, 0.75]
notebook_C[0].rotation = [0, 0, 0.09111058871462283]
notebook_C[0].optimize = 2

