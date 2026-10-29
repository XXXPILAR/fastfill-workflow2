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
    Wall(corner1=[7.69, 7.86, 0.00], corner2=[8.96, 7.86, 0.00]),
    Wall(corner1=[8.96, 7.86, 0.00], corner2=[8.96, 8.85, 0.00]),
    Wall(corner1=[8.96, 8.85, 0.00], corner2=[6.30, 8.85, 0.00]),
    Wall(corner1=[6.30, 8.85, 0.00], corner2=[6.30, 7.62, 0.00]),
    Wall(corner1=[6.30, 7.62, 0.00], corner2=[0.00, 7.62, 0.00]),
    Wall(corner1=[0.00, 7.62, 0.00], corner2=[0.00, 1.51, 0.00]),
    Wall(corner1=[0.00, 1.51, 0.00], corner2=[5.40, 1.51, 0.00]),
    Wall(corner1=[5.40, 1.51, 0.00], corner2=[5.40, 1.26, 0.00]),
    Wall(corner1=[5.40, 1.26, 0.00], corner2=[3.52, 1.26, 0.00]),
    Wall(corner1=[3.52, 1.26, 0.00], corner2=[3.52, 0.00, 0.00]),
    Wall(corner1=[3.52, 0.00, 0.00], corner2=[7.69, 0.00, 0.00]),
    Wall(corner1=[7.69, 0.00, 0.00], corner2=[7.69, 0.03, 0.00]),
    Wall(corner1=[7.69, 0.03, 0.00], corner2=[8.36, 0.03, 0.00]),
    Wall(corner1=[8.36, 0.03, 0.00], corner2=[8.36, 1.34, 0.00]),
    Wall(corner1=[8.36, 1.34, 0.00], corner2=[7.69, 1.34, 0.00]),
    Wall(corner1=[7.69, 1.34, 0.00], corner2=[7.69, 1.51, 0.00]),
    Wall(corner1=[7.69, 1.51, 0.00], corner2=[10.89, 1.51, 0.00]),
    Wall(corner1=[10.89, 1.51, 0.00], corner2=[10.89, 4.94, 0.00]),
    Wall(corner1=[10.89, 4.94, 0.00], corner2=[7.69, 4.94, 0.00]),
    Wall(corner1=[7.69, 4.94, 0.00], corner2=[7.69, 7.86, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bar_chair_A = Assets(description="bar chair", size=[0.52, 0.48, 1.05], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[2.80, 3.60, 0.02], placements=[AssetInstance() for _ in range(1)])
potted_bonsai = Assets(description="potted bonsai", size=[0.35, 0.45, 0.50], placements=[AssetInstance() for _ in range(1)])
side_table_A = Assets(description="side table", size=[0.60, 0.60, 0.55], placements=[AssetInstance() for _ in range(1)])
wardrobe_A = Assets(description="wardrobe", size=[0.60, 1.60, 2.30], placements=[AssetInstance() for _ in range(1)])
side_table_B = Assets(description="side table", size=[0.50, 0.65, 0.65], placements=[AssetInstance() for _ in range(1)])
wine_cabinet = Assets(description="wine cabinet", size=[0.45, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
bar_chair_B = Assets(description="bar chair", size=[0.52, 0.48, 1.05], placements=[AssetInstance() for _ in range(1)])
bookcase_A = Assets(description="bookcase", size=[0.35, 1.00, 2.10], placements=[AssetInstance() for _ in range(1)])
bookcase_B = Assets(description="bookcase", size=[0.35, 1.00, 2.10], placements=[AssetInstance() for _ in range(1)])
bar_chair_C = Assets(description="bar chair", size=[0.52, 0.48, 1.05], placements=[AssetInstance() for _ in range(1)])
sofa_A = Assets(description="sofa", size=[0.95, 2.40, 0.85], placements=[AssetInstance() for _ in range(1)])
bar = Assets(description="bar", size=[0.65, 2.10, 1.05], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="coffee table", size=[0.70, 1.30, 0.42], placements=[AssetInstance() for _ in range(1)])
wardrobe_B = Assets(description="wardrobe", size=[0.60, 1.60, 2.30], placements=[AssetInstance() for _ in range(1)])
shoe_cabinet = Assets(description="shoe cabinet", size=[0.35, 1.10, 1.00], placements=[AssetInstance() for _ in range(1)])
ornaments = Assets(description="ornaments", size=[0.20, 0.30, 0.35], placements=[AssetInstance() for _ in range(1)])
sofa_B = Assets(description="sofa", size=[0.95, 1.80, 0.85], placements=[AssetInstance() for _ in range(1)])
dining_table_combination = Assets(description="dining table combination", size=[2.40, 2.80, 0.90], placements=[AssetInstance() for _ in range(1)])

bar_chair_A[0].instance_id = 'bar_chair_A_0'
carpet[0].instance_id = 'carpet_0'
potted_bonsai[0].instance_id = 'potted_bonsai_0'
side_table_A[0].instance_id = 'side_table_A_0'
wardrobe_A[0].instance_id = 'wardrobe_A_0'
side_table_B[0].instance_id = 'side_table_B_0'
wine_cabinet[0].instance_id = 'wine_cabinet_0'
bar_chair_B[0].instance_id = 'bar_chair_B_0'
bookcase_A[0].instance_id = 'bookcase_A_0'
bookcase_B[0].instance_id = 'bookcase_B_0'
bar_chair_C[0].instance_id = 'bar_chair_C_0'
sofa_A[0].instance_id = 'sofa_A_0'
bar[0].instance_id = 'bar_0'
coffee_table[0].instance_id = 'coffee_table_0'
wardrobe_B[0].instance_id = 'wardrobe_B_0'
shoe_cabinet[0].instance_id = 'shoe_cabinet_0'
ornaments[0].instance_id = 'ornaments_0'
sofa_B[0].instance_id = 'sofa_B_0'
dining_table_combination[0].instance_id = 'dining_table_combination_0'
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
walls[16].instance_id = 'walls_16'
walls[17].instance_id = 'walls_17'
walls[18].instance_id = 'walls_18'
walls[19].instance_id = 'walls_19'

bar_chair_A[0].position = [5.829894440513911, 2.6379048325672665, 0.525]
bar_chair_A[0].rotation = [0, 0, 0]
carpet[0].position = [10.211406532910017, 3.8166400754969243, 0.01]
carpet[0].rotation = [0, 0, 0]
potted_bonsai[0].position = [5.483795279106088, 6.547976043518772, 0.25]
potted_bonsai[0].rotation = [0, 0, 0]
side_table_A[0].position = [9.159675779023429, 3.918920673448271, 0.275]
side_table_A[0].rotation = [0, 0, 0]
wardrobe_A[0].position = [4.552385157701355, 4.095747036635692, 1.15]
wardrobe_A[0].rotation = [0, 0, 0]
side_table_B[0].position = [6.6366866839134735, 3.590796726522911, 0.325]
side_table_B[0].rotation = [0, 0, 0]
wine_cabinet[0].position = [8.078497121846548, 3.153442612441499, 0.9]
wine_cabinet[0].rotation = [0, 0, 0]
bar_chair_B[0].position = [3.031158404214671, 2.409645318047797, 0.525]
bar_chair_B[0].rotation = [0, 0, 0]
bookcase_A[0].position = [1.3088418676366356, 2.944796502877586, 1.05]
bookcase_A[0].rotation = [0, 0, 0]
bookcase_B[0].position = [9.772741942701163, 2.888454251316417, 1.05]
bookcase_B[0].rotation = [0, 0, 0]
bar_chair_C[0].position = [0.4376931332100264, 6.576152612038132, 0.525]
bar_chair_C[0].rotation = [0, 0, 0]
sofa_A[0].position = [4.85210418663833, 6.000009799721791, 0.425]
sofa_A[0].rotation = [0, 0, 0]
bar[0].position = [10.723328897402297, 2.5254923299572707, 0.525]
bar[0].rotation = [0, 0, 0]
coffee_table[0].position = [3.951857777686569, 5.429988824800828, 0.21]
coffee_table[0].rotation = [0, 0, 0]
wardrobe_B[0].position = [6.036656127841705, 5.494794677660336, 1.15]
wardrobe_B[0].rotation = [0, 0, 0]
shoe_cabinet[0].position = [2.135776955150878, 5.422183818822179, 0.5]
shoe_cabinet[0].rotation = [0, 0, 0]
ornaments[0].position = [8.064037585950679, 1.8324957461036635, 0.175]
ornaments[0].rotation = [0, 0, 0]
sofa_B[0].position = [4.830321361545428, 4.691416913968309, 0.425]
sofa_B[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [1.554332895822912, 5.865477828992732, 0.45]
dining_table_combination[0].rotation = [0, 0, 0]
bar_chair_A[0].position = [5.829894440513911, 2.6379048325672665, 0.525]
bar_chair_A[0].rotation = [0, 0, 0]
carpet[0].position = [10.211406532910017, 3.8166400754969243, 0.01]
carpet[0].rotation = [0, 0, 0]
potted_bonsai[0].position = [5.483795279106088, 6.547976043518772, 0.25]
potted_bonsai[0].rotation = [0, 0, 0]
side_table_A[0].position = [9.159675779023429, 3.918920673448271, 0.275]
side_table_A[0].rotation = [0, 0, 0]
wardrobe_A[0].position = [4.552385157701355, 4.095747036635692, 1.15]
wardrobe_A[0].rotation = [0, 0, 0]
side_table_B[0].position = [6.6366866839134735, 3.590796726522911, 0.325]
side_table_B[0].rotation = [0, 0, 0]
wine_cabinet[0].position = [8.078497121846548, 3.153442612441499, 0.9]
wine_cabinet[0].rotation = [0, 0, 0]
bar_chair_B[0].position = [3.031158404214671, 2.409645318047797, 0.525]
bar_chair_B[0].rotation = [0, 0, 0]
bookcase_A[0].position = [1.3088418676366356, 2.944796502877586, 1.05]
bookcase_A[0].rotation = [0, 0, 0]
bookcase_B[0].position = [9.772741942701163, 2.888454251316417, 1.05]
bookcase_B[0].rotation = [0, 0, 0]
bar_chair_C[0].position = [0.4376931332100264, 6.576152612038132, 0.525]
bar_chair_C[0].rotation = [0, 0, 0]
sofa_A[0].position = [4.85210418663833, 6.000009799721791, 0.425]
sofa_A[0].rotation = [0, 0, 0]
bar[0].position = [10.723328897402297, 2.5254923299572707, 0.525]
bar[0].rotation = [0, 0, 0]
coffee_table[0].position = [3.951857777686569, 5.429988824800828, 0.21]
coffee_table[0].rotation = [0, 0, 0]
wardrobe_B[0].position = [6.036656127841705, 5.494794677660336, 1.15]
wardrobe_B[0].rotation = [0, 0, 0]
shoe_cabinet[0].position = [2.135776955150878, 5.422183818822179, 0.5]
shoe_cabinet[0].rotation = [0, 0, 0]
ornaments[0].position = [8.064037585950679, 1.8324957461036635, 0.175]
ornaments[0].rotation = [0, 0, 0]
sofa_B[0].position = [4.830321361545428, 4.691416913968309, 0.425]
sofa_B[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [1.554332895822912, 5.865477828992732, 0.45]
dining_table_combination[0].rotation = [0, 0, 0]

solver.constraints = []

# Coordinates follow the supplied wall polygon, rather than recentering it.
# Keep the upper entrance vestibule and the east-hand door approach unfurnished.
# The carpet is intentionally beneath lounge furniture; decorative objects are
# intentionally supported by furniture rather than placed on the floor.

layout_specs = [
    (wardrobe_A,              [0.95, 1.81, 1.15],  90),
    (wardrobe_B,              [3.25, 1.81, 1.15],  90),
    (bar_chair_C,             [2.10, 1.81, 0.525], 90),

    (dining_table_combination,[1.50, 5.25, 0.45],   0),
    (bookcase_A,              [0.65, 7.445, 1.05], 270),
    (bookcase_B,              [1.75, 7.445, 1.05], 270),

    (carpet,                  [4.65, 5.00, 0.01],   0),
    (sofa_A,                  [4.40, 3.55, 0.445], 90),
    (sofa_B,                  [6.10, 5.40, 0.445], 180),
    (coffee_table,            [4.40, 5.00, 0.23],  90),
    (bar_chair_A,             [4.40, 6.60, 0.545], 270),
    (side_table_A,            [2.80, 3.35, 0.275],  0),
    (potted_bonsai,           [2.80, 3.35, 0.80],   0),

    (bar,                    [8.10, 3.10, 0.525], 180),
    (side_table_B,            [8.10, 4.575, 0.325],180),
    (bar_chair_B,             [7.00, 3.10, 0.525],  0),
    (wine_cabinet,            [9.55, 1.735, 0.90], 90),
    (ornaments,              [9.55, 1.735, 1.975],90),

    (shoe_cabinet,            [5.90, 0.175, 0.50], 90),
]

for asset_group, location, heading in layout_specs:
    asset_group[0].position = list(location)
    asset_group[0].rotation = [0, 0, radians(heading)]

# Primary semantic constraints precede the general placement constraints.

# Both wardrobes have their backs against the uninterrupted lower wall.
# Chair C (o0010) occupies the gap between them.
solver.against_wall(wardrobe_A[0], walls[6])
solver.against_wall(wardrobe_B[0], walls[6])
solver.distance_constraint(
    bar_chair_C[0],
    AssetInstance(position=[2.10, 1.81, 0.525]),
    0, 0, weight=10
)
for wardrobe_group in (wardrobe_A, wardrobe_B):
    solver.distance_constraint(
        bar_chair_C[0], wardrobe_group[0], 1.30, 1.32, weight=10
    )
solver.align_with(bar_chair_C[0], wardrobe_A[0])

# Sofa A (o0011) faces chair A (o0000), across the coffee table.
solver.point_towards(sofa_A[0], bar_chair_A[0])
solver.point_towards(bar_chair_A[0], sofa_A[0])
solver.point_towards(sofa_B[0], coffee_table[0])
solver.point_towards(bar_chair_B[0], bar[0])
solver.point_towards(
    bar[0], AssetInstance(position=[7.00, 3.10, 0.525])
)

# The bar and side table B have a 0.10 m footprint edge gap.
# Center distance includes their 0.20 m difference in center height.
solver.distance_constraint(
    bar[0], side_table_B[0], 1.48, 1.51, weight=10
)
solver.align_with(side_table_B[0], bar[0])

# Place small decorative assets on genuine supporting surfaces.
solver.on_top_of(potted_bonsai[0], side_table_A[0])
solver.distance_constraint(
    potted_bonsai[0], side_table_A[0], 0.525, 0.525, weight=10
)
solver.align_with(potted_bonsai[0], side_table_A[0])

solver.on_top_of(ornaments[0], wine_cabinet[0])
solver.distance_constraint(
    ornaments[0], wine_cabinet[0], 1.075, 1.075, weight=10
)
solver.align_with(ornaments[0], wine_cabinet[0])

# Wall storage stays outside the fixed TV cabinet footprint
# (x=2.25..6.27, y=7.165..7.615).
solver.against_wall(bookcase_A[0], walls[4])
solver.against_wall(bookcase_B[0], walls[4])
solver.against_wall(wine_cabinet[0], walls[16])
solver.against_wall(shoe_cabinet[0], walls[10])

# Give every instance a positional neighborhood and an orientation constraint.
# Small tolerances preserve the designed clearances and doorway routes.
# Fixed references are constraint targets only, not additional scene assets.
for asset_group, location, heading in layout_specs:
    solver.distance_constraint(
        asset_group[0],
        AssetInstance(position=list(location)),
        0, 0.02, weight=10
    )
    solver.align_with(
        asset_group[0],
        AssetInstance(rotation=[0, 0, radians(heading)])
    )

# Maintain usable gaps in the lounge and between the bar and its chair.
solver.distance_constraint(
    sofa_A[0], coffee_table[0], 1.44, 1.49, weight=10
)
solver.distance_constraint(
    bar_chair_A[0], coffee_table[0], 1.61, 1.66, weight=10
)
solver.distance_constraint(
    bar_chair_B[0], bar[0], 1.08, 1.12, weight=10
)
solver.distance_constraint(
    bookcase_A[0], bookcase_B[0], 1.08, 1.12
)

solver.constraints = []
shoe_cabinet[0].position = [7.808437347412109, 0.2029927670955658, 0.5]
shoe_cabinet[0].rotation = [0, 0, 1.579855469467957]
shoe_cabinet[0].optimize = 2
bar_chair_A[0].position = [4.400000095367432, 6.658048152923584, 0.5249999761581421]
bar_chair_A[0].rotation = [0, 0, -1.5519467713960802]
bar_chair_A[0].optimize = 2
sofa_A[0].position = [4.400000095367432, 3.549999952316284, 0.42500001192092896]
sofa_A[0].rotation = [0, 0, 1.589645882193713]
sofa_A[0].optimize = 2
bookcase_A[0].position = [0.6499999761581421, 7.443000316619873, 1.0499999523162842]
bookcase_A[0].rotation = [0, 0, -1.570796283091378]
bookcase_A[0].optimize = 2
side_table_B[0].position = [8.100000381469727, 4.574999809265137, 0.32499998807907104]
side_table_B[0].rotation = [0, 0, -3.1164599079105946]
side_table_B[0].optimize = 2
ornaments[0].position = [9.550000190734863, 1.7350000143051147, 1.9749999046325684]
ornaments[0].rotation = [0, 0, 1.570796370526468]
ornaments[0].optimize = 2
dining_table_combination[0].position = [1.5, 5.25, 0.44999998807907104]
dining_table_combination[0].rotation = [0, 0, 0.00942477746072377]
dining_table_combination[0].optimize = 2
sofa_B[0].position = [6.099999904632568, 5.400000095367432, 0.42500001192092896]
sofa_B[0].rotation = [0, 0, -3.1088111065422344]
sofa_B[0].optimize = 2
potted_bonsai[0].position = [2.799999952316284, 3.3499999046325684, 0.800000011920929]
potted_bonsai[0].rotation = [0, 0, 0.01884955367222363]
potted_bonsai[0].optimize = 2
side_table_A[0].position = [2.799999952316284, 3.3499999046325684, 0.2750000059604645]
side_table_A[0].rotation = [0, 0, 0.01884955539881635]
side_table_A[0].optimize = 2
wardrobe_A[0].position = [0.949999988079071, 1.80899977684021, 1.149999976158142]
wardrobe_A[0].rotation = [0, 0, 1.5707963514216565]
wardrobe_A[0].optimize = 2
bar_chair_B[0].position = [7.0, 3.0999999046325684, 0.5249999761581421]
bar_chair_B[0].rotation = [0, 0, 0.0157079639172164]
bar_chair_B[0].optimize = 2
bookcase_B[0].position = [1.75, 7.443000316619873, 1.0499999523162842]
bookcase_B[0].rotation = [0, 0, -1.570796283091378]
bookcase_B[0].optimize = 2
wardrobe_B[0].position = [3.8199989795684814, 0.800029993057251, 1.149999976158142]
wardrobe_B[0].rotation = [0, 0, 9.998266459675962e-05]
wardrobe_B[0].optimize = 2
coffee_table[0].position = [4.400000095367432, 5.0, 0.20999999344348907]
coffee_table[0].rotation = [0, 0, 1.589645882193713]
coffee_table[0].optimize = 2
carpet[0].position = [4.650000095367432, 5.0, 0.009999999776482582]
carpet[0].rotation = [0, 0, 0.00942477746072377]
carpet[0].optimize = 2
bar_chair_C[0].position = [2.253763437271118, 1.7689906358718872, 0.5249999761581421]
bar_chair_C[0].rotation = [0, 0, 1.5707963513582732]
bar_chair_C[0].optimize = 2
bar[0].position = [8.100000381469727, 3.083725690841675, 0.5249999761581421]
bar[0].rotation = [0, 0, -3.1164599134799373]
bar[0].optimize = 2
wine_cabinet[0].position = [9.550000190734863, 1.7461392879486084, 0.8999999761581421]
wine_cabinet[0].rotation = [0, 0, 1.5707963705280874]
wine_cabinet[0].optimize = 2

