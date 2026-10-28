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
wall_shelf = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.22, 0.80, 0.25], placements=[AssetInstance() for _ in range(1)])
shared_study_desk = Assets(description="shared study desk", size=[0.55, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.55, 0.70, 1.90], placements=[AssetInstance() for _ in range(1)])

wall_shelf[0].instance_id = 'wall_shelf_0'
shared_study_desk[0].instance_id = 'shared_study_desk_0'
wardrobe[0].instance_id = 'wardrobe_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

wall_shelf[0].position = [1.3916103457164082, 0.46688376355462724, 0.125]
wall_shelf[0].rotation = [0, 0, 0]
shared_study_desk[0].position = [0.6847979958023698, 0.2960152923256463, 0.375]
shared_study_desk[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.6449271881008114, 1.6543653148977309, 0.95]
wardrobe[0].rotation = [0, 0, 0]
wall_shelf[0].position = [1.3916103457164082, 0.46688376355462724, 0.125]
wall_shelf[0].rotation = [0, 0, 0]
shared_study_desk[0].position = [0.6847979958023698, 0.2960152923256463, 0.375]
shared_study_desk[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.6449271881008114, 1.6543653148977309, 0.95]
wardrobe[0].rotation = [0, 0, 0]

solver.constraints = []

# Keep the furniture in the lower part of the room so the 1.05 m-wide
# doorway centered on the left wall at (0.00, 1.39) remains unobstructed.
room_center = AssetInstance(position=[1.00, 1.00, 0.00])

# Rotate the desk so its 1.20 m dimension runs along the bottom wall.
shared_study_desk[0].position = [0.65, 0.275, 0.375]
shared_study_desk[0].rotation = [0, 0, radians(90)]

# Place the wardrobe in the lower-right corner. Its front faces into the room.
wardrobe[0].position = [1.725, 0.35, 0.95]
wardrobe[0].rotation = [0, 0, radians(180)]

# Put the shelf on the rear portion of the desktop. Its rotated footprint is
# 0.80 m along x and 0.22 m along y, so it fits fully on the desk.
wall_shelf[0].position = [0.65, 0.11, 0.875]
wall_shelf[0].rotation = [0, 0, radians(90)]

# The desk must remain against the bottom wall and face into the room.
solver.against_wall(shared_study_desk[0], walls[0])
solver.point_towards(shared_study_desk[0], room_center)

# Keep the wardrobe against the right wall and oriented toward the interior.
solver.against_wall(wardrobe[0], walls[1])
solver.point_towards(wardrobe[0], room_center)

# The shelf is supported by the desk and kept along its wall-side edge.
solver.on_top_of(wall_shelf[0], shared_study_desk[0])
solver.against_wall(wall_shelf[0], walls[0])
solver.align_with(wall_shelf[0], shared_study_desk[0])

# The distance API measures center-to-center distance. With the desk rotated,
# their facing half-widths total 0.875 m, so a maximum center distance of
# 1.08 m preserves no more than approximately 0.20 m of edge-to-edge spacing.
solver.distance_constraint(
    shared_study_desk[0],
    wardrobe[0],
    min_distance=0.88,
    max_distance=1.08,
    weight=10,
)

solver.constraints = []
wardrobe[0].position = [1.7250031232833862, 0.4012714922428131, 0.949999988079071]
wardrobe[0].rotation = [0, 0, 3.1415886866953007]
wardrobe[0].optimize = 2
wall_shelf[0].position = [0.6499999761581421, 0.11000452935695648, 0.875]
wall_shelf[0].rotation = [0, 0, 1.5707929848170032]
wall_shelf[0].optimize = 2
shared_study_desk[0].position = [0.6499999761581421, 0.27499526739120483, 0.375]
shared_study_desk[0].rotation = [0, 0, 1.5708002683279707]
shared_study_desk[0].optimize = 2

