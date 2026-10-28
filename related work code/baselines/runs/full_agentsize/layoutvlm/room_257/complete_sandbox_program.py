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
    Wall(corner1=[2.94, 5.79, 0.00], corner2=[1.46, 5.79, 0.00]),
    Wall(corner1=[1.46, 5.79, 0.00], corner2=[1.46, 7.47, 0.00]),
    Wall(corner1=[1.46, 7.47, 0.00], corner2=[0.00, 7.47, 0.00]),
    Wall(corner1=[0.00, 7.47, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.94, 0.00, 0.00]),
    Wall(corner1=[2.94, 0.00, 0.00], corner2=[2.94, 3.45, 0.00]),
    Wall(corner1=[2.94, 3.45, 0.00], corner2=[5.65, 3.45, 0.00]),
    Wall(corner1=[5.65, 3.45, 0.00], corner2=[5.65, 4.49, 0.00]),
    Wall(corner1=[5.65, 4.49, 0.00], corner2=[2.94, 4.49, 0.00]),
    Wall(corner1=[2.94, 4.49, 0.00], corner2=[2.94, 5.79, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
sofa = Assets(description="sofa", size=[0.95, 2.40, 0.85], placements=[AssetInstance() for _ in range(1)])
side_table = Assets(description="side table", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
ornaments_A = Assets(description="ornaments", size=[0.14, 0.18, 0.32], placements=[AssetInstance() for _ in range(1)])
ornaments_B = Assets(description="ornaments", size=[0.12, 0.15, 0.25], placements=[AssetInstance() for _ in range(1)])
ornaments_C = Assets(description="ornaments", size=[0.15, 0.20, 0.28], placements=[AssetInstance() for _ in range(1)])
tv_cabinet = Assets(description="tv cabinet", size=[0.45, 1.80, 0.55], placements=[AssetInstance() for _ in range(1)])
sideboard = Assets(description="sideboard", size=[0.45, 1.60, 0.80], placements=[AssetInstance() for _ in range(1)])
flowers_A = Assets(description="flowers", size=[0.30, 0.30, 0.50], placements=[AssetInstance() for _ in range(1)])
flowers_B = Assets(description="flowers", size=[0.25, 0.25, 0.40], placements=[AssetInstance() for _ in range(1)])
flowers_C = Assets(description="flowers", size=[0.30, 0.30, 0.45], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[2.00, 3.00, 0.02], placements=[AssetInstance() for _ in range(1)])
stool = Assets(description="stool", size=[0.45, 0.45, 0.48], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="coffee table", size=[0.65, 1.20, 0.42], placements=[AssetInstance() for _ in range(1)])
floor_standing_lamp = Assets(description="floor standing lamp", size=[0.40, 0.40, 1.65], placements=[AssetInstance() for _ in range(1)])
ornaments_D = Assets(description="ornaments", size=[0.12, 0.16, 0.30], placements=[AssetInstance() for _ in range(1)])
dining_table = Assets(description="dining table", size=[0.90, 1.80, 0.75], placements=[AssetInstance() for _ in range(1)])

sofa[0].instance_id = 'sofa_0'
side_table[0].instance_id = 'side_table_0'
ornaments_A[0].instance_id = 'ornaments_A_0'
ornaments_B[0].instance_id = 'ornaments_B_0'
ornaments_C[0].instance_id = 'ornaments_C_0'
tv_cabinet[0].instance_id = 'tv_cabinet_0'
sideboard[0].instance_id = 'sideboard_0'
flowers_A[0].instance_id = 'flowers_A_0'
flowers_B[0].instance_id = 'flowers_B_0'
flowers_C[0].instance_id = 'flowers_C_0'
carpet[0].instance_id = 'carpet_0'
stool[0].instance_id = 'stool_0'
coffee_table[0].instance_id = 'coffee_table_0'
floor_standing_lamp[0].instance_id = 'floor_standing_lamp_0'
ornaments_D[0].instance_id = 'ornaments_D_0'
dining_table[0].instance_id = 'dining_table_0'
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

sofa[0].position = [1.7202656572342403, 4.484453729844255, 0.425]
sofa[0].rotation = [0, 0, 0]
side_table[0].position = [4.7108101352573035, 3.710635981768176, 0.275]
side_table[0].rotation = [0, 0, 0]
ornaments_A[0].position = [1.3419463979597868, 0.27205991192590506, 0.16]
ornaments_A[0].rotation = [0, 0, 0]
ornaments_B[0].position = [1.6272935753104099, 2.0237536502841875, 0.125]
ornaments_B[0].rotation = [0, 0, 0]
ornaments_C[0].position = [1.3382951800964211, 2.8892784807267007, 0.14]
ornaments_C[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [1.8360074135579365, 4.255144035400145, 0.275]
tv_cabinet[0].rotation = [0, 0, 0]
sideboard[0].position = [1.3731982386635533, 0.8964820650565327, 0.4]
sideboard[0].rotation = [0, 0, 0]
flowers_A[0].position = [1.2896242514509069, 1.8204577959687724, 0.25]
flowers_A[0].rotation = [0, 0, 0]
flowers_B[0].position = [0.208459245246998, 4.223419550647846, 0.2]
flowers_B[0].rotation = [0, 0, 0]
flowers_C[0].position = [0.12001301650387526, 4.644778492758277, 0.225]
flowers_C[0].rotation = [0, 0, 0]
carpet[0].position = [1.5156150896596627, 5.335316623073422, 0.01]
carpet[0].rotation = [0, 0, 0]
stool[0].position = [1.3295057244740434, 0.8033048837609978, 0.24]
stool[0].rotation = [0, 0, 0]
coffee_table[0].position = [0.3150183431319087, 2.6350838843717836, 0.21]
coffee_table[0].rotation = [0, 0, 0]
floor_standing_lamp[0].position = [0.71459061546091, 0.2187134117302752, 0.825]
floor_standing_lamp[0].rotation = [0, 0, 0]
ornaments_D[0].position = [0.5452074888105803, 6.484875931635415, 0.15]
ornaments_D[0].rotation = [0, 0, 0]
dining_table[0].position = [0.5672936006828335, 3.9526648414255967, 0.375]
dining_table[0].rotation = [0, 0, 0]
sofa[0].position = [1.7202656572342403, 4.484453729844255, 0.425]
sofa[0].rotation = [0, 0, 0]
side_table[0].position = [4.7108101352573035, 3.710635981768176, 0.275]
side_table[0].rotation = [0, 0, 0]
ornaments_A[0].position = [1.3419463979597868, 0.27205991192590506, 0.16]
ornaments_A[0].rotation = [0, 0, 0]
ornaments_B[0].position = [1.6272935753104099, 2.0237536502841875, 0.125]
ornaments_B[0].rotation = [0, 0, 0]
ornaments_C[0].position = [1.3382951800964211, 2.8892784807267007, 0.14]
ornaments_C[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [1.8360074135579365, 4.255144035400145, 0.275]
tv_cabinet[0].rotation = [0, 0, 0]
sideboard[0].position = [1.3731982386635533, 0.8964820650565327, 0.4]
sideboard[0].rotation = [0, 0, 0]
flowers_A[0].position = [1.2896242514509069, 1.8204577959687724, 0.25]
flowers_A[0].rotation = [0, 0, 0]
flowers_B[0].position = [0.208459245246998, 4.223419550647846, 0.2]
flowers_B[0].rotation = [0, 0, 0]
flowers_C[0].position = [0.12001301650387526, 4.644778492758277, 0.225]
flowers_C[0].rotation = [0, 0, 0]
carpet[0].position = [1.5156150896596627, 5.335316623073422, 0.01]
carpet[0].rotation = [0, 0, 0]
stool[0].position = [1.3295057244740434, 0.8033048837609978, 0.24]
stool[0].rotation = [0, 0, 0]
coffee_table[0].position = [0.3150183431319087, 2.6350838843717836, 0.21]
coffee_table[0].rotation = [0, 0, 0]
floor_standing_lamp[0].position = [0.71459061546091, 0.2187134117302752, 0.825]
floor_standing_lamp[0].rotation = [0, 0, 0]
ornaments_D[0].position = [0.5452074888105803, 6.484875931635415, 0.15]
ornaments_D[0].rotation = [0, 0, 0]
dining_table[0].position = [0.5672936006828335, 3.9526648414255967, 0.375]
dining_table[0].rotation = [0, 0, 0]

solver.constraints = []

# The living area occupies the lower part of the main room.  The eastward
# projection and the upper alcove are intentionally left clear because they
# contain several closely spaced doors.
sofa[0].position = [0.475, 2.55, 0.425]
sofa[0].rotation = [0, 0, radians(0)]

coffee_table[0].position = [1.55, 2.55, 0.23]
coffee_table[0].rotation = [0, 0, radians(180)]

carpet[0].position = [1.50, 2.55, 0.01]
carpet[0].rotation = [0, 0, radians(0)]

tv_cabinet[0].position = [2.715, 2.55, 0.275]
tv_cabinet[0].rotation = [0, 0, radians(180)]

# The side table and lamp sit beside opposite ends of the sofa without
# obstructing the circulation route from the wide south door.
side_table[0].position = [0.75, 4.05, 0.275]
side_table[0].rotation = [0, 0, radians(0)]

floor_standing_lamp[0].position = [0.25, 1.10, 0.825]
floor_standing_lamp[0].rotation = [0, 0, radians(0)]

# The stool provides movable seating at the open northeast corner of the
# living group while remaining out of the east projection.
stool[0].position = [2.45, 4.15, 0.24]
stool[0].rotation = [0, 0, radians(225)]

# The sideboard uses the uninterrupted west wall.  The dining table is
# rotated so its long dimension runs across the room, leaving the upper
# doorways and their approaches clear.
sideboard[0].position = [0.225, 4.90, 0.40]
sideboard[0].rotation = [0, 0, radians(0)]

dining_table[0].position = [1.75, 5.15, 0.375]
dining_table[0].rotation = [0, 0, radians(90)]

# Decorative objects are distributed over the available supporting surfaces.
ornaments_A[0].position = [2.60, 1.95, 0.71]
ornaments_A[0].rotation = [0, 0, radians(180)]

ornaments_B[0].position = [2.60, 2.55, 0.675]
ornaments_B[0].rotation = [0, 0, radians(180)]

ornaments_C[0].position = [2.60, 3.15, 0.69]
ornaments_C[0].rotation = [0, 0, radians(180)]

ornaments_D[0].position = [0.75, 4.05, 0.70]
ornaments_D[0].rotation = [0, 0, radians(0)]

flowers_A[0].position = [1.20, 5.15, 1.00]
flowers_A[0].rotation = [0, 0, radians(90)]

flowers_B[0].position = [1.75, 5.15, 0.95]
flowers_B[0].rotation = [0, 0, radians(90)]

flowers_C[0].position = [2.30, 5.15, 0.975]
flowers_C[0].rotation = [0, 0, radians(90)]


# Required high-priority layout relationships.
solver.point_towards(sofa[0], coffee_table[0])
solver.against_wall(sideboard[0], walls[3])

# The center spacing of 1.45 m places the lamp 0.05 m from the sofa's end:
# sofa half-width 1.20 m + lamp half-width 0.20 m + 0.05 m clearance.
solver.distance_constraint(
    floor_standing_lamp[0], sofa[0], 1.40, 1.50, weight=10
)

# Anchor the two main wall-facing pieces to the uninterrupted west/east walls.
solver.against_wall(sofa[0], walls[3])
solver.against_wall(tv_cabinet[0], walls[5])
solver.point_towards(tv_cabinet[0], sofa[0])
solver.align_with(sideboard[0], sofa[0])

# Keep the coffee table centered in front of the sofa and facing back toward it.
solver.distance_constraint(
    coffee_table[0], sofa[0], 1.075, 1.075, weight=10
)
solver.point_towards(coffee_table[0], sofa[0])

# Keep the rug centered beneath the living group. The coffee table rests on
# the rug, while the rug's rotation follows the sofa.
solver.distance_constraint(
    carpet[0], AssetInstance(position=[1.50, 2.55, 0.01]),
    0, 0, weight=10
)
solver.align_with(carpet[0], sofa[0])
solver.on_top_of(coffee_table[0], carpet[0])

# Place the side table beside the sofa's north end.
solver.distance_constraint(
    side_table[0], sofa[0], 1.53, 1.53, weight=10
)
solver.align_with(side_table[0], sofa[0])

# The lamp has little directional significance, but aligning it with the sofa
# gives it the required stable orientation constraint.
solver.align_with(floor_standing_lamp[0], sofa[0])

# Keep the stool near and oriented toward the conversation area.
solver.distance_constraint(
    stool[0], coffee_table[0], 1.80, 1.90, weight=5
)
solver.point_towards(stool[0], coffee_table[0])

# Preserve the dining table's position below the upper door approaches and
# orient it perpendicular to the sideboard.
solver.distance_constraint(
    dining_table[0], AssetInstance(position=[1.75, 5.15, 0.375]),
    0, 0, weight=10
)
solver.align_with(dining_table[0], sideboard[0], angle=90)

# TV-cabinet ornaments: each has a supporting-surface constraint, a
# position constraint, and an orientation constraint.
solver.on_top_of(ornaments_A[0], tv_cabinet[0])
solver.distance_constraint(
    ornaments_A[0], AssetInstance(position=[2.60, 1.95, 0.71]),
    0, 0, weight=10
)
solver.align_with(ornaments_A[0], tv_cabinet[0])

solver.on_top_of(ornaments_B[0], tv_cabinet[0])
solver.distance_constraint(
    ornaments_B[0], AssetInstance(position=[2.60, 2.55, 0.675]),
    0, 0, weight=10
)
solver.align_with(ornaments_B[0], tv_cabinet[0])

solver.on_top_of(ornaments_C[0], tv_cabinet[0])
solver.distance_constraint(
    ornaments_C[0], AssetInstance(position=[2.60, 3.15, 0.69]),
    0, 0, weight=10
)
solver.align_with(ornaments_C[0], tv_cabinet[0])

# The fourth ornament is centered on the side table.
solver.on_top_of(ornaments_D[0], side_table[0])
solver.distance_constraint(
    ornaments_D[0], side_table[0], 0.425, 0.425, weight=10
)
solver.align_with(ornaments_D[0], side_table[0])

# The three flower arrangements form a spaced row along the dining table.
solver.on_top_of(flowers_A[0], dining_table[0])
solver.distance_constraint(
    flowers_A[0], AssetInstance(position=[1.20, 5.15, 1.00]),
    0, 0, weight=10
)
solver.align_with(flowers_A[0], dining_table[0])

solver.on_top_of(flowers_B[0], dining_table[0])
solver.distance_constraint(
    flowers_B[0], AssetInstance(position=[1.75, 5.15, 0.95]),
    0, 0, weight=10
)
solver.align_with(flowers_B[0], dining_table[0])

solver.on_top_of(flowers_C[0], dining_table[0])
solver.distance_constraint(
    flowers_C[0], AssetInstance(position=[2.30, 5.15, 0.975]),
    0, 0, weight=10
)
solver.align_with(flowers_C[0], dining_table[0])

solver.constraints = []
sofa[0].position = [0.4837576448917389, 2.549999952316284, 0.42500001192092896]
sofa[0].rotation = [0, 0, 0.008485305088931586]
sofa[0].optimize = 2
ornaments_C[0].position = [2.5999999046325684, 3.1500000953674316, 0.6899999976158142]
ornaments_C[0].rotation = [0, 0, -3.132564432340134]
ornaments_C[0].optimize = 2
tv_cabinet[0].position = [2.7205710411071777, 2.498093366622925, 0.2750000059604645]
tv_cabinet[0].rotation = [0, 0, -3.1381478346977096]
tv_cabinet[0].optimize = 2
dining_table[0].position = [1.75, 5.150000095367432, 0.375]
dining_table[0].rotation = [0, 0, 1.575421492302902]
dining_table[0].optimize = 2
carpet[0].position = [1.5, 2.549999952316284, 0.009999999776482582]
carpet[0].rotation = [0, 0, -0.012438531317762474]
carpet[0].optimize = 2
stool[0].position = [2.4748804569244385, 4.174879550933838, 0.23999999463558197]
stool[0].rotation = [0, 0, -2.3467697250267454]
stool[0].optimize = 2
flowers_C[0].position = [2.299999952316284, 5.150000095367432, 0.9750000238418579]
flowers_C[0].rotation = [0, 0, 1.577784519432973]
flowers_C[0].optimize = 2
ornaments_D[0].position = [0.5552179217338562, 3.855262041091919, 0.7000000476837158]
ornaments_D[0].rotation = [0, 0, -0.0452157895059769]
ornaments_D[0].optimize = 2
flowers_A[0].position = [1.2000000476837158, 5.150000095367432, 1.0]
flowers_A[0].rotation = [0, 0, 1.577784519432973]
flowers_A[0].optimize = 2
ornaments_A[0].position = [2.5999999046325684, 1.9500000476837158, 0.7100000381469727]
ornaments_A[0].rotation = [0, 0, -3.132564432340134]
ornaments_A[0].optimize = 2
floor_standing_lamp[0].position = [0.25, 1.100000023841858, 0.824999988079071]
floor_standing_lamp[0].rotation = [0, 0, -0.013860132765154532]
floor_standing_lamp[0].optimize = 2
sideboard[0].position = [0.22715584933757782, 4.900000095367432, 0.4000000059604645]
sideboard[0].rotation = [0, 0, 0.001030243248118589]
sideboard[0].optimize = 2
coffee_table[0].position = [1.6381906270980835, 2.549999952316284, 0.22999998927116394]
coffee_table[0].rotation = [0, 0, -3.1196015053037707]
coffee_table[0].optimize = 2
side_table[0].position = [0.7550975680351257, 4.057497978210449, 0.2750000059604645]
side_table[0].rotation = [0, 0, -0.008755149878910733]
side_table[0].optimize = 2
ornaments_B[0].position = [2.5999999046325684, 2.549999952316284, 0.675000011920929]
ornaments_B[0].rotation = [0, 0, -3.132564432340134]
ornaments_B[0].optimize = 2
flowers_B[0].position = [1.75, 5.150000095367432, 0.949999988079071]
flowers_B[0].rotation = [0, 0, 1.577784519432973]
flowers_B[0].optimize = 2

