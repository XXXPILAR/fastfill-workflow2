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
    Wall(corner1=[4.20, 8.21, 0.00], corner2=[4.20, 5.34, 0.00]),
    Wall(corner1=[4.20, 5.34, 0.00], corner2=[0.00, 5.34, 0.00]),
    Wall(corner1=[0.00, 5.34, 0.00], corner2=[0.00, 4.16, 0.00]),
    Wall(corner1=[0.00, 4.16, 0.00], corner2=[4.39, 4.16, 0.00]),
    Wall(corner1=[4.39, 4.16, 0.00], corner2=[4.39, 0.00, 0.00]),
    Wall(corner1=[4.39, 0.00, 0.00], corner2=[8.20, 0.00, 0.00]),
    Wall(corner1=[8.20, 0.00, 0.00], corner2=[8.20, 5.34, 0.00]),
    Wall(corner1=[8.20, 5.34, 0.00], corner2=[6.90, 5.34, 0.00]),
    Wall(corner1=[6.90, 5.34, 0.00], corner2=[6.90, 8.21, 0.00]),
    Wall(corner1=[6.90, 8.21, 0.00], corner2=[4.20, 8.21, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
cabinet = Assets(description="cabinet", size=[0.45, 2.00, 0.75], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="table", size=[0.65, 1.20, 0.42], placements=[AssetInstance() for _ in range(1)])
sofa = Assets(description="sofa", size=[0.95, 2.40, 0.85], placements=[AssetInstance() for _ in range(1)])

cabinet[0].instance_id = 'cabinet_0'
table[0].instance_id = 'table_0'
sofa[0].instance_id = 'sofa_0'
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

cabinet[0].position = [2.582493145462747, 4.471069996999572, 0.375]
cabinet[0].rotation = [0, 0, 0]
table[0].position = [7.190242549499327, 1.6189209643489242, 0.21]
table[0].rotation = [0, 0, 0]
sofa[0].position = [0.4106423279241383, 4.92341874726459, 0.425]
sofa[0].rotation = [0, 0, 0]
cabinet[0].position = [2.582493145462747, 4.471069996999572, 0.375]
cabinet[0].rotation = [0, 0, 0]
table[0].position = [7.190242549499327, 1.6189209643489242, 0.21]
table[0].rotation = [0, 0, 0]
sofa[0].position = [0.4106423279241383, 4.92341874726459, 0.425]
sofa[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the lower main room for the seating group. Keep the bottom entrance
# approach (y < 1.30), the upper circulation area, and all other doors clear.
# Asset sizes are measured in their local axes; these rotations leave their
# long dimensions parallel to the side walls.
sofa[0].position = [4.865, 2.50, 0.425]
sofa[0].rotation = [0, 0, 0]

cabinet[0].position = [7.975, 2.50, 0.375]
cabinet[0].rotation = [0, 0, radians(180)]

table[0].position = [6.15, 2.50, 0.21]
table[0].rotation = [0, 0, 0]

# Prioritize these clear, non-overlapping locations. Fixed points are only
# constraint references, not additional furnishings.
solver.distance_constraint(
    sofa[0], AssetInstance(position=[4.865, 2.50, 0.425]),
    0, 0, weight=10
)
solver.distance_constraint(
    cabinet[0], AssetInstance(position=[7.975, 2.50, 0.375]),
    0, 0, weight=10
)
solver.distance_constraint(
    table[0], AssetInstance(position=[6.15, 2.50, 0.21]),
    0, 0, weight=10
)

# Put the seating and cabinet against opposite solid wall sections.
# Their footprints stop below the nearby door approaches.
solver.against_wall(sofa[0], walls[4])
solver.against_wall(cabinet[0], walls[6])

# The sofa faces the cabinet; the cabinet faces back toward the seating.
# Align the coffee table with the sofa.
solver.point_towards(sofa[0], cabinet[0])
solver.point_towards(cabinet[0], sofa[0])
solver.align_with(table[0], sofa[0])

# Maintain useful separation, including approximately 0.49 m between
# the sofa's front edge and the coffee table. Distances are between 3D centers.
solver.distance_constraint(table[0], sofa[0], 1.25, 1.40, weight=10)
solver.distance_constraint(table[0], cabinet[0], 1.80, 1.90)
solver.distance_constraint(sofa[0], cabinet[0], 3.05, 3.20)

# All three assets are floor-standing; no on_top_of constraint is needed.

solver.constraints = []
sofa[0].position = [4.860332012176514, 2.5, 0.42500001192092896]
sofa[0].rotation = [0, 0, -3.796233747008186e-08]
sofa[0].optimize = 2
cabinet[0].position = [7.978535175323486, 2.5, 0.375]
cabinet[0].rotation = [0, 0, -3.1415924676108857]
cabinet[0].optimize = 2
table[0].position = [6.150000095367432, 2.5, 0.20999999344348907]
table[0].rotation = [0, 0, 2.08479126331302e-07]
table[0].optimize = 2

