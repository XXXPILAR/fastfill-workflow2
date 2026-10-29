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
    Wall(corner1=[4.99, 0.24, 0.00], corner2=[5.91, 0.24, 0.00]),
    Wall(corner1=[5.91, 0.24, 0.00], corner2=[5.91, 5.38, 0.00]),
    Wall(corner1=[5.91, 5.38, 0.00], corner2=[7.17, 5.38, 0.00]),
    Wall(corner1=[7.17, 5.38, 0.00], corner2=[7.17, 8.06, 0.00]),
    Wall(corner1=[7.17, 8.06, 0.00], corner2=[6.15, 8.06, 0.00]),
    Wall(corner1=[6.15, 8.06, 0.00], corner2=[6.15, 6.71, 0.00]),
    Wall(corner1=[6.15, 6.71, 0.00], corner2=[2.60, 6.71, 0.00]),
    Wall(corner1=[2.60, 6.71, 0.00], corner2=[2.60, 10.02, 0.00]),
    Wall(corner1=[2.60, 10.02, 0.00], corner2=[0.00, 10.02, 0.00]),
    Wall(corner1=[0.00, 10.02, 0.00], corner2=[0.00, 5.38, 0.00]),
    Wall(corner1=[0.00, 5.38, 0.00], corner2=[1.88, 5.38, 0.00]),
    Wall(corner1=[1.88, 5.38, 0.00], corner2=[1.88, 0.24, 0.00]),
    Wall(corner1=[1.88, 0.24, 0.00], corner2=[2.74, 0.24, 0.00]),
    Wall(corner1=[2.74, 0.24, 0.00], corner2=[2.74, 0.00, 0.00]),
    Wall(corner1=[2.74, 0.00, 0.00], corner2=[4.99, 0.00, 0.00]),
    Wall(corner1=[4.99, 0.00, 0.00], corner2=[4.99, 0.24, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
drawer_chest = Assets(description="A tall, modern bookshelf with a sleek black metal frame and wooden shelves. It has five evenly spaced shelves and a minimalist design.", size=[0.38, 0.90, 1.85], placements=[AssetInstance() for _ in range(1)])
dining_table = Assets(description="A sleek, modern coffee table with a rectangular top and angled legs.", size=[0.85, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
side_table = Assets(description="A modern side table with a rectangular top and a single drawer. The legs are uniquely designed with a textured pattern that resembles a quilted or woven material.", size=[0.45, 0.60, 0.58], placements=[AssetInstance() for _ in range(1)])
three_seat_sofa = Assets(description="A modern sectional sofa with a curved design, upholstered in dark gray fabric. It features multiple cushions in shades of purple, black, and gray, arranged for comfort and style.", size=[1.65, 3.10, 0.85], placements=[AssetInstance() for _ in range(1)])
sideboard = Assets(description="A simple console table with a flat top surface and four legs, designed for placement against a wall. It features a minimalist design with clean lines.", size=[0.40, 1.50, 0.80], placements=[AssetInstance() for _ in range(1)])
dining_chair_A = Assets(description="An elegant armchair with a sleek black frame and upholstered seat and backrest in a soft blue fabric. The backrest features an ornate golden patterned design that adds a touch of luxury. The chair has curved armrests and slightly angled legs.", size=[0.65, 0.62, 0.95], placements=[AssetInstance() for _ in range(1)])
dining_chair_B = Assets(description="An elegant armchair with a sleek black frame and upholstered seat and backrest in a soft blue fabric. The backrest features an ornate golden patterned design that adds a touch of luxury. The chair has curved armrests and slightly angled legs.", size=[0.65, 0.62, 0.95], placements=[AssetInstance() for _ in range(1)])
lounge_chair = Assets(description="A black barber chair with a cushioned seat and backrest, featuring metallic armrests and a footrest. It has a sturdy base for stability.", size=[1.15, 0.75, 1.05], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="An elegant oval-shaped coffee table with a glossy black tabletop and ornate metallic legs. The table features intricate detailing on its legs and a sturdy base connecting them.", size=[0.75, 1.30, 0.45], placements=[AssetInstance() for _ in range(1)])
dining_chair_C = Assets(description="An elegant armchair with a sleek black frame and upholstered seat and backrest in a soft blue fabric. The backrest features an ornate golden patterned design that adds a touch of luxury. The chair has curved armrests and slightly angled legs.", size=[0.65, 0.62, 0.95], placements=[AssetInstance() for _ in range(1)])
dining_chair_D = Assets(description="An elegant armchair with a sleek black frame and upholstered seat and backrest in a soft blue fabric. The backrest features an ornate golden patterned design that adds a touch of luxury. The chair has curved armrests and slightly angled legs.", size=[0.65, 0.62, 0.95], placements=[AssetInstance() for _ in range(1)])
tv_stand = Assets(description="A long, rectangular cabinet with a flat top surface and multiple doors, some of which feature glass panels. It has a simple design with clean lines and a sturdy base.", size=[0.45, 2.10, 0.60], placements=[AssetInstance() for _ in range(1)])

drawer_chest[0].instance_id = 'drawer_chest_0'
dining_table[0].instance_id = 'dining_table_0'
side_table[0].instance_id = 'side_table_0'
three_seat_sofa[0].instance_id = 'three_seat_sofa_0'
sideboard[0].instance_id = 'sideboard_0'
dining_chair_A[0].instance_id = 'dining_chair_A_0'
dining_chair_B[0].instance_id = 'dining_chair_B_0'
lounge_chair[0].instance_id = 'lounge_chair_0'
coffee_table[0].instance_id = 'coffee_table_0'
dining_chair_C[0].instance_id = 'dining_chair_C_0'
dining_chair_D[0].instance_id = 'dining_chair_D_0'
tv_stand[0].instance_id = 'tv_stand_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'
walls[8].instance_id = 'walls_8'
walls[9].instance_id = 'walls_9'
walls[10].instance_id = 'walls_10'
walls[11].instance_id = 'walls_11'
walls[12].instance_id = 'walls_12'
walls[13].instance_id = 'walls_13'
walls[14].instance_id = 'walls_14'
walls[15].instance_id = 'walls_15'

drawer_chest[0].position = [4.630930317311627, 1.0163235437472837, 0.925]
drawer_chest[0].rotation = [0, 0, 0]
dining_table[0].position = [5.116515555752631, 3.894045869508103, 0.375]
dining_table[0].rotation = [0, 0, 0]
side_table[0].position = [4.772932758251576, 3.2664299754075072, 0.29]
side_table[0].rotation = [0, 0, 0]
three_seat_sofa[0].position = [1.724975792701577, 7.882265538278838, 0.425]
three_seat_sofa[0].rotation = [0, 0, 0]
sideboard[0].position = [4.101780911019258, 2.4789540726537673, 0.4]
sideboard[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [3.7579541081699093, 3.983143157289333, 0.475]
dining_chair_A[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [1.2909275824606472, 8.062667946195822, 0.475]
dining_chair_B[0].rotation = [0, 0, 0]
lounge_chair[0].position = [0.8434223041990292, 5.892825743338927, 0.525]
lounge_chair[0].rotation = [0, 0, 0]
coffee_table[0].position = [5.503021115126651, 0.8695320507513263, 0.225]
coffee_table[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [0.4162188089092851, 7.997276353845867, 0.475]
dining_chair_C[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [3.156530367003776, 1.4907537444314727, 0.475]
dining_chair_D[0].rotation = [0, 0, 0]
tv_stand[0].position = [2.9283046870269764, 6.323328079524426, 0.3]
tv_stand[0].rotation = [0, 0, 0]
drawer_chest[0].position = [4.630930317311627, 1.0163235437472837, 0.925]
drawer_chest[0].rotation = [0, 0, 0]
dining_table[0].position = [5.116515555752631, 3.894045869508103, 0.375]
dining_table[0].rotation = [0, 0, 0]
side_table[0].position = [4.772932758251576, 3.2664299754075072, 0.29]
side_table[0].rotation = [0, 0, 0]
three_seat_sofa[0].position = [1.724975792701577, 7.882265538278838, 0.425]
three_seat_sofa[0].rotation = [0, 0, 0]
sideboard[0].position = [4.101780911019258, 2.4789540726537673, 0.4]
sideboard[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [3.7579541081699093, 3.983143157289333, 0.475]
dining_chair_A[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [1.2909275824606472, 8.062667946195822, 0.475]
dining_chair_B[0].rotation = [0, 0, 0]
lounge_chair[0].position = [0.8434223041990292, 5.892825743338927, 0.525]
lounge_chair[0].rotation = [0, 0, 0]
coffee_table[0].position = [5.503021115126651, 0.8695320507513263, 0.225]
coffee_table[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [0.4162188089092851, 7.997276353845867, 0.475]
dining_chair_C[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [3.156530367003776, 1.4907537444314727, 0.475]
dining_chair_D[0].rotation = [0, 0, 0]
tv_stand[0].position = [2.9283046870269764, 6.323328079524426, 0.3]
tv_stand[0].rotation = [0, 0, 0]

solver.constraints = []

from math import atan2, sqrt

# The lower area is used for dining; the middle area is a sitting/TV zone.
# Keep y < 1.45 largely open for the wide entrance, and leave the cross-room
# circulation route at y = 6 clear. The narrow right-hand vestibule stays empty.
dining_table[0].position = [3.85, 1.90, 0.375]
dining_table[0].rotation = [0, 0, radians(90)]

dining_chair_A[0].position = [2.50, 1.90, 0.475]
dining_chair_A[0].rotation = [
    0, 0, atan2(4.95 - 1.90, 4.35 - 2.50)
]
dining_chair_C[0].position = [5.15, 1.90, 0.475]
dining_chair_C[0].rotation = [0, 0, radians(180)]

# Two additional chairs occupy the north side, rather than blocking the
# entrance on the south side of the dining table.
dining_chair_B[0].position = [3.35, 2.85, 0.475]
dining_chair_B[0].rotation = [0, 0, radians(270)]
dining_chair_D[0].position = [4.35, 2.85, 0.475]
dining_chair_D[0].rotation = [0, 0, radians(270)]

three_seat_sofa[0].position = [2.705, 4.95, 0.425]
three_seat_sofa[0].rotation = [0, 0, 0]
coffee_table[0].position = [4.35, 4.95, 0.225]
coffee_table[0].rotation = [0, 0, 0]
tv_stand[0].position = [5.685, 4.95, 0.30]
tv_stand[0].rotation = [0, 0, radians(180)]

side_table[0].position = [2.25, 2.90, 0.29]
side_table[0].rotation = [0, 0, 0]

# Storage occupies the solid east wall of the upper-left alcove, away from
# the window. The lounge chair leaves the west-side door approaches open.
drawer_chest[0].position = [2.41, 9.30, 0.925]
drawer_chest[0].rotation = [0, 0, radians(180)]
sideboard[0].position = [2.40, 7.60, 0.40]
sideboard[0].rotation = [0, 0, radians(180)]
lounge_chair[0].position = [1.50, 9.25, 0.525]
lounge_chair[0].rotation = [0, 0, radians(270)]

# High-priority position anchors preserve the verified non-overlapping
# footprints and door clearances. These are fixed references, not new props.
for placed_group in (
    dining_table, dining_chair_A, dining_chair_B,
    dining_chair_C, dining_chair_D, three_seat_sofa,
    coffee_table, tv_stand, side_table, drawer_chest,
    sideboard, lounge_chair,
):
    solver.distance_constraint(
        placed_group[0],
        AssetInstance(position=list(placed_group[0].position)),
        0, 0, weight=10,
    )

# Required facing relationship: chair A faces the coffee table even though
# it sits at the west end of the dining table.
solver.point_towards(dining_chair_A[0], coffee_table[0])
solver.point_towards(dining_chair_C[0], dining_table[0])

# Both north-side chairs face south, toward the dining-table surface.
solver.align_with(
    dining_chair_B[0], AssetInstance(rotation=[0, 0, radians(270)])
)
solver.align_with(dining_chair_D[0], dining_chair_B[0])

solver.align_with(
    dining_table[0], AssetInstance(rotation=[0, 0, radians(90)])
)
solver.point_towards(three_seat_sofa[0], tv_stand[0])
solver.point_towards(tv_stand[0], three_seat_sofa[0])
solver.align_with(coffee_table[0], three_seat_sofa[0])
solver.align_with(side_table[0], three_seat_sofa[0])
solver.align_with(
    drawer_chest[0], AssetInstance(rotation=[0, 0, radians(180)])
)
solver.align_with(sideboard[0], drawer_chest[0])
solver.align_with(
    lounge_chair[0], AssetInstance(rotation=[0, 0, radians(270)])
)

# Compatible wall contacts for the west-facing storage and east-facing sofa.
solver.against_wall(drawer_chest[0], walls[7])
solver.against_wall(sideboard[0], walls[7])
solver.against_wall(three_seat_sofa[0], walls[11])

# The table lies between chairs A and C: their horizontal distances sum
# exactly to the distance between the chairs. Equal chair heights and the
# anchored table center preserve the intended straight-line arrangement.
solver.distance_constraint(
    dining_chair_A[0], dining_table[0],
    sqrt(1.35 ** 2 + 0.10 ** 2),
    sqrt(1.35 ** 2 + 0.10 ** 2),
    weight=10,
)
solver.distance_constraint(
    dining_chair_C[0], dining_table[0],
    sqrt(1.30 ** 2 + 0.10 ** 2),
    sqrt(1.30 ** 2 + 0.10 ** 2),
    weight=10,
)
solver.distance_constraint(
    dining_chair_A[0], dining_chair_C[0], 2.65, 2.65, weight=10
)

# Maintain useful seating/table spacing and the TV viewing arrangement.
for north_chair_group in (dining_chair_B, dining_chair_D):
    solver.distance_constraint(
        north_chair_group[0], dining_table[0], 1.05, 1.12
    )

solver.distance_constraint(
    three_seat_sofa[0], coffee_table[0], 1.65, 1.70
)
solver.distance_constraint(
    coffee_table[0], tv_stand[0], 1.30, 1.40
)
solver.distance_constraint(
    side_table[0], three_seat_sofa[0], 2.05, 2.15
)

# All listed assets are floor-standing furniture; none needs on_top_of.

solver.constraints = []
side_table[0].position = [2.25, 2.9000000953674316, 0.28999999165534973]
side_table[0].rotation = [0, 0, 4.159219730767438e-08]
side_table[0].optimize = 2
lounge_chair[0].position = [1.5, 9.25, 0.5249999761581421]
lounge_chair[0].rotation = [0, 0, -1.5613715493341729]
lounge_chair[0].optimize = 2
dining_chair_D[0].position = [4.349999904632568, 2.8499999046325684, 0.4749999940395355]
dining_chair_D[0].rotation = [0, 0, -1.5550883677220086]
dining_chair_D[0].optimize = 2
drawer_chest[0].position = [2.4050002098083496, 9.300000190734863, 0.925000011920929]
drawer_chest[0].rotation = [0, 0, -3.141592610037852]
drawer_chest[0].optimize = 2
coffee_table[0].position = [4.349999904632568, 4.949999809265137, 0.22499999403953552]
coffee_table[0].rotation = [0, 0, 3.8222348390285136e-08]
coffee_table[0].optimize = 2
dining_table[0].position = [3.8499999046325684, 1.899999976158142, 0.375]
dining_table[0].rotation = [0, 0, 1.5959290669047523]
dining_table[0].optimize = 2
dining_chair_C[0].position = [5.153695106506348, 1.899999976158142, 0.4749999940395355]
dining_chair_C[0].rotation = [0, 0, -3.125884689672577]
dining_chair_C[0].optimize = 2
three_seat_sofa[0].position = [2.7056000232696533, 4.949999809265137, 0.42500001192092896]
three_seat_sofa[0].rotation = [0, 0, 4.3296880021010436e-08]
three_seat_sofa[0].optimize = 2
sideboard[0].position = [2.3949999809265137, 7.599999904632568, 0.4000000059604645]
sideboard[0].rotation = [0, 0, -3.1415926094784656]
sideboard[0].optimize = 2
dining_chair_A[0].position = [2.5033950805664062, 1.899999976158142, 0.4749999940395355]
dining_chair_A[0].rotation = [0, 0, 1.0412771464128618]
dining_chair_A[0].optimize = 2
dining_chair_B[0].position = [3.3499999046325684, 2.8499999046325684, 0.4749999940395355]
dining_chair_B[0].rotation = [0, 0, -1.5550883628776802]
dining_chair_B[0].optimize = 2
tv_stand[0].position = [5.665635108947754, 4.949999809265137, 0.30000001192092896]
tv_stand[0].rotation = [0, 0, -3.125884689672577]
tv_stand[0].optimize = 2

