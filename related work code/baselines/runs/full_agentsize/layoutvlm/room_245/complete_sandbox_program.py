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
    Wall(corner1=[5.94, 7.08, 0.00], corner2=[4.71, 7.08, 0.00]),
    Wall(corner1=[4.71, 7.08, 0.00], corner2=[4.71, 5.52, 0.00]),
    Wall(corner1=[4.71, 5.52, 0.00], corner2=[2.84, 5.52, 0.00]),
    Wall(corner1=[2.84, 5.52, 0.00], corner2=[2.84, 9.18, 0.00]),
    Wall(corner1=[2.84, 9.18, 0.00], corner2=[0.00, 9.18, 0.00]),
    Wall(corner1=[0.00, 9.18, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.94, 0.00, 0.00]),
    Wall(corner1=[3.94, 0.00, 0.00], corner2=[3.94, 4.37, 0.00]),
    Wall(corner1=[3.94, 4.37, 0.00], corner2=[5.94, 4.37, 0.00]),
    Wall(corner1=[5.94, 4.37, 0.00], corner2=[5.94, 7.08, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
coffee_table = Assets(description="coffee table", size=[0.60, 1.20, 0.42], placements=[AssetInstance() for _ in range(1)])
wine_cabinet_A = Assets(description="wine cabinet", size=[0.40, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
tv_cabinet = Assets(description="tv cabinet", size=[0.45, 2.00, 0.55], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[1.70, 2.40, 0.02], placements=[AssetInstance() for _ in range(1)])
combination_sofa = Assets(description="combination sofa", size=[2.20, 3.20, 0.85], placements=[AssetInstance() for _ in range(1)])
dining_table_combination = Assets(description="dining table combination", size=[2.20, 2.80, 0.78], placements=[AssetInstance() for _ in range(1)])
wine_cabinet_B = Assets(description="wine cabinet", size=[0.40, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])

coffee_table[0].instance_id = 'coffee_table_0'
wine_cabinet_A[0].instance_id = 'wine_cabinet_A_0'
tv_cabinet[0].instance_id = 'tv_cabinet_0'
carpet[0].instance_id = 'carpet_0'
combination_sofa[0].instance_id = 'combination_sofa_0'
dining_table_combination[0].instance_id = 'dining_table_combination_0'
wine_cabinet_B[0].instance_id = 'wine_cabinet_B_0'
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

coffee_table[0].position = [5.212745347009326, 4.441394373788266, 0.21]
coffee_table[0].rotation = [0, 0, 0]
wine_cabinet_A[0].position = [0.7058876358503338, 6.596802376880725, 0.9]
wine_cabinet_A[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [0.7700020027687973, 1.4241464223545142, 0.275]
tv_cabinet[0].rotation = [0, 0, 0]
carpet[0].position = [0.9626439428087846, 7.428265532757857, 0.01]
carpet[0].rotation = [0, 0, 0]
combination_sofa[0].position = [4.721676979707933, 5.906963215291681, 0.425]
combination_sofa[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [2.8773695906078807, 4.985788459448748, 0.39]
dining_table_combination[0].rotation = [0, 0, 0]
wine_cabinet_B[0].position = [2.0865648891629887, 0.33983053064458585, 0.9]
wine_cabinet_B[0].rotation = [0, 0, 0]
coffee_table[0].position = [5.212745347009326, 4.441394373788266, 0.21]
coffee_table[0].rotation = [0, 0, 0]
wine_cabinet_A[0].position = [0.7058876358503338, 6.596802376880725, 0.9]
wine_cabinet_A[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [0.7700020027687973, 1.4241464223545142, 0.275]
tv_cabinet[0].rotation = [0, 0, 0]
carpet[0].position = [0.9626439428087846, 7.428265532757857, 0.01]
carpet[0].rotation = [0, 0, 0]
combination_sofa[0].position = [4.721676979707933, 5.906963215291681, 0.425]
combination_sofa[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [2.8773695906078807, 4.985788459448748, 0.39]
dining_table_combination[0].rotation = [0, 0, 0]
wine_cabinet_B[0].position = [2.0865648891629887, 0.33983053064458585, 0.9]
wine_cabinet_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Establish explicit target centers so the major furniture remains in its
# intended zone even if the solver adjusts the layout for physical feasibility.
coffee_table_target = AssetInstance(position=[1.20, 2.70, 0.23])
wine_cabinet_A_target = AssetInstance(position=[3.74, 0.55, 0.90])
tv_cabinet_target = AssetInstance(position=[0.225, 2.70, 0.275])
carpet_target = AssetInstance(position=[1.30, 2.70, 0.01])
combination_sofa_target = AssetInstance(position=[2.84, 2.70, 0.425])
dining_table_target = AssetInstance(position=[1.42, 6.66, 0.39])
wine_cabinet_B_target = AssetInstance(position=[3.35, 5.32, 0.90])

# Directional reference points used to preserve intentional orientations.
north_of_dining_table = AssetInstance(position=[1.42, 8.50, 0.39])
inside_from_wine_cabinet_A = AssetInstance(position=[3.00, 0.55, 0.90])
inside_from_wine_cabinet_B = AssetInstance(position=[3.35, 4.50, 0.90])

# The living area occupies the lower part of the room. The sofa is backed
# against the right wall and faces the TV on the opposite wall.
combination_sofa[0].position = [2.84, 2.70, 0.425]
combination_sofa[0].rotation = [0, 0, radians(180)]

tv_cabinet[0].position = [0.225, 2.70, 0.275]
tv_cabinet[0].rotation = [0, 0, radians(0)]

# The rug and coffee table are centered between the TV and sofa. The rug runs
# slightly beneath the front of the sofa, as is typical in a living room.
carpet[0].position = [1.30, 2.70, 0.01]
carpet[0].rotation = [0, 0, radians(180)]

coffee_table[0].position = [1.20, 2.70, 0.23]
coffee_table[0].rotation = [0, 0, radians(180)]

# The dining set uses the upper-left room. Its long footprint runs east-west,
# leaving clearance in front of the wide door on the upper wall.
dining_table_combination[0].position = [1.42, 6.66, 0.39]
dining_table_combination[0].rotation = [0, 0, radians(90)]

# One wine cabinet uses the short lower-right wall area outside the bottom-door
# travel path. The other sits against the recessed wall, next to the dining zone.
wine_cabinet_A[0].position = [3.74, 0.55, 0.90]
wine_cabinet_A[0].rotation = [0, 0, radians(180)]

wine_cabinet_B[0].position = [3.35, 5.32, 0.90]
wine_cabinet_B[0].rotation = [0, 0, radians(-90)]

# High-priority position constraints preserve the planned non-overlapping zones.
solver.distance_constraint(
    combination_sofa[0], combination_sofa_target, 0, 0, weight=10
)
solver.distance_constraint(
    tv_cabinet[0], tv_cabinet_target, 0, 0, weight=10
)
solver.distance_constraint(
    carpet[0], carpet_target, 0, 0, weight=10
)
solver.distance_constraint(
    coffee_table[0], coffee_table_target, 0, 0, weight=10
)
solver.distance_constraint(
    dining_table_combination[0], dining_table_target, 0, 0, weight=10
)
solver.distance_constraint(
    wine_cabinet_A[0], wine_cabinet_A_target, 0, 0, weight=10
)
solver.distance_constraint(
    wine_cabinet_B[0], wine_cabinet_B_target, 0, 0, weight=10
)

# Primary orientation requirements for every new asset.
solver.point_towards(combination_sofa[0], tv_cabinet[0])
solver.point_towards(tv_cabinet[0], combination_sofa[0])
solver.align_with(carpet[0], combination_sofa[0])
solver.align_with(coffee_table[0], combination_sofa[0])
solver.point_towards(dining_table_combination[0], north_of_dining_table)
solver.point_towards(wine_cabinet_A[0], inside_from_wine_cabinet_A)
solver.point_towards(wine_cabinet_B[0], inside_from_wine_cabinet_B)

# Keep the wall furniture flush with its corresponding boundary segment.
solver.against_wall(combination_sofa[0], walls[7])
solver.against_wall(tv_cabinet[0], walls[5])
solver.against_wall(wine_cabinet_A[0], walls[7])
solver.against_wall(wine_cabinet_B[0], walls[2])

# The coffee table stands on the rug rather than intersecting the floor through it.
solver.on_top_of(coffee_table[0], carpet[0])

# Secondary relational constraints retain comfortable living-room spacing if
# the exact targets need minor adjustment.
solver.distance_constraint(
    coffee_table[0], combination_sofa[0], 1.55, 1.75, weight=1
)
solver.distance_constraint(
    coffee_table[0], tv_cabinet[0], 0.85, 1.15, weight=1
)
solver.distance_constraint(
    combination_sofa[0], tv_cabinet[0], 2.50, 2.80, weight=1
)
solver.distance_constraint(
    carpet[0], coffee_table[0], 0.0, 0.20, weight=1
)

solver.constraints = []
wine_cabinet_A[0].position = [3.740999937057495, 0.550000011920929, 0.8999999761581421]
wine_cabinet_A[0].rotation = [0, 0, -3.141592623362455]
wine_cabinet_A[0].optimize = 2
carpet[0].position = [1.2999999523162842, 2.700000047683716, 0.009999999776482582]
carpet[0].rotation = [0, 0, -3.1415925702376404]
carpet[0].optimize = 2
coffee_table[0].position = [1.2000000476837158, 2.700000047683716, 0.22999998927116394]
coffee_table[0].rotation = [0, 0, -3.141592535694296]
coffee_table[0].optimize = 2
wine_cabinet_B[0].position = [3.3499999046325684, 5.321999549865723, 0.8999999761581421]
wine_cabinet_B[0].rotation = [0, 0, -1.570796273692925]
wine_cabinet_B[0].optimize = 2
tv_cabinet[0].position = [0.22500000894069672, 2.700000047683716, 0.2750000059604645]
tv_cabinet[0].rotation = [0, 0, 1.6290189493918057e-08]
tv_cabinet[0].optimize = 2
combination_sofa[0].position = [2.7962067127227783, 2.700000047683716, 0.42500001192092896]
combination_sofa[0].rotation = [0, 0, -3.1415926016781026]
combination_sofa[0].optimize = 2
dining_table_combination[0].position = [1.4199999570846558, 6.659999847412109, 0.38999998569488525]
dining_table_combination[0].rotation = [0, 0, 1.5802211042556205]
dining_table_combination[0].optimize = 2

