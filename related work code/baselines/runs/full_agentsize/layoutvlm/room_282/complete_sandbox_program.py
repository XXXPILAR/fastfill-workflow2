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
    Wall(corner1=[3.86, 1.47, 0.00], corner2=[6.37, 1.47, 0.00]),
    Wall(corner1=[6.37, 1.47, 0.00], corner2=[6.37, 7.07, 0.00]),
    Wall(corner1=[6.37, 7.07, 0.00], corner2=[3.82, 7.07, 0.00]),
    Wall(corner1=[3.82, 7.07, 0.00], corner2=[3.82, 5.78, 0.00]),
    Wall(corner1=[3.82, 5.78, 0.00], corner2=[0.00, 5.78, 0.00]),
    Wall(corner1=[0.00, 5.78, 0.00], corner2=[0.00, 1.47, 0.00]),
    Wall(corner1=[0.00, 1.47, 0.00], corner2=[2.59, 1.47, 0.00]),
    Wall(corner1=[2.59, 1.47, 0.00], corner2=[2.59, 0.00, 0.00]),
    Wall(corner1=[2.59, 0.00, 0.00], corner2=[3.86, 0.00, 0.00]),
    Wall(corner1=[3.86, 0.00, 0.00], corner2=[3.86, 1.47, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
cabinet_A = Assets(description="cabinet", size=[0.45, 1.60, 0.85], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="chair", size=[0.78, 0.72, 0.86], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.42, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.78, 0.72, 0.86], placements=[AssetInstance() for _ in range(1)])
table_A = Assets(description="table", size=[0.60, 0.60, 0.55], placements=[AssetInstance() for _ in range(1)])
table_B = Assets(description="table", size=[0.70, 1.30, 0.42], placements=[AssetInstance() for _ in range(1)])
table_C = Assets(description="table", size=[0.50, 0.50, 0.50], placements=[AssetInstance() for _ in range(1)])
table_D = Assets(description="table", size=[0.60, 0.60, 0.55], placements=[AssetInstance() for _ in range(1)])
sofa_A = Assets(description="sofa", size=[0.95, 2.20, 0.85], placements=[AssetInstance() for _ in range(1)])
sofa_B = Assets(description="sofa", size=[1.00, 2.40, 0.88], placements=[AssetInstance() for _ in range(1)])

cabinet_A[0].instance_id = 'cabinet_A_0'
chair_A[0].instance_id = 'chair_A_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
chair_B[0].instance_id = 'chair_B_0'
table_A[0].instance_id = 'table_A_0'
table_B[0].instance_id = 'table_B_0'
table_C[0].instance_id = 'table_C_0'
table_D[0].instance_id = 'table_D_0'
sofa_A[0].instance_id = 'sofa_A_0'
sofa_B[0].instance_id = 'sofa_B_0'
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

cabinet_A[0].position = [3.693470050134326, 4.1733871924095585, 0.425]
cabinet_A[0].rotation = [0, 0, 0]
chair_A[0].position = [0.23758384133176827, 2.077794452200539, 0.43]
chair_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [4.990271316284795, 2.3638616223271027, 0.9]
cabinet_B[0].rotation = [0, 0, 0]
chair_B[0].position = [0.007178690274139959, 5.149676668222568, 0.43]
chair_B[0].rotation = [0, 0, 0]
table_A[0].position = [3.1210872322618033, 3.7762537609851643, 0.275]
table_A[0].rotation = [0, 0, 0]
table_B[0].position = [4.611730953926161, 4.000179975981471, 0.21]
table_B[0].rotation = [0, 0, 0]
table_C[0].position = [1.344409885502301, 5.751370629687511, 0.25]
table_C[0].rotation = [0, 0, 0]
table_D[0].position = [2.3854498519616065, 4.207841502223894, 0.275]
table_D[0].rotation = [0, 0, 0]
sofa_A[0].position = [2.662232849261974, 2.4906465729875356, 0.425]
sofa_A[0].rotation = [0, 0, 0]
sofa_B[0].position = [3.3015505144014305, 2.578682397689599, 0.44]
sofa_B[0].rotation = [0, 0, 0]
cabinet_A[0].position = [3.693470050134326, 4.1733871924095585, 0.425]
cabinet_A[0].rotation = [0, 0, 0]
chair_A[0].position = [0.23758384133176827, 2.077794452200539, 0.43]
chair_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [4.990271316284795, 2.3638616223271027, 0.9]
cabinet_B[0].rotation = [0, 0, 0]
chair_B[0].position = [0.007178690274139959, 5.149676668222568, 0.43]
chair_B[0].rotation = [0, 0, 0]
table_A[0].position = [3.1210872322618033, 3.7762537609851643, 0.275]
table_A[0].rotation = [0, 0, 0]
table_B[0].position = [4.611730953926161, 4.000179975981471, 0.21]
table_B[0].rotation = [0, 0, 0]
table_C[0].position = [1.344409885502301, 5.751370629687511, 0.25]
table_C[0].rotation = [0, 0, 0]
table_D[0].position = [2.3854498519616065, 4.207841502223894, 0.275]
table_D[0].rotation = [0, 0, 0]
sofa_A[0].position = [2.662232849261974, 2.4906465729875356, 0.425]
sofa_A[0].rotation = [0, 0, 0]
sofa_B[0].position = [3.3015505144014305, 2.578682397689599, 0.44]
sofa_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed placement targets keep the furniture in the intended functional zones.
# The upper seating group remains below the walls and clear of the large west
# doorway, while the lower-right group avoids the east doorway and the fixed
# structure centred at (5.13, 1.48).
cabinet_A_target = AssetInstance(
    position=[0.90, 1.695, 0.425],
    rotation=[0, 0, radians(90)],
)
cabinet_B_target = AssetInstance(
    position=[0.65, 5.57, 0.90],
    rotation=[0, 0, radians(90)],
)
chair_A_target = AssetInstance(
    position=[3.35, 2.75, 0.43],
    rotation=[0, 0, radians(0)],
)
chair_B_target = AssetInstance(
    position=[4.25, 3.95, 0.43],
    rotation=[0, 0, radians(-90)],
)
table_A_target = AssetInstance(
    position=[1.55, 5.20, 0.275],
    rotation=[0, 0, radians(-90)],
)
table_B_target = AssetInstance(
    position=[4.25, 2.75, 0.21],
    rotation=[0, 0, radians(0)],
)
table_C_target = AssetInstance(
    position=[2.05, 3.55, 0.25],
    rotation=[0, 0, radians(55)],
)
table_D_target = AssetInstance(
    position=[4.75, 5.20, 0.275],
    rotation=[0, 0, radians(-90)],
)
sofa_A_target = AssetInstance(
    position=[3.15, 5.20, 0.425],
    rotation=[0, 0, radians(-90)],
)
sofa_B_target = AssetInstance(
    position=[5.87, 2.75, 0.44],
    rotation=[0, 0, radians(180)],
)

# Specify complete initial placements. All z coordinates are half the
# corresponding asset heights because these objects stand on the floor.
cabinet_A[0].position = [0.90, 1.695, 0.425]
cabinet_A[0].rotation = [0, 0, radians(90)]

cabinet_B[0].position = [0.65, 5.57, 0.90]
cabinet_B[0].rotation = [0, 0, radians(90)]

chair_A[0].position = [3.35, 2.75, 0.43]
chair_A[0].rotation = [0, 0, radians(0)]

chair_B[0].position = [4.25, 3.95, 0.43]
chair_B[0].rotation = [0, 0, radians(-90)]

table_A[0].position = [1.55, 5.20, 0.275]
table_A[0].rotation = [0, 0, radians(-90)]

table_B[0].position = [4.25, 2.75, 0.21]
table_B[0].rotation = [0, 0, radians(0)]

table_C[0].position = [2.05, 3.55, 0.25]
table_C[0].rotation = [0, 0, radians(55)]

table_D[0].position = [4.75, 5.20, 0.275]
table_D[0].rotation = [0, 0, radians(-90)]

sofa_A[0].position = [3.15, 5.20, 0.425]
sofa_A[0].rotation = [0, 0, radians(-90)]

sofa_B[0].position = [5.87, 2.75, 0.44]
sofa_B[0].rotation = [0, 0, radians(180)]

# High-priority position constraints preserve the non-overlapping layout and
# keep all circulation areas in front of the seven doors unobstructed.
solver.distance_constraint(
    cabinet_A[0], cabinet_A_target, 0, 0, weight=10
)
solver.distance_constraint(
    cabinet_B[0], cabinet_B_target, 0, 0, weight=10
)
solver.distance_constraint(
    chair_A[0], chair_A_target, 0, 0, weight=10
)
solver.distance_constraint(
    chair_B[0], chair_B_target, 0, 0, weight=10
)
solver.distance_constraint(
    table_A[0], table_A_target, 0, 0, weight=10
)
solver.distance_constraint(
    table_B[0], table_B_target, 0, 0, weight=10
)
solver.distance_constraint(
    table_C[0], table_C_target, 0, 0, weight=10
)
solver.distance_constraint(
    table_D[0], table_D_target, 0, 0, weight=10
)
solver.distance_constraint(
    sofa_A[0], sofa_A_target, 0, 0, weight=10
)
solver.distance_constraint(
    sofa_B[0], sofa_B_target, 0, 0, weight=10
)

# Wall constraints keep the shallow sides of the cabinets flush with their
# respective walls. Sofa_B uses the uninterrupted lower part of the east wall,
# ending before the doorway centred at y=4.44.
solver.against_wall(cabinet_A[0], walls[6])
solver.against_wall(cabinet_B[0], walls[4])
solver.against_wall(sofa_B[0], walls[1])

# Cabinet orientation constraints ensure their broad backs remain parallel to
# the horizontal walls.
solver.align_with(cabinet_A[0], cabinet_A_target)
solver.align_with(cabinet_B[0], cabinet_B_target)

# Sofa_A is centred between table_A and table_D. The symmetric distance bounds
# preserve that relationship if physical-feasibility adjustment is required.
solver.distance_constraint(
    sofa_A[0], table_A[0], 1.55, 1.70, weight=10
)
solver.distance_constraint(
    sofa_A[0], table_D[0], 1.55, 1.70, weight=10
)
solver.distance_constraint(
    table_A[0], table_D[0], 3.10, 3.30, weight=1
)

# The upper sofa and its two end tables share an orientation. Sofa_A faces into
# the room, toward the lower part of the seating area.
sofa_A_view_target = AssetInstance(position=[3.15, 3.50, 0.425])
solver.point_towards(sofa_A[0], sofa_A_view_target)
solver.align_with(table_A[0], sofa_A[0])
solver.align_with(table_D[0], sofa_A[0])

# Sofa_B directly faces table_B as required. The table is parallel but oriented
# oppositely, producing a conventional face-to-face seating arrangement.
solver.point_towards(sofa_B[0], table_B[0])
solver.align_with(table_B[0], sofa_B[0], angle=180)
solver.distance_constraint(
    sofa_B[0], table_B[0], 1.55, 1.75, weight=10
)

# Both chairs serve table_B and are oriented toward it. Their target positions
# leave usable gaps around the table without overlapping either sofa.
solver.point_towards(chair_A[0], table_B[0])
solver.point_towards(chair_B[0], table_B[0])
solver.distance_constraint(
    chair_A[0], table_B[0], 0.85, 1.05, weight=1
)
solver.distance_constraint(
    chair_B[0], table_B[0], 1.10, 1.30, weight=1
)

# Table_C occupies the open central-left area and is oriented toward Sofa_A,
# making it accessible without intruding into the west-door circulation path.
solver.point_towards(table_C[0], sofa_A[0])
solver.distance_constraint(
    table_C[0], sofa_A[0], 1.85, 2.15, weight=1
)

solver.constraints = []
cabinet_A[0].position = [0.8999999761581421, 1.7052500247955322, 0.42500001192092896]
cabinet_A[0].rotation = [0, 0, 1.5707949921215294]
cabinet_A[0].optimize = 2
table_D[0].position = [4.75, 5.199999809265137, 0.2750000059604645]
table_D[0].rotation = [0, 0, -1.542523373960234]
table_D[0].optimize = 2
cabinet_B[0].position = [0.6499999761581421, 5.50401496887207, 0.8999999761581421]
cabinet_B[0].rotation = [0, 0, -1.675421007956088]
cabinet_B[0].optimize = 2
chair_B[0].position = [4.25, 3.950000047683716, 0.4300000071525574]
chair_B[0].rotation = [0, 0, -1.5582299555380688]
chair_B[0].optimize = 2
chair_A[0].position = [3.3499999046325684, 2.75, 0.4300000071525574]
chair_A[0].rotation = [0, 0, 0.01256637125682779]
chair_A[0].optimize = 2
table_A[0].position = [1.5499999523162842, 5.199999809265137, 0.2750000059604645]
table_A[0].rotation = [0, 0, -1.542523373960234]
table_A[0].optimize = 2
table_B[0].position = [4.25, 2.75, 0.20999999344348907]
table_B[0].rotation = [0, 0, 3.933320361244313e-06]
table_B[0].optimize = 2
sofa_B[0].position = [5.872790813446045, 2.75, 0.4399999976158142]
sofa_B[0].rotation = [0, 0, -3.141592279782444]
sofa_B[0].optimize = 2
sofa_A[0].position = [3.1500000953674316, 5.199999809265137, 0.42500001192092896]
sofa_A[0].rotation = [0, 0, -1.5425219923833045]
sofa_A[0].optimize = 2
table_C[0].position = [2.049999952316284, 3.549999952316284, 0.25]
table_C[0].rotation = [0, 0, 0.9724974504614351]
table_C[0].optimize = 2

