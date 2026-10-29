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
    Wall(corner1=[5.75, 0.00, 0.00], corner2=[5.75, 5.75, 0.00]),
    Wall(corner1=[5.75, 5.75, 0.00], corner2=[3.50, 5.75, 0.00]),
    Wall(corner1=[3.50, 5.75, 0.00], corner2=[3.50, 3.25, 0.00]),
    Wall(corner1=[3.50, 3.25, 0.00], corner2=[0.00, 3.25, 0.00]),
    Wall(corner1=[0.00, 3.25, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[5.75, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
table = Assets(description="table", size=[0.90, 1.80, 0.76], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="shelf", size=[0.25, 0.90, 0.04], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.25, 0.90, 0.04], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="chair", size=[0.54, 0.48, 0.88], placements=[AssetInstance() for _ in range(1)])
plate = Assets(description="plate", size=[0.27, 0.27, 0.03], placements=[AssetInstance() for _ in range(1)])
cup_A = Assets(description="cup", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.54, 0.48, 0.88], placements=[AssetInstance() for _ in range(1)])
bottle_A = Assets(description="bottle", size=[0.08, 0.08, 0.30], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="bottle", size=[0.08, 0.08, 0.28], placements=[AssetInstance() for _ in range(1)])
utensil = Assets(description="utensil", size=[0.21, 0.03, 0.01], placements=[AssetInstance() for _ in range(1)])
bottle_C = Assets(description="bottle", size=[0.07, 0.07, 0.30], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="lamp", size=[0.35, 0.35, 1.60], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.45, 1.40, 0.85], placements=[AssetInstance() for _ in range(1)])
pot_A = Assets(description="pot", size=[0.24, 0.24, 0.22], placements=[AssetInstance() for _ in range(1)])
shelf_C = Assets(description="shelf", size=[0.25, 0.80, 0.04], placements=[AssetInstance() for _ in range(1)])
shelf_D = Assets(description="shelf", size=[0.25, 0.80, 0.04], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.40, 1.00, 1.20], placements=[AssetInstance() for _ in range(1)])
pot_B = Assets(description="pot", size=[0.20, 0.20, 0.18], placements=[AssetInstance() for _ in range(1)])
shelf_E = Assets(description="shelf", size=[0.25, 1.00, 0.04], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="chair", size=[0.54, 0.48, 0.88], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.28, 0.28, 0.48], placements=[AssetInstance() for _ in range(1)])
vase_A = Assets(description="vase", size=[0.16, 0.16, 0.30], placements=[AssetInstance() for _ in range(1)])
cup_B = Assets(description="cup", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
pot_C = Assets(description="pot", size=[0.18, 0.18, 0.17], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="book", size=[0.04, 0.16, 0.24], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="book", size=[0.03, 0.18, 0.26], placements=[AssetInstance() for _ in range(1)])
book_C = Assets(description="book", size=[0.03, 0.15, 0.23], placements=[AssetInstance() for _ in range(1)])
vase_B = Assets(description="vase", size=[0.14, 0.14, 0.25], placements=[AssetInstance() for _ in range(1)])

table[0].instance_id = 'table_0'
shelf_A[0].instance_id = 'shelf_A_0'
shelf_B[0].instance_id = 'shelf_B_0'
chair_A[0].instance_id = 'chair_A_0'
plate[0].instance_id = 'plate_0'
cup_A[0].instance_id = 'cup_A_0'
chair_B[0].instance_id = 'chair_B_0'
bottle_A[0].instance_id = 'bottle_A_0'
bottle_B[0].instance_id = 'bottle_B_0'
utensil[0].instance_id = 'utensil_0'
bottle_C[0].instance_id = 'bottle_C_0'
lamp_A[0].instance_id = 'lamp_A_0'
cabinet_A[0].instance_id = 'cabinet_A_0'
pot_A[0].instance_id = 'pot_A_0'
shelf_C[0].instance_id = 'shelf_C_0'
shelf_D[0].instance_id = 'shelf_D_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
pot_B[0].instance_id = 'pot_B_0'
shelf_E[0].instance_id = 'shelf_E_0'
chair_C[0].instance_id = 'chair_C_0'
lamp_B[0].instance_id = 'lamp_B_0'
vase_A[0].instance_id = 'vase_A_0'
cup_B[0].instance_id = 'cup_B_0'
pot_C[0].instance_id = 'pot_C_0'
book_A[0].instance_id = 'book_A_0'
book_B[0].instance_id = 'book_B_0'
book_C[0].instance_id = 'book_C_0'
vase_B[0].instance_id = 'vase_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

table[0].position = [0.4114320579064528, 3.138081928713521, 0.38]
table[0].rotation = [0, 0, 0]
shelf_A[0].position = [4.132129838734894, 5.671920628195477, 0.02]
shelf_A[0].rotation = [0, 0, 0]
shelf_B[0].position = [3.5114674521106193, 5.2339513971168365, 0.02]
shelf_B[0].rotation = [0, 0, 0]
chair_A[0].position = [3.5328618555300855, 2.5037299633636496, 0.44]
chair_A[0].rotation = [0, 0, 0]
plate[0].position = [0.8228587710103482, 0.948824403685484, 0.0125]
plate[0].rotation = [0, 0, 0]
cup_A[0].position = [3.867284555133865, 1.0749059702759944, 0.05]
cup_A[0].rotation = [0, 0, 0]
chair_B[0].position = [1.0221339289552223, 1.270896563114222, 0.44]
chair_B[0].rotation = [0, 0, 0]
bottle_A[0].position = [3.888275966610871, 3.4995581028939253, 0.15]
bottle_A[0].rotation = [0, 0, 0]
bottle_B[0].position = [5.070361357921701, 1.3955864673049696, 0.14]
bottle_B[0].rotation = [0, 0, 0]
utensil[0].position = [3.9269631406672976, 4.140049023035628, 0.0075]
utensil[0].rotation = [0, 0, 0]
bottle_C[0].position = [5.730260532198757, 0.7541695339028173, 0.15]
bottle_C[0].rotation = [0, 0, 0]
lamp_A[0].position = [5.174611198423848, 4.4963328224153525, 0.8]
lamp_A[0].rotation = [0, 0, 0]
cabinet_A[0].position = [0.1991553321939532, 0.5140672300775899, 0.425]
cabinet_A[0].rotation = [0, 0, 0]
pot_A[0].position = [0.5941288953959787, 2.4307683014471544, 0.11]
pot_A[0].rotation = [0, 0, 0]
shelf_C[0].position = [0.5125361591503519, 2.662989793176579, 0.02]
shelf_C[0].rotation = [0, 0, 0]
shelf_D[0].position = [0.856935660369624, 1.041795240923986, 0.02]
shelf_D[0].rotation = [0, 0, 0]
cabinet_B[0].position = [4.995812804659241, 2.015846158369271, 0.6]
cabinet_B[0].rotation = [0, 0, 0]
pot_B[0].position = [3.8437477957172597, 5.243109945518635, 0.09]
pot_B[0].rotation = [0, 0, 0]
shelf_E[0].position = [3.7635844450199705, 1.6595322390469203, 0.02]
shelf_E[0].rotation = [0, 0, 0]
chair_C[0].position = [4.781645627705027, 0.9787783359013414, 0.44]
chair_C[0].rotation = [0, 0, 0]
lamp_B[0].position = [5.510241610333331, 2.541187800253457, 0.24]
lamp_B[0].rotation = [0, 0, 0]
vase_A[0].position = [4.856111816893391, 0.30947283726769464, 0.15]
vase_A[0].rotation = [0, 0, 0]
cup_B[0].position = [3.7457556904372438, 2.3524054832523835, 0.05]
cup_B[0].rotation = [0, 0, 0]
pot_C[0].position = [0.7631945965959083, 0.0866735670316561, 0.085]
pot_C[0].rotation = [0, 0, 0]
book_A[0].position = [2.6793690888225488, 0.879683193568421, 0.12]
book_A[0].rotation = [0, 0, 0]
book_B[0].position = [4.084113388282966, 2.2650019760343985, 0.13]
book_B[0].rotation = [0, 0, 0]
book_C[0].position = [4.250493144745006, 5.290984483889744, 0.115]
book_C[0].rotation = [0, 0, 0]
vase_B[0].position = [4.097617766019374, 4.4606533235001296, 0.125]
vase_B[0].rotation = [0, 0, 0]
table[0].position = [0.4114320579064528, 3.138081928713521, 0.38]
table[0].rotation = [0, 0, 0]
shelf_A[0].position = [4.132129838734894, 5.671920628195477, 0.02]
shelf_A[0].rotation = [0, 0, 0]
shelf_B[0].position = [3.5114674521106193, 5.2339513971168365, 0.02]
shelf_B[0].rotation = [0, 0, 0]
chair_A[0].position = [3.5328618555300855, 2.5037299633636496, 0.44]
chair_A[0].rotation = [0, 0, 0]
plate[0].position = [0.8228587710103482, 0.948824403685484, 0.0125]
plate[0].rotation = [0, 0, 0]
cup_A[0].position = [3.867284555133865, 1.0749059702759944, 0.05]
cup_A[0].rotation = [0, 0, 0]
chair_B[0].position = [1.0221339289552223, 1.270896563114222, 0.44]
chair_B[0].rotation = [0, 0, 0]
bottle_A[0].position = [3.888275966610871, 3.4995581028939253, 0.15]
bottle_A[0].rotation = [0, 0, 0]
bottle_B[0].position = [5.070361357921701, 1.3955864673049696, 0.14]
bottle_B[0].rotation = [0, 0, 0]
utensil[0].position = [3.9269631406672976, 4.140049023035628, 0.0075]
utensil[0].rotation = [0, 0, 0]
bottle_C[0].position = [5.730260532198757, 0.7541695339028173, 0.15]
bottle_C[0].rotation = [0, 0, 0]
lamp_A[0].position = [5.174611198423848, 4.4963328224153525, 0.8]
lamp_A[0].rotation = [0, 0, 0]
cabinet_A[0].position = [0.1991553321939532, 0.5140672300775899, 0.425]
cabinet_A[0].rotation = [0, 0, 0]
pot_A[0].position = [0.5941288953959787, 2.4307683014471544, 0.11]
pot_A[0].rotation = [0, 0, 0]
shelf_C[0].position = [0.5125361591503519, 2.662989793176579, 0.02]
shelf_C[0].rotation = [0, 0, 0]
shelf_D[0].position = [0.856935660369624, 1.041795240923986, 0.02]
shelf_D[0].rotation = [0, 0, 0]
cabinet_B[0].position = [4.995812804659241, 2.015846158369271, 0.6]
cabinet_B[0].rotation = [0, 0, 0]
pot_B[0].position = [3.8437477957172597, 5.243109945518635, 0.09]
pot_B[0].rotation = [0, 0, 0]
shelf_E[0].position = [3.7635844450199705, 1.6595322390469203, 0.02]
shelf_E[0].rotation = [0, 0, 0]
chair_C[0].position = [4.781645627705027, 0.9787783359013414, 0.44]
chair_C[0].rotation = [0, 0, 0]
lamp_B[0].position = [5.510241610333331, 2.541187800253457, 0.24]
lamp_B[0].rotation = [0, 0, 0]
vase_A[0].position = [4.856111816893391, 0.30947283726769464, 0.15]
vase_A[0].rotation = [0, 0, 0]
cup_B[0].position = [3.7457556904372438, 2.3524054832523835, 0.05]
cup_B[0].rotation = [0, 0, 0]
pot_C[0].position = [0.7631945965959083, 0.0866735670316561, 0.085]
pot_C[0].rotation = [0, 0, 0]
book_A[0].position = [2.6793690888225488, 0.879683193568421, 0.12]
book_A[0].rotation = [0, 0, 0]
book_B[0].position = [4.084113388282966, 2.2650019760343985, 0.13]
book_B[0].rotation = [0, 0, 0]
book_C[0].position = [4.250493144745006, 5.290984483889744, 0.115]
book_C[0].rotation = [0, 0, 0]
vase_B[0].position = [4.097617766019374, 4.4606533235001296, 0.125]
vase_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the supplied boundary coordinates directly. The dining area occupies
# the lower-left bay; storage uses the solid walls, leaving the right-hand
# circulation route and both door approaches clear.
def place_instance(group, xyz, yaw=0):
    instance = group[0]
    instance.position = list(xyz)
    instance.rotation = [0, 0, radians(yaw)]

    # Fixed reference preserves both the intended location and orientation.
    # These references are constraint targets, not additional scene assets.
    reference = AssetInstance(
        position=list(xyz),
        rotation=[0, 0, radians(yaw)]
    )
    solver.distance_constraint(instance, reference, 0, 0, weight=10)
    solver.align_with(instance, reference)
    return instance


# Dining table: its long axis runs north–south.
place_instance(table, [1.95, 1.65, 0.38])
place_instance(chair_A, [1.12, 1.15, 0.44], 0)
place_instance(chair_B, [1.12, 2.15, 0.44], 0)
place_instance(chair_C, [2.78, 1.65, 0.44], 180)

# Face each chair toward its own seating position along the table edge.
for seat_group in (chair_A, chair_B, chair_C):
    solver.point_towards(
        seat_group[0],
        AssetInstance(position=[1.95, seat_group[0].position[1], 0.44])
    )
    solver.distance_constraint(seat_group[0], table[0], 0.82, 1.05)

# Low sideboard against the solid wall above the dining bay.
# Rotation makes the 1.40 m dimension parallel to that wall.
place_instance(cabinet_A, [1.70, 3.025, 0.425], 270)
solver.against_wall(cabinet_A[0], walls[3])

# Tall cabinet against the recessed bay's west wall, facing east.
place_instance(cabinet_B, [3.70, 4.30, 0.60], 0)
solver.against_wall(cabinet_B[0], walls[2])

# Floor lamp in the unused upper-left corner, away from chair pull-out space.
place_instance(lamp_A, [0.45, 2.90, 0.80], 0)

# These thin shelves are wall-mounted, not floor-standing objects.
# Their fixed-height anchors model the wall mounting; on_top_of would
# incorrectly place them directly on a cabinet.
place_instance(shelf_A, [1.65, 3.125, 1.50], 270)
place_instance(shelf_B, [1.65, 3.125, 1.95], 270)
solver.against_wall(shelf_A[0], walls[3])
solver.against_wall(shelf_B[0], walls[3])
solver.align_with(shelf_B[0], shelf_A[0])

place_instance(shelf_C, [3.625, 4.30, 1.50], 0)
place_instance(shelf_D, [3.625, 4.30, 1.95], 0)
solver.against_wall(shelf_C[0], walls[2])
solver.against_wall(shelf_D[0], walls[2])
solver.align_with(shelf_D[0], shelf_C[0])

place_instance(shelf_E, [4.50, 5.625, 1.90], 270)
solver.against_wall(shelf_E[0], walls[1])

# Table setting. All heights include half the object's own height above
# the 0.76 m tabletop; the individual footprints remain separated.
place_instance(plate, [1.77, 1.15, 0.775])
place_instance(cup_A, [1.80, 1.48, 0.81])
place_instance(utensil, [1.77, 0.94, 0.765], 90)
place_instance(cup_B, [2.12, 1.65, 0.81], 180)

place_instance(bottle_A, [2.10, 2.20, 0.91])
place_instance(bottle_B, [2.10, 2.38, 0.90])
place_instance(bottle_C, [1.92, 2.30, 0.91])

for tabletop_group in (
    plate, cup_A, utensil, cup_B, bottle_A, bottle_B, bottle_C
):
    solver.on_top_of(tabletop_group[0], table[0])

# Sideboard accessories occupy opposite ends of its top.
place_instance(pot_A, [1.15, 3.025, 0.96])
solver.on_top_of(pot_A[0], cabinet_A[0])

place_instance(lamp_B, [2.13, 3.025, 1.09], 270)
solver.on_top_of(lamp_B[0], cabinet_A[0])

# The pot fits below the first shelf with clearance above its rim.
place_instance(pot_B, [3.70, 4.05, 1.29])
solver.on_top_of(pot_B[0], cabinet_B[0])

# Decorations fit entirely within their shallow shelf footprints.
place_instance(vase_A, [1.40, 3.125, 1.67], 270)
solver.on_top_of(vase_A[0], shelf_A[0])

place_instance(vase_B, [1.90, 3.125, 2.095], 270)
solver.on_top_of(vase_B[0], shelf_B[0])

place_instance(pot_C, [3.625, 4.40, 1.605])
solver.on_top_of(pot_C[0], shelf_C[0])

# Upright books: their supplied bounding boxes fit the shelf depth.
# Separate positions along y prevent their covers from intersecting.
place_instance(book_A, [3.625, 4.08, 2.09])
place_instance(book_B, [3.625, 4.30, 2.10])
place_instance(book_C, [3.625, 4.52, 2.085])

for book_group in (book_A, book_B, book_C):
    solver.on_top_of(book_group[0], shelf_D[0])
    solver.align_with(book_group[0], shelf_D[0])

solver.constraints = []
bottle_A[0].position = [2.0999999046325684, 2.200000047683716, 0.9099999666213989]
bottle_A[0].rotation = [0, 0, 0.01256637125682779]
bottle_A[0].optimize = 2
plate[0].position = [1.7699999809265137, 1.149999976158142, 0.7749999761581421]
plate[0].rotation = [0, 0, 0.01256637125682779]
plate[0].optimize = 2
bottle_C[0].position = [1.9199999570846558, 2.299999952316284, 0.9099999666213989]
bottle_C[0].rotation = [0, 0, 0.01256637125682779]
bottle_C[0].optimize = 2
pot_B[0].position = [3.700000047683716, 4.050000190734863, 1.290000081062317]
pot_B[0].rotation = [0, 0, 0.01256637125682779]
pot_B[0].optimize = 2
chair_C[0].position = [2.7799999713897705, 1.649999976158142, 0.4399999976158142]
chair_C[0].rotation = [0, 0, -3.125884689672577]
chair_C[0].optimize = 2
shelf_E[0].position = [4.5, 5.629866123199463, 0.019999999552965164]
shelf_E[0].rotation = [0, 0, -1.5665801517471825]
shelf_E[0].optimize = 2
table[0].position = [1.9500000476837158, 1.649999976158142, 0.3799999952316284]
table[0].rotation = [0, 0, 0.04084070568744688]
table[0].optimize = 2
book_B[0].position = [3.625, 4.300000190734863, 0.16999998688697815]
book_B[0].rotation = [0, 0, -0.023276635753310123]
book_B[0].optimize = 2
bottle_B[0].position = [2.0999999046325684, 2.380000114440918, 0.8999999761581421]
bottle_B[0].rotation = [0, 0, 0.01256637125682779]
bottle_B[0].optimize = 2
pot_A[0].position = [1.149999976158142, 3.0250000953674316, 0.9600000381469727]
pot_A[0].rotation = [0, 0, 0.01256637125682779]
pot_A[0].optimize = 2
shelf_B[0].position = [1.649999976158142, 3.12795352935791, 0.019999999552965164]
shelf_B[0].rotation = [0, 0, -1.5654954225590347]
shelf_B[0].optimize = 2
cup_A[0].position = [1.7999999523162842, 1.4800000190734863, 0.8100000023841858]
cup_A[0].rotation = [0, 0, 0.01256637125682779]
cup_A[0].optimize = 2
utensil[0].position = [1.7699999809265137, 0.9399999976158142, 0.7649999856948853]
utensil[0].rotation = [0, 0, 1.5833626980517244]
utensil[0].optimize = 2
cabinet_A[0].position = [1.7000000476837158, 3.021254301071167, 0.42500001192092896]
cabinet_A[0].rotation = [0, 0, -1.5655024205633938]
cabinet_A[0].optimize = 2
shelf_D[0].position = [3.6301565170288086, 4.300000190734863, 0.019999999552965164]
shelf_D[0].rotation = [0, 0, -0.010968223702487893]
shelf_D[0].optimize = 2
pot_C[0].position = [3.625, 4.400000095367432, 0.125]
pot_C[0].rotation = [0, 0, 0.01256637125682779]
pot_C[0].optimize = 2
book_C[0].position = [3.625, 4.519999980926514, 0.1550000011920929]
book_C[0].rotation = [0, 0, -0.023276635753310123]
book_C[0].optimize = 2
shelf_C[0].position = [3.624861478805542, 4.300000190734863, 0.019999999552965164]
shelf_C[0].rotation = [0, 0, 0.005300808448847467]
shelf_C[0].optimize = 2
shelf_A[0].position = [1.649999976158142, 3.12795352935791, 0.019999999552965164]
shelf_A[0].rotation = [0, 0, -1.5654954225590347]
shelf_A[0].optimize = 2
vase_B[0].position = [1.899999976158142, 3.125, 0.16499999165534973]
vase_B[0].rotation = [0, 0, -1.5582299555380688]
vase_B[0].optimize = 2
chair_B[0].position = [1.1200000047683716, 2.1500000953674316, 0.4399999976158142]
chair_B[0].rotation = [0, 0, 0.0157079639172164]
chair_B[0].optimize = 2
cup_B[0].position = [2.119999885559082, 1.649999976158142, 0.8100000023841858]
cup_B[0].rotation = [0, 0, -3.1290262823329655]
cup_B[0].optimize = 2
vase_A[0].position = [1.399999976158142, 3.125, 0.1899999976158142]
vase_A[0].rotation = [0, 0, -1.5582299555380688]
vase_A[0].optimize = 2
cabinet_B[0].position = [3.700662851333618, 4.300000190734863, 0.6000000238418579]
cabinet_B[0].rotation = [0, 0, 0.006141395021098107]
cabinet_B[0].optimize = 2
chair_A[0].position = [1.1200000047683716, 1.149999976158142, 0.4399999976158142]
chair_A[0].rotation = [0, 0, 0.0157079639172164]
chair_A[0].optimize = 2
lamp_B[0].position = [2.130000114440918, 3.0250000953674316, 1.090000033378601]
lamp_B[0].rotation = [0, 0, -1.5582299555380688]
lamp_B[0].optimize = 2
lamp_A[0].position = [0.44999998807907104, 2.9000000953674316, 0.800000011920929]
lamp_A[0].rotation = [0, 0, 0.00942477746072377]
lamp_A[0].optimize = 2
book_A[0].position = [3.625, 4.079999923706055, 0.1599999964237213]
book_A[0].rotation = [0, 0, -0.023276635753310123]
book_A[0].optimize = 2

