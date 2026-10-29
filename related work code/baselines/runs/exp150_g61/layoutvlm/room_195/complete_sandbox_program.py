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
    Wall(corner1=[4.59, 7.20, 0.00], corner2=[4.59, 3.79, 0.00]),
    Wall(corner1=[4.59, 3.79, 0.00], corner2=[0.00, 3.79, 0.00]),
    Wall(corner1=[0.00, 3.79, 0.00], corner2=[0.00, 2.73, 0.00]),
    Wall(corner1=[0.00, 2.73, 0.00], corner2=[4.99, 2.73, 0.00]),
    Wall(corner1=[4.99, 2.73, 0.00], corner2=[4.99, 0.00, 0.00]),
    Wall(corner1=[4.99, 0.00, 0.00], corner2=[7.97, 0.00, 0.00]),
    Wall(corner1=[7.97, 0.00, 0.00], corner2=[7.97, 7.20, 0.00]),
    Wall(corner1=[7.97, 7.20, 0.00], corner2=[4.59, 7.20, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
dining_chair_A = Assets(description="dining chair", size=[0.55, 0.48, 0.88], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[2.40, 3.00, 0.01], placements=[AssetInstance() for _ in range(1)])
dining_chair_B = Assets(description="dining chair", size=[0.55, 0.48, 0.88], placements=[AssetInstance() for _ in range(1)])
air_conditioner = Assets(description="air conditioner", size=[0.24, 1.00, 0.32], placements=[AssetInstance() for _ in range(1)])
dining_table = Assets(description="dining table", size=[0.90, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
dining_chair_C = Assets(description="dining chair", size=[0.55, 0.48, 0.88], placements=[AssetInstance() for _ in range(1)])
dining_chair_D = Assets(description="dining chair", size=[0.55, 0.48, 0.88], placements=[AssetInstance() for _ in range(1)])
combination_sofa = Assets(description="combination sofa", size=[2.00, 3.20, 0.85], placements=[AssetInstance() for _ in range(1)])

dining_chair_A[0].instance_id = 'dining_chair_A_0'
carpet[0].instance_id = 'carpet_0'
dining_chair_B[0].instance_id = 'dining_chair_B_0'
air_conditioner[0].instance_id = 'air_conditioner_0'
dining_table[0].instance_id = 'dining_table_0'
dining_chair_C[0].instance_id = 'dining_chair_C_0'
dining_chair_D[0].instance_id = 'dining_chair_D_0'
combination_sofa[0].instance_id = 'combination_sofa_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

dining_chair_A[0].position = [5.286351356955277, 5.607416939680035, 0.44]
dining_chair_A[0].rotation = [0, 0, 0]
carpet[0].position = [3.490012718878292, 3.6139041281395894, 0.0075]
carpet[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [0.10825063580689616, 3.7861312807686223, 0.44]
dining_chair_B[0].rotation = [0, 0, 0]
air_conditioner[0].position = [5.845085216986269, 2.0175298264403656, 0.16]
air_conditioner[0].rotation = [0, 0, 0]
dining_table[0].position = [1.1393691236566388, 3.5074503329209907, 0.375]
dining_table[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [6.984448484644516, 2.629161092390814, 0.44]
dining_chair_C[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [5.943590042619351, 0.6625964437902404, 0.44]
dining_chair_D[0].rotation = [0, 0, 0]
combination_sofa[0].position = [5.280779458500981, 2.8939279414338515, 0.425]
combination_sofa[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [5.286351356955277, 5.607416939680035, 0.44]
dining_chair_A[0].rotation = [0, 0, 0]
carpet[0].position = [3.490012718878292, 3.6139041281395894, 0.0075]
carpet[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [0.10825063580689616, 3.7861312807686223, 0.44]
dining_chair_B[0].rotation = [0, 0, 0]
air_conditioner[0].position = [5.845085216986269, 2.0175298264403656, 0.16]
air_conditioner[0].rotation = [0, 0, 0]
dining_table[0].position = [1.1393691236566388, 3.5074503329209907, 0.375]
dining_table[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [6.984448484644516, 2.629161092390814, 0.44]
dining_chair_C[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [5.943590042619351, 0.6625964437902404, 0.44]
dining_chair_D[0].rotation = [0, 0, 0]
combination_sofa[0].position = [5.280779458500981, 2.8939279414338515, 0.425]
combination_sofa[0].rotation = [0, 0, 0]

solver.constraints = []

# Keep the narrow western corridor empty. The dining area occupies the
# southern bay, while the sofa leaves a passage along its west side and
# approximately 0.80 m of clear floor below the northern doorway.
dining_table[0].position = [6.65, 2.05, dining_table.size[2] / 2]
dining_table[0].rotation = [0, 0, radians(90)]

# Two opposing pairs: the table lies between the chairs in each pair.
dining_chair_A[0].position = [6.20, 1.25, dining_chair_A.size[2] / 2]
dining_chair_A[0].rotation = [0, 0, radians(90)]

dining_chair_B[0].position = [6.20, 2.85, dining_chair_B.size[2] / 2]
dining_chair_B[0].rotation = [0, 0, radians(-90)]

dining_chair_C[0].position = [7.10, 1.25, dining_chair_C.size[2] / 2]
dining_chair_C[0].rotation = [0, 0, radians(90)]

dining_chair_D[0].position = [7.10, 2.85, dining_chair_D.size[2] / 2]
dining_chair_D[0].rotation = [0, 0, radians(-90)]

# A thin rug beneath the lounge seating is intentional, not an obstacle
# in the circulation route. Raise the sofa above the rug's upper surface.
carpet[0].position = [6.75, 4.80, carpet.size[2] / 2]
carpet[0].rotation = [0, 0, 0]

combination_sofa[0].position = [
    6.95, 4.80, carpet.size[2] + combination_sofa.size[2] / 2
]
combination_sofa[0].rotation = [0, 0, radians(180)]

# Mount the air conditioner high on the western lounge wall.
# It is a wall-mounted appliance, not a tabletop object.
air_conditioner[0].position = [4.71, 5.00, 2.35]
air_conditioner[0].rotation = [0, 0, 0]

# Prioritize the chosen centers: the room's many doorways make arbitrary
# lateral movement undesirable. Fixed-point constraints also preserve
# mounting height for the air conditioner.
for layout_group in (
    dining_table,
    dining_chair_A,
    dining_chair_B,
    dining_chair_C,
    dining_chair_D,
    carpet,
    combination_sofa,
    air_conditioner,
):
    solver.distance_constraint(
        layout_group[0],
        AssetInstance(position=list(layout_group[0].position)),
        0,
        0,
        weight=10,
    )

# Orientation constraints use fixed facing targets, not additional furniture.
solver.point_towards(
    dining_table[0], AssetInstance(position=[6.65, 3.05, 0.375])
)
solver.point_towards(
    carpet[0], AssetInstance(position=[7.75, 4.80, 0.005])
)
solver.point_towards(
    combination_sofa[0],
    AssetInstance(position=[5.20, 4.80, combination_sofa[0].position[2]]),
)
solver.point_towards(
    air_conditioner[0], AssetInstance(position=[6.00, 5.00, 2.35])
)

# Each chair faces straight across the tabletop rather than diagonally
# toward its center. Opposing chairs remain parallel and face one another.
for south_group, north_group in (
    (dining_chair_A, dining_chair_B),
    (dining_chair_C, dining_chair_D),
):
    solver.point_towards(south_group[0], north_group[0])
    solver.point_towards(north_group[0], south_group[0])
    solver.distance_constraint(
        south_group[0], north_group[0], 1.60, 1.60, weight=10
    )
    solver.distance_constraint(
        north_group[0], south_group[0], 1.60, 1.60, weight=10
    )

# Preserve chair-to-table spacing, accounting for the vertical difference
# between their bounding-box centers.
for chair_group in (
    dining_chair_A,
    dining_chair_B,
    dining_chair_C,
    dining_chair_D,
):
    chair_table_distance = (
        0.45**2
        + 0.80**2
        + ((chair_group.size[2] - dining_table.size[2]) / 2)**2
    ) ** 0.5
    solver.distance_constraint(
        chair_group[0],
        dining_table[0],
        chair_table_distance,
        chair_table_distance,
        weight=10,
    )

# Maintain the lounge's supporting surface and wall relationships.
solver.on_top_of(combination_sofa[0], carpet[0])
solver.against_wall(air_conditioner[0], walls[0])
solver.align_with(carpet[0], combination_sofa[0], angle=180)

solver.constraints = []
dining_chair_D[0].position = [7.158048152923584, 2.848179340362549, 0.4399999976158142]
dining_chair_D[0].rotation = [0, 0, -1.548805178508874]
dining_chair_D[0].optimize = 2
air_conditioner[0].position = [4.712500095367432, 5.0, 0.1599999964237213]
air_conditioner[0].rotation = [0, 0, 4.380727390082195e-08]
air_conditioner[0].optimize = 2
carpet[0].position = [6.75, 4.800000190734863, 0.004999999888241291]
carpet[0].rotation = [0, 0, 0.015708052527605286]
carpet[0].optimize = 2
dining_table[0].position = [6.650000095367432, 2.049999952316284, 0.375]
dining_table[0].rotation = [0, 0, 1.5927874750809192]
dining_table[0].optimize = 2
dining_chair_C[0].position = [7.158048152923584, 1.2518196105957031, 0.4399999976158142]
dining_chair_C[0].rotation = [0, 0, 1.5927874750809192]
dining_chair_C[0].optimize = 2
combination_sofa[0].position = [6.949999809265137, 4.800000190734863, 0.4350000023841858]
combination_sofa[0].rotation = [0, 0, -3.125884689672577]
combination_sofa[0].optimize = 2
dining_chair_A[0].position = [6.141951560974121, 1.2518196105957031, 0.4399999976158142]
dining_chair_A[0].rotation = [0, 0, 1.5927874750809192]
dining_chair_A[0].optimize = 2
dining_chair_B[0].position = [6.141951560974121, 2.848179340362549, 0.4399999976158142]
dining_chair_B[0].rotation = [0, 0, -1.548805178508874]
dining_chair_B[0].optimize = 2

