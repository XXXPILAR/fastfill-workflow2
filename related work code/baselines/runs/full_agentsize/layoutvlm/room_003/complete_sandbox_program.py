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
    Wall(corner1=[0.00, 3.26, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.25, 0.00, 0.00]),
    Wall(corner1=[3.25, 0.00, 0.00], corner2=[3.24, 3.26, 0.00]),
    Wall(corner1=[3.24, 3.26, 0.00], corner2=[0.00, 3.26, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
container_A = Assets(description="container", size=[0.32, 0.38, 0.28], placements=[AssetInstance() for _ in range(1)])
wardrobe_A = Assets(description="wardrobe", size=[0.60, 0.90, 2.20], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="lamp", size=[0.28, 0.28, 0.48], placements=[AssetInstance() for _ in range(1)])
decoration = Assets(description="decoration", size=[0.12, 0.22, 0.30], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="shelf", size=[0.25, 0.80, 0.04], placements=[AssetInstance() for _ in range(1)])
clock = Assets(description="clock", size=[0.05, 0.30, 0.30], placements=[AssetInstance() for _ in range(1)])
container_B = Assets(description="container", size=[0.30, 0.32, 0.24], placements=[AssetInstance() for _ in range(1)])
rack = Assets(description="rack", size=[0.38, 0.85, 1.55], placements=[AssetInstance() for _ in range(1)])
container_C = Assets(description="container", size=[0.32, 0.38, 0.28], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.35, 0.65, 0.75], placements=[AssetInstance() for _ in range(1)])
wardrobe_B = Assets(description="wardrobe", size=[0.60, 0.90, 2.20], placements=[AssetInstance() for _ in range(1)])
container_D = Assets(description="container", size=[0.28, 0.30, 0.22], placements=[AssetInstance() for _ in range(1)])
container_E = Assets(description="container", size=[0.36, 0.42, 0.30], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.00, 1.50, 0.55], placements=[AssetInstance() for _ in range(1)])
container_F = Assets(description="container", size=[0.36, 0.42, 0.30], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.30, 0.30, 0.50], placements=[AssetInstance() for _ in range(1)])

container_A[0].instance_id = 'container_A_0'
wardrobe_A[0].instance_id = 'wardrobe_A_0'
lamp_A[0].instance_id = 'lamp_A_0'
decoration[0].instance_id = 'decoration_0'
shelf_A[0].instance_id = 'shelf_A_0'
clock[0].instance_id = 'clock_0'
container_B[0].instance_id = 'container_B_0'
rack[0].instance_id = 'rack_0'
container_C[0].instance_id = 'container_C_0'
shelf_B[0].instance_id = 'shelf_B_0'
wardrobe_B[0].instance_id = 'wardrobe_B_0'
container_D[0].instance_id = 'container_D_0'
container_E[0].instance_id = 'container_E_0'
bed[0].instance_id = 'bed_0'
container_F[0].instance_id = 'container_F_0'
lamp_B[0].instance_id = 'lamp_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

container_A[0].position = [2.2684553327295984, 1.8541272660261652, 0.14]
container_A[0].rotation = [0, 0, 0]
wardrobe_A[0].position = [2.2036749920646046, 0.6119465575467609, 1.1]
wardrobe_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [1.9278546559074037, 1.7079527983566423, 0.24]
lamp_A[0].rotation = [0, 0, 0]
decoration[0].position = [2.883470802926292, 0.9064305820405365, 0.15]
decoration[0].rotation = [0, 0, 0]
shelf_A[0].position = [2.135899167297461, 1.1454369121085695, 0.02]
shelf_A[0].rotation = [0, 0, 0]
clock[0].position = [2.2007655691316503, 1.7426594183689228, 0.15]
clock[0].rotation = [0, 0, 0]
container_B[0].position = [2.1232652051171734, 0.3253393745924026, 0.12]
container_B[0].rotation = [0, 0, 0]
rack[0].position = [0.12105274922585914, 0.7253610744746477, 0.775]
rack[0].rotation = [0, 0, 0]
container_C[0].position = [1.164894055103776, 1.1380371461454206, 0.14]
container_C[0].rotation = [0, 0, 0]
shelf_B[0].position = [1.8554419202184183, 2.7362331115694523, 0.375]
shelf_B[0].rotation = [0, 0, 0]
wardrobe_B[0].position = [1.520713694166509, 1.9351544546099433, 1.1]
wardrobe_B[0].rotation = [0, 0, 0]
container_D[0].position = [0.31316589369127273, 1.405180799319922, 0.11]
container_D[0].rotation = [0, 0, 0]
container_E[0].position = [1.9208449524954359, 1.2178430501037252, 0.15]
container_E[0].rotation = [0, 0, 0]
bed[0].position = [1.7201311991804844, 0.6541516626757684, 0.275]
bed[0].rotation = [0, 0, 0]
container_F[0].position = [1.224753988530316, 1.070942285948454, 0.15]
container_F[0].rotation = [0, 0, 0]
lamp_B[0].position = [2.5603141886238547, 1.1463688005290624, 0.25]
lamp_B[0].rotation = [0, 0, 0]
container_A[0].position = [2.2684553327295984, 1.8541272660261652, 0.14]
container_A[0].rotation = [0, 0, 0]
wardrobe_A[0].position = [2.2036749920646046, 0.6119465575467609, 1.1]
wardrobe_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [1.9278546559074037, 1.7079527983566423, 0.24]
lamp_A[0].rotation = [0, 0, 0]
decoration[0].position = [2.883470802926292, 0.9064305820405365, 0.15]
decoration[0].rotation = [0, 0, 0]
shelf_A[0].position = [2.135899167297461, 1.1454369121085695, 0.02]
shelf_A[0].rotation = [0, 0, 0]
clock[0].position = [2.2007655691316503, 1.7426594183689228, 0.15]
clock[0].rotation = [0, 0, 0]
container_B[0].position = [2.1232652051171734, 0.3253393745924026, 0.12]
container_B[0].rotation = [0, 0, 0]
rack[0].position = [0.12105274922585914, 0.7253610744746477, 0.775]
rack[0].rotation = [0, 0, 0]
container_C[0].position = [1.164894055103776, 1.1380371461454206, 0.14]
container_C[0].rotation = [0, 0, 0]
shelf_B[0].position = [1.8554419202184183, 2.7362331115694523, 0.375]
shelf_B[0].rotation = [0, 0, 0]
wardrobe_B[0].position = [1.520713694166509, 1.9351544546099433, 1.1]
wardrobe_B[0].rotation = [0, 0, 0]
container_D[0].position = [0.31316589369127273, 1.405180799319922, 0.11]
container_D[0].rotation = [0, 0, 0]
container_E[0].position = [1.9208449524954359, 1.2178430501037252, 0.15]
container_E[0].rotation = [0, 0, 0]
bed[0].position = [1.7201311991804844, 0.6541516626757684, 0.275]
bed[0].rotation = [0, 0, 0]
container_F[0].position = [1.224753988530316, 1.070942285948454, 0.15]
container_F[0].rotation = [0, 0, 0]
lamp_B[0].position = [2.5603141886238547, 1.1463688005290624, 0.25]
lamp_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Orientation references for furniture facing inward from each occupied wall.
left_facing = AssetInstance(rotation=[0, 0, radians(0)])
bottom_facing = AssetInstance(rotation=[0, 0, radians(90)])
top_facing = AssetInstance(rotation=[0, 0, radians(-90)])

# The bed occupies the lower-left portion of the room. Rotating it places its
# 1.50 m side along x and leaves a clear circulation lane to the door.
bed[0].position = [0.75, 1.00, 0.275]
bed[0].rotation = [0, 0, radians(90)]

# A low shelf assembly occupies the left wall immediately beyond the bed.
shelf_B[0].position = [0.175, 2.42, 0.375]
shelf_B[0].rotation = [0, 0, radians(0)]

# The thin shelf is supported by shelf_B. Its center is deliberately between
# container_C (o0008) and container_A (o0000).
shelf_A[0].position = [0.125, 2.42, 0.77]
shelf_A[0].rotation = [0, 0, radians(0)]

container_C[0].position = [0.16, 2.22, 0.93]
container_C[0].rotation = [0, 0, radians(0)]

container_A[0].position = [0.16, 2.62, 0.93]
container_A[0].rotation = [0, 0, radians(0)]

# Tall storage is grouped along the top wall, facing into the room.
wardrobe_A[0].position = [0.48, 2.96, 1.10]
wardrobe_A[0].rotation = [0, 0, radians(-90)]

wardrobe_B[0].position = [1.43, 2.96, 1.10]
wardrobe_B[0].rotation = [0, 0, radians(-90)]

rack[0].position = [2.70, 3.07, 0.775]
rack[0].rotation = [0, 0, radians(-90)]

# Smaller storage and decoration use the tops of the wardrobes, keeping the
# limited floor area available for circulation.
container_B[0].position = [0.48, 3.11, 2.32]
container_B[0].rotation = [0, 0, radians(-90)]

decoration[0].position = [0.48, 3.20, 2.59]
decoration[0].rotation = [0, 0, radians(-90)]

container_D[0].position = [1.43, 3.12, 2.31]
container_D[0].rotation = [0, 0, radians(-90)]

# These containers serve as compact bedside stands. They remain below the
# doorway's lower edge, leaving the main door approach unobstructed.
container_E[0].position = [1.75, 0.21, 0.15]
container_E[0].rotation = [0, 0, radians(90)]

container_F[0].position = [2.23, 0.21, 0.15]
container_F[0].rotation = [0, 0, radians(90)]

lamp_A[0].position = [1.75, 0.15, 0.54]
lamp_A[0].rotation = [0, 0, radians(90)]

lamp_B[0].position = [2.23, 0.15, 0.55]
lamp_B[0].rotation = [0, 0, radians(90)]

# The clock is wall-mounted above the bed, so it consumes no additional floor
# area and faces into the room.
clock[0].position = [0.025, 1.65, 1.60]
clock[0].rotation = [0, 0, radians(0)]


# Major floor objects are anchored to their intended walls first.
solver.against_wall(bed[0], walls[1])
solver.align_with(bed[0], bottom_facing)

solver.against_wall(shelf_B[0], walls[0])
solver.align_with(shelf_B[0], left_facing)

solver.against_wall(wardrobe_A[0], walls[3])
solver.align_with(wardrobe_A[0], top_facing)

solver.against_wall(wardrobe_B[0], walls[3])
solver.align_with(wardrobe_B[0], top_facing)

solver.against_wall(rack[0], walls[3])
solver.align_with(rack[0], top_facing)


# Preserve the vertical shelf assembly and the required
# container_C -- shelf_A -- container_A ordering.
solver.against_wall(shelf_A[0], walls[0])
solver.on_top_of(shelf_A[0], shelf_B[0])
solver.align_with(shelf_A[0], shelf_B[0])

solver.against_wall(container_C[0], walls[0])
solver.on_top_of(container_C[0], shelf_A[0])
solver.align_with(container_C[0], shelf_A[0])

solver.against_wall(container_A[0], walls[0])
solver.on_top_of(container_A[0], shelf_A[0])
solver.align_with(container_A[0], shelf_A[0])

# Keep the two flanking containers evenly separated about the shelf center.
solver.distance_constraint(
    container_C[0], container_A[0], 0.40, 0.40, weight=10
)
solver.distance_constraint(
    shelf_A[0], container_C[0], 0.25, 0.27, weight=5
)
solver.distance_constraint(
    shelf_A[0], container_A[0], 0.25, 0.27, weight=5
)


# Secure the objects stored above the wardrobes.
solver.against_wall(container_B[0], walls[3])
solver.on_top_of(container_B[0], wardrobe_A[0])
solver.align_with(container_B[0], wardrobe_A[0])

solver.against_wall(decoration[0], walls[3])
solver.on_top_of(decoration[0], container_B[0])
solver.align_with(decoration[0], container_B[0])

solver.against_wall(container_D[0], walls[3])
solver.on_top_of(container_D[0], wardrobe_B[0])
solver.align_with(container_D[0], wardrobe_B[0])


# Anchor the bedside containers and their lamps below the door opening.
solver.against_wall(container_E[0], walls[1])
solver.align_with(container_E[0], bottom_facing)

solver.against_wall(container_F[0], walls[1])
solver.align_with(container_F[0], bottom_facing)

solver.against_wall(lamp_A[0], walls[1])
solver.on_top_of(lamp_A[0], container_E[0])
solver.align_with(lamp_A[0], container_E[0])

solver.against_wall(lamp_B[0], walls[1])
solver.on_top_of(lamp_B[0], container_F[0])
solver.align_with(lamp_B[0], container_F[0])


# Keep the wall clock attached to and oriented away from the left wall.
solver.against_wall(clock[0], walls[0])
solver.align_with(clock[0], left_facing)

solver.constraints = []
container_E[0].position = [1.75, 0.1799682229757309, 0.15000000596046448]
container_E[0].rotation = [0, 0, 1.5707610123327027]
container_E[0].optimize = 2
container_D[0].position = [1.4299999475479126, 3.118260145187378, 2.309999942779541]
container_D[0].rotation = [0, 0, -1.570818341911119]
container_D[0].optimize = 2
container_C[0].position = [0.15999360382556915, 2.2200000286102295, 0.9299999475479126]
container_C[0].rotation = [0, 0, -3.973111930164916e-06]
container_C[0].optimize = 2
container_A[0].position = [0.15999360382556915, 2.619999885559082, 0.9299999475479126]
container_A[0].rotation = [0, 0, -3.973111930164916e-06]
container_A[0].optimize = 2
rack[0].position = [2.700000047683716, 3.0682601928710938, 0.7749999761581421]
rack[0].rotation = [0, 0, -1.570816698864252]
rack[0].optimize = 2
shelf_B[0].position = [0.1749887466430664, 2.4200000762939453, 0.375]
shelf_B[0].rotation = [0, 0, -3.5549518470181136e-05]
shelf_B[0].optimize = 2
container_F[0].position = [2.2300000190734863, 0.1799682229757309, 0.15000000596046448]
container_F[0].rotation = [0, 0, 1.5707610123327027]
container_F[0].optimize = 2
lamp_A[0].position = [1.75, 0.13997378945350647, 0.5400000214576721]
lamp_A[0].rotation = [0, 0, 1.57077457948608]
lamp_A[0].optimize = 2
shelf_A[0].position = [0.12497763335704803, 2.404602289199829, 0.7699999809265137]
shelf_A[0].rotation = [0, 0, 5.591579235960039e-05]
shelf_A[0].optimize = 2
wardrobe_B[0].position = [1.4299999475479126, 2.9582595825195312, 1.100000023841858]
wardrobe_B[0].rotation = [0, 0, -1.5708319193272544]
wardrobe_B[0].optimize = 2
bed[0].position = [1.0388768911361694, 1.280829668045044, 0.2750000059604645]
bed[0].rotation = [0, 0, -0.02142216710632135]
bed[0].optimize = 2
clock[0].position = [0.02498561516404152, 1.649999976158142, 0.15000000596046448]
clock[0].rotation = [0, 0, -2.0486061700082245e-05]
clock[0].optimize = 2
wardrobe_A[0].position = [0.47999998927116394, 2.9582595825195312, 1.100000023841858]
wardrobe_A[0].rotation = [0, 0, -1.5708319193272544]
wardrobe_A[0].optimize = 2
container_B[0].position = [0.47999998927116394, 3.1082606315612793, 2.319999933242798]
container_B[0].rotation = [0, 0, -1.5708003302029074]
container_B[0].optimize = 2
decoration[0].position = [0.47999998927116394, 3.198260545730591, 2.5899999141693115]
decoration[0].rotation = [0, 0, -1.5708183062907837]
decoration[0].optimize = 2
lamp_B[0].position = [2.2300000190734863, 0.14997635781764984, 0.550000011920929]
lamp_B[0].rotation = [0, 0, 1.5707744876805316]
lamp_B[0].optimize = 2

