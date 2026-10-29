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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.06, 0.00, 0.00]),
    Wall(corner1=[4.06, 0.00, 0.00], corner2=[4.06, 3.84, 0.00]),
    Wall(corner1=[4.06, 3.84, 0.00], corner2=[0.00, 3.84, 0.00]),
    Wall(corner1=[0.00, 3.84, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
side_table_A = Assets(description="A sleek black nightstand with a minimalist design, featuring a single drawer with a round handle. It has a rectangular top and sturdy legs connected by horizontal bars for stability.", size=[0.40, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
king_size_bed = Assets(description="A wooden bed with a simple design featuring a headboard with two horizontal bars and side tables integrated into the frame. It has a light blue patterned mattress and matching pillows.", size=[2.15, 2.50, 1.05], placements=[AssetInstance() for _ in range(1)])
dressing_table = Assets(description="A wooden secretary desk with a slanted top that opens to reveal storage space inside. It features two drawers with round knobs and four tapered legs.", size=[0.45, 0.85, 1.00], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="A wooden wardrobe with sliding doors and internal shelves for storage.", size=[0.60, 1.60, 2.10], placements=[AssetInstance() for _ in range(1)])
floor_lamp = Assets(description="A tall floor lamp with a rectangular lampshade and a decorative tassel hanging from its frame.", size=[0.35, 0.35, 1.65], placements=[AssetInstance() for _ in range(1)])
dressing_chair = Assets(description="A decorative chair with a metal frame and a cushioned seat. The backrest features an intricate floral design made of metal.", size=[0.50, 0.45, 0.90], placements=[AssetInstance() for _ in range(1)])
side_table_B = Assets(description="A sleek black nightstand with a minimalist design, featuring a single drawer with a round handle. It has a rectangular top and sturdy legs connected by horizontal bars for stability.", size=[0.40, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])

side_table_A[0].instance_id = 'side_table_A_0'
king_size_bed[0].instance_id = 'king_size_bed_0'
dressing_table[0].instance_id = 'dressing_table_0'
wardrobe[0].instance_id = 'wardrobe_0'
floor_lamp[0].instance_id = 'floor_lamp_0'
dressing_chair[0].instance_id = 'dressing_chair_0'
side_table_B[0].instance_id = 'side_table_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

side_table_A[0].position = [0.8065114745728248, 1.293695822848067, 0.275]
side_table_A[0].rotation = [0, 0, 0]
king_size_bed[0].position = [3.2464679908743936, 3.1236714848990914, 0.525]
king_size_bed[0].rotation = [0, 0, 0]
dressing_table[0].position = [2.333621851319298, 0.060953235377218036, 0.5]
dressing_table[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.5084865677524063, 2.1189612126123403, 1.05]
wardrobe[0].rotation = [0, 0, 0]
floor_lamp[0].position = [0.603823100946371, 0.818273833434514, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
dressing_chair[0].position = [0.5727358228135351, 1.4985621659340331, 0.45]
dressing_chair[0].rotation = [0, 0, 0]
side_table_B[0].position = [0.3478530524428699, 0.960157015262815, 0.275]
side_table_B[0].rotation = [0, 0, 0]
side_table_A[0].position = [0.8065114745728248, 1.293695822848067, 0.275]
side_table_A[0].rotation = [0, 0, 0]
king_size_bed[0].position = [3.2464679908743936, 3.1236714848990914, 0.525]
king_size_bed[0].rotation = [0, 0, 0]
dressing_table[0].position = [2.333621851319298, 0.060953235377218036, 0.5]
dressing_table[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.5084865677524063, 2.1189612126123403, 1.05]
wardrobe[0].rotation = [0, 0, 0]
floor_lamp[0].position = [0.603823100946371, 0.818273833434514, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
dressing_chair[0].position = [0.5727358228135351, 1.4985621659340331, 0.45]
dressing_chair[0].rotation = [0, 0, 0]
side_table_B[0].position = [0.3478530524428699, 0.960157015262815, 0.275]
side_table_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the actual wall coordinates: the room occupies [0, 4.06] x [0, 3.84].
# The bed faces south, with its head against the north wall. Its rotated
# footprint is 2.50 m wide by 2.15 m deep, leaving a clear southern aisle.
king_size_bed[0].position = [2.03, 2.765, 0.525]
king_size_bed[0].rotation = [0, 0, radians(-90)]

# Place both nightstands alongside the head of the bed, not in the aisle.
side_table_A[0].position = [0.43, 3.64, 0.275]
side_table_A[0].rotation = [0, 0, radians(-90)]
side_table_B[0].position = [3.63, 3.64, 0.275]
side_table_B[0].rotation = [0, 0, radians(-90)]

# The dressing table backs onto the west wall, above the doorway.
# Its footprint begins at y=0.975, clear of the door opening (y=0.08..0.90).
dressing_table[0].position = [0.225, 1.40, 0.50]
dressing_table[0].rotation = [0, 0, 0]

# The chair faces the dressing table and sits just south of the bed footprint.
dressing_chair[0].position = [0.95, 1.40, 0.45]
dressing_chair[0].rotation = [0, 0, radians(180)]

# Keep tall storage against the east wall, away from the south-wall window.
wardrobe[0].position = [3.76, 0.85, 1.05]
wardrobe[0].rotation = [0, 0, radians(180)]

# A reading lamp occupies the free strip west of the bed.
floor_lamp[0].position = [0.25, 2.60, 0.825]
floor_lamp[0].rotation = [0, 0, 0]

# Prioritize wall relationships and useful facing directions.
solver.against_wall(king_size_bed[0], walls[2])
solver.against_wall(dressing_table[0], walls[3])
solver.against_wall(wardrobe[0], walls[1])
solver.against_wall(side_table_A[0], walls[2])
solver.against_wall(side_table_B[0], walls[2])

solver.point_towards(dressing_chair[0], dressing_table[0])
solver.align_with(side_table_A[0], king_size_bed[0])
solver.align_with(side_table_B[0], king_size_bed[0])
solver.point_towards(
    floor_lamp[0],
    AssetInstance(position=[2.03, 2.60, 0.825])
)

# Fixed layout references preserve the non-overlapping footprints, the clear
# entrance, and the window access. Each reference is a constraint target,
# not an additional scene asset.
for placed_instance, target_position, target_yaw in [
    (king_size_bed[0], [2.03, 2.765, 0.525], -90),
    (side_table_A[0], [0.43, 3.64, 0.275], -90),
    (side_table_B[0], [3.63, 3.64, 0.275], -90),
    (dressing_table[0], [0.225, 1.40, 0.50], 0),
    (dressing_chair[0], [0.95, 1.40, 0.45], 180),
    (wardrobe[0], [3.76, 0.85, 1.05], 180),
    (floor_lamp[0], [0.25, 2.60, 0.825], 0),
]:
    solver.distance_constraint(
        placed_instance,
        AssetInstance(position=target_position),
        0, 0, weight=10
    )
    solver.align_with(
        placed_instance,
        AssetInstance(rotation=[0, 0, radians(target_yaw)])
    )

# All listed objects are floor-standing; no on_top_of constraint is needed.

solver.constraints = []
wardrobe[0].position = [3.756389856338501, 0.8500000238418579, 1.0499999523162842]
wardrobe[0].rotation = [0, 0, -3.141592610020817]
wardrobe[0].optimize = 2
dressing_chair[0].position = [0.949999988079071, 1.399999976158142, 0.44999998807907104]
dressing_chair[0].rotation = [0, 0, -3.1290262823329655]
dressing_chair[0].optimize = 2
floor_lamp[0].position = [0.25, 2.5999999046325684, 0.824999988079071]
floor_lamp[0].rotation = [0, 0, 0.01256637125682779]
floor_lamp[0].optimize = 2
side_table_A[0].position = [0.4300000071525574, 3.64421010017395, 0.2750000059604645]
side_table_A[0].rotation = [0, 0, -1.5707962829400903]
side_table_A[0].optimize = 2
side_table_B[0].position = [3.630000114440918, 3.64421010017395, 0.2750000059604645]
side_table_B[0].rotation = [0, 0, -1.5707962829400903]
side_table_B[0].optimize = 2
king_size_bed[0].position = [2.0299999713897705, 2.769209861755371, 0.5249999761581421]
king_size_bed[0].rotation = [0, 0, -1.5707963085546437]
king_size_bed[0].optimize = 2
dressing_table[0].position = [0.22499999403953552, 1.399999976158142, 0.5]
dressing_table[0].rotation = [0, 0, 4.122386466220041e-08]
dressing_table[0].optimize = 2

