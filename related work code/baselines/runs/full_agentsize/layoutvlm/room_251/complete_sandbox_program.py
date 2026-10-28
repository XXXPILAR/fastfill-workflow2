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
    Wall(corner1=[3.38, 0.00, 0.00], corner2=[3.38, 2.88, 0.00]),
    Wall(corner1=[3.38, 2.88, 0.00], corner2=[0.00, 2.88, 0.00]),
    Wall(corner1=[0.00, 2.88, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.38, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
floor_standing_lamp = Assets(description="floor standing lamp", size=[0.30, 0.30, 1.55], placements=[AssetInstance() for _ in range(1)])
chair = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.00, 1.40, 0.55], placements=[AssetInstance() for _ in range(1)])
desk = Assets(description="desk", size=[0.55, 1.10, 0.75], placements=[AssetInstance() for _ in range(1)])
wardrobe_A = Assets(description="wardrobe", size=[0.60, 0.90, 2.00], placements=[AssetInstance() for _ in range(1)])
wardrobe_B = Assets(description="wardrobe", size=[0.60, 0.90, 2.00], placements=[AssetInstance() for _ in range(1)])

floor_standing_lamp[0].instance_id = 'floor_standing_lamp_0'
chair[0].instance_id = 'chair_0'
bed[0].instance_id = 'bed_0'
desk[0].instance_id = 'desk_0'
wardrobe_A[0].instance_id = 'wardrobe_A_0'
wardrobe_B[0].instance_id = 'wardrobe_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

floor_standing_lamp[0].position = [1.5315293492051807, 1.1467599359807972, 0.775]
floor_standing_lamp[0].rotation = [0, 0, 0]
chair[0].position = [1.0033027609524154, 1.859645961622776, 0.425]
chair[0].rotation = [0, 0, 0]
bed[0].position = [2.7641982298430885, 0.5561952380807246, 0.275]
bed[0].rotation = [0, 0, 0]
desk[0].position = [1.185390757745861, 2.382723388106362, 0.375]
desk[0].rotation = [0, 0, 0]
wardrobe_A[0].position = [2.846226040523821, 2.8057229152388423, 1.0]
wardrobe_A[0].rotation = [0, 0, 0]
wardrobe_B[0].position = [2.5890042992876268, 2.0206109753178105, 1.0]
wardrobe_B[0].rotation = [0, 0, 0]
floor_standing_lamp[0].position = [1.5315293492051807, 1.1467599359807972, 0.775]
floor_standing_lamp[0].rotation = [0, 0, 0]
chair[0].position = [1.0033027609524154, 1.859645961622776, 0.425]
chair[0].rotation = [0, 0, 0]
bed[0].position = [2.7641982298430885, 0.5561952380807246, 0.275]
bed[0].rotation = [0, 0, 0]
desk[0].position = [1.185390757745861, 2.382723388106362, 0.375]
desk[0].rotation = [0, 0, 0]
wardrobe_A[0].position = [2.846226040523821, 2.8057229152388423, 1.0]
wardrobe_A[0].rotation = [0, 0, 0]
wardrobe_B[0].position = [2.5890042992876268, 2.0206109753178105, 1.0]
wardrobe_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the bed along the upper wall, leaving the doorway and the center-right
# work area unobstructed.
bed[0].position = [1.00, 2.18, 0.275]
bed[0].rotation = [0, 0, radians(0)]

# Center the desk beneath the window on the right wall. Its front faces -x,
# toward the chair.
desk[0].position = [3.105, 1.45, 0.375]
desk[0].rotation = [0, 0, radians(180)]

# Leave a usable gap between the chair and desk while keeping the chair clear
# of the bed.
chair[0].position = [2.42, 1.45, 0.425]
chair[0].rotation = [0, 0, radians(0)]

# Put both wardrobes along the lower wall, well to the right of the door and
# its approach path. Rotating them makes their 0.60 m depth face into the room.
wardrobe_A[0].position = [2.90, 0.30, 1.00]
wardrobe_A[0].rotation = [0, 0, radians(90)]

wardrobe_B[0].position = [1.90, 0.30, 1.00]
wardrobe_B[0].rotation = [0, 0, radians(90)]

# The lamp occupies the otherwise unused upper-right corner, clear of both
# the desk and the bed.
floor_standing_lamp[0].position = [3.20, 2.73, 0.775]
floor_standing_lamp[0].rotation = [0, 0, radians(0)]


# Fixed-point anchors preserve the selected positions if the solver adjusts
# the scene. Their z coordinates match the corresponding object centers.
bed_anchor = AssetInstance(position=[1.00, 2.18, 0.275])
desk_anchor = AssetInstance(position=[3.105, 1.45, 0.375])
chair_anchor = AssetInstance(position=[2.42, 1.45, 0.425])
wardrobe_A_anchor = AssetInstance(position=[2.90, 0.30, 1.00])
wardrobe_B_anchor = AssetInstance(position=[1.90, 0.30, 1.00])
lamp_anchor = AssetInstance(position=[3.20, 2.73, 0.775])

# Primary position constraints: retain the wall relationships and keep the
# freestanding chair in its selected working position.
solver.against_wall(bed[0], walls[1])
solver.distance_constraint(bed[0], bed_anchor, 0, 0, weight=10)

solver.against_wall(desk[0], walls[0])
solver.distance_constraint(desk[0], desk_anchor, 0, 0, weight=10)

solver.distance_constraint(chair[0], chair_anchor, 0, 0, weight=10)
solver.distance_constraint(chair[0], desk[0], 0.68, 0.75, weight=10)

solver.against_wall(wardrobe_A[0], walls[3])
solver.distance_constraint(
    wardrobe_A[0], wardrobe_A_anchor, 0, 0, weight=10
)

solver.against_wall(wardrobe_B[0], walls[3])
solver.distance_constraint(
    wardrobe_B[0], wardrobe_B_anchor, 0, 0, weight=10
)

solver.against_wall(floor_standing_lamp[0], walls[1])
solver.distance_constraint(
    floor_standing_lamp[0], lamp_anchor, 0, 0, weight=10
)

# Primary orientation constraints: the desk and chair face each other.
solver.point_towards(desk[0], chair[0])
solver.point_towards(chair[0], desk[0])

# Keep the bed parallel to the upper wall, the wardrobes consistently
# oriented along the lower wall, and the lamp at its unobtrusive orientation.
solver.align_with(bed[0], desk[0], angle=180)
solver.align_with(wardrobe_A[0], desk[0], angle=-90)
solver.align_with(wardrobe_B[0], desk[0], angle=-90)
solver.align_with(floor_standing_lamp[0], bed[0])

# Secondary spacing constraints preserve clearances between neighboring
# furniture and discourage overlaps during feasibility adjustments.
solver.distance_constraint(bed[0], chair[0], 1.50, None, weight=10)
solver.distance_constraint(wardrobe_A[0], wardrobe_B[0], 0.95, None, weight=10)
solver.distance_constraint(desk[0], wardrobe_A[0], 1.10, None, weight=10)
solver.distance_constraint(chair[0], wardrobe_A[0], 1.15, None, weight=10)
solver.distance_constraint(
    floor_standing_lamp[0], desk[0], 1.20, None, weight=10
)

solver.constraints = []
wardrobe_A[0].position = [2.9000000953674316, 0.30000004172325134, 1.0]
wardrobe_A[0].rotation = [0, 0, 1.5707963651502053]
wardrobe_A[0].optimize = 2
wardrobe_B[0].position = [1.899999976158142, 0.30000001192092896, 1.0]
wardrobe_B[0].rotation = [0, 0, 1.5707963651181849]
wardrobe_B[0].optimize = 2
bed[0].position = [0.7681164145469666, 1.879978895187378, 0.2750000059604645]
bed[0].rotation = [0, 0, -1.5707962781393332]
bed[0].optimize = 2
desk[0].position = [3.0999996662139893, 1.4500000476837158, 0.375]
desk[0].rotation = [0, 0, -3.141592622897168]
desk[0].optimize = 2
floor_standing_lamp[0].position = [3.200000047683716, 2.7305002212524414, 0.7749999761581421]
floor_standing_lamp[0].rotation = [0, 0, -1.5707962991553168]
floor_standing_lamp[0].optimize = 2
chair[0].position = [2.361948013305664, 1.4500000476837158, 0.42500001192092896]
chair[0].rotation = [0, 0, 0.021991148286022624]
chair[0].optimize = 2

