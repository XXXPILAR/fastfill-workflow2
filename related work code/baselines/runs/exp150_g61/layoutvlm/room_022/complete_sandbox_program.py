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
wine_cabinet = Assets(description="A tall, dark-colored wine rack cabinet with multiple shelves and compartments. It features a central section for storing wine bottles in a diamond pattern, surrounded by open shelves and closed cabinets at the bottom.", size=[0.40, 1.20, 2.00], placements=[AssetInstance() for _ in range(1)])
l_shaped_sofa = Assets(description="A modern sectional sofa with a light gray fabric upholstery and dark wooden legs. It features a chaise lounge on one side and multiple cushioned seats along its length.", size=[1.65, 2.80, 0.85], placements=[AssetInstance() for _ in range(1)])
washing_machine = Assets(description="A black washing machine with a circular door and control panel on the top right side. It has a sleek design with smooth surfaces and a rectangular base.", size=[0.65, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
potted_plant = Assets(description="A potted plant with broad green leaves and a textured brown trunk, placed in a white spherical pot on a black square base.", size=[0.80, 0.80, 1.65], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="A modern ottoman with a sleek design, featuring a rectangular shape and rounded edges. It has a dark gray or black cushioned top and a lighter gray base with a wavy texture along the edge.", size=[0.65, 1.10, 0.42], placements=[AssetInstance() for _ in range(1)])
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

tv_stand[0].position = [8.279464963375958, 2.7261132670966206, 0.275]
tv_stand[0].rotation = [0, 0, 0]
wine_cabinet[0].position = [7.833549626435189, 3.9586393741503536, 1.0]
wine_cabinet[0].rotation = [0, 0, 0]
l_shaped_sofa[0].position = [5.328745594455744, 0.16964782873966985, 0.425]
l_shaped_sofa[0].rotation = [0, 0, 0]
washing_machine[0].position = [4.642949207150464, 3.3540440179704083, 0.425]
washing_machine[0].rotation = [0, 0, 0]
potted_plant[0].position = [0.6897843171778746, 3.4382217284597765, 0.825]
potted_plant[0].rotation = [0, 0, 0]
coffee_table[0].position = [2.2449631250417554, 0.9968451495689212, 0.21]
coffee_table[0].rotation = [0, 0, 0]
sideboard[0].position = [3.061570905452444, 3.1713501997770135, 0.4]
sideboard[0].rotation = [0, 0, 0]
tv_stand[0].position = [8.279464963375958, 2.7261132670966206, 0.275]
tv_stand[0].rotation = [0, 0, 0]
wine_cabinet[0].position = [7.833549626435189, 3.9586393741503536, 1.0]
wine_cabinet[0].rotation = [0, 0, 0]
l_shaped_sofa[0].position = [5.328745594455744, 0.16964782873966985, 0.425]
l_shaped_sofa[0].rotation = [0, 0, 0]
washing_machine[0].position = [4.642949207150464, 3.3540440179704083, 0.425]
washing_machine[0].rotation = [0, 0, 0]
potted_plant[0].position = [0.6897843171778746, 3.4382217284597765, 0.825]
potted_plant[0].rotation = [0, 0, 0]
coffee_table[0].position = [2.2449631250417554, 0.9968451495689212, 0.21]
coffee_table[0].rotation = [0, 0, 0]
sideboard[0].position = [3.061570905452444, 3.1713501997770135, 0.4]
sideboard[0].rotation = [0, 0, 0]

solver.constraints = []

# Keep all furniture in the larger western room; leave the narrow eastern
# corridor and every doorway unobstructed. All coordinates are box centers.
# The sofa is low enough to sit beneath the large western window.
l_shaped_sofa[0].position = [0.825, 1.45, 0.425]
l_shaped_sofa[0].rotation = [0, 0, 0]

coffee_table[0].position = [2.65, 1.45, 0.21]
coffee_table[0].rotation = [0, 0, 0]

# The plant lies directly along the sofa's forward axis.
potted_plant[0].position = [4.65, 1.45, 0.825]
potted_plant[0].rotation = [0, 0, radians(180)]

# Put the media console on the southern wall, facing into the room.
tv_stand[0].position = [3.25, 0.21, 0.275]
tv_stand[0].rotation = [0, 0, radians(90)]

# Northern storage avoids both the small window and the northern doors.
wine_cabinet[0].position = [1.65, 3.76, 1.00]
wine_cabinet[0].rotation = [0, 0, radians(270)]

sideboard[0].position = [3.35, 3.735, 0.40]
sideboard[0].rotation = [0, 0, radians(270)]

# The washer occupies the eastern wall below the corridor junction.
# Its front faces west, with clear loading space in front.
washing_machine[0].position = [5.195, 2.30, 0.425]
washing_machine[0].rotation = [0, 0, radians(180)]

# Prioritize the chosen, nonoverlapping centers. Fixed reference instances
# are constraint anchors only, not additional scene furniture.
for placed_instance in (
    l_shaped_sofa[0],
    coffee_table[0],
    potted_plant[0],
    tv_stand[0],
    wine_cabinet[0],
    sideboard[0],
    washing_machine[0],
):
    solver.distance_constraint(
        placed_instance,
        AssetInstance(position=list(placed_instance.position)),
        0,
        0,
        weight=10,
    )

# Preserve the principal seating relationship and aligned coffee table.
solver.point_towards(l_shaped_sofa[0], potted_plant[0])
solver.align_with(coffee_table[0], l_shaped_sofa[0])
solver.point_towards(potted_plant[0], l_shaped_sofa[0])

# Explicit inward-facing orientations for wall furniture.
solver.align_with(tv_stand[0], l_shaped_sofa[0], angle=90)
solver.align_with(wine_cabinet[0], l_shaped_sofa[0], angle=270)
solver.align_with(sideboard[0], l_shaped_sofa[0], angle=270)
solver.align_with(washing_machine[0], l_shaped_sofa[0], angle=180)

solver.against_wall(l_shaped_sofa[0], walls[0])
solver.against_wall(tv_stand[0], walls[1])
solver.against_wall(wine_cabinet[0], walls[5])
solver.against_wall(sideboard[0], walls[5])
solver.against_wall(washing_machine[0], walls[2])

# All supplied objects are floor-standing, including the ottoman-style
# coffee table and the large plant; no on_top_of constraints are needed.

solver.constraints = []
tv_stand[0].position = [3.25, 0.20999999344348907, 0.2750000059604645]
tv_stand[0].rotation = [0, 0, 1.5707963639175542]
tv_stand[0].optimize = 2
potted_plant[0].position = [4.650000095367432, 1.4500000476837158, 0.824999988079071]
potted_plant[0].rotation = [0, 0, -3.1290262823329655]
potted_plant[0].optimize = 2
washing_machine[0].position = [5.190699577331543, 2.299999952316284, 0.42500001192092896]
washing_machine[0].rotation = [0, 0, -3.1415926029974233]
washing_machine[0].optimize = 2
wine_cabinet[0].position = [1.649999976158142, 3.759999990463257, 1.0]
wine_cabinet[0].rotation = [0, 0, -1.5707962815234624]
wine_cabinet[0].optimize = 2
l_shaped_sofa[0].position = [0.824999988079071, 1.4500000476837158, 0.42500001192092896]
l_shaped_sofa[0].rotation = [0, 0, 2.7270394984981857e-08]
l_shaped_sofa[0].optimize = 2
coffee_table[0].position = [2.6500000953674316, 1.4500000476837158, 0.20999999344348907]
coffee_table[0].rotation = [0, 0, 2.269069016452411e-08]
coffee_table[0].optimize = 2
sideboard[0].position = [3.3499999046325684, 3.7350001335144043, 0.4000000059604645]
sideboard[0].rotation = [0, 0, -1.570796300698664]
sideboard[0].optimize = 2

