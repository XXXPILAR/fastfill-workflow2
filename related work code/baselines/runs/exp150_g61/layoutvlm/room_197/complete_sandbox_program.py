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
    Wall(corner1=[1.11, 4.02, 0.00], corner2=[1.11, 5.78, 0.00]),
    Wall(corner1=[1.11, 5.78, 0.00], corner2=[0.00, 5.78, 0.00]),
    Wall(corner1=[0.00, 5.78, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.13, 0.00, 0.00]),
    Wall(corner1=[3.13, 0.00, 0.00], corner2=[3.13, 4.02, 0.00]),
    Wall(corner1=[3.13, 4.02, 0.00], corner2=[1.11, 4.02, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
nightstand = Assets(description="nightstand", size=[0.40, 0.45, 0.50], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.00, 1.60, 0.55], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.60, 1.80, 2.20], placements=[AssetInstance() for _ in range(1)])

nightstand[0].instance_id = 'nightstand_0'
bed[0].instance_id = 'bed_0'
wardrobe[0].instance_id = 'wardrobe_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

nightstand[0].position = [1.5742750620614405, 2.821073721904329, 0.25]
nightstand[0].rotation = [0, 0, 0]
bed[0].position = [2.7630032110791882, 1.6695742333701495, 0.275]
bed[0].rotation = [0, 0, 0]
wardrobe[0].position = [2.1038065201838196, 3.197277090800297, 1.1]
wardrobe[0].rotation = [0, 0, 0]
nightstand[0].position = [1.5742750620614405, 2.821073721904329, 0.25]
nightstand[0].rotation = [0, 0, 0]
bed[0].position = [2.7630032110791882, 1.6695742333701495, 0.275]
bed[0].rotation = [0, 0, 0]
wardrobe[0].position = [2.1038065201838196, 3.197277090800297, 1.1]
wardrobe[0].rotation = [0, 0, 0]

solver.constraints = []

# Keep all furniture in the main rectangular room, leaving the entire
# northern entrance passage (y >= 4.02) and both door approaches clear.
#
# Bed footprint:       x=[0.90, 2.50], y=[0.00, 2.00]
# Nightstand footprint:x=[0.40, 0.85], y=[0.00, 0.40]
# Wardrobe footprint:  x=[2.53, 3.13], y=[2.15, 3.95]
# The nightstand is beside the bed's head, with a 0.05 m edge-to-edge gap.
# A 0.90 m aisle remains along the bed's left side, and the wardrobe
# opens toward the unobstructed area north of the bed.

bed[0].position = [1.70, 1.00, bed.size[2] / 2]
bed[0].rotation = [0, 0, radians(90)]

nightstand[0].position = [0.625, 0.20, nightstand.size[2] / 2]
nightstand[0].rotation = [0, 0, radians(90)]

wardrobe[0].position = [2.83, 3.05, wardrobe.size[2] / 2]
wardrobe[0].rotation = [0, 0, radians(180)]

# Fixed reference poses preserve the chosen clearances and door access.
bed_reference = AssetInstance(
    position=[1.70, 1.00, 0.275],
    rotation=[0, 0, radians(90)]
)
nightstand_reference = AssetInstance(
    position=[0.625, 0.20, 0.25],
    rotation=[0, 0, radians(90)]
)
wardrobe_reference = AssetInstance(
    position=[2.83, 3.05, 1.10],
    rotation=[0, 0, radians(180)]
)

# Prioritize the required wall contacts.
solver.against_wall(nightstand[0], walls[3])
solver.against_wall(wardrobe[0], walls[4])
solver.against_wall(bed[0], walls[3])

# Explicit positional constraints prevent sliding toward doors or
# into neighboring furniture.
solver.distance_constraint(bed[0], bed_reference, 0, 0, weight=10)
solver.distance_constraint(
    nightstand[0], nightstand_reference, 0, 0, weight=10
)
solver.distance_constraint(
    wardrobe[0], wardrobe_reference, 0, 0, weight=10
)

# Orient the bed and nightstand away from the south wall;
# the wardrobe faces west, into its clear operating area.
solver.align_with(bed[0], bed_reference)
solver.align_with(nightstand[0], nightstand_reference)
solver.align_with(wardrobe[0], wardrobe_reference)

# Distances are measured between 3D bounding-box centers, not edges.
# This separation corresponds to the intended 0.05 m bedside gap.
bedside_center_distance = (
    (1.70 - 0.625) ** 2
    + (1.00 - 0.20) ** 2
    + (0.275 - 0.25) ** 2
) ** 0.5
solver.distance_constraint(
    bed[0],
    nightstand[0],
    bedside_center_distance,
    bedside_center_distance,
    weight=10
)

solver.constraints = []
wardrobe[0].position = [2.8326337337493896, 3.049999952316284, 1.100000023841858]
wardrobe[0].rotation = [0, 0, 3.141530877403781]
wardrobe[0].optimize = 2
nightstand[0].position = [0.625, 0.2001301348209381, 0.25]
nightstand[0].rotation = [0, 0, 1.5709785319414318]
nightstand[0].optimize = 2
bed[0].position = [1.7000000476837158, 1.0262398719787598, 0.2750000059604645]
bed[0].rotation = [0, 0, 2.8867703856168934]
bed[0].optimize = 2

