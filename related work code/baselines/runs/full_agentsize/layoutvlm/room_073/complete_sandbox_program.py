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
bottle_A = Assets(description="bottle", size=[0.08, 0.08, 0.24], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.40, 0.65, 0.85], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="bottle", size=[0.07, 0.07, 0.20], placements=[AssetInstance() for _ in range(1)])
pot = Assets(description="pot", size=[0.18, 0.18, 0.16], placements=[AssetInstance() for _ in range(1)])
lamp = Assets(description="lamp", size=[0.12, 0.22, 0.30], placements=[AssetInstance() for _ in range(1)])
book = Assets(description="book", size=[0.15, 0.21, 0.03], placements=[AssetInstance() for _ in range(1)])
toilet = Assets(description="toilet", size=[0.68, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
bottle_C = Assets(description="bottle", size=[0.06, 0.06, 0.18], placements=[AssetInstance() for _ in range(1)])
sink = Assets(description="sink", size=[0.45, 0.55, 0.18], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.48, 0.60, 0.72], placements=[AssetInstance() for _ in range(1)])
shelf = Assets(description="shelf", size=[0.20, 0.70, 0.04], placements=[AssetInstance() for _ in range(1)])

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

bottle_A[0].position = [4.008441830875755, 2.0904196054055757, 0.12]
bottle_A[0].rotation = [0, 0, 0]
cabinet_A[0].position = [4.095431086256077, 0.809477317801232, 0.425]
cabinet_A[0].rotation = [0, 0, 0]
bottle_B[0].position = [2.33633850639894, 1.0946624871716504, 0.1]
bottle_B[0].rotation = [0, 0, 0]
pot[0].position = [1.50943037502358, 0.7465340316753452, 0.08]
pot[0].rotation = [0, 0, 0]
lamp[0].position = [2.0320344155987873, 0.2563751483002404, 0.15]
lamp[0].rotation = [0, 0, 0]
book[0].position = [1.4769983325256193, 1.9076767259846614, 0.015]
book[0].rotation = [0, 0, 0]
toilet[0].position = [0.5554012701932506, 1.2735258144084334, 0.39]
toilet[0].rotation = [0, 0, 0]
bottle_C[0].position = [1.610100589207745, 0.9169922898696977, 0.09]
bottle_C[0].rotation = [0, 0, 0]
sink[0].position = [0.17443914810204622, 0.659883373332917, 0.09]
sink[0].rotation = [0, 0, 0]
cabinet_B[0].position = [1.7961086553990862, 1.7111706091923147, 0.36]
cabinet_B[0].rotation = [0, 0, 0]
shelf[0].position = [3.832832789927241, 1.0497660805766649, 0.02]
shelf[0].rotation = [0, 0, 0]
bottle_A[0].position = [4.008441830875755, 2.0904196054055757, 0.12]
bottle_A[0].rotation = [0, 0, 0]
cabinet_A[0].position = [4.095431086256077, 0.809477317801232, 0.425]
cabinet_A[0].rotation = [0, 0, 0]
bottle_B[0].position = [2.33633850639894, 1.0946624871716504, 0.1]
bottle_B[0].rotation = [0, 0, 0]
pot[0].position = [1.50943037502358, 0.7465340316753452, 0.08]
pot[0].rotation = [0, 0, 0]
lamp[0].position = [2.0320344155987873, 0.2563751483002404, 0.15]
lamp[0].rotation = [0, 0, 0]
book[0].position = [1.4769983325256193, 1.9076767259846614, 0.015]
book[0].rotation = [0, 0, 0]
toilet[0].position = [0.5554012701932506, 1.2735258144084334, 0.39]
toilet[0].rotation = [0, 0, 0]
bottle_C[0].position = [1.610100589207745, 0.9169922898696977, 0.09]
bottle_C[0].rotation = [0, 0, 0]
sink[0].position = [0.17443914810204622, 0.659883373332917, 0.09]
sink[0].rotation = [0, 0, 0]
cabinet_B[0].position = [1.7961086553990862, 1.7111706091923147, 0.36]
cabinet_B[0].rotation = [0, 0, 0]
shelf[0].position = [3.832832789927241, 1.0497660805766649, 0.02]
shelf[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the two cabinets and the toilet along the unobstructed part of the
# bottom wall. The toilet lies spatially between the cabinets and points toward
# cabinet_B (o0009), while the door and the bottom-right window remain clear.
cabinet_A[0].position = [0.42, 0.20, 0.425]
cabinet_A[0].rotation = [0, 0, radians(90)]

toilet[0].position = [1.25, 0.19, 0.39]
toilet[0].rotation = [0, 0, radians(0)]

cabinet_B[0].position = [2.12, 0.24, 0.36]
cabinet_B[0].rotation = [0, 0, radians(90)]

# Place the wall-mounted sink and shelf on the window-free right portion of the
# upper wall. Their fronts point into the room.
sink[0].position = [3.78, 2.035, 0.82]
sink[0].rotation = [0, 0, radians(-90)]

shelf[0].position = [2.95, 2.16, 1.35]
shelf[0].rotation = [0, 0, radians(-90)]

# Put the lamp against the lower portion of the left wall, below the door
# opening, so that it does not obstruct the entrance.
lamp[0].position = [0.06, 0.55, 0.15]
lamp[0].rotation = [0, 0, radians(0)]

# Distribute the small objects across suitable supporting surfaces.
bottle_A[0].position = [0.27, 0.30, 0.97]
bottle_A[0].rotation = [0, 0, radians(90)]

pot[0].position = [0.55, 0.30, 0.93]
pot[0].rotation = [0, 0, radians(90)]

bottle_B[0].position = [2.12, 0.24, 0.82]
bottle_B[0].rotation = [0, 0, radians(90)]

bottle_C[0].position = [3.78, 2.035, 1.00]
bottle_C[0].rotation = [0, 0, radians(-90)]

book[0].position = [2.95, 2.14, 1.385]
book[0].rotation = [0, 0, radians(-90)]

# Fixed reference points retain the intended zones while allowing the solver
# to make small physical-feasibility adjustments.
cabinet_A_anchor = AssetInstance(
    position=[0.42, 0.20, 0.425],
    rotation=[0, 0, radians(90)]
)
toilet_anchor = AssetInstance(
    position=[1.25, 0.19, 0.39],
    rotation=[0, 0, radians(0)]
)
cabinet_B_anchor = AssetInstance(
    position=[2.12, 0.24, 0.36],
    rotation=[0, 0, radians(90)]
)
sink_anchor = AssetInstance(
    position=[3.78, 2.035, 0.82],
    rotation=[0, 0, radians(-90)]
)
shelf_anchor = AssetInstance(
    position=[2.95, 2.16, 1.35],
    rotation=[0, 0, radians(-90)]
)
lamp_anchor = AssetInstance(
    position=[0.06, 0.55, 0.15],
    rotation=[0, 0, radians(0)]
)

bottle_A_anchor = AssetInstance(
    position=[0.27, 0.30, 0.97],
    rotation=[0, 0, radians(90)]
)
pot_anchor = AssetInstance(
    position=[0.55, 0.30, 0.93],
    rotation=[0, 0, radians(90)]
)
bottle_B_anchor = AssetInstance(
    position=[2.12, 0.24, 0.82],
    rotation=[0, 0, radians(90)]
)
bottle_C_anchor = AssetInstance(
    position=[3.78, 2.035, 1.00],
    rotation=[0, 0, radians(-90)]
)
book_anchor = AssetInstance(
    position=[2.95, 2.14, 1.385],
    rotation=[0, 0, radians(-90)]
)

# Preserve the primary semantic requirement first: the toilet faces cabinet_B.
solver.point_towards(toilet[0], cabinet_B[0])

# Keep the three lower fixtures in their ordered, non-overlapping locations.
solver.distance_constraint(
    cabinet_A[0], cabinet_A_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    toilet[0], toilet_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    cabinet_B[0], cabinet_B_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    toilet[0], cabinet_A[0], 0.78, 0.98, weight=10
)
solver.distance_constraint(
    toilet[0], cabinet_B[0], 0.78, 0.98, weight=10
)

solver.against_wall(cabinet_A[0], walls[3])
solver.against_wall(toilet[0], walls[3])
solver.against_wall(cabinet_B[0], walls[3])

solver.align_with(cabinet_A[0], cabinet_A_anchor)
solver.align_with(cabinet_B[0], cabinet_B_anchor)

# Constrain the upper-wall fixtures to the window-free wall section.
solver.distance_constraint(sink[0], sink_anchor, 0, 0, weight=10)
solver.against_wall(sink[0], walls[1])
solver.align_with(sink[0], sink_anchor)

solver.distance_constraint(shelf[0], shelf_anchor, 0, 0, weight=10)
solver.against_wall(shelf[0], walls[1])
solver.align_with(shelf[0], shelf_anchor)

# The lamp is explicitly required to be against a wall.
solver.against_wall(lamp[0], walls[2])
solver.distance_constraint(lamp[0], lamp_anchor, 0, 0, weight=10)
solver.align_with(lamp[0], lamp_anchor)

# Each small object receives a position constraint, an orientation constraint,
# and an on-top-of constraint so it remains on its intended support.
solver.on_top_of(bottle_A[0], cabinet_A[0])
solver.distance_constraint(
    bottle_A[0], bottle_A_anchor, 0, 0, weight=10
)
solver.align_with(bottle_A[0], cabinet_A[0])

solver.on_top_of(pot[0], cabinet_A[0])
solver.distance_constraint(pot[0], pot_anchor, 0, 0, weight=10)
solver.align_with(pot[0], cabinet_A[0])

solver.on_top_of(bottle_B[0], cabinet_B[0])
solver.distance_constraint(
    bottle_B[0], bottle_B_anchor, 0, 0, weight=10
)
solver.align_with(bottle_B[0], cabinet_B[0])

solver.on_top_of(bottle_C[0], sink[0])
solver.distance_constraint(
    bottle_C[0], bottle_C_anchor, 0, 0, weight=10
)
solver.align_with(bottle_C[0], sink[0])

solver.on_top_of(book[0], shelf[0])
solver.distance_constraint(book[0], book_anchor, 0, 0, weight=10)
solver.align_with(book[0], shelf[0])

solver.constraints = []
pot[0].position = [0.550000011920929, 0.30000001192092896, 0.9300000071525574]
pot[0].rotation = [0, 0, 1.5707963693014755]
pot[0].optimize = 2
book[0].position = [2.950000047683716, 2.140000104904175, 0.054999999701976776]
book[0].rotation = [0, 0, -1.5707962826823691]
book[0].optimize = 2
bottle_B[0].position = [2.119999885559082, 0.23999999463558197, 0.8200000524520874]
bottle_B[0].rotation = [0, 0, 1.5707963663845186]
bottle_B[0].optimize = 2
sink[0].position = [3.7799999713897705, 2.0365777015686035, 0.09000000357627869]
sink[0].rotation = [0, 0, -1.5707962826229047]
sink[0].optimize = 2
lamp[0].position = [0.06000000238418579, 0.550000011920929, 0.15000000596046448]
lamp[0].rotation = [0, 0, 4.409125561393438e-08]
lamp[0].optimize = 2
bottle_A[0].position = [0.27000001072883606, 0.30000001192092896, 0.9700000286102295]
bottle_A[0].rotation = [0, 0, 1.5707963693014755]
bottle_A[0].optimize = 2
cabinet_A[0].position = [0.41999998688697815, 0.20000001788139343, 0.42500001192092896]
cabinet_A[0].rotation = [0, 0, 1.5707963697291438]
cabinet_A[0].optimize = 2
toilet[0].position = [1.25, 0.35705846548080444, 0.38999998569488525]
toilet[0].rotation = [0, 0, 1.4721564974628478]
toilet[0].optimize = 2
bottle_C[0].position = [3.7799999713897705, 2.0350000858306885, 0.27000001072883606]
bottle_C[0].rotation = [0, 0, -1.5707962829431936]
bottle_C[0].optimize = 2
cabinet_B[0].position = [2.119999885559082, 0.24000000953674316, 0.36000001430511475]
cabinet_B[0].rotation = [0, 0, 1.5707963676980798]
cabinet_B[0].optimize = 2
shelf[0].position = [2.950000047683716, 2.1615779399871826, 0.019999999552965164]
shelf[0].rotation = [0, 0, -1.570796283735354]
shelf[0].optimize = 2

