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
    Wall(corner1=[5.12, 5.62, 0.00], corner2=[2.30, 5.62, 0.00]),
    Wall(corner1=[2.30, 5.62, 0.00], corner2=[2.27, 5.59, 0.00]),
    Wall(corner1=[2.27, 5.59, 0.00], corner2=[0.00, 2.46, 0.00]),
    Wall(corner1=[0.00, 2.46, 0.00], corner2=[0.00, 0.04, 0.00]),
    Wall(corner1=[0.00, 0.04, 0.00], corner2=[0.04, 0.00, 0.00]),
    Wall(corner1=[0.04, 0.00, 0.00], corner2=[5.12, 0.00, 0.00]),
    Wall(corner1=[5.12, 0.00, 0.00], corner2=[5.16, 0.04, 0.00]),
    Wall(corner1=[5.16, 0.04, 0.00], corner2=[5.16, 5.59, 0.00]),
    Wall(corner1=[5.16, 5.59, 0.00], corner2=[5.12, 5.62, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bag = Assets(description="bag", size=[0.18, 0.40, 0.32], placements=[AssetInstance() for _ in range(1)])
flowerpot_A = Assets(description="flowerpot", size=[0.18, 0.18, 0.22], placements=[AssetInstance() for _ in range(1)])
monitor_A = Assets(description="monitor", size=[0.20, 0.55, 0.42], placements=[AssetInstance() for _ in range(1)])
cup_A = Assets(description="cup", size=[0.09, 0.12, 0.11], placements=[AssetInstance() for _ in range(1)])
plant = Assets(description="plant", size=[0.50, 0.55, 1.10], placements=[AssetInstance() for _ in range(1)])
cushion = Assets(description="cushion", size=[0.15, 0.45, 0.45], placements=[AssetInstance() for _ in range(1)])
bottle = Assets(description="bottle", size=[0.08, 0.08, 0.26], placements=[AssetInstance() for _ in range(1)])
book = Assets(description="book", size=[0.28, 0.21, 0.03], placements=[AssetInstance() for _ in range(1)])
table_A = Assets(description="table", size=[0.70, 1.40, 0.75], placements=[AssetInstance() for _ in range(1)])
flowerpot_B = Assets(description="flowerpot", size=[0.16, 0.16, 0.18], placements=[AssetInstance() for _ in range(1)])
cup_B = Assets(description="cup", size=[0.09, 0.12, 0.11], placements=[AssetInstance() for _ in range(1)])
table_B = Assets(description="table", size=[0.70, 1.40, 0.75], placements=[AssetInstance() for _ in range(1)])
monitor_B = Assets(description="monitor", size=[0.20, 0.55, 0.42], placements=[AssetInstance() for _ in range(1)])
tissue_box_A = Assets(description="tissue box", size=[0.12, 0.23, 0.09], placements=[AssetInstance() for _ in range(1)])
vase = Assets(description="vase", size=[0.16, 0.16, 0.30], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="chair", size=[0.62, 0.62, 0.95], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="shelf", size=[0.30, 0.80, 1.80], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.40, 1.00, 0.85], placements=[AssetInstance() for _ in range(1)])
flowerpot_C = Assets(description="flowerpot", size=[0.32, 0.32, 0.35], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.62, 0.62, 0.95], placements=[AssetInstance() for _ in range(1)])
cup_C = Assets(description="cup", size=[0.09, 0.12, 0.11], placements=[AssetInstance() for _ in range(1)])
basket = Assets(description="basket", size=[0.28, 0.35, 0.25], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.30, 0.80, 1.80], placements=[AssetInstance() for _ in range(1)])
flowerpot_D = Assets(description="flowerpot", size=[0.18, 0.18, 0.20], placements=[AssetInstance() for _ in range(1)])
hat = Assets(description="hat", size=[0.28, 0.30, 0.15], placements=[AssetInstance() for _ in range(1)])
flowerpot_E = Assets(description="flowerpot", size=[0.20, 0.20, 0.23], placements=[AssetInstance() for _ in range(1)])
couch_A = Assets(description="couch", size=[0.85, 1.80, 0.82], placements=[AssetInstance() for _ in range(1)])
table_C = Assets(description="table", size=[0.55, 1.00, 0.42], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.40, 0.90, 0.85], placements=[AssetInstance() for _ in range(1)])
flowerpot_F = Assets(description="flowerpot", size=[0.15, 0.15, 0.18], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="chair", size=[0.52, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
couch_B = Assets(description="couch", size=[0.85, 1.55, 0.82], placements=[AssetInstance() for _ in range(1)])
flowerpot_G = Assets(description="flowerpot", size=[0.16, 0.16, 0.20], placements=[AssetInstance() for _ in range(1)])
table_D = Assets(description="table", size=[0.80, 0.80, 0.74], placements=[AssetInstance() for _ in range(1)])
table_E = Assets(description="table", size=[0.55, 0.55, 0.50], placements=[AssetInstance() for _ in range(1)])
chair_D = Assets(description="chair", size=[0.52, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
chair_E = Assets(description="chair", size=[0.52, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
tissue_box_B = Assets(description="tissue box", size=[0.12, 0.23, 0.09], placements=[AssetInstance() for _ in range(1)])

bag[0].instance_id = 'bag_0'
flowerpot_A[0].instance_id = 'flowerpot_A_0'
monitor_A[0].instance_id = 'monitor_A_0'
cup_A[0].instance_id = 'cup_A_0'
plant[0].instance_id = 'plant_0'
cushion[0].instance_id = 'cushion_0'
bottle[0].instance_id = 'bottle_0'
book[0].instance_id = 'book_0'
table_A[0].instance_id = 'table_A_0'
flowerpot_B[0].instance_id = 'flowerpot_B_0'
cup_B[0].instance_id = 'cup_B_0'
table_B[0].instance_id = 'table_B_0'
monitor_B[0].instance_id = 'monitor_B_0'
tissue_box_A[0].instance_id = 'tissue_box_A_0'
vase[0].instance_id = 'vase_0'
chair_A[0].instance_id = 'chair_A_0'
shelf_A[0].instance_id = 'shelf_A_0'
cabinet_A[0].instance_id = 'cabinet_A_0'
flowerpot_C[0].instance_id = 'flowerpot_C_0'
chair_B[0].instance_id = 'chair_B_0'
cup_C[0].instance_id = 'cup_C_0'
basket[0].instance_id = 'basket_0'
shelf_B[0].instance_id = 'shelf_B_0'
flowerpot_D[0].instance_id = 'flowerpot_D_0'
hat[0].instance_id = 'hat_0'
flowerpot_E[0].instance_id = 'flowerpot_E_0'
couch_A[0].instance_id = 'couch_A_0'
table_C[0].instance_id = 'table_C_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
flowerpot_F[0].instance_id = 'flowerpot_F_0'
chair_C[0].instance_id = 'chair_C_0'
couch_B[0].instance_id = 'couch_B_0'
flowerpot_G[0].instance_id = 'flowerpot_G_0'
table_D[0].instance_id = 'table_D_0'
table_E[0].instance_id = 'table_E_0'
chair_D[0].instance_id = 'chair_D_0'
chair_E[0].instance_id = 'chair_E_0'
tissue_box_B[0].instance_id = 'tissue_box_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'
walls[8].instance_id = 'walls_8'

bag[0].position = [3.74462284548967, 4.8747294003740524, 0.16]
bag[0].rotation = [0, 0, 0]
flowerpot_A[0].position = [2.490943037039499, 5.587638201103743, 0.11]
flowerpot_A[0].rotation = [0, 0, 0]
monitor_A[0].position = [3.803549122133288, 2.9173921430088443, 0.21]
monitor_A[0].rotation = [0, 0, 0]
cup_A[0].position = [1.825096237880253, 0.293006077404871, 0.055]
cup_A[0].rotation = [0, 0, 0]
plant[0].position = [3.7497834841075, 5.428099402976248, 0.55]
plant[0].rotation = [0, 0, 0]
cushion[0].position = [3.217309263898018, 2.6399346205851457, 0.225]
cushion[0].rotation = [0, 0, 0]
bottle[0].position = [1.029977460322607, 2.6343144526435203, 0.13]
bottle[0].rotation = [0, 0, 0]
book[0].position = [0.8960898923000353, 0.30157641926987766, 0.015]
book[0].rotation = [0, 0, 0]
table_A[0].position = [3.143595563483959, 2.0248021727756766, 0.375]
table_A[0].rotation = [0, 0, 0]
flowerpot_B[0].position = [3.2195333832284856, 2.170214299232333, 0.09]
flowerpot_B[0].rotation = [0, 0, 0]
cup_B[0].position = [4.35559493910155, 3.207640250187657, 0.055]
cup_B[0].rotation = [0, 0, 0]
table_B[0].position = [0.8915966859411798, 0.1445922979574924, 0.375]
table_B[0].rotation = [0, 0, 0]
monitor_B[0].position = [1.0106895766340998, 3.1217439451413256, 0.21]
monitor_B[0].rotation = [0, 0, 0]
tissue_box_A[0].position = [1.6517280340473046, 1.9424780225933413, 0.045]
tissue_box_A[0].rotation = [0, 0, 0]
vase[0].position = [2.5213481032360296, 4.010764677115433, 0.15]
vase[0].rotation = [0, 0, 0]
chair_A[0].position = [0.45074015701972964, 2.7054679785937763, 0.475]
chair_A[0].rotation = [0, 0, 0]
shelf_A[0].position = [5.088642733673684, 5.033013955832967, 0.9]
shelf_A[0].rotation = [0, 0, 0]
cabinet_A[0].position = [2.7999272203743617, 4.103778014995346, 0.425]
cabinet_A[0].rotation = [0, 0, 0]
flowerpot_C[0].position = [1.871469731372966, 0.3685288699984217, 0.175]
flowerpot_C[0].rotation = [0, 0, 0]
chair_B[0].position = [4.056362749068064, 3.0765204636320225, 0.475]
chair_B[0].rotation = [0, 0, 0]
cup_C[0].position = [4.122213850623086, 4.187921505325814, 0.055]
cup_C[0].rotation = [0, 0, 0]
basket[0].position = [1.9757807389734212, 2.7817414439139614, 0.125]
basket[0].rotation = [0, 0, 0]
shelf_B[0].position = [1.237199490162443, 2.523045398949823, 0.9]
shelf_B[0].rotation = [0, 0, 0]
flowerpot_D[0].position = [1.523689286065885, 1.6530775500971067, 0.1]
flowerpot_D[0].rotation = [0, 0, 0]
hat[0].position = [0.7606611682163398, 1.6725460587457417, 0.075]
hat[0].rotation = [0, 0, 0]
flowerpot_E[0].position = [0.4244081907658591, 2.1107776874897692, 0.115]
flowerpot_E[0].rotation = [0, 0, 0]
couch_A[0].position = [2.4842831819870805, 0.6260808290288444, 0.41]
couch_A[0].rotation = [0, 0, 0]
table_C[0].position = [2.174457119230422, 2.5828061007145378, 0.21]
table_C[0].rotation = [0, 0, 0]
cabinet_B[0].position = [4.765369860186382, 5.448186189325608, 0.425]
cabinet_B[0].rotation = [0, 0, 0]
flowerpot_F[0].position = [1.6639751845086315, 4.108647011555939, 0.09]
flowerpot_F[0].rotation = [0, 0, 0]
chair_C[0].position = [0.2590333406535722, 1.0217271390482299, 0.41]
chair_C[0].rotation = [0, 0, 0]
couch_B[0].position = [1.2016907852473364, 0.2757732686574319, 0.41]
couch_B[0].rotation = [0, 0, 0]
flowerpot_G[0].position = [3.5424276094037834, 1.894511933481333, 0.1]
flowerpot_G[0].rotation = [0, 0, 0]
table_D[0].position = [3.340490736796956, 4.767592878958089, 0.37]
table_D[0].rotation = [0, 0, 0]
table_E[0].position = [2.821370524043747, 4.73265887004299, 0.25]
table_E[0].rotation = [0, 0, 0]
chair_D[0].position = [4.576564170482398, 5.237870040277462, 0.41]
chair_D[0].rotation = [0, 0, 0]
chair_E[0].position = [2.7047835200403876, 3.36842825284073, 0.41]
chair_E[0].rotation = [0, 0, 0]
tissue_box_B[0].position = [4.8522411579073506, 4.687810635363989, 0.045]
tissue_box_B[0].rotation = [0, 0, 0]
bag[0].position = [3.74462284548967, 4.8747294003740524, 0.16]
bag[0].rotation = [0, 0, 0]
flowerpot_A[0].position = [2.490943037039499, 5.587638201103743, 0.11]
flowerpot_A[0].rotation = [0, 0, 0]
monitor_A[0].position = [3.803549122133288, 2.9173921430088443, 0.21]
monitor_A[0].rotation = [0, 0, 0]
cup_A[0].position = [1.825096237880253, 0.293006077404871, 0.055]
cup_A[0].rotation = [0, 0, 0]
plant[0].position = [3.7497834841075, 5.428099402976248, 0.55]
plant[0].rotation = [0, 0, 0]
cushion[0].position = [3.217309263898018, 2.6399346205851457, 0.225]
cushion[0].rotation = [0, 0, 0]
bottle[0].position = [1.029977460322607, 2.6343144526435203, 0.13]
bottle[0].rotation = [0, 0, 0]
book[0].position = [0.8960898923000353, 0.30157641926987766, 0.015]
book[0].rotation = [0, 0, 0]
table_A[0].position = [3.143595563483959, 2.0248021727756766, 0.375]
table_A[0].rotation = [0, 0, 0]
flowerpot_B[0].position = [3.2195333832284856, 2.170214299232333, 0.09]
flowerpot_B[0].rotation = [0, 0, 0]
cup_B[0].position = [4.35559493910155, 3.207640250187657, 0.055]
cup_B[0].rotation = [0, 0, 0]
table_B[0].position = [0.8915966859411798, 0.1445922979574924, 0.375]
table_B[0].rotation = [0, 0, 0]
monitor_B[0].position = [1.0106895766340998, 3.1217439451413256, 0.21]
monitor_B[0].rotation = [0, 0, 0]
tissue_box_A[0].position = [1.6517280340473046, 1.9424780225933413, 0.045]
tissue_box_A[0].rotation = [0, 0, 0]
vase[0].position = [2.5213481032360296, 4.010764677115433, 0.15]
vase[0].rotation = [0, 0, 0]
chair_A[0].position = [0.45074015701972964, 2.7054679785937763, 0.475]
chair_A[0].rotation = [0, 0, 0]
shelf_A[0].position = [5.088642733673684, 5.033013955832967, 0.9]
shelf_A[0].rotation = [0, 0, 0]
cabinet_A[0].position = [2.7999272203743617, 4.103778014995346, 0.425]
cabinet_A[0].rotation = [0, 0, 0]
flowerpot_C[0].position = [1.871469731372966, 0.3685288699984217, 0.175]
flowerpot_C[0].rotation = [0, 0, 0]
chair_B[0].position = [4.056362749068064, 3.0765204636320225, 0.475]
chair_B[0].rotation = [0, 0, 0]
cup_C[0].position = [4.122213850623086, 4.187921505325814, 0.055]
cup_C[0].rotation = [0, 0, 0]
basket[0].position = [1.9757807389734212, 2.7817414439139614, 0.125]
basket[0].rotation = [0, 0, 0]
shelf_B[0].position = [1.237199490162443, 2.523045398949823, 0.9]
shelf_B[0].rotation = [0, 0, 0]
flowerpot_D[0].position = [1.523689286065885, 1.6530775500971067, 0.1]
flowerpot_D[0].rotation = [0, 0, 0]
hat[0].position = [0.7606611682163398, 1.6725460587457417, 0.075]
hat[0].rotation = [0, 0, 0]
flowerpot_E[0].position = [0.4244081907658591, 2.1107776874897692, 0.115]
flowerpot_E[0].rotation = [0, 0, 0]
couch_A[0].position = [2.4842831819870805, 0.6260808290288444, 0.41]
couch_A[0].rotation = [0, 0, 0]
table_C[0].position = [2.174457119230422, 2.5828061007145378, 0.21]
table_C[0].rotation = [0, 0, 0]
cabinet_B[0].position = [4.765369860186382, 5.448186189325608, 0.425]
cabinet_B[0].rotation = [0, 0, 0]
flowerpot_F[0].position = [1.6639751845086315, 4.108647011555939, 0.09]
flowerpot_F[0].rotation = [0, 0, 0]
chair_C[0].position = [0.2590333406535722, 1.0217271390482299, 0.41]
chair_C[0].rotation = [0, 0, 0]
couch_B[0].position = [1.2016907852473364, 0.2757732686574319, 0.41]
couch_B[0].rotation = [0, 0, 0]
flowerpot_G[0].position = [3.5424276094037834, 1.894511933481333, 0.1]
flowerpot_G[0].rotation = [0, 0, 0]
table_D[0].position = [3.340490736796956, 4.767592878958089, 0.37]
table_D[0].rotation = [0, 0, 0]
table_E[0].position = [2.821370524043747, 4.73265887004299, 0.25]
table_E[0].rotation = [0, 0, 0]
chair_D[0].position = [4.576564170482398, 5.237870040277462, 0.41]
chair_D[0].rotation = [0, 0, 0]
chair_E[0].position = [2.7047835200403876, 3.36842825284073, 0.41]
chair_E[0].rotation = [0, 0, 0]
tissue_box_B[0].position = [4.8522411579073506, 4.687810635363989, 0.045]
tissue_box_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Two workstations occupy the south wall; dining is in the wider part of
# the west side, and the lounge is in the northeast. The entry at
# (0, 2.14) and its approach remain free of furniture.
#
# Each tuple gives an existing asset, its center, and its heading in degrees.
floor_layout = [
    (table_A,   [1.45, 0.35, 0.375],  90),
    (table_B,   [3.00, 0.35, 0.375],  90),
    (chair_A,   [1.45, 1.20, 0.475], -90),
    (chair_B,   [3.00, 1.20, 0.475], -90),

    (shelf_A,   [5.01, 0.55, 0.90],  180),
    (shelf_B,   [5.01, 1.48, 0.90],  180),
    (cabinet_A, [4.96, 2.55, 0.425], 180),
    (cabinet_B, [4.20, 0.20, 0.425],  90),

    (couch_A,   [4.735, 4.45, 0.41], 180),
    (couch_B,   [3.00, 5.195, 0.41], -90),
    (table_C,   [3.65, 4.10, 0.21],    0),
    (table_E,   [4.00, 3.10, 0.25],    0),

    (table_D,   [1.90, 3.35, 0.37],    0),
    (chair_C,   [1.15, 3.35, 0.41],    0),
    (chair_D,   [1.90, 2.60, 0.41],   90),
    (chair_E,   [1.90, 4.10, 0.41],  -90),

    (plant,     [0.36, 0.40, 0.55],    0),
]

for asset_ref, center, heading in floor_layout:
    asset_ref[0].position = center
    asset_ref[0].rotation = [0, 0, radians(heading)]

# Register support constraints before other constraints on small objects.
# Heights use the supporting asset's top bounding-box face.
surface_layout = [
    (monitor_A,    table_A,   1.45, 0.20,  90),
    (flowerpot_A,  table_A,   0.92, 0.22,   0),
    (cup_A,        table_A,   1.95, 0.48,  90),
    (book,         table_A,   1.40, 0.52,  90),

    (monitor_B,    table_B,   3.00, 0.20,  90),
    (flowerpot_B,  table_B,   2.48, 0.20,   0),
    (cup_B,        table_B,   3.50, 0.48,  90),
    (bottle,       table_B,   2.48, 0.50,   0),
    (tissue_box_A, table_B,   3.00, 0.52,  90),

    (bag,          shelf_A,   5.01, 0.55, 180),
    (hat,          shelf_B,   5.01, 1.48, 180),
    (flowerpot_C,  cabinet_A, 4.96, 2.30,   0),
    (vase,         cabinet_A, 4.96, 2.85,   0),
    (basket,       cabinet_B, 3.98, 0.20,  90),
    (flowerpot_D,  cabinet_B, 4.45, 0.20,   0),

    (cup_C,        table_C,   3.65, 3.80,   0),
    (tissue_box_B, table_C,   3.65, 4.12,   0),
    (flowerpot_E,  table_C,   3.65, 4.40,   0),
    (flowerpot_F,  table_D,   1.90, 3.35,   0),
    (flowerpot_G,  table_E,   4.00, 3.10,   0),

    # Keep the cushion entirely within the sofa's supporting footprint.
    (cushion,      couch_A,   4.735, 4.35, 180),
]

for asset_ref, support_ref, px, py, heading in surface_layout:
    top_z = support_ref[0].position[2] + support_ref.size[2] / 2
    asset_ref[0].position = [px, py, top_z + asset_ref.size[2] / 2]
    asset_ref[0].rotation = [0, 0, radians(heading)]
    solver.on_top_of(asset_ref[0], support_ref[0])

# Pin the calculated floor centers to preserve the circulation lanes,
# boundary clearances, and separation between functional zones.
for asset_ref, center, heading in floor_layout:
    solver.distance_constraint(
        asset_ref[0],
        AssetInstance(position=list(center)),
        0, 0, weight=10
    )

# Wall contact is consistent with the pinned furniture footprints.
for asset_ref, wall_index in [
    (table_A, 5), (table_B, 5), (cabinet_B, 5),
    (shelf_A, 7), (shelf_B, 7), (cabinet_A, 7),
    (couch_A, 7), (couch_B, 0),
]:
    solver.against_wall(asset_ref[0], walls[wall_index])

# Functional orientation constraints: work chairs face their monitors;
# lounge seating faces the coffee table; dining chairs face the table.
solver.point_towards(chair_A[0], monitor_A[0])
solver.point_towards(chair_B[0], monitor_B[0])
solver.point_towards(monitor_A[0], chair_A[0])
solver.point_towards(monitor_B[0], chair_B[0])

for asset_ref in (chair_C, chair_D, chair_E):
    solver.point_towards(asset_ref[0], table_D[0])

# Preserve the wall-parallel lounge orientations, rather than turning
# their rectangular footprints diagonally toward the coffee table.
for asset_ref in (
    table_A, table_B, shelf_A, shelf_B, cabinet_A, cabinet_B,
    couch_A, couch_B, table_C, table_D, table_E, plant
):
    solver.align_with(
        asset_ref[0],
        AssetInstance(rotation=list(asset_ref[0].rotation))
    )

# Each supported item receives both a position-based constraint and an
# orientation constraint. Exact anchors retain separate tabletop areas
# instead of allowing small items to collapse onto a common center.
for asset_ref, support_ref, px, py, heading in surface_layout:
    solver.distance_constraint(
        asset_ref[0],
        AssetInstance(position=list(asset_ref[0].position)),
        0, 0, weight=10
    )
    if asset_ref is not monitor_A and asset_ref is not monitor_B:
        solver.align_with(
            asset_ref[0],
            AssetInstance(rotation=[0, 0, radians(heading)])
        )

# Explicit pairwise footprint-clearance constraints for floor furniture.
# These distances use the current separating direction and the rotated
# bounding-box half-extents, so they do not demand excessive radial gaps.
# The center-distance API includes z, hence the vertical term below.
for idx, (first_ref, _, _) in enumerate(floor_layout):
    for second_ref, _, _ in floor_layout[idx + 1:]:
        first_pos = first_ref[0].position
        second_pos = second_ref[0].position
        dx = second_pos[0] - first_pos[0]
        dy = second_pos[1] - first_pos[1]
        planar_distance = (dx * dx + dy * dy) ** 0.5
        if planar_distance == 0:
            continue

        ux, uy = dx / planar_distance, dy / planar_distance
        projected_radii = []
        for footprint_ref in (first_ref, second_ref):
            yaw = footprint_ref[0].rotation[2]
            half_x = footprint_ref.size[0] / 2
            half_y = footprint_ref.size[1] / 2
            projected_radii.append(
                half_x * abs(ux * cos(yaw) + uy * sin(yaw))
                + half_y * abs(-ux * sin(yaw) + uy * cos(yaw))
            )

        # Only add a conservative directional gap when it is compatible
        # with the chosen nonoverlapping layout.
        required_planar_gap = sum(projected_radii) + 0.03
        if planar_distance >= required_planar_gap:
            dz = second_pos[2] - first_pos[2]
            minimum_distance = (required_planar_gap ** 2 + dz ** 2) ** 0.5
            solver.distance_constraint(
                first_ref[0], second_ref[0],
                minimum_distance, None
            )
            solver.distance_constraint(
                second_ref[0], first_ref[0],
                minimum_distance, None
            )

solver.constraints = []
flowerpot_E[0].position = [3.6500000953674316, 4.400000095367432, 0.5349999666213989]
flowerpot_E[0].rotation = [0, 0, 0.01256637125682779]
flowerpot_E[0].optimize = 2
couch_B[0].position = [3.1637277603149414, 5.200006484985352, 0.4099999964237213]
couch_B[0].rotation = [0, 0, -1.5707821989245514]
couch_B[0].optimize = 2
chair_C[0].position = [1.149999976158142, 3.3499999046325684, 0.4099999964237213]
chair_C[0].rotation = [0, 0, 0.1099557411604048]
chair_C[0].optimize = 2
basket[0].position = [3.9800000190734863, 0.20000000298023224, 0.9750000238418579]
basket[0].rotation = [0, 0, 1.5833626980517244]
basket[0].optimize = 2
monitor_A[0].position = [1.4500000476837158, 0.20000000298023224, 0.9599999785423279]
monitor_A[0].rotation = [0, 0, 1.586504290712113]
monitor_A[0].optimize = 2
table_B[0].position = [3.0, 0.34998422861099243, 0.375]
table_B[0].rotation = [0, 0, 1.5708019349005595]
table_B[0].optimize = 2
table_C[0].position = [3.6500000953674316, 4.099999904632568, 0.20999999344348907]
table_C[0].rotation = [0, 0, 0.1130973358793679]
table_C[0].optimize = 2
cup_A[0].position = [1.9500000476837158, 0.47999998927116394, 0.8050000071525574]
cup_A[0].rotation = [0, 0, 1.5833626980517244]
cup_A[0].optimize = 2
cabinet_A[0].position = [4.956239223480225, 2.549999952316284, 0.42500001192092896]
cabinet_A[0].rotation = [0, 0, -3.141576691924496]
cabinet_A[0].optimize = 2
cup_C[0].position = [3.6500000953674316, 3.799999952316284, 0.4749999940395355]
cup_C[0].rotation = [0, 0, 0.01256637125682779]
cup_C[0].optimize = 2
chair_B[0].position = [3.0, 1.2000000476837158, 0.4749999940395355]
chair_B[0].rotation = [0, 0, -1.4576989909155287]
chair_B[0].optimize = 2
cabinet_B[0].position = [4.199999809265137, 0.19999636709690094, 0.42500001192092896]
cabinet_B[0].rotation = [0, 0, 1.5708173677574586]
cabinet_B[0].optimize = 2
flowerpot_D[0].position = [4.449999809265137, 0.20000000298023224, 0.9500000476837158]
flowerpot_D[0].rotation = [0, 0, 0.01256637125682779]
flowerpot_D[0].optimize = 2
flowerpot_F[0].position = [1.899999976158142, 3.3499999046325684, 0.8300000429153442]
flowerpot_F[0].rotation = [0, 0, 0.01256637125682779]
flowerpot_F[0].optimize = 2
tissue_box_A[0].position = [3.0, 0.5199999809265137, 0.7950000166893005]
tissue_box_A[0].rotation = [0, 0, 1.5833626980517244]
tissue_box_A[0].optimize = 2
flowerpot_A[0].position = [0.9200000166893005, 0.2199999988079071, 0.8600000143051147]
flowerpot_A[0].rotation = [0, 0, 0.01256637125682779]
flowerpot_A[0].optimize = 2
bag[0].position = [5.010000228881836, 0.550000011920929, 1.959999918937683]
bag[0].rotation = [0, 0, -3.1290262823329655]
bag[0].optimize = 2
bottle[0].position = [2.4800000190734863, 0.5, 0.8799999952316284]
bottle[0].rotation = [0, 0, 0.01256637125682779]
bottle[0].optimize = 2
monitor_B[0].position = [3.0, 0.20000000298023224, 0.9599999785423279]
monitor_B[0].rotation = [0, 0, 1.586504290712113]
monitor_B[0].optimize = 2
plant[0].position = [0.36000001430511475, 0.4000000059604645, 0.550000011920929]
plant[0].rotation = [0, 0, 0.1099557411604048]
plant[0].optimize = 2
table_D[0].position = [1.899999976158142, 3.3499999046325684, 0.3700000047683716]
table_D[0].rotation = [0, 0, 0.12252211682714997]
table_D[0].optimize = 2
tissue_box_B[0].position = [3.6500000953674316, 4.119999885559082, 0.4649999737739563]
tissue_box_B[0].rotation = [0, 0, 0.01256637125682779]
tissue_box_B[0].optimize = 2
table_A[0].position = [1.4500000476837158, 0.34998372197151184, 0.375]
table_A[0].rotation = [0, 0, 1.5707908009396667]
table_A[0].optimize = 2
book[0].position = [1.399999976158142, 0.5199999809265137, 0.7649999856948853]
book[0].rotation = [0, 0, 1.5833626980517244]
book[0].optimize = 2
vase[0].position = [4.960000038146973, 2.8499999046325684, 1.0]
vase[0].rotation = [0, 0, 0.01256637125682779]
vase[0].optimize = 2
table_E[0].position = [4.0, 3.0999999046325684, 0.25]
table_E[0].rotation = [0, 0, 0.1130973358793679]
table_E[0].optimize = 2
flowerpot_B[0].position = [2.4800000190734863, 0.20000000298023224, 0.8400000333786011]
flowerpot_B[0].rotation = [0, 0, 0.01256637125682779]
flowerpot_B[0].optimize = 2
shelf_B[0].position = [5.006243705749512, 1.4800000190734863, 0.8999999761581421]
shelf_B[0].rotation = [0, 0, -3.14157132418366]
shelf_B[0].optimize = 2
flowerpot_C[0].position = [4.960000038146973, 2.299999952316284, 1.024999976158142]
flowerpot_C[0].rotation = [0, 0, 0.01256637125682779]
flowerpot_C[0].optimize = 2
hat[0].position = [5.010000228881836, 1.4800000190734863, 1.875]
hat[0].rotation = [0, 0, -3.1290262823329655]
hat[0].optimize = 2
cushion[0].position = [4.735000133514404, 4.349999904632568, 1.0449999570846558]
cushion[0].rotation = [0, 0, -3.1290262823329655]
cushion[0].optimize = 2
chair_E[0].position = [1.899999976158142, 4.099999904632568, 0.4099999964237213]
chair_E[0].rotation = [0, 0, -1.460840585634492]
chair_E[0].optimize = 2
shelf_A[0].position = [5.006243705749512, 0.550000011920929, 0.8999999761581421]
shelf_A[0].rotation = [0, 0, -3.14157132418366]
shelf_A[0].optimize = 2
cup_B[0].position = [3.5, 0.47999998927116394, 0.8050000071525574]
cup_B[0].rotation = [0, 0, 1.5833626980517244]
cup_B[0].optimize = 2
couch_A[0].position = [4.7312397956848145, 4.449999809265137, 0.4099999964237213]
couch_A[0].rotation = [0, 0, -3.1415719527124777]
couch_A[0].optimize = 2
chair_D[0].position = [1.899999976158142, 2.5999999046325684, 0.4099999964237213]
chair_D[0].rotation = [0, 0, 1.6807520679553014]
chair_D[0].optimize = 2
chair_A[0].position = [1.4500000476837158, 1.2000000476837158, 0.4749999940395355]
chair_A[0].rotation = [0, 0, -1.4576989909155287]
chair_A[0].optimize = 2
flowerpot_G[0].position = [4.0, 3.0999999046325684, 0.6000000238418579]
flowerpot_G[0].rotation = [0, 0, 0.01256637125682779]
flowerpot_G[0].optimize = 2

