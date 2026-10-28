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
    Wall(corner1=[4.33, 6.17, 0.00], corner2=[2.38, 6.17, 0.00]),
    Wall(corner1=[2.38, 6.17, 0.00], corner2=[2.38, 4.51, 0.00]),
    Wall(corner1=[2.38, 4.51, 0.00], corner2=[3.17, 4.51, 0.00]),
    Wall(corner1=[3.17, 4.51, 0.00], corner2=[3.17, 2.30, 0.00]),
    Wall(corner1=[3.17, 2.30, 0.00], corner2=[0.00, 2.30, 0.00]),
    Wall(corner1=[0.00, 2.30, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[9.42, 0.00, 0.00]),
    Wall(corner1=[9.42, 0.00, 0.00], corner2=[9.42, 3.86, 0.00]),
    Wall(corner1=[9.42, 3.86, 0.00], corner2=[4.33, 3.86, 0.00]),
    Wall(corner1=[4.33, 3.86, 0.00], corner2=[4.33, 6.17, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
toy_A = Assets(description="toy", size=[0.16, 0.22, 0.18], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="coffee table", size=[0.60, 1.20, 0.42], placements=[AssetInstance() for _ in range(1)])
dining_chair_A = Assets(description="dining chair", size=[0.55, 0.48, 0.86], placements=[AssetInstance() for _ in range(1)])
sofa = Assets(description="sofa", size=[0.95, 2.40, 0.85], placements=[AssetInstance() for _ in range(1)])
tv_cabinet = Assets(description="tv cabinet", size=[0.45, 1.80, 0.55], placements=[AssetInstance() for _ in range(1)])
dining_chair_B = Assets(description="dining chair", size=[0.55, 0.48, 0.86], placements=[AssetInstance() for _ in range(1)])
toy_B = Assets(description="toy", size=[0.25, 0.35, 0.30], placements=[AssetInstance() for _ in range(1)])
partition_cabinet = Assets(description="partition cabinet", size=[0.40, 1.60, 1.80], placements=[AssetInstance() for _ in range(1)])
bookcase = Assets(description="bookcase", size=[0.32, 1.00, 2.00], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[2.00, 2.80, 0.01], placements=[AssetInstance() for _ in range(1)])
shoe_cabinet = Assets(description="shoe cabinet", size=[0.35, 1.00, 1.10], placements=[AssetInstance() for _ in range(1)])
refrigerator = Assets(description="refrigerator", size=[0.70, 0.70, 1.85], placements=[AssetInstance() for _ in range(1)])
chair = Assets(description="chair", size=[0.75, 0.70, 0.85], placements=[AssetInstance() for _ in range(1)])
dining_table = Assets(description="dining table", size=[0.90, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
ornaments = Assets(description="ornaments", size=[0.16, 0.22, 0.38], placements=[AssetInstance() for _ in range(1)])

toy_A[0].instance_id = 'toy_A_0'
coffee_table[0].instance_id = 'coffee_table_0'
dining_chair_A[0].instance_id = 'dining_chair_A_0'
sofa[0].instance_id = 'sofa_0'
tv_cabinet[0].instance_id = 'tv_cabinet_0'
dining_chair_B[0].instance_id = 'dining_chair_B_0'
toy_B[0].instance_id = 'toy_B_0'
partition_cabinet[0].instance_id = 'partition_cabinet_0'
bookcase[0].instance_id = 'bookcase_0'
carpet[0].instance_id = 'carpet_0'
shoe_cabinet[0].instance_id = 'shoe_cabinet_0'
refrigerator[0].instance_id = 'refrigerator_0'
chair[0].instance_id = 'chair_0'
dining_table[0].instance_id = 'dining_table_0'
ornaments[0].instance_id = 'ornaments_0'
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

toy_A[0].position = [8.050243293163623, 0.7048815938132467, 0.09]
toy_A[0].rotation = [0, 0, 0]
coffee_table[0].position = [0.5184903970876509, 0.8874441623208028, 0.21]
coffee_table[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [6.343516868089224, 3.5832220161781065, 0.43]
dining_chair_A[0].rotation = [0, 0, 0]
sofa[0].position = [7.6844822060354545, 0.9543173782807247, 0.425]
sofa[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [7.03231289835169, 3.804128092109213, 0.275]
tv_cabinet[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [8.093035702238232, 1.261384099964936, 0.43]
dining_chair_B[0].rotation = [0, 0, 0]
toy_B[0].position = [7.654478094580588, 2.65100016683432, 0.15]
toy_B[0].rotation = [0, 0, 0]
partition_cabinet[0].position = [4.580936482627547, 2.679810421441824, 0.9]
partition_cabinet[0].rotation = [0, 0, 0]
bookcase[0].position = [0.39597973787498014, 1.9746773152033854, 1.0]
bookcase[0].rotation = [0, 0, 0]
carpet[0].position = [7.920855062559766, 3.8261631471822706, 0.0075]
carpet[0].rotation = [0, 0, 0]
shoe_cabinet[0].position = [8.285304359193994, 3.294309852300098, 0.55]
shoe_cabinet[0].rotation = [0, 0, 0]
refrigerator[0].position = [8.63868586880729, 3.6435633309065536, 0.925]
refrigerator[0].rotation = [0, 0, 0]
chair[0].position = [6.384810702352017, 0.8838432688976131, 0.425]
chair[0].rotation = [0, 0, 0]
dining_table[0].position = [3.2124434770502144, 2.4088682600300926, 0.375]
dining_table[0].rotation = [0, 0, 0]
ornaments[0].position = [3.9596793089086777, 2.78831368339957, 0.19]
ornaments[0].rotation = [0, 0, 0]
toy_A[0].position = [8.050243293163623, 0.7048815938132467, 0.09]
toy_A[0].rotation = [0, 0, 0]
coffee_table[0].position = [0.5184903970876509, 0.8874441623208028, 0.21]
coffee_table[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [6.343516868089224, 3.5832220161781065, 0.43]
dining_chair_A[0].rotation = [0, 0, 0]
sofa[0].position = [7.6844822060354545, 0.9543173782807247, 0.425]
sofa[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [7.03231289835169, 3.804128092109213, 0.275]
tv_cabinet[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [8.093035702238232, 1.261384099964936, 0.43]
dining_chair_B[0].rotation = [0, 0, 0]
toy_B[0].position = [7.654478094580588, 2.65100016683432, 0.15]
toy_B[0].rotation = [0, 0, 0]
partition_cabinet[0].position = [4.580936482627547, 2.679810421441824, 0.9]
partition_cabinet[0].rotation = [0, 0, 0]
bookcase[0].position = [0.39597973787498014, 1.9746773152033854, 1.0]
bookcase[0].rotation = [0, 0, 0]
carpet[0].position = [7.920855062559766, 3.8261631471822706, 0.0075]
carpet[0].rotation = [0, 0, 0]
shoe_cabinet[0].position = [8.285304359193994, 3.294309852300098, 0.55]
shoe_cabinet[0].rotation = [0, 0, 0]
refrigerator[0].position = [8.63868586880729, 3.6435633309065536, 0.925]
refrigerator[0].rotation = [0, 0, 0]
chair[0].position = [6.384810702352017, 0.8838432688976131, 0.425]
chair[0].rotation = [0, 0, 0]
dining_table[0].position = [3.2124434770502144, 2.4088682600300926, 0.375]
dining_table[0].rotation = [0, 0, 0]
ornaments[0].position = [3.9596793089086777, 2.78831368339957, 0.19]
ornaments[0].rotation = [0, 0, 0]

solver.constraints = []

# The left side is used for dining, while the larger right side forms the
# living area. The upper recess and both door approach zones remain clear.

# Dining group: the table is centered between two chairs on opposite sides.
dining_table[0].position = [2.10, 1.25, 0.375]
dining_table[0].rotation = [0, 0, radians(90)]

dining_chair_A[0].position = [1.00, 1.25, 0.43]
dining_chair_A[0].rotation = [0, 0, radians(0)]

dining_chair_B[0].position = [3.20, 1.25, 0.43]
dining_chair_B[0].rotation = [0, 0, radians(180)]

# Living group: the sofa is against the bottom wall and faces the TV.
sofa[0].position = [6.90, 0.475, 0.425]
sofa[0].rotation = [0, 0, radians(90)]

carpet[0].position = [6.90, 2.00, 0.005]
carpet[0].rotation = [0, 0, radians(0)]

coffee_table[0].position = [6.90, 1.90, 0.21]
coffee_table[0].rotation = [0, 0, radians(90)]

tv_cabinet[0].position = [6.90, 3.635, 0.275]
tv_cabinet[0].rotation = [0, 0, radians(-90)]

# The lounge chair is outside the main sofa/coffee-table circulation line and
# points toward toy_A (the specified toy o0006).
chair[0].position = [8.55, 1.65, 0.425]
chair[0].rotation = [0, 0, radians(170)]

# Small objects are supported by furniture rather than floating or sitting
# directly on the floor.
toy_A[0].position = [7.10, 1.90, 0.51]
toy_A[0].rotation = [0, 0, radians(90)]

toy_B[0].position = [6.70, 1.90, 0.57]
toy_B[0].rotation = [0, 0, radians(90)]

ornaments[0].position = [6.90, 3.635, 0.74]
ornaments[0].rotation = [0, 0, radians(-90)]

# Storage is distributed along solid wall portions, avoiding both windows and
# the floor areas immediately in front of the two doors.
refrigerator[0].position = [4.75, 3.51, 0.925]
refrigerator[0].rotation = [0, 0, radians(-90)]

bookcase[0].position = [3.33, 3.85, 1.00]
bookcase[0].rotation = [0, 0, radians(0)]

shoe_cabinet[0].position = [3.345, 2.75, 0.55]
shoe_cabinet[0].rotation = [0, 0, radians(0)]

# This cabinet separates the dining and living zones without obstructing
# either doorway or the central route through the room.
partition_cabinet[0].position = [4.13, 1.35, 0.90]
partition_cabinet[0].rotation = [0, 0, radians(0)]


# Fixed references preserve the functional zones if the solver adjusts the
# scene. Their z coordinates match the corresponding asset centers.
dining_table_anchor = AssetInstance(
    position=[2.10, 1.25, 0.375],
    rotation=[0, 0, radians(90)]
)
dining_chair_A_anchor = AssetInstance(
    position=[1.00, 1.25, 0.43],
    rotation=[0, 0, radians(0)]
)
dining_chair_B_anchor = AssetInstance(
    position=[3.20, 1.25, 0.43],
    rotation=[0, 0, radians(180)]
)
sofa_anchor = AssetInstance(
    position=[6.90, 0.475, 0.425],
    rotation=[0, 0, radians(90)]
)
carpet_anchor = AssetInstance(
    position=[6.90, 2.00, 0.005],
    rotation=[0, 0, radians(0)]
)
coffee_table_anchor = AssetInstance(
    position=[6.90, 1.90, 0.21],
    rotation=[0, 0, radians(90)]
)
tv_cabinet_anchor = AssetInstance(
    position=[6.90, 3.635, 0.275],
    rotation=[0, 0, radians(-90)]
)
chair_anchor = AssetInstance(
    position=[8.55, 1.65, 0.425]
)
toy_A_anchor = AssetInstance(
    position=[7.10, 1.90, 0.51]
)
toy_B_anchor = AssetInstance(
    position=[6.70, 1.90, 0.57]
)
ornaments_anchor = AssetInstance(
    position=[6.90, 3.635, 0.74]
)
refrigerator_anchor = AssetInstance(
    position=[4.75, 3.51, 0.925],
    rotation=[0, 0, radians(-90)]
)
bookcase_anchor = AssetInstance(
    position=[3.33, 3.85, 1.00],
    rotation=[0, 0, radians(0)]
)
shoe_cabinet_anchor = AssetInstance(
    position=[3.345, 2.75, 0.55],
    rotation=[0, 0, radians(0)]
)
partition_cabinet_anchor = AssetInstance(
    position=[4.13, 1.35, 0.90],
    rotation=[0, 0, radians(0)]
)


# High-priority semantic constraints are declared first.

# Keep the dining table equidistant between the two opposed dining chairs.
solver.distance_constraint(
    dining_table[0], dining_chair_A[0], 1.10, 1.10, weight=10
)
solver.distance_constraint(
    dining_table[0], dining_chair_B[0], 1.10, 1.10, weight=10
)
solver.point_towards(dining_chair_A[0], dining_table[0])
solver.point_towards(dining_chair_B[0], dining_table[0])
solver.align_with(dining_table[0], dining_table_anchor)

# The sofa must remain against the bottom wall and directed into the living
# area toward the television.
solver.against_wall(sofa[0], walls[6])
solver.point_towards(sofa[0], tv_cabinet[0])
solver.against_wall(tv_cabinet[0], walls[8])
solver.point_towards(tv_cabinet[0], sofa[0])

# Required chair-to-toy relationship.
solver.point_towards(chair[0], toy_A[0])

# Supported small objects.
solver.on_top_of(toy_A[0], coffee_table[0])
solver.on_top_of(toy_B[0], coffee_table[0])
solver.on_top_of(ornaments[0], tv_cabinet[0])
solver.align_with(toy_A[0], coffee_table[0])
solver.align_with(toy_B[0], coffee_table[0])
solver.align_with(ornaments[0], tv_cabinet[0])

# Wall-mounted storage constraints use solid wall sections away from openings.
solver.against_wall(refrigerator[0], walls[8])
solver.align_with(refrigerator[0], refrigerator_anchor)

solver.against_wall(bookcase[0], walls[3])
solver.align_with(bookcase[0], bookcase_anchor)

solver.against_wall(shoe_cabinet[0], walls[3])
solver.align_with(shoe_cabinet[0], shoe_cabinet_anchor)

# Position constraints retain clearance, prevent overlap, and preserve zones.
solver.distance_constraint(
    dining_table[0], dining_table_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    dining_chair_A[0], dining_chair_A_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    dining_chair_B[0], dining_chair_B_anchor, 0, 0, weight=10
)
solver.distance_constraint(sofa[0], sofa_anchor, 0, 0, weight=10)
solver.distance_constraint(carpet[0], carpet_anchor, 0, 0, weight=10)
solver.distance_constraint(
    coffee_table[0], coffee_table_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    tv_cabinet[0], tv_cabinet_anchor, 0, 0, weight=10
)
solver.distance_constraint(chair[0], chair_anchor, 0, 0, weight=10)
solver.distance_constraint(toy_A[0], toy_A_anchor, 0, 0, weight=10)
solver.distance_constraint(toy_B[0], toy_B_anchor, 0, 0, weight=10)
solver.distance_constraint(
    ornaments[0], ornaments_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    refrigerator[0], refrigerator_anchor, 0, 0, weight=10
)
solver.distance_constraint(bookcase[0], bookcase_anchor, 0, 0, weight=10)
solver.distance_constraint(
    shoe_cabinet[0], shoe_cabinet_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    partition_cabinet[0], partition_cabinet_anchor, 0, 0, weight=10
)

# Remaining orientation constraints.
solver.align_with(carpet[0], carpet_anchor)
solver.align_with(coffee_table[0], coffee_table_anchor)
solver.align_with(partition_cabinet[0], partition_cabinet_anchor)

solver.constraints = []
sofa[0].position = [6.900000095367432, 0.47466790676116943, 0.42500001192092896]
sofa[0].rotation = [0, 0, 1.570458811325211]
sofa[0].optimize = 2
carpet[0].position = [6.900000095367432, 2.0, 0.004999999888241291]
carpet[0].rotation = [0, 0, 0.00942477746072377]
carpet[0].optimize = 2
dining_chair_A[0].position = [1.0, 1.25, 0.4300000071525574]
dining_chair_A[0].rotation = [0, 0, 0.01256637125682779]
dining_chair_A[0].optimize = 2
ornaments[0].position = [6.900000095367432, 3.634999990463257, 0.7400000095367432]
ornaments[0].rotation = [0, 0, -1.5724065736574688]
ornaments[0].optimize = 2
partition_cabinet[0].position = [4.130000114440918, 1.350000023841858, 0.8999999761581421]
partition_cabinet[0].rotation = [0, 0, 0.00942477746072377]
partition_cabinet[0].optimize = 2
bookcase[0].position = [3.8626177310943604, 3.7276647090911865, 1.0]
bookcase[0].rotation = [0, 0, -1.0384661610575938]
bookcase[0].optimize = 2
shoe_cabinet[0].position = [3.347968101501465, 2.862859010696411, 0.550000011920929]
shoe_cabinet[0].rotation = [0, 0, -0.00046768844478664145]
shoe_cabinet[0].optimize = 2
refrigerator[0].position = [4.75, 3.515220880508423, 0.925000011920929]
refrigerator[0].rotation = [0, 0, -1.570545364626579]
refrigerator[0].optimize = 2
chair[0].position = [8.550000190734863, 1.649999976158142, 0.42500001192092896]
chair[0].rotation = [0, 0, 2.976484514402671]
chair[0].optimize = 2
coffee_table[0].position = [6.900000095367432, 1.899999976158142, 0.20999999344348907]
coffee_table[0].rotation = [0, 0, 1.5927874750809192]
coffee_table[0].optimize = 2
dining_chair_B[0].position = [3.200000047683716, 1.25, 0.4300000071525574]
dining_chair_B[0].rotation = [0, 0, -3.1290262823329655]
dining_chair_B[0].optimize = 2
toy_B[0].position = [6.699999809265137, 1.899999976158142, 0.5699999928474426]
toy_B[0].rotation = [0, 0, 1.5924883756714379]
toy_B[0].optimize = 2
tv_cabinet[0].position = [6.900000095367432, 3.6399383544921875, 0.2750000059604645]
tv_cabinet[0].rotation = [0, 0, -1.5710469872812713]
tv_cabinet[0].optimize = 2
dining_table[0].position = [2.100673198699951, 1.25, 0.375]
dining_table[0].rotation = [0, 0, 1.5927874750809192]
dining_table[0].optimize = 2
toy_A[0].position = [7.099999904632568, 1.899999976158142, 0.5099999904632568]
toy_A[0].rotation = [0, 0, 1.592552864505454]
toy_A[0].optimize = 2

