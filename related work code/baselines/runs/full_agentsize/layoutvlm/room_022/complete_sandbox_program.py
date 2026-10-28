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
    Wall(corner1=[0.00, 3.96, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[5.52, 0.00, 0.00]),
    Wall(corner1=[5.52, 0.00, 0.00], corner2=[5.52, 2.70, 0.00]),
    Wall(corner1=[5.52, 2.70, 0.00], corner2=[10.20, 2.70, 0.00]),
    Wall(corner1=[10.20, 2.70, 0.00], corner2=[10.20, 3.96, 0.00]),
    Wall(corner1=[10.20, 3.96, 0.00], corner2=[0.00, 3.96, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
tv_stand = Assets(description="A modern media console with a sleek design, featuring multiple compartments and drawers for storage. It has a rectangular shape with a flat top surface and is supported by thin legs.", size=[0.42, 1.80, 0.55], placements=[AssetInstance() for _ in range(1)])
wine_cabinet = Assets(description="A tall, dark-colored wine rack cabinet with multiple shelves and compartments. It features a central section for storing wine bottles in a diamond pattern, surrounded by open shelves and closed cabinets at the bottom.", size=[0.40, 1.20, 1.90], placements=[AssetInstance() for _ in range(1)])
l_shaped_sofa = Assets(description="A modern sectional sofa with a light gray fabric upholstery and dark wooden legs. It features a chaise lounge on one side and multiple cushioned seats along its length.", size=[1.70, 2.80, 0.85], placements=[AssetInstance() for _ in range(1)])
washing_machine = Assets(description="A black washing machine with a circular door and control panel on the top right side. It has a sleek design with smooth surfaces and a rectangular base.", size=[0.65, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
potted_plant = Assets(description="A potted plant with broad green leaves and a textured brown trunk, placed in a white spherical pot on a black square base.", size=[0.65, 0.65, 1.50], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="A modern ottoman with a sleek design, featuring a rectangular shape and rounded edges. It has a dark gray or black cushioned top and a lighter gray base with a wavy texture along the edge.", size=[0.70, 1.20, 0.42], placements=[AssetInstance() for _ in range(1)])
sideboard = Assets(description="A wooden cabinet with a dark brown finish and three gray doors. It has a simple design with a flat top surface and a base that extends slightly outward.", size=[0.45, 1.50, 0.80], placements=[AssetInstance() for _ in range(1)])

tv_stand[0].instance_id = 'tv_stand_0'
wine_cabinet[0].instance_id = 'wine_cabinet_0'
l_shaped_sofa[0].instance_id = 'l_shaped_sofa_0'
washing_machine[0].instance_id = 'washing_machine_0'
potted_plant[0].instance_id = 'potted_plant_0'
coffee_table[0].instance_id = 'coffee_table_0'
sideboard[0].instance_id = 'sideboard_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

tv_stand[0].position = [2.1650510359408135, 0.7520157726291623, 0.275]
tv_stand[0].rotation = [0, 0, 0]
wine_cabinet[0].position = [9.62778223809803, 3.1803810742647043, 0.95]
wine_cabinet[0].rotation = [0, 0, 0]
l_shaped_sofa[0].position = [7.637602002921752, 3.7890158316499902, 0.425]
l_shaped_sofa[0].rotation = [0, 0, 0]
washing_machine[0].position = [1.5918022230263293, 2.8717199952110373, 0.425]
washing_machine[0].rotation = [0, 0, 0]
potted_plant[0].position = [0.6051888507761308, 1.289126565181859, 0.75]
potted_plant[0].rotation = [0, 0, 0]
coffee_table[0].position = [5.410727249980915, 1.8748912228239099, 0.21]
coffee_table[0].rotation = [0, 0, 0]
sideboard[0].position = [8.88437554804182, 2.9294827791130396, 0.4]
sideboard[0].rotation = [0, 0, 0]
tv_stand[0].position = [2.1650510359408135, 0.7520157726291623, 0.275]
tv_stand[0].rotation = [0, 0, 0]
wine_cabinet[0].position = [9.62778223809803, 3.1803810742647043, 0.95]
wine_cabinet[0].rotation = [0, 0, 0]
l_shaped_sofa[0].position = [7.637602002921752, 3.7890158316499902, 0.425]
l_shaped_sofa[0].rotation = [0, 0, 0]
washing_machine[0].position = [1.5918022230263293, 2.8717199952110373, 0.425]
washing_machine[0].rotation = [0, 0, 0]
potted_plant[0].position = [0.6051888507761308, 1.289126565181859, 0.75]
potted_plant[0].rotation = [0, 0, 0]
coffee_table[0].position = [5.410727249980915, 1.8748912228239099, 0.21]
coffee_table[0].rotation = [0, 0, 0]
sideboard[0].position = [8.88437554804182, 2.9294827791130396, 0.4]
sideboard[0].rotation = [0, 0, 0]

solver.constraints = []

# Keep the primary living area in the wider left portion of the L-shaped room.
# The upper-right extension is left open because it contains several doorways.

# The sectional sits along the lower wall and faces the plant across the room.
l_shaped_sofa[0].position = [1.45, 0.85, 0.425]
l_shaped_sofa[0].rotation = [0, 0, radians(90)]

# Place the plant directly in front of the sofa, against the upper wall.
potted_plant[0].position = [1.45, 3.635, 0.75]
potted_plant[0].rotation = [0, 0, radians(-90)]

# Center the coffee table in the clear space between the sofa and plant.
coffee_table[0].position = [1.45, 2.20, 0.21]
coffee_table[0].rotation = [0, 0, radians(90)]

# Place the media console against the upper wall, clear of the plant and doors.
tv_stand[0].position = [3.10, 3.75, 0.275]
tv_stand[0].rotation = [0, 0, radians(-90)]

# Group the utility/storage pieces along the lower and right walls.
wine_cabinet[0].position = [3.70, 0.20, 0.95]
wine_cabinet[0].rotation = [0, 0, radians(90)]

washing_machine[0].position = [4.85, 0.325, 0.425]
washing_machine[0].rotation = [0, 0, radians(90)]

sideboard[0].position = [5.295, 1.70, 0.40]
sideboard[0].rotation = [0, 0, radians(180)]


# Fixed center points preserve the non-overlapping arrangement and keep all
# furniture away from the doorway-heavy upper-right portion of the plan.
sofa_center = AssetInstance(position=[1.45, 0.85, 0.425])
plant_center = AssetInstance(position=[1.45, 3.635, 0.75])
coffee_table_center = AssetInstance(position=[1.45, 2.20, 0.21])
tv_stand_center = AssetInstance(position=[3.10, 3.75, 0.275])
wine_cabinet_center = AssetInstance(position=[3.70, 0.20, 0.95])
washing_machine_center = AssetInstance(position=[4.85, 0.325, 0.425])
sideboard_center = AssetInstance(position=[5.295, 1.70, 0.40])

solver.distance_constraint(
    l_shaped_sofa[0], sofa_center, 0, 0, weight=10
)
solver.against_wall(l_shaped_sofa[0], walls[1])
# This is the principal orientation requirement: the sofa faces the plant.
solver.point_towards(l_shaped_sofa[0], potted_plant[0])

solver.distance_constraint(
    potted_plant[0], plant_center, 0, 0, weight=10
)
solver.against_wall(potted_plant[0], walls[5])
solver.point_towards(potted_plant[0], l_shaped_sofa[0])

solver.distance_constraint(
    coffee_table[0], coffee_table_center, 0, 0, weight=10
)
solver.align_with(coffee_table[0], l_shaped_sofa[0])

solver.distance_constraint(
    tv_stand[0], tv_stand_center, 0, 0, weight=10
)
solver.against_wall(tv_stand[0], walls[5])
solver.point_towards(tv_stand[0], l_shaped_sofa[0])

solver.distance_constraint(
    wine_cabinet[0], wine_cabinet_center, 0, 0, weight=10
)
solver.against_wall(wine_cabinet[0], walls[1])
solver.point_towards(wine_cabinet[0], potted_plant[0])

solver.distance_constraint(
    washing_machine[0], washing_machine_center, 0, 0, weight=10
)
solver.against_wall(washing_machine[0], walls[1])
solver.point_towards(washing_machine[0], potted_plant[0])

solver.distance_constraint(
    sideboard[0], sideboard_center, 0, 0, weight=10
)
solver.against_wall(sideboard[0], walls[2])
solver.point_towards(sideboard[0], coffee_table[0])

# Secondary semantic spacing constraints preserve useful circulation and the
# relationship among the three pieces in the seating group.
solver.distance_constraint(
    coffee_table[0], l_shaped_sofa[0], 1.25, 1.50, weight=1
)
solver.distance_constraint(
    coffee_table[0], potted_plant[0], 1.25, 1.60, weight=1
)
solver.distance_constraint(
    tv_stand[0], potted_plant[0], 1.50, 1.80, weight=1
)

solver.constraints = []
wine_cabinet[0].position = [3.700000047683716, 0.20000001788139343, 0.949999988079071]
wine_cabinet[0].rotation = [0, 0, 1.5707963643058962]
wine_cabinet[0].optimize = 2
sideboard[0].position = [5.2906999588012695, 1.7000000476837158, 0.4000000059604645]
sideboard[0].rotation = [0, 0, -3.1415926097233378]
sideboard[0].optimize = 2
washing_machine[0].position = [4.849999904632568, 0.32500001788139343, 0.42500001192092896]
washing_machine[0].rotation = [0, 0, 1.5707963703182917]
washing_machine[0].optimize = 2
l_shaped_sofa[0].position = [1.4500000476837158, 0.8500000238418579, 0.42500001192092896]
l_shaped_sofa[0].rotation = [0, 0, 1.5707963405440906]
l_shaped_sofa[0].optimize = 2
coffee_table[0].position = [1.4500000476837158, 2.200000047683716, 0.20999999344348907]
coffee_table[0].rotation = [0, 0, 1.5707963524638358]
coffee_table[0].optimize = 2
tv_stand[0].position = [3.0999999046325684, 3.749999761581421, 0.2750000059604645]
tv_stand[0].rotation = [0, 0, -1.5707962834854217]
tv_stand[0].optimize = 2
potted_plant[0].position = [1.4500000476837158, 3.6349997520446777, 0.75]
potted_plant[0].rotation = [0, 0, -1.570796283408398]
potted_plant[0].optimize = 2

