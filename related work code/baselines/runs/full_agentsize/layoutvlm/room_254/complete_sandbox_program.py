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
    Wall(corner1=[0.00, 3.62, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.23, 0.00, 0.00]),
    Wall(corner1=[3.23, 0.00, 0.00], corner2=[3.23, 3.62, 0.00]),
    Wall(corner1=[3.23, 3.62, 0.00], corner2=[0.00, 3.62, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bookcase_A = Assets(description="bookcase", size=[0.30, 0.80, 1.80], placements=[AssetInstance() for _ in range(1)])
desk = Assets(description="desk", size=[0.60, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
ornaments = Assets(description="ornaments", size=[0.12, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
bookcase_B = Assets(description="bookcase", size=[0.30, 0.80, 1.80], placements=[AssetInstance() for _ in range(1)])
chair = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])

bookcase_A[0].instance_id = 'bookcase_A_0'
desk[0].instance_id = 'desk_0'
ornaments[0].instance_id = 'ornaments_0'
bookcase_B[0].instance_id = 'bookcase_B_0'
chair[0].instance_id = 'chair_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

bookcase_A[0].position = [2.4846149025167774, 1.4346512446609028, 0.9]
bookcase_A[0].rotation = [0, 0, 0]
desk[0].position = [1.5056128561768118, 0.36344340463286456, 0.375]
desk[0].rotation = [0, 0, 0]
ornaments[0].position = [0.9567639196651441, 0.8022901802534966, 0.125]
ornaments[0].rotation = [0, 0, 0]
bookcase_B[0].position = [1.1206844064213892, 2.781792157984537, 0.9]
bookcase_B[0].rotation = [0, 0, 0]
chair[0].position = [0.9749350706916955, 1.928795134599025, 0.425]
chair[0].rotation = [0, 0, 0]
bookcase_A[0].position = [2.4846149025167774, 1.4346512446609028, 0.9]
bookcase_A[0].rotation = [0, 0, 0]
desk[0].position = [1.5056128561768118, 0.36344340463286456, 0.375]
desk[0].rotation = [0, 0, 0]
ornaments[0].position = [0.9567639196651441, 0.8022901802534966, 0.125]
ornaments[0].rotation = [0, 0, 0]
bookcase_B[0].position = [1.1206844064213892, 2.781792157984537, 0.9]
bookcase_B[0].rotation = [0, 0, 0]
chair[0].position = [0.9749350706916955, 1.928795134599025, 0.425]
chair[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the two bookcases on separate sections of the right wall. Their fronts
# face into the room, while the central aisle and both door approaches remain clear.
bookcase_A[0].position = [3.08, 1.25, 0.90]
bookcase_A[0].rotation = [0, 0, radians(180)]

bookcase_B[0].position = [3.08, 2.55, 0.90]
bookcase_B[0].rotation = [0, 0, radians(180)]

# Place the desk toward the center-left, facing the two bookcases. This leaves
# clearance around the bottom door, the left-wall door, and the top window.
desk[0].position = [1.35, 1.90, 0.375]
desk[0].rotation = [0, 0, radians(0)]

# Put the ornaments at the center of the desktop.
ornaments[0].position = [1.35, 1.90, 0.875]
ornaments[0].rotation = [0, 0, radians(0)]

# Place the chair beside bookcase_A with approximately 0.22 m of edge-to-edge
# clearance (0.63 m center distance), satisfying the requested 0.30 m proximity.
# It is angled toward the desk and does not overlap either piece of furniture.
chair[0].position = [2.45, 1.25, 0.425]
chair[0].rotation = [0, 0, radians(145)]

# Fixed points preserve the functional initial arrangement during adjustment.
desk_anchor = AssetInstance(position=[1.35, 1.90, 0.375])
ornaments_anchor = AssetInstance(position=[1.35, 1.90, 0.875])
chair_anchor = AssetInstance(position=[2.45, 1.25, 0.425])

# Wall attachment is the primary positional requirement for both bookcases.
solver.against_wall(bookcase_A[0], walls[2])
solver.against_wall(bookcase_B[0], walls[2])

# Keep bookcase_A close to the chair. The center-distance limits account for
# their bounding-box depths and permit no more than 0.30 m between their edges.
solver.distance_constraint(
    bookcase_A[0], chair[0],
    min_distance=0.41, max_distance=0.71, weight=10
)

# Both bookcases face inward toward the desk.
solver.point_towards(bookcase_A[0], desk[0])
solver.point_towards(bookcase_B[0], desk[0])

# Keep the desk in the selected clear central-left location. Its two facing
# constraints encode the requirement that it face both bookcases.
solver.distance_constraint(
    desk[0], desk_anchor,
    min_distance=0, max_distance=0, weight=10
)
solver.point_towards(desk[0], bookcase_B[0])
solver.point_towards(desk[0], bookcase_A[0])

# The ornaments remain supported by and aligned with the desk. The anchor is
# also a position-based constraint for this small asset.
solver.on_top_of(ornaments[0], desk[0])
solver.distance_constraint(
    ornaments[0], ornaments_anchor,
    min_distance=0, max_distance=0, weight=10
)
solver.align_with(ornaments[0], desk[0])

# Keep the chair beside bookcase_A and oriented toward the working surface.
solver.distance_constraint(
    chair[0], bookcase_A[0],
    min_distance=0.41, max_distance=0.71, weight=10
)
solver.distance_constraint(
    chair[0], chair_anchor,
    min_distance=0, max_distance=0, weight=1
)
solver.point_towards(chair[0], desk[0])

solver.constraints = []
bookcase_B[0].position = [3.075137138366699, 2.5524003505706787, 0.8999999761581421]
bookcase_B[0].rotation = [0, 0, 3.1415397934489433]
bookcase_B[0].optimize = 2
ornaments[0].position = [1.350000023841858, 1.899999976158142, 0.875]
ornaments[0].rotation = [0, 0, 0.1363239001865646]
ornaments[0].optimize = 2
desk[0].position = [1.350000023841858, 1.899999976158142, 0.375]
desk[0].rotation = [0, 0, 0.13634704292420813]
desk[0].optimize = 2
bookcase_A[0].position = [3.0750718116760254, 1.245306134223938, 0.8999999761581421]
bookcase_A[0].rotation = [0, 0, 3.141547568750513]
bookcase_A[0].optimize = 2
chair[0].position = [2.450000047683716, 1.25, 0.42500001192092896]
chair[0].rotation = [0, 0, 2.546435351291427]
chair[0].optimize = 2

