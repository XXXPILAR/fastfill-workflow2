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
    Wall(corner1=[5.59, 5.94, 0.00], corner2=[1.37, 5.94, 0.00]),
    Wall(corner1=[1.37, 5.94, 0.00], corner2=[1.33, 5.90, 0.00]),
    Wall(corner1=[1.33, 5.90, 0.00], corner2=[0.00, 4.18, 0.00]),
    Wall(corner1=[0.00, 4.18, 0.00], corner2=[0.00, 0.04, 0.00]),
    Wall(corner1=[0.00, 0.04, 0.00], corner2=[0.04, 0.00, 0.00]),
    Wall(corner1=[0.04, 0.00, 0.00], corner2=[3.24, 0.00, 0.00]),
    Wall(corner1=[3.24, 0.00, 0.00], corner2=[5.59, 2.11, 0.00]),
    Wall(corner1=[5.59, 2.11, 0.00], corner2=[5.62, 2.15, 0.00]),
    Wall(corner1=[5.62, 2.15, 0.00], corner2=[5.62, 5.90, 0.00]),
    Wall(corner1=[5.62, 5.90, 0.00], corner2=[5.59, 5.94, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
table_A = Assets(description="table", size=[0.90, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
toy = Assets(description="toy", size=[0.18, 0.25, 0.15], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.60, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.60, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
table_B = Assets(description="table", size=[0.60, 1.10, 0.45], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
oven = Assets(description="oven", size=[0.60, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
bin = Assets(description="bin", size=[0.28, 0.32, 0.48], placements=[AssetInstance() for _ in range(1)])
plant = Assets(description="plant", size=[0.55, 0.55, 1.20], placements=[AssetInstance() for _ in range(1)])
book = Assets(description="book", size=[0.17, 0.24, 0.03], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
cabinet_C = Assets(description="cabinet", size=[0.60, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
cabinet_D = Assets(description="cabinet", size=[0.60, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
couch_A = Assets(description="couch", size=[0.90, 2.15, 0.82], placements=[AssetInstance() for _ in range(1)])
cabinet_E = Assets(description="cabinet", size=[0.60, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
shelf = Assets(description="shelf", size=[0.30, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
lamp = Assets(description="lamp", size=[0.38, 0.38, 1.55], placements=[AssetInstance() for _ in range(1)])
cabinet_F = Assets(description="cabinet", size=[0.38, 0.80, 0.70], placements=[AssetInstance() for _ in range(1)])
couch_B = Assets(description="couch", size=[0.88, 1.85, 0.82], placements=[AssetInstance() for _ in range(1)])
chair_D = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
pillow = Assets(description="pillow", size=[0.16, 0.50, 0.50], placements=[AssetInstance() for _ in range(1)])
teapot = Assets(description="teapot", size=[0.16, 0.22, 0.18], placements=[AssetInstance() for _ in range(1)])

table_A[0].instance_id = 'table_A_0'
toy[0].instance_id = 'toy_0'
cabinet_A[0].instance_id = 'cabinet_A_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
table_B[0].instance_id = 'table_B_0'
chair_A[0].instance_id = 'chair_A_0'
chair_B[0].instance_id = 'chair_B_0'
oven[0].instance_id = 'oven_0'
bin[0].instance_id = 'bin_0'
plant[0].instance_id = 'plant_0'
book[0].instance_id = 'book_0'
chair_C[0].instance_id = 'chair_C_0'
cabinet_C[0].instance_id = 'cabinet_C_0'
cabinet_D[0].instance_id = 'cabinet_D_0'
couch_A[0].instance_id = 'couch_A_0'
cabinet_E[0].instance_id = 'cabinet_E_0'
shelf[0].instance_id = 'shelf_0'
lamp[0].instance_id = 'lamp_0'
cabinet_F[0].instance_id = 'cabinet_F_0'
couch_B[0].instance_id = 'couch_B_0'
chair_D[0].instance_id = 'chair_D_0'
pillow[0].instance_id = 'pillow_0'
teapot[0].instance_id = 'teapot_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'
walls[8].instance_id = 'walls_8'
walls[9].instance_id = 'walls_9'

table_A[0].position = [1.7358198578699005, 2.817331948521724, 0.375]
table_A[0].rotation = [0, 0, 0]
toy[0].position = [5.373944216467466, 5.54662872820931, 0.075]
toy[0].rotation = [0, 0, 0]
cabinet_A[0].position = [5.375490144884138, 5.726525377959975, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [0.3052750014764942, 0.6987271161033762, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
table_B[0].position = [2.432656582784652, 1.7635775229759232, 0.225]
table_B[0].rotation = [0, 0, 0]
chair_A[0].position = [3.8874575644137583, 1.4263154944259124, 0.425]
chair_A[0].rotation = [0, 0, 0]
chair_B[0].position = [4.653795480029987, 4.85894122506162, 0.425]
chair_B[0].rotation = [0, 0, 0]
oven[0].position = [3.934788902177007, 3.757720119697797, 0.45]
oven[0].rotation = [0, 0, 0]
bin[0].position = [0.24398543096278189, 3.49290585959416, 0.24]
bin[0].rotation = [0, 0, 0]
plant[0].position = [2.53039132125631, 0.030427881994156136, 0.6]
plant[0].rotation = [0, 0, 0]
book[0].position = [1.220430674947027, 5.495077059397333, 0.015]
book[0].rotation = [0, 0, 0]
chair_C[0].position = [2.700007236016145, 1.5940468941305066, 0.425]
chair_C[0].rotation = [0, 0, 0]
cabinet_C[0].position = [1.0106218327628154, 1.8338518845277447, 0.45]
cabinet_C[0].rotation = [0, 0, 0]
cabinet_D[0].position = [0.9047216972131871, 3.340267123303842, 0.45]
cabinet_D[0].rotation = [0, 0, 0]
couch_A[0].position = [0.9965349983528062, 4.909222916687963, 0.41]
couch_A[0].rotation = [0, 0, 0]
cabinet_E[0].position = [1.433504238837665, 4.595705507458623, 0.45]
cabinet_E[0].rotation = [0, 0, 0]
shelf[0].position = [4.002489846730911, 3.8681110251432997, 0.9]
shelf[0].rotation = [0, 0, 0]
lamp[0].position = [0.9792802876831757, 4.127911506585132, 0.775]
lamp[0].rotation = [0, 0, 0]
cabinet_F[0].position = [0.29977968964316304, 2.1166004792434516, 0.35]
cabinet_F[0].rotation = [0, 0, 0]
couch_B[0].position = [4.918606594038525, 3.0455772807554387, 0.41]
couch_B[0].rotation = [0, 0, 0]
chair_D[0].position = [2.166560220120838, 3.7569419261248704, 0.425]
chair_D[0].rotation = [0, 0, 0]
pillow[0].position = [3.0941408810220072, 0.8254498264111468, 0.25]
pillow[0].rotation = [0, 0, 0]
teapot[0].position = [1.2794574045369536, 4.939675125002867, 0.09]
teapot[0].rotation = [0, 0, 0]
table_A[0].position = [1.7358198578699005, 2.817331948521724, 0.375]
table_A[0].rotation = [0, 0, 0]
toy[0].position = [5.373944216467466, 5.54662872820931, 0.075]
toy[0].rotation = [0, 0, 0]
cabinet_A[0].position = [5.375490144884138, 5.726525377959975, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [0.3052750014764942, 0.6987271161033762, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
table_B[0].position = [2.432656582784652, 1.7635775229759232, 0.225]
table_B[0].rotation = [0, 0, 0]
chair_A[0].position = [3.8874575644137583, 1.4263154944259124, 0.425]
chair_A[0].rotation = [0, 0, 0]
chair_B[0].position = [4.653795480029987, 4.85894122506162, 0.425]
chair_B[0].rotation = [0, 0, 0]
oven[0].position = [3.934788902177007, 3.757720119697797, 0.45]
oven[0].rotation = [0, 0, 0]
bin[0].position = [0.24398543096278189, 3.49290585959416, 0.24]
bin[0].rotation = [0, 0, 0]
plant[0].position = [2.53039132125631, 0.030427881994156136, 0.6]
plant[0].rotation = [0, 0, 0]
book[0].position = [1.220430674947027, 5.495077059397333, 0.015]
book[0].rotation = [0, 0, 0]
chair_C[0].position = [2.700007236016145, 1.5940468941305066, 0.425]
chair_C[0].rotation = [0, 0, 0]
cabinet_C[0].position = [1.0106218327628154, 1.8338518845277447, 0.45]
cabinet_C[0].rotation = [0, 0, 0]
cabinet_D[0].position = [0.9047216972131871, 3.340267123303842, 0.45]
cabinet_D[0].rotation = [0, 0, 0]
couch_A[0].position = [0.9965349983528062, 4.909222916687963, 0.41]
couch_A[0].rotation = [0, 0, 0]
cabinet_E[0].position = [1.433504238837665, 4.595705507458623, 0.45]
cabinet_E[0].rotation = [0, 0, 0]
shelf[0].position = [4.002489846730911, 3.8681110251432997, 0.9]
shelf[0].rotation = [0, 0, 0]
lamp[0].position = [0.9792802876831757, 4.127911506585132, 0.775]
lamp[0].rotation = [0, 0, 0]
cabinet_F[0].position = [0.29977968964316304, 2.1166004792434516, 0.35]
cabinet_F[0].rotation = [0, 0, 0]
couch_B[0].position = [4.918606594038525, 3.0455772807554387, 0.41]
couch_B[0].rotation = [0, 0, 0]
chair_D[0].position = [2.166560220120838, 3.7569419261248704, 0.425]
chair_D[0].rotation = [0, 0, 0]
pillow[0].position = [3.0941408810220072, 0.8254498264111468, 0.25]
pillow[0].rotation = [0, 0, 0]
teapot[0].position = [1.2794574045369536, 4.939675125002867, 0.09]
teapot[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed reference headings and points used to preserve the intended arrangement.
heading_east = AssetInstance(rotation=[0, 0, radians(0)])
heading_north = AssetInstance(rotation=[0, 0, radians(90)])
heading_northwest = AssetInstance(rotation=[0, 0, radians(138)])
heading_southeast = AssetInstance(rotation=[0, 0, radians(-38)])

# ---------------------------------------------------------------------------
# Dining area in the upper-middle of the room. The table remains far enough
# from the north wall that neither north-wall window is blocked by furniture.
# ---------------------------------------------------------------------------

table_A[0].position = [2.50, 4.65, 0.375]
table_A[0].rotation = [0, 0, radians(0)]
table_A_anchor = AssetInstance(position=[2.50, 4.65, 0.375])
solver.distance_constraint(table_A[0], table_A_anchor, 0, 0, weight=10)
solver.align_with(table_A[0], heading_east)

# Two chairs are arranged on each long side of the dining table, leaving its
# short ends and the route toward the windows open.
chair_A[0].position = [1.65, 4.20, 0.425]
chair_A[0].rotation = [0, 0, radians(0)]
chair_A_anchor = AssetInstance(position=[1.65, 4.20, 0.425])
solver.distance_constraint(chair_A[0], chair_A_anchor, 0, 0, weight=10)
solver.point_towards(chair_A[0], table_A[0])
solver.distance_constraint(chair_A[0], table_A[0], 0.85, 1.05)

chair_B[0].position = [1.65, 5.05, 0.425]
chair_B[0].rotation = [0, 0, radians(0)]
chair_B_anchor = AssetInstance(position=[1.65, 5.05, 0.425])
solver.distance_constraint(chair_B[0], chair_B_anchor, 0, 0, weight=10)
solver.point_towards(chair_B[0], table_A[0])
solver.distance_constraint(chair_B[0], table_A[0], 0.85, 1.10)

chair_C[0].position = [3.35, 4.20, 0.425]
chair_C[0].rotation = [0, 0, radians(180)]
chair_C_anchor = AssetInstance(position=[3.35, 4.20, 0.425])
solver.distance_constraint(chair_C[0], chair_C_anchor, 0, 0, weight=10)
solver.point_towards(chair_C[0], table_A[0])
solver.distance_constraint(chair_C[0], table_A[0], 0.85, 1.05)

chair_D[0].position = [3.35, 5.05, 0.425]
chair_D[0].rotation = [0, 0, radians(180)]
chair_D_anchor = AssetInstance(position=[3.35, 5.05, 0.425])
solver.distance_constraint(chair_D[0], chair_D_anchor, 0, 0, weight=10)
solver.point_towards(chair_D[0], table_A[0])
solver.distance_constraint(chair_D[0], table_A[0], 0.85, 1.10)

# Small dining objects are supported by the tabletop and kept separate.
toy[0].position = [2.28, 4.48, 0.825]
toy[0].rotation = [0, 0, radians(0)]
toy_anchor = AssetInstance(position=[2.28, 4.48, 0.825])
solver.distance_constraint(toy[0], toy_anchor, 0, 0, weight=10)
solver.on_top_of(toy[0], table_A[0])
solver.align_with(toy[0], table_A[0])
solver.distance_constraint(toy[0], book[0], 0.25, 0.55)

book[0].position = [2.68, 4.78, 0.765]
book[0].rotation = [0, 0, radians(8)]
book_anchor = AssetInstance(position=[2.68, 4.78, 0.765])
solver.distance_constraint(book[0], book_anchor, 0, 0, weight=10)
solver.on_top_of(book[0], table_A[0])
solver.align_with(book[0], table_A[0], angle=8)
solver.distance_constraint(book[0], toy[0], 0.25, 0.55)

# ---------------------------------------------------------------------------
# Living area in the lower half. The couches face the coffee table and leave
# a broad circulation route between the living and dining zones.
# ---------------------------------------------------------------------------

couch_A[0].position = [0.45, 1.30, 0.41]
couch_A[0].rotation = [0, 0, radians(0)]
couch_A_anchor = AssetInstance(position=[0.45, 1.30, 0.41])
solver.distance_constraint(couch_A[0], couch_A_anchor, 0, 0, weight=10)
solver.against_wall(couch_A[0], walls[3])
solver.point_towards(couch_A[0], table_B[0])

# This couch follows the lower-right diagonal wall and faces northwest into
# the seating group.
couch_B[0].position = [4.20, 1.43, 0.41]
couch_B[0].rotation = [0, 0, radians(138)]
couch_B_anchor = AssetInstance(position=[4.20, 1.43, 0.41])
solver.distance_constraint(couch_B[0], couch_B_anchor, 0, 0, weight=10)
solver.against_wall(couch_B[0], walls[6])
solver.point_towards(couch_B[0], table_B[0])

table_B[0].position = [2.25, 1.80, 0.225]
table_B[0].rotation = [0, 0, radians(0)]
table_B_anchor = AssetInstance(position=[2.25, 1.80, 0.225])
solver.distance_constraint(table_B[0], table_B_anchor, 0, 0, weight=10)
solver.align_with(table_B[0], heading_east)
solver.distance_constraint(table_B[0], couch_A[0], 1.55, 2.10)
solver.distance_constraint(table_B[0], couch_B[0], 1.65, 2.20)

teapot[0].position = [2.25, 1.80, 0.54]
teapot[0].rotation = [0, 0, radians(0)]
teapot_anchor = AssetInstance(position=[2.25, 1.80, 0.54])
solver.distance_constraint(teapot[0], teapot_anchor, 0, 0, weight=10)
solver.on_top_of(teapot[0], table_B[0])
solver.align_with(teapot[0], table_B[0])

# The pillow is upright on the diagonal couch and follows its orientation.
pillow[0].position = [4.05, 1.58, 1.07]
pillow[0].rotation = [0, 0, radians(138)]
pillow_anchor = AssetInstance(position=[4.05, 1.58, 1.07])
solver.distance_constraint(pillow[0], pillow_anchor, 0, 0, weight=10)
solver.on_top_of(pillow[0], couch_B[0])
solver.align_with(pillow[0], couch_B[0])

# A compact side cabinet and floor lamp serve the living area without
# narrowing the main route around the coffee table.
cabinet_F[0].position = [1.30, 0.50, 0.35]
cabinet_F[0].rotation = [0, 0, radians(90)]
cabinet_F_anchor = AssetInstance(position=[1.30, 0.50, 0.35])
solver.distance_constraint(cabinet_F[0], cabinet_F_anchor, 0, 0, weight=10)
solver.align_with(cabinet_F[0], heading_north)
solver.distance_constraint(cabinet_F[0], couch_A[0], 0.80, 1.35)

lamp[0].position = [3.00, 0.55, 0.775]
lamp[0].rotation = [0, 0, radians(90)]
lamp_anchor = AssetInstance(position=[3.00, 0.55, 0.775])
solver.distance_constraint(lamp[0], lamp_anchor, 0, 0, weight=10)
solver.point_towards(lamp[0], table_B[0])
solver.distance_constraint(lamp[0], couch_B[0], 1.20, 1.80)

# ---------------------------------------------------------------------------
# Kitchen run along the straight right wall. All units face west into the
# room, and their consecutive centers form a practical uninterrupted run.
# ---------------------------------------------------------------------------

cabinet_A[0].position = [5.32, 2.55, 0.45]
cabinet_A[0].rotation = [0, 0, radians(180)]
cabinet_A_anchor = AssetInstance(position=[5.32, 2.55, 0.45])
solver.distance_constraint(cabinet_A[0], cabinet_A_anchor, 0, 0, weight=10)
solver.against_wall(cabinet_A[0], walls[8])
solver.point_towards(cabinet_A[0], table_B[0])

oven[0].position = [5.32, 3.25, 0.45]
oven[0].rotation = [0, 0, radians(180)]
oven_anchor = AssetInstance(position=[5.32, 3.25, 0.45])
solver.distance_constraint(oven[0], oven_anchor, 0, 0, weight=10)
solver.against_wall(oven[0], walls[8])
solver.align_with(oven[0], cabinet_A[0])
solver.distance_constraint(oven[0], cabinet_A[0], 0.65, 0.75)

cabinet_B[0].position = [5.32, 3.95, 0.45]
cabinet_B[0].rotation = [0, 0, radians(180)]
cabinet_B_anchor = AssetInstance(position=[5.32, 3.95, 0.45])
solver.distance_constraint(cabinet_B[0], cabinet_B_anchor, 0, 0, weight=10)
solver.against_wall(cabinet_B[0], walls[8])
solver.align_with(cabinet_B[0], oven[0])
solver.distance_constraint(cabinet_B[0], oven[0], 0.65, 0.75)

cabinet_C[0].position = [5.32, 4.70, 0.45]
cabinet_C[0].rotation = [0, 0, radians(180)]
cabinet_C_anchor = AssetInstance(position=[5.32, 4.70, 0.45])
solver.distance_constraint(cabinet_C[0], cabinet_C_anchor, 0, 0, weight=10)
solver.against_wall(cabinet_C[0], walls[8])
solver.align_with(cabinet_C[0], cabinet_B[0])
solver.distance_constraint(cabinet_C[0], cabinet_B[0], 0.70, 0.80)

cabinet_D[0].position = [5.32, 5.50, 0.45]
cabinet_D[0].rotation = [0, 0, radians(180)]
cabinet_D_anchor = AssetInstance(position=[5.32, 5.50, 0.45])
solver.distance_constraint(cabinet_D[0], cabinet_D_anchor, 0, 0, weight=10)
solver.against_wall(cabinet_D[0], walls[8])
solver.align_with(cabinet_D[0], cabinet_C[0])
solver.distance_constraint(cabinet_D[0], cabinet_C[0], 0.75, 0.85)

# The bin sits beside the first kitchen cabinet, clear of both the cabinet
# doors and the diagonal couch.
bin[0].position = [4.75, 2.65, 0.24]
bin[0].rotation = [0, 0, radians(180)]
bin_anchor = AssetInstance(position=[4.75, 2.65, 0.24])
solver.distance_constraint(bin[0], bin_anchor, 0, 0, weight=10)
solver.align_with(bin[0], cabinet_A[0])
solver.distance_constraint(bin[0], cabinet_A[0], 0.50, 0.70)

# ---------------------------------------------------------------------------
# Storage and decoration along the left side. These placements use the wall
# segments that do not contain either of the north-wall windows.
# ---------------------------------------------------------------------------

cabinet_E[0].position = [0.30, 3.00, 0.45]
cabinet_E[0].rotation = [0, 0, radians(0)]
cabinet_E_anchor = AssetInstance(position=[0.30, 3.00, 0.45])
solver.distance_constraint(cabinet_E[0], cabinet_E_anchor, 0, 0, weight=10)
solver.against_wall(cabinet_E[0], walls[3])
solver.point_towards(cabinet_E[0], table_A[0])

# The shelf follows the upper-left diagonal wall; its shallow side projects
# into the room while its long side runs parallel to that wall.
shelf[0].position = [0.72, 4.90, 0.90]
shelf[0].rotation = [0, 0, radians(-38)]
shelf_anchor = AssetInstance(position=[0.72, 4.90, 0.90])
solver.distance_constraint(shelf[0], shelf_anchor, 0, 0, weight=10)
solver.against_wall(shelf[0], walls[2])
solver.align_with(shelf[0], heading_southeast)

plant[0].position = [0.45, 3.85, 0.60]
plant[0].rotation = [0, 0, radians(0)]
plant_anchor = AssetInstance(position=[0.45, 3.85, 0.60])
solver.distance_constraint(plant[0], plant_anchor, 0, 0, weight=10)
solver.point_towards(plant[0], table_A[0])
solver.distance_constraint(plant[0], cabinet_E[0], 0.75, 1.00)
solver.distance_constraint(plant[0], shelf[0], 0.90, 1.25)

solver.constraints = []
couch_B[0].position = [4.120294094085693, 1.5196727514266968, 0.4099999964237213]
couch_B[0].rotation = [0, 0, 2.4195729063005422]
couch_B[0].optimize = 2
cabinet_E[0].position = [0.3022558391094208, 3.0, 0.44999998807907104]
cabinet_E[0].rotation = [0, 0, 0.005651521427410857]
cabinet_E[0].optimize = 2
table_B[0].position = [2.25, 1.7999999523162842, 0.22499999403953552]
table_B[0].rotation = [0, 0, 0.03455751882667646]
table_B[0].optimize = 2
cabinet_B[0].position = [5.3299994468688965, 3.950000047683716, 0.44999998807907104]
cabinet_B[0].rotation = [0, 0, -3.1297196341954674]
cabinet_B[0].optimize = 2
chair_D[0].position = [3.3499999046325684, 5.050000190734863, 0.42500001192092896]
chair_D[0].rotation = [0, 0, -3.1290262823329655]
chair_D[0].optimize = 2
toy[0].position = [2.2799999713897705, 4.480000019073486, 0.824999988079071]
toy[0].rotation = [0, 0, 0.02913607460511493]
toy[0].optimize = 2
pillow[0].position = [4.050000190734863, 1.5800000429153442, 1.0699999332427979]
pillow[0].rotation = [0, 0, 2.435217610300436]
pillow[0].optimize = 2
teapot[0].position = [2.25, 1.7999999523162842, 0.5399999618530273]
teapot[0].rotation = [0, 0, 0.022790561024514572]
teapot[0].optimize = 2
chair_C[0].position = [3.3499999046325684, 4.199999809265137, 0.42500001192092896]
chair_C[0].rotation = [0, 0, -3.1290262823329655]
chair_C[0].optimize = 2
cabinet_F[0].position = [1.2999999523162842, 0.5, 0.3499999940395355]
cabinet_F[0].rotation = [0, 0, 1.5833626980517244]
cabinet_F[0].optimize = 2
couch_A[0].position = [0.460182249546051, 1.2999999523162842, 0.4099999964237213]
couch_A[0].rotation = [0, 0, 0.008762199994830322]
couch_A[0].optimize = 2
table_A[0].position = [2.5, 4.650000095367432, 0.375]
table_A[0].rotation = [0, 0, 0.053407073383009665]
table_A[0].optimize = 2
cabinet_D[0].position = [5.3299994468688965, 5.4900007247924805, 0.44999998807907104]
cabinet_D[0].rotation = [0, 0, -3.135941134673872]
cabinet_D[0].optimize = 2
book[0].position = [2.680000066757202, 4.78000020980835, 0.7649999856948853]
book[0].rotation = [0, 0, 0.17002341161548834]
book[0].optimize = 2
bin[0].position = [4.75, 2.6500000953674316, 0.23999999463558197]
bin[0].rotation = [0, 0, -3.118803053451712]
bin[0].optimize = 2
chair_A[0].position = [1.649999976158142, 4.199999809265137, 0.42500001192092896]
chair_A[0].rotation = [0, 0, 0.01256637125682779]
chair_A[0].optimize = 2
plant[0].position = [0.44999998807907104, 3.8499999046325684, 0.6000000238418579]
plant[0].rotation = [0, 0, 0.0157079639172164]
plant[0].optimize = 2
lamp[0].position = [3.0, 0.550000011920929, 0.7749999761581421]
lamp[0].rotation = [0, 0, 1.5935881221455732]
lamp[0].optimize = 2
cabinet_A[0].position = [5.319040298461914, 2.549999952316284, 0.44999998807907104]
cabinet_A[0].rotation = [0, 0, -3.1266087393606927]
cabinet_A[0].optimize = 2
chair_B[0].position = [1.649999976158142, 5.050000190734863, 0.42500001192092896]
chair_B[0].rotation = [0, 0, 0.01256637125682779]
chair_B[0].optimize = 2
cabinet_C[0].position = [5.3299994468688965, 4.699999809265137, 0.44999998807907104]
cabinet_C[0].rotation = [0, 0, -3.1297196341954674]
cabinet_C[0].optimize = 2
oven[0].position = [5.3299994468688965, 3.25, 0.44999998807907104]
oven[0].rotation = [0, 0, -3.129719632351079]
oven[0].optimize = 2
shelf[0].position = [0.7392237186431885, 4.887417793273926, 0.8999999761581421]
shelf[0].rotation = [0, 0, -0.6615512587699299]
shelf[0].optimize = 2

