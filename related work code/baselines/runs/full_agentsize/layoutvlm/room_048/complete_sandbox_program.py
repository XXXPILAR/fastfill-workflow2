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
plant_A = Assets(description="plant", size=[0.65, 0.65, 1.55], placements=[AssetInstance() for _ in range(1)])
fruit_A = Assets(description="fruit", size=[0.09, 0.09, 0.08], placements=[AssetInstance() for _ in range(1)])
table_A = Assets(description="table", size=[0.90, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="chair", size=[0.58, 0.52, 0.84], placements=[AssetInstance() for _ in range(1)])
side_table_A = Assets(description="side table", size=[0.55, 0.55, 0.52], placements=[AssetInstance() for _ in range(1)])
plant_B = Assets(description="plant", size=[0.45, 0.45, 1.15], placements=[AssetInstance() for _ in range(1)])
plant_C = Assets(description="plant", size=[0.70, 0.70, 1.70], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.60, 0.55, 0.86], placements=[AssetInstance() for _ in range(1)])
plant_D = Assets(description="plant", size=[0.35, 0.35, 0.75], placements=[AssetInstance() for _ in range(1)])
fruit_B = Assets(description="fruit", size=[0.10, 0.10, 0.09], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="chair", size=[0.57, 0.52, 0.83], placements=[AssetInstance() for _ in range(1)])
cup_A = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
chair_D = Assets(description="chair", size=[0.59, 0.54, 0.85], placements=[AssetInstance() for _ in range(1)])
plant_E = Assets(description="plant", size=[0.55, 0.55, 1.35], placements=[AssetInstance() for _ in range(1)])
chair_E = Assets(description="chair", size=[0.58, 0.53, 0.84], placements=[AssetInstance() for _ in range(1)])
fruit_C = Assets(description="fruit", size=[0.08, 0.08, 0.07], placements=[AssetInstance() for _ in range(1)])
plant_F = Assets(description="plant", size=[0.80, 0.80, 1.90], placements=[AssetInstance() for _ in range(1)])
multi_person_sofa_A = Assets(description="multi person sofa", size=[0.92, 2.15, 0.82], placements=[AssetInstance() for _ in range(1)])
fruit_D = Assets(description="fruit", size=[0.11, 0.11, 0.10], placements=[AssetInstance() for _ in range(1)])
multi_person_sofa_B = Assets(description="multi person sofa", size=[0.95, 2.40, 0.84], placements=[AssetInstance() for _ in range(1)])
fruit_E = Assets(description="fruit", size=[0.09, 0.09, 0.08], placements=[AssetInstance() for _ in range(1)])
plant_G = Assets(description="plant", size=[0.50, 0.50, 1.25], placements=[AssetInstance() for _ in range(1)])
cup_B = Assets(description="cup", size=[0.09, 0.09, 0.12], placements=[AssetInstance() for _ in range(1)])
fruit_F = Assets(description="fruit", size=[0.10, 0.12, 0.09], placements=[AssetInstance() for _ in range(1)])
high_chair_A = Assets(description="high chair", size=[0.55, 0.50, 1.02], placements=[AssetInstance() for _ in range(1)])
landscape_stone_A = Assets(description="landscape stone", size=[0.65, 0.85, 0.42], placements=[AssetInstance() for _ in range(1)])
plant_H = Assets(description="plant", size=[0.38, 0.38, 0.85], placements=[AssetInstance() for _ in range(1)])
side_table_B = Assets(description="side table", size=[0.60, 0.60, 0.50], placements=[AssetInstance() for _ in range(1)])
fruit_G = Assets(description="fruit", size=[0.08, 0.08, 0.07], placements=[AssetInstance() for _ in range(1)])
multi_person_sofa_C = Assets(description="multi person sofa", size=[0.90, 2.25, 0.80], placements=[AssetInstance() for _ in range(1)])
chair_F = Assets(description="chair", size=[0.60, 0.55, 0.86], placements=[AssetInstance() for _ in range(1)])
plant_I = Assets(description="plant", size=[0.65, 0.65, 1.60], placements=[AssetInstance() for _ in range(1)])
flowerpot_A = Assets(description="flowerpot", size=[0.38, 0.38, 0.35], placements=[AssetInstance() for _ in range(1)])
chair_G = Assets(description="chair", size=[0.58, 0.52, 0.83], placements=[AssetInstance() for _ in range(1)])
plant_J = Assets(description="plant", size=[0.40, 0.40, 0.95], placements=[AssetInstance() for _ in range(1)])
side_table_C = Assets(description="side table", size=[0.50, 0.50, 0.48], placements=[AssetInstance() for _ in range(1)])
fruit_H = Assets(description="fruit", size=[0.10, 0.10, 0.09], placements=[AssetInstance() for _ in range(1)])
chair_H = Assets(description="chair", size=[0.58, 0.54, 0.85], placements=[AssetInstance() for _ in range(1)])
chair_I = Assets(description="chair", size=[0.60, 0.55, 0.87], placements=[AssetInstance() for _ in range(1)])
chair_J = Assets(description="chair", size=[0.57, 0.52, 0.84], placements=[AssetInstance() for _ in range(1)])
chair_K = Assets(description="chair", size=[0.59, 0.53, 0.85], placements=[AssetInstance() for _ in range(1)])
floor_lamp_A = Assets(description="floor lamp", size=[0.42, 0.42, 1.65], placements=[AssetInstance() for _ in range(1)])
plant_K = Assets(description="plant", size=[0.55, 0.55, 1.40], placements=[AssetInstance() for _ in range(1)])
plant_L = Assets(description="plant", size=[0.30, 0.30, 0.65], placements=[AssetInstance() for _ in range(1)])
chair_L = Assets(description="chair", size=[0.61, 0.56, 0.86], placements=[AssetInstance() for _ in range(1)])
plant_M = Assets(description="plant", size=[0.70, 0.70, 1.75], placements=[AssetInstance() for _ in range(1)])
plant_N = Assets(description="plant", size=[0.45, 0.45, 1.10], placements=[AssetInstance() for _ in range(1)])
fruit_I = Assets(description="fruit", size=[0.09, 0.09, 0.08], placements=[AssetInstance() for _ in range(1)])
plant_O = Assets(description="plant", size=[0.60, 0.60, 1.50], placements=[AssetInstance() for _ in range(1)])
side_table_D = Assets(description="side table", size=[0.58, 0.58, 0.50], placements=[AssetInstance() for _ in range(1)])
chair_M = Assets(description="chair", size=[0.59, 0.54, 0.84], placements=[AssetInstance() for _ in range(1)])
flowerpot_B = Assets(description="flowerpot", size=[0.40, 0.40, 0.38], placements=[AssetInstance() for _ in range(1)])
fruit_J = Assets(description="fruit", size=[0.10, 0.11, 0.09], placements=[AssetInstance() for _ in range(1)])
plant_P = Assets(description="plant", size=[0.75, 0.75, 1.80], placements=[AssetInstance() for _ in range(1)])
plant_Q = Assets(description="plant", size=[0.35, 0.35, 0.80], placements=[AssetInstance() for _ in range(1)])
fruit_K = Assets(description="fruit", size=[0.08, 0.08, 0.07], placements=[AssetInstance() for _ in range(1)])
chair_N = Assets(description="chair", size=[0.58, 0.52, 0.83], placements=[AssetInstance() for _ in range(1)])
plant_R = Assets(description="plant", size=[0.50, 0.50, 1.20], placements=[AssetInstance() for _ in range(1)])
side_table_E = Assets(description="side table", size=[0.55, 0.55, 0.50], placements=[AssetInstance() for _ in range(1)])
plant_S = Assets(description="plant", size=[0.65, 0.65, 1.55], placements=[AssetInstance() for _ in range(1)])
fruit_L = Assets(description="fruit", size=[0.10, 0.10, 0.09], placements=[AssetInstance() for _ in range(1)])
high_chair_B = Assets(description="high chair", size=[0.54, 0.48, 1.00], placements=[AssetInstance() for _ in range(1)])
side_table_F = Assets(description="side table", size=[0.62, 0.62, 0.52], placements=[AssetInstance() for _ in range(1)])
chair_O = Assets(description="chair", size=[0.60, 0.55, 0.85], placements=[AssetInstance() for _ in range(1)])
table_B = Assets(description="table", size=[0.90, 1.80, 0.75], placements=[AssetInstance() for _ in range(1)])
chair_P = Assets(description="chair", size=[0.58, 0.53, 0.84], placements=[AssetInstance() for _ in range(1)])
flowerpot_C = Assets(description="flowerpot", size=[0.36, 0.36, 0.34], placements=[AssetInstance() for _ in range(1)])
chair_Q = Assets(description="chair", size=[0.59, 0.54, 0.86], placements=[AssetInstance() for _ in range(1)])
plant_T = Assets(description="plant", size=[0.55, 0.55, 1.30], placements=[AssetInstance() for _ in range(1)])
dining_plate = Assets(description="dining plate", size=[0.27, 0.27, 0.03], placements=[AssetInstance() for _ in range(1)])
chair_R = Assets(description="chair", size=[0.57, 0.52, 0.83], placements=[AssetInstance() for _ in range(1)])
high_chair_C = Assets(description="high chair", size=[0.56, 0.50, 1.03], placements=[AssetInstance() for _ in range(1)])
fruit_M = Assets(description="fruit", size=[0.09, 0.09, 0.08], placements=[AssetInstance() for _ in range(1)])
fruit_N = Assets(description="fruit", size=[0.10, 0.11, 0.09], placements=[AssetInstance() for _ in range(1)])
multi_person_sofa_D = Assets(description="multi person sofa", size=[0.94, 2.30, 0.83], placements=[AssetInstance() for _ in range(1)])
plant_U = Assets(description="plant", size=[0.40, 0.40, 0.90], placements=[AssetInstance() for _ in range(1)])
plant_V = Assets(description="plant", size=[0.70, 0.70, 1.65], placements=[AssetInstance() for _ in range(1)])
fruit_O = Assets(description="fruit", size=[0.08, 0.08, 0.07], placements=[AssetInstance() for _ in range(1)])
multi_person_sofa_E = Assets(description="multi person sofa", size=[0.92, 2.20, 0.81], placements=[AssetInstance() for _ in range(1)])
plant_W = Assets(description="plant", size=[0.50, 0.50, 1.20], placements=[AssetInstance() for _ in range(1)])
fruit_P = Assets(description="fruit", size=[0.10, 0.10, 0.09], placements=[AssetInstance() for _ in range(1)])
multi_person_sofa_F = Assets(description="multi person sofa", size=[0.98, 2.45, 0.85], placements=[AssetInstance() for _ in range(1)])
fruit_Q = Assets(description="fruit", size=[0.09, 0.09, 0.08], placements=[AssetInstance() for _ in range(1)])
plant_X = Assets(description="plant", size=[0.60, 0.60, 1.45], placements=[AssetInstance() for _ in range(1)])
chair_S = Assets(description="chair", size=[0.59, 0.55, 0.85], placements=[AssetInstance() for _ in range(1)])
table_C = Assets(description="table", size=[0.85, 1.50, 0.74], placements=[AssetInstance() for _ in range(1)])
stool = Assets(description="stool", size=[0.42, 0.42, 0.46], placements=[AssetInstance() for _ in range(1)])
fruit_R = Assets(description="fruit", size=[0.10, 0.12, 0.09], placements=[AssetInstance() for _ in range(1)])
fruit_S = Assets(description="fruit", size=[0.08, 0.08, 0.07], placements=[AssetInstance() for _ in range(1)])
flowerpot_D = Assets(description="flowerpot", size=[0.42, 0.42, 0.40], placements=[AssetInstance() for _ in range(1)])
chair_T = Assets(description="chair", size=[0.58, 0.53, 0.84], placements=[AssetInstance() for _ in range(1)])
chair_U = Assets(description="chair", size=[0.60, 0.54, 0.86], placements=[AssetInstance() for _ in range(1)])
fruit_T = Assets(description="fruit", size=[0.10, 0.10, 0.09], placements=[AssetInstance() for _ in range(1)])
chair_V = Assets(description="chair", size=[0.57, 0.52, 0.83], placements=[AssetInstance() for _ in range(1)])
wall_lamp = Assets(description="wall lamp", size=[0.18, 0.28, 0.42], placements=[AssetInstance() for _ in range(1)])
wine = Assets(description="wine", size=[0.08, 0.08, 0.30], placements=[AssetInstance() for _ in range(1)])
fruit_U = Assets(description="fruit", size=[0.09, 0.09, 0.08], placements=[AssetInstance() for _ in range(1)])
plant_Y = Assets(description="plant", size=[0.35, 0.35, 0.80], placements=[AssetInstance() for _ in range(1)])
plant_Z = Assets(description="plant", size=[0.55, 0.55, 1.35], placements=[AssetInstance() for _ in range(1)])
plant_group_2_A = Assets(description="plant", size=[0.75, 0.75, 1.85], placements=[AssetInstance() for _ in range(1)])
fruit_V = Assets(description="fruit", size=[0.10, 0.11, 0.09], placements=[AssetInstance() for _ in range(1)])
floor_lamp_B = Assets(description="floor lamp", size=[0.40, 0.40, 1.70], placements=[AssetInstance() for _ in range(1)])
landscape_stone_B = Assets(description="landscape stone", size=[0.55, 0.70, 0.35], placements=[AssetInstance() for _ in range(1)])
plant_group_2_B = Assets(description="plant", size=[0.45, 0.45, 1.05], placements=[AssetInstance() for _ in range(1)])
fruit_W = Assets(description="fruit", size=[0.08, 0.08, 0.07], placements=[AssetInstance() for _ in range(1)])
fruit_X = Assets(description="fruit", size=[0.10, 0.10, 0.09], placements=[AssetInstance() for _ in range(1)])
chair_W = Assets(description="chair", size=[0.60, 0.55, 0.86], placements=[AssetInstance() for _ in range(1)])
plant_group_2_C = Assets(description="plant", size=[0.65, 0.65, 1.55], placements=[AssetInstance() for _ in range(1)])
multi_person_sofa_G = Assets(description="multi person sofa", size=[0.95, 2.35, 0.84], placements=[AssetInstance() for _ in range(1)])
side_table_G = Assets(description="side table", size=[0.58, 0.58, 0.50], placements=[AssetInstance() for _ in range(1)])
multi_person_sofa_H = Assets(description="multi person sofa", size=[0.90, 2.20, 0.82], placements=[AssetInstance() for _ in range(1)])
fruit_Y = Assets(description="fruit", size=[0.09, 0.09, 0.08], placements=[AssetInstance() for _ in range(1)])
high_chair_D = Assets(description="high chair", size=[0.55, 0.49, 1.01], placements=[AssetInstance() for _ in range(1)])
plant_group_2_D = Assets(description="plant", size=[0.50, 0.50, 1.25], placements=[AssetInstance() for _ in range(1)])
side_table_H = Assets(description="side table", size=[0.60, 0.60, 0.52], placements=[AssetInstance() for _ in range(1)])
shelf = Assets(description="shelf", size=[0.32, 1.40, 1.80], placements=[AssetInstance() for _ in range(1)])
chair_X = Assets(description="chair", size=[0.58, 0.53, 0.84], placements=[AssetInstance() for _ in range(1)])
chair_Y = Assets(description="chair", size=[0.60, 0.55, 0.85], placements=[AssetInstance() for _ in range(1)])
chair_Z = Assets(description="chair", size=[0.57, 0.52, 0.83], placements=[AssetInstance() for _ in range(1)])
plant_group_2_E = Assets(description="plant", size=[0.70, 0.70, 1.70], placements=[AssetInstance() for _ in range(1)])
plant_group_2_F = Assets(description="plant", size=[0.38, 0.38, 0.85], placements=[AssetInstance() for _ in range(1)])
floor_lamp_C = Assets(description="floor lamp", size=[0.44, 0.44, 1.68], placements=[AssetInstance() for _ in range(1)])
landscape_stone_C = Assets(description="landscape stone", size=[0.70, 0.95, 0.46], placements=[AssetInstance() for _ in range(1)])
fruit_Z = Assets(description="fruit", size=[0.10, 0.10, 0.09], placements=[AssetInstance() for _ in range(1)])
fruit_group_2_A = Assets(description="fruit", size=[0.08, 0.08, 0.07], placements=[AssetInstance() for _ in range(1)])
plant_group_2_G = Assets(description="plant", size=[0.60, 0.60, 1.50], placements=[AssetInstance() for _ in range(1)])
fruit_group_2_B = Assets(description="fruit", size=[0.10, 0.11, 0.09], placements=[AssetInstance() for _ in range(1)])
water_bar = Assets(description="water bar", size=[0.70, 2.40, 1.05], placements=[AssetInstance() for _ in range(1)])
chair_group_2_A = Assets(description="chair", size=[0.59, 0.54, 0.85], placements=[AssetInstance() for _ in range(1)])
fruit_group_2_C = Assets(description="fruit", size=[0.09, 0.09, 0.08], placements=[AssetInstance() for _ in range(1)])
billboard = Assets(description="billboard", size=[0.12, 2.40, 1.35], placements=[AssetInstance() for _ in range(1)])
jar = Assets(description="jar", size=[0.16, 0.16, 0.28], placements=[AssetInstance() for _ in range(1)])
fruit_group_2_D = Assets(description="fruit", size=[0.10, 0.10, 0.09], placements=[AssetInstance() for _ in range(1)])
flowerpot_E = Assets(description="flowerpot", size=[0.40, 0.40, 0.38], placements=[AssetInstance() for _ in range(1)])
side_table_I = Assets(description="side table", size=[0.55, 0.55, 0.50], placements=[AssetInstance() for _ in range(1)])
chair_group_2_B = Assets(description="chair", size=[0.58, 0.53, 0.84], placements=[AssetInstance() for _ in range(1)])
landscape_stone_D = Assets(description="landscape stone", size=[0.60, 0.80, 0.40], placements=[AssetInstance() for _ in range(1)])
high_chair_E = Assets(description="high chair", size=[0.56, 0.50, 1.02], placements=[AssetInstance() for _ in range(1)])
fruit_group_2_E = Assets(description="fruit", size=[0.08, 0.08, 0.07], placements=[AssetInstance() for _ in range(1)])
table_D = Assets(description="table", size=[0.90, 1.70, 0.75], placements=[AssetInstance() for _ in range(1)])
plant_group_2_H = Assets(description="plant", size=[0.65, 0.65, 1.60], placements=[AssetInstance() for _ in range(1)])
chair_group_2_C = Assets(description="chair", size=[0.60, 0.55, 0.86], placements=[AssetInstance() for _ in range(1)])
cup_C = Assets(description="cup", size=[0.09, 0.09, 0.12], placements=[AssetInstance() for _ in range(1)])
multi_person_sofa_I = Assets(description="multi person sofa", size=[0.94, 2.30, 0.83], placements=[AssetInstance() for _ in range(1)])
fruit_group_2_F = Assets(description="fruit", size=[0.10, 0.10, 0.09], placements=[AssetInstance() for _ in range(1)])
chair_group_2_D = Assets(description="chair", size=[0.58, 0.52, 0.84], placements=[AssetInstance() for _ in range(1)])
chair_group_2_E = Assets(description="chair", size=[0.59, 0.54, 0.85], placements=[AssetInstance() for _ in range(1)])
plant_group_2_I = Assets(description="plant", size=[0.45, 0.45, 1.10], placements=[AssetInstance() for _ in range(1)])
plant_group_2_J = Assets(description="plant", size=[0.35, 0.35, 0.75], placements=[AssetInstance() for _ in range(1)])
side_table_J = Assets(description="side table", size=[0.60, 0.60, 0.52], placements=[AssetInstance() for _ in range(1)])
side_table_K = Assets(description="side table", size=[0.55, 0.55, 0.50], placements=[AssetInstance() for _ in range(1)])

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

plant_A[0].position = [6.715335418562416, 6.851101661616638, 0.775]
plant_A[0].rotation = [0, 0, 0]
fruit_A[0].position = [5.279660471897502, 8.714911574373103, 0.04]
fruit_A[0].rotation = [0, 0, 0]
table_A[0].position = [8.832470871771466, 5.579108817024144, 0.375]
table_A[0].rotation = [0, 0, 0]
chair_A[0].position = [13.776300285085235, 2.562036861877493, 0.42]
chair_A[0].rotation = [0, 0, 0]
side_table_A[0].position = [7.416215583563333, 5.189132097785975, 0.26]
side_table_A[0].rotation = [0, 0, 0]
plant_B[0].position = [14.18642516499795, 3.16725680671861, 0.575]
plant_B[0].rotation = [0, 0, 0]
plant_C[0].position = [6.597000486478625, 5.759532941963927, 0.85]
plant_C[0].rotation = [0, 0, 0]
chair_B[0].position = [2.319037071471075, 7.979947236860584, 0.43]
chair_B[0].rotation = [0, 0, 0]
plant_D[0].position = [4.080859914908888, 8.291434466525898, 0.375]
plant_D[0].rotation = [0, 0, 0]
fruit_B[0].position = [8.292565225954071, 0.4687464375786902, 0.045]
fruit_B[0].rotation = [0, 0, 0]
chair_C[0].position = [3.601616403760873, 6.5962245392592616, 0.415]
chair_C[0].rotation = [0, 0, 0]
cup_A[0].position = [2.2046953515998684, 4.824806812357413, 0.055]
cup_A[0].rotation = [0, 0, 0]
chair_D[0].position = [10.26808219247019, 0.46768110491923087, 0.425]
chair_D[0].rotation = [0, 0, 0]
plant_E[0].position = [4.854168186599155, 5.140318916583378, 0.675]
plant_E[0].rotation = [0, 0, 0]
chair_E[0].position = [3.452922431036716, 6.802356966335782, 0.42]
chair_E[0].rotation = [0, 0, 0]
fruit_C[0].position = [5.18824811914512, 0.7704735681621789, 0.035]
fruit_C[0].rotation = [0, 0, 0]
plant_F[0].position = [4.3274745501651095, 2.3963496426773325, 0.95]
plant_F[0].rotation = [0, 0, 0]
multi_person_sofa_A[0].position = [0.4028878267046215, 8.320335015418754, 0.41]
multi_person_sofa_A[0].rotation = [0, 0, 0]
fruit_D[0].position = [1.677096807688844, 0.325972416976689, 0.05]
fruit_D[0].rotation = [0, 0, 0]
multi_person_sofa_B[0].position = [5.417170667594397, 8.063788992819296, 0.42]
multi_person_sofa_B[0].rotation = [0, 0, 0]
fruit_E[0].position = [13.1835780370048, 7.759711277959688, 0.04]
fruit_E[0].rotation = [0, 0, 0]
plant_G[0].position = [14.07681733430434, 6.722170645471942, 0.625]
plant_G[0].rotation = [0, 0, 0]
cup_B[0].position = [5.906408286753282, 4.2088509956710585, 0.06]
cup_B[0].rotation = [0, 0, 0]
fruit_F[0].position = [10.80890840578611, 1.6846656024052502, 0.045]
fruit_F[0].rotation = [0, 0, 0]
high_chair_A[0].position = [13.131332882049193, 5.38831877832577, 0.51]
high_chair_A[0].rotation = [0, 0, 0]
landscape_stone_A[0].position = [2.672231974193435, 2.2675572323801476, 0.21]
landscape_stone_A[0].rotation = [0, 0, 0]
plant_H[0].position = [2.8300441301423795, 8.346137883023715, 0.425]
plant_H[0].rotation = [0, 0, 0]
side_table_B[0].position = [13.735959298763163, 7.382619314761488, 0.25]
side_table_B[0].rotation = [0, 0, 0]
fruit_G[0].position = [14.09245885024563, 0.10420550618831624, 0.035]
fruit_G[0].rotation = [0, 0, 0]
multi_person_sofa_C[0].position = [0.19210861378448793, 8.189467629433382, 0.4]
multi_person_sofa_C[0].rotation = [0, 0, 0]
chair_F[0].position = [9.668226599082747, 3.954679302406552, 0.43]
chair_F[0].rotation = [0, 0, 0]
plant_I[0].position = [0.5660540540926969, 8.202442177341837, 0.8]
plant_I[0].rotation = [0, 0, 0]
flowerpot_A[0].position = [8.761185663578297, 4.2912994607235575, 0.175]
flowerpot_A[0].rotation = [0, 0, 0]
chair_G[0].position = [2.942579721505684, 3.7632443683081953, 0.415]
chair_G[0].rotation = [0, 0, 0]
plant_J[0].position = [8.747066827295798, 4.818663943514892, 0.475]
plant_J[0].rotation = [0, 0, 0]
side_table_C[0].position = [1.834636585516707, 1.4770179836536075, 0.24]
side_table_C[0].rotation = [0, 0, 0]
fruit_H[0].position = [12.153057429600063, 4.783556656264806, 0.045]
fruit_H[0].rotation = [0, 0, 0]
chair_H[0].position = [1.6421137250670625, 1.885886853049447, 0.425]
chair_H[0].rotation = [0, 0, 0]
chair_I[0].position = [10.77389704520296, 8.804173156329139, 0.435]
chair_I[0].rotation = [0, 0, 0]
chair_J[0].position = [10.376597415268645, 7.612935248641497, 0.42]
chair_J[0].rotation = [0, 0, 0]
chair_K[0].position = [11.713946706994259, 6.451696630106733, 0.425]
chair_K[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [3.3869501517351046, 5.923157144215915, 0.825]
floor_lamp_A[0].rotation = [0, 0, 0]
plant_K[0].position = [9.497709997037768, 8.999521117360496, 0.7]
plant_K[0].rotation = [0, 0, 0]
plant_L[0].position = [9.479473491983201, 7.425960893680325, 0.325]
plant_L[0].rotation = [0, 0, 0]
chair_L[0].position = [11.749067303938165, 3.283618480806342, 0.43]
chair_L[0].rotation = [0, 0, 0]
plant_M[0].position = [10.574149937094658, 5.454535123058321, 0.875]
plant_M[0].rotation = [0, 0, 0]
plant_N[0].position = [12.447524216971319, 1.8530532379175182, 0.55]
plant_N[0].rotation = [0, 0, 0]
fruit_I[0].position = [8.715441353939605, 5.835299235438715, 0.04]
fruit_I[0].rotation = [0, 0, 0]
plant_O[0].position = [7.964733187550455, 5.5498844347606, 0.75]
plant_O[0].rotation = [0, 0, 0]
side_table_D[0].position = [12.232632848913683, 8.793165753003317, 0.25]
side_table_D[0].rotation = [0, 0, 0]
chair_M[0].position = [4.723770313848459, 9.03760713397998, 0.42]
chair_M[0].rotation = [0, 0, 0]
flowerpot_B[0].position = [9.657229361524942, 10.092774565729165, 0.19]
flowerpot_B[0].rotation = [0, 0, 0]
fruit_J[0].position = [7.8085831537289785, 0.12338236738713429, 0.045]
fruit_J[0].rotation = [0, 0, 0]
plant_P[0].position = [2.572567769777499, 0.5324203987493797, 0.9]
plant_P[0].rotation = [0, 0, 0]
plant_Q[0].position = [8.054830465826628, 9.43293533626558, 0.4]
plant_Q[0].rotation = [0, 0, 0]
fruit_K[0].position = [4.642187505453536, 6.764003923315667, 0.035]
fruit_K[0].rotation = [0, 0, 0]
chair_N[0].position = [3.499971873490305, 7.181874107587461, 0.415]
chair_N[0].rotation = [0, 0, 0]
plant_R[0].position = [11.049545179694883, 0.5517824191053822, 0.6]
plant_R[0].rotation = [0, 0, 0]
side_table_E[0].position = [1.371099860796193, 0.5325986658749431, 0.25]
side_table_E[0].rotation = [0, 0, 0]
plant_S[0].position = [1.819273842058082, 7.751109773909954, 0.775]
plant_S[0].rotation = [0, 0, 0]
fruit_L[0].position = [12.568876485664038, 4.093569113160615, 0.045]
fruit_L[0].rotation = [0, 0, 0]
high_chair_B[0].position = [7.0450209558582495, 4.321028219166385, 0.5]
high_chair_B[0].rotation = [0, 0, 0]
side_table_F[0].position = [1.4601710557834724, 3.3432176748048934, 0.26]
side_table_F[0].rotation = [0, 0, 0]
chair_O[0].position = [12.161057698875876, 3.991222705114231, 0.425]
chair_O[0].rotation = [0, 0, 0]
table_B[0].position = [7.335308209479064, 9.925363190657016, 0.375]
table_B[0].rotation = [0, 0, 0]
chair_P[0].position = [1.8562522414013605, 5.67877643834237, 0.42]
chair_P[0].rotation = [0, 0, 0]
flowerpot_C[0].position = [7.376293293662965, 7.296813389718328, 0.17]
flowerpot_C[0].rotation = [0, 0, 0]
chair_Q[0].position = [6.726671779884778, 3.570829512743734, 0.43]
chair_Q[0].rotation = [0, 0, 0]
plant_T[0].position = [5.667939893898114, 7.290165703686424, 0.65]
plant_T[0].rotation = [0, 0, 0]
dining_plate[0].position = [7.432083594871947, 1.408259335535892, 0.015]
dining_plate[0].rotation = [0, 0, 0]
chair_R[0].position = [10.312034479835281, 4.435286612543974, 0.415]
chair_R[0].rotation = [0, 0, 0]
high_chair_C[0].position = [13.055936723451461, 2.4123852671076436, 0.515]
high_chair_C[0].rotation = [0, 0, 0]
fruit_M[0].position = [2.770989816049757, 9.515106925952301, 0.04]
fruit_M[0].rotation = [0, 0, 0]
fruit_N[0].position = [11.346882012242991, 0.23882856820253234, 0.045]
fruit_N[0].rotation = [0, 0, 0]
multi_person_sofa_D[0].position = [6.5186348675065595, 4.307275962732583, 0.415]
multi_person_sofa_D[0].rotation = [0, 0, 0]
plant_U[0].position = [4.626741586231222, 4.671831929161999, 0.45]
plant_U[0].rotation = [0, 0, 0]
plant_V[0].position = [11.973304205119806, 8.633704938983701, 0.825]
plant_V[0].rotation = [0, 0, 0]
fruit_O[0].position = [9.745742239408417, 8.724714154578734, 0.035]
fruit_O[0].rotation = [0, 0, 0]
multi_person_sofa_E[0].position = [9.170533530589399, 2.6297081171613823, 0.405]
multi_person_sofa_E[0].rotation = [0, 0, 0]
plant_W[0].position = [5.137825713748017, 2.0445190952768444, 0.6]
plant_W[0].rotation = [0, 0, 0]
fruit_P[0].position = [4.9540275843793244, 9.121936977388245, 0.045]
fruit_P[0].rotation = [0, 0, 0]
multi_person_sofa_F[0].position = [8.820170114783378, 2.278342938593853, 0.425]
multi_person_sofa_F[0].rotation = [0, 0, 0]
fruit_Q[0].position = [7.86078548196282, 9.849088601463647, 0.04]
fruit_Q[0].rotation = [0, 0, 0]
plant_X[0].position = [11.994540747813746, 5.88549571442224, 0.725]
plant_X[0].rotation = [0, 0, 0]
chair_S[0].position = [8.055431608468814, 4.623632866669622, 0.425]
chair_S[0].rotation = [0, 0, 0]
table_C[0].position = [13.944455826956084, 0.07983801576721257, 0.37]
table_C[0].rotation = [0, 0, 0]
stool[0].position = [8.896383131434987, 4.6638023891114235, 0.23]
stool[0].rotation = [0, 0, 0]
fruit_R[0].position = [3.5502931929005377, 4.317261839984441, 0.045]
fruit_R[0].rotation = [0, 0, 0]
fruit_S[0].position = [5.063180858588964, 3.258471486315472, 0.035]
fruit_S[0].rotation = [0, 0, 0]
flowerpot_D[0].position = [13.571891913879838, 1.2596791839050614, 0.2]
flowerpot_D[0].rotation = [0, 0, 0]
chair_T[0].position = [9.997392183402333, 0.9833303536233403, 0.42]
chair_T[0].rotation = [0, 0, 0]
chair_U[0].position = [8.78219882670258, 8.570304521463289, 0.43]
chair_U[0].rotation = [0, 0, 0]
fruit_T[0].position = [13.675136083007722, 3.866706968350008, 0.045]
fruit_T[0].rotation = [0, 0, 0]
chair_V[0].position = [10.618612799558434, 4.07491801190759, 0.415]
chair_V[0].rotation = [0, 0, 0]
wall_lamp[0].position = [9.782841233900388, 2.900128016601025, 0.21]
wall_lamp[0].rotation = [0, 0, 0]
wine[0].position = [12.657399882525848, 0.2304451538958361, 0.15]
wine[0].rotation = [0, 0, 0]
fruit_U[0].position = [13.063343746267481, 2.1539636512889455, 0.04]
fruit_U[0].rotation = [0, 0, 0]
plant_Y[0].position = [13.62151598890533, 4.813028143803968, 0.4]
plant_Y[0].rotation = [0, 0, 0]
plant_Z[0].position = [3.1529615673140023, 0.6809497559719905, 0.675]
plant_Z[0].rotation = [0, 0, 0]
plant_group_2_A[0].position = [11.094174061875103, 6.5311328154258455, 0.925]
plant_group_2_A[0].rotation = [0, 0, 0]
fruit_V[0].position = [5.855037032926624, 4.855334382270505, 0.045]
fruit_V[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [3.9551121020625466, 6.790149563466774, 0.85]
floor_lamp_B[0].rotation = [0, 0, 0]
landscape_stone_B[0].position = [10.259319624440773, 6.231319159131287, 0.175]
landscape_stone_B[0].rotation = [0, 0, 0]
plant_group_2_B[0].position = [12.11078688207764, 8.123206593606877, 0.525]
plant_group_2_B[0].rotation = [0, 0, 0]
fruit_W[0].position = [2.5733990364998673, 5.024212853251091, 0.035]
fruit_W[0].rotation = [0, 0, 0]
fruit_X[0].position = [2.796990053882639, 2.7580346525793487, 0.045]
fruit_X[0].rotation = [0, 0, 0]
chair_W[0].position = [13.644609504792326, 9.138208831361228, 0.43]
chair_W[0].rotation = [0, 0, 0]
plant_group_2_C[0].position = [6.730825074366687, 7.151836260523459, 0.775]
plant_group_2_C[0].rotation = [0, 0, 0]
multi_person_sofa_G[0].position = [3.8700202287888033, 7.637815393293357, 0.42]
multi_person_sofa_G[0].rotation = [0, 0, 0]
side_table_G[0].position = [10.81914748136945, 9.233357827130844, 0.25]
side_table_G[0].rotation = [0, 0, 0]
multi_person_sofa_H[0].position = [1.9789910716200343, 5.721576739355098, 0.41]
multi_person_sofa_H[0].rotation = [0, 0, 0]
fruit_Y[0].position = [12.598869764951107, 9.811323338344513, 0.04]
fruit_Y[0].rotation = [0, 0, 0]
high_chair_D[0].position = [8.724512713950526, 1.8374810306348157, 0.505]
high_chair_D[0].rotation = [0, 0, 0]
plant_group_2_D[0].position = [2.914096493383958, 3.4511894274059487, 0.625]
plant_group_2_D[0].rotation = [0, 0, 0]
side_table_H[0].position = [2.7201587910509324, 4.538286980408135, 0.26]
side_table_H[0].rotation = [0, 0, 0]
shelf[0].position = [9.89404468645937, 1.1083911997533282, 0.9]
shelf[0].rotation = [0, 0, 0]
chair_X[0].position = [6.381164487675241, 5.109741990787726, 0.42]
chair_X[0].rotation = [0, 0, 0]
chair_Y[0].position = [6.176920126381909, 8.399898879707957, 0.425]
chair_Y[0].rotation = [0, 0, 0]
chair_Z[0].position = [2.5135240121055205, 4.489322898238944, 0.415]
chair_Z[0].rotation = [0, 0, 0]
plant_group_2_E[0].position = [5.651531664661862, 2.509814597136473, 0.85]
plant_group_2_E[0].rotation = [0, 0, 0]
plant_group_2_F[0].position = [2.356918392692041, 1.2422802313044359, 0.425]
plant_group_2_F[0].rotation = [0, 0, 0]
floor_lamp_C[0].position = [13.28918865547531, 3.8680076422155225, 0.84]
floor_lamp_C[0].rotation = [0, 0, 0]
landscape_stone_C[0].position = [6.496598248251865, 8.443422126435483, 0.23]
landscape_stone_C[0].rotation = [0, 0, 0]
fruit_Z[0].position = [10.725652020317213, 1.7364965137924195, 0.045]
fruit_Z[0].rotation = [0, 0, 0]
fruit_group_2_A[0].position = [8.694753924280333, 8.345175796204286, 0.035]
fruit_group_2_A[0].rotation = [0, 0, 0]
plant_group_2_G[0].position = [9.26248209100532, 2.928147026585198, 0.75]
plant_group_2_G[0].rotation = [0, 0, 0]
fruit_group_2_B[0].position = [13.900023089311798, 0.12044168497039295, 0.045]
fruit_group_2_B[0].rotation = [0, 0, 0]
water_bar[0].position = [7.079468715086639, 5.409436519589491, 0.525]
water_bar[0].rotation = [0, 0, 0]
chair_group_2_A[0].position = [8.927396444512157, 2.7431732210890325, 0.425]
chair_group_2_A[0].rotation = [0, 0, 0]
fruit_group_2_C[0].position = [10.838397010242241, 7.539119695567469, 0.04]
fruit_group_2_C[0].rotation = [0, 0, 0]
billboard[0].position = [12.022421974252028, 3.051275826989486, 0.675]
billboard[0].rotation = [0, 0, 0]
jar[0].position = [11.333871370887582, 7.73021500125345, 0.14]
jar[0].rotation = [0, 0, 0]
fruit_group_2_D[0].position = [11.164719080011967, 4.510357489564747, 0.045]
fruit_group_2_D[0].rotation = [0, 0, 0]
flowerpot_E[0].position = [7.0107939393101475, 2.653913520022426, 0.19]
flowerpot_E[0].rotation = [0, 0, 0]
side_table_I[0].position = [0.7166675853284568, 7.820321321880608, 0.25]
side_table_I[0].rotation = [0, 0, 0]
chair_group_2_B[0].position = [11.391971052018599, 1.2598896616062925, 0.42]
chair_group_2_B[0].rotation = [0, 0, 0]
landscape_stone_D[0].position = [9.240543943438277, 9.812155821268728, 0.2]
landscape_stone_D[0].rotation = [0, 0, 0]
high_chair_E[0].position = [5.052485918650895, 9.921240223052578, 0.51]
high_chair_E[0].rotation = [0, 0, 0]
fruit_group_2_E[0].position = [12.916420964101443, 2.8201713425634387, 0.035]
fruit_group_2_E[0].rotation = [0, 0, 0]
table_D[0].position = [4.450998058480763, 1.868899503153652, 0.375]
table_D[0].rotation = [0, 0, 0]
plant_group_2_H[0].position = [9.12908605060849, 9.015126847267467, 0.8]
plant_group_2_H[0].rotation = [0, 0, 0]
chair_group_2_C[0].position = [13.027030619971665, 6.442003222728293, 0.43]
chair_group_2_C[0].rotation = [0, 0, 0]
cup_C[0].position = [11.935603154727092, 7.524739799286385, 0.06]
cup_C[0].rotation = [0, 0, 0]
multi_person_sofa_I[0].position = [11.321458013694068, 7.489102778942913, 0.415]
multi_person_sofa_I[0].rotation = [0, 0, 0]
fruit_group_2_F[0].position = [5.825707111440631, 8.272180099885137, 0.045]
fruit_group_2_F[0].rotation = [0, 0, 0]
chair_group_2_D[0].position = [10.475354332433989, 6.964967450099929, 0.42]
chair_group_2_D[0].rotation = [0, 0, 0]
chair_group_2_E[0].position = [2.734559082396526, 3.799662896021694, 0.425]
chair_group_2_E[0].rotation = [0, 0, 0]
plant_group_2_I[0].position = [11.825982097332988, 7.83662313979785, 0.55]
plant_group_2_I[0].rotation = [0, 0, 0]
plant_group_2_J[0].position = [9.769753360342483, 2.874553292437249, 0.375]
plant_group_2_J[0].rotation = [0, 0, 0]
side_table_J[0].position = [7.749047472101797, 5.999953122317441, 0.26]
side_table_J[0].rotation = [0, 0, 0]
side_table_K[0].position = [5.898140950492629, 3.816261202011113, 0.25]
side_table_K[0].rotation = [0, 0, 0]
plant_A[0].position = [6.715335418562416, 6.851101661616638, 0.775]
plant_A[0].rotation = [0, 0, 0]
fruit_A[0].position = [5.279660471897502, 8.714911574373103, 0.04]
fruit_A[0].rotation = [0, 0, 0]
table_A[0].position = [8.832470871771466, 5.579108817024144, 0.375]
table_A[0].rotation = [0, 0, 0]
chair_A[0].position = [13.776300285085235, 2.562036861877493, 0.42]
chair_A[0].rotation = [0, 0, 0]
side_table_A[0].position = [7.416215583563333, 5.189132097785975, 0.26]
side_table_A[0].rotation = [0, 0, 0]
plant_B[0].position = [14.18642516499795, 3.16725680671861, 0.575]
plant_B[0].rotation = [0, 0, 0]
plant_C[0].position = [6.597000486478625, 5.759532941963927, 0.85]
plant_C[0].rotation = [0, 0, 0]
chair_B[0].position = [2.319037071471075, 7.979947236860584, 0.43]
chair_B[0].rotation = [0, 0, 0]
plant_D[0].position = [4.080859914908888, 8.291434466525898, 0.375]
plant_D[0].rotation = [0, 0, 0]
fruit_B[0].position = [8.292565225954071, 0.4687464375786902, 0.045]
fruit_B[0].rotation = [0, 0, 0]
chair_C[0].position = [3.601616403760873, 6.5962245392592616, 0.415]
chair_C[0].rotation = [0, 0, 0]
cup_A[0].position = [2.2046953515998684, 4.824806812357413, 0.055]
cup_A[0].rotation = [0, 0, 0]
chair_D[0].position = [10.26808219247019, 0.46768110491923087, 0.425]
chair_D[0].rotation = [0, 0, 0]
plant_E[0].position = [4.854168186599155, 5.140318916583378, 0.675]
plant_E[0].rotation = [0, 0, 0]
chair_E[0].position = [3.452922431036716, 6.802356966335782, 0.42]
chair_E[0].rotation = [0, 0, 0]
fruit_C[0].position = [5.18824811914512, 0.7704735681621789, 0.035]
fruit_C[0].rotation = [0, 0, 0]
plant_F[0].position = [4.3274745501651095, 2.3963496426773325, 0.95]
plant_F[0].rotation = [0, 0, 0]
multi_person_sofa_A[0].position = [0.4028878267046215, 8.320335015418754, 0.41]
multi_person_sofa_A[0].rotation = [0, 0, 0]
fruit_D[0].position = [1.677096807688844, 0.325972416976689, 0.05]
fruit_D[0].rotation = [0, 0, 0]
multi_person_sofa_B[0].position = [5.417170667594397, 8.063788992819296, 0.42]
multi_person_sofa_B[0].rotation = [0, 0, 0]
fruit_E[0].position = [13.1835780370048, 7.759711277959688, 0.04]
fruit_E[0].rotation = [0, 0, 0]
plant_G[0].position = [14.07681733430434, 6.722170645471942, 0.625]
plant_G[0].rotation = [0, 0, 0]
cup_B[0].position = [5.906408286753282, 4.2088509956710585, 0.06]
cup_B[0].rotation = [0, 0, 0]
fruit_F[0].position = [10.80890840578611, 1.6846656024052502, 0.045]
fruit_F[0].rotation = [0, 0, 0]
high_chair_A[0].position = [13.131332882049193, 5.38831877832577, 0.51]
high_chair_A[0].rotation = [0, 0, 0]
landscape_stone_A[0].position = [2.672231974193435, 2.2675572323801476, 0.21]
landscape_stone_A[0].rotation = [0, 0, 0]
plant_H[0].position = [2.8300441301423795, 8.346137883023715, 0.425]
plant_H[0].rotation = [0, 0, 0]
side_table_B[0].position = [13.735959298763163, 7.382619314761488, 0.25]
side_table_B[0].rotation = [0, 0, 0]
fruit_G[0].position = [14.09245885024563, 0.10420550618831624, 0.035]
fruit_G[0].rotation = [0, 0, 0]
multi_person_sofa_C[0].position = [0.19210861378448793, 8.189467629433382, 0.4]
multi_person_sofa_C[0].rotation = [0, 0, 0]
chair_F[0].position = [9.668226599082747, 3.954679302406552, 0.43]
chair_F[0].rotation = [0, 0, 0]
plant_I[0].position = [0.5660540540926969, 8.202442177341837, 0.8]
plant_I[0].rotation = [0, 0, 0]
flowerpot_A[0].position = [8.761185663578297, 4.2912994607235575, 0.175]
flowerpot_A[0].rotation = [0, 0, 0]
chair_G[0].position = [2.942579721505684, 3.7632443683081953, 0.415]
chair_G[0].rotation = [0, 0, 0]
plant_J[0].position = [8.747066827295798, 4.818663943514892, 0.475]
plant_J[0].rotation = [0, 0, 0]
side_table_C[0].position = [1.834636585516707, 1.4770179836536075, 0.24]
side_table_C[0].rotation = [0, 0, 0]
fruit_H[0].position = [12.153057429600063, 4.783556656264806, 0.045]
fruit_H[0].rotation = [0, 0, 0]
chair_H[0].position = [1.6421137250670625, 1.885886853049447, 0.425]
chair_H[0].rotation = [0, 0, 0]
chair_I[0].position = [10.77389704520296, 8.804173156329139, 0.435]
chair_I[0].rotation = [0, 0, 0]
chair_J[0].position = [10.376597415268645, 7.612935248641497, 0.42]
chair_J[0].rotation = [0, 0, 0]
chair_K[0].position = [11.713946706994259, 6.451696630106733, 0.425]
chair_K[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [3.3869501517351046, 5.923157144215915, 0.825]
floor_lamp_A[0].rotation = [0, 0, 0]
plant_K[0].position = [9.497709997037768, 8.999521117360496, 0.7]
plant_K[0].rotation = [0, 0, 0]
plant_L[0].position = [9.479473491983201, 7.425960893680325, 0.325]
plant_L[0].rotation = [0, 0, 0]
chair_L[0].position = [11.749067303938165, 3.283618480806342, 0.43]
chair_L[0].rotation = [0, 0, 0]
plant_M[0].position = [10.574149937094658, 5.454535123058321, 0.875]
plant_M[0].rotation = [0, 0, 0]
plant_N[0].position = [12.447524216971319, 1.8530532379175182, 0.55]
plant_N[0].rotation = [0, 0, 0]
fruit_I[0].position = [8.715441353939605, 5.835299235438715, 0.04]
fruit_I[0].rotation = [0, 0, 0]
plant_O[0].position = [7.964733187550455, 5.5498844347606, 0.75]
plant_O[0].rotation = [0, 0, 0]
side_table_D[0].position = [12.232632848913683, 8.793165753003317, 0.25]
side_table_D[0].rotation = [0, 0, 0]
chair_M[0].position = [4.723770313848459, 9.03760713397998, 0.42]
chair_M[0].rotation = [0, 0, 0]
flowerpot_B[0].position = [9.657229361524942, 10.092774565729165, 0.19]
flowerpot_B[0].rotation = [0, 0, 0]
fruit_J[0].position = [7.8085831537289785, 0.12338236738713429, 0.045]
fruit_J[0].rotation = [0, 0, 0]
plant_P[0].position = [2.572567769777499, 0.5324203987493797, 0.9]
plant_P[0].rotation = [0, 0, 0]
plant_Q[0].position = [8.054830465826628, 9.43293533626558, 0.4]
plant_Q[0].rotation = [0, 0, 0]
fruit_K[0].position = [4.642187505453536, 6.764003923315667, 0.035]
fruit_K[0].rotation = [0, 0, 0]
chair_N[0].position = [3.499971873490305, 7.181874107587461, 0.415]
chair_N[0].rotation = [0, 0, 0]
plant_R[0].position = [11.049545179694883, 0.5517824191053822, 0.6]
plant_R[0].rotation = [0, 0, 0]
side_table_E[0].position = [1.371099860796193, 0.5325986658749431, 0.25]
side_table_E[0].rotation = [0, 0, 0]
plant_S[0].position = [1.819273842058082, 7.751109773909954, 0.775]
plant_S[0].rotation = [0, 0, 0]
fruit_L[0].position = [12.568876485664038, 4.093569113160615, 0.045]
fruit_L[0].rotation = [0, 0, 0]
high_chair_B[0].position = [7.0450209558582495, 4.321028219166385, 0.5]
high_chair_B[0].rotation = [0, 0, 0]
side_table_F[0].position = [1.4601710557834724, 3.3432176748048934, 0.26]
side_table_F[0].rotation = [0, 0, 0]
chair_O[0].position = [12.161057698875876, 3.991222705114231, 0.425]
chair_O[0].rotation = [0, 0, 0]
table_B[0].position = [7.335308209479064, 9.925363190657016, 0.375]
table_B[0].rotation = [0, 0, 0]
chair_P[0].position = [1.8562522414013605, 5.67877643834237, 0.42]
chair_P[0].rotation = [0, 0, 0]
flowerpot_C[0].position = [7.376293293662965, 7.296813389718328, 0.17]
flowerpot_C[0].rotation = [0, 0, 0]
chair_Q[0].position = [6.726671779884778, 3.570829512743734, 0.43]
chair_Q[0].rotation = [0, 0, 0]
plant_T[0].position = [5.667939893898114, 7.290165703686424, 0.65]
plant_T[0].rotation = [0, 0, 0]
dining_plate[0].position = [7.432083594871947, 1.408259335535892, 0.015]
dining_plate[0].rotation = [0, 0, 0]
chair_R[0].position = [10.312034479835281, 4.435286612543974, 0.415]
chair_R[0].rotation = [0, 0, 0]
high_chair_C[0].position = [13.055936723451461, 2.4123852671076436, 0.515]
high_chair_C[0].rotation = [0, 0, 0]
fruit_M[0].position = [2.770989816049757, 9.515106925952301, 0.04]
fruit_M[0].rotation = [0, 0, 0]
fruit_N[0].position = [11.346882012242991, 0.23882856820253234, 0.045]
fruit_N[0].rotation = [0, 0, 0]
multi_person_sofa_D[0].position = [6.5186348675065595, 4.307275962732583, 0.415]
multi_person_sofa_D[0].rotation = [0, 0, 0]
plant_U[0].position = [4.626741586231222, 4.671831929161999, 0.45]
plant_U[0].rotation = [0, 0, 0]
plant_V[0].position = [11.973304205119806, 8.633704938983701, 0.825]
plant_V[0].rotation = [0, 0, 0]
fruit_O[0].position = [9.745742239408417, 8.724714154578734, 0.035]
fruit_O[0].rotation = [0, 0, 0]
multi_person_sofa_E[0].position = [9.170533530589399, 2.6297081171613823, 0.405]
multi_person_sofa_E[0].rotation = [0, 0, 0]
plant_W[0].position = [5.137825713748017, 2.0445190952768444, 0.6]
plant_W[0].rotation = [0, 0, 0]
fruit_P[0].position = [4.9540275843793244, 9.121936977388245, 0.045]
fruit_P[0].rotation = [0, 0, 0]
multi_person_sofa_F[0].position = [8.820170114783378, 2.278342938593853, 0.425]
multi_person_sofa_F[0].rotation = [0, 0, 0]
fruit_Q[0].position = [7.86078548196282, 9.849088601463647, 0.04]
fruit_Q[0].rotation = [0, 0, 0]
plant_X[0].position = [11.994540747813746, 5.88549571442224, 0.725]
plant_X[0].rotation = [0, 0, 0]
chair_S[0].position = [8.055431608468814, 4.623632866669622, 0.425]
chair_S[0].rotation = [0, 0, 0]
table_C[0].position = [13.944455826956084, 0.07983801576721257, 0.37]
table_C[0].rotation = [0, 0, 0]
stool[0].position = [8.896383131434987, 4.6638023891114235, 0.23]
stool[0].rotation = [0, 0, 0]
fruit_R[0].position = [3.5502931929005377, 4.317261839984441, 0.045]
fruit_R[0].rotation = [0, 0, 0]
fruit_S[0].position = [5.063180858588964, 3.258471486315472, 0.035]
fruit_S[0].rotation = [0, 0, 0]
flowerpot_D[0].position = [13.571891913879838, 1.2596791839050614, 0.2]
flowerpot_D[0].rotation = [0, 0, 0]
chair_T[0].position = [9.997392183402333, 0.9833303536233403, 0.42]
chair_T[0].rotation = [0, 0, 0]
chair_U[0].position = [8.78219882670258, 8.570304521463289, 0.43]
chair_U[0].rotation = [0, 0, 0]
fruit_T[0].position = [13.675136083007722, 3.866706968350008, 0.045]
fruit_T[0].rotation = [0, 0, 0]
chair_V[0].position = [10.618612799558434, 4.07491801190759, 0.415]
chair_V[0].rotation = [0, 0, 0]
wall_lamp[0].position = [9.782841233900388, 2.900128016601025, 0.21]
wall_lamp[0].rotation = [0, 0, 0]
wine[0].position = [12.657399882525848, 0.2304451538958361, 0.15]
wine[0].rotation = [0, 0, 0]
fruit_U[0].position = [13.063343746267481, 2.1539636512889455, 0.04]
fruit_U[0].rotation = [0, 0, 0]
plant_Y[0].position = [13.62151598890533, 4.813028143803968, 0.4]
plant_Y[0].rotation = [0, 0, 0]
plant_Z[0].position = [3.1529615673140023, 0.6809497559719905, 0.675]
plant_Z[0].rotation = [0, 0, 0]
plant_group_2_A[0].position = [11.094174061875103, 6.5311328154258455, 0.925]
plant_group_2_A[0].rotation = [0, 0, 0]
fruit_V[0].position = [5.855037032926624, 4.855334382270505, 0.045]
fruit_V[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [3.9551121020625466, 6.790149563466774, 0.85]
floor_lamp_B[0].rotation = [0, 0, 0]
landscape_stone_B[0].position = [10.259319624440773, 6.231319159131287, 0.175]
landscape_stone_B[0].rotation = [0, 0, 0]
plant_group_2_B[0].position = [12.11078688207764, 8.123206593606877, 0.525]
plant_group_2_B[0].rotation = [0, 0, 0]
fruit_W[0].position = [2.5733990364998673, 5.024212853251091, 0.035]
fruit_W[0].rotation = [0, 0, 0]
fruit_X[0].position = [2.796990053882639, 2.7580346525793487, 0.045]
fruit_X[0].rotation = [0, 0, 0]
chair_W[0].position = [13.644609504792326, 9.138208831361228, 0.43]
chair_W[0].rotation = [0, 0, 0]
plant_group_2_C[0].position = [6.730825074366687, 7.151836260523459, 0.775]
plant_group_2_C[0].rotation = [0, 0, 0]
multi_person_sofa_G[0].position = [3.8700202287888033, 7.637815393293357, 0.42]
multi_person_sofa_G[0].rotation = [0, 0, 0]
side_table_G[0].position = [10.81914748136945, 9.233357827130844, 0.25]
side_table_G[0].rotation = [0, 0, 0]
multi_person_sofa_H[0].position = [1.9789910716200343, 5.721576739355098, 0.41]
multi_person_sofa_H[0].rotation = [0, 0, 0]
fruit_Y[0].position = [12.598869764951107, 9.811323338344513, 0.04]
fruit_Y[0].rotation = [0, 0, 0]
high_chair_D[0].position = [8.724512713950526, 1.8374810306348157, 0.505]
high_chair_D[0].rotation = [0, 0, 0]
plant_group_2_D[0].position = [2.914096493383958, 3.4511894274059487, 0.625]
plant_group_2_D[0].rotation = [0, 0, 0]
side_table_H[0].position = [2.7201587910509324, 4.538286980408135, 0.26]
side_table_H[0].rotation = [0, 0, 0]
shelf[0].position = [9.89404468645937, 1.1083911997533282, 0.9]
shelf[0].rotation = [0, 0, 0]
chair_X[0].position = [6.381164487675241, 5.109741990787726, 0.42]
chair_X[0].rotation = [0, 0, 0]
chair_Y[0].position = [6.176920126381909, 8.399898879707957, 0.425]
chair_Y[0].rotation = [0, 0, 0]
chair_Z[0].position = [2.5135240121055205, 4.489322898238944, 0.415]
chair_Z[0].rotation = [0, 0, 0]
plant_group_2_E[0].position = [5.651531664661862, 2.509814597136473, 0.85]
plant_group_2_E[0].rotation = [0, 0, 0]
plant_group_2_F[0].position = [2.356918392692041, 1.2422802313044359, 0.425]
plant_group_2_F[0].rotation = [0, 0, 0]
floor_lamp_C[0].position = [13.28918865547531, 3.8680076422155225, 0.84]
floor_lamp_C[0].rotation = [0, 0, 0]
landscape_stone_C[0].position = [6.496598248251865, 8.443422126435483, 0.23]
landscape_stone_C[0].rotation = [0, 0, 0]
fruit_Z[0].position = [10.725652020317213, 1.7364965137924195, 0.045]
fruit_Z[0].rotation = [0, 0, 0]
fruit_group_2_A[0].position = [8.694753924280333, 8.345175796204286, 0.035]
fruit_group_2_A[0].rotation = [0, 0, 0]
plant_group_2_G[0].position = [9.26248209100532, 2.928147026585198, 0.75]
plant_group_2_G[0].rotation = [0, 0, 0]
fruit_group_2_B[0].position = [13.900023089311798, 0.12044168497039295, 0.045]
fruit_group_2_B[0].rotation = [0, 0, 0]
water_bar[0].position = [7.079468715086639, 5.409436519589491, 0.525]
water_bar[0].rotation = [0, 0, 0]
chair_group_2_A[0].position = [8.927396444512157, 2.7431732210890325, 0.425]
chair_group_2_A[0].rotation = [0, 0, 0]
fruit_group_2_C[0].position = [10.838397010242241, 7.539119695567469, 0.04]
fruit_group_2_C[0].rotation = [0, 0, 0]
billboard[0].position = [12.022421974252028, 3.051275826989486, 0.675]
billboard[0].rotation = [0, 0, 0]
jar[0].position = [11.333871370887582, 7.73021500125345, 0.14]
jar[0].rotation = [0, 0, 0]
fruit_group_2_D[0].position = [11.164719080011967, 4.510357489564747, 0.045]
fruit_group_2_D[0].rotation = [0, 0, 0]
flowerpot_E[0].position = [7.0107939393101475, 2.653913520022426, 0.19]
flowerpot_E[0].rotation = [0, 0, 0]
side_table_I[0].position = [0.7166675853284568, 7.820321321880608, 0.25]
side_table_I[0].rotation = [0, 0, 0]
chair_group_2_B[0].position = [11.391971052018599, 1.2598896616062925, 0.42]
chair_group_2_B[0].rotation = [0, 0, 0]
landscape_stone_D[0].position = [9.240543943438277, 9.812155821268728, 0.2]
landscape_stone_D[0].rotation = [0, 0, 0]
high_chair_E[0].position = [5.052485918650895, 9.921240223052578, 0.51]
high_chair_E[0].rotation = [0, 0, 0]
fruit_group_2_E[0].position = [12.916420964101443, 2.8201713425634387, 0.035]
fruit_group_2_E[0].rotation = [0, 0, 0]
table_D[0].position = [4.450998058480763, 1.868899503153652, 0.375]
table_D[0].rotation = [0, 0, 0]
plant_group_2_H[0].position = [9.12908605060849, 9.015126847267467, 0.8]
plant_group_2_H[0].rotation = [0, 0, 0]
chair_group_2_C[0].position = [13.027030619971665, 6.442003222728293, 0.43]
chair_group_2_C[0].rotation = [0, 0, 0]
cup_C[0].position = [11.935603154727092, 7.524739799286385, 0.06]
cup_C[0].rotation = [0, 0, 0]
multi_person_sofa_I[0].position = [11.321458013694068, 7.489102778942913, 0.415]
multi_person_sofa_I[0].rotation = [0, 0, 0]
fruit_group_2_F[0].position = [5.825707111440631, 8.272180099885137, 0.045]
fruit_group_2_F[0].rotation = [0, 0, 0]
chair_group_2_D[0].position = [10.475354332433989, 6.964967450099929, 0.42]
chair_group_2_D[0].rotation = [0, 0, 0]
chair_group_2_E[0].position = [2.734559082396526, 3.799662896021694, 0.425]
chair_group_2_E[0].rotation = [0, 0, 0]
plant_group_2_I[0].position = [11.825982097332988, 7.83662313979785, 0.55]
plant_group_2_I[0].rotation = [0, 0, 0]
plant_group_2_J[0].position = [9.769753360342483, 2.874553292437249, 0.375]
plant_group_2_J[0].rotation = [0, 0, 0]
side_table_J[0].position = [7.749047472101797, 5.999953122317441, 0.26]
side_table_J[0].rotation = [0, 0, 0]
side_table_K[0].position = [5.898140950492629, 3.816261202011113, 0.25]
side_table_K[0].rotation = [0, 0, 0]

solver.constraints = []

# Helper functions preserve explicit placements while giving every new instance
# both a position constraint and an orientation constraint.
def _place(asset, x, y, z, yaw=0.0, face=None):
    asset[0].position = [x, y, z]
    asset[0].rotation = [0, 0, radians(yaw)]

    # A weighted fixed-point constraint preserves the planned non-overlapping layout.
    position_anchor = AssetInstance(position=[x, y, z])
    solver.distance_constraint(
        asset[0], position_anchor, 0.0, 0.0, weight=10
    )

    if face is None:
        orientation_anchor = AssetInstance(
            position=[x, y, z],
            rotation=[0, 0, radians(yaw)]
        )
        solver.align_with(asset[0], orientation_anchor)
    else:
        facing_anchor = AssetInstance(position=[face[0], face[1], z])
        solver.point_towards(asset[0], facing_anchor)


def _place_on(asset, support, x, y, z, yaw=0.0):
    asset[0].position = [x, y, z]
    asset[0].rotation = [0, 0, radians(yaw)]

    # The support relationship is the most important vertical constraint.
    solver.on_top_of(asset[0], support[0])

    position_anchor = AssetInstance(position=[x, y, z])
    solver.distance_constraint(
        asset[0], position_anchor, 0.0, 0.0, weight=10
    )
    solver.align_with(asset[0], support[0], angle=yaw)


# ---------------------------------------------------------------------------
# Dining zone along the south side. Tables are spaced into four independent
# groups while preserving the main circulation route through the room.
# ---------------------------------------------------------------------------

_place(table_A, 3.00, 1.85, 0.375, 0)
_place(table_B, 5.95, 1.85, 0.375, 0)
_place(table_C, 8.75, 1.85, 0.370, 0)
_place(table_D, 11.35, 1.45, 0.375, 0)

# Chairs around table A.
_place(chair_A, 2.18, 1.30, 0.420, 0, face=(3.00, 1.85))
_place(chair_B, 3.82, 1.30, 0.430, 180, face=(3.00, 1.85))
_place(chair_C, 2.18, 2.38, 0.415, 0, face=(3.00, 1.85))
_place(chair_D, 3.82, 2.38, 0.425, 180, face=(3.00, 1.85))
_place(chair_E, 3.00, 0.68, 0.420, 90, face=(3.00, 1.85))

# Chairs around table B.
_place(chair_F, 5.12, 1.28, 0.430, 0, face=(5.95, 1.85))
_place(chair_G, 6.78, 1.28, 0.415, 180, face=(5.95, 1.85))
_place(chair_H, 5.12, 2.40, 0.425, 0, face=(5.95, 1.85))
_place(chair_I, 6.78, 2.40, 0.435, 180, face=(5.95, 1.85))
_place(chair_J, 5.95, 0.67, 0.420, 90, face=(5.95, 1.85))
_place(chair_K, 5.95, 3.02, 0.425, -90, face=(5.95, 1.85))

# Chairs around table C.
_place(chair_L, 7.92, 1.28, 0.430, 0, face=(8.75, 1.85))
_place(chair_M, 9.58, 1.28, 0.420, 180, face=(8.75, 1.85))
_place(chair_N, 7.92, 2.40, 0.415, 0, face=(8.75, 1.85))
_place(chair_O, 9.58, 2.40, 0.425, 180, face=(8.75, 1.85))
_place(chair_P, 8.75, 0.67, 0.420, 90, face=(8.75, 1.85))
_place(chair_Q, 8.75, 3.02, 0.430, -90, face=(8.75, 1.85))

# Chairs around table D remain south of the fixed partition at y=3.20.
_place(chair_R, 10.52, 1.02, 0.415, 0, face=(11.35, 1.45))
_place(chair_S, 12.18, 1.02, 0.425, 180, face=(11.35, 1.45))
_place(chair_T, 10.52, 1.88, 0.420, 0, face=(11.35, 1.45))
_place(chair_U, 12.18, 1.88, 0.430, 180, face=(11.35, 1.45))
_place(chair_V, 11.35, 2.70, 0.415, -90, face=(11.35, 1.45))

# High chairs supplement the dining groups without blocking their end aisles.
_place(high_chair_A, 4.18, 0.65, 0.510, 90, face=(3.00, 1.85))
_place(high_chair_B, 6.98, 0.64, 0.500, 90, face=(5.95, 1.85))
_place(high_chair_C, 9.78, 0.64, 0.515, 90, face=(8.75, 1.85))
_place(high_chair_D, 12.52, 2.62, 0.505, 135, face=(11.35, 1.45))
_place(high_chair_E, 10.25, 2.78, 0.510, -45, face=(11.35, 1.45))


# ---------------------------------------------------------------------------
# Lounge seating. Sofas are rotated so their long dimensions run east-west.
# Rows and gaps are staggered around the fixed columns and partitions.
# ---------------------------------------------------------------------------

_place(multi_person_sofa_A, 3.30, 4.82, 0.410, 90, face=(3.30, 5.75))
_place(multi_person_sofa_B, 6.20, 4.82, 0.420, 90, face=(6.20, 5.75))
_place(multi_person_sofa_C, 9.10, 4.82, 0.400, 90, face=(9.10, 5.75))

_place(multi_person_sofa_D, 3.30, 6.62, 0.415, -90, face=(3.30, 5.75))
_place(multi_person_sofa_E, 6.20, 6.62, 0.405, -90, face=(6.20, 5.75))
_place(multi_person_sofa_F, 9.10, 6.62, 0.425, -90, face=(9.10, 5.75))
_place(multi_person_sofa_G, 12.35, 6.62, 0.420, 180, face=(10.85, 6.62))

_place(multi_person_sofa_H, 4.35, 8.72, 0.410, -90, face=(4.35, 7.75))
_place(multi_person_sofa_I, 8.05, 8.72, 0.415, -90, face=(8.05, 7.75))

# Side tables occupy usable gaps between seating groups.
_place(side_table_A, 4.68, 5.72, 0.260, 0)
_place(side_table_B, 7.65, 5.72, 0.250, 0)
_place(side_table_C, 10.55, 5.72, 0.240, 0)
_place(side_table_D, 2.00, 5.68, 0.250, 0)
_place(side_table_E, 4.78, 7.58, 0.250, 0)
_place(side_table_F, 6.85, 7.58, 0.260, 0)
_place(side_table_G, 9.92, 7.58, 0.250, 0)
_place(side_table_H, 13.55, 8.62, 0.260, 0)
_place(side_table_I, 2.65, 9.55, 0.250, 0)
_place(side_table_J, 10.72, 8.72, 0.260, 0)
_place(side_table_K, 13.52, 5.18, 0.250, 0)

# Additional lounge chairs face nearby sofas while preserving the west-door
# approach and the aisle between the middle and north seating rows.
_place(chair_W, 3.25, 7.72, 0.430, 90, face=(4.35, 8.72))
_place(chair_X, 5.72, 7.72, 0.420, 90, face=(4.35, 8.72))
_place(chair_Y, 7.82, 7.72, 0.425, 90, face=(8.05, 8.72))
_place(chair_Z, 8.78, 7.72, 0.415, 90, face=(8.05, 8.72))

_place(chair_group_2_A, 2.55, 8.55, 0.425, 0, face=(4.35, 8.72))
_place(chair_group_2_B, 6.05, 8.72, 0.420, 0, face=(8.05, 8.72))
_place(chair_group_2_C, 9.72, 8.72, 0.430, 180, face=(8.05, 8.72))
_place(chair_group_2_D, 11.45, 8.05, 0.420, -90, face=(11.45, 6.62))
_place(chair_group_2_E, 12.50, 8.08, 0.425, -90, face=(12.35, 6.62))

_place(stool, 11.55, 5.42, 0.230, 180, face=(12.35, 6.62))


# ---------------------------------------------------------------------------
# Service, storage, display, and lighting.
# ---------------------------------------------------------------------------

# The bar is below the east door opening; it does not intrude into the
# y=2.76..4.36 door-clearance zone.
_place(water_bar, 13.78, 1.35, 0.525, 180)
solver.against_wall(water_bar[0], walls[1])

# The shelf uses the west wall above the fixed low cabinet.
_place(shelf, 1.45, 5.86, 0.900, 0)
solver.against_wall(shelf[0], walls[15])

# The billboard is placed against the uninterrupted north wall.
_place(billboard, 11.92, 10.05, 0.675, -90)
solver.against_wall(billboard[0], walls[6])

# Wall lamp is elevated on the east wall, outside the door opening.
_place(wall_lamp, 14.10, 5.05, 1.55, 180)
solver.against_wall(wall_lamp[0], walls[5])

_place(floor_lamp_A, 1.72, 4.72, 0.825, 0)
_place(floor_lamp_B, 5.72, 9.70, 0.850, -90)
_place(floor_lamp_C, 10.18, 9.70, 0.840, -90)

# Landscape stones form small planting accents away from walking routes.
_place(landscape_stone_A, 2.05, 3.65, 0.210, 20)
_place(landscape_stone_B, 4.05, 3.72, 0.175, -15)
_place(landscape_stone_C, 12.82, 5.12, 0.230, 75)
_place(landscape_stone_D, 13.25, 9.58, 0.200, 90)


# ---------------------------------------------------------------------------
# Floor plants. Large plants are concentrated at boundaries and at the ends
# of furniture groups, leaving both marked door approaches unobstructed.
# ---------------------------------------------------------------------------

_place(plant_A, 2.05, 4.42, 0.775, 0)
_place(plant_B, 2.02, 6.72, 0.575, 15)
_place(plant_C, 3.05, 9.72, 0.850, -20)
_place(plant_E, 4.65, 9.72, 0.675, 10)
_place(plant_F, 6.55, 9.70, 0.950, -10)
_place(plant_G, 7.45, 3.55, 0.625, 20)
_place(plant_I, 9.05, 9.68, 0.800, -15)
_place(plant_K, 10.85, 9.68, 0.700, 15)
_place(plant_M, 12.15, 9.60, 0.875, -20)
_place(plant_O, 13.62, 9.65, 0.750, 10)

_place(plant_P, 1.70, 6.05, 0.900, 0)
_place(plant_R, 1.72, 7.05, 0.600, 15)
_place(plant_S, 4.75, 3.62, 0.775, -10)
_place(plant_T, 6.22, 3.60, 0.650, 10)
_place(plant_V, 8.42, 3.62, 0.825, -15)
_place(plant_W, 9.65, 3.62, 0.600, 15)
_place(plant_X, 13.55, 4.62, 0.725, 0)
_place(plant_Z, 13.62, 7.72, 0.675, 10)

_place(plant_group_2_A, 2.18, 9.65, 0.925, -10)
_place(plant_group_2_C, 7.12, 9.68, 0.775, 15)
_place(plant_group_2_D, 10.72, 4.88, 0.625, -15)
_place(plant_group_2_E, 11.42, 5.62, 0.850, 10)
_place(plant_group_2_G, 12.88, 7.70, 0.750, -10)
_place(plant_group_2_H, 13.70, 5.92, 0.800, 20)


# ---------------------------------------------------------------------------
# Small plants and flowerpots are supported by side tables, dining tables,
# the shelf, or the water bar instead of floating in the scene.
# ---------------------------------------------------------------------------

_place_on(plant_D, side_table_A, 4.68, 5.72, 0.895, 0)
_place_on(plant_H, side_table_B, 7.65, 5.72, 0.925, 15)
_place_on(plant_J, side_table_C, 10.55, 5.72, 0.955, -10)
_place_on(plant_L, side_table_D, 2.00, 5.68, 0.845, 0)
_place_on(plant_N, side_table_E, 4.78, 7.58, 1.050, 10)
_place_on(plant_Q, side_table_F, 6.85, 7.58, 0.920, -10)
_place_on(plant_U, side_table_G, 9.92, 7.58, 0.950, 5)
_place_on(plant_Y, side_table_H, 13.55, 8.62, 0.920, -5)

_place_on(plant_group_2_B, side_table_I, 2.65, 9.55, 1.025, 10)
_place_on(plant_group_2_F, side_table_J, 10.72, 8.72, 0.945, -10)
_place_on(plant_group_2_I, side_table_K, 13.52, 5.18, 1.050, 15)
_place_on(plant_group_2_J, shelf, 1.68, 5.86, 2.175, 0)

_place_on(flowerpot_A, table_A, 3.00, 1.85, 0.925, 0)
_place_on(flowerpot_B, table_B, 5.95, 1.85, 0.940, 10)
_place_on(flowerpot_C, table_C, 8.75, 1.85, 0.910, -10)
_place_on(flowerpot_D, table_D, 11.35, 1.45, 0.950, 0)
_place_on(flowerpot_E, water_bar, 13.78, 1.05, 1.240, 0)


# ---------------------------------------------------------------------------
# Tabletop food, drink, and serving objects. Offsets keep the small objects
# separated from one another and from the table-center flowerpots.
# ---------------------------------------------------------------------------

# Table A.
_place_on(fruit_A, table_A, 2.78, 1.55, 0.790, 0)
_place_on(fruit_B, table_A, 3.22, 1.55, 0.795, 20)
_place_on(fruit_C, table_A, 2.78, 2.14, 0.785, -15)
_place_on(fruit_D, table_A, 3.22, 2.14, 0.800, 10)
_place_on(cup_A, table_A, 3.00, 1.48, 0.805, 0)

# Table B.
_place_on(fruit_E, table_B, 5.72, 1.48, 0.790, 0)
_place_on(fruit_F, table_B, 6.18, 1.48, 0.795, 20)
_place_on(fruit_G, table_B, 5.70, 2.20, 0.785, -15)
_place_on(fruit_H, table_B, 6.20, 2.20, 0.795, 10)
_place_on(fruit_I, table_B, 5.95, 2.35, 0.790, 0)
_place_on(cup_B, table_B, 5.95, 1.40, 0.810, 0)

# Table C.
_place_on(fruit_J, table_C, 8.52, 1.48, 0.785, 0)
_place_on(fruit_K, table_C, 8.98, 1.48, 0.775, 15)
_place_on(fruit_L, table_C, 8.50, 2.19, 0.785, -15)
_place_on(fruit_M, table_C, 9.00, 2.19, 0.780, 10)
_place_on(fruit_N, table_C, 8.75, 2.36, 0.785, 0)
_place_on(dining_plate, table_C, 8.75, 1.47, 0.765, 0)

# Table D.
_place_on(fruit_O, table_D, 11.12, 1.12, 0.785, 0)
_place_on(fruit_P, table_D, 11.58, 1.12, 0.795, 20)
_place_on(fruit_Q, table_D, 11.10, 1.79, 0.790, -15)
_place_on(fruit_R, table_D, 11.60, 1.79, 0.795, 10)
_place_on(fruit_S, table_D, 11.35, 2.03, 0.785, 0)
_place_on(cup_C, table_D, 11.35, 1.04, 0.810, 0)

# Lounge side tables.
_place_on(fruit_T, side_table_A, 4.48, 5.58, 0.565, 0)
_place_on(fruit_U, side_table_B, 7.84, 5.57, 0.540, 10)
_place_on(fruit_V, side_table_C, 10.35, 5.56, 0.565, -10)
_place_on(fruit_W, side_table_D, 1.83, 5.53, 0.535, 0)
_place_on(fruit_X, side_table_E, 4.58, 7.43, 0.545, 15)
_place_on(fruit_Y, side_table_F, 7.04, 7.43, 0.560, -15)
_place_on(fruit_Z, side_table_G, 9.72, 7.43, 0.545, 10)

_place_on(fruit_group_2_A, side_table_H, 13.37, 8.47, 0.555, 0)
_place_on(fruit_group_2_B, side_table_I, 2.46, 9.39, 0.545, 15)
_place_on(fruit_group_2_C, side_table_J, 10.52, 8.57, 0.560, -10)
_place_on(fruit_group_2_D, side_table_K, 13.32, 5.03, 0.545, 10)

# Remaining refreshments are grouped on the bar.
_place_on(fruit_group_2_E, water_bar, 13.76, 1.42, 1.085, 0)
_place_on(fruit_group_2_F, water_bar, 13.76, 1.70, 1.095, 15)
_place_on(wine, water_bar, 13.76, 1.95, 1.200, 0)
_place_on(jar, water_bar, 13.76, 0.72, 1.190, 0)

solver.constraints = []
side_table_J[0].position = [10.720000267028809, 8.720000267028809, 0.25999999046325684]
side_table_J[0].rotation = [0, 0, 0.021991148286022624]
side_table_J[0].optimize = 2
fruit_B[0].position = [3.2200000286102295, 1.5499999523162842, 0.7950000166893005]
fruit_B[0].rotation = [0, 0, 0.39618973554881015]
fruit_B[0].optimize = 2
fruit_T[0].position = [4.480000019073486, 5.579999923706055, 0.5649999976158142]
fruit_T[0].rotation = [0, 0, 0.021991145012924443]
fruit_T[0].optimize = 2
table_C[0].position = [8.75, 1.850000023841858, 0.3700000047683716]
table_C[0].rotation = [0, 0, 0.053407073383009665]
table_C[0].optimize = 2
plant_Z[0].position = [13.619999885559082, 7.71999979019165, 0.675000011920929]
plant_Z[0].rotation = [0, 0, 0.1839577022555754]
plant_Z[0].optimize = 2
high_chair_D[0].position = [12.520000457763672, 2.619999885559082, 0.5049999952316284]
high_chair_D[0].rotation = [0, 0, 2.3656192553579443]
high_chair_D[0].optimize = 2
flowerpot_C[0].position = [8.75, 1.850000023841858, 0.9100000262260437]
flowerpot_C[0].rotation = [0, 0, -0.12112585761989468]
flowerpot_C[0].optimize = 2
landscape_stone_D[0].position = [13.25, 9.579999923706055, 0.20000000298023224]
landscape_stone_D[0].rotation = [0, 0, 1.5802211042556205]
landscape_stone_D[0].optimize = 2
chair_E[0].position = [3.0, 0.6800000071525574, 0.41999998688697815]
chair_E[0].rotation = [0, 0, 1.5802211042556205]
chair_E[0].optimize = 2
plant_T[0].position = [6.21999979019165, 3.5999999046325684, 0.6499999761581421]
plant_T[0].rotation = [0, 0, 0.1839577022555754]
plant_T[0].optimize = 2
plant_group_2_H[0].position = [13.699999809265137, 5.920000076293945, 0.800000011920929]
plant_group_2_H[0].rotation = [0, 0, 0.35849063180849555]
plant_group_2_H[0].optimize = 2
fruit_O[0].position = [11.119999885559082, 1.1200000047683716, 0.7850000262260437]
fruit_O[0].rotation = [0, 0, 0.05340707759649543]
fruit_O[0].optimize = 2
flowerpot_B[0].position = [5.949999809265137, 1.850000023841858, 0.9399999976158142]
flowerpot_B[0].rotation = [0, 0, 0.2279400213940979]
flowerpot_B[0].optimize = 2
side_table_I[0].position = [2.8240280151367188, 9.475224494934082, 0.25]
side_table_I[0].rotation = [0, 0, 0.021991148286022624]
side_table_I[0].optimize = 2
plant_Y[0].position = [13.550000190734863, 8.619999885559082, 0.9199999570846558]
plant_Y[0].rotation = [0, 0, -0.06527530320178636]
plant_Y[0].optimize = 2
plant_group_2_F[0].position = [10.720000267028809, 8.720000267028809, 0.9449999928474426]
plant_group_2_F[0].rotation = [0, 0, -0.15254176314572285]
plant_group_2_F[0].optimize = 2
fruit_N[0].position = [8.75, 2.359999895095825, 0.7850000262260437]
fruit_N[0].rotation = [0, 0, 0.05340707759649543]
fruit_N[0].optimize = 2
cup_A[0].position = [3.0, 1.4800000190734863, 0.8050000071525574]
cup_A[0].rotation = [0, 0, 0.04712388718302966]
cup_A[0].optimize = 2
landscape_stone_A[0].position = [2.049999952316284, 3.6500000953674316, 0.20999999344348907]
landscape_stone_A[0].rotation = [0, 0, 0.35849063180849555]
landscape_stone_A[0].optimize = 2
chair_I[0].position = [6.78000020980835, 2.4000000953674316, 0.4350000023841858]
chair_I[0].rotation = [0, 0, -3.1321678761290697]
chair_I[0].optimize = 2
multi_person_sofa_C[0].position = [9.100000381469727, 4.820000171661377, 0.4000000059604645]
multi_person_sofa_C[0].rotation = [0, 0, 1.5802211042556205]
multi_person_sofa_C[0].optimize = 2
fruit_M[0].position = [9.0, 2.190000057220459, 0.7800000309944153]
fruit_M[0].rotation = [0, 0, 0.2279400213940979]
fruit_M[0].optimize = 2
plant_group_2_B[0].position = [2.8059725761413574, 9.550000190734863, 1.024999976158142]
plant_group_2_B[0].rotation = [0, 0, 0.19652402574277117]
plant_group_2_B[0].optimize = 2
plant_C[0].position = [3.049999952316284, 9.720000267028809, 0.8500000238418579]
plant_C[0].rotation = [0, 0, -0.3396410672987018]
plant_C[0].optimize = 2
chair_Y[0].position = [7.820000171661377, 7.71999979019165, 0.42500001192092896]
chair_Y[0].rotation = [0, 0, 1.5802211042556205]
chair_Y[0].optimize = 2
chair_O[0].position = [9.579999923706055, 2.4000000953674316, 0.42500001192092896]
chair_O[0].rotation = [0, 0, -3.1321678761290697]
chair_O[0].optimize = 2
plant_W[0].position = [9.649999618530273, 3.619999885559082, 0.6000000238418579]
plant_W[0].rotation = [0, 0, 0.27122416455253917]
plant_W[0].optimize = 2
billboard[0].position = [11.920000076293945, 10.102483749389648, 0.675000011920929]
billboard[0].rotation = [0, 0, -1.5707963581520448]
billboard[0].optimize = 2
cup_B[0].position = [5.949999809265137, 1.399999976158142, 0.8100000023841858]
cup_B[0].rotation = [0, 0, 0.05340707759649543]
cup_B[0].optimize = 2
high_chair_B[0].position = [6.980000019073486, 0.6399999856948853, 0.5]
high_chair_B[0].rotation = [0, 0, 1.5802211042556205]
high_chair_B[0].optimize = 2
cup_C[0].position = [11.350000381469727, 1.0399999618530273, 0.8100000023841858]
cup_C[0].rotation = [0, 0, 0.05340707759649543]
cup_C[0].optimize = 2
floor_lamp_A[0].position = [1.7200000286102295, 4.71999979019165, 0.824999988079071]
floor_lamp_A[0].rotation = [0, 0, 0.00942477746072377]
floor_lamp_A[0].optimize = 2
chair_G[0].position = [6.78000020980835, 1.2799999713897705, 0.41499999165534973]
chair_G[0].rotation = [0, 0, -3.1321678761290697]
chair_G[0].optimize = 2
multi_person_sofa_A[0].position = [3.299999952316284, 4.820000171661377, 0.4099999964237213]
multi_person_sofa_A[0].rotation = [0, 0, 1.5802211042556205]
multi_person_sofa_A[0].optimize = 2
fruit_W[0].position = [1.8300000429153442, 5.53000020980835, 0.5350000262260437]
fruit_W[0].rotation = [0, 0, 0.021991145012924443]
fruit_W[0].optimize = 2
chair_S[0].position = [12.180000305175781, 1.0199999809265137, 0.42500001192092896]
chair_S[0].rotation = [0, 0, -3.1321678761290697]
chair_S[0].optimize = 2
fruit_V[0].position = [10.350000381469727, 5.559999942779541, 0.5249999761581421]
fruit_V[0].rotation = [0, 0, -0.15254176314572285]
fruit_V[0].optimize = 2
plant_group_2_A[0].position = [2.8513128757476807, 9.502510070800781, 0.925000011920929]
plant_group_2_A[0].rotation = [0, 0, -0.16510813918712253]
plant_group_2_A[0].optimize = 2
plant_N[0].position = [4.78000020980835, 7.579999923706055, 1.0499999523162842]
plant_N[0].rotation = [0, 0, 0.19652402574277117]
plant_N[0].optimize = 2
plant_group_2_J[0].position = [1.589559555053711, 5.858592987060547, 2.174999952316284]
plant_group_2_J[0].rotation = [0, 0, 4.102479316927234e-08]
plant_group_2_J[0].optimize = 2
wine[0].position = [13.760000228881836, 1.9500000476837158, 1.1999999284744263]
wine[0].rotation = [0, 0, 3.0626248982231785]
wine[0].optimize = 2
plant_group_2_C[0].position = [7.119999885559082, 9.680000305175781, 0.7749999761581421]
plant_group_2_C[0].rotation = [0, 0, 0.27122416455253917]
plant_group_2_C[0].optimize = 2
dining_plate[0].position = [8.75, 1.4700000286102295, 0.7549999952316284]
dining_plate[0].rotation = [0, 0, 0.05340707759649543]
dining_plate[0].optimize = 2
chair_H[0].position = [5.119999885559082, 2.4000000953674316, 0.42500001192092896]
chair_H[0].rotation = [0, 0, 0.00942477746072377]
chair_H[0].optimize = 2
plant_D[0].position = [4.679999828338623, 5.71999979019165, 0.8949999809265137]
plant_D[0].rotation = [0, 0, 0.021991145012924443]
plant_D[0].optimize = 2
chair_J[0].position = [5.949999809265137, 0.6700000166893005, 0.41999998688697815]
chair_J[0].rotation = [0, 0, 1.5802211042556205]
chair_J[0].optimize = 2
multi_person_sofa_E[0].position = [6.199999809265137, 6.619999885559082, 0.4050000011920929]
multi_person_sofa_E[0].rotation = [0, 0, -1.5613715493341729]
multi_person_sofa_E[0].optimize = 2
plant_group_2_G[0].position = [12.880000114440918, 7.699999809265137, 0.75]
plant_group_2_G[0].rotation = [0, 0, -0.16510813918712253]
plant_group_2_G[0].optimize = 2
chair_F[0].position = [5.119999885559082, 1.2799999713897705, 0.4300000071525574]
chair_F[0].rotation = [0, 0, 0.00942477746072377]
chair_F[0].optimize = 2
shelf[0].position = [1.429613471031189, 5.860000133514404, 0.8999999761581421]
shelf[0].rotation = [0, 0, 3.2425853305976026e-08]
shelf[0].optimize = 2
plant_U[0].position = [9.920000076293945, 7.579999923706055, 0.949999988079071]
plant_U[0].rotation = [0, 0, 0.10925761255905678]
plant_U[0].optimize = 2
chair_A[0].position = [2.180000066757202, 1.2999999523162842, 0.41999998688697815]
chair_A[0].rotation = [0, 0, 0.00942477746072377]
chair_A[0].optimize = 2
multi_person_sofa_G[0].position = [12.350000381469727, 6.619999885559082, 0.41999998688697815]
multi_person_sofa_G[0].rotation = [0, 0, -3.1321678761290697]
multi_person_sofa_G[0].optimize = 2
plant_B[0].position = [2.0199999809265137, 6.71999979019165, 0.574999988079071]
plant_B[0].rotation = [0, 0, 0.27122416455253917]
plant_B[0].optimize = 2
plant_A[0].position = [2.049999952316284, 4.420000076293945, 0.7749999761581421]
plant_A[0].rotation = [0, 0, 0.00942477746072377]
plant_A[0].optimize = 2
fruit_Q[0].position = [11.100000381469727, 1.7899999618530273, 0.7900000214576721]
fruit_Q[0].rotation = [0, 0, -0.20839231804389766]
fruit_Q[0].optimize = 2
stool[0].position = [11.550000190734863, 5.420000076293945, 0.23000000417232513]
stool[0].rotation = [0, 0, -3.1321678761290697]
stool[0].optimize = 2
fruit_group_2_F[0].position = [13.760000228881836, 1.7000000476837158, 1.09499990940094]
fruit_group_2_F[0].rotation = [0, 0, -2.961494724142301]
fruit_group_2_F[0].optimize = 2
plant_group_2_E[0].position = [11.420000076293945, 5.619999885559082, 0.8500000238418579]
plant_group_2_E[0].rotation = [0, 0, 0.1839577022555754]
plant_group_2_E[0].optimize = 2
chair_Q[0].position = [8.75, 3.0199999809265137, 0.4300000071525574]
chair_Q[0].rotation = [0, 0, -1.5613715493341729]
chair_Q[0].optimize = 2
fruit_U[0].position = [7.840000152587891, 5.570000171661377, 0.5400000214576721]
fruit_U[0].rotation = [0, 0, 0.19652402574277117]
fruit_U[0].optimize = 2
multi_person_sofa_H[0].position = [4.349999904632568, 8.720000267028809, 0.4099999964237213]
multi_person_sofa_H[0].rotation = [0, 0, -1.5613715493341729]
multi_person_sofa_H[0].optimize = 2
plant_P[0].position = [1.7000000476837158, 6.050000190734863, 0.8999999761581421]
plant_P[0].rotation = [0, 0, 0.00942477746072377]
plant_P[0].optimize = 2
floor_lamp_C[0].position = [10.180000305175781, 9.699999809265137, 0.8399999737739563]
floor_lamp_C[0].rotation = [0, 0, -1.5613715493341729]
floor_lamp_C[0].optimize = 2
chair_U[0].position = [12.180000305175781, 1.8799999952316284, 0.4300000071525574]
chair_U[0].rotation = [0, 0, -3.1321678761290697]
chair_U[0].optimize = 2
fruit_X[0].position = [4.579999923706055, 7.429999828338623, 0.5450000166893005]
fruit_X[0].rotation = [0, 0, 0.2837905265402015]
fruit_X[0].optimize = 2
wall_lamp[0].position = [14.100000381469727, 5.050000190734863, 0.20999999344348907]
wall_lamp[0].rotation = [0, 0, -3.141592611426633]
wall_lamp[0].optimize = 2
plant_G[0].position = [7.449999809265137, 3.549999952316284, 0.625]
plant_G[0].rotation = [0, 0, 0.35849063180849555]
plant_G[0].optimize = 2
fruit_K[0].position = [8.979999542236328, 1.4800000190734863, 0.7750000357627869]
fruit_K[0].rotation = [0, 0, 0.31520646490854193]
fruit_K[0].optimize = 2
chair_group_2_B[0].position = [6.050000190734863, 8.720000267028809, 0.41999998688697815]
chair_group_2_B[0].rotation = [0, 0, 0.00942477746072377]
chair_group_2_B[0].optimize = 2
chair_R[0].position = [10.520000457763672, 1.0199999809265137, 0.41499999165534973]
chair_R[0].rotation = [0, 0, 0.00942477746072377]
chair_R[0].optimize = 2
floor_lamp_B[0].position = [5.71999979019165, 9.699999809265137, 0.8500000238418579]
floor_lamp_B[0].rotation = [0, 0, -1.5613715493341729]
floor_lamp_B[0].optimize = 2
side_table_K[0].position = [13.520000457763672, 5.179999828338623, 0.25]
side_table_K[0].rotation = [0, 0, 0.021991148286022624]
side_table_K[0].optimize = 2
chair_Z[0].position = [8.779999732971191, 7.71999979019165, 0.41499999165534973]
chair_Z[0].rotation = [0, 0, 1.5802211042556205]
chair_Z[0].optimize = 2
fruit_group_2_C[0].position = [10.520000457763672, 8.569999694824219, 0.5600000023841858]
fruit_group_2_C[0].rotation = [0, 0, -0.15254176314572285]
fruit_group_2_C[0].optimize = 2
plant_X[0].position = [13.550000190734863, 4.619999885559082, 0.7250000238418579]
plant_X[0].rotation = [0, 0, 0.00942477746072377]
plant_X[0].optimize = 2
multi_person_sofa_I[0].position = [8.050000190734863, 8.720000267028809, 0.41499999165534973]
multi_person_sofa_I[0].rotation = [0, 0, -1.5613715493341729]
multi_person_sofa_I[0].optimize = 2
high_chair_C[0].position = [9.779999732971191, 0.6399999856948853, 0.5149999856948853]
high_chair_C[0].rotation = [0, 0, 1.5802211042556205]
high_chair_C[0].optimize = 2
chair_V[0].position = [11.350000381469727, 2.700000047683716, 0.41499999165534973]
chair_V[0].rotation = [0, 0, -1.5613715493341729]
chair_V[0].optimize = 2
plant_H[0].position = [7.650000095367432, 5.71999979019165, 0.925000011920929]
plant_H[0].rotation = [0, 0, 0.2837905265402015]
plant_H[0].optimize = 2
chair_M[0].position = [9.579999923706055, 1.2799999713897705, 0.41999998688697815]
chair_M[0].rotation = [0, 0, -3.1321678761290697]
chair_M[0].optimize = 2
multi_person_sofa_B[0].position = [6.199999809265137, 4.820000171661377, 0.41999998688697815]
multi_person_sofa_B[0].rotation = [0, 0, 1.5802211042556205]
multi_person_sofa_B[0].optimize = 2
fruit_C[0].position = [2.7799999713897705, 2.140000104904175, 0.7850000262260437]
fruit_C[0].rotation = [0, 0, -0.21467550218211454]
fruit_C[0].optimize = 2
table_D[0].position = [11.350000381469727, 1.4500000476837158, 0.375]
table_D[0].rotation = [0, 0, 0.053407073383009665]
table_D[0].optimize = 2
plant_O[0].position = [13.619999885559082, 9.649999618530273, 0.75]
plant_O[0].rotation = [0, 0, 0.1839577022555754]
plant_O[0].optimize = 2
plant_Q[0].position = [6.849999904632568, 7.579999923706055, 0.9199999570846558]
plant_Q[0].rotation = [0, 0, -0.15254176314572285]
plant_Q[0].optimize = 2
jar[0].position = [13.760000228881836, 0.7200000286102295, 1.1899999380111694]
jar[0].rotation = [0, 0, 3.0626248982231785]
jar[0].optimize = 2
chair_B[0].position = [3.819999933242798, 1.2999999523162842, 0.4300000071525574]
chair_B[0].rotation = [0, 0, -3.1321678761290697]
chair_B[0].optimize = 2
fruit_F[0].position = [6.179999828338623, 1.4800000190734863, 0.7950000166893005]
fruit_F[0].rotation = [0, 0, 0.40247287671616416]
fruit_F[0].optimize = 2
landscape_stone_B[0].position = [4.050000190734863, 3.7200000286102295, 0.17499999701976776]
landscape_stone_B[0].rotation = [0, 0, -0.2523746056580361]
landscape_stone_B[0].optimize = 2
fruit_G[0].position = [5.699999809265137, 2.200000047683716, 0.7850000262260437]
fruit_G[0].rotation = [0, 0, -0.20839231804389766]
fruit_G[0].optimize = 2
plant_group_2_D[0].position = [10.720000267028809, 4.880000114440918, 0.625]
plant_group_2_D[0].rotation = [0, 0, -0.2523746056580361]
plant_group_2_D[0].optimize = 2
fruit_I[0].position = [5.949999809265137, 2.3499999046325684, 0.7900000214576721]
fruit_I[0].rotation = [0, 0, 0.05340707759649543]
fruit_I[0].optimize = 2
plant_V[0].position = [8.420000076293945, 3.619999885559082, 0.824999988079071]
plant_V[0].rotation = [0, 0, -0.2523746056580361]
plant_V[0].optimize = 2
chair_T[0].position = [10.520000457763672, 1.8799999952316284, 0.41999998688697815]
chair_T[0].rotation = [0, 0, 0.00942477746072377]
chair_T[0].optimize = 2
fruit_D[0].position = [3.2200000286102295, 2.140000104904175, 0.800000011920929]
fruit_D[0].rotation = [0, 0, 0.22165682199215]
fruit_D[0].optimize = 2
plant_S[0].position = [4.75, 3.619999885559082, 0.7749999761581421]
plant_S[0].rotation = [0, 0, -0.16510813918712253]
plant_S[0].optimize = 2
table_A[0].position = [3.0, 1.850000023841858, 0.375]
table_A[0].rotation = [0, 0, 0.04712389191905141]
table_A[0].optimize = 2
side_table_H[0].position = [13.550000190734863, 8.619999885559082, 0.25999999046325684]
side_table_H[0].rotation = [0, 0, 0.021991148286022624]
side_table_H[0].optimize = 2
side_table_E[0].position = [4.78000020980835, 7.579999923706055, 0.25]
side_table_E[0].rotation = [0, 0, 0.021991148286022624]
side_table_E[0].optimize = 2
chair_C[0].position = [2.180000066757202, 2.380000114440918, 0.41499999165534973]
chair_C[0].rotation = [0, 0, 0.00942477746072377]
chair_C[0].optimize = 2
fruit_A[0].position = [2.7799999713897705, 1.5499999523162842, 0.7900000214576721]
fruit_A[0].rotation = [0, 0, 0.04712388718302966]
fruit_A[0].optimize = 2
plant_K[0].position = [10.850000381469727, 9.680000305175781, 0.699999988079071]
plant_K[0].rotation = [0, 0, 0.27122416455253917]
plant_K[0].optimize = 2
chair_W[0].position = [3.25, 7.71999979019165, 0.4300000071525574]
chair_W[0].rotation = [0, 0, 1.5802211042556205]
chair_W[0].optimize = 2
side_table_F[0].position = [6.849999904632568, 7.579999923706055, 0.25999999046325684]
side_table_F[0].rotation = [0, 0, 0.021991148286022624]
side_table_F[0].optimize = 2
chair_P[0].position = [8.75, 0.6700000166893005, 0.41999998688697815]
chair_P[0].rotation = [0, 0, 1.5802211042556205]
chair_P[0].optimize = 2
fruit_P[0].position = [11.579999923706055, 1.1200000047683716, 0.7950000166893005]
fruit_P[0].rotation = [0, 0, 0.40247287671616416]
fruit_P[0].optimize = 2
high_chair_A[0].position = [4.179999828338623, 0.6499999761581421, 0.5099999904632568]
high_chair_A[0].rotation = [0, 0, 1.5802211042556205]
high_chair_A[0].optimize = 2
fruit_L[0].position = [8.5, 2.190000057220459, 0.7850000262260437]
fruit_L[0].rotation = [0, 0, -0.20839231804389766]
fruit_L[0].optimize = 2
flowerpot_A[0].position = [3.0, 1.850000023841858, 0.925000011920929]
flowerpot_A[0].rotation = [0, 0, 0.04712388718302966]
flowerpot_A[0].optimize = 2
plant_F[0].position = [6.550000190734863, 9.699999809265137, 0.949999988079071]
plant_F[0].rotation = [0, 0, -0.16510813918712253]
plant_F[0].optimize = 2
fruit_group_2_A[0].position = [13.369999885559082, 8.470000267028809, 0.5550000071525574]
fruit_group_2_A[0].rotation = [0, 0, 0.021991145012924443]
fruit_group_2_A[0].optimize = 2
plant_E[0].position = [4.650000095367432, 9.720000267028809, 0.675000011920929]
plant_E[0].rotation = [0, 0, 0.1839577022555754]
plant_E[0].optimize = 2
side_table_G[0].position = [9.920000076293945, 7.579999923706055, 0.25]
side_table_G[0].rotation = [0, 0, 0.021991148286022624]
side_table_G[0].optimize = 2
chair_group_2_C[0].position = [9.720000267028809, 8.720000267028809, 0.4300000071525574]
chair_group_2_C[0].rotation = [0, 0, -3.1321678761290697]
chair_group_2_C[0].optimize = 2
side_table_B[0].position = [7.650000095367432, 5.71999979019165, 0.25]
side_table_B[0].rotation = [0, 0, 0.021991148286022624]
side_table_B[0].optimize = 2
fruit_R[0].position = [11.600000381469727, 1.7899999618530273, 0.7950000166893005]
fruit_R[0].rotation = [0, 0, 0.2279400213940979]
fruit_R[0].optimize = 2
fruit_Y[0].position = [7.039999961853027, 7.429999828338623, 0.5600000023841858]
fruit_Y[0].rotation = [0, 0, -0.23980825685194154]
fruit_Y[0].optimize = 2
fruit_E[0].position = [5.71999979019165, 1.4800000190734863, 0.7900000214576721]
fruit_E[0].rotation = [0, 0, 0.05340707759649543]
fruit_E[0].optimize = 2
plant_I[0].position = [9.050000190734863, 9.680000305175781, 0.800000011920929]
plant_I[0].rotation = [0, 0, -0.2523746056580361]
plant_I[0].optimize = 2
side_table_D[0].position = [2.0, 5.679999828338623, 0.25]
side_table_D[0].rotation = [0, 0, 0.021991148286022624]
side_table_D[0].optimize = 2
chair_group_2_D[0].position = [11.449999809265137, 8.050000190734863, 0.41999998688697815]
chair_group_2_D[0].rotation = [0, 0, -1.5613715493341729]
chair_group_2_D[0].optimize = 2
chair_N[0].position = [7.920000076293945, 2.4000000953674316, 0.41499999165534973]
chair_N[0].rotation = [0, 0, 0.00942477746072377]
chair_N[0].optimize = 2
chair_D[0].position = [3.819999933242798, 2.380000114440918, 0.42500001192092896]
chair_D[0].rotation = [0, 0, -3.1321678761290697]
chair_D[0].optimize = 2
table_B[0].position = [5.949999809265137, 1.850000023841858, 0.375]
table_B[0].rotation = [0, 0, 0.053407073383009665]
table_B[0].optimize = 2
plant_group_2_I[0].position = [13.520000457763672, 5.179999828338623, 1.0499999523162842]
plant_group_2_I[0].rotation = [0, 0, 0.2837905265402015]
plant_group_2_I[0].optimize = 2
chair_K[0].position = [5.949999809265137, 3.0199999809265137, 0.42500001192092896]
chair_K[0].rotation = [0, 0, -1.5613715493341729]
chair_K[0].optimize = 2
plant_J[0].position = [10.550000190734863, 5.71999979019165, 0.9549999833106995]
plant_J[0].rotation = [0, 0, -0.15254176314572285]
plant_J[0].optimize = 2
chair_group_2_A[0].position = [2.549999952316284, 8.550000190734863, 0.42500001192092896]
chair_group_2_A[0].rotation = [0, 0, 0.00942477746072377]
chair_group_2_A[0].optimize = 2
fruit_H[0].position = [6.199999809265137, 2.200000047683716, 0.7950000166893005]
fruit_H[0].rotation = [0, 0, 0.2279400213940979]
fruit_H[0].optimize = 2
multi_person_sofa_F[0].position = [9.100000381469727, 6.619999885559082, 0.42500001192092896]
multi_person_sofa_F[0].rotation = [0, 0, -1.5613715493341729]
multi_person_sofa_F[0].optimize = 2
plant_L[0].position = [2.0, 5.679999828338623, 0.824999988079071]
plant_L[0].rotation = [0, 0, 0.021991145012924443]
plant_L[0].optimize = 2
plant_R[0].position = [1.7200000286102295, 7.050000190734863, 0.6000000238418579]
plant_R[0].rotation = [0, 0, 0.27122416455253917]
plant_R[0].optimize = 2
fruit_group_2_D[0].position = [13.319999694824219, 5.03000020980835, 0.5450000166893005]
fruit_group_2_D[0].rotation = [0, 0, 0.19652402574277117]
fruit_group_2_D[0].optimize = 2
flowerpot_E[0].position = [13.779999732971191, 1.0499999523162842, 1.2400000095367432]
flowerpot_E[0].rotation = [0, 0, 3.0626248982231785]
flowerpot_E[0].optimize = 2
fruit_Z[0].position = [9.720000267028809, 7.429999828338623, 0.5450000166893005]
fruit_Z[0].rotation = [0, 0, 0.19652402574277117]
fruit_Z[0].optimize = 2
water_bar[0].position = [13.789410591125488, 1.2180265188217163, 0.5249999761581421]
water_bar[0].rotation = [0, 0, 3.0844639801503044]
water_bar[0].optimize = 2
plant_M[0].position = [12.149999618530273, 9.600000381469727, 0.875]
plant_M[0].rotation = [0, 0, -0.3396410672987018]
plant_M[0].optimize = 2
fruit_group_2_E[0].position = [13.760000228881836, 1.4199999570846558, 1.084999918937683]
fruit_group_2_E[0].rotation = [0, 0, 3.0626248982231785]
fruit_group_2_E[0].optimize = 2
fruit_group_2_B[0].position = [2.606078863143921, 9.390000343322754, 0.5450000166893005]
fruit_group_2_B[0].rotation = [0, 0, 0.2837905265402015]
fruit_group_2_B[0].optimize = 2
flowerpot_D[0].position = [11.350000381469727, 1.4500000476837158, 0.949999988079071]
flowerpot_D[0].rotation = [0, 0, 0.05340707759649543]
flowerpot_D[0].optimize = 2
fruit_S[0].position = [11.350000381469727, 2.0299999713897705, 0.7850000262260437]
fruit_S[0].rotation = [0, 0, 0.05340707759649543]
fruit_S[0].optimize = 2
landscape_stone_C[0].position = [12.819999694824219, 5.119999885559082, 0.23000000417232513]
landscape_stone_C[0].rotation = [0, 0, 1.3184217211368605]
landscape_stone_C[0].optimize = 2
multi_person_sofa_D[0].position = [3.299999952316284, 6.619999885559082, 0.41499999165534973]
multi_person_sofa_D[0].rotation = [0, 0, -1.5613715493341729]
multi_person_sofa_D[0].optimize = 2
side_table_A[0].position = [4.679999828338623, 5.71999979019165, 0.25999999046325684]
side_table_A[0].rotation = [0, 0, 0.021991148286022624]
side_table_A[0].optimize = 2
chair_X[0].position = [5.71999979019165, 7.71999979019165, 0.41999998688697815]
chair_X[0].rotation = [0, 0, 1.5802211042556205]
chair_X[0].optimize = 2
side_table_C[0].position = [10.550000190734863, 5.71999979019165, 0.23999999463558197]
side_table_C[0].rotation = [0, 0, 0.021991148286022624]
side_table_C[0].optimize = 2
high_chair_E[0].position = [10.25, 2.7799999713897705, 0.5099999904632568]
high_chair_E[0].rotation = [0, 0, -0.7759733982318487]
high_chair_E[0].optimize = 2
chair_group_2_E[0].position = [12.5, 8.079999923706055, 0.42500001192092896]
chair_group_2_E[0].rotation = [0, 0, -1.5613715493341729]
chair_group_2_E[0].optimize = 2
fruit_J[0].position = [8.520000457763672, 1.4800000190734863, 0.7850000262260437]
fruit_J[0].rotation = [0, 0, 0.05340707759649543]
fruit_J[0].optimize = 2
chair_L[0].position = [7.920000076293945, 1.2799999713897705, 0.4300000071525574]
chair_L[0].rotation = [0, 0, 0.00942477746072377]
chair_L[0].optimize = 2

