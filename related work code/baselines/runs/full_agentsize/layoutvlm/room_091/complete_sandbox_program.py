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
    Wall(corner1=[4.75, 0.00, 0.00], corner2=[4.75, 4.25, 0.00]),
    Wall(corner1=[4.75, 4.25, 0.00], corner2=[0.00, 4.25, 0.00]),
    Wall(corner1=[0.00, 4.25, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.75, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
oven = Assets(description="oven", size=[0.60, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
can_A = Assets(description="can", size=[0.07, 0.07, 0.12], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="shelf", size=[0.30, 1.20, 0.04], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="lamp", size=[0.30, 0.30, 0.25], placements=[AssetInstance() for _ in range(1)])
can_B = Assets(description="can", size=[0.07, 0.07, 0.12], placements=[AssetInstance() for _ in range(1)])
bottle_A = Assets(description="bottle", size=[0.08, 0.08, 0.28], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.30, 0.30, 0.25], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.40, 1.50, 1.80], placements=[AssetInstance() for _ in range(1)])
dishwasher = Assets(description="dishwasher", size=[0.60, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
can_C = Assets(description="can", size=[0.07, 0.07, 0.12], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="bottle", size=[0.08, 0.08, 0.28], placements=[AssetInstance() for _ in range(1)])
lamp_C = Assets(description="lamp", size=[0.30, 0.30, 0.25], placements=[AssetInstance() for _ in range(1)])
food_A = Assets(description="food", size=[0.08, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
food_B = Assets(description="food", size=[0.08, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
food_C = Assets(description="food", size=[0.08, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])

oven[0].instance_id = 'oven_0'
can_A[0].instance_id = 'can_A_0'
shelf_A[0].instance_id = 'shelf_A_0'
lamp_A[0].instance_id = 'lamp_A_0'
can_B[0].instance_id = 'can_B_0'
bottle_A[0].instance_id = 'bottle_A_0'
lamp_B[0].instance_id = 'lamp_B_0'
shelf_B[0].instance_id = 'shelf_B_0'
dishwasher[0].instance_id = 'dishwasher_0'
can_C[0].instance_id = 'can_C_0'
bottle_B[0].instance_id = 'bottle_B_0'
lamp_C[0].instance_id = 'lamp_C_0'
food_A[0].instance_id = 'food_A_0'
food_B[0].instance_id = 'food_B_0'
food_C[0].instance_id = 'food_C_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

oven[0].position = [1.1084453996736683, 3.844916593601406, 0.45]
oven[0].rotation = [0, 0, 0]
can_A[0].position = [2.189906645536053, 0.06809274837737701, 0.06]
can_A[0].rotation = [0, 0, 0]
shelf_A[0].position = [2.5102301612230917, 1.2151533607025797, 0.02]
shelf_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [0.048934391960856666, 2.8726484720820387, 0.125]
lamp_A[0].rotation = [0, 0, 0]
can_B[0].position = [4.565080771271384, 0.8191668986470078, 0.06]
can_B[0].rotation = [0, 0, 0]
bottle_A[0].position = [4.295037937803878, 0.9598520269105535, 0.14]
bottle_A[0].rotation = [0, 0, 0]
lamp_B[0].position = [2.4343743995938705, 3.43389972883728, 0.125]
lamp_B[0].rotation = [0, 0, 0]
shelf_B[0].position = [0.39121194853283864, 2.264255700899299, 0.9]
shelf_B[0].rotation = [0, 0, 0]
dishwasher[0].position = [2.152230538445368, 2.2472696860803434, 0.425]
dishwasher[0].rotation = [0, 0, 0]
can_C[0].position = [0.6209864907994409, 1.7809886071316363, 0.06]
can_C[0].rotation = [0, 0, 0]
bottle_B[0].position = [2.4839045839406686, 0.6607515748615796, 0.14]
bottle_B[0].rotation = [0, 0, 0]
lamp_C[0].position = [3.7566168144799867, 1.0030379781917897, 0.125]
lamp_C[0].rotation = [0, 0, 0]
food_A[0].position = [3.6760519149171724, 3.2893905710684717, 0.125]
food_A[0].rotation = [0, 0, 0]
food_B[0].position = [3.013047612322917, 2.1525979936102804, 0.125]
food_B[0].rotation = [0, 0, 0]
food_C[0].position = [1.0228215433058792, 3.8495712218431346, 0.125]
food_C[0].rotation = [0, 0, 0]
oven[0].position = [1.1084453996736683, 3.844916593601406, 0.45]
oven[0].rotation = [0, 0, 0]
can_A[0].position = [2.189906645536053, 0.06809274837737701, 0.06]
can_A[0].rotation = [0, 0, 0]
shelf_A[0].position = [2.5102301612230917, 1.2151533607025797, 0.02]
shelf_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [0.048934391960856666, 2.8726484720820387, 0.125]
lamp_A[0].rotation = [0, 0, 0]
can_B[0].position = [4.565080771271384, 0.8191668986470078, 0.06]
can_B[0].rotation = [0, 0, 0]
bottle_A[0].position = [4.295037937803878, 0.9598520269105535, 0.14]
bottle_A[0].rotation = [0, 0, 0]
lamp_B[0].position = [2.4343743995938705, 3.43389972883728, 0.125]
lamp_B[0].rotation = [0, 0, 0]
shelf_B[0].position = [0.39121194853283864, 2.264255700899299, 0.9]
shelf_B[0].rotation = [0, 0, 0]
dishwasher[0].position = [2.152230538445368, 2.2472696860803434, 0.425]
dishwasher[0].rotation = [0, 0, 0]
can_C[0].position = [0.6209864907994409, 1.7809886071316363, 0.06]
can_C[0].rotation = [0, 0, 0]
bottle_B[0].position = [2.4839045839406686, 0.6607515748615796, 0.14]
bottle_B[0].rotation = [0, 0, 0]
lamp_C[0].position = [3.7566168144799867, 1.0030379781917897, 0.125]
lamp_C[0].rotation = [0, 0, 0]
food_A[0].position = [3.6760519149171724, 3.2893905710684717, 0.125]
food_A[0].rotation = [0, 0, 0]
food_B[0].position = [3.013047612322917, 2.1525979936102804, 0.125]
food_B[0].rotation = [0, 0, 0]
food_C[0].position = [1.0228215433058792, 3.8495712218431346, 0.125]
food_C[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the two floor appliances along the lower wall, well to the left of
# the door at x=2.95. Both face into the room (+y).
oven[0].position = [0.45, 0.30, 0.45]
oven[0].rotation = [0, 0, radians(90)]

dishwasher[0].position = [1.20, 0.30, 0.425]
dishwasher[0].rotation = [0, 0, radians(90)]

# Place the tall shelf (o0007 / shelf_B) against the unobstructed left wall.
# Its long axis follows the wall and its front faces into the room.
shelf_B[0].position = [0.20, 3.15, 0.90]
shelf_B[0].rotation = [0, 0, 0]

# Use shelf_A as a wall-mounted pantry shelf on a separate portion of the
# left wall. Its elevation leaves the floor and circulation route clear.
shelf_A[0].position = [0.15, 1.40, 1.25]
shelf_A[0].rotation = [0, 0, 0]

# Put one lamp on each major horizontal surface.
lamp_A[0].position = [0.45, 0.30, 1.025]
lamp_A[0].rotation = [0, 0, radians(90)]

lamp_B[0].position = [1.20, 0.30, 0.975]
lamp_B[0].rotation = [0, 0, radians(90)]

lamp_C[0].position = [0.20, 3.15, 1.925]
lamp_C[0].rotation = [0, 0, 0]

# Arrange the compact pantry items in one non-overlapping row on shelf_A.
# The shelf's upper surface is at z=1.27.
can_A[0].position = [0.15, 0.84, 1.33]
can_A[0].rotation = [0, 0, 0]

bottle_A[0].position = [0.15, 0.94, 1.41]
bottle_A[0].rotation = [0, 0, 0]

food_A[0].position = [0.15, 1.10, 1.395]
food_A[0].rotation = [0, 0, 0]

can_B[0].position = [0.15, 1.245, 1.33]
can_B[0].rotation = [0, 0, 0]

bottle_B[0].position = [0.15, 1.35, 1.41]
bottle_B[0].rotation = [0, 0, 0]

food_B[0].position = [0.15, 1.51, 1.395]
food_B[0].rotation = [0, 0, 0]

can_C[0].position = [0.15, 1.655, 1.33]
can_C[0].rotation = [0, 0, 0]

food_C[0].position = [0.15, 1.80, 1.395]
food_C[0].rotation = [0, 0, 0]


# Fixed targets preserve the intended positions while allowing the solver to
# make small feasibility adjustments through the wall/support constraints.
oven_anchor = AssetInstance(position=[0.45, 0.30, 0.45])
dishwasher_anchor = AssetInstance(position=[1.20, 0.30, 0.425])
shelf_A_anchor = AssetInstance(position=[0.15, 1.40, 1.25])
shelf_B_anchor = AssetInstance(position=[0.20, 3.15, 0.90])

# Targets directly in front of the floor appliances establish their +y
# orientation without pulling either appliance toward the doorway.
oven_front_target = AssetInstance(position=[0.45, 2.00, 0.45])
dishwasher_front_target = AssetInstance(position=[1.20, 2.00, 0.425])

# Floor assets: wall contact is the primary semantic constraint.
solver.against_wall(oven[0], walls[3])
solver.distance_constraint(oven[0], oven_anchor, 0, 0, weight=10)
solver.point_towards(oven[0], oven_front_target)

solver.against_wall(dishwasher[0], walls[3])
solver.distance_constraint(
    dishwasher[0], dishwasher_anchor, 0, 0, weight=10
)
solver.point_towards(dishwasher[0], dishwasher_front_target)

# The tall shelf explicitly satisfies the requirement that shelf o0007 be
# against a wall. Both shelves face +x, toward the room interior.
solver.against_wall(shelf_B[0], walls[2])
solver.distance_constraint(shelf_B[0], shelf_B_anchor, 0, 0, weight=10)
solver.point_towards(
    shelf_B[0],
    AssetInstance(position=[2.00, 3.15, 0.90]),
)

solver.against_wall(shelf_A[0], walls[2])
solver.distance_constraint(shelf_A[0], shelf_A_anchor, 0, 0, weight=10)
solver.align_with(shelf_A[0], shelf_B[0])

# Lamps remain supported by their respective surfaces. Each also has a
# position-based anchor and an orientation relationship.
solver.on_top_of(lamp_A[0], oven[0])
solver.distance_constraint(
    lamp_A[0],
    AssetInstance(position=[0.45, 0.30, 1.025]),
    0,
    0,
    weight=10,
)
solver.align_with(lamp_A[0], oven[0])

solver.on_top_of(lamp_B[0], dishwasher[0])
solver.distance_constraint(
    lamp_B[0],
    AssetInstance(position=[1.20, 0.30, 0.975]),
    0,
    0,
    weight=10,
)
solver.align_with(lamp_B[0], dishwasher[0])

solver.on_top_of(lamp_C[0], shelf_B[0])
solver.distance_constraint(
    lamp_C[0],
    AssetInstance(position=[0.20, 3.15, 1.925]),
    0,
    0,
    weight=10,
)
solver.align_with(lamp_C[0], shelf_B[0])

# Every pantry item is constrained onto shelf_A, anchored to its own slot,
# and aligned with the shelf so the organized row is maintained.
solver.on_top_of(can_A[0], shelf_A[0])
solver.distance_constraint(
    can_A[0],
    AssetInstance(position=[0.15, 0.84, 1.33]),
    0,
    0,
    weight=10,
)
solver.align_with(can_A[0], shelf_A[0])

solver.on_top_of(bottle_A[0], shelf_A[0])
solver.distance_constraint(
    bottle_A[0],
    AssetInstance(position=[0.15, 0.94, 1.41]),
    0,
    0,
    weight=10,
)
solver.align_with(bottle_A[0], shelf_A[0])

solver.on_top_of(food_A[0], shelf_A[0])
solver.distance_constraint(
    food_A[0],
    AssetInstance(position=[0.15, 1.10, 1.395]),
    0,
    0,
    weight=10,
)
solver.align_with(food_A[0], shelf_A[0])

solver.on_top_of(can_B[0], shelf_A[0])
solver.distance_constraint(
    can_B[0],
    AssetInstance(position=[0.15, 1.245, 1.33]),
    0,
    0,
    weight=10,
)
solver.align_with(can_B[0], shelf_A[0])

solver.on_top_of(bottle_B[0], shelf_A[0])
solver.distance_constraint(
    bottle_B[0],
    AssetInstance(position=[0.15, 1.35, 1.41]),
    0,
    0,
    weight=10,
)
solver.align_with(bottle_B[0], shelf_A[0])

solver.on_top_of(food_B[0], shelf_A[0])
solver.distance_constraint(
    food_B[0],
    AssetInstance(position=[0.15, 1.51, 1.395]),
    0,
    0,
    weight=10,
)
solver.align_with(food_B[0], shelf_A[0])

solver.on_top_of(can_C[0], shelf_A[0])
solver.distance_constraint(
    can_C[0],
    AssetInstance(position=[0.15, 1.655, 1.33]),
    0,
    0,
    weight=10,
)
solver.align_with(can_C[0], shelf_A[0])

solver.on_top_of(food_C[0], shelf_A[0])
solver.distance_constraint(
    food_C[0],
    AssetInstance(position=[0.15, 1.80, 1.395]),
    0,
    0,
    weight=10,
)
solver.align_with(food_C[0], shelf_A[0])

solver.constraints = []
shelf_B[0].position = [0.19999995827674866, 3.1500000953674316, 0.8999999761581421]
shelf_B[0].rotation = [0, 0, 1.9322192577699163e-07]
shelf_B[0].optimize = 2
food_A[0].position = [0.15000000596046448, 1.100000023841858, 0.16499999165534973]
food_A[0].rotation = [0, 0, -1.6259636839588875e-06]
food_A[0].optimize = 2
can_B[0].position = [0.15000000596046448, 1.2450000047683716, 0.09999999403953552]
can_B[0].rotation = [0, 0, -1.6259636839588875e-06]
can_B[0].optimize = 2
can_C[0].position = [0.15000000596046448, 1.6549999713897705, 0.09999999403953552]
can_C[0].rotation = [0, 0, -1.6259636839588875e-06]
can_C[0].optimize = 2
food_B[0].position = [0.15000000596046448, 1.5099999904632568, 0.16499999165534973]
food_B[0].rotation = [0, 0, -1.6259636839588875e-06]
food_B[0].optimize = 2
shelf_A[0].position = [0.14999976754188538, 1.399999976158142, 0.019999999552965164]
shelf_A[0].rotation = [0, 0, 3.819321263933732e-07]
shelf_A[0].optimize = 2
can_A[0].position = [0.15000000596046448, 0.8399999737739563, 0.09999999403953552]
can_A[0].rotation = [0, 0, -1.6259636839588875e-06]
can_A[0].optimize = 2
bottle_B[0].position = [0.15000000596046448, 1.350000023841858, 0.18000000715255737]
bottle_B[0].rotation = [0, 0, -1.6259636839588875e-06]
bottle_B[0].optimize = 2
lamp_A[0].position = [0.44999998807907104, 0.30000001192092896, 1.024999976158142]
lamp_A[0].rotation = [0, 0, 1.5707960696398897]
lamp_A[0].optimize = 2
lamp_B[0].position = [1.2000000476837158, 0.30000001192092896, 0.9750000238418579]
lamp_B[0].rotation = [0, 0, 1.5707960696398897]
lamp_B[0].optimize = 2
bottle_A[0].position = [0.15000000596046448, 0.9399999976158142, 0.18000000715255737]
bottle_A[0].rotation = [0, 0, -1.6259636839588875e-06]
bottle_A[0].optimize = 2
dishwasher[0].position = [1.2000000476837158, 0.30000007152557373, 0.42500001192092896]
dishwasher[0].rotation = [0, 0, 1.5707962736782894]
dishwasher[0].optimize = 2
food_C[0].position = [0.15000000596046448, 1.7999999523162842, 0.16499999165534973]
food_C[0].rotation = [0, 0, -1.6259636839588875e-06]
food_C[0].optimize = 2
lamp_C[0].position = [0.20000000298023224, 3.1500000953674316, 1.9249999523162842]
lamp_C[0].rotation = [0, 0, 1.9551552599275463e-07]
lamp_C[0].optimize = 2
oven[0].position = [0.44999998807907104, 0.30000007152557373, 0.44999998807907104]
oven[0].rotation = [0, 0, 1.5707962736782894]
oven[0].optimize = 2

