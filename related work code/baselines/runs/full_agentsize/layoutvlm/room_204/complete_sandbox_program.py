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
chair_A = Assets(description="chair", size=[0.78, 0.72, 0.82], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.80, 0.74, 0.84], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="chair", size=[0.78, 0.72, 0.82], placements=[AssetInstance() for _ in range(1)])
ornaments_A = Assets(description="ornaments", size=[0.14, 0.18, 0.32], placements=[AssetInstance() for _ in range(1)])
dining_chair_A = Assets(description="dining chair", size=[0.55, 0.48, 0.86], placements=[AssetInstance() for _ in range(1)])
ornaments_B = Assets(description="ornaments", size=[0.16, 0.22, 0.28], placements=[AssetInstance() for _ in range(1)])
flowers_A = Assets(description="flowers", size=[0.32, 0.32, 0.52], placements=[AssetInstance() for _ in range(1)])
dining_table = Assets(description="dining table", size=[1.00, 2.20, 0.76], placements=[AssetInstance() for _ in range(1)])
ornaments_C = Assets(description="ornaments", size=[0.16, 0.16, 0.38], placements=[AssetInstance() for _ in range(1)])
wall_cabinet = Assets(description="wall cabinet", size=[0.36, 1.60, 0.72], placements=[AssetInstance() for _ in range(1)])
ornaments_D = Assets(description="ornaments", size=[0.18, 0.24, 0.34], placements=[AssetInstance() for _ in range(1)])
tv_cabinet = Assets(description="tv cabinet", size=[0.45, 2.00, 0.58], placements=[AssetInstance() for _ in range(1)])
flowers_B = Assets(description="flowers", size=[0.30, 0.30, 0.48], placements=[AssetInstance() for _ in range(1)])
dining_chair_B = Assets(description="dining chair", size=[0.55, 0.48, 0.86], placements=[AssetInstance() for _ in range(1)])
sofa_A = Assets(description="sofa", size=[0.92, 2.25, 0.84], placements=[AssetInstance() for _ in range(1)])
ornaments_E = Assets(description="ornaments", size=[0.16, 0.20, 0.30], placements=[AssetInstance() for _ in range(1)])
chair_D = Assets(description="chair", size=[0.82, 0.76, 0.86], placements=[AssetInstance() for _ in range(1)])
ornaments_F = Assets(description="ornaments", size=[0.14, 0.17, 0.26], placements=[AssetInstance() for _ in range(1)])
side_table_A = Assets(description="side table", size=[0.50, 0.50, 0.56], placements=[AssetInstance() for _ in range(1)])
dining_chair_C = Assets(description="dining chair", size=[0.55, 0.48, 0.86], placements=[AssetInstance() for _ in range(1)])
flowers_C = Assets(description="flowers", size=[0.28, 0.28, 0.44], placements=[AssetInstance() for _ in range(1)])
flowers_D = Assets(description="flowers", size=[0.30, 0.30, 0.50], placements=[AssetInstance() for _ in range(1)])
desk_lamp_A = Assets(description="desk lamp", size=[0.28, 0.28, 0.52], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[2.40, 3.20, 0.02], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="coffee table", size=[0.70, 1.30, 0.42], placements=[AssetInstance() for _ in range(1)])
sofa_B = Assets(description="sofa", size=[0.95, 2.40, 0.85], placements=[AssetInstance() for _ in range(1)])
desk_lamp_B = Assets(description="desk lamp", size=[0.27, 0.27, 0.50], placements=[AssetInstance() for _ in range(1)])
dining_chair_D = Assets(description="dining chair", size=[0.55, 0.48, 0.86], placements=[AssetInstance() for _ in range(1)])
dining_chair_E = Assets(description="dining chair", size=[0.55, 0.48, 0.86], placements=[AssetInstance() for _ in range(1)])
nakadao_station = Assets(description="nakadao station", size=[0.45, 1.20, 0.85], placements=[AssetInstance() for _ in range(1)])
ornaments_G = Assets(description="ornaments", size=[0.18, 0.25, 0.36], placements=[AssetInstance() for _ in range(1)])
dining_chair_F = Assets(description="dining chair", size=[0.55, 0.48, 0.86], placements=[AssetInstance() for _ in range(1)])
side_table_B = Assets(description="side table", size=[0.52, 0.52, 0.56], placements=[AssetInstance() for _ in range(1)])
ornaments_H = Assets(description="ornaments", size=[0.15, 0.20, 0.30], placements=[AssetInstance() for _ in range(1)])
side_table_C = Assets(description="side table", size=[0.50, 0.50, 0.56], placements=[AssetInstance() for _ in range(1)])

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

chair_A[0].position = [5.019188072237885, 9.166666529239299, 0.41]
chair_A[0].rotation = [0, 0, 0]
chair_B[0].position = [1.626139453277327, 6.069635201634333, 0.42]
chair_B[0].rotation = [0, 0, 0]
chair_C[0].position = [1.4601966832403128, 10.696283320258269, 0.41]
chair_C[0].rotation = [0, 0, 0]
ornaments_A[0].position = [4.323953513353444, 9.635424687187598, 0.16]
ornaments_A[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [0.7220991652571355, 7.4816066079339025, 0.43]
dining_chair_A[0].rotation = [0, 0, 0]
ornaments_B[0].position = [0.1337306642256466, 5.169508075712696, 0.14]
ornaments_B[0].rotation = [0, 0, 0]
flowers_A[0].position = [4.581240326469797, 2.2213870563503737, 0.26]
flowers_A[0].rotation = [0, 0, 0]
dining_table[0].position = [0.9721196673409218, 8.614464779958173, 0.38]
dining_table[0].rotation = [0, 0, 0]
ornaments_C[0].position = [4.537523331069865, 0.27193424528792215, 0.19]
ornaments_C[0].rotation = [0, 0, 0]
wall_cabinet[0].position = [1.2362052608398577, 8.540097611536643, 0.36]
wall_cabinet[0].rotation = [0, 0, 0]
ornaments_D[0].position = [0.14050319016597376, 5.721764064858514, 0.17]
ornaments_D[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [2.0542962342344233, 5.789157089855678, 0.29]
tv_cabinet[0].rotation = [0, 0, 0]
flowers_B[0].position = [0.5783935599946182, 11.247057912722934, 0.24]
flowers_B[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [3.046128809330875, 1.9089205112448726, 0.43]
dining_chair_B[0].rotation = [0, 0, 0]
sofa_A[0].position = [1.380595939365623, 11.688162583985925, 0.42]
sofa_A[0].rotation = [0, 0, 0]
ornaments_E[0].position = [1.2222362292175584, 13.000256611582117, 0.15]
ornaments_E[0].rotation = [0, 0, 0]
chair_D[0].position = [4.3829230984181065, 4.400024035691588, 0.43]
chair_D[0].rotation = [0, 0, 0]
ornaments_F[0].position = [0.68402059730907, 1.0745075449022152, 0.13]
ornaments_F[0].rotation = [0, 0, 0]
side_table_A[0].position = [2.2091183666971905, 5.325925105257085, 0.28]
side_table_A[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [1.5027585127169851, 12.449860522580341, 0.43]
dining_chair_C[0].rotation = [0, 0, 0]
flowers_C[0].position = [0.7030334342204811, 12.433799403648653, 0.22]
flowers_C[0].rotation = [0, 0, 0]
flowers_D[0].position = [2.8089898552969403, 2.3408120201538, 0.25]
flowers_D[0].rotation = [0, 0, 0]
desk_lamp_A[0].position = [0.9575412064227056, 1.0032750288363261, 0.26]
desk_lamp_A[0].rotation = [0, 0, 0]
carpet[0].position = [1.3412855856103851, 1.9457110333932437, 0.01]
carpet[0].rotation = [0, 0, 0]
coffee_table[0].position = [1.5821400086588095, 1.0475635850059972, 0.21]
coffee_table[0].rotation = [0, 0, 0]
sofa_B[0].position = [2.317997746869281, 5.759507372032586, 0.425]
sofa_B[0].rotation = [0, 0, 0]
desk_lamp_B[0].position = [4.971068000280533, 8.104670962027642, 0.25]
desk_lamp_B[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [0.1535822115783195, 3.4425931915131196, 0.43]
dining_chair_D[0].rotation = [0, 0, 0]
dining_chair_E[0].position = [4.44417423321223, 1.6086594012824342, 0.43]
dining_chair_E[0].rotation = [0, 0, 0]
nakadao_station[0].position = [1.8677751238837943, 8.335189004126073, 0.425]
nakadao_station[0].rotation = [0, 0, 0]
ornaments_G[0].position = [1.591752715903657, 2.0571960800406055, 0.18]
ornaments_G[0].rotation = [0, 0, 0]
dining_chair_F[0].position = [4.403646308594029, 8.205664051007927, 0.43]
dining_chair_F[0].rotation = [0, 0, 0]
side_table_B[0].position = [1.7282500660332505, 3.5541192642144814, 0.28]
side_table_B[0].rotation = [0, 0, 0]
ornaments_H[0].position = [1.3942539173092294, 11.898284004842113, 0.15]
ornaments_H[0].rotation = [0, 0, 0]
side_table_C[0].position = [3.4802394715334515, 9.951104763971546, 0.28]
side_table_C[0].rotation = [0, 0, 0]
chair_A[0].position = [5.019188072237885, 9.166666529239299, 0.41]
chair_A[0].rotation = [0, 0, 0]
chair_B[0].position = [1.626139453277327, 6.069635201634333, 0.42]
chair_B[0].rotation = [0, 0, 0]
chair_C[0].position = [1.4601966832403128, 10.696283320258269, 0.41]
chair_C[0].rotation = [0, 0, 0]
ornaments_A[0].position = [4.323953513353444, 9.635424687187598, 0.16]
ornaments_A[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [0.7220991652571355, 7.4816066079339025, 0.43]
dining_chair_A[0].rotation = [0, 0, 0]
ornaments_B[0].position = [0.1337306642256466, 5.169508075712696, 0.14]
ornaments_B[0].rotation = [0, 0, 0]
flowers_A[0].position = [4.581240326469797, 2.2213870563503737, 0.26]
flowers_A[0].rotation = [0, 0, 0]
dining_table[0].position = [0.9721196673409218, 8.614464779958173, 0.38]
dining_table[0].rotation = [0, 0, 0]
ornaments_C[0].position = [4.537523331069865, 0.27193424528792215, 0.19]
ornaments_C[0].rotation = [0, 0, 0]
wall_cabinet[0].position = [1.2362052608398577, 8.540097611536643, 0.36]
wall_cabinet[0].rotation = [0, 0, 0]
ornaments_D[0].position = [0.14050319016597376, 5.721764064858514, 0.17]
ornaments_D[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [2.0542962342344233, 5.789157089855678, 0.29]
tv_cabinet[0].rotation = [0, 0, 0]
flowers_B[0].position = [0.5783935599946182, 11.247057912722934, 0.24]
flowers_B[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [3.046128809330875, 1.9089205112448726, 0.43]
dining_chair_B[0].rotation = [0, 0, 0]
sofa_A[0].position = [1.380595939365623, 11.688162583985925, 0.42]
sofa_A[0].rotation = [0, 0, 0]
ornaments_E[0].position = [1.2222362292175584, 13.000256611582117, 0.15]
ornaments_E[0].rotation = [0, 0, 0]
chair_D[0].position = [4.3829230984181065, 4.400024035691588, 0.43]
chair_D[0].rotation = [0, 0, 0]
ornaments_F[0].position = [0.68402059730907, 1.0745075449022152, 0.13]
ornaments_F[0].rotation = [0, 0, 0]
side_table_A[0].position = [2.2091183666971905, 5.325925105257085, 0.28]
side_table_A[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [1.5027585127169851, 12.449860522580341, 0.43]
dining_chair_C[0].rotation = [0, 0, 0]
flowers_C[0].position = [0.7030334342204811, 12.433799403648653, 0.22]
flowers_C[0].rotation = [0, 0, 0]
flowers_D[0].position = [2.8089898552969403, 2.3408120201538, 0.25]
flowers_D[0].rotation = [0, 0, 0]
desk_lamp_A[0].position = [0.9575412064227056, 1.0032750288363261, 0.26]
desk_lamp_A[0].rotation = [0, 0, 0]
carpet[0].position = [1.3412855856103851, 1.9457110333932437, 0.01]
carpet[0].rotation = [0, 0, 0]
coffee_table[0].position = [1.5821400086588095, 1.0475635850059972, 0.21]
coffee_table[0].rotation = [0, 0, 0]
sofa_B[0].position = [2.317997746869281, 5.759507372032586, 0.425]
sofa_B[0].rotation = [0, 0, 0]
desk_lamp_B[0].position = [4.971068000280533, 8.104670962027642, 0.25]
desk_lamp_B[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [0.1535822115783195, 3.4425931915131196, 0.43]
dining_chair_D[0].rotation = [0, 0, 0]
dining_chair_E[0].position = [4.44417423321223, 1.6086594012824342, 0.43]
dining_chair_E[0].rotation = [0, 0, 0]
nakadao_station[0].position = [1.8677751238837943, 8.335189004126073, 0.425]
nakadao_station[0].rotation = [0, 0, 0]
ornaments_G[0].position = [1.591752715903657, 2.0571960800406055, 0.18]
ornaments_G[0].rotation = [0, 0, 0]
dining_chair_F[0].position = [4.403646308594029, 8.205664051007927, 0.43]
dining_chair_F[0].rotation = [0, 0, 0]
side_table_B[0].position = [1.7282500660332505, 3.5541192642144814, 0.28]
side_table_B[0].rotation = [0, 0, 0]
ornaments_H[0].position = [1.3942539173092294, 11.898284004842113, 0.15]
ornaments_H[0].rotation = [0, 0, 0]
side_table_C[0].position = [3.4802394715334515, 9.951104763971546, 0.28]
side_table_C[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed orientation references let every movable asset retain its intended heading.
face_east = AssetInstance(rotation=[0, 0, radians(0)])
face_north = AssetInstance(rotation=[0, 0, radians(90)])
face_west = AssetInstance(rotation=[0, 0, radians(180)])
face_south = AssetInstance(rotation=[0, 0, radians(270)])

def fix_placement(asset_instance, position, orientation_reference):
    """Preserve the planned position and upright orientation during optimization."""
    asset_instance.position = position
    asset_instance.rotation = orientation_reference.rotation.copy()
    solver.distance_constraint(
        asset_instance,
        AssetInstance(position=position),
        0,
        0,
        weight=10,
    )
    solver.align_with(asset_instance, orientation_reference, angle=0)


# Dining zone in the lower part of the room. Its circulation stays clear of
# the window wall and of the door on the left at y=5.52.
fix_placement(dining_table[0], [2.55, 2.25, 0.38], face_north)

# Three chairs are placed along each long side of the dining table.
fix_placement(dining_chair_A[0], [1.58, 1.40, 0.43], face_east)
fix_placement(dining_chair_B[0], [1.58, 2.30, 0.43], face_east)
fix_placement(dining_chair_C[0], [1.58, 3.20, 0.43], face_east)
fix_placement(dining_chair_D[0], [3.52, 1.40, 0.43], face_west)
fix_placement(dining_chair_E[0], [3.52, 2.30, 0.43], face_west)
fix_placement(dining_chair_F[0], [3.52, 3.20, 0.43], face_west)

# Reinforce the functional relationship between the dining chairs and table.
for dining_seat in [
    dining_chair_A[0], dining_chair_B[0], dining_chair_C[0],
    dining_chair_D[0], dining_chair_E[0], dining_chair_F[0],
]:
    solver.distance_constraint(dining_seat, dining_table[0], 0.85, 1.50)
    solver.point_towards(dining_seat, dining_table[0])


# Main conversation area. The carpet and coffee table remain centered, while
# sofa_A (o0014) is spatially between chair_D (o0016) and chair_B (o0001).
fix_placement(carpet[0], [2.58, 6.85, 0.01], face_east)
fix_placement(coffee_table[0], [2.58, 6.35, 0.21], face_north)
fix_placement(sofa_A[0], [2.58, 7.55, 0.42], face_south)

fix_placement(chair_D[0], [1.02, 7.55, 0.43], face_south)
fix_placement(chair_B[0], [4.14, 7.55, 0.42], face_south)

# Additional lounge chairs occupy the open side of the carpet and face inward.
fix_placement(chair_A[0], [1.25, 5.65, 0.41], face_north)
fix_placement(chair_C[0], [3.90, 5.65, 0.41], face_north)

# Preserve the requested "sofa between the two chairs" grouping.
solver.distance_constraint(chair_D[0], sofa_A[0], 1.50, 1.70, weight=10)
solver.distance_constraint(chair_B[0], sofa_A[0], 1.50, 1.70, weight=10)
solver.align_with(chair_D[0], chair_B[0])

# chair_D is o0016 and dining_chair_F is o0031; this explicit constraint
# enforces the requested facing relationship.
solver.point_towards(chair_D[0], dining_chair_F[0], angle=0)

# Keep the other lounge seating directed toward the central coffee table.
solver.point_towards(chair_A[0], coffee_table[0])
solver.point_towards(chair_B[0], coffee_table[0])
solver.point_towards(chair_C[0], coffee_table[0])
solver.point_towards(sofa_A[0], coffee_table[0])


# A second sofa forms a separate reading/conversation edge. It stays below
# the left-side door at y=5.52 and outside the dining-chair clearances.
fix_placement(sofa_B[0], [4.60, 4.45, 0.425], face_west)
solver.distance_constraint(sofa_B[0], coffee_table[0], 1.80, 2.70)
solver.point_towards(sofa_B[0], coffee_table[0])


# Low media furniture sits beneath the right-side window; the taller cabinet
# is farther north, beyond that window. The station occupies the short,
# window-free part of the bottom wall.
fix_placement(tv_cabinet[0], [4.935, 7.30, 0.29], face_west)
solver.against_wall(tv_cabinet[0], walls[7])
solver.point_towards(tv_cabinet[0], sofa_A[0], angle=180)

fix_placement(wall_cabinet[0], [4.98, 9.35, 0.36], face_west)
solver.against_wall(wall_cabinet[0], walls[7])
solver.align_with(wall_cabinet[0], tv_cabinet[0])

fix_placement(nakadao_station[0], [4.48, 0.225, 0.425], face_north)
solver.against_wall(nakadao_station[0], walls[6])
solver.align_with(nakadao_station[0], face_north)


# Side tables are placed beside lounge seats rather than in circulation paths.
fix_placement(side_table_A[0], [0.55, 6.35, 0.28], face_east)
fix_placement(side_table_B[0], [4.58, 6.35, 0.28], face_west)
fix_placement(side_table_C[0], [0.58, 8.50, 0.28], face_east)

solver.distance_constraint(side_table_A[0], chair_A[0], 0.70, 1.10)
solver.align_with(side_table_A[0], chair_A[0])
solver.distance_constraint(side_table_B[0], chair_C[0], 0.70, 1.10)
solver.align_with(side_table_B[0], chair_C[0])
solver.distance_constraint(side_table_C[0], chair_D[0], 0.85, 1.20)
solver.align_with(side_table_C[0], chair_D[0])


# Small dining-table objects. Exact horizontal locations prevent their
# bounding boxes from overlapping; on_top_of supplies the correct height.
fix_placement(ornaments_A[0], [2.30, 1.72, 0.92], face_north)
solver.on_top_of(ornaments_A[0], dining_table[0])

fix_placement(ornaments_B[0], [2.78, 1.72, 0.90], face_north)
solver.on_top_of(ornaments_B[0], dining_table[0])

fix_placement(flowers_A[0], [2.30, 2.72, 1.02], face_north)
solver.on_top_of(flowers_A[0], dining_table[0])

fix_placement(flowers_B[0], [2.78, 2.72, 1.00], face_north)
solver.on_top_of(flowers_B[0], dining_table[0])


# Decorations on the coffee table are spread across its long axis.
fix_placement(ornaments_E[0], [2.15, 6.18, 0.57], face_south)
solver.on_top_of(ornaments_E[0], coffee_table[0])

fix_placement(ornaments_F[0], [2.15, 6.52, 0.55], face_south)
solver.on_top_of(ornaments_F[0], coffee_table[0])

fix_placement(flowers_C[0], [2.95, 6.18, 0.64], face_south)
solver.on_top_of(flowers_C[0], coffee_table[0])

fix_placement(flowers_D[0], [2.95, 6.52, 0.67], face_south)
solver.on_top_of(flowers_D[0], coffee_table[0])


# Two ornaments sit on the long top of the wall cabinet.
fix_placement(ornaments_C[0], [4.98, 9.02, 0.91], face_west)
solver.on_top_of(ornaments_C[0], wall_cabinet[0])

fix_placement(ornaments_D[0], [4.98, 9.66, 0.89], face_west)
solver.on_top_of(ornaments_D[0], wall_cabinet[0])


# Remaining ornaments are placed at opposite ends of the TV cabinet.
fix_placement(ornaments_G[0], [4.93, 6.78, 0.76], face_west)
solver.on_top_of(ornaments_G[0], tv_cabinet[0])

fix_placement(ornaments_H[0], [4.93, 7.78, 0.73], face_west)
solver.on_top_of(ornaments_H[0], tv_cabinet[0])


# Reading lamps belong on the two side tables adjacent to the lounge chairs.
fix_placement(desk_lamp_A[0], [0.55, 6.35, 0.82], face_north)
solver.on_top_of(desk_lamp_A[0], side_table_A[0])

fix_placement(desk_lamp_B[0], [4.58, 6.35, 0.81], face_north)
solver.on_top_of(desk_lamp_B[0], side_table_B[0])

solver.constraints = []
chair_C[0].position = [3.9000000953674316, 5.650000095367432, 0.4099999964237213]
chair_C[0].rotation = [0, 0, 2.1452280138729436]
chair_C[0].optimize = 2
ornaments_D[0].position = [4.974637508392334, 9.508193969726562, 0.89000004529953]
ornaments_D[0].rotation = [0, 0, -3.1290262823329655]
ornaments_D[0].optimize = 2
side_table_B[0].position = [4.579999923706055, 6.349999904632568, 0.2800000011920929]
side_table_B[0].rotation = [0, 0, 2.1115063336777142]
side_table_B[0].optimize = 2
wall_cabinet[0].position = [4.354144096374512, 9.350000381469727, 0.36000001430511475]
wall_cabinet[0].rotation = [0, 0, -1.6061057976070334]
wall_cabinet[0].optimize = 2
dining_chair_A[0].position = [1.5800000429153442, 1.399999976158142, 0.4300000071525574]
dining_chair_A[0].rotation = [0, 0, 0.19797867243872083]
dining_chair_A[0].optimize = 2
chair_D[0].position = [1.0199999809265137, 7.550000190734863, 0.4300000071525574]
chair_D[0].rotation = [0, 0, -1.5848864616886127]
chair_D[0].optimize = 2
ornaments_F[0].position = [2.1500000953674316, 6.519999980926514, 0.5499999523162842]
ornaments_F[0].rotation = [0, 0, -1.5582299555380688]
ornaments_F[0].optimize = 2
ornaments_G[0].position = [4.929999828338623, 6.78000020980835, 0.7599999904632568]
ornaments_G[0].rotation = [0, 0, -3.1290262823329655]
ornaments_G[0].optimize = 2
dining_chair_C[0].position = [1.5800000429153442, 3.200000047683716, 0.4300000071525574]
dining_chair_C[0].rotation = [0, 0, -0.19595997381625216]
dining_chair_C[0].optimize = 2
flowers_B[0].position = [2.7799999713897705, 2.7200000286102295, 1.0]
flowers_B[0].rotation = [0, 0, 1.5833626980517244]
flowers_B[0].optimize = 2
ornaments_C[0].position = [4.984508037567139, 9.147621154785156, 0.9100000262260437]
ornaments_C[0].rotation = [0, 0, -3.1290262823329655]
ornaments_C[0].optimize = 2
coffee_table[0].position = [2.5799999237060547, 6.349999904632568, 0.20999999344348907]
coffee_table[0].rotation = [0, 0, 1.6116370324823435]
coffee_table[0].optimize = 2
tv_cabinet[0].position = [4.934896469116211, 7.300000190734863, 0.28999999165534973]
tv_cabinet[0].rotation = [0, 0, 3.141520628359458]
tv_cabinet[0].optimize = 2
dining_chair_B[0].position = [1.5800000429153442, 2.299999952316284, 0.4300000071525574]
dining_chair_B[0].rotation = [0, 0, 0.0157079639172164]
dining_chair_B[0].optimize = 2
flowers_C[0].position = [2.950000047683716, 6.179999828338623, 0.6399999856948853]
flowers_C[0].rotation = [0, 0, -1.5582299555380688]
flowers_C[0].optimize = 2
chair_A[0].position = [1.25, 5.650000095367432, 0.4099999964237213]
chair_A[0].rotation = [0, 0, 0.9846552401052558]
chair_A[0].optimize = 2
desk_lamp_A[0].position = [0.550000011920929, 6.349999904632568, 0.8199999928474426]
desk_lamp_A[0].rotation = [0, 0, 1.5833626980517244]
desk_lamp_A[0].optimize = 2
sofa_B[0].position = [4.141190052032471, 4.449999809265137, 0.42500001192092896]
sofa_B[0].rotation = [0, 0, 2.608649102829063]
sofa_B[0].optimize = 2
flowers_A[0].position = [2.299999952316284, 2.7200000286102295, 1.0199999809265137]
flowers_A[0].rotation = [0, 0, 1.5833626980517244]
flowers_A[0].optimize = 2
ornaments_A[0].position = [2.2991561889648438, 1.7341171503067017, 0.9199999570846558]
ornaments_A[0].rotation = [0, 0, 1.5833626980517244]
ornaments_A[0].optimize = 2
dining_chair_D[0].position = [3.5199999809265137, 1.399999976158142, 0.4300000071525574]
dining_chair_D[0].rotation = [0, 0, 2.994285560766236]
dining_chair_D[0].optimize = 2
ornaments_B[0].position = [2.7774481773376465, 1.7627005577087402, 0.8999999761581421]
ornaments_B[0].rotation = [0, 0, 1.5833626980517244]
ornaments_B[0].optimize = 2
dining_table[0].position = [2.549999952316284, 2.25, 0.3799999952316284]
dining_table[0].rotation = [0, 0, 1.6304865860847333]
dining_table[0].optimize = 2
carpet[0].position = [2.5799999237060547, 6.849999904632568, 0.009999999776482582]
carpet[0].rotation = [0, 0, 0.00942477746072377]
carpet[0].optimize = 2
side_table_C[0].position = [0.5799999833106995, 8.5, 0.2800000011920929]
side_table_C[0].rotation = [0, 0, -1.5321411919547108]
side_table_C[0].optimize = 2
flowers_D[0].position = [2.950000047683716, 6.519999980926514, 0.6699999570846558]
flowers_D[0].rotation = [0, 0, -1.5582299555380688]
flowers_D[0].optimize = 2
dining_chair_F[0].position = [3.5199999809265137, 3.200000047683716, 0.4300000071525574]
dining_chair_F[0].rotation = [0, 0, -2.898732495764446]
dining_chair_F[0].optimize = 2
ornaments_H[0].position = [4.929999828338623, 7.78000020980835, 0.7300000190734863]
ornaments_H[0].rotation = [0, 0, -3.1290262823329655]
ornaments_H[0].optimize = 2
sofa_A[0].position = [2.5799999237060547, 7.550000190734863, 0.41999998688697815]
sofa_A[0].rotation = [0, 0, -1.548805178508874]
sofa_A[0].optimize = 2
ornaments_E[0].position = [2.1500000953674316, 6.179999828338623, 0.5699999928474426]
ornaments_E[0].rotation = [0, 0, -1.5582299555380688]
ornaments_E[0].optimize = 2
side_table_A[0].position = [0.550000011920929, 6.349999904632568, 0.2800000011920929]
side_table_A[0].rotation = [0, 0, 1.0052262159853054]
side_table_A[0].optimize = 2
nakadao_station[0].position = [4.480000019073486, 0.22496441006660461, 0.42500001192092896]
nakadao_station[0].rotation = [0, 0, 1.5708019950135064]
nakadao_station[0].optimize = 2
chair_B[0].position = [4.139999866485596, 7.550000190734863, 0.41999998688697815]
chair_B[0].rotation = [0, 0, -2.1071662981949997]
chair_B[0].optimize = 2
dining_chair_E[0].position = [3.5199999809265137, 2.299999952316284, 0.4300000071525574]
dining_chair_E[0].rotation = [0, 0, -3.125884689672577]
dining_chair_E[0].optimize = 2
desk_lamp_B[0].position = [4.579999923706055, 6.349999904632568, 0.8100000023841858]
desk_lamp_B[0].rotation = [0, 0, 1.5833626980517244]
desk_lamp_B[0].optimize = 2

