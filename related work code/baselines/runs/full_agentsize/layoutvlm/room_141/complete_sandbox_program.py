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
    Wall(corner1=[3.00, 0.00, 0.00], corner2=[3.00, 3.00, 0.00]),
    Wall(corner1=[3.00, 3.00, 0.00], corner2=[0.00, 3.00, 0.00]),
    Wall(corner1=[0.00, 3.00, 0.00], corner2=[0.00, 1.00, 0.00]),
    Wall(corner1=[0.00, 1.00, 0.00], corner2=[1.00, 1.00, 0.00]),
    Wall(corner1=[1.00, 1.00, 0.00], corner2=[1.00, 0.00, 0.00]),
    Wall(corner1=[1.00, 0.00, 0.00], corner2=[3.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
small_bathroom_bin_A = Assets(description="A small cylindrical gray trash can with a black step opener and a large black hinge on top.", size=[0.28, 0.22, 0.32], placements=[AssetInstance() for _ in range(1)])
freestanding_towel_rack = Assets(description="A black towel rack.", size=[0.30, 0.65, 0.90], placements=[AssetInstance() for _ in range(1)])
shower_enclosure = Assets(description="A big cabinet with two large doors.", size=[0.90, 1.20, 2.10], placements=[AssetInstance() for _ in range(1)])
wall_shelf_bathroom_A = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.18, 0.60, 0.22], placements=[AssetInstance() for _ in range(1)])
wall_shelf_bathroom_B = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.18, 0.60, 0.22], placements=[AssetInstance() for _ in range(1)])
vanity_cabinet_with_sink = Assets(description="A kitchen sink with a wood cabinet.", size=[0.52, 0.90, 0.88], placements=[AssetInstance() for _ in range(1)])
small_toiletry_bottles = Assets(description="White soap bottle model", size=[0.08, 0.18, 0.22], placements=[AssetInstance() for _ in range(1)])
tall_bathroom_cabinet = Assets(description="tall bathroom cabinet", size=[0.38, 0.45, 1.85], placements=[AssetInstance() for _ in range(1)])
wall_mirror = Assets(description="A rectangular mirror in a brown wooden frame.", size=[0.04, 0.70, 0.90], placements=[AssetInstance() for _ in range(1)])
small_bathroom_bin_B = Assets(description="A small cylindrical gray trash can with a black step opener and a large black hinge on top.", size=[0.28, 0.22, 0.32], placements=[AssetInstance() for _ in range(1)])
laundry_hamper = Assets(description="A wicker basket with pink bands and some blue patterns.", size=[0.38, 0.45, 0.58], placements=[AssetInstance() for _ in range(1)])
toilet = Assets(description="White toilet model", size=[0.70, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])

small_bathroom_bin_A[0].instance_id = 'small_bathroom_bin_A_0'
freestanding_towel_rack[0].instance_id = 'freestanding_towel_rack_0'
shower_enclosure[0].instance_id = 'shower_enclosure_0'
wall_shelf_bathroom_A[0].instance_id = 'wall_shelf_bathroom_A_0'
wall_shelf_bathroom_B[0].instance_id = 'wall_shelf_bathroom_B_0'
vanity_cabinet_with_sink[0].instance_id = 'vanity_cabinet_with_sink_0'
small_toiletry_bottles[0].instance_id = 'small_toiletry_bottles_0'
tall_bathroom_cabinet[0].instance_id = 'tall_bathroom_cabinet_0'
wall_mirror[0].instance_id = 'wall_mirror_0'
small_bathroom_bin_B[0].instance_id = 'small_bathroom_bin_B_0'
laundry_hamper[0].instance_id = 'laundry_hamper_0'
toilet[0].instance_id = 'toilet_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

small_bathroom_bin_A[0].position = [1.1880287321085765, 1.4232544677874168, 0.16]
small_bathroom_bin_A[0].rotation = [0, 0, 0]
freestanding_towel_rack[0].position = [1.8941078765713062, 0.05200090934867363, 0.45]
freestanding_towel_rack[0].rotation = [0, 0, 0]
shower_enclosure[0].position = [2.4062192662263184, 2.3346662051513, 1.05]
shower_enclosure[0].rotation = [0, 0, 0]
wall_shelf_bathroom_A[0].position = [2.912191459584358, 1.1294821275004658, 0.11]
wall_shelf_bathroom_A[0].rotation = [0, 0, 0]
wall_shelf_bathroom_B[0].position = [2.2755176458374566, 0.4022052298048262, 0.11]
wall_shelf_bathroom_B[0].rotation = [0, 0, 0]
vanity_cabinet_with_sink[0].position = [0.5160737637792439, 1.349892413531585, 0.44]
vanity_cabinet_with_sink[0].rotation = [0, 0, 0]
small_toiletry_bottles[0].position = [2.7088036066572325, 1.3605941911998711, 0.11]
small_toiletry_bottles[0].rotation = [0, 0, 0]
tall_bathroom_cabinet[0].position = [0.5276626707298602, 2.2664207921222514, 0.925]
tall_bathroom_cabinet[0].rotation = [0, 0, 0]
wall_mirror[0].position = [1.6678296584862728, 1.579231776244838, 0.45]
wall_mirror[0].rotation = [0, 0, 0]
small_bathroom_bin_B[0].position = [0.22758026742851345, 1.8099386581237624, 0.16]
small_bathroom_bin_B[0].rotation = [0, 0, 0]
laundry_hamper[0].position = [0.6222844150020066, 2.4516848003283487, 0.29]
laundry_hamper[0].rotation = [0, 0, 0]
toilet[0].position = [1.3388964474794827, 2.29108811572868, 0.39]
toilet[0].rotation = [0, 0, 0]
small_bathroom_bin_A[0].position = [1.1880287321085765, 1.4232544677874168, 0.16]
small_bathroom_bin_A[0].rotation = [0, 0, 0]
freestanding_towel_rack[0].position = [1.8941078765713062, 0.05200090934867363, 0.45]
freestanding_towel_rack[0].rotation = [0, 0, 0]
shower_enclosure[0].position = [2.4062192662263184, 2.3346662051513, 1.05]
shower_enclosure[0].rotation = [0, 0, 0]
wall_shelf_bathroom_A[0].position = [2.912191459584358, 1.1294821275004658, 0.11]
wall_shelf_bathroom_A[0].rotation = [0, 0, 0]
wall_shelf_bathroom_B[0].position = [2.2755176458374566, 0.4022052298048262, 0.11]
wall_shelf_bathroom_B[0].rotation = [0, 0, 0]
vanity_cabinet_with_sink[0].position = [0.5160737637792439, 1.349892413531585, 0.44]
vanity_cabinet_with_sink[0].rotation = [0, 0, 0]
small_toiletry_bottles[0].position = [2.7088036066572325, 1.3605941911998711, 0.11]
small_toiletry_bottles[0].rotation = [0, 0, 0]
tall_bathroom_cabinet[0].position = [0.5276626707298602, 2.2664207921222514, 0.925]
tall_bathroom_cabinet[0].rotation = [0, 0, 0]
wall_mirror[0].position = [1.6678296584862728, 1.579231776244838, 0.45]
wall_mirror[0].rotation = [0, 0, 0]
small_bathroom_bin_B[0].position = [0.22758026742851345, 1.8099386581237624, 0.16]
small_bathroom_bin_B[0].rotation = [0, 0, 0]
laundry_hamper[0].position = [0.6222844150020066, 2.4516848003283487, 0.29]
laundry_hamper[0].rotation = [0, 0, 0]
toilet[0].position = [1.3388964474794827, 2.29108811572868, 0.39]
toilet[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the large fixtures around the perimeter, leaving the lower-central area
# in front of the door unobstructed.
small_bathroom_bin_A[0].position = [1.05, 2.35, 0.16]
small_bathroom_bin_A[0].rotation = [0, 0, radians(-90)]

freestanding_towel_rack[0].position = [0.15, 1.40, 0.45]
freestanding_towel_rack[0].rotation = [0, 0, radians(0)]

# The enclosure occupies the upper-left corner and opens toward the room.
shower_enclosure[0].position = [0.45, 2.40, 1.05]
shower_enclosure[0].rotation = [0, 0, radians(0)]

# The shelves are mounted on the right wall, above the floor fixtures and
# beyond the window centered at y=0.60.
wall_shelf_bathroom_A[0].position = [2.91, 1.35, 1.35]
wall_shelf_bathroom_A[0].rotation = [0, 0, radians(180)]

wall_shelf_bathroom_B[0].position = [2.91, 1.95, 1.35]
wall_shelf_bathroom_B[0].rotation = [0, 0, radians(180)]

# The vanity and mirror form a group on the upper wall.
vanity_cabinet_with_sink[0].position = [1.55, 2.74, 0.44]
vanity_cabinet_with_sink[0].rotation = [0, 0, radians(-90)]

small_toiletry_bottles[0].position = [1.55, 2.55, 0.99]
small_toiletry_bottles[0].rotation = [0, 0, radians(-90)]

wall_mirror[0].position = [1.55, 2.98, 1.55]
wall_mirror[0].rotation = [0, 0, radians(-90)]

# The tall cabinet fits in the upper-right corner without obstructing the
# vanity or the toilet.
tall_bathroom_cabinet[0].position = [2.75, 2.81, 0.925]
tall_bathroom_cabinet[0].rotation = [0, 0, radians(-90)]

small_bathroom_bin_B[0].position = [2.65, 1.82, 0.16]
small_bathroom_bin_B[0].rotation = [0, 0, radians(180)]

# Keep the hamper above the window zone and away from the door approach.
laundry_hamper[0].position = [2.81, 1.30, 0.29]
laundry_hamper[0].rotation = [0, 0, radians(180)]

# The toilet is backed against the right wall and faces the shower enclosure.
toilet[0].position = [2.65, 2.35, 0.39]
toilet[0].rotation = [0, 0, radians(180)]


# Fixed target points preserve the proposed functional zones while allowing
# the solver to reconcile the accompanying wall and relationship constraints.
_target_bin_A = AssetInstance(position=[1.05, 2.35, 0.16])
_target_towel_rack = AssetInstance(position=[0.15, 1.40, 0.45])
_target_shower = AssetInstance(position=[0.45, 2.40, 1.05])
_target_shelf_A = AssetInstance(position=[2.91, 1.35, 1.35])
_target_shelf_B = AssetInstance(position=[2.91, 1.95, 1.35])
_target_vanity = AssetInstance(position=[1.55, 2.74, 0.44])
_target_bottles = AssetInstance(position=[1.55, 2.55, 0.99])
_target_cabinet = AssetInstance(position=[2.75, 2.81, 0.925])
_target_mirror = AssetInstance(position=[1.55, 2.98, 1.55])
_target_bin_B = AssetInstance(position=[2.65, 1.82, 0.16])
_target_hamper = AssetInstance(position=[2.81, 1.30, 0.29])
_target_toilet = AssetInstance(position=[2.65, 2.35, 0.39])

# Orientation references point into the usable room from the relevant walls.
_center_from_left = AssetInstance(position=[1.50, 1.40, 0.45])
_center_from_shower = AssetInstance(position=[1.50, 2.40, 1.05])
_center_from_top = AssetInstance(position=[1.55, 1.50, 0.44])

# High-priority position constraints keep every new instance in its intended
# non-overlapping location.
solver.distance_constraint(
    small_bathroom_bin_A[0], _target_bin_A, 0, 0, weight=10
)
solver.distance_constraint(
    freestanding_towel_rack[0], _target_towel_rack, 0, 0, weight=10
)
solver.distance_constraint(
    shower_enclosure[0], _target_shower, 0, 0, weight=10
)
solver.distance_constraint(
    wall_shelf_bathroom_A[0], _target_shelf_A, 0, 0, weight=10
)
solver.distance_constraint(
    wall_shelf_bathroom_B[0], _target_shelf_B, 0, 0, weight=10
)
solver.distance_constraint(
    vanity_cabinet_with_sink[0], _target_vanity, 0, 0, weight=10
)
solver.distance_constraint(
    small_toiletry_bottles[0], _target_bottles, 0, 0, weight=10
)
solver.distance_constraint(
    tall_bathroom_cabinet[0], _target_cabinet, 0, 0, weight=10
)
solver.distance_constraint(
    wall_mirror[0], _target_mirror, 0, 0, weight=10
)
solver.distance_constraint(
    small_bathroom_bin_B[0], _target_bin_B, 0, 0, weight=10
)
solver.distance_constraint(
    laundry_hamper[0], _target_hamper, 0, 0, weight=10
)
solver.distance_constraint(
    toilet[0], _target_toilet, 0, 0, weight=10
)

# Perimeter relationships for floor-standing and wall-mounted objects.
solver.against_wall(freestanding_towel_rack[0], walls[2])
solver.against_wall(shower_enclosure[0], walls[2])
solver.against_wall(wall_shelf_bathroom_A[0], walls[0])
solver.against_wall(wall_shelf_bathroom_B[0], walls[0])
solver.against_wall(vanity_cabinet_with_sink[0], walls[1])
solver.against_wall(tall_bathroom_cabinet[0], walls[1])
solver.against_wall(wall_mirror[0], walls[1])
solver.against_wall(laundry_hamper[0], walls[0])
solver.against_wall(toilet[0], walls[0])

# The soap bottle is a small object and must remain supported by the vanity.
solver.on_top_of(small_toiletry_bottles[0], vanity_cabinet_with_sink[0])

# Orientation constraints for every asset. The toilet-to-shower relationship is
# specified directly so it remains valid if either fixture is adjusted.
solver.align_with(
    small_bathroom_bin_A[0], vanity_cabinet_with_sink[0]
)
solver.point_towards(
    freestanding_towel_rack[0], _center_from_left
)
solver.point_towards(
    shower_enclosure[0], _center_from_shower
)
solver.align_with(
    wall_shelf_bathroom_A[0], toilet[0]
)
solver.align_with(
    wall_shelf_bathroom_B[0], toilet[0]
)
solver.point_towards(
    vanity_cabinet_with_sink[0], _center_from_top
)
solver.align_with(
    small_toiletry_bottles[0], vanity_cabinet_with_sink[0]
)
solver.align_with(
    tall_bathroom_cabinet[0], vanity_cabinet_with_sink[0]
)
solver.align_with(
    wall_mirror[0], vanity_cabinet_with_sink[0]
)
solver.align_with(
    small_bathroom_bin_B[0], toilet[0]
)
solver.align_with(
    laundry_hamper[0], toilet[0]
)
solver.point_towards(toilet[0], shower_enclosure[0])

# Preserve a practical separation between the two opposing major fixtures.
solver.distance_constraint(
    toilet[0], shower_enclosure[0], 2.0, 2.6, weight=1
)

solver.constraints = []
freestanding_towel_rack[0].position = [0.15082532167434692, 1.399999976158142, 0.44999998807907104]
freestanding_towel_rack[0].rotation = [0, 0, 0.002540918150658852]
freestanding_towel_rack[0].optimize = 2
toilet[0].position = [2.6466195583343506, 2.3499999046325684, 0.38999998569488525]
toilet[0].rotation = [0, 0, -3.123497738126235]
toilet[0].optimize = 2
small_bathroom_bin_B[0].position = [2.6500000953674316, 1.8200000524520874, 0.1599999964237213]
small_bathroom_bin_B[0].rotation = [0, 0, -3.1219750899034664]
small_bathroom_bin_B[0].optimize = 2
tall_bathroom_cabinet[0].position = [2.75, 2.8094289302825928, 0.925000011920929]
tall_bathroom_cabinet[0].rotation = [0, 0, -1.5682554074221384]
tall_bathroom_cabinet[0].optimize = 2
wall_shelf_bathroom_A[0].position = [2.90923810005188, 1.350000023841858, 0.10999999940395355]
wall_shelf_bathroom_A[0].rotation = [0, 0, -3.139051734217035]
wall_shelf_bathroom_A[0].optimize = 2
wall_mirror[0].position = [1.5499999523162842, 2.9886972904205322, 0.44999998807907104]
wall_mirror[0].rotation = [0, 0, -1.5682554086442377]
wall_mirror[0].optimize = 2
small_bathroom_bin_A[0].position = [1.0499999523162842, 2.3499999046325684, 0.1599999964237213]
small_bathroom_bin_A[0].rotation = [0, 0, -1.5511787631085696]
small_bathroom_bin_A[0].optimize = 2
vanity_cabinet_with_sink[0].position = [1.5499999523162842, 2.737381935119629, 0.4399999976158142]
vanity_cabinet_with_sink[0].rotation = [0, 0, -1.5527014150200016]
vanity_cabinet_with_sink[0].optimize = 2
laundry_hamper[0].position = [2.8094289302825928, 1.2999999523162842, 0.28999999165534973]
laundry_hamper[0].rotation = [0, 0, -3.139051734217035]
laundry_hamper[0].optimize = 2
shower_enclosure[0].position = [0.4512293338775635, 2.4000000953674316, 1.0499999523162842]
shower_enclosure[0].rotation = [0, 0, 0.008762216232799396]
shower_enclosure[0].optimize = 2
small_toiletry_bottles[0].position = [1.5499999523162842, 2.549999952316284, 0.9900000095367432]
small_toiletry_bottles[0].rotation = [0, 0, -1.5480062806449197]
small_toiletry_bottles[0].optimize = 2
wall_shelf_bathroom_B[0].position = [2.90923810005188, 1.9500000476837158, 0.10999999940395355]
wall_shelf_bathroom_B[0].rotation = [0, 0, -3.139051734217035]
wall_shelf_bathroom_B[0].optimize = 2

