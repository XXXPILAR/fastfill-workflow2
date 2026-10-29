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
    Wall(corner1=[10.99, 2.94, 0.00], corner2=[10.99, 4.02, 0.00]),
    Wall(corner1=[10.99, 4.02, 0.00], corner2=[6.76, 4.02, 0.00]),
    Wall(corner1=[6.76, 4.02, 0.00], corner2=[6.76, 6.86, 0.00]),
    Wall(corner1=[6.76, 6.86, 0.00], corner2=[2.80, 6.86, 0.00]),
    Wall(corner1=[2.80, 6.86, 0.00], corner2=[2.80, 3.06, 0.00]),
    Wall(corner1=[2.80, 3.06, 0.00], corner2=[0.00, 3.06, 0.00]),
    Wall(corner1=[0.00, 3.06, 0.00], corner2=[0.00, 1.29, 0.00]),
    Wall(corner1=[0.00, 1.29, 0.00], corner2=[2.80, 1.29, 0.00]),
    Wall(corner1=[2.80, 1.29, 0.00], corner2=[2.80, 0.00, 0.00]),
    Wall(corner1=[2.80, 0.00, 0.00], corner2=[6.16, 0.00, 0.00]),
    Wall(corner1=[6.16, 0.00, 0.00], corner2=[6.16, 2.94, 0.00]),
    Wall(corner1=[6.16, 2.94, 0.00], corner2=[10.99, 2.94, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
chair = Assets(description="chair", size=[0.85, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
side_table = Assets(description="side table", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
air_conditioner = Assets(description="air conditioner", size=[0.24, 1.00, 0.32], placements=[AssetInstance() for _ in range(1)])
refrigerator = Assets(description="refrigerator", size=[0.75, 0.75, 1.85], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[2.40, 3.00, 0.02], placements=[AssetInstance() for _ in range(1)])
flowers = Assets(description="flowers", size=[0.35, 0.35, 0.50], placements=[AssetInstance() for _ in range(1)])
dining_table_combination = Assets(description="dining table combination", size=[2.20, 2.80, 0.95], placements=[AssetInstance() for _ in range(1)])
floor_standing_lamp = Assets(description="floor standing lamp", size=[0.45, 0.45, 1.65], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="coffee table", size=[0.70, 1.30, 0.42], placements=[AssetInstance() for _ in range(1)])
tv_cabinet = Assets(description="tv cabinet", size=[0.45, 2.20, 0.50], placements=[AssetInstance() for _ in range(1)])
sofa = Assets(description="sofa", size=[1.00, 2.80, 0.85], placements=[AssetInstance() for _ in range(1)])

chair[0].instance_id = 'chair_0'
side_table[0].instance_id = 'side_table_0'
air_conditioner[0].instance_id = 'air_conditioner_0'
refrigerator[0].instance_id = 'refrigerator_0'
carpet[0].instance_id = 'carpet_0'
flowers[0].instance_id = 'flowers_0'
dining_table_combination[0].instance_id = 'dining_table_combination_0'
floor_standing_lamp[0].instance_id = 'floor_standing_lamp_0'
coffee_table[0].instance_id = 'coffee_table_0'
tv_cabinet[0].instance_id = 'tv_cabinet_0'
sofa[0].instance_id = 'sofa_0'
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

chair[0].position = [0.8037302383906993, 2.913111663514004, 0.45]
chair[0].rotation = [0, 0, 0]
side_table[0].position = [2.5985606375619703, 1.8495645239979739, 0.275]
side_table[0].rotation = [0, 0, 0]
air_conditioner[0].position = [1.6410857737481026, 2.2533643582800154, 0.16]
air_conditioner[0].rotation = [0, 0, 0]
refrigerator[0].position = [7.706599547835112, 3.8101087951094286, 0.925]
refrigerator[0].rotation = [0, 0, 0]
carpet[0].position = [4.6024717310290795, 3.835006070664938, 0.01]
carpet[0].rotation = [0, 0, 0]
flowers[0].position = [4.549939659602967, 4.36670440526389, 0.25]
flowers[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [3.013774907819621, 2.5194980829887594, 0.475]
dining_table_combination[0].rotation = [0, 0, 0]
floor_standing_lamp[0].position = [8.187574839683908, 3.9602076196051352, 0.825]
floor_standing_lamp[0].rotation = [0, 0, 0]
coffee_table[0].position = [2.8678344133409475, 5.819959912998003, 0.21]
coffee_table[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [4.728327707695398, 0.5598644881073026, 0.25]
tv_cabinet[0].rotation = [0, 0, 0]
sofa[0].position = [4.660061320926242, 2.283609493051739, 0.425]
sofa[0].rotation = [0, 0, 0]
chair[0].position = [0.8037302383906993, 2.913111663514004, 0.45]
chair[0].rotation = [0, 0, 0]
side_table[0].position = [2.5985606375619703, 1.8495645239979739, 0.275]
side_table[0].rotation = [0, 0, 0]
air_conditioner[0].position = [1.6410857737481026, 2.2533643582800154, 0.16]
air_conditioner[0].rotation = [0, 0, 0]
refrigerator[0].position = [7.706599547835112, 3.8101087951094286, 0.925]
refrigerator[0].rotation = [0, 0, 0]
carpet[0].position = [4.6024717310290795, 3.835006070664938, 0.01]
carpet[0].rotation = [0, 0, 0]
flowers[0].position = [4.549939659602967, 4.36670440526389, 0.25]
flowers[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [3.013774907819621, 2.5194980829887594, 0.475]
dining_table_combination[0].rotation = [0, 0, 0]
floor_standing_lamp[0].position = [8.187574839683908, 3.9602076196051352, 0.825]
floor_standing_lamp[0].rotation = [0, 0, 0]
coffee_table[0].position = [2.8678344133409475, 5.819959912998003, 0.21]
coffee_table[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [4.728327707695398, 0.5598644881073026, 0.25]
tv_cabinet[0].rotation = [0, 0, 0]
sofa[0].position = [4.660061320926242, 2.283609493051739, 0.425]
sofa[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the upper bay for dining, the lower bay for the sitting/TV group,
# and the shallow western alcove for a reading chair. The eastern passage
# remains completely unfurnished so all four passage doors remain usable.

# Lower sitting area: the sofa faces west toward the TV cabinet.
sofa[0].position = [5.66, 1.55, 0.425]
sofa[0].rotation = [0, 0, radians(180)]

tv_cabinet[0].position = [3.025, 1.60, 0.25]
tv_cabinet[0].rotation = [0, 0, 0]

coffee_table[0].position = [4.50, 1.85, 0.21]
coffee_table[0].rotation = [0, 0, 0]

# The rug lies beneath the furniture, not through its solid volumes.
carpet[0].position = [4.65, 1.60, 0.01]
carpet[0].rotation = [0, 0, 0]

# Leave approximately one metre between the bottom entrance and the
# coffee table; the route onward runs along the table's western side.
solver.against_wall(sofa[0], walls[10])
solver.point_towards(sofa[0], tv_cabinet[0])
solver.distance_constraint(
    sofa[0], AssetInstance(position=[5.66, 1.55, 0.425]), 0, 0, weight=10
)

# The cabinet is freestanding: the left boundary steps outward at y=1.29.
solver.distance_constraint(
    tv_cabinet[0], AssetInstance(position=[3.025, 1.60, 0.25]), 0, 0, weight=10
)
solver.point_towards(tv_cabinet[0], sofa[0])

solver.distance_constraint(
    coffee_table[0], AssetInstance(position=[4.50, 1.85, 0.21]), 0, 0, weight=10
)
solver.align_with(coffee_table[0], tv_cabinet[0])
solver.distance_constraint(coffee_table[0], sofa[0], 1.10, 1.35)

solver.distance_constraint(
    carpet[0], AssetInstance(position=[4.65, 1.60, 0.01]), 0, 0, weight=10
)
solver.align_with(carpet[0], tv_cabinet[0])

# Dining set includes its chairs. Its footprint stops at y=6.05,
# leaving an unobstructed landing inside the wide northern doorway.
# A generous aisle passes to its east.
dining_table_combination[0].position = [4.45, 4.65, 0.475]
dining_table_combination[0].rotation = [0, 0, 0]
solver.distance_constraint(
    dining_table_combination[0],
    AssetInstance(position=[4.45, 4.65, 0.475]),
    0, 0, weight=10
)
solver.align_with(dining_table_combination[0], tv_cabinet[0])

# Refrigerator opens west into the dining-side aisle, away from the
# eastern corridor junction.
refrigerator[0].position = [6.385, 4.65, 0.925]
refrigerator[0].rotation = [0, 0, radians(180)]
solver.against_wall(refrigerator[0], walls[2])
solver.distance_constraint(
    refrigerator[0],
    AssetInstance(position=[6.385, 4.65, 0.925]),
    0, 0, weight=10
)
solver.align_with(refrigerator[0], sofa[0])

# Reading nook occupies only the southern edge of the western alcove.
# Its northern strip stays open between the west and north alcove doors.
chair[0].position = [1.05, 1.74, 0.45]
chair[0].rotation = [0, 0, 0]
side_table[0].position = [1.85, 1.57, 0.275]
side_table[0].rotation = [0, 0, 0]

solver.distance_constraint(
    chair[0], AssetInstance(position=[1.05, 1.74, 0.45]), 0, 0, weight=10
)
solver.align_with(chair[0], tv_cabinet[0])

solver.distance_constraint(
    side_table[0], AssetInstance(position=[1.85, 1.57, 0.275]), 0, 0, weight=10
)
solver.align_with(side_table[0], chair[0])
solver.distance_constraint(side_table[0], chair[0], 0.80, 0.90)

# Flowers sit on the side table; their base meets its 0.55 m tabletop.
flowers[0].position = [1.85, 1.57, 0.80]
flowers[0].rotation = [0, 0, 0]
solver.on_top_of(flowers[0], side_table[0])
solver.distance_constraint(
    flowers[0], side_table[0], 0.525, 0.525, weight=10
)
solver.align_with(flowers[0], side_table[0])

# The lamp fits in the northeast corner, outside the northern door span.
floor_standing_lamp[0].position = [6.535, 6.55, 0.825]
floor_standing_lamp[0].rotation = [0, 0, radians(180)]
solver.against_wall(floor_standing_lamp[0], walls[2])
solver.distance_constraint(
    floor_standing_lamp[0],
    AssetInstance(position=[6.535, 6.55, 0.825]),
    0, 0, weight=10
)
solver.align_with(floor_standing_lamp[0], refrigerator[0])

# Wall-mounted AC above the sofa. Its explicit elevated anchor prevents
# it from being treated as a floor appliance; no support surface is needed.
air_conditioner[0].position = [6.04, 1.55, 2.45]
air_conditioner[0].rotation = [0, 0, radians(180)]
solver.distance_constraint(
    air_conditioner[0],
    AssetInstance(position=[6.04, 1.55, 2.45]),
    0, 0, weight=10
)
solver.against_wall(air_conditioner[0], walls[10])
solver.align_with(air_conditioner[0], sofa[0])

solver.constraints = []
tv_cabinet[0].position = [3.0250000953674316, 1.600000023841858, 0.25]
tv_cabinet[0].rotation = [0, 0, 0.025132740109855806]
tv_cabinet[0].optimize = 2
side_table[0].position = [1.850000023841858, 1.5700000524520874, 0.2750000059604645]
side_table[0].rotation = [0, 0, 0.02723203474245144]
side_table[0].optimize = 2
refrigerator[0].position = [6.029426097869873, 4.270545482635498, 0.925000011920929]
refrigerator[0].rotation = [0, 0, 2.909819615008199]
refrigerator[0].optimize = 2
chair[0].position = [1.0499999523162842, 1.7400000095367432, 0.44999998807907104]
chair[0].rotation = [0, 0, 0.02425190673629754]
chair[0].optimize = 2
flowers[0].position = [1.850000023841858, 1.5700000524520874, 0.800000011920929]
flowers[0].rotation = [0, 0, 0.01738372493157994]
flowers[0].optimize = 2
floor_standing_lamp[0].position = [6.534884929656982, 6.550000190734863, 0.824999988079071]
floor_standing_lamp[0].rotation = [0, 0, 3.141484920736423]
floor_standing_lamp[0].optimize = 2
air_conditioner[0].position = [6.039441108703613, 1.5499999523162842, 0.1599999964237213]
air_conditioner[0].rotation = [0, 0, 3.1414837391229335]
air_conditioner[0].optimize = 2
coffee_table[0].position = [4.5, 1.850000023841858, 0.20999999344348907]
coffee_table[0].rotation = [0, 0, 0.02625105139801769]
coffee_table[0].optimize = 2
sofa[0].position = [5.624975681304932, 1.9744586944580078, 0.42500001192092896]
sofa[0].rotation = [0, 0, 2.62109422495218]
sofa[0].optimize = 2
carpet[0].position = [4.650000095367432, 1.600000023841858, 0.009999999776482582]
carpet[0].rotation = [0, 0, 0.024208663519025363]
carpet[0].optimize = 2
dining_table_combination[0].position = [4.449999809265137, 4.650000095367432, 0.4749999940395355]
dining_table_combination[0].rotation = [0, 0, 0.024208663519025363]
dining_table_combination[0].optimize = 2

