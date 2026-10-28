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
    Wall(corner1=[0.24, 1.06, 0.00], corner2=[0.00, 1.06, 0.00]),
    Wall(corner1=[0.00, 1.06, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[0.24, 0.00, 0.00]),
    Wall(corner1=[0.24, 0.00, 0.00], corner2=[0.24, 0.52, 0.00]),
    Wall(corner1=[0.24, 0.52, 0.00], corner2=[3.92, 0.52, 0.00]),
    Wall(corner1=[3.92, 0.52, 0.00], corner2=[3.92, 5.34, 0.00]),
    Wall(corner1=[3.92, 5.34, 0.00], corner2=[3.54, 5.34, 0.00]),
    Wall(corner1=[3.54, 5.34, 0.00], corner2=[3.54, 5.58, 0.00]),
    Wall(corner1=[3.54, 5.58, 0.00], corner2=[2.64, 5.58, 0.00]),
    Wall(corner1=[2.64, 5.58, 0.00], corner2=[2.64, 5.34, 0.00]),
    Wall(corner1=[2.64, 5.34, 0.00], corner2=[2.52, 5.34, 0.00]),
    Wall(corner1=[2.52, 5.34, 0.00], corner2=[2.52, 3.54, 0.00]),
    Wall(corner1=[2.52, 3.54, 0.00], corner2=[0.24, 3.54, 0.00]),
    Wall(corner1=[0.24, 3.54, 0.00], corner2=[0.24, 1.06, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
sideboard = Assets(description="A tall, dark brown chest of drawers with multiple drawers and ornate handles. It features a classic design with a slightly curved front and decorative molding at the top.", size=[0.50, 1.15, 1.30], placements=[AssetInstance() for _ in range(1)])
houseplant = Assets(description="A potted Monstera plant with large, green leaves and a sturdy stem, placed in a white pot on a black square base.", size=[0.80, 0.80, 1.40], placements=[AssetInstance() for _ in range(1)])
dining_table = Assets(description="A round wooden table with an ornate pedestal base, featuring carved details and a dark finish.", size=[1.40, 1.40, 0.76], placements=[AssetInstance() for _ in range(1)])
wine_cabinet = Assets(description="A wooden cabinet with a combination of open shelves and closed compartments. It features a wine rack section, storage for bottles, and a countertop area. The design includes both light and dark wood finishes.", size=[0.48, 1.20, 1.70], placements=[AssetInstance() for _ in range(1)])

sideboard[0].instance_id = 'sideboard_0'
houseplant[0].instance_id = 'houseplant_0'
dining_table[0].instance_id = 'dining_table_0'
wine_cabinet[0].instance_id = 'wine_cabinet_0'
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

sideboard[0].position = [1.227088462838582, 1.8140638654904304, 0.65]
sideboard[0].rotation = [0, 0, 0]
houseplant[0].position = [3.565991637292785, 3.9236662327825957, 0.7]
houseplant[0].rotation = [0, 0, 0]
dining_table[0].position = [0.5842998843437777, 2.5788086025971335, 0.38]
dining_table[0].rotation = [0, 0, 0]
wine_cabinet[0].position = [3.892280626126568, 2.994864835868213, 0.85]
wine_cabinet[0].rotation = [0, 0, 0]
sideboard[0].position = [1.227088462838582, 1.8140638654904304, 0.65]
sideboard[0].rotation = [0, 0, 0]
houseplant[0].position = [3.565991637292785, 3.9236662327825957, 0.7]
houseplant[0].rotation = [0, 0, 0]
dining_table[0].position = [0.5842998843437777, 2.5788086025971335, 0.38]
dining_table[0].rotation = [0, 0, 0]
wine_cabinet[0].position = [3.892280626126568, 2.994864835868213, 0.85]
wine_cabinet[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the round dining table in the lower half of the main room, leaving
# a clear approach to the wide doorway at y=3.54.
dining_table[0].position = [2.00, 1.85, 0.38]
dining_table[0].rotation = [0, 0, 0]

# Tuck the plant into the lower-left corner without touching either wall.
houseplant[0].position = [0.70, 1.00, 0.70]
houseplant[0].rotation = [0, 0, radians(33)]

# Both storage pieces use the long right-hand wall. The wine cabinet remains
# in the main room, while the sideboard occupies the upper-right wall segment.
# Their shallow dimensions are normal to the wall, and they face into the room.
wine_cabinet[0].position = [3.68, 2.35, 0.85]
wine_cabinet[0].rotation = [0, 0, radians(180)]

sideboard[0].position = [3.67, 4.65, 0.65]
sideboard[0].rotation = [0, 0, radians(180)]

# Fixed targets preserve the intended centers while the solver resolves the
# remaining constraints. Their heights match the corresponding asset centers.
table_anchor = AssetInstance(position=[2.00, 1.85, 0.38])
plant_anchor = AssetInstance(position=[0.70, 1.00, 0.70])
wine_anchor = AssetInstance(position=[3.68, 2.35, 0.85])
sideboard_anchor = AssetInstance(position=[3.67, 4.65, 0.65])

# Important position constraints are specified first.
solver.distance_constraint(
    dining_table[0], table_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    houseplant[0], plant_anchor, 0, 0, weight=10
)

# Wall 5 is the continuous right wall from (3.92, 0.52) to (3.92, 5.34).
solver.against_wall(wine_cabinet[0], walls[5])
solver.distance_constraint(
    wine_cabinet[0], wine_anchor, 0, 0, weight=10
)

# The requested sideboard-against-wall relationship.
solver.against_wall(sideboard[0], walls[5])
solver.distance_constraint(
    sideboard[0], sideboard_anchor, 0, 0, weight=10
)

# Orientation constraints for every new asset. The cabinets face inward from
# the right wall, the table aligns with the room axes, and the plant faces the
# dining arrangement.
solver.point_towards(
    wine_cabinet[0],
    AssetInstance(position=[2.50, 2.35, 0.85])
)
solver.point_towards(
    sideboard[0],
    AssetInstance(position=[2.50, 4.65, 0.65])
)
solver.align_with(dining_table[0], wine_cabinet[0], angle=180)
solver.point_towards(houseplant[0], dining_table[0])

# Low-weight spacing constraints maintain non-overlap and usable circulation.
solver.distance_constraint(
    dining_table[0], houseplant[0], 1.45, None, weight=0.1
)
solver.distance_constraint(
    dining_table[0], wine_cabinet[0], 1.65, None, weight=0.1
)
solver.distance_constraint(
    dining_table[0], sideboard[0], 2.70, None, weight=0.1
)
solver.distance_constraint(
    wine_cabinet[0], sideboard[0], 1.40, None, weight=0.1
)
solver.distance_constraint(
    houseplant[0], wine_cabinet[0], 2.50, None, weight=0.1
)

# Keep the central floor immediately inside the two doorways unobstructed.
wide_door_approach = AssetInstance(position=[1.28, 3.10, 0.38])
upper_door_approach = AssetInstance(position=[3.09, 5.08, 0.65])

solver.distance_constraint(
    dining_table[0], wide_door_approach, 1.30, None, weight=1
)
solver.distance_constraint(
    sideboard[0], upper_door_approach, 0.75, None, weight=1
)

solver.constraints = []
sideboard[0].position = [3.2861435413360596, 5.003155708312988, 0.6499999761581421]
sideboard[0].rotation = [0, 0, -3.1410554771872596]
sideboard[0].optimize = 2
dining_table[0].position = [2.0413966178894043, 1.9108933210372925, 0.3799999952316284]
dining_table[0].rotation = [0, 0, 1.3559403157466098e-07]
dining_table[0].optimize = 2
houseplant[0].position = [0.7951029539108276, 1.0796229839324951, 0.699999988079071]
houseplant[0].rotation = [0, 0, 0.5916666211542109]
houseplant[0].optimize = 2
wine_cabinet[0].position = [3.6648976802825928, 2.3499999046325684, 0.8500000238418579]
wine_cabinet[0].rotation = [0, 0, -3.1415926092219064]
wine_cabinet[0].optimize = 2

