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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.50, 0.00, 0.00]),
    Wall(corner1=[3.50, 0.00, 0.00], corner2=[3.50, 4.00, 0.00]),
    Wall(corner1=[3.50, 4.00, 0.00], corner2=[0.00, 4.00, 0.00]),
    Wall(corner1=[0.00, 4.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
botanical_print_A = Assets(description="botanical print", size=[0.03, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])
shelving_unit = Assets(description="shelving unit", size=[0.35, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
massage_table = Assets(description="massage table", size=[0.70, 1.85, 0.75], placements=[AssetInstance() for _ in range(1)])
terry_towel = Assets(description="terry towel", size=[0.30, 0.60, 0.03], placements=[AssetInstance() for _ in range(1)])
trolley_cart = Assets(description="trolley cart", size=[0.45, 0.65, 0.85], placements=[AssetInstance() for _ in range(1)])
privacy_screen = Assets(description="privacy screen", size=[0.45, 1.80, 1.80], placements=[AssetInstance() for _ in range(1)])
floor_lamp = Assets(description="floor lamp", size=[0.35, 0.35, 1.65], placements=[AssetInstance() for _ in range(1)])
clock = Assets(description="clock", size=[0.04, 0.30, 0.30], placements=[AssetInstance() for _ in range(1)])
stool = Assets(description="stool", size=[0.38, 0.38, 0.48], placements=[AssetInstance() for _ in range(1)])
artwork = Assets(description="artwork", size=[0.04, 0.70, 0.50], placements=[AssetInstance() for _ in range(1)])
botanical_print_B = Assets(description="botanical print", size=[0.03, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])

botanical_print_A[0].instance_id = 'botanical_print_A_0'
shelving_unit[0].instance_id = 'shelving_unit_0'
massage_table[0].instance_id = 'massage_table_0'
terry_towel[0].instance_id = 'terry_towel_0'
trolley_cart[0].instance_id = 'trolley_cart_0'
privacy_screen[0].instance_id = 'privacy_screen_0'
floor_lamp[0].instance_id = 'floor_lamp_0'
clock[0].instance_id = 'clock_0'
stool[0].instance_id = 'stool_0'
artwork[0].instance_id = 'artwork_0'
botanical_print_B[0].instance_id = 'botanical_print_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

botanical_print_A[0].position = [2.935723912177499, 1.9630224293083183, 0.3]
botanical_print_A[0].rotation = [0, 0, 0]
shelving_unit[0].position = [0.1714305851325634, 0.5510322100892417, 0.9]
shelving_unit[0].rotation = [0, 0, 0]
massage_table[0].position = [1.8676642750897738, 0.7607914702372214, 0.375]
massage_table[0].rotation = [0, 0, 0]
terry_towel[0].position = [1.4291277379112963, 1.9203358808463045, 0.015]
terry_towel[0].rotation = [0, 0, 0]
trolley_cart[0].position = [2.4529223636333257, 1.1236201182094083, 0.425]
trolley_cart[0].rotation = [0, 0, 0]
privacy_screen[0].position = [1.514982642901418, 2.798634681391512, 0.9]
privacy_screen[0].rotation = [0, 0, 0]
floor_lamp[0].position = [2.70180594597286, 3.746552898002713, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
clock[0].position = [0.7539290557662999, 1.3757367159610654, 0.15]
clock[0].rotation = [0, 0, 0]
stool[0].position = [0.36354180134873604, 0.5005322495830629, 0.24]
stool[0].rotation = [0, 0, 0]
artwork[0].position = [2.6340171864506705, 2.3530054748937492, 0.25]
artwork[0].rotation = [0, 0, 0]
botanical_print_B[0].position = [2.900317686933045, 2.5896472238454247, 0.3]
botanical_print_B[0].rotation = [0, 0, 0]
botanical_print_A[0].position = [2.935723912177499, 1.9630224293083183, 0.3]
botanical_print_A[0].rotation = [0, 0, 0]
shelving_unit[0].position = [0.1714305851325634, 0.5510322100892417, 0.9]
shelving_unit[0].rotation = [0, 0, 0]
massage_table[0].position = [1.8676642750897738, 0.7607914702372214, 0.375]
massage_table[0].rotation = [0, 0, 0]
terry_towel[0].position = [1.4291277379112963, 1.9203358808463045, 0.015]
terry_towel[0].rotation = [0, 0, 0]
trolley_cart[0].position = [2.4529223636333257, 1.1236201182094083, 0.425]
trolley_cart[0].rotation = [0, 0, 0]
privacy_screen[0].position = [1.514982642901418, 2.798634681391512, 0.9]
privacy_screen[0].rotation = [0, 0, 0]
floor_lamp[0].position = [2.70180594597286, 3.746552898002713, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
clock[0].position = [0.7539290557662999, 1.3757367159610654, 0.15]
clock[0].rotation = [0, 0, 0]
stool[0].position = [0.36354180134873604, 0.5005322495830629, 0.24]
stool[0].rotation = [0, 0, 0]
artwork[0].position = [2.6340171864506705, 2.3530054748937492, 0.25]
artwork[0].rotation = [0, 0, 0]
botanical_print_B[0].position = [2.900317686933045, 2.5896472238454247, 0.3]
botanical_print_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed orientation/position references used only by the constraints.
table_layout_anchor = AssetInstance(position=[2.25, 2.35, 0.375], rotation=[0, 0, 0])
towel_layout_anchor = AssetInstance(position=[2.25, 2.35, 0.765], rotation=[0, 0, 0])
lamp_layout_anchor = AssetInstance(position=[0.20, 1.60, 0.825], rotation=[0, 0, radians(20)])
bottom_wall_orientation = AssetInstance(rotation=[0, 0, radians(90)])
top_wall_orientation = AssetInstance(rotation=[0, 0, radians(-90)])
left_wall_orientation = AssetInstance(rotation=[0, 0, 0])
right_wall_orientation = AssetInstance(rotation=[0, 0, radians(180)])

# Place the treatment table in the open center-right portion of the room.
# Its long axis runs north-south, leaving access along both long sides.
massage_table[0].position = [2.25, 2.35, 0.375]
massage_table[0].rotation = [0, 0, 0]

# Place the folding screen along the north wall. Its panel extends east-west,
# screening the head end of the treatment table without blocking circulation.
privacy_screen[0].position = [0.95, 3.775, 0.90]
privacy_screen[0].rotation = [0, 0, radians(-90)]

# Place the stool beside the west side of the table with a 5 cm edge gap.
stool[0].position = [1.66, 2.35, 0.24]
stool[0].rotation = [0, 0, 0]

# Put the towel flat on the middle of the massage table.
terry_towel[0].position = [2.25, 2.35, 0.765]
terry_towel[0].rotation = [0, 0, 0]

# Keep storage against opposite side walls and away from the treatment area.
shelving_unit[0].position = [0.175, 0.65, 0.90]
shelving_unit[0].rotation = [0, 0, 0]

trolley_cart[0].position = [3.275, 0.65, 0.425]
trolley_cart[0].rotation = [0, 0, radians(180)]

# Place the lamp in the clear section of the west wall, aimed toward the table.
floor_lamp[0].position = [0.20, 1.60, 0.825]
floor_lamp[0].rotation = [0, 0, radians(20)]

# Arrange the wall decorations above floor level. The three south-wall pieces
# are spaced across the wall, while the clock occupies the east wall.
botanical_print_A[0].position = [0.65, 0.015, 1.65]
botanical_print_A[0].rotation = [0, 0, radians(90)]

artwork[0].position = [1.75, 0.02, 1.55]
artwork[0].rotation = [0, 0, radians(90)]

botanical_print_B[0].position = [2.75, 0.015, 1.65]
botanical_print_B[0].rotation = [0, 0, radians(90)]

clock[0].position = [3.48, 2.80, 1.65]
clock[0].rotation = [0, 0, radians(180)]


# Preserve the requested table-to-screen relationship as the table is adjusted.
solver.distance_constraint(
    massage_table[0], privacy_screen[0],
    min_distance=None, max_distance=0.50, weight=10
)
solver.align_with(massage_table[0], table_layout_anchor)

# Keep the screen on the north wall and parallel to it.
solver.against_wall(privacy_screen[0], walls[2])
solver.align_with(privacy_screen[0], top_wall_orientation)

# Keep the stool immediately beside the massage table and facing it.
solver.distance_constraint(
    stool[0], massage_table[0],
    min_distance=None, max_distance=0.10, weight=10
)
solver.point_towards(stool[0], massage_table[0])

# The towel must remain supported by and aligned with the massage table.
solver.on_top_of(terry_towel[0], massage_table[0])
solver.distance_constraint(
    terry_towel[0], towel_layout_anchor,
    min_distance=0, max_distance=0.05, weight=10
)
solver.align_with(terry_towel[0], massage_table[0])

# Anchor the shelving unit to the west wall, facing into the room.
solver.against_wall(shelving_unit[0], walls[3])
solver.align_with(shelving_unit[0], left_wall_orientation)

# Anchor the trolley to the east wall, facing inward toward the treatment area.
solver.against_wall(trolley_cart[0], walls[1])
solver.point_towards(trolley_cart[0], massage_table[0])

# Keep the freestanding lamp in its clear wall-side location and aim it at
# the treatment table.
solver.distance_constraint(
    floor_lamp[0], lamp_layout_anchor,
    min_distance=0, max_distance=0.05, weight=10
)
solver.point_towards(floor_lamp[0], massage_table[0])

# Wall-mounted decorations remain flush with their respective walls and
# oriented toward the room interior.
solver.against_wall(botanical_print_A[0], walls[0])
solver.align_with(botanical_print_A[0], bottom_wall_orientation)

solver.against_wall(artwork[0], walls[0])
solver.align_with(artwork[0], bottom_wall_orientation)

solver.against_wall(botanical_print_B[0], walls[0])
solver.align_with(botanical_print_B[0], bottom_wall_orientation)

solver.against_wall(clock[0], walls[1])
solver.align_with(clock[0], right_wall_orientation)

solver.constraints = []
privacy_screen[0].position = [0.949999988079071, 3.774995803833008, 0.8999999761581421]
privacy_screen[0].rotation = [0, 0, -1.5708432270992143]
privacy_screen[0].optimize = 2
artwork[0].position = [1.75, 0.019967643544077873, 0.25]
artwork[0].rotation = [0, 0, 1.5707563383129561]
artwork[0].optimize = 2
botanical_print_A[0].position = [0.6499999761581421, 0.015038231387734413, 0.30000001192092896]
botanical_print_A[0].rotation = [0, 0, 1.5707563436244976]
botanical_print_A[0].optimize = 2
trolley_cart[0].position = [3.2750465869903564, 0.6499999761581421, 0.42500001192092896]
trolley_cart[0].rotation = [0, 0, 3.141552610596207]
trolley_cart[0].optimize = 2
shelving_unit[0].position = [0.17495818436145782, 0.6499999761581421, 0.8999999761581421]
shelving_unit[0].rotation = [0, 0, -4.003419434185002e-05]
shelving_unit[0].optimize = 2
clock[0].position = [3.480017900466919, 2.799999952316284, 0.15000000596046448]
clock[0].rotation = [0, 0, 3.1415526688283744]
clock[0].optimize = 2
botanical_print_B[0].position = [2.75, 0.015038231387734413, 0.30000001192092896]
botanical_print_B[0].rotation = [0, 0, 1.5707563436244976]
botanical_print_B[0].optimize = 2
massage_table[0].position = [2.25, 2.3499999046325684, 0.375]
massage_table[0].rotation = [0, 0, 0.02827433441159227]
massage_table[0].optimize = 2
floor_lamp[0].position = [0.22527551651000977, 1.600000023841858, 0.824999988079071]
floor_lamp[0].rotation = [0, 0, 0.35849063180849555]
floor_lamp[0].optimize = 2
terry_towel[0].position = [2.25, 2.3499999046325684, 0.7649999856948853]
terry_towel[0].rotation = [0, 0, 0.028286518345377282]
terry_towel[0].optimize = 2
stool[0].position = [1.659999966621399, 2.3499999046325684, 0.23999999463558197]
stool[0].rotation = [0, 0, 0.00942477746072377]
stool[0].optimize = 2

