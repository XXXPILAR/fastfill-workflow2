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
    Wall(corner1=[2.00, 4.50, 0.00], corner2=[2.00, 0.00, 0.00]),
    Wall(corner1=[2.00, 0.00, 0.00], corner2=[6.76, 0.00, 0.00]),
    Wall(corner1=[6.76, 0.00, 0.00], corner2=[6.76, 6.76, 0.00]),
    Wall(corner1=[6.76, 6.76, 0.00], corner2=[0.00, 6.76, 0.00]),
    Wall(corner1=[0.00, 6.76, 0.00], corner2=[0.00, 4.50, 0.00]),
    Wall(corner1=[0.00, 4.50, 0.00], corner2=[2.00, 4.50, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
carpet = Assets(description="carpet", size=[2.00, 3.00, 0.01], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="lamp", size=[0.28, 0.28, 0.48], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="book", size=[0.23, 0.16, 0.03], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.35, 0.35, 1.60], placements=[AssetInstance() for _ in range(1)])
desk = Assets(description="desk", size=[0.70, 1.40, 0.75], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="shelf", size=[0.35, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
bed_A = Assets(description="bed", size=[2.10, 1.60, 0.60], placements=[AssetInstance() for _ in range(1)])
lamp_C = Assets(description="lamp", size=[0.25, 0.25, 0.45], placements=[AssetInstance() for _ in range(1)])
table_A = Assets(description="table", size=[0.45, 0.55, 0.55], placements=[AssetInstance() for _ in range(1)])
lamp_D = Assets(description="lamp", size=[0.25, 0.25, 0.45], placements=[AssetInstance() for _ in range(1)])
tv = Assets(description="tv", size=[0.08, 1.10, 0.65], placements=[AssetInstance() for _ in range(1)])
lamp_E = Assets(description="lamp", size=[0.22, 0.22, 0.42], placements=[AssetInstance() for _ in range(1)])
lamp_F = Assets(description="lamp", size=[0.15, 0.25, 0.35], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.30, 0.80, 1.60], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="book", size=[0.22, 0.15, 0.03], placements=[AssetInstance() for _ in range(1)])
shelf_C = Assets(description="shelf", size=[0.40, 1.30, 0.65], placements=[AssetInstance() for _ in range(1)])
shelf_D = Assets(description="shelf", size=[0.35, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
book_C = Assets(description="book", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
table_B = Assets(description="table", size=[0.45, 0.55, 0.55], placements=[AssetInstance() for _ in range(1)])
book_D = Assets(description="book", size=[0.23, 0.16, 0.03], placements=[AssetInstance() for _ in range(1)])
book_E = Assets(description="book", size=[0.25, 0.18, 0.04], placements=[AssetInstance() for _ in range(1)])
bed_B = Assets(description="bed", size=[2.10, 1.60, 0.60], placements=[AssetInstance() for _ in range(1)])
shelf_E = Assets(description="shelf", size=[0.30, 0.75, 1.50], placements=[AssetInstance() for _ in range(1)])
book_F = Assets(description="book", size=[0.21, 0.15, 0.03], placements=[AssetInstance() for _ in range(1)])

carpet[0].instance_id = 'carpet_0'
lamp_A[0].instance_id = 'lamp_A_0'
book_A[0].instance_id = 'book_A_0'
lamp_B[0].instance_id = 'lamp_B_0'
desk[0].instance_id = 'desk_0'
shelf_A[0].instance_id = 'shelf_A_0'
bed_A[0].instance_id = 'bed_A_0'
lamp_C[0].instance_id = 'lamp_C_0'
table_A[0].instance_id = 'table_A_0'
lamp_D[0].instance_id = 'lamp_D_0'
tv[0].instance_id = 'tv_0'
lamp_E[0].instance_id = 'lamp_E_0'
lamp_F[0].instance_id = 'lamp_F_0'
shelf_B[0].instance_id = 'shelf_B_0'
book_B[0].instance_id = 'book_B_0'
shelf_C[0].instance_id = 'shelf_C_0'
shelf_D[0].instance_id = 'shelf_D_0'
book_C[0].instance_id = 'book_C_0'
table_B[0].instance_id = 'table_B_0'
book_D[0].instance_id = 'book_D_0'
book_E[0].instance_id = 'book_E_0'
bed_B[0].instance_id = 'bed_B_0'
shelf_E[0].instance_id = 'shelf_E_0'
book_F[0].instance_id = 'book_F_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

carpet[0].position = [4.930466556510828, 3.071593884000935, 0.005]
carpet[0].rotation = [0, 0, 0]
lamp_A[0].position = [4.544919801792745, 3.6521699390195286, 0.24]
lamp_A[0].rotation = [0, 0, 0]
book_A[0].position = [5.381176961935565, 0.2143761671177434, 0.015]
book_A[0].rotation = [0, 0, 0]
lamp_B[0].position = [2.017733386930327, 4.125135541997747, 0.8]
lamp_B[0].rotation = [0, 0, 0]
desk[0].position = [0.8844513717980943, 5.782089475796353, 0.375]
desk[0].rotation = [0, 0, 0]
shelf_A[0].position = [1.9265304194948922, 6.154410809287146, 0.9]
shelf_A[0].rotation = [0, 0, 0]
bed_A[0].position = [5.417905411141731, 6.021817934013072, 0.3]
bed_A[0].rotation = [0, 0, 0]
lamp_C[0].position = [6.620584242398566, 6.481893577796699, 0.225]
lamp_C[0].rotation = [0, 0, 0]
table_A[0].position = [3.1450138449993443, 0.5970669617581472, 0.275]
table_A[0].rotation = [0, 0, 0]
lamp_D[0].position = [2.1785798614072083, 6.311209055748089, 0.225]
lamp_D[0].rotation = [0, 0, 0]
tv[0].position = [3.5874261308237614, 0.4358365193068175, 0.325]
tv[0].rotation = [0, 0, 0]
lamp_E[0].position = [2.9715582142088306, 6.660291085682499, 0.21]
lamp_E[0].rotation = [0, 0, 0]
lamp_F[0].position = [4.284564568423678, 4.851381341063705, 0.175]
lamp_F[0].rotation = [0, 0, 0]
shelf_B[0].position = [2.770923060468426, 1.6745471211374041, 0.8]
shelf_B[0].rotation = [0, 0, 0]
book_B[0].position = [3.8787756500714585, 2.8050812472329993, 0.015]
book_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [6.275806477241413, 0.917422959968702, 0.325]
shelf_C[0].rotation = [0, 0, 0]
shelf_D[0].position = [5.707606980551731, 6.17230132704766, 0.9]
shelf_D[0].rotation = [0, 0, 0]
book_C[0].position = [0.9682521488706907, 5.328401644541787, 0.0175]
book_C[0].rotation = [0, 0, 0]
table_B[0].position = [5.60698919111348, 1.633068087452351, 0.275]
table_B[0].rotation = [0, 0, 0]
book_D[0].position = [1.8848693207097504, 5.268437282122046, 0.0125]
book_D[0].rotation = [0, 0, 0]
book_E[0].position = [5.88092746921858, 1.606330309117965, 0.02]
book_E[0].rotation = [0, 0, 0]
bed_B[0].position = [4.264446117232816, 3.567998358855434, 0.3]
bed_B[0].rotation = [0, 0, 0]
shelf_E[0].position = [5.098746256933105, 6.504556465426642, 0.75]
shelf_E[0].rotation = [0, 0, 0]
book_F[0].position = [2.2878612912852607, 3.5064398612249414, 0.015]
book_F[0].rotation = [0, 0, 0]
carpet[0].position = [4.930466556510828, 3.071593884000935, 0.005]
carpet[0].rotation = [0, 0, 0]
lamp_A[0].position = [4.544919801792745, 3.6521699390195286, 0.24]
lamp_A[0].rotation = [0, 0, 0]
book_A[0].position = [5.381176961935565, 0.2143761671177434, 0.015]
book_A[0].rotation = [0, 0, 0]
lamp_B[0].position = [2.017733386930327, 4.125135541997747, 0.8]
lamp_B[0].rotation = [0, 0, 0]
desk[0].position = [0.8844513717980943, 5.782089475796353, 0.375]
desk[0].rotation = [0, 0, 0]
shelf_A[0].position = [1.9265304194948922, 6.154410809287146, 0.9]
shelf_A[0].rotation = [0, 0, 0]
bed_A[0].position = [5.417905411141731, 6.021817934013072, 0.3]
bed_A[0].rotation = [0, 0, 0]
lamp_C[0].position = [6.620584242398566, 6.481893577796699, 0.225]
lamp_C[0].rotation = [0, 0, 0]
table_A[0].position = [3.1450138449993443, 0.5970669617581472, 0.275]
table_A[0].rotation = [0, 0, 0]
lamp_D[0].position = [2.1785798614072083, 6.311209055748089, 0.225]
lamp_D[0].rotation = [0, 0, 0]
tv[0].position = [3.5874261308237614, 0.4358365193068175, 0.325]
tv[0].rotation = [0, 0, 0]
lamp_E[0].position = [2.9715582142088306, 6.660291085682499, 0.21]
lamp_E[0].rotation = [0, 0, 0]
lamp_F[0].position = [4.284564568423678, 4.851381341063705, 0.175]
lamp_F[0].rotation = [0, 0, 0]
shelf_B[0].position = [2.770923060468426, 1.6745471211374041, 0.8]
shelf_B[0].rotation = [0, 0, 0]
book_B[0].position = [3.8787756500714585, 2.8050812472329993, 0.015]
book_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [6.275806477241413, 0.917422959968702, 0.325]
shelf_C[0].rotation = [0, 0, 0]
shelf_D[0].position = [5.707606980551731, 6.17230132704766, 0.9]
shelf_D[0].rotation = [0, 0, 0]
book_C[0].position = [0.9682521488706907, 5.328401644541787, 0.0175]
book_C[0].rotation = [0, 0, 0]
table_B[0].position = [5.60698919111348, 1.633068087452351, 0.275]
table_B[0].rotation = [0, 0, 0]
book_D[0].position = [1.8848693207097504, 5.268437282122046, 0.0125]
book_D[0].rotation = [0, 0, 0]
book_E[0].position = [5.88092746921858, 1.606330309117965, 0.02]
book_E[0].rotation = [0, 0, 0]
bed_B[0].position = [4.264446117232816, 3.567998358855434, 0.3]
bed_B[0].rotation = [0, 0, 0]
shelf_E[0].position = [5.098746256933105, 6.504556465426642, 0.75]
shelf_E[0].rotation = [0, 0, 0]
book_F[0].position = [2.2878612912852607, 3.5064398612249414, 0.015]
book_F[0].rotation = [0, 0, 0]

solver.constraints = []

# Orientation references used to keep rotations stable while the solver adjusts positions.
face_east = AssetInstance(rotation=[0, 0, radians(0)])
face_north = AssetInstance(rotation=[0, 0, radians(90)])
face_west = AssetInstance(rotation=[0, 0, radians(180)])
face_south = AssetInstance(rotation=[0, 0, radians(-90)])

# Fixed-position references provide every asset with an explicit position-based
# constraint. Their coordinates match the initial placements below.
position_anchors = {}


def pin_position(name, instance):
    solver.distance_constraint(
        instance,
        position_anchors[name],
        min_distance=0,
        max_distance=0,
        weight=10,
    )


# ---------------------------------------------------------------------------
# Initial placements
#
# Tall furniture is concentrated on solid wall sections, away from both
# windows. The northern doorway and its approach (around x=5.84) remain clear.
# ---------------------------------------------------------------------------

carpet[0].position = [4.65, 4.65, 0.005]
carpet[0].rotation = [0, 0, radians(90)]

# Small lamp on top of shelf_E.
lamp_A[0].position = [4.75, 6.61, 1.71]
lamp_A[0].rotation = [0, 0, radians(-90)]

# Book on top of shelf_A.
book_A[0].position = [2.75, 6.61, 1.815]
book_A[0].rotation = [0, 0, radians(-90)]

# o0003: floor lamp placed between o0005 (shelf_A) and o0016 (shelf_D).
lamp_B[0].position = [3.38, 6.57, 0.80]
lamp_B[0].rotation = [0, 0, radians(-90)]

# The desk occupies the east wall below the east window.
desk[0].position = [6.41, 1.10, 0.375]
desk[0].rotation = [0, 0, radians(180)]

# o0005
shelf_A[0].position = [2.75, 6.585, 0.90]
shelf_A[0].rotation = [0, 0, radians(-90)]

# Lower bed uses the solid west wall and stays clear of the south window.
bed_A[0].position = [2.80, 1.30, 0.30]
bed_A[0].rotation = [0, 0, radians(90)]

lamp_C[0].position = [4.05, 1.00, 0.775]
lamp_C[0].rotation = [0, 0, radians(0)]

table_A[0].position = [4.05, 1.00, 0.275]
table_A[0].rotation = [0, 0, radians(0)]

lamp_D[0].position = [2.50, 5.45, 0.775]
lamp_D[0].rotation = [0, 0, radians(0)]

# The television is supported by the low shelf_C.
tv[0].position = [2.20, 3.60, 0.975]
tv[0].rotation = [0, 0, radians(0)]

# Desk lamp, offset along the desktop so that a book can share the surface.
lamp_E[0].position = [6.41, 0.80, 0.96]
lamp_E[0].rotation = [0, 0, radians(180)]

# o0012: compact floor lamp against the lower west wall.
lamp_F[0].position = [2.075, 2.75, 0.175]
lamp_F[0].rotation = [0, 0, radians(0)]

# East-wall shelf is above the window and outside the doorway approach.
shelf_B[0].position = [6.61, 5.10, 0.80]
shelf_B[0].rotation = [0, 0, radians(180)]

book_B[0].position = [6.60, 5.10, 1.615]
book_B[0].rotation = [0, 0, radians(180)]

# Low media shelf on the solid lower portion of the west wall.
shelf_C[0].position = [2.20, 3.60, 0.325]
shelf_C[0].rotation = [0, 0, radians(0)]

# o0016
shelf_D[0].position = [4.00, 6.585, 0.90]
shelf_D[0].rotation = [0, 0, radians(-90)]

book_C[0].position = [4.00, 6.61, 1.82]
book_C[0].rotation = [0, 0, radians(-90)]

table_B[0].position = [2.50, 5.45, 0.275]
table_B[0].rotation = [0, 0, radians(0)]

# Book sharing shelf_E with lamp_A; their lateral offsets prevent overlap.
book_D[0].position = [5.12, 6.61, 1.515]
book_D[0].rotation = [0, 0, radians(-90)]

# Book placed toward the opposite end of the desk from lamp_E.
book_E[0].position = [6.41, 1.45, 0.77]
book_E[0].rotation = [0, 0, radians(180)]

# Upper bed occupies the left alcove, leaving the door side of the room open.
bed_B[0].position = [1.10, 5.96, 0.30]
bed_B[0].rotation = [0, 0, radians(0)]

# Northern shelf stops well before the door opening.
shelf_E[0].position = [4.95, 6.61, 0.75]
shelf_E[0].rotation = [0, 0, radians(-90)]

book_F[0].position = [1.10, 5.96, 0.615]
book_F[0].rotation = [0, 0, radians(0)]


# Create absolute position references after assigning all intended coordinates.
for anchor_name, placed_instance in [
    ("carpet", carpet[0]),
    ("lamp_A", lamp_A[0]),
    ("book_A", book_A[0]),
    ("lamp_B", lamp_B[0]),
    ("desk", desk[0]),
    ("shelf_A", shelf_A[0]),
    ("bed_A", bed_A[0]),
    ("lamp_C", lamp_C[0]),
    ("table_A", table_A[0]),
    ("lamp_D", lamp_D[0]),
    ("tv", tv[0]),
    ("lamp_E", lamp_E[0]),
    ("lamp_F", lamp_F[0]),
    ("shelf_B", shelf_B[0]),
    ("book_B", book_B[0]),
    ("shelf_C", shelf_C[0]),
    ("shelf_D", shelf_D[0]),
    ("book_C", book_C[0]),
    ("table_B", table_B[0]),
    ("book_D", book_D[0]),
    ("book_E", book_E[0]),
    ("bed_B", bed_B[0]),
    ("shelf_E", shelf_E[0]),
    ("book_F", book_F[0]),
]:
    position_anchors[anchor_name] = AssetInstance(
        position=list(placed_instance.position)
    )


# ---------------------------------------------------------------------------
# Wall and support constraints are specified first because they encode the
# most important physical relationships.
# ---------------------------------------------------------------------------

# Northern wall furniture, with the required floor lamp between the two shelves.
solver.against_wall(shelf_A[0], walls[3])
solver.against_wall(lamp_B[0], walls[3])
solver.against_wall(shelf_D[0], walls[3])
solver.against_wall(shelf_E[0], walls[3])
solver.against_wall(bed_B[0], walls[3])

# Solid east-wall sections; neither object blocks the east window.
solver.against_wall(desk[0], walls[2])
solver.against_wall(shelf_B[0], walls[2])

# Solid lower-west wall.
solver.against_wall(bed_A[0], walls[0])
solver.against_wall(shelf_C[0], walls[0])

# Explicit requirement: o0012 (lamp_F) is against a wall.
solver.against_wall(lamp_F[0], walls[0])

# Small objects must remain supported by their intended surfaces.
solver.on_top_of(lamp_A[0], shelf_E[0])
solver.on_top_of(book_A[0], shelf_A[0])
solver.on_top_of(lamp_C[0], table_A[0])
solver.on_top_of(lamp_D[0], table_B[0])
solver.on_top_of(tv[0], shelf_C[0])
solver.on_top_of(lamp_E[0], desk[0])
solver.on_top_of(book_B[0], shelf_B[0])
solver.on_top_of(book_C[0], shelf_D[0])
solver.on_top_of(book_D[0], shelf_E[0])
solver.on_top_of(book_E[0], desk[0])
solver.on_top_of(book_F[0], bed_B[0])


# Pin all assets to their collision-free initial positions. These also provide
# a position-based constraint for objects governed by an on-top-of constraint.
for anchor_name, placed_instance in [
    ("carpet", carpet[0]),
    ("lamp_A", lamp_A[0]),
    ("book_A", book_A[0]),
    ("lamp_B", lamp_B[0]),
    ("desk", desk[0]),
    ("shelf_A", shelf_A[0]),
    ("bed_A", bed_A[0]),
    ("lamp_C", lamp_C[0]),
    ("table_A", table_A[0]),
    ("lamp_D", lamp_D[0]),
    ("tv", tv[0]),
    ("lamp_E", lamp_E[0]),
    ("lamp_F", lamp_F[0]),
    ("shelf_B", shelf_B[0]),
    ("book_B", book_B[0]),
    ("shelf_C", shelf_C[0]),
    ("shelf_D", shelf_D[0]),
    ("book_C", book_C[0]),
    ("table_B", table_B[0]),
    ("book_D", book_D[0]),
    ("book_E", book_E[0]),
    ("bed_B", bed_B[0]),
    ("shelf_E", shelf_E[0]),
    ("book_F", book_F[0]),
]:
    pin_position(anchor_name, placed_instance)


# Keep o0003 close to both bounding shelves, preserving its "between" relation
# if the wall grouping is adjusted.
solver.distance_constraint(
    lamp_B[0], shelf_A[0], min_distance=0.55, max_distance=0.70, weight=10
)
solver.distance_constraint(
    lamp_B[0], shelf_D[0], min_distance=0.55, max_distance=0.70, weight=10
)


# ---------------------------------------------------------------------------
# Orientation constraints for every asset
# ---------------------------------------------------------------------------

solver.align_with(carpet[0], face_north)

solver.align_with(lamp_A[0], shelf_E[0])
solver.align_with(book_A[0], shelf_A[0])
solver.align_with(lamp_B[0], face_south)

# Required semantic relation: the desk faces o0012 (lamp_F).
solver.point_towards(desk[0], lamp_F[0])
solver.point_towards(lamp_F[0], desk[0])

solver.align_with(shelf_A[0], face_south)
solver.align_with(bed_A[0], face_north)

solver.align_with(lamp_C[0], table_A[0])
solver.align_with(table_A[0], face_east)

solver.align_with(lamp_D[0], table_B[0])
solver.align_with(table_B[0], face_east)

solver.align_with(tv[0], shelf_C[0])
solver.align_with(lamp_E[0], desk[0])

solver.align_with(shelf_B[0], face_west)
solver.align_with(book_B[0], shelf_B[0])

solver.align_with(shelf_C[0], face_east)
solver.align_with(shelf_D[0], face_south)
solver.align_with(book_C[0], shelf_D[0])

solver.align_with(book_D[0], shelf_E[0])
solver.align_with(book_E[0], desk[0])

solver.align_with(bed_B[0], face_east)
solver.align_with(shelf_E[0], face_south)
solver.align_with(book_F[0], bed_B[0])

solver.constraints = []
carpet[0].position = [4.650000095367432, 4.650000095367432, 0.004999999888241291]
carpet[0].rotation = [0, 0, 1.5802211042556205]
carpet[0].optimize = 2
bed_B[0].position = [1.3518785238265991, 5.657272815704346, 0.30000001192092896]
bed_B[0].rotation = [0, 0, -1.4991983119864978]
bed_B[0].optimize = 2
book_D[0].position = [5.119999885559082, 6.610000133514404, 1.5149999856948853]
book_D[0].rotation = [0, 0, -1.5712079506717695]
book_D[0].optimize = 2
book_E[0].position = [6.409999847412109, 1.4500000476837158, 0.7699999809265137]
book_E[0].rotation = [0, 0, 3.1413753745923105]
book_E[0].optimize = 2
lamp_D[0].position = [2.5, 5.449999809265137, 0.7749999761581421]
lamp_D[0].rotation = [0, 0, 0.015670612819753637]
lamp_D[0].optimize = 2
desk[0].position = [6.411902904510498, 1.100000023841858, 0.375]
desk[0].rotation = [0, 0, -3.141408372588544]
desk[0].optimize = 2
table_B[0].position = [2.5, 5.449999809265137, 0.2750000059604645]
table_B[0].rotation = [0, 0, 0.0157079639172164]
table_B[0].optimize = 2
book_C[0].position = [4.0, 6.610000133514404, 1.8199999332427979]
book_C[0].rotation = [0, 0, -1.5710354312362702]
book_C[0].optimize = 2
shelf_D[0].position = [4.0, 6.586847305297852, 0.8999999761581421]
shelf_D[0].rotation = [0, 0, -1.5708301177880313]
shelf_D[0].optimize = 2
lamp_B[0].position = [3.380000114440918, 6.586765289306641, 0.800000011920929]
lamp_B[0].rotation = [0, 0, -1.5707426928008537]
lamp_B[0].optimize = 2
book_A[0].position = [2.75, 6.610000133514404, 1.8149999380111694]
book_A[0].rotation = [0, 0, -1.5710354312362702]
book_A[0].optimize = 2
lamp_A[0].position = [4.75, 6.610000133514404, 1.7400000095367432]
lamp_A[0].rotation = [0, 0, -1.5712079506717695]
lamp_A[0].optimize = 2
book_B[0].position = [6.599999904632568, 5.099999904632568, 1.6150000095367432]
book_B[0].rotation = [0, 0, -3.141423813369277]
book_B[0].optimize = 2
lamp_E[0].position = [6.409999847412109, 0.800000011920929, 0.9599999785423279]
lamp_E[0].rotation = [0, 0, 3.1413753745923105]
lamp_E[0].optimize = 2
bed_A[0].position = [3.096222400665283, 1.3620857000350952, 0.30000001192092896]
bed_A[0].rotation = [0, 0, 0.06019116079643428]
bed_A[0].optimize = 2
tv[0].position = [2.200000047683716, 3.5999999046325684, 0.9749999642372131]
tv[0].rotation = [0, 0, 0.00016795177440386274]
tv[0].optimize = 2
table_A[0].position = [4.050000190734863, 1.0, 0.2750000059604645]
table_A[0].rotation = [0, 0, 0.0157079639172164]
table_A[0].optimize = 2
shelf_A[0].position = [2.75, 6.586847305297852, 0.8999999761581421]
shelf_A[0].rotation = [0, 0, -1.5708301177880313]
shelf_A[0].optimize = 2
book_F[0].position = [1.100000023841858, 5.960000038146973, 0.6150000095367432]
book_F[0].rotation = [0, 0, -1.4968416452543913]
book_F[0].optimize = 2
shelf_E[0].position = [4.949999809265137, 6.611875057220459, 0.75]
shelf_E[0].rotation = [0, 0, -1.5708699473196668]
shelf_E[0].optimize = 2
lamp_C[0].position = [4.050000190734863, 1.0, 0.7749999761581421]
lamp_C[0].rotation = [0, 0, 0.015670612819753637]
lamp_C[0].optimize = 2
lamp_F[0].position = [2.0750362873077393, 2.75, 0.17499999701976776]
lamp_F[0].rotation = [0, 0, 5.9988727908047245e-06]
lamp_F[0].optimize = 2
shelf_C[0].position = [2.199944257736206, 3.5999999046325684, 0.32499998807907104]
shelf_C[0].rotation = [0, 0, 5.334017929879028e-05]
shelf_C[0].optimize = 2
shelf_B[0].position = [6.611781120300293, 5.099999904632568, 0.800000011920929]
shelf_B[0].rotation = [0, 0, -3.1415399307783614]
shelf_B[0].optimize = 2

