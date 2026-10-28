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
    Wall(corner1=[0.00, 4.34, 0.00], corner2=[0.00, 0.04, 0.00]),
    Wall(corner1=[0.00, 0.04, 0.00], corner2=[0.04, 0.00, 0.00]),
    Wall(corner1=[0.04, 0.00, 0.00], corner2=[3.40, 0.00, 0.00]),
    Wall(corner1=[3.40, 0.00, 0.00], corner2=[5.74, 1.72, 0.00]),
    Wall(corner1=[5.74, 1.72, 0.00], corner2=[5.78, 1.76, 0.00]),
    Wall(corner1=[5.78, 1.76, 0.00], corner2=[5.78, 4.34, 0.00]),
    Wall(corner1=[5.78, 4.34, 0.00], corner2=[5.74, 4.38, 0.00]),
    Wall(corner1=[5.74, 4.38, 0.00], corner2=[0.04, 4.38, 0.00]),
    Wall(corner1=[0.04, 4.38, 0.00], corner2=[0.00, 4.34, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
cup_A = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="table", size=[0.80, 1.40, 0.75], placements=[AssetInstance() for _ in range(1)])
cup_B = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
bottle_A = Assets(description="bottle", size=[0.08, 0.08, 0.28], placements=[AssetInstance() for _ in range(1)])
stove = Assets(description="stove", size=[0.52, 0.60, 0.08], placements=[AssetInstance() for _ in range(1)])
towel = Assets(description="towel", size=[0.03, 0.50, 0.75], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.60, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
cup_C = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
box_A = Assets(description="box", size=[0.24, 0.32, 0.18], placements=[AssetInstance() for _ in range(1)])
can_A = Assets(description="can", size=[0.07, 0.07, 0.12], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.35, 0.80, 0.70], placements=[AssetInstance() for _ in range(1)])
cabinet_C = Assets(description="cabinet", size=[0.60, 1.00, 0.90], placements=[AssetInstance() for _ in range(1)])
bin = Assets(description="bin", size=[0.30, 0.35, 0.50], placements=[AssetInstance() for _ in range(1)])
cup_D = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
box_B = Assets(description="box", size=[0.22, 0.28, 0.16], placements=[AssetInstance() for _ in range(1)])
can_B = Assets(description="can", size=[0.07, 0.07, 0.12], placements=[AssetInstance() for _ in range(1)])
cabinet_D = Assets(description="cabinet", size=[0.35, 0.60, 0.70], placements=[AssetInstance() for _ in range(1)])
cup_E = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
refrigerator = Assets(description="refrigerator", size=[0.75, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
cup_F = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
box_C = Assets(description="box", size=[0.28, 0.35, 0.20], placements=[AssetInstance() for _ in range(1)])
box_D = Assets(description="box", size=[0.20, 0.25, 0.15], placements=[AssetInstance() for _ in range(1)])
cup_G = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
bowl_A = Assets(description="bowl", size=[0.20, 0.20, 0.09], placements=[AssetInstance() for _ in range(1)])
cabinet_E = Assets(description="cabinet", size=[0.60, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
cabinet_F = Assets(description="cabinet", size=[0.35, 0.80, 0.70], placements=[AssetInstance() for _ in range(1)])
fruit = Assets(description="fruit", size=[0.09, 0.09, 0.08], placements=[AssetInstance() for _ in range(1)])
cup_H = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
oven = Assets(description="oven", size=[0.60, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="bottle", size=[0.08, 0.08, 0.30], placements=[AssetInstance() for _ in range(1)])
bottle_C = Assets(description="bottle", size=[0.08, 0.08, 0.30], placements=[AssetInstance() for _ in range(1)])
cabinet_G = Assets(description="cabinet", size=[0.60, 1.00, 0.90], placements=[AssetInstance() for _ in range(1)])
microwave = Assets(description="microwave", size=[0.42, 0.52, 0.31], placements=[AssetInstance() for _ in range(1)])
cup_I = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
can_C = Assets(description="can", size=[0.07, 0.07, 0.12], placements=[AssetInstance() for _ in range(1)])
bowl_B = Assets(description="bowl", size=[0.22, 0.22, 0.10], placements=[AssetInstance() for _ in range(1)])
cup_J = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])

cup_A[0].instance_id = 'cup_A_0'
table[0].instance_id = 'table_0'
cup_B[0].instance_id = 'cup_B_0'
bottle_A[0].instance_id = 'bottle_A_0'
stove[0].instance_id = 'stove_0'
towel[0].instance_id = 'towel_0'
cabinet_A[0].instance_id = 'cabinet_A_0'
cup_C[0].instance_id = 'cup_C_0'
box_A[0].instance_id = 'box_A_0'
can_A[0].instance_id = 'can_A_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
cabinet_C[0].instance_id = 'cabinet_C_0'
bin[0].instance_id = 'bin_0'
cup_D[0].instance_id = 'cup_D_0'
box_B[0].instance_id = 'box_B_0'
can_B[0].instance_id = 'can_B_0'
cabinet_D[0].instance_id = 'cabinet_D_0'
cup_E[0].instance_id = 'cup_E_0'
refrigerator[0].instance_id = 'refrigerator_0'
cup_F[0].instance_id = 'cup_F_0'
box_C[0].instance_id = 'box_C_0'
box_D[0].instance_id = 'box_D_0'
cup_G[0].instance_id = 'cup_G_0'
bowl_A[0].instance_id = 'bowl_A_0'
cabinet_E[0].instance_id = 'cabinet_E_0'
cabinet_F[0].instance_id = 'cabinet_F_0'
fruit[0].instance_id = 'fruit_0'
cup_H[0].instance_id = 'cup_H_0'
oven[0].instance_id = 'oven_0'
bottle_B[0].instance_id = 'bottle_B_0'
bottle_C[0].instance_id = 'bottle_C_0'
cabinet_G[0].instance_id = 'cabinet_G_0'
microwave[0].instance_id = 'microwave_0'
cup_I[0].instance_id = 'cup_I_0'
can_C[0].instance_id = 'can_C_0'
bowl_B[0].instance_id = 'bowl_B_0'
cup_J[0].instance_id = 'cup_J_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'
walls[8].instance_id = 'walls_8'

cup_A[0].position = [0.5746862237306947, 3.75103648927413, 0.055]
cup_A[0].rotation = [0, 0, 0]
table[0].position = [3.7127352306087475, 0.26458462627874263, 0.375]
table[0].rotation = [0, 0, 0]
cup_B[0].position = [2.465761083550346, 3.3335794352267434, 0.055]
cup_B[0].rotation = [0, 0, 0]
bottle_A[0].position = [4.546928362789192, 1.635398751805023, 0.14]
bottle_A[0].rotation = [0, 0, 0]
stove[0].position = [1.7011721387450647, 0.9032519095852115, 0.04]
stove[0].rotation = [0, 0, 0]
towel[0].position = [4.43022673424648, 2.1143501527280844, 0.375]
towel[0].rotation = [0, 0, 0]
cabinet_A[0].position = [2.933506834962686, 3.253247829164064, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
cup_C[0].position = [0.8209377386641706, 0.8694818314855647, 0.055]
cup_C[0].rotation = [0, 0, 0]
box_A[0].position = [1.2655789881217372, 2.1207467354708087, 0.09]
box_A[0].rotation = [0, 0, 0]
can_A[0].position = [1.5498837401075072, 0.19964645950248217, 0.06]
can_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [3.912308084302264, 0.5153560671561923, 0.35]
cabinet_B[0].rotation = [0, 0, 0]
cabinet_C[0].position = [5.531431383251785, 3.831026434615191, 0.45]
cabinet_C[0].rotation = [0, 0, 0]
bin[0].position = [2.400092699498246, 3.986018749962914, 0.25]
bin[0].rotation = [0, 0, 0]
cup_D[0].position = [5.0410287834359115, 1.6280235690574298, 0.055]
cup_D[0].rotation = [0, 0, 0]
box_B[0].position = [1.3227006650972146, 3.7552331574922024, 0.08]
box_B[0].rotation = [0, 0, 0]
can_B[0].position = [3.4395299599042883, 4.284397146156894, 0.06]
can_B[0].rotation = [0, 0, 0]
cabinet_D[0].position = [1.4569686178774746, 2.298313260914441, 0.35]
cabinet_D[0].rotation = [0, 0, 0]
cup_E[0].position = [3.784026185072404, 3.6494582995911427, 0.055]
cup_E[0].rotation = [0, 0, 0]
refrigerator[0].position = [4.242280115537755, 1.3797435656110937, 0.9]
refrigerator[0].rotation = [0, 0, 0]
cup_F[0].position = [3.4333358619025893, 2.135321851696074, 0.055]
cup_F[0].rotation = [0, 0, 0]
box_C[0].position = [3.6245277448387863, 3.33496858293911, 0.1]
box_C[0].rotation = [0, 0, 0]
box_D[0].position = [2.1432186040861927, 3.896425719913429, 0.075]
box_D[0].rotation = [0, 0, 0]
cup_G[0].position = [0.13049618645321515, 2.82128046132439, 0.055]
cup_G[0].rotation = [0, 0, 0]
bowl_A[0].position = [0.48422214032777255, 0.9123876273135444, 0.045]
bowl_A[0].rotation = [0, 0, 0]
cabinet_E[0].position = [1.1967639756716921, 2.4967058940084574, 0.45]
cabinet_E[0].rotation = [0, 0, 0]
cabinet_F[0].position = [3.362868359013054, 2.9254439117551048, 0.35]
cabinet_F[0].rotation = [0, 0, 0]
fruit[0].position = [1.8089914178650703, 2.542021850146962, 0.04]
fruit[0].rotation = [0, 0, 0]
cup_H[0].position = [1.840215201602787, 2.740027385341859, 0.055]
cup_H[0].rotation = [0, 0, 0]
oven[0].position = [2.3117461432685715, 0.019500429844804476, 0.425]
oven[0].rotation = [0, 0, 0]
bottle_B[0].position = [1.6921519772347535, 4.062766802564674, 0.15]
bottle_B[0].rotation = [0, 0, 0]
bottle_C[0].position = [3.0443596715862005, 2.0332803314276386, 0.15]
bottle_C[0].rotation = [0, 0, 0]
cabinet_G[0].position = [0.9155904489485863, 2.3097470999211747, 0.45]
cabinet_G[0].rotation = [0, 0, 0]
microwave[0].position = [5.383497510774336, 2.5658894281736844, 0.155]
microwave[0].rotation = [0, 0, 0]
cup_I[0].position = [0.35117800150546724, 2.3226926221470885, 0.055]
cup_I[0].rotation = [0, 0, 0]
can_C[0].position = [0.17700656086100086, 2.574540668830251, 0.06]
can_C[0].rotation = [0, 0, 0]
bowl_B[0].position = [1.4560890577730963, 2.5106708319237554, 0.05]
bowl_B[0].rotation = [0, 0, 0]
cup_J[0].position = [3.543793001952525, 2.060149926638388, 0.055]
cup_J[0].rotation = [0, 0, 0]
cup_A[0].position = [0.5746862237306947, 3.75103648927413, 0.055]
cup_A[0].rotation = [0, 0, 0]
table[0].position = [3.7127352306087475, 0.26458462627874263, 0.375]
table[0].rotation = [0, 0, 0]
cup_B[0].position = [2.465761083550346, 3.3335794352267434, 0.055]
cup_B[0].rotation = [0, 0, 0]
bottle_A[0].position = [4.546928362789192, 1.635398751805023, 0.14]
bottle_A[0].rotation = [0, 0, 0]
stove[0].position = [1.7011721387450647, 0.9032519095852115, 0.04]
stove[0].rotation = [0, 0, 0]
towel[0].position = [4.43022673424648, 2.1143501527280844, 0.375]
towel[0].rotation = [0, 0, 0]
cabinet_A[0].position = [2.933506834962686, 3.253247829164064, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
cup_C[0].position = [0.8209377386641706, 0.8694818314855647, 0.055]
cup_C[0].rotation = [0, 0, 0]
box_A[0].position = [1.2655789881217372, 2.1207467354708087, 0.09]
box_A[0].rotation = [0, 0, 0]
can_A[0].position = [1.5498837401075072, 0.19964645950248217, 0.06]
can_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [3.912308084302264, 0.5153560671561923, 0.35]
cabinet_B[0].rotation = [0, 0, 0]
cabinet_C[0].position = [5.531431383251785, 3.831026434615191, 0.45]
cabinet_C[0].rotation = [0, 0, 0]
bin[0].position = [2.400092699498246, 3.986018749962914, 0.25]
bin[0].rotation = [0, 0, 0]
cup_D[0].position = [5.0410287834359115, 1.6280235690574298, 0.055]
cup_D[0].rotation = [0, 0, 0]
box_B[0].position = [1.3227006650972146, 3.7552331574922024, 0.08]
box_B[0].rotation = [0, 0, 0]
can_B[0].position = [3.4395299599042883, 4.284397146156894, 0.06]
can_B[0].rotation = [0, 0, 0]
cabinet_D[0].position = [1.4569686178774746, 2.298313260914441, 0.35]
cabinet_D[0].rotation = [0, 0, 0]
cup_E[0].position = [3.784026185072404, 3.6494582995911427, 0.055]
cup_E[0].rotation = [0, 0, 0]
refrigerator[0].position = [4.242280115537755, 1.3797435656110937, 0.9]
refrigerator[0].rotation = [0, 0, 0]
cup_F[0].position = [3.4333358619025893, 2.135321851696074, 0.055]
cup_F[0].rotation = [0, 0, 0]
box_C[0].position = [3.6245277448387863, 3.33496858293911, 0.1]
box_C[0].rotation = [0, 0, 0]
box_D[0].position = [2.1432186040861927, 3.896425719913429, 0.075]
box_D[0].rotation = [0, 0, 0]
cup_G[0].position = [0.13049618645321515, 2.82128046132439, 0.055]
cup_G[0].rotation = [0, 0, 0]
bowl_A[0].position = [0.48422214032777255, 0.9123876273135444, 0.045]
bowl_A[0].rotation = [0, 0, 0]
cabinet_E[0].position = [1.1967639756716921, 2.4967058940084574, 0.45]
cabinet_E[0].rotation = [0, 0, 0]
cabinet_F[0].position = [3.362868359013054, 2.9254439117551048, 0.35]
cabinet_F[0].rotation = [0, 0, 0]
fruit[0].position = [1.8089914178650703, 2.542021850146962, 0.04]
fruit[0].rotation = [0, 0, 0]
cup_H[0].position = [1.840215201602787, 2.740027385341859, 0.055]
cup_H[0].rotation = [0, 0, 0]
oven[0].position = [2.3117461432685715, 0.019500429844804476, 0.425]
oven[0].rotation = [0, 0, 0]
bottle_B[0].position = [1.6921519772347535, 4.062766802564674, 0.15]
bottle_B[0].rotation = [0, 0, 0]
bottle_C[0].position = [3.0443596715862005, 2.0332803314276386, 0.15]
bottle_C[0].rotation = [0, 0, 0]
cabinet_G[0].position = [0.9155904489485863, 2.3097470999211747, 0.45]
cabinet_G[0].rotation = [0, 0, 0]
microwave[0].position = [5.383497510774336, 2.5658894281736844, 0.155]
microwave[0].rotation = [0, 0, 0]
cup_I[0].position = [0.35117800150546724, 2.3226926221470885, 0.055]
cup_I[0].rotation = [0, 0, 0]
can_C[0].position = [0.17700656086100086, 2.574540668830251, 0.06]
can_C[0].rotation = [0, 0, 0]
bowl_B[0].position = [1.4560890577730963, 2.5106708319237554, 0.05]
bowl_B[0].rotation = [0, 0, 0]
cup_J[0].position = [3.543793001952525, 2.060149926638388, 0.055]
cup_J[0].rotation = [0, 0, 0]

solver.constraints = []

# Keep the doorway and its inward approach zone clear. The main counter run
# therefore ends at x=4.16, well before the door's left edge at x=4.81.
# The table forms a compact central work/dining island with ample circulation.

# Main cabinets along the upper wall, facing into the room (-y).
cabinet_A[0].position = [0.50, 4.08, 0.45]
cabinet_A[0].rotation = [0, 0, radians(-90)]

cabinet_C[0].position = [1.42, 4.08, 0.45]
cabinet_C[0].rotation = [0, 0, radians(-90)]

cabinet_E[0].position = [2.54, 4.08, 0.45]
cabinet_E[0].rotation = [0, 0, radians(-90)]

cabinet_G[0].position = [3.66, 4.08, 0.45]
cabinet_G[0].rotation = [0, 0, radians(-90)]

# Shallow cabinets form a second run along the lower wall and face +y.
cabinet_B[0].position = [1.40, 0.175, 0.35]
cabinet_B[0].rotation = [0, 0, radians(90)]

cabinet_D[0].position = [2.15, 0.175, 0.35]
cabinet_D[0].rotation = [0, 0, radians(90)]

cabinet_F[0].position = [2.85, 0.175, 0.35]
cabinet_F[0].rotation = [0, 0, radians(90)]

# The refrigerator occupies the remaining lower-wall segment.
refrigerator[0].position = [0.55, 0.375, 0.90]
refrigerator[0].rotation = [0, 0, radians(90)]

# The oven is against the right wall but remains south of the doorway approach.
oven[0].position = [5.48, 2.55, 0.425]
oven[0].rotation = [0, 0, radians(180)]

# The stove is centered on the oven.
stove[0].position = [5.48, 2.55, 0.89]
stove[0].rotation = [0, 0, radians(180)]

# Central table: its 1.40 m dimension runs north-south.
table[0].position = [2.30, 2.10, 0.375]
table[0].rotation = [0, 0, 0]

# Utility objects are kept against the left wall and away from circulation.
bin[0].position = [0.15, 1.25, 0.25]
bin[0].rotation = [0, 0, 0]

towel[0].position = [0.015, 2.80, 0.375]
towel[0].rotation = [0, 0, 0]

# Microwave and pantry items occupy cabinet_E's countertop.
microwave[0].position = [2.54, 4.08, 1.055]
microwave[0].rotation = [0, 0, radians(-90)]

bottle_A[0].position = [2.03, 3.90, 1.04]
bottle_A[0].rotation = [0, 0, radians(-90)]

bottle_B[0].position = [2.16, 3.90, 1.05]
bottle_B[0].rotation = [0, 0, radians(-90)]

bottle_C[0].position = [3.03, 3.90, 1.05]
bottle_C[0].rotation = [0, 0, radians(-90)]

can_A[0].position = [2.03, 4.08, 0.96]
can_A[0].rotation = [0, 0, radians(-90)]

can_B[0].position = [2.16, 4.08, 0.96]
can_B[0].rotation = [0, 0, radians(-90)]

can_C[0].position = [3.03, 4.08, 0.96]
can_C[0].rotation = [0, 0, radians(-90)]

# Boxes occupy two orderly rows on the southern half of the table.
box_A[0].position = [2.07, 1.62, 0.84]
box_A[0].rotation = [0, 0, 0]

box_C[0].position = [2.48, 1.62, 0.85]
box_C[0].rotation = [0, 0, 0]

box_B[0].position = [2.07, 2.02, 0.83]
box_B[0].rotation = [0, 0, 0]

box_D[0].position = [2.48, 2.02, 0.825]
box_D[0].rotation = [0, 0, 0]

# Bowls sit between the boxes and cups. Fruit is placed in bowl_A.
bowl_A[0].position = [2.05, 2.40, 0.795]
bowl_A[0].rotation = [0, 0, 0]

bowl_B[0].position = [2.48, 2.40, 0.80]
bowl_B[0].rotation = [0, 0, 0]

fruit[0].position = [2.05, 2.40, 0.88]
fruit[0].rotation = [0, 0, 0]

# Cups form two spaced rows along the northern end of the table.
cup_A[0].position = [1.98, 2.61, 0.805]
cup_A[0].rotation = [0, 0, 0]

cup_B[0].position = [2.14, 2.61, 0.805]
cup_B[0].rotation = [0, 0, 0]

cup_C[0].position = [2.30, 2.61, 0.805]
cup_C[0].rotation = [0, 0, 0]

cup_D[0].position = [2.46, 2.61, 0.805]
cup_D[0].rotation = [0, 0, 0]

cup_E[0].position = [2.62, 2.61, 0.805]
cup_E[0].rotation = [0, 0, 0]

cup_F[0].position = [1.98, 2.74, 0.805]
cup_F[0].rotation = [0, 0, 0]

cup_G[0].position = [2.14, 2.74, 0.805]
cup_G[0].rotation = [0, 0, 0]

cup_H[0].position = [2.30, 2.74, 0.805]
cup_H[0].rotation = [0, 0, 0]

cup_I[0].position = [2.46, 2.74, 0.805]
cup_I[0].rotation = [0, 0, 0]

cup_J[0].position = [2.62, 2.74, 0.805]
cup_J[0].rotation = [0, 0, 0]


# Fixed references let position and heading constraints preserve the designed
# arrangement if the solver makes feasibility adjustments.
_zero_heading = AssetInstance(rotation=[0, 0, 0])

def _pin(instance, position):
    solver.distance_constraint(
        instance,
        AssetInstance(position=position),
        0,
        0,
        weight=10,
    )


# Floor-standing perimeter assets: wall contact is the primary positional
# relationship, followed by an exact anchor and an inward-facing orientation.
solver.against_wall(cabinet_A[0], walls[7])
_pin(cabinet_A[0], [0.50, 4.08, 0.45])
solver.align_with(cabinet_A[0], _zero_heading, angle=-90)

solver.against_wall(cabinet_C[0], walls[7])
_pin(cabinet_C[0], [1.42, 4.08, 0.45])
solver.align_with(cabinet_C[0], _zero_heading, angle=-90)

solver.against_wall(cabinet_E[0], walls[7])
_pin(cabinet_E[0], [2.54, 4.08, 0.45])
solver.align_with(cabinet_E[0], _zero_heading, angle=-90)

solver.against_wall(cabinet_G[0], walls[7])
_pin(cabinet_G[0], [3.66, 4.08, 0.45])
solver.align_with(cabinet_G[0], _zero_heading, angle=-90)

solver.against_wall(cabinet_B[0], walls[2])
_pin(cabinet_B[0], [1.40, 0.175, 0.35])
solver.align_with(cabinet_B[0], _zero_heading, angle=90)

solver.against_wall(cabinet_D[0], walls[2])
_pin(cabinet_D[0], [2.15, 0.175, 0.35])
solver.align_with(cabinet_D[0], _zero_heading, angle=90)

solver.against_wall(cabinet_F[0], walls[2])
_pin(cabinet_F[0], [2.85, 0.175, 0.35])
solver.align_with(cabinet_F[0], _zero_heading, angle=90)

solver.against_wall(refrigerator[0], walls[2])
_pin(refrigerator[0], [0.55, 0.375, 0.90])
solver.align_with(refrigerator[0], _zero_heading, angle=90)

solver.against_wall(oven[0], walls[5])
_pin(oven[0], [5.48, 2.55, 0.425])
solver.align_with(oven[0], _zero_heading, angle=180)

solver.against_wall(bin[0], walls[0])
_pin(bin[0], [0.15, 1.25, 0.25])
solver.align_with(bin[0], _zero_heading)

solver.against_wall(towel[0], walls[0])
_pin(towel[0], [0.015, 2.80, 0.375])
solver.align_with(towel[0], _zero_heading)

# The freestanding table is fixed in the open central area.
_pin(table[0], [2.30, 2.10, 0.375])
solver.align_with(table[0], _zero_heading)

# Appliance support relationships.
solver.on_top_of(stove[0], oven[0])
_pin(stove[0], [5.48, 2.55, 0.89])
solver.align_with(stove[0], oven[0])

solver.on_top_of(microwave[0], cabinet_E[0])
_pin(microwave[0], [2.54, 4.08, 1.055])
solver.align_with(microwave[0], cabinet_E[0])

# Countertop bottles and cans.
solver.on_top_of(bottle_A[0], cabinet_E[0])
_pin(bottle_A[0], [2.03, 3.90, 1.04])
solver.align_with(bottle_A[0], cabinet_E[0])

solver.on_top_of(bottle_B[0], cabinet_E[0])
_pin(bottle_B[0], [2.16, 3.90, 1.05])
solver.align_with(bottle_B[0], cabinet_E[0])

solver.on_top_of(bottle_C[0], cabinet_E[0])
_pin(bottle_C[0], [3.03, 3.90, 1.05])
solver.align_with(bottle_C[0], cabinet_E[0])

solver.on_top_of(can_A[0], cabinet_E[0])
_pin(can_A[0], [2.03, 4.08, 0.96])
solver.align_with(can_A[0], cabinet_E[0])

solver.on_top_of(can_B[0], cabinet_E[0])
_pin(can_B[0], [2.16, 4.08, 0.96])
solver.align_with(can_B[0], cabinet_E[0])

solver.on_top_of(can_C[0], cabinet_E[0])
_pin(can_C[0], [3.03, 4.08, 0.96])
solver.align_with(can_C[0], cabinet_E[0])

# Tabletop boxes.
solver.on_top_of(box_A[0], table[0])
_pin(box_A[0], [2.07, 1.62, 0.84])
solver.align_with(box_A[0], table[0])

solver.on_top_of(box_B[0], table[0])
_pin(box_B[0], [2.07, 2.02, 0.83])
solver.align_with(box_B[0], table[0])

solver.on_top_of(box_C[0], table[0])
_pin(box_C[0], [2.48, 1.62, 0.85])
solver.align_with(box_C[0], table[0])

solver.on_top_of(box_D[0], table[0])
_pin(box_D[0], [2.48, 2.02, 0.825])
solver.align_with(box_D[0], table[0])

# Bowls and fruit.
solver.on_top_of(bowl_A[0], table[0])
_pin(bowl_A[0], [2.05, 2.40, 0.795])
solver.align_with(bowl_A[0], table[0])

solver.on_top_of(bowl_B[0], table[0])
_pin(bowl_B[0], [2.48, 2.40, 0.80])
solver.align_with(bowl_B[0], table[0])

solver.on_top_of(fruit[0], bowl_A[0])
_pin(fruit[0], [2.05, 2.40, 0.88])
solver.align_with(fruit[0], bowl_A[0])

# Every cup is supported by, positioned on, and aligned with the table.
solver.on_top_of(cup_A[0], table[0])
_pin(cup_A[0], [1.98, 2.61, 0.805])
solver.align_with(cup_A[0], table[0])

solver.on_top_of(cup_B[0], table[0])
_pin(cup_B[0], [2.14, 2.61, 0.805])
solver.align_with(cup_B[0], table[0])

solver.on_top_of(cup_C[0], table[0])
_pin(cup_C[0], [2.30, 2.61, 0.805])
solver.align_with(cup_C[0], table[0])

solver.on_top_of(cup_D[0], table[0])
_pin(cup_D[0], [2.46, 2.61, 0.805])
solver.align_with(cup_D[0], table[0])

solver.on_top_of(cup_E[0], table[0])
_pin(cup_E[0], [2.62, 2.61, 0.805])
solver.align_with(cup_E[0], table[0])

solver.on_top_of(cup_F[0], table[0])
_pin(cup_F[0], [1.98, 2.74, 0.805])
solver.align_with(cup_F[0], table[0])

solver.on_top_of(cup_G[0], table[0])
_pin(cup_G[0], [2.14, 2.74, 0.805])
solver.align_with(cup_G[0], table[0])

solver.on_top_of(cup_H[0], table[0])
_pin(cup_H[0], [2.30, 2.74, 0.805])
solver.align_with(cup_H[0], table[0])

solver.on_top_of(cup_I[0], table[0])
_pin(cup_I[0], [2.46, 2.74, 0.805])
solver.align_with(cup_I[0], table[0])

solver.on_top_of(cup_J[0], table[0])
_pin(cup_J[0], [2.62, 2.74, 0.805])
solver.align_with(cup_J[0], table[0])

solver.constraints = []
box_A[0].position = [2.069999933242798, 1.6200000047683716, 0.8400000333786011]
box_A[0].rotation = [0, 0, 0.10997300186267076]
box_A[0].optimize = 2
cup_F[0].position = [1.9800000190734863, 2.740000009536743, 0.8050000071525574]
cup_F[0].rotation = [0, 0, 0.10997300186267076]
cup_F[0].optimize = 2
cabinet_B[0].position = [1.399999976158142, 0.1750006079673767, 0.3499999940395355]
cabinet_B[0].rotation = [0, 0, 1.5707943862799623]
cabinet_B[0].optimize = 2
bowl_B[0].position = [2.4800000190734863, 2.4000000953674316, 0.800000011920929]
bowl_B[0].rotation = [0, 0, 0.10997300186267076]
bowl_B[0].optimize = 2
bowl_A[0].position = [2.049999952316284, 2.4000000953674316, 0.7950000166893005]
bowl_A[0].rotation = [0, 0, 0.10995232644427605]
bowl_A[0].optimize = 2
fruit[0].position = [2.049999952316284, 2.4000000953674316, 0.8800000548362732]
fruit[0].rotation = [0, 0, 0.10995226625293901]
fruit[0].optimize = 2
stove[0].position = [5.480000019073486, 2.549999952316284, 0.89000004529953]
stove[0].rotation = [0, 0, -3.1415916810583657]
stove[0].optimize = 2
bottle_C[0].position = [3.0299999713897705, 3.9000000953674316, 1.0499999523162842]
bottle_C[0].rotation = [0, 0, -1.5708154226240352]
bottle_C[0].optimize = 2
towel[0].position = [0.014999437145888805, 2.799999952316284, 0.375]
towel[0].rotation = [0, 0, -1.9502476627342156e-06]
towel[0].optimize = 2
cabinet_C[0].position = [1.4199999570846558, 4.0750017166137695, 0.44999998807907104]
cabinet_C[0].rotation = [0, 0, -1.5707982628480397]
cabinet_C[0].optimize = 2
cup_A[0].position = [1.9800000190734863, 2.609999895095825, 0.8050000071525574]
cup_A[0].rotation = [0, 0, 0.10997300186267076]
cup_A[0].optimize = 2
refrigerator[0].position = [0.550000011920929, 0.3749989867210388, 0.8999999761581421]
refrigerator[0].rotation = [0, 0, 1.5707944002370218]
refrigerator[0].optimize = 2
cup_G[0].position = [2.140000104904175, 2.740000009536743, 0.8050000071525574]
cup_G[0].rotation = [0, 0, 0.10997300186267076]
cup_G[0].optimize = 2
cup_I[0].position = [2.4600000381469727, 2.740000009536743, 0.8050000071525574]
cup_I[0].rotation = [0, 0, 0.10997300186267076]
cup_I[0].optimize = 2
cabinet_G[0].position = [3.6600000858306885, 4.0750017166137695, 0.44999998807907104]
cabinet_G[0].rotation = [0, 0, -1.5707982628480397]
cabinet_G[0].optimize = 2
cabinet_E[0].position = [2.5399999618530273, 4.075001239776611, 0.44999998807907104]
cabinet_E[0].rotation = [0, 0, -1.5708060558498995]
cabinet_E[0].optimize = 2
table[0].position = [2.299999952316284, 2.0999999046325684, 0.375]
table[0].rotation = [0, 0, 0.1099557411604048]
table[0].optimize = 2
cup_E[0].position = [2.619999885559082, 2.609999895095825, 0.8050000071525574]
cup_E[0].rotation = [0, 0, 0.10997300186267076]
cup_E[0].optimize = 2
cup_J[0].position = [2.619999885559082, 2.740000009536743, 0.8050000071525574]
cup_J[0].rotation = [0, 0, 0.10997300186267076]
cup_J[0].optimize = 2
cup_D[0].position = [2.4600000381469727, 2.609999895095825, 0.8050000071525574]
cup_D[0].rotation = [0, 0, 0.10997300186267076]
cup_D[0].optimize = 2
box_C[0].position = [2.4800000190734863, 1.6200000047683716, 0.8500000238418579]
box_C[0].rotation = [0, 0, 0.10997300186267076]
box_C[0].optimize = 2
cup_C[0].position = [2.299999952316284, 2.609999895095825, 0.8050000071525574]
cup_C[0].rotation = [0, 0, 0.10997300186267076]
cup_C[0].optimize = 2
cabinet_F[0].position = [2.8499999046325684, 0.1750006079673767, 0.3499999940395355]
cabinet_F[0].rotation = [0, 0, 1.5707943862799623]
cabinet_F[0].optimize = 2
can_B[0].position = [2.1600000858306885, 4.079999923706055, 0.9599999785423279]
can_B[0].rotation = [0, 0, -1.5708154226240352]
can_B[0].optimize = 2
oven[0].position = [5.4812517166137695, 2.549999952316284, 0.42500001192092896]
oven[0].rotation = [0, 0, -3.141589873845596]
oven[0].optimize = 2
cup_H[0].position = [2.299999952316284, 2.740000009536743, 0.8050000071525574]
cup_H[0].rotation = [0, 0, 0.10997300186267076]
cup_H[0].optimize = 2
cabinet_D[0].position = [2.1500000953674316, 0.17499855160713196, 0.3499999940395355]
cabinet_D[0].rotation = [0, 0, 1.5707943870972565]
cabinet_D[0].optimize = 2
can_A[0].position = [2.0299999713897705, 4.079999923706055, 0.9599999785423279]
can_A[0].rotation = [0, 0, -1.5708154226240352]
can_A[0].optimize = 2
bin[0].position = [0.15000136196613312, 1.25, 0.25]
bin[0].rotation = [0, 0, -1.9405355641239893e-06]
bin[0].optimize = 2
can_C[0].position = [3.0299999713897705, 4.079999923706055, 0.9599999785423279]
can_C[0].rotation = [0, 0, -1.5708154226240352]
can_C[0].optimize = 2
bottle_B[0].position = [2.1600000858306885, 3.9000000953674316, 1.0499999523162842]
bottle_B[0].rotation = [0, 0, -1.5708154226240352]
bottle_B[0].optimize = 2
cup_B[0].position = [2.140000104904175, 2.609999895095825, 0.8050000071525574]
cup_B[0].rotation = [0, 0, 0.10997300186267076]
cup_B[0].optimize = 2
bottle_A[0].position = [2.0299999713897705, 3.9000000953674316, 1.0399999618530273]
bottle_A[0].rotation = [0, 0, -1.5708154226240352]
bottle_A[0].optimize = 2
cabinet_A[0].position = [0.5, 4.075001239776611, 0.44999998807907104]
cabinet_A[0].rotation = [0, 0, -1.5707982526093958]
cabinet_A[0].optimize = 2
microwave[0].position = [2.5399999618530273, 4.079999923706055, 1.0549999475479126]
microwave[0].rotation = [0, 0, -1.5708154226240352]
microwave[0].optimize = 2
box_D[0].position = [2.4800000190734863, 2.0199999809265137, 0.824999988079071]
box_D[0].rotation = [0, 0, 0.10997300186267076]
box_D[0].optimize = 2
box_B[0].position = [2.069999933242798, 2.0199999809265137, 0.8299999833106995]
box_B[0].rotation = [0, 0, 0.10997300186267076]
box_B[0].optimize = 2

