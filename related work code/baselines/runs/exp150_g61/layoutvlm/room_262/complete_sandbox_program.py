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
    Wall(corner1=[6.96, 6.49, 0.00], corner2=[0.00, 6.49, 0.00]),
    Wall(corner1=[0.00, 6.49, 0.00], corner2=[0.00, 4.98, 0.00]),
    Wall(corner1=[0.00, 4.98, 0.00], corner2=[0.40, 4.97, 0.00]),
    Wall(corner1=[0.40, 4.97, 0.00], corner2=[0.40, 4.74, 0.00]),
    Wall(corner1=[0.40, 4.74, 0.00], corner2=[0.00, 4.74, 0.00]),
    Wall(corner1=[0.00, 4.74, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.82, 0.03, 0.00]),
    Wall(corner1=[2.82, 0.03, 0.00], corner2=[2.82, 0.44, 0.00]),
    Wall(corner1=[2.82, 0.44, 0.00], corner2=[6.42, 0.44, 0.00]),
    Wall(corner1=[6.42, 0.44, 0.00], corner2=[6.44, 4.98, 0.00]),
    Wall(corner1=[6.44, 4.98, 0.00], corner2=[6.96, 4.98, 0.00]),
    Wall(corner1=[6.96, 4.98, 0.00], corner2=[6.96, 6.49, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
lighting_A = Assets(description="lighting", size=[0.18, 0.24, 0.35], placements=[AssetInstance() for _ in range(1)])
lighting_B = Assets(description="lighting", size=[0.18, 0.24, 0.35], placements=[AssetInstance() for _ in range(1)])
lighting_C = Assets(description="lighting", size=[0.18, 0.24, 0.35], placements=[AssetInstance() for _ in range(1)])
lighting_D = Assets(description="lighting", size=[0.18, 0.24, 0.35], placements=[AssetInstance() for _ in range(1)])
lighting_E = Assets(description="lighting", size=[0.18, 0.24, 0.35], placements=[AssetInstance() for _ in range(1)])
bookcase_A = Assets(description="bookcase", size=[0.35, 1.20, 2.10], placements=[AssetInstance() for _ in range(1)])
dining_table_combination = Assets(description="dining table combination", size=[2.20, 2.60, 0.95], placements=[AssetInstance() for _ in range(1)])
bookcase_B = Assets(description="bookcase", size=[0.35, 1.20, 2.10], placements=[AssetInstance() for _ in range(1)])

lighting_A[0].instance_id = 'lighting_A_0'
lighting_B[0].instance_id = 'lighting_B_0'
lighting_C[0].instance_id = 'lighting_C_0'
lighting_D[0].instance_id = 'lighting_D_0'
lighting_E[0].instance_id = 'lighting_E_0'
bookcase_A[0].instance_id = 'bookcase_A_0'
dining_table_combination[0].instance_id = 'dining_table_combination_0'
bookcase_B[0].instance_id = 'bookcase_B_0'
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

lighting_A[0].position = [1.1054545238693128, 4.3069712355461744, 0.175]
lighting_A[0].rotation = [0, 0, 0]
lighting_B[0].position = [1.6222317926427738, 4.524657660666114, 0.175]
lighting_B[0].rotation = [0, 0, 0]
lighting_C[0].position = [3.2659390443896457, 0.8831904106771289, 0.175]
lighting_C[0].rotation = [0, 0, 0]
lighting_D[0].position = [5.1110254767182735, 6.122925030419707, 0.175]
lighting_D[0].rotation = [0, 0, 0]
lighting_E[0].position = [4.178959474227611, 2.6456340110052627, 0.175]
lighting_E[0].rotation = [0, 0, 0]
bookcase_A[0].position = [5.499177016207832, 1.9471779485903553, 1.05]
bookcase_A[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [0.7139632510618951, 3.993054352208949, 0.475]
dining_table_combination[0].rotation = [0, 0, 0]
bookcase_B[0].position = [3.300865655274315, 3.292249044323338, 1.05]
bookcase_B[0].rotation = [0, 0, 0]
lighting_A[0].position = [1.1054545238693128, 4.3069712355461744, 0.175]
lighting_A[0].rotation = [0, 0, 0]
lighting_B[0].position = [1.6222317926427738, 4.524657660666114, 0.175]
lighting_B[0].rotation = [0, 0, 0]
lighting_C[0].position = [3.2659390443896457, 0.8831904106771289, 0.175]
lighting_C[0].rotation = [0, 0, 0]
lighting_D[0].position = [5.1110254767182735, 6.122925030419707, 0.175]
lighting_D[0].rotation = [0, 0, 0]
lighting_E[0].position = [4.178959474227611, 2.6456340110052627, 0.175]
lighting_E[0].rotation = [0, 0, 0]
bookcase_A[0].position = [5.499177016207832, 1.9471779485903553, 1.05]
bookcase_A[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [0.7139632510618951, 3.993054352208949, 0.475]
dining_table_combination[0].rotation = [0, 0, 0]
bookcase_B[0].position = [3.300865655274315, 3.292249044323338, 1.05]
bookcase_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Interpret o0000 ... o0004 as lighting_A ... lighting_E, respectively.
# Put the small lights on bookcases, not on the floor. Keep the north
# window unobstructed and leave both southern door approaches clear.

bookcase_A[0].position = [0.175, 3.90, 1.05]
bookcase_A[0].rotation = [0, 0, 0]
bookcase_B[0].position = [0.175, 2.50, 1.05]
bookcase_B[0].rotation = [0, 0, 0]

dining_table_combination[0].position = [3.60, 3.70, 0.475]
dining_table_combination[0].rotation = [0, 0, 0]

# The first light touches the west wall while resting on bookcase_A.
lighting_A[0].position = [0.09, 3.90, 2.275]
lighting_A[0].rotation = [0, 0, 0]

# Arrange the other four lights along bookcase_B in the order B, D, C, E.
# Their 0.26 m pitch leaves 0.02 m between adjacent bounding boxes.
# C is therefore between both D/E and B/E.
lighting_B[0].position = [0.175, 2.11, 2.275]
lighting_B[0].rotation = [0, 0, 0]
lighting_D[0].position = [0.175, 2.37, 2.275]
lighting_D[0].rotation = [0, 0, 0]
lighting_C[0].position = [0.175, 2.63, 2.275]
lighting_C[0].rotation = [0, 0, 0]
lighting_E[0].position = [0.175, 2.89, 2.275]
lighting_E[0].rotation = [0, 0, 0]

# Wall placement and inward-facing orientation for both bookcases.
for storage_asset in (bookcase_A, bookcase_B):
    solver.against_wall(storage_asset[0], walls[5])
    solver.distance_constraint(
        storage_asset[0],
        AssetInstance(position=list(storage_asset[0].position)),
        0, 0, weight=10,
    )
    solver.align_with(
        storage_asset[0],
        AssetInstance(rotation=[0, 0, 0]),
    )

# Anchor the dining combination in the open central area.
# Its footprint leaves ample space south of it for door circulation.
solver.distance_constraint(
    dining_table_combination[0],
    AssetInstance(position=[3.60, 3.70, 0.475]),
    0, 0, weight=10,
)
solver.align_with(dining_table_combination[0], bookcase_A[0])

# Support constraints take priority over any subsequent layout refinements.
solver.on_top_of(lighting_A[0], bookcase_A[0])
solver.against_wall(lighting_A[0], walls[5])
solver.distance_constraint(
    lighting_A[0],
    AssetInstance(position=[0.09, 3.90, 2.275]),
    0, 0, weight=10,
)
solver.align_with(lighting_A[0], bookcase_A[0])

for light_asset in (lighting_B, lighting_D, lighting_C, lighting_E):
    solver.on_top_of(light_asset[0], bookcase_B[0])
    # Fixed centers preserve the collinear order and prevent overlaps.
    solver.distance_constraint(
        light_asset[0],
        AssetInstance(position=list(light_asset[0].position)),
        0, 0, weight=10,
    )
    solver.align_with(light_asset[0], bookcase_B[0])

# Explicit relational distances reinforce the requested lighting grouping.
solver.distance_constraint(
    lighting_D[0], lighting_C[0], 0.26, 0.30, weight=10
)
solver.distance_constraint(
    lighting_C[0], lighting_E[0], 0.26, 0.26, weight=10
)
solver.distance_constraint(
    lighting_C[0], lighting_B[0], 0.52, 0.52, weight=10
)
solver.distance_constraint(
    lighting_D[0], lighting_E[0], 0.52, 0.52, weight=10
)
solver.distance_constraint(
    lighting_B[0], lighting_E[0], 0.78, 0.78, weight=10
)

solver.constraints = []
bookcase_B[0].position = [0.19748976826667786, 2.5, 1.0499999523162842]
bookcase_B[0].rotation = [0, 0, 4.375108408150312e-08]
bookcase_B[0].optimize = 2
lighting_D[0].position = [0.17499999701976776, 2.369999885559082, 2.2749998569488525]
lighting_D[0].rotation = [0, 0, 4.3668034674728905e-08]
lighting_D[0].optimize = 2
bookcase_A[0].position = [0.17663292586803436, 5.575967311859131, 1.0499999523162842]
bookcase_A[0].rotation = [0, 0, -0.0027226473020888187]
bookcase_A[0].optimize = 2
lighting_B[0].position = [0.17499999701976776, 2.109999895095825, 2.2749998569488525]
lighting_B[0].rotation = [0, 0, 4.3668034674728905e-08]
lighting_B[0].optimize = 2
dining_table_combination[0].position = [3.5999999046325684, 3.700000047683716, 0.4749999940395355]
dining_table_combination[0].rotation = [0, 0, -0.0027428200379004926]
dining_table_combination[0].optimize = 2
lighting_E[0].position = [0.17499999701976776, 2.890000104904175, 2.2749998569488525]
lighting_E[0].rotation = [0, 0, 4.37654709765762e-08]
lighting_E[0].optimize = 2
lighting_C[0].position = [0.17499999701976776, 2.630000114440918, 2.2749998569488525]
lighting_C[0].rotation = [0, 0, 4.37654709765762e-08]
lighting_C[0].optimize = 2
lighting_A[0].position = [0.08999890089035034, 5.1053466796875, 2.2749998569488525]
lighting_A[0].rotation = [0, 0, -1.1704452219480716e-05]
lighting_A[0].optimize = 2

