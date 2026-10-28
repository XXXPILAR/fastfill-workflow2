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
balcony_floor_lantern_A = Assets(description="A brown wooden lantern with paper panels.", size=[0.25, 0.25, 0.55], placements=[AssetInstance() for _ in range(1)])
balcony_wall_shelf = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.20, 0.80, 0.25], placements=[AssetInstance() for _ in range(1)])
balcony_storage_bench = Assets(description="Blue toy chest with wood top and carved letters on side.", size=[0.45, 1.10, 0.55], placements=[AssetInstance() for _ in range(1)])
throw_pillow = Assets(description="A large white pillow with golden edges.", size=[0.18, 0.50, 0.50], placements=[AssetInstance() for _ in range(1)])
balcony_floor_lantern_B = Assets(description="A brown wooden lantern with paper panels.", size=[0.25, 0.25, 0.55], placements=[AssetInstance() for _ in range(1)])

balcony_floor_lantern_A[0].instance_id = 'balcony_floor_lantern_A_0'
balcony_wall_shelf[0].instance_id = 'balcony_wall_shelf_0'
balcony_storage_bench[0].instance_id = 'balcony_storage_bench_0'
throw_pillow[0].instance_id = 'throw_pillow_0'
balcony_floor_lantern_B[0].instance_id = 'balcony_floor_lantern_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

balcony_floor_lantern_A[0].position = [1.1423737941958185, 0.17778402116986847, 0.275]
balcony_floor_lantern_A[0].rotation = [0, 0, 0]
balcony_wall_shelf[0].position = [0.5335212482518537, 1.5529363917272316, 0.125]
balcony_wall_shelf[0].rotation = [0, 0, 0]
balcony_storage_bench[0].position = [0.2555003020953668, 1.5649936111721006, 0.275]
balcony_storage_bench[0].rotation = [0, 0, 0]
throw_pillow[0].position = [1.0797910347490804, 1.691795680336467, 0.25]
throw_pillow[0].rotation = [0, 0, 0]
balcony_floor_lantern_B[0].position = [0.04208493052264717, 0.36437414759229214, 0.275]
balcony_floor_lantern_B[0].rotation = [0, 0, 0]
balcony_floor_lantern_A[0].position = [1.1423737941958185, 0.17778402116986847, 0.275]
balcony_floor_lantern_A[0].rotation = [0, 0, 0]
balcony_wall_shelf[0].position = [0.5335212482518537, 1.5529363917272316, 0.125]
balcony_wall_shelf[0].rotation = [0, 0, 0]
balcony_storage_bench[0].position = [0.2555003020953668, 1.5649936111721006, 0.275]
balcony_storage_bench[0].rotation = [0, 0, 0]
throw_pillow[0].position = [1.0797910347490804, 1.691795680336467, 0.25]
throw_pillow[0].rotation = [0, 0, 0]
balcony_floor_lantern_B[0].position = [0.04208493052264717, 0.36437414759229214, 0.275]
balcony_floor_lantern_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed references preserve the intended clearances and keep all furniture on
# the left side of the balcony, away from the door on the right wall.
bench_anchor = AssetInstance(position=[0.225, 1.25, 0.275])
shelf_anchor = AssetInstance(position=[0.10, 1.25, 1.35])
lantern_A_anchor = AssetInstance(position=[0.625, 1.58, 0.275])
lantern_B_anchor = AssetInstance(position=[0.625, 0.92, 0.275])
pillow_anchor = AssetInstance(position=[0.225, 1.25, 0.80])
left_wall_inward_orientation = AssetInstance(
    position=[1.00, 1.25, 0.00],
    rotation=[0, 0, radians(0)]
)

# The bench sits flush against the left wall and faces inward. Its footprint
# spans y=0.70..1.80, leaving the door approach on the right unobstructed.
balcony_storage_bench[0].position = [0.225, 1.25, 0.275]
balcony_storage_bench[0].rotation = [0, 0, radians(0)]
solver.against_wall(balcony_storage_bench[0], walls[3])
solver.distance_constraint(
    balcony_storage_bench[0], bench_anchor, 0.0, 0.0, weight=10
)
solver.align_with(
    balcony_storage_bench[0], left_wall_inward_orientation, angle=0
)

# Mount the shallow shelf above the bench. It remains clear of the top-wall
# window because its x extent ends before the window begins at x=0.26.
balcony_wall_shelf[0].position = [0.10, 1.25, 1.35]
balcony_wall_shelf[0].rotation = [0, 0, radians(0)]
solver.against_wall(balcony_wall_shelf[0], walls[3])
solver.distance_constraint(
    balcony_wall_shelf[0], shelf_anchor, 0.0, 0.0, weight=10
)
solver.align_with(
    balcony_wall_shelf[0], balcony_storage_bench[0], angle=0
)

# Center the pillow on the bench lid. The anchor supplies its required
# position-based constraint, while on_top_of maintains the vertical relation.
throw_pillow[0].position = [0.225, 1.25, 0.80]
throw_pillow[0].rotation = [0, 0, radians(0)]
solver.on_top_of(throw_pillow[0], balcony_storage_bench[0])
solver.distance_constraint(
    throw_pillow[0], pillow_anchor, 0.0, 0.0, weight=10
)
solver.align_with(throw_pillow[0], balcony_storage_bench[0], angle=0)

# Place both lanterns beside the bench on the room-facing side. Their 0.05 m
# edge clearance is within the requested 0.20 m. The center-distance range
# accounts for the bench and lantern half-widths as well as that edge gap.
balcony_floor_lantern_A[0].position = [0.625, 1.58, 0.275]
balcony_floor_lantern_A[0].rotation = [0, 0, radians(0)]
solver.distance_constraint(
    balcony_floor_lantern_A[0],
    balcony_storage_bench[0],
    0.35,
    0.55,
    weight=10,
)
solver.distance_constraint(
    balcony_floor_lantern_A[0], lantern_A_anchor, 0.0, 0.0, weight=10
)
solver.align_with(
    balcony_floor_lantern_A[0], balcony_storage_bench[0], angle=0
)

balcony_floor_lantern_B[0].position = [0.625, 0.92, 0.275]
balcony_floor_lantern_B[0].rotation = [0, 0, radians(0)]
solver.distance_constraint(
    balcony_floor_lantern_B[0],
    balcony_storage_bench[0],
    0.35,
    0.55,
    weight=10,
)
solver.distance_constraint(
    balcony_floor_lantern_B[0], lantern_B_anchor, 0.0, 0.0, weight=10
)
solver.align_with(
    balcony_floor_lantern_B[0], balcony_storage_bench[0], angle=0
)

# Preserve separation between the two lanterns.
solver.distance_constraint(
    balcony_floor_lantern_A[0],
    balcony_floor_lantern_B[0],
    0.50,
    None,
    weight=10,
)

solver.constraints = []
throw_pillow[0].position = [0.22499999403953552, 1.25, 0.800000011920929]
throw_pillow[0].rotation = [0, 0, 0.022790561024514572]
throw_pillow[0].optimize = 2
balcony_floor_lantern_A[0].position = [0.625, 1.5800000429153442, 0.2750000059604645]
balcony_floor_lantern_A[0].rotation = [0, 0, 0.02596296874331517]
balcony_floor_lantern_A[0].optimize = 2
balcony_floor_lantern_B[0].position = [0.625, 0.9200000166893005, 0.2750000059604645]
balcony_floor_lantern_B[0].rotation = [0, 0, 0.02596296874331517]
balcony_floor_lantern_B[0].optimize = 2
balcony_storage_bench[0].position = [0.23386864364147186, 1.25, 0.2750000059604645]
balcony_storage_bench[0].rotation = [0, 0, 0.024317193648187223]
balcony_storage_bench[0].optimize = 2
balcony_wall_shelf[0].position = [0.10101605206727982, 1.25, 0.125]
balcony_wall_shelf[0].rotation = [0, 0, 0.002540916928559797]
balcony_wall_shelf[0].optimize = 2

