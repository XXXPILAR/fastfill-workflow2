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
    Wall(corner1=[2.78, 0.00, 0.00], corner2=[2.78, 3.28, 0.00]),
    Wall(corner1=[2.78, 3.28, 0.00], corner2=[0.00, 3.28, 0.00]),
    Wall(corner1=[0.00, 3.28, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.78, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
cup_A = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="shelf", size=[0.30, 0.90, 0.04], placements=[AssetInstance() for _ in range(1)])
lamp = Assets(description="lamp", size=[0.20, 0.20, 0.35], placements=[AssetInstance() for _ in range(1)])
bottle_A = Assets(description="bottle", size=[0.08, 0.08, 0.25], placements=[AssetInstance() for _ in range(1)])
plate_A = Assets(description="plate", size=[0.27, 0.27, 0.03], placements=[AssetInstance() for _ in range(1)])
cup_B = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
pot_A = Assets(description="pot", size=[0.28, 0.28, 0.20], placements=[AssetInstance() for _ in range(1)])
cup_C = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="bottle", size=[0.08, 0.08, 0.24], placements=[AssetInstance() for _ in range(1)])
plate_B = Assets(description="plate", size=[0.25, 0.25, 0.03], placements=[AssetInstance() for _ in range(1)])
bottle_C = Assets(description="bottle", size=[0.07, 0.07, 0.22], placements=[AssetInstance() for _ in range(1)])
microwave = Assets(description="microwave", size=[0.40, 0.50, 0.30], placements=[AssetInstance() for _ in range(1)])
pan = Assets(description="pan", size=[0.28, 0.46, 0.08], placements=[AssetInstance() for _ in range(1)])
cup_D = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
bottle_D = Assets(description="bottle", size=[0.08, 0.08, 0.27], placements=[AssetInstance() for _ in range(1)])
bottle_E = Assets(description="bottle", size=[0.07, 0.07, 0.23], placements=[AssetInstance() for _ in range(1)])
cup_E = Assets(description="cup", size=[0.09, 0.09, 0.10], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="cabinet", size=[0.60, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
plate_C = Assets(description="plate", size=[0.27, 0.27, 0.03], placements=[AssetInstance() for _ in range(1)])
bottle_F = Assets(description="bottle", size=[0.08, 0.08, 0.25], placements=[AssetInstance() for _ in range(1)])
bottle_G = Assets(description="bottle", size=[0.07, 0.07, 0.22], placements=[AssetInstance() for _ in range(1)])
bottle_H = Assets(description="bottle", size=[0.09, 0.09, 0.29], placements=[AssetInstance() for _ in range(1)])
bottle_I = Assets(description="bottle", size=[0.07, 0.07, 0.24], placements=[AssetInstance() for _ in range(1)])
bottle_J = Assets(description="bottle", size=[0.08, 0.08, 0.26], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.30, 0.90, 0.04], placements=[AssetInstance() for _ in range(1)])
bottle_K = Assets(description="bottle", size=[0.08, 0.08, 0.25], placements=[AssetInstance() for _ in range(1)])
refrigerator = Assets(description="refrigerator", size=[0.70, 0.70, 1.80], placements=[AssetInstance() for _ in range(1)])
cup_F = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
bottle_L = Assets(description="bottle", size=[0.08, 0.08, 0.25], placements=[AssetInstance() for _ in range(1)])
mirror = Assets(description="mirror", size=[0.03, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
pot_B = Assets(description="pot", size=[0.24, 0.24, 0.18], placements=[AssetInstance() for _ in range(1)])
faucet = Assets(description="faucet", size=[0.25, 0.20, 0.30], placements=[AssetInstance() for _ in range(1)])
pot_C = Assets(description="pot", size=[0.30, 0.30, 0.22], placements=[AssetInstance() for _ in range(1)])
pot_D = Assets(description="pot", size=[0.22, 0.22, 0.16], placements=[AssetInstance() for _ in range(1)])
plate_D = Assets(description="plate", size=[0.26, 0.26, 0.03], placements=[AssetInstance() for _ in range(1)])
can = Assets(description="can", size=[0.07, 0.07, 0.12], placements=[AssetInstance() for _ in range(1)])
cup_G = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
bottle_M = Assets(description="bottle", size=[0.08, 0.08, 0.26], placements=[AssetInstance() for _ in range(1)])
pot_E = Assets(description="pot", size=[0.26, 0.26, 0.19], placements=[AssetInstance() for _ in range(1)])
bottle_N = Assets(description="bottle", size=[0.07, 0.07, 0.23], placements=[AssetInstance() for _ in range(1)])
bottle_O = Assets(description="bottle", size=[0.08, 0.08, 0.25], placements=[AssetInstance() for _ in range(1)])

cup_A[0].instance_id = 'cup_A_0'
shelf_A[0].instance_id = 'shelf_A_0'
lamp[0].instance_id = 'lamp_0'
bottle_A[0].instance_id = 'bottle_A_0'
plate_A[0].instance_id = 'plate_A_0'
cup_B[0].instance_id = 'cup_B_0'
pot_A[0].instance_id = 'pot_A_0'
cup_C[0].instance_id = 'cup_C_0'
bottle_B[0].instance_id = 'bottle_B_0'
plate_B[0].instance_id = 'plate_B_0'
bottle_C[0].instance_id = 'bottle_C_0'
microwave[0].instance_id = 'microwave_0'
pan[0].instance_id = 'pan_0'
cup_D[0].instance_id = 'cup_D_0'
bottle_D[0].instance_id = 'bottle_D_0'
bottle_E[0].instance_id = 'bottle_E_0'
cup_E[0].instance_id = 'cup_E_0'
cabinet[0].instance_id = 'cabinet_0'
plate_C[0].instance_id = 'plate_C_0'
bottle_F[0].instance_id = 'bottle_F_0'
bottle_G[0].instance_id = 'bottle_G_0'
bottle_H[0].instance_id = 'bottle_H_0'
bottle_I[0].instance_id = 'bottle_I_0'
bottle_J[0].instance_id = 'bottle_J_0'
shelf_B[0].instance_id = 'shelf_B_0'
bottle_K[0].instance_id = 'bottle_K_0'
refrigerator[0].instance_id = 'refrigerator_0'
cup_F[0].instance_id = 'cup_F_0'
bottle_L[0].instance_id = 'bottle_L_0'
mirror[0].instance_id = 'mirror_0'
pot_B[0].instance_id = 'pot_B_0'
faucet[0].instance_id = 'faucet_0'
pot_C[0].instance_id = 'pot_C_0'
pot_D[0].instance_id = 'pot_D_0'
plate_D[0].instance_id = 'plate_D_0'
can[0].instance_id = 'can_0'
cup_G[0].instance_id = 'cup_G_0'
bottle_M[0].instance_id = 'bottle_M_0'
pot_E[0].instance_id = 'pot_E_0'
bottle_N[0].instance_id = 'bottle_N_0'
bottle_O[0].instance_id = 'bottle_O_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

cup_A[0].position = [0.43346620222793447, 2.9730586337445675, 0.055]
cup_A[0].rotation = [0, 0, 0]
shelf_A[0].position = [0.41942607714052904, 2.7428459253380697, 0.02]
shelf_A[0].rotation = [0, 0, 0]
lamp[0].position = [2.7300102041046044, 1.0108518007123946, 0.175]
lamp[0].rotation = [0, 0, 0]
bottle_A[0].position = [0.8132549390818877, 0.4622844902105241, 0.125]
bottle_A[0].rotation = [0, 0, 0]
plate_A[0].position = [2.3813034435866256, 1.0741145298583628, 0.015]
plate_A[0].rotation = [0, 0, 0]
cup_B[0].position = [2.191197772953158, 1.9858679699143291, 0.055]
cup_B[0].rotation = [0, 0, 0]
pot_A[0].position = [2.6501101753550564, 0.13405957760063858, 0.1]
pot_A[0].rotation = [0, 0, 0]
cup_C[0].position = [2.750645984048939, 2.4873246645999174, 0.055]
cup_C[0].rotation = [0, 0, 0]
bottle_B[0].position = [0.42383633021118594, 1.7574731727305144, 0.12]
bottle_B[0].rotation = [0, 0, 0]
plate_B[0].position = [2.7789171961666934, 2.9781194303709806, 0.015]
plate_B[0].rotation = [0, 0, 0]
bottle_C[0].position = [0.9375497060135989, 3.148294825829398, 0.11]
bottle_C[0].rotation = [0, 0, 0]
microwave[0].position = [1.2897859804548284, 0.9473761588091874, 0.15]
microwave[0].rotation = [0, 0, 0]
pan[0].position = [0.09089714979972843, 0.03331763228861413, 0.04]
pan[0].rotation = [0, 0, 0]
cup_D[0].position = [0.46809343257555946, 0.6372776881776377, 0.055]
cup_D[0].rotation = [0, 0, 0]
bottle_D[0].position = [0.4520454332054707, 2.1111730352768325, 0.135]
bottle_D[0].rotation = [0, 0, 0]
bottle_E[0].position = [0.7207521842330091, 2.857395995795244, 0.115]
bottle_E[0].rotation = [0, 0, 0]
cup_E[0].position = [0.1593996192204188, 1.3410601001593356, 0.05]
cup_E[0].rotation = [0, 0, 0]
cabinet[0].position = [2.7459161774638616, 0.34251395051082884, 0.45]
cabinet[0].rotation = [0, 0, 0]
plate_C[0].position = [2.703283744854808, 2.0364445252673233, 0.015]
plate_C[0].rotation = [0, 0, 0]
bottle_F[0].position = [0.47544227248686793, 2.265997329518899, 0.125]
bottle_F[0].rotation = [0, 0, 0]
bottle_G[0].position = [2.0622127834117423, 2.8708959127322093, 0.11]
bottle_G[0].rotation = [0, 0, 0]
bottle_H[0].position = [0.984595711154725, 1.951218183485881, 0.145]
bottle_H[0].rotation = [0, 0, 0]
bottle_I[0].position = [1.6942058292870443, 2.077554422763361, 0.12]
bottle_I[0].rotation = [0, 0, 0]
bottle_J[0].position = [0.02092084561752546, 0.49127836496592736, 0.13]
bottle_J[0].rotation = [0, 0, 0]
shelf_B[0].position = [0.6107224441706429, 2.059302321653335, 0.02]
shelf_B[0].rotation = [0, 0, 0]
bottle_K[0].position = [1.5381996218577028, 1.679276897938385, 0.125]
bottle_K[0].rotation = [0, 0, 0]
refrigerator[0].position = [2.055921377075595, 1.9670993491307047, 0.9]
refrigerator[0].rotation = [0, 0, 0]
cup_F[0].position = [1.955804661712704, 0.48832110684923247, 0.055]
cup_F[0].rotation = [0, 0, 0]
bottle_L[0].position = [0.5918129627900363, 0.6160819357639933, 0.125]
bottle_L[0].rotation = [0, 0, 0]
mirror[0].position = [1.4432835370363506, 0.2218734475379646, 0.4]
mirror[0].rotation = [0, 0, 0]
pot_B[0].position = [1.0806188072128695, 0.31085615097204883, 0.09]
pot_B[0].rotation = [0, 0, 0]
faucet[0].position = [2.511374263872266, 3.086630460942275, 0.15]
faucet[0].rotation = [0, 0, 0]
pot_C[0].position = [0.8829289437139296, 0.42911920082771843, 0.11]
pot_C[0].rotation = [0, 0, 0]
pot_D[0].position = [0.3617295111505649, 1.7362747950601518, 0.08]
pot_D[0].rotation = [0, 0, 0]
plate_D[0].position = [0.0807403038699288, 1.5242394722935955, 0.015]
plate_D[0].rotation = [0, 0, 0]
can[0].position = [2.4207360199244836, 0.9439745086464294, 0.06]
can[0].rotation = [0, 0, 0]
cup_G[0].position = [1.204608978315245, 2.8856617279021277, 0.055]
cup_G[0].rotation = [0, 0, 0]
bottle_M[0].position = [2.297988052609638, 2.5791760813758366, 0.13]
bottle_M[0].rotation = [0, 0, 0]
pot_E[0].position = [1.680819467246404, 1.2328656356422298, 0.095]
pot_E[0].rotation = [0, 0, 0]
bottle_N[0].position = [1.1364408179883234, 1.5508006691507579, 0.115]
bottle_N[0].rotation = [0, 0, 0]
bottle_O[0].position = [2.095190987692269, 2.4112606753541344, 0.125]
bottle_O[0].rotation = [0, 0, 0]
cup_A[0].position = [0.43346620222793447, 2.9730586337445675, 0.055]
cup_A[0].rotation = [0, 0, 0]
shelf_A[0].position = [0.41942607714052904, 2.7428459253380697, 0.02]
shelf_A[0].rotation = [0, 0, 0]
lamp[0].position = [2.7300102041046044, 1.0108518007123946, 0.175]
lamp[0].rotation = [0, 0, 0]
bottle_A[0].position = [0.8132549390818877, 0.4622844902105241, 0.125]
bottle_A[0].rotation = [0, 0, 0]
plate_A[0].position = [2.3813034435866256, 1.0741145298583628, 0.015]
plate_A[0].rotation = [0, 0, 0]
cup_B[0].position = [2.191197772953158, 1.9858679699143291, 0.055]
cup_B[0].rotation = [0, 0, 0]
pot_A[0].position = [2.6501101753550564, 0.13405957760063858, 0.1]
pot_A[0].rotation = [0, 0, 0]
cup_C[0].position = [2.750645984048939, 2.4873246645999174, 0.055]
cup_C[0].rotation = [0, 0, 0]
bottle_B[0].position = [0.42383633021118594, 1.7574731727305144, 0.12]
bottle_B[0].rotation = [0, 0, 0]
plate_B[0].position = [2.7789171961666934, 2.9781194303709806, 0.015]
plate_B[0].rotation = [0, 0, 0]
bottle_C[0].position = [0.9375497060135989, 3.148294825829398, 0.11]
bottle_C[0].rotation = [0, 0, 0]
microwave[0].position = [1.2897859804548284, 0.9473761588091874, 0.15]
microwave[0].rotation = [0, 0, 0]
pan[0].position = [0.09089714979972843, 0.03331763228861413, 0.04]
pan[0].rotation = [0, 0, 0]
cup_D[0].position = [0.46809343257555946, 0.6372776881776377, 0.055]
cup_D[0].rotation = [0, 0, 0]
bottle_D[0].position = [0.4520454332054707, 2.1111730352768325, 0.135]
bottle_D[0].rotation = [0, 0, 0]
bottle_E[0].position = [0.7207521842330091, 2.857395995795244, 0.115]
bottle_E[0].rotation = [0, 0, 0]
cup_E[0].position = [0.1593996192204188, 1.3410601001593356, 0.05]
cup_E[0].rotation = [0, 0, 0]
cabinet[0].position = [2.7459161774638616, 0.34251395051082884, 0.45]
cabinet[0].rotation = [0, 0, 0]
plate_C[0].position = [2.703283744854808, 2.0364445252673233, 0.015]
plate_C[0].rotation = [0, 0, 0]
bottle_F[0].position = [0.47544227248686793, 2.265997329518899, 0.125]
bottle_F[0].rotation = [0, 0, 0]
bottle_G[0].position = [2.0622127834117423, 2.8708959127322093, 0.11]
bottle_G[0].rotation = [0, 0, 0]
bottle_H[0].position = [0.984595711154725, 1.951218183485881, 0.145]
bottle_H[0].rotation = [0, 0, 0]
bottle_I[0].position = [1.6942058292870443, 2.077554422763361, 0.12]
bottle_I[0].rotation = [0, 0, 0]
bottle_J[0].position = [0.02092084561752546, 0.49127836496592736, 0.13]
bottle_J[0].rotation = [0, 0, 0]
shelf_B[0].position = [0.6107224441706429, 2.059302321653335, 0.02]
shelf_B[0].rotation = [0, 0, 0]
bottle_K[0].position = [1.5381996218577028, 1.679276897938385, 0.125]
bottle_K[0].rotation = [0, 0, 0]
refrigerator[0].position = [2.055921377075595, 1.9670993491307047, 0.9]
refrigerator[0].rotation = [0, 0, 0]
cup_F[0].position = [1.955804661712704, 0.48832110684923247, 0.055]
cup_F[0].rotation = [0, 0, 0]
bottle_L[0].position = [0.5918129627900363, 0.6160819357639933, 0.125]
bottle_L[0].rotation = [0, 0, 0]
mirror[0].position = [1.4432835370363506, 0.2218734475379646, 0.4]
mirror[0].rotation = [0, 0, 0]
pot_B[0].position = [1.0806188072128695, 0.31085615097204883, 0.09]
pot_B[0].rotation = [0, 0, 0]
faucet[0].position = [2.511374263872266, 3.086630460942275, 0.15]
faucet[0].rotation = [0, 0, 0]
pot_C[0].position = [0.8829289437139296, 0.42911920082771843, 0.11]
pot_C[0].rotation = [0, 0, 0]
pot_D[0].position = [0.3617295111505649, 1.7362747950601518, 0.08]
pot_D[0].rotation = [0, 0, 0]
plate_D[0].position = [0.0807403038699288, 1.5242394722935955, 0.015]
plate_D[0].rotation = [0, 0, 0]
can[0].position = [2.4207360199244836, 0.9439745086464294, 0.06]
can[0].rotation = [0, 0, 0]
cup_G[0].position = [1.204608978315245, 2.8856617279021277, 0.055]
cup_G[0].rotation = [0, 0, 0]
bottle_M[0].position = [2.297988052609638, 2.5791760813758366, 0.13]
bottle_M[0].rotation = [0, 0, 0]
pot_E[0].position = [1.680819467246404, 1.2328656356422298, 0.095]
pot_E[0].rotation = [0, 0, 0]
bottle_N[0].position = [1.1364408179883234, 1.5508006691507579, 0.115]
bottle_N[0].rotation = [0, 0, 0]
bottle_O[0].position = [2.095190987692269, 2.4112606753541344, 0.125]
bottle_O[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed references used to preserve absolute positions and orientations.
room_center = AssetInstance(position=[1.39, 1.64, 0.0])
heading_pos_x = AssetInstance(rotation=[0, 0, radians(0)])
heading_pos_y = AssetInstance(rotation=[0, 0, radians(90)])
heading_neg_y = AssetInstance(rotation=[0, 0, radians(-90)])


def constrain_at(instance, position, heading_reference, weight=10):
    """Keep an instance at its planned location and preserve its orientation."""
    anchor = AssetInstance(position=position)
    solver.distance_constraint(instance, anchor, 0, 0, weight=weight)
    solver.align_with(instance, heading_reference)


def constrain_on_surface(instance, support, position, heading_reference):
    """Anchor a small object horizontally and keep it on its supporting surface."""
    # The exact anchor preserves the non-overlapping tabletop arrangement.
    constrain_at(instance, position, heading_reference)
    solver.on_top_of(instance, support)


# ---------------------------------------------------------------------------
# Major furniture and room fixtures
#
# The two low shelves and refrigerator form one run along the bottom wall.
# Their x-order is shelf_A, refrigerator, shelf_B, so the refrigerator is
# explicitly between the two shelves. This run remains well away from the
# right-wall door at y=0.99.
# ---------------------------------------------------------------------------

shelf_A[0].position = [0.55, 0.15, 0.02]
shelf_A[0].rotation = [0, 0, radians(90)]
solver.against_wall(shelf_A[0], walls[3])
constrain_at(shelf_A[0], shelf_A[0].position, heading_pos_y)

refrigerator[0].position = [1.39, 0.35, 0.90]
refrigerator[0].rotation = [0, 0, radians(90)]
solver.against_wall(refrigerator[0], walls[3])
constrain_at(refrigerator[0], refrigerator[0].position, heading_pos_y)

shelf_B[0].position = [2.23, 0.15, 0.02]
shelf_B[0].rotation = [0, 0, radians(90)]
solver.against_wall(shelf_B[0], walls[3])
constrain_at(shelf_B[0], shelf_B[0].position, heading_pos_y)

# Preserve the refrigerator's centered relationship between the shelves.
solver.distance_constraint(
    refrigerator[0], shelf_A[0], 0.84, 0.84, weight=10
)
solver.distance_constraint(
    refrigerator[0], shelf_B[0], 0.84, 0.84, weight=10
)

# The cabinet occupies the middle portion of the left wall and provides the
# primary work surface. Its placement leaves the top-wall window unobstructed.
cabinet[0].position = [0.30, 1.85, 0.45]
cabinet[0].rotation = [0, 0, radians(0)]
solver.against_wall(cabinet[0], walls[2])
constrain_at(cabinet[0], cabinet[0].position, heading_pos_x)

# Mount the mirror on the short top-wall section to the right of the window.
mirror[0].position = [2.40, 3.265, 1.30]
mirror[0].rotation = [0, 0, radians(-90)]
solver.against_wall(mirror[0], walls[1])
constrain_at(mirror[0], mirror[0].position, heading_neg_y)


# ---------------------------------------------------------------------------
# Cabinet worktop (surface height 0.90 m)
# ---------------------------------------------------------------------------

microwave[0].position = [0.22, 1.53, 1.05]
microwave[0].rotation = [0, 0, radians(0)]
constrain_on_surface(
    microwave[0], cabinet[0], microwave[0].position, heading_pos_x
)

pot_A[0].position = [0.15, 1.96, 1.00]
pot_A[0].rotation = [0, 0, radians(0)]
constrain_on_surface(pot_A[0], cabinet[0], pot_A[0].position, heading_pos_x)

pot_B[0].position = [0.46, 1.96, 0.99]
pot_B[0].rotation = [0, 0, radians(0)]
constrain_on_surface(pot_B[0], cabinet[0], pot_B[0].position, heading_pos_x)

pot_C[0].position = [0.15, 2.29, 1.01]
pot_C[0].rotation = [0, 0, radians(0)]
constrain_on_surface(pot_C[0], cabinet[0], pot_C[0].position, heading_pos_x)

pot_D[0].position = [0.46, 2.29, 0.98]
pot_D[0].rotation = [0, 0, radians(0)]
constrain_on_surface(pot_D[0], cabinet[0], pot_D[0].position, heading_pos_x)


# ---------------------------------------------------------------------------
# Microwave top (surface height 1.20 m)
#
# The lamp occupies the left side. Ten narrow cups and bottles form two
# orderly columns on the right side without extending beyond the microwave.
# ---------------------------------------------------------------------------

lamp[0].position = [0.12, 1.55, 1.375]
lamp[0].rotation = [0, 0, radians(0)]
constrain_on_surface(lamp[0], microwave[0], lamp[0].position, heading_pos_x)

microwave_top_items = [
    (cup_A[0],    [0.285, 1.34, 1.255]),
    (bottle_A[0], [0.375, 1.34, 1.325]),
    (cup_B[0],    [0.285, 1.44, 1.255]),
    (bottle_B[0], [0.375, 1.44, 1.320]),
    (cup_C[0],    [0.285, 1.54, 1.255]),
    (bottle_C[0], [0.375, 1.54, 1.310]),
    (cup_D[0],    [0.285, 1.64, 1.255]),
    (bottle_D[0], [0.375, 1.64, 1.335]),
    (cup_E[0],    [0.285, 1.74, 1.250]),
    (bottle_E[0], [0.375, 1.74, 1.315]),
]

for small_instance, planned_position in microwave_top_items:
    small_instance.position = planned_position
    small_instance.rotation = [0, 0, radians(0)]
    constrain_on_surface(
        small_instance, microwave[0], planned_position, heading_pos_x
    )


# ---------------------------------------------------------------------------
# Left low shelf (surface height 0.04 m)
#
# Nine bottles are spaced at 0.10 m intervals along the 0.90 m shelf.
# ---------------------------------------------------------------------------

shelf_A_items = [
    (bottle_F[0], [0.15, 0.15, 0.165]),
    (bottle_G[0], [0.25, 0.15, 0.150]),
    (bottle_H[0], [0.35, 0.15, 0.185]),
    (bottle_I[0], [0.45, 0.15, 0.160]),
    (bottle_J[0], [0.55, 0.15, 0.170]),
    (bottle_K[0], [0.65, 0.15, 0.165]),
    (bottle_L[0], [0.75, 0.15, 0.165]),
    (bottle_M[0], [0.85, 0.15, 0.170]),
    (bottle_N[0], [0.95, 0.15, 0.155]),
]

for small_instance, planned_position in shelf_A_items:
    small_instance.position = planned_position
    small_instance.rotation = [0, 0, radians(90)]
    constrain_on_surface(
        small_instance, shelf_A[0], planned_position, heading_pos_y
    )


# ---------------------------------------------------------------------------
# Right low shelf (surface height 0.04 m)
#
# Rotating the pan makes its 0.46 m side run along the shelf. The faucet and
# final bottle use the remaining length.
# ---------------------------------------------------------------------------

pan[0].position = [2.01, 0.15, 0.08]
pan[0].rotation = [0, 0, radians(90)]
constrain_on_surface(pan[0], shelf_B[0], pan[0].position, heading_pos_y)

faucet[0].position = [2.375, 0.15, 0.19]
faucet[0].rotation = [0, 0, radians(0)]
constrain_on_surface(faucet[0], shelf_B[0], faucet[0].position, heading_pos_x)

bottle_O[0].position = [2.62, 0.15, 0.165]
bottle_O[0].rotation = [0, 0, radians(90)]
constrain_on_surface(
    bottle_O[0], shelf_B[0], bottle_O[0].position, heading_pos_y
)


# ---------------------------------------------------------------------------
# Refrigerator top (surface height 1.80 m)
#
# The remaining pot and three plates use a compact two-by-two arrangement.
# Two cups are placed centrally on separate plates.
# ---------------------------------------------------------------------------

pot_E[0].position = [1.20, 0.18, 1.895]
pot_E[0].rotation = [0, 0, radians(0)]
constrain_on_surface(
    pot_E[0], refrigerator[0], pot_E[0].position, heading_pos_x
)

plate_A[0].position = [1.56, 0.18, 1.815]
plate_A[0].rotation = [0, 0, radians(0)]
constrain_on_surface(
    plate_A[0], refrigerator[0], plate_A[0].position, heading_pos_x
)

plate_B[0].position = [1.20, 0.53, 1.815]
plate_B[0].rotation = [0, 0, radians(0)]
constrain_on_surface(
    plate_B[0], refrigerator[0], plate_B[0].position, heading_pos_x
)

plate_C[0].position = [1.56, 0.53, 1.815]
plate_C[0].rotation = [0, 0, radians(0)]
constrain_on_surface(
    plate_C[0], refrigerator[0], plate_C[0].position, heading_pos_x
)

# The fourth plate is stacked neatly on plate_A to avoid consuming another
# section of work surface.
plate_D[0].position = [1.56, 0.18, 1.845]
plate_D[0].rotation = [0, 0, radians(0)]
constrain_on_surface(plate_D[0], plate_A[0], plate_D[0].position, heading_pos_x)

cup_F[0].position = [1.20, 0.53, 1.885]
cup_F[0].rotation = [0, 0, radians(0)]
constrain_on_surface(cup_F[0], plate_B[0], cup_F[0].position, heading_pos_x)

cup_G[0].position = [1.56, 0.53, 1.885]
cup_G[0].rotation = [0, 0, radians(0)]
constrain_on_surface(cup_G[0], plate_C[0], cup_G[0].position, heading_pos_x)

# The small can fits beside the lamp on the microwave without interfering
# with the two columns of drinkware.
can[0].position = [0.10, 1.34, 1.26]
can[0].rotation = [0, 0, radians(0)]
constrain_on_surface(can[0], microwave[0], can[0].position, heading_pos_x)

solver.constraints = []
bottle_E[0].position = [0.375, 1.7400000095367432, 1.3149999380111694]
bottle_E[0].rotation = [0, 0, 0.01256637125682779]
bottle_E[0].optimize = 2
bottle_H[0].position = [0.3499999940395355, 0.15000000596046448, 0.1850000023841858]
bottle_H[0].rotation = [0, 0, 1.5833626980517244]
bottle_H[0].optimize = 2
pot_E[0].position = [1.2000000476837158, 0.18000000715255737, 1.8949999809265137]
pot_E[0].rotation = [0, 0, 0.01256637125682779]
pot_E[0].optimize = 2
cup_F[0].position = [1.2000000476837158, 0.5299999713897705, 1.8849998712539673]
cup_F[0].rotation = [0, 0, 0.01256637125682779]
cup_F[0].optimize = 2
bottle_O[0].position = [2.619999885559082, 0.15000000596046448, 0.16499999165534973]
bottle_O[0].rotation = [0, 0, 1.5833626980517244]
bottle_O[0].optimize = 2
bottle_F[0].position = [0.15000000596046448, 0.15000000596046448, 0.16499999165534973]
bottle_F[0].rotation = [0, 0, 1.5833626980517244]
bottle_F[0].optimize = 2
bottle_D[0].position = [0.375, 1.6399999856948853, 1.334999918937683]
bottle_D[0].rotation = [0, 0, 0.01256637125682779]
bottle_D[0].optimize = 2
plate_C[0].position = [1.559999942779541, 0.5299999713897705, 1.8149999380111694]
plate_C[0].rotation = [0, 0, 0.0157079639172164]
plate_C[0].optimize = 2
bottle_J[0].position = [0.550000011920929, 0.15000000596046448, 0.16999998688697815]
bottle_J[0].rotation = [0, 0, 1.5833626980517244]
bottle_J[0].optimize = 2
pot_D[0].position = [0.46000000834465027, 2.2899999618530273, 0.9799999594688416]
pot_D[0].rotation = [0, 0, 0.01256637125682779]
pot_D[0].optimize = 2
can[0].position = [0.10000000149011612, 1.340000033378601, 1.2599998712539673]
can[0].rotation = [0, 0, 0.01256637125682779]
can[0].optimize = 2
shelf_A[0].position = [0.550000011920929, 0.14530639350414276, 0.019999999552965164]
shelf_A[0].rotation = [0, 0, 1.5779820078141633]
shelf_A[0].optimize = 2
bottle_L[0].position = [0.75, 0.15000000596046448, 0.16499999165534973]
bottle_L[0].rotation = [0, 0, 1.5833626980517244]
bottle_L[0].optimize = 2
lamp[0].position = [0.11999999731779099, 1.5499999523162842, 1.3749998807907104]
lamp[0].rotation = [0, 0, 0.01256637125682779]
lamp[0].optimize = 2
bottle_C[0].position = [0.375, 1.5399999618530273, 1.309999942779541]
bottle_C[0].rotation = [0, 0, 0.01256637125682779]
bottle_C[0].optimize = 2
plate_B[0].position = [1.2000000476837158, 0.5299999713897705, 1.8149999380111694]
plate_B[0].rotation = [0, 0, 0.0157079639172164]
plate_B[0].optimize = 2
shelf_B[0].position = [2.2300000190734863, 0.1528296321630478, 0.019999999552965164]
shelf_B[0].rotation = [0, 0, 1.5709264442582487]
shelf_B[0].optimize = 2
cup_A[0].position = [0.2849999964237213, 1.340000033378601, 1.2549998760223389]
cup_A[0].rotation = [0, 0, 0.01256637125682779]
cup_A[0].optimize = 2
bottle_I[0].position = [0.44999998807907104, 0.15000000596046448, 0.1599999964237213]
bottle_I[0].rotation = [0, 0, 1.5833626980517244]
bottle_I[0].optimize = 2
refrigerator[0].position = [1.3899999856948853, 0.35275909304618835, 0.8999999761581421]
refrigerator[0].rotation = [0, 0, 1.576839134014631]
refrigerator[0].optimize = 2
pot_C[0].position = [0.15000000596046448, 2.2899999618530273, 1.0099999904632568]
pot_C[0].rotation = [0, 0, 0.01256637125682779]
pot_C[0].optimize = 2
faucet[0].position = [2.375, 0.15000000596046448, 0.1899999976158142]
faucet[0].rotation = [0, 0, 0.01256637125682779]
faucet[0].optimize = 2
cup_G[0].position = [1.559999942779541, 0.5299999713897705, 1.8849998712539673]
cup_G[0].rotation = [0, 0, 0.01256637125682779]
cup_G[0].optimize = 2
pan[0].position = [2.009999990463257, 0.15000000596046448, 0.07999999821186066]
pan[0].rotation = [0, 0, 1.5833626980517244]
pan[0].optimize = 2
pot_B[0].position = [0.46000000834465027, 1.9600000381469727, 0.9900000095367432]
pot_B[0].rotation = [0, 0, 0.01256637125682779]
pot_B[0].optimize = 2
pot_A[0].position = [0.15000000596046448, 1.9600000381469727, 1.0]
pot_A[0].rotation = [0, 0, 0.01256637125682779]
pot_A[0].optimize = 2
bottle_G[0].position = [0.25, 0.15000000596046448, 0.15000000596046448]
bottle_G[0].rotation = [0, 0, 1.5833626980517244]
bottle_G[0].optimize = 2
bottle_N[0].position = [0.949999988079071, 0.15000000596046448, 0.1550000011920929]
bottle_N[0].rotation = [0, 0, 1.5833626980517244]
bottle_N[0].optimize = 2
cup_E[0].position = [0.2849999964237213, 1.7400000095367432, 1.2499998807907104]
cup_E[0].rotation = [0, 0, 0.01256637125682779]
cup_E[0].optimize = 2
cup_D[0].position = [0.2849999964237213, 1.6399999856948853, 1.2549998760223389]
cup_D[0].rotation = [0, 0, 0.01256637125682779]
cup_D[0].optimize = 2
plate_A[0].position = [1.559999942779541, 0.18000000715255737, 1.8149999380111694]
plate_A[0].rotation = [0, 0, 0.0157079639172164]
plate_A[0].optimize = 2
cup_C[0].position = [0.2849999964237213, 1.5399999618530273, 1.2549998760223389]
cup_C[0].rotation = [0, 0, 0.01256637125682779]
cup_C[0].optimize = 2
cabinet[0].position = [0.29705455899238586, 1.850000023841858, 0.44999998807907104]
cabinet[0].rotation = [0, 0, 0.003381965340968776]
cabinet[0].optimize = 2
mirror[0].position = [2.4000000953674316, 3.2615609169006348, 0.4000000059604645]
mirror[0].rotation = [0, 0, -1.5697590946506368]
mirror[0].optimize = 2
bottle_B[0].position = [0.375, 1.440000057220459, 1.3199999332427979]
bottle_B[0].rotation = [0, 0, 0.01256637125682779]
bottle_B[0].optimize = 2
bottle_K[0].position = [0.6499999761581421, 0.15000000596046448, 0.16499999165534973]
bottle_K[0].rotation = [0, 0, 1.5833626980517244]
bottle_K[0].optimize = 2
cup_B[0].position = [0.2849999964237213, 1.440000057220459, 1.2549998760223389]
cup_B[0].rotation = [0, 0, 0.01256637125682779]
cup_B[0].optimize = 2
bottle_A[0].position = [0.375, 1.340000033378601, 1.3249999284744263]
bottle_A[0].rotation = [0, 0, 0.01256637125682779]
bottle_A[0].optimize = 2
microwave[0].position = [0.2199999988079071, 1.5299999713897705, 1.0499999523162842]
microwave[0].rotation = [0, 0, 0.05026547968485982]
microwave[0].optimize = 2
plate_D[0].position = [1.559999942779541, 0.18000000715255737, 1.84499990940094]
plate_D[0].rotation = [0, 0, 0.01256637125682779]
plate_D[0].optimize = 2
bottle_M[0].position = [0.8500000238418579, 0.15000000596046448, 0.16999998688697815]
bottle_M[0].rotation = [0, 0, 1.5833626980517244]
bottle_M[0].optimize = 2

