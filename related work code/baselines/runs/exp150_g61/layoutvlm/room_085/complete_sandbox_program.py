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
oven = Assets(description="oven", size=[0.65, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
microwave = Assets(description="microwave", size=[0.40, 0.50, 0.30], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.60, 1.80, 0.90], placements=[AssetInstance() for _ in range(1)])
can = Assets(description="can", size=[0.07, 0.07, 0.12], placements=[AssetInstance() for _ in range(1)])
plate_A = Assets(description="plate", size=[0.26, 0.26, 0.03], placements=[AssetInstance() for _ in range(1)])
box_A = Assets(description="box", size=[0.12, 0.20, 0.30], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="lamp", size=[0.22, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
bottle_A = Assets(description="bottle", size=[0.08, 0.08, 0.30], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="bottle", size=[0.07, 0.07, 0.25], placements=[AssetInstance() for _ in range(1)])
box_B = Assets(description="box", size=[0.10, 0.16, 0.24], placements=[AssetInstance() for _ in range(1)])
cup_A = Assets(description="cup", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
plate_B = Assets(description="plate", size=[0.22, 0.22, 0.02], placements=[AssetInstance() for _ in range(1)])
box_C = Assets(description="box", size=[0.18, 0.25, 0.12], placements=[AssetInstance() for _ in range(1)])
pot_A = Assets(description="pot", size=[0.24, 0.32, 0.20], placements=[AssetInstance() for _ in range(1)])
box_D = Assets(description="box", size=[0.12, 0.18, 0.26], placements=[AssetInstance() for _ in range(1)])
pan = Assets(description="pan", size=[0.48, 0.28, 0.07], placements=[AssetInstance() for _ in range(1)])
cup_B = Assets(description="cup", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
food = Assets(description="food", size=[0.12, 0.16, 0.07], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.22, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
pot_B = Assets(description="pot", size=[0.22, 0.28, 0.16], placements=[AssetInstance() for _ in range(1)])
lamp_C = Assets(description="lamp", size=[0.22, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
bottle_C = Assets(description="bottle", size=[0.09, 0.09, 0.28], placements=[AssetInstance() for _ in range(1)])
book = Assets(description="book", size=[0.28, 0.21, 0.03], placements=[AssetInstance() for _ in range(1)])
pot_C = Assets(description="pot", size=[0.18, 0.24, 0.14], placements=[AssetInstance() for _ in range(1)])
cup_C = Assets(description="cup", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
cup_D = Assets(description="cup", size=[0.08, 0.11, 0.09], placements=[AssetInstance() for _ in range(1)])
cup_E = Assets(description="cup", size=[0.08, 0.11, 0.09], placements=[AssetInstance() for _ in range(1)])
box_E = Assets(description="box", size=[0.15, 0.22, 0.10], placements=[AssetInstance() for _ in range(1)])
cup_F = Assets(description="cup", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.60, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
lamp_D = Assets(description="lamp", size=[0.22, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
cabinet_C = Assets(description="cabinet", size=[0.35, 1.20, 0.80], placements=[AssetInstance() for _ in range(1)])
pot_D = Assets(description="pot", size=[0.17, 0.22, 0.13], placements=[AssetInstance() for _ in range(1)])
cup_G = Assets(description="cup", size=[0.08, 0.11, 0.09], placements=[AssetInstance() for _ in range(1)])
cup_H = Assets(description="cup", size=[0.08, 0.11, 0.09], placements=[AssetInstance() for _ in range(1)])
faucet = Assets(description="faucet", size=[0.25, 0.16, 0.35], placements=[AssetInstance() for _ in range(1)])
bottle_D = Assets(description="bottle", size=[0.08, 0.08, 0.26], placements=[AssetInstance() for _ in range(1)])
box_F = Assets(description="box", size=[0.14, 0.20, 0.28], placements=[AssetInstance() for _ in range(1)])
bottle_E = Assets(description="bottle", size=[0.07, 0.07, 0.22], placements=[AssetInstance() for _ in range(1)])
refrigerator = Assets(description="refrigerator", size=[0.72, 0.75, 1.85], placements=[AssetInstance() for _ in range(1)])

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

oven[0].position = [3.50113186521799, 0.369979711538411, 0.45]
oven[0].rotation = [0, 0, 0]
microwave[0].position = [0.5607510830721106, 0.7801426314886887, 0.15]
microwave[0].rotation = [0, 0, 0]
cabinet_A[0].position = [1.790331971698447, 3.037044918579503, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
can[0].position = [2.9051716288311376, 1.0056778006972515, 0.06]
can[0].rotation = [0, 0, 0]
plate_A[0].position = [3.745832327464891, 4.537082586393177, 0.0125]
plate_A[0].rotation = [0, 0, 0]
box_A[0].position = [4.153188720743951, 0.8397549687744444, 0.15]
box_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [3.497973403313495, 0.2499555822055965, 0.125]
lamp_A[0].rotation = [0, 0, 0]
bottle_A[0].position = [4.1962967230669825, 3.567291566134412, 0.15]
bottle_A[0].rotation = [0, 0, 0]
bottle_B[0].position = [0.2913597040199161, 3.6801565031855183, 0.125]
bottle_B[0].rotation = [0, 0, 0]
box_B[0].position = [3.8607046637690616, 0.4590545483177247, 0.12]
box_B[0].rotation = [0, 0, 0]
cup_A[0].position = [4.180879154879092, 0.7777694413871664, 0.05]
cup_A[0].rotation = [0, 0, 0]
plate_B[0].position = [1.1104729321708402, 3.34111999748321, 0.01]
plate_B[0].rotation = [0, 0, 0]
box_C[0].position = [1.5093199996684796, 2.04068676569158, 0.06]
box_C[0].rotation = [0, 0, 0]
pot_A[0].position = [0.08474022145842708, 3.989397513660027, 0.1]
pot_A[0].rotation = [0, 0, 0]
box_D[0].position = [1.6320503109192401, 3.041746751783087, 0.13]
box_D[0].rotation = [0, 0, 0]
pan[0].position = [1.1446162043828214, 1.7734535745308275, 0.035]
pan[0].rotation = [0, 0, 0]
cup_B[0].position = [0.7390973234848232, 2.7696682448808048, 0.05]
cup_B[0].rotation = [0, 0, 0]
food[0].position = [2.9700066613801743, 1.806920792794359, 0.035]
food[0].rotation = [0, 0, 0]
lamp_B[0].position = [1.2084033514119792, 3.4594581564305096, 0.125]
lamp_B[0].rotation = [0, 0, 0]
pot_B[0].position = [3.4926487620156528, 3.58709055424263, 0.08]
pot_B[0].rotation = [0, 0, 0]
lamp_C[0].position = [0.8061903781774794, 2.826631584780461, 0.125]
lamp_C[0].rotation = [0, 0, 0]
bottle_C[0].position = [2.430405739648045, 2.2110860850612357, 0.14]
bottle_C[0].rotation = [0, 0, 0]
book[0].position = [0.31215115577498437, 3.6272210918896746, 0.0125]
book[0].rotation = [0, 0, 0]
pot_C[0].position = [4.141202840096315, 0.7575714803411384, 0.07]
pot_C[0].rotation = [0, 0, 0]
cup_C[0].position = [3.7518694746218624, 0.022175694662669138, 0.05]
cup_C[0].rotation = [0, 0, 0]
cup_D[0].position = [1.7409757986131467, 0.4572177600497059, 0.045]
cup_D[0].rotation = [0, 0, 0]
cup_E[0].position = [3.43338712035284, 2.5368263456162645, 0.045]
cup_E[0].rotation = [0, 0, 0]
box_E[0].position = [1.9060139134089598, 3.8911041428241275, 0.05]
box_E[0].rotation = [0, 0, 0]
cup_F[0].position = [4.564505717454796, 1.5021281867910419, 0.05]
cup_F[0].rotation = [0, 0, 0]
cabinet_B[0].position = [2.9956435536533035, 0.03085977160009193, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
lamp_D[0].position = [4.081537763473761, 2.6387322843085093, 0.125]
lamp_D[0].rotation = [0, 0, 0]
cabinet_C[0].position = [2.1726214975497404, 0.1400157006903258, 0.4]
cabinet_C[0].rotation = [0, 0, 0]
pot_D[0].position = [3.362620919520473, 3.10808440234162, 0.065]
pot_D[0].rotation = [0, 0, 0]
cup_G[0].position = [1.4938185045000247, 2.7873297036285556, 0.045]
cup_G[0].rotation = [0, 0, 0]
cup_H[0].position = [2.746880985557299, 2.8414706362505946, 0.045]
cup_H[0].rotation = [0, 0, 0]
faucet[0].position = [2.575360742595389, 2.0012587531069395, 0.175]
faucet[0].rotation = [0, 0, 0]
bottle_D[0].position = [0.09915875714980317, 0.32252003116889577, 0.13]
bottle_D[0].rotation = [0, 0, 0]
box_F[0].position = [2.673337430317538, 2.577056622697047, 0.14]
box_F[0].rotation = [0, 0, 0]
bottle_E[0].position = [4.508619566193856, 1.0149496751623228, 0.11]
bottle_E[0].rotation = [0, 0, 0]
refrigerator[0].position = [1.0887497548758267, 2.738482665418756, 0.925]
refrigerator[0].rotation = [0, 0, 0]
oven[0].position = [3.50113186521799, 0.369979711538411, 0.45]
oven[0].rotation = [0, 0, 0]
microwave[0].position = [0.5607510830721106, 0.7801426314886887, 0.15]
microwave[0].rotation = [0, 0, 0]
cabinet_A[0].position = [1.790331971698447, 3.037044918579503, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
can[0].position = [2.9051716288311376, 1.0056778006972515, 0.06]
can[0].rotation = [0, 0, 0]
plate_A[0].position = [3.745832327464891, 4.537082586393177, 0.0125]
plate_A[0].rotation = [0, 0, 0]
box_A[0].position = [4.153188720743951, 0.8397549687744444, 0.15]
box_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [3.497973403313495, 0.2499555822055965, 0.125]
lamp_A[0].rotation = [0, 0, 0]
bottle_A[0].position = [4.1962967230669825, 3.567291566134412, 0.15]
bottle_A[0].rotation = [0, 0, 0]
bottle_B[0].position = [0.2913597040199161, 3.6801565031855183, 0.125]
bottle_B[0].rotation = [0, 0, 0]
box_B[0].position = [3.8607046637690616, 0.4590545483177247, 0.12]
box_B[0].rotation = [0, 0, 0]
cup_A[0].position = [4.180879154879092, 0.7777694413871664, 0.05]
cup_A[0].rotation = [0, 0, 0]
plate_B[0].position = [1.1104729321708402, 3.34111999748321, 0.01]
plate_B[0].rotation = [0, 0, 0]
box_C[0].position = [1.5093199996684796, 2.04068676569158, 0.06]
box_C[0].rotation = [0, 0, 0]
pot_A[0].position = [0.08474022145842708, 3.989397513660027, 0.1]
pot_A[0].rotation = [0, 0, 0]
box_D[0].position = [1.6320503109192401, 3.041746751783087, 0.13]
box_D[0].rotation = [0, 0, 0]
pan[0].position = [1.1446162043828214, 1.7734535745308275, 0.035]
pan[0].rotation = [0, 0, 0]
cup_B[0].position = [0.7390973234848232, 2.7696682448808048, 0.05]
cup_B[0].rotation = [0, 0, 0]
food[0].position = [2.9700066613801743, 1.806920792794359, 0.035]
food[0].rotation = [0, 0, 0]
lamp_B[0].position = [1.2084033514119792, 3.4594581564305096, 0.125]
lamp_B[0].rotation = [0, 0, 0]
pot_B[0].position = [3.4926487620156528, 3.58709055424263, 0.08]
pot_B[0].rotation = [0, 0, 0]
lamp_C[0].position = [0.8061903781774794, 2.826631584780461, 0.125]
lamp_C[0].rotation = [0, 0, 0]
bottle_C[0].position = [2.430405739648045, 2.2110860850612357, 0.14]
bottle_C[0].rotation = [0, 0, 0]
book[0].position = [0.31215115577498437, 3.6272210918896746, 0.0125]
book[0].rotation = [0, 0, 0]
pot_C[0].position = [4.141202840096315, 0.7575714803411384, 0.07]
pot_C[0].rotation = [0, 0, 0]
cup_C[0].position = [3.7518694746218624, 0.022175694662669138, 0.05]
cup_C[0].rotation = [0, 0, 0]
cup_D[0].position = [1.7409757986131467, 0.4572177600497059, 0.045]
cup_D[0].rotation = [0, 0, 0]
cup_E[0].position = [3.43338712035284, 2.5368263456162645, 0.045]
cup_E[0].rotation = [0, 0, 0]
box_E[0].position = [1.9060139134089598, 3.8911041428241275, 0.05]
box_E[0].rotation = [0, 0, 0]
cup_F[0].position = [4.564505717454796, 1.5021281867910419, 0.05]
cup_F[0].rotation = [0, 0, 0]
cabinet_B[0].position = [2.9956435536533035, 0.03085977160009193, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
lamp_D[0].position = [4.081537763473761, 2.6387322843085093, 0.125]
lamp_D[0].rotation = [0, 0, 0]
cabinet_C[0].position = [2.1726214975497404, 0.1400157006903258, 0.4]
cabinet_C[0].rotation = [0, 0, 0]
pot_D[0].position = [3.362620919520473, 3.10808440234162, 0.065]
pot_D[0].rotation = [0, 0, 0]
cup_G[0].position = [1.4938185045000247, 2.7873297036285556, 0.045]
cup_G[0].rotation = [0, 0, 0]
cup_H[0].position = [2.746880985557299, 2.8414706362505946, 0.045]
cup_H[0].rotation = [0, 0, 0]
faucet[0].position = [2.575360742595389, 2.0012587531069395, 0.175]
faucet[0].rotation = [0, 0, 0]
bottle_D[0].position = [0.09915875714980317, 0.32252003116889577, 0.13]
bottle_D[0].rotation = [0, 0, 0]
box_F[0].position = [2.673337430317538, 2.577056622697047, 0.14]
box_F[0].rotation = [0, 0, 0]
bottle_E[0].position = [4.508619566193856, 1.0149496751623228, 0.11]
bottle_E[0].rotation = [0, 0, 0]
refrigerator[0].position = [1.0887497548758267, 2.738482665418756, 0.925]
refrigerator[0].rotation = [0, 0, 0]

solver.constraints = []

# Keep the entrance at (4.72, 1.21) and the central circulation area clear.
# Cabinets form a west-wall preparation run and a short north-wall worktop.
# Coordinates below use bounding-box centers, including the vertical coordinate.

def place_floor_unit(asset_group, x, y, yaw_degrees, wall_index):
    instance = asset_group[0]
    z = asset_group.size[2] / 2
    instance.position = [x, y, z]
    instance.rotation = [0, 0, radians(yaw_degrees)]

    solver.against_wall(instance, walls[wall_index])
    solver.distance_constraint(
        instance, AssetInstance(position=[x, y, z]),
        0, 0, weight=10
    )
    solver.align_with(
        instance,
        AssetInstance(position=[x, y, z], rotation=[0, 0, radians(yaw_degrees)])
    )


place_floor_unit(cabinet_A, 0.30, 1.30, 0, 4)
place_floor_unit(cabinet_B, 0.30, 2.85, 0, 4)
place_floor_unit(cabinet_C, 2.50, 4.545, -90, 3)
place_floor_unit(oven, 1.30, 0.325, 90, 5)
place_floor_unit(refrigerator, 0.36, 4.10, 0, 4)


def place_on_surface(asset_group, support_group, x, y, yaw_degrees=0):
    instance = asset_group[0]
    support = support_group[0]
    z = (
        support.position[2]
        + support_group.size[2] / 2
        + asset_group.size[2] / 2
    )
    instance.position = [x, y, z]
    instance.rotation = [0, 0, radians(yaw_degrees)]

    # Establish the support relation first. The fixed center preserves the
    # nonoverlapping arrangement within that support's usable footprint.
    solver.on_top_of(instance, support)
    solver.distance_constraint(
        instance, AssetInstance(position=[x, y, z]),
        0, 0, weight=10
    )
    solver.align_with(
        instance,
        AssetInstance(position=[x, y, z], rotation=[0, 0, radians(yaw_degrees)])
    )


# West preparation counter: two separated lanes of utensils and provisions.
for item_group, px, py in [
    (plate_A,  0.16, 0.60),
    (bottle_A, 0.45, 0.60),
    (can,      0.45, 0.80),
    (box_A,    0.15, 0.95),
    (box_B,    0.45, 0.95),
    (lamp_A,   0.15, 1.30),
    (bottle_B, 0.45, 1.30),
    (plate_B,  0.15, 1.65),
    (cup_A,    0.45, 1.65),
    (box_C,    0.15, 2.00),
    (cup_B,    0.45, 2.00),
]:
    place_on_surface(item_group, cabinet_A, px, py)

# Food rests on the plate, not directly on the counter.
place_on_surface(food, plate_A, 0.16, 0.60)

# Microwave and cookware occupy distinct areas of the second counter.
place_on_surface(microwave, cabinet_B, 0.30, 2.58)
for item_group, px, py in [
    (pot_B,  0.15, 3.02),
    (lamp_B, 0.45, 3.02),
    (pot_C,  0.15, 3.32),
    (lamp_C, 0.45, 3.31),
]:
    place_on_surface(item_group, cabinet_B, px, py)

# Six cups fit in two columns on the microwave's top, with gaps between rows.
for item_group, px, py in [
    (cup_C, 0.20, 2.43),
    (cup_D, 0.40, 2.43),
    (cup_E, 0.20, 2.58),
    (cup_F, 0.40, 2.58),
    (cup_G, 0.20, 2.73),
    (cup_H, 0.40, 2.73),
]:
    place_on_surface(item_group, microwave, px, py)

# The pan and pot are separated front-to-back on the oven's top.
place_on_surface(pan, oven, 1.30, 0.17)
place_on_surface(pot_A, oven, 1.30, 0.49)

# Shallow north-wall worktop. Face the faucet toward the room.
place_on_surface(faucet, cabinet_C, 2.08, 4.60, -90)
place_on_surface(pot_D, cabinet_C, 2.40, 4.55)
place_on_surface(book, cabinet_C, 2.70, 4.55)
place_on_surface(lamp_D, cabinet_C, 2.96, 4.55)

# Less frequently used packaged goods occupy the refrigerator top.
for item_group, px, py in [
    (box_D,    0.16, 3.93),
    (box_F,    0.40, 3.93),
    (bottle_C, 0.62, 3.90),
    (box_E,    0.16, 4.24),
    (bottle_D, 0.40, 4.25),
    (bottle_E, 0.58, 4.25),
]:
    place_on_surface(item_group, refrigerator, px, py)

solver.constraints = []
cup_F[0].position = [0.4000000059604645, 2.5799999237060547, 1.2499998807907104]
cup_F[0].rotation = [0, 0, 0.01256637125682779]
cup_F[0].optimize = 2
microwave[0].position = [0.30000001192092896, 2.5799999237060547, 1.0499999523162842]
microwave[0].rotation = [0, 0, 0.031415925765816845]
microwave[0].optimize = 2
bottle_C[0].position = [0.6200000047683716, 3.9000000953674316, 1.9900000095367432]
bottle_C[0].rotation = [0, 0, 0.01256637125682779]
bottle_C[0].optimize = 2
pot_B[0].position = [0.15000000596046448, 3.0199999809265137, 0.9799999594688416]
pot_B[0].rotation = [0, 0, 0.01256637125682779]
pot_B[0].optimize = 2
plate_B[0].position = [0.15000000596046448, 1.649999976158142, 0.9099999666213989]
plate_B[0].rotation = [0, 0, 0.01256637125682779]
plate_B[0].optimize = 2
bottle_B[0].position = [0.44999998807907104, 1.2999999523162842, 1.024999976158142]
bottle_B[0].rotation = [0, 0, 0.01256637125682779]
bottle_B[0].optimize = 2
box_D[0].position = [0.1599999964237213, 3.930000066757202, 1.9800000190734863]
box_D[0].rotation = [0, 0, 0.01256637125682779]
box_D[0].optimize = 2
pot_A[0].position = [1.2999999523162842, 0.49000000953674316, 1.0]
pot_A[0].rotation = [0, 0, 0.01256637125682779]
pot_A[0].optimize = 2
cup_A[0].position = [0.44999998807907104, 1.649999976158142, 0.949999988079071]
cup_A[0].rotation = [0, 0, 0.01256637125682779]
cup_A[0].optimize = 2
cabinet_A[0].position = [0.300161212682724, 1.2999999523162842, 0.44999998807907104]
cabinet_A[0].rotation = [0, 0, 6.959812313301341e-05]
cabinet_A[0].optimize = 2
refrigerator[0].position = [0.3599572777748108, 4.099999904632568, 0.925000011920929]
refrigerator[0].rotation = [0, 0, -4.2782981378407526e-05]
refrigerator[0].optimize = 2
can[0].position = [0.44999998807907104, 0.800000011920929, 0.9599999785423279]
can[0].rotation = [0, 0, 0.01256637125682779]
can[0].optimize = 2
pot_C[0].position = [0.15272225439548492, 3.143083095550537, 0.9699999690055847]
pot_C[0].rotation = [0, 0, 0.01256637125682779]
pot_C[0].optimize = 2
cup_C[0].position = [0.20000000298023224, 2.430000066757202, 1.2499998807907104]
cup_C[0].rotation = [0, 0, 0.01256637125682779]
cup_C[0].optimize = 2
food[0].position = [0.1599999964237213, 0.6000000238418579, 0.9649999737739563]
food[0].rotation = [0, 0, 0.01256637125682779]
food[0].optimize = 2
plate_A[0].position = [0.1599999964237213, 0.6000000238418579, 0.9149999618530273]
plate_A[0].rotation = [0, 0, 0.0157079639172164]
plate_A[0].optimize = 2
lamp_D[0].position = [2.9600000381469727, 4.550000190734863, 0.925000011920929]
lamp_D[0].rotation = [0, 0, 0.01256637125682779]
lamp_D[0].optimize = 2
cabinet_B[0].position = [0.6045446395874023, 2.8499999046325684, 0.44999998807907104]
cabinet_B[0].rotation = [0, 0, -1.555410465680798]
cabinet_B[0].optimize = 2
lamp_B[0].position = [0.44999998807907104, 3.0199999809265137, 1.024999976158142]
lamp_B[0].rotation = [0, 0, 0.01256637125682779]
lamp_B[0].optimize = 2
bottle_A[0].position = [0.44999998807907104, 0.6000000238418579, 1.0499999523162842]
bottle_A[0].rotation = [0, 0, 0.01256637125682779]
bottle_A[0].optimize = 2
cabinet_C[0].position = [2.5, 4.545774459838867, 0.4000000059604645]
cabinet_C[0].rotation = [0, 0, -1.5706981922956074]
cabinet_C[0].optimize = 2
cup_E[0].position = [0.20000000298023224, 2.5799999237060547, 1.244999885559082]
cup_E[0].rotation = [0, 0, 0.01256637125682779]
cup_E[0].optimize = 2
box_A[0].position = [0.15000000596046448, 0.949999988079071, 1.0499999523162842]
box_A[0].rotation = [0, 0, 0.01256637125682779]
box_A[0].optimize = 2
cup_H[0].position = [0.4000000059604645, 2.7300000190734863, 1.244999885559082]
cup_H[0].rotation = [0, 0, 0.01256637125682779]
cup_H[0].optimize = 2
lamp_C[0].position = [0.4524973928928375, 3.147695779800415, 1.024999976158142]
lamp_C[0].rotation = [0, 0, 0.01256637125682779]
lamp_C[0].optimize = 2
pan[0].position = [1.2999999523162842, 0.17000000178813934, 0.9350000023841858]
pan[0].rotation = [0, 0, 0.01256637125682779]
pan[0].optimize = 2
faucet[0].position = [2.0799999237060547, 4.599999904632568, 0.9750000238418579]
faucet[0].rotation = [0, 0, -1.5582299555380688]
faucet[0].optimize = 2
book[0].position = [2.700000047683716, 4.550000190734863, 0.8149999976158142]
book[0].rotation = [0, 0, 0.01256637125682779]
book[0].optimize = 2
oven[0].position = [1.2999999523162842, 0.32502201199531555, 0.44999998807907104]
oven[0].rotation = [0, 0, 1.5708677873704873]
oven[0].optimize = 2
pot_D[0].position = [2.4000000953674316, 4.550000190734863, 0.8650000095367432]
pot_D[0].rotation = [0, 0, 0.01256637125682779]
pot_D[0].optimize = 2
box_E[0].position = [0.1599999964237213, 4.239999771118164, 1.899999976158142]
box_E[0].rotation = [0, 0, 0.01256637125682779]
box_E[0].optimize = 2
box_B[0].position = [0.44999998807907104, 0.949999988079071, 1.0199999809265137]
box_B[0].rotation = [0, 0, 0.01256637125682779]
box_B[0].optimize = 2
box_F[0].position = [0.4000000059604645, 3.930000066757202, 1.9900000095367432]
box_F[0].rotation = [0, 0, 0.01256637125682779]
box_F[0].optimize = 2
bottle_E[0].position = [0.5799999833106995, 4.25, 1.9600000381469727]
bottle_E[0].rotation = [0, 0, 0.01256637125682779]
bottle_E[0].optimize = 2
cup_B[0].position = [0.44999998807907104, 2.0, 0.949999988079071]
cup_B[0].rotation = [0, 0, 0.01256637125682779]
cup_B[0].optimize = 2
cup_D[0].position = [0.4000000059604645, 2.430000066757202, 1.244999885559082]
cup_D[0].rotation = [0, 0, 0.01256637125682779]
cup_D[0].optimize = 2
cup_G[0].position = [0.20000000298023224, 2.7300000190734863, 1.244999885559082]
cup_G[0].rotation = [0, 0, 0.01256637125682779]
cup_G[0].optimize = 2
bottle_D[0].position = [0.4000000059604645, 4.25, 1.9800000190734863]
bottle_D[0].rotation = [0, 0, 0.01256637125682779]
bottle_D[0].optimize = 2
box_C[0].position = [0.15000000596046448, 2.0, 0.9599999785423279]
box_C[0].rotation = [0, 0, 0.01256637125682779]
box_C[0].optimize = 2
lamp_A[0].position = [0.15000000596046448, 1.2999999523162842, 1.024999976158142]
lamp_A[0].rotation = [0, 0, 0.01256637125682779]
lamp_A[0].optimize = 2

