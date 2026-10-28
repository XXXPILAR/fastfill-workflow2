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
    Wall(corner1=[5.00, 0.00, 0.00], corner2=[5.00, 5.00, 0.00]),
    Wall(corner1=[5.00, 5.00, 0.00], corner2=[0.00, 5.00, 0.00]),
    Wall(corner1=[0.00, 5.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
paper_towel_dispenser = Assets(description="A hand soap dispenser for a wall.", size=[0.10, 0.12, 0.25], placements=[AssetInstance() for _ in range(1)])
entry_bench = Assets(description="A wooden bench to sit on with metal re-enforcement.", size=[0.45, 1.50, 0.45], placements=[AssetInstance() for _ in range(1)])
mirror_panel = Assets(description="A rectangular mirror in a brown wooden frame.", size=[0.05, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
toilet_suite_A = Assets(description="toilet suite", size=[0.70, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
hand_dryer_A = Assets(description="A white rectangular box.", size=[0.18, 0.30, 0.55], placements=[AssetInstance() for _ in range(1)])
waste_bin_A = Assets(description="a wheeled trash can", size=[0.55, 0.48, 0.95], placements=[AssetInstance() for _ in range(1)])
hand_dryer_B = Assets(description="A white rectangular box.", size=[0.18, 0.30, 0.55], placements=[AssetInstance() for _ in range(1)])
waste_bin_B = Assets(description="a wheeled trash can", size=[0.55, 0.48, 0.95], placements=[AssetInstance() for _ in range(1)])
cleaning_cabinet = Assets(description="cleaning cabinet", size=[0.45, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
toilet_suite_B = Assets(description="toilet suite", size=[0.70, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
vanity_counter = Assets(description="A sink inside of a kitchen cabinet.", size=[0.60, 1.50, 0.90], placements=[AssetInstance() for _ in range(1)])
toilet_suite_C = Assets(description="toilet suite", size=[0.70, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])

paper_towel_dispenser[0].instance_id = 'paper_towel_dispenser_0'
entry_bench[0].instance_id = 'entry_bench_0'
mirror_panel[0].instance_id = 'mirror_panel_0'
toilet_suite_A[0].instance_id = 'toilet_suite_A_0'
hand_dryer_A[0].instance_id = 'hand_dryer_A_0'
waste_bin_A[0].instance_id = 'waste_bin_A_0'
hand_dryer_B[0].instance_id = 'hand_dryer_B_0'
waste_bin_B[0].instance_id = 'waste_bin_B_0'
cleaning_cabinet[0].instance_id = 'cleaning_cabinet_0'
toilet_suite_B[0].instance_id = 'toilet_suite_B_0'
vanity_counter[0].instance_id = 'vanity_counter_0'
toilet_suite_C[0].instance_id = 'toilet_suite_C_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

paper_towel_dispenser[0].position = [2.424221451091416, 0.019891790570637502, 0.125]
paper_towel_dispenser[0].rotation = [0, 0, 0]
entry_bench[0].position = [3.109261998283859, 3.851563709787838, 0.225]
entry_bench[0].rotation = [0, 0, 0]
mirror_panel[0].position = [1.832919565983372, 1.6983312908614452, 0.45]
mirror_panel[0].rotation = [0, 0, 0]
toilet_suite_A[0].position = [3.677467204821782, 1.103966030977403, 0.39]
toilet_suite_A[0].rotation = [0, 0, 0]
hand_dryer_A[0].position = [2.1252444453187085, 0.39772304746807097, 0.275]
hand_dryer_A[0].rotation = [0, 0, 0]
waste_bin_A[0].position = [4.057514754160642, 0.14073452518601592, 0.475]
waste_bin_A[0].rotation = [0, 0, 0]
hand_dryer_B[0].position = [0.23804313199430716, 2.065779389932514, 0.275]
hand_dryer_B[0].rotation = [0, 0, 0]
waste_bin_B[0].position = [1.6619049130413814, 0.8355044049513682, 0.475]
waste_bin_B[0].rotation = [0, 0, 0]
cleaning_cabinet[0].position = [2.690844112478819, 3.826144839144328, 0.9]
cleaning_cabinet[0].rotation = [0, 0, 0]
toilet_suite_B[0].position = [3.6684424021230253, 1.886397084683273, 0.39]
toilet_suite_B[0].rotation = [0, 0, 0]
vanity_counter[0].position = [0.5282188275085231, 0.6716362232869383, 0.45]
vanity_counter[0].rotation = [0, 0, 0]
toilet_suite_C[0].position = [2.704132748218488, 1.7452292627442034, 0.39]
toilet_suite_C[0].rotation = [0, 0, 0]
paper_towel_dispenser[0].position = [2.424221451091416, 0.019891790570637502, 0.125]
paper_towel_dispenser[0].rotation = [0, 0, 0]
entry_bench[0].position = [3.109261998283859, 3.851563709787838, 0.225]
entry_bench[0].rotation = [0, 0, 0]
mirror_panel[0].position = [1.832919565983372, 1.6983312908614452, 0.45]
mirror_panel[0].rotation = [0, 0, 0]
toilet_suite_A[0].position = [3.677467204821782, 1.103966030977403, 0.39]
toilet_suite_A[0].rotation = [0, 0, 0]
hand_dryer_A[0].position = [2.1252444453187085, 0.39772304746807097, 0.275]
hand_dryer_A[0].rotation = [0, 0, 0]
waste_bin_A[0].position = [4.057514754160642, 0.14073452518601592, 0.475]
waste_bin_A[0].rotation = [0, 0, 0]
hand_dryer_B[0].position = [0.23804313199430716, 2.065779389932514, 0.275]
hand_dryer_B[0].rotation = [0, 0, 0]
waste_bin_B[0].position = [1.6619049130413814, 0.8355044049513682, 0.475]
waste_bin_B[0].rotation = [0, 0, 0]
cleaning_cabinet[0].position = [2.690844112478819, 3.826144839144328, 0.9]
cleaning_cabinet[0].rotation = [0, 0, 0]
toilet_suite_B[0].position = [3.6684424021230253, 1.886397084683273, 0.39]
toilet_suite_B[0].rotation = [0, 0, 0]
vanity_counter[0].position = [0.5282188275085231, 0.6716362232869383, 0.45]
vanity_counter[0].rotation = [0, 0, 0]
toilet_suite_C[0].position = [2.704132748218488, 1.7452292627442034, 0.39]
toilet_suite_C[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed reference points used to preserve the intended positions and orientations.
room_center = AssetInstance(position=[2.50, 2.50, 0.00])
east_facing_reference = AssetInstance(position=[2.50, 0.00, 0.00])
north_facing_reference = AssetInstance(position=[0.00, 2.50, 0.00])

# Place the three toilet suites in a row along the west wall. Based on the
# provided object identifiers, toilet_suite_B (o0009) is centered between
# toilet_suite_A (o0003) and toilet_suite_C (o0011).
toilet_suite_A[0].position = [0.35, 0.90, 0.39]
toilet_suite_A[0].rotation = [0, 0, radians(0)]

toilet_suite_B[0].position = [0.35, 2.10, 0.39]
toilet_suite_B[0].rotation = [0, 0, radians(0)]

toilet_suite_C[0].position = [0.35, 3.30, 0.39]
toilet_suite_C[0].rotation = [0, 0, radians(0)]

# Keep the middle toilet equidistant from the two outer toilets so that the
# required A-B-C ordering is maintained.
solver.distance_constraint(
    toilet_suite_B[0], toilet_suite_A[0], 1.20, 1.20, weight=10
)
solver.distance_constraint(
    toilet_suite_B[0], toilet_suite_C[0], 1.20, 1.20, weight=10
)

for toilet_asset, toilet_position in [
    (toilet_suite_A[0], [0.35, 0.90, 0.39]),
    (toilet_suite_B[0], [0.35, 2.10, 0.39]),
    (toilet_suite_C[0], [0.35, 3.30, 0.39]),
]:
    solver.distance_constraint(
        toilet_asset,
        AssetInstance(position=toilet_position),
        0,
        0,
        weight=10,
    )
    solver.against_wall(toilet_asset, walls[3])
    solver.point_towards(
        toilet_asset,
        AssetInstance(position=[2.50, toilet_position[1], 0.39]),
    )

# Put the bench against the south wall, left of the entrance. Its long axis is
# parallel to that wall, and it faces into the room. This leaves the door's
# x=2.69..3.71 opening and the approach in front of it unobstructed.
entry_bench[0].position = [1.20, 0.225, 0.225]
entry_bench[0].rotation = [0, 0, radians(90)]
solver.distance_constraint(
    entry_bench[0],
    AssetInstance(position=[1.20, 0.225, 0.225]),
    0,
    0,
    weight=10,
)
solver.against_wall(entry_bench[0], walls[0])
solver.point_towards(entry_bench[0], north_facing_reference)

# Install the vanity on the east wall, away from both the entrance and the
# north-wall windows. It faces west into the open central aisle.
vanity_counter[0].position = [4.70, 1.50, 0.45]
vanity_counter[0].rotation = [0, 0, radians(180)]
solver.distance_constraint(
    vanity_counter[0],
    AssetInstance(position=[4.70, 1.50, 0.45]),
    0,
    0,
    weight=10,
)
solver.against_wall(vanity_counter[0], walls[1])
solver.point_towards(
    vanity_counter[0], AssetInstance(position=[2.50, 1.50, 0.45])
)

# Mount the mirror above the vanity. Its bottom is at 1.00 m, safely above the
# 0.90 m counter, and it faces west.
mirror_panel[0].position = [4.975, 1.50, 1.45]
mirror_panel[0].rotation = [0, 0, radians(180)]
solver.distance_constraint(
    mirror_panel[0],
    AssetInstance(position=[4.975, 1.50, 1.45]),
    0,
    0,
    weight=10,
)
solver.against_wall(mirror_panel[0], walls[1])
solver.point_towards(
    mirror_panel[0], AssetInstance(position=[2.50, 1.50, 1.45])
)

# Mount the soap/paper-towel dispenser beside the vanity rather than over a
# window or in the entrance circulation zone.
paper_towel_dispenser[0].position = [4.95, 2.35, 1.20]
paper_towel_dispenser[0].rotation = [0, 0, radians(180)]
solver.distance_constraint(
    paper_towel_dispenser[0],
    AssetInstance(position=[4.95, 2.35, 1.20]),
    0,
    0,
    weight=10,
)
solver.against_wall(paper_towel_dispenser[0], walls[1])
solver.point_towards(
    paper_towel_dispenser[0], AssetInstance(position=[2.50, 2.35, 1.20])
)

# Mount one hand dryer near the vanity and another farther north. Both are
# elevated wall fixtures and face west into the room.
hand_dryer_A[0].position = [4.91, 0.45, 1.25]
hand_dryer_A[0].rotation = [0, 0, radians(180)]
solver.distance_constraint(
    hand_dryer_A[0],
    AssetInstance(position=[4.91, 0.45, 1.25]),
    0,
    0,
    weight=10,
)
solver.against_wall(hand_dryer_A[0], walls[1])
solver.point_towards(
    hand_dryer_A[0], AssetInstance(position=[2.50, 0.45, 1.25])
)

hand_dryer_B[0].position = [4.91, 3.05, 1.25]
hand_dryer_B[0].rotation = [0, 0, radians(180)]
solver.distance_constraint(
    hand_dryer_B[0],
    AssetInstance(position=[4.91, 3.05, 1.25]),
    0,
    0,
    weight=10,
)
solver.against_wall(hand_dryer_B[0], walls[1])
solver.point_towards(
    hand_dryer_B[0], AssetInstance(position=[2.50, 3.05, 1.25])
)

# Place both bins along the east wall where they remain accessible without
# narrowing the central circulation route.
waste_bin_B[0].position = [4.725, 2.70, 0.475]
waste_bin_B[0].rotation = [0, 0, radians(180)]
solver.distance_constraint(
    waste_bin_B[0],
    AssetInstance(position=[4.725, 2.70, 0.475]),
    0,
    0,
    weight=10,
)
solver.against_wall(waste_bin_B[0], walls[1])
solver.point_towards(
    waste_bin_B[0], AssetInstance(position=[2.50, 2.70, 0.475])
)

waste_bin_A[0].position = [4.725, 3.48, 0.475]
waste_bin_A[0].rotation = [0, 0, radians(180)]
solver.distance_constraint(
    waste_bin_A[0],
    AssetInstance(position=[4.725, 3.48, 0.475]),
    0,
    0,
    weight=10,
)
solver.against_wall(waste_bin_A[0], walls[1])
solver.point_towards(
    waste_bin_A[0], AssetInstance(position=[2.50, 3.48, 0.475])
)

# Put the cleaning cabinet at the northeast end of the east wall. It does not
# obstruct any north-wall window and is adjacent to waste_bin_A (o0005).
cleaning_cabinet[0].position = [4.775, 4.30, 0.90]
cleaning_cabinet[0].rotation = [0, 0, radians(180)]

# The distance API measures center-to-center distance. For these side-by-side
# objects, 0.89 m equals their combined y half-widths (0.69 m) plus the required
# maximum 0.20 m edge gap. Their specified centers are approximately 0.82 m
# apart, corresponding to an edge gap of about 0.13 m without overlap.
solver.distance_constraint(
    cleaning_cabinet[0], waste_bin_A[0], 0.69, 0.89, weight=10
)
solver.distance_constraint(
    cleaning_cabinet[0],
    AssetInstance(position=[4.775, 4.30, 0.90]),
    0,
    0,
    weight=10,
)
solver.against_wall(cleaning_cabinet[0], walls[1])
solver.point_towards(
    cleaning_cabinet[0], AssetInstance(position=[2.50, 4.30, 0.90])
)

solver.constraints = []
waste_bin_A[0].position = [4.724161148071289, 3.4800000190734863, 0.4749999940395355]
waste_bin_A[0].rotation = [0, 0, 3.1388750342327083]
waste_bin_A[0].optimize = 2
hand_dryer_A[0].position = [4.911225318908691, 0.44999998807907104, 0.2750000059604645]
hand_dryer_A[0].rotation = [0, 0, -3.1405564602419083]
hand_dryer_A[0].optimize = 2
vanity_counter[0].position = [4.69849157333374, 1.5, 0.44999998807907104]
vanity_counter[0].rotation = [0, 0, -3.1405582217522023]
vanity_counter[0].optimize = 2
entry_bench[0].position = [1.2000000476837158, 0.22651861608028412, 0.22499999403953552]
entry_bench[0].rotation = [0, 0, 1.5718314217387388]
entry_bench[0].optimize = 2
hand_dryer_B[0].position = [4.911225318908691, 3.049999952316284, 0.2750000059604645]
hand_dryer_B[0].rotation = [0, 0, -3.1405564602419083]
hand_dryer_B[0].optimize = 2
toilet_suite_B[0].position = [0.34968286752700806, 2.1023995876312256, 0.38999998569488525]
toilet_suite_B[0].rotation = [0, 0, -0.004222738532387275]
toilet_suite_B[0].optimize = 2
paper_towel_dispenser[0].position = [4.952760696411133, 2.3499999046325684, 0.125]
paper_towel_dispenser[0].rotation = [0, 0, -3.1405553852819814]
paper_towel_dispenser[0].optimize = 2
mirror_panel[0].position = [4.973680019378662, 1.5, 0.44999998807907104]
mirror_panel[0].rotation = [0, 0, -3.1405558173007964]
mirror_panel[0].optimize = 2
toilet_suite_C[0].position = [0.35008350014686584, 3.299999952316284, 0.38999998569488525]
toilet_suite_C[0].rotation = [0, 0, -0.0027188451595564042]
toilet_suite_C[0].optimize = 2
waste_bin_B[0].position = [4.725910186767578, 2.700000047683716, 0.4749999940395355]
waste_bin_B[0].rotation = [0, 0, -3.140558596377268]
waste_bin_B[0].optimize = 2
cleaning_cabinet[0].position = [4.77363920211792, 4.300000190734863, 0.8999999761581421]
cleaning_cabinet[0].rotation = [0, 0, 3.138876173512724]
cleaning_cabinet[0].optimize = 2
toilet_suite_A[0].position = [0.35008350014686584, 0.8999999761581421, 0.38999998569488525]
toilet_suite_A[0].rotation = [0, 0, -0.0027188451595564042]
toilet_suite_A[0].optimize = 2

