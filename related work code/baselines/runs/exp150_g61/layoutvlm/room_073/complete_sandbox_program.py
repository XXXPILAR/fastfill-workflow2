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
    Wall(corner1=[4.26, 0.00, 0.00], corner2=[4.26, 2.26, 0.00]),
    Wall(corner1=[4.26, 2.26, 0.00], corner2=[0.00, 2.26, 0.00]),
    Wall(corner1=[0.00, 2.26, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.26, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bottle_A = Assets(description="bottle", size=[0.08, 0.08, 0.23], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.40, 0.65, 1.80], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="bottle", size=[0.07, 0.07, 0.20], placements=[AssetInstance() for _ in range(1)])
pot = Assets(description="pot", size=[0.18, 0.18, 0.16], placements=[AssetInstance() for _ in range(1)])
lamp = Assets(description="lamp", size=[0.20, 0.16, 0.28], placements=[AssetInstance() for _ in range(1)])
book = Assets(description="book", size=[0.23, 0.16, 0.03], placements=[AssetInstance() for _ in range(1)])
toilet = Assets(description="toilet", size=[0.70, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
bottle_C = Assets(description="bottle", size=[0.07, 0.08, 0.18], placements=[AssetInstance() for _ in range(1)])
sink = Assets(description="sink", size=[0.44, 0.58, 0.18], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.50, 0.90, 0.72], placements=[AssetInstance() for _ in range(1)])
shelf = Assets(description="shelf", size=[0.20, 0.65, 0.04], placements=[AssetInstance() for _ in range(1)])

bottle_A[0].instance_id = 'bottle_A_0'
cabinet_A[0].instance_id = 'cabinet_A_0'
bottle_B[0].instance_id = 'bottle_B_0'
pot[0].instance_id = 'pot_0'
lamp[0].instance_id = 'lamp_0'
book[0].instance_id = 'book_0'
toilet[0].instance_id = 'toilet_0'
bottle_C[0].instance_id = 'bottle_C_0'
sink[0].instance_id = 'sink_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
shelf[0].instance_id = 'shelf_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

bottle_A[0].position = [2.124113948922353, 1.6500024061858374, 0.115]
bottle_A[0].rotation = [0, 0, 0]
cabinet_A[0].position = [1.9044511379961413, 2.1821058993595814, 0.9]
cabinet_A[0].rotation = [0, 0, 0]
bottle_B[0].position = [1.9284461537254443, 1.9454432002177038, 0.1]
bottle_B[0].rotation = [0, 0, 0]
pot[0].position = [1.6189450344219238, 1.4770221614017662, 0.08]
pot[0].rotation = [0, 0, 0]
lamp[0].position = [0.735424073070024, 0.3798103393262876, 0.14]
lamp[0].rotation = [0, 0, 0]
book[0].position = [2.6288753097832505, 0.17208832104048935, 0.0125]
book[0].rotation = [0, 0, 0]
toilet[0].position = [0.13344598841958638, 1.252196082679183, 0.39]
toilet[0].rotation = [0, 0, 0]
bottle_C[0].position = [0.019225442454579408, 0.5488729318915231, 0.09]
bottle_C[0].rotation = [0, 0, 0]
sink[0].position = [1.9134945028769366, 2.238025682127968, 0.09]
sink[0].rotation = [0, 0, 0]
cabinet_B[0].position = [3.2299480749058906, 1.0702665121652473, 0.36]
cabinet_B[0].rotation = [0, 0, 0]
shelf[0].position = [3.2118401294278187, 0.9355422575386674, 0.02]
shelf[0].rotation = [0, 0, 0]
bottle_A[0].position = [2.124113948922353, 1.6500024061858374, 0.115]
bottle_A[0].rotation = [0, 0, 0]
cabinet_A[0].position = [1.9044511379961413, 2.1821058993595814, 0.9]
cabinet_A[0].rotation = [0, 0, 0]
bottle_B[0].position = [1.9284461537254443, 1.9454432002177038, 0.1]
bottle_B[0].rotation = [0, 0, 0]
pot[0].position = [1.6189450344219238, 1.4770221614017662, 0.08]
pot[0].rotation = [0, 0, 0]
lamp[0].position = [0.735424073070024, 0.3798103393262876, 0.14]
lamp[0].rotation = [0, 0, 0]
book[0].position = [2.6288753097832505, 0.17208832104048935, 0.0125]
book[0].rotation = [0, 0, 0]
toilet[0].position = [0.13344598841958638, 1.252196082679183, 0.39]
toilet[0].rotation = [0, 0, 0]
bottle_C[0].position = [0.019225442454579408, 0.5488729318915231, 0.09]
bottle_C[0].rotation = [0, 0, 0]
sink[0].position = [1.9134945028769366, 2.238025682127968, 0.09]
sink[0].rotation = [0, 0, 0]
cabinet_B[0].position = [3.2299480749058906, 1.0702665121652473, 0.36]
cabinet_B[0].rotation = [0, 0, 0]
shelf[0].position = [3.2118401294278187, 0.9355422575386674, 0.02]
shelf[0].rotation = [0, 0, 0]

solver.constraints = []

# Keep the entry at x=0, y=1.68 clear. The cabinets and toilet form
# a left-to-right row: cabinet_B (o0009), toilet (o0006), cabinet_A (o0001).
# The toilet faces left toward cabinet_B. The tall cabinet is away
# from all window openings.
cabinet_B[0].position = [0.25, 0.55, 0.36]
cabinet_B[0].rotation = [0, 0, 0]

toilet[0].position = [2.00, 0.55, 0.39]
toilet[0].rotation = [0, 0, radians(180)]

cabinet_A[0].position = [3.00, 0.55, 0.90]
cabinet_A[0].rotation = [0, 0, radians(180)]

# The sink fits within the low cabinet's countertop.
sink[0].position = [0.25, 0.55, 0.81]
sink[0].rotation = [0, 0, 0]

# Toiletries occupy the two free countertop strips beside the sink.
bottle_A[0].position = [0.25, 0.17, 0.835]
bottle_A[0].rotation = [0, 0, 0]

bottle_B[0].position = [0.25, 0.93, 0.82]
bottle_B[0].rotation = [0, 0, 0]

# A shallow wall-mounted shelf uses the solid bottom wall.
# Rotating it 90 degrees puts its long dimension along that wall.
shelf[0].position = [1.15, 0.10, 1.25]
shelf[0].rotation = [0, 0, radians(90)]

# Both objects rest on the shelf without overlapping. The lamp's
# rotated depth is 0.20 m, so its back touches the wall at y=0.
lamp[0].position = [1.00, 0.10, 1.41]
lamp[0].rotation = [0, 0, radians(90)]

pot[0].position = [1.33, 0.10, 1.35]
pot[0].rotation = [0, 0, radians(90)]

# Separate the remaining small objects on the tall cabinet's top.
bottle_C[0].position = [3.00, 0.40, 1.89]
bottle_C[0].rotation = [0, 0, radians(180)]

book[0].position = [3.00, 0.70, 1.815]
book[0].rotation = [0, 0, radians(180)]

# Important semantic constraints first.
solver.point_towards(toilet[0], cabinet_B[0])
solver.against_wall(cabinet_B[0], walls[2])
solver.against_wall(shelf[0], walls[3])
solver.against_wall(lamp[0], walls[3])

# Surface support: the shelf itself is wall-mounted rather than
# resting on the floor; all loose objects have physical support.
solver.on_top_of(sink[0], cabinet_B[0])
solver.on_top_of(bottle_A[0], cabinet_B[0])
solver.on_top_of(bottle_B[0], cabinet_B[0])
solver.on_top_of(lamp[0], shelf[0])
solver.on_top_of(pot[0], shelf[0])
solver.on_top_of(bottle_C[0], cabinet_A[0])
solver.on_top_of(book[0], cabinet_A[0])

# Fixed layout targets preserve the clear entry, the cabinet/toilet
# ordering, the elevated shelf, and the nonoverlapping surface positions.
# These are reference points, not additional scene furnishings.
for placed_instance in (
    cabinet_B[0], toilet[0], cabinet_A[0], sink[0],
    bottle_A[0], bottle_B[0], shelf[0], lamp[0],
    pot[0], bottle_C[0], book[0],
):
    solver.distance_constraint(
        placed_instance,
        AssetInstance(position=list(placed_instance.position)),
        0, 0, weight=10,
    )

# Explicit orientation constraints for every instance.
solver.align_with(
    cabinet_B[0], AssetInstance(rotation=[0, 0, 0])
)
solver.align_with(cabinet_A[0], cabinet_B[0], angle=180)
solver.align_with(sink[0], cabinet_B[0])
solver.align_with(bottle_A[0], cabinet_B[0])
solver.align_with(bottle_B[0], cabinet_B[0])
solver.align_with(shelf[0], cabinet_B[0], angle=90)
solver.align_with(lamp[0], shelf[0])
solver.align_with(pot[0], shelf[0])
solver.align_with(bottle_C[0], cabinet_A[0])
solver.align_with(book[0], cabinet_A[0])

solver.constraints = []
bottle_A[0].position = [0.25, 0.17000000178813934, 0.8350000381469727]
bottle_A[0].rotation = [0, 0, 2.048137862542808e-07]
bottle_A[0].optimize = 2
cabinet_A[0].position = [3.0, 0.550000011920929, 0.8999999761581421]
cabinet_A[0].rotation = [0, 0, -3.1415922583344624]
cabinet_A[0].optimize = 2
bottle_C[0].position = [3.0, 0.4000000059604645, 1.8899999856948853]
bottle_C[0].rotation = [0, 0, -3.141592463913959]
bottle_C[0].optimize = 2
lamp[0].position = [1.0, 0.09999999403953552, 0.18000000715255737]
lamp[0].rotation = [0, 0, 1.5707963923977426]
lamp[0].optimize = 2
sink[0].position = [0.25, 0.550000011920929, 0.8100000619888306]
sink[0].rotation = [0, 0, 2.048137862542808e-07]
sink[0].optimize = 2
shelf[0].position = [1.149999976158142, 0.09999999403953552, 0.019999999552965164]
shelf[0].rotation = [0, 0, 1.5707963289274618]
shelf[0].optimize = 2
book[0].position = [3.0, 0.699999988079071, 1.8149999380111694]
book[0].rotation = [0, 0, -3.141592463913959]
book[0].optimize = 2
bottle_B[0].position = [0.25, 0.9300000071525574, 0.8200000524520874]
bottle_B[0].rotation = [0, 0, 2.048137862542808e-07]
bottle_B[0].optimize = 2
toilet[0].position = [2.0, 0.550000011920929, 0.38999998569488525]
toilet[0].rotation = [0, 0, -3.1321678761290697]
toilet[0].optimize = 2
cabinet_B[0].position = [0.2500000298023224, 0.550000011920929, 0.36000001430511475]
cabinet_B[0].rotation = [0, 0, -7.679423426348721e-09]
cabinet_B[0].optimize = 2
pot[0].position = [1.3300000429153442, 0.10000000149011612, 0.11999999731779099]
pot[0].rotation = [0, 0, 1.5707964514035477]
pot[0].optimize = 2

