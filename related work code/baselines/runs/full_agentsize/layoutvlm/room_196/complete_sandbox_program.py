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
    Wall(corner1=[0.00, 3.15, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.06, 0.00, 0.00]),
    Wall(corner1=[6.06, 0.00, 0.00], corner2=[6.06, 1.00, 0.00]),
    Wall(corner1=[6.06, 1.00, 0.00], corner2=[6.02, 1.00, 0.00]),
    Wall(corner1=[6.02, 1.00, 0.00], corner2=[6.02, 0.98, 0.00]),
    Wall(corner1=[6.02, 0.98, 0.00], corner2=[4.04, 0.98, 0.00]),
    Wall(corner1=[4.04, 0.98, 0.00], corner2=[4.04, 3.15, 0.00]),
    Wall(corner1=[4.04, 3.15, 0.00], corner2=[0.00, 3.15, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bed = Assets(description="bed", size=[2.00, 1.80, 0.60], placements=[AssetInstance() for _ in range(1)])
nightstand_A = Assets(description="nightstand", size=[0.40, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.60, 2.40, 2.40], placements=[AssetInstance() for _ in range(1)])
nightstand_B = Assets(description="nightstand", size=[0.40, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])

bed[0].instance_id = 'bed_0'
nightstand_A[0].instance_id = 'nightstand_A_0'
wardrobe[0].instance_id = 'wardrobe_0'
nightstand_B[0].instance_id = 'nightstand_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

bed[0].position = [2.5851732851582767, 0.43759232771893636, 0.3]
bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [0.13019756991964482, 0.33138978303326855, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
wardrobe[0].position = [4.243103078620529, 0.4425268365687329, 1.2]
wardrobe[0].rotation = [0, 0, 0]
nightstand_B[0].position = [1.5379048248554572, 1.8048109400436905, 0.275]
nightstand_B[0].rotation = [0, 0, 0]
bed[0].position = [2.5851732851582767, 0.43759232771893636, 0.3]
bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [0.13019756991964482, 0.33138978303326855, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
wardrobe[0].position = [4.243103078620529, 0.4425268365687329, 1.2]
wardrobe[0].rotation = [0, 0, 0]
nightstand_B[0].position = [1.5379048248554572, 1.8048109400436905, 0.275]
nightstand_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the bed with its head against the north wall. Rotating it 270 degrees
# makes its long axis run north-south and its front face toward the room.
bed[0].position = [2.00, 2.15, 0.30]
bed[0].rotation = [0, 0, radians(270)]

# Flank the bed at the north wall so that the bed lies between the nightstands.
# Their edges meet the sides of the bed without overlapping.
nightstand_A[0].position = [0.85, 2.95, 0.275]
nightstand_A[0].rotation = [0, 0, radians(270)]

nightstand_B[0].position = [3.15, 2.95, 0.275]
nightstand_B[0].rotation = [0, 0, radians(270)]

# Put the wardrobe against the south wall of the main rectangular portion.
# Its shallow dimension projects into the room, while its placement avoids
# both doors and leaves the window and circulation routes unobstructed.
wardrobe[0].position = [2.40, 0.30, 1.20]
wardrobe[0].rotation = [0, 0, radians(90)]

# Fixed anchors preserve the intended ordering and doorway-safe arrangement
# if the solver needs to adjust the layout.
bed_anchor = AssetInstance(position=[2.00, 2.15, 0.30])
nightstand_A_anchor = AssetInstance(position=[0.85, 2.95, 0.275])
nightstand_B_anchor = AssetInstance(position=[3.15, 2.95, 0.275])
wardrobe_anchor = AssetInstance(position=[2.40, 0.30, 1.20])
bedroom_center = AssetInstance(position=[2.00, 1.45, 0.30])
wardrobe_front_target = AssetInstance(position=[2.40, 1.45, 1.20])

# Bed: retain its central position, keep its head against the north wall,
# and orient its front toward the open floor.
solver.distance_constraint(bed[0], bed_anchor, 0.0, 0.0, weight=10)
solver.against_wall(bed[0], walls[7])
solver.point_towards(bed[0], bedroom_center)

# Nightstand A: preserve the left-hand flanking position, remain against the
# same wall as the bed, and share the bed's orientation.
solver.distance_constraint(
    nightstand_A[0], nightstand_A_anchor, 0.0, 0.0, weight=10
)
solver.against_wall(nightstand_A[0], walls[7])
solver.distance_constraint(
    nightstand_A[0], bed[0], 1.40, 1.41, weight=10
)
solver.align_with(nightstand_A[0], bed[0])

# Nightstand B: preserve the right-hand flanking position so the bed remains
# between the two nightstands.
solver.distance_constraint(
    nightstand_B[0], nightstand_B_anchor, 0.0, 0.0, weight=10
)
solver.against_wall(nightstand_B[0], walls[7])
solver.distance_constraint(
    nightstand_B[0], bed[0], 1.40, 1.41, weight=10
)
solver.align_with(nightstand_B[0], bed[0])

# Wardrobe: stay on the unobstructed part of the south wall and face into the
# room. Its anchor keeps it away from the door centered at (5.59, 0.00).
solver.distance_constraint(
    wardrobe[0], wardrobe_anchor, 0.0, 0.0, weight=10
)
solver.against_wall(wardrobe[0], walls[1])
solver.point_towards(wardrobe[0], wardrobe_front_target)

solver.constraints = []
nightstand_B[0].position = [3.200195550918579, 2.9499998092651367, 0.2750000059604645]
nightstand_B[0].rotation = [0, 0, -1.5707960871763984]
nightstand_B[0].optimize = 2
bed[0].position = [2.0, 2.1500000953674316, 0.30000001192092896]
bed[0].rotation = [0, 0, -1.5707961465187001]
bed[0].optimize = 2
wardrobe[0].position = [2.4000000953674316, 0.29999983310699463, 1.2000000476837158]
wardrobe[0].rotation = [0, 0, 1.5707964786921425]
wardrobe[0].optimize = 2
nightstand_A[0].position = [0.7998045682907104, 2.9499998092651367, 0.2750000059604645]
nightstand_A[0].rotation = [0, 0, -1.5707960871763984]
nightstand_A[0].optimize = 2

