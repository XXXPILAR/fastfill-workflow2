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
    Wall(corner1=[4.59, 3.05, 0.00], corner2=[4.59, 3.62, 0.00]),
    Wall(corner1=[4.59, 3.62, 0.00], corner2=[4.04, 3.61, 0.00]),
    Wall(corner1=[4.04, 3.61, 0.00], corner2=[1.56, 3.61, 0.00]),
    Wall(corner1=[1.56, 3.61, 0.00], corner2=[0.00, 3.56, 0.00]),
    Wall(corner1=[0.00, 3.56, 0.00], corner2=[0.01, 1.01, 0.00]),
    Wall(corner1=[0.01, 1.01, 0.00], corner2=[0.01, 0.00, 0.00]),
    Wall(corner1=[0.01, 0.00, 0.00], corner2=[4.87, 0.00, 0.00]),
    Wall(corner1=[4.87, 0.00, 0.00], corner2=[4.87, 3.05, 0.00]),
    Wall(corner1=[4.87, 3.05, 0.00], corner2=[4.59, 3.05, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
lounge_chair_A = Assets(description="A modern dining chair with a curved wooden backrest and a cushioned seat. The chair has four slender legs made of wood.", size=[0.56, 0.52, 0.79], placements=[AssetInstance() for _ in range(1)])
drawer_chest = Assets(description="A wooden dresser with a sleek design featuring multiple drawers and thin legs. The dresser has a warm brown finish and gold-colored knobs on each drawer.", size=[0.45, 1.35, 0.82], placements=[AssetInstance() for _ in range(1)])
dining_table = Assets(description="A sleek wooden dining table with a rectangular top and four slightly angled legs.", size=[0.90, 1.80, 0.75], placements=[AssetInstance() for _ in range(1)])
bookcase = Assets(description="A tall, modern wardrobe with a wooden frame and gray doors. It features a central black panel and a shelf with decorative items.", size=[0.45, 1.20, 2.10], placements=[AssetInstance() for _ in range(1)])
lounge_chair_B = Assets(description="A modern dining chair with a curved wooden backrest and a cushioned seat. The chair has four slender legs made of wood.", size=[0.56, 0.52, 0.79], placements=[AssetInstance() for _ in range(1)])
bicycle = Assets(description="A classic-style bicycle with a black frame, curved handlebars, and a comfortable seat. It features large wheels with thin tires, suitable for smooth rides on paved surfaces.", size=[0.60, 1.75, 1.10], placements=[AssetInstance() for _ in range(1)])
lounge_chair_C = Assets(description="A modern dining chair with a curved wooden backrest and a cushioned seat. The chair has four slender legs made of wood.", size=[0.56, 0.52, 0.79], placements=[AssetInstance() for _ in range(1)])
lounge_chair_D = Assets(description="A modern dining chair with a curved wooden backrest and a cushioned seat. The chair has four slender legs made of wood.", size=[0.56, 0.52, 0.79], placements=[AssetInstance() for _ in range(1)])

lounge_chair_A[0].instance_id = 'lounge_chair_A_0'
drawer_chest[0].instance_id = 'drawer_chest_0'
dining_table[0].instance_id = 'dining_table_0'
bookcase[0].instance_id = 'bookcase_0'
lounge_chair_B[0].instance_id = 'lounge_chair_B_0'
bicycle[0].instance_id = 'bicycle_0'
lounge_chair_C[0].instance_id = 'lounge_chair_C_0'
lounge_chair_D[0].instance_id = 'lounge_chair_D_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'
walls[8].instance_id = 'walls_8'

lounge_chair_A[0].position = [0.06889470490641277, 3.2290465457398607, 0.395]
lounge_chair_A[0].rotation = [0, 0, 0]
drawer_chest[0].position = [4.76354971602735, 2.821633156316086, 0.41]
drawer_chest[0].rotation = [0, 0, 0]
dining_table[0].position = [4.170418375232406, 2.238632492436835, 0.375]
dining_table[0].rotation = [0, 0, 0]
bookcase[0].position = [0.07128964903448964, 3.087098110901537, 1.05]
bookcase[0].rotation = [0, 0, 0]
lounge_chair_B[0].position = [1.257655117376464, 2.0997624063650644, 0.395]
lounge_chair_B[0].rotation = [0, 0, 0]
bicycle[0].position = [2.6703234516753174, 2.740427422184368, 0.55]
bicycle[0].rotation = [0, 0, 0]
lounge_chair_C[0].position = [4.254291183052452, 2.3581752543637173, 0.395]
lounge_chair_C[0].rotation = [0, 0, 0]
lounge_chair_D[0].position = [4.049490411359078, 1.8323704034925203, 0.395]
lounge_chair_D[0].rotation = [0, 0, 0]
lounge_chair_A[0].position = [0.06889470490641277, 3.2290465457398607, 0.395]
lounge_chair_A[0].rotation = [0, 0, 0]
drawer_chest[0].position = [4.76354971602735, 2.821633156316086, 0.41]
drawer_chest[0].rotation = [0, 0, 0]
dining_table[0].position = [4.170418375232406, 2.238632492436835, 0.375]
dining_table[0].rotation = [0, 0, 0]
bookcase[0].position = [0.07128964903448964, 3.087098110901537, 1.05]
bookcase[0].rotation = [0, 0, 0]
lounge_chair_B[0].position = [1.257655117376464, 2.0997624063650644, 0.395]
lounge_chair_B[0].rotation = [0, 0, 0]
bicycle[0].position = [2.6703234516753174, 2.740427422184368, 0.55]
bicycle[0].rotation = [0, 0, 0]
lounge_chair_C[0].position = [4.254291183052452, 2.3581752543637173, 0.395]
lounge_chair_C[0].rotation = [0, 0, 0]
lounge_chair_D[0].position = [4.049490411359078, 1.8323704034925203, 0.395]
lounge_chair_D[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the dining group centrally, with lounge_chair_A and lounge_chair_B
# on opposite sides so the table lies directly between them.
lounge_chair_A[0].position = [1.55, 1.80, 0.395]
lounge_chair_A[0].rotation = [0, 0, radians(0)]

drawer_chest[0].position = [0.235, 2.25, 0.41]
drawer_chest[0].rotation = [0, 0, radians(0)]

dining_table[0].position = [2.40, 1.80, 0.375]
dining_table[0].rotation = [0, 0, radians(0)]

# Rotate the bookcase so its wide side follows the upper wall.
bookcase[0].position = [3.43, 3.385, 1.05]
bookcase[0].rotation = [0, 0, radians(90)]

# This chair explicitly faces the dining table, as required.
lounge_chair_B[0].position = [3.25, 1.80, 0.395]
lounge_chair_B[0].rotation = [0, 0, radians(180)]

# Store the bicycle parallel to and against the right wall, away from the
# central dining area.
bicycle[0].position = [4.57, 1.30, 0.55]
bicycle[0].rotation = [0, 0, radians(0)]

# Place the remaining chairs at the short ends of the table.
lounge_chair_C[0].position = [2.40, 0.52, 0.395]
lounge_chair_C[0].rotation = [0, 0, radians(90)]

lounge_chair_D[0].position = [2.40, 3.08, 0.395]
lounge_chair_D[0].rotation = [0, 0, radians(-90)]


# Fixed points preserve the intended non-overlapping arrangement while still
# allowing the solver to reconcile the layout with the room boundary.
anchor_chair_A = AssetInstance(position=[1.55, 1.80, 0.395])
anchor_drawer = AssetInstance(position=[0.235, 2.25, 0.41])
anchor_table = AssetInstance(position=[2.40, 1.80, 0.375])
anchor_bookcase = AssetInstance(position=[3.43, 3.385, 1.05])
anchor_chair_B = AssetInstance(position=[3.25, 1.80, 0.395])
anchor_bicycle = AssetInstance(position=[4.57, 1.30, 0.55])
anchor_chair_C = AssetInstance(position=[2.40, 0.52, 0.395])
anchor_chair_D = AssetInstance(position=[2.40, 3.08, 0.395])

# Orientation references for objects whose facing direction is not naturally
# expressed by pointing toward another scene asset.
parallel_to_y_axis = AssetInstance(rotation=[0, 0, radians(0)])
parallel_to_x_axis = AssetInstance(rotation=[0, 0, radians(90)])


# The wall requirement for the drawer is the highest-priority constraint.
solver.against_wall(drawer_chest[0], walls[4])
solver.distance_constraint(
    drawer_chest[0], anchor_drawer, 0, 0, weight=10
)
solver.align_with(drawer_chest[0], parallel_to_y_axis)

# Anchor the table before adding the dining-group relationships. Its long axis
# runs north-south and leaves circulation space around the group.
solver.distance_constraint(
    dining_table[0], anchor_table, 0, 0, weight=10
)
solver.align_with(dining_table[0], parallel_to_y_axis)

# Opposing side chairs: these positions put the table between A and B.
solver.distance_constraint(
    lounge_chair_A[0], anchor_chair_A, 0, 0, weight=10
)
solver.point_towards(lounge_chair_A[0], dining_table[0])
solver.distance_constraint(
    lounge_chair_A[0], dining_table[0], 0.85, 0.85, weight=5
)

solver.distance_constraint(
    lounge_chair_B[0], anchor_chair_B, 0, 0, weight=10
)
solver.point_towards(lounge_chair_B[0], dining_table[0])
solver.distance_constraint(
    lounge_chair_B[0], dining_table[0], 0.85, 0.85, weight=5
)

# End chairs face inward toward the center of the table.
solver.distance_constraint(
    lounge_chair_C[0], anchor_chair_C, 0, 0, weight=10
)
solver.point_towards(lounge_chair_C[0], dining_table[0])
solver.distance_constraint(
    lounge_chair_C[0], dining_table[0], 1.28, 1.28, weight=5
)

solver.distance_constraint(
    lounge_chair_D[0], anchor_chair_D, 0, 0, weight=10
)
solver.point_towards(lounge_chair_D[0], dining_table[0])
solver.distance_constraint(
    lounge_chair_D[0], dining_table[0], 1.28, 1.28, weight=5
)

# Keep the tall bookcase stable against the long upper wall and parallel to it.
solver.against_wall(bookcase[0], walls[2])
solver.distance_constraint(
    bookcase[0], anchor_bookcase, 0, 0, weight=10
)
solver.align_with(bookcase[0], parallel_to_x_axis)

# Keep the bicycle against the right wall and parallel to that wall.
solver.against_wall(bicycle[0], walls[7])
solver.distance_constraint(
    bicycle[0], anchor_bicycle, 0, 0, weight=10
)
solver.align_with(bicycle[0], parallel_to_y_axis)

solver.constraints = []
drawer_chest[0].position = [0.25801414251327515, 1.2456496953964233, 0.4099999964237213]
drawer_chest[0].rotation = [0, 0, 0.03873242541726601]
drawer_chest[0].optimize = 2
bicycle[0].position = [4.031109809875488, 2.2628183364868164, 0.550000011920929]
bicycle[0].rotation = [0, 0, -2.332552069846808]
bicycle[0].optimize = 2
lounge_chair_C[0].position = [2.4000000953674316, 0.5199999809265137, 0.39500001072883606]
lounge_chair_C[0].rotation = [0, 0, 1.5833626980517244]
lounge_chair_C[0].optimize = 2
lounge_chair_D[0].position = [2.4000000953674316, 3.0799999237060547, 0.39500001072883606]
lounge_chair_D[0].rotation = [0, 0, -1.5582299555380688]
lounge_chair_D[0].optimize = 2
bookcase[0].position = [4.028418064117432, 3.062183141708374, 1.0499999523162842]
bookcase[0].rotation = [0, 0, -2.2503572268579917]
bookcase[0].optimize = 2
lounge_chair_A[0].position = [1.5499999523162842, 1.7999999523162842, 0.39500001072883606]
lounge_chair_A[0].rotation = [0, 0, 0.01256637125682779]
lounge_chair_A[0].optimize = 2
lounge_chair_B[0].position = [3.3080520629882812, 1.7999999523162842, 0.39500001072883606]
lounge_chair_B[0].rotation = [0, 0, -3.1290262823329655]
lounge_chair_B[0].optimize = 2
dining_table[0].position = [2.4000000953674316, 1.7999999523162842, 0.375]
dining_table[0].rotation = [0, 0, 0.03455751882667646]
dining_table[0].optimize = 2

