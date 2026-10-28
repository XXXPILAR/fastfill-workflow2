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
    Wall(corner1=[2.77, 3.05, 0.00], corner2=[0.00, 3.05, 0.00]),
    Wall(corner1=[0.00, 3.05, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.77, 0.00, 0.00]),
    Wall(corner1=[2.77, 0.00, 0.00], corner2=[2.77, 3.05, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
chair = Assets(description="chair", size=[0.52, 0.50, 0.85], placements=[AssetInstance() for _ in range(1)])
multifunctional_combination_bed = Assets(description="multifunctional combination bed", size=[1.10, 2.05, 1.80], placements=[AssetInstance() for _ in range(1)])

chair[0].instance_id = 'chair_0'
multifunctional_combination_bed[0].instance_id = 'multifunctional_combination_bed_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

chair[0].position = [2.0779018047381492, 2.307430433607539, 0.425]
chair[0].rotation = [0, 0, 0]
multifunctional_combination_bed[0].position = [0.3660154281170982, 1.4444881209343958, 0.9]
multifunctional_combination_bed[0].rotation = [0, 0, 0]
chair[0].position = [2.0779018047381492, 2.307430433607539, 0.425]
chair[0].rotation = [0, 0, 0]
multifunctional_combination_bed[0].position = [0.3660154281170982, 1.4444881209343958, 0.9]
multifunctional_combination_bed[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the bed lengthwise along the left wall. Its front faces into the room,
# while its position leaves both the window and the entrance circulation clear.
multifunctional_combination_bed[0].position = [0.55, 1.55, 0.90]
multifunctional_combination_bed[0].rotation = [0, 0, radians(0)]

# Place the chair near the upper-right corner, away from the door's approach
# path, and turn it toward the bed.
chair[0].position = [2.51, 2.65, 0.425]
chair[0].rotation = [0, 0, radians(210)]

# Fixed references preserve the intended locations along their respective walls.
bed_anchor = AssetInstance(position=[0.55, 1.55, 0.90])
chair_anchor = AssetInstance(position=[2.51, 2.65, 0.425])

# The bed's primary requirement is to remain against the left wall.
solver.against_wall(multifunctional_combination_bed[0], walls[1])
solver.distance_constraint(
    multifunctional_combination_bed[0], bed_anchor,
    min_distance=0.0, max_distance=0.0, weight=10
)

# Keep the bed parallel to its anchor orientation so its long dimension follows
# the left wall and its accessible side faces the open part of the room.
solver.align_with(multifunctional_combination_bed[0], bed_anchor)

# Keep the chair against the right wall and localized in the upper-right area,
# safely beyond the floor space directly in front of the door.
solver.against_wall(chair[0], walls[3])
solver.distance_constraint(
    chair[0], chair_anchor,
    min_distance=0.0, max_distance=0.0, weight=10
)

# Orient the chair toward the bed for a functional relationship between them.
solver.point_towards(chair[0], multifunctional_combination_bed[0])

# Maintain useful separation between the two assets and prevent overlap while
# allowing a modest amount of adjustment during feasibility solving.
solver.distance_constraint(
    chair[0], multifunctional_combination_bed[0],
    min_distance=1.80, max_distance=2.50, weight=1
)

solver.constraints = []
chair[0].position = [2.507624864578247, 2.6500000953674316, 0.42500001192092896]
chair[0].rotation = [0, 0, -3.1415925783884493]
chair[0].optimize = 2
multifunctional_combination_bed[0].position = [0.550000011920929, 1.5499999523162842, 0.8999999761581421]
multifunctional_combination_bed[0].rotation = [0, 0, 3.373768988821543e-08]
multifunctional_combination_bed[0].optimize = 2

