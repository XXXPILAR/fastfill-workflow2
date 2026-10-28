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
    Wall(corner1=[0.00, 2.52, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.17, 0.00, 0.00]),
    Wall(corner1=[3.17, 0.00, 0.00], corner2=[3.17, 0.70, 0.00]),
    Wall(corner1=[3.17, 0.70, 0.00], corner2=[3.99, 0.70, 0.00]),
    Wall(corner1=[3.99, 0.70, 0.00], corner2=[3.99, 2.62, 0.00]),
    Wall(corner1=[3.99, 2.62, 0.00], corner2=[3.87, 2.62, 0.00]),
    Wall(corner1=[3.87, 2.62, 0.00], corner2=[3.87, 3.07, 0.00]),
    Wall(corner1=[3.87, 3.07, 0.00], corner2=[1.12, 3.07, 0.00]),
    Wall(corner1=[1.12, 3.07, 0.00], corner2=[1.12, 2.52, 0.00]),
    Wall(corner1=[1.12, 2.52, 0.00], corner2=[0.00, 2.52, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
flowers = Assets(description="flowers", size=[0.35, 0.35, 0.50], placements=[AssetInstance() for _ in range(1)])
bookcase = Assets(description="bookcase", size=[0.35, 1.20, 2.00], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[1.70, 2.40, 0.02], placements=[AssetInstance() for _ in range(1)])
dining_table_combination = Assets(description="dining table combination", size=[1.20, 1.80, 0.76], placements=[AssetInstance() for _ in range(1)])
plants = Assets(description="plants", size=[0.50, 0.50, 1.20], placements=[AssetInstance() for _ in range(1)])

flowers[0].instance_id = 'flowers_0'
bookcase[0].instance_id = 'bookcase_0'
carpet[0].instance_id = 'carpet_0'
dining_table_combination[0].instance_id = 'dining_table_combination_0'
plants[0].instance_id = 'plants_0'
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

flowers[0].position = [0.10046876415957728, 0.0035068781725942043, 0.25]
flowers[0].rotation = [0, 0, 0]
bookcase[0].position = [2.550198536449615, 2.018006189889691, 1.0]
bookcase[0].rotation = [0, 0, 0]
carpet[0].position = [1.4657641697156745, 2.7495442937873746, 0.01]
carpet[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [3.169273270038408, 0.8248623987681646, 0.38]
dining_table_combination[0].rotation = [0, 0, 0]
plants[0].position = [3.9146166940091858, 0.8945798218190403, 0.6]
plants[0].rotation = [0, 0, 0]
flowers[0].position = [0.10046876415957728, 0.0035068781725942043, 0.25]
flowers[0].rotation = [0, 0, 0]
bookcase[0].position = [2.550198536449615, 2.018006189889691, 1.0]
bookcase[0].rotation = [0, 0, 0]
carpet[0].position = [1.4657641697156745, 2.7495442937873746, 0.01]
carpet[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [3.169273270038408, 0.8248623987681646, 0.38]
dining_table_combination[0].rotation = [0, 0, 0]
plants[0].position = [3.9146166940091858, 0.8945798218190403, 0.6]
plants[0].rotation = [0, 0, 0]

solver.constraints = []

# Keep the doorway corridor along the left side clear by placing the dining
# arrangement in the central-right portion of the room.
bookcase[0].position = [0.175, 0.75, 1.00]
bookcase[0].rotation = [0, 0, radians(0)]

carpet[0].position = [2.15, 1.45, 0.01]
carpet[0].rotation = [0, 0, radians(0)]

# The dining set is centered on the carpet. Its height includes the carpet.
dining_table_combination[0].position = [2.15, 1.45, 0.40]
dining_table_combination[0].rotation = [0, 0, radians(0)]

# Flowers are centered on top of the dining table.
flowers[0].position = [2.15, 1.45, 1.03]
flowers[0].rotation = [0, 0, radians(0)]

# Put the plant in the upper-right recess, away from the window and doorway.
plants[0].position = [3.52, 2.72, 0.60]
plants[0].rotation = [0, 0, radians(-137)]

# Fixed points stabilize positions while allowing the semantic constraints
# below to preserve the intended relationships.
bookcase_anchor = AssetInstance(position=[0.175, 0.75, 1.00])
bookcase_facing_point = AssetInstance(position=[2.00, 0.75, 1.00])
carpet_anchor = AssetInstance(position=[2.15, 1.45, 0.01])
table_anchor = AssetInstance(position=[2.15, 1.45, 0.40])
table_facing_point = AssetInstance(position=[3.15, 1.45, 0.40])
flowers_anchor = AssetInstance(position=[2.15, 1.45, 1.03])
plants_anchor = AssetInstance(position=[3.52, 2.72, 0.60])

# The bookcase is backed against the lower portion of the left wall, below
# the door, and faces into the room.
solver.against_wall(bookcase[0], walls[0])
solver.distance_constraint(
    bookcase[0], bookcase_anchor, min_distance=0, max_distance=0, weight=10
)
solver.point_towards(bookcase[0], bookcase_facing_point)

# Anchor and orient the carpet in the open central-right floor area.
solver.distance_constraint(
    carpet[0], carpet_anchor, min_distance=0, max_distance=0, weight=10
)
solver.align_with(carpet[0], dining_table_combination[0])

# Center the dining set on the carpet and orient its long footprint
# consistently with the room.
solver.on_top_of(dining_table_combination[0], carpet[0])
solver.distance_constraint(
    dining_table_combination[0], table_anchor,
    min_distance=0, max_distance=0, weight=10
)
solver.point_towards(dining_table_combination[0], table_facing_point)

# The flowers require both support and horizontal-position semantics.
solver.on_top_of(flowers[0], dining_table_combination[0])
solver.distance_constraint(
    flowers[0], flowers_anchor, min_distance=0, max_distance=0, weight=10
)
solver.align_with(flowers[0], dining_table_combination[0])

# Anchor the plant inside the upper-right recess and turn it toward the
# dining area. The separation prevents overlap with the dining arrangement.
solver.distance_constraint(
    plants[0], plants_anchor, min_distance=0, max_distance=0, weight=10
)
solver.point_towards(plants[0], dining_table_combination[0])
solver.distance_constraint(
    plants[0], dining_table_combination[0],
    min_distance=1.50, max_distance=2.20, weight=1
)

# Additional clearance keeps the freestanding furniture separated from the
# wall-mounted bookcase.
solver.distance_constraint(
    dining_table_combination[0], bookcase[0],
    min_distance=1.70, max_distance=None, weight=1
)

solver.constraints = []
dining_table_combination[0].position = [2.1500000953674316, 1.4500000476837158, 0.4000000059604645]
dining_table_combination[0].rotation = [0, 0, 0.031415925765816845]
dining_table_combination[0].optimize = 2
flowers[0].position = [2.1500000953674316, 1.4500000476837158, 1.0299999713897705]
flowers[0].rotation = [0, 0, 0.03141585436950005]
flowers[0].optimize = 2
plants[0].position = [3.5199999809265137, 2.7200000286102295, 0.6000000238418579]
plants[0].rotation = [0, 0, -2.3785346837738808]
plants[0].optimize = 2
bookcase[0].position = [0.5986807346343994, 0.75, 1.0]
bookcase[0].rotation = [0, 0, 1.5708515556815952]
bookcase[0].optimize = 2
carpet[0].position = [2.1500000953674316, 1.4500000476837158, 0.009999999776482582]
carpet[0].rotation = [0, 0, 0.03141585436950005]
carpet[0].optimize = 2

