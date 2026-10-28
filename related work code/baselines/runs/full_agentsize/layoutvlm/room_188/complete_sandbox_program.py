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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.41, 0.00, 0.00]),
    Wall(corner1=[2.41, 0.00, 0.00], corner2=[2.41, 2.58, 0.00]),
    Wall(corner1=[2.41, 2.58, 0.00], corner2=[1.85, 2.58, 0.00]),
    Wall(corner1=[1.85, 2.58, 0.00], corner2=[1.85, 3.31, 0.00]),
    Wall(corner1=[1.85, 3.31, 0.00], corner2=[0.00, 3.31, 0.00]),
    Wall(corner1=[0.00, 3.31, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
wardrobe = Assets(description="wardrobe", size=[0.60, 1.20, 2.00], placements=[AssetInstance() for _ in range(1)])
stool = Assets(description="stool", size=[0.40, 0.40, 0.45], placements=[AssetInstance() for _ in range(1)])
sofa = Assets(description="sofa", size=[0.80, 1.60, 0.85], placements=[AssetInstance() for _ in range(1)])

wardrobe[0].instance_id = 'wardrobe_0'
stool[0].instance_id = 'stool_0'
sofa[0].instance_id = 'sofa_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

wardrobe[0].position = [0.7131890589627431, 1.3508600865095404, 1.0]
wardrobe[0].rotation = [0, 0, 0]
stool[0].position = [1.6878290837243208, 2.8770425098650207, 0.225]
stool[0].rotation = [0, 0, 0]
sofa[0].position = [1.6665843756642746, 0.8289334204943022, 0.425]
sofa[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.7131890589627431, 1.3508600865095404, 1.0]
wardrobe[0].rotation = [0, 0, 0]
stool[0].position = [1.6878290837243208, 2.8770425098650207, 0.225]
stool[0].rotation = [0, 0, 0]
sofa[0].position = [1.6665843756642746, 0.8289334204943022, 0.425]
sofa[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the wardrobe along the bottom wall, to the right of the door.
# Its 1.20 m side runs parallel to the wall, leaving the doorway and its
# inward circulation path clear.
wardrobe[0].position = [1.66, 0.30, 1.00]
wardrobe[0].rotation = [0, 0, radians(90)]

# Place the sofa against the upper portion of the left wall, facing inward.
sofa[0].position = [0.40, 2.30, 0.425]
sofa[0].rotation = [0, 0, 0]

# Place the stool beside the sofa with a 0.05 m edge-to-edge gap.
# Their center distance is 0.65 m: 0.40 m sofa half-depth +
# 0.20 m stool half-width + 0.05 m clearance.
stool[0].position = [1.05, 2.30, 0.225]
stool[0].rotation = [0, 0, 0]

# Fixed orientation references preserve inward-facing, wall-aligned rotations.
wardrobe_orientation = AssetInstance(
    position=[1.66, 1.30, 1.00],
    rotation=[0, 0, radians(90)]
)
sofa_orientation = AssetInstance(
    position=[1.40, 2.30, 0.425],
    rotation=[0, 0, 0]
)

# Important wall constraints come first so the large furniture remains flush
# with its selected wall if physical-feasibility adjustments are required.
solver.against_wall(wardrobe[0], walls[0])
solver.align_with(wardrobe[0], wardrobe_orientation)

solver.against_wall(sofa[0], walls[5])
solver.align_with(sofa[0], sofa_orientation)

# Keep the stool next to, but not overlapping, the sofa. The allowed
# center-distance interval corresponds to an edge gap between 0 and 0.10 m.
solver.distance_constraint(
    stool[0], sofa[0],
    min_distance=0.60,
    max_distance=0.70,
    weight=10
)
solver.align_with(stool[0], sofa[0])

# Apply the same proximity relationship from the sofa side while retaining
# the higher-priority wall constraint specified above.
solver.distance_constraint(
    sofa[0], stool[0],
    min_distance=0.60,
    max_distance=0.70,
    weight=10
)

solver.constraints = []
sofa[0].position = [1.00617516040802, 2.4545931816101074, 0.42500001192092896]
sofa[0].rotation = [0, 0, -1.6954895071952965]
sofa[0].optimize = 2
wardrobe[0].position = [1.5311651229858398, 0.9515815377235413, 1.0]
wardrobe[0].rotation = [0, 0, -3.0102820227971767]
wardrobe[0].optimize = 2
stool[0].position = [1.3117659091949463, 1.8726749420166016, 0.22499999403953552]
stool[0].rotation = [0, 0, -1.6957438906371818]
stool[0].optimize = 2

