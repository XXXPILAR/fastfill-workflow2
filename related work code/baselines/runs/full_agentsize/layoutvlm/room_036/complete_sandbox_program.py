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
    Wall(corner1=[3.79, 2.77, 0.00], corner2=[0.00, 2.77, 0.00]),
    Wall(corner1=[0.00, 2.77, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.79, 0.00, 0.00]),
    Wall(corner1=[3.79, 0.00, 0.00], corner2=[3.79, 2.77, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
nightstand_A = Assets(description="A cylindrical object with vertical slats that vary in shades of gray and brown, giving it a modern and sleek appearance.", size=[0.45, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
nightstand_B = Assets(description="A cylindrical object with vertical slats that vary in shades of gray and brown, giving it a modern and sleek appearance.", size=[0.45, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])

nightstand_A[0].instance_id = 'nightstand_A_0'
nightstand_B[0].instance_id = 'nightstand_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

nightstand_A[0].position = [3.3655192754829906, 2.276989974998923, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
nightstand_B[0].position = [0.5939898902511079, 1.0537932426169623, 0.275]
nightstand_B[0].rotation = [0, 0, 0]
nightstand_A[0].position = [3.3655192754829906, 2.276989974998923, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
nightstand_B[0].position = [0.5939898902511079, 1.0537932426169623, 0.275]
nightstand_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Place both nightstands against the upper wall, with generous separation so
# they remain accessible and do not overlap. Their centers sit half their
# height above the floor and one radius inward from the wall.
nightstand_A[0].position = [1.10, 2.545, 0.275]
nightstand_A[0].rotation = [0, 0, radians(-90)]

nightstand_B[0].position = [2.69, 2.545, 0.275]
nightstand_B[0].rotation = [0, 0, radians(-90)]

# Fixed reference points preserve the intended locations along the upper wall.
nightstand_A_anchor = AssetInstance(position=[1.10, 2.545, 0.275])
nightstand_B_anchor = AssetInstance(position=[2.69, 2.545, 0.275])
room_center_reference = AssetInstance(position=[1.895, 1.385, 0.275])

# Wall contact is the primary positional requirement for both nightstands.
solver.against_wall(nightstand_A[0], walls[0])
solver.against_wall(nightstand_B[0], walls[0])

# Keep each nightstand in its designated part of the wall and maintain enough
# clearance between the two 0.45 m diameter objects.
solver.distance_constraint(
    nightstand_A[0], nightstand_A_anchor,
    min_distance=0, max_distance=0, weight=10
)
solver.distance_constraint(
    nightstand_B[0], nightstand_B_anchor,
    min_distance=0, max_distance=0, weight=10
)
solver.distance_constraint(
    nightstand_B[0], nightstand_A[0],
    min_distance=1.40, max_distance=1.80, weight=10
)

# Orient both objects inward toward the usable center of the room.
solver.point_towards(nightstand_A[0], room_center_reference)
solver.point_towards(nightstand_B[0], room_center_reference)

solver.constraints = []
nightstand_A[0].position = [1.1001222133636475, 2.542980432510376, 0.2750000059604645]
nightstand_A[0].rotation = [0, 0, -1.571065180656679]
nightstand_A[0].optimize = 2
nightstand_B[0].position = [2.6893742084503174, 2.542562961578369, 0.2750000059604645]
nightstand_B[0].rotation = [0, 0, -1.5710651972355774]
nightstand_B[0].optimize = 2

