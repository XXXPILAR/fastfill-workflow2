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
    Wall(corner1=[3.17, 0.00, 0.00], corner2=[3.17, 2.63, 0.00]),
    Wall(corner1=[3.17, 2.63, 0.00], corner2=[1.08, 2.63, 0.00]),
    Wall(corner1=[1.08, 2.63, 0.00], corner2=[1.08, 3.21, 0.00]),
    Wall(corner1=[1.08, 3.21, 0.00], corner2=[0.00, 3.21, 0.00]),
    Wall(corner1=[0.00, 3.21, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.17, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
chair = Assets(description="chair", size=[0.65, 0.65, 1.00], placements=[AssetInstance() for _ in range(1)])
desk = Assets(description="desk", size=[0.70, 1.40, 0.75], placements=[AssetInstance() for _ in range(1)])
combination_sofa = Assets(description="combination sofa", size=[0.85, 1.80, 0.85], placements=[AssetInstance() for _ in range(1)])
bookshelf = Assets(description="bookshelf", size=[0.30, 0.80, 1.80], placements=[AssetInstance() for _ in range(1)])

chair[0].instance_id = 'chair_0'
desk[0].instance_id = 'desk_0'
combination_sofa[0].instance_id = 'combination_sofa_0'
bookshelf[0].instance_id = 'bookshelf_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

chair[0].position = [2.725044191006302, 0.6507420340423123, 0.5]
chair[0].rotation = [0, 0, 0]
desk[0].position = [2.3106338392587533, 0.8690695577231857, 0.375]
desk[0].rotation = [0, 0, 0]
combination_sofa[0].position = [0.25627268506025075, 0.5872987255845998, 0.425]
combination_sofa[0].rotation = [0, 0, 0]
bookshelf[0].position = [0.6910950506849626, 2.0205995989423022, 0.9]
bookshelf[0].rotation = [0, 0, 0]
chair[0].position = [2.725044191006302, 0.6507420340423123, 0.5]
chair[0].rotation = [0, 0, 0]
desk[0].position = [2.3106338392587533, 0.8690695577231857, 0.375]
desk[0].rotation = [0, 0, 0]
combination_sofa[0].position = [0.25627268506025075, 0.5872987255845998, 0.425]
combination_sofa[0].rotation = [0, 0, 0]
bookshelf[0].position = [0.6910950506849626, 2.0205995989423022, 0.9]
bookshelf[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the sofa along the left wall, leaving the central and right-side
# circulation paths open.
combination_sofa[0].position = [0.425, 1.45, 0.425]
combination_sofa[0].rotation = [0, 0, radians(0)]

# Form a compact workstation along the bottom wall. The chair remains far
# enough from the desk for comfortable use while staying out of the doorway.
desk[0].position = [1.70, 0.35, 0.375]
desk[0].rotation = [0, 0, radians(90)]

chair[0].position = [1.70, 1.45, 0.50]
chair[0].rotation = [0, 0, radians(-90)]

# Put the shallow bookshelf on the lower portion of the right wall, below the
# door opening. It faces into the room and does not obstruct the door.
bookshelf[0].position = [3.02, 0.65, 0.90]
bookshelf[0].rotation = [0, 0, radians(180)]

# Fixed anchors preserve the selected functional zones if the solver adjusts
# the arrangement for physical feasibility.
sofa_anchor = AssetInstance(position=[0.425, 1.45, 0.425])
desk_anchor = AssetInstance(position=[1.70, 0.35, 0.375])
chair_anchor = AssetInstance(position=[1.70, 1.45, 0.50])
bookshelf_anchor = AssetInstance(position=[3.02, 0.65, 0.90])

# The sofa's wall relationship is the primary layout requirement.
solver.against_wall(combination_sofa[0], walls[4])
solver.distance_constraint(
    combination_sofa[0], sofa_anchor, 0, 0, weight=10
)
solver.point_towards(combination_sofa[0], chair[0])

# Keep the desk against the bottom wall and make its front face the chair.
solver.against_wall(desk[0], walls[5])
solver.distance_constraint(desk[0], desk_anchor, 0, 0, weight=10)
solver.point_towards(desk[0], chair[0])

# Anchor the chair opposite the desk and orient it toward the work surface.
solver.distance_constraint(chair[0], chair_anchor, 0, 0, weight=10)
solver.point_towards(chair[0], desk[0])
solver.distance_constraint(chair[0], desk[0], 1.10, 1.10, weight=5)

# Keep the bookshelf against the right wall, below the door, and orient its
# accessible front toward the room.
solver.against_wall(bookshelf[0], walls[0])
solver.distance_constraint(
    bookshelf[0], bookshelf_anchor, 0, 0, weight=10
)
solver.align_with(bookshelf[0], combination_sofa[0], angle=180)

# Additional spacing constraints preserve clear circulation and prevent the
# independently adjustable furniture groups from drifting into one another.
solver.distance_constraint(chair[0], combination_sofa[0], 1.20, None, weight=5)
solver.distance_constraint(chair[0], bookshelf[0], 1.30, None, weight=5)
solver.distance_constraint(desk[0], bookshelf[0], 1.25, None, weight=5)

solver.constraints = []
bookshelf[0].position = [3.0180001258850098, 0.6499999761581421, 0.8999999761581421]
bookshelf[0].rotation = [0, 0, -3.141592623240951]
bookshelf[0].optimize = 2
desk[0].position = [1.7000000476837158, 0.34999996423721313, 0.375]
desk[0].rotation = [0, 0, 1.570796347390409]
desk[0].optimize = 2
combination_sofa[0].position = [0.42500004172325134, 1.4500000476837158, 0.42500001192092896]
combination_sofa[0].rotation = [0, 0, 3.57907036688737e-08]
combination_sofa[0].optimize = 2
chair[0].position = [1.7000000476837158, 1.4500205516815186, 0.5]
chair[0].rotation = [0, 0, -1.5456635866850408]
chair[0].optimize = 2

