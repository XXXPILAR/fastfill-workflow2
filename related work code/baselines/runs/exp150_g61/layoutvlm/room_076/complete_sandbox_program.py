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
    Wall(corner1=[5.72, 0.00, 0.00], corner2=[5.72, 6.72, 0.00]),
    Wall(corner1=[5.72, 6.72, 0.00], corner2=[0.00, 6.72, 0.00]),
    Wall(corner1=[0.00, 6.72, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[5.72, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
book_A = Assets(description="book", size=[0.23, 0.16, 0.03], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="book", size=[0.26, 0.19, 0.04], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="shelf", size=[0.30, 1.20, 0.05], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="lamp", size=[0.28, 0.28, 0.45], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.15, 1.90, 1.10], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.30, 0.30, 0.50], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="table", size=[0.55, 1.10, 0.75], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.45, 2.00, 0.85], placements=[AssetInstance() for _ in range(1)])
lamp_C = Assets(description="lamp", size=[0.28, 0.28, 0.45], placements=[AssetInstance() for _ in range(1)])
book_C = Assets(description="book", size=[0.24, 0.17, 0.03], placements=[AssetInstance() for _ in range(1)])
lamp_D = Assets(description="lamp", size=[0.28, 0.28, 0.45], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.30, 1.00, 0.05], placements=[AssetInstance() for _ in range(1)])
vase = Assets(description="vase", size=[0.18, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[3.00, 2.40, 0.01], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.42, 0.55, 0.55], placements=[AssetInstance() for _ in range(1)])
lamp_E = Assets(description="lamp", size=[0.30, 0.30, 0.50], placements=[AssetInstance() for _ in range(1)])
lamp_F = Assets(description="lamp", size=[0.40, 0.40, 1.60], placements=[AssetInstance() for _ in range(1)])
cabinet_C = Assets(description="cabinet", size=[0.42, 0.55, 0.55], placements=[AssetInstance() for _ in range(1)])

book_A[0].instance_id = 'book_A_0'
book_B[0].instance_id = 'book_B_0'
shelf_A[0].instance_id = 'shelf_A_0'
lamp_A[0].instance_id = 'lamp_A_0'
bed[0].instance_id = 'bed_0'
lamp_B[0].instance_id = 'lamp_B_0'
table[0].instance_id = 'table_0'
cabinet_A[0].instance_id = 'cabinet_A_0'
lamp_C[0].instance_id = 'lamp_C_0'
book_C[0].instance_id = 'book_C_0'
lamp_D[0].instance_id = 'lamp_D_0'
shelf_B[0].instance_id = 'shelf_B_0'
vase[0].instance_id = 'vase_0'
carpet[0].instance_id = 'carpet_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
lamp_E[0].instance_id = 'lamp_E_0'
lamp_F[0].instance_id = 'lamp_F_0'
cabinet_C[0].instance_id = 'cabinet_C_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

book_A[0].position = [1.0610116031484025, 6.0653986862343405, 0.015]
book_A[0].rotation = [0, 0, 0]
book_B[0].position = [2.8207141180913586, 2.115603312623527, 0.02]
book_B[0].rotation = [0, 0, 0]
shelf_A[0].position = [1.5834553903228699, 3.0387711180527957, 0.025]
shelf_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [3.4057283616591025, 4.560830441200634, 0.225]
lamp_A[0].rotation = [0, 0, 0]
bed[0].position = [5.167094182782889, 4.076703067437746, 0.55]
bed[0].rotation = [0, 0, 0]
lamp_B[0].position = [4.279362510771511, 0.8437162262894653, 0.25]
lamp_B[0].rotation = [0, 0, 0]
table[0].position = [0.6680738494083367, 3.788723577509704, 0.375]
table[0].rotation = [0, 0, 0]
cabinet_A[0].position = [1.109032640274972, 0.2684612622084207, 0.425]
cabinet_A[0].rotation = [0, 0, 0]
lamp_C[0].position = [5.479131329428661, 2.8756563010091387, 0.225]
lamp_C[0].rotation = [0, 0, 0]
book_C[0].position = [4.755356248698776, 3.574008805004242, 0.015]
book_C[0].rotation = [0, 0, 0]
lamp_D[0].position = [0.757825258989971, 1.8300787999368642, 0.225]
lamp_D[0].rotation = [0, 0, 0]
shelf_B[0].position = [2.517326779365824, 2.2601519230780083, 0.025]
shelf_B[0].rotation = [0, 0, 0]
vase[0].position = [1.006377466249511, 1.6927055179141355, 0.15]
vase[0].rotation = [0, 0, 0]
carpet[0].position = [3.664422742134635, 4.765863443542392, 0.0075]
carpet[0].rotation = [0, 0, 0]
cabinet_B[0].position = [2.847048484283336, 5.788495107437256, 0.275]
cabinet_B[0].rotation = [0, 0, 0]
lamp_E[0].position = [0.0719116604951233, 3.264459024191928, 0.25]
lamp_E[0].rotation = [0, 0, 0]
lamp_F[0].position = [3.7583982815610892, 4.380530777177089, 0.8]
lamp_F[0].rotation = [0, 0, 0]
cabinet_C[0].position = [1.3440191168083857, 1.2287102694663412, 0.275]
cabinet_C[0].rotation = [0, 0, 0]
book_A[0].position = [1.0610116031484025, 6.0653986862343405, 0.015]
book_A[0].rotation = [0, 0, 0]
book_B[0].position = [2.8207141180913586, 2.115603312623527, 0.02]
book_B[0].rotation = [0, 0, 0]
shelf_A[0].position = [1.5834553903228699, 3.0387711180527957, 0.025]
shelf_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [3.4057283616591025, 4.560830441200634, 0.225]
lamp_A[0].rotation = [0, 0, 0]
bed[0].position = [5.167094182782889, 4.076703067437746, 0.55]
bed[0].rotation = [0, 0, 0]
lamp_B[0].position = [4.279362510771511, 0.8437162262894653, 0.25]
lamp_B[0].rotation = [0, 0, 0]
table[0].position = [0.6680738494083367, 3.788723577509704, 0.375]
table[0].rotation = [0, 0, 0]
cabinet_A[0].position = [1.109032640274972, 0.2684612622084207, 0.425]
cabinet_A[0].rotation = [0, 0, 0]
lamp_C[0].position = [5.479131329428661, 2.8756563010091387, 0.225]
lamp_C[0].rotation = [0, 0, 0]
book_C[0].position = [4.755356248698776, 3.574008805004242, 0.015]
book_C[0].rotation = [0, 0, 0]
lamp_D[0].position = [0.757825258989971, 1.8300787999368642, 0.225]
lamp_D[0].rotation = [0, 0, 0]
shelf_B[0].position = [2.517326779365824, 2.2601519230780083, 0.025]
shelf_B[0].rotation = [0, 0, 0]
vase[0].position = [1.006377466249511, 1.6927055179141355, 0.15]
vase[0].rotation = [0, 0, 0]
carpet[0].position = [3.664422742134635, 4.765863443542392, 0.0075]
carpet[0].rotation = [0, 0, 0]
cabinet_B[0].position = [2.847048484283336, 5.788495107437256, 0.275]
cabinet_B[0].rotation = [0, 0, 0]
lamp_E[0].position = [0.0719116604951233, 3.264459024191928, 0.25]
lamp_E[0].rotation = [0, 0, 0]
lamp_F[0].position = [3.7583982815610892, 4.380530777177089, 0.8]
lamp_F[0].rotation = [0, 0, 0]
cabinet_C[0].position = [1.3440191168083857, 1.2287102694663412, 0.275]
cabinet_C[0].rotation = [0, 0, 0]

solver.constraints = []

# Coordinates follow the supplied boundary: x=0..5.72, y=0..6.72.
# Keep the east-side doorway and its approach (approximately
# x=4.6..5.72, y=4.65..5.6) free of furniture.
#
# The asset-list identifiers imply:
# o0003 = lamp_A, o0008 = lamp_C, o0010 = lamp_D.

def place_and_anchor(asset_group, xyz, yaw_degrees):
    instance = asset_group[0]
    instance.position = list(xyz)
    instance.rotation = [0, 0, radians(yaw_degrees)]

    # A fixed reference preserves the selected room-relative location and
    # orientation, including clearance from windows and the doorway.
    reference = AssetInstance(
        position=list(xyz),
        rotation=[0, 0, radians(yaw_degrees)]
    )
    solver.distance_constraint(instance, reference, 0, 0, weight=10)
    solver.align_with(instance, reference, angle=0)


# Sleeping zone: bed against the south wall, facing into the room.
# Rotation exchanges its horizontal footprint dimensions:
# x=1.95..3.85, y=0..2.15.
place_and_anchor(bed, [2.90, 1.075, 0.55], 90)
solver.against_wall(bed[0], walls[3])

# Bedside cabinets flank the bed without covering the south window,
# which occupies approximately x=0.76..1.70.
place_and_anchor(cabinet_B, [1.60, 0.36, 0.275], 90)
place_and_anchor(cabinet_C, [4.20, 0.36, 0.275], 90)
solver.align_with(cabinet_B[0], bed[0])
solver.align_with(cabinet_C[0], bed[0])

place_and_anchor(lamp_B, [1.60, 0.36, 0.80], 90)
solver.on_top_of(lamp_B[0], cabinet_B[0])
solver.align_with(lamp_B[0], cabinet_B[0])

place_and_anchor(lamp_E, [4.20, 0.36, 0.80], 90)
solver.on_top_of(lamp_E[0], cabinet_C[0])
solver.align_with(lamp_E[0], cabinet_C[0])

# The rug lies beyond the foot of the bed, rather than intersecting it.
# Its footprint is x=1.30..4.30, y=2.40..4.80.
place_and_anchor(carpet, [2.80, 3.60, 0.005], 0)

# A low east-wall cabinet provides a sufficiently wide supporting surface
# for three lamps. Its footprint ends at y=3.40, well below the door.
place_and_anchor(cabinet_A, [5.495, 2.40, 0.425], 180)
solver.against_wall(cabinet_A[0], walls[0])

# lamp_A is exactly between lamp_C and lamp_D on the same surface.
# Each lamp has at least 0.32 m of edge-to-edge separation from its neighbor.
place_and_anchor(lamp_C, [5.495, 1.80, 1.075], 180)
place_and_anchor(lamp_A, [5.495, 2.40, 1.075], 180)
place_and_anchor(lamp_D, [5.495, 3.00, 1.075], 180)

for lamp_group in (lamp_C, lamp_A, lamp_D):
    solver.on_top_of(lamp_group[0], cabinet_A[0])
    solver.align_with(lamp_group[0], cabinet_A[0])

solver.distance_constraint(lamp_A[0], lamp_C[0], 0.60, 0.60, weight=10)
solver.distance_constraint(lamp_A[0], lamp_D[0], 0.60, 0.60, weight=10)
solver.distance_constraint(lamp_C[0], lamp_D[0], 1.20, 1.20, weight=10)

# Wall-mounted shelves occupy solid sections of the east wall.
# They are deliberately elevated, not floor-standing small objects.
# Shelf_A stops at y=4.55, below the doorway opening.
place_and_anchor(shelf_A, [5.57, 3.95, 1.60], 180)
solver.against_wall(shelf_A[0], walls[0])

place_and_anchor(shelf_B, [5.57, 0.65, 1.20], 180)
solver.against_wall(shelf_B[0], walls[0])
solver.align_with(shelf_B[0], shelf_A[0])

# This book fits fully within the shallow shelf's 0.30 m depth.
place_and_anchor(book_C, [5.57, 0.65, 1.24], 180)
solver.on_top_of(book_C[0], shelf_B[0])
solver.align_with(book_C[0], shelf_B[0])

# A compact table occupies the solid northwest wall segment above the
# west window; it also stays clear of the north-wall glazing.
place_and_anchor(table, [0.275, 5.70, 0.375], 0)
solver.against_wall(table[0], walls[2])

# Separate tabletop objects along its long axis, with no stacking or
# overlapping footprints.
place_and_anchor(book_A, [0.275, 5.34, 0.765], 0)
solver.on_top_of(book_A[0], table[0])
solver.align_with(book_A[0], table[0])

place_and_anchor(book_B, [0.275, 5.68, 0.77], 0)
solver.on_top_of(book_B[0], table[0])
solver.align_with(book_B[0], table[0])

place_and_anchor(vase, [0.275, 6.04, 0.90], 0)
solver.on_top_of(vase[0], table[0])
solver.align_with(vase[0], table[0])

# The tall floor lamp stands beside, not underneath, the table.
# Its footprint is x=0.95..1.35, y=5.85..6.25.
place_and_anchor(lamp_F, [1.15, 6.05, 0.80], -90)

solver.constraints = []
cabinet_C[0].position = [4.199999809265137, 0.36000001430511475, 0.2750000059604645]
cabinet_C[0].rotation = [0, 0, 1.5711463563020638]
cabinet_C[0].optimize = 2
lamp_C[0].position = [5.494999885559082, 1.7999999523162842, 1.0750000476837158]
lamp_C[0].rotation = [0, 0, -3.1414797002076593]
lamp_C[0].optimize = 2
table[0].position = [0.2750963568687439, 5.699999809265137, 0.375]
table[0].rotation = [0, 0, -5.0314510431145735e-05]
table[0].optimize = 2
book_B[0].position = [0.2750000059604645, 5.679999828338623, 0.7699999809265137]
book_B[0].rotation = [0, 0, 0.00038518416006455466]
book_B[0].optimize = 2
vase[0].position = [0.2750000059604645, 6.039999961853027, 0.8999999761581421]
vase[0].rotation = [0, 0, 0.00038518416006455466]
vase[0].optimize = 2
bed[0].position = [2.9000000953674316, 1.075124979019165, 0.550000011920929]
bed[0].rotation = [0, 0, 1.5708552488423198]
bed[0].optimize = 2
shelf_B[0].position = [5.574355125427246, 0.6499999761581421, 0.02500000037252903]
shelf_B[0].rotation = [0, 0, 3.141558826439508]
shelf_B[0].optimize = 2
lamp_F[0].position = [1.149999976158142, 6.050000190734863, 0.800000011920929]
lamp_F[0].rotation = [0, 0, -1.5613715493341729]
lamp_F[0].optimize = 2
lamp_E[0].position = [4.199999809265137, 0.36000001430511475, 0.800000011920929]
lamp_E[0].rotation = [0, 0, 1.5715314666354958]
lamp_E[0].optimize = 2
cabinet_A[0].position = [5.499191761016846, 2.4000000953674316, 0.42500001192092896]
cabinet_A[0].rotation = [0, 0, 3.1415418901840626]
cabinet_A[0].optimize = 2
book_C[0].position = [5.570000171661377, 0.6499999761581421, 0.06499999761581421]
book_C[0].rotation = [0, 0, 3.1413312353900125]
book_C[0].optimize = 2
shelf_A[0].position = [5.574296474456787, 3.950000047683716, 0.02500000037252903]
shelf_A[0].rotation = [0, 0, -3.1415868319346747]
shelf_A[0].optimize = 2
carpet[0].position = [2.799999952316284, 3.5999999046325684, 0.004999999888241291]
carpet[0].rotation = [0, 0, 0.00942477746072377]
carpet[0].optimize = 2
lamp_D[0].position = [5.494999885559082, 3.0, 1.0750000476837158]
lamp_D[0].rotation = [0, 0, -3.1414797002076593]
lamp_D[0].optimize = 2
cabinet_B[0].position = [1.600000023841858, 0.36000001430511475, 0.2750000059604645]
cabinet_B[0].rotation = [0, 0, 1.5711463563020638]
cabinet_B[0].optimize = 2
lamp_B[0].position = [1.600000023841858, 0.36000001430511475, 0.800000011920929]
lamp_B[0].rotation = [0, 0, 1.5715314666354958]
lamp_B[0].optimize = 2
lamp_A[0].position = [5.494999885559082, 2.4000000953674316, 1.0750000476837158]
lamp_A[0].rotation = [0, 0, -3.1414797002076593]
lamp_A[0].optimize = 2
book_A[0].position = [0.2750000059604645, 5.340000152587891, 0.7649999856948853]
book_A[0].rotation = [0, 0, 0.00038518416006455466]
book_A[0].optimize = 2

