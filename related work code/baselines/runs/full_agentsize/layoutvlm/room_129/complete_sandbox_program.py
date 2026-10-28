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
wall_shelf_A = Assets(description="A set of three wooden shelves.", size=[0.20, 0.75, 0.75], placements=[AssetInstance() for _ in range(1)])
shared_wardrobe = Assets(description="shared wardrobe", size=[0.55, 1.20, 2.00], placements=[AssetInstance() for _ in range(1)])
wall_shelf_B = Assets(description="A set of three wooden shelves.", size=[0.20, 0.75, 0.75], placements=[AssetInstance() for _ in range(1)])
wall_art_panel = Assets(description="The plaque has a design in the middle of the board.", size=[0.03, 0.60, 0.40], placements=[AssetInstance() for _ in range(1)])

wall_shelf_A[0].instance_id = 'wall_shelf_A_0'
shared_wardrobe[0].instance_id = 'shared_wardrobe_0'
wall_shelf_B[0].instance_id = 'wall_shelf_B_0'
wall_art_panel[0].instance_id = 'wall_art_panel_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

wall_shelf_A[0].position = [0.2888171751345452, 1.3846824549388799, 0.375]
wall_shelf_A[0].rotation = [0, 0, 0]
shared_wardrobe[0].position = [1.7442310306365476, 0.3490853027834795, 1.0]
shared_wardrobe[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [1.5631545783684224, 0.32531443749027367, 0.375]
wall_shelf_B[0].rotation = [0, 0, 0]
wall_art_panel[0].position = [1.13954117791583, 0.5803499307371678, 0.2]
wall_art_panel[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [0.2888171751345452, 1.3846824549388799, 0.375]
wall_shelf_A[0].rotation = [0, 0, 0]
shared_wardrobe[0].position = [1.7442310306365476, 0.3490853027834795, 1.0]
shared_wardrobe[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [1.5631545783684224, 0.32531443749027367, 0.375]
wall_shelf_B[0].rotation = [0, 0, 0]
wall_art_panel[0].position = [1.13954117791583, 0.5803499307371678, 0.2]
wall_art_panel[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the wardrobe against the right wall, away from the doorway at
# (0.00, 1.40). Its front faces into the room toward the -x direction.
shared_wardrobe[0].position = [1.725, 1.25, 1.00]
shared_wardrobe[0].rotation = [0, 0, radians(180)]

# Mount both shelf sets on the bottom wall. Their separation prevents overlap,
# while their elevated z positions keep the floor area usable.
wall_shelf_A[0].position = [0.45, 0.10, 1.45]
wall_shelf_A[0].rotation = [0, 0, radians(90)]

wall_shelf_B[0].position = [1.35, 0.10, 1.45]
wall_shelf_B[0].rotation = [0, 0, radians(90)]

# Mount the decorative panel on the top wall, facing into the room.
wall_art_panel[0].position = [0.75, 1.985, 1.45]
wall_art_panel[0].rotation = [0, 0, radians(-90)]

# Fixed anchors preserve the selected positions along each wall when the
# solver adjusts the layout.
wardrobe_anchor = AssetInstance(position=[1.725, 1.25, 1.00])
shelf_A_anchor = AssetInstance(position=[0.45, 0.10, 1.45])
shelf_B_anchor = AssetInstance(position=[1.35, 0.10, 1.45])
art_anchor = AssetInstance(position=[0.75, 1.985, 1.45])

# Interior-facing targets provide explicit orientation semantics.
wardrobe_facing_target = AssetInstance(position=[0.75, 1.25, 1.00])
shelf_A_facing_target = AssetInstance(position=[0.45, 1.00, 1.45])
shelf_B_facing_target = AssetInstance(position=[1.35, 1.00, 1.45])
art_facing_target = AssetInstance(position=[0.75, 1.00, 1.45])

# Important wall-contact constraints are listed first.
solver.against_wall(shared_wardrobe[0], walls[1])
solver.against_wall(wall_shelf_A[0], walls[0])
solver.against_wall(wall_shelf_B[0], walls[0])
solver.against_wall(wall_art_panel[0], walls[2])

# Keep each object at its intended non-overlapping location on its wall.
solver.distance_constraint(
    shared_wardrobe[0], wardrobe_anchor, 0.0, 0.0, weight=10
)
solver.distance_constraint(
    wall_shelf_A[0], shelf_A_anchor, 0.0, 0.0, weight=10
)
solver.distance_constraint(
    wall_shelf_B[0], shelf_B_anchor, 0.0, 0.0, weight=10
)
solver.distance_constraint(
    wall_art_panel[0], art_anchor, 0.0, 0.0, weight=10
)

# Orient every wall-mounted asset toward the room interior.
solver.point_towards(shared_wardrobe[0], wardrobe_facing_target)
solver.point_towards(wall_shelf_A[0], shelf_A_facing_target)
solver.point_towards(wall_shelf_B[0], shelf_B_facing_target)
solver.point_towards(wall_art_panel[0], art_facing_target)

solver.constraints = []
wall_art_panel[0].position = [0.75, 1.984999656677246, 0.20000000298023224]
wall_art_panel[0].rotation = [0, 0, -1.5707962875764554]
wall_art_panel[0].optimize = 2
wall_shelf_B[0].position = [1.350000023841858, 0.10000000894069672, 0.375]
wall_shelf_B[0].rotation = [0, 0, 1.5707963675720344]
wall_shelf_B[0].optimize = 2
wall_shelf_A[0].position = [0.44999998807907104, 0.10000000894069672, 0.375]
wall_shelf_A[0].rotation = [0, 0, 1.5707963675720344]
wall_shelf_A[0].optimize = 2
shared_wardrobe[0].position = [1.725000023841858, 1.25, 1.0]
shared_wardrobe[0].rotation = [0, 0, -3.141592610816515]
shared_wardrobe[0].optimize = 2

