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
    Wall(corner1=[6.00, 0.00, 0.00], corner2=[6.00, 7.00, 0.00]),
    Wall(corner1=[6.00, 7.00, 0.00], corner2=[0.00, 7.00, 0.00]),
    Wall(corner1=[0.00, 7.00, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
sofa = Assets(description="extra-large modern sectional sofa in soft neutral fabric with chaise lounge", size=[2.10, 3.60, 0.85], placements=[AssetInstance() for _ in range(1)])
floor_lamp_A = Assets(description="tall modern arc floor lamp with adjustable head", size=[1.60, 0.55, 2.10], placements=[AssetInstance() for _ in range(1)])
plant_stand_A = Assets(description="decorative wooden plant stand holding large potted plant", size=[0.65, 0.65, 1.65], placements=[AssetInstance() for _ in range(1)])
media_console = Assets(description="long low modern media console with matte finish and storage cabinets", size=[0.45, 2.40, 0.55], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="large rectangular wooden coffee table with glass top and lower storage shelf", size=[0.80, 1.40, 0.42], placements=[AssetInstance() for _ in range(1)])
bookshelf_A = Assets(description="extra tall open bookshelf with wooden frame and multiple compartments", size=[0.35, 1.20, 2.40], placements=[AssetInstance() for _ in range(1)])
floor_lamp_B = Assets(description="tall modern arc floor lamp with adjustable head", size=[1.60, 0.55, 2.10], placements=[AssetInstance() for _ in range(1)])
plant_stand_B = Assets(description="decorative wooden plant stand holding large potted plant", size=[0.65, 0.65, 1.65], placements=[AssetInstance() for _ in range(1)])
bookshelf_B = Assets(description="extra tall open bookshelf with wooden frame and multiple compartments", size=[0.35, 1.20, 2.40], placements=[AssetInstance() for _ in range(1)])
accent_cabinet = Assets(description="medium-height accent cabinet with doors and drawers, wooden finish", size=[0.45, 1.10, 1.00], placements=[AssetInstance() for _ in range(1)])

sofa[0].instance_id = 'sofa_0'
floor_lamp_A[0].instance_id = 'floor_lamp_A_0'
plant_stand_A[0].instance_id = 'plant_stand_A_0'
media_console[0].instance_id = 'media_console_0'
coffee_table[0].instance_id = 'coffee_table_0'
bookshelf_A[0].instance_id = 'bookshelf_A_0'
floor_lamp_B[0].instance_id = 'floor_lamp_B_0'
plant_stand_B[0].instance_id = 'plant_stand_B_0'
bookshelf_B[0].instance_id = 'bookshelf_B_0'
accent_cabinet[0].instance_id = 'accent_cabinet_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

sofa[0].position = [0.6534102937936654, 0.8778668271440133, 0.425]
sofa[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [2.261446644661728, 6.477125656435977, 1.05]
floor_lamp_A[0].rotation = [0, 0, 0]
plant_stand_A[0].position = [3.5272180836127083, 0.08308139448598817, 0.825]
plant_stand_A[0].rotation = [0, 0, 0]
media_console[0].position = [1.2402848955161523, 5.731592325158473, 0.275]
media_console[0].rotation = [0, 0, 0]
coffee_table[0].position = [5.0488475929134085, 5.397855136836492, 0.21]
coffee_table[0].rotation = [0, 0, 0]
bookshelf_A[0].position = [4.46413788190233, 0.10679194111193513, 1.2]
bookshelf_A[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [0.4333671860161601, 5.625049569628693, 1.05]
floor_lamp_B[0].rotation = [0, 0, 0]
plant_stand_B[0].position = [1.13007101762031, 4.877917816508228, 0.825]
plant_stand_B[0].rotation = [0, 0, 0]
bookshelf_B[0].position = [1.2707326853573453, 5.2608562113522614, 1.2]
bookshelf_B[0].rotation = [0, 0, 0]
accent_cabinet[0].position = [1.7629724918813168, 6.5620080200877515, 0.5]
accent_cabinet[0].rotation = [0, 0, 0]
sofa[0].position = [0.6534102937936654, 0.8778668271440133, 0.425]
sofa[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [2.261446644661728, 6.477125656435977, 1.05]
floor_lamp_A[0].rotation = [0, 0, 0]
plant_stand_A[0].position = [3.5272180836127083, 0.08308139448598817, 0.825]
plant_stand_A[0].rotation = [0, 0, 0]
media_console[0].position = [1.2402848955161523, 5.731592325158473, 0.275]
media_console[0].rotation = [0, 0, 0]
coffee_table[0].position = [5.0488475929134085, 5.397855136836492, 0.21]
coffee_table[0].rotation = [0, 0, 0]
bookshelf_A[0].position = [4.46413788190233, 0.10679194111193513, 1.2]
bookshelf_A[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [0.4333671860161601, 5.625049569628693, 1.05]
floor_lamp_B[0].rotation = [0, 0, 0]
plant_stand_B[0].position = [1.13007101762031, 4.877917816508228, 0.825]
plant_stand_B[0].rotation = [0, 0, 0]
bookshelf_B[0].position = [1.2707326853573453, 5.2608562113522614, 1.2]
bookshelf_B[0].rotation = [0, 0, 0]
accent_cabinet[0].position = [1.7629724918813168, 6.5620080200877515, 0.5]
accent_cabinet[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the supplied boundary: x=0..6, y=0..7.
# All assets are floor-standing, including the integrated plant stands.
# The sofa faces east, with one lamp beyond each end of its long side.
layout_specs = [
    (sofa,          [1.050, 3.500, 0.425],    0),
    (floor_lamp_A,  [1.050, 1.050, 1.050],    0),
    (floor_lamp_B,  [1.050, 5.950, 1.050],    0),
    (coffee_table,  [3.050, 3.500, 0.210],    0),
    (bookshelf_A,   [5.825, 3.500, 1.200],  180),
    (media_console, [5.775, 1.300, 0.275],  180),
    (bookshelf_B,   [5.825, 5.300, 1.200],  180),
    (accent_cabinet,[3.000, 6.775, 0.500],  -90),
    (plant_stand_A, [4.650, 0.500, 0.825],   90),
    (plant_stand_B, [4.650, 6.500, 0.825],  -90),
]

for asset_group, center, heading in layout_specs:
    asset_group[0].position = list(center)
    asset_group[0].rotation = [0, 0, radians(heading)]

# Highest-priority semantic orientation: the sofa faces bookshelf_A.
solver.point_towards(sofa[0], bookshelf_A[0])
solver.point_towards(bookshelf_A[0], sofa[0])

# Preserve the calculated, non-overlapping locations. These position constraints
# also keep the lamps on opposite ends of the sofa rather than merely nearby.
# The coffee table has 0.55 m clearance from the sofa's front edge, with a
# generous circulation aisle between the table and the eastern storage wall.
for asset_group, center, heading in layout_specs:
    solver.distance_constraint(
        asset_group[0],
        AssetInstance(position=list(center)),
        min_distance=0,
        max_distance=0,
        weight=10,
    )

# Back the sofa and storage pieces against their respective walls.
solver.against_wall(sofa[0], walls[2])
solver.against_wall(bookshelf_A[0], walls[0])
solver.against_wall(media_console[0], walls[0])
solver.against_wall(bookshelf_B[0], walls[0])
solver.against_wall(accent_cabinet[0], walls[1])

# Keep the elongated lamps and table parallel to the sofa so their bounding
# boxes retain the clearances used above.
solver.align_with(floor_lamp_A[0], sofa[0])
solver.align_with(floor_lamp_B[0], sofa[0])
solver.align_with(coffee_table[0], sofa[0])

# Eastern storage faces into the room; the northern cabinet faces south.
solver.align_with(media_console[0], bookshelf_A[0])
solver.align_with(bookshelf_B[0], bookshelf_A[0])
solver.align_with(accent_cabinet[0], sofa[0], angle=-90)

# Orient the decorative plant stands inward from the south and north edges.
solver.align_with(plant_stand_A[0], sofa[0], angle=90)
solver.align_with(plant_stand_B[0], sofa[0], angle=-90)

solver.constraints = []
floor_lamp_A[0].position = [1.0499999523162842, 1.0499999523162842, 1.0499999523162842]
floor_lamp_A[0].rotation = [0, 0, 3.2366495247604005e-08]
floor_lamp_A[0].optimize = 2
accent_cabinet[0].position = [3.0, 6.774999618530273, 0.5]
accent_cabinet[0].rotation = [0, 0, -1.5707962830564535]
accent_cabinet[0].optimize = 2
floor_lamp_B[0].position = [1.0499999523162842, 5.949999809265137, 1.0499999523162842]
floor_lamp_B[0].rotation = [0, 0, 3.2366495247604005e-08]
floor_lamp_B[0].optimize = 2
bookshelf_A[0].position = [5.824999809265137, 3.5, 1.2000000476837158]
bookshelf_A[0].rotation = [0, 0, -3.141592609902724]
bookshelf_A[0].optimize = 2
plant_stand_A[0].position = [4.650000095367432, 0.5, 0.824999988079071]
plant_stand_A[0].rotation = [0, 0, 1.570796402872776]
plant_stand_A[0].optimize = 2
coffee_table[0].position = [3.049999952316284, 3.5, 0.20999999344348907]
coffee_table[0].rotation = [0, 0, 3.2366495247604005e-08]
coffee_table[0].optimize = 2
sofa[0].position = [1.0499999523162842, 3.5, 0.42500001192092896]
sofa[0].rotation = [0, 0, 2.3438404825106614e-08]
sofa[0].optimize = 2
media_console[0].position = [5.77500057220459, 1.2999999523162842, 0.2750000059604645]
media_console[0].rotation = [0, 0, -3.1415926099221174]
media_console[0].optimize = 2
plant_stand_B[0].position = [4.650000095367432, 6.5, 0.824999988079071]
plant_stand_B[0].rotation = [0, 0, -1.5707963381397874]
plant_stand_B[0].optimize = 2
bookshelf_B[0].position = [5.8249993324279785, 5.300000190734863, 1.2000000476837158]
bookshelf_B[0].rotation = [0, 0, -3.1415926099000107]
bookshelf_B[0].optimize = 2

