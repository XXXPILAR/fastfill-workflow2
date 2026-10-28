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
    Wall(corner1=[0.00, 4.29, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.16, 0.00, 0.00]),
    Wall(corner1=[6.16, 0.00, 0.00], corner2=[6.16, 4.29, 0.00]),
    Wall(corner1=[6.16, 4.29, 0.00], corner2=[0.00, 4.29, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
plant_A = Assets(description="plant", size=[0.35, 0.35, 1.20], placements=[AssetInstance() for _ in range(1)])
tea_table_combination = Assets(description="tea table combination", size=[0.60, 1.20, 0.45], placements=[AssetInstance() for _ in range(1)])
landscape_stone = Assets(description="landscape stone", size=[0.20, 0.30, 0.15], placements=[AssetInstance() for _ in range(1)])
storage_rack = Assets(description="storage rack", size=[0.40, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
plant_B = Assets(description="plant", size=[0.40, 0.40, 1.00], placements=[AssetInstance() for _ in range(1)])

plant_A[0].instance_id = 'plant_A_0'
tea_table_combination[0].instance_id = 'tea_table_combination_0'
landscape_stone[0].instance_id = 'landscape_stone_0'
storage_rack[0].instance_id = 'storage_rack_0'
plant_B[0].instance_id = 'plant_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

plant_A[0].position = [4.188949844932052, 1.287095891376618, 0.6]
plant_A[0].rotation = [0, 0, 0]
tea_table_combination[0].position = [1.2629107798806214, 2.8355687608814506, 0.225]
tea_table_combination[0].rotation = [0, 0, 0]
landscape_stone[0].position = [2.920927656657104, 1.9139295242775616, 0.075]
landscape_stone[0].rotation = [0, 0, 0]
storage_rack[0].position = [4.855712371021976, 4.023360710298691, 0.9]
storage_rack[0].rotation = [0, 0, 0]
plant_B[0].position = [4.748645918362854, 3.882867743694865, 0.5]
plant_B[0].rotation = [0, 0, 0]
plant_A[0].position = [4.188949844932052, 1.287095891376618, 0.6]
plant_A[0].rotation = [0, 0, 0]
tea_table_combination[0].position = [1.2629107798806214, 2.8355687608814506, 0.225]
tea_table_combination[0].rotation = [0, 0, 0]
landscape_stone[0].position = [2.920927656657104, 1.9139295242775616, 0.075]
landscape_stone[0].rotation = [0, 0, 0]
storage_rack[0].position = [4.855712371021976, 4.023360710298691, 0.9]
storage_rack[0].rotation = [0, 0, 0]
plant_B[0].position = [4.748645918362854, 3.882867743694865, 0.5]
plant_B[0].rotation = [0, 0, 0]

solver.constraints = []

from math import radians

# Place the storage rack along the left wall, away from the door and window.
# Its longer dimension runs along the y-axis, leaving the room's circulation area open.
storage_rack[0].position = [0.25, 3.10, 0.90]
storage_rack[0].rotation = [0, 0, 0]

# The first plant is displayed on top of the storage rack.  The shared x-y
# location makes it horizontally within 0.10 m of the rack while avoiding overlap
# in the usable floor area.
plant_A[0].position = [0.25, 3.10, 2.40]
plant_A[0].rotation = [0, 0, radians(90)]

# Put the tea table in the central part of the room, keeping the area in front
# of the door at x=6.16, y=0.52 clear.
tea_table_combination[0].position = [3.10, 2.00, 0.225]
tea_table_combination[0].rotation = [0, 0, 0]

# The landscape stone is a small decorative object placed on the tea table.
landscape_stone[0].position = [3.10, 2.00, 0.525]
landscape_stone[0].rotation = [0, 0, radians(45)]

# Place the second plant in the back-right portion of the room, clear of both
# the door and the window section of the right wall.
plant_B[0].position = [4.80, 3.35, 0.50]
plant_B[0].rotation = [0, 0, radians(180)]

# Important support and proximity constraints.
solver.against_wall(storage_rack[0], walls[0])
solver.on_top_of(plant_A[0], storage_rack[0])
solver.on_top_of(landscape_stone[0], tea_table_combination[0])

# Anchor each floor-standing asset to its intended location.  Fixed points
# preserve the planned layout when the solver adjusts the scene.
solver.distance_constraint(
    storage_rack[0],
    AssetInstance(position=[0.25, 3.10, 0.90]),
    0.0, 0.0, weight=10
)
solver.distance_constraint(
    tea_table_combination[0],
    AssetInstance(position=[3.10, 2.00, 0.225]),
    0.0, 0.0, weight=10
)
solver.distance_constraint(
    plant_B[0],
    AssetInstance(position=[4.80, 3.35, 0.50]),
    0.0, 0.0, weight=10
)

# The plant and rack share the same x-y center, satisfying the required
# within-0.10-m proximity.  The z coordinate matches the top of the rack.
solver.distance_constraint(
    plant_A[0],
    AssetInstance(position=[0.25, 3.10, 2.40]),
    0.0, 0.0, weight=10
)

# Anchor the elevated decorative stone to the center of the tabletop.
solver.distance_constraint(
    landscape_stone[0],
    AssetInstance(position=[3.10, 2.00, 0.525]),
    0.0, 0.0, weight=10
)

# Orientation constraints: objects face into the room or toward the room center.
# These also provide an orientation constraint for every new asset instance.
room_center = AssetInstance(position=[3.08, 2.15, 0.0])
solver.point_towards(storage_rack[0], room_center)
solver.point_towards(plant_A[0], room_center)
solver.point_towards(tea_table_combination[0], room_center)
solver.point_towards(landscape_stone[0], room_center)
solver.point_towards(plant_B[0], room_center)

solver.constraints = []
landscape_stone[0].position = [3.0999999046325684, 2.0, 0.5249999761581421]
landscape_stone[0].rotation = [0, 0, 0.7979645348947851]
landscape_stone[0].optimize = 2
storage_rack[0].position = [0.24000005424022675, 3.0999999046325684, 0.8999999761581421]
storage_rack[0].rotation = [0, 0, 0.005651515482244516]
storage_rack[0].optimize = 2
plant_B[0].position = [4.800000190734863, 3.3499999046325684, 0.5]
plant_B[0].rotation = [0, 0, -3.1321678761290697]
plant_B[0].optimize = 2
plant_A[0].position = [0.25, 3.0999999046325684, 2.4000000953674316]
plant_A[0].rotation = [0, 0, 1.5833626980517244]
plant_A[0].optimize = 2
tea_table_combination[0].position = [3.0999999046325684, 2.0, 0.22499999403953552]
tea_table_combination[0].rotation = [0, 0, 0.01256637125682779]
tea_table_combination[0].optimize = 2

