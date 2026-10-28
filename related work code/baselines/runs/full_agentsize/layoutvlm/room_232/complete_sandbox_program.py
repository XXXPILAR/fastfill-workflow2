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
bed = Assets(description="bed", size=[2.00, 1.60, 0.55], placements=[AssetInstance() for _ in range(1)])
nightstand_A = Assets(description="nightstand", size=[0.40, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
nightstand_B = Assets(description="nightstand", size=[0.40, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.60, 1.20, 2.20], placements=[AssetInstance() for _ in range(1)])

bed[0].instance_id = 'bed_0'
nightstand_A[0].instance_id = 'nightstand_A_0'
nightstand_B[0].instance_id = 'nightstand_B_0'
wardrobe[0].instance_id = 'wardrobe_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

bed[0].position = [3.2252720510615953, 2.1315966068361405, 0.275]
bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [2.645541720093126, 0.9394725961474811, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
nightstand_B[0].position = [2.860985071190953, 1.516741124594993, 0.275]
nightstand_B[0].rotation = [0, 0, 0]
wardrobe[0].position = [1.2860060956537587, 1.6043760463583747, 1.1]
wardrobe[0].rotation = [0, 0, 0]
bed[0].position = [3.2252720510615953, 2.1315966068361405, 0.275]
bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [2.645541720093126, 0.9394725961474811, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
nightstand_B[0].position = [2.860985071190953, 1.516741124594993, 0.275]
nightstand_B[0].rotation = [0, 0, 0]
wardrobe[0].position = [1.2860060956537587, 1.6043760463583747, 1.1]
wardrobe[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the bed with its head against the bottom wall. Rotating it 90 degrees
# makes its 2.00 m dimension run into the room while leaving space at both sides.
bed[0].position = [1.70, 1.00, 0.275]
bed[0].rotation = [0, 0, radians(90)]

# Place the nightstands symmetrically on either side of the bed's head.
# Their nearest edges are only 0.025 m from the bed, satisfying the requested
# proximity without creating an overlap.
nightstand_A[0].position = [0.65, 0.20, 0.275]
nightstand_A[0].rotation = [0, 0, radians(90)]

nightstand_B[0].position = [2.75, 0.20, 0.275]
nightstand_B[0].rotation = [0, 0, radians(90)]

# Put the wardrobe against the upper wall, outside the inward clearance zones
# of both doors. It faces into the room and has 0.15 m clearance from the bed.
wardrobe[0].position = [0.70, 2.45, 1.10]
wardrobe[0].rotation = [0, 0, radians(-90)]


# Fixed references preserve the intended locations and orientations if the
# solver adjusts the scene.
bed_anchor = AssetInstance(
    position=[1.70, 1.00, 0.275],
    rotation=[0, 0, radians(90)],
)
nightstand_A_anchor = AssetInstance(
    position=[0.65, 0.20, 0.275],
    rotation=[0, 0, radians(90)],
)
nightstand_B_anchor = AssetInstance(
    position=[2.75, 0.20, 0.275],
    rotation=[0, 0, radians(90)],
)
wardrobe_anchor = AssetInstance(
    position=[0.70, 2.45, 1.10],
    rotation=[0, 0, radians(-90)],
)

# Important wall and adjacency requirements come first.
solver.against_wall(bed[0], walls[2])
solver.against_wall(nightstand_A[0], walls[2])
solver.against_wall(nightstand_B[0], walls[2])
solver.against_wall(wardrobe[0], walls[0])

# The API measures center-to-center distance. With these object dimensions,
# approximately 1.32 m center separation corresponds to less than 0.10 m of
# edge clearance between the bed and each nightstand.
solver.distance_constraint(
    bed[0], nightstand_B[0],
    min_distance=1.28, max_distance=1.36, weight=10,
)
solver.distance_constraint(
    bed[0], nightstand_A[0],
    min_distance=1.28, max_distance=1.36, weight=10,
)

# High-weight anchors maintain the symmetric arrangement, keep the bed between
# the two nightstands, and preserve clear circulation in front of both doors.
solver.distance_constraint(
    bed[0], bed_anchor,
    min_distance=0, max_distance=0, weight=10,
)
solver.distance_constraint(
    nightstand_A[0], nightstand_A_anchor,
    min_distance=0, max_distance=0, weight=10,
)
solver.distance_constraint(
    nightstand_B[0], nightstand_B_anchor,
    min_distance=0, max_distance=0, weight=10,
)
solver.distance_constraint(
    wardrobe[0], wardrobe_anchor,
    min_distance=0, max_distance=0, weight=10,
)

# Orientation constraints are supplied for every new asset. The nightstands
# remain parallel to the bed, while the wardrobe faces away from the upper wall.
solver.align_with(bed[0], bed_anchor)
solver.align_with(nightstand_A[0], bed[0])
solver.align_with(nightstand_B[0], bed[0])
solver.align_with(wardrobe[0], wardrobe_anchor)

solver.constraints = []
nightstand_B[0].position = [2.7557153701782227, 0.20040516555309296, 0.2750000059604645]
nightstand_B[0].rotation = [0, 0, 1.5709433849481367]
nightstand_B[0].optimize = 2
wardrobe[0].position = [0.699999988079071, 2.4494998455047607, 1.100000023841858]
wardrobe[0].rotation = [0, 0, -1.570796283134356]
wardrobe[0].optimize = 2
bed[0].position = [1.7180323600769043, 1.000252604484558, 0.2750000059604645]
bed[0].rotation = [0, 0, 1.5709433710705738]
bed[0].optimize = 2
nightstand_A[0].position = [0.6573997139930725, 0.20009665191173553, 0.2750000059604645]
nightstand_A[0].rotation = [0, 0, 1.5709433849533165]
nightstand_A[0].optimize = 2

