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
shelf_A = Assets(description="shelf", size=[0.30, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="book", size=[0.04, 0.16, 0.24], placements=[AssetInstance() for _ in range(1)])
bottle_A = Assets(description="bottle", size=[0.08, 0.08, 0.28], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="table", size=[0.90, 1.80, 0.76], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.35, 1.40, 1.90], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="lamp", size=[0.32, 0.32, 0.58], placements=[AssetInstance() for _ in range(1)])
cup_A = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="chair", size=[0.52, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
shelf_C = Assets(description="shelf", size=[0.30, 1.10, 1.70], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.30, 0.30, 0.55], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.52, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="chair", size=[0.52, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
chair_D = Assets(description="chair", size=[0.52, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="bottle", size=[0.08, 0.08, 0.30], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="book", size=[0.04, 0.18, 0.26], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.45, 1.20, 0.85], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.42, 1.00, 0.90], placements=[AssetInstance() for _ in range(1)])
cabinet_C = Assets(description="cabinet", size=[0.40, 0.90, 1.10], placements=[AssetInstance() for _ in range(1)])
bottle_C = Assets(description="bottle", size=[0.07, 0.07, 0.25], placements=[AssetInstance() for _ in range(1)])
lamp_C = Assets(description="lamp", size=[0.28, 0.28, 0.52], placements=[AssetInstance() for _ in range(1)])
plate = Assets(description="plate", size=[0.27, 0.27, 0.03], placements=[AssetInstance() for _ in range(1)])
cup_B = Assets(description="cup", size=[0.09, 0.09, 0.10], placements=[AssetInstance() for _ in range(1)])
cabinet_D = Assets(description="cabinet", size=[0.45, 1.10, 0.90], placements=[AssetInstance() for _ in range(1)])
lamp_D = Assets(description="lamp", size=[0.30, 0.30, 0.56], placements=[AssetInstance() for _ in range(1)])

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

shelf_A[0].position = [2.4349190107050305, 1.8001745196401562, 0.9]
shelf_A[0].rotation = [0, 0, 0]
book_A[0].position = [1.5470819000156062, 1.4078785377605185, 0.12]
book_A[0].rotation = [0, 0, 0]
bottle_A[0].position = [0.6670810901921299, 0.5837964908550457, 0.14]
bottle_A[0].rotation = [0, 0, 0]
table[0].position = [3.6579026712736, 2.3196379210322853, 0.38]
table[0].rotation = [0, 0, 0]
shelf_B[0].position = [0.7235783353173912, 2.9518158502065885, 0.95]
shelf_B[0].rotation = [0, 0, 0]
lamp_A[0].position = [0.3879368339975327, 3.2061033418018563, 0.29]
lamp_A[0].rotation = [0, 0, 0]
cup_A[0].position = [2.7701907241379575, 0.01691389821048943, 0.055]
cup_A[0].rotation = [0, 0, 0]
chair_A[0].position = [4.6760948616757565, 0.3510674966135226, 0.45]
chair_A[0].rotation = [0, 0, 0]
shelf_C[0].position = [1.9254859887419318, 0.9902443560143988, 0.85]
shelf_C[0].rotation = [0, 0, 0]
lamp_B[0].position = [3.170438972417592, 5.4765102600491185, 0.275]
lamp_B[0].rotation = [0, 0, 0]
chair_B[0].position = [0.2553148589057726, 0.4775308353151497, 0.45]
chair_B[0].rotation = [0, 0, 0]
chair_C[0].position = [2.651997199194901, 4.944340509409072, 0.45]
chair_C[0].rotation = [0, 0, 0]
chair_D[0].position = [0.18275920506928903, 1.5232929242125903, 0.45]
chair_D[0].rotation = [0, 0, 0]
bottle_B[0].position = [1.3551238956415876, 4.655240147038127, 0.15]
bottle_B[0].rotation = [0, 0, 0]
book_B[0].position = [5.567703866290951, 4.362470232689305, 0.13]
book_B[0].rotation = [0, 0, 0]
cabinet_A[0].position = [1.2459524868818637, 4.8386507139509805, 0.425]
cabinet_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [1.9525437215327468, 2.7186238027905048, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
cabinet_C[0].position = [0.13997001772650425, 4.0864978592196275, 0.55]
cabinet_C[0].rotation = [0, 0, 0]
bottle_C[0].position = [4.924335072102147, 3.698946583466984, 0.125]
bottle_C[0].rotation = [0, 0, 0]
lamp_C[0].position = [2.2873683193157843, 0.7024335031683842, 0.26]
lamp_C[0].rotation = [0, 0, 0]
plate[0].position = [3.4678241017389904, 2.4847641139941286, 0.015]
plate[0].rotation = [0, 0, 0]
cup_B[0].position = [0.14700624324827397, 3.1153000665244472, 0.05]
cup_B[0].rotation = [0, 0, 0]
cabinet_D[0].position = [1.265293522048024, 5.536067130535958, 0.45]
cabinet_D[0].rotation = [0, 0, 0]
lamp_D[0].position = [4.126108855004287, 2.2907173770201856, 0.28]
lamp_D[0].rotation = [0, 0, 0]
shelf_A[0].position = [2.4349190107050305, 1.8001745196401562, 0.9]
shelf_A[0].rotation = [0, 0, 0]
book_A[0].position = [1.5470819000156062, 1.4078785377605185, 0.12]
book_A[0].rotation = [0, 0, 0]
bottle_A[0].position = [0.6670810901921299, 0.5837964908550457, 0.14]
bottle_A[0].rotation = [0, 0, 0]
table[0].position = [3.6579026712736, 2.3196379210322853, 0.38]
table[0].rotation = [0, 0, 0]
shelf_B[0].position = [0.7235783353173912, 2.9518158502065885, 0.95]
shelf_B[0].rotation = [0, 0, 0]
lamp_A[0].position = [0.3879368339975327, 3.2061033418018563, 0.29]
lamp_A[0].rotation = [0, 0, 0]
cup_A[0].position = [2.7701907241379575, 0.01691389821048943, 0.055]
cup_A[0].rotation = [0, 0, 0]
chair_A[0].position = [4.6760948616757565, 0.3510674966135226, 0.45]
chair_A[0].rotation = [0, 0, 0]
shelf_C[0].position = [1.9254859887419318, 0.9902443560143988, 0.85]
shelf_C[0].rotation = [0, 0, 0]
lamp_B[0].position = [3.170438972417592, 5.4765102600491185, 0.275]
lamp_B[0].rotation = [0, 0, 0]
chair_B[0].position = [0.2553148589057726, 0.4775308353151497, 0.45]
chair_B[0].rotation = [0, 0, 0]
chair_C[0].position = [2.651997199194901, 4.944340509409072, 0.45]
chair_C[0].rotation = [0, 0, 0]
chair_D[0].position = [0.18275920506928903, 1.5232929242125903, 0.45]
chair_D[0].rotation = [0, 0, 0]
bottle_B[0].position = [1.3551238956415876, 4.655240147038127, 0.15]
bottle_B[0].rotation = [0, 0, 0]
book_B[0].position = [5.567703866290951, 4.362470232689305, 0.13]
book_B[0].rotation = [0, 0, 0]
cabinet_A[0].position = [1.2459524868818637, 4.8386507139509805, 0.425]
cabinet_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [1.9525437215327468, 2.7186238027905048, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
cabinet_C[0].position = [0.13997001772650425, 4.0864978592196275, 0.55]
cabinet_C[0].rotation = [0, 0, 0]
bottle_C[0].position = [4.924335072102147, 3.698946583466984, 0.125]
bottle_C[0].rotation = [0, 0, 0]
lamp_C[0].position = [2.2873683193157843, 0.7024335031683842, 0.26]
lamp_C[0].rotation = [0, 0, 0]
plate[0].position = [3.4678241017389904, 2.4847641139941286, 0.015]
plate[0].rotation = [0, 0, 0]
cup_B[0].position = [0.14700624324827397, 3.1153000665244472, 0.05]
cup_B[0].rotation = [0, 0, 0]
cabinet_D[0].position = [1.265293522048024, 5.536067130535958, 0.45]
cabinet_D[0].rotation = [0, 0, 0]
lamp_D[0].position = [4.126108855004287, 2.2907173770201856, 0.28]
lamp_D[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed reference points preserve the intended zones while allowing the solver
# to make small feasibility adjustments.
room_center = AssetInstance(position=[2.35, 2.85, 0.0])
table_anchor = AssetInstance(position=[2.60, 2.85, 0.38], rotation=[0, 0, 0])

shelf_A_anchor = AssetInstance(position=[0.15, 0.75, 0.90])
shelf_B_anchor = AssetInstance(position=[1.80, 5.525, 0.95])
shelf_C_anchor = AssetInstance(position=[0.15, 2.20, 0.85])

cabinet_A_anchor = AssetInstance(position=[0.80, 0.225, 0.425])
cabinet_B_anchor = AssetInstance(position=[0.21, 4.40, 0.45])
cabinet_C_anchor = AssetInstance(position=[4.23, 5.50, 0.55])
cabinet_D_anchor = AssetInstance(position=[4.05, 0.225, 0.45])

chair_A_anchor = AssetInstance(position=[1.50, 2.85, 0.45])
chair_B_anchor = AssetInstance(position=[3.70, 2.85, 0.45])
chair_C_anchor = AssetInstance(position=[2.60, 1.25, 0.45])
chair_D_anchor = AssetInstance(position=[2.60, 4.45, 0.45])

# Place the dining/work table centrally, leaving both door approaches clear.
table[0].position = [2.60, 2.85, 0.38]
table[0].rotation = [0, 0, radians(0)]
solver.distance_constraint(table[0], table_anchor, 0, 0, weight=10)
solver.align_with(table[0], table_anchor)

# Chairs A and B serve the two long sides of the table.
chair_A[0].position = [1.50, 2.85, 0.45]
chair_A[0].rotation = [0, 0, radians(0)]
solver.distance_constraint(chair_A[0], chair_A_anchor, 0, 0, weight=10)
solver.point_towards(chair_A[0], table[0])

chair_B[0].position = [3.70, 2.85, 0.45]
chair_B[0].rotation = [0, 0, radians(180)]
solver.distance_constraint(chair_B[0], chair_B_anchor, 0, 0, weight=10)
solver.point_towards(chair_B[0], table[0])

# The table lies between chair_C (o0011) and chair_D (o0012).
# Chair_C points through the table toward shelf_B (o0004), as requested.
chair_C[0].position = [2.60, 1.25, 0.45]
chair_C[0].rotation = [0, 0, radians(98)]
solver.distance_constraint(chair_C[0], chair_C_anchor, 0, 0, weight=10)
solver.point_towards(chair_C[0], shelf_B[0])

chair_D[0].position = [2.60, 4.45, 0.45]
chair_D[0].rotation = [0, 0, radians(-90)]
solver.distance_constraint(chair_D[0], chair_D_anchor, 0, 0, weight=10)
solver.point_towards(chair_D[0], table[0])

# Shelves occupy solid wall sections and face into the room. Shelf_B is kept
# west of the north door so that its doorway and approach remain unobstructed.
shelf_A[0].position = [0.15, 0.75, 0.90]
shelf_A[0].rotation = [0, 0, radians(0)]
solver.distance_constraint(shelf_A[0], shelf_A_anchor, 0, 0, weight=10)
solver.against_wall(shelf_A[0], walls[6])
solver.point_towards(shelf_A[0], room_center)

shelf_B[0].position = [1.80, 5.525, 0.95]
shelf_B[0].rotation = [0, 0, radians(-90)]
solver.distance_constraint(shelf_B[0], shelf_B_anchor, 0, 0, weight=10)
solver.against_wall(shelf_B[0], walls[5])
solver.point_towards(shelf_B[0], room_center)

shelf_C[0].position = [0.15, 2.20, 0.85]
shelf_C[0].rotation = [0, 0, radians(0)]
solver.distance_constraint(shelf_C[0], shelf_C_anchor, 0, 0, weight=10)
solver.against_wall(shelf_C[0], walls[6])
solver.point_towards(shelf_C[0], room_center)

# Cabinets are distributed along solid wall areas. In particular, cabinet_A
# (o0015) is explicitly constrained against the south wall.
cabinet_A[0].position = [0.80, 0.225, 0.425]
cabinet_A[0].rotation = [0, 0, radians(90)]
solver.distance_constraint(cabinet_A[0], cabinet_A_anchor, 0, 0, weight=10)
solver.against_wall(cabinet_A[0], walls[7])
solver.point_towards(cabinet_A[0], room_center)

cabinet_B[0].position = [0.21, 4.40, 0.45]
cabinet_B[0].rotation = [0, 0, radians(0)]
solver.distance_constraint(cabinet_B[0], cabinet_B_anchor, 0, 0, weight=10)
solver.against_wall(cabinet_B[0], walls[6])
solver.point_towards(cabinet_B[0], room_center)

cabinet_C[0].position = [4.23, 5.50, 0.55]
cabinet_C[0].rotation = [0, 0, radians(-90)]
solver.distance_constraint(cabinet_C[0], cabinet_C_anchor, 0, 0, weight=10)
solver.against_wall(cabinet_C[0], walls[5])
solver.point_towards(cabinet_C[0], room_center)

cabinet_D[0].position = [4.05, 0.225, 0.45]
cabinet_D[0].rotation = [0, 0, radians(90)]
solver.distance_constraint(cabinet_D[0], cabinet_D_anchor, 0, 0, weight=10)
solver.against_wall(cabinet_D[0], walls[7])
solver.point_towards(cabinet_D[0], room_center)

# Each lamp is centered on a different cabinet. The anchor heights equal the
# cabinet top plus half the lamp height.
lamp_A_anchor = AssetInstance(position=[0.80, 0.225, 1.14])
lamp_A[0].position = [0.80, 0.225, 1.14]
lamp_A[0].rotation = [0, 0, radians(90)]
solver.on_top_of(lamp_A[0], cabinet_A[0])
solver.distance_constraint(lamp_A[0], lamp_A_anchor, 0, 0, weight=10)
solver.align_with(lamp_A[0], cabinet_A[0])

lamp_B_anchor = AssetInstance(position=[0.21, 4.40, 1.175])
lamp_B[0].position = [0.21, 4.40, 1.175]
lamp_B[0].rotation = [0, 0, radians(0)]
solver.on_top_of(lamp_B[0], cabinet_B[0])
solver.distance_constraint(lamp_B[0], lamp_B_anchor, 0, 0, weight=10)
solver.align_with(lamp_B[0], cabinet_B[0])

lamp_C_anchor = AssetInstance(position=[4.23, 5.50, 1.36])
lamp_C[0].position = [4.23, 5.50, 1.36]
lamp_C[0].rotation = [0, 0, radians(-90)]
solver.on_top_of(lamp_C[0], cabinet_C[0])
solver.distance_constraint(lamp_C[0], lamp_C_anchor, 0, 0, weight=10)
solver.align_with(lamp_C[0], cabinet_C[0])

lamp_D_anchor = AssetInstance(position=[4.05, 0.225, 1.18])
lamp_D[0].position = [4.05, 0.225, 1.18]
lamp_D[0].rotation = [0, 0, radians(90)]
solver.on_top_of(lamp_D[0], cabinet_D[0])
solver.distance_constraint(lamp_D[0], lamp_D_anchor, 0, 0, weight=10)
solver.align_with(lamp_D[0], cabinet_D[0])

# Small dining and reading objects are spread across the tabletop without
# overlap. Exact anchors provide their required horizontal position constraints.
book_A_anchor = AssetInstance(position=[2.35, 2.45, 0.88])
book_A[0].position = [2.35, 2.45, 0.88]
book_A[0].rotation = [0, 0, radians(0)]
solver.on_top_of(book_A[0], table[0])
solver.distance_constraint(book_A[0], book_A_anchor, 0, 0, weight=10)
solver.align_with(book_A[0], table[0])

bottle_A_anchor = AssetInstance(position=[2.78, 2.35, 0.90])
bottle_A[0].position = [2.78, 2.35, 0.90]
bottle_A[0].rotation = [0, 0, radians(0)]
solver.on_top_of(bottle_A[0], table[0])
solver.distance_constraint(bottle_A[0], bottle_A_anchor, 0, 0, weight=10)
solver.align_with(bottle_A[0], table[0])

cup_A_anchor = AssetInstance(position=[2.75, 3.15, 0.815])
cup_A[0].position = [2.75, 3.15, 0.815]
cup_A[0].rotation = [0, 0, radians(0)]
solver.on_top_of(cup_A[0], table[0])
solver.distance_constraint(cup_A[0], cup_A_anchor, 0, 0, weight=10)
solver.align_with(cup_A[0], table[0])

bottle_B_anchor = AssetInstance(position=[2.35, 3.25, 0.91])
bottle_B[0].position = [2.35, 3.25, 0.91]
bottle_B[0].rotation = [0, 0, radians(0)]
solver.on_top_of(bottle_B[0], table[0])
solver.distance_constraint(bottle_B[0], bottle_B_anchor, 0, 0, weight=10)
solver.align_with(bottle_B[0], table[0])

book_B_anchor = AssetInstance(position=[2.52, 2.70, 0.89])
book_B[0].position = [2.52, 2.70, 0.89]
book_B[0].rotation = [0, 0, radians(90)]
solver.on_top_of(book_B[0], table[0])
solver.distance_constraint(book_B[0], book_B_anchor, 0, 0, weight=10)
solver.align_with(book_B[0], table[0], angle=90)

bottle_C_anchor = AssetInstance(position=[2.82, 2.80, 0.885])
bottle_C[0].position = [2.82, 2.80, 0.885]
bottle_C[0].rotation = [0, 0, radians(0)]
solver.on_top_of(bottle_C[0], table[0])
solver.distance_constraint(bottle_C[0], bottle_C_anchor, 0, 0, weight=10)
solver.align_with(bottle_C[0], table[0])

plate_anchor = AssetInstance(position=[2.35, 2.95, 0.775])
plate[0].position = [2.35, 2.95, 0.775]
plate[0].rotation = [0, 0, radians(0)]
solver.on_top_of(plate[0], table[0])
solver.distance_constraint(plate[0], plate_anchor, 0, 0, weight=10)
solver.align_with(plate[0], table[0])

cup_B_anchor = AssetInstance(position=[2.58, 3.35, 0.81])
cup_B[0].position = [2.58, 3.35, 0.81]
cup_B[0].rotation = [0, 0, radians(0)]
solver.on_top_of(cup_B[0], table[0])
solver.distance_constraint(cup_B[0], cup_B_anchor, 0, 0, weight=10)
solver.align_with(cup_B[0], table[0])

solver.constraints = []
cup_A[0].position = [2.75, 3.1500000953674316, 0.8149999976158142]
cup_A[0].rotation = [0, 0, 0.07062536289831628]
cup_A[0].optimize = 2
plate[0].position = [2.3499999046325684, 2.950000047683716, 0.7749999761581421]
plate[0].rotation = [0, 0, 0.07062536289831628]
plate[0].optimize = 2
lamp_D[0].position = [4.050000190734863, 0.22499999403953552, 1.1799999475479126]
lamp_D[0].rotation = [0, 0, 1.5689731623259617]
lamp_D[0].optimize = 2
table[0].position = [2.5999999046325684, 2.8499999046325684, 0.3799999952316284]
table[0].rotation = [0, 0, 0.06911503821575936]
table[0].optimize = 2
lamp_A[0].position = [0.800000011920929, 0.22499999403953552, 1.1399999856948853]
lamp_A[0].rotation = [0, 0, 1.5689731131841518]
lamp_A[0].optimize = 2
book_A[0].position = [2.3499999046325684, 2.450000047683716, 0.8799999952316284]
book_A[0].rotation = [0, 0, 0.07062536289831628]
book_A[0].optimize = 2
lamp_B[0].position = [0.20999999344348907, 4.400000095367432, 1.1749999523162842]
lamp_B[0].rotation = [0, 0, -0.001821267321860602]
lamp_B[0].optimize = 2
book_B[0].position = [2.5199999809265137, 2.700000047683716, 0.8899999856948853]
book_B[0].rotation = [0, 0, 1.641421734533877]
book_B[0].optimize = 2
chair_B[0].position = [3.700000047683716, 2.8499999046325684, 0.44999998807907104]
chair_B[0].rotation = [0, 0, -3.1321678761290697]
chair_B[0].optimize = 2
cabinet_B[0].position = [0.210183784365654, 4.400000095367432, 0.44999998807907104]
cabinet_B[0].rotation = [0, 0, 0.0005718037855168738]
cabinet_B[0].optimize = 2
chair_D[0].position = [2.5999999046325684, 4.449999809265137, 0.44999998807907104]
chair_D[0].rotation = [0, 0, -1.5613715493341729]
chair_D[0].optimize = 2
shelf_C[0].position = [0.14992564916610718, 2.200000047683716, 0.8500000238418579]
shelf_C[0].rotation = [0, 0, 0.000252554999496275]
shelf_C[0].optimize = 2
chair_C[0].position = [2.5999999046325684, 1.25, 0.44999998807907104]
chair_C[0].rotation = [0, 0, 1.7198474423756605]
chair_C[0].optimize = 2
cabinet_D[0].position = [4.050000190734863, 0.2250305414199829, 0.44999998807907104]
cabinet_D[0].rotation = [0, 0, 1.571368050927398]
cabinet_D[0].optimize = 2
shelf_A[0].position = [0.15006929636001587, 0.75, 0.8999999761581421]
shelf_A[0].rotation = [0, 0, 0.0002525523099305928]
shelf_A[0].optimize = 2
chair_A[0].position = [1.5, 2.8499999046325684, 0.44999998807907104]
chair_A[0].rotation = [0, 0, 0.00942477746072377]
chair_A[0].optimize = 2
bottle_B[0].position = [2.3499999046325684, 3.25, 0.9099999666213989]
bottle_B[0].rotation = [0, 0, 0.07062536289831628]
bottle_B[0].optimize = 2
cup_B[0].position = [2.5799999237060547, 3.3499999046325684, 0.8100000023841858]
cup_B[0].rotation = [0, 0, 0.07062536289831628]
cup_B[0].optimize = 2
bottle_C[0].position = [2.819999933242798, 2.799999952316284, 0.8849999904632568]
bottle_C[0].rotation = [0, 0, 0.07062536289831628]
bottle_C[0].optimize = 2
bottle_A[0].position = [2.7799999713897705, 2.3499999046325684, 0.8999999761581421]
bottle_A[0].rotation = [0, 0, 0.07062536289831628]
bottle_A[0].optimize = 2
cabinet_A[0].position = [0.800000011920929, 0.22463129460811615, 0.42500001192092896]
cabinet_A[0].rotation = [0, 0, 1.5713680592220385]
cabinet_A[0].optimize = 2
lamp_C[0].position = [4.230000019073486, 5.5, 1.3600000143051147]
lamp_C[0].rotation = [0, 0, -1.5726168516711077]
lamp_C[0].optimize = 2
cabinet_C[0].position = [4.230000019073486, 5.504825115203857, 0.550000011920929]
cabinet_C[0].rotation = [0, 0, -1.570224622203064]
cabinet_C[0].optimize = 2
shelf_B[0].position = [1.7999999523162842, 5.52982234954834, 0.949999988079071]
shelf_B[0].rotation = [0, 0, -1.5711385621140448]
shelf_B[0].optimize = 2

