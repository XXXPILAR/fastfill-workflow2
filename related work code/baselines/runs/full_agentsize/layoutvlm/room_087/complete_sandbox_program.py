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
    Wall(corner1=[0.50, 0.50, 0.00], corner2=[0.50, 0.00, 0.00]),
    Wall(corner1=[0.50, 0.00, 0.00], corner2=[3.26, 0.00, 0.00]),
    Wall(corner1=[3.26, 0.00, 0.00], corner2=[3.26, 5.26, 0.00]),
    Wall(corner1=[3.26, 5.26, 0.00], corner2=[0.00, 5.26, 0.00]),
    Wall(corner1=[0.00, 5.26, 0.00], corner2=[0.00, 0.50, 0.00]),
    Wall(corner1=[0.00, 0.50, 0.00], corner2=[0.50, 0.50, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
cabinet_A = Assets(description="cabinet", size=[0.60, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
food_A = Assets(description="food", size=[0.12, 0.18, 0.08], placements=[AssetInstance() for _ in range(1)])
pan = Assets(description="pan", size=[0.28, 0.45, 0.08], placements=[AssetInstance() for _ in range(1)])
food_B = Assets(description="food", size=[0.15, 0.22, 0.10], placements=[AssetInstance() for _ in range(1)])
cup_A = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
bottle_A = Assets(description="bottle", size=[0.08, 0.08, 0.28], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="bottle", size=[0.07, 0.07, 0.24], placements=[AssetInstance() for _ in range(1)])
lamp = Assets(description="lamp", size=[0.15, 0.30, 0.35], placements=[AssetInstance() for _ in range(1)])
oven = Assets(description="oven", size=[0.60, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
can = Assets(description="can", size=[0.07, 0.07, 0.12], placements=[AssetInstance() for _ in range(1)])
shelf = Assets(description="shelf", size=[0.35, 0.80, 1.80], placements=[AssetInstance() for _ in range(1)])
bottle_C = Assets(description="bottle", size=[0.08, 0.08, 0.30], placements=[AssetInstance() for _ in range(1)])
refrigerator = Assets(description="refrigerator", size=[0.75, 0.75, 1.90], placements=[AssetInstance() for _ in range(1)])
microwave = Assets(description="microwave", size=[0.40, 0.50, 0.30], placements=[AssetInstance() for _ in range(1)])
bottle_D = Assets(description="bottle", size=[0.07, 0.07, 0.25], placements=[AssetInstance() for _ in range(1)])
book = Assets(description="book", size=[0.04, 0.20, 0.28], placements=[AssetInstance() for _ in range(1)])
cup_B = Assets(description="cup", size=[0.09, 0.09, 0.10], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.60, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
cabinet_C = Assets(description="cabinet", size=[0.60, 0.70, 0.90], placements=[AssetInstance() for _ in range(1)])
bottle_E = Assets(description="bottle", size=[0.09, 0.09, 0.32], placements=[AssetInstance() for _ in range(1)])
faucet = Assets(description="faucet", size=[0.25, 0.20, 0.35], placements=[AssetInstance() for _ in range(1)])

cabinet_A[0].instance_id = 'cabinet_A_0'
food_A[0].instance_id = 'food_A_0'
pan[0].instance_id = 'pan_0'
food_B[0].instance_id = 'food_B_0'
cup_A[0].instance_id = 'cup_A_0'
bottle_A[0].instance_id = 'bottle_A_0'
bottle_B[0].instance_id = 'bottle_B_0'
lamp[0].instance_id = 'lamp_0'
oven[0].instance_id = 'oven_0'
can[0].instance_id = 'can_0'
shelf[0].instance_id = 'shelf_0'
bottle_C[0].instance_id = 'bottle_C_0'
refrigerator[0].instance_id = 'refrigerator_0'
microwave[0].instance_id = 'microwave_0'
bottle_D[0].instance_id = 'bottle_D_0'
book[0].instance_id = 'book_0'
cup_B[0].instance_id = 'cup_B_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
cabinet_C[0].instance_id = 'cabinet_C_0'
bottle_E[0].instance_id = 'bottle_E_0'
faucet[0].instance_id = 'faucet_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

cabinet_A[0].position = [1.0326603578378166, 4.683080253071673, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
food_A[0].position = [0.4261422958216228, 3.4618937050252807, 0.04]
food_A[0].rotation = [0, 0, 0]
pan[0].position = [0.550507745863008, 1.6794974355041816, 0.04]
pan[0].rotation = [0, 0, 0]
food_B[0].position = [1.9751844534374976, 2.853690962304324, 0.05]
food_B[0].rotation = [0, 0, 0]
cup_A[0].position = [2.7000229492008305, 1.707634208015175, 0.055]
cup_A[0].rotation = [0, 0, 0]
bottle_A[0].position = [2.687300494554344, 4.124463913314613, 0.14]
bottle_A[0].rotation = [0, 0, 0]
bottle_B[0].position = [0.31548654231386103, 0.5689915267827892, 0.12]
bottle_B[0].rotation = [0, 0, 0]
lamp[0].position = [2.3233225935694874, 4.255064976726728, 0.175]
lamp[0].rotation = [0, 0, 0]
oven[0].position = [0.6309739022696379, 1.505029918571521, 0.45]
oven[0].rotation = [0, 0, 0]
can[0].position = [0.3375433880740263, 4.634475446290556, 0.06]
can[0].rotation = [0, 0, 0]
shelf[0].position = [0.6719150834143455, 5.0524351739547795, 0.9]
shelf[0].rotation = [0, 0, 0]
bottle_C[0].position = [0.36769835428976916, 3.4880066112542876, 0.15]
bottle_C[0].rotation = [0, 0, 0]
refrigerator[0].position = [1.8874688724103605, 4.4680991037669315, 0.95]
refrigerator[0].rotation = [0, 0, 0]
microwave[0].position = [2.533911633509153, 2.9130560633708225, 0.15]
microwave[0].rotation = [0, 0, 0]
bottle_D[0].position = [1.6033134905263955, 3.3041069749701206, 0.125]
bottle_D[0].rotation = [0, 0, 0]
book[0].position = [0.2046243818268285, 2.5457017393253696, 0.14]
book[0].rotation = [0, 0, 0]
cup_B[0].position = [2.1326585861118934, 1.8546147784889155, 0.05]
cup_B[0].rotation = [0, 0, 0]
cabinet_B[0].position = [2.179454016156042, 0.22139556603661933, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
cabinet_C[0].position = [2.079297440692232, 3.4138703896963665, 0.45]
cabinet_C[0].rotation = [0, 0, 0]
bottle_E[0].position = [0.7285831264124754, 2.2613539130336946, 0.16]
bottle_E[0].rotation = [0, 0, 0]
faucet[0].position = [2.638208691136194, 1.5218249017866197, 0.175]
faucet[0].rotation = [0, 0, 0]
cabinet_A[0].position = [1.0326603578378166, 4.683080253071673, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
food_A[0].position = [0.4261422958216228, 3.4618937050252807, 0.04]
food_A[0].rotation = [0, 0, 0]
pan[0].position = [0.550507745863008, 1.6794974355041816, 0.04]
pan[0].rotation = [0, 0, 0]
food_B[0].position = [1.9751844534374976, 2.853690962304324, 0.05]
food_B[0].rotation = [0, 0, 0]
cup_A[0].position = [2.7000229492008305, 1.707634208015175, 0.055]
cup_A[0].rotation = [0, 0, 0]
bottle_A[0].position = [2.687300494554344, 4.124463913314613, 0.14]
bottle_A[0].rotation = [0, 0, 0]
bottle_B[0].position = [0.31548654231386103, 0.5689915267827892, 0.12]
bottle_B[0].rotation = [0, 0, 0]
lamp[0].position = [2.3233225935694874, 4.255064976726728, 0.175]
lamp[0].rotation = [0, 0, 0]
oven[0].position = [0.6309739022696379, 1.505029918571521, 0.45]
oven[0].rotation = [0, 0, 0]
can[0].position = [0.3375433880740263, 4.634475446290556, 0.06]
can[0].rotation = [0, 0, 0]
shelf[0].position = [0.6719150834143455, 5.0524351739547795, 0.9]
shelf[0].rotation = [0, 0, 0]
bottle_C[0].position = [0.36769835428976916, 3.4880066112542876, 0.15]
bottle_C[0].rotation = [0, 0, 0]
refrigerator[0].position = [1.8874688724103605, 4.4680991037669315, 0.95]
refrigerator[0].rotation = [0, 0, 0]
microwave[0].position = [2.533911633509153, 2.9130560633708225, 0.15]
microwave[0].rotation = [0, 0, 0]
bottle_D[0].position = [1.6033134905263955, 3.3041069749701206, 0.125]
bottle_D[0].rotation = [0, 0, 0]
book[0].position = [0.2046243818268285, 2.5457017393253696, 0.14]
book[0].rotation = [0, 0, 0]
cup_B[0].position = [2.1326585861118934, 1.8546147784889155, 0.05]
cup_B[0].rotation = [0, 0, 0]
cabinet_B[0].position = [2.179454016156042, 0.22139556603661933, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
cabinet_C[0].position = [2.079297440692232, 3.4138703896963665, 0.45]
cabinet_C[0].rotation = [0, 0, 0]
bottle_E[0].position = [0.7285831264124754, 2.2613539130336946, 0.16]
bottle_E[0].rotation = [0, 0, 0]
faucet[0].position = [2.638208691136194, 1.5218249017866197, 0.175]
faucet[0].rotation = [0, 0, 0]

solver.constraints = []

# The uninterrupted north wall is used for the main kitchen run.  The run is
# ordered west-to-east as cabinet_A, oven, cabinet_B, and cabinet_C, placing
# the oven between the two specified cabinets while keeping all openings clear.
cabinet_A[0].position = [0.40, 4.96, 0.45]
cabinet_A[0].rotation = [0, 0, radians(-90)]

oven[0].position = [1.10, 4.96, 0.45]
oven[0].rotation = [0, 0, radians(-90)]

cabinet_B[0].position = [1.80, 4.96, 0.45]
cabinet_B[0].rotation = [0, 0, radians(-90)]

cabinet_C[0].position = [2.55, 4.96, 0.45]
cabinet_C[0].rotation = [0, 0, radians(-90)]

# The shelf and refrigerator occupy the clear upper section of the west wall.
# Their bounding boxes have a 0.10 m edge-to-edge gap: the center spacing is
# 0.875 m because their half-widths along the wall are 0.40 m and 0.375 m.
shelf[0].position = [0.175, 2.65, 0.90]
shelf[0].rotation = [0, 0, radians(0)]

refrigerator[0].position = [0.375, 3.525, 0.95]
refrigerator[0].rotation = [0, 0, radians(0)]

# Countertop objects are distributed across the work surfaces without overlap.
food_A[0].position = [0.18, 4.88, 0.94]
food_A[0].rotation = [0, 0, radians(-90)]

cup_A[0].position = [0.43, 4.88, 0.955]
cup_A[0].rotation = [0, 0, radians(-90)]

bottle_A[0].position = [0.65, 4.88, 1.04]
bottle_A[0].rotation = [0, 0, radians(-90)]

pan[0].position = [1.10, 4.95, 0.94]
pan[0].rotation = [0, 0, radians(-90)]

faucet[0].position = [1.52, 4.95, 1.075]
faucet[0].rotation = [0, 0, radians(-90)]

food_B[0].position = [1.82, 4.82, 0.95]
food_B[0].rotation = [0, 0, radians(-90)]

bottle_B[0].position = [2.06, 4.84, 1.02]
bottle_B[0].rotation = [0, 0, radians(-90)]

can[0].position = [1.90, 5.15, 0.96]
can[0].rotation = [0, 0, radians(-90)]

microwave[0].position = [2.50, 4.97, 1.05]
microwave[0].rotation = [0, 0, radians(-90)]

# Tall surfaces provide additional storage without consuming circulation space.
lamp[0].position = [0.18, 2.50, 1.975]
lamp[0].rotation = [0, 0, radians(0)]

book[0].position = [0.18, 2.80, 1.94]
book[0].rotation = [0, 0, radians(0)]

bottle_E[0].position = [0.18, 3.00, 2.06]
bottle_E[0].rotation = [0, 0, radians(0)]

bottle_C[0].position = [0.20, 3.35, 2.05]
bottle_C[0].rotation = [0, 0, radians(0)]

bottle_D[0].position = [0.52, 3.40, 2.025]
bottle_D[0].rotation = [0, 0, radians(0)]

cup_B[0].position = [0.36, 3.72, 2.00]
cup_B[0].rotation = [0, 0, radians(0)]

room_center = AssetInstance(position=[1.63, 2.63, 0.45])

# Preserve the required cabinet–oven–cabinet ordering before applying the wall
# constraints. Adjacent center distances equal the sum of their half-widths.
solver.distance_constraint(oven[0], cabinet_A[0], 0.70, 0.70, weight=10)
solver.distance_constraint(oven[0], cabinet_B[0], 0.70, 0.70, weight=10)
solver.distance_constraint(cabinet_C[0], cabinet_B[0], 0.75, 0.75, weight=10)

solver.against_wall(cabinet_A[0], walls[3])
solver.against_wall(oven[0], walls[3])
solver.against_wall(cabinet_B[0], walls[3])
solver.against_wall(cabinet_C[0], walls[3])

# All four appliance/cabinet fronts face inward, away from the north wall.
solver.point_towards(cabinet_A[0], room_center)
solver.point_towards(oven[0], room_center)
solver.point_towards(cabinet_B[0], room_center)
solver.point_towards(cabinet_C[0], room_center)

# Enforce proximity as an edge-to-edge clearance of no more than 0.10 m.
# The lower bound prevents overlap; the upper bound permits up to 0.10 m gap.
solver.distance_constraint(refrigerator[0], shelf[0], 0.775, 0.875, weight=10)
solver.against_wall(shelf[0], walls[4])
solver.against_wall(refrigerator[0], walls[4])
solver.point_towards(shelf[0], room_center)
solver.point_towards(refrigerator[0], room_center)

# Objects on cabinet_A.
solver.on_top_of(food_A[0], cabinet_A[0])
solver.distance_constraint(food_A[0], cabinet_A[0], 0.50, 0.60, weight=10)
solver.align_with(food_A[0], cabinet_A[0])

solver.on_top_of(cup_A[0], cabinet_A[0])
solver.distance_constraint(cup_A[0], cabinet_A[0], 0.48, 0.56, weight=10)
solver.align_with(cup_A[0], cabinet_A[0])

solver.on_top_of(bottle_A[0], cabinet_A[0])
solver.distance_constraint(bottle_A[0], cabinet_A[0], 0.60, 0.70, weight=10)
solver.align_with(bottle_A[0], cabinet_A[0])

# The pan sits on the oven's upper cooking surface.
solver.on_top_of(pan[0], oven[0])
solver.distance_constraint(pan[0], oven[0], 0.45, 0.55, weight=10)
solver.align_with(pan[0], oven[0])

# Objects on cabinet_B.
solver.on_top_of(faucet[0], cabinet_B[0])
solver.distance_constraint(faucet[0], cabinet_B[0], 0.64, 0.73, weight=10)
solver.align_with(faucet[0], cabinet_B[0])

solver.on_top_of(food_B[0], cabinet_B[0])
solver.distance_constraint(food_B[0], cabinet_B[0], 0.48, 0.57, weight=10)
solver.align_with(food_B[0], cabinet_B[0])

solver.on_top_of(bottle_B[0], cabinet_B[0])
solver.distance_constraint(bottle_B[0], cabinet_B[0], 0.60, 0.69, weight=10)
solver.align_with(bottle_B[0], cabinet_B[0])

solver.on_top_of(can[0], cabinet_B[0])
solver.distance_constraint(can[0], cabinet_B[0], 0.51, 0.61, weight=10)
solver.align_with(can[0], cabinet_B[0])

# The microwave is centered on the final cabinet.
solver.on_top_of(microwave[0], cabinet_C[0])
solver.distance_constraint(microwave[0], cabinet_C[0], 0.57, 0.65, weight=10)
solver.align_with(microwave[0], cabinet_C[0])

# Objects on the shelf.
solver.on_top_of(lamp[0], shelf[0])
solver.distance_constraint(lamp[0], shelf[0], 1.02, 1.14, weight=10)
solver.align_with(lamp[0], shelf[0])

solver.on_top_of(book[0], shelf[0])
solver.distance_constraint(book[0], shelf[0], 1.00, 1.11, weight=10)
solver.align_with(book[0], shelf[0])

solver.on_top_of(bottle_E[0], shelf[0])
solver.distance_constraint(bottle_E[0], shelf[0], 1.16, 1.27, weight=10)
solver.align_with(bottle_E[0], shelf[0])

# Objects on the refrigerator are spaced across its top.
solver.on_top_of(bottle_C[0], refrigerator[0])
solver.distance_constraint(bottle_C[0], refrigerator[0], 1.06, 1.17, weight=10)
solver.align_with(bottle_C[0], refrigerator[0])

solver.on_top_of(bottle_D[0], refrigerator[0])
solver.distance_constraint(bottle_D[0], refrigerator[0], 1.03, 1.14, weight=10)
solver.align_with(bottle_D[0], refrigerator[0])

solver.on_top_of(cup_B[0], refrigerator[0])
solver.distance_constraint(cup_B[0], refrigerator[0], 1.00, 1.08, weight=10)
solver.align_with(cup_B[0], refrigerator[0])

solver.constraints = []
bottle_E[0].position = [0.18000000715255737, 3.0, 1.959999918937683]
bottle_E[0].rotation = [0, 0, 4.1250867467494e-08]
bottle_E[0].optimize = 2
cup_A[0].position = [0.7119076251983643, 4.473989963531494, 0.9549999833106995]
cup_A[0].rotation = [0, 0, -2.0279418358018377e-08]
cup_A[0].optimize = 2
refrigerator[0].position = [0.3750523030757904, 3.4716362953186035, 0.949999988079071]
refrigerator[0].rotation = [0, 0, 4.379502153613989e-08]
refrigerator[0].optimize = 2
faucet[0].position = [1.399999976158142, 5.135119438171387, 1.0749999284744263]
faucet[0].rotation = [0, 0, -1.5707962832078495]
faucet[0].optimize = 2
pan[0].position = [0.7887808680534363, 4.66011905670166, 0.9399999976158142]
pan[0].rotation = [0, 0, -1.570796282908362]
pan[0].optimize = 2
cabinet_B[0].position = [1.7999999523162842, 4.960119247436523, 0.44999998807907104]
cabinet_B[0].rotation = [0, 0, -1.57079628332816]
cabinet_B[0].optimize = 2
bottle_D[0].position = [0.5199999809265137, 3.4000000953674316, 2.0250000953674316]
bottle_D[0].rotation = [0, 0, 4.34313063658721e-08]
bottle_D[0].optimize = 2
food_A[0].position = [0.11191526055335999, 4.459839344024658, 0.9399999976158142]
food_A[0].rotation = [0, 0, -2.0279418358018377e-08]
food_A[0].optimize = 2
can[0].position = [2.200000047683716, 5.225119590759277, 0.9599999785423279]
can[0].rotation = [0, 0, -1.5707962832078495]
can[0].optimize = 2
food_B[0].position = [2.2000012397766113, 4.66011905670166, 0.949999988079071]
food_B[0].rotation = [0, 0, -1.5707962832078495]
food_B[0].optimize = 2
book[0].position = [0.019999980926513672, 3.0500001907348633, 1.9399999380111694]
book[0].rotation = [0, 0, 4.1250867467494e-08]
book[0].optimize = 2
bottle_B[0].position = [2.200000047683716, 4.66011905670166, 1.0199999809265137]
bottle_B[0].rotation = [0, 0, -1.5707962832078495]
bottle_B[0].optimize = 2
lamp[0].position = [0.18000000715255737, 2.5, 1.9749999046325684]
lamp[0].rotation = [0, 0, 4.1250867467494e-08]
lamp[0].optimize = 2
bottle_C[0].position = [0.20000000298023224, 3.3499999046325684, 2.049999952316284]
bottle_C[0].rotation = [0, 0, 4.34313063658721e-08]
bottle_C[0].optimize = 2
cup_B[0].position = [0.04499998688697815, 3.8466362953186035, 1.9499999284744263]
cup_B[0].rotation = [0, 0, 4.34313063658721e-08]
cup_B[0].optimize = 2
bottle_A[0].position = [0.7119152545928955, 4.459839344024658, 1.0399999618530273]
bottle_A[0].rotation = [0, 0, -2.0279418358018377e-08]
bottle_A[0].optimize = 2
cabinet_A[0].position = [0.41191527247428894, 4.85983943939209, 0.44999998807907104]
cabinet_A[0].rotation = [0, 0, -1.841040881081692e-08]
cabinet_A[0].optimize = 2
microwave[0].position = [2.200000047683716, 5.06011962890625, 1.0499999523162842]
microwave[0].rotation = [0, 0, -1.570796283369015]
microwave[0].optimize = 2
cabinet_C[0].position = [2.549999952316284, 4.960118770599365, 0.44999998807907104]
cabinet_C[0].rotation = [0, 0, -1.5707962830265068]
cabinet_C[0].optimize = 2
oven[0].position = [1.0887808799743652, 4.960119247436523, 0.44999998807907104]
oven[0].rotation = [0, 0, -1.5707962825525341]
oven[0].optimize = 2
shelf[0].position = [0.17499996721744537, 2.6500000953674316, 0.8999999761581421]
shelf[0].rotation = [0, 0, 4.1197798498765826e-08]
shelf[0].optimize = 2

