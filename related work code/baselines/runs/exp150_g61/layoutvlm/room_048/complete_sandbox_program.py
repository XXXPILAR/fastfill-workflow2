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
    Wall(corner1=[14.21, 0.00, 0.00], corner2=[14.21, 0.08, 0.00]),
    Wall(corner1=[14.21, 0.08, 0.00], corner2=[14.21, 2.69, 0.00]),
    Wall(corner1=[14.21, 2.69, 0.00], corner2=[14.21, 2.76, 0.00]),
    Wall(corner1=[14.21, 2.76, 0.00], corner2=[14.21, 4.36, 0.00]),
    Wall(corner1=[14.21, 4.36, 0.00], corner2=[14.21, 4.42, 0.00]),
    Wall(corner1=[14.21, 4.42, 0.00], corner2=[14.21, 10.16, 0.00]),
    Wall(corner1=[14.21, 10.16, 0.00], corner2=[2.54, 10.16, 0.00]),
    Wall(corner1=[2.54, 10.16, 0.00], corner2=[2.54, 9.43, 0.00]),
    Wall(corner1=[2.54, 9.43, 0.00], corner2=[2.54, 9.19, 0.00]),
    Wall(corner1=[2.54, 9.19, 0.00], corner2=[0.00, 9.19, 0.00]),
    Wall(corner1=[0.00, 9.19, 0.00], corner2=[0.00, 9.10, 0.00]),
    Wall(corner1=[0.00, 9.10, 0.00], corner2=[0.00, 7.50, 0.00]),
    Wall(corner1=[0.00, 7.50, 0.00], corner2=[0.00, 7.38, 0.00]),
    Wall(corner1=[0.00, 7.38, 0.00], corner2=[1.03, 7.38, 0.00]),
    Wall(corner1=[1.03, 7.38, 0.00], corner2=[1.27, 7.38, 0.00]),
    Wall(corner1=[1.27, 7.38, 0.00], corner2=[1.27, 0.00, 0.00]),
    Wall(corner1=[1.27, 0.00, 0.00], corner2=[14.21, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
plant_A = Assets(description="plant", size=[0.65, 0.65, 1.50], placements=[AssetInstance() for _ in range(1)])
fruit_A = Assets(description="fruit", size=[0.08, 0.08, 0.09], placements=[AssetInstance() for _ in range(1)])
table_A = Assets(description="table", size=[0.75, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
side_table_A = Assets(description="side table", size=[0.65, 0.65, 0.55], placements=[AssetInstance() for _ in range(1)])
plant_B = Assets(description="plant", size=[0.30, 0.30, 0.40], placements=[AssetInstance() for _ in range(1)])
plant_C = Assets(description="plant", size=[0.55, 0.55, 1.20], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
plant_D = Assets(description="plant", size=[0.45, 0.45, 0.90], placements=[AssetInstance() for _ in range(1)])
fruit_B = Assets(description="fruit", size=[0.08, 0.08, 0.08], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
cup_A = Assets(description="cup", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
chair_D = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
plant_E = Assets(description="plant", size=[0.60, 0.60, 1.40], placements=[AssetInstance() for _ in range(1)])
chair_E = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
fruit_C = Assets(description="fruit", size=[0.09, 0.09, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_F = Assets(description="plant", size=[0.50, 0.50, 1.10], placements=[AssetInstance() for _ in range(1)])
multi_person_sofa_A = Assets(description="multi person sofa", size=[0.82, 1.80, 0.85], placements=[AssetInstance() for _ in range(1)])
fruit_D = Assets(description="fruit", size=[0.08, 0.08, 0.09], placements=[AssetInstance() for _ in range(1)])
multi_person_sofa_B = Assets(description="multi person sofa", size=[0.82, 1.80, 0.85], placements=[AssetInstance() for _ in range(1)])
fruit_E = Assets(description="fruit", size=[0.08, 0.08, 0.08], placements=[AssetInstance() for _ in range(1)])
plant_G = Assets(description="plant", size=[0.55, 0.55, 1.30], placements=[AssetInstance() for _ in range(1)])
cup_B = Assets(description="cup", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
fruit_F = Assets(description="fruit", size=[0.09, 0.09, 0.10], placements=[AssetInstance() for _ in range(1)])
high_chair_A = Assets(description="high chair", size=[0.48, 0.45, 1.05], placements=[AssetInstance() for _ in range(1)])
landscape_stone_A = Assets(description="landscape stone", size=[0.45, 0.60, 0.35], placements=[AssetInstance() for _ in range(1)])
plant_H = Assets(description="plant", size=[0.60, 0.60, 1.40], placements=[AssetInstance() for _ in range(1)])
side_table_B = Assets(description="side table", size=[0.65, 0.65, 0.55], placements=[AssetInstance() for _ in range(1)])
fruit_G = Assets(description="fruit", size=[0.08, 0.08, 0.09], placements=[AssetInstance() for _ in range(1)])
multi_person_sofa_C = Assets(description="multi person sofa", size=[0.82, 1.80, 0.85], placements=[AssetInstance() for _ in range(1)])
chair_F = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
plant_I = Assets(description="plant", size=[0.45, 0.45, 0.85], placements=[AssetInstance() for _ in range(1)])
flowerpot_A = Assets(description="flowerpot", size=[0.35, 0.35, 0.36], placements=[AssetInstance() for _ in range(1)])
chair_G = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
plant_J = Assets(description="plant", size=[0.30, 0.30, 0.40], placements=[AssetInstance() for _ in range(1)])
side_table_C = Assets(description="side table", size=[0.65, 0.65, 0.55], placements=[AssetInstance() for _ in range(1)])
fruit_H = Assets(description="fruit", size=[0.08, 0.08, 0.08], placements=[AssetInstance() for _ in range(1)])
chair_H = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
chair_I = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
chair_J = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
chair_K = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
floor_lamp_A = Assets(description="floor lamp", size=[0.40, 0.40, 1.65], placements=[AssetInstance() for _ in range(1)])
plant_K = Assets(description="plant", size=[0.65, 0.65, 1.60], placements=[AssetInstance() for _ in range(1)])
plant_L = Assets(description="plant", size=[0.45, 0.45, 0.95], placements=[AssetInstance() for _ in range(1)])
chair_L = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
plant_M = Assets(description="plant", size=[0.25, 0.25, 0.35], placements=[AssetInstance() for _ in range(1)])
plant_N = Assets(description="plant", size=[0.50, 0.50, 1.15], placements=[AssetInstance() for _ in range(1)])
fruit_I = Assets(description="fruit", size=[0.08, 0.08, 0.09], placements=[AssetInstance() for _ in range(1)])
plant_O = Assets(description="plant", size=[0.60, 0.60, 1.35], placements=[AssetInstance() for _ in range(1)])
side_table_D = Assets(description="side table", size=[0.65, 0.65, 0.55], placements=[AssetInstance() for _ in range(1)])
chair_M = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
flowerpot_B = Assets(description="flowerpot", size=[0.32, 0.32, 0.34], placements=[AssetInstance() for _ in range(1)])
fruit_J = Assets(description="fruit", size=[0.09, 0.09, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_P = Assets(description="plant", size=[0.45, 0.45, 0.80], placements=[AssetInstance() for _ in range(1)])
plant_Q = Assets(description="plant", size=[0.55, 0.55, 1.20], placements=[AssetInstance() for _ in range(1)])
fruit_K = Assets(description="fruit", size=[0.08, 0.08, 0.08], placements=[AssetInstance() for _ in range(1)])
chair_N = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
plant_R = Assets(description="plant", size=[0.30, 0.30, 0.45], placements=[AssetInstance() for _ in range(1)])
side_table_E = Assets(description="side table", size=[0.65, 0.65, 0.55], placements=[AssetInstance() for _ in range(1)])
plant_S = Assets(description="plant", size=[0.60, 0.60, 1.40], placements=[AssetInstance() for _ in range(1)])
fruit_L = Assets(description="fruit", size=[0.08, 0.08, 0.09], placements=[AssetInstance() for _ in range(1)])
high_chair_B = Assets(description="high chair", size=[0.48, 0.45, 1.05], placements=[AssetInstance() for _ in range(1)])
side_table_F = Assets(description="side table", size=[0.65, 0.65, 0.55], placements=[AssetInstance() for _ in range(1)])
chair_O = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
table_B = Assets(description="table", size=[0.75, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
chair_P = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
flowerpot_C = Assets(description="flowerpot", size=[0.35, 0.35, 0.36], placements=[AssetInstance() for _ in range(1)])
chair_Q = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
plant_T = Assets(description="plant", size=[0.50, 0.50, 0.90], placements=[AssetInstance() for _ in range(1)])
dining_plate = Assets(description="dining plate", size=[0.28, 0.28, 0.03], placements=[AssetInstance() for _ in range(1)])
chair_R = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
high_chair_C = Assets(description="high chair", size=[0.48, 0.45, 1.05], placements=[AssetInstance() for _ in range(1)])
fruit_M = Assets(description="fruit", size=[0.08, 0.08, 0.09], placements=[AssetInstance() for _ in range(1)])
fruit_N = Assets(description="fruit", size=[0.08, 0.08, 0.08], placements=[AssetInstance() for _ in range(1)])
multi_person_sofa_D = Assets(description="multi person sofa", size=[0.82, 1.80, 0.85], placements=[AssetInstance() for _ in range(1)])
plant_U = Assets(description="plant", size=[0.55, 0.55, 1.25], placements=[AssetInstance() for _ in range(1)])
plant_V = Assets(description="plant", size=[0.45, 0.45, 0.90], placements=[AssetInstance() for _ in range(1)])
fruit_O = Assets(description="fruit", size=[0.09, 0.09, 0.10], placements=[AssetInstance() for _ in range(1)])
multi_person_sofa_E = Assets(description="multi person sofa", size=[0.82, 1.80, 0.85], placements=[AssetInstance() for _ in range(1)])
plant_W = Assets(description="plant", size=[0.65, 0.65, 1.50], placements=[AssetInstance() for _ in range(1)])
fruit_P = Assets(description="fruit", size=[0.08, 0.08, 0.09], placements=[AssetInstance() for _ in range(1)])
multi_person_sofa_F = Assets(description="multi person sofa", size=[0.82, 1.80, 0.85], placements=[AssetInstance() for _ in range(1)])
fruit_Q = Assets(description="fruit", size=[0.08, 0.08, 0.08], placements=[AssetInstance() for _ in range(1)])
plant_X = Assets(description="plant", size=[0.25, 0.25, 0.35], placements=[AssetInstance() for _ in range(1)])
chair_S = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
table_C = Assets(description="table", size=[0.75, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
stool = Assets(description="stool", size=[0.38, 0.38, 0.46], placements=[AssetInstance() for _ in range(1)])
fruit_R = Assets(description="fruit", size=[0.08, 0.08, 0.09], placements=[AssetInstance() for _ in range(1)])
fruit_S = Assets(description="fruit", size=[0.09, 0.09, 0.10], placements=[AssetInstance() for _ in range(1)])
flowerpot_D = Assets(description="flowerpot", size=[0.35, 0.35, 0.36], placements=[AssetInstance() for _ in range(1)])
chair_T = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
chair_U = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
fruit_T = Assets(description="fruit", size=[0.08, 0.08, 0.08], placements=[AssetInstance() for _ in range(1)])
chair_V = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
wall_lamp = Assets(description="wall lamp", size=[0.25, 0.22, 0.35], placements=[AssetInstance() for _ in range(1)])
wine = Assets(description="wine", size=[0.08, 0.08, 0.30], placements=[AssetInstance() for _ in range(1)])
fruit_U = Assets(description="fruit", size=[0.08, 0.08, 0.09], placements=[AssetInstance() for _ in range(1)])
plant_Y = Assets(description="plant", size=[0.50, 0.50, 0.95], placements=[AssetInstance() for _ in range(1)])
plant_Z = Assets(description="plant", size=[0.55, 0.55, 1.25], placements=[AssetInstance() for _ in range(1)])
plant_group_2_A = Assets(description="plant", size=[0.45, 0.45, 1.00], placements=[AssetInstance() for _ in range(1)])
fruit_V = Assets(description="fruit", size=[0.09, 0.09, 0.10], placements=[AssetInstance() for _ in range(1)])
floor_lamp_B = Assets(description="floor lamp", size=[0.40, 0.40, 1.65], placements=[AssetInstance() for _ in range(1)])
landscape_stone_B = Assets(description="landscape stone", size=[0.40, 0.50, 0.30], placements=[AssetInstance() for _ in range(1)])
plant_group_2_B = Assets(description="plant", size=[0.60, 0.60, 1.45], placements=[AssetInstance() for _ in range(1)])
fruit_W = Assets(description="fruit", size=[0.08, 0.08, 0.08], placements=[AssetInstance() for _ in range(1)])
fruit_X = Assets(description="fruit", size=[0.08, 0.08, 0.09], placements=[AssetInstance() for _ in range(1)])
chair_W = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
plant_group_2_C = Assets(description="plant", size=[0.30, 0.30, 0.40], placements=[AssetInstance() for _ in range(1)])
multi_person_sofa_G = Assets(description="multi person sofa", size=[0.82, 1.80, 0.85], placements=[AssetInstance() for _ in range(1)])
side_table_G = Assets(description="side table", size=[0.65, 0.65, 0.55], placements=[AssetInstance() for _ in range(1)])
multi_person_sofa_H = Assets(description="multi person sofa", size=[0.82, 1.80, 0.85], placements=[AssetInstance() for _ in range(1)])
fruit_Y = Assets(description="fruit", size=[0.08, 0.08, 0.08], placements=[AssetInstance() for _ in range(1)])
high_chair_D = Assets(description="high chair", size=[0.48, 0.45, 1.05], placements=[AssetInstance() for _ in range(1)])
plant_group_2_D = Assets(description="plant", size=[0.25, 0.25, 0.35], placements=[AssetInstance() for _ in range(1)])
side_table_H = Assets(description="side table", size=[0.65, 0.65, 0.55], placements=[AssetInstance() for _ in range(1)])
shelf = Assets(description="shelf", size=[0.35, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
chair_X = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
chair_Y = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
chair_Z = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
plant_group_2_E = Assets(description="plant", size=[0.50, 0.50, 1.10], placements=[AssetInstance() for _ in range(1)])
plant_group_2_F = Assets(description="plant", size=[0.60, 0.60, 1.40], placements=[AssetInstance() for _ in range(1)])
floor_lamp_C = Assets(description="floor lamp", size=[0.40, 0.40, 1.65], placements=[AssetInstance() for _ in range(1)])
landscape_stone_C = Assets(description="landscape stone", size=[0.45, 0.65, 0.40], placements=[AssetInstance() for _ in range(1)])
fruit_Z = Assets(description="fruit", size=[0.09, 0.09, 0.10], placements=[AssetInstance() for _ in range(1)])
fruit_group_2_A = Assets(description="fruit", size=[0.08, 0.08, 0.09], placements=[AssetInstance() for _ in range(1)])
plant_group_2_G = Assets(description="plant", size=[0.30, 0.30, 0.45], placements=[AssetInstance() for _ in range(1)])
fruit_group_2_B = Assets(description="fruit", size=[0.08, 0.08, 0.08], placements=[AssetInstance() for _ in range(1)])
water_bar = Assets(description="water bar", size=[0.75, 3.00, 1.05], placements=[AssetInstance() for _ in range(1)])
chair_group_2_A = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
fruit_group_2_C = Assets(description="fruit", size=[0.08, 0.08, 0.09], placements=[AssetInstance() for _ in range(1)])
billboard = Assets(description="billboard", size=[0.08, 0.65, 0.90], placements=[AssetInstance() for _ in range(1)])
jar = Assets(description="jar", size=[0.16, 0.16, 0.25], placements=[AssetInstance() for _ in range(1)])
fruit_group_2_D = Assets(description="fruit", size=[0.09, 0.09, 0.10], placements=[AssetInstance() for _ in range(1)])
flowerpot_E = Assets(description="flowerpot", size=[0.35, 0.35, 0.36], placements=[AssetInstance() for _ in range(1)])
side_table_I = Assets(description="side table", size=[0.65, 0.65, 0.55], placements=[AssetInstance() for _ in range(1)])
chair_group_2_B = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
landscape_stone_D = Assets(description="landscape stone", size=[0.40, 0.55, 0.30], placements=[AssetInstance() for _ in range(1)])
high_chair_E = Assets(description="high chair", size=[0.48, 0.45, 1.05], placements=[AssetInstance() for _ in range(1)])
fruit_group_2_E = Assets(description="fruit", size=[0.08, 0.08, 0.08], placements=[AssetInstance() for _ in range(1)])
table_D = Assets(description="table", size=[0.75, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
plant_group_2_H = Assets(description="plant", size=[0.50, 0.50, 0.90], placements=[AssetInstance() for _ in range(1)])
chair_group_2_C = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
cup_C = Assets(description="cup", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
multi_person_sofa_I = Assets(description="multi person sofa", size=[0.82, 1.80, 0.85], placements=[AssetInstance() for _ in range(1)])
fruit_group_2_F = Assets(description="fruit", size=[0.08, 0.08, 0.09], placements=[AssetInstance() for _ in range(1)])
chair_group_2_D = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
chair_group_2_E = Assets(description="chair", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
plant_group_2_I = Assets(description="plant", size=[0.28, 0.28, 0.40], placements=[AssetInstance() for _ in range(1)])
plant_group_2_J = Assets(description="plant", size=[0.28, 0.28, 0.40], placements=[AssetInstance() for _ in range(1)])
side_table_J = Assets(description="side table", size=[0.65, 0.65, 0.55], placements=[AssetInstance() for _ in range(1)])
side_table_K = Assets(description="side table", size=[0.65, 0.65, 0.55], placements=[AssetInstance() for _ in range(1)])

plant_A[0].instance_id = 'plant_A_0'
fruit_A[0].instance_id = 'fruit_A_0'
table_A[0].instance_id = 'table_A_0'
chair_A[0].instance_id = 'chair_A_0'
side_table_A[0].instance_id = 'side_table_A_0'
plant_B[0].instance_id = 'plant_B_0'
plant_C[0].instance_id = 'plant_C_0'
chair_B[0].instance_id = 'chair_B_0'
plant_D[0].instance_id = 'plant_D_0'
fruit_B[0].instance_id = 'fruit_B_0'
chair_C[0].instance_id = 'chair_C_0'
cup_A[0].instance_id = 'cup_A_0'
chair_D[0].instance_id = 'chair_D_0'
plant_E[0].instance_id = 'plant_E_0'
chair_E[0].instance_id = 'chair_E_0'
fruit_C[0].instance_id = 'fruit_C_0'
plant_F[0].instance_id = 'plant_F_0'
multi_person_sofa_A[0].instance_id = 'multi_person_sofa_A_0'
fruit_D[0].instance_id = 'fruit_D_0'
multi_person_sofa_B[0].instance_id = 'multi_person_sofa_B_0'
fruit_E[0].instance_id = 'fruit_E_0'
plant_G[0].instance_id = 'plant_G_0'
cup_B[0].instance_id = 'cup_B_0'
fruit_F[0].instance_id = 'fruit_F_0'
high_chair_A[0].instance_id = 'high_chair_A_0'
landscape_stone_A[0].instance_id = 'landscape_stone_A_0'
plant_H[0].instance_id = 'plant_H_0'
side_table_B[0].instance_id = 'side_table_B_0'
fruit_G[0].instance_id = 'fruit_G_0'
multi_person_sofa_C[0].instance_id = 'multi_person_sofa_C_0'
chair_F[0].instance_id = 'chair_F_0'
plant_I[0].instance_id = 'plant_I_0'
flowerpot_A[0].instance_id = 'flowerpot_A_0'
chair_G[0].instance_id = 'chair_G_0'
plant_J[0].instance_id = 'plant_J_0'
side_table_C[0].instance_id = 'side_table_C_0'
fruit_H[0].instance_id = 'fruit_H_0'
chair_H[0].instance_id = 'chair_H_0'
chair_I[0].instance_id = 'chair_I_0'
chair_J[0].instance_id = 'chair_J_0'
chair_K[0].instance_id = 'chair_K_0'
floor_lamp_A[0].instance_id = 'floor_lamp_A_0'
plant_K[0].instance_id = 'plant_K_0'
plant_L[0].instance_id = 'plant_L_0'
chair_L[0].instance_id = 'chair_L_0'
plant_M[0].instance_id = 'plant_M_0'
plant_N[0].instance_id = 'plant_N_0'
fruit_I[0].instance_id = 'fruit_I_0'
plant_O[0].instance_id = 'plant_O_0'
side_table_D[0].instance_id = 'side_table_D_0'
chair_M[0].instance_id = 'chair_M_0'
flowerpot_B[0].instance_id = 'flowerpot_B_0'
fruit_J[0].instance_id = 'fruit_J_0'
plant_P[0].instance_id = 'plant_P_0'
plant_Q[0].instance_id = 'plant_Q_0'
fruit_K[0].instance_id = 'fruit_K_0'
chair_N[0].instance_id = 'chair_N_0'
plant_R[0].instance_id = 'plant_R_0'
side_table_E[0].instance_id = 'side_table_E_0'
plant_S[0].instance_id = 'plant_S_0'
fruit_L[0].instance_id = 'fruit_L_0'
high_chair_B[0].instance_id = 'high_chair_B_0'
side_table_F[0].instance_id = 'side_table_F_0'
chair_O[0].instance_id = 'chair_O_0'
table_B[0].instance_id = 'table_B_0'
chair_P[0].instance_id = 'chair_P_0'
flowerpot_C[0].instance_id = 'flowerpot_C_0'
chair_Q[0].instance_id = 'chair_Q_0'
plant_T[0].instance_id = 'plant_T_0'
dining_plate[0].instance_id = 'dining_plate_0'
chair_R[0].instance_id = 'chair_R_0'
high_chair_C[0].instance_id = 'high_chair_C_0'
fruit_M[0].instance_id = 'fruit_M_0'
fruit_N[0].instance_id = 'fruit_N_0'
multi_person_sofa_D[0].instance_id = 'multi_person_sofa_D_0'
plant_U[0].instance_id = 'plant_U_0'
plant_V[0].instance_id = 'plant_V_0'
fruit_O[0].instance_id = 'fruit_O_0'
multi_person_sofa_E[0].instance_id = 'multi_person_sofa_E_0'
plant_W[0].instance_id = 'plant_W_0'
fruit_P[0].instance_id = 'fruit_P_0'
multi_person_sofa_F[0].instance_id = 'multi_person_sofa_F_0'
fruit_Q[0].instance_id = 'fruit_Q_0'
plant_X[0].instance_id = 'plant_X_0'
chair_S[0].instance_id = 'chair_S_0'
table_C[0].instance_id = 'table_C_0'
stool[0].instance_id = 'stool_0'
fruit_R[0].instance_id = 'fruit_R_0'
fruit_S[0].instance_id = 'fruit_S_0'
flowerpot_D[0].instance_id = 'flowerpot_D_0'
chair_T[0].instance_id = 'chair_T_0'
chair_U[0].instance_id = 'chair_U_0'
fruit_T[0].instance_id = 'fruit_T_0'
chair_V[0].instance_id = 'chair_V_0'
wall_lamp[0].instance_id = 'wall_lamp_0'
wine[0].instance_id = 'wine_0'
fruit_U[0].instance_id = 'fruit_U_0'
plant_Y[0].instance_id = 'plant_Y_0'
plant_Z[0].instance_id = 'plant_Z_0'
plant_group_2_A[0].instance_id = 'plant_group_2_A_0'
fruit_V[0].instance_id = 'fruit_V_0'
floor_lamp_B[0].instance_id = 'floor_lamp_B_0'
landscape_stone_B[0].instance_id = 'landscape_stone_B_0'
plant_group_2_B[0].instance_id = 'plant_group_2_B_0'
fruit_W[0].instance_id = 'fruit_W_0'
fruit_X[0].instance_id = 'fruit_X_0'
chair_W[0].instance_id = 'chair_W_0'
plant_group_2_C[0].instance_id = 'plant_group_2_C_0'
multi_person_sofa_G[0].instance_id = 'multi_person_sofa_G_0'
side_table_G[0].instance_id = 'side_table_G_0'
multi_person_sofa_H[0].instance_id = 'multi_person_sofa_H_0'
fruit_Y[0].instance_id = 'fruit_Y_0'
high_chair_D[0].instance_id = 'high_chair_D_0'
plant_group_2_D[0].instance_id = 'plant_group_2_D_0'
side_table_H[0].instance_id = 'side_table_H_0'
shelf[0].instance_id = 'shelf_0'
chair_X[0].instance_id = 'chair_X_0'
chair_Y[0].instance_id = 'chair_Y_0'
chair_Z[0].instance_id = 'chair_Z_0'
plant_group_2_E[0].instance_id = 'plant_group_2_E_0'
plant_group_2_F[0].instance_id = 'plant_group_2_F_0'
floor_lamp_C[0].instance_id = 'floor_lamp_C_0'
landscape_stone_C[0].instance_id = 'landscape_stone_C_0'
fruit_Z[0].instance_id = 'fruit_Z_0'
fruit_group_2_A[0].instance_id = 'fruit_group_2_A_0'
plant_group_2_G[0].instance_id = 'plant_group_2_G_0'
fruit_group_2_B[0].instance_id = 'fruit_group_2_B_0'
water_bar[0].instance_id = 'water_bar_0'
chair_group_2_A[0].instance_id = 'chair_group_2_A_0'
fruit_group_2_C[0].instance_id = 'fruit_group_2_C_0'
billboard[0].instance_id = 'billboard_0'
jar[0].instance_id = 'jar_0'
fruit_group_2_D[0].instance_id = 'fruit_group_2_D_0'
flowerpot_E[0].instance_id = 'flowerpot_E_0'
side_table_I[0].instance_id = 'side_table_I_0'
chair_group_2_B[0].instance_id = 'chair_group_2_B_0'
landscape_stone_D[0].instance_id = 'landscape_stone_D_0'
high_chair_E[0].instance_id = 'high_chair_E_0'
fruit_group_2_E[0].instance_id = 'fruit_group_2_E_0'
table_D[0].instance_id = 'table_D_0'
plant_group_2_H[0].instance_id = 'plant_group_2_H_0'
chair_group_2_C[0].instance_id = 'chair_group_2_C_0'
cup_C[0].instance_id = 'cup_C_0'
multi_person_sofa_I[0].instance_id = 'multi_person_sofa_I_0'
fruit_group_2_F[0].instance_id = 'fruit_group_2_F_0'
chair_group_2_D[0].instance_id = 'chair_group_2_D_0'
chair_group_2_E[0].instance_id = 'chair_group_2_E_0'
plant_group_2_I[0].instance_id = 'plant_group_2_I_0'
plant_group_2_J[0].instance_id = 'plant_group_2_J_0'
side_table_J[0].instance_id = 'side_table_J_0'
side_table_K[0].instance_id = 'side_table_K_0'
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
walls[10].instance_id = 'walls_10'
walls[11].instance_id = 'walls_11'
walls[12].instance_id = 'walls_12'
walls[13].instance_id = 'walls_13'
walls[14].instance_id = 'walls_14'
walls[15].instance_id = 'walls_15'
walls[16].instance_id = 'walls_16'

plant_A[0].position = [10.617221340802592, 7.176254177131905, 0.75]
plant_A[0].rotation = [0, 0, 0]
fruit_A[0].position = [12.868270537001369, 5.091843815678029, 0.045]
fruit_A[0].rotation = [0, 0, 0]
table_A[0].position = [6.873560861583599, 9.098592731075101, 0.375]
table_A[0].rotation = [0, 0, 0]
chair_A[0].position = [13.544567296346898, 1.074219839886862, 0.41]
chair_A[0].rotation = [0, 0, 0]
side_table_A[0].position = [9.281238898045027, 10.036519143766403, 0.275]
side_table_A[0].rotation = [0, 0, 0]
plant_B[0].position = [1.3315584922819783, 1.3223409874569214, 0.2]
plant_B[0].rotation = [0, 0, 0]
plant_C[0].position = [2.2338293382935133, 8.135070252030339, 0.6]
plant_C[0].rotation = [0, 0, 0]
chair_B[0].position = [5.099350305087663, 5.107651637167095, 0.41]
chair_B[0].rotation = [0, 0, 0]
plant_D[0].position = [13.019011834467962, 4.396981999175424, 0.45]
plant_D[0].rotation = [0, 0, 0]
fruit_B[0].position = [7.277250699921799, 7.970136120138503, 0.04]
fruit_B[0].rotation = [0, 0, 0]
chair_C[0].position = [11.689641393684699, 1.8902856928941323, 0.41]
chair_C[0].rotation = [0, 0, 0]
cup_A[0].position = [9.479413067272352, 5.232985557466265, 0.05]
cup_A[0].rotation = [0, 0, 0]
chair_D[0].position = [13.706672408812826, 0.795116397771662, 0.41]
chair_D[0].rotation = [0, 0, 0]
plant_E[0].position = [5.174250240007087, 7.160526394680079, 0.7]
plant_E[0].rotation = [0, 0, 0]
chair_E[0].position = [5.058859487746946, 5.24912754898407, 0.41]
chair_E[0].rotation = [0, 0, 0]
fruit_C[0].position = [5.622079491813983, 5.153597677192798, 0.05]
fruit_C[0].rotation = [0, 0, 0]
plant_F[0].position = [7.865486111232172, 10.074369449819276, 0.55]
plant_F[0].rotation = [0, 0, 0]
multi_person_sofa_A[0].position = [13.983978523548764, 4.590142379514699, 0.425]
multi_person_sofa_A[0].rotation = [0, 0, 0]
fruit_D[0].position = [12.574904920941561, 8.2676483147102, 0.045]
fruit_D[0].rotation = [0, 0, 0]
multi_person_sofa_B[0].position = [4.21762409319424, 7.645406481290438, 0.425]
multi_person_sofa_B[0].rotation = [0, 0, 0]
fruit_E[0].position = [8.199231724533, 0.5282633916825037, 0.04]
fruit_E[0].rotation = [0, 0, 0]
plant_G[0].position = [12.12963671167984, 9.273374241621152, 0.65]
plant_G[0].rotation = [0, 0, 0]
cup_B[0].position = [11.211207516557558, 6.23612352565397, 0.05]
cup_B[0].rotation = [0, 0, 0]
fruit_F[0].position = [4.386800592733997, 4.3816411541794205, 0.05]
fruit_F[0].rotation = [0, 0, 0]
high_chair_A[0].position = [9.072988173423893, 1.2887399367691657, 0.525]
high_chair_A[0].rotation = [0, 0, 0]
landscape_stone_A[0].position = [4.256210421613512, 1.4197725502697722, 0.175]
landscape_stone_A[0].rotation = [0, 0, 0]
plant_H[0].position = [3.7832918230930312, 2.0148781087160295, 0.7]
plant_H[0].rotation = [0, 0, 0]
side_table_B[0].position = [3.0781699921151713, 6.41502757409281, 0.275]
side_table_B[0].rotation = [0, 0, 0]
fruit_G[0].position = [12.60286362136617, 9.134086367538966, 0.045]
fruit_G[0].rotation = [0, 0, 0]
multi_person_sofa_C[0].position = [6.3303884198393225, 9.379230305206692, 0.425]
multi_person_sofa_C[0].rotation = [0, 0, 0]
chair_F[0].position = [7.852178050111696, 9.581778430909496, 0.41]
chair_F[0].rotation = [0, 0, 0]
plant_I[0].position = [0.9729350391912491, 9.137884322142698, 0.425]
plant_I[0].rotation = [0, 0, 0]
flowerpot_A[0].position = [1.3833044289855319, 2.1248433032304237, 0.18]
flowerpot_A[0].rotation = [0, 0, 0]
chair_G[0].position = [5.6427447303130105, 7.837694350556559, 0.41]
chair_G[0].rotation = [0, 0, 0]
plant_J[0].position = [3.949362892520773, 8.99113443185571, 0.2]
plant_J[0].rotation = [0, 0, 0]
side_table_C[0].position = [11.719088076932191, 6.312937427738753, 0.275]
side_table_C[0].rotation = [0, 0, 0]
fruit_H[0].position = [0.049787674858779545, 8.984279772944271, 0.04]
fruit_H[0].rotation = [0, 0, 0]
chair_H[0].position = [8.916462640964538, 7.1797887277803145, 0.41]
chair_H[0].rotation = [0, 0, 0]
chair_I[0].position = [13.533979858701851, 5.065616317705984, 0.41]
chair_I[0].rotation = [0, 0, 0]
chair_J[0].position = [9.40478343477465, 6.922424372376998, 0.41]
chair_J[0].rotation = [0, 0, 0]
chair_K[0].position = [1.8162921264030722, 4.030774812773261, 0.41]
chair_K[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [3.4796732738985967, 9.818404077021576, 0.825]
floor_lamp_A[0].rotation = [0, 0, 0]
plant_K[0].position = [3.7835647098651206, 5.33314997817384, 0.8]
plant_K[0].rotation = [0, 0, 0]
plant_L[0].position = [6.564912422520932, 9.664718684019638, 0.475]
plant_L[0].rotation = [0, 0, 0]
chair_L[0].position = [13.308673217317605, 5.626173613457153, 0.41]
chair_L[0].rotation = [0, 0, 0]
plant_M[0].position = [3.7281672332914786, 8.025656071693078, 0.175]
plant_M[0].rotation = [0, 0, 0]
plant_N[0].position = [8.803521396458516, 3.622321382277774, 0.575]
plant_N[0].rotation = [0, 0, 0]
fruit_I[0].position = [6.745340249887001, 8.171873371829053, 0.045]
fruit_I[0].rotation = [0, 0, 0]
plant_O[0].position = [1.6374100756622103, 4.610398190188038, 0.675]
plant_O[0].rotation = [0, 0, 0]
side_table_D[0].position = [13.964616554128897, 1.0909849425988534, 0.275]
side_table_D[0].rotation = [0, 0, 0]
chair_M[0].position = [1.982982909350666, 4.258111938028087, 0.41]
chair_M[0].rotation = [0, 0, 0]
flowerpot_B[0].position = [9.539475414092355, 0.7622931248521588, 0.17]
flowerpot_B[0].rotation = [0, 0, 0]
fruit_J[0].position = [7.2483904313419, 0.08690439258828742, 0.05]
fruit_J[0].rotation = [0, 0, 0]
plant_P[0].position = [9.357163240091666, 3.1677098814280638, 0.4]
plant_P[0].rotation = [0, 0, 0]
plant_Q[0].position = [6.810510509500287, 6.981094196010057, 0.6]
plant_Q[0].rotation = [0, 0, 0]
fruit_K[0].position = [5.386311442332733, 6.727425776440038, 0.04]
fruit_K[0].rotation = [0, 0, 0]
chair_N[0].position = [9.781127442885142, 7.758064342613868, 0.41]
chair_N[0].rotation = [0, 0, 0]
plant_R[0].position = [5.432021955789311, 1.8189474488480966, 0.225]
plant_R[0].rotation = [0, 0, 0]
side_table_E[0].position = [4.501439252493683, 3.2396907017200682, 0.275]
side_table_E[0].rotation = [0, 0, 0]
plant_S[0].position = [9.882486372467126, 2.0635154778775564, 0.7]
plant_S[0].rotation = [0, 0, 0]
fruit_L[0].position = [12.767533679734225, 7.827702458308081, 0.045]
fruit_L[0].rotation = [0, 0, 0]
high_chair_B[0].position = [13.91468042002167, 3.9824280793882196, 0.525]
high_chair_B[0].rotation = [0, 0, 0]
side_table_F[0].position = [9.143359749243878, 6.750715900279881, 0.275]
side_table_F[0].rotation = [0, 0, 0]
chair_O[0].position = [12.353008652227576, 3.360721253655317, 0.41]
chair_O[0].rotation = [0, 0, 0]
table_B[0].position = [2.307352597100678, 1.5653819006058964, 0.375]
table_B[0].rotation = [0, 0, 0]
chair_P[0].position = [13.746683398449777, 7.577589565911292, 0.41]
chair_P[0].rotation = [0, 0, 0]
flowerpot_C[0].position = [4.583765193821065, 3.9471027440441255, 0.18]
flowerpot_C[0].rotation = [0, 0, 0]
chair_Q[0].position = [7.424821668806926, 3.6442900385225934, 0.41]
chair_Q[0].rotation = [0, 0, 0]
plant_T[0].position = [1.4646683511332153, 7.267858269893803, 0.45]
plant_T[0].rotation = [0, 0, 0]
dining_plate[0].position = [13.792217381962953, 8.916236747686701, 0.0125]
dining_plate[0].rotation = [0, 0, 0]
chair_R[0].position = [3.926225602247111, 9.024218588006528, 0.41]
chair_R[0].rotation = [0, 0, 0]
high_chair_C[0].position = [5.559533517824101, 3.7785233799514506, 0.525]
high_chair_C[0].rotation = [0, 0, 0]
fruit_M[0].position = [5.913405451269104, 5.379126663268403, 0.045]
fruit_M[0].rotation = [0, 0, 0]
fruit_N[0].position = [0.3058409136389647, 8.453686364780026, 0.04]
fruit_N[0].rotation = [0, 0, 0]
multi_person_sofa_D[0].position = [10.916560702958673, 6.167301148287413, 0.425]
multi_person_sofa_D[0].rotation = [0, 0, 0]
plant_U[0].position = [1.9281695404539483, 5.214306024107029, 0.625]
plant_U[0].rotation = [0, 0, 0]
plant_V[0].position = [5.856191627002608, 1.6358503504054305, 0.45]
plant_V[0].rotation = [0, 0, 0]
fruit_O[0].position = [9.026759530192571, 9.969874133303115, 0.05]
fruit_O[0].rotation = [0, 0, 0]
multi_person_sofa_E[0].position = [11.454305777217733, 4.536046312318257, 0.425]
multi_person_sofa_E[0].rotation = [0, 0, 0]
plant_W[0].position = [12.629389844634447, 8.06072883841789, 0.75]
plant_W[0].rotation = [0, 0, 0]
fruit_P[0].position = [11.068998009756745, 1.022467369171242, 0.045]
fruit_P[0].rotation = [0, 0, 0]
multi_person_sofa_F[0].position = [11.206032198048849, 5.69775060128087, 0.425]
multi_person_sofa_F[0].rotation = [0, 0, 0]
fruit_Q[0].position = [6.894669600014414, 9.30087908932557, 0.04]
fruit_Q[0].rotation = [0, 0, 0]
plant_X[0].position = [7.094169038071282, 5.6940141247208444, 0.175]
plant_X[0].rotation = [0, 0, 0]
chair_S[0].position = [6.787998260719234, 1.2324460734780525, 0.41]
chair_S[0].rotation = [0, 0, 0]
table_C[0].position = [11.372234082108594, 3.0107408347478244, 0.375]
table_C[0].rotation = [0, 0, 0]
stool[0].position = [8.797943365349012, 0.7141746191458603, 0.23]
stool[0].rotation = [0, 0, 0]
fruit_R[0].position = [8.746200063839305, 5.346221801981874, 0.045]
fruit_R[0].rotation = [0, 0, 0]
fruit_S[0].position = [5.04489235788079, 8.396366184059982, 0.05]
fruit_S[0].rotation = [0, 0, 0]
flowerpot_D[0].position = [1.485527348964332, 3.9869318055885237, 0.18]
flowerpot_D[0].rotation = [0, 0, 0]
chair_T[0].position = [8.81616593737657, 9.007859736073344, 0.41]
chair_T[0].rotation = [0, 0, 0]
chair_U[0].position = [3.3396489233649764, 7.4352122139126875, 0.41]
chair_U[0].rotation = [0, 0, 0]
fruit_T[0].position = [1.436091925905319, 5.182595214812962, 0.04]
fruit_T[0].rotation = [0, 0, 0]
chair_V[0].position = [8.473162462885943, 8.905818995397569, 0.41]
chair_V[0].rotation = [0, 0, 0]
wall_lamp[0].position = [7.729455445211027, 6.31061692031484, 0.175]
wall_lamp[0].rotation = [0, 0, 0]
wine[0].position = [5.8998622770882285, 8.758742510859248, 0.15]
wine[0].rotation = [0, 0, 0]
fruit_U[0].position = [8.022693075245229, 9.786162333096009, 0.045]
fruit_U[0].rotation = [0, 0, 0]
plant_Y[0].position = [13.31543641058551, 0.9493577128876213, 0.475]
plant_Y[0].rotation = [0, 0, 0]
plant_Z[0].position = [3.4190618626163705, 8.313077669737664, 0.625]
plant_Z[0].rotation = [0, 0, 0]
plant_group_2_A[0].position = [7.22157106011126, 6.456625447387202, 0.5]
plant_group_2_A[0].rotation = [0, 0, 0]
fruit_V[0].position = [3.7815269664625983, 4.310896116538128, 0.05]
fruit_V[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [5.602713189978469, 2.2420884881140952, 0.825]
floor_lamp_B[0].rotation = [0, 0, 0]
landscape_stone_B[0].position = [1.563704778143696, 4.719151479373636, 0.15]
landscape_stone_B[0].rotation = [0, 0, 0]
plant_group_2_B[0].position = [2.23597325529703, 3.0388360158204186, 0.725]
plant_group_2_B[0].rotation = [0, 0, 0]
fruit_W[0].position = [10.66289895029524, 0.5935774533098164, 0.04]
fruit_W[0].rotation = [0, 0, 0]
fruit_X[0].position = [5.259384115314945, 0.08291071244252204, 0.045]
fruit_X[0].rotation = [0, 0, 0]
chair_W[0].position = [6.747553641080537, 8.935236926468585, 0.41]
chair_W[0].rotation = [0, 0, 0]
plant_group_2_C[0].position = [4.317721579190781, 2.384848817567878, 0.2]
plant_group_2_C[0].rotation = [0, 0, 0]
multi_person_sofa_G[0].position = [3.548944730529337, 6.039834957174802, 0.425]
multi_person_sofa_G[0].rotation = [0, 0, 0]
side_table_G[0].position = [11.973915620546503, 0.7385046787223424, 0.275]
side_table_G[0].rotation = [0, 0, 0]
multi_person_sofa_H[0].position = [12.84032268240738, 7.882851749780765, 0.425]
multi_person_sofa_H[0].rotation = [0, 0, 0]
fruit_Y[0].position = [9.794230474817747, 1.4274046738836117, 0.04]
fruit_Y[0].rotation = [0, 0, 0]
high_chair_D[0].position = [5.14062365918681, 4.969639315367645, 0.525]
high_chair_D[0].rotation = [0, 0, 0]
plant_group_2_D[0].position = [10.002484936586418, 2.0183835874772598, 0.175]
plant_group_2_D[0].rotation = [0, 0, 0]
side_table_H[0].position = [8.097908191921658, 9.393965992312358, 0.275]
side_table_H[0].rotation = [0, 0, 0]
shelf[0].position = [5.296117833686803, 6.183100041525689, 0.9]
shelf[0].rotation = [0, 0, 0]
chair_X[0].position = [5.956177780780536, 6.2137382978232925, 0.41]
chair_X[0].rotation = [0, 0, 0]
chair_Y[0].position = [10.644560539459135, 7.4594053175669774, 0.41]
chair_Y[0].rotation = [0, 0, 0]
chair_Z[0].position = [12.903888673024513, 9.41300300516119, 0.41]
chair_Z[0].rotation = [0, 0, 0]
plant_group_2_E[0].position = [2.761594714491149, 4.1233755475674165, 0.55]
plant_group_2_E[0].rotation = [0, 0, 0]
plant_group_2_F[0].position = [11.484666042864589, 7.653755116738576, 0.7]
plant_group_2_F[0].rotation = [0, 0, 0]
floor_lamp_C[0].position = [9.44149120897586, 0.18281175189723364, 0.825]
floor_lamp_C[0].rotation = [0, 0, 0]
landscape_stone_C[0].position = [5.030118190557074, 4.462890281221306, 0.2]
landscape_stone_C[0].rotation = [0, 0, 0]
fruit_Z[0].position = [2.2920753045325863, 1.5687136445180851, 0.05]
fruit_Z[0].rotation = [0, 0, 0]
fruit_group_2_A[0].position = [8.008497262633947, 1.397951670657433, 0.045]
fruit_group_2_A[0].rotation = [0, 0, 0]
plant_group_2_G[0].position = [5.742519008431667, 6.1415265121614455, 0.225]
plant_group_2_G[0].rotation = [0, 0, 0]
fruit_group_2_B[0].position = [12.966636786247445, 2.4815190924095827, 0.04]
fruit_group_2_B[0].rotation = [0, 0, 0]
water_bar[0].position = [4.394111621566379, 7.1591703441901275, 0.525]
water_bar[0].rotation = [0, 0, 0]
chair_group_2_A[0].position = [1.3687317865416717, 1.1171470170844067, 0.41]
chair_group_2_A[0].rotation = [0, 0, 0]
fruit_group_2_C[0].position = [11.003853444366701, 6.404933078686163, 0.045]
fruit_group_2_C[0].rotation = [0, 0, 0]
billboard[0].position = [2.0821646656139725, 7.299033768304631, 0.45]
billboard[0].rotation = [0, 0, 0]
jar[0].position = [8.604107875241525, 4.694151911127004, 0.125]
jar[0].rotation = [0, 0, 0]
fruit_group_2_D[0].position = [1.479008415604825, 7.158138847974781, 0.05]
fruit_group_2_D[0].rotation = [0, 0, 0]
flowerpot_E[0].position = [11.489002224218693, 7.804627169359122, 0.18]
flowerpot_E[0].rotation = [0, 0, 0]
side_table_I[0].position = [6.616853488061107, 9.603918523533396, 0.275]
side_table_I[0].rotation = [0, 0, 0]
chair_group_2_B[0].position = [10.38039292922794, 9.77386272373443, 0.41]
chair_group_2_B[0].rotation = [0, 0, 0]
landscape_stone_D[0].position = [10.849744234069089, 5.253708264375397, 0.15]
landscape_stone_D[0].rotation = [0, 0, 0]
high_chair_E[0].position = [8.252670109008044, 2.903104148327602, 0.525]
high_chair_E[0].rotation = [0, 0, 0]
fruit_group_2_E[0].position = [9.501293413966359, 7.00746164285229, 0.04]
fruit_group_2_E[0].rotation = [0, 0, 0]
table_D[0].position = [10.71198480805035, 7.292457303235942, 0.375]
table_D[0].rotation = [0, 0, 0]
plant_group_2_H[0].position = [4.798127858943068, 6.490456150542945, 0.45]
plant_group_2_H[0].rotation = [0, 0, 0]
chair_group_2_C[0].position = [5.635388560564619, 7.765951009346927, 0.41]
chair_group_2_C[0].rotation = [0, 0, 0]
cup_C[0].position = [12.368044884619268, 4.72215644413021, 0.05]
cup_C[0].rotation = [0, 0, 0]
multi_person_sofa_I[0].position = [12.2480018905322, 0.7914737021084725, 0.425]
multi_person_sofa_I[0].rotation = [0, 0, 0]
fruit_group_2_F[0].position = [12.707460334145017, 9.988728511586602, 0.045]
fruit_group_2_F[0].rotation = [0, 0, 0]
chair_group_2_D[0].position = [14.096988869394742, 2.2550070747282662, 0.41]
chair_group_2_D[0].rotation = [0, 0, 0]
chair_group_2_E[0].position = [11.562097480611225, 9.618780750185582, 0.41]
chair_group_2_E[0].rotation = [0, 0, 0]
plant_group_2_I[0].position = [4.677751358852882, 6.150575903263827, 0.2]
plant_group_2_I[0].rotation = [0, 0, 0]
plant_group_2_J[0].position = [8.594726011983344, 4.943030227599958, 0.2]
plant_group_2_J[0].rotation = [0, 0, 0]
side_table_J[0].position = [12.79834485736972, 7.504701195585733, 0.275]
side_table_J[0].rotation = [0, 0, 0]
side_table_K[0].position = [8.160036548535988, 6.53047186641066, 0.275]
side_table_K[0].rotation = [0, 0, 0]
plant_A[0].position = [10.617221340802592, 7.176254177131905, 0.75]
plant_A[0].rotation = [0, 0, 0]
fruit_A[0].position = [12.868270537001369, 5.091843815678029, 0.045]
fruit_A[0].rotation = [0, 0, 0]
table_A[0].position = [6.873560861583599, 9.098592731075101, 0.375]
table_A[0].rotation = [0, 0, 0]
chair_A[0].position = [13.544567296346898, 1.074219839886862, 0.41]
chair_A[0].rotation = [0, 0, 0]
side_table_A[0].position = [9.281238898045027, 10.036519143766403, 0.275]
side_table_A[0].rotation = [0, 0, 0]
plant_B[0].position = [1.3315584922819783, 1.3223409874569214, 0.2]
plant_B[0].rotation = [0, 0, 0]
plant_C[0].position = [2.2338293382935133, 8.135070252030339, 0.6]
plant_C[0].rotation = [0, 0, 0]
chair_B[0].position = [5.099350305087663, 5.107651637167095, 0.41]
chair_B[0].rotation = [0, 0, 0]
plant_D[0].position = [13.019011834467962, 4.396981999175424, 0.45]
plant_D[0].rotation = [0, 0, 0]
fruit_B[0].position = [7.277250699921799, 7.970136120138503, 0.04]
fruit_B[0].rotation = [0, 0, 0]
chair_C[0].position = [11.689641393684699, 1.8902856928941323, 0.41]
chair_C[0].rotation = [0, 0, 0]
cup_A[0].position = [9.479413067272352, 5.232985557466265, 0.05]
cup_A[0].rotation = [0, 0, 0]
chair_D[0].position = [13.706672408812826, 0.795116397771662, 0.41]
chair_D[0].rotation = [0, 0, 0]
plant_E[0].position = [5.174250240007087, 7.160526394680079, 0.7]
plant_E[0].rotation = [0, 0, 0]
chair_E[0].position = [5.058859487746946, 5.24912754898407, 0.41]
chair_E[0].rotation = [0, 0, 0]
fruit_C[0].position = [5.622079491813983, 5.153597677192798, 0.05]
fruit_C[0].rotation = [0, 0, 0]
plant_F[0].position = [7.865486111232172, 10.074369449819276, 0.55]
plant_F[0].rotation = [0, 0, 0]
multi_person_sofa_A[0].position = [13.983978523548764, 4.590142379514699, 0.425]
multi_person_sofa_A[0].rotation = [0, 0, 0]
fruit_D[0].position = [12.574904920941561, 8.2676483147102, 0.045]
fruit_D[0].rotation = [0, 0, 0]
multi_person_sofa_B[0].position = [4.21762409319424, 7.645406481290438, 0.425]
multi_person_sofa_B[0].rotation = [0, 0, 0]
fruit_E[0].position = [8.199231724533, 0.5282633916825037, 0.04]
fruit_E[0].rotation = [0, 0, 0]
plant_G[0].position = [12.12963671167984, 9.273374241621152, 0.65]
plant_G[0].rotation = [0, 0, 0]
cup_B[0].position = [11.211207516557558, 6.23612352565397, 0.05]
cup_B[0].rotation = [0, 0, 0]
fruit_F[0].position = [4.386800592733997, 4.3816411541794205, 0.05]
fruit_F[0].rotation = [0, 0, 0]
high_chair_A[0].position = [9.072988173423893, 1.2887399367691657, 0.525]
high_chair_A[0].rotation = [0, 0, 0]
landscape_stone_A[0].position = [4.256210421613512, 1.4197725502697722, 0.175]
landscape_stone_A[0].rotation = [0, 0, 0]
plant_H[0].position = [3.7832918230930312, 2.0148781087160295, 0.7]
plant_H[0].rotation = [0, 0, 0]
side_table_B[0].position = [3.0781699921151713, 6.41502757409281, 0.275]
side_table_B[0].rotation = [0, 0, 0]
fruit_G[0].position = [12.60286362136617, 9.134086367538966, 0.045]
fruit_G[0].rotation = [0, 0, 0]
multi_person_sofa_C[0].position = [6.3303884198393225, 9.379230305206692, 0.425]
multi_person_sofa_C[0].rotation = [0, 0, 0]
chair_F[0].position = [7.852178050111696, 9.581778430909496, 0.41]
chair_F[0].rotation = [0, 0, 0]
plant_I[0].position = [0.9729350391912491, 9.137884322142698, 0.425]
plant_I[0].rotation = [0, 0, 0]
flowerpot_A[0].position = [1.3833044289855319, 2.1248433032304237, 0.18]
flowerpot_A[0].rotation = [0, 0, 0]
chair_G[0].position = [5.6427447303130105, 7.837694350556559, 0.41]
chair_G[0].rotation = [0, 0, 0]
plant_J[0].position = [3.949362892520773, 8.99113443185571, 0.2]
plant_J[0].rotation = [0, 0, 0]
side_table_C[0].position = [11.719088076932191, 6.312937427738753, 0.275]
side_table_C[0].rotation = [0, 0, 0]
fruit_H[0].position = [0.049787674858779545, 8.984279772944271, 0.04]
fruit_H[0].rotation = [0, 0, 0]
chair_H[0].position = [8.916462640964538, 7.1797887277803145, 0.41]
chair_H[0].rotation = [0, 0, 0]
chair_I[0].position = [13.533979858701851, 5.065616317705984, 0.41]
chair_I[0].rotation = [0, 0, 0]
chair_J[0].position = [9.40478343477465, 6.922424372376998, 0.41]
chair_J[0].rotation = [0, 0, 0]
chair_K[0].position = [1.8162921264030722, 4.030774812773261, 0.41]
chair_K[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [3.4796732738985967, 9.818404077021576, 0.825]
floor_lamp_A[0].rotation = [0, 0, 0]
plant_K[0].position = [3.7835647098651206, 5.33314997817384, 0.8]
plant_K[0].rotation = [0, 0, 0]
plant_L[0].position = [6.564912422520932, 9.664718684019638, 0.475]
plant_L[0].rotation = [0, 0, 0]
chair_L[0].position = [13.308673217317605, 5.626173613457153, 0.41]
chair_L[0].rotation = [0, 0, 0]
plant_M[0].position = [3.7281672332914786, 8.025656071693078, 0.175]
plant_M[0].rotation = [0, 0, 0]
plant_N[0].position = [8.803521396458516, 3.622321382277774, 0.575]
plant_N[0].rotation = [0, 0, 0]
fruit_I[0].position = [6.745340249887001, 8.171873371829053, 0.045]
fruit_I[0].rotation = [0, 0, 0]
plant_O[0].position = [1.6374100756622103, 4.610398190188038, 0.675]
plant_O[0].rotation = [0, 0, 0]
side_table_D[0].position = [13.964616554128897, 1.0909849425988534, 0.275]
side_table_D[0].rotation = [0, 0, 0]
chair_M[0].position = [1.982982909350666, 4.258111938028087, 0.41]
chair_M[0].rotation = [0, 0, 0]
flowerpot_B[0].position = [9.539475414092355, 0.7622931248521588, 0.17]
flowerpot_B[0].rotation = [0, 0, 0]
fruit_J[0].position = [7.2483904313419, 0.08690439258828742, 0.05]
fruit_J[0].rotation = [0, 0, 0]
plant_P[0].position = [9.357163240091666, 3.1677098814280638, 0.4]
plant_P[0].rotation = [0, 0, 0]
plant_Q[0].position = [6.810510509500287, 6.981094196010057, 0.6]
plant_Q[0].rotation = [0, 0, 0]
fruit_K[0].position = [5.386311442332733, 6.727425776440038, 0.04]
fruit_K[0].rotation = [0, 0, 0]
chair_N[0].position = [9.781127442885142, 7.758064342613868, 0.41]
chair_N[0].rotation = [0, 0, 0]
plant_R[0].position = [5.432021955789311, 1.8189474488480966, 0.225]
plant_R[0].rotation = [0, 0, 0]
side_table_E[0].position = [4.501439252493683, 3.2396907017200682, 0.275]
side_table_E[0].rotation = [0, 0, 0]
plant_S[0].position = [9.882486372467126, 2.0635154778775564, 0.7]
plant_S[0].rotation = [0, 0, 0]
fruit_L[0].position = [12.767533679734225, 7.827702458308081, 0.045]
fruit_L[0].rotation = [0, 0, 0]
high_chair_B[0].position = [13.91468042002167, 3.9824280793882196, 0.525]
high_chair_B[0].rotation = [0, 0, 0]
side_table_F[0].position = [9.143359749243878, 6.750715900279881, 0.275]
side_table_F[0].rotation = [0, 0, 0]
chair_O[0].position = [12.353008652227576, 3.360721253655317, 0.41]
chair_O[0].rotation = [0, 0, 0]
table_B[0].position = [2.307352597100678, 1.5653819006058964, 0.375]
table_B[0].rotation = [0, 0, 0]
chair_P[0].position = [13.746683398449777, 7.577589565911292, 0.41]
chair_P[0].rotation = [0, 0, 0]
flowerpot_C[0].position = [4.583765193821065, 3.9471027440441255, 0.18]
flowerpot_C[0].rotation = [0, 0, 0]
chair_Q[0].position = [7.424821668806926, 3.6442900385225934, 0.41]
chair_Q[0].rotation = [0, 0, 0]
plant_T[0].position = [1.4646683511332153, 7.267858269893803, 0.45]
plant_T[0].rotation = [0, 0, 0]
dining_plate[0].position = [13.792217381962953, 8.916236747686701, 0.0125]
dining_plate[0].rotation = [0, 0, 0]
chair_R[0].position = [3.926225602247111, 9.024218588006528, 0.41]
chair_R[0].rotation = [0, 0, 0]
high_chair_C[0].position = [5.559533517824101, 3.7785233799514506, 0.525]
high_chair_C[0].rotation = [0, 0, 0]
fruit_M[0].position = [5.913405451269104, 5.379126663268403, 0.045]
fruit_M[0].rotation = [0, 0, 0]
fruit_N[0].position = [0.3058409136389647, 8.453686364780026, 0.04]
fruit_N[0].rotation = [0, 0, 0]
multi_person_sofa_D[0].position = [10.916560702958673, 6.167301148287413, 0.425]
multi_person_sofa_D[0].rotation = [0, 0, 0]
plant_U[0].position = [1.9281695404539483, 5.214306024107029, 0.625]
plant_U[0].rotation = [0, 0, 0]
plant_V[0].position = [5.856191627002608, 1.6358503504054305, 0.45]
plant_V[0].rotation = [0, 0, 0]
fruit_O[0].position = [9.026759530192571, 9.969874133303115, 0.05]
fruit_O[0].rotation = [0, 0, 0]
multi_person_sofa_E[0].position = [11.454305777217733, 4.536046312318257, 0.425]
multi_person_sofa_E[0].rotation = [0, 0, 0]
plant_W[0].position = [12.629389844634447, 8.06072883841789, 0.75]
plant_W[0].rotation = [0, 0, 0]
fruit_P[0].position = [11.068998009756745, 1.022467369171242, 0.045]
fruit_P[0].rotation = [0, 0, 0]
multi_person_sofa_F[0].position = [11.206032198048849, 5.69775060128087, 0.425]
multi_person_sofa_F[0].rotation = [0, 0, 0]
fruit_Q[0].position = [6.894669600014414, 9.30087908932557, 0.04]
fruit_Q[0].rotation = [0, 0, 0]
plant_X[0].position = [7.094169038071282, 5.6940141247208444, 0.175]
plant_X[0].rotation = [0, 0, 0]
chair_S[0].position = [6.787998260719234, 1.2324460734780525, 0.41]
chair_S[0].rotation = [0, 0, 0]
table_C[0].position = [11.372234082108594, 3.0107408347478244, 0.375]
table_C[0].rotation = [0, 0, 0]
stool[0].position = [8.797943365349012, 0.7141746191458603, 0.23]
stool[0].rotation = [0, 0, 0]
fruit_R[0].position = [8.746200063839305, 5.346221801981874, 0.045]
fruit_R[0].rotation = [0, 0, 0]
fruit_S[0].position = [5.04489235788079, 8.396366184059982, 0.05]
fruit_S[0].rotation = [0, 0, 0]
flowerpot_D[0].position = [1.485527348964332, 3.9869318055885237, 0.18]
flowerpot_D[0].rotation = [0, 0, 0]
chair_T[0].position = [8.81616593737657, 9.007859736073344, 0.41]
chair_T[0].rotation = [0, 0, 0]
chair_U[0].position = [3.3396489233649764, 7.4352122139126875, 0.41]
chair_U[0].rotation = [0, 0, 0]
fruit_T[0].position = [1.436091925905319, 5.182595214812962, 0.04]
fruit_T[0].rotation = [0, 0, 0]
chair_V[0].position = [8.473162462885943, 8.905818995397569, 0.41]
chair_V[0].rotation = [0, 0, 0]
wall_lamp[0].position = [7.729455445211027, 6.31061692031484, 0.175]
wall_lamp[0].rotation = [0, 0, 0]
wine[0].position = [5.8998622770882285, 8.758742510859248, 0.15]
wine[0].rotation = [0, 0, 0]
fruit_U[0].position = [8.022693075245229, 9.786162333096009, 0.045]
fruit_U[0].rotation = [0, 0, 0]
plant_Y[0].position = [13.31543641058551, 0.9493577128876213, 0.475]
plant_Y[0].rotation = [0, 0, 0]
plant_Z[0].position = [3.4190618626163705, 8.313077669737664, 0.625]
plant_Z[0].rotation = [0, 0, 0]
plant_group_2_A[0].position = [7.22157106011126, 6.456625447387202, 0.5]
plant_group_2_A[0].rotation = [0, 0, 0]
fruit_V[0].position = [3.7815269664625983, 4.310896116538128, 0.05]
fruit_V[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [5.602713189978469, 2.2420884881140952, 0.825]
floor_lamp_B[0].rotation = [0, 0, 0]
landscape_stone_B[0].position = [1.563704778143696, 4.719151479373636, 0.15]
landscape_stone_B[0].rotation = [0, 0, 0]
plant_group_2_B[0].position = [2.23597325529703, 3.0388360158204186, 0.725]
plant_group_2_B[0].rotation = [0, 0, 0]
fruit_W[0].position = [10.66289895029524, 0.5935774533098164, 0.04]
fruit_W[0].rotation = [0, 0, 0]
fruit_X[0].position = [5.259384115314945, 0.08291071244252204, 0.045]
fruit_X[0].rotation = [0, 0, 0]
chair_W[0].position = [6.747553641080537, 8.935236926468585, 0.41]
chair_W[0].rotation = [0, 0, 0]
plant_group_2_C[0].position = [4.317721579190781, 2.384848817567878, 0.2]
plant_group_2_C[0].rotation = [0, 0, 0]
multi_person_sofa_G[0].position = [3.548944730529337, 6.039834957174802, 0.425]
multi_person_sofa_G[0].rotation = [0, 0, 0]
side_table_G[0].position = [11.973915620546503, 0.7385046787223424, 0.275]
side_table_G[0].rotation = [0, 0, 0]
multi_person_sofa_H[0].position = [12.84032268240738, 7.882851749780765, 0.425]
multi_person_sofa_H[0].rotation = [0, 0, 0]
fruit_Y[0].position = [9.794230474817747, 1.4274046738836117, 0.04]
fruit_Y[0].rotation = [0, 0, 0]
high_chair_D[0].position = [5.14062365918681, 4.969639315367645, 0.525]
high_chair_D[0].rotation = [0, 0, 0]
plant_group_2_D[0].position = [10.002484936586418, 2.0183835874772598, 0.175]
plant_group_2_D[0].rotation = [0, 0, 0]
side_table_H[0].position = [8.097908191921658, 9.393965992312358, 0.275]
side_table_H[0].rotation = [0, 0, 0]
shelf[0].position = [5.296117833686803, 6.183100041525689, 0.9]
shelf[0].rotation = [0, 0, 0]
chair_X[0].position = [5.956177780780536, 6.2137382978232925, 0.41]
chair_X[0].rotation = [0, 0, 0]
chair_Y[0].position = [10.644560539459135, 7.4594053175669774, 0.41]
chair_Y[0].rotation = [0, 0, 0]
chair_Z[0].position = [12.903888673024513, 9.41300300516119, 0.41]
chair_Z[0].rotation = [0, 0, 0]
plant_group_2_E[0].position = [2.761594714491149, 4.1233755475674165, 0.55]
plant_group_2_E[0].rotation = [0, 0, 0]
plant_group_2_F[0].position = [11.484666042864589, 7.653755116738576, 0.7]
plant_group_2_F[0].rotation = [0, 0, 0]
floor_lamp_C[0].position = [9.44149120897586, 0.18281175189723364, 0.825]
floor_lamp_C[0].rotation = [0, 0, 0]
landscape_stone_C[0].position = [5.030118190557074, 4.462890281221306, 0.2]
landscape_stone_C[0].rotation = [0, 0, 0]
fruit_Z[0].position = [2.2920753045325863, 1.5687136445180851, 0.05]
fruit_Z[0].rotation = [0, 0, 0]
fruit_group_2_A[0].position = [8.008497262633947, 1.397951670657433, 0.045]
fruit_group_2_A[0].rotation = [0, 0, 0]
plant_group_2_G[0].position = [5.742519008431667, 6.1415265121614455, 0.225]
plant_group_2_G[0].rotation = [0, 0, 0]
fruit_group_2_B[0].position = [12.966636786247445, 2.4815190924095827, 0.04]
fruit_group_2_B[0].rotation = [0, 0, 0]
water_bar[0].position = [4.394111621566379, 7.1591703441901275, 0.525]
water_bar[0].rotation = [0, 0, 0]
chair_group_2_A[0].position = [1.3687317865416717, 1.1171470170844067, 0.41]
chair_group_2_A[0].rotation = [0, 0, 0]
fruit_group_2_C[0].position = [11.003853444366701, 6.404933078686163, 0.045]
fruit_group_2_C[0].rotation = [0, 0, 0]
billboard[0].position = [2.0821646656139725, 7.299033768304631, 0.45]
billboard[0].rotation = [0, 0, 0]
jar[0].position = [8.604107875241525, 4.694151911127004, 0.125]
jar[0].rotation = [0, 0, 0]
fruit_group_2_D[0].position = [1.479008415604825, 7.158138847974781, 0.05]
fruit_group_2_D[0].rotation = [0, 0, 0]
flowerpot_E[0].position = [11.489002224218693, 7.804627169359122, 0.18]
flowerpot_E[0].rotation = [0, 0, 0]
side_table_I[0].position = [6.616853488061107, 9.603918523533396, 0.275]
side_table_I[0].rotation = [0, 0, 0]
chair_group_2_B[0].position = [10.38039292922794, 9.77386272373443, 0.41]
chair_group_2_B[0].rotation = [0, 0, 0]
landscape_stone_D[0].position = [10.849744234069089, 5.253708264375397, 0.15]
landscape_stone_D[0].rotation = [0, 0, 0]
high_chair_E[0].position = [8.252670109008044, 2.903104148327602, 0.525]
high_chair_E[0].rotation = [0, 0, 0]
fruit_group_2_E[0].position = [9.501293413966359, 7.00746164285229, 0.04]
fruit_group_2_E[0].rotation = [0, 0, 0]
table_D[0].position = [10.71198480805035, 7.292457303235942, 0.375]
table_D[0].rotation = [0, 0, 0]
plant_group_2_H[0].position = [4.798127858943068, 6.490456150542945, 0.45]
plant_group_2_H[0].rotation = [0, 0, 0]
chair_group_2_C[0].position = [5.635388560564619, 7.765951009346927, 0.41]
chair_group_2_C[0].rotation = [0, 0, 0]
cup_C[0].position = [12.368044884619268, 4.72215644413021, 0.05]
cup_C[0].rotation = [0, 0, 0]
multi_person_sofa_I[0].position = [12.2480018905322, 0.7914737021084725, 0.425]
multi_person_sofa_I[0].rotation = [0, 0, 0]
fruit_group_2_F[0].position = [12.707460334145017, 9.988728511586602, 0.045]
fruit_group_2_F[0].rotation = [0, 0, 0]
chair_group_2_D[0].position = [14.096988869394742, 2.2550070747282662, 0.41]
chair_group_2_D[0].rotation = [0, 0, 0]
chair_group_2_E[0].position = [11.562097480611225, 9.618780750185582, 0.41]
chair_group_2_E[0].rotation = [0, 0, 0]
plant_group_2_I[0].position = [4.677751358852882, 6.150575903263827, 0.2]
plant_group_2_I[0].rotation = [0, 0, 0]
plant_group_2_J[0].position = [8.594726011983344, 4.943030227599958, 0.2]
plant_group_2_J[0].rotation = [0, 0, 0]
side_table_J[0].position = [12.79834485736972, 7.504701195585733, 0.275]
side_table_J[0].rotation = [0, 0, 0]
side_table_K[0].position = [8.160036548535988, 6.53047186641066, 0.275]
side_table_K[0].rotation = [0, 0, 0]

solver.constraints = []

# Coordinates follow the supplied plan (rather than recentering its origin).
# Fixed columns, partitions and the cabinet are treated as exclusion zones.
# Keep the west entrance approach and the east door/partition vestibule empty.

def place_floor(asset_ref, x, y, yaw=0, facing=None):
    inst = asset_ref[0]
    inst.position = [x, y, asset_ref.size[2] / 2]
    inst.rotation = [0, 0, radians(yaw)]
    # Exact fixed-point constraints preserve the checked layout and clearances.
    solver.distance_constraint(
        inst, AssetInstance(position=list(inst.position)), 0, 0, weight=10
    )
    if facing is None:
        solver.align_with(
            inst, AssetInstance(rotation=[0, 0, radians(yaw)])
        )
    else:
        solver.point_towards(inst, facing)


def place_surface(asset_ref, support_ref, dx=0, dy=0, yaw=0):
    support_inst = support_ref[0]
    inst = asset_ref[0]
    inst.position = [
        support_inst.position[0] + dx,
        support_inst.position[1] + dy,
        support_inst.position[2]
        + support_ref.size[2] / 2
        + asset_ref.size[2] / 2,
    ]
    inst.rotation = [0, 0, radians(yaw)]
    # Support is the first priority; the fixed point preserves the tabletop offset.
    solver.on_top_of(inst, support_inst)
    solver.distance_constraint(
        inst, AssetInstance(position=list(inst.position)), 0, 0, weight=10
    )
    solver.align_with(
        inst, AssetInstance(rotation=[0, 0, radians(yaw)])
    )


# Refreshment counter: leave working space between it and the fixed cabinet.
place_floor(water_bar, 3.00, 2.00)
place_floor(shelf, 1.47, 4.70)
solver.against_wall(shelf[0], walls[15])

# Five counter seats face the bar, with enough spacing for their footprints.
for seat_ref, seat_y in zip(
    [high_chair_A, high_chair_B, high_chair_C, high_chair_D, high_chair_E],
    [0.80, 1.40, 2.00, 2.60, 3.20],
):
    place_floor(
        seat_ref, 4.10, seat_y, 180,
        facing=AssetInstance(position=[3.00, seat_y, 0.525]),
    )
    solver.distance_constraint(seat_ref[0], water_bar[0], 1.10, 1.70)


# Four compact dining groups in the southern part of the room.
# The northern chairs end below the fixed partition at y=3.20.
dining_layout = [
    (table_A, 5.50, [chair_A, chair_B, chair_C, chair_D]),
    (table_B, 7.90, [chair_E, chair_F, chair_G, chair_H]),
    (table_C, 10.30, [chair_I, chair_J, chair_K, chair_L]),
    (table_D, 12.70, [chair_M, chair_N, chair_O, chair_P]),
]
for table_ref, table_x, seat_refs in dining_layout:
    place_floor(table_ref, table_x, 1.80)
    for seat_ref, dx, dy, yaw in [
        (seat_refs[0], -0.82, 0.00, 0),
        (seat_refs[1], 0.82, 0.00, 180),
        (seat_refs[2], 0.00, -1.00, 90),
        (seat_refs[3], 0.00, 1.00, 270),
    ]:
        place_floor(
            seat_ref, table_x + dx, 1.80 + dy, yaw,
            facing=table_ref[0],
        )
        solver.distance_constraint(seat_ref[0], table_ref[0], 0.80, 1.05)


# Northern lounge: sofas face south. Their long local y dimension becomes
# east-west after the 270-degree rotation.
north_lounge = [
    (multi_person_sofa_A, side_table_A, 3.70),
    (multi_person_sofa_B, side_table_B, 6.05),
    (multi_person_sofa_C, side_table_C, 8.40),
    (multi_person_sofa_D, side_table_D, 10.75),
    (multi_person_sofa_E, side_table_E, 13.10),
]
north_seats = [
    chair_Q, chair_R, chair_S, chair_T, chair_U,
    chair_V, chair_W, chair_X, chair_Y, chair_Z,
]
for lounge_index, (sofa_ref, table_ref, lounge_x) in enumerate(north_lounge):
    place_floor(table_ref, lounge_x, 8.25)
    place_floor(
        sofa_ref, lounge_x, 9.45, 270, facing=table_ref[0]
    )
    solver.distance_constraint(sofa_ref[0], table_ref[0], 1.20, 1.30)

    for seat_offset, dx, yaw in [(0, -0.80, 0), (1, 0.80, 180)]:
        seat_ref = north_seats[2 * lounge_index + seat_offset]
        place_floor(
            seat_ref, lounge_x + dx, 8.25, yaw, facing=table_ref[0]
        )
        solver.distance_constraint(seat_ref[0], table_ref[0], 0.80, 0.90)


# Second lounge row. The planting strip behind these sofas avoids both
# columns at y=7.50, and the tables remain clear of the east vestibule.
middle_lounge = [
    (multi_person_sofa_F, side_table_F, chair_group_2_A, 3.20),
    (multi_person_sofa_G, side_table_G, chair_group_2_B, 6.00),
    (multi_person_sofa_H, side_table_H, chair_group_2_C, 9.00),
    (multi_person_sofa_I, side_table_I, chair_group_2_D, 12.80),
]
for sofa_ref, table_ref, seat_ref, lounge_x in middle_lounge:
    place_floor(table_ref, lounge_x, 5.60)
    place_floor(
        sofa_ref, lounge_x, 6.70, 270, facing=table_ref[0]
    )
    solver.distance_constraint(sofa_ref[0], table_ref[0], 1.10, 1.20)
    place_floor(
        seat_ref, lounge_x, 4.75, 90, facing=table_ref[0]
    )
    solver.distance_constraint(seat_ref[0], table_ref[0], 0.85, 0.95)

# Two additional small seating spots, outside the main entrance approaches.
place_floor(side_table_J, 3.10, 4.20)
place_floor(
    chair_group_2_E, 2.30, 4.20, 0, facing=side_table_J[0]
)
solver.distance_constraint(chair_group_2_E[0], side_table_J[0], 0.80, 0.90)

place_floor(side_table_K, 10.55, 5.35)
place_floor(stool, 10.55, 4.55, 90, facing=side_table_K[0])
solver.distance_constraint(stool[0], side_table_K[0], 0.80, 0.90)


# Floor planting: a spaced strip between lounge rows, a southern strip,
# and low planting north of the dining chairs. No plant occupies a column.
floor_plant_layout = [
    (plant_A, 2.00, 7.50),
    (plant_C, 2.85, 7.50),
    (plant_D, 3.70, 7.50),
    (plant_E, 4.55, 7.50),
    (plant_F, 5.40, 7.50),
    (plant_G, 6.25, 7.50),
    (plant_H, 8.00, 7.50),
    (plant_I, 8.85, 7.50),
    (plant_K, 9.70, 7.50),
    (plant_L, 10.55, 7.50),
    (plant_N, 12.10, 7.50),
    (plant_O, 12.95, 7.50),
    (plant_P, 13.80, 7.50),

    (plant_Q, 4.60, 3.80),
    (plant_S, 5.40, 3.80),
    (plant_T, 6.20, 3.80),
    (plant_U, 8.00, 3.80),
    (plant_V, 8.80, 3.80),
    (plant_W, 9.60, 3.80),
    (plant_Y, 10.30, 3.80),

    (plant_Z, 4.20, 0.35),
    (plant_group_2_A, 6.70, 0.35),
    (plant_group_2_B, 9.10, 0.35),
    (plant_group_2_E, 11.50, 0.35),
    (plant_group_2_F, 13.75, 0.35),
    (plant_group_2_H, 1.70, 6.50),
]
for plant_ref, plant_x, plant_y in floor_plant_layout:
    place_floor(plant_ref, plant_x, plant_y)


# Small plants belong on surfaces, not on the circulation floor.
for plant_ref, support_ref in [
    (plant_B, side_table_A),
    (plant_J, side_table_B),
    (plant_M, side_table_C),
    (plant_R, side_table_D),
    (plant_X, side_table_E),
    (plant_group_2_C, side_table_F),
    (plant_group_2_D, side_table_G),
    (plant_group_2_G, side_table_H),
    (plant_group_2_I, side_table_I),
    (plant_group_2_J, side_table_J),
]:
    place_surface(plant_ref, support_ref)

for pot_ref, support_ref, dx, dy in [
    (flowerpot_A, table_B, 0.00, 0.00),
    (flowerpot_B, table_C, 0.00, 0.00),
    (flowerpot_C, table_D, 0.00, 0.00),
    (flowerpot_D, shelf, 0.00, 0.00),
    (flowerpot_E, side_table_K, 0.00, 0.00),
]:
    place_surface(pot_ref, support_ref)


# Decorative stones stay on the floor in isolated pockets, not in doorways
# or immediately beside a chair's occupied footprint.
for stone_ref, stone_x, stone_y in [
    (landscape_stone_A, 2.10, 5.55),
    (landscape_stone_B, 6.90, 5.50),
    (landscape_stone_C, 10.10, 5.60),
    (landscape_stone_D, 12.00, 0.90),
]:
    place_floor(stone_ref, stone_x, stone_y)


# Lamps fit in the gaps between northern sofas.
for lamp_ref, lamp_x in [
    (floor_lamp_A, 4.875),
    (floor_lamp_B, 7.225),
    (floor_lamp_C, 9.575),
]:
    place_floor(lamp_ref, lamp_x, 9.65, 270)

# A freestanding sign sits beyond the west door's clear approach.
place_floor(billboard, 2.90, 8.85, 270)

# The wall lamp is wall-mounted, not floor-standing or tabletop-supported.
wall_lamp[0].position = [11.90, 10.035, 1.90]
wall_lamp[0].rotation = [0, 0, radians(270)]
solver.distance_constraint(
    wall_lamp[0],
    AssetInstance(position=[11.90, 10.035, 1.90]),
    0, 0, weight=10,
)
solver.against_wall(wall_lamp[0], walls[6])
solver.align_with(
    wall_lamp[0], AssetInstance(rotation=[0, 0, radians(270)])
)


# Fruit display on the water bar: all 32 pieces occupy separate positions
# in a four-column grid, fully within the counter's 0.75 x 3.00 m top.
fruit_display = [
    fruit_A, fruit_B, fruit_C, fruit_D, fruit_E, fruit_F,
    fruit_G, fruit_H, fruit_I, fruit_J, fruit_K, fruit_L,
    fruit_M, fruit_N, fruit_O, fruit_P, fruit_Q, fruit_R,
    fruit_S, fruit_T, fruit_U, fruit_V, fruit_W, fruit_X,
    fruit_Y, fruit_Z,
    fruit_group_2_A, fruit_group_2_B, fruit_group_2_C,
    fruit_group_2_D, fruit_group_2_E, fruit_group_2_F,
]
for fruit_index, fruit_ref in enumerate(fruit_display):
    display_dx = -0.27 + 0.18 * (fruit_index % 4)
    display_dy = -1.20 + 0.32 * (fruit_index // 4)
    place_surface(fruit_ref, water_bar, display_dx, display_dy)


# Dining accessories are separated from one another and from center plants.
place_surface(dining_plate, table_A, 0.00, 0.00)
place_surface(cup_A, table_A, -0.20, 0.34)
place_surface(wine, table_A, 0.20, 0.34)
place_surface(cup_B, table_B, 0.20, 0.38)
place_surface(cup_C, table_C, 0.20, 0.38)
place_surface(jar, table_D, 0.00, 0.40)

solver.constraints = []
jar[0].position = [12.699999809265137, 2.200000047683716, 0.875]
jar[0].rotation = [0, 0, 0.01256637125682779]
jar[0].optimize = 2
chair_C[0].position = [5.5, 0.800000011920929, 0.4099999964237213]
chair_C[0].rotation = [0, 0, 1.5833626980517244]
chair_C[0].optimize = 2
chair_P[0].position = [12.699999809265137, 2.799999952316284, 0.4099999964237213]
chair_P[0].rotation = [0, 0, -1.5582299555380688]
chair_P[0].optimize = 2
plant_V[0].position = [8.800000190734863, 3.799999952316284, 0.44999998807907104]
plant_V[0].rotation = [0, 0, 0.00942477746072377]
plant_V[0].optimize = 2
high_chair_C[0].position = [4.099999904632568, 2.0, 0.5249999761581421]
high_chair_C[0].rotation = [0, 0, -3.1290262823329655]
high_chair_C[0].optimize = 2
fruit_M[0].position = [2.7300000190734863, 1.7599999904632568, 1.09499990940094]
fruit_M[0].rotation = [0, 0, 0.01256637125682779]
fruit_M[0].optimize = 2
table_B[0].position = [7.900000095367432, 1.7999999523162842, 0.375]
table_B[0].rotation = [0, 0, 0.04084070568744688]
table_B[0].optimize = 2
plant_T[0].position = [6.199999809265137, 3.799999952316284, 0.44999998807907104]
plant_T[0].rotation = [0, 0, 0.00942477746072377]
plant_T[0].optimize = 2
table_C[0].position = [10.300000190734863, 1.7999999523162842, 0.375]
table_C[0].rotation = [0, 0, 0.04084070568744688]
table_C[0].optimize = 2
plant_I[0].position = [8.850000381469727, 7.5, 0.42500001192092896]
plant_I[0].rotation = [0, 0, 0.00942477746072377]
plant_I[0].optimize = 2
multi_person_sofa_B[0].position = [6.050000190734863, 9.460000038146973, 0.42500001192092896]
multi_person_sofa_B[0].rotation = [0, 0, -1.5582299555380688]
multi_person_sofa_B[0].optimize = 2
side_table_D[0].position = [10.75, 8.25, 0.2750000059604645]
side_table_D[0].rotation = [0, 0, 0.031415925765816845]
side_table_D[0].optimize = 2
multi_person_sofa_A[0].position = [3.700000047683716, 9.460000038146973, 0.42500001192092896]
multi_person_sofa_A[0].rotation = [0, 0, -1.5582299555380688]
multi_person_sofa_A[0].optimize = 2
fruit_E[0].position = [2.7300000190734863, 1.1200000047683716, 1.0899999141693115]
fruit_E[0].rotation = [0, 0, 0.01256637125682779]
fruit_E[0].optimize = 2
plant_group_2_B[0].position = [9.100000381469727, 0.3499999940395355, 0.7250000238418579]
plant_group_2_B[0].rotation = [0, 0, 0.00942477746072377]
plant_group_2_B[0].optimize = 2
chair_L[0].position = [10.300000190734863, 2.799999952316284, 0.4099999964237213]
chair_L[0].rotation = [0, 0, -1.5582299555380688]
chair_L[0].optimize = 2
fruit_F[0].position = [2.9100000858306885, 1.1200000047683716, 1.0999999046325684]
fruit_F[0].rotation = [0, 0, 0.01256637125682779]
fruit_F[0].optimize = 2
multi_person_sofa_C[0].position = [8.399999618530273, 9.460000038146973, 0.42500001192092896]
multi_person_sofa_C[0].rotation = [0, 0, -1.5582299555380688]
multi_person_sofa_C[0].optimize = 2
plant_O[0].position = [12.949999809265137, 7.5, 0.675000011920929]
plant_O[0].rotation = [0, 0, 0.00942477746072377]
plant_O[0].optimize = 2
fruit_B[0].position = [2.9100000858306885, 0.800000011920929, 1.0899999141693115]
fruit_B[0].rotation = [0, 0, 0.01256637125682779]
fruit_B[0].optimize = 2
floor_lamp_C[0].position = [9.574999809265137, 9.649999618530273, 0.824999988079071]
floor_lamp_C[0].rotation = [0, 0, -1.5613715493341729]
floor_lamp_C[0].optimize = 2
cup_C[0].position = [10.5, 2.180000066757202, 0.800000011920929]
cup_C[0].rotation = [0, 0, 0.01256637125682779]
cup_C[0].optimize = 2
chair_group_2_D[0].position = [12.800000190734863, 4.739999771118164, 0.4099999964237213]
chair_group_2_D[0].rotation = [0, 0, 1.5833626980517244]
chair_group_2_D[0].optimize = 2
flowerpot_D[0].position = [1.4700000286102295, 4.699999809265137, 1.9800000190734863]
flowerpot_D[0].rotation = [0, 0, 0.01256637125682779]
flowerpot_D[0].optimize = 2
floor_lamp_A[0].position = [4.875, 9.649999618530273, 0.824999988079071]
floor_lamp_A[0].rotation = [0, 0, -1.5613715493341729]
floor_lamp_A[0].optimize = 2
plant_B[0].position = [3.700000047683716, 8.25, 0.75]
plant_B[0].rotation = [0, 0, 0.01256637125682779]
plant_B[0].optimize = 2
chair_N[0].position = [13.520000457763672, 1.7999999523162842, 0.4099999964237213]
chair_N[0].rotation = [0, 0, -3.1290262823329655]
chair_N[0].optimize = 2
plant_S[0].position = [5.400000095367432, 3.799999952316284, 0.699999988079071]
plant_S[0].rotation = [0, 0, 0.00942477746072377]
plant_S[0].optimize = 2
side_table_B[0].position = [6.050000190734863, 8.25, 0.2750000059604645]
side_table_B[0].rotation = [0, 0, 0.031415925765816845]
side_table_B[0].optimize = 2
chair_G[0].position = [7.900000095367432, 0.800000011920929, 0.4099999964237213]
chair_G[0].rotation = [0, 0, 1.5833626980517244]
chair_G[0].optimize = 2
plant_M[0].position = [8.399999618530273, 8.25, 0.7250000238418579]
plant_M[0].rotation = [0, 0, 0.01256637125682779]
plant_M[0].optimize = 2
wall_lamp[0].position = [11.899999618530273, 10.044999122619629, 0.17499999701976776]
wall_lamp[0].rotation = [0, 0, -1.5682554052778654]
wall_lamp[0].optimize = 2
fruit_U[0].position = [2.7300000190734863, 2.4000000953674316, 1.09499990940094]
fruit_U[0].rotation = [0, 0, 0.01256637125682779]
fruit_U[0].optimize = 2
chair_O[0].position = [12.699999809265137, 0.800000011920929, 0.4099999964237213]
chair_O[0].rotation = [0, 0, 1.5833626980517244]
chair_O[0].optimize = 2
stool[0].position = [10.550000190734863, 4.539999961853027, 0.23000000417232513]
stool[0].rotation = [0, 0, 1.5833626980517244]
stool[0].optimize = 2
plant_group_2_E[0].position = [11.5, 0.3499999940395355, 0.550000011920929]
plant_group_2_E[0].rotation = [0, 0, 0.00942477746072377]
plant_group_2_E[0].optimize = 2
plant_H[0].position = [8.0, 7.5, 0.699999988079071]
plant_H[0].rotation = [0, 0, 0.00942477746072377]
plant_H[0].optimize = 2
fruit_group_2_F[0].position = [3.2469656467437744, 3.0370900630950928, 1.09499990940094]
fruit_group_2_F[0].rotation = [0, 0, 0.01256637125682779]
fruit_group_2_F[0].optimize = 2
plant_group_2_F[0].position = [13.75, 0.3499999940395355, 0.699999988079071]
plant_group_2_F[0].rotation = [0, 0, 0.00942477746072377]
plant_group_2_F[0].optimize = 2
plant_A[0].position = [2.0, 7.5, 0.75]
plant_A[0].rotation = [0, 0, 0.00942477746072377]
plant_A[0].optimize = 2
fruit_A[0].position = [2.7729296684265137, 0.8054232597351074, 1.09499990940094]
fruit_A[0].rotation = [0, 0, 0.01256637125682779]
fruit_A[0].optimize = 2
multi_person_sofa_D[0].position = [10.75, 9.460000038146973, 0.42500001192092896]
multi_person_sofa_D[0].rotation = [0, 0, -1.5582299555380688]
multi_person_sofa_D[0].optimize = 2
plant_C[0].position = [2.8499999046325684, 7.5, 0.6000000238418579]
plant_C[0].rotation = [0, 0, 0.00942477746072377]
plant_C[0].optimize = 2
multi_person_sofa_G[0].position = [6.0, 6.710000038146973, 0.42500001192092896]
multi_person_sofa_G[0].rotation = [0, 0, -1.5582299555380688]
multi_person_sofa_G[0].optimize = 2
chair_E[0].position = [7.079999923706055, 1.7999999523162842, 0.4099999964237213]
chair_E[0].rotation = [0, 0, 0.01256637125682779]
chair_E[0].optimize = 2
plant_group_2_J[0].position = [3.0999999046325684, 4.199999809265137, 0.75]
plant_group_2_J[0].rotation = [0, 0, 0.01256637125682779]
plant_group_2_J[0].optimize = 2
chair_T[0].position = [6.860000133514404, 8.25, 0.4099999964237213]
chair_T[0].rotation = [0, 0, -3.1290262823329655]
chair_T[0].optimize = 2
chair_group_2_B[0].position = [6.0, 4.739999771118164, 0.4099999964237213]
chair_group_2_B[0].rotation = [0, 0, 1.5833626980517244]
chair_group_2_B[0].optimize = 2
chair_M[0].position = [11.880000114440918, 1.7999999523162842, 0.4099999964237213]
chair_M[0].rotation = [0, 0, 0.01256637125682779]
chair_M[0].optimize = 2
flowerpot_E[0].position = [10.550000190734863, 5.349999904632568, 0.7300000190734863]
flowerpot_E[0].rotation = [0, 0, 0.01256637125682779]
flowerpot_E[0].optimize = 2
fruit_D[0].position = [3.2699999809265137, 0.800000011920929, 1.09499990940094]
fruit_D[0].rotation = [0, 0, 0.01256637125682779]
fruit_D[0].optimize = 2
high_chair_D[0].position = [4.099999904632568, 2.5999999046325684, 0.5249999761581421]
high_chair_D[0].rotation = [0, 0, -3.1290262823329655]
high_chair_D[0].optimize = 2
plant_D[0].position = [3.700000047683716, 7.5, 0.44999998807907104]
plant_D[0].rotation = [0, 0, 0.00942477746072377]
plant_D[0].optimize = 2
side_table_E[0].position = [13.100000381469727, 8.25, 0.2750000059604645]
side_table_E[0].rotation = [0, 0, 0.031415925765816845]
side_table_E[0].optimize = 2
chair_F[0].position = [8.720000267028809, 1.7999999523162842, 0.4099999964237213]
chair_F[0].rotation = [0, 0, -3.1290262823329655]
chair_F[0].optimize = 2
fruit_Q[0].position = [2.7300000190734863, 2.0799999237060547, 1.0899999141693115]
fruit_Q[0].rotation = [0, 0, 0.01256637125682779]
fruit_Q[0].optimize = 2
chair_Y[0].position = [12.300000190734863, 8.25, 0.4099999964237213]
chair_Y[0].rotation = [0, 0, 0.01256637125682779]
chair_Y[0].optimize = 2
cup_A[0].position = [5.300000190734863, 2.140000104904175, 0.800000011920929]
cup_A[0].rotation = [0, 0, 0.01256637125682779]
cup_A[0].optimize = 2
plant_L[0].position = [10.550000190734863, 7.5, 0.4749999940395355]
plant_L[0].rotation = [0, 0, 0.00942477746072377]
plant_L[0].optimize = 2
side_table_J[0].position = [3.0999999046325684, 4.199999809265137, 0.2750000059604645]
side_table_J[0].rotation = [0, 0, 0.01884955539881635]
side_table_J[0].optimize = 2
fruit_L[0].position = [3.2699999809265137, 1.440000057220459, 1.09499990940094]
fruit_L[0].rotation = [0, 0, 0.01256637125682779]
fruit_L[0].optimize = 2
high_chair_E[0].position = [4.099999904632568, 3.200000047683716, 0.5249999761581421]
high_chair_E[0].rotation = [0, 0, -3.1290262823329655]
high_chair_E[0].optimize = 2
fruit_H[0].position = [3.2699999809265137, 1.1200000047683716, 1.0899999141693115]
fruit_H[0].rotation = [0, 0, 0.01256637125682779]
fruit_H[0].optimize = 2
fruit_T[0].position = [3.2699999809265137, 2.0799999237060547, 1.0899999141693115]
fruit_T[0].rotation = [0, 0, 0.01256637125682779]
fruit_T[0].optimize = 2
billboard[0].position = [2.9000000953674316, 8.850000381469727, 0.44999998807907104]
billboard[0].rotation = [0, 0, -1.5613715493341729]
billboard[0].optimize = 2
multi_person_sofa_F[0].position = [3.200000047683716, 6.710000038146973, 0.42500001192092896]
multi_person_sofa_F[0].rotation = [0, 0, -1.5582299555380688]
multi_person_sofa_F[0].optimize = 2
multi_person_sofa_E[0].position = [13.100000381469727, 9.460000038146973, 0.42500001192092896]
multi_person_sofa_E[0].rotation = [0, 0, -1.5582299555380688]
multi_person_sofa_E[0].optimize = 2
high_chair_A[0].position = [4.099999904632568, 0.800000011920929, 0.5249999761581421]
high_chair_A[0].rotation = [0, 0, -3.1290262823329655]
high_chair_A[0].optimize = 2
high_chair_B[0].position = [4.099999904632568, 1.399999976158142, 0.5249999761581421]
high_chair_B[0].rotation = [0, 0, -3.1290262823329655]
high_chair_B[0].optimize = 2
fruit_G[0].position = [3.0899999141693115, 1.1200000047683716, 1.09499990940094]
fruit_G[0].rotation = [0, 0, 0.01256637125682779]
fruit_G[0].optimize = 2
fruit_X[0].position = [3.2699999809265137, 2.4000000953674316, 1.09499990940094]
fruit_X[0].rotation = [0, 0, 0.01256637125682779]
fruit_X[0].optimize = 2
landscape_stone_D[0].position = [12.0, 0.8999999761581421, 0.15000000596046448]
landscape_stone_D[0].rotation = [0, 0, 0.00942477746072377]
landscape_stone_D[0].optimize = 2
fruit_group_2_C[0].position = [2.7300000190734863, 3.0399999618530273, 1.09499990940094]
fruit_group_2_C[0].rotation = [0, 0, 0.01256637125682779]
fruit_group_2_C[0].optimize = 2
fruit_W[0].position = [3.0899999141693115, 2.4000000953674316, 1.0899999141693115]
fruit_W[0].rotation = [0, 0, 0.01256637125682779]
fruit_W[0].optimize = 2
flowerpot_C[0].position = [12.699999809265137, 1.7999999523162842, 0.9300000071525574]
flowerpot_C[0].rotation = [0, 0, 0.01256637125682779]
flowerpot_C[0].optimize = 2
plant_P[0].position = [13.800000190734863, 7.5, 0.4000000059604645]
plant_P[0].rotation = [0, 0, 0.00942477746072377]
plant_P[0].optimize = 2
landscape_stone_A[0].position = [2.0999999046325684, 5.550000190734863, 0.17499999701976776]
landscape_stone_A[0].rotation = [0, 0, 0.00942477746072377]
landscape_stone_A[0].optimize = 2
plant_group_2_G[0].position = [9.0, 5.599999904632568, 0.7749999761581421]
plant_group_2_G[0].rotation = [0, 0, 0.01256637125682779]
plant_group_2_G[0].optimize = 2
chair_S[0].position = [5.25, 8.25, 0.4099999964237213]
chair_S[0].rotation = [0, 0, 0.01256637125682779]
chair_S[0].optimize = 2
plant_group_2_A[0].position = [6.699999809265137, 0.3499999940395355, 0.5]
plant_group_2_A[0].rotation = [0, 0, 0.00942477746072377]
plant_group_2_A[0].optimize = 2
shelf[0].position = [1.4600001573562622, 4.699999809265137, 0.8999999761581421]
shelf[0].rotation = [0, 0, 0.005651515482244516]
shelf[0].optimize = 2
plant_group_2_D[0].position = [6.0, 5.599999904632568, 0.7250000238418579]
plant_group_2_D[0].rotation = [0, 0, 0.01256637125682779]
plant_group_2_D[0].optimize = 2
water_bar[0].position = [3.0, 2.0, 0.5249999761581421]
water_bar[0].rotation = [0, 0, 0.12566370455444695]
water_bar[0].optimize = 2
plant_group_2_I[0].position = [12.800000190734863, 5.599999904632568, 0.75]
plant_group_2_I[0].rotation = [0, 0, 0.01256637125682779]
plant_group_2_I[0].optimize = 2
dining_plate[0].position = [5.5, 1.7999999523162842, 0.7649999856948853]
dining_plate[0].rotation = [0, 0, 0.01256637125682779]
dining_plate[0].optimize = 2
plant_X[0].position = [13.100000381469727, 8.25, 0.7250000238418579]
plant_X[0].rotation = [0, 0, 0.01256637125682779]
plant_X[0].optimize = 2
plant_group_2_H[0].position = [1.7000000476837158, 6.5, 0.44999998807907104]
plant_group_2_H[0].rotation = [0, 0, 0.00942477746072377]
plant_group_2_H[0].optimize = 2
side_table_G[0].position = [6.0, 5.599999904632568, 0.2750000059604645]
side_table_G[0].rotation = [0, 0, 0.025132740109855806]
side_table_G[0].optimize = 2
plant_F[0].position = [5.400000095367432, 7.5, 0.550000011920929]
plant_F[0].rotation = [0, 0, 0.00942477746072377]
plant_F[0].optimize = 2
chair_J[0].position = [11.119999885559082, 1.7999999523162842, 0.4099999964237213]
chair_J[0].rotation = [0, 0, -3.1290262823329655]
chair_J[0].optimize = 2
fruit_J[0].position = [2.9100000858306885, 1.440000057220459, 1.0999999046325684]
fruit_J[0].rotation = [0, 0, 0.01256637125682779]
fruit_J[0].optimize = 2
fruit_R[0].position = [2.9100000858306885, 2.0799999237060547, 1.09499990940094]
fruit_R[0].rotation = [0, 0, 0.01256637125682779]
fruit_R[0].optimize = 2
fruit_Y[0].position = [2.7300000190734863, 2.7200000286102295, 1.0899999141693115]
fruit_Y[0].rotation = [0, 0, 0.01256637125682779]
fruit_Y[0].optimize = 2
plant_Z[0].position = [4.199999809265137, 0.3499999940395355, 0.625]
plant_Z[0].rotation = [0, 0, 0.00942477746072377]
plant_Z[0].optimize = 2
fruit_group_2_D[0].position = [2.9100000858306885, 3.0399999618530273, 1.0999999046325684]
fruit_group_2_D[0].rotation = [0, 0, 0.01256637125682779]
fruit_group_2_D[0].optimize = 2
chair_X[0].position = [11.550000190734863, 8.25, 0.4099999964237213]
chair_X[0].rotation = [0, 0, -3.1290262823329655]
chair_X[0].optimize = 2
chair_group_2_C[0].position = [9.0, 4.739999771118164, 0.4099999964237213]
chair_group_2_C[0].rotation = [0, 0, 1.5833626980517244]
chair_group_2_C[0].optimize = 2
fruit_K[0].position = [3.0899999141693115, 1.440000057220459, 1.0899999141693115]
fruit_K[0].rotation = [0, 0, 0.01256637125682779]
fruit_K[0].optimize = 2
plant_K[0].position = [9.699999809265137, 7.5, 0.800000011920929]
plant_K[0].rotation = [0, 0, 0.00942477746072377]
plant_K[0].optimize = 2
table_D[0].position = [12.699999809265137, 1.7999999523162842, 0.375]
table_D[0].rotation = [0, 0, 0.04084070568744688]
table_D[0].optimize = 2
chair_K[0].position = [10.300000190734863, 0.800000011920929, 0.4099999964237213]
chair_K[0].rotation = [0, 0, 1.5833626980517244]
chair_K[0].optimize = 2
chair_Z[0].position = [13.90999984741211, 8.25, 0.4099999964237213]
chair_Z[0].rotation = [0, 0, -3.1290262823329655]
chair_Z[0].optimize = 2
table_A[0].position = [5.5, 1.7999999523162842, 0.375]
table_A[0].rotation = [0, 0, 0.043982298440307294]
table_A[0].optimize = 2
plant_J[0].position = [6.050000190734863, 8.25, 0.75]
plant_J[0].rotation = [0, 0, 0.01256637125682779]
plant_J[0].optimize = 2
plant_Q[0].position = [4.599999904632568, 3.799999952316284, 0.6000000238418579]
plant_Q[0].rotation = [0, 0, 0.00942477746072377]
plant_Q[0].optimize = 2
side_table_K[0].position = [10.550000190734863, 5.349999904632568, 0.2750000059604645]
side_table_K[0].rotation = [0, 0, 0.01884955539881635]
side_table_K[0].optimize = 2
plant_Y[0].position = [10.300000190734863, 3.799999952316284, 0.4749999940395355]
plant_Y[0].rotation = [0, 0, 0.00942477746072377]
plant_Y[0].optimize = 2
multi_person_sofa_H[0].position = [9.0, 6.710000038146973, 0.42500001192092896]
multi_person_sofa_H[0].rotation = [0, 0, -1.5582299555380688]
multi_person_sofa_H[0].optimize = 2
fruit_N[0].position = [2.9100000858306885, 1.7599999904632568, 1.0899999141693115]
fruit_N[0].rotation = [0, 0, 0.01256637125682779]
fruit_N[0].optimize = 2
chair_A[0].position = [4.679999828338623, 1.7999999523162842, 0.4099999964237213]
chair_A[0].rotation = [0, 0, 0.01256637125682779]
chair_A[0].optimize = 2
fruit_group_2_A[0].position = [3.0899999141693115, 2.7200000286102295, 1.09499990940094]
fruit_group_2_A[0].rotation = [0, 0, 0.01256637125682779]
fruit_group_2_A[0].optimize = 2
side_table_F[0].position = [3.200000047683716, 5.599999904632568, 0.2750000059604645]
side_table_F[0].rotation = [0, 0, 0.025132740109855806]
side_table_F[0].optimize = 2
multi_person_sofa_I[0].position = [12.800000190734863, 6.710000038146973, 0.42500001192092896]
multi_person_sofa_I[0].rotation = [0, 0, -1.5582299555380688]
multi_person_sofa_I[0].optimize = 2
landscape_stone_B[0].position = [6.900000095367432, 5.5, 0.15000000596046448]
landscape_stone_B[0].rotation = [0, 0, 0.00942477746072377]
landscape_stone_B[0].optimize = 2
fruit_O[0].position = [3.0899999141693115, 1.7599999904632568, 1.0999999046325684]
fruit_O[0].rotation = [0, 0, 0.01256637125682779]
fruit_O[0].optimize = 2
plant_G[0].position = [6.25, 7.5, 0.6499999761581421]
plant_G[0].rotation = [0, 0, 0.00942477746072377]
plant_G[0].optimize = 2
chair_I[0].position = [9.479999542236328, 1.7999999523162842, 0.4099999964237213]
chair_I[0].rotation = [0, 0, 0.01256637125682779]
chair_I[0].optimize = 2
plant_E[0].position = [4.550000190734863, 7.5, 0.699999988079071]
plant_E[0].rotation = [0, 0, 0.00942477746072377]
plant_E[0].optimize = 2
fruit_group_2_E[0].position = [3.0899999141693115, 3.0399999618530273, 1.0899999141693115]
fruit_group_2_E[0].rotation = [0, 0, 0.01256637125682779]
fruit_group_2_E[0].optimize = 2
side_table_I[0].position = [12.800000190734863, 5.599999904632568, 0.2750000059604645]
side_table_I[0].rotation = [0, 0, 0.025132740109855806]
side_table_I[0].optimize = 2
side_table_C[0].position = [8.399999618530273, 8.25, 0.2750000059604645]
side_table_C[0].rotation = [0, 0, 0.031415925765816845]
side_table_C[0].optimize = 2
chair_Q[0].position = [2.890000104904175, 8.25, 0.4099999964237213]
chair_Q[0].rotation = [0, 0, 0.01256637125682779]
chair_Q[0].optimize = 2
fruit_P[0].position = [3.2699999809265137, 1.7599999904632568, 1.09499990940094]
fruit_P[0].rotation = [0, 0, 0.01256637125682779]
fruit_P[0].optimize = 2
floor_lamp_B[0].position = [7.224999904632568, 9.649999618530273, 0.824999988079071]
floor_lamp_B[0].rotation = [0, 0, -1.5613715493341729]
floor_lamp_B[0].optimize = 2
fruit_Z[0].position = [2.9100000858306885, 2.7200000286102295, 1.0999999046325684]
fruit_Z[0].rotation = [0, 0, 0.01256637125682779]
fruit_Z[0].optimize = 2
chair_V[0].position = [9.199999809265137, 8.25, 0.4099999964237213]
chair_V[0].rotation = [0, 0, -3.1290262823329655]
chair_V[0].optimize = 2
plant_R[0].position = [10.75, 8.25, 0.7749999761581421]
plant_R[0].rotation = [0, 0, 0.01256637125682779]
plant_R[0].optimize = 2
fruit_C[0].position = [3.0899999141693115, 0.800000011920929, 1.0999999046325684]
fruit_C[0].rotation = [0, 0, 0.01256637125682779]
fruit_C[0].optimize = 2
plant_U[0].position = [8.0, 3.799999952316284, 0.625]
plant_U[0].rotation = [0, 0, 0.00942477746072377]
plant_U[0].optimize = 2
chair_B[0].position = [6.320000171661377, 1.7999999523162842, 0.4099999964237213]
chair_B[0].rotation = [0, 0, -3.1290262823329655]
chair_B[0].optimize = 2
plant_N[0].position = [12.100000381469727, 7.5, 0.574999988079071]
plant_N[0].rotation = [0, 0, 0.00942477746072377]
plant_N[0].optimize = 2
plant_group_2_C[0].position = [3.200000047683716, 5.599999904632568, 0.75]
plant_group_2_C[0].rotation = [0, 0, 0.01256637125682779]
plant_group_2_C[0].optimize = 2
flowerpot_A[0].position = [7.900000095367432, 1.7999999523162842, 0.9300000071525574]
flowerpot_A[0].rotation = [0, 0, 0.01256637125682779]
flowerpot_A[0].optimize = 2
landscape_stone_C[0].position = [10.100000381469727, 5.599999904632568, 0.20000000298023224]
landscape_stone_C[0].rotation = [0, 0, 0.00942477746072377]
landscape_stone_C[0].optimize = 2
fruit_V[0].position = [2.9100000858306885, 2.4000000953674316, 1.0999999046325684]
fruit_V[0].rotation = [0, 0, 0.01256637125682779]
fruit_V[0].optimize = 2
chair_group_2_E[0].position = [2.2899999618530273, 4.199999809265137, 0.4099999964237213]
chair_group_2_E[0].rotation = [0, 0, 0.01256637125682779]
chair_group_2_E[0].optimize = 2
fruit_I[0].position = [2.7300000190734863, 1.440000057220459, 1.09499990940094]
fruit_I[0].rotation = [0, 0, 0.01256637125682779]
fruit_I[0].optimize = 2
side_table_A[0].position = [3.700000047683716, 8.25, 0.2750000059604645]
side_table_A[0].rotation = [0, 0, 0.031415925765816845]
side_table_A[0].optimize = 2
chair_U[0].position = [7.589999675750732, 8.25, 0.4099999964237213]
chair_U[0].rotation = [0, 0, 0.01256637125682779]
chair_U[0].optimize = 2
fruit_group_2_B[0].position = [3.2699999809265137, 2.7200000286102295, 1.0899999141693115]
fruit_group_2_B[0].rotation = [0, 0, 0.01256637125682779]
fruit_group_2_B[0].optimize = 2
side_table_H[0].position = [9.0, 5.599999904632568, 0.2750000059604645]
side_table_H[0].rotation = [0, 0, 0.025132740109855806]
side_table_H[0].optimize = 2
wine[0].position = [5.699999809265137, 2.140000104904175, 0.8999999761581421]
wine[0].rotation = [0, 0, 0.01256637125682779]
wine[0].optimize = 2
chair_W[0].position = [9.949999809265137, 8.25, 0.4099999964237213]
chair_W[0].rotation = [0, 0, 0.01256637125682779]
chair_W[0].optimize = 2
fruit_S[0].position = [3.0899999141693115, 2.0799999237060547, 1.0999999046325684]
fruit_S[0].rotation = [0, 0, 0.01256637125682779]
fruit_S[0].optimize = 2
plant_W[0].position = [9.600000381469727, 3.799999952316284, 0.75]
plant_W[0].rotation = [0, 0, 0.00942477746072377]
plant_W[0].optimize = 2
chair_R[0].position = [4.510000228881836, 8.25, 0.4099999964237213]
chair_R[0].rotation = [0, 0, -3.1290262823329655]
chair_R[0].optimize = 2
chair_H[0].position = [7.900000095367432, 2.799999952316284, 0.4099999964237213]
chair_H[0].rotation = [0, 0, -1.5582299555380688]
chair_H[0].optimize = 2
cup_B[0].position = [8.100000381469727, 2.180000066757202, 0.800000011920929]
cup_B[0].rotation = [0, 0, 0.01256637125682779]
cup_B[0].optimize = 2
chair_D[0].position = [5.5, 2.799999952316284, 0.4099999964237213]
chair_D[0].rotation = [0, 0, -1.5582299555380688]
chair_D[0].optimize = 2
flowerpot_B[0].position = [10.300000190734863, 1.7999999523162842, 0.9200000166893005]
flowerpot_B[0].rotation = [0, 0, 0.01256637125682779]
flowerpot_B[0].optimize = 2
chair_group_2_A[0].position = [3.200000047683716, 4.739999771118164, 0.4099999964237213]
chair_group_2_A[0].rotation = [0, 0, 1.5833626980517244]
chair_group_2_A[0].optimize = 2

