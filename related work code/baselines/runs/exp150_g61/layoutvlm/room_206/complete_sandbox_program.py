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
    Wall(corner1=[0.71, 3.80, 0.00], corner2=[0.71, 3.20, 0.00]),
    Wall(corner1=[0.71, 3.20, 0.00], corner2=[0.30, 3.20, 0.00]),
    Wall(corner1=[0.30, 3.20, 0.00], corner2=[0.30, 2.94, 0.00]),
    Wall(corner1=[0.30, 2.94, 0.00], corner2=[0.00, 2.94, 0.00]),
    Wall(corner1=[0.00, 2.94, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.45, 0.00, 0.00]),
    Wall(corner1=[3.45, 0.00, 0.00], corner2=[3.45, 0.30, 0.00]),
    Wall(corner1=[3.45, 0.30, 0.00], corner2=[3.87, 0.30, 0.00]),
    Wall(corner1=[3.87, 0.30, 0.00], corner2=[3.87, 2.94, 0.00]),
    Wall(corner1=[3.87, 2.94, 0.00], corner2=[3.45, 2.94, 0.00]),
    Wall(corner1=[3.45, 2.94, 0.00], corner2=[3.45, 3.20, 0.00]),
    Wall(corner1=[3.45, 3.20, 0.00], corner2=[2.73, 3.20, 0.00]),
    Wall(corner1=[2.73, 3.20, 0.00], corner2=[2.73, 3.80, 0.00]),
    Wall(corner1=[2.73, 3.80, 0.00], corner2=[0.71, 3.80, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
wardrobe = Assets(description="wardrobe", size=[0.60, 1.80, 2.20], placements=[AssetInstance() for _ in range(1)])
dining_chair = Assets(description="dining chair", size=[0.52, 0.46, 0.88], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.05, 1.40, 0.95], placements=[AssetInstance() for _ in range(1)])

wardrobe[0].instance_id = 'wardrobe_0'
dining_chair[0].instance_id = 'dining_chair_0'
bed[0].instance_id = 'bed_0'
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
walls[12].instance_id = 'walls_12'
walls[13].instance_id = 'walls_13'

wardrobe[0].position = [0.7097346605444587, 1.8472429959172132, 1.1]
wardrobe[0].rotation = [0, 0, 0]
dining_chair[0].position = [3.7664000725898785, 2.300250948500568, 0.44]
dining_chair[0].rotation = [0, 0, 0]
bed[0].position = [2.367817208388823, 0.6736412352585764, 0.475]
bed[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.7097346605444587, 1.8472429959172132, 1.1]
wardrobe[0].rotation = [0, 0, 0]
dining_chair[0].position = [3.7664000725898785, 2.300250948500568, 0.44]
dining_chair[0].rotation = [0, 0, 0]
bed[0].position = [2.367817208388823, 0.6736412352585764, 0.475]
bed[0].rotation = [0, 0, 0]

solver.constraints = []

# Put the bed against the west wall, with its foot facing east toward
# the chair. Its footprint is x=[0, 2.05], y=[1.40, 2.80], entirely
# within the main room and clear of the northern window recess.
bed[0].position = [1.025, 2.10, bed.size[2] / 2]
bed[0].rotation = [0, 0, radians(0)]

# Place the wardrobe along the southern wall, facing north.
# Its rotated footprint is x=[0.05, 1.85], y=[0, 0.60], leaving
# the doorway at x=[2.67, 3.45] and its approach unobstructed.
wardrobe[0].position = [0.95, 0.30, wardrobe.size[2] / 2]
wardrobe[0].rotation = [0, 0, radians(90)]

# The chair faces the bed across a 0.54 m gap between their footprints.
# It stays away from the windows and leaves the southern entry area open.
dining_chair[0].position = [2.85, 2.10, dining_chair.size[2] / 2]
dining_chair[0].rotation = [0, 0, radians(180)]

# Prioritize the chosen, collision-free positions. Fixed-point constraints
# also preserve the circulation space without moving any existing geometry.
solver.distance_constraint(
    bed[0],
    AssetInstance(position=[1.025, 2.10, bed.size[2] / 2]),
    0, 0, weight=10
)
solver.distance_constraint(
    wardrobe[0],
    AssetInstance(position=[0.95, 0.30, wardrobe.size[2] / 2]),
    0, 0, weight=10
)
solver.distance_constraint(
    dining_chair[0],
    AssetInstance(position=[2.85, 2.10, dining_chair.size[2] / 2]),
    0, 0, weight=10
)

# Explicitly preserve the requested bed-to-chair facing relationship.
solver.point_towards(bed[0], dining_chair[0])
solver.point_towards(dining_chair[0], bed[0])

# The wardrobe's front faces into the room, rather than into its wall.
solver.point_towards(
    wardrobe[0],
    AssetInstance(position=[0.95, 1.30, wardrobe.size[2] / 2])
)

# Reinforce the intended wall contacts after the primary placement constraints.
solver.against_wall(bed[0], walls[4])
solver.against_wall(wardrobe[0], walls[5])

# All three assets are floor-standing; no on_top_of constraints are needed.

solver.constraints = []
wardrobe[0].position = [0.949999988079071, 0.3112857937812805, 1.100000023841858]
wardrobe[0].rotation = [0, 0, 1.5707963697503287]
wardrobe[0].optimize = 2
dining_chair[0].position = [2.8499999046325684, 2.0999999046325684, 0.4399999976158142]
dining_chair[0].rotation = [0, 0, 2.8566018997206535]
dining_chair[0].optimize = 2
bed[0].position = [1.644107460975647, 3.007335662841797, 0.4749999940395355]
bed[0].rotation = [0, 0, -0.09352502269580923]
bed[0].optimize = 2

