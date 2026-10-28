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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[8.04, 0.00, 0.00]),
    Wall(corner1=[8.04, 0.00, 0.00], corner2=[8.04, 8.73, 0.00]),
    Wall(corner1=[8.04, 8.73, 0.00], corner2=[0.00, 8.73, 0.00]),
    Wall(corner1=[0.00, 8.73, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
cabinet_A = Assets(description="A modern kitchen cabinet with a sleek design, featuring an integrated oven and a countertop. The cabinet has a white body with a dark green countertop and a black oven door with control knobs.", size=[0.65, 1.20, 2.10], placements=[AssetInstance() for _ in range(1)])
oven = Assets(description="A modern kitchen stove with a white body, black burners, red knobs, and two ovens.", size=[0.65, 0.90, 1.15], placements=[AssetInstance() for _ in range(1)])
fridge = Assets(description="A white refrigerator with a sleek design, featuring a handle on its side. It appears to be a standalone appliance with no additional accessories or decorations.", size=[0.70, 0.70, 1.80], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="A white cabinet with a light wooden top, featuring clean lines and a minimalist design.", size=[0.60, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
cabinet_C = Assets(description="A wooden wine cabinet with a rustic design, featuring a door with a handle on the left side and an open section with multiple compartments for storing bottles on the right side.", size=[0.45, 1.00, 1.10], placements=[AssetInstance() for _ in range(1)])
stand = Assets(description="A white cabinet with multiple drawers and open shelves, designed for storage purposes.", size=[0.45, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])

cabinet_A[0].instance_id = 'cabinet_A_0'
oven[0].instance_id = 'oven_0'
fridge[0].instance_id = 'fridge_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
cabinet_C[0].instance_id = 'cabinet_C_0'
stand[0].instance_id = 'stand_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

cabinet_A[0].position = [4.0307553266553695, 2.852126734147265, 1.05]
cabinet_A[0].rotation = [0, 0, 0]
oven[0].position = [3.8311795136653912, 4.970989721384596, 0.575]
oven[0].rotation = [0, 0, 0]
fridge[0].position = [3.2304399807273145, 0.9643994689126929, 0.9]
fridge[0].rotation = [0, 0, 0]
cabinet_B[0].position = [5.686610533402034, 0.5569659106805628, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
cabinet_C[0].position = [2.8101398833169586, 7.157474979591897, 0.55]
cabinet_C[0].rotation = [0, 0, 0]
stand[0].position = [1.7231976792867285, 7.802449523505235, 0.45]
stand[0].rotation = [0, 0, 0]
cabinet_A[0].position = [4.0307553266553695, 2.852126734147265, 1.05]
cabinet_A[0].rotation = [0, 0, 0]
oven[0].position = [3.8311795136653912, 4.970989721384596, 0.575]
oven[0].rotation = [0, 0, 0]
fridge[0].position = [3.2304399807273145, 0.9643994689126929, 0.9]
fridge[0].rotation = [0, 0, 0]
cabinet_B[0].position = [5.686610533402034, 0.5569659106805628, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
cabinet_C[0].position = [2.8101398833169586, 7.157474979591897, 0.55]
cabinet_C[0].rotation = [0, 0, 0]
stand[0].position = [1.7231976792867285, 7.802449523505235, 0.45]
stand[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the appliances and cabinets as a single functional kitchen run along
# the north wall. Their fronts face south into the open workspace.
cabinet_A[0].position = [0.60, 8.405, 1.05]
cabinet_A[0].rotation = [0, 0, radians(-90)]

oven[0].position = [1.75, 8.405, 0.575]
oven[0].rotation = [0, 0, radians(-90)]

cabinet_B[0].position = [2.90, 8.43, 0.45]
cabinet_B[0].rotation = [0, 0, radians(-90)]

cabinet_C[0].position = [4.10, 8.505, 0.55]
cabinet_C[0].rotation = [0, 0, radians(-90)]

stand[0].position = [5.25, 8.505, 0.45]
stand[0].rotation = [0, 0, radians(-90)]

fridge[0].position = [6.45, 8.38, 0.90]
fridge[0].rotation = [0, 0, radians(-90)]

# Fixed points directly south of each object preserve the intended orientation
# without causing the row to converge toward a single point.
cabinet_A_south = AssetInstance(position=[0.60, 4.00, 1.05])
oven_south = AssetInstance(position=[1.75, 4.00, 0.575])
cabinet_B_south = AssetInstance(position=[2.90, 4.00, 0.45])
cabinet_C_south = AssetInstance(position=[4.10, 4.00, 0.55])
stand_south = AssetInstance(position=[5.25, 4.00, 0.45])
fridge_south = AssetInstance(position=[6.45, 4.00, 0.90])

# Important semantic constraints are specified first. The center-distance
# bounds include the objects' half-widths and vertical center offsets, so the
# requested 0.50 m and 0.20 m limits represent clear edge-to-edge gaps while
# still preventing the neighboring footprints from overlapping.
solver.against_wall(oven[0], walls[2])
solver.distance_constraint(
    fridge[0], stand[0],
    min_distance=1.05, max_distance=1.52, weight=10
)
solver.against_wall(cabinet_B[0], walls[2])
solver.distance_constraint(
    cabinet_C[0], stand[0],
    min_distance=1.10, max_distance=1.31, weight=10
)

# Keep the complete kitchen run against the north wall.
solver.against_wall(cabinet_A[0], walls[2])
solver.against_wall(fridge[0], walls[2])
solver.against_wall(cabinet_C[0], walls[2])
solver.against_wall(stand[0], walls[2])

# Every new instance receives an orientation constraint and faces the room.
solver.point_towards(cabinet_A[0], cabinet_A_south)
solver.point_towards(oven[0], oven_south)
solver.point_towards(fridge[0], fridge_south)
solver.point_towards(cabinet_B[0], cabinet_B_south)
solver.point_towards(cabinet_C[0], cabinet_C_south)
solver.point_towards(stand[0], stand_south)

solver.constraints = []
fridge[0].position = [6.449999809265137, 8.382466316223145, 0.8999999761581421]
fridge[0].rotation = [0, 0, -1.5707963031149896]
fridge[0].optimize = 2
cabinet_B[0].position = [2.9000000953674316, 8.432466506958008, 0.44999998807907104]
cabinet_B[0].rotation = [0, 0, -1.5707962649953549]
cabinet_B[0].optimize = 2
oven[0].position = [1.75, 8.40746784210205, 0.574999988079071]
oven[0].rotation = [0, 0, -1.5707962516479776]
oven[0].optimize = 2
cabinet_A[0].position = [0.6580268740653992, 8.407468795776367, 1.0499999523162842]
cabinet_A[0].rotation = [0, 0, -1.570796295805062]
cabinet_A[0].optimize = 2
stand[0].position = [5.25, 8.507467269897461, 0.44999998807907104]
stand[0].rotation = [0, 0, -1.5707963118904797]
stand[0].optimize = 2
cabinet_C[0].position = [4.099999904632568, 8.507467269897461, 0.550000011920929]
cabinet_C[0].rotation = [0, 0, -1.5707963028474254]
cabinet_C[0].optimize = 2

