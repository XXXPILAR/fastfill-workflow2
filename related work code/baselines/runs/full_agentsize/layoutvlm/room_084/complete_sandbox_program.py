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
table = Assets(description="table", size=[0.90, 1.80, 0.75], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="shelf", size=[0.30, 1.20, 0.05], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.30, 1.20, 0.05], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="chair", size=[0.52, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
plate = Assets(description="plate", size=[0.27, 0.27, 0.03], placements=[AssetInstance() for _ in range(1)])
cup_A = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.52, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
bottle_A = Assets(description="bottle", size=[0.08, 0.08, 0.30], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="bottle", size=[0.08, 0.08, 0.30], placements=[AssetInstance() for _ in range(1)])
utensil = Assets(description="utensil", size=[0.22, 0.04, 0.02], placements=[AssetInstance() for _ in range(1)])
bottle_C = Assets(description="bottle", size=[0.08, 0.08, 0.30], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="lamp", size=[0.35, 0.35, 1.60], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.45, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
pot_A = Assets(description="pot", size=[0.28, 0.28, 0.24], placements=[AssetInstance() for _ in range(1)])
shelf_C = Assets(description="shelf", size=[0.28, 1.00, 0.05], placements=[AssetInstance() for _ in range(1)])
shelf_D = Assets(description="shelf", size=[0.28, 1.00, 0.05], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.42, 1.00, 1.10], placements=[AssetInstance() for _ in range(1)])
pot_B = Assets(description="pot", size=[0.24, 0.24, 0.22], placements=[AssetInstance() for _ in range(1)])
shelf_E = Assets(description="shelf", size=[0.28, 1.00, 0.05], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="chair", size=[0.52, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.30, 0.30, 0.55], placements=[AssetInstance() for _ in range(1)])
vase_A = Assets(description="vase", size=[0.18, 0.18, 0.35], placements=[AssetInstance() for _ in range(1)])
cup_B = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
pot_C = Assets(description="pot", size=[0.22, 0.22, 0.20], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="book", size=[0.04, 0.22, 0.30], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="book", size=[0.04, 0.20, 0.28], placements=[AssetInstance() for _ in range(1)])
book_C = Assets(description="book", size=[0.04, 0.24, 0.32], placements=[AssetInstance() for _ in range(1)])
vase_B = Assets(description="vase", size=[0.16, 0.16, 0.30], placements=[AssetInstance() for _ in range(1)])

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

table[0].position = [5.6746584874109764, 4.63056957771152, 0.375]
table[0].rotation = [0, 0, 0]
shelf_A[0].position = [4.188063219904262, 3.27742657397769, 0.025]
shelf_A[0].rotation = [0, 0, 0]
shelf_B[0].position = [3.934128976501294, 4.464402035561506, 0.025]
shelf_B[0].rotation = [0, 0, 0]
chair_A[0].position = [3.3608056837654994, 3.212112157914822, 0.45]
chair_A[0].rotation = [0, 0, 0]
plate[0].position = [4.038991541693141, 1.1508778455094726, 0.015]
plate[0].rotation = [0, 0, 0]
cup_A[0].position = [3.9986298770202016, 0.7972232705381493, 0.055]
cup_A[0].rotation = [0, 0, 0]
chair_B[0].position = [5.581105342088432, 3.7335367666898356, 0.45]
chair_B[0].rotation = [0, 0, 0]
bottle_A[0].position = [5.00437936220677, 2.6758597713425667, 0.15]
bottle_A[0].rotation = [0, 0, 0]
bottle_B[0].position = [1.0562549732316637, 1.1832878031239953, 0.15]
bottle_B[0].rotation = [0, 0, 0]
utensil[0].position = [3.506857871019086, 3.197356052787115, 0.01]
utensil[0].rotation = [0, 0, 0]
bottle_C[0].position = [3.836711001508974, 5.32972973413349, 0.15]
bottle_C[0].rotation = [0, 0, 0]
lamp_A[0].position = [3.4667490731839052, 0.05987755789262061, 0.8]
lamp_A[0].rotation = [0, 0, 0]
cabinet_A[0].position = [3.839093452892147, 0.37309351628021303, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
pot_A[0].position = [0.8047033770383748, 0.40892865708309384, 0.12]
pot_A[0].rotation = [0, 0, 0]
shelf_C[0].position = [4.075369853851564, 0.8172897928648065, 0.025]
shelf_C[0].rotation = [0, 0, 0]
shelf_D[0].position = [2.9599312610043294, 1.1400860812561855, 0.025]
shelf_D[0].rotation = [0, 0, 0]
cabinet_B[0].position = [0.16589464018975375, 2.3581090218742595, 0.55]
cabinet_B[0].rotation = [0, 0, 0]
pot_B[0].position = [3.727281038601408, 2.511893060311979, 0.11]
pot_B[0].rotation = [0, 0, 0]
shelf_E[0].position = [1.4571662600868067, 0.05167074447118602, 0.025]
shelf_E[0].rotation = [0, 0, 0]
chair_C[0].position = [3.826516016556131, 2.600956930972898, 0.45]
chair_C[0].rotation = [0, 0, 0]
lamp_B[0].position = [0.04324301218727415, 1.7081752018567578, 0.275]
lamp_B[0].rotation = [0, 0, 0]
vase_A[0].position = [4.524212100008955, 2.3468320954657784, 0.175]
vase_A[0].rotation = [0, 0, 0]
cup_B[0].position = [0.46111126036132927, 0.5073688898619888, 0.055]
cup_B[0].rotation = [0, 0, 0]
pot_C[0].position = [0.49786926141594656, 0.4622902518052365, 0.1]
pot_C[0].rotation = [0, 0, 0]
book_A[0].position = [0.9075589787059408, 3.233185958050904, 0.15]
book_A[0].rotation = [0, 0, 0]
book_B[0].position = [2.215709826973868, 2.830696154837774, 0.14]
book_B[0].rotation = [0, 0, 0]
book_C[0].position = [4.761142628639326, 1.5488399415276395, 0.16]
book_C[0].rotation = [0, 0, 0]
vase_B[0].position = [5.692461641223475, 3.922376280310574, 0.15]
vase_B[0].rotation = [0, 0, 0]
table[0].position = [5.6746584874109764, 4.63056957771152, 0.375]
table[0].rotation = [0, 0, 0]
shelf_A[0].position = [4.188063219904262, 3.27742657397769, 0.025]
shelf_A[0].rotation = [0, 0, 0]
shelf_B[0].position = [3.934128976501294, 4.464402035561506, 0.025]
shelf_B[0].rotation = [0, 0, 0]
chair_A[0].position = [3.3608056837654994, 3.212112157914822, 0.45]
chair_A[0].rotation = [0, 0, 0]
plate[0].position = [4.038991541693141, 1.1508778455094726, 0.015]
plate[0].rotation = [0, 0, 0]
cup_A[0].position = [3.9986298770202016, 0.7972232705381493, 0.055]
cup_A[0].rotation = [0, 0, 0]
chair_B[0].position = [5.581105342088432, 3.7335367666898356, 0.45]
chair_B[0].rotation = [0, 0, 0]
bottle_A[0].position = [5.00437936220677, 2.6758597713425667, 0.15]
bottle_A[0].rotation = [0, 0, 0]
bottle_B[0].position = [1.0562549732316637, 1.1832878031239953, 0.15]
bottle_B[0].rotation = [0, 0, 0]
utensil[0].position = [3.506857871019086, 3.197356052787115, 0.01]
utensil[0].rotation = [0, 0, 0]
bottle_C[0].position = [3.836711001508974, 5.32972973413349, 0.15]
bottle_C[0].rotation = [0, 0, 0]
lamp_A[0].position = [3.4667490731839052, 0.05987755789262061, 0.8]
lamp_A[0].rotation = [0, 0, 0]
cabinet_A[0].position = [3.839093452892147, 0.37309351628021303, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
pot_A[0].position = [0.8047033770383748, 0.40892865708309384, 0.12]
pot_A[0].rotation = [0, 0, 0]
shelf_C[0].position = [4.075369853851564, 0.8172897928648065, 0.025]
shelf_C[0].rotation = [0, 0, 0]
shelf_D[0].position = [2.9599312610043294, 1.1400860812561855, 0.025]
shelf_D[0].rotation = [0, 0, 0]
cabinet_B[0].position = [0.16589464018975375, 2.3581090218742595, 0.55]
cabinet_B[0].rotation = [0, 0, 0]
pot_B[0].position = [3.727281038601408, 2.511893060311979, 0.11]
pot_B[0].rotation = [0, 0, 0]
shelf_E[0].position = [1.4571662600868067, 0.05167074447118602, 0.025]
shelf_E[0].rotation = [0, 0, 0]
chair_C[0].position = [3.826516016556131, 2.600956930972898, 0.45]
chair_C[0].rotation = [0, 0, 0]
lamp_B[0].position = [0.04324301218727415, 1.7081752018567578, 0.275]
lamp_B[0].rotation = [0, 0, 0]
vase_A[0].position = [4.524212100008955, 2.3468320954657784, 0.175]
vase_A[0].rotation = [0, 0, 0]
cup_B[0].position = [0.46111126036132927, 0.5073688898619888, 0.055]
cup_B[0].rotation = [0, 0, 0]
pot_C[0].position = [0.49786926141594656, 0.4622902518052365, 0.1]
pot_C[0].rotation = [0, 0, 0]
book_A[0].position = [0.9075589787059408, 3.233185958050904, 0.15]
book_A[0].rotation = [0, 0, 0]
book_B[0].position = [2.215709826973868, 2.830696154837774, 0.14]
book_B[0].rotation = [0, 0, 0]
book_C[0].position = [4.761142628639326, 1.5488399415276395, 0.16]
book_C[0].rotation = [0, 0, 0]
vase_B[0].position = [5.692461641223475, 3.922376280310574, 0.15]
vase_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Keep the main dining arrangement in the broad lower part of the L-shaped room.
# The eastern side is intentionally left open as a circulation route between
# the two doors at (5.75, 0.97) and (5.75, 5.03).
table[0].position = [2.05, 1.85, 0.375]
table[0].rotation = [0, 0, radians(0)]

chair_A[0].position = [1.22, 1.85, 0.45]
chair_A[0].rotation = [0, 0, radians(0)]
chair_B[0].position = [2.88, 1.85, 0.45]
chair_B[0].rotation = [0, 0, radians(180)]
chair_C[0].position = [2.05, 0.65, 0.45]
chair_C[0].rotation = [0, 0, radians(90)]

# Dining objects are distributed across the tabletop without overlapping.
plate[0].position = [2.05, 1.85, 0.765]
plate[0].rotation = [0, 0, radians(0)]
cup_A[0].position = [1.78, 1.55, 0.805]
cup_A[0].rotation = [0, 0, radians(0)]
bottle_A[0].position = [2.30, 1.52, 0.90]
bottle_A[0].rotation = [0, 0, radians(0)]
bottle_B[0].position = [1.78, 2.20, 0.90]
bottle_B[0].rotation = [0, 0, radians(0)]
utensil[0].position = [2.31, 1.84, 0.76]
utensil[0].rotation = [0, 0, radians(90)]
bottle_C[0].position = [2.30, 2.18, 0.90]
bottle_C[0].rotation = [0, 0, radians(0)]

# These floating shelves use the window-free inner wall at y=3.25.
# Rotating them 90 degrees places their long dimensions parallel to that wall.
shelf_A[0].position = [0.80, 3.10, 1.25]
shelf_A[0].rotation = [0, 0, radians(90)]
shelf_B[0].position = [2.30, 3.10, 1.25]
shelf_B[0].rotation = [0, 0, radians(90)]

pot_A[0].position = [0.80, 3.08, 1.395]
pot_A[0].rotation = [0, 0, radians(90)]
pot_B[0].position = [2.30, 3.08, 1.385]
pot_B[0].rotation = [0, 0, radians(90)]

# Storage is concentrated in the upper alcove, away from both door openings.
cabinet_A[0].position = [3.725, 4.15, 0.45]
cabinet_A[0].rotation = [0, 0, radians(0)]
cabinet_B[0].position = [4.65, 5.54, 0.55]
cabinet_B[0].rotation = [0, 0, radians(-90)]

# Two shelves run along the alcove's left wall. The third runs along its top
# wall above cabinet_B, so their vertical separation prevents overlap.
shelf_C[0].position = [3.64, 3.90, 1.55]
shelf_C[0].rotation = [0, 0, radians(0)]
shelf_D[0].position = [3.64, 4.95, 1.55]
shelf_D[0].rotation = [0, 0, radians(0)]
shelf_E[0].position = [5.00, 5.61, 1.55]
shelf_E[0].rotation = [0, 0, radians(-90)]

pot_C[0].position = [3.66, 3.90, 1.675]
pot_C[0].rotation = [0, 0, radians(0)]
vase_A[0].position = [3.66, 4.95, 1.75]
vase_A[0].rotation = [0, 0, radians(0)]

# Books stand side-by-side on shelf_E, with the vase at the other end.
book_A[0].position = [4.67, 5.60, 1.725]
book_A[0].rotation = [0, 0, radians(0)]
book_B[0].position = [4.76, 5.60, 1.715]
book_B[0].rotation = [0, 0, radians(0)]
book_C[0].position = [4.85, 5.60, 1.735]
book_C[0].rotation = [0, 0, radians(0)]
vase_B[0].position = [5.25, 5.60, 1.725]
vase_B[0].rotation = [0, 0, radians(0)]

# The small lamp sits on cabinet_B, and the spare cup sits on cabinet_A.
lamp_B[0].position = [4.92, 5.54, 1.375]
lamp_B[0].rotation = [0, 0, radians(-90)]
cup_B[0].position = [3.72, 4.15, 0.955]
cup_B[0].rotation = [0, 0, radians(0)]

# The floor lamp occupies the lower-right corner of the dining zone while
# remaining outside the eastern door circulation path.
lamp_A[0].position = [3.20, 0.55, 0.80]
lamp_A[0].rotation = [0, 0, radians(135)]


# Fixed points are constraint references, not additional scene assets.
# Pinning each placement preserves the selected collision-free arrangement.
def _pin(asset_instance, coordinates, weight=10):
    solver.distance_constraint(
        asset_instance,
        AssetInstance(position=coordinates),
        0,
        0,
        weight=weight,
    )


east_heading = AssetInstance(rotation=[0, 0, radians(0)])
north_heading = AssetInstance(rotation=[0, 0, radians(90)])
south_heading = AssetInstance(rotation=[0, 0, radians(-90)])

# Main furniture constraints.
_pin(table[0], [2.05, 1.85, 0.375])
solver.align_with(table[0], east_heading)

_pin(chair_A[0], [1.22, 1.85, 0.45])
solver.point_towards(chair_A[0], table[0])
solver.distance_constraint(chair_A[0], table[0], 0.78, 0.88, weight=10)

_pin(chair_B[0], [2.88, 1.85, 0.45])
solver.point_towards(chair_B[0], table[0])
solver.distance_constraint(chair_B[0], table[0], 0.78, 0.88, weight=10)

_pin(chair_C[0], [2.05, 0.65, 0.45])
solver.point_towards(chair_C[0], table[0])
solver.distance_constraint(chair_C[0], table[0], 1.15, 1.25, weight=10)

_pin(lamp_A[0], [3.20, 0.55, 0.80])
solver.point_towards(lamp_A[0], table[0])

# Tabletop-object constraints: each object is pinned horizontally, supported
# by the table, and given an orientation relative to the table.
_pin(plate[0], [2.05, 1.85, 0.765])
solver.on_top_of(plate[0], table[0])
solver.align_with(plate[0], table[0])

_pin(cup_A[0], [1.78, 1.55, 0.805])
solver.on_top_of(cup_A[0], table[0])
solver.align_with(cup_A[0], table[0])

_pin(bottle_A[0], [2.30, 1.52, 0.90])
solver.on_top_of(bottle_A[0], table[0])
solver.align_with(bottle_A[0], table[0])

_pin(bottle_B[0], [1.78, 2.20, 0.90])
solver.on_top_of(bottle_B[0], table[0])
solver.align_with(bottle_B[0], table[0])

_pin(utensil[0], [2.31, 1.84, 0.76])
solver.on_top_of(utensil[0], table[0])
solver.align_with(utensil[0], table[0], angle=90)

_pin(bottle_C[0], [2.30, 2.18, 0.90])
solver.on_top_of(bottle_C[0], table[0])
solver.align_with(bottle_C[0], table[0])

# Inner-wall shelves and their contents.
solver.against_wall(shelf_A[0], walls[3])
_pin(shelf_A[0], [0.80, 3.10, 1.25])
solver.align_with(shelf_A[0], north_heading)

solver.against_wall(shelf_B[0], walls[3])
_pin(shelf_B[0], [2.30, 3.10, 1.25])
solver.align_with(shelf_B[0], north_heading)

_pin(pot_A[0], [0.80, 3.08, 1.395])
solver.on_top_of(pot_A[0], shelf_A[0])
solver.align_with(pot_A[0], shelf_A[0])

_pin(pot_B[0], [2.30, 3.08, 1.385])
solver.on_top_of(pot_B[0], shelf_B[0])
solver.align_with(pot_B[0], shelf_B[0])

# Alcove cabinets remain flush with their respective walls and face inward.
solver.against_wall(cabinet_A[0], walls[2])
_pin(cabinet_A[0], [3.725, 4.15, 0.45])
solver.align_with(cabinet_A[0], east_heading)

solver.against_wall(cabinet_B[0], walls[1])
_pin(cabinet_B[0], [4.65, 5.54, 0.55])
solver.align_with(cabinet_B[0], south_heading)

# Alcove wall shelves.
solver.against_wall(shelf_C[0], walls[2])
_pin(shelf_C[0], [3.64, 3.90, 1.55])
solver.align_with(shelf_C[0], east_heading)

solver.against_wall(shelf_D[0], walls[2])
_pin(shelf_D[0], [3.64, 4.95, 1.55])
solver.align_with(shelf_D[0], east_heading)

solver.against_wall(shelf_E[0], walls[1])
_pin(shelf_E[0], [5.00, 5.61, 1.55])
solver.align_with(shelf_E[0], south_heading)

# Objects supported by the alcove shelves.
_pin(pot_C[0], [3.66, 3.90, 1.675])
solver.on_top_of(pot_C[0], shelf_C[0])
solver.align_with(pot_C[0], shelf_C[0])

_pin(vase_A[0], [3.66, 4.95, 1.75])
solver.on_top_of(vase_A[0], shelf_D[0])
solver.align_with(vase_A[0], shelf_D[0])

_pin(book_A[0], [4.67, 5.60, 1.725])
solver.on_top_of(book_A[0], shelf_E[0])
solver.align_with(book_A[0], east_heading)

_pin(book_B[0], [4.76, 5.60, 1.715])
solver.on_top_of(book_B[0], shelf_E[0])
solver.align_with(book_B[0], east_heading)

_pin(book_C[0], [4.85, 5.60, 1.735])
solver.on_top_of(book_C[0], shelf_E[0])
solver.align_with(book_C[0], east_heading)

_pin(vase_B[0], [5.25, 5.60, 1.725])
solver.on_top_of(vase_B[0], shelf_E[0])
solver.align_with(vase_B[0], shelf_E[0])

# Cabinet-top accessories.
_pin(lamp_B[0], [4.92, 5.54, 1.375])
solver.on_top_of(lamp_B[0], cabinet_B[0])
solver.align_with(lamp_B[0], cabinet_B[0])

_pin(cup_B[0], [3.72, 4.15, 0.955])
solver.on_top_of(cup_B[0], cabinet_A[0])
solver.align_with(cup_B[0], cabinet_A[0])

solver.constraints = []
cup_A[0].position = [1.7799999713897705, 1.5499999523162842, 0.8050000071525574]
cup_A[0].rotation = [0, 0, 0.06911488301475333]
cup_A[0].optimize = 2
pot_C[0].position = [3.6600000858306885, 3.9000000953674316, 0.15000000596046448]
pot_C[0].rotation = [0, 0, -2.7105295805193966e-07]
pot_C[0].optimize = 2
vase_B[0].position = [5.25, 5.599999904632568, 0.20000000298023224]
vase_B[0].rotation = [0, 0, -1.5708921917669216]
vase_B[0].optimize = 2
plate[0].position = [2.049999952316284, 1.850000023841858, 0.7649999856948853]
plate[0].rotation = [0, 0, 0.06911488301475333]
plate[0].optimize = 2
pot_B[0].position = [2.2869136333465576, 3.07476806640625, 0.1599999964237213]
pot_B[0].rotation = [0, 0, -1.56517127637233]
pot_B[0].optimize = 2
pot_A[0].position = [0.7869136929512024, 3.07476806640625, 0.17000000178813934]
pot_A[0].rotation = [0, 0, -1.56517127637233]
pot_A[0].optimize = 2
book_C[0].position = [4.849999904632568, 5.599999904632568, 0.20999999344348907]
book_C[0].rotation = [0, 0, 0.01256637125682779]
book_C[0].optimize = 2
utensil[0].position = [2.309999942779541, 1.840000033378601, 0.7599999904632568]
utensil[0].rotation = [0, 0, 1.6399112616366467]
utensil[0].optimize = 2
table[0].position = [2.049999952316284, 1.850000023841858, 0.375]
table[0].rotation = [0, 0, 0.06911503821575936]
table[0].optimize = 2
lamp_A[0].position = [3.200000047683716, 0.550000011920929, 0.800000011920929]
lamp_A[0].rotation = [0, 0, 2.3656192553579443]
lamp_A[0].optimize = 2
shelf_D[0].position = [3.640000104904175, 4.949999809265137, 0.02500000037252903]
shelf_D[0].rotation = [0, 0, -6.84853165838509e-08]
shelf_D[0].optimize = 2
lamp_B[0].position = [4.920000076293945, 5.539999961853027, 1.375]
lamp_B[0].rotation = [0, 0, -1.5707966372344513]
lamp_B[0].optimize = 2
book_A[0].position = [4.670000076293945, 5.599999904632568, 0.20000000298023224]
book_A[0].rotation = [0, 0, 0.01256637125682779]
book_A[0].optimize = 2
vase_A[0].position = [3.6600000858306885, 4.949999809265137, 0.22499999403953552]
vase_A[0].rotation = [0, 0, -2.7105295805193966e-07]
vase_A[0].optimize = 2
book_B[0].position = [4.760000228881836, 5.599999904632568, 0.1899999976158142]
book_B[0].rotation = [0, 0, 0.01256637125682779]
book_B[0].optimize = 2
cabinet_B[0].position = [4.650000095367432, 5.54077672958374, 0.550000011920929]
cabinet_B[0].rotation = [0, 0, -1.57079630468356]
cabinet_B[0].optimize = 2
chair_C[0].position = [2.049999952316284, 0.6499999761581421, 0.44999998807907104]
chair_C[0].rotation = [0, 0, 1.5833626980517244]
chair_C[0].optimize = 2
shelf_A[0].position = [0.800000011920929, 3.0993638038635254, 0.02500000037252903]
shelf_A[0].rotation = [0, 0, -1.5653753579156975]
shelf_A[0].optimize = 2
chair_A[0].position = [1.2200000286102295, 1.850000023841858, 0.44999998807907104]
chair_A[0].rotation = [0, 0, 0.01256637125682779]
chair_A[0].optimize = 2
bottle_B[0].position = [1.7799999713897705, 2.200000047683716, 0.8999999761581421]
bottle_B[0].rotation = [0, 0, 0.06911488301475333]
bottle_B[0].optimize = 2
cup_B[0].position = [3.7200000286102295, 4.150000095367432, 0.9549999833106995]
cup_B[0].rotation = [0, 0, -2.7534982553402107e-07]
cup_B[0].optimize = 2
bottle_C[0].position = [2.299999952316284, 2.180000066757202, 0.8999999761581421]
bottle_C[0].rotation = [0, 0, 0.06911488301475333]
bottle_C[0].optimize = 2
bottle_A[0].position = [2.299999952316284, 1.5199999809265137, 0.8999999761581421]
bottle_A[0].rotation = [0, 0, 0.06911488301475333]
bottle_A[0].optimize = 2
cabinet_A[0].position = [3.7250001430511475, 4.150000095367432, 0.44999998807907104]
cabinet_A[0].rotation = [0, 0, -5.637356310878603e-08]
cabinet_A[0].optimize = 2
shelf_E[0].position = [5.0, 5.610776901245117, 0.02500000037252903]
shelf_E[0].rotation = [0, 0, -1.5707960912080028]
shelf_E[0].optimize = 2
chair_B[0].position = [2.880000114440918, 1.850000023841858, 0.44999998807907104]
chair_B[0].rotation = [0, 0, -3.1290262823329655]
chair_B[0].optimize = 2
shelf_C[0].position = [3.640000104904175, 3.9000000953674316, 0.02500000037252903]
shelf_C[0].rotation = [0, 0, -6.84853165838509e-08]
shelf_C[0].optimize = 2
shelf_B[0].position = [2.299999952316284, 3.0993638038635254, 0.02500000037252903]
shelf_B[0].rotation = [0, 0, -1.5653753579156975]
shelf_B[0].optimize = 2

