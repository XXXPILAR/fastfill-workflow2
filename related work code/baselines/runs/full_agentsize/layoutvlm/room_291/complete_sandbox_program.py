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
    Wall(corner1=[3.94, 1.37, 0.00], corner2=[0.00, 1.37, 0.00]),
    Wall(corner1=[0.00, 1.37, 0.00], corner2=[0.00, 0.15, 0.00]),
    Wall(corner1=[0.00, 0.15, 0.00], corner2=[2.62, 0.15, 0.00]),
    Wall(corner1=[2.62, 0.15, 0.00], corner2=[2.62, 0.00, 0.00]),
    Wall(corner1=[2.62, 0.00, 0.00], corner2=[3.63, 0.00, 0.00]),
    Wall(corner1=[3.63, 0.00, 0.00], corner2=[3.63, 0.15, 0.00]),
    Wall(corner1=[3.63, 0.15, 0.00], corner2=[3.94, 0.15, 0.00]),
    Wall(corner1=[3.94, 0.15, 0.00], corner2=[3.94, 1.37, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
cabinet = Assets(description="cabinet", size=[0.35, 1.00, 0.85], placements=[AssetInstance() for _ in range(1)])
mirror = Assets(description="mirror", size=[0.03, 0.80, 1.10], placements=[AssetInstance() for _ in range(1)])

cabinet[0].instance_id = 'cabinet_0'
mirror[0].instance_id = 'mirror_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

cabinet[0].position = [1.3757334115916924, 0.7313783758583655, 0.425]
cabinet[0].rotation = [0, 0, 0]
mirror[0].position = [2.441616913139673, 0.2366989608260831, 0.55]
mirror[0].rotation = [0, 0, 0]
cabinet[0].position = [1.3757334115916924, 0.7313783758583655, 0.425]
cabinet[0].rotation = [0, 0, 0]
mirror[0].position = [2.441616913139673, 0.2366989608260831, 0.55]
mirror[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the uninterrupted section of the north wall, immediately east of the
# 1.58 m doorway. Both objects face south into the room. This leaves the
# bottom and east-side door approaches unobstructed.
cabinet[0].position = [2.58, 1.195, 0.425]
cabinet[0].rotation = [0, 0, radians(-90)]

# Mount the mirror directly above the cabinet. Its back is flush with the
# north wall, while its bottom touches the cabinet's top.
mirror[0].position = [2.58, 1.355, 1.400]
mirror[0].rotation = [0, 0, radians(-90)]

# A reference point inside the room makes both assets face away from the
# north wall and toward the usable interior.
interior_reference = AssetInstance(position=[2.58, 0.65, 0.90])

# Wall attachment is the primary positional requirement.
solver.against_wall(cabinet[0], walls[0])
solver.against_wall(mirror[0], walls[0])

# Keep the mirror vertically supported by and centered over the cabinet.
solver.on_top_of(mirror[0], cabinet[0])

# The center-distance bounds account for the objects' half-heights:
# 0.85 / 2 + 1.10 / 2 = 0.975 m. The extra 0.10 m permits at most the
# requested 10 cm separation between their nearest surfaces.
solver.distance_constraint(
    mirror[0], cabinet[0],
    min_distance=0.975,
    max_distance=1.075,
    weight=10
)

# Orientation constraints for every new instance.
solver.point_towards(cabinet[0], interior_reference)
solver.point_towards(mirror[0], interior_reference)
solver.align_with(mirror[0], cabinet[0])

solver.constraints = []
cabinet[0].position = [2.7974913120269775, 0.5015490055084229, 0.42500001192092896]
cabinet[0].rotation = [0, 0, 0.008966263564190294]
cabinet[0].optimize = 2
mirror[0].position = [2.6180152893066406, 0.9999598264694214, 1.4000000953674316]
mirror[0].rotation = [0, 0, -1.5707996704131129]
mirror[0].optimize = 2

