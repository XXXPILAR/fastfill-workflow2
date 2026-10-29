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
    Wall(corner1=[1.87, 7.32, 0.00], corner2=[1.87, 7.98, 0.00]),
    Wall(corner1=[1.87, 7.98, 0.00], corner2=[0.00, 7.98, 0.00]),
    Wall(corner1=[0.00, 7.98, 0.00], corner2=[0.00, 6.69, 0.00]),
    Wall(corner1=[0.00, 6.69, 0.00], corner2=[5.52, 6.69, 0.00]),
    Wall(corner1=[5.52, 6.69, 0.00], corner2=[5.52, 0.00, 0.00]),
    Wall(corner1=[5.52, 0.00, 0.00], corner2=[9.40, 0.00, 0.00]),
    Wall(corner1=[9.40, 0.00, 0.00], corner2=[9.40, 7.98, 0.00]),
    Wall(corner1=[9.40, 7.98, 0.00], corner2=[2.11, 7.98, 0.00]),
    Wall(corner1=[2.11, 7.98, 0.00], corner2=[2.11, 7.32, 0.00]),
    Wall(corner1=[2.11, 7.32, 0.00], corner2=[1.87, 7.32, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
ornaments_A = Assets(description="ornaments", size=[0.18, 0.25, 0.32], placements=[AssetInstance() for _ in range(1)])
bookcase_A = Assets(description="bookcase", size=[0.35, 1.20, 2.10], placements=[AssetInstance() for _ in range(1)])
bookcase_B = Assets(description="bookcase", size=[0.35, 1.20, 2.10], placements=[AssetInstance() for _ in range(1)])
potted_bonsai = Assets(description="potted bonsai", size=[0.35, 0.45, 0.50], placements=[AssetInstance() for _ in range(1)])
dining_table = Assets(description="dining table", size=[0.90, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
dining_chair_A = Assets(description="dining chair", size=[0.55, 0.48, 0.88], placements=[AssetInstance() for _ in range(1)])
dining_chair_B = Assets(description="dining chair", size=[0.55, 0.48, 0.88], placements=[AssetInstance() for _ in range(1)])
dining_chair_C = Assets(description="dining chair", size=[0.55, 0.48, 0.88], placements=[AssetInstance() for _ in range(1)])
dining_chair_D = Assets(description="dining chair", size=[0.55, 0.48, 0.88], placements=[AssetInstance() for _ in range(1)])
sofa = Assets(description="sofa", size=[0.95, 2.40, 0.85], placements=[AssetInstance() for _ in range(1)])
air_conditioner = Assets(description="air conditioner", size=[0.23, 0.95, 0.32], placements=[AssetInstance() for _ in range(1)])
plants = Assets(description="plants", size=[0.65, 0.65, 1.40], placements=[AssetInstance() for _ in range(1)])
washing_machine = Assets(description="washing machine", size=[0.65, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
ornaments_B = Assets(description="ornaments", size=[0.20, 0.30, 0.25], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="coffee table", size=[0.65, 1.20, 0.42], placements=[AssetInstance() for _ in range(1)])
washing_cabinet = Assets(description="washing cabinet", size=[0.65, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])

ornaments_A[0].instance_id = 'ornaments_A_0'
bookcase_A[0].instance_id = 'bookcase_A_0'
bookcase_B[0].instance_id = 'bookcase_B_0'
potted_bonsai[0].instance_id = 'potted_bonsai_0'
dining_table[0].instance_id = 'dining_table_0'
dining_chair_A[0].instance_id = 'dining_chair_A_0'
dining_chair_B[0].instance_id = 'dining_chair_B_0'
dining_chair_C[0].instance_id = 'dining_chair_C_0'
dining_chair_D[0].instance_id = 'dining_chair_D_0'
sofa[0].instance_id = 'sofa_0'
air_conditioner[0].instance_id = 'air_conditioner_0'
plants[0].instance_id = 'plants_0'
washing_machine[0].instance_id = 'washing_machine_0'
ornaments_B[0].instance_id = 'ornaments_B_0'
coffee_table[0].instance_id = 'coffee_table_0'
washing_cabinet[0].instance_id = 'washing_cabinet_0'
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

ornaments_A[0].position = [9.18989543787281, 0.6388804528918782, 0.16]
ornaments_A[0].rotation = [0, 0, 0]
bookcase_A[0].position = [7.801652869950775, 1.1326807109866976, 1.05]
bookcase_A[0].rotation = [0, 0, 0]
bookcase_B[0].position = [7.67844326916517, 7.92908437502688, 1.05]
bookcase_B[0].rotation = [0, 0, 0]
potted_bonsai[0].position = [7.559563664378765, 2.2291792586316954, 0.25]
potted_bonsai[0].rotation = [0, 0, 0]
dining_table[0].position = [7.575332286560916, 6.8725989106057925, 0.375]
dining_table[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [5.8201543150196615, 2.3959601184378476, 0.44]
dining_chair_A[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [6.372773552039862, 1.864388022063783, 0.44]
dining_chair_B[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [8.835884483952166, 6.6644654154496505, 0.44]
dining_chair_C[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [3.168746034565118, 7.139270537684956, 0.44]
dining_chair_D[0].rotation = [0, 0, 0]
sofa[0].position = [8.706398286325493, 6.191617075704981, 0.425]
sofa[0].rotation = [0, 0, 0]
air_conditioner[0].position = [1.6367486978066734, 7.317796570080176, 0.16]
air_conditioner[0].rotation = [0, 0, 0]
plants[0].position = [7.109600497949675, 0.1322639953929699, 0.7]
plants[0].rotation = [0, 0, 0]
washing_machine[0].position = [8.186617090657904, 1.6259821544710447, 0.425]
washing_machine[0].rotation = [0, 0, 0]
ornaments_B[0].position = [8.883407309186074, 2.136656279213394, 0.125]
ornaments_B[0].rotation = [0, 0, 0]
coffee_table[0].position = [3.350085599833772, 7.564451647817016, 0.21]
coffee_table[0].rotation = [0, 0, 0]
washing_cabinet[0].position = [2.392809023754558, 7.910923940242913, 0.45]
washing_cabinet[0].rotation = [0, 0, 0]
ornaments_A[0].position = [9.18989543787281, 0.6388804528918782, 0.16]
ornaments_A[0].rotation = [0, 0, 0]
bookcase_A[0].position = [7.801652869950775, 1.1326807109866976, 1.05]
bookcase_A[0].rotation = [0, 0, 0]
bookcase_B[0].position = [7.67844326916517, 7.92908437502688, 1.05]
bookcase_B[0].rotation = [0, 0, 0]
potted_bonsai[0].position = [7.559563664378765, 2.2291792586316954, 0.25]
potted_bonsai[0].rotation = [0, 0, 0]
dining_table[0].position = [7.575332286560916, 6.8725989106057925, 0.375]
dining_table[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [5.8201543150196615, 2.3959601184378476, 0.44]
dining_chair_A[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [6.372773552039862, 1.864388022063783, 0.44]
dining_chair_B[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [8.835884483952166, 6.6644654154496505, 0.44]
dining_chair_C[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [3.168746034565118, 7.139270537684956, 0.44]
dining_chair_D[0].rotation = [0, 0, 0]
sofa[0].position = [8.706398286325493, 6.191617075704981, 0.425]
sofa[0].rotation = [0, 0, 0]
air_conditioner[0].position = [1.6367486978066734, 7.317796570080176, 0.16]
air_conditioner[0].rotation = [0, 0, 0]
plants[0].position = [7.109600497949675, 0.1322639953929699, 0.7]
plants[0].rotation = [0, 0, 0]
washing_machine[0].position = [8.186617090657904, 1.6259821544710447, 0.425]
washing_machine[0].rotation = [0, 0, 0]
ornaments_B[0].position = [8.883407309186074, 2.136656279213394, 0.125]
ornaments_B[0].rotation = [0, 0, 0]
coffee_table[0].position = [3.350085599833772, 7.564451647817016, 0.21]
coffee_table[0].rotation = [0, 0, 0]
washing_cabinet[0].position = [2.392809023754558, 7.910923940242913, 0.45]
washing_cabinet[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the broad eastern part of the L-shaped room for furniture.
# Keep the narrow northern passage and both southern door approaches clear.
# Coordinates are bounding-box centers; rotations describe the front (+x locally).
layout_specs = [
    (bookcase_A,       [6.25, 7.805, 1.05], -90),
    (bookcase_B,       [8.50, 7.805, 1.05], -90),
    (dining_table,     [7.30, 5.70, 0.375],  90),
    # A (o0005) faces the coffee table, as requested.
    (dining_chair_A,   [7.30, 4.65, 0.44],  -90),
    (dining_chair_B,   [6.15, 5.70, 0.44],    0),
    # C (o0007) is opposite A, with the dining table between them.
    (dining_chair_C,   [7.30, 6.75, 0.44],  -90),
    (dining_chair_D,   [8.45, 5.70, 0.44],  180),
    (sofa,            [8.925, 3.25, 0.425], 180),
    (coffee_table,    [7.30, 3.25, 0.21],     0),
    (plants,          [8.90, 6.95, 0.70],   180),
    # Laundry appliances occupy the western edge without covering its window.
    (washing_machine, [5.845, 0.40, 0.425],   0),
    (washing_cabinet, [5.845, 2.95, 0.45],    0),
    # Wall-mounted above the sofa, not resting on it.
    (air_conditioner, [9.285, 3.25, 2.50],  180),
    # Small objects rest on usable surfaces, with clear footprint separation.
    (ornaments_A,     [5.845, 2.95, 1.06],    0),
    (potted_bonsai,   [7.30, 5.70, 1.00],    0),
    (ornaments_B,     [7.30, 3.50, 0.545],    0),
]

for asset_group, center_xyz, yaw_degrees in layout_specs:
    asset_group[0].position = list(center_xyz)
    asset_group[0].rotation = [0, 0, radians(yaw_degrees)]

# Establish the primary architectural and support relationships first.
# Both bookcases face into the room from the northern wall.
solver.against_wall(bookcase_A[0], walls[7])
solver.against_wall(bookcase_B[0], walls[7])
solver.against_wall(sofa[0], walls[6])
solver.against_wall(air_conditioner[0], walls[6])
solver.against_wall(washing_machine[0], walls[4])
solver.against_wall(washing_cabinet[0], walls[4])

solver.on_top_of(ornaments_A[0], washing_cabinet[0])
solver.on_top_of(potted_bonsai[0], dining_table[0])
solver.on_top_of(ornaments_B[0], coffee_table[0])

# Preserve the requested facing direction before other orientation constraints.
solver.point_towards(dining_chair_A[0], coffee_table[0])
solver.point_towards(dining_chair_C[0], dining_table[0])
solver.point_towards(dining_chair_B[0], dining_table[0])
solver.point_towards(dining_chair_D[0], dining_table[0])
solver.point_towards(sofa[0], coffee_table[0])

# Every instance receives a position constraint and an orientation constraint.
# Tight positional neighborhoods preserve the nonoverlapping layout and keep
# furniture out of the door approaches. Matching-height anchors also preserve
# mounting/support elevations.
for asset_group, center_xyz, yaw_degrees in layout_specs:
    solver.distance_constraint(
        asset_group[0],
        AssetInstance(position=list(center_xyz)),
        0.0, 0.02,
        weight=10,
    )
    solver.align_with(
        asset_group[0],
        AssetInstance(
            position=list(center_xyz),
            rotation=[0, 0, radians(yaw_degrees)],
        ),
        angle=0,
    )

# Reinforce the dining arrangement using actual 3D center distances.
# Equal opposing offsets keep the table between chairs A and C.
dining_end_distance = (1.05**2 + (0.44 - 0.375)**2)**0.5
dining_side_distance = (1.15**2 + (0.44 - 0.375)**2)**0.5

solver.distance_constraint(
    dining_chair_A[0], dining_table[0],
    dining_end_distance - 0.02, dining_end_distance + 0.02, weight=10,
)
solver.distance_constraint(
    dining_chair_C[0], dining_table[0],
    dining_end_distance - 0.02, dining_end_distance + 0.02, weight=10,
)
solver.distance_constraint(
    dining_chair_B[0], dining_table[0],
    dining_side_distance - 0.02, dining_side_distance + 0.02,
)
solver.distance_constraint(
    dining_chair_D[0], dining_table[0],
    dining_side_distance - 0.02, dining_side_distance + 0.02,
)
solver.distance_constraint(
    dining_chair_A[0], dining_chair_C[0], 2.08, 2.12, weight=10,
)

# The coffee table leaves approximately 0.82 m between its edge and the sofa.
living_center_distance = (1.625**2 + (0.425 - 0.21)**2)**0.5
solver.distance_constraint(
    coffee_table[0], sofa[0],
    living_center_distance - 0.02, living_center_distance + 0.02,
)

# Keep decorations aligned with their supporting furniture.
solver.align_with(ornaments_A[0], washing_cabinet[0])
solver.align_with(potted_bonsai[0], dining_table[0], angle=-90)
solver.align_with(ornaments_B[0], coffee_table[0])
solver.align_with(air_conditioner[0], sofa[0])

solver.constraints = []
bookcase_A[0].position = [6.25, 7.804999828338623, 1.0499999523162842]
bookcase_A[0].rotation = [0, 0, -1.568255404977939]
bookcase_A[0].optimize = 2
washing_cabinet[0].position = [5.8462443351745605, 2.950000047683716, 0.44999998807907104]
washing_cabinet[0].rotation = [0, 0, 0.008762216232799396]
washing_cabinet[0].optimize = 2
ornaments_A[0].position = [5.84499979019165, 2.950000047683716, 1.059999942779541]
ornaments_A[0].rotation = [0, 0, 0.02595596860215056]
ornaments_A[0].optimize = 2
washing_machine[0].position = [5.835000514984131, 0.4000000059604645, 0.42500001192092896]
washing_machine[0].rotation = [0, 0, 0.0025409202949315235]
washing_machine[0].optimize = 2
sofa[0].position = [8.904727935791016, 3.25, 0.42500001192092896]
sofa[0].rotation = [0, 0, -3.129719655515574]
sofa[0].optimize = 2
ornaments_B[0].position = [7.300000190734863, 3.5, 0.5449999570846558]
ornaments_B[0].rotation = [0, 0, 0.025961558158328533]
ornaments_B[0].optimize = 2
dining_chair_A[0].position = [7.300000190734863, 4.650000095367432, 0.4399999976158142]
dining_chair_A[0].rotation = [0, 0, -1.5519467713960802]
dining_chair_A[0].optimize = 2
dining_chair_B[0].position = [6.150000095367432, 5.699999809265137, 0.4399999976158142]
dining_chair_B[0].rotation = [0, 0, 0.0157079639172164]
dining_chair_B[0].optimize = 2
potted_bonsai[0].position = [7.300000190734863, 5.699999809265137, 1.0]
potted_bonsai[0].rotation = [0, 0, 0.02596317052810393]
potted_bonsai[0].optimize = 2
bookcase_B[0].position = [8.5, 7.804999828338623, 1.0499999523162842]
bookcase_B[0].rotation = [0, 0, -1.568255404977939]
bookcase_B[0].optimize = 2
dining_chair_D[0].position = [8.449999809265137, 5.699999809265137, 0.4399999976158142]
dining_chair_D[0].rotation = [0, 0, -3.125884689672577]
dining_chair_D[0].optimize = 2
air_conditioner[0].position = [9.283552169799805, 3.25, 0.1599999964237213]
air_conditioner[0].rotation = [0, 0, -3.135941133751684]
air_conditioner[0].optimize = 2
coffee_table[0].position = [7.289999961853027, 3.25, 0.20999999344348907]
coffee_table[0].rotation = [0, 0, 0.025132740109855806]
coffee_table[0].optimize = 2
dining_table[0].position = [7.300000190734863, 5.699999809265137, 0.375]
dining_table[0].rotation = [0, 0, 1.608495437993307]
dining_table[0].optimize = 2
dining_chair_C[0].position = [7.300000190734863, 6.75, 0.4399999976158142]
dining_chair_C[0].rotation = [0, 0, -1.5519467713960802]
dining_chair_C[0].optimize = 2
plants[0].position = [8.899999618530273, 6.949999809265137, 0.699999988079071]
plants[0].rotation = [0, 0, -3.1321678761290697]
plants[0].optimize = 2

