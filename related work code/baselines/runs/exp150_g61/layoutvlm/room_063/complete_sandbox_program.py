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
    Wall(corner1=[0.00, 7.62, 0.00], corner2=[0.00, 0.04, 0.00]),
    Wall(corner1=[0.00, 0.04, 0.00], corner2=[0.04, 0.00, 0.00]),
    Wall(corner1=[0.04, 0.00, 0.00], corner2=[6.45, 0.00, 0.00]),
    Wall(corner1=[6.45, 0.00, 0.00], corner2=[6.48, 0.04, 0.00]),
    Wall(corner1=[6.48, 0.04, 0.00], corner2=[6.48, 7.62, 0.00]),
    Wall(corner1=[6.48, 7.62, 0.00], corner2=[6.45, 7.66, 0.00]),
    Wall(corner1=[6.45, 7.66, 0.00], corner2=[0.04, 7.66, 0.00]),
    Wall(corner1=[0.04, 7.66, 0.00], corner2=[0.00, 7.62, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
cabinet_A = Assets(description="cabinet", size=[0.60, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
table_A = Assets(description="table", size=[0.85, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
basket = Assets(description="basket", size=[0.28, 0.35, 0.25], placements=[AssetInstance() for _ in range(1)])
table_B = Assets(description="table", size=[0.80, 1.40, 0.75], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
refrigerator = Assets(description="refrigerator", size=[0.70, 0.70, 1.85], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.35, 0.80, 0.70], placements=[AssetInstance() for _ in range(1)])
cabinet_C = Assets(description="cabinet", size=[0.60, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
cup_A = Assets(description="cup", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
backpack = Assets(description="backpack", size=[0.20, 0.32, 0.45], placements=[AssetInstance() for _ in range(1)])
cabinet_D = Assets(description="cabinet", size=[0.35, 0.80, 0.70], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
cabinet_E = Assets(description="cabinet", size=[0.45, 1.20, 0.85], placements=[AssetInstance() for _ in range(1)])
chair_D = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
chair_E = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
dishwasher = Assets(description="dishwasher", size=[0.60, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
chair_F = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
chair_G = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
couch_A = Assets(description="couch", size=[0.85, 1.65, 0.82], placements=[AssetInstance() for _ in range(1)])
chair_H = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
kettle = Assets(description="kettle", size=[0.18, 0.22, 0.25], placements=[AssetInstance() for _ in range(1)])
can = Assets(description="can", size=[0.07, 0.07, 0.12], placements=[AssetInstance() for _ in range(1)])
box = Assets(description="box", size=[0.25, 0.30, 0.20], placements=[AssetInstance() for _ in range(1)])
chair_I = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
table_C = Assets(description="table", size=[0.60, 1.10, 0.42], placements=[AssetInstance() for _ in range(1)])
stool = Assets(description="stool", size=[0.35, 0.35, 0.45], placements=[AssetInstance() for _ in range(1)])
couch_B = Assets(description="couch", size=[0.85, 1.65, 0.82], placements=[AssetInstance() for _ in range(1)])
cup_B = Assets(description="cup", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
chair_J = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
cabinet_F = Assets(description="cabinet", size=[0.60, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
chair_K = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
cup_C = Assets(description="cup", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
couch_C = Assets(description="couch", size=[0.85, 1.65, 0.82], placements=[AssetInstance() for _ in range(1)])

cabinet_A[0].instance_id = 'cabinet_A_0'
chair_A[0].instance_id = 'chair_A_0'
table_A[0].instance_id = 'table_A_0'
basket[0].instance_id = 'basket_0'
table_B[0].instance_id = 'table_B_0'
chair_B[0].instance_id = 'chair_B_0'
refrigerator[0].instance_id = 'refrigerator_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
cabinet_C[0].instance_id = 'cabinet_C_0'
cup_A[0].instance_id = 'cup_A_0'
backpack[0].instance_id = 'backpack_0'
cabinet_D[0].instance_id = 'cabinet_D_0'
chair_C[0].instance_id = 'chair_C_0'
cabinet_E[0].instance_id = 'cabinet_E_0'
chair_D[0].instance_id = 'chair_D_0'
chair_E[0].instance_id = 'chair_E_0'
dishwasher[0].instance_id = 'dishwasher_0'
chair_F[0].instance_id = 'chair_F_0'
chair_G[0].instance_id = 'chair_G_0'
couch_A[0].instance_id = 'couch_A_0'
chair_H[0].instance_id = 'chair_H_0'
kettle[0].instance_id = 'kettle_0'
can[0].instance_id = 'can_0'
box[0].instance_id = 'box_0'
chair_I[0].instance_id = 'chair_I_0'
table_C[0].instance_id = 'table_C_0'
stool[0].instance_id = 'stool_0'
couch_B[0].instance_id = 'couch_B_0'
cup_B[0].instance_id = 'cup_B_0'
chair_J[0].instance_id = 'chair_J_0'
cabinet_F[0].instance_id = 'cabinet_F_0'
chair_K[0].instance_id = 'chair_K_0'
cup_C[0].instance_id = 'cup_C_0'
couch_C[0].instance_id = 'couch_C_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

cabinet_A[0].position = [4.123163974856989, 4.181450281951378, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
chair_A[0].position = [5.580467236684718, 0.8782830098739091, 0.425]
chair_A[0].rotation = [0, 0, 0]
table_A[0].position = [3.7167962133631978, 0.33927712459760423, 0.375]
table_A[0].rotation = [0, 0, 0]
basket[0].position = [6.186018838949444, 3.5642437589246887, 0.125]
basket[0].rotation = [0, 0, 0]
table_B[0].position = [1.1696068330843539, 7.370877771986246, 0.375]
table_B[0].rotation = [0, 0, 0]
chair_B[0].position = [3.0407429869459035, 5.142349559743713, 0.425]
chair_B[0].rotation = [0, 0, 0]
refrigerator[0].position = [4.207428490844246, 2.894413870701523, 0.925]
refrigerator[0].rotation = [0, 0, 0]
cabinet_B[0].position = [3.263035588673723, 4.974413017933263, 0.35]
cabinet_B[0].rotation = [0, 0, 0]
cabinet_C[0].position = [3.416964725533464, 4.791007825993894, 0.45]
cabinet_C[0].rotation = [0, 0, 0]
cup_A[0].position = [2.633701380388281, 1.5817125303807957, 0.05]
cup_A[0].rotation = [0, 0, 0]
backpack[0].position = [5.449740393926966, 1.111387666774908, 0.225]
backpack[0].rotation = [0, 0, 0]
cabinet_D[0].position = [4.464007026351576, 0.4244330417863314, 0.35]
cabinet_D[0].rotation = [0, 0, 0]
chair_C[0].position = [5.7558321668596255, 3.6974790178614003, 0.425]
chair_C[0].rotation = [0, 0, 0]
cabinet_E[0].position = [0.553875544093751, 4.423896623261491, 0.425]
cabinet_E[0].rotation = [0, 0, 0]
chair_D[0].position = [2.3628867720667626, 5.274833137291689, 0.425]
chair_D[0].rotation = [0, 0, 0]
chair_E[0].position = [0.9642918495291785, 6.445215528686957, 0.425]
chair_E[0].rotation = [0, 0, 0]
dishwasher[0].position = [6.265616834329401, 6.371694574100197, 0.425]
dishwasher[0].rotation = [0, 0, 0]
chair_F[0].position = [5.916043372843692, 5.143120983683309, 0.425]
chair_F[0].rotation = [0, 0, 0]
chair_G[0].position = [2.6801227587992695, 6.255853202259341, 0.425]
chair_G[0].rotation = [0, 0, 0]
couch_A[0].position = [2.8657507820118524, 0.9372981353811334, 0.41]
couch_A[0].rotation = [0, 0, 0]
chair_H[0].position = [2.2710664913375, 0.8183204451735606, 0.425]
chair_H[0].rotation = [0, 0, 0]
kettle[0].position = [1.7883948448437483, 4.445258544273254, 0.125]
kettle[0].rotation = [0, 0, 0]
can[0].position = [2.8966095039782536, 3.726785332167002, 0.06]
can[0].rotation = [0, 0, 0]
box[0].position = [4.246483918155487, 1.4412790515150606, 0.1]
box[0].rotation = [0, 0, 0]
chair_I[0].position = [1.3086071820416314, 4.525022816123189, 0.425]
chair_I[0].rotation = [0, 0, 0]
table_C[0].position = [5.715879182978429, 5.872870946120401, 0.21]
table_C[0].rotation = [0, 0, 0]
stool[0].position = [2.9828550366114173, 5.60667271309994, 0.225]
stool[0].rotation = [0, 0, 0]
couch_B[0].position = [1.3471852838053935, 4.2286073136709685, 0.41]
couch_B[0].rotation = [0, 0, 0]
cup_B[0].position = [3.0927504073587606, 0.047424846258790516, 0.05]
cup_B[0].rotation = [0, 0, 0]
chair_J[0].position = [2.63781159318549, 3.2248762878980055, 0.425]
chair_J[0].rotation = [0, 0, 0]
cabinet_F[0].position = [2.179055890973022, 4.542005256055353, 0.45]
cabinet_F[0].rotation = [0, 0, 0]
chair_K[0].position = [4.577552371936078, 4.066620097288829, 0.425]
chair_K[0].rotation = [0, 0, 0]
cup_C[0].position = [0.5033637140707072, 6.292902170608566, 0.05]
cup_C[0].rotation = [0, 0, 0]
couch_C[0].position = [4.661346146843338, 5.898228118258717, 0.41]
couch_C[0].rotation = [0, 0, 0]
cabinet_A[0].position = [4.123163974856989, 4.181450281951378, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
chair_A[0].position = [5.580467236684718, 0.8782830098739091, 0.425]
chair_A[0].rotation = [0, 0, 0]
table_A[0].position = [3.7167962133631978, 0.33927712459760423, 0.375]
table_A[0].rotation = [0, 0, 0]
basket[0].position = [6.186018838949444, 3.5642437589246887, 0.125]
basket[0].rotation = [0, 0, 0]
table_B[0].position = [1.1696068330843539, 7.370877771986246, 0.375]
table_B[0].rotation = [0, 0, 0]
chair_B[0].position = [3.0407429869459035, 5.142349559743713, 0.425]
chair_B[0].rotation = [0, 0, 0]
refrigerator[0].position = [4.207428490844246, 2.894413870701523, 0.925]
refrigerator[0].rotation = [0, 0, 0]
cabinet_B[0].position = [3.263035588673723, 4.974413017933263, 0.35]
cabinet_B[0].rotation = [0, 0, 0]
cabinet_C[0].position = [3.416964725533464, 4.791007825993894, 0.45]
cabinet_C[0].rotation = [0, 0, 0]
cup_A[0].position = [2.633701380388281, 1.5817125303807957, 0.05]
cup_A[0].rotation = [0, 0, 0]
backpack[0].position = [5.449740393926966, 1.111387666774908, 0.225]
backpack[0].rotation = [0, 0, 0]
cabinet_D[0].position = [4.464007026351576, 0.4244330417863314, 0.35]
cabinet_D[0].rotation = [0, 0, 0]
chair_C[0].position = [5.7558321668596255, 3.6974790178614003, 0.425]
chair_C[0].rotation = [0, 0, 0]
cabinet_E[0].position = [0.553875544093751, 4.423896623261491, 0.425]
cabinet_E[0].rotation = [0, 0, 0]
chair_D[0].position = [2.3628867720667626, 5.274833137291689, 0.425]
chair_D[0].rotation = [0, 0, 0]
chair_E[0].position = [0.9642918495291785, 6.445215528686957, 0.425]
chair_E[0].rotation = [0, 0, 0]
dishwasher[0].position = [6.265616834329401, 6.371694574100197, 0.425]
dishwasher[0].rotation = [0, 0, 0]
chair_F[0].position = [5.916043372843692, 5.143120983683309, 0.425]
chair_F[0].rotation = [0, 0, 0]
chair_G[0].position = [2.6801227587992695, 6.255853202259341, 0.425]
chair_G[0].rotation = [0, 0, 0]
couch_A[0].position = [2.8657507820118524, 0.9372981353811334, 0.41]
couch_A[0].rotation = [0, 0, 0]
chair_H[0].position = [2.2710664913375, 0.8183204451735606, 0.425]
chair_H[0].rotation = [0, 0, 0]
kettle[0].position = [1.7883948448437483, 4.445258544273254, 0.125]
kettle[0].rotation = [0, 0, 0]
can[0].position = [2.8966095039782536, 3.726785332167002, 0.06]
can[0].rotation = [0, 0, 0]
box[0].position = [4.246483918155487, 1.4412790515150606, 0.1]
box[0].rotation = [0, 0, 0]
chair_I[0].position = [1.3086071820416314, 4.525022816123189, 0.425]
chair_I[0].rotation = [0, 0, 0]
table_C[0].position = [5.715879182978429, 5.872870946120401, 0.21]
table_C[0].rotation = [0, 0, 0]
stool[0].position = [2.9828550366114173, 5.60667271309994, 0.225]
stool[0].rotation = [0, 0, 0]
couch_B[0].position = [1.3471852838053935, 4.2286073136709685, 0.41]
couch_B[0].rotation = [0, 0, 0]
cup_B[0].position = [3.0927504073587606, 0.047424846258790516, 0.05]
cup_B[0].rotation = [0, 0, 0]
chair_J[0].position = [2.63781159318549, 3.2248762878980055, 0.425]
chair_J[0].rotation = [0, 0, 0]
cabinet_F[0].position = [2.179055890973022, 4.542005256055353, 0.45]
cabinet_F[0].rotation = [0, 0, 0]
chair_K[0].position = [4.577552371936078, 4.066620097288829, 0.425]
chair_K[0].rotation = [0, 0, 0]
cup_C[0].position = [0.5033637140707072, 6.292902170608566, 0.05]
cup_C[0].rotation = [0, 0, 0]
couch_C[0].position = [4.661346146843338, 5.898228118258717, 0.41]
couch_C[0].rotation = [0, 0, 0]

solver.constraints = []

# The o#### identifiers correspond to the zero-based asset order:
# o0013 = cabinet_E, o0017 = chair_F, o0024 = chair_I,
# o0029 = chair_J, and o0031 = chair_K.
#
# Use the actual wall coordinates, rather than assuming a centered origin.
# Keep x >= 5.40 clear below y = 7.05 for both east-wall door approaches.
# Leave the fixed fireplace footprint (x=0.38..1.94, y=0..0.57) empty.

# Floor-standing furniture: (asset, x, y, heading in degrees).
# North-wall storage, two dining groups, and a west/south lounge are separated
# by circulation space. Coordinates account for rotated bounding boxes.
floor_layout = [
    (cabinet_A,    1.40, 7.360, -90),
    (cabinet_B,    4.60, 7.485, -90),
    (cabinet_C,    2.20, 7.360, -90),
    (cabinet_D,    5.50, 7.485, -90),
    (cabinet_E,    0.225, 3.48,   0),
    (cabinet_F,    3.70, 7.360, -90),
    (refrigerator, 0.50, 7.310, -90),
    (dishwasher,   2.90, 7.360, -90),

    (table_A,      1.90, 5.45,   0),
    (table_B,      3.65, 4.90,   0),
    (table_C,      1.80, 1.65,   0),

    (chair_A,      1.90, 6.65, -90),
    (chair_B,      1.90, 4.25,  90),
    (chair_C,      2.85, 5.00, 180),
    (chair_D,      2.85, 5.80, 180),
    (chair_E,      3.65, 6.15, -90),
    (chair_F,      4.65, 4.20, 180),
    (chair_G,      2.85, 1.65, 180),
    (chair_H,      3.65, 3.65,  90),
    (chair_I,      4.65, 3.48, 180),
    (chair_J,      4.65, 5.60, 180),
    (chair_K,      4.65, 4.90, 180),

    (couch_A,      0.425, 1.60,  0),
    (couch_B,      3.30, 0.425, 90),
    (couch_C,      0.425, 5.35,  0),
    (stool,        1.80, 2.70, -90),
]

for asset_spec, px, py, heading in floor_layout:
    asset_spec[0].position = [px, py, asset_spec.size[2] / 2]
    asset_spec[0].rotation = [0, 0, radians(heading)]

# Small items rest on real surfaces, with their centers above the surface.
# Offsets keep each item wholly within its supporting tabletop/cabinet.
surface_layout = [
    (basket,   cabinet_B, 4.60, 7.485, -90),
    (backpack, cabinet_D, 5.50, 7.485, -90),
    (box,      cabinet_C, 2.20, 7.360, -90),
    (kettle,   cabinet_A, 1.40, 7.360, -90),
    (can,      cabinet_F, 3.70, 7.360, -90),
    (cup_A,    table_A,   1.90, 5.650,   0),
    (cup_B,    table_B,   3.65, 5.100,   0),
    (cup_C,    table_C,   1.80, 1.650,   0),
]

for item_spec, support_spec, px, py, heading in surface_layout:
    surface_z = support_spec[0].position[2] + support_spec.size[2] / 2
    item_spec[0].position = [px, py, surface_z + item_spec.size[2] / 2]
    item_spec[0].rotation = [0, 0, radians(heading)]

# Highest-priority semantic constraints.
solver.point_towards(chair_I[0], cabinet_E[0])

# "Within 0.30 m" is interpreted as edge-to-edge clearance:
# 0.72 m center spacing minus 0.48 m chair width leaves a 0.24 m gap.
# A 0.30 m center-distance limit would force these chairs to overlap.
solver.distance_constraint(chair_I[0], chair_F[0], 0.72, 0.72, weight=10)
solver.align_with(chair_I[0], chair_F[0])

# Triangle equality places K on the segment between J and F.
solver.distance_constraint(chair_K[0], chair_F[0], 0.70, 0.70, weight=10)
solver.distance_constraint(chair_K[0], chair_J[0], 0.70, 0.70, weight=10)
solver.distance_constraint(chair_J[0], chair_F[0], 1.40, 1.40, weight=10)
solver.align_with(chair_K[0], chair_F[0])
solver.align_with(chair_J[0], chair_F[0])

# Positional anchors preserve the collision-free arrangement, fireplace
# clearance, and door circulation. Each floor instance also receives an
# orientation constraint against its fixed reference.
for asset_spec, px, py, heading in floor_layout:
    layout_reference = AssetInstance(
        position=[px, py, asset_spec.size[2] / 2],
        rotation=[0, 0, radians(heading)],
    )
    solver.distance_constraint(
        asset_spec[0], layout_reference, 0, 0, weight=10
    )
    solver.align_with(asset_spec[0], layout_reference)

# Explicit wall relationships for storage and perimeter seating.
for storage_spec in [
    cabinet_A, cabinet_B, cabinet_C, cabinet_D,
    cabinet_F, refrigerator, dishwasher,
]:
    solver.against_wall(storage_spec[0], walls[6])

solver.against_wall(cabinet_E[0], walls[0])
solver.against_wall(couch_A[0], walls[0])
solver.against_wall(couch_C[0], walls[0])
solver.against_wall(couch_B[0], walls[2])

# Dining chairs have consistent orientations relative to their tables.
for dining_chair_spec in [chair_A, chair_E]:
    solver.align_with(dining_chair_spec[0], table_A[0], angle=-90)
for dining_chair_spec in [chair_B, chair_H]:
    solver.align_with(dining_chair_spec[0], table_A[0], angle=90)
for dining_chair_spec in [chair_C, chair_D, chair_F, chair_J, chair_K]:
    solver.align_with(dining_chair_spec[0], table_A[0], angle=180)
solver.point_towards(chair_G[0], table_C[0])
solver.point_towards(stool[0], table_C[0])

# Each small item receives support, position, and orientation constraints.
# Center distances include the vertical offset because the API uses 3D centers.
for item_spec, support_spec, px, py, heading in surface_layout:
    solver.on_top_of(item_spec[0], support_spec[0])

    center_distance = sum(
        (item_spec[0].position[axis] - support_spec[0].position[axis]) ** 2
        for axis in range(3)
    ) ** 0.5
    solver.distance_constraint(
        item_spec[0], support_spec[0],
        center_distance, center_distance, weight=10
    )
    solver.align_with(item_spec[0], support_spec[0])

    # The support-distance constraint alone permits lateral drift; this fixed
    # reference preserves the selected safe spot on the supporting surface.
    item_reference = AssetInstance(
        position=list(item_spec[0].position),
        rotation=list(item_spec[0].rotation),
    )
    solver.distance_constraint(
        item_spec[0], item_reference, 0, 0, weight=10
    )

solver.constraints = []
couch_B[0].position = [3.299999952316284, 0.42500001192092896, 0.4099999964237213]
couch_B[0].rotation = [0, 0, 1.5707963615361702]
couch_B[0].optimize = 2
chair_C[0].position = [2.8499999046325684, 5.0, 0.42500001192092896]
chair_C[0].rotation = [0, 0, -3.0944686726830053]
chair_C[0].optimize = 2
basket[0].position = [4.599999904632568, 7.516250133514404, 0.824999988079071]
basket[0].rotation = [0, 0, -1.5707962780041536]
basket[0].optimize = 2
dishwasher[0].position = [2.9000000953674316, 7.356249809265137, 0.42500001192092896]
dishwasher[0].rotation = [0, 0, -1.5707962844519943]
dishwasher[0].optimize = 2
chair_F[0].position = [4.650000095367432, 4.199999809265137, 0.42500001192092896]
chair_F[0].rotation = [0, 0, -3.0944686757090327]
chair_F[0].optimize = 2
table_B[0].position = [3.6500000953674316, 4.900000095367432, 0.375]
table_B[0].rotation = [0, 0, 0.01884955539881635]
table_B[0].optimize = 2
table_C[0].position = [1.7999999523162842, 1.649999976158142, 0.20999999344348907]
table_C[0].rotation = [0, 0, 0.025132740109855806]
table_C[0].optimize = 2
chair_I[0].position = [4.650000095367432, 3.4800000190734863, 0.42500001192092896]
chair_I[0].rotation = [0, 0, -3.0944686813285895]
chair_I[0].optimize = 2
cup_A[0].position = [1.899999976158142, 6.035370826721191, 0.800000011920929]
cup_A[0].rotation = [0, 0, 0.047123893767390714]
cup_A[0].optimize = 2
cabinet_F[0].position = [3.700000047683716, 7.356249809265137, 0.44999998807907104]
cabinet_F[0].rotation = [0, 0, -1.5707962831346352]
cabinet_F[0].optimize = 2
cabinet_A[0].position = [1.399999976158142, 7.356249809265137, 0.44999998807907104]
cabinet_A[0].rotation = [0, 0, -1.5707962831346352]
cabinet_A[0].optimize = 2
refrigerator[0].position = [0.5, 7.30625057220459, 0.925000011920929]
refrigerator[0].rotation = [0, 0, -1.5707962828468343]
refrigerator[0].optimize = 2
chair_J[0].position = [4.650000095367432, 5.599999904632568, 0.42500001192092896]
chair_J[0].rotation = [0, 0, -3.094468692304118]
chair_J[0].optimize = 2
can[0].position = [3.700000047683716, 7.621250152587891, 0.9599999785423279]
can[0].rotation = [0, 0, -1.5707962775842157]
can[0].optimize = 2
box[0].position = [2.200000047683716, 7.53125, 1.0]
box[0].rotation = [0, 0, -1.5707962774711683]
box[0].optimize = 2
cup_C[0].position = [1.7999999523162842, 1.649999976158142, 0.4699999988079071]
cup_C[0].rotation = [0, 0, 0.025132745679198647]
cup_C[0].optimize = 2
chair_B[0].position = [1.899999976158142, 4.25, 0.42500001192092896]
chair_B[0].rotation = [0, 0, 1.6179202626409217]
chair_B[0].optimize = 2
cabinet_B[0].position = [4.599999904632568, 7.481249809265137, 0.3499999940395355]
cabinet_B[0].rotation = [0, 0, -1.5707962843572905]
cabinet_B[0].optimize = 2
backpack[0].position = [5.5, 7.556249618530273, 0.9249999523162842]
backpack[0].rotation = [0, 0, -1.5707962780041536]
backpack[0].optimize = 2
cabinet_C[0].position = [2.200000047683716, 7.356250286102295, 0.44999998807907104]
cabinet_C[0].rotation = [0, 0, -1.570796283845389]
cabinet_C[0].optimize = 2
cabinet_D[0].position = [5.5, 7.481249809265137, 0.3499999940395355]
cabinet_D[0].rotation = [0, 0, -1.5707962843572905]
cabinet_D[0].optimize = 2
chair_G[0].position = [2.8499999046325684, 1.649999976158142, 0.42500001192092896]
chair_G[0].rotation = [0, 0, -3.1290262823329655]
chair_G[0].optimize = 2
kettle[0].position = [1.399999976158142, 7.566250324249268, 1.024999976158142]
kettle[0].rotation = [0, 0, -1.5707962775842157]
kettle[0].optimize = 2
chair_K[0].position = [4.650000095367432, 4.900000095367432, 0.42500001192092896]
chair_K[0].rotation = [0, 0, -3.094468692304118]
chair_K[0].optimize = 2
table_A[0].position = [1.899999976158142, 5.449999809265137, 0.375]
table_A[0].rotation = [0, 0, 0.04712389191905141]
table_A[0].optimize = 2
couch_C[0].position = [0.42500001192092896, 5.349999904632568, 0.4099999964237213]
couch_C[0].rotation = [0, 0, 3.4741276547927364e-08]
couch_C[0].optimize = 2
stool[0].position = [1.7999999523162842, 2.700000047683716, 0.22499999403953552]
stool[0].rotation = [0, 0, -1.5582299555380688]
stool[0].optimize = 2
chair_E[0].position = [3.6500000953674316, 6.150000095367432, 0.42500001192092896]
chair_E[0].rotation = [0, 0, -1.5236724810703668]
chair_E[0].optimize = 2
chair_H[0].position = [3.6500000953674316, 3.6500000953674316, 0.42500001192092896]
chair_H[0].rotation = [0, 0, 1.6179202626409217]
chair_H[0].optimize = 2
couch_A[0].position = [0.42500001192092896, 1.600000023841858, 0.4099999964237213]
couch_A[0].rotation = [0, 0, 3.4741276547927364e-08]
couch_A[0].optimize = 2
chair_D[0].position = [2.8499999046325684, 5.800000190734863, 0.42500001192092896]
chair_D[0].rotation = [0, 0, -3.0944686726830053]
chair_D[0].optimize = 2
cup_B[0].position = [3.6500000953674316, 5.485370635986328, 0.800000011920929]
cup_B[0].rotation = [0, 0, 0.018849557077629343]
cup_B[0].optimize = 2
chair_A[0].position = [1.899999976158142, 6.650000095367432, 0.42500001192092896]
chair_A[0].rotation = [0, 0, -1.5236724810703668]
chair_A[0].optimize = 2
cabinet_E[0].position = [0.22500000894069672, 3.4800000190734863, 0.42500001192092896]
cabinet_E[0].rotation = [0, 0, 3.915819301431072e-08]
cabinet_E[0].optimize = 2

