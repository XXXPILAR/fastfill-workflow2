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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[8.23, 0.00, 0.00]),
    Wall(corner1=[8.23, 0.00, 0.00], corner2=[8.23, 7.51, 0.00]),
    Wall(corner1=[8.23, 7.51, 0.00], corner2=[0.00, 7.51, 0.00]),
    Wall(corner1=[0.00, 7.51, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
file_cabinet_A = Assets(description="A white drawer unit with five drawers, each featuring a black handle. It has a simple, modern design suitable for storage.", size=[0.58, 0.36, 0.70], placements=[AssetInstance() for _ in range(1)])
file_cabinet_B = Assets(description="A white drawer unit with five drawers, each featuring a black handle. It has a simple, modern design suitable for storage.", size=[0.58, 0.36, 0.70], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="A white bathroom cabinet with a sink on top, featuring a simple design with clean lines and a minimalist aesthetic.", size=[0.48, 0.80, 0.85], placements=[AssetInstance() for _ in range(1)])
drawer_desk = Assets(description="A sturdy workbench with a wooden tabletop and a white-painted frame. It features a lower shelf for additional storage space.", size=[0.60, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])

file_cabinet_A[0].instance_id = 'file_cabinet_A_0'
file_cabinet_B[0].instance_id = 'file_cabinet_B_0'
cabinet[0].instance_id = 'cabinet_0'
drawer_desk[0].instance_id = 'drawer_desk_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

file_cabinet_A[0].position = [2.0538057764507927, 7.1017036030274046, 0.35]
file_cabinet_A[0].rotation = [0, 0, 0]
file_cabinet_B[0].position = [6.229693068469876, 2.319663979272727, 0.35]
file_cabinet_B[0].rotation = [0, 0, 0]
cabinet[0].position = [4.4270345078281075, 5.417298801486182, 0.425]
cabinet[0].rotation = [0, 0, 0]
drawer_desk[0].position = [3.1135248540128253, 4.492810616560655, 0.45]
drawer_desk[0].rotation = [0, 0, 0]
file_cabinet_A[0].position = [2.0538057764507927, 7.1017036030274046, 0.35]
file_cabinet_A[0].rotation = [0, 0, 0]
file_cabinet_B[0].position = [6.229693068469876, 2.319663979272727, 0.35]
file_cabinet_B[0].rotation = [0, 0, 0]
cabinet[0].position = [4.4270345078281075, 5.417298801486182, 0.425]
cabinet[0].rotation = [0, 0, 0]
drawer_desk[0].position = [3.1135248540128253, 4.492810616560655, 0.45]
drawer_desk[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the workbench against the south wall, facing into the room.
drawer_desk[0].position = [3.60, 0.30, 0.45]
drawer_desk[0].rotation = [0, 0, radians(90)]

# The two compact drawer units fit side-by-side on the workbench. This satisfies
# the unusually small proximity requirements without creating floor-level overlaps.
file_cabinet_B[0].position = [3.80, 0.30, 1.25]
file_cabinet_B[0].rotation = [0, 0, radians(90)]

file_cabinet_A[0].position = [3.40, 0.30, 1.25]
file_cabinet_A[0].rotation = [0, 0, radians(90)]

# Put the sink cabinet against the north wall, facing south into the room.
cabinet[0].position = [6.50, 7.27, 0.425]
cabinet[0].rotation = [0, 0, radians(-90)]

# Fixed directional targets provide unambiguous inward-facing orientations.
desk_front_target = AssetInstance(position=[3.60, 3.75, 0.45])
cabinet_front_target = AssetInstance(position=[6.50, 3.75, 0.425])

# Preserve the primary requirement that the desk remain against a wall.
solver.against_wall(drawer_desk[0], walls[0])
solver.point_towards(drawer_desk[0], desk_front_target)

# Keep file cabinet B on the workbench and within 0.30 m of the desk in plan.
solver.on_top_of(file_cabinet_B[0], drawer_desk[0])
solver.distance_constraint(
    file_cabinet_B[0], drawer_desk[0],
    min_distance=0.0, max_distance=0.30, weight=10
)
solver.align_with(file_cabinet_B[0], drawer_desk[0])

# Keep file cabinet A beside B, while maintaining the required 0.50 m proximity.
solver.on_top_of(file_cabinet_A[0], drawer_desk[0])
solver.distance_constraint(
    file_cabinet_A[0], file_cabinet_B[0],
    min_distance=0.38, max_distance=0.50, weight=10
)
solver.align_with(file_cabinet_A[0], file_cabinet_B[0])

# The sink cabinet has its own wall-backed location away from the work area.
solver.against_wall(cabinet[0], walls[2])
solver.point_towards(cabinet[0], cabinet_front_target)

solver.constraints = []
drawer_desk[0].position = [3.5999999046325684, 0.3000194728374481, 0.44999998807907104]
drawer_desk[0].rotation = [0, 0, 1.5708264037214847]
drawer_desk[0].optimize = 2
cabinet[0].position = [6.5, 7.273475646972656, 0.42500001192092896]
cabinet[0].rotation = [0, 0, -1.5708169701926398]
cabinet[0].optimize = 2
file_cabinet_B[0].position = [4.139328956604004, 0.2899111807346344, 1.25]
file_cabinet_B[0].rotation = [0, 0, 1.5706310008719133]
file_cabinet_B[0].optimize = 2
file_cabinet_A[0].position = [3.6723341941833496, 0.2898510992527008, 1.25]
file_cabinet_A[0].rotation = [0, 0, 1.5709343117202184]
file_cabinet_A[0].optimize = 2

