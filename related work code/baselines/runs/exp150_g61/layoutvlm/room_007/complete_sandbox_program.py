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
    Wall(corner1=[0.00, 3.93, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.49, 0.00, 0.00]),
    Wall(corner1=[3.49, 0.00, 0.00], corner2=[3.49, 3.93, 0.00]),
    Wall(corner1=[3.49, 3.93, 0.00], corner2=[2.85, 3.93, 0.00]),
    Wall(corner1=[2.85, 3.93, 0.00], corner2=[2.85, 4.72, 0.00]),
    Wall(corner1=[2.85, 4.72, 0.00], corner2=[0.97, 4.72, 0.00]),
    Wall(corner1=[0.97, 4.72, 0.00], corner2=[0.97, 3.93, 0.00]),
    Wall(corner1=[0.97, 3.93, 0.00], corner2=[0.00, 3.93, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
tv_stand = Assets(description="A sleek, modern media console with a dark wood finish and a minimalist design. It features a long rectangular shape with thin legs and an open shelf section on one side.", size=[0.40, 1.50, 0.50], placements=[AssetInstance() for _ in range(1)])
single_bed = Assets(description="A modern bed with a teal base and a mustard-yellow headboard. It features gray bedding and multiple pillows arranged neatly.", size=[2.10, 1.10, 1.10], placements=[AssetInstance() for _ in range(1)])
nightstand_A = Assets(description="A rectangular cabinet with a smooth surface and a small object placed nearby.", size=[0.40, 0.45, 0.50], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="A tall, rectangular wardrobe with a smooth surface and a single door on one side. It features an open shelving unit on the other side with multiple compartments for storage. The design includes a decorative circular element on the door.", size=[0.60, 1.40, 2.20], placements=[AssetInstance() for _ in range(1)])
cushion = Assets(description="A beige cushion with a smooth texture, resting on a black surface. The cushion appears soft and slightly rounded at the edges.", size=[0.55, 0.55, 0.18], placements=[AssetInstance() for _ in range(1)])
nightstand_B = Assets(description="A rectangular cabinet with a smooth surface and a small object placed nearby.", size=[0.40, 0.45, 0.50], placements=[AssetInstance() for _ in range(1)])

tv_stand[0].instance_id = 'tv_stand_0'
single_bed[0].instance_id = 'single_bed_0'
nightstand_A[0].instance_id = 'nightstand_A_0'
wardrobe[0].instance_id = 'wardrobe_0'
cushion[0].instance_id = 'cushion_0'
nightstand_B[0].instance_id = 'nightstand_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

tv_stand[0].position = [3.1100105229683375, 3.5202961530684065, 0.25]
tv_stand[0].rotation = [0, 0, 0]
single_bed[0].position = [0.48479980347762347, 0.25697466934194707, 0.55]
single_bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [3.107069363293384, 3.2842487227205215, 0.25]
nightstand_A[0].rotation = [0, 0, 0]
wardrobe[0].position = [3.375430721175034, 1.2286720929198065, 1.1]
wardrobe[0].rotation = [0, 0, 0]
cushion[0].position = [0.43509920883880243, 0.18206652282080693, 0.09]
cushion[0].rotation = [0, 0, 0]
nightstand_B[0].position = [2.0656573696591622, 1.8852451195694946, 0.25]
nightstand_B[0].rotation = [0, 0, 0]
tv_stand[0].position = [3.1100105229683375, 3.5202961530684065, 0.25]
tv_stand[0].rotation = [0, 0, 0]
single_bed[0].position = [0.48479980347762347, 0.25697466934194707, 0.55]
single_bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [3.107069363293384, 3.2842487227205215, 0.25]
nightstand_A[0].rotation = [0, 0, 0]
wardrobe[0].position = [3.375430721175034, 1.2286720929198065, 1.1]
wardrobe[0].rotation = [0, 0, 0]
cushion[0].position = [0.43509920883880243, 0.18206652282080693, 0.09]
cushion[0].rotation = [0, 0, 0]
nightstand_B[0].position = [2.0656573696591622, 1.8852451195694946, 0.25]
nightstand_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the coordinates of the supplied boundary: the main room is
# x=0..3.49, y=0..3.93, with a northern alcove extending to y=4.72.
# The bed's head occupies that alcove; its foot faces the southern TV stand.
single_bed[0].position = [1.91, 3.67, 0.55]
single_bed[0].rotation = [0, 0, radians(270)]

tv_stand[0].position = [1.91, 0.20, 0.25]
tv_stand[0].rotation = [0, 0, radians(90)]

# Flank the bed near its head, but keep both cabinets below the alcove's
# narrower opening. Each cabinet has a 0.155 m lateral gap from the bed.
nightstand_A[0].position = [0.98, 3.65, 0.25]
nightstand_A[0].rotation = [0, 0, radians(270)]

nightstand_B[0].position = [2.84, 3.65, 0.25]
nightstand_B[0].rotation = [0, 0, radians(270)]

# The wardrobe backs onto the west wall and opens into the clear central
# area. It does not obstruct either bedside cabinet or the bed's foot.
wardrobe[0].position = [0.30, 1.55, 1.10]
wardrobe[0].rotation = [0, 0, 0]

# Support the cushion on the bed, toward its head.
cushion[0].position = [1.91, 4.05, 1.19]
cushion[0].rotation = [0, 0, radians(270)]

# Establish support and wall relationships first.
solver.on_top_of(cushion[0], single_bed[0])
solver.against_wall(tv_stand[0], walls[1])
solver.against_wall(single_bed[0], walls[5])
solver.against_wall(wardrobe[0], walls[0])

# Fixed-position constraints preserve the nonoverlapping footprints,
# bedside ordering, and circulation space. Each new instance receives
# its own position-based constraint.
for placed_instance, target_position in [
    (single_bed[0], [1.91, 3.67, 0.55]),
    (tv_stand[0], [1.91, 0.20, 0.25]),
    (nightstand_A[0], [0.98, 3.65, 0.25]),
    (nightstand_B[0], [2.84, 3.65, 0.25]),
    (wardrobe[0], [0.30, 1.55, 1.10]),
    (cushion[0], [1.91, 4.05, 1.19]),
]:
    solver.distance_constraint(
        placed_instance,
        AssetInstance(position=target_position),
        min_distance=0,
        max_distance=0,
        weight=10,
    )

# Every new instance also receives an orientation constraint.
solver.point_towards(single_bed[0], tv_stand[0])
solver.point_towards(tv_stand[0], single_bed[0])
solver.align_with(nightstand_A[0], single_bed[0])
solver.align_with(nightstand_B[0], single_bed[0])
solver.align_with(cushion[0], single_bed[0])
solver.point_towards(
    wardrobe[0],
    AssetInstance(position=[2.00, 1.55, 1.10]),
)

solver.constraints = []
wardrobe[0].position = [0.30041784048080444, 1.5499999523162842, 1.100000023841858]
wardrobe[0].rotation = [0, 0, 0.00421755017240569]
wardrobe[0].optimize = 2
cushion[0].position = [1.909999966621399, 4.050000190734863, 1.190000057220459]
cushion[0].rotation = [0, 0, -1.6098554469150728]
cushion[0].optimize = 2
single_bed[0].position = [2.015031099319458, 3.554340362548828, 0.550000011920929]
single_bed[0].rotation = [0, 0, -1.6450321316729704]
single_bed[0].optimize = 2
tv_stand[0].position = [1.909999966621399, 0.2026815563440323, 0.25]
tv_stand[0].rotation = [0, 0, 1.5769367896688014]
tv_stand[0].optimize = 2
nightstand_A[0].position = [0.9800000190734863, 3.6500000953674316, 0.25]
nightstand_A[0].rotation = [0, 0, -1.6066313782220802]
nightstand_A[0].optimize = 2
nightstand_B[0].position = [2.8399999141693115, 3.6500000953674316, 0.25]
nightstand_B[0].rotation = [0, 0, -1.6066313782220802]
nightstand_B[0].optimize = 2

