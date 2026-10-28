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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.00, 0.00, 0.00]),
    Wall(corner1=[4.00, 0.00, 0.00], corner2=[4.00, 4.00, 0.00]),
    Wall(corner1=[4.00, 4.00, 0.00], corner2=[0.00, 4.00, 0.00]),
    Wall(corner1=[0.00, 4.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
wall_art_A = Assets(description="A painting done in relief on a board of wood.", size=[0.05, 0.80, 0.60], placements=[AssetInstance() for _ in range(1)])
wall_art_B = Assets(description="A painting done in relief on a board of wood.", size=[0.05, 0.80, 0.60], placements=[AssetInstance() for _ in range(1)])
table_lamp_A = Assets(description="table lamp", size=[0.30, 0.30, 0.55], placements=[AssetInstance() for _ in range(1)])
wall_tv = Assets(description="A boxy black television with bright white screen.", size=[0.12, 1.10, 0.65], placements=[AssetInstance() for _ in range(1)])
desk_lamp = Assets(description="desk lamp", size=[0.35, 0.20, 0.45], placements=[AssetInstance() for _ in range(1)])
table_lamp_B = Assets(description="table lamp", size=[0.30, 0.30, 0.55], placements=[AssetInstance() for _ in range(1)])
wall_mirror = Assets(description="A rectangular mirror in a brown wooden frame.", size=[0.05, 0.70, 1.00], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.60, 1.20, 2.00], placements=[AssetInstance() for _ in range(1)])
luggage_bench = Assets(description="luggage bench", size=[0.45, 1.10, 0.50], placements=[AssetInstance() for _ in range(1)])
desk_chair = Assets(description="desk chair", size=[0.55, 0.55, 0.90], placements=[AssetInstance() for _ in range(1)])
bedside_table_A = Assets(description="bedside table", size=[0.45, 0.50, 0.60], placements=[AssetInstance() for _ in range(1)])
writing_desk = Assets(description="writing desk", size=[0.60, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
bed_pillow = Assets(description="bed pillow", size=[0.40, 0.65, 0.15], placements=[AssetInstance() for _ in range(1)])
queen_bed = Assets(description="queen bed", size=[2.00, 1.60, 0.55], placements=[AssetInstance() for _ in range(1)])
bedside_table_B = Assets(description="bedside table", size=[0.45, 0.50, 0.60], placements=[AssetInstance() for _ in range(1)])

wall_art_A[0].instance_id = 'wall_art_A_0'
wall_art_B[0].instance_id = 'wall_art_B_0'
table_lamp_A[0].instance_id = 'table_lamp_A_0'
wall_tv[0].instance_id = 'wall_tv_0'
desk_lamp[0].instance_id = 'desk_lamp_0'
table_lamp_B[0].instance_id = 'table_lamp_B_0'
wall_mirror[0].instance_id = 'wall_mirror_0'
wardrobe[0].instance_id = 'wardrobe_0'
luggage_bench[0].instance_id = 'luggage_bench_0'
desk_chair[0].instance_id = 'desk_chair_0'
bedside_table_A[0].instance_id = 'bedside_table_A_0'
writing_desk[0].instance_id = 'writing_desk_0'
bed_pillow[0].instance_id = 'bed_pillow_0'
queen_bed[0].instance_id = 'queen_bed_0'
bedside_table_B[0].instance_id = 'bedside_table_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

wall_art_A[0].position = [3.4998903225265585, 2.7762975622495993, 0.3]
wall_art_A[0].rotation = [0, 0, 0]
wall_art_B[0].position = [0.38399403029923906, 2.953115145989655, 0.3]
wall_art_B[0].rotation = [0, 0, 0]
table_lamp_A[0].position = [1.5343123567831727, 2.4619321249252026, 0.275]
table_lamp_A[0].rotation = [0, 0, 0]
wall_tv[0].position = [1.083630827961524, 0.5940760181475957, 0.325]
wall_tv[0].rotation = [0, 0, 0]
desk_lamp[0].position = [0.4380297620670479, 3.113557954275963, 0.225]
desk_lamp[0].rotation = [0, 0, 0]
table_lamp_B[0].position = [0.8466308220487653, 1.7354517363468438, 0.275]
table_lamp_B[0].rotation = [0, 0, 0]
wall_mirror[0].position = [1.084394252981407, 2.597737915802173, 0.5]
wall_mirror[0].rotation = [0, 0, 0]
wardrobe[0].position = [1.472736008808175, 2.2174106985664666, 1.0]
wardrobe[0].rotation = [0, 0, 0]
luggage_bench[0].position = [0.4227909194354136, 1.8634485125890987, 0.25]
luggage_bench[0].rotation = [0, 0, 0]
desk_chair[0].position = [2.201045923342692, 1.3743928301616584, 0.45]
desk_chair[0].rotation = [0, 0, 0]
bedside_table_A[0].position = [2.1929197262511804, 1.9969311985224443, 0.3]
bedside_table_A[0].rotation = [0, 0, 0]
writing_desk[0].position = [0.8604298856717478, 1.4211162834760374, 0.375]
writing_desk[0].rotation = [0, 0, 0]
bed_pillow[0].position = [0.40401096694113914, 1.02488730932392, 0.075]
bed_pillow[0].rotation = [0, 0, 0]
queen_bed[0].position = [1.7467186477722025, 1.6413105808201838, 0.275]
queen_bed[0].rotation = [0, 0, 0]
bedside_table_B[0].position = [3.1394997860871268, 0.945361082346603, 0.3]
bedside_table_B[0].rotation = [0, 0, 0]
wall_art_A[0].position = [3.4998903225265585, 2.7762975622495993, 0.3]
wall_art_A[0].rotation = [0, 0, 0]
wall_art_B[0].position = [0.38399403029923906, 2.953115145989655, 0.3]
wall_art_B[0].rotation = [0, 0, 0]
table_lamp_A[0].position = [1.5343123567831727, 2.4619321249252026, 0.275]
table_lamp_A[0].rotation = [0, 0, 0]
wall_tv[0].position = [1.083630827961524, 0.5940760181475957, 0.325]
wall_tv[0].rotation = [0, 0, 0]
desk_lamp[0].position = [0.4380297620670479, 3.113557954275963, 0.225]
desk_lamp[0].rotation = [0, 0, 0]
table_lamp_B[0].position = [0.8466308220487653, 1.7354517363468438, 0.275]
table_lamp_B[0].rotation = [0, 0, 0]
wall_mirror[0].position = [1.084394252981407, 2.597737915802173, 0.5]
wall_mirror[0].rotation = [0, 0, 0]
wardrobe[0].position = [1.472736008808175, 2.2174106985664666, 1.0]
wardrobe[0].rotation = [0, 0, 0]
luggage_bench[0].position = [0.4227909194354136, 1.8634485125890987, 0.25]
luggage_bench[0].rotation = [0, 0, 0]
desk_chair[0].position = [2.201045923342692, 1.3743928301616584, 0.45]
desk_chair[0].rotation = [0, 0, 0]
bedside_table_A[0].position = [2.1929197262511804, 1.9969311985224443, 0.3]
bedside_table_A[0].rotation = [0, 0, 0]
writing_desk[0].position = [0.8604298856717478, 1.4211162834760374, 0.375]
writing_desk[0].rotation = [0, 0, 0]
bed_pillow[0].position = [0.40401096694113914, 1.02488730932392, 0.075]
bed_pillow[0].rotation = [0, 0, 0]
queen_bed[0].position = [1.7467186477722025, 1.6413105808201838, 0.275]
queen_bed[0].rotation = [0, 0, 0]
bedside_table_B[0].position = [3.1394997860871268, 0.945361082346603, 0.3]
bedside_table_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed reference points preserve the intended zones while allowing the solver
# to make small feasibility adjustments.
bed_anchor = AssetInstance(position=[1.00, 1.15, 0.275])
bench_anchor = AssetInstance(position=[2.30, 1.15, 0.25])
wardrobe_anchor = AssetInstance(position=[3.70, 0.65, 1.00])
desk_anchor = AssetInstance(position=[3.30, 3.70, 0.375])
table_A_anchor = AssetInstance(position=[2.63, 2.70, 0.30])
chair_anchor = AssetInstance(position=[3.20, 2.70, 0.45])
table_B_anchor = AssetInstance(position=[3.77, 2.70, 0.30])
room_center = AssetInstance(position=[2.00, 2.00, 1.20])

# The bed is placed against the left wall, away from both windows and the door.
queen_bed[0].position = [1.00, 1.15, 0.275]
queen_bed[0].rotation = [0, 0, radians(0)]
solver.against_wall(queen_bed[0], walls[3])
solver.distance_constraint(
    queen_bed[0], bed_anchor, 0.0, 0.0, weight=10
)
solver.point_towards(queen_bed[0], room_center)

# The pillow rests near the head of the bed.
bed_pillow[0].position = [0.42, 1.15, 0.625]
bed_pillow[0].rotation = [0, 0, radians(0)]
solver.on_top_of(bed_pillow[0], queen_bed[0])
solver.distance_constraint(
    bed_pillow[0], queen_bed[0], 0.35, 0.75, weight=10
)
solver.align_with(bed_pillow[0], queen_bed[0])

# The luggage bench sits at the foot of the bed with a small circulation gap.
luggage_bench[0].position = [2.30, 1.15, 0.25]
luggage_bench[0].rotation = [0, 0, radians(0)]
solver.distance_constraint(
    luggage_bench[0], bench_anchor, 0.0, 0.0, weight=10
)
solver.distance_constraint(
    luggage_bench[0], queen_bed[0], 1.30, 1.35, weight=10
)
solver.align_with(luggage_bench[0], queen_bed[0])

# The wardrobe occupies the lower part of the right wall without covering a window.
wardrobe[0].position = [3.70, 0.65, 1.00]
wardrobe[0].rotation = [0, 0, radians(180)]
solver.against_wall(wardrobe[0], walls[1])
solver.distance_constraint(
    wardrobe[0], wardrobe_anchor, 0.0, 0.0, weight=10
)
solver.point_towards(wardrobe[0], room_center)

# The television is wall-mounted above the open area next to the wardrobe.
wall_tv[0].position = [3.94, 1.85, 1.55]
wall_tv[0].rotation = [0, 0, radians(180)]
solver.against_wall(wall_tv[0], walls[1])
solver.distance_constraint(
    wall_tv[0],
    AssetInstance(position=[3.94, 1.85, 1.55]),
    0.0,
    0.0,
    weight=10,
)
solver.point_towards(wall_tv[0], room_center)

# The mirror is mounted on the left wall beyond the bed.
wall_mirror[0].position = [0.025, 3.05, 1.55]
wall_mirror[0].rotation = [0, 0, radians(0)]
solver.against_wall(wall_mirror[0], walls[3])
solver.distance_constraint(
    wall_mirror[0],
    AssetInstance(position=[0.025, 3.05, 1.55]),
    0.0,
    0.0,
    weight=10,
)
solver.point_towards(wall_mirror[0], room_center)

# One artwork uses the short upper-left wall section, clear of the doorway.
wall_art_A[0].position = [0.65, 3.975, 1.65]
wall_art_A[0].rotation = [0, 0, radians(-90)]
solver.against_wall(wall_art_A[0], walls[2])
solver.distance_constraint(
    wall_art_A[0],
    AssetInstance(position=[0.65, 3.975, 1.65]),
    0.0,
    0.0,
    weight=10,
)
solver.point_towards(wall_art_A[0], room_center)

# The second artwork is mounted above the writing area.
wall_art_B[0].position = [3.35, 3.975, 1.65]
wall_art_B[0].rotation = [0, 0, radians(-90)]
solver.against_wall(wall_art_B[0], walls[2])
solver.distance_constraint(
    wall_art_B[0],
    AssetInstance(position=[3.35, 3.975, 1.65]),
    0.0,
    0.0,
    weight=10,
)
solver.point_towards(wall_art_B[0], room_center)

# The two bedside tables and chair form a compact writing-area row.
# Their centers are equally spaced, putting the chair between the tables.
bedside_table_A[0].position = [2.63, 2.70, 0.30]
bedside_table_A[0].rotation = [0, 0, radians(-90)]
solver.distance_constraint(
    bedside_table_A[0], table_A_anchor, 0.0, 0.0, weight=10
)
solver.align_with(bedside_table_A[0], writing_desk[0])

bedside_table_B[0].position = [3.77, 2.70, 0.30]
bedside_table_B[0].rotation = [0, 0, radians(-90)]
solver.distance_constraint(
    bedside_table_B[0], table_B_anchor, 0.0, 0.0, weight=10
)
solver.align_with(bedside_table_B[0], bedside_table_A[0])

desk_chair[0].position = [3.20, 2.70, 0.45]
desk_chair[0].rotation = [0, 0, radians(90)]
solver.distance_constraint(
    desk_chair[0], bedside_table_A[0], 0.57, 0.57, weight=10
)
solver.distance_constraint(
    desk_chair[0], bedside_table_B[0], 0.57, 0.57, weight=10
)
solver.distance_constraint(
    desk_chair[0], chair_anchor, 0.0, 0.0, weight=10
)
solver.point_towards(desk_chair[0], writing_desk[0])

# The desk occupies the upper-right wall section, outside the door opening.
# It faces bedside_table_A as required.
writing_desk[0].position = [3.30, 3.70, 0.375]
writing_desk[0].rotation = [0, 0, radians(-124)]
solver.against_wall(writing_desk[0], walls[2])
solver.distance_constraint(
    writing_desk[0], desk_anchor, 0.0, 0.0, weight=10
)
solver.point_towards(writing_desk[0], bedside_table_A[0])

# The desk lamp is supported by the writing desk.
desk_lamp[0].position = [3.47, 3.69, 0.975]
desk_lamp[0].rotation = [0, 0, radians(-124)]
solver.on_top_of(desk_lamp[0], writing_desk[0])
solver.distance_constraint(
    desk_lamp[0], writing_desk[0], 0.60, 0.75, weight=10
)
solver.align_with(desk_lamp[0], writing_desk[0])

# Each table lamp is placed on a table; table_lamp_B is specifically placed
# on bedside_table_B as required by the asset-ID relationship.
table_lamp_A[0].position = [2.63, 2.70, 0.875]
table_lamp_A[0].rotation = [0, 0, radians(-90)]
solver.on_top_of(table_lamp_A[0], bedside_table_A[0])
solver.distance_constraint(
    table_lamp_A[0], bedside_table_A[0], 0.575, 0.575, weight=10
)
solver.align_with(table_lamp_A[0], bedside_table_A[0])

table_lamp_B[0].position = [3.77, 2.70, 0.875]
table_lamp_B[0].rotation = [0, 0, radians(-90)]
solver.on_top_of(table_lamp_B[0], bedside_table_B[0])
solver.distance_constraint(
    table_lamp_B[0], bedside_table_B[0], 0.575, 0.575, weight=10
)
solver.align_with(table_lamp_B[0], bedside_table_B[0])

solver.constraints = []
wall_tv[0].position = [3.9399237632751465, 1.850000023841858, 0.32499998807907104]
wall_tv[0].rotation = [0, 0, -3.137377890871723]
wall_tv[0].optimize = 2
writing_desk[0].position = [3.299999952316284, 3.4788079261779785, 0.375]
writing_desk[0].rotation = [0, 0, -1.996951088282489]
writing_desk[0].optimize = 2
bedside_table_B[0].position = [3.742863178253174, 2.700000047683716, 0.30000001192092896]
bedside_table_B[0].rotation = [0, 0, -1.6196735933214672]
bedside_table_B[0].optimize = 2
bedside_table_A[0].position = [2.630000114440918, 2.700000047683716, 0.30000001192092896]
bedside_table_A[0].rotation = [0, 0, -1.6449929279895048]
bedside_table_A[0].optimize = 2
luggage_bench[0].position = [2.358107566833496, 1.149999976158142, 0.25]
luggage_bench[0].rotation = [0, 0, -0.026111657329667266]
luggage_bench[0].optimize = 2
wall_art_B[0].position = [3.3499999046325684, 3.977504253387451, 0.30000001192092896]
wall_art_B[0].rotation = [0, 0, -1.5665822241533673]
wall_art_B[0].optimize = 2
desk_lamp[0].position = [3.5328636169433594, 3.7025604248046875, 0.9750000238418579]
desk_lamp[0].rotation = [0, 0, -2.0109167089851026]
desk_lamp[0].optimize = 2
wall_art_A[0].position = [0.6499999761581421, 3.977504253387451, 0.30000001192092896]
wall_art_A[0].rotation = [0, 0, -1.5665822241533673]
wall_art_A[0].optimize = 2
table_lamp_A[0].position = [2.630000114440918, 2.700000047683716, 0.875]
table_lamp_A[0].rotation = [0, 0, -1.6098540967695218]
table_lamp_A[0].optimize = 2
bed_pillow[0].position = [0.3136450946331024, 1.149999976158142, 0.625]
bed_pillow[0].rotation = [0, 0, -0.026111657329667266]
bed_pillow[0].optimize = 2
wall_mirror[0].position = [0.022541524842381477, 3.049999952316284, 0.5]
wall_mirror[0].rotation = [0, 0, 0.004214081229184454]
wall_mirror[0].optimize = 2
table_lamp_B[0].position = [3.8475210666656494, 2.700000047683716, 0.875]
table_lamp_B[0].rotation = [0, 0, -1.5874631404143231]
table_lamp_B[0].optimize = 2
desk_chair[0].position = [3.175814151763916, 2.700000047683716, 0.44999998807907104]
desk_chair[0].rotation = [0, 0, 1.586504290712113]
desk_chair[0].optimize = 2
wardrobe[0].position = [3.6999003887176514, 0.6499999761581421, 1.0]
wardrobe[0].rotation = [0, 0, -3.137374813348266]
wardrobe[0].optimize = 2
queen_bed[0].position = [1.0032200813293457, 1.149999976158142, 0.2750000059604645]
queen_bed[0].rotation = [0, 0, -0.0045558384740347025]
queen_bed[0].optimize = 2

