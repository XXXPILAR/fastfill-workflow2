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
    Wall(corner1=[4.70, 0.00, 0.00], corner2=[4.70, 3.00, 0.00]),
    Wall(corner1=[4.70, 3.00, 0.00], corner2=[5.70, 3.00, 0.00]),
    Wall(corner1=[5.70, 3.00, 0.00], corner2=[5.70, 5.20, 0.00]),
    Wall(corner1=[5.70, 5.20, 0.00], corner2=[4.70, 5.20, 0.00]),
    Wall(corner1=[4.70, 5.20, 0.00], corner2=[4.70, 5.70, 0.00]),
    Wall(corner1=[4.70, 5.70, 0.00], corner2=[0.00, 5.70, 0.00]),
    Wall(corner1=[0.00, 5.70, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.70, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
shelf_A = Assets(description="shelf", size=[0.30, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="book", size=[0.24, 0.18, 0.04], placements=[AssetInstance() for _ in range(1)])
bottle_A = Assets(description="bottle", size=[0.08, 0.08, 0.30], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="table", size=[0.95, 1.80, 0.76], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.30, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="lamp", size=[0.30, 0.30, 0.50], placements=[AssetInstance() for _ in range(1)])
cup_A = Assets(description="cup", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="chair", size=[0.55, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
shelf_C = Assets(description="shelf", size=[0.30, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.30, 0.30, 0.50], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.55, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="chair", size=[0.55, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
chair_D = Assets(description="chair", size=[0.55, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="bottle", size=[0.08, 0.08, 0.30], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="book", size=[0.24, 0.18, 0.04], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.45, 1.20, 0.85], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.40, 0.80, 0.85], placements=[AssetInstance() for _ in range(1)])
cabinet_C = Assets(description="cabinet", size=[0.40, 0.80, 0.85], placements=[AssetInstance() for _ in range(1)])
bottle_C = Assets(description="bottle", size=[0.09, 0.09, 0.28], placements=[AssetInstance() for _ in range(1)])
lamp_C = Assets(description="lamp", size=[0.30, 0.30, 0.50], placements=[AssetInstance() for _ in range(1)])
plate = Assets(description="plate", size=[0.27, 0.27, 0.03], placements=[AssetInstance() for _ in range(1)])
cup_B = Assets(description="cup", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
cabinet_D = Assets(description="cabinet", size=[0.40, 0.80, 0.85], placements=[AssetInstance() for _ in range(1)])
lamp_D = Assets(description="lamp", size=[0.40, 0.40, 1.60], placements=[AssetInstance() for _ in range(1)])

shelf_A[0].instance_id = 'shelf_A_0'
book_A[0].instance_id = 'book_A_0'
bottle_A[0].instance_id = 'bottle_A_0'
table[0].instance_id = 'table_0'
shelf_B[0].instance_id = 'shelf_B_0'
lamp_A[0].instance_id = 'lamp_A_0'
cup_A[0].instance_id = 'cup_A_0'
chair_A[0].instance_id = 'chair_A_0'
shelf_C[0].instance_id = 'shelf_C_0'
lamp_B[0].instance_id = 'lamp_B_0'
chair_B[0].instance_id = 'chair_B_0'
chair_C[0].instance_id = 'chair_C_0'
chair_D[0].instance_id = 'chair_D_0'
bottle_B[0].instance_id = 'bottle_B_0'
book_B[0].instance_id = 'book_B_0'
cabinet_A[0].instance_id = 'cabinet_A_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
cabinet_C[0].instance_id = 'cabinet_C_0'
bottle_C[0].instance_id = 'bottle_C_0'
lamp_C[0].instance_id = 'lamp_C_0'
plate[0].instance_id = 'plate_0'
cup_B[0].instance_id = 'cup_B_0'
cabinet_D[0].instance_id = 'cabinet_D_0'
lamp_D[0].instance_id = 'lamp_D_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

shelf_A[0].position = [4.435420813194791, 4.318420472034447, 0.9]
shelf_A[0].rotation = [0, 0, 0]
book_A[0].position = [1.5199509839144725, 5.428792571299029, 0.0175]
book_A[0].rotation = [0, 0, 0]
bottle_A[0].position = [3.5782557031503446, 3.7376055015577885, 0.15]
bottle_A[0].rotation = [0, 0, 0]
table[0].position = [1.1399371724717906, 5.256015342174107, 0.38]
table[0].rotation = [0, 0, 0]
shelf_B[0].position = [4.935139402551713, 3.144227926671696, 0.9]
shelf_B[0].rotation = [0, 0, 0]
lamp_A[0].position = [0.06719252961707314, 4.394895383987185, 0.25]
lamp_A[0].rotation = [0, 0, 0]
cup_A[0].position = [2.5002583478452083, 3.814536009781342, 0.05]
cup_A[0].rotation = [0, 0, 0]
chair_A[0].position = [2.848760270993174, 2.246792528184248, 0.45]
chair_A[0].rotation = [0, 0, 0]
shelf_C[0].position = [5.473181384669763, 3.1294218972762615, 0.9]
shelf_C[0].rotation = [0, 0, 0]
lamp_B[0].position = [5.19059198754669, 3.028036680446623, 0.25]
lamp_B[0].rotation = [0, 0, 0]
chair_B[0].position = [0.6978324062114459, 0.03961447817650409, 0.45]
chair_B[0].rotation = [0, 0, 0]
chair_C[0].position = [1.222978990365746, 5.14486734983534, 0.45]
chair_C[0].rotation = [0, 0, 0]
chair_D[0].position = [0.8016779160484957, 1.5312114487049233, 0.45]
chair_D[0].rotation = [0, 0, 0]
bottle_B[0].position = [0.075198995133969, 2.6407357015490955, 0.15]
bottle_B[0].rotation = [0, 0, 0]
book_B[0].position = [3.5923333534576014, 4.420323804807331, 0.0175]
book_B[0].rotation = [0, 0, 0]
cabinet_A[0].position = [0.667528534488315, 4.787724528840047, 0.425]
cabinet_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [2.5458027224211333, 3.0281266832571134, 0.425]
cabinet_B[0].rotation = [0, 0, 0]
cabinet_C[0].position = [0.29470176314442686, 2.75061510620136, 0.425]
cabinet_C[0].rotation = [0, 0, 0]
bottle_C[0].position = [1.0758502832316785, 1.4102896346467182, 0.14]
bottle_C[0].rotation = [0, 0, 0]
lamp_C[0].position = [0.5371050779610416, 2.4503661286059715, 0.25]
lamp_C[0].rotation = [0, 0, 0]
plate[0].position = [2.375677709172666, 4.4400473092779515, 0.0125]
plate[0].rotation = [0, 0, 0]
cup_B[0].position = [3.93085287195376, 4.968430469705806, 0.05]
cup_B[0].rotation = [0, 0, 0]
cabinet_D[0].position = [3.8072266798643315, 0.6274644954947283, 0.425]
cabinet_D[0].rotation = [0, 0, 0]
lamp_D[0].position = [5.206645852231396, 3.8904211587764768, 0.8]
lamp_D[0].rotation = [0, 0, 0]
shelf_A[0].position = [4.435420813194791, 4.318420472034447, 0.9]
shelf_A[0].rotation = [0, 0, 0]
book_A[0].position = [1.5199509839144725, 5.428792571299029, 0.0175]
book_A[0].rotation = [0, 0, 0]
bottle_A[0].position = [3.5782557031503446, 3.7376055015577885, 0.15]
bottle_A[0].rotation = [0, 0, 0]
table[0].position = [1.1399371724717906, 5.256015342174107, 0.38]
table[0].rotation = [0, 0, 0]
shelf_B[0].position = [4.935139402551713, 3.144227926671696, 0.9]
shelf_B[0].rotation = [0, 0, 0]
lamp_A[0].position = [0.06719252961707314, 4.394895383987185, 0.25]
lamp_A[0].rotation = [0, 0, 0]
cup_A[0].position = [2.5002583478452083, 3.814536009781342, 0.05]
cup_A[0].rotation = [0, 0, 0]
chair_A[0].position = [2.848760270993174, 2.246792528184248, 0.45]
chair_A[0].rotation = [0, 0, 0]
shelf_C[0].position = [5.473181384669763, 3.1294218972762615, 0.9]
shelf_C[0].rotation = [0, 0, 0]
lamp_B[0].position = [5.19059198754669, 3.028036680446623, 0.25]
lamp_B[0].rotation = [0, 0, 0]
chair_B[0].position = [0.6978324062114459, 0.03961447817650409, 0.45]
chair_B[0].rotation = [0, 0, 0]
chair_C[0].position = [1.222978990365746, 5.14486734983534, 0.45]
chair_C[0].rotation = [0, 0, 0]
chair_D[0].position = [0.8016779160484957, 1.5312114487049233, 0.45]
chair_D[0].rotation = [0, 0, 0]
bottle_B[0].position = [0.075198995133969, 2.6407357015490955, 0.15]
bottle_B[0].rotation = [0, 0, 0]
book_B[0].position = [3.5923333534576014, 4.420323804807331, 0.0175]
book_B[0].rotation = [0, 0, 0]
cabinet_A[0].position = [0.667528534488315, 4.787724528840047, 0.425]
cabinet_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [2.5458027224211333, 3.0281266832571134, 0.425]
cabinet_B[0].rotation = [0, 0, 0]
cabinet_C[0].position = [0.29470176314442686, 2.75061510620136, 0.425]
cabinet_C[0].rotation = [0, 0, 0]
bottle_C[0].position = [1.0758502832316785, 1.4102896346467182, 0.14]
bottle_C[0].rotation = [0, 0, 0]
lamp_C[0].position = [0.5371050779610416, 2.4503661286059715, 0.25]
lamp_C[0].rotation = [0, 0, 0]
plate[0].position = [2.375677709172666, 4.4400473092779515, 0.0125]
plate[0].rotation = [0, 0, 0]
cup_B[0].position = [3.93085287195376, 4.968430469705806, 0.05]
cup_B[0].rotation = [0, 0, 0]
cabinet_D[0].position = [3.8072266798643315, 0.6274644954947283, 0.425]
cabinet_D[0].rotation = [0, 0, 0]
lamp_D[0].position = [5.206645852231396, 3.8904211587764768, 0.8]
lamp_D[0].rotation = [0, 0, 0]

solver.constraints = []

# The supplied wall coordinates define the usable footprint.
# Asset IDs follow the order in the asset list: o0011 is chair_C,
# o0012 is chair_D, o0004 is shelf_B, and o0015 is cabinet_A.
#
# Keep the bottom doorway at x=2.64 and the top doorway at x=3.35
# unobstructed. Place tall storage along the window-free west wall.

def place_instance(asset_group, xyz, yaw_degrees, wall_index=None, support=None):
    instance = asset_group[0]
    instance.position = list(xyz)
    instance.rotation = [0, 0, radians(yaw_degrees)]

    # Register support and wall relationships before positional refinement.
    if support is not None:
        solver.on_top_of(instance, support)
    if wall_index is not None:
        solver.against_wall(instance, walls[wall_index])

    # Fixed references preserve both the clear circulation routes and the
    # non-overlapping arrangement; these are references, not additional assets.
    reference = AssetInstance(
        position=list(xyz),
        rotation=[0, 0, radians(yaw_degrees)]
    )
    solver.distance_constraint(instance, reference, 0, 0, weight=10)
    solver.align_with(instance, reference)


# West-wall shelves face east into the room.
place_instance(shelf_A, [0.15, 1.10, 0.90], 0, wall_index=6)
place_instance(shelf_B, [0.15, 2.90, 0.90], 0, wall_index=6)
place_instance(shelf_C, [0.15, 4.70, 0.90], 0, wall_index=6)

# Cabinets occupy solid north/south wall sections, outside both door openings.
# Local x is cabinet depth, so rotating 90 degrees puts the back on the south wall.
place_instance(cabinet_A, [0.95, 0.225, 0.425], 90, wall_index=7)
place_instance(cabinet_B, [1.00, 5.50, 0.425], 270, wall_index=5)
place_instance(cabinet_C, [2.10, 5.50, 0.425], 270, wall_index=5)
place_instance(cabinet_D, [3.90, 0.20, 0.425], 90, wall_index=7)

# Central table: its long axis runs north–south.
# The east-side circulation strip remains open between the two doors.
place_instance(table, [2.10, 2.90, 0.38], 0)

# Opposing east/west chairs put the table directly between chair_D and chair_C.
# chair_C faces west toward shelf_B, as requested.
place_instance(chair_C, [3.05, 2.90, 0.45], 180)
place_instance(chair_D, [1.15, 2.90, 0.45], 0)
solver.point_towards(chair_C[0], shelf_B[0])
solver.point_towards(chair_D[0], table[0])
solver.align_with(chair_D[0], chair_C[0], angle=180)
solver.distance_constraint(chair_C[0], table[0], 0.95, 1.05, weight=10)
solver.distance_constraint(chair_D[0], table[0], 0.95, 1.05, weight=10)
solver.distance_constraint(chair_C[0], chair_D[0], 1.90, 1.90, weight=10)

# Two additional chairs serve the short ends, with a gap from the tabletop edge.
place_instance(chair_A, [2.10, 1.50, 0.45], 90)
place_instance(chair_B, [2.10, 4.30, 0.45], 270)
solver.point_towards(chair_A[0], table[0])
solver.point_towards(chair_B[0], table[0])
solver.distance_constraint(chair_A[0], table[0], 1.40, 1.45)
solver.distance_constraint(chair_B[0], table[0], 1.40, 1.45)

# Tabletop objects rest at table height plus half their own heights.
# Distinct footprints leave the middle of the table useful.
place_instance(book_A, [1.90, 2.40, 0.78], 0, support=table[0])
place_instance(bottle_A, [2.30, 2.40, 0.91], 0, support=table[0])
place_instance(cup_A, [2.30, 2.75, 0.81], 0, support=table[0])
place_instance(plate, [2.05, 3.15, 0.775], 0, support=table[0])
place_instance(cup_B, [2.30, 3.50, 0.81], 0, support=table[0])
place_instance(bottle_B, [1.85, 3.60, 0.91], 0, support=table[0])

# Small lamps sit on cabinets rather than on the floor.
# Their complete footprints fit inside their supporting cabinet tops.
place_instance(lamp_A, [0.70, 0.225, 1.10], 90, support=cabinet_A[0])
place_instance(lamp_B, [1.00, 5.50, 1.10], 270, support=cabinet_B[0])
place_instance(lamp_C, [3.90, 0.20, 1.10], 90, support=cabinet_D[0])

# Separate book and bottle footprints on the remaining north-wall cabinet.
place_instance(book_B, [2.05, 5.50, 0.87], 0, support=cabinet_C[0])
place_instance(bottle_C, [2.32, 5.50, 0.99], 0, support=cabinet_C[0])

# The tall lamp is a floor-standing fixture in the east window bay.
# It is clear of the central seating group and both doorway approaches.
place_instance(lamp_D, [5.25, 4.10, 0.80], 180)
solver.point_towards(lamp_D[0], table[0])
solver.distance_constraint(lamp_D[0], chair_C[0], 2.40, None)

solver.constraints = []
bottle_A[0].position = [2.299999952316284, 2.4000000953674316, 0.9099999666213989]
bottle_A[0].rotation = [0, 0, 0.01256637125682779]
bottle_A[0].optimize = 2
plate[0].position = [2.049999952316284, 3.1500000953674316, 0.7749999761581421]
plate[0].rotation = [0, 0, 0.01256637125682779]
plate[0].optimize = 2
bottle_C[0].position = [2.319999933242798, 5.5, 0.9900000095367432]
bottle_C[0].rotation = [0, 0, 0.01256637125682779]
bottle_C[0].optimize = 2
cabinet_C[0].position = [2.0999999046325684, 5.5045976638793945, 0.42500001192092896]
cabinet_C[0].rotation = [0, 0, -1.5707248399955114]
cabinet_C[0].optimize = 2
cabinet_D[0].position = [3.9000000953674316, 0.19998234510421753, 0.42500001192092896]
cabinet_D[0].rotation = [0, 0, 1.5707466041709104]
cabinet_D[0].optimize = 2
chair_C[0].position = [2.990905523300171, 2.9000000953674316, 0.44999998807907104]
chair_C[0].rotation = [0, 0, -3.1164599134799373]
chair_C[0].optimize = 2
lamp_C[0].position = [3.9000000953674316, 0.20000000298023224, 1.100000023841858]
lamp_C[0].rotation = [0, 0, 1.5833626980517244]
lamp_C[0].optimize = 2
table[0].position = [2.0999999046325684, 2.9000000953674316, 0.3799999952316284]
table[0].rotation = [0, 0, 0.053407073383009665]
table[0].optimize = 2
book_B[0].position = [2.049999952316284, 5.5, 0.8700000047683716]
book_B[0].rotation = [0, 0, 0.01256637125682779]
book_B[0].optimize = 2
bottle_B[0].position = [1.850000023841858, 3.5999999046325684, 0.9099999666213989]
bottle_B[0].rotation = [0, 0, 0.01256637125682779]
bottle_B[0].optimize = 2
shelf_B[0].position = [0.5988668203353882, 2.9000000953674316, 0.8999999761581421]
shelf_B[0].rotation = [0, 0, 1.5782405327959559]
shelf_B[0].optimize = 2
cup_A[0].position = [2.299999952316284, 2.75, 0.8100000023841858]
cup_A[0].rotation = [0, 0, 0.01256637125682779]
cup_A[0].optimize = 2
cabinet_A[0].position = [0.949999988079071, 0.22498956322669983, 0.42500001192092896]
cabinet_A[0].rotation = [0, 0, 1.570746569944807]
cabinet_A[0].optimize = 2
shelf_C[0].position = [0.15002697706222534, 4.699999809265137, 0.8999999761581421]
shelf_C[0].rotation = [0, 0, -4.70800729483976e-05]
shelf_C[0].optimize = 2
shelf_A[0].position = [0.15002697706222534, 1.100000023841858, 0.8999999761581421]
shelf_A[0].rotation = [0, 0, -4.70800729483976e-05]
shelf_A[0].optimize = 2
chair_B[0].position = [2.0999999046325684, 4.300000190734863, 0.44999998807907104]
chair_B[0].rotation = [0, 0, -1.5550883628776802]
chair_B[0].optimize = 2
lamp_D[0].position = [5.25, 4.099999904632568, 0.800000011920929]
lamp_D[0].rotation = [0, 0, -3.0528097415979274]
lamp_D[0].optimize = 2
cup_B[0].position = [2.299999952316284, 3.5, 0.8100000023841858]
cup_B[0].rotation = [0, 0, 0.01256637125682779]
cup_B[0].optimize = 2
cabinet_B[0].position = [1.0, 5.5046000480651855, 0.42500001192092896]
cabinet_B[0].rotation = [0, 0, -1.5708460527582073]
cabinet_B[0].optimize = 2
chair_D[0].position = [1.091949462890625, 2.9000000953674316, 0.44999998807907104]
chair_D[0].rotation = [0, 0, 0.025146608358361418]
chair_D[0].optimize = 2
chair_A[0].position = [2.0999999046325684, 1.5, 0.44999998807907104]
chair_A[0].rotation = [0, 0, 1.586504290712113]
chair_A[0].optimize = 2
lamp_B[0].position = [1.0, 5.5, 1.100000023841858]
lamp_B[0].rotation = [0, 0, -1.5582299555380688]
lamp_B[0].optimize = 2
lamp_A[0].position = [0.699999988079071, 0.22499999403953552, 1.100000023841858]
lamp_A[0].rotation = [0, 0, 1.5833626980517244]
lamp_A[0].optimize = 2
book_A[0].position = [1.899999976158142, 2.4000000953674316, 0.7799999713897705]
book_A[0].rotation = [0, 0, 0.01256637125682779]
book_A[0].optimize = 2

