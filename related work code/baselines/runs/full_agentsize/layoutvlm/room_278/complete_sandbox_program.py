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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.30, 0.00, 0.00]),
    Wall(corner1=[2.30, 0.00, 0.00], corner2=[2.30, 2.20, 0.00]),
    Wall(corner1=[2.30, 2.20, 0.00], corner2=[3.01, 2.20, 0.00]),
    Wall(corner1=[3.01, 2.20, 0.00], corner2=[3.01, 7.01, 0.00]),
    Wall(corner1=[3.01, 7.01, 0.00], corner2=[0.00, 7.01, 0.00]),
    Wall(corner1=[0.00, 7.01, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
cabinet_A = Assets(description="cabinet", size=[0.42, 0.90, 0.85], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.40, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
sofa = Assets(description="sofa", size=[0.90, 2.10, 0.85], placements=[AssetInstance() for _ in range(1)])
cabinet_C = Assets(description="cabinet", size=[0.42, 0.90, 0.85], placements=[AssetInstance() for _ in range(1)])
chair = Assets(description="chair", size=[0.80, 0.75, 0.85], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="table", size=[0.60, 1.10, 0.45], placements=[AssetInstance() for _ in range(1)])

cabinet_A[0].instance_id = 'cabinet_A_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
sofa[0].instance_id = 'sofa_0'
cabinet_C[0].instance_id = 'cabinet_C_0'
chair[0].instance_id = 'chair_0'
table[0].instance_id = 'table_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

cabinet_A[0].position = [0.28210085351635034, 0.14898684533102793, 0.425]
cabinet_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [2.552786659092813, 4.312089801506928, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
sofa[0].position = [2.731520636889252, 4.688436510888331, 0.425]
sofa[0].rotation = [0, 0, 0]
cabinet_C[0].position = [2.481320373856521, 4.80268239462355, 0.425]
cabinet_C[0].rotation = [0, 0, 0]
chair[0].position = [1.4973240749361258, 0.5011326046686865, 0.425]
chair[0].rotation = [0, 0, 0]
table[0].position = [1.239012942312994, 4.289613423783059, 0.225]
table[0].rotation = [0, 0, 0]
cabinet_A[0].position = [0.28210085351635034, 0.14898684533102793, 0.425]
cabinet_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [2.552786659092813, 4.312089801506928, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
sofa[0].position = [2.731520636889252, 4.688436510888331, 0.425]
sofa[0].rotation = [0, 0, 0]
cabinet_C[0].position = [2.481320373856521, 4.80268239462355, 0.425]
cabinet_C[0].rotation = [0, 0, 0]
chair[0].position = [1.4973240749361258, 0.5011326046686865, 0.425]
chair[0].rotation = [0, 0, 0]
table[0].position = [1.239012942312994, 4.289613423783059, 0.225]
table[0].rotation = [0, 0, 0]

solver.constraints = []

# Keep all furniture in the upper part of the room so that the doors at the
# bottom, lower-right, and left side retain clear approach paths.
# cabinet_A and cabinet_C correspond to the two cabinets that must have the
# table spatially between them.

cabinet_A[0].position = [0.21, 4.475, 0.425]
cabinet_A[0].rotation = [0, 0, radians(0)]

table[0].position = [0.30, 5.50, 0.225]
table[0].rotation = [0, 0, radians(0)]

cabinet_C[0].position = [0.21, 6.525, 0.425]
cabinet_C[0].rotation = [0, 0, radians(0)]

# Place the larger cabinet on the unobstructed upper-right wall, below the sofa.
cabinet_B[0].position = [2.81, 3.48, 0.45]
cabinet_B[0].rotation = [0, 0, radians(180)]

# The sofa occupies the upper-right wall and faces into the seating area.
sofa[0].position = [2.56, 5.60, 0.425]
sofa[0].rotation = [0, 0, radians(180)]

# The chair remains away from the wall and faces the sofa.
chair[0].position = [1.35, 4.30, 0.425]
chair[0].rotation = [0, 0, radians(47)]

# Fixed targets preserve the intended positions while the additional wall and
# relational constraints maintain the layout semantics during adjustment.
cabinet_A_target = AssetInstance(position=[0.21, 4.475, 0.425])
table_target = AssetInstance(position=[0.30, 5.50, 0.225])
cabinet_C_target = AssetInstance(position=[0.21, 6.525, 0.425])
cabinet_B_target = AssetInstance(position=[2.81, 3.48, 0.45])
sofa_target = AssetInstance(position=[2.56, 5.60, 0.425])
chair_target = AssetInstance(position=[1.35, 4.30, 0.425])

# Important position constraints are specified first.
solver.distance_constraint(
    cabinet_A[0], cabinet_A_target, 0, 0, weight=10
)
solver.distance_constraint(
    table[0], table_target, 0, 0, weight=10
)
solver.distance_constraint(
    cabinet_C[0], cabinet_C_target, 0, 0, weight=10
)
solver.distance_constraint(
    cabinet_B[0], cabinet_B_target, 0, 0, weight=10
)
solver.distance_constraint(
    sofa[0], sofa_target, 0, 0, weight=10
)
solver.distance_constraint(
    chair[0], chair_target, 0, 0, weight=10
)

# Keep the three-item sequence against the left wall. Their center spacing
# leaves a small gap between adjacent bounding boxes, with the table centered
# between cabinet_A and cabinet_C.
solver.against_wall(cabinet_A[0], walls[5])
solver.against_wall(table[0], walls[5])
solver.against_wall(cabinet_C[0], walls[5])
solver.distance_constraint(
    table[0], cabinet_A[0], 1.025, 1.025, weight=10
)
solver.distance_constraint(
    table[0], cabinet_C[0], 1.025, 1.025, weight=10
)

# Keep the larger cabinet and sofa against the unobstructed upper-right wall.
solver.against_wall(cabinet_B[0], walls[3])
solver.against_wall(sofa[0], walls[3])

# Orientation constraints: wall furniture faces inward, while the chair faces
# the sofa. Fixed interior points make the desired facing direction explicit.
left_interior_target = AssetInstance(position=[1.50, 5.50, 0.45])
right_interior_target = AssetInstance(position=[1.50, 5.50, 0.45])

solver.point_towards(cabinet_A[0], left_interior_target)
solver.point_towards(table[0], left_interior_target)
solver.point_towards(cabinet_C[0], left_interior_target)
solver.point_towards(cabinet_B[0], right_interior_target)
solver.point_towards(sofa[0], right_interior_target)
solver.point_towards(chair[0], sofa[0])

solver.constraints = []
cabinet_A[0].position = [0.21011003851890564, 4.477478504180908, 0.42500001192092896]
cabinet_A[0].rotation = [0, 0, -6.350822657868648e-05]
cabinet_A[0].optimize = 2
sofa[0].position = [2.5409438610076904, 5.599999904632568, 0.42500001192092896]
sofa[0].rotation = [0, 0, 3.141543147286875]
sofa[0].optimize = 2
cabinet_B[0].position = [2.807412624359131, 3.4800000190734863, 0.44999998807907104]
cabinet_B[0].rotation = [0, 0, 3.1415456836421023]
cabinet_B[0].optimize = 2
table[0].position = [0.30040261149406433, 5.501394748687744, 0.22499999403953552]
table[0].rotation = [0, 0, 5.791501226369579e-05]
table[0].optimize = 2
cabinet_C[0].position = [0.21013695001602173, 6.527469635009766, 0.42500001192092896]
cabinet_C[0].rotation = [0, 0, -6.350769567575389e-05]
cabinet_C[0].optimize = 2
chair[0].position = [1.350000023841858, 4.300000190734863, 0.42500001192092896]
chair[0].rotation = [0, 0, 0.8297295030491324]
chair[0].optimize = 2

