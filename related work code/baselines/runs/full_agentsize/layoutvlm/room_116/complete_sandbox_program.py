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
pantry_notice_board = Assets(description="A chalk billboard with some prices on it.", size=[0.05, 1.20, 0.80], placements=[AssetInstance() for _ in range(1)])
hand_dryer_unit_A = Assets(description="A hand dryer for a bathroom.", size=[0.20, 0.30, 0.55], placements=[AssetInstance() for _ in range(1)])
liquid_soap_dispenser = Assets(description="White soap bottle model", size=[0.07, 0.09, 0.20], placements=[AssetInstance() for _ in range(1)])
restroom_wall_shelf = Assets(description="A set of radiator pipes that are bolted into the wall.", size=[0.25, 1.20, 0.60], placements=[AssetInstance() for _ in range(1)])
restroom_mirror_panel = Assets(description="A poster of blueprints for a picture frame.", size=[0.04, 1.60, 0.90], placements=[AssetInstance() for _ in range(1)])
toilet_suite_A = Assets(description="toilet suite", size=[0.70, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
pantry_open_shelf = Assets(description="A purple set of shelves with green and purple shelving.", size=[0.30, 1.00, 0.90], placements=[AssetInstance() for _ in range(1)])
pantry_wall_cabinet = Assets(description="A tall slim cupboard with four shelves in it.", size=[0.35, 0.60, 1.80], placements=[AssetInstance() for _ in range(1)])
toilet_suite_B = Assets(description="toilet suite", size=[0.70, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
toilet_suite_C = Assets(description="toilet suite", size=[0.70, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
pantry_base_cabinet = Assets(description="Wood cabinet with three doors and three drawers above.", size=[0.60, 1.80, 0.90], placements=[AssetInstance() for _ in range(1)])
hand_dryer_unit_B = Assets(description="A hand dryer for a bathroom.", size=[0.20, 0.30, 0.55], placements=[AssetInstance() for _ in range(1)])
restroom_vanity_counter = Assets(description="A long standing desk with two computer monitors on it and a plant.", size=[0.55, 1.80, 0.85], placements=[AssetInstance() for _ in range(1)])
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

pantry_notice_board[0].position = [1.7053303607532273, 2.9950950294971386, 0.4]
pantry_notice_board[0].rotation = [0, 0, 0]
hand_dryer_unit_A[0].position = [3.782126095537987, 5.782981924227702, 0.275]
hand_dryer_unit_A[0].rotation = [0, 0, 0]
liquid_soap_dispenser[0].position = [1.1860325262235354, 1.8002022580762342, 0.1]
liquid_soap_dispenser[0].rotation = [0, 0, 0]
restroom_wall_shelf[0].position = [0.026366567301113975, 2.008591144326203, 0.3]
restroom_wall_shelf[0].rotation = [0, 0, 0]
restroom_mirror_panel[0].position = [1.2428521374845203, 4.9157919694373895, 0.45]
restroom_mirror_panel[0].rotation = [0, 0, 0]
toilet_suite_A[0].position = [2.44235831725303, 2.0241507427762224, 0.39]
toilet_suite_A[0].rotation = [0, 0, 0]
pantry_open_shelf[0].position = [1.2465377822732653, 3.610975241549056, 0.45]
pantry_open_shelf[0].rotation = [0, 0, 0]
pantry_wall_cabinet[0].position = [3.3034838961583315, 0.43156950817297246, 0.9]
pantry_wall_cabinet[0].rotation = [0, 0, 0]
toilet_suite_B[0].position = [1.4284836182384817, 2.414617830736816, 0.39]
toilet_suite_B[0].rotation = [0, 0, 0]
toilet_suite_C[0].position = [3.0440311202771997, 2.1935816082004562, 0.39]
toilet_suite_C[0].rotation = [0, 0, 0]
pantry_base_cabinet[0].position = [3.8869197062472507, 2.771474028362918, 0.45]
pantry_base_cabinet[0].rotation = [0, 0, 0]
hand_dryer_unit_B[0].position = [0.7831716942379554, 3.682118919123738, 0.275]
hand_dryer_unit_B[0].rotation = [0, 0, 0]
restroom_vanity_counter[0].position = [0.17978435022991368, 1.6055966246225941, 0.425]
restroom_vanity_counter[0].rotation = [0, 0, 0]
pantry_undercounter_fridge[0].position = [3.70310842277733, 3.226331398072416, 0.425]
pantry_undercounter_fridge[0].rotation = [0, 0, 0]
pantry_notice_board[0].position = [1.7053303607532273, 2.9950950294971386, 0.4]
pantry_notice_board[0].rotation = [0, 0, 0]
hand_dryer_unit_A[0].position = [3.782126095537987, 5.782981924227702, 0.275]
hand_dryer_unit_A[0].rotation = [0, 0, 0]
liquid_soap_dispenser[0].position = [1.1860325262235354, 1.8002022580762342, 0.1]
liquid_soap_dispenser[0].rotation = [0, 0, 0]
restroom_wall_shelf[0].position = [0.026366567301113975, 2.008591144326203, 0.3]
restroom_wall_shelf[0].rotation = [0, 0, 0]
restroom_mirror_panel[0].position = [1.2428521374845203, 4.9157919694373895, 0.45]
restroom_mirror_panel[0].rotation = [0, 0, 0]
toilet_suite_A[0].position = [2.44235831725303, 2.0241507427762224, 0.39]
toilet_suite_A[0].rotation = [0, 0, 0]
pantry_open_shelf[0].position = [1.2465377822732653, 3.610975241549056, 0.45]
pantry_open_shelf[0].rotation = [0, 0, 0]
pantry_wall_cabinet[0].position = [3.3034838961583315, 0.43156950817297246, 0.9]
pantry_wall_cabinet[0].rotation = [0, 0, 0]
toilet_suite_B[0].position = [1.4284836182384817, 2.414617830736816, 0.39]
toilet_suite_B[0].rotation = [0, 0, 0]
toilet_suite_C[0].position = [3.0440311202771997, 2.1935816082004562, 0.39]
toilet_suite_C[0].rotation = [0, 0, 0]
pantry_base_cabinet[0].position = [3.8869197062472507, 2.771474028362918, 0.45]
pantry_base_cabinet[0].rotation = [0, 0, 0]
hand_dryer_unit_B[0].position = [0.7831716942379554, 3.682118919123738, 0.275]
hand_dryer_unit_B[0].rotation = [0, 0, 0]
restroom_vanity_counter[0].position = [0.17978435022991368, 1.6055966246225941, 0.425]
restroom_vanity_counter[0].rotation = [0, 0, 0]
pantry_undercounter_fridge[0].position = [3.70310842277733, 3.226331398072416, 0.425]
pantry_undercounter_fridge[0].rotation = [0, 0, 0]

solver.constraints = []

# Divide the L-shaped room into a pantry zone along the west wall and a
# restroom zone using the north and southeast walls. The entrance area in
# front of the door at (0.79, 0.00) remains unobstructed.

# Pantry fixtures along the west wall.
pantry_wall_cabinet[0].position = [0.175, 0.70, 0.90]
pantry_wall_cabinet[0].rotation = [0, 0, radians(0)]

pantry_undercounter_fridge[0].position = [0.30, 1.35, 0.425]
pantry_undercounter_fridge[0].rotation = [0, 0, radians(0)]

pantry_base_cabinet[0].position = [0.30, 2.90, 0.45]
pantry_base_cabinet[0].rotation = [0, 0, radians(0)]

# The open shelf is stacked over the base cabinet, preserving floor space.
pantry_open_shelf[0].position = [0.15, 2.90, 1.35]
pantry_open_shelf[0].rotation = [0, 0, radians(0)]

# Mount the notice board above the low fridge area.
pantry_notice_board[0].position = [0.025, 1.70, 1.50]
pantry_notice_board[0].rotation = [0, 0, radians(0)]

# Three toilets form a row against the north wall. Toilet A (o0005) is
# explicitly centered between toilet B (o0008) and toilet C (o0009).
toilet_suite_B[0].position = [1.45, 5.65, 0.39]
toilet_suite_B[0].rotation = [0, 0, radians(-90)]

toilet_suite_A[0].position = [2.50, 5.65, 0.39]
toilet_suite_A[0].rotation = [0, 0, radians(-90)]

toilet_suite_C[0].position = [3.55, 5.65, 0.39]
toilet_suite_C[0].rotation = [0, 0, radians(-90)]

# Place the vanity on the southeast portion of the south wall, beyond the
# door opening and its approach path.
restroom_vanity_counter[0].position = [2.60, 0.275, 0.425]
restroom_vanity_counter[0].rotation = [0, 0, radians(90)]

restroom_mirror_panel[0].position = [2.60, 0.02, 1.40]
restroom_mirror_panel[0].rotation = [0, 0, radians(90)]

liquid_soap_dispenser[0].position = [2.20, 0.275, 0.95]
liquid_soap_dispenser[0].rotation = [0, 0, radians(90)]

hand_dryer_unit_A[0].position = [3.75, 0.10, 1.20]
hand_dryer_unit_A[0].rotation = [0, 0, radians(90)]

# Use the west face of the upper recess for additional wall-mounted restroom
# equipment, leaving the east-wall windows completely unobstructed.
hand_dryer_unit_B[0].position = [1.10, 4.25, 1.20]
hand_dryer_unit_B[0].rotation = [0, 0, radians(0)]

restroom_wall_shelf[0].position = [1.125, 5.15, 1.30]
restroom_wall_shelf[0].rotation = [0, 0, radians(0)]


# Exact anchors preserve the selected along-wall locations and mounting
# heights. These are fixed points, not additional scene assets.
pantry_wall_cabinet_anchor = AssetInstance(position=[0.175, 0.70, 0.90])
pantry_fridge_anchor = AssetInstance(position=[0.30, 1.35, 0.425])
pantry_base_anchor = AssetInstance(position=[0.30, 2.90, 0.45])
pantry_open_shelf_anchor = AssetInstance(position=[0.15, 2.90, 1.35])
pantry_notice_anchor = AssetInstance(position=[0.025, 1.70, 1.50])

toilet_B_anchor = AssetInstance(position=[1.45, 5.65, 0.39])
toilet_A_anchor = AssetInstance(position=[2.50, 5.65, 0.39])
toilet_C_anchor = AssetInstance(position=[3.55, 5.65, 0.39])

vanity_anchor = AssetInstance(position=[2.60, 0.275, 0.425])
mirror_anchor = AssetInstance(position=[2.60, 0.02, 1.40])
soap_anchor = AssetInstance(position=[2.20, 0.275, 0.95])
dryer_A_anchor = AssetInstance(position=[3.75, 0.10, 1.20])
dryer_B_anchor = AssetInstance(position=[1.10, 4.25, 1.20])
restroom_shelf_anchor = AssetInstance(position=[1.125, 5.15, 1.30])

# Orientation targets located directly in front of each relevant wall.
west_wall_inward_target = AssetInstance(position=[2.00, 2.50, 1.00])
north_wall_inward_target = AssetInstance(position=[2.50, 4.50, 0.39])
south_wall_inward_target = AssetInstance(position=[2.60, 2.00, 1.00])
upper_recess_inward_target = AssetInstance(position=[2.50, 5.00, 1.20])


# Pantry constraints: retain wall contact, selected spacing, and inward-facing
# orientations. The shelf also receives the required vertical support.
solver.distance_constraint(
    pantry_wall_cabinet[0], pantry_wall_cabinet_anchor, 0, 0, weight=10
)
solver.against_wall(pantry_wall_cabinet[0], walls[0])
solver.point_towards(pantry_wall_cabinet[0], west_wall_inward_target)

solver.distance_constraint(
    pantry_undercounter_fridge[0], pantry_fridge_anchor, 0, 0, weight=10
)
solver.against_wall(pantry_undercounter_fridge[0], walls[0])
solver.point_towards(pantry_undercounter_fridge[0], west_wall_inward_target)

solver.distance_constraint(
    pantry_base_cabinet[0], pantry_base_anchor, 0, 0, weight=10
)
solver.against_wall(pantry_base_cabinet[0], walls[0])
solver.point_towards(pantry_base_cabinet[0], west_wall_inward_target)

solver.distance_constraint(
    pantry_open_shelf[0], pantry_open_shelf_anchor, 0, 0, weight=10
)
solver.on_top_of(pantry_open_shelf[0], pantry_base_cabinet[0])
solver.against_wall(pantry_open_shelf[0], walls[0])
solver.align_with(pantry_open_shelf[0], pantry_base_cabinet[0])

solver.distance_constraint(
    pantry_notice_board[0], pantry_notice_anchor, 0, 0, weight=10
)
solver.against_wall(pantry_notice_board[0], walls[0])
solver.point_towards(pantry_notice_board[0], west_wall_inward_target)


# Anchor the two outer toilets first, then preserve equal spacing from the
# middle toilet. Together with the common north wall, these constraints keep
# toilet A geometrically between B and C.
solver.distance_constraint(toilet_suite_B[0], toilet_B_anchor, 0, 0, weight=10)
solver.against_wall(toilet_suite_B[0], walls[3])
solver.point_towards(toilet_suite_B[0], north_wall_inward_target)

solver.distance_constraint(toilet_suite_C[0], toilet_C_anchor, 0, 0, weight=10)
solver.against_wall(toilet_suite_C[0], walls[3])
solver.point_towards(toilet_suite_C[0], north_wall_inward_target)

solver.distance_constraint(toilet_suite_A[0], toilet_A_anchor, 0, 0, weight=10)
solver.distance_constraint(
    toilet_suite_A[0], toilet_suite_B[0], 1.05, 1.05, weight=10
)
solver.distance_constraint(
    toilet_suite_A[0], toilet_suite_C[0], 1.05, 1.05, weight=10
)
solver.against_wall(toilet_suite_A[0], walls[3])
solver.point_towards(toilet_suite_A[0], north_wall_inward_target)


# Vanity-group constraints. The mirror remains wall-mounted above the vanity,
# while the small soap dispenser is supported by the vanity top.
solver.distance_constraint(
    restroom_vanity_counter[0], vanity_anchor, 0, 0, weight=10
)
solver.against_wall(restroom_vanity_counter[0], walls[1])
solver.point_towards(restroom_vanity_counter[0], south_wall_inward_target)

solver.distance_constraint(
    restroom_mirror_panel[0], mirror_anchor, 0, 0, weight=10
)
solver.against_wall(restroom_mirror_panel[0], walls[1])
solver.align_with(restroom_mirror_panel[0], restroom_vanity_counter[0])

solver.distance_constraint(
    liquid_soap_dispenser[0], soap_anchor, 0, 0, weight=10
)
solver.on_top_of(liquid_soap_dispenser[0], restroom_vanity_counter[0])
solver.align_with(liquid_soap_dispenser[0], restroom_vanity_counter[0])

solver.distance_constraint(
    hand_dryer_unit_A[0], dryer_A_anchor, 0, 0, weight=10
)
solver.against_wall(hand_dryer_unit_A[0], walls[1])
solver.point_towards(hand_dryer_unit_A[0], south_wall_inward_target)

solver.distance_constraint(
    hand_dryer_unit_B[0], dryer_B_anchor, 0, 0, weight=10
)
solver.against_wall(hand_dryer_unit_B[0], walls[4])
solver.point_towards(hand_dryer_unit_B[0], upper_recess_inward_target)

solver.distance_constraint(
    restroom_wall_shelf[0], restroom_shelf_anchor, 0, 0, weight=10
)
solver.against_wall(restroom_wall_shelf[0], walls[4])
solver.point_towards(restroom_wall_shelf[0], upper_recess_inward_target)

solver.constraints = []
pantry_notice_board[0].position = [0.026524467393755913, 1.7000000476837158, 0.4000000059604645]
pantry_notice_board[0].rotation = [0, 0, 0.0025409114179187954]
pantry_notice_board[0].optimize = 2
restroom_vanity_counter[0].position = [2.5999999046325684, 0.28472408652305603, 0.42500001192092896]
restroom_vanity_counter[0].rotation = [0, 0, 1.5826693327625838]
restroom_vanity_counter[0].optimize = 2
restroom_wall_shelf[0].position = [1.1265242099761963, 5.150000095367432, 0.30000001192092896]
restroom_wall_shelf[0].rotation = [0, 0, 0.002540910495746011]
restroom_wall_shelf[0].optimize = 2
pantry_wall_cabinet[0].position = [0.17576171457767487, 0.699999988079071, 0.8999999761581421]
pantry_wall_cabinet[0].rotation = [0, 0, 0.0025409193727581954]
pantry_wall_cabinet[0].optimize = 2
hand_dryer_unit_B[0].position = [1.1003808975219727, 4.25, 0.2750000059604645]
hand_dryer_unit_B[0].rotation = [0, 0, 0.0025409215170312644]
hand_dryer_unit_B[0].optimize = 2
liquid_soap_dispenser[0].position = [2.200000047683716, 0.2750000059604645, 0.9500000476837158]
liquid_soap_dispenser[0].rotation = [0, 0, 1.593585179335]
liquid_soap_dispenser[0].optimize = 2
pantry_undercounter_fridge[0].position = [0.300761342048645, 1.350000023841858, 0.42500001192092896]
pantry_undercounter_fridge[0].rotation = [0, 0, 0.002540918450584867]
pantry_undercounter_fridge[0].optimize = 2
toilet_suite_B[0].position = [1.4500000476837158, 5.648931980133057, 0.38999998569488525]
toilet_suite_B[0].rotation = [0, 0, -1.5651448028559958]
toilet_suite_B[0].optimize = 2
pantry_base_cabinet[0].position = [0.3069104850292206, 2.9000000953674316, 0.44999998807907104]
pantry_base_cabinet[0].rotation = [0, 0, 0.00876220575225972]
pantry_base_cabinet[0].optimize = 2
hand_dryer_unit_A[0].position = [3.75, 0.10038082301616669, 0.2750000059604645]
hand_dryer_unit_A[0].rotation = [0, 0, 1.573337248311928]
hand_dryer_unit_A[0].optimize = 2
toilet_suite_C[0].position = [3.549999952316284, 5.648931980133057, 0.38999998569488525]
toilet_suite_C[0].rotation = [0, 0, -1.5651448028559958]
toilet_suite_C[0].optimize = 2
restroom_mirror_panel[0].position = [2.5999999046325684, 0.0200515054166317, 0.44999998807907104]
restroom_mirror_panel[0].rotation = [0, 0, 1.5733372287135647]
restroom_mirror_panel[0].optimize = 2
toilet_suite_A[0].position = [2.5, 5.648348808288574, 0.38999998569488525]
toilet_suite_A[0].rotation = [0, 0, -1.5620341020380741]
toilet_suite_A[0].optimize = 2
pantry_open_shelf[0].position = [0.15282335877418518, 2.9000000953674316, 1.3499999046325684]
pantry_open_shelf[0].rotation = [0, 0, 0.005651517993733263]
pantry_open_shelf[0].optimize = 2

