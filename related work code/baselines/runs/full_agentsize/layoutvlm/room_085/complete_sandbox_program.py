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
    Wall(corner1=[4.72, 0.00, 0.00], corner2=[4.72, 2.72, 0.00]),
    Wall(corner1=[4.72, 2.72, 0.00], corner2=[4.22, 2.72, 0.00]),
    Wall(corner1=[4.22, 2.72, 0.00], corner2=[4.22, 4.72, 0.00]),
    Wall(corner1=[4.22, 4.72, 0.00], corner2=[0.00, 4.72, 0.00]),
    Wall(corner1=[0.00, 4.72, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.72, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
oven = Assets(description="oven", size=[0.60, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
microwave = Assets(description="microwave", size=[0.40, 0.52, 0.30], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.62, 1.80, 0.90], placements=[AssetInstance() for _ in range(1)])
can = Assets(description="can", size=[0.08, 0.08, 0.12], placements=[AssetInstance() for _ in range(1)])
plate_A = Assets(description="plate", size=[0.27, 0.27, 0.03], placements=[AssetInstance() for _ in range(1)])
box_A = Assets(description="box", size=[0.22, 0.30, 0.12], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="lamp", size=[0.32, 0.32, 0.25], placements=[AssetInstance() for _ in range(1)])
bottle_A = Assets(description="bottle", size=[0.08, 0.08, 0.28], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="bottle", size=[0.07, 0.07, 0.24], placements=[AssetInstance() for _ in range(1)])
box_B = Assets(description="box", size=[0.16, 0.24, 0.08], placements=[AssetInstance() for _ in range(1)])
cup_A = Assets(description="cup", size=[0.09, 0.09, 0.10], placements=[AssetInstance() for _ in range(1)])
plate_B = Assets(description="plate", size=[0.24, 0.24, 0.03], placements=[AssetInstance() for _ in range(1)])
box_C = Assets(description="box", size=[0.22, 0.32, 0.14], placements=[AssetInstance() for _ in range(1)])
pot_A = Assets(description="pot", size=[0.22, 0.28, 0.16], placements=[AssetInstance() for _ in range(1)])
box_D = Assets(description="box", size=[0.14, 0.20, 0.09], placements=[AssetInstance() for _ in range(1)])
pan = Assets(description="pan", size=[0.28, 0.46, 0.09], placements=[AssetInstance() for _ in range(1)])
cup_B = Assets(description="cup", size=[0.10, 0.10, 0.11], placements=[AssetInstance() for _ in range(1)])
food = Assets(description="food", size=[0.12, 0.18, 0.08], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.28, 0.28, 0.22], placements=[AssetInstance() for _ in range(1)])
pot_B = Assets(description="pot", size=[0.20, 0.24, 0.14], placements=[AssetInstance() for _ in range(1)])
lamp_C = Assets(description="lamp", size=[0.35, 0.35, 0.28], placements=[AssetInstance() for _ in range(1)])
bottle_C = Assets(description="bottle", size=[0.09, 0.09, 0.30], placements=[AssetInstance() for _ in range(1)])
book = Assets(description="book", size=[0.16, 0.22, 0.03], placements=[AssetInstance() for _ in range(1)])
pot_C = Assets(description="pot", size=[0.26, 0.32, 0.19], placements=[AssetInstance() for _ in range(1)])
cup_C = Assets(description="cup", size=[0.09, 0.09, 0.10], placements=[AssetInstance() for _ in range(1)])
cup_D = Assets(description="cup", size=[0.08, 0.08, 0.10], placements=[AssetInstance() for _ in range(1)])
cup_E = Assets(description="cup", size=[0.10, 0.10, 0.12], placements=[AssetInstance() for _ in range(1)])
box_E = Assets(description="box", size=[0.20, 0.28, 0.11], placements=[AssetInstance() for _ in range(1)])
cup_F = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.62, 1.50, 0.90], placements=[AssetInstance() for _ in range(1)])
lamp_D = Assets(description="lamp", size=[0.30, 0.30, 0.24], placements=[AssetInstance() for _ in range(1)])
cabinet_C = Assets(description="cabinet", size=[0.62, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
pot_D = Assets(description="pot", size=[0.17, 0.20, 0.12], placements=[AssetInstance() for _ in range(1)])
cup_G = Assets(description="cup", size=[0.08, 0.08, 0.09], placements=[AssetInstance() for _ in range(1)])
cup_H = Assets(description="cup", size=[0.11, 0.11, 0.12], placements=[AssetInstance() for _ in range(1)])
faucet = Assets(description="faucet", size=[0.20, 0.05, 0.30], placements=[AssetInstance() for _ in range(1)])
bottle_D = Assets(description="bottle", size=[0.08, 0.08, 0.25], placements=[AssetInstance() for _ in range(1)])
box_F = Assets(description="box", size=[0.25, 0.36, 0.18], placements=[AssetInstance() for _ in range(1)])
bottle_E = Assets(description="bottle", size=[0.10, 0.10, 0.32], placements=[AssetInstance() for _ in range(1)])
refrigerator = Assets(description="refrigerator", size=[0.75, 0.90, 1.85], placements=[AssetInstance() for _ in range(1)])

oven[0].instance_id = 'oven_0'
microwave[0].instance_id = 'microwave_0'
cabinet_A[0].instance_id = 'cabinet_A_0'
can[0].instance_id = 'can_0'
plate_A[0].instance_id = 'plate_A_0'
box_A[0].instance_id = 'box_A_0'
lamp_A[0].instance_id = 'lamp_A_0'
bottle_A[0].instance_id = 'bottle_A_0'
bottle_B[0].instance_id = 'bottle_B_0'
box_B[0].instance_id = 'box_B_0'
cup_A[0].instance_id = 'cup_A_0'
plate_B[0].instance_id = 'plate_B_0'
box_C[0].instance_id = 'box_C_0'
pot_A[0].instance_id = 'pot_A_0'
box_D[0].instance_id = 'box_D_0'
pan[0].instance_id = 'pan_0'
cup_B[0].instance_id = 'cup_B_0'
food[0].instance_id = 'food_0'
lamp_B[0].instance_id = 'lamp_B_0'
pot_B[0].instance_id = 'pot_B_0'
lamp_C[0].instance_id = 'lamp_C_0'
bottle_C[0].instance_id = 'bottle_C_0'
book[0].instance_id = 'book_0'
pot_C[0].instance_id = 'pot_C_0'
cup_C[0].instance_id = 'cup_C_0'
cup_D[0].instance_id = 'cup_D_0'
cup_E[0].instance_id = 'cup_E_0'
box_E[0].instance_id = 'box_E_0'
cup_F[0].instance_id = 'cup_F_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
lamp_D[0].instance_id = 'lamp_D_0'
cabinet_C[0].instance_id = 'cabinet_C_0'
pot_D[0].instance_id = 'pot_D_0'
cup_G[0].instance_id = 'cup_G_0'
cup_H[0].instance_id = 'cup_H_0'
faucet[0].instance_id = 'faucet_0'
bottle_D[0].instance_id = 'bottle_D_0'
box_F[0].instance_id = 'box_F_0'
bottle_E[0].instance_id = 'bottle_E_0'
refrigerator[0].instance_id = 'refrigerator_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

oven[0].position = [1.2924108341048408, 0.6139774576998044, 0.45]
oven[0].rotation = [0, 0, 0]
microwave[0].position = [0.7211982110752773, 3.5333359799414197, 0.15]
microwave[0].rotation = [0, 0, 0]
cabinet_A[0].position = [0.3830721761135136, 2.5246290178171087, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
can[0].position = [1.3694014600060649, 2.754477900468853, 0.06]
can[0].rotation = [0, 0, 0]
plate_A[0].position = [0.6907447908013166, 3.405894170446171, 0.0125]
plate_A[0].rotation = [0, 0, 0]
box_A[0].position = [3.9999996509625295, 4.043452534651761, 0.06]
box_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [0.42756197706313687, 1.3254484627061478, 0.125]
lamp_A[0].rotation = [0, 0, 0]
bottle_A[0].position = [1.9274056216300055, 4.2511926818993295, 0.14]
bottle_A[0].rotation = [0, 0, 0]
bottle_B[0].position = [1.0799832508555518, 3.30457439452309, 0.12]
bottle_B[0].rotation = [0, 0, 0]
box_B[0].position = [0.4704250180588424, 0.6109580629006673, 0.04]
box_B[0].rotation = [0, 0, 0]
cup_A[0].position = [0.6637086397246978, 2.5710962130203385, 0.05]
cup_A[0].rotation = [0, 0, 0]
plate_B[0].position = [2.2812047534241393, 4.523888416320086, 0.0125]
plate_B[0].rotation = [0, 0, 0]
box_C[0].position = [1.087083739369598, 0.7448709121588771, 0.07]
box_C[0].rotation = [0, 0, 0]
pot_A[0].position = [2.7760841114616044, 0.9810494380218683, 0.08]
pot_A[0].rotation = [0, 0, 0]
box_D[0].position = [2.1923777300916996, 4.6052326807194195, 0.045]
box_D[0].rotation = [0, 0, 0]
pan[0].position = [0.9398480824369335, 4.013658039220867, 0.045]
pan[0].rotation = [0, 0, 0]
cup_B[0].position = [0.19763678254178227, 0.40526935217565424, 0.055]
cup_B[0].rotation = [0, 0, 0]
food[0].position = [3.256024393506339, 4.366034224539564, 0.04]
food[0].rotation = [0, 0, 0]
lamp_B[0].position = [2.033887100887725, 0.20151086725989953, 0.11]
lamp_B[0].rotation = [0, 0, 0]
pot_B[0].position = [1.4501784785652514, 3.5716980922693495, 0.07]
pot_B[0].rotation = [0, 0, 0]
lamp_C[0].position = [4.045219789703722, 1.1797837039912245, 0.14]
lamp_C[0].rotation = [0, 0, 0]
bottle_C[0].position = [2.189221813314474, 2.2424218365669133, 0.15]
bottle_C[0].rotation = [0, 0, 0]
book[0].position = [0.8441000370430886, 3.921713031973632, 0.015]
book[0].rotation = [0, 0, 0]
pot_C[0].position = [2.7599490028376197, 3.696461746947199, 0.095]
pot_C[0].rotation = [0, 0, 0]
cup_C[0].position = [3.3529136583339425, 0.9630562915691769, 0.05]
cup_C[0].rotation = [0, 0, 0]
cup_D[0].position = [0.19725932309598818, 2.9857635165638627, 0.05]
cup_D[0].rotation = [0, 0, 0]
cup_E[0].position = [2.1349982622052197, 0.16727326124448633, 0.06]
cup_E[0].rotation = [0, 0, 0]
box_E[0].position = [1.1843781522533916, 1.749039711431269, 0.055]
box_E[0].rotation = [0, 0, 0]
cup_F[0].position = [4.234388712544468, 1.3047728580912943, 0.055]
cup_F[0].rotation = [0, 0, 0]
cabinet_B[0].position = [0.48125359697157155, 1.65231890772466, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
lamp_D[0].position = [2.3943308418811924, 1.16666897065784, 0.12]
lamp_D[0].rotation = [0, 0, 0]
cabinet_C[0].position = [0.32557256649540506, 3.2335065156265177, 0.45]
cabinet_C[0].rotation = [0, 0, 0]
pot_D[0].position = [3.4123563564041697, 2.1195295665615608, 0.06]
pot_D[0].rotation = [0, 0, 0]
cup_G[0].position = [3.1941262128679817, 1.430686815382355, 0.045]
cup_G[0].rotation = [0, 0, 0]
cup_H[0].position = [0.03321612414895231, 0.9862835693636944, 0.06]
cup_H[0].rotation = [0, 0, 0]
faucet[0].position = [0.10858217100349316, 1.9808456105156051, 0.15]
faucet[0].rotation = [0, 0, 0]
bottle_D[0].position = [2.354423505665014, 3.609185768026024, 0.125]
bottle_D[0].rotation = [0, 0, 0]
box_F[0].position = [3.2390707322009535, 2.595255248650923, 0.09]
box_F[0].rotation = [0, 0, 0]
bottle_E[0].position = [1.2245625662129551, 0.9100673982652653, 0.16]
bottle_E[0].rotation = [0, 0, 0]
refrigerator[0].position = [4.381845968461591, 0.36529484925934375, 0.925]
refrigerator[0].rotation = [0, 0, 0]
oven[0].position = [1.2924108341048408, 0.6139774576998044, 0.45]
oven[0].rotation = [0, 0, 0]
microwave[0].position = [0.7211982110752773, 3.5333359799414197, 0.15]
microwave[0].rotation = [0, 0, 0]
cabinet_A[0].position = [0.3830721761135136, 2.5246290178171087, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
can[0].position = [1.3694014600060649, 2.754477900468853, 0.06]
can[0].rotation = [0, 0, 0]
plate_A[0].position = [0.6907447908013166, 3.405894170446171, 0.0125]
plate_A[0].rotation = [0, 0, 0]
box_A[0].position = [3.9999996509625295, 4.043452534651761, 0.06]
box_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [0.42756197706313687, 1.3254484627061478, 0.125]
lamp_A[0].rotation = [0, 0, 0]
bottle_A[0].position = [1.9274056216300055, 4.2511926818993295, 0.14]
bottle_A[0].rotation = [0, 0, 0]
bottle_B[0].position = [1.0799832508555518, 3.30457439452309, 0.12]
bottle_B[0].rotation = [0, 0, 0]
box_B[0].position = [0.4704250180588424, 0.6109580629006673, 0.04]
box_B[0].rotation = [0, 0, 0]
cup_A[0].position = [0.6637086397246978, 2.5710962130203385, 0.05]
cup_A[0].rotation = [0, 0, 0]
plate_B[0].position = [2.2812047534241393, 4.523888416320086, 0.0125]
plate_B[0].rotation = [0, 0, 0]
box_C[0].position = [1.087083739369598, 0.7448709121588771, 0.07]
box_C[0].rotation = [0, 0, 0]
pot_A[0].position = [2.7760841114616044, 0.9810494380218683, 0.08]
pot_A[0].rotation = [0, 0, 0]
box_D[0].position = [2.1923777300916996, 4.6052326807194195, 0.045]
box_D[0].rotation = [0, 0, 0]
pan[0].position = [0.9398480824369335, 4.013658039220867, 0.045]
pan[0].rotation = [0, 0, 0]
cup_B[0].position = [0.19763678254178227, 0.40526935217565424, 0.055]
cup_B[0].rotation = [0, 0, 0]
food[0].position = [3.256024393506339, 4.366034224539564, 0.04]
food[0].rotation = [0, 0, 0]
lamp_B[0].position = [2.033887100887725, 0.20151086725989953, 0.11]
lamp_B[0].rotation = [0, 0, 0]
pot_B[0].position = [1.4501784785652514, 3.5716980922693495, 0.07]
pot_B[0].rotation = [0, 0, 0]
lamp_C[0].position = [4.045219789703722, 1.1797837039912245, 0.14]
lamp_C[0].rotation = [0, 0, 0]
bottle_C[0].position = [2.189221813314474, 2.2424218365669133, 0.15]
bottle_C[0].rotation = [0, 0, 0]
book[0].position = [0.8441000370430886, 3.921713031973632, 0.015]
book[0].rotation = [0, 0, 0]
pot_C[0].position = [2.7599490028376197, 3.696461746947199, 0.095]
pot_C[0].rotation = [0, 0, 0]
cup_C[0].position = [3.3529136583339425, 0.9630562915691769, 0.05]
cup_C[0].rotation = [0, 0, 0]
cup_D[0].position = [0.19725932309598818, 2.9857635165638627, 0.05]
cup_D[0].rotation = [0, 0, 0]
cup_E[0].position = [2.1349982622052197, 0.16727326124448633, 0.06]
cup_E[0].rotation = [0, 0, 0]
box_E[0].position = [1.1843781522533916, 1.749039711431269, 0.055]
box_E[0].rotation = [0, 0, 0]
cup_F[0].position = [4.234388712544468, 1.3047728580912943, 0.055]
cup_F[0].rotation = [0, 0, 0]
cabinet_B[0].position = [0.48125359697157155, 1.65231890772466, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
lamp_D[0].position = [2.3943308418811924, 1.16666897065784, 0.12]
lamp_D[0].rotation = [0, 0, 0]
cabinet_C[0].position = [0.32557256649540506, 3.2335065156265177, 0.45]
cabinet_C[0].rotation = [0, 0, 0]
pot_D[0].position = [3.4123563564041697, 2.1195295665615608, 0.06]
pot_D[0].rotation = [0, 0, 0]
cup_G[0].position = [3.1941262128679817, 1.430686815382355, 0.045]
cup_G[0].rotation = [0, 0, 0]
cup_H[0].position = [0.03321612414895231, 0.9862835693636944, 0.06]
cup_H[0].rotation = [0, 0, 0]
faucet[0].position = [0.10858217100349316, 1.9808456105156051, 0.15]
faucet[0].rotation = [0, 0, 0]
bottle_D[0].position = [2.354423505665014, 3.609185768026024, 0.125]
bottle_D[0].rotation = [0, 0, 0]
box_F[0].position = [3.2390707322009535, 2.595255248650923, 0.09]
box_F[0].rotation = [0, 0, 0]
bottle_E[0].position = [1.2245625662129551, 0.9100673982652653, 0.16]
bottle_E[0].rotation = [0, 0, 0]
refrigerator[0].position = [4.381845968461591, 0.36529484925934375, 0.925]
refrigerator[0].rotation = [0, 0, 0]

solver.constraints = []

# Helper functions keep the initial placements and their semantic constraints consistent.
# Exact-position anchors are given high weight so that countertop objects remain in
# their intended non-overlapping work zones when the solver adjusts the layout.
def _facing_target(x, y, z, yaw_degrees):
    return AssetInstance(
        position=[
            x + cos(radians(yaw_degrees)),
            y + sin(radians(yaw_degrees)),
            z,
        ]
    )


def _constrain_position_and_facing(asset_instance, x, y, z, yaw_degrees):
    anchor = AssetInstance(position=[x, y, z])
    solver.distance_constraint(
        asset_instance, anchor, 0.0, 0.0, weight=10
    )
    solver.point_towards(
        asset_instance,
        _facing_target(x, y, z, yaw_degrees),
    )


def _place_floor_asset(asset, x, y, yaw_degrees, wall=None):
    z = asset.size[2] / 2.0
    asset[0].position = [x, y, z]
    asset[0].rotation = [0, 0, radians(yaw_degrees)]

    # Wall contact is listed first for perimeter fixtures because it is the
    # primary spatial requirement.
    if wall is not None:
        solver.against_wall(asset[0], wall)

    _constrain_position_and_facing(asset[0], x, y, z, yaw_degrees)


def _place_on_surface(
    asset, support, x, y, support_top_z, yaw_degrees
):
    z = support_top_z + asset.size[2] / 2.0
    asset[0].position = [x, y, z]
    asset[0].rotation = [0, 0, radians(yaw_degrees)]

    solver.on_top_of(asset[0], support[0])
    _constrain_position_and_facing(asset[0], x, y, z, yaw_degrees)


# Arrange the three cabinets as an L-shaped counter along the upper walls.
# Their 0.62 m depths project into the room. Cabinet C is moved to the inset
# right wall because all three cabinets cannot fit along the 4.22 m top wall.
_place_floor_asset(cabinet_A, 0.95, 4.41, -90, walls[3])
_place_floor_asset(cabinet_B, 2.60, 4.41, -90, walls[3])
_place_floor_asset(cabinet_C, 3.91, 3.50, 180, walls[2])

# Place the tall refrigerator and oven on the lower wall. This keeps the entire
# door approach at x=4.72, y=1.21 clear and leaves a broad central aisle.
_place_floor_asset(refrigerator, 0.48, 0.45, 90, walls[5])
_place_floor_asset(oven, 1.30, 0.30, 90, walls[5])

# All cabinets have a 0.90 m-high work surface.
_counter_top = 0.90

# Cabinet A: microwave zone and grouped storage items.
_place_on_surface(microwave, cabinet_A, 0.30, 4.41, _counter_top, -90)
_place_on_surface(box_F, cabinet_A, 0.68, 4.28, _counter_top, -90)
_place_on_surface(lamp_C, cabinet_A, 1.02, 4.28, _counter_top, -90)
_place_on_surface(pot_C, cabinet_A, 1.36, 4.28, _counter_top, -90)
_place_on_surface(box_C, cabinet_A, 1.66, 4.28, _counter_top, -90)
_place_on_surface(bottle_E, cabinet_A, 0.66, 4.62, _counter_top, -90)
_place_on_surface(cup_H, cabinet_A, 0.88, 4.62, _counter_top, -90)
_place_on_surface(can, cabinet_A, 1.08, 4.62, _counter_top, -90)

# Cabinet B: cookware and serving items, with larger objects in the front row.
_place_on_surface(pan, cabinet_B, 1.99, 4.40, _counter_top, -90)
_place_on_surface(pot_A, cabinet_B, 2.31, 4.27, _counter_top, -90)
_place_on_surface(pot_B, cabinet_B, 2.57, 4.27, _counter_top, -90)
_place_on_surface(lamp_A, cabinet_B, 2.87, 4.27, _counter_top, -90)
_place_on_surface(box_A, cabinet_B, 3.16, 4.27, _counter_top, -90)
_place_on_surface(plate_A, cabinet_B, 2.30, 4.57, _counter_top, -90)
_place_on_surface(plate_B, cabinet_B, 2.61, 4.57, _counter_top, -90)
_place_on_surface(bottle_A, cabinet_B, 2.83, 4.60, _counter_top, -90)
_place_on_surface(bottle_B, cabinet_B, 3.00, 4.60, _counter_top, -90)

# Cups placed on plates form functional place settings and avoid consuming
# additional counter area.
_plate_top = _counter_top + plate_A.size[2]
_place_on_surface(cup_A, plate_A, 2.30, 4.57, _plate_top, -90)

_plate_b_top = _counter_top + plate_B.size[2]
_place_on_surface(cup_B, plate_B, 2.61, 4.57, _plate_b_top, -90)

# Cabinet C: compact rows run down the inset wall, leaving the corner and aisle
# unobstructed. Objects face toward the room (-x).
_place_on_surface(lamp_B, cabinet_C, 3.76, 2.98, _counter_top, 180)
_place_on_surface(box_B, cabinet_C, 4.10, 2.98, _counter_top, 180)
_place_on_surface(lamp_D, cabinet_C, 3.76, 3.32, _counter_top, 180)
_place_on_surface(box_E, cabinet_C, 4.09, 3.32, _counter_top, 180)
_place_on_surface(pot_D, cabinet_C, 3.71, 3.61, _counter_top, 180)
_place_on_surface(box_D, cabinet_C, 3.94, 3.61, _counter_top, 180)
_place_on_surface(food, cabinet_C, 4.14, 3.61, _counter_top, 180)
_place_on_surface(book, cabinet_C, 3.70, 3.86, _counter_top, 180)
_place_on_surface(faucet, cabinet_C, 3.93, 3.86, _counter_top, 180)
_place_on_surface(bottle_C, cabinet_C, 4.14, 3.86, _counter_top, 180)
_place_on_surface(bottle_D, cabinet_C, 4.15, 3.16, _counter_top, 180)

# Stack the remaining small cups neatly on the storage boxes. Each cup still
# receives its own exact position and orientation constraints.
_box_b_top = _counter_top + box_B.size[2]
_place_on_surface(cup_E, box_B, 4.10, 2.93, _box_b_top, 180)
_place_on_surface(cup_F, box_B, 4.10, 3.04, _box_b_top, 180)

_box_e_top = _counter_top + box_E.size[2]
_place_on_surface(cup_C, box_E, 4.04, 3.25, _box_e_top, 180)
_place_on_surface(cup_D, box_E, 4.13, 3.38, _box_e_top, 180)

_box_d_top = _counter_top + box_D.size[2]
_place_on_surface(cup_G, box_D, 3.94, 3.61, _box_d_top, 180)

solver.constraints = []
bottle_E[0].position = [0.6600000262260437, 4.619999885559082, 1.059999942779541]
bottle_E[0].rotation = [0, 0, -1.5582299555380688]
bottle_E[0].optimize = 2
box_A[0].position = [3.1600000858306885, 4.269999980926514, 0.9599999785423279]
box_A[0].rotation = [0, 0, -1.5582299555380688]
box_A[0].optimize = 2
cup_F[0].position = [4.099999904632568, 3.0399999618530273, 1.034999966621399]
cup_F[0].rotation = [0, 0, -3.1290262823329655]
cup_F[0].optimize = 2
cabinet_B[0].position = [2.5999999046325684, 4.410714149475098, 0.44999998807907104]
cabinet_B[0].rotation = [0, 0, -1.570796280751915]
cabinet_B[0].optimize = 2
bottle_D[0].position = [4.150000095367432, 3.1600000858306885, 1.024999976158142]
bottle_D[0].rotation = [0, 0, -3.1290262823329655]
bottle_D[0].optimize = 2
pot_D[0].position = [3.7100000381469727, 3.609999895095825, 0.9599999785423279]
pot_D[0].rotation = [0, 0, -3.1290262823329655]
pot_D[0].optimize = 2
can[0].position = [1.0800000429153442, 4.619999885559082, 0.9599999785423279]
can[0].rotation = [0, 0, -1.5582299555380688]
can[0].optimize = 2
book[0].position = [3.700000047683716, 3.859999895095825, 0.9149999618530273]
book[0].rotation = [0, 0, -3.1290262823329655]
book[0].optimize = 2
bottle_C[0].position = [4.139999866485596, 3.859999895095825, 1.0499999523162842]
bottle_C[0].rotation = [0, 0, -3.1290262823329655]
bottle_C[0].optimize = 2
plate_B[0].position = [2.609999895095825, 4.570000171661377, 0.9149999618530273]
plate_B[0].rotation = [0, 0, -1.5550883628776802]
plate_B[0].optimize = 2
lamp_C[0].position = [1.0199999809265137, 4.28000020980835, 1.0399999618530273]
lamp_C[0].rotation = [0, 0, -1.5582299555380688]
lamp_C[0].optimize = 2
food[0].position = [4.139999866485596, 3.609999895095825, 0.9399999976158142]
food[0].rotation = [0, 0, -3.1290262823329655]
food[0].optimize = 2
cabinet_C[0].position = [3.9107136726379395, 3.5, 0.44999998807907104]
cabinet_C[0].rotation = [0, 0, 3.141592629079739]
cabinet_C[0].optimize = 2
cup_A[0].position = [2.299999952316284, 4.570000171661377, 0.9799999594688416]
cup_A[0].rotation = [0, 0, -1.5582299555380688]
cup_A[0].optimize = 2
cup_G[0].position = [3.940000057220459, 3.609999895095825, 1.034999966621399]
cup_G[0].rotation = [0, 0, -3.1290262823329655]
cup_G[0].optimize = 2
pot_C[0].position = [1.3600000143051147, 4.28000020980835, 0.9950000047683716]
pot_C[0].rotation = [0, 0, -1.5582299555380688]
pot_C[0].optimize = 2
box_E[0].position = [4.090000152587891, 3.319999933242798, 0.9549999833106995]
box_E[0].rotation = [0, 0, -3.122743098190977]
box_E[0].optimize = 2
faucet[0].position = [3.930000066757202, 3.859999895095825, 1.0499999523162842]
faucet[0].rotation = [0, 0, -3.1290262823329655]
faucet[0].optimize = 2
refrigerator[0].position = [0.47999998927116394, 0.3749999403953552, 0.925000011920929]
refrigerator[0].rotation = [0, 0, 1.5707963487023222]
refrigerator[0].optimize = 2
lamp_D[0].position = [3.759999990463257, 3.319999933242798, 1.0199999809265137]
lamp_D[0].rotation = [0, 0, -3.1290262823329655]
lamp_D[0].optimize = 2
pan[0].position = [1.9900000095367432, 4.400000095367432, 0.9449999928474426]
pan[0].rotation = [0, 0, -1.5582299555380688]
pan[0].optimize = 2
pot_B[0].position = [2.569999933242798, 4.269999980926514, 0.9699999690055847]
pot_B[0].rotation = [0, 0, -1.5582299555380688]
pot_B[0].optimize = 2
pot_A[0].position = [2.309999942779541, 4.269999980926514, 0.9799999594688416]
pot_A[0].rotation = [0, 0, -1.5582299555380688]
pot_A[0].optimize = 2
lamp_A[0].position = [2.869999885559082, 4.269999980926514, 1.024999976158142]
lamp_A[0].rotation = [0, 0, -1.5582299555380688]
lamp_A[0].optimize = 2
lamp_B[0].position = [3.759999990463257, 2.9800000190734863, 1.0099999904632568]
lamp_B[0].rotation = [0, 0, -3.1290262823329655]
lamp_B[0].optimize = 2
cup_E[0].position = [4.099999904632568, 2.930000066757202, 1.0399999618530273]
cup_E[0].rotation = [0, 0, -3.1290262823329655]
cup_E[0].optimize = 2
cup_D[0].position = [4.130000114440918, 3.380000114440918, 1.059999942779541]
cup_D[0].rotation = [0, 0, -3.1290262823329655]
cup_D[0].optimize = 2
plate_A[0].position = [2.299999952316284, 4.570000171661377, 0.9149999618530273]
plate_A[0].rotation = [0, 0, -1.5550883628776802]
plate_A[0].optimize = 2
box_F[0].position = [0.6800000071525574, 4.28000020980835, 0.9900000095367432]
box_F[0].rotation = [0, 0, -1.5582299555380688]
box_F[0].optimize = 2
box_C[0].position = [1.659999966621399, 4.28000020980835, 0.9699999690055847]
box_C[0].rotation = [0, 0, -1.5582299555380688]
box_C[0].optimize = 2
cup_C[0].position = [4.039999961853027, 3.25, 1.059999942779541]
cup_C[0].rotation = [0, 0, -3.1290262823329655]
cup_C[0].optimize = 2
oven[0].position = [1.2999999523162842, 0.2999999225139618, 0.44999998807907104]
oven[0].rotation = [0, 0, 1.5707963472486868]
oven[0].optimize = 2
cup_H[0].position = [0.8799999952316284, 4.619999885559082, 0.9599999785423279]
cup_H[0].rotation = [0, 0, -1.5582299555380688]
cup_H[0].optimize = 2
bottle_B[0].position = [3.0, 4.599999904632568, 1.0199999809265137]
bottle_B[0].rotation = [0, 0, -1.5582299555380688]
bottle_B[0].optimize = 2
cup_B[0].position = [2.609999895095825, 4.570000171661377, 0.98499995470047]
cup_B[0].rotation = [0, 0, -1.5582299555380688]
cup_B[0].optimize = 2
bottle_A[0].position = [2.8299999237060547, 4.599999904632568, 1.0399999618530273]
bottle_A[0].rotation = [0, 0, -1.5582299555380688]
bottle_A[0].optimize = 2
cabinet_A[0].position = [0.949999988079071, 4.410714626312256, 0.44999998807907104]
cabinet_A[0].rotation = [0, 0, -1.57079628294087]
cabinet_A[0].optimize = 2
microwave[0].position = [0.30000001192092896, 4.409999847412109, 1.0499999523162842]
microwave[0].rotation = [0, 0, -1.5582299555380688]
microwave[0].optimize = 2
box_D[0].position = [3.940000057220459, 3.609999895095825, 0.9449999928474426]
box_D[0].rotation = [0, 0, -3.125884689672577]
box_D[0].optimize = 2
box_B[0].position = [4.099999904632568, 2.9800000190734863, 0.9399999976158142]
box_B[0].rotation = [0, 0, -3.122743098190977]
box_B[0].optimize = 2

