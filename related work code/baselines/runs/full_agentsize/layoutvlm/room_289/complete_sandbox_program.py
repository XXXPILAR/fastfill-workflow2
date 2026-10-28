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
    Wall(corner1=[0.00, 7.66, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[10.11, 0.00, 0.00]),
    Wall(corner1=[10.11, 0.00, 0.00], corner2=[10.11, 7.66, 0.00]),
    Wall(corner1=[10.11, 7.66, 0.00], corner2=[0.00, 7.66, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
cabinet_A = Assets(description="cabinet", size=[0.45, 1.80, 0.80], placements=[AssetInstance() for _ in range(1)])
sofa_A = Assets(description="sofa", size=[0.95, 2.20, 0.85], placements=[AssetInstance() for _ in range(1)])
table_A = Assets(description="table", size=[0.60, 1.20, 0.45], placements=[AssetInstance() for _ in range(1)])
table_B = Assets(description="table", size=[0.75, 1.40, 0.45], placements=[AssetInstance() for _ in range(1)])
sofa_B = Assets(description="sofa", size=[0.95, 2.10, 0.85], placements=[AssetInstance() for _ in range(1)])
sofa_C = Assets(description="sofa", size=[0.95, 2.20, 0.85], placements=[AssetInstance() for _ in range(1)])
sofa_D = Assets(description="sofa", size=[0.95, 2.20, 0.85], placements=[AssetInstance() for _ in range(1)])
table_C = Assets(description="table", size=[0.70, 1.30, 0.45], placements=[AssetInstance() for _ in range(1)])
lamp = Assets(description="lamp", size=[0.35, 0.35, 0.65], placements=[AssetInstance() for _ in range(1)])
table_D = Assets(description="table", size=[0.55, 0.55, 0.55], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.42, 1.60, 1.80], placements=[AssetInstance() for _ in range(1)])

cabinet_A[0].instance_id = 'cabinet_A_0'
sofa_A[0].instance_id = 'sofa_A_0'
table_A[0].instance_id = 'table_A_0'
table_B[0].instance_id = 'table_B_0'
sofa_B[0].instance_id = 'sofa_B_0'
sofa_C[0].instance_id = 'sofa_C_0'
sofa_D[0].instance_id = 'sofa_D_0'
table_C[0].instance_id = 'table_C_0'
lamp[0].instance_id = 'lamp_0'
table_D[0].instance_id = 'table_D_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

cabinet_A[0].position = [6.84081009054576, 2.3821376577636486, 0.4]
cabinet_A[0].rotation = [0, 0, 0]
sofa_A[0].position = [5.491688513003469, 6.590338169868705, 0.425]
sofa_A[0].rotation = [0, 0, 0]
table_A[0].position = [7.799970700528022, 1.29775567128532, 0.225]
table_A[0].rotation = [0, 0, 0]
table_B[0].position = [3.4237461730690666, 6.324837067303234, 0.225]
table_B[0].rotation = [0, 0, 0]
sofa_B[0].position = [6.15057096362738, 0.5486624313210935, 0.425]
sofa_B[0].rotation = [0, 0, 0]
sofa_C[0].position = [2.912504066119512, 1.7648989479727375, 0.425]
sofa_C[0].rotation = [0, 0, 0]
sofa_D[0].position = [9.882061075902751, 3.4141286809406557, 0.425]
sofa_D[0].rotation = [0, 0, 0]
table_C[0].position = [0.17826710992122452, 3.6416426008423075, 0.225]
table_C[0].rotation = [0, 0, 0]
lamp[0].position = [0.6573785864068684, 7.545911568176325, 0.325]
lamp[0].rotation = [0, 0, 0]
table_D[0].position = [7.206821167339422, 5.184972851907555, 0.275]
table_D[0].rotation = [0, 0, 0]
cabinet_B[0].position = [3.6422489551212953, 5.082984941298788, 0.9]
cabinet_B[0].rotation = [0, 0, 0]
cabinet_A[0].position = [6.84081009054576, 2.3821376577636486, 0.4]
cabinet_A[0].rotation = [0, 0, 0]
sofa_A[0].position = [5.491688513003469, 6.590338169868705, 0.425]
sofa_A[0].rotation = [0, 0, 0]
table_A[0].position = [7.799970700528022, 1.29775567128532, 0.225]
table_A[0].rotation = [0, 0, 0]
table_B[0].position = [3.4237461730690666, 6.324837067303234, 0.225]
table_B[0].rotation = [0, 0, 0]
sofa_B[0].position = [6.15057096362738, 0.5486624313210935, 0.425]
sofa_B[0].rotation = [0, 0, 0]
sofa_C[0].position = [2.912504066119512, 1.7648989479727375, 0.425]
sofa_C[0].rotation = [0, 0, 0]
sofa_D[0].position = [9.882061075902751, 3.4141286809406557, 0.425]
sofa_D[0].rotation = [0, 0, 0]
table_C[0].position = [0.17826710992122452, 3.6416426008423075, 0.225]
table_C[0].rotation = [0, 0, 0]
lamp[0].position = [0.6573785864068684, 7.545911568176325, 0.325]
lamp[0].rotation = [0, 0, 0]
table_D[0].position = [7.206821167339422, 5.184972851907555, 0.275]
table_D[0].rotation = [0, 0, 0]
cabinet_B[0].position = [3.6422489551212953, 5.082984941298788, 0.9]
cabinet_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Place two cabinets along the north wall, away from the west-wall door and
# without covering the east-wall window.
cabinet_A[0].position = [2.00, 7.435, 0.40]
cabinet_A[0].rotation = [0, 0, radians(-90)]

cabinet_B[0].position = [4.30, 7.45, 0.90]
cabinet_B[0].rotation = [0, 0, radians(-90)]

# Left seating group. sofa_A (o0001) faces table_B (o0003), as requested.
# This group is north of the door clearance zone on the west wall.
sofa_A[0].position = [0.475, 4.90, 0.425]
sofa_A[0].rotation = [0, 0, radians(0)]

table_B[0].position = [2.15, 4.90, 0.225]
table_B[0].rotation = [0, 0, radians(0)]

# South-east seating group, leaving a broad circulation route from the door.
sofa_B[0].position = [9.15, 1.35, 0.425]
sofa_B[0].rotation = [0, 0, radians(180)]

table_A[0].position = [7.45, 1.35, 0.225]
table_A[0].rotation = [0, 0, radians(0)]

# Main conversation group. table_C (o0007) is centered between sofa_C
# (o0005) and sofa_D (o0006), with the sofas facing inward.
sofa_C[0].position = [5.55, 5.25, 0.425]
sofa_C[0].rotation = [0, 0, radians(0)]

table_C[0].position = [7.20, 5.25, 0.225]
table_C[0].rotation = [0, 0, radians(0)]

sofa_D[0].position = [8.85, 5.25, 0.425]
sofa_D[0].rotation = [0, 0, radians(180)]

# The small side table and lamp occupy otherwise unused floor space.
# The lamp's z coordinate places its base on the table's top surface.
table_D[0].position = [5.35, 1.35, 0.275]
table_D[0].rotation = [0, 0, radians(0)]

lamp[0].position = [5.35, 1.35, 0.875]
lamp[0].rotation = [0, 0, radians(0)]

# Fixed anchors preserve the planned furniture zones while the solver makes
# small feasibility adjustments.
table_A_anchor = AssetInstance(position=[7.45, 1.35, 0.225])
table_B_anchor = AssetInstance(position=[2.15, 4.90, 0.225])
sofa_B_anchor = AssetInstance(position=[9.15, 1.35, 0.425])
sofa_C_anchor = AssetInstance(position=[5.55, 5.25, 0.425])
sofa_D_anchor = AssetInstance(position=[8.85, 5.25, 0.425])
table_D_anchor = AssetInstance(position=[5.35, 1.35, 0.275])
lamp_anchor = AssetInstance(position=[5.35, 1.35, 0.875])
room_center = AssetInstance(position=[5.055, 3.83, 0.40])

# Cabinets: wall contact is the primary positional relationship. Pointing
# toward the room gives both cabinets an inward-facing orientation.
solver.against_wall(cabinet_A[0], walls[3])
solver.point_towards(cabinet_A[0], room_center)

solver.against_wall(cabinet_B[0], walls[3])
solver.point_towards(cabinet_B[0], room_center)

# sofa_A remains against the west wall north of the door and directly faces
# table_B. The table is kept at a functional conversational distance.
solver.against_wall(sofa_A[0], walls[0])
solver.point_towards(sofa_A[0], table_B[0])
solver.distance_constraint(sofa_A[0], table_B[0], 1.60, 1.85, weight=10)

solver.distance_constraint(table_B[0], table_B_anchor, 0, 0, weight=10)
solver.align_with(table_B[0], sofa_A[0])

# South-east sofa and table form a separate unobstructed seating area.
solver.distance_constraint(sofa_B[0], sofa_B_anchor, 0, 0, weight=10)
solver.point_towards(sofa_B[0], table_A[0])
solver.distance_constraint(sofa_B[0], table_A[0], 1.60, 1.85, weight=10)

solver.distance_constraint(table_A[0], table_A_anchor, 0, 0, weight=10)
solver.align_with(table_A[0], sofa_B[0])

# Anchor the two opposing sofas, then orient both toward the central table.
solver.distance_constraint(sofa_C[0], sofa_C_anchor, 0, 0, weight=10)
solver.point_towards(sofa_C[0], table_C[0])

solver.distance_constraint(sofa_D[0], sofa_D_anchor, 0, 0, weight=10)
solver.point_towards(sofa_D[0], table_C[0])

# Equal high-priority distances keep table_C between sofa_C and sofa_D.
solver.distance_constraint(table_C[0], sofa_C[0], 1.65, 1.65, weight=10)
solver.distance_constraint(table_C[0], sofa_D[0], 1.65, 1.65, weight=10)
solver.align_with(table_C[0], sofa_C[0])

# Keep the side table in its planned position and give it an orientation
# consistent with the nearby south-east furniture group.
solver.distance_constraint(table_D[0], table_D_anchor, 0, 0, weight=10)
solver.align_with(table_D[0], table_A[0])

# The support relationship is most important for the lamp. Its matching anchor
# supplies the required position-based constraint, while alignment provides
# the required orientation-based constraint.
solver.on_top_of(lamp[0], table_D[0])
solver.distance_constraint(lamp[0], lamp_anchor, 0, 0, weight=10)
solver.align_with(lamp[0], table_D[0])

solver.constraints = []
cabinet_A[0].position = [2.0, 7.4376726150512695, 0.4000000059604645]
cabinet_A[0].rotation = [0, 0, -1.570796283079175]
cabinet_A[0].optimize = 2
sofa_C[0].position = [5.550000190734863, 5.25, 0.42500001192092896]
sofa_C[0].rotation = [0, 0, 0.0157079639172164]
sofa_C[0].optimize = 2
table_D[0].position = [5.349999904632568, 1.350000023841858, 0.2750000059604645]
table_D[0].rotation = [0, 0, -3.1259192608771658]
table_D[0].optimize = 2
cabinet_B[0].position = [4.300000190734863, 7.452672481536865, 0.8999999761581421]
cabinet_B[0].rotation = [0, 0, -1.5707962833469313]
cabinet_B[0].optimize = 2
lamp[0].position = [5.349999904632568, 1.350000023841858, 0.875]
lamp[0].rotation = [0, 0, -3.1259199325719678]
lamp[0].optimize = 2
table_A[0].position = [7.449999809265137, 1.350000023841858, 0.22499999403953552]
table_A[0].rotation = [0, 0, -3.1259187602142338]
table_A[0].optimize = 2
sofa_B[0].position = [9.149999618530273, 1.350000023841858, 0.42500001192092896]
sofa_B[0].rotation = [0, 0, -3.125884689672577]
sofa_B[0].optimize = 2
table_B[0].position = [2.1500000953674316, 4.900000095367432, 0.22499999403953552]
table_B[0].rotation = [0, 0, 2.9215044491365194e-08]
table_B[0].optimize = 2
sofa_A[0].position = [0.47499993443489075, 4.900000095367432, 0.42500001192092896]
sofa_A[0].rotation = [0, 0, 3.097538896703255e-08]
sofa_A[0].optimize = 2
table_C[0].position = [7.20087194442749, 5.25, 0.22499999403953552]
table_C[0].rotation = [0, 0, 0.015707962784977787]
table_C[0].optimize = 2
sofa_D[0].position = [8.850000381469727, 5.25, 0.42500001192092896]
sofa_D[0].rotation = [0, 0, -3.1290262823329655]
sofa_D[0].optimize = 2

