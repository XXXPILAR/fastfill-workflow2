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
    Wall(corner1=[6.20, 6.60, 0.00], corner2=[0.00, 6.60, 0.00]),
    Wall(corner1=[0.00, 6.60, 0.00], corner2=[0.00, 4.10, 0.00]),
    Wall(corner1=[0.00, 4.10, 0.00], corner2=[0.50, 4.10, 0.00]),
    Wall(corner1=[0.50, 4.10, 0.00], corner2=[0.50, 3.60, 0.00]),
    Wall(corner1=[0.50, 3.60, 0.00], corner2=[0.00, 3.60, 0.00]),
    Wall(corner1=[0.00, 3.60, 0.00], corner2=[0.00, 0.10, 0.00]),
    Wall(corner1=[0.00, 0.10, 0.00], corner2=[1.00, 0.10, 0.00]),
    Wall(corner1=[1.00, 0.10, 0.00], corner2=[1.00, 0.00, 0.00]),
    Wall(corner1=[1.00, 0.00, 0.00], corner2=[6.20, 0.00, 0.00]),
    Wall(corner1=[6.20, 0.00, 0.00], corner2=[6.20, 6.60, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
sofa = Assets(description="sofa", size=[0.90, 2.20, 0.85], placements=[AssetInstance() for _ in range(1)])
multifunctional_combination_bed = Assets(description="multifunctional combination bed", size=[2.10, 2.40, 2.20], placements=[AssetInstance() for _ in range(1)])
shower_room_A = Assets(description="shower room", size=[1.20, 1.20, 2.30], placements=[AssetInstance() for _ in range(1)])
shower_room_B = Assets(description="shower room", size=[1.20, 1.20, 2.30], placements=[AssetInstance() for _ in range(1)])

sofa[0].instance_id = 'sofa_0'
multifunctional_combination_bed[0].instance_id = 'multifunctional_combination_bed_0'
shower_room_A[0].instance_id = 'shower_room_A_0'
shower_room_B[0].instance_id = 'shower_room_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'
walls[8].instance_id = 'walls_8'
walls[9].instance_id = 'walls_9'

sofa[0].position = [1.8219704966030261, 5.700075411318124, 0.425]
sofa[0].rotation = [0, 0, 0]
multifunctional_combination_bed[0].position = [5.763417017423294, 6.100577145184051, 1.1]
multifunctional_combination_bed[0].rotation = [0, 0, 0]
shower_room_A[0].position = [1.9173113500172638, 6.298213761006449, 1.15]
shower_room_A[0].rotation = [0, 0, 0]
shower_room_B[0].position = [4.794855666218318, 2.508403049912169, 1.15]
shower_room_B[0].rotation = [0, 0, 0]
sofa[0].position = [1.8219704966030261, 5.700075411318124, 0.425]
sofa[0].rotation = [0, 0, 0]
multifunctional_combination_bed[0].position = [5.763417017423294, 6.100577145184051, 1.1]
multifunctional_combination_bed[0].rotation = [0, 0, 0]
shower_room_A[0].position = [1.9173113500172638, 6.298213761006449, 1.15]
shower_room_A[0].rotation = [0, 0, 0]
shower_room_B[0].position = [4.794855666218318, 2.508403049912169, 1.15]
shower_room_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the bed along the upper wall, facing +x toward shower_room_B.
# Its footprint spans x=0.50..2.60 and y=4.20..6.60.
multifunctional_combination_bed[0].position = [1.55, 5.40, 1.10]
multifunctional_combination_bed[0].rotation = [0, 0, radians(0)]

# Place shower_room_B along the right wall, directly in front of the bed.
# It remains above the doorway clearance zone.
shower_room_B[0].position = [5.60, 5.40, 1.15]
shower_room_B[0].rotation = [0, 0, radians(180)]

# Place the sofa along the lower wall, oriented into the room. Rotating it
# 90 degrees makes its shallow 0.90 m dimension perpendicular to the wall.
sofa[0].position = [3.25, 0.45, 0.425]
sofa[0].rotation = [0, 0, radians(90)]

# Place the other shower room against the lower section of the left wall.
shower_room_A[0].position = [0.60, 1.30, 1.15]
shower_room_A[0].rotation = [0, 0, radians(0)]

# Fixed anchors retain the proposed functional zones while physical
# feasibility adjustments are performed.
bed_anchor = AssetInstance(position=[1.55, 5.40, 1.10])
shower_B_anchor = AssetInstance(position=[5.60, 5.40, 1.15])
sofa_anchor = AssetInstance(position=[3.25, 0.45, 0.425])
shower_A_anchor = AssetInstance(position=[0.60, 1.30, 1.15])

# Important position constraints are listed first. They keep every asset at
# its planned location and leave the 1 m doorway centered at (6.20, 3.90)
# unobstructed.
solver.distance_constraint(
    multifunctional_combination_bed[0], bed_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    shower_room_B[0], shower_B_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    sofa[0], sofa_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    shower_room_A[0], shower_A_anchor, 0, 0, weight=10
)

# Wall relationships preserve the intended perimeter placement.
solver.against_wall(multifunctional_combination_bed[0], walls[0])
solver.against_wall(shower_room_B[0], walls[9])
solver.against_wall(sofa[0], walls[8])
solver.against_wall(shower_room_A[0], walls[5])

# The multifunctional bed faces shower_room_B (o0003), as required.
solver.point_towards(
    multifunctional_combination_bed[0], shower_room_B[0]
)

# Orient shower_room_B back toward the bed and give the remaining assets
# stable orientations consistent with their assigned walls.
solver.point_towards(
    shower_room_B[0], multifunctional_combination_bed[0]
)
solver.align_with(
    sofa[0], multifunctional_combination_bed[0], angle=90
)
solver.align_with(
    shower_room_A[0], multifunctional_combination_bed[0], angle=0
)

# Supplemental spacing constraints help prevent overlap if later feasibility
# adjustments move assets away from their anchors.
solver.distance_constraint(
    multifunctional_combination_bed[0], shower_room_B[0],
    3.50, None, weight=1
)
solver.distance_constraint(
    multifunctional_combination_bed[0], sofa[0],
    3.00, None, weight=1
)
solver.distance_constraint(
    multifunctional_combination_bed[0], shower_room_A[0],
    3.00, None, weight=1
)
solver.distance_constraint(
    sofa[0], shower_room_A[0],
    2.00, None, weight=1
)
solver.distance_constraint(
    sofa[0], shower_room_B[0],
    3.00, None, weight=1
)

solver.constraints = []
sofa[0].position = [3.25, 0.47407951951026917, 0.42500001192092896]
sofa[0].rotation = [0, 0, 1.571034890268998]
sofa[0].optimize = 2
shower_room_B[0].position = [5.599864482879639, 5.400000095367432, 1.149999976158142]
shower_room_B[0].rotation = [0, 0, -3.141353258336989]
shower_room_B[0].optimize = 2
shower_room_A[0].position = [0.6112025380134583, 1.2999999523162842, 1.149999976158142]
shower_room_A[0].rotation = [0, 0, -0.00018603434910622138]
shower_room_A[0].optimize = 2
multifunctional_combination_bed[0].position = [1.5499999523162842, 5.367610931396484, 1.100000023841858]
multifunctional_combination_bed[0].rotation = [0, 0, 0.0002277764091409394]
multifunctional_combination_bed[0].optimize = 2

