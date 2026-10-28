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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.47, 0.00, 0.00]),
    Wall(corner1=[2.47, 0.00, 0.00], corner2=[2.47, 3.15, 0.00]),
    Wall(corner1=[2.47, 3.15, 0.00], corner2=[0.00, 3.15, 0.00]),
    Wall(corner1=[0.00, 3.15, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
clothes_rack = Assets(description="clothes rack", size=[0.45, 1.00, 1.70], placements=[AssetInstance() for _ in range(1)])
sofa = Assets(description="sofa", size=[0.85, 1.90, 0.85], placements=[AssetInstance() for _ in range(1)])

clothes_rack[0].instance_id = 'clothes_rack_0'
sofa[0].instance_id = 'sofa_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

clothes_rack[0].position = [0.6781317761491807, 2.2288123444330457, 0.85]
clothes_rack[0].rotation = [0, 0, 0]
sofa[0].position = [0.47387501865671694, 1.4307035966119959, 0.425]
sofa[0].rotation = [0, 0, 0]
clothes_rack[0].position = [0.6781317761491807, 2.2288123444330457, 0.85]
clothes_rack[0].rotation = [0, 0, 0]
sofa[0].position = [0.47387501865671694, 1.4307035966119959, 0.425]
sofa[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the sofa along the right wall, facing into the room. Its position
# leaves both the bottom-right doorway and the upper-left doorway approaches clear.
sofa[0].position = [2.045, 1.75, 0.425]
sofa[0].rotation = [0, 0, radians(180)]

# Place the clothes rack against the lower portion of the left wall, facing
# into the room. This keeps it away from both doorway circulation paths.
clothes_rack[0].position = [0.225, 0.65, 0.85]
clothes_rack[0].rotation = [0, 0, radians(0)]

# Fixed anchors preserve the selected locations while the solver makes
# small adjustments for physical feasibility.
sofa_anchor = AssetInstance(position=[2.045, 1.75, 0.425])
rack_anchor = AssetInstance(position=[0.225, 0.65, 0.85])

# The sofa must remain against the right wall and face toward the room.
solver.against_wall(sofa[0], walls[1])
solver.distance_constraint(sofa[0], sofa_anchor, 0, 0, weight=10)
solver.point_towards(sofa[0], clothes_rack[0])

# Keep the rack against the left wall and oriented toward the usable room area.
solver.against_wall(clothes_rack[0], walls[3])
solver.distance_constraint(clothes_rack[0], rack_anchor, 0, 0, weight=10)
solver.point_towards(clothes_rack[0], sofa[0])

# Maintain ample center-to-center separation so the two assets cannot overlap
# and a useful circulation aisle remains between them.
solver.distance_constraint(sofa[0], clothes_rack[0], 1.70, None, weight=10)
solver.distance_constraint(clothes_rack[0], sofa[0], 1.70, None, weight=10)

solver.constraints = []
sofa[0].position = [2.0450000762939453, 1.75, 0.42500001192092896]
sofa[0].rotation = [0, 0, -3.1415926244342183]
sofa[0].optimize = 2
clothes_rack[0].position = [0.22499999403953552, 0.6499999761581421, 0.8500000238418579]
clothes_rack[0].rotation = [0, 0, 3.595691742006396e-08]
clothes_rack[0].optimize = 2

