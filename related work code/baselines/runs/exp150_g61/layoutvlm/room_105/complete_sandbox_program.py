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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.00, 0.00, 0.00]),
    Wall(corner1=[6.00, 0.00, 0.00], corner2=[6.00, 3.00, 0.00]),
    Wall(corner1=[6.00, 3.00, 0.00], corner2=[0.00, 3.00, 0.00]),
    Wall(corner1=[0.00, 3.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
compact_round_bistro_table_A = Assets(description="A circular four legged light brown wooden table.", size=[0.70, 0.70, 0.75], placements=[AssetInstance() for _ in range(1)])
storage_box_A = Assets(description="A brown box with a cover that says patient files.", size=[0.32, 0.40, 0.27], placements=[AssetInstance() for _ in range(1)])
tall_pantry_cabinet_A = Assets(description="tall pantry cabinet", size=[0.60, 0.60, 2.10], placements=[AssetInstance() for _ in range(1)])
base_cabinet_run = Assets(description="A row of cabinets in white wood.", size=[0.60, 1.80, 0.90], placements=[AssetInstance() for _ in range(1)])
side_chair_A = Assets(description="An orange wooden chair with seat and back rest bolted with four black bolts.", size=[0.50, 0.45, 0.82], placements=[AssetInstance() for _ in range(1)])
waste_bin_A = Assets(description="a wheeled trash can", size=[0.50, 0.40, 0.80], placements=[AssetInstance() for _ in range(1)])
compact_round_bistro_table_B = Assets(description="A circular four legged light brown wooden table.", size=[0.70, 0.70, 0.75], placements=[AssetInstance() for _ in range(1)])
tall_refrigerator = Assets(description="tall refrigerator", size=[0.68, 0.65, 1.85], placements=[AssetInstance() for _ in range(1)])
storage_box_B = Assets(description="A brown box with a cover that says patient files.", size=[0.32, 0.40, 0.27], placements=[AssetInstance() for _ in range(1)])
side_chair_B = Assets(description="An orange wooden chair with seat and back rest bolted with four black bolts.", size=[0.50, 0.45, 0.82], placements=[AssetInstance() for _ in range(1)])
tall_pantry_cabinet_B = Assets(description="tall pantry cabinet", size=[0.60, 0.60, 2.10], placements=[AssetInstance() for _ in range(1)])
side_chair_C = Assets(description="An orange wooden chair with seat and back rest bolted with four black bolts.", size=[0.50, 0.45, 0.82], placements=[AssetInstance() for _ in range(1)])
waste_bin_B = Assets(description="a wheeled trash can", size=[0.50, 0.40, 0.80], placements=[AssetInstance() for _ in range(1)])
under_counter_cabinet = Assets(description="A black cabinet with a black tabletop.", size=[0.60, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
freestanding_shelving_unit = Assets(description="A bunch of wooden shelves with a couple of drawers.", size=[0.40, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])

compact_round_bistro_table_A[0].instance_id = 'compact_round_bistro_table_A_0'
storage_box_A[0].instance_id = 'storage_box_A_0'
tall_pantry_cabinet_A[0].instance_id = 'tall_pantry_cabinet_A_0'
base_cabinet_run[0].instance_id = 'base_cabinet_run_0'
side_chair_A[0].instance_id = 'side_chair_A_0'
waste_bin_A[0].instance_id = 'waste_bin_A_0'
compact_round_bistro_table_B[0].instance_id = 'compact_round_bistro_table_B_0'
tall_refrigerator[0].instance_id = 'tall_refrigerator_0'
storage_box_B[0].instance_id = 'storage_box_B_0'
side_chair_B[0].instance_id = 'side_chair_B_0'
tall_pantry_cabinet_B[0].instance_id = 'tall_pantry_cabinet_B_0'
side_chair_C[0].instance_id = 'side_chair_C_0'
waste_bin_B[0].instance_id = 'waste_bin_B_0'
under_counter_cabinet[0].instance_id = 'under_counter_cabinet_0'
freestanding_shelving_unit[0].instance_id = 'freestanding_shelving_unit_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

compact_round_bistro_table_A[0].position = [2.3277018073854334, 1.5766704392860562, 0.375]
compact_round_bistro_table_A[0].rotation = [0, 0, 0]
storage_box_A[0].position = [5.294444183754409, 2.065135001260005, 0.135]
storage_box_A[0].rotation = [0, 0, 0]
tall_pantry_cabinet_A[0].position = [1.294115505260399, 0.5962782181133506, 1.05]
tall_pantry_cabinet_A[0].rotation = [0, 0, 0]
base_cabinet_run[0].position = [5.701390777729861, 2.442090123918235, 0.45]
base_cabinet_run[0].rotation = [0, 0, 0]
side_chair_A[0].position = [3.361169549022992, 2.0761744665772754, 0.41]
side_chair_A[0].rotation = [0, 0, 0]
waste_bin_A[0].position = [0.1468953565399973, 2.3439906349213677, 0.4]
waste_bin_A[0].rotation = [0, 0, 0]
compact_round_bistro_table_B[0].position = [3.456579379965374, 2.3669187664455995, 0.375]
compact_round_bistro_table_B[0].rotation = [0, 0, 0]
tall_refrigerator[0].position = [2.4846615637738383, 0.38635900495978526, 0.925]
tall_refrigerator[0].rotation = [0, 0, 0]
storage_box_B[0].position = [2.552452389799115, 0.9648159267293986, 0.135]
storage_box_B[0].rotation = [0, 0, 0]
side_chair_B[0].position = [5.55258889103367, 1.6985458286965571, 0.41]
side_chair_B[0].rotation = [0, 0, 0]
tall_pantry_cabinet_B[0].position = [2.51355579419826, 1.3176370991376696, 1.05]
tall_pantry_cabinet_B[0].rotation = [0, 0, 0]
side_chair_C[0].position = [2.4655554871864385, 1.001403855033384, 0.41]
side_chair_C[0].rotation = [0, 0, 0]
waste_bin_B[0].position = [3.75661863365473, 0.3305036261683245, 0.4]
waste_bin_B[0].rotation = [0, 0, 0]
under_counter_cabinet[0].position = [4.547199707614369, 0.8556062121489086, 0.45]
under_counter_cabinet[0].rotation = [0, 0, 0]
freestanding_shelving_unit[0].position = [2.7096630778025528, 2.9169970324613548, 0.9]
freestanding_shelving_unit[0].rotation = [0, 0, 0]
compact_round_bistro_table_A[0].position = [2.3277018073854334, 1.5766704392860562, 0.375]
compact_round_bistro_table_A[0].rotation = [0, 0, 0]
storage_box_A[0].position = [5.294444183754409, 2.065135001260005, 0.135]
storage_box_A[0].rotation = [0, 0, 0]
tall_pantry_cabinet_A[0].position = [1.294115505260399, 0.5962782181133506, 1.05]
tall_pantry_cabinet_A[0].rotation = [0, 0, 0]
base_cabinet_run[0].position = [5.701390777729861, 2.442090123918235, 0.45]
base_cabinet_run[0].rotation = [0, 0, 0]
side_chair_A[0].position = [3.361169549022992, 2.0761744665772754, 0.41]
side_chair_A[0].rotation = [0, 0, 0]
waste_bin_A[0].position = [0.1468953565399973, 2.3439906349213677, 0.4]
waste_bin_A[0].rotation = [0, 0, 0]
compact_round_bistro_table_B[0].position = [3.456579379965374, 2.3669187664455995, 0.375]
compact_round_bistro_table_B[0].rotation = [0, 0, 0]
tall_refrigerator[0].position = [2.4846615637738383, 0.38635900495978526, 0.925]
tall_refrigerator[0].rotation = [0, 0, 0]
storage_box_B[0].position = [2.552452389799115, 0.9648159267293986, 0.135]
storage_box_B[0].rotation = [0, 0, 0]
side_chair_B[0].position = [5.55258889103367, 1.6985458286965571, 0.41]
side_chair_B[0].rotation = [0, 0, 0]
tall_pantry_cabinet_B[0].position = [2.51355579419826, 1.3176370991376696, 1.05]
tall_pantry_cabinet_B[0].rotation = [0, 0, 0]
side_chair_C[0].position = [2.4655554871864385, 1.001403855033384, 0.41]
side_chair_C[0].rotation = [0, 0, 0]
waste_bin_B[0].position = [3.75661863365473, 0.3305036261683245, 0.4]
waste_bin_B[0].rotation = [0, 0, 0]
under_counter_cabinet[0].position = [4.547199707614369, 0.8556062121489086, 0.45]
under_counter_cabinet[0].rotation = [0, 0, 0]
freestanding_shelving_unit[0].position = [2.7096630778025528, 2.9169970324613548, 0.9]
freestanding_shelving_unit[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the supplied boundary coordinates: the room occupies [0, 6] x [0, 3].
# Keep the window wall (x=0) free of storage, put seating in the western
# half, and put cabinets along the eastern, northern and southern walls.
layout_specs = [
    (compact_round_bistro_table_A, [0.95, 1.50, 0.375], 0),
    (compact_round_bistro_table_B, [2.55, 1.50, 0.375], 0),
    (side_chair_A,                [0.95, 2.25, 0.410], -90),
    (side_chair_B,                [0.95, 0.75, 0.410], 90),
    (side_chair_C,                [1.85, 1.50, 0.410], 0),
    (base_cabinet_run,            [5.70, 1.50, 0.450], 180),
    (tall_pantry_cabinet_A,       [3.00, 0.30, 1.050], 90),
    (tall_pantry_cabinet_B,       [3.70, 0.30, 1.050], 90),
    (tall_refrigerator,           [4.50, 0.34, 0.925], 90),
    (under_counter_cabinet,       [3.40, 2.70, 0.450], -90),
    (freestanding_shelving_unit,  [4.55, 2.80, 0.900], -90),
    (waste_bin_A,                 [5.75, 0.25, 0.400], 180),
    (waste_bin_B,                 [5.75, 2.75, 0.400], 180),
    (storage_box_A,               [5.70, 1.10, 1.035], 180),
    (storage_box_B,               [5.70, 1.80, 1.035], 180),
]

# Initialize every existing placement, without replacing any Assets objects.
for asset_group, center, yaw_degrees in layout_specs:
    asset_group[0].position = center.copy()
    asset_group[0].rotation = [0, 0, radians(yaw_degrees)]

# Important support and wall relationships come first.
solver.on_top_of(storage_box_A[0], base_cabinet_run[0])
solver.on_top_of(storage_box_B[0], base_cabinet_run[0])

for asset_group, wall_index in [
    (base_cabinet_run, 1),
    (tall_pantry_cabinet_A, 0),
    (tall_pantry_cabinet_B, 0),
    (tall_refrigerator, 0),
    (under_counter_cabinet, 2),
    (freestanding_shelving_unit, 2),
    (waste_bin_A, 1),
    (waste_bin_B, 1),
]:
    solver.against_wall(asset_group[0], walls[wall_index])

# o0009 faces table A. The other chairs also face their associated tables.
solver.point_towards(side_chair_B[0], compact_round_bistro_table_A[0])
solver.point_towards(side_chair_A[0], compact_round_bistro_table_A[0])
solver.point_towards(side_chair_C[0], compact_round_bistro_table_B[0])

# o0011 lies on the segment between the two table centers.
# A literal center distance <=0.30 m would overlap these assets.
# Interpret "within 0.30 m" as a clear edge-to-edge gap: the proposed
# chair/table-B center separation is 0.70 m, giving a 0.10 m gap.
# Include the floor-standing objects' small center-height difference.
chair_table_height_delta = 0.410 - 0.375
solver.distance_constraint(
    compact_round_bistro_table_B[0], side_chair_C[0],
    (0.60**2 + chair_table_height_delta**2)**0.5,
    (0.90**2 + chair_table_height_delta**2)**0.5,
    weight=10,
)
solver.distance_constraint(
    side_chair_C[0], compact_round_bistro_table_B[0],
    (0.60**2 + chair_table_height_delta**2)**0.5,
    (0.90**2 + chair_table_height_delta**2)**0.5,
    weight=10,
)

# These exact distances preserve the collinear A--chair-C--B arrangement.
for moving_instance, reference_instance, horizontal_distance, height_delta in [
    (side_chair_C[0], compact_round_bistro_table_A[0], 0.90,
     chair_table_height_delta),
    (side_chair_C[0], compact_round_bistro_table_B[0], 0.70,
     chair_table_height_delta),
    (compact_round_bistro_table_B[0], compact_round_bistro_table_A[0],
     1.60, 0.0),
    (side_chair_A[0], compact_round_bistro_table_A[0], 0.75,
     chair_table_height_delta),
    (side_chair_B[0], compact_round_bistro_table_A[0], 0.75,
     chair_table_height_delta),
]:
    center_distance = (horizontal_distance**2 + height_delta**2)**0.5
    solver.distance_constraint(
        moving_instance, reference_instance,
        center_distance, center_distance, weight=10,
    )

# Preserve the non-overlapping layout with fixed-point position anchors.
# Each instance receives a position constraint and an orientation constraint.
# Fixed points are reference coordinates, not additional scene furniture.
for asset_group, center, yaw_degrees in layout_specs:
    solver.distance_constraint(
        asset_group[0],
        AssetInstance(position=center.copy()),
        0, 0, weight=10,
    )
    if asset_group not in (side_chair_A, side_chair_B, side_chair_C):
        solver.align_with(
            asset_group[0],
            AssetInstance(
                position=center.copy(),
                rotation=[0, 0, radians(yaw_degrees)],
            ),
            angle=0,
        )

# Keep both file boxes parallel to their supporting cabinet.
solver.align_with(storage_box_A[0], base_cabinet_run[0])
solver.align_with(storage_box_B[0], base_cabinet_run[0])

solver.constraints = []
side_chair_A[0].position = [0.949999988079071, 2.3080520629882812, 0.4099999964237213]
side_chair_A[0].rotation = [0, 0, -1.5582299555380688]
side_chair_A[0].optimize = 2
freestanding_shelving_unit[0].position = [4.550000190734863, 2.799999952316284, 0.8999999761581421]
freestanding_shelving_unit[0].rotation = [0, 0, -1.5707965355236682]
freestanding_shelving_unit[0].optimize = 2
storage_box_B[0].position = [5.699999809265137, 1.7999999523162842, 1.034999966621399]
storage_box_B[0].rotation = [0, 0, -3.141589913969134]
storage_box_B[0].optimize = 2
tall_pantry_cabinet_B[0].position = [3.700000047683716, 0.29999977350234985, 1.0499999523162842]
tall_pantry_cabinet_B[0].rotation = [0, 0, 1.5707961072014696]
tall_pantry_cabinet_B[0].optimize = 2
storage_box_A[0].position = [5.699999809265137, 1.100000023841858, 1.034999966621399]
storage_box_A[0].rotation = [0, 0, -3.141589913969134]
storage_box_A[0].optimize = 2
compact_round_bistro_table_A[0].position = [0.949999988079071, 1.5, 0.375]
compact_round_bistro_table_A[0].rotation = [0, 0, 0.02827433441159227]
compact_round_bistro_table_A[0].optimize = 2
base_cabinet_run[0].position = [5.699999809265137, 1.5, 0.44999998807907104]
base_cabinet_run[0].rotation = [0, 0, 3.1415918874637283]
base_cabinet_run[0].optimize = 2
waste_bin_A[0].position = [5.66156005859375, 0.24995540082454681, 0.4000000059604645]
waste_bin_A[0].rotation = [0, 0, 1.5712727511128093]
waste_bin_A[0].optimize = 2
tall_pantry_cabinet_A[0].position = [3.0, 0.29999977350234985, 1.0499999523162842]
tall_pantry_cabinet_A[0].rotation = [0, 0, 1.5707961072014696]
tall_pantry_cabinet_A[0].optimize = 2
under_counter_cabinet[0].position = [3.4000000953674316, 2.6999995708465576, 0.44999998807907104]
under_counter_cabinet[0].rotation = [0, 0, -1.5707965387778944]
under_counter_cabinet[0].optimize = 2
side_chair_C[0].position = [1.8506289720535278, 1.5, 0.4099999964237213]
side_chair_C[0].rotation = [0, 0, 0.021991148286022624]
side_chair_C[0].optimize = 2
side_chair_B[0].position = [0.949999988079071, 0.6919474005699158, 0.4099999964237213]
side_chair_B[0].rotation = [0, 0, 1.5833626980517244]
side_chair_B[0].optimize = 2
tall_refrigerator[0].position = [4.5, 0.33999958634376526, 0.925000011920929]
tall_refrigerator[0].rotation = [0, 0, 1.5707961071996497]
tall_refrigerator[0].optimize = 2
compact_round_bistro_table_B[0].position = [2.549999952316284, 1.5, 0.375]
compact_round_bistro_table_B[0].rotation = [0, 0, 0.025132740109855806]
compact_round_bistro_table_B[0].optimize = 2
waste_bin_B[0].position = [5.749999523162842, 2.75, 0.4000000059604645]
waste_bin_B[0].rotation = [0, 0, 3.1415923966356285]
waste_bin_B[0].optimize = 2

