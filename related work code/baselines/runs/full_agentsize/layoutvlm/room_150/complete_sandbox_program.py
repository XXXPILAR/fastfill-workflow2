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
    Wall(corner1=[6.00, 0.00, 0.00], corner2=[6.00, 5.00, 0.00]),
    Wall(corner1=[6.00, 5.00, 0.00], corner2=[0.00, 5.00, 0.00]),
    Wall(corner1=[0.00, 5.00, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
tall_pantry_cabinet_A = Assets(description="floor-standing tall pantry cabinet with multiple shelves and solid doors for bulk storage", size=[0.60, 0.60, 2.10], placements=[AssetInstance() for _ in range(1)])
tall_pantry_cabinet_B = Assets(description="floor-standing tall pantry cabinet with multiple shelves and solid doors for bulk storage", size=[0.60, 0.60, 2.10], placements=[AssetInstance() for _ in range(1)])
floor_wine_rack_cabinet = Assets(description="compact floor cabinet with built-in wine rack for bottle storage", size=[0.60, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
kitchen_island_with_storage_and_countertop_A = Assets(description="large modern rectangular kitchen island with spacious storage cupboards and durable countertop", size=[1.00, 2.20, 0.92], placements=[AssetInstance() for _ in range(1)])
base_kitchen_cabinets_with_countertop = Assets(description="long stretch of modern base kitchen cabinets with wooden countertop and ample storage", size=[0.65, 3.00, 0.92], placements=[AssetInstance() for _ in range(1)])
oven_with_built_in_stove = Assets(description="floor-standing built-in oven with stove top including four burners", size=[0.65, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
kitchen_island_with_storage_and_countertop_B = Assets(description="large modern rectangular kitchen island with spacious storage cupboards and durable countertop", size=[1.00, 2.20, 0.92], placements=[AssetInstance() for _ in range(1)])
floor_microwave_cabinet_with_countertop = Assets(description="floor cabinet designed to hold microwave, with countertop space", size=[0.65, 0.90, 0.92], placements=[AssetInstance() for _ in range(1)])

tall_pantry_cabinet_A[0].instance_id = 'tall_pantry_cabinet_A_0'
tall_pantry_cabinet_B[0].instance_id = 'tall_pantry_cabinet_B_0'
floor_wine_rack_cabinet[0].instance_id = 'floor_wine_rack_cabinet_0'
kitchen_island_with_storage_and_countertop_A[0].instance_id = 'kitchen_island_with_storage_and_countertop_A_0'
base_kitchen_cabinets_with_countertop[0].instance_id = 'base_kitchen_cabinets_with_countertop_0'
oven_with_built_in_stove[0].instance_id = 'oven_with_built_in_stove_0'
kitchen_island_with_storage_and_countertop_B[0].instance_id = 'kitchen_island_with_storage_and_countertop_B_0'
floor_microwave_cabinet_with_countertop[0].instance_id = 'floor_microwave_cabinet_with_countertop_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

tall_pantry_cabinet_A[0].position = [4.774421548302648, 0.2866738245598788, 1.05]
tall_pantry_cabinet_A[0].rotation = [0, 0, 0]
tall_pantry_cabinet_B[0].position = [4.01802824519552, 1.04471096494775, 1.05]
tall_pantry_cabinet_B[0].rotation = [0, 0, 0]
floor_wine_rack_cabinet[0].position = [5.087906570054212, 4.341360342534097, 0.45]
floor_wine_rack_cabinet[0].rotation = [0, 0, 0]
kitchen_island_with_storage_and_countertop_A[0].position = [5.5097122421216955, 4.894462871450609, 0.46]
kitchen_island_with_storage_and_countertop_A[0].rotation = [0, 0, 0]
base_kitchen_cabinets_with_countertop[0].position = [5.351552030907824, 1.5598778353228382, 0.46]
base_kitchen_cabinets_with_countertop[0].rotation = [0, 0, 0]
oven_with_built_in_stove[0].position = [1.4350110178865803, 1.9660593596039422, 0.45]
oven_with_built_in_stove[0].rotation = [0, 0, 0]
kitchen_island_with_storage_and_countertop_B[0].position = [3.2529995388627047, 2.2718425480103352, 0.46]
kitchen_island_with_storage_and_countertop_B[0].rotation = [0, 0, 0]
floor_microwave_cabinet_with_countertop[0].position = [5.446280682247431, 3.2537279563708896, 0.46]
floor_microwave_cabinet_with_countertop[0].rotation = [0, 0, 0]
tall_pantry_cabinet_A[0].position = [4.774421548302648, 0.2866738245598788, 1.05]
tall_pantry_cabinet_A[0].rotation = [0, 0, 0]
tall_pantry_cabinet_B[0].position = [4.01802824519552, 1.04471096494775, 1.05]
tall_pantry_cabinet_B[0].rotation = [0, 0, 0]
floor_wine_rack_cabinet[0].position = [5.087906570054212, 4.341360342534097, 0.45]
floor_wine_rack_cabinet[0].rotation = [0, 0, 0]
kitchen_island_with_storage_and_countertop_A[0].position = [5.5097122421216955, 4.894462871450609, 0.46]
kitchen_island_with_storage_and_countertop_A[0].rotation = [0, 0, 0]
base_kitchen_cabinets_with_countertop[0].position = [5.351552030907824, 1.5598778353228382, 0.46]
base_kitchen_cabinets_with_countertop[0].rotation = [0, 0, 0]
oven_with_built_in_stove[0].position = [1.4350110178865803, 1.9660593596039422, 0.45]
oven_with_built_in_stove[0].rotation = [0, 0, 0]
kitchen_island_with_storage_and_countertop_B[0].position = [3.2529995388627047, 2.2718425480103352, 0.46]
kitchen_island_with_storage_and_countertop_B[0].rotation = [0, 0, 0]
floor_microwave_cabinet_with_countertop[0].position = [5.446280682247431, 3.2537279563708896, 0.46]
floor_microwave_cabinet_with_countertop[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange a continuous run of storage and cooking cabinets along the back wall.
# Their fronts face into the room (-y), leaving the center and front accessible.
tall_pantry_cabinet_A[0].position = [0.30, 4.70, 1.05]
tall_pantry_cabinet_A[0].rotation = [0, 0, radians(-90)]

tall_pantry_cabinet_B[0].position = [0.90, 4.70, 1.05]
tall_pantry_cabinet_B[0].rotation = [0, 0, radians(-90)]

floor_wine_rack_cabinet[0].position = [1.50, 4.70, 0.45]
floor_wine_rack_cabinet[0].rotation = [0, 0, radians(-90)]

base_kitchen_cabinets_with_countertop[0].position = [3.30, 4.675, 0.46]
base_kitchen_cabinets_with_countertop[0].rotation = [0, 0, radians(-90)]

oven_with_built_in_stove[0].position = [5.10, 4.675, 0.45]
oven_with_built_in_stove[0].rotation = [0, 0, radians(-90)]

# Place the microwave cabinet against the right wall, facing into the room.
# Keeping it near the front separates it from the back-wall cabinet run.
floor_microwave_cabinet_with_countertop[0].position = [5.675, 0.55, 0.46]
floor_microwave_cabinet_with_countertop[0].rotation = [0, 0, radians(180)]

# Place the two islands parallel to one another with a generous aisle between
# them and circulation space around the perimeter cabinetry.
kitchen_island_with_storage_and_countertop_A[0].position = [2.00, 2.25, 0.46]
kitchen_island_with_storage_and_countertop_A[0].rotation = [0, 0, radians(0)]

kitchen_island_with_storage_and_countertop_B[0].position = [4.00, 2.25, 0.46]
kitchen_island_with_storage_and_countertop_B[0].rotation = [0, 0, radians(180)]


# Fixed anchors preserve the intended non-overlapping positions if the solver
# adjusts the layout. Orientation targets sit directly in front of each wall
# unit so that point_towards produces the desired cardinal orientation.
pantry_A_anchor = AssetInstance(position=[0.30, 4.70, 1.05])
pantry_B_anchor = AssetInstance(position=[0.90, 4.70, 1.05])
wine_rack_anchor = AssetInstance(position=[1.50, 4.70, 0.45])
base_cabinets_anchor = AssetInstance(position=[3.30, 4.675, 0.46])
oven_anchor = AssetInstance(position=[5.10, 4.675, 0.45])
microwave_anchor = AssetInstance(position=[5.675, 0.55, 0.46])
island_A_anchor = AssetInstance(position=[2.00, 2.25, 0.46])
island_B_anchor = AssetInstance(position=[4.00, 2.25, 0.46])

pantry_A_front_target = AssetInstance(position=[0.30, 3.70, 1.05])
pantry_B_front_target = AssetInstance(position=[0.90, 3.70, 1.05])
wine_rack_front_target = AssetInstance(position=[1.50, 3.70, 0.45])
base_cabinets_front_target = AssetInstance(position=[3.30, 3.70, 0.46])
oven_front_target = AssetInstance(position=[5.10, 3.70, 0.45])
microwave_front_target = AssetInstance(position=[4.675, 0.55, 0.46])


# Back-wall cabinetry: wall contact is the primary placement requirement,
# followed by high-weight anchors that maintain the ordered cabinet run.
solver.against_wall(tall_pantry_cabinet_A[0], walls[1])
solver.distance_constraint(
    tall_pantry_cabinet_A[0], pantry_A_anchor, 0, 0, weight=10
)
solver.point_towards(tall_pantry_cabinet_A[0], pantry_A_front_target)

solver.against_wall(tall_pantry_cabinet_B[0], walls[1])
solver.distance_constraint(
    tall_pantry_cabinet_B[0], pantry_B_anchor, 0, 0, weight=10
)
solver.point_towards(tall_pantry_cabinet_B[0], pantry_B_front_target)

solver.against_wall(floor_wine_rack_cabinet[0], walls[1])
solver.distance_constraint(
    floor_wine_rack_cabinet[0], wine_rack_anchor, 0, 0, weight=10
)
solver.point_towards(floor_wine_rack_cabinet[0], wine_rack_front_target)

solver.against_wall(base_kitchen_cabinets_with_countertop[0], walls[1])
solver.distance_constraint(
    base_kitchen_cabinets_with_countertop[0],
    base_cabinets_anchor,
    0,
    0,
    weight=10,
)
solver.point_towards(
    base_kitchen_cabinets_with_countertop[0], base_cabinets_front_target
)

solver.against_wall(oven_with_built_in_stove[0], walls[1])
solver.distance_constraint(
    oven_with_built_in_stove[0], oven_anchor, 0, 0, weight=10
)
solver.point_towards(oven_with_built_in_stove[0], oven_front_target)

# Right-wall microwave cabinet.
solver.against_wall(floor_microwave_cabinet_with_countertop[0], walls[0])
solver.distance_constraint(
    floor_microwave_cabinet_with_countertop[0],
    microwave_anchor,
    0,
    0,
    weight=10,
)
solver.point_towards(
    floor_microwave_cabinet_with_countertop[0], microwave_front_target
)

# Exact center anchors keep both islands clear of the perimeter cabinets.
# The islands face each other across the 1 m clear aisle between their edges.
solver.distance_constraint(
    kitchen_island_with_storage_and_countertop_A[0],
    island_A_anchor,
    0,
    0,
    weight=10,
)
solver.point_towards(
    kitchen_island_with_storage_and_countertop_A[0],
    kitchen_island_with_storage_and_countertop_B[0],
)

solver.distance_constraint(
    kitchen_island_with_storage_and_countertop_B[0],
    island_B_anchor,
    0,
    0,
    weight=10,
)
solver.point_towards(
    kitchen_island_with_storage_and_countertop_B[0],
    kitchen_island_with_storage_and_countertop_A[0],
)

# Preserve the two-meter center-to-center spacing between the islands.
solver.distance_constraint(
    kitchen_island_with_storage_and_countertop_A[0],
    kitchen_island_with_storage_and_countertop_B[0],
    2.0,
    2.0,
    weight=10,
)
solver.distance_constraint(
    kitchen_island_with_storage_and_countertop_B[0],
    kitchen_island_with_storage_and_countertop_A[0],
    2.0,
    2.0,
    weight=10,
)

solver.constraints = []
floor_microwave_cabinet_with_countertop[0].position = [5.674999713897705, 0.550000011920929, 0.46000000834465027]
floor_microwave_cabinet_with_countertop[0].rotation = [0, 0, -3.141592609932231]
floor_microwave_cabinet_with_countertop[0].optimize = 2
kitchen_island_with_storage_and_countertop_A[0].position = [2.0, 2.25, 0.46000000834465027]
kitchen_island_with_storage_and_countertop_A[0].rotation = [0, 0, 0.01884955539881635]
kitchen_island_with_storage_and_countertop_A[0].optimize = 2
floor_wine_rack_cabinet[0].position = [1.5, 4.6999993324279785, 0.44999998807907104]
floor_wine_rack_cabinet[0].rotation = [0, 0, -1.5707962830639253]
floor_wine_rack_cabinet[0].optimize = 2
kitchen_island_with_storage_and_countertop_B[0].position = [4.0, 2.25, 0.46000000834465027]
kitchen_island_with_storage_and_countertop_B[0].rotation = [0, 0, -3.122743098190977]
kitchen_island_with_storage_and_countertop_B[0].optimize = 2
oven_with_built_in_stove[0].position = [5.099999904632568, 4.674999713897705, 0.44999998807907104]
oven_with_built_in_stove[0].rotation = [0, 0, -1.5707962830767017]
oven_with_built_in_stove[0].optimize = 2
tall_pantry_cabinet_B[0].position = [0.8999999761581421, 4.6999993324279785, 1.0499999523162842]
tall_pantry_cabinet_B[0].rotation = [0, 0, -1.5707962830639253]
tall_pantry_cabinet_B[0].optimize = 2
tall_pantry_cabinet_A[0].position = [0.29999998211860657, 4.562824726104736, 1.0499999523162842]
tall_pantry_cabinet_A[0].rotation = [0, 0, 2.1171892564157898e-08]
tall_pantry_cabinet_A[0].optimize = 2
base_kitchen_cabinets_with_countertop[0].position = [3.299999952316284, 4.675000190734863, 0.46000000834465027]
base_kitchen_cabinets_with_countertop[0].rotation = [0, 0, -1.5707962970276046]
base_kitchen_cabinets_with_countertop[0].optimize = 2

