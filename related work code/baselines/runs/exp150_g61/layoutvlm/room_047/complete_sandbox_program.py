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
bed = Assets(description="A white bed with a simple design, featuring a headboard and footboard. It has a gray blanket and white pillows neatly arranged on it.", size=[2.15, 1.60, 1.05], placements=[AssetInstance() for _ in range(1)])
dresser_A = Assets(description="A wooden wardrobe with a simple design, featuring a smooth surface and clean lines. It has a rectangular shape with a slightly protruding frame around the edges.", size=[0.60, 1.40, 2.00], placements=[AssetInstance() for _ in range(1)])
lamp_table = Assets(description="A tall floor lamp with a cylindrical white shade featuring vertical slats and a black metal base.", size=[0.40, 0.40, 1.60], placements=[AssetInstance() for _ in range(1)])
seat = Assets(description="A classic rocking chair with a dark wooden frame and upholstered seat and backrest. The seat and backrest feature tufted leather upholstery, providing both comfort and style. The curved armrests and rockers add to its traditional design.", size=[1.05, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
dresser_B = Assets(description="A white dresser with black accents and multiple drawers, designed for storage purposes.", size=[0.50, 1.40, 0.85], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="A wooden nightstand with two drawers, featuring a smooth finish and slightly curved edges. It has four slender legs that taper towards the bottom.", size=[0.40, 0.50, 0.60], placements=[AssetInstance() for _ in range(1)])

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

bed[0].position = [1.8766835914263862, 3.4953237999515627, 0.525]
bed[0].rotation = [0, 0, 0]
dresser_A[0].position = [5.513177045796407, 6.1193227916266295, 1.0]
dresser_A[0].rotation = [0, 0, 0]
lamp_table[0].position = [0.6660120086582978, 4.145590892582371, 0.8]
lamp_table[0].rotation = [0, 0, 0]
seat[0].position = [1.2165388278783225, 3.8947183261034284, 0.55]
seat[0].rotation = [0, 0, 0]
dresser_B[0].position = [7.470751685744979, 3.7240468003311737, 0.425]
dresser_B[0].rotation = [0, 0, 0]
cabinet[0].position = [5.406486689635243, 0.47956328747832344, 0.3]
cabinet[0].rotation = [0, 0, 0]
bed[0].position = [1.8766835914263862, 3.4953237999515627, 0.525]
bed[0].rotation = [0, 0, 0]
dresser_A[0].position = [5.513177045796407, 6.1193227916266295, 1.0]
dresser_A[0].rotation = [0, 0, 0]
lamp_table[0].position = [0.6660120086582978, 4.145590892582371, 0.8]
lamp_table[0].rotation = [0, 0, 0]
seat[0].position = [1.2165388278783225, 3.8947183261034284, 0.55]
seat[0].rotation = [0, 0, 0]
dresser_B[0].position = [7.470751685744979, 3.7240468003311737, 0.425]
dresser_B[0].rotation = [0, 0, 0]
cabinet[0].position = [5.406486689635243, 0.47956328747832344, 0.3]
cabinet[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the explicit wall coordinates: the room spans x=0..9.18, y=0..6.51.
# The bed's head is at the west wall, with its foot facing the rocking chair.
# All positions are bounding-box centers, so floor-standing objects use height / 2.
bed[0].position = [1.075, 3.60, 0.525]
bed[0].rotation = [0, 0, radians(0)]

seat[0].position = [5.60, 3.60, 0.55]
seat[0].rotation = [0, 0, radians(180)]

# Place the nightstand beside the head of the bed, touching the west wall.
# Its lower edge is 0.20 m beyond the bed's upper edge.
cabinet[0].position = [0.20, 4.85, 0.30]
cabinet[0].rotation = [0, 0, radians(0)]

# Separate storage along the east wall, with doors/drawers facing into the room.
dresser_A[0].position = [8.88, 5.00, 1.00]
dresser_A[0].rotation = [0, 0, radians(180)]

dresser_B[0].position = [8.93, 1.50, 0.425]
dresser_B[0].rotation = [0, 0, radians(180)]

# This is a floor lamp, not a tabletop lamp. Keep it beside the reading chair,
# clear of the chair's footprint and the main route between bed and storage.
lamp_table[0].position = [6.10, 4.50, 0.80]
lamp_table[0].rotation = [0, 0, radians(180)]

# Primary semantic constraints first.
solver.point_towards(bed[0], seat[0])
solver.point_towards(seat[0], bed[0])
solver.against_wall(cabinet[0], walls[3])
solver.against_wall(bed[0], walls[3])
solver.against_wall(dresser_A[0], walls[1])
solver.against_wall(dresser_B[0], walls[1])

# Fixed center targets preserve the calculated, non-overlapping arrangement.
# These are constraint references only, not additional scene furniture.
for placed_instance in (
    bed[0], seat[0], cabinet[0],
    dresser_A[0], dresser_B[0], lamp_table[0]
):
    solver.distance_constraint(
        placed_instance,
        AssetInstance(position=list(placed_instance.position)),
        min_distance=0,
        max_distance=0,
        weight=10,
    )

# Explicit orientations for every remaining new instance.
solver.align_with(cabinet[0], bed[0])
solver.align_with(dresser_A[0], bed[0], angle=180)
solver.align_with(dresser_B[0], dresser_A[0])
solver.align_with(lamp_table[0], seat[0])

# Preserve bedside and reading-area associations if secondary constraints
# are consulted during feasibility adjustment. Distances include z offsets.
solver.distance_constraint(cabinet[0], bed[0], 1.50, 1.65)
solver.distance_constraint(lamp_table[0], seat[0], 1.00, 1.15)
solver.distance_constraint(seat[0], bed[0], 4.40, 4.65)

solver.constraints = []
cabinet[0].position = [0.19999997317790985, 4.849999904632568, 0.30000001192092896]
cabinet[0].rotation = [0, 0, 4.1965277673135784e-08]
cabinet[0].optimize = 2
dresser_B[0].position = [8.93386459350586, 1.5, 0.42500001192092896]
dresser_B[0].rotation = [0, 0, -3.141592610351432]
dresser_B[0].optimize = 2
lamp_table[0].position = [6.099999904632568, 4.5, 0.800000011920929]
lamp_table[0].rotation = [0, 0, -3.11960150319319]
lamp_table[0].optimize = 2
dresser_A[0].position = [8.88386344909668, 5.0, 1.0]
dresser_A[0].rotation = [0, 0, -3.1415926104782277]
dresser_A[0].optimize = 2
seat[0].position = [5.599999904632568, 3.5999999046325684, 0.550000011920929]
seat[0].rotation = [0, 0, -3.1196015053037707]
seat[0].optimize = 2
bed[0].position = [1.0750000476837158, 3.5999999046325684, 0.5249999761581421]
bed[0].rotation = [0, 0, 4.2428366231861795e-08]
bed[0].optimize = 2

