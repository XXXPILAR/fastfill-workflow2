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
    Wall(corner1=[2.94, 5.79, 0.00], corner2=[1.46, 5.79, 0.00]),
    Wall(corner1=[1.46, 5.79, 0.00], corner2=[1.46, 7.47, 0.00]),
    Wall(corner1=[1.46, 7.47, 0.00], corner2=[0.00, 7.47, 0.00]),
    Wall(corner1=[0.00, 7.47, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.94, 0.00, 0.00]),
    Wall(corner1=[2.94, 0.00, 0.00], corner2=[2.94, 3.45, 0.00]),
    Wall(corner1=[2.94, 3.45, 0.00], corner2=[5.65, 3.45, 0.00]),
    Wall(corner1=[5.65, 3.45, 0.00], corner2=[5.65, 4.49, 0.00]),
    Wall(corner1=[5.65, 4.49, 0.00], corner2=[2.94, 4.49, 0.00]),
    Wall(corner1=[2.94, 4.49, 0.00], corner2=[2.94, 5.79, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
sofa = Assets(description="sofa", size=[0.95, 2.40, 0.85], placements=[AssetInstance() for _ in range(1)])
side_table = Assets(description="side table", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
ornaments_A = Assets(description="ornaments", size=[0.16, 0.18, 0.28], placements=[AssetInstance() for _ in range(1)])
ornaments_B = Assets(description="ornaments", size=[0.12, 0.30, 0.22], placements=[AssetInstance() for _ in range(1)])
ornaments_C = Assets(description="ornaments", size=[0.20, 0.20, 0.32], placements=[AssetInstance() for _ in range(1)])
tv_cabinet = Assets(description="tv cabinet", size=[0.42, 1.80, 0.50], placements=[AssetInstance() for _ in range(1)])
sideboard = Assets(description="sideboard", size=[0.45, 1.60, 0.85], placements=[AssetInstance() for _ in range(1)])
flowers_A = Assets(description="flowers", size=[0.35, 0.35, 0.50], placements=[AssetInstance() for _ in range(1)])
flowers_B = Assets(description="flowers", size=[0.25, 0.25, 0.35], placements=[AssetInstance() for _ in range(1)])
flowers_C = Assets(description="flowers", size=[0.40, 0.40, 0.55], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[2.00, 2.80, 0.01], placements=[AssetInstance() for _ in range(1)])
stool = Assets(description="stool", size=[0.45, 0.45, 0.45], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="coffee table", size=[0.65, 1.20, 0.42], placements=[AssetInstance() for _ in range(1)])
floor_standing_lamp = Assets(description="floor standing lamp", size=[0.40, 0.40, 1.65], placements=[AssetInstance() for _ in range(1)])
ornaments_D = Assets(description="ornaments", size=[0.15, 0.25, 0.20], placements=[AssetInstance() for _ in range(1)])
dining_table = Assets(description="dining table", size=[0.85, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])

sofa[0].instance_id = 'sofa_0'
side_table[0].instance_id = 'side_table_0'
ornaments_A[0].instance_id = 'ornaments_A_0'
ornaments_B[0].instance_id = 'ornaments_B_0'
ornaments_C[0].instance_id = 'ornaments_C_0'
tv_cabinet[0].instance_id = 'tv_cabinet_0'
sideboard[0].instance_id = 'sideboard_0'
flowers_A[0].instance_id = 'flowers_A_0'
flowers_B[0].instance_id = 'flowers_B_0'
flowers_C[0].instance_id = 'flowers_C_0'
carpet[0].instance_id = 'carpet_0'
stool[0].instance_id = 'stool_0'
coffee_table[0].instance_id = 'coffee_table_0'
floor_standing_lamp[0].instance_id = 'floor_standing_lamp_0'
ornaments_D[0].instance_id = 'ornaments_D_0'
dining_table[0].instance_id = 'dining_table_0'
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

sofa[0].position = [5.374055952117537, 4.191279037416981, 0.425]
sofa[0].rotation = [0, 0, 0]
side_table[0].position = [2.55321308863466, 3.2137877836830997, 0.275]
side_table[0].rotation = [0, 0, 0]
ornaments_A[0].position = [0.14733158171014687, 1.763538713298441, 0.14]
ornaments_A[0].rotation = [0, 0, 0]
ornaments_B[0].position = [2.3218036404386835, 3.805993742977, 0.11]
ornaments_B[0].rotation = [0, 0, 0]
ornaments_C[0].position = [2.6782318521001693, 4.903259986318861, 0.16]
ornaments_C[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [1.5105453383387855, 4.770381801784232, 0.25]
tv_cabinet[0].rotation = [0, 0, 0]
sideboard[0].position = [0.6924080637097775, 4.864457719829939, 0.425]
sideboard[0].rotation = [0, 0, 0]
flowers_A[0].position = [0.2828743464378514, 5.919341345996121, 0.25]
flowers_A[0].rotation = [0, 0, 0]
flowers_B[0].position = [3.392768957398207, 4.385038373962992, 0.175]
flowers_B[0].rotation = [0, 0, 0]
flowers_C[0].position = [0.13737245112660673, 7.298688694414964, 0.275]
flowers_C[0].rotation = [0, 0, 0]
carpet[0].position = [0.7076264651439612, 4.838829974935076, 0.0075]
carpet[0].rotation = [0, 0, 0]
stool[0].position = [1.823380449104122, 3.5950685000045874, 0.225]
stool[0].rotation = [0, 0, 0]
coffee_table[0].position = [0.5557541374246853, 2.359705219530704, 0.21]
coffee_table[0].rotation = [0, 0, 0]
floor_standing_lamp[0].position = [0.24416446108902884, 1.6260637530254476, 0.825]
floor_standing_lamp[0].rotation = [0, 0, 0]
ornaments_D[0].position = [0.26433357528313023, 6.350187174150206, 0.1]
ornaments_D[0].rotation = [0, 0, 0]
dining_table[0].position = [1.2775603158070845, 6.909166948637647, 0.375]
dining_table[0].rotation = [0, 0, 0]
sofa[0].position = [5.374055952117537, 4.191279037416981, 0.425]
sofa[0].rotation = [0, 0, 0]
side_table[0].position = [2.55321308863466, 3.2137877836830997, 0.275]
side_table[0].rotation = [0, 0, 0]
ornaments_A[0].position = [0.14733158171014687, 1.763538713298441, 0.14]
ornaments_A[0].rotation = [0, 0, 0]
ornaments_B[0].position = [2.3218036404386835, 3.805993742977, 0.11]
ornaments_B[0].rotation = [0, 0, 0]
ornaments_C[0].position = [2.6782318521001693, 4.903259986318861, 0.16]
ornaments_C[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [1.5105453383387855, 4.770381801784232, 0.25]
tv_cabinet[0].rotation = [0, 0, 0]
sideboard[0].position = [0.6924080637097775, 4.864457719829939, 0.425]
sideboard[0].rotation = [0, 0, 0]
flowers_A[0].position = [0.2828743464378514, 5.919341345996121, 0.25]
flowers_A[0].rotation = [0, 0, 0]
flowers_B[0].position = [3.392768957398207, 4.385038373962992, 0.175]
flowers_B[0].rotation = [0, 0, 0]
flowers_C[0].position = [0.13737245112660673, 7.298688694414964, 0.275]
flowers_C[0].rotation = [0, 0, 0]
carpet[0].position = [0.7076264651439612, 4.838829974935076, 0.0075]
carpet[0].rotation = [0, 0, 0]
stool[0].position = [1.823380449104122, 3.5950685000045874, 0.225]
stool[0].rotation = [0, 0, 0]
coffee_table[0].position = [0.5557541374246853, 2.359705219530704, 0.21]
coffee_table[0].rotation = [0, 0, 0]
floor_standing_lamp[0].position = [0.24416446108902884, 1.6260637530254476, 0.825]
floor_standing_lamp[0].rotation = [0, 0, 0]
ornaments_D[0].position = [0.26433357528313023, 6.350187174150206, 0.1]
ornaments_D[0].rotation = [0, 0, 0]
dining_table[0].position = [1.2775603158070845, 6.909166948637647, 0.375]
dining_table[0].rotation = [0, 0, 0]

solver.constraints = []

# Keep the eastward corridor (x > 2.94) completely empty.
# Arrange seating along the west wall, leaving the southern entrances clear.
# The northern alcove and its two door approaches remain unfurnished.
# Coordinates below use the supplied floor-plan coordinates, not a recentered plan.

layout_specs = [
    (sofa,                [0.475, 2.80, 0.435],   0),
    (side_table,          [0.350, 1.30, 0.275],   0),
    (tv_cabinet,          [2.730, 2.45, 0.250], 180),
    (sideboard,           [0.225, 5.30, 0.425],   0),
    (carpet,              [1.000, 2.80, 0.005],   0),
    (stool,               [1.700, 3.95, 0.235], -90),
    (coffee_table,        [1.650, 2.80, 0.220],   0),
    (floor_standing_lamp, [0.550, 4.25, 0.825],   0),
    (dining_table,        [1.750, 5.05, 0.375],  90),

    # Small objects are distributed across separate supporting surfaces.
    (ornaments_A,        [0.350, 1.30, 0.690],   0),
    (ornaments_B,        [2.730, 2.00, 0.610], 180),
    (ornaments_C,        [0.225, 4.90, 1.010],   0),
    (flowers_A,          [0.225, 5.70, 1.100],   0),
    (flowers_B,          [2.250, 5.05, 0.925],  90),
    (flowers_C,          [1.250, 5.05, 1.025],  90),
    (ornaments_D,        [1.650, 2.80, 0.530],   0),
]

# Position anchors preserve clear door approaches and the separation between
# furniture groups. They are fixed references, not additional scene objects.
for asset_group, planned_position, yaw_degrees in layout_specs:
    asset_group[0].position = list(planned_position)
    asset_group[0].rotation = [0, 0, radians(yaw_degrees)]
    solver.distance_constraint(
        asset_group[0],
        AssetInstance(position=list(planned_position)),
        0.0, 0.0,
        weight=10,
    )

# Main furniture: orient every instance and preserve useful wall relationships.
solver.against_wall(sofa[0], walls[3])
solver.point_towards(sofa[0], coffee_table[0])

solver.against_wall(tv_cabinet[0], walls[5])
solver.point_towards(tv_cabinet[0], sofa[0])

solver.against_wall(sideboard[0], walls[3])
solver.align_with(sideboard[0], sofa[0])

solver.align_with(side_table[0], sofa[0])
solver.align_with(carpet[0], sofa[0])
solver.align_with(coffee_table[0], sofa[0])
solver.point_towards(stool[0], coffee_table[0])
solver.align_with(dining_table[0], sofa[0], angle=90)
solver.align_with(floor_standing_lamp[0], sofa[0])

# The lamp's footprint is 0.05 m beyond the sofa's north end.
# These are bounding-box CENTER distances, including the height difference;
# a 0.10 m center-distance constraint would incorrectly force an overlap.
lamp_sofa_center_distance = sum(
    (floor_standing_lamp[0].position[axis] - sofa[0].position[axis]) ** 2
    for axis in range(3)
) ** 0.5
solver.distance_constraint(
    floor_standing_lamp[0], sofa[0],
    lamp_sofa_center_distance, lamp_sofa_center_distance,
    weight=10,
)

# The carpet deliberately lies beneath the seating furniture. Raise supported
# furniture by its thickness rather than allowing solid geometry to intersect.
solver.on_top_of(sofa[0], carpet[0])
solver.on_top_of(coffee_table[0], carpet[0])
solver.on_top_of(stool[0], carpet[0])

# Preserve a usable sofa-to-coffee-table gap and the adjacent side table.
solver.distance_constraint(
    coffee_table[0], sofa[0], 1.15, 1.25, weight=10
)
solver.distance_constraint(
    side_table[0], sofa[0], 1.45, 1.60
)

# Each decorative item has an explicit support, orientation, and the position
# constraint registered above. Their footprints are separated on each surface.
supported_items = [
    (ornaments_A, side_table),
    (ornaments_B, tv_cabinet),
    (ornaments_C, sideboard),
    (flowers_A, sideboard),
    (flowers_B, dining_table),
    (flowers_C, dining_table),
    (ornaments_D, coffee_table),
]

for decoration_group, support_group in supported_items:
    solver.on_top_of(decoration_group[0], support_group[0])
    solver.align_with(decoration_group[0], support_group[0])

solver.constraints = []
flowers_C[0].position = [1.25, 5.050000190734863, 1.024999976158142]
flowers_C[0].rotation = [0, 0, 1.560869400230672]
flowers_C[0].optimize = 2
side_table[0].position = [0.3499999940395355, 1.2999999523162842, 0.2750000059604645]
side_table[0].rotation = [0, 0, 0.01765094614714067]
side_table[0].optimize = 2
floor_standing_lamp[0].position = [0.5550262928009033, 4.297124862670898, 0.824999988079071]
floor_standing_lamp[0].rotation = [0, 0, 0.014728330518320306]
floor_standing_lamp[0].optimize = 2
ornaments_A[0].position = [0.3499999940395355, 1.2999999523162842, 0.6899999976158142]
ornaments_A[0].rotation = [0, 0, 0.00139181772222299]
ornaments_A[0].optimize = 2
ornaments_D[0].position = [1.649999976158142, 2.799999952316284, 0.5300000309944153]
ornaments_D[0].rotation = [0, 0, -0.019297724190722194]
ornaments_D[0].optimize = 2
sofa[0].position = [0.48094338178634644, 2.799999952316284, 0.4350000023841858]
sofa[0].rotation = [0, 0, 0.0022940941951586917]
sofa[0].optimize = 2
flowers_B[0].position = [2.25, 5.050000190734863, 0.925000011920929]
flowers_B[0].rotation = [0, 0, 1.560869400230672]
flowers_B[0].optimize = 2
ornaments_B[0].position = [2.7300000190734863, 2.0, 0.6100000143051147]
ornaments_B[0].rotation = [0, 0, 3.133770864866889]
ornaments_B[0].optimize = 2
stool[0].position = [1.7000000476837158, 3.950000047683716, 0.23499999940395355]
stool[0].rotation = [0, 0, -1.5582299555380688]
stool[0].optimize = 2
tv_cabinet[0].position = [2.734805107116699, 2.450000047683716, 0.25]
tv_cabinet[0].rotation = [0, 0, -3.1391733199673415]
tv_cabinet[0].optimize = 2
coffee_table[0].position = [1.6766984462738037, 2.799999952316284, 0.2199999988079071]
coffee_table[0].rotation = [0, 0, 0.02189016877602557]
coffee_table[0].optimize = 2
flowers_A[0].position = [0.22499999403953552, 5.699999809265137, 1.100000023841858]
flowers_A[0].rotation = [0, 0, -0.0008935683570984736]
flowers_A[0].optimize = 2
carpet[0].position = [1.0403600931167603, 2.799999952316284, 0.004999999888241291]
carpet[0].rotation = [0, 0, 0.01765094614714067]
carpet[0].optimize = 2
dining_table[0].position = [1.75, 5.050000190734863, 0.375]
dining_table[0].rotation = [0, 0, 1.589912814081729]
dining_table[0].optimize = 2
sideboard[0].position = [0.2272716909646988, 5.300000190734863, 0.42500001192092896]
sideboard[0].rotation = [0, 0, 0.00017700400157291403]
sideboard[0].optimize = 2
ornaments_C[0].position = [0.22499999403953552, 4.900000095367432, 1.0099999904632568]
ornaments_C[0].rotation = [0, 0, -0.0008935683570984736]
ornaments_C[0].optimize = 2

