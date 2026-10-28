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
side_table_A = Assets(description="A sleek black nightstand with a minimalist design, featuring a single drawer with a round handle. It has a rectangular top and sturdy legs connected by horizontal bars for stability.", size=[0.40, 0.50, 0.60], placements=[AssetInstance() for _ in range(1)])
king_size_bed = Assets(description="A wooden bed with a simple design featuring a headboard with two horizontal bars and side tables integrated into the frame. It has a light blue patterned mattress and matching pillows.", size=[2.15, 3.20, 1.05], placements=[AssetInstance() for _ in range(1)])
dressing_table = Assets(description="A wooden secretary desk with a slanted top that opens to reveal storage space inside. It features two drawers with round knobs and four tapered legs.", size=[0.48, 0.90, 1.05], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="A wooden wardrobe with sliding doors and internal shelves for storage.", size=[0.62, 1.80, 2.20], placements=[AssetInstance() for _ in range(1)])
floor_lamp = Assets(description="A tall floor lamp with a rectangular lampshade and a decorative tassel hanging from its frame.", size=[0.40, 0.40, 1.65], placements=[AssetInstance() for _ in range(1)])
dressing_chair = Assets(description="A decorative chair with a metal frame and a cushioned seat. The backrest features an intricate floral design made of metal.", size=[0.55, 0.50, 0.92], placements=[AssetInstance() for _ in range(1)])
side_table_B = Assets(description="A sleek black nightstand with a minimalist design, featuring a single drawer with a round handle. It has a rectangular top and sturdy legs connected by horizontal bars for stability.", size=[0.40, 0.50, 0.60], placements=[AssetInstance() for _ in range(1)])

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

side_table_A[0].position = [2.9390773361892895, 0.4023088844668149, 0.3]
side_table_A[0].rotation = [0, 0, 0]
king_size_bed[0].position = [3.1472526510895884, 2.3607699059903635, 0.525]
king_size_bed[0].rotation = [0, 0, 0]
dressing_table[0].position = [3.206705123905342, 3.3874645927124125, 0.525]
dressing_table[0].rotation = [0, 0, 0]
wardrobe[0].position = [3.927858591138203, 1.3580712797875552, 1.1]
wardrobe[0].rotation = [0, 0, 0]
floor_lamp[0].position = [2.5589981939905795, 0.3882434386298278, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
dressing_chair[0].position = [2.0026532682133147, 2.031437990363799, 0.46]
dressing_chair[0].rotation = [0, 0, 0]
side_table_B[0].position = [3.970494021624777, 2.2071146036856057, 0.3]
side_table_B[0].rotation = [0, 0, 0]
side_table_A[0].position = [2.9390773361892895, 0.4023088844668149, 0.3]
side_table_A[0].rotation = [0, 0, 0]
king_size_bed[0].position = [3.1472526510895884, 2.3607699059903635, 0.525]
king_size_bed[0].rotation = [0, 0, 0]
dressing_table[0].position = [3.206705123905342, 3.3874645927124125, 0.525]
dressing_table[0].rotation = [0, 0, 0]
wardrobe[0].position = [3.927858591138203, 1.3580712797875552, 1.1]
wardrobe[0].rotation = [0, 0, 0]
floor_lamp[0].position = [2.5589981939905795, 0.3882434386298278, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
dressing_chair[0].position = [2.0026532682133147, 2.031437990363799, 0.46]
dressing_chair[0].rotation = [0, 0, 0]
side_table_B[0].position = [3.970494021624777, 2.2071146036856057, 0.3]
side_table_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the bed against the right wall so that it faces into the room.
# This leaves a generous circulation and dressing zone along the left side,
# while keeping the doorway on the lower-left wall unobstructed.
king_size_bed[0].position = [2.985, 1.92, 0.525]
king_size_bed[0].rotation = [0, 0, radians(180)]

# Place the nightstands beside the two accessible corners of the bed.
side_table_A[0].position = [1.65, 0.30, 0.30]
side_table_A[0].rotation = [0, 0, radians(180)]

side_table_B[0].position = [1.65, 3.54, 0.30]
side_table_B[0].rotation = [0, 0, radians(180)]

# Put the dressing table against the left wall, above the door opening.
# Its chair faces the table and remains outside the bed footprint.
dressing_table[0].position = [0.24, 1.45, 0.525]
dressing_table[0].rotation = [0, 0, radians(0)]

dressing_chair[0].position = [0.80, 1.45, 0.46]
dressing_chair[0].rotation = [0, 0, radians(180)]

# The wardrobe occupies the upper-left wall, away from both the door and window.
wardrobe[0].position = [0.31, 2.94, 1.10]
wardrobe[0].rotation = [0, 0, radians(0)]

# Place the lamp in the free upper aisle between the wardrobe and nightstand.
floor_lamp[0].position = [0.95, 3.56, 0.825]
floor_lamp[0].rotation = [0, 0, radians(-39)]

# Fixed anchors preserve the selected non-overlapping arrangement if the
# solver needs to adjust the scene.
bed_anchor = AssetInstance(position=[2.985, 1.92, 0.525])
side_table_A_anchor = AssetInstance(position=[1.65, 0.30, 0.30])
side_table_B_anchor = AssetInstance(position=[1.65, 3.54, 0.30])
dressing_table_anchor = AssetInstance(position=[0.24, 1.45, 0.525])
dressing_chair_anchor = AssetInstance(position=[0.80, 1.45, 0.46])
wardrobe_anchor = AssetInstance(position=[0.31, 2.94, 1.10])
floor_lamp_anchor = AssetInstance(position=[0.95, 3.56, 0.825])
room_center = AssetInstance(position=[2.03, 1.92, 0.525])

# Important wall relationships come first.
solver.against_wall(king_size_bed[0], walls[1])
solver.distance_constraint(
    king_size_bed[0], bed_anchor, 0, 0, weight=10
)
solver.point_towards(king_size_bed[0], room_center)

solver.against_wall(dressing_table[0], walls[3])
solver.distance_constraint(
    dressing_table[0], dressing_table_anchor, 0, 0, weight=10
)
solver.point_towards(dressing_table[0], dressing_chair[0])

solver.against_wall(wardrobe[0], walls[2])
solver.distance_constraint(
    wardrobe[0], wardrobe_anchor, 0, 0, weight=10
)
solver.align_with(wardrobe[0], dressing_table[0])

# Keep the chair directly in front of and facing the dressing table.
solver.distance_constraint(
    dressing_chair[0], dressing_chair_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    dressing_chair[0], dressing_table[0], 0.50, 0.65, weight=5
)
solver.point_towards(dressing_chair[0], dressing_table[0])

# Anchor both nightstands beside the bed and keep their fronts aligned with it.
solver.distance_constraint(
    side_table_A[0], side_table_A_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    side_table_A[0], king_size_bed[0], 2.00, 2.20, weight=2
)
solver.align_with(side_table_A[0], king_size_bed[0])

solver.distance_constraint(
    side_table_B[0], side_table_B_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    side_table_B[0], king_size_bed[0], 2.00, 2.20, weight=2
)
solver.align_with(side_table_B[0], king_size_bed[0])

# Keep the lamp in its clear corner and orient it toward the sleeping area.
solver.distance_constraint(
    floor_lamp[0], floor_lamp_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    floor_lamp[0], side_table_B[0], 0.65, 0.80, weight=2
)
solver.point_towards(floor_lamp[0], king_size_bed[0])

solver.constraints = []
side_table_A[0].position = [1.649999976158142, 0.30000001192092896, 0.30000001192092896]
side_table_A[0].rotation = [0, 0, 3.141592623170876]
side_table_A[0].optimize = 2
dressing_table[0].position = [0.23999999463558197, 1.4500000476837158, 0.5249999761581421]
dressing_table[0].rotation = [0, 0, 3.421855031616434e-08]
dressing_table[0].optimize = 2
king_size_bed[0].position = [2.9813897609710693, 1.9199999570846558, 0.5249999761581421]
king_size_bed[0].rotation = [0, 0, -3.1415926416212088]
king_size_bed[0].optimize = 2
side_table_B[0].position = [1.649999976158142, 3.5399999618530273, 0.30000001192092896]
side_table_B[0].rotation = [0, 0, 3.1415925882685567]
side_table_B[0].optimize = 2
wardrobe[0].position = [0.3100000321865082, 2.940000057220459, 1.100000023841858]
wardrobe[0].rotation = [0, 0, 1.3804799335557438e-08]
wardrobe[0].optimize = 2
dressing_chair[0].position = [0.800000011920929, 1.4500000476837158, 0.46000000834465027]
dressing_chair[0].rotation = [0, 0, -3.125884689672577]
dressing_chair[0].optimize = 2
floor_lamp[0].position = [0.949999988079071, 3.559999942779541, 0.824999988079071]
floor_lamp[0].rotation = [0, 0, -0.6681120140675211]
floor_lamp[0].optimize = 2

