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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[5.00, 0.00, 0.00]),
    Wall(corner1=[5.00, 0.00, 0.00], corner2=[5.00, 3.00, 0.00]),
    Wall(corner1=[5.00, 3.00, 0.00], corner2=[0.00, 3.00, 0.00]),
    Wall(corner1=[0.00, 3.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
towel_bar_A = Assets(description="A plain silver towel rack.", size=[0.08, 0.65, 0.06], placements=[AssetInstance() for _ in range(1)])
laundry_hamper_A = Assets(description="A wicker basket with pink bands and some blue patterns.", size=[0.35, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])
low_bathroom_storage_bench = Assets(description="low bathroom storage bench", size=[0.42, 1.20, 0.48], placements=[AssetInstance() for _ in range(1)])
small_side_stool_A = Assets(description="a wooden stool with two legs", size=[0.30, 0.40, 0.45], placements=[AssetInstance() for _ in range(1)])
floor_planter_A = Assets(description="A potted plant with green leaves.", size=[0.55, 0.55, 1.10], placements=[AssetInstance() for _ in range(1)])
towel_bar_B = Assets(description="A plain silver towel rack.", size=[0.08, 0.65, 0.06], placements=[AssetInstance() for _ in range(1)])
tall_bathroom_cabinet = Assets(description="tall bathroom cabinet", size=[0.40, 0.75, 1.90], placements=[AssetInstance() for _ in range(1)])
small_side_stool_B = Assets(description="a wooden stool with two legs", size=[0.30, 0.40, 0.45], placements=[AssetInstance() for _ in range(1)])
laundry_hamper_B = Assets(description="A wicker basket with pink bands and some blue patterns.", size=[0.35, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])
toilet = Assets(description="An old dirty white porcelain toilet.", size=[0.70, 0.40, 0.78], placements=[AssetInstance() for _ in range(1)])
towel_bar_C = Assets(description="A plain silver towel rack.", size=[0.08, 0.65, 0.06], placements=[AssetInstance() for _ in range(1)])
wall_shelf_A = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.22, 0.80, 0.25], placements=[AssetInstance() for _ in range(1)])
wall_shelf_B = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.22, 0.80, 0.25], placements=[AssetInstance() for _ in range(1)])
bidet = Assets(description="A cartoon grey and red-striped toilet.", size=[0.58, 0.38, 0.42], placements=[AssetInstance() for _ in range(1)])
floor_planter_B = Assets(description="A potted plant with green leaves.", size=[0.55, 0.55, 1.10], placements=[AssetInstance() for _ in range(1)])
small_potted_plant = Assets(description="A pale brown flowerpot with a two branched green and white plant growing inside.", size=[0.30, 0.30, 0.55], placements=[AssetInstance() for _ in range(1)])
freestanding_bathtub = Assets(description="White curved bathtub with no feet.", size=[0.80, 1.75, 0.60], placements=[AssetInstance() for _ in range(1)])
heated_towel_rail = Assets(description="A black towel rack.", size=[0.12, 0.60, 1.20], placements=[AssetInstance() for _ in range(1)])

towel_bar_A[0].instance_id = 'towel_bar_A_0'
laundry_hamper_A[0].instance_id = 'laundry_hamper_A_0'
low_bathroom_storage_bench[0].instance_id = 'low_bathroom_storage_bench_0'
small_side_stool_A[0].instance_id = 'small_side_stool_A_0'
floor_planter_A[0].instance_id = 'floor_planter_A_0'
towel_bar_B[0].instance_id = 'towel_bar_B_0'
tall_bathroom_cabinet[0].instance_id = 'tall_bathroom_cabinet_0'
small_side_stool_B[0].instance_id = 'small_side_stool_B_0'
laundry_hamper_B[0].instance_id = 'laundry_hamper_B_0'
toilet[0].instance_id = 'toilet_0'
towel_bar_C[0].instance_id = 'towel_bar_C_0'
wall_shelf_A[0].instance_id = 'wall_shelf_A_0'
wall_shelf_B[0].instance_id = 'wall_shelf_B_0'
bidet[0].instance_id = 'bidet_0'
floor_planter_B[0].instance_id = 'floor_planter_B_0'
small_potted_plant[0].instance_id = 'small_potted_plant_0'
freestanding_bathtub[0].instance_id = 'freestanding_bathtub_0'
heated_towel_rail[0].instance_id = 'heated_towel_rail_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

towel_bar_A[0].position = [2.667575482253497, 1.8791116599990978, 0.03]
towel_bar_A[0].rotation = [0, 0, 0]
laundry_hamper_A[0].position = [0.9777180409258857, 2.2346227236508955, 0.3]
laundry_hamper_A[0].rotation = [0, 0, 0]
low_bathroom_storage_bench[0].position = [3.2103920413918967, 1.2382174401647472, 0.24]
low_bathroom_storage_bench[0].rotation = [0, 0, 0]
small_side_stool_A[0].position = [3.308598675314249, 0.72017016851422, 0.225]
small_side_stool_A[0].rotation = [0, 0, 0]
floor_planter_A[0].position = [3.8165487299601435, 2.213746194684277, 0.55]
floor_planter_A[0].rotation = [0, 0, 0]
towel_bar_B[0].position = [0.8485305309000052, 0.9101595745441335, 0.03]
towel_bar_B[0].rotation = [0, 0, 0]
tall_bathroom_cabinet[0].position = [0.45296082278522665, 0.10185715591713995, 0.95]
tall_bathroom_cabinet[0].rotation = [0, 0, 0]
small_side_stool_B[0].position = [1.4929059227991255, 2.7173391356261978, 0.225]
small_side_stool_B[0].rotation = [0, 0, 0]
laundry_hamper_B[0].position = [0.02711422141922104, 1.0199210393870937, 0.3]
laundry_hamper_B[0].rotation = [0, 0, 0]
toilet[0].position = [4.447988415516391, 0.1591090494218893, 0.39]
toilet[0].rotation = [0, 0, 0]
towel_bar_C[0].position = [0.1428913475636323, 0.7389655299742338, 0.03]
towel_bar_C[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [0.261182154783679, 1.187379725328634, 0.125]
wall_shelf_A[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [1.8583415120194613, 0.03792852798257107, 0.125]
wall_shelf_B[0].rotation = [0, 0, 0]
bidet[0].position = [3.831488522819388, 1.9067569033030383, 0.21]
bidet[0].rotation = [0, 0, 0]
floor_planter_B[0].position = [2.3822732390976786, 1.3155501952377953, 0.55]
floor_planter_B[0].rotation = [0, 0, 0]
small_potted_plant[0].position = [2.884653939841259, 2.226930923337442, 0.275]
small_potted_plant[0].rotation = [0, 0, 0]
freestanding_bathtub[0].position = [1.5367592039285056, 1.3267327074202377, 0.3]
freestanding_bathtub[0].rotation = [0, 0, 0]
heated_towel_rail[0].position = [4.784359277907875, 2.0398889852187856, 0.6]
heated_towel_rail[0].rotation = [0, 0, 0]
towel_bar_A[0].position = [2.667575482253497, 1.8791116599990978, 0.03]
towel_bar_A[0].rotation = [0, 0, 0]
laundry_hamper_A[0].position = [0.9777180409258857, 2.2346227236508955, 0.3]
laundry_hamper_A[0].rotation = [0, 0, 0]
low_bathroom_storage_bench[0].position = [3.2103920413918967, 1.2382174401647472, 0.24]
low_bathroom_storage_bench[0].rotation = [0, 0, 0]
small_side_stool_A[0].position = [3.308598675314249, 0.72017016851422, 0.225]
small_side_stool_A[0].rotation = [0, 0, 0]
floor_planter_A[0].position = [3.8165487299601435, 2.213746194684277, 0.55]
floor_planter_A[0].rotation = [0, 0, 0]
towel_bar_B[0].position = [0.8485305309000052, 0.9101595745441335, 0.03]
towel_bar_B[0].rotation = [0, 0, 0]
tall_bathroom_cabinet[0].position = [0.45296082278522665, 0.10185715591713995, 0.95]
tall_bathroom_cabinet[0].rotation = [0, 0, 0]
small_side_stool_B[0].position = [1.4929059227991255, 2.7173391356261978, 0.225]
small_side_stool_B[0].rotation = [0, 0, 0]
laundry_hamper_B[0].position = [0.02711422141922104, 1.0199210393870937, 0.3]
laundry_hamper_B[0].rotation = [0, 0, 0]
toilet[0].position = [4.447988415516391, 0.1591090494218893, 0.39]
toilet[0].rotation = [0, 0, 0]
towel_bar_C[0].position = [0.1428913475636323, 0.7389655299742338, 0.03]
towel_bar_C[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [0.261182154783679, 1.187379725328634, 0.125]
wall_shelf_A[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [1.8583415120194613, 0.03792852798257107, 0.125]
wall_shelf_B[0].rotation = [0, 0, 0]
bidet[0].position = [3.831488522819388, 1.9067569033030383, 0.21]
bidet[0].rotation = [0, 0, 0]
floor_planter_B[0].position = [2.3822732390976786, 1.3155501952377953, 0.55]
floor_planter_B[0].rotation = [0, 0, 0]
small_potted_plant[0].position = [2.884653939841259, 2.226930923337442, 0.275]
small_potted_plant[0].rotation = [0, 0, 0]
freestanding_bathtub[0].position = [1.5367592039285056, 1.3267327074202377, 0.3]
freestanding_bathtub[0].rotation = [0, 0, 0]
heated_towel_rail[0].position = [4.784359277907875, 2.0398889852187856, 0.6]
heated_towel_rail[0].rotation = [0, 0, 0]

solver.constraints = []

# The doorway occupies x=0.00..1.00 on the north wall (y=3.00).
# Keep its approach clear by placing all floor-standing objects outside that zone.

# Cardinal rotations used by objects placed against each wall.
_face_east = AssetInstance(rotation=[0, 0, radians(0)])
_face_north = AssetInstance(rotation=[0, 0, radians(90)])
_face_west = AssetInstance(rotation=[0, 0, radians(180)])
_face_south = AssetInstance(rotation=[0, 0, radians(-90)])


def pin_position(instance, position, orientation):
    """Keep an instance at its planned location and orientation."""
    solver.distance_constraint(
        instance,
        AssetInstance(position=position),
        0,
        0,
        weight=10,
    )
    solver.align_with(instance, orientation)


def place_at_wall(instance, wall, position, orientation):
    """Preserve both wall adjacency and the selected position along the wall."""
    solver.against_wall(instance, wall)
    pin_position(instance, position, orientation)


# ---------------------------------------------------------------------------
# Initial placements
# ---------------------------------------------------------------------------

# Left-wall group.
tall_bathroom_cabinet[0].position = [0.20, 0.55, 0.95]
tall_bathroom_cabinet[0].rotation = [0, 0, radians(0)]

towel_bar_A[0].position = [0.04, 1.30, 1.30]
towel_bar_A[0].rotation = [0, 0, radians(0)]

wall_shelf_A[0].position = [0.11, 1.90, 1.65]
wall_shelf_A[0].rotation = [0, 0, radians(0)]

# South-wall group. These objects face into the room and remain well away
# from the doorway approach at the northwest corner.
floor_planter_A[0].position = [0.75, 0.275, 0.55]
floor_planter_A[0].rotation = [0, 0, radians(90)]

laundry_hamper_A[0].position = [1.30, 0.225, 0.30]
laundry_hamper_A[0].rotation = [0, 0, radians(90)]

small_side_stool_A[0].position = [1.82, 0.20, 0.225]
small_side_stool_A[0].rotation = [0, 0, radians(90)]

toilet[0].position = [2.35, 0.35, 0.39]
toilet[0].rotation = [0, 0, radians(90)]

bidet[0].position = [2.95, 0.29, 0.21]
bidet[0].rotation = [0, 0, radians(90)]

floor_planter_B[0].position = [3.55, 0.275, 0.55]
floor_planter_B[0].rotation = [0, 0, radians(90)]

# The second towel bar is mounted above the south-wall furniture.
towel_bar_B[0].position = [1.48, 0.04, 1.30]
towel_bar_B[0].rotation = [0, 0, radians(90)]

# North-wall storage begins to the right of the one-meter-wide doorway.
low_bathroom_storage_bench[0].position = [1.65, 2.79, 0.24]
low_bathroom_storage_bench[0].rotation = [0, 0, radians(-90)]

laundry_hamper_B[0].position = [2.55, 2.825, 0.30]
laundry_hamper_B[0].rotation = [0, 0, radians(-90)]

small_side_stool_B[0].position = [3.08, 2.85, 0.225]
small_side_stool_B[0].rotation = [0, 0, radians(-90)]

# Center the small plant on the storage bench. Its center height is the
# bench height (0.48 m) plus half the plant height (0.275 m).
small_potted_plant[0].position = [1.65, 2.79, 0.755]
small_potted_plant[0].rotation = [0, 0, radians(-90)]

# The bathtub runs lengthwise along the right wall. Its northern end stops
# before the north-wall furniture, leaving usable circulation in the middle.
freestanding_bathtub[0].position = [4.60, 1.55, 0.30]
freestanding_bathtub[0].rotation = [0, 0, radians(180)]

# Right-wall accessories are mounted above the bathtub and do not intersect it.
wall_shelf_B[0].position = [4.89, 1.45, 1.65]
wall_shelf_B[0].rotation = [0, 0, radians(180)]

towel_bar_C[0].position = [4.96, 2.48, 1.40]
towel_bar_C[0].rotation = [0, 0, radians(180)]

# The heated rail occupies the unobstructed north-wall section near the
# northeast corner. Its bottom is at floor level, as implied by its height.
heated_towel_rail[0].position = [4.55, 2.94, 0.60]
heated_towel_rail[0].rotation = [0, 0, radians(-90)]


# ---------------------------------------------------------------------------
# Constraints
# walls[0] = south, walls[1] = east, walls[2] = north, walls[3] = west
# ---------------------------------------------------------------------------

# Left wall.
place_at_wall(
    tall_bathroom_cabinet[0], walls[3],
    [0.20, 0.55, 0.95], _face_east
)
place_at_wall(
    towel_bar_A[0], walls[3],
    [0.04, 1.30, 1.30], _face_east
)
place_at_wall(
    wall_shelf_A[0], walls[3],
    [0.11, 1.90, 1.65], _face_east
)

# South wall and adjacent floor-standing objects.
place_at_wall(
    floor_planter_A[0], walls[0],
    [0.75, 0.275, 0.55], _face_north
)
place_at_wall(
    laundry_hamper_A[0], walls[0],
    [1.30, 0.225, 0.30], _face_north
)
place_at_wall(
    small_side_stool_A[0], walls[0],
    [1.82, 0.20, 0.225], _face_north
)
place_at_wall(
    toilet[0], walls[0],
    [2.35, 0.35, 0.39], _face_north
)
place_at_wall(
    bidet[0], walls[0],
    [2.95, 0.29, 0.21], _face_north
)
place_at_wall(
    floor_planter_B[0], walls[0],
    [3.55, 0.275, 0.55], _face_north
)
place_at_wall(
    towel_bar_B[0], walls[0],
    [1.48, 0.04, 1.30], _face_north
)

# North wall. All floor-level placements start beyond x=1.00, preserving the
# full doorway and the floor area directly in front of it.
place_at_wall(
    low_bathroom_storage_bench[0], walls[2],
    [1.65, 2.79, 0.24], _face_south
)
place_at_wall(
    laundry_hamper_B[0], walls[2],
    [2.55, 2.825, 0.30], _face_south
)
place_at_wall(
    small_side_stool_B[0], walls[2],
    [3.08, 2.85, 0.225], _face_south
)
place_at_wall(
    heated_towel_rail[0], walls[2],
    [4.55, 2.94, 0.60], _face_south
)

# The plant-to-bench relationship is the primary semantic requirement.
solver.on_top_of(
    small_potted_plant[0],
    low_bathroom_storage_bench[0],
)
solver.distance_constraint(
    small_potted_plant[0],
    AssetInstance(position=[1.65, 2.79, 0.755]),
    0,
    0,
    weight=10,
)
solver.align_with(
    small_potted_plant[0],
    low_bathroom_storage_bench[0],
)

# Right wall.
place_at_wall(
    freestanding_bathtub[0], walls[1],
    [4.60, 1.55, 0.30], _face_west
)
place_at_wall(
    wall_shelf_B[0], walls[1],
    [4.89, 1.45, 1.65], _face_west
)
place_at_wall(
    towel_bar_C[0], walls[1],
    [4.96, 2.48, 1.40], _face_west
)

solver.constraints = []
small_potted_plant[0].position = [1.649999976158142, 2.7899999618530273, 0.7549999952316284]
small_potted_plant[0].rotation = [0, 0, -1.548008960619117]
small_potted_plant[0].optimize = 2
freestanding_bathtub[0].position = [4.59903621673584, 1.5499999523162842, 0.30000001192092896]
freestanding_bathtub[0].rotation = [0, 0, -3.1390517531931446]
freestanding_bathtub[0].optimize = 2
tall_bathroom_cabinet[0].position = [0.2009522169828415, 0.550000011920929, 0.949999988079071]
tall_bathroom_cabinet[0].rotation = [0, 0, 0.002540918150658852]
tall_bathroom_cabinet[0].optimize = 2
towel_bar_C[0].position = [4.959174156188965, 2.4800000190734863, 0.029999999329447746]
towel_bar_C[0].rotation = [0, 0, -3.1390517354391343]
towel_bar_C[0].optimize = 2
laundry_hamper_A[0].position = [1.2999999523162842, 0.21500004827976227, 0.30000001192092896]
laundry_hamper_A[0].rotation = [0, 0, 1.5733372470898281]
laundry_hamper_A[0].optimize = 2
low_bathroom_storage_bench[0].position = [1.649999976158142, 2.7887279987335205, 0.23999999463558197]
low_bathroom_storage_bench[0].rotation = [0, 0, -1.562034109639902]
low_bathroom_storage_bench[0].optimize = 2
floor_planter_B[0].position = [3.549999952316284, 0.27569788694381714, 0.550000011920929]
floor_planter_B[0].rotation = [0, 0, 1.573337246167655]
floor_planter_B[0].optimize = 2
heated_towel_rail[0].position = [4.550000190734863, 2.9392378330230713, 0.6000000238418579]
heated_towel_rail[0].rotation = [0, 0, -1.5682554074221384]
heated_towel_rail[0].optimize = 2
small_side_stool_B[0].position = [3.0799999237060547, 2.849492311477661, 0.22499999403953552]
small_side_stool_B[0].rotation = [0, 0, -1.5682554052778654]
small_side_stool_B[0].optimize = 2
wall_shelf_B[0].position = [4.888984203338623, 1.4500000476837158, 0.125]
wall_shelf_B[0].rotation = [0, 0, -3.13905173573906]
wall_shelf_B[0].optimize = 2
towel_bar_A[0].position = [0.04082566872239113, 1.2999999523162842, 0.029999999329447746]
towel_bar_A[0].rotation = [0, 0, 0.0025409172284856325]
towel_bar_A[0].optimize = 2
towel_bar_B[0].position = [1.4800000190734863, 0.04082566872239113, 0.029999999329447746]
towel_bar_B[0].rotation = [0, 0, 1.5733372440233822]
towel_bar_B[0].optimize = 2
toilet[0].position = [2.3499999046325684, 0.35050708055496216, 0.38999998569488525]
toilet[0].rotation = [0, 0, 1.573337248311928]
toilet[0].optimize = 2
laundry_hamper_B[0].position = [2.549999952316284, 2.8244287967681885, 0.30000001192092896]
laundry_hamper_B[0].rotation = [0, 0, -1.5682554074221384]
laundry_hamper_B[0].optimize = 2
small_side_stool_A[0].position = [1.8200000524520874, 0.19000005722045898, 0.22499999403953552]
small_side_stool_A[0].rotation = [0, 0, 1.5733372473897544]
small_side_stool_A[0].optimize = 2
floor_planter_A[0].position = [0.75, 0.27569788694381714, 0.550000011920929]
floor_planter_A[0].rotation = [0, 0, 1.573337246167655]
floor_planter_A[0].optimize = 2
wall_shelf_A[0].position = [0.11101601272821426, 1.899999976158142, 0.125]
wall_shelf_A[0].rotation = [0, 0, 0.002540916928559797]
wall_shelf_A[0].optimize = 2
bidet[0].position = [2.950000047683716, 0.290481835603714, 0.20999999344348907]
bidet[0].rotation = [0, 0, 1.573337248311928]
bidet[0].optimize = 2

