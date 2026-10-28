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
    Wall(corner1=[6.90, 0.00, 0.00], corner2=[6.90, 1.87, 0.00]),
    Wall(corner1=[6.90, 1.87, 0.00], corner2=[8.19, 1.87, 0.00]),
    Wall(corner1=[8.19, 1.87, 0.00], corner2=[8.19, 2.94, 0.00]),
    Wall(corner1=[8.19, 2.94, 0.00], corner2=[3.68, 2.94, 0.00]),
    Wall(corner1=[3.68, 2.94, 0.00], corner2=[3.68, 7.04, 0.00]),
    Wall(corner1=[3.68, 7.04, 0.00], corner2=[0.00, 7.04, 0.00]),
    Wall(corner1=[0.00, 7.04, 0.00], corner2=[0.00, 3.58, 0.00]),
    Wall(corner1=[0.00, 3.58, 0.00], corner2=[1.29, 3.58, 0.00]),
    Wall(corner1=[1.29, 3.58, 0.00], corner2=[1.29, 2.77, 0.00]),
    Wall(corner1=[1.29, 2.77, 0.00], corner2=[1.79, 2.77, 0.00]),
    Wall(corner1=[1.79, 2.77, 0.00], corner2=[1.79, 0.55, 0.00]),
    Wall(corner1=[1.79, 0.55, 0.00], corner2=[1.49, 0.55, 0.00]),
    Wall(corner1=[1.49, 0.55, 0.00], corner2=[1.49, 0.00, 0.00]),
    Wall(corner1=[1.49, 0.00, 0.00], corner2=[6.90, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
tv_cabinet = Assets(description="tv cabinet", size=[0.45, 2.20, 0.55], placements=[AssetInstance() for _ in range(1)])
wine_cabinet = Assets(description="wine cabinet", size=[0.45, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
refrigerator = Assets(description="refrigerator", size=[0.72, 0.90, 1.85], placements=[AssetInstance() for _ in range(1)])
sofa = Assets(description="sofa", size=[0.95, 3.00, 0.85], placements=[AssetInstance() for _ in range(1)])
carpet_A = Assets(description="carpet", size=[2.40, 3.20, 0.02], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="coffee table", size=[0.65, 1.20, 0.42], placements=[AssetInstance() for _ in range(1)])
carpet_B = Assets(description="carpet", size=[2.00, 2.80, 0.02], placements=[AssetInstance() for _ in range(1)])
entrance_cabinet = Assets(description="entrance cabinet", size=[0.40, 1.40, 1.10], placements=[AssetInstance() for _ in range(1)])
dining_table_combination = Assets(description="dining table combination", size=[2.20, 2.80, 0.78], placements=[AssetInstance() for _ in range(1)])

tv_cabinet[0].instance_id = 'tv_cabinet_0'
wine_cabinet[0].instance_id = 'wine_cabinet_0'
refrigerator[0].instance_id = 'refrigerator_0'
sofa[0].instance_id = 'sofa_0'
carpet_A[0].instance_id = 'carpet_A_0'
coffee_table[0].instance_id = 'coffee_table_0'
carpet_B[0].instance_id = 'carpet_B_0'
entrance_cabinet[0].instance_id = 'entrance_cabinet_0'
dining_table_combination[0].instance_id = 'dining_table_combination_0'
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

tv_cabinet[0].position = [1.841284060075838, 4.126433993575514, 0.275]
tv_cabinet[0].rotation = [0, 0, 0]
wine_cabinet[0].position = [3.780308433542336, 2.2990181402493204, 0.9]
wine_cabinet[0].rotation = [0, 0, 0]
refrigerator[0].position = [5.060999395238162, 2.465766261226587, 0.925]
refrigerator[0].rotation = [0, 0, 0]
sofa[0].position = [0.36104448347293777, 4.384698006606518, 0.425]
sofa[0].rotation = [0, 0, 0]
carpet_A[0].position = [5.0434361842740385, 1.0081289869820458, 0.01]
carpet_A[0].rotation = [0, 0, 0]
coffee_table[0].position = [2.6385682826391554, 0.047960320796598434, 0.21]
coffee_table[0].rotation = [0, 0, 0]
carpet_B[0].position = [1.370471194990964, 4.389294286167876, 0.01]
carpet_B[0].rotation = [0, 0, 0]
entrance_cabinet[0].position = [5.847954321108312, 1.9478886859522235, 0.55]
entrance_cabinet[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [3.2451199849022756, 0.43415346766488405, 0.39]
dining_table_combination[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [1.841284060075838, 4.126433993575514, 0.275]
tv_cabinet[0].rotation = [0, 0, 0]
wine_cabinet[0].position = [3.780308433542336, 2.2990181402493204, 0.9]
wine_cabinet[0].rotation = [0, 0, 0]
refrigerator[0].position = [5.060999395238162, 2.465766261226587, 0.925]
refrigerator[0].rotation = [0, 0, 0]
sofa[0].position = [0.36104448347293777, 4.384698006606518, 0.425]
sofa[0].rotation = [0, 0, 0]
carpet_A[0].position = [5.0434361842740385, 1.0081289869820458, 0.01]
carpet_A[0].rotation = [0, 0, 0]
coffee_table[0].position = [2.6385682826391554, 0.047960320796598434, 0.21]
coffee_table[0].rotation = [0, 0, 0]
carpet_B[0].position = [1.370471194990964, 4.389294286167876, 0.01]
carpet_B[0].rotation = [0, 0, 0]
entrance_cabinet[0].position = [5.847954321108312, 1.9478886859522235, 0.55]
entrance_cabinet[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [3.2451199849022756, 0.43415346766488405, 0.39]
dining_table_combination[0].rotation = [0, 0, 0]

solver.constraints = []

# Furnish the upper room as a living area. The sofa and TV cabinet are placed
# opposite one another, while preserving circulation through the lower rooms.
tv_cabinet[0].position = [3.455, 5.45, 0.275]
tv_cabinet[0].rotation = [0, 0, radians(180)]

wine_cabinet[0].position = [3.455, 3.54, 0.90]
wine_cabinet[0].rotation = [0, 0, radians(180)]

sofa[0].position = [0.475, 5.45, 0.425]
sofa[0].rotation = [0, 0, radians(0)]

carpet_A[0].position = [2.05, 5.35, 0.01]
carpet_A[0].rotation = [0, 0, radians(0)]

coffee_table[0].position = [2.05, 5.35, 0.23]
coffee_table[0].rotation = [0, 0, radians(0)]

# Furnish the lower room as the dining/entry area. Rotating the dining set
# keeps the door zones at (2.40, 0.00), (6.30, 2.94), and (7.67, 2.94) clear.
carpet_B[0].position = [4.45, 1.60, 0.01]
carpet_B[0].rotation = [0, 0, radians(90)]

dining_table_combination[0].position = [4.45, 1.60, 0.41]
dining_table_combination[0].rotation = [0, 0, radians(90)]

entrance_cabinet[0].position = [3.55, 0.20, 0.55]
entrance_cabinet[0].rotation = [0, 0, radians(90)]

# The refrigerator is placed against the bottom wall, away from the bottom
# entrance and with an unobstructed approach from the center of the room.
refrigerator[0].position = [6.45, 0.36, 0.925]
refrigerator[0].rotation = [0, 0, radians(90)]


# Fixed placement references keep the principal zones and door clearances
# stable if the constraint solver adjusts the layout.
tv_anchor = AssetInstance(position=[3.455, 5.45, 0.275])
wine_anchor = AssetInstance(position=[3.455, 3.54, 0.90])
sofa_anchor = AssetInstance(position=[0.475, 5.45, 0.425])
living_rug_anchor = AssetInstance(position=[2.05, 5.35, 0.01])
coffee_anchor = AssetInstance(position=[2.05, 5.35, 0.23])

dining_rug_anchor = AssetInstance(position=[4.45, 1.60, 0.01])
dining_anchor = AssetInstance(position=[4.45, 1.60, 0.41])
entrance_cabinet_anchor = AssetInstance(position=[3.55, 0.20, 0.55])
refrigerator_anchor = AssetInstance(position=[6.45, 0.36, 0.925])


# TV cabinet: retain its exact location against the east wall of the living
# area, and point its front toward the sofa.
solver.distance_constraint(
    tv_cabinet[0], tv_anchor, 0, 0, weight=10
)
solver.against_wall(tv_cabinet[0], walls[4])
solver.point_towards(tv_cabinet[0], sofa[0])

# Sofa: keep it against the opposite wall and facing the TV as required.
solver.distance_constraint(
    sofa[0], sofa_anchor, 0, 0, weight=10
)
solver.against_wall(sofa[0], walls[6])
solver.point_towards(sofa[0], tv_cabinet[0])

# The approximately three-meter separation provides a practical viewing
# distance while reinforcing the relationship between sofa and television.
solver.distance_constraint(
    sofa[0], tv_cabinet[0], 2.85, 3.10, weight=10
)

# Wine cabinet: place it at the lower end of the same wall as the TV cabinet
# without blocking the opening into the living room.
solver.distance_constraint(
    wine_cabinet[0], wine_anchor, 0, 0, weight=10
)
solver.against_wall(wine_cabinet[0], walls[4])
solver.align_with(wine_cabinet[0], tv_cabinet[0])

# Living-room carpet and coffee table form a centered conversation area.
solver.distance_constraint(
    carpet_A[0], living_rug_anchor, 0, 0, weight=10
)
solver.align_with(carpet_A[0], sofa[0])

solver.distance_constraint(
    coffee_table[0], coffee_anchor, 0, 0, weight=10
)
solver.on_top_of(coffee_table[0], carpet_A[0])
solver.align_with(coffee_table[0], sofa[0])
solver.distance_constraint(
    coffee_table[0], sofa[0], 1.45, 1.75, weight=5
)
solver.distance_constraint(
    coffee_table[0], tv_cabinet[0], 1.25, 1.55, weight=5
)

# Dining rug and dining combination occupy the central lower room, clear of
# the doorways along both the top and bottom boundaries.
solver.distance_constraint(
    carpet_B[0], dining_rug_anchor, 0, 0, weight=10
)
solver.align_with(carpet_B[0], dining_table_combination[0])

solver.distance_constraint(
    dining_table_combination[0], dining_anchor, 0, 0, weight=10
)
solver.on_top_of(dining_table_combination[0], carpet_B[0])
solver.align_with(dining_table_combination[0], carpet_B[0])

# Entrance cabinet: keep it beside, rather than in front of, the bottom door.
solver.distance_constraint(
    entrance_cabinet[0], entrance_cabinet_anchor, 0, 0, weight=10
)
solver.against_wall(entrance_cabinet[0], walls[13])
solver.align_with(entrance_cabinet[0], dining_table_combination[0])

# Refrigerator: enforce the required wall placement and orient its front into
# the room. Its anchor leaves a gap from the dining set and keeps the route to
# the door at (6.30, 2.94) open.
solver.distance_constraint(
    refrigerator[0], refrigerator_anchor, 0, 0, weight=10
)
solver.against_wall(refrigerator[0], walls[13])
solver.align_with(refrigerator[0], dining_table_combination[0])
solver.distance_constraint(
    refrigerator[0], dining_table_combination[0], 1.90, 2.20, weight=5
)

solver.constraints = []
sofa[0].position = [0.475159227848053, 5.449999809265137, 0.42500001192092896]
sofa[0].rotation = [0, 0, -8.062285058907835e-05]
sofa[0].optimize = 2
refrigerator[0].position = [6.400622367858887, 0.5485354661941528, 0.925000011920929]
refrigerator[0].rotation = [0, 0, -2.7784204017797705]
refrigerator[0].optimize = 2
carpet_A[0].position = [2.049999952316284, 5.349999904632568, 0.009999999776482582]
carpet_A[0].rotation = [0, 0, -0.00011203192204646481]
carpet_A[0].optimize = 2
dining_table_combination[0].position = [4.449999809265137, 1.600000023841858, 0.4099999964237213]
dining_table_combination[0].rotation = [0, 0, 1.5898819362170535]
dining_table_combination[0].optimize = 2
wine_cabinet[0].position = [3.077517509460449, 3.167623281478882, 0.8999999761581421]
wine_cabinet[0].rotation = [0, 0, 1.5730896759636415]
wine_cabinet[0].optimize = 2
coffee_table[0].position = [2.049999952316284, 5.349999904632568, 0.22999998927116394]
coffee_table[0].rotation = [0, 0, 3.503774484442646e-06]
coffee_table[0].optimize = 2
tv_cabinet[0].position = [3.4520163536071777, 5.449999809265137, 0.2750000059604645]
tv_cabinet[0].rotation = [0, 0, -3.141494573883262]
tv_cabinet[0].optimize = 2
carpet_B[0].position = [4.449999809265137, 1.600000023841858, 0.009999999776482582]
carpet_B[0].rotation = [0, 0, 1.5898390724151978]
carpet_B[0].optimize = 2
entrance_cabinet[0].position = [3.549999952316284, 0.6983035802841187, 0.550000011920929]
entrance_cabinet[0].rotation = [0, 0, -3.1332325141642]
entrance_cabinet[0].optimize = 2

