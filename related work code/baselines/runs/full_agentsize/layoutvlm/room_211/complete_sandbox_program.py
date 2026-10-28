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
    Wall(corner1=[2.70, 1.15, 0.00], corner2=[0.00, 1.15, 0.00]),
    Wall(corner1=[0.00, 1.15, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.08, 0.00, 0.00]),
    Wall(corner1=[6.08, 0.00, 0.00], corner2=[6.08, 3.43, 0.00]),
    Wall(corner1=[6.08, 3.43, 0.00], corner2=[2.70, 3.43, 0.00]),
    Wall(corner1=[2.70, 3.43, 0.00], corner2=[2.70, 1.15, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
desk = Assets(description="desk", size=[0.80, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
sofa = Assets(description="sofa", size=[0.90, 2.10, 0.85], placements=[AssetInstance() for _ in range(1)])
chair = Assets(description="chair", size=[0.65, 0.65, 1.00], placements=[AssetInstance() for _ in range(1)])

desk[0].instance_id = 'desk_0'
sofa[0].instance_id = 'sofa_0'
chair[0].instance_id = 'chair_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

desk[0].position = [5.909690067428654, 0.3682762305906576, 0.375]
desk[0].rotation = [0, 0, 0]
sofa[0].position = [0.5690033975661328, 0.06281407033346742, 0.425]
sofa[0].rotation = [0, 0, 0]
chair[0].position = [5.531049250523659, 2.058838167746167, 0.5]
chair[0].rotation = [0, 0, 0]
desk[0].position = [5.909690067428654, 0.3682762305906576, 0.375]
desk[0].rotation = [0, 0, 0]
sofa[0].position = [0.5690033975661328, 0.06281407033346742, 0.425]
sofa[0].rotation = [0, 0, 0]
chair[0].position = [5.531049250523659, 2.058838167746167, 0.5]
chair[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the work area along the lower wall, well away from the entrance at
# (0.00, 0.59). Rotating the desk by +90 degrees makes it face into the room.
desk[0].position = [3.20, 0.40, 0.375]
desk[0].rotation = [0, 0, radians(90)]

# The chair is directly in front of the desk. The 0.825 m horizontal
# center-to-center spacing leaves approximately 0.10 m between their edges.
chair[0].position = [3.20, 1.225, 0.50]
chair[0].rotation = [0, 0, radians(-90)]

# Put the sofa against the upper wall, facing into the room. This keeps it
# clear of both the work area and the window on the right wall.
sofa[0].position = [4.80, 2.98, 0.425]
sofa[0].rotation = [0, 0, radians(-90)]

# Fixed points preserve the selected functional zones while still allowing
# small feasibility adjustments.
desk_anchor = AssetInstance(position=[3.20, 0.40, 0.375])
chair_anchor = AssetInstance(position=[3.20, 1.225, 0.50])
sofa_anchor = AssetInstance(position=[4.80, 2.98, 0.425])
sofa_facing_target = AssetInstance(position=[4.80, 2.00, 0.425])

# Primary placement constraints.
solver.against_wall(desk[0], walls[2])
solver.against_wall(sofa[0], walls[4])

# Account for the furniture sizes when enforcing the requested chair-to-desk
# clearance. The small z-center difference makes the corresponding 3D
# center-distance range approximately 0.74–0.84 m.
solver.distance_constraint(chair[0], desk[0], 0.74, 0.84, weight=10)

# Keep each item near its intended part of the room and away from the doorway.
solver.distance_constraint(desk[0], desk_anchor, 0.00, 0.12, weight=10)
solver.distance_constraint(chair[0], chair_anchor, 0.00, 0.12, weight=10)
solver.distance_constraint(sofa[0], sofa_anchor, 0.00, 0.12, weight=10)

# Preserve non-overlapping separation between the seating and work zones.
solver.distance_constraint(sofa[0], desk[0], 1.50, None, weight=10)
solver.distance_constraint(sofa[0], chair[0], 1.50, None, weight=10)

# Required facing relationships for the work area.
solver.point_towards(desk[0], chair[0])
solver.point_towards(chair[0], desk[0])

# Orient the sofa away from its wall and toward the room interior.
solver.point_towards(sofa[0], sofa_facing_target)

solver.constraints = []
sofa[0].position = [4.800000190734863, 2.984936475753784, 0.42500001192092896]
sofa[0].rotation = [0, 0, -1.5707962875145247]
sofa[0].optimize = 2
desk[0].position = [3.200000047683716, 0.3999999761581421, 0.375]
desk[0].rotation = [0, 0, 1.5707963488554497]
desk[0].optimize = 2
chair[0].position = [3.200000047683716, 1.225000023841858, 0.5]
chair[0].rotation = [0, 0, -1.5519467713960802]
chair[0].optimize = 2

