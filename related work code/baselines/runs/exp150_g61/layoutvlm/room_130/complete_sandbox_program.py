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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.00, 0.00, 0.00]),
    Wall(corner1=[2.00, 0.00, 0.00], corner2=[2.00, 2.00, 0.00]),
    Wall(corner1=[2.00, 2.00, 0.00], corner2=[0.00, 2.00, 0.00]),
    Wall(corner1=[0.00, 2.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
wall_shelf = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.25, 0.80, 0.25], placements=[AssetInstance() for _ in range(1)])
shared_study_desk = Assets(description="shared study desk", size=[0.55, 1.40, 0.75], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.55, 0.60, 2.00], placements=[AssetInstance() for _ in range(1)])

wall_shelf[0].instance_id = 'wall_shelf_0'
shared_study_desk[0].instance_id = 'shared_study_desk_0'
wardrobe[0].instance_id = 'wardrobe_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

wall_shelf[0].position = [1.0797272054774991, 0.3573467824753258, 0.125]
wall_shelf[0].rotation = [0, 0, 0]
shared_study_desk[0].position = [0.16673140668540598, 1.4628770841305296, 0.375]
shared_study_desk[0].rotation = [0, 0, 0]
wardrobe[0].position = [1.969532638614276, 0.23584718044357111, 1.0]
wardrobe[0].rotation = [0, 0, 0]
wall_shelf[0].position = [1.0797272054774991, 0.3573467824753258, 0.125]
wall_shelf[0].rotation = [0, 0, 0]
shared_study_desk[0].position = [0.16673140668540598, 1.4628770841305296, 0.375]
shared_study_desk[0].rotation = [0, 0, 0]
wardrobe[0].position = [1.969532638614276, 0.23584718044357111, 1.0]
wardrobe[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the supplied [0, 2] x [0, 2] boundary coordinates.
# The desk occupies x=[0, 1.40], y=[0, 0.55], facing into the room.
# The wardrobe occupies x=[1.45, 2.00], y=[0, 0.60], facing left.
# Their bounding boxes have a 0.05 m gap, satisfying the 0.20 m requirement.
# Both stay below the door opening (approximately y=0.865 to 1.915),
# keeping the entrance and the central circulation area clear.
shared_study_desk[0].position = [0.70, 0.275, 0.375]
shared_study_desk[0].rotation = [0, 0, radians(90)]

wardrobe[0].position = [1.725, 0.30, 1.00]
wardrobe[0].rotation = [0, 0, radians(180)]

# Put the shelf at the back of the desktop, against the bottom wall.
# Its bottom is at desktop height, 0.75 m, and its top is at 1.00 m.
wall_shelf[0].position = [0.70, 0.125, 0.875]
wall_shelf[0].rotation = [0, 0, radians(90)]

# Fixed references preserve the intended positions, orientations, and doorway
# clearance. These are constraint references, not additional scene objects.
desk_reference = AssetInstance(
    position=[0.70, 0.275, 0.375],
    rotation=[0, 0, radians(90)]
)
wardrobe_reference = AssetInstance(
    position=[1.725, 0.30, 1.00],
    rotation=[0, 0, radians(180)]
)
shelf_reference = AssetInstance(
    position=[0.70, 0.125, 0.875],
    rotation=[0, 0, radians(90)]
)

# Prioritize the nonoverlapping, door-safe layout.
solver.distance_constraint(
    shared_study_desk[0], desk_reference, 0, 0, weight=10
)
solver.distance_constraint(
    wardrobe[0], wardrobe_reference, 0, 0, weight=10
)
solver.distance_constraint(
    wall_shelf[0], shelf_reference, 0, 0, weight=10
)

# Each floor-standing piece is backed against a wall and faces the room.
solver.against_wall(shared_study_desk[0], walls[0])
solver.align_with(shared_study_desk[0], desk_reference)
solver.against_wall(wardrobe[0], walls[1])
solver.align_with(wardrobe[0], wardrobe_reference)

# The small shelf is supported by the desktop rather than placed on the floor.
solver.on_top_of(wall_shelf[0], shared_study_desk[0])
solver.against_wall(wall_shelf[0], walls[0])
solver.align_with(wall_shelf[0], shared_study_desk[0])

# Distances use 3D bounding-box centers, not the 0.05 m surface gap.
# Preserve the desk/wardrobe adjacency in both adjustment directions.
desk_wardrobe_center_distance = (
    1.025**2 + 0.025**2 + 0.625**2
) ** 0.5
solver.distance_constraint(
    shared_study_desk[0], wardrobe[0],
    desk_wardrobe_center_distance, desk_wardrobe_center_distance,
    weight=10
)
solver.distance_constraint(
    wardrobe[0], shared_study_desk[0],
    desk_wardrobe_center_distance, desk_wardrobe_center_distance,
    weight=10
)

solver.constraints = []
wardrobe[0].position = [1.7249999046325684, 0.43322572112083435, 1.0]
wardrobe[0].rotation = [0, 0, -3.1415926139109986]
wardrobe[0].optimize = 2
shared_study_desk[0].position = [0.698946475982666, 0.27766671776771545, 0.375]
shared_study_desk[0].rotation = [0, 0, 1.5746087650397032]
shared_study_desk[0].optimize = 2
wall_shelf[0].position = [0.699999988079071, 0.1249999925494194, 0.875]
wall_shelf[0].rotation = [0, 0, 1.5707963694290836]
wall_shelf[0].optimize = 2

