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
    Wall(corner1=[4.21, 0.00, 0.00], corner2=[4.21, 4.21, 0.00]),
    Wall(corner1=[4.21, 4.21, 0.00], corner2=[0.00, 4.21, 0.00]),
    Wall(corner1=[0.00, 4.21, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.21, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
shelf_A = Assets(description="shelf", size=[0.35, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="book", size=[0.24, 0.16, 0.04], placements=[AssetInstance() for _ in range(1)])
bottle_A = Assets(description="bottle", size=[0.08, 0.08, 0.28], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="lamp", size=[0.22, 0.22, 0.42], placements=[AssetInstance() for _ in range(1)])
food_A = Assets(description="food", size=[0.12, 0.18, 0.24], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="book", size=[0.25, 0.18, 0.04], placements=[AssetInstance() for _ in range(1)])
box = Assets(description="box", size=[0.28, 0.35, 0.22], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="bottle", size=[0.07, 0.07, 0.25], placements=[AssetInstance() for _ in range(1)])
can_A = Assets(description="can", size=[0.08, 0.08, 0.12], placements=[AssetInstance() for _ in range(1)])
microwave = Assets(description="microwave", size=[0.40, 0.50, 0.30], placements=[AssetInstance() for _ in range(1)])
book_C = Assets(description="book", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
pan_A = Assets(description="pan", size=[0.28, 0.46, 0.12], placements=[AssetInstance() for _ in range(1)])
bottle_C = Assets(description="bottle", size=[0.08, 0.08, 0.30], placements=[AssetInstance() for _ in range(1)])
bottle_D = Assets(description="bottle", size=[0.07, 0.07, 0.24], placements=[AssetInstance() for _ in range(1)])
can_B = Assets(description="can", size=[0.08, 0.08, 0.12], placements=[AssetInstance() for _ in range(1)])
bottle_E = Assets(description="bottle", size=[0.09, 0.09, 0.31], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.30, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
food_B = Assets(description="food", size=[0.14, 0.20, 0.25], placements=[AssetInstance() for _ in range(1)])
bottle_F = Assets(description="bottle", size=[0.08, 0.08, 0.27], placements=[AssetInstance() for _ in range(1)])
shelf_C = Assets(description="shelf", size=[0.35, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
book_D = Assets(description="book", size=[0.23, 0.16, 0.04], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="cabinet", size=[0.60, 1.00, 0.90], placements=[AssetInstance() for _ in range(1)])
faucet = Assets(description="faucet", size=[0.25, 0.18, 0.32], placements=[AssetInstance() for _ in range(1)])
pan_B = Assets(description="pan", size=[0.30, 0.48, 0.14], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.24, 0.24, 0.45], placements=[AssetInstance() for _ in range(1)])
book_E = Assets(description="book", size=[0.26, 0.19, 0.04], placements=[AssetInstance() for _ in range(1)])
bottle_G = Assets(description="bottle", size=[0.08, 0.08, 0.29], placements=[AssetInstance() for _ in range(1)])
oven = Assets(description="oven", size=[0.60, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
food_C = Assets(description="food", size=[0.15, 0.22, 0.26], placements=[AssetInstance() for _ in range(1)])
bottle_H = Assets(description="bottle", size=[0.07, 0.07, 0.25], placements=[AssetInstance() for _ in range(1)])

shelf_A[0].instance_id = 'shelf_A_0'
book_A[0].instance_id = 'book_A_0'
bottle_A[0].instance_id = 'bottle_A_0'
lamp_A[0].instance_id = 'lamp_A_0'
food_A[0].instance_id = 'food_A_0'
book_B[0].instance_id = 'book_B_0'
box[0].instance_id = 'box_0'
bottle_B[0].instance_id = 'bottle_B_0'
can_A[0].instance_id = 'can_A_0'
microwave[0].instance_id = 'microwave_0'
book_C[0].instance_id = 'book_C_0'
pan_A[0].instance_id = 'pan_A_0'
bottle_C[0].instance_id = 'bottle_C_0'
bottle_D[0].instance_id = 'bottle_D_0'
can_B[0].instance_id = 'can_B_0'
bottle_E[0].instance_id = 'bottle_E_0'
shelf_B[0].instance_id = 'shelf_B_0'
food_B[0].instance_id = 'food_B_0'
bottle_F[0].instance_id = 'bottle_F_0'
shelf_C[0].instance_id = 'shelf_C_0'
book_D[0].instance_id = 'book_D_0'
cabinet[0].instance_id = 'cabinet_0'
faucet[0].instance_id = 'faucet_0'
pan_B[0].instance_id = 'pan_B_0'
lamp_B[0].instance_id = 'lamp_B_0'
book_E[0].instance_id = 'book_E_0'
bottle_G[0].instance_id = 'bottle_G_0'
oven[0].instance_id = 'oven_0'
food_C[0].instance_id = 'food_C_0'
bottle_H[0].instance_id = 'bottle_H_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

shelf_A[0].position = [0.0007948418520118064, 1.429131632134269, 0.9]
shelf_A[0].rotation = [0, 0, 0]
book_A[0].position = [0.3470968378747222, 2.7498517563703384, 0.02]
book_A[0].rotation = [0, 0, 0]
bottle_A[0].position = [1.774447108874097, 2.753937867945613, 0.14]
bottle_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [3.1094086762051028, 2.2795154221746716, 0.21]
lamp_A[0].rotation = [0, 0, 0]
food_A[0].position = [1.5527085102759073, 2.221824843106616, 0.12]
food_A[0].rotation = [0, 0, 0]
book_B[0].position = [1.5075193555871018, 3.652304287096366, 0.02]
book_B[0].rotation = [0, 0, 0]
box[0].position = [1.4686965320904568, 2.836379752631051, 0.11]
box[0].rotation = [0, 0, 0]
bottle_B[0].position = [2.668267553371498, 2.186840373212449, 0.125]
bottle_B[0].rotation = [0, 0, 0]
can_A[0].position = [3.2843888480023544, 0.38586029249423603, 0.06]
can_A[0].rotation = [0, 0, 0]
microwave[0].position = [3.5645946334238126, 0.6997719983847911, 0.15]
microwave[0].rotation = [0, 0, 0]
book_C[0].position = [3.4025833184649916, 2.112944311695075, 0.02]
book_C[0].rotation = [0, 0, 0]
pan_A[0].position = [1.5812945181328173, 0.9267782390602757, 0.06]
pan_A[0].rotation = [0, 0, 0]
bottle_C[0].position = [0.39884181881146535, 1.3936186733854776, 0.15]
bottle_C[0].rotation = [0, 0, 0]
bottle_D[0].position = [1.7118722563726347, 0.39135074827484556, 0.12]
bottle_D[0].rotation = [0, 0, 0]
can_B[0].position = [1.4983158624796868, 1.2670657504531553, 0.06]
can_B[0].rotation = [0, 0, 0]
bottle_E[0].position = [3.6509370401500325, 1.2778128775610507, 0.155]
bottle_E[0].rotation = [0, 0, 0]
shelf_B[0].position = [2.3504268040394716, 3.9544174891765413, 0.45]
shelf_B[0].rotation = [0, 0, 0]
food_B[0].position = [3.75136442556204, 3.050129020620299, 0.125]
food_B[0].rotation = [0, 0, 0]
bottle_F[0].position = [0.44944389487010344, 0.18523792421684462, 0.135]
bottle_F[0].rotation = [0, 0, 0]
shelf_C[0].position = [0.4641500198463341, 3.6948962947181925, 0.9]
shelf_C[0].rotation = [0, 0, 0]
book_D[0].position = [1.9067074915244397, 3.669156531775885, 0.02]
book_D[0].rotation = [0, 0, 0]
cabinet[0].position = [0.4990651381178142, 0.5624450243151315, 0.45]
cabinet[0].rotation = [0, 0, 0]
faucet[0].position = [4.0262953626151985, 0.5119673400793913, 0.16]
faucet[0].rotation = [0, 0, 0]
pan_B[0].position = [4.04348192183907, 0.2905849556888792, 0.07]
pan_B[0].rotation = [0, 0, 0]
lamp_B[0].position = [2.9525617428981703, 3.8850139246692517, 0.225]
lamp_B[0].rotation = [0, 0, 0]
book_E[0].position = [4.015198267123658, 3.210931886445013, 0.02]
book_E[0].rotation = [0, 0, 0]
bottle_G[0].position = [2.7336341189876405, 1.6558217327540068, 0.145]
bottle_G[0].rotation = [0, 0, 0]
oven[0].position = [1.8121278318964817, 3.240065174882071, 0.45]
oven[0].rotation = [0, 0, 0]
food_C[0].position = [3.838661104408688, 3.1205262935648395, 0.13]
food_C[0].rotation = [0, 0, 0]
bottle_H[0].position = [3.289689905328238, 2.6377383197244844, 0.125]
bottle_H[0].rotation = [0, 0, 0]
shelf_A[0].position = [0.0007948418520118064, 1.429131632134269, 0.9]
shelf_A[0].rotation = [0, 0, 0]
book_A[0].position = [0.3470968378747222, 2.7498517563703384, 0.02]
book_A[0].rotation = [0, 0, 0]
bottle_A[0].position = [1.774447108874097, 2.753937867945613, 0.14]
bottle_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [3.1094086762051028, 2.2795154221746716, 0.21]
lamp_A[0].rotation = [0, 0, 0]
food_A[0].position = [1.5527085102759073, 2.221824843106616, 0.12]
food_A[0].rotation = [0, 0, 0]
book_B[0].position = [1.5075193555871018, 3.652304287096366, 0.02]
book_B[0].rotation = [0, 0, 0]
box[0].position = [1.4686965320904568, 2.836379752631051, 0.11]
box[0].rotation = [0, 0, 0]
bottle_B[0].position = [2.668267553371498, 2.186840373212449, 0.125]
bottle_B[0].rotation = [0, 0, 0]
can_A[0].position = [3.2843888480023544, 0.38586029249423603, 0.06]
can_A[0].rotation = [0, 0, 0]
microwave[0].position = [3.5645946334238126, 0.6997719983847911, 0.15]
microwave[0].rotation = [0, 0, 0]
book_C[0].position = [3.4025833184649916, 2.112944311695075, 0.02]
book_C[0].rotation = [0, 0, 0]
pan_A[0].position = [1.5812945181328173, 0.9267782390602757, 0.06]
pan_A[0].rotation = [0, 0, 0]
bottle_C[0].position = [0.39884181881146535, 1.3936186733854776, 0.15]
bottle_C[0].rotation = [0, 0, 0]
bottle_D[0].position = [1.7118722563726347, 0.39135074827484556, 0.12]
bottle_D[0].rotation = [0, 0, 0]
can_B[0].position = [1.4983158624796868, 1.2670657504531553, 0.06]
can_B[0].rotation = [0, 0, 0]
bottle_E[0].position = [3.6509370401500325, 1.2778128775610507, 0.155]
bottle_E[0].rotation = [0, 0, 0]
shelf_B[0].position = [2.3504268040394716, 3.9544174891765413, 0.45]
shelf_B[0].rotation = [0, 0, 0]
food_B[0].position = [3.75136442556204, 3.050129020620299, 0.125]
food_B[0].rotation = [0, 0, 0]
bottle_F[0].position = [0.44944389487010344, 0.18523792421684462, 0.135]
bottle_F[0].rotation = [0, 0, 0]
shelf_C[0].position = [0.4641500198463341, 3.6948962947181925, 0.9]
shelf_C[0].rotation = [0, 0, 0]
book_D[0].position = [1.9067074915244397, 3.669156531775885, 0.02]
book_D[0].rotation = [0, 0, 0]
cabinet[0].position = [0.4990651381178142, 0.5624450243151315, 0.45]
cabinet[0].rotation = [0, 0, 0]
faucet[0].position = [4.0262953626151985, 0.5119673400793913, 0.16]
faucet[0].rotation = [0, 0, 0]
pan_B[0].position = [4.04348192183907, 0.2905849556888792, 0.07]
pan_B[0].rotation = [0, 0, 0]
lamp_B[0].position = [2.9525617428981703, 3.8850139246692517, 0.225]
lamp_B[0].rotation = [0, 0, 0]
book_E[0].position = [4.015198267123658, 3.210931886445013, 0.02]
book_E[0].rotation = [0, 0, 0]
bottle_G[0].position = [2.7336341189876405, 1.6558217327540068, 0.145]
bottle_G[0].rotation = [0, 0, 0]
oven[0].position = [1.8121278318964817, 3.240065174882071, 0.45]
oven[0].rotation = [0, 0, 0]
food_C[0].position = [3.838661104408688, 3.1205262935648395, 0.13]
food_C[0].rotation = [0, 0, 0]
bottle_H[0].position = [3.289689905328238, 2.6377383197244844, 0.125]
bottle_H[0].rotation = [0, 0, 0]

solver.constraints = []

# The three tall units form a continuous storage run along the north wall.
# shelf_A and shelf_C correspond to the two shelves named in the criterion;
# placing the cabinet midway between them keeps the requested ordering.
shelf_A[0].position = [0.65, 4.035, 0.90]
shelf_A[0].rotation = [0, 0, radians(-90)]

cabinet[0].position = [2.105, 3.91, 0.45]
cabinet[0].rotation = [0, 0, radians(-90)]

shelf_C[0].position = [3.56, 4.035, 0.90]
shelf_C[0].rotation = [0, 0, radians(-90)]

# A low shelf, a storage box, and the oven use the south wall. This leaves the
# center aisle, the west-wall window, and the east-wall door approach clear.
shelf_B[0].position = [0.55, 0.15, 0.45]
shelf_B[0].rotation = [0, 0, radians(90)]

box[0].position = [1.35, 0.14, 0.11]
box[0].rotation = [0, 0, radians(90)]

oven[0].position = [3.40, 0.30, 0.45]
oven[0].rotation = [0, 0, radians(90)]

# Objects arranged across the top of shelf_A without footprint overlap.
lamp_A[0].position = [0.34, 4.03, 2.01]
lamp_A[0].rotation = [0, 0, radians(-90)]

book_A[0].position = [0.61, 4.03, 1.82]
book_A[0].rotation = [0, 0, radians(-90)]

bottle_A[0].position = [0.82, 4.03, 1.94]
bottle_A[0].rotation = [0, 0, radians(-90)]

food_A[0].position = [0.99, 4.03, 1.92]
food_A[0].rotation = [0, 0, radians(-90)]

# Objects arranged across the top of the low south shelf.
book_B[0].position = [0.25, 0.15, 0.92]
book_B[0].rotation = [0, 0, radians(90)]

bottle_B[0].position = [0.40, 0.15, 1.025]
bottle_B[0].rotation = [0, 0, radians(90)]

can_A[0].position = [0.50, 0.15, 0.96]
can_A[0].rotation = [0, 0, radians(90)]

food_B[0].position = [0.64, 0.15, 1.025]
food_B[0].rotation = [0, 0, radians(90)]

bottle_F[0].position = [0.85, 0.15, 1.035]
bottle_F[0].rotation = [0, 0, radians(90)]

# The microwave and faucet share the cabinet worktop.
faucet[0].position = [1.76, 3.91, 1.06]
faucet[0].rotation = [0, 0, radians(-90)]

microwave[0].position = [2.28, 3.91, 1.05]
microwave[0].rotation = [0, 0, radians(-90)]

# Compact pantry items are grouped on top of the microwave.
book_C[0].position = [2.12, 3.84, 1.22]
book_C[0].rotation = [0, 0, radians(-90)]

bottle_C[0].position = [2.29, 3.79, 1.35]
bottle_C[0].rotation = [0, 0, radians(-90)]

bottle_D[0].position = [2.41, 3.79, 1.325]
bottle_D[0].rotation = [0, 0, radians(-90)]

can_B[0].position = [2.28, 4.03, 1.26]
can_B[0].rotation = [0, 0, radians(-90)]

bottle_E[0].position = [2.42, 4.03, 1.355]
bottle_E[0].rotation = [0, 0, radians(-90)]

# Objects arranged across shelf_C. book_E is stacked on book_D to conserve
# usable shelf area while keeping both books fully supported.
lamp_B[0].position = [3.25, 4.03, 2.025]
lamp_B[0].rotation = [0, 0, radians(-90)]

book_D[0].position = [3.47, 4.03, 1.82]
book_D[0].rotation = [0, 0, radians(-90)]

book_E[0].position = [3.47, 4.03, 1.86]
book_E[0].rotation = [0, 0, radians(-90)]

bottle_G[0].position = [3.62, 4.03, 1.945]
bottle_G[0].rotation = [0, 0, radians(-90)]

food_C[0].position = [3.78, 4.03, 1.93]
food_C[0].rotation = [0, 0, radians(-90)]

bottle_H[0].position = [3.96, 4.03, 1.925]
bottle_H[0].rotation = [0, 0, radians(-90)]

# The larger pan sits directly on the oven; the smaller pan is nested above it.
pan_B[0].position = [3.40, 0.30, 0.97]
pan_B[0].rotation = [0, 0, radians(90)]

pan_A[0].position = [3.40, 0.30, 1.10]
pan_A[0].rotation = [0, 0, radians(90)]


# Fixed pose references make the intended coordinates and rotations resilient
# to later feasibility adjustment.
north_facing_reference = AssetInstance(
    position=[2.105, 2.105, 0.0],
    rotation=[0, 0, radians(-90)]
)
south_facing_reference = AssetInstance(
    position=[2.105, 2.105, 0.0],
    rotation=[0, 0, radians(90)]
)

# Floor furniture: wall contact is the primary positional relationship.
solver.against_wall(shelf_A[0], walls[1])
solver.distance_constraint(
    shelf_A[0], AssetInstance(position=[0.65, 4.035, 0.90]),
    0, 0, weight=10
)
solver.point_towards(shelf_A[0], north_facing_reference)

solver.against_wall(cabinet[0], walls[1])
# Equal spacing from the two flanking shelves encodes "between the shelves."
solver.distance_constraint(cabinet[0], shelf_A[0], 1.45, 1.48, weight=10)
solver.distance_constraint(cabinet[0], shelf_C[0], 1.45, 1.48, weight=10)
solver.distance_constraint(
    cabinet[0], AssetInstance(position=[2.105, 3.91, 0.45]),
    0, 0, weight=10
)
solver.align_with(cabinet[0], shelf_A[0])

solver.against_wall(shelf_C[0], walls[1])
solver.distance_constraint(
    shelf_C[0], AssetInstance(position=[3.56, 4.035, 0.90]),
    0, 0, weight=10
)
solver.align_with(shelf_C[0], shelf_A[0])

solver.against_wall(shelf_B[0], walls[3])
solver.distance_constraint(
    shelf_B[0], AssetInstance(position=[0.55, 0.15, 0.45]),
    0, 0, weight=10
)
solver.point_towards(shelf_B[0], south_facing_reference)

solver.against_wall(box[0], walls[3])
solver.distance_constraint(
    box[0], AssetInstance(position=[1.35, 0.14, 0.11]),
    0, 0, weight=10
)
solver.align_with(box[0], shelf_B[0])

solver.against_wall(oven[0], walls[3])
solver.distance_constraint(
    oven[0], AssetInstance(position=[3.40, 0.30, 0.45]),
    0, 0, weight=10
)
solver.align_with(oven[0], shelf_B[0])

# Keep the closest north-wall unit away from the east-wall doorway centered at
# (4.21, 2.93), preserving a clear approach from the room.
door_reference = AssetInstance(position=[4.21, 2.93, 0.90])
solver.distance_constraint(shelf_C[0], door_reference, 1.0, None, weight=10)


# shelf_A contents: every item has vertical support, a fixed position, and an
# orientation relationship with its supporting shelf.
solver.on_top_of(lamp_A[0], shelf_A[0])
solver.distance_constraint(
    lamp_A[0], AssetInstance(position=[0.34, 4.03, 2.01]),
    0, 0, weight=10
)
solver.align_with(lamp_A[0], shelf_A[0])

solver.on_top_of(book_A[0], shelf_A[0])
solver.distance_constraint(
    book_A[0], AssetInstance(position=[0.61, 4.03, 1.82]),
    0, 0, weight=10
)
solver.align_with(book_A[0], shelf_A[0])

solver.on_top_of(bottle_A[0], shelf_A[0])
solver.distance_constraint(
    bottle_A[0], AssetInstance(position=[0.82, 4.03, 1.94]),
    0, 0, weight=10
)
solver.align_with(bottle_A[0], shelf_A[0])

solver.on_top_of(food_A[0], shelf_A[0])
solver.distance_constraint(
    food_A[0], AssetInstance(position=[0.99, 4.03, 1.92]),
    0, 0, weight=10
)
solver.align_with(food_A[0], shelf_A[0])


# shelf_B contents.
solver.on_top_of(book_B[0], shelf_B[0])
solver.distance_constraint(
    book_B[0], AssetInstance(position=[0.25, 0.15, 0.92]),
    0, 0, weight=10
)
solver.align_with(book_B[0], shelf_B[0])

solver.on_top_of(bottle_B[0], shelf_B[0])
solver.distance_constraint(
    bottle_B[0], AssetInstance(position=[0.40, 0.15, 1.025]),
    0, 0, weight=10
)
solver.align_with(bottle_B[0], shelf_B[0])

solver.on_top_of(can_A[0], shelf_B[0])
solver.distance_constraint(
    can_A[0], AssetInstance(position=[0.50, 0.15, 0.96]),
    0, 0, weight=10
)
solver.align_with(can_A[0], shelf_B[0])

solver.on_top_of(food_B[0], shelf_B[0])
solver.distance_constraint(
    food_B[0], AssetInstance(position=[0.64, 0.15, 1.025]),
    0, 0, weight=10
)
solver.align_with(food_B[0], shelf_B[0])

solver.on_top_of(bottle_F[0], shelf_B[0])
solver.distance_constraint(
    bottle_F[0], AssetInstance(position=[0.85, 0.15, 1.035]),
    0, 0, weight=10
)
solver.align_with(bottle_F[0], shelf_B[0])


# Cabinet worktop contents.
solver.on_top_of(faucet[0], cabinet[0])
solver.distance_constraint(
    faucet[0], AssetInstance(position=[1.76, 3.91, 1.06]),
    0, 0, weight=10
)
solver.align_with(faucet[0], cabinet[0])

solver.on_top_of(microwave[0], cabinet[0])
solver.distance_constraint(
    microwave[0], AssetInstance(position=[2.28, 3.91, 1.05]),
    0, 0, weight=10
)
solver.align_with(microwave[0], cabinet[0])


# Microwave-top contents.
solver.on_top_of(book_C[0], microwave[0])
solver.distance_constraint(
    book_C[0], AssetInstance(position=[2.12, 3.84, 1.22]),
    0, 0, weight=10
)
solver.align_with(book_C[0], microwave[0])

solver.on_top_of(bottle_C[0], microwave[0])
solver.distance_constraint(
    bottle_C[0], AssetInstance(position=[2.29, 3.79, 1.35]),
    0, 0, weight=10
)
solver.align_with(bottle_C[0], microwave[0])

solver.on_top_of(bottle_D[0], microwave[0])
solver.distance_constraint(
    bottle_D[0], AssetInstance(position=[2.41, 3.79, 1.325]),
    0, 0, weight=10
)
solver.align_with(bottle_D[0], microwave[0])

solver.on_top_of(can_B[0], microwave[0])
solver.distance_constraint(
    can_B[0], AssetInstance(position=[2.28, 4.03, 1.26]),
    0, 0, weight=10
)
solver.align_with(can_B[0], microwave[0])

solver.on_top_of(bottle_E[0], microwave[0])
solver.distance_constraint(
    bottle_E[0], AssetInstance(position=[2.42, 4.03, 1.355]),
    0, 0, weight=10
)
solver.align_with(bottle_E[0], microwave[0])


# shelf_C contents.
solver.on_top_of(lamp_B[0], shelf_C[0])
solver.distance_constraint(
    lamp_B[0], AssetInstance(position=[3.25, 4.03, 2.025]),
    0, 0, weight=10
)
solver.align_with(lamp_B[0], shelf_C[0])

solver.on_top_of(book_D[0], shelf_C[0])
solver.distance_constraint(
    book_D[0], AssetInstance(position=[3.47, 4.03, 1.82]),
    0, 0, weight=10
)
solver.align_with(book_D[0], shelf_C[0])

solver.on_top_of(book_E[0], book_D[0])
solver.distance_constraint(
    book_E[0], AssetInstance(position=[3.47, 4.03, 1.86]),
    0, 0, weight=10
)
solver.align_with(book_E[0], book_D[0])

solver.on_top_of(bottle_G[0], shelf_C[0])
solver.distance_constraint(
    bottle_G[0], AssetInstance(position=[3.62, 4.03, 1.945]),
    0, 0, weight=10
)
solver.align_with(bottle_G[0], shelf_C[0])

solver.on_top_of(food_C[0], shelf_C[0])
solver.distance_constraint(
    food_C[0], AssetInstance(position=[3.78, 4.03, 1.93]),
    0, 0, weight=10
)
solver.align_with(food_C[0], shelf_C[0])

solver.on_top_of(bottle_H[0], shelf_C[0])
solver.distance_constraint(
    bottle_H[0], AssetInstance(position=[3.96, 4.03, 1.925]),
    0, 0, weight=10
)
solver.align_with(bottle_H[0], shelf_C[0])


# Nested cookware on the oven.
solver.on_top_of(pan_B[0], oven[0])
solver.distance_constraint(
    pan_B[0], AssetInstance(position=[3.40, 0.30, 0.97]),
    0, 0, weight=10
)
solver.align_with(pan_B[0], oven[0])

solver.on_top_of(pan_A[0], pan_B[0])
solver.distance_constraint(
    pan_A[0], AssetInstance(position=[3.40, 0.30, 1.10]),
    0, 0, weight=10
)
solver.align_with(pan_A[0], pan_B[0])

solver.constraints = []
bottle_E[0].position = [2.4200000762939453, 4.03000020980835, 1.3549998998641968]
bottle_E[0].rotation = [0, 0, -1.5708437591434772]
bottle_E[0].optimize = 2
book_D[0].position = [3.4700000286102295, 4.03000020980835, 1.8199999332427979]
book_D[0].rotation = [0, 0, -1.5711042238496926]
book_D[0].optimize = 2
bottle_H[0].position = [3.9600000381469727, 4.03000020980835, 1.9249999523162842]
bottle_H[0].rotation = [0, 0, -1.5710872334461912]
bottle_H[0].optimize = 2
faucet[0].position = [1.7599999904632568, 3.9100000858306885, 1.059999942779541]
faucet[0].rotation = [0, 0, -1.5707756291752246]
faucet[0].optimize = 2
book_E[0].position = [3.4700000286102295, 4.03000020980835, 1.8599998950958252]
book_E[0].rotation = [0, 0, -1.5699433236074511]
book_E[0].optimize = 2
pan_A[0].position = [3.4000000953674316, 0.30000001192092896, 1.0999999046325684]
pan_A[0].rotation = [0, 0, 1.570957338958633]
pan_A[0].optimize = 2
book_C[0].position = [2.119999885559082, 3.8399999141693115, 1.21999990940094]
book_C[0].rotation = [0, 0, -1.5708437591434772]
book_C[0].optimize = 2
lamp_A[0].position = [0.3400000035762787, 4.03000020980835, 2.009999990463257]
lamp_A[0].rotation = [0, 0, -1.5710138101381688]
lamp_A[0].optimize = 2
book_A[0].position = [0.6100000143051147, 4.03000020980835, 1.8199999332427979]
book_A[0].rotation = [0, 0, -1.5710138101381688]
book_A[0].optimize = 2
pan_B[0].position = [3.4000000953674316, 0.30000001192092896, 0.9699999690055847]
pan_B[0].rotation = [0, 0, 1.5707182241492903]
pan_B[0].optimize = 2
lamp_B[0].position = [3.25, 4.03000020980835, 2.0249998569488525]
lamp_B[0].rotation = [0, 0, -1.5710872334461912]
lamp_B[0].optimize = 2
bottle_G[0].position = [3.619999885559082, 4.03000020980835, 1.9449999332427979]
bottle_G[0].rotation = [0, 0, -1.5710872334461912]
bottle_G[0].optimize = 2
book_B[0].position = [0.25, 0.15000000596046448, 0.9199999570846558]
book_B[0].rotation = [0, 0, 1.570505474909683]
book_B[0].optimize = 2
food_C[0].position = [3.7799999713897705, 4.03000020980835, 1.9299999475479126]
food_C[0].rotation = [0, 0, -1.5710872334461912]
food_C[0].optimize = 2
bottle_F[0].position = [0.8500000238418579, 0.15000000596046448, 1.034999966621399]
bottle_F[0].rotation = [0, 0, 1.570505474909683]
bottle_F[0].optimize = 2
bottle_D[0].position = [2.4100000858306885, 3.7899999618530273, 1.3199999332427979]
bottle_D[0].rotation = [0, 0, -1.5708437591434772]
bottle_D[0].optimize = 2
food_A[0].position = [0.9900000095367432, 4.03000020980835, 1.9199999570846558]
food_A[0].rotation = [0, 0, -1.5710138101381688]
food_A[0].optimize = 2
cabinet[0].position = [2.1050000190734863, 3.911623239517212, 0.44999998807907104]
cabinet[0].rotation = [0, 0, -1.570839166339431]
cabinet[0].optimize = 2
can_B[0].position = [2.2799999713897705, 4.03000020980835, 1.2599998712539673]
can_B[0].rotation = [0, 0, -1.5708437591434772]
can_B[0].optimize = 2
oven[0].position = [3.4000000953674316, 0.29999247193336487, 0.44999998807907104]
oven[0].rotation = [0, 0, 1.570770422904829]
oven[0].optimize = 2
food_B[0].position = [0.6399999856948853, 0.15000000596046448, 1.024999976158142]
food_B[0].rotation = [0, 0, 1.570505474909683]
food_B[0].optimize = 2
shelf_A[0].position = [0.6499999761581421, 4.036585807800293, 0.8999999761581421]
shelf_A[0].rotation = [0, 0, -1.5707604921096114]
shelf_A[0].optimize = 2
can_A[0].position = [0.5, 0.15000000596046448, 0.9599999785423279]
can_A[0].rotation = [0, 0, 1.570505474909683]
can_A[0].optimize = 2
bottle_B[0].position = [0.4000000059604645, 0.15000000596046448, 1.024999976158142]
bottle_B[0].rotation = [0, 0, 1.570505474909683]
bottle_B[0].optimize = 2
box[0].position = [1.350000023841858, 0.1400138884782791, 0.10999999940395355]
box[0].rotation = [0, 0, 1.5707864291853433]
box[0].optimize = 2
bottle_C[0].position = [2.2899999618530273, 3.7899999618530273, 1.3499999046325684]
bottle_C[0].rotation = [0, 0, -1.5708437591434772]
bottle_C[0].optimize = 2
bottle_A[0].position = [0.8199999928474426, 4.03000020980835, 1.9399999380111694]
bottle_A[0].rotation = [0, 0, -1.5710138101381688]
bottle_A[0].optimize = 2
microwave[0].position = [2.2799999713897705, 3.9100000858306885, 1.0499999523162842]
microwave[0].rotation = [0, 0, -1.5705963073551708]
microwave[0].optimize = 2
shelf_C[0].position = [3.559999942779541, 4.036637306213379, 0.8999999761581421]
shelf_C[0].rotation = [0, 0, -1.570727119239904]
shelf_C[0].optimize = 2
shelf_B[0].position = [0.550000011920929, 0.15001918375492096, 0.44999998807907104]
shelf_B[0].rotation = [0, 0, 1.5708656033341115]
shelf_B[0].optimize = 2

