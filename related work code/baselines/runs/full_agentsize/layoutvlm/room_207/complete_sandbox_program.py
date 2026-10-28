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
chair = Assets(description="chair", size=[0.58, 0.55, 0.82], placements=[AssetInstance() for _ in range(1)])
side_table = Assets(description="side table", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
air_conditioner = Assets(description="air conditioner", size=[0.25, 1.00, 0.32], placements=[AssetInstance() for _ in range(1)])
refrigerator = Assets(description="refrigerator", size=[0.75, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[2.00, 3.00, 0.02], placements=[AssetInstance() for _ in range(1)])
flowers = Assets(description="flowers", size=[0.35, 0.35, 0.55], placements=[AssetInstance() for _ in range(1)])
dining_table_combination = Assets(description="dining table combination", size=[1.80, 2.40, 0.90], placements=[AssetInstance() for _ in range(1)])
floor_standing_lamp = Assets(description="floor standing lamp", size=[0.45, 0.45, 1.65], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="coffee table", size=[0.65, 1.20, 0.42], placements=[AssetInstance() for _ in range(1)])
tv_cabinet = Assets(description="tv cabinet", size=[0.45, 2.00, 0.55], placements=[AssetInstance() for _ in range(1)])
sofa = Assets(description="sofa", size=[0.95, 2.40, 0.85], placements=[AssetInstance() for _ in range(1)])

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

chair[0].position = [5.639501893199051, 2.9619148456786086, 0.41]
chair[0].rotation = [0, 0, 0]
side_table[0].position = [5.028453334295683, 6.084739933701445, 0.275]
side_table[0].rotation = [0, 0, 0]
air_conditioner[0].position = [2.8253473366769284, 0.4798883062936821, 0.16]
air_conditioner[0].rotation = [0, 0, 0]
refrigerator[0].position = [3.288577452690726, 4.1956888505559995, 0.9]
refrigerator[0].rotation = [0, 0, 0]
carpet[0].position = [6.070841745747156, 4.735019806452977, 0.01]
carpet[0].rotation = [0, 0, 0]
flowers[0].position = [5.913747982070482, 1.537077309603642, 0.275]
flowers[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [2.542987869552404, 2.914565627580821, 0.45]
dining_table_combination[0].rotation = [0, 0, 0]
floor_standing_lamp[0].position = [2.6036977145133036, 2.9922487961220057, 0.825]
floor_standing_lamp[0].rotation = [0, 0, 0]
coffee_table[0].position = [4.788059724853364, 5.926516830359027, 0.21]
coffee_table[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [2.147522870330241, 2.061667892292701, 0.275]
tv_cabinet[0].rotation = [0, 0, 0]
sofa[0].position = [2.598067430128373, 2.7504238940114982, 0.425]
sofa[0].rotation = [0, 0, 0]
chair[0].position = [5.639501893199051, 2.9619148456786086, 0.41]
chair[0].rotation = [0, 0, 0]
side_table[0].position = [5.028453334295683, 6.084739933701445, 0.275]
side_table[0].rotation = [0, 0, 0]
air_conditioner[0].position = [2.8253473366769284, 0.4798883062936821, 0.16]
air_conditioner[0].rotation = [0, 0, 0]
refrigerator[0].position = [3.288577452690726, 4.1956888505559995, 0.9]
refrigerator[0].rotation = [0, 0, 0]
carpet[0].position = [6.070841745747156, 4.735019806452977, 0.01]
carpet[0].rotation = [0, 0, 0]
flowers[0].position = [5.913747982070482, 1.537077309603642, 0.275]
flowers[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [2.542987869552404, 2.914565627580821, 0.45]
dining_table_combination[0].rotation = [0, 0, 0]
floor_standing_lamp[0].position = [2.6036977145133036, 2.9922487961220057, 0.825]
floor_standing_lamp[0].rotation = [0, 0, 0]
coffee_table[0].position = [4.788059724853364, 5.926516830359027, 0.21]
coffee_table[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [2.147522870330241, 2.061667892292701, 0.275]
tv_cabinet[0].rotation = [0, 0, 0]
sofa[0].position = [2.598067430128373, 2.7504238940114982, 0.425]
sofa[0].rotation = [0, 0, 0]

solver.constraints = []

# Divide the irregular floor plan into two functional zones:
# - dining in the central/lower area, clear of the southern and eastern doors;
# - living in the upper area, leaving a clear strip immediately inside the wide
#   northern door (the living furniture ends at approximately y=6.20).
#
# Furniture touching a wall uses a center offset equal to half of its depth.
# Small decor is vertically supported with an on_top_of constraint.

chair.placements[0].position = [5.72, 1.58, chair.size[2] / 2]
chair.placements[0].rotation = [0, 0, radians(180)]

side_table.placements[0].position = [3.15, 6.50, side_table.size[2] / 2]
side_table.placements[0].rotation = [0, 0, 0]

# Wall-mounted above the western end of the living zone.
air_conditioner.placements[0].position = [2.925, 4.75, 2.30]
air_conditioner.placements[0].rotation = [0, 0, 0]

# Against the lower part of the east wall, away from the nearby doorway.
refrigerator.placements[0].position = [5.785, 0.55, refrigerator.size[2] / 2]
refrigerator.placements[0].rotation = [0, 0, radians(180)]

# Rotating the carpet makes its floor footprint 3.0 m by 2.0 m.
carpet.placements[0].position = [4.80, 5.00, carpet.size[2] / 2]
carpet.placements[0].rotation = [0, 0, radians(90)]

# The flowers share the side table's x-y center and sit on its top surface.
flowers.placements[0].position = [
    3.15,
    6.50,
    side_table.size[2] + flowers.size[2] / 2,
]
flowers.placements[0].rotation = [0, 0, 0]

# The rotated dining set occupies approximately x=[2.95, 5.35],
# y=[1.30, 3.10], keeping the approach from the southern door open.
dining_table_combination.placements[0].position = [
    4.15,
    2.20,
    dining_table_combination.size[2] / 2,
]
dining_table_combination.placements[0].rotation = [0, 0, radians(90)]

floor_standing_lamp.placements[0].position = [
    5.95,
    4.35,
    floor_standing_lamp.size[2] / 2,
]
floor_standing_lamp.placements[0].rotation = [0, 0, radians(90)]

coffee_table.placements[0].position = [
    4.80,
    5.00,
    coffee_table.size[2] / 2,
]
coffee_table.placements[0].rotation = [0, 0, 0]

# The cabinet and sofa face one another across the living area.
tv_cabinet.placements[0].position = [
    6.535,
    5.00,
    tv_cabinet.size[2] / 2,
]
tv_cabinet.placements[0].rotation = [0, 0, radians(180)]

sofa.placements[0].position = [3.275, 5.00, sofa.size[2] / 2]
sofa.placements[0].rotation = [0, 0, 0]


# Fixed anchors preserve the selected zones and the clear door approaches.
_chair_anchor = AssetInstance(position=[5.72, 1.58, chair.size[2] / 2])
_side_table_anchor = AssetInstance(
    position=[3.15, 6.50, side_table.size[2] / 2]
)
_air_conditioner_anchor = AssetInstance(position=[2.925, 4.75, 2.30])
_refrigerator_anchor = AssetInstance(
    position=[5.785, 0.55, refrigerator.size[2] / 2]
)
_carpet_anchor = AssetInstance(
    position=[4.80, 5.00, carpet.size[2] / 2],
    rotation=[0, 0, radians(90)],
)
_flowers_anchor = AssetInstance(
    position=[3.15, 6.50, side_table.size[2] + flowers.size[2] / 2]
)
_dining_anchor = AssetInstance(
    position=[4.15, 2.20, dining_table_combination.size[2] / 2],
    rotation=[0, 0, radians(90)],
)
_lamp_anchor = AssetInstance(
    position=[5.95, 4.35, floor_standing_lamp.size[2] / 2]
)
_coffee_anchor = AssetInstance(
    position=[4.80, 5.00, coffee_table.size[2] / 2]
)
_tv_anchor = AssetInstance(
    position=[6.535, 5.00, tv_cabinet.size[2] / 2]
)
_sofa_anchor = AssetInstance(position=[3.275, 5.00, sofa.size[2] / 2])


# High-priority position constraints maintain the non-overlapping arrangement.
solver.distance_constraint(
    chair[0], _chair_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    side_table[0], _side_table_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    air_conditioner[0], _air_conditioner_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    refrigerator[0], _refrigerator_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    carpet[0], _carpet_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    flowers[0], _flowers_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    dining_table_combination[0], _dining_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    floor_standing_lamp[0], _lamp_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    coffee_table[0], _coffee_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    tv_cabinet[0], _tv_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    sofa[0], _sofa_anchor, 0, 0, weight=10
)


# Wall relationships for the major perimeter furniture.
solver.against_wall(air_conditioner[0], walls[4])
solver.against_wall(refrigerator[0], walls[10])
solver.against_wall(tv_cabinet[0], walls[2])
solver.against_wall(sofa[0], walls[4])

# The flowers must remain supported by the side table.
solver.on_top_of(flowers[0], side_table[0])

# Functional proximity constraints supplement the exact layout anchors.
solver.distance_constraint(
    chair[0], dining_table_combination[0], 1.40, 1.75, weight=1
)
solver.distance_constraint(
    sofa[0], coffee_table[0], 1.45, 1.65, weight=1
)
solver.distance_constraint(
    coffee_table[0], tv_cabinet[0], 1.60, 1.85, weight=1
)
solver.distance_constraint(
    side_table[0], sofa[0], 1.45, 1.60, weight=1
)
solver.distance_constraint(
    floor_standing_lamp[0], coffee_table[0], 1.30, 1.50, weight=1
)

# Orientation constraints: the dining chair faces the table; the sofa and
# cabinet face each other; the remaining assets retain coherent alignment.
solver.point_towards(chair[0], dining_table_combination[0])
solver.align_with(side_table[0], sofa[0])
solver.point_towards(air_conditioner[0], coffee_table[0])
solver.point_towards(refrigerator[0], dining_table_combination[0])
solver.align_with(carpet[0], dining_table_combination[0])
solver.align_with(flowers[0], side_table[0])
solver.align_with(dining_table_combination[0], _dining_anchor)
solver.point_towards(floor_standing_lamp[0], coffee_table[0])
solver.align_with(coffee_table[0], sofa[0])
solver.point_towards(tv_cabinet[0], sofa[0])
solver.point_towards(sofa[0], tv_cabinet[0])

solver.constraints = []
sofa[0].position = [3.298734664916992, 5.0, 0.42500001192092896]
sofa[0].rotation = [0, 0, 0.01809489430059444]
sofa[0].optimize = 2
refrigerator[0].position = [5.783857822418213, 0.550000011920929, 0.8999999761581421]
refrigerator[0].rotation = [0, 0, -3.1390517385055796]
refrigerator[0].optimize = 2
side_table[0].position = [3.1500000953674316, 6.5, 0.2750000059604645]
side_table[0].rotation = [0, 0, 0.02913410042039103]
side_table[0].optimize = 2
flowers[0].position = [3.1500000953674316, 6.5, 0.8250000476837158]
flowers[0].rotation = [0, 0, 0.02278736617577962]
flowers[0].optimize = 2
floor_standing_lamp[0].position = [5.949999809265137, 4.349999904632568, 0.824999988079071]
floor_standing_lamp[0].rotation = [0, 0, 1.5935881447584697]
floor_standing_lamp[0].optimize = 2
air_conditioner[0].position = [2.926270008087158, 4.75, 0.1599999964237213]
air_conditioner[0].rotation = [0, 0, 0.002540913862115027]
air_conditioner[0].optimize = 2
coffee_table[0].position = [4.800000190734863, 5.0, 0.20999999344348907]
coffee_table[0].rotation = [0, 0, 0.035473676517363766]
coffee_table[0].optimize = 2
dining_table_combination[0].position = [4.150000095367432, 2.200000047683716, 0.44999998807907104]
dining_table_combination[0].rotation = [0, 0, 1.5927874750809192]
dining_table_combination[0].optimize = 2
tv_cabinet[0].position = [6.544938564300537, 5.009999752044678, 0.2750000059604645]
tv_cabinet[0].rotation = [0, 0, -3.132830449794054]
tv_cabinet[0].optimize = 2
chair[0].position = [5.71999979019165, 1.5800000429153442, 0.4099999964237213]
chair[0].rotation = [0, 0, -3.1290262823329655]
chair[0].optimize = 2
carpet[0].position = [4.800000190734863, 5.0, 0.009999999776482582]
carpet[0].rotation = [0, 0, 1.5904130731936221]
carpet[0].optimize = 2

