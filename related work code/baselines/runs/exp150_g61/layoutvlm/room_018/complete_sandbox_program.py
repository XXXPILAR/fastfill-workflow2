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
    Wall(corner1=[1.79, 4.17, 0.00], corner2=[1.79, 4.29, 0.00]),
    Wall(corner1=[1.79, 4.29, 0.00], corner2=[2.21, 4.29, 0.00]),
    Wall(corner1=[2.21, 4.29, 0.00], corner2=[2.21, 5.64, 0.00]),
    Wall(corner1=[2.21, 5.64, 0.00], corner2=[1.79, 5.64, 0.00]),
    Wall(corner1=[1.79, 5.64, 0.00], corner2=[1.79, 5.76, 0.00]),
    Wall(corner1=[1.79, 5.76, 0.00], corner2=[0.32, 5.76, 0.00]),
    Wall(corner1=[0.32, 5.76, 0.00], corner2=[0.32, 4.17, 0.00]),
    Wall(corner1=[0.32, 4.17, 0.00], corner2=[0.00, 4.17, 0.00]),
    Wall(corner1=[0.00, 4.17, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.65, 0.00, 0.00]),
    Wall(corner1=[3.65, 0.00, 0.00], corner2=[3.65, 4.17, 0.00]),
    Wall(corner1=[3.65, 4.17, 0.00], corner2=[1.79, 4.17, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
potted_plant = Assets(description="A potted plant with large green leaves in a white pot, placed on a black square base.", size=[0.65, 0.65, 1.50], placements=[AssetInstance() for _ in range(1)])
l_shaped_sofa = Assets(description="A modern sectional sofa with a sleek design, featuring a combination of tufted and plain cushions. It has a dark brown leather or faux leather upholstery and black legs.", size=[1.70, 2.70, 0.85], placements=[AssetInstance() for _ in range(1)])
sideboard = Assets(description="A modern sideboard with a combination of wooden and white panels. It features two drawers on the top, two cabinet doors on the bottom, and an open shelf in the middle displaying various kitchenware items. The sideboard has a sleek design with thin legs.", size=[0.40, 1.40, 1.10], placements=[AssetInstance() for _ in range(1)])
floor_lamp = Assets(description="A sleek black floor lamp with a cylindrical shade and a curved base.", size=[0.55, 0.45, 1.65], placements=[AssetInstance() for _ in range(1)])
tv_stand = Assets(description="A sleek, modern media console with a wooden finish and a combination of dark gray and white panels. It features two drawers on the right side and a cabinet on the left side, supported by thin legs.", size=[0.40, 1.60, 0.55], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="A pair of modern side tables with wooden legs and hexagonal tabletops. One table holds a potted plant while the other has decorative vases.", size=[0.65, 1.05, 0.45], placements=[AssetInstance() for _ in range(1)])
plant_stand = Assets(description="A modern plant stand with a circular wooden top supporting a potted plant. The stand has four slender legs made of wood and a metal ring near the base for stability.", size=[0.45, 0.45, 0.95], placements=[AssetInstance() for _ in range(1)])

potted_plant[0].instance_id = 'potted_plant_0'
l_shaped_sofa[0].instance_id = 'l_shaped_sofa_0'
sideboard[0].instance_id = 'sideboard_0'
floor_lamp[0].instance_id = 'floor_lamp_0'
tv_stand[0].instance_id = 'tv_stand_0'
coffee_table[0].instance_id = 'coffee_table_0'
plant_stand[0].instance_id = 'plant_stand_0'
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

potted_plant[0].position = [2.4255636064481254, 2.999352607055475, 0.75]
potted_plant[0].rotation = [0, 0, 0]
l_shaped_sofa[0].position = [0.9678947520411724, 3.1349252499613405, 0.425]
l_shaped_sofa[0].rotation = [0, 0, 0]
sideboard[0].position = [3.495672540398533, 1.9509212045348, 0.55]
sideboard[0].rotation = [0, 0, 0]
floor_lamp[0].position = [1.436831404653803, 0.8761138302848025, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
tv_stand[0].position = [3.381041881158662, 1.6141136648579508, 0.275]
tv_stand[0].rotation = [0, 0, 0]
coffee_table[0].position = [1.7425490531442323, 1.8625273531129383, 0.225]
coffee_table[0].rotation = [0, 0, 0]
plant_stand[0].position = [2.4840265868059825, 3.367843566988378, 0.475]
plant_stand[0].rotation = [0, 0, 0]
potted_plant[0].position = [2.4255636064481254, 2.999352607055475, 0.75]
potted_plant[0].rotation = [0, 0, 0]
l_shaped_sofa[0].position = [0.9678947520411724, 3.1349252499613405, 0.425]
l_shaped_sofa[0].rotation = [0, 0, 0]
sideboard[0].position = [3.495672540398533, 1.9509212045348, 0.55]
sideboard[0].rotation = [0, 0, 0]
floor_lamp[0].position = [1.436831404653803, 0.8761138302848025, 0.825]
floor_lamp[0].rotation = [0, 0, 0]
tv_stand[0].position = [3.381041881158662, 1.6141136648579508, 0.275]
tv_stand[0].rotation = [0, 0, 0]
coffee_table[0].position = [1.7425490531442323, 1.8625273531129383, 0.225]
coffee_table[0].rotation = [0, 0, 0]
plant_stand[0].position = [2.4840265868059825, 3.367843566988378, 0.475]
plant_stand[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the seating along the west wall, facing the plant stand across
# the room. Keep the southern entrance apron (x=0.51..2.83) unobstructed.
l_shaped_sofa[0].position = [0.85, 2.50, 0.425]
l_shaped_sofa[0].rotation = [0, 0, 0]

# Shallow storage occupies the east wall without blocking either entrance.
sideboard[0].position = [3.45, 3.45, 0.55]
sideboard[0].rotation = [0, 0, radians(180)]

tv_stand[0].position = [3.45, 1.40, 0.275]
tv_stand[0].rotation = [0, 0, radians(180)]

# Leave 0.40 m between the sofa's bounding box and the coffee table.
coffee_table[0].position = [2.425, 2.50, 0.225]
coffee_table[0].rotation = [0, 0, 0]

# This stand sits between the two east-wall cabinets, directly ahead
# of the sofa, with a separate, non-overlapping footprint.
plant_stand[0].position = [3.40, 2.50, 0.475]
plant_stand[0].rotation = [0, 0, radians(180)]

# Use the eastern side of the northern alcove for greenery and lighting.
# Their footprints leave the approach to the door at (0.32, 5.10) clear.
potted_plant[0].position = [1.80, 4.65, 0.75]
potted_plant[0].rotation = [0, 0, radians(180)]

floor_lamp[0].position = [1.85, 5.40, 0.825]
floor_lamp[0].rotation = [0, 0, radians(180)]

# Preserve the carefully separated footprints and entrance clearances.
# Fixed points are constraint references only, not additional scene assets.
for placed_instance in (
    l_shaped_sofa[0],
    sideboard[0],
    tv_stand[0],
    coffee_table[0],
    plant_stand[0],
    potted_plant[0],
    floor_lamp[0],
):
    solver.distance_constraint(
        placed_instance,
        AssetInstance(position=list(placed_instance.position)),
        min_distance=0,
        max_distance=0,
        weight=10,
    )

# Required wall relationships; the orientations below face into the room.
solver.against_wall(sideboard[0], walls[10])
solver.against_wall(tv_stand[0], walls[10])
solver.against_wall(l_shaped_sofa[0], walls[8])

# Give every new instance an explicit orientation constraint.
solver.point_towards(l_shaped_sofa[0], plant_stand[0])
solver.point_towards(plant_stand[0], l_shaped_sofa[0])
solver.align_with(sideboard[0], l_shaped_sofa[0], angle=180)
solver.align_with(tv_stand[0], l_shaped_sofa[0], angle=180)
solver.align_with(coffee_table[0], l_shaped_sofa[0])
solver.align_with(potted_plant[0], sideboard[0])
solver.align_with(floor_lamp[0], sideboard[0])

# All listed assets are floor-standing, including the complete plant stand
# and coffee-table assembly; no separate tabletop objects require on_top_of.

solver.constraints = []
plant_stand[0].position = [3.4000000953674316, 2.5, 0.4749999940395355]
plant_stand[0].rotation = [0, 0, -3.1290262823329655]
plant_stand[0].optimize = 2
tv_stand[0].position = [3.445066452026367, 1.399999976158142, 0.2750000059604645]
tv_stand[0].rotation = [0, 0, -3.1413413210946866]
tv_stand[0].optimize = 2
potted_plant[0].position = [1.7999999523162842, 4.650000095367432, 0.75]
potted_plant[0].rotation = [0, 0, 3.139872586551095]
potted_plant[0].optimize = 2
l_shaped_sofa[0].position = [1.2496074438095093, 3.0392017364501953, 0.42500001192092896]
l_shaped_sofa[0].rotation = [0, 0, -0.3380397395555693]
l_shaped_sofa[0].optimize = 2
coffee_table[0].position = [2.424999952316284, 2.5, 0.22499999403953552]
coffee_table[0].rotation = [0, 0, -0.3410782400006253]
coffee_table[0].optimize = 2
sideboard[0].position = [3.4450395107269287, 3.450000047683716, 0.550000011920929]
sideboard[0].rotation = [0, 0, -3.1410209515732035]
sideboard[0].optimize = 2
floor_lamp[0].position = [1.850000023841858, 5.400000095367432, 0.824999988079071]
floor_lamp[0].rotation = [0, 0, 3.139872586551095]
floor_lamp[0].optimize = 2

