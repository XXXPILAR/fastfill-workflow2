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
    Wall(corner1=[7.00, 0.00, 0.00], corner2=[7.00, 6.00, 0.00]),
    Wall(corner1=[7.00, 6.00, 0.00], corner2=[0.00, 6.00, 0.00]),
    Wall(corner1=[0.00, 6.00, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[7.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
tv_stand = Assets(description="large modern low-profile tv stand in dark walnut wood finish", size=[0.45, 2.20, 0.55], placements=[AssetInstance() for _ in range(1)])
floor_lamp_A = Assets(description="tall arched floor lamp with large dome shade in black", size=[1.70, 0.55, 2.10], placements=[AssetInstance() for _ in range(1)])
floor_side_table_A = Assets(description="modern round side table with dark wood surface and slender metal legs", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
floor_lamp_B = Assets(description="tall arched floor lamp with large dome shade in black", size=[1.70, 0.55, 2.10], placements=[AssetInstance() for _ in range(1)])
floor_bookshelf = Assets(description="extra tall and wide open-shelf wooden bookshelf with multiple compartments", size=[0.40, 2.40, 2.30], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="large rectangular wooden coffee table with open storage shelf below", size=[0.80, 1.40, 0.45], placements=[AssetInstance() for _ in range(1)])
sectional_sofa = Assets(description="large modern l-shaped sectional sofa in medium grey fabric with deep cushions", size=[2.40, 3.40, 0.85], placements=[AssetInstance() for _ in range(1)])
floor_pouf_A = Assets(description="large knitted fabric floor pouf in soft neutral color", size=[0.75, 0.75, 0.40], placements=[AssetInstance() for _ in range(1)])
floor_pouf_B = Assets(description="large knitted fabric floor pouf in soft neutral color", size=[0.75, 0.75, 0.40], placements=[AssetInstance() for _ in range(1)])
floor_side_table_B = Assets(description="modern round side table with dark wood surface and slender metal legs", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])

tv_stand[0].instance_id = 'tv_stand_0'
floor_lamp_A[0].instance_id = 'floor_lamp_A_0'
floor_side_table_A[0].instance_id = 'floor_side_table_A_0'
floor_lamp_B[0].instance_id = 'floor_lamp_B_0'
floor_bookshelf[0].instance_id = 'floor_bookshelf_0'
coffee_table[0].instance_id = 'coffee_table_0'
sectional_sofa[0].instance_id = 'sectional_sofa_0'
floor_pouf_A[0].instance_id = 'floor_pouf_A_0'
floor_pouf_B[0].instance_id = 'floor_pouf_B_0'
floor_side_table_B[0].instance_id = 'floor_side_table_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

tv_stand[0].position = [4.172934092618622, 1.527196577186266, 0.275]
tv_stand[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [1.027367411537125, 5.061392483415211, 1.05]
floor_lamp_A[0].rotation = [0, 0, 0]
floor_side_table_A[0].position = [0.6401944475596542, 1.5175612161166225, 0.275]
floor_side_table_A[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [2.9229802895195958, 1.5547401642208585, 1.05]
floor_lamp_B[0].rotation = [0, 0, 0]
floor_bookshelf[0].position = [0.7322452373782247, 1.1752601982834205, 1.15]
floor_bookshelf[0].rotation = [0, 0, 0]
coffee_table[0].position = [0.3470184473313347, 4.211301315995211, 0.225]
coffee_table[0].rotation = [0, 0, 0]
sectional_sofa[0].position = [4.500058598285417, 5.208020409472326, 0.425]
sectional_sofa[0].rotation = [0, 0, 0]
floor_pouf_A[0].position = [0.7269365468541743, 0.9753899203427583, 0.2]
floor_pouf_A[0].rotation = [0, 0, 0]
floor_pouf_B[0].position = [0.16556344870704842, 2.2342231292349677, 0.2]
floor_pouf_B[0].rotation = [0, 0, 0]
floor_side_table_B[0].position = [4.364744379882175, 4.0174257289106245, 0.275]
floor_side_table_B[0].rotation = [0, 0, 0]
tv_stand[0].position = [4.172934092618622, 1.527196577186266, 0.275]
tv_stand[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [1.027367411537125, 5.061392483415211, 1.05]
floor_lamp_A[0].rotation = [0, 0, 0]
floor_side_table_A[0].position = [0.6401944475596542, 1.5175612161166225, 0.275]
floor_side_table_A[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [2.9229802895195958, 1.5547401642208585, 1.05]
floor_lamp_B[0].rotation = [0, 0, 0]
floor_bookshelf[0].position = [0.7322452373782247, 1.1752601982834205, 1.15]
floor_bookshelf[0].rotation = [0, 0, 0]
coffee_table[0].position = [0.3470184473313347, 4.211301315995211, 0.225]
coffee_table[0].rotation = [0, 0, 0]
sectional_sofa[0].position = [4.500058598285417, 5.208020409472326, 0.425]
sectional_sofa[0].rotation = [0, 0, 0]
floor_pouf_A[0].position = [0.7269365468541743, 0.9753899203427583, 0.2]
floor_pouf_A[0].rotation = [0, 0, 0]
floor_pouf_B[0].position = [0.16556344870704842, 2.2342231292349677, 0.2]
floor_pouf_B[0].rotation = [0, 0, 0]
floor_side_table_B[0].position = [4.364744379882175, 4.0174257289106245, 0.275]
floor_side_table_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the media and storage units against opposite side walls, leaving the
# middle of the room available for the seating group.
tv_stand[0].position = [6.775, 3.00, 0.275]
tv_stand[0].rotation = [0, 0, radians(180)]

floor_bookshelf[0].position = [0.20, 4.50, 1.15]
floor_bookshelf[0].rotation = [0, 0, radians(0)]

# The sectional faces +x toward the poufs and TV. Its center lies between the
# two lamps along the y-axis.
sectional_sofa[0].position = [3.90, 3.00, 0.425]
sectional_sofa[0].rotation = [0, 0, radians(0)]

floor_lamp_A[0].position = [4.10, 5.45, 1.05]
floor_lamp_A[0].rotation = [0, 0, radians(0)]

floor_lamp_B[0].position = [4.10, 0.55, 1.05]
floor_lamp_B[0].rotation = [0, 0, radians(90)]

# This is o0009. It touches the north wall and is 0.30 m from o0001 in plan.
# The lamp's broad bounding box includes its arch, so the close placement is
# intentional: the table sits beside/under the arched portion of the lamp.
floor_side_table_B[0].position = [4.10, 5.75, 0.275]
floor_side_table_B[0].rotation = [0, 0, radians(0)]

# Arrange the remaining pieces around the open sides of the sectional.
floor_side_table_A[0].position = [2.15, 1.00, 0.275]
floor_side_table_A[0].rotation = [0, 0, radians(0)]

coffee_table[0].position = [5.65, 4.25, 0.225]
coffee_table[0].rotation = [0, 0, radians(0)]

# o0007 is directly in front of the sofa, while the second pouf occupies the
# lower part of the same seating area without blocking the TV or coffee table.
floor_pouf_A[0].position = [5.65, 2.75, 0.20]
floor_pouf_A[0].rotation = [0, 0, radians(180)]

floor_pouf_B[0].position = [5.65, 1.25, 0.20]
floor_pouf_B[0].rotation = [0, 0, radians(180)]


# Fixed reference points preserve the selected functional zones while still
# allowing the semantic constraints below to take priority.
tv_anchor = AssetInstance(position=[6.775, 3.00, 0.275])
bookshelf_anchor = AssetInstance(position=[0.20, 4.50, 1.15])
sofa_anchor = AssetInstance(position=[3.90, 3.00, 0.425])
lamp_A_anchor = AssetInstance(position=[4.10, 5.45, 1.05])
lamp_B_anchor = AssetInstance(position=[4.10, 0.55, 1.05])
side_table_A_anchor = AssetInstance(position=[2.15, 1.00, 0.275])
side_table_B_anchor = AssetInstance(position=[4.10, 5.75, 0.275])
coffee_anchor = AssetInstance(position=[5.65, 4.25, 0.225])
pouf_A_anchor = AssetInstance(position=[5.65, 2.75, 0.20])
pouf_B_anchor = AssetInstance(position=[5.65, 1.25, 0.20])


# High-priority layout criteria: o0009 remains at the north wall, o0001 stays
# within 0.30 m of it in floor-plan distance, and the sofa remains centered
# between the two lamps.
solver.against_wall(floor_side_table_B[0], walls[1])
solver.distance_constraint(
    floor_lamp_A[0], floor_side_table_B[0],
    min_distance=None, max_distance=0.30, weight=10
)
solver.distance_constraint(
    sectional_sofa[0], floor_lamp_A[0],
    min_distance=2.40, max_distance=2.65, weight=10
)
solver.distance_constraint(
    sectional_sofa[0], floor_lamp_B[0],
    min_distance=2.40, max_distance=2.65, weight=10
)

# The sofa's primary orientation criterion is to face o0007.
solver.point_towards(sectional_sofa[0], floor_pouf_A[0])


# Wall constraints and target zones for the large perimeter furniture.
solver.against_wall(tv_stand[0], walls[0])
solver.distance_constraint(
    tv_stand[0], tv_anchor, min_distance=0, max_distance=0.05, weight=10
)
solver.point_towards(tv_stand[0], sectional_sofa[0])

solver.against_wall(floor_bookshelf[0], walls[2])
solver.distance_constraint(
    floor_bookshelf[0], bookshelf_anchor,
    min_distance=0, max_distance=0.05, weight=10
)
solver.point_towards(floor_bookshelf[0], sectional_sofa[0])


# Position and orientation constraints for both lamps.
solver.distance_constraint(
    floor_lamp_A[0], lamp_A_anchor,
    min_distance=0, max_distance=0.05, weight=1
)
solver.point_towards(floor_lamp_A[0], floor_side_table_B[0])

solver.distance_constraint(
    floor_lamp_B[0], lamp_B_anchor,
    min_distance=0, max_distance=0.05, weight=10
)
solver.point_towards(floor_lamp_B[0], sectional_sofa[0])


# Anchor the sofa after its more important between-the-lamps constraints.
solver.distance_constraint(
    sectional_sofa[0], sofa_anchor,
    min_distance=0, max_distance=0.05, weight=1
)

# Side-table constraints. The round tables' rotations are visually neutral,
# but aligning them with the sofa gives every instance an orientation rule.
solver.distance_constraint(
    floor_side_table_A[0], side_table_A_anchor,
    min_distance=0, max_distance=0.05, weight=10
)
solver.align_with(floor_side_table_A[0], sectional_sofa[0])

solver.distance_constraint(
    floor_side_table_B[0], side_table_B_anchor,
    min_distance=0, max_distance=0.05, weight=10
)
solver.align_with(floor_side_table_B[0], sectional_sofa[0])


# Keep the coffee table in the open area in front and to the side of the
# sectional, with its long axis parallel to the sofa.
solver.distance_constraint(
    coffee_table[0], coffee_anchor,
    min_distance=0, max_distance=0.05, weight=10
)
solver.align_with(coffee_table[0], sectional_sofa[0])


# Preserve the two non-overlapping pouf positions and orient both toward the
# seating group.
solver.distance_constraint(
    floor_pouf_A[0], pouf_A_anchor,
    min_distance=0, max_distance=0.05, weight=10
)
solver.point_towards(floor_pouf_A[0], sectional_sofa[0])

solver.distance_constraint(
    floor_pouf_B[0], pouf_B_anchor,
    min_distance=0, max_distance=0.05, weight=10
)
solver.point_towards(floor_pouf_B[0], sectional_sofa[0])

solver.constraints = []
coffee_table[0].position = [5.650000095367432, 4.25, 0.22499999403953552]
coffee_table[0].rotation = [0, 0, 0.04278321063458886]
coffee_table[0].optimize = 2
sectional_sofa[0].position = [3.9000000953674316, 3.0, 0.42500001192092896]
sectional_sofa[0].rotation = [0, 0, 0.04084070568744688]
sectional_sofa[0].optimize = 2
floor_side_table_A[0].position = [2.1500000953674316, 1.0, 0.2750000059604645]
floor_side_table_A[0].rotation = [0, 0, 0.04278321063458886]
floor_side_table_A[0].optimize = 2
floor_pouf_A[0].position = [5.650000095367432, 2.75, 0.20000000298023224]
floor_pouf_A[0].rotation = [0, 0, -3.1290262823329655]
floor_pouf_A[0].optimize = 2
floor_side_table_B[0].position = [4.099999904632568, 5.678825378417969, 0.2750000059604645]
floor_side_table_B[0].rotation = [0, 0, -0.35408904440250855]
floor_side_table_B[0].optimize = 2
tv_stand[0].position = [6.776951789855957, 3.0, 0.2750000059604645]
tv_stand[0].rotation = [0, 0, 3.1398164966361124]
tv_stand[0].optimize = 2
floor_lamp_A[0].position = [4.099999904632568, 5.387104034423828, 1.0499999523162842]
floor_lamp_A[0].rotation = [0, 0, 0.443135001594273]
floor_lamp_A[0].optimize = 2
floor_bookshelf[0].position = [0.19791170954704285, 4.5, 1.149999976158142]
floor_bookshelf[0].rotation = [0, 0, -0.0017759881544234233]
floor_bookshelf[0].optimize = 2
floor_pouf_B[0].position = [5.650000095367432, 1.25, 0.20000000298023224]
floor_pouf_B[0].rotation = [0, 0, 3.1315827454187772]
floor_pouf_B[0].optimize = 2
floor_lamp_B[0].position = [4.099999904632568, 0.8464773297309875, 1.0499999523162842]
floor_lamp_B[0].rotation = [0, 0, 1.5833626980517244]
floor_lamp_B[0].optimize = 2

