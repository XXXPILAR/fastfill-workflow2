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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[9.18, 0.00, 0.00]),
    Wall(corner1=[9.18, 0.00, 0.00], corner2=[9.18, 6.51, 0.00]),
    Wall(corner1=[9.18, 6.51, 0.00], corner2=[0.00, 6.51, 0.00]),
    Wall(corner1=[0.00, 6.51, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bed = Assets(description="A white bed with a simple design, featuring a headboard and footboard. It has a gray blanket and white pillows neatly arranged on it.", size=[2.10, 1.10, 1.00], placements=[AssetInstance() for _ in range(1)])
dresser_A = Assets(description="A wooden wardrobe with a simple design, featuring a smooth surface and clean lines. It has a rectangular shape with a slightly protruding frame around the edges.", size=[0.60, 1.20, 1.90], placements=[AssetInstance() for _ in range(1)])
lamp_table = Assets(description="A tall floor lamp with a cylindrical white shade featuring vertical slats and a black metal base.", size=[0.40, 0.40, 1.60], placements=[AssetInstance() for _ in range(1)])
seat = Assets(description="A classic rocking chair with a dark wooden frame and upholstered seat and backrest. The seat and backrest feature tufted leather upholstery, providing both comfort and style. The curved armrests and rockers add to its traditional design.", size=[0.95, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
dresser_B = Assets(description="A white dresser with black accents and multiple drawers, designed for storage purposes.", size=[0.50, 1.40, 0.85], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="A wooden nightstand with two drawers, featuring a smooth finish and slightly curved edges. It has four slender legs that taper towards the bottom.", size=[0.45, 0.55, 0.65], placements=[AssetInstance() for _ in range(1)])

bed[0].instance_id = 'bed_0'
dresser_A[0].instance_id = 'dresser_A_0'
lamp_table[0].instance_id = 'lamp_table_0'
seat[0].instance_id = 'seat_0'
dresser_B[0].instance_id = 'dresser_B_0'
cabinet[0].instance_id = 'cabinet_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

bed[0].position = [7.076910767977355, 4.2548430313683285, 0.5]
bed[0].rotation = [0, 0, 0]
dresser_A[0].position = [4.141957552368747, 4.7966859681074885, 0.95]
dresser_A[0].rotation = [0, 0, 0]
lamp_table[0].position = [2.2322219474117766, 6.21117184156448, 0.8]
lamp_table[0].rotation = [0, 0, 0]
seat[0].position = [1.8257417795002089, 3.57395839732671, 0.55]
seat[0].rotation = [0, 0, 0]
dresser_B[0].position = [1.9607488254000018, 1.4173395410184897, 0.425]
dresser_B[0].rotation = [0, 0, 0]
cabinet[0].position = [5.778334044964583, 0.8646750851832387, 0.325]
cabinet[0].rotation = [0, 0, 0]
bed[0].position = [7.076910767977355, 4.2548430313683285, 0.5]
bed[0].rotation = [0, 0, 0]
dresser_A[0].position = [4.141957552368747, 4.7966859681074885, 0.95]
dresser_A[0].rotation = [0, 0, 0]
lamp_table[0].position = [2.2322219474117766, 6.21117184156448, 0.8]
lamp_table[0].rotation = [0, 0, 0]
seat[0].position = [1.8257417795002089, 3.57395839732671, 0.55]
seat[0].rotation = [0, 0, 0]
dresser_B[0].position = [1.9607488254000018, 1.4173395410184897, 0.425]
dresser_B[0].rotation = [0, 0, 0]
cabinet[0].position = [5.778334044964583, 0.8646750851832387, 0.325]
cabinet[0].rotation = [0, 0, 0]

solver.constraints = []

# Initial placements use each asset's half-height so every object rests on the floor.
# The bed and rocking chair form a central sleeping/seating arrangement, while the
# storage pieces remain along the perimeter and leave a wide circulation aisle.
bed[0].position = [4.20, 1.35, 0.50]
bed[0].rotation = [0, 0, radians(90)]

dresser_A[0].position = [8.88, 3.15, 0.95]
dresser_A[0].rotation = [0, 0, radians(180)]

lamp_table[0].position = [5.65, 1.05, 0.80]
lamp_table[0].rotation = [0, 0, radians(135)]

seat[0].position = [4.20, 4.25, 0.55]
seat[0].rotation = [0, 0, radians(-90)]

dresser_B[0].position = [0.25, 5.35, 0.425]
dresser_B[0].rotation = [0, 0, 0]

cabinet[0].position = [5.65, 0.275, 0.325]
cabinet[0].rotation = [0, 0, radians(90)]


# Fixed anchors preserve the proposed zones if the solver needs to make the
# arrangement physically feasible.
bed_anchor = AssetInstance(position=[4.20, 1.35, 0.50])
seat_anchor = AssetInstance(position=[4.20, 4.25, 0.55])
lamp_anchor = AssetInstance(position=[5.65, 1.05, 0.80])

# The principal semantic requirement is specified first: the bed faces the seat.
solver.point_towards(bed[0], seat[0])
solver.distance_constraint(bed[0], bed_anchor, 0, 0, weight=10)

# Keep the chair opposite the bed and orient it toward the sleeping area.
solver.point_towards(seat[0], bed[0])
solver.distance_constraint(seat[0], seat_anchor, 0, 0, weight=10)
solver.distance_constraint(seat[0], bed[0], 2.75, 3.15, weight=10)

# Place the wardrobe against the right wall and make its front face into the room.
solver.against_wall(dresser_A[0], walls[1])
solver.point_towards(dresser_A[0], bed[0])
solver.distance_constraint(
    dresser_A[0],
    AssetInstance(position=[8.88, 3.15, 0.95]),
    0,
    0,
    weight=10,
)

# Place the low dresser against the left wall, also facing into the room.
solver.against_wall(dresser_B[0], walls[3])
solver.point_towards(dresser_B[0], bed[0])
solver.distance_constraint(
    dresser_B[0],
    AssetInstance(position=[0.25, 5.35, 0.425]),
    0,
    0,
    weight=10,
)

# The nightstand is explicitly constrained against the bottom wall, close enough
# to serve the bed without blocking the bed-to-chair circulation path.
solver.against_wall(cabinet[0], walls[0])
solver.point_towards(cabinet[0], bed[0])
solver.distance_constraint(
    cabinet[0],
    AssetInstance(position=[5.65, 0.275, 0.325]),
    0,
    0,
    weight=10,
)
solver.distance_constraint(cabinet[0], bed[0], 1.60, 2.15, weight=1)

# Keep the floor lamp beside the nightstand and direct its shade toward the bed.
solver.distance_constraint(lamp_table[0], lamp_anchor, 0, 0, weight=10)
solver.point_towards(lamp_table[0], bed[0])
solver.distance_constraint(lamp_table[0], cabinet[0], 0.70, 0.90, weight=10)
solver.distance_constraint(lamp_table[0], bed[0], 1.25, 1.85, weight=1)

solver.constraints = []
seat[0].position = [4.199999809265137, 4.25, 0.550000011920929]
seat[0].rotation = [0, 0, -1.5550883628776802]
seat[0].optimize = 2
dresser_B[0].position = [0.2499999850988388, 5.349999904632568, 0.42500001192092896]
dresser_B[0].rotation = [0, 0, 3.4881489071311764e-08]
dresser_B[0].optimize = 2
cabinet[0].position = [5.650000095367432, 0.22499999403953552, 0.32499998807907104]
cabinet[0].rotation = [0, 0, 1.5707963694097669]
cabinet[0].optimize = 2
lamp_table[0].position = [5.650000095367432, 1.0499999523162842, 0.800000011920929]
lamp_table[0].rotation = [0, 0, 2.371902466007656]
lamp_table[0].optimize = 2
bed[0].position = [4.199999809265137, 1.350000023841858, 0.5]
bed[0].rotation = [0, 0, 1.605353845621573]
bed[0].optimize = 2
dresser_A[0].position = [8.883864402770996, 3.1500000953674316, 0.949999988079071]
dresser_A[0].rotation = [0, 0, -3.1415926093562647]
dresser_A[0].optimize = 2

