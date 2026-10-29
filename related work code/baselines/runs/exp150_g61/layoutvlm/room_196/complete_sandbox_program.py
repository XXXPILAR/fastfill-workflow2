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
    Wall(corner1=[0.00, 3.15, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.06, 0.00, 0.00]),
    Wall(corner1=[6.06, 0.00, 0.00], corner2=[6.06, 1.00, 0.00]),
    Wall(corner1=[6.06, 1.00, 0.00], corner2=[6.02, 1.00, 0.00]),
    Wall(corner1=[6.02, 1.00, 0.00], corner2=[6.02, 0.98, 0.00]),
    Wall(corner1=[6.02, 0.98, 0.00], corner2=[4.04, 0.98, 0.00]),
    Wall(corner1=[4.04, 0.98, 0.00], corner2=[4.04, 3.15, 0.00]),
    Wall(corner1=[4.04, 3.15, 0.00], corner2=[0.00, 3.15, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bed = Assets(description="bed", size=[2.10, 1.80, 1.10], placements=[AssetInstance() for _ in range(1)])
nightstand_A = Assets(description="nightstand", size=[0.40, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.60, 2.40, 2.30], placements=[AssetInstance() for _ in range(1)])
nightstand_B = Assets(description="nightstand", size=[0.40, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])

bed[0].instance_id = 'bed_0'
nightstand_A[0].instance_id = 'nightstand_A_0'
wardrobe[0].instance_id = 'wardrobe_0'
nightstand_B[0].instance_id = 'nightstand_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

bed[0].position = [1.904331136031407, 1.7602468400393985, 0.55]
bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [3.730578709640502, 1.5132841536703643, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.2762138907333395, 2.918852664880972, 1.15]
wardrobe[0].rotation = [0, 0, 0]
nightstand_B[0].position = [1.5521358371464407, 1.121115891438758, 0.275]
nightstand_B[0].rotation = [0, 0, 0]
bed[0].position = [1.904331136031407, 1.7602468400393985, 0.55]
bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [3.730578709640502, 1.5132841536703643, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.2762138907333395, 2.918852664880972, 1.15]
wardrobe[0].rotation = [0, 0, 0]
nightstand_B[0].position = [1.5521358371464407, 1.121115891438758, 0.275]
nightstand_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the coordinates of the supplied walls: the main room occupies
# x=0..4.04, y=0..3.15; the entrance alcove extends to the right.
# Put the bed's head against the upper wall, with a nightstand on each side.
# At -90 degrees the bed's footprint is 1.80 m across and 2.10 m deep.
bed[0].position = [1.55, 2.10, bed.size[2] / 2]
bed[0].rotation = [0, 0, radians(-90)]

nightstand_A[0].position = [0.35, 2.95, nightstand_A.size[2] / 2]
nightstand_A[0].rotation = [0, 0, radians(-90)]

nightstand_B[0].position = [2.75, 2.95, nightstand_B.size[2] / 2]
nightstand_B[0].rotation = [0, 0, radians(-90)]

# The wardrobe backs onto the right-hand wall and opens toward the room.
# Its footprint is x=3.44..4.04, y=0.75..3.15.
# This leaves about 0.99 m between the wardrobe and the bed, and a
# 0.75 m passage below the wardrobe connecting to the clear entrance alcove.
wardrobe[0].position = [3.74, 1.95, wardrobe.size[2] / 2]
wardrobe[0].rotation = [0, 0, radians(180)]

# Prioritize the collision-free positions. Fixed anchors also preserve the
# left/right ordering of the nightstands, which distances alone cannot do.
# Each instance receives both a position and an orientation constraint.
for placed_instance in (
    bed[0], nightstand_A[0], nightstand_B[0], wardrobe[0]
):
    fixed_pose = AssetInstance(
        position=list(placed_instance.position),
        rotation=list(placed_instance.rotation),
    )
    solver.distance_constraint(
        placed_instance, fixed_pose, 0.0, 0.0, weight=10
    )
    solver.align_with(placed_instance, fixed_pose)

# Maintain the wall-backed furniture arrangement.
solver.against_wall(bed[0], walls[7])
solver.against_wall(nightstand_A[0], walls[7])
solver.against_wall(nightstand_B[0], walls[7])
solver.against_wall(wardrobe[0], walls[6])

# Both nightstands face the same direction as the bed.
solver.align_with(nightstand_A[0], bed[0])
solver.align_with(nightstand_B[0], bed[0])

# Keep the nightstands close to the head of the bed. Distances here are
# full 3D center distances, including the difference in furniture heights.
bedside_distance = (
    1.20**2 + 0.85**2
    + ((bed.size[2] - nightstand_A.size[2]) / 2)**2
) ** 0.5
solver.distance_constraint(
    nightstand_A[0], bed[0], bedside_distance, bedside_distance
)
solver.distance_constraint(
    nightstand_B[0], bed[0], bedside_distance, bedside_distance
)
solver.distance_constraint(
    nightstand_A[0], nightstand_B[0], 2.40, 2.40
)

# All four items are floor-standing; their center heights above already
# place their bottoms at z=0. No on_top_of constraints are needed.
# The window wall is free of tall furniture, and neither door's approach
# in the right-hand alcove contains any furniture.

solver.constraints = []
wardrobe[0].position = [3.7300004959106445, 1.9492415189743042, 1.149999976158142]
wardrobe[0].rotation = [0, 0, -3.1390516191148654]
wardrobe[0].optimize = 2
bed[0].position = [1.5499999523162842, 2.087714433670044, 0.550000011920929]
bed[0].rotation = [0, 0, -1.5558124234809214]
bed[0].optimize = 2
nightstand_A[0].position = [0.3400000035762787, 2.9470460414886475, 0.2750000059604645]
nightstand_A[0].rotation = [0, 0, -1.5589233055561824]
nightstand_A[0].optimize = 2
nightstand_B[0].position = [2.759999990463257, 2.9470460414886475, 0.2750000059604645]
nightstand_B[0].rotation = [0, 0, -1.5589233055561824]
nightstand_B[0].optimize = 2

