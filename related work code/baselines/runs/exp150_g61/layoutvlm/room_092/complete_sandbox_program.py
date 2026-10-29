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
    Wall(corner1=[0.00, 6.37, 0.00], corner2=[0.00, 0.04, 0.00]),
    Wall(corner1=[0.00, 0.04, 0.00], corner2=[0.04, 0.00, 0.00]),
    Wall(corner1=[0.04, 0.00, 0.00], corner2=[2.62, 0.00, 0.00]),
    Wall(corner1=[2.62, 0.00, 0.00], corner2=[2.66, 0.04, 0.00]),
    Wall(corner1=[2.66, 0.04, 0.00], corner2=[5.16, 4.34, 0.00]),
    Wall(corner1=[5.16, 4.34, 0.00], corner2=[5.16, 6.37, 0.00]),
    Wall(corner1=[5.16, 6.37, 0.00], corner2=[5.12, 6.41, 0.00]),
    Wall(corner1=[5.12, 6.41, 0.00], corner2=[0.04, 6.41, 0.00]),
    Wall(corner1=[0.04, 6.41, 0.00], corner2=[0.00, 6.37, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
table_A = Assets(description="table", size=[0.70, 1.40, 0.75], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.60, 1.60, 2.10], placements=[AssetInstance() for _ in range(1)])
pot = Assets(description="pot", size=[0.30, 0.30, 0.28], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="shelf", size=[0.40, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
table_B = Assets(description="table", size=[0.65, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.40, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
shelf_C = Assets(description="shelf", size=[0.40, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])

table_A[0].instance_id = 'table_A_0'
wardrobe[0].instance_id = 'wardrobe_0'
pot[0].instance_id = 'pot_0'
shelf_A[0].instance_id = 'shelf_A_0'
table_B[0].instance_id = 'table_B_0'
shelf_B[0].instance_id = 'shelf_B_0'
shelf_C[0].instance_id = 'shelf_C_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'
walls[8].instance_id = 'walls_8'

table_A[0].position = [1.7425364434565849, 1.1469880196532385, 0.375]
table_A[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.11743794409552985, 1.9209200108872966, 1.05]
wardrobe[0].rotation = [0, 0, 0]
pot[0].position = [1.7067576046323383, 2.5732893358583953, 0.14]
pot[0].rotation = [0, 0, 0]
shelf_A[0].position = [2.309611276712272, 5.454539047893274, 0.9]
shelf_A[0].rotation = [0, 0, 0]
table_B[0].position = [0.44283414362631496, 4.7328920439572455, 0.375]
table_B[0].rotation = [0, 0, 0]
shelf_B[0].position = [5.128593748164165, 6.196991417345912, 0.9]
shelf_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [0.4597101241770118, 2.3121505908776316, 0.9]
shelf_C[0].rotation = [0, 0, 0]
table_A[0].position = [1.7425364434565849, 1.1469880196532385, 0.375]
table_A[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.11743794409552985, 1.9209200108872966, 1.05]
wardrobe[0].rotation = [0, 0, 0]
pot[0].position = [1.7067576046323383, 2.5732893358583953, 0.14]
pot[0].rotation = [0, 0, 0]
shelf_A[0].position = [2.309611276712272, 5.454539047893274, 0.9]
shelf_A[0].rotation = [0, 0, 0]
table_B[0].position = [0.44283414362631496, 4.7328920439572455, 0.375]
table_B[0].rotation = [0, 0, 0]
shelf_B[0].position = [5.128593748164165, 6.196991417345912, 0.9]
shelf_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [0.4597101241770118, 2.3121505908776316, 0.9]
shelf_C[0].rotation = [0, 0, 0]

solver.constraints = []

# The supplied wall coordinates define the usable room.
# Arrange storage along the west wall, stopping below the door at y=4.79.
# In asset-list order, shelf_A is o0003, shelf_B is o0005,
# and shelf_C is o0006.
shelf_B[0].position = [0.20, 0.50, 0.90]
shelf_C[0].position = [0.20, 1.42, 0.90]
wardrobe[0].position = [0.30, 2.69, 1.05]
shelf_A[0].position = [0.20, 3.96, 0.90]

# All storage fronts face east into the room.
for storage_group in (shelf_B, shelf_C, wardrobe, shelf_A):
    storage_group[0].rotation = [0, 0, 0]

# Put the larger table against the east wall, facing into the room.
# Its northern edge stops at y=6.00, leaving the north doorway accessible.
table_A[0].position = [4.81, 5.30, 0.375]
table_A[0].rotation = [0, 0, radians(180)]

# A freestanding worktable leaves circulation space beside the storage,
# below the west doorway, and behind the south entrance.
table_B[0].position = [2.35, 2.70, 0.375]
table_B[0].rotation = [0, 0, 0]

# The pot rests fully within the larger tabletop.
pot[0].position = [4.81, 5.30, 0.89]
pot[0].rotation = [0, 0, radians(180)]

# Preserve the collision-free locations first. These fixed reference points
# are constraint anchors, not additional scene furnishings.
for placed_group in (
    shelf_B, shelf_C, wardrobe, shelf_A, table_A, table_B, pot
):
    solver.distance_constraint(
        placed_group[0],
        AssetInstance(position=list(placed_group[0].position)),
        0,
        0,
        weight=10,
    )

# Maintain wall contact and inward-facing orientations for the storage.
for storage_group in (shelf_B, shelf_C, wardrobe, shelf_A):
    solver.against_wall(storage_group[0], walls[0])
    solver.align_with(
        storage_group[0],
        AssetInstance(rotation=[0, 0, 0]),
    )

solver.against_wall(table_A[0], walls[5])
solver.align_with(
    table_A[0],
    AssetInstance(rotation=[0, 0, radians(180)]),
)
solver.align_with(
    table_B[0],
    AssetInstance(rotation=[0, 0, 0]),
)

# Shelf_C and shelf_B have a 0.02 m edge gap. Their center separation
# must be 0.90–1.00 m to maintain a nonoverlapping gap of at most 0.10 m.
solver.distance_constraint(
    shelf_C[0], shelf_B[0], 0.90, 1.00, weight=10
)
solver.align_with(shelf_C[0], shelf_B[0])

# Wardrobe lies between shelf_C and shelf_A along the west wall.
# Each neighboring edge gap is 0.02 m. Account for the different
# horizontal depths and center heights in these 3D center distances.
storage_neighbor_distance = (1.27**2 + 0.10**2 + 0.15**2) ** 0.5
solver.distance_constraint(
    wardrobe[0], shelf_C[0],
    storage_neighbor_distance, storage_neighbor_distance, weight=10
)
solver.distance_constraint(
    shelf_A[0], wardrobe[0],
    storage_neighbor_distance, storage_neighbor_distance, weight=10
)
solver.align_with(wardrobe[0], shelf_C[0])
solver.align_with(shelf_A[0], wardrobe[0])

# Keep the pot supported and centered on the tabletop.
solver.on_top_of(pot[0], table_A[0])
solver.distance_constraint(
    pot[0], table_A[0], 0.515, 0.515, weight=10
)
solver.align_with(pot[0], table_A[0])

solver.constraints = []
wardrobe[0].position = [0.2967965006828308, 2.6993181705474854, 1.0499999523162842]
wardrobe[0].rotation = [0, 0, -7.745856387540518e-07]
wardrobe[0].optimize = 2
table_B[0].position = [2.3499999046325684, 2.700000047683716, 0.375]
table_B[0].rotation = [0, 0, 0.00942477746072377]
table_B[0].optimize = 2
table_A[0].position = [4.806250095367432, 5.300000190734863, 0.375]
table_A[0].rotation = [0, 0, 3.141591873059023]
table_A[0].optimize = 2
shelf_B[0].position = [0.20000019669532776, 0.5, 0.8999999761581421]
shelf_B[0].rotation = [0, 0, -5.589391502944215e-07]
shelf_B[0].optimize = 2
shelf_C[0].position = [0.1999998241662979, 1.4199999570846558, 0.8999999761581421]
shelf_C[0].rotation = [0, 0, -7.374560906678209e-07]
shelf_C[0].optimize = 2
pot[0].position = [5.006249904632568, 5.300000190734863, 0.8899999856948853]
pot[0].rotation = [0, 0, -3.141592530533452]
pot[0].optimize = 2
shelf_A[0].position = [0.2072237730026245, 3.9768176078796387, 0.8999999761581421]
shelf_A[0].rotation = [0, 0, -5.543334788981698e-07]
shelf_A[0].optimize = 2

