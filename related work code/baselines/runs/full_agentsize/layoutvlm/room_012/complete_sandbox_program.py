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
    Wall(corner1=[3.19, 3.70, 0.00], corner2=[0.00, 3.70, 0.00]),
    Wall(corner1=[0.00, 3.70, 0.00], corner2=[0.00, 1.26, 0.00]),
    Wall(corner1=[0.00, 1.26, 0.00], corner2=[1.95, 1.26, 0.00]),
    Wall(corner1=[1.95, 1.26, 0.00], corner2=[1.95, 0.00, 0.00]),
    Wall(corner1=[1.95, 0.00, 0.00], corner2=[3.19, 0.00, 0.00]),
    Wall(corner1=[3.19, 0.00, 0.00], corner2=[3.19, 3.70, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
desk = Assets(description="A modern desk with a sleek design, featuring a lamp, potted plants, and decorative items. The desk has a wooden surface with metal legs and is accompanied by floating shelves holding a bicycle model.", size=[0.60, 1.40, 0.75], placements=[AssetInstance() for _ in range(1)])
floor_lamp = Assets(description="A modern floor lamp with an adjustable arm and multiple light sources. It features a sleek design with a central pole and a circular base for stability.", size=[0.35, 0.35, 1.75], placements=[AssetInstance() for _ in range(1)])
bookcase = Assets(description="A tall, modern bookshelf with multiple shelves holding books, decorative items, and small plants.", size=[0.30, 0.90, 2.10], placements=[AssetInstance() for _ in range(1)])
barstool = Assets(description="A modern bar stool with a sleek wooden seat and black metal legs. The seat has a curved design for comfort, and the legs are supported by a square base for stability.", size=[0.45, 0.45, 0.75], placements=[AssetInstance() for _ in range(1)])

desk[0].instance_id = 'desk_0'
floor_lamp[0].instance_id = 'floor_lamp_0'
bookcase[0].instance_id = 'bookcase_0'
barstool[0].instance_id = 'barstool_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

desk[0].position = [0.11961798374566547, 2.0885069834603134, 0.375]
desk[0].rotation = [0, 0, 0]
floor_lamp[0].position = [1.389506521294994, 2.938990135908333, 0.875]
floor_lamp[0].rotation = [0, 0, 0]
bookcase[0].position = [3.0710128888701074, 2.385116657450603, 1.05]
bookcase[0].rotation = [0, 0, 0]
barstool[0].position = [2.8456592022797897, 1.0883603248167508, 0.375]
barstool[0].rotation = [0, 0, 0]
desk[0].position = [0.11961798374566547, 2.0885069834603134, 0.375]
desk[0].rotation = [0, 0, 0]
floor_lamp[0].position = [1.389506521294994, 2.938990135908333, 0.875]
floor_lamp[0].rotation = [0, 0, 0]
bookcase[0].position = [3.0710128888701074, 2.385116657450603, 1.05]
bookcase[0].rotation = [0, 0, 0]
barstool[0].position = [2.8456592022797897, 1.0883603248167508, 0.375]
barstool[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the furniture along the north wall, leaving the door area on the
# west side and the window on the east side unobstructed.
desk[0].position = [1.65, 3.40, 0.375]
desk[0].rotation = [0, 0, radians(-90)]

floor_lamp[0].position = [2.625, 3.40, 0.875]
floor_lamp[0].rotation = [0, 0, radians(-90)]

bookcase[0].position = [0.45, 3.55, 1.05]
bookcase[0].rotation = [0, 0, radians(-90)]

barstool[0].position = [2.625, 2.90, 0.375]
barstool[0].rotation = [0, 0, radians(90)]


# High-priority anchors preserve the non-overlapping arrangement and keep the
# circulation route from the door at (0.00, 1.78) clear.
desk_anchor = AssetInstance(position=[1.65, 3.40, 0.375])
lamp_anchor = AssetInstance(position=[2.625, 3.40, 0.875])
bookcase_anchor = AssetInstance(position=[0.45, 3.55, 1.05])
barstool_anchor = AssetInstance(position=[2.625, 2.90, 0.375])

solver.distance_constraint(desk[0], desk_anchor, 0, 0, weight=10)
solver.distance_constraint(floor_lamp[0], lamp_anchor, 0, 0, weight=10)
solver.distance_constraint(bookcase[0], bookcase_anchor, 0, 0, weight=10)
solver.distance_constraint(barstool[0], barstool_anchor, 0, 0, weight=10)


# Both required wall-mounted pieces use the uninterrupted north wall. Their
# rotations make their fronts face south into the usable part of the room.
solver.against_wall(desk[0], walls[0])
solver.against_wall(bookcase[0], walls[0])

south_facing_reference = AssetInstance(
    position=[1.65, 2.40, 0.375],
    rotation=[0, 0, radians(-90)]
)
solver.point_towards(desk[0], south_facing_reference)
solver.align_with(bookcase[0], desk[0])


# Keep the lamp beside the desk. Since this API measures center-to-center
# distance, 0.875 m is touching distance for their rotated bounding boxes
# (0.70 m + 0.175 m); 0.975 m represents a clear edge gap of 0.10 m.
solver.distance_constraint(desk[0], floor_lamp[0], 0.875, 0.975, weight=10)
solver.align_with(floor_lamp[0], desk[0])


# The stool is exactly 0.50 m from the lamp, with a 0.10 m edge clearance
# between their bases, and faces toward the lamp.
solver.distance_constraint(barstool[0], floor_lamp[0], 0.50, 0.50, weight=10)
solver.point_towards(barstool[0], floor_lamp[0])

solver.constraints = []
bookcase[0].position = [0.492201030254364, 3.5504069328308105, 1.0499999523162842]
bookcase[0].rotation = [0, 0, -1.5665522609154225]
bookcase[0].optimize = 2
floor_lamp[0].position = [2.625, 3.4000000953674316, 0.875]
floor_lamp[0].rotation = [0, 0, -1.5945025612772308]
floor_lamp[0].optimize = 2
barstool[0].position = [2.625, 2.9000000953674316, 0.375]
barstool[0].rotation = [0, 0, 1.5833626980517244]
barstool[0].optimize = 2
desk[0].position = [1.649999976158142, 3.3937506675720215, 0.375]
desk[0].rotation = [0, 0, -1.5681604675054204]
desk[0].optimize = 2

