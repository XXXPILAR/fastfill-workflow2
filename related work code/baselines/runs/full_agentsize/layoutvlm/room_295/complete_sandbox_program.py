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
table_A = Assets(description="table", size=[0.40, 1.40, 0.76], placements=[AssetInstance() for _ in range(1)])
sofa = Assets(description="sofa", size=[0.95, 2.20, 0.85], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="chair", size=[0.80, 0.75, 0.85], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.80, 0.75, 0.85], placements=[AssetInstance() for _ in range(1)])
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

table_A[0].position = [3.7123031780999947, 5.3423920104435245, 0.38]
table_A[0].rotation = [0, 0, 0]
sofa[0].position = [2.718468588671878, 5.909107761995682, 0.425]
sofa[0].rotation = [0, 0, 0]
chair_A[0].position = [3.8540980514896392, 2.383629476341736, 0.425]
chair_A[0].rotation = [0, 0, 0]
chair_B[0].position = [3.3143480870336464, 2.4277509926858363, 0.425]
chair_B[0].rotation = [0, 0, 0]
table_B[0].position = [4.6741530000466085, 4.151277253174702, 0.21]
table_B[0].rotation = [0, 0, 0]
table_A[0].position = [3.7123031780999947, 5.3423920104435245, 0.38]
table_A[0].rotation = [0, 0, 0]
sofa[0].position = [2.718468588671878, 5.909107761995682, 0.425]
sofa[0].rotation = [0, 0, 0]
chair_A[0].position = [3.8540980514896392, 2.383629476341736, 0.425]
chair_A[0].rotation = [0, 0, 0]
chair_B[0].position = [3.3143480870336464, 2.4277509926858363, 0.425]
chair_B[0].rotation = [0, 0, 0]
table_B[0].position = [4.6741530000466085, 4.151277253174702, 0.21]
table_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the furniture in the lower rectangular portion of the room.
# The composition runs from west to east as:
# table_A -> sofa -> table_B, satisfying the requirement that the sofa is
# between the two tables. The chairs flank table_B while leaving circulation
# space toward the doors and the window unobstructed.

table_A[0].position = [2.28, 2.40, 0.38]
table_A[0].rotation = [0, 0, radians(0)]

sofa[0].position = [3.05, 2.40, 0.425]
sofa[0].rotation = [0, 0, radians(0)]

table_B[0].position = [4.30, 2.40, 0.21]
table_B[0].rotation = [0, 0, radians(0)]

chair_A[0].position = [4.30, 1.30, 0.425]
chair_A[0].rotation = [0, 0, radians(90)]

chair_B[0].position = [4.30, 3.50, 0.425]
chair_B[0].rotation = [0, 0, radians(-90)]


# Fixed placement references preserve the collision-free arrangement while
# still allowing the solver to reconcile the relational constraints below.
table_A_anchor = AssetInstance(position=[2.28, 2.40, 0.38])
sofa_anchor = AssetInstance(position=[3.05, 2.40, 0.425])
table_B_anchor = AssetInstance(position=[4.30, 2.40, 0.21])
chair_A_anchor = AssetInstance(position=[4.30, 1.30, 0.425])
chair_B_anchor = AssetInstance(position=[4.30, 3.50, 0.425])

solver.distance_constraint(
    table_A[0], table_A_anchor, 0.0, 0.0, weight=10
)
solver.distance_constraint(
    sofa[0], sofa_anchor, 0.0, 0.0, weight=10
)
solver.distance_constraint(
    table_B[0], table_B_anchor, 0.0, 0.0, weight=10
)
solver.distance_constraint(
    chair_A[0], chair_A_anchor, 0.0, 0.0, weight=10
)
solver.distance_constraint(
    chair_B[0], chair_B_anchor, 0.0, 0.0, weight=10
)


# Keep the narrow table against the west wall of the lower room, where it
# functions as a console without blocking the window or any doorway.
solver.against_wall(table_A[0], walls[4])
solver.align_with(table_A[0], sofa[0])


# Preserve the west-to-east sequence table_A -> sofa -> table_B.
# The center distances include sufficient clearance between bounding boxes.
solver.distance_constraint(
    sofa[0], table_A[0], 0.75, 0.90, weight=5
)
solver.distance_constraint(
    sofa[0], table_B[0], 1.20, 1.35, weight=5
)

# The sofa's front points east toward table_B as explicitly requested.
solver.point_towards(sofa[0], table_B[0])
solver.align_with(table_B[0], sofa[0])


# Place one chair on each side of table_B, with both chairs facing it.
# Their distances provide usable seating clearance without overlapping the
# table, sofa, walls, or the circulation route toward the doors.
solver.distance_constraint(
    chair_A[0], table_B[0], 1.05, 1.15, weight=5
)
solver.point_towards(chair_A[0], table_B[0])

solver.distance_constraint(
    chair_B[0], table_B[0], 1.05, 1.15, weight=5
)
solver.point_towards(chair_B[0], table_B[0])

# Maintain the balanced opposing-chair arrangement.
solver.distance_constraint(
    chair_A[0], chair_B[0], 2.15, 2.25, weight=2
)
solver.align_with(chair_B[0], chair_A[0], angle=180)

solver.constraints = []
sofa[0].position = [3.049999952316284, 2.4000000953674316, 0.42500001192092896]
sofa[0].rotation = [0, 0, 0.021991148286022624]
sofa[0].optimize = 2
chair_B[0].position = [4.300000190734863, 3.5, 0.42500001192092896]
chair_B[0].rotation = [0, 0, -1.5519466674934148]
chair_B[0].optimize = 2
chair_A[0].position = [4.300000190734863, 1.2999999523162842, 0.42500001192092896]
chair_A[0].rotation = [0, 0, 1.589645882193713]
chair_A[0].optimize = 2
table_A[0].position = [2.2561519145965576, 2.4000000953674316, 0.3799999952316284]
table_A[0].rotation = [0, 0, 1.1690596765143953e-07]
table_A[0].optimize = 2
table_B[0].position = [4.300000190734863, 2.4000000953674316, 0.20999999344348907]
table_B[0].rotation = [0, 0, 0.021991143478238915]
table_B[0].optimize = 2

