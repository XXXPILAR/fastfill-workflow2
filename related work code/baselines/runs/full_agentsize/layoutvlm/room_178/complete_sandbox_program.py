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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[5.50, 0.00, 0.00]),
    Wall(corner1=[5.50, 0.00, 0.00], corner2=[5.50, 4.50, 0.00]),
    Wall(corner1=[5.50, 4.50, 0.00], corner2=[0.00, 4.50, 0.00]),
    Wall(corner1=[0.00, 4.50, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
wall_sconce_A = Assets(description="wall sconce", size=[0.22, 0.18, 0.38], placements=[AssetInstance() for _ in range(1)])
dining_chair_A = Assets(description="dining chair", size=[0.55, 0.48, 0.88], placements=[AssetInstance() for _ in range(1)])
candle_holder_A = Assets(description="candle holder", size=[0.12, 0.12, 0.24], placements=[AssetInstance() for _ in range(1)])
vase_A = Assets(description="vase", size=[0.24, 0.24, 0.42], placements=[AssetInstance() for _ in range(1)])
print_A = Assets(description="print", size=[0.03, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
taper_candle_A = Assets(description="taper candle", size=[0.02, 0.02, 0.25], placements=[AssetInstance() for _ in range(1)])
mirror = Assets(description="mirror", size=[0.04, 0.90, 1.20], placements=[AssetInstance() for _ in range(1)])
plant_stand = Assets(description="plant stand", size=[0.35, 0.35, 0.75], placements=[AssetInstance() for _ in range(1)])
wall_sconce_B = Assets(description="wall sconce", size=[0.22, 0.18, 0.38], placements=[AssetInstance() for _ in range(1)])
vase_B = Assets(description="vase", size=[0.20, 0.20, 0.34], placements=[AssetInstance() for _ in range(1)])
eucalyptus_sprig_A = Assets(description="eucalyptus sprig", size=[0.25, 0.35, 0.75], placements=[AssetInstance() for _ in range(1)])
rug = Assets(description="rug", size=[2.40, 3.20, 0.01], placements=[AssetInstance() for _ in range(1)])
dining_chair_B = Assets(description="dining chair", size=[0.55, 0.48, 0.88], placements=[AssetInstance() for _ in range(1)])
candle_holder_B = Assets(description="candle holder", size=[0.12, 0.12, 0.24], placements=[AssetInstance() for _ in range(1)])
print_B = Assets(description="print", size=[0.03, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
dining_chair_C = Assets(description="dining chair", size=[0.55, 0.48, 0.88], placements=[AssetInstance() for _ in range(1)])
clock = Assets(description="clock", size=[0.05, 0.40, 0.40], placements=[AssetInstance() for _ in range(1)])
dining_chair_D = Assets(description="dining chair", size=[0.55, 0.48, 0.88], placements=[AssetInstance() for _ in range(1)])
dining_chair_E = Assets(description="dining chair", size=[0.55, 0.48, 0.88], placements=[AssetInstance() for _ in range(1)])
apple_A = Assets(description="apple", size=[0.08, 0.08, 0.08], placements=[AssetInstance() for _ in range(1)])
eucalyptus_sprig_B = Assets(description="eucalyptus sprig", size=[0.22, 0.32, 0.70], placements=[AssetInstance() for _ in range(1)])
apple_B = Assets(description="apple", size=[0.08, 0.08, 0.08], placements=[AssetInstance() for _ in range(1)])
painting = Assets(description="painting", size=[0.04, 1.10, 0.80], placements=[AssetInstance() for _ in range(1)])
dining_table = Assets(description="dining table", size=[1.00, 2.10, 0.76], placements=[AssetInstance() for _ in range(1)])
print_C = Assets(description="print", size=[0.03, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
taper_candle_B = Assets(description="taper candle", size=[0.02, 0.02, 0.25], placements=[AssetInstance() for _ in range(1)])
fruit_bowl_A = Assets(description="fruit bowl", size=[0.34, 0.34, 0.12], placements=[AssetInstance() for _ in range(1)])
small_orange_fruit = Assets(description="small orange fruit", size=[0.07, 0.07, 0.07], placements=[AssetInstance() for _ in range(1)])
buffet_cabinet = Assets(description="buffet cabinet", size=[0.45, 1.80, 0.85], placements=[AssetInstance() for _ in range(1)])
fruit_bowl_B = Assets(description="fruit bowl", size=[0.30, 0.30, 0.11], placements=[AssetInstance() for _ in range(1)])
dining_chair_F = Assets(description="dining chair", size=[0.55, 0.48, 0.88], placements=[AssetInstance() for _ in range(1)])

wall_sconce_A[0].instance_id = 'wall_sconce_A_0'
dining_chair_A[0].instance_id = 'dining_chair_A_0'
candle_holder_A[0].instance_id = 'candle_holder_A_0'
vase_A[0].instance_id = 'vase_A_0'
print_A[0].instance_id = 'print_A_0'
taper_candle_A[0].instance_id = 'taper_candle_A_0'
mirror[0].instance_id = 'mirror_0'
plant_stand[0].instance_id = 'plant_stand_0'
wall_sconce_B[0].instance_id = 'wall_sconce_B_0'
vase_B[0].instance_id = 'vase_B_0'
eucalyptus_sprig_A[0].instance_id = 'eucalyptus_sprig_A_0'
rug[0].instance_id = 'rug_0'
dining_chair_B[0].instance_id = 'dining_chair_B_0'
candle_holder_B[0].instance_id = 'candle_holder_B_0'
print_B[0].instance_id = 'print_B_0'
dining_chair_C[0].instance_id = 'dining_chair_C_0'
clock[0].instance_id = 'clock_0'
dining_chair_D[0].instance_id = 'dining_chair_D_0'
dining_chair_E[0].instance_id = 'dining_chair_E_0'
apple_A[0].instance_id = 'apple_A_0'
eucalyptus_sprig_B[0].instance_id = 'eucalyptus_sprig_B_0'
apple_B[0].instance_id = 'apple_B_0'
painting[0].instance_id = 'painting_0'
dining_table[0].instance_id = 'dining_table_0'
print_C[0].instance_id = 'print_C_0'
taper_candle_B[0].instance_id = 'taper_candle_B_0'
fruit_bowl_A[0].instance_id = 'fruit_bowl_A_0'
small_orange_fruit[0].instance_id = 'small_orange_fruit_0'
buffet_cabinet[0].instance_id = 'buffet_cabinet_0'
fruit_bowl_B[0].instance_id = 'fruit_bowl_B_0'
dining_chair_F[0].instance_id = 'dining_chair_F_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

wall_sconce_A[0].position = [0.8991507768597082, 4.253434146770264, 0.19]
wall_sconce_A[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [4.017689467280637, 3.8640340018765764, 0.44]
dining_chair_A[0].rotation = [0, 0, 0]
candle_holder_A[0].position = [4.9348791053892995, 0.12352372062386935, 0.12]
candle_holder_A[0].rotation = [0, 0, 0]
vase_A[0].position = [0.05928552554242239, 2.6766644067634706, 0.21]
vase_A[0].rotation = [0, 0, 0]
print_A[0].position = [5.224511705895598, 4.31462491310745, 0.35]
print_A[0].rotation = [0, 0, 0]
taper_candle_A[0].position = [2.696818345794362, 1.0442676690061643, 0.125]
taper_candle_A[0].rotation = [0, 0, 0]
mirror[0].position = [2.2761394341586803, 2.0408456303177522, 0.6]
mirror[0].rotation = [0, 0, 0]
plant_stand[0].position = [0.1502478098957391, 4.354603546918727, 0.375]
plant_stand[0].rotation = [0, 0, 0]
wall_sconce_B[0].position = [5.1514494947989755, 2.9559940424444644, 0.19]
wall_sconce_B[0].rotation = [0, 0, 0]
vase_B[0].position = [3.3039431824758463, 3.708547888152569, 0.17]
vase_B[0].rotation = [0, 0, 0]
eucalyptus_sprig_A[0].position = [0.14299692923690055, 1.4958833562616731, 0.375]
eucalyptus_sprig_A[0].rotation = [0, 0, 0]
rug[0].position = [0.08675526861761279, 2.198031710078861, 0.006]
rug[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [0.7822678665728805, 1.7170710570235217, 0.44]
dining_chair_B[0].rotation = [0, 0, 0]
candle_holder_B[0].position = [0.13607415881975804, 2.012035390287903, 0.12]
candle_holder_B[0].rotation = [0, 0, 0]
print_B[0].position = [2.4757047181814147, 0.9814255943402017, 0.35]
print_B[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [1.0750081479913103, 3.621810957847027, 0.44]
dining_chair_C[0].rotation = [0, 0, 0]
clock[0].position = [1.055372617478408, 2.146390478925526, 0.2]
clock[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [1.0328704042093684, 0.006221199220270868, 0.44]
dining_chair_D[0].rotation = [0, 0, 0]
dining_chair_E[0].position = [1.9415284419264516, 1.2809221583052737, 0.44]
dining_chair_E[0].rotation = [0, 0, 0]
apple_A[0].position = [4.598595606764775, 4.459563583793563, 0.04]
apple_A[0].rotation = [0, 0, 0]
eucalyptus_sprig_B[0].position = [3.3687236823383646, 2.005214193942302, 0.35]
eucalyptus_sprig_B[0].rotation = [0, 0, 0]
apple_B[0].position = [4.337257930804004, 2.387073419192992, 0.04]
apple_B[0].rotation = [0, 0, 0]
painting[0].position = [5.013970640062642, 4.485034184166281, 0.4]
painting[0].rotation = [0, 0, 0]
dining_table[0].position = [3.3732098761054194, 1.106338176755254, 0.38]
dining_table[0].rotation = [0, 0, 0]
print_C[0].position = [4.317897636818744, 2.738277304662458, 0.35]
print_C[0].rotation = [0, 0, 0]
taper_candle_B[0].position = [4.512491719599228, 3.2080940206338364, 0.125]
taper_candle_B[0].rotation = [0, 0, 0]
fruit_bowl_A[0].position = [0.3190588840157929, 0.22909464958124803, 0.06]
fruit_bowl_A[0].rotation = [0, 0, 0]
small_orange_fruit[0].position = [5.298117577501611, 0.2571840076137131, 0.0325]
small_orange_fruit[0].rotation = [0, 0, 0]
buffet_cabinet[0].position = [5.480143720048255, 1.512560557315366, 0.425]
buffet_cabinet[0].rotation = [0, 0, 0]
fruit_bowl_B[0].position = [2.413193684460762, 0.7436566181759474, 0.055]
fruit_bowl_B[0].rotation = [0, 0, 0]
dining_chair_F[0].position = [2.1445990967444177, 1.5812879421500912, 0.44]
dining_chair_F[0].rotation = [0, 0, 0]
wall_sconce_A[0].position = [0.8991507768597082, 4.253434146770264, 0.19]
wall_sconce_A[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [4.017689467280637, 3.8640340018765764, 0.44]
dining_chair_A[0].rotation = [0, 0, 0]
candle_holder_A[0].position = [4.9348791053892995, 0.12352372062386935, 0.12]
candle_holder_A[0].rotation = [0, 0, 0]
vase_A[0].position = [0.05928552554242239, 2.6766644067634706, 0.21]
vase_A[0].rotation = [0, 0, 0]
print_A[0].position = [5.224511705895598, 4.31462491310745, 0.35]
print_A[0].rotation = [0, 0, 0]
taper_candle_A[0].position = [2.696818345794362, 1.0442676690061643, 0.125]
taper_candle_A[0].rotation = [0, 0, 0]
mirror[0].position = [2.2761394341586803, 2.0408456303177522, 0.6]
mirror[0].rotation = [0, 0, 0]
plant_stand[0].position = [0.1502478098957391, 4.354603546918727, 0.375]
plant_stand[0].rotation = [0, 0, 0]
wall_sconce_B[0].position = [5.1514494947989755, 2.9559940424444644, 0.19]
wall_sconce_B[0].rotation = [0, 0, 0]
vase_B[0].position = [3.3039431824758463, 3.708547888152569, 0.17]
vase_B[0].rotation = [0, 0, 0]
eucalyptus_sprig_A[0].position = [0.14299692923690055, 1.4958833562616731, 0.375]
eucalyptus_sprig_A[0].rotation = [0, 0, 0]
rug[0].position = [0.08675526861761279, 2.198031710078861, 0.006]
rug[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [0.7822678665728805, 1.7170710570235217, 0.44]
dining_chair_B[0].rotation = [0, 0, 0]
candle_holder_B[0].position = [0.13607415881975804, 2.012035390287903, 0.12]
candle_holder_B[0].rotation = [0, 0, 0]
print_B[0].position = [2.4757047181814147, 0.9814255943402017, 0.35]
print_B[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [1.0750081479913103, 3.621810957847027, 0.44]
dining_chair_C[0].rotation = [0, 0, 0]
clock[0].position = [1.055372617478408, 2.146390478925526, 0.2]
clock[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [1.0328704042093684, 0.006221199220270868, 0.44]
dining_chair_D[0].rotation = [0, 0, 0]
dining_chair_E[0].position = [1.9415284419264516, 1.2809221583052737, 0.44]
dining_chair_E[0].rotation = [0, 0, 0]
apple_A[0].position = [4.598595606764775, 4.459563583793563, 0.04]
apple_A[0].rotation = [0, 0, 0]
eucalyptus_sprig_B[0].position = [3.3687236823383646, 2.005214193942302, 0.35]
eucalyptus_sprig_B[0].rotation = [0, 0, 0]
apple_B[0].position = [4.337257930804004, 2.387073419192992, 0.04]
apple_B[0].rotation = [0, 0, 0]
painting[0].position = [5.013970640062642, 4.485034184166281, 0.4]
painting[0].rotation = [0, 0, 0]
dining_table[0].position = [3.3732098761054194, 1.106338176755254, 0.38]
dining_table[0].rotation = [0, 0, 0]
print_C[0].position = [4.317897636818744, 2.738277304662458, 0.35]
print_C[0].rotation = [0, 0, 0]
taper_candle_B[0].position = [4.512491719599228, 3.2080940206338364, 0.125]
taper_candle_B[0].rotation = [0, 0, 0]
fruit_bowl_A[0].position = [0.3190588840157929, 0.22909464958124803, 0.06]
fruit_bowl_A[0].rotation = [0, 0, 0]
small_orange_fruit[0].position = [5.298117577501611, 0.2571840076137131, 0.0325]
small_orange_fruit[0].rotation = [0, 0, 0]
buffet_cabinet[0].position = [5.480143720048255, 1.512560557315366, 0.425]
buffet_cabinet[0].rotation = [0, 0, 0]
fruit_bowl_B[0].position = [2.413193684460762, 0.7436566181759474, 0.055]
fruit_bowl_B[0].rotation = [0, 0, 0]
dining_chair_F[0].position = [2.1445990967444177, 1.5812879421500912, 0.44]
dining_chair_F[0].rotation = [0, 0, 0]

solver.constraints = []

# The furniture group is centered in the 5.50 m by 4.50 m room.
# dining_chair_A and dining_chair_B occupy opposite ends of the table, so
# the dining table is directly between the two requested dining chairs.
room_center = AssetInstance(position=[2.75, 2.25, 1.20])
fixed_heading = AssetInstance(position=[2.75, 2.25, 0.00], rotation=[0, 0, 0])

# Main dining furniture and rug.
rug[0].position = [2.75, 2.25, 0.005]
rug[0].rotation = [0, 0, radians(0)]

dining_table[0].position = [2.75, 2.25, 0.390]
dining_table[0].rotation = [0, 0, radians(0)]

# End chairs: the table lies between chair A and chair B.
dining_chair_A[0].position = [2.75, 0.65, 0.450]
dining_chair_A[0].rotation = [0, 0, radians(90)]

dining_chair_B[0].position = [2.75, 3.85, 0.450]
dining_chair_B[0].rotation = [0, 0, radians(-90)]

# Two chairs on each long side of the table.
dining_chair_C[0].position = [1.72, 1.68, 0.450]
dining_chair_C[0].rotation = [0, 0, radians(0)]

dining_chair_D[0].position = [3.78, 1.68, 0.450]
dining_chair_D[0].rotation = [0, 0, radians(180)]

dining_chair_E[0].position = [1.72, 2.82, 0.450]
dining_chair_E[0].rotation = [0, 0, radians(0)]

dining_chair_F[0].position = [3.78, 2.82, 0.450]
dining_chair_F[0].rotation = [0, 0, radians(180)]

# The buffet is placed along the right wall, outside the chair circulation
# zone. The plant stand decorates the otherwise open lower-left corner.
buffet_cabinet[0].position = [5.275, 2.25, 0.425]
buffet_cabinet[0].rotation = [0, 0, radians(180)]

plant_stand[0].position = [0.50, 0.50, 0.375]
plant_stand[0].rotation = [0, 0, radians(45)]

# Tabletop centerpiece and placeable decorations.
candle_holder_A[0].position = [2.55, 1.73, 0.890]
candle_holder_A[0].rotation = [0, 0, radians(0)]
taper_candle_A[0].position = [2.55, 1.73, 1.135]
taper_candle_A[0].rotation = [0, 0, radians(0)]

candle_holder_B[0].position = [2.95, 2.77, 0.890]
candle_holder_B[0].rotation = [0, 0, radians(0)]
taper_candle_B[0].position = [2.95, 2.77, 1.135]
taper_candle_B[0].rotation = [0, 0, radians(0)]

fruit_bowl_A[0].position = [2.75, 2.25, 0.830]
fruit_bowl_A[0].rotation = [0, 0, radians(0)]

apple_A[0].position = [2.67, 2.25, 0.930]
apple_A[0].rotation = [0, 0, radians(0)]
apple_B[0].position = [2.82, 2.30, 0.930]
apple_B[0].rotation = [0, 0, radians(30)]
small_orange_fruit[0].position = [2.78, 2.17, 0.925]
small_orange_fruit[0].rotation = [0, 0, radians(-20)]

vase_B[0].position = [2.75, 3.00, 0.980]
vase_B[0].rotation = [0, 0, radians(0)]
eucalyptus_sprig_B[0].position = [2.75, 3.00, 1.540]
eucalyptus_sprig_B[0].rotation = [0, 0, radians(0)]

# Buffet-top decorations are spaced apart and remain clear of the mirror.
fruit_bowl_B[0].position = [5.25, 1.70, 0.905]
fruit_bowl_B[0].rotation = [0, 0, radians(180)]

vase_A[0].position = [5.25, 2.62, 1.060]
vase_A[0].rotation = [0, 0, radians(180)]
eucalyptus_sprig_A[0].position = [5.25, 2.62, 1.645]
eucalyptus_sprig_A[0].rotation = [0, 0, radians(180)]

# Artwork on the thin left wall faces into the room.
print_A[0].position = [0.015, 1.25, 1.65]
print_A[0].rotation = [0, 0, radians(0)]
print_B[0].position = [0.015, 2.25, 1.65]
print_B[0].rotation = [0, 0, radians(0)]
print_C[0].position = [0.015, 3.25, 1.65]
print_C[0].rotation = [0, 0, radians(0)]

# The painting, clock, and sconces form a balanced display on the top wall.
painting[0].position = [2.75, 4.48, 2.15]
painting[0].rotation = [0, 0, radians(-90)]

clock[0].position = [4.65, 4.475, 1.85]
clock[0].rotation = [0, 0, radians(-90)]

wall_sconce_A[0].position = [1.60, 4.39, 1.80]
wall_sconce_A[0].rotation = [0, 0, radians(-90)]
wall_sconce_B[0].position = [3.90, 4.39, 1.80]
wall_sconce_B[0].rotation = [0, 0, radians(-90)]

# The mirror occupies the upper section of the right wall, beyond the
# buffet's footprint.
mirror[0].position = [5.48, 3.78, 1.70]
mirror[0].rotation = [0, 0, radians(180)]


# Pin every proposed center before adding softer semantic relationships.
# This gives every new instance a position-based constraint and preserves
# the non-overlapping arrangement.
placed_instances = [
    wall_sconce_A[0], dining_chair_A[0], candle_holder_A[0], vase_A[0],
    print_A[0], taper_candle_A[0], mirror[0], plant_stand[0],
    wall_sconce_B[0], vase_B[0], eucalyptus_sprig_A[0], rug[0],
    dining_chair_B[0], candle_holder_B[0], print_B[0],
    dining_chair_C[0], clock[0], dining_chair_D[0], dining_chair_E[0],
    apple_A[0], eucalyptus_sprig_B[0], apple_B[0], painting[0],
    dining_table[0], print_C[0], taper_candle_B[0], fruit_bowl_A[0],
    small_orange_fruit[0], buffet_cabinet[0], fruit_bowl_B[0],
    dining_chair_F[0],
]
for placed_instance in placed_instances:
    placement_anchor = AssetInstance(position=list(placed_instance.position))
    solver.distance_constraint(
        placed_instance, placement_anchor, 0.0, 0.0, weight=10
    )

# Keep the dining group centered and maintain the table between the two end
# chairs. Equal table-to-chair distances preserve the intended symmetry.
solver.distance_constraint(dining_table[0], room_center, 0.0, 0.0, weight=10)
solver.distance_constraint(
    dining_chair_A[0], dining_table[0], 1.60, 1.60, weight=10
)
solver.distance_constraint(
    dining_chair_B[0], dining_table[0], 1.60, 1.60, weight=10
)
solver.distance_constraint(
    dining_chair_C[0], dining_table[0], 1.10, 1.30, weight=1
)
solver.distance_constraint(
    dining_chair_D[0], dining_table[0], 1.10, 1.30, weight=1
)
solver.distance_constraint(
    dining_chair_E[0], dining_table[0], 1.10, 1.30, weight=1
)
solver.distance_constraint(
    dining_chair_F[0], dining_table[0], 1.10, 1.30, weight=1
)

# Floor furniture and rug orientations.
solver.align_with(dining_table[0], fixed_heading, angle=0)
solver.align_with(rug[0], dining_table[0], angle=0)
solver.point_towards(dining_chair_A[0], dining_table[0])
solver.point_towards(dining_chair_B[0], dining_table[0])
solver.point_towards(dining_chair_C[0], dining_table[0])
solver.point_towards(dining_chair_D[0], dining_table[0])
solver.point_towards(dining_chair_E[0], dining_table[0])
solver.point_towards(dining_chair_F[0], dining_table[0])
solver.point_towards(buffet_cabinet[0], room_center)
solver.point_towards(plant_stand[0], dining_table[0])

# Explicit wall relationships keep all wall-mounted pieces attached to their
# intended walls. Pointing toward the room also supplies their orientation
# constraints.
solver.against_wall(print_A[0], walls[3])
solver.against_wall(print_B[0], walls[3])
solver.against_wall(print_C[0], walls[3])
solver.point_towards(print_A[0], room_center)
solver.point_towards(print_B[0], room_center)
solver.point_towards(print_C[0], room_center)

solver.against_wall(painting[0], walls[2])
solver.against_wall(clock[0], walls[2])
solver.against_wall(wall_sconce_A[0], walls[2])
solver.against_wall(wall_sconce_B[0], walls[2])
solver.point_towards(painting[0], room_center)
solver.point_towards(clock[0], room_center)
solver.point_towards(wall_sconce_A[0], room_center)
solver.point_towards(wall_sconce_B[0], room_center)

solver.against_wall(mirror[0], walls[1])
solver.point_towards(mirror[0], room_center)
solver.against_wall(buffet_cabinet[0], walls[1])

# Surface constraints ensure that all small decorations remain supported.
solver.on_top_of(dining_table[0], rug[0])

solver.on_top_of(candle_holder_A[0], dining_table[0])
solver.on_top_of(candle_holder_B[0], dining_table[0])
solver.on_top_of(taper_candle_A[0], candle_holder_A[0])
solver.on_top_of(taper_candle_B[0], candle_holder_B[0])

solver.on_top_of(fruit_bowl_A[0], dining_table[0])
solver.on_top_of(apple_A[0], fruit_bowl_A[0])
solver.on_top_of(apple_B[0], fruit_bowl_A[0])
solver.on_top_of(small_orange_fruit[0], fruit_bowl_A[0])

solver.on_top_of(vase_B[0], dining_table[0])
solver.on_top_of(eucalyptus_sprig_B[0], vase_B[0])

solver.on_top_of(fruit_bowl_B[0], buffet_cabinet[0])
solver.on_top_of(vase_A[0], buffet_cabinet[0])
solver.on_top_of(eucalyptus_sprig_A[0], vase_A[0])

# Orientation constraints for every tabletop and buffet-top object.
solver.align_with(candle_holder_A[0], dining_table[0])
solver.align_with(candle_holder_B[0], dining_table[0])
solver.align_with(taper_candle_A[0], candle_holder_A[0])
solver.align_with(taper_candle_B[0], candle_holder_B[0])
solver.align_with(fruit_bowl_A[0], dining_table[0])
solver.align_with(apple_A[0], fruit_bowl_A[0])
solver.align_with(apple_B[0], fruit_bowl_A[0], angle=30)
solver.align_with(small_orange_fruit[0], fruit_bowl_A[0], angle=-20)
solver.align_with(vase_B[0], dining_table[0])
solver.align_with(eucalyptus_sprig_B[0], vase_B[0])
solver.align_with(fruit_bowl_B[0], buffet_cabinet[0])
solver.align_with(vase_A[0], buffet_cabinet[0])
solver.align_with(eucalyptus_sprig_A[0], vase_A[0])

solver.constraints = []
candle_holder_B[0].position = [2.950000047683716, 2.7699999809265137, 0.8899999856948853]
candle_holder_B[0].rotation = [0, 0, 0.08481563903295303]
candle_holder_B[0].optimize = 2
mirror[0].position = [5.4799981117248535, 3.7799999713897705, 0.6000000238418579]
mirror[0].rotation = [0, 0, 3.141590747861383]
mirror[0].optimize = 2
apple_B[0].position = [2.819999933242798, 2.299999952316284, 0.9300000071525574]
apple_B[0].rotation = [0, 0, 0.6084177815813607]
apple_B[0].optimize = 2
vase_B[0].position = [2.75, 3.0, 0.9399999976158142]
vase_B[0].rotation = [0, 0, 0.08481563903295303]
vase_B[0].optimize = 2
print_A[0].position = [0.014999437145888805, 1.25, 0.3499999940395355]
print_A[0].rotation = [0, 0, -1.9502476627342156e-06]
print_A[0].optimize = 2
taper_candle_B[0].position = [2.950000047683716, 2.7699999809265137, 1.1349999904632568]
taper_candle_B[0].rotation = [0, 0, 0.08481412644332627]
taper_candle_B[0].optimize = 2
fruit_bowl_A[0].position = [2.75, 2.25, 0.8299999833106995]
fruit_bowl_A[0].rotation = [0, 0, 0.08482103981283241]
fruit_bowl_A[0].optimize = 2
clock[0].position = [4.650000095367432, 4.475001811981201, 0.20000000298023224]
clock[0].rotation = [0, 0, -1.5707982851022557]
clock[0].optimize = 2
fruit_bowl_B[0].position = [5.25, 1.7000000476837158, 0.9050000309944153]
fruit_bowl_B[0].rotation = [0, 0, 3.1415806509379345]
fruit_bowl_B[0].optimize = 2
dining_chair_D[0].position = [3.7799999713897705, 1.6799999475479126, 0.4399999976158142]
dining_chair_D[0].rotation = [0, 0, -3.1290262823329655]
dining_chair_D[0].optimize = 2
print_B[0].position = [0.014999437145888805, 2.25, 0.3499999940395355]
print_B[0].rotation = [0, 0, -1.9502476627342156e-06]
print_B[0].optimize = 2
dining_table[0].position = [2.75, 2.25, 0.38999998569488525]
dining_table[0].rotation = [0, 0, 0.08482299704637274]
dining_table[0].optimize = 2
candle_holder_A[0].position = [2.549999952316284, 1.7300000190734863, 0.8899999856948853]
candle_holder_A[0].rotation = [0, 0, 0.08481563903295303]
candle_holder_A[0].optimize = 2
taper_candle_A[0].position = [2.549999952316284, 1.7300000190734863, 1.1349999904632568]
taper_candle_A[0].rotation = [0, 0, 0.08481412644332627]
taper_candle_A[0].optimize = 2
dining_chair_A[0].position = [2.75, 0.6499999761581421, 0.4399999976158142]
dining_chair_A[0].rotation = [0, 0, 1.5833626980517244]
dining_chair_A[0].optimize = 2
painting[0].position = [2.75, 4.4799981117248535, 0.4000000059604645]
painting[0].rotation = [0, 0, -1.570798358647807]
painting[0].optimize = 2
apple_A[0].position = [2.6700000762939453, 2.25, 0.9300000071525574]
apple_A[0].rotation = [0, 0, 0.08482651499269346]
apple_A[0].optimize = 2
dining_chair_C[0].position = [1.7200000286102295, 1.6799999475479126, 0.4399999976158142]
dining_chair_C[0].rotation = [0, 0, 0.01256637125682779]
dining_chair_C[0].optimize = 2
print_C[0].position = [0.014999437145888805, 3.25, 0.3499999940395355]
print_C[0].rotation = [0, 0, -1.9502476627342156e-06]
print_C[0].optimize = 2
buffet_cabinet[0].position = [5.274996280670166, 2.25, 0.42500001192092896]
buffet_cabinet[0].rotation = [0, 0, 3.1415921548751604]
buffet_cabinet[0].optimize = 2
plant_stand[0].position = [0.5, 0.5, 0.375]
plant_stand[0].rotation = [0, 0, 0.7948229285630478]
plant_stand[0].optimize = 2
rug[0].position = [2.75, 2.25, 0.004999999888241291]
rug[0].rotation = [0, 0, 0.0848358750626114]
rug[0].optimize = 2
small_orange_fruit[0].position = [2.7799999713897705, 2.1700000762939453, 0.925000011920929]
small_orange_fruit[0].rotation = [0, 0, -0.2642015485522922]
small_orange_fruit[0].optimize = 2
dining_chair_F[0].position = [3.7799999713897705, 2.819999933242798, 0.4399999976158142]
dining_chair_F[0].rotation = [0, 0, -3.1290262823329655]
dining_chair_F[0].optimize = 2
wall_sconce_A[0].position = [1.600000023841858, 4.389997482299805, 0.1899999976158142]
wall_sconce_A[0].rotation = [0, 0, -1.5707982765769173]
wall_sconce_A[0].optimize = 2
eucalyptus_sprig_B[0].position = [2.75, 3.0, 1.4600000381469727]
eucalyptus_sprig_B[0].rotation = [0, 0, 0.08481412644332627]
eucalyptus_sprig_B[0].optimize = 2
vase_A[0].position = [5.25, 2.619999885559082, 1.0600000619888306]
vase_A[0].rotation = [0, 0, 3.1415790657251184]
vase_A[0].optimize = 2
dining_chair_B[0].position = [2.75, 3.851050853729248, 0.4399999976158142]
dining_chair_B[0].rotation = [0, 0, -1.5582299555380688]
dining_chair_B[0].optimize = 2
eucalyptus_sprig_A[0].position = [5.25, 2.619999885559082, 1.6450001001358032]
eucalyptus_sprig_A[0].rotation = [0, 0, 3.1415923998100257]
eucalyptus_sprig_A[0].optimize = 2
dining_chair_E[0].position = [1.7200000286102295, 2.819999933242798, 0.4399999976158142]
dining_chair_E[0].rotation = [0, 0, 0.01256637125682779]
dining_chair_E[0].optimize = 2
wall_sconce_B[0].position = [3.9000000953674316, 4.389997482299805, 0.1899999976158142]
wall_sconce_B[0].rotation = [0, 0, -1.5707982765769173]
wall_sconce_B[0].optimize = 2

