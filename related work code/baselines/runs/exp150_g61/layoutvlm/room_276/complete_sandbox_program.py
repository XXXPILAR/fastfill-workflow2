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
    Wall(corner1=[2.76, 3.35, 0.00], corner2=[0.00, 3.35, 0.00]),
    Wall(corner1=[0.00, 3.35, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.76, 0.00, 0.00]),
    Wall(corner1=[2.76, 0.00, 0.00], corner2=[2.76, 3.35, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
chair = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.00, 1.35, 0.55], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="cabinet", size=[0.45, 0.80, 1.80], placements=[AssetInstance() for _ in range(1)])
desk = Assets(description="desk", size=[0.55, 1.00, 0.75], placements=[AssetInstance() for _ in range(1)])

chair[0].instance_id = 'chair_0'
bed[0].instance_id = 'bed_0'
cabinet[0].instance_id = 'cabinet_0'
desk[0].instance_id = 'desk_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

chair[0].position = [0.992173093825829, 2.149695508110831, 0.425]
chair[0].rotation = [0, 0, 0]
bed[0].position = [1.3370207184669503, 3.285838820788059, 0.275]
bed[0].rotation = [0, 0, 0]
cabinet[0].position = [0.06758519946330875, 0.9867941697866633, 0.9]
cabinet[0].rotation = [0, 0, 0]
desk[0].position = [2.161486985373236, 3.038165558203036, 0.375]
desk[0].rotation = [0, 0, 0]
chair[0].position = [0.992173093825829, 2.149695508110831, 0.425]
chair[0].rotation = [0, 0, 0]
bed[0].position = [1.3370207184669503, 3.285838820788059, 0.275]
bed[0].rotation = [0, 0, 0]
cabinet[0].position = [0.06758519946330875, 0.9867941697866633, 0.9]
cabinet[0].rotation = [0, 0, 0]
desk[0].position = [2.161486985373236, 3.038165558203036, 0.375]
desk[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the supplied wall coordinates: the room occupies x=[0, 2.76],
# y=[0, 3.35]. Keep the doorway and its approach at the lower left clear.

# Bed along the upper wall: footprint x=[0, 2.00], y=[2.00, 3.35].
bed[0].position = [1.00, 2.675, 0.275]
bed[0].rotation = [0, 0, 0]

# Cabinet against the left wall, beyond the doorway approach.
# Footprint x=[0, 0.45], y=[1.10, 1.90]; its front faces into the room.
cabinet[0].position = [0.225, 1.50, 0.90]
cabinet[0].rotation = [0, 0, 0]

# Desk against the right wall, beside the lower portion of the window.
# Footprint x=[2.21, 2.76], y=[0.80, 1.80].
desk[0].position = [2.485, 1.30, 0.375]
desk[0].rotation = [0, 0, radians(180)]

# Chair faces the desk, with a 0.35 m gap between their bounding boxes.
# Its left side leaves an approximately 0.89 m passage past the cabinet.
chair[0].position = [1.60, 1.30, 0.425]
chair[0].rotation = [0, 0, 0]

# Fixed targets preserve the nonoverlapping footprints and the clear entrance.
# These are reference points, not additional physical scene assets.
solver.distance_constraint(
    bed[0], AssetInstance(position=[1.00, 2.675, 0.275]),
    0, 0, weight=10
)
solver.distance_constraint(
    cabinet[0], AssetInstance(position=[0.225, 1.50, 0.90]),
    0, 0, weight=10
)
solver.distance_constraint(
    desk[0], AssetInstance(position=[2.485, 1.30, 0.375]),
    0, 0, weight=10
)
solver.distance_constraint(
    chair[0], AssetInstance(position=[1.60, 1.30, 0.425]),
    0, 0, weight=10
)

# Specify the functional orientations before secondary constraints.
solver.point_towards(chair[0], desk[0])
solver.point_towards(desk[0], chair[0])
solver.align_with(
    cabinet[0],
    AssetInstance(position=[0.225, 1.50, 0.90], rotation=[0, 0, 0])
)
solver.align_with(
    bed[0],
    AssetInstance(position=[1.00, 2.675, 0.275], rotation=[0, 0, 0])
)

# Maintain wall contact without changing the chosen orientations.
solver.against_wall(cabinet[0], walls[1])
solver.against_wall(bed[0], walls[0])
solver.against_wall(desk[0], walls[3])

# Preserve a usable chair-to-desk spacing, accounting for center heights.
solver.distance_constraint(chair[0], desk[0], 0.85, 0.95, weight=10)

# All four assets stand on the floor; no on_top_of constraints are needed.

solver.constraints = []
cabinet[0].position = [0.22502964735031128, 1.5, 0.8999999761581421]
cabinet[0].rotation = [0, 0, -4.7037657186488826e-05]
cabinet[0].optimize = 2
bed[0].position = [1.2341200113296509, 2.352879762649536, 0.2750000059604645]
bed[0].rotation = [0, 0, -1.5720867284162503]
bed[0].optimize = 2
desk[0].position = [2.4801573753356934, 1.2999999523162842, 0.375]
desk[0].rotation = [0, 0, -3.1415213498088432]
desk[0].optimize = 2
chair[0].position = [1.600000023841858, 1.2999999523162842, 0.42500001192092896]
chair[0].rotation = [0, 0, 0.0157079639172164]
chair[0].optimize = 2

