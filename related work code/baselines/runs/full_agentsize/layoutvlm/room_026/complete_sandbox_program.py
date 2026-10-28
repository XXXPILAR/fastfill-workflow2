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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.38, 0.00, 0.00]),
    Wall(corner1=[3.38, 0.00, 0.00], corner2=[3.38, 2.95, 0.00]),
    Wall(corner1=[3.38, 2.95, 0.00], corner2=[0.00, 2.95, 0.00]),
    Wall(corner1=[0.00, 2.95, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
lounge_chair_A = Assets(description="An ergonomic office chair with a high backrest and armrests, designed for comfort during long hours of work. It features a swivel base with wheels for easy mobility.", size=[0.68, 0.68, 1.15], placements=[AssetInstance() for _ in range(1)])
desk_A = Assets(description="A wooden desk with a metal frame and a storage unit attached to it. The desk has a flat surface for writing or working and includes a small cabinet with a door and shelves inside.", size=[0.60, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
bookcase_A = Assets(description="A modern wall-mounted cabinet with a combination of wooden and gray panels. It features multiple shelves and compartments for storage.", size=[0.32, 0.60, 0.65], placements=[AssetInstance() for _ in range(1)])
sideboard = Assets(description="A wooden dresser with multiple drawers and cabinets, topped with decorative items such as a lamp, vases, and spheres.", size=[0.45, 1.40, 0.82], placements=[AssetInstance() for _ in range(1)])
bookcase_B = Assets(description="A modern wall-mounted cabinet with a combination of wooden and gray panels. It features multiple shelves and compartments for storage.", size=[0.32, 0.60, 0.65], placements=[AssetInstance() for _ in range(1)])
bookcase_C = Assets(description="A modern wall-mounted cabinet with a combination of wooden and gray panels. It features multiple shelves and compartments for storage.", size=[0.32, 0.60, 0.65], placements=[AssetInstance() for _ in range(1)])
bookcase_D = Assets(description="A modern wall-mounted cabinet with a combination of wooden and gray panels. It features multiple shelves and compartments for storage.", size=[0.32, 0.60, 0.65], placements=[AssetInstance() for _ in range(1)])
desk_B = Assets(description="A wooden desk with a metal frame and a storage unit attached to it. The desk has a flat surface for writing or working and includes a small cabinet with a door and shelves inside.", size=[0.60, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
bookcase_E = Assets(description="A modern wall-mounted cabinet with a combination of wooden and gray panels. It features multiple shelves and compartments for storage.", size=[0.32, 0.60, 0.65], placements=[AssetInstance() for _ in range(1)])
lounge_chair_B = Assets(description="An ergonomic office chair with a high backrest and armrests, designed for comfort during long hours of work. It features a swivel base with wheels for easy mobility.", size=[0.68, 0.68, 1.15], placements=[AssetInstance() for _ in range(1)])

lounge_chair_A[0].instance_id = 'lounge_chair_A_0'
desk_A[0].instance_id = 'desk_A_0'
bookcase_A[0].instance_id = 'bookcase_A_0'
sideboard[0].instance_id = 'sideboard_0'
bookcase_B[0].instance_id = 'bookcase_B_0'
bookcase_C[0].instance_id = 'bookcase_C_0'
bookcase_D[0].instance_id = 'bookcase_D_0'
desk_B[0].instance_id = 'desk_B_0'
bookcase_E[0].instance_id = 'bookcase_E_0'
lounge_chair_B[0].instance_id = 'lounge_chair_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

lounge_chair_A[0].position = [1.2900980485267868, 2.577032003152488, 0.575]
lounge_chair_A[0].rotation = [0, 0, 0]
desk_A[0].position = [0.3713180817166092, 1.1141474605836428, 0.375]
desk_A[0].rotation = [0, 0, 0]
bookcase_A[0].position = [2.64442771422305, 0.4531405892215753, 0.325]
bookcase_A[0].rotation = [0, 0, 0]
sideboard[0].position = [2.5828814967606175, 0.6865981138870049, 0.41]
sideboard[0].rotation = [0, 0, 0]
bookcase_B[0].position = [0.07260658606052992, 2.2455268002129376, 0.325]
bookcase_B[0].rotation = [0, 0, 0]
bookcase_C[0].position = [1.481372115724414, 0.1647780198753472, 0.325]
bookcase_C[0].rotation = [0, 0, 0]
bookcase_D[0].position = [1.798495036991873, 0.4789126366315887, 0.325]
bookcase_D[0].rotation = [0, 0, 0]
desk_B[0].position = [3.05414116170876, 1.4756894026014518, 0.375]
desk_B[0].rotation = [0, 0, 0]
bookcase_E[0].position = [3.0226369186998734, 2.8338674428352473, 0.325]
bookcase_E[0].rotation = [0, 0, 0]
lounge_chair_B[0].position = [1.1874481623702067, 2.8729708141722905, 0.575]
lounge_chair_B[0].rotation = [0, 0, 0]
lounge_chair_A[0].position = [1.2900980485267868, 2.577032003152488, 0.575]
lounge_chair_A[0].rotation = [0, 0, 0]
desk_A[0].position = [0.3713180817166092, 1.1141474605836428, 0.375]
desk_A[0].rotation = [0, 0, 0]
bookcase_A[0].position = [2.64442771422305, 0.4531405892215753, 0.325]
bookcase_A[0].rotation = [0, 0, 0]
sideboard[0].position = [2.5828814967606175, 0.6865981138870049, 0.41]
sideboard[0].rotation = [0, 0, 0]
bookcase_B[0].position = [0.07260658606052992, 2.2455268002129376, 0.325]
bookcase_B[0].rotation = [0, 0, 0]
bookcase_C[0].position = [1.481372115724414, 0.1647780198753472, 0.325]
bookcase_C[0].rotation = [0, 0, 0]
bookcase_D[0].position = [1.798495036991873, 0.4789126366315887, 0.325]
bookcase_D[0].rotation = [0, 0, 0]
desk_B[0].position = [3.05414116170876, 1.4756894026014518, 0.375]
desk_B[0].rotation = [0, 0, 0]
bookcase_E[0].position = [3.0226369186998734, 2.8338674428352473, 0.325]
bookcase_E[0].rotation = [0, 0, 0]
lounge_chair_B[0].position = [1.1874481623702067, 2.8729708141722905, 0.575]
lounge_chair_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the two desks on opposing side walls. This makes lounge_chair_A
# (o0000) lie clearly between desk_A (o0001) and desk_B (o0007).
desk_A[0].position = [0.30, 0.95, 0.375]
desk_A[0].rotation = [0, 0, radians(0)]

desk_B[0].position = [3.08, 0.95, 0.375]
desk_B[0].rotation = [0, 0, radians(180)]

lounge_chair_A[0].position = [1.69, 0.95, 0.575]
lounge_chair_A[0].rotation = [0, 0, radians(180)]

# Place the second chair near desk_B while preserving a clear central aisle.
lounge_chair_B[0].position = [2.25, 1.85, 0.575]
lounge_chair_B[0].rotation = [0, 0, radians(0)]

# The shallow cabinets form a row along the north wall. Rotating them by
# -90 degrees puts their 0.32 m depth perpendicular to that wall.
bookcase_A[0].position = [0.30, 2.79, 0.325]
bookcase_A[0].rotation = [0, 0, radians(-90)]

bookcase_B[0].position = [0.95, 2.79, 0.325]
bookcase_B[0].rotation = [0, 0, radians(-90)]

bookcase_C[0].position = [1.60, 2.79, 0.325]
bookcase_C[0].rotation = [0, 0, radians(-90)]

bookcase_D[0].position = [2.25, 2.79, 0.325]
bookcase_D[0].rotation = [0, 0, radians(-90)]

bookcase_E[0].position = [2.90, 2.79, 0.325]
bookcase_E[0].rotation = [0, 0, radians(-90)]

# Put the sideboard against the south wall, away from both desk footprints.
sideboard[0].position = [1.69, 0.225, 0.41]
sideboard[0].rotation = [0, 0, radians(90)]

# Fixed anchors preserve the intended zones if the solver adjusts the layout.
desk_A_anchor = AssetInstance(position=[0.30, 0.95, 0.375])
desk_B_anchor = AssetInstance(position=[3.08, 0.95, 0.375])
chair_A_anchor = AssetInstance(position=[1.69, 0.95, 0.575])
chair_B_anchor = AssetInstance(position=[2.25, 1.85, 0.575])
bookcase_A_anchor = AssetInstance(position=[0.30, 2.79, 0.325])
bookcase_B_anchor = AssetInstance(position=[0.95, 2.79, 0.325])
bookcase_C_anchor = AssetInstance(position=[1.60, 2.79, 0.325])
bookcase_D_anchor = AssetInstance(position=[2.25, 2.79, 0.325])
bookcase_E_anchor = AssetInstance(position=[2.90, 2.79, 0.325])
sideboard_anchor = AssetInstance(position=[1.69, 0.225, 0.41])

# Important position constraints are listed first.
solver.distance_constraint(desk_A[0], desk_A_anchor, 0, 0, weight=10)
solver.distance_constraint(desk_B[0], desk_B_anchor, 0, 0, weight=10)
solver.distance_constraint(lounge_chair_A[0], chair_A_anchor, 0, 0, weight=10)
solver.distance_constraint(lounge_chair_B[0], chair_B_anchor, 0, 0, weight=10)
solver.distance_constraint(bookcase_A[0], bookcase_A_anchor, 0, 0, weight=10)
solver.distance_constraint(bookcase_B[0], bookcase_B_anchor, 0, 0, weight=10)
solver.distance_constraint(bookcase_C[0], bookcase_C_anchor, 0, 0, weight=10)
solver.distance_constraint(bookcase_D[0], bookcase_D_anchor, 0, 0, weight=10)
solver.distance_constraint(bookcase_E[0], bookcase_E_anchor, 0, 0, weight=10)
solver.distance_constraint(sideboard[0], sideboard_anchor, 0, 0, weight=10)

# Keep perimeter furniture flush with its intended wall.
solver.against_wall(desk_A[0], walls[3])
solver.against_wall(desk_B[0], walls[1])
solver.against_wall(bookcase_A[0], walls[2])
solver.against_wall(bookcase_B[0], walls[2])
solver.against_wall(bookcase_C[0], walls[2])
solver.against_wall(bookcase_D[0], walls[2])
solver.against_wall(bookcase_E[0], walls[2])
solver.against_wall(sideboard[0], walls[0])

# Both desks face inward, and each chair faces its associated desk.
solver.point_towards(desk_A[0], lounge_chair_A[0])
solver.point_towards(desk_B[0], lounge_chair_A[0])
solver.point_towards(lounge_chair_A[0], desk_A[0])
solver.point_towards(lounge_chair_B[0], desk_B[0])

# The north-wall cabinets face into the room, and the sideboard faces north.
solver.point_towards(bookcase_A[0], chair_A_anchor)
solver.point_towards(bookcase_B[0], chair_A_anchor)
solver.point_towards(bookcase_C[0], chair_A_anchor)
solver.point_towards(bookcase_D[0], chair_A_anchor)
solver.point_towards(bookcase_E[0], chair_A_anchor)
solver.point_towards(sideboard[0], chair_A_anchor)

# These semantic spacing constraints retain usable chair clearances and keep
# lounge_chair_A between the two opposing desks.
solver.distance_constraint(lounge_chair_A[0], desk_A[0], 1.30, 1.50, weight=10)
solver.distance_constraint(lounge_chair_A[0], desk_B[0], 1.30, 1.50, weight=10)
solver.distance_constraint(lounge_chair_B[0], desk_B[0], 1.10, 1.35, weight=1)
solver.distance_constraint(lounge_chair_A[0], lounge_chair_B[0], 0.95, None, weight=1)

# Maintain separation among the neighboring cabinets in the north-wall row.
solver.distance_constraint(bookcase_B[0], bookcase_A[0], 0.62, None, weight=1)
solver.distance_constraint(bookcase_C[0], bookcase_B[0], 0.62, None, weight=1)
solver.distance_constraint(bookcase_D[0], bookcase_C[0], 0.62, None, weight=1)
solver.distance_constraint(bookcase_E[0], bookcase_D[0], 0.62, None, weight=1)

solver.constraints = []
bookcase_D[0].position = [2.308647871017456, 2.7899999618530273, 0.32499998807907104]
bookcase_D[0].rotation = [0, 0, -1.5707962805023103]
bookcase_D[0].optimize = 2
bookcase_E[0].position = [2.9637768268585205, 2.7899997234344482, 0.32499998807907104]
bookcase_E[0].rotation = [0, 0, -1.5707962828071083]
bookcase_E[0].optimize = 2
bookcase_B[0].position = [0.9990857839584351, 2.7900002002716064, 0.32499998807907104]
bookcase_B[0].rotation = [0, 0, -1.5707962806677158]
bookcase_B[0].optimize = 2
sideboard[0].position = [1.690000057220459, 0.22499999403953552, 0.4099999964237213]
sideboard[0].rotation = [0, 0, 1.570796369103573]
sideboard[0].optimize = 2
lounge_chair_A[0].position = [1.690000057220459, 0.949999988079071, 0.574999988079071]
lounge_chair_A[0].rotation = [0, 0, -3.1164599134799373]
lounge_chair_A[0].optimize = 2
desk_B[0].position = [3.0799999237060547, 0.949999988079071, 0.375]
desk_B[0].rotation = [0, 0, -3.141592623443199]
desk_B[0].optimize = 2
lounge_chair_B[0].position = [2.25, 1.850000023841858, 0.574999988079071]
lounge_chair_B[0].rotation = [0, 0, -0.26284623455222245]
lounge_chair_B[0].optimize = 2
bookcase_C[0].position = [1.652571201324463, 2.7899999618530273, 0.32499998807907104]
bookcase_C[0].rotation = [0, 0, -1.570796280517399]
bookcase_C[0].optimize = 2
desk_A[0].position = [0.30000001192092896, 0.949999988079071, 0.375]
desk_A[0].rotation = [0, 0, 4.2561751444019056e-08]
desk_A[0].optimize = 2
bookcase_A[0].position = [0.35802164673805237, 2.7899997234344482, 0.32499998807907104]
bookcase_A[0].rotation = [0, 0, -1.5707962796679118]
bookcase_A[0].optimize = 2

