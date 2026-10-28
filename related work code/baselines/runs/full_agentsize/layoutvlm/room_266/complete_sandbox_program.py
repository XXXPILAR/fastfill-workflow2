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
    Wall(corner1=[1.94, 7.83, 0.00], corner2=[1.94, 4.73, 0.00]),
    Wall(corner1=[1.94, 4.73, 0.00], corner2=[1.20, 4.73, 0.00]),
    Wall(corner1=[1.20, 4.73, 0.00], corner2=[1.20, 4.97, 0.00]),
    Wall(corner1=[1.20, 4.97, 0.00], corner2=[1.70, 4.97, 0.00]),
    Wall(corner1=[1.70, 4.97, 0.00], corner2=[1.70, 6.07, 0.00]),
    Wall(corner1=[1.70, 6.07, 0.00], corner2=[0.00, 6.07, 0.00]),
    Wall(corner1=[0.00, 6.07, 0.00], corner2=[0.00, 3.55, 0.00]),
    Wall(corner1=[0.00, 3.55, 0.00], corner2=[1.94, 3.55, 0.00]),
    Wall(corner1=[1.94, 3.55, 0.00], corner2=[1.94, 0.00, 0.00]),
    Wall(corner1=[1.94, 0.00, 0.00], corner2=[5.63, 0.00, 0.00]),
    Wall(corner1=[5.63, 0.00, 0.00], corner2=[5.63, 7.83, 0.00]),
    Wall(corner1=[5.63, 7.83, 0.00], corner2=[5.23, 7.83, 0.00]),
    Wall(corner1=[5.23, 7.83, 0.00], corner2=[5.23, 8.07, 0.00]),
    Wall(corner1=[5.23, 8.07, 0.00], corner2=[5.63, 8.07, 0.00]),
    Wall(corner1=[5.63, 8.07, 0.00], corner2=[5.63, 9.77, 0.00]),
    Wall(corner1=[5.63, 9.77, 0.00], corner2=[3.93, 9.77, 0.00]),
    Wall(corner1=[3.93, 9.77, 0.00], corner2=[3.93, 7.83, 0.00]),
    Wall(corner1=[3.93, 7.83, 0.00], corner2=[1.94, 7.83, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
refrigerator = Assets(description="refrigerator", size=[0.76, 0.91, 1.78], placements=[AssetInstance() for _ in range(1)])
stool = Assets(description="stool", size=[0.42, 0.42, 0.65], placements=[AssetInstance() for _ in range(1)])
plants = Assets(description="plants", size=[0.55, 0.55, 1.35], placements=[AssetInstance() for _ in range(1)])
coffee_table_A = Assets(description="coffee table", size=[0.60, 1.20, 0.42], placements=[AssetInstance() for _ in range(1)])
dining_chair_A = Assets(description="dining chair", size=[0.55, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
dining_chair_B = Assets(description="dining chair", size=[0.55, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
dining_table = Assets(description="dining table", size=[0.90, 1.80, 0.76], placements=[AssetInstance() for _ in range(1)])
dining_chair_C = Assets(description="dining chair", size=[0.55, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
tv = Assets(description="tv", size=[0.07, 1.23, 0.71], placements=[AssetInstance() for _ in range(1)])
dining_chair_D = Assets(description="dining chair", size=[0.55, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
coffee_table_B = Assets(description="coffee table", size=[0.60, 0.60, 0.40], placements=[AssetInstance() for _ in range(1)])

refrigerator[0].instance_id = 'refrigerator_0'
stool[0].instance_id = 'stool_0'
plants[0].instance_id = 'plants_0'
coffee_table_A[0].instance_id = 'coffee_table_A_0'
dining_chair_A[0].instance_id = 'dining_chair_A_0'
dining_chair_B[0].instance_id = 'dining_chair_B_0'
dining_table[0].instance_id = 'dining_table_0'
dining_chair_C[0].instance_id = 'dining_chair_C_0'
tv[0].instance_id = 'tv_0'
dining_chair_D[0].instance_id = 'dining_chair_D_0'
coffee_table_B[0].instance_id = 'coffee_table_B_0'
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
walls[10].instance_id = 'walls_10'
walls[11].instance_id = 'walls_11'
walls[12].instance_id = 'walls_12'
walls[13].instance_id = 'walls_13'
walls[14].instance_id = 'walls_14'
walls[15].instance_id = 'walls_15'
walls[16].instance_id = 'walls_16'
walls[17].instance_id = 'walls_17'

refrigerator[0].position = [2.410572541188428, 6.894953862939933, 0.89]
refrigerator[0].rotation = [0, 0, 0]
stool[0].position = [0.7815852631159446, 5.92546543857151, 0.325]
stool[0].rotation = [0, 0, 0]
plants[0].position = [3.1964144312801532, 6.541685530458182, 0.675]
plants[0].rotation = [0, 0, 0]
coffee_table_A[0].position = [2.842194226198077, 2.1351138648074435, 0.21]
coffee_table_A[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [5.622144060402296, 4.492471732022719, 0.425]
dining_chair_A[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [5.348443317852388, 6.011325817399818, 0.425]
dining_chair_B[0].rotation = [0, 0, 0]
dining_table[0].position = [4.728065533104566, 1.2909410318538856, 0.38]
dining_table[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [5.223504134902207, 2.1787186866622252, 0.425]
dining_chair_C[0].rotation = [0, 0, 0]
tv[0].position = [4.6244455246735034, 8.05012302739826, 0.355]
tv[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [2.4967895048044837, 7.805533685337848, 0.425]
dining_chair_D[0].rotation = [0, 0, 0]
coffee_table_B[0].position = [5.564916622578802, 6.94338789266643, 0.2]
coffee_table_B[0].rotation = [0, 0, 0]
refrigerator[0].position = [2.410572541188428, 6.894953862939933, 0.89]
refrigerator[0].rotation = [0, 0, 0]
stool[0].position = [0.7815852631159446, 5.92546543857151, 0.325]
stool[0].rotation = [0, 0, 0]
plants[0].position = [3.1964144312801532, 6.541685530458182, 0.675]
plants[0].rotation = [0, 0, 0]
coffee_table_A[0].position = [2.842194226198077, 2.1351138648074435, 0.21]
coffee_table_A[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [5.622144060402296, 4.492471732022719, 0.425]
dining_chair_A[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [5.348443317852388, 6.011325817399818, 0.425]
dining_chair_B[0].rotation = [0, 0, 0]
dining_table[0].position = [4.728065533104566, 1.2909410318538856, 0.38]
dining_table[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [5.223504134902207, 2.1787186866622252, 0.425]
dining_chair_C[0].rotation = [0, 0, 0]
tv[0].position = [4.6244455246735034, 8.05012302739826, 0.355]
tv[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [2.4967895048044837, 7.805533685337848, 0.425]
dining_chair_D[0].rotation = [0, 0, 0]
coffee_table_B[0].position = [5.564916622578802, 6.94338789266643, 0.2]
coffee_table_B[0].rotation = [0, 0, 0]

solver.constraints = []

# The dining group occupies the central-lower portion of the main room.
# Chairs A and D are placed on opposite sides so that the dining table is
# geometrically between them. The south entrance and all left/top doorways
# retain clear circulation paths.

refrigerator[0].position = [5.25, 1.65, refrigerator.size[2] / 2]
refrigerator[0].rotation = [0, 0, radians(180)]

dining_table[0].position = [3.35, 3.20, dining_table.size[2] / 2]
dining_table[0].rotation = [0, 0, radians(0)]

dining_chair_A[0].position = [2.35, 3.20, dining_chair_A.size[2] / 2]
dining_chair_A[0].rotation = [0, 0, radians(0)]

dining_chair_D[0].position = [4.35, 3.20, dining_chair_D.size[2] / 2]
dining_chair_D[0].rotation = [0, 0, radians(180)]

dining_chair_B[0].position = [3.35, 1.70, dining_chair_B.size[2] / 2]
dining_chair_B[0].rotation = [0, 0, radians(90)]

dining_chair_C[0].position = [3.35, 4.70, dining_chair_C.size[2] / 2]
dining_chair_C[0].rotation = [0, 0, radians(-90)]

# The TV and coffee tables form a compact living area in the upper-right
# part of the main room, outside the approach to the doors at y=7.83.
tv[0].position = [5.595, 5.80, tv.size[2] / 2]
tv[0].rotation = [0, 0, radians(180)]

coffee_table_A[0].position = [4.55, 5.80, coffee_table_A.size[2] / 2]
coffee_table_A[0].rotation = [0, 0, radians(0)]

coffee_table_B[0].position = [3.40, 5.70, coffee_table_B.size[2] / 2]
coffee_table_B[0].rotation = [0, 0, radians(0)]

stool[0].position = [4.10, 6.85, stool.size[2] / 2]
stool[0].rotation = [0, 0, radians(-90)]

# The plant fills the upper-right corner without obstructing the wide
# doorway on the y=7.83 boundary or the doorway at the top of the niche.
plants[0].position = [5.355, 7.38, plants.size[2] / 2]
plants[0].rotation = [0, 0, radians(180)]


# Fixed points keep the functional zones in their intended positions while
# allowing a small amount of solver adjustment where appropriate.
refrigerator_anchor = AssetInstance(position=[5.25, 1.65, refrigerator.size[2] / 2])
table_anchor = AssetInstance(position=[3.35, 3.20, dining_table.size[2] / 2])
chair_A_anchor = AssetInstance(position=[2.35, 3.20, dining_chair_A.size[2] / 2])
chair_D_anchor = AssetInstance(position=[4.35, 3.20, dining_chair_D.size[2] / 2])
chair_B_anchor = AssetInstance(position=[3.35, 1.70, dining_chair_B.size[2] / 2])
chair_C_anchor = AssetInstance(position=[3.35, 4.70, dining_chair_C.size[2] / 2])
tv_anchor = AssetInstance(position=[5.595, 5.80, tv.size[2] / 2])
coffee_A_anchor = AssetInstance(position=[4.55, 5.80, coffee_table_A.size[2] / 2])
coffee_B_anchor = AssetInstance(position=[3.40, 5.70, coffee_table_B.size[2] / 2])
stool_anchor = AssetInstance(position=[4.10, 6.85, stool.size[2] / 2])
plants_anchor = AssetInstance(position=[5.355, 7.38, plants.size[2] / 2])

living_area_center = AssetInstance(position=[4.35, 5.75, 0.40])
room_center = AssetInstance(position=[3.75, 4.50, 0.70])


# Wall-mounted/adjacent assets: these wall constraints are the primary
# position semantics, followed by anchors that select an unobstructed
# location along the long east wall.
solver.against_wall(refrigerator[0], walls[10])
solver.distance_constraint(
    refrigerator[0], refrigerator_anchor, 0, 0.05, weight=10
)
solver.point_towards(refrigerator[0], room_center)

solver.against_wall(tv[0], walls[10])
solver.distance_constraint(tv[0], tv_anchor, 0, 0.05, weight=10)
solver.point_towards(tv[0], coffee_table_A[0])

solver.against_wall(plants[0], walls[10])
solver.distance_constraint(plants[0], plants_anchor, 0, 0.05, weight=10)
solver.point_towards(plants[0], room_center)


# Anchor the dining table first because it determines the dining layout.
solver.distance_constraint(dining_table[0], table_anchor, 0, 0.05, weight=10)
solver.point_towards(dining_table[0], dining_chair_D[0])

# Opposing chairs A and D establish the required table-between-chairs
# arrangement. Their one-meter center distances provide usable seat spacing.
solver.distance_constraint(
    dining_chair_A[0], chair_A_anchor, 0, 0.05, weight=10
)
solver.distance_constraint(
    dining_chair_A[0], dining_table[0], 0.95, 1.05, weight=10
)
solver.point_towards(dining_chair_A[0], dining_table[0])

solver.distance_constraint(
    dining_chair_D[0], chair_D_anchor, 0, 0.05, weight=10
)
solver.distance_constraint(
    dining_chair_D[0], dining_table[0], 0.95, 1.05, weight=10
)
solver.point_towards(dining_chair_D[0], dining_table[0])

# The other two chairs complete the four-sided dining arrangement.
solver.distance_constraint(
    dining_chair_B[0], chair_B_anchor, 0, 0.05, weight=10
)
solver.distance_constraint(
    dining_chair_B[0], dining_table[0], 1.45, 1.55, weight=10
)
solver.point_towards(dining_chair_B[0], dining_table[0])

solver.distance_constraint(
    dining_chair_C[0], chair_C_anchor, 0, 0.05, weight=10
)
solver.distance_constraint(
    dining_chair_C[0], dining_table[0], 1.45, 1.55, weight=10
)
solver.point_towards(dining_chair_C[0], dining_table[0])


# Keep both coffee tables centered in front of the TV and separated from
# each other. Pointing them toward the TV also keeps their main axes coherent.
solver.distance_constraint(
    coffee_table_A[0], coffee_A_anchor, 0, 0.05, weight=10
)
solver.distance_constraint(coffee_table_A[0], tv[0], 1.00, 1.15, weight=5)
solver.point_towards(coffee_table_A[0], tv[0])

solver.distance_constraint(
    coffee_table_B[0], coffee_B_anchor, 0, 0.05, weight=10
)
solver.distance_constraint(
    coffee_table_B[0], coffee_table_A[0], 1.10, 1.25, weight=5
)
solver.point_towards(coffee_table_B[0], tv[0])

# The stool remains near the living group but beyond the coffee-table
# footprints and away from the top doorway's direct approach.
solver.distance_constraint(stool[0], stool_anchor, 0, 0.05, weight=10)
solver.distance_constraint(stool[0], coffee_table_A[0], 1.10, 1.30, weight=5)
solver.point_towards(stool[0], living_area_center)

solver.constraints = []
stool[0].position = [4.099999904632568, 6.849999904632568, 0.32499998807907104]
stool[0].rotation = [0, 0, -1.5582299555380688]
stool[0].optimize = 2
dining_chair_A[0].position = [2.3499999046325684, 3.200000047683716, 0.42500001192092896]
dining_chair_A[0].rotation = [0, 0, 0.01256637125682779]
dining_chair_A[0].optimize = 2
dining_chair_C[0].position = [3.3499999046325684, 4.699999809265137, 0.42500001192092896]
dining_chair_C[0].rotation = [0, 0, -1.5582299555380688]
dining_chair_C[0].optimize = 2
refrigerator[0].position = [5.25, 1.649999976158142, 0.8899999856948853]
refrigerator[0].rotation = [0, 0, 3.1415901007133047]
refrigerator[0].optimize = 2
tv[0].position = [5.592135906219482, 5.800000190734863, 0.35499998927116394]
tv[0].rotation = [0, 0, -3.141590992598787]
tv[0].optimize = 2
coffee_table_A[0].position = [4.550000190734863, 5.800000190734863, 0.20999999344348907]
coffee_table_A[0].rotation = [0, 0, 0.021991148286022624]
coffee_table_A[0].optimize = 2
dining_chair_D[0].position = [4.349999904632568, 3.200000047683716, 0.42500001192092896]
dining_chair_D[0].rotation = [0, 0, -3.125884689672577]
dining_chair_D[0].optimize = 2
coffee_table_B[0].position = [3.4000000953674316, 5.699999809265137, 0.20000000298023224]
coffee_table_B[0].rotation = [0, 0, 0.01256637125682779]
coffee_table_B[0].optimize = 2
plants[0].position = [4.952315330505371, 7.9472222328186035, 0.675000011920929]
plants[0].rotation = [0, 0, 3.1415646576672063]
plants[0].optimize = 2
dining_chair_B[0].position = [3.3499999046325684, 1.7000000476837158, 0.42500001192092896]
dining_chair_B[0].rotation = [0, 0, 1.5833626980517244]
dining_chair_B[0].optimize = 2
dining_table[0].position = [3.3499999046325684, 3.200000047683716, 0.3799999952316284]
dining_table[0].rotation = [0, 0, 0.03455751882667646]
dining_table[0].optimize = 2

