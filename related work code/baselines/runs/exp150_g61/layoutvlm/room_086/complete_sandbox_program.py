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
box_A = Assets(description="box", size=[0.18, 0.24, 0.32], placements=[AssetInstance() for _ in range(1)])
bottle_A = Assets(description="bottle", size=[0.08, 0.08, 0.30], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="lamp", size=[0.22, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="bottle", size=[0.07, 0.07, 0.24], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.62, 0.90, 0.90], placements=[AssetInstance() for _ in range(1)])
bottle_C = Assets(description="bottle", size=[0.09, 0.09, 0.31], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.35, 0.80, 0.75], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.22, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
lamp_C = Assets(description="lamp", size=[0.22, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
cabinet_C = Assets(description="cabinet", size=[0.62, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
microwave = Assets(description="microwave", size=[0.42, 0.52, 0.31], placements=[AssetInstance() for _ in range(1)])
pot_A = Assets(description="pot", size=[0.25, 0.32, 0.20], placements=[AssetInstance() for _ in range(1)])
bottle_D = Assets(description="bottle", size=[0.08, 0.08, 0.28], placements=[AssetInstance() for _ in range(1)])
lamp_D = Assets(description="lamp", size=[0.22, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
can_A = Assets(description="can", size=[0.08, 0.08, 0.12], placements=[AssetInstance() for _ in range(1)])
cabinet_D = Assets(description="cabinet", size=[0.62, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
bottle_E = Assets(description="bottle", size=[0.07, 0.07, 0.22], placements=[AssetInstance() for _ in range(1)])
box_B = Assets(description="box", size=[0.12, 0.20, 0.28], placements=[AssetInstance() for _ in range(1)])
pan_A = Assets(description="pan", size=[0.48, 0.28, 0.08], placements=[AssetInstance() for _ in range(1)])
book = Assets(description="book", size=[0.04, 0.21, 0.27], placements=[AssetInstance() for _ in range(1)])
bottle_F = Assets(description="bottle", size=[0.08, 0.08, 0.30], placements=[AssetInstance() for _ in range(1)])
bottle_G = Assets(description="bottle", size=[0.07, 0.07, 0.25], placements=[AssetInstance() for _ in range(1)])
pot_B = Assets(description="pot", size=[0.24, 0.30, 0.18], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="shelf", size=[0.32, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
box_C = Assets(description="box", size=[0.10, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
box_D = Assets(description="box", size=[0.15, 0.22, 0.30], placements=[AssetInstance() for _ in range(1)])
food_A = Assets(description="food", size=[0.14, 0.24, 0.12], placements=[AssetInstance() for _ in range(1)])
faucet = Assets(description="faucet", size=[0.25, 0.18, 0.38], placements=[AssetInstance() for _ in range(1)])
cabinet_E = Assets(description="cabinet", size=[0.35, 1.00, 0.75], placements=[AssetInstance() for _ in range(1)])
cabinet_F = Assets(description="cabinet", size=[0.62, 0.90, 0.90], placements=[AssetInstance() for _ in range(1)])
cup_A = Assets(description="cup", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
box_E = Assets(description="box", size=[0.10, 0.16, 0.22], placements=[AssetInstance() for _ in range(1)])
bottle_H = Assets(description="bottle", size=[0.09, 0.09, 0.32], placements=[AssetInstance() for _ in range(1)])
box_F = Assets(description="box", size=[0.18, 0.25, 0.12], placements=[AssetInstance() for _ in range(1)])
bottle_I = Assets(description="bottle", size=[0.06, 0.06, 0.18], placements=[AssetInstance() for _ in range(1)])
bottle_J = Assets(description="bottle", size=[0.06, 0.06, 0.18], placements=[AssetInstance() for _ in range(1)])
bottle_K = Assets(description="bottle", size=[0.07, 0.07, 0.23], placements=[AssetInstance() for _ in range(1)])
bottle_L = Assets(description="bottle", size=[0.08, 0.08, 0.29], placements=[AssetInstance() for _ in range(1)])
vase = Assets(description="vase", size=[0.16, 0.16, 0.28], placements=[AssetInstance() for _ in range(1)])
food_B = Assets(description="food", size=[0.15, 0.18, 0.10], placements=[AssetInstance() for _ in range(1)])
bottle_M = Assets(description="bottle", size=[0.08, 0.08, 0.27], placements=[AssetInstance() for _ in range(1)])
bottle_N = Assets(description="bottle", size=[0.07, 0.07, 0.24], placements=[AssetInstance() for _ in range(1)])
pan_B = Assets(description="pan", size=[0.44, 0.26, 0.07], placements=[AssetInstance() for _ in range(1)])
bottle_O = Assets(description="bottle", size=[0.09, 0.09, 0.30], placements=[AssetInstance() for _ in range(1)])
can_B = Assets(description="can", size=[0.10, 0.10, 0.15], placements=[AssetInstance() for _ in range(1)])
dishwasher = Assets(description="dishwasher", size=[0.60, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
bottle_P = Assets(description="bottle", size=[0.08, 0.08, 0.26], placements=[AssetInstance() for _ in range(1)])
food_C = Assets(description="food", size=[0.16, 0.28, 0.12], placements=[AssetInstance() for _ in range(1)])
oven = Assets(description="oven", size=[0.62, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.28, 1.00, 0.75], placements=[AssetInstance() for _ in range(1)])
lamp_E = Assets(description="lamp", size=[0.22, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
cup_B = Assets(description="cup", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
pot_C = Assets(description="pot", size=[0.28, 0.36, 0.24], placements=[AssetInstance() for _ in range(1)])

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

box_A[0].position = [3.2215663986335703, 5.378347727477083, 0.16]
box_A[0].rotation = [0, 0, 0]
bottle_A[0].position = [5.196069473600862, 4.052804178511285, 0.15]
bottle_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [1.078614968675854, 0.15313903349273428, 0.125]
lamp_A[0].rotation = [0, 0, 0]
bottle_B[0].position = [3.7653656135690814, 5.369368979992522, 0.12]
bottle_B[0].rotation = [0, 0, 0]
cabinet_A[0].position = [5.441732041589875, 1.62899303416095, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
bottle_C[0].position = [1.1378438892140301, 0.5351363505718176, 0.155]
bottle_C[0].rotation = [0, 0, 0]
cabinet_B[0].position = [2.8214237365894608, 2.3908856095822086, 0.375]
cabinet_B[0].rotation = [0, 0, 0]
lamp_B[0].position = [5.339214490323414, 3.017903760920819, 0.125]
lamp_B[0].rotation = [0, 0, 0]
lamp_C[0].position = [3.6193879696794493, 1.83589750934521, 0.125]
lamp_C[0].rotation = [0, 0, 0]
cabinet_C[0].position = [5.186665616212649, 0.4369677782617163, 0.45]
cabinet_C[0].rotation = [0, 0, 0]
microwave[0].position = [0.23540796164503955, 2.070793038152251, 0.155]
microwave[0].rotation = [0, 0, 0]
pot_A[0].position = [5.01222506596378, 0.049967372864377954, 0.1]
pot_A[0].rotation = [0, 0, 0]
bottle_D[0].position = [5.871804099900303, 0.17859314615020058, 0.14]
bottle_D[0].rotation = [0, 0, 0]
lamp_D[0].position = [1.9586899148881594, 4.104906615304944, 0.125]
lamp_D[0].rotation = [0, 0, 0]
can_A[0].position = [3.9646139016835518, 0.7497016710366691, 0.06]
can_A[0].rotation = [0, 0, 0]
cabinet_D[0].position = [2.2325245947447647, 5.088568956754181, 0.45]
cabinet_D[0].rotation = [0, 0, 0]
bottle_E[0].position = [5.418502633714912, 3.483191082989333, 0.11]
bottle_E[0].rotation = [0, 0, 0]
box_B[0].position = [4.868634966044175, 4.407527345218538, 0.14]
box_B[0].rotation = [0, 0, 0]
pan_A[0].position = [3.9360370760149297, 2.5199173377705932, 0.04]
pan_A[0].rotation = [0, 0, 0]
book[0].position = [4.03605167563475, 4.591060414018027, 0.135]
book[0].rotation = [0, 0, 0]
bottle_F[0].position = [4.429116767103689, 4.899349904885062, 0.15]
bottle_F[0].rotation = [0, 0, 0]
bottle_G[0].position = [3.6522361566588857, 3.7572809549018586, 0.125]
bottle_G[0].rotation = [0, 0, 0]
pot_B[0].position = [0.813170593490154, 1.0870725032336976, 0.09]
pot_B[0].rotation = [0, 0, 0]
shelf_A[0].position = [4.848590833439954, 0.14857471111237783, 0.9]
shelf_A[0].rotation = [0, 0, 0]
box_C[0].position = [2.9515386794184324, 3.4595401547401146, 0.125]
box_C[0].rotation = [0, 0, 0]
box_D[0].position = [3.6049486100865233, 4.334106780079395, 0.15]
box_D[0].rotation = [0, 0, 0]
food_A[0].position = [2.96433288159858, 4.599273641048633, 0.06]
food_A[0].rotation = [0, 0, 0]
faucet[0].position = [6.224841321391776, 5.197821017194376, 0.19]
faucet[0].rotation = [0, 0, 0]
cabinet_E[0].position = [2.379051026336035, 1.9017537586050675, 0.375]
cabinet_E[0].rotation = [0, 0, 0]
cabinet_F[0].position = [2.7760947674040457, 2.0422406638831734, 0.45]
cabinet_F[0].rotation = [0, 0, 0]
cup_A[0].position = [3.8762810296637795, 4.255343010397551, 0.05]
cup_A[0].rotation = [0, 0, 0]
box_E[0].position = [0.7978978335769212, 1.0125952746191533, 0.11]
box_E[0].rotation = [0, 0, 0]
bottle_H[0].position = [5.663344997586378, 4.174130351383636, 0.16]
bottle_H[0].rotation = [0, 0, 0]
box_F[0].position = [5.072708383663375, 0.14118878873247995, 0.06]
box_F[0].rotation = [0, 0, 0]
bottle_I[0].position = [2.585334098560656, 4.343587388827851, 0.09]
bottle_I[0].rotation = [0, 0, 0]
bottle_J[0].position = [1.3681182207751077, 0.9824468105513291, 0.09]
bottle_J[0].rotation = [0, 0, 0]
bottle_K[0].position = [5.737132733272494, 0.18177147918379727, 0.115]
bottle_K[0].rotation = [0, 0, 0]
bottle_L[0].position = [2.6682621826995945, 3.995419659317789, 0.145]
bottle_L[0].rotation = [0, 0, 0]
vase[0].position = [6.14763842876295, 0.3672635261715662, 0.14]
vase[0].rotation = [0, 0, 0]
food_B[0].position = [1.8891655060558352, 3.4350911512529114, 0.05]
food_B[0].rotation = [0, 0, 0]
bottle_M[0].position = [6.097510225645231, 1.2775489054794409, 0.135]
bottle_M[0].rotation = [0, 0, 0]
bottle_N[0].position = [6.134578539050824, 0.21999197714331348, 0.12]
bottle_N[0].rotation = [0, 0, 0]
pan_B[0].position = [0.2809665953937519, 0.7218654118245145, 0.035]
pan_B[0].rotation = [0, 0, 0]
bottle_O[0].position = [4.666431071698196, 1.5599307542097547, 0.15]
bottle_O[0].rotation = [0, 0, 0]
can_B[0].position = [3.4646150092643406, 0.9978887934165062, 0.075]
can_B[0].rotation = [0, 0, 0]
dishwasher[0].position = [2.670067632775374, 4.312449453859043, 0.425]
dishwasher[0].rotation = [0, 0, 0]
bottle_P[0].position = [5.081646232753678, 3.114391764265525, 0.13]
bottle_P[0].rotation = [0, 0, 0]
food_C[0].position = [5.713362312118993, 0.6026887197366393, 0.06]
food_C[0].rotation = [0, 0, 0]
oven[0].position = [1.724627945208562, 3.557785057477044, 0.45]
oven[0].rotation = [0, 0, 0]
shelf_B[0].position = [1.7315433363228672, 4.224328160143426, 0.375]
shelf_B[0].rotation = [0, 0, 0]
lamp_E[0].position = [3.6931627922038297, 0.7610112035510972, 0.125]
lamp_E[0].rotation = [0, 0, 0]
cup_B[0].position = [3.456922216231299, 0.5617480526367375, 0.05]
cup_B[0].rotation = [0, 0, 0]
pot_C[0].position = [0.39435200124442576, 0.9896329200439374, 0.12]
pot_C[0].rotation = [0, 0, 0]
box_A[0].position = [3.2215663986335703, 5.378347727477083, 0.16]
box_A[0].rotation = [0, 0, 0]
bottle_A[0].position = [5.196069473600862, 4.052804178511285, 0.15]
bottle_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [1.078614968675854, 0.15313903349273428, 0.125]
lamp_A[0].rotation = [0, 0, 0]
bottle_B[0].position = [3.7653656135690814, 5.369368979992522, 0.12]
bottle_B[0].rotation = [0, 0, 0]
cabinet_A[0].position = [5.441732041589875, 1.62899303416095, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
bottle_C[0].position = [1.1378438892140301, 0.5351363505718176, 0.155]
bottle_C[0].rotation = [0, 0, 0]
cabinet_B[0].position = [2.8214237365894608, 2.3908856095822086, 0.375]
cabinet_B[0].rotation = [0, 0, 0]
lamp_B[0].position = [5.339214490323414, 3.017903760920819, 0.125]
lamp_B[0].rotation = [0, 0, 0]
lamp_C[0].position = [3.6193879696794493, 1.83589750934521, 0.125]
lamp_C[0].rotation = [0, 0, 0]
cabinet_C[0].position = [5.186665616212649, 0.4369677782617163, 0.45]
cabinet_C[0].rotation = [0, 0, 0]
microwave[0].position = [0.23540796164503955, 2.070793038152251, 0.155]
microwave[0].rotation = [0, 0, 0]
pot_A[0].position = [5.01222506596378, 0.049967372864377954, 0.1]
pot_A[0].rotation = [0, 0, 0]
bottle_D[0].position = [5.871804099900303, 0.17859314615020058, 0.14]
bottle_D[0].rotation = [0, 0, 0]
lamp_D[0].position = [1.9586899148881594, 4.104906615304944, 0.125]
lamp_D[0].rotation = [0, 0, 0]
can_A[0].position = [3.9646139016835518, 0.7497016710366691, 0.06]
can_A[0].rotation = [0, 0, 0]
cabinet_D[0].position = [2.2325245947447647, 5.088568956754181, 0.45]
cabinet_D[0].rotation = [0, 0, 0]
bottle_E[0].position = [5.418502633714912, 3.483191082989333, 0.11]
bottle_E[0].rotation = [0, 0, 0]
box_B[0].position = [4.868634966044175, 4.407527345218538, 0.14]
box_B[0].rotation = [0, 0, 0]
pan_A[0].position = [3.9360370760149297, 2.5199173377705932, 0.04]
pan_A[0].rotation = [0, 0, 0]
book[0].position = [4.03605167563475, 4.591060414018027, 0.135]
book[0].rotation = [0, 0, 0]
bottle_F[0].position = [4.429116767103689, 4.899349904885062, 0.15]
bottle_F[0].rotation = [0, 0, 0]
bottle_G[0].position = [3.6522361566588857, 3.7572809549018586, 0.125]
bottle_G[0].rotation = [0, 0, 0]
pot_B[0].position = [0.813170593490154, 1.0870725032336976, 0.09]
pot_B[0].rotation = [0, 0, 0]
shelf_A[0].position = [4.848590833439954, 0.14857471111237783, 0.9]
shelf_A[0].rotation = [0, 0, 0]
box_C[0].position = [2.9515386794184324, 3.4595401547401146, 0.125]
box_C[0].rotation = [0, 0, 0]
box_D[0].position = [3.6049486100865233, 4.334106780079395, 0.15]
box_D[0].rotation = [0, 0, 0]
food_A[0].position = [2.96433288159858, 4.599273641048633, 0.06]
food_A[0].rotation = [0, 0, 0]
faucet[0].position = [6.224841321391776, 5.197821017194376, 0.19]
faucet[0].rotation = [0, 0, 0]
cabinet_E[0].position = [2.379051026336035, 1.9017537586050675, 0.375]
cabinet_E[0].rotation = [0, 0, 0]
cabinet_F[0].position = [2.7760947674040457, 2.0422406638831734, 0.45]
cabinet_F[0].rotation = [0, 0, 0]
cup_A[0].position = [3.8762810296637795, 4.255343010397551, 0.05]
cup_A[0].rotation = [0, 0, 0]
box_E[0].position = [0.7978978335769212, 1.0125952746191533, 0.11]
box_E[0].rotation = [0, 0, 0]
bottle_H[0].position = [5.663344997586378, 4.174130351383636, 0.16]
bottle_H[0].rotation = [0, 0, 0]
box_F[0].position = [5.072708383663375, 0.14118878873247995, 0.06]
box_F[0].rotation = [0, 0, 0]
bottle_I[0].position = [2.585334098560656, 4.343587388827851, 0.09]
bottle_I[0].rotation = [0, 0, 0]
bottle_J[0].position = [1.3681182207751077, 0.9824468105513291, 0.09]
bottle_J[0].rotation = [0, 0, 0]
bottle_K[0].position = [5.737132733272494, 0.18177147918379727, 0.115]
bottle_K[0].rotation = [0, 0, 0]
bottle_L[0].position = [2.6682621826995945, 3.995419659317789, 0.145]
bottle_L[0].rotation = [0, 0, 0]
vase[0].position = [6.14763842876295, 0.3672635261715662, 0.14]
vase[0].rotation = [0, 0, 0]
food_B[0].position = [1.8891655060558352, 3.4350911512529114, 0.05]
food_B[0].rotation = [0, 0, 0]
bottle_M[0].position = [6.097510225645231, 1.2775489054794409, 0.135]
bottle_M[0].rotation = [0, 0, 0]
bottle_N[0].position = [6.134578539050824, 0.21999197714331348, 0.12]
bottle_N[0].rotation = [0, 0, 0]
pan_B[0].position = [0.2809665953937519, 0.7218654118245145, 0.035]
pan_B[0].rotation = [0, 0, 0]
bottle_O[0].position = [4.666431071698196, 1.5599307542097547, 0.15]
bottle_O[0].rotation = [0, 0, 0]
can_B[0].position = [3.4646150092643406, 0.9978887934165062, 0.075]
can_B[0].rotation = [0, 0, 0]
dishwasher[0].position = [2.670067632775374, 4.312449453859043, 0.425]
dishwasher[0].rotation = [0, 0, 0]
bottle_P[0].position = [5.081646232753678, 3.114391764265525, 0.13]
bottle_P[0].rotation = [0, 0, 0]
food_C[0].position = [5.713362312118993, 0.6026887197366393, 0.06]
food_C[0].rotation = [0, 0, 0]
oven[0].position = [1.724627945208562, 3.557785057477044, 0.45]
oven[0].rotation = [0, 0, 0]
shelf_B[0].position = [1.7315433363228672, 4.224328160143426, 0.375]
shelf_B[0].rotation = [0, 0, 0]
lamp_E[0].position = [3.6931627922038297, 0.7610112035510972, 0.125]
lamp_E[0].rotation = [0, 0, 0]
cup_B[0].position = [3.456922216231299, 0.5617480526367375, 0.05]
cup_B[0].rotation = [0, 0, 0]
pot_C[0].position = [0.39435200124442576, 0.9896329200439374, 0.12]
pot_C[0].rotation = [0, 0, 0]

solver.constraints = []

# North-wall cooking run: cabinet_A (o0004), oven, cabinet_F (o0029).
# All depths are measured along local x; rotating -90 degrees makes the
# appliances face south, into the room. The east-side doorway stays clear.
def place_floor(asset_group, x, y, yaw, wall_index):
    instance = asset_group[0]
    instance.position = [x, y, asset_group.size[2] / 2]
    instance.rotation = [0, 0, radians(yaw)]

    solver.against_wall(instance, walls[wall_index])
    solver.distance_constraint(
        instance,
        AssetInstance(position=list(instance.position)),
        0, 0, weight=10,
    )
    solver.align_with(
        instance,
        AssetInstance(rotation=[0, 0, radians(yaw)]),
    )


place_floor(cabinet_A, 1.40, 5.43, -90, 1)
place_floor(oven,      2.17, 5.43, -90, 1)
place_floor(cabinet_F, 2.94, 5.43, -90, 1)
place_floor(cabinet_C, 4.01, 5.43, -90, 1)
place_floor(cabinet_D, 5.03, 5.43, -90, 1)
place_floor(dishwasher, 5.75, 5.44, -90, 1)

# Preserve the oven's position between its two neighboring cabinets.
# The fixed center anchors above preserve the ordering as well as spacing.
solver.distance_constraint(oven[0], cabinet_A[0], 0.77, 0.77, weight=10)
solver.distance_constraint(oven[0], cabinet_F[0], 0.77, 0.77, weight=10)
solver.align_with(oven[0], cabinet_A[0])
solver.align_with(cabinet_F[0], oven[0])

# Shallow storage along the south wall starts beyond the south window.
# These units face north and leave the middle of the kitchen unobstructed.
place_floor(cabinet_B, 2.50, 0.175, 90, 5)
place_floor(cabinet_E, 3.50, 0.175, 90, 5)
place_floor(shelf_B,   4.70, 0.140, 90, 5)

# Tall shelf_A (o0023) occupies the east wall north of the door.
# Its footprint spans y=3.50..4.70, well away from the door at y=2.54.
place_floor(shelf_A, 6.08, 4.10, 180, 0)


def place_on_surface(asset_group, support_group, x, y, yaw=0):
    """Place an item on a supplied surface, retaining its chosen clear slot."""
    instance = asset_group[0]
    support = support_group[0]
    surface_z = support.position[2] + support_group.size[2] / 2

    instance.position = [x, y, surface_z + asset_group.size[2] / 2]
    instance.rotation = [0, 0, radians(yaw)]

    solver.on_top_of(instance, support)
    solver.distance_constraint(
        instance,
        AssetInstance(position=list(instance.position)),
        0, 0, weight=10,
    )
    solver.align_with(
        instance,
        AssetInstance(rotation=[0, 0, radians(yaw)]),
    )


# Microwave station: retain separate landing space for the lamp and bottle.
place_on_surface(microwave, cabinet_A, 1.48, 5.43, -90)
place_on_surface(lamp_A,    cabinet_A, 1.06, 5.43, -90)
place_on_surface(bottle_A,  cabinet_A, 1.80, 5.50)

# The two small food packages occupy distinct areas of the microwave top.
place_on_surface(food_C, microwave, 1.48, 5.32, 90)
place_on_surface(food_A, microwave, 1.48, 5.52, 90)

# Cooking and washing stations. The faucet is toward the rear edge of
# cabinet_F, with the cup and food in front, not underneath it.
place_on_surface(pot_A,    oven,      2.04, 5.42)
place_on_surface(faucet,   cabinet_F, 2.94, 5.58, -90)
place_on_surface(cup_A,    cabinet_F, 2.66, 5.27)
place_on_surface(bottle_B, cabinet_F, 3.25, 5.57)
place_on_surface(bottle_C, cabinet_F, 3.24, 5.30)
place_on_surface(food_B,   cabinet_F, 2.93, 5.26)

# Main preparation counter: cookware in front, bottles along the back.
place_on_surface(pot_B,    cabinet_C, 3.65, 5.42)
place_on_surface(pan_A,    cabinet_C, 4.16, 5.40)
place_on_surface(bottle_D, cabinet_C, 3.87, 5.64)
place_on_surface(bottle_E, cabinet_C, 4.43, 5.64)
place_on_surface(can_A,    cabinet_C, 4.45, 5.27)
place_on_surface(bottle_M, cabinet_C, 3.55, 5.66)
place_on_surface(bottle_N, cabinet_C, 3.73, 5.66)
place_on_surface(bottle_O, cabinet_C, 4.07, 5.65)
place_on_surface(bottle_P, cabinet_C, 4.25, 5.65)

place_on_surface(pan_B,    cabinet_D, 5.03, 5.37)
place_on_surface(bottle_F, cabinet_D, 4.76, 5.62)
place_on_surface(bottle_G, cabinet_D, 5.30, 5.62)
place_on_surface(can_B,    cabinet_D, 5.31, 5.25)

# These items sit fully within the dishwasher's top footprint.
place_on_surface(pot_C,    dishwasher, 5.75, 5.43)
place_on_surface(bottle_H, dishwasher, 5.97, 5.65)
place_on_surface(cup_B,    dishwasher, 5.52, 5.24)

# South-wall storage surfaces: rotate the boxes to fit the shallow tops.
place_on_surface(lamp_B,   cabinet_B, 2.25, 0.175, 90)
place_on_surface(box_A,    cabinet_B, 2.53, 0.175, 90)
place_on_surface(bottle_I, cabinet_B, 2.78, 0.175)

place_on_surface(lamp_C,   cabinet_E, 3.15, 0.175, 90)
place_on_surface(box_B,    cabinet_E, 3.40, 0.175, 90)
place_on_surface(box_C,    cabinet_E, 3.65, 0.175, 90)
place_on_surface(bottle_J, cabinet_E, 3.88, 0.175)

place_on_surface(lamp_D,   shelf_B, 4.34, 0.14, 90)
place_on_surface(box_D,    shelf_B, 4.62, 0.14, 90)
place_on_surface(box_E,    shelf_B, 4.87, 0.14, 90)
place_on_surface(bottle_K, shelf_B, 5.08, 0.14)

# Use the tall shelf's top surface rather than assuming unspecified
# internal shelf heights. Each object has its own nonoverlapping slot.
place_on_surface(lamp_E,   shelf_A, 6.08, 3.65)
place_on_surface(box_F,    shelf_A, 6.08, 3.91)
place_on_surface(book,     shelf_A, 6.08, 4.18)
place_on_surface(vase,     shelf_A, 6.08, 4.43)
place_on_surface(bottle_L, shelf_A, 6.08, 4.63)

solver.constraints = []
bottle_C[0].position = [3.240000009536743, 5.300000190734863, 1.0549999475479126]
bottle_C[0].rotation = [0, 0, 0.01256637125682779]
bottle_C[0].optimize = 2
microwave[0].position = [1.4800000190734863, 5.429999828338623, 1.0549999475479126]
microwave[0].rotation = [0, 0, -1.5519467713960802]
microwave[0].optimize = 2
pot_B[0].position = [3.6500000953674316, 5.420000076293945, 0.9900000095367432]
pot_B[0].rotation = [0, 0, 0.01256637125682779]
pot_B[0].optimize = 2
dishwasher[0].position = [5.75, 5.4358696937561035, 0.42500001192092896]
dishwasher[0].rotation = [0, 0, -1.5707970956858892]
dishwasher[0].optimize = 2
pan_B[0].position = [5.03000020980835, 5.369999885559082, 0.9350000023841858]
pan_B[0].rotation = [0, 0, 0.01256637125682779]
pan_B[0].optimize = 2
bottle_B[0].position = [3.25, 5.570000171661377, 1.0199999809265137]
bottle_B[0].rotation = [0, 0, 0.01256637125682779]
bottle_B[0].optimize = 2
pan_A[0].position = [4.159999847412109, 5.400000095367432, 0.9399999976158142]
pan_A[0].rotation = [0, 0, 0.01256637125682779]
pan_A[0].optimize = 2
pot_A[0].position = [2.0399999618530273, 5.420000076293945, 1.0]
pot_A[0].rotation = [0, 0, 0.01256637125682779]
pot_A[0].optimize = 2
box_D[0].position = [4.619999885559082, 0.14000000059604645, 0.8999999761581421]
box_D[0].rotation = [0, 0, 1.5833626980517244]
box_D[0].optimize = 2
cup_A[0].position = [2.6600000858306885, 5.269999980926514, 0.949999988079071]
cup_A[0].rotation = [0, 0, 0.01256637125682779]
cup_A[0].optimize = 2
cabinet_F[0].position = [2.940000057220459, 5.425869941711426, 0.44999998807907104]
cabinet_F[0].rotation = [0, 0, -1.5707973422745927]
cabinet_F[0].optimize = 2
cabinet_A[0].position = [1.399999976158142, 5.425870418548584, 0.44999998807907104]
cabinet_A[0].rotation = [0, 0, -1.5707958107041413]
cabinet_A[0].optimize = 2
lamp_E[0].position = [6.079999923706055, 3.6500000953674316, 1.9249999523162842]
lamp_E[0].rotation = [0, 0, 0.01256637125682779]
lamp_E[0].optimize = 2
bottle_H[0].position = [5.96999979019165, 5.650000095367432, 1.0099999904632568]
bottle_H[0].rotation = [0, 0, 0.01256637125682779]
bottle_H[0].optimize = 2
bottle_I[0].position = [2.7799999713897705, 0.17499999701976776, 0.8400000333786011]
bottle_I[0].rotation = [0, 0, 0.01256637125682779]
bottle_I[0].optimize = 2
bottle_N[0].position = [3.7300000190734863, 5.659999847412109, 1.0199999809265137]
bottle_N[0].rotation = [0, 0, 0.01256637125682779]
bottle_N[0].optimize = 2
can_B[0].position = [5.309999942779541, 5.25, 0.9749999642372131]
can_B[0].rotation = [0, 0, 0.01256637125682779]
can_B[0].optimize = 2
pot_C[0].position = [5.75, 5.429999828338623, 0.9700000286102295]
pot_C[0].rotation = [0, 0, 0.01256637125682779]
pot_C[0].optimize = 2
lamp_D[0].position = [4.340000152587891, 0.14000000059604645, 0.875]
lamp_D[0].rotation = [0, 0, 1.5833626980517244]
lamp_D[0].optimize = 2
cabinet_B[0].position = [2.5, 0.17499975860118866, 0.375]
cabinet_B[0].rotation = [0, 0, 1.5707955471350674]
cabinet_B[0].optimize = 2
lamp_B[0].position = [2.25, 0.17499999701976776, 0.875]
lamp_B[0].rotation = [0, 0, 1.5833626980517244]
lamp_B[0].optimize = 2
bottle_G[0].position = [5.300000190734863, 5.619999885559082, 1.024999976158142]
bottle_G[0].rotation = [0, 0, 0.01256637125682779]
bottle_G[0].optimize = 2
food_A[0].position = [1.4800000190734863, 5.519999980926514, 1.2699998617172241]
food_A[0].rotation = [0, 0, 1.5833626980517244]
food_A[0].optimize = 2
bottle_K[0].position = [5.079999923706055, 0.14000000059604645, 0.8650000095367432]
bottle_K[0].rotation = [0, 0, 0.01256637125682779]
bottle_K[0].optimize = 2
bottle_M[0].position = [3.549999952316284, 5.659999847412109, 1.034999966621399]
bottle_M[0].rotation = [0, 0, 0.01256637125682779]
bottle_M[0].optimize = 2
bottle_A[0].position = [1.7999999523162842, 5.5, 1.0499999523162842]
bottle_A[0].rotation = [0, 0, 0.01256637125682779]
bottle_A[0].optimize = 2
cabinet_C[0].position = [4.010000228881836, 5.425870418548584, 0.44999998807907104]
cabinet_C[0].rotation = [0, 0, -1.5707973249380929]
cabinet_C[0].optimize = 2
bottle_F[0].position = [4.760000228881836, 5.619999885559082, 1.0499999523162842]
bottle_F[0].rotation = [0, 0, 0.01256637125682779]
bottle_F[0].optimize = 2
cabinet_D[0].position = [5.03000020980835, 5.425870418548584, 0.44999998807907104]
cabinet_D[0].rotation = [0, 0, -1.570797059653378]
cabinet_D[0].optimize = 2
box_A[0].position = [2.5299999713897705, 0.17499999701976776, 0.9099999666213989]
box_A[0].rotation = [0, 0, 1.5833626980517244]
box_A[0].optimize = 2
bottle_P[0].position = [4.25, 5.650000095367432, 1.0299999713897705]
bottle_P[0].rotation = [0, 0, 0.01256637125682779]
bottle_P[0].optimize = 2
lamp_C[0].position = [3.1500000953674316, 0.17499999701976776, 0.875]
lamp_C[0].rotation = [0, 0, 1.5833626980517244]
lamp_C[0].optimize = 2
bottle_J[0].position = [3.880000114440918, 0.17499999701976776, 0.8400000333786011]
bottle_J[0].rotation = [0, 0, 0.01256637125682779]
bottle_J[0].optimize = 2
bottle_L[0].position = [6.079999923706055, 4.630000114440918, 1.9449999332427979]
bottle_L[0].rotation = [0, 0, 0.01256637125682779]
bottle_L[0].optimize = 2
faucet[0].position = [2.940000057220459, 5.579999923706055, 1.0899999141693115]
faucet[0].rotation = [0, 0, -1.5582299555380688]
faucet[0].optimize = 2
food_B[0].position = [2.930000066757202, 5.260000228881836, 0.949999988079071]
food_B[0].rotation = [0, 0, 0.01256637125682779]
food_B[0].optimize = 2
can_A[0].position = [4.449999809265137, 5.269999980926514, 0.9599999785423279]
can_A[0].rotation = [0, 0, 0.01256637125682779]
can_A[0].optimize = 2
book[0].position = [6.079999923706055, 4.179999828338623, 1.934999942779541]
book[0].rotation = [0, 0, 0.01256637125682779]
book[0].optimize = 2
vase[0].position = [6.079999923706055, 4.429999828338623, 1.9399999380111694]
vase[0].rotation = [0, 0, 0.01256637125682779]
vase[0].optimize = 2
oven[0].position = [2.1700000762939453, 5.425870418548584, 0.44999998807907104]
oven[0].rotation = [0, 0, -1.570795782993395]
oven[0].optimize = 2
box_E[0].position = [4.869999885559082, 0.14000000059604645, 0.8600000143051147]
box_E[0].rotation = [0, 0, 1.5833626980517244]
box_E[0].optimize = 2
shelf_B[0].position = [4.699999809265137, 0.13999994099140167, 0.375]
shelf_B[0].rotation = [0, 0, 1.5707955919532202]
shelf_B[0].optimize = 2
box_B[0].position = [3.4000000953674316, 0.17499999701976776, 0.8899999856948853]
box_B[0].rotation = [0, 0, 1.5833626980517244]
box_B[0].optimize = 2
food_C[0].position = [1.4800000190734863, 5.320000171661377, 1.2699998617172241]
food_C[0].rotation = [0, 0, 1.5833626980517244]
food_C[0].optimize = 2
box_F[0].position = [6.079999923706055, 3.9100000858306885, 1.8599998950958252]
box_F[0].rotation = [0, 0, 0.01256637125682779]
box_F[0].optimize = 2
shelf_A[0].position = [6.075870037078857, 4.099999904632568, 0.8999999761581421]
shelf_A[0].rotation = [0, 0, -3.1415921281744557]
shelf_A[0].optimize = 2
bottle_E[0].position = [4.429999828338623, 5.639999866485596, 1.0099999904632568]
bottle_E[0].rotation = [0, 0, 0.01256637125682779]
bottle_E[0].optimize = 2
bottle_O[0].position = [4.070000171661377, 5.650000095367432, 1.0499999523162842]
bottle_O[0].rotation = [0, 0, 0.01256637125682779]
bottle_O[0].optimize = 2
bottle_D[0].position = [3.869999885559082, 5.639999866485596, 1.0399999618530273]
bottle_D[0].rotation = [0, 0, 0.01256637125682779]
bottle_D[0].optimize = 2
cup_B[0].position = [5.519999980926514, 5.239999771118164, 0.9000000357627869]
cup_B[0].rotation = [0, 0, 0.01256637125682779]
cup_B[0].optimize = 2
box_C[0].position = [3.6500000953674316, 0.17499999701976776, 0.875]
box_C[0].rotation = [0, 0, 1.5833626980517244]
box_C[0].optimize = 2
lamp_A[0].position = [1.059999942779541, 5.429999828338623, 1.024999976158142]
lamp_A[0].rotation = [0, 0, -1.5582299555380688]
lamp_A[0].optimize = 2
cabinet_E[0].position = [3.5, 0.17499995231628418, 0.375]
cabinet_E[0].rotation = [0, 0, 1.5707955894520647]
cabinet_E[0].optimize = 2

