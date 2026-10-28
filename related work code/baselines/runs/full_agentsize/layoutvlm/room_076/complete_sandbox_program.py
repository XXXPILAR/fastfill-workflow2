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
    Wall(corner1=[5.72, 0.00, 0.00], corner2=[5.72, 6.72, 0.00]),
    Wall(corner1=[5.72, 6.72, 0.00], corner2=[0.00, 6.72, 0.00]),
    Wall(corner1=[0.00, 6.72, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[5.72, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
book_A = Assets(description="book", size=[0.24, 0.16, 0.03], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="book", size=[0.22, 0.15, 0.03], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="shelf", size=[0.28, 1.20, 0.04], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="lamp", size=[0.28, 0.28, 0.52], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.10, 1.80, 0.65], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.30, 0.30, 0.55], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="table", size=[0.65, 1.40, 0.76], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.45, 0.65, 0.70], placements=[AssetInstance() for _ in range(1)])
lamp_C = Assets(description="lamp", size=[0.25, 0.25, 0.45], placements=[AssetInstance() for _ in range(1)])
book_C = Assets(description="book", size=[0.25, 0.18, 0.04], placements=[AssetInstance() for _ in range(1)])
lamp_D = Assets(description="lamp", size=[0.25, 0.25, 0.45], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.25, 1.00, 0.04], placements=[AssetInstance() for _ in range(1)])
vase = Assets(description="vase", size=[0.18, 0.18, 0.32], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[3.20, 2.40, 0.01], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.48, 1.20, 0.85], placements=[AssetInstance() for _ in range(1)])
lamp_E = Assets(description="lamp", size=[0.28, 0.28, 0.50], placements=[AssetInstance() for _ in range(1)])
lamp_F = Assets(description="lamp", size=[0.30, 0.30, 0.55], placements=[AssetInstance() for _ in range(1)])
cabinet_C = Assets(description="cabinet", size=[0.45, 0.65, 0.70], placements=[AssetInstance() for _ in range(1)])

book_A[0].instance_id = 'book_A_0'
book_B[0].instance_id = 'book_B_0'
shelf_A[0].instance_id = 'shelf_A_0'
lamp_A[0].instance_id = 'lamp_A_0'
bed[0].instance_id = 'bed_0'
lamp_B[0].instance_id = 'lamp_B_0'
table[0].instance_id = 'table_0'
cabinet_A[0].instance_id = 'cabinet_A_0'
lamp_C[0].instance_id = 'lamp_C_0'
book_C[0].instance_id = 'book_C_0'
lamp_D[0].instance_id = 'lamp_D_0'
shelf_B[0].instance_id = 'shelf_B_0'
vase[0].instance_id = 'vase_0'
carpet[0].instance_id = 'carpet_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
lamp_E[0].instance_id = 'lamp_E_0'
lamp_F[0].instance_id = 'lamp_F_0'
cabinet_C[0].instance_id = 'cabinet_C_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

book_A[0].position = [2.193189160633158, 0.36658198804493886, 0.015]
book_A[0].rotation = [0, 0, 0]
book_B[0].position = [0.010900031393098666, 3.833263392167256, 0.015]
book_B[0].rotation = [0, 0, 0]
shelf_A[0].position = [2.1119733059411283, 6.639660464902894, 0.02]
shelf_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [1.2651505069982345, 3.6743981060937942, 0.26]
lamp_A[0].rotation = [0, 0, 0]
bed[0].position = [1.0199777753973123, 0.7489888937506533, 0.325]
bed[0].rotation = [0, 0, 0]
lamp_B[0].position = [2.5727946609476766, 5.062228261956366, 0.275]
lamp_B[0].rotation = [0, 0, 0]
table[0].position = [1.7743079806558284, 5.404351325397705, 0.38]
table[0].rotation = [0, 0, 0]
cabinet_A[0].position = [1.268028755453413, 5.261665063167832, 0.35]
cabinet_A[0].rotation = [0, 0, 0]
lamp_C[0].position = [3.5952834671538807, 3.305863856413813, 0.225]
lamp_C[0].rotation = [0, 0, 0]
book_C[0].position = [4.1602842404700375, 3.24062982580191, 0.0175]
book_C[0].rotation = [0, 0, 0]
lamp_D[0].position = [4.535468286862968, 5.889966291004138, 0.225]
lamp_D[0].rotation = [0, 0, 0]
shelf_B[0].position = [1.6224355053474022, 1.5417122519670297, 0.02]
shelf_B[0].rotation = [0, 0, 0]
vase[0].position = [1.0396287170132104, 3.034805244873552, 0.16]
vase[0].rotation = [0, 0, 0]
carpet[0].position = [4.285561924055855, 4.638866583663959, 0.0075]
carpet[0].rotation = [0, 0, 0]
cabinet_B[0].position = [0.39404492543728104, 1.1389150330713231, 0.425]
cabinet_B[0].rotation = [0, 0, 0]
lamp_E[0].position = [4.4420899075164995, 4.91522608636834, 0.25]
lamp_E[0].rotation = [0, 0, 0]
lamp_F[0].position = [0.03322635138580429, 3.1085178687775543, 0.275]
lamp_F[0].rotation = [0, 0, 0]
cabinet_C[0].position = [0.47422844427293864, 0.23713576522275975, 0.35]
cabinet_C[0].rotation = [0, 0, 0]
book_A[0].position = [2.193189160633158, 0.36658198804493886, 0.015]
book_A[0].rotation = [0, 0, 0]
book_B[0].position = [0.010900031393098666, 3.833263392167256, 0.015]
book_B[0].rotation = [0, 0, 0]
shelf_A[0].position = [2.1119733059411283, 6.639660464902894, 0.02]
shelf_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [1.2651505069982345, 3.6743981060937942, 0.26]
lamp_A[0].rotation = [0, 0, 0]
bed[0].position = [1.0199777753973123, 0.7489888937506533, 0.325]
bed[0].rotation = [0, 0, 0]
lamp_B[0].position = [2.5727946609476766, 5.062228261956366, 0.275]
lamp_B[0].rotation = [0, 0, 0]
table[0].position = [1.7743079806558284, 5.404351325397705, 0.38]
table[0].rotation = [0, 0, 0]
cabinet_A[0].position = [1.268028755453413, 5.261665063167832, 0.35]
cabinet_A[0].rotation = [0, 0, 0]
lamp_C[0].position = [3.5952834671538807, 3.305863856413813, 0.225]
lamp_C[0].rotation = [0, 0, 0]
book_C[0].position = [4.1602842404700375, 3.24062982580191, 0.0175]
book_C[0].rotation = [0, 0, 0]
lamp_D[0].position = [4.535468286862968, 5.889966291004138, 0.225]
lamp_D[0].rotation = [0, 0, 0]
shelf_B[0].position = [1.6224355053474022, 1.5417122519670297, 0.02]
shelf_B[0].rotation = [0, 0, 0]
vase[0].position = [1.0396287170132104, 3.034805244873552, 0.16]
vase[0].rotation = [0, 0, 0]
carpet[0].position = [4.285561924055855, 4.638866583663959, 0.0075]
carpet[0].rotation = [0, 0, 0]
cabinet_B[0].position = [0.39404492543728104, 1.1389150330713231, 0.425]
cabinet_B[0].rotation = [0, 0, 0]
lamp_E[0].position = [4.4420899075164995, 4.91522608636834, 0.25]
lamp_E[0].rotation = [0, 0, 0]
lamp_F[0].position = [0.03322635138580429, 3.1085178687775543, 0.275]
lamp_F[0].rotation = [0, 0, 0]
cabinet_C[0].position = [0.47422844427293864, 0.23713576522275975, 0.35]
cabinet_C[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed orientation references used to preserve deliberate facing directions.
face_east = AssetInstance(rotation=[0, 0, radians(0)])
face_north = AssetInstance(rotation=[0, 0, radians(90)])
face_west = AssetInstance(rotation=[0, 0, radians(180)])
face_south = AssetInstance(rotation=[0, 0, radians(270)])

# The bed occupies the lower-right corner, leaving the door approach at
# (5.72, 5.12) unobstructed.
bed[0].position = [4.62, 1.35, 0.325]
bed[0].rotation = [0, 0, radians(180)]
bed_anchor = AssetInstance(position=[4.62, 1.35, 0.325])
solver.against_wall(bed[0], walls[0])
solver.distance_constraint(bed[0], bed_anchor, 0, 0, weight=10)
solver.align_with(bed[0], face_west)

# A central rug and table establish the main usable area without intruding
# into the bed footprint or the doorway circulation zone.
carpet[0].position = [1.90, 3.10, 0.005]
carpet[0].rotation = [0, 0, radians(0)]
carpet_anchor = AssetInstance(position=[1.90, 3.10, 0.005])
solver.distance_constraint(carpet[0], carpet_anchor, 0, 0, weight=10)
solver.align_with(carpet[0], face_east)

table[0].position = [1.90, 3.10, 0.39]
table[0].rotation = [0, 0, radians(0)]
table_anchor = AssetInstance(position=[1.90, 3.10, 0.39])
solver.on_top_of(table[0], carpet[0])
solver.distance_constraint(table[0], table_anchor, 0, 0, weight=10)
solver.align_with(table[0], carpet[0])

# The two thin shelves are placed at wall edges. Shelf A is beyond the upper
# end of the left-wall window; shelf B is a low-profile shelf at the top wall.
shelf_A[0].position = [0.14, 5.75, 0.02]
shelf_A[0].rotation = [0, 0, radians(0)]
shelf_A_anchor = AssetInstance(position=[0.14, 5.75, 0.02])
solver.against_wall(shelf_A[0], walls[2])
solver.distance_constraint(shelf_A[0], shelf_A_anchor, 0, 0, weight=10)
solver.align_with(shelf_A[0], face_east)

shelf_B[0].position = [1.90, 6.595, 0.02]
shelf_B[0].rotation = [0, 0, radians(90)]
shelf_B_anchor = AssetInstance(position=[1.90, 6.595, 0.02])
solver.against_wall(shelf_B[0], walls[1])
solver.distance_constraint(shelf_B[0], shelf_B_anchor, 0, 0, weight=10)
solver.align_with(shelf_B[0], face_north)

# Books A and B sit on their respective shelves.
book_A[0].position = [0.14, 5.75, 0.055]
book_A[0].rotation = [0, 0, radians(0)]
book_A_anchor = AssetInstance(position=[0.14, 5.75, 0.055])
solver.on_top_of(book_A[0], shelf_A[0])
solver.distance_constraint(book_A[0], book_A_anchor, 0, 0, weight=10)
solver.align_with(book_A[0], shelf_A[0])

book_B[0].position = [1.90, 6.595, 0.055]
book_B[0].rotation = [0, 0, radians(90)]
book_B_anchor = AssetInstance(position=[1.90, 6.595, 0.055])
solver.on_top_of(book_B[0], shelf_B[0])
solver.distance_constraint(book_B[0], book_B_anchor, 0, 0, weight=10)
solver.align_with(book_B[0], shelf_B[0])

# Two compact cabinets fit along the bottom wall on either side of the small
# bottom window, while staying clear of the bed.
cabinet_A[0].position = [2.45, 0.225, 0.35]
cabinet_A[0].rotation = [0, 0, radians(90)]
cabinet_A_anchor = AssetInstance(position=[2.45, 0.225, 0.35])
solver.against_wall(cabinet_A[0], walls[3])
solver.distance_constraint(cabinet_A[0], cabinet_A_anchor, 0, 0, weight=10)
solver.align_with(cabinet_A[0], face_north)

cabinet_C[0].position = [3.25, 0.225, 0.35]
cabinet_C[0].rotation = [0, 0, radians(90)]
cabinet_C_anchor = AssetInstance(position=[3.25, 0.225, 0.35])
solver.against_wall(cabinet_C[0], walls[3])
solver.distance_constraint(cabinet_C[0], cabinet_C_anchor, 0, 0, weight=10)
solver.align_with(cabinet_C[0], face_north)

# The tall cabinet uses the right wall below the door, preserving a clear
# approach to the doorway from the room center.
cabinet_B[0].position = [5.48, 3.20, 0.425]
cabinet_B[0].rotation = [0, 0, radians(180)]
cabinet_B_anchor = AssetInstance(position=[5.48, 3.20, 0.425])
solver.against_wall(cabinet_B[0], walls[0])
solver.distance_constraint(cabinet_B[0], cabinet_B_anchor, 0, 0, weight=10)
solver.align_with(cabinet_B[0], face_west)

# Lamps B, E, and F are supported by the three cabinets.
lamp_B[0].position = [2.45, 0.225, 0.975]
lamp_B[0].rotation = [0, 0, radians(90)]
lamp_B_anchor = AssetInstance(position=[2.45, 0.225, 0.975])
solver.on_top_of(lamp_B[0], cabinet_A[0])
solver.distance_constraint(lamp_B[0], lamp_B_anchor, 0, 0, weight=10)
solver.align_with(lamp_B[0], cabinet_A[0])

lamp_E[0].position = [3.25, 0.225, 0.95]
lamp_E[0].rotation = [0, 0, radians(90)]
lamp_E_anchor = AssetInstance(position=[3.25, 0.225, 0.95])
solver.on_top_of(lamp_E[0], cabinet_C[0])
solver.distance_constraint(lamp_E[0], lamp_E_anchor, 0, 0, weight=10)
solver.align_with(lamp_E[0], cabinet_C[0])

lamp_F[0].position = [5.48, 3.20, 1.125]
lamp_F[0].rotation = [0, 0, radians(180)]
lamp_F_anchor = AssetInstance(position=[5.48, 3.20, 1.125])
solver.on_top_of(lamp_F[0], cabinet_B[0])
solver.distance_constraint(lamp_F[0], lamp_F_anchor, 0, 0, weight=10)
solver.align_with(lamp_F[0], cabinet_B[0])

# Lamps C, A, and D form a straight row on the table. Lamp A (o0003) is
# exactly midway between lamp C (o0008) and lamp D (o0010).
lamp_C[0].position = [2.05, 2.66, 0.995]
lamp_C[0].rotation = [0, 0, radians(0)]
lamp_C_anchor = AssetInstance(position=[2.05, 2.66, 0.995])
solver.on_top_of(lamp_C[0], table[0])
solver.distance_constraint(lamp_C[0], lamp_C_anchor, 0, 0, weight=10)
solver.align_with(lamp_C[0], table[0])

lamp_A[0].position = [2.05, 3.10, 1.03]
lamp_A[0].rotation = [0, 0, radians(0)]
lamp_A_anchor = AssetInstance(position=[2.05, 3.10, 1.03])
solver.on_top_of(lamp_A[0], table[0])
solver.distance_constraint(lamp_A[0], lamp_A_anchor, 0, 0, weight=10)
solver.align_with(lamp_A[0], lamp_C[0])

lamp_D[0].position = [2.05, 3.54, 0.995]
lamp_D[0].rotation = [0, 0, radians(0)]
lamp_D_anchor = AssetInstance(position=[2.05, 3.54, 0.995])
solver.on_top_of(lamp_D[0], table[0])
solver.distance_constraint(lamp_D[0], lamp_D_anchor, 0, 0, weight=10)
solver.align_with(lamp_D[0], lamp_C[0])

# These relational distances preserve the required C-A-D ordering even if
# the table group must be adjusted for physical feasibility.
solver.distance_constraint(lamp_A[0], lamp_C[0], 0.44, 0.44, weight=10)
solver.distance_constraint(lamp_A[0], lamp_D[0], 0.44, 0.44, weight=10)
solver.distance_constraint(lamp_D[0], lamp_C[0], 0.88, 0.88, weight=10)

# The remaining book and vase occupy the free side of the tabletop, separated
# laterally from the three lamps.
book_C[0].position = [1.70, 3.50, 0.79]
book_C[0].rotation = [0, 0, radians(90)]
book_C_anchor = AssetInstance(position=[1.70, 3.50, 0.79])
solver.on_top_of(book_C[0], table[0])
solver.distance_constraint(book_C[0], book_C_anchor, 0, 0, weight=10)
solver.align_with(book_C[0], face_north)

vase[0].position = [1.70, 2.70, 0.93]
vase[0].rotation = [0, 0, radians(0)]
vase_anchor = AssetInstance(position=[1.70, 2.70, 0.93])
solver.on_top_of(vase[0], table[0])
solver.distance_constraint(vase[0], vase_anchor, 0, 0, weight=10)
solver.align_with(vase[0], table[0])

solver.constraints = []
carpet[0].position = [1.899999976158142, 3.0999999046325684, 0.004999999888241291]
carpet[0].rotation = [0, 0, 0.0157079639172164]
carpet[0].optimize = 2
lamp_D[0].position = [2.049999952316284, 3.5399999618530273, 0.9950000047683716]
lamp_D[0].rotation = [0, 0, 0.01570808616214074]
lamp_D[0].optimize = 2
book_C[0].position = [1.7000000476837158, 3.5, 0.7899999618530273]
book_C[0].rotation = [0, 0, 1.5833626980517244]
book_C[0].optimize = 2
table[0].position = [1.899999976158142, 3.0999999046325684, 0.38999998569488525]
table[0].rotation = [0, 0, 0.015707975442133575]
table[0].optimize = 2
lamp_A[0].position = [2.049999952316284, 3.099377155303955, 1.0299999713897705]
lamp_A[0].rotation = [0, 0, 0.01570808616214074]
lamp_A[0].optimize = 2
book_A[0].position = [0.14000000059604645, 5.75, 0.054999999701976776]
book_A[0].rotation = [0, 0, 1.0613328338897031e-07]
book_A[0].optimize = 2
lamp_B[0].position = [2.450000047683716, 0.22499999403953552, 0.9750000238418579]
lamp_B[0].rotation = [0, 0, 1.5707964359987714]
lamp_B[0].optimize = 2
book_B[0].position = [1.8861724138259888, 6.589555263519287, 0.054999999701976776]
book_B[0].rotation = [0, 0, -1.568915628819359]
book_B[0].optimize = 2
bed[0].position = [4.6742844581604, 1.350000023841858, 0.32499998807907104]
bed[0].rotation = [0, 0, -3.1415925981152686]
bed[0].optimize = 2
lamp_E[0].position = [3.25, 0.22499999403953552, 0.949999988079071]
lamp_E[0].rotation = [0, 0, 1.5707964359987714]
lamp_E[0].optimize = 2
cabinet_B[0].position = [5.484283924102783, 3.200000047683716, 0.42500001192092896]
cabinet_B[0].rotation = [0, 0, -3.1415926345494496]
cabinet_B[0].optimize = 2
vase[0].position = [1.7000000476837158, 2.700000047683716, 0.9299999475479126]
vase[0].rotation = [0, 0, 0.015707908236022375]
vase[0].optimize = 2
shelf_A[0].position = [0.14000000059604645, 5.75, 0.019999999552965164]
shelf_A[0].rotation = [0, 0, 4.35532783582195e-08]
shelf_A[0].optimize = 2
cabinet_A[0].position = [2.450000047683716, 0.22500000894069672, 0.3499999940395355]
cabinet_A[0].rotation = [0, 0, 1.5707963736599486]
cabinet_A[0].optimize = 2
lamp_C[0].position = [2.049999952316284, 2.6600000858306885, 0.9950000047683716]
lamp_C[0].rotation = [0, 0, 0.015707926922711554]
lamp_C[0].optimize = 2
lamp_F[0].position = [5.480000019073486, 3.200000047683716, 1.125]
lamp_F[0].rotation = [0, 0, -3.1415925532838593]
lamp_F[0].optimize = 2
cabinet_C[0].position = [3.25, 0.22500000894069672, 0.3499999940395355]
cabinet_C[0].rotation = [0, 0, 1.5707963736599486]
cabinet_C[0].optimize = 2
shelf_B[0].position = [1.899999976158142, 6.5996012687683105, 0.019999999552965164]
shelf_B[0].rotation = [0, 0, -1.568978982721266]
shelf_B[0].optimize = 2

