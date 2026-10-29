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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.05, 0.00, 0.00]),
    Wall(corner1=[2.05, 0.00, 0.00], corner2=[2.05, 3.66, 0.00]),
    Wall(corner1=[2.05, 3.66, 0.00], corner2=[1.36, 3.66, 0.00]),
    Wall(corner1=[1.36, 3.66, 0.00], corner2=[1.36, 3.06, 0.00]),
    Wall(corner1=[1.36, 3.06, 0.00], corner2=[0.60, 3.06, 0.00]),
    Wall(corner1=[0.60, 3.06, 0.00], corner2=[0.60, 1.62, 0.00]),
    Wall(corner1=[0.60, 1.62, 0.00], corner2=[0.00, 1.62, 0.00]),
    Wall(corner1=[0.00, 1.62, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
children_cabinet_A = Assets(description="A tall, multi-shelved bookshelf with a combination of open shelves and closed cabinets at the bottom. It holds various items such as books, decorative vases, and a potted plant.", size=[0.35, 0.80, 1.90], placements=[AssetInstance() for _ in range(1)])
children_cabinet_B = Assets(description="A tall wooden wardrobe with a dark brown finish and a simple design. It features two doors that open outward, revealing an interior space. The wardrobe has a clean and modern look.", size=[0.60, 1.00, 2.00], placements=[AssetInstance() for _ in range(1)])

children_cabinet_A[0].instance_id = 'children_cabinet_A_0'
children_cabinet_B[0].instance_id = 'children_cabinet_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

children_cabinet_A[0].position = [0.9936473961819202, 0.8288135633586605, 0.95]
children_cabinet_A[0].rotation = [0, 0, 0]
children_cabinet_B[0].position = [1.3087596263116035, 0.7617438494815341, 1.0]
children_cabinet_B[0].rotation = [0, 0, 0]
children_cabinet_A[0].position = [0.9936473961819202, 0.8288135633586605, 0.95]
children_cabinet_A[0].rotation = [0, 0, 0]
children_cabinet_B[0].position = [1.3087596263116035, 0.7617438494815341, 1.0]
children_cabinet_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Place both cabinets along the south wall, facing north into the room.
# Their footprints are:
# B: x=[0.05, 1.05], y=[0.00, 0.60]
# A: x=[1.10, 1.90], y=[0.00, 0.35]
# The 0.05 m side gap satisfies the requested proximity without overlap.
# This keeps the doorway at (0.60, 2.49) and its approach unobstructed.
children_cabinet_B[0].position = [0.55, 0.30, 1.00]
children_cabinet_B[0].rotation = [0, 0, radians(90)]

children_cabinet_A[0].position = [1.50, 0.175, 0.95]
children_cabinet_A[0].rotation = [0, 0, radians(90)]

# Prioritize wall contact and inward-facing orientations.
solver.against_wall(children_cabinet_B[0], walls[0])
solver.align_with(
    children_cabinet_B[0],
    AssetInstance(rotation=[0, 0, radians(90)])
)
solver.against_wall(children_cabinet_A[0], walls[0])
solver.align_with(children_cabinet_A[0], children_cabinet_B[0])

# Retain the chosen positions along the wall, away from the doorway.
solver.distance_constraint(
    children_cabinet_B[0],
    AssetInstance(position=[0.55, 0.30, 1.00]),
    0, 0, weight=10
)
solver.distance_constraint(
    children_cabinet_A[0],
    AssetInstance(position=[1.50, 0.175, 0.95]),
    0, 0, weight=10
)

# Distance constraints measure 3D center distances, not surface gaps.
# With wall-aligned backs, center offsets in y and z are 0.125 and 0.05.
# A 0–0.10 m side gap corresponds to an x-center offset of 0.90–1.00 m.
solver.distance_constraint(
    children_cabinet_A[0],
    children_cabinet_B[0],
    (0.90**2 + 0.125**2 + 0.05**2)**0.5,
    (1.00**2 + 0.125**2 + 0.05**2)**0.5,
    weight=10
)

solver.constraints = []
children_cabinet_A[0].position = [1.6441082954406738, 1.3875402212142944, 0.949999988079071]
children_cabinet_A[0].rotation = [0, 0, -0.1201005774049127]
children_cabinet_A[0].optimize = 2
children_cabinet_B[0].position = [0.9021247625350952, 1.9489586353302002, 1.0]
children_cabinet_B[0].rotation = [0, 0, -0.01003784228302477]
children_cabinet_B[0].optimize = 2

