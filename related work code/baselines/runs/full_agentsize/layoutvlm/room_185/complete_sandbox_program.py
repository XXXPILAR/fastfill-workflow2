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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.00, 0.00, 0.00]),
    Wall(corner1=[3.00, 0.00, 0.00], corner2=[3.00, 2.40, 0.00]),
    Wall(corner1=[3.00, 2.40, 0.00], corner2=[0.00, 2.40, 0.00]),
    Wall(corner1=[0.00, 2.40, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bathroom_mat = Assets(description="bathroom mat", size=[0.50, 0.80, 0.01], placements=[AssetInstance() for _ in range(1)])
mirror = Assets(description="mirror", size=[0.04, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
poster_print = Assets(description="poster print", size=[0.02, 0.40, 0.60], placements=[AssetInstance() for _ in range(1)])
bathroom_vanity = Assets(description="bathroom vanity", size=[0.55, 1.00, 0.85], placements=[AssetInstance() for _ in range(1)])
toilet = Assets(description="toilet", size=[0.70, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
clock = Assets(description="clock", size=[0.05, 0.30, 0.30], placements=[AssetInstance() for _ in range(1)])
art_print = Assets(description="art print", size=[0.02, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])

bathroom_mat[0].instance_id = 'bathroom_mat_0'
mirror[0].instance_id = 'mirror_0'
poster_print[0].instance_id = 'poster_print_0'
bathroom_vanity[0].instance_id = 'bathroom_vanity_0'
toilet[0].instance_id = 'toilet_0'
clock[0].instance_id = 'clock_0'
art_print[0].instance_id = 'art_print_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

bathroom_mat[0].position = [2.0758222825658055, 0.421564833277289, 0.005]
bathroom_mat[0].rotation = [0, 0, 0]
mirror[0].position = [1.4285667101965198, 1.0251386577916983, 0.45]
mirror[0].rotation = [0, 0, 0]
poster_print[0].position = [2.6047221608043616, 1.1175294101006448, 0.3]
poster_print[0].rotation = [0, 0, 0]
bathroom_vanity[0].position = [2.2514851816446226, 1.4910592915110805, 0.425]
bathroom_vanity[0].rotation = [0, 0, 0]
toilet[0].position = [1.707171187904973, 1.2562974699356815, 0.39]
toilet[0].rotation = [0, 0, 0]
clock[0].position = [0.40239926655664604, 1.3780893102596867, 0.15]
clock[0].rotation = [0, 0, 0]
art_print[0].position = [0.19806780654415573, 2.0336730821816897, 0.35]
art_print[0].rotation = [0, 0, 0]
bathroom_mat[0].position = [2.0758222825658055, 0.421564833277289, 0.005]
bathroom_mat[0].rotation = [0, 0, 0]
mirror[0].position = [1.4285667101965198, 1.0251386577916983, 0.45]
mirror[0].rotation = [0, 0, 0]
poster_print[0].position = [2.6047221608043616, 1.1175294101006448, 0.3]
poster_print[0].rotation = [0, 0, 0]
bathroom_vanity[0].position = [2.2514851816446226, 1.4910592915110805, 0.425]
bathroom_vanity[0].rotation = [0, 0, 0]
toilet[0].position = [1.707171187904973, 1.2562974699356815, 0.39]
toilet[0].rotation = [0, 0, 0]
clock[0].position = [0.40239926655664604, 1.3780893102596867, 0.15]
clock[0].rotation = [0, 0, 0]
art_print[0].position = [0.19806780654415573, 2.0336730821816897, 0.35]
art_print[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the vanity and toilet on opposing side walls, leaving a clear central aisle.
# The toilet faces the vanity as required.
bathroom_vanity[0].position = [0.275, 1.70, 0.425]
bathroom_vanity[0].rotation = [0, 0, radians(0)]

toilet[0].position = [2.65, 1.70, 0.39]
toilet[0].rotation = [0, 0, radians(180)]

# Place the mat directly in front of the vanity with a small clearance.
bathroom_mat[0].position = [0.90, 1.70, 0.005]
bathroom_mat[0].rotation = [0, 0, radians(0)]

# Mount the mirror above the vanity. Its bottom is above the vanity countertop.
mirror[0].position = [0.02, 1.70, 1.45]
mirror[0].rotation = [0, 0, radians(0)]

# Distribute the remaining wall decorations across the top and bottom walls.
poster_print[0].position = [1.15, 2.39, 1.55]
poster_print[0].rotation = [0, 0, radians(-90)]

art_print[0].position = [2.25, 2.39, 1.45]
art_print[0].rotation = [0, 0, radians(-90)]

clock[0].position = [1.60, 0.025, 1.60]
clock[0].rotation = [0, 0, radians(90)]

# Fixed reference points preserve the intended positions along the walls and
# prevent the solver from sliding objects into one another.
vanity_anchor = AssetInstance(position=[0.275, 1.70, 0.425])
toilet_anchor = AssetInstance(position=[2.65, 1.70, 0.39])
mat_anchor = AssetInstance(position=[0.90, 1.70, 0.005])
mirror_anchor = AssetInstance(position=[0.02, 1.70, 1.45])
poster_anchor = AssetInstance(position=[1.15, 2.39, 1.55])
art_anchor = AssetInstance(position=[2.25, 2.39, 1.45])
clock_anchor = AssetInstance(position=[1.60, 0.025, 1.60])
room_center = AssetInstance(position=[1.50, 1.20, 1.45])

# Primary position constraints.
solver.distance_constraint(
    bathroom_vanity[0], vanity_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    toilet[0], toilet_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    bathroom_mat[0], mat_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    mirror[0], mirror_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    poster_print[0], poster_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    art_print[0], art_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    clock[0], clock_anchor, 0, 0, weight=10
)

# Semantic wall-contact constraints for the fixtures and wall decorations.
solver.against_wall(bathroom_vanity[0], walls[3])
solver.against_wall(toilet[0], walls[1])
solver.against_wall(mirror[0], walls[3])
solver.against_wall(poster_print[0], walls[2])
solver.against_wall(art_print[0], walls[2])
solver.against_wall(clock[0], walls[0])

# Keep the floor mat functionally close to, but clear of, the vanity.
solver.distance_constraint(
    bathroom_mat[0], bathroom_vanity[0], 0.60, 0.70, weight=5
)

# Orientation constraints. The toilet's required relationship is specified
# first so it takes priority over any later adjustment.
solver.point_towards(toilet[0], bathroom_vanity[0])
solver.point_towards(bathroom_vanity[0], toilet[0])
solver.align_with(bathroom_mat[0], bathroom_vanity[0])
solver.align_with(mirror[0], bathroom_vanity[0])
solver.point_towards(poster_print[0], room_center)
solver.point_towards(art_print[0], room_center)
solver.point_towards(clock[0], room_center)

solver.constraints = []
clock[0].position = [1.600000023841858, 0.016124853864312172, 0.15000000596046448]
clock[0].rotation = [0, 0, 1.573337248311928]
clock[0].optimize = 2
mirror[0].position = [0.011367769911885262, 1.7000000476837158, 0.44999998807907104]
mirror[0].rotation = [0, 0, 0.002540916928559797]
mirror[0].optimize = 2
poster_print[0].position = [1.149999976158142, 2.3974101543426514, 0.30000001192092896]
poster_print[0].rotation = [0, 0, -1.5682554052778654]
poster_print[0].optimize = 2
bathroom_mat[0].position = [0.8999999761581421, 1.7000000476837158, 0.004999999888241291]
bathroom_mat[0].rotation = [0, 0, 0.02278960013808119]
bathroom_mat[0].optimize = 2
art_print[0].position = [2.25, 2.3976950645446777, 0.3499999940395355]
art_print[0].rotation = [0, 0, -1.5682554064999652]
art_print[0].optimize = 2
bathroom_vanity[0].position = [0.2774783968925476, 1.7000000476837158, 0.42500001192092896]
bathroom_vanity[0].rotation = [0, 0, 0.014983913306916511]
bathroom_vanity[0].optimize = 2
toilet[0].position = [2.6489317417144775, 1.7000000476837158, 0.38999998569488525]
toilet[0].rotation = [0, 0, -3.135941128728704]
toilet[0].optimize = 2

