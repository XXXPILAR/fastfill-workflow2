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
    Wall(corner1=[0.04, 3.44, 0.00], corner2=[0.00, 3.40, 0.00]),
    Wall(corner1=[0.00, 3.40, 0.00], corner2=[0.00, 0.04, 0.00]),
    Wall(corner1=[0.00, 0.04, 0.00], corner2=[0.04, 0.00, 0.00]),
    Wall(corner1=[0.04, 0.00, 0.00], corner2=[3.40, 0.00, 0.00]),
    Wall(corner1=[3.40, 0.00, 0.00], corner2=[3.44, 0.04, 0.00]),
    Wall(corner1=[3.44, 0.04, 0.00], corner2=[3.44, 3.40, 0.00]),
    Wall(corner1=[3.44, 3.40, 0.00], corner2=[3.40, 3.44, 0.00]),
    Wall(corner1=[3.40, 3.44, 0.00], corner2=[0.04, 3.44, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
cup = Assets(description="cup", size=[0.08, 0.09, 0.10], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.60, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
bottle = Assets(description="bottle", size=[0.08, 0.10, 0.28], placements=[AssetInstance() for _ in range(1)])
washing_machine_A = Assets(description="washing machine", size=[0.65, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.35, 0.60, 0.70], placements=[AssetInstance() for _ in range(1)])
cabinet_C = Assets(description="cabinet", size=[0.60, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
sink = Assets(description="sink", size=[0.50, 0.60, 0.22], placements=[AssetInstance() for _ in range(1)])
cabinet_D = Assets(description="cabinet", size=[0.60, 0.60, 2.10], placements=[AssetInstance() for _ in range(1)])
washing_machine_B = Assets(description="washing machine", size=[0.65, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
plant = Assets(description="plant", size=[0.25, 0.25, 0.40], placements=[AssetInstance() for _ in range(1)])
shelf = Assets(description="shelf", size=[0.25, 0.90, 0.04], placements=[AssetInstance() for _ in range(1)])

cup[0].instance_id = 'cup_0'
cabinet_A[0].instance_id = 'cabinet_A_0'
bottle[0].instance_id = 'bottle_0'
washing_machine_A[0].instance_id = 'washing_machine_A_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
cabinet_C[0].instance_id = 'cabinet_C_0'
sink[0].instance_id = 'sink_0'
cabinet_D[0].instance_id = 'cabinet_D_0'
washing_machine_B[0].instance_id = 'washing_machine_B_0'
plant[0].instance_id = 'plant_0'
shelf[0].instance_id = 'shelf_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

cup[0].position = [1.5014710131143811, 0.45292787608450696, 0.05]
cup[0].rotation = [0, 0, 0]
cabinet_A[0].position = [3.021924821463962, 2.133092745924846, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
bottle[0].position = [2.2672929002766113, 2.4357375431607307, 0.14]
bottle[0].rotation = [0, 0, 0]
washing_machine_A[0].position = [3.4154406117606912, 2.506606328655752, 0.425]
washing_machine_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [1.6155228490266518, 0.5411364279542455, 0.35]
cabinet_B[0].rotation = [0, 0, 0]
cabinet_C[0].position = [1.9807277031953898, 2.3095631185028505, 0.45]
cabinet_C[0].rotation = [0, 0, 0]
sink[0].position = [1.7553127466348308, 1.4555945511655606, 0.11]
sink[0].rotation = [0, 0, 0]
cabinet_D[0].position = [1.4130141851159423, 0.2723063287004241, 1.05]
cabinet_D[0].rotation = [0, 0, 0]
washing_machine_B[0].position = [0.8814469094362334, 0.8318457035375524, 0.425]
washing_machine_B[0].rotation = [0, 0, 0]
plant[0].position = [1.3878474313842815, 2.825379645467025, 0.2]
plant[0].rotation = [0, 0, 0]
shelf[0].position = [2.3173324247695946, 0.9252392334786229, 0.02]
shelf[0].rotation = [0, 0, 0]
cup[0].position = [1.5014710131143811, 0.45292787608450696, 0.05]
cup[0].rotation = [0, 0, 0]
cabinet_A[0].position = [3.021924821463962, 2.133092745924846, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
bottle[0].position = [2.2672929002766113, 2.4357375431607307, 0.14]
bottle[0].rotation = [0, 0, 0]
washing_machine_A[0].position = [3.4154406117606912, 2.506606328655752, 0.425]
washing_machine_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [1.6155228490266518, 0.5411364279542455, 0.35]
cabinet_B[0].rotation = [0, 0, 0]
cabinet_C[0].position = [1.9807277031953898, 2.3095631185028505, 0.45]
cabinet_C[0].rotation = [0, 0, 0]
sink[0].position = [1.7553127466348308, 1.4555945511655606, 0.11]
sink[0].rotation = [0, 0, 0]
cabinet_D[0].position = [1.4130141851159423, 0.2723063287004241, 1.05]
cabinet_D[0].rotation = [0, 0, 0]
washing_machine_B[0].position = [0.8814469094362334, 0.8318457035375524, 0.425]
washing_machine_B[0].rotation = [0, 0, 0]
plant[0].position = [1.3878474313842815, 2.825379645467025, 0.2]
plant[0].rotation = [0, 0, 0]
shelf[0].position = [2.3173324247695946, 0.9252392334786229, 0.02]
shelf[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the actual boundary coordinates: the room occupies [0, 3.44]^2.
# A west-wall utility run leaves the center and east-side doorway clear.
# The sink sits below the north window; tall storage stays away from it.
# Rotated bounding boxes and small gaps are accounted for in these centers.
layout_specs = [
    (cabinet_D[0],         [0.300, 0.400, 1.050],   0, walls[1]),
    (washing_machine_A[0], [0.325, 1.150, 0.425],   0, walls[1]),
    (washing_machine_B[0], [0.325, 1.850, 0.425],   0, walls[1]),
    (cabinet_A[0],         [0.300, 2.650, 0.450],   0, walls[1]),

    # At -90 degrees, cabinet_C has a 0.80 m east-west footprint.
    (cabinet_C[0],         [1.710, 3.140, 0.450], -90, walls[7]),
    (sink[0],              [1.710, 3.140, 1.010], -90, None),

    # Shallow south-wall storage faces into the room.
    (cabinet_B[0],         [1.350, 0.175, 0.350],  90, walls[3]),
    (cup[0],              [1.350, 0.175, 0.750],  90, None),

    # Wall-mounted shelf above the machines, not across their floor access.
    (shelf[0],            [0.125, 1.500, 1.500],   0, walls[1]),
    (bottle[0],           [0.125, 1.650, 1.660],   0, None),
    (plant[0],            [0.300, 2.650, 1.100],   0, None),
]

for instance, center, yaw_degrees, supporting_wall in layout_specs:
    instance.position = list(center)
    instance.rotation = [0, 0, radians(yaw_degrees)]

# Support constraints come first: the small objects must not fall to the floor.
# The sink rests on cabinet_C rather than intersecting its bounding box.
solver.on_top_of(sink[0], cabinet_C[0])
solver.on_top_of(cup[0], cabinet_B[0])
solver.on_top_of(bottle[0], shelf[0])
solver.on_top_of(plant[0], cabinet_A[0])

# Every instance receives an explicit position and orientation constraint.
# Fixed center targets preserve the clear entrance route, appliance gaps,
# and tabletop object separation. The shelf is wall-mounted at 1.50 m.
for instance, center, yaw_degrees, supporting_wall in layout_specs:
    solver.distance_constraint(
        instance,
        AssetInstance(position=list(center)),
        min_distance=0,
        max_distance=0,
        weight=10,
    )
    solver.align_with(
        instance,
        AssetInstance(rotation=[0, 0, radians(yaw_degrees)]),
        angle=0,
    )
    if supporting_wall is not None:
        solver.against_wall(instance, supporting_wall)

# Preserve support-relative orientation if the arrangement is adjusted.
solver.align_with(sink[0], cabinet_C[0])
solver.align_with(cup[0], cabinet_B[0])
solver.align_with(bottle[0], shelf[0])
solver.align_with(plant[0], cabinet_A[0])

solver.constraints = []
cup[0].position = [1.350000023841858, 0.17499999701976776, 0.75]
cup[0].rotation = [0, 0, 1.570870831101278]
cup[0].optimize = 2
cabinet_A[0].position = [0.3000052273273468, 2.6500000953674316, 0.44999998807907104]
cabinet_A[0].rotation = [0, 0, 5.245995315695289e-05]
cabinet_A[0].optimize = 2
bottle[0].position = [0.125, 1.649999976158142, 0.18000000715255737]
bottle[0].rotation = [0, 0, 7.43023099182291e-05]
bottle[0].optimize = 2
cabinet_C[0].position = [1.7100000381469727, 3.137533187866211, 0.44999998807907104]
cabinet_C[0].rotation = [0, 0, -1.5707439053054617]
cabinet_C[0].optimize = 2
cabinet_D[0].position = [0.3000418245792389, 0.4000000059604645, 1.0499999523162842]
cabinet_D[0].rotation = [0, 0, -8.597806966846727e-05]
cabinet_D[0].optimize = 2
sink[0].position = [1.7100000381469727, 3.140000104904175, 1.0099999904632568]
sink[0].rotation = [0, 0, -1.570722460565336]
sink[0].optimize = 2
plant[0].position = [0.30000001192092896, 2.6500000953674316, 1.100000023841858]
plant[0].rotation = [0, 0, 7.440840839034884e-05]
plant[0].optimize = 2
washing_machine_B[0].position = [0.3250451385974884, 1.850000023841858, 0.42500001192092896]
washing_machine_B[0].rotation = [0, 0, -8.598013467235346e-05]
washing_machine_B[0].optimize = 2
washing_machine_A[0].position = [0.3250451385974884, 1.149999976158142, 0.42500001192092896]
washing_machine_A[0].rotation = [0, 0, -8.598013467235346e-05]
washing_machine_A[0].optimize = 2
shelf[0].position = [0.1250176876783371, 1.5, 0.019999999552965164]
shelf[0].rotation = [0, 0, 5.2450719912011976e-05]
shelf[0].optimize = 2
cabinet_B[0].position = [1.350000023841858, 0.1749853938817978, 0.3499999940395355]
cabinet_B[0].rotation = [0, 0, 1.5708486836208766]
cabinet_B[0].optimize = 2

