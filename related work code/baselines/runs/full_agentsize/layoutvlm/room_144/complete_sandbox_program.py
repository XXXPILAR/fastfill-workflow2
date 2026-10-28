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
    Wall(corner1=[2.00, 0.00, 0.00], corner2=[2.00, 3.00, 0.00]),
    Wall(corner1=[2.00, 3.00, 0.00], corner2=[0.00, 3.00, 0.00]),
    Wall(corner1=[0.00, 3.00, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
small_stool = Assets(description="simple wooden small bathroom stool", size=[0.30, 0.40, 0.45], placements=[AssetInstance() for _ in range(1)])
bathroom_storage_cabinet = Assets(description="tall contemporary slim storage cabinet with glass doors", size=[0.35, 0.40, 1.80], placements=[AssetInstance() for _ in range(1)])
vanity_cabinet = Assets(description="large modern vanity cabinet with integrated double sink and wide countertop", size=[0.55, 1.40, 0.85], placements=[AssetInstance() for _ in range(1)])

small_stool[0].instance_id = 'small_stool_0'
bathroom_storage_cabinet[0].instance_id = 'bathroom_storage_cabinet_0'
vanity_cabinet[0].instance_id = 'vanity_cabinet_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

small_stool[0].position = [1.286804899642574, 2.2981486318234694, 0.225]
small_stool[0].rotation = [0, 0, 0]
bathroom_storage_cabinet[0].position = [0.19624338592677093, 0.8782184229355603, 0.9]
bathroom_storage_cabinet[0].rotation = [0, 0, 0]
vanity_cabinet[0].position = [0.4673861051310859, 0.3842722392931067, 0.425]
vanity_cabinet[0].rotation = [0, 0, 0]
small_stool[0].position = [1.286804899642574, 2.2981486318234694, 0.225]
small_stool[0].rotation = [0, 0, 0]
bathroom_storage_cabinet[0].position = [0.19624338592677093, 0.8782184229355603, 0.9]
bathroom_storage_cabinet[0].rotation = [0, 0, 0]
vanity_cabinet[0].position = [0.4673861051310859, 0.3842722392931067, 0.425]
vanity_cabinet[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the stool and storage cabinet along the left wall. Their centers are
# less than 0.50 m apart, while their footprints remain separated along y.
small_stool[0].position = [0.15, 0.40, 0.225]
small_stool[0].rotation = [0, 0, radians(0)]

bathroom_storage_cabinet[0].position = [0.175, 0.89, 0.90]
bathroom_storage_cabinet[0].rotation = [0, 0, radians(0)]

# Place the wide vanity against the opposite wall, leaving the middle of the
# room open for circulation and keeping it clear of the stool/storage group.
vanity_cabinet[0].position = [1.725, 1.60, 0.425]
vanity_cabinet[0].rotation = [0, 0, radians(180)]

# Fixed reference points preserve the intended positions along each wall.
stool_anchor = AssetInstance(position=[0.15, 0.40, 0.225])
storage_anchor = AssetInstance(position=[0.175, 0.89, 0.90])
vanity_anchor = AssetInstance(position=[1.725, 1.60, 0.425])

# Interior-facing reference points preserve functional front orientations.
stool_facing_point = AssetInstance(position=[1.00, 0.40, 0.225])
storage_facing_point = AssetInstance(position=[1.00, 0.89, 0.90])
vanity_facing_point = AssetInstance(position=[1.00, 1.60, 0.425])

# The stool must remain against the left wall and face into the room.
solver.against_wall(small_stool[0], walls[2])
solver.distance_constraint(
    small_stool[0], stool_anchor, 0.0, 0.0, weight=10
)
solver.point_towards(small_stool[0], stool_facing_point)

# Keep the storage cabinet within 0.50 m of the stool as required. At the
# proposed 0.491 m center distance, the two footprints have a small gap.
solver.distance_constraint(
    bathroom_storage_cabinet[0], small_stool[0],
    min_distance=0.45, max_distance=0.50, weight=10
)
solver.against_wall(bathroom_storage_cabinet[0], walls[2])
solver.distance_constraint(
    bathroom_storage_cabinet[0], storage_anchor, 0.0, 0.0, weight=10
)
solver.point_towards(
    bathroom_storage_cabinet[0], storage_facing_point
)

# Keep the vanity against the right wall, facing inward and well separated
# from both objects on the left side of the room.
solver.against_wall(vanity_cabinet[0], walls[0])
solver.distance_constraint(
    vanity_cabinet[0], vanity_anchor, 0.0, 0.0, weight=10
)
solver.point_towards(vanity_cabinet[0], vanity_facing_point)
solver.distance_constraint(
    vanity_cabinet[0], small_stool[0],
    min_distance=1.20, max_distance=None
)
solver.distance_constraint(
    vanity_cabinet[0], bathroom_storage_cabinet[0],
    min_distance=1.10, max_distance=None
)

solver.constraints = []
vanity_cabinet[0].position = [1.725000023841858, 1.600000023841858, 0.42500001192092896]
vanity_cabinet[0].rotation = [0, 0, -3.1415926098732037]
vanity_cabinet[0].optimize = 2
small_stool[0].position = [0.14999999105930328, 0.4000000059604645, 0.22499999403953552]
small_stool[0].rotation = [0, 0, 4.2463930187983815e-08]
small_stool[0].optimize = 2
bathroom_storage_cabinet[0].position = [0.17500001192092896, 0.8899999856948853, 0.8999999761581421]
bathroom_storage_cabinet[0].rotation = [0, 0, 4.246396689943707e-08]
bathroom_storage_cabinet[0].optimize = 2

