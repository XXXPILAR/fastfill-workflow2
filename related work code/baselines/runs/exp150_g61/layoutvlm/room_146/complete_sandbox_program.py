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
toilet = Assets(description="modern compact toilet with advanced soft-close lid and bidet features", size=[0.70, 0.40, 0.78], placements=[AssetInstance() for _ in range(1)])
vanity_cabinet = Assets(description="large double-sink modern wooden vanity cabinet with ample storage", size=[0.55, 1.60, 0.85], placements=[AssetInstance() for _ in range(1)])
storage_cabinet = Assets(description="tall slim bathroom storage cabinet with multiple shelves and doors", size=[0.35, 0.40, 1.80], placements=[AssetInstance() for _ in range(1)])
small_bench = Assets(description="compact wooden bench for seating and placing items", size=[0.35, 0.75, 0.45], placements=[AssetInstance() for _ in range(1)])

bathtub[0].instance_id = 'bathtub_0'
toilet[0].instance_id = 'toilet_0'
vanity_cabinet[0].instance_id = 'vanity_cabinet_0'
storage_cabinet[0].instance_id = 'storage_cabinet_0'
small_bench[0].instance_id = 'small_bench_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

bathtub[0].position = [1.619848790355622, 0.5587934372342426, 0.3]
bathtub[0].rotation = [0, 0, 0]
toilet[0].position = [1.1909870624334191, 1.365639673906935, 0.39]
toilet[0].rotation = [0, 0, 0]
vanity_cabinet[0].position = [1.6599981286524343, 0.7332506388937764, 0.425]
vanity_cabinet[0].rotation = [0, 0, 0]
storage_cabinet[0].position = [0.9603506188130129, 2.219684542661534, 0.9]
storage_cabinet[0].rotation = [0, 0, 0]
small_bench[0].position = [3.9667241938481874, 0.9780815300860393, 0.225]
small_bench[0].rotation = [0, 0, 0]
bathtub[0].position = [1.619848790355622, 0.5587934372342426, 0.3]
bathtub[0].rotation = [0, 0, 0]
toilet[0].position = [1.1909870624334191, 1.365639673906935, 0.39]
toilet[0].rotation = [0, 0, 0]
vanity_cabinet[0].position = [1.6599981286524343, 0.7332506388937764, 0.425]
vanity_cabinet[0].rotation = [0, 0, 0]
storage_cabinet[0].position = [0.9603506188130129, 2.219684542661534, 0.9]
storage_cabinet[0].rotation = [0, 0, 0]
small_bench[0].position = [3.9667241938481874, 0.9780815300860393, 0.225]
small_bench[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the actual wall coordinates: the room spans x=0..4 and y=0..3.
# The bathtub occupies the west side; the toilet faces it from the east.
# The vanity and bench occupy opposite walls, leaving an open central aisle.
bathtub[0].position = [0.60, 1.70, 0.30]
bathtub[0].rotation = [0, 0, 0]

toilet[0].position = [3.65, 1.70, 0.39]
toilet[0].rotation = [0, 0, radians(180)]

vanity_cabinet[0].position = [1.90, 0.275, 0.425]
vanity_cabinet[0].rotation = [0, 0, radians(90)]

storage_cabinet[0].position = [3.825, 2.65, 0.90]
storage_cabinet[0].rotation = [0, 0, radians(180)]

small_bench[0].position = [2.30, 2.825, 0.225]
small_bench[0].rotation = [0, 0, radians(270)]

# Prioritize the required facing relationship and wall contact.
solver.point_towards(toilet[0], bathtub[0])
solver.against_wall(small_bench[0], walls[1])
solver.against_wall(toilet[0], walls[0])
solver.against_wall(vanity_cabinet[0], walls[3])
solver.against_wall(storage_cabinet[0], walls[0])

# Fixed reference instances are constraint targets, not additional scene assets.
# Preserve the chosen positions, including the freestanding tub's wall clearance.
for layout_asset in (
    bathtub, toilet, vanity_cabinet, storage_cabinet, small_bench
):
    solver.distance_constraint(
        layout_asset[0],
        AssetInstance(position=list(layout_asset[0].position)),
        0,
        0,
        weight=10,
    )

# Keep wall-mounted furniture facing into the room. The tub's long axis runs
# north–south because its local y dimension is its 1.80 m length.
layout_orientation_reference = AssetInstance(rotation=[0, 0, 0])
solver.align_with(bathtub[0], layout_orientation_reference, angle=0)
solver.align_with(vanity_cabinet[0], layout_orientation_reference, angle=90)
solver.align_with(storage_cabinet[0], layout_orientation_reference, angle=180)
solver.align_with(small_bench[0], layout_orientation_reference, angle=270)

# Conservative pairwise clearances: non-intersecting circumscribed footprint
# circles guarantee that the furniture bounding boxes do not overlap.
# Include the vertical center offset because distance_constraint uses 3D centers.
layout_assets = (
    bathtub, toilet, vanity_cabinet, storage_cabinet, small_bench
)
for layout_i, layout_first in enumerate(layout_assets):
    for layout_second in layout_assets[layout_i + 1:]:
        layout_radius_first = (
            layout_first.size[0] ** 2 + layout_first.size[1] ** 2
        ) ** 0.5 / 2
        layout_radius_second = (
            layout_second.size[0] ** 2 + layout_second.size[1] ** 2
        ) ** 0.5 / 2
        layout_vertical_offset = (
            layout_first.size[2] - layout_second.size[2]
        ) / 2
        layout_minimum_distance = (
            (layout_radius_first + layout_radius_second + 0.08) ** 2
            + layout_vertical_offset ** 2
        ) ** 0.5
        solver.distance_constraint(
            layout_first[0], layout_second[0],
            layout_minimum_distance, None, weight=10
        )

# All five assets are floor-standing; no on_top_of constraints are needed.

solver.constraints = []
storage_cabinet[0].position = [3.825000047683716, 2.6500000953674316, 0.8999999761581421]
storage_cabinet[0].rotation = [0, 0, -3.1415926102518914]
storage_cabinet[0].optimize = 2
small_bench[0].position = [2.299999952316284, 2.8249998092651367, 0.22499999403953552]
small_bench[0].rotation = [0, 0, -1.5707962827064184]
small_bench[0].optimize = 2
vanity_cabinet[0].position = [1.899999976158142, 0.27500003576278687, 0.42500001192092896]
vanity_cabinet[0].rotation = [0, 0, 1.5707963611913898]
vanity_cabinet[0].optimize = 2
bathtub[0].position = [0.5419474244117737, 1.7580525875091553, 0.30000001192092896]
bathtub[0].rotation = [0, 0, 0.025132740109855806]
bathtub[0].optimize = 2
toilet[0].position = [3.65000057220459, 1.7000000476837158, 0.38999998569488525]
toilet[0].rotation = [0, 0, -3.1415926102560694]
toilet[0].optimize = 2

