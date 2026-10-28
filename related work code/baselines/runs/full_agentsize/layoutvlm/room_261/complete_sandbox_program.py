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
    Wall(corner1=[2.06, 2.01, 0.00], corner2=[3.81, 2.01, 0.00]),
    Wall(corner1=[3.81, 2.01, 0.00], corner2=[3.81, 3.66, 0.00]),
    Wall(corner1=[3.81, 3.66, 0.00], corner2=[0.22, 3.66, 0.00]),
    Wall(corner1=[0.22, 3.66, 0.00], corner2=[0.22, 3.43, 0.00]),
    Wall(corner1=[0.22, 3.43, 0.00], corner2=[0.00, 3.43, 0.00]),
    Wall(corner1=[0.00, 3.43, 0.00], corner2=[0.00, 0.33, 0.00]),
    Wall(corner1=[0.00, 0.33, 0.00], corner2=[0.35, 0.33, 0.00]),
    Wall(corner1=[0.35, 0.33, 0.00], corner2=[0.35, 0.00, 0.00]),
    Wall(corner1=[0.35, 0.00, 0.00], corner2=[2.06, 0.00, 0.00]),
    Wall(corner1=[2.06, 0.00, 0.00], corner2=[2.06, 2.01, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
oven = Assets(description="oven", size=[0.60, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
refrigerator = Assets(description="refrigerator", size=[0.75, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])

oven[0].instance_id = 'oven_0'
refrigerator[0].instance_id = 'refrigerator_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'
walls[8].instance_id = 'walls_8'
walls[9].instance_id = 'walls_9'

oven[0].position = [0.931372689890291, 2.5905555236330873, 0.45]
oven[0].rotation = [0, 0, 0]
refrigerator[0].position = [3.7083984436518356, 2.8293950617757133, 0.9]
refrigerator[0].rotation = [0, 0, 0]
oven[0].position = [0.931372689890291, 2.5905555236330873, 0.45]
oven[0].rotation = [0, 0, 0]
refrigerator[0].position = [3.7083984436518356, 2.8293950617757133, 0.9]
refrigerator[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the south wall of the upper-right alcove for a compact appliance run.
# Both appliances face north (+y), into the usable part of the alcove. This
# leaves the entry corridor and the full area in front of the south door clear.
refrigerator[0].position = [2.55, 2.385, refrigerator.size[2] / 2]
refrigerator[0].rotation = [0, 0, radians(90)]

oven[0].position = [3.38, 2.31, oven.size[2] / 2]
oven[0].rotation = [0, 0, radians(90)]

# Fixed reference points preserve the intended locations along the wall while
# still allowing the wall constraints to enforce contact with the boundary.
refrigerator_anchor = AssetInstance(
    position=[2.55, 2.385, refrigerator.size[2] / 2]
)
oven_anchor = AssetInstance(
    position=[3.38, 2.31, oven.size[2] / 2]
)

# Reference points directly north of each appliance define their front-facing
# direction without introducing any additional scene assets.
refrigerator_facing_target = AssetInstance(
    position=[2.55, 3.20, refrigerator.size[2] / 2]
)
oven_facing_target = AssetInstance(
    position=[3.38, 3.20, oven.size[2] / 2]
)

# The against-wall constraints are the primary positional requirements.
solver.against_wall(refrigerator[0], walls[0])
solver.against_wall(oven[0], walls[0])

# Strong anchors keep the refrigerator and oven side by side, separated by a
# small gap, and away from the windows and door circulation zone.
solver.distance_constraint(
    refrigerator[0], refrigerator_anchor,
    min_distance=0, max_distance=0, weight=10
)
solver.distance_constraint(
    oven[0], oven_anchor,
    min_distance=0, max_distance=0, weight=10
)

# Orient both appliance fronts toward the open interior of the alcove.
solver.point_towards(refrigerator[0], refrigerator_facing_target)
solver.point_towards(oven[0], oven_facing_target)

solver.constraints = []
refrigerator[0].position = [2.549999952316284, 2.3849997520446777, 0.8999999761581421]
refrigerator[0].rotation = [0, 0, 1.570796466799783]
refrigerator[0].optimize = 2
oven[0].position = [3.380000114440918, 2.309999704360962, 0.44999998807907104]
oven[0].rotation = [0, 0, 1.5707964780015429]
oven[0].optimize = 2

