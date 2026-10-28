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
dining_chair_A = Assets(description="An elegant armchair with a sleek black frame and upholstered seat and backrest in a soft blue fabric. The backrest features an ornate golden patterned design that adds a touch of luxury. The chair has curved armrests and slightly angled legs.", size=[0.64, 0.62, 0.92], placements=[AssetInstance() for _ in range(1)])
side_table = Assets(description="A modern side table with a rectangular top and a single drawer. The legs are uniquely designed with a textured pattern that resembles a quilted or woven material.", size=[0.45, 0.55, 0.58], placements=[AssetInstance() for _ in range(1)])
tv_stand = Assets(description="A long, rectangular cabinet with a flat top surface and multiple doors, some of which feature glass panels. It has a simple design with clean lines and a sturdy base.", size=[0.45, 2.00, 0.62], placements=[AssetInstance() for _ in range(1)])
dining_chair_B = Assets(description="An elegant armchair with a sleek black frame and upholstered seat and backrest in a soft blue fabric. The backrest features an ornate golden patterned design that adds a touch of luxury. The chair has curved armrests and slightly angled legs.", size=[0.64, 0.62, 0.92], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="An elegant dining table with a curved metal frame and a dark blue tablecloth adorned with white floral patterns.", size=[0.75, 1.30, 0.45], placements=[AssetInstance() for _ in range(1)])
dining_chair_C = Assets(description="An elegant armchair with a sleek black frame and upholstered seat and backrest in a soft blue fabric. The backrest features an ornate golden patterned design that adds a touch of luxury. The chair has curved armrests and slightly angled legs.", size=[0.64, 0.62, 0.92], placements=[AssetInstance() for _ in range(1)])
sideboard = Assets(description="A modern console table with a wooden top and black base, featuring two drawers and two cabinet doors. It is adorned with decorative items such as a small bicycle model and potted plants.", size=[0.45, 1.60, 0.82], placements=[AssetInstance() for _ in range(1)])
dining_table = Assets(description="A sleek, modern coffee table with a rectangular top and angled legs.", size=[0.90, 1.80, 0.76], placements=[AssetInstance() for _ in range(1)])
drawer_chest = Assets(description="A tall, modern bookshelf with a sleek black metal frame and wooden shelves. It has five evenly spaced shelves and a minimalist design.", size=[0.38, 0.90, 1.85], placements=[AssetInstance() for _ in range(1)])
three_seat_sofa = Assets(description="A modern sectional sofa with a curved design, upholstered in dark gray fabric. It features multiple cushions in shades of purple, black, and gray, arranged for comfort and style.", size=[1.05, 2.55, 0.86], placements=[AssetInstance() for _ in range(1)])
lounge_chair = Assets(description="A black barber chair with a cushioned seat and backrest, featuring metallic armrests and a footrest. It has a sturdy base for stability.", size=[1.00, 0.75, 1.05], placements=[AssetInstance() for _ in range(1)])
dining_chair_D = Assets(description="An elegant armchair with a sleek black frame and upholstered seat and backrest in a soft blue fabric. The backrest features an ornate golden patterned design that adds a touch of luxury. The chair has curved armrests and slightly angled legs.", size=[0.64, 0.62, 0.92], placements=[AssetInstance() for _ in range(1)])

dining_chair_A[0].instance_id = 'dining_chair_A_0'
side_table[0].instance_id = 'side_table_0'
tv_stand[0].instance_id = 'tv_stand_0'
dining_chair_B[0].instance_id = 'dining_chair_B_0'
coffee_table[0].instance_id = 'coffee_table_0'
dining_chair_C[0].instance_id = 'dining_chair_C_0'
sideboard[0].instance_id = 'sideboard_0'
dining_table[0].instance_id = 'dining_table_0'
drawer_chest[0].instance_id = 'drawer_chest_0'
three_seat_sofa[0].instance_id = 'three_seat_sofa_0'
lounge_chair[0].instance_id = 'lounge_chair_0'
dining_chair_D[0].instance_id = 'dining_chair_D_0'
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

dining_chair_A[0].position = [1.0678024536232171, 8.813701998074954, 0.46]
dining_chair_A[0].rotation = [0, 0, 0]
side_table[0].position = [2.258867882903204, 2.795041293999963, 0.29]
side_table[0].rotation = [0, 0, 0]
tv_stand[0].position = [4.312855901063195, 0.9424808540323385, 0.31]
tv_stand[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [0.15195315716183175, 7.177208248748914, 0.46]
dining_chair_B[0].rotation = [0, 0, 0]
coffee_table[0].position = [5.0227695853453325, 3.490659072875936, 0.225]
coffee_table[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [1.4162971077662507, 8.987888180550186, 0.46]
dining_chair_C[0].rotation = [0, 0, 0]
sideboard[0].position = [5.701124711266981, 1.4287381316413383, 0.41]
sideboard[0].rotation = [0, 0, 0]
dining_table[0].position = [2.177548442603435, 2.8188184895046247, 0.38]
dining_table[0].rotation = [0, 0, 0]
drawer_chest[0].position = [3.2782490095111143, 0.460137611240198, 0.925]
drawer_chest[0].rotation = [0, 0, 0]
three_seat_sofa[0].position = [1.8922174923694757, 0.8568410078175416, 0.43]
three_seat_sofa[0].rotation = [0, 0, 0]
lounge_chair[0].position = [5.318923536458979, 3.583629392232062, 0.525]
lounge_chair[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [2.2929470695930556, 6.341609229227167, 0.46]
dining_chair_D[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [1.0678024536232171, 8.813701998074954, 0.46]
dining_chair_A[0].rotation = [0, 0, 0]
side_table[0].position = [2.258867882903204, 2.795041293999963, 0.29]
side_table[0].rotation = [0, 0, 0]
tv_stand[0].position = [4.312855901063195, 0.9424808540323385, 0.31]
tv_stand[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [0.15195315716183175, 7.177208248748914, 0.46]
dining_chair_B[0].rotation = [0, 0, 0]
coffee_table[0].position = [5.0227695853453325, 3.490659072875936, 0.225]
coffee_table[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [1.4162971077662507, 8.987888180550186, 0.46]
dining_chair_C[0].rotation = [0, 0, 0]
sideboard[0].position = [5.701124711266981, 1.4287381316413383, 0.41]
sideboard[0].rotation = [0, 0, 0]
dining_table[0].position = [2.177548442603435, 2.8188184895046247, 0.38]
dining_table[0].rotation = [0, 0, 0]
drawer_chest[0].position = [3.2782490095111143, 0.460137611240198, 0.925]
drawer_chest[0].rotation = [0, 0, 0]
three_seat_sofa[0].position = [1.8922174923694757, 0.8568410078175416, 0.43]
three_seat_sofa[0].rotation = [0, 0, 0]
lounge_chair[0].position = [5.318923536458979, 3.583629392232062, 0.525]
lounge_chair[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [2.2929470695930556, 6.341609229227167, 0.46]
dining_chair_D[0].rotation = [0, 0, 0]

solver.constraints = []

# The room is divided into two functional zones:
# - a living area in the broad lower portion of the room;
# - a dining area near the upper side of that lower portion.
# This leaves the upper-left room and the routes to all door openings unobstructed.

# Place the living-room furniture.
three_seat_sofa[0].position = [2.43, 2.10, 0.43]
three_seat_sofa[0].rotation = [0, 0, radians(0)]

tv_stand[0].position = [5.68, 2.10, 0.31]
tv_stand[0].rotation = [0, 0, radians(180)]

coffee_table[0].position = [4.05, 2.10, 0.225]
coffee_table[0].rotation = [0, 0, radians(0)]

lounge_chair[0].position = [4.25, 3.35, 0.525]
lounge_chair[0].rotation = [0, 0, radians(-90)]

side_table[0].position = [2.13, 3.95, 0.29]
side_table[0].rotation = [0, 0, radians(0)]

# Place the dining table lengthwise along the x-axis. The chairs are arranged
# in two facing pairs on its long sides, while preserving circulation at the
# right-side doors and the passage into the upper-left part of the plan.
dining_table[0].position = [4.00, 5.25, 0.38]
dining_table[0].rotation = [0, 0, radians(90)]

dining_chair_A[0].position = [3.55, 4.35, 0.46]
dining_chair_A[0].rotation = [0, 0, radians(90)]

dining_chair_B[0].position = [3.55, 6.15, 0.46]
dining_chair_B[0].rotation = [0, 0, radians(-90)]

dining_chair_C[0].position = [4.45, 4.35, 0.46]
dining_chair_C[0].rotation = [0, 0, radians(90)]

dining_chair_D[0].position = [4.45, 6.15, 0.46]
dining_chair_D[0].rotation = [0, 0, radians(-90)]

# Put storage against peripheral walls so that it does not occupy the main
# seating, dining, or doorway circulation zones.
sideboard[0].position = [2.375, 8.65, 0.41]
sideboard[0].rotation = [0, 0, radians(180)]

drawer_chest[0].position = [5.45, 0.43, 0.925]
drawer_chest[0].rotation = [0, 0, radians(90)]


# High-priority positional anchors preserve the proposed zoning and clearances.
sofa_anchor = AssetInstance(position=[2.43, 2.10, 0.43])
tv_anchor = AssetInstance(position=[5.68, 2.10, 0.31])
coffee_anchor = AssetInstance(position=[4.05, 2.10, 0.225])
lounge_anchor = AssetInstance(position=[4.25, 3.35, 0.525])
side_table_anchor = AssetInstance(position=[2.13, 3.95, 0.29])

dining_table_anchor = AssetInstance(position=[4.00, 5.25, 0.38])
chair_A_anchor = AssetInstance(position=[3.55, 4.35, 0.46])
chair_B_anchor = AssetInstance(position=[3.55, 6.15, 0.46])
chair_C_anchor = AssetInstance(position=[4.45, 4.35, 0.46])
chair_D_anchor = AssetInstance(position=[4.45, 6.15, 0.46])

sideboard_anchor = AssetInstance(position=[2.375, 8.65, 0.41])
drawer_anchor = AssetInstance(position=[5.45, 0.43, 0.925])

solver.distance_constraint(three_seat_sofa[0], sofa_anchor, 0, 0, weight=10)
solver.distance_constraint(tv_stand[0], tv_anchor, 0, 0, weight=10)
solver.distance_constraint(coffee_table[0], coffee_anchor, 0, 0, weight=10)
solver.distance_constraint(lounge_chair[0], lounge_anchor, 0, 0, weight=10)
solver.distance_constraint(side_table[0], side_table_anchor, 0, 0, weight=10)

solver.distance_constraint(dining_table[0], dining_table_anchor, 0, 0, weight=10)
solver.distance_constraint(dining_chair_A[0], chair_A_anchor, 0, 0, weight=10)
solver.distance_constraint(dining_chair_B[0], chair_B_anchor, 0, 0, weight=10)
solver.distance_constraint(dining_chair_C[0], chair_C_anchor, 0, 0, weight=10)
solver.distance_constraint(dining_chair_D[0], chair_D_anchor, 0, 0, weight=10)

solver.distance_constraint(sideboard[0], sideboard_anchor, 0, 0, weight=10)
solver.distance_constraint(drawer_chest[0], drawer_anchor, 0, 0, weight=10)


# Orient the living-room seating toward the central table and media cabinet.
solver.point_towards(three_seat_sofa[0], coffee_table[0])
solver.point_towards(tv_stand[0], coffee_table[0])
solver.point_towards(lounge_chair[0], coffee_table[0])
solver.align_with(coffee_table[0], three_seat_sofa[0])
solver.align_with(side_table[0], three_seat_sofa[0])

# Keep the wall furniture against its intended walls.
solver.against_wall(three_seat_sofa[0], walls[11])
solver.against_wall(tv_stand[0], walls[1])
solver.against_wall(side_table[0], walls[11])
solver.against_wall(sideboard[0], walls[7])
solver.against_wall(drawer_chest[0], walls[0])

# Orient the two chair rows toward the dining table. In particular, chair A
# and chair B are on opposite sides, so the dining table lies between them.
solver.point_towards(dining_chair_A[0], dining_table[0])
solver.point_towards(dining_chair_B[0], dining_table[0])
solver.point_towards(dining_chair_C[0], dining_table[0])
solver.point_towards(dining_chair_D[0], dining_table[0])
solver.align_with(dining_table[0], dining_chair_A[0])

# Relational distances retain usable seating gaps if feasibility adjustment
# moves the dining group. The A-to-B constraint also preserves the requested
# table-between-chairs arrangement.
solver.distance_constraint(
    dining_chair_A[0], dining_chair_B[0], 1.70, 1.90, weight=5
)
solver.distance_constraint(
    dining_table[0], dining_chair_A[0], 0.90, 1.05, weight=5
)
solver.distance_constraint(
    dining_table[0], dining_chair_B[0], 0.90, 1.05, weight=5
)
solver.distance_constraint(
    dining_table[0], dining_chair_C[0], 0.90, 1.05, weight=5
)
solver.distance_constraint(
    dining_table[0], dining_chair_D[0], 0.90, 1.05, weight=5
)

# Preserve practical spacing in the living group.
solver.distance_constraint(
    three_seat_sofa[0], coffee_table[0], 1.45, 1.80, weight=3
)
solver.distance_constraint(
    tv_stand[0], coffee_table[0], 1.45, 1.80, weight=3
)
solver.distance_constraint(
    lounge_chair[0], coffee_table[0], 1.10, 1.45, weight=3
)

# Explicit orientation references for storage pieces, which do not naturally
# point toward another functional object.
sideboard_orientation = AssetInstance(rotation=[0, 0, radians(180)])
drawer_orientation = AssetInstance(rotation=[0, 0, radians(90)])
solver.align_with(sideboard[0], sideboard_orientation)
solver.align_with(drawer_chest[0], drawer_orientation)

solver.constraints = []
side_table[0].position = [2.1259636878967285, 3.950000047683716, 0.28999999165534973]
side_table[0].rotation = [0, 0, 0.07651796635783219]
side_table[0].optimize = 2
three_seat_sofa[0].position = [3.236079216003418, 2.0999999046325684, 0.4300000071525574]
three_seat_sofa[0].rotation = [0, 0, 0.9957796278987161]
three_seat_sofa[0].optimize = 2
drawer_chest[0].position = [5.451329708099365, 0.4303947985172272, 0.925000011920929]
drawer_chest[0].rotation = [0, 0, 1.5714093053808695]
drawer_chest[0].optimize = 2
tv_stand[0].position = [5.681333065032959, 2.0999999046325684, 0.3100000023841858]
tv_stand[0].rotation = [0, 0, 3.1410761789618307]
tv_stand[0].optimize = 2
dining_chair_D[0].position = [4.449999809265137, 6.150000095367432, 0.46000000834465027]
dining_chair_D[0].rotation = [0, 0, -1.5582299555380688]
dining_chair_D[0].optimize = 2
dining_chair_C[0].position = [4.449999809265137, 4.349999904632568, 0.46000000834465027]
dining_chair_C[0].rotation = [0, 0, 1.5833626980517244]
dining_chair_C[0].optimize = 2
dining_chair_A[0].position = [3.549999952316284, 4.349999904632568, 0.46000000834465027]
dining_chair_A[0].rotation = [0, 0, 1.589645882193713]
dining_chair_A[0].optimize = 2
dining_chair_B[0].position = [3.549999952316284, 6.150000095367432, 0.46000000834465027]
dining_chair_B[0].rotation = [0, 0, -1.5550883628776802]
dining_chair_B[0].optimize = 2
sideboard[0].position = [2.369720935821533, 8.649999618530273, 0.4099999964237213]
sideboard[0].rotation = [0, 0, -3.140962629586671]
sideboard[0].optimize = 2
coffee_table[0].position = [4.050000190734863, 2.0999999046325684, 0.22499999403953552]
coffee_table[0].rotation = [0, 0, 0.917308555521291]
coffee_table[0].optimize = 2
dining_table[0].position = [4.0, 5.25, 0.3799999952316284]
dining_table[0].rotation = [0, 0, 1.5898800821992016]
dining_table[0].optimize = 2
lounge_chair[0].position = [4.25, 3.3499999046325684, 0.5249999761581421]
lounge_chair[0].rotation = [0, 0, -1.5582299555380688]
lounge_chair[0].optimize = 2

