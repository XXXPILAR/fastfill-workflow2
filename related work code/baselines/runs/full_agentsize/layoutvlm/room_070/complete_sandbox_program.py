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
    Wall(corner1=[2.71, 0.00, 0.00], corner2=[2.70, 0.29, 0.00]),
    Wall(corner1=[2.70, 0.29, 0.00], corner2=[1.25, 1.75, 0.00]),
    Wall(corner1=[1.25, 1.75, 0.00], corner2=[0.79, 2.20, 0.00]),
    Wall(corner1=[0.79, 2.20, 0.00], corner2=[0.00, 2.21, 0.00]),
    Wall(corner1=[0.00, 2.21, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.71, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
sink = Assets(description="sink", size=[0.50, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
shelf = Assets(description="shelf", size=[0.15, 0.60, 0.04], placements=[AssetInstance() for _ in range(1)])
toilet = Assets(description="toilet", size=[0.70, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
bottle_A = Assets(description="bottle", size=[0.07, 0.07, 0.20], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="bottle", size=[0.06, 0.06, 0.18], placements=[AssetInstance() for _ in range(1)])
bottle_C = Assets(description="bottle", size=[0.08, 0.08, 0.22], placements=[AssetInstance() for _ in range(1)])

sink[0].instance_id = 'sink_0'
shelf[0].instance_id = 'shelf_0'
toilet[0].instance_id = 'toilet_0'
bottle_A[0].instance_id = 'bottle_A_0'
bottle_B[0].instance_id = 'bottle_B_0'
bottle_C[0].instance_id = 'bottle_C_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

sink[0].position = [0.7007198469322219, 1.217590998797697, 0.425]
sink[0].rotation = [0, 0, 0]
shelf[0].position = [1.4555540394957462, 1.014255416228549, 0.02]
shelf[0].rotation = [0, 0, 0]
toilet[0].position = [2.245168910946712, 0.325997147173375, 0.39]
toilet[0].rotation = [0, 0, 0]
bottle_A[0].position = [0.007887069383895533, 1.1682314410724093, 0.1]
bottle_A[0].rotation = [0, 0, 0]
bottle_B[0].position = [1.203380738410254, 0.17512827739766632, 0.09]
bottle_B[0].rotation = [0, 0, 0]
bottle_C[0].position = [1.7534423231255336, 1.0450990903930792, 0.11]
bottle_C[0].rotation = [0, 0, 0]
sink[0].position = [0.7007198469322219, 1.217590998797697, 0.425]
sink[0].rotation = [0, 0, 0]
shelf[0].position = [1.4555540394957462, 1.014255416228549, 0.02]
shelf[0].rotation = [0, 0, 0]
toilet[0].position = [2.245168910946712, 0.325997147173375, 0.39]
toilet[0].rotation = [0, 0, 0]
bottle_A[0].position = [0.007887069383895533, 1.1682314410724093, 0.1]
bottle_A[0].rotation = [0, 0, 0]
bottle_B[0].position = [1.203380738410254, 0.17512827739766632, 0.09]
bottle_B[0].rotation = [0, 0, 0]
bottle_C[0].position = [1.7534423231255336, 1.0450990903930792, 0.11]
bottle_C[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the sink along the left wall, below the window that starts near y=1.53.
# Its front faces into the room (+x), and this location stays clear of the door.
sink[0].position = [0.25, 1.12, 0.425]
sink[0].rotation = [0, 0, radians(0)]

# Use the narrow shelf as a rear ledge on top of the sink. Its shallow depth
# keeps most of the sink surface usable while leaving room for the bottles.
shelf[0].position = [0.075, 1.12, 0.87]
shelf[0].rotation = [0, 0, radians(0)]

# Place the toilet at the diagonal wall, away from the entrance clearance.
# The initial rotation points its front approximately toward the sink.
toilet[0].position = [1.65, 1.08, 0.39]
toilet[0].rotation = [0, 0, radians(178)]

# Arrange the three bottles in a row on the shelf.
bottle_A[0].position = [0.075, 0.94, 0.99]
bottle_A[0].rotation = [0, 0, radians(0)]

bottle_B[0].position = [0.075, 1.12, 0.98]
bottle_B[0].rotation = [0, 0, radians(0)]

bottle_C[0].position = [0.075, 1.30, 1.00]
bottle_C[0].rotation = [0, 0, radians(0)]

# Primary fixture constraints: retain wall contact and the required facing
# relationship. The reciprocal sink constraint keeps both fixtures facing
# one another if either fixture is moved during feasibility adjustment.
solver.against_wall(sink[0], walls[4])
solver.point_towards(sink[0], toilet[0])

solver.against_wall(toilet[0], walls[1])
solver.point_towards(toilet[0], sink[0])

# Keep the shelf attached to the left wall and supported by the sink.
solver.against_wall(shelf[0], walls[4])
solver.on_top_of(shelf[0], sink[0])
solver.align_with(shelf[0], sink[0])

# The centers are about 0.48 m apart when the shelf rests on the sink.
# A 0.545 m upper bound accounts for the fixtures' half-heights and permits
# no more than approximately 0.10 m separation between their surfaces.
solver.distance_constraint(
    shelf[0], sink[0],
    min_distance=None, max_distance=0.545, weight=10
)

# Position anchors preserve the non-overlapping row while on_top_of maintains
# correct vertical support. Each bottle also inherits the shelf orientation.
bottle_A_anchor = AssetInstance(position=[0.075, 0.94, 0.99])
bottle_B_anchor = AssetInstance(position=[0.075, 1.12, 0.98])
bottle_C_anchor = AssetInstance(position=[0.075, 1.30, 1.00])

solver.on_top_of(bottle_A[0], shelf[0])
solver.distance_constraint(
    bottle_A[0], bottle_A_anchor,
    min_distance=0.0, max_distance=0.02, weight=10
)
solver.align_with(bottle_A[0], shelf[0])

solver.on_top_of(bottle_B[0], shelf[0])
solver.distance_constraint(
    bottle_B[0], bottle_B_anchor,
    min_distance=0.0, max_distance=0.02, weight=10
)
solver.align_with(bottle_B[0], shelf[0])

solver.on_top_of(bottle_C[0], shelf[0])
solver.distance_constraint(
    bottle_C[0], bottle_C_anchor,
    min_distance=0.0, max_distance=0.02, weight=10
)
solver.align_with(bottle_C[0], shelf[0])

solver.constraints = []
sink[0].position = [0.24999995529651642, 1.1200000047683716, 0.42500001192092896]
sink[0].rotation = [0, 0, 1.1694572961337976e-07]
sink[0].optimize = 2
bottle_A[0].position = [0.07500000298023224, 0.9399999976158142, 0.9900000095367432]
bottle_A[0].rotation = [0, 0, -3.180450996731986e-07]
bottle_A[0].optimize = 2
bottle_C[0].position = [0.07500000298023224, 1.2999999523162842, 1.0]
bottle_C[0].rotation = [0, 0, -3.180450996731986e-07]
bottle_C[0].optimize = 2
toilet[0].position = [1.5351368188858032, 0.9671981930732727, 0.38999998569488525]
toilet[0].rotation = [0, 0, -2.3632814517328757]
toilet[0].optimize = 2
shelf[0].position = [0.07500005513429642, 1.1200000047683716, 0.8700000047683716]
shelf[0].rotation = [0, 0, 4.594210981811005e-07]
shelf[0].optimize = 2
bottle_B[0].position = [0.07500000298023224, 1.1200000047683716, 0.9800000190734863]
bottle_B[0].rotation = [0, 0, -3.180450996731986e-07]
bottle_B[0].optimize = 2

