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
    Wall(corner1=[0.00, 3.84, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.67, 0.00, 0.00]),
    Wall(corner1=[2.67, 0.00, 0.00], corner2=[2.67, 3.84, 0.00]),
    Wall(corner1=[2.67, 3.84, 0.00], corner2=[0.00, 3.84, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
chair_A = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.00, 1.40, 0.55], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="cabinet", size=[0.45, 0.80, 1.80], placements=[AssetInstance() for _ in range(1)])
desk = Assets(description="desk", size=[0.60, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])

chair_A[0].instance_id = 'chair_A_0'
bed[0].instance_id = 'bed_0'
chair_B[0].instance_id = 'chair_B_0'
cabinet[0].instance_id = 'cabinet_0'
desk[0].instance_id = 'desk_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

chair_A[0].position = [2.2033837817275908, 1.5595661421426574, 0.425]
chair_A[0].rotation = [0, 0, 0]
bed[0].position = [0.9597521856233239, 1.314180102198184, 0.275]
bed[0].rotation = [0, 0, 0]
chair_B[0].position = [1.6370264502108556, 3.705788368875264, 0.425]
chair_B[0].rotation = [0, 0, 0]
cabinet[0].position = [1.2027282491270983, 0.17702708870502848, 0.9]
cabinet[0].rotation = [0, 0, 0]
desk[0].position = [1.7994141816427172, 3.488061324097768, 0.375]
desk[0].rotation = [0, 0, 0]
chair_A[0].position = [2.2033837817275908, 1.5595661421426574, 0.425]
chair_A[0].rotation = [0, 0, 0]
bed[0].position = [0.9597521856233239, 1.314180102198184, 0.275]
bed[0].rotation = [0, 0, 0]
chair_B[0].position = [1.6370264502108556, 3.705788368875264, 0.425]
chair_B[0].rotation = [0, 0, 0]
cabinet[0].position = [1.2027282491270983, 0.17702708870502848, 0.9]
cabinet[0].rotation = [0, 0, 0]
desk[0].position = [1.7994141816427172, 3.488061324097768, 0.375]
desk[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the bed lengthwise along the left wall. This preserves a clear aisle on
# the right side of the room and keeps the doorway approach unobstructed.
bed[0].position = [0.70, 2.40, 0.275]
bed[0].rotation = [0, 0, radians(90)]

# Place the desk against the right wall, directly opposite the bed. Its front
# faces -x, toward the bed, while its northern edge stops well before the door.
desk[0].position = [2.37, 2.40, 0.375]
desk[0].rotation = [0, 0, radians(180)]

# Keep the tall cabinet against the lower part of the right wall, away from the
# door, desk, and window. It faces inward toward the room.
cabinet[0].position = [2.445, 0.55, 0.90]
cabinet[0].rotation = [0, 0, radians(180)]

# Group the two chairs near the foot of the bed. Their centers are separated by
# 0.72 m, giving their roughly 0.52 m-wide footprints no more than 0.20 m of
# edge-to-edge separation without forcing the chairs to overlap.
chair_A[0].position = [0.45, 0.80, 0.425]
chair_A[0].rotation = [0, 0, radians(41)]
chair_B[0].position = [1.17, 0.80, 0.425]
chair_B[0].rotation = [0, 0, radians(52)]

# Fixed anchors preserve the intended zones while the solver resolves minor
# physical adjustments. Orientation references are used for assets whose
# facing should remain tied to the room rather than to another movable object.
bed_anchor = AssetInstance(position=[0.70, 2.40, 0.275])
desk_anchor = AssetInstance(position=[2.37, 2.40, 0.375])
cabinet_anchor = AssetInstance(position=[2.445, 0.55, 0.90])
chair_A_anchor = AssetInstance(position=[0.45, 0.80, 0.425])
chair_B_anchor = AssetInstance(position=[1.17, 0.80, 0.425])

bed_orientation = AssetInstance(rotation=[0, 0, radians(90)])
room_center = AssetInstance(position=[1.335, 1.92, 0.90])

# Desk: facing the bed is the primary semantic requirement.
solver.point_towards(desk[0], bed[0])
solver.against_wall(desk[0], walls[2])
solver.distance_constraint(
    desk[0], desk_anchor, min_distance=0, max_distance=0, weight=10
)

# Bed: hold it against the left wall and lengthwise along that wall.
solver.against_wall(bed[0], walls[0])
solver.align_with(bed[0], bed_orientation)
solver.distance_constraint(
    bed[0], bed_anchor, min_distance=0, max_distance=0, weight=10
)

# Cabinet: enforce the requested wall placement and orient its front inward.
solver.against_wall(cabinet[0], walls[2])
solver.point_towards(cabinet[0], room_center)
solver.distance_constraint(
    cabinet[0], cabinet_anchor, min_distance=0, max_distance=0, weight=10
)

# The chair-center range accounts for a chair's approximate width: a center
# distance of 0.52–0.72 m corresponds to an edge gap of approximately 0–0.20 m.
# Apply the relationship in both directions so either chair can be adjusted.
solver.distance_constraint(
    chair_A[0], chair_B[0], min_distance=0.52, max_distance=0.72, weight=10
)
solver.point_towards(chair_A[0], desk[0])
solver.distance_constraint(
    chair_A[0], chair_A_anchor, min_distance=0, max_distance=0, weight=10
)

solver.distance_constraint(
    chair_B[0], chair_A[0], min_distance=0.52, max_distance=0.72, weight=10
)
solver.point_towards(chair_B[0], desk[0])
solver.distance_constraint(
    chair_B[0], chair_B_anchor, min_distance=0, max_distance=0, weight=10
)

solver.constraints = []
bed[0].position = [1.000000238418579, 2.4000000953674316, 0.2750000059604645]
bed[0].rotation = [0, 0, -2.6055702202324906e-08]
bed[0].optimize = 2
cabinet[0].position = [2.4498531818389893, 0.5519171953201294, 0.8999999761581421]
cabinet[0].rotation = [0, 0, -3.141558796415946]
cabinet[0].optimize = 2
chair_B[0].position = [1.1699999570846558, 0.800000011920929, 0.42500001192092896]
chair_B[0].rotation = [0, 0, 0.9232791655214302]
chair_B[0].optimize = 2
desk[0].position = [2.374790668487549, 2.4058587551116943, 0.375]
desk[0].rotation = [0, 0, -3.1415587962391682]
desk[0].optimize = 2
chair_A[0].position = [0.44999998807907104, 0.800000011920929, 0.42500001192092896]
chair_A[0].rotation = [0, 0, 0.7312929384118189]
chair_A[0].optimize = 2

