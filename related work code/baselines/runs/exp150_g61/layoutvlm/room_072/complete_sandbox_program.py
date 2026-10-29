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
    Wall(corner1=[4.27, 0.00, 0.00], corner2=[4.27, 1.77, 0.00]),
    Wall(corner1=[4.27, 1.77, 0.00], corner2=[1.77, 1.77, 0.00]),
    Wall(corner1=[1.77, 1.77, 0.00], corner2=[1.77, 4.77, 0.00]),
    Wall(corner1=[1.77, 4.77, 0.00], corner2=[0.00, 4.77, 0.00]),
    Wall(corner1=[0.00, 4.77, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.27, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
shelf_A = Assets(description="shelf", size=[0.25, 0.80, 0.04], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.50, 1.00, 0.82], placements=[AssetInstance() for _ in range(1)])
sink = Assets(description="sink", size=[0.45, 0.65, 0.18], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.25, 0.70, 0.04], placements=[AssetInstance() for _ in range(1)])
shelf_C = Assets(description="shelf", size=[0.25, 0.70, 0.04], placements=[AssetInstance() for _ in range(1)])
shelf_D = Assets(description="shelf", size=[0.25, 0.80, 0.04], placements=[AssetInstance() for _ in range(1)])
shelf_E = Assets(description="shelf", size=[0.25, 0.70, 0.04], placements=[AssetInstance() for _ in range(1)])
bottle_A = Assets(description="bottle", size=[0.08, 0.08, 0.24], placements=[AssetInstance() for _ in range(1)])
toilet = Assets(description="toilet", size=[0.70, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.40, 0.60, 1.80], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="bottle", size=[0.07, 0.07, 0.20], placements=[AssetInstance() for _ in range(1)])
bottle_C = Assets(description="bottle", size=[0.06, 0.08, 0.22], placements=[AssetInstance() for _ in range(1)])

shelf_A[0].instance_id = 'shelf_A_0'
cabinet_A[0].instance_id = 'cabinet_A_0'
sink[0].instance_id = 'sink_0'
shelf_B[0].instance_id = 'shelf_B_0'
shelf_C[0].instance_id = 'shelf_C_0'
shelf_D[0].instance_id = 'shelf_D_0'
shelf_E[0].instance_id = 'shelf_E_0'
bottle_A[0].instance_id = 'bottle_A_0'
toilet[0].instance_id = 'toilet_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
bottle_B[0].instance_id = 'bottle_B_0'
bottle_C[0].instance_id = 'bottle_C_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

shelf_A[0].position = [0.5397733189451429, 1.3024465849099454, 0.02]
shelf_A[0].rotation = [0, 0, 0]
cabinet_A[0].position = [0.8397331261012999, 0.28147308441396224, 0.41]
cabinet_A[0].rotation = [0, 0, 0]
sink[0].position = [1.1429885532359987, 4.430638688880458, 0.09]
sink[0].rotation = [0, 0, 0]
shelf_B[0].position = [0.7055414649833182, 3.5893540993109254, 0.02]
shelf_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [3.606391833173186, 1.2349124851553759, 0.02]
shelf_C[0].rotation = [0, 0, 0]
shelf_D[0].position = [2.8631058319346523, 0.7545744800381261, 0.02]
shelf_D[0].rotation = [0, 0, 0]
shelf_E[0].position = [1.2930419567028, 4.698613581994187, 0.02]
shelf_E[0].rotation = [0, 0, 0]
bottle_A[0].position = [1.358869987549872, 1.7978775841316528, 0.12]
bottle_A[0].rotation = [0, 0, 0]
toilet[0].position = [1.7381702678706037, 2.094831313451145, 0.39]
toilet[0].rotation = [0, 0, 0]
cabinet_B[0].position = [0.342810822318589, 0.04252174350404758, 0.9]
cabinet_B[0].rotation = [0, 0, 0]
bottle_B[0].position = [4.258024543016921, 0.4240338222586729, 0.1]
bottle_B[0].rotation = [0, 0, 0]
bottle_C[0].position = [0.2959097259744635, 4.0643713198585445, 0.11]
bottle_C[0].rotation = [0, 0, 0]
shelf_A[0].position = [0.5397733189451429, 1.3024465849099454, 0.02]
shelf_A[0].rotation = [0, 0, 0]
cabinet_A[0].position = [0.8397331261012999, 0.28147308441396224, 0.41]
cabinet_A[0].rotation = [0, 0, 0]
sink[0].position = [1.1429885532359987, 4.430638688880458, 0.09]
sink[0].rotation = [0, 0, 0]
shelf_B[0].position = [0.7055414649833182, 3.5893540993109254, 0.02]
shelf_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [3.606391833173186, 1.2349124851553759, 0.02]
shelf_C[0].rotation = [0, 0, 0]
shelf_D[0].position = [2.8631058319346523, 0.7545744800381261, 0.02]
shelf_D[0].rotation = [0, 0, 0]
shelf_E[0].position = [1.2930419567028, 4.698613581994187, 0.02]
shelf_E[0].rotation = [0, 0, 0]
bottle_A[0].position = [1.358869987549872, 1.7978775841316528, 0.12]
bottle_A[0].rotation = [0, 0, 0]
toilet[0].position = [1.7381702678706037, 2.094831313451145, 0.39]
toilet[0].rotation = [0, 0, 0]
cabinet_B[0].position = [0.342810822318589, 0.04252174350404758, 0.9]
cabinet_B[0].rotation = [0, 0, 0]
bottle_B[0].position = [4.258024543016921, 0.4240338222586729, 0.1]
bottle_B[0].rotation = [0, 0, 0]
bottle_C[0].position = [0.2959097259744635, 4.0643713198585445, 0.11]
bottle_C[0].rotation = [0, 0, 0]

solver.constraints = []

# Coordinates follow the supplied walls. Keep the entrance and its approach
# clear; locate the vanity and toilet in the wider, eastern part of the room.
# The shallow shelves are wall-mounted, not loose objects resting on the floor.
layout_specs = [
    (cabinet_A, [4.02, 0.90, 0.41], 180),
    (sink,      [4.02, 0.90, 0.91], 180),
    (toilet,    [2.45, 0.90, 0.39],   0),
    (cabinet_B, [1.57, 4.42, 0.90], 180),

    # o0003 = shelf_B, o0004 = shelf_C, o0006 = shelf_E.
    # Their equal heights and ordered y coordinates put shelf_E between
    # shelf_B and shelf_C, with small gaps between adjacent shelves.
    (shelf_B,   [1.645, 2.15, 1.20], 180),
    (shelf_E,   [1.645, 2.90, 1.20], 180),
    (shelf_C,   [1.645, 3.65, 1.20], 180),

    # Two higher shelves provide additional storage without blocking
    # the windows on the western and northern walls.
    (shelf_A,   [1.645, 2.20, 1.90], 180),
    (shelf_D,   [1.645, 3.20, 1.90], 180),

    # Shelf tops are at z=1.22 and z=1.92 respectively.
    (bottle_A,  [1.645, 2.90, 1.34], 180),
    (bottle_B,  [1.645, 2.15, 1.32], 180),
    (bottle_C,  [1.645, 2.20, 2.03], 180),
]

for asset_group, center, yaw_degrees in layout_specs:
    asset_group[0].position = center
    asset_group[0].rotation = [0, 0, radians(yaw_degrees)]

# Important support and facing relationships come first.
solver.on_top_of(sink[0], cabinet_A[0])
solver.on_top_of(bottle_A[0], shelf_E[0])
solver.on_top_of(bottle_B[0], shelf_B[0])
solver.on_top_of(bottle_C[0], shelf_A[0])
solver.point_towards(toilet[0], sink[0])
solver.point_towards(sink[0], toilet[0])

solver.against_wall(cabinet_A[0], walls[0])
solver.against_wall(cabinet_B[0], walls[2])

for mounted_shelf in (shelf_A, shelf_B, shelf_C, shelf_D, shelf_E):
    solver.against_wall(mounted_shelf[0], walls[2])

# Preserve the selected centers, including the wall-mounted shelf heights.
# These fixed reference points are constraint targets, not additional furniture.
# Every new instance receives both a position and an orientation constraint.
for asset_group, center, yaw_degrees in layout_specs:
    fixed_reference = AssetInstance(
        position=list(center),
        rotation=[0, 0, radians(yaw_degrees)]
    )
    solver.distance_constraint(
        asset_group[0], fixed_reference, 0, 0, weight=10
    )
    solver.align_with(asset_group[0], fixed_reference)

# Reinforce the collinear shelf sequence. The outer shelves are 1.50 m
# apart and the middle shelf is 0.75 m from each, preserving "between".
solver.distance_constraint(shelf_E[0], shelf_C[0], 0.75, 0.75, weight=10)
solver.distance_constraint(shelf_E[0], shelf_B[0], 0.75, 0.75, weight=10)
solver.distance_constraint(shelf_C[0], shelf_B[0], 1.50, 1.50, weight=10)
solver.align_with(shelf_E[0], shelf_C[0])
solver.align_with(shelf_B[0], shelf_C[0])

# Keep the supported objects centered on their intended surfaces.
# Distances include the vertical separation of bounding-box centers.
solver.distance_constraint(sink[0], cabinet_A[0], 0.50, 0.50)
solver.distance_constraint(bottle_A[0], shelf_E[0], 0.14, 0.14)
solver.distance_constraint(bottle_B[0], shelf_B[0], 0.12, 0.12)
solver.distance_constraint(bottle_C[0], shelf_A[0], 0.13, 0.13)
solver.align_with(bottle_A[0], shelf_E[0])
solver.align_with(bottle_B[0], shelf_B[0])
solver.align_with(bottle_C[0], shelf_A[0])

# Maintain usable space between the toilet and vanity.
solver.distance_constraint(toilet[0], cabinet_A[0], 1.40, None, weight=10)

solver.constraints = []
bottle_A[0].position = [1.7256534099578857, 2.7297632694244385, 0.1599999964237213]
bottle_A[0].rotation = [0, 0, -3.141410266475614]
bottle_A[0].optimize = 2
shelf_D[0].position = [1.640641689300537, 3.200000047683716, 0.019999999552965164]
shelf_D[0].rotation = [0, 0, 3.1415706072530423]
shelf_D[0].optimize = 2
cabinet_A[0].position = [4.015617370605469, 0.8999999761581421, 0.4099999964237213]
cabinet_A[0].rotation = [0, 0, -3.141562746195155]
cabinet_A[0].optimize = 2
bottle_C[0].position = [1.7356394529342651, 2.200000047683716, 0.15000000596046448]
bottle_C[0].rotation = [0, 0, 3.141427547922751]
bottle_C[0].optimize = 2
sink[0].position = [4.038045883178711, 0.8999999761581421, 0.9099999666213989]
sink[0].rotation = [0, 0, -3.1196015053037707]
sink[0].optimize = 2
shelf_C[0].position = [1.6405603885650635, 3.6496121883392334, 0.019999999552965164]
shelf_C[0].rotation = [0, 0, 3.14156341522367]
shelf_C[0].optimize = 2
shelf_A[0].position = [1.6406264305114746, 2.200000047683716, 0.019999999552965164]
shelf_A[0].rotation = [0, 0, -3.141563092659401]
shelf_A[0].optimize = 2
shelf_E[0].position = [1.6395355463027954, 2.899214744567871, 0.019999999552965164]
shelf_E[0].rotation = [0, 0, -3.1415320484562215]
shelf_E[0].optimize = 2
cabinet_B[0].position = [1.5656418800354004, 4.420000076293945, 0.8999999761581421]
cabinet_B[0].rotation = [0, 0, 3.141570534778288]
cabinet_B[0].optimize = 2
bottle_B[0].position = [1.7306524515151978, 2.1500000953674316, 0.14000000059604645]
bottle_B[0].rotation = [0, 0, -3.1414100044455537]
bottle_B[0].optimize = 2
toilet[0].position = [2.450000047683716, 0.8999999761581421, 0.38999998569488525]
toilet[0].rotation = [0, 0, 0.01884955539881635]
toilet[0].optimize = 2
shelf_B[0].position = [1.6406170129776, 2.1500000953674316, 0.019999999552965164]
shelf_B[0].rotation = [0, 0, -3.141532090528433]
shelf_B[0].optimize = 2

