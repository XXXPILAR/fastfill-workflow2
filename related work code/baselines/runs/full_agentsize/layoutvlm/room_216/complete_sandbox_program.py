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
    Wall(corner1=[4.85, 9.82, 0.00], corner2=[1.29, 9.82, 0.00]),
    Wall(corner1=[1.29, 9.82, 0.00], corner2=[1.29, 4.81, 0.00]),
    Wall(corner1=[1.29, 4.81, 0.00], corner2=[0.00, 4.81, 0.00]),
    Wall(corner1=[0.00, 4.81, 0.00], corner2=[0.00, 3.29, 0.00]),
    Wall(corner1=[0.00, 3.29, 0.00], corner2=[1.31, 3.29, 0.00]),
    Wall(corner1=[1.31, 3.29, 0.00], corner2=[1.31, 0.00, 0.00]),
    Wall(corner1=[1.31, 0.00, 0.00], corner2=[4.24, 0.00, 0.00]),
    Wall(corner1=[4.24, 0.00, 0.00], corner2=[4.24, 3.97, 0.00]),
    Wall(corner1=[4.24, 3.97, 0.00], corner2=[4.88, 3.97, 0.00]),
    Wall(corner1=[4.88, 3.97, 0.00], corner2=[4.88, 5.22, 0.00]),
    Wall(corner1=[4.88, 5.22, 0.00], corner2=[4.86, 5.22, 0.00]),
    Wall(corner1=[4.86, 5.22, 0.00], corner2=[4.85, 9.82, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
coffee_table_A = Assets(description="coffee table", size=[0.60, 1.20, 0.42], placements=[AssetInstance() for _ in range(1)])
dining_chair_A = Assets(description="dining chair", size=[0.52, 0.48, 0.86], placements=[AssetInstance() for _ in range(1)])
dining_chair_B = Assets(description="dining chair", size=[0.52, 0.48, 0.86], placements=[AssetInstance() for _ in range(1)])
dining_table = Assets(description="dining table", size=[0.90, 1.80, 0.76], placements=[AssetInstance() for _ in range(1)])
dining_chair_C = Assets(description="dining chair", size=[0.52, 0.48, 0.86], placements=[AssetInstance() for _ in range(1)])
sofa_A = Assets(description="sofa", size=[0.90, 2.20, 0.85], placements=[AssetInstance() for _ in range(1)])
dining_chair_D = Assets(description="dining chair", size=[0.52, 0.48, 0.86], placements=[AssetInstance() for _ in range(1)])
dining_chair_E = Assets(description="dining chair", size=[0.52, 0.48, 0.86], placements=[AssetInstance() for _ in range(1)])
side_table = Assets(description="side table", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[3.40, 2.40, 0.02], placements=[AssetInstance() for _ in range(1)])
floor_standing_lamp = Assets(description="floor standing lamp", size=[0.45, 0.45, 1.65], placements=[AssetInstance() for _ in range(1)])
sofa_B = Assets(description="sofa", size=[0.90, 1.80, 0.85], placements=[AssetInstance() for _ in range(1)])
coffee_table_B = Assets(description="coffee table", size=[0.90, 0.90, 0.40], placements=[AssetInstance() for _ in range(1)])

coffee_table_A[0].instance_id = 'coffee_table_A_0'
dining_chair_A[0].instance_id = 'dining_chair_A_0'
dining_chair_B[0].instance_id = 'dining_chair_B_0'
dining_table[0].instance_id = 'dining_table_0'
dining_chair_C[0].instance_id = 'dining_chair_C_0'
sofa_A[0].instance_id = 'sofa_A_0'
dining_chair_D[0].instance_id = 'dining_chair_D_0'
dining_chair_E[0].instance_id = 'dining_chair_E_0'
side_table[0].instance_id = 'side_table_0'
carpet[0].instance_id = 'carpet_0'
floor_standing_lamp[0].instance_id = 'floor_standing_lamp_0'
sofa_B[0].instance_id = 'sofa_B_0'
coffee_table_B[0].instance_id = 'coffee_table_B_0'
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

coffee_table_A[0].position = [3.244195576809152, 3.676735365254644, 0.21]
coffee_table_A[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [1.5913362322350575, 8.568053715667348, 0.43]
dining_chair_A[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [2.7550393296043896, 6.175933914724015, 0.43]
dining_chair_B[0].rotation = [0, 0, 0]
dining_table[0].position = [4.079140589414257, 1.2141832551801657, 0.38]
dining_table[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [1.6070021856704018, 0.6021422337857851, 0.43]
dining_chair_C[0].rotation = [0, 0, 0]
sofa_A[0].position = [3.817437263338255, 9.13764992992521, 0.425]
sofa_A[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [1.7893183402636839, 5.691319841296424, 0.43]
dining_chair_D[0].rotation = [0, 0, 0]
dining_chair_E[0].position = [2.2417356420287984, 8.386166075062853, 0.43]
dining_chair_E[0].rotation = [0, 0, 0]
side_table[0].position = [3.0916505330805295, 4.128020667266304, 0.275]
side_table[0].rotation = [0, 0, 0]
carpet[0].position = [3.445342011102437, 5.02681446443653, 0.01]
carpet[0].rotation = [0, 0, 0]
floor_standing_lamp[0].position = [2.5148480280404826, 4.67254486460837, 0.825]
floor_standing_lamp[0].rotation = [0, 0, 0]
sofa_B[0].position = [2.9746108257191537, 8.04820808628975, 0.425]
sofa_B[0].rotation = [0, 0, 0]
coffee_table_B[0].position = [2.9396200137236885, 0.12166909340771012, 0.2]
coffee_table_B[0].rotation = [0, 0, 0]
coffee_table_A[0].position = [3.244195576809152, 3.676735365254644, 0.21]
coffee_table_A[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [1.5913362322350575, 8.568053715667348, 0.43]
dining_chair_A[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [2.7550393296043896, 6.175933914724015, 0.43]
dining_chair_B[0].rotation = [0, 0, 0]
dining_table[0].position = [4.079140589414257, 1.2141832551801657, 0.38]
dining_table[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [1.6070021856704018, 0.6021422337857851, 0.43]
dining_chair_C[0].rotation = [0, 0, 0]
sofa_A[0].position = [3.817437263338255, 9.13764992992521, 0.425]
sofa_A[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [1.7893183402636839, 5.691319841296424, 0.43]
dining_chair_D[0].rotation = [0, 0, 0]
dining_chair_E[0].position = [2.2417356420287984, 8.386166075062853, 0.43]
dining_chair_E[0].rotation = [0, 0, 0]
side_table[0].position = [3.0916505330805295, 4.128020667266304, 0.275]
side_table[0].rotation = [0, 0, 0]
carpet[0].position = [3.445342011102437, 5.02681446443653, 0.01]
carpet[0].rotation = [0, 0, 0]
floor_standing_lamp[0].position = [2.5148480280404826, 4.67254486460837, 0.825]
floor_standing_lamp[0].rotation = [0, 0, 0]
sofa_B[0].position = [2.9746108257191537, 8.04820808628975, 0.425]
sofa_B[0].rotation = [0, 0, 0]
coffee_table_B[0].position = [2.9396200137236885, 0.12166909340771012, 0.2]
coffee_table_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Divide the room into two functional zones:
# - Dining area near the window at the north end.
# - Living area in the wider middle section.
# The lower part and the west-side recesses remain open for all four doorways.

# Dining group near the north window.
dining_table[0].position = [3.05, 8.65, 0.38]
dining_table[0].rotation = [0, 0, radians(90)]

dining_chair_A[0].position = [2.55, 9.48, 0.43]
dining_chair_A[0].rotation = [0, 0, radians(-90)]

dining_chair_B[0].position = [4.40, 9.00, 0.43]
dining_chair_B[0].rotation = [0, 0, radians(195)]

dining_chair_C[0].position = [3.25, 7.75, 0.43]
dining_chair_C[0].rotation = [0, 0, radians(90)]

# dining_chair_D and dining_chair_B lie on opposite sides of the table,
# satisfying the requirement that the table be between o0006 and o0004.
dining_chair_D[0].position = [1.70, 8.30, 0.43]
dining_chair_D[0].rotation = [0, 0, radians(0)]

# dining_chair_E is directly opposite dining_chair_D so they face each other.
dining_chair_E[0].position = [4.40, 8.30, 0.43]
dining_chair_E[0].rotation = [0, 0, radians(180)]

# Living group in the middle of the room. The carpet may extend beneath the
# furniture, while the furniture footprints themselves remain separated.
carpet[0].position = [3.00, 6.05, 0.01]
carpet[0].rotation = [0, 0, radians(90)]

# sofa_A is backed against the long west wall and faces into the room.
sofa_A[0].position = [1.74, 6.25, 0.425]
sofa_A[0].rotation = [0, 0, radians(0)]

# sofa_B forms an L-shaped conversation group with sofa_A. Their upholstery
# footprints are separated by only a small gap, well under 0.50 m.
sofa_B[0].position = [3.15, 5.00, 0.425]
sofa_B[0].rotation = [0, 0, radians(90)]

coffee_table_A[0].position = [2.70, 6.20, 0.21]
coffee_table_A[0].rotation = [0, 0, radians(0)]

coffee_table_B[0].position = [3.55, 6.65, 0.20]
coffee_table_B[0].rotation = [0, 0, radians(0)]

side_table[0].position = [1.75, 7.55, 0.275]
side_table[0].rotation = [0, 0, radians(0)]

floor_standing_lamp[0].position = [4.55, 5.55, 0.825]
floor_standing_lamp[0].rotation = [0, 0, radians(180)]


# Fixed points preserve the selected functional zones while allowing the
# solver to make small feasibility adjustments.
dining_table_point = AssetInstance(position=[3.05, 8.65, 0.38])
dining_chair_A_point = AssetInstance(position=[2.55, 9.48, 0.43])
dining_chair_B_point = AssetInstance(position=[4.40, 9.00, 0.43])
dining_chair_C_point = AssetInstance(position=[3.25, 7.75, 0.43])
dining_chair_D_point = AssetInstance(position=[1.70, 8.30, 0.43])
dining_chair_E_point = AssetInstance(position=[4.40, 8.30, 0.43])

carpet_point = AssetInstance(position=[3.00, 6.05, 0.01])
sofa_A_point = AssetInstance(position=[1.74, 6.25, 0.425])
sofa_B_point = AssetInstance(position=[3.15, 5.00, 0.425])
coffee_table_A_point = AssetInstance(position=[2.70, 6.20, 0.21])
coffee_table_B_point = AssetInstance(position=[3.55, 6.65, 0.20])
side_table_point = AssetInstance(position=[1.75, 7.55, 0.275])
lamp_point = AssetInstance(position=[4.55, 5.55, 0.825])

# Orientation references for objects whose orientation is not naturally
# determined by pointing toward another piece of furniture.
north_orientation = AssetInstance(rotation=[0, 0, radians(90)])
east_orientation = AssetInstance(rotation=[0, 0, radians(0)])
south_orientation = AssetInstance(rotation=[0, 0, radians(-90)])
west_orientation = AssetInstance(rotation=[0, 0, radians(180)])


# Highest-priority dining semantics: the table remains approximately
# equidistant from chairs B and D and therefore between them.
solver.distance_constraint(
    dining_table[0], dining_chair_D[0], 1.35, 1.45, weight=10
)
solver.distance_constraint(
    dining_table[0], dining_chair_B[0], 1.35, 1.45, weight=10
)

# Chair D (o0006) faces chair E (o0007).
solver.point_towards(dining_chair_D[0], dining_chair_E[0])
solver.point_towards(dining_chair_E[0], dining_chair_D[0])

# The remaining dining chairs face the table.
solver.point_towards(dining_chair_A[0], dining_table[0])
solver.point_towards(dining_chair_B[0], dining_table[0])
solver.point_towards(dining_chair_C[0], dining_table[0])
solver.align_with(dining_table[0], north_orientation)

# Keep the table and all five chairs in their selected, non-overlapping
# positions near the window.
solver.distance_constraint(
    dining_table[0], dining_table_point, 0, 0, weight=10
)
solver.distance_constraint(
    dining_chair_A[0], dining_chair_A_point, 0, 0, weight=10
)
solver.distance_constraint(
    dining_chair_B[0], dining_chair_B_point, 0, 0, weight=10
)
solver.distance_constraint(
    dining_chair_C[0], dining_chair_C_point, 0, 0, weight=10
)
solver.distance_constraint(
    dining_chair_D[0], dining_chair_D_point, 0, 0, weight=10
)
solver.distance_constraint(
    dining_chair_E[0], dining_chair_E_point, 0, 0, weight=10
)


# sofa_A is against the long west wall above the door at y=4.81.
solver.against_wall(sofa_A[0], walls[1])
solver.align_with(sofa_A[0], east_orientation)

# The API measures center-to-center distance. A center distance around 1.85 m
# corresponds to less than 0.50 m between the two perpendicular sofa
# footprints while avoiding overlap.
solver.distance_constraint(sofa_A[0], sofa_B[0], 1.75, 2.00, weight=10)
solver.point_towards(sofa_B[0], coffee_table_A[0])

solver.distance_constraint(sofa_A[0], sofa_A_point, 0, 0, weight=10)
solver.distance_constraint(sofa_B[0], sofa_B_point, 0, 0, weight=10)

# The main coffee table is centered between the sofas and aligned with sofa_A.
solver.distance_constraint(
    coffee_table_A[0], coffee_table_A_point, 0, 0, weight=10
)
solver.align_with(coffee_table_A[0], sofa_A[0])
solver.distance_constraint(
    coffee_table_A[0], sofa_A[0], 0.90, 1.10, weight=5
)
solver.distance_constraint(
    coffee_table_A[0], sofa_B[0], 1.00, 1.30, weight=5
)

# The square coffee table occupies the open northeast part of the living zone.
solver.distance_constraint(
    coffee_table_B[0], coffee_table_B_point, 0, 0, weight=10
)
solver.align_with(coffee_table_B[0], sofa_A[0])
solver.distance_constraint(
    coffee_table_B[0], sofa_A[0], 1.70, 2.10, weight=3
)

# Keep the side table beside the north end of sofa_A.
solver.distance_constraint(side_table[0], side_table_point, 0, 0, weight=10)
solver.align_with(side_table[0], sofa_A[0])
solver.distance_constraint(side_table[0], sofa_A[0], 1.25, 1.35, weight=5)

# Place the floor lamp in the free east corner of the seating group.
solver.distance_constraint(
    floor_standing_lamp[0], lamp_point, 0, 0, weight=10
)
solver.point_towards(floor_standing_lamp[0], coffee_table_A[0])
solver.distance_constraint(
    floor_standing_lamp[0], sofa_B[0], 1.40, 1.65, weight=3
)

# The carpet anchors the living group and is oriented along the room.
solver.distance_constraint(carpet[0], carpet_point, 0, 0, weight=10)
solver.align_with(carpet[0], north_orientation)

solver.constraints = []
dining_chair_C[0].position = [3.25, 7.75, 0.4300000071525574]
dining_chair_C[0].rotation = [0, 0, 1.5802211042556205]
dining_chair_C[0].optimize = 2
side_table[0].position = [1.75, 7.550000190734863, 0.2750000059604645]
side_table[0].rotation = [0, 0, -0.02119644611335827]
side_table[0].optimize = 2
floor_standing_lamp[0].position = [4.550000190734863, 5.550000190734863, 0.824999988079071]
floor_standing_lamp[0].rotation = [0, 0, 3.106370425656669]
floor_standing_lamp[0].optimize = 2
sofa_A[0].position = [1.7781566381454468, 6.249998092651367, 0.42500001192092896]
sofa_A[0].rotation = [0, 0, -0.01240675135005541]
sofa_A[0].optimize = 2
carpet[0].position = [3.0, 6.050000190734863, 0.009999999776482582]
carpet[0].rotation = [0, 0, 1.5802211042556205]
carpet[0].optimize = 2
dining_chair_D[0].position = [1.7000000476837158, 8.300000190734863, 0.4300000071525574]
dining_chair_D[0].rotation = [0, 0, 0.0157079639172164]
dining_chair_D[0].optimize = 2
coffee_table_B[0].position = [3.549999952316284, 6.650000095367432, 0.20000000298023224]
coffee_table_B[0].rotation = [0, 0, -0.02119644611335827]
coffee_table_B[0].optimize = 2
dining_chair_B[0].position = [4.400000095367432, 9.0, 0.4300000071525574]
dining_chair_B[0].rotation = [0, 0, -2.867226913247425]
dining_chair_B[0].optimize = 2
dining_table[0].position = [3.049999952316284, 8.649999618530273, 0.3799999952316284]
dining_table[0].rotation = [0, 0, 1.5959290669047523]
dining_table[0].optimize = 2
dining_chair_E[0].position = [4.400000095367432, 8.300000190734863, 0.4300000071525574]
dining_chair_E[0].rotation = [0, 0, -3.1290262823329655]
dining_chair_E[0].optimize = 2
sofa_B[0].position = [3.1500000953674316, 5.0, 0.42500001192092896]
sofa_B[0].rotation = [0, 0, 1.6629414697842844]
sofa_B[0].optimize = 2
dining_chair_A[0].position = [2.549999952316284, 9.479999542236328, 0.4300000071525574]
dining_chair_A[0].rotation = [0, 0, -1.5613715493341729]
dining_chair_A[0].optimize = 2
coffee_table_A[0].position = [2.700000047683716, 6.199999809265137, 0.20999999344348907]
coffee_table_A[0].rotation = [0, 0, -0.028384331277329842]
coffee_table_A[0].optimize = 2

