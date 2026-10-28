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
    Wall(corner1=[1.87, 7.32, 0.00], corner2=[1.87, 7.98, 0.00]),
    Wall(corner1=[1.87, 7.98, 0.00], corner2=[0.00, 7.98, 0.00]),
    Wall(corner1=[0.00, 7.98, 0.00], corner2=[0.00, 6.69, 0.00]),
    Wall(corner1=[0.00, 6.69, 0.00], corner2=[5.52, 6.69, 0.00]),
    Wall(corner1=[5.52, 6.69, 0.00], corner2=[5.52, 0.00, 0.00]),
    Wall(corner1=[5.52, 0.00, 0.00], corner2=[9.40, 0.00, 0.00]),
    Wall(corner1=[9.40, 0.00, 0.00], corner2=[9.40, 7.98, 0.00]),
    Wall(corner1=[9.40, 7.98, 0.00], corner2=[2.11, 7.98, 0.00]),
    Wall(corner1=[2.11, 7.98, 0.00], corner2=[2.11, 7.32, 0.00]),
    Wall(corner1=[2.11, 7.32, 0.00], corner2=[1.87, 7.32, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
ornaments_A = Assets(description="ornaments", size=[0.18, 0.25, 0.35], placements=[AssetInstance() for _ in range(1)])
bookcase_A = Assets(description="bookcase", size=[0.35, 1.20, 1.90], placements=[AssetInstance() for _ in range(1)])
bookcase_B = Assets(description="bookcase", size=[0.35, 1.20, 1.90], placements=[AssetInstance() for _ in range(1)])
potted_bonsai = Assets(description="potted bonsai", size=[0.35, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
dining_table = Assets(description="dining table", size=[0.90, 1.80, 0.76], placements=[AssetInstance() for _ in range(1)])
dining_chair_A = Assets(description="dining chair", size=[0.55, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
dining_chair_B = Assets(description="dining chair", size=[0.55, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
dining_chair_C = Assets(description="dining chair", size=[0.55, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
dining_chair_D = Assets(description="dining chair", size=[0.55, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
sofa = Assets(description="sofa", size=[0.95, 2.30, 0.85], placements=[AssetInstance() for _ in range(1)])
air_conditioner = Assets(description="air conditioner", size=[0.25, 1.00, 0.32], placements=[AssetInstance() for _ in range(1)])
plants = Assets(description="plants", size=[0.65, 0.65, 1.40], placements=[AssetInstance() for _ in range(1)])
washing_machine = Assets(description="washing machine", size=[0.65, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
ornaments_B = Assets(description="ornaments", size=[0.20, 0.30, 0.40], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="coffee table", size=[0.60, 1.20, 0.45], placements=[AssetInstance() for _ in range(1)])
washing_cabinet = Assets(description="washing cabinet", size=[0.65, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])

ornaments_A[0].instance_id = 'ornaments_A_0'
bookcase_A[0].instance_id = 'bookcase_A_0'
bookcase_B[0].instance_id = 'bookcase_B_0'
potted_bonsai[0].instance_id = 'potted_bonsai_0'
dining_table[0].instance_id = 'dining_table_0'
dining_chair_A[0].instance_id = 'dining_chair_A_0'
dining_chair_B[0].instance_id = 'dining_chair_B_0'
dining_chair_C[0].instance_id = 'dining_chair_C_0'
dining_chair_D[0].instance_id = 'dining_chair_D_0'
sofa[0].instance_id = 'sofa_0'
air_conditioner[0].instance_id = 'air_conditioner_0'
plants[0].instance_id = 'plants_0'
washing_machine[0].instance_id = 'washing_machine_0'
ornaments_B[0].instance_id = 'ornaments_B_0'
coffee_table[0].instance_id = 'coffee_table_0'
washing_cabinet[0].instance_id = 'washing_cabinet_0'
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

ornaments_A[0].position = [6.361868634837832, 6.023234212434455, 0.175]
ornaments_A[0].rotation = [0, 0, 0]
bookcase_A[0].position = [7.036627063979477, 7.8241598192188055, 0.95]
bookcase_A[0].rotation = [0, 0, 0]
bookcase_B[0].position = [5.385378927441969, 7.145421366227506, 0.95]
bookcase_B[0].rotation = [0, 0, 0]
potted_bonsai[0].position = [8.324257860640868, 6.609753010940074, 0.275]
potted_bonsai[0].rotation = [0, 0, 0]
dining_table[0].position = [7.159284906423735, 1.9265141718383136, 0.38]
dining_table[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [6.363052039220945, 0.9258542633223734, 0.45]
dining_chair_A[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [5.56080018636599, 0.026026107084659245, 0.45]
dining_chair_B[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [5.535829840491993, 3.0483397023938856, 0.45]
dining_chair_C[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [5.684801260213056, 5.957444495341466, 0.45]
dining_chair_D[0].rotation = [0, 0, 0]
sofa[0].position = [8.565184019725471, 4.859755391231691, 0.425]
sofa[0].rotation = [0, 0, 0]
air_conditioner[0].position = [2.6591504704891964, 7.531845750643642, 0.16]
air_conditioner[0].rotation = [0, 0, 0]
plants[0].position = [6.711980240517836, 1.197304424218743, 0.7]
plants[0].rotation = [0, 0, 0]
washing_machine[0].position = [7.717322762532113, 7.02229370159228, 0.425]
washing_machine[0].rotation = [0, 0, 0]
ornaments_B[0].position = [8.590697996578744, 1.0754476795390657, 0.2]
ornaments_B[0].rotation = [0, 0, 0]
coffee_table[0].position = [2.442610994476895, 7.071976548820644, 0.225]
coffee_table[0].rotation = [0, 0, 0]
washing_cabinet[0].position = [5.954752834068802, 3.756428067562666, 0.45]
washing_cabinet[0].rotation = [0, 0, 0]
ornaments_A[0].position = [6.361868634837832, 6.023234212434455, 0.175]
ornaments_A[0].rotation = [0, 0, 0]
bookcase_A[0].position = [7.036627063979477, 7.8241598192188055, 0.95]
bookcase_A[0].rotation = [0, 0, 0]
bookcase_B[0].position = [5.385378927441969, 7.145421366227506, 0.95]
bookcase_B[0].rotation = [0, 0, 0]
potted_bonsai[0].position = [8.324257860640868, 6.609753010940074, 0.275]
potted_bonsai[0].rotation = [0, 0, 0]
dining_table[0].position = [7.159284906423735, 1.9265141718383136, 0.38]
dining_table[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [6.363052039220945, 0.9258542633223734, 0.45]
dining_chair_A[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [5.56080018636599, 0.026026107084659245, 0.45]
dining_chair_B[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [5.535829840491993, 3.0483397023938856, 0.45]
dining_chair_C[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [5.684801260213056, 5.957444495341466, 0.45]
dining_chair_D[0].rotation = [0, 0, 0]
sofa[0].position = [8.565184019725471, 4.859755391231691, 0.425]
sofa[0].rotation = [0, 0, 0]
air_conditioner[0].position = [2.6591504704891964, 7.531845750643642, 0.16]
air_conditioner[0].rotation = [0, 0, 0]
plants[0].position = [6.711980240517836, 1.197304424218743, 0.7]
plants[0].rotation = [0, 0, 0]
washing_machine[0].position = [7.717322762532113, 7.02229370159228, 0.425]
washing_machine[0].rotation = [0, 0, 0]
ornaments_B[0].position = [8.590697996578744, 1.0754476795390657, 0.2]
ornaments_B[0].rotation = [0, 0, 0]
coffee_table[0].position = [2.442610994476895, 7.071976548820644, 0.225]
coffee_table[0].rotation = [0, 0, 0]
washing_cabinet[0].position = [5.954752834068802, 3.756428067562666, 0.45]
washing_cabinet[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed references preserve the intended room zoning and provide orientation
# references without introducing additional scene assets.
dining_anchor = AssetInstance(position=[7.40, 6.55, 0.38])
living_anchor = AssetInstance(position=[7.45, 4.05, 0.225])
plant_anchor = AssetInstance(position=[6.35, 5.20, 0.70])
horizontal_reference = AssetInstance(
    position=[7.40, 6.55, 0.00],
    rotation=[0, 0, 0],
)

# Place the bookcases on unobstructed portions of the north wall. Their narrow
# sides are normal to the wall, and their fronts face into the room.
bookcase_A[0].position = [0.65, 7.805, 0.95]
bookcase_A[0].rotation = [0, 0, radians(-90)]

bookcase_B[0].position = [5.35, 7.805, 0.95]
bookcase_B[0].rotation = [0, 0, radians(-90)]

# The dining group occupies the upper-right part of the room. The table lies
# between chairs A (o0005) and C (o0007), while the other chairs use its sides.
dining_table[0].position = [7.40, 6.55, 0.38]
dining_table[0].rotation = [0, 0, radians(90)]

dining_chair_A[0].position = [6.05, 6.55, 0.45]
dining_chair_A[0].rotation = [0, 0, radians(-59)]

dining_chair_B[0].position = [7.40, 5.35, 0.45]
dining_chair_B[0].rotation = [0, 0, radians(90)]

dining_chair_C[0].position = [8.75, 6.55, 0.45]
dining_chair_C[0].rotation = [0, 0, radians(180)]

dining_chair_D[0].position = [7.40, 7.55, 0.45]
dining_chair_D[0].rotation = [0, 0, radians(-90)]

# The sofa is backed against the east wall and faces the coffee table. This
# leaves the two doors on the south wall unobstructed.
sofa[0].position = [8.925, 4.05, 0.425]
sofa[0].rotation = [0, 0, radians(180)]

coffee_table[0].position = [7.45, 4.05, 0.225]
coffee_table[0].rotation = [0, 0, 0]

# Keep the plant near the living/dining transition, away from all door paths.
plants[0].position = [6.35, 5.20, 0.70]
plants[0].rotation = [0, 0, radians(-49)]

# Laundry appliances use the west wall below the living area while avoiding
# the window centered at y=1.51.
washing_cabinet[0].position = [5.845, 2.85, 0.45]
washing_cabinet[0].rotation = [0, 0, 0]

washing_machine[0].position = [5.845, 4.30, 0.425]
washing_machine[0].rotation = [0, 0, 0]

# Mount the air conditioner high on the east wall, clear of furniture.
air_conditioner[0].position = [9.275, 1.50, 2.30]
air_conditioner[0].rotation = [0, 0, radians(180)]

# Small decorative objects are supported by furniture rather than the floor.
potted_bonsai[0].position = [5.845, 2.85, 1.175]
potted_bonsai[0].rotation = [0, 0, 0]

ornaments_A[0].position = [7.35, 3.72, 0.625]
ornaments_A[0].rotation = [0, 0, 0]

ornaments_B[0].position = [7.50, 4.28, 0.65]
ornaments_B[0].rotation = [0, 0, 0]


# Bookcase wall contact is the key semantic requirement. The room-side points
# also ensure that both fronts remain directed inward.
solver.against_wall(bookcase_A[0], walls[1])
solver.point_towards(
    bookcase_A[0],
    AssetInstance(position=[0.65, 7.00, 0.95]),
)

solver.against_wall(bookcase_B[0], walls[7])
solver.point_towards(
    bookcase_B[0],
    AssetInstance(position=[5.35, 7.00, 0.95]),
)

# Anchor the table before constraining the chairs, since it establishes the
# dining group's location and orientation.
solver.distance_constraint(
    dining_table[0], dining_anchor, 0.0, 0.0, weight=10
)
solver.align_with(dining_table[0], horizontal_reference, angle=90)

# Equal chair-to-table distances plus the full A-to-C separation keep the
# table between chairs A and C. Chair A's required orientation toward the
# coffee table is specified before any other possible orientation relation.
solver.distance_constraint(
    dining_chair_A[0], dining_table[0], 1.35, 1.35, weight=10
)
solver.point_towards(dining_chair_A[0], coffee_table[0])

solver.distance_constraint(
    dining_chair_C[0], dining_table[0], 1.35, 1.35, weight=10
)
solver.distance_constraint(
    dining_chair_C[0], dining_chair_A[0], 2.70, 2.70, weight=10
)
solver.point_towards(dining_chair_C[0], dining_table[0])

solver.distance_constraint(
    dining_chair_B[0], dining_table[0], 1.20, 1.20, weight=10
)
solver.point_towards(dining_chair_B[0], dining_table[0])

solver.distance_constraint(
    dining_chair_D[0], dining_table[0], 1.00, 1.00, weight=10
)
solver.point_towards(dining_chair_D[0], dining_table[0])

# Establish the living-area relationship: sofa against the wall, coffee table
# in front, and both oriented consistently.
solver.against_wall(sofa[0], walls[6])
solver.distance_constraint(
    sofa[0], coffee_table[0], 1.35, 1.50, weight=10
)
solver.point_towards(sofa[0], coffee_table[0])

solver.distance_constraint(
    coffee_table[0], living_anchor, 0.0, 0.0, weight=10
)
solver.align_with(coffee_table[0], sofa[0], angle=180)

# The plant is anchored in a clear floor area and turned toward the living
# arrangement.
solver.distance_constraint(
    plants[0], plant_anchor, 0.0, 0.0, weight=10
)
solver.point_towards(plants[0], coffee_table[0])

# Keep both laundry units flush with the west wall and front-facing into the
# room. Their separation prevents their bounding boxes from overlapping.
solver.against_wall(washing_cabinet[0], walls[4])
solver.distance_constraint(
    washing_cabinet[0], washing_machine[0], 1.40, 1.55, weight=5
)
solver.align_with(washing_cabinet[0], horizontal_reference)

solver.against_wall(washing_machine[0], walls[4])
solver.distance_constraint(
    washing_machine[0], washing_cabinet[0], 1.40, 1.55, weight=5
)
solver.align_with(washing_machine[0], washing_cabinet[0])

# Preserve the wall-mounted air conditioner's exact height and wall location,
# with its front directed into the room.
solver.against_wall(air_conditioner[0], walls[6])
solver.distance_constraint(
    air_conditioner[0],
    AssetInstance(position=[9.275, 1.50, 2.30]),
    0.0,
    0.0,
    weight=10,
)
solver.point_towards(
    air_conditioner[0],
    AssetInstance(position=[8.00, 1.50, 2.30]),
)

# Support and horizontal-location constraints keep each small object on its
# intended surface. Alignment supplies an orientation constraint for each.
solver.on_top_of(potted_bonsai[0], washing_cabinet[0])
solver.distance_constraint(
    potted_bonsai[0], washing_cabinet[0], 0.725, 0.725, weight=10
)
solver.align_with(potted_bonsai[0], washing_cabinet[0])

solver.on_top_of(ornaments_A[0], coffee_table[0])
solver.distance_constraint(
    ornaments_A[0], coffee_table[0], 0.45, 0.65, weight=10
)
solver.align_with(ornaments_A[0], coffee_table[0])

solver.on_top_of(ornaments_B[0], coffee_table[0])
solver.distance_constraint(
    ornaments_B[0], coffee_table[0], 0.42, 0.60, weight=10
)
solver.align_with(ornaments_B[0], coffee_table[0])

solver.constraints = []
washing_machine[0].position = [5.841070175170898, 4.300000190734863, 0.42500001192092896]
washing_machine[0].rotation = [0, 0, 0.00018253287148906554]
washing_machine[0].optimize = 2
potted_bonsai[0].position = [5.691349029541016, 2.8499999046325684, 1.1749999523162842]
potted_bonsai[0].rotation = [0, 0, -0.0015533484168132829]
potted_bonsai[0].optimize = 2
plants[0].position = [6.349999904632568, 5.199999809265137, 0.699999988079071]
plants[0].rotation = [0, 0, -0.8457865764946293]
plants[0].optimize = 2
ornaments_A[0].position = [7.168330669403076, 3.5402941703796387, 0.625]
ornaments_A[0].rotation = [0, 0, 0.0018660903053196705]
ornaments_A[0].optimize = 2
air_conditioner[0].position = [9.271084785461426, 1.5, 0.1599999964237213]
air_conditioner[0].rotation = [0, 0, 3.141531114273336]
air_conditioner[0].optimize = 2
washing_cabinet[0].position = [5.840714931488037, 2.8499999046325684, 0.44999998807907104]
washing_cabinet[0].rotation = [0, 0, 0.00012390371799981246]
washing_cabinet[0].optimize = 2
dining_chair_D[0].position = [7.400000095367432, 7.550000190734863, 0.44999998807907104]
dining_chair_D[0].rotation = [0, 0, -1.5613715493341729]
dining_chair_D[0].optimize = 2
dining_table[0].position = [7.400000095367432, 6.550000190734863, 0.3799999952316284]
dining_table[0].rotation = [0, 0, 1.6022122525607134]
dining_table[0].optimize = 2
ornaments_B[0].position = [7.753608703613281, 4.528088092803955, 0.6499999761581421]
ornaments_B[0].rotation = [0, 0, 0.0018660903053196705]
ornaments_B[0].optimize = 2
dining_chair_A[0].position = [6.048758029937744, 6.550000190734863, 0.44999998807907104]
dining_chair_A[0].rotation = [0, 0, -1.0171778773564293]
dining_chair_A[0].optimize = 2
bookcase_A[0].position = [0.6499999761581421, 7.804936408996582, 0.949999988079071]
bookcase_A[0].rotation = [0, 0, -1.5709781032043837]
bookcase_A[0].optimize = 2
sofa[0].position = [8.920982360839844, 4.050000190734863, 0.42500001192092896]
sofa[0].rotation = [0, 0, -3.141406450557634]
sofa[0].optimize = 2
dining_chair_C[0].position = [8.749805450439453, 6.550000190734863, 0.44999998807907104]
dining_chair_C[0].rotation = [0, 0, -3.1290262823329655]
dining_chair_C[0].optimize = 2
coffee_table[0].position = [7.449999809265137, 4.050000190734863, 0.22499999403953552]
coffee_table[0].rotation = [0, 0, 0.0004129687225067311]
coffee_table[0].optimize = 2
bookcase_B[0].position = [5.683343887329102, 7.229172706604004, 0.949999988079071]
bookcase_B[0].rotation = [0, 0, -0.24646540040064824]
bookcase_B[0].optimize = 2
dining_chair_B[0].position = [7.400000095367432, 5.349999904632568, 0.44999998807907104]
dining_chair_B[0].rotation = [0, 0, 1.5802211042556205]
dining_chair_B[0].optimize = 2

