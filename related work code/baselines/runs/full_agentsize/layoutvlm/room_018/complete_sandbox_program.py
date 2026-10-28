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
potted_plant = Assets(description="A potted plant with large green leaves in a white pot, placed on a black square base.", size=[0.65, 0.65, 1.35], placements=[AssetInstance() for _ in range(1)])
l_shaped_sofa = Assets(description="A modern sectional sofa with a sleek design, featuring a combination of tufted and plain cushions. It has a dark brown leather or faux leather upholstery and black legs.", size=[2.00, 2.80, 0.85], placements=[AssetInstance() for _ in range(1)])
sideboard = Assets(description="A modern sideboard with a combination of wooden and white panels. It features two drawers on the top, two cabinet doors on the bottom, and an open shelf in the middle displaying various kitchenware items. The sideboard has a sleek design with thin legs.", size=[0.42, 1.20, 1.05], placements=[AssetInstance() for _ in range(1)])
floor_lamp = Assets(description="A sleek black floor lamp with a cylindrical shade and a curved base.", size=[0.40, 0.40, 1.70], placements=[AssetInstance() for _ in range(1)])
tv_stand = Assets(description="A sleek, modern media console with a wooden finish and a combination of dark gray and white panels. It features two drawers on the right side and a cabinet on the left side, supported by thin legs.", size=[0.42, 1.60, 0.60], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="A pair of modern side tables with wooden legs and hexagonal tabletops. One table holds a potted plant while the other has decorative vases.", size=[0.65, 1.20, 0.55], placements=[AssetInstance() for _ in range(1)])
plant_stand = Assets(description="A modern plant stand with a circular wooden top supporting a potted plant. The stand has four slender legs made of wood and a metal ring near the base for stability.", size=[0.45, 0.45, 1.00], placements=[AssetInstance() for _ in range(1)])

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

potted_plant[0].position = [1.8564465594541528, 2.223052069790752, 0.675]
potted_plant[0].rotation = [0, 0, 0]
l_shaped_sofa[0].position = [2.370477106755893, 1.1646534105615, 0.425]
l_shaped_sofa[0].rotation = [0, 0, 0]
sideboard[0].position = [0.9210414090614649, 5.699799676194691, 0.525]
sideboard[0].rotation = [0, 0, 0]
floor_lamp[0].position = [1.0244844983578252, 1.826607835377104, 0.85]
floor_lamp[0].rotation = [0, 0, 0]
tv_stand[0].position = [2.4706268136259455, 1.1367985793206368, 0.3]
tv_stand[0].rotation = [0, 0, 0]
coffee_table[0].position = [1.5672604902464982, 5.698942795461557, 0.275]
coffee_table[0].rotation = [0, 0, 0]
plant_stand[0].position = [3.366092348643111, 2.2977690971555784, 0.5]
plant_stand[0].rotation = [0, 0, 0]
potted_plant[0].position = [1.8564465594541528, 2.223052069790752, 0.675]
potted_plant[0].rotation = [0, 0, 0]
l_shaped_sofa[0].position = [2.370477106755893, 1.1646534105615, 0.425]
l_shaped_sofa[0].rotation = [0, 0, 0]
sideboard[0].position = [0.9210414090614649, 5.699799676194691, 0.525]
sideboard[0].rotation = [0, 0, 0]
floor_lamp[0].position = [1.0244844983578252, 1.826607835377104, 0.85]
floor_lamp[0].rotation = [0, 0, 0]
tv_stand[0].position = [2.4706268136259455, 1.1367985793206368, 0.3]
tv_stand[0].rotation = [0, 0, 0]
coffee_table[0].position = [1.5672604902464982, 5.698942795461557, 0.275]
coffee_table[0].rotation = [0, 0, 0]
plant_stand[0].position = [3.366092348643111, 2.2977690971555784, 0.5]
plant_stand[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed reference points preserve the intended furniture zones while allowing the
# solver to make small feasibility adjustments.
sofa_anchor = AssetInstance(position=[2.55, 2.45, 0.425])
plant_stand_anchor = AssetInstance(position=[0.55, 1.75, 0.50])
coffee_table_anchor = AssetInstance(position=[1.15, 2.45, 0.275])
tv_stand_anchor = AssetInstance(position=[0.21, 3.25, 0.30])
sideboard_anchor = AssetInstance(position=[1.00, 5.55, 0.525])
floor_lamp_anchor = AssetInstance(position=[1.20, 4.00, 0.85])
potted_plant_anchor = AssetInstance(position=[1.80, 4.65, 0.675])

# The sectional occupies the right side of the main room, leaving the two door
# approaches unobstructed. Its front faces generally west toward the plant stand.
l_shaped_sofa[0].position = [2.55, 2.45, 0.425]
l_shaped_sofa[0].rotation = [0, 0, radians(180)]

# The plant stand is opposite the sofa without blocking the left-side circulation.
plant_stand[0].position = [0.55, 1.75, 0.50]
plant_stand[0].rotation = [0, 0, radians(20)]

# The coffee table sits between the sofa and plant stand, with clearance from both.
coffee_table[0].position = [1.15, 2.45, 0.275]
coffee_table[0].rotation = [0, 0, 0]

# The media console uses the uninterrupted portion of the west wall.
tv_stand[0].position = [0.21, 3.25, 0.30]
tv_stand[0].rotation = [0, 0, 0]

# Rotating the sideboard places its shallow dimension against the north wall of
# the upper alcove. This location remains clear of the door on the alcove's west wall.
sideboard[0].position = [1.00, 5.55, 0.525]
sideboard[0].rotation = [0, 0, radians(-90)]

# The lamp occupies the transition beside the seating area without overlapping it.
floor_lamp[0].position = [1.20, 4.00, 0.85]
floor_lamp[0].rotation = [0, 0, radians(180)]

# The larger plant decorates the upper alcove while retaining access to both doors.
potted_plant[0].position = [1.80, 4.65, 0.675]
potted_plant[0].rotation = [0, 0, radians(180)]

# High-priority position constraints maintain the non-overlapping layout and keep
# the central strip in front of the south door clear.
solver.distance_constraint(
    l_shaped_sofa[0], sofa_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    plant_stand[0], plant_stand_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    coffee_table[0], coffee_table_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    floor_lamp[0], floor_lamp_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    potted_plant[0], potted_plant_anchor, 0, 0, weight=10
)

# Wall constraints encode the required wall relationships. The sideboard is
# attached to the north wall, and the TV stand is attached to the west wall.
solver.against_wall(sideboard[0], walls[5])
solver.distance_constraint(
    sideboard[0], sideboard_anchor, 0, 0, weight=10
)

solver.against_wall(tv_stand[0], walls[8])
solver.distance_constraint(
    tv_stand[0], tv_stand_anchor, 0, 0, weight=10
)

# The sofa and plant stand face one another as requested.
solver.point_towards(l_shaped_sofa[0], plant_stand[0])
solver.point_towards(plant_stand[0], l_shaped_sofa[0])

# The coffee table and media console orient toward the seating group.
solver.point_towards(coffee_table[0], l_shaped_sofa[0])
solver.point_towards(tv_stand[0], l_shaped_sofa[0])

# The sideboard faces inward from the north wall. The remaining decorative assets
# receive stable orientations consistent with the principal furniture.
solver.point_towards(sideboard[0], coffee_table[0])
solver.align_with(floor_lamp[0], l_shaped_sofa[0])
solver.point_towards(potted_plant[0], coffee_table[0])

solver.constraints = []
sideboard[0].position = [1.6080328226089478, 5.4312520027160645, 0.5249999761581421]
sideboard[0].rotation = [0, 0, -1.5872163849635608]
sideboard[0].optimize = 2
l_shaped_sofa[0].position = [2.357668399810791, 2.450000047683716, 0.42500001192092896]
l_shaped_sofa[0].rotation = [0, 0, -2.9162082258511854]
l_shaped_sofa[0].optimize = 2
plant_stand[0].position = [0.550000011920929, 1.75, 0.5]
plant_stand[0].rotation = [0, 0, 0.3616321980963252]
plant_stand[0].optimize = 2
coffee_table[0].position = [1.149999976158142, 2.450000047683716, 0.2750000059604645]
coffee_table[0].rotation = [0, 0, 0.0157079639172164]
coffee_table[0].optimize = 2
tv_stand[0].position = [0.5238858461380005, 4.1030120849609375, 0.30000001192092896]
tv_stand[0].rotation = [0, 0, -0.032540644634822764]
tv_stand[0].optimize = 2
floor_lamp[0].position = [1.2000000476837158, 4.0, 0.8500000238418579]
floor_lamp[0].rotation = [0, 0, -2.916617616462814]
floor_lamp[0].optimize = 2
potted_plant[0].position = [1.7659265995025635, 4.615903377532959, 0.675000011920929]
potted_plant[0].rotation = [0, 0, -2.107450850501451]
potted_plant[0].optimize = 2

