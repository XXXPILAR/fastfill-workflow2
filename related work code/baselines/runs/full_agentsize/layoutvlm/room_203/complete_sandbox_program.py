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
    Wall(corner1=[0.00, 5.78, 0.00], corner2=[0.00, 3.80, 0.00]),
    Wall(corner1=[0.00, 3.80, 0.00], corner2=[1.74, 3.80, 0.00]),
    Wall(corner1=[1.74, 3.80, 0.00], corner2=[1.74, 0.00, 0.00]),
    Wall(corner1=[1.74, 0.00, 0.00], corner2=[6.60, 0.00, 0.00]),
    Wall(corner1=[6.60, 0.00, 0.00], corner2=[6.60, 3.45, 0.00]),
    Wall(corner1=[6.60, 3.45, 0.00], corner2=[7.70, 3.45, 0.00]),
    Wall(corner1=[7.70, 3.45, 0.00], corner2=[7.70, 4.90, 0.00]),
    Wall(corner1=[7.70, 4.90, 0.00], corner2=[6.80, 4.90, 0.00]),
    Wall(corner1=[6.80, 4.90, 0.00], corner2=[6.80, 4.83, 0.00]),
    Wall(corner1=[6.80, 4.83, 0.00], corner2=[3.46, 4.83, 0.00]),
    Wall(corner1=[3.46, 4.83, 0.00], corner2=[3.46, 4.92, 0.00]),
    Wall(corner1=[3.46, 4.92, 0.00], corner2=[0.99, 4.92, 0.00]),
    Wall(corner1=[0.99, 4.92, 0.00], corner2=[0.99, 5.78, 0.00]),
    Wall(corner1=[0.99, 5.78, 0.00], corner2=[0.00, 5.78, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
coffee_table = Assets(description="coffee table", size=[0.60, 1.20, 0.42], placements=[AssetInstance() for _ in range(1)])
tv_cabinet_A = Assets(description="tv cabinet", size=[0.42, 1.80, 0.55], placements=[AssetInstance() for _ in range(1)])
air_conditioner = Assets(description="air conditioner", size=[0.22, 0.90, 0.30], placements=[AssetInstance() for _ in range(1)])
tv_cabinet_B = Assets(description="tv cabinet", size=[0.45, 2.00, 0.55], placements=[AssetInstance() for _ in range(1)])
sofa = Assets(description="sofa", size=[0.95, 2.40, 0.85], placements=[AssetInstance() for _ in range(1)])
ornaments_A = Assets(description="ornaments", size=[0.16, 0.22, 0.35], placements=[AssetInstance() for _ in range(1)])
ornaments_B = Assets(description="ornaments", size=[0.14, 0.18, 0.28], placements=[AssetInstance() for _ in range(1)])

coffee_table[0].instance_id = 'coffee_table_0'
tv_cabinet_A[0].instance_id = 'tv_cabinet_A_0'
air_conditioner[0].instance_id = 'air_conditioner_0'
tv_cabinet_B[0].instance_id = 'tv_cabinet_B_0'
sofa[0].instance_id = 'sofa_0'
ornaments_A[0].instance_id = 'ornaments_A_0'
ornaments_B[0].instance_id = 'ornaments_B_0'
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
walls[12].instance_id = 'walls_12'
walls[13].instance_id = 'walls_13'

coffee_table[0].position = [4.964888564877496, 1.8818657345145884, 0.21]
coffee_table[0].rotation = [0, 0, 0]
tv_cabinet_A[0].position = [1.8343869684016076, 3.257951501049107, 0.275]
tv_cabinet_A[0].rotation = [0, 0, 0]
air_conditioner[0].position = [3.0258753033279593, 0.4248286129216094, 0.15]
air_conditioner[0].rotation = [0, 0, 0]
tv_cabinet_B[0].position = [3.336133983971404, 2.478528264156119, 0.275]
tv_cabinet_B[0].rotation = [0, 0, 0]
sofa[0].position = [5.527723803399815, 2.751408707282135, 0.425]
sofa[0].rotation = [0, 0, 0]
ornaments_A[0].position = [6.9708704829923605, 4.690929700410925, 0.175]
ornaments_A[0].rotation = [0, 0, 0]
ornaments_B[0].position = [3.8075211907696693, 4.723112031031681, 0.14]
ornaments_B[0].rotation = [0, 0, 0]
coffee_table[0].position = [4.964888564877496, 1.8818657345145884, 0.21]
coffee_table[0].rotation = [0, 0, 0]
tv_cabinet_A[0].position = [1.8343869684016076, 3.257951501049107, 0.275]
tv_cabinet_A[0].rotation = [0, 0, 0]
air_conditioner[0].position = [3.0258753033279593, 0.4248286129216094, 0.15]
air_conditioner[0].rotation = [0, 0, 0]
tv_cabinet_B[0].position = [3.336133983971404, 2.478528264156119, 0.275]
tv_cabinet_B[0].rotation = [0, 0, 0]
sofa[0].position = [5.527723803399815, 2.751408707282135, 0.425]
sofa[0].rotation = [0, 0, 0]
ornaments_A[0].position = [6.9708704829923605, 4.690929700410925, 0.175]
ornaments_A[0].rotation = [0, 0, 0]
ornaments_B[0].position = [3.8075211907696693, 4.723112031031681, 0.14]
ornaments_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the seating group along the room's lower and upper walls. The sofa
# faces north toward tv_cabinet_B (o0003), with the coffee table between them.
sofa[0].position = [5.20, 0.475, 0.425]
sofa[0].rotation = [0, 0, radians(90)]

tv_cabinet_B[0].position = [5.20, 4.605, 0.275]
tv_cabinet_B[0].rotation = [0, 0, radians(-90)]

coffee_table[0].position = [5.20, 1.65, 0.21]
coffee_table[0].rotation = [0, 0, radians(90)]

# Place tv_cabinet_A (o0001) against the long left wall, facing into the room.
tv_cabinet_A[0].position = [1.95, 2.10, 0.275]
tv_cabinet_A[0].rotation = [0, 0, radians(0)]

# Mount the air conditioner high on the same wall. Its elevation keeps it
# vertically clear of the cabinet while preserving open circulation below.
air_conditioner[0].position = [1.85, 3.30, 2.35]
air_conditioner[0].rotation = [0, 0, radians(0)]

# Center one ornament on each cabinet. Their z coordinates correspond to the
# top surfaces of their supporting cabinets.
ornaments_A[0].position = [1.95, 2.10, 0.725]
ornaments_A[0].rotation = [0, 0, radians(0)]

ornaments_B[0].position = [5.20, 4.605, 0.690]
ornaments_B[0].rotation = [0, 0, radians(-90)]


# --- Primary wall and facing constraints ---

# The requested cabinet o0001 is against the left wall and oriented into the room.
solver.against_wall(tv_cabinet_A[0], walls[2])
solver.point_towards(
    tv_cabinet_A[0],
    AssetInstance(position=[4.00, 2.10, 0.275])
)

# Keep the main TV cabinet against the upper wall. Both it and the sofa face
# each other, establishing the requested viewing arrangement.
solver.against_wall(tv_cabinet_B[0], walls[9])
solver.point_towards(tv_cabinet_B[0], sofa[0])

solver.against_wall(sofa[0], walls[3])
solver.point_towards(sofa[0], tv_cabinet_B[0])
solver.distance_constraint(
    sofa[0], tv_cabinet_B[0],
    min_distance=3.90, max_distance=4.35, weight=10
)

# Anchor the coffee table on the centerline of the seating group and keep its
# long direction parallel to the sofa.
coffee_table_anchor = AssetInstance(position=[5.20, 1.65, 0.21])
solver.distance_constraint(
    coffee_table[0], coffee_table_anchor,
    min_distance=0, max_distance=0, weight=10
)
solver.align_with(coffee_table[0], sofa[0])
solver.distance_constraint(
    coffee_table[0], sofa[0],
    min_distance=1.05, max_distance=1.35, weight=5
)
solver.distance_constraint(
    coffee_table[0], tv_cabinet_B[0],
    min_distance=2.75, max_distance=3.20, weight=2
)

# The air conditioner remains attached to the left wall and faces inward.
solver.against_wall(air_conditioner[0], walls[2])
solver.point_towards(
    air_conditioner[0],
    AssetInstance(position=[4.00, 3.30, 2.35])
)
air_conditioner_anchor = AssetInstance(position=[1.85, 3.30, 2.35])
solver.distance_constraint(
    air_conditioner[0], air_conditioner_anchor,
    min_distance=0, max_distance=0, weight=10
)

# --- Ornament support, position, and orientation constraints ---

# The center-to-center distances equal the required vertical offsets when each
# ornament is centered on its supporting cabinet.
solver.on_top_of(ornaments_A[0], tv_cabinet_A[0])
solver.distance_constraint(
    ornaments_A[0], tv_cabinet_A[0],
    min_distance=0.45, max_distance=0.45, weight=10
)
solver.align_with(ornaments_A[0], tv_cabinet_A[0])

solver.on_top_of(ornaments_B[0], tv_cabinet_B[0])
solver.distance_constraint(
    ornaments_B[0], tv_cabinet_B[0],
    min_distance=0.415, max_distance=0.415, weight=10
)
solver.align_with(ornaments_B[0], tv_cabinet_B[0])

solver.constraints = []
sofa[0].position = [5.199999809265137, 0.47323697805404663, 0.42500001192092896]
sofa[0].rotation = [0, 0, 1.5690227192779873]
sofa[0].optimize = 2
tv_cabinet_A[0].position = [1.9508886337280273, 2.0999999046325684, 0.2750000059604645]
tv_cabinet_A[0].rotation = [0, 0, -0.000712824541910986]
tv_cabinet_A[0].optimize = 2
ornaments_B[0].position = [5.199999809265137, 4.7563157081604, 0.6899999976158142]
ornaments_B[0].rotation = [0, 0, -1.578809712201082]
ornaments_B[0].optimize = 2
tv_cabinet_B[0].position = [5.199999809265137, 4.6027512550354, 0.2750000059604645]
tv_cabinet_B[0].rotation = [0, 0, -1.5693540070767633]
tv_cabinet_B[0].optimize = 2
ornaments_A[0].position = [1.8192596435546875, 2.0999999046325684, 0.7250000238418579]
ornaments_A[0].rotation = [0, 0, 0.0012742178967808393]
ornaments_A[0].optimize = 2
air_conditioner[0].position = [1.8485862016677856, 3.299999952316284, 0.15000000596046448]
air_conditioner[0].rotation = [0, 0, -0.00010882404962054544]
air_conditioner[0].optimize = 2
coffee_table[0].position = [5.199999809265137, 1.649999976158142, 0.20999999344348907]
coffee_table[0].rotation = [0, 0, 1.5700544695119094]
coffee_table[0].optimize = 2

