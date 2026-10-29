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
    Wall(corner1=[6.27, 0.00, 0.00], corner2=[6.27, 5.34, 0.00]),
    Wall(corner1=[6.27, 5.34, 0.00], corner2=[2.84, 8.77, 0.00]),
    Wall(corner1=[2.84, 8.77, 0.00], corner2=[0.50, 8.77, 0.00]),
    Wall(corner1=[0.50, 8.77, 0.00], corner2=[0.50, 2.77, 0.00]),
    Wall(corner1=[0.50, 2.77, 0.00], corner2=[0.00, 2.77, 0.00]),
    Wall(corner1=[0.00, 2.77, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.27, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
shelf_A = Assets(description="shelf", size=[0.35, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
bed_A = Assets(description="bed", size=[2.10, 1.60, 0.60], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="lamp", size=[0.30, 0.30, 0.50], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.40, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
shelf_C = Assets(description="shelf", size=[0.40, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.30, 0.30, 0.50], placements=[AssetInstance() for _ in range(1)])
shelf_D = Assets(description="shelf", size=[0.35, 0.80, 1.80], placements=[AssetInstance() for _ in range(1)])
lamp_C = Assets(description="lamp", size=[0.35, 0.25, 0.45], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="table", size=[0.65, 1.40, 0.75], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="book", size=[0.24, 0.16, 0.03], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[3.20, 2.40, 0.02], placements=[AssetInstance() for _ in range(1)])
tv = Assets(description="tv", size=[0.08, 1.12, 0.65], placements=[AssetInstance() for _ in range(1)])
lamp_D = Assets(description="lamp", size=[0.40, 0.40, 1.60], placements=[AssetInstance() for _ in range(1)])
bed_B = Assets(description="bed", size=[2.10, 1.00, 0.60], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="book", size=[0.26, 0.18, 0.04], placements=[AssetInstance() for _ in range(1)])
shelf_E = Assets(description="shelf", size=[0.35, 0.80, 1.80], placements=[AssetInstance() for _ in range(1)])

shelf_A[0].instance_id = 'shelf_A_0'
bed_A[0].instance_id = 'bed_A_0'
lamp_A[0].instance_id = 'lamp_A_0'
shelf_B[0].instance_id = 'shelf_B_0'
shelf_C[0].instance_id = 'shelf_C_0'
lamp_B[0].instance_id = 'lamp_B_0'
shelf_D[0].instance_id = 'shelf_D_0'
lamp_C[0].instance_id = 'lamp_C_0'
table[0].instance_id = 'table_0'
book_A[0].instance_id = 'book_A_0'
carpet[0].instance_id = 'carpet_0'
tv[0].instance_id = 'tv_0'
lamp_D[0].instance_id = 'lamp_D_0'
bed_B[0].instance_id = 'bed_B_0'
book_B[0].instance_id = 'book_B_0'
shelf_E[0].instance_id = 'shelf_E_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'

shelf_A[0].position = [0.8873426752688832, 8.372684295737063, 0.9]
shelf_A[0].rotation = [0, 0, 0]
bed_A[0].position = [5.873509053889107, 5.335017924828386, 0.3]
bed_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [4.243147710679329, 5.369635857927991, 0.25]
lamp_A[0].rotation = [0, 0, 0]
shelf_B[0].position = [1.1524426392180562, 5.405153043949751, 0.275]
shelf_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [2.780663410306223, 7.449397140065971, 0.275]
shelf_C[0].rotation = [0, 0, 0]
lamp_B[0].position = [3.5691207482716933, 5.91301831279138, 0.25]
lamp_B[0].rotation = [0, 0, 0]
shelf_D[0].position = [5.231072549492383, 0.5896343856434036, 0.9]
shelf_D[0].rotation = [0, 0, 0]
lamp_C[0].position = [0.9536433403450378, 1.7416745341673223, 0.225]
lamp_C[0].rotation = [0, 0, 0]
table[0].position = [0.6733180780785387, 6.1702497354173325, 0.375]
table[0].rotation = [0, 0, 0]
book_A[0].position = [5.645328714562085, 2.746334952587925, 0.015]
book_A[0].rotation = [0, 0, 0]
carpet[0].position = [1.1901600993728318, 7.098076268480529, 0.01]
carpet[0].rotation = [0, 0, 0]
tv[0].position = [5.165184627202614, 1.1678691036715951, 0.325]
tv[0].rotation = [0, 0, 0]
lamp_D[0].position = [0.8380395346328969, 3.429547610065919, 0.8]
lamp_D[0].rotation = [0, 0, 0]
bed_B[0].position = [1.0266028877937041, 1.1833215945499624, 0.3]
bed_B[0].rotation = [0, 0, 0]
book_B[0].position = [4.356687810961862, 3.718959516914221, 0.0175]
book_B[0].rotation = [0, 0, 0]
shelf_E[0].position = [5.354425805505316, 4.150575375824176, 0.9]
shelf_E[0].rotation = [0, 0, 0]
shelf_A[0].position = [0.8873426752688832, 8.372684295737063, 0.9]
shelf_A[0].rotation = [0, 0, 0]
bed_A[0].position = [5.873509053889107, 5.335017924828386, 0.3]
bed_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [4.243147710679329, 5.369635857927991, 0.25]
lamp_A[0].rotation = [0, 0, 0]
shelf_B[0].position = [1.1524426392180562, 5.405153043949751, 0.275]
shelf_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [2.780663410306223, 7.449397140065971, 0.275]
shelf_C[0].rotation = [0, 0, 0]
lamp_B[0].position = [3.5691207482716933, 5.91301831279138, 0.25]
lamp_B[0].rotation = [0, 0, 0]
shelf_D[0].position = [5.231072549492383, 0.5896343856434036, 0.9]
shelf_D[0].rotation = [0, 0, 0]
lamp_C[0].position = [0.9536433403450378, 1.7416745341673223, 0.225]
lamp_C[0].rotation = [0, 0, 0]
table[0].position = [0.6733180780785387, 6.1702497354173325, 0.375]
table[0].rotation = [0, 0, 0]
book_A[0].position = [5.645328714562085, 2.746334952587925, 0.015]
book_A[0].rotation = [0, 0, 0]
carpet[0].position = [1.1901600993728318, 7.098076268480529, 0.01]
carpet[0].rotation = [0, 0, 0]
tv[0].position = [5.165184627202614, 1.1678691036715951, 0.325]
tv[0].rotation = [0, 0, 0]
lamp_D[0].position = [0.8380395346328969, 3.429547610065919, 0.8]
lamp_D[0].rotation = [0, 0, 0]
bed_B[0].position = [1.0266028877937041, 1.1833215945499624, 0.3]
bed_B[0].rotation = [0, 0, 0]
book_B[0].position = [4.356687810961862, 3.718959516914221, 0.0175]
book_B[0].rotation = [0, 0, 0]
shelf_E[0].position = [5.354425805505316, 4.150575375824176, 0.9]
shelf_E[0].rotation = [0, 0, 0]

solver.constraints = []

# The southern wall provides a storage/media run, with the table between
# the two matching tall shelves. Keep the southern window (x=3.10..4.46)
# and the western doorway unobstructed.
shelf_D[0].position = [0.40, 0.175, 0.90]
shelf_D[0].rotation = [0, 0, radians(90)]
table[0].position = [1.55, 0.325, 0.375]
table[0].rotation = [0, 0, radians(90)]
shelf_E[0].position = [2.70, 0.175, 0.90]
shelf_E[0].rotation = [0, 0, radians(90)]

# Separate sleeping areas leave the middle of the room open.
# Both beds have their heads against the western boundary.
bed_A[0].position = [1.55, 6.90, 0.30]
bed_A[0].rotation = [0, 0, 0]
bed_B[0].position = [1.05, 2.00, 0.30]
bed_B[0].rotation = [0, 0, 0]

# Low bedside shelves do not obstruct the northern window.
shelf_B[0].position = [0.70, 5.75, 0.275]
shelf_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [0.70, 8.15, 0.275]
shelf_C[0].rotation = [0, 0, 0]

# This tall shelf stops below the doorway's southern jamb.
shelf_A[0].position = [0.675, 3.60, 0.90]
shelf_A[0].rotation = [0, 0, 0]

lamp_A[0].position = [0.70, 5.75, 0.80]
lamp_A[0].rotation = [0, 0, 0]
lamp_B[0].position = [0.70, 8.15, 0.80]
lamp_B[0].rotation = [0, 0, 0]

# TV, reading lamp, and book occupy distinct parts of the tabletop.
tv[0].position = [1.68, 0.49, 1.075]
tv[0].rotation = [0, 0, radians(90)]
lamp_C[0].position = [0.98, 0.30, 0.975]
lamp_C[0].rotation = [0, 0, radians(90)]
book_A[0].position = [1.65, 0.18, 0.765]
book_A[0].rotation = [0, 0, 0]

book_B[0].position = [0.675, 3.60, 1.82]
book_B[0].rotation = [0, 0, 0]

lamp_D[0].position = [2.45, 2.20, 0.80]
lamp_D[0].rotation = [0, 0, radians(180)]

# The rug occupies the open eastern floor, away from furniture footprints
# and the entrance route. Its eastern edge remains inside the room.
carpet[0].position = [4.20, 3.65, 0.01]
carpet[0].rotation = [0, 0, 0]

# Preserve the checked floor footprints first. Fixed center targets keep
# the door approach, window setbacks, and furniture clearances intact.
# Each new floor asset receives both position and orientation constraints.
for layout_asset, layout_wall, layout_heading in [
    (shelf_D, walls[6], 90),
    (table, walls[6], 90),
    (shelf_E, walls[6], 90),
    (bed_A, walls[3], 0),
    (bed_B, walls[5], 0),
    (shelf_B, walls[3], 0),
    (shelf_C, walls[3], 0),
    (shelf_A, walls[3], 0),
]:
    solver.distance_constraint(
        layout_asset[0],
        AssetInstance(position=list(layout_asset[0].position)),
        0, 0, weight=10
    )
    solver.align_with(
        layout_asset[0],
        AssetInstance(rotation=[0, 0, radians(layout_heading)])
    )
    solver.against_wall(layout_asset[0], layout_wall)

for layout_asset, layout_heading in [(lamp_D, 180), (carpet, 0)]:
    solver.distance_constraint(
        layout_asset[0],
        AssetInstance(position=list(layout_asset[0].position)),
        0, 0, weight=10
    )
    solver.align_with(
        layout_asset[0],
        AssetInstance(rotation=[0, 0, radians(layout_heading)])
    )

# Explicit flanking relationships: all three centers lie on the same
# southern-wall run, with the table between the shelves.
solver.align_with(shelf_D[0], table[0])
solver.align_with(shelf_E[0], table[0])
for layout_neighbor in [shelf_D[0], shelf_E[0]]:
    layout_separation = sum(
        (table[0].position[axis] - layout_neighbor.position[axis]) ** 2
        for axis in range(3)
    ) ** 0.5
    solver.distance_constraint(
        table[0], layout_neighbor,
        layout_separation, layout_separation, weight=10
    )

# Surface support comes first for small objects. Exact relative center
# distances preserve each tabletop location, including vertical offsets.
for layout_item, layout_support, layout_heading in [
    (lamp_A, shelf_B, 0),
    (lamp_B, shelf_C, 0),
    (lamp_C, table, 90),
    (tv, table, 90),
    (book_A, table, 0),
    (book_B, shelf_A, 0),
]:
    solver.on_top_of(layout_item[0], layout_support[0])
    solver.distance_constraint(
        layout_item[0],
        AssetInstance(position=list(layout_item[0].position)),
        0, 0, weight=10
    )
    layout_separation = sum(
        (layout_item[0].position[axis]
         - layout_support[0].position[axis]) ** 2
        for axis in range(3)
    ) ** 0.5
    solver.distance_constraint(
        layout_item[0], layout_support[0],
        layout_separation, layout_separation, weight=10
    )
    solver.align_with(
        layout_item[0],
        AssetInstance(rotation=[0, 0, radians(layout_heading)])
    )

solver.constraints = []
tv[0].position = [1.6899999380111694, 0.5, 1.0750000476837158]
tv[0].rotation = [0, 0, 1.586504290712113]
tv[0].optimize = 2
lamp_C[0].position = [0.9700000286102295, 0.2900000214576721, 0.9750000238418579]
lamp_C[0].rotation = [0, 0, 1.586504290712113]
lamp_C[0].optimize = 2
shelf_E[0].position = [2.700000047683716, 0.17849811911582947, 0.8999999761581421]
shelf_E[0].rotation = [0, 0, 1.5795585477508047]
shelf_E[0].optimize = 2
table[0].position = [1.5425124168395996, 0.36546337604522705, 0.375]
table[0].rotation = [0, 0, 1.6044476840692317]
table[0].optimize = 2
book_B[0].position = [0.675000011920929, 3.5999999046325684, 1.8199999332427979]
book_B[0].rotation = [0, 0, 0.0157079639172164]
book_B[0].optimize = 2
bed_A[0].position = [1.5520293712615967, 6.900000095367432, 0.30000001192092896]
bed_A[0].rotation = [0, 0, 0.0025409028408403984]
bed_A[0].optimize = 2
bed_B[0].position = [1.059999942779541, 2.009999990463257, 0.30000001192092896]
bed_B[0].rotation = [0, 0, 0.002540830603107858]
bed_B[0].optimize = 2
shelf_B[0].position = [0.7021828889846802, 5.75, 0.2750000059604645]
shelf_B[0].rotation = [0, 0, 0.008762224756822399]
shelf_B[0].optimize = 2
shelf_D[0].position = [0.4000000059604645, 0.17499999701976776, 0.8999999761581421]
shelf_D[0].rotation = [0, 0, 1.5795584761194248]
shelf_D[0].optimize = 2
shelf_C[0].position = [0.7021828889846802, 8.149999618530273, 0.2750000059604645]
shelf_C[0].rotation = [0, 0, 0.008762224756822399]
shelf_C[0].optimize = 2
shelf_A[0].position = [0.678936243057251, 3.5999999046325684, 0.8999999761581421]
shelf_A[0].rotation = [0, 0, 0.008762219111517372]
shelf_A[0].optimize = 2
carpet[0].position = [4.199999809265137, 3.6500000953674316, 0.009999999776482582]
carpet[0].rotation = [0, 0, 0.00942477746072377]
carpet[0].optimize = 2
lamp_D[0].position = [2.450000047683716, 2.200000047683716, 0.800000011920929]
lamp_D[0].rotation = [0, 0, -3.1321678761290697]
lamp_D[0].optimize = 2
lamp_B[0].position = [0.699999988079071, 8.149999618530273, 0.800000011920929]
lamp_B[0].rotation = [0, 0, 0.0157079639172164]
lamp_B[0].optimize = 2
lamp_A[0].position = [0.699999988079071, 5.75, 0.800000011920929]
lamp_A[0].rotation = [0, 0, 0.0157079639172164]
lamp_A[0].optimize = 2
book_A[0].position = [1.659999966621399, 0.17000001668930054, 0.7649999856948853]
book_A[0].rotation = [0, 0, 0.0157079639172164]
book_A[0].optimize = 2

