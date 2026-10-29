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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[9.00, 0.00, 0.00]),
    Wall(corner1=[9.00, 0.00, 0.00], corner2=[9.00, 3.00, 0.00]),
    Wall(corner1=[9.00, 3.00, 0.00], corner2=[0.00, 3.00, 0.00]),
    Wall(corner1=[0.00, 3.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
luggage_bench = Assets(description="luggage bench", size=[0.45, 0.90, 0.50], placements=[AssetInstance() for _ in range(1)])
single_bed = Assets(description="single bed", size=[2.00, 1.00, 0.60], placements=[AssetInstance() for _ in range(1)])
storage_cabinet = Assets(description="storage cabinet", size=[0.40, 0.80, 1.10], placements=[AssetInstance() for _ in range(1)])
writing_desk = Assets(description="writing desk", size=[0.60, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.60, 1.20, 2.10], placements=[AssetInstance() for _ in range(1)])
wall_shelf_A = Assets(description="A brown wood frame.", size=[0.22, 0.80, 0.35], placements=[AssetInstance() for _ in range(1)])
wall_mirror = Assets(description="A rectangular mirror in a brown wooden frame.", size=[0.04, 0.65, 1.00], placements=[AssetInstance() for _ in range(1)])
side_chair = Assets(description="side chair", size=[0.55, 0.50, 0.85], placements=[AssetInstance() for _ in range(1)])
floor_lamp = Assets(description="floor lamp", size=[0.35, 0.35, 1.60], placements=[AssetInstance() for _ in range(1)])
bedside_table = Assets(description="bedside table", size=[0.40, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
tv_console = Assets(description="tv console", size=[0.40, 1.20, 0.55], placements=[AssetInstance() for _ in range(1)])
desk_chair = Assets(description="desk chair", size=[0.55, 0.55, 0.90], placements=[AssetInstance() for _ in range(1)])
wall_shelf_B = Assets(description="A brown wood frame.", size=[0.22, 0.80, 0.35], placements=[AssetInstance() for _ in range(1)])

luggage_bench[0].instance_id = 'luggage_bench_0'
single_bed[0].instance_id = 'single_bed_0'
storage_cabinet[0].instance_id = 'storage_cabinet_0'
writing_desk[0].instance_id = 'writing_desk_0'
wardrobe[0].instance_id = 'wardrobe_0'
wall_shelf_A[0].instance_id = 'wall_shelf_A_0'
wall_mirror[0].instance_id = 'wall_mirror_0'
side_chair[0].instance_id = 'side_chair_0'
floor_lamp[0].instance_id = 'floor_lamp_0'
bedside_table[0].instance_id = 'bedside_table_0'
tv_console[0].instance_id = 'tv_console_0'
desk_chair[0].instance_id = 'desk_chair_0'
wall_shelf_B[0].instance_id = 'wall_shelf_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

luggage_bench[0].position = [4.6791513509753475, 1.4142526508932138, 0.25]
luggage_bench[0].rotation = [0, 0, 0]
single_bed[0].position = [2.1002368168035916, 0.28700188016398087, 0.3]
single_bed[0].rotation = [0, 0, 0]
storage_cabinet[0].position = [8.561301709700176, 2.277372546026153, 0.55]
storage_cabinet[0].rotation = [0, 0, 0]
writing_desk[0].position = [7.599495694656724, 0.6516490722146943, 0.375]
writing_desk[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.2766715259877701, 0.40646359225547, 1.05]
wardrobe[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [3.8861353746940432, 1.4038095311708498, 0.175]
wall_shelf_A[0].rotation = [0, 0, 0]
wall_mirror[0].position = [3.066287848183346, 1.4634250956241632, 0.5]
wall_mirror[0].rotation = [0, 0, 0]
side_chair[0].position = [2.069224156118475, 0.11952183878897638, 0.425]
side_chair[0].rotation = [0, 0, 0]
floor_lamp[0].position = [8.122500202677621, 1.1813249748496126, 0.8]
floor_lamp[0].rotation = [0, 0, 0]
bedside_table[0].position = [1.380659073211904, 1.1122784631411458, 0.275]
bedside_table[0].rotation = [0, 0, 0]
tv_console[0].position = [6.671667530264683, 0.22616514726593828, 0.275]
tv_console[0].rotation = [0, 0, 0]
desk_chair[0].position = [3.2037656544450375, 0.21587756209568, 0.45]
desk_chair[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [6.05472837486055, 0.5733377080748387, 0.175]
wall_shelf_B[0].rotation = [0, 0, 0]
luggage_bench[0].position = [4.6791513509753475, 1.4142526508932138, 0.25]
luggage_bench[0].rotation = [0, 0, 0]
single_bed[0].position = [2.1002368168035916, 0.28700188016398087, 0.3]
single_bed[0].rotation = [0, 0, 0]
storage_cabinet[0].position = [8.561301709700176, 2.277372546026153, 0.55]
storage_cabinet[0].rotation = [0, 0, 0]
writing_desk[0].position = [7.599495694656724, 0.6516490722146943, 0.375]
writing_desk[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.2766715259877701, 0.40646359225547, 1.05]
wardrobe[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [3.8861353746940432, 1.4038095311708498, 0.175]
wall_shelf_A[0].rotation = [0, 0, 0]
wall_mirror[0].position = [3.066287848183346, 1.4634250956241632, 0.5]
wall_mirror[0].rotation = [0, 0, 0]
side_chair[0].position = [2.069224156118475, 0.11952183878897638, 0.425]
side_chair[0].rotation = [0, 0, 0]
floor_lamp[0].position = [8.122500202677621, 1.1813249748496126, 0.8]
floor_lamp[0].rotation = [0, 0, 0]
bedside_table[0].position = [1.380659073211904, 1.1122784631411458, 0.275]
bedside_table[0].rotation = [0, 0, 0]
tv_console[0].position = [6.671667530264683, 0.22616514726593828, 0.275]
tv_console[0].rotation = [0, 0, 0]
desk_chair[0].position = [3.2037656544450375, 0.21587756209568, 0.45]
desk_chair[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [6.05472837486055, 0.5733377080748387, 0.175]
wall_shelf_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Keep the entrance at x=0 clear: the first furniture begins at x=1.4.
# Storage occupies the left end, the work area the middle, and the bed
# the far end. The right-wall window remains unobstructed.
#
# Each entry specifies an existing asset, its center, its heading in
# degrees, and (where applicable) the wall supporting its back.
layout_specs = [
    (luggage_bench,  [2.00, 0.225, 0.250],  90, 0),
    (wardrobe,      [2.00, 2.700, 1.050], 270, 2),
    (wall_mirror,   [2.00, 0.020, 1.500],  90, 0),

    (side_chair,    [3.20, 2.600, 0.425], 270, None),
    (floor_lamp,    [3.85, 2.800, 0.800], 270, None),

    # The desk is freestanding, with a low cabinet behind it.
    # The seated user faces both the desk and the cabinet.
    (writing_desk,  [5.30, 2.150, 0.375], 270, None),
    (storage_cabinet, [5.30, 2.800, 0.550], 270, 2),
    (desk_chair,    [5.30, 1.400, 0.450],  90, None),

    # These are wall-mounted shelves, not floor-standing objects.
    # Their lower edges are above both the cabinet and desk.
    (wall_shelf_A,  [4.80, 2.890, 1.650], 270, 2),
    (wall_shelf_B,  [5.80, 2.890, 1.650], 270, 2),

    (single_bed,    [7.70, 2.450, 0.300],   0, None),
    (bedside_table, [6.40, 2.800, 0.275], 270, 2),
    (tv_console,    [7.70, 0.200, 0.275],  90, 0),
]

# Exact center anchors preserve the entrance clearance, central walkway,
# window clearance, and non-overlapping footprints. They also fix the
# installation heights of the wall-mounted mirror and shelves without
# incorrectly placing those fixtures on top of floor furniture.
for asset_group, center_xyz, heading_deg, wall_index in layout_specs:
    placed_instance = asset_group[0]
    placed_instance.position = list(center_xyz)
    placed_instance.rotation = [0, 0, radians(heading_deg)]

    solver.distance_constraint(
        placed_instance,
        AssetInstance(position=list(center_xyz)),
        min_distance=0,
        max_distance=0,
        weight=10,
    )

# Explicitly enforce the requested chair-to-cabinet facing relationship
# before adding the remaining orientation constraints.
solver.point_towards(desk_chair[0], storage_cabinet[0])

for asset_group, center_xyz, heading_deg, wall_index in layout_specs:
    placed_instance = asset_group[0]

    if asset_group is not desk_chair:
        solver.align_with(
            placed_instance,
            AssetInstance(
                position=list(center_xyz),
                rotation=[0, 0, radians(heading_deg)],
            ),
            angle=0,
        )

    if wall_index is not None:
        solver.against_wall(placed_instance, walls[wall_index])

# Functional relationships supplement the absolute placement anchors.
# Distance constraints measure 3D center-to-center distances.
def retain_center_spacing(first_instance, second_instance):
    center_distance = sum(
        (first_instance.position[axis] - second_instance.position[axis]) ** 2
        for axis in range(3)
    ) ** 0.5
    solver.distance_constraint(
        first_instance, second_instance,
        min_distance=center_distance,
        max_distance=center_distance,
    )

retain_center_spacing(desk_chair[0], writing_desk[0])
retain_center_spacing(writing_desk[0], storage_cabinet[0])
retain_center_spacing(bedside_table[0], single_bed[0])
retain_center_spacing(tv_console[0], single_bed[0])
retain_center_spacing(floor_lamp[0], side_chair[0])

# The desk faces its user; the console faces the sleeping area.
solver.point_towards(writing_desk[0], desk_chair[0])
solver.point_towards(tv_console[0], single_bed[0])

solver.constraints = []
bedside_table[0].position = [6.398447513580322, 2.7956337928771973, 0.2750000059604645]
bedside_table[0].rotation = [0, 0, -1.5735083979552418]
bedside_table[0].optimize = 2
luggage_bench[0].position = [2.0, 0.22556152939796448, 0.25]
luggage_bench[0].rotation = [0, 0, 1.5718310431632023]
luggage_bench[0].optimize = 2
single_bed[0].position = [7.699999809265137, 2.450000047683716, 0.30000001192092896]
single_bed[0].rotation = [0, 0, 0.01884955539881635]
single_bed[0].optimize = 2
wall_mirror[0].position = [2.0, 0.017607150599360466, 0.5]
wall_mirror[0].rotation = [0, 0, 1.571833513224998]
wall_mirror[0].optimize = 2
tv_console[0].position = [7.699999809265137, 0.2049812376499176, 0.2750000059604645]
tv_console[0].rotation = [0, 0, 1.5665763831602915]
tv_console[0].optimize = 2
wall_shelf_A[0].position = [4.800000190734863, 2.8896210193634033, 0.17499999701976776]
wall_shelf_A[0].rotation = [0, 0, -1.5697603623320309]
wall_shelf_A[0].optimize = 2
wardrobe[0].position = [2.0, 2.6987946033477783, 1.0499999523162842]
wardrobe[0].rotation = [0, 0, -1.5697621856958444]
wardrobe[0].optimize = 2
storage_cabinet[0].position = [5.300000190734863, 2.7987024784088135, 0.550000011920929]
storage_cabinet[0].rotation = [0, 0, -1.5750178293714083]
storage_cabinet[0].optimize = 2
side_chair[0].position = [3.200000047683716, 2.5999999046325684, 0.42500001192092896]
side_chair[0].rotation = [0, 0, -1.5582299555380688]
side_chair[0].optimize = 2
writing_desk[0].position = [5.300000190734863, 2.0774295330047607, 0.375]
writing_desk[0].rotation = [0, 0, -1.5519467713960802]
writing_desk[0].optimize = 2
desk_chair[0].position = [5.300000190734863, 1.2988797426223755, 0.44999998807907104]
desk_chair[0].rotation = [0, 0, 1.586504290712113]
desk_chair[0].optimize = 2
floor_lamp[0].position = [3.9191782474517822, 2.8272128105163574, 0.800000011920929]
floor_lamp[0].rotation = [0, 0, -1.5582299555380688]
floor_lamp[0].optimize = 2
wall_shelf_B[0].position = [5.800000190734863, 2.8896210193634033, 0.17499999701976776]
wall_shelf_B[0].rotation = [0, 0, -1.5697603623320309]
wall_shelf_B[0].optimize = 2

