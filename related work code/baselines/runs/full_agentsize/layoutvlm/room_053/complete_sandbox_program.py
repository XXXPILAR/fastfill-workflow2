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
    Wall(corner1=[0.00, 2.36, 0.00], corner2=[0.33, 2.36, 0.00]),
    Wall(corner1=[0.33, 2.36, 0.00], corner2=[0.54, 2.36, 0.00]),
    Wall(corner1=[0.54, 2.36, 0.00], corner2=[0.54, 1.69, 0.00]),
    Wall(corner1=[0.54, 1.69, 0.00], corner2=[0.54, 0.00, 0.00]),
    Wall(corner1=[0.54, 0.00, 0.00], corner2=[3.41, 0.00, 0.00]),
    Wall(corner1=[3.41, 0.00, 0.00], corner2=[4.11, 0.00, 0.00]),
    Wall(corner1=[4.11, 0.00, 0.00], corner2=[4.11, 4.29, 0.00]),
    Wall(corner1=[4.11, 4.29, 0.00], corner2=[1.73, 4.29, 0.00]),
    Wall(corner1=[1.73, 4.29, 0.00], corner2=[1.61, 4.29, 0.00]),
    Wall(corner1=[1.61, 4.29, 0.00], corner2=[1.61, 5.56, 0.00]),
    Wall(corner1=[1.61, 5.56, 0.00], corner2=[1.51, 5.56, 0.00]),
    Wall(corner1=[1.51, 5.56, 0.00], corner2=[0.66, 5.56, 0.00]),
    Wall(corner1=[0.66, 5.56, 0.00], corner2=[0.00, 5.56, 0.00]),
    Wall(corner1=[0.00, 5.56, 0.00], corner2=[0.00, 2.36, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bed = Assets(description="bed", size=[2.00, 1.60, 0.55], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[3.00, 2.00, 0.02], placements=[AssetInstance() for _ in range(1)])
dresser = Assets(description="dresser", size=[0.50, 1.40, 0.85], placements=[AssetInstance() for _ in range(1)])
stool = Assets(description="stool", size=[0.45, 0.45, 0.45], placements=[AssetInstance() for _ in range(1)])
mirror = Assets(description="mirror", size=[0.04, 1.00, 0.80], placements=[AssetInstance() for _ in range(1)])

bed[0].instance_id = 'bed_0'
carpet[0].instance_id = 'carpet_0'
dresser[0].instance_id = 'dresser_0'
stool[0].instance_id = 'stool_0'
mirror[0].instance_id = 'mirror_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'
walls[8].instance_id = 'walls_8'
walls[9].instance_id = 'walls_9'
walls[10].instance_id = 'walls_10'
walls[11].instance_id = 'walls_11'
walls[12].instance_id = 'walls_12'
walls[13].instance_id = 'walls_13'

bed[0].position = [1.5903411787579094, 3.2312949612426554, 0.275]
bed[0].rotation = [0, 0, 0]
carpet[0].position = [0.22968667087761613, 4.220653912316699, 0.01]
carpet[0].rotation = [0, 0, 0]
dresser[0].position = [3.7379742520918025, 3.9327599967681697, 0.425]
dresser[0].rotation = [0, 0, 0]
stool[0].position = [0.7886174586678177, 0.9531092516089477, 0.225]
stool[0].rotation = [0, 0, 0]
mirror[0].position = [0.5577101892399539, 3.5011096604016387, 0.4]
mirror[0].rotation = [0, 0, 0]
bed[0].position = [1.5903411787579094, 3.2312949612426554, 0.275]
bed[0].rotation = [0, 0, 0]
carpet[0].position = [0.22968667087761613, 4.220653912316699, 0.01]
carpet[0].rotation = [0, 0, 0]
dresser[0].position = [3.7379742520918025, 3.9327599967681697, 0.425]
dresser[0].rotation = [0, 0, 0]
stool[0].position = [0.7886174586678177, 0.9531092516089477, 0.225]
stool[0].rotation = [0, 0, 0]
mirror[0].position = [0.5577101892399539, 3.5011096604016387, 0.4]
mirror[0].rotation = [0, 0, 0]

solver.constraints = []

from math import radians

# The bed is placed against the upper wall, with its long axis running
# perpendicular to that wall.  Its center is kept clear of the doorway.
bed[0].position = [2.80, 3.29, 0.275]
bed[0].rotation = [0, 0, radians(-90)]

# The carpet is rotated so that it occupies the open central floor area,
# avoiding both the fixed wardrobe and the dresser.
carpet[0].position = [1.70, 1.80, 0.01]
carpet[0].rotation = [0, 0, radians(90)]

# The dresser is placed along the right-hand wall below the bed, leaving
# the window and the door unobstructed.
dresser[0].position = [3.41, 1.10, 0.425]
dresser[0].rotation = [0, 0, radians(90)]

# The stool is placed on the bed surface near its center.  This satisfies
# the required proximity to the bed without occupying additional floor
# space or blocking circulation.
stool[0].position = [2.80, 3.10, 0.775]
stool[0].rotation = [0, 0, radians(0)]

# The mirror is mounted against the right wall in the open area between
# the dresser and the bed.
mirror[0].position = [4.07, 1.90, 0.40]
mirror[0].rotation = [0, 0, radians(0)]

# Fixed reference points make the intended initial positions explicit and
# provide strong positional anchors during constraint solving.
bed_target = AssetInstance(position=[2.80, 3.29, 0.275])
carpet_target = AssetInstance(position=[1.70, 1.80, 0.01])
dresser_target = AssetInstance(position=[3.41, 1.10, 0.425])
stool_target = AssetInstance(position=[2.80, 3.10, 0.775])
mirror_target = AssetInstance(position=[4.07, 1.90, 0.40])

# Bed: first anchor it to the upper wall and orient it toward the room.
solver.against_wall(bed[0], walls[7])
solver.distance_constraint(bed[0], bed_target, 0, 0, weight=10)
solver.point_towards(
    bed[0],
    AssetInstance(position=[2.80, 2.00, 0.275]),
    angle=0,
)

# Carpet: anchor its floor position and preserve its orientation.
solver.distance_constraint(carpet[0], carpet_target, 0, 0, weight=10)
solver.align_with(carpet[0], AssetInstance(position=[0, 0, 0]), angle=90)

# Dresser: constrain it against the right wall and keep it below the bed.
solver.against_wall(dresser[0], walls[6])
solver.distance_constraint(dresser[0], dresser_target, 0, 0, weight=10)
solver.point_towards(
    dresser[0],
    AssetInstance(position=[3.00, 1.10, 0.425]),
    angle=180,
)

# Stool: keep it on top of the bed and within 0.20 m of the bed center.
# The exact target keeps it near the intended location if the solver has
# to make small physical adjustments.
solver.on_top_of(stool[0], bed[0])
solver.distance_constraint(stool[0], bed[0], 0, 0.20, weight=10)
solver.distance_constraint(stool[0], stool_target, 0, 0, weight=5)
solver.point_towards(stool[0], bed[0], angle=0)

# Mirror: anchor it to the right wall and orient its front toward the room.
solver.against_wall(mirror[0], walls[6])
solver.distance_constraint(mirror[0], mirror_target, 0, 0, weight=10)
solver.point_towards(
    mirror[0],
    AssetInstance(position=[3.00, 1.90, 0.40]),
    angle=0,
)

solver.constraints = []
dresser[0].position = [3.8517680168151855, 1.100000023841858, 0.42500001192092896]
dresser[0].rotation = [0, 0, -3.120363373116642]
dresser[0].optimize = 2
mirror[0].position = [3.6679747104644775, 1.899999976158142, 0.4000000059604645]
mirror[0].rotation = [0, 0, 2.0986229594519434]
mirror[0].optimize = 2
bed[0].position = [2.0644803047180176, 2.7222230434417725, 0.2750000059604645]
bed[0].rotation = [0, 0, 0.4277327168543881]
bed[0].optimize = 2
stool[0].position = [2.841935873031616, 3.4275760650634766, 0.7749999761581421]
stool[0].rotation = [0, 0, -0.1837329443467314]
stool[0].optimize = 2
carpet[0].position = [1.7000000476837158, 1.7999999523162842, 0.009999999776482582]
carpet[0].rotation = [0, 0, 1.5802211042556205]
carpet[0].optimize = 2

