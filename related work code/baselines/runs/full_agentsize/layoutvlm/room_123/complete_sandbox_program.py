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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.00, 0.00, 0.00]),
    Wall(corner1=[3.00, 0.00, 0.00], corner2=[3.00, 5.00, 0.00]),
    Wall(corner1=[3.00, 5.00, 0.00], corner2=[0.00, 5.00, 0.00]),
    Wall(corner1=[0.00, 5.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
mobile_clean_supply_cart_A = Assets(description="A hospital cart with a set of clear drawers, iv pole and a red biohazard disposal container.", size=[0.55, 0.62, 1.75], placements=[AssetInstance() for _ in range(1)])
mop_and_broom_wall_rack = Assets(description="A wooden coat hanger with gold hooks.", size=[0.10, 0.90, 0.18], placements=[AssetInstance() for _ in range(1)])
wall_notice_board = Assets(description="A poster of blueprints for a picture frame.", size=[0.04, 0.85, 0.60], placements=[AssetInstance() for _ in range(1)])
mobile_clean_supply_cart_B = Assets(description="A hospital cart with a set of clear drawers, iv pole and a red biohazard disposal container.", size=[0.55, 0.62, 1.75], placements=[AssetInstance() for _ in range(1)])
cleaning_work_counter = Assets(description="A light brown colored shelf unit with blue crates.", size=[0.55, 1.20, 0.95], placements=[AssetInstance() for _ in range(1)])
utility_sink_cabinet = Assets(description="A kitchen sink with a wood cabinet.", size=[0.62, 1.00, 0.90], placements=[AssetInstance() for _ in range(1)])
clean_linen_cart = Assets(description="a blue three-tier cart with two bins and wheels.", size=[0.52, 0.85, 1.00], placements=[AssetInstance() for _ in range(1)])
tall_clean_storage_cabinet_A = Assets(description="Two stacked locker units that are yellow and gray.", size=[0.50, 0.90, 1.90], placements=[AssetInstance() for _ in range(1)])
hand_soap_dispenser_bottle = Assets(description="White soap bottle model", size=[0.06, 0.08, 0.20], placements=[AssetInstance() for _ in range(1)])
tall_clean_storage_cabinet_B = Assets(description="Two stacked locker units that are yellow and gray.", size=[0.50, 0.90, 1.90], placements=[AssetInstance() for _ in range(1)])
open_wall_shelf_unit = Assets(description="A purple set of shelves with green and purple shelving.", size=[0.30, 1.10, 0.90], placements=[AssetInstance() for _ in range(1)])

mobile_clean_supply_cart_A[0].instance_id = 'mobile_clean_supply_cart_A_0'
mop_and_broom_wall_rack[0].instance_id = 'mop_and_broom_wall_rack_0'
wall_notice_board[0].instance_id = 'wall_notice_board_0'
mobile_clean_supply_cart_B[0].instance_id = 'mobile_clean_supply_cart_B_0'
cleaning_work_counter[0].instance_id = 'cleaning_work_counter_0'
utility_sink_cabinet[0].instance_id = 'utility_sink_cabinet_0'
clean_linen_cart[0].instance_id = 'clean_linen_cart_0'
tall_clean_storage_cabinet_A[0].instance_id = 'tall_clean_storage_cabinet_A_0'
hand_soap_dispenser_bottle[0].instance_id = 'hand_soap_dispenser_bottle_0'
tall_clean_storage_cabinet_B[0].instance_id = 'tall_clean_storage_cabinet_B_0'
open_wall_shelf_unit[0].instance_id = 'open_wall_shelf_unit_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

mobile_clean_supply_cart_A[0].position = [0.8872938469949344, 4.774885160968905, 0.875]
mobile_clean_supply_cart_A[0].rotation = [0, 0, 0]
mop_and_broom_wall_rack[0].position = [2.2395584823385786, 3.434521227690927, 0.09]
mop_and_broom_wall_rack[0].rotation = [0, 0, 0]
wall_notice_board[0].position = [0.6709193075496684, 0.3046156045504028, 0.3]
wall_notice_board[0].rotation = [0, 0, 0]
mobile_clean_supply_cart_B[0].position = [2.0675834987844737, 1.1973903454959918, 0.875]
mobile_clean_supply_cart_B[0].rotation = [0, 0, 0]
cleaning_work_counter[0].position = [0.7113540969136226, 1.339759715621035, 0.475]
cleaning_work_counter[0].rotation = [0, 0, 0]
utility_sink_cabinet[0].position = [0.7509374446493751, 0.017116218070818978, 0.45]
utility_sink_cabinet[0].rotation = [0, 0, 0]
clean_linen_cart[0].position = [1.9171793838357343, 0.7089000624654579, 0.5]
clean_linen_cart[0].rotation = [0, 0, 0]
tall_clean_storage_cabinet_A[0].position = [0.7010658590226139, 3.5065056181185876, 0.95]
tall_clean_storage_cabinet_A[0].rotation = [0, 0, 0]
hand_soap_dispenser_bottle[0].position = [2.229182813810753, 3.1451610635226706, 0.1]
hand_soap_dispenser_bottle[0].rotation = [0, 0, 0]
tall_clean_storage_cabinet_B[0].position = [0.49247229879819066, 1.23972433675814, 0.95]
tall_clean_storage_cabinet_B[0].rotation = [0, 0, 0]
open_wall_shelf_unit[0].position = [1.8964055337726582, 1.0664819727074337, 0.45]
open_wall_shelf_unit[0].rotation = [0, 0, 0]
mobile_clean_supply_cart_A[0].position = [0.8872938469949344, 4.774885160968905, 0.875]
mobile_clean_supply_cart_A[0].rotation = [0, 0, 0]
mop_and_broom_wall_rack[0].position = [2.2395584823385786, 3.434521227690927, 0.09]
mop_and_broom_wall_rack[0].rotation = [0, 0, 0]
wall_notice_board[0].position = [0.6709193075496684, 0.3046156045504028, 0.3]
wall_notice_board[0].rotation = [0, 0, 0]
mobile_clean_supply_cart_B[0].position = [2.0675834987844737, 1.1973903454959918, 0.875]
mobile_clean_supply_cart_B[0].rotation = [0, 0, 0]
cleaning_work_counter[0].position = [0.7113540969136226, 1.339759715621035, 0.475]
cleaning_work_counter[0].rotation = [0, 0, 0]
utility_sink_cabinet[0].position = [0.7509374446493751, 0.017116218070818978, 0.45]
utility_sink_cabinet[0].rotation = [0, 0, 0]
clean_linen_cart[0].position = [1.9171793838357343, 0.7089000624654579, 0.5]
clean_linen_cart[0].rotation = [0, 0, 0]
tall_clean_storage_cabinet_A[0].position = [0.7010658590226139, 3.5065056181185876, 0.95]
tall_clean_storage_cabinet_A[0].rotation = [0, 0, 0]
hand_soap_dispenser_bottle[0].position = [2.229182813810753, 3.1451610635226706, 0.1]
hand_soap_dispenser_bottle[0].rotation = [0, 0, 0]
tall_clean_storage_cabinet_B[0].position = [0.49247229879819066, 1.23972433675814, 0.95]
tall_clean_storage_cabinet_B[0].rotation = [0, 0, 0]
open_wall_shelf_unit[0].position = [1.8964055337726582, 1.0664819727074337, 0.45]
open_wall_shelf_unit[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed reference points used to preserve the intended locations and orientations.
room_center = AssetInstance(position=[1.50, 2.50, 1.00])
cart_A_anchor = AssetInstance(position=[1.25, 0.275, 0.875])
cart_B_anchor = AssetInstance(position=[2.07, 0.275, 0.875])
linen_anchor = AssetInstance(position=[2.75, 2.725, 0.50])
soap_anchor = AssetInstance(position=[0.20, 0.70, 1.00])

# Floor-standing assets are set at half their heights. The central aisle and
# the approach to the door at (1.16, 5.00) are intentionally left unobstructed.
mobile_clean_supply_cart_A[0].position = [1.25, 0.275, 0.875]
mobile_clean_supply_cart_A[0].rotation = [0, 0, radians(90)]

mobile_clean_supply_cart_B[0].position = [2.07, 0.275, 0.875]
mobile_clean_supply_cart_B[0].rotation = [0, 0, radians(90)]

utility_sink_cabinet[0].position = [0.31, 0.55, 0.45]
utility_sink_cabinet[0].rotation = [0, 0, radians(0)]

cleaning_work_counter[0].position = [0.275, 1.75, 0.475]
cleaning_work_counter[0].rotation = [0, 0, radians(0)]

open_wall_shelf_unit[0].position = [0.15, 3.05, 0.45]
open_wall_shelf_unit[0].rotation = [0, 0, radians(0)]

tall_clean_storage_cabinet_A[0].position = [2.75, 0.55, 0.95]
tall_clean_storage_cabinet_A[0].rotation = [0, 0, radians(180)]

tall_clean_storage_cabinet_B[0].position = [2.75, 1.65, 0.95]
tall_clean_storage_cabinet_B[0].rotation = [0, 0, radians(180)]

# This cart is beside cabinet B with 0.20 m of horizontal clearance between
# their bounding boxes.
clean_linen_cart[0].position = [2.75, 2.725, 0.50]
clean_linen_cart[0].rotation = [0, 0, radians(180)]

# Wall-mounted items are raised above the floor. The notice board is to the
# right of the doorway, while the narrow rack is above the work-counter area.
mop_and_broom_wall_rack[0].position = [0.05, 2.00, 1.45]
mop_and_broom_wall_rack[0].rotation = [0, 0, radians(0)]

wall_notice_board[0].position = [2.40, 4.98, 1.50]
wall_notice_board[0].rotation = [0, 0, radians(-90)]

# Place the small bottle on the sink's upper surface and away from its edges.
hand_soap_dispenser_bottle[0].position = [0.20, 0.70, 1.00]
hand_soap_dispenser_bottle[0].rotation = [0, 0, radians(0)]


# --- Required proximity relationships (listed first because they are important) ---

# The carts have equal heights. At 0.82 m center separation, their rotated
# 0.62 m-wide footprints have 0.20 m clear space, satisfying the 0.30 m limit.
solver.distance_constraint(
    mobile_clean_supply_cart_A[0],
    mobile_clean_supply_cart_B[0],
    0.62,
    0.92,
    weight=10,
)

# Cabinet B is the tall cabinet assigned to the linen-cart station. The
# center-distance limit accounts for their half-widths, the allowed 0.20 m
# horizontal gap, and the 0.45 m difference between their center heights.
solver.distance_constraint(
    clean_linen_cart[0],
    tall_clean_storage_cabinet_B[0],
    0.98,
    1.17,
    weight=10,
)


# --- Position constraints for floor-standing and wall-mounted assets ---

solver.distance_constraint(
    mobile_clean_supply_cart_A[0], cart_A_anchor, 0.0, 0.0, weight=10
)
solver.distance_constraint(
    mobile_clean_supply_cart_B[0], cart_B_anchor, 0.0, 0.0, weight=10
)

solver.against_wall(utility_sink_cabinet[0], walls[3])
solver.against_wall(cleaning_work_counter[0], walls[3])
solver.against_wall(open_wall_shelf_unit[0], walls[3])

solver.against_wall(tall_clean_storage_cabinet_A[0], walls[1])
solver.against_wall(tall_clean_storage_cabinet_B[0], walls[1])
solver.distance_constraint(
    clean_linen_cart[0], linen_anchor, 0.0, 0.0, weight=10
)

solver.against_wall(mop_and_broom_wall_rack[0], walls[3])
solver.against_wall(wall_notice_board[0], walls[2])

# The soap bottle needs both a support constraint and a position-based
# constraint; the anchor preserves its offset on the sink countertop.
solver.on_top_of(hand_soap_dispenser_bottle[0], utility_sink_cabinet[0])
solver.distance_constraint(
    hand_soap_dispenser_bottle[0], soap_anchor, 0.0, 0.0, weight=10
)


# --- Orientation constraints for every new asset ---

# The carts face into the room from the bottom wall.
solver.point_towards(mobile_clean_supply_cart_A[0], room_center)
solver.align_with(
    mobile_clean_supply_cart_B[0], mobile_clean_supply_cart_A[0], angle=0
)

# Left-wall fixtures face toward +x, into the room.
solver.point_towards(utility_sink_cabinet[0], room_center)
solver.align_with(
    cleaning_work_counter[0], utility_sink_cabinet[0], angle=0
)
solver.align_with(
    open_wall_shelf_unit[0], utility_sink_cabinet[0], angle=0
)
solver.align_with(
    mop_and_broom_wall_rack[0], utility_sink_cabinet[0], angle=0
)

# Right-wall storage and the linen cart face toward -x, into the room.
solver.point_towards(tall_clean_storage_cabinet_A[0], room_center)
solver.align_with(
    tall_clean_storage_cabinet_B[0],
    tall_clean_storage_cabinet_A[0],
    angle=0,
)
solver.align_with(
    clean_linen_cart[0], tall_clean_storage_cabinet_B[0], angle=0
)

# The top-wall notice board faces into the room, and the bottle follows the
# orientation of the sink on which it is placed.
solver.point_towards(wall_notice_board[0], room_center)
solver.align_with(
    hand_soap_dispenser_bottle[0], utility_sink_cabinet[0], angle=0
)

solver.constraints = []
hand_soap_dispenser_bottle[0].position = [0.20000000298023224, 0.699999988079071, 1.0]
hand_soap_dispenser_bottle[0].rotation = [0, 0, -0.0009047892746606243]
hand_soap_dispenser_bottle[0].optimize = 2
utility_sink_cabinet[0].position = [0.3100009262561798, 0.550000011920929, 0.44999998807907104]
utility_sink_cabinet[0].rotation = [0, 0, 0.00043986333479544877]
utility_sink_cabinet[0].optimize = 2
clean_linen_cart[0].position = [2.734679937362671, 2.7249999046325684, 0.5]
clean_linen_cart[0].rotation = [0, 0, -3.1411385127303593]
clean_linen_cart[0].optimize = 2
mobile_clean_supply_cart_B[0].position = [2.069999933242798, 0.2750000059604645, 0.875]
mobile_clean_supply_cart_B[0].rotation = [0, 0, 1.5865407164161895]
mobile_clean_supply_cart_B[0].optimize = 2
tall_clean_storage_cabinet_A[0].position = [2.749937057495117, 0.550000011920929, 0.949999988079071]
tall_clean_storage_cabinet_A[0].rotation = [0, 0, 3.141530874775766]
tall_clean_storage_cabinet_A[0].optimize = 2
tall_clean_storage_cabinet_B[0].position = [2.749885320663452, 1.649999976158142, 0.949999988079071]
tall_clean_storage_cabinet_B[0].rotation = [0, 0, -3.1414102928917087]
tall_clean_storage_cabinet_B[0].optimize = 2
open_wall_shelf_unit[0].position = [0.1500091701745987, 3.049999952316284, 0.44999998807907104]
open_wall_shelf_unit[0].rotation = [0, 0, -0.00018172326873627345]
open_wall_shelf_unit[0].optimize = 2
mobile_clean_supply_cart_A[0].position = [1.25, 0.2750000059604645, 0.875]
mobile_clean_supply_cart_A[0].rotation = [0, 0, 1.586504290712113]
mobile_clean_supply_cart_A[0].optimize = 2
wall_notice_board[0].position = [2.4000000953674316, 4.979874134063721, 0.30000001192092896]
wall_notice_board[0].rotation = [0, 0, -1.5709782193577269]
wall_notice_board[0].optimize = 2
cleaning_work_counter[0].position = [0.2751022279262543, 1.75, 0.4749999940395355]
cleaning_work_counter[0].rotation = [0, 0, -0.00018173139004178712]
cleaning_work_counter[0].optimize = 2
mop_and_broom_wall_rack[0].position = [0.04978743940591812, 2.0, 0.09000000357627869]
mop_and_broom_wall_rack[0].rotation = [0, 0, -0.00018180241889543587]
mop_and_broom_wall_rack[0].optimize = 2

