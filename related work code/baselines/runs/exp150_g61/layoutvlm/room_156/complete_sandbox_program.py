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
    Wall(corner1=[6.00, 0.00, 0.00], corner2=[6.00, 7.00, 0.00]),
    Wall(corner1=[6.00, 7.00, 0.00], corner2=[0.00, 7.00, 0.00]),
    Wall(corner1=[0.00, 7.00, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
armchair_A = Assets(description="modern single armchair in light grey upholstery with wooden legs", size=[0.90, 0.85, 0.85], placements=[AssetInstance() for _ in range(1)])
side_table_A = Assets(description="round metal-framed side table with dark wooden top", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
armchair_B = Assets(description="modern single armchair in light grey upholstery with wooden legs", size=[0.90, 0.85, 0.85], placements=[AssetInstance() for _ in range(1)])
sectional_sofa = Assets(description="large l-shaped sectional sofa in dark blue fabric with deep seating", size=[2.20, 3.20, 0.85], placements=[AssetInstance() for _ in range(1)])
tv_stand = Assets(description="large low modern tv stand in dark wood finish with ample storage", size=[0.45, 2.00, 0.50], placements=[AssetInstance() for _ in range(1)])
console_table = Assets(description="narrow wooden console table with metal legs", size=[0.35, 1.20, 0.80], placements=[AssetInstance() for _ in range(1)])
plant_stand_A = Assets(description="wood and metal plant stand holding multiple pots", size=[0.40, 0.65, 1.10], placements=[AssetInstance() for _ in range(1)])
floor_lamp_A = Assets(description="tall modern floor lamp with adjustable arm and warm light", size=[0.40, 0.65, 1.75], placements=[AssetInstance() for _ in range(1)])
armchair_C = Assets(description="modern single armchair in light grey upholstery with wooden legs", size=[0.90, 0.85, 0.85], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="large rectangular wooden coffee table with lower shelf and glass top", size=[0.70, 1.30, 0.42], placements=[AssetInstance() for _ in range(1)])
side_table_B = Assets(description="round metal-framed side table with dark wooden top", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
plant_stand_B = Assets(description="wood and metal plant stand holding multiple pots", size=[0.40, 0.65, 1.10], placements=[AssetInstance() for _ in range(1)])
floor_lamp_B = Assets(description="tall modern floor lamp with adjustable arm and warm light", size=[0.40, 0.65, 1.75], placements=[AssetInstance() for _ in range(1)])
bookshelf_A = Assets(description="extra tall open bookshelf with multiple shelves in light wood finish", size=[0.35, 0.90, 2.20], placements=[AssetInstance() for _ in range(1)])
side_table_C = Assets(description="round metal-framed side table with dark wooden top", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
bookshelf_B = Assets(description="extra tall open bookshelf with multiple shelves in light wood finish", size=[0.35, 0.90, 2.20], placements=[AssetInstance() for _ in range(1)])

armchair_A[0].instance_id = 'armchair_A_0'
side_table_A[0].instance_id = 'side_table_A_0'
armchair_B[0].instance_id = 'armchair_B_0'
sectional_sofa[0].instance_id = 'sectional_sofa_0'
tv_stand[0].instance_id = 'tv_stand_0'
console_table[0].instance_id = 'console_table_0'
plant_stand_A[0].instance_id = 'plant_stand_A_0'
floor_lamp_A[0].instance_id = 'floor_lamp_A_0'
armchair_C[0].instance_id = 'armchair_C_0'
coffee_table[0].instance_id = 'coffee_table_0'
side_table_B[0].instance_id = 'side_table_B_0'
plant_stand_B[0].instance_id = 'plant_stand_B_0'
floor_lamp_B[0].instance_id = 'floor_lamp_B_0'
bookshelf_A[0].instance_id = 'bookshelf_A_0'
side_table_C[0].instance_id = 'side_table_C_0'
bookshelf_B[0].instance_id = 'bookshelf_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

armchair_A[0].position = [2.9767160528641385, 5.822250281279106, 0.425]
armchair_A[0].rotation = [0, 0, 0]
side_table_A[0].position = [3.005243551099618, 1.19453565489839, 0.275]
side_table_A[0].rotation = [0, 0, 0]
armchair_B[0].position = [3.6420160344955166, 3.7244116132950236, 0.425]
armchair_B[0].rotation = [0, 0, 0]
sectional_sofa[0].position = [4.816058558500248, 5.455577229989274, 0.425]
sectional_sofa[0].rotation = [0, 0, 0]
tv_stand[0].position = [5.068830723992617, 4.792301900597173, 0.25]
tv_stand[0].rotation = [0, 0, 0]
console_table[0].position = [5.706752529997326, 1.4273255880110143, 0.4]
console_table[0].rotation = [0, 0, 0]
plant_stand_A[0].position = [1.8496963101037303, 6.4183957981734965, 0.55]
plant_stand_A[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [2.729936548564572, 0.8439709151332732, 0.875]
floor_lamp_A[0].rotation = [0, 0, 0]
armchair_C[0].position = [1.2564947587291302, 0.050720412078103294, 0.425]
armchair_C[0].rotation = [0, 0, 0]
coffee_table[0].position = [5.567454116778936, 3.5274071942568224, 0.21]
coffee_table[0].rotation = [0, 0, 0]
side_table_B[0].position = [1.5126322512829276, 0.19483876678268108, 0.275]
side_table_B[0].rotation = [0, 0, 0]
plant_stand_B[0].position = [3.6172975005578802, 4.631140480049393, 0.55]
plant_stand_B[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [1.924226190673721, 0.7726493440895513, 0.875]
floor_lamp_B[0].rotation = [0, 0, 0]
bookshelf_A[0].position = [4.130630790127739, 1.6748121633892108, 1.1]
bookshelf_A[0].rotation = [0, 0, 0]
side_table_C[0].position = [2.263121973561175, 5.869803386745065, 0.275]
side_table_C[0].rotation = [0, 0, 0]
bookshelf_B[0].position = [5.935560528509968, 4.179506177698561, 1.1]
bookshelf_B[0].rotation = [0, 0, 0]
armchair_A[0].position = [2.9767160528641385, 5.822250281279106, 0.425]
armchair_A[0].rotation = [0, 0, 0]
side_table_A[0].position = [3.005243551099618, 1.19453565489839, 0.275]
side_table_A[0].rotation = [0, 0, 0]
armchair_B[0].position = [3.6420160344955166, 3.7244116132950236, 0.425]
armchair_B[0].rotation = [0, 0, 0]
sectional_sofa[0].position = [4.816058558500248, 5.455577229989274, 0.425]
sectional_sofa[0].rotation = [0, 0, 0]
tv_stand[0].position = [5.068830723992617, 4.792301900597173, 0.25]
tv_stand[0].rotation = [0, 0, 0]
console_table[0].position = [5.706752529997326, 1.4273255880110143, 0.4]
console_table[0].rotation = [0, 0, 0]
plant_stand_A[0].position = [1.8496963101037303, 6.4183957981734965, 0.55]
plant_stand_A[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [2.729936548564572, 0.8439709151332732, 0.875]
floor_lamp_A[0].rotation = [0, 0, 0]
armchair_C[0].position = [1.2564947587291302, 0.050720412078103294, 0.425]
armchair_C[0].rotation = [0, 0, 0]
coffee_table[0].position = [5.567454116778936, 3.5274071942568224, 0.21]
coffee_table[0].rotation = [0, 0, 0]
side_table_B[0].position = [1.5126322512829276, 0.19483876678268108, 0.275]
side_table_B[0].rotation = [0, 0, 0]
plant_stand_B[0].position = [3.6172975005578802, 4.631140480049393, 0.55]
plant_stand_B[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [1.924226190673721, 0.7726493440895513, 0.875]
floor_lamp_B[0].rotation = [0, 0, 0]
bookshelf_A[0].position = [4.130630790127739, 1.6748121633892108, 1.1]
bookshelf_A[0].rotation = [0, 0, 0]
side_table_C[0].position = [2.263121973561175, 5.869803386745065, 0.275]
side_table_C[0].rotation = [0, 0, 0]
bookshelf_B[0].position = [5.935560528509968, 4.179506177698561, 1.1]
bookshelf_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the supplied wall coordinates: the room occupies x=0..6, y=0..7.
# o0000 = armchair_A, o0002 = armchair_B, o0008 = armchair_C,
# and o0015 = bookshelf_B.
#
# The sofa and TV form a southern lounge. Three chairs occupy a northern
# row, with A exactly between B and C. Furniture near the perimeter leaves
# circulation space between the two seating zones.
layout_specs = [
    (armchair_A,     [3.00, 5.25, 0.425], -90),
    (side_table_A,   [2.15, 5.25, 0.275],   0),
    (armchair_B,     [1.30, 5.25, 0.425], -90),
    (sectional_sofa, [1.10, 2.30, 0.425],   0),
    (tv_stand,       [5.775, 2.30, 0.25], 180),
    (console_table,  [3.00, 6.825, 0.40], -90),
    (plant_stand_A,  [0.40, 6.40, 0.55],    0),
    (floor_lamp_A,   [0.40, 4.60, 0.875],   0),
    (armchair_C,     [4.70, 5.25, 0.425], -90),
    (coffee_table,   [3.25, 2.30, 0.21],    0),
    (side_table_B,   [3.85, 5.25, 0.275],   0),
    (plant_stand_B,  [5.60, 6.40, 0.55],  180),
    (floor_lamp_B,   [5.60, 4.50, 0.875], 180),
    (bookshelf_A,    [3.40, 0.175, 1.10],  90),
    (side_table_C,   [2.65, 3.70, 0.275],   0),
    (bookshelf_B,    [4.70, 0.175, 1.10],  90),
]

for asset_group, initial_position, yaw_degrees in layout_specs:
    asset_group[0].position = initial_position.copy()
    asset_group[0].rotation = [0, 0, radians(yaw_degrees)]

# Apply the explicitly requested relationships first.
# The console's rotated footprint is 1.20 m wide and 0.35 m deep.
solver.against_wall(console_table[0], walls[1])
solver.point_towards(armchair_C[0], bookshelf_B[0])

# Equal adjacent distances and the full endpoint distance maintain the
# collinear chair ordering C -- A -- B, with A at the midpoint.
solver.distance_constraint(armchair_A[0], armchair_C[0], 1.70, 1.70, weight=10)
solver.distance_constraint(armchair_A[0], armchair_B[0], 1.70, 1.70, weight=10)
solver.distance_constraint(armchair_B[0], armchair_C[0], 3.40, 3.40, weight=10)

# Back the large perimeter pieces against their respective walls.
solver.against_wall(sectional_sofa[0], walls[2])
solver.against_wall(tv_stand[0], walls[0])
solver.against_wall(bookshelf_A[0], walls[3])
solver.against_wall(bookshelf_B[0], walls[3])

# Fixed center references preserve the planned clearances and prevent
# unconstrained drift. Every asset receives a position constraint and an
# orientation constraint; the bookshelf-facing chair uses point_towards.
for asset_group, initial_position, yaw_degrees in layout_specs:
    layout_reference = AssetInstance(
        position=initial_position.copy(),
        rotation=[0, 0, radians(yaw_degrees)],
    )
    solver.distance_constraint(
        asset_group[0], layout_reference, 0.0, 0.0, weight=10
    )
    if asset_group is not armchair_C:
        solver.align_with(asset_group[0], layout_reference)

# Additional functional relationships: the sofa faces the TV cabinet,
# and the tables remain conveniently close to their associated seating.
solver.point_towards(sectional_sofa[0], tv_stand[0])
solver.point_towards(tv_stand[0], sectional_sofa[0])

solver.distance_constraint(coffee_table[0], sectional_sofa[0], 2.05, 2.30)
solver.align_with(coffee_table[0], sectional_sofa[0])

solver.distance_constraint(side_table_A[0], armchair_B[0], 0.80, 0.95)
solver.distance_constraint(side_table_A[0], armchair_A[0], 0.80, 0.95)
solver.distance_constraint(side_table_B[0], armchair_A[0], 0.80, 0.95)
solver.distance_constraint(side_table_B[0], armchair_C[0], 0.80, 0.95)
solver.distance_constraint(side_table_C[0], sectional_sofa[0], 2.00, 2.25)

# All listed assets are floor-standing, including the plant stands and
# side tables; no tabletop accessories require an on_top_of constraint.

solver.constraints = []
floor_lamp_A[0].position = [0.4000000059604645, 4.599999904632568, 0.875]
floor_lamp_A[0].rotation = [0, 0, 0.00942477746072377]
floor_lamp_A[0].optimize = 2
armchair_C[0].position = [4.699999809265137, 5.25, 0.42500001192092896]
armchair_C[0].rotation = [0, 0, -1.5519467713960802]
armchair_C[0].optimize = 2
plant_stand_A[0].position = [0.4000000059604645, 6.400000095367432, 0.550000011920929]
plant_stand_A[0].rotation = [0, 0, 0.00942477746072377]
plant_stand_A[0].optimize = 2
side_table_B[0].position = [3.8499999046325684, 5.25, 0.2750000059604645]
side_table_B[0].rotation = [0, 0, 0.0157079639172164]
side_table_B[0].optimize = 2
plant_stand_B[0].position = [5.599999904632568, 6.400000095367432, 0.550000011920929]
plant_stand_B[0].rotation = [0, 0, -3.1321678761290697]
plant_stand_B[0].optimize = 2
armchair_B[0].position = [1.2999999523162842, 5.25, 0.42500001192092896]
armchair_B[0].rotation = [0, 0, -1.5519467713960802]
armchair_B[0].optimize = 2
sectional_sofa[0].position = [1.100000023841858, 2.299999952316284, 0.42500001192092896]
sectional_sofa[0].rotation = [0, 0, 1.9787041305268464e-08]
sectional_sofa[0].optimize = 2
side_table_A[0].position = [2.1500000953674316, 5.25, 0.2750000059604645]
side_table_A[0].rotation = [0, 0, 0.0157079639172164]
side_table_A[0].optimize = 2
side_table_C[0].position = [2.6500000953674316, 3.700000047683716, 0.2750000059604645]
side_table_C[0].rotation = [0, 0, 0.01256637125682779]
side_table_C[0].optimize = 2
floor_lamp_B[0].position = [5.599999904632568, 4.5, 0.875]
floor_lamp_B[0].rotation = [0, 0, -3.1321678761290697]
floor_lamp_B[0].optimize = 2
bookshelf_A[0].position = [3.4000000953674316, 0.17499999701976776, 1.100000023841858]
bookshelf_A[0].rotation = [0, 0, 1.5707963678486037]
bookshelf_A[0].optimize = 2
coffee_table[0].position = [3.25, 2.299999952316284, 0.20999999344348907]
coffee_table[0].rotation = [0, 0, 2.9127155265342682e-08]
coffee_table[0].optimize = 2
armchair_A[0].position = [3.0, 5.25, 0.42500001192092896]
armchair_A[0].rotation = [0, 0, -1.548805178508874]
armchair_A[0].optimize = 2
bookshelf_B[0].position = [4.699999809265137, 0.17499999701976776, 1.100000023841858]
bookshelf_B[0].rotation = [0, 0, 1.5707963678384897]
bookshelf_B[0].optimize = 2
tv_stand[0].position = [5.775000095367432, 2.299999952316284, 0.25]
tv_stand[0].rotation = [0, 0, -3.1415926098324864]
tv_stand[0].optimize = 2
console_table[0].position = [3.0, 6.825000286102295, 0.4000000059604645]
console_table[0].rotation = [0, 0, -1.570796283083111]
console_table[0].optimize = 2

