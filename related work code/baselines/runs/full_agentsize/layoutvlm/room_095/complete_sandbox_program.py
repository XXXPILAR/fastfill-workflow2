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
    Wall(corner1=[0.00, 5.27, 0.00], corner2=[0.00, 1.99, 0.00]),
    Wall(corner1=[0.00, 1.99, 0.00], corner2=[0.04, 1.95, 0.00]),
    Wall(corner1=[0.04, 1.95, 0.00], corner2=[2.85, 0.00, 0.00]),
    Wall(corner1=[2.85, 0.00, 0.00], corner2=[4.18, 0.00, 0.00]),
    Wall(corner1=[4.18, 0.00, 0.00], corner2=[4.22, 0.04, 0.00]),
    Wall(corner1=[4.22, 0.04, 0.00], corner2=[4.22, 5.27, 0.00]),
    Wall(corner1=[4.22, 5.27, 0.00], corner2=[4.18, 5.31, 0.00]),
    Wall(corner1=[4.18, 5.31, 0.00], corner2=[0.04, 5.31, 0.00]),
    Wall(corner1=[0.04, 5.31, 0.00], corner2=[0.00, 5.27, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
chair_A = Assets(description="chair", size=[0.68, 0.62, 0.86], placements=[AssetInstance() for _ in range(1)])
cup = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
couch_A = Assets(description="couch", size=[0.88, 1.95, 0.84], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.68, 0.62, 0.86], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="lamp", size=[0.32, 0.32, 0.58], placements=[AssetInstance() for _ in range(1)])
table_A = Assets(description="table", size=[0.65, 1.20, 0.45], placements=[AssetInstance() for _ in range(1)])
couch_B = Assets(description="couch", size=[0.88, 1.95, 0.84], placements=[AssetInstance() for _ in range(1)])
table_B = Assets(description="table", size=[0.55, 0.55, 0.55], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.32, 0.32, 0.58], placements=[AssetInstance() for _ in range(1)])
table_C = Assets(description="table", size=[0.55, 0.55, 0.55], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="chair", size=[0.68, 0.62, 0.86], placements=[AssetInstance() for _ in range(1)])
book = Assets(description="book", size=[0.16, 0.22, 0.03], placements=[AssetInstance() for _ in range(1)])
paper_A = Assets(description="paper", size=[0.21, 0.30, 0.00], placements=[AssetInstance() for _ in range(1)])
toy = Assets(description="toy", size=[0.12, 0.18, 0.15], placements=[AssetInstance() for _ in range(1)])
paper_B = Assets(description="paper", size=[0.21, 0.30, 0.00], placements=[AssetInstance() for _ in range(1)])

chair_A[0].instance_id = 'chair_A_0'
cup[0].instance_id = 'cup_0'
couch_A[0].instance_id = 'couch_A_0'
chair_B[0].instance_id = 'chair_B_0'
lamp_A[0].instance_id = 'lamp_A_0'
table_A[0].instance_id = 'table_A_0'
couch_B[0].instance_id = 'couch_B_0'
table_B[0].instance_id = 'table_B_0'
lamp_B[0].instance_id = 'lamp_B_0'
table_C[0].instance_id = 'table_C_0'
chair_C[0].instance_id = 'chair_C_0'
book[0].instance_id = 'book_0'
paper_A[0].instance_id = 'paper_A_0'
toy[0].instance_id = 'toy_0'
paper_B[0].instance_id = 'paper_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'
walls[8].instance_id = 'walls_8'

chair_A[0].position = [1.786488678155487, 4.279061055711034, 0.43]
chair_A[0].rotation = [0, 0, 0]
cup[0].position = [2.663467684987722, 0.4474106145840304, 0.055]
cup[0].rotation = [0, 0, 0]
couch_A[0].position = [3.213020535347374, 0.5680900314653228, 0.42]
couch_A[0].rotation = [0, 0, 0]
chair_B[0].position = [0.1630973054328248, 3.8981722379328754, 0.43]
chair_B[0].rotation = [0, 0, 0]
lamp_A[0].position = [2.890126234941359, 1.7271869552412573, 0.29]
lamp_A[0].rotation = [0, 0, 0]
table_A[0].position = [2.235021913972358, 1.7832674617149893, 0.225]
table_A[0].rotation = [0, 0, 0]
couch_B[0].position = [2.9590213428446406, 1.8831427707076887, 0.42]
couch_B[0].rotation = [0, 0, 0]
table_B[0].position = [0.052605241119825195, 2.6847914465866625, 0.275]
table_B[0].rotation = [0, 0, 0]
lamp_B[0].position = [4.195099454832701, 4.849545808068803, 0.29]
lamp_B[0].rotation = [0, 0, 0]
table_C[0].position = [3.089672681437202, 0.13798678769623646, 0.275]
table_C[0].rotation = [0, 0, 0]
chair_C[0].position = [3.646935107087667, 3.5681823788533085, 0.43]
chair_C[0].rotation = [0, 0, 0]
book[0].position = [2.3868387685713737, 2.331384517906646, 0.015]
book[0].rotation = [0, 0, 0]
paper_A[0].position = [0.6868456064559056, 3.0954847940113575, 0.0005]
paper_A[0].rotation = [0, 0, 0]
toy[0].position = [0.7890642668110616, 5.142873315177327, 0.075]
toy[0].rotation = [0, 0, 0]
paper_B[0].position = [0.4286924794377167, 3.802989859540084, 0.0005]
paper_B[0].rotation = [0, 0, 0]
chair_A[0].position = [1.786488678155487, 4.279061055711034, 0.43]
chair_A[0].rotation = [0, 0, 0]
cup[0].position = [2.663467684987722, 0.4474106145840304, 0.055]
cup[0].rotation = [0, 0, 0]
couch_A[0].position = [3.213020535347374, 0.5680900314653228, 0.42]
couch_A[0].rotation = [0, 0, 0]
chair_B[0].position = [0.1630973054328248, 3.8981722379328754, 0.43]
chair_B[0].rotation = [0, 0, 0]
lamp_A[0].position = [2.890126234941359, 1.7271869552412573, 0.29]
lamp_A[0].rotation = [0, 0, 0]
table_A[0].position = [2.235021913972358, 1.7832674617149893, 0.225]
table_A[0].rotation = [0, 0, 0]
couch_B[0].position = [2.9590213428446406, 1.8831427707076887, 0.42]
couch_B[0].rotation = [0, 0, 0]
table_B[0].position = [0.052605241119825195, 2.6847914465866625, 0.275]
table_B[0].rotation = [0, 0, 0]
lamp_B[0].position = [4.195099454832701, 4.849545808068803, 0.29]
lamp_B[0].rotation = [0, 0, 0]
table_C[0].position = [3.089672681437202, 0.13798678769623646, 0.275]
table_C[0].rotation = [0, 0, 0]
chair_C[0].position = [3.646935107087667, 3.5681823788533085, 0.43]
chair_C[0].rotation = [0, 0, 0]
book[0].position = [2.3868387685713737, 2.331384517906646, 0.015]
book[0].rotation = [0, 0, 0]
paper_A[0].position = [0.6868456064559056, 3.0954847940113575, 0.0005]
paper_A[0].rotation = [0, 0, 0]
toy[0].position = [0.7890642668110616, 5.142873315177327, 0.075]
toy[0].rotation = [0, 0, 0]
paper_B[0].position = [0.4286924794377167, 3.802989859540084, 0.0005]
paper_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Create a conversational seating area in the broad upper-right portion of the
# room, leaving the angled lower-left side open as a circulation path.
chair_A[0].position = [1.70, 3.40, 0.43]
chair_A[0].rotation = [0, 0, radians(3)]

chair_B[0].position = [2.55, 2.30, 0.43]
chair_B[0].rotation = [0, 0, radians(85)]

chair_C[0].position = [1.25, 2.55, 0.43]
chair_C[0].rotation = [0, 0, radians(33)]

# The two couches form an L-shaped seating arrangement against the right and
# upper walls. Their centers account for their rotated footprints.
couch_A[0].position = [3.78, 4.00, 0.42]
couch_A[0].rotation = [0, 0, radians(180)]

couch_B[0].position = [2.20, 4.87, 0.42]
couch_B[0].rotation = [0, 0, radians(-90)]

# The long table is the central coffee table for the complete seating group.
table_A[0].position = [2.65, 3.45, 0.225]
table_A[0].rotation = [0, 0, 0]

# Side tables occupy otherwise-unused wall-side spaces without blocking seats.
table_B[0].position = [3.945, 2.58, 0.275]
table_B[0].rotation = [0, 0, 0]

table_C[0].position = [0.275, 4.95, 0.275]
table_C[0].rotation = [0, 0, 0]

# Each lamp is centered on its corresponding side table.
lamp_A[0].position = [3.945, 2.58, 0.84]
lamp_A[0].rotation = [0, 0, 0]

lamp_B[0].position = [0.275, 4.95, 0.84]
lamp_B[0].rotation = [0, 0, 0]

# Distribute the small objects over the coffee-table surface with non-overlapping
# footprints. Their z coordinates place their bottoms on the 0.45 m tabletop.
cup[0].position = [2.50, 3.15, 0.505]
cup[0].rotation = [0, 0, 0]

book[0].position = [2.72, 3.25, 0.465]
book[0].rotation = [0, 0, radians(10)]

paper_A[0].position = [2.52, 3.58, 0.45]
paper_A[0].rotation = [0, 0, radians(-8)]

paper_B[0].position = [2.76, 3.66, 0.45]
paper_B[0].rotation = [0, 0, radians(8)]

toy[0].position = [2.68, 3.92, 0.525]
toy[0].rotation = [0, 0, radians(-5)]


# Fixed references preserve the intentionally collision-free zones while still
# allowing the semantic furniture relationships below to guide adjustment.
chair_A_anchor = AssetInstance(position=[1.70, 3.40, 0.43])
chair_B_anchor = AssetInstance(position=[2.55, 2.30, 0.43])
chair_C_anchor = AssetInstance(position=[1.25, 2.55, 0.43])
couch_A_anchor = AssetInstance(position=[3.78, 4.00, 0.42])
couch_B_anchor = AssetInstance(position=[2.20, 4.87, 0.42])
coffee_table_anchor = AssetInstance(position=[2.65, 3.45, 0.225])
side_table_B_anchor = AssetInstance(position=[3.945, 2.58, 0.275])
side_table_C_anchor = AssetInstance(position=[0.275, 4.95, 0.275])
layout_axis = AssetInstance(rotation=[0, 0, 0])

# Keep the couches against their respective walls, then retain their safe
# positions. Both couches face inward toward the coffee table.
solver.against_wall(couch_A[0], walls[5])
solver.distance_constraint(
    couch_A[0], couch_A_anchor, 0, 0, weight=10
)
solver.point_towards(couch_A[0], table_A[0])

solver.against_wall(couch_B[0], walls[7])
solver.distance_constraint(
    couch_B[0], couch_B_anchor, 0, 0, weight=10
)
solver.point_towards(couch_B[0], table_A[0])

# Anchor the coffee table at the center of the seating group and align its long
# direction with the room axes.
solver.distance_constraint(
    table_A[0], coffee_table_anchor, 0, 0, weight=10
)
solver.align_with(table_A[0], layout_axis)

# Keep each chair in its allocated clear zone and oriented toward the table.
# The secondary distance ranges preserve useful conversational spacing.
solver.distance_constraint(
    chair_A[0], chair_A_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    chair_A[0], table_A[0], 0.90, 1.05, weight=1
)
solver.point_towards(chair_A[0], table_A[0])

solver.distance_constraint(
    chair_B[0], chair_B_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    chair_B[0], table_A[0], 1.10, 1.25, weight=1
)
solver.point_towards(chair_B[0], table_A[0])

solver.distance_constraint(
    chair_C[0], chair_C_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    chair_C[0], table_A[0], 1.55, 1.75, weight=1
)
solver.point_towards(chair_C[0], table_A[0])

# Side tables remain against the walls and aligned with the room.
solver.against_wall(table_B[0], walls[5])
solver.distance_constraint(
    table_B[0], side_table_B_anchor, 0, 0, weight=10
)
solver.align_with(table_B[0], layout_axis)

solver.against_wall(table_C[0], walls[0])
solver.distance_constraint(
    table_C[0], side_table_C_anchor, 0, 0, weight=10
)
solver.align_with(table_C[0], layout_axis)

# Lamps must stay on their assigned side tables. The center-distance constraints
# are position-based and allow the vertical offset produced by on_top_of.
solver.on_top_of(lamp_A[0], table_B[0])
solver.distance_constraint(
    lamp_A[0], table_B[0], 0.54, 0.59, weight=10
)
solver.align_with(lamp_A[0], table_B[0])

solver.on_top_of(lamp_B[0], table_C[0])
solver.distance_constraint(
    lamp_B[0], table_C[0], 0.54, 0.59, weight=10
)
solver.align_with(lamp_B[0], table_C[0])

# Every small object remains on the coffee table. Tight center-distance bands,
# together with the initialized positions, retain their separated arrangement.
solver.on_top_of(cup[0], table_A[0])
solver.distance_constraint(
    cup[0], table_A[0], 0.41, 0.46, weight=10
)
solver.align_with(cup[0], table_A[0])

solver.on_top_of(book[0], table_A[0])
solver.distance_constraint(
    book[0], table_A[0], 0.29, 0.35, weight=10
)
solver.align_with(book[0], table_A[0], angle=10)

solver.on_top_of(paper_A[0], table_A[0])
solver.distance_constraint(
    paper_A[0], table_A[0], 0.27, 0.32, weight=10
)
solver.align_with(paper_A[0], table_A[0], angle=-8)

solver.on_top_of(paper_B[0], table_A[0])
solver.distance_constraint(
    paper_B[0], table_A[0], 0.30, 0.35, weight=10
)
solver.align_with(paper_B[0], table_A[0], angle=8)

solver.on_top_of(toy[0], table_A[0])
solver.distance_constraint(
    toy[0], table_A[0], 0.53, 0.59, weight=10
)
solver.align_with(toy[0], table_A[0], angle=-5)

solver.constraints = []
toy[0].position = [2.748136043548584, 4.01573371887207, 0.5249999761581421]
toy[0].rotation = [0, 0, -0.005585020931203407]
toy[0].optimize = 2
table_C[0].position = [0.27500003576278687, 4.949999809265137, 0.2750000059604645]
table_C[0].rotation = [0, 0, 3.0531366085907724e-08]
table_C[0].optimize = 2
couch_B[0].position = [2.200000047683716, 4.872499465942383, 0.41999998688697815]
couch_B[0].rotation = [0, 0, -1.5707962815005192]
couch_B[0].optimize = 2
chair_C[0].position = [1.25, 2.549999952316284, 0.4300000071525574]
chair_C[0].rotation = [0, 0, 0.5885249943626787]
chair_C[0].optimize = 2
paper_A[0].position = [2.289478302001953, 3.8702895641326904, 0.44999998807907104]
paper_A[0].rotation = [0, 0, -0.05794499177684476]
paper_A[0].optimize = 2
couch_A[0].position = [3.77875018119812, 4.0, 0.41999998688697815]
couch_A[0].rotation = [0, 0, -3.1415926305303876]
couch_A[0].optimize = 2
table_A[0].position = [2.6500000953674316, 3.450000047683716, 0.22499999403953552]
table_A[0].rotation = [0, 0, 0.08168141045923738]
table_A[0].optimize = 2
book[0].position = [2.97354793548584, 3.000765800476074, 0.4649999737739563]
book[0].rotation = [0, 0, 0.25621431321946203]
book[0].optimize = 2
cup[0].position = [2.356016159057617, 3.0065083503723145, 0.5049999952316284]
cup[0].rotation = [0, 0, 0.08168136309662645]
cup[0].optimize = 2
chair_A[0].position = [1.7000000476837158, 3.4000000953674316, 0.4300000071525574]
chair_A[0].rotation = [0, 0, 0.06492624466047128]
chair_A[0].optimize = 2
table_B[0].position = [3.943575620651245, 2.5799999237060547, 0.2750000059604645]
table_B[0].rotation = [0, 0, -3.14025692231392]
table_B[0].optimize = 2
lamp_A[0].position = [3.668943166732788, 2.3046329021453857, 0.8400000333786011]
lamp_A[0].rotation = [0, 0, -3.140199498004901]
lamp_A[0].optimize = 2
lamp_B[0].position = [0.15999996662139893, 4.949999809265137, 0.8400000333786011]
lamp_B[0].rotation = [0, 0, 1.0890360600656574e-07]
lamp_B[0].optimize = 2
chair_B[0].position = [2.549999952316284, 2.299999952316284, 0.4300000071525574]
chair_B[0].rotation = [0, 0, 1.4960962313099773]
chair_B[0].optimize = 2
paper_B[0].position = [2.939025640487671, 3.9030158519744873, 0.44999998807907104]
paper_B[0].rotation = [0, 0, 0.2213076947405211]
paper_B[0].optimize = 2

