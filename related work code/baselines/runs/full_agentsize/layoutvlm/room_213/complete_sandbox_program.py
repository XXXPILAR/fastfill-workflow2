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
    Wall(corner1=[8.79, 4.48, 0.00], corner2=[2.30, 4.48, 0.00]),
    Wall(corner1=[2.30, 4.48, 0.00], corner2=[2.30, 1.50, 0.00]),
    Wall(corner1=[2.30, 1.50, 0.00], corner2=[0.00, 1.50, 0.00]),
    Wall(corner1=[0.00, 1.50, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[9.90, 0.00, 0.00]),
    Wall(corner1=[9.90, 0.00, 0.00], corner2=[9.90, 1.20, 0.00]),
    Wall(corner1=[9.90, 1.20, 0.00], corner2=[8.79, 1.20, 0.00]),
    Wall(corner1=[8.79, 1.20, 0.00], corner2=[8.79, 4.48, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
shoe_cabinet = Assets(description="shoe cabinet", size=[0.35, 1.20, 1.00], placements=[AssetInstance() for _ in range(1)])
dining_table_combination = Assets(description="dining table combination", size=[0.90, 1.80, 0.75], placements=[AssetInstance() for _ in range(1)])
bar_chair_A = Assets(description="bar chair", size=[0.50, 0.45, 1.00], placements=[AssetInstance() for _ in range(1)])
flowers = Assets(description="flowers", size=[0.35, 0.35, 0.55], placements=[AssetInstance() for _ in range(1)])
combination_sofa = Assets(description="combination sofa", size=[1.60, 3.20, 0.85], placements=[AssetInstance() for _ in range(1)])
ornaments = Assets(description="ornaments", size=[0.18, 0.25, 0.40], placements=[AssetInstance() for _ in range(1)])
bar_chair_B = Assets(description="bar chair", size=[0.50, 0.45, 1.00], placements=[AssetInstance() for _ in range(1)])
bar = Assets(description="bar", size=[0.60, 1.80, 1.05], placements=[AssetInstance() for _ in range(1)])

shoe_cabinet[0].instance_id = 'shoe_cabinet_0'
dining_table_combination[0].instance_id = 'dining_table_combination_0'
bar_chair_A[0].instance_id = 'bar_chair_A_0'
flowers[0].instance_id = 'flowers_0'
combination_sofa[0].instance_id = 'combination_sofa_0'
ornaments[0].instance_id = 'ornaments_0'
bar_chair_B[0].instance_id = 'bar_chair_B_0'
bar[0].instance_id = 'bar_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

shoe_cabinet[0].position = [7.465884704394785, 3.1042605845563647, 0.5]
shoe_cabinet[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [6.98018162424754, 3.0155318897017325, 0.375]
dining_table_combination[0].rotation = [0, 0, 0]
bar_chair_A[0].position = [6.557873000606885, 3.8754865615200256, 0.5]
bar_chair_A[0].rotation = [0, 0, 0]
flowers[0].position = [5.934009446958888, 2.848574116177753, 0.275]
flowers[0].rotation = [0, 0, 0]
combination_sofa[0].position = [8.167220466475507, 1.4221171587522996, 0.425]
combination_sofa[0].rotation = [0, 0, 0]
ornaments[0].position = [1.725862182695415, 0.5617231313286065, 0.2]
ornaments[0].rotation = [0, 0, 0]
bar_chair_B[0].position = [5.671279841709129, 3.3209232011423486, 0.5]
bar_chair_B[0].rotation = [0, 0, 0]
bar[0].position = [3.4983787388334293, 4.210113615484727, 0.525]
bar[0].rotation = [0, 0, 0]
shoe_cabinet[0].position = [7.465884704394785, 3.1042605845563647, 0.5]
shoe_cabinet[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [6.98018162424754, 3.0155318897017325, 0.375]
dining_table_combination[0].rotation = [0, 0, 0]
bar_chair_A[0].position = [6.557873000606885, 3.8754865615200256, 0.5]
bar_chair_A[0].rotation = [0, 0, 0]
flowers[0].position = [5.934009446958888, 2.848574116177753, 0.275]
flowers[0].rotation = [0, 0, 0]
combination_sofa[0].position = [8.167220466475507, 1.4221171587522996, 0.425]
combination_sofa[0].rotation = [0, 0, 0]
ornaments[0].position = [1.725862182695415, 0.5617231313286065, 0.2]
ornaments[0].rotation = [0, 0, 0]
bar_chair_B[0].position = [5.671279841709129, 3.3209232011423486, 0.5]
bar_chair_B[0].rotation = [0, 0, 0]
bar[0].position = [3.4983787388334293, 4.210113615484727, 0.525]
bar[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the room as three functional zones:
# - dining area on the left,
# - sofa/lounge area in the center-right,
# - bar along the unobstructed section of the bottom wall.
# The approximately 1 m deep strips inside the upper doors remain clear, as do
# the approaches to the lower, left, and right-side doors.

shoe_cabinet[0].position = [8.615, 3.78, 0.50]
shoe_cabinet[0].rotation = [0, 0, radians(180)]

dining_table_combination[0].position = [3.65, 2.55, 0.375]
dining_table_combination[0].rotation = [0, 0, radians(0)]

bar_chair_A[0].position = [4.75, 1.15, 0.50]
bar_chair_A[0].rotation = [0, 0, radians(40.6)]

flowers[0].position = [4.75, 0.30, 1.325]
flowers[0].rotation = [0, 0, radians(0)]

combination_sofa[0].position = [6.50, 2.65, 0.425]
combination_sofa[0].rotation = [0, 0, radians(-90)]

ornaments[0].position = [5.75, 0.30, 1.25]
ornaments[0].rotation = [0, 0, radians(0)]

bar_chair_B[0].position = [5.75, 1.15, 0.50]
bar_chair_B[0].rotation = [0, 0, radians(63.4)]

bar[0].position = [5.25, 0.30, 0.525]
bar[0].rotation = [0, 0, radians(90)]


# Fixed reference points preserve the selected functional zones while the
# solver makes small feasibility adjustments.
dining_anchor = AssetInstance(position=[3.65, 2.55, 0.375])
chair_A_anchor = AssetInstance(position=[4.75, 1.15, 0.50])
flowers_anchor = AssetInstance(position=[4.75, 0.30, 1.325])
sofa_anchor = AssetInstance(position=[6.50, 2.65, 0.425])
ornaments_anchor = AssetInstance(position=[5.75, 0.30, 1.25])
chair_B_anchor = AssetInstance(position=[5.75, 1.15, 0.50])

shoe_cabinet_interior_point = AssetInstance(position=[7.50, 3.78, 0.50])
bar_interior_point = AssetInstance(position=[5.25, 2.00, 0.525])


# The shoe cabinet occupies the short right-wall section above the side door.
# Its narrow dimension projects into the room and its front faces inward.
solver.against_wall(shoe_cabinet[0], walls[7])
solver.point_towards(shoe_cabinet[0], shoe_cabinet_interior_point)
solver.distance_constraint(
    shoe_cabinet[0], combination_sofa[0], 2.25, 2.60, weight=1
)

# Keep the dining set in the left-central zone, with clearance from the side
# doorway at x=2.30 and from the sofa. It faces toward the lounge area.
solver.distance_constraint(
    dining_table_combination[0], dining_anchor, 0, 0, weight=10
)
solver.point_towards(dining_table_combination[0], combination_sofa[0])
solver.distance_constraint(
    dining_table_combination[0], combination_sofa[0], 2.70, 3.05, weight=1
)

# The sofa is kept clear of the upper doors and aligned horizontally across
# the room. Its front faces toward the bar and stools.
solver.distance_constraint(
    combination_sofa[0], sofa_anchor, 0, 0, weight=10
)
solver.align_with(combination_sofa[0], bar[0], angle=180)
solver.distance_constraint(
    combination_sofa[0], bar[0], 2.55, 2.95, weight=1
)

# The bar fits against the uninterrupted bottom-wall section between the
# doors at x=3.48 and x=7.12, and faces into the room.
solver.against_wall(bar[0], walls[4])
solver.point_towards(bar[0], bar_interior_point)
solver.distance_constraint(
    bar[0], combination_sofa[0], 2.55, 2.95, weight=1
)

# Both stools remain in front of the bar while facing the combination sofa,
# as required. Separate anchors prevent the stools from collapsing together.
solver.distance_constraint(
    bar_chair_A[0], chair_A_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    bar_chair_A[0], bar[0], 0.90, 1.10, weight=1
)
solver.point_towards(bar_chair_A[0], combination_sofa[0])
solver.distance_constraint(
    bar_chair_A[0], bar_chair_B[0], 0.90, 1.10, weight=1
)

solver.distance_constraint(
    bar_chair_B[0], chair_B_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    bar_chair_B[0], bar[0], 0.90, 1.10, weight=1
)
solver.point_towards(bar_chair_B[0], combination_sofa[0])
solver.distance_constraint(
    bar_chair_B[0], bar_chair_A[0], 0.90, 1.10, weight=1
)

# Place both decorative objects securely on top of the bar. Their distinct
# anchored positions keep them separated and away from the bar's edges.
solver.on_top_of(flowers[0], bar[0])
solver.distance_constraint(
    flowers[0], flowers_anchor, 0, 0, weight=10
)
solver.align_with(flowers[0], bar[0], angle=-90)
solver.distance_constraint(
    flowers[0], ornaments[0], 0.90, 1.10, weight=1
)

solver.on_top_of(ornaments[0], bar[0])
solver.distance_constraint(
    ornaments[0], ornaments_anchor, 0, 0, weight=10
)
solver.align_with(ornaments[0], bar[0], angle=-90)
solver.distance_constraint(
    ornaments[0], flowers[0], 0.90, 1.10, weight=1
)

solver.constraints = []
combination_sofa[0].position = [6.5, 2.6500000953674316, 0.42500001192092896]
combination_sofa[0].rotation = [0, 0, -1.5707963833262168]
combination_sofa[0].optimize = 2
bar_chair_A[0].position = [4.75, 1.149999976158142, 0.5]
bar_chair_A[0].rotation = [0, 0, 0.7274532327941379]
bar_chair_A[0].optimize = 2
bar_chair_B[0].position = [5.75, 1.149999976158142, 0.5]
bar_chair_B[0].rotation = [0, 0, 1.1253883027208602]
bar_chair_B[0].optimize = 2
flowers[0].position = [4.75, 0.30000001192092896, 1.3249999284744263]
flowers[0].rotation = [0, 0, -6.122150685256713e-08]
flowers[0].optimize = 2
shoe_cabinet[0].position = [8.614999771118164, 3.7799999713897705, 0.5]
shoe_cabinet[0].rotation = [0, 0, -3.1415925881924167]
shoe_cabinet[0].optimize = 2
bar[0].position = [5.25, 0.29999998211860657, 0.5249999761581421]
bar[0].rotation = [0, 0, 1.570796419730865]
bar[0].optimize = 2
dining_table_combination[0].position = [3.6500000953674316, 2.549999952316284, 0.375]
dining_table_combination[0].rotation = [0, 0, 0.01256637125682779]
dining_table_combination[0].optimize = 2
ornaments[0].position = [5.75, 0.30000001192092896, 1.25]
ornaments[0].rotation = [0, 0, -6.122150685256713e-08]
ornaments[0].optimize = 2

