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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[8.56, 0.00, 0.00]),
    Wall(corner1=[8.56, 0.00, 0.00], corner2=[8.56, 6.22, 0.00]),
    Wall(corner1=[8.56, 6.22, 0.00], corner2=[0.00, 6.22, 0.00]),
    Wall(corner1=[0.00, 6.22, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
seat = Assets(description="An ergonomic office chair with a mesh backrest, padded seat, and adjustable armrests. It features a five-point base with casters for mobility.", size=[0.68, 0.68, 1.15], placements=[AssetInstance() for _ in range(1)])
drawer_desk = Assets(description="A white desk with a rectangular tabletop supported by two large side panels. It features multiple drawers with silver handles, providing ample storage space. The design is simple yet elegant, suitable for an office or study area.", size=[0.75, 1.50, 0.76], placements=[AssetInstance() for _ in range(1)])
file_cabinet = Assets(description="A black filing cabinet with two drawers, each featuring a beige panel and a handle. The cabinet has a sturdy build suitable for office storage.", size=[0.62, 0.46, 0.72], placements=[AssetInstance() for _ in range(1)])

seat[0].instance_id = 'seat_0'
drawer_desk[0].instance_id = 'drawer_desk_0'
file_cabinet[0].instance_id = 'file_cabinet_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

seat[0].position = [2.6341824562269394, 5.78662760356539, 0.575]
seat[0].rotation = [0, 0, 0]
drawer_desk[0].position = [2.7031099075546106, 4.960113627575867, 0.38]
drawer_desk[0].rotation = [0, 0, 0]
file_cabinet[0].position = [5.959469224572275, 0.6264121768205673, 0.36]
file_cabinet[0].rotation = [0, 0, 0]
seat[0].position = [2.6341824562269394, 5.78662760356539, 0.575]
seat[0].rotation = [0, 0, 0]
drawer_desk[0].position = [2.7031099075546106, 4.960113627575867, 0.38]
drawer_desk[0].rotation = [0, 0, 0]
file_cabinet[0].position = [5.959469224572275, 0.6264121768205673, 0.36]
file_cabinet[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the three assets in a compact office/storage run along the north wall.
# The desk and chair are side-by-side because both are required to be against a
# wall. Their nearest bounding-box edges are approximately 0.11 m apart.
seat[0].position = [3.08, 5.88, 0.575]
seat[0].rotation = [0, 0, radians(-90)]

drawer_desk[0].position = [4.28, 5.845, 0.38]
drawer_desk[0].rotation = [0, 0, radians(-90)]

file_cabinet[0].position = [5.36, 5.91, 0.36]
file_cabinet[0].rotation = [0, 0, radians(-90)]

# A fixed orientation reference makes every asset face south, into the room.
south_facing_reference = AssetInstance(rotation=[0, 0, radians(-90)])

# Required wall relationships are specified first because they are the most
# important positional constraints.
solver.against_wall(drawer_desk[0], walls[2])
solver.against_wall(seat[0], walls[2])
solver.against_wall(file_cabinet[0], walls[2])

# With the desk rotated 90 degrees, its width along the wall is 1.50 m.
# The chair's width is 0.68 m, so non-overlap requires at least
# 1.50 / 2 + 0.68 / 2 = 1.09 m between centers. A maximum of 1.29 m
# corresponds to no more than 0.20 m between their nearest surfaces.
solver.distance_constraint(
    drawer_desk[0], seat[0],
    min_distance=1.09, max_distance=1.29, weight=10
)

# Keep the filing cabinet beside the desk with approximately 0.10 m clearance.
# Their required non-overlapping center distance along the wall is
# 1.50 / 2 + 0.46 / 2 = 0.98 m.
solver.distance_constraint(
    file_cabinet[0], drawer_desk[0],
    min_distance=0.98, max_distance=1.18, weight=5
)

# Preserve separation between the chair and filing cabinet as an additional
# safeguard against overlap if the solver adjusts the wall arrangement.
solver.distance_constraint(
    file_cabinet[0], seat[0],
    min_distance=2.07, max_distance=2.50, weight=1
)

# Orientation constraints for every newly placed asset.
solver.align_with(drawer_desk[0], south_facing_reference)
solver.align_with(seat[0], south_facing_reference)
solver.align_with(file_cabinet[0], south_facing_reference)

solver.constraints = []
drawer_desk[0].position = [4.28000020980835, 5.841233730316162, 0.3799999952316284]
drawer_desk[0].rotation = [0, 0, -1.5707962841901204]
drawer_desk[0].optimize = 2
seat[0].position = [3.0799999237060547, 5.87623405456543, 0.574999988079071]
seat[0].rotation = [0, 0, -1.5707962840388354]
seat[0].optimize = 2
file_cabinet[0].position = [5.360000133514404, 5.9062347412109375, 0.36000001430511475]
file_cabinet[0].rotation = [0, 0, -1.570796284220033]
file_cabinet[0].optimize = 2

