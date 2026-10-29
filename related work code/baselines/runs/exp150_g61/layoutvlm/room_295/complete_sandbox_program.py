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
    Wall(corner1=[5.98, 4.20, 0.00], corner2=[5.98, 6.18, 0.00]),
    Wall(corner1=[5.98, 6.18, 0.00], corner2=[0.00, 6.18, 0.00]),
    Wall(corner1=[0.00, 6.18, 0.00], corner2=[0.00, 4.40, 0.00]),
    Wall(corner1=[0.00, 4.40, 0.00], corner2=[2.06, 4.40, 0.00]),
    Wall(corner1=[2.06, 4.40, 0.00], corner2=[2.06, 0.00, 0.00]),
    Wall(corner1=[2.06, 0.00, 0.00], corner2=[4.98, 0.00, 0.00]),
    Wall(corner1=[4.98, 0.00, 0.00], corner2=[4.98, 4.20, 0.00]),
    Wall(corner1=[4.98, 4.20, 0.00], corner2=[5.98, 4.20, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
table_A = Assets(description="table", size=[0.40, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
sofa = Assets(description="sofa", size=[0.95, 2.30, 0.85], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="chair", size=[0.85, 0.80, 0.85], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.85, 0.80, 0.85], placements=[AssetInstance() for _ in range(1)])
table_B = Assets(description="table", size=[0.65, 1.20, 0.42], placements=[AssetInstance() for _ in range(1)])

table_A[0].instance_id = 'table_A_0'
sofa[0].instance_id = 'sofa_0'
chair_A[0].instance_id = 'chair_A_0'
chair_B[0].instance_id = 'chair_B_0'
table_B[0].instance_id = 'table_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

table_A[0].position = [1.0736444602645525, 5.517753268033173, 0.375]
table_A[0].rotation = [0, 0, 0]
sofa[0].position = [2.746029493886847, 4.991320424876667, 0.425]
sofa[0].rotation = [0, 0, 0]
chair_A[0].position = [3.120836072969226, 2.766647195518966, 0.425]
chair_A[0].rotation = [0, 0, 0]
chair_B[0].position = [1.7978211861036515, 4.661882482605977, 0.425]
chair_B[0].rotation = [0, 0, 0]
table_B[0].position = [3.401385872300703, 2.686805560217544, 0.21]
table_B[0].rotation = [0, 0, 0]
table_A[0].position = [1.0736444602645525, 5.517753268033173, 0.375]
table_A[0].rotation = [0, 0, 0]
sofa[0].position = [2.746029493886847, 4.991320424876667, 0.425]
sofa[0].rotation = [0, 0, 0]
chair_A[0].position = [3.120836072969226, 2.766647195518966, 0.425]
chair_A[0].rotation = [0, 0, 0]
chair_B[0].position = [1.7978211861036515, 4.661882482605977, 0.425]
chair_B[0].rotation = [0, 0, 0]
table_B[0].position = [3.401385872300703, 2.686805560217544, 0.21]
table_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the seating group in the narrow southern part of the room.
# The console (table_A), sofa, and coffee table (table_B) share an axis:
# console behind the sofa, coffee table in front. The northern entrance
# area remains empty, including the approaches to all four doors.

table_A[0].position = [3.52, 3.95, 0.375]
table_A[0].rotation = [0, 0, radians(-90)]

sofa[0].position = [3.52, 3.05, 0.425]
sofa[0].rotation = [0, 0, radians(-90)]

table_B[0].position = [3.52, 1.70, 0.21]
table_B[0].rotation = [0, 0, radians(-90)]

# Two chairs face north toward the seating group. Their rotated footprints
# remain inside the side walls and leave the middle of the window accessible.
chair_A[0].position = [2.65, 0.55, 0.425]
chair_A[0].rotation = [0, 0, radians(90)]

chair_B[0].position = [4.39, 0.55, 0.425]
chair_B[0].rotation = [0, 0, radians(90)]

# Prioritize these collision-free center positions. Fixed references are
# constraint anchors, not additional scene furniture. Using matching heights
# makes these constraints valid for three-dimensional center distances.
for furnishing in (table_A, sofa, table_B, chair_A, chair_B):
    solver.distance_constraint(
        furnishing[0],
        AssetInstance(position=list(furnishing[0].position)),
        0.0,
        0.0,
        weight=10,
    )

# Primary orientation requirement: the sofa faces the coffee table.
solver.point_towards(sofa[0], table_B[0])

# Keep both tables parallel to the sofa, and the chairs facing the sofa.
solver.align_with(table_A[0], sofa[0], angle=0)
solver.align_with(table_B[0], sofa[0], angle=0)
solver.align_with(chair_A[0], sofa[0], angle=180)
solver.align_with(chair_B[0], sofa[0], angle=180)

# Preserve usable gaps between the furniture if the layout is adjusted.
# Distances refer to bounding-box centers, including their different heights.
solver.distance_constraint(sofa[0], table_A[0], 0.85, 1.00, weight=10)
solver.distance_constraint(table_A[0], sofa[0], 0.85, 1.00, weight=10)
solver.distance_constraint(sofa[0], table_B[0], 1.30, 1.45, weight=10)
solver.distance_constraint(table_B[0], sofa[0], 1.30, 1.45, weight=10)

solver.distance_constraint(chair_A[0], table_B[0], 1.40, 1.60)
solver.distance_constraint(chair_B[0], table_B[0], 1.40, 1.60)
solver.distance_constraint(chair_A[0], chair_B[0], 1.65, 1.85)
solver.distance_constraint(chair_B[0], chair_A[0], 1.65, 1.85)

# All supplied assets are floor-standing furniture; no on_top_of constraints
# are appropriate here.

solver.constraints = []
sofa[0].position = [3.5199999809265137, 3.049999952316284, 0.42500001192092896]
sofa[0].rotation = [0, 0, -1.53623880796822]
sofa[0].optimize = 2
chair_B[0].position = [4.389999866485596, 0.550000011920929, 0.42500001192092896]
chair_B[0].rotation = [0, 0, 1.6053049998316455]
chair_B[0].optimize = 2
table_B[0].position = [3.5199999809265137, 1.7000000476837158, 0.20999999344348907]
table_B[0].rotation = [0, 0, -1.5365673193683849]
table_B[0].optimize = 2
table_A[0].position = [3.5199999809265137, 3.950000047683716, 0.375]
table_A[0].rotation = [0, 0, -1.5359080495387476]
table_A[0].optimize = 2
chair_A[0].position = [2.6500000953674316, 0.550000011920929, 0.42500001192092896]
chair_A[0].rotation = [0, 0, 1.6053049998316455]
chair_A[0].optimize = 2

