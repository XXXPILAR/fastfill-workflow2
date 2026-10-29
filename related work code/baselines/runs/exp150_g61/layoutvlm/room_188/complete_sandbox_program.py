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
wardrobe = Assets(description="wardrobe", size=[0.60, 1.20, 2.10], placements=[AssetInstance() for _ in range(1)])
stool = Assets(description="stool", size=[0.35, 0.35, 0.45], placements=[AssetInstance() for _ in range(1)])
sofa = Assets(description="sofa", size=[0.80, 1.60, 0.80], placements=[AssetInstance() for _ in range(1)])

wardrobe[0].instance_id = 'wardrobe_0'
stool[0].instance_id = 'stool_0'
sofa[0].instance_id = 'sofa_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

wardrobe[0].position = [2.257168155232639, 0.678255845920038, 1.05]
wardrobe[0].rotation = [0, 0, 0]
stool[0].position = [1.410588539099012, 3.128824972898419, 0.225]
stool[0].rotation = [0, 0, 0]
sofa[0].position = [1.7863900636429124, 0.38330615202759505, 0.4]
sofa[0].rotation = [0, 0, 0]
wardrobe[0].position = [2.257168155232639, 0.678255845920038, 1.05]
wardrobe[0].rotation = [0, 0, 0]
stool[0].position = [1.410588539099012, 3.128824972898419, 0.225]
stool[0].rotation = [0, 0, 0]
sofa[0].position = [1.7863900636429124, 0.38330615202759505, 0.4]
sofa[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the supplied boundary coordinates directly.
# Sofa footprint: x=[0.125, 1.725], y=[2.51, 3.31].
# Its back touches the north wall and its front faces into the room.
sofa[0].position = [0.925, 2.91, 0.40]
sofa[0].rotation = [0, 0, radians(-90)]

# Wardrobe footprint: x=[1.81, 2.41], y=[0.25, 1.45].
# Place its back against the east wall, with doors opening toward the room.
wardrobe[0].position = [2.11, 0.85, 1.05]
wardrobe[0].rotation = [0, 0, radians(180)]

# The stool stands on the floor, immediately in front of the sofa.
# Its footprint ends at y=2.46, leaving a 0.05 m gap to the sofa.
stool[0].position = [0.925, 2.285, 0.225]
stool[0].rotation = [0, 0, radians(-90)]

# Prioritize the required wall contact and inward-facing orientations.
solver.against_wall(sofa[0], walls[4])
solver.point_towards(
    sofa[0], AssetInstance(position=[0.925, 1.91, 0.40])
)
solver.against_wall(wardrobe[0], walls[1])
solver.point_towards(
    wardrobe[0], AssetInstance(position=[1.11, 0.85, 1.05])
)

# Preserve positions along the walls so neither item drifts toward the door
# or across the stepped boundary.
solver.distance_constraint(
    sofa[0],
    AssetInstance(position=[0.925, 2.91, 0.40]),
    0, 0, weight=10
)
solver.distance_constraint(
    wardrobe[0],
    AssetInstance(position=[2.11, 0.85, 1.05]),
    0, 0, weight=10
)

# Distances are measured between 3D bounding-box centers, not surfaces:
# a 0.625 m horizontal separation gives the desired 0.05 m surface gap.
solver.distance_constraint(
    stool[0], sofa[0],
    (0.625**2 + 0.175**2)**0.5,
    (0.625**2 + 0.175**2)**0.5,
    weight=10
)
solver.align_with(stool[0], sofa[0], angle=0)
solver.distance_constraint(
    stool[0],
    AssetInstance(position=[0.925, 2.285, 0.225]),
    0, 0, weight=10
)

# All three items are floor-standing, so no on_top_of constraint is needed.
# The entrance at x=[0.12, 0.92], y=0 and the floor immediately inside it
# remain unobstructed; the west/central aisle provides access to the seating.

solver.constraints = []
sofa[0].position = [1.0001248121261597, 2.6117022037506104, 0.4000000059604645]
sofa[0].rotation = [0, 0, -1.7164588201681656]
sofa[0].optimize = 2
wardrobe[0].position = [1.8304070234298706, 1.1417423486709595, 1.0499999523162842]
wardrobe[0].rotation = [0, 0, -2.9330109587488122]
wardrobe[0].optimize = 2
stool[0].position = [0.7374107241630554, 2.0819454193115234, 0.22499999403953552]
stool[0].rotation = [0, 0, -1.7294986123202407]
stool[0].optimize = 2

