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
    Wall(corner1=[0.04, 3.44, 0.00], corner2=[0.00, 3.40, 0.00]),
    Wall(corner1=[0.00, 3.40, 0.00], corner2=[0.00, 0.04, 0.00]),
    Wall(corner1=[0.00, 0.04, 0.00], corner2=[0.04, 0.00, 0.00]),
    Wall(corner1=[0.04, 0.00, 0.00], corner2=[3.40, 0.00, 0.00]),
    Wall(corner1=[3.40, 0.00, 0.00], corner2=[3.44, 0.04, 0.00]),
    Wall(corner1=[3.44, 0.04, 0.00], corner2=[3.44, 3.40, 0.00]),
    Wall(corner1=[3.44, 3.40, 0.00], corner2=[3.40, 3.44, 0.00]),
    Wall(corner1=[3.40, 3.44, 0.00], corner2=[0.04, 3.44, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
cup = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.60, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
bottle = Assets(description="bottle", size=[0.08, 0.08, 0.28], placements=[AssetInstance() for _ in range(1)])
washing_machine_A = Assets(description="washing machine", size=[0.65, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.60, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
cabinet_C = Assets(description="cabinet", size=[0.35, 0.60, 0.70], placements=[AssetInstance() for _ in range(1)])
sink = Assets(description="sink", size=[0.45, 0.55, 0.20], placements=[AssetInstance() for _ in range(1)])
cabinet_D = Assets(description="cabinet", size=[0.60, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
washing_machine_B = Assets(description="washing machine", size=[0.65, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
plant = Assets(description="plant", size=[0.25, 0.25, 0.40], placements=[AssetInstance() for _ in range(1)])
shelf = Assets(description="shelf", size=[0.30, 1.20, 0.04], placements=[AssetInstance() for _ in range(1)])

cup[0].instance_id = 'cup_0'
cabinet_A[0].instance_id = 'cabinet_A_0'
bottle[0].instance_id = 'bottle_0'
washing_machine_A[0].instance_id = 'washing_machine_A_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
cabinet_C[0].instance_id = 'cabinet_C_0'
sink[0].instance_id = 'sink_0'
cabinet_D[0].instance_id = 'cabinet_D_0'
washing_machine_B[0].instance_id = 'washing_machine_B_0'
plant[0].instance_id = 'plant_0'
shelf[0].instance_id = 'shelf_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

cup[0].position = [2.478907176965199, 0.7057146644858435, 0.055]
cup[0].rotation = [0, 0, 0]
cabinet_A[0].position = [0.5473294220091136, 3.0443316944816283, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
bottle[0].position = [2.96326008622175, 1.0923139426598993, 0.14]
bottle[0].rotation = [0, 0, 0]
washing_machine_A[0].position = [0.3293975812731018, 1.6784500630267054, 0.425]
washing_machine_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [2.23407928545115, 0.18782679654073595, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
cabinet_C[0].position = [1.1347820755229565, 3.3998083520759637, 0.35]
cabinet_C[0].rotation = [0, 0, 0]
sink[0].position = [2.3631696878021984, 2.163377787352748, 0.1]
sink[0].rotation = [0, 0, 0]
cabinet_D[0].position = [3.3224285124123254, 1.6525010802224167, 0.45]
cabinet_D[0].rotation = [0, 0, 0]
washing_machine_B[0].position = [1.0474138300906177, 0.0643727067537746, 0.425]
washing_machine_B[0].rotation = [0, 0, 0]
plant[0].position = [0.4527538690077517, 1.779621764539285, 0.2]
plant[0].rotation = [0, 0, 0]
shelf[0].position = [2.898758077479735, 2.8360033967883207, 0.02]
shelf[0].rotation = [0, 0, 0]
cup[0].position = [2.478907176965199, 0.7057146644858435, 0.055]
cup[0].rotation = [0, 0, 0]
cabinet_A[0].position = [0.5473294220091136, 3.0443316944816283, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
bottle[0].position = [2.96326008622175, 1.0923139426598993, 0.14]
bottle[0].rotation = [0, 0, 0]
washing_machine_A[0].position = [0.3293975812731018, 1.6784500630267054, 0.425]
washing_machine_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [2.23407928545115, 0.18782679654073595, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
cabinet_C[0].position = [1.1347820755229565, 3.3998083520759637, 0.35]
cabinet_C[0].rotation = [0, 0, 0]
sink[0].position = [2.3631696878021984, 2.163377787352748, 0.1]
sink[0].rotation = [0, 0, 0]
cabinet_D[0].position = [3.3224285124123254, 1.6525010802224167, 0.45]
cabinet_D[0].rotation = [0, 0, 0]
washing_machine_B[0].position = [1.0474138300906177, 0.0643727067537746, 0.425]
washing_machine_B[0].rotation = [0, 0, 0]
plant[0].position = [0.4527538690077517, 1.779621764539285, 0.2]
plant[0].rotation = [0, 0, 0]
shelf[0].position = [2.898758077479735, 2.8360033967883207, 0.02]
shelf[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the large appliances and cabinets along the bottom and left walls.
# This leaves the right side open as a circulation path to the door at
# (3.44, 1.54), while also keeping the window on the upper wall unobstructed.
cabinet_A[0].position = [0.34, 0.30, 0.45]
cabinet_A[0].rotation = [0, 0, radians(90)]

washing_machine_A[0].position = [0.965, 0.30, 0.425]
washing_machine_A[0].rotation = [0, 0, radians(90)]

cabinet_B[0].position = [1.59, 0.40, 0.45]
cabinet_B[0].rotation = [0, 0, radians(90)]

washing_machine_B[0].position = [2.215, 0.30, 0.425]
washing_machine_B[0].rotation = [0, 0, radians(90)]

# The deeper cabinet is placed on the left wall, facing into the room.
cabinet_D[0].position = [0.30, 1.30, 0.45]
cabinet_D[0].rotation = [0, 0, radians(0)]

# The smaller cabinet continues the storage run along the left wall.
cabinet_C[0].position = [0.175, 2.20, 0.35]
cabinet_C[0].rotation = [0, 0, radians(0)]

# The sink is centered on cabinet_B.
sink[0].position = [1.59, 0.40, 1.00]
sink[0].rotation = [0, 0, radians(90)]

# Use cabinet_D as the support for the long, shallow shelf. The shelf's
# 1.20 m dimension runs parallel to the left wall.
shelf[0].position = [0.30, 1.30, 0.92]
shelf[0].rotation = [0, 0, radians(0)]

# Separate the cup and bottle along the shelf so they do not overlap.
cup[0].position = [0.30, 1.05, 0.995]
cup[0].rotation = [0, 0, radians(0)]

bottle[0].position = [0.30, 1.55, 1.08]
bottle[0].rotation = [0, 0, radians(0)]

# The plant sits on the smaller cabinet, away from the door and window.
plant[0].position = [0.175, 2.20, 0.90]
plant[0].rotation = [0, 0, radians(0)]


# Fixed orientation references make the wall-facing directions explicit.
north_facing = AssetInstance(rotation=[0, 0, radians(90)])
east_facing = AssetInstance(rotation=[0, 0, radians(0)])

# High-priority position constraints preserve the non-overlapping layout.
solver.distance_constraint(
    cabinet_A[0], AssetInstance(position=[0.34, 0.30, 0.45]),
    0, 0, weight=10
)
solver.against_wall(cabinet_A[0], walls[3])
solver.align_with(cabinet_A[0], north_facing)

solver.distance_constraint(
    washing_machine_A[0], AssetInstance(position=[0.965, 0.30, 0.425]),
    0, 0, weight=10
)
solver.against_wall(washing_machine_A[0], walls[3])
solver.align_with(washing_machine_A[0], north_facing)

solver.distance_constraint(
    cabinet_B[0], AssetInstance(position=[1.59, 0.40, 0.45]),
    0, 0, weight=10
)
solver.against_wall(cabinet_B[0], walls[3])
solver.align_with(cabinet_B[0], north_facing)

solver.distance_constraint(
    washing_machine_B[0], AssetInstance(position=[2.215, 0.30, 0.425]),
    0, 0, weight=10
)
solver.against_wall(washing_machine_B[0], walls[3])
solver.align_with(washing_machine_B[0], north_facing)

solver.distance_constraint(
    cabinet_D[0], AssetInstance(position=[0.30, 1.30, 0.45]),
    0, 0, weight=10
)
solver.against_wall(cabinet_D[0], walls[1])
solver.align_with(cabinet_D[0], east_facing)

solver.distance_constraint(
    cabinet_C[0], AssetInstance(position=[0.175, 2.20, 0.35]),
    0, 0, weight=10
)
solver.against_wall(cabinet_C[0], walls[1])
solver.align_with(cabinet_C[0], east_facing)

# Supported assets receive both an on-top constraint and a position-based
# constraint so that their horizontal locations remain well defined.
solver.distance_constraint(
    sink[0], AssetInstance(position=[1.59, 0.40, 1.00]),
    0, 0, weight=10
)
solver.on_top_of(sink[0], cabinet_B[0])
solver.align_with(sink[0], cabinet_B[0])

solver.distance_constraint(
    shelf[0], AssetInstance(position=[0.30, 1.30, 0.92]),
    0, 0, weight=10
)
solver.on_top_of(shelf[0], cabinet_D[0])
solver.align_with(shelf[0], cabinet_D[0])

solver.distance_constraint(
    cup[0], AssetInstance(position=[0.30, 1.05, 0.995]),
    0, 0, weight=10
)
solver.on_top_of(cup[0], shelf[0])
solver.align_with(cup[0], shelf[0])

solver.distance_constraint(
    bottle[0], AssetInstance(position=[0.30, 1.55, 1.08]),
    0, 0, weight=10
)
solver.on_top_of(bottle[0], shelf[0])
solver.align_with(bottle[0], shelf[0])

solver.distance_constraint(
    plant[0], AssetInstance(position=[0.175, 2.20, 0.90]),
    0, 0, weight=10
)
solver.on_top_of(plant[0], cabinet_C[0])
solver.align_with(plant[0], cabinet_C[0])

solver.constraints = []
washing_machine_A[0].position = [0.9649999737739563, 0.3312038481235504, 0.42500001192092896]
washing_machine_A[0].rotation = [0, 0, 1.573337246167655]
washing_machine_A[0].optimize = 2
cabinet_D[0].position = [0.30349335074424744, 1.2999999523162842, 0.44999998807907104]
cabinet_D[0].rotation = [0, 0, 0.008762220955908069]
cabinet_D[0].optimize = 2
cup[0].position = [0.30000001192092896, 1.0499999523162842, 0.9949999451637268]
cup[0].rotation = [0, 0, 0.02278960013808119]
cup[0].optimize = 2
plant[0].position = [0.17499999701976776, 2.200000047683716, 0.8999999761581421]
plant[0].rotation = [0, 0, 0.02278736617577962]
plant[0].optimize = 2
sink[0].position = [1.590000033378601, 0.4000000059604645, 1.0]
sink[0].rotation = [0, 0, 1.5935836929706761]
sink[0].optimize = 2
washing_machine_B[0].position = [2.2149999141693115, 0.3312038481235504, 0.42500001192092896]
washing_machine_B[0].rotation = [0, 0, 1.573337246167655]
washing_machine_B[0].optimize = 2
cabinet_A[0].position = [0.3400000035762787, 0.300761342048645, 0.44999998807907104]
cabinet_A[0].rotation = [0, 0, 1.5733372452454815]
cabinet_A[0].optimize = 2
cabinet_B[0].position = [1.590000033378601, 0.39000004529953003, 0.44999998807907104]
cabinet_B[0].rotation = [0, 0, 1.5795585468286093]
cabinet_B[0].optimize = 2
bottle[0].position = [0.30000001192092896, 1.5499999523162842, 1.0799999237060547]
bottle[0].rotation = [0, 0, 0.02278960013808119]
bottle[0].optimize = 2
cabinet_C[0].position = [0.17762191593647003, 2.200000047683716, 0.3499999940395355]
cabinet_C[0].rotation = [0, 0, 0.008762222912431483]
cabinet_C[0].optimize = 2
shelf[0].position = [0.30000001192092896, 1.2999999523162842, 0.9199999570846558]
shelf[0].rotation = [0, 0, 0.014986366218674498]
shelf[0].optimize = 2

