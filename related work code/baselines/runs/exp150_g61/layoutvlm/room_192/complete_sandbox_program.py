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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.71, 0.00, 0.00]),
    Wall(corner1=[3.71, 0.00, 0.00], corner2=[3.71, 2.80, 0.00]),
    Wall(corner1=[3.71, 2.80, 0.00], corner2=[0.00, 2.79, 0.00]),
    Wall(corner1=[0.00, 2.79, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
ornaments_A = Assets(description="ornaments", size=[0.14, 0.14, 0.22], placements=[AssetInstance() for _ in range(1)])
nightstand = Assets(description="nightstand", size=[0.40, 0.45, 0.50], placements=[AssetInstance() for _ in range(1)])
ornaments_B = Assets(description="ornaments", size=[0.12, 0.18, 0.20], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.10, 1.60, 0.95], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.60, 1.20, 2.20], placements=[AssetInstance() for _ in range(1)])
desk = Assets(description="desk", size=[0.45, 0.90, 0.75], placements=[AssetInstance() for _ in range(1)])
desk_lamp = Assets(description="desk lamp", size=[0.25, 0.18, 0.40], placements=[AssetInstance() for _ in range(1)])
chair = Assets(description="chair", size=[0.50, 0.45, 0.85], placements=[AssetInstance() for _ in range(1)])

ornaments_A[0].instance_id = 'ornaments_A_0'
nightstand[0].instance_id = 'nightstand_0'
ornaments_B[0].instance_id = 'ornaments_B_0'
bed[0].instance_id = 'bed_0'
wardrobe[0].instance_id = 'wardrobe_0'
desk[0].instance_id = 'desk_0'
desk_lamp[0].instance_id = 'desk_lamp_0'
chair[0].instance_id = 'chair_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

ornaments_A[0].position = [2.5424291580504934, 0.48357384803217807, 0.11]
ornaments_A[0].rotation = [0, 0, 0]
nightstand[0].position = [0.9733727742924909, 0.7714663343244164, 0.25]
nightstand[0].rotation = [0, 0, 0]
ornaments_B[0].position = [3.1640590541597957, 0.9888168967723422, 0.1]
ornaments_B[0].rotation = [0, 0, 0]
bed[0].position = [3.0268827715600755, 0.26849723925789104, 0.475]
bed[0].rotation = [0, 0, 0]
wardrobe[0].position = [2.027873992406736, 2.745993081901288, 1.1]
wardrobe[0].rotation = [0, 0, 0]
desk[0].position = [0.8837538924190278, 0.5985097856967382, 0.375]
desk[0].rotation = [0, 0, 0]
desk_lamp[0].position = [3.5981040649435623, 2.3709271461459447, 0.2]
desk_lamp[0].rotation = [0, 0, 0]
chair[0].position = [1.6911032124121086, 0.27218976257582395, 0.425]
chair[0].rotation = [0, 0, 0]
ornaments_A[0].position = [2.5424291580504934, 0.48357384803217807, 0.11]
ornaments_A[0].rotation = [0, 0, 0]
nightstand[0].position = [0.9733727742924909, 0.7714663343244164, 0.25]
nightstand[0].rotation = [0, 0, 0]
ornaments_B[0].position = [3.1640590541597957, 0.9888168967723422, 0.1]
ornaments_B[0].rotation = [0, 0, 0]
bed[0].position = [3.0268827715600755, 0.26849723925789104, 0.475]
bed[0].rotation = [0, 0, 0]
wardrobe[0].position = [2.027873992406736, 2.745993081901288, 1.1]
wardrobe[0].rotation = [0, 0, 0]
desk[0].position = [0.8837538924190278, 0.5985097856967382, 0.375]
desk[0].rotation = [0, 0, 0]
desk_lamp[0].position = [3.5981040649435623, 2.3709271461459447, 0.2]
desk_lamp[0].rotation = [0, 0, 0]
chair[0].position = [1.6911032124121086, 0.27218976257582395, 0.425]
chair[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the supplied boundary coordinates: x=0..3.71, y=0..approximately 2.80.
# The bed occupies the southeast corner. Storage stays below the main
# circulation route, and the desk occupies the northwest wall segment.
# Keep the west doorway's approach and the northeast doorway landing clear.

bed[0].position = [2.66, 0.80, 0.475]
bed[0].rotation = [0, 0, 0]

wardrobe[0].position = [1.15, 0.60, 1.10]
wardrobe[0].rotation = [0, 0, radians(180)]

nightstand[0].position = [1.81, 1.875, 0.25]
nightstand[0].rotation = [0, 0, 0]

desk[0].position = [1.10, 2.565, 0.375]
desk[0].rotation = [0, 0, radians(270)]

# The chair faces north toward the desk, with a small gap between footprints.
chair[0].position = [1.10, 1.97, 0.425]
chair[0].rotation = [0, 0, radians(90)]

# Small objects sit on their supporting surfaces, not on the floor.
desk_lamp[0].position = [1.40, 2.565, 0.95]
desk_lamp[0].rotation = [0, 0, radians(270)]

# Separate the two ornaments along the depth of the nightstand.
ornaments_A[0].position = [1.81, 1.77, 0.61]
ornaments_A[0].rotation = [0, 0, 0]

ornaments_B[0].position = [1.81, 1.98, 0.60]
ornaments_B[0].rotation = [0, 0, 0]

# Register the important position constraints first. Fixed center anchors
# preserve the compact, nonoverlapping arrangement and the doorway clearances.
for placed_instance in (
    bed[0],
    wardrobe[0],
    nightstand[0],
    desk[0],
    chair[0],
    desk_lamp[0],
    ornaments_A[0],
    ornaments_B[0],
):
    solver.distance_constraint(
        placed_instance,
        AssetInstance(position=list(placed_instance.position)),
        0,
        0,
        weight=10,
    )

# Preserve the floor furniture orientations independently of solver movement.
for placed_instance in (
    bed[0],
    wardrobe[0],
    nightstand[0],
    desk[0],
):
    solver.align_with(
        placed_instance,
        AssetInstance(rotation=list(placed_instance.rotation)),
        angle=0,
    )

# The bed touches the south and east walls; the wardrobe backs onto the
# south-side storage zone while opening west into the available approach.
solver.against_wall(bed[0], walls[0])
solver.against_wall(bed[0], walls[1])
solver.against_wall(wardrobe[0], walls[0])

# Keep the bedside surface beside the bed, with parallel orientation.
solver.align_with(nightstand[0], bed[0])
solver.distance_constraint(nightstand[0], bed[0], 1.35, 1.50, weight=10)

# Chair and desk face each other; the lamp follows the desk orientation.
solver.point_towards(chair[0], desk[0])
solver.align_with(chair[0], desk[0], angle=180)
solver.distance_constraint(chair[0], desk[0], 0.59, 0.66, weight=10)

solver.on_top_of(desk_lamp[0], desk[0])
solver.align_with(desk_lamp[0], desk[0])
solver.distance_constraint(desk_lamp[0], desk[0], 0.64, 0.67)

# Both ornaments remain supported by the nightstand. Their center separation
# exceeds their combined footprint half-depths, so they do not touch.
solver.on_top_of(ornaments_A[0], nightstand[0])
solver.on_top_of(ornaments_B[0], nightstand[0])
solver.align_with(ornaments_A[0], nightstand[0])
solver.align_with(ornaments_B[0], nightstand[0])
solver.distance_constraint(
    ornaments_A[0], ornaments_B[0], 0.20, 0.23, weight=10
)

solver.constraints = []
chair[0].position = [1.100000023841858, 1.9700000286102295, 0.42500001192092896]
chair[0].rotation = [0, 0, 1.5990707210351487]
chair[0].optimize = 2
desk_lamp[0].position = [1.5561810731887817, 2.352811813354492, 0.949999988079071]
desk_lamp[0].rotation = [0, 0, -1.5425220200603302]
desk_lamp[0].optimize = 2
ornaments_A[0].position = [1.768648624420166, 1.885122537612915, 0.6100000143051147]
ornaments_A[0].rotation = [0, 0, 1.5707742464934138]
ornaments_A[0].optimize = 2
wardrobe[0].position = [1.149999976158142, 0.3000146746635437, 1.100000023841858]
wardrobe[0].rotation = [0, 0, 1.5708007209701238]
wardrobe[0].optimize = 2
desk[0].position = [1.100000023841858, 2.565000057220459, 0.375]
desk[0].rotation = [0, 0, -1.5425219923833045]
desk[0].optimize = 2
ornaments_B[0].position = [1.7842860221862793, 1.979995608329773, 0.6000000238418579]
ornaments_B[0].rotation = [0, 0, 1.5707742464934138]
ornaments_B[0].optimize = 2
bed[0].position = [2.637662172317505, 1.0498988628387451, 0.4749999940395355]
bed[0].rotation = [0, 0, 1.5707766570195107]
bed[0].optimize = 2
nightstand[0].position = [1.5592855215072632, 2.0851268768310547, 0.25]
nightstand[0].rotation = [0, 0, 1.5707756944049538]
nightstand[0].optimize = 2

