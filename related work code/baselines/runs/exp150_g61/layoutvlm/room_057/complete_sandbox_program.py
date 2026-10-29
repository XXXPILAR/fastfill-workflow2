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
    Wall(corner1=[0.68, 1.86, 0.00], corner2=[0.00, 1.86, 0.00]),
    Wall(corner1=[0.00, 1.86, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[5.15, 0.00, 0.00]),
    Wall(corner1=[5.15, 0.00, 0.00], corner2=[5.15, 1.86, 0.00]),
    Wall(corner1=[5.15, 1.86, 0.00], corner2=[4.47, 1.86, 0.00]),
    Wall(corner1=[4.47, 1.86, 0.00], corner2=[0.68, 1.86, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
washing_machine = Assets(description="washing machine", size=[0.60, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
chair = Assets(description="chair", size=[0.48, 0.45, 0.85], placements=[AssetInstance() for _ in range(1)])
high_chair_A = Assets(description="high chair", size=[0.45, 0.42, 1.00], placements=[AssetInstance() for _ in range(1)])
bar_counter = Assets(description="bar counter", size=[0.50, 1.50, 1.05], placements=[AssetInstance() for _ in range(1)])
pool = Assets(description="pool", size=[0.40, 0.50, 0.20], placements=[AssetInstance() for _ in range(1)])
high_chair_B = Assets(description="high chair", size=[0.45, 0.42, 1.00], placements=[AssetInstance() for _ in range(1)])
basin_cabinet = Assets(description="basin cabinet", size=[0.60, 0.80, 0.85], placements=[AssetInstance() for _ in range(1)])
side_table = Assets(description="side table", size=[0.40, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])

washing_machine[0].instance_id = 'washing_machine_0'
chair[0].instance_id = 'chair_0'
high_chair_A[0].instance_id = 'high_chair_A_0'
bar_counter[0].instance_id = 'bar_counter_0'
pool[0].instance_id = 'pool_0'
high_chair_B[0].instance_id = 'high_chair_B_0'
basin_cabinet[0].instance_id = 'basin_cabinet_0'
side_table[0].instance_id = 'side_table_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

washing_machine[0].position = [4.1977547616583255, 0.12470984058482994, 0.425]
washing_machine[0].rotation = [0, 0, 0]
chair[0].position = [4.396024084003685, 0.8885852002697853, 0.425]
chair[0].rotation = [0, 0, 0]
high_chair_A[0].position = [2.561237849085255, 0.4994598112892628, 0.5]
high_chair_A[0].rotation = [0, 0, 0]
bar_counter[0].position = [2.786383602691862, 0.08985391920553953, 0.525]
bar_counter[0].rotation = [0, 0, 0]
pool[0].position = [0.5865088108281227, 0.27769078415659537, 0.1]
pool[0].rotation = [0, 0, 0]
high_chair_B[0].position = [3.2579407474904705, 0.30315401593014135, 0.5]
high_chair_B[0].rotation = [0, 0, 0]
basin_cabinet[0].position = [4.471969334653718, 0.6237332468079944, 0.425]
basin_cabinet[0].rotation = [0, 0, 0]
side_table[0].position = [0.41428443677771193, 1.8189285310474481, 0.3]
side_table[0].rotation = [0, 0, 0]
washing_machine[0].position = [4.1977547616583255, 0.12470984058482994, 0.425]
washing_machine[0].rotation = [0, 0, 0]
chair[0].position = [4.396024084003685, 0.8885852002697853, 0.425]
chair[0].rotation = [0, 0, 0]
high_chair_A[0].position = [2.561237849085255, 0.4994598112892628, 0.5]
high_chair_A[0].rotation = [0, 0, 0]
bar_counter[0].position = [2.786383602691862, 0.08985391920553953, 0.525]
bar_counter[0].rotation = [0, 0, 0]
pool[0].position = [0.5865088108281227, 0.27769078415659537, 0.1]
pool[0].rotation = [0, 0, 0]
high_chair_B[0].position = [3.2579407474904705, 0.30315401593014135, 0.5]
high_chair_B[0].rotation = [0, 0, 0]
basin_cabinet[0].position = [4.471969334653718, 0.6237332468079944, 0.425]
basin_cabinet[0].rotation = [0, 0, 0]
side_table[0].position = [0.41428443677771193, 1.8189285310474481, 0.3]
side_table[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the actual wall coordinates: the room spans x=0..5.15, y=0..1.86.
# Keep the doorway's full x=1.41..3.75 approach clear by putting utilities
# at the left end and the counter/seating at the right end.
# Positions refer to bounding-box centers.
layout_specs = [
    (washing_machine[0], [0.30, 0.32, 0.425], 0),
    (basin_cabinet[0],   [0.30, 1.30, 0.425], 0),
    (side_table[0],      [0.95, 0.30, 0.300], 0),
    (bar_counter[0],     [4.90, 0.93, 0.525], 180),
    (chair[0],           [4.15, 0.93, 0.425], 0),
    (high_chair_A[0],    [4.15, 0.32, 0.500], 0),
    (high_chair_B[0],    [4.15, 1.54, 0.500], 0),
    # The small pool/basin sits entirely within the cabinet's top footprint.
    (pool[0],            [0.30, 1.30, 0.950], 0),
]

# Strong positional anchors preserve the clear central circulation zone.
# Every instance receives both a position and an orientation constraint.
for instance, center, heading in layout_specs:
    instance.position = list(center)
    instance.rotation = [0, 0, radians(heading)]
    fixed_pose = AssetInstance(
        position=list(center),
        rotation=[0, 0, radians(heading)]
    )
    solver.distance_constraint(instance, fixed_pose, 0, 0, weight=10)

    if instance is chair[0]:
        # Explicitly satisfy the requirement that the chair face the counter.
        solver.point_towards(instance, bar_counter[0])
    else:
        solver.align_with(instance, fixed_pose)

# These wall contacts agree with the anchored positions and keep the bulky
# pieces at the ends rather than obstructing the entrance.
solver.against_wall(washing_machine[0], walls[1])
solver.against_wall(basin_cabinet[0], walls[1])
solver.against_wall(bar_counter[0], walls[3])

# The cabinet top is at z=0.85; the small basin's center is therefore z=0.95.
solver.on_top_of(pool[0], basin_cabinet[0])
solver.align_with(pool[0], basin_cabinet[0])

# Seats face the counter's working side. Their footprints have approximately
# 0.16 m gaps along y and at least 0.26 m clearance from the counter along x.
solver.align_with(high_chair_A[0], bar_counter[0], angle=180)
solver.align_with(high_chair_B[0], bar_counter[0], angle=180)

solver.constraints = []
high_chair_B[0].position = [4.150000095367432, 1.5399999618530273, 0.5]
high_chair_B[0].rotation = [0, 0, -0.00023949902730473468]
high_chair_B[0].optimize = 2
side_table[0].position = [0.949999988079071, 0.30000001192092896, 0.30000001192092896]
side_table[0].rotation = [0, 0, 0.00942477746072377]
side_table[0].optimize = 2
chair[0].position = [4.150000095367432, 0.9300000071525574, 0.42500001192092896]
chair[0].rotation = [0, 0, 0.00942477746072377]
chair[0].optimize = 2
washing_machine[0].position = [0.3000418245792389, 0.3199999928474426, 0.42500001192092896]
washing_machine[0].rotation = [0, 0, -8.597806966846727e-05]
washing_machine[0].optimize = 2
basin_cabinet[0].position = [0.29996198415756226, 1.2999999523162842, 0.42500001192092896]
basin_cabinet[0].rotation = [0, 0, 5.264718708102458e-05]
basin_cabinet[0].optimize = 2
pool[0].position = [0.30000001192092896, 1.2999999523162842, 0.9500000476837158]
pool[0].rotation = [0, 0, 7.406630988048876e-05]
pool[0].optimize = 2
bar_counter[0].position = [4.900010108947754, 0.9300000071525574, 0.5249999761581421]
bar_counter[0].rotation = [0, 0, 3.1415576767731435]
bar_counter[0].optimize = 2
high_chair_A[0].position = [4.150000095367432, 0.3199999928474426, 0.5]
high_chair_A[0].rotation = [0, 0, -0.00023949902730473468]
high_chair_A[0].optimize = 2

