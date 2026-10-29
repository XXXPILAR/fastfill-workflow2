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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.76, 0.00, 0.00]),
    Wall(corner1=[2.76, 0.00, 0.00], corner2=[2.76, 3.85, 0.00]),
    Wall(corner1=[2.76, 3.85, 0.00], corner2=[0.00, 3.85, 0.00]),
    Wall(corner1=[0.00, 3.85, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
nightstand_A = Assets(description="A modern nightstand with a sleek design, featuring a wooden frame and a gray panel on the front. It has four angled legs for stability.", size=[0.40, 0.40, 0.50], placements=[AssetInstance() for _ in range(1)])
king_size_bed = Assets(description="A modern bed with a wooden base and a padded headboard. It features a neatly arranged bedding set with gray pillows and a black throw blanket.", size=[2.15, 1.90, 1.10], placements=[AssetInstance() for _ in range(1)])
nightstand_B = Assets(description="A modern nightstand with a sleek design, featuring a wooden frame and a gray panel on the front. It has four angled legs for stability.", size=[0.40, 0.40, 0.50], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="A large wooden wardrobe with two sections, each featuring double doors with vertical slats and silver handles. The interior appears to have shelves or compartments.", size=[0.60, 1.80, 2.20], placements=[AssetInstance() for _ in range(1)])

nightstand_A[0].instance_id = 'nightstand_A_0'
king_size_bed[0].instance_id = 'king_size_bed_0'
nightstand_B[0].instance_id = 'nightstand_B_0'
wardrobe[0].instance_id = 'wardrobe_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

nightstand_A[0].position = [0.09521288472194334, 0.7449098511909807, 0.25]
nightstand_A[0].rotation = [0, 0, 0]
king_size_bed[0].position = [0.9858150427259067, 0.4665150113288396, 0.55]
king_size_bed[0].rotation = [0, 0, 0]
nightstand_B[0].position = [2.4027680464050714, 3.3641959298622264, 0.25]
nightstand_B[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.14403738742489158, 3.0263651899302024, 1.1]
wardrobe[0].rotation = [0, 0, 0]
nightstand_A[0].position = [0.09521288472194334, 0.7449098511909807, 0.25]
nightstand_A[0].rotation = [0, 0, 0]
king_size_bed[0].position = [0.9858150427259067, 0.4665150113288396, 0.55]
king_size_bed[0].rotation = [0, 0, 0]
nightstand_B[0].position = [2.4027680464050714, 3.3641959298622264, 0.25]
nightstand_B[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.14403738742489158, 3.0263651899302024, 1.1]
wardrobe[0].rotation = [0, 0, 0]

solver.constraints = []

# Put the headboard against the right wall, leaving a 0.61 m foot-side
# aisle along the left wall. The two nightstands flank the bed.
king_size_bed[0].position = [1.685, 1.75, 0.55]
king_size_bed[0].rotation = [0, 0, radians(180)]

nightstand_A[0].position = [2.56, 2.95, 0.25]
nightstand_A[0].rotation = [0, 0, radians(180)]

nightstand_B[0].position = [2.56, 0.55, 0.25]
nightstand_B[0].rotation = [0, 0, radians(180)]

# The wardrobe occupies the upper-right corner and opens toward -y.
# Its rotated footprint is 1.80 m wide and 0.60 m deep.
# There is a 0.10 m edge-to-edge gap to nightstand_A.
wardrobe[0].position = [1.86, 3.55, 1.10]
wardrobe[0].rotation = [0, 0, radians(270)]

# Preserve these nonoverlapping positions. Fixed-point anchors also
# preserve floor heights and the circulation space beside the bed.
# Note: the room is exceptionally tight: this wardrobe position encroaches
# 0.03 m into the doorway's horizontal projection at its right-hand edge.
# Full-width door clearance and this arrangement cannot both be guaranteed.
for placed_instance in (
    king_size_bed[0],
    nightstand_A[0],
    nightstand_B[0],
    wardrobe[0],
):
    solver.distance_constraint(
        placed_instance,
        AssetInstance(position=list(placed_instance.position)),
        0,
        0,
        weight=10,
    )

# Wall attachments are secondary to the explicit placement anchors.
solver.against_wall(king_size_bed[0], walls[1])
solver.against_wall(nightstand_A[0], walls[1])
solver.against_wall(nightstand_B[0], walls[1])
solver.against_wall(wardrobe[0], walls[2])

# Absolute orientation references avoid ambiguity about which way fronts face.
solver.align_with(
    king_size_bed[0],
    AssetInstance(rotation=[0, 0, radians(180)]),
)
solver.align_with(nightstand_A[0], king_size_bed[0])
solver.align_with(nightstand_B[0], king_size_bed[0])
solver.align_with(
    wardrobe[0],
    AssetInstance(rotation=[0, 0, radians(270)]),
)

# Both stands sit just outside the bed's lateral edges, with 0.05 m gaps.
# Center distances include the 0.30 m difference in bounding-box heights.
bedside_center_distance = (
    (2.56 - 1.685) ** 2 + 1.20 ** 2 + 0.30 ** 2
) ** 0.5

solver.distance_constraint(
    nightstand_A[0], king_size_bed[0],
    bedside_center_distance, bedside_center_distance,
)
solver.distance_constraint(
    nightstand_B[0], king_size_bed[0],
    bedside_center_distance, bedside_center_distance,
)

# Encode the wardrobe/nightstand proximity using the corresponding
# three-dimensional center distance, not a misleading 0.10 m center distance.
wardrobe_stand_distance = (
    0.70 ** 2 + 0.60 ** 2 + 0.85 ** 2
) ** 0.5
solver.distance_constraint(
    nightstand_A[0], wardrobe[0],
    wardrobe_stand_distance, wardrobe_stand_distance,
    weight=10,
)

solver.constraints = []
king_size_bed[0].position = [1.6854239702224731, 1.75, 0.550000011920929]
king_size_bed[0].rotation = [0, 0, -3.1411472661369317]
king_size_bed[0].optimize = 2
nightstand_A[0].position = [2.5599570274353027, 2.786440849304199, 0.25]
nightstand_A[0].rotation = [0, 0, 3.1414275704776617]
nightstand_A[0].optimize = 2
nightstand_B[0].position = [2.5566606521606445, 0.4500957727432251, 0.25]
nightstand_B[0].rotation = [0, 0, -3.1414103967227174]
nightstand_B[0].optimize = 2
wardrobe[0].position = [1.8088312149047852, 3.5548102855682373, 1.100000023841858]
wardrobe[0].rotation = [0, 0, -1.570618364363746]
wardrobe[0].optimize = 2

