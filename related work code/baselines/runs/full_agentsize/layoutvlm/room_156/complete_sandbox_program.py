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
    Wall(corner1=[6.00, 0.00, 0.00], corner2=[6.00, 7.00, 0.00]),
    Wall(corner1=[6.00, 7.00, 0.00], corner2=[0.00, 7.00, 0.00]),
    Wall(corner1=[0.00, 7.00, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
armchair_A = Assets(description="modern single armchair in light grey upholstery with wooden legs", size=[0.90, 0.85, 0.90], placements=[AssetInstance() for _ in range(1)])
side_table_A = Assets(description="round metal-framed side table with dark wooden top", size=[0.50, 0.50, 0.58], placements=[AssetInstance() for _ in range(1)])
armchair_B = Assets(description="modern single armchair in light grey upholstery with wooden legs", size=[0.90, 0.85, 0.90], placements=[AssetInstance() for _ in range(1)])
sectional_sofa = Assets(description="large l-shaped sectional sofa in dark blue fabric with deep seating", size=[2.40, 3.20, 0.88], placements=[AssetInstance() for _ in range(1)])
tv_stand = Assets(description="large low modern tv stand in dark wood finish with ample storage", size=[0.48, 2.20, 0.58], placements=[AssetInstance() for _ in range(1)])
console_table = Assets(description="narrow wooden console table with metal legs", size=[0.38, 1.50, 0.80], placements=[AssetInstance() for _ in range(1)])
plant_stand_A = Assets(description="wood and metal plant stand holding multiple pots", size=[0.40, 0.90, 1.20], placements=[AssetInstance() for _ in range(1)])
floor_lamp_A = Assets(description="tall modern floor lamp with adjustable arm and warm light", size=[0.90, 0.65, 1.80], placements=[AssetInstance() for _ in range(1)])
armchair_C = Assets(description="modern single armchair in light grey upholstery with wooden legs", size=[0.90, 0.85, 0.90], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="large rectangular wooden coffee table with lower shelf and glass top", size=[0.80, 1.40, 0.45], placements=[AssetInstance() for _ in range(1)])
side_table_B = Assets(description="round metal-framed side table with dark wooden top", size=[0.50, 0.50, 0.58], placements=[AssetInstance() for _ in range(1)])
plant_stand_B = Assets(description="wood and metal plant stand holding multiple pots", size=[0.40, 0.90, 1.20], placements=[AssetInstance() for _ in range(1)])
floor_lamp_B = Assets(description="tall modern floor lamp with adjustable arm and warm light", size=[0.90, 0.65, 1.80], placements=[AssetInstance() for _ in range(1)])
bookshelf_A = Assets(description="extra tall open bookshelf with multiple shelves in light wood finish", size=[0.35, 1.10, 2.30], placements=[AssetInstance() for _ in range(1)])
side_table_C = Assets(description="round metal-framed side table with dark wooden top", size=[0.50, 0.50, 0.58], placements=[AssetInstance() for _ in range(1)])
bookshelf_B = Assets(description="extra tall open bookshelf with multiple shelves in light wood finish", size=[0.35, 1.10, 2.30], placements=[AssetInstance() for _ in range(1)])

armchair_A[0].instance_id = 'armchair_A_0'
side_table_A[0].instance_id = 'side_table_A_0'
armchair_B[0].instance_id = 'armchair_B_0'
sectional_sofa[0].instance_id = 'sectional_sofa_0'
tv_stand[0].instance_id = 'tv_stand_0'
console_table[0].instance_id = 'console_table_0'
plant_stand_A[0].instance_id = 'plant_stand_A_0'
floor_lamp_A[0].instance_id = 'floor_lamp_A_0'
armchair_C[0].instance_id = 'armchair_C_0'
coffee_table[0].instance_id = 'coffee_table_0'
side_table_B[0].instance_id = 'side_table_B_0'
plant_stand_B[0].instance_id = 'plant_stand_B_0'
floor_lamp_B[0].instance_id = 'floor_lamp_B_0'
bookshelf_A[0].instance_id = 'bookshelf_A_0'
side_table_C[0].instance_id = 'side_table_C_0'
bookshelf_B[0].instance_id = 'bookshelf_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

armchair_A[0].position = [0.6465466461068452, 5.488623883147499, 0.45]
armchair_A[0].rotation = [0, 0, 0]
side_table_A[0].position = [0.1604862741708537, 5.481144295643314, 0.29]
side_table_A[0].rotation = [0, 0, 0]
armchair_B[0].position = [1.7220103889348273, 5.480384010238289, 0.45]
armchair_B[0].rotation = [0, 0, 0]
sectional_sofa[0].position = [3.489750078711638, 5.743600475844492, 0.44]
sectional_sofa[0].rotation = [0, 0, 0]
tv_stand[0].position = [0.07323401833430343, 2.5818338780958174, 0.29]
tv_stand[0].rotation = [0, 0, 0]
console_table[0].position = [4.001319683425885, 4.654832302065093, 0.4]
console_table[0].rotation = [0, 0, 0]
plant_stand_A[0].position = [5.894270654987749, 3.3669548172755994, 0.6]
plant_stand_A[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [1.0065930476785578, 6.936067639878679, 0.9]
floor_lamp_A[0].rotation = [0, 0, 0]
armchair_C[0].position = [5.543905208557653, 6.215297090512257, 0.45]
armchair_C[0].rotation = [0, 0, 0]
coffee_table[0].position = [3.8904723739867375, 3.04659958460252, 0.225]
coffee_table[0].rotation = [0, 0, 0]
side_table_B[0].position = [4.919355468736699, 1.764151681740484, 0.29]
side_table_B[0].rotation = [0, 0, 0]
plant_stand_B[0].position = [3.849421471390761, 1.2793210322353568, 0.6]
plant_stand_B[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [1.3049432821302693, 4.798429047754341, 0.9]
floor_lamp_B[0].rotation = [0, 0, 0]
bookshelf_A[0].position = [1.7233240667102068, 4.1538537380161795, 1.15]
bookshelf_A[0].rotation = [0, 0, 0]
side_table_C[0].position = [5.655046555525313, 4.025187103971814, 0.29]
side_table_C[0].rotation = [0, 0, 0]
bookshelf_B[0].position = [3.5701239438525, 4.858963865521198, 1.15]
bookshelf_B[0].rotation = [0, 0, 0]
armchair_A[0].position = [0.6465466461068452, 5.488623883147499, 0.45]
armchair_A[0].rotation = [0, 0, 0]
side_table_A[0].position = [0.1604862741708537, 5.481144295643314, 0.29]
side_table_A[0].rotation = [0, 0, 0]
armchair_B[0].position = [1.7220103889348273, 5.480384010238289, 0.45]
armchair_B[0].rotation = [0, 0, 0]
sectional_sofa[0].position = [3.489750078711638, 5.743600475844492, 0.44]
sectional_sofa[0].rotation = [0, 0, 0]
tv_stand[0].position = [0.07323401833430343, 2.5818338780958174, 0.29]
tv_stand[0].rotation = [0, 0, 0]
console_table[0].position = [4.001319683425885, 4.654832302065093, 0.4]
console_table[0].rotation = [0, 0, 0]
plant_stand_A[0].position = [5.894270654987749, 3.3669548172755994, 0.6]
plant_stand_A[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [1.0065930476785578, 6.936067639878679, 0.9]
floor_lamp_A[0].rotation = [0, 0, 0]
armchair_C[0].position = [5.543905208557653, 6.215297090512257, 0.45]
armchair_C[0].rotation = [0, 0, 0]
coffee_table[0].position = [3.8904723739867375, 3.04659958460252, 0.225]
coffee_table[0].rotation = [0, 0, 0]
side_table_B[0].position = [4.919355468736699, 1.764151681740484, 0.29]
side_table_B[0].rotation = [0, 0, 0]
plant_stand_B[0].position = [3.849421471390761, 1.2793210322353568, 0.6]
plant_stand_B[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [1.3049432821302693, 4.798429047754341, 0.9]
floor_lamp_B[0].rotation = [0, 0, 0]
bookshelf_A[0].position = [1.7233240667102068, 4.1538537380161795, 1.15]
bookshelf_A[0].rotation = [0, 0, 0]
side_table_C[0].position = [5.655046555525313, 4.025187103971814, 0.29]
side_table_C[0].rotation = [0, 0, 0]
bookshelf_B[0].position = [3.5701239438525, 4.858963865521198, 1.15]
bookshelf_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the main seating group around a central coffee table. The sectional
# occupies the left side and faces the TV stand on the right side.
sectional_sofa[0].position = [1.25, 3.55, 0.44]
sectional_sofa[0].rotation = [0, 0, radians(0)]

tv_stand[0].position = [5.76, 3.55, 0.29]
tv_stand[0].rotation = [0, 0, radians(180)]

coffee_table[0].position = [3.20, 3.55, 0.225]
coffee_table[0].rotation = [0, 0, radians(0)]

# Place the three armchairs in an ordered row along the upper side of the room.
# This makes armchair_A (o0000) spatially between armchair_C (o0008) and
# armchair_B (o0002), with clearance between all three chairs.
armchair_C[0].position = [1.15, 6.30, 0.45]
armchair_C[0].rotation = [0, 0, radians(0)]

armchair_A[0].position = [2.25, 6.30, 0.45]
armchair_A[0].rotation = [0, 0, radians(-90)]

armchair_B[0].position = [3.35, 6.30, 0.45]
armchair_B[0].rotation = [0, 0, radians(-90)]

# Distribute side tables near the seating while keeping the circulation space
# between the armchairs and the main seating group open.
side_table_A[0].position = [2.75, 5.45, 0.29]
side_table_A[0].rotation = [0, 0, radians(0)]

side_table_B[0].position = [3.90, 5.35, 0.29]
side_table_B[0].rotation = [0, 0, radians(0)]

side_table_C[0].position = [5.45, 1.35, 0.29]
side_table_C[0].rotation = [0, 0, radians(0)]

# The console is set against the bottom wall, with its shallow dimension
# perpendicular to that wall.
console_table[0].position = [1.35, 0.19, 0.40]
console_table[0].rotation = [0, 0, radians(90)]

# Place the plant stands along the bottom wall, separated from the console and
# from each other.
plant_stand_A[0].position = [2.60, 0.20, 0.60]
plant_stand_A[0].rotation = [0, 0, radians(90)]

plant_stand_B[0].position = [4.60, 0.20, 0.60]
plant_stand_B[0].rotation = [0, 0, radians(90)]

# Lamps are placed beside the upper armchair group and in the open lower area.
floor_lamp_A[0].position = [4.75, 5.20, 0.90]
floor_lamp_A[0].rotation = [0, 0, radians(150)]

floor_lamp_B[0].position = [3.65, 1.25, 0.90]
floor_lamp_B[0].rotation = [0, 0, radians(90)]

# The bookshelves use opposite walls and face inward. bookshelf_B is placed
# directly to the right of armchair_C so that armchair_C can face it.
bookshelf_A[0].position = [0.175, 0.75, 1.15]
bookshelf_A[0].rotation = [0, 0, radians(0)]

bookshelf_B[0].position = [5.825, 6.30, 1.15]
bookshelf_B[0].rotation = [0, 0, radians(180)]


# Strong position anchors preserve the planned non-overlapping layout.
solver.distance_constraint(
    sectional_sofa[0],
    AssetInstance(position=[1.25, 3.55, 0.44]),
    0, 0, weight=10
)
solver.distance_constraint(
    tv_stand[0],
    AssetInstance(position=[5.76, 3.55, 0.29]),
    0, 0, weight=10
)
solver.distance_constraint(
    coffee_table[0],
    AssetInstance(position=[3.20, 3.55, 0.225]),
    0, 0, weight=10
)

solver.distance_constraint(
    armchair_C[0],
    AssetInstance(position=[1.15, 6.30, 0.45]),
    0, 0, weight=10
)
solver.distance_constraint(
    armchair_A[0],
    AssetInstance(position=[2.25, 6.30, 0.45]),
    0, 0, weight=10
)
solver.distance_constraint(
    armchair_B[0],
    AssetInstance(position=[3.35, 6.30, 0.45]),
    0, 0, weight=10
)

solver.distance_constraint(
    side_table_A[0],
    AssetInstance(position=[2.75, 5.45, 0.29]),
    0, 0, weight=10
)
solver.distance_constraint(
    side_table_B[0],
    AssetInstance(position=[3.90, 5.35, 0.29]),
    0, 0, weight=10
)
solver.distance_constraint(
    side_table_C[0],
    AssetInstance(position=[5.45, 1.35, 0.29]),
    0, 0, weight=10
)

# Wall contact is the primary positional requirement for the console and both
# bookshelves; their anchors then select the intended locations on those walls.
solver.against_wall(console_table[0], walls[3])
solver.distance_constraint(
    console_table[0],
    AssetInstance(position=[1.35, 0.19, 0.40]),
    0, 0, weight=10
)

solver.against_wall(bookshelf_A[0], walls[2])
solver.distance_constraint(
    bookshelf_A[0],
    AssetInstance(position=[0.175, 0.75, 1.15]),
    0, 0, weight=10
)

solver.against_wall(bookshelf_B[0], walls[0])
solver.distance_constraint(
    bookshelf_B[0],
    AssetInstance(position=[5.825, 6.30, 1.15]),
    0, 0, weight=10
)

solver.distance_constraint(
    plant_stand_A[0],
    AssetInstance(position=[2.60, 0.20, 0.60]),
    0, 0, weight=10
)
solver.distance_constraint(
    plant_stand_B[0],
    AssetInstance(position=[4.60, 0.20, 0.60]),
    0, 0, weight=10
)
solver.distance_constraint(
    floor_lamp_A[0],
    AssetInstance(position=[4.75, 5.20, 0.90]),
    0, 0, weight=10
)
solver.distance_constraint(
    floor_lamp_B[0],
    AssetInstance(position=[3.65, 1.25, 0.90]),
    0, 0, weight=10
)

# Preserve the required "between" relationship: armchair_A remains equally
# spaced from armchair_C and armchair_B.
solver.distance_constraint(
    armchair_A[0], armchair_C[0], 1.10, 1.10, weight=10
)
solver.distance_constraint(
    armchair_A[0], armchair_B[0], 1.10, 1.10, weight=10
)

# Orient the principal furniture toward its functional counterpart.
solver.point_towards(sectional_sofa[0], tv_stand[0])
solver.point_towards(tv_stand[0], sectional_sofa[0])
solver.align_with(coffee_table[0], sectional_sofa[0])

solver.point_towards(armchair_A[0], coffee_table[0])
solver.point_towards(armchair_B[0], coffee_table[0])

# Required orientation: armchair_C (o0008) faces bookshelf_B (o0015).
solver.point_towards(armchair_C[0], bookshelf_B[0])

# Side tables share the coffee table's orientation, giving every table an
# orientation constraint despite their nearly rotationally symmetric shape.
solver.align_with(side_table_A[0], coffee_table[0])
solver.align_with(side_table_B[0], coffee_table[0])
solver.align_with(side_table_C[0], coffee_table[0])

# Keep the wall furniture oriented into the room.
solver.align_with(console_table[0], bookshelf_A[0], angle=90)
solver.align_with(bookshelf_A[0], sectional_sofa[0])
solver.align_with(bookshelf_B[0], sectional_sofa[0], angle=180)

# Plants and lamps point toward the area they visually serve.
solver.point_towards(plant_stand_A[0], coffee_table[0])
solver.point_towards(plant_stand_B[0], coffee_table[0])
solver.point_towards(floor_lamp_A[0], armchair_B[0])
solver.point_towards(floor_lamp_B[0], coffee_table[0])

solver.constraints = []
armchair_A[0].position = [2.25, 6.300000190734863, 0.44999998807907104]
armchair_A[0].rotation = [0, 0, -1.4013577374685644]
armchair_A[0].optimize = 2
armchair_B[0].position = [3.3499999046325684, 6.300000190734863, 0.44999998807907104]
armchair_B[0].rotation = [0, 0, -1.5550883628776802]
armchair_B[0].optimize = 2
floor_lamp_A[0].position = [4.75, 5.199999809265137, 0.8999999761581421]
floor_lamp_A[0].rotation = [0, 0, 2.6274186791011758]
floor_lamp_A[0].optimize = 2
coffee_table[0].position = [3.200000047683716, 3.549999952316284, 0.22499999403953552]
coffee_table[0].rotation = [0, 0, 0.02199113863787278]
coffee_table[0].optimize = 2
bookshelf_B[0].position = [5.825000286102295, 6.300000190734863, 1.149999976158142]
bookshelf_B[0].rotation = [0, 0, -3.141592616926917]
bookshelf_B[0].optimize = 2
side_table_B[0].position = [3.9000000953674316, 5.349999904632568, 0.28999999165534973]
side_table_B[0].rotation = [0, 0, 0.021991162497193264]
side_table_B[0].optimize = 2
plant_stand_B[0].position = [4.599999904632568, 0.30581504106521606, 0.6000000238418579]
plant_stand_B[0].rotation = [0, 0, 1.8226106426076234]
plant_stand_B[0].optimize = 2
side_table_A[0].position = [2.75, 5.449999809265137, 0.28999999165534973]
side_table_A[0].rotation = [0, 0, 0.021991162497193264]
side_table_A[0].optimize = 2
tv_stand[0].position = [5.746196269989014, 3.549999952316284, 0.28999999165534973]
tv_stand[0].rotation = [0, 0, -3.1290262823329655]
tv_stand[0].optimize = 2
bookshelf_A[0].position = [0.17500004172325134, 0.75, 1.149999976158142]
bookshelf_A[0].rotation = [0, 0, 6.337007710469276e-08]
bookshelf_A[0].optimize = 2
plant_stand_A[0].position = [2.5999999046325684, 0.22143836319446564, 0.6000000238418579]
plant_stand_A[0].rotation = [0, 0, 1.5226212945494608]
plant_stand_A[0].optimize = 2
console_table[0].position = [1.350000023841858, 0.1900000125169754, 0.4000000059604645]
console_table[0].rotation = [0, 0, 1.5707963396349909]
console_table[0].optimize = 2
side_table_C[0].position = [5.449999809265137, 1.350000023841858, 0.28999999165534973]
side_table_C[0].rotation = [0, 0, 0.021991162497193264]
side_table_C[0].optimize = 2
sectional_sofa[0].position = [1.25, 3.549999952316284, 0.4399999976158142]
sectional_sofa[0].rotation = [0, 0, 0.021991148286022624]
sectional_sofa[0].optimize = 2
armchair_C[0].position = [1.149999976158142, 6.300000190734863, 0.44999998807907104]
armchair_C[0].rotation = [0, 0, 0.01256637125682779]
armchair_C[0].optimize = 2
floor_lamp_B[0].position = [3.6500000953674316, 1.25, 0.8999999761581421]
floor_lamp_B[0].rotation = [0, 0, 1.6003690829995407]
floor_lamp_B[0].optimize = 2

