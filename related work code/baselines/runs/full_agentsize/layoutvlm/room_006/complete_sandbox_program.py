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
    Wall(corner1=[3.76, 4.84, 0.00], corner2=[0.00, 4.84, 0.00]),
    Wall(corner1=[0.00, 4.84, 0.00], corner2=[0.10, 0.00, 0.00]),
    Wall(corner1=[0.10, 0.00, 0.00], corner2=[3.76, 0.00, 0.00]),
    Wall(corner1=[3.76, 0.00, 0.00], corner2=[3.76, 4.84, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
carpet_A = Assets(description="carpet", size=[1.70, 2.40, 0.02], placements=[AssetInstance() for _ in range(1)])
decoration_A = Assets(description="decoration", size=[0.12, 0.32, 0.45], placements=[AssetInstance() for _ in range(1)])
seat_A = Assets(description="seat", size=[0.78, 0.72, 0.84], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="cabinet", size=[0.42, 0.90, 0.78], placements=[AssetInstance() for _ in range(1)])
decoration_B = Assets(description="decoration", size=[0.05, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])
candle = Assets(description="candle", size=[0.08, 0.08, 0.18], placements=[AssetInstance() for _ in range(1)])
dresser = Assets(description="dresser", size=[0.50, 1.35, 0.82], placements=[AssetInstance() for _ in range(1)])
casket = Assets(description="casket", size=[0.25, 0.42, 0.22], placements=[AssetInstance() for _ in range(1)])
seat_B = Assets(description="seat", size=[0.78, 0.72, 0.84], placements=[AssetInstance() for _ in range(1)])
decoration_C = Assets(description="decoration", size=[0.16, 0.28, 0.38], placements=[AssetInstance() for _ in range(1)])
decoration_D = Assets(description="decoration", size=[0.05, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
vase = Assets(description="vase", size=[0.18, 0.18, 0.34], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.05, 1.60, 0.95], placements=[AssetInstance() for _ in range(1)])
mirror = Assets(description="mirror", size=[0.04, 0.75, 1.05], placements=[AssetInstance() for _ in range(1)])
carpet_B = Assets(description="carpet", size=[1.20, 1.80, 0.02], placements=[AssetInstance() for _ in range(1)])
pillow = Assets(description="pillow", size=[0.45, 0.70, 0.16], placements=[AssetInstance() for _ in range(1)])
case = Assets(description="case", size=[0.38, 0.48, 0.55], placements=[AssetInstance() for _ in range(1)])
globe = Assets(description="globe", size=[0.30, 0.30, 0.42], placements=[AssetInstance() for _ in range(1)])
lamp = Assets(description="lamp", size=[0.32, 0.32, 0.58], placements=[AssetInstance() for _ in range(1)])

carpet_A[0].instance_id = 'carpet_A_0'
decoration_A[0].instance_id = 'decoration_A_0'
seat_A[0].instance_id = 'seat_A_0'
cabinet[0].instance_id = 'cabinet_0'
decoration_B[0].instance_id = 'decoration_B_0'
candle[0].instance_id = 'candle_0'
dresser[0].instance_id = 'dresser_0'
casket[0].instance_id = 'casket_0'
seat_B[0].instance_id = 'seat_B_0'
decoration_C[0].instance_id = 'decoration_C_0'
decoration_D[0].instance_id = 'decoration_D_0'
vase[0].instance_id = 'vase_0'
bed[0].instance_id = 'bed_0'
mirror[0].instance_id = 'mirror_0'
carpet_B[0].instance_id = 'carpet_B_0'
pillow[0].instance_id = 'pillow_0'
case[0].instance_id = 'case_0'
globe[0].instance_id = 'globe_0'
lamp[0].instance_id = 'lamp_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

carpet_A[0].position = [1.2447162423686216, 2.547829175075929, 0.01]
carpet_A[0].rotation = [0, 0, 0]
decoration_A[0].position = [0.22965794315044263, 2.9959606726508894, 0.225]
decoration_A[0].rotation = [0, 0, 0]
seat_A[0].position = [3.3498239099086287, 4.44313558899267, 0.42]
seat_A[0].rotation = [0, 0, 0]
cabinet[0].position = [1.6058158419828474, 2.6154937764164674, 0.39]
cabinet[0].rotation = [0, 0, 0]
decoration_B[0].position = [3.669531067594171, 0.24214700395282487, 0.3]
decoration_B[0].rotation = [0, 0, 0]
candle[0].position = [3.173062176996257, 2.109214238813379, 0.09]
candle[0].rotation = [0, 0, 0]
dresser[0].position = [1.318575459712361, 3.897628805135568, 0.41]
dresser[0].rotation = [0, 0, 0]
casket[0].position = [1.1062312038496198, 0.4017373951483593, 0.11]
casket[0].rotation = [0, 0, 0]
seat_B[0].position = [2.4302965928112843, 3.3479684748987673, 0.42]
seat_B[0].rotation = [0, 0, 0]
decoration_C[0].position = [3.528832291596631, 0.4784608304226936, 0.19]
decoration_C[0].rotation = [0, 0, 0]
decoration_D[0].position = [3.5588209389792795, 2.7890801995802708, 0.35]
decoration_D[0].rotation = [0, 0, 0]
vase[0].position = [1.7740469053680306, 2.6619577427236605, 0.17]
vase[0].rotation = [0, 0, 0]
bed[0].position = [1.3738900232079467, 3.3457367057239935, 0.475]
bed[0].rotation = [0, 0, 0]
mirror[0].position = [0.027655420108724273, 3.901460138793778, 0.525]
mirror[0].rotation = [0, 0, 0]
carpet_B[0].position = [1.6049990585402834, 2.9691674339230145, 0.01]
carpet_B[0].rotation = [0, 0, 0]
pillow[0].position = [1.680346921085056, 3.3708166217473163, 0.08]
pillow[0].rotation = [0, 0, 0]
case[0].position = [2.234754261513868, 0.9071529435308883, 0.275]
case[0].rotation = [0, 0, 0]
globe[0].position = [2.983559501379251, 3.179910587841251, 0.21]
globe[0].rotation = [0, 0, 0]
lamp[0].position = [0.2975479445806726, 1.9414487713625779, 0.29]
lamp[0].rotation = [0, 0, 0]
carpet_A[0].position = [1.2447162423686216, 2.547829175075929, 0.01]
carpet_A[0].rotation = [0, 0, 0]
decoration_A[0].position = [0.22965794315044263, 2.9959606726508894, 0.225]
decoration_A[0].rotation = [0, 0, 0]
seat_A[0].position = [3.3498239099086287, 4.44313558899267, 0.42]
seat_A[0].rotation = [0, 0, 0]
cabinet[0].position = [1.6058158419828474, 2.6154937764164674, 0.39]
cabinet[0].rotation = [0, 0, 0]
decoration_B[0].position = [3.669531067594171, 0.24214700395282487, 0.3]
decoration_B[0].rotation = [0, 0, 0]
candle[0].position = [3.173062176996257, 2.109214238813379, 0.09]
candle[0].rotation = [0, 0, 0]
dresser[0].position = [1.318575459712361, 3.897628805135568, 0.41]
dresser[0].rotation = [0, 0, 0]
casket[0].position = [1.1062312038496198, 0.4017373951483593, 0.11]
casket[0].rotation = [0, 0, 0]
seat_B[0].position = [2.4302965928112843, 3.3479684748987673, 0.42]
seat_B[0].rotation = [0, 0, 0]
decoration_C[0].position = [3.528832291596631, 0.4784608304226936, 0.19]
decoration_C[0].rotation = [0, 0, 0]
decoration_D[0].position = [3.5588209389792795, 2.7890801995802708, 0.35]
decoration_D[0].rotation = [0, 0, 0]
vase[0].position = [1.7740469053680306, 2.6619577427236605, 0.17]
vase[0].rotation = [0, 0, 0]
bed[0].position = [1.3738900232079467, 3.3457367057239935, 0.475]
bed[0].rotation = [0, 0, 0]
mirror[0].position = [0.027655420108724273, 3.901460138793778, 0.525]
mirror[0].rotation = [0, 0, 0]
carpet_B[0].position = [1.6049990585402834, 2.9691674339230145, 0.01]
carpet_B[0].rotation = [0, 0, 0]
pillow[0].position = [1.680346921085056, 3.3708166217473163, 0.08]
pillow[0].rotation = [0, 0, 0]
case[0].position = [2.234754261513868, 0.9071529435308883, 0.275]
case[0].rotation = [0, 0, 0]
globe[0].position = [2.983559501379251, 3.179910587841251, 0.21]
globe[0].rotation = [0, 0, 0]
lamp[0].position = [0.2975479445806726, 1.9414487713625779, 0.29]
lamp[0].rotation = [0, 0, 0]

solver.constraints = []

# Reference points used for position and facing constraints.
room_center = AssetInstance(position=[1.88, 2.42, 0.00])
bed_anchor = AssetInstance(position=[1.88, 3.815, 0.495])
carpet_A_anchor = AssetInstance(position=[1.88, 3.64, 0.01])
carpet_B_anchor = AssetInstance(position=[1.35, 0.75, 0.01])
seat_A_anchor = AssetInstance(position=[0.60, 0.60, 0.44])
seat_B_anchor = AssetInstance(position=[2.10, 0.60, 0.44])
case_anchor = AssetInstance(position=[1.35, 0.60, 0.285])
cabinet_anchor = AssetInstance(position=[3.55, 3.90, 0.39])
dresser_anchor = AssetInstance(position=[3.51, 1.45, 0.41])

# The bed occupies the upper portion of the room, with its head against the
# north wall and its front directed into the room.
bed[0].position = [1.88, 3.815, 0.495]
bed[0].rotation = [0, 0, radians(-90)]
solver.against_wall(bed[0], walls[0])
solver.distance_constraint(bed[0], bed_anchor, 0, 0, weight=10)
solver.point_towards(bed[0], room_center)

# This carpet is centered beneath the bed. Its orientation gives enough
# coverage around the sides and foot of the bed.
carpet_A[0].position = [1.88, 3.64, 0.01]
carpet_A[0].rotation = [0, 0, 0]
solver.distance_constraint(carpet_A[0], carpet_A_anchor, 0, 0, weight=10)
solver.align_with(carpet_A[0], bed[0], angle=90)
solver.on_top_of(bed[0], carpet_A[0])

# A second rug defines a compact seating area near the south side of the room.
carpet_B[0].position = [1.35, 0.75, 0.01]
carpet_B[0].rotation = [0, 0, radians(90)]
solver.distance_constraint(carpet_B[0], carpet_B_anchor, 0, 0, weight=10)
solver.align_with(carpet_B[0], case[0])

# The two seats are separated sufficiently for access and face toward the bed.
seat_A[0].position = [0.60, 0.60, 0.44]
seat_A[0].rotation = [0, 0, radians(68)]
solver.distance_constraint(seat_A[0], seat_A_anchor, 0, 0, weight=10)
solver.point_towards(seat_A[0], bed[0])
solver.on_top_of(seat_A[0], carpet_B[0])

seat_B[0].position = [2.10, 0.60, 0.44]
seat_B[0].rotation = [0, 0, radians(94)]
solver.distance_constraint(seat_B[0], seat_B_anchor, 0, 0, weight=10)
solver.point_towards(seat_B[0], bed[0])
solver.on_top_of(seat_B[0], carpet_B[0])

# The case is explicitly centered between the two seats, satisfying the
# required seat_A -- case -- seat_B ordering.
case[0].position = [1.35, 0.60, 0.285]
case[0].rotation = [0, 0, radians(90)]
solver.distance_constraint(case[0], case_anchor, 0, 0, weight=10)
solver.point_towards(case[0], bed[0])
solver.distance_constraint(case[0], seat_A[0], 0.70, 0.80, weight=10)
solver.distance_constraint(case[0], seat_B[0], 0.70, 0.80, weight=10)
solver.on_top_of(case[0], carpet_B[0])

# The lamp uses the case as a small table and remains centered on its top.
lamp[0].position = [1.35, 0.60, 0.84]
lamp[0].rotation = [0, 0, radians(90)]
lamp_anchor = AssetInstance(position=[1.35, 0.60, 0.84])
solver.on_top_of(lamp[0], case[0])
solver.distance_constraint(lamp[0], lamp_anchor, 0, 0, weight=10)
solver.align_with(lamp[0], case[0])

# The cabinet and dresser occupy separate sections of the east wall, leaving
# clear circulation between the seating area and bed.
cabinet[0].position = [3.55, 3.90, 0.39]
cabinet[0].rotation = [0, 0, radians(180)]
solver.against_wall(cabinet[0], walls[3])
solver.distance_constraint(cabinet[0], cabinet_anchor, 0, 0, weight=10)
solver.point_towards(cabinet[0], room_center)

dresser[0].position = [3.51, 1.45, 0.41]
dresser[0].rotation = [0, 0, radians(180)]
solver.against_wall(dresser[0], walls[3])
solver.distance_constraint(dresser[0], dresser_anchor, 0, 0, weight=10)
solver.point_towards(dresser[0], room_center)

# Two small objects are distributed across the cabinet top.
decoration_A[0].position = [3.48, 3.70, 1.005]
decoration_A[0].rotation = [0, 0, radians(180)]
decoration_A_anchor = AssetInstance(position=[3.48, 3.70, 1.005])
solver.on_top_of(decoration_A[0], cabinet[0])
solver.distance_constraint(decoration_A[0], decoration_A_anchor, 0, 0, weight=10)
solver.align_with(decoration_A[0], cabinet[0])

candle[0].position = [3.48, 4.10, 0.87]
candle[0].rotation = [0, 0, radians(180)]
candle_anchor = AssetInstance(position=[3.48, 4.10, 0.87])
solver.on_top_of(candle[0], cabinet[0])
solver.distance_constraint(candle[0], candle_anchor, 0, 0, weight=10)
solver.align_with(candle[0], cabinet[0])

# The dresser's longer top accommodates four objects in a non-overlapping row.
casket[0].position = [3.48, 0.94, 0.93]
casket[0].rotation = [0, 0, radians(180)]
casket_anchor = AssetInstance(position=[3.48, 0.94, 0.93])
solver.on_top_of(casket[0], dresser[0])
solver.distance_constraint(casket[0], casket_anchor, 0, 0, weight=10)
solver.align_with(casket[0], dresser[0])

decoration_C[0].position = [3.48, 1.30, 1.01]
decoration_C[0].rotation = [0, 0, radians(180)]
decoration_C_anchor = AssetInstance(position=[3.48, 1.30, 1.01])
solver.on_top_of(decoration_C[0], dresser[0])
solver.distance_constraint(decoration_C[0], decoration_C_anchor, 0, 0, weight=10)
solver.align_with(decoration_C[0], dresser[0])

vase[0].position = [3.48, 1.54, 0.99]
vase[0].rotation = [0, 0, radians(180)]
vase_anchor = AssetInstance(position=[3.48, 1.54, 0.99])
solver.on_top_of(vase[0], dresser[0])
solver.distance_constraint(vase[0], vase_anchor, 0, 0, weight=10)
solver.align_with(vase[0], dresser[0])

globe[0].position = [3.48, 1.84, 1.03]
globe[0].rotation = [0, 0, radians(180)]
globe_anchor = AssetInstance(position=[3.48, 1.84, 1.03])
solver.on_top_of(globe[0], dresser[0])
solver.distance_constraint(globe[0], globe_anchor, 0, 0, weight=10)
solver.align_with(globe[0], dresser[0])

# The pillow rests near the head of the bed and follows the bed's orientation.
pillow[0].position = [1.88, 4.28, 1.05]
pillow[0].rotation = [0, 0, radians(-90)]
pillow_anchor = AssetInstance(position=[1.88, 4.28, 1.05])
solver.on_top_of(pillow[0], bed[0])
solver.distance_constraint(pillow[0], pillow_anchor, 0, 0, weight=10)
solver.align_with(pillow[0], bed[0])

# Thin decorations and the mirror are mounted at distinct heights and
# horizontal locations along the west wall, above the floor furniture.
decoration_B[0].position = [0.055, 3.55, 1.45]
decoration_B[0].rotation = [0, 0, 0]
decoration_B_anchor = AssetInstance(position=[0.055, 3.55, 1.45])
solver.against_wall(decoration_B[0], walls[1])
solver.distance_constraint(decoration_B[0], decoration_B_anchor, 0, 0, weight=10)
solver.point_towards(decoration_B[0], room_center)

mirror[0].position = [0.065, 2.35, 1.30]
mirror[0].rotation = [0, 0, 0]
mirror_anchor = AssetInstance(position=[0.065, 2.35, 1.30])
solver.against_wall(mirror[0], walls[1])
solver.distance_constraint(mirror[0], mirror_anchor, 0, 0, weight=10)
solver.point_towards(mirror[0], room_center)

decoration_D[0].position = [0.085, 1.30, 1.45]
decoration_D[0].rotation = [0, 0, 0]
decoration_D_anchor = AssetInstance(position=[0.085, 1.30, 1.45])
solver.against_wall(decoration_D[0], walls[1])
solver.distance_constraint(decoration_D[0], decoration_D_anchor, 0, 0, weight=10)
solver.point_towards(decoration_D[0], room_center)

solver.constraints = []
lamp[0].position = [1.350000023841858, 0.6000000238418579, 0.8600000143051147]
lamp[0].rotation = [0, 0, 1.5935863729448736]
lamp[0].optimize = 2
globe[0].position = [3.4800000190734863, 1.840000033378601, 1.0299999713897705]
globe[0].rotation = [0, 0, -3.118801930015634]
globe[0].optimize = 2
decoration_C[0].position = [3.4800000190734863, 1.2999999523162842, 1.0099999904632568]
decoration_C[0].rotation = [0, 0, -3.118801930015634]
decoration_C[0].optimize = 2
decoration_B[0].position = [0.04500076174736023, 3.54003643989563, 0.30000001192092896]
decoration_B[0].rotation = [0, 0, 0.022791509970920977]
decoration_B[0].optimize = 2
cabinet[0].position = [3.5481209754943848, 3.9000000953674316, 0.38999998569488525]
cabinet[0].rotation = [0, 0, -3.1266087393606927]
cabinet[0].optimize = 2
bed[0].position = [1.8799999952316284, 3.7952518463134766, 0.4950000047683716]
bed[0].rotation = [0, 0, -1.5464791378616152]
bed[0].optimize = 2
dresser[0].position = [3.4995765686035156, 1.4500000476837158, 0.4099999964237213]
dresser[0].rotation = [0, 0, -3.114164176491425]
dresser[0].optimize = 2
carpet_A[0].position = [1.8799999952316284, 3.6266937255859375, 0.009999999776482582]
carpet_A[0].rotation = [0, 0, 0.022790561024514572]
carpet_A[0].optimize = 2
pillow[0].position = [1.8799999952316284, 4.28000020980835, 1.0500000715255737]
pillow[0].rotation = [0, 0, -1.548005765770382]
pillow[0].optimize = 2
decoration_D[0].position = [0.09040917456150055, 1.290378212928772, 0.3499999940395355]
decoration_D[0].rotation = [0, 0, 0.022791511342743993]
decoration_D[0].optimize = 2
carpet_B[0].position = [1.350000023841858, 0.75, 0.009999999776482582]
carpet_B[0].rotation = [0, 0, 1.5999304272152877]
carpet_B[0].optimize = 2
vase[0].position = [3.4800000190734863, 1.5399999618530273, 0.9900000095367432]
vase[0].rotation = [0, 0, -3.118801930015634]
vase[0].optimize = 2
seat_B[0].position = [2.0999999046325684, 0.6000000238418579, 0.4399999976158142]
seat_B[0].rotation = [0, 0, 1.656317458744293]
seat_B[0].optimize = 2
candle[0].position = [3.4800000190734863, 4.099999904632568, 0.8700000047683716]
candle[0].rotation = [0, 0, -3.118803053451712]
candle[0].optimize = 2
seat_A[0].position = [0.6000000238418579, 0.6000000238418579, 0.4399999976158142]
seat_A[0].rotation = [0, 0, 1.2025318668606495]
seat_A[0].optimize = 2
decoration_A[0].position = [3.4800000190734863, 3.700000047683716, 1.0049999952316284]
decoration_A[0].rotation = [0, 0, -3.118803053451712]
decoration_A[0].optimize = 2
casket[0].position = [3.4800000190734863, 0.9399999976158142, 0.9300000071525574]
casket[0].rotation = [0, 0, -3.118801930015634]
casket[0].optimize = 2
mirror[0].position = [0.0749996155500412, 2.3599815368652344, 0.5249999761581421]
mirror[0].rotation = [0, 0, 0.02279152196309187]
mirror[0].optimize = 2
case[0].position = [1.350000023841858, 0.6000000238418579, 0.29500001668930054]
case[0].rotation = [0, 0, 1.5990706612064889]
case[0].optimize = 2

