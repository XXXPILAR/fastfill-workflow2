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
    Wall(corner1=[0.00, 0.52, 0.00], corner2=[0.00, 0.47, 0.00]),
    Wall(corner1=[0.00, 0.47, 0.00], corner2=[0.01, 0.42, 0.00]),
    Wall(corner1=[0.01, 0.42, 0.00], corner2=[0.02, 0.37, 0.00]),
    Wall(corner1=[0.02, 0.37, 0.00], corner2=[0.03, 0.32, 0.00]),
    Wall(corner1=[0.03, 0.32, 0.00], corner2=[0.05, 0.28, 0.00]),
    Wall(corner1=[0.05, 0.28, 0.00], corner2=[0.07, 0.24, 0.00]),
    Wall(corner1=[0.07, 0.24, 0.00], corner2=[0.10, 0.20, 0.00]),
    Wall(corner1=[0.10, 0.20, 0.00], corner2=[0.13, 0.16, 0.00]),
    Wall(corner1=[0.13, 0.16, 0.00], corner2=[0.16, 0.12, 0.00]),
    Wall(corner1=[0.16, 0.12, 0.00], corner2=[0.20, 0.09, 0.00]),
    Wall(corner1=[0.20, 0.09, 0.00], corner2=[0.24, 0.07, 0.00]),
    Wall(corner1=[0.24, 0.07, 0.00], corner2=[0.29, 0.04, 0.00]),
    Wall(corner1=[0.29, 0.04, 0.00], corner2=[0.33, 0.02, 0.00]),
    Wall(corner1=[0.33, 0.02, 0.00], corner2=[0.38, 0.01, 0.00]),
    Wall(corner1=[0.38, 0.01, 0.00], corner2=[0.43, 0.00, 0.00]),
    Wall(corner1=[0.43, 0.00, 0.00], corner2=[6.50, 0.00, 0.00]),
    Wall(corner1=[6.50, 0.00, 0.00], corner2=[6.50, 3.00, 0.00]),
    Wall(corner1=[6.50, 3.00, 0.00], corner2=[0.00, 3.00, 0.00]),
    Wall(corner1=[0.00, 3.00, 0.00], corner2=[0.00, 0.52, 0.00]),
    Wall(corner1=[0.00, 0.52, 0.00], corner2=[0.00, 0.52, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
round_end_table = Assets(description="A modern floor lamp with a cylindrical lampshade and three slender legs that converge at the base.", size=[0.55, 0.55, 1.55], placements=[AssetInstance() for _ in range(1)])
three_seat_sofa = Assets(description="A brown leather sofa with multiple cushions and decorative pillows arranged on it. The sofa has a classic design with rolled armrests and a segmented backrest.", size=[0.95, 2.30, 0.90], placements=[AssetInstance() for _ in range(1)])
sideboard = Assets(description="A wooden wardrobe with two doors and a simple design. It features a clean and minimalist appearance suitable for various interior styles.", size=[0.45, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
dining_chair = Assets(description="A modern armchair with a sleek design, featuring a curved backrest and armrests upholstered in black fabric or leather. The frame is made of metal with a matte finish, providing sturdy support for the seat.", size=[0.70, 0.65, 0.82], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="A modern, minimalist table with two circular platforms connected by a central support. It features a sleek black finish and holds various small objects such as a bottle, a cup, and a rectangular block.", size=[0.60, 1.00, 0.42], placements=[AssetInstance() for _ in range(1)])

round_end_table[0].instance_id = 'round_end_table_0'
three_seat_sofa[0].instance_id = 'three_seat_sofa_0'
sideboard[0].instance_id = 'sideboard_0'
dining_chair[0].instance_id = 'dining_chair_0'
coffee_table[0].instance_id = 'coffee_table_0'
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
walls[14].instance_id = 'walls_14'
walls[15].instance_id = 'walls_15'
walls[16].instance_id = 'walls_16'
walls[17].instance_id = 'walls_17'
walls[18].instance_id = 'walls_18'
walls[19].instance_id = 'walls_19'

round_end_table[0].position = [5.877337234405304, 0.09180419726695788, 0.775]
round_end_table[0].rotation = [0, 0, 0]
three_seat_sofa[0].position = [3.7420847454148265, 1.2481156435023588, 0.45]
three_seat_sofa[0].rotation = [0, 0, 0]
sideboard[0].position = [0.08439405420040627, 2.3701732201460146, 0.9]
sideboard[0].rotation = [0, 0, 0]
dining_chair[0].position = [4.517618084213493, 1.762955913097235, 0.41]
dining_chair[0].rotation = [0, 0, 0]
coffee_table[0].position = [1.3379209911005228, 0.5998536710846455, 0.21]
coffee_table[0].rotation = [0, 0, 0]
round_end_table[0].position = [5.877337234405304, 0.09180419726695788, 0.775]
round_end_table[0].rotation = [0, 0, 0]
three_seat_sofa[0].position = [3.7420847454148265, 1.2481156435023588, 0.45]
three_seat_sofa[0].rotation = [0, 0, 0]
sideboard[0].position = [0.08439405420040627, 2.3701732201460146, 0.9]
sideboard[0].rotation = [0, 0, 0]
dining_chair[0].position = [4.517618084213493, 1.762955913097235, 0.41]
dining_chair[0].rotation = [0, 0, 0]
coffee_table[0].position = [1.3379209911005228, 0.5998536710846455, 0.21]
coffee_table[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the sofa along the upper wall, facing south into the seating area.
three_seat_sofa[0].position = [3.30, 2.525, 0.45]
three_seat_sofa[0].rotation = [0, 0, radians(-90)]

# Place the coffee table parallel to and directly in front of the sofa.
# Their center separation is 0.975 m, leaving approximately 0.20 m
# between their bounding-box edges.
coffee_table[0].position = [3.30, 1.55, 0.21]
coffee_table[0].rotation = [0, 0, radians(-90)]

# Place the chair opposite the sofa to form a compact conversation group.
dining_chair[0].position = [3.30, 0.70, 0.41]
dining_chair[0].rotation = [0, 0, radians(90)]

# Place the floor lamp beside the sofa without intersecting its arm.
round_end_table[0].position = [4.85, 2.50, 0.775]
round_end_table[0].rotation = [0, 0, radians(180)]

# Place the sideboard against the right wall, facing into the room.
sideboard[0].position = [6.275, 1.05, 0.90]
sideboard[0].rotation = [0, 0, radians(180)]


# Sofa: wall contact is the primary positional requirement, and it must
# face the coffee table.
solver.against_wall(three_seat_sofa[0], walls[17])
solver.point_towards(three_seat_sofa[0], coffee_table[0])
solver.distance_constraint(
    three_seat_sofa[0],
    AssetInstance(position=[3.30, 2.525, 0.45]),
    0,
    0,
    weight=0.1,
)

# Coffee table: account for both assets' half-depths when translating the
# requested maximum 0.30 m edge gap into a center-distance constraint.
# With these rotations, the minimum non-overlapping center distance is
# about 0.775 m and a 0.30 m gap corresponds to about 1.075 m.
solver.distance_constraint(
    coffee_table[0], three_seat_sofa[0], 0.775, 1.075, weight=10
)
solver.align_with(coffee_table[0], three_seat_sofa[0])
solver.distance_constraint(
    coffee_table[0],
    AssetInstance(position=[3.30, 1.55, 0.21]),
    0,
    0,
    weight=0.1,
)

# Chair: keep it across from the table with sufficient clearance and orient
# it toward the center of the seating arrangement.
solver.distance_constraint(
    dining_chair[0], coffee_table[0], 0.75, 1.05, weight=10
)
solver.point_towards(dining_chair[0], coffee_table[0])
solver.distance_constraint(
    dining_chair[0],
    AssetInstance(position=[3.30, 0.70, 0.41]),
    0,
    0,
    weight=0.1,
)

# Floor lamp: keep it close to the sofa as a functional reading lamp while
# preserving enough center distance to prevent overlap.
solver.distance_constraint(
    round_end_table[0], three_seat_sofa[0], 1.40, 1.75, weight=10
)
solver.point_towards(round_end_table[0], three_seat_sofa[0])
solver.distance_constraint(
    round_end_table[0],
    AssetInstance(position=[4.85, 2.50, 0.775]),
    0,
    0,
    weight=0.1,
)

# Sideboard: prioritize contact with the right wall and orient its front
# toward the room's central furniture group.
solver.against_wall(sideboard[0], walls[16])
solver.point_towards(sideboard[0], coffee_table[0])
solver.distance_constraint(
    sideboard[0],
    AssetInstance(position=[6.275, 1.05, 0.90]),
    0,
    0,
    weight=0.1,
)

solver.constraints = []
sideboard[0].position = [6.27500057220459, 1.0499999523162842, 0.8999999761581421]
sideboard[0].rotation = [0, 0, -3.1415926073969023]
sideboard[0].optimize = 2
round_end_table[0].position = [4.849999904632568, 2.5, 0.7749999761581421]
round_end_table[0].rotation = [0, 0, -3.1290262823329655]
round_end_table[0].optimize = 2
three_seat_sofa[0].position = [3.299999952316284, 2.5250000953674316, 0.44999998807907104]
three_seat_sofa[0].rotation = [0, 0, -1.5707963360531456]
three_seat_sofa[0].optimize = 2
coffee_table[0].position = [3.299999952316284, 1.5499999523162842, 0.20999999344348907]
coffee_table[0].rotation = [0, 0, -1.5707962147894188]
coffee_table[0].optimize = 2
dining_chair[0].position = [3.299999952316284, 0.699999988079071, 0.4099999964237213]
dining_chair[0].rotation = [0, 0, 1.5833626980517244]
dining_chair[0].optimize = 2

