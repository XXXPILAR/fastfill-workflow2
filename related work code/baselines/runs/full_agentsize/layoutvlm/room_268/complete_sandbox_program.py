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
    Wall(corner1=[3.42, 3.23, 0.00], corner2=[1.95, 3.23, 0.00]),
    Wall(corner1=[1.95, 3.23, 0.00], corner2=[1.95, 3.83, 0.00]),
    Wall(corner1=[1.95, 3.83, 0.00], corner2=[0.00, 3.83, 0.00]),
    Wall(corner1=[0.00, 3.83, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.42, 0.00, 0.00]),
    Wall(corner1=[3.42, 0.00, 0.00], corner2=[3.42, 3.23, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bed = Assets(description="bed", size=[2.00, 1.60, 0.60], placements=[AssetInstance() for _ in range(1)])
nightstand_A = Assets(description="nightstand", size=[0.40, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[3.00, 2.40, 0.01], placements=[AssetInstance() for _ in range(1)])
nightstand_B = Assets(description="nightstand", size=[0.40, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])

bed[0].instance_id = 'bed_0'
nightstand_A[0].instance_id = 'nightstand_A_0'
carpet[0].instance_id = 'carpet_0'
nightstand_B[0].instance_id = 'nightstand_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

bed[0].position = [2.297751130183861, 3.040429807368887, 0.3]
bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [1.436091574594508, 3.5371188029512752, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
carpet[0].position = [0.3640263264986054, 2.2813239376017505, 0.005]
carpet[0].rotation = [0, 0, 0]
nightstand_B[0].position = [0.8906958435119179, 3.0337731685906535, 0.275]
nightstand_B[0].rotation = [0, 0, 0]
bed[0].position = [2.297751130183861, 3.040429807368887, 0.3]
bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [1.436091574594508, 3.5371188029512752, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
carpet[0].position = [0.3640263264986054, 2.2813239376017505, 0.005]
carpet[0].rotation = [0, 0, 0]
nightstand_B[0].position = [0.8906958435119179, 3.0337731685906535, 0.275]
nightstand_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the bed along the solid left wall. This keeps both door approaches
# clear and provides enough space to flank the bed with the two nightstands.
bed[0].position = [1.00, 1.65, 0.31]
bed[0].rotation = [0, 0, radians(0)]

# o0001: placed beside the upper side of the bed and against the left wall.
nightstand_A[0].position = [0.20, 2.725, 0.285]
nightstand_A[0].rotation = [0, 0, radians(0)]

# The carpet lies beneath the furniture. Its edges remain inside the room,
# with clearance before both door thresholds.
carpet[0].position = [1.60, 1.60, 0.005]
carpet[0].rotation = [0, 0, radians(0)]

# o0003: placed on the opposite side so the bed is between the nightstands.
# Its x extent ends at 0.40 m, just outside the southern doorway opening.
nightstand_B[0].position = [0.20, 0.575, 0.285]
nightstand_B[0].rotation = [0, 0, radians(0)]

left_wall = walls[3]
room_interior_point = AssetInstance(position=[2.50, 1.65, 0.31])
carpet_anchor = AssetInstance(position=[1.60, 1.60, 0.005])

# Preserve the required bed-to-o0001 relationship first. At these placements,
# the boxes have a 0.05 m edge gap. The center-distance bounds account for the
# bed and nightstand dimensions and permit no more than a 0.10 m edge gap.
solver.distance_constraint(
    bed[0], nightstand_A[0],
    min_distance=1.30, max_distance=1.38, weight=10
)

# Keep the bed between the two nightstands by maintaining the corresponding
# close relationship on its opposite side.
solver.distance_constraint(
    bed[0], nightstand_B[0],
    min_distance=1.30, max_distance=1.38, weight=10
)

# Position the bed and both nightstands along the uninterrupted left wall.
solver.against_wall(bed[0], left_wall)
solver.against_wall(nightstand_A[0], left_wall)
solver.against_wall(nightstand_B[0], left_wall)

# The bed faces into the room, and both nightstands share its orientation.
solver.point_towards(bed[0], room_interior_point)
solver.align_with(nightstand_A[0], bed[0])
solver.align_with(nightstand_B[0], bed[0])

# Anchor the carpet centrally beneath the furniture and orient it parallel
# to the bed. This is the carpet's required position-based constraint.
solver.distance_constraint(
    carpet[0], carpet_anchor,
    min_distance=0.0, max_distance=0.0, weight=10
)
solver.align_with(carpet[0], bed[0])

# Account for the carpet's 0.01 m thickness so the furniture rests on its
# surface rather than intersecting it.
solver.on_top_of(bed[0], carpet[0])
solver.on_top_of(nightstand_A[0], carpet[0])
solver.on_top_of(nightstand_B[0], carpet[0])

solver.constraints = []
nightstand_B[0].position = [0.4567064344882965, 0.8330605626106262, 0.2849999964237213]
nightstand_B[0].rotation = [0, 0, 3.9431611170523977e-07]
nightstand_B[0].optimize = 2
carpet[0].position = [1.778252124786377, 1.6545981168746948, 0.004999999888241291]
carpet[0].rotation = [0, 0, -2.854710361127526]
carpet[0].optimize = 2
bed[0].position = [1.189853310585022, 1.8676412105560303, 0.3100000023841858]
bed[0].rotation = [0, 0, -2.8489911546431412]
bed[0].optimize = 2
nightstand_A[0].position = [0.27731752395629883, 2.4629244804382324, 0.2849999964237213]
nightstand_A[0].rotation = [0, 0, 3.753637452874787e-07]
nightstand_A[0].optimize = 2

