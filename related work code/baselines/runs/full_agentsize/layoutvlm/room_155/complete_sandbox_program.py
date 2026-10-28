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
sofa = Assets(description="extra-large modern sectional sofa in soft neutral fabric with chaise lounge", size=[2.20, 3.60, 0.85], placements=[AssetInstance() for _ in range(1)])
floor_lamp_A = Assets(description="tall modern arc floor lamp with adjustable head", size=[1.20, 0.50, 2.10], placements=[AssetInstance() for _ in range(1)])
plant_stand_A = Assets(description="decorative wooden plant stand holding large potted plant", size=[0.75, 0.75, 1.65], placements=[AssetInstance() for _ in range(1)])
media_console = Assets(description="long low modern media console with matte finish and storage cabinets", size=[0.48, 2.40, 0.62], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="large rectangular wooden coffee table with glass top and lower storage shelf", size=[0.85, 1.50, 0.45], placements=[AssetInstance() for _ in range(1)])
bookshelf_A = Assets(description="extra tall open bookshelf with wooden frame and multiple compartments", size=[0.38, 1.40, 2.40], placements=[AssetInstance() for _ in range(1)])
floor_lamp_B = Assets(description="tall modern arc floor lamp with adjustable head", size=[1.20, 0.50, 2.10], placements=[AssetInstance() for _ in range(1)])
plant_stand_B = Assets(description="decorative wooden plant stand holding large potted plant", size=[0.75, 0.75, 1.65], placements=[AssetInstance() for _ in range(1)])
bookshelf_B = Assets(description="extra tall open bookshelf with wooden frame and multiple compartments", size=[0.38, 1.40, 2.40], placements=[AssetInstance() for _ in range(1)])
accent_cabinet = Assets(description="medium-height accent cabinet with doors and drawers, wooden finish", size=[0.45, 1.20, 1.05], placements=[AssetInstance() for _ in range(1)])

sofa[0].instance_id = 'sofa_0'
floor_lamp_A[0].instance_id = 'floor_lamp_A_0'
plant_stand_A[0].instance_id = 'plant_stand_A_0'
media_console[0].instance_id = 'media_console_0'
coffee_table[0].instance_id = 'coffee_table_0'
bookshelf_A[0].instance_id = 'bookshelf_A_0'
floor_lamp_B[0].instance_id = 'floor_lamp_B_0'
plant_stand_B[0].instance_id = 'plant_stand_B_0'
bookshelf_B[0].instance_id = 'bookshelf_B_0'
accent_cabinet[0].instance_id = 'accent_cabinet_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

sofa[0].position = [3.6820539440697586, 6.024341690303864, 0.425]
sofa[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [3.466042704812023, 6.337177638674872, 1.05]
floor_lamp_A[0].rotation = [0, 0, 0]
plant_stand_A[0].position = [3.1140976726009635, 3.995837211946541, 0.825]
plant_stand_A[0].rotation = [0, 0, 0]
media_console[0].position = [5.27737880097699, 0.046534830492512724, 0.31]
media_console[0].rotation = [0, 0, 0]
coffee_table[0].position = [4.706406294086676, 0.3444796090248259, 0.225]
coffee_table[0].rotation = [0, 0, 0]
bookshelf_A[0].position = [0.28195523266480405, 0.9379945617801505, 1.2]
bookshelf_A[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [3.9684781683742387, 2.8400858151178756, 1.05]
floor_lamp_B[0].rotation = [0, 0, 0]
plant_stand_B[0].position = [3.65574592328074, 2.3833342080400075, 0.825]
plant_stand_B[0].rotation = [0, 0, 0]
bookshelf_B[0].position = [5.603898264000378, 3.4518418051417106, 1.2]
bookshelf_B[0].rotation = [0, 0, 0]
accent_cabinet[0].position = [4.415908483540481, 3.8247039155271256, 0.525]
accent_cabinet[0].rotation = [0, 0, 0]
sofa[0].position = [3.6820539440697586, 6.024341690303864, 0.425]
sofa[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [3.466042704812023, 6.337177638674872, 1.05]
floor_lamp_A[0].rotation = [0, 0, 0]
plant_stand_A[0].position = [3.1140976726009635, 3.995837211946541, 0.825]
plant_stand_A[0].rotation = [0, 0, 0]
media_console[0].position = [5.27737880097699, 0.046534830492512724, 0.31]
media_console[0].rotation = [0, 0, 0]
coffee_table[0].position = [4.706406294086676, 0.3444796090248259, 0.225]
coffee_table[0].rotation = [0, 0, 0]
bookshelf_A[0].position = [0.28195523266480405, 0.9379945617801505, 1.2]
bookshelf_A[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [3.9684781683742387, 2.8400858151178756, 1.05]
floor_lamp_B[0].rotation = [0, 0, 0]
plant_stand_B[0].position = [3.65574592328074, 2.3833342080400075, 0.825]
plant_stand_B[0].rotation = [0, 0, 0]
bookshelf_B[0].position = [5.603898264000378, 3.4518418051417106, 1.2]
bookshelf_B[0].rotation = [0, 0, 0]
accent_cabinet[0].position = [4.415908483540481, 3.8247039155271256, 0.525]
accent_cabinet[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the sectional against the left wall, facing across the room.
# The two floor lamps flank it along the y-axis, making the sofa spatially
# between floor_lamp_A and floor_lamp_B.
sofa[0].position = [1.10, 3.50, 0.425]
sofa[0].rotation = [0, 0, radians(0)]

floor_lamp_A[0].position = [0.60, 1.35, 1.05]
floor_lamp_A[0].rotation = [0, 0, radians(0)]

floor_lamp_B[0].position = [0.60, 5.65, 1.05]
floor_lamp_B[0].rotation = [0, 0, radians(0)]

# Put the main bookshelf directly opposite the sofa so the sofa can face it.
bookshelf_A[0].position = [5.81, 3.50, 1.20]
bookshelf_A[0].rotation = [0, 0, radians(180)]

# The coffee table sits centrally in the clear space between the sofa and
# bookshelf, with circulation gaps on both sides.
coffee_table[0].position = [3.30, 3.50, 0.225]
coffee_table[0].rotation = [0, 0, radians(0)]

# Use the bottom wall for the low media console. Rotating it 90 degrees puts
# its long dimension along the wall while its front faces into the room.
media_console[0].position = [3.00, 0.24, 0.31]
media_console[0].rotation = [0, 0, radians(90)]

# Plants occupy the two bottom corners without obstructing the media console.
plant_stand_A[0].position = [0.60, 0.375, 0.825]
plant_stand_A[0].rotation = [0, 0, radians(45)]

plant_stand_B[0].position = [5.40, 0.375, 0.825]
plant_stand_B[0].rotation = [0, 0, radians(135)]

# The second bookshelf and accent cabinet use separate portions of the top
# wall and face inward, leaving the top-right area open for circulation.
bookshelf_B[0].position = [1.00, 6.81, 1.20]
bookshelf_B[0].rotation = [0, 0, radians(-90)]

accent_cabinet[0].position = [3.00, 6.775, 0.525]
accent_cabinet[0].rotation = [0, 0, radians(-90)]


# Fixed anchors preserve the deliberately non-overlapping furniture zones.
sofa_anchor = AssetInstance(position=[1.10, 3.50, 0.425])
floor_lamp_A_anchor = AssetInstance(position=[0.60, 1.35, 1.05])
floor_lamp_B_anchor = AssetInstance(position=[0.60, 5.65, 1.05])
bookshelf_A_anchor = AssetInstance(position=[5.81, 3.50, 1.20])
coffee_table_anchor = AssetInstance(position=[3.30, 3.50, 0.225])
media_console_anchor = AssetInstance(position=[3.00, 0.24, 0.31])
plant_stand_A_anchor = AssetInstance(position=[0.60, 0.375, 0.825])
plant_stand_B_anchor = AssetInstance(position=[5.40, 0.375, 0.825])
bookshelf_B_anchor = AssetInstance(position=[1.00, 6.81, 1.20])
accent_cabinet_anchor = AssetInstance(position=[3.00, 6.775, 0.525])

# Directional reference points used to keep wall furniture facing inward.
media_console_inward = AssetInstance(position=[3.00, 2.00, 0.31])
bookshelf_B_inward = AssetInstance(position=[1.00, 5.00, 1.20])
accent_cabinet_inward = AssetInstance(position=[3.00, 5.00, 0.525])
plant_stand_A_inward = AssetInstance(position=[2.00, 1.80, 0.825])
plant_stand_B_inward = AssetInstance(position=[4.00, 1.80, 0.825])

# High-priority positional anchors maintain the intended clearances and encode
# the required sofa-between-lamps arrangement.
solver.distance_constraint(sofa[0], sofa_anchor, 0, 0, weight=10)
solver.distance_constraint(floor_lamp_A[0], floor_lamp_A_anchor, 0, 0, weight=10)
solver.distance_constraint(floor_lamp_B[0], floor_lamp_B_anchor, 0, 0, weight=10)
solver.distance_constraint(bookshelf_A[0], bookshelf_A_anchor, 0, 0, weight=10)
solver.distance_constraint(coffee_table[0], coffee_table_anchor, 0, 0, weight=10)
solver.distance_constraint(media_console[0], media_console_anchor, 0, 0, weight=10)
solver.distance_constraint(plant_stand_A[0], plant_stand_A_anchor, 0, 0, weight=10)
solver.distance_constraint(plant_stand_B[0], plant_stand_B_anchor, 0, 0, weight=10)
solver.distance_constraint(bookshelf_B[0], bookshelf_B_anchor, 0, 0, weight=10)
solver.distance_constraint(accent_cabinet[0], accent_cabinet_anchor, 0, 0, weight=10)

# Wall relationships preserve the room-edge organization.
solver.against_wall(sofa[0], walls[2])
solver.against_wall(floor_lamp_A[0], walls[2])
solver.against_wall(floor_lamp_B[0], walls[2])
solver.against_wall(bookshelf_A[0], walls[0])
solver.against_wall(media_console[0], walls[3])
solver.against_wall(plant_stand_A[0], walls[3])
solver.against_wall(plant_stand_B[0], walls[3])
solver.against_wall(bookshelf_B[0], walls[1])
solver.against_wall(accent_cabinet[0], walls[1])

# Keep the main seating relationship explicit: the sofa faces bookshelf_A.
solver.point_towards(sofa[0], bookshelf_A[0])
solver.point_towards(bookshelf_A[0], sofa[0])

# Both lamps direct their heads toward the seating area while continuing to
# flank the sofa from opposite ends.
solver.point_towards(floor_lamp_A[0], sofa[0])
solver.point_towards(floor_lamp_B[0], sofa[0])

# Keep the coffee table parallel to the sofa and visually centered in the
# seating arrangement.
solver.align_with(coffee_table[0], sofa[0])
solver.distance_constraint(coffee_table[0], sofa[0], 2.15, 2.30, weight=5)
solver.distance_constraint(coffee_table[0], bookshelf_A[0], 2.40, 2.60, weight=5)

# Remaining perimeter pieces face toward usable room space.
solver.point_towards(media_console[0], media_console_inward)
solver.point_towards(plant_stand_A[0], plant_stand_A_inward)
solver.point_towards(plant_stand_B[0], plant_stand_B_inward)
solver.point_towards(bookshelf_B[0], bookshelf_B_inward)
solver.point_towards(accent_cabinet[0], accent_cabinet_inward)

solver.constraints = []
coffee_table[0].position = [3.3580520153045654, 3.5, 0.22499999403953552]
coffee_table[0].rotation = [0, 0, 2.854508522111751e-08]
coffee_table[0].optimize = 2
media_console[0].position = [3.0, 0.23999997973442078, 0.3100000023841858]
media_console[0].rotation = [0, 0, 1.5707963531455962]
media_console[0].optimize = 2
sofa[0].position = [1.100000023841858, 3.5, 0.42500001192092896]
sofa[0].rotation = [0, 0, 4.017491386741299e-08]
sofa[0].optimize = 2
bookshelf_B[0].position = [1.0, 6.809999942779541, 1.2000000476837158]
bookshelf_B[0].rotation = [0, 0, -1.5707962830707265]
bookshelf_B[0].optimize = 2
plant_stand_B[0].position = [5.400000095367432, 0.3749999701976776, 0.824999988079071]
plant_stand_B[0].rotation = [0, 0, 1.5707963528603448]
plant_stand_B[0].optimize = 2
bookshelf_A[0].position = [5.809999942779541, 3.5, 1.2000000476837158]
bookshelf_A[0].rotation = [0, 0, -3.1415926098563904]
bookshelf_A[0].optimize = 2
plant_stand_A[0].position = [0.6000000238418579, 0.3750000298023224, 0.824999988079071]
plant_stand_A[0].rotation = [0, 0, 1.5707963815051]
plant_stand_A[0].optimize = 2
accent_cabinet[0].position = [3.0, 6.77500057220459, 0.5249999761581421]
accent_cabinet[0].rotation = [0, 0, -1.570796283096463]
accent_cabinet[0].optimize = 2
floor_lamp_A[0].position = [0.6000001430511475, 1.350000023841858, 1.0499999523162842]
floor_lamp_A[0].rotation = [0, 0, 4.3704645136196e-08]
floor_lamp_A[0].optimize = 2
floor_lamp_B[0].position = [0.6000001430511475, 5.650000095367432, 1.0499999523162842]
floor_lamp_B[0].rotation = [0, 0, 4.370463897489084e-08]
floor_lamp_B[0].optimize = 2

