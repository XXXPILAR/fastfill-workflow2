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
cabinet_A = Assets(description="cabinet", size=[0.60, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="chair", size=[0.55, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
table_A = Assets(description="table", size=[0.90, 1.80, 0.75], placements=[AssetInstance() for _ in range(1)])
basket = Assets(description="basket", size=[0.30, 0.40, 0.25], placements=[AssetInstance() for _ in range(1)])
table_B = Assets(description="table", size=[0.60, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.55, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
refrigerator = Assets(description="refrigerator", size=[0.75, 0.91, 1.80], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.35, 0.80, 0.70], placements=[AssetInstance() for _ in range(1)])
cabinet_C = Assets(description="cabinet", size=[0.60, 1.00, 0.90], placements=[AssetInstance() for _ in range(1)])
cup_A = Assets(description="cup", size=[0.09, 0.09, 0.10], placements=[AssetInstance() for _ in range(1)])
backpack = Assets(description="backpack", size=[0.20, 0.32, 0.45], placements=[AssetInstance() for _ in range(1)])
cabinet_D = Assets(description="cabinet", size=[0.35, 0.80, 0.70], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="chair", size=[0.55, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
cabinet_E = Assets(description="cabinet", size=[0.60, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
chair_D = Assets(description="chair", size=[0.55, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
chair_E = Assets(description="chair", size=[0.55, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
dishwasher = Assets(description="dishwasher", size=[0.60, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
chair_F = Assets(description="chair", size=[0.55, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
chair_G = Assets(description="chair", size=[0.55, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
couch_A = Assets(description="couch", size=[0.90, 2.10, 0.85], placements=[AssetInstance() for _ in range(1)])
chair_H = Assets(description="chair", size=[0.55, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
kettle = Assets(description="kettle", size=[0.18, 0.22, 0.25], placements=[AssetInstance() for _ in range(1)])
can = Assets(description="can", size=[0.07, 0.07, 0.12], placements=[AssetInstance() for _ in range(1)])
box = Assets(description="box", size=[0.30, 0.40, 0.25], placements=[AssetInstance() for _ in range(1)])
chair_I = Assets(description="chair", size=[0.55, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
table_C = Assets(description="table", size=[0.60, 1.10, 0.45], placements=[AssetInstance() for _ in range(1)])
stool = Assets(description="stool", size=[0.40, 0.40, 0.65], placements=[AssetInstance() for _ in range(1)])
couch_B = Assets(description="couch", size=[0.88, 1.80, 0.84], placements=[AssetInstance() for _ in range(1)])
cup_B = Assets(description="cup", size=[0.09, 0.09, 0.10], placements=[AssetInstance() for _ in range(1)])
chair_J = Assets(description="chair", size=[0.55, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
cabinet_F = Assets(description="cabinet", size=[0.45, 1.50, 0.80], placements=[AssetInstance() for _ in range(1)])
chair_K = Assets(description="chair", size=[0.55, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
cup_C = Assets(description="cup", size=[0.09, 0.09, 0.10], placements=[AssetInstance() for _ in range(1)])
couch_C = Assets(description="couch", size=[0.95, 2.20, 0.86], placements=[AssetInstance() for _ in range(1)])

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

cabinet_A[0].position = [4.522294180990765, 5.544126299564766, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
chair_A[0].position = [1.7166958396008896, 0.7542907715111914, 0.425]
chair_A[0].rotation = [0, 0, 0]
table_A[0].position = [0.7765751801797732, 4.040660561395456, 0.375]
table_A[0].rotation = [0, 0, 0]
basket[0].position = [3.8085233297890184, 2.2984626261361076, 0.125]
basket[0].rotation = [0, 0, 0]
table_B[0].position = [3.6598566340260636, 2.3316750290524904, 0.375]
table_B[0].rotation = [0, 0, 0]
chair_B[0].position = [0.846918303444537, 3.7997737246907586, 0.425]
chair_B[0].rotation = [0, 0, 0]
refrigerator[0].position = [3.0301018277923335, 4.841496392042854, 0.9]
refrigerator[0].rotation = [0, 0, 0]
cabinet_B[0].position = [4.6389207422968175, 1.8331882976253693, 0.35]
cabinet_B[0].rotation = [0, 0, 0]
cabinet_C[0].position = [2.2492531070272026, 2.876744530991784, 0.45]
cabinet_C[0].rotation = [0, 0, 0]
cup_A[0].position = [3.900125114676885, 4.661383329808636, 0.05]
cup_A[0].rotation = [0, 0, 0]
backpack[0].position = [5.4454487951948245, 6.63900828021262, 0.225]
backpack[0].rotation = [0, 0, 0]
cabinet_D[0].position = [4.6186870322781415, 6.895619631716159, 0.35]
cabinet_D[0].rotation = [0, 0, 0]
chair_C[0].position = [4.402347767601656, 3.4041543024381054, 0.425]
chair_C[0].rotation = [0, 0, 0]
cabinet_E[0].position = [5.944355395549926, 7.2435790976178245, 0.45]
cabinet_E[0].rotation = [0, 0, 0]
chair_D[0].position = [5.3841412693040365, 0.8907656485812656, 0.425]
chair_D[0].rotation = [0, 0, 0]
chair_E[0].position = [1.3991165624141175, 0.6812505461997861, 0.425]
chair_E[0].rotation = [0, 0, 0]
dishwasher[0].position = [0.4729376660027339, 7.276043581784075, 0.425]
dishwasher[0].rotation = [0, 0, 0]
chair_F[0].position = [5.587254123105734, 3.275975178946245, 0.425]
chair_F[0].rotation = [0, 0, 0]
chair_G[0].position = [2.0060660537157093, 1.9702170406969028, 0.425]
chair_G[0].rotation = [0, 0, 0]
couch_A[0].position = [1.2458074520270834, 4.416239667105372, 0.425]
couch_A[0].rotation = [0, 0, 0]
chair_H[0].position = [4.281420518383663, 7.6219220633576334, 0.425]
chair_H[0].rotation = [0, 0, 0]
kettle[0].position = [1.1135323518179716, 6.142151234675228, 0.125]
kettle[0].rotation = [0, 0, 0]
can[0].position = [2.5434136101714575, 0.7785540318529341, 0.06]
can[0].rotation = [0, 0, 0]
box[0].position = [0.718029437516584, 3.7126901709995423, 0.125]
box[0].rotation = [0, 0, 0]
chair_I[0].position = [5.028592431914271, 0.46793909290333346, 0.425]
chair_I[0].rotation = [0, 0, 0]
table_C[0].position = [6.3933888985050285, 2.873384000341086, 0.225]
table_C[0].rotation = [0, 0, 0]
stool[0].position = [6.122173187656205, 7.629614608922548, 0.325]
stool[0].rotation = [0, 0, 0]
couch_B[0].position = [3.704324955558467, 6.748314035416335, 0.42]
couch_B[0].rotation = [0, 0, 0]
cup_B[0].position = [2.7299084768239172, 6.418780884851668, 0.05]
cup_B[0].rotation = [0, 0, 0]
chair_J[0].position = [3.983123108296856, 2.1408804461808617, 0.425]
chair_J[0].rotation = [0, 0, 0]
cabinet_F[0].position = [5.95165084306175, 6.729436652670117, 0.4]
cabinet_F[0].rotation = [0, 0, 0]
chair_K[0].position = [4.8623142225629294, 3.0019613484956755, 0.425]
chair_K[0].rotation = [0, 0, 0]
cup_C[0].position = [2.65952231578999, 4.511341385088323, 0.05]
cup_C[0].rotation = [0, 0, 0]
couch_C[0].position = [3.058492712461447, 5.84292095965986, 0.43]
couch_C[0].rotation = [0, 0, 0]
cabinet_A[0].position = [4.522294180990765, 5.544126299564766, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
chair_A[0].position = [1.7166958396008896, 0.7542907715111914, 0.425]
chair_A[0].rotation = [0, 0, 0]
table_A[0].position = [0.7765751801797732, 4.040660561395456, 0.375]
table_A[0].rotation = [0, 0, 0]
basket[0].position = [3.8085233297890184, 2.2984626261361076, 0.125]
basket[0].rotation = [0, 0, 0]
table_B[0].position = [3.6598566340260636, 2.3316750290524904, 0.375]
table_B[0].rotation = [0, 0, 0]
chair_B[0].position = [0.846918303444537, 3.7997737246907586, 0.425]
chair_B[0].rotation = [0, 0, 0]
refrigerator[0].position = [3.0301018277923335, 4.841496392042854, 0.9]
refrigerator[0].rotation = [0, 0, 0]
cabinet_B[0].position = [4.6389207422968175, 1.8331882976253693, 0.35]
cabinet_B[0].rotation = [0, 0, 0]
cabinet_C[0].position = [2.2492531070272026, 2.876744530991784, 0.45]
cabinet_C[0].rotation = [0, 0, 0]
cup_A[0].position = [3.900125114676885, 4.661383329808636, 0.05]
cup_A[0].rotation = [0, 0, 0]
backpack[0].position = [5.4454487951948245, 6.63900828021262, 0.225]
backpack[0].rotation = [0, 0, 0]
cabinet_D[0].position = [4.6186870322781415, 6.895619631716159, 0.35]
cabinet_D[0].rotation = [0, 0, 0]
chair_C[0].position = [4.402347767601656, 3.4041543024381054, 0.425]
chair_C[0].rotation = [0, 0, 0]
cabinet_E[0].position = [5.944355395549926, 7.2435790976178245, 0.45]
cabinet_E[0].rotation = [0, 0, 0]
chair_D[0].position = [5.3841412693040365, 0.8907656485812656, 0.425]
chair_D[0].rotation = [0, 0, 0]
chair_E[0].position = [1.3991165624141175, 0.6812505461997861, 0.425]
chair_E[0].rotation = [0, 0, 0]
dishwasher[0].position = [0.4729376660027339, 7.276043581784075, 0.425]
dishwasher[0].rotation = [0, 0, 0]
chair_F[0].position = [5.587254123105734, 3.275975178946245, 0.425]
chair_F[0].rotation = [0, 0, 0]
chair_G[0].position = [2.0060660537157093, 1.9702170406969028, 0.425]
chair_G[0].rotation = [0, 0, 0]
couch_A[0].position = [1.2458074520270834, 4.416239667105372, 0.425]
couch_A[0].rotation = [0, 0, 0]
chair_H[0].position = [4.281420518383663, 7.6219220633576334, 0.425]
chair_H[0].rotation = [0, 0, 0]
kettle[0].position = [1.1135323518179716, 6.142151234675228, 0.125]
kettle[0].rotation = [0, 0, 0]
can[0].position = [2.5434136101714575, 0.7785540318529341, 0.06]
can[0].rotation = [0, 0, 0]
box[0].position = [0.718029437516584, 3.7126901709995423, 0.125]
box[0].rotation = [0, 0, 0]
chair_I[0].position = [5.028592431914271, 0.46793909290333346, 0.425]
chair_I[0].rotation = [0, 0, 0]
table_C[0].position = [6.3933888985050285, 2.873384000341086, 0.225]
table_C[0].rotation = [0, 0, 0]
stool[0].position = [6.122173187656205, 7.629614608922548, 0.325]
stool[0].rotation = [0, 0, 0]
couch_B[0].position = [3.704324955558467, 6.748314035416335, 0.42]
couch_B[0].rotation = [0, 0, 0]
cup_B[0].position = [2.7299084768239172, 6.418780884851668, 0.05]
cup_B[0].rotation = [0, 0, 0]
chair_J[0].position = [3.983123108296856, 2.1408804461808617, 0.425]
chair_J[0].rotation = [0, 0, 0]
cabinet_F[0].position = [5.95165084306175, 6.729436652670117, 0.4]
cabinet_F[0].rotation = [0, 0, 0]
chair_K[0].position = [4.8623142225629294, 3.0019613484956755, 0.425]
chair_K[0].rotation = [0, 0, 0]
cup_C[0].position = [2.65952231578999, 4.511341385088323, 0.05]
cup_C[0].rotation = [0, 0, 0]
couch_C[0].position = [3.058492712461447, 5.84292095965986, 0.43]
couch_C[0].rotation = [0, 0, 0]

solver.constraints = []

# The room is divided into three functional areas:
# - kitchen storage and appliances along the top and upper-left walls,
# - dining furniture in the upper-middle area,
# - living furniture in the lower half.
# The strip next to the right wall is intentionally left open for both doors,
# and the lower-left fireplace footprint is also kept clear.

# Asset identifiers referenced by the criteria map as follows:
# o0013 = cabinet_E, o0017 = chair_F, o0024 = chair_I,
# o0029 = chair_J, and o0031 = chair_K.

# Fixed reference points used to preserve the intended furniture groupings.
dining_table_A_center = AssetInstance(position=[2.15, 5.60, 0.375])
dining_table_B_center = AssetInstance(position=[4.35, 5.65, 0.375])
coffee_table_center = AssetInstance(position=[2.30, 2.00, 0.225])

# Initial placements ---------------------------------------------------------

# Kitchen cabinetry and appliances.
refrigerator[0].position = [0.55, 7.205, 0.90]
refrigerator[0].rotation = [0, 0, radians(-90)]

cabinet_A[0].position = [1.65, 7.36, 0.45]
cabinet_A[0].rotation = [0, 0, radians(-90)]

cabinet_E[0].position = [2.90, 7.36, 0.45]
cabinet_E[0].rotation = [0, 0, radians(-90)]

cabinet_C[0].position = [4.05, 7.36, 0.45]
cabinet_C[0].rotation = [0, 0, radians(-90)]

dishwasher[0].position = [4.90, 7.36, 0.425]
dishwasher[0].rotation = [0, 0, radians(-90)]

cabinet_F[0].position = [0.225, 5.85, 0.40]
cabinet_F[0].rotation = [0, 0, radians(0)]

cabinet_B[0].position = [0.175, 4.55, 0.35]
cabinet_B[0].rotation = [0, 0, radians(0)]

cabinet_D[0].position = [0.175, 3.55, 0.35]
cabinet_D[0].rotation = [0, 0, radians(0)]

# Dining tables.
table_A[0].position = [2.15, 5.60, 0.375]
table_A[0].rotation = [0, 0, radians(0)]

table_B[0].position = [4.35, 5.65, 0.375]
table_B[0].rotation = [0, 0, radians(90)]

# Four chairs around the main dining table.
chair_A[0].position = [1.28, 5.15, 0.425]
chair_A[0].rotation = [0, 0, radians(0)]

chair_B[0].position = [3.02, 5.15, 0.425]
chair_B[0].rotation = [0, 0, radians(180)]

chair_C[0].position = [1.28, 6.08, 0.425]
chair_C[0].rotation = [0, 0, radians(0)]

chair_D[0].position = [3.02, 6.08, 0.425]
chair_D[0].rotation = [0, 0, radians(180)]

# Seating around the smaller table.
chair_E[0].position = [3.55, 5.05, 0.425]
chair_E[0].rotation = [0, 0, radians(40)]

chair_G[0].position = [4.35, 4.90, 0.425]
chair_G[0].rotation = [0, 0, radians(90)]

chair_H[0].position = [5.18, 5.65, 0.425]
chair_H[0].rotation = [0, 0, radians(180)]

stool[0].position = [4.35, 6.30, 0.325]
stool[0].rotation = [0, 0, radians(-90)]

# Living area. The couches surround the low coffee table while leaving a
# circulation strip between them and the doors on the right wall.
couch_A[0].position = [0.45, 1.90, 0.425]
couch_A[0].rotation = [0, 0, radians(0)]

couch_B[0].position = [3.30, 0.44, 0.42]
couch_B[0].rotation = [0, 0, radians(90)]

couch_C[0].position = [4.88, 2.85, 0.43]
couch_C[0].rotation = [0, 0, radians(180)]

table_C[0].position = [2.30, 2.00, 0.225]
table_C[0].rotation = [0, 0, radians(90)]

# Required chair relationship: chair_K is centered between chair_J and
# chair_F. All three face generally toward the living-room coffee table.
chair_J[0].position = [2.25, 3.55, 0.425]
chair_J[0].rotation = [0, 0, radians(-90)]

chair_K[0].position = [2.85, 3.55, 0.425]
chair_K[0].rotation = [0, 0, radians(-90)]

chair_F[0].position = [3.45, 3.55, 0.425]
chair_F[0].rotation = [0, 0, radians(-90)]

# The requested 0.30 m center-distance condition is used here exactly.
# Since this is smaller than the chairs' horizontal dimensions, it is the
# highest-priority semantic constraint and may require the feasibility solver
# to make the smallest possible local adjustment.
chair_I[0].position = [3.45, 3.85, 0.425]
chair_I[0].rotation = [0, 0, radians(99)]

# Floor accessories are kept beside furniture and outside circulation paths.
basket[0].position = [1.08, 3.55, 0.125]
basket[0].rotation = [0, 0, radians(0)]

backpack[0].position = [0.85, 4.48, 0.225]
backpack[0].rotation = [0, 0, radians(15)]

box[0].position = [5.05, 4.45, 0.125]
box[0].rotation = [0, 0, radians(0)]

# Small objects are initialized on the tops of their supporting tables.
cup_A[0].position = [2.00, 5.35, 0.80]
cup_A[0].rotation = [0, 0, radians(0)]

cup_C[0].position = [2.25, 5.85, 0.80]
cup_C[0].rotation = [0, 0, radians(0)]

kettle[0].position = [4.15, 5.65, 0.875]
kettle[0].rotation = [0, 0, radians(90)]

can[0].position = [4.55, 5.65, 0.81]
can[0].rotation = [0, 0, radians(0)]

cup_B[0].position = [2.30, 2.00, 0.50]
cup_B[0].rotation = [0, 0, radians(0)]


# Constraints ---------------------------------------------------------------
# Important explicit layout criteria are declared first so they take priority.

# chair_K (o0031) remains halfway between chair_J (o0029) and chair_F
# (o0017): both neighboring center distances are equal.
solver.distance_constraint(
    chair_K[0], chair_J[0], 0.60, 0.60, weight=10
)
solver.distance_constraint(
    chair_K[0], chair_F[0], 0.60, 0.60, weight=10
)

# chair_I (o0024) must remain within 0.30 m of chair_F (o0017), and its
# front must face cabinet_E (o0013).
solver.distance_constraint(
    chair_I[0], chair_F[0], None, 0.30, weight=10
)
solver.point_towards(chair_I[0], cabinet_E[0])

# Wall-mounted kitchen pieces. These calls provide their position-based
# constraints; alignment references preserve their inward-facing rotations.
solver.against_wall(refrigerator[0], walls[6])
solver.align_with(
    refrigerator[0],
    AssetInstance(rotation=[0, 0, radians(-90)])
)

solver.against_wall(cabinet_A[0], walls[6])
solver.align_with(
    cabinet_A[0],
    AssetInstance(rotation=[0, 0, radians(-90)])
)

solver.against_wall(cabinet_E[0], walls[6])
solver.align_with(
    cabinet_E[0],
    AssetInstance(rotation=[0, 0, radians(-90)])
)

solver.against_wall(cabinet_C[0], walls[6])
solver.align_with(
    cabinet_C[0],
    AssetInstance(rotation=[0, 0, radians(-90)])
)

solver.against_wall(dishwasher[0], walls[6])
solver.align_with(
    dishwasher[0],
    AssetInstance(rotation=[0, 0, radians(-90)])
)

solver.against_wall(cabinet_F[0], walls[0])
solver.align_with(
    cabinet_F[0],
    AssetInstance(rotation=[0, 0, radians(0)])
)

solver.against_wall(cabinet_B[0], walls[0])
solver.align_with(
    cabinet_B[0],
    AssetInstance(rotation=[0, 0, radians(0)])
)

solver.against_wall(cabinet_D[0], walls[0])
solver.align_with(
    cabinet_D[0],
    AssetInstance(rotation=[0, 0, radians(0)])
)

# Preserve the tables' functional locations and orientations.
solver.distance_constraint(
    table_A[0], dining_table_A_center, 0, 0, weight=10
)
solver.align_with(
    table_A[0],
    AssetInstance(rotation=[0, 0, radians(0)])
)

solver.distance_constraint(
    table_B[0], dining_table_B_center, 0, 0, weight=10
)
solver.align_with(
    table_B[0],
    AssetInstance(rotation=[0, 0, radians(90)])
)

solver.distance_constraint(
    table_C[0], coffee_table_center, 0, 0, weight=10
)
solver.align_with(
    table_C[0],
    AssetInstance(rotation=[0, 0, radians(90)])
)

# Main dining chairs stay near and face the large dining table.
solver.distance_constraint(chair_A[0], table_A[0], 0.85, 1.05)
solver.point_towards(chair_A[0], table_A[0])

solver.distance_constraint(chair_B[0], table_A[0], 0.85, 1.05)
solver.point_towards(chair_B[0], table_A[0])

solver.distance_constraint(chair_C[0], table_A[0], 0.85, 1.05)
solver.point_towards(chair_C[0], table_A[0])

solver.distance_constraint(chair_D[0], table_A[0], 0.85, 1.05)
solver.point_towards(chair_D[0], table_A[0])

# Secondary dining chairs and stool stay near and face the smaller table.
solver.distance_constraint(chair_E[0], table_B[0], 0.80, 1.10)
solver.point_towards(chair_E[0], table_B[0])

solver.distance_constraint(chair_G[0], table_B[0], 0.70, 1.00)
solver.point_towards(chair_G[0], table_B[0])

solver.distance_constraint(chair_H[0], table_B[0], 0.75, 1.05)
solver.point_towards(chair_H[0], table_B[0])

solver.distance_constraint(stool[0], table_B[0], 0.60, 0.90)
solver.point_towards(stool[0], table_B[0])

# Living-room seating remains grouped around and oriented toward table_C.
solver.distance_constraint(couch_A[0], table_C[0], 1.20, 2.20)
solver.point_towards(couch_A[0], table_C[0])

solver.distance_constraint(couch_B[0], table_C[0], 1.20, 2.20)
solver.point_towards(couch_B[0], table_C[0])

solver.distance_constraint(couch_C[0], table_C[0], 2.00, 3.20)
solver.point_towards(couch_C[0], table_C[0])

solver.distance_constraint(chair_J[0], table_C[0], 1.30, 1.80)
solver.point_towards(chair_J[0], table_C[0])

solver.distance_constraint(chair_K[0], table_C[0], 1.30, 1.90)
solver.point_towards(chair_K[0], table_C[0])

solver.distance_constraint(chair_F[0], table_C[0], 1.60, 2.20)
solver.point_towards(chair_F[0], table_C[0])

# Pin the required chair grouping to its intended open part of the room.
solver.distance_constraint(
    chair_J[0],
    AssetInstance(position=[2.25, 3.55, 0.425]),
    0, 0, weight=10
)
solver.distance_constraint(
    chair_F[0],
    AssetInstance(position=[3.45, 3.55, 0.425]),
    0, 0, weight=10
)

# Floor accessories receive both position and orientation constraints.
solver.distance_constraint(
    basket[0],
    AssetInstance(position=[1.08, 3.55, 0.125]),
    0, 0, weight=10
)
solver.align_with(
    basket[0],
    AssetInstance(rotation=[0, 0, radians(0)])
)

solver.distance_constraint(
    backpack[0],
    AssetInstance(position=[0.85, 4.48, 0.225]),
    0, 0, weight=10
)
solver.align_with(
    backpack[0],
    AssetInstance(rotation=[0, 0, radians(15)])
)

solver.distance_constraint(
    box[0],
    AssetInstance(position=[5.05, 4.45, 0.125]),
    0, 0, weight=10
)
solver.align_with(
    box[0],
    AssetInstance(rotation=[0, 0, radians(0)])
)

# Small tabletop objects must remain on their supporting surfaces. Exact
# horizontal anchors prevent multiple objects on one table from overlapping.
solver.on_top_of(cup_A[0], table_A[0])
solver.distance_constraint(
    cup_A[0],
    AssetInstance(position=[2.00, 5.35, 0.80]),
    0, 0, weight=10
)
solver.align_with(
    cup_A[0],
    AssetInstance(rotation=[0, 0, radians(0)])
)

solver.on_top_of(cup_C[0], table_A[0])
solver.distance_constraint(
    cup_C[0],
    AssetInstance(position=[2.25, 5.85, 0.80]),
    0, 0, weight=10
)
solver.align_with(
    cup_C[0],
    AssetInstance(rotation=[0, 0, radians(0)])
)

solver.on_top_of(kettle[0], table_B[0])
solver.distance_constraint(
    kettle[0],
    AssetInstance(position=[4.15, 5.65, 0.875]),
    0, 0, weight=10
)
solver.align_with(
    kettle[0],
    AssetInstance(rotation=[0, 0, radians(90)])
)

solver.on_top_of(can[0], table_B[0])
solver.distance_constraint(
    can[0],
    AssetInstance(position=[4.55, 5.65, 0.81]),
    0, 0, weight=10
)
solver.align_with(
    can[0],
    AssetInstance(rotation=[0, 0, radians(0)])
)

solver.on_top_of(cup_B[0], table_C[0])
solver.distance_constraint(
    cup_B[0],
    AssetInstance(position=[2.30, 2.00, 0.50]),
    0, 0, weight=10
)
solver.align_with(
    cup_B[0],
    AssetInstance(rotation=[0, 0, radians(0)])
)

solver.constraints = []
table_B[0].position = [4.349999904632568, 5.650000095367432, 0.375]
table_B[0].rotation = [0, 0, 1.6116370324823435]
table_B[0].optimize = 2
basket[0].position = [1.0800000429153442, 3.549999952316284, 0.125]
basket[0].rotation = [0, 0, 0.00942477746072377]
basket[0].optimize = 2
chair_F[0].position = [3.450000047683716, 3.549999952316284, 0.42500001192092896]
chair_F[0].rotation = [0, 0, -1.8934535021778647]
chair_F[0].optimize = 2
cabinet_B[0].position = [0.1750013679265976, 4.550000190734863, 0.3499999940395355]
cabinet_B[0].rotation = [0, 0, -2.0565179704693133e-05]
cabinet_B[0].optimize = 2
chair_E[0].position = [3.549999952316284, 5.050000190734863, 0.42500001192092896]
chair_E[0].rotation = [0, 0, 0.7075564902324459]
chair_E[0].optimize = 2
backpack[0].position = [0.8500000238418579, 4.480000019073486, 0.22499999403953552]
backpack[0].rotation = [0, 0, 0.27122416455253917]
backpack[0].optimize = 2
table_C[0].position = [2.299999952316284, 2.0, 0.22499999403953552]
table_C[0].rotation = [0, 0, 1.6210618064797564]
table_C[0].optimize = 2
can[0].position = [4.550000190734863, 5.650000095367432, 0.8100000023841858]
can[0].rotation = [0, 0, 0.01256637125682779]
can[0].optimize = 2
chair_A[0].position = [1.2799999713897705, 5.150000095367432, 0.42500001192092896]
chair_A[0].rotation = [0, 0, 0.00942477746072377]
chair_A[0].optimize = 2
box[0].position = [5.050000190734863, 4.449999809265137, 0.125]
box[0].rotation = [0, 0, 0.00942477746072377]
box[0].optimize = 2
cabinet_C[0].position = [4.050000190734863, 7.356231689453125, 0.44999998807907104]
cabinet_C[0].rotation = [0, 0, -1.570816625693004]
cabinet_C[0].optimize = 2
chair_K[0].position = [2.8499999046325684, 3.549999952316284, 0.42500001192092896]
chair_K[0].rotation = [0, 0, -1.5651448480627257]
chair_K[0].optimize = 2
chair_H[0].position = [5.179999828338623, 5.650000095367432, 0.42500001192092896]
chair_H[0].rotation = [0, 0, -3.1321678761290697]
chair_H[0].optimize = 2
refrigerator[0].position = [0.550000011920929, 7.281186103820801, 0.8999999761581421]
refrigerator[0].rotation = [0, 0, -1.570819201308096]
refrigerator[0].optimize = 2
cup_A[0].position = [2.0, 5.349999904632568, 0.800000011920929]
cup_A[0].rotation = [0, 0, 0.01256637125682779]
cup_A[0].optimize = 2
couch_B[0].position = [3.299999952316284, 0.6753599643707275, 0.41999998688697815]
couch_B[0].rotation = [0, 0, 1.8558870559866674]
couch_B[0].optimize = 2
cabinet_E[0].position = [2.9000000953674316, 7.356232166290283, 0.44999998807907104]
cabinet_E[0].rotation = [0, 0, -1.5708179256333599]
cabinet_E[0].optimize = 2
kettle[0].position = [4.150000095367432, 5.650000095367432, 0.875]
kettle[0].rotation = [0, 0, 1.5833626980517244]
kettle[0].optimize = 2
chair_G[0].position = [4.349999904632568, 4.900000095367432, 0.42500001192092896]
chair_G[0].rotation = [0, 0, 1.5802211042556205]
chair_G[0].optimize = 2
couch_C[0].position = [4.880000114440918, 2.8499999046325684, 0.4300000071525574]
couch_C[0].rotation = [0, 0, -2.9556446154574174]
couch_C[0].optimize = 2
stool[0].position = [4.349999904632568, 6.300000190734863, 0.32499998807907104]
stool[0].rotation = [0, 0, -1.5613715493341729]
stool[0].optimize = 2
chair_D[0].position = [3.0199999809265137, 6.079999923706055, 0.42500001192092896]
chair_D[0].rotation = [0, 0, -3.1321678761290697]
chair_D[0].optimize = 2
cup_C[0].position = [2.25, 5.849999904632568, 0.800000011920929]
cup_C[0].rotation = [0, 0, 0.01256637125682779]
cup_C[0].optimize = 2
chair_C[0].position = [1.2799999713897705, 6.079999923706055, 0.42500001192092896]
chair_C[0].rotation = [0, 0, 0.00942477746072377]
chair_C[0].optimize = 2
cabinet_F[0].position = [0.22497834265232086, 5.849999904632568, 0.4000000059604645]
cabinet_F[0].rotation = [0, 0, -2.056904442394828e-05]
cabinet_F[0].optimize = 2
couch_A[0].position = [0.44999998807907104, 1.899999976158142, 0.42500001192092896]
couch_A[0].rotation = [0, 0, 0.00942477746072377]
couch_A[0].optimize = 2
table_A[0].position = [2.1500000953674316, 5.599999904632568, 0.375]
table_A[0].rotation = [0, 0, 0.04084070568744688]
table_A[0].optimize = 2
cabinet_D[0].position = [0.1750013679265976, 3.549999952316284, 0.3499999940395355]
cabinet_D[0].rotation = [0, 0, -2.0565179704693133e-05]
cabinet_D[0].optimize = 2
chair_I[0].position = [3.450000047683716, 3.8499999046325684, 0.42500001192092896]
chair_I[0].rotation = [0, 0, 1.7373007423469427]
chair_I[0].optimize = 2
chair_J[0].position = [2.25, 3.549999952316284, 0.42500001192092896]
chair_J[0].rotation = [0, 0, -1.5550883628776802]
chair_J[0].optimize = 2
cup_B[0].position = [2.299999952316284, 2.0, 0.5]
cup_B[0].rotation = [0, 0, 0.01256637125682779]
cup_B[0].optimize = 2
cabinet_A[0].position = [1.649999976158142, 7.356231689453125, 0.44999998807907104]
cabinet_A[0].rotation = [0, 0, -1.570816665290985]
cabinet_A[0].optimize = 2
dishwasher[0].position = [4.900000095367432, 7.356231212615967, 0.42500001192092896]
dishwasher[0].rotation = [0, 0, -1.5708166044123668]
dishwasher[0].optimize = 2
chair_B[0].position = [3.0199999809265137, 5.150000095367432, 0.42500001192092896]
chair_B[0].rotation = [0, 0, -3.1321678761290697]
chair_B[0].optimize = 2

