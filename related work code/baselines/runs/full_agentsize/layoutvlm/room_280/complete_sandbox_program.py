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
    Wall(corner1=[0.00, 1.49, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[8.60, 0.00, 0.00]),
    Wall(corner1=[8.60, 0.00, 0.00], corner2=[8.60, 3.71, 0.00]),
    Wall(corner1=[8.60, 3.71, 0.00], corner2=[5.14, 3.71, 0.00]),
    Wall(corner1=[5.14, 3.71, 0.00], corner2=[5.14, 5.38, 0.00]),
    Wall(corner1=[5.14, 5.38, 0.00], corner2=[4.19, 5.38, 0.00]),
    Wall(corner1=[4.19, 5.38, 0.00], corner2=[4.19, 3.71, 0.00]),
    Wall(corner1=[4.19, 3.71, 0.00], corner2=[1.39, 3.71, 0.00]),
    Wall(corner1=[1.39, 3.71, 0.00], corner2=[1.39, 2.04, 0.00]),
    Wall(corner1=[1.39, 2.04, 0.00], corner2=[1.11, 2.04, 0.00]),
    Wall(corner1=[1.11, 2.04, 0.00], corner2=[1.11, 1.49, 0.00]),
    Wall(corner1=[1.11, 1.49, 0.00], corner2=[0.00, 1.49, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
chair = Assets(description="chair", size=[0.82, 0.75, 0.88], placements=[AssetInstance() for _ in range(1)])
table_A = Assets(description="table", size=[0.90, 1.80, 0.76], placements=[AssetInstance() for _ in range(1)])
sofa_A = Assets(description="sofa", size=[0.95, 2.25, 0.85], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.45, 1.60, 0.82], placements=[AssetInstance() for _ in range(1)])
table_B = Assets(description="table", size=[0.55, 0.55, 0.58], placements=[AssetInstance() for _ in range(1)])
sofa_B = Assets(description="sofa", size=[1.00, 2.40, 0.86], placements=[AssetInstance() for _ in range(1)])
table_C = Assets(description="table", size=[0.55, 0.55, 0.58], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.45, 2.00, 0.70], placements=[AssetInstance() for _ in range(1)])
table_D = Assets(description="table", size=[0.65, 1.20, 0.42], placements=[AssetInstance() for _ in range(1)])

chair[0].instance_id = 'chair_0'
table_A[0].instance_id = 'table_A_0'
sofa_A[0].instance_id = 'sofa_A_0'
cabinet_A[0].instance_id = 'cabinet_A_0'
table_B[0].instance_id = 'table_B_0'
sofa_B[0].instance_id = 'sofa_B_0'
table_C[0].instance_id = 'table_C_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
table_D[0].instance_id = 'table_D_0'
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

chair[0].position = [6.007251053942677, 3.4340611661820426, 0.44]
chair[0].rotation = [0, 0, 0]
table_A[0].position = [8.466777501608632, 2.492356577440913, 0.38]
table_A[0].rotation = [0, 0, 0]
sofa_A[0].position = [3.8951662845512534, 0.5491467841970973, 0.425]
sofa_A[0].rotation = [0, 0, 0]
cabinet_A[0].position = [3.7794988665281375, 0.8589812495424263, 0.41]
cabinet_A[0].rotation = [0, 0, 0]
table_B[0].position = [7.027945483007791, 0.5738376864787553, 0.29]
table_B[0].rotation = [0, 0, 0]
sofa_B[0].position = [7.58745159890502, 0.311063286522428, 0.43]
sofa_B[0].rotation = [0, 0, 0]
table_C[0].position = [4.148574580033876, 1.8499810615478895, 0.29]
table_C[0].rotation = [0, 0, 0]
cabinet_B[0].position = [3.677636713195155, 1.0043394987277556, 0.35]
cabinet_B[0].rotation = [0, 0, 0]
table_D[0].position = [1.4969964890116312, 3.2810861111291443, 0.21]
table_D[0].rotation = [0, 0, 0]
chair[0].position = [6.007251053942677, 3.4340611661820426, 0.44]
chair[0].rotation = [0, 0, 0]
table_A[0].position = [8.466777501608632, 2.492356577440913, 0.38]
table_A[0].rotation = [0, 0, 0]
sofa_A[0].position = [3.8951662845512534, 0.5491467841970973, 0.425]
sofa_A[0].rotation = [0, 0, 0]
cabinet_A[0].position = [3.7794988665281375, 0.8589812495424263, 0.41]
cabinet_A[0].rotation = [0, 0, 0]
table_B[0].position = [7.027945483007791, 0.5738376864787553, 0.29]
table_B[0].rotation = [0, 0, 0]
sofa_B[0].position = [7.58745159890502, 0.311063286522428, 0.43]
sofa_B[0].rotation = [0, 0, 0]
table_C[0].position = [4.148574580033876, 1.8499810615478895, 0.29]
table_C[0].rotation = [0, 0, 0]
cabinet_B[0].position = [3.677636713195155, 1.0043394987277556, 0.35]
cabinet_B[0].rotation = [0, 0, 0]
table_D[0].position = [1.4969964890116312, 3.2810861111291443, 0.21]
table_D[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed target points preserve the proposed functional layout while still allowing
# the solver to make small feasibility adjustments through the semantic constraints.
chair_target = AssetInstance(position=[3.00, 1.75, 0.44])
table_A_target = AssetInstance(position=[4.95, 1.55, 0.38])
sofa_A_target = AssetInstance(position=[3.30, 3.15, 0.425])
cabinet_A_target = AssetInstance(position=[4.55, 0.225, 0.41])
table_B_target = AssetInstance(position=[2.00, 1.75, 0.29])
sofa_B_target = AssetInstance(position=[6.50, 3.21, 0.43])
table_C_target = AssetInstance(position=[4.00, 1.75, 0.29])
cabinet_B_target = AssetInstance(position=[6.65, 0.225, 0.35])
table_D_target = AssetInstance(position=[6.50, 2.20, 0.21])

# Initial placements:
# - The two small tables flank the chair, satisfying the required ordering.
# - The large sofas and coffee table form seating zones in the upper half.
# - Both cabinets use the unobstructed part of the bottom wall.
# - The right-hand doorway and the four doorway approach areas remain clear.
chair[0].position = [3.00, 1.75, 0.44]
chair[0].rotation = [0, 0, radians(90)]

table_A[0].position = [4.95, 1.55, 0.38]
table_A[0].rotation = [0, 0, radians(90)]

sofa_A[0].position = [3.30, 3.15, 0.425]
sofa_A[0].rotation = [0, 0, radians(-90)]

cabinet_A[0].position = [4.55, 0.225, 0.41]
cabinet_A[0].rotation = [0, 0, radians(90)]

table_B[0].position = [2.00, 1.75, 0.29]
table_B[0].rotation = [0, 0, radians(90)]

sofa_B[0].position = [6.50, 3.21, 0.43]
sofa_B[0].rotation = [0, 0, radians(-90)]

table_C[0].position = [4.00, 1.75, 0.29]
table_C[0].rotation = [0, 0, radians(90)]

cabinet_B[0].position = [6.65, 0.225, 0.35]
cabinet_B[0].rotation = [0, 0, radians(90)]

table_D[0].position = [6.50, 2.20, 0.21]
table_D[0].rotation = [0, 0, radians(-90)]

# High-priority position constraints establish the collision-free target layout.
solver.distance_constraint(chair[0], chair_target, 0, 0, weight=10)
solver.distance_constraint(table_A[0], table_A_target, 0, 0, weight=10)
solver.distance_constraint(sofa_A[0], sofa_A_target, 0, 0, weight=10)
solver.distance_constraint(cabinet_A[0], cabinet_A_target, 0, 0, weight=10)
solver.distance_constraint(table_B[0], table_B_target, 0, 0, weight=10)
solver.distance_constraint(sofa_B[0], sofa_B_target, 0, 0, weight=10)
solver.distance_constraint(table_C[0], table_C_target, 0, 0, weight=10)
solver.distance_constraint(cabinet_B[0], cabinet_B_target, 0, 0, weight=10)
solver.distance_constraint(table_D[0], table_D_target, 0, 0, weight=10)

# Maintain the required chair-between-tables arrangement. Equal chair-to-table
# distances place table_B and table_C symmetrically on opposite sides of the chair.
solver.distance_constraint(chair[0], table_B[0], 0.95, 1.05, weight=10)
solver.distance_constraint(chair[0], table_C[0], 0.95, 1.05, weight=10)
solver.distance_constraint(table_B[0], table_C[0], 1.95, 2.05, weight=10)

# Keep the wall furniture flush with solid, unobstructed wall segments.
# wall[1] is the bottom wall; wall[3] is the upper-right wall.
solver.against_wall(cabinet_A[0], walls[1])
solver.against_wall(cabinet_B[0], walls[1])
solver.against_wall(sofa_B[0], walls[3])

# Preserve functional clearances around the two seating arrangements.
solver.distance_constraint(table_D[0], sofa_B[0], 0.95, 1.10, weight=10)
solver.distance_constraint(table_D[0], table_A[0], 1.20, None, weight=1)
solver.distance_constraint(table_A[0], sofa_A[0], 1.10, None, weight=1)

# Orientation constraints for every asset.
# The chair faces sofa_A while the two flanking tables share its orientation.
solver.point_towards(chair[0], sofa_A[0])
solver.align_with(table_B[0], chair[0])
solver.align_with(table_C[0], chair[0])
solver.point_towards(sofa_A[0], chair[0])

# The dining table and nearby cabinet face into the usable room area.
solver.point_towards(cabinet_A[0], table_A[0])
solver.align_with(table_A[0], cabinet_A[0])

# sofa_B faces cabinet_B as required. The low table remains parallel to sofa_B,
# and cabinet_B faces back toward the seating area.
solver.point_towards(sofa_B[0], cabinet_B[0])
solver.point_towards(cabinet_B[0], sofa_B[0])
solver.align_with(table_D[0], sofa_B[0])

solver.constraints = []
cabinet_A[0].position = [4.550000190734863, 0.22753828763961792, 0.4099999964237213]
cabinet_A[0].rotation = [0, 0, 1.5764478356648661]
cabinet_A[0].optimize = 2
table_D[0].position = [6.5, 2.200000047683716, 0.20999999344348907]
table_D[0].rotation = [0, 0, -1.5448361766376022]
table_D[0].optimize = 2
cabinet_B[0].position = [6.650000095367432, 0.2306797057390213, 0.3499999940395355]
cabinet_B[0].rotation = [0, 0, 1.5764478290525958]
cabinet_B[0].optimize = 2
chair[0].position = [3.0, 1.75, 0.4399999976158142]
chair[0].rotation = [0, 0, 1.5959290669047523]
chair[0].optimize = 2
table_A[0].position = [4.949999809265137, 1.5499999523162842, 0.3799999952316284]
table_A[0].rotation = [0, 0, 1.5795630678886143]
table_A[0].optimize = 2
table_B[0].position = [2.0, 1.75, 0.28999999165534973]
table_B[0].rotation = [0, 0, 1.5967578830729263]
table_B[0].optimize = 2
sofa_B[0].position = [6.5, 3.1929967403411865, 0.4300000071525574]
sofa_B[0].rotation = [0, 0, -1.558923329642871]
sofa_B[0].optimize = 2
sofa_A[0].position = [3.299999952316284, 3.1500000953674316, 0.42500001192092896]
sofa_A[0].rotation = [0, 0, -1.5550883628776802]
sofa_A[0].optimize = 2
table_C[0].position = [4.0, 1.75, 0.28999999165534973]
table_C[0].rotation = [0, 0, 1.5967578830729263]
table_C[0].optimize = 2

