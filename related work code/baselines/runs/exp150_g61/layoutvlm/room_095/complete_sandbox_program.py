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
    Wall(corner1=[0.00, 5.27, 0.00], corner2=[0.00, 1.99, 0.00]),
    Wall(corner1=[0.00, 1.99, 0.00], corner2=[0.04, 1.95, 0.00]),
    Wall(corner1=[0.04, 1.95, 0.00], corner2=[2.85, 0.00, 0.00]),
    Wall(corner1=[2.85, 0.00, 0.00], corner2=[4.18, 0.00, 0.00]),
    Wall(corner1=[4.18, 0.00, 0.00], corner2=[4.22, 0.04, 0.00]),
    Wall(corner1=[4.22, 0.04, 0.00], corner2=[4.22, 5.27, 0.00]),
    Wall(corner1=[4.22, 5.27, 0.00], corner2=[4.18, 5.31, 0.00]),
    Wall(corner1=[4.18, 5.31, 0.00], corner2=[0.04, 5.31, 0.00]),
    Wall(corner1=[0.04, 5.31, 0.00], corner2=[0.00, 5.27, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
chair_A = Assets(description="chair", size=[0.75, 0.70, 0.85], placements=[AssetInstance() for _ in range(1)])
cup = Assets(description="cup", size=[0.08, 0.11, 0.10], placements=[AssetInstance() for _ in range(1)])
couch_A = Assets(description="couch", size=[0.85, 1.80, 0.85], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.75, 0.70, 0.85], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="lamp", size=[0.32, 0.32, 0.55], placements=[AssetInstance() for _ in range(1)])
table_A = Assets(description="table", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
couch_B = Assets(description="couch", size=[0.85, 1.80, 0.85], placements=[AssetInstance() for _ in range(1)])
table_B = Assets(description="table", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.32, 0.32, 0.55], placements=[AssetInstance() for _ in range(1)])
table_C = Assets(description="table", size=[0.60, 1.10, 0.42], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="chair", size=[0.75, 0.70, 0.85], placements=[AssetInstance() for _ in range(1)])
book = Assets(description="book", size=[0.28, 0.21, 0.03], placements=[AssetInstance() for _ in range(1)])
paper_A = Assets(description="paper", size=[0.30, 0.21, 0.00], placements=[AssetInstance() for _ in range(1)])
toy = Assets(description="toy", size=[0.10, 0.15, 0.12], placements=[AssetInstance() for _ in range(1)])
paper_B = Assets(description="paper", size=[0.30, 0.21, 0.00], placements=[AssetInstance() for _ in range(1)])

chair_A[0].instance_id = 'chair_A_0'
cup[0].instance_id = 'cup_0'
couch_A[0].instance_id = 'couch_A_0'
chair_B[0].instance_id = 'chair_B_0'
lamp_A[0].instance_id = 'lamp_A_0'
table_A[0].instance_id = 'table_A_0'
couch_B[0].instance_id = 'couch_B_0'
table_B[0].instance_id = 'table_B_0'
lamp_B[0].instance_id = 'lamp_B_0'
table_C[0].instance_id = 'table_C_0'
chair_C[0].instance_id = 'chair_C_0'
book[0].instance_id = 'book_0'
paper_A[0].instance_id = 'paper_A_0'
toy[0].instance_id = 'toy_0'
paper_B[0].instance_id = 'paper_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'
walls[8].instance_id = 'walls_8'

chair_A[0].position = [1.167193550729237, 2.7854136494050725, 0.425]
chair_A[0].rotation = [0, 0, 0]
cup[0].position = [3.6754693295945833, 1.8710234480042542, 0.05]
cup[0].rotation = [0, 0, 0]
couch_A[0].position = [3.773861893351702, 5.058939515901083, 0.425]
couch_A[0].rotation = [0, 0, 0]
chair_B[0].position = [1.7639272360278122, 4.801871826227752, 0.425]
chair_B[0].rotation = [0, 0, 0]
lamp_A[0].position = [0.556190632268963, 3.8778371227035633, 0.275]
lamp_A[0].rotation = [0, 0, 0]
table_A[0].position = [3.947791886852659, 5.240133076934247, 0.275]
table_A[0].rotation = [0, 0, 0]
couch_B[0].position = [2.600360727852872, 4.014975419934635, 0.425]
couch_B[0].rotation = [0, 0, 0]
table_B[0].position = [2.904774049925304, 3.3430105746731926, 0.275]
table_B[0].rotation = [0, 0, 0]
lamp_B[0].position = [2.561055811202568, 0.22433208664103493, 0.275]
lamp_B[0].rotation = [0, 0, 0]
table_C[0].position = [2.167952931981395, 2.3923083263096157, 0.21]
table_C[0].rotation = [0, 0, 0]
chair_C[0].position = [4.006462731715401, 1.7483531339330818, 0.425]
chair_C[0].rotation = [0, 0, 0]
book[0].position = [2.8427635405612026, 4.645291504081437, 0.0125]
book[0].rotation = [0, 0, 0]
paper_A[0].position = [0.7756638348037854, 2.484936061014796, 0.0005]
paper_A[0].rotation = [0, 0, 0]
toy[0].position = [0.5524757293344604, 2.4562982109873657, 0.06]
toy[0].rotation = [0, 0, 0]
paper_B[0].position = [3.833307061649397, 4.370001816515092, 0.0005]
paper_B[0].rotation = [0, 0, 0]
chair_A[0].position = [1.167193550729237, 2.7854136494050725, 0.425]
chair_A[0].rotation = [0, 0, 0]
cup[0].position = [3.6754693295945833, 1.8710234480042542, 0.05]
cup[0].rotation = [0, 0, 0]
couch_A[0].position = [3.773861893351702, 5.058939515901083, 0.425]
couch_A[0].rotation = [0, 0, 0]
chair_B[0].position = [1.7639272360278122, 4.801871826227752, 0.425]
chair_B[0].rotation = [0, 0, 0]
lamp_A[0].position = [0.556190632268963, 3.8778371227035633, 0.275]
lamp_A[0].rotation = [0, 0, 0]
table_A[0].position = [3.947791886852659, 5.240133076934247, 0.275]
table_A[0].rotation = [0, 0, 0]
couch_B[0].position = [2.600360727852872, 4.014975419934635, 0.425]
couch_B[0].rotation = [0, 0, 0]
table_B[0].position = [2.904774049925304, 3.3430105746731926, 0.275]
table_B[0].rotation = [0, 0, 0]
lamp_B[0].position = [2.561055811202568, 0.22433208664103493, 0.275]
lamp_B[0].rotation = [0, 0, 0]
table_C[0].position = [2.167952931981395, 2.3923083263096157, 0.21]
table_C[0].rotation = [0, 0, 0]
chair_C[0].position = [4.006462731715401, 1.7483531339330818, 0.425]
chair_C[0].rotation = [0, 0, 0]
book[0].position = [2.8427635405612026, 4.645291504081437, 0.0125]
book[0].rotation = [0, 0, 0]
paper_A[0].position = [0.7756638348037854, 2.484936061014796, 0.0005]
paper_A[0].rotation = [0, 0, 0]
toy[0].position = [0.5524757293344604, 2.4562982109873657, 0.06]
toy[0].rotation = [0, 0, 0]
paper_B[0].position = [3.833307061649397, 4.370001816515092, 0.0005]
paper_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange a conversation area in the rectangular upper part of the room.
# Opposing sofas leave a generous central aisle; the angled lower boundary
# remains clear. Coordinates use the supplied wall coordinates.
floor_layout = [
    (couch_A, [0.425, 3.65, 0.425], 0),
    (couch_B, [3.795, 3.65, 0.425], 180),
    (chair_A, [1.50, 4.935, 0.425], -90),
    (chair_B, [2.70, 4.935, 0.425], -90),
    (chair_C, [2.11, 2.25, 0.425], 90),
    (table_A, [0.35, 2.30, 0.275], 0),
    (table_B, [3.87, 2.30, 0.275], 180),
    (table_C, [2.11, 3.65, 0.21], 0),
]

for asset_group, center, yaw in floor_layout:
    asset_group[0].position = center
    asset_group[0].rotation = [0, 0, radians(yaw)]

    # Fixed references preserve both the collision-free footprint and heading.
    # Exact center constraints take priority over supplementary relationships.
    reference = AssetInstance(
        position=list(center), rotation=[0, 0, radians(yaw)]
    )
    solver.distance_constraint(asset_group[0], reference, 0, 0, weight=10)
    solver.align_with(asset_group[0], reference)

# Sofa backs and the two northern chair backs meet their respective walls.
solver.against_wall(couch_A[0], walls[0])
solver.against_wall(couch_B[0], walls[5])
solver.against_wall(chair_A[0], walls[7])
solver.against_wall(chair_B[0], walls[7])

# Reinforce the inward-facing seating arrangement.
solver.point_towards(couch_A[0], couch_B[0])
solver.point_towards(couch_B[0], couch_A[0])
solver.point_towards(chair_C[0], table_C[0])

# Each lamp is supported by its own side table.
# Coffee-table accessories occupy separate patches, with no stacking or overlap.
surface_layout = [
    (lamp_A, table_A, [0.35, 2.30, 0.825], 0),
    (lamp_B, table_B, [3.87, 2.30, 0.825], 180),
    (book, table_C, [2.11, 3.45, 0.435], 0),
    (paper_A, table_C, [2.11, 3.75, 0.42], 0),
    (paper_B, table_C, [2.11, 4.00, 0.42], 0),
    (cup, table_C, [1.94, 3.18, 0.47], 0),
    (toy, table_C, [2.25, 3.18, 0.48], 0),
]

for asset_group, support_group, center, yaw in surface_layout:
    asset_group[0].position = center
    asset_group[0].rotation = [0, 0, radians(yaw)]

    # Support comes first so these small objects cannot fall to the floor.
    solver.on_top_of(asset_group[0], support_group[0])
    reference = AssetInstance(
        position=list(center), rotation=[0, 0, radians(yaw)]
    )
    solver.distance_constraint(asset_group[0], reference, 0, 0, weight=10)
    solver.align_with(asset_group[0], support_group[0])

solver.constraints = []
cup[0].position = [1.940000057220459, 3.180000066757202, 0.4699999988079071]
cup[0].rotation = [0, 0, 0.043906777834255284]
cup[0].optimize = 2
book[0].position = [2.109999895095825, 3.450000047683716, 0.4349999725818634]
book[0].rotation = [0, 0, 0.043906777834255284]
book[0].optimize = 2
couch_B[0].position = [3.7936882972717285, 3.6500000953674316, 0.42500001192092896]
couch_B[0].rotation = [0, 0, -3.1415378097498543]
couch_B[0].optimize = 2
chair_C[0].position = [2.109999895095825, 2.25, 0.42500001192092896]
chair_C[0].rotation = [0, 0, 1.5833626980517244]
chair_C[0].optimize = 2
paper_B[0].position = [2.109999895095825, 4.0, 0.41999998688697815]
paper_B[0].rotation = [0, 0, 0.043906777834255284]
paper_B[0].optimize = 2
paper_A[0].position = [2.109999895095825, 3.75, 0.41999998688697815]
paper_A[0].rotation = [0, 0, 0.043906777834255284]
paper_A[0].optimize = 2
chair_B[0].position = [2.700000047683716, 4.937465667724609, 0.42500001192092896]
chair_B[0].rotation = [0, 0, -1.5708823045326188]
chair_B[0].optimize = 2
couch_A[0].position = [0.42506125569343567, 3.6500000953674316, 0.42500001192092896]
couch_A[0].rotation = [0, 0, 5.486364568758997e-05]
couch_A[0].optimize = 2
table_B[0].position = [3.869999885559082, 2.299999952316284, 0.2750000059604645]
table_B[0].rotation = [0, 0, -3.125884689672577]
table_B[0].optimize = 2
table_A[0].position = [0.3499999940395355, 2.299999952316284, 0.2750000059604645]
table_A[0].rotation = [0, 0, 0.0157079639172164]
table_A[0].optimize = 2
table_C[0].position = [2.109999895095825, 3.6500000953674316, 0.20999999344348907]
table_C[0].rotation = [0, 0, 0.043982298440307294]
table_C[0].optimize = 2
chair_A[0].position = [1.5, 4.937465667724609, 0.42500001192092896]
chair_A[0].rotation = [0, 0, -1.5708823045326188]
chair_A[0].optimize = 2
lamp_B[0].position = [3.869999885559082, 2.299999952316284, 0.8250000476837158]
lamp_B[0].rotation = [0, 0, -3.1259220407700394]
lamp_B[0].optimize = 2
lamp_A[0].position = [0.3499999940395355, 2.299999952316284, 0.8250000476837158]
lamp_A[0].rotation = [0, 0, 0.015670612819753637]
lamp_A[0].optimize = 2
toy[0].position = [2.25, 3.180000066757202, 0.47999998927116394]
toy[0].rotation = [0, 0, 0.043906777834255284]
toy[0].optimize = 2

