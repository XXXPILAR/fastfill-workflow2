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
    Wall(corner1=[3.76, 4.84, 0.00], corner2=[0.00, 4.84, 0.00]),
    Wall(corner1=[0.00, 4.84, 0.00], corner2=[0.10, 0.00, 0.00]),
    Wall(corner1=[0.10, 0.00, 0.00], corner2=[3.76, 0.00, 0.00]),
    Wall(corner1=[3.76, 0.00, 0.00], corner2=[3.76, 4.84, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
carpet_A = Assets(description="carpet", size=[3.00, 2.40, 0.02], placements=[AssetInstance() for _ in range(1)])
decoration_A = Assets(description="decoration", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
seat_A = Assets(description="seat", size=[0.70, 0.65, 0.85], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="cabinet", size=[0.50, 0.85, 1.80], placements=[AssetInstance() for _ in range(1)])
decoration_B = Assets(description="decoration", size=[0.18, 0.22, 0.32], placements=[AssetInstance() for _ in range(1)])
candle = Assets(description="candle", size=[0.08, 0.08, 0.15], placements=[AssetInstance() for _ in range(1)])
dresser = Assets(description="dresser", size=[0.50, 1.20, 0.85], placements=[AssetInstance() for _ in range(1)])
casket = Assets(description="casket", size=[0.18, 0.25, 0.12], placements=[AssetInstance() for _ in range(1)])
seat_B = Assets(description="seat", size=[0.70, 0.65, 0.85], placements=[AssetInstance() for _ in range(1)])
decoration_C = Assets(description="decoration", size=[0.04, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])
decoration_D = Assets(description="decoration", size=[0.15, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
vase = Assets(description="vase", size=[0.18, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.10, 1.60, 1.05], placements=[AssetInstance() for _ in range(1)])
mirror = Assets(description="mirror", size=[0.04, 0.70, 1.00], placements=[AssetInstance() for _ in range(1)])
carpet_B = Assets(description="carpet", size=[1.20, 0.70, 0.01], placements=[AssetInstance() for _ in range(1)])
pillow = Assets(description="pillow", size=[0.45, 0.65, 0.15], placements=[AssetInstance() for _ in range(1)])
case = Assets(description="case", size=[0.45, 0.60, 0.55], placements=[AssetInstance() for _ in range(1)])
globe = Assets(description="globe", size=[0.28, 0.28, 0.40], placements=[AssetInstance() for _ in range(1)])
lamp = Assets(description="lamp", size=[0.35, 0.35, 1.50], placements=[AssetInstance() for _ in range(1)])

carpet_A[0].instance_id = 'carpet_A_0'
decoration_A[0].instance_id = 'decoration_A_0'
seat_A[0].instance_id = 'seat_A_0'
cabinet[0].instance_id = 'cabinet_0'
decoration_B[0].instance_id = 'decoration_B_0'
candle[0].instance_id = 'candle_0'
dresser[0].instance_id = 'dresser_0'
casket[0].instance_id = 'casket_0'
seat_B[0].instance_id = 'seat_B_0'
decoration_C[0].instance_id = 'decoration_C_0'
decoration_D[0].instance_id = 'decoration_D_0'
vase[0].instance_id = 'vase_0'
bed[0].instance_id = 'bed_0'
mirror[0].instance_id = 'mirror_0'
carpet_B[0].instance_id = 'carpet_B_0'
pillow[0].instance_id = 'pillow_0'
case[0].instance_id = 'case_0'
globe[0].instance_id = 'globe_0'
lamp[0].instance_id = 'lamp_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

carpet_A[0].position = [2.9471445851656655, 1.2252577584297273, 0.01]
carpet_A[0].rotation = [0, 0, 0]
decoration_A[0].position = [2.8947277603652974, 1.5117012833677008, 0.4]
decoration_A[0].rotation = [0, 0, 0]
seat_A[0].position = [3.681857957945774, 2.4670646551997812, 0.425]
seat_A[0].rotation = [0, 0, 0]
cabinet[0].position = [1.7815635555441103, 4.288682430617075, 0.9]
cabinet[0].rotation = [0, 0, 0]
decoration_B[0].position = [1.6551230974524163, 0.46915006784070834, 0.16]
decoration_B[0].rotation = [0, 0, 0]
candle[0].position = [1.2790549580314865, 1.4939743250738498, 0.075]
candle[0].rotation = [0, 0, 0]
dresser[0].position = [1.172738348233762, 1.2504118475472743, 0.425]
dresser[0].rotation = [0, 0, 0]
casket[0].position = [2.3773343650809386, 1.6925157270114002, 0.06]
casket[0].rotation = [0, 0, 0]
seat_B[0].position = [2.178334352756879, 2.463533498225792, 0.425]
seat_B[0].rotation = [0, 0, 0]
decoration_C[0].position = [0.6857998836521552, 3.6476296859127304, 0.3]
decoration_C[0].rotation = [0, 0, 0]
decoration_D[0].position = [3.415065711759618, 0.03732941605323823, 0.125]
decoration_D[0].rotation = [0, 0, 0]
vase[0].position = [0.3220445481493193, 0.15082836042191794, 0.15]
vase[0].rotation = [0, 0, 0]
bed[0].position = [0.35393802744705427, 0.26841958196091137, 0.525]
bed[0].rotation = [0, 0, 0]
mirror[0].position = [1.0260399936862934, 0.24848088140398725, 0.5]
mirror[0].rotation = [0, 0, 0]
carpet_B[0].position = [0.5223042671647654, 2.026160461230386, 0.0075]
carpet_B[0].rotation = [0, 0, 0]
pillow[0].position = [1.443104252027624, 3.840940590743344, 0.075]
pillow[0].rotation = [0, 0, 0]
case[0].position = [0.38410523004721964, 2.173920673588432, 0.275]
case[0].rotation = [0, 0, 0]
globe[0].position = [0.22498685248959904, 2.3108295458505514, 0.2]
globe[0].rotation = [0, 0, 0]
lamp[0].position = [0.37581603097981847, 4.507281760798061, 0.75]
lamp[0].rotation = [0, 0, 0]
carpet_A[0].position = [2.9471445851656655, 1.2252577584297273, 0.01]
carpet_A[0].rotation = [0, 0, 0]
decoration_A[0].position = [2.8947277603652974, 1.5117012833677008, 0.4]
decoration_A[0].rotation = [0, 0, 0]
seat_A[0].position = [3.681857957945774, 2.4670646551997812, 0.425]
seat_A[0].rotation = [0, 0, 0]
cabinet[0].position = [1.7815635555441103, 4.288682430617075, 0.9]
cabinet[0].rotation = [0, 0, 0]
decoration_B[0].position = [1.6551230974524163, 0.46915006784070834, 0.16]
decoration_B[0].rotation = [0, 0, 0]
candle[0].position = [1.2790549580314865, 1.4939743250738498, 0.075]
candle[0].rotation = [0, 0, 0]
dresser[0].position = [1.172738348233762, 1.2504118475472743, 0.425]
dresser[0].rotation = [0, 0, 0]
casket[0].position = [2.3773343650809386, 1.6925157270114002, 0.06]
casket[0].rotation = [0, 0, 0]
seat_B[0].position = [2.178334352756879, 2.463533498225792, 0.425]
seat_B[0].rotation = [0, 0, 0]
decoration_C[0].position = [0.6857998836521552, 3.6476296859127304, 0.3]
decoration_C[0].rotation = [0, 0, 0]
decoration_D[0].position = [3.415065711759618, 0.03732941605323823, 0.125]
decoration_D[0].rotation = [0, 0, 0]
vase[0].position = [0.3220445481493193, 0.15082836042191794, 0.15]
vase[0].rotation = [0, 0, 0]
bed[0].position = [0.35393802744705427, 0.26841958196091137, 0.525]
bed[0].rotation = [0, 0, 0]
mirror[0].position = [1.0260399936862934, 0.24848088140398725, 0.5]
mirror[0].rotation = [0, 0, 0]
carpet_B[0].position = [0.5223042671647654, 2.026160461230386, 0.0075]
carpet_B[0].rotation = [0, 0, 0]
pillow[0].position = [1.443104252027624, 3.840940590743344, 0.075]
pillow[0].rotation = [0, 0, 0]
case[0].position = [0.38410523004721964, 2.173920673588432, 0.275]
case[0].rotation = [0, 0, 0]
globe[0].position = [0.22498685248959904, 2.3108295458505514, 0.2]
globe[0].rotation = [0, 0, 0]
lamp[0].position = [0.37581603097981847, 4.507281760798061, 0.75]
lamp[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange a bedroom with a seating group at the south end and a clear
# central approach to the bed. Coordinates follow the supplied boundary.
# The two seats flank the case, with all three facing into the room.
layout_specs = [
    (carpet_A,     [1.90, 1.30, 0.010],   0),
    (seat_A,       [0.85, 0.75, 0.445],  90),
    (case,         [1.85, 0.75, 0.295],  90),
    (seat_B,       [2.85, 0.75, 0.445],  90),
    (lamp,         [3.30, 1.90, 0.770], 180),

    # The bed's long axis runs north-south; its head is at the north wall.
    (bed,         [2.00, 3.79, 0.525], -90),
    (dresser,     [0.32, 3.75, 0.425],   0),
    (cabinet,     [3.51, 4.10, 0.900], 180),
    (carpet_B,     [0.85, 2.92, 0.005],   0),

    # Thin decorations are wall-mounted rather than left on the floor.
    (decoration_A,[0.083, 1.80, 1.60],    0),
    (decoration_C,[0.65, 4.82, 1.55],   -90),
    (mirror,      [3.74, 2.00, 1.55],   180),

    # Small items occupy distinct positions on their supporting surfaces.
    (decoration_B,[0.32, 4.10, 1.010],    0),
    (candle,      [0.32, 3.72, 0.925],    0),
    (casket,      [0.32, 3.40, 0.910],    0),
    (decoration_D,[1.85, 0.65, 0.695],   90),
    (vase,        [3.51, 3.88, 1.950],  180),
    (globe,       [3.51, 4.30, 2.000],  180),
    (pillow,      [2.00, 4.40, 1.125],  -90),
]

# Fixed reference constraints preserve the proposed zones, wall-art heights,
# and the exact seat–case–seat ordering. Each instance receives both a
# position constraint and an orientation constraint.
for asset_group, proposed_position, yaw_degrees in layout_specs:
    asset_group[0].position = proposed_position[:]
    asset_group[0].rotation = [0, 0, radians(yaw_degrees)]
    fixed_reference = AssetInstance(
        position=proposed_position[:],
        rotation=[0, 0, radians(yaw_degrees)]
    )
    solver.distance_constraint(
        asset_group[0], fixed_reference, 0, 0, weight=10
    )
    solver.align_with(asset_group[0], fixed_reference)

# Explicit supports prevent tabletop decorations and bedding from dropping
# to the floor. The south seating group stands on the thin area carpet.
solver.on_top_of(seat_A[0], carpet_A[0])
solver.on_top_of(case[0], carpet_A[0])
solver.on_top_of(seat_B[0], carpet_A[0])
solver.on_top_of(lamp[0], carpet_A[0])

solver.on_top_of(decoration_B[0], dresser[0])
solver.on_top_of(candle[0], dresser[0])
solver.on_top_of(casket[0], dresser[0])
solver.on_top_of(decoration_D[0], case[0])
solver.on_top_of(vase[0], cabinet[0])
solver.on_top_of(globe[0], cabinet[0])
solver.on_top_of(pillow[0], bed[0])

# Reinforce the principal wall relationships.
solver.against_wall(bed[0], walls[0])
solver.against_wall(cabinet[0], walls[3])
solver.against_wall(decoration_A[0], walls[1])
solver.against_wall(decoration_C[0], walls[0])
solver.against_wall(mirror[0], walls[3])

# Equal spacing and common orientation maintain the case between the seats.
# Distances include the difference in the bounding-box center heights.
seat_case_distance = (1.0**2 + (0.445 - 0.295)**2)**0.5
solver.distance_constraint(
    seat_A[0], case[0], seat_case_distance, seat_case_distance, weight=10
)
solver.distance_constraint(
    seat_B[0], case[0], seat_case_distance, seat_case_distance, weight=10
)
solver.distance_constraint(seat_A[0], seat_B[0], 2.0, 2.0, weight=10)
solver.align_with(seat_A[0], case[0])
solver.align_with(seat_B[0], case[0])
solver.align_with(pillow[0], bed[0])

# Maintain usable separation between the bed and the tall storage unit.
solver.distance_constraint(bed[0], cabinet[0], 1.55, None)

solver.constraints = []
case[0].position = [1.850000023841858, 0.75, 0.29500001668930054]
case[0].rotation = [0, 0, 1.5990706612064889]
case[0].optimize = 2
carpet_B[0].position = [0.8500000238418579, 2.9200000762939453, 0.004999999888241291]
carpet_B[0].rotation = [0, 0, 0.00942477746072377]
carpet_B[0].optimize = 2
casket[0].position = [0.3199999928474426, 3.4000000953674316, 0.9100000262260437]
casket[0].rotation = [0, 0, 0.01256637125682779]
casket[0].optimize = 2
decoration_B[0].position = [0.3199999928474426, 4.099999904632568, 1.0099999904632568]
decoration_B[0].rotation = [0, 0, 0.01256637125682779]
decoration_B[0].optimize = 2
cabinet[0].position = [3.5148398876190186, 4.099999904632568, 0.8999999761581421]
cabinet[0].rotation = [0, 0, -3.1415924455966286]
cabinet[0].optimize = 2
carpet_A[0].position = [1.899999976158142, 1.2999999523162842, 0.009999999776482582]
carpet_A[0].rotation = [0, 0, 0.021991148286022624]
carpet_A[0].optimize = 2
seat_B[0].position = [2.8600687980651855, 0.75, 0.445000022649765]
seat_B[0].rotation = [0, 0, 1.5990706800499639]
seat_B[0].optimize = 2
vase[0].position = [3.509999990463257, 3.880000114440918, 1.9499999284744263]
vase[0].rotation = [0, 0, -3.1290262823329655]
vase[0].optimize = 2
lamp[0].position = [3.299999952316284, 1.899999976158142, 0.7699999809265137]
lamp[0].rotation = [0, 0, -3.1290262823329655]
lamp[0].optimize = 2
bed[0].position = [1.94194757938385, 3.7872796058654785, 0.5249999761581421]
bed[0].rotation = [0, 0, -1.5707961520628835]
bed[0].optimize = 2
candle[0].position = [0.3199999928474426, 3.7200000286102295, 0.925000011920929]
candle[0].rotation = [0, 0, 0.01256637125682779]
candle[0].optimize = 2
dresser[0].position = [0.3199999928474426, 3.75, 0.42500001192092896]
dresser[0].rotation = [0, 0, 0.01884955539881635]
dresser[0].optimize = 2
pillow[0].position = [2.0, 4.400000095367432, 1.125]
pillow[0].rotation = [0, 0, -1.5707961732060691]
pillow[0].optimize = 2
mirror[0].position = [3.744839668273926, 2.0, 0.5]
mirror[0].rotation = [0, 0, -3.1415925098444277]
mirror[0].optimize = 2
decoration_C[0].position = [0.6499999761581421, 4.817280292510986, 0.30000001192092896]
decoration_C[0].rotation = [0, 0, -1.570796182665777]
decoration_C[0].optimize = 2
decoration_D[0].position = [1.850000023841858, 0.6499999761581421, 0.6950000524520874]
decoration_D[0].rotation = [0, 0, 1.5833626980517244]
decoration_D[0].optimize = 2
globe[0].position = [3.509999990463257, 4.300000190734863, 2.0]
globe[0].rotation = [0, 0, -3.1290262823329655]
globe[0].optimize = 2
seat_A[0].position = [0.8619009852409363, 0.75, 0.445000022649765]
seat_A[0].rotation = [0, 0, 1.5990706800499639]
seat_A[0].optimize = 2
decoration_A[0].position = [0.08292704075574875, 1.8035390377044678, 0.4000000059604645]
decoration_A[0].rotation = [0, 0, 0.020738077585296322]
decoration_A[0].optimize = 2

