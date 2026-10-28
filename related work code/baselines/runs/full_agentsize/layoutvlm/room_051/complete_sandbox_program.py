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
    Wall(corner1=[5.52, 1.02, 0.00], corner2=[4.74, 1.02, 0.00]),
    Wall(corner1=[4.74, 1.02, 0.00], corner2=[4.74, 1.14, 0.00]),
    Wall(corner1=[4.74, 1.14, 0.00], corner2=[4.74, 3.06, 0.00]),
    Wall(corner1=[4.74, 3.06, 0.00], corner2=[0.62, 3.06, 0.00]),
    Wall(corner1=[0.62, 3.06, 0.00], corner2=[0.62, 2.42, 0.00]),
    Wall(corner1=[0.62, 2.42, 0.00], corner2=[0.38, 2.42, 0.00]),
    Wall(corner1=[0.38, 2.42, 0.00], corner2=[0.00, 2.42, 0.00]),
    Wall(corner1=[0.00, 2.42, 0.00], corner2=[0.00, 0.72, 0.00]),
    Wall(corner1=[0.00, 0.72, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[5.52, 0.00, 0.00]),
    Wall(corner1=[5.52, 0.00, 0.00], corner2=[5.52, 0.07, 0.00]),
    Wall(corner1=[5.52, 0.07, 0.00], corner2=[5.52, 0.92, 0.00]),
    Wall(corner1=[5.52, 0.92, 0.00], corner2=[5.52, 1.02, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
clock = Assets(description="clock", size=[0.05, 0.30, 0.30], placements=[AssetInstance() for _ in range(1)])
ornament_A = Assets(description="ornament", size=[0.12, 0.18, 0.28], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="book", size=[0.16, 0.22, 0.03], placements=[AssetInstance() for _ in range(1)])
chair = Assets(description="chair", size=[0.58, 0.55, 0.85], placements=[AssetInstance() for _ in range(1)])
bed_combination = Assets(description="bed combination", size=[2.10, 1.80, 1.10], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="book", size=[0.17, 0.24, 0.04], placements=[AssetInstance() for _ in range(1)])
book_C = Assets(description="book", size=[0.15, 0.21, 0.03], placements=[AssetInstance() for _ in range(1)])
book_D = Assets(description="book", size=[0.16, 0.23, 0.03], placements=[AssetInstance() for _ in range(1)])
ornament_B = Assets(description="ornament", size=[0.14, 0.16, 0.25], placements=[AssetInstance() for _ in range(1)])
bedside_table_A = Assets(description="bedside table", size=[0.42, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
book_E = Assets(description="book", size=[0.14, 0.20, 0.03], placements=[AssetInstance() for _ in range(1)])
book_F = Assets(description="book", size=[0.18, 0.25, 0.04], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[1.80, 2.60, 0.01], placements=[AssetInstance() for _ in range(1)])
book_G = Assets(description="book", size=[0.15, 0.22, 0.03], placements=[AssetInstance() for _ in range(1)])
bedside_table_B = Assets(description="bedside table", size=[0.42, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])

clock[0].instance_id = 'clock_0'
ornament_A[0].instance_id = 'ornament_A_0'
book_A[0].instance_id = 'book_A_0'
chair[0].instance_id = 'chair_0'
bed_combination[0].instance_id = 'bed_combination_0'
book_B[0].instance_id = 'book_B_0'
book_C[0].instance_id = 'book_C_0'
book_D[0].instance_id = 'book_D_0'
ornament_B[0].instance_id = 'ornament_B_0'
bedside_table_A[0].instance_id = 'bedside_table_A_0'
book_E[0].instance_id = 'book_E_0'
book_F[0].instance_id = 'book_F_0'
carpet[0].instance_id = 'carpet_0'
book_G[0].instance_id = 'book_G_0'
bedside_table_B[0].instance_id = 'bedside_table_B_0'
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

clock[0].position = [3.1073725108320844, 1.1147889305057144, 0.15]
clock[0].rotation = [0, 0, 0]
ornament_A[0].position = [4.192927901032594, 0.6155700423519314, 0.14]
ornament_A[0].rotation = [0, 0, 0]
book_A[0].position = [0.9506899312136422, 1.6183263741870004, 0.015]
book_A[0].rotation = [0, 0, 0]
chair[0].position = [1.285365654279945, 0.11045542324666763, 0.425]
chair[0].rotation = [0, 0, 0]
bed_combination[0].position = [1.033036972075042, 2.0298313082480095, 0.55]
bed_combination[0].rotation = [0, 0, 0]
book_B[0].position = [2.687200726363924, 2.20373125021294, 0.0175]
book_B[0].rotation = [0, 0, 0]
book_C[0].position = [0.8025412729915828, 0.46546141366471666, 0.015]
book_C[0].rotation = [0, 0, 0]
book_D[0].position = [1.3896264798086315, 2.62113779099745, 0.015]
book_D[0].rotation = [0, 0, 0]
ornament_B[0].position = [4.6452251272425, 0.5306966074658122, 0.125]
ornament_B[0].rotation = [0, 0, 0]
bedside_table_A[0].position = [1.410397773962018, 1.061535923638991, 0.275]
bedside_table_A[0].rotation = [0, 0, 0]
book_E[0].position = [4.6792924158575655, 0.3244111790168113, 0.0125]
book_E[0].rotation = [0, 0, 0]
book_F[0].position = [0.8070351666914792, 0.48268402221652384, 0.02]
book_F[0].rotation = [0, 0, 0]
carpet[0].position = [1.3183470457685642, 0.7042193830518564, 0.006]
carpet[0].rotation = [0, 0, 0]
book_G[0].position = [3.4318810837730225, 0.35219381184697346, 0.015]
book_G[0].rotation = [0, 0, 0]
bedside_table_B[0].position = [2.461302562141634, 1.942316102488807, 0.275]
bedside_table_B[0].rotation = [0, 0, 0]
clock[0].position = [3.1073725108320844, 1.1147889305057144, 0.15]
clock[0].rotation = [0, 0, 0]
ornament_A[0].position = [4.192927901032594, 0.6155700423519314, 0.14]
ornament_A[0].rotation = [0, 0, 0]
book_A[0].position = [0.9506899312136422, 1.6183263741870004, 0.015]
book_A[0].rotation = [0, 0, 0]
chair[0].position = [1.285365654279945, 0.11045542324666763, 0.425]
chair[0].rotation = [0, 0, 0]
bed_combination[0].position = [1.033036972075042, 2.0298313082480095, 0.55]
bed_combination[0].rotation = [0, 0, 0]
book_B[0].position = [2.687200726363924, 2.20373125021294, 0.0175]
book_B[0].rotation = [0, 0, 0]
book_C[0].position = [0.8025412729915828, 0.46546141366471666, 0.015]
book_C[0].rotation = [0, 0, 0]
book_D[0].position = [1.3896264798086315, 2.62113779099745, 0.015]
book_D[0].rotation = [0, 0, 0]
ornament_B[0].position = [4.6452251272425, 0.5306966074658122, 0.125]
ornament_B[0].rotation = [0, 0, 0]
bedside_table_A[0].position = [1.410397773962018, 1.061535923638991, 0.275]
bedside_table_A[0].rotation = [0, 0, 0]
book_E[0].position = [4.6792924158575655, 0.3244111790168113, 0.0125]
book_E[0].rotation = [0, 0, 0]
book_F[0].position = [0.8070351666914792, 0.48268402221652384, 0.02]
book_F[0].rotation = [0, 0, 0]
carpet[0].position = [1.3183470457685642, 0.7042193830518564, 0.006]
carpet[0].rotation = [0, 0, 0]
book_G[0].position = [3.4318810837730225, 0.35219381184697346, 0.015]
book_G[0].rotation = [0, 0, 0]
bedside_table_B[0].position = [2.461302562141634, 1.942316102488807, 0.275]
bedside_table_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the bed with its head against the upper wall. Rotating it 90 degrees
# makes its 2.10 m dimension extend into the room and leaves space on both sides.
bed_combination[0].position = [2.60, 2.01, 0.56]
bed_combination[0].rotation = [0, 0, radians(90)]

# Both tables sit beside the head of the bed with approximately 5 cm edge gaps.
# Their fronts face into the room, away from the upper wall.
bedside_table_A[0].position = [1.40, 2.85, 0.275]
bedside_table_A[0].rotation = [0, 0, radians(-90)]

bedside_table_B[0].position = [3.80, 2.85, 0.275]
bedside_table_B[0].rotation = [0, 0, radians(-90)]

# The rug is centered under the bed and extends toward the open foot of the bed.
carpet[0].position = [2.60, 1.50, 0.005]
carpet[0].rotation = [0, 0, 0]

# Place the chair in the clear lower-left area, outside the rug and away from
# the doorway at the lower-right side. It faces diagonally toward the bed.
chair[0].position = [0.95, 0.45, 0.425]
chair[0].rotation = [0, 0, radians(43)]

# Mount the clock on the upper wall, centered over the bed.
clock[0].position = [2.60, 3.035, 1.65]
clock[0].rotation = [0, 0, radians(-90)]

# Stack four books and an ornament on the left bedside table.
book_A[0].position = [1.40, 2.85, 0.565]
book_A[0].rotation = [0, 0, radians(-90)]

book_B[0].position = [1.40, 2.85, 0.600]
book_B[0].rotation = [0, 0, radians(-90)]

book_C[0].position = [1.40, 2.85, 0.635]
book_C[0].rotation = [0, 0, radians(-90)]

book_D[0].position = [1.40, 2.85, 0.665]
book_D[0].rotation = [0, 0, radians(-90)]

ornament_A[0].position = [1.40, 2.85, 0.820]
ornament_A[0].rotation = [0, 0, radians(-90)]

# Stack the remaining three books and ornament on the right bedside table.
book_E[0].position = [3.80, 2.85, 0.565]
book_E[0].rotation = [0, 0, radians(-90)]

book_F[0].position = [3.80, 2.85, 0.600]
book_F[0].rotation = [0, 0, radians(-90)]

book_G[0].position = [3.80, 2.85, 0.635]
book_G[0].rotation = [0, 0, radians(-90)]

ornament_B[0].position = [3.80, 2.85, 0.775]
ornament_B[0].rotation = [0, 0, radians(-90)]


# Fixed-point constraints retain the collision-free arrangement around the two
# immovable wardrobes and keep the entire lower-right door approach clear.
def pin_position(instance, position, weight=10):
    solver.distance_constraint(
        instance,
        AssetInstance(position=position),
        0,
        0,
        weight=weight,
    )


# Main furniture constraints are listed first because they determine the room's
# functional circulation and the required bed/table relationship.
pin_position(bed_combination[0], [2.60, 2.01, 0.56])
solver.against_wall(bed_combination[0], walls[3])
solver.align_with(bed_combination[0], carpet[0], angle=90)
solver.on_top_of(bed_combination[0], carpet[0])

pin_position(bedside_table_A[0], [1.40, 2.85, 0.275])
solver.against_wall(bedside_table_A[0], walls[3])
solver.align_with(bedside_table_A[0], clock[0])
# This center-distance range corresponds to an approximately 5 cm horizontal
# edge gap while accounting for the objects' different center heights.
solver.distance_constraint(
    bedside_table_A[0], bed_combination[0], 1.44, 1.54, weight=10
)

pin_position(bedside_table_B[0], [3.80, 2.85, 0.275])
solver.against_wall(bedside_table_B[0], walls[3])
solver.align_with(bedside_table_B[0], bedside_table_A[0])
solver.distance_constraint(
    bedside_table_B[0], bed_combination[0], 1.44, 1.54, weight=10
)

pin_position(carpet[0], [2.60, 1.50, 0.005])
solver.align_with(carpet[0], bedside_table_A[0], angle=90)

pin_position(chair[0], [0.95, 0.45, 0.425])
solver.point_towards(chair[0], bed_combination[0])

pin_position(clock[0], [2.60, 3.035, 1.65])
solver.against_wall(clock[0], walls[3])
solver.point_towards(clock[0], bed_combination[0])


# Left-table stack: every small object has an explicit position constraint,
# an orientation constraint, and a support constraint.
pin_position(book_A[0], [1.40, 2.85, 0.565])
solver.align_with(book_A[0], bedside_table_A[0])
solver.on_top_of(book_A[0], bedside_table_A[0])

pin_position(book_B[0], [1.40, 2.85, 0.600])
solver.align_with(book_B[0], book_A[0])
solver.on_top_of(book_B[0], book_A[0])

pin_position(book_C[0], [1.40, 2.85, 0.635])
solver.align_with(book_C[0], book_B[0])
solver.on_top_of(book_C[0], book_B[0])

pin_position(book_D[0], [1.40, 2.85, 0.665])
solver.align_with(book_D[0], book_C[0])
solver.on_top_of(book_D[0], book_C[0])

pin_position(ornament_A[0], [1.40, 2.85, 0.820])
solver.align_with(ornament_A[0], book_D[0])
solver.on_top_of(ornament_A[0], book_D[0])


# Right-table stack.
pin_position(book_E[0], [3.80, 2.85, 0.565])
solver.align_with(book_E[0], bedside_table_B[0])
solver.on_top_of(book_E[0], bedside_table_B[0])

pin_position(book_F[0], [3.80, 2.85, 0.600])
solver.align_with(book_F[0], book_E[0])
solver.on_top_of(book_F[0], book_E[0])

pin_position(book_G[0], [3.80, 2.85, 0.635])
solver.align_with(book_G[0], book_F[0])
solver.on_top_of(book_G[0], book_F[0])

pin_position(ornament_B[0], [3.80, 2.85, 0.775])
solver.align_with(ornament_B[0], book_G[0])
solver.on_top_of(ornament_B[0], book_G[0])

solver.constraints = []
book_F[0].position = [3.612352132797241, 2.6024417877197266, 0.5999999642372131]
book_F[0].rotation = [0, 0, -1.5707966119571797]
book_F[0].optimize = 2
book_B[0].position = [1.399999976158142, 2.8499999046325684, 0.5999999642372131]
book_B[0].rotation = [0, 0, -1.5707961777650292]
book_B[0].optimize = 2
ornament_A[0].position = [1.399999976158142, 2.8499999046325684, 0.8199998736381531]
ornament_A[0].rotation = [0, 0, -1.570784326083746]
ornament_A[0].optimize = 2
bed_combination[0].position = [1.9523837566375732, 1.3465930223464966, 0.5600000023841858]
bed_combination[0].rotation = [0, 0, -1.2312248459600712]
bed_combination[0].optimize = 2
book_G[0].position = [3.737352132797241, 2.692441701889038, 0.6349999308586121]
book_G[0].rotation = [0, 0, -1.570794079668586]
book_G[0].optimize = 2
bedside_table_A[0].position = [1.399999976158142, 2.8500001430511475, 0.2750000059604645]
bedside_table_A[0].rotation = [0, 0, -1.5707963468911064]
bedside_table_A[0].optimize = 2
bedside_table_B[0].position = [3.262352228164673, 2.322441816329956, 0.2750000059604645]
bedside_table_B[0].rotation = [0, 0, -1.5707962602903764]
bedside_table_B[0].optimize = 2
book_D[0].position = [1.399999976158142, 2.8499999046325684, 0.6649999022483826]
book_D[0].rotation = [0, 0, -1.5707956467596549]
book_D[0].optimize = 2
carpet[0].position = [2.5999999046325684, 1.5, 0.004999999888241291]
carpet[0].rotation = [0, 0, 2.8781327622634156e-07]
carpet[0].optimize = 2
book_E[0].position = [3.512352228164673, 2.5324418544769287, 0.5649999976158142]
book_E[0].rotation = [0, 0, -1.5707962852330062]
book_E[0].optimize = 2
ornament_B[0].position = [3.8000001907348633, 2.767441987991333, 0.7749999165534973]
ornament_B[0].rotation = [0, 0, -1.5707973387205758]
ornament_B[0].optimize = 2
chair[0].position = [0.949999988079071, 0.44999998807907104, 0.42500001192092896]
chair[0].rotation = [0, 0, 0.7599163717939723]
chair[0].optimize = 2
book_A[0].position = [1.399999976158142, 2.8499999046325684, 0.5649999976158142]
book_A[0].rotation = [0, 0, -1.5707960229539533]
book_A[0].optimize = 2
book_C[0].position = [1.399999976158142, 2.8499999046325684, 0.6349999308586121]
book_C[0].rotation = [0, 0, -1.570797629444687]
book_C[0].optimize = 2
clock[0].position = [2.5999999046325684, 3.0349998474121094, 0.15000000596046448]
clock[0].rotation = [0, 0, -1.5707962411214902]
clock[0].optimize = 2

