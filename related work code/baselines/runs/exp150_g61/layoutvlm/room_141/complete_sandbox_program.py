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
small_bathroom_bin_A = Assets(description="A small cylindrical gray trash can with a black step opener and a large black hinge on top.", size=[0.28, 0.24, 0.32], placements=[AssetInstance() for _ in range(1)])
freestanding_towel_rack = Assets(description="A black towel rack.", size=[0.30, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
shower_enclosure = Assets(description="A big cabinet with two large doors.", size=[0.90, 0.90, 2.10], placements=[AssetInstance() for _ in range(1)])
wall_shelf_bathroom_A = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.20, 0.60, 0.18], placements=[AssetInstance() for _ in range(1)])
wall_shelf_bathroom_B = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.20, 0.60, 0.18], placements=[AssetInstance() for _ in range(1)])
vanity_cabinet_with_sink = Assets(description="A kitchen sink with a wood cabinet.", size=[0.50, 0.80, 0.85], placements=[AssetInstance() for _ in range(1)])
small_toiletry_bottles = Assets(description="White soap bottle model", size=[0.07, 0.07, 0.18], placements=[AssetInstance() for _ in range(1)])
tall_bathroom_cabinet = Assets(description="tall bathroom cabinet", size=[0.35, 0.40, 1.80], placements=[AssetInstance() for _ in range(1)])
wall_mirror = Assets(description="A rectangular mirror in a brown wooden frame.", size=[0.04, 0.65, 0.85], placements=[AssetInstance() for _ in range(1)])
small_bathroom_bin_B = Assets(description="A small cylindrical gray trash can with a black step opener and a large black hinge on top.", size=[0.28, 0.24, 0.32], placements=[AssetInstance() for _ in range(1)])
laundry_hamper = Assets(description="A wicker basket with pink bands and some blue patterns.", size=[0.35, 0.40, 0.55], placements=[AssetInstance() for _ in range(1)])
toilet = Assets(description="White toilet model", size=[0.68, 0.38, 0.80], placements=[AssetInstance() for _ in range(1)])

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

small_bathroom_bin_A[0].position = [2.7090919840821157, 1.324459245326496, 0.16]
small_bathroom_bin_A[0].rotation = [0, 0, 0]
freestanding_towel_rack[0].position = [1.2843319044928099, 1.6363305077060892, 0.45]
freestanding_towel_rack[0].rotation = [0, 0, 0]
shower_enclosure[0].position = [1.2601029382093636, 2.701847005221377, 1.05]
shower_enclosure[0].rotation = [0, 0, 0]
wall_shelf_bathroom_A[0].position = [0.4953283076534274, 2.074302299976379, 0.09]
wall_shelf_bathroom_A[0].rotation = [0, 0, 0]
wall_shelf_bathroom_B[0].position = [1.2894584878559703, 0.40807762505372425, 0.09]
wall_shelf_bathroom_B[0].rotation = [0, 0, 0]
vanity_cabinet_with_sink[0].position = [1.539069107433948, 1.6947006004477156, 0.425]
vanity_cabinet_with_sink[0].rotation = [0, 0, 0]
small_toiletry_bottles[0].position = [1.62963010867928, 0.8038073385755143, 0.09]
small_toiletry_bottles[0].rotation = [0, 0, 0]
tall_bathroom_cabinet[0].position = [1.3856398997585329, 1.535480423099524, 0.9]
tall_bathroom_cabinet[0].rotation = [0, 0, 0]
wall_mirror[0].position = [1.8080223546895917, 1.52069054009015, 0.425]
wall_mirror[0].rotation = [0, 0, 0]
small_bathroom_bin_B[0].position = [2.699600481369909, 2.144454418318546, 0.16]
small_bathroom_bin_B[0].rotation = [0, 0, 0]
laundry_hamper[0].position = [0.011721245306167694, 1.4495604572851861, 0.275]
laundry_hamper[0].rotation = [0, 0, 0]
toilet[0].position = [0.5940826122555569, 2.695370187371111, 0.4]
toilet[0].rotation = [0, 0, 0]
small_bathroom_bin_A[0].position = [2.7090919840821157, 1.324459245326496, 0.16]
small_bathroom_bin_A[0].rotation = [0, 0, 0]
freestanding_towel_rack[0].position = [1.2843319044928099, 1.6363305077060892, 0.45]
freestanding_towel_rack[0].rotation = [0, 0, 0]
shower_enclosure[0].position = [1.2601029382093636, 2.701847005221377, 1.05]
shower_enclosure[0].rotation = [0, 0, 0]
wall_shelf_bathroom_A[0].position = [0.4953283076534274, 2.074302299976379, 0.09]
wall_shelf_bathroom_A[0].rotation = [0, 0, 0]
wall_shelf_bathroom_B[0].position = [1.2894584878559703, 0.40807762505372425, 0.09]
wall_shelf_bathroom_B[0].rotation = [0, 0, 0]
vanity_cabinet_with_sink[0].position = [1.539069107433948, 1.6947006004477156, 0.425]
vanity_cabinet_with_sink[0].rotation = [0, 0, 0]
small_toiletry_bottles[0].position = [1.62963010867928, 0.8038073385755143, 0.09]
small_toiletry_bottles[0].rotation = [0, 0, 0]
tall_bathroom_cabinet[0].position = [1.3856398997585329, 1.535480423099524, 0.9]
tall_bathroom_cabinet[0].rotation = [0, 0, 0]
wall_mirror[0].position = [1.8080223546895917, 1.52069054009015, 0.425]
wall_mirror[0].rotation = [0, 0, 0]
small_bathroom_bin_B[0].position = [2.699600481369909, 2.144454418318546, 0.16]
small_bathroom_bin_B[0].rotation = [0, 0, 0]
laundry_hamper[0].position = [0.011721245306167694, 1.4495604572851861, 0.275]
laundry_hamper[0].rotation = [0, 0, 0]
toilet[0].position = [0.5940826122555569, 2.695370187371111, 0.4]
toilet[0].rotation = [0, 0, 0]

solver.constraints = []

# Keep the entrance (x=1.22..2.24 on y=0) and the central aisle clear.
# The shower and toilet face one another across the back of the room.
shower_enclosure[0].position = [2.55, 2.55, 1.05]
shower_enclosure[0].rotation = [0, 0, radians(180)]

toilet[0].position = [0.34, 2.55, 0.40]
toilet[0].rotation = [0, 0, 0]

# Sink on the west wall, with a wall-mounted mirror above it.
vanity_cabinet_with_sink[0].position = [0.25, 1.60, 0.425]
vanity_cabinet_with_sink[0].rotation = [0, 0, 0]

wall_mirror[0].position = [0.02, 1.60, 1.50]
wall_mirror[0].rotation = [0, 0, 0]

# Place the soap toward the rear side of the countertop, away from its edge.
small_toiletry_bottles[0].position = [0.25, 1.85, 0.94]
small_toiletry_bottles[0].rotation = [0, 0, 0]

# Back-wall storage occupies the space between the toilet and shower.
tall_bathroom_cabinet[0].position = [0.95, 2.825, 0.90]
tall_bathroom_cabinet[0].rotation = [0, 0, radians(270)]

# These are wall-mounted shelves, not floor-standing objects.
# Their fixed-height position constraints below provide their wall support.
wall_shelf_bathroom_A[0].position = [1.50, 2.90, 1.35]
wall_shelf_bathroom_A[0].rotation = [0, 0, radians(270)]

wall_shelf_bathroom_B[0].position = [1.50, 2.90, 1.85]
wall_shelf_bathroom_B[0].rotation = [0, 0, radians(270)]

# One bin fits between the vanity and toilet; the other is on the east wall.
small_bathroom_bin_A[0].position = [0.14, 2.19, 0.16]
small_bathroom_bin_A[0].rotation = [0, 0, 0]

small_bathroom_bin_B[0].position = [2.86, 1.25, 0.16]
small_bathroom_bin_B[0].rotation = [0, 0, radians(180)]

laundry_hamper[0].position = [2.825, 1.80, 0.275]
laundry_hamper[0].rotation = [0, 0, radians(180)]

# The rack sits beyond the door's right jamb, facing into the room.
# Nothing is installed against the window at x=3, y=0.19..1.01.
freestanding_towel_rack[0].position = [2.60, 0.15, 0.45]
freestanding_towel_rack[0].rotation = [0, 0, radians(90)]

# Preserve the carefully separated footprints and the mounting elevations.
# Fixed points are constraint references only, not additional scene assets.
for placed_instance in (
    shower_enclosure[0],
    toilet[0],
    vanity_cabinet_with_sink[0],
    wall_mirror[0],
    small_toiletry_bottles[0],
    tall_bathroom_cabinet[0],
    wall_shelf_bathroom_A[0],
    wall_shelf_bathroom_B[0],
    small_bathroom_bin_A[0],
    small_bathroom_bin_B[0],
    laundry_hamper[0],
    freestanding_towel_rack[0],
):
    solver.distance_constraint(
        placed_instance,
        AssetInstance(position=list(placed_instance.position)),
        0,
        0,
        weight=10,
    )

# Essential facing relationship comes before other orientation constraints.
solver.point_towards(toilet[0], shower_enclosure[0])
solver.point_towards(shower_enclosure[0], toilet[0])

# Preserve inward-facing orientations for the remaining fixtures.
for placed_instance in (
    vanity_cabinet_with_sink[0],
    wall_mirror[0],
    small_toiletry_bottles[0],
    tall_bathroom_cabinet[0],
    wall_shelf_bathroom_A[0],
    wall_shelf_bathroom_B[0],
    small_bathroom_bin_A[0],
    small_bathroom_bin_B[0],
    laundry_hamper[0],
    freestanding_towel_rack[0],
):
    solver.align_with(
        placed_instance,
        AssetInstance(
            position=list(placed_instance.position),
            rotation=list(placed_instance.rotation),
        ),
    )

# Wall attachment constraints reinforce the intended perimeter arrangement.
solver.against_wall(shower_enclosure[0], walls[0])
solver.against_wall(shower_enclosure[0], walls[1])
solver.against_wall(toilet[0], walls[2])
solver.against_wall(vanity_cabinet_with_sink[0], walls[2])
solver.against_wall(wall_mirror[0], walls[2])
solver.against_wall(small_bathroom_bin_A[0], walls[2])
solver.against_wall(tall_bathroom_cabinet[0], walls[1])
solver.against_wall(wall_shelf_bathroom_A[0], walls[1])
solver.against_wall(wall_shelf_bathroom_B[0], walls[1])
solver.against_wall(small_bathroom_bin_B[0], walls[0])
solver.against_wall(laundry_hamper[0], walls[0])
solver.against_wall(freestanding_towel_rack[0], walls[5])

# The bottle rests on the vanity, rather than on the floor.
solver.on_top_of(small_toiletry_bottles[0], vanity_cabinet_with_sink[0])
solver.align_with(small_toiletry_bottles[0], vanity_cabinet_with_sink[0])
solver.align_with(wall_mirror[0], vanity_cabinet_with_sink[0])
solver.align_with(wall_shelf_bathroom_B[0], wall_shelf_bathroom_A[0])

solver.constraints = []
wall_mirror[0].position = [0.019999999552965164, 1.600000023841858, 0.42500001192092896]
wall_mirror[0].rotation = [0, 0, 4.2007912657886956e-08]
wall_mirror[0].optimize = 2
freestanding_towel_rack[0].position = [2.5999999046325684, 0.15000000596046448, 0.44999998807907104]
freestanding_towel_rack[0].rotation = [0, 0, 1.5707963687077433]
freestanding_towel_rack[0].optimize = 2
wall_shelf_bathroom_A[0].position = [1.5, 2.8999998569488525, 0.09000000357627869]
wall_shelf_bathroom_A[0].rotation = [0, 0, -1.5707962830908866]
wall_shelf_bathroom_A[0].optimize = 2
vanity_cabinet_with_sink[0].position = [0.2500000298023224, 1.600000023841858, 0.42500001192092896]
vanity_cabinet_with_sink[0].rotation = [0, 0, 4.015642342182576e-08]
vanity_cabinet_with_sink[0].optimize = 2
small_bathroom_bin_A[0].position = [0.14000000059604645, 2.190000057220459, 0.1599999964237213]
small_bathroom_bin_A[0].rotation = [0, 0, 4.372283764140888e-08]
small_bathroom_bin_A[0].optimize = 2
wall_shelf_bathroom_B[0].position = [1.5, 2.8999998569488525, 0.09000000357627869]
wall_shelf_bathroom_B[0].rotation = [0, 0, -1.5707962830908866]
wall_shelf_bathroom_B[0].optimize = 2
laundry_hamper[0].position = [2.8249998092651367, 1.7999999523162842, 0.2750000059604645]
laundry_hamper[0].rotation = [0, 0, -3.141592609878265]
laundry_hamper[0].optimize = 2
shower_enclosure[0].position = [2.5500001907348633, 2.4919562339782715, 1.0499999523162842]
shower_enclosure[0].rotation = [0, 0, -3.141592609882439]
shower_enclosure[0].optimize = 2
tall_bathroom_cabinet[0].position = [1.1749930381774902, 1.0399460792541504, 0.8999999761581421]
tall_bathroom_cabinet[0].rotation = [0, 0, 0.008879083685889024]
tall_bathroom_cabinet[0].optimize = 2
small_toiletry_bottles[0].position = [0.25, 1.850000023841858, 0.940000057220459]
small_toiletry_bottles[0].rotation = [0, 0, 4.008326422137238e-08]
small_toiletry_bottles[0].optimize = 2
toilet[0].position = [0.3400000333786011, 2.549999952316284, 0.4000000059604645]
toilet[0].rotation = [0, 0, 4.370758703941423e-08]
toilet[0].optimize = 2
small_bathroom_bin_B[0].position = [2.8600001335144043, 1.25, 0.1599999964237213]
small_bathroom_bin_B[0].rotation = [0, 0, -3.141592609862223]
small_bathroom_bin_B[0].optimize = 2

