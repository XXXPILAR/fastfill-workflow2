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
ornaments_A = Assets(description="ornaments", size=[0.12, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
nightstand = Assets(description="nightstand", size=[0.40, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
ornaments_B = Assets(description="ornaments", size=[0.14, 0.20, 0.28], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.00, 1.60, 0.95], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.60, 1.40, 2.20], placements=[AssetInstance() for _ in range(1)])
desk = Assets(description="desk", size=[0.50, 1.00, 0.75], placements=[AssetInstance() for _ in range(1)])
desk_lamp = Assets(description="desk lamp", size=[0.22, 0.18, 0.42], placements=[AssetInstance() for _ in range(1)])
chair = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])

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

ornaments_A[0].position = [2.5974607723772962, 0.8055487396290676, 0.125]
ornaments_A[0].rotation = [0, 0, 0]
nightstand[0].position = [2.6737279392412803, 0.047238928690547646, 0.275]
nightstand[0].rotation = [0, 0, 0]
ornaments_B[0].position = [1.6938217857071414, 1.6292298115798034, 0.14]
ornaments_B[0].rotation = [0, 0, 0]
bed[0].position = [3.24615439203794, 0.8206857123752138, 0.475]
bed[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.2729777302891058, 0.1657218497594168, 1.1]
wardrobe[0].rotation = [0, 0, 0]
desk[0].position = [1.9278184052393805, 0.6994791523972035, 0.375]
desk[0].rotation = [0, 0, 0]
desk_lamp[0].position = [2.5729130257442754, 2.1751904714354233, 0.21]
desk_lamp[0].rotation = [0, 0, 0]
chair[0].position = [2.109957553704267, 2.7317288336430883, 0.425]
chair[0].rotation = [0, 0, 0]
ornaments_A[0].position = [2.5974607723772962, 0.8055487396290676, 0.125]
ornaments_A[0].rotation = [0, 0, 0]
nightstand[0].position = [2.6737279392412803, 0.047238928690547646, 0.275]
nightstand[0].rotation = [0, 0, 0]
ornaments_B[0].position = [1.6938217857071414, 1.6292298115798034, 0.14]
ornaments_B[0].rotation = [0, 0, 0]
bed[0].position = [3.24615439203794, 0.8206857123752138, 0.475]
bed[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.2729777302891058, 0.1657218497594168, 1.1]
wardrobe[0].rotation = [0, 0, 0]
desk[0].position = [1.9278184052393805, 0.6994791523972035, 0.375]
desk[0].rotation = [0, 0, 0]
desk_lamp[0].position = [2.5729130257442754, 2.1751904714354233, 0.21]
desk_lamp[0].rotation = [0, 0, 0]
chair[0].position = [2.109957553704267, 2.7317288336430883, 0.425]
chair[0].rotation = [0, 0, 0]

solver.constraints = []

# The bed occupies the lower-right part of the room. Its long axis runs
# east-west, and its head/back is placed against the right wall. This leaves
# a circulation lane from both doors through the upper-middle/left area.
bed[0].position = [2.71, 0.85, 0.475]
bed[0].rotation = [0, 0, radians(180)]

# The nightstand sits beside the exposed lower-left corner of the bed.
nightstand[0].position = [1.43, 0.225, 0.275]
nightstand[0].rotation = [0, 0, radians(180)]

# The desk is against the bottom wall, clear of the left-wall doorway.
# Rotating it 90 degrees makes its 1 m-wide working edge run along the wall.
desk[0].position = [0.60, 0.25, 0.375]
desk[0].rotation = [0, 0, radians(90)]

# The chair is in front of the desk, with enough room to pull it back without
# intersecting the bed or the route immediately inside the left doorway.
chair[0].position = [0.85, 0.95, 0.425]
chair[0].rotation = [0, 0, radians(-90)]

# The wardrobe is centered on the unobstructed portion of the top wall.
# Its footprint ends before the top doorway, whose opening begins near x=2.70.
wardrobe[0].position = [1.75, 2.50, 1.10]
wardrobe[0].rotation = [0, 0, radians(-90)]

# Small objects are initialized at the correct surface heights.
ornaments_A[0].position = [1.43, 0.225, 0.675]
ornaments_A[0].rotation = [0, 0, radians(180)]

ornaments_B[0].position = [0.85, 0.25, 0.89]
ornaments_B[0].rotation = [0, 0, radians(90)]

desk_lamp[0].position = [0.35, 0.25, 0.96]
desk_lamp[0].rotation = [0, 0, radians(90)]


# Reference points preserve the assets' intended positions along their walls
# and keep them from sliding into either doorway during optimization.
bed_anchor = AssetInstance(position=[2.71, 0.85, 0.475])
nightstand_anchor = AssetInstance(position=[1.43, 0.225, 0.275])
desk_anchor = AssetInstance(position=[0.60, 0.25, 0.375])
chair_anchor = AssetInstance(position=[0.85, 0.95, 0.425])
wardrobe_anchor = AssetInstance(position=[1.75, 2.50, 1.10])

ornaments_A_anchor = AssetInstance(position=[1.43, 0.225, 0.675])
ornaments_B_anchor = AssetInstance(position=[0.85, 0.25, 0.89])
desk_lamp_anchor = AssetInstance(position=[0.35, 0.25, 0.96])


# Bed: contact with the right wall is the primary positional relationship.
# It faces into the room, and the anchor prevents movement toward the top door.
solver.against_wall(bed[0], walls[1])
solver.distance_constraint(
    bed[0], bed_anchor, min_distance=0.0, max_distance=0.10, weight=10
)
solver.point_towards(bed[0], chair[0])

# Nightstand: keep it against the bottom wall and immediately beside the bed.
solver.against_wall(nightstand[0], walls[0])
solver.distance_constraint(
    nightstand[0], nightstand_anchor,
    min_distance=0.0, max_distance=0.06, weight=10
)
solver.align_with(nightstand[0], bed[0])

# Desk: retain wall contact and its position below the left doorway opening.
solver.against_wall(desk[0], walls[0])
solver.distance_constraint(
    desk[0], desk_anchor, min_distance=0.0, max_distance=0.08, weight=10
)
solver.point_towards(desk[0], chair[0])

# Chair: keep it at a usable distance from the desk and facing the work surface.
solver.distance_constraint(
    chair[0], chair_anchor, min_distance=0.0, max_distance=0.12, weight=10
)
solver.distance_constraint(
    chair[0], desk[0], min_distance=0.70, max_distance=0.90, weight=5
)
solver.point_towards(chair[0], desk[0])

# Wardrobe: retain contact with the top wall while remaining left of the
# top doorway and away from the left doorway's interior approach.
solver.against_wall(wardrobe[0], walls[2])
solver.distance_constraint(
    wardrobe[0], wardrobe_anchor,
    min_distance=0.0, max_distance=0.08, weight=10
)
solver.point_towards(wardrobe[0], chair[0])

# Ornament A belongs on the nightstand. The anchor keeps it centered safely
# within the relatively small tabletop.
solver.on_top_of(ornaments_A[0], nightstand[0])
solver.distance_constraint(
    ornaments_A[0], ornaments_A_anchor,
    min_distance=0.0, max_distance=0.04, weight=10
)
solver.distance_constraint(
    ornaments_A[0], nightstand[0],
    min_distance=0.35, max_distance=0.50, weight=5
)
solver.align_with(ornaments_A[0], nightstand[0])

# Ornament B and the lamp occupy opposite portions of the desk surface.
solver.on_top_of(ornaments_B[0], desk[0])
solver.distance_constraint(
    ornaments_B[0], ornaments_B_anchor,
    min_distance=0.0, max_distance=0.05, weight=10
)
solver.distance_constraint(
    ornaments_B[0], desk[0],
    min_distance=0.45, max_distance=0.65, weight=5
)
solver.align_with(ornaments_B[0], desk[0])

solver.on_top_of(desk_lamp[0], desk[0])
solver.distance_constraint(
    desk_lamp[0], desk_lamp_anchor,
    min_distance=0.0, max_distance=0.05, weight=10
)
solver.distance_constraint(
    desk_lamp[0], desk[0],
    min_distance=0.55, max_distance=0.75, weight=5
)
solver.align_with(desk_lamp[0], desk[0])

# Maintain separation between the two desktop objects if the desk is adjusted.
solver.distance_constraint(
    ornaments_B[0], desk_lamp[0],
    min_distance=0.40, max_distance=0.65, weight=5
)

solver.constraints = []
desk[0].position = [0.6000000238418579, 0.2502101957798004, 0.375]
desk[0].rotation = [0, 0, 1.5707242667469334]
desk[0].optimize = 2
nightstand[0].position = [1.4299999475479126, 0.23809196054935455, 0.2750000059604645]
nightstand[0].rotation = [0, 0, 1.7564297816144845]
nightstand[0].optimize = 2
bed[0].position = [2.394308090209961, 1.127265453338623, 0.4749999940395355]
bed[0].rotation = [0, 0, 1.751122306979137]
bed[0].optimize = 2
ornaments_A[0].position = [1.4535788297653198, 0.4460161328315735, 0.675000011920929]
ornaments_A[0].rotation = [0, 0, 1.763283426924222]
ornaments_A[0].optimize = 2
ornaments_B[0].position = [0.5293752551078796, 0.07010290026664734, 0.8899999856948853]
ornaments_B[0].rotation = [0, 0, 1.5697670415576597]
ornaments_B[0].optimize = 2
desk_lamp[0].position = [0.09011317789554596, 0.11009258031845093, 0.9599999785423279]
desk_lamp[0].rotation = [0, 0, 1.5697670415576597]
desk_lamp[0].optimize = 2
wardrobe[0].position = [1.7424211502075195, 2.494786262512207, 1.100000023841858]
wardrobe[0].rotation = [0, 0, -1.5693216759350967]
wardrobe[0].optimize = 2
chair[0].position = [0.8500000238418579, 0.949999988079071, 0.42500001192092896]
chair[0].rotation = [0, 0, -1.548805178508874]
chair[0].optimize = 2

