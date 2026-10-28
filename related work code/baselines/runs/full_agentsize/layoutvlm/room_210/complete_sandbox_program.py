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
    Wall(corner1=[2.61, 2.89, 0.00], corner2=[0.00, 2.89, 0.00]),
    Wall(corner1=[0.00, 2.89, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.61, 0.00, 0.00]),
    Wall(corner1=[2.61, 0.00, 0.00], corner2=[2.61, 2.89, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bed = Assets(description="bed", size=[2.00, 1.40, 0.55], placements=[AssetInstance() for _ in range(1)])
nightstand_A = Assets(description="nightstand", size=[0.40, 0.45, 0.50], placements=[AssetInstance() for _ in range(1)])
nightstand_B = Assets(description="nightstand", size=[0.40, 0.45, 0.50], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.60, 1.20, 2.10], placements=[AssetInstance() for _ in range(1)])

bed[0].instance_id = 'bed_0'
nightstand_A[0].instance_id = 'nightstand_A_0'
nightstand_B[0].instance_id = 'nightstand_B_0'
wardrobe[0].instance_id = 'wardrobe_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

bed[0].position = [1.8101175384022483, 1.3442803085316983, 0.275]
bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [0.7927472826378473, 0.7441292017896537, 0.25]
nightstand_A[0].rotation = [0, 0, 0]
nightstand_B[0].position = [0.24582145781041845, 0.8776987933233967, 0.25]
nightstand_B[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.038844891505398424, 0.02132652581764223, 1.05]
wardrobe[0].rotation = [0, 0, 0]
bed[0].position = [1.8101175384022483, 1.3442803085316983, 0.275]
bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [0.7927472826378473, 0.7441292017896537, 0.25]
nightstand_A[0].rotation = [0, 0, 0]
nightstand_B[0].position = [0.24582145781041845, 0.8776987933233967, 0.25]
nightstand_B[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.038844891505398424, 0.02132652581764223, 1.05]
wardrobe[0].rotation = [0, 0, 0]

solver.constraints = []

# The bed is centered beneath the window with its head against the north wall.
# Rotating it -90 degrees makes it face into the room while leaving a clear
# access aisle along its left side from the entrance.
bed[0].position = [1.305, 1.89, 0.275]
bed[0].rotation = [0, 0, radians(-90)]

# Place the two nightstands symmetrically beside the head of the bed, making
# the bed spatially between them without any bounding-box overlap.
nightstand_A[0].position = [0.37, 2.69, 0.25]
nightstand_A[0].rotation = [0, 0, radians(-90)]

nightstand_B[0].position = [2.24, 2.69, 0.25]
nightstand_B[0].rotation = [0, 0, radians(-90)]

# The wardrobe is against the unobstructed portion of the south wall, to the
# right of the door. Its front faces north into the room, and the entrance
# area in front of the door (approximately x=0.05 to x=0.83) remains clear.
wardrobe[0].position = [1.91, 0.30, 1.05]
wardrobe[0].rotation = [0, 0, radians(90)]

# Fixed reference points preserve the intended centers if the solver adjusts
# the layout for physical feasibility.
bed_anchor = AssetInstance(position=[1.305, 1.89, 0.275])
nightstand_A_anchor = AssetInstance(position=[0.37, 2.69, 0.25])
nightstand_B_anchor = AssetInstance(position=[2.24, 2.69, 0.25])
wardrobe_anchor = AssetInstance(position=[1.91, 0.30, 1.05])

# Directional reference points face the bed south and the wardrobe north.
bed_facing_point = AssetInstance(position=[1.305, 0.89, 0.275])
wardrobe_facing_point = AssetInstance(position=[1.91, 1.30, 1.05])

# High-priority position constraints establish the non-overlapping layout.
solver.distance_constraint(
    bed[0], bed_anchor, min_distance=0, max_distance=0, weight=10
)
solver.distance_constraint(
    nightstand_A[0], nightstand_A_anchor,
    min_distance=0, max_distance=0, weight=10
)
solver.distance_constraint(
    nightstand_B[0], nightstand_B_anchor,
    min_distance=0, max_distance=0, weight=10
)
solver.distance_constraint(
    wardrobe[0], wardrobe_anchor, min_distance=0, max_distance=0, weight=10
)

# Wall constraints preserve the bedroom arrangement: the bed and nightstands
# remain at the north wall, while the wardrobe stays at the south wall.
solver.against_wall(bed[0], walls[0])
solver.against_wall(nightstand_A[0], walls[0])
solver.against_wall(nightstand_B[0], walls[0])
solver.against_wall(wardrobe[0], walls[2])

# Orientation constraints are specified for every new asset. The nightstands
# share the bed's orientation, while the bed and wardrobe face into the room.
solver.point_towards(bed[0], bed_facing_point)
solver.align_with(nightstand_A[0], bed[0])
solver.align_with(nightstand_B[0], bed[0])
solver.point_towards(wardrobe[0], wardrobe_facing_point)

solver.constraints = []
nightstand_B[0].position = [2.240000009536743, 2.6945557594299316, 0.25]
nightstand_B[0].rotation = [0, 0, -1.5707961802873462]
nightstand_B[0].optimize = 2
bed[0].position = [1.3049999475479126, 1.894555926322937, 0.2750000059604645]
bed[0].rotation = [0, 0, -1.570796399790033]
bed[0].optimize = 2
wardrobe[0].position = [1.909999966621399, 0.29999998211860657, 1.0499999523162842]
wardrobe[0].rotation = [0, 0, 1.5707964629188718]
wardrobe[0].optimize = 2
nightstand_A[0].position = [0.3700000047683716, 2.6945557594299316, 0.25]
nightstand_A[0].rotation = [0, 0, -1.5707961802873462]
nightstand_A[0].optimize = 2

