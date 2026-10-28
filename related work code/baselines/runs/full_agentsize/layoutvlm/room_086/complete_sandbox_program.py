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
    Wall(corner1=[6.24, 0.00, 0.00], corner2=[6.24, 5.74, 0.00]),
    Wall(corner1=[6.24, 5.74, 0.00], corner2=[0.50, 5.74, 0.00]),
    Wall(corner1=[0.50, 5.74, 0.00], corner2=[0.50, 3.24, 0.00]),
    Wall(corner1=[0.50, 3.24, 0.00], corner2=[0.00, 3.24, 0.00]),
    Wall(corner1=[0.00, 3.24, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.24, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
box_A = Assets(description="box", size=[0.24, 0.32, 0.18], placements=[AssetInstance() for _ in range(1)])
bottle_A = Assets(description="bottle", size=[0.08, 0.08, 0.28], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="lamp", size=[0.32, 0.32, 0.22], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="bottle", size=[0.07, 0.07, 0.24], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.62, 0.90, 0.90], placements=[AssetInstance() for _ in range(1)])
bottle_C = Assets(description="bottle", size=[0.09, 0.09, 0.30], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.35, 0.80, 0.70], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.30, 0.30, 0.20], placements=[AssetInstance() for _ in range(1)])
lamp_C = Assets(description="lamp", size=[0.30, 0.30, 0.20], placements=[AssetInstance() for _ in range(1)])
cabinet_C = Assets(description="cabinet", size=[0.62, 0.90, 0.90], placements=[AssetInstance() for _ in range(1)])
microwave = Assets(description="microwave", size=[0.40, 0.52, 0.30], placements=[AssetInstance() for _ in range(1)])
pot_A = Assets(description="pot", size=[0.28, 0.28, 0.20], placements=[AssetInstance() for _ in range(1)])
bottle_D = Assets(description="bottle", size=[0.08, 0.08, 0.27], placements=[AssetInstance() for _ in range(1)])
lamp_D = Assets(description="lamp", size=[0.32, 0.32, 0.22], placements=[AssetInstance() for _ in range(1)])
can_A = Assets(description="can", size=[0.07, 0.07, 0.12], placements=[AssetInstance() for _ in range(1)])
cabinet_D = Assets(description="cabinet", size=[0.35, 0.80, 0.70], placements=[AssetInstance() for _ in range(1)])
bottle_E = Assets(description="bottle", size=[0.07, 0.07, 0.25], placements=[AssetInstance() for _ in range(1)])
box_B = Assets(description="box", size=[0.20, 0.28, 0.12], placements=[AssetInstance() for _ in range(1)])
pan_A = Assets(description="pan", size=[0.28, 0.46, 0.08], placements=[AssetInstance() for _ in range(1)])
book = Assets(description="book", size=[0.04, 0.22, 0.28], placements=[AssetInstance() for _ in range(1)])
bottle_F = Assets(description="bottle", size=[0.08, 0.08, 0.30], placements=[AssetInstance() for _ in range(1)])
bottle_G = Assets(description="bottle", size=[0.07, 0.07, 0.22], placements=[AssetInstance() for _ in range(1)])
pot_B = Assets(description="pot", size=[0.30, 0.30, 0.22], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="shelf", size=[0.35, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
box_C = Assets(description="box", size=[0.25, 0.35, 0.20], placements=[AssetInstance() for _ in range(1)])
box_D = Assets(description="box", size=[0.22, 0.30, 0.16], placements=[AssetInstance() for _ in range(1)])
food_A = Assets(description="food", size=[0.12, 0.18, 0.08], placements=[AssetInstance() for _ in range(1)])
faucet = Assets(description="faucet", size=[0.16, 0.22, 0.32], placements=[AssetInstance() for _ in range(1)])
cabinet_E = Assets(description="cabinet", size=[0.62, 1.00, 0.90], placements=[AssetInstance() for _ in range(1)])
cabinet_F = Assets(description="cabinet", size=[0.62, 0.90, 0.90], placements=[AssetInstance() for _ in range(1)])
cup_A = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
box_E = Assets(description="box", size=[0.28, 0.40, 0.20], placements=[AssetInstance() for _ in range(1)])
bottle_H = Assets(description="bottle", size=[0.08, 0.08, 0.26], placements=[AssetInstance() for _ in range(1)])
box_F = Assets(description="box", size=[0.18, 0.25, 0.12], placements=[AssetInstance() for _ in range(1)])
bottle_I = Assets(description="bottle", size=[0.07, 0.07, 0.23], placements=[AssetInstance() for _ in range(1)])
bottle_J = Assets(description="bottle", size=[0.09, 0.09, 0.31], placements=[AssetInstance() for _ in range(1)])
bottle_K = Assets(description="bottle", size=[0.08, 0.08, 0.28], placements=[AssetInstance() for _ in range(1)])
bottle_L = Assets(description="bottle", size=[0.07, 0.07, 0.24], placements=[AssetInstance() for _ in range(1)])
vase = Assets(description="vase", size=[0.16, 0.16, 0.32], placements=[AssetInstance() for _ in range(1)])
food_B = Assets(description="food", size=[0.16, 0.22, 0.10], placements=[AssetInstance() for _ in range(1)])
bottle_M = Assets(description="bottle", size=[0.08, 0.08, 0.27], placements=[AssetInstance() for _ in range(1)])
bottle_N = Assets(description="bottle", size=[0.07, 0.07, 0.25], placements=[AssetInstance() for _ in range(1)])
pan_B = Assets(description="pan", size=[0.30, 0.48, 0.09], placements=[AssetInstance() for _ in range(1)])
bottle_O = Assets(description="bottle", size=[0.09, 0.09, 0.29], placements=[AssetInstance() for _ in range(1)])
can_B = Assets(description="can", size=[0.07, 0.07, 0.11], placements=[AssetInstance() for _ in range(1)])
dishwasher = Assets(description="dishwasher", size=[0.60, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
bottle_P = Assets(description="bottle", size=[0.08, 0.08, 0.25], placements=[AssetInstance() for _ in range(1)])
food_C = Assets(description="food", size=[0.15, 0.20, 0.09], placements=[AssetInstance() for _ in range(1)])
oven = Assets(description="oven", size=[0.62, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.30, 0.90, 0.05], placements=[AssetInstance() for _ in range(1)])
lamp_E = Assets(description="lamp", size=[0.30, 0.30, 0.20], placements=[AssetInstance() for _ in range(1)])
cup_B = Assets(description="cup", size=[0.09, 0.09, 0.10], placements=[AssetInstance() for _ in range(1)])
pot_C = Assets(description="pot", size=[0.26, 0.26, 0.18], placements=[AssetInstance() for _ in range(1)])

box_A[0].instance_id = 'box_A_0'
bottle_A[0].instance_id = 'bottle_A_0'
lamp_A[0].instance_id = 'lamp_A_0'
bottle_B[0].instance_id = 'bottle_B_0'
cabinet_A[0].instance_id = 'cabinet_A_0'
bottle_C[0].instance_id = 'bottle_C_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
lamp_B[0].instance_id = 'lamp_B_0'
lamp_C[0].instance_id = 'lamp_C_0'
cabinet_C[0].instance_id = 'cabinet_C_0'
microwave[0].instance_id = 'microwave_0'
pot_A[0].instance_id = 'pot_A_0'
bottle_D[0].instance_id = 'bottle_D_0'
lamp_D[0].instance_id = 'lamp_D_0'
can_A[0].instance_id = 'can_A_0'
cabinet_D[0].instance_id = 'cabinet_D_0'
bottle_E[0].instance_id = 'bottle_E_0'
box_B[0].instance_id = 'box_B_0'
pan_A[0].instance_id = 'pan_A_0'
book[0].instance_id = 'book_0'
bottle_F[0].instance_id = 'bottle_F_0'
bottle_G[0].instance_id = 'bottle_G_0'
pot_B[0].instance_id = 'pot_B_0'
shelf_A[0].instance_id = 'shelf_A_0'
box_C[0].instance_id = 'box_C_0'
box_D[0].instance_id = 'box_D_0'
food_A[0].instance_id = 'food_A_0'
faucet[0].instance_id = 'faucet_0'
cabinet_E[0].instance_id = 'cabinet_E_0'
cabinet_F[0].instance_id = 'cabinet_F_0'
cup_A[0].instance_id = 'cup_A_0'
box_E[0].instance_id = 'box_E_0'
bottle_H[0].instance_id = 'bottle_H_0'
box_F[0].instance_id = 'box_F_0'
bottle_I[0].instance_id = 'bottle_I_0'
bottle_J[0].instance_id = 'bottle_J_0'
bottle_K[0].instance_id = 'bottle_K_0'
bottle_L[0].instance_id = 'bottle_L_0'
vase[0].instance_id = 'vase_0'
food_B[0].instance_id = 'food_B_0'
bottle_M[0].instance_id = 'bottle_M_0'
bottle_N[0].instance_id = 'bottle_N_0'
pan_B[0].instance_id = 'pan_B_0'
bottle_O[0].instance_id = 'bottle_O_0'
can_B[0].instance_id = 'can_B_0'
dishwasher[0].instance_id = 'dishwasher_0'
bottle_P[0].instance_id = 'bottle_P_0'
food_C[0].instance_id = 'food_C_0'
oven[0].instance_id = 'oven_0'
shelf_B[0].instance_id = 'shelf_B_0'
lamp_E[0].instance_id = 'lamp_E_0'
cup_B[0].instance_id = 'cup_B_0'
pot_C[0].instance_id = 'pot_C_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

box_A[0].position = [5.505248232406356, 0.4467992982256133, 0.09]
box_A[0].rotation = [0, 0, 0]
bottle_A[0].position = [2.832016318457215, 4.476487249737532, 0.14]
bottle_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [4.572023027181723, 3.8682312258331226, 0.11]
lamp_A[0].rotation = [0, 0, 0]
bottle_B[0].position = [4.5515977964917065, 5.38277692003809, 0.12]
bottle_B[0].rotation = [0, 0, 0]
cabinet_A[0].position = [5.179701727423521, 4.423575604392453, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
bottle_C[0].position = [1.5148386924822186, 1.41039031308245, 0.15]
bottle_C[0].rotation = [0, 0, 0]
cabinet_B[0].position = [3.2791646033506057, 4.902986637415832, 0.35]
cabinet_B[0].rotation = [0, 0, 0]
lamp_B[0].position = [3.562371423734155, 4.340294951050887, 0.1]
lamp_B[0].rotation = [0, 0, 0]
lamp_C[0].position = [2.277379418951524, 0.590095751812574, 0.1]
lamp_C[0].rotation = [0, 0, 0]
cabinet_C[0].position = [0.3984572601856624, 1.3392354695036468, 0.45]
cabinet_C[0].rotation = [0, 0, 0]
microwave[0].position = [5.06185268709111, 3.028414704541609, 0.15]
microwave[0].rotation = [0, 0, 0]
pot_A[0].position = [3.1793281212359763, 2.030679738849474, 0.1]
pot_A[0].rotation = [0, 0, 0]
bottle_D[0].position = [4.369026933246132, 5.314514573133245, 0.135]
bottle_D[0].rotation = [0, 0, 0]
lamp_D[0].position = [1.1160913531785437, 0.012455188826792673, 0.11]
lamp_D[0].rotation = [0, 0, 0]
can_A[0].position = [1.7205093110065721, 2.5757726333085413, 0.06]
can_A[0].rotation = [0, 0, 0]
cabinet_D[0].position = [5.516682522634521, 2.1565532903289433, 0.35]
cabinet_D[0].rotation = [0, 0, 0]
bottle_E[0].position = [5.004860046826044, 4.932443404826222, 0.125]
bottle_E[0].rotation = [0, 0, 0]
box_B[0].position = [4.942119189634472, 2.316249332739601, 0.06]
box_B[0].rotation = [0, 0, 0]
pan_A[0].position = [3.3207039498630997, 3.745410185177046, 0.04]
pan_A[0].rotation = [0, 0, 0]
book[0].position = [5.900360804727596, 0.5057344198591429, 0.14]
book[0].rotation = [0, 0, 0]
bottle_F[0].position = [4.998333983449229, 1.3821990151320709, 0.15]
bottle_F[0].rotation = [0, 0, 0]
bottle_G[0].position = [4.627520320065158, 4.809942663254825, 0.11]
bottle_G[0].rotation = [0, 0, 0]
pot_B[0].position = [3.988126016251464, 3.2184644948595373, 0.11]
pot_B[0].rotation = [0, 0, 0]
shelf_A[0].position = [1.0261759677610032, 2.112576232218078, 0.9]
shelf_A[0].rotation = [0, 0, 0]
box_C[0].position = [1.8183091589245686, 4.825126791500792, 0.1]
box_C[0].rotation = [0, 0, 0]
box_D[0].position = [2.1737506292393176, 1.103052557017762, 0.08]
box_D[0].rotation = [0, 0, 0]
food_A[0].position = [1.44876625852784, 3.5829437833099074, 0.04]
food_A[0].rotation = [0, 0, 0]
faucet[0].position = [2.183502729584739, 2.8683066740657117, 0.16]
faucet[0].rotation = [0, 0, 0]
cabinet_E[0].position = [1.021982344249433, 3.6633422394827146, 0.45]
cabinet_E[0].rotation = [0, 0, 0]
cabinet_F[0].position = [1.0336704310884035, 4.140587266333038, 0.45]
cabinet_F[0].rotation = [0, 0, 0]
cup_A[0].position = [0.3126342578109185, 2.3764945837001266, 0.055]
cup_A[0].rotation = [0, 0, 0]
box_E[0].position = [5.04099269779804, 4.385857062481146, 0.1]
box_E[0].rotation = [0, 0, 0]
bottle_H[0].position = [0.3548452109351124, 1.7336677415416308, 0.13]
bottle_H[0].rotation = [0, 0, 0]
box_F[0].position = [3.3151037457966046, 0.2240037660929406, 0.06]
box_F[0].rotation = [0, 0, 0]
bottle_I[0].position = [1.6344783601718846, 3.0264900930755103, 0.115]
bottle_I[0].rotation = [0, 0, 0]
bottle_J[0].position = [3.004269088306459, 2.139421089177233, 0.155]
bottle_J[0].rotation = [0, 0, 0]
bottle_K[0].position = [4.3571683742510015, 2.5582531012956164, 0.14]
bottle_K[0].rotation = [0, 0, 0]
bottle_L[0].position = [3.997818274417382, 3.997796857906462, 0.12]
bottle_L[0].rotation = [0, 0, 0]
vase[0].position = [2.6063569539996565, 2.9128115504718, 0.16]
vase[0].rotation = [0, 0, 0]
food_B[0].position = [0.012913211123093122, 0.3078783200088772, 0.05]
food_B[0].rotation = [0, 0, 0]
bottle_M[0].position = [3.105387879317773, 1.4193646255028567, 0.135]
bottle_M[0].rotation = [0, 0, 0]
bottle_N[0].position = [1.2539636062200044, 0.637946109131725, 0.125]
bottle_N[0].rotation = [0, 0, 0]
pan_B[0].position = [3.5065694997564134, 5.220101040501307, 0.045]
pan_B[0].rotation = [0, 0, 0]
bottle_O[0].position = [3.875784108457921, 4.878209082153387, 0.145]
bottle_O[0].rotation = [0, 0, 0]
can_B[0].position = [5.884906235477279, 5.051034449400479, 0.055]
can_B[0].rotation = [0, 0, 0]
dishwasher[0].position = [3.0949634059784272, 3.0375916539531933, 0.425]
dishwasher[0].rotation = [0, 0, 0]
bottle_P[0].position = [4.036656876344391, 4.9486458877137975, 0.125]
bottle_P[0].rotation = [0, 0, 0]
food_C[0].position = [0.714880388657622, 0.2910148243688746, 0.045]
food_C[0].rotation = [0, 0, 0]
oven[0].position = [1.7101433651256872, 3.8214797361370905, 0.45]
oven[0].rotation = [0, 0, 0]
shelf_B[0].position = [3.006769061709371, 1.9693622038820238, 0.025]
shelf_B[0].rotation = [0, 0, 0]
lamp_E[0].position = [6.175392207549698, 1.3074150036908994, 0.1]
lamp_E[0].rotation = [0, 0, 0]
cup_B[0].position = [1.195506504405903, 0.4116389983023425, 0.05]
cup_B[0].rotation = [0, 0, 0]
pot_C[0].position = [5.457587281126416, 0.5024751312766695, 0.09]
pot_C[0].rotation = [0, 0, 0]
box_A[0].position = [5.505248232406356, 0.4467992982256133, 0.09]
box_A[0].rotation = [0, 0, 0]
bottle_A[0].position = [2.832016318457215, 4.476487249737532, 0.14]
bottle_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [4.572023027181723, 3.8682312258331226, 0.11]
lamp_A[0].rotation = [0, 0, 0]
bottle_B[0].position = [4.5515977964917065, 5.38277692003809, 0.12]
bottle_B[0].rotation = [0, 0, 0]
cabinet_A[0].position = [5.179701727423521, 4.423575604392453, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
bottle_C[0].position = [1.5148386924822186, 1.41039031308245, 0.15]
bottle_C[0].rotation = [0, 0, 0]
cabinet_B[0].position = [3.2791646033506057, 4.902986637415832, 0.35]
cabinet_B[0].rotation = [0, 0, 0]
lamp_B[0].position = [3.562371423734155, 4.340294951050887, 0.1]
lamp_B[0].rotation = [0, 0, 0]
lamp_C[0].position = [2.277379418951524, 0.590095751812574, 0.1]
lamp_C[0].rotation = [0, 0, 0]
cabinet_C[0].position = [0.3984572601856624, 1.3392354695036468, 0.45]
cabinet_C[0].rotation = [0, 0, 0]
microwave[0].position = [5.06185268709111, 3.028414704541609, 0.15]
microwave[0].rotation = [0, 0, 0]
pot_A[0].position = [3.1793281212359763, 2.030679738849474, 0.1]
pot_A[0].rotation = [0, 0, 0]
bottle_D[0].position = [4.369026933246132, 5.314514573133245, 0.135]
bottle_D[0].rotation = [0, 0, 0]
lamp_D[0].position = [1.1160913531785437, 0.012455188826792673, 0.11]
lamp_D[0].rotation = [0, 0, 0]
can_A[0].position = [1.7205093110065721, 2.5757726333085413, 0.06]
can_A[0].rotation = [0, 0, 0]
cabinet_D[0].position = [5.516682522634521, 2.1565532903289433, 0.35]
cabinet_D[0].rotation = [0, 0, 0]
bottle_E[0].position = [5.004860046826044, 4.932443404826222, 0.125]
bottle_E[0].rotation = [0, 0, 0]
box_B[0].position = [4.942119189634472, 2.316249332739601, 0.06]
box_B[0].rotation = [0, 0, 0]
pan_A[0].position = [3.3207039498630997, 3.745410185177046, 0.04]
pan_A[0].rotation = [0, 0, 0]
book[0].position = [5.900360804727596, 0.5057344198591429, 0.14]
book[0].rotation = [0, 0, 0]
bottle_F[0].position = [4.998333983449229, 1.3821990151320709, 0.15]
bottle_F[0].rotation = [0, 0, 0]
bottle_G[0].position = [4.627520320065158, 4.809942663254825, 0.11]
bottle_G[0].rotation = [0, 0, 0]
pot_B[0].position = [3.988126016251464, 3.2184644948595373, 0.11]
pot_B[0].rotation = [0, 0, 0]
shelf_A[0].position = [1.0261759677610032, 2.112576232218078, 0.9]
shelf_A[0].rotation = [0, 0, 0]
box_C[0].position = [1.8183091589245686, 4.825126791500792, 0.1]
box_C[0].rotation = [0, 0, 0]
box_D[0].position = [2.1737506292393176, 1.103052557017762, 0.08]
box_D[0].rotation = [0, 0, 0]
food_A[0].position = [1.44876625852784, 3.5829437833099074, 0.04]
food_A[0].rotation = [0, 0, 0]
faucet[0].position = [2.183502729584739, 2.8683066740657117, 0.16]
faucet[0].rotation = [0, 0, 0]
cabinet_E[0].position = [1.021982344249433, 3.6633422394827146, 0.45]
cabinet_E[0].rotation = [0, 0, 0]
cabinet_F[0].position = [1.0336704310884035, 4.140587266333038, 0.45]
cabinet_F[0].rotation = [0, 0, 0]
cup_A[0].position = [0.3126342578109185, 2.3764945837001266, 0.055]
cup_A[0].rotation = [0, 0, 0]
box_E[0].position = [5.04099269779804, 4.385857062481146, 0.1]
box_E[0].rotation = [0, 0, 0]
bottle_H[0].position = [0.3548452109351124, 1.7336677415416308, 0.13]
bottle_H[0].rotation = [0, 0, 0]
box_F[0].position = [3.3151037457966046, 0.2240037660929406, 0.06]
box_F[0].rotation = [0, 0, 0]
bottle_I[0].position = [1.6344783601718846, 3.0264900930755103, 0.115]
bottle_I[0].rotation = [0, 0, 0]
bottle_J[0].position = [3.004269088306459, 2.139421089177233, 0.155]
bottle_J[0].rotation = [0, 0, 0]
bottle_K[0].position = [4.3571683742510015, 2.5582531012956164, 0.14]
bottle_K[0].rotation = [0, 0, 0]
bottle_L[0].position = [3.997818274417382, 3.997796857906462, 0.12]
bottle_L[0].rotation = [0, 0, 0]
vase[0].position = [2.6063569539996565, 2.9128115504718, 0.16]
vase[0].rotation = [0, 0, 0]
food_B[0].position = [0.012913211123093122, 0.3078783200088772, 0.05]
food_B[0].rotation = [0, 0, 0]
bottle_M[0].position = [3.105387879317773, 1.4193646255028567, 0.135]
bottle_M[0].rotation = [0, 0, 0]
bottle_N[0].position = [1.2539636062200044, 0.637946109131725, 0.125]
bottle_N[0].rotation = [0, 0, 0]
pan_B[0].position = [3.5065694997564134, 5.220101040501307, 0.045]
pan_B[0].rotation = [0, 0, 0]
bottle_O[0].position = [3.875784108457921, 4.878209082153387, 0.145]
bottle_O[0].rotation = [0, 0, 0]
can_B[0].position = [5.884906235477279, 5.051034449400479, 0.055]
can_B[0].rotation = [0, 0, 0]
dishwasher[0].position = [3.0949634059784272, 3.0375916539531933, 0.425]
dishwasher[0].rotation = [0, 0, 0]
bottle_P[0].position = [4.036656876344391, 4.9486458877137975, 0.125]
bottle_P[0].rotation = [0, 0, 0]
food_C[0].position = [0.714880388657622, 0.2910148243688746, 0.045]
food_C[0].rotation = [0, 0, 0]
oven[0].position = [1.7101433651256872, 3.8214797361370905, 0.45]
oven[0].rotation = [0, 0, 0]
shelf_B[0].position = [3.006769061709371, 1.9693622038820238, 0.025]
shelf_B[0].rotation = [0, 0, 0]
lamp_E[0].position = [6.175392207549698, 1.3074150036908994, 0.1]
lamp_E[0].rotation = [0, 0, 0]
cup_B[0].position = [1.195506504405903, 0.4116389983023425, 0.05]
cup_B[0].rotation = [0, 0, 0]
pot_C[0].position = [5.457587281126416, 0.5024751312766695, 0.09]
pot_C[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed pose anchors let every placement retain its intended position and
# orientation while the solver resolves the additional semantic constraints.
def _place(asset, position, yaw_degrees, support=None, wall=None):
    instance = asset[0]
    instance.position = position
    instance.rotation = [0, 0, radians(yaw_degrees)]

    pose_anchor = AssetInstance(
        position=position,
        rotation=[0, 0, radians(yaw_degrees)],
    )

    # High-priority position and orientation constraints preserve the
    # collision-free layout shown below.
    solver.distance_constraint(
        instance, pose_anchor, 0, 0, weight=10
    )
    solver.align_with(instance, pose_anchor, angle=0)

    if wall is not None:
        solver.against_wall(instance, wall)

    if support is not None:
        solver.on_top_of(instance, support[0])


# ---------------------------------------------------------------------------
# Floor-standing kitchen units
#
# The main run occupies the north wall. It leaves the windows on the west and
# south walls unobstructed and keeps the right-wall door area around
# (6.24, 2.54) completely clear.
#
# Along the north wall, the required ordering is:
# cabinet_A (o0004) -> oven (o0048) -> cabinet_F (o0029).
# All north-wall units face into the room (-y).
# ---------------------------------------------------------------------------

_place(cabinet_A, [0.95, 5.43, 0.45], -90, wall=walls[1])
_place(oven,      [1.70, 5.44, 0.45], -90, wall=walls[1])
_place(cabinet_F, [2.45, 5.43, 0.45], -90, wall=walls[1])
_place(cabinet_C, [3.35, 5.43, 0.45], -90, wall=walls[1])
_place(cabinet_E, [4.30, 5.43, 0.45], -90, wall=walls[1])
_place(dishwasher,[5.10, 5.44, 0.425], -90, wall=walls[1])
_place(cabinet_B, [5.82, 5.565, 0.35], -90, wall=walls[1])

# A low auxiliary cabinet is placed on the unobstructed part of the south
# wall, east of the south window. It faces north into the room.
_place(cabinet_D, [3.00, 0.175, 0.35], 90, wall=walls[5])

# The tall shelf (o0023) is against the upper part of the east wall, well away
# from the door. It faces west into the room.
_place(shelf_A, [6.065, 4.65, 0.90], 180, wall=walls[0])

# Reinforce the required oven-between-cabinets relationship.
solver.distance_constraint(
    oven[0], cabinet_A[0], 0.72, 0.78, weight=10
)
solver.distance_constraint(
    oven[0], cabinet_F[0], 0.72, 0.78, weight=10
)
solver.align_with(oven[0], cabinet_A[0], angle=0)
solver.align_with(oven[0], cabinet_F[0], angle=0)


# ---------------------------------------------------------------------------
# Objects on cabinet_A
# ---------------------------------------------------------------------------

_place(box_A,    [0.70, 5.40, 0.99], -90, support=cabinet_A)
_place(bottle_A, [0.98, 5.42, 1.04], -90, support=cabinet_A)
_place(lamp_A,   [1.23, 5.40, 1.01], -90, support=cabinet_A)


# ---------------------------------------------------------------------------
# Cookware on the oven. The two pots sit side by side without overlapping.
# ---------------------------------------------------------------------------

_place(pot_A, [1.55, 5.38, 1.00], -90, support=oven)
_place(pot_B, [1.84, 5.38, 1.01], -90, support=oven)


# ---------------------------------------------------------------------------
# Objects on cabinet_F
# ---------------------------------------------------------------------------

_place(box_B,    [2.18, 5.39, 0.96], -90, support=cabinet_F)
_place(bottle_B, [2.43, 5.42, 1.02], -90, support=cabinet_F)
_place(bottle_C, [2.56, 5.42, 1.05], -90, support=cabinet_F)
_place(lamp_B,   [2.73, 5.40, 1.00], -90, support=cabinet_F)


# ---------------------------------------------------------------------------
# Microwave and a compact pantry stack on cabinet_C
# ---------------------------------------------------------------------------

_place(microwave, [3.35, 5.43, 1.05], -90, support=cabinet_C)
_place(box_C,     [3.35, 5.43, 1.30], -90, support=microwave)
_place(box_D,     [3.35, 5.43, 1.48], -90, support=box_C)
_place(food_A,    [3.35, 5.43, 1.60], -90, support=box_D)


# ---------------------------------------------------------------------------
# Sink-side objects on cabinet_E
# ---------------------------------------------------------------------------

_place(faucet,   [4.04, 5.40, 1.06], -90, support=cabinet_E)
_place(bottle_D, [4.28, 5.42, 1.035], -90, support=cabinet_E)
_place(lamp_C,   [4.55, 5.40, 1.00], -90, support=cabinet_E)
_place(cup_A,    [4.72, 5.58, 0.955], -90, support=cabinet_E)
_place(cup_B,    [4.57, 5.59, 0.95], -90, support=cabinet_E)


# ---------------------------------------------------------------------------
# Storage box and food items on the dishwasher
# ---------------------------------------------------------------------------

_place(box_E,    [5.10, 5.43, 0.95], -90, support=dishwasher)
_place(bottle_H, [4.97, 5.42, 1.18], -90, support=box_E)
_place(food_B,   [5.15, 5.42, 1.10], -90, support=box_E)
_place(food_C,   [5.15, 5.42, 1.195], -90, support=food_B)


# ---------------------------------------------------------------------------
# Objects on cabinet_B. Smaller containers are grouped on top of box_F.
# ---------------------------------------------------------------------------

_place(lamp_D, [5.64, 5.56, 0.81], -90, support=cabinet_B)
_place(box_F,  [6.04, 5.56, 0.76], -90, support=cabinet_B)

_place(bottle_E, [5.94, 5.53, 0.945], -90, support=box_F)
_place(bottle_F, [6.07, 5.53, 0.97],  -90, support=box_F)
_place(can_A,    [5.96, 5.64, 0.88],  -90, support=box_F)
_place(can_B,    [6.09, 5.64, 0.875], -90, support=box_F)


# ---------------------------------------------------------------------------
# Cookware station on cabinet_D. The pans and pot form a stable cookware
# stack, while lamp_E occupies the remaining end of the cabinet.
# ---------------------------------------------------------------------------

_place(pan_A,  [2.86, 0.17, 0.74], 90, support=cabinet_D)
_place(pan_B,  [2.86, 0.17, 0.825], 90, support=pan_A)
_place(pot_C,  [2.86, 0.17, 0.96], 90, support=pan_B)
_place(lamp_E, [3.25, 0.17, 0.80], 90, support=cabinet_D)


# ---------------------------------------------------------------------------
# Shallow upper shelf and organized display/storage objects
# ---------------------------------------------------------------------------

_place(shelf_B, [6.06, 4.70, 1.825], 180, support=shelf_A)

# Taller display pieces occupy the rear portion of the shelf.
_place(book, [5.96, 4.38, 1.99], 180, support=shelf_B)
_place(vase, [6.10, 4.38, 2.01], 180, support=shelf_B)

# Bottles are arranged in three narrow columns with sufficient spacing.
_place(bottle_G, [5.96, 4.62, 1.96], 180, support=shelf_B)
_place(bottle_I, [6.06, 4.62, 1.965], 180, support=shelf_B)
_place(bottle_J, [6.16, 4.62, 2.005], 180, support=shelf_B)

_place(bottle_K, [5.96, 4.78, 1.99], 180, support=shelf_B)
_place(bottle_L, [6.06, 4.78, 1.97], 180, support=shelf_B)
_place(bottle_M, [6.16, 4.78, 1.985], 180, support=shelf_B)

_place(bottle_N, [5.96, 4.94, 1.975], 180, support=shelf_B)
_place(bottle_O, [6.06, 4.94, 1.995], 180, support=shelf_B)
_place(bottle_P, [6.16, 4.94, 1.975], 180, support=shelf_B)

solver.constraints = []
bottle_E[0].position = [5.940000057220459, 5.53000020980835, 0.9449999928474426]
bottle_E[0].rotation = [0, 0, -1.5582299555380688]
bottle_E[0].optimize = 2
bottle_H[0].position = [4.96999979019165, 5.420000076293945, 1.1800000667572021]
bottle_H[0].rotation = [0, 0, -1.5582299555380688]
bottle_H[0].optimize = 2
box_A[0].position = [0.699999988079071, 5.400000095367432, 0.9900000095367432]
box_A[0].rotation = [0, 0, -1.5582299555380688]
box_A[0].optimize = 2
pan_B[0].position = [2.859999895095825, 0.17000000178813934, 0.8250000476837158]
pan_B[0].rotation = [0, 0, 1.586504290712113]
pan_B[0].optimize = 2
bottle_O[0].position = [6.059999942779541, 4.940000057220459, 1.994999885559082]
bottle_O[0].rotation = [0, 0, -3.1290262823329655]
bottle_O[0].optimize = 2
cabinet_B[0].position = [5.820000171661377, 5.563361644744873, 0.3499999940395355]
cabinet_B[0].rotation = [0, 0, -1.5620341067611838]
cabinet_B[0].optimize = 2
bottle_F[0].position = [6.070000171661377, 5.53000020980835, 0.9700000286102295]
bottle_F[0].rotation = [0, 0, -1.5582299555380688]
bottle_F[0].optimize = 2
bottle_D[0].position = [4.28000020980835, 5.420000076293945, 1.034999966621399]
bottle_D[0].rotation = [0, 0, -1.5582299555380688]
bottle_D[0].optimize = 2
bottle_J[0].position = [6.159999847412109, 4.619999885559082, 2.004999876022339]
bottle_J[0].rotation = [0, 0, -3.1290262823329655]
bottle_J[0].optimize = 2
book[0].position = [5.960000038146973, 4.380000114440918, 1.9899998903274536]
book[0].rotation = [0, 0, -3.1290262823329655]
book[0].optimize = 2
shelf_A[0].position = [6.061467170715332, 4.650000095367432, 0.8999999761581421]
shelf_A[0].rotation = [0, 0, -3.135941139029737]
shelf_A[0].optimize = 2
bottle_L[0].position = [6.059999942779541, 4.78000020980835, 1.96999990940094]
bottle_L[0].rotation = [0, 0, -3.1290262823329655]
bottle_L[0].optimize = 2
bottle_C[0].position = [2.559999942779541, 5.420000076293945, 1.0499999523162842]
bottle_C[0].rotation = [0, 0, -1.5582299555380688]
bottle_C[0].optimize = 2
lamp_C[0].position = [4.550000190734863, 5.400000095367432, 1.0]
lamp_C[0].rotation = [0, 0, -1.5582299555380688]
lamp_C[0].optimize = 2
cabinet_C[0].position = [3.3499999046325684, 5.428840160369873, 0.44999998807907104]
cabinet_C[0].rotation = [0, 0, -1.565144806956787]
cabinet_C[0].optimize = 2
shelf_B[0].position = [6.059999942779541, 4.699999809265137, 1.8249999284744263]
shelf_B[0].rotation = [0, 0, -3.094468761670742]
shelf_B[0].optimize = 2
cup_A[0].position = [4.71999979019165, 5.579999923706055, 0.9549999833106995]
cup_A[0].rotation = [0, 0, -1.5582299555380688]
cup_A[0].optimize = 2
bottle_I[0].position = [6.059999942779541, 4.619999885559082, 1.9649999141693115]
bottle_I[0].rotation = [0, 0, -3.1290262823329655]
bottle_I[0].optimize = 2
pot_C[0].position = [2.859999895095825, 0.17000000178813934, 0.9600000381469727]
pot_C[0].rotation = [0, 0, 1.5833626980517244]
pot_C[0].optimize = 2
box_E[0].position = [5.099999904632568, 5.429999828338623, 0.9500000476837158]
box_E[0].rotation = [0, 0, -1.5519467713960802]
box_E[0].optimize = 2
faucet[0].position = [4.039999961853027, 5.400000095367432, 1.059999942779541]
faucet[0].rotation = [0, 0, -1.5582299555380688]
faucet[0].optimize = 2
lamp_D[0].position = [5.639999866485596, 5.559999942779541, 0.8100000023841858]
lamp_D[0].rotation = [0, 0, -1.5582299555380688]
lamp_D[0].optimize = 2
cabinet_E[0].position = [4.300000190734863, 5.421858787536621, 0.44999998807907104]
cabinet_E[0].rotation = [0, 0, -1.5527014171561073]
cabinet_E[0].optimize = 2
pot_B[0].position = [1.840000033378601, 5.380000114440918, 1.0099999904632568]
pot_B[0].rotation = [0, 0, -1.5582299555380688]
pot_B[0].optimize = 2
pot_A[0].position = [1.5499999523162842, 5.380000114440918, 1.0]
pot_A[0].rotation = [0, 0, -1.5582299555380688]
pot_A[0].optimize = 2
lamp_A[0].position = [1.2300000190734863, 5.400000095367432, 1.0099999904632568]
lamp_A[0].rotation = [0, 0, -1.5582299555380688]
lamp_A[0].optimize = 2
lamp_B[0].position = [2.7300000190734863, 5.400000095367432, 1.0]
lamp_B[0].rotation = [0, 0, -1.5582299555380688]
lamp_B[0].optimize = 2
bottle_G[0].position = [5.960000038146973, 4.619999885559082, 1.959999918937683]
bottle_G[0].rotation = [0, 0, -3.1290262823329655]
bottle_G[0].optimize = 2
bottle_N[0].position = [5.960000038146973, 4.940000057220459, 1.9749999046325684]
bottle_N[0].rotation = [0, 0, -3.1290262823329655]
bottle_N[0].optimize = 2
food_C[0].position = [5.150000095367432, 5.420000076293945, 1.1949999332427979]
food_C[0].rotation = [0, 0, -1.5582299555380688]
food_C[0].optimize = 2
lamp_E[0].position = [3.25, 0.17000000178813934, 0.800000011920929]
lamp_E[0].rotation = [0, 0, 1.5833626980517244]
lamp_E[0].optimize = 2
box_F[0].position = [6.039999961853027, 5.559999942779541, 0.7599999904632568]
box_F[0].rotation = [0, 0, -1.5456635866850408]
box_F[0].optimize = 2
box_C[0].position = [3.3499999046325684, 5.429999828338623, 1.2999999523162842]
box_C[0].rotation = [0, 0, -1.5550883628776802]
box_C[0].optimize = 2
food_A[0].position = [3.3499999046325684, 5.429999828338623, 1.600000023841858]
food_A[0].rotation = [0, 0, -1.5582299555380688]
food_A[0].optimize = 2
cabinet_F[0].position = [2.450000047683716, 5.42188835144043, 0.44999998807907104]
cabinet_F[0].rotation = [0, 0, -1.549590325245573]
cabinet_F[0].optimize = 2
can_B[0].position = [6.090000152587891, 5.639999866485596, 0.875]
can_B[0].rotation = [0, 0, -1.5582299555380688]
can_B[0].optimize = 2
vase[0].position = [6.099999904632568, 4.380000114440918, 2.009999990463257]
vase[0].rotation = [0, 0, -3.1290262823329655]
vase[0].optimize = 2
oven[0].position = [1.7000000476837158, 5.426599979400635, 0.44999998807907104]
oven[0].rotation = [0, 0, -1.5495903208978976]
oven[0].optimize = 2
cabinet_D[0].position = [3.0, 0.17849811911582947, 0.3499999940395355]
cabinet_D[0].rotation = [0, 0, 1.5795585477508047]
cabinet_D[0].optimize = 2
can_A[0].position = [5.960000038146973, 5.639999866485596, 0.8799999952316284]
can_A[0].rotation = [0, 0, -1.5582299555380688]
can_A[0].optimize = 2
food_B[0].position = [5.150000095367432, 5.420000076293945, 1.100000023841858]
food_B[0].rotation = [0, 0, -1.5550883628776802]
food_B[0].optimize = 2
box_B[0].position = [2.180000066757202, 5.389999866485596, 0.9599999785423279]
box_B[0].rotation = [0, 0, -1.5582299555380688]
box_B[0].optimize = 2
bottle_B[0].position = [2.430000066757202, 5.420000076293945, 1.0199999809265137]
bottle_B[0].rotation = [0, 0, -1.5582299555380688]
bottle_B[0].optimize = 2
bottle_K[0].position = [5.960000038146973, 4.78000020980835, 1.9899998903274536]
bottle_K[0].rotation = [0, 0, -3.1290262823329655]
bottle_K[0].optimize = 2
cup_B[0].position = [4.570000171661377, 5.590000152587891, 0.949999988079071]
cup_B[0].rotation = [0, 0, -1.5582299555380688]
cup_B[0].optimize = 2
bottle_A[0].position = [0.9800000190734863, 5.420000076293945, 1.0399999618530273]
bottle_A[0].rotation = [0, 0, -1.5582299555380688]
bottle_A[0].optimize = 2
cabinet_A[0].position = [0.9599993824958801, 5.423272132873535, 0.44999998807907104]
cabinet_A[0].rotation = [0, 0, -1.5527014190004387]
cabinet_A[0].optimize = 2
dishwasher[0].position = [5.099999904632568, 5.4300007820129395, 0.42500001192092896]
dishwasher[0].rotation = [0, 0, -1.565144803778184]
dishwasher[0].optimize = 2
microwave[0].position = [3.3499999046325684, 5.429999828338623, 1.0499999523162842]
microwave[0].rotation = [0, 0, -1.5550883628776802]
microwave[0].optimize = 2
bottle_P[0].position = [6.159999847412109, 4.940000057220459, 1.9749999046325684]
bottle_P[0].rotation = [0, 0, -3.1290262823329655]
bottle_P[0].optimize = 2
box_D[0].position = [3.3499999046325684, 5.429999828338623, 1.4800000190734863]
box_D[0].rotation = [0, 0, -1.5550883628776802]
box_D[0].optimize = 2
pan_A[0].position = [2.859999895095825, 0.17000000178813934, 0.7400000095367432]
pan_A[0].rotation = [0, 0, 1.586504290712113]
pan_A[0].optimize = 2
bottle_M[0].position = [6.159999847412109, 4.78000020980835, 1.9849998950958252]
bottle_M[0].rotation = [0, 0, -3.1290262823329655]
bottle_M[0].optimize = 2

