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
    Wall(corner1=[0.00, 3.66, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[9.76, 0.00, 0.00]),
    Wall(corner1=[9.76, 0.00, 0.00], corner2=[9.76, 1.27, 0.00]),
    Wall(corner1=[9.76, 1.27, 0.00], corner2=[7.35, 1.27, 0.00]),
    Wall(corner1=[7.35, 1.27, 0.00], corner2=[7.35, 3.66, 0.00]),
    Wall(corner1=[7.35, 3.66, 0.00], corner2=[0.00, 3.66, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
lounge_chair_A = Assets(description="A modern black chair with a woven seat and backrest, featuring curved armrests that extend into the back support.", size=[0.60, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
wine_cabinet_A = Assets(description="A tall, dark wooden wardrobe with two doors featuring vertical lines and decorative elements. The wardrobe has a sleek design with a polished finish.", size=[0.45, 0.90, 1.90], placements=[AssetInstance() for _ in range(1)])
potted_plant_A = Assets(description="A tall potted plant with slender green leaves and brown stems, housed in a square pot with a striped pattern.", size=[0.65, 0.65, 1.65], placements=[AssetInstance() for _ in range(1)])
loveseat_sofa = Assets(description="A modern daybed with a sleek black frame and a gray cushioned mattress. It features decorative pillows and a throw blanket, along with a book resting on it.", size=[0.85, 1.85, 0.75], placements=[AssetInstance() for _ in range(1)])
wine_cabinet_B = Assets(description="A tall, dark wooden wardrobe with two doors featuring vertical lines and decorative elements. The wardrobe has a sleek design with a polished finish.", size=[0.45, 0.90, 1.90], placements=[AssetInstance() for _ in range(1)])
footstool = Assets(description="A decorative mask with intricate blue and white patterns resembling traditional East Asian art. It features two large eye holes and a wide mouth opening, giving it an expressive appearance.", size=[0.40, 0.40, 0.45], placements=[AssetInstance() for _ in range(1)])
lounge_chair_B = Assets(description="A modern black chair with a woven seat and backrest, featuring curved armrests that extend into the back support.", size=[0.60, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
lounge_chair_C = Assets(description="A wooden armchair with a cushioned seat and backrest, featuring an intricate lattice design on the backrest.", size=[0.75, 0.70, 0.85], placements=[AssetInstance() for _ in range(1)])
potted_plant_B = Assets(description="A potted bamboo plant with slender green leaves and brown stems, placed in a beige pot on a black reflective surface.", size=[0.60, 0.60, 1.60], placements=[AssetInstance() for _ in range(1)])
lounge_chair_D = Assets(description="A modern black chair with a woven seat and backrest, featuring curved armrests that extend into the back support.", size=[0.60, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="A modern coffee table with a sleek design featuring a rectangular marble top and a black metal frame with curved legs.", size=[0.60, 1.15, 0.42], placements=[AssetInstance() for _ in range(1)])
shelf = Assets(description="A tall, dark wooden bookshelf with five shelves, designed for storing books or decorative items. It has a sturdy frame and a simple, modern design.", size=[0.35, 0.80, 1.85], placements=[AssetInstance() for _ in range(1)])
tv_stand = Assets(description="A dark brown sideboard with intricate floral and bird designs on its panels. It features multiple drawers and doors, each adorned with decorative patterns. The sideboard has a classic design with ornate details and stands on small legs.", size=[0.45, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
dining_table = Assets(description="A sleek dining table with a rectangular top and four angled legs that converge at the center for stability.", size=[0.85, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
lounge_chair_E = Assets(description="A modern black chair with a woven seat and backrest, featuring curved armrests that extend into the back support.", size=[0.60, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
lounge_chair_F = Assets(description="A wooden armchair with a cushioned seat and backrest, featuring an intricate lattice design on the backrest.", size=[0.75, 0.70, 0.85], placements=[AssetInstance() for _ in range(1)])

lounge_chair_A[0].instance_id = 'lounge_chair_A_0'
wine_cabinet_A[0].instance_id = 'wine_cabinet_A_0'
potted_plant_A[0].instance_id = 'potted_plant_A_0'
loveseat_sofa[0].instance_id = 'loveseat_sofa_0'
wine_cabinet_B[0].instance_id = 'wine_cabinet_B_0'
footstool[0].instance_id = 'footstool_0'
lounge_chair_B[0].instance_id = 'lounge_chair_B_0'
lounge_chair_C[0].instance_id = 'lounge_chair_C_0'
potted_plant_B[0].instance_id = 'potted_plant_B_0'
lounge_chair_D[0].instance_id = 'lounge_chair_D_0'
coffee_table[0].instance_id = 'coffee_table_0'
shelf[0].instance_id = 'shelf_0'
tv_stand[0].instance_id = 'tv_stand_0'
dining_table[0].instance_id = 'dining_table_0'
lounge_chair_E[0].instance_id = 'lounge_chair_E_0'
lounge_chair_F[0].instance_id = 'lounge_chair_F_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

lounge_chair_A[0].position = [0.6814598287181391, 3.5218895075144374, 0.4]
lounge_chair_A[0].rotation = [0, 0, 0]
wine_cabinet_A[0].position = [6.435471832854102, 2.326836787286516, 0.95]
wine_cabinet_A[0].rotation = [0, 0, 0]
potted_plant_A[0].position = [5.282809299159279, 0.4167855953929758, 0.825]
potted_plant_A[0].rotation = [0, 0, 0]
loveseat_sofa[0].position = [5.690644958228402, 1.3430511257360882, 0.375]
loveseat_sofa[0].rotation = [0, 0, 0]
wine_cabinet_B[0].position = [0.6691770744179357, 3.2099839229932234, 0.95]
wine_cabinet_B[0].rotation = [0, 0, 0]
footstool[0].position = [3.65367271605874, 3.472685055585013, 0.225]
footstool[0].rotation = [0, 0, 0]
lounge_chair_B[0].position = [0.472535967059828, 2.056357118842908, 0.4]
lounge_chair_B[0].rotation = [0, 0, 0]
lounge_chair_C[0].position = [3.4362861358833565, 0.44180241876329623, 0.425]
lounge_chair_C[0].rotation = [0, 0, 0]
potted_plant_B[0].position = [4.9115912752646205, 1.6073619218344395, 0.8]
potted_plant_B[0].rotation = [0, 0, 0]
lounge_chair_D[0].position = [1.134000669375225, 1.3354983409331522, 0.4]
lounge_chair_D[0].rotation = [0, 0, 0]
coffee_table[0].position = [7.162036446785241, 1.864994269740511, 0.21]
coffee_table[0].rotation = [0, 0, 0]
shelf[0].position = [4.444086110439138, 0.4594669323187181, 0.925]
shelf[0].rotation = [0, 0, 0]
tv_stand[0].position = [1.6490935078508406, 1.4084037444068982, 0.375]
tv_stand[0].rotation = [0, 0, 0]
dining_table[0].position = [1.5447536670120667, 1.8527946590478017, 0.375]
dining_table[0].rotation = [0, 0, 0]
lounge_chair_E[0].position = [4.155973064800754, 0.5067346718020946, 0.4]
lounge_chair_E[0].rotation = [0, 0, 0]
lounge_chair_F[0].position = [1.0992345761921993, 2.9675217947333477, 0.425]
lounge_chair_F[0].rotation = [0, 0, 0]
lounge_chair_A[0].position = [0.6814598287181391, 3.5218895075144374, 0.4]
lounge_chair_A[0].rotation = [0, 0, 0]
wine_cabinet_A[0].position = [6.435471832854102, 2.326836787286516, 0.95]
wine_cabinet_A[0].rotation = [0, 0, 0]
potted_plant_A[0].position = [5.282809299159279, 0.4167855953929758, 0.825]
potted_plant_A[0].rotation = [0, 0, 0]
loveseat_sofa[0].position = [5.690644958228402, 1.3430511257360882, 0.375]
loveseat_sofa[0].rotation = [0, 0, 0]
wine_cabinet_B[0].position = [0.6691770744179357, 3.2099839229932234, 0.95]
wine_cabinet_B[0].rotation = [0, 0, 0]
footstool[0].position = [3.65367271605874, 3.472685055585013, 0.225]
footstool[0].rotation = [0, 0, 0]
lounge_chair_B[0].position = [0.472535967059828, 2.056357118842908, 0.4]
lounge_chair_B[0].rotation = [0, 0, 0]
lounge_chair_C[0].position = [3.4362861358833565, 0.44180241876329623, 0.425]
lounge_chair_C[0].rotation = [0, 0, 0]
potted_plant_B[0].position = [4.9115912752646205, 1.6073619218344395, 0.8]
potted_plant_B[0].rotation = [0, 0, 0]
lounge_chair_D[0].position = [1.134000669375225, 1.3354983409331522, 0.4]
lounge_chair_D[0].rotation = [0, 0, 0]
coffee_table[0].position = [7.162036446785241, 1.864994269740511, 0.21]
coffee_table[0].rotation = [0, 0, 0]
shelf[0].position = [4.444086110439138, 0.4594669323187181, 0.925]
shelf[0].rotation = [0, 0, 0]
tv_stand[0].position = [1.6490935078508406, 1.4084037444068982, 0.375]
tv_stand[0].rotation = [0, 0, 0]
dining_table[0].position = [1.5447536670120667, 1.8527946590478017, 0.375]
dining_table[0].rotation = [0, 0, 0]
lounge_chair_E[0].position = [4.155973064800754, 0.5067346718020946, 0.4]
lounge_chair_E[0].rotation = [0, 0, 0]
lounge_chair_F[0].position = [1.0992345761921993, 2.9675217947333477, 0.425]
lounge_chair_F[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the supplied wall coordinates directly: the room occupies x >= 0, y >= 0.
# Dining is on the left, seating on the right, and the narrow eastern extension
# is left empty for access to its doors.
#
# Each entry specifies the bounding-box center and upright yaw. Rotating the
# sofa/table by 90 degrees makes their longer local-y dimension run along x.
layout_specs = [
    (lounge_chair_A, (1.05, 2.00, 0.400),   0),
    (wine_cabinet_A, (0.60, 3.435, 0.950), 270),
    (potted_plant_A, (0.35, 1.50, 0.825),   0),
    (loveseat_sofa,  (5.25, 3.235, 0.375), 270),
    (wine_cabinet_B, (3.20, 3.435, 0.950), 270),
    # The asset description identifies a decorative mask rather than a usable
    # stool; display this small object on the coffee table.
    (footstool,      (5.25, 2.00, 0.645),   0),
    (lounge_chair_B, (3.00, 2.00, 0.400), 180),
    (lounge_chair_C, (4.10, 2.00, 0.425),   0),
    (potted_plant_B, (6.95, 3.30, 0.800), 180),
    (lounge_chair_D, (2.00, 0.65, 0.400),  90),
    (coffee_table,   (5.25, 2.00, 0.210),  90),
    (shelf,          (7.175, 2.20, 0.925), 180),
    (tv_stand,       (6.50, 0.225, 0.375),  90),
    (dining_table,   (2.00, 2.00, 0.375),   0),
    (lounge_chair_E, (2.00, 3.25, 0.400), 270),
    (lounge_chair_F, (6.45, 2.00, 0.425), 180),
]

# Preserve the existing asset objects and placement lists.
# Fixed-point constraints retain these collision-free locations, including
# the clear approaches to all five doors.
for asset_group, center_xyz, yaw_degrees in layout_specs:
    asset_group[0].position = list(center_xyz)
    asset_group[0].rotation = [0, 0, radians(yaw_degrees)]

    solver.distance_constraint(
        asset_group[0],
        AssetInstance(position=list(center_xyz)),
        min_distance=0,
        max_distance=0,
        weight=10,
    )

# Height support for the decorative object: its bottom is at z=0.42,
# exactly the coffee-table top. All other objects stand on the floor.
solver.on_top_of(footstool[0], coffee_table[0])

# Primary functional orientations. A and B sit on opposite sides of the
# dining table, satisfying the requested A--table--B arrangement.
for dining_seat in (
    lounge_chair_A[0],
    lounge_chair_B[0],
    lounge_chair_D[0],
    lounge_chair_E[0],
):
    solver.point_towards(dining_seat, dining_table[0])

for living_seat in (
    loveseat_sofa[0],
    lounge_chair_C[0],
    lounge_chair_F[0],
):
    solver.point_towards(living_seat, coffee_table[0])

# Explicit orientation constraints for the remaining assets. Fixed rotation
# references are not additional scene furnishings.
for oriented_group, yaw_degrees in (
    (wine_cabinet_A, 270),
    (wine_cabinet_B, 270),
    (potted_plant_A, 0),
    (potted_plant_B, 180),
    (footstool, 0),
    (coffee_table, 90),
    (shelf, 180),
    (tv_stand, 90),
    (dining_table, 0),
):
    solver.align_with(
        oriented_group[0],
        AssetInstance(rotation=[0, 0, radians(yaw_degrees)]),
    )

# Wall-backed furniture uses solid walls, not the windowed western wall.
solver.against_wall(wine_cabinet_A[0], walls[5])
solver.against_wall(wine_cabinet_B[0], walls[5])
solver.against_wall(loveseat_sofa[0], walls[5])
solver.against_wall(shelf[0], walls[4])
# This sideboard fits between the door at x=5.04 and the eastern extension.
solver.against_wall(tv_stand[0], walls[1])

# Secondary semantic constraints preserve useful furniture relationships.
# Distances include vertical center offsets, as required by the solver.
def center_distance(first_instance, second_instance):
    return sum(
        (first_instance.position[axis] - second_instance.position[axis]) ** 2
        for axis in range(3)
    ) ** 0.5

for dining_seat in (
    lounge_chair_A[0],
    lounge_chair_B[0],
    lounge_chair_D[0],
    lounge_chair_E[0],
):
    dining_spacing = center_distance(dining_seat, dining_table[0])
    solver.distance_constraint(
        dining_seat, dining_table[0],
        dining_spacing - 0.05, dining_spacing + 0.05,
    )

for living_seat in (
    loveseat_sofa[0],
    lounge_chair_C[0],
    lounge_chair_F[0],
):
    seating_spacing = center_distance(living_seat, coffee_table[0])
    solver.distance_constraint(
        living_seat, coffee_table[0],
        seating_spacing - 0.05, seating_spacing + 0.05,
    )

# Keep the decorative piece centered on its supporting tabletop.
solver.distance_constraint(
    footstool[0], coffee_table[0], 0.435, 0.435
)

solver.constraints = []
lounge_chair_A[0].position = [1.0499999523162842, 2.0, 0.4000000059604645]
lounge_chair_A[0].rotation = [0, 0, 0.01256637125682779]
lounge_chair_A[0].optimize = 2
potted_plant_B[0].position = [6.949999809265137, 3.299999952316284, 0.800000011920929]
potted_plant_B[0].rotation = [0, 0, -3.1321678761290697]
potted_plant_B[0].optimize = 2
wine_cabinet_B[0].position = [3.200000047683716, 3.4299163818359375, 0.949999988079071]
wine_cabinet_B[0].rotation = [0, 0, -1.570918388485033]
wine_cabinet_B[0].optimize = 2
loveseat_sofa[0].position = [5.25, 3.2299866676330566, 0.375]
loveseat_sofa[0].rotation = [0, 0, -1.5706359680788675]
loveseat_sofa[0].optimize = 2
footstool[0].position = [5.25, 2.0, 0.6449999809265137]
footstool[0].rotation = [0, 0, 0.0157079639172164]
footstool[0].optimize = 2
lounge_chair_B[0].position = [3.0, 2.0, 0.4000000059604645]
lounge_chair_B[0].rotation = [0, 0, -3.1290262823329655]
lounge_chair_B[0].optimize = 2
lounge_chair_C[0].position = [4.099999904632568, 2.0, 0.42500001192092896]
lounge_chair_C[0].rotation = [0, 0, 0.01256637125682779]
lounge_chair_C[0].optimize = 2
potted_plant_A[0].position = [0.3499999940395355, 1.5, 0.824999988079071]
potted_plant_A[0].rotation = [0, 0, 0.00942477746072377]
potted_plant_A[0].optimize = 2
lounge_chair_D[0].position = [2.0, 0.6499999761581421, 0.4000000059604645]
lounge_chair_D[0].rotation = [0, 0, 1.5833626980517244]
lounge_chair_D[0].optimize = 2
coffee_table[0].position = [5.25, 2.0, 0.20999999344348907]
coffee_table[0].rotation = [0, 0, 1.605353845621573]
coffee_table[0].optimize = 2
wine_cabinet_A[0].position = [0.6000000238418579, 3.4299163818359375, 0.949999988079071]
wine_cabinet_A[0].rotation = [0, 0, -1.570918388485033]
wine_cabinet_A[0].optimize = 2
lounge_chair_E[0].position = [2.0, 3.25, 0.4000000059604645]
lounge_chair_E[0].rotation = [0, 0, -1.5582299555380688]
lounge_chair_E[0].optimize = 2
dining_table[0].position = [2.0, 2.0, 0.375]
dining_table[0].rotation = [0, 0, 0.03455751882667646]
dining_table[0].optimize = 2
lounge_chair_F[0].position = [6.449999809265137, 2.0, 0.42500001192092896]
lounge_chair_F[0].rotation = [0, 0, -3.1290262823329655]
lounge_chair_F[0].optimize = 2
shelf[0].position = [7.17796516418457, 2.200000047683716, 0.925000011920929]
shelf[0].rotation = [0, 0, 3.1414709103011886]
shelf[0].optimize = 2
tv_stand[0].position = [6.5, 0.22512689232826233, 0.375]
tv_stand[0].rotation = [0, 0, 1.5706740844182057]
tv_stand[0].optimize = 2

