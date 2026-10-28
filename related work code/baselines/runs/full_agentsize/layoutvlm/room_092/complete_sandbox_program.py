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
table_A = Assets(description="table", size=[0.60, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.60, 1.80, 2.10], placements=[AssetInstance() for _ in range(1)])
pot = Assets(description="pot", size=[0.25, 0.25, 0.30], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="shelf", size=[0.35, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
table_B = Assets(description="table", size=[0.50, 1.00, 0.75], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.30, 0.80, 1.80], placements=[AssetInstance() for _ in range(1)])
shelf_C = Assets(description="shelf", size=[0.30, 0.80, 1.80], placements=[AssetInstance() for _ in range(1)])

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

table_A[0].position = [0.9972296430266914, 5.407034214812186, 0.375]
table_A[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.20274805160699624, 1.9282116114480699, 1.05]
wardrobe[0].rotation = [0, 0, 0]
pot[0].position = [2.399337979226685, 3.3039347682292464, 0.15]
pot[0].rotation = [0, 0, 0]
shelf_A[0].position = [4.060168335511705, 6.262814608711722, 0.9]
shelf_A[0].rotation = [0, 0, 0]
table_B[0].position = [0.9114362511198997, 2.8810218502410687, 0.375]
table_B[0].rotation = [0, 0, 0]
shelf_B[0].position = [2.7274034958568976, 4.096768228453951, 0.9]
shelf_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [2.993655294176466, 6.193117265363884, 0.9]
shelf_C[0].rotation = [0, 0, 0]
table_A[0].position = [0.9972296430266914, 5.407034214812186, 0.375]
table_A[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.20274805160699624, 1.9282116114480699, 1.05]
wardrobe[0].rotation = [0, 0, 0]
pot[0].position = [2.399337979226685, 3.3039347682292464, 0.15]
pot[0].rotation = [0, 0, 0]
shelf_A[0].position = [4.060168335511705, 6.262814608711722, 0.9]
shelf_A[0].rotation = [0, 0, 0]
table_B[0].position = [0.9114362511198997, 2.8810218502410687, 0.375]
table_B[0].rotation = [0, 0, 0]
shelf_B[0].position = [2.7274034958568976, 4.096768228453951, 0.9]
shelf_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [2.993655294176466, 6.193117265363884, 0.9]
shelf_C[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the four tall storage units along the lower portion of the left wall.
# Their fronts face +x into the room. From bottom to top, shelf_A, wardrobe,
# shelf_C, and shelf_B form one compact row; therefore the wardrobe lies
# between shelf_A (o0003) and shelf_C (o0006). shelf_C and shelf_B have a
# 0.05 m edge-to-edge gap, satisfying the requested maximum 0.10 m spacing.
shelf_A[0].position = [0.175, 0.49, 0.90]
shelf_A[0].rotation = [0, 0, radians(0)]

wardrobe[0].position = [0.30, 1.865, 1.05]
wardrobe[0].rotation = [0, 0, radians(0)]

shelf_C[0].position = [0.15, 3.19, 0.90]
shelf_C[0].rotation = [0, 0, radians(0)]

shelf_B[0].position = [0.15, 4.04, 0.90]
shelf_B[0].rotation = [0, 0, radians(0)]

# Keep the tables in the open interior. These locations avoid the bottom
# door/window approaches, the left door at y=4.79, and the upper doorway.
table_A[0].position = [2.10, 4.90, 0.375]
table_A[0].rotation = [0, 0, radians(0)]

table_B[0].position = [3.65, 3.45, 0.375]
table_B[0].rotation = [0, 0, radians(90)]

# Place the small pot at the center of table_A's top surface.
pot[0].position = [2.10, 4.90, 0.90]
pot[0].rotation = [0, 0, radians(0)]

# Fixed anchors preserve the intended positions and, in particular, the
# ordering of the storage units along the left wall.
shelf_A_anchor = AssetInstance(position=[0.175, 0.49, 0.90])
wardrobe_anchor = AssetInstance(position=[0.30, 1.865, 1.05])
shelf_C_anchor = AssetInstance(position=[0.15, 3.19, 0.90])
shelf_B_anchor = AssetInstance(position=[0.15, 4.04, 0.90])
table_A_anchor = AssetInstance(position=[2.10, 4.90, 0.375])
table_B_anchor = AssetInstance(position=[3.65, 3.45, 0.375])
pot_anchor = AssetInstance(position=[2.10, 4.90, 0.90])

# Orientation references make the storage fronts face into the room and
# preserve the selected perpendicular relationship between the two tables.
east_facing_reference = AssetInstance(rotation=[0, 0, radians(0)])
north_facing_reference = AssetInstance(rotation=[0, 0, radians(90)])

# Storage-unit position constraints. The exact anchors retain their
# non-overlapping longitudinal positions, while against_wall keeps their
# backs flush with the left boundary if feasibility adjustment is needed.
solver.distance_constraint(
    shelf_A[0], shelf_A_anchor, 0.0, 0.0, weight=10
)
solver.against_wall(shelf_A[0], walls[0])
solver.align_with(shelf_A[0], east_facing_reference)

solver.distance_constraint(
    wardrobe[0], wardrobe_anchor, 0.0, 0.0, weight=10
)
solver.against_wall(wardrobe[0], walls[0])
solver.align_with(wardrobe[0], east_facing_reference)

solver.distance_constraint(
    shelf_C[0], shelf_C_anchor, 0.0, 0.0, weight=10
)
solver.against_wall(shelf_C[0], walls[0])
solver.align_with(shelf_C[0], east_facing_reference)

solver.distance_constraint(
    shelf_B[0], shelf_B_anchor, 0.0, 0.0, weight=10
)
solver.against_wall(shelf_B[0], walls[0])
solver.align_with(shelf_B[0], east_facing_reference)

# The shelf centers are 0.85 m apart. Since both shelves are 0.80 m wide
# along the wall, this maintains a 0.05 m edge gap (no more than 0.10 m).
solver.distance_constraint(
    shelf_C[0], shelf_B[0], 0.80, 0.90, weight=10
)
solver.distance_constraint(
    shelf_B[0], shelf_C[0], 0.80, 0.90, weight=10
)

# Preserve the wardrobe's intended relationship to the shelves on either
# side: its center remains approximately midway between shelf_A and shelf_C.
solver.distance_constraint(
    wardrobe[0], shelf_A[0], 1.35, 1.40, weight=5
)
solver.distance_constraint(
    wardrobe[0], shelf_C[0], 1.30, 1.35, weight=5
)

# Interior table position and orientation constraints.
solver.distance_constraint(
    table_A[0], table_A_anchor, 0.0, 0.0, weight=10
)
solver.align_with(table_A[0], east_facing_reference)

solver.distance_constraint(
    table_B[0], table_B_anchor, 0.0, 0.0, weight=10
)
solver.align_with(table_B[0], north_facing_reference)

# The pot receives a z-axis support constraint as well as independent
# position and orientation constraints, as required for every new instance.
solver.on_top_of(pot[0], table_A[0])
solver.distance_constraint(
    pot[0], pot_anchor, 0.0, 0.0, weight=10
)
solver.align_with(pot[0], table_A[0])

solver.constraints = []
shelf_C[0].position = [0.14748866856098175, 3.190000057220459, 0.8999999761581421]
shelf_C[0].rotation = [0, 0, 0.0026546960467839914]
shelf_C[0].optimize = 2
pot[0].position = [2.0999999046325684, 4.900000095367432, 0.8999999761581421]
pot[0].rotation = [0, 0, 0.016395029648726894]
pot[0].optimize = 2
wardrobe[0].position = [0.3124975562095642, 1.8843891620635986, 1.0499999523162842]
wardrobe[0].rotation = [0, 0, 0.005288095987690255]
wardrobe[0].optimize = 2
table_A[0].position = [2.0999999046325684, 4.900000095367432, 0.375]
table_A[0].rotation = [0, 0, 0.0157079639172164]
table_A[0].optimize = 2
shelf_A[0].position = [0.17578111588954926, 0.5321999192237854, 0.8999999761581421]
shelf_A[0].rotation = [0, 0, 0.006142303543186067]
shelf_A[0].optimize = 2
table_B[0].position = [3.6500000953674316, 3.450000047683716, 0.375]
table_B[0].rotation = [0, 0, 1.5802211042556205]
table_B[0].optimize = 2
shelf_B[0].position = [0.14985349774360657, 4.039999961853027, 0.8999999761581421]
shelf_B[0].rotation = [0, 0, 0.0053008984474949864]
shelf_B[0].optimize = 2

