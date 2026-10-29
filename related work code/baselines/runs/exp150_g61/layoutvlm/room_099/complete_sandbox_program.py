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
plant_floor = Assets(description="A potted plant with big green leaves.", size=[0.70, 0.70, 1.50], placements=[AssetInstance() for _ in range(1)])
pen_A = Assets(description="A long white mechanical pencil.", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_set_A = Assets(description="A wood sculpture that is to be hung on the wall.", size=[0.06, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
huddle_table = Assets(description="huddle table", size=[1.00, 2.00, 0.75], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_set_B = Assets(description="A wood sculpture that is to be hung on the wall.", size=[0.06, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
glass_water_carafe = Assets(description="A blue glass bottle.", size=[0.10, 0.10, 0.28], placements=[AssetInstance() for _ in range(1)])
conference_speakerphone = Assets(description="An old school black discman cd player with a cord plugged into side with a orange foam headset.", size=[0.22, 0.24, 0.06], placements=[AssetInstance() for _ in range(1)])
pen_B = Assets(description="A pencil with a blue cap on the end of it.", size=[0.01, 0.18, 0.01], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_set_C = Assets(description="A wood sculpture that is to be hung on the wall.", size=[0.06, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
coat_stand = Assets(description="A coat that's different shades of blue on a black four legged stand.", size=[0.60, 0.60, 1.75], placements=[AssetInstance() for _ in range(1)])
mobile_whiteboard = Assets(description="A whiteboard with a black marker.", size=[0.60, 1.20, 1.85], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_set_D = Assets(description="A wood sculpture that is to be hung on the wall.", size=[0.06, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
wall_monitor = Assets(description="A boxy black television with bright white screen.", size=[0.10, 1.23, 0.71], placements=[AssetInstance() for _ in range(1)])
wall_shelf_A = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.25, 0.90, 0.25], placements=[AssetInstance() for _ in range(1)])
whiteboard = Assets(description="A white rectangular poster with black blue and orange marks and irregular writing.", size=[0.04, 1.50, 0.90], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_set_E = Assets(description="A wood sculpture that is to be hung on the wall.", size=[0.06, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
storage_cabinet = Assets(description="storage cabinet", size=[0.45, 0.90, 1.20], placements=[AssetInstance() for _ in range(1)])
pen_C = Assets(description="a green pen with a purple tip.", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
table_plant = Assets(description="a vase with flowers, scissors, and a snail on a shelf.", size=[0.25, 0.30, 0.40], placements=[AssetInstance() for _ in range(1)])
pen_D = Assets(description="A blue marker with a cup on the top of it.", size=[0.02, 0.14, 0.02], placements=[AssetInstance() for _ in range(1)])
notebook_A = Assets(description="A brown book with silver corners.", size=[0.29, 0.21, 0.03], placements=[AssetInstance() for _ in range(1)])
side_credenza = Assets(description="A bunch of white cubby shelves.", size=[0.40, 1.50, 0.80], placements=[AssetInstance() for _ in range(1)])
wall_shelf_B = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.25, 0.90, 0.25], placements=[AssetInstance() for _ in range(1)])
huddle_chair = Assets(description="An office chair on wheels with a black fabric seat.", size=[0.65, 0.65, 0.95], placements=[AssetInstance() for _ in range(1)])
notebook_B = Assets(description="A red notepad decorated with a slug in the lower corner.", size=[0.21, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
lounge_chair = Assets(description="A black chair with four legs.", size=[0.80, 0.75, 0.80], placements=[AssetInstance() for _ in range(1)])
pen_E = Assets(description="red and blue pen.", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
notebook_C = Assets(description="A red and yellow notepad with metal spirals reading 'dolphin ko's notepad'.", size=[0.25, 0.18, 0.02], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_set_F = Assets(description="A wood sculpture that is to be hung on the wall.", size=[0.06, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_set_G = Assets(description="A wood sculpture that is to be hung on the wall.", size=[0.06, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])
notebook_D = Assets(description="A pink spiral notebook with a green leaf on it.", size=[0.25, 0.18, 0.02], placements=[AssetInstance() for _ in range(1)])
acoustic_panel_set_H = Assets(description="A wood sculpture that is to be hung on the wall.", size=[0.06, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])

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

plant_floor[0].position = [1.0456904860746281, 4.971991025091285, 0.75]
plant_floor[0].rotation = [0, 0, 0]
pen_A[0].position = [1.228989989880589, 4.838077924972771, 0.005]
pen_A[0].rotation = [0, 0, 0]
acoustic_panel_set_A[0].position = [0.8348302768971577, 3.3889148657105146, 0.6]
acoustic_panel_set_A[0].rotation = [0, 0, 0]
huddle_table[0].position = [1.0344145804773714, 3.878790362521828, 0.375]
huddle_table[0].rotation = [0, 0, 0]
acoustic_panel_set_B[0].position = [0.4110457842566906, 5.715459720998549, 0.6]
acoustic_panel_set_B[0].rotation = [0, 0, 0]
glass_water_carafe[0].position = [4.33324701131936, 0.8377590697292164, 0.14]
glass_water_carafe[0].rotation = [0, 0, 0]
conference_speakerphone[0].position = [2.7320158302521973, 3.6985298584782185, 0.03]
conference_speakerphone[0].rotation = [0, 0, 0]
pen_B[0].position = [1.5102473798139342, 3.011474798081184, 0.005]
pen_B[0].rotation = [0, 0, 0]
acoustic_panel_set_C[0].position = [1.5046892473397038, 6.242449971211928, 0.6]
acoustic_panel_set_C[0].rotation = [0, 0, 0]
coat_stand[0].position = [4.524736228018927, 0.005003451755111299, 0.875]
coat_stand[0].rotation = [0, 0, 0]
mobile_whiteboard[0].position = [4.905147224643651, 3.3581757553434946, 0.925]
mobile_whiteboard[0].rotation = [0, 0, 0]
acoustic_panel_set_D[0].position = [3.634947570655652, 0.32069920360517157, 0.6]
acoustic_panel_set_D[0].rotation = [0, 0, 0]
wall_monitor[0].position = [3.5403431155431075, 2.7465337222316397, 0.355]
wall_monitor[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [3.2509202132721997, 3.9618651372090214, 0.125]
wall_shelf_A[0].rotation = [0, 0, 0]
whiteboard[0].position = [0.7256644714346222, 3.920115607531374, 0.45]
whiteboard[0].rotation = [0, 0, 0]
acoustic_panel_set_E[0].position = [3.948780761435981, 1.5288252312658115, 0.6]
acoustic_panel_set_E[0].rotation = [0, 0, 0]
storage_cabinet[0].position = [4.11203009754702, 2.424690506285685, 0.6]
storage_cabinet[0].rotation = [0, 0, 0]
pen_C[0].position = [4.00229492283565, 2.002188329077394, 0.006]
pen_C[0].rotation = [0, 0, 0]
table_plant[0].position = [0.17085988513124095, 6.876722957113297, 0.2]
table_plant[0].rotation = [0, 0, 0]
pen_D[0].position = [2.7444322908665764, 3.830438593678553, 0.009]
pen_D[0].rotation = [0, 0, 0]
notebook_A[0].position = [3.5478917325220833, 2.0387583873316686, 0.0125]
notebook_A[0].rotation = [0, 0, 0]
side_credenza[0].position = [0.6127464572755315, 4.504667873739225, 0.4]
side_credenza[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [3.8644033551238217, 0.1950967439771586, 0.125]
wall_shelf_B[0].rotation = [0, 0, 0]
huddle_chair[0].position = [1.2767343729179603, 3.805555527046752, 0.475]
huddle_chair[0].rotation = [0, 0, 0]
notebook_B[0].position = [4.717100408115079, 3.800278018450918, 0.0075]
notebook_B[0].rotation = [0, 0, 0]
lounge_chair[0].position = [4.81662889876904, 0.505053040024682, 0.4]
lounge_chair[0].rotation = [0, 0, 0]
pen_E[0].position = [3.828313680693906, 1.8332636909139024, 0.006]
pen_E[0].rotation = [0, 0, 0]
notebook_C[0].position = [0.2969783157429956, 5.1321988347639955, 0.01]
notebook_C[0].rotation = [0, 0, 0]
acoustic_panel_set_F[0].position = [0.2733340305060955, 6.077314231466165, 0.6]
acoustic_panel_set_F[0].rotation = [0, 0, 0]
acoustic_panel_set_G[0].position = [4.404147224685552, 1.290196753735645, 0.6]
acoustic_panel_set_G[0].rotation = [0, 0, 0]
notebook_D[0].position = [1.347731714124047, 4.208186979956442, 0.01]
notebook_D[0].rotation = [0, 0, 0]
acoustic_panel_set_H[0].position = [4.641386760598878, 2.8462905405574737, 0.6]
acoustic_panel_set_H[0].rotation = [0, 0, 0]
plant_floor[0].position = [1.0456904860746281, 4.971991025091285, 0.75]
plant_floor[0].rotation = [0, 0, 0]
pen_A[0].position = [1.228989989880589, 4.838077924972771, 0.005]
pen_A[0].rotation = [0, 0, 0]
acoustic_panel_set_A[0].position = [0.8348302768971577, 3.3889148657105146, 0.6]
acoustic_panel_set_A[0].rotation = [0, 0, 0]
huddle_table[0].position = [1.0344145804773714, 3.878790362521828, 0.375]
huddle_table[0].rotation = [0, 0, 0]
acoustic_panel_set_B[0].position = [0.4110457842566906, 5.715459720998549, 0.6]
acoustic_panel_set_B[0].rotation = [0, 0, 0]
glass_water_carafe[0].position = [4.33324701131936, 0.8377590697292164, 0.14]
glass_water_carafe[0].rotation = [0, 0, 0]
conference_speakerphone[0].position = [2.7320158302521973, 3.6985298584782185, 0.03]
conference_speakerphone[0].rotation = [0, 0, 0]
pen_B[0].position = [1.5102473798139342, 3.011474798081184, 0.005]
pen_B[0].rotation = [0, 0, 0]
acoustic_panel_set_C[0].position = [1.5046892473397038, 6.242449971211928, 0.6]
acoustic_panel_set_C[0].rotation = [0, 0, 0]
coat_stand[0].position = [4.524736228018927, 0.005003451755111299, 0.875]
coat_stand[0].rotation = [0, 0, 0]
mobile_whiteboard[0].position = [4.905147224643651, 3.3581757553434946, 0.925]
mobile_whiteboard[0].rotation = [0, 0, 0]
acoustic_panel_set_D[0].position = [3.634947570655652, 0.32069920360517157, 0.6]
acoustic_panel_set_D[0].rotation = [0, 0, 0]
wall_monitor[0].position = [3.5403431155431075, 2.7465337222316397, 0.355]
wall_monitor[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [3.2509202132721997, 3.9618651372090214, 0.125]
wall_shelf_A[0].rotation = [0, 0, 0]
whiteboard[0].position = [0.7256644714346222, 3.920115607531374, 0.45]
whiteboard[0].rotation = [0, 0, 0]
acoustic_panel_set_E[0].position = [3.948780761435981, 1.5288252312658115, 0.6]
acoustic_panel_set_E[0].rotation = [0, 0, 0]
storage_cabinet[0].position = [4.11203009754702, 2.424690506285685, 0.6]
storage_cabinet[0].rotation = [0, 0, 0]
pen_C[0].position = [4.00229492283565, 2.002188329077394, 0.006]
pen_C[0].rotation = [0, 0, 0]
table_plant[0].position = [0.17085988513124095, 6.876722957113297, 0.2]
table_plant[0].rotation = [0, 0, 0]
pen_D[0].position = [2.7444322908665764, 3.830438593678553, 0.009]
pen_D[0].rotation = [0, 0, 0]
notebook_A[0].position = [3.5478917325220833, 2.0387583873316686, 0.0125]
notebook_A[0].rotation = [0, 0, 0]
side_credenza[0].position = [0.6127464572755315, 4.504667873739225, 0.4]
side_credenza[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [3.8644033551238217, 0.1950967439771586, 0.125]
wall_shelf_B[0].rotation = [0, 0, 0]
huddle_chair[0].position = [1.2767343729179603, 3.805555527046752, 0.475]
huddle_chair[0].rotation = [0, 0, 0]
notebook_B[0].position = [4.717100408115079, 3.800278018450918, 0.0075]
notebook_B[0].rotation = [0, 0, 0]
lounge_chair[0].position = [4.81662889876904, 0.505053040024682, 0.4]
lounge_chair[0].rotation = [0, 0, 0]
pen_E[0].position = [3.828313680693906, 1.8332636909139024, 0.006]
pen_E[0].rotation = [0, 0, 0]
notebook_C[0].position = [0.2969783157429956, 5.1321988347639955, 0.01]
notebook_C[0].rotation = [0, 0, 0]
acoustic_panel_set_F[0].position = [0.2733340305060955, 6.077314231466165, 0.6]
acoustic_panel_set_F[0].rotation = [0, 0, 0]
acoustic_panel_set_G[0].position = [4.404147224685552, 1.290196753735645, 0.6]
acoustic_panel_set_G[0].rotation = [0, 0, 0]
notebook_D[0].position = [1.347731714124047, 4.208186979956442, 0.01]
notebook_D[0].rotation = [0, 0, 0]
acoustic_panel_set_H[0].position = [4.641386760598878, 2.8462905405574737, 0.6]
acoustic_panel_set_H[0].rotation = [0, 0, 0]

solver.constraints = []

# The floor plan is a bent room, not its rectangular bounding box.
# Use the southeast wing for the huddle area and the northwest wing for
# storage/lounge seating. Keep the approach to the door at x=2, y=5.2 clear.

def place_asset(group, xyz, yaw_degrees, wall_index=None):
    instance = group[0]
    instance.position = list(xyz)
    instance.rotation = [0, 0, radians(yaw_degrees)]

    # Fixed references preserve both location (including mounting height)
    # and orientation. They are references only, not additional scene assets.
    reference = AssetInstance(
        position=list(xyz),
        rotation=[0, 0, radians(yaw_degrees)]
    )
    solver.distance_constraint(instance, reference, 0, 0, weight=10)
    solver.align_with(instance, reference)
    if wall_index is not None:
        solver.against_wall(instance, walls[wall_index])


# Huddle table: its long axis runs north-south, entirely inside the right wing.
place_asset(huddle_table, [4.00, 1.80, 0.375], 0)
place_asset(huddle_chair, [4.00, 3.30, 0.475], -90)
solver.point_towards(huddle_chair[0], huddle_table[0])
solver.distance_constraint(huddle_chair[0], huddle_table[0], 1.45, 1.60)

# Presentation surfaces are wall-mounted above floor/table height.
# Neither occupies the window on the south wall.
place_asset(wall_monitor, [4.95, 1.80, 1.65], 180, 3)
place_asset(whiteboard, [3.02, 1.80, 1.60], 0, 1)
solver.point_towards(wall_monitor[0], huddle_table[0])
solver.point_towards(whiteboard[0], huddle_table[0])

# Northwest furnishings stay outside the door's 1.91 m opening and approach.
# The west-side furniture ends at x=0.65 around the doorway.
place_asset(storage_cabinet, [0.225, 4.45, 0.60], 0, 7)
place_asset(coat_stand, [0.35, 5.25, 0.875], 0)
place_asset(mobile_whiteboard, [0.35, 6.30, 0.925], 0)
place_asset(lounge_chair, [1.40, 6.55, 0.40], -90)
solver.point_towards(
    lounge_chair[0],
    AssetInstance(position=[1.40, 4.00, 0.40])
)

# Low storage along the bottom edge of the west wing leaves the connecting
# passage above it open.
place_asset(side_credenza, [1.25, 3.20, 0.40], 90, 0)

# Place the floor plant beside, rather than directly in front of, the window.
place_asset(plant_floor, [4.65, 0.40, 0.75], 180)

# Wall shelves are suspended, with their heights explicitly retained.
place_asset(wall_shelf_A, [0.125, 3.60, 1.65], 0, 7)
place_asset(wall_shelf_B, [0.125, 4.65, 1.85], 0, 7)

# Acoustic panels form an elevated band, above the monitor and whiteboard.
# Their separate wall intervals avoid panel-to-panel overlaps.
for panel_group, panel_xyz, panel_yaw, panel_wall in [
    (acoustic_panel_set_A, [4.97, 0.65, 2.75], 180, 3),
    (acoustic_panel_set_B, [4.97, 1.45, 2.75], 180, 3),
    (acoustic_panel_set_C, [4.97, 2.25, 2.75], 180, 3),
    (acoustic_panel_set_D, [4.97, 3.05, 2.75], 180, 3),
    (acoustic_panel_set_E, [3.03, 0.65, 2.75], 0, 1),
    (acoustic_panel_set_F, [3.03, 1.45, 2.75], 0, 1),
    (acoustic_panel_set_G, [3.03, 2.25, 2.75], 0, 1),
    (acoustic_panel_set_H, [3.65, 3.97, 2.75], -90, 4),
]:
    place_asset(panel_group, panel_xyz, panel_yaw, panel_wall)


def place_on_surface(group, support_group, xy, yaw_degrees=0):
    support_instance = support_group[0]
    surface_height = (
        support_instance.position[2] + support_group.size[2] / 2
    )
    xyz = [xy[0], xy[1], surface_height + group.size[2] / 2]

    # Establish support first; the positional reference then retains the
    # deliberately separated tabletop/shelf arrangement.
    solver.on_top_of(group[0], support_instance)
    place_asset(group, xyz, yaw_degrees)
    solver.align_with(group[0], support_instance, angle=yaw_degrees)


# All notebooks, including notebook_A (o0020), lie flat on the huddle table.
# Four separated writing stations leave the middle for shared equipment.
place_on_surface(notebook_A, huddle_table, [3.78, 1.25])
place_on_surface(notebook_B, huddle_table, [4.22, 1.25])
place_on_surface(notebook_C, huddle_table, [3.78, 2.30])
place_on_surface(notebook_D, huddle_table, [4.22, 2.30])

place_on_surface(pen_A, huddle_table, [4.00, 1.25])
place_on_surface(pen_B, huddle_table, [4.42, 1.25])
place_on_surface(pen_C, huddle_table, [3.98, 2.30])
place_on_surface(pen_D, huddle_table, [4.41, 2.30])
place_on_surface(pen_E, huddle_table, [4.05, 2.62])

place_on_surface(conference_speakerphone, huddle_table, [4.00, 1.80])
place_on_surface(glass_water_carafe, huddle_table, [4.30, 1.80])

# The decorative tabletop plant fits entirely on the first wall shelf.
place_on_surface(table_plant, wall_shelf_A, [0.125, 3.60])

# Additional relational constraints preserve the functional groupings.
solver.distance_constraint(
    mobile_whiteboard[0], lounge_chair[0], 1.05, 1.25
)
solver.distance_constraint(
    coat_stand[0], storage_cabinet[0], 0.80, 0.95
)
solver.distance_constraint(
    conference_speakerphone[0], glass_water_carafe[0], 0.28, 0.36
)

solver.constraints = []
whiteboard[0].position = [3.0227808952331543, 1.7999999523162842, 0.44999998807907104]
whiteboard[0].rotation = [0, 0, -0.002715292342231881]
whiteboard[0].optimize = 2
side_credenza[0].position = [1.25, 3.201521396636963, 0.4000000059604645]
side_credenza[0].rotation = [0, 0, 1.5718316543845796]
side_credenza[0].optimize = 2
acoustic_panel_set_H[0].position = [3.6500000953674316, 3.972677707672119, 0.6000000238418579]
acoustic_panel_set_H[0].rotation = [0, 0, -1.5697591344295099]
acoustic_panel_set_H[0].optimize = 2
acoustic_panel_set_C[0].position = [4.972708225250244, 2.25, 0.6000000238418579]
acoustic_panel_set_C[0].rotation = [0, 0, -3.1405554233409774]
acoustic_panel_set_C[0].optimize = 2
lounge_chair[0].position = [1.399999976158142, 6.550000190734863, 0.4000000059604645]
lounge_chair[0].rotation = [0, 0, -1.5550883628776802]
lounge_chair[0].optimize = 2
plant_floor[0].position = [4.650000095367432, 0.4000000059604645, 0.75]
plant_floor[0].rotation = [0, 0, -3.1321678761290697]
plant_floor[0].optimize = 2
wall_monitor[0].position = [4.948718070983887, 1.7999999523162842, 0.35499998927116394]
wall_monitor[0].rotation = [0, 0, 3.1388775084389415]
wall_monitor[0].optimize = 2
glass_water_carafe[0].position = [4.300000190734863, 1.7999999523162842, 0.8899999856948853]
glass_water_carafe[0].rotation = [0, 0, 0.09402054284636124]
glass_water_carafe[0].optimize = 2
pen_B[0].position = [4.420000076293945, 1.25, 0.7549999952316284]
pen_B[0].rotation = [0, 0, 0.09646095776605146]
pen_B[0].optimize = 2
table_plant[0].position = [0.125, 3.5999999046325684, 0.44999998807907104]
table_plant[0].rotation = [0, 0, 0.015441399849685589]
table_plant[0].optimize = 2
storage_cabinet[0].position = [0.2263607382774353, 4.449999809265137, 0.6000000238418579]
storage_cabinet[0].rotation = [0, 0, -0.002716474190263934]
storage_cabinet[0].optimize = 2
acoustic_panel_set_B[0].position = [4.972708225250244, 1.4500000476837158, 0.6000000238418579]
acoustic_panel_set_B[0].rotation = [0, 0, -3.1405554233409774]
acoustic_panel_set_B[0].optimize = 2
pen_D[0].position = [4.409999847412109, 2.299999952316284, 0.7599999904632568]
pen_D[0].rotation = [0, 0, 0.09646095776605146]
pen_D[0].optimize = 2
acoustic_panel_set_E[0].position = [3.0273220539093018, 0.6499999761581421, 0.6000000238418579]
acoustic_panel_set_E[0].rotation = [0, 0, 0.0010372034890529912]
acoustic_panel_set_E[0].optimize = 2
acoustic_panel_set_A[0].position = [4.972708225250244, 0.6499999761581421, 0.6000000238418579]
acoustic_panel_set_A[0].rotation = [0, 0, -3.1405554233409774]
acoustic_panel_set_A[0].optimize = 2
wall_shelf_B[0].position = [0.12564429640769958, 4.650000095367432, 0.125]
wall_shelf_B[0].rotation = [0, 0, 0.001035807506085799]
wall_shelf_B[0].optimize = 2
pen_E[0].position = [4.050000190734863, 2.619999885559082, 0.7549999952316284]
pen_E[0].rotation = [0, 0, 0.09646095776605146]
pen_E[0].optimize = 2
acoustic_panel_set_F[0].position = [3.0273220539093018, 1.4500000476837158, 0.6000000238418579]
acoustic_panel_set_F[0].rotation = [0, 0, 0.0010372034890529912]
acoustic_panel_set_F[0].optimize = 2
conference_speakerphone[0].position = [4.0, 1.7999999523162842, 0.7799999713897705]
conference_speakerphone[0].rotation = [0, 0, 0.09402054284636124]
conference_speakerphone[0].optimize = 2
notebook_A[0].position = [3.7799999713897705, 1.25, 0.7649999856948853]
notebook_A[0].rotation = [0, 0, 0.09646095776605146]
notebook_A[0].optimize = 2
acoustic_panel_set_G[0].position = [3.0273220539093018, 2.25, 0.6000000238418579]
acoustic_panel_set_G[0].rotation = [0, 0, 0.0010372034890529912]
acoustic_panel_set_G[0].optimize = 2
huddle_table[0].position = [4.0, 1.7999999523162842, 0.375]
huddle_table[0].rotation = [0, 0, 0.09110618432572477]
huddle_table[0].optimize = 2
notebook_B[0].position = [4.21999979019165, 1.25, 0.7549999952316284]
notebook_B[0].rotation = [0, 0, 0.09646095776605146]
notebook_B[0].optimize = 2
mobile_whiteboard[0].position = [0.3499999940395355, 6.300000190734863, 0.925000011920929]
mobile_whiteboard[0].rotation = [0, 0, 0.01256637125682779]
mobile_whiteboard[0].optimize = 2
huddle_chair[0].position = [4.0, 3.299999952316284, 0.4749999940395355]
huddle_chair[0].rotation = [0, 0, -1.5550883628776802]
huddle_chair[0].optimize = 2
acoustic_panel_set_D[0].position = [4.972708225250244, 3.049999952316284, 0.6000000238418579]
acoustic_panel_set_D[0].rotation = [0, 0, -3.1405554233409774]
acoustic_panel_set_D[0].optimize = 2
notebook_C[0].position = [3.7799999713897705, 2.299999952316284, 0.7599999904632568]
notebook_C[0].rotation = [0, 0, 0.09646095776605146]
notebook_C[0].optimize = 2
wall_shelf_A[0].position = [0.12614010274410248, 3.5999999046325684, 0.125]
wall_shelf_A[0].rotation = [0, 0, -0.004221606977464284]
wall_shelf_A[0].optimize = 2
pen_C[0].position = [3.9800000190734863, 2.299999952316284, 0.7549999952316284]
pen_C[0].rotation = [0, 0, 0.09646095776605146]
pen_C[0].optimize = 2
coat_stand[0].position = [0.3499999940395355, 5.25, 0.875]
coat_stand[0].rotation = [0, 0, 0.01256637125682779]
coat_stand[0].optimize = 2
notebook_D[0].position = [4.21999979019165, 2.299999952316284, 0.7599999904632568]
notebook_D[0].rotation = [0, 0, 0.09646095776605146]
notebook_D[0].optimize = 2
pen_A[0].position = [4.0, 1.25, 0.7549999952316284]
pen_A[0].rotation = [0, 0, 0.09646095776605146]
pen_A[0].optimize = 2

