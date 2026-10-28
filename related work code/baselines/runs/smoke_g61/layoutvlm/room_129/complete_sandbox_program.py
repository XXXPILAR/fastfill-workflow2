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
wall_shelf_A = Assets(description="A set of three wooden shelves.", size=[0.22, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
shared_wardrobe = Assets(description="shared wardrobe", size=[0.60, 1.20, 2.10], placements=[AssetInstance() for _ in range(1)])
wall_shelf_B = Assets(description="A set of three wooden shelves.", size=[0.22, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
wall_art_panel = Assets(description="The plaque has a design in the middle of the board.", size=[0.02, 0.40, 0.50], placements=[AssetInstance() for _ in range(1)])

wall_shelf_A[0].instance_id = 'wall_shelf_A_0'
shared_wardrobe[0].instance_id = 'shared_wardrobe_0'
wall_shelf_B[0].instance_id = 'wall_shelf_B_0'
wall_art_panel[0].instance_id = 'wall_art_panel_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

wall_shelf_A[0].position = [0.5032399120499755, 1.3803087065239723, 0.4]
wall_shelf_A[0].rotation = [0, 0, 0]
shared_wardrobe[0].position = [1.9286398110539251, 0.004208229636350813, 1.05]
shared_wardrobe[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [1.4903657911657173, 1.8844623947825807, 0.4]
wall_shelf_B[0].rotation = [0, 0, 0]
wall_art_panel[0].position = [1.3345466210218495, 1.9824502561611634, 0.25]
wall_art_panel[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [0.5032399120499755, 1.3803087065239723, 0.4]
wall_shelf_A[0].rotation = [0, 0, 0]
shared_wardrobe[0].position = [1.9286398110539251, 0.004208229636350813, 1.05]
shared_wardrobe[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [1.4903657911657173, 1.8844623947825807, 0.4]
wall_shelf_B[0].rotation = [0, 0, 0]
wall_art_panel[0].position = [1.3345466210218495, 1.9824502561611634, 0.25]
wall_art_panel[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the actual boundary coordinates: the room occupies [0, 2] x [0, 2].
# Keep the west-wall doorway (y=0.89..1.91) and its approach unobstructed.
# The wardrobe faces west, with 1.4 m of open space in front of it.
shared_wardrobe[0].position = [1.70, 1.30, 1.05]
shared_wardrobe[0].rotation = [0, 0, radians(180)]

# Mount the shelves on the south wall, facing north. Their horizontal
# extents are x=0.10..0.70 and x=0.80..1.40, leaving a 0.10 m gap.
wall_shelf_A[0].position = [0.40, 0.11, 1.40]
wall_shelf_A[0].rotation = [0, 0, radians(90)]

wall_shelf_B[0].position = [1.10, 0.11, 1.40]
wall_shelf_B[0].rotation = [0, 0, radians(90)]

# Mount the plaque on the north wall, facing south, outside the wardrobe.
wall_art_panel[0].position = [0.65, 1.99, 1.50]
wall_art_panel[0].rotation = [0, 0, radians(270)]

# Fixed reference poses preserve wall positions and mounting heights.
# These are constraint references, not additional scene objects.
wardrobe_reference = AssetInstance(
    position=[1.70, 1.30, 1.05], rotation=[0, 0, radians(180)]
)
shelf_A_reference = AssetInstance(
    position=[0.40, 0.11, 1.40], rotation=[0, 0, radians(90)]
)
shelf_B_reference = AssetInstance(
    position=[1.10, 0.11, 1.40], rotation=[0, 0, radians(90)]
)
panel_reference = AssetInstance(
    position=[0.65, 1.99, 1.50], rotation=[0, 0, radians(270)]
)

# Prioritize exact, non-overlapping poses and the clear doorway approach.
solver.distance_constraint(
    shared_wardrobe[0], wardrobe_reference, 0, 0, weight=10
)
solver.against_wall(shared_wardrobe[0], walls[1])
solver.align_with(shared_wardrobe[0], wardrobe_reference)

# The shelves and plaque are wall-mounted fixtures, not loose tabletop
# objects; wall attachment and fixed center heights replace on_top_of.
solver.distance_constraint(
    wall_shelf_A[0], shelf_A_reference, 0, 0, weight=10
)
solver.against_wall(wall_shelf_A[0], walls[0])
solver.align_with(wall_shelf_A[0], shelf_A_reference)

solver.distance_constraint(
    wall_shelf_B[0], shelf_B_reference, 0, 0, weight=10
)
solver.against_wall(wall_shelf_B[0], walls[0])
solver.align_with(wall_shelf_B[0], shelf_B_reference)

solver.distance_constraint(
    wall_art_panel[0], panel_reference, 0, 0, weight=10
)
solver.against_wall(wall_art_panel[0], walls[2])
solver.align_with(wall_art_panel[0], panel_reference)

solver.constraints = []
shared_wardrobe[0].position = [1.7000000476837158, 1.2999999523162842, 1.0499999523162842]
shared_wardrobe[0].rotation = [0, 0, -3.141592629669634]
shared_wardrobe[0].optimize = 2
wall_shelf_A[0].position = [0.4000000059604645, 0.10999999940395355, 0.4000000059604645]
wall_shelf_A[0].rotation = [0, 0, 1.5707963624831933]
wall_shelf_A[0].optimize = 2
wall_shelf_B[0].position = [1.100000023841858, 0.10999999940395355, 0.4000000059604645]
wall_shelf_B[0].rotation = [0, 0, 1.5707963624831933]
wall_shelf_B[0].optimize = 2
wall_art_panel[0].position = [0.6499999761581421, 1.9899998903274536, 0.25]
wall_art_panel[0].rotation = [0, 0, -1.5707962799533677]
wall_art_panel[0].optimize = 2

