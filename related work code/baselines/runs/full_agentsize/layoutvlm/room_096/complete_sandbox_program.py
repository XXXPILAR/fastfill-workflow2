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
    Wall(corner1=[0.00, 3.40, 0.00], corner2=[0.00, 0.04, 0.00]),
    Wall(corner1=[0.00, 0.04, 0.00], corner2=[0.04, 0.00, 0.00]),
    Wall(corner1=[0.04, 0.00, 0.00], corner2=[3.09, 0.00, 0.00]),
    Wall(corner1=[3.09, 0.00, 0.00], corner2=[3.12, 0.04, 0.00]),
    Wall(corner1=[3.12, 0.04, 0.00], corner2=[3.12, 3.40, 0.00]),
    Wall(corner1=[3.12, 3.40, 0.00], corner2=[3.09, 3.44, 0.00]),
    Wall(corner1=[3.09, 3.44, 0.00], corner2=[0.04, 3.44, 0.00]),
    Wall(corner1=[0.04, 3.44, 0.00], corner2=[0.00, 3.40, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bed = Assets(description="bed", size=[2.00, 1.60, 0.55], placements=[AssetInstance() for _ in range(1)])
basket = Assets(description="basket", size=[0.32, 0.42, 0.30], placements=[AssetInstance() for _ in range(1)])
book = Assets(description="book", size=[0.23, 0.16, 0.03], placements=[AssetInstance() for _ in range(1)])
bin = Assets(description="bin", size=[0.25, 0.25, 0.35], placements=[AssetInstance() for _ in range(1)])
bag_A = Assets(description="bag", size=[0.20, 0.42, 0.32], placements=[AssetInstance() for _ in range(1)])
toy_A = Assets(description="toy", size=[0.12, 0.18, 0.15], placements=[AssetInstance() for _ in range(1)])
backpack_A = Assets(description="backpack", size=[0.20, 0.32, 0.45], placements=[AssetInstance() for _ in range(1)])
hat = Assets(description="hat", size=[0.30, 0.30, 0.14], placements=[AssetInstance() for _ in range(1)])
stand = Assets(description="stand", size=[0.45, 0.45, 1.70], placements=[AssetInstance() for _ in range(1)])
backpack_B = Assets(description="backpack", size=[0.18, 0.30, 0.42], placements=[AssetInstance() for _ in range(1)])
shoe = Assets(description="shoe", size=[0.30, 0.12, 0.11], placements=[AssetInstance() for _ in range(1)])
dresser = Assets(description="dresser", size=[0.45, 0.90, 0.80], placements=[AssetInstance() for _ in range(1)])
toy_B = Assets(description="toy", size=[0.15, 0.22, 0.12], placements=[AssetInstance() for _ in range(1)])
bag_B = Assets(description="bag", size=[0.22, 0.45, 0.35], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="table", size=[0.45, 0.55, 0.62], placements=[AssetInstance() for _ in range(1)])
bowl = Assets(description="bowl", size=[0.22, 0.22, 0.09], placements=[AssetInstance() for _ in range(1)])
shelf = Assets(description="shelf", size=[0.25, 0.80, 0.04], placements=[AssetInstance() for _ in range(1)])
bag_C = Assets(description="bag", size=[0.20, 0.40, 0.32], placements=[AssetInstance() for _ in range(1)])

bed[0].instance_id = 'bed_0'
basket[0].instance_id = 'basket_0'
book[0].instance_id = 'book_0'
bin[0].instance_id = 'bin_0'
bag_A[0].instance_id = 'bag_A_0'
toy_A[0].instance_id = 'toy_A_0'
backpack_A[0].instance_id = 'backpack_A_0'
hat[0].instance_id = 'hat_0'
stand[0].instance_id = 'stand_0'
backpack_B[0].instance_id = 'backpack_B_0'
shoe[0].instance_id = 'shoe_0'
dresser[0].instance_id = 'dresser_0'
toy_B[0].instance_id = 'toy_B_0'
bag_B[0].instance_id = 'bag_B_0'
table[0].instance_id = 'table_0'
bowl[0].instance_id = 'bowl_0'
shelf[0].instance_id = 'shelf_0'
bag_C[0].instance_id = 'bag_C_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

bed[0].position = [1.5943187251248925, 1.184005709381463, 0.275]
bed[0].rotation = [0, 0, 0]
basket[0].position = [1.7307090065649744, 1.1069625036796082, 0.15]
basket[0].rotation = [0, 0, 0]
book[0].position = [2.391976977241069, 0.30351102700761784, 0.015]
book[0].rotation = [0, 0, 0]
bin[0].position = [0.2231801243494161, 0.8030493570373983, 0.175]
bin[0].rotation = [0, 0, 0]
bag_A[0].position = [1.5752989680158636, 0.2622313565050061, 0.16]
bag_A[0].rotation = [0, 0, 0]
toy_A[0].position = [2.442157944426551, 1.2627039497639498, 0.075]
toy_A[0].rotation = [0, 0, 0]
backpack_A[0].position = [1.3877827088481616, 2.558656478755313, 0.225]
backpack_A[0].rotation = [0, 0, 0]
hat[0].position = [1.5514040104388436, 1.9145267228868996, 0.07]
hat[0].rotation = [0, 0, 0]
stand[0].position = [0.0051663250566706675, 3.239895873498192, 0.85]
stand[0].rotation = [0, 0, 0]
backpack_B[0].position = [2.6702508454655027, 2.1423331942640114, 0.21]
backpack_B[0].rotation = [0, 0, 0]
shoe[0].position = [0.005310377358776555, 2.582949690725596, 0.055]
shoe[0].rotation = [0, 0, 0]
dresser[0].position = [2.9335770547586932, 0.9000481862755949, 0.4]
dresser[0].rotation = [0, 0, 0]
toy_B[0].position = [1.0497867475199267, 0.11126356371345442, 0.06]
toy_B[0].rotation = [0, 0, 0]
bag_B[0].position = [1.6694833573771273, 2.0937338744448173, 0.175]
bag_B[0].rotation = [0, 0, 0]
table[0].position = [0.775286984008117, 2.3129516806701, 0.31]
table[0].rotation = [0, 0, 0]
bowl[0].position = [1.468484856881017, 0.8198005079468452, 0.045]
bowl[0].rotation = [0, 0, 0]
shelf[0].position = [0.34672092056305637, 0.4099854870801054, 0.02]
shelf[0].rotation = [0, 0, 0]
bag_C[0].position = [2.615680199701649, 2.0188059624539325, 0.16]
bag_C[0].rotation = [0, 0, 0]
bed[0].position = [1.5943187251248925, 1.184005709381463, 0.275]
bed[0].rotation = [0, 0, 0]
basket[0].position = [1.7307090065649744, 1.1069625036796082, 0.15]
basket[0].rotation = [0, 0, 0]
book[0].position = [2.391976977241069, 0.30351102700761784, 0.015]
book[0].rotation = [0, 0, 0]
bin[0].position = [0.2231801243494161, 0.8030493570373983, 0.175]
bin[0].rotation = [0, 0, 0]
bag_A[0].position = [1.5752989680158636, 0.2622313565050061, 0.16]
bag_A[0].rotation = [0, 0, 0]
toy_A[0].position = [2.442157944426551, 1.2627039497639498, 0.075]
toy_A[0].rotation = [0, 0, 0]
backpack_A[0].position = [1.3877827088481616, 2.558656478755313, 0.225]
backpack_A[0].rotation = [0, 0, 0]
hat[0].position = [1.5514040104388436, 1.9145267228868996, 0.07]
hat[0].rotation = [0, 0, 0]
stand[0].position = [0.0051663250566706675, 3.239895873498192, 0.85]
stand[0].rotation = [0, 0, 0]
backpack_B[0].position = [2.6702508454655027, 2.1423331942640114, 0.21]
backpack_B[0].rotation = [0, 0, 0]
shoe[0].position = [0.005310377358776555, 2.582949690725596, 0.055]
shoe[0].rotation = [0, 0, 0]
dresser[0].position = [2.9335770547586932, 0.9000481862755949, 0.4]
dresser[0].rotation = [0, 0, 0]
toy_B[0].position = [1.0497867475199267, 0.11126356371345442, 0.06]
toy_B[0].rotation = [0, 0, 0]
bag_B[0].position = [1.6694833573771273, 2.0937338744448173, 0.175]
bag_B[0].rotation = [0, 0, 0]
table[0].position = [0.775286984008117, 2.3129516806701, 0.31]
table[0].rotation = [0, 0, 0]
bowl[0].position = [1.468484856881017, 0.8198005079468452, 0.045]
bowl[0].rotation = [0, 0, 0]
shelf[0].position = [0.34672092056305637, 0.4099854870801054, 0.02]
shelf[0].rotation = [0, 0, 0]
bag_C[0].position = [2.615680199701649, 2.0188059624539325, 0.16]
bag_C[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the bed along the upper wall, shifted right so that the two door
# approaches on the left remain unobstructed. Its front points toward bag_C
# (o0017), which is positioned beside the bed.
bed[0].position = [2.07, 2.64, 0.275]
bed[0].rotation = [0, 0, radians(180)]

# Arrange bag_A (o0004), the basket (o0001), and bag_B (o0013) in a row.
# The basket is centered between the two bags with enough separation to
# prevent their bounding boxes from overlapping.
bag_A[0].position = [0.85, 1.27, 0.16]
bag_A[0].rotation = [0, 0, 0]

basket[0].position = [1.25, 1.27, 0.15]
basket[0].rotation = [0, 0, 0]

bag_B[0].position = [1.65, 1.27, 0.175]
bag_B[0].rotation = [0, 0, radians(180)]

# Keep the lower-left door approaches clear by placing the remaining
# floor objects away from the left wall.
backpack_A[0].position = [1.00, 0.69, 0.225]
backpack_A[0].rotation = [0, 0, radians(-90)]

backpack_B[0].position = [1.40, 0.68, 0.21]
backpack_B[0].rotation = [0, 0, radians(-90)]

stand[0].position = [1.90, 0.225, 0.85]
stand[0].rotation = [0, 0, radians(90)]

shoe[0].position = [2.43, 0.12, 0.055]
shoe[0].rotation = [0, 0, 0]

# Put the dresser against the lower portion of the right wall, below the
# window area. The nearby table remains separated from it and from the bed.
dresser[0].position = [2.895, 0.68, 0.40]
dresser[0].rotation = [0, 0, radians(180)]

table[0].position = [2.25, 1.39, 0.31]
table[0].rotation = [0, 0, radians(180)]

# Use the otherwise unused upper-left corner for the bin, beyond the door
# openings and outside the bed footprint.
bin[0].position = [0.15, 3.20, 0.175]
bin[0].rotation = [0, 0, radians(90)]

# bag_C (o0017) sits beside the bed without blocking either doorway.
bag_C[0].position = [0.75, 2.70, 0.16]
bag_C[0].rotation = [0, 0, 0]

# Place small objects on suitable supporting surfaces.
toy_A[0].position = [2.05, 2.62, 0.625]
toy_A[0].rotation = [0, 0, radians(180)]

book[0].position = [2.25, 1.24, 0.635]
book[0].rotation = [0, 0, radians(180)]

bowl[0].position = [2.25, 1.49, 0.665]
bowl[0].rotation = [0, 0, radians(180)]

# The shelf fits on the dresser top; toy_B is placed on the shelf.
shelf[0].position = [2.895, 0.68, 0.82]
shelf[0].rotation = [0, 0, radians(180)]

toy_B[0].position = [2.895, 0.68, 0.90]
toy_B[0].rotation = [0, 0, radians(180)]

# The hat is supported by the tall stand.
hat[0].position = [1.90, 0.225, 1.77]
hat[0].rotation = [0, 0, radians(90)]


# Fixed references preserve the selected functional zones while allowing
# the solver to make small feasibility adjustments.
bed_anchor = AssetInstance(position=[2.07, 2.64, 0.275])
bag_A_anchor = AssetInstance(position=[0.85, 1.27, 0.16])
basket_anchor = AssetInstance(position=[1.25, 1.27, 0.15])
bag_B_anchor = AssetInstance(position=[1.65, 1.27, 0.175])
backpack_A_anchor = AssetInstance(position=[1.00, 0.69, 0.225])
backpack_B_anchor = AssetInstance(position=[1.40, 0.68, 0.21])
stand_anchor = AssetInstance(
    position=[1.90, 0.225, 0.85],
    rotation=[0, 0, radians(90)],
)
shoe_anchor = AssetInstance(
    position=[2.43, 0.12, 0.055],
    rotation=[0, 0, 0],
)
dresser_anchor = AssetInstance(
    position=[2.895, 0.68, 0.40],
    rotation=[0, 0, radians(180)],
)
table_anchor = AssetInstance(
    position=[2.25, 1.39, 0.31],
    rotation=[0, 0, radians(180)],
)
bin_anchor = AssetInstance(
    position=[0.15, 3.20, 0.175],
    rotation=[0, 0, radians(90)],
)
bag_C_anchor = AssetInstance(position=[0.75, 2.70, 0.16])


# Bed: staying at the upper wall is important, and it must face bag_C.
solver.against_wall(bed[0], walls[6])
solver.distance_constraint(bed[0], bed_anchor, 0, 0.08, weight=10)
solver.point_towards(bed[0], bag_C[0])

# Preserve the required bag_A--basket--bag_B ordering. The equal distances,
# together with their initial collinear positions, keep the basket between
# the two bags.
solver.distance_constraint(basket[0], basket_anchor, 0, 0.05, weight=10)
solver.distance_constraint(basket[0], bag_A[0], 0.40, 0.40, weight=10)
solver.distance_constraint(basket[0], bag_B[0], 0.40, 0.40, weight=10)
solver.align_with(basket[0], bag_A[0])

solver.distance_constraint(bag_A[0], bag_A_anchor, 0, 0.05, weight=10)
solver.distance_constraint(bag_A[0], basket[0], 0.40, 0.40, weight=10)
solver.point_towards(bag_A[0], basket[0])

solver.distance_constraint(bag_B[0], bag_B_anchor, 0, 0.05, weight=10)
solver.distance_constraint(bag_B[0], basket[0], 0.40, 0.40, weight=10)
solver.point_towards(bag_B[0], basket[0])

# Floor-object position and orientation constraints.
solver.distance_constraint(backpack_A[0], backpack_A_anchor, 0, 0.06, weight=10)
solver.point_towards(backpack_A[0], stand[0])

solver.distance_constraint(backpack_B[0], backpack_B_anchor, 0, 0.06, weight=10)
solver.point_towards(backpack_B[0], stand[0])

solver.against_wall(stand[0], walls[2])
solver.distance_constraint(stand[0], stand_anchor, 0, 0.05, weight=10)
solver.align_with(stand[0], stand_anchor)

solver.against_wall(shoe[0], walls[2])
solver.distance_constraint(shoe[0], shoe_anchor, 0, 0.05, weight=10)
solver.align_with(shoe[0], shoe_anchor)

solver.against_wall(dresser[0], walls[4])
solver.distance_constraint(dresser[0], dresser_anchor, 0, 0.05, weight=10)
solver.align_with(dresser[0], dresser_anchor)

solver.distance_constraint(table[0], table_anchor, 0, 0.06, weight=10)
solver.align_with(table[0], dresser[0])

solver.against_wall(bin[0], walls[0])
solver.distance_constraint(bin[0], bin_anchor, 0, 0.05, weight=10)
solver.align_with(bin[0], bin_anchor)

solver.distance_constraint(bag_C[0], bag_C_anchor, 0, 0.06, weight=10)
solver.point_towards(bag_C[0], bed[0])


# Supported objects receive both a support constraint and a horizontal
# position constraint relative to that support.
solver.on_top_of(toy_A[0], bed[0])
solver.distance_constraint(toy_A[0], bed[0], 0, 0.15, weight=10)
solver.align_with(toy_A[0], bed[0])

solver.on_top_of(book[0], table[0])
solver.distance_constraint(book[0], table[0], 0.15, 0.15, weight=10)
solver.align_with(book[0], table[0])

solver.on_top_of(bowl[0], table[0])
solver.distance_constraint(bowl[0], table[0], 0.10, 0.10, weight=10)
solver.align_with(bowl[0], table[0])

solver.on_top_of(shelf[0], dresser[0])
solver.distance_constraint(shelf[0], dresser[0], 0, 0.03, weight=10)
solver.align_with(shelf[0], dresser[0])

solver.on_top_of(toy_B[0], shelf[0])
solver.distance_constraint(toy_B[0], shelf[0], 0, 0.03, weight=10)
solver.align_with(toy_B[0], shelf[0])

solver.on_top_of(hat[0], stand[0])
solver.distance_constraint(hat[0], stand[0], 0, 0.03, weight=10)
solver.align_with(hat[0], stand[0])

solver.constraints = []
bag_A[0].position = [0.8485634922981262, 1.2699999809265137, 0.1599999964237213]
bag_A[0].rotation = [0, 0, 0.01884955539881635]
bag_A[0].optimize = 2
hat[0].position = [1.899999976158142, 0.14986610412597656, 1.7700001001358032]
hat[0].rotation = [0, 0, 1.571688500181179]
hat[0].optimize = 2
stand[0].position = [1.899999976158142, 0.22498151659965515, 0.8500000238418579]
stand[0].rotation = [0, 0, 1.570567716901361]
stand[0].optimize = 2
shoe[0].position = [2.430000066757202, 0.15086305141448975, 0.054999999701976776]
shoe[0].rotation = [0, 0, 1.4558281281834926]
shoe[0].optimize = 2
backpack_B[0].position = [1.399999976158142, 0.6800000071525574, 0.20999999344348907]
backpack_B[0].rotation = [0, 0, -1.184365760036396]
backpack_B[0].optimize = 2
basket[0].position = [1.2468889951705933, 1.2699999809265137, 0.15000000596046448]
basket[0].rotation = [0, 0, 0.018963220857627732]
basket[0].optimize = 2
table[0].position = [2.25, 1.3899999856948853, 0.3100000023841858]
table[0].rotation = [0, 0, 3.1414221763656247]
table[0].optimize = 2
bed[0].position = [1.7784379720687866, 2.3434784412384033, 0.2750000059604645]
bed[0].rotation = [0, 0, -1.6989193493261603]
bed[0].optimize = 2
bowl[0].position = [2.2499687671661377, 1.6649999618530273, 0.6650000214576721]
bowl[0].rotation = [0, 0, -3.1411409023520807]
bowl[0].optimize = 2
toy_A[0].position = [1.1030347347259521, 3.3619484901428223, 0.625]
toy_A[0].rotation = [0, 0, -1.7004636960083572]
toy_A[0].optimize = 2
book[0].position = [2.250023365020752, 1.1150000095367432, 0.6349999904632568]
book[0].rotation = [0, 0, -3.1411409023520807]
book[0].optimize = 2
bin[0].position = [0.14337919652462006, 3.200000047683716, 0.17499999701976776]
bin[0].rotation = [0, 0, 0.16058970180904752]
bin[0].optimize = 2
bag_B[0].position = [1.6543960571289062, 1.2699999809265137, 0.17499999701976776]
bag_B[0].rotation = [0, 0, -3.125884689672577]
bag_B[0].optimize = 2
dresser[0].position = [2.8999085426330566, 0.6800000071525574, 0.4000000059604645]
dresser[0].rotation = [0, 0, 3.1414645682643982]
dresser[0].optimize = 2
backpack_A[0].position = [1.0, 0.6899999976158142, 0.22499999403953552]
backpack_A[0].rotation = [0, 0, -0.7961643751831097]
backpack_A[0].optimize = 2
toy_B[0].position = [2.6592891216278076, 0.6800000071525574, 0.8999999761581421]
toy_B[0].rotation = [0, 0, 3.140701697093408]
toy_B[0].optimize = 2
bag_C[0].position = [0.75, 2.700000047683716, 0.1599999964237213]
bag_C[0].rotation = [0, 0, 0.01256637125682779]
bag_C[0].optimize = 2
shelf[0].position = [2.674908399581909, 0.6799673438072205, 0.8199999928474426]
shelf[0].rotation = [0, 0, -3.140700027370043]
shelf[0].optimize = 2

