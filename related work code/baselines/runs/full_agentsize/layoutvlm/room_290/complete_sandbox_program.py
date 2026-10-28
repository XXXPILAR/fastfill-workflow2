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
    Wall(corner1=[8.70, 0.00, 0.00], corner2=[8.70, 1.50, 0.00]),
    Wall(corner1=[8.70, 1.50, 0.00], corner2=[8.87, 1.50, 0.00]),
    Wall(corner1=[8.87, 1.50, 0.00], corner2=[8.87, 2.24, 0.00]),
    Wall(corner1=[8.87, 2.24, 0.00], corner2=[5.61, 2.24, 0.00]),
    Wall(corner1=[5.61, 2.24, 0.00], corner2=[5.61, 3.14, 0.00]),
    Wall(corner1=[5.61, 3.14, 0.00], corner2=[0.00, 3.14, 0.00]),
    Wall(corner1=[0.00, 3.14, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[8.70, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
cabinet_A = Assets(description="cabinet", size=[0.40, 1.20, 0.85], placements=[AssetInstance() for _ in range(1)])
table_A = Assets(description="table", size=[0.70, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
chair = Assets(description="chair", size=[0.55, 0.50, 0.85], placements=[AssetInstance() for _ in range(1)])
table_B = Assets(description="table", size=[0.50, 0.90, 0.45], placements=[AssetInstance() for _ in range(1)])
table_C = Assets(description="table", size=[0.50, 0.50, 0.50], placements=[AssetInstance() for _ in range(1)])
table_D = Assets(description="table", size=[0.70, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
sofa = Assets(description="sofa", size=[0.90, 2.10, 0.85], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.45, 1.50, 0.90], placements=[AssetInstance() for _ in range(1)])
cabinet_C = Assets(description="cabinet", size=[0.40, 0.80, 1.80], placements=[AssetInstance() for _ in range(1)])

cabinet_A[0].instance_id = 'cabinet_A_0'
table_A[0].instance_id = 'table_A_0'
chair[0].instance_id = 'chair_0'
table_B[0].instance_id = 'table_B_0'
table_C[0].instance_id = 'table_C_0'
table_D[0].instance_id = 'table_D_0'
sofa[0].instance_id = 'sofa_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
cabinet_C[0].instance_id = 'cabinet_C_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

cabinet_A[0].position = [7.847833005539515, 1.3341577972609127, 0.425]
cabinet_A[0].rotation = [0, 0, 0]
table_A[0].position = [2.5428000751659474, 2.6797711540594165, 0.375]
table_A[0].rotation = [0, 0, 0]
chair[0].position = [0.3452127285092025, 1.8893142013794564, 0.425]
chair[0].rotation = [0, 0, 0]
table_B[0].position = [2.0686376908417206, 0.5694462061699976, 0.225]
table_B[0].rotation = [0, 0, 0]
table_C[0].position = [0.8399481482465083, 1.4662136178884968, 0.25]
table_C[0].rotation = [0, 0, 0]
table_D[0].position = [5.537621565124157, 0.7311920929107071, 0.375]
table_D[0].rotation = [0, 0, 0]
sofa[0].position = [2.5564802641988194, 2.4808679047166278, 0.425]
sofa[0].rotation = [0, 0, 0]
cabinet_B[0].position = [8.299745588969918, 0.325152142823828, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
cabinet_C[0].position = [0.4471561096708452, 2.202127287183382, 0.9]
cabinet_C[0].rotation = [0, 0, 0]
cabinet_A[0].position = [7.847833005539515, 1.3341577972609127, 0.425]
cabinet_A[0].rotation = [0, 0, 0]
table_A[0].position = [2.5428000751659474, 2.6797711540594165, 0.375]
table_A[0].rotation = [0, 0, 0]
chair[0].position = [0.3452127285092025, 1.8893142013794564, 0.425]
chair[0].rotation = [0, 0, 0]
table_B[0].position = [2.0686376908417206, 0.5694462061699976, 0.225]
table_B[0].rotation = [0, 0, 0]
table_C[0].position = [0.8399481482465083, 1.4662136178884968, 0.25]
table_C[0].rotation = [0, 0, 0]
table_D[0].position = [5.537621565124157, 0.7311920929107071, 0.375]
table_D[0].rotation = [0, 0, 0]
sofa[0].position = [2.5564802641988194, 2.4808679047166278, 0.425]
sofa[0].rotation = [0, 0, 0]
cabinet_B[0].position = [8.299745588969918, 0.325152142823828, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
cabinet_C[0].position = [0.4471561096708452, 2.202127287183382, 0.9]
cabinet_C[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the main seating group in the wider left portion of the room. The chair
# lies between the two full-height tables and faces the cabinet on the north wall.
cabinet_A[0].position = [2.20, 2.94, 0.425]
cabinet_A[0].rotation = [0, 0, radians(-90)]

table_A[0].position = [1.50, 1.50, 0.375]
table_A[0].rotation = [0, 0, radians(0)]

chair[0].position = [2.20, 1.50, 0.425]
chair[0].rotation = [0, 0, radians(90)]

table_D[0].position = [2.85, 1.50, 0.375]
table_D[0].rotation = [0, 0, radians(0)]

# Place the smaller tables beyond the seating group while leaving the approach
# to the two doors on the north wall clear.
table_B[0].position = [3.80, 1.00, 0.225]
table_B[0].rotation = [0, 0, radians(90)]

table_C[0].position = [4.35, 1.80, 0.25]
table_C[0].rotation = [0, 0, radians(0)]

# The sofa is placed along the long south wall, facing into the room. Its east
# end remains well short of the doors in the stepped and right-hand walls.
sofa[0].position = [6.40, 0.45, 0.425]
sofa[0].rotation = [0, 0, radians(90)]

# Use the remaining wall areas for storage. Cabinet B occupies the south wall
# between the central furniture and sofa; cabinet C occupies the northwest
# corner without obstructing the large door in the west wall.
cabinet_B[0].position = [4.40, 0.225, 0.45]
cabinet_B[0].rotation = [0, 0, radians(90)]

cabinet_C[0].position = [0.50, 2.94, 0.90]
cabinet_C[0].rotation = [0, 0, radians(-90)]


# Fixed layout references let the solver preserve the selected door clearances
# and the deliberately non-overlapping arrangement.
cabinet_A_anchor = AssetInstance(
    position=[2.20, 2.94, 0.425],
    rotation=[0, 0, radians(-90)],
)
table_A_anchor = AssetInstance(
    position=[1.50, 1.50, 0.375],
    rotation=[0, 0, radians(0)],
)
chair_anchor = AssetInstance(
    position=[2.20, 1.50, 0.425],
    rotation=[0, 0, radians(90)],
)
table_B_anchor = AssetInstance(
    position=[3.80, 1.00, 0.225],
    rotation=[0, 0, radians(90)],
)
table_C_anchor = AssetInstance(
    position=[4.35, 1.80, 0.25],
    rotation=[0, 0, radians(0)],
)
table_D_anchor = AssetInstance(
    position=[2.85, 1.50, 0.375],
    rotation=[0, 0, radians(0)],
)
sofa_anchor = AssetInstance(
    position=[6.40, 0.45, 0.425],
    rotation=[0, 0, radians(90)],
)
cabinet_B_anchor = AssetInstance(
    position=[4.40, 0.225, 0.45],
    rotation=[0, 0, radians(90)],
)
cabinet_C_anchor = AssetInstance(
    position=[0.50, 2.94, 0.90],
    rotation=[0, 0, radians(-90)],
)


# The chair-facing relation is the most important orientation constraint.
solver.point_towards(chair[0], cabinet_A[0])
solver.align_with(chair[0], chair_anchor)

# At these rotations, table A and the chair occupy 0.70 m and 0.50 m along
# the x-axis. Their half-widths total 0.60 m, so a center distance no greater
# than 0.90 m represents no more than 0.30 m of edge-to-edge clearance while
# still avoiding bounding-box overlap.
solver.distance_constraint(
    chair[0], table_A[0],
    min_distance=0.60,
    max_distance=0.90,
    weight=10,
)

# Keeping the chair close to table D on its other side preserves the requested
# ordering: table A -- chair -- table D.
solver.distance_constraint(
    chair[0], table_D[0],
    min_distance=0.60,
    max_distance=0.85,
    weight=10,
)

# Position references preserve the chosen left-to-right ordering and keep all
# three members of the seating group away from door approaches.
solver.distance_constraint(chair[0], chair_anchor, 0, 0, weight=10)
solver.distance_constraint(table_A[0], table_A_anchor, 0, 0, weight=10)
solver.align_with(table_A[0], table_A_anchor)
solver.distance_constraint(table_D[0], table_D_anchor, 0, 0, weight=10)
solver.align_with(table_D[0], table_D_anchor)

# Cabinet A is flush with the north wall and faces inward toward the chair.
solver.against_wall(cabinet_A[0], walls[5])
solver.distance_constraint(cabinet_A[0], cabinet_A_anchor, 0, 0, weight=10)
solver.align_with(cabinet_A[0], cabinet_A_anchor)

# Maintain the positions and orientations of the two auxiliary tables.
solver.distance_constraint(table_B[0], table_B_anchor, 0, 0, weight=10)
solver.align_with(table_B[0], table_B_anchor)
solver.distance_constraint(table_C[0], table_C_anchor, 0, 0, weight=10)
solver.align_with(table_C[0], table_C_anchor)

# Wall constraints keep the sofa and remaining cabinets flush with their
# respective walls; the anchors select safe portions of those walls.
solver.against_wall(sofa[0], walls[7])
solver.distance_constraint(sofa[0], sofa_anchor, 0, 0, weight=10)
solver.align_with(sofa[0], sofa_anchor)

solver.against_wall(cabinet_B[0], walls[7])
solver.distance_constraint(cabinet_B[0], cabinet_B_anchor, 0, 0, weight=10)
solver.align_with(cabinet_B[0], cabinet_B_anchor)

solver.against_wall(cabinet_C[0], walls[5])
solver.distance_constraint(cabinet_C[0], cabinet_C_anchor, 0, 0, weight=10)
solver.align_with(cabinet_C[0], cabinet_C_anchor)

solver.constraints = []
cabinet_A[0].position = [2.200000047683716, 2.939997911453247, 0.42500001192092896]
cabinet_A[0].rotation = [0, 0, -1.5707962695809035]
cabinet_A[0].optimize = 2
sofa[0].position = [6.407962322235107, 0.45019155740737915, 0.42500001192092896]
sofa[0].rotation = [0, 0, 1.570826246069054]
sofa[0].optimize = 2
table_D[0].position = [2.8499999046325684, 1.5, 0.375]
table_D[0].rotation = [0, 0, 0.01256637125682779]
table_D[0].optimize = 2
cabinet_B[0].position = [4.404148578643799, 0.22513166069984436, 0.44999998807907104]
cabinet_B[0].rotation = [0, 0, 1.5708262545971898]
cabinet_B[0].optimize = 2
cabinet_C[0].position = [0.5, 2.939997673034668, 0.8999999761581421]
cabinet_C[0].rotation = [0, 0, -1.5707962966523759]
cabinet_C[0].optimize = 2
chair[0].position = [2.200000047683716, 1.5, 0.42500001192092896]
chair[0].rotation = [0, 0, 1.589645882193713]
chair[0].optimize = 2
table_A[0].position = [1.5, 1.5, 0.375]
table_A[0].rotation = [0, 0, 0.01256637125682779]
table_A[0].optimize = 2
table_B[0].position = [3.799999952316284, 1.0, 0.22499999403953552]
table_B[0].rotation = [0, 0, 1.5802211042556205]
table_B[0].optimize = 2
table_C[0].position = [4.349999904632568, 1.7999999523162842, 0.25]
table_C[0].rotation = [0, 0, 0.00942477746072377]
table_C[0].optimize = 2

