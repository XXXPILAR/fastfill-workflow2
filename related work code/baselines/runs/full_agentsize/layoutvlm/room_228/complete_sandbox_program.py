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
    Wall(corner1=[2.80, 4.26, 0.00], corner2=[0.00, 4.26, 0.00]),
    Wall(corner1=[0.00, 4.26, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.80, 0.00, 0.00]),
    Wall(corner1=[2.80, 0.00, 0.00], corner2=[2.80, 4.26, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
wardrobe = Assets(description="wardrobe", size=[0.60, 1.80, 2.20], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[2.30, 1.60, 0.01], placements=[AssetInstance() for _ in range(1)])

wardrobe[0].instance_id = 'wardrobe_0'
carpet[0].instance_id = 'carpet_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

wardrobe[0].position = [0.4829687549939094, 2.043439729255322, 1.1]
wardrobe[0].rotation = [0, 0, 0]
carpet[0].position = [0.7565435896441337, 1.5147135217618546, 0.005]
carpet[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.4829687549939094, 2.043439729255322, 1.1]
wardrobe[0].rotation = [0, 0, 0]
carpet[0].position = [0.7565435896441337, 1.5147135217618546, 0.005]
carpet[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the wardrobe along the right wall, away from the door and its approach.
# Its shallow 0.60 m dimension extends into the room, and it faces inward (-x).
wardrobe[0].position = [2.50, 3.20, 1.10]
wardrobe[0].rotation = [0, 0, radians(180)]

# Place the carpet in the open lower portion of the room. Its bounds are
# approximately x=[0.25, 2.55], y=[0.40, 2.00], leaving both the doorway
# approach and the wardrobe footprint clear.
carpet[0].position = [1.40, 1.20, 0.005]
carpet[0].rotation = [0, 0, radians(0)]

# Fixed references preserve the intended locations and room-axis alignment.
wardrobe_anchor = AssetInstance(position=[2.50, 3.20, 1.10])
wardrobe_interior_target = AssetInstance(position=[1.40, 3.20, 1.10])
carpet_anchor = AssetInstance(position=[1.40, 1.20, 0.005])
room_axis_reference = AssetInstance(
    position=[1.40, 1.20, 0.005],
    rotation=[0, 0, radians(0)]
)

# The wardrobe must remain against the right wall and near the selected section
# of that wall. Pointing toward the interior makes its front face into the room.
solver.against_wall(wardrobe[0], walls[3])
solver.distance_constraint(
    wardrobe[0], wardrobe_anchor,
    min_distance=0.0, max_distance=0.0, weight=10
)
solver.point_towards(wardrobe[0], wardrobe_interior_target)

# Keep the carpet centered in the unobstructed floor area and aligned with the
# room walls. It remains on the floor, so no on_top_of constraint is needed.
solver.distance_constraint(
    carpet[0], carpet_anchor,
    min_distance=0.0, max_distance=0.0, weight=10
)
solver.align_with(carpet[0], room_axis_reference)

solver.constraints = []
carpet[0].position = [1.399999976158142, 1.2000000476837158, 0.004999999888241291]
carpet[0].rotation = [0, 0, 0.00942477746072377]
carpet[0].optimize = 2
wardrobe[0].position = [2.5, 3.200000047683716, 1.100000023841858]
wardrobe[0].rotation = [0, 0, -3.141592645805161]
wardrobe[0].optimize = 2

