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
    Wall(corner1=[3.16, 3.81, 0.00], corner2=[0.00, 3.81, 0.00]),
    Wall(corner1=[0.00, 3.81, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.16, 0.00, 0.00]),
    Wall(corner1=[3.16, 0.00, 0.00], corner2=[3.16, 3.81, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
carpet = Assets(description="carpet", size=[1.70, 2.40, 0.02], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.60, 1.80, 2.20], placements=[AssetInstance() for _ in range(1)])
nightstand_A = Assets(description="nightstand", size=[0.40, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.00, 1.60, 0.55], placements=[AssetInstance() for _ in range(1)])
nightstand_B = Assets(description="nightstand", size=[0.40, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])

carpet[0].instance_id = 'carpet_0'
wardrobe[0].instance_id = 'wardrobe_0'
nightstand_A[0].instance_id = 'nightstand_A_0'
bed[0].instance_id = 'bed_0'
nightstand_B[0].instance_id = 'nightstand_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

carpet[0].position = [0.528531758271786, 1.2993977426174728, 0.01]
carpet[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.20392131101067226, 1.766655700216721, 1.1]
wardrobe[0].rotation = [0, 0, 0]
nightstand_A[0].position = [0.8079684375445445, 3.4511304478646148, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
bed[0].position = [1.0383384237891835, 3.5839416615273323, 0.275]
bed[0].rotation = [0, 0, 0]
nightstand_B[0].position = [1.2200422464013532, 2.0362544222149728, 0.275]
nightstand_B[0].rotation = [0, 0, 0]
carpet[0].position = [0.528531758271786, 1.2993977426174728, 0.01]
carpet[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.20392131101067226, 1.766655700216721, 1.1]
wardrobe[0].rotation = [0, 0, 0]
nightstand_A[0].position = [0.8079684375445445, 3.4511304478646148, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
bed[0].position = [1.0383384237891835, 3.5839416615273323, 0.275]
bed[0].rotation = [0, 0, 0]
nightstand_B[0].position = [1.2200422464013532, 2.0362544222149728, 0.275]
nightstand_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the bed against the north wall, centered beneath the window. The two
# nightstands flank it symmetrically, so the bed lies between them.
bed[0].position = [1.58, 2.81, 0.275]
bed[0].rotation = [0, 0, radians(-90)]

nightstand_A[0].position = [0.45, 3.61, 0.275]
nightstand_A[0].rotation = [0, 0, radians(-90)]

nightstand_B[0].position = [2.71, 3.61, 0.275]
nightstand_B[0].rotation = [0, 0, radians(-90)]

# Put the wardrobe along the lower part of the east wall. This keeps it clear
# of the bed and leaves the entrance area around the south-wall door open.
wardrobe[0].position = [2.86, 0.90, 1.10]
wardrobe[0].rotation = [0, 0, radians(180)]

# Center the carpet beneath the bed, with some carpet extending beyond its
# foot. As a thin floor covering, it can safely occupy the bed's footprint.
carpet[0].position = [1.58, 2.20, 0.01]
carpet[0].rotation = [0, 0, 0]

# Fixed reference points preserve the intended arrangement if the solver
# needs to make small feasibility adjustments.
bed_anchor = AssetInstance(position=[1.58, 2.81, 0.275])
nightstand_A_anchor = AssetInstance(position=[0.45, 3.61, 0.275])
nightstand_B_anchor = AssetInstance(position=[2.71, 3.61, 0.275])
wardrobe_anchor = AssetInstance(position=[2.86, 0.90, 1.10])
carpet_anchor = AssetInstance(position=[1.58, 2.20, 0.01])
room_center = AssetInstance(position=[1.58, 1.905, 0.275])

# Bed: keep the head end against the north wall and orient it toward the room.
solver.against_wall(bed[0], walls[0])
solver.distance_constraint(bed[0], bed_anchor, 0, 0, weight=10)
solver.point_towards(bed[0], room_center)

# Nightstand A (o0002): explicitly satisfy the required wall placement.
# Its anchor and bed-relative distance keep it on the left side of the bed.
solver.against_wall(nightstand_A[0], walls[0])
solver.distance_constraint(
    nightstand_A[0], nightstand_A_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    nightstand_A[0], bed[0], 1.36, 1.41, weight=10
)
solver.align_with(nightstand_A[0], bed[0])

# Nightstand B mirrors nightstand A on the other side, making the bed the
# middle object in the three-piece arrangement.
solver.against_wall(nightstand_B[0], walls[0])
solver.distance_constraint(
    nightstand_B[0], nightstand_B_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    nightstand_B[0], bed[0], 1.36, 1.41, weight=10
)
solver.align_with(nightstand_B[0], bed[0])

# Wardrobe: hold it against the east wall and make its front face into the room.
solver.against_wall(wardrobe[0], walls[3])
solver.distance_constraint(
    wardrobe[0], wardrobe_anchor, 0, 0, weight=10
)
solver.point_towards(wardrobe[0], room_center)

# Carpet: anchor it under the bed and orient its long axis along the bed.
solver.distance_constraint(carpet[0], carpet_anchor, 0, 0, weight=10)
solver.distance_constraint(carpet[0], bed[0], 0.61, 0.61, weight=1)
solver.align_with(carpet[0], bed[0], angle=90)

solver.constraints = []
carpet[0].position = [1.5800000429153442, 2.200000047683716, 0.009999999776482582]
carpet[0].rotation = [0, 0, -0.00034414631800869266]
carpet[0].optimize = 2
bed[0].position = [1.5800000429153442, 2.8100690841674805, 0.2750000059604645]
bed[0].rotation = [0, 0, -1.5708321380821504]
bed[0].optimize = 2
nightstand_A[0].position = [0.44999998807907104, 3.6100282669067383, 0.2750000059604645]
nightstand_A[0].rotation = [0, 0, -1.5708460492464582]
nightstand_A[0].optimize = 2
nightstand_B[0].position = [2.7100000381469727, 3.6100282669067383, 0.2750000059604645]
nightstand_B[0].rotation = [0, 0, -1.5708460492464582]
nightstand_B[0].optimize = 2
wardrobe[0].position = [2.8549952507019043, 0.9512732625007629, 1.100000023841858]
wardrobe[0].rotation = [0, 0, 3.1415445116530494]
wardrobe[0].optimize = 2

