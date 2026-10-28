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
    Wall(corner1=[2.64, 0.00, 0.00], corner2=[2.64, 0.24, 0.00]),
    Wall(corner1=[2.64, 0.24, 0.00], corner2=[4.44, 0.24, 0.00]),
    Wall(corner1=[4.44, 0.24, 0.00], corner2=[4.44, 15.48, 0.00]),
    Wall(corner1=[4.44, 15.48, 0.00], corner2=[0.00, 15.48, 0.00]),
    Wall(corner1=[0.00, 15.48, 0.00], corner2=[0.00, 0.24, 0.00]),
    Wall(corner1=[0.00, 0.24, 0.00], corner2=[1.72, 0.24, 0.00]),
    Wall(corner1=[1.72, 0.24, 0.00], corner2=[1.72, 0.00, 0.00]),
    Wall(corner1=[1.72, 0.00, 0.00], corner2=[2.64, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
side_table = Assets(description="A sleek, modern table with a circular tabletop supported by an abstract, sculptural base.", size=[0.55, 0.55, 0.55], placements=[AssetInstance() for _ in range(1)])
wine_cooler_A = Assets(description="A tall, dark gray bookcase with multiple shelves and a small drawer at the bottom. It has thin legs and appears to be made of a matte material.", size=[0.40, 0.80, 1.80], placements=[AssetInstance() for _ in range(1)])
wine_cooler_B = Assets(description="A tall, dark gray bookcase with multiple shelves and a small drawer at the bottom. It has thin legs and appears to be made of a matte material.", size=[0.40, 0.80, 1.80], placements=[AssetInstance() for _ in range(1)])
lounge_chair_A = Assets(description="A modern, sleek chair with a continuous, flowing design. It features a smooth, glossy surface and an ergonomic shape that provides both support and comfort.", size=[0.90, 0.72, 0.82], placements=[AssetInstance() for _ in range(1)])
lounge_chair_B = Assets(description="A modern, sleek chair with a continuous, flowing design. It features a smooth, glossy surface and an ergonomic shape that provides both support and comfort.", size=[0.90, 0.72, 0.82], placements=[AssetInstance() for _ in range(1)])

side_table[0].instance_id = 'side_table_0'
wine_cooler_A[0].instance_id = 'wine_cooler_A_0'
wine_cooler_B[0].instance_id = 'wine_cooler_B_0'
lounge_chair_A[0].instance_id = 'lounge_chair_A_0'
lounge_chair_B[0].instance_id = 'lounge_chair_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

side_table[0].position = [1.2063267171703855, 15.148544745177707, 0.275]
side_table[0].rotation = [0, 0, 0]
wine_cooler_A[0].position = [3.510583443144174, 2.6867301040877893, 0.9]
wine_cooler_A[0].rotation = [0, 0, 0]
wine_cooler_B[0].position = [3.8218792040571516, 3.922075212055037, 0.9]
wine_cooler_B[0].rotation = [0, 0, 0]
lounge_chair_A[0].position = [0.806154325395288, 4.016613714253558, 0.41]
lounge_chair_A[0].rotation = [0, 0, 0]
lounge_chair_B[0].position = [1.2816271610712295, 7.572010394426417, 0.41]
lounge_chair_B[0].rotation = [0, 0, 0]
side_table[0].position = [1.2063267171703855, 15.148544745177707, 0.275]
side_table[0].rotation = [0, 0, 0]
wine_cooler_A[0].position = [3.510583443144174, 2.6867301040877893, 0.9]
wine_cooler_A[0].rotation = [0, 0, 0]
wine_cooler_B[0].position = [3.8218792040571516, 3.922075212055037, 0.9]
wine_cooler_B[0].rotation = [0, 0, 0]
lounge_chair_A[0].position = [0.806154325395288, 4.016613714253558, 0.41]
lounge_chair_A[0].rotation = [0, 0, 0]
lounge_chair_B[0].position = [1.2816271610712295, 7.572010394426417, 0.41]
lounge_chair_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange a compact lounge grouping at the far end of the room. This keeps
# both doors, their approach paths, and the window wall unobstructed.
side_table[0].position = [2.22, 13.25, 0.275]
side_table[0].rotation = [0, 0, radians(90)]

wine_cooler_A[0].position = [1.20, 15.28, 0.90]
wine_cooler_A[0].rotation = [0, 0, radians(-90)]

wine_cooler_B[0].position = [3.24, 15.28, 0.90]
wine_cooler_B[0].rotation = [0, 0, radians(-90)]

lounge_chair_A[0].position = [1.25, 13.25, 0.41]
lounge_chair_A[0].rotation = [0, 0, radians(90)]

lounge_chair_B[0].position = [3.19, 13.25, 0.41]
lounge_chair_B[0].rotation = [0, 0, radians(90)]

# Fixed points preserve the intended grouping while still allowing the
# relational constraints below to maintain its semantics if adjusted.
side_table_anchor = AssetInstance(
    position=[2.22, 13.25, 0.275],
    rotation=[0, 0, radians(90)]
)
wine_cooler_A_anchor = AssetInstance(
    position=[1.20, 15.28, 0.90],
    rotation=[0, 0, radians(-90)]
)
wine_cooler_B_anchor = AssetInstance(
    position=[3.24, 15.28, 0.90],
    rotation=[0, 0, radians(-90)]
)
lounge_chair_A_anchor = AssetInstance(
    position=[1.25, 13.25, 0.41],
    rotation=[0, 0, radians(90)]
)
lounge_chair_B_anchor = AssetInstance(
    position=[3.19, 13.25, 0.41],
    rotation=[0, 0, radians(90)]
)

# Important position constraints are specified first.
solver.distance_constraint(
    wine_cooler_A[0], wine_cooler_A_anchor, 0.0, 0.0, weight=10
)
solver.distance_constraint(
    wine_cooler_B[0], wine_cooler_B_anchor, 0.0, 0.0, weight=10
)
solver.distance_constraint(
    lounge_chair_A[0], lounge_chair_A_anchor, 0.0, 0.0, weight=10
)
solver.distance_constraint(
    lounge_chair_B[0], lounge_chair_B_anchor, 0.0, 0.0, weight=10
)
solver.distance_constraint(
    side_table[0], side_table_anchor, 0.0, 0.0, weight=10
)

# Both coolers stand against the solid upper wall, away from the window.
solver.against_wall(wine_cooler_A[0], walls[3])
solver.against_wall(wine_cooler_B[0], walls[3])

# The coolers face into the room toward their associated lounge chairs.
solver.point_towards(wine_cooler_A[0], lounge_chair_A[0])
solver.point_towards(wine_cooler_B[0], lounge_chair_B[0])

# Each lounge chair faces its corresponding wine cooler, as requested.
solver.point_towards(lounge_chair_A[0], wine_cooler_A[0])
solver.point_towards(lounge_chair_B[0], wine_cooler_B[0])

# The round table is orientation-neutral, but aligning it with the chairs
# provides the required stable orientation constraint.
solver.align_with(side_table[0], lounge_chair_A[0])

# Preserve useful clearances and the balanced, non-overlapping arrangement.
solver.distance_constraint(
    wine_cooler_A[0], wine_cooler_B[0], 1.90, 2.20, weight=5
)
solver.distance_constraint(
    lounge_chair_A[0], lounge_chair_B[0], 1.80, 2.10, weight=5
)
solver.distance_constraint(
    side_table[0], lounge_chair_A[0], 0.85, 1.10, weight=5
)
solver.distance_constraint(
    side_table[0], lounge_chair_B[0], 0.85, 1.10, weight=5
)
solver.distance_constraint(
    lounge_chair_A[0], wine_cooler_A[0], 1.80, 2.20, weight=5
)
solver.distance_constraint(
    lounge_chair_B[0], wine_cooler_B[0], 1.80, 2.20, weight=5
)

solver.constraints = []
lounge_chair_A[0].position = [1.25, 13.25, 0.4099999964237213]
lounge_chair_A[0].rotation = [0, 0, 1.5959290669047523]
lounge_chair_A[0].optimize = 2
wine_cooler_B[0].position = [3.240000009536743, 15.279999732971191, 0.8999999761581421]
wine_cooler_B[0].rotation = [0, 0, -1.5707971438158408]
wine_cooler_B[0].optimize = 2
side_table[0].position = [2.2200000286102295, 13.25, 0.2750000059604645]
side_table[0].rotation = [0, 0, 1.5959286567459086]
side_table[0].optimize = 2
lounge_chair_B[0].position = [3.190000057220459, 13.25, 0.4099999964237213]
lounge_chair_B[0].rotation = [0, 0, 1.5927874750809192]
lounge_chair_B[0].optimize = 2
wine_cooler_A[0].position = [1.2000000476837158, 15.279999732971191, 0.8999999761581421]
wine_cooler_A[0].rotation = [0, 0, -1.5707971438158408]
wine_cooler_A[0].optimize = 2

