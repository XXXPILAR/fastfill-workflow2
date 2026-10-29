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
    Wall(corner1=[3.16, 3.81, 0.00], corner2=[0.00, 3.81, 0.00]),
    Wall(corner1=[0.00, 3.81, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.16, 0.00, 0.00]),
    Wall(corner1=[3.16, 0.00, 0.00], corner2=[3.16, 3.81, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
carpet = Assets(description="carpet", size=[2.80, 2.30, 0.01], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.60, 1.60, 2.20], placements=[AssetInstance() for _ in range(1)])
nightstand_A = Assets(description="nightstand", size=[0.40, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.10, 1.60, 1.05], placements=[AssetInstance() for _ in range(1)])
nightstand_B = Assets(description="nightstand", size=[0.40, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])

carpet[0].instance_id = 'carpet_0'
wardrobe[0].instance_id = 'wardrobe_0'
nightstand_A[0].instance_id = 'nightstand_A_0'
bed[0].instance_id = 'bed_0'
nightstand_B[0].instance_id = 'nightstand_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

carpet[0].position = [1.2129835967497324, 0.5106248875365457, 0.0075]
carpet[0].rotation = [0, 0, 0]
wardrobe[0].position = [1.0547732733365789, 2.1869509100208626, 1.1]
wardrobe[0].rotation = [0, 0, 0]
nightstand_A[0].position = [0.06354744834020809, 1.7075263158600595, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
bed[0].position = [2.975181501742402, 3.7527123114871546, 0.525]
bed[0].rotation = [0, 0, 0]
nightstand_B[0].position = [1.1042016273988267, 2.387042551296296, 0.275]
nightstand_B[0].rotation = [0, 0, 0]
carpet[0].position = [1.2129835967497324, 0.5106248875365457, 0.0075]
carpet[0].rotation = [0, 0, 0]
wardrobe[0].position = [1.0547732733365789, 2.1869509100208626, 1.1]
wardrobe[0].rotation = [0, 0, 0]
nightstand_A[0].position = [0.06354744834020809, 1.7075263158600595, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
bed[0].position = [2.975181501742402, 3.7527123114871546, 0.525]
bed[0].rotation = [0, 0, 0]
nightstand_B[0].position = [1.1042016273988267, 2.387042551296296, 0.275]
nightstand_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the supplied wall coordinates (the room spans x=0..3.16, y=0..3.81).
# The bed faces south, with its head at the north wall and a nightstand
# on either side. The low furniture leaves the north window unobstructed.
bed[0].position = [1.58, 2.76, 0.535]
bed[0].rotation = [0, 0, radians(270)]

nightstand_A[0].position = [0.505, 3.61, 0.275]
nightstand_A[0].rotation = [0, 0, radians(270)]

nightstand_B[0].position = [2.655, 3.61, 0.275]
nightstand_B[0].rotation = [0, 0, radians(270)]

# Put the wardrobe against the south wall, facing north.
# Its footprint is x=1.36..2.96, y=0..0.60, clear of the door
# opening at x=0.13..1.01 and its approach on the southwest side.
wardrobe[0].position = [2.16, 0.30, 1.10]
wardrobe[0].rotation = [0, 0, radians(90)]

# The carpet is a floor covering, intentionally extending under the bed.
# Its footprint is x=0.18..2.98, y=0.90..3.20, away from the door.
# The bed's bounding-box bottom is at the carpet's top (z=0.01),
# so their bounding-box volumes do not intersect.
carpet[0].position = [1.58, 2.05, 0.005]
carpet[0].rotation = [0, 0, 0]

# Prioritize the collision-free positions and their orientations.
# Fixed references are not additional scene furniture.
for layout_instance in (
    bed[0], nightstand_A[0], nightstand_B[0], wardrobe[0], carpet[0]
):
    layout_reference = AssetInstance(
        position=list(layout_instance.position),
        rotation=list(layout_instance.rotation),
    )
    solver.distance_constraint(
        layout_instance, layout_reference, 0.0, 0.0, weight=10
    )
    solver.align_with(layout_instance, layout_reference)

# Reinforce the wall relationships. With these rotations, each piece's
# back touches the relevant wall; neither nightstand overlaps the bed.
solver.against_wall(nightstand_A[0], walls[0])
solver.against_wall(nightstand_B[0], walls[0])
solver.against_wall(bed[0], walls[0])
solver.against_wall(wardrobe[0], walls[2])

solver.align_with(nightstand_A[0], bed[0])
solver.align_with(nightstand_B[0], bed[0])
solver.align_with(wardrobe[0], bed[0], angle=180)

# Preserve the bedside grouping using full 3D bounding-box-center distances.
# Each nightstand has a 0.05 m horizontal gap from its side of the bed.
bedside_center_distance = (
    1.075 ** 2 + 0.85 ** 2 + 0.260 ** 2
) ** 0.5

solver.distance_constraint(
    nightstand_A[0], bed[0],
    bedside_center_distance, bedside_center_distance, weight=10
)
solver.distance_constraint(
    nightstand_B[0], bed[0],
    bedside_center_distance, bedside_center_distance, weight=10
)
solver.distance_constraint(
    nightstand_A[0], nightstand_B[0], 2.15, 2.15, weight=10
)

# Keep the rug aligned with the room and beneath the bed rather than
# treating it as a small object needing a furniture support surface.
solver.align_with(carpet[0], bed[0], angle=90)
solver.distance_constraint(
    carpet[0], bed[0],
    (0.71 ** 2 + 0.53 ** 2) ** 0.5,
    (0.71 ** 2 + 0.53 ** 2) ** 0.5,
    weight=10,
)

solver.constraints = []
carpet[0].position = [1.5800000429153442, 2.049999952316284, 0.004999999888241291]
carpet[0].rotation = [0, 0, 0.02596296874331517]
carpet[0].optimize = 2
wardrobe[0].position = [2.1600000858306885, 0.3025290369987488, 1.100000023841858]
wardrobe[0].rotation = [0, 0, 1.5764478356648661]
wardrobe[0].optimize = 2
nightstand_B[0].position = [2.6649999618530273, 3.6073427200317383, 0.2750000059604645]
nightstand_B[0].rotation = [0, 0, -1.5589233046339883]
nightstand_B[0].optimize = 2
bed[0].position = [1.5800000429153442, 2.7429864406585693, 0.5249999761581421]
bed[0].rotation = [0, 0, -1.5464791397058195]
bed[0].optimize = 2
nightstand_A[0].position = [0.4950000047683716, 3.6073427200317383, 0.2750000059604645]
nightstand_A[0].rotation = [0, 0, -1.5589233046339883]
nightstand_A[0].optimize = 2

