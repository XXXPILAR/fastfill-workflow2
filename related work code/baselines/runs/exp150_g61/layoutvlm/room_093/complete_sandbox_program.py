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
towel = Assets(description="towel", size=[0.30, 0.40, 0.06], placements=[AssetInstance() for _ in range(1)])
backpack_A = Assets(description="backpack", size=[0.22, 0.32, 0.45], placements=[AssetInstance() for _ in range(1)])
bin = Assets(description="bin", size=[0.25, 0.25, 0.35], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.00, 0.95, 0.55], placements=[AssetInstance() for _ in range(1)])
box_A = Assets(description="box", size=[0.25, 0.35, 0.20], placements=[AssetInstance() for _ in range(1)])
bottle_A = Assets(description="bottle", size=[0.08, 0.08, 0.24], placements=[AssetInstance() for _ in range(1)])
bathtub = Assets(description="bathtub", size=[1.60, 0.75, 0.58], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="cabinet", size=[0.40, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
backpack_B = Assets(description="backpack", size=[0.20, 0.30, 0.42], placements=[AssetInstance() for _ in range(1)])
chair = Assets(description="chair", size=[0.50, 0.45, 0.85], placements=[AssetInstance() for _ in range(1)])
stopcock = Assets(description="stopcock", size=[0.10, 0.08, 0.08], placements=[AssetInstance() for _ in range(1)])
shoe_A = Assets(description="shoe", size=[0.28, 0.11, 0.12], placements=[AssetInstance() for _ in range(1)])
toilet_paper = Assets(description="toilet paper", size=[0.11, 0.11, 0.10], placements=[AssetInstance() for _ in range(1)])
toilet = Assets(description="toilet", size=[0.68, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
box_B = Assets(description="box", size=[0.12, 0.16, 0.08], placements=[AssetInstance() for _ in range(1)])
mat = Assets(description="mat", size=[0.40, 0.60, 0.01], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="bottle", size=[0.07, 0.07, 0.21], placements=[AssetInstance() for _ in range(1)])
ledge_A = Assets(description="ledge", size=[0.15, 0.70, 0.05], placements=[AssetInstance() for _ in range(1)])
ledge_B = Assets(description="ledge", size=[0.18, 0.45, 0.05], placements=[AssetInstance() for _ in range(1)])
shoe_B = Assets(description="shoe", size=[0.28, 0.11, 0.12], placements=[AssetInstance() for _ in range(1)])
toothbrush = Assets(description="toothbrush", size=[0.02, 0.01, 0.19], placements=[AssetInstance() for _ in range(1)])
desk = Assets(description="desk", size=[0.50, 0.90, 0.75], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="table", size=[0.45, 0.55, 0.55], placements=[AssetInstance() for _ in range(1)])
case = Assets(description="case", size=[0.10, 0.22, 0.07], placements=[AssetInstance() for _ in range(1)])
clothes = Assets(description="clothes", size=[0.30, 0.40, 0.12], placements=[AssetInstance() for _ in range(1)])
stand = Assets(description="stand", size=[0.35, 0.55, 0.65], placements=[AssetInstance() for _ in range(1)])
backpack_C = Assets(description="backpack", size=[0.20, 0.30, 0.40], placements=[AssetInstance() for _ in range(1)])
shoe_C = Assets(description="shoe", size=[0.27, 0.11, 0.11], placements=[AssetInstance() for _ in range(1)])

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

towel[0].position = [2.951652248116575, 5.1058063607786535, 0.03]
towel[0].rotation = [0, 0, 0]
backpack_A[0].position = [1.731115275201262, 4.82412860652317, 0.225]
backpack_A[0].rotation = [0, 0, 0]
bin[0].position = [2.2593278477814067, 1.1287487328327597, 0.175]
bin[0].rotation = [0, 0, 0]
bed[0].position = [1.0283266579933972, 2.569524835625245, 0.275]
bed[0].rotation = [0, 0, 0]
box_A[0].position = [2.460489915742692, 2.8455009011880255, 0.1]
box_A[0].rotation = [0, 0, 0]
bottle_A[0].position = [2.4168461301113506, 5.423726529963541, 0.12]
bottle_A[0].rotation = [0, 0, 0]
bathtub[0].position = [0.27479314834718593, 0.8254320120171382, 0.29]
bathtub[0].rotation = [0, 0, 0]
cabinet[0].position = [2.2570874464904556, 4.3488685864408, 0.425]
cabinet[0].rotation = [0, 0, 0]
backpack_B[0].position = [2.315012394403908, 1.1579703298687989, 0.21]
backpack_B[0].rotation = [0, 0, 0]
chair[0].position = [1.8169285899625316, 0.26798039615812685, 0.425]
chair[0].rotation = [0, 0, 0]
stopcock[0].position = [1.6057339525231737, 4.818049680223803, 0.04]
stopcock[0].rotation = [0, 0, 0]
shoe_A[0].position = [2.611536519853728, 1.2437195820086275, 0.06]
shoe_A[0].rotation = [0, 0, 0]
toilet_paper[0].position = [0.09118193207619069, 3.9493094516321885, 0.05]
toilet_paper[0].rotation = [0, 0, 0]
toilet[0].position = [0.8803518373599363, 0.6127460370603202, 0.39]
toilet[0].rotation = [0, 0, 0]
box_B[0].position = [2.4280035324155254, 0.2923050349689943, 0.04]
box_B[0].rotation = [0, 0, 0]
mat[0].position = [1.738911054751531, 0.5877235844020784, 0.0075]
mat[0].rotation = [0, 0, 0]
bottle_B[0].position = [2.34033013335859, 2.892295260029388, 0.105]
bottle_B[0].rotation = [0, 0, 0]
ledge_A[0].position = [2.3871595473120353, 5.667080322680189, 0.025]
ledge_A[0].rotation = [0, 0, 0]
ledge_B[0].position = [1.5020098069478596, 0.22437500228706714, 0.025]
ledge_B[0].rotation = [0, 0, 0]
shoe_B[0].position = [2.4894174892253793, 3.6454715852893798, 0.06]
shoe_B[0].rotation = [0, 0, 0]
toothbrush[0].position = [2.410936123346568, 2.3324743189741555, 0.095]
toothbrush[0].rotation = [0, 0, 0]
desk[0].position = [1.6397679809199992, 0.2646765348267728, 0.375]
desk[0].rotation = [0, 0, 0]
table[0].position = [1.1972600195163619, 2.581044984654156, 0.275]
table[0].rotation = [0, 0, 0]
case[0].position = [0.99629609500022, 5.301642103209899, 0.035]
case[0].rotation = [0, 0, 0]
clothes[0].position = [1.3901912721825511, 3.4809976477500144, 0.06]
clothes[0].rotation = [0, 0, 0]
stand[0].position = [1.9491048005371434, 2.45957248601803, 0.325]
stand[0].rotation = [0, 0, 0]
backpack_C[0].position = [2.061347131107723, 4.04215112770248, 0.2]
backpack_C[0].rotation = [0, 0, 0]
shoe_C[0].position = [1.9419185126902634, 2.7994383264329334, 0.055]
shoe_C[0].rotation = [0, 0, 0]
towel[0].position = [2.951652248116575, 5.1058063607786535, 0.03]
towel[0].rotation = [0, 0, 0]
backpack_A[0].position = [1.731115275201262, 4.82412860652317, 0.225]
backpack_A[0].rotation = [0, 0, 0]
bin[0].position = [2.2593278477814067, 1.1287487328327597, 0.175]
bin[0].rotation = [0, 0, 0]
bed[0].position = [1.0283266579933972, 2.569524835625245, 0.275]
bed[0].rotation = [0, 0, 0]
box_A[0].position = [2.460489915742692, 2.8455009011880255, 0.1]
box_A[0].rotation = [0, 0, 0]
bottle_A[0].position = [2.4168461301113506, 5.423726529963541, 0.12]
bottle_A[0].rotation = [0, 0, 0]
bathtub[0].position = [0.27479314834718593, 0.8254320120171382, 0.29]
bathtub[0].rotation = [0, 0, 0]
cabinet[0].position = [2.2570874464904556, 4.3488685864408, 0.425]
cabinet[0].rotation = [0, 0, 0]
backpack_B[0].position = [2.315012394403908, 1.1579703298687989, 0.21]
backpack_B[0].rotation = [0, 0, 0]
chair[0].position = [1.8169285899625316, 0.26798039615812685, 0.425]
chair[0].rotation = [0, 0, 0]
stopcock[0].position = [1.6057339525231737, 4.818049680223803, 0.04]
stopcock[0].rotation = [0, 0, 0]
shoe_A[0].position = [2.611536519853728, 1.2437195820086275, 0.06]
shoe_A[0].rotation = [0, 0, 0]
toilet_paper[0].position = [0.09118193207619069, 3.9493094516321885, 0.05]
toilet_paper[0].rotation = [0, 0, 0]
toilet[0].position = [0.8803518373599363, 0.6127460370603202, 0.39]
toilet[0].rotation = [0, 0, 0]
box_B[0].position = [2.4280035324155254, 0.2923050349689943, 0.04]
box_B[0].rotation = [0, 0, 0]
mat[0].position = [1.738911054751531, 0.5877235844020784, 0.0075]
mat[0].rotation = [0, 0, 0]
bottle_B[0].position = [2.34033013335859, 2.892295260029388, 0.105]
bottle_B[0].rotation = [0, 0, 0]
ledge_A[0].position = [2.3871595473120353, 5.667080322680189, 0.025]
ledge_A[0].rotation = [0, 0, 0]
ledge_B[0].position = [1.5020098069478596, 0.22437500228706714, 0.025]
ledge_B[0].rotation = [0, 0, 0]
shoe_B[0].position = [2.4894174892253793, 3.6454715852893798, 0.06]
shoe_B[0].rotation = [0, 0, 0]
toothbrush[0].position = [2.410936123346568, 2.3324743189741555, 0.095]
toothbrush[0].rotation = [0, 0, 0]
desk[0].position = [1.6397679809199992, 0.2646765348267728, 0.375]
desk[0].rotation = [0, 0, 0]
table[0].position = [1.1972600195163619, 2.581044984654156, 0.275]
table[0].rotation = [0, 0, 0]
case[0].position = [0.99629609500022, 5.301642103209899, 0.035]
case[0].rotation = [0, 0, 0]
clothes[0].position = [1.3901912721825511, 3.4809976477500144, 0.06]
clothes[0].rotation = [0, 0, 0]
stand[0].position = [1.9491048005371434, 2.45957248601803, 0.325]
stand[0].rotation = [0, 0, 0]
backpack_C[0].position = [2.061347131107723, 4.04215112770248, 0.2]
backpack_C[0].rotation = [0, 0, 0]
shoe_C[0].position = [1.9419185126902634, 2.7994383264329334, 0.055]
shoe_C[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the supplied 0 <= x <= 2.97, 0 <= y <= 5.78 boundary.
# Keep the doorway and its approach (x=0.23..1.17, y=0..1.0)
# unobstructed. Sleeping/work furniture occupies the left side, while
# bathing/toiletry furniture occupies the right side.
#
# Coordinates are bounding-box centers. Wall-mounted ledges are elevated;
# the small items below are subsequently constrained to their supports.
layout_specs = [
    (bed,        [0.475, 3.250, 0.275],  90),
    (stand,      [0.475, 4.850, 0.325], 270),
    (box_A,      [0.475, 4.850, 0.750],   0),
    (table,      [0.225, 5.450, 0.275],   0),
    (clothes,    [0.225, 5.450, 0.610],   0),

    (desk,       [0.250, 1.650, 0.375],   0),
    (chair,      [0.950, 1.650, 0.425], 180),
    (case,       [0.250, 1.800, 0.785],   0),

    (bathtub,    [2.595, 4.700, 0.290],  90),
    (mat,        [1.950, 4.700, 0.005],   0),
    (cabinet,    [2.770, 2.950, 0.425], 180),
    (towel,      [2.770, 2.950, 0.880],   0),
    (box_B,      [2.770, 2.950, 0.950],   0),
    (toilet,     [2.630, 1.900, 0.390], 180),
    (bin,        [2.800, 0.650, 0.175],   0),

    # This shelf is above the bath, not intersecting its bounding box.
    # The stopcock lies midway between the bottles in plan.
    (ledge_A,    [2.895, 4.700, 1.100], 180),
    (bottle_A,   [2.895, 4.470, 1.245],   0),
    (stopcock,   [2.895, 4.700, 1.165], 180),
    (bottle_B,   [2.895, 4.930, 1.230],   0),

    (ledge_B,    [2.880, 2.300, 1.100], 180),
    (toilet_paper, [2.880, 2.200, 1.175], 0),
    (toothbrush, [2.880, 2.400, 1.220],   0),

    # Store bags and shoes to the right of the entrance approach.
    (backpack_A, [1.600, 0.350, 0.225],  90),
    (backpack_B, [2.000, 0.350, 0.210],  90),
    (backpack_C, [2.400, 0.350, 0.200],  90),
    (shoe_A,     [1.600, 0.900, 0.060],  90),
    (shoe_B,     [2.000, 0.900, 0.060],  90),
    (shoe_C,     [2.400, 0.900, 0.055],  90),
]

for asset_group, center, yaw_degrees in layout_specs:
    asset_group[0].position = list(center)
    asset_group[0].rotation = [0, 0, radians(yaw_degrees)]

# Specify the essential semantic constraints before general anchors.
solver.point_towards(bed[0], stand[0])
solver.point_towards(stand[0], bed[0])
solver.point_towards(chair[0], desk[0])

# Put small objects on actual supporting surfaces.
solver.on_top_of(box_A[0], stand[0])
solver.on_top_of(clothes[0], table[0])
solver.on_top_of(case[0], desk[0])
solver.on_top_of(towel[0], cabinet[0])
solver.on_top_of(box_B[0], towel[0])
solver.on_top_of(bottle_A[0], ledge_A[0])
solver.on_top_of(stopcock[0], ledge_A[0])
solver.on_top_of(bottle_B[0], ledge_A[0])
solver.on_top_of(toilet_paper[0], ledge_B[0])
solver.on_top_of(toothbrush[0], ledge_B[0])

# The small box is directly above the towel: center distance is 0.07 m.
solver.distance_constraint(box_B[0], towel[0], 0.07, 0.20, weight=10)

# These near-triangle-equality distances, together with the explicit anchors
# below, retain the stopcock between the two separated bottles.
solver.distance_constraint(stopcock[0], bottle_A[0], 0.240, 0.250, weight=10)
solver.distance_constraint(stopcock[0], bottle_B[0], 0.235, 0.245, weight=10)
solver.distance_constraint(bottle_A[0], bottle_B[0], 0.460, 0.465, weight=10)

# Attach the shelves to the right wall at their specified elevations.
solver.against_wall(ledge_A[0], walls[4])
solver.against_wall(ledge_B[0], walls[4])

# Place the larger perimeter furniture flush with the appropriate walls.
solver.against_wall(bed[0], walls[0])
solver.against_wall(desk[0], walls[0])
solver.against_wall(table[0], walls[0])
solver.against_wall(bathtub[0], walls[4])
solver.against_wall(cabinet[0], walls[4])
solver.against_wall(toilet[0], walls[4])

# Functional relationships supplement the absolute layout.
solver.distance_constraint(chair[0], desk[0], 0.65, 0.80, weight=10)
solver.distance_constraint(bed[0], stand[0], 1.55, 1.70, weight=10)
solver.align_with(mat[0], bathtub[0], angle=90)
solver.align_with(box_A[0], stand[0], angle=90)
solver.align_with(box_B[0], towel[0])
solver.align_with(case[0], desk[0])
solver.align_with(clothes[0], table[0])

# Give EVERY instance a position-based and orientation-based constraint.
# Fixed reference instances are constraint anchors, not additional scene assets.
# Exact center anchors preserve the clear entrance, separated footprints,
# shelf ordering, and planned circulation space during adjustment.
for asset_group, center, yaw_degrees in layout_specs:
    solver.distance_constraint(
        asset_group[0],
        AssetInstance(position=list(center)),
        0.0, 0.0,
        weight=10,
    )
    solver.align_with(
        asset_group[0],
        AssetInstance(
            position=list(center),
            rotation=[0, 0, radians(yaw_degrees)],
        ),
        angle=0,
    )

solver.constraints = []
bin[0].position = [2.799999952316284, 0.6499999761581421, 0.17499999701976776]
bin[0].rotation = [0, 0, 0.00942477746072377]
bin[0].optimize = 2
bottle_A[0].position = [2.8949999809265137, 4.46999979019165, 0.17000000178813934]
bottle_A[0].rotation = [0, 0, 0.01884955539881635]
bottle_A[0].optimize = 2
cabinet[0].position = [2.768751382827759, 2.950000047683716, 0.42500001192092896]
cabinet[0].rotation = [0, 0, 3.1415825430501387]
cabinet[0].optimize = 2
stopcock[0].position = [2.8949999809265137, 4.699999809265137, 0.09000000357627869]
stopcock[0].rotation = [0, 0, -3.122743098190977]
stopcock[0].optimize = 2
chair[0].position = [0.949999988079071, 1.649999976158142, 0.42500001192092896]
chair[0].rotation = [0, 0, -3.125884689672577]
chair[0].optimize = 2
box_A[0].position = [0.4749999940395355, 4.849999904632568, 0.75]
box_A[0].rotation = [0, 0, 0.025125831130727708]
box_A[0].optimize = 2
backpack_A[0].position = [1.600000023841858, 0.3499999940395355, 0.22499999403953552]
backpack_A[0].rotation = [0, 0, 1.5802211042556205]
backpack_A[0].optimize = 2
ledge_A[0].position = [2.893751859664917, 4.699999809265137, 0.02500000037252903]
ledge_A[0].rotation = [0, 0, -3.1415685837479654]
ledge_A[0].optimize = 2
backpack_C[0].position = [2.4000000953674316, 0.3499999940395355, 0.20000000298023224]
backpack_C[0].rotation = [0, 0, 1.5802211042556205]
backpack_C[0].optimize = 2
table[0].position = [0.225005105137825, 5.449999809265137, 0.2750000059604645]
table[0].rotation = [0, 0, -2.5897314536217824e-05]
table[0].optimize = 2
case[0].position = [0.25, 1.7999999523162842, 0.7850000262260437]
case[0].rotation = [0, 0, -1.3694352626879358e-05]
case[0].optimize = 2
bed[0].position = [1.0314840078353882, 3.3287997245788574, 0.2750000059604645]
bed[0].rotation = [0, 0, 0.07176237505886841]
bed[0].optimize = 2
bottle_B[0].position = [2.8949999809265137, 4.929999828338623, 0.1550000011920929]
bottle_B[0].rotation = [0, 0, 0.01884955539881635]
bottle_B[0].optimize = 2
toilet[0].position = [2.628750801086426, 1.899999976158142, 0.38999998569488525]
toilet[0].rotation = [0, 0, 3.141582568707925]
toilet[0].optimize = 2
backpack_B[0].position = [2.0, 0.3499999940395355, 0.20999999344348907]
backpack_B[0].rotation = [0, 0, 1.5802211042556205]
backpack_B[0].optimize = 2
clothes[0].position = [0.22499999403953552, 5.449999809265137, 0.6100000143051147]
clothes[0].rotation = [0, 0, 5.167440941405061e-05]
clothes[0].optimize = 2
toilet_paper[0].position = [2.880000114440918, 2.200000047683716, 0.10000000149011612]
toilet_paper[0].rotation = [0, 0, 0.01256637125682779]
toilet_paper[0].optimize = 2
shoe_B[0].position = [2.0, 0.8999999761581421, 0.05999999865889549]
shoe_B[0].rotation = [0, 0, 1.5802211042556205]
shoe_B[0].optimize = 2
box_B[0].position = [2.7699999809265137, 2.950000047683716, 0.949999988079071]
box_B[0].rotation = [0, 0, 0.021980252291194602]
box_B[0].optimize = 2
stand[0].position = [0.4749999940395355, 4.849999904632568, 0.32499998807907104]
stand[0].rotation = [0, 0, -1.5456635866850408]
stand[0].optimize = 2
ledge_B[0].position = [2.878751516342163, 2.299999952316284, 0.02500000037252903]
ledge_B[0].rotation = [0, 0, 3.1415667527179023]
ledge_B[0].optimize = 2
toothbrush[0].position = [2.880000114440918, 2.4000000953674316, 0.14499999582767487]
toothbrush[0].rotation = [0, 0, 0.01256637125682779]
toothbrush[0].optimize = 2
bathtub[0].position = [2.1487956047058105, 4.699999809265137, 0.28999999165534973]
bathtub[0].rotation = [0, 0, -3.1232282503151096]
bathtub[0].optimize = 2
shoe_C[0].position = [2.4000000953674316, 0.8999999761581421, 0.054999999701976776]
shoe_C[0].rotation = [0, 0, 1.5802211042556205]
shoe_C[0].optimize = 2
desk[0].position = [0.250017374753952, 1.649999976158142, 0.375]
desk[0].rotation = [0, 0, -2.1890672670039616e-05]
desk[0].optimize = 2
mat[0].position = [1.9500000476837158, 4.699999809265137, 0.004999999888241291]
mat[0].rotation = [0, 0, -1.5943942432156928]
mat[0].optimize = 2
towel[0].position = [2.7699999809265137, 2.950000047683716, 0.8799999952316284]
towel[0].rotation = [0, 0, 0.021991148286022624]
towel[0].optimize = 2
shoe_A[0].position = [1.600000023841858, 0.8999999761581421, 0.05999999865889549]
shoe_A[0].rotation = [0, 0, 1.5802211042556205]
shoe_A[0].optimize = 2

