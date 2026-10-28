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
    Wall(corner1=[0.04, 7.81, 0.00], corner2=[0.00, 7.77, 0.00]),
    Wall(corner1=[0.00, 7.77, 0.00], corner2=[0.00, 5.27, 0.00]),
    Wall(corner1=[0.00, 5.27, 0.00], corner2=[3.67, 0.04, 0.00]),
    Wall(corner1=[3.67, 0.04, 0.00], corner2=[3.71, 0.00, 0.00]),
    Wall(corner1=[3.71, 0.00, 0.00], corner2=[6.52, 0.00, 0.00]),
    Wall(corner1=[6.52, 0.00, 0.00], corner2=[6.56, 0.04, 0.00]),
    Wall(corner1=[6.56, 0.04, 0.00], corner2=[6.56, 7.77, 0.00]),
    Wall(corner1=[6.56, 7.77, 0.00], corner2=[6.52, 7.81, 0.00]),
    Wall(corner1=[6.52, 7.81, 0.00], corner2=[0.04, 7.81, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
cabinet_A = Assets(description="cabinet", size=[0.60, 0.90, 0.90], placements=[AssetInstance() for _ in range(1)])
bin_A = Assets(description="bin", size=[0.35, 0.35, 0.60], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.60, 0.90, 0.90], placements=[AssetInstance() for _ in range(1)])
oven_A = Assets(description="oven", size=[0.60, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="chair", size=[0.50, 0.45, 0.90], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.50, 0.45, 0.90], placements=[AssetInstance() for _ in range(1)])
cabinet_C = Assets(description="cabinet", size=[0.60, 0.90, 0.90], placements=[AssetInstance() for _ in range(1)])
cup = Assets(description="cup", size=[0.09, 0.09, 0.12], placements=[AssetInstance() for _ in range(1)])
oven_B = Assets(description="oven", size=[0.60, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
case = Assets(description="case", size=[0.35, 0.50, 0.50], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="chair", size=[0.50, 0.45, 0.90], placements=[AssetInstance() for _ in range(1)])
cabinet_D = Assets(description="cabinet", size=[0.60, 0.90, 0.90], placements=[AssetInstance() for _ in range(1)])
sink = Assets(description="sink", size=[0.55, 0.80, 0.25], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="table", size=[0.90, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
box = Assets(description="box", size=[0.30, 0.40, 0.25], placements=[AssetInstance() for _ in range(1)])
basket = Assets(description="basket", size=[0.45, 0.45, 0.50], placements=[AssetInstance() for _ in range(1)])
microwave = Assets(description="microwave", size=[0.40, 0.50, 0.30], placements=[AssetInstance() for _ in range(1)])
cabinet_E = Assets(description="cabinet", size=[0.60, 0.90, 0.90], placements=[AssetInstance() for _ in range(1)])
cabinet_F = Assets(description="cabinet", size=[0.60, 0.90, 2.10], placements=[AssetInstance() for _ in range(1)])
bin_B = Assets(description="bin", size=[0.35, 0.35, 0.60], placements=[AssetInstance() for _ in range(1)])

cabinet_A[0].instance_id = 'cabinet_A_0'
bin_A[0].instance_id = 'bin_A_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
oven_A[0].instance_id = 'oven_A_0'
chair_A[0].instance_id = 'chair_A_0'
chair_B[0].instance_id = 'chair_B_0'
cabinet_C[0].instance_id = 'cabinet_C_0'
cup[0].instance_id = 'cup_0'
oven_B[0].instance_id = 'oven_B_0'
case[0].instance_id = 'case_0'
chair_C[0].instance_id = 'chair_C_0'
cabinet_D[0].instance_id = 'cabinet_D_0'
sink[0].instance_id = 'sink_0'
table[0].instance_id = 'table_0'
box[0].instance_id = 'box_0'
basket[0].instance_id = 'basket_0'
microwave[0].instance_id = 'microwave_0'
cabinet_E[0].instance_id = 'cabinet_E_0'
cabinet_F[0].instance_id = 'cabinet_F_0'
bin_B[0].instance_id = 'bin_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'
walls[8].instance_id = 'walls_8'

cabinet_A[0].position = [2.846560583020349, 6.872596748083242, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
bin_A[0].position = [6.534203713068975, 3.4725882867518587, 0.3]
bin_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [4.668904155524365, 0.2158153048951051, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
oven_A[0].position = [5.821647049526122, 6.530106681699707, 0.45]
oven_A[0].rotation = [0, 0, 0]
chair_A[0].position = [4.082779867209438, 6.279603915595329, 0.45]
chair_A[0].rotation = [0, 0, 0]
chair_B[0].position = [3.787461278626984, 5.610159686704541, 0.45]
chair_B[0].rotation = [0, 0, 0]
cabinet_C[0].position = [4.470761470446915, 5.741990608264903, 0.45]
cabinet_C[0].rotation = [0, 0, 0]
cup[0].position = [6.384714527077273, 5.169578151012424, 0.06]
cup[0].rotation = [0, 0, 0]
oven_B[0].position = [2.5613772620505393, 3.9530047045116032, 0.45]
oven_B[0].rotation = [0, 0, 0]
case[0].position = [3.614513069675231, 6.882474709728982, 0.25]
case[0].rotation = [0, 0, 0]
chair_C[0].position = [2.938868859562107, 4.52453074594522, 0.45]
chair_C[0].rotation = [0, 0, 0]
cabinet_D[0].position = [5.823202730668697, 1.5787821550363597, 0.45]
cabinet_D[0].rotation = [0, 0, 0]
sink[0].position = [5.2793520546957105, 0.2876135213406876, 0.125]
sink[0].rotation = [0, 0, 0]
table[0].position = [0.9739273311990035, 6.834218246768636, 0.375]
table[0].rotation = [0, 0, 0]
box[0].position = [2.561119645735393, 2.984701792729142, 0.125]
box[0].rotation = [0, 0, 0]
basket[0].position = [5.392341098527429, 2.1427366656685596, 0.25]
basket[0].rotation = [0, 0, 0]
microwave[0].position = [2.6313757610227615, 1.7718045710230224, 0.15]
microwave[0].rotation = [0, 0, 0]
cabinet_E[0].position = [2.8922593749281638, 4.644421284413011, 0.45]
cabinet_E[0].rotation = [0, 0, 0]
cabinet_F[0].position = [3.9767336735303997, 3.364878354492863, 1.05]
cabinet_F[0].rotation = [0, 0, 0]
bin_B[0].position = [5.923175695162469, 3.527184775790994, 0.3]
bin_B[0].rotation = [0, 0, 0]
cabinet_A[0].position = [2.846560583020349, 6.872596748083242, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
bin_A[0].position = [6.534203713068975, 3.4725882867518587, 0.3]
bin_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [4.668904155524365, 0.2158153048951051, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
oven_A[0].position = [5.821647049526122, 6.530106681699707, 0.45]
oven_A[0].rotation = [0, 0, 0]
chair_A[0].position = [4.082779867209438, 6.279603915595329, 0.45]
chair_A[0].rotation = [0, 0, 0]
chair_B[0].position = [3.787461278626984, 5.610159686704541, 0.45]
chair_B[0].rotation = [0, 0, 0]
cabinet_C[0].position = [4.470761470446915, 5.741990608264903, 0.45]
cabinet_C[0].rotation = [0, 0, 0]
cup[0].position = [6.384714527077273, 5.169578151012424, 0.06]
cup[0].rotation = [0, 0, 0]
oven_B[0].position = [2.5613772620505393, 3.9530047045116032, 0.45]
oven_B[0].rotation = [0, 0, 0]
case[0].position = [3.614513069675231, 6.882474709728982, 0.25]
case[0].rotation = [0, 0, 0]
chair_C[0].position = [2.938868859562107, 4.52453074594522, 0.45]
chair_C[0].rotation = [0, 0, 0]
cabinet_D[0].position = [5.823202730668697, 1.5787821550363597, 0.45]
cabinet_D[0].rotation = [0, 0, 0]
sink[0].position = [5.2793520546957105, 0.2876135213406876, 0.125]
sink[0].rotation = [0, 0, 0]
table[0].position = [0.9739273311990035, 6.834218246768636, 0.375]
table[0].rotation = [0, 0, 0]
box[0].position = [2.561119645735393, 2.984701792729142, 0.125]
box[0].rotation = [0, 0, 0]
basket[0].position = [5.392341098527429, 2.1427366656685596, 0.25]
basket[0].rotation = [0, 0, 0]
microwave[0].position = [2.6313757610227615, 1.7718045710230224, 0.15]
microwave[0].rotation = [0, 0, 0]
cabinet_E[0].position = [2.8922593749281638, 4.644421284413011, 0.45]
cabinet_E[0].rotation = [0, 0, 0]
cabinet_F[0].position = [3.9767336735303997, 3.364878354492863, 1.05]
cabinet_F[0].rotation = [0, 0, 0]
bin_B[0].position = [5.923175695162469, 3.527184775790994, 0.3]
bin_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the cooking/storage run along the lower portion of the right wall.
# It ends before the door opening (y=4.81), keeping the entrance clear.
cabinet_A[0].position = [6.26, 0.45, 0.45]
cabinet_A[0].rotation = [0, 0, radians(180)]

oven_A[0].position = [6.26, 1.20, 0.45]
oven_A[0].rotation = [0, 0, radians(180)]

cabinet_B[0].position = [6.26, 1.95, 0.45]
cabinet_B[0].rotation = [0, 0, radians(180)]

oven_B[0].position = [6.26, 2.70, 0.45]
oven_B[0].rotation = [0, 0, radians(180)]

cabinet_C[0].position = [6.26, 3.45, 0.45]
cabinet_C[0].rotation = [0, 0, radians(180)]

cabinet_D[0].position = [6.26, 4.35, 0.45]
cabinet_D[0].rotation = [0, 0, radians(180)]

# Place additional storage against the upper wall, to the left of the window.
cabinet_F[0].position = [1.00, 7.51, 1.05]
cabinet_F[0].rotation = [0, 0, radians(-90)]

cabinet_E[0].position = [2.20, 7.51, 0.45]
cabinet_E[0].rotation = [0, 0, radians(-90)]

# bin_A is o0001 and cabinet_E is o0017. Their nearest bounding-box
# surfaces are 0.10 m apart; the corresponding center separation is
# approximately 0.736 m because the solver measures center distance.
bin_A[0].position = [2.925, 7.635, 0.30]
bin_A[0].rotation = [0, 0, radians(-90)]

# Put the sink and microwave on compatible base cabinets.
sink[0].position = [6.26, 3.45, 1.025]
sink[0].rotation = [0, 0, radians(180)]

microwave[0].position = [6.26, 4.35, 1.05]
microwave[0].rotation = [0, 0, radians(180)]

# The dining/work area is in the broad upper-left portion of the room,
# away from both the door approach and the window.
table[0].position = [3.20, 6.30, 0.375]
table[0].rotation = [0, 0, radians(90)]

# chair_B (o0005) lies between chair_A (o0004) and chair_C (o0010).
# chair_C faces chair_B as explicitly required.
chair_A[0].position = [2.30, 5.35, 0.45]
chair_A[0].rotation = [0, 0, radians(90)]

chair_B[0].position = [3.20, 5.25, 0.45]
chair_B[0].rotation = [0, 0, radians(90)]

chair_C[0].position = [4.10, 5.35, 0.45]
chair_C[0].rotation = [0, 0, radians(180)]

# The cup belongs on the table.
cup[0].position = [3.20, 6.30, 0.81]
cup[0].rotation = [0, 0, radians(90)]

# Keep the remaining portable storage objects in the open lower-right
# area without obstructing the kitchen run or circulation from the door.
case[0].position = [4.05, 1.15, 0.25]
case[0].rotation = [0, 0, radians(90)]

box[0].position = [4.85, 1.10, 0.125]
box[0].rotation = [0, 0, radians(90)]

basket[0].position = [5.55, 1.10, 0.25]
basket[0].rotation = [0, 0, radians(90)]

bin_B[0].position = [5.45, 2.00, 0.30]
bin_B[0].rotation = [0, 0, radians(180)]


# Fixed references preserve the intended zones while allowing the solver
# to make small feasibility adjustments.
room_center = AssetInstance(position=[3.60, 4.20, 0.45])
cabinet_A_anchor = AssetInstance(position=[6.26, 0.45, 0.45])
oven_A_anchor = AssetInstance(position=[6.26, 1.20, 0.45])
cabinet_B_anchor = AssetInstance(position=[6.26, 1.95, 0.45])
oven_B_anchor = AssetInstance(position=[6.26, 2.70, 0.45])
cabinet_C_anchor = AssetInstance(position=[6.26, 3.45, 0.45])
cabinet_D_anchor = AssetInstance(position=[6.26, 4.35, 0.45])
cabinet_E_anchor = AssetInstance(position=[2.20, 7.51, 0.45])
cabinet_F_anchor = AssetInstance(position=[1.00, 7.51, 1.05])
case_anchor = AssetInstance(position=[4.05, 1.15, 0.25])
box_anchor = AssetInstance(position=[4.85, 1.10, 0.125])
basket_anchor = AssetInstance(position=[5.55, 1.10, 0.25])
bin_B_anchor = AssetInstance(position=[5.45, 2.00, 0.30])

# Important room-boundary constraints for the perimeter furniture.
solver.against_wall(cabinet_A[0], walls[6])
solver.against_wall(oven_A[0], walls[6])
solver.against_wall(cabinet_B[0], walls[6])
solver.against_wall(oven_B[0], walls[6])
solver.against_wall(cabinet_C[0], walls[6])
solver.against_wall(cabinet_D[0], walls[6])
solver.against_wall(cabinet_E[0], walls[8])
solver.against_wall(cabinet_F[0], walls[8])
solver.against_wall(bin_A[0], walls[8])

# Anchor the wall run so it remains ordered and clear of the doorway.
solver.distance_constraint(cabinet_A[0], cabinet_A_anchor, 0, 0, weight=10)
solver.distance_constraint(oven_A[0], oven_A_anchor, 0, 0, weight=10)
solver.distance_constraint(cabinet_B[0], cabinet_B_anchor, 0, 0, weight=10)
solver.distance_constraint(oven_B[0], oven_B_anchor, 0, 0, weight=10)
solver.distance_constraint(cabinet_C[0], cabinet_C_anchor, 0, 0, weight=10)
solver.distance_constraint(cabinet_D[0], cabinet_D_anchor, 0, 0, weight=10)
solver.distance_constraint(cabinet_E[0], cabinet_E_anchor, 0, 0, weight=10)
solver.distance_constraint(cabinet_F[0], cabinet_F_anchor, 0, 0, weight=10)

# All wall furniture faces inward.
solver.point_towards(cabinet_A[0], room_center)
solver.point_towards(oven_A[0], room_center)
solver.point_towards(cabinet_B[0], room_center)
solver.point_towards(oven_B[0], room_center)
solver.point_towards(cabinet_C[0], room_center)
solver.point_towards(cabinet_D[0], room_center)
solver.point_towards(cabinet_E[0], room_center)
solver.point_towards(cabinet_F[0], room_center)
solver.point_towards(bin_A[0], room_center)

# Encode the required bin-to-cabinet proximity in terms of center distance.
# The 0.625–0.74 m range allows a surface gap no greater than 0.10 m.
solver.distance_constraint(bin_A[0], cabinet_E[0], 0.625, 0.74, weight=10)

# Countertop appliances/fixtures receive both support and position constraints.
solver.on_top_of(sink[0], cabinet_C[0])
solver.distance_constraint(
    sink[0],
    AssetInstance(position=[6.26, 3.45, 1.025]),
    0, 0,
    weight=10,
)
solver.align_with(sink[0], cabinet_C[0])

solver.on_top_of(microwave[0], cabinet_D[0])
solver.distance_constraint(
    microwave[0],
    AssetInstance(position=[6.26, 4.35, 1.05]),
    0, 0,
    weight=10,
)
solver.align_with(microwave[0], cabinet_D[0])

# Fix the table in its circulation-safe zone and orient it across the room.
solver.distance_constraint(
    table[0],
    AssetInstance(position=[3.20, 6.30, 0.375]),
    0, 0,
    weight=10,
)
solver.point_towards(table[0], chair_B[0])

# Preserve the three-chair ordering. Equal distances from chair_B to the
# outer chairs, plus their wider mutual separation, keep chair_B between them.
solver.distance_constraint(chair_A[0], chair_B[0], 0.90, 0.92, weight=10)
solver.distance_constraint(chair_C[0], chair_B[0], 0.90, 0.92, weight=10)
solver.distance_constraint(chair_A[0], chair_C[0], 1.79, 1.81, weight=10)

# The outer positions also prevent the group from drifting into the doorway.
solver.distance_constraint(
    chair_A[0],
    AssetInstance(position=[2.30, 5.35, 0.45]),
    0, 0,
    weight=10,
)
solver.distance_constraint(
    chair_B[0],
    AssetInstance(position=[3.20, 5.25, 0.45]),
    0, 0,
    weight=10,
)
solver.distance_constraint(
    chair_C[0],
    AssetInstance(position=[4.10, 5.35, 0.45]),
    0, 0,
    weight=10,
)

solver.point_towards(chair_A[0], table[0])
solver.point_towards(chair_B[0], table[0])
solver.point_towards(chair_C[0], chair_B[0])

# Keep the cup centered on and supported by the table.
solver.on_top_of(cup[0], table[0])
solver.distance_constraint(
    cup[0],
    AssetInstance(position=[3.20, 6.30, 0.81]),
    0, 0,
    weight=10,
)
solver.align_with(cup[0], table[0])

# Position and orient each remaining floor-standing object.
solver.distance_constraint(case[0], case_anchor, 0, 0, weight=10)
solver.align_with(case[0], table[0])

solver.distance_constraint(box[0], box_anchor, 0, 0, weight=10)
solver.align_with(box[0], table[0])

solver.distance_constraint(basket[0], basket_anchor, 0, 0, weight=10)
solver.align_with(basket[0], table[0])

solver.distance_constraint(bin_B[0], bin_B_anchor, 0, 0, weight=10)
solver.point_towards(bin_B[0], room_center)

solver.constraints = []
cabinet_E[0].position = [2.200000047683716, 7.5099616050720215, 0.44999998807907104]
cabinet_E[0].rotation = [0, 0, -1.5651448078789751]
cabinet_E[0].optimize = 2
sink[0].position = [6.260000228881836, 3.450000047683716, 1.024999976158142]
sink[0].rotation = [0, 0, -3.1188052874140135]
sink[0].optimize = 2
basket[0].position = [5.550000190734863, 1.100000023841858, 0.25]
basket[0].rotation = [0, 0, 1.5904141227569952]
basket[0].optimize = 2
table[0].position = [3.200000047683716, 6.300000190734863, 0.375]
table[0].rotation = [0, 0, 1.6126210785781452]
table[0].optimize = 2
oven_B[0].position = [6.269999027252197, 2.700000047683716, 0.44999998807907104]
oven_B[0].rotation = [0, 0, -3.139051734217035]
oven_B[0].optimize = 2
cabinet_B[0].position = [6.269999027252197, 1.9500000476837158, 0.44999998807907104]
cabinet_B[0].rotation = [0, 0, -3.1390517385055796]
cabinet_B[0].optimize = 2
oven_A[0].position = [6.269999027252197, 1.2000000476837158, 0.44999998807907104]
oven_A[0].rotation = [0, 0, -3.139051734217035]
oven_A[0].optimize = 2
chair_C[0].position = [4.099999904632568, 5.349999904632568, 0.44999998807907104]
chair_C[0].rotation = [0, 0, -3.125884689672577]
chair_C[0].optimize = 2
cabinet_F[0].position = [1.0, 7.519999027252197, 1.0499999523162842]
cabinet_F[0].rotation = [0, 0, -1.568255411710683]
cabinet_F[0].optimize = 2
microwave[0].position = [6.260000228881836, 4.349999904632568, 1.0499999523162842]
microwave[0].rotation = [0, 0, -3.1188052874140135]
microwave[0].optimize = 2
cabinet_D[0].position = [6.25856876373291, 4.349999904632568, 0.44999998807907104]
cabinet_D[0].rotation = [0, 0, -3.1328304335560806]
cabinet_D[0].optimize = 2
case[0].position = [4.050000190734863, 1.149999976158142, 0.25]
case[0].rotation = [0, 0, 1.5904141227569952]
case[0].optimize = 2
cup[0].position = [3.200000047683716, 6.300000190734863, 0.8100000023841858]
cup[0].rotation = [0, 0, 1.593586675425212]
cup[0].optimize = 2
chair_A[0].position = [2.299999952316284, 5.349999904632568, 0.44999998807907104]
chair_A[0].rotation = [0, 0, 1.5764477861023531]
chair_A[0].optimize = 2
bin_B[0].position = [5.449999809265137, 2.0, 0.30000001192092896]
bin_B[0].rotation = [0, 0, -3.1321678761290697]
bin_B[0].optimize = 2
box[0].position = [4.849999904632568, 1.100000023841858, 0.125]
box[0].rotation = [0, 0, 1.5904141227569952]
box[0].optimize = 2
cabinet_A[0].position = [6.250805854797363, 0.47919395565986633, 0.44999998807907104]
cabinet_A[0].rotation = [0, 0, -3.1390517311505883]
cabinet_A[0].optimize = 2
chair_B[0].position = [3.200000047683716, 5.25, 0.44999998807907104]
chair_B[0].rotation = [0, 0, 1.5927874750809192]
chair_B[0].optimize = 2
bin_A[0].position = [2.924999952316284, 7.644999027252197, 0.30000001192092896]
bin_A[0].rotation = [0, 0, -1.5682554052778654]
bin_A[0].optimize = 2
cabinet_C[0].position = [6.25856876373291, 3.450000047683716, 0.44999998807907104]
cabinet_C[0].rotation = [0, 0, -3.1328304335560806]
cabinet_C[0].optimize = 2

