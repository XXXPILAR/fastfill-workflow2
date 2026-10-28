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
    Wall(corner1=[3.80, 5.20, 0.00], corner2=[3.80, 4.00, 0.00]),
    Wall(corner1=[3.80, 4.00, 0.00], corner2=[0.00, 4.00, 0.00]),
    Wall(corner1=[0.00, 4.00, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[5.45, 0.00, 0.00]),
    Wall(corner1=[5.45, 0.00, 0.00], corner2=[5.45, 5.20, 0.00]),
    Wall(corner1=[5.45, 5.20, 0.00], corner2=[3.80, 5.20, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
sofa = Assets(description="sofa", size=[0.95, 2.20, 0.85], placements=[AssetInstance() for _ in range(1)])
shoe_cabinet = Assets(description="shoe cabinet", size=[0.35, 1.20, 1.00], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="coffee table", size=[0.60, 1.20, 0.42], placements=[AssetInstance() for _ in range(1)])
side_table = Assets(description="side table", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])

sofa[0].instance_id = 'sofa_0'
shoe_cabinet[0].instance_id = 'shoe_cabinet_0'
coffee_table[0].instance_id = 'coffee_table_0'
side_table[0].instance_id = 'side_table_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

sofa[0].position = [3.0800180829729515, 0.9635816954188187, 0.425]
sofa[0].rotation = [0, 0, 0]
shoe_cabinet[0].position = [0.6714763110443509, 3.787916409740366, 0.5]
shoe_cabinet[0].rotation = [0, 0, 0]
coffee_table[0].position = [4.535417887468913, 1.9949648110911442, 0.21]
coffee_table[0].rotation = [0, 0, 0]
side_table[0].position = [3.532066824823553, 1.268805555781024, 0.275]
side_table[0].rotation = [0, 0, 0]
sofa[0].position = [3.0800180829729515, 0.9635816954188187, 0.425]
sofa[0].rotation = [0, 0, 0]
shoe_cabinet[0].position = [0.6714763110443509, 3.787916409740366, 0.5]
shoe_cabinet[0].rotation = [0, 0, 0]
coffee_table[0].position = [4.535417887468913, 1.9949648110911442, 0.21]
coffee_table[0].rotation = [0, 0, 0]
side_table[0].position = [3.532066824823553, 1.268805555781024, 0.275]
side_table[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the sofa along the upper wall of the main rectangular area. Its width
# runs along the wall, and its front faces downward toward the fixed TV cabinet.
sofa[0].position = [2.50, 3.525, sofa.size[2] / 2]
sofa[0].rotation = [0, 0, radians(-90)]

# Place the shallow shoe cabinet against the lower portion of the right wall,
# clear of both the bottom-right doorway and the doorway in the upper extension.
shoe_cabinet[0].position = [5.275, 2.35, shoe_cabinet.size[2] / 2]
shoe_cabinet[0].rotation = [0, 0, radians(180)]

# Center the coffee table in front of the sofa, leaving comfortable circulation
# around it and an unobstructed route from the left-hand doorway.
coffee_table[0].position = [2.50, 2.10, coffee_table.size[2] / 2]
coffee_table[0].rotation = [0, 0, radians(-90)]

# Put the side table beside the sofa's right arm with a small physical gap.
side_table[0].position = [4.00, 3.525, side_table.size[2] / 2]
side_table[0].rotation = [0, 0, radians(-90)]


# Fixed references used to preserve the intended functional relationships.
# The TV-facing point lies on the fixed cabinet, whose footprint is centered at
# (1.36, 0.18) and extends to approximately x=2.725.
tv_facing_point = AssetInstance(position=[2.50, 0.18, sofa.size[2] / 2])
shoe_facing_point = AssetInstance(position=[4.00, 2.35, shoe_cabinet.size[2] / 2])

# Sofa: wall contact is the primary positional requirement. The distance to the
# TV-facing point keeps it on the useful part of the wall, and its front is
# directed toward the cabinet.
solver.against_wall(sofa[0], walls[1])
solver.distance_constraint(
    sofa[0], tv_facing_point, min_distance=3.20, max_distance=3.50, weight=10
)
solver.point_towards(sofa[0], tv_facing_point)

# Shoe cabinet: keep its shallow back against the right wall and near the chosen
# wall segment without encroaching on either adjacent doorway.
solver.against_wall(shoe_cabinet[0], walls[4])
solver.distance_constraint(
    shoe_cabinet[0], shoe_facing_point,
    min_distance=1.20, max_distance=1.35, weight=10
)
solver.point_towards(shoe_cabinet[0], shoe_facing_point)

# Coffee table: maintain a usable sofa-to-table spacing and keep it between the
# sofa and TV. Parallel alignment makes its long edge follow the sofa.
solver.distance_constraint(
    coffee_table[0], sofa[0], min_distance=1.35, max_distance=1.50, weight=10
)
solver.distance_constraint(
    coffee_table[0], tv_facing_point,
    min_distance=1.80, max_distance=2.05, weight=1
)
solver.align_with(coffee_table[0], sofa[0])

# Side table: preserve its position beside the sofa rather than in front of it.
# The secondary coffee-table distance disambiguates the desired side.
solver.distance_constraint(
    side_table[0], sofa[0], min_distance=1.45, max_distance=1.60, weight=10
)
solver.distance_constraint(
    side_table[0], coffee_table[0],
    min_distance=1.95, max_distance=2.20, weight=1
)
solver.align_with(side_table[0], sofa[0])

solver.constraints = []
sofa[0].position = [2.5, 3.5250000953674316, 0.42500001192092896]
sofa[0].rotation = [0, 0, -1.5707962988379771]
sofa[0].optimize = 2
shoe_cabinet[0].position = [5.274999141693115, 2.3499999046325684, 0.5]
shoe_cabinet[0].rotation = [0, 0, 3.141592621938999]
shoe_cabinet[0].optimize = 2
side_table[0].position = [4.0, 3.5250000953674316, 0.2750000059604645]
side_table[0].rotation = [0, 0, -1.5707962368496635]
side_table[0].optimize = 2
coffee_table[0].position = [2.5, 2.0999999046325684, 0.20999999344348907]
coffee_table[0].rotation = [0, 0, -1.570796183469682]
coffee_table[0].optimize = 2

