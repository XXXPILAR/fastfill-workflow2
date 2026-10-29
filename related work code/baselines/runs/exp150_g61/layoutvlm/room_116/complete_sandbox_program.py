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
    Wall(corner1=[0.00, 4.00, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.00, 0.00, 0.00]),
    Wall(corner1=[4.00, 0.00, 0.00], corner2=[4.00, 6.00, 0.00]),
    Wall(corner1=[4.00, 6.00, 0.00], corner2=[1.00, 6.00, 0.00]),
    Wall(corner1=[1.00, 6.00, 0.00], corner2=[1.00, 4.00, 0.00]),
    Wall(corner1=[1.00, 4.00, 0.00], corner2=[0.00, 4.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
pantry_notice_board = Assets(description="A chalk billboard with some prices on it.", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
hand_dryer_unit_A = Assets(description="A hand dryer for a bathroom.", size=[0.18, 0.30, 0.35], placements=[AssetInstance() for _ in range(1)])
liquid_soap_dispenser = Assets(description="White soap bottle model", size=[0.08, 0.09, 0.20], placements=[AssetInstance() for _ in range(1)])
restroom_wall_shelf = Assets(description="A set of radiator pipes that are bolted into the wall.", size=[0.12, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
restroom_mirror_panel = Assets(description="A poster of blueprints for a picture frame.", size=[0.03, 1.20, 0.80], placements=[AssetInstance() for _ in range(1)])
toilet_suite_A = Assets(description="toilet suite", size=[0.70, 0.40, 0.80], placements=[AssetInstance() for _ in range(1)])
pantry_open_shelf = Assets(description="A purple set of shelves with green and purple shelving.", size=[0.30, 0.80, 0.75], placements=[AssetInstance() for _ in range(1)])
pantry_wall_cabinet = Assets(description="A tall slim cupboard with four shelves in it.", size=[0.35, 0.45, 1.20], placements=[AssetInstance() for _ in range(1)])
toilet_suite_B = Assets(description="toilet suite", size=[0.70, 0.40, 0.80], placements=[AssetInstance() for _ in range(1)])
toilet_suite_C = Assets(description="toilet suite", size=[0.70, 0.40, 0.80], placements=[AssetInstance() for _ in range(1)])
pantry_base_cabinet = Assets(description="Wood cabinet with three doors and three drawers above.", size=[0.60, 1.50, 0.90], placements=[AssetInstance() for _ in range(1)])
hand_dryer_unit_B = Assets(description="A hand dryer for a bathroom.", size=[0.18, 0.30, 0.35], placements=[AssetInstance() for _ in range(1)])
restroom_vanity_counter = Assets(description="A long standing desk with two computer monitors on it and a plant.", size=[0.60, 1.60, 0.85], placements=[AssetInstance() for _ in range(1)])
pantry_undercounter_fridge = Assets(description="pantry undercounter fridge", size=[0.60, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])

pantry_notice_board[0].instance_id = 'pantry_notice_board_0'
hand_dryer_unit_A[0].instance_id = 'hand_dryer_unit_A_0'
liquid_soap_dispenser[0].instance_id = 'liquid_soap_dispenser_0'
restroom_wall_shelf[0].instance_id = 'restroom_wall_shelf_0'
restroom_mirror_panel[0].instance_id = 'restroom_mirror_panel_0'
toilet_suite_A[0].instance_id = 'toilet_suite_A_0'
pantry_open_shelf[0].instance_id = 'pantry_open_shelf_0'
pantry_wall_cabinet[0].instance_id = 'pantry_wall_cabinet_0'
toilet_suite_B[0].instance_id = 'toilet_suite_B_0'
toilet_suite_C[0].instance_id = 'toilet_suite_C_0'
pantry_base_cabinet[0].instance_id = 'pantry_base_cabinet_0'
hand_dryer_unit_B[0].instance_id = 'hand_dryer_unit_B_0'
restroom_vanity_counter[0].instance_id = 'restroom_vanity_counter_0'
pantry_undercounter_fridge[0].instance_id = 'pantry_undercounter_fridge_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

pantry_notice_board[0].position = [2.163366832637244, 2.0659723327823514, 0.4]
pantry_notice_board[0].rotation = [0, 0, 0]
hand_dryer_unit_A[0].position = [0.43561892254182766, 2.940394190254202, 0.175]
hand_dryer_unit_A[0].rotation = [0, 0, 0]
liquid_soap_dispenser[0].position = [3.560068254687803, 0.8017629936494863, 0.1]
liquid_soap_dispenser[0].rotation = [0, 0, 0]
restroom_wall_shelf[0].position = [3.0188236118586125, 2.4480878469494716, 0.4]
restroom_wall_shelf[0].rotation = [0, 0, 0]
restroom_mirror_panel[0].position = [1.2243047564780003, 4.318577316884897, 0.4]
restroom_mirror_panel[0].rotation = [0, 0, 0]
toilet_suite_A[0].position = [2.159372287675998, 2.110127839687067, 0.4]
toilet_suite_A[0].rotation = [0, 0, 0]
pantry_open_shelf[0].position = [2.831370420388304, 5.4105904975856145, 0.375]
pantry_open_shelf[0].rotation = [0, 0, 0]
pantry_wall_cabinet[0].position = [1.3105707581851167, 2.9990303251598887, 0.6]
pantry_wall_cabinet[0].rotation = [0, 0, 0]
toilet_suite_B[0].position = [0.9096888741377676, 0.5329992343433358, 0.4]
toilet_suite_B[0].rotation = [0, 0, 0]
toilet_suite_C[0].position = [3.9081768614367514, 2.0562981705866648, 0.4]
toilet_suite_C[0].rotation = [0, 0, 0]
pantry_base_cabinet[0].position = [0.9269222114015108, 1.0855023974219966, 0.45]
pantry_base_cabinet[0].rotation = [0, 0, 0]
hand_dryer_unit_B[0].position = [1.9347298330127876, 2.4780189581385152, 0.175]
hand_dryer_unit_B[0].rotation = [0, 0, 0]
restroom_vanity_counter[0].position = [0.036168677679123906, 1.909669497891763, 0.425]
restroom_vanity_counter[0].rotation = [0, 0, 0]
pantry_undercounter_fridge[0].position = [2.8576415844730816, 0.9140332020967759, 0.425]
pantry_undercounter_fridge[0].rotation = [0, 0, 0]
pantry_notice_board[0].position = [2.163366832637244, 2.0659723327823514, 0.4]
pantry_notice_board[0].rotation = [0, 0, 0]
hand_dryer_unit_A[0].position = [0.43561892254182766, 2.940394190254202, 0.175]
hand_dryer_unit_A[0].rotation = [0, 0, 0]
liquid_soap_dispenser[0].position = [3.560068254687803, 0.8017629936494863, 0.1]
liquid_soap_dispenser[0].rotation = [0, 0, 0]
restroom_wall_shelf[0].position = [3.0188236118586125, 2.4480878469494716, 0.4]
restroom_wall_shelf[0].rotation = [0, 0, 0]
restroom_mirror_panel[0].position = [1.2243047564780003, 4.318577316884897, 0.4]
restroom_mirror_panel[0].rotation = [0, 0, 0]
toilet_suite_A[0].position = [2.159372287675998, 2.110127839687067, 0.4]
toilet_suite_A[0].rotation = [0, 0, 0]
pantry_open_shelf[0].position = [2.831370420388304, 5.4105904975856145, 0.375]
pantry_open_shelf[0].rotation = [0, 0, 0]
pantry_wall_cabinet[0].position = [1.3105707581851167, 2.9990303251598887, 0.6]
pantry_wall_cabinet[0].rotation = [0, 0, 0]
toilet_suite_B[0].position = [0.9096888741377676, 0.5329992343433358, 0.4]
toilet_suite_B[0].rotation = [0, 0, 0]
toilet_suite_C[0].position = [3.9081768614367514, 2.0562981705866648, 0.4]
toilet_suite_C[0].rotation = [0, 0, 0]
pantry_base_cabinet[0].position = [0.9269222114015108, 1.0855023974219966, 0.45]
pantry_base_cabinet[0].rotation = [0, 0, 0]
hand_dryer_unit_B[0].position = [1.9347298330127876, 2.4780189581385152, 0.175]
hand_dryer_unit_B[0].rotation = [0, 0, 0]
restroom_vanity_counter[0].position = [0.036168677679123906, 1.909669497891763, 0.425]
restroom_vanity_counter[0].rotation = [0, 0, 0]
pantry_undercounter_fridge[0].position = [2.8576415844730816, 0.9140332020967759, 0.425]
pantry_undercounter_fridge[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the actual boundary coordinates: the entrance is on y=0 and
# the window wall is x=4. Keep the entrance approach and window wall clear.
# The three toilet suites occupy the rear wall, with A between B and C.
# Each tuple specifies asset, center position, facing angle, and backing wall.
layout_specs = [
    (toilet_suite_B, [1.60, 5.65, 0.40], -90, 3),
    (toilet_suite_A, [2.50, 5.65, 0.40], -90, 3),
    (toilet_suite_C, [3.40, 5.65, 0.40], -90, 3),

    # West-wall vanity, with an elevated mirror above its work surface.
    (restroom_vanity_counter, [0.30, 3.00, 0.425], 0, 0),
    (restroom_mirror_panel, [0.015, 3.00, 1.55], 0, 0),

    # Storage starts beyond the entrance approach.
    (pantry_open_shelf, [0.15, 1.60, 0.375], 0, 0),

    # Pantry work zone along the south wall, east of the door.
    (pantry_base_cabinet, [2.50, 0.30, 0.45], 90, 1),
    (pantry_undercounter_fridge, [3.60, 0.30, 0.425], 90, 1),
    (pantry_notice_board, [2.50, 0.02, 1.65], 90, 1),

    # Upper-left return wall: separate the cabinet and wall-mounted fixtures.
    (pantry_wall_cabinet, [1.175, 4.70, 0.60], 0, 4),
    (restroom_wall_shelf, [1.06, 5.40, 1.20], 0, 4),
    (hand_dryer_unit_B, [1.09, 4.20, 1.25], 0, 4),

    # Accessible dryer between the open shelving and vanity.
    (hand_dryer_unit_A, [0.09, 2.00, 1.25], 0, 0),
]

for asset_ref, center, facing_degrees, wall_index in layout_specs:
    asset_ref[0].position = center
    asset_ref[0].rotation = [0, 0, radians(facing_degrees)]

    # Wall contact is the primary positional requirement.
    solver.against_wall(asset_ref[0], walls[wall_index])

    # Fixed center targets preserve spacing, wall-mounting heights, and the
    # unobstructed entrance route. These are reference points, not new objects.
    solver.distance_constraint(
        asset_ref[0],
        AssetInstance(position=list(center)),
        0, 0, weight=10,
    )
    solver.align_with(
        asset_ref[0],
        AssetInstance(rotation=[0, 0, radians(facing_degrees)]),
        angle=0,
    )

# Soap belongs on the vanity, rather than on the floor.
liquid_soap_dispenser[0].position = [0.35, 2.75, 0.95]
liquid_soap_dispenser[0].rotation = [0, 0, 0]
solver.on_top_of(liquid_soap_dispenser[0], restroom_vanity_counter[0])
solver.distance_constraint(
    liquid_soap_dispenser[0],
    AssetInstance(position=[0.35, 2.75, 0.95]),
    0, 0, weight=10,
)
solver.align_with(
    liquid_soap_dispenser[0], restroom_vanity_counter[0], angle=0
)

# Preserve the evenly spaced toilet row. Together with the center targets,
# these relationships keep A between B and C, all facing into the room.
solver.distance_constraint(
    toilet_suite_A[0], toilet_suite_B[0], 0.90, 0.90, weight=10
)
solver.distance_constraint(
    toilet_suite_A[0], toilet_suite_C[0], 0.90, 0.90, weight=10
)
solver.distance_constraint(
    toilet_suite_C[0], toilet_suite_B[0], 1.80, 1.80, weight=10
)
solver.align_with(toilet_suite_A[0], toilet_suite_B[0])
solver.align_with(toilet_suite_C[0], toilet_suite_B[0])

solver.constraints = []
restroom_mirror_panel[0].position = [0.006743620149791241, 3.0, 0.4000000059604645]
restroom_mirror_panel[0].rotation = [0, 0, 0.0025409114179187954]
restroom_mirror_panel[0].optimize = 2
hand_dryer_unit_B[0].position = [1.0903809070587158, 4.199999809265137, 0.17499999701976776]
hand_dryer_unit_B[0].rotation = [0, 0, 0.0025409215170312644]
hand_dryer_unit_B[0].optimize = 2
hand_dryer_unit_A[0].position = [0.09038085490465164, 2.0, 0.17499999701976776]
hand_dryer_unit_A[0].rotation = [0, 0, 0.0025409215170312644]
hand_dryer_unit_A[0].optimize = 2
restroom_vanity_counter[0].position = [0.3050256371498108, 3.0, 0.42500001192092896]
restroom_vanity_counter[0].rotation = [0, 0, 0.008762208630975439]
restroom_vanity_counter[0].optimize = 2
toilet_suite_B[0].position = [1.600000023841858, 5.647042751312256, 0.4000000059604645]
toilet_suite_B[0].rotation = [0, 0, -1.5558124089525998]
toilet_suite_B[0].optimize = 2
pantry_open_shelf[0].position = [0.15101589262485504, 1.600000023841858, 0.375]
pantry_open_shelf[0].rotation = [0, 0, 0.002540916928559797]
pantry_open_shelf[0].optimize = 2
pantry_wall_cabinet[0].position = [1.1755712032318115, 4.699999809265137, 0.6000000238418579]
pantry_wall_cabinet[0].rotation = [0, 0, 0.0025409202949315235]
pantry_wall_cabinet[0].optimize = 2
toilet_suite_A[0].position = [2.5, 5.647650241851807, 0.4000000059604645]
toilet_suite_A[0].rotation = [0, 0, -1.5589233055561824]
toilet_suite_A[0].optimize = 2
restroom_wall_shelf[0].position = [1.0607621669769287, 5.400000095367432, 0.4000000059604645]
restroom_wall_shelf[0].rotation = [0, 0, 0.0025409193727581954]
restroom_wall_shelf[0].optimize = 2
pantry_base_cabinet[0].position = [2.5, 0.30190473794937134, 0.44999998807907104]
pantry_base_cabinet[0].rotation = [0, 0, 1.5733372317800058]
pantry_base_cabinet[0].optimize = 2
pantry_undercounter_fridge[0].position = [3.5999999046325684, 0.300761342048645, 0.42500001192092896]
pantry_undercounter_fridge[0].rotation = [0, 0, 1.5733372452454815]
pantry_undercounter_fridge[0].optimize = 2
liquid_soap_dispenser[0].position = [0.3499999940395355, 2.75, 0.9500000476837158]
liquid_soap_dispenser[0].rotation = [0, 0, 0.02278736617577962]
liquid_soap_dispenser[0].optimize = 2
pantry_notice_board[0].position = [2.5, 0.011367769911885262, 0.4000000059604645]
pantry_notice_board[0].rotation = [0, 0, 1.573337246167655]
pantry_notice_board[0].optimize = 2
toilet_suite_C[0].position = [3.4000000953674316, 5.647650241851807, 0.4000000059604645]
toilet_suite_C[0].rotation = [0, 0, -1.5589233055561824]
toilet_suite_C[0].optimize = 2

