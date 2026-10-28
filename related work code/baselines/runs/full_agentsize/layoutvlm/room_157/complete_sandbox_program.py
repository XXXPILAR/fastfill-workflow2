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
tv_stand = Assets(description="modern low-profile tv stand in walnut finish with multiple compartments", size=[0.45, 1.80, 0.55], placements=[AssetInstance() for _ in range(1)])
bookshelf_A = Assets(description="tall open wooden bookshelf with multiple shelves and back panel", size=[0.32, 0.90, 2.00], placements=[AssetInstance() for _ in range(1)])
plant_stand = Assets(description="multi-tier wooden plant stand with natural finish", size=[0.40, 0.80, 1.10], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="large rectangular wooden coffee table with glass top and storage underneath", size=[0.80, 1.40, 0.45], placements=[AssetInstance() for _ in range(1)])
floor_lamp_A = Assets(description="tall modern arc floor lamp with fabric shade and dimmable light", size=[0.40, 1.20, 2.10], placements=[AssetInstance() for _ in range(1)])
sideboard_cabinet = Assets(description="wide wooden sideboard cabinet with drawers and cupboard space", size=[0.45, 1.80, 0.85], placements=[AssetInstance() for _ in range(1)])
floor_lamp_B = Assets(description="tall modern arc floor lamp with fabric shade and dimmable light", size=[0.40, 1.20, 2.10], placements=[AssetInstance() for _ in range(1)])
bookshelf_B = Assets(description="tall open wooden bookshelf with multiple shelves and back panel", size=[0.32, 0.90, 2.00], placements=[AssetInstance() for _ in range(1)])
bookshelf_C = Assets(description="tall open wooden bookshelf with multiple shelves and back panel", size=[0.32, 0.90, 2.00], placements=[AssetInstance() for _ in range(1)])
sectional_sofa = Assets(description="modern l-shaped sectional sofa in light grey fabric with deep cushions", size=[2.20, 3.20, 0.90], placements=[AssetInstance() for _ in range(1)])
side_table_A = Assets(description="round wooden side table with drawer and modern legs", size=[0.50, 0.50, 0.58], placements=[AssetInstance() for _ in range(1)])
side_table_B = Assets(description="round wooden side table with drawer and modern legs", size=[0.50, 0.50, 0.58], placements=[AssetInstance() for _ in range(1)])

tv_stand[0].instance_id = 'tv_stand_0'
bookshelf_A[0].instance_id = 'bookshelf_A_0'
plant_stand[0].instance_id = 'plant_stand_0'
coffee_table[0].instance_id = 'coffee_table_0'
floor_lamp_A[0].instance_id = 'floor_lamp_A_0'
sideboard_cabinet[0].instance_id = 'sideboard_cabinet_0'
floor_lamp_B[0].instance_id = 'floor_lamp_B_0'
bookshelf_B[0].instance_id = 'bookshelf_B_0'
bookshelf_C[0].instance_id = 'bookshelf_C_0'
sectional_sofa[0].instance_id = 'sectional_sofa_0'
side_table_A[0].instance_id = 'side_table_A_0'
side_table_B[0].instance_id = 'side_table_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

tv_stand[0].position = [1.1710169691090322, 5.830530495495527, 0.275]
tv_stand[0].rotation = [0, 0, 0]
bookshelf_A[0].position = [0.7185143054455136, 1.6515863281484089, 1.0]
bookshelf_A[0].rotation = [0, 0, 0]
plant_stand[0].position = [0.6813439198900231, 2.2149044167984204, 0.55]
plant_stand[0].rotation = [0, 0, 0]
coffee_table[0].position = [4.763642586284178, 3.665909535535501, 0.225]
coffee_table[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [1.7809656375241123, 0.38093050283863783, 1.05]
floor_lamp_A[0].rotation = [0, 0, 0]
sideboard_cabinet[0].position = [0.7310467179702431, 4.255126833395703, 0.425]
sideboard_cabinet[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [0.7636552109693269, 6.77810892657114, 1.05]
floor_lamp_B[0].rotation = [0, 0, 0]
bookshelf_B[0].position = [2.9884006292913243, 6.787608006884944, 1.0]
bookshelf_B[0].rotation = [0, 0, 0]
bookshelf_C[0].position = [1.1507758969716306, 2.0299232586352907, 1.0]
bookshelf_C[0].rotation = [0, 0, 0]
sectional_sofa[0].position = [1.9408547602137176, 1.960936399262716, 0.45]
sectional_sofa[0].rotation = [0, 0, 0]
side_table_A[0].position = [0.34301121634274345, 0.4092059044763541, 0.29]
side_table_A[0].rotation = [0, 0, 0]
side_table_B[0].position = [2.4901896823219762, 0.2678093415910421, 0.29]
side_table_B[0].rotation = [0, 0, 0]
tv_stand[0].position = [1.1710169691090322, 5.830530495495527, 0.275]
tv_stand[0].rotation = [0, 0, 0]
bookshelf_A[0].position = [0.7185143054455136, 1.6515863281484089, 1.0]
bookshelf_A[0].rotation = [0, 0, 0]
plant_stand[0].position = [0.6813439198900231, 2.2149044167984204, 0.55]
plant_stand[0].rotation = [0, 0, 0]
coffee_table[0].position = [4.763642586284178, 3.665909535535501, 0.225]
coffee_table[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [1.7809656375241123, 0.38093050283863783, 1.05]
floor_lamp_A[0].rotation = [0, 0, 0]
sideboard_cabinet[0].position = [0.7310467179702431, 4.255126833395703, 0.425]
sideboard_cabinet[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [0.7636552109693269, 6.77810892657114, 1.05]
floor_lamp_B[0].rotation = [0, 0, 0]
bookshelf_B[0].position = [2.9884006292913243, 6.787608006884944, 1.0]
bookshelf_B[0].rotation = [0, 0, 0]
bookshelf_C[0].position = [1.1507758969716306, 2.0299232586352907, 1.0]
bookshelf_C[0].rotation = [0, 0, 0]
sectional_sofa[0].position = [1.9408547602137176, 1.960936399262716, 0.45]
sectional_sofa[0].rotation = [0, 0, 0]
side_table_A[0].position = [0.34301121634274345, 0.4092059044763541, 0.29]
side_table_A[0].rotation = [0, 0, 0]
side_table_B[0].position = [2.4901896823219762, 0.2678093415910421, 0.29]
side_table_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the three bookshelves as a centered row along the north wall.
# bookshelf_A corresponds to the specified middle bookshelf (o0007), with
# bookshelf_B and bookshelf_C on its two sides.
bookshelf_B[0].position = [1.40, 6.84, 1.00]
bookshelf_B[0].rotation = [0, 0, radians(-90)]

bookshelf_A[0].position = [3.00, 6.84, 1.00]
bookshelf_A[0].rotation = [0, 0, radians(-90)]

bookshelf_C[0].position = [4.60, 6.84, 1.00]
bookshelf_C[0].rotation = [0, 0, radians(-90)]

# Establish a living-room arrangement across the room's width. The sectional
# faces east toward the TV stand, while the coffee table remains between them.
sectional_sofa[0].position = [1.10, 3.20, 0.45]
sectional_sofa[0].rotation = [0, 0, radians(0)]

coffee_table[0].position = [3.50, 3.20, 0.225]
coffee_table[0].rotation = [0, 0, radians(0)]

tv_stand[0].position = [5.775, 3.50, 0.275]
tv_stand[0].rotation = [0, 0, radians(180)]

# Place one side table near each end of the sectional, leaving a small gap
# between their bounding boxes and keeping the central route unobstructed.
side_table_A[0].position = [2.50, 1.95, 0.29]
side_table_A[0].rotation = [0, 0, radians(0)]

side_table_B[0].position = [2.50, 4.45, 0.29]
side_table_B[0].rotation = [0, 0, radians(0)]

# Use the south wall for the sideboard and one lamp. Their footprints do not
# overlap, and both remain clear of the sectional.
floor_lamp_A[0].position = [2.80, 0.20, 1.05]
floor_lamp_A[0].rotation = [0, 0, radians(90)]

sideboard_cabinet[0].position = [4.75, 0.225, 0.425]
sideboard_cabinet[0].rotation = [0, 0, radians(90)]

# Fill the open portions of the east wall with the plant stand and second lamp,
# leaving the TV stand centered between them.
plant_stand[0].position = [5.80, 1.55, 0.55]
plant_stand[0].rotation = [0, 0, radians(180)]

floor_lamp_B[0].position = [5.80, 5.55, 1.05]
floor_lamp_B[0].rotation = [0, 0, radians(180)]


# Fixed reference points softly preserve the intended zones while allowing
# small adjustments if the solver needs to resolve physical feasibility.
sofa_anchor = AssetInstance(position=[1.10, 3.20, 0.45])
coffee_anchor = AssetInstance(position=[3.50, 3.20, 0.225])
side_table_A_anchor = AssetInstance(position=[2.50, 1.95, 0.29])
side_table_B_anchor = AssetInstance(position=[2.50, 4.45, 0.29])
plant_anchor = AssetInstance(position=[5.80, 1.55, 0.55])
lamp_A_anchor = AssetInstance(position=[2.80, 0.20, 1.05])
lamp_B_anchor = AssetInstance(position=[5.80, 5.55, 1.05])
sideboard_anchor = AssetInstance(position=[4.75, 0.225, 0.425])
bookshelf_B_anchor = AssetInstance(position=[1.40, 6.84, 1.00])


# --- Primary wall-placement constraints ---

solver.against_wall(sectional_sofa[0], walls[2])
solver.against_wall(tv_stand[0], walls[0])

solver.against_wall(bookshelf_B[0], walls[1])
solver.against_wall(bookshelf_A[0], walls[1])
solver.against_wall(bookshelf_C[0], walls[1])

solver.against_wall(floor_lamp_A[0], walls[3])
solver.against_wall(sideboard_cabinet[0], walls[3])

solver.against_wall(plant_stand[0], walls[0])
solver.against_wall(floor_lamp_B[0], walls[0])


# --- Important relational position constraints ---

# Pin the left bookshelf's general location, then preserve equal spacing.
# Since all three shelves are constrained to the same wall, equal 1.60 m
# distances place bookshelf_A directly between bookshelf_B and bookshelf_C.
solver.distance_constraint(
    bookshelf_B[0], bookshelf_B_anchor, 0.0, 0.10, weight=10
)
solver.distance_constraint(
    bookshelf_A[0], bookshelf_B[0], 1.60, 1.60, weight=10
)
solver.distance_constraint(
    bookshelf_C[0], bookshelf_A[0], 1.60, 1.60, weight=10
)
solver.distance_constraint(
    bookshelf_C[0], bookshelf_B[0], 3.20, 3.20, weight=10
)

# Preserve a practical sofa-to-TV viewing distance and keep the coffee table
# centered within the seating arrangement.
solver.distance_constraint(
    tv_stand[0], sectional_sofa[0], 4.60, 4.85, weight=10
)
solver.distance_constraint(
    coffee_table[0], sectional_sofa[0], 2.30, 2.50, weight=10
)
solver.distance_constraint(
    coffee_table[0], tv_stand[0], 2.20, 2.45, weight=10
)

# Keep each side table beside an end of the sectional and away from the coffee
# table's footprint.
solver.distance_constraint(
    side_table_A[0], side_table_A_anchor, 0.0, 0.10, weight=10
)
solver.distance_constraint(
    side_table_B[0], side_table_B_anchor, 0.0, 0.10, weight=10
)
solver.distance_constraint(
    side_table_A[0], coffee_table[0], 1.40, None, weight=10
)
solver.distance_constraint(
    side_table_B[0], coffee_table[0], 1.40, None, weight=10
)

# Maintain the intended wall zones and separation among the remaining pieces.
solver.distance_constraint(
    sectional_sofa[0], sofa_anchor, 0.0, 0.15, weight=1
)
solver.distance_constraint(
    coffee_table[0], coffee_anchor, 0.0, 0.15, weight=1
)
solver.distance_constraint(
    plant_stand[0], plant_anchor, 0.0, 0.15, weight=1
)
solver.distance_constraint(
    floor_lamp_A[0], lamp_A_anchor, 0.0, 0.15, weight=1
)
solver.distance_constraint(
    floor_lamp_B[0], lamp_B_anchor, 0.0, 0.15, weight=1
)
solver.distance_constraint(
    sideboard_cabinet[0], sideboard_anchor, 0.0, 0.15, weight=1
)
solver.distance_constraint(
    plant_stand[0], tv_stand[0], 1.70, None, weight=10
)
solver.distance_constraint(
    floor_lamp_B[0], tv_stand[0], 1.75, None, weight=10
)
solver.distance_constraint(
    floor_lamp_A[0], sideboard_cabinet[0], 1.75, None, weight=10
)


# --- Orientation constraints for every new asset ---

# The seating and media unit face one another.
solver.point_towards(sectional_sofa[0], tv_stand[0])
solver.point_towards(tv_stand[0], sectional_sofa[0])

# Keep the table surfaces and side tables aligned with the sectional.
solver.align_with(coffee_table[0], sectional_sofa[0])
solver.align_with(side_table_A[0], sectional_sofa[0])
solver.align_with(side_table_B[0], sectional_sofa[0])

# The south-wall sideboard faces into the room.
solver.align_with(sideboard_cabinet[0], sectional_sofa[0], angle=90)

# All bookshelves share an inward-facing orientation perpendicular to the
# north wall.
solver.align_with(bookshelf_A[0], sideboard_cabinet[0], angle=180)
solver.align_with(bookshelf_B[0], bookshelf_A[0])
solver.align_with(bookshelf_C[0], bookshelf_A[0])

# Aim the decorative plant stand and both arc lamps toward the seating group.
solver.point_towards(plant_stand[0], coffee_table[0])
solver.point_towards(floor_lamp_A[0], coffee_table[0])
solver.point_towards(floor_lamp_B[0], coffee_table[0])

solver.constraints = []
coffee_table[0].position = [3.5, 3.200000047683716, 0.22499999403953552]
coffee_table[0].rotation = [0, 0, 2.9458086969353904e-08]
coffee_table[0].optimize = 2
bookshelf_B[0].position = [1.399999976158142, 6.840000152587891, 1.0]
bookshelf_B[0].rotation = [0, 0, -1.5707962799803714]
bookshelf_B[0].optimize = 2
sideboard_cabinet[0].position = [4.75, 0.22499999403953552, 0.42500001192092896]
sideboard_cabinet[0].rotation = [0, 0, 1.570796364684587]
sideboard_cabinet[0].optimize = 2
bookshelf_C[0].position = [4.601669788360596, 6.840234279632568, 1.0]
bookshelf_C[0].rotation = [0, 0, -1.5707962801274538]
bookshelf_C[0].optimize = 2
side_table_B[0].position = [2.5, 4.449999809265137, 0.28999999165534973]
side_table_B[0].rotation = [0, 0, 2.5726270688653302e-08]
side_table_B[0].optimize = 2
sectional_sofa[0].position = [1.100000023841858, 3.200000047683716, 0.44999998807907104]
sectional_sofa[0].rotation = [0, 0, 2.0273290920942583e-08]
sectional_sofa[0].optimize = 2
side_table_A[0].position = [2.5, 1.9500000476837158, 0.28999999165534973]
side_table_A[0].rotation = [0, 0, 2.5726270688653302e-08]
side_table_A[0].optimize = 2
bookshelf_A[0].position = [2.9996957778930664, 6.839852809906006, 1.0]
bookshelf_A[0].rotation = [0, 0, -1.5707962802601823]
bookshelf_A[0].optimize = 2
tv_stand[0].position = [5.775000095367432, 3.5, 0.2750000059604645]
tv_stand[0].rotation = [0, 0, -3.141592606067721]
tv_stand[0].optimize = 2
floor_lamp_A[0].position = [2.799999952316284, 0.20000000298023224, 1.0499999523162842]
floor_lamp_A[0].rotation = [0, 0, 1.5707963655280441]
floor_lamp_A[0].optimize = 2
plant_stand[0].position = [5.800000190734863, 1.5499999523162842, 0.550000011920929]
plant_stand[0].rotation = [0, 0, -3.141592611442629]
plant_stand[0].optimize = 2
floor_lamp_B[0].position = [5.800000190734863, 5.550000190734863, 1.0499999523162842]
floor_lamp_B[0].rotation = [0, 0, -3.1415926122756686]
floor_lamp_B[0].optimize = 2

