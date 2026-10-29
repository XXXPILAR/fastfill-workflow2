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
mirror = Assets(description="mirror", size=[0.03, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
poster_print = Assets(description="poster print", size=[0.02, 0.30, 0.40], placements=[AssetInstance() for _ in range(1)])
bathroom_vanity = Assets(description="bathroom vanity", size=[0.50, 1.00, 0.85], placements=[AssetInstance() for _ in range(1)])
toilet = Assets(description="toilet", size=[0.70, 0.38, 0.80], placements=[AssetInstance() for _ in range(1)])
clock = Assets(description="clock", size=[0.04, 0.25, 0.25], placements=[AssetInstance() for _ in range(1)])
art_print = Assets(description="art print", size=[0.02, 0.40, 0.50], placements=[AssetInstance() for _ in range(1)])

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

bathroom_mat[0].position = [0.7349848030532232, 0.6837003989751325, 0.0075]
bathroom_mat[0].rotation = [0, 0, 0]
mirror[0].position = [2.238845306198324, 0.8333278076638289, 0.45]
mirror[0].rotation = [0, 0, 0]
poster_print[0].position = [2.6896519848573637, 2.3089697137715923, 0.2]
poster_print[0].rotation = [0, 0, 0]
bathroom_vanity[0].position = [0.5589074126584929, 0.9038031315031225, 0.425]
bathroom_vanity[0].rotation = [0, 0, 0]
toilet[0].position = [0.05538711037560008, 1.174016610250854, 0.4]
toilet[0].rotation = [0, 0, 0]
clock[0].position = [0.6944719451160863, 1.3842083665068279, 0.125]
clock[0].rotation = [0, 0, 0]
art_print[0].position = [0.8821834404981299, 0.2831481419371333, 0.25]
art_print[0].rotation = [0, 0, 0]
bathroom_mat[0].position = [0.7349848030532232, 0.6837003989751325, 0.0075]
bathroom_mat[0].rotation = [0, 0, 0]
mirror[0].position = [2.238845306198324, 0.8333278076638289, 0.45]
mirror[0].rotation = [0, 0, 0]
poster_print[0].position = [2.6896519848573637, 2.3089697137715923, 0.2]
poster_print[0].rotation = [0, 0, 0]
bathroom_vanity[0].position = [0.5589074126584929, 0.9038031315031225, 0.425]
bathroom_vanity[0].rotation = [0, 0, 0]
toilet[0].position = [0.05538711037560008, 1.174016610250854, 0.4]
toilet[0].rotation = [0, 0, 0]
clock[0].position = [0.6944719451160863, 1.3842083665068279, 0.125]
clock[0].rotation = [0, 0, 0]
art_print[0].position = [0.8821834404981299, 0.2831481419371333, 0.25]
art_print[0].rotation = [0, 0, 0]

solver.constraints = []

# The supplied boundary is x=[0, 3], y=[0, 2.4].
# Put the vanity and toilet on opposite walls, leaving a generous clear aisle.
bathroom_vanity[0].position = [0.25, 1.30, 0.425]
bathroom_vanity[0].rotation = [0, 0, 0]

toilet[0].position = [2.65, 1.30, 0.40]
toilet[0].rotation = [0, 0, radians(180)]

# The mat is in front of the vanity, with a 0.20 m gap from its footprint.
bathroom_mat[0].position = [0.95, 1.30, 0.005]
bathroom_mat[0].rotation = [0, 0, 0]

# Wall-mounted items are elevated explicitly, not placed on the floor or
# supported by the vanity. The mirror bottom is 0.20 m above the countertop.
mirror[0].position = [0.015, 1.30, 1.50]
mirror[0].rotation = [0, 0, 0]

# The clock sits above the mirror, with no overlap between their bounds.
clock[0].position = [0.02, 1.30, 2.20]
clock[0].rotation = [0, 0, 0]

# Two separate pictures on the north wall face into the room (-y).
poster_print[0].position = [1.00, 2.39, 1.55]
poster_print[0].rotation = [0, 0, radians(270)]

art_print[0].position = [2.00, 2.39, 1.55]
art_print[0].rotation = [0, 0, radians(270)]

# Prioritize the required facing relationship.
solver.point_towards(toilet[0], bathroom_vanity[0])

# Fixed-center constraints preserve the chosen mounting heights and lateral
# spacing. In particular, wall decorations must not drop to floor level.
# These anchors are reference points only, not additional scene assets.
for placed_instance in (
    bathroom_vanity[0],
    toilet[0],
    bathroom_mat[0],
    mirror[0],
    clock[0],
    poster_print[0],
    art_print[0],
):
    solver.distance_constraint(
        placed_instance,
        AssetInstance(position=list(placed_instance.position)),
        0,
        0,
        weight=10,
    )

# Keep the backs of the fixtures and wall-mounted decorations against
# their respective walls. Their initial rotated bounds are fully inside.
solver.against_wall(bathroom_vanity[0], walls[3])
solver.against_wall(toilet[0], walls[1])
solver.against_wall(mirror[0], walls[3])
solver.against_wall(clock[0], walls[3])
solver.against_wall(poster_print[0], walls[2])
solver.against_wall(art_print[0], walls[2])

# Explicit orientation constraints for every remaining asset.
solver.align_with(
    bathroom_vanity[0],
    AssetInstance(position=[1.50, 1.30, 0.425], rotation=[0, 0, 0]),
)
solver.align_with(bathroom_mat[0], bathroom_vanity[0])
solver.align_with(mirror[0], bathroom_vanity[0])
solver.align_with(clock[0], bathroom_vanity[0])
solver.align_with(poster_print[0], bathroom_vanity[0], angle=270)
solver.align_with(art_print[0], poster_print[0])

solver.constraints = []
art_print[0].position = [2.0, 2.3974101543426514, 0.25]
art_print[0].rotation = [0, 0, -1.5682554052778654]
art_print[0].optimize = 2
mirror[0].position = [0.006743620149791241, 1.2999999523162842, 0.44999998807907104]
mirror[0].rotation = [0, 0, 0.002540916928559797]
mirror[0].optimize = 2
poster_print[0].position = [1.0, 2.398266553878784, 0.20000000298023224]
poster_print[0].rotation = [0, 0, -1.565144802188882]
poster_print[0].optimize = 2
bathroom_vanity[0].position = [0.2540355324745178, 1.2999999523162842, 0.42500001192092896]
bathroom_vanity[0].rotation = [0, 0, 0.01809490963878927]
bathroom_vanity[0].optimize = 2
toilet[0].position = [2.6495182514190674, 1.2999999523162842, 0.4000000059604645]
toilet[0].rotation = [0, 0, -3.1390517329949352]
toilet[0].optimize = 2
bathroom_mat[0].position = [0.949999988079071, 1.2999999523162842, 0.004999999888241291]
bathroom_mat[0].rotation = [0, 0, 0.019617563686327]
bathroom_mat[0].optimize = 2
clock[0].position = [0.01136790681630373, 1.2999999523162842, 0.125]
clock[0].rotation = [0, 0, 0.002540922439204702]
clock[0].optimize = 2

