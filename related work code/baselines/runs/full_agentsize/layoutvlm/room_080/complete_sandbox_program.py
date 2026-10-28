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
    Wall(corner1=[3.42, 0.01, 0.00], corner2=[10.71, 0.00, 0.00]),
    Wall(corner1=[10.71, 0.00, 0.00], corner2=[10.71, 8.71, 0.00]),
    Wall(corner1=[10.71, 8.71, 0.00], corner2=[8.00, 8.71, 0.00]),
    Wall(corner1=[8.00, 8.71, 0.00], corner2=[8.00, 2.21, 0.00]),
    Wall(corner1=[8.00, 2.21, 0.00], corner2=[5.21, 2.21, 0.00]),
    Wall(corner1=[5.21, 2.21, 0.00], corner2=[5.21, 4.71, 0.00]),
    Wall(corner1=[5.21, 4.71, 0.00], corner2=[0.00, 4.71, 0.00]),
    Wall(corner1=[0.00, 4.71, 0.00], corner2=[0.01, 3.42, 0.00]),
    Wall(corner1=[0.01, 3.42, 0.00], corner2=[3.42, 0.01, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
shelf_A = Assets(description="shelf", size=[0.35, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="lamp", size=[0.32, 0.32, 0.58], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.45, 0.65, 0.70], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.10, 1.80, 0.95], placements=[AssetInstance() for _ in range(1)])
vase = Assets(description="vase", size=[0.22, 0.22, 0.40], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="book", size=[0.16, 0.22, 0.03], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.50, 1.40, 0.85], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.32, 0.32, 0.58], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="book", size=[0.18, 0.24, 0.04], placements=[AssetInstance() for _ in range(1)])
book_C = Assets(description="book", size=[0.15, 0.21, 0.03], placements=[AssetInstance() for _ in range(1)])
lamp_C = Assets(description="lamp", size=[0.30, 0.30, 0.55], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="table", size=[0.60, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.30, 1.00, 1.60], placements=[AssetInstance() for _ in range(1)])
lamp_D = Assets(description="lamp", size=[0.28, 0.28, 0.52], placements=[AssetInstance() for _ in range(1)])
lamp_E = Assets(description="lamp", size=[0.40, 0.40, 1.55], placements=[AssetInstance() for _ in range(1)])

shelf_A[0].instance_id = 'shelf_A_0'
lamp_A[0].instance_id = 'lamp_A_0'
cabinet_A[0].instance_id = 'cabinet_A_0'
bed[0].instance_id = 'bed_0'
vase[0].instance_id = 'vase_0'
book_A[0].instance_id = 'book_A_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
lamp_B[0].instance_id = 'lamp_B_0'
book_B[0].instance_id = 'book_B_0'
book_C[0].instance_id = 'book_C_0'
lamp_C[0].instance_id = 'lamp_C_0'
table[0].instance_id = 'table_0'
shelf_B[0].instance_id = 'shelf_B_0'
lamp_D[0].instance_id = 'lamp_D_0'
lamp_E[0].instance_id = 'lamp_E_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'
walls[8].instance_id = 'walls_8'

shelf_A[0].position = [1.3780718039370214, 4.029717719685894, 0.9]
shelf_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [8.975513102459631, 1.0784039836939763, 0.29]
lamp_A[0].rotation = [0, 0, 0]
cabinet_A[0].position = [4.199834453945093, 2.517797883208286, 0.35]
cabinet_A[0].rotation = [0, 0, 0]
bed[0].position = [3.8207880170860844, 3.8751650080917464, 0.475]
bed[0].rotation = [0, 0, 0]
vase[0].position = [8.634012353115404, 5.740234979050687, 0.2]
vase[0].rotation = [0, 0, 0]
book_A[0].position = [8.214311860635947, 1.4798870066927645, 0.015]
book_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [9.774466713328467, 1.8089025121784252, 0.425]
cabinet_B[0].rotation = [0, 0, 0]
lamp_B[0].position = [1.478020899090324, 3.680020703917385, 0.29]
lamp_B[0].rotation = [0, 0, 0]
book_B[0].position = [4.93338265968813, 2.5646082584227794, 0.0175]
book_B[0].rotation = [0, 0, 0]
book_C[0].position = [9.592248305704839, 8.37662566728733, 0.015]
book_C[0].rotation = [0, 0, 0]
lamp_C[0].position = [4.081000140408891, 2.643394590757719, 0.275]
lamp_C[0].rotation = [0, 0, 0]
table[0].position = [10.244949056032953, 7.728643998995565, 0.375]
table[0].rotation = [0, 0, 0]
shelf_B[0].position = [5.690127945655303, 1.357289189629654, 0.8]
shelf_B[0].rotation = [0, 0, 0]
lamp_D[0].position = [9.95314303306302, 1.3730472179336903, 0.26]
lamp_D[0].rotation = [0, 0, 0]
lamp_E[0].position = [3.1275069043944743, 1.1654806274215916, 0.775]
lamp_E[0].rotation = [0, 0, 0]
shelf_A[0].position = [1.3780718039370214, 4.029717719685894, 0.9]
shelf_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [8.975513102459631, 1.0784039836939763, 0.29]
lamp_A[0].rotation = [0, 0, 0]
cabinet_A[0].position = [4.199834453945093, 2.517797883208286, 0.35]
cabinet_A[0].rotation = [0, 0, 0]
bed[0].position = [3.8207880170860844, 3.8751650080917464, 0.475]
bed[0].rotation = [0, 0, 0]
vase[0].position = [8.634012353115404, 5.740234979050687, 0.2]
vase[0].rotation = [0, 0, 0]
book_A[0].position = [8.214311860635947, 1.4798870066927645, 0.015]
book_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [9.774466713328467, 1.8089025121784252, 0.425]
cabinet_B[0].rotation = [0, 0, 0]
lamp_B[0].position = [1.478020899090324, 3.680020703917385, 0.29]
lamp_B[0].rotation = [0, 0, 0]
book_B[0].position = [4.93338265968813, 2.5646082584227794, 0.0175]
book_B[0].rotation = [0, 0, 0]
book_C[0].position = [9.592248305704839, 8.37662566728733, 0.015]
book_C[0].rotation = [0, 0, 0]
lamp_C[0].position = [4.081000140408891, 2.643394590757719, 0.275]
lamp_C[0].rotation = [0, 0, 0]
table[0].position = [10.244949056032953, 7.728643998995565, 0.375]
table[0].rotation = [0, 0, 0]
shelf_B[0].position = [5.690127945655303, 1.357289189629654, 0.8]
shelf_B[0].rotation = [0, 0, 0]
lamp_D[0].position = [9.95314303306302, 1.3730472179336903, 0.26]
lamp_D[0].rotation = [0, 0, 0]
lamp_E[0].position = [3.1275069043944743, 1.1654806274215916, 0.775]
lamp_E[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the room as two functional zones: a bedroom in the upper-right
# section and a study/storage area in the left section. The passage through
# the door at (8.00, 5.65) is intentionally left unobstructed.

# Bedroom furniture.
bed[0].position = [9.70, 7.66, 0.475]
bed[0].rotation = [0, 0, radians(-90)]

cabinet_B[0].position = [8.25, 7.70, 0.425]
cabinet_B[0].rotation = [0, 0, radians(0)]

lamp_B[0].position = [8.25, 7.70, 1.14]
lamp_B[0].rotation = [0, 0, radians(0)]

lamp_E[0].position = [10.51, 5.55, 0.775]
lamp_E[0].rotation = [0, 0, radians(180)]

# Study and storage furniture along the walls of the left-hand area.
table[0].position = [3.50, 4.41, 0.375]
table[0].rotation = [0, 0, radians(-90)]

cabinet_A[0].position = [4.65, 4.485, 0.35]
cabinet_A[0].rotation = [0, 0, radians(-90)]

shelf_A[0].position = [5.035, 3.05, 0.90]
shelf_A[0].rotation = [0, 0, radians(180)]

shelf_B[0].position = [2.10, 4.56, 0.80]
shelf_B[0].rotation = [0, 0, radians(-90)]

# Two task lamps share the wide table without overlapping.
lamp_C[0].position = [3.18, 4.41, 1.025]
lamp_C[0].rotation = [0, 0, radians(-90)]

lamp_D[0].position = [3.78, 4.41, 1.01]
lamp_D[0].rotation = [0, 0, radians(-90)]

# The smaller cabinet carries its own lamp.
lamp_A[0].position = [4.65, 4.485, 0.99]
lamp_A[0].rotation = [0, 0, radians(-90)]

# Decorative objects are supported by the shelves. The three books are
# spaced across shelf_B's one-meter-wide top.
vase[0].position = [5.035, 3.05, 2.00]
vase[0].rotation = [0, 0, radians(180)]

book_A[0].position = [1.80, 4.56, 1.615]
book_A[0].rotation = [0, 0, radians(-90)]

book_B[0].position = [2.10, 4.56, 1.62]
book_B[0].rotation = [0, 0, radians(-90)]

book_C[0].position = [2.39, 4.56, 1.615]
book_C[0].rotation = [0, 0, radians(-90)]


# Fixed reference points retain each item's intended position along its wall
# while the wall constraints keep the furniture flush with the boundary.
bed_anchor = AssetInstance(position=[9.70, 7.66, 0.475])
cabinet_B_anchor = AssetInstance(position=[8.25, 7.70, 0.425])
lamp_E_anchor = AssetInstance(position=[10.51, 5.55, 0.775])
table_anchor = AssetInstance(position=[3.50, 4.41, 0.375])
cabinet_A_anchor = AssetInstance(position=[4.65, 4.485, 0.35])
shelf_A_anchor = AssetInstance(position=[5.035, 3.05, 0.90])
shelf_B_anchor = AssetInstance(position=[2.10, 4.56, 0.80])

# Furniture-wall relationships are the primary position constraints.
solver.against_wall(bed[0], walls[2])
solver.distance_constraint(bed[0], bed_anchor, 0, 0, weight=10)
solver.point_towards(
    bed[0], AssetInstance(position=[9.70, 5.50, 0.475])
)

solver.against_wall(cabinet_B[0], walls[3])
solver.distance_constraint(cabinet_B[0], cabinet_B_anchor, 0, 0, weight=10)
solver.point_towards(
    cabinet_B[0], AssetInstance(position=[9.50, 7.70, 0.425])
)

solver.against_wall(lamp_E[0], walls[1])
solver.distance_constraint(lamp_E[0], lamp_E_anchor, 0, 0, weight=10)
solver.point_towards(lamp_E[0], bed[0])

solver.against_wall(table[0], walls[6])
solver.distance_constraint(table[0], table_anchor, 0, 0, weight=10)
solver.point_towards(
    table[0], AssetInstance(position=[3.50, 3.20, 0.375])
)

solver.against_wall(cabinet_A[0], walls[6])
solver.distance_constraint(cabinet_A[0], cabinet_A_anchor, 0, 0, weight=10)
solver.point_towards(
    cabinet_A[0], AssetInstance(position=[4.65, 3.50, 0.35])
)

solver.against_wall(shelf_A[0], walls[5])
solver.distance_constraint(shelf_A[0], shelf_A_anchor, 0, 0, weight=10)
solver.point_towards(
    shelf_A[0], AssetInstance(position=[4.00, 3.05, 0.90])
)

solver.against_wall(shelf_B[0], walls[6])
solver.distance_constraint(shelf_B[0], shelf_B_anchor, 0, 0, weight=10)
solver.point_towards(
    shelf_B[0], AssetInstance(position=[2.10, 3.40, 0.80])
)


# Every small object receives a support constraint, a position constraint,
# and an orientation constraint relative to its supporting furniture.
solver.on_top_of(lamp_B[0], cabinet_B[0])
solver.distance_constraint(
    lamp_B[0],
    AssetInstance(position=[8.25, 7.70, 1.14]),
    0,
    0,
    weight=10,
)
solver.align_with(lamp_B[0], cabinet_B[0])

solver.on_top_of(lamp_A[0], cabinet_A[0])
solver.distance_constraint(
    lamp_A[0],
    AssetInstance(position=[4.65, 4.485, 0.99]),
    0,
    0,
    weight=10,
)
solver.align_with(lamp_A[0], cabinet_A[0])

solver.on_top_of(lamp_C[0], table[0])
solver.distance_constraint(
    lamp_C[0],
    AssetInstance(position=[3.18, 4.41, 1.025]),
    0,
    0,
    weight=10,
)
solver.align_with(lamp_C[0], table[0])

solver.on_top_of(lamp_D[0], table[0])
solver.distance_constraint(
    lamp_D[0],
    AssetInstance(position=[3.78, 4.41, 1.01]),
    0,
    0,
    weight=10,
)
solver.align_with(lamp_D[0], table[0])

solver.on_top_of(vase[0], shelf_A[0])
solver.distance_constraint(
    vase[0],
    AssetInstance(position=[5.035, 3.05, 2.00]),
    0,
    0,
    weight=10,
)
solver.align_with(vase[0], shelf_A[0])

solver.on_top_of(book_A[0], shelf_B[0])
solver.distance_constraint(
    book_A[0],
    AssetInstance(position=[1.80, 4.56, 1.615]),
    0,
    0,
    weight=10,
)
solver.align_with(book_A[0], shelf_B[0])

solver.on_top_of(book_B[0], shelf_B[0])
solver.distance_constraint(
    book_B[0],
    AssetInstance(position=[2.10, 4.56, 1.62]),
    0,
    0,
    weight=10,
)
solver.align_with(book_B[0], shelf_B[0])

solver.on_top_of(book_C[0], shelf_B[0])
solver.distance_constraint(
    book_C[0],
    AssetInstance(position=[2.39, 4.56, 1.615]),
    0,
    0,
    weight=10,
)
solver.align_with(book_C[0], shelf_B[0])

solver.constraints = []
vase[0].position = [5.034999847412109, 3.049999952316284, 2.0]
vase[0].rotation = [0, 0, -3.1415920440358183]
vase[0].optimize = 2
lamp_C[0].position = [3.180000066757202, 4.409999847412109, 1.024999976158142]
lamp_C[0].rotation = [0, 0, -1.5707959044469426]
lamp_C[0].optimize = 2
lamp_D[0].position = [3.7799999713897705, 4.409999847412109, 1.0099999904632568]
lamp_D[0].rotation = [0, 0, -1.5707959044469426]
lamp_D[0].optimize = 2
shelf_A[0].position = [5.034576416015625, 3.049999952316284, 0.8999999761581421]
shelf_A[0].rotation = [0, 0, 3.141592450955651]
shelf_A[0].optimize = 2
lamp_E[0].position = [10.509576797485352, 5.550000190734863, 0.7749999761581421]
lamp_E[0].rotation = [0, 0, -3.1415925066137977]
lamp_E[0].optimize = 2
book_C[0].position = [2.390000104904175, 4.559999942779541, 1.6150000095367432]
book_C[0].rotation = [0, 0, -1.5707949030245818]
book_C[0].optimize = 2
table[0].position = [3.5, 4.409576892852783, 0.375]
table[0].rotation = [0, 0, -1.5707961742264307]
table[0].optimize = 2
lamp_A[0].position = [4.650000095367432, 4.485000133514404, 0.9900000095367432]
lamp_A[0].rotation = [0, 0, -1.5707956861436796]
lamp_A[0].optimize = 2
book_A[0].position = [1.7999999523162842, 4.559999942779541, 1.6150000095367432]
book_A[0].rotation = [0, 0, -1.5707949030245818]
book_A[0].optimize = 2
lamp_B[0].position = [8.25, 7.699999809265137, 1.1399999856948853]
lamp_B[0].rotation = [0, 0, 5.382788746647353e-07]
lamp_B[0].optimize = 2
cabinet_A[0].position = [4.650000095367432, 4.484576225280762, 0.3499999940395355]
cabinet_A[0].rotation = [0, 0, -1.5707964972022295]
cabinet_A[0].optimize = 2
book_B[0].position = [2.0999999046325684, 4.559999942779541, 1.6200000047683716]
book_B[0].rotation = [0, 0, -1.5707949030245818]
book_B[0].optimize = 2
bed[0].position = [9.657933235168457, 7.291684150695801, 0.4749999940395355]
bed[0].rotation = [0, 0, 3.141421527559109]
bed[0].optimize = 2
cabinet_B[0].position = [8.250000953674316, 7.699999809265137, 0.42500001192092896]
cabinet_B[0].rotation = [0, 0, -1.2909899092382186e-07]
cabinet_B[0].optimize = 2
shelf_B[0].position = [2.0999999046325684, 4.559576511383057, 0.800000011920929]
shelf_B[0].rotation = [0, 0, -1.5707966329872916]
shelf_B[0].optimize = 2

