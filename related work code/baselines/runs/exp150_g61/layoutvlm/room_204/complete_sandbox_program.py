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
    Wall(corner1=[1.56, 13.12, 0.00], corner2=[0.36, 13.12, 0.00]),
    Wall(corner1=[0.36, 13.12, 0.00], corner2=[0.36, 10.63, 0.00]),
    Wall(corner1=[0.36, 10.63, 0.00], corner2=[0.42, 10.63, 0.00]),
    Wall(corner1=[0.42, 10.63, 0.00], corner2=[0.42, 9.36, 0.00]),
    Wall(corner1=[0.42, 9.36, 0.00], corner2=[0.00, 9.36, 0.00]),
    Wall(corner1=[0.00, 9.36, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[5.16, 0.00, 0.00]),
    Wall(corner1=[5.16, 0.00, 0.00], corner2=[5.16, 10.26, 0.00]),
    Wall(corner1=[5.16, 10.26, 0.00], corner2=[1.56, 10.26, 0.00]),
    Wall(corner1=[1.56, 10.26, 0.00], corner2=[1.56, 13.12, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
chair_A = Assets(description="chair", size=[0.80, 0.75, 0.85], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.80, 0.75, 0.85], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="chair", size=[0.80, 0.75, 0.85], placements=[AssetInstance() for _ in range(1)])
ornaments_A = Assets(description="ornaments", size=[0.18, 0.24, 0.32], placements=[AssetInstance() for _ in range(1)])
dining_chair_A = Assets(description="dining chair", size=[0.55, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
ornaments_B = Assets(description="ornaments", size=[0.20, 0.28, 0.25], placements=[AssetInstance() for _ in range(1)])
flowers_A = Assets(description="flowers", size=[0.35, 0.35, 0.50], placements=[AssetInstance() for _ in range(1)])
dining_table = Assets(description="dining table", size=[0.95, 2.00, 0.76], placements=[AssetInstance() for _ in range(1)])
ornaments_C = Assets(description="ornaments", size=[0.18, 0.20, 0.30], placements=[AssetInstance() for _ in range(1)])
wall_cabinet = Assets(description="wall cabinet", size=[0.32, 1.40, 0.65], placements=[AssetInstance() for _ in range(1)])
ornaments_D = Assets(description="ornaments", size=[0.20, 0.30, 0.18], placements=[AssetInstance() for _ in range(1)])
tv_cabinet = Assets(description="tv cabinet", size=[0.45, 1.80, 0.50], placements=[AssetInstance() for _ in range(1)])
flowers_B = Assets(description="flowers", size=[0.28, 0.28, 0.42], placements=[AssetInstance() for _ in range(1)])
dining_chair_B = Assets(description="dining chair", size=[0.55, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
sofa_A = Assets(description="sofa", size=[0.90, 2.10, 0.85], placements=[AssetInstance() for _ in range(1)])
ornaments_E = Assets(description="ornaments", size=[0.24, 0.30, 0.12], placements=[AssetInstance() for _ in range(1)])
chair_D = Assets(description="chair", size=[0.80, 0.75, 0.85], placements=[AssetInstance() for _ in range(1)])
ornaments_F = Assets(description="ornaments", size=[0.18, 0.18, 0.28], placements=[AssetInstance() for _ in range(1)])
side_table_A = Assets(description="side table", size=[0.55, 0.55, 0.55], placements=[AssetInstance() for _ in range(1)])
dining_chair_C = Assets(description="dining chair", size=[0.55, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
flowers_C = Assets(description="flowers", size=[0.30, 0.30, 0.45], placements=[AssetInstance() for _ in range(1)])
flowers_D = Assets(description="flowers", size=[0.32, 0.32, 0.40], placements=[AssetInstance() for _ in range(1)])
desk_lamp_A = Assets(description="desk lamp", size=[0.28, 0.28, 0.50], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[3.20, 2.40, 0.01], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="coffee table", size=[0.65, 1.20, 0.42], placements=[AssetInstance() for _ in range(1)])
sofa_B = Assets(description="sofa", size=[0.90, 1.80, 0.85], placements=[AssetInstance() for _ in range(1)])
desk_lamp_B = Assets(description="desk lamp", size=[0.28, 0.28, 0.50], placements=[AssetInstance() for _ in range(1)])
dining_chair_D = Assets(description="dining chair", size=[0.55, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
dining_chair_E = Assets(description="dining chair", size=[0.55, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
nakadao_station = Assets(description="nakadao station", size=[0.45, 1.20, 0.85], placements=[AssetInstance() for _ in range(1)])
ornaments_G = Assets(description="ornaments", size=[0.20, 0.25, 0.35], placements=[AssetInstance() for _ in range(1)])
dining_chair_F = Assets(description="dining chair", size=[0.55, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
side_table_B = Assets(description="side table", size=[0.50, 0.60, 0.60], placements=[AssetInstance() for _ in range(1)])
ornaments_H = Assets(description="ornaments", size=[0.18, 0.22, 0.27], placements=[AssetInstance() for _ in range(1)])
side_table_C = Assets(description="side table", size=[0.50, 0.60, 0.60], placements=[AssetInstance() for _ in range(1)])

chair_A[0].instance_id = 'chair_A_0'
chair_B[0].instance_id = 'chair_B_0'
chair_C[0].instance_id = 'chair_C_0'
ornaments_A[0].instance_id = 'ornaments_A_0'
dining_chair_A[0].instance_id = 'dining_chair_A_0'
ornaments_B[0].instance_id = 'ornaments_B_0'
flowers_A[0].instance_id = 'flowers_A_0'
dining_table[0].instance_id = 'dining_table_0'
ornaments_C[0].instance_id = 'ornaments_C_0'
wall_cabinet[0].instance_id = 'wall_cabinet_0'
ornaments_D[0].instance_id = 'ornaments_D_0'
tv_cabinet[0].instance_id = 'tv_cabinet_0'
flowers_B[0].instance_id = 'flowers_B_0'
dining_chair_B[0].instance_id = 'dining_chair_B_0'
sofa_A[0].instance_id = 'sofa_A_0'
ornaments_E[0].instance_id = 'ornaments_E_0'
chair_D[0].instance_id = 'chair_D_0'
ornaments_F[0].instance_id = 'ornaments_F_0'
side_table_A[0].instance_id = 'side_table_A_0'
dining_chair_C[0].instance_id = 'dining_chair_C_0'
flowers_C[0].instance_id = 'flowers_C_0'
flowers_D[0].instance_id = 'flowers_D_0'
desk_lamp_A[0].instance_id = 'desk_lamp_A_0'
carpet[0].instance_id = 'carpet_0'
coffee_table[0].instance_id = 'coffee_table_0'
sofa_B[0].instance_id = 'sofa_B_0'
desk_lamp_B[0].instance_id = 'desk_lamp_B_0'
dining_chair_D[0].instance_id = 'dining_chair_D_0'
dining_chair_E[0].instance_id = 'dining_chair_E_0'
nakadao_station[0].instance_id = 'nakadao_station_0'
ornaments_G[0].instance_id = 'ornaments_G_0'
dining_chair_F[0].instance_id = 'dining_chair_F_0'
side_table_B[0].instance_id = 'side_table_B_0'
ornaments_H[0].instance_id = 'ornaments_H_0'
side_table_C[0].instance_id = 'side_table_C_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'
walls[8].instance_id = 'walls_8'
walls[9].instance_id = 'walls_9'

chair_A[0].position = [2.772998508892719, 5.512393102329213, 0.425]
chair_A[0].rotation = [0, 0, 0]
chair_B[0].position = [5.152632629347034, 7.454561984437473, 0.425]
chair_B[0].rotation = [0, 0, 0]
chair_C[0].position = [3.839896512923906, 9.356162202604091, 0.425]
chair_C[0].rotation = [0, 0, 0]
ornaments_A[0].position = [1.7954092901908587, 9.652866652830536, 0.16]
ornaments_A[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [0.5462253078787658, 0.4165721144621777, 0.45]
dining_chair_A[0].rotation = [0, 0, 0]
ornaments_B[0].position = [4.108374205841311, 1.285977848987753, 0.125]
ornaments_B[0].rotation = [0, 0, 0]
flowers_A[0].position = [3.8780392493098232, 7.982202878329718, 0.25]
flowers_A[0].rotation = [0, 0, 0]
dining_table[0].position = [3.8224259633293616, 4.447556119416654, 0.38]
dining_table[0].rotation = [0, 0, 0]
ornaments_C[0].position = [5.123289241015644, 1.4769022758544188, 0.15]
ornaments_C[0].rotation = [0, 0, 0]
wall_cabinet[0].position = [0.8994023497503432, 5.939551872235649, 0.325]
wall_cabinet[0].rotation = [0, 0, 0]
ornaments_D[0].position = [3.8853946731829896, 2.307642141020391, 0.09]
ornaments_D[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [0.5221354927906363, 11.56390951666827, 0.25]
tv_cabinet[0].rotation = [0, 0, 0]
flowers_B[0].position = [4.439441597409951, 6.616640885262788, 0.21]
flowers_B[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [4.914141634369972, 6.368133143367564, 0.45]
dining_chair_B[0].rotation = [0, 0, 0]
sofa_A[0].position = [4.473519261061195, 4.376843065294289, 0.425]
sofa_A[0].rotation = [0, 0, 0]
ornaments_E[0].position = [2.7288868018605505, 9.869048259613091, 0.06]
ornaments_E[0].rotation = [0, 0, 0]
chair_D[0].position = [3.3523493542823566, 9.390130311327328, 0.425]
chair_D[0].rotation = [0, 0, 0]
ornaments_F[0].position = [2.323644864785533, 2.3822035527253744, 0.14]
ornaments_F[0].rotation = [0, 0, 0]
side_table_A[0].position = [2.2557399650254193, 3.4815626224371026, 0.275]
side_table_A[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [2.9403568850489563, 6.275985870507012, 0.45]
dining_chair_C[0].rotation = [0, 0, 0]
flowers_C[0].position = [2.799392947667047, 6.66834125909259, 0.225]
flowers_C[0].rotation = [0, 0, 0]
flowers_D[0].position = [2.867545745117949, 2.1862727101607176, 0.2]
flowers_D[0].rotation = [0, 0, 0]
desk_lamp_A[0].position = [3.2916343511866155, 5.631072700677707, 0.25]
desk_lamp_A[0].rotation = [0, 0, 0]
carpet[0].position = [0.3383043901030136, 7.158224686003175, 0.0075]
carpet[0].rotation = [0, 0, 0]
coffee_table[0].position = [4.284148810343772, 3.9216281173109406, 0.21]
coffee_table[0].rotation = [0, 0, 0]
sofa_B[0].position = [0.7721952563548672, 1.1747270085308306, 0.425]
sofa_B[0].rotation = [0, 0, 0]
desk_lamp_B[0].position = [3.672103130791748, 8.648596657301034, 0.25]
desk_lamp_B[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [4.162918759657251, 7.4740898823207, 0.45]
dining_chair_D[0].rotation = [0, 0, 0]
dining_chair_E[0].position = [3.827260758903333, 4.011675216850387, 0.45]
dining_chair_E[0].rotation = [0, 0, 0]
nakadao_station[0].position = [0.37227031608192473, 6.30895007625358, 0.425]
nakadao_station[0].rotation = [0, 0, 0]
ornaments_G[0].position = [2.9160374808718244, 2.4157663957028186, 0.175]
ornaments_G[0].rotation = [0, 0, 0]
dining_chair_F[0].position = [2.1019322597719077, 9.132593123938948, 0.45]
dining_chair_F[0].rotation = [0, 0, 0]
side_table_B[0].position = [3.8896777337882225, 1.8882664756585312, 0.3]
side_table_B[0].rotation = [0, 0, 0]
ornaments_H[0].position = [1.7398810566390837, 8.82588345246092, 0.135]
ornaments_H[0].rotation = [0, 0, 0]
side_table_C[0].position = [2.283403338505459, 4.701381452288203, 0.3]
side_table_C[0].rotation = [0, 0, 0]
chair_A[0].position = [2.772998508892719, 5.512393102329213, 0.425]
chair_A[0].rotation = [0, 0, 0]
chair_B[0].position = [5.152632629347034, 7.454561984437473, 0.425]
chair_B[0].rotation = [0, 0, 0]
chair_C[0].position = [3.839896512923906, 9.356162202604091, 0.425]
chair_C[0].rotation = [0, 0, 0]
ornaments_A[0].position = [1.7954092901908587, 9.652866652830536, 0.16]
ornaments_A[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [0.5462253078787658, 0.4165721144621777, 0.45]
dining_chair_A[0].rotation = [0, 0, 0]
ornaments_B[0].position = [4.108374205841311, 1.285977848987753, 0.125]
ornaments_B[0].rotation = [0, 0, 0]
flowers_A[0].position = [3.8780392493098232, 7.982202878329718, 0.25]
flowers_A[0].rotation = [0, 0, 0]
dining_table[0].position = [3.8224259633293616, 4.447556119416654, 0.38]
dining_table[0].rotation = [0, 0, 0]
ornaments_C[0].position = [5.123289241015644, 1.4769022758544188, 0.15]
ornaments_C[0].rotation = [0, 0, 0]
wall_cabinet[0].position = [0.8994023497503432, 5.939551872235649, 0.325]
wall_cabinet[0].rotation = [0, 0, 0]
ornaments_D[0].position = [3.8853946731829896, 2.307642141020391, 0.09]
ornaments_D[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [0.5221354927906363, 11.56390951666827, 0.25]
tv_cabinet[0].rotation = [0, 0, 0]
flowers_B[0].position = [4.439441597409951, 6.616640885262788, 0.21]
flowers_B[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [4.914141634369972, 6.368133143367564, 0.45]
dining_chair_B[0].rotation = [0, 0, 0]
sofa_A[0].position = [4.473519261061195, 4.376843065294289, 0.425]
sofa_A[0].rotation = [0, 0, 0]
ornaments_E[0].position = [2.7288868018605505, 9.869048259613091, 0.06]
ornaments_E[0].rotation = [0, 0, 0]
chair_D[0].position = [3.3523493542823566, 9.390130311327328, 0.425]
chair_D[0].rotation = [0, 0, 0]
ornaments_F[0].position = [2.323644864785533, 2.3822035527253744, 0.14]
ornaments_F[0].rotation = [0, 0, 0]
side_table_A[0].position = [2.2557399650254193, 3.4815626224371026, 0.275]
side_table_A[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [2.9403568850489563, 6.275985870507012, 0.45]
dining_chair_C[0].rotation = [0, 0, 0]
flowers_C[0].position = [2.799392947667047, 6.66834125909259, 0.225]
flowers_C[0].rotation = [0, 0, 0]
flowers_D[0].position = [2.867545745117949, 2.1862727101607176, 0.2]
flowers_D[0].rotation = [0, 0, 0]
desk_lamp_A[0].position = [3.2916343511866155, 5.631072700677707, 0.25]
desk_lamp_A[0].rotation = [0, 0, 0]
carpet[0].position = [0.3383043901030136, 7.158224686003175, 0.0075]
carpet[0].rotation = [0, 0, 0]
coffee_table[0].position = [4.284148810343772, 3.9216281173109406, 0.21]
coffee_table[0].rotation = [0, 0, 0]
sofa_B[0].position = [0.7721952563548672, 1.1747270085308306, 0.425]
sofa_B[0].rotation = [0, 0, 0]
desk_lamp_B[0].position = [3.672103130791748, 8.648596657301034, 0.25]
desk_lamp_B[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [4.162918759657251, 7.4740898823207, 0.45]
dining_chair_D[0].rotation = [0, 0, 0]
dining_chair_E[0].position = [3.827260758903333, 4.011675216850387, 0.45]
dining_chair_E[0].rotation = [0, 0, 0]
nakadao_station[0].position = [0.37227031608192473, 6.30895007625358, 0.425]
nakadao_station[0].rotation = [0, 0, 0]
ornaments_G[0].position = [2.9160374808718244, 2.4157663957028186, 0.175]
ornaments_G[0].rotation = [0, 0, 0]
dining_chair_F[0].position = [2.1019322597719077, 9.132593123938948, 0.45]
dining_chair_F[0].rotation = [0, 0, 0]
side_table_B[0].position = [3.8896777337882225, 1.8882664756585312, 0.3]
side_table_B[0].rotation = [0, 0, 0]
ornaments_H[0].position = [1.7398810566390837, 8.82588345246092, 0.135]
ornaments_H[0].rotation = [0, 0, 0]
side_table_C[0].position = [2.283403338505459, 4.701381452288203, 0.3]
side_table_C[0].rotation = [0, 0, 0]

solver.constraints = []

from math import atan2

# The long lower portion is the lounge; the upper portion is the dining area.
# Keep the narrow northern vestibule completely empty and preserve access to
# both west-wall doors and the wide northern dining-room door.
#
# The supplied descriptions omit object IDs. Interpret the requested seating
# relationship as sofa_A between chair_A and chair_D, with chair_D facing
# dining_chair_F.

floor_layout = [
    # Asset, center x, center y, center z, heading (degrees).
    (chair_A,         0.65, 0.85, 0.425,   0),
    (sofa_A,          0.65, 2.70, 0.435,   0),
    (chair_D,         0.65, 4.35, 0.435,   0),
    (sofa_B,          3.10, 0.55, 0.425,  90),
    (chair_B,         4.15, 1.85, 0.435, 180),
    (chair_C,         4.15, 3.00, 0.435, 180),
    (coffee_table,    2.45, 2.70, 0.220,   0),
    (carpet,          2.45, 2.70, 0.005,   0),
    (side_table_A,    1.50, 1.10, 0.275,   0),
    (side_table_B,    1.55, 4.25, 0.300,   0),
    (side_table_C,    4.20, 5.90, 0.300,   0),
    (tv_cabinet,      4.935, 4.45, 0.250, 180),

    # This cabinet occupies the solid wall segment between the west doors.
    (wall_cabinet,    0.16, 6.70, 0.325,   0),

    # Six seats, three on each long side of the dining table.
    (dining_table,    2.75, 7.85, 0.380,   0),
    (dining_chair_A,  1.80, 7.15, 0.450,   0),
    (dining_chair_B,  1.80, 7.85, 0.450,   0),
    (dining_chair_C,  1.80, 8.55, 0.450,   0),
    (dining_chair_D,  3.70, 7.15, 0.450, 180),
    (dining_chair_E,  3.70, 7.85, 0.450, 180),
    (dining_chair_F,  3.70, 8.55, 0.450, 180),
    (nakadao_station, 4.935, 9.10, 0.425, 180),
]

for asset_ref, px, py, pz, heading in floor_layout:
    asset_ref[0].position = [px, py, pz]
    asset_ref[0].rotation = [0, 0, radians(heading)]

# Aim the requested lounge chair at the actual dining-chair position.
chair_D[0].rotation = [
    0, 0,
    atan2(
        dining_chair_F[0].position[1] - chair_D[0].position[1],
        dining_chair_F[0].position[0] - chair_D[0].position[0],
    ),
]

# Small objects are distributed over real supporting surfaces, with enough
# separation between their footprints. Heights are support top + half height.
surface_layout = [
    (ornaments_A, dining_table, 2.75, 7.15, 0),
    (flowers_A,   dining_table, 2.75, 7.85, 0),
    (ornaments_B, dining_table, 2.75, 8.55, 0),

    (flowers_B,   wall_cabinet, 0.16, 6.30, 0),
    (ornaments_C, wall_cabinet, 0.16, 6.90, 0),
    (ornaments_D, wall_cabinet, 0.16, 7.20, 0),

    (flowers_C,   tv_cabinet, 4.935, 4.00, 180),
    (ornaments_E, tv_cabinet, 4.935, 4.60, 180),
    (ornaments_F, tv_cabinet, 4.935, 5.05, 180),

    (desk_lamp_A, side_table_A, 1.50, 1.10, 90),
    (desk_lamp_B, side_table_B, 1.55, 4.25, 270),
    (flowers_D,   side_table_C, 4.20, 5.90, 0),

    (ornaments_G, coffee_table, 2.45, 2.40, 0),
    (ornaments_H, coffee_table, 2.45, 3.00, 0),
]

for item_ref, support_ref, px, py, heading in surface_layout:
    support_top = support_ref[0].position[2] + support_ref.size[2] / 2
    item_ref[0].position = [
        px, py, support_top + item_ref.size[2] / 2
    ]
    item_ref[0].rotation = [0, 0, radians(heading)]

# Establish the defining orientation before the generic orientation anchors.
solver.point_towards(chair_D[0], dining_chair_F[0])

# Exact position anchors preserve the checked non-overlapping floor layout,
# the sofa-between-chairs relationship, and all doorway circulation space.
# Anchors are fixed reference points, not additional scene furniture.
for asset_ref, px, py, pz, heading in floor_layout:
    solver.distance_constraint(
        asset_ref[0],
        AssetInstance(position=[px, py, pz]),
        0, 0, weight=10,
    )
    if asset_ref is not chair_D:
        solver.align_with(
            asset_ref[0],
            AssetInstance(
                position=[px, py, pz],
                rotation=[0, 0, radians(heading)],
            ),
        )

# The carpet intentionally lies beneath lounge furniture; the intersecting
# furniture has been raised by its 1 cm thickness rather than intersecting it.
solver.on_top_of(coffee_table[0], carpet[0])
solver.on_top_of(sofa_A[0], carpet[0])
solver.on_top_of(chair_B[0], carpet[0])
solver.on_top_of(chair_C[0], carpet[0])
solver.on_top_of(chair_D[0], carpet[0])

# Wall contacts are only used on solid segments, never across a doorway.
solver.against_wall(wall_cabinet[0], walls[5])
solver.against_wall(tv_cabinet[0], walls[7])
solver.against_wall(nakadao_station[0], walls[7])

# Every tabletop object receives support, position, and orientation constraints.
# Zero-distance anchors retain the deliberately separated tabletop footprints.
for item_ref, support_ref, px, py, heading in surface_layout:
    solver.on_top_of(item_ref[0], support_ref[0])
    solver.distance_constraint(
        item_ref[0],
        AssetInstance(position=list(item_ref[0].position)),
        0, 0, weight=10,
    )
    solver.align_with(
        item_ref[0],
        AssetInstance(
            position=list(item_ref[0].position),
            rotation=[0, 0, radians(heading)],
        ),
    )

# Reinforce dining-chair function without changing the specified headings:
# each side faces across the table, with a usable gap to its edge.
for seat_ref in (
    dining_chair_A, dining_chair_B, dining_chair_C,
    dining_chair_D, dining_chair_E, dining_chair_F,
):
    solver.distance_constraint(
        seat_ref[0], dining_table[0], 0.95, 1.20, weight=10
    )

solver.constraints = []
ornaments_E[0].position = [4.934999942779541, 4.599999904632568, 0.5600000023841858]
ornaments_E[0].rotation = [0, 0, -3.1290262823329655]
ornaments_E[0].optimize = 2
flowers_C[0].position = [4.934999942779541, 4.0, 0.7250000238418579]
flowers_C[0].rotation = [0, 0, -3.1290262823329655]
flowers_C[0].optimize = 2
sofa_A[0].position = [0.8493685126304626, 2.7050118446350098, 0.4350000023841858]
sofa_A[0].rotation = [0, 0, 0.01256637125682779]
sofa_A[0].optimize = 2
chair_C[0].position = [4.043031692504883, 2.9973111152648926, 0.4350000023841858]
chair_C[0].rotation = [0, 0, -3.1290262823329655]
chair_C[0].optimize = 2
ornaments_A[0].position = [2.75, 7.150000095367432, 0.9199999570846558]
ornaments_A[0].rotation = [0, 0, 0.01256637125682779]
ornaments_A[0].optimize = 2
ornaments_D[0].position = [0.1599999964237213, 7.199999809265137, 0.7400000095367432]
ornaments_D[0].rotation = [0, 0, 0.01256637125682779]
ornaments_D[0].optimize = 2
ornaments_B[0].position = [2.75, 8.550000190734863, 0.8849999904632568]
ornaments_B[0].rotation = [0, 0, 0.01256637125682779]
ornaments_B[0].optimize = 2
flowers_D[0].position = [4.199999809265137, 5.900000095367432, 0.800000011920929]
flowers_D[0].rotation = [0, 0, 0.01256637125682779]
flowers_D[0].optimize = 2
dining_chair_A[0].position = [1.7999999523162842, 7.150000095367432, 0.44999998807907104]
dining_chair_A[0].rotation = [0, 0, 0.01256637125682779]
dining_chair_A[0].optimize = 2
dining_chair_B[0].position = [1.7999999523162842, 7.849999904632568, 0.44999998807907104]
dining_chair_B[0].rotation = [0, 0, 0.01256637125682779]
dining_chair_B[0].optimize = 2
wall_cabinet[0].position = [0.15989041328430176, 6.699999809265137, 0.32499998807907104]
wall_cabinet[0].rotation = [0, 0, -3.427505453407993e-05]
wall_cabinet[0].optimize = 2
tv_cabinet[0].position = [4.935095310211182, 4.449999809265137, 0.25]
tv_cabinet[0].rotation = [0, 0, 3.141557702140299]
tv_cabinet[0].optimize = 2
side_table_C[0].position = [4.199999809265137, 5.900000095367432, 0.30000001192092896]
side_table_C[0].rotation = [0, 0, 0.01256637125682779]
side_table_C[0].optimize = 2
dining_chair_F[0].position = [3.700000047683716, 8.550000190734863, 0.44999998807907104]
dining_chair_F[0].rotation = [0, 0, -3.125884689672577]
dining_chair_F[0].optimize = 2
coffee_table[0].position = [2.450000047683716, 2.700000047683716, 0.2199999988079071]
coffee_table[0].rotation = [0, 0, 0.01884955539881635]
coffee_table[0].optimize = 2
dining_chair_C[0].position = [1.7999999523162842, 8.550000190734863, 0.44999998807907104]
dining_chair_C[0].rotation = [0, 0, 0.01256637125682779]
dining_chair_C[0].optimize = 2
carpet[0].position = [2.450000047683716, 2.700000047683716, 0.004999999888241291]
carpet[0].rotation = [0, 0, 0.025132740109855806]
carpet[0].optimize = 2
chair_B[0].position = [4.071922302246094, 1.8480372428894043, 0.4350000023841858]
chair_B[0].rotation = [0, 0, -3.1290262823329655]
chair_B[0].optimize = 2
ornaments_G[0].position = [2.450000047683716, 2.4000000953674316, 0.6050000190734863]
ornaments_G[0].rotation = [0, 0, 0.01256637125682779]
ornaments_G[0].optimize = 2
desk_lamp_B[0].position = [1.5499999523162842, 4.25, 0.8500000238418579]
desk_lamp_B[0].rotation = [0, 0, -1.5582299555380688]
desk_lamp_B[0].optimize = 2
ornaments_C[0].position = [0.1599999964237213, 6.900000095367432, 0.7999999523162842]
ornaments_C[0].rotation = [0, 0, 0.01256637125682779]
ornaments_C[0].optimize = 2
dining_chair_E[0].position = [3.700000047683716, 7.849999904632568, 0.44999998807907104]
dining_chair_E[0].rotation = [0, 0, -3.1290262823329655]
dining_chair_E[0].optimize = 2
nakadao_station[0].position = [4.934954643249512, 9.100000381469727, 0.42500001192092896]
nakadao_station[0].rotation = [0, 0, 3.1415066881659697]
nakadao_station[0].optimize = 2
side_table_B[0].position = [1.5499999523162842, 4.25, 0.30000001192092896]
side_table_B[0].rotation = [0, 0, 0.01256637125682779]
side_table_B[0].optimize = 2
flowers_B[0].position = [0.1599999964237213, 6.300000190734863, 0.85999995470047]
flowers_B[0].rotation = [0, 0, 0.01256637125682779]
flowers_B[0].optimize = 2
sofa_B[0].position = [3.0999999046325684, 0.550000011920929, 0.42500001192092896]
sofa_B[0].rotation = [0, 0, 1.5802211042556205]
sofa_B[0].optimize = 2
side_table_A[0].position = [1.5, 1.100000023841858, 0.2750000059604645]
side_table_A[0].rotation = [0, 0, 0.01256637125682779]
side_table_A[0].optimize = 2
ornaments_F[0].position = [4.934999942779541, 5.050000190734863, 0.6399999856948853]
ornaments_F[0].rotation = [0, 0, -3.1290262823329655]
ornaments_F[0].optimize = 2
dining_chair_D[0].position = [3.700000047683716, 7.150000095367432, 0.44999998807907104]
dining_chair_D[0].rotation = [0, 0, -3.1290262823329655]
dining_chair_D[0].optimize = 2
flowers_A[0].position = [2.75, 7.849999904632568, 1.0099999904632568]
flowers_A[0].rotation = [0, 0, 0.01256637125682779]
flowers_A[0].optimize = 2
dining_table[0].position = [2.75, 7.849999904632568, 0.3799999952316284]
dining_table[0].rotation = [0, 0, 0.03769911119841034]
dining_table[0].optimize = 2
desk_lamp_A[0].position = [1.5, 1.100000023841858, 0.800000011920929]
desk_lamp_A[0].rotation = [0, 0, 1.5833626980517244]
desk_lamp_A[0].optimize = 2
ornaments_H[0].position = [2.450000047683716, 3.0, 0.5649999976158142]
ornaments_H[0].rotation = [0, 0, 0.01256637125682779]
ornaments_H[0].optimize = 2
chair_D[0].position = [0.8203490972518921, 3.8594131469726562, 0.4350000023841858]
chair_D[0].rotation = [0, 0, 0.9552746542297077]
chair_D[0].optimize = 2
chair_A[0].position = [0.6499999761581421, 0.8500000238418579, 0.42500001192092896]
chair_A[0].rotation = [0, 0, 0.00942477746072377]
chair_A[0].optimize = 2

