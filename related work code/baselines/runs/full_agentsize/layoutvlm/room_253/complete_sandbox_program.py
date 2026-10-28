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
    Wall(corner1=[2.68, 0.00, 0.00], corner2=[2.68, 4.29, 0.00]),
    Wall(corner1=[2.68, 4.29, 0.00], corner2=[0.00, 4.29, 0.00]),
    Wall(corner1=[0.00, 4.29, 0.00], corner2=[0.00, 0.79, 0.00]),
    Wall(corner1=[0.00, 0.79, 0.00], corner2=[0.90, 0.79, 0.00]),
    Wall(corner1=[0.90, 0.79, 0.00], corner2=[0.90, 0.00, 0.00]),
    Wall(corner1=[0.90, 0.00, 0.00], corner2=[2.68, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
chair = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[2.30, 1.60, 0.01], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.00, 1.40, 0.55], placements=[AssetInstance() for _ in range(1)])

chair[0].instance_id = 'chair_0'
carpet[0].instance_id = 'carpet_0'
bed[0].instance_id = 'bed_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

chair[0].position = [0.6937369245946226, 2.206012685796013, 0.425]
chair[0].rotation = [0, 0, 0]
carpet[0].position = [0.4164741587600614, 3.3320483385347206, 0.005]
carpet[0].rotation = [0, 0, 0]
bed[0].position = [1.8368726014202634, 1.9780780012744363, 0.275]
bed[0].rotation = [0, 0, 0]
chair[0].position = [0.6937369245946226, 2.206012685796013, 0.425]
chair[0].rotation = [0, 0, 0]
carpet[0].position = [0.4164741587600614, 3.3320483385347206, 0.005]
carpet[0].rotation = [0, 0, 0]
bed[0].position = [1.8368726014202634, 1.9780780012744363, 0.275]
bed[0].rotation = [0, 0, 0]

solver.constraints = []

# Reference anchors preserve the intended room-relative positions and orientation.
chair_anchor = AssetInstance(position=[1.00, 2.60, 0.425])
carpet_anchor = AssetInstance(position=[1.34, 1.59, 0.005])
room_x_axis = AssetInstance(position=[1.34, 2.15, 0.00], rotation=[0, 0, 0])

# Place the bed lengthwise against the right wall. Its lower end remains well
# above the doorway, leaving the entrance and its approach unobstructed.
bed[0].position = [1.98, 2.60, 0.275]
bed[0].rotation = [0, 0, radians(90)]

# Place the chair beside the bed with a small gap and orient it toward the bed.
chair[0].position = [1.00, 2.60, 0.425]
chair[0].rotation = [0, 0, 0]

# The carpet lies fully above the lower-left recess and does not obstruct the
# door. Its very small height permits the bed and chair to stand partly on it.
carpet[0].position = [1.34, 1.59, 0.005]
carpet[0].rotation = [0, 0, 0]

# Bed constraints: keep it against the right wall and parallel to that wall.
solver.against_wall(bed[0], walls[0])
solver.align_with(bed[0], room_x_axis, angle=90)

# The center-distance bounds account for the bed's 0.70 m horizontal half-width
# after rotation and the chair's 0.26 m half-width. Thus, a center distance no
# greater than 1.46 m guarantees that their nearest edges are within 0.50 m;
# the 0.96 m lower bound prevents their bounding boxes from overlapping.
solver.distance_constraint(bed[0], chair[0], 0.96, 1.46, weight=10)

# Chair constraints: anchor its functional position beside the bed, retain the
# required near-bed relationship, and make its front face the bed.
solver.distance_constraint(chair[0], chair_anchor, 0, 0, weight=10)
solver.distance_constraint(chair[0], bed[0], 0.96, 1.46, weight=10)
solver.point_towards(chair[0], bed[0])

# Carpet constraints: anchor it within the valid footprint and align its long
# dimension with the room's x-axis.
solver.distance_constraint(carpet[0], carpet_anchor, 0, 0, weight=10)
solver.align_with(carpet[0], room_x_axis, angle=0)

solver.constraints = []
carpet[0].position = [1.340000033378601, 1.6058027744293213, 0.004999999888241291]
carpet[0].rotation = [0, 0, 0.00942477746072377]
carpet[0].optimize = 2
chair[0].position = [0.6265105605125427, 2.5999999046325684, 0.42500001192092896]
chair[0].rotation = [0, 0, 0.0157079639172164]
chair[0].optimize = 2
bed[0].position = [1.6793382167816162, 2.5999999046325684, 0.2750000059604645]
bed[0].rotation = [0, 0, 3.140646661834708]
bed[0].optimize = 2

