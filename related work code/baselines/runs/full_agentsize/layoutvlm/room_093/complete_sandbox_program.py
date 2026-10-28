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
    Wall(corner1=[0.00, 5.74, 0.00], corner2=[0.00, 0.04, 0.00]),
    Wall(corner1=[0.00, 0.04, 0.00], corner2=[0.04, 0.00, 0.00]),
    Wall(corner1=[0.04, 0.00, 0.00], corner2=[2.93, 0.00, 0.00]),
    Wall(corner1=[2.93, 0.00, 0.00], corner2=[2.97, 0.04, 0.00]),
    Wall(corner1=[2.97, 0.04, 0.00], corner2=[2.97, 5.74, 0.00]),
    Wall(corner1=[2.97, 5.74, 0.00], corner2=[2.93, 5.78, 0.00]),
    Wall(corner1=[2.93, 5.78, 0.00], corner2=[0.04, 5.78, 0.00]),
    Wall(corner1=[0.04, 5.78, 0.00], corner2=[0.00, 5.74, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
towel = Assets(description="towel", size=[0.03, 0.70, 1.40], placements=[AssetInstance() for _ in range(1)])
backpack_A = Assets(description="backpack", size=[0.20, 0.32, 0.45], placements=[AssetInstance() for _ in range(1)])
bin = Assets(description="bin", size=[0.28, 0.28, 0.40], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.00, 1.40, 0.55], placements=[AssetInstance() for _ in range(1)])
box_A = Assets(description="box", size=[0.30, 0.40, 0.25], placements=[AssetInstance() for _ in range(1)])
bottle_A = Assets(description="bottle", size=[0.07, 0.07, 0.22], placements=[AssetInstance() for _ in range(1)])
bathtub = Assets(description="bathtub", size=[1.70, 0.75, 0.58], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="cabinet", size=[0.45, 0.80, 1.80], placements=[AssetInstance() for _ in range(1)])
backpack_B = Assets(description="backpack", size=[0.18, 0.30, 0.42], placements=[AssetInstance() for _ in range(1)])
chair = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
stopcock = Assets(description="stopcock", size=[0.07, 0.08, 0.08], placements=[AssetInstance() for _ in range(1)])
shoe_A = Assets(description="shoe", size=[0.30, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
toilet_paper = Assets(description="toilet paper", size=[0.12, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
toilet = Assets(description="toilet", size=[0.68, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
box_B = Assets(description="box", size=[0.28, 0.35, 0.20], placements=[AssetInstance() for _ in range(1)])
mat = Assets(description="mat", size=[0.90, 0.60, 0.01], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="bottle", size=[0.07, 0.07, 0.24], placements=[AssetInstance() for _ in range(1)])
ledge_A = Assets(description="ledge", size=[0.14, 0.55, 0.04], placements=[AssetInstance() for _ in range(1)])
ledge_B = Assets(description="ledge", size=[0.13, 0.50, 0.04], placements=[AssetInstance() for _ in range(1)])
shoe_B = Assets(description="shoe", size=[0.30, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
toothbrush = Assets(description="toothbrush", size=[0.02, 0.01, 0.19], placements=[AssetInstance() for _ in range(1)])
desk = Assets(description="desk", size=[0.60, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="table", size=[0.65, 0.65, 0.72], placements=[AssetInstance() for _ in range(1)])
case = Assets(description="case", size=[0.30, 0.42, 0.12], placements=[AssetInstance() for _ in range(1)])
clothes = Assets(description="clothes", size=[0.40, 0.55, 0.12], placements=[AssetInstance() for _ in range(1)])
stand = Assets(description="stand", size=[0.40, 0.90, 0.55], placements=[AssetInstance() for _ in range(1)])
backpack_C = Assets(description="backpack", size=[0.22, 0.34, 0.48], placements=[AssetInstance() for _ in range(1)])
shoe_C = Assets(description="shoe", size=[0.30, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])

towel[0].instance_id = 'towel_0'
backpack_A[0].instance_id = 'backpack_A_0'
bin[0].instance_id = 'bin_0'
bed[0].instance_id = 'bed_0'
box_A[0].instance_id = 'box_A_0'
bottle_A[0].instance_id = 'bottle_A_0'
bathtub[0].instance_id = 'bathtub_0'
cabinet[0].instance_id = 'cabinet_0'
backpack_B[0].instance_id = 'backpack_B_0'
chair[0].instance_id = 'chair_0'
stopcock[0].instance_id = 'stopcock_0'
shoe_A[0].instance_id = 'shoe_A_0'
toilet_paper[0].instance_id = 'toilet_paper_0'
toilet[0].instance_id = 'toilet_0'
box_B[0].instance_id = 'box_B_0'
mat[0].instance_id = 'mat_0'
bottle_B[0].instance_id = 'bottle_B_0'
ledge_A[0].instance_id = 'ledge_A_0'
ledge_B[0].instance_id = 'ledge_B_0'
shoe_B[0].instance_id = 'shoe_B_0'
toothbrush[0].instance_id = 'toothbrush_0'
desk[0].instance_id = 'desk_0'
table[0].instance_id = 'table_0'
case[0].instance_id = 'case_0'
clothes[0].instance_id = 'clothes_0'
stand[0].instance_id = 'stand_0'
backpack_C[0].instance_id = 'backpack_C_0'
shoe_C[0].instance_id = 'shoe_C_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

towel[0].position = [2.094205321050013, 3.3531490805327637, 0.7]
towel[0].rotation = [0, 0, 0]
backpack_A[0].position = [2.235675077025649, 5.07773572307114, 0.225]
backpack_A[0].rotation = [0, 0, 0]
bin[0].position = [1.2409823337401733, 5.396244794205443, 0.2]
bin[0].rotation = [0, 0, 0]
bed[0].position = [0.8656790213570168, 0.10450631567942735, 0.275]
bed[0].rotation = [0, 0, 0]
box_A[0].position = [2.531290972893289, 2.6513793369757046, 0.125]
box_A[0].rotation = [0, 0, 0]
bottle_A[0].position = [2.1245398175860744, 3.5408616430914215, 0.11]
bottle_A[0].rotation = [0, 0, 0]
bathtub[0].position = [1.532359422490701, 4.682290911297196, 0.29]
bathtub[0].rotation = [0, 0, 0]
cabinet[0].position = [1.1971934044475148, 0.9650292241511209, 0.9]
cabinet[0].rotation = [0, 0, 0]
backpack_B[0].position = [1.5783531482268713, 5.757365397475311, 0.21]
backpack_B[0].rotation = [0, 0, 0]
chair[0].position = [2.8611112803205105, 1.9117828426756762, 0.425]
chair[0].rotation = [0, 0, 0]
stopcock[0].position = [2.2079100824546387, 0.9709670844578409, 0.04]
stopcock[0].rotation = [0, 0, 0]
shoe_A[0].position = [0.13302307409404643, 4.414879721297892, 0.05]
shoe_A[0].rotation = [0, 0, 0]
toilet_paper[0].position = [2.102231016741712, 3.20639753483882, 0.05]
toilet_paper[0].rotation = [0, 0, 0]
toilet[0].position = [2.8252903544820596, 3.3212683734427118, 0.39]
toilet[0].rotation = [0, 0, 0]
box_B[0].position = [0.12240315407736917, 2.26886446415441, 0.1]
box_B[0].rotation = [0, 0, 0]
mat[0].position = [2.3167548313403907, 3.4326883173425875, 0.0075]
mat[0].rotation = [0, 0, 0]
bottle_B[0].position = [1.2011841701179795, 0.09590183615153484, 0.12]
bottle_B[0].rotation = [0, 0, 0]
ledge_A[0].position = [1.8944916514131402, 1.223792697899886, 0.02]
ledge_A[0].rotation = [0, 0, 0]
ledge_B[0].position = [0.4459568959770075, 2.5000339265298575, 0.02]
ledge_B[0].rotation = [0, 0, 0]
shoe_B[0].position = [2.244460596866658, 2.278106509699568, 0.05]
shoe_B[0].rotation = [0, 0, 0]
toothbrush[0].position = [0.09653243199769726, 2.976740564866929, 0.095]
toothbrush[0].rotation = [0, 0, 0]
desk[0].position = [1.0267267232799062, 0.8232608765254442, 0.375]
desk[0].rotation = [0, 0, 0]
table[0].position = [1.3750948893608501, 2.5171937158595346, 0.36]
table[0].rotation = [0, 0, 0]
case[0].position = [2.0919105543225887, 3.3779556246112885, 0.06]
case[0].rotation = [0, 0, 0]
clothes[0].position = [1.6607365190800374, 4.0314290961074155, 0.06]
clothes[0].rotation = [0, 0, 0]
stand[0].position = [1.5112265792322384, 0.7194028791276338, 0.275]
stand[0].rotation = [0, 0, 0]
backpack_C[0].position = [0.3877999258836454, 3.6346606292917265, 0.24]
backpack_C[0].rotation = [0, 0, 0]
shoe_C[0].position = [2.1376283792440156, 3.073001361910373, 0.05]
shoe_C[0].rotation = [0, 0, 0]
towel[0].position = [2.094205321050013, 3.3531490805327637, 0.7]
towel[0].rotation = [0, 0, 0]
backpack_A[0].position = [2.235675077025649, 5.07773572307114, 0.225]
backpack_A[0].rotation = [0, 0, 0]
bin[0].position = [1.2409823337401733, 5.396244794205443, 0.2]
bin[0].rotation = [0, 0, 0]
bed[0].position = [0.8656790213570168, 0.10450631567942735, 0.275]
bed[0].rotation = [0, 0, 0]
box_A[0].position = [2.531290972893289, 2.6513793369757046, 0.125]
box_A[0].rotation = [0, 0, 0]
bottle_A[0].position = [2.1245398175860744, 3.5408616430914215, 0.11]
bottle_A[0].rotation = [0, 0, 0]
bathtub[0].position = [1.532359422490701, 4.682290911297196, 0.29]
bathtub[0].rotation = [0, 0, 0]
cabinet[0].position = [1.1971934044475148, 0.9650292241511209, 0.9]
cabinet[0].rotation = [0, 0, 0]
backpack_B[0].position = [1.5783531482268713, 5.757365397475311, 0.21]
backpack_B[0].rotation = [0, 0, 0]
chair[0].position = [2.8611112803205105, 1.9117828426756762, 0.425]
chair[0].rotation = [0, 0, 0]
stopcock[0].position = [2.2079100824546387, 0.9709670844578409, 0.04]
stopcock[0].rotation = [0, 0, 0]
shoe_A[0].position = [0.13302307409404643, 4.414879721297892, 0.05]
shoe_A[0].rotation = [0, 0, 0]
toilet_paper[0].position = [2.102231016741712, 3.20639753483882, 0.05]
toilet_paper[0].rotation = [0, 0, 0]
toilet[0].position = [2.8252903544820596, 3.3212683734427118, 0.39]
toilet[0].rotation = [0, 0, 0]
box_B[0].position = [0.12240315407736917, 2.26886446415441, 0.1]
box_B[0].rotation = [0, 0, 0]
mat[0].position = [2.3167548313403907, 3.4326883173425875, 0.0075]
mat[0].rotation = [0, 0, 0]
bottle_B[0].position = [1.2011841701179795, 0.09590183615153484, 0.12]
bottle_B[0].rotation = [0, 0, 0]
ledge_A[0].position = [1.8944916514131402, 1.223792697899886, 0.02]
ledge_A[0].rotation = [0, 0, 0]
ledge_B[0].position = [0.4459568959770075, 2.5000339265298575, 0.02]
ledge_B[0].rotation = [0, 0, 0]
shoe_B[0].position = [2.244460596866658, 2.278106509699568, 0.05]
shoe_B[0].rotation = [0, 0, 0]
toothbrush[0].position = [0.09653243199769726, 2.976740564866929, 0.095]
toothbrush[0].rotation = [0, 0, 0]
desk[0].position = [1.0267267232799062, 0.8232608765254442, 0.375]
desk[0].rotation = [0, 0, 0]
table[0].position = [1.3750948893608501, 2.5171937158595346, 0.36]
table[0].rotation = [0, 0, 0]
case[0].position = [2.0919105543225887, 3.3779556246112885, 0.06]
case[0].rotation = [0, 0, 0]
clothes[0].position = [1.6607365190800374, 4.0314290961074155, 0.06]
clothes[0].rotation = [0, 0, 0]
stand[0].position = [1.5112265792322384, 0.7194028791276338, 0.275]
stand[0].rotation = [0, 0, 0]
backpack_C[0].position = [0.3877999258836454, 3.6346606292917265, 0.24]
backpack_C[0].rotation = [0, 0, 0]
shoe_C[0].position = [2.1376283792440156, 3.073001361910373, 0.05]
shoe_C[0].rotation = [0, 0, 0]

solver.constraints = []

# Direction references used only to constrain rotations.
east_facing = AssetInstance(position=[1.49, 2.89, 0.00], rotation=[0, 0, radians(0)])
north_facing = AssetInstance(position=[1.49, 2.89, 0.00], rotation=[0, 0, radians(90)])
west_facing = AssetInstance(position=[1.49, 2.89, 0.00], rotation=[0, 0, radians(180)])

# Helper for anchoring an asset near its collision-free initial location.
def fixed_point(x, y, z):
    return AssetInstance(position=[x, y, z])


# The doorway occupies x=0.23..1.17 on the bottom wall. All placements are
# kept beyond its immediate approach, leaving a clear path into the room.

# Left-wall storage and work zone.
towel[0].position = [0.015, 3.75, 0.86]
towel[0].rotation = [0, 0, radians(0)]

backpack_A[0].position = [0.10, 0.70, 0.225]
backpack_A[0].rotation = [0, 0, radians(0)]

cabinet[0].position = [0.225, 3.00, 0.90]
cabinet[0].rotation = [0, 0, radians(0)]

backpack_B[0].position = [0.09, 2.40, 0.21]
backpack_B[0].rotation = [0, 0, radians(0)]

ledge_A[0].position = [0.12, 3.75, 0.74]
ledge_A[0].rotation = [0, 0, radians(0)]

desk[0].position = [0.30, 1.65, 0.375]
desk[0].rotation = [0, 0, radians(0)]

# The requested box is supported by ledge_A and lies 0.165 m from the
# towel's center, while their bounding boxes remain separated in x.
box_B[0].position = [0.18, 3.75, 0.86]
box_B[0].rotation = [0, 0, radians(0)]

# Bed zone at the far end of the room. The bed faces the stand across the
# room, and both touch their respective side walls.
bed[0].position = [1.00, 5.08, 0.275]
bed[0].rotation = [0, 0, radians(0)]

clothes[0].position = [0.75, 5.05, 0.61]
clothes[0].rotation = [0, 0, radians(0)]

stand[0].position = [2.77, 4.85, 0.275]
stand[0].rotation = [0, 0, radians(180)]

backpack_C[0].position = [2.86, 3.95, 0.24]
backpack_C[0].rotation = [0, 0, radians(180)]

# Central table and chair, with enough separation from the bed and desk.
table[0].position = [1.25, 2.80, 0.36]
table[0].rotation = [0, 0, radians(0)]

chair[0].position = [1.35, 3.65, 0.425]
chair[0].rotation = [0, 0, radians(-98)]

box_A[0].position = [1.08, 2.80, 0.845]
box_A[0].rotation = [0, 0, radians(0)]

case[0].position = [1.40, 2.80, 0.78]
case[0].rotation = [0, 0, radians(0)]

# Shoes are lined up beside the desk rather than in the doorway.
shoe_A[0].position = [0.82, 1.30, 0.05]
shoe_A[0].rotation = [0, 0, radians(0)]

shoe_B[0].position = [0.82, 1.65, 0.05]
shoe_B[0].rotation = [0, 0, radians(0)]

shoe_C[0].position = [0.82, 2.00, 0.05]
shoe_C[0].rotation = [0, 0, radians(0)]

# Bathroom fixtures occupy the right side of the room.
bin[0].position = [2.83, 0.30, 0.20]
bin[0].rotation = [0, 0, radians(180)]

bathtub[0].position = [2.595, 1.45, 0.29]
bathtub[0].rotation = [0, 0, radians(90)]

mat[0].position = [1.65, 1.25, 0.005]
mat[0].rotation = [0, 0, radians(0)]

toilet[0].position = [2.63, 2.65, 0.39]
toilet[0].rotation = [0, 0, radians(180)]

toilet_paper[0].position = [2.55, 2.65, 0.83]
toilet_paper[0].rotation = [0, 0, radians(180)]

# A wall-mounted ledge supports the two bottles, the stopcock, and toothbrush.
# In plan view, the stopcock is centered between the two bottles.
ledge_B[0].position = [2.905, 3.35, 1.00]
ledge_B[0].rotation = [0, 0, radians(0)]

bottle_A[0].position = [2.90, 3.20, 1.13]
bottle_A[0].rotation = [0, 0, radians(0)]

stopcock[0].position = [2.90, 3.35, 1.06]
stopcock[0].rotation = [0, 0, radians(0)]

bottle_B[0].position = [2.90, 3.50, 1.14]
bottle_B[0].rotation = [0, 0, radians(0)]

toothbrush[0].position = [2.90, 3.58, 1.115]
toothbrush[0].rotation = [0, 0, radians(0)]


# -------------------------------------------------------------------------
# Highest-priority layout-criteria constraints.
# -------------------------------------------------------------------------

# Keep box_B within 0.20 m of the towel.
solver.distance_constraint(box_B[0], towel[0], 0.12, 0.20, weight=10)

# Preserve the bottle–stopcock–bottle grouping. The initial coordinates put
# the stopcock on the line segment between the bottles.
solver.distance_constraint(stopcock[0], bottle_A[0], 0.14, 0.19, weight=10)
solver.distance_constraint(stopcock[0], bottle_B[0], 0.14, 0.19, weight=10)
solver.distance_constraint(bottle_B[0], bottle_A[0], 0.28, 0.32, weight=10)

# The bed's front (+x at its initial rotation) points directly at the stand.
solver.point_towards(bed[0], stand[0])
solver.point_towards(stand[0], bed[0])


# -------------------------------------------------------------------------
# Wall relationships and orientation constraints for perimeter assets.
# -------------------------------------------------------------------------

solver.against_wall(towel[0], walls[0])
solver.align_with(towel[0], east_facing)

solver.against_wall(backpack_A[0], walls[0])
solver.align_with(backpack_A[0], east_facing)

solver.against_wall(cabinet[0], walls[0])
solver.align_with(cabinet[0], east_facing)

solver.against_wall(backpack_B[0], walls[0])
solver.align_with(backpack_B[0], east_facing)

solver.align_with(ledge_A[0], east_facing)

solver.against_wall(desk[0], walls[0])
solver.align_with(desk[0], east_facing)

solver.against_wall(bed[0], walls[0])

solver.against_wall(stand[0], walls[4])

solver.against_wall(backpack_C[0], walls[4])
solver.align_with(backpack_C[0], west_facing)

solver.against_wall(bin[0], walls[4])
solver.align_with(bin[0], west_facing)

solver.against_wall(bathtub[0], walls[4])
solver.align_with(bathtub[0], north_facing)

solver.against_wall(toilet[0], walls[4])
solver.align_with(toilet[0], west_facing)

solver.against_wall(ledge_B[0], walls[4])
solver.align_with(ledge_B[0], east_facing)


# -------------------------------------------------------------------------
# Supported-object constraints. These keep every small loose object on a
# suitable surface instead of allowing it to fall to the floor.
# -------------------------------------------------------------------------

solver.on_top_of(box_B[0], ledge_A[0])
solver.align_with(box_B[0], towel[0])

solver.on_top_of(clothes[0], bed[0])
solver.align_with(clothes[0], bed[0])

solver.on_top_of(box_A[0], table[0])
solver.align_with(box_A[0], table[0])

solver.on_top_of(case[0], table[0])
solver.align_with(case[0], table[0])

solver.on_top_of(toilet_paper[0], toilet[0])
solver.align_with(toilet_paper[0], toilet[0])

solver.on_top_of(bottle_A[0], ledge_B[0])
solver.align_with(bottle_A[0], ledge_B[0])

solver.on_top_of(stopcock[0], ledge_B[0])
solver.align_with(stopcock[0], ledge_B[0])

solver.on_top_of(bottle_B[0], ledge_B[0])
solver.align_with(bottle_B[0], ledge_B[0])

solver.on_top_of(toothbrush[0], ledge_B[0])
solver.align_with(toothbrush[0], ledge_B[0])


# -------------------------------------------------------------------------
# Functional relationships and orientations for free-standing floor assets.
# -------------------------------------------------------------------------

solver.point_towards(chair[0], table[0])
solver.align_with(table[0], east_facing)

solver.distance_constraint(mat[0], bathtub[0], 0.80, 1.20)
solver.align_with(mat[0], east_facing)

solver.distance_constraint(shoe_A[0], desk[0], 0.45, 0.80)
solver.align_with(shoe_A[0], desk[0])

solver.distance_constraint(shoe_B[0], desk[0], 0.40, 0.70)
solver.align_with(shoe_B[0], desk[0])

solver.distance_constraint(shoe_C[0], desk[0], 0.45, 0.80)
solver.align_with(shoe_C[0], desk[0])


# -------------------------------------------------------------------------
# Low-priority anchors preserve the collision-free arrangement while still
# allowing the semantic constraints above to take precedence.
# -------------------------------------------------------------------------

solver.distance_constraint(towel[0], fixed_point(0.015, 3.75, 0.86), 0, 0, weight=0.1)
solver.distance_constraint(backpack_A[0], fixed_point(0.10, 0.70, 0.225), 0, 0, weight=0.1)
solver.distance_constraint(bin[0], fixed_point(2.83, 0.30, 0.20), 0, 0, weight=0.1)
solver.distance_constraint(bed[0], fixed_point(1.00, 5.08, 0.275), 0, 0, weight=0.1)
solver.distance_constraint(box_A[0], fixed_point(1.08, 2.80, 0.845), 0, 0, weight=0.1)
solver.distance_constraint(bottle_A[0], fixed_point(2.90, 3.20, 1.13), 0, 0, weight=0.1)
solver.distance_constraint(bathtub[0], fixed_point(2.595, 1.45, 0.29), 0, 0, weight=0.1)
solver.distance_constraint(cabinet[0], fixed_point(0.225, 3.00, 0.90), 0, 0, weight=0.1)
solver.distance_constraint(backpack_B[0], fixed_point(0.09, 2.40, 0.21), 0, 0, weight=0.1)
solver.distance_constraint(chair[0], fixed_point(1.35, 3.65, 0.425), 0, 0, weight=0.1)
solver.distance_constraint(stopcock[0], fixed_point(2.90, 3.35, 1.06), 0, 0, weight=0.1)
solver.distance_constraint(shoe_A[0], fixed_point(0.82, 1.30, 0.05), 0, 0, weight=0.1)
solver.distance_constraint(toilet_paper[0], fixed_point(2.55, 2.65, 0.83), 0, 0, weight=0.1)
solver.distance_constraint(toilet[0], fixed_point(2.63, 2.65, 0.39), 0, 0, weight=0.1)
solver.distance_constraint(box_B[0], fixed_point(0.18, 3.75, 0.86), 0, 0, weight=0.1)
solver.distance_constraint(mat[0], fixed_point(1.65, 1.25, 0.005), 0, 0, weight=0.1)
solver.distance_constraint(bottle_B[0], fixed_point(2.90, 3.50, 1.14), 0, 0, weight=0.1)
solver.distance_constraint(ledge_A[0], fixed_point(0.12, 3.75, 0.74), 0, 0, weight=0.1)
solver.distance_constraint(ledge_B[0], fixed_point(2.905, 3.35, 1.00), 0, 0, weight=0.1)
solver.distance_constraint(shoe_B[0], fixed_point(0.82, 1.65, 0.05), 0, 0, weight=0.1)
solver.distance_constraint(toothbrush[0], fixed_point(2.90, 3.58, 1.115), 0, 0, weight=0.1)
solver.distance_constraint(desk[0], fixed_point(0.30, 1.65, 0.375), 0, 0, weight=0.1)
solver.distance_constraint(table[0], fixed_point(1.25, 2.80, 0.36), 0, 0, weight=0.1)
solver.distance_constraint(case[0], fixed_point(1.40, 2.80, 0.78), 0, 0, weight=0.1)
solver.distance_constraint(clothes[0], fixed_point(0.75, 5.05, 0.61), 0, 0, weight=0.1)
solver.distance_constraint(stand[0], fixed_point(2.77, 4.85, 0.275), 0, 0, weight=0.1)
solver.distance_constraint(backpack_C[0], fixed_point(2.86, 3.95, 0.24), 0, 0, weight=0.1)
solver.distance_constraint(shoe_C[0], fixed_point(0.82, 2.00, 0.05), 0, 0, weight=0.1)

solver.constraints = []
chair[0].position = [1.350000023841858, 3.6500000953674316, 0.42500001192092896]
chair[0].rotation = [0, 0, -1.7009978866812985]
chair[0].optimize = 2
ledge_B[0].position = [2.71195650100708, 3.3499999046325684, 0.019999999552965164]
ledge_B[0].rotation = [0, 0, 1.933645281254986]
ledge_B[0].optimize = 2
stopcock[0].position = [2.9000000953674316, 3.3499999046325684, 0.07999999821186066]
stopcock[0].rotation = [0, 0, 1.893859311347834]
stopcock[0].optimize = 2
mat[0].position = [1.466172456741333, 1.0548479557037354, 0.004999999888241291]
mat[0].rotation = [0, 0, 0.01256637125682779]
mat[0].optimize = 2
box_A[0].position = [1.0800000429153442, 2.799999952316284, 0.8450000286102295]
box_A[0].rotation = [0, 0, 0.02511023092109797]
box_A[0].optimize = 2
bathtub[0].position = [2.12375545501709, 1.4500000476837158, 0.28999999165534973]
bathtub[0].rotation = [0, 0, -3.128440202616284]
bathtub[0].optimize = 2
desk[0].position = [0.299964040517807, 1.649999976158142, 0.375]
desk[0].rotation = [0, 0, -4.207848686032626e-05]
desk[0].optimize = 2
stand[0].position = [2.768751621246338, 4.849999904632568, 0.2750000059604645]
stand[0].rotation = [0, 0, 3.141543139957441]
stand[0].optimize = 2
backpack_B[0].position = [0.0900188609957695, 2.4000000953674316, 0.20999999344348907]
backpack_B[0].rotation = [0, 0, -4.711437497822361e-05]
backpack_B[0].optimize = 2
table[0].position = [1.25, 2.799999952316284, 0.36000001430511475]
table[0].rotation = [0, 0, 0.025132740109855806]
table[0].optimize = 2
shoe_B[0].position = [0.8199999928474426, 1.649999976158142, 0.05000000074505806]
shoe_B[0].rotation = [0, 0, -0.0003378481716016706]
shoe_B[0].optimize = 2
bed[0].position = [1.2877784967422485, 4.7331390380859375, 0.2750000059604645]
bed[0].rotation = [0, 0, -1.4982448907609724]
bed[0].optimize = 2
toothbrush[0].position = [2.922607898712158, 3.499502420425415, 0.13499999046325684]
toothbrush[0].rotation = [0, 0, 1.8871922197536648]
toothbrush[0].optimize = 2
clothes[0].position = [0.75, 5.050000190734863, 0.6100000143051147]
clothes[0].rotation = [0, 0, -1.498782006219241]
clothes[0].optimize = 2
cabinet[0].position = [0.22502964735031128, 3.0, 0.8999999761581421]
cabinet[0].rotation = [0, 0, -4.7037657186488826e-05]
cabinet[0].optimize = 2
ledge_A[0].position = [0.11999999731779099, 3.75, 0.019999999552965164]
ledge_A[0].rotation = [0, 0, 0.01256637125682779]
ledge_A[0].optimize = 2
shoe_A[0].position = [0.8199999928474426, 1.2999999523162842, 0.05000000074505806]
shoe_A[0].rotation = [0, 0, -0.0003378481716016706]
shoe_A[0].optimize = 2
bin[0].position = [2.8287508487701416, 0.30000001192092896, 0.20000000298023224]
bin[0].rotation = [0, 0, 3.1415454388858493]
bin[0].optimize = 2
case[0].position = [1.399999976158142, 2.799999952316284, 0.7800000309944153]
case[0].rotation = [0, 0, 0.02511023092109797]
case[0].optimize = 2
bottle_B[0].position = [2.9000000953674316, 3.5, 0.1599999964237213]
bottle_B[0].rotation = [0, 0, 1.893859311347834]
bottle_B[0].optimize = 2
shoe_C[0].position = [0.8199999928474426, 2.0, 0.05000000074505806]
shoe_C[0].rotation = [0, 0, -0.0003378481716016706]
shoe_C[0].optimize = 2
bottle_A[0].position = [2.84960675239563, 3.332733154296875, 0.15000000596046448]
bottle_A[0].rotation = [0, 0, 1.893859311347834]
bottle_A[0].optimize = 2
backpack_A[0].position = [0.10001347213983536, 0.699999988079071, 0.22499999403953552]
backpack_A[0].rotation = [0, 0, -4.7108755378510776e-05]
backpack_A[0].optimize = 2
toilet_paper[0].position = [2.549999952316284, 2.6500000953674316, 0.8299999833106995]
toilet_paper[0].rotation = [0, 0, 3.1414874503357724]
toilet_paper[0].optimize = 2
toilet[0].position = [2.6287519931793213, 2.6500000953674316, 0.38999998569488525]
toilet[0].rotation = [0, 0, -3.1415211937283947]
toilet[0].optimize = 2
towel[0].position = [0.014981512911617756, 3.75, 0.699999988079071]
towel[0].rotation = [0, 0, 7.152753907917757e-05]
towel[0].optimize = 2
backpack_C[0].position = [2.858750820159912, 3.950000047683716, 0.23999999463558197]
backpack_C[0].rotation = [0, 0, 3.1415454445937576]
backpack_C[0].optimize = 2
box_B[0].position = [0.18000000715255737, 3.75, 0.14000000059604645]
box_B[0].rotation = [0, 0, -3.517472390342471e-05]
box_B[0].optimize = 2

