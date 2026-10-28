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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[8.74, 0.00, 0.00]),
    Wall(corner1=[8.74, 0.00, 0.00], corner2=[8.74, 6.04, 0.00]),
    Wall(corner1=[8.74, 6.04, 0.00], corner2=[0.00, 6.04, 0.00]),
    Wall(corner1=[0.00, 6.04, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
seat = Assets(description="A modern office chair with a wooden frame and a brown leather cushioned seat. It features a unique backrest design that curves outward and has five swivel wheels for mobility.", size=[0.68, 0.65, 0.95], placements=[AssetInstance() for _ in range(1)])
drawer_desk = Assets(description="A classic wooden writing desk with multiple drawers and ornate legs, designed for elegant office or study settings.", size=[0.75, 1.50, 0.78], placements=[AssetInstance() for _ in range(1)])

seat[0].instance_id = 'seat_0'
drawer_desk[0].instance_id = 'drawer_desk_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

seat[0].position = [8.380551772370206, 0.6005979770986702, 0.475]
seat[0].rotation = [0, 0, 0]
drawer_desk[0].position = [0.055368465692994855, 5.196152900890274, 0.39]
drawer_desk[0].rotation = [0, 0, 0]
seat[0].position = [8.380551772370206, 0.6005979770986702, 0.475]
seat[0].rotation = [0, 0, 0]
drawer_desk[0].position = [0.055368465692994855, 5.196152900890274, 0.39]
drawer_desk[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the chair flush with the bottom wall and facing into the room.
seat[0].position = [6.20, 0.34, 0.475]
seat[0].rotation = [0, 0, radians(90)]

# Rotate the desk so its 1.50 m dimension runs parallel to the wall.
# Its nearest edge is 0.15 m from the chair, providing a close but
# non-overlapping working arrangement. This is also well clear of the beam.
drawer_desk[0].position = [6.20, 1.205, 0.39]
drawer_desk[0].rotation = [0, 0, radians(-90)]

# Keep the chair against the bottom wall, as required.
solver.against_wall(seat[0], walls[0])

# Make the chair face the desk and the working side of the desk face the chair.
solver.point_towards(seat[0], drawer_desk[0])
solver.point_towards(drawer_desk[0], seat[0])

# With these rotations, the chair and desk have half-depths of 0.34 m and
# 0.375 m. Center distances of 0.715-0.915 m therefore represent an
# edge-to-edge separation of 0.00-0.20 m without allowing overlap.
solver.distance_constraint(
    drawer_desk[0], seat[0],
    min_distance=0.715,
    max_distance=0.915,
    weight=10
)

# Give the chair an additional position relationship while preserving the
# wall constraint; the same non-overlapping proximity interval applies.
solver.distance_constraint(
    seat[0], drawer_desk[0],
    min_distance=0.715,
    max_distance=0.915,
    weight=10
)

solver.constraints = []
drawer_desk[0].position = [6.199999809265137, 1.2050000429153442, 0.38999998569488525]
drawer_desk[0].rotation = [0, 0, -1.5550883628776802]
drawer_desk[0].optimize = 2
seat[0].position = [6.199999809265137, 0.3399999439716339, 0.4749999940395355]
seat[0].rotation = [0, 0, 1.5707962747318887]
seat[0].optimize = 2

