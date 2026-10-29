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
    Wall(corner1=[5.00, 0.00, 0.00], corner2=[5.00, 4.00, 0.00]),
    Wall(corner1=[5.00, 4.00, 0.00], corner2=[0.00, 4.00, 0.00]),
    Wall(corner1=[0.00, 4.00, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[5.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
kitchen_island = Assets(description="extra-large central kitchen island with extended countertop for prep and casual dining", size=[1.10, 2.40, 0.92], placements=[AssetInstance() for _ in range(1)])
kitchen_cabinet_run = Assets(description="long kitchen cabinet set with extended countertop and built-in appliances", size=[0.65, 3.60, 0.92], placements=[AssetInstance() for _ in range(1)])
floor_pantry_cabinet = Assets(description="tall pantry cabinet for food and kitchen supply storage", size=[0.65, 0.60, 2.20], placements=[AssetInstance() for _ in range(1)])
breakfast_nook_table = Assets(description="compact round breakfast table for casual dining", size=[0.85, 0.85, 0.75], placements=[AssetInstance() for _ in range(1)])

kitchen_island[0].instance_id = 'kitchen_island_0'
kitchen_cabinet_run[0].instance_id = 'kitchen_cabinet_run_0'
floor_pantry_cabinet[0].instance_id = 'floor_pantry_cabinet_0'
breakfast_nook_table[0].instance_id = 'breakfast_nook_table_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

kitchen_island[0].position = [2.9278394441549644, 1.8982552421988164, 0.46]
kitchen_island[0].rotation = [0, 0, 0]
kitchen_cabinet_run[0].position = [4.120435323199667, 1.3762837166605424, 0.46]
kitchen_cabinet_run[0].rotation = [0, 0, 0]
floor_pantry_cabinet[0].position = [1.968560209366963, 3.049975799885396, 1.1]
floor_pantry_cabinet[0].rotation = [0, 0, 0]
breakfast_nook_table[0].position = [1.4817236396885525, 0.06630718920908452, 0.375]
breakfast_nook_table[0].rotation = [0, 0, 0]
kitchen_island[0].position = [2.9278394441549644, 1.8982552421988164, 0.46]
kitchen_island[0].rotation = [0, 0, 0]
kitchen_cabinet_run[0].position = [4.120435323199667, 1.3762837166605424, 0.46]
kitchen_cabinet_run[0].rotation = [0, 0, 0]
floor_pantry_cabinet[0].position = [1.968560209366963, 3.049975799885396, 1.1]
floor_pantry_cabinet[0].rotation = [0, 0, 0]
breakfast_nook_table[0].position = [1.4817236396885525, 0.06630718920908452, 0.375]
breakfast_nook_table[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the actual wall coordinates: the room spans x=0..5 and y=0..4.
# The cabinet run follows the north wall; the island follows the east wall.
# A pantry bridges their ends with 5 cm clear gaps, forming a compact L.
kitchen_cabinet_run[0].position = [1.80, 3.675, 0.46]
kitchen_cabinet_run[0].rotation = [0, 0, radians(-90)]

kitchen_island[0].position = [4.45, 2.15, 0.46]
kitchen_island[0].rotation = [0, 0, radians(180)]

# Facing west keeps pantry access away from the island immediately south.
floor_pantry_cabinet[0].position = [3.975, 3.70, 1.10]
floor_pantry_cabinet[0].rotation = [0, 0, radians(180)]

# Leave the southwest and central floor open for circulation and dining.
breakfast_nook_table[0].position = [1.45, 1.25, 0.375]
breakfast_nook_table[0].rotation = [0, 0, radians(0)]

# Wall contact and inward-facing orientations.
solver.against_wall(kitchen_cabinet_run[0], walls[1])
solver.align_with(
    kitchen_cabinet_run[0],
    AssetInstance(rotation=[0, 0, radians(-90)])
)
solver.against_wall(kitchen_island[0], walls[0])
solver.align_with(
    kitchen_island[0],
    AssetInstance(rotation=[0, 0, radians(180)])
)

# Preserve the chosen positions along the walls as well as the wall contact.
solver.distance_constraint(
    kitchen_cabinet_run[0],
    AssetInstance(position=[1.80, 3.675, 0.46]),
    0, 0, weight=10
)
solver.distance_constraint(
    kitchen_island[0],
    AssetInstance(position=[4.45, 2.15, 0.46]),
    0, 0, weight=10
)

solver.distance_constraint(
    floor_pantry_cabinet[0],
    AssetInstance(position=[3.975, 3.70, 1.10]),
    0, 0, weight=10
)
solver.align_with(floor_pantry_cabinet[0], kitchen_island[0])

# Distances refer to bounding-box centers, not edge clearances.
# At these anchored positions, the pantry has a 0.05 m surface gap
# from both the island and cabinet run, satisfying both proximity limits.
pantry_island_center_distance = (
    (3.975 - 4.45) ** 2
    + (3.70 - 2.15) ** 2
    + (1.10 - 0.46) ** 2
) ** 0.5
pantry_run_center_distance = (
    (3.975 - 1.80) ** 2
    + (3.70 - 3.675) ** 2
    + (1.10 - 0.46) ** 2
) ** 0.5

solver.distance_constraint(
    floor_pantry_cabinet[0], kitchen_island[0],
    pantry_island_center_distance, pantry_island_center_distance,
    weight=10
)
solver.distance_constraint(
    floor_pantry_cabinet[0], kitchen_cabinet_run[0],
    pantry_run_center_distance, pantry_run_center_distance,
    weight=10
)

# The table is floor-standing, so no on_top_of constraint is needed.
solver.distance_constraint(
    breakfast_nook_table[0],
    AssetInstance(position=[1.45, 1.25, 0.375]),
    0, 0, weight=10
)
solver.align_with(
    breakfast_nook_table[0],
    AssetInstance(rotation=[0, 0, 0])
)

# Additional separation safeguards for the dining area.
solver.distance_constraint(
    breakfast_nook_table[0], kitchen_island[0], 2.5, None
)
solver.distance_constraint(
    breakfast_nook_table[0], kitchen_cabinet_run[0], 2.0, None
)
solver.distance_constraint(
    breakfast_nook_table[0], floor_pantry_cabinet[0], 2.5, None
)

solver.constraints = []
kitchen_island[0].position = [4.449999809265137, 2.1500000953674316, 0.46000000834465027]
kitchen_island[0].rotation = [0, 0, -3.1415926098670948]
kitchen_island[0].optimize = 2
floor_pantry_cabinet[0].position = [4.118043899536133, 3.6999998092651367, 1.100000023841858]
floor_pantry_cabinet[0].rotation = [0, 0, -3.1415926101749703]
floor_pantry_cabinet[0].optimize = 2
kitchen_cabinet_run[0].position = [1.8580396175384521, 3.674999952316284, 0.46000000834465027]
kitchen_cabinet_run[0].rotation = [0, 0, -1.5707962892791512]
kitchen_cabinet_run[0].optimize = 2
breakfast_nook_table[0].position = [1.4500000476837158, 1.25, 0.375]
breakfast_nook_table[0].rotation = [0, 0, 0.01884955539881635]
breakfast_nook_table[0].optimize = 2

