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
    Wall(corner1=[0.00, 5.78, 0.00], corner2=[0.00, 3.80, 0.00]),
    Wall(corner1=[0.00, 3.80, 0.00], corner2=[1.74, 3.80, 0.00]),
    Wall(corner1=[1.74, 3.80, 0.00], corner2=[1.74, 0.00, 0.00]),
    Wall(corner1=[1.74, 0.00, 0.00], corner2=[6.60, 0.00, 0.00]),
    Wall(corner1=[6.60, 0.00, 0.00], corner2=[6.60, 3.45, 0.00]),
    Wall(corner1=[6.60, 3.45, 0.00], corner2=[7.70, 3.45, 0.00]),
    Wall(corner1=[7.70, 3.45, 0.00], corner2=[7.70, 4.90, 0.00]),
    Wall(corner1=[7.70, 4.90, 0.00], corner2=[6.80, 4.90, 0.00]),
    Wall(corner1=[6.80, 4.90, 0.00], corner2=[6.80, 4.83, 0.00]),
    Wall(corner1=[6.80, 4.83, 0.00], corner2=[3.46, 4.83, 0.00]),
    Wall(corner1=[3.46, 4.83, 0.00], corner2=[3.46, 4.92, 0.00]),
    Wall(corner1=[3.46, 4.92, 0.00], corner2=[0.99, 4.92, 0.00]),
    Wall(corner1=[0.99, 4.92, 0.00], corner2=[0.99, 5.78, 0.00]),
    Wall(corner1=[0.99, 5.78, 0.00], corner2=[0.00, 5.78, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
coffee_table = Assets(description="coffee table", size=[0.65, 1.20, 0.42], placements=[AssetInstance() for _ in range(1)])
tv_cabinet_A = Assets(description="tv cabinet", size=[0.40, 1.80, 0.55], placements=[AssetInstance() for _ in range(1)])
air_conditioner = Assets(description="air conditioner", size=[0.23, 0.90, 0.30], placements=[AssetInstance() for _ in range(1)])
tv_cabinet_B = Assets(description="tv cabinet", size=[0.45, 2.00, 0.50], placements=[AssetInstance() for _ in range(1)])
sofa = Assets(description="sofa", size=[0.95, 2.60, 0.85], placements=[AssetInstance() for _ in range(1)])
ornaments_A = Assets(description="ornaments", size=[0.16, 0.20, 0.30], placements=[AssetInstance() for _ in range(1)])
ornaments_B = Assets(description="ornaments", size=[0.18, 0.25, 0.22], placements=[AssetInstance() for _ in range(1)])

coffee_table[0].instance_id = 'coffee_table_0'
tv_cabinet_A[0].instance_id = 'tv_cabinet_A_0'
air_conditioner[0].instance_id = 'air_conditioner_0'
tv_cabinet_B[0].instance_id = 'tv_cabinet_B_0'
sofa[0].instance_id = 'sofa_0'
ornaments_A[0].instance_id = 'ornaments_A_0'
ornaments_B[0].instance_id = 'ornaments_B_0'
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
walls[13].instance_id = 'walls_13'

coffee_table[0].position = [0.867987571465427, 4.753990466905209, 0.21]
coffee_table[0].rotation = [0, 0, 0]
tv_cabinet_A[0].position = [4.464877456212142, 0.5357572469458691, 0.275]
tv_cabinet_A[0].rotation = [0, 0, 0]
air_conditioner[0].position = [5.001549693873813, 3.123989976097162, 0.15]
air_conditioner[0].rotation = [0, 0, 0]
tv_cabinet_B[0].position = [3.434144002339252, 4.902707343212349, 0.25]
tv_cabinet_B[0].rotation = [0, 0, 0]
sofa[0].position = [5.117726674434498, 0.6321146745624303, 0.425]
sofa[0].rotation = [0, 0, 0]
ornaments_A[0].position = [5.869499802405546, 2.0854964462316388, 0.15]
ornaments_A[0].rotation = [0, 0, 0]
ornaments_B[0].position = [5.172138523469212, 4.034511893958561, 0.11]
ornaments_B[0].rotation = [0, 0, 0]
coffee_table[0].position = [0.867987571465427, 4.753990466905209, 0.21]
coffee_table[0].rotation = [0, 0, 0]
tv_cabinet_A[0].position = [4.464877456212142, 0.5357572469458691, 0.275]
tv_cabinet_A[0].rotation = [0, 0, 0]
air_conditioner[0].position = [5.001549693873813, 3.123989976097162, 0.15]
air_conditioner[0].rotation = [0, 0, 0]
tv_cabinet_B[0].position = [3.434144002339252, 4.902707343212349, 0.25]
tv_cabinet_B[0].rotation = [0, 0, 0]
sofa[0].position = [5.117726674434498, 0.6321146745624303, 0.425]
sofa[0].rotation = [0, 0, 0]
ornaments_A[0].position = [5.869499802405546, 2.0854964462316388, 0.15]
ornaments_A[0].rotation = [0, 0, 0]
ornaments_B[0].position = [5.172138523469212, 4.034511893958561, 0.11]
ornaments_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the actual boundary coordinates: the main room lies between
# x=1.74 and x=6.60. Keep the northern recesses open for circulation.
# Asset order identifies tv_cabinet_A as o0001 and tv_cabinet_B as o0003.

# Main seating group: the sofa faces east toward cabinet B.
sofa[0].position = [2.45, 1.90, 0.425]
sofa[0].rotation = [0, 0, 0]

tv_cabinet_B[0].position = [6.375, 1.90, 0.25]
tv_cabinet_B[0].rotation = [0, 0, radians(180)]

coffee_table[0].position = [4.05, 1.90, 0.21]
coffee_table[0].rotation = [0, 0, 0]

# Cabinet A backs onto the northern wall, with its long dimension
# running along that wall and its front facing south.
tv_cabinet_A[0].position = [5.10, 4.63, 0.275]
tv_cabinet_A[0].rotation = [0, 0, radians(270)]

# This is a wall-mounted air conditioner, not a floor-standing object.
# Its elevation is maintained by a fixed-height position constraint.
air_conditioner[0].position = [1.855, 3.25, 2.35]
air_conditioner[0].rotation = [0, 0, 0]

# Place the decorative objects fully within the cabinet tops.
ornaments_A[0].position = [5.55, 4.63, 0.70]
ornaments_A[0].rotation = [0, 0, radians(270)]

ornaments_B[0].position = [6.375, 2.55, 0.61]
ornaments_B[0].rotation = [0, 0, radians(180)]

# Prioritize required wall contact and viewing directions.
solver.against_wall(tv_cabinet_A[0], walls[9])
solver.against_wall(tv_cabinet_B[0], walls[4])
solver.point_towards(sofa[0], tv_cabinet_B[0])
solver.point_towards(tv_cabinet_B[0], sofa[0])
solver.align_with(tv_cabinet_A[0], AssetInstance(rotation=[0, 0, radians(270)]))
solver.align_with(coffee_table[0], sofa[0])

# Anchor the principal furniture to the selected clear, nonoverlapping
# locations. Matching anchor heights makes these true 3D center constraints.
solver.distance_constraint(
    sofa[0], AssetInstance(position=[2.45, 1.90, 0.425]),
    0, 0, weight=10
)
solver.distance_constraint(
    tv_cabinet_B[0], AssetInstance(position=[6.375, 1.90, 0.25]),
    0, 0, weight=10
)
solver.distance_constraint(
    tv_cabinet_A[0], AssetInstance(position=[5.10, 4.63, 0.275]),
    0, 0, weight=10
)
solver.distance_constraint(
    coffee_table[0], AssetInstance(position=[4.05, 1.90, 0.21]),
    0, 0, weight=10
)

# Preserve comfortable separation around the coffee table; distances
# account for the different bounding-box center heights.
solver.distance_constraint(
    coffee_table[0], sofa[0],
    (1.60**2 + 0.215**2)**0.5, 1.85
)
solver.distance_constraint(
    coffee_table[0], tv_cabinet_B[0],
    (2.325**2 + 0.04**2)**0.5, 2.55
)

# Wall-mounted equipment remains above the floor and clear of the sofa.
solver.against_wall(air_conditioner[0], walls[2])
solver.distance_constraint(
    air_conditioner[0], AssetInstance(position=[1.855, 3.25, 2.35]),
    0, 0, weight=10
)
solver.align_with(air_conditioner[0], sofa[0])

# Surface support, position, and orientation constraints for each ornament.
solver.on_top_of(ornaments_A[0], tv_cabinet_A[0])
solver.distance_constraint(
    ornaments_A[0], AssetInstance(position=[5.55, 4.63, 0.70]),
    0, 0, weight=10
)
solver.align_with(ornaments_A[0], tv_cabinet_A[0])

solver.on_top_of(ornaments_B[0], tv_cabinet_B[0])
solver.distance_constraint(
    ornaments_B[0], AssetInstance(position=[6.375, 2.55, 0.61]),
    0, 0, weight=10
)
solver.align_with(ornaments_B[0], tv_cabinet_B[0])

solver.constraints = []
sofa[0].position = [2.450000047683716, 1.899999976158142, 0.42500001192092896]
sofa[0].rotation = [0, 0, 0.021991148286022624]
sofa[0].optimize = 2
tv_cabinet_B[0].position = [6.378495693206787, 1.899999976158142, 0.25]
tv_cabinet_B[0].rotation = [0, 0, 3.140761315791322]
tv_cabinet_B[0].optimize = 2
tv_cabinet_A[0].position = [5.099999904632568, 4.620431423187256, 0.2750000059604645]
tv_cabinet_A[0].rotation = [0, 0, -1.5655042890077557]
tv_cabinet_A[0].optimize = 2
ornaments_B[0].position = [6.375, 2.549999952316284, 0.6100000143051147]
ornaments_B[0].rotation = [0, 0, 3.1158429618508032]
ornaments_B[0].optimize = 2
coffee_table[0].position = [4.072666645050049, 1.899999976158142, 0.20999999344348907]
coffee_table[0].rotation = [0, 0, 0.024753659037385373]
coffee_table[0].optimize = 2
air_conditioner[0].position = [1.8503373861312866, 3.25, 0.15000000596046448]
air_conditioner[0].rotation = [0, 0, 0.004216023245092528]
air_conditioner[0].optimize = 2
ornaments_A[0].position = [5.550000190734863, 4.630000114440918, 0.7000000476837158]
ornaments_A[0].rotation = [0, 0, -1.5888408992638545]
ornaments_A[0].optimize = 2

