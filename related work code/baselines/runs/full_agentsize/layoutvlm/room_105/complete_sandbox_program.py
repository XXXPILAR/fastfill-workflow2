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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.00, 0.00, 0.00]),
    Wall(corner1=[6.00, 0.00, 0.00], corner2=[6.00, 3.00, 0.00]),
    Wall(corner1=[6.00, 3.00, 0.00], corner2=[0.00, 3.00, 0.00]),
    Wall(corner1=[0.00, 3.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
compact_round_bistro_table_A = Assets(description="A circular four legged light brown wooden table.", size=[0.80, 0.80, 0.75], placements=[AssetInstance() for _ in range(1)])
storage_box_A = Assets(description="A brown box with a cover that says patient files.", size=[0.35, 0.45, 0.28], placements=[AssetInstance() for _ in range(1)])
tall_pantry_cabinet_A = Assets(description="tall pantry cabinet", size=[0.60, 0.80, 2.10], placements=[AssetInstance() for _ in range(1)])
base_cabinet_run = Assets(description="A row of cabinets in white wood.", size=[0.60, 2.40, 0.90], placements=[AssetInstance() for _ in range(1)])
side_chair_A = Assets(description="An orange wooden chair with seat and back rest bolted with four black bolts.", size=[0.52, 0.45, 0.85], placements=[AssetInstance() for _ in range(1)])
waste_bin_A = Assets(description="a wheeled trash can", size=[0.65, 0.55, 1.00], placements=[AssetInstance() for _ in range(1)])
compact_round_bistro_table_B = Assets(description="A circular four legged light brown wooden table.", size=[0.80, 0.80, 0.75], placements=[AssetInstance() for _ in range(1)])
tall_refrigerator = Assets(description="tall refrigerator", size=[0.75, 0.80, 1.90], placements=[AssetInstance() for _ in range(1)])
storage_box_B = Assets(description="A brown box with a cover that says patient files.", size=[0.35, 0.45, 0.28], placements=[AssetInstance() for _ in range(1)])
side_chair_B = Assets(description="An orange wooden chair with seat and back rest bolted with four black bolts.", size=[0.52, 0.45, 0.85], placements=[AssetInstance() for _ in range(1)])
tall_pantry_cabinet_B = Assets(description="tall pantry cabinet", size=[0.60, 0.80, 2.10], placements=[AssetInstance() for _ in range(1)])
side_chair_C = Assets(description="An orange wooden chair with seat and back rest bolted with four black bolts.", size=[0.52, 0.45, 0.85], placements=[AssetInstance() for _ in range(1)])
waste_bin_B = Assets(description="a wheeled trash can", size=[0.65, 0.55, 1.00], placements=[AssetInstance() for _ in range(1)])
under_counter_cabinet = Assets(description="A black cabinet with a black tabletop.", size=[0.60, 0.90, 0.90], placements=[AssetInstance() for _ in range(1)])
freestanding_shelving_unit = Assets(description="A bunch of wooden shelves with a couple of drawers.", size=[0.45, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])

compact_round_bistro_table_A[0].instance_id = 'compact_round_bistro_table_A_0'
storage_box_A[0].instance_id = 'storage_box_A_0'
tall_pantry_cabinet_A[0].instance_id = 'tall_pantry_cabinet_A_0'
base_cabinet_run[0].instance_id = 'base_cabinet_run_0'
side_chair_A[0].instance_id = 'side_chair_A_0'
waste_bin_A[0].instance_id = 'waste_bin_A_0'
compact_round_bistro_table_B[0].instance_id = 'compact_round_bistro_table_B_0'
tall_refrigerator[0].instance_id = 'tall_refrigerator_0'
storage_box_B[0].instance_id = 'storage_box_B_0'
side_chair_B[0].instance_id = 'side_chair_B_0'
tall_pantry_cabinet_B[0].instance_id = 'tall_pantry_cabinet_B_0'
side_chair_C[0].instance_id = 'side_chair_C_0'
waste_bin_B[0].instance_id = 'waste_bin_B_0'
under_counter_cabinet[0].instance_id = 'under_counter_cabinet_0'
freestanding_shelving_unit[0].instance_id = 'freestanding_shelving_unit_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

compact_round_bistro_table_A[0].position = [4.977946742681162, 0.30909739930772373, 0.375]
compact_round_bistro_table_A[0].rotation = [0, 0, 0]
storage_box_A[0].position = [3.868102285981916, 2.4900219511660624, 0.14]
storage_box_A[0].rotation = [0, 0, 0]
tall_pantry_cabinet_A[0].position = [1.710882805357281, 2.8780295859336613, 1.05]
tall_pantry_cabinet_A[0].rotation = [0, 0, 0]
base_cabinet_run[0].position = [5.520105676254023, 1.3297701390417347, 0.45]
base_cabinet_run[0].rotation = [0, 0, 0]
side_chair_A[0].position = [2.6621691780899672, 2.8124219304636315, 0.425]
side_chair_A[0].rotation = [0, 0, 0]
waste_bin_A[0].position = [3.1576874778595263, 0.20828976732505966, 0.5]
waste_bin_A[0].rotation = [0, 0, 0]
compact_round_bistro_table_B[0].position = [4.513297435065491, 2.768974601847388, 0.375]
compact_round_bistro_table_B[0].rotation = [0, 0, 0]
tall_refrigerator[0].position = [4.3244695199418555, 1.4182444552977636, 0.95]
tall_refrigerator[0].rotation = [0, 0, 0]
storage_box_B[0].position = [0.8317239756722812, 1.2897817401142084, 0.14]
storage_box_B[0].rotation = [0, 0, 0]
side_chair_B[0].position = [0.07751035338258672, 2.208798292303845, 0.425]
side_chair_B[0].rotation = [0, 0, 0]
tall_pantry_cabinet_B[0].position = [1.2579348444073968, 1.332265133291675, 1.05]
tall_pantry_cabinet_B[0].rotation = [0, 0, 0]
side_chair_C[0].position = [5.312962079658977, 1.2841036367445469, 0.425]
side_chair_C[0].rotation = [0, 0, 0]
waste_bin_B[0].position = [3.805059908587949, 1.0961203850866341, 0.5]
waste_bin_B[0].rotation = [0, 0, 0]
under_counter_cabinet[0].position = [0.8869487569721046, 1.2314665274467738, 0.45]
under_counter_cabinet[0].rotation = [0, 0, 0]
freestanding_shelving_unit[0].position = [0.7233025516769287, 1.992627906444079, 0.9]
freestanding_shelving_unit[0].rotation = [0, 0, 0]
compact_round_bistro_table_A[0].position = [4.977946742681162, 0.30909739930772373, 0.375]
compact_round_bistro_table_A[0].rotation = [0, 0, 0]
storage_box_A[0].position = [3.868102285981916, 2.4900219511660624, 0.14]
storage_box_A[0].rotation = [0, 0, 0]
tall_pantry_cabinet_A[0].position = [1.710882805357281, 2.8780295859336613, 1.05]
tall_pantry_cabinet_A[0].rotation = [0, 0, 0]
base_cabinet_run[0].position = [5.520105676254023, 1.3297701390417347, 0.45]
base_cabinet_run[0].rotation = [0, 0, 0]
side_chair_A[0].position = [2.6621691780899672, 2.8124219304636315, 0.425]
side_chair_A[0].rotation = [0, 0, 0]
waste_bin_A[0].position = [3.1576874778595263, 0.20828976732505966, 0.5]
waste_bin_A[0].rotation = [0, 0, 0]
compact_round_bistro_table_B[0].position = [4.513297435065491, 2.768974601847388, 0.375]
compact_round_bistro_table_B[0].rotation = [0, 0, 0]
tall_refrigerator[0].position = [4.3244695199418555, 1.4182444552977636, 0.95]
tall_refrigerator[0].rotation = [0, 0, 0]
storage_box_B[0].position = [0.8317239756722812, 1.2897817401142084, 0.14]
storage_box_B[0].rotation = [0, 0, 0]
side_chair_B[0].position = [0.07751035338258672, 2.208798292303845, 0.425]
side_chair_B[0].rotation = [0, 0, 0]
tall_pantry_cabinet_B[0].position = [1.2579348444073968, 1.332265133291675, 1.05]
tall_pantry_cabinet_B[0].rotation = [0, 0, 0]
side_chair_C[0].position = [5.312962079658977, 1.2841036367445469, 0.425]
side_chair_C[0].rotation = [0, 0, 0]
waste_bin_B[0].position = [3.805059908587949, 1.0961203850866341, 0.5]
waste_bin_B[0].rotation = [0, 0, 0]
under_counter_cabinet[0].position = [0.8869487569721046, 1.2314665274467738, 0.45]
under_counter_cabinet[0].rotation = [0, 0, 0]
freestanding_shelving_unit[0].position = [0.7233025516769287, 1.992627906444079, 0.9]
freestanding_shelving_unit[0].rotation = [0, 0, 0]

solver.constraints = []

# Orientation references used to keep wall-mounted runs parallel to their walls.
facing_pos_x = AssetInstance(rotation=[0, 0, radians(0)])
facing_pos_y = AssetInstance(rotation=[0, 0, radians(90)])

# Place the two tables and side_chair_C along a common line. side_chair_C is
# geometrically between the tables, with a 0.09 m edge-to-edge gap to table B.
compact_round_bistro_table_A[0].position = [1.00, 1.45, 0.375]
compact_round_bistro_table_A[0].rotation = [0, 0, radians(0)]

side_chair_C[0].position = [1.80, 1.45, 0.425]
side_chair_C[0].rotation = [0, 0, radians(180)]

compact_round_bistro_table_B[0].position = [2.55, 1.45, 0.375]
compact_round_bistro_table_B[0].rotation = [0, 0, radians(0)]

# Additional chairs serve the two tables while leaving circulation space.
side_chair_B[0].position = [1.00, 0.425, 0.425]
side_chair_B[0].rotation = [0, 0, radians(90)]

side_chair_A[0].position = [3.35, 1.45, 0.425]
side_chair_A[0].rotation = [0, 0, radians(180)]

# Put the main cabinet run on the upper wall. Its 90-degree rotation makes its
# 2.40 m dimension run horizontally along that wall.
base_cabinet_run[0].position = [1.30, 2.70, 0.45]
base_cabinet_run[0].rotation = [0, 0, radians(90)]

under_counter_cabinet[0].position = [3.05, 2.70, 0.45]
under_counter_cabinet[0].rotation = [0, 0, radians(90)]

freestanding_shelving_unit[0].position = [4.20, 2.775, 0.90]
freestanding_shelving_unit[0].rotation = [0, 0, radians(90)]

# Place the tall appliances and pantry cabinets in a continuous run on the
# right wall, away from both windows on the left wall.
tall_pantry_cabinet_A[0].position = [5.70, 2.55, 1.05]
tall_pantry_cabinet_A[0].rotation = [0, 0, radians(0)]

tall_refrigerator[0].position = [5.625, 1.50, 0.95]
tall_refrigerator[0].rotation = [0, 0, radians(0)]

tall_pantry_cabinet_B[0].position = [5.70, 0.45, 1.05]
tall_pantry_cabinet_B[0].rotation = [0, 0, radians(0)]

# Keep the waste bins accessible along the lower wall without blocking chairs.
waste_bin_A[0].position = [3.85, 0.275, 0.50]
waste_bin_A[0].rotation = [0, 0, radians(90)]

waste_bin_B[0].position = [4.70, 0.275, 0.50]
waste_bin_B[0].rotation = [0, 0, radians(90)]

# Small storage boxes belong on work surfaces rather than on the floor.
storage_box_A[0].position = [0.65, 2.70, 1.04]
storage_box_A[0].rotation = [0, 0, radians(90)]

storage_box_B[0].position = [3.05, 2.70, 1.04]
storage_box_B[0].rotation = [0, 0, radians(90)]


# Important semantic constraints are specified first.

# The base cabinet run must remain against the upper wall.
solver.against_wall(base_cabinet_run[0], walls[2])
solver.align_with(base_cabinet_run[0], facing_pos_y)

# Keep side_chair_C between the two tables. The center-distance upper bounds
# include the objects' half-widths plus at most 0.30 m of clear edge gap.
solver.distance_constraint(
    side_chair_C[0], compact_round_bistro_table_A[0],
    0.66, 0.96, weight=10
)
solver.distance_constraint(
    compact_round_bistro_table_B[0], side_chair_C[0],
    0.66, 0.96, weight=10
)
solver.point_towards(side_chair_C[0], compact_round_bistro_table_A[0])

# side_chair_B (o0009) must face table A (o0000).
solver.distance_constraint(
    side_chair_B[0], compact_round_bistro_table_A[0],
    0.80, 1.20, weight=10
)
solver.point_towards(side_chair_B[0], compact_round_bistro_table_A[0])


# Position and orientation constraints for the remaining table/chair grouping.
solver.distance_constraint(
    compact_round_bistro_table_A[0],
    AssetInstance(position=[1.00, 1.45, 0.375]),
    0, 0, weight=10
)
solver.align_with(compact_round_bistro_table_A[0], facing_pos_x)

solver.distance_constraint(
    compact_round_bistro_table_B[0],
    AssetInstance(position=[2.55, 1.45, 0.375]),
    0, 0, weight=10
)
solver.align_with(compact_round_bistro_table_B[0], facing_pos_x)

solver.distance_constraint(
    side_chair_C[0],
    AssetInstance(position=[1.80, 1.45, 0.425]),
    0, 0, weight=10
)

solver.distance_constraint(
    side_chair_B[0],
    AssetInstance(position=[1.00, 0.425, 0.425]),
    0, 0, weight=10
)

solver.distance_constraint(
    side_chair_A[0], compact_round_bistro_table_B[0],
    0.70, 1.00, weight=10
)
solver.point_towards(side_chair_A[0], compact_round_bistro_table_B[0])


# Upper-wall storage and work surfaces.
solver.against_wall(under_counter_cabinet[0], walls[2])
solver.distance_constraint(
    under_counter_cabinet[0],
    AssetInstance(position=[3.05, 2.70, 0.45]),
    0, 0, weight=10
)
solver.align_with(under_counter_cabinet[0], base_cabinet_run[0])

solver.against_wall(freestanding_shelving_unit[0], walls[2])
solver.distance_constraint(
    freestanding_shelving_unit[0],
    AssetInstance(position=[4.20, 2.775, 0.90]),
    0, 0, weight=10
)
solver.align_with(freestanding_shelving_unit[0], base_cabinet_run[0])

# Retain the intended tangential location of the long base cabinet.
solver.distance_constraint(
    base_cabinet_run[0],
    AssetInstance(position=[1.30, 2.70, 0.45]),
    0, 0, weight=10
)


# Right-wall tall storage and refrigerator run.
solver.against_wall(tall_pantry_cabinet_A[0], walls[1])
solver.distance_constraint(
    tall_pantry_cabinet_A[0],
    AssetInstance(position=[5.70, 2.55, 1.05]),
    0, 0, weight=10
)
solver.align_with(tall_pantry_cabinet_A[0], facing_pos_x)

solver.against_wall(tall_refrigerator[0], walls[1])
solver.distance_constraint(
    tall_refrigerator[0],
    AssetInstance(position=[5.625, 1.50, 0.95]),
    0, 0, weight=10
)
solver.align_with(tall_refrigerator[0], tall_pantry_cabinet_A[0])

solver.against_wall(tall_pantry_cabinet_B[0], walls[1])
solver.distance_constraint(
    tall_pantry_cabinet_B[0],
    AssetInstance(position=[5.70, 0.45, 1.05]),
    0, 0, weight=10
)
solver.align_with(tall_pantry_cabinet_B[0], tall_pantry_cabinet_A[0])


# Lower-wall waste-bin positions.
solver.against_wall(waste_bin_A[0], walls[0])
solver.distance_constraint(
    waste_bin_A[0],
    AssetInstance(position=[3.85, 0.275, 0.50]),
    0, 0, weight=10
)
solver.align_with(waste_bin_A[0], facing_pos_y)

solver.against_wall(waste_bin_B[0], walls[0])
solver.distance_constraint(
    waste_bin_B[0],
    AssetInstance(position=[4.70, 0.275, 0.50]),
    0, 0, weight=10
)
solver.align_with(waste_bin_B[0], waste_bin_A[0])


# The boxes are supported by countertop surfaces. The distance constraints
# supply the required position-based constraints in addition to on_top_of.
solver.on_top_of(storage_box_A[0], base_cabinet_run[0])
solver.distance_constraint(
    storage_box_A[0],
    AssetInstance(position=[0.65, 2.70, 1.04]),
    0, 0, weight=10
)
solver.align_with(storage_box_A[0], base_cabinet_run[0])

solver.on_top_of(storage_box_B[0], under_counter_cabinet[0])
solver.distance_constraint(
    storage_box_B[0],
    AssetInstance(position=[3.05, 2.70, 1.04]),
    0, 0, weight=10
)
solver.align_with(storage_box_B[0], under_counter_cabinet[0])

solver.constraints = []
compact_round_bistro_table_A[0].position = [1.0, 1.4500000476837158, 0.375]
compact_round_bistro_table_A[0].rotation = [0, 0, 0.021991148286022624]
compact_round_bistro_table_A[0].optimize = 2
side_chair_A[0].position = [3.3499999046325684, 1.4500000476837158, 0.42500001192092896]
side_chair_A[0].rotation = [0, 0, -3.1321678761290697]
side_chair_A[0].optimize = 2
waste_bin_A[0].position = [3.8499999046325684, 0.32500001788139343, 0.5]
waste_bin_A[0].rotation = [0, 0, 1.5707963704785888]
waste_bin_A[0].optimize = 2
base_cabinet_run[0].position = [1.2999999523162842, 2.6998722553253174, 0.44999998807907104]
base_cabinet_run[0].rotation = [0, 0, -1.5707968302546131]
base_cabinet_run[0].optimize = 2
tall_refrigerator[0].position = [5.625, 1.5, 0.949999988079071]
tall_refrigerator[0].rotation = [0, 0, -3.1415912755329534]
tall_refrigerator[0].optimize = 2
tall_pantry_cabinet_A[0].position = [5.699997901916504, 2.549999952316284, 1.0499999523162842]
tall_pantry_cabinet_A[0].rotation = [0, 0, -3.141591002299298]
tall_pantry_cabinet_A[0].optimize = 2
side_chair_B[0].position = [1.0, 0.42500001192092896, 0.42500001192092896]
side_chair_B[0].rotation = [0, 0, 1.5833626980517244]
side_chair_B[0].optimize = 2
tall_pantry_cabinet_B[0].position = [5.699997901916504, 0.5341030359268188, 1.0499999523162842]
tall_pantry_cabinet_B[0].rotation = [0, 0, -3.141590944871474]
tall_pantry_cabinet_B[0].optimize = 2
compact_round_bistro_table_B[0].position = [2.549999952316284, 1.4500000476837158, 0.375]
compact_round_bistro_table_B[0].rotation = [0, 0, 0.01884955539881635]
compact_round_bistro_table_B[0].optimize = 2
storage_box_B[0].position = [3.049999952316284, 2.700000047683716, 1.0399999618530273]
storage_box_B[0].rotation = [0, 0, -1.5707944129999332]
storage_box_B[0].optimize = 2
side_chair_C[0].position = [1.7999999523162842, 1.4500000476837158, 0.42500001192092896]
side_chair_C[0].rotation = [0, 0, -3.125884689672577]
side_chair_C[0].optimize = 2
freestanding_shelving_unit[0].position = [4.199999809265137, 2.7749996185302734, 0.8999999761581421]
freestanding_shelving_unit[0].rotation = [0, 0, -1.5707947285204682]
freestanding_shelving_unit[0].optimize = 2
storage_box_A[0].position = [0.6499999761581421, 2.700000047683716, 1.0399999618530273]
storage_box_A[0].rotation = [0, 0, -1.5707969059882498]
storage_box_A[0].optimize = 2
waste_bin_B[0].position = [4.699999809265137, 0.32500001788139343, 0.5]
waste_bin_B[0].rotation = [0, 0, 1.5707963704841963]
waste_bin_B[0].optimize = 2
under_counter_cabinet[0].position = [3.049999952316284, 2.6999993324279785, 0.44999998807907104]
under_counter_cabinet[0].rotation = [0, 0, -1.570794472442697]
under_counter_cabinet[0].optimize = 2

