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
    Wall(corner1=[4.00, 6.00, 0.00], corner2=[4.00, 3.00, 0.00]),
    Wall(corner1=[4.00, 3.00, 0.00], corner2=[0.00, 3.00, 0.00]),
    Wall(corner1=[0.00, 3.00, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.00, 0.00, 0.00]),
    Wall(corner1=[6.00, 0.00, 0.00], corner2=[6.00, 2.00, 0.00]),
    Wall(corner1=[6.00, 2.00, 0.00], corner2=[7.00, 2.00, 0.00]),
    Wall(corner1=[7.00, 2.00, 0.00], corner2=[7.00, 6.00, 0.00]),
    Wall(corner1=[7.00, 6.00, 0.00], corner2=[4.00, 6.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
toilet_suite_A = Assets(description="toilet suite", size=[0.70, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
number_label = Assets(description="number label", size=[0.01, 0.10, 0.06], placements=[AssetInstance() for _ in range(1)])
waste_bin_floor_A = Assets(description="waste bin floor", size=[0.25, 0.30, 0.45], placements=[AssetInstance() for _ in range(1)])
vanity_counter = Assets(description="vanity counter", size=[0.60, 1.80, 0.90], placements=[AssetInstance() for _ in range(1)])
waste_bin_floor_B = Assets(description="waste bin floor", size=[0.25, 0.30, 0.45], placements=[AssetInstance() for _ in range(1)])
hand_dryer_A = Assets(description="White smart speaker with two mounting brackets.", size=[0.20, 0.30, 0.35], placements=[AssetInstance() for _ in range(1)])
toilet_suite_B = Assets(description="toilet suite", size=[0.70, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
vanity_mirror = Assets(description="A square mirror in a carved wooden frame.", size=[0.06, 0.80, 0.80], placements=[AssetInstance() for _ in range(1)])
wall_shelf_A = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.22, 0.80, 0.25], placements=[AssetInstance() for _ in range(1)])
shelf_accessories = Assets(description="shelf accessories", size=[0.25, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])
wall_shelf_B = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.22, 0.80, 0.25], placements=[AssetInstance() for _ in range(1)])
label_holder = Assets(description="label holder", size=[0.02, 0.12, 0.05], placements=[AssetInstance() for _ in range(1)])
small_potted_plant_A = Assets(description="small potted plant", size=[0.20, 0.20, 0.30], placements=[AssetInstance() for _ in range(1)])
informational_sign_A = Assets(description="A card with an animal.", size=[0.02, 0.30, 0.40], placements=[AssetInstance() for _ in range(1)])
small_potted_plant_B = Assets(description="small potted plant", size=[0.20, 0.20, 0.30], placements=[AssetInstance() for _ in range(1)])
informational_sign_B = Assets(description="A card with an animal.", size=[0.02, 0.30, 0.40], placements=[AssetInstance() for _ in range(1)])
hand_dryer_B = Assets(description="White smart speaker with two mounting brackets.", size=[0.20, 0.30, 0.35], placements=[AssetInstance() for _ in range(1)])
waste_bin_floor_C = Assets(description="waste bin floor", size=[0.25, 0.30, 0.45], placements=[AssetInstance() for _ in range(1)])
locker_column = Assets(description="locker column", size=[0.50, 0.45, 1.90], placements=[AssetInstance() for _ in range(1)])
cleaning_supply_cabinet = Assets(description="cleaning supply cabinet", size=[0.50, 0.80, 1.90], placements=[AssetInstance() for _ in range(1)])
toilet_suite_C = Assets(description="toilet suite", size=[0.70, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])

toilet_suite_A[0].instance_id = 'toilet_suite_A_0'
number_label[0].instance_id = 'number_label_0'
waste_bin_floor_A[0].instance_id = 'waste_bin_floor_A_0'
vanity_counter[0].instance_id = 'vanity_counter_0'
waste_bin_floor_B[0].instance_id = 'waste_bin_floor_B_0'
hand_dryer_A[0].instance_id = 'hand_dryer_A_0'
toilet_suite_B[0].instance_id = 'toilet_suite_B_0'
vanity_mirror[0].instance_id = 'vanity_mirror_0'
wall_shelf_A[0].instance_id = 'wall_shelf_A_0'
shelf_accessories[0].instance_id = 'shelf_accessories_0'
wall_shelf_B[0].instance_id = 'wall_shelf_B_0'
label_holder[0].instance_id = 'label_holder_0'
small_potted_plant_A[0].instance_id = 'small_potted_plant_A_0'
informational_sign_A[0].instance_id = 'informational_sign_A_0'
small_potted_plant_B[0].instance_id = 'small_potted_plant_B_0'
informational_sign_B[0].instance_id = 'informational_sign_B_0'
hand_dryer_B[0].instance_id = 'hand_dryer_B_0'
waste_bin_floor_C[0].instance_id = 'waste_bin_floor_C_0'
locker_column[0].instance_id = 'locker_column_0'
cleaning_supply_cabinet[0].instance_id = 'cleaning_supply_cabinet_0'
toilet_suite_C[0].instance_id = 'toilet_suite_C_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

toilet_suite_A[0].position = [4.332875125362597, 2.644429908483212, 0.39]
toilet_suite_A[0].rotation = [0, 0, 0]
number_label[0].position = [4.115397239295929, 4.4588408780041275, 0.03]
number_label[0].rotation = [0, 0, 0]
waste_bin_floor_A[0].position = [1.3171588724937582, 1.1931010869014207, 0.225]
waste_bin_floor_A[0].rotation = [0, 0, 0]
vanity_counter[0].position = [4.862959208248193, 5.045989380966487, 0.45]
vanity_counter[0].rotation = [0, 0, 0]
waste_bin_floor_B[0].position = [4.330604371806891, 4.853912746057983, 0.225]
waste_bin_floor_B[0].rotation = [0, 0, 0]
hand_dryer_A[0].position = [2.029646206361879, 1.7755232819948663, 0.175]
hand_dryer_A[0].rotation = [0, 0, 0]
toilet_suite_B[0].position = [4.831376347903763, 1.9350055387898168, 0.39]
toilet_suite_B[0].rotation = [0, 0, 0]
vanity_mirror[0].position = [5.034167633892372, 1.94420283174437, 0.4]
vanity_mirror[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [2.8208691625760425, 2.5287120790972897, 0.125]
wall_shelf_A[0].rotation = [0, 0, 0]
shelf_accessories[0].position = [5.678264083553314, 4.285929724487989, 0.3]
shelf_accessories[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [5.327628892880316, 3.3724580458438624, 0.125]
wall_shelf_B[0].rotation = [0, 0, 0]
label_holder[0].position = [5.5804681200638955, 0.5149955501362984, 0.025]
label_holder[0].rotation = [0, 0, 0]
small_potted_plant_A[0].position = [5.768573536120235, 0.8190843114745043, 0.15]
small_potted_plant_A[0].rotation = [0, 0, 0]
informational_sign_A[0].position = [4.928912406514533, 3.359812400867133, 0.2]
informational_sign_A[0].rotation = [0, 0, 0]
small_potted_plant_B[0].position = [2.8085470915148614, 2.904027286498362, 0.15]
small_potted_plant_B[0].rotation = [0, 0, 0]
informational_sign_B[0].position = [5.759371870689118, 2.0467808787005133, 0.2]
informational_sign_B[0].rotation = [0, 0, 0]
hand_dryer_B[0].position = [3.1723916289206135, 0.9805933151744628, 0.175]
hand_dryer_B[0].rotation = [0, 0, 0]
waste_bin_floor_C[0].position = [6.759548387405084, 3.6769241046517296, 0.225]
waste_bin_floor_C[0].rotation = [0, 0, 0]
locker_column[0].position = [2.513320567590207, 1.6707610131120598, 0.95]
locker_column[0].rotation = [0, 0, 0]
cleaning_supply_cabinet[0].position = [0.38292608572654097, 2.1880435238816425, 0.95]
cleaning_supply_cabinet[0].rotation = [0, 0, 0]
toilet_suite_C[0].position = [4.640639993439293, 2.8114853501157397, 0.39]
toilet_suite_C[0].rotation = [0, 0, 0]
toilet_suite_A[0].position = [4.332875125362597, 2.644429908483212, 0.39]
toilet_suite_A[0].rotation = [0, 0, 0]
number_label[0].position = [4.115397239295929, 4.4588408780041275, 0.03]
number_label[0].rotation = [0, 0, 0]
waste_bin_floor_A[0].position = [1.3171588724937582, 1.1931010869014207, 0.225]
waste_bin_floor_A[0].rotation = [0, 0, 0]
vanity_counter[0].position = [4.862959208248193, 5.045989380966487, 0.45]
vanity_counter[0].rotation = [0, 0, 0]
waste_bin_floor_B[0].position = [4.330604371806891, 4.853912746057983, 0.225]
waste_bin_floor_B[0].rotation = [0, 0, 0]
hand_dryer_A[0].position = [2.029646206361879, 1.7755232819948663, 0.175]
hand_dryer_A[0].rotation = [0, 0, 0]
toilet_suite_B[0].position = [4.831376347903763, 1.9350055387898168, 0.39]
toilet_suite_B[0].rotation = [0, 0, 0]
vanity_mirror[0].position = [5.034167633892372, 1.94420283174437, 0.4]
vanity_mirror[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [2.8208691625760425, 2.5287120790972897, 0.125]
wall_shelf_A[0].rotation = [0, 0, 0]
shelf_accessories[0].position = [5.678264083553314, 4.285929724487989, 0.3]
shelf_accessories[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [5.327628892880316, 3.3724580458438624, 0.125]
wall_shelf_B[0].rotation = [0, 0, 0]
label_holder[0].position = [5.5804681200638955, 0.5149955501362984, 0.025]
label_holder[0].rotation = [0, 0, 0]
small_potted_plant_A[0].position = [5.768573536120235, 0.8190843114745043, 0.15]
small_potted_plant_A[0].rotation = [0, 0, 0]
informational_sign_A[0].position = [4.928912406514533, 3.359812400867133, 0.2]
informational_sign_A[0].rotation = [0, 0, 0]
small_potted_plant_B[0].position = [2.8085470915148614, 2.904027286498362, 0.15]
small_potted_plant_B[0].rotation = [0, 0, 0]
informational_sign_B[0].position = [5.759371870689118, 2.0467808787005133, 0.2]
informational_sign_B[0].rotation = [0, 0, 0]
hand_dryer_B[0].position = [3.1723916289206135, 0.9805933151744628, 0.175]
hand_dryer_B[0].rotation = [0, 0, 0]
waste_bin_floor_C[0].position = [6.759548387405084, 3.6769241046517296, 0.225]
waste_bin_floor_C[0].rotation = [0, 0, 0]
locker_column[0].position = [2.513320567590207, 1.6707610131120598, 0.95]
locker_column[0].rotation = [0, 0, 0]
cleaning_supply_cabinet[0].position = [0.38292608572654097, 2.1880435238816425, 0.95]
cleaning_supply_cabinet[0].rotation = [0, 0, 0]
toilet_suite_C[0].position = [4.640639993439293, 2.8114853501157397, 0.39]
toilet_suite_C[0].rotation = [0, 0, 0]

solver.constraints = []

# Direction references used to keep wall-mounted and floor-standing assets
# facing into the room.
_facing_east = AssetInstance(rotation=[0, 0, radians(0)])
_facing_north = AssetInstance(rotation=[0, 0, radians(90)])
_facing_west = AssetInstance(rotation=[0, 0, radians(180)])
_facing_south = AssetInstance(rotation=[0, 0, radians(-90)])


def _pin_position(instance):
    """Keep an instance close to its selected, collision-free layout position."""
    target = AssetInstance(position=list(instance.position))
    solver.distance_constraint(instance, target, 0, 0, weight=10)


# ---------------------------------------------------------------------------
# Initial placements
#
# The entrance corridor at x=0.89..1.91 is left unobstructed. The vanity uses
# the recessed lower room, the toilets use the south/east walls, and storage
# occupies the north wall without blocking the window on the x=4 wall.
# ---------------------------------------------------------------------------

# East-wall toilet, facing west into the room.
toilet_suite_A[0].position = [6.65, 3.00, 0.39]
toilet_suite_A[0].rotation = [0, 0, radians(180)]

# Small entrance number and its holder are mounted on the west wall. The
# number sits immediately in front of the holder rather than intersecting it.
label_holder[0].position = [0.01, 1.60, 1.55]
label_holder[0].rotation = [0, 0, radians(0)]

number_label[0].position = [0.025, 1.60, 1.55]
number_label[0].rotation = [0, 0, radians(0)]

# The required toilet/bin group is arranged along the south wall. Toilet C is
# spatially between waste bins A and B, while remaining well right of the door.
waste_bin_floor_A[0].position = [4.10, 0.15, 0.225]
waste_bin_floor_A[0].rotation = [0, 0, radians(90)]

toilet_suite_C[0].position = [4.65, 0.35, 0.39]
toilet_suite_C[0].rotation = [0, 0, radians(90)]

waste_bin_floor_B[0].position = [5.20, 0.15, 0.225]
waste_bin_floor_B[0].rotation = [0, 0, radians(90)]

# Vanity runs along the y=3 wall in the lower-left recess. Its long dimension
# is parallel to the wall and its front faces south.
vanity_counter[0].position = [2.80, 2.70, 0.45]
vanity_counter[0].rotation = [0, 0, radians(-90)]

vanity_mirror[0].position = [2.80, 2.97, 1.50]
vanity_mirror[0].rotation = [0, 0, radians(-90)]

# Required plant A is centered over a clear part of the vanity countertop.
small_potted_plant_A[0].position = [2.45, 2.65, 1.05]
small_potted_plant_A[0].rotation = [0, 0, radians(-90)]

# A hand dryer is mounted on the west wall, away from the entrance opening.
hand_dryer_A[0].position = [0.10, 2.25, 1.20]
hand_dryer_A[0].rotation = [0, 0, radians(0)]

# Two shelves occupy the lower portion of the x=4 wall. Both remain below the
# window, whose lower edge is approximately y=5.025.
wall_shelf_A[0].position = [4.11, 3.55, 1.35]
wall_shelf_A[0].rotation = [0, 0, radians(0)]

wall_shelf_B[0].position = [4.11, 4.50, 1.45]
wall_shelf_B[0].rotation = [0, 0, radians(0)]

# Small shelf objects are vertically supported by their respective shelves.
shelf_accessories[0].position = [4.14, 3.55, 1.775]
shelf_accessories[0].rotation = [0, 0, radians(0)]

small_potted_plant_B[0].position = [4.14, 4.50, 1.725]
small_potted_plant_B[0].rotation = [0, 0, radians(0)]

# Second east-wall toilet and wall signage.
toilet_suite_B[0].position = [6.65, 4.15, 0.39]
toilet_suite_B[0].rotation = [0, 0, radians(180)]

informational_sign_A[0].position = [6.99, 3.00, 1.60]
informational_sign_A[0].rotation = [0, 0, radians(180)]

informational_sign_B[0].position = [6.99, 4.15, 1.60]
informational_sign_B[0].rotation = [0, 0, radians(180)]

# Dryer B and the third bin share the east wall at different heights.
waste_bin_floor_C[0].position = [6.875, 5.20, 0.225]
waste_bin_floor_C[0].rotation = [0, 0, radians(180)]

hand_dryer_B[0].position = [6.90, 5.20, 1.20]
hand_dryer_B[0].rotation = [0, 0, radians(180)]

# Tall storage is placed against the north wall, clear of the window opening.
cleaning_supply_cabinet[0].position = [4.65, 5.75, 0.95]
cleaning_supply_cabinet[0].rotation = [0, 0, radians(-90)]

locker_column[0].position = [5.55, 5.75, 0.95]
locker_column[0].rotation = [0, 0, radians(-90)]


# ---------------------------------------------------------------------------
# Constraints
# ---------------------------------------------------------------------------

# Toilet A: retain contact with the east wall and face the room.
solver.against_wall(toilet_suite_A[0], walls[6])
_pin_position(toilet_suite_A[0])
solver.point_towards(
    toilet_suite_A[0],
    AssetInstance(position=[5.40, 3.00, 0.39])
)

# Entrance labels.
solver.against_wall(label_holder[0], walls[2])
_pin_position(label_holder[0])
solver.align_with(label_holder[0], _facing_east)

# Keep the number directly in front of its holder. This is its positional
# relationship; the very small separation prevents mesh overlap.
solver.distance_constraint(
    number_label[0], label_holder[0], 0.015, 0.025, weight=10
)
_pin_position(number_label[0])
solver.align_with(number_label[0], label_holder[0])

# South-wall toilet/bin group. The high-priority wall constraints preserve the
# left-bin / toilet / right-bin ordering selected above.
solver.against_wall(waste_bin_floor_A[0], walls[3])
_pin_position(waste_bin_floor_A[0])
solver.align_with(waste_bin_floor_A[0], _facing_north)

solver.against_wall(toilet_suite_C[0], walls[3])
_pin_position(toilet_suite_C[0])
solver.point_towards(
    toilet_suite_C[0],
    AssetInstance(position=[4.65, 2.00, 0.39])
)

solver.against_wall(waste_bin_floor_B[0], walls[3])
_pin_position(waste_bin_floor_B[0])
solver.align_with(waste_bin_floor_B[0], _facing_north)

# These balanced distances reinforce that toilet C stays between the two bins.
solver.distance_constraint(
    toilet_suite_C[0], waste_bin_floor_A[0], 0.50, 0.65, weight=10
)
solver.distance_constraint(
    toilet_suite_C[0], waste_bin_floor_B[0], 0.50, 0.65, weight=10
)

# Vanity grouping.
solver.against_wall(vanity_counter[0], walls[1])
_pin_position(vanity_counter[0])
solver.align_with(vanity_counter[0], _facing_south)

solver.against_wall(vanity_mirror[0], walls[1])
_pin_position(vanity_mirror[0])
solver.align_with(vanity_mirror[0], vanity_counter[0])

# The support constraint is specified first because keeping plant A on the
# vanity is a required semantic relationship.
solver.on_top_of(small_potted_plant_A[0], vanity_counter[0])
_pin_position(small_potted_plant_A[0])
solver.align_with(small_potted_plant_A[0], vanity_counter[0])

# West-wall dryer.
solver.against_wall(hand_dryer_A[0], walls[2])
_pin_position(hand_dryer_A[0])
solver.align_with(hand_dryer_A[0], _facing_east)

# Wall shelves.
solver.against_wall(wall_shelf_A[0], walls[0])
_pin_position(wall_shelf_A[0])
solver.align_with(wall_shelf_A[0], _facing_east)

solver.against_wall(wall_shelf_B[0], walls[0])
_pin_position(wall_shelf_B[0])
solver.align_with(wall_shelf_B[0], _facing_east)

# Shelf-top objects receive both vertical support and positional constraints.
solver.on_top_of(shelf_accessories[0], wall_shelf_A[0])
_pin_position(shelf_accessories[0])
solver.align_with(shelf_accessories[0], wall_shelf_A[0])

solver.on_top_of(small_potted_plant_B[0], wall_shelf_B[0])
_pin_position(small_potted_plant_B[0])
solver.align_with(small_potted_plant_B[0], wall_shelf_B[0])

# Toilet B: retain contact with the east wall and face west.
solver.against_wall(toilet_suite_B[0], walls[6])
_pin_position(toilet_suite_B[0])
solver.point_towards(
    toilet_suite_B[0],
    AssetInstance(position=[5.40, 4.15, 0.39])
)

# Signs are mounted above their corresponding east-wall toilets.
solver.against_wall(informational_sign_A[0], walls[6])
_pin_position(informational_sign_A[0])
solver.align_with(informational_sign_A[0], _facing_west)

solver.against_wall(informational_sign_B[0], walls[6])
_pin_position(informational_sign_B[0])
solver.align_with(informational_sign_B[0], _facing_west)

# East-wall bin and dryer.
solver.against_wall(waste_bin_floor_C[0], walls[6])
_pin_position(waste_bin_floor_C[0])
solver.align_with(waste_bin_floor_C[0], _facing_west)

solver.against_wall(hand_dryer_B[0], walls[6])
_pin_position(hand_dryer_B[0])
solver.align_with(hand_dryer_B[0], _facing_west)

# North-wall storage. The selected positions leave clearance between the two
# units and keep both clear of the x=4 window.
solver.against_wall(cleaning_supply_cabinet[0], walls[7])
_pin_position(cleaning_supply_cabinet[0])
solver.align_with(cleaning_supply_cabinet[0], _facing_south)

solver.against_wall(locker_column[0], walls[7])
_pin_position(locker_column[0])
solver.align_with(locker_column[0], _facing_south)

solver.distance_constraint(
    locker_column[0], cleaning_supply_cabinet[0], 0.85, 1.10, weight=10
)

solver.constraints = []
locker_column[0].position = [5.550000190734863, 5.74998664855957, 0.949999988079071]
locker_column[0].rotation = [0, 0, -1.5708460993602478]
locker_column[0].optimize = 2
vanity_counter[0].position = [2.799999952316284, 2.700082302093506, 0.44999998807907104]
vanity_counter[0].rotation = [0, 0, -1.5708737501748276]
vanity_counter[0].optimize = 2
waste_bin_floor_A[0].position = [4.099999904632568, 0.15000000596046448, 0.22499999403953552]
waste_bin_floor_A[0].rotation = [0, 0, 0.004803879939770536]
waste_bin_floor_A[0].optimize = 2
hand_dryer_A[0].position = [0.10002098977565765, 2.25, 0.17499999701976776]
hand_dryer_A[0].rotation = [0, 0, -4.7108684528153416e-05]
hand_dryer_A[0].optimize = 2
shelf_accessories[0].position = [4.139999866485596, 3.549999952316284, 0.550000011920929]
shelf_accessories[0].rotation = [0, 0, -0.0001058824736820817]
shelf_accessories[0].optimize = 2
hand_dryer_B[0].position = [6.899980068206787, 5.199999809265137, 0.17499999701976776]
hand_dryer_B[0].rotation = [0, 0, 3.1415455566672055]
hand_dryer_B[0].optimize = 2
toilet_suite_B[0].position = [6.649967670440674, 4.150000095367432, 0.38999998569488525]
toilet_suite_B[0].rotation = [0, 0, 3.1415456994605013]
toilet_suite_B[0].optimize = 2
number_label[0].position = [0.005005301907658577, 1.600000023841858, 0.029999999329447746]
number_label[0].rotation = [0, 0, -0.0001060202367689975]
number_label[0].optimize = 2
waste_bin_floor_C[0].position = [6.874973297119141, 5.199999809265137, 0.22499999403953552]
waste_bin_floor_C[0].rotation = [0, 0, 3.1415455515727233]
waste_bin_floor_C[0].optimize = 2
waste_bin_floor_B[0].position = [5.199999809265137, 0.12492228299379349, 0.22499999403953552]
waste_bin_floor_B[0].rotation = [0, 0, 1.5707462299813486]
waste_bin_floor_B[0].optimize = 2
wall_shelf_B[0].position = [4.109997272491455, 4.5, 0.125]
wall_shelf_B[0].rotation = [0, 0, 7.149007726155715e-05]
wall_shelf_B[0].optimize = 2
toilet_suite_C[0].position = [4.650000095367432, 0.3499743640422821, 0.38999998569488525]
toilet_suite_C[0].rotation = [0, 0, 1.5708678384977097]
toilet_suite_C[0].optimize = 2
vanity_mirror[0].position = [2.799999952316284, 2.9699649810791016, 0.4000000059604645]
vanity_mirror[0].rotation = [0, 0, -1.5708434690543736]
vanity_mirror[0].optimize = 2
cleaning_supply_cabinet[0].position = [4.650000095367432, 5.7500200271606445, 0.949999988079071]
cleaning_supply_cabinet[0].rotation = [0, 0, -1.5708460925335357]
cleaning_supply_cabinet[0].optimize = 2
informational_sign_A[0].position = [6.850089073181152, 3.0, 0.20000000298023224]
informational_sign_A[0].rotation = [0, 0, -1.5624361873693033]
informational_sign_A[0].optimize = 2
toilet_suite_A[0].position = [6.650000095367432, 3.0, 0.38999998569488525]
toilet_suite_A[0].rotation = [0, 0, -1.5624361873693033]
toilet_suite_A[0].optimize = 2
wall_shelf_A[0].position = [4.109997272491455, 3.549999952316284, 0.125]
wall_shelf_A[0].rotation = [0, 0, 7.149007726155715e-05]
wall_shelf_A[0].optimize = 2
label_holder[0].position = [0.010043097659945488, 1.600000023841858, 0.02500000037252903]
label_holder[0].rotation = [0, 0, 7.153750985501418e-05]
label_holder[0].optimize = 2
informational_sign_B[0].position = [6.990041255950928, 4.150000095367432, 0.20000000298023224]
informational_sign_B[0].rotation = [0, 0, 3.1415454897479327]
informational_sign_B[0].optimize = 2
small_potted_plant_B[0].position = [4.139999866485596, 4.5, 0.4000000059604645]
small_potted_plant_B[0].rotation = [0, 0, -0.0001058824736820817]
small_potted_plant_B[0].optimize = 2
small_potted_plant_A[0].position = [2.450000047683716, 2.6500000953674316, 1.0499999523162842]
small_potted_plant_A[0].rotation = [0, 0, -1.570526000909328]
small_potted_plant_A[0].optimize = 2

