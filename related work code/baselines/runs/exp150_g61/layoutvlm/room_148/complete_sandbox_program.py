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
    Wall(corner1=[5.00, 0.00, 0.00], corner2=[5.00, 4.00, 0.00]),
    Wall(corner1=[5.00, 4.00, 0.00], corner2=[0.00, 4.00, 0.00]),
    Wall(corner1=[0.00, 4.00, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[5.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
freestanding_pantry_cabinet = Assets(description="tall freestanding pantry cabinet for dry goods and kitchen supplies", size=[0.60, 0.90, 2.10], placements=[AssetInstance() for _ in range(1)])
under_counter_wine_rack = Assets(description="under-counter wine rack able to hold several bottles horizontally", size=[0.55, 0.45, 0.85], placements=[AssetInstance() for _ in range(1)])
kitchen_countertop_with_stove = Assets(description="extended long kitchen countertop integrated with a 6-burner stove and oven below", size=[0.65, 2.40, 0.90], placements=[AssetInstance() for _ in range(1)])
kitchen_base_cabinets = Assets(description="extended base kitchen cabinets with drawers and storage under countertop", size=[0.60, 1.80, 0.86], placements=[AssetInstance() for _ in range(1)])

freestanding_pantry_cabinet[0].instance_id = 'freestanding_pantry_cabinet_0'
under_counter_wine_rack[0].instance_id = 'under_counter_wine_rack_0'
kitchen_countertop_with_stove[0].instance_id = 'kitchen_countertop_with_stove_0'
kitchen_base_cabinets[0].instance_id = 'kitchen_base_cabinets_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

freestanding_pantry_cabinet[0].position = [3.374225774907668, 1.242888922525161, 1.05]
freestanding_pantry_cabinet[0].rotation = [0, 0, 0]
under_counter_wine_rack[0].position = [3.723704766718194, 3.066611627665126, 0.425]
under_counter_wine_rack[0].rotation = [0, 0, 0]
kitchen_countertop_with_stove[0].position = [3.953588310792912, 3.4427999603075436, 0.45]
kitchen_countertop_with_stove[0].rotation = [0, 0, 0]
kitchen_base_cabinets[0].position = [0.8300509884378604, 0.5391459848112472, 0.43]
kitchen_base_cabinets[0].rotation = [0, 0, 0]
freestanding_pantry_cabinet[0].position = [3.374225774907668, 1.242888922525161, 1.05]
freestanding_pantry_cabinet[0].rotation = [0, 0, 0]
under_counter_wine_rack[0].position = [3.723704766718194, 3.066611627665126, 0.425]
under_counter_wine_rack[0].rotation = [0, 0, 0]
kitchen_countertop_with_stove[0].position = [3.953588310792912, 3.4427999603075436, 0.45]
kitchen_countertop_with_stove[0].rotation = [0, 0, 0]
kitchen_base_cabinets[0].position = [0.8300509884378604, 0.5391459848112472, 0.43]
kitchen_base_cabinets[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the actual wall coordinates: the room spans x=0..5, y=0..4.
# Arrange stove, base cabinets, and wine rack along the north wall,
# facing south. Their long local y axes become horizontal after rotation.
# Leave 0.05 m between neighboring units and ample open working space.
kitchen_countertop_with_stove[0].position = [1.25, 3.675, 0.45]
kitchen_countertop_with_stove[0].rotation = [0, 0, radians(-90)]

kitchen_base_cabinets[0].position = [3.40, 3.70, 0.43]
kitchen_base_cabinets[0].rotation = [0, 0, radians(-90)]

under_counter_wine_rack[0].position = [4.575, 3.725, 0.425]
under_counter_wine_rack[0].rotation = [0, 0, radians(-90)]

# Place the tall pantry against the west wall, facing east.
# Its footprint ends at y=2.25, clear of the north-wall worktop.
freestanding_pantry_cabinet[0].position = [0.30, 1.80, 1.05]
freestanding_pantry_cabinet[0].rotation = [0, 0, 0]

# Preserve these feasible, non-overlapping locations first.
# Fixed-point anchors are references, not additional scene furniture.
for placed_unit in (
    kitchen_countertop_with_stove[0],
    kitchen_base_cabinets[0],
    under_counter_wine_rack[0],
    freestanding_pantry_cabinet[0],
):
    solver.distance_constraint(
        placed_unit,
        AssetInstance(position=list(placed_unit.position)),
        0, 0,
        weight=10,
    )

solver.against_wall(kitchen_countertop_with_stove[0], walls[1])
solver.against_wall(kitchen_base_cabinets[0], walls[1])
solver.against_wall(under_counter_wine_rack[0], walls[1])
solver.against_wall(freestanding_pantry_cabinet[0], walls[2])

# Orientation references share each unit's height and lie directly in front.
solver.point_towards(
    kitchen_countertop_with_stove[0],
    AssetInstance(position=[1.25, 2.675, 0.45]),
)
solver.point_towards(
    kitchen_base_cabinets[0],
    AssetInstance(position=[3.40, 2.70, 0.43]),
)
solver.point_towards(
    under_counter_wine_rack[0],
    AssetInstance(position=[4.575, 2.725, 0.425]),
)
solver.point_towards(
    freestanding_pantry_cabinet[0],
    AssetInstance(position=[1.30, 1.80, 1.05]),
)

# The requested proximity must refer to surface gaps: center distances
# of 0.50 m or 0.30 m would force these large units to overlap.
# Convert the allowed surface gaps into center-distance bounds using
# their horizontal half-widths and their small y/z center offsets.
solver.distance_constraint(
    kitchen_base_cabinets[0],
    kitchen_countertop_with_stove[0],
    (2.10**2 + 0.025**2 + 0.020**2)**0.5,
    (2.60**2 + 0.025**2 + 0.020**2)**0.5,
    weight=10,
)
solver.distance_constraint(
    kitchen_base_cabinets[0],
    under_counter_wine_rack[0],
    (1.125**2 + 0.025**2 + 0.005**2)**0.5,
    (1.425**2 + 0.025**2 + 0.005**2)**0.5,
    weight=10,
)

# All four units are floor-standing; the wine rack is not a tabletop object.

solver.constraints = []
freestanding_pantry_cabinet[0].position = [0.30000001192092896, 1.7999999523162842, 1.0499999523162842]
freestanding_pantry_cabinet[0].rotation = [0, 0, 3.6461838347439e-08]
freestanding_pantry_cabinet[0].optimize = 2
kitchen_countertop_with_stove[0].position = [1.25, 3.674999952316284, 0.44999998807907104]
kitchen_countertop_with_stove[0].rotation = [0, 0, -1.570796286077873]
kitchen_countertop_with_stove[0].optimize = 2
kitchen_base_cabinets[0].position = [3.4000000953674316, 3.700000047683716, 0.4300000071525574]
kitchen_base_cabinets[0].rotation = [0, 0, -1.5707962855479267]
kitchen_base_cabinets[0].optimize = 2
under_counter_wine_rack[0].position = [4.574999809265137, 3.72499942779541, 0.42500001192092896]
under_counter_wine_rack[0].rotation = [0, 0, -1.5707962847317822]
under_counter_wine_rack[0].optimize = 2

