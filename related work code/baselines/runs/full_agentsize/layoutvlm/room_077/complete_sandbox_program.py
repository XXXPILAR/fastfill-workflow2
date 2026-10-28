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
    Wall(corner1=[0.00, 3.38, 0.00], corner2=[0.12, 2.50, 0.00]),
    Wall(corner1=[0.12, 2.50, 0.00], corner2=[0.45, 1.69, 0.00]),
    Wall(corner1=[0.45, 1.69, 0.00], corner2=[0.72, 1.34, 0.00]),
    Wall(corner1=[0.72, 1.34, 0.00], corner2=[0.99, 0.99, 0.00]),
    Wall(corner1=[0.99, 0.99, 0.00], corner2=[1.69, 0.45, 0.00]),
    Wall(corner1=[1.69, 0.45, 0.00], corner2=[2.50, 0.12, 0.00]),
    Wall(corner1=[2.50, 0.12, 0.00], corner2=[3.38, 0.00, 0.00]),
    Wall(corner1=[3.38, 0.00, 0.00], corner2=[9.74, 0.00, 0.00]),
    Wall(corner1=[9.74, 0.00, 0.00], corner2=[9.74, 4.74, 0.00]),
    Wall(corner1=[9.74, 4.74, 0.00], corner2=[3.74, 4.74, 0.00]),
    Wall(corner1=[3.74, 4.74, 0.00], corner2=[3.74, 6.24, 0.00]),
    Wall(corner1=[3.74, 6.24, 0.00], corner2=[0.00, 6.24, 0.00]),
    Wall(corner1=[0.00, 6.24, 0.00], corner2=[0.00, 3.38, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
shelf_A = Assets(description="shelf", size=[0.30, 0.80, 1.80], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.35, 1.40, 1.80], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="book", size=[0.04, 0.16, 0.24], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[2.20, 3.00, 0.02], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="book", size=[0.05, 0.18, 0.26], placements=[AssetInstance() for _ in range(1)])
shelf_C = Assets(description="shelf", size=[0.30, 1.00, 1.60], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="lamp", size=[0.28, 0.28, 0.48], placements=[AssetInstance() for _ in range(1)])
shelf_D = Assets(description="shelf", size=[0.30, 0.80, 1.80], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="table", size=[0.60, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.24, 0.24, 0.42], placements=[AssetInstance() for _ in range(1)])
lamp_C = Assets(description="lamp", size=[0.22, 0.22, 0.40], placements=[AssetInstance() for _ in range(1)])
book_C = Assets(description="book", size=[0.04, 0.15, 0.23], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.00, 1.80, 0.55], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="cabinet", size=[0.45, 1.00, 0.85], placements=[AssetInstance() for _ in range(1)])
lamp_D = Assets(description="lamp", size=[0.22, 0.22, 0.40], placements=[AssetInstance() for _ in range(1)])
book_D = Assets(description="book", size=[0.05, 0.20, 0.28], placements=[AssetInstance() for _ in range(1)])

shelf_A[0].instance_id = 'shelf_A_0'
shelf_B[0].instance_id = 'shelf_B_0'
book_A[0].instance_id = 'book_A_0'
carpet[0].instance_id = 'carpet_0'
book_B[0].instance_id = 'book_B_0'
shelf_C[0].instance_id = 'shelf_C_0'
lamp_A[0].instance_id = 'lamp_A_0'
shelf_D[0].instance_id = 'shelf_D_0'
table[0].instance_id = 'table_0'
lamp_B[0].instance_id = 'lamp_B_0'
lamp_C[0].instance_id = 'lamp_C_0'
book_C[0].instance_id = 'book_C_0'
bed[0].instance_id = 'bed_0'
cabinet[0].instance_id = 'cabinet_0'
lamp_D[0].instance_id = 'lamp_D_0'
book_D[0].instance_id = 'book_D_0'
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

shelf_A[0].position = [8.393146390000167, 2.6945660059462786, 0.9]
shelf_A[0].rotation = [0, 0, 0]
shelf_B[0].position = [3.673622085947664, 1.18133183182688, 0.9]
shelf_B[0].rotation = [0, 0, 0]
book_A[0].position = [9.040622664034888, 0.03202461157840542, 0.12]
book_A[0].rotation = [0, 0, 0]
carpet[0].position = [3.803172443516495, 1.4423370186085005, 0.01]
carpet[0].rotation = [0, 0, 0]
book_B[0].position = [7.556339470923971, 0.2904847973188561, 0.13]
book_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [2.2973036249930865, 5.5173096489240985, 0.8]
shelf_C[0].rotation = [0, 0, 0]
lamp_A[0].position = [0.8447672586171023, 4.467231781102846, 0.24]
lamp_A[0].rotation = [0, 0, 0]
shelf_D[0].position = [3.09517379583831, 5.124638883999538, 0.9]
shelf_D[0].rotation = [0, 0, 0]
table[0].position = [9.735782953006916, 1.7659147341923607, 0.375]
table[0].rotation = [0, 0, 0]
lamp_B[0].position = [8.203217991676233, 2.458018447073821, 0.21]
lamp_B[0].rotation = [0, 0, 0]
lamp_C[0].position = [7.042955293349634, 0.41108844132136363, 0.2]
lamp_C[0].rotation = [0, 0, 0]
book_C[0].position = [4.45068564150156, 0.7414380503132648, 0.115]
book_C[0].rotation = [0, 0, 0]
bed[0].position = [1.6162906098955916, 5.520469980825532, 0.275]
bed[0].rotation = [0, 0, 0]
cabinet[0].position = [6.29320910303114, 4.244358693060548, 0.425]
cabinet[0].rotation = [0, 0, 0]
lamp_D[0].position = [2.6496966187660975, 4.976304069841754, 0.2]
lamp_D[0].rotation = [0, 0, 0]
book_D[0].position = [7.743471392109583, 2.4149811117583866, 0.14]
book_D[0].rotation = [0, 0, 0]
shelf_A[0].position = [8.393146390000167, 2.6945660059462786, 0.9]
shelf_A[0].rotation = [0, 0, 0]
shelf_B[0].position = [3.673622085947664, 1.18133183182688, 0.9]
shelf_B[0].rotation = [0, 0, 0]
book_A[0].position = [9.040622664034888, 0.03202461157840542, 0.12]
book_A[0].rotation = [0, 0, 0]
carpet[0].position = [3.803172443516495, 1.4423370186085005, 0.01]
carpet[0].rotation = [0, 0, 0]
book_B[0].position = [7.556339470923971, 0.2904847973188561, 0.13]
book_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [2.2973036249930865, 5.5173096489240985, 0.8]
shelf_C[0].rotation = [0, 0, 0]
lamp_A[0].position = [0.8447672586171023, 4.467231781102846, 0.24]
lamp_A[0].rotation = [0, 0, 0]
shelf_D[0].position = [3.09517379583831, 5.124638883999538, 0.9]
shelf_D[0].rotation = [0, 0, 0]
table[0].position = [9.735782953006916, 1.7659147341923607, 0.375]
table[0].rotation = [0, 0, 0]
lamp_B[0].position = [8.203217991676233, 2.458018447073821, 0.21]
lamp_B[0].rotation = [0, 0, 0]
lamp_C[0].position = [7.042955293349634, 0.41108844132136363, 0.2]
lamp_C[0].rotation = [0, 0, 0]
book_C[0].position = [4.45068564150156, 0.7414380503132648, 0.115]
book_C[0].rotation = [0, 0, 0]
bed[0].position = [1.6162906098955916, 5.520469980825532, 0.275]
bed[0].rotation = [0, 0, 0]
cabinet[0].position = [6.29320910303114, 4.244358693060548, 0.425]
cabinet[0].rotation = [0, 0, 0]
lamp_D[0].position = [2.6496966187660975, 4.976304069841754, 0.2]
lamp_D[0].rotation = [0, 0, 0]
book_D[0].position = [7.743471392109583, 2.4149811117583866, 0.14]
book_D[0].rotation = [0, 0, 0]

solver.constraints = []

# The three shelves referenced by the criteria correspond to shelf_A (o0007),
# shelf_B (o0000), and shelf_C (o0001).  shelf_A and shelf_B are placed
# symmetrically along the north wall, so the bed lies between them.  shelf_C
# is on the east wall, directly in front of the bed and below the east window.

shelf_A[0].position = [4.55, 4.59, 0.90]
shelf_A[0].rotation = [0, 0, radians(-90)]

shelf_B[0].position = [7.65, 4.565, 0.90]
shelf_B[0].rotation = [0, 0, radians(-90)]

book_A[0].position = [8.50, 4.72, 1.92]
book_A[0].rotation = [0, 0, radians(-90)]

carpet[0].position = [6.10, 2.25, 0.01]
carpet[0].rotation = [0, 0, 0]

book_B[0].position = [4.55, 4.56, 1.93]
book_B[0].rotation = [0, 0, radians(-90)]

shelf_C[0].position = [9.59, 2.25, 0.80]
shelf_C[0].rotation = [0, 0, radians(180)]

lamp_A[0].position = [8.20, 0.78, 0.99]
lamp_A[0].rotation = [0, 0, 0]

shelf_D[0].position = [8.70, 4.59, 0.90]
shelf_D[0].rotation = [0, 0, radians(-90)]

table[0].position = [8.20, 1.05, 0.375]
table[0].rotation = [0, 0, 0]

lamp_B[0].position = [3.50, 5.45, 1.06]
lamp_B[0].rotation = [0, 0, radians(180)]

lamp_C[0].position = [9.52, 2.05, 1.80]
lamp_C[0].rotation = [0, 0, radians(180)]

book_C[0].position = [8.20, 1.43, 0.865]
book_C[0].rotation = [0, 0, 0]

# The bed faces +x toward shelf_C. Its center is the midpoint in x between
# shelf_A and shelf_B, while its carpet defines the sleeping area.
bed[0].position = [6.10, 2.25, 0.295]
bed[0].rotation = [0, 0, 0]

# The cabinet occupies the short wall of the upper alcove. This keeps the
# region below the door at (0.93, 6.24) unobstructed.
cabinet[0].position = [3.515, 5.45, 0.425]
cabinet[0].rotation = [0, 0, radians(180)]

lamp_D[0].position = [8.87, 4.54, 2.00]
lamp_D[0].rotation = [0, 0, radians(-90)]

book_D[0].position = [7.65, 4.55, 1.94]
book_D[0].rotation = [0, 0, radians(-90)]


# Fixed placement references retain the intended clearances when the solver
# adjusts the layout. Exact-distance constraints are also the required
# position-based constraints for assets placed on top of other assets.
shelf_A_position = AssetInstance(position=[4.55, 4.59, 0.90])
shelf_B_position = AssetInstance(position=[7.65, 4.565, 0.90])
book_A_position = AssetInstance(position=[8.50, 4.72, 1.92])
carpet_position = AssetInstance(position=[6.10, 2.25, 0.01])
book_B_position = AssetInstance(position=[4.55, 4.56, 1.93])
shelf_C_position = AssetInstance(position=[9.59, 2.25, 0.80])
lamp_A_position = AssetInstance(position=[8.20, 0.78, 0.99])
shelf_D_position = AssetInstance(position=[8.70, 4.59, 0.90])
table_position = AssetInstance(position=[8.20, 1.05, 0.375])
lamp_B_position = AssetInstance(position=[3.50, 5.45, 1.06])
lamp_C_position = AssetInstance(position=[9.52, 2.05, 1.80])
book_C_position = AssetInstance(position=[8.20, 1.43, 0.865])
bed_position = AssetInstance(position=[6.10, 2.25, 0.295])
cabinet_position = AssetInstance(position=[3.515, 5.45, 0.425])
lamp_D_position = AssetInstance(position=[8.87, 4.54, 2.00])
book_D_position = AssetInstance(position=[7.65, 4.55, 1.94])

room_center = AssetInstance(position=[6.10, 2.25, 0.90])
north_heading = AssetInstance(rotation=[0, 0, radians(-90)])
east_heading = AssetInstance(rotation=[0, 0, 0])
west_heading = AssetInstance(rotation=[0, 0, radians(180)])


# Primary semantic requirements are declared first.
solver.point_towards(bed[0], shelf_C[0])
solver.distance_constraint(
    bed[0], bed_position, min_distance=0, max_distance=0, weight=10
)

# Equal distance bands reinforce that the bed remains between the two shelves.
solver.distance_constraint(
    bed[0], shelf_A[0], min_distance=2.75, max_distance=2.90, weight=10
)
solver.distance_constraint(
    bed[0], shelf_B[0], min_distance=2.75, max_distance=2.90, weight=10
)

# book_A is the specified wall-backed book. It stands on shelf_D while its
# thin rear edge remains against the north wall.
solver.against_wall(book_A[0], walls[9])
solver.on_top_of(book_A[0], shelf_D[0])
solver.distance_constraint(
    book_A[0], book_A_position, min_distance=0, max_distance=0, weight=10
)
solver.align_with(book_A[0], shelf_D[0])


# North-wall shelves face into the room. The chosen section of wall has no
# window and leaves the upper-left door approach clear.
solver.against_wall(shelf_A[0], walls[9])
solver.distance_constraint(
    shelf_A[0], shelf_A_position, min_distance=0, max_distance=0, weight=10
)
solver.point_towards(shelf_A[0], room_center)

solver.against_wall(shelf_B[0], walls[9])
solver.distance_constraint(
    shelf_B[0], shelf_B_position, min_distance=0, max_distance=0, weight=10
)
solver.point_towards(shelf_B[0], room_center)

solver.against_wall(shelf_D[0], walls[9])
solver.distance_constraint(
    shelf_D[0], shelf_D_position, min_distance=0, max_distance=0, weight=10
)
solver.point_towards(shelf_D[0], room_center)

# shelf_C is below the right-wall window and faces the bed.
solver.against_wall(shelf_C[0], walls[8])
solver.distance_constraint(
    shelf_C[0], shelf_C_position, min_distance=0, max_distance=0, weight=10
)
solver.point_towards(shelf_C[0], bed[0])

# The carpet and bed form one aligned sleeping zone.
solver.distance_constraint(
    carpet[0], carpet_position, min_distance=0, max_distance=0, weight=10
)
solver.align_with(carpet[0], bed[0])
solver.on_top_of(bed[0], carpet[0])

# The table is in the southeast area, separated from the bed and shelf_C.
solver.distance_constraint(
    table[0], table_position, min_distance=0, max_distance=0, weight=10
)
solver.align_with(table[0], east_heading)
solver.distance_constraint(
    table[0], bed[0], min_distance=2.20, max_distance=2.45
)

# The cabinet uses the alcove's east wall, away from the doorway.
solver.against_wall(cabinet[0], walls[10])
solver.distance_constraint(
    cabinet[0], cabinet_position, min_distance=0, max_distance=0, weight=10
)
solver.point_towards(cabinet[0], room_center)


# Small objects are supported by furniture. Each also has an exact position
# constraint and an orientation constraint, as required.
solver.on_top_of(book_B[0], shelf_A[0])
solver.distance_constraint(
    book_B[0], book_B_position, min_distance=0, max_distance=0, weight=10
)
solver.align_with(book_B[0], shelf_A[0])

solver.on_top_of(book_C[0], table[0])
solver.distance_constraint(
    book_C[0], book_C_position, min_distance=0, max_distance=0, weight=10
)
solver.align_with(book_C[0], table[0])

solver.on_top_of(book_D[0], shelf_B[0])
solver.distance_constraint(
    book_D[0], book_D_position, min_distance=0, max_distance=0, weight=10
)
solver.align_with(book_D[0], shelf_B[0])

solver.on_top_of(lamp_A[0], table[0])
solver.distance_constraint(
    lamp_A[0], lamp_A_position, min_distance=0, max_distance=0, weight=10
)
solver.align_with(lamp_A[0], table[0])

solver.on_top_of(lamp_B[0], cabinet[0])
solver.distance_constraint(
    lamp_B[0], lamp_B_position, min_distance=0, max_distance=0, weight=10
)
solver.align_with(lamp_B[0], cabinet[0])

solver.on_top_of(lamp_C[0], shelf_C[0])
solver.distance_constraint(
    lamp_C[0], lamp_C_position, min_distance=0, max_distance=0, weight=10
)
solver.align_with(lamp_C[0], shelf_C[0])

solver.on_top_of(lamp_D[0], shelf_D[0])
solver.distance_constraint(
    lamp_D[0], lamp_D_position, min_distance=0, max_distance=0, weight=10
)
solver.align_with(lamp_D[0], shelf_D[0])

solver.constraints = []
carpet[0].position = [6.099999904632568, 2.25, 0.009999999776482582]
carpet[0].rotation = [0, 0, 0.022040183732228987]
carpet[0].optimize = 2
book_D[0].position = [7.650000095367432, 4.550000190734863, 1.9399999380111694]
book_D[0].rotation = [0, 0, -1.593563690200807]
book_D[0].optimize = 2
lamp_D[0].position = [8.869999885559082, 4.539999961853027, 2.0]
lamp_D[0].rotation = [0, 0, -1.596532278131522]
lamp_D[0].optimize = 2
book_C[0].position = [8.199999809265137, 1.4299999475479126, 0.8650000095367432]
book_C[0].rotation = [0, 0, 0.021852364228046945]
book_C[0].optimize = 2
shelf_D[0].position = [8.699999809265137, 4.5871453285217285, 0.8999999761581421]
shelf_D[0].rotation = [0, 0, -1.5716038274395645]
shelf_D[0].optimize = 2
lamp_A[0].position = [8.199999809265137, 0.7799999713897705, 0.9900000095367432]
lamp_A[0].rotation = [0, 0, 0.021852364228046945]
lamp_A[0].optimize = 2
book_A[0].position = [8.5, 4.716517448425293, 1.9199999570846558]
book_A[0].rotation = [0, 0, -1.5646564390278437]
book_A[0].optimize = 2
table[0].position = [8.199999809265137, 1.0499999523162842, 0.375]
table[0].rotation = [0, 0, 0.025132740109855806]
table[0].optimize = 2
lamp_B[0].position = [3.5, 5.449999809265137, 1.0600000619888306]
lamp_B[0].rotation = [0, 0, 3.1235548402590845]
lamp_B[0].optimize = 2
book_B[0].position = [4.550000190734863, 4.559999942779541, 1.9299999475479126]
book_B[0].rotation = [0, 0, -1.5935555067329235]
book_B[0].optimize = 2
bed[0].position = [6.099999904632568, 2.25, 0.29500001668930054]
bed[0].rotation = [0, 0, 0.02827433441159227]
bed[0].optimize = 2
cabinet[0].position = [3.5131311416625977, 5.449999809265137, 0.42500001192092896]
cabinet[0].rotation = [0, 0, -3.136295078360791]
cabinet[0].optimize = 2
shelf_A[0].position = [4.550000190734863, 4.589034557342529, 0.8999999761581421]
shelf_A[0].rotation = [0, 0, -1.5681446824237868]
shelf_A[0].optimize = 2
lamp_C[0].position = [9.520000457763672, 2.049999952316284, 1.8000000715255737]
lamp_C[0].rotation = [0, 0, 3.1188309258691707]
lamp_C[0].optimize = 2
shelf_C[0].position = [9.585615158081055, 2.25, 0.800000011920929]
shelf_C[0].rotation = [0, 0, -3.138943037358757]
shelf_C[0].optimize = 2
shelf_B[0].position = [7.650000095367432, 4.555816650390625, 0.8999999761581421]
shelf_B[0].rotation = [0, 0, -1.5681526896110034]
shelf_B[0].optimize = 2

