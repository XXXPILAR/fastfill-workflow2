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
    Wall(corner1=[11.29, 0.00, 0.00], corner2=[11.29, 3.29, 0.00]),
    Wall(corner1=[11.29, 3.29, 0.00], corner2=[6.50, 3.29, 0.00]),
    Wall(corner1=[6.50, 3.29, 0.00], corner2=[6.50, 2.79, 0.00]),
    Wall(corner1=[6.50, 2.79, 0.00], corner2=[3.79, 2.79, 0.00]),
    Wall(corner1=[3.79, 2.79, 0.00], corner2=[3.79, 6.79, 0.00]),
    Wall(corner1=[3.79, 6.79, 0.00], corner2=[0.00, 6.79, 0.00]),
    Wall(corner1=[0.00, 6.79, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[11.29, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
book_A = Assets(description="book", size=[0.16, 0.22, 0.03], placements=[AssetInstance() for _ in range(1)])
bed_A = Assets(description="bed", size=[1.60, 2.05, 0.60], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.45, 0.60, 0.70], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="shelf", size=[0.30, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
tv = Assets(description="tv", size=[0.08, 1.23, 0.72], placements=[AssetInstance() for _ in range(1)])
desk = Assets(description="desk", size=[0.65, 1.40, 0.75], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.45, 0.60, 0.70], placements=[AssetInstance() for _ in range(1)])
carpet_A = Assets(description="carpet", size=[1.70, 2.40, 0.02], placements=[AssetInstance() for _ in range(1)])
carpet_B = Assets(description="carpet", size=[1.40, 2.00, 0.02], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="book", size=[0.17, 0.24, 0.04], placements=[AssetInstance() for _ in range(1)])
book_C = Assets(description="book", size=[0.15, 0.21, 0.03], placements=[AssetInstance() for _ in range(1)])
vase = Assets(description="vase", size=[0.18, 0.18, 0.32], placements=[AssetInstance() for _ in range(1)])
book_D = Assets(description="book", size=[0.20, 0.28, 0.04], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="lamp", size=[0.30, 0.30, 0.55], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.30, 0.30, 0.55], placements=[AssetInstance() for _ in range(1)])
lamp_C = Assets(description="lamp", size=[0.22, 0.22, 0.42], placements=[AssetInstance() for _ in range(1)])
lamp_D = Assets(description="lamp", size=[0.20, 0.20, 0.38], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.28, 1.00, 1.60], placements=[AssetInstance() for _ in range(1)])
shelf_C = Assets(description="shelf", size=[0.30, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
lamp_E = Assets(description="lamp", size=[0.28, 0.28, 0.50], placements=[AssetInstance() for _ in range(1)])
bed_B = Assets(description="bed", size=[1.60, 2.05, 0.60], placements=[AssetInstance() for _ in range(1)])
lamp_F = Assets(description="lamp", size=[0.28, 0.28, 0.50], placements=[AssetInstance() for _ in range(1)])

book_A[0].instance_id = 'book_A_0'
bed_A[0].instance_id = 'bed_A_0'
cabinet_A[0].instance_id = 'cabinet_A_0'
shelf_A[0].instance_id = 'shelf_A_0'
tv[0].instance_id = 'tv_0'
desk[0].instance_id = 'desk_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
carpet_A[0].instance_id = 'carpet_A_0'
carpet_B[0].instance_id = 'carpet_B_0'
book_B[0].instance_id = 'book_B_0'
book_C[0].instance_id = 'book_C_0'
vase[0].instance_id = 'vase_0'
book_D[0].instance_id = 'book_D_0'
lamp_A[0].instance_id = 'lamp_A_0'
lamp_B[0].instance_id = 'lamp_B_0'
lamp_C[0].instance_id = 'lamp_C_0'
lamp_D[0].instance_id = 'lamp_D_0'
shelf_B[0].instance_id = 'shelf_B_0'
shelf_C[0].instance_id = 'shelf_C_0'
lamp_E[0].instance_id = 'lamp_E_0'
bed_B[0].instance_id = 'bed_B_0'
lamp_F[0].instance_id = 'lamp_F_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

book_A[0].position = [1.6816319684841585, 4.913112607635805, 0.015]
book_A[0].rotation = [0, 0, 0]
bed_A[0].position = [3.444137181530959, 2.0338452988058364, 0.3]
bed_A[0].rotation = [0, 0, 0]
cabinet_A[0].position = [0.1792034541604389, 4.860214407426585, 0.35]
cabinet_A[0].rotation = [0, 0, 0]
shelf_A[0].position = [1.6073121331506737, 3.80422221819915, 0.9]
shelf_A[0].rotation = [0, 0, 0]
tv[0].position = [8.32211932848199, 2.8820620959854706, 0.36]
tv[0].rotation = [0, 0, 0]
desk[0].position = [10.355914297718643, 0.17639337066158675, 0.375]
desk[0].rotation = [0, 0, 0]
cabinet_B[0].position = [8.027818949283741, 1.844548028233073, 0.35]
cabinet_B[0].rotation = [0, 0, 0]
carpet_A[0].position = [1.9425867265425958, 4.668217833804375, 0.01]
carpet_A[0].rotation = [0, 0, 0]
carpet_B[0].position = [0.6310938509748941, 3.0771115210273052, 0.01]
carpet_B[0].rotation = [0, 0, 0]
book_B[0].position = [8.058073299052003, 1.6274115630298165, 0.0175]
book_B[0].rotation = [0, 0, 0]
book_C[0].position = [5.782445693629408, 1.9144264920402576, 0.0125]
book_C[0].rotation = [0, 0, 0]
vase[0].position = [2.639914259640813, 5.952133464407241, 0.16]
vase[0].rotation = [0, 0, 0]
book_D[0].position = [2.4855022814662426, 6.747704956109392, 0.02]
book_D[0].rotation = [0, 0, 0]
lamp_A[0].position = [10.709345148577325, 1.2702614997672872, 0.275]
lamp_A[0].rotation = [0, 0, 0]
lamp_B[0].position = [6.66343808049337, 1.071914230615197, 0.275]
lamp_B[0].rotation = [0, 0, 0]
lamp_C[0].position = [7.156188146736129, 0.5978502515271319, 0.21]
lamp_C[0].rotation = [0, 0, 0]
lamp_D[0].position = [9.539118047060368, 1.4322636135307174, 0.19]
lamp_D[0].rotation = [0, 0, 0]
shelf_B[0].position = [3.2363344936218756, 3.7443335527490844, 0.8]
shelf_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [3.2907822973401175, 5.154408058652867, 0.45]
shelf_C[0].rotation = [0, 0, 0]
lamp_E[0].position = [9.071103117882357, 3.107449563834717, 0.25]
lamp_E[0].rotation = [0, 0, 0]
bed_B[0].position = [0.5076537412199861, 2.61416158328292, 0.3]
bed_B[0].rotation = [0, 0, 0]
lamp_F[0].position = [5.058846114123757, 1.9818345062657345, 0.25]
lamp_F[0].rotation = [0, 0, 0]
book_A[0].position = [1.6816319684841585, 4.913112607635805, 0.015]
book_A[0].rotation = [0, 0, 0]
bed_A[0].position = [3.444137181530959, 2.0338452988058364, 0.3]
bed_A[0].rotation = [0, 0, 0]
cabinet_A[0].position = [0.1792034541604389, 4.860214407426585, 0.35]
cabinet_A[0].rotation = [0, 0, 0]
shelf_A[0].position = [1.6073121331506737, 3.80422221819915, 0.9]
shelf_A[0].rotation = [0, 0, 0]
tv[0].position = [8.32211932848199, 2.8820620959854706, 0.36]
tv[0].rotation = [0, 0, 0]
desk[0].position = [10.355914297718643, 0.17639337066158675, 0.375]
desk[0].rotation = [0, 0, 0]
cabinet_B[0].position = [8.027818949283741, 1.844548028233073, 0.35]
cabinet_B[0].rotation = [0, 0, 0]
carpet_A[0].position = [1.9425867265425958, 4.668217833804375, 0.01]
carpet_A[0].rotation = [0, 0, 0]
carpet_B[0].position = [0.6310938509748941, 3.0771115210273052, 0.01]
carpet_B[0].rotation = [0, 0, 0]
book_B[0].position = [8.058073299052003, 1.6274115630298165, 0.0175]
book_B[0].rotation = [0, 0, 0]
book_C[0].position = [5.782445693629408, 1.9144264920402576, 0.0125]
book_C[0].rotation = [0, 0, 0]
vase[0].position = [2.639914259640813, 5.952133464407241, 0.16]
vase[0].rotation = [0, 0, 0]
book_D[0].position = [2.4855022814662426, 6.747704956109392, 0.02]
book_D[0].rotation = [0, 0, 0]
lamp_A[0].position = [10.709345148577325, 1.2702614997672872, 0.275]
lamp_A[0].rotation = [0, 0, 0]
lamp_B[0].position = [6.66343808049337, 1.071914230615197, 0.275]
lamp_B[0].rotation = [0, 0, 0]
lamp_C[0].position = [7.156188146736129, 0.5978502515271319, 0.21]
lamp_C[0].rotation = [0, 0, 0]
lamp_D[0].position = [9.539118047060368, 1.4322636135307174, 0.19]
lamp_D[0].rotation = [0, 0, 0]
shelf_B[0].position = [3.2363344936218756, 3.7443335527490844, 0.8]
shelf_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [3.2907822973401175, 5.154408058652867, 0.45]
shelf_C[0].rotation = [0, 0, 0]
lamp_E[0].position = [9.071103117882357, 3.107449563834717, 0.25]
lamp_E[0].rotation = [0, 0, 0]
bed_B[0].position = [0.5076537412199861, 2.61416158328292, 0.3]
bed_B[0].rotation = [0, 0, 0]
lamp_F[0].position = [5.058846114123757, 1.9818345062657345, 0.25]
lamp_F[0].rotation = [0, 0, 0]

solver.constraints = []

# The room naturally divides into a larger sleeping area on the left and a
# lower rectangular work/lounge area on the right. Furniture is kept away
# from the door at (10.61, 3.29) and from the three windows.

# Fixed orientation references used only by orientation constraints.
east_facing = AssetInstance(rotation=[0, 0, radians(0)])
north_facing = AssetInstance(rotation=[0, 0, radians(90)])
west_facing = AssetInstance(rotation=[0, 0, radians(180)])
south_facing = AssetInstance(rotation=[0, 0, radians(-90)])

# ---------------------------------------------------------------------------
# Initial placements
# ---------------------------------------------------------------------------

# Two beds occupy the wider upper-left portion of the room. Their perpendicular
# arrangement leaves a central aisle and avoids the windows on the bottom wall.
bed_A[0].position = [2.65, 5.99, 0.30]
bed_A[0].rotation = [0, 0, radians(-90)]

bed_B[0].position = [0.80, 4.85, 0.30]
bed_B[0].rotation = [0, 0, radians(0)]

# o0018 corresponds to shelf_C in the supplied ordering. Place it physically
# between cabinet_A (o0002) and cabinet_B (o0006) along the west wall.
cabinet_A[0].position = [0.225, 0.65, 0.35]
cabinet_A[0].rotation = [0, 0, radians(0)]

shelf_C[0].position = [0.15, 1.65, 0.45]
shelf_C[0].rotation = [0, 0, radians(0)]

cabinet_B[0].position = [0.225, 2.65, 0.35]
cabinet_B[0].rotation = [0, 0, radians(0)]

# A tall shelf sits on the unobstructed portion of the south wall, clear of
# the window centered at x=1.08.
shelf_A[0].position = [2.80, 0.15, 0.90]
shelf_A[0].rotation = [0, 0, radians(90)]

# The desk and second tall shelf use the north wall of the right-hand area.
# Both stop well before the door opening centered at x=10.61.
desk[0].position = [7.40, 2.965, 0.375]
desk[0].rotation = [0, 0, radians(-90)]

shelf_B[0].position = [9.00, 3.15, 0.80]
shelf_B[0].rotation = [0, 0, radians(-90)]

# The TV is supported by the low shelf between the two cabinets.
tv[0].position = [0.15, 1.65, 1.26]
tv[0].rotation = [0, 0, radians(0)]

# Rugs define open usable areas without blocking the entrance or overlapping
# the beds and wall furniture.
carpet_A[0].position = [8.10, 1.35, 0.01]
carpet_A[0].rotation = [0, 0, radians(90)]

carpet_B[0].position = [5.45, 1.35, 0.01]
carpet_B[0].rotation = [0, 0, radians(0)]

# Bedside lamps are centered on their respective cabinets.
lamp_A[0].position = [0.225, 0.65, 0.975]
lamp_A[0].rotation = [0, 0, radians(0)]

lamp_B[0].position = [0.225, 2.65, 0.975]
lamp_B[0].rotation = [0, 0, radians(0)]

# Four books and a compact task lamp are distributed across the desk top.
book_A[0].position = [6.85, 2.88, 0.765]
book_A[0].rotation = [0, 0, radians(-90)]

book_B[0].position = [7.10, 2.88, 0.77]
book_B[0].rotation = [0, 0, radians(-90)]

book_C[0].position = [7.34, 2.88, 0.765]
book_C[0].rotation = [0, 0, radians(-90)]

book_D[0].position = [7.60, 2.88, 0.77]
book_D[0].rotation = [0, 0, radians(-90)]

lamp_C[0].position = [7.91, 2.91, 0.96]
lamp_C[0].rotation = [0, 0, radians(-90)]

# Decorative objects are spaced across shelf_B's top surface.
lamp_D[0].position = [8.64, 3.15, 1.79]
lamp_D[0].rotation = [0, 0, radians(-90)]

vase[0].position = [8.99, 3.15, 1.76]
vase[0].rotation = [0, 0, radians(-90)]

lamp_F[0].position = [9.35, 3.15, 1.85]
lamp_F[0].rotation = [0, 0, radians(-90)]

# The remaining lamp decorates shelf_A.
lamp_E[0].position = [2.80, 0.15, 2.05]
lamp_E[0].rotation = [0, 0, radians(90)]

# ---------------------------------------------------------------------------
# Position constraints for floor-standing furniture
# ---------------------------------------------------------------------------

# Exact-distance anchors preserve the intended zones if the layout is solved.
solver.distance_constraint(
    bed_A[0], AssetInstance(position=[2.65, 5.99, 0.30]), 0, 0, weight=10
)
solver.against_wall(bed_A[0], walls[5])

solver.distance_constraint(
    bed_B[0], AssetInstance(position=[0.80, 4.85, 0.30]), 0, 0, weight=10
)
solver.against_wall(bed_B[0], walls[6])

solver.distance_constraint(
    cabinet_A[0], AssetInstance(position=[0.225, 0.65, 0.35]), 0, 0, weight=10
)
solver.against_wall(cabinet_A[0], walls[6])

solver.distance_constraint(
    shelf_C[0], AssetInstance(position=[0.15, 1.65, 0.45]), 0, 0, weight=10
)
solver.against_wall(shelf_C[0], walls[6])

solver.distance_constraint(
    cabinet_B[0], AssetInstance(position=[0.225, 2.65, 0.35]), 0, 0, weight=10
)
solver.against_wall(cabinet_B[0], walls[6])

# These two bounds reinforce the required cabinet–shelf–cabinet sequence.
solver.distance_constraint(shelf_C[0], cabinet_A[0], 0.95, 1.05, weight=10)
solver.distance_constraint(shelf_C[0], cabinet_B[0], 0.95, 1.05, weight=10)

solver.distance_constraint(
    shelf_A[0], AssetInstance(position=[2.80, 0.15, 0.90]), 0, 0, weight=10
)
solver.against_wall(shelf_A[0], walls[7])

solver.distance_constraint(
    desk[0], AssetInstance(position=[7.40, 2.965, 0.375]), 0, 0, weight=10
)
solver.against_wall(desk[0], walls[1])

solver.distance_constraint(
    shelf_B[0], AssetInstance(position=[9.00, 3.15, 0.80]), 0, 0, weight=10
)
solver.against_wall(shelf_B[0], walls[1])

solver.distance_constraint(
    carpet_A[0], AssetInstance(position=[8.10, 1.35, 0.01]), 0, 0, weight=10
)
solver.distance_constraint(
    carpet_B[0], AssetInstance(position=[5.45, 1.35, 0.01]), 0, 0, weight=10
)

# ---------------------------------------------------------------------------
# Support and position constraints for tabletop/shelf-top objects
# ---------------------------------------------------------------------------

solver.on_top_of(tv[0], shelf_C[0])
solver.distance_constraint(
    tv[0], AssetInstance(position=[0.15, 1.65, 1.26]), 0, 0, weight=10
)

solver.on_top_of(lamp_A[0], cabinet_A[0])
solver.distance_constraint(
    lamp_A[0], AssetInstance(position=[0.225, 0.65, 0.975]), 0, 0, weight=10
)

solver.on_top_of(lamp_B[0], cabinet_B[0])
solver.distance_constraint(
    lamp_B[0], AssetInstance(position=[0.225, 2.65, 0.975]), 0, 0, weight=10
)

solver.on_top_of(book_A[0], desk[0])
solver.distance_constraint(
    book_A[0], AssetInstance(position=[6.85, 2.88, 0.765]), 0, 0, weight=10
)

solver.on_top_of(book_B[0], desk[0])
solver.distance_constraint(
    book_B[0], AssetInstance(position=[7.10, 2.88, 0.77]), 0, 0, weight=10
)

solver.on_top_of(book_C[0], desk[0])
solver.distance_constraint(
    book_C[0], AssetInstance(position=[7.34, 2.88, 0.765]), 0, 0, weight=10
)

solver.on_top_of(book_D[0], desk[0])
solver.distance_constraint(
    book_D[0], AssetInstance(position=[7.60, 2.88, 0.77]), 0, 0, weight=10
)

solver.on_top_of(lamp_C[0], desk[0])
solver.distance_constraint(
    lamp_C[0], AssetInstance(position=[7.91, 2.91, 0.96]), 0, 0, weight=10
)

solver.on_top_of(lamp_D[0], shelf_B[0])
solver.distance_constraint(
    lamp_D[0], AssetInstance(position=[8.64, 3.15, 1.79]), 0, 0, weight=10
)

solver.on_top_of(vase[0], shelf_B[0])
solver.distance_constraint(
    vase[0], AssetInstance(position=[8.99, 3.15, 1.76]), 0, 0, weight=10
)

solver.on_top_of(lamp_F[0], shelf_B[0])
solver.distance_constraint(
    lamp_F[0], AssetInstance(position=[9.35, 3.15, 1.85]), 0, 0, weight=10
)

solver.on_top_of(lamp_E[0], shelf_A[0])
solver.distance_constraint(
    lamp_E[0], AssetInstance(position=[2.80, 0.15, 2.05]), 0, 0, weight=10
)

# ---------------------------------------------------------------------------
# Orientation constraints for every new asset instance
# ---------------------------------------------------------------------------

solver.align_with(bed_A[0], south_facing)
solver.align_with(bed_B[0], east_facing)

solver.align_with(cabinet_A[0], east_facing)
solver.align_with(shelf_C[0], east_facing)
solver.align_with(cabinet_B[0], east_facing)

solver.align_with(shelf_A[0], north_facing)
solver.align_with(desk[0], south_facing)
solver.align_with(shelf_B[0], south_facing)

solver.align_with(carpet_A[0], north_facing)
solver.align_with(carpet_B[0], east_facing)

solver.align_with(tv[0], shelf_C[0])
solver.align_with(lamp_A[0], cabinet_A[0])
solver.align_with(lamp_B[0], cabinet_B[0])

solver.align_with(book_A[0], desk[0])
solver.align_with(book_B[0], desk[0])
solver.align_with(book_C[0], desk[0])
solver.align_with(book_D[0], desk[0])
solver.align_with(lamp_C[0], desk[0])

solver.align_with(lamp_D[0], shelf_B[0])
solver.align_with(vase[0], shelf_B[0])
solver.align_with(lamp_F[0], shelf_B[0])
solver.align_with(lamp_E[0], shelf_A[0])

solver.constraints = []
bed_B[0].position = [0.800000011920929, 4.849999904632568, 0.30000001192092896]
bed_B[0].rotation = [0, 0, 3.124863431953012e-08]
bed_B[0].optimize = 2
book_D[0].position = [6.570579528808594, 2.796743869781494, 0.7699999809265137]
book_D[0].rotation = [0, 0, -1.5668264598417618]
book_D[0].optimize = 2
lamp_D[0].position = [8.640000343322754, 3.1500000953674316, 1.7899999618530273]
lamp_D[0].rotation = [0, 0, -1.5707962942230238]
lamp_D[0].optimize = 2
desk[0].position = [5.871852874755859, 2.469015121459961, 0.375]
desk[0].rotation = [0, 0, -1.566894490382818]
desk[0].optimize = 2
book_C[0].position = [6.570579528808594, 2.796743869781494, 0.7649999856948853]
book_C[0].rotation = [0, 0, -1.5668264598417618]
book_C[0].optimize = 2
lamp_A[0].position = [0.22499999403953552, 0.6499999761581421, 0.9750000238418579]
lamp_A[0].rotation = [0, 0, 4.1527800940821374e-08]
lamp_A[0].optimize = 2
book_A[0].position = [6.570579528808594, 2.796743869781494, 0.7649999856948853]
book_A[0].rotation = [0, 0, -1.5668264598417618]
book_A[0].optimize = 2
lamp_B[0].position = [0.22499999403953552, 2.6500000953674316, 0.9750000238418579]
lamp_B[0].rotation = [0, 0, -1.570808132487185]
lamp_B[0].optimize = 2
book_B[0].position = [6.570579528808594, 2.796743869781494, 0.7699999809265137]
book_B[0].rotation = [0, 0, -1.5668264598417618]
book_B[0].optimize = 2
cabinet_B[0].position = [0.30222904682159424, 2.6500000953674316, 0.3499999940395355]
cabinet_B[0].rotation = [0, 0, -1.570808093953536]
cabinet_B[0].optimize = 2
carpet_A[0].position = [8.100000381469727, 1.350000023841858, 0.009999999776482582]
carpet_A[0].rotation = [0, 0, 1.5802211042556205]
carpet_A[0].optimize = 2
lamp_E[0].position = [2.799999952316284, 0.15000000596046448, 2.049999952316284]
lamp_E[0].rotation = [0, 0, 1.570796361846135]
lamp_E[0].optimize = 2
bed_A[0].position = [2.6500000953674316, 5.993978023529053, 0.30000001192092896]
bed_A[0].rotation = [0, 0, -1.5707962647037916]
bed_A[0].optimize = 2
vase[0].position = [8.989999771118164, 3.1500000953674316, 1.7599999904632568]
vase[0].rotation = [0, 0, -1.5707962942230238]
vase[0].optimize = 2
tv[0].position = [0.15000000596046448, 1.649999976158142, 1.2599999904632568]
tv[0].rotation = [0, 0, 4.3587160691938266e-08]
tv[0].optimize = 2
shelf_A[0].position = [2.799999952316284, 0.15000000596046448, 0.8999999761581421]
shelf_A[0].rotation = [0, 0, 1.5707963659822521]
shelf_A[0].optimize = 2
carpet_B[0].position = [5.449999809265137, 1.350000023841858, 0.009999999776482582]
carpet_B[0].rotation = [0, 0, 0.00942477746072377]
carpet_B[0].optimize = 2
cabinet_A[0].position = [0.22500000894069672, 0.6499999761581421, 0.3499999940395355]
cabinet_A[0].rotation = [0, 0, 4.245346495491605e-08]
cabinet_A[0].optimize = 2
lamp_C[0].position = [6.570579528808594, 2.796743869781494, 0.9599999785423279]
lamp_C[0].rotation = [0, 0, -1.5668264598417618]
lamp_C[0].optimize = 2
lamp_F[0].position = [9.350000381469727, 3.1500000953674316, 1.850000023841858]
lamp_F[0].rotation = [0, 0, -1.5707962942230238]
lamp_F[0].optimize = 2
shelf_C[0].position = [0.15000000596046448, 1.649999976158142, 0.44999998807907104]
shelf_C[0].rotation = [0, 0, 3.9212206974928576e-08]
shelf_C[0].optimize = 2
shelf_B[0].position = [9.0, 3.153978109359741, 0.800000011920929]
shelf_B[0].rotation = [0, 0, -1.570796300478304]
shelf_B[0].optimize = 2

