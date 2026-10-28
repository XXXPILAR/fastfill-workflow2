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
    Wall(corner1=[1.53, 3.84, 0.00], corner2=[0.00, 3.84, 0.00]),
    Wall(corner1=[0.00, 3.84, 0.00], corner2=[0.00, 1.89, 0.00]),
    Wall(corner1=[0.00, 1.89, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[0.24, 0.00, 0.00]),
    Wall(corner1=[0.24, 0.00, 0.00], corner2=[2.10, 0.00, 0.00]),
    Wall(corner1=[2.10, 0.00, 0.00], corner2=[2.79, 0.00, 0.00]),
    Wall(corner1=[2.79, 0.00, 0.00], corner2=[2.79, 3.71, 0.00]),
    Wall(corner1=[2.79, 3.71, 0.00], corner2=[2.79, 3.96, 0.00]),
    Wall(corner1=[2.79, 3.96, 0.00], corner2=[2.79, 4.76, 0.00]),
    Wall(corner1=[2.79, 4.76, 0.00], corner2=[2.79, 4.95, 0.00]),
    Wall(corner1=[2.79, 4.95, 0.00], corner2=[1.65, 4.95, 0.00]),
    Wall(corner1=[1.65, 4.95, 0.00], corner2=[1.65, 4.80, 0.00]),
    Wall(corner1=[1.65, 4.80, 0.00], corner2=[1.65, 4.00, 0.00]),
    Wall(corner1=[1.65, 4.00, 0.00], corner2=[1.65, 3.84, 0.00]),
    Wall(corner1=[1.65, 3.84, 0.00], corner2=[1.53, 3.84, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
book_A = Assets(description="book", size=[0.22, 0.15, 0.03], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="book", size=[0.24, 0.16, 0.03], placements=[AssetInstance() for _ in range(1)])
bedside_table_A = Assets(description="bedside table", size=[0.40, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[2.30, 1.60, 0.01], placements=[AssetInstance() for _ in range(1)])
book_C = Assets(description="book", size=[0.21, 0.14, 0.03], placements=[AssetInstance() for _ in range(1)])
bedside_table_B = Assets(description="bedside table", size=[0.40, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
bottle = Assets(description="bottle", size=[0.07, 0.07, 0.24], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.00, 1.40, 0.55], placements=[AssetInstance() for _ in range(1)])

book_A[0].instance_id = 'book_A_0'
book_B[0].instance_id = 'book_B_0'
bedside_table_A[0].instance_id = 'bedside_table_A_0'
carpet[0].instance_id = 'carpet_0'
book_C[0].instance_id = 'book_C_0'
bedside_table_B[0].instance_id = 'bedside_table_B_0'
bottle[0].instance_id = 'bottle_0'
bed[0].instance_id = 'bed_0'
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
walls[13].instance_id = 'walls_13'
walls[14].instance_id = 'walls_14'

book_A[0].position = [1.1972038045738973, 1.040453820368135, 0.0125]
book_A[0].rotation = [0, 0, 0]
book_B[0].position = [0.7847445710756988, 2.0464803625143047, 0.015]
book_B[0].rotation = [0, 0, 0]
bedside_table_A[0].position = [2.2636598606440916, 4.679758307073741, 0.275]
bedside_table_A[0].rotation = [0, 0, 0]
carpet[0].position = [0.30715877322564533, 2.2409720595988682, 0.0075]
carpet[0].rotation = [0, 0, 0]
book_C[0].position = [0.6732051230859661, 2.30630332651916, 0.0125]
book_C[0].rotation = [0, 0, 0]
bedside_table_B[0].position = [1.954800665155901, 4.456457050868617, 0.275]
bedside_table_B[0].rotation = [0, 0, 0]
bottle[0].position = [2.4182625336577033, 2.4316732092502717, 0.12]
bottle[0].rotation = [0, 0, 0]
bed[0].position = [2.2422266291913098, 2.2021704639038853, 0.275]
bed[0].rotation = [0, 0, 0]
book_A[0].position = [1.1972038045738973, 1.040453820368135, 0.0125]
book_A[0].rotation = [0, 0, 0]
book_B[0].position = [0.7847445710756988, 2.0464803625143047, 0.015]
book_B[0].rotation = [0, 0, 0]
bedside_table_A[0].position = [2.2636598606440916, 4.679758307073741, 0.275]
bedside_table_A[0].rotation = [0, 0, 0]
carpet[0].position = [0.30715877322564533, 2.2409720595988682, 0.0075]
carpet[0].rotation = [0, 0, 0]
book_C[0].position = [0.6732051230859661, 2.30630332651916, 0.0125]
book_C[0].rotation = [0, 0, 0]
bedside_table_B[0].position = [1.954800665155901, 4.456457050868617, 0.275]
bedside_table_B[0].rotation = [0, 0, 0]
bottle[0].position = [2.4182625336577033, 2.4316732092502717, 0.12]
bottle[0].rotation = [0, 0, 0]
bed[0].position = [2.2422266291913098, 2.2021704639038853, 0.275]
bed[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the bed with its head end against the long right wall. This avoids the
# fixed wardrobe and keeps both door approaches in the upper alcove clear.
bed[0].position = [1.79, 1.75, 0.275]
bed[0].rotation = [0, 0, radians(180)]

# The bedside tables flank the bed along its two sides, so the bed is spatially
# between them. Both tables remain against the same wall as the bed.
bedside_table_A[0].position = [2.565, 0.80, 0.275]
bedside_table_A[0].rotation = [0, 0, radians(180)]

bedside_table_B[0].position = [2.565, 2.70, 0.275]
bedside_table_B[0].rotation = [0, 0, radians(180)]

# Center the carpet beneath the bed while leaving a small visible border around
# its sides and foot. Its thin height places it directly on the floor.
carpet[0].position = [1.55, 1.75, 0.005]
carpet[0].rotation = [0, 0, radians(0)]

# Arrange two books separately on the lower bedside table.
book_A[0].position = [2.53, 0.69, 0.565]
book_A[0].rotation = [0, 0, radians(0)]

book_B[0].position = [2.53, 0.91, 0.565]
book_B[0].rotation = [0, 0, radians(0)]

# Place the remaining book and bottle on separate parts of the upper table.
book_C[0].position = [2.50, 2.65, 0.565]
book_C[0].rotation = [0, 0, radians(0)]

bottle[0].position = [2.68, 2.84, 0.67]
bottle[0].rotation = [0, 0, radians(0)]


# Important wall and flanking constraints come first. Wall 6 is the long
# right-hand wall below the door, so these constraints do not obstruct either
# doorway.
solver.against_wall(bed[0], walls[6])
solver.against_wall(bedside_table_A[0], walls[6])
solver.against_wall(bedside_table_B[0], walls[6])

# Keep the two tables symmetrically spaced from the bed. Their bounding boxes
# touch the bed's sides without overlapping it.
solver.distance_constraint(
    bedside_table_A[0], bed[0], 1.22, 1.24, weight=10
)
solver.distance_constraint(
    bedside_table_B[0], bed[0], 1.22, 1.24, weight=10
)

# Preserve the bed-and-tables orientation along the right wall.
solver.align_with(bedside_table_A[0], bed[0], angle=0)
solver.align_with(bedside_table_B[0], bed[0], angle=0)

# The bed faces into the usable center of the room, away from the wall.
bed_facing_target = AssetInstance(position=[0.80, 1.75, 0.275])
solver.point_towards(bed[0], bed_facing_target)

# Anchor the carpet under the bed and keep its edges parallel to the bed.
carpet_target = AssetInstance(position=[1.55, 1.75, 0.005])
solver.distance_constraint(carpet[0], carpet_target, 0, 0, weight=10)
solver.align_with(carpet[0], bed[0], angle=180)

# The small objects must remain supported by their respective tables.
solver.on_top_of(book_A[0], bedside_table_A[0])
solver.on_top_of(book_B[0], bedside_table_A[0])
solver.on_top_of(book_C[0], bedside_table_B[0])
solver.on_top_of(bottle[0], bedside_table_B[0])

# These position constraints keep each tabletop object near its intended part
# of the supporting surface if the furniture is adjusted by the solver.
solver.distance_constraint(
    book_A[0], bedside_table_A[0], 0.29, 0.34, weight=10
)
solver.distance_constraint(
    book_B[0], bedside_table_A[0], 0.29, 0.34, weight=10
)
solver.distance_constraint(
    book_C[0], bedside_table_B[0], 0.29, 0.34, weight=10
)
solver.distance_constraint(
    bottle[0], bedside_table_B[0], 0.39, 0.43, weight=10
)

# Maintain sensible orientations for all tabletop objects.
solver.align_with(book_A[0], bedside_table_A[0], angle=180)
solver.align_with(book_B[0], bedside_table_A[0], angle=180)
solver.align_with(book_C[0], bedside_table_B[0], angle=180)
solver.align_with(bottle[0], bedside_table_B[0], angle=0)

solver.constraints = []
book_B[0].position = [2.427877902984619, 1.9727894067764282, 0.5649999976158142]
book_B[0].rotation = [0, 0, 1.3781031318616507e-07]
book_B[0].optimize = 2
bed[0].position = [2.316387414932251, 3.543703079223633, 0.2750000059604645]
bed[0].rotation = [0, 0, -0.3813306640336228]
bed[0].optimize = 2
bedside_table_B[0].position = [2.5734829902648926, 4.706628799438477, 0.2750000059604645]
bedside_table_B[0].rotation = [0, 0, 3.059210697059431]
bedside_table_B[0].optimize = 2
carpet[0].position = [1.4099398851394653, 1.75, 0.004999999888241291]
carpet[0].rotation = [0, 0, 2.757859634084841]
carpet[0].optimize = 2
book_A[0].position = [2.4718775749206543, 1.9727894067764282, 0.5649999976158142]
book_A[0].rotation = [0, 0, 1.3781031318616507e-07]
book_A[0].optimize = 2
bottle[0].position = [2.7542896270751953, 4.4659342765808105, 0.6700000166893005]
bottle[0].rotation = [0, 0, 3.0850757658702466]
bottle[0].optimize = 2
book_C[0].position = [2.6906838417053223, 4.47118616104126, 0.5649999976158142]
book_C[0].rotation = [0, 0, -0.08265954787568941]
book_C[0].optimize = 2
bedside_table_A[0].position = [2.5913195610046387, 2.197789430618286, 0.2750000059604645]
bedside_table_A[0].rotation = [0, 0, -3.1415926157726903]
bedside_table_A[0].optimize = 2

