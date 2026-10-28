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
    Wall(corner1=[4.00, 0.00, 0.00], corner2=[4.00, 3.00, 0.00]),
    Wall(corner1=[4.00, 3.00, 0.00], corner2=[0.00, 3.00, 0.00]),
    Wall(corner1=[0.00, 3.00, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bathtub = Assets(description="large freestanding oval bathtub with elegant modern design", size=[0.85, 1.80, 0.60], placements=[AssetInstance() for _ in range(1)])
toilet = Assets(description="modern compact toilet with advanced soft-close lid and bidet features", size=[0.70, 0.40, 0.48], placements=[AssetInstance() for _ in range(1)])
vanity_cabinet = Assets(description="large double-sink modern wooden vanity cabinet with ample storage", size=[0.55, 1.80, 0.85], placements=[AssetInstance() for _ in range(1)])
storage_cabinet = Assets(description="tall slim bathroom storage cabinet with multiple shelves and doors", size=[0.35, 0.45, 1.90], placements=[AssetInstance() for _ in range(1)])
small_bench = Assets(description="compact wooden bench for seating and placing items", size=[0.35, 0.80, 0.45], placements=[AssetInstance() for _ in range(1)])

bathtub[0].instance_id = 'bathtub_0'
toilet[0].instance_id = 'toilet_0'
vanity_cabinet[0].instance_id = 'vanity_cabinet_0'
storage_cabinet[0].instance_id = 'storage_cabinet_0'
small_bench[0].instance_id = 'small_bench_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

bathtub[0].position = [3.2388632207130117, 1.4763718414250728, 0.3]
bathtub[0].rotation = [0, 0, 0]
toilet[0].position = [1.005560340618156, 2.1428257535398645, 0.24]
toilet[0].rotation = [0, 0, 0]
vanity_cabinet[0].position = [0.2000049118132079, 0.661536443242699, 0.425]
vanity_cabinet[0].rotation = [0, 0, 0]
storage_cabinet[0].position = [3.3028626746853744, 2.732647841533714, 0.95]
storage_cabinet[0].rotation = [0, 0, 0]
small_bench[0].position = [3.09598816947848, 1.3808565996483353, 0.225]
small_bench[0].rotation = [0, 0, 0]
bathtub[0].position = [3.2388632207130117, 1.4763718414250728, 0.3]
bathtub[0].rotation = [0, 0, 0]
toilet[0].position = [1.005560340618156, 2.1428257535398645, 0.24]
toilet[0].rotation = [0, 0, 0]
vanity_cabinet[0].position = [0.2000049118132079, 0.661536443242699, 0.425]
vanity_cabinet[0].rotation = [0, 0, 0]
storage_cabinet[0].position = [3.3028626746853744, 2.732647841533714, 0.95]
storage_cabinet[0].rotation = [0, 0, 0]
small_bench[0].position = [3.09598816947848, 1.3808565996483353, 0.225]
small_bench[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the bathtub lengthwise against the left wall, leaving its open side
# facing the center of the bathroom.
bathtub[0].position = [0.425, 1.75, 0.30]
bathtub[0].rotation = [0, 0, radians(0)]

# Place the toilet against the right wall. Its exact orientation is initialized
# toward the bathtub and reinforced below with point_towards.
toilet[0].position = [3.62, 0.75, 0.24]
toilet[0].rotation = [0, 0, radians(169)]

# Place the double vanity along the top wall, facing into the room.
vanity_cabinet[0].position = [2.35, 2.725, 0.425]
vanity_cabinet[0].rotation = [0, 0, radians(-90)]

# Place the tall cabinet against the bottom wall near the lower-left corner,
# while retaining clearance from the bathtub.
storage_cabinet[0].position = [0.45, 0.175, 0.95]
storage_cabinet[0].rotation = [0, 0, radians(90)]

# Place the bench against the bottom wall, clear of the cabinet and toilet.
small_bench[0].position = [1.45, 0.175, 0.225]
small_bench[0].rotation = [0, 0, radians(90)]


# Fixed anchors preserve the intended zones if the solver needs to adjust the
# layout. Their z-coordinates match the centers of the corresponding assets.
bathtub_anchor = AssetInstance(position=[0.425, 1.75, 0.30])
toilet_anchor = AssetInstance(position=[3.62, 0.75, 0.24])
vanity_anchor = AssetInstance(position=[2.35, 2.725, 0.425])
storage_anchor = AssetInstance(position=[0.45, 0.175, 0.95])
bench_anchor = AssetInstance(position=[1.45, 0.175, 0.225])
room_center = AssetInstance(position=[2.00, 1.50, 0.30])


# Important wall relationships are specified first:
# walls[0] = right, walls[1] = top, walls[2] = left, walls[3] = bottom.
solver.against_wall(bathtub[0], walls[2])
solver.against_wall(toilet[0], walls[0])
solver.against_wall(vanity_cabinet[0], walls[1])
solver.against_wall(storage_cabinet[0], walls[3])
solver.against_wall(small_bench[0], walls[3])


# Keep each fixture near its selected section of the corresponding wall.
solver.distance_constraint(
    bathtub[0], bathtub_anchor, min_distance=0, max_distance=0, weight=10
)
solver.distance_constraint(
    toilet[0], toilet_anchor, min_distance=0, max_distance=0, weight=10
)
solver.distance_constraint(
    vanity_cabinet[0], vanity_anchor, min_distance=0, max_distance=0, weight=10
)
solver.distance_constraint(
    storage_cabinet[0], storage_anchor, min_distance=0, max_distance=0, weight=10
)
solver.distance_constraint(
    small_bench[0], bench_anchor, min_distance=0, max_distance=0, weight=10
)


# The toilet must face the bathtub. The other wall-mounted assets face into the
# room, giving them functional access from the open central circulation area.
solver.point_towards(toilet[0], bathtub[0])
solver.point_towards(bathtub[0], room_center)
solver.point_towards(vanity_cabinet[0], room_center)
solver.point_towards(storage_cabinet[0], room_center)
solver.point_towards(small_bench[0], room_center)


# Clearance constraints discourage the solver from moving neighboring assets
# into one another while still permitting small feasibility adjustments.
solver.distance_constraint(
    bathtub[0], vanity_cabinet[0], min_distance=1.10, max_distance=None, weight=10
)
solver.distance_constraint(
    bathtub[0], storage_cabinet[0], min_distance=1.00, max_distance=None, weight=10
)
solver.distance_constraint(
    bathtub[0], small_bench[0], min_distance=1.00, max_distance=None, weight=10
)
solver.distance_constraint(
    bathtub[0], toilet[0], min_distance=1.20, max_distance=None, weight=10
)
solver.distance_constraint(
    vanity_cabinet[0], toilet[0], min_distance=1.00, max_distance=None, weight=10
)
solver.distance_constraint(
    vanity_cabinet[0], small_bench[0], min_distance=1.00, max_distance=None, weight=10
)
solver.distance_constraint(
    storage_cabinet[0], small_bench[0], min_distance=0.85, max_distance=None, weight=10
)
solver.distance_constraint(
    small_bench[0], toilet[0], min_distance=1.00, max_distance=None, weight=10
)

solver.constraints = []
bathtub[0].position = [0.42500001192092896, 1.75, 0.30000001192092896]
bathtub[0].rotation = [0, 0, 3.476062566211614e-08]
bathtub[0].optimize = 2
vanity_cabinet[0].position = [2.3499999046325684, 2.7250001430511475, 0.42500001192092896]
vanity_cabinet[0].rotation = [0, 0, -1.5707963115212031]
vanity_cabinet[0].optimize = 2
toilet[0].position = [3.6500000953674316, 0.75, 0.23999999463558197]
toilet[0].rotation = [0, 0, -3.1415925995146368]
toilet[0].optimize = 2
storage_cabinet[0].position = [0.44999998807907104, 0.17500001192092896, 0.949999988079071]
storage_cabinet[0].rotation = [0, 0, 1.5707963694845368]
storage_cabinet[0].optimize = 2
small_bench[0].position = [1.4500000476837158, 0.17499998211860657, 0.22499999403953552]
small_bench[0].rotation = [0, 0, 1.5707963664671107]
small_bench[0].optimize = 2

