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
    Wall(corner1=[8.09, 7.81, 0.00], corner2=[5.27, 7.81, 0.00]),
    Wall(corner1=[5.27, 7.81, 0.00], corner2=[0.04, 6.17, 0.00]),
    Wall(corner1=[0.04, 6.17, 0.00], corner2=[0.00, 6.13, 0.00]),
    Wall(corner1=[0.00, 6.13, 0.00], corner2=[0.00, 4.65, 0.00]),
    Wall(corner1=[0.00, 4.65, 0.00], corner2=[0.04, 4.61, 0.00]),
    Wall(corner1=[0.04, 4.61, 0.00], corner2=[5.20, 0.00, 0.00]),
    Wall(corner1=[5.20, 0.00, 0.00], corner2=[8.09, 0.00, 0.00]),
    Wall(corner1=[8.09, 0.00, 0.00], corner2=[8.12, 0.04, 0.00]),
    Wall(corner1=[8.12, 0.04, 0.00], corner2=[8.12, 7.77, 0.00]),
    Wall(corner1=[8.12, 7.77, 0.00], corner2=[8.09, 7.81, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
oven_A = Assets(description="oven", size=[0.60, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.60, 0.90, 0.90], placements=[AssetInstance() for _ in range(1)])
cup = Assets(description="cup", size=[0.09, 0.09, 0.10], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.35, 1.00, 0.70], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
table_A = Assets(description="table", size=[0.90, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
machine = Assets(description="machine", size=[0.65, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
sink = Assets(description="sink", size=[0.50, 0.80, 0.20], placements=[AssetInstance() for _ in range(1)])
cabinet_C = Assets(description="cabinet", size=[0.60, 0.90, 0.85], placements=[AssetInstance() for _ in range(1)])
box = Assets(description="box", size=[0.30, 0.40, 0.25], placements=[AssetInstance() for _ in range(1)])
basket = Assets(description="basket", size=[0.32, 0.42, 0.25], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
table_B = Assets(description="table", size=[0.80, 1.40, 0.75], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
cabinet_D = Assets(description="cabinet", size=[0.60, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
cabinet_E = Assets(description="cabinet", size=[0.60, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
bottle = Assets(description="bottle", size=[0.08, 0.08, 0.28], placements=[AssetInstance() for _ in range(1)])
chair_D = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
cabinet_F = Assets(description="cabinet", size=[0.35, 1.00, 0.70], placements=[AssetInstance() for _ in range(1)])
chair_E = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
oven_B = Assets(description="oven", size=[0.60, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
cabinet_G = Assets(description="cabinet", size=[0.60, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])

oven_A[0].instance_id = 'oven_A_0'
cabinet_A[0].instance_id = 'cabinet_A_0'
cup[0].instance_id = 'cup_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
chair_A[0].instance_id = 'chair_A_0'
table_A[0].instance_id = 'table_A_0'
machine[0].instance_id = 'machine_0'
sink[0].instance_id = 'sink_0'
cabinet_C[0].instance_id = 'cabinet_C_0'
box[0].instance_id = 'box_0'
basket[0].instance_id = 'basket_0'
chair_B[0].instance_id = 'chair_B_0'
table_B[0].instance_id = 'table_B_0'
chair_C[0].instance_id = 'chair_C_0'
cabinet_D[0].instance_id = 'cabinet_D_0'
cabinet_E[0].instance_id = 'cabinet_E_0'
bottle[0].instance_id = 'bottle_0'
chair_D[0].instance_id = 'chair_D_0'
cabinet_F[0].instance_id = 'cabinet_F_0'
chair_E[0].instance_id = 'chair_E_0'
oven_B[0].instance_id = 'oven_B_0'
cabinet_G[0].instance_id = 'cabinet_G_0'
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

oven_A[0].position = [1.3430187090842542, 4.566138810609223, 0.425]
oven_A[0].rotation = [0, 0, 0]
cabinet_A[0].position = [0.7085040094793102, 5.99824230813043, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
cup[0].position = [5.8005311920489255, 0.42646680739818166, 0.05]
cup[0].rotation = [0, 0, 0]
cabinet_B[0].position = [6.605958209082906, 2.1835836643731694, 0.35]
cabinet_B[0].rotation = [0, 0, 0]
chair_A[0].position = [6.369599956829835, 5.507302235561263, 0.425]
chair_A[0].rotation = [0, 0, 0]
table_A[0].position = [1.1373942760381581, 4.469268258311909, 0.375]
table_A[0].rotation = [0, 0, 0]
machine[0].position = [1.0191679111007281, 5.584989916100933, 0.425]
machine[0].rotation = [0, 0, 0]
sink[0].position = [7.951517606852234, 0.020901641624902767, 0.1]
sink[0].rotation = [0, 0, 0]
cabinet_C[0].position = [4.347144788313114, 4.334328979821001, 0.425]
cabinet_C[0].rotation = [0, 0, 0]
box[0].position = [5.983589399993, 3.3705742773143914, 0.125]
box[0].rotation = [0, 0, 0]
basket[0].position = [0.39514773602657827, 5.124073605821282, 0.125]
basket[0].rotation = [0, 0, 0]
chair_B[0].position = [6.761962092084819, 1.3040097448719505, 0.425]
chair_B[0].rotation = [0, 0, 0]
table_B[0].position = [2.8008814557816764, 4.7791320642112725, 0.375]
table_B[0].rotation = [0, 0, 0]
chair_C[0].position = [5.252329733549399, 4.635471130441123, 0.425]
chair_C[0].rotation = [0, 0, 0]
cabinet_D[0].position = [1.5094527487143337, 6.564233556185277, 0.45]
cabinet_D[0].rotation = [0, 0, 0]
cabinet_E[0].position = [3.411812659210544, 3.194928265742928, 0.45]
cabinet_E[0].rotation = [0, 0, 0]
bottle[0].position = [7.670337376269423, 6.886266498955489, 0.14]
bottle[0].rotation = [0, 0, 0]
chair_D[0].position = [7.797113598372846, 6.3783988083665175, 0.425]
chair_D[0].rotation = [0, 0, 0]
cabinet_F[0].position = [4.96388291357919, 5.931014137620852, 0.35]
cabinet_F[0].rotation = [0, 0, 0]
chair_E[0].position = [3.61589954039511, 4.759278688076481, 0.425]
chair_E[0].rotation = [0, 0, 0]
oven_B[0].position = [4.790597135184067, 5.252769587296078, 0.425]
oven_B[0].rotation = [0, 0, 0]
cabinet_G[0].position = [5.931434056335622, 0.5433567640189367, 0.45]
cabinet_G[0].rotation = [0, 0, 0]
oven_A[0].position = [1.3430187090842542, 4.566138810609223, 0.425]
oven_A[0].rotation = [0, 0, 0]
cabinet_A[0].position = [0.7085040094793102, 5.99824230813043, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
cup[0].position = [5.8005311920489255, 0.42646680739818166, 0.05]
cup[0].rotation = [0, 0, 0]
cabinet_B[0].position = [6.605958209082906, 2.1835836643731694, 0.35]
cabinet_B[0].rotation = [0, 0, 0]
chair_A[0].position = [6.369599956829835, 5.507302235561263, 0.425]
chair_A[0].rotation = [0, 0, 0]
table_A[0].position = [1.1373942760381581, 4.469268258311909, 0.375]
table_A[0].rotation = [0, 0, 0]
machine[0].position = [1.0191679111007281, 5.584989916100933, 0.425]
machine[0].rotation = [0, 0, 0]
sink[0].position = [7.951517606852234, 0.020901641624902767, 0.1]
sink[0].rotation = [0, 0, 0]
cabinet_C[0].position = [4.347144788313114, 4.334328979821001, 0.425]
cabinet_C[0].rotation = [0, 0, 0]
box[0].position = [5.983589399993, 3.3705742773143914, 0.125]
box[0].rotation = [0, 0, 0]
basket[0].position = [0.39514773602657827, 5.124073605821282, 0.125]
basket[0].rotation = [0, 0, 0]
chair_B[0].position = [6.761962092084819, 1.3040097448719505, 0.425]
chair_B[0].rotation = [0, 0, 0]
table_B[0].position = [2.8008814557816764, 4.7791320642112725, 0.375]
table_B[0].rotation = [0, 0, 0]
chair_C[0].position = [5.252329733549399, 4.635471130441123, 0.425]
chair_C[0].rotation = [0, 0, 0]
cabinet_D[0].position = [1.5094527487143337, 6.564233556185277, 0.45]
cabinet_D[0].rotation = [0, 0, 0]
cabinet_E[0].position = [3.411812659210544, 3.194928265742928, 0.45]
cabinet_E[0].rotation = [0, 0, 0]
bottle[0].position = [7.670337376269423, 6.886266498955489, 0.14]
bottle[0].rotation = [0, 0, 0]
chair_D[0].position = [7.797113598372846, 6.3783988083665175, 0.425]
chair_D[0].rotation = [0, 0, 0]
cabinet_F[0].position = [4.96388291357919, 5.931014137620852, 0.35]
cabinet_F[0].rotation = [0, 0, 0]
chair_E[0].position = [3.61589954039511, 4.759278688076481, 0.425]
chair_E[0].rotation = [0, 0, 0]
oven_B[0].position = [4.790597135184067, 5.252769587296078, 0.425]
oven_B[0].rotation = [0, 0, 0]
cabinet_G[0].position = [5.931434056335622, 0.5433567640189367, 0.45]
cabinet_G[0].rotation = [0, 0, 0]

solver.constraints = []

# Orientation references used to keep wall-mounted fixtures and furniture aligned.
right_wall_facing = AssetInstance(rotation=[0, 0, radians(180)])
sloped_wall_facing = AssetInstance(rotation=[0, 0, radians(-72.6)])
room_axis_facing = AssetInstance(rotation=[0, 0, 0])

# Place the lower kitchen run against the right wall. The run stops before the
# side door at (8.12, 5.21), leaving its inward approach unobstructed.
oven_A[0].position = [7.82, 2.52, 0.425]
oven_A[0].rotation = [0, 0, radians(180)]

cabinet_A[0].position = [7.82, 1.75, 0.45]
cabinet_A[0].rotation = [0, 0, radians(180)]

machine[0].position = [7.795, 3.13, 0.425]
machine[0].rotation = [0, 0, radians(180)]

cabinet_C[0].position = [7.82, 3.88, 0.425]
cabinet_C[0].rotation = [0, 0, radians(180)]

cabinet_D[0].position = [7.82, 0.70, 0.45]
cabinet_D[0].rotation = [0, 0, radians(180)]

# Continue the kitchen/storage run above the side doorway.
cabinet_E[0].position = [7.82, 7.31, 0.45]
cabinet_E[0].rotation = [0, 0, radians(180)]

cabinet_G[0].position = [7.82, 6.30, 0.45]
cabinet_G[0].rotation = [0, 0, radians(180)]

# Shallow cabinets and the second oven follow the upper-left sloping wall.
# Their fronts point southeast into the room.
cabinet_B[0].position = [1.30, 6.24, 0.35]
cabinet_B[0].rotation = [0, 0, radians(-72.6)]

cabinet_F[0].position = [2.50, 6.62, 0.35]
cabinet_F[0].rotation = [0, 0, radians(-72.6)]

oven_B[0].position = [3.75, 6.94, 0.425]
oven_B[0].rotation = [0, 0, radians(-72.6)]

# Place the two tables in the open central area. Their separation leaves room
# for chair_D (o0017) to sit between them without intersecting either table.
table_A[0].position = [4.40, 4.30, 0.375]  # table o0005
table_A[0].rotation = [0, 0, 0]

table_B[0].position = [6.40, 4.10, 0.375]  # table o0012
table_B[0].rotation = [0, 0, 0]

# chair_A (o0004) and chair_B (o0011) occupy opposite sides of table_B.
# chair_B explicitly faces chair_A as required.
chair_A[0].position = [6.40, 5.25, 0.425]
chair_A[0].rotation = [0, 0, radians(-90)]

chair_B[0].position = [6.40, 2.95, 0.425]
chair_B[0].rotation = [0, 0, radians(90)]

chair_C[0].position = [7.35, 4.05, 0.425]
chair_C[0].rotation = [0, 0, radians(180)]

chair_D[0].position = [5.43, 4.20, 0.425]  # chair o0017
chair_D[0].rotation = [0, 0, 0]

# chair_E (o0019) is 0.90 m from table_A's center. Given the table and chair
# half-widths, this corresponds to a physical edge gap of about 0.19 m.
chair_E[0].position = [3.50, 4.30, 0.425]
chair_E[0].rotation = [0, 0, 0]

# Put all small objects on usable support surfaces.
sink[0].position = [7.82, 0.70, 1.00]
sink[0].rotation = [0, 0, radians(180)]

cup[0].position = [4.40, 4.30, 0.80]
cup[0].rotation = [0, 0, 0]

box[0].position = [7.82, 1.75, 1.025]
box[0].rotation = [0, 0, radians(180)]

basket[0].position = [7.82, 6.30, 1.025]
basket[0].rotation = [0, 0, radians(180)]

bottle[0].position = [7.82, 7.31, 1.04]
bottle[0].rotation = [0, 0, radians(180)]


# Important semantic constraints are declared first so they take priority.
# chair_D remains between the two tables and clear of both bounding boxes.
solver.distance_constraint(chair_D[0], table_A[0], 0.90, 1.15, weight=10)
solver.distance_constraint(chair_D[0], table_B[0], 0.80, 1.10, weight=10)
solver.point_towards(chair_D[0], table_B[0])

# chair_B must face chair_A.
solver.point_towards(chair_B[0], chair_A[0])

# Convert the requested 0.20 m table clearance into a center-distance range:
# 0.45 m table half-width + 0.26 m chair half-width + up to 0.20 m gap.
solver.distance_constraint(chair_E[0], table_A[0], 0.71, 0.91, weight=10)
solver.point_towards(chair_E[0], table_A[0])

# Fixed anchors preserve the planned non-overlapping arrangement while allowing
# the semantic constraints above to retain priority.
oven_A_anchor = AssetInstance(position=[7.82, 2.52, 0.425])
cabinet_A_anchor = AssetInstance(position=[7.82, 1.75, 0.45])
machine_anchor = AssetInstance(position=[7.795, 3.13, 0.425])
cabinet_C_anchor = AssetInstance(position=[7.82, 3.88, 0.425])
cabinet_D_anchor = AssetInstance(position=[7.82, 0.70, 0.45])
cabinet_E_anchor = AssetInstance(position=[7.82, 7.31, 0.45])
cabinet_G_anchor = AssetInstance(position=[7.82, 6.30, 0.45])
cabinet_B_anchor = AssetInstance(position=[1.30, 6.24, 0.35])
cabinet_F_anchor = AssetInstance(position=[2.50, 6.62, 0.35])
oven_B_anchor = AssetInstance(position=[3.75, 6.94, 0.425])
table_A_anchor = AssetInstance(position=[4.40, 4.30, 0.375])
table_B_anchor = AssetInstance(position=[6.40, 4.10, 0.375])
chair_A_anchor = AssetInstance(position=[6.40, 5.25, 0.425])
chair_B_anchor = AssetInstance(position=[6.40, 2.95, 0.425])
chair_C_anchor = AssetInstance(position=[7.35, 4.05, 0.425])
chair_D_anchor = AssetInstance(position=[5.43, 4.20, 0.425])
chair_E_anchor = AssetInstance(position=[3.50, 4.30, 0.425])
sink_anchor = AssetInstance(position=[7.82, 0.70, 1.00])
cup_anchor = AssetInstance(position=[4.40, 4.30, 0.80])
box_anchor = AssetInstance(position=[7.82, 1.75, 1.025])
basket_anchor = AssetInstance(position=[7.82, 6.30, 1.025])
bottle_anchor = AssetInstance(position=[7.82, 7.31, 1.04])

solver.distance_constraint(oven_A[0], oven_A_anchor, 0, 0, weight=10)
solver.distance_constraint(cabinet_A[0], cabinet_A_anchor, 0, 0, weight=10)
solver.distance_constraint(machine[0], machine_anchor, 0, 0, weight=10)
solver.distance_constraint(cabinet_C[0], cabinet_C_anchor, 0, 0, weight=10)
solver.distance_constraint(cabinet_D[0], cabinet_D_anchor, 0, 0, weight=10)
solver.distance_constraint(cabinet_E[0], cabinet_E_anchor, 0, 0, weight=10)
solver.distance_constraint(cabinet_G[0], cabinet_G_anchor, 0, 0, weight=10)
solver.distance_constraint(cabinet_B[0], cabinet_B_anchor, 0, 0, weight=10)
solver.distance_constraint(cabinet_F[0], cabinet_F_anchor, 0, 0, weight=10)
solver.distance_constraint(oven_B[0], oven_B_anchor, 0, 0, weight=10)
solver.distance_constraint(table_A[0], table_A_anchor, 0, 0, weight=10)
solver.distance_constraint(table_B[0], table_B_anchor, 0, 0, weight=10)
solver.distance_constraint(chair_A[0], chair_A_anchor, 0, 0, weight=10)
solver.distance_constraint(chair_B[0], chair_B_anchor, 0, 0, weight=10)
solver.distance_constraint(chair_C[0], chair_C_anchor, 0, 0, weight=10)
solver.distance_constraint(chair_D[0], chair_D_anchor, 0, 0, weight=5)
solver.distance_constraint(chair_E[0], chair_E_anchor, 0, 0, weight=5)
solver.distance_constraint(sink[0], sink_anchor, 0, 0, weight=10)
solver.distance_constraint(cup[0], cup_anchor, 0, 0, weight=10)
solver.distance_constraint(box[0], box_anchor, 0, 0, weight=10)
solver.distance_constraint(basket[0], basket_anchor, 0, 0, weight=10)
solver.distance_constraint(bottle[0], bottle_anchor, 0, 0, weight=10)

# Keep the perimeter fixtures physically against their assigned walls.
solver.against_wall(oven_A[0], walls[8])
solver.against_wall(cabinet_A[0], walls[8])
solver.against_wall(machine[0], walls[8])
solver.against_wall(cabinet_C[0], walls[8])
solver.against_wall(cabinet_D[0], walls[8])
solver.against_wall(cabinet_E[0], walls[8])
solver.against_wall(cabinet_G[0], walls[8])
solver.against_wall(cabinet_B[0], walls[1])
solver.against_wall(cabinet_F[0], walls[1])
solver.against_wall(oven_B[0], walls[1])

# Explicit support constraints keep small objects above their surfaces.
solver.on_top_of(sink[0], cabinet_D[0])
solver.on_top_of(cup[0], table_A[0])
solver.on_top_of(box[0], cabinet_A[0])
solver.on_top_of(basket[0], cabinet_G[0])
solver.on_top_of(bottle[0], cabinet_E[0])

# Orient all right-wall fixtures toward the room and all sloped-wall fixtures
# perpendicular to their wall.
solver.align_with(oven_A[0], right_wall_facing)
solver.align_with(cabinet_A[0], right_wall_facing)
solver.align_with(machine[0], right_wall_facing)
solver.align_with(cabinet_C[0], right_wall_facing)
solver.align_with(cabinet_D[0], right_wall_facing)
solver.align_with(cabinet_E[0], right_wall_facing)
solver.align_with(cabinet_G[0], right_wall_facing)

solver.align_with(cabinet_B[0], sloped_wall_facing)
solver.align_with(cabinet_F[0], sloped_wall_facing)
solver.align_with(oven_B[0], sloped_wall_facing)

# Remaining furniture receives explicit functional orientation constraints.
solver.align_with(table_A[0], room_axis_facing)
solver.align_with(table_B[0], room_axis_facing)
solver.point_towards(chair_A[0], chair_B[0])
solver.point_towards(chair_C[0], table_B[0])

# Small items align with the support beneath them.
solver.align_with(sink[0], cabinet_D[0])
solver.align_with(cup[0], table_A[0])
solver.align_with(box[0], cabinet_A[0])
solver.align_with(basket[0], cabinet_G[0])
solver.align_with(bottle[0], cabinet_E[0])

solver.constraints = []
cabinet_G[0].position = [7.825556755065918, 6.300000190734863, 0.44999998807907104]
cabinet_G[0].rotation = [0, 0, -3.1362942490694334]
cabinet_G[0].optimize = 2
cabinet_E[0].position = [7.826448917388916, 7.309999942779541, 0.44999998807907104]
cabinet_E[0].rotation = [0, 0, -3.1362934524478083]
cabinet_E[0].optimize = 2
table_B[0].position = [6.400000095367432, 4.099999904632568, 0.375]
table_B[0].rotation = [0, 0, 0.01884955539881635]
table_B[0].optimize = 2
sink[0].position = [7.820000171661377, 0.699999988079071, 1.0]
sink[0].rotation = [0, 0, 3.1235521559729977]
sink[0].optimize = 2
basket[0].position = [7.820000171661377, 6.300000190734863, 1.024999976158142]
basket[0].rotation = [0, 0, 3.1235521559729977]
basket[0].optimize = 2
oven_B[0].position = [3.676105260848999, 6.997509002685547, 0.42500001192092896]
oven_B[0].rotation = [0, 0, -1.2668835448821458]
oven_B[0].optimize = 2
chair_B[0].position = [6.400000095367432, 2.950000047683716, 0.42500001192092896]
chair_B[0].rotation = [0, 0, 1.5833626980517244]
chair_B[0].optimize = 2
cabinet_B[0].position = [1.2020045518875122, 6.337995529174805, 0.3499999940395355]
cabinet_B[0].rotation = [0, 0, -1.2669231074737823]
cabinet_B[0].optimize = 2
chair_D[0].position = [5.429999828338623, 4.199999809265137, 0.42500001192092896]
chair_D[0].rotation = [0, 0, 0.0157079639172164]
chair_D[0].optimize = 2
chair_E[0].position = [3.5, 4.300000190734863, 0.42500001192092896]
chair_E[0].rotation = [0, 0, 0.01256637125682779]
chair_E[0].optimize = 2
oven_A[0].position = [7.826401710510254, 2.5199999809265137, 0.42500001192092896]
oven_A[0].rotation = [0, 0, -3.1373721166587885]
oven_A[0].optimize = 2
chair_C[0].position = [7.349999904632568, 4.050000190734863, 0.42500001192092896]
chair_C[0].rotation = [0, 0, -3.1321678761290697]
chair_C[0].optimize = 2
cabinet_F[0].position = [2.402413845062256, 6.717585563659668, 0.3499999940395355]
cabinet_F[0].rotation = [0, 0, -1.2669231992800731]
cabinet_F[0].optimize = 2
table_A[0].position = [4.400000095367432, 4.300000190734863, 0.375]
table_A[0].rotation = [0, 0, 0.025132740109855806]
table_A[0].optimize = 2
cabinet_D[0].position = [7.825556755065918, 0.699999988079071, 0.44999998807907104]
cabinet_D[0].rotation = [0, 0, -3.1362942490694334]
cabinet_D[0].optimize = 2
cup[0].position = [4.400000095367432, 4.300000190734863, 0.800000011920929]
cup[0].rotation = [0, 0, 0.021852364228046945]
cup[0].optimize = 2
chair_A[0].position = [6.400000095367432, 5.25, 0.42500001192092896]
chair_A[0].rotation = [0, 0, -1.5582299555380688]
chair_A[0].optimize = 2
box[0].position = [7.820000171661377, 1.75, 1.024999976158142]
box[0].rotation = [0, 0, 3.1235633698953054]
box[0].optimize = 2
cabinet_A[0].position = [7.826448917388916, 1.75, 0.44999998807907104]
cabinet_A[0].rotation = [0, 0, -3.1362934185253395]
cabinet_A[0].optimize = 2
machine[0].position = [7.801405906677246, 3.130000114440918, 0.42500001192092896]
machine[0].rotation = [0, 0, -3.1373715274539675]
machine[0].optimize = 2
bottle[0].position = [7.820000171661377, 7.309999942779541, 1.0399999618530273]
bottle[0].rotation = [0, 0, 3.1235632995022584]
bottle[0].optimize = 2
cabinet_C[0].position = [7.82640266418457, 3.880000114440918, 0.42500001192092896]
cabinet_C[0].rotation = [0, 0, -3.137372334391582]
cabinet_C[0].optimize = 2

