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
    Wall(corner1=[6.00, 0.00, 0.00], corner2=[6.00, 4.00, 0.00]),
    Wall(corner1=[6.00, 4.00, 0.00], corner2=[0.00, 4.00, 0.00]),
    Wall(corner1=[0.00, 4.00, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
tall_pantry_cabinet_A = Assets(description="tall pantry unit with multiple shelves and drawers for kitchen storage", size=[0.60, 0.90, 2.10], placements=[AssetInstance() for _ in range(1)])
kitchen_utility_cart = Assets(description="mobile kitchen utility cart with shelves and towel rack", size=[0.45, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
bar_cabinet = Assets(description="medium-size bar cabinet with glass doors and storage compartments", size=[0.45, 1.10, 1.40], placements=[AssetInstance() for _ in range(1)])
tall_pantry_cabinet_B = Assets(description="tall pantry unit with multiple shelves and drawers for kitchen storage", size=[0.60, 0.90, 2.10], placements=[AssetInstance() for _ in range(1)])
kitchen_dining_table = Assets(description="larger rectangular kitchen dining table with 6 chairs", size=[1.80, 2.40, 0.95], placements=[AssetInstance() for _ in range(1)])
base_cabinets_with_countertop = Assets(description="extended long set of base cabinets with durable countertop for cooking prep", size=[0.65, 2.80, 0.92], placements=[AssetInstance() for _ in range(1)])

tall_pantry_cabinet_A[0].instance_id = 'tall_pantry_cabinet_A_0'
kitchen_utility_cart[0].instance_id = 'kitchen_utility_cart_0'
bar_cabinet[0].instance_id = 'bar_cabinet_0'
tall_pantry_cabinet_B[0].instance_id = 'tall_pantry_cabinet_B_0'
kitchen_dining_table[0].instance_id = 'kitchen_dining_table_0'
base_cabinets_with_countertop[0].instance_id = 'base_cabinets_with_countertop_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

tall_pantry_cabinet_A[0].position = [1.352182018171251, 0.29984823075367784, 1.05]
tall_pantry_cabinet_A[0].rotation = [0, 0, 0]
kitchen_utility_cart[0].position = [3.5165515693796774, 1.183609600527392, 0.45]
kitchen_utility_cart[0].rotation = [0, 0, 0]
bar_cabinet[0].position = [0.019495020151026665, 1.6626864247913136, 0.7]
bar_cabinet[0].rotation = [0, 0, 0]
tall_pantry_cabinet_B[0].position = [3.0632875260758556, 0.6743500994023615, 1.05]
tall_pantry_cabinet_B[0].rotation = [0, 0, 0]
kitchen_dining_table[0].position = [1.5046172048153692, 2.2670457900578844, 0.475]
kitchen_dining_table[0].rotation = [0, 0, 0]
base_cabinets_with_countertop[0].position = [2.2504455078695567, 1.6620303817300734, 0.46]
base_cabinets_with_countertop[0].rotation = [0, 0, 0]
tall_pantry_cabinet_A[0].position = [1.352182018171251, 0.29984823075367784, 1.05]
tall_pantry_cabinet_A[0].rotation = [0, 0, 0]
kitchen_utility_cart[0].position = [3.5165515693796774, 1.183609600527392, 0.45]
kitchen_utility_cart[0].rotation = [0, 0, 0]
bar_cabinet[0].position = [0.019495020151026665, 1.6626864247913136, 0.7]
bar_cabinet[0].rotation = [0, 0, 0]
tall_pantry_cabinet_B[0].position = [3.0632875260758556, 0.6743500994023615, 1.05]
tall_pantry_cabinet_B[0].rotation = [0, 0, 0]
kitchen_dining_table[0].position = [1.5046172048153692, 2.2670457900578844, 0.475]
kitchen_dining_table[0].rotation = [0, 0, 0]
base_cabinets_with_countertop[0].position = [2.2504455078695567, 1.6620303817300734, 0.46]
base_cabinets_with_countertop[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the three-part cabinet run along the upper wall. Their front sides
# face into the room, and the countertop unit is centered between the pantries.
tall_pantry_cabinet_A[0].position = [0.70, 3.70, 1.05]
tall_pantry_cabinet_A[0].rotation = [0, 0, radians(-90)]

base_cabinets_with_countertop[0].position = [2.55, 3.675, 0.46]
base_cabinets_with_countertop[0].rotation = [0, 0, radians(-90)]

tall_pantry_cabinet_B[0].position = [4.40, 3.70, 1.05]
tall_pantry_cabinet_B[0].rotation = [0, 0, radians(-90)]

# Keep the dining set in the open central area with usable circulation on all
# sides. Its long dimension runs from left to right.
kitchen_dining_table[0].position = [3.00, 1.45, 0.475]
kitchen_dining_table[0].rotation = [0, 0, radians(-90)]

# Place the cart against the lower wall, away from the dining set, with its
# working side facing into the room.
kitchen_utility_cart[0].position = [0.65, 0.225, 0.45]
kitchen_utility_cart[0].rotation = [0, 0, radians(90)]

# Place the bar cabinet on the lower portion of the right wall, facing inward.
bar_cabinet[0].position = [5.775, 0.80, 0.70]
bar_cabinet[0].rotation = [0, 0, radians(180)]


# High-priority anchors preserve the intended non-overlapping zones and ensure
# that the countertop cabinet remains geometrically between the two pantries.
pantry_A_anchor = AssetInstance(position=[0.70, 3.70, 1.05])
countertop_anchor = AssetInstance(position=[2.55, 3.675, 0.46])
pantry_B_anchor = AssetInstance(position=[4.40, 3.70, 1.05])
table_anchor = AssetInstance(position=[3.00, 1.45, 0.475])
cart_anchor = AssetInstance(position=[0.65, 0.225, 0.45])
bar_anchor = AssetInstance(position=[5.775, 0.80, 0.70])

solver.distance_constraint(
    tall_pantry_cabinet_A[0], pantry_A_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    base_cabinets_with_countertop[0], countertop_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    tall_pantry_cabinet_B[0], pantry_B_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    kitchen_dining_table[0], table_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    kitchen_utility_cart[0], cart_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    bar_cabinet[0], bar_anchor, 0, 0, weight=10
)

# Keep all wall furniture flush with its assigned boundary.
solver.against_wall(tall_pantry_cabinet_A[0], walls[1])
solver.against_wall(base_cabinets_with_countertop[0], walls[1])
solver.against_wall(tall_pantry_cabinet_B[0], walls[1])
solver.against_wall(kitchen_utility_cart[0], walls[3])
solver.against_wall(bar_cabinet[0], walls[0])

# Preserve a continuous cabinet run: each pantry sits immediately beside the
# countertop unit. The narrow tolerance accounts for their slightly different
# depths while keeping the units visually contiguous.
solver.distance_constraint(
    tall_pantry_cabinet_A[0],
    base_cabinets_with_countertop[0],
    1.84,
    1.87,
    weight=10,
)
solver.distance_constraint(
    tall_pantry_cabinet_B[0],
    base_cabinets_with_countertop[0],
    1.84,
    1.87,
    weight=10,
)

# Orientation targets make each wall-mounted item face directly into the room.
pantry_A_inward_target = AssetInstance(position=[0.70, 2.00, 1.05])
countertop_inward_target = AssetInstance(position=[2.55, 2.00, 0.46])
pantry_B_inward_target = AssetInstance(position=[4.40, 2.00, 1.05])
cart_inward_target = AssetInstance(position=[0.65, 2.00, 0.45])
bar_inward_target = AssetInstance(position=[3.00, 0.80, 0.70])

solver.point_towards(
    tall_pantry_cabinet_A[0], pantry_A_inward_target
)
solver.point_towards(
    base_cabinets_with_countertop[0], countertop_inward_target
)
solver.point_towards(
    tall_pantry_cabinet_B[0], pantry_B_inward_target
)
solver.point_towards(
    kitchen_utility_cart[0], cart_inward_target
)
solver.point_towards(
    bar_cabinet[0], bar_inward_target
)

# Align the dining set with the cabinet run so that its long footprint remains
# parallel to that wall and does not obstruct the wall-mounted furniture.
solver.align_with(
    kitchen_dining_table[0], base_cabinets_with_countertop[0]
)

solver.constraints = []
bar_cabinet[0].position = [5.77500057220459, 0.800000011920929, 0.699999988079071]
bar_cabinet[0].rotation = [0, 0, -3.1415925379825316]
bar_cabinet[0].optimize = 2
base_cabinets_with_countertop[0].position = [2.549999952316284, 3.674999713897705, 0.46000000834465027]
base_cabinets_with_countertop[0].rotation = [0, 0, -1.5707961375648578]
base_cabinets_with_countertop[0].optimize = 2
kitchen_utility_cart[0].position = [0.6499999761581421, 0.22499994933605194, 0.44999998807907104]
kitchen_utility_cart[0].rotation = [0, 0, 1.5707964675573447]
kitchen_utility_cart[0].optimize = 2
kitchen_dining_table[0].position = [3.0, 1.4500000476837158, 0.4749999940395355]
kitchen_dining_table[0].rotation = [0, 0, -1.5707961426924812]
kitchen_dining_table[0].optimize = 2
tall_pantry_cabinet_B[0].position = [4.400000095367432, 3.6999995708465576, 1.0499999523162842]
tall_pantry_cabinet_B[0].rotation = [0, 0, -1.570796171137072]
tall_pantry_cabinet_B[0].optimize = 2
tall_pantry_cabinet_A[0].position = [0.699999988079071, 3.6999995708465576, 1.0499999523162842]
tall_pantry_cabinet_A[0].rotation = [0, 0, -1.570796171137072]
tall_pantry_cabinet_A[0].optimize = 2

