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
    Wall(corner1=[5.68, 5.25, 0.00], corner2=[5.40, 5.25, 0.00]),
    Wall(corner1=[5.40, 5.25, 0.00], corner2=[5.40, 8.90, 0.00]),
    Wall(corner1=[5.40, 8.90, 0.00], corner2=[2.97, 8.90, 0.00]),
    Wall(corner1=[2.97, 8.90, 0.00], corner2=[2.97, 7.17, 0.00]),
    Wall(corner1=[2.97, 7.17, 0.00], corner2=[0.00, 7.17, 0.00]),
    Wall(corner1=[0.00, 7.17, 0.00], corner2=[0.00, 5.95, 0.00]),
    Wall(corner1=[0.00, 5.95, 0.00], corner2=[1.46, 5.95, 0.00]),
    Wall(corner1=[1.46, 5.95, 0.00], corner2=[1.46, 0.00, 0.00]),
    Wall(corner1=[1.46, 0.00, 0.00], corner2=[5.68, 0.00, 0.00]),
    Wall(corner1=[5.68, 0.00, 0.00], corner2=[5.68, 5.25, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
table = Assets(description="table", size=[0.65, 1.20, 0.42], placements=[AssetInstance() for _ in range(1)])
sofa = Assets(description="sofa", size=[0.95, 2.40, 0.85], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.40, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.45, 1.80, 0.55], placements=[AssetInstance() for _ in range(1)])

table[0].instance_id = 'table_0'
sofa[0].instance_id = 'sofa_0'
cabinet_A[0].instance_id = 'cabinet_A_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
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

table[0].position = [4.7311085106959405, 3.2806989450436976, 0.21]
table[0].rotation = [0, 0, 0]
sofa[0].position = [3.3229290020604187, 1.9773183703492654, 0.425]
sofa[0].rotation = [0, 0, 0]
cabinet_A[0].position = [5.003284215325106, 1.7908907791333832, 0.9]
cabinet_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [2.767158901393607, 0.834995108204101, 0.275]
cabinet_B[0].rotation = [0, 0, 0]
table[0].position = [4.7311085106959405, 3.2806989450436976, 0.21]
table[0].rotation = [0, 0, 0]
sofa[0].position = [3.3229290020604187, 1.9773183703492654, 0.425]
sofa[0].rotation = [0, 0, 0]
cabinet_A[0].position = [5.003284215325106, 1.7908907791333832, 0.9]
cabinet_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [2.767158901393607, 0.834995108204101, 0.275]
cabinet_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the lower rectangular part of the room for the sitting area.
# All furniture remains below y=4.4, leaving the northern doors and
# their connecting circulation area clear. Keep the south window unobstructed.

# Sofa: back against the west wall, facing the low cabinet across the room.
sofa[0].position = [1.935, 3.20, 0.425]
sofa[0].rotation = [0, 0, 0]

# Low cabinet / media unit: back against the east wall, facing the sofa.
cabinet_B[0].position = [5.455, 3.20, 0.275]
cabinet_B[0].rotation = [0, 0, radians(180)]

# Coffee table: approximately 0.42 m clear of the sofa's front edge.
# Its long dimension runs parallel to the sofa.
table[0].position = [3.15, 3.20, 0.21]
table[0].rotation = [0, 0, 0]

# Tall cabinet: against the west wall, south of the sofa.
# Its footprint ends at y=1.50; the sofa starts at y=2.00.
cabinet_A[0].position = [1.66, 0.90, 0.90]
cabinet_A[0].rotation = [0, 0, 0]

# Prioritize wall contact and the required sofa-to-cabinet facing relationship.
solver.against_wall(cabinet_A[0], walls[7])
solver.against_wall(sofa[0], walls[7])
solver.against_wall(cabinet_B[0], walls[9])
solver.point_towards(sofa[0], cabinet_B[0])
solver.point_towards(cabinet_B[0], sofa[0])

# Fixed reference points retain the intended furniture zones during adjustment.
# Their heights match the respective bounding-box centers.
solver.distance_constraint(
    sofa[0],
    AssetInstance(position=[1.935, 3.20, 0.425]),
    0, 0.05, weight=10
)
solver.distance_constraint(
    cabinet_B[0],
    AssetInstance(position=[5.455, 3.20, 0.275]),
    0, 0.05, weight=10
)
solver.distance_constraint(
    cabinet_A[0],
    AssetInstance(position=[1.66, 0.90, 0.90]),
    0, 0.05, weight=10
)
solver.distance_constraint(
    table[0],
    AssetInstance(position=[3.15, 3.20, 0.21]),
    0, 0.05, weight=10
)

# Orient the tall cabinet into the room and the table parallel to the sofa.
solver.point_towards(
    cabinet_A[0], AssetInstance(position=[4.0, 0.90, 0.90])
)
solver.align_with(table[0], sofa[0], angle=0)

# Center-distance ranges account for the different asset heights.
# Together with the zone constraints, these preserve the seating relationship
# and prevent the table from drifting into the sofa or media cabinet.
solver.distance_constraint(table[0], sofa[0], 1.20, 1.30)
solver.distance_constraint(table[0], cabinet_B[0], 2.25, 2.36)
solver.distance_constraint(sofa[0], cabinet_B[0], 3.45, 3.60)

# These are all floor-standing assets, including the low coffee table;
# no on_top_of constraint is appropriate.

solver.constraints = []
sofa[0].position = [1.9367512464523315, 3.200000047683716, 0.42500001192092896]
sofa[0].rotation = [0, 0, -6.940505921554104e-05]
sofa[0].optimize = 2
cabinet_A[0].position = [1.6618647575378418, 0.8999999761581421, 0.8999999761581421]
cabinet_A[0].rotation = [0, 0, -8.595137116607035e-05]
cabinet_A[0].optimize = 2
cabinet_B[0].position = [5.4370808601379395, 3.200000047683716, 0.2750000059604645]
cabinet_B[0].rotation = [0, 0, 3.1415595549293194]
cabinet_B[0].optimize = 2
table[0].position = [3.153900623321533, 3.200000047683716, 0.20999999344348907]
table[0].rotation = [0, 0, -0.0004576472781458095]
table[0].optimize = 2

