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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[5.47, 0.00, 0.00]),
    Wall(corner1=[5.47, 0.00, 0.00], corner2=[5.47, 4.19, 0.00]),
    Wall(corner1=[5.47, 4.19, 0.00], corner2=[1.02, 4.19, 0.00]),
    Wall(corner1=[1.02, 4.19, 0.00], corner2=[1.03, 1.64, 0.00]),
    Wall(corner1=[1.03, 1.64, 0.00], corner2=[0.00, 1.64, 0.00]),
    Wall(corner1=[0.00, 1.64, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bed = Assets(description="bed", size=[2.10, 1.80, 1.05], placements=[AssetInstance() for _ in range(1)])
nightstand_A = Assets(description="nightstand", size=[0.42, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
chair = Assets(description="chair", size=[0.55, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
stool = Assets(description="stool", size=[0.40, 0.40, 0.45], placements=[AssetInstance() for _ in range(1)])
wardrobe_A = Assets(description="wardrobe", size=[0.60, 1.20, 2.30], placements=[AssetInstance() for _ in range(1)])
nightstand_B = Assets(description="nightstand", size=[0.42, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[3.00, 2.40, 0.01], placements=[AssetInstance() for _ in range(1)])
dining_table_combination = Assets(description="dining table combination", size=[0.65, 0.90, 0.75], placements=[AssetInstance() for _ in range(1)])
wardrobe_B = Assets(description="wardrobe", size=[0.60, 1.20, 2.30], placements=[AssetInstance() for _ in range(1)])

bed[0].instance_id = 'bed_0'
nightstand_A[0].instance_id = 'nightstand_A_0'
chair[0].instance_id = 'chair_0'
stool[0].instance_id = 'stool_0'
wardrobe_A[0].instance_id = 'wardrobe_A_0'
nightstand_B[0].instance_id = 'nightstand_B_0'
carpet[0].instance_id = 'carpet_0'
dining_table_combination[0].instance_id = 'dining_table_combination_0'
wardrobe_B[0].instance_id = 'wardrobe_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

bed[0].position = [1.855522563453437, 3.954234327759548, 0.525]
bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [4.97182428125591, 1.5123990218430412, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
chair[0].position = [2.6663517315672562, 0.6806258139115293, 0.425]
chair[0].rotation = [0, 0, 0]
stool[0].position = [0.9797513636589408, 0.6792897600158209, 0.225]
stool[0].rotation = [0, 0, 0]
wardrobe_A[0].position = [2.6560523673165464, 1.9432852317083165, 1.15]
wardrobe_A[0].rotation = [0, 0, 0]
nightstand_B[0].position = [1.6293405138008135, 3.621410126678435, 0.275]
nightstand_B[0].rotation = [0, 0, 0]
carpet[0].position = [3.5158379610303756, 1.2861474812286489, 0.0075]
carpet[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [1.825527977560692, 2.323512734876842, 0.375]
dining_table_combination[0].rotation = [0, 0, 0]
wardrobe_B[0].position = [1.1352589517875264, 1.5683636691971807, 1.15]
wardrobe_B[0].rotation = [0, 0, 0]
bed[0].position = [1.855522563453437, 3.954234327759548, 0.525]
bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [4.97182428125591, 1.5123990218430412, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
chair[0].position = [2.6663517315672562, 0.6806258139115293, 0.425]
chair[0].rotation = [0, 0, 0]
stool[0].position = [0.9797513636589408, 0.6792897600158209, 0.225]
stool[0].rotation = [0, 0, 0]
wardrobe_A[0].position = [2.6560523673165464, 1.9432852317083165, 1.15]
wardrobe_A[0].rotation = [0, 0, 0]
nightstand_B[0].position = [1.6293405138008135, 3.621410126678435, 0.275]
nightstand_B[0].rotation = [0, 0, 0]
carpet[0].position = [3.5158379610303756, 1.2861474812286489, 0.0075]
carpet[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [1.825527977560692, 2.323512734876842, 0.375]
dining_table_combination[0].rotation = [0, 0, 0]
wardrobe_B[0].position = [1.1352589517875264, 1.5683636691971807, 1.15]
wardrobe_B[0].rotation = [0, 0, 0]

solver.constraints = []

# The upper-right area is the sleeping zone. The bed faces south, with
# a nightstand on each side of its head. The carpet supports this group.
# Keep the west entrance alcove and the route into the room unobstructed.
bed[0].position = [3.85, 3.14, 0.535]
bed[0].rotation = [0, 0, radians(-90)]

nightstand_A[0].position = [2.65, 3.98, 0.285]
nightstand_A[0].rotation = [0, 0, radians(-90)]

nightstand_B[0].position = [5.05, 3.98, 0.285]
nightstand_B[0].rotation = [0, 0, radians(-90)]

carpet[0].position = [3.87, 2.99, 0.005]
carpet[0].rotation = [0, 0, 0]

# Two wardrobes along the south wall face into the room.
# Their combined footprint leaves the entrance approach clear.
wardrobe_A[0].position = [1.95, 0.30, 1.15]
wardrobe_A[0].rotation = [0, 0, radians(90)]

wardrobe_B[0].position = [3.25, 0.30, 1.15]
wardrobe_B[0].rotation = [0, 0, radians(90)]

# The dining area occupies the southeast corner, below the window.
# The chair has a gap to the table and an open approach from the north.
dining_table_combination[0].position = [5.145, 0.65, 0.375]
dining_table_combination[0].rotation = [0, 0, radians(180)]

chair[0].position = [4.20, 0.65, 0.425]
chair[0].rotation = [0, 0, 0]

# A spare stool sits in the northwest corner, outside the circulation route.
stool[0].position = [1.50, 3.90, 0.225]
stool[0].rotation = [0, 0, radians(-90)]

# Preserve the verified, non-intersecting positions. Fixed-point constraints
# also keep the door approaches clear without inventing physical assets.
for placed_instance in (
    bed[0],
    nightstand_A[0],
    nightstand_B[0],
    carpet[0],
    wardrobe_A[0],
    wardrobe_B[0],
    dining_table_combination[0],
    chair[0],
    stool[0],
):
    solver.distance_constraint(
        placed_instance,
        AssetInstance(position=list(placed_instance.position)),
        0,
        0,
        weight=10,
    )

# Set the primary facing constraints before supplemental alignments.
solver.point_towards(chair[0], dining_table_combination[0])
solver.align_with(
    bed[0], AssetInstance(rotation=[0, 0, radians(-90)])
)
solver.align_with(nightstand_A[0], bed[0])
solver.align_with(nightstand_B[0], bed[0])
solver.align_with(
    carpet[0], AssetInstance(rotation=[0, 0, 0])
)
solver.align_with(
    wardrobe_A[0], AssetInstance(rotation=[0, 0, radians(90)])
)
solver.align_with(wardrobe_B[0], wardrobe_A[0])
solver.align_with(dining_table_combination[0], chair[0], angle=180)
solver.align_with(stool[0], bed[0])

# Only the thin carpet intentionally shares the sleeping group's footprint;
# furniture rests on its upper surface rather than intersecting it.
solver.on_top_of(bed[0], carpet[0])
solver.on_top_of(nightstand_A[0], carpet[0])
solver.on_top_of(nightstand_B[0], carpet[0])

# Reinforce wall placement without placing tall furniture over the window.
solver.against_wall(bed[0], walls[2])
solver.against_wall(nightstand_A[0], walls[2])
solver.against_wall(nightstand_B[0], walls[2])
solver.against_wall(wardrobe_A[0], walls[0])
solver.against_wall(wardrobe_B[0], walls[0])
solver.against_wall(dining_table_combination[0], walls[1])

# Preserve bedside relationships and dining clearance using true 3D
# center distances, since the assets have different center heights.
for bedside_instance in (nightstand_A[0], nightstand_B[0]):
    bedside_distance = sum(
        (bedside_instance.position[axis] - bed[0].position[axis]) ** 2
        for axis in range(3)
    ) ** 0.5
    solver.distance_constraint(
        bedside_instance, bed[0],
        bedside_distance, bedside_distance, weight=10
    )

dining_distance = sum(
    (chair[0].position[axis]
     - dining_table_combination[0].position[axis]) ** 2
    for axis in range(3)
) ** 0.5
solver.distance_constraint(
    chair[0], dining_table_combination[0],
    dining_distance, dining_distance, weight=10
)

solver.constraints = []
wardrobe_A[0].position = [1.9499987363815308, 0.30000025033950806, 1.149999976158142]
wardrobe_A[0].rotation = [0, 0, 1.5707963016857298]
wardrobe_A[0].optimize = 2
chair[0].position = [4.202425003051758, 0.6499854922294617, 0.42500001192092896]
chair[0].rotation = [0, 0, 0.0157079639172164]
chair[0].optimize = 2
wardrobe_B[0].position = [3.250001907348633, 0.3000001907348633, 1.149999976158142]
wardrobe_B[0].rotation = [0, 0, 1.5707963021494045]
wardrobe_B[0].optimize = 2
carpet[0].position = [3.869999885559082, 2.9641101360321045, 0.004999999888241291]
carpet[0].rotation = [0, 0, 0.01884955539881635]
carpet[0].optimize = 2
dining_table_combination[0].position = [5.147507190704346, 0.6499853134155273, 0.375]
dining_table_combination[0].rotation = [0, 0, -3.140262679484729]
dining_table_combination[0].optimize = 2
nightstand_B[0].position = [5.131727695465088, 3.982147216796875, 0.2849999964237213]
nightstand_B[0].rotation = [0, 0, -1.5707963929979891]
nightstand_B[0].optimize = 2
stool[0].position = [1.5, 3.9000000953674316, 0.22499999403953552]
stool[0].rotation = [0, 0, -1.5707964687417038]
stool[0].optimize = 2
bed[0].position = [3.8502957820892334, 3.1421701908111572, 0.5349999666213989]
bed[0].rotation = [0, 0, -1.570796451487615]
bed[0].optimize = 2
nightstand_A[0].position = [2.5682718753814697, 3.982147693634033, 0.2849999964237213]
nightstand_A[0].rotation = [0, 0, -1.5707963934291773]
nightstand_A[0].optimize = 2

