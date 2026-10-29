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
    Wall(corner1=[0.00, 3.38, 0.00], corner2=[0.12, 2.50, 0.00]),
    Wall(corner1=[0.12, 2.50, 0.00], corner2=[0.45, 1.69, 0.00]),
    Wall(corner1=[0.45, 1.69, 0.00], corner2=[0.72, 1.34, 0.00]),
    Wall(corner1=[0.72, 1.34, 0.00], corner2=[0.99, 0.99, 0.00]),
    Wall(corner1=[0.99, 0.99, 0.00], corner2=[1.69, 0.45, 0.00]),
    Wall(corner1=[1.69, 0.45, 0.00], corner2=[2.50, 0.12, 0.00]),
    Wall(corner1=[2.50, 0.12, 0.00], corner2=[3.38, 0.00, 0.00]),
    Wall(corner1=[3.38, 0.00, 0.00], corner2=[9.74, 0.00, 0.00]),
    Wall(corner1=[9.74, 0.00, 0.00], corner2=[9.74, 4.74, 0.00]),
    Wall(corner1=[9.74, 4.74, 0.00], corner2=[3.74, 4.74, 0.00]),
    Wall(corner1=[3.74, 4.74, 0.00], corner2=[3.74, 6.24, 0.00]),
    Wall(corner1=[3.74, 6.24, 0.00], corner2=[0.00, 6.24, 0.00]),
    Wall(corner1=[0.00, 6.24, 0.00], corner2=[0.00, 3.38, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
shelf_A = Assets(description="shelf", size=[0.35, 0.65, 1.10], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.35, 1.80, 1.80], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="book", size=[0.23, 0.16, 0.03], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[4.00, 3.00, 0.01], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="book", size=[0.04, 0.20, 0.28], placements=[AssetInstance() for _ in range(1)])
shelf_C = Assets(description="shelf", size=[0.30, 1.00, 1.80], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="lamp", size=[0.30, 0.30, 0.50], placements=[AssetInstance() for _ in range(1)])
shelf_D = Assets(description="shelf", size=[0.35, 0.65, 1.10], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="table", size=[0.70, 1.40, 0.75], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.30, 0.30, 0.50], placements=[AssetInstance() for _ in range(1)])
lamp_C = Assets(description="lamp", size=[0.35, 0.25, 0.50], placements=[AssetInstance() for _ in range(1)])
book_C = Assets(description="book", size=[0.25, 0.18, 0.04], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.10, 1.80, 0.95], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="cabinet", size=[0.55, 1.60, 0.90], placements=[AssetInstance() for _ in range(1)])
lamp_D = Assets(description="lamp", size=[0.40, 0.40, 1.60], placements=[AssetInstance() for _ in range(1)])
book_D = Assets(description="book", size=[0.23, 0.16, 0.03], placements=[AssetInstance() for _ in range(1)])

shelf_A[0].instance_id = 'shelf_A_0'
shelf_B[0].instance_id = 'shelf_B_0'
book_A[0].instance_id = 'book_A_0'
carpet[0].instance_id = 'carpet_0'
book_B[0].instance_id = 'book_B_0'
shelf_C[0].instance_id = 'shelf_C_0'
lamp_A[0].instance_id = 'lamp_A_0'
shelf_D[0].instance_id = 'shelf_D_0'
table[0].instance_id = 'table_0'
lamp_B[0].instance_id = 'lamp_B_0'
lamp_C[0].instance_id = 'lamp_C_0'
book_C[0].instance_id = 'book_C_0'
bed[0].instance_id = 'bed_0'
cabinet[0].instance_id = 'cabinet_0'
lamp_D[0].instance_id = 'lamp_D_0'
book_D[0].instance_id = 'book_D_0'
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

shelf_A[0].position = [7.744743422202579, 1.3180158835027538, 0.55]
shelf_A[0].rotation = [0, 0, 0]
shelf_B[0].position = [1.8470410961589019, 6.033613236164803, 0.9]
shelf_B[0].rotation = [0, 0, 0]
book_A[0].position = [2.35059028503189, 0.9828740160329574, 0.015]
book_A[0].rotation = [0, 0, 0]
carpet[0].position = [4.640111730619893, 0.06794377112997366, 0.0075]
carpet[0].rotation = [0, 0, 0]
book_B[0].position = [8.726067918437298, 0.04986184782073808, 0.14]
book_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [3.6907330012582698, 5.174717955036484, 0.9]
shelf_C[0].rotation = [0, 0, 0]
lamp_A[0].position = [6.53213512917078, 3.472703938745206, 0.25]
lamp_A[0].rotation = [0, 0, 0]
shelf_D[0].position = [3.6309126134569283, 2.125466270334919, 0.55]
shelf_D[0].rotation = [0, 0, 0]
table[0].position = [6.42370433020088, 3.592017893397974, 0.375]
table[0].rotation = [0, 0, 0]
lamp_B[0].position = [7.101502782554951, 0.7044512251126678, 0.25]
lamp_B[0].rotation = [0, 0, 0]
lamp_C[0].position = [8.6328473020152, 2.3177001958670203, 0.25]
lamp_C[0].rotation = [0, 0, 0]
book_C[0].position = [2.4350090061280127, 4.617886053880975, 0.0175]
book_C[0].rotation = [0, 0, 0]
bed[0].position = [6.249684876075107, 0.5711402396564743, 0.475]
bed[0].rotation = [0, 0, 0]
cabinet[0].position = [9.492747476281131, 3.872256257812621, 0.45]
cabinet[0].rotation = [0, 0, 0]
lamp_D[0].position = [4.1295375540675385, 0.036044622285121175, 0.8]
lamp_D[0].rotation = [0, 0, 0]
book_D[0].position = [1.2825607645247679, 5.451595891936335, 0.0125]
book_D[0].rotation = [0, 0, 0]
shelf_A[0].position = [7.744743422202579, 1.3180158835027538, 0.55]
shelf_A[0].rotation = [0, 0, 0]
shelf_B[0].position = [1.8470410961589019, 6.033613236164803, 0.9]
shelf_B[0].rotation = [0, 0, 0]
book_A[0].position = [2.35059028503189, 0.9828740160329574, 0.015]
book_A[0].rotation = [0, 0, 0]
carpet[0].position = [4.640111730619893, 0.06794377112997366, 0.0075]
carpet[0].rotation = [0, 0, 0]
book_B[0].position = [8.726067918437298, 0.04986184782073808, 0.14]
book_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [3.6907330012582698, 5.174717955036484, 0.9]
shelf_C[0].rotation = [0, 0, 0]
lamp_A[0].position = [6.53213512917078, 3.472703938745206, 0.25]
lamp_A[0].rotation = [0, 0, 0]
shelf_D[0].position = [3.6309126134569283, 2.125466270334919, 0.55]
shelf_D[0].rotation = [0, 0, 0]
table[0].position = [6.42370433020088, 3.592017893397974, 0.375]
table[0].rotation = [0, 0, 0]
lamp_B[0].position = [7.101502782554951, 0.7044512251126678, 0.25]
lamp_B[0].rotation = [0, 0, 0]
lamp_C[0].position = [8.6328473020152, 2.3177001958670203, 0.25]
lamp_C[0].rotation = [0, 0, 0]
book_C[0].position = [2.4350090061280127, 4.617886053880975, 0.0175]
book_C[0].rotation = [0, 0, 0]
bed[0].position = [6.249684876075107, 0.5711402396564743, 0.475]
bed[0].rotation = [0, 0, 0]
cabinet[0].position = [9.492747476281131, 3.872256257812621, 0.45]
cabinet[0].rotation = [0, 0, 0]
lamp_D[0].position = [4.1295375540675385, 0.036044622285121175, 0.8]
lamp_D[0].rotation = [0, 0, 0]
book_D[0].position = [1.2825607645247679, 5.451595891936335, 0.0125]
book_D[0].rotation = [0, 0, 0]

solver.constraints = []

# The listed ordering identifies o0000/o0007 as shelf_A/shelf_D,
# o0001 as shelf_B, o0004 as book_B, and o0012 as bed.
# Put the bed against the north wall, between two bedside shelves,
# facing south toward shelf_B. Keep the northwest doorway unobstructed.

# Each tuple specifies an existing asset, its center, and its yaw in degrees.
# Furniture footprints are separated; only supported objects touch their supports.
layout_specs = [
    (bed,     [7.60, 3.690, 0.475], -90),
    (shelf_A, [6.20, 4.565, 0.550], -90),
    (shelf_D, [9.00, 4.565, 0.550], -90),

    # Freestanding shelving opposite the bed leaves a 1.265 m foot aisle
    # and space behind it to reach the south windows.
    (shelf_B, [7.60, 1.200, 0.900], 90),

    # Reading/work area in the northwest extension, east of the entry path.
    (cabinet, [2.55, 5.965, 0.450], -90),
    (shelf_C, [3.59, 5.700, 0.900], 180),
    (table,   [3.00, 4.800, 0.375], 90),

    # Keep the rug separate from furniture footprints and out of the doorway.
    (carpet,  [3.20, 2.750, 0.005], 0),
    (lamp_D,  [5.70, 3.800, 0.800], 180),

    # Small objects rest on explicit supporting surfaces.
    (lamp_A,  [6.20, 4.565, 1.350], -90),
    (lamp_B,  [9.00, 4.565, 1.350], -90),
    (lamp_C,  [3.35, 4.950, 1.000], -90),
    (book_A,  [2.70, 4.600, 0.765], 0),
    (book_C,  [2.65, 5.000, 0.770], 0),
    (book_D,  [2.75, 5.980, 0.915], 0),

    # Upright book: its back edge reaches y=6.24, against the north wall,
    # while its entire footprint remains supported by the cabinet.
    (book_B,  [2.20, 6.140, 1.040], -90),
]

for asset_group, center_xyz, yaw_degrees in layout_specs:
    asset_group[0].position = list(center_xyz)
    asset_group[0].rotation = [0, 0, radians(yaw_degrees)]

# Important support and wall relationships come first.
solver.on_top_of(lamp_A[0], shelf_A[0])
solver.on_top_of(lamp_B[0], shelf_D[0])
solver.on_top_of(lamp_C[0], table[0])
solver.on_top_of(book_A[0], table[0])
solver.on_top_of(book_C[0], table[0])
solver.on_top_of(book_D[0], cabinet[0])
solver.on_top_of(book_B[0], cabinet[0])

# book_B is rotated -90 degrees, so its local x thickness is along y.
# Adjust its center so its 0.04 m thickness, rather than its 0.20 m width,
# meets the wall exactly.
book_B[0].position = [2.20, 6.220, 1.040]
solver.against_wall(book_B[0], walls[11])

solver.against_wall(bed[0], walls[9])
solver.against_wall(shelf_A[0], walls[9])
solver.against_wall(shelf_D[0], walls[9])
solver.against_wall(cabinet[0], walls[11])
solver.against_wall(shelf_C[0], walls[10])

# Bed orientation expresses the requested facing relationship directly.
solver.point_towards(bed[0], shelf_B[0])

# Give every instance a position-based constraint and an orientation-based
# constraint. Fixed references preserve the calculated clearances, including
# the clear entry route, without introducing any additional physical assets.
for asset_group, center_xyz, yaw_degrees in layout_specs:
    fixed_reference = AssetInstance(
        position=list(asset_group[0].position),
        rotation=[0, 0, radians(yaw_degrees)],
    )
    solver.distance_constraint(
        asset_group[0], fixed_reference,
        min_distance=0.0, max_distance=0.0, weight=10,
    )
    if asset_group is not bed:
        solver.align_with(asset_group[0], fixed_reference, angle=0)

solver.constraints = []
cabinet[0].position = [2.549999952316284, 5.962189674377441, 0.44999998807907104]
cabinet[0].rotation = [0, 0, -1.5709813039200156]
cabinet[0].optimize = 2
lamp_C[0].position = [3.3499999046325684, 4.949999809265137, 1.0]
lamp_C[0].rotation = [0, 0, -1.5582299555380688]
lamp_C[0].optimize = 2
table[0].position = [3.0, 4.800000190734863, 0.375]
table[0].rotation = [0, 0, 1.589645882193713]
table[0].optimize = 2
book_B[0].position = [2.200000047683716, 6.217087268829346, 1.0399999618530273]
book_B[0].rotation = [0, 0, -1.5706347606470248]
book_B[0].optimize = 2
bed[0].position = [7.599999904632568, 3.687194585800171, 0.4749999940395355]
bed[0].rotation = [0, 0, -1.5709211275530022]
bed[0].optimize = 2
shelf_B[0].position = [7.599999904632568, 1.2000000476837158, 0.8999999761581421]
shelf_B[0].rotation = [0, 0, 1.5833626980517244]
shelf_B[0].optimize = 2
shelf_D[0].position = [9.0, 4.5620880126953125, 0.550000011920929]
shelf_D[0].rotation = [0, 0, -1.570634698269627]
shelf_D[0].optimize = 2
shelf_C[0].position = [3.5870866775512695, 5.699999809265137, 0.8999999761581421]
shelf_C[0].rotation = [0, 0, 3.1414714013806235]
shelf_C[0].optimize = 2
book_C[0].position = [2.6500000953674316, 5.0, 0.7699999809265137]
book_C[0].rotation = [0, 0, 0.01256637125682779]
book_C[0].optimize = 2
shelf_A[0].position = [6.199999809265137, 4.5620880126953125, 0.550000011920929]
shelf_A[0].rotation = [0, 0, -1.570634698269627]
shelf_A[0].optimize = 2
book_D[0].position = [2.75, 5.980000019073486, 0.9149999618530273]
book_D[0].rotation = [0, 0, 0.01256637125682779]
book_D[0].optimize = 2
carpet[0].position = [3.200000047683716, 2.75, 0.004999999888241291]
carpet[0].rotation = [0, 0, 0.00942477746072377]
carpet[0].optimize = 2
lamp_D[0].position = [5.699999809265137, 3.799999952316284, 0.800000011920929]
lamp_D[0].rotation = [0, 0, -3.1321678761290697]
lamp_D[0].optimize = 2
lamp_B[0].position = [9.0, 4.565000057220459, 1.350000023841858]
lamp_B[0].rotation = [0, 0, -1.5582299555380688]
lamp_B[0].optimize = 2
lamp_A[0].position = [6.199999809265137, 4.565000057220459, 1.350000023841858]
lamp_A[0].rotation = [0, 0, -1.5582299555380688]
lamp_A[0].optimize = 2
book_A[0].position = [2.700000047683716, 4.599999904632568, 0.7649999856948853]
book_A[0].rotation = [0, 0, 0.01256637125682779]
book_A[0].optimize = 2

