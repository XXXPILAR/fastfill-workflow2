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
    Wall(corner1=[7.06, 1.46, 0.00], corner2=[0.00, 1.46, 0.00]),
    Wall(corner1=[0.00, 1.46, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[7.06, 0.00, 0.00]),
    Wall(corner1=[7.06, 0.00, 0.00], corner2=[7.06, 1.46, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
wardrobe = Assets(description="wardrobe", size=[0.60, 1.20, 2.20], placements=[AssetInstance() for _ in range(1)])
washing_cabinet = Assets(description="washing cabinet", size=[0.65, 0.70, 0.90], placements=[AssetInstance() for _ in range(1)])

wardrobe[0].instance_id = 'wardrobe_0'
washing_cabinet[0].instance_id = 'washing_cabinet_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

wardrobe[0].position = [3.0703738846600954, 0.7182584329868895, 1.1]
wardrobe[0].rotation = [0, 0, 0]
washing_cabinet[0].position = [4.7248521947850834, 0.1880384652725552, 0.45]
washing_cabinet[0].rotation = [0, 0, 0]
wardrobe[0].position = [3.0703738846600954, 0.7182584329868895, 1.1]
wardrobe[0].rotation = [0, 0, 0]
washing_cabinet[0].position = [4.7248521947850834, 0.1880384652725552, 0.45]
washing_cabinet[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the two short end walls so neither asset blocks the windows along the
# upper wall. The wardrobe is shifted toward the upper-left corner to preserve
# as much clearance as possible in front of the lower-left door. The washing
# cabinet fits beside the lower-right door without entering its opening.
wardrobe[0].position = [0.30, 0.86, 1.10]
wardrobe[0].rotation = [0, 0, radians(0)]

washing_cabinet[0].position = [6.735, 0.35, 0.45]
washing_cabinet[0].rotation = [0, 0, radians(180)]

# Fixed markers preserve the selected positions along their respective walls.
wardrobe_target = AssetInstance(position=[0.30, 0.86, 1.10])
washing_cabinet_target = AssetInstance(position=[6.735, 0.35, 0.45])
room_center_marker = AssetInstance(position=[3.53, 0.73, 0.00])

# Wardrobe: keep it against the left end wall and facing inward.
solver.against_wall(wardrobe[0], walls[1])
solver.distance_constraint(
    wardrobe[0], wardrobe_target,
    min_distance=0.0, max_distance=0.0, weight=10
)
solver.point_towards(wardrobe[0], room_center_marker)

# Washing cabinet: keep it against the right end wall and facing inward.
solver.against_wall(washing_cabinet[0], walls[3])
solver.distance_constraint(
    washing_cabinet[0], washing_cabinet_target,
    min_distance=0.0, max_distance=0.0, weight=10
)
solver.point_towards(washing_cabinet[0], room_center_marker)

# Maintain generous separation so the assets cannot overlap if adjusted.
solver.distance_constraint(
    wardrobe[0], washing_cabinet[0],
    min_distance=5.50, max_distance=None, weight=10
)
solver.distance_constraint(
    washing_cabinet[0], wardrobe[0],
    min_distance=5.50, max_distance=None, weight=10
)

solver.constraints = []
washing_cabinet[0].position = [6.735000133514404, 0.4001557528972626, 0.44999998807907104]
washing_cabinet[0].rotation = [0, 0, -3.1415926083908112]
washing_cabinet[0].optimize = 2
wardrobe[0].position = [0.29999998211860657, 0.8098480105400085, 1.100000023841858]
wardrobe[0].rotation = [0, 0, 4.1214809475030494e-08]
wardrobe[0].optimize = 2

