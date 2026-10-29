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
    Wall(corner1=[3.40, 2.75, 0.00], corner2=[0.00, 2.75, 0.00]),
    Wall(corner1=[0.00, 2.75, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.40, 0.00, 0.00]),
    Wall(corner1=[3.40, 0.00, 0.00], corner2=[3.40, 2.75, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bed = Assets(description="bed", size=[2.05, 1.60, 1.10], placements=[AssetInstance() for _ in range(1)])
nightstand_A = Assets(description="nightstand", size=[0.40, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
nightstand_B = Assets(description="nightstand", size=[0.40, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.60, 1.50, 2.30], placements=[AssetInstance() for _ in range(1)])

bed[0].instance_id = 'bed_0'
nightstand_A[0].instance_id = 'nightstand_A_0'
nightstand_B[0].instance_id = 'nightstand_B_0'
wardrobe[0].instance_id = 'wardrobe_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

bed[0].position = [1.0146640064873595, 1.366519990176767, 0.55]
bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [0.9426164099446949, 1.3876120270768124, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
nightstand_B[0].position = [3.237125718245047, 0.8779090052510742, 0.275]
nightstand_B[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.5952411028483577, 2.005821712489834, 1.15]
wardrobe[0].rotation = [0, 0, 0]
bed[0].position = [1.0146640064873595, 1.366519990176767, 0.55]
bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [0.9426164099446949, 1.3876120270768124, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
nightstand_B[0].position = [3.237125718245047, 0.8779090052510742, 0.275]
nightstand_B[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.5952411028483577, 2.005821712489834, 1.15]
wardrobe[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the supplied wall coordinates: the room occupies [0, 3.40] x [0, 2.75].
# Put the head of the bed against the bottom wall, facing +y.
# Its footprint is x=[1.00, 2.60], y=[0.00, 2.05].
bed[0].position = [1.80, 1.025, 0.55]
bed[0].rotation = [0, 0, radians(90)]

# Flank the headboard with floor-standing nightstands.
# After rotation, each footprint is 0.45 m wide and 0.40 m deep.
# Both nightstands have a 0.05 m horizontal gap from the bed.
nightstand_A[0].position = [0.725, 0.20, 0.275]
nightstand_A[0].rotation = [0, 0, radians(90)]

nightstand_B[0].position = [2.875, 0.20, 0.275]
nightstand_B[0].rotation = [0, 0, radians(90)]

# Place the wardrobe against the top wall, facing into the room.
# Footprint: x=[0.00, 1.50], y=[2.15, 2.75].
# This stays above the left doorway, whose opening ends at y=2.125.
# The right-hand passage beside the bed remains 0.80 m wide.
wardrobe[0].position = [0.75, 2.45, 1.15]
wardrobe[0].rotation = [0, 0, radians(270)]

# Fixed references preserve the chosen footprints and doorway clearances.
# These references are constraint targets, not additional scene furniture.
bed_reference = AssetInstance(
    position=[1.80, 1.025, 0.55],
    rotation=[0, 0, radians(90)]
)
nightstand_A_reference = AssetInstance(
    position=[0.725, 0.20, 0.275],
    rotation=[0, 0, radians(90)]
)
nightstand_B_reference = AssetInstance(
    position=[2.875, 0.20, 0.275],
    rotation=[0, 0, radians(90)]
)
wardrobe_reference = AssetInstance(
    position=[0.75, 2.45, 1.15],
    rotation=[0, 0, radians(270)]
)

# Apply the most important positioning and orientation constraints first.
solver.distance_constraint(bed[0], bed_reference, 0, 0, weight=10)
solver.align_with(bed[0], bed_reference)

solver.distance_constraint(
    nightstand_A[0], nightstand_A_reference, 0, 0, weight=10
)
solver.align_with(nightstand_A[0], nightstand_A_reference)

solver.distance_constraint(
    nightstand_B[0], nightstand_B_reference, 0, 0, weight=10
)
solver.align_with(nightstand_B[0], nightstand_B_reference)

solver.distance_constraint(wardrobe[0], wardrobe_reference, 0, 0, weight=10)
solver.align_with(wardrobe[0], wardrobe_reference)

# Explicit wall relationships: the bed and both nightstands share the
# bottom wall, while the wardrobe backs onto the top wall.
solver.against_wall(bed[0], walls[2])
solver.against_wall(nightstand_A[0], walls[2])
solver.against_wall(nightstand_B[0], walls[2])
solver.against_wall(wardrobe[0], walls[0])

# Preserve matching nightstand orientations and the opposing wardrobe front.
solver.align_with(nightstand_A[0], bed[0])
solver.align_with(nightstand_B[0], bed[0])
solver.align_with(wardrobe[0], bed[0], angle=180)

# The solver measures 3D center distances, not edge gaps.
# These distances encode the selected 0.05 m bed-to-nightstand gaps,
# including the different center heights and headboard-side offsets.
bedside_center_distance = (
    1.075**2 + 0.825**2 + 0.275**2
) ** 0.5

solver.distance_constraint(
    nightstand_A[0], bed[0],
    bedside_center_distance, bedside_center_distance,
    weight=10
)
solver.distance_constraint(
    nightstand_B[0], bed[0],
    bedside_center_distance, bedside_center_distance,
    weight=10
)
solver.distance_constraint(
    nightstand_A[0], nightstand_B[0], 2.15, 2.15
)

# All four assets are floor-standing; no on_top_of constraints are needed.

solver.constraints = []
wardrobe[0].position = [0.8071110248565674, 2.450355052947998, 1.149999976158142]
wardrobe[0].rotation = [0, 0, -1.5696176652179472]
wardrobe[0].optimize = 2
bed[0].position = [1.8215575218200684, 1.0238286256790161, 0.550000011920929]
bed[0].rotation = [0, 0, 1.5723433005817453]
bed[0].optimize = 2
nightstand_A[0].position = [0.7966287732124329, 0.20051755011081696, 0.2750000059604645]
nightstand_A[0].rotation = [0, 0, 1.569162212765862]
nightstand_A[0].optimize = 2
nightstand_B[0].position = [2.9832277297973633, 0.20083829760551453, 0.2750000059604645]
nightstand_B[0].rotation = [0, 0, 1.5691654808517215]
nightstand_B[0].optimize = 2

