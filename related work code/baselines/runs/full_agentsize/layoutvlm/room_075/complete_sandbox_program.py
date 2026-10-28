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
    Wall(corner1=[3.43, 0.00, 0.00], corner2=[6.26, 0.00, 0.00]),
    Wall(corner1=[6.26, 0.00, 0.00], corner2=[6.26, 6.26, 0.00]),
    Wall(corner1=[6.26, 6.26, 0.00], corner2=[0.00, 6.26, 0.00]),
    Wall(corner1=[0.00, 6.26, 0.00], corner2=[0.00, 3.43, 0.00]),
    Wall(corner1=[0.00, 3.43, 0.00], corner2=[3.43, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
cabinet_A = Assets(description="cabinet", size=[0.45, 0.60, 0.65], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="lamp", size=[0.30, 0.30, 0.55], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="book", size=[0.24, 0.16, 0.04], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="shelf", size=[0.30, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
bed_A = Assets(description="bed", size=[2.10, 1.60, 0.60], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.30, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[2.20, 3.00, 0.02], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="book", size=[0.24, 0.16, 0.04], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.30, 0.30, 0.55], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.45, 0.60, 0.65], placements=[AssetInstance() for _ in range(1)])
bed_B = Assets(description="bed", size=[2.10, 1.60, 0.60], placements=[AssetInstance() for _ in range(1)])

cabinet_A[0].instance_id = 'cabinet_A_0'
lamp_A[0].instance_id = 'lamp_A_0'
book_A[0].instance_id = 'book_A_0'
shelf_A[0].instance_id = 'shelf_A_0'
bed_A[0].instance_id = 'bed_A_0'
shelf_B[0].instance_id = 'shelf_B_0'
carpet[0].instance_id = 'carpet_0'
book_B[0].instance_id = 'book_B_0'
lamp_B[0].instance_id = 'lamp_B_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
bed_B[0].instance_id = 'bed_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'

cabinet_A[0].position = [6.050251837538608, 6.1715527301656605, 0.325]
cabinet_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [4.965322254626665, 6.093670030204538, 0.275]
lamp_A[0].rotation = [0, 0, 0]
book_A[0].position = [5.695413617766672, 4.316661034218517, 0.02]
book_A[0].rotation = [0, 0, 0]
shelf_A[0].position = [4.1532608878374635, 4.092881861559831, 0.9]
shelf_A[0].rotation = [0, 0, 0]
bed_A[0].position = [3.6981439090351356, 4.62335566286864, 0.3]
bed_A[0].rotation = [0, 0, 0]
shelf_B[0].position = [4.645151399074496, 4.367463539024733, 0.9]
shelf_B[0].rotation = [0, 0, 0]
carpet[0].position = [1.4344984756343389, 4.424534557373755, 0.01]
carpet[0].rotation = [0, 0, 0]
book_B[0].position = [4.464357056980536, 5.887720166923912, 0.02]
book_B[0].rotation = [0, 0, 0]
lamp_B[0].position = [4.7915941649602605, 0.7839349882335487, 0.275]
lamp_B[0].rotation = [0, 0, 0]
cabinet_B[0].position = [5.799841613132699, 5.879954742189224, 0.325]
cabinet_B[0].rotation = [0, 0, 0]
bed_B[0].position = [1.1302799525377558, 4.5699090710299615, 0.3]
bed_B[0].rotation = [0, 0, 0]
cabinet_A[0].position = [6.050251837538608, 6.1715527301656605, 0.325]
cabinet_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [4.965322254626665, 6.093670030204538, 0.275]
lamp_A[0].rotation = [0, 0, 0]
book_A[0].position = [5.695413617766672, 4.316661034218517, 0.02]
book_A[0].rotation = [0, 0, 0]
shelf_A[0].position = [4.1532608878374635, 4.092881861559831, 0.9]
shelf_A[0].rotation = [0, 0, 0]
bed_A[0].position = [3.6981439090351356, 4.62335566286864, 0.3]
bed_A[0].rotation = [0, 0, 0]
shelf_B[0].position = [4.645151399074496, 4.367463539024733, 0.9]
shelf_B[0].rotation = [0, 0, 0]
carpet[0].position = [1.4344984756343389, 4.424534557373755, 0.01]
carpet[0].rotation = [0, 0, 0]
book_B[0].position = [4.464357056980536, 5.887720166923912, 0.02]
book_B[0].rotation = [0, 0, 0]
lamp_B[0].position = [4.7915941649602605, 0.7839349882335487, 0.275]
lamp_B[0].rotation = [0, 0, 0]
cabinet_B[0].position = [5.799841613132699, 5.879954742189224, 0.325]
cabinet_B[0].rotation = [0, 0, 0]
bed_B[0].position = [1.1302799525377558, 4.5699090710299615, 0.3]
bed_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange two beds along the unobstructed north wall. Their heads are against
# the wall and they face south into the room.
bed_A[0].position = [1.25, 5.21, 0.30]
bed_A[0].rotation = [0, 0, radians(-90)]

bed_B[0].position = [4.95, 5.21, 0.30]
bed_B[0].rotation = [0, 0, radians(-90)]

# Place one bedside cabinet on the inner side of each bed. Rotating the
# cabinets makes their 0.45 m dimension perpendicular to the north wall.
cabinet_A[0].position = [2.375, 6.035, 0.325]
cabinet_A[0].rotation = [0, 0, radians(-90)]

cabinet_B[0].position = [3.625, 6.035, 0.325]
cabinet_B[0].rotation = [0, 0, radians(-90)]

# Put a lamp and book on each cabinet. The lateral offsets keep each lamp
# separate from its neighboring book while remaining within the cabinet top.
lamp_A[0].position = [2.23, 6.035, 0.925]
lamp_A[0].rotation = [0, 0, radians(-90)]

book_A[0].position = [2.55, 6.035, 0.67]
book_A[0].rotation = [0, 0, radians(-90)]

book_B[0].position = [3.45, 6.035, 0.67]
book_B[0].rotation = [0, 0, radians(-90)]

lamp_B[0].position = [3.77, 6.035, 0.925]
lamp_B[0].rotation = [0, 0, radians(-90)]

# The left shelf occupies the short section above the west-wall window.
# A small unavoidable edge overlap with the window span is minimized.
shelf_A[0].position = [0.15, 5.66, 0.90]
shelf_A[0].rotation = [0, 0, 0]

# The right shelf is north of the door and leaves the entire doorway and its
# approach clear. It faces inward, toward the center of the room.
shelf_B[0].position = [6.11, 3.55, 0.90]
shelf_B[0].rotation = [0, 0, radians(180)]

# Center the carpet in the open lower area. Its placement stays above the
# diagonal boundary and leaves a clear circulation route from the east door.
carpet[0].position = [3.80, 2.35, 0.01]
carpet[0].rotation = [0, 0, 0]


# Beds: preserve contact with the north wall, anchor their separate positions,
# and make them face directly south.
solver.against_wall(bed_A[0], walls[2])
solver.distance_constraint(
    bed_A[0], AssetInstance(position=[1.25, 5.21, 0.30]),
    0, 0, weight=10
)
solver.point_towards(
    bed_A[0], AssetInstance(position=[1.25, 4.21, 0.30])
)

solver.against_wall(bed_B[0], walls[2])
solver.distance_constraint(
    bed_B[0], AssetInstance(position=[4.95, 5.21, 0.30]),
    0, 0, weight=10
)
solver.point_towards(
    bed_B[0], AssetInstance(position=[4.95, 4.21, 0.30])
)

# Cabinets: keep them against the same wall, beside rather than overlapping
# the beds, and orient their fronts toward the room.
solver.against_wall(cabinet_A[0], walls[2])
solver.distance_constraint(
    cabinet_A[0], AssetInstance(position=[2.375, 6.035, 0.325]),
    0, 0, weight=10
)
solver.point_towards(
    cabinet_A[0], AssetInstance(position=[2.375, 5.035, 0.325])
)

solver.against_wall(cabinet_B[0], walls[2])
solver.distance_constraint(
    cabinet_B[0], AssetInstance(position=[3.625, 6.035, 0.325]),
    0, 0, weight=10
)
solver.point_towards(
    cabinet_B[0], AssetInstance(position=[3.625, 5.035, 0.325])
)

# Small objects must remain supported by their respective cabinets. Exact
# position anchors preserve the non-overlapping offsets on each cabinet top.
solver.on_top_of(lamp_A[0], cabinet_A[0])
solver.distance_constraint(
    lamp_A[0], AssetInstance(position=[2.23, 6.035, 0.925]),
    0, 0, weight=10
)
solver.align_with(lamp_A[0], cabinet_A[0])

solver.on_top_of(book_A[0], cabinet_A[0])
solver.distance_constraint(
    book_A[0], AssetInstance(position=[2.55, 6.035, 0.67]),
    0, 0, weight=10
)
solver.align_with(book_A[0], cabinet_A[0])

solver.on_top_of(book_B[0], cabinet_B[0])
solver.distance_constraint(
    book_B[0], AssetInstance(position=[3.45, 6.035, 0.67]),
    0, 0, weight=10
)
solver.align_with(book_B[0], cabinet_B[0])

solver.on_top_of(lamp_B[0], cabinet_B[0])
solver.distance_constraint(
    lamp_B[0], AssetInstance(position=[3.77, 6.035, 0.925]),
    0, 0, weight=10
)
solver.align_with(lamp_B[0], cabinet_B[0])

# Shelves: constrain each to its selected wall and orient it into the room.
solver.against_wall(shelf_A[0], walls[3])
solver.distance_constraint(
    shelf_A[0], AssetInstance(position=[0.15, 5.66, 0.90]),
    0, 0, weight=10
)
solver.point_towards(
    shelf_A[0], AssetInstance(position=[1.15, 5.66, 0.90])
)

solver.against_wall(shelf_B[0], walls[1])
solver.distance_constraint(
    shelf_B[0], AssetInstance(position=[6.11, 3.55, 0.90]),
    0, 0, weight=10
)
solver.point_towards(
    shelf_B[0], AssetInstance(position=[5.11, 3.55, 0.90])
)

# Anchor and orient the carpet independently in the open floor area.
solver.distance_constraint(
    carpet[0], AssetInstance(position=[3.80, 2.35, 0.01]),
    0, 0, weight=10
)
solver.point_towards(
    carpet[0], AssetInstance(position=[4.80, 2.35, 0.01])
)

solver.constraints = []
carpet[0].position = [3.799999952316284, 2.3499999046325684, 0.009999999776482582]
carpet[0].rotation = [0, 0, 0.00942477746072377]
carpet[0].optimize = 2
bed_B[0].position = [4.949999809265137, 5.214914321899414, 0.30000001192092896]
bed_B[0].rotation = [0, 0, -1.570817440138601]
bed_B[0].optimize = 2
shelf_A[0].position = [0.15096522867679596, 5.615488052368164, 0.8999999761581421]
shelf_A[0].rotation = [0, 0, 0.0015234895851079719]
shelf_A[0].optimize = 2
lamp_A[0].position = [2.2300000190734863, 6.034999847412109, 0.9249999523162842]
lamp_A[0].rotation = [0, 0, -1.5707983137119272]
lamp_A[0].optimize = 2
book_A[0].position = [2.549999952316284, 6.034999847412109, 0.6699999570846558]
book_A[0].rotation = [0, 0, -1.5707983137119272]
book_A[0].optimize = 2
lamp_B[0].position = [3.7699999809265137, 6.034999847412109, 0.9249999523162842]
lamp_B[0].rotation = [0, 0, -1.5707983137119272]
lamp_B[0].optimize = 2
cabinet_A[0].position = [2.375, 6.039919853210449, 0.32499998807907104]
cabinet_A[0].rotation = [0, 0, -1.570824883780916]
cabinet_A[0].optimize = 2
book_B[0].position = [3.450000047683716, 6.034999847412109, 0.6699999570846558]
book_B[0].rotation = [0, 0, -1.5707983137119272]
book_B[0].optimize = 2
cabinet_B[0].position = [3.625, 6.039919853210449, 0.32499998807907104]
cabinet_B[0].rotation = [0, 0, -1.570824883780916]
cabinet_B[0].optimize = 2
bed_A[0].position = [1.25, 5.214914321899414, 0.30000001192092896]
bed_A[0].rotation = [0, 0, -1.570817440138601]
bed_A[0].optimize = 2
shelf_B[0].position = [6.114912033081055, 3.549999952316284, 0.8999999761581421]
shelf_B[0].rotation = [0, 0, 3.141570850687227]
shelf_B[0].optimize = 2

