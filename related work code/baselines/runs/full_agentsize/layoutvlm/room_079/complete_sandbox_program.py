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
    Wall(corner1=[6.27, 0.00, 0.00], corner2=[6.27, 5.34, 0.00]),
    Wall(corner1=[6.27, 5.34, 0.00], corner2=[2.84, 8.77, 0.00]),
    Wall(corner1=[2.84, 8.77, 0.00], corner2=[0.50, 8.77, 0.00]),
    Wall(corner1=[0.50, 8.77, 0.00], corner2=[0.50, 2.77, 0.00]),
    Wall(corner1=[0.50, 2.77, 0.00], corner2=[0.00, 2.77, 0.00]),
    Wall(corner1=[0.00, 2.77, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.27, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
shelf_A = Assets(description="shelf", size=[0.35, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
bed_A = Assets(description="bed", size=[2.10, 1.60, 0.55], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="lamp", size=[0.30, 0.30, 0.55], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.40, 0.55, 0.60], placements=[AssetInstance() for _ in range(1)])
shelf_C = Assets(description="shelf", size=[0.30, 1.00, 0.30], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.30, 0.30, 0.55], placements=[AssetInstance() for _ in range(1)])
shelf_D = Assets(description="shelf", size=[0.40, 0.60, 0.65], placements=[AssetInstance() for _ in range(1)])
lamp_C = Assets(description="lamp", size=[0.35, 0.35, 1.55], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="table", size=[0.60, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="book", size=[0.24, 0.16, 0.04], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[3.40, 2.40, 0.02], placements=[AssetInstance() for _ in range(1)])
tv = Assets(description="tv", size=[0.08, 1.23, 0.71], placements=[AssetInstance() for _ in range(1)])
lamp_D = Assets(description="lamp", size=[0.30, 0.30, 0.55], placements=[AssetInstance() for _ in range(1)])
bed_B = Assets(description="bed", size=[2.10, 1.60, 0.55], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="book", size=[0.26, 0.18, 0.04], placements=[AssetInstance() for _ in range(1)])
shelf_E = Assets(description="shelf", size=[0.40, 0.60, 0.65], placements=[AssetInstance() for _ in range(1)])

shelf_A[0].instance_id = 'shelf_A_0'
bed_A[0].instance_id = 'bed_A_0'
lamp_A[0].instance_id = 'lamp_A_0'
shelf_B[0].instance_id = 'shelf_B_0'
shelf_C[0].instance_id = 'shelf_C_0'
lamp_B[0].instance_id = 'lamp_B_0'
shelf_D[0].instance_id = 'shelf_D_0'
lamp_C[0].instance_id = 'lamp_C_0'
table[0].instance_id = 'table_0'
book_A[0].instance_id = 'book_A_0'
carpet[0].instance_id = 'carpet_0'
tv[0].instance_id = 'tv_0'
lamp_D[0].instance_id = 'lamp_D_0'
bed_B[0].instance_id = 'bed_B_0'
book_B[0].instance_id = 'book_B_0'
shelf_E[0].instance_id = 'shelf_E_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'

shelf_A[0].position = [4.732474369358098, 4.594674671739847, 0.9]
shelf_A[0].rotation = [0, 0, 0]
bed_A[0].position = [2.370920990099824, 3.3823369957239025, 0.275]
bed_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [1.557580905990193, 5.92718200234812, 0.275]
lamp_A[0].rotation = [0, 0, 0]
shelf_B[0].position = [4.865390394037622, 0.5932637380844358, 0.3]
shelf_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [5.4447994908009045, 3.065788663907625, 0.15]
shelf_C[0].rotation = [0, 0, 0]
lamp_B[0].position = [5.44595245608284, 3.177270894149408, 0.275]
lamp_B[0].rotation = [0, 0, 0]
shelf_D[0].position = [1.7818406143507026, 3.64176485219978, 0.325]
shelf_D[0].rotation = [0, 0, 0]
lamp_C[0].position = [1.8381425722844478, 6.223842743517844, 0.775]
lamp_C[0].rotation = [0, 0, 0]
table[0].position = [2.9284330473594364, 7.68787643290318, 0.375]
table[0].rotation = [0, 0, 0]
book_A[0].position = [1.893754111452743, 4.223994962918779, 0.02]
book_A[0].rotation = [0, 0, 0]
carpet[0].position = [3.497976836800952, 3.7027406034899464, 0.01]
carpet[0].rotation = [0, 0, 0]
tv[0].position = [2.564923896988465, 7.645674129001605, 0.355]
tv[0].rotation = [0, 0, 0]
lamp_D[0].position = [4.747842449669348, 6.368516758688392, 0.275]
lamp_D[0].rotation = [0, 0, 0]
bed_B[0].position = [5.502316830755722, 3.329742712112655, 0.275]
bed_B[0].rotation = [0, 0, 0]
book_B[0].position = [3.2091145247362935, 0.5773304832240298, 0.02]
book_B[0].rotation = [0, 0, 0]
shelf_E[0].position = [4.985906436344118, 5.442545224228439, 0.325]
shelf_E[0].rotation = [0, 0, 0]
shelf_A[0].position = [4.732474369358098, 4.594674671739847, 0.9]
shelf_A[0].rotation = [0, 0, 0]
bed_A[0].position = [2.370920990099824, 3.3823369957239025, 0.275]
bed_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [1.557580905990193, 5.92718200234812, 0.275]
lamp_A[0].rotation = [0, 0, 0]
shelf_B[0].position = [4.865390394037622, 0.5932637380844358, 0.3]
shelf_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [5.4447994908009045, 3.065788663907625, 0.15]
shelf_C[0].rotation = [0, 0, 0]
lamp_B[0].position = [5.44595245608284, 3.177270894149408, 0.275]
lamp_B[0].rotation = [0, 0, 0]
shelf_D[0].position = [1.7818406143507026, 3.64176485219978, 0.325]
shelf_D[0].rotation = [0, 0, 0]
lamp_C[0].position = [1.8381425722844478, 6.223842743517844, 0.775]
lamp_C[0].rotation = [0, 0, 0]
table[0].position = [2.9284330473594364, 7.68787643290318, 0.375]
table[0].rotation = [0, 0, 0]
book_A[0].position = [1.893754111452743, 4.223994962918779, 0.02]
book_A[0].rotation = [0, 0, 0]
carpet[0].position = [3.497976836800952, 3.7027406034899464, 0.01]
carpet[0].rotation = [0, 0, 0]
tv[0].position = [2.564923896988465, 7.645674129001605, 0.355]
tv[0].rotation = [0, 0, 0]
lamp_D[0].position = [4.747842449669348, 6.368516758688392, 0.275]
lamp_D[0].rotation = [0, 0, 0]
bed_B[0].position = [5.502316830755722, 3.329742712112655, 0.275]
bed_B[0].rotation = [0, 0, 0]
book_B[0].position = [3.2091145247362935, 0.5773304832240298, 0.02]
book_B[0].rotation = [0, 0, 0]
shelf_E[0].position = [4.985906436344118, 5.442545224228439, 0.325]
shelf_E[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed reference points preserve the intended zones while allowing the solver
# to make small feasibility adjustments. The west-side door at y=4.84 and the
# windowed walls are kept unobstructed.
bed_A_target = AssetInstance(position=[1.40, 1.05, 0.275])
bed_B_target = AssetInstance(position=[4.90, 1.05, 0.275])
shelf_B_target = AssetInstance(position=[2.60, 1.00, 0.30])
carpet_target = AssetInstance(position=[3.60, 4.15, 0.01])
shelf_A_target = AssetInstance(position=[0.675, 6.15, 0.90])
shelf_C_target = AssetInstance(position=[0.65, 7.60, 0.15])
shelf_D_target = AssetInstance(position=[2.25, 6.45, 0.325])
table_target = AssetInstance(position=[3.25, 6.45, 0.375])
shelf_E_target = AssetInstance(position=[4.25, 6.45, 0.325])
lamp_C_target = AssetInstance(position=[5.60, 5.15, 0.775])

# The beds run away from the south wall, leaving a broad central aisle and
# keeping the south window accessible between them.
bed_A[0].position = [1.40, 1.05, 0.275]
bed_A[0].rotation = [0, 0, radians(90)]
bed_B[0].position = [4.90, 1.05, 0.275]
bed_B[0].rotation = [0, 0, radians(90)]

solver.distance_constraint(bed_A[0], bed_A_target, 0, 0, weight=10)
solver.against_wall(bed_A[0], walls[6])
solver.point_towards(
    bed_A[0],
    AssetInstance(position=[1.40, 4.00, 0.275])
)

solver.distance_constraint(bed_B[0], bed_B_target, 0, 0, weight=10)
solver.against_wall(bed_B[0], walls[6])
solver.point_towards(
    bed_B[0],
    AssetInstance(position=[4.90, 4.00, 0.275])
)

# A low bedside shelf sits beside bed_A without narrowing the central aisle.
shelf_B[0].position = [2.60, 1.00, 0.30]
shelf_B[0].rotation = [0, 0, radians(180)]
solver.distance_constraint(shelf_B[0], shelf_B_target, 0, 0, weight=10)
solver.distance_constraint(shelf_B[0], bed_A[0], 1.20, 1.30)
solver.point_towards(shelf_B[0], bed_A[0])

# Place one small lamp securely on the bedside shelf.
lamp_A[0].position = [2.60, 1.00, 0.875]
lamp_A[0].rotation = [0, 0, radians(180)]
solver.on_top_of(lamp_A[0], shelf_B[0])
solver.distance_constraint(lamp_A[0], shelf_B[0], 0, 0, weight=10)
solver.align_with(lamp_A[0], shelf_B[0])

# The carpet defines a central shared area while starting well east of the
# door, preserving a clear entrance path from the west wall.
carpet[0].position = [3.60, 4.15, 0.01]
carpet[0].rotation = [0, 0, 0]
solver.distance_constraint(carpet[0], carpet_target, 0, 0, weight=10)
solver.align_with(carpet[0], table[0])

# Tall storage occupies a solid section of the west wall above the doorway.
shelf_A[0].position = [0.675, 6.15, 0.90]
shelf_A[0].rotation = [0, 0, 0]
solver.distance_constraint(shelf_A[0], shelf_A_target, 0, 0, weight=10)
solver.against_wall(shelf_A[0], walls[3])
solver.point_towards(
    shelf_A[0],
    AssetInstance(position=[3.00, 6.15, 0.90])
)

# The low media shelf and television occupy the upper west wall. Their depth
# projects into the room rather than crossing the boundary.
shelf_C[0].position = [0.65, 7.60, 0.15]
shelf_C[0].rotation = [0, 0, 0]
solver.distance_constraint(shelf_C[0], shelf_C_target, 0, 0, weight=10)
solver.against_wall(shelf_C[0], walls[3])
solver.point_towards(
    shelf_C[0],
    AssetInstance(position=[3.60, 7.60, 0.15])
)

tv[0].position = [0.84, 7.60, 0.655]
tv[0].rotation = [0, 0, 0]
solver.on_top_of(tv[0], shelf_C[0])
solver.distance_constraint(tv[0], shelf_C[0], 0.19, 0.19, weight=10)
solver.point_towards(
    tv[0],
    AssetInstance(position=[3.60, 4.15, 0.65])
)

# Required o0015–o0008–o0006 relationship:
# shelf_E (o0015) and shelf_D (o0006) flank table (o0008), so the table is
# geometrically between the two shelves along the x-axis.
shelf_D[0].position = [2.25, 6.45, 0.325]
shelf_D[0].rotation = [0, 0, 0]
table[0].position = [3.25, 6.45, 0.375]
table[0].rotation = [0, 0, 0]
shelf_E[0].position = [4.25, 6.45, 0.325]
shelf_E[0].rotation = [0, 0, radians(180)]

solver.distance_constraint(shelf_D[0], shelf_D_target, 0, 0, weight=10)
solver.distance_constraint(table[0], table_target, 0, 0, weight=10)
solver.distance_constraint(shelf_E[0], shelf_E_target, 0, 0, weight=10)

# Equal center distances maintain the flanking arrangement and adequate gaps.
solver.distance_constraint(table[0], shelf_D[0], 1.00, 1.00, weight=10)
solver.distance_constraint(table[0], shelf_E[0], 1.00, 1.00, weight=10)
solver.point_towards(shelf_D[0], table[0])
solver.align_with(table[0], shelf_D[0])
solver.point_towards(shelf_E[0], table[0])

# Lamps on the two flanking shelves form a balanced task-lighting arrangement.
lamp_B[0].position = [2.25, 6.45, 0.925]
lamp_B[0].rotation = [0, 0, 0]
solver.on_top_of(lamp_B[0], shelf_D[0])
solver.distance_constraint(lamp_B[0], shelf_D[0], 0, 0, weight=10)
solver.align_with(lamp_B[0], shelf_D[0])

lamp_D[0].position = [4.25, 6.45, 0.925]
lamp_D[0].rotation = [0, 0, radians(180)]
solver.on_top_of(lamp_D[0], shelf_E[0])
solver.distance_constraint(lamp_D[0], shelf_E[0], 0, 0, weight=10)
solver.align_with(lamp_D[0], shelf_E[0])

# Both books rest on separate portions of the table surface.
book_A[0].position = [3.25, 6.15, 0.77]
book_A[0].rotation = [0, 0, 0]
solver.on_top_of(book_A[0], table[0])
solver.distance_constraint(book_A[0], table[0], 0.30, 0.30, weight=10)
solver.align_with(book_A[0], table[0])

book_B[0].position = [3.25, 6.75, 0.77]
book_B[0].rotation = [0, 0, 0]
solver.on_top_of(book_B[0], table[0])
solver.distance_constraint(book_B[0], table[0], 0.30, 0.30, weight=10)
solver.align_with(book_B[0], table[0])

# The floor lamp provides reading light near bed_B while remaining inside the
# diagonal boundary and outside the door and main circulation paths.
lamp_C[0].position = [5.60, 5.15, 0.775]
lamp_C[0].rotation = [0, 0, radians(-120)]
solver.distance_constraint(lamp_C[0], lamp_C_target, 0, 0, weight=10)
solver.distance_constraint(lamp_C[0], bed_B[0], 4.15, 4.30)
solver.point_towards(lamp_C[0], bed_B[0])

solver.constraints = []
carpet[0].position = [3.5999999046325684, 4.150000095367432, 0.009999999776482582]
carpet[0].rotation = [0, 0, 0.025132740962295976]
carpet[0].optimize = 2
bed_B[0].position = [4.900000095367432, 1.0499999523162842, 0.2750000059604645]
bed_B[0].rotation = [0, 0, 1.570796369352549]
bed_B[0].optimize = 2
lamp_D[0].position = [4.25, 6.449999809265137, 0.9249999523162842]
lamp_D[0].rotation = [0, 0, -3.11960150319319]
lamp_D[0].optimize = 2
shelf_D[0].position = [2.25, 6.449999809265137, 0.32499998807907104]
shelf_D[0].rotation = [0, 0, 0.025132740109855806]
shelf_D[0].optimize = 2
lamp_A[0].position = [2.1421568393707275, 1.7137436866760254, 0.875]
lamp_A[0].rotation = [0, 0, 2.8207263977357355]
lamp_A[0].optimize = 2
lamp_B[0].position = [2.25, 6.449999809265137, 0.9249999523162842]
lamp_B[0].rotation = [0, 0, 0.025132743180522565]
lamp_B[0].optimize = 2
table[0].position = [3.25, 6.449999809265137, 0.375]
table[0].rotation = [0, 0, 0.02513274219698523]
table[0].optimize = 2
book_A[0].position = [3.25, 5.969911098480225, 0.7699999809265137]
book_A[0].rotation = [0, 0, 0.025132742515919404]
book_A[0].optimize = 2
book_B[0].position = [3.25, 6.941635608673096, 0.7699999809265137]
book_B[0].rotation = [0, 0, 0.025132742515919404]
book_B[0].optimize = 2
bed_A[0].position = [1.5427250862121582, 2.8760743141174316, 0.2750000059604645]
bed_A[0].rotation = [0, 0, -0.11685029354313176]
bed_A[0].optimize = 2
tv[0].position = [0.8000012636184692, 7.405688285827637, 0.6549999713897705]
tv[0].rotation = [0, 0, 0.01256637125682779]
tv[0].optimize = 2
shelf_A[0].position = [0.675000011920929, 6.150000095367432, 0.8999999761581421]
shelf_A[0].rotation = [0, 0, 3.7648076153808906e-08]
shelf_A[0].optimize = 2
shelf_E[0].position = [4.25, 6.449999809265137, 0.32499998807907104]
shelf_E[0].rotation = [0, 0, -3.1196015053037707]
shelf_E[0].optimize = 2
lamp_C[0].position = [5.658048152923584, 5.208048343658447, 0.7749999761581421]
lamp_C[0].rotation = [0, 0, -2.01757237969587]
lamp_C[0].optimize = 2
shelf_C[0].position = [0.6500000357627869, 7.599999904632568, 0.15000000596046448]
shelf_C[0].rotation = [0, 0, 3.906893249262783e-08]
shelf_C[0].optimize = 2
shelf_B[0].position = [2.314375162124634, 1.5967192649841309, 0.30000001192092896]
shelf_B[0].rotation = [0, 0, 2.8266019577201016]
shelf_B[0].optimize = 2

