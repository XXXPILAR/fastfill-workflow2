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
    Wall(corner1=[7.72, 3.66, 0.00], corner2=[7.72, 7.46, 0.00]),
    Wall(corner1=[7.72, 7.46, 0.00], corner2=[4.02, 7.46, 0.00]),
    Wall(corner1=[4.02, 7.46, 0.00], corner2=[4.02, 3.66, 0.00]),
    Wall(corner1=[4.02, 3.66, 0.00], corner2=[3.82, 3.66, 0.00]),
    Wall(corner1=[3.82, 3.66, 0.00], corner2=[3.82, 4.26, 0.00]),
    Wall(corner1=[3.82, 4.26, 0.00], corner2=[1.23, 4.26, 0.00]),
    Wall(corner1=[1.23, 4.26, 0.00], corner2=[1.23, 3.66, 0.00]),
    Wall(corner1=[1.23, 3.66, 0.00], corner2=[0.00, 3.66, 0.00]),
    Wall(corner1=[0.00, 3.66, 0.00], corner2=[0.00, 2.55, 0.00]),
    Wall(corner1=[0.00, 2.55, 0.00], corner2=[4.76, 2.55, 0.00]),
    Wall(corner1=[4.76, 2.55, 0.00], corner2=[4.76, 0.00, 0.00]),
    Wall(corner1=[4.76, 0.00, 0.00], corner2=[7.72, 0.00, 0.00]),
    Wall(corner1=[7.72, 0.00, 0.00], corner2=[7.72, 2.26, 0.00]),
    Wall(corner1=[7.72, 2.26, 0.00], corner2=[12.16, 2.26, 0.00]),
    Wall(corner1=[12.16, 2.26, 0.00], corner2=[12.16, 3.66, 0.00]),
    Wall(corner1=[12.16, 3.66, 0.00], corner2=[10.57, 3.66, 0.00]),
    Wall(corner1=[10.57, 3.66, 0.00], corner2=[10.57, 4.00, 0.00]),
    Wall(corner1=[10.57, 4.00, 0.00], corner2=[8.02, 4.00, 0.00]),
    Wall(corner1=[8.02, 4.00, 0.00], corner2=[8.02, 3.66, 0.00]),
    Wall(corner1=[8.02, 3.66, 0.00], corner2=[7.72, 3.66, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
sofa_A = Assets(description="sofa", size=[0.95, 2.40, 0.85], placements=[AssetInstance() for _ in range(1)])
sofa_B = Assets(description="sofa", size=[0.95, 1.80, 0.85], placements=[AssetInstance() for _ in range(1)])
stool = Assets(description="stool", size=[0.45, 0.45, 0.45], placements=[AssetInstance() for _ in range(1)])
carpet_A = Assets(description="carpet", size=[2.80, 3.60, 0.02], placements=[AssetInstance() for _ in range(1)])
dining_table_combination = Assets(description="dining table combination", size=[2.40, 3.20, 0.95], placements=[AssetInstance() for _ in range(1)])
sofa_C = Assets(description="sofa", size=[0.95, 2.40, 0.85], placements=[AssetInstance() for _ in range(1)])
wine_cabinet = Assets(description="wine cabinet", size=[0.45, 1.20, 1.90], placements=[AssetInstance() for _ in range(1)])
side_table_A = Assets(description="side table", size=[0.55, 0.55, 0.55], placements=[AssetInstance() for _ in range(1)])
carpet_B = Assets(description="carpet", size=[3.00, 3.80, 0.02], placements=[AssetInstance() for _ in range(1)])
side_table_B = Assets(description="side table", size=[0.55, 0.55, 0.55], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.60, 1.80, 2.30], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="coffee table", size=[0.70, 1.30, 0.42], placements=[AssetInstance() for _ in range(1)])

sofa_A[0].instance_id = 'sofa_A_0'
sofa_B[0].instance_id = 'sofa_B_0'
stool[0].instance_id = 'stool_0'
carpet_A[0].instance_id = 'carpet_A_0'
dining_table_combination[0].instance_id = 'dining_table_combination_0'
sofa_C[0].instance_id = 'sofa_C_0'
wine_cabinet[0].instance_id = 'wine_cabinet_0'
side_table_A[0].instance_id = 'side_table_A_0'
carpet_B[0].instance_id = 'carpet_B_0'
side_table_B[0].instance_id = 'side_table_B_0'
wardrobe[0].instance_id = 'wardrobe_0'
coffee_table[0].instance_id = 'coffee_table_0'
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
walls[10].instance_id = 'walls_10'
walls[11].instance_id = 'walls_11'
walls[12].instance_id = 'walls_12'
walls[13].instance_id = 'walls_13'
walls[14].instance_id = 'walls_14'
walls[15].instance_id = 'walls_15'
walls[16].instance_id = 'walls_16'
walls[17].instance_id = 'walls_17'
walls[18].instance_id = 'walls_18'
walls[19].instance_id = 'walls_19'

sofa_A[0].position = [10.39984696782747, 3.2369747605302344, 0.425]
sofa_A[0].rotation = [0, 0, 0]
sofa_B[0].position = [11.8481328937064, 2.4893571157816137, 0.425]
sofa_B[0].rotation = [0, 0, 0]
stool[0].position = [7.396303208057059, 2.2600921233642413, 0.225]
stool[0].rotation = [0, 0, 0]
carpet_A[0].position = [7.484240816438498, 1.464213392898182, 0.01]
carpet_A[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [4.443623753470007, 5.718883810308502, 0.475]
dining_table_combination[0].rotation = [0, 0, 0]
sofa_C[0].position = [6.734610695629808, 3.81486799829081, 0.425]
sofa_C[0].rotation = [0, 0, 0]
wine_cabinet[0].position = [6.364153915048771, 1.5858134972286502, 0.95]
wine_cabinet[0].rotation = [0, 0, 0]
side_table_A[0].position = [10.199499488064896, 2.980510586286013, 0.275]
side_table_A[0].rotation = [0, 0, 0]
carpet_B[0].position = [7.671553830241373, 6.086632172258299, 0.01]
carpet_B[0].rotation = [0, 0, 0]
side_table_B[0].position = [0.621393305333788, 3.391162114354164, 0.275]
side_table_B[0].rotation = [0, 0, 0]
wardrobe[0].position = [6.117376833728338, 2.6445748455802605, 1.15]
wardrobe[0].rotation = [0, 0, 0]
coffee_table[0].position = [4.68513323233775, 4.456470722751201, 0.21]
coffee_table[0].rotation = [0, 0, 0]
sofa_A[0].position = [10.39984696782747, 3.2369747605302344, 0.425]
sofa_A[0].rotation = [0, 0, 0]
sofa_B[0].position = [11.8481328937064, 2.4893571157816137, 0.425]
sofa_B[0].rotation = [0, 0, 0]
stool[0].position = [7.396303208057059, 2.2600921233642413, 0.225]
stool[0].rotation = [0, 0, 0]
carpet_A[0].position = [7.484240816438498, 1.464213392898182, 0.01]
carpet_A[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [4.443623753470007, 5.718883810308502, 0.475]
dining_table_combination[0].rotation = [0, 0, 0]
sofa_C[0].position = [6.734610695629808, 3.81486799829081, 0.425]
sofa_C[0].rotation = [0, 0, 0]
wine_cabinet[0].position = [6.364153915048771, 1.5858134972286502, 0.95]
wine_cabinet[0].rotation = [0, 0, 0]
side_table_A[0].position = [10.199499488064896, 2.980510586286013, 0.275]
side_table_A[0].rotation = [0, 0, 0]
carpet_B[0].position = [7.671553830241373, 6.086632172258299, 0.01]
carpet_B[0].rotation = [0, 0, 0]
side_table_B[0].position = [0.621393305333788, 3.391162114354164, 0.275]
side_table_B[0].rotation = [0, 0, 0]
wardrobe[0].position = [6.117376833728338, 2.6445748455802605, 1.15]
wardrobe[0].rotation = [0, 0, 0]
coffee_table[0].position = [4.68513323233775, 4.456470722751201, 0.21]
coffee_table[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the upper room for dining, the left recess for sofa_A, and the
# central/right portions for the remaining seating. All coordinates follow
# the supplied boundary rather than assuming a rectangular room.
#
# Rugs intentionally lie beneath furniture; their overlapping footprints
# are not furniture collisions. Their thickness is included in supported
# furniture heights.

layout_specs = [
    # asset,                 center position,       yaw in degrees
    (sofa_A,                 [2.55, 3.77, 0.425],   270),
    (sofa_B,                 [9.35, 3.50, 0.425],   270),
    (sofa_C,                 [7.20, 3.03, 0.445],   180),
    (coffee_table,           [5.70, 3.03, 0.230],     0),
    (stool,                  [4.30, 3.40, 0.225],     0),
    (dining_table_combination, [5.85, 5.47, 0.495],   90),
    (wine_cabinet,           [0.80, 2.80, 0.950],    90),
    (side_table_A,           [4.35, 3.98, 0.295],     0),
    (side_table_B,           [8.12, 2.58, 0.275],    90),
    (wardrobe,               [7.40, 0.90, 1.170],   180),
    (carpet_A,               [6.25, 1.85, 0.010],     0),
    (carpet_B,               [5.55, 5.56, 0.010],     0),
]

# Absolute position and orientation references keep furniture out of door
# approaches and prevent the solver from moving pieces into narrow wings.
# In particular, the upper dining group ends at y=6.67, leaving a clear
# approach to the large north doorway. The fixed cabinet at (4.18, 7.06)
# is untouched and has no furniture placed over its footprint.
for asset_group, center_xyz, yaw_degrees in layout_specs:
    asset_group[0].position = list(center_xyz)
    asset_group[0].rotation = [0, 0, radians(yaw_degrees)]

    solver.distance_constraint(
        asset_group[0],
        AssetInstance(position=list(center_xyz)),
        0,
        0,
        weight=10,
    )

# State the required facing relationship before general orientation locks.
# The coffee table is in the open space between the left sofa and sofa_C;
# sofa_C faces directly west toward it.
solver.point_towards(sofa_C[0], coffee_table[0])

for asset_group, center_xyz, yaw_degrees in layout_specs:
    solver.align_with(
        asset_group[0],
        AssetInstance(
            position=list(center_xyz),
            rotation=[0, 0, radians(yaw_degrees)],
        ),
        angle=0,
    )

# These floor-level pieces rest on the rugs rather than intersecting their
# thin solids. The coffee and side tables are freestanding furniture, not
# tabletop accessories.
solver.on_top_of(coffee_table[0], carpet_A[0])
solver.on_top_of(wardrobe[0], carpet_A[0])
solver.on_top_of(sofa_C[0], carpet_A[0])
solver.on_top_of(dining_table_combination[0], carpet_B[0])
solver.on_top_of(side_table_A[0], carpet_B[0])

# Preserve the seating relationships as well as their absolute placement.
# Distances use full 3-D bounding-box centers, as required by the API.
for moving_instance, reference_instance in [
    (coffee_table[0], sofa_A[0]),
    (coffee_table[0], sofa_C[0]),
    (sofa_C[0], coffee_table[0]),
    (side_table_A[0], sofa_A[0]),
    (side_table_B[0], sofa_B[0]),
]:
    center_distance = sum(
        (moving_instance.position[axis] - reference_instance.position[axis]) ** 2
        for axis in range(3)
    ) ** 0.5
    solver.distance_constraint(
        moving_instance,
        reference_instance,
        center_distance,
        center_distance,
        weight=10,
    )

# Reinforce separation for every pair of solid furniture pieces. At the
# specified orientations, the horizontal bounding boxes are disjoint.
# Rugs are excluded because furniture is intentionally supported by them.
solid_groups = [
    sofa_A, sofa_B, sofa_C, coffee_table, stool,
    dining_table_combination, wine_cabinet,
    side_table_A, side_table_B, wardrobe,
]

for first_index, first_group in enumerate(solid_groups):
    for second_group in solid_groups[first_index + 1:]:
        separation = sum(
            (first_group[0].position[axis] -
             second_group[0].position[axis]) ** 2
            for axis in range(3)
        ) ** 0.5
        solver.distance_constraint(
            first_group[0], second_group[0],
            separation, None, weight=10,
        )
        solver.distance_constraint(
            second_group[0], first_group[0],
            separation, None, weight=10,
        )

solver.constraints = []
sofa_C[0].position = [7.152313232421875, 2.9922537803649902, 0.445000022649765]
sofa_C[0].rotation = [0, 0, -3.063052831984764]
sofa_C[0].optimize = 2
sofa_A[0].position = [2.461160898208618, 3.6971068382263184, 0.42500001192092896]
sofa_A[0].rotation = [0, 0, -1.4985396962335082]
sofa_A[0].optimize = 2
side_table_B[0].position = [8.18044662475586, 2.587968349456787, 0.2750000059604645]
side_table_B[0].rotation = [0, 0, 1.639911365010656]
side_table_B[0].optimize = 2
coffee_table[0].position = [5.613243579864502, 3.132570505142212, 0.22999998927116394]
coffee_table[0].rotation = [0, 0, 0.08168141045923738]
coffee_table[0].optimize = 2
carpet_B[0].position = [5.550000190734863, 5.536673545837402, 0.009999999776482582]
carpet_B[0].rotation = [0, 0, 0.0157079639172164]
carpet_B[0].optimize = 2
dining_table_combination[0].position = [5.777646541595459, 5.542350769042969, 0.4950000047683716]
dining_table_combination[0].rotation = [0, 0, 1.639911365010656]
dining_table_combination[0].optimize = 2
sofa_B[0].position = [9.417699813842773, 3.463979959487915, 0.42500001192092896]
sofa_B[0].rotation = [0, 0, -1.5016812885791373]
sofa_B[0].optimize = 2
carpet_A[0].position = [6.25, 1.850000023841858, 0.009999999776482582]
carpet_A[0].rotation = [0, 0, 0.01884955539881635]
carpet_A[0].optimize = 2
wardrobe[0].position = [7.358561992645264, 0.9185692667961121, 1.1699999570846558]
wardrobe[0].rotation = [0, 0, -3.072477615374034]
wardrobe[0].optimize = 2
stool[0].position = [4.267970561981201, 3.3995962142944336, 0.22499999403953552]
stool[0].rotation = [0, 0, 0.0659734453763722]
stool[0].optimize = 2
side_table_A[0].position = [4.314136028289795, 3.881253719329834, 0.29500001668930054]
side_table_A[0].rotation = [0, 0, 0.0722566305613884]
side_table_A[0].optimize = 2
wine_cabinet[0].position = [0.6588597297668457, 2.814065933227539, 0.949999988079071]
wine_cabinet[0].rotation = [0, 0, 1.6367697721712688]
wine_cabinet[0].optimize = 2

