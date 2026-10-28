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
base_cabinet_A = Assets(description="lower kitchen cabinet with multiple drawers and extra storage", size=[0.60, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
kitchen_counter = Assets(description="extended long kitchen counter with integrated sink, stove, and ample workspace", size=[0.65, 3.20, 0.92], placements=[AssetInstance() for _ in range(1)])
pantry_cabinet_A = Assets(description="tall wooden pantry cabinet with multiple shelves and greater storage capacity", size=[0.60, 0.90, 2.10], placements=[AssetInstance() for _ in range(1)])
free_standing_kitchen_island = Assets(description="large kitchen island with countertop workspace and storage underneath", size=[0.90, 1.80, 0.92], placements=[AssetInstance() for _ in range(1)])
base_cabinet_B = Assets(description="lower kitchen cabinet with multiple drawers and extra storage", size=[0.60, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
pantry_cabinet_B = Assets(description="tall wooden pantry cabinet with multiple shelves and greater storage capacity", size=[0.60, 0.90, 2.10], placements=[AssetInstance() for _ in range(1)])
base_cabinet_C = Assets(description="lower kitchen cabinet with multiple drawers and extra storage", size=[0.60, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
pantry_cabinet_C = Assets(description="tall wooden pantry cabinet with multiple shelves and greater storage capacity", size=[0.60, 0.90, 2.10], placements=[AssetInstance() for _ in range(1)])

base_cabinet_A[0].instance_id = 'base_cabinet_A_0'
kitchen_counter[0].instance_id = 'kitchen_counter_0'
pantry_cabinet_A[0].instance_id = 'pantry_cabinet_A_0'
free_standing_kitchen_island[0].instance_id = 'free_standing_kitchen_island_0'
base_cabinet_B[0].instance_id = 'base_cabinet_B_0'
pantry_cabinet_B[0].instance_id = 'pantry_cabinet_B_0'
base_cabinet_C[0].instance_id = 'base_cabinet_C_0'
pantry_cabinet_C[0].instance_id = 'pantry_cabinet_C_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

base_cabinet_A[0].position = [3.497397849644185, 0.06401843408398278, 0.45]
base_cabinet_A[0].rotation = [0, 0, 0]
kitchen_counter[0].position = [2.6399177438253187, 1.4913047557279118, 0.46]
kitchen_counter[0].rotation = [0, 0, 0]
pantry_cabinet_A[0].position = [0.7354186016753546, 2.151548774084188, 1.05]
pantry_cabinet_A[0].rotation = [0, 0, 0]
free_standing_kitchen_island[0].position = [1.6348137742063207, 3.5650950625331457, 0.46]
free_standing_kitchen_island[0].rotation = [0, 0, 0]
base_cabinet_B[0].position = [3.7974127030112053, 2.1428480894627966, 0.45]
base_cabinet_B[0].rotation = [0, 0, 0]
pantry_cabinet_B[0].position = [2.839722549115016, 3.233612941942306, 1.05]
pantry_cabinet_B[0].rotation = [0, 0, 0]
base_cabinet_C[0].position = [2.6924456050025207, 4.521039608424585, 0.45]
base_cabinet_C[0].rotation = [0, 0, 0]
pantry_cabinet_C[0].position = [0.0519467371432949, 3.255810437621621, 1.05]
pantry_cabinet_C[0].rotation = [0, 0, 0]
base_cabinet_A[0].position = [3.497397849644185, 0.06401843408398278, 0.45]
base_cabinet_A[0].rotation = [0, 0, 0]
kitchen_counter[0].position = [2.6399177438253187, 1.4913047557279118, 0.46]
kitchen_counter[0].rotation = [0, 0, 0]
pantry_cabinet_A[0].position = [0.7354186016753546, 2.151548774084188, 1.05]
pantry_cabinet_A[0].rotation = [0, 0, 0]
free_standing_kitchen_island[0].position = [1.6348137742063207, 3.5650950625331457, 0.46]
free_standing_kitchen_island[0].rotation = [0, 0, 0]
base_cabinet_B[0].position = [3.7974127030112053, 2.1428480894627966, 0.45]
base_cabinet_B[0].rotation = [0, 0, 0]
pantry_cabinet_B[0].position = [2.839722549115016, 3.233612941942306, 1.05]
pantry_cabinet_B[0].rotation = [0, 0, 0]
base_cabinet_C[0].position = [2.6924456050025207, 4.521039608424585, 0.45]
base_cabinet_C[0].rotation = [0, 0, 0]
pantry_cabinet_C[0].position = [0.0519467371432949, 3.255810437621621, 1.05]
pantry_cabinet_C[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the main counter along the top wall, facing into the room.
kitchen_counter[0].position = [2.00, 4.675, 0.46]
kitchen_counter[0].rotation = [0, 0, radians(-90)]

# Arrange three storage units along the left wall. Their depths extend inward
# from x=0, and their fronts face the central work area.
pantry_cabinet_A[0].position = [0.30, 0.45, 1.05]
pantry_cabinet_A[0].rotation = [0, 0, 0]

base_cabinet_A[0].position = [0.30, 1.30, 0.45]
base_cabinet_A[0].rotation = [0, 0, 0]

pantry_cabinet_B[0].position = [0.30, 2.15, 1.05]
pantry_cabinet_B[0].rotation = [0, 0, 0]

# Arrange the remaining storage units along the right wall, facing inward.
pantry_cabinet_C[0].position = [3.70, 0.45, 1.05]
pantry_cabinet_C[0].rotation = [0, 0, radians(180)]

base_cabinet_B[0].position = [3.70, 1.30, 0.45]
base_cabinet_B[0].rotation = [0, 0, radians(180)]

base_cabinet_C[0].position = [3.70, 2.10, 0.45]
base_cabinet_C[0].rotation = [0, 0, radians(180)]

# Place the island centrally between the two cabinet runs. This leaves useful
# circulation space on both sides and in front of the wall-mounted counter.
free_standing_kitchen_island[0].position = [2.00, 2.70, 0.46]
free_standing_kitchen_island[0].rotation = [0, 0, 0]

# Fixed reference point used to retain the island's central placement.
island_anchor = AssetInstance(position=[2.00, 2.70, 0.46])

# High-priority wall constraints preserve the three functional cabinet runs.
solver.against_wall(kitchen_counter[0], walls[1])

solver.against_wall(pantry_cabinet_A[0], walls[2])
solver.against_wall(base_cabinet_A[0], walls[2])
solver.against_wall(pantry_cabinet_B[0], walls[2])

solver.against_wall(pantry_cabinet_C[0], walls[0])
solver.against_wall(base_cabinet_B[0], walls[0])
solver.against_wall(base_cabinet_C[0], walls[0])

# Keep the island at the center of the available work zone.
solver.distance_constraint(
    free_standing_kitchen_island[0],
    island_anchor,
    0.0,
    0.0,
    weight=10,
)

# All wall-mounted units face the island and therefore open toward the room.
solver.point_towards(kitchen_counter[0], free_standing_kitchen_island[0])

solver.point_towards(pantry_cabinet_A[0], free_standing_kitchen_island[0])
solver.point_towards(base_cabinet_A[0], free_standing_kitchen_island[0])
solver.point_towards(pantry_cabinet_B[0], free_standing_kitchen_island[0])

solver.point_towards(pantry_cabinet_C[0], free_standing_kitchen_island[0])
solver.point_towards(base_cabinet_B[0], free_standing_kitchen_island[0])
solver.point_towards(base_cabinet_C[0], free_standing_kitchen_island[0])

# The island remains perpendicular to the top-wall counter, matching its
# initial long-axis orientation.
solver.align_with(
    free_standing_kitchen_island[0],
    kitchen_counter[0],
    angle=90,
)

# Preserve contiguous, non-overlapping cabinet runs along each side wall.
solver.distance_constraint(
    base_cabinet_A[0], pantry_cabinet_A[0], 0.85, 0.85, weight=10
)
solver.distance_constraint(
    pantry_cabinet_B[0], base_cabinet_A[0], 0.85, 0.85, weight=10
)

solver.distance_constraint(
    base_cabinet_B[0], pantry_cabinet_C[0], 0.85, 0.85, weight=10
)
solver.distance_constraint(
    base_cabinet_C[0], base_cabinet_B[0], 0.80, 0.80, weight=10
)

# Maintain practical clearance between the island, the top counter, and the
# closest cabinets on both sides.
solver.distance_constraint(
    free_standing_kitchen_island[0],
    kitchen_counter[0],
    1.90,
    2.10,
    weight=1,
)
solver.distance_constraint(
    free_standing_kitchen_island[0],
    pantry_cabinet_B[0],
    1.70,
    2.10,
    weight=1,
)
solver.distance_constraint(
    free_standing_kitchen_island[0],
    base_cabinet_C[0],
    1.70,
    2.10,
    weight=1,
)

solver.constraints = []
base_cabinet_B[0].position = [3.700000047683716, 1.3580524921417236, 0.44999998807907104]
base_cabinet_B[0].rotation = [0, 0, -3.141592600653956]
base_cabinet_B[0].optimize = 2
pantry_cabinet_B[0].position = [0.30000001192092896, 2.2594223022460938, 1.0499999523162842]
pantry_cabinet_B[0].rotation = [0, 0, 3.336456715051585e-08]
pantry_cabinet_B[0].optimize = 2
free_standing_kitchen_island[0].position = [2.0, 2.700000047683716, 0.46000000834465027]
free_standing_kitchen_island[0].rotation = [0, 0, 9.075224415824671e-08]
free_standing_kitchen_island[0].optimize = 2
kitchen_counter[0].position = [2.0, 4.675000190734863, 0.46000000834465027]
kitchen_counter[0].rotation = [0, 0, -1.5707963231783817]
kitchen_counter[0].optimize = 2
pantry_cabinet_C[0].position = [3.700000047683716, 0.5012764930725098, 1.0499999523162842]
pantry_cabinet_C[0].rotation = [0, 0, -3.1415926106835443]
pantry_cabinet_C[0].optimize = 2
base_cabinet_C[0].position = [3.700000047683716, 2.2094249725341797, 0.44999998807907104]
base_cabinet_C[0].rotation = [0, 0, -3.141592600653956]
base_cabinet_C[0].optimize = 2
pantry_cabinet_A[0].position = [0.30000001192092896, 0.5080318450927734, 1.0499999523162842]
pantry_cabinet_A[0].rotation = [0, 0, 4.599096316652835e-08]
pantry_cabinet_A[0].optimize = 2
base_cabinet_A[0].position = [0.30000004172325134, 1.3580524921417236, 0.44999998807907104]
base_cabinet_A[0].rotation = [0, 0, 3.310950086549757e-08]
base_cabinet_A[0].optimize = 2

