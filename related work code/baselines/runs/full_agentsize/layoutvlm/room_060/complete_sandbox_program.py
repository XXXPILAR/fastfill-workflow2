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
    Wall(corner1=[0.04, 4.22, 0.00], corner2=[0.00, 4.18, 0.00]),
    Wall(corner1=[0.00, 4.18, 0.00], corner2=[0.00, 0.04, 0.00]),
    Wall(corner1=[0.00, 0.04, 0.00], corner2=[0.04, 0.00, 0.00]),
    Wall(corner1=[0.04, 0.00, 0.00], corner2=[4.34, 0.00, 0.00]),
    Wall(corner1=[4.34, 0.00, 0.00], corner2=[4.38, 0.04, 0.00]),
    Wall(corner1=[4.38, 0.04, 0.00], corner2=[4.38, 4.18, 0.00]),
    Wall(corner1=[4.38, 4.18, 0.00], corner2=[4.34, 4.22, 0.00]),
    Wall(corner1=[4.34, 4.22, 0.00], corner2=[0.04, 4.22, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bed_A = Assets(description="bed", size=[1.60, 2.00, 0.50], placements=[AssetInstance() for _ in range(1)])
bed_B = Assets(description="bed", size=[1.60, 2.00, 0.50], placements=[AssetInstance() for _ in range(1)])
rack = Assets(description="rack", size=[0.45, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
toy = Assets(description="toy", size=[0.20, 0.30, 0.25], placements=[AssetInstance() for _ in range(1)])
bin = Assets(description="bin", size=[0.40, 0.50, 0.60], placements=[AssetInstance() for _ in range(1)])
box = Assets(description="box", size=[0.30, 0.40, 0.25], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="cabinet", size=[0.50, 1.00, 1.20], placements=[AssetInstance() for _ in range(1)])
treadmill = Assets(description="treadmill", size=[1.80, 0.80, 1.40], placements=[AssetInstance() for _ in range(1)])
scale = Assets(description="scale", size=[0.30, 0.35, 0.05], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="shelf", size=[0.35, 1.00, 1.80], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.35, 0.90, 1.50], placements=[AssetInstance() for _ in range(1)])
basket_A = Assets(description="basket", size=[0.35, 0.45, 0.30], placements=[AssetInstance() for _ in range(1)])
basket_B = Assets(description="basket", size=[0.35, 0.45, 0.30], placements=[AssetInstance() for _ in range(1)])
shelf_C = Assets(description="shelf", size=[0.35, 1.00, 1.80], placements=[AssetInstance() for _ in range(1)])
clothes = Assets(description="clothes", size=[0.30, 0.50, 0.10], placements=[AssetInstance() for _ in range(1)])
drawer = Assets(description="drawer", size=[0.45, 0.80, 0.80], placements=[AssetInstance() for _ in range(1)])
picture = Assets(description="picture", size=[0.05, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
lamp = Assets(description="lamp", size=[0.30, 0.30, 0.50], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="table", size=[0.60, 1.00, 0.75], placements=[AssetInstance() for _ in range(1)])
plant = Assets(description="plant", size=[0.40, 0.40, 0.80], placements=[AssetInstance() for _ in range(1)])
hanger = Assets(description="hanger", size=[0.05, 0.05, 1.60], placements=[AssetInstance() for _ in range(1)])

bed_A[0].instance_id = 'bed_A_0'
bed_B[0].instance_id = 'bed_B_0'
rack[0].instance_id = 'rack_0'
toy[0].instance_id = 'toy_0'
bin[0].instance_id = 'bin_0'
box[0].instance_id = 'box_0'
cabinet[0].instance_id = 'cabinet_0'
treadmill[0].instance_id = 'treadmill_0'
scale[0].instance_id = 'scale_0'
shelf_A[0].instance_id = 'shelf_A_0'
shelf_B[0].instance_id = 'shelf_B_0'
basket_A[0].instance_id = 'basket_A_0'
basket_B[0].instance_id = 'basket_B_0'
shelf_C[0].instance_id = 'shelf_C_0'
clothes[0].instance_id = 'clothes_0'
drawer[0].instance_id = 'drawer_0'
picture[0].instance_id = 'picture_0'
lamp[0].instance_id = 'lamp_0'
table[0].instance_id = 'table_0'
plant[0].instance_id = 'plant_0'
hanger[0].instance_id = 'hanger_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

bed_A[0].position = [1.9579989099220727, 0.29708344314966356, 0.25]
bed_A[0].rotation = [0, 0, 0]
bed_B[0].position = [1.6882777972580352, 1.3404359674655408, 0.25]
bed_B[0].rotation = [0, 0, 0]
rack[0].position = [0.698490763553026, 1.1557318042771894, 0.9]
rack[0].rotation = [0, 0, 0]
toy[0].position = [3.7675851870624437, 1.4930296110666856, 0.125]
toy[0].rotation = [0, 0, 0]
bin[0].position = [4.196856136922771, 3.6555513736323624, 0.3]
bin[0].rotation = [0, 0, 0]
box[0].position = [4.199182156563487, 0.6131727985413588, 0.125]
box[0].rotation = [0, 0, 0]
cabinet[0].position = [1.9057048809083648, 3.476329107183196, 0.6]
cabinet[0].rotation = [0, 0, 0]
treadmill[0].position = [2.198224121139001, 1.9218270767615664, 0.7]
treadmill[0].rotation = [0, 0, 0]
scale[0].position = [0.10481943803452208, 2.927911297744784, 0.025]
scale[0].rotation = [0, 0, 0]
shelf_A[0].position = [0.22172940045256703, 0.5863631373610195, 0.9]
shelf_A[0].rotation = [0, 0, 0]
shelf_B[0].position = [2.6448460855542413, 2.9453054348972034, 0.75]
shelf_B[0].rotation = [0, 0, 0]
basket_A[0].position = [1.2728701121218637, 4.180156774183554, 0.15]
basket_A[0].rotation = [0, 0, 0]
basket_B[0].position = [3.7244181078372556, 2.9143338728839083, 0.15]
basket_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [0.6124025670285381, 3.4342320615490896, 0.9]
shelf_C[0].rotation = [0, 0, 0]
clothes[0].position = [3.1212397848466953, 2.7496324349484316, 0.05]
clothes[0].rotation = [0, 0, 0]
drawer[0].position = [3.9267582034493707, 0.7845726488346704, 0.4]
drawer[0].rotation = [0, 0, 0]
picture[0].position = [0.4638768542639867, 0.525314907290794, 0.4]
picture[0].rotation = [0, 0, 0]
lamp[0].position = [1.5173565621400593, 1.4097158859462502, 0.25]
lamp[0].rotation = [0, 0, 0]
table[0].position = [1.5973089853703493, 1.5541002014419472, 0.375]
table[0].rotation = [0, 0, 0]
plant[0].position = [2.201795255779627, 2.774270543433317, 0.4]
plant[0].rotation = [0, 0, 0]
hanger[0].position = [0.48090053144268036, 0.842475942121328, 0.8]
hanger[0].rotation = [0, 0, 0]
bed_A[0].position = [1.9579989099220727, 0.29708344314966356, 0.25]
bed_A[0].rotation = [0, 0, 0]
bed_B[0].position = [1.6882777972580352, 1.3404359674655408, 0.25]
bed_B[0].rotation = [0, 0, 0]
rack[0].position = [0.698490763553026, 1.1557318042771894, 0.9]
rack[0].rotation = [0, 0, 0]
toy[0].position = [3.7675851870624437, 1.4930296110666856, 0.125]
toy[0].rotation = [0, 0, 0]
bin[0].position = [4.196856136922771, 3.6555513736323624, 0.3]
bin[0].rotation = [0, 0, 0]
box[0].position = [4.199182156563487, 0.6131727985413588, 0.125]
box[0].rotation = [0, 0, 0]
cabinet[0].position = [1.9057048809083648, 3.476329107183196, 0.6]
cabinet[0].rotation = [0, 0, 0]
treadmill[0].position = [2.198224121139001, 1.9218270767615664, 0.7]
treadmill[0].rotation = [0, 0, 0]
scale[0].position = [0.10481943803452208, 2.927911297744784, 0.025]
scale[0].rotation = [0, 0, 0]
shelf_A[0].position = [0.22172940045256703, 0.5863631373610195, 0.9]
shelf_A[0].rotation = [0, 0, 0]
shelf_B[0].position = [2.6448460855542413, 2.9453054348972034, 0.75]
shelf_B[0].rotation = [0, 0, 0]
basket_A[0].position = [1.2728701121218637, 4.180156774183554, 0.15]
basket_A[0].rotation = [0, 0, 0]
basket_B[0].position = [3.7244181078372556, 2.9143338728839083, 0.15]
basket_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [0.6124025670285381, 3.4342320615490896, 0.9]
shelf_C[0].rotation = [0, 0, 0]
clothes[0].position = [3.1212397848466953, 2.7496324349484316, 0.05]
clothes[0].rotation = [0, 0, 0]
drawer[0].position = [3.9267582034493707, 0.7845726488346704, 0.4]
drawer[0].rotation = [0, 0, 0]
picture[0].position = [0.4638768542639867, 0.525314907290794, 0.4]
picture[0].rotation = [0, 0, 0]
lamp[0].position = [1.5173565621400593, 1.4097158859462502, 0.25]
lamp[0].rotation = [0, 0, 0]
table[0].position = [1.5973089853703493, 1.5541002014419472, 0.375]
table[0].rotation = [0, 0, 0]
plant[0].position = [2.201795255779627, 2.774270543433317, 0.4]
plant[0].rotation = [0, 0, 0]
hanger[0].position = [0.48090053144268036, 0.842475942121328, 0.8]
hanger[0].rotation = [0, 0, 0]

solver.constraints = []

from math import radians

# Initial placements use the room coordinate system directly.  Beds and the
# table are kept near the north side of the room, while the treadmill occupies
# the central circulation area between the two tall shelves.
bed_A[0].position = [1.20, 3.10, 0.25]
bed_A[0].rotation = [0, 0, radians(-135)]

bed_B[0].position = [3.35, 3.10, 0.25]
bed_B[0].rotation = [0, 0, radians(135)]

rack[0].position = [0.32, 1.05, 0.90]
rack[0].rotation = [0, 0, radians(0)]

toy[0].position = [0.30, 2.20, 1.925]
toy[0].rotation = [0, 0, radians(0)]

bin[0].position = [1.05, 0.85, 0.30]
bin[0].rotation = [0, 0, radians(90)]

box[0].position = [0.32, 1.05, 1.925]
box[0].rotation = [0, 0, radians(0)]

cabinet[0].position = [3.75, 0.95, 0.60]
cabinet[0].rotation = [0, 0, radians(0)]

treadmill[0].position = [2.20, 1.45, 0.70]
treadmill[0].rotation = [0, 0, radians(0)]

scale[0].position = [2.20, 0.75, 0.025]
scale[0].rotation = [0, 0, radians(0)]

shelf_A[0].position = [0.25, 2.20, 0.90]
shelf_A[0].rotation = [0, 0, radians(0)]

shelf_B[0].position = [4.10, 2.25, 0.75]
shelf_B[0].rotation = [0, 0, radians(0)]

basket_A[0].position = [0.25, 2.20, 1.95]
basket_A[0].rotation = [0, 0, radians(0)]

basket_B[0].position = [4.10, 2.25, 1.65]
basket_B[0].rotation = [0, 0, radians(0)]

shelf_C[0].position = [4.10, 3.55, 0.90]
shelf_C[0].rotation = [0, 0, radians(0)]

clothes[0].position = [3.75, 0.95, 1.25]
clothes[0].rotation = [0, 0, radians(0)]

drawer[0].position = [3.75, 2.95, 0.40]
drawer[0].rotation = [0, 0, radians(0)]

picture[0].position = [2.45, 4.00, 2.20]
picture[0].rotation = [0, 0, radians(90)]

lamp[0].position = [1.45, 3.10, 1.00]
lamp[0].rotation = [0, 0, radians(0)]

table[0].position = [1.45, 3.10, 0.375]
table[0].rotation = [0, 0, radians(0)]

plant[0].position = [3.75, 3.75, 0.40]
plant[0].rotation = [0, 0, radians(0)]

hanger[0].position = [0.32, 1.05, 2.60]
hanger[0].rotation = [0, 0, radians(0)]


# Fixed reference points are used to preserve the intended initial locations
# while allowing the solver to make small physical-feasibility adjustments.
room_center = AssetInstance(position=[2.20, 2.10, 0.00])
bed_A_reference = AssetInstance(position=[1.20, 3.10, 0.25])
bed_B_reference = AssetInstance(position=[3.35, 3.10, 0.25])
rack_reference = AssetInstance(position=[0.32, 1.05, 0.90])
toy_reference = AssetInstance(position=[0.30, 2.20, 1.925])
bin_reference = AssetInstance(position=[1.05, 0.85, 0.30])
box_reference = AssetInstance(position=[0.32, 1.05, 1.925])
cabinet_reference = AssetInstance(position=[3.75, 0.95, 0.60])
treadmill_reference = AssetInstance(position=[2.20, 1.45, 0.70])
scale_reference = AssetInstance(position=[2.20, 0.75, 0.025])
shelf_A_reference = AssetInstance(position=[0.25, 2.20, 0.90])
shelf_B_reference = AssetInstance(position=[4.10, 2.25, 0.75])
basket_A_reference = AssetInstance(position=[0.25, 2.20, 1.95])
basket_B_reference = AssetInstance(position=[4.10, 2.25, 1.65])
shelf_C_reference = AssetInstance(position=[4.10, 3.55, 0.90])
clothes_reference = AssetInstance(position=[3.75, 0.95, 1.25])
drawer_reference = AssetInstance(position=[3.75, 2.95, 0.40])
picture_reference = AssetInstance(position=[2.45, 4.00, 2.20])
lamp_reference = AssetInstance(position=[1.45, 3.10, 1.00])
table_reference = AssetInstance(position=[1.45, 3.10, 0.375])
plant_reference = AssetInstance(position=[3.75, 3.75, 0.40])
hanger_reference = AssetInstance(position=[0.32, 1.05, 2.60])


# The bed/table relation is specified first because it is an explicit layout
# requirement.  Their centers are initially 0.25 m apart.
solver.distance_constraint(bed_A[0], table[0], 0.0, 0.30, weight=10)
solver.point_towards(bed_A[0], shelf_A[0])
solver.distance_constraint(bed_A[0], bed_A_reference, 0.0, 0.08, weight=5)

# The second bed is kept in the remaining upper-right area and oriented toward
# the room interior.
solver.distance_constraint(bed_B[0], bed_B_reference, 0.0, 0.08, weight=5)
solver.point_towards(bed_B[0], room_center)

# Tall storage pieces are placed along the side walls, leaving the center
# clear for circulation and exercise equipment.
solver.against_wall(rack[0], walls[1])
solver.point_towards(rack[0], room_center)
solver.distance_constraint(rack[0], rack_reference, 0.0, 0.08, weight=5)

solver.against_wall(cabinet[0], walls[5])
solver.point_towards(cabinet[0], room_center)
solver.distance_constraint(cabinet[0], cabinet_reference, 0.0, 0.08, weight=5)

solver.against_wall(shelf_A[0], walls[1])
solver.point_towards(shelf_A[0], room_center)
solver.distance_constraint(shelf_A[0], shelf_A_reference, 0.0, 0.08, weight=5)

solver.against_wall(shelf_B[0], walls[5])
solver.point_towards(shelf_B[0], room_center)
solver.distance_constraint(shelf_B[0], shelf_B_reference, 0.0, 0.08, weight=5)

solver.against_wall(shelf_C[0], walls[5])
solver.point_towards(shelf_C[0], room_center)
solver.distance_constraint(shelf_C[0], shelf_C_reference, 0.0, 0.08, weight=5)

# The treadmill is explicitly kept between the left and right shelves.
solver.distance_constraint(treadmill[0], shelf_A[0], 1.40, 2.35, weight=8)
solver.distance_constraint(treadmill[0], shelf_C[0], 1.40, 2.35, weight=8)
solver.point_towards(treadmill[0], room_center)
solver.distance_constraint(treadmill[0], treadmill_reference, 0.0, 0.10, weight=5)

# Floor-standing utility objects avoid the window/radiator zone along the
# bottom wall.
solver.distance_constraint(bin[0], bin_reference, 0.0, 0.08, weight=5)
solver.point_towards(bin[0], room_center)

solver.distance_constraint(scale[0], scale_reference, 0.0, 0.08, weight=5)
solver.point_towards(scale[0], treadmill[0])

solver.distance_constraint(drawer[0], drawer_reference, 0.0, 0.08, weight=5)
solver.point_towards(drawer[0], room_center)

solver.distance_constraint(plant[0], plant_reference, 0.0, 0.08, weight=5)
solver.point_towards(plant[0], room_center)

# The table remains close to the first bed and is oriented toward it.
solver.distance_constraint(table[0], bed_A[0], 0.0, 0.30, weight=10)
solver.point_towards(table[0], bed_A[0])
solver.distance_constraint(table[0], table_reference, 0.0, 0.08, weight=5)

# Wall-mounted picture placement is kept below the top wall while avoiding
# the window/radiator on the bottom wall.
solver.against_wall(picture[0], walls[7])
solver.point_towards(picture[0], room_center)
solver.distance_constraint(picture[0], picture_reference, 0.0, 0.08, weight=5)

# Small objects are supported by nearby furniture rather than being left on
# the floor.  Their position constraints also keep them near the supporting
# asset in the x-y plane.
solver.on_top_of(toy[0], shelf_A[0])
solver.distance_constraint(toy[0], toy_reference, 0.0, 0.08, weight=5)
solver.point_towards(toy[0], room_center)

solver.on_top_of(box[0], rack[0])
solver.distance_constraint(box[0], box_reference, 0.0, 0.08, weight=5)
solver.point_towards(box[0], room_center)

solver.on_top_of(basket_A[0], shelf_A[0])
solver.distance_constraint(basket_A[0], basket_A_reference, 0.0, 0.08, weight=5)
solver.point_towards(basket_A[0], room_center)

solver.on_top_of(basket_B[0], shelf_B[0])
solver.distance_constraint(basket_B[0], basket_B_reference, 0.0, 0.08, weight=5)
solver.point_towards(basket_B[0], room_center)

solver.on_top_of(clothes[0], drawer[0])
solver.distance_constraint(clothes[0], clothes_reference, 0.0, 0.08, weight=5)
solver.point_towards(clothes[0], room_center)

solver.on_top_of(lamp[0], table[0])
solver.distance_constraint(lamp[0], lamp_reference, 0.0, 0.08, weight=5)
solver.point_towards(lamp[0], bed_A[0])

solver.on_top_of(hanger[0], rack[0])
solver.distance_constraint(hanger[0], hanger_reference, 0.0, 0.08, weight=5)
solver.point_towards(hanger[0], room_center)

solver.constraints = []
plant[0].position = [3.75, 3.75, 0.4000000059604645]
plant[0].rotation = [0, 0, 0.00942477746072377]
plant[0].optimize = 2
treadmill[0].position = [2.400021553039551, 1.6456304788589478, 0.699999988079071]
treadmill[0].rotation = [0, 0, 0.01884955539881635]
treadmill[0].optimize = 2
lamp[0].position = [1.4500000476837158, 3.0999999046325684, 1.0]
lamp[0].rotation = [0, 0, 0.01256637125682779]
lamp[0].optimize = 2
basket_A[0].position = [0.25, 2.200000047683716, 1.9499999284744263]
basket_A[0].rotation = [0, 0, 0.01256637125682779]
basket_A[0].optimize = 2
picture[0].position = [2.450000047683716, 4.194769382476807, 0.4000000059604645]
picture[0].rotation = [0, 0, -1.5752341221438808]
picture[0].optimize = 2
toy[0].position = [0.30000001192092896, 2.200000047683716, 1.9249999523162842]
toy[0].rotation = [0, 0, 0.01256637125682779]
toy[0].optimize = 2
rack[0].position = [0.22500090301036835, 1.0499999523162842, 0.8999999761581421]
rack[0].rotation = [0, 0, -1.5715175669095322e-07]
rack[0].optimize = 2
shelf_B[0].position = [4.199244022369385, 2.25, 0.75]
shelf_B[0].rotation = [0, 0, 3.141175746264196]
shelf_B[0].optimize = 2
shelf_C[0].position = [4.200220108032227, 3.549999952316284, 0.8999999761581421]
shelf_C[0].rotation = [0, 0, -3.1403373695259624]
shelf_C[0].optimize = 2
bin[0].position = [1.0499999523162842, 0.8500000238418579, 0.30000001192092896]
bin[0].rotation = [0, 0, 1.5802211042556205]
bin[0].optimize = 2
shelf_A[0].position = [0.17499931156635284, 2.200000047683716, 0.8999999761581421]
shelf_A[0].rotation = [0, 0, 1.9904950704391555e-07]
shelf_A[0].optimize = 2
box[0].position = [0.3199999928474426, 1.0499999523162842, 1.9249999523162842]
box[0].rotation = [0, 0, 0.01256637125682779]
box[0].optimize = 2
cabinet[0].position = [4.123406410217285, 0.949999988079071, 0.6000000238418579]
cabinet[0].rotation = [0, 0, 3.1408721247206324]
cabinet[0].optimize = 2
bed_B[0].position = [3.1035971641540527, 2.9446816444396973, 0.25]
bed_B[0].rotation = [0, 0, 2.3656192553579443]
bed_B[0].optimize = 2
bed_A[0].position = [1.2755942344665527, 2.9493751525878906, 0.25]
bed_A[0].rotation = [0, 0, -2.3342033586689483]
bed_A[0].optimize = 2
table[0].position = [1.4500000476837158, 3.0999999046325684, 0.375]
table[0].rotation = [0, 0, 0.01884955539881635]
table[0].optimize = 2
basket_B[0].position = [4.099999904632568, 2.25, 1.649999976158142]
basket_B[0].rotation = [0, 0, 0.01256637125682779]
basket_B[0].optimize = 2
hanger[0].position = [0.3199999928474426, 1.0499999523162842, 2.5999999046325684]
hanger[0].rotation = [0, 0, 0.01256637125682779]
hanger[0].optimize = 2
scale[0].position = [2.200000047683716, 0.75, 0.02500000037252903]
scale[0].rotation = [0, 0, 0.45147939505416734]
scale[0].optimize = 2
drawer[0].position = [3.75, 2.950000047683716, 0.4000000059604645]
drawer[0].rotation = [0, 0, 0.01256637125682779]
drawer[0].optimize = 2
clothes[0].position = [3.729896068572998, 2.549715757369995, 0.8500000238418579]
clothes[0].rotation = [0, 0, 0.01256637125682779]
clothes[0].optimize = 2

