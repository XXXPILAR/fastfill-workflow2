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
    Wall(corner1=[2.47, 0.00, 0.00], corner2=[2.47, 2.79, 0.00]),
    Wall(corner1=[2.47, 2.79, 0.00], corner2=[0.00, 2.79, 0.00]),
    Wall(corner1=[0.00, 2.79, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.47, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bed = Assets(description="bed", size=[2.00, 1.00, 0.55], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="cabinet", size=[0.45, 0.80, 1.80], placements=[AssetInstance() for _ in range(1)])

bed[0].instance_id = 'bed_0'
cabinet[0].instance_id = 'cabinet_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

bed[0].position = [2.45965416880031, 1.0159685024279341, 0.275]
bed[0].rotation = [0, 0, 0]
cabinet[0].position = [0.7099637487530841, 2.1294261739035187, 0.9]
cabinet[0].rotation = [0, 0, 0]
bed[0].position = [2.45965416880031, 1.0159685024279341, 0.275]
bed[0].rotation = [0, 0, 0]
cabinet[0].position = [0.7099637487530841, 2.1294261739035187, 0.9]
cabinet[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed reference points preserve the intended centers while allowing the solver
# to retain the wall-adjacency and facing relationships.
bed_anchor = AssetInstance(position=[0.60, 1.72, 0.275])
cabinet_anchor = AssetInstance(position=[0.70, 0.30, 0.90])
door_center = AssetInstance(position=[2.47, 2.34, 0.275])

# Place the bed lengthwise near the left wall. Its slightly angled orientation
# faces the cabinet while keeping its footprint inside the room and leaving the
# upper-right door approach unobstructed.
bed[0].position = [0.60, 1.72, 0.275]
bed[0].rotation = [0, 0, radians(-86)]

# The cabinet's center is fixed by the layout criteria. It faces into the room
# toward the bed and remains adjacent to the bottom wall.
cabinet[0].position = [0.70, 0.30, 0.90]
cabinet[0].rotation = [0, 0, radians(94)]

# Highest-priority constraints preserve the selected non-overlapping centers.
solver.distance_constraint(
    cabinet[0], cabinet_anchor, 0.0, 0.0, weight=10
)
solver.distance_constraint(
    bed[0], bed_anchor, 0.0, 0.0, weight=10
)

# The cabinet is fixed against the bottom wall, while the bed is kept along the
# left side of the room. The exact-center constraints above take precedence if
# bounding-box differences make wall contact slightly inconsistent.
solver.against_wall(cabinet[0], walls[3])
solver.against_wall(bed[0], walls[2])

# The bed must face the cabinet. Having the cabinet face the bed also gives the
# cabinet a useful inward-facing orientation.
solver.point_towards(bed[0], cabinet[0])
solver.point_towards(cabinet[0], bed[0])

# Maintain separation between the two footprints and preserve a clear approach
# to the 0.90 m door on the right wall.
solver.distance_constraint(
    bed[0], cabinet[0], 1.40, None, weight=10
)
solver.distance_constraint(
    bed[0], door_center, 1.10, None, weight=10
)
solver.distance_constraint(
    cabinet[0], door_center, 1.10, None, weight=10
)

solver.constraints = []
cabinet[0].position = [0.699999988079071, 0.22499999403953552, 0.8999999761581421]
cabinet[0].rotation = [0, 0, 1.5707963673942154]
cabinet[0].optimize = 2
bed[0].position = [1.0, 1.6512266397476196, 0.2750000059604645]
bed[0].rotation = [0, 0, -1.786944699999591e-08]
bed[0].optimize = 2

