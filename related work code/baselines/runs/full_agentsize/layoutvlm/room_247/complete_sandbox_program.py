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
    Wall(corner1=[1.42, 2.06, 0.00], corner2=[1.42, 3.26, 0.00]),
    Wall(corner1=[1.42, 3.26, 0.00], corner2=[0.18, 3.26, 0.00]),
    Wall(corner1=[0.18, 3.26, 0.00], corner2=[0.18, 3.03, 0.00]),
    Wall(corner1=[0.18, 3.03, 0.00], corner2=[0.00, 3.03, 0.00]),
    Wall(corner1=[0.00, 3.03, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[0.89, 0.00, 0.00]),
    Wall(corner1=[0.89, 0.00, 0.00], corner2=[0.89, 0.36, 0.00]),
    Wall(corner1=[0.89, 0.36, 0.00], corner2=[1.42, 0.36, 0.00]),
    Wall(corner1=[1.42, 0.36, 0.00], corner2=[1.42, 1.91, 0.00]),
    Wall(corner1=[1.42, 1.91, 0.00], corner2=[1.33, 1.91, 0.00]),
    Wall(corner1=[1.33, 1.91, 0.00], corner2=[1.33, 2.06, 0.00]),
    Wall(corner1=[1.33, 2.06, 0.00], corner2=[1.42, 2.06, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bar_chair = Assets(description="bar chair", size=[0.45, 0.42, 0.78], placements=[AssetInstance() for _ in range(1)])
bar = Assets(description="bar", size=[0.50, 1.00, 1.05], placements=[AssetInstance() for _ in range(1)])

bar_chair[0].instance_id = 'bar_chair_0'
bar[0].instance_id = 'bar_0'
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
walls[10].instance_id = 'walls_10'
walls[11].instance_id = 'walls_11'

bar_chair[0].position = [0.8034787919188825, 1.6298270098918368, 0.39]
bar_chair[0].rotation = [0, 0, 0]
bar[0].position = [0.6417297392002654, 1.8107265310476817, 0.525]
bar[0].rotation = [0, 0, 0]
bar_chair[0].position = [0.8034787919188825, 1.6298270098918368, 0.39]
bar_chair[0].rotation = [0, 0, 0]
bar[0].position = [0.6417297392002654, 1.8107265310476817, 0.525]
bar[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the bar against the lower portion of the right wall, away from the
# window and doorway/notches. Its 0.50 m depth extends into the room.
bar[0].position = [1.17, 1.20, 0.525]
bar[0].rotation = [0, 0, radians(180)]

# Place the chair directly in front of the bar with a 0.10 m clear gap.
# Along x, the non-overlapping center distance is:
# 0.50 / 2 + 0.45 / 2 + 0.10 = 0.575 m.
bar_chair[0].position = [0.595, 1.20, 0.39]
bar_chair[0].rotation = [0, 0, radians(0)]

# Keep the bar anchored to the unobstructed right-wall segment.
solver.against_wall(bar[0], walls[8])

# Keep the chair between contact distance (0.475 m center-to-center) and
# a 0.10 m surface gap (0.575 m center-to-center) from the bar.
solver.distance_constraint(
    bar_chair[0], bar[0],
    min_distance=0.475,
    max_distance=0.575,
    weight=10
)

# Apply the reciprocal relation so the bar remains close to the chair while
# the earlier wall constraint retains priority.
solver.distance_constraint(
    bar[0], bar_chair[0],
    min_distance=0.475,
    max_distance=0.575,
    weight=1
)

# The chair faces +x toward the bar; the bar faces back toward the chair.
solver.point_towards(bar_chair[0], bar[0])
solver.point_towards(bar[0], bar_chair[0])

solver.constraints = []
bar_chair[0].position = [0.6090030670166016, 1.214003086090088, 0.38999998569488525]
bar_chair[0].rotation = [0, 0, 0.0157079639172164]
bar_chair[0].optimize = 2
bar[0].position = [1.0632100105285645, 1.716614007949829, 0.5249999761581421]
bar[0].rotation = [0, 0, -3.113776851171308]
bar[0].optimize = 2

