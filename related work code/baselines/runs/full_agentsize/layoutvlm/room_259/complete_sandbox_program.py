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
    Wall(corner1=[0.00, 1.85, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.37, 0.00, 0.00]),
    Wall(corner1=[3.37, 0.00, 0.00], corner2=[3.37, 1.85, 0.00]),
    Wall(corner1=[3.37, 1.85, 0.00], corner2=[0.00, 1.85, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bathroom_cabinet = Assets(description="bathroom cabinet", size=[0.48, 0.80, 0.85], placements=[AssetInstance() for _ in range(1)])
toilet = Assets(description="toilet", size=[0.68, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])

bathroom_cabinet[0].instance_id = 'bathroom_cabinet_0'
toilet[0].instance_id = 'toilet_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

bathroom_cabinet[0].position = [0.6555846882580495, 0.7299138474504139, 0.425]
bathroom_cabinet[0].rotation = [0, 0, 0]
toilet[0].position = [3.0980685116511437, 0.9750566685083132, 0.39]
toilet[0].rotation = [0, 0, 0]
bathroom_cabinet[0].position = [0.6555846882580495, 0.7299138474504139, 0.425]
bathroom_cabinet[0].rotation = [0, 0, 0]
toilet[0].position = [3.0980685116511437, 0.9750566685083132, 0.39]
toilet[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the cabinet on the upper wall, facing into the room. Its rotated
# footprint is approximately 0.80 m along x and 0.48 m along y.
bathroom_cabinet[0].position = [0.55, 1.61, 0.425]
bathroom_cabinet[0].rotation = [0, 0, radians(-90)]

# Place the toilet against the lower wall on the right side. This keeps it
# away from the doorway on the left wall and from the window on the right.
toilet[0].position = [2.45, 0.34, 0.39]
toilet[0].rotation = [0, 0, radians(90)]

# Fixed interior targets preserve the intended positions and orientations.
cabinet_position_anchor = AssetInstance(position=[0.55, 1.61, 0.425])
cabinet_facing_target = AssetInstance(position=[0.55, 0.80, 0.425])
toilet_position_anchor = AssetInstance(position=[2.45, 0.34, 0.39])
toilet_facing_target = AssetInstance(position=[2.45, 1.00, 0.39])

# Keep both fixtures against their designated walls.
solver.against_wall(bathroom_cabinet[0], walls[3])
solver.against_wall(toilet[0], walls[1])

# Preserve their locations along the walls, leaving the doorway approach clear.
solver.distance_constraint(
    bathroom_cabinet[0], cabinet_position_anchor,
    min_distance=0, max_distance=0, weight=10
)
solver.distance_constraint(
    toilet[0], toilet_position_anchor,
    min_distance=0, max_distance=0, weight=10
)

# Both fixtures face inward so their usable fronts remain accessible.
solver.point_towards(bathroom_cabinet[0], cabinet_facing_target)
solver.point_towards(toilet[0], toilet_facing_target)

# Maintain generous separation between the fixtures to prevent overlap and
# provide usable circulation space through the center of the bathroom.
solver.distance_constraint(
    bathroom_cabinet[0], toilet[0],
    min_distance=1.40, max_distance=None, weight=10
)
solver.distance_constraint(
    toilet[0], bathroom_cabinet[0],
    min_distance=1.40, max_distance=None, weight=10
)

solver.constraints = []
toilet[0].position = [2.450000047683716, 0.33999988436698914, 0.38999998569488525]
toilet[0].rotation = [0, 0, 1.5707961427494121]
toilet[0].optimize = 2
bathroom_cabinet[0].position = [0.550000011920929, 1.6099998950958252, 0.42500001192092896]
bathroom_cabinet[0].rotation = [0, 0, -1.570796514218176]
bathroom_cabinet[0].optimize = 2

