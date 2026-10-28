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
    Wall(corner1=[4.00, 0.00, 0.00], corner2=[4.00, 5.00, 0.00]),
    Wall(corner1=[4.00, 5.00, 0.00], corner2=[0.00, 5.00, 0.00]),
    Wall(corner1=[0.00, 5.00, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
kitchen_cabinet_lower_A = Assets(description="long base kitchen cabinet with drawers and closed storage, white finish", size=[0.60, 1.80, 0.90], placements=[AssetInstance() for _ in range(1)])
rolling_kitchen_cart = Assets(description="mobile kitchen cart with stainless steel top and wooden shelves", size=[0.45, 0.75, 0.90], placements=[AssetInstance() for _ in range(1)])
oven_and_stove_unit_A = Assets(description="built-in oven with 5-burner stove top, stainless steel", size=[0.65, 0.90, 0.90], placements=[AssetInstance() for _ in range(1)])
kitchen_cabinet_lower_B = Assets(description="long base kitchen cabinet with drawers and closed storage, white finish", size=[0.60, 1.60, 0.90], placements=[AssetInstance() for _ in range(1)])
oven_and_stove_unit_B = Assets(description="built-in oven with 5-burner stove top, stainless steel", size=[0.65, 0.90, 0.90], placements=[AssetInstance() for _ in range(1)])
freestanding_pantry_cabinet = Assets(description="tall freestanding pantry cabinet with multiple shelves, natural wood finish", size=[0.45, 0.90, 2.00], placements=[AssetInstance() for _ in range(1)])

kitchen_cabinet_lower_A[0].instance_id = 'kitchen_cabinet_lower_A_0'
rolling_kitchen_cart[0].instance_id = 'rolling_kitchen_cart_0'
oven_and_stove_unit_A[0].instance_id = 'oven_and_stove_unit_A_0'
kitchen_cabinet_lower_B[0].instance_id = 'kitchen_cabinet_lower_B_0'
oven_and_stove_unit_B[0].instance_id = 'oven_and_stove_unit_B_0'
freestanding_pantry_cabinet[0].instance_id = 'freestanding_pantry_cabinet_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

kitchen_cabinet_lower_A[0].position = [1.733890963412117, 3.189910011867376, 0.45]
kitchen_cabinet_lower_A[0].rotation = [0, 0, 0]
rolling_kitchen_cart[0].position = [3.199677083408552, 4.653952446534003, 0.45]
rolling_kitchen_cart[0].rotation = [0, 0, 0]
oven_and_stove_unit_A[0].position = [1.8347431464111086, 3.6425611994485547, 0.45]
oven_and_stove_unit_A[0].rotation = [0, 0, 0]
kitchen_cabinet_lower_B[0].position = [0.575661985638225, 4.786501879191266, 0.45]
kitchen_cabinet_lower_B[0].rotation = [0, 0, 0]
oven_and_stove_unit_B[0].position = [0.9946980738611799, 4.003716830960231, 0.45]
oven_and_stove_unit_B[0].rotation = [0, 0, 0]
freestanding_pantry_cabinet[0].position = [2.5717568499395904, 1.8478783414619988, 1.0]
freestanding_pantry_cabinet[0].rotation = [0, 0, 0]
kitchen_cabinet_lower_A[0].position = [1.733890963412117, 3.189910011867376, 0.45]
kitchen_cabinet_lower_A[0].rotation = [0, 0, 0]
rolling_kitchen_cart[0].position = [3.199677083408552, 4.653952446534003, 0.45]
rolling_kitchen_cart[0].rotation = [0, 0, 0]
oven_and_stove_unit_A[0].position = [1.8347431464111086, 3.6425611994485547, 0.45]
oven_and_stove_unit_A[0].rotation = [0, 0, 0]
kitchen_cabinet_lower_B[0].position = [0.575661985638225, 4.786501879191266, 0.45]
kitchen_cabinet_lower_B[0].rotation = [0, 0, 0]
oven_and_stove_unit_B[0].position = [0.9946980738611799, 4.003716830960231, 0.45]
oven_and_stove_unit_B[0].rotation = [0, 0, 0]
freestanding_pantry_cabinet[0].position = [2.5717568499395904, 1.8478783414619988, 1.0]
freestanding_pantry_cabinet[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the appliances as three wall runs, leaving the middle of the room
# open for circulation. All z coordinates place the assets on the floor.
kitchen_cabinet_lower_A.placements = [
    AssetInstance(position=[2.00, 4.70, 0.45], rotation=[0, 0, radians(-90)])
]
rolling_kitchen_cart.placements = [
    AssetInstance(position=[3.775, 3.225, 0.45], rotation=[0, 0, radians(180)])
]
oven_and_stove_unit_A.placements = [
    AssetInstance(position=[0.325, 2.25, 0.45], rotation=[0, 0, radians(0)])
]
kitchen_cabinet_lower_B.placements = [
    AssetInstance(position=[0.30, 1.00, 0.45], rotation=[0, 0, radians(0)])
]
oven_and_stove_unit_B.placements = [
    AssetInstance(position=[3.675, 0.65, 0.45], rotation=[0, 0, radians(180)])
]
freestanding_pantry_cabinet.placements = [
    AssetInstance(position=[3.775, 4.25, 1.00], rotation=[0, 0, radians(180)])
]

room_center = AssetInstance(position=[2.00, 2.50, 0.45])

# Position constraints keep every unit on its intended wall.
solver.against_wall(kitchen_cabinet_lower_A[0], walls[1])
solver.against_wall(rolling_kitchen_cart[0], walls[0])
solver.against_wall(oven_and_stove_unit_A[0], walls[2])
solver.against_wall(kitchen_cabinet_lower_B[0], walls[2])
solver.against_wall(oven_and_stove_unit_B[0], walls[0])
solver.against_wall(freestanding_pantry_cabinet[0], walls[0])

# The pantry and cart are adjacent along the right wall. Their combined
# half-width is 0.825 m, so these center-distance bounds represent a
# non-overlapping surface gap between 0 and 0.30 m.
solver.distance_constraint(
    freestanding_pantry_cabinet[0],
    rolling_kitchen_cart[0],
    0.825,
    1.125,
    weight=10,
)

# Cabinet B and oven A are adjacent along the left wall. Their combined
# half-width is 1.25 m, so the upper bound allows at most a 0.10 m gap.
solver.distance_constraint(
    kitchen_cabinet_lower_B[0],
    oven_and_stove_unit_A[0],
    1.25,
    1.35,
    weight=10,
)

# Orient all fronts toward the room interior.
solver.point_towards(kitchen_cabinet_lower_A[0], room_center)
solver.point_towards(rolling_kitchen_cart[0], room_center)
solver.point_towards(oven_and_stove_unit_A[0], room_center)
solver.point_towards(kitchen_cabinet_lower_B[0], room_center)
solver.point_towards(oven_and_stove_unit_B[0], room_center)
solver.point_towards(freestanding_pantry_cabinet[0], room_center)

# Preserve parallel orientation within each adjoining wall run.
solver.align_with(kitchen_cabinet_lower_B[0], oven_and_stove_unit_A[0])
solver.align_with(oven_and_stove_unit_A[0], kitchen_cabinet_lower_B[0])
solver.align_with(freestanding_pantry_cabinet[0], rolling_kitchen_cart[0])
solver.align_with(rolling_kitchen_cart[0], freestanding_pantry_cabinet[0])

solver.constraints = []
kitchen_cabinet_lower_B[0].position = [0.30000007152557373, 1.0, 0.44999998807907104]
kitchen_cabinet_lower_B[0].rotation = [0, 0, 3.414197935437419e-08]
kitchen_cabinet_lower_B[0].optimize = 2
rolling_kitchen_cart[0].position = [3.77500057220459, 3.2249999046325684, 0.44999998807907104]
rolling_kitchen_cart[0].rotation = [0, 0, -3.1415926098806413]
rolling_kitchen_cart[0].optimize = 2
oven_and_stove_unit_B[0].position = [3.674999713897705, 0.6499999761581421, 0.44999998807907104]
oven_and_stove_unit_B[0].rotation = [0, 0, -3.1415926098996385]
oven_and_stove_unit_B[0].optimize = 2
kitchen_cabinet_lower_A[0].position = [2.0, 4.6999993324279785, 0.44999998807907104]
kitchen_cabinet_lower_A[0].rotation = [0, 0, -1.5707963536783087]
kitchen_cabinet_lower_A[0].optimize = 2
oven_and_stove_unit_A[0].position = [0.32500001788139343, 2.25, 0.44999998807907104]
oven_and_stove_unit_A[0].rotation = [0, 0, 3.8346258017103806e-08]
oven_and_stove_unit_A[0].optimize = 2
freestanding_pantry_cabinet[0].position = [3.7750000953674316, 4.25, 1.0]
freestanding_pantry_cabinet[0].rotation = [0, 0, -3.1415926098968474]
freestanding_pantry_cabinet[0].optimize = 2

