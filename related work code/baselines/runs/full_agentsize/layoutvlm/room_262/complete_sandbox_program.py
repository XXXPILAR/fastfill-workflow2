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
    Wall(corner1=[6.96, 6.49, 0.00], corner2=[0.00, 6.49, 0.00]),
    Wall(corner1=[0.00, 6.49, 0.00], corner2=[0.00, 4.98, 0.00]),
    Wall(corner1=[0.00, 4.98, 0.00], corner2=[0.40, 4.97, 0.00]),
    Wall(corner1=[0.40, 4.97, 0.00], corner2=[0.40, 4.74, 0.00]),
    Wall(corner1=[0.40, 4.74, 0.00], corner2=[0.00, 4.74, 0.00]),
    Wall(corner1=[0.00, 4.74, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.82, 0.03, 0.00]),
    Wall(corner1=[2.82, 0.03, 0.00], corner2=[2.82, 0.44, 0.00]),
    Wall(corner1=[2.82, 0.44, 0.00], corner2=[6.42, 0.44, 0.00]),
    Wall(corner1=[6.42, 0.44, 0.00], corner2=[6.44, 4.98, 0.00]),
    Wall(corner1=[6.44, 4.98, 0.00], corner2=[6.96, 4.98, 0.00]),
    Wall(corner1=[6.96, 4.98, 0.00], corner2=[6.96, 6.49, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
lighting_A = Assets(description="lighting", size=[0.35, 0.35, 1.65], placements=[AssetInstance() for _ in range(1)])
lighting_B = Assets(description="lighting", size=[0.30, 0.30, 1.55], placements=[AssetInstance() for _ in range(1)])
lighting_C = Assets(description="lighting", size=[0.28, 0.28, 1.50], placements=[AssetInstance() for _ in range(1)])
lighting_D = Assets(description="lighting", size=[0.30, 0.30, 1.55], placements=[AssetInstance() for _ in range(1)])
lighting_E = Assets(description="lighting", size=[0.30, 0.30, 1.55], placements=[AssetInstance() for _ in range(1)])
bookcase_A = Assets(description="bookcase", size=[0.35, 1.20, 2.00], placements=[AssetInstance() for _ in range(1)])
dining_table_combination = Assets(description="dining table combination", size=[1.80, 2.40, 0.90], placements=[AssetInstance() for _ in range(1)])
bookcase_B = Assets(description="bookcase", size=[0.35, 1.20, 2.00], placements=[AssetInstance() for _ in range(1)])

lighting_A[0].instance_id = 'lighting_A_0'
lighting_B[0].instance_id = 'lighting_B_0'
lighting_C[0].instance_id = 'lighting_C_0'
lighting_D[0].instance_id = 'lighting_D_0'
lighting_E[0].instance_id = 'lighting_E_0'
bookcase_A[0].instance_id = 'bookcase_A_0'
dining_table_combination[0].instance_id = 'dining_table_combination_0'
bookcase_B[0].instance_id = 'bookcase_B_0'
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

lighting_A[0].position = [3.2920894305019024, 5.750552769518591, 0.825]
lighting_A[0].rotation = [0, 0, 0]
lighting_B[0].position = [1.1983974097751533, 0.2530535052791104, 0.775]
lighting_B[0].rotation = [0, 0, 0]
lighting_C[0].position = [2.6722087584811156, 3.4764104821531863, 0.75]
lighting_C[0].rotation = [0, 0, 0]
lighting_D[0].position = [5.513569529209094, 5.4242009142694245, 0.775]
lighting_D[0].rotation = [0, 0, 0]
lighting_E[0].position = [2.7970003594710025, 3.1455054873366812, 0.775]
lighting_E[0].rotation = [0, 0, 0]
bookcase_A[0].position = [3.5868961059322984, 1.1919090772937129, 1.0]
bookcase_A[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [1.0139410859575269, 6.449238684093893, 0.45]
dining_table_combination[0].rotation = [0, 0, 0]
bookcase_B[0].position = [6.060799801934694, 1.2239004500305783, 1.0]
bookcase_B[0].rotation = [0, 0, 0]
lighting_A[0].position = [3.2920894305019024, 5.750552769518591, 0.825]
lighting_A[0].rotation = [0, 0, 0]
lighting_B[0].position = [1.1983974097751533, 0.2530535052791104, 0.775]
lighting_B[0].rotation = [0, 0, 0]
lighting_C[0].position = [2.6722087584811156, 3.4764104821531863, 0.75]
lighting_C[0].rotation = [0, 0, 0]
lighting_D[0].position = [5.513569529209094, 5.4242009142694245, 0.775]
lighting_D[0].rotation = [0, 0, 0]
lighting_E[0].position = [2.7970003594710025, 3.1455054873366812, 0.775]
lighting_E[0].rotation = [0, 0, 0]
bookcase_A[0].position = [3.5868961059322984, 1.1919090772937129, 1.0]
bookcase_A[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [1.0139410859575269, 6.449238684093893, 0.45]
dining_table_combination[0].rotation = [0, 0, 0]
bookcase_B[0].position = [6.060799801934694, 1.2239004500305783, 1.0]
bookcase_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Explicit initial placements. The central dining set stays well clear of both
# south-side door approaches, while the bookcases and lighting_A use perimeter
# space. The four related lights form the ordered row B--D--C--E, so C (o0002)
# is between both D/E and B/E.
lighting_A[0].position = [6.255, 1.55, 0.825]
lighting_A[0].rotation = [0, 0, 2.545]

lighting_B[0].position = [1.700, 5.70, 0.775]
lighting_B[0].rotation = [0, 0, -0.923]

lighting_C[0].position = [3.100, 5.70, 0.750]
lighting_C[0].rotation = [0, 0, -1.438]

lighting_D[0].position = [2.805, 5.70, 0.775]
lighting_D[0].rotation = [0, 0, -1.310]

lighting_E[0].position = [4.300, 5.70, 0.775]
lighting_E[0].rotation = [0, 0, -1.951]

bookcase_A[0].position = [0.175, 3.35, 1.00]
bookcase_A[0].rotation = [0, 0, 0]

dining_table_combination[0].position = [3.40, 3.45, 0.45]
dining_table_combination[0].rotation = [0, 0, radians(90)]

bookcase_B[0].position = [6.255, 3.35, 1.00]
bookcase_B[0].rotation = [0, 0, radians(180)]


# Fixed references retain the intended zones while allowing the solver to make
# small feasibility adjustments. They are not additional scene assets.
lighting_A_anchor = AssetInstance(position=[6.255, 1.55, 0.825])
lighting_B_anchor = AssetInstance(position=[1.700, 5.70, 0.775])
lighting_C_anchor = AssetInstance(position=[3.100, 5.70, 0.750])
lighting_D_anchor = AssetInstance(position=[2.805, 5.70, 0.775])
lighting_E_anchor = AssetInstance(position=[4.300, 5.70, 0.775])
bookcase_A_anchor = AssetInstance(position=[0.175, 3.35, 1.00])
dining_anchor = AssetInstance(
    position=[3.40, 3.45, 0.45],
    rotation=[0, 0, radians(90)],
)
bookcase_B_anchor = AssetInstance(position=[6.255, 3.35, 1.00])


# Highest-priority semantic constraints establish the required B--D--C--E
# ordering. D and C are 0.296 m apart center-to-center, satisfying the
# "within 0.30 m" requirement while leaving a small footprint gap.
solver.distance_constraint(
    lighting_D[0], lighting_C[0], 0.296, 0.300, weight=10
)
solver.distance_constraint(
    lighting_C[0], lighting_E[0], 1.19, 1.21, weight=10
)
solver.distance_constraint(
    lighting_D[0], lighting_E[0], 1.49, 1.50, weight=10
)
solver.distance_constraint(
    lighting_B[0], lighting_C[0], 1.39, 1.41, weight=10
)
solver.distance_constraint(
    lighting_B[0], lighting_E[0], 2.59, 2.61, weight=10
)

# lighting_A (o0000) is placed against the long right-hand wall.
solver.against_wall(lighting_A[0], walls[9])

# Both shallow bookcases are secured against opposite side walls, with their
# fronts directed into the room.
solver.against_wall(bookcase_A[0], walls[5])
solver.against_wall(bookcase_B[0], walls[9])

# Position constraints for every new instance preserve clear circulation and
# keep the dining set away from the two doors along the south boundary.
solver.distance_constraint(
    lighting_A[0], lighting_A_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    lighting_B[0], lighting_B_anchor, 0, 0, weight=5
)
solver.distance_constraint(
    lighting_C[0], lighting_C_anchor, 0, 0, weight=5
)
solver.distance_constraint(
    lighting_D[0], lighting_D_anchor, 0, 0, weight=5
)
solver.distance_constraint(
    lighting_E[0], lighting_E_anchor, 0, 0, weight=5
)
solver.distance_constraint(
    bookcase_A[0], bookcase_A_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    dining_table_combination[0], dining_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    bookcase_B[0], bookcase_B_anchor, 0, 0, weight=10
)

# Orient the perimeter pieces and all lights toward the dining area. This gives
# every instance an orientation-based constraint and keeps bookcase fronts
# accessible from the room.
solver.point_towards(lighting_A[0], dining_table_combination[0])
solver.point_towards(lighting_B[0], dining_table_combination[0])
solver.point_towards(lighting_C[0], dining_table_combination[0])
solver.point_towards(lighting_D[0], dining_table_combination[0])
solver.point_towards(lighting_E[0], dining_table_combination[0])
solver.point_towards(bookcase_A[0], dining_table_combination[0])
solver.point_towards(bookcase_B[0], dining_table_combination[0])

# Keep the long axis of the dining combination north-south.
solver.align_with(dining_table_combination[0], dining_anchor)

solver.constraints = []
bookcase_B[0].position = [6.2590436935424805, 3.3460426330566406, 1.0]
bookcase_B[0].rotation = [0, 0, 3.1379482600002193]
bookcase_B[0].optimize = 2
lighting_B[0].position = [1.7000000476837158, 5.699999809265137, 0.7749999761581421]
lighting_B[0].rotation = [0, 0, -0.9072920191504615]
lighting_B[0].optimize = 2
lighting_E[0].position = [4.300000190734863, 5.699999809265137, 0.7749999761581421]
lighting_E[0].rotation = [0, 0, -1.9321504387500235]
lighting_E[0].optimize = 2
lighting_A[0].position = [6.252254962921143, 1.483237385749817, 0.824999988079071]
lighting_A[0].rotation = [0, 0, 3.137948202257686]
lighting_A[0].optimize = 2
dining_table_combination[0].position = [3.4000000953674316, 3.450000047683716, 0.44999998807907104]
dining_table_combination[0].rotation = [0, 0, 1.6022122525607134]
dining_table_combination[0].optimize = 2
lighting_C[0].position = [3.0999999046325684, 5.699999809265137, 0.75]
lighting_C[0].rotation = [0, 0, -1.4191504400281754]
lighting_C[0].optimize = 2
bookcase_A[0].position = [0.17488761246204376, 5.263148784637451, 1.0]
bookcase_A[0].rotation = [0, 0, -0.00997676583792855]
bookcase_A[0].optimize = 2
lighting_D[0].position = [2.801088333129883, 5.699999809265137, 0.7749999761581421]
lighting_D[0].rotation = [0, 0, -1.2942920350680673]
lighting_D[0].optimize = 2

