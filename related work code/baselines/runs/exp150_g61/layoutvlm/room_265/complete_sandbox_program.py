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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.43, 0.00, 0.00]),
    Wall(corner1=[3.43, 0.00, 0.00], corner2=[3.43, 3.12, 0.00]),
    Wall(corner1=[3.43, 3.12, 0.00], corner2=[1.02, 3.12, 0.00]),
    Wall(corner1=[1.02, 3.12, 0.00], corner2=[1.02, 2.56, 0.00]),
    Wall(corner1=[1.02, 2.56, 0.00], corner2=[0.90, 2.56, 0.00]),
    Wall(corner1=[0.90, 2.56, 0.00], corner2=[0.90, 4.70, 0.00]),
    Wall(corner1=[0.90, 4.70, 0.00], corner2=[0.00, 4.70, 0.00]),
    Wall(corner1=[0.00, 4.70, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
stool = Assets(description="stool", size=[0.40, 0.45, 0.45], placements=[AssetInstance() for _ in range(1)])
nightstand_A = Assets(description="nightstand", size=[0.40, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.60, 1.80, 2.30], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.10, 1.80, 1.10], placements=[AssetInstance() for _ in range(1)])
dressing_table = Assets(description="dressing table", size=[0.45, 1.00, 0.78], placements=[AssetInstance() for _ in range(1)])
nightstand_B = Assets(description="nightstand", size=[0.40, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])

stool[0].instance_id = 'stool_0'
nightstand_A[0].instance_id = 'nightstand_A_0'
wardrobe[0].instance_id = 'wardrobe_0'
bed[0].instance_id = 'bed_0'
dressing_table[0].instance_id = 'dressing_table_0'
nightstand_B[0].instance_id = 'nightstand_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

stool[0].position = [0.6040786808630154, 4.291157614750454, 0.225]
stool[0].rotation = [0, 0, 0]
nightstand_A[0].position = [0.661932815451755, 0.8226242261260647, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
wardrobe[0].position = [2.5839603474395823, 0.39701683698903845, 1.15]
wardrobe[0].rotation = [0, 0, 0]
bed[0].position = [3.119491499402852, 2.786163713657825, 0.55]
bed[0].rotation = [0, 0, 0]
dressing_table[0].position = [0.4703304189402853, 2.8231800674275127, 0.39]
dressing_table[0].rotation = [0, 0, 0]
nightstand_B[0].position = [1.8649483193008967, 2.924186834381317, 0.275]
nightstand_B[0].rotation = [0, 0, 0]
stool[0].position = [0.6040786808630154, 4.291157614750454, 0.225]
stool[0].rotation = [0, 0, 0]
nightstand_A[0].position = [0.661932815451755, 0.8226242261260647, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
wardrobe[0].position = [2.5839603474395823, 0.39701683698903845, 1.15]
wardrobe[0].rotation = [0, 0, 0]
bed[0].position = [3.119491499402852, 2.786163713657825, 0.55]
bed[0].rotation = [0, 0, 0]
dressing_table[0].position = [0.4703304189402853, 2.8231800674275127, 0.39]
dressing_table[0].rotation = [0, 0, 0]
nightstand_B[0].position = [1.8649483193008967, 2.924186834381317, 0.275]
nightstand_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the supplied wall coordinates directly. Keep the entrance corridor
# (the narrow extension above y=3.12) completely free of furniture.
# The bed's long axis runs east-west, with its head against the east wall.
bed[0].position = [2.38, 1.53, 0.55]
bed[0].rotation = [0, 0, radians(180)]

# Flank the head of the bed, leaving small gaps beside the mattress.
nightstand_A[0].position = [3.23, 0.30, 0.275]
nightstand_A[0].rotation = [0, 0, radians(180)]
nightstand_B[0].position = [3.23, 2.78, 0.275]
nightstand_B[0].rotation = [0, 0, radians(180)]

# Keep the tall wardrobe away from the window on the south wall.
wardrobe[0].position = [0.30, 0.95, 1.15]
wardrobe[0].rotation = [0, 0, 0]

# Place the dressing table on the north wall of the main room, near
# its western end so it can also be approached from the entrance side.
dressing_table[0].position = [1.55, 2.895, 0.39]
dressing_table[0].rotation = [0, 0, radians(270)]

# A movable stool sits at the foot of the bed, facing back toward it.
# All listed objects are floor-standing; none needs an on_top_of constraint.
stool[0].position = [0.98, 1.53, 0.225]
stool[0].rotation = [0, 0, 0]

# High-priority position anchors preserve the compact, nonoverlapping layout.
# Fixed points are constraint references, not additional scene furniture.
for layout_asset in (
    bed, nightstand_A, nightstand_B, wardrobe, dressing_table, stool
):
    solver.distance_constraint(
        layout_asset[0],
        AssetInstance(position=list(layout_asset[0].position)),
        0, 0, weight=10
    )

# The bed and both bedside tables share the same head wall.
solver.against_wall(bed[0], walls[1])
solver.against_wall(nightstand_A[0], walls[1])
solver.against_wall(nightstand_B[0], walls[1])
solver.against_wall(wardrobe[0], walls[7])
solver.against_wall(dressing_table[0], walls[2])

# Explicit facing constraints: the bed faces the stool, and wall-backed
# furniture faces into the room rather than into its supporting wall.
solver.point_towards(bed[0], stool[0])
solver.point_towards(stool[0], bed[0])
solver.align_with(nightstand_A[0], bed[0])
solver.align_with(nightstand_B[0], bed[0])
solver.align_with(wardrobe[0], bed[0], angle=180)
solver.align_with(dressing_table[0], bed[0], angle=90)

# Preserve the bedside relationship and keep the stool at the bed's foot.
# Distances include the difference in bounding-box center heights.
for bedside_asset in (nightstand_A, nightstand_B):
    bedside_distance = sum(
        (bedside_asset[0].position[axis] - bed[0].position[axis]) ** 2
        for axis in range(3)
    ) ** 0.5
    solver.distance_constraint(
        bedside_asset[0], bed[0],
        bedside_distance, bedside_distance, weight=10
    )

foot_distance = sum(
    (stool[0].position[axis] - bed[0].position[axis]) ** 2
    for axis in range(3)
) ** 0.5
solver.distance_constraint(
    stool[0], bed[0], foot_distance, foot_distance, weight=10
)

solver.constraints = []
wardrobe[0].position = [0.2994542717933655, 0.949999988079071, 1.149999976158142]
wardrobe[0].rotation = [0, 0, 0.0006305123364032291]
wardrobe[0].optimize = 2
nightstand_B[0].position = [3.2267072200775146, 2.837700366973877, 0.2750000059604645]
nightstand_B[0].rotation = [0, 0, 3.141068346198522]
nightstand_B[0].optimize = 2
stool[0].position = [0.8143859505653381, 1.5299999713897705, 0.22499999403953552]
stool[0].rotation = [0, 0, 0.0157079639172164]
stool[0].optimize = 2
bed[0].position = [2.0723907947540283, 1.5562281608581543, 0.550000011920929]
bed[0].rotation = [0, 0, -2.2296534652527575]
bed[0].optimize = 2
nightstand_A[0].position = [3.2267799377441406, 0.242893248796463, 0.2750000059604645]
nightstand_A[0].rotation = [0, 0, 3.141359836835819]
nightstand_A[0].optimize = 2
dressing_table[0].position = [1.5499999523162842, 2.8922691345214844, 0.38999998569488525]
dressing_table[0].rotation = [0, 0, -1.5701681838848371]
dressing_table[0].optimize = 2

