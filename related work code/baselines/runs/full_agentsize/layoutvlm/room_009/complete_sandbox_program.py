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
    Wall(corner1=[0.00, 0.40, 0.00], corner2=[0.20, 0.40, 0.00]),
    Wall(corner1=[0.20, 0.40, 0.00], corner2=[0.20, 0.00, 0.00]),
    Wall(corner1=[0.20, 0.00, 0.00], corner2=[4.37, 0.00, 0.00]),
    Wall(corner1=[4.37, 0.00, 0.00], corner2=[4.37, 4.03, 0.00]),
    Wall(corner1=[4.37, 4.03, 0.00], corner2=[0.00, 4.02, 0.00]),
    Wall(corner1=[0.00, 4.02, 0.00], corner2=[0.00, 3.64, 0.00]),
    Wall(corner1=[0.00, 3.64, 0.00], corner2=[0.00, 3.64, 0.00]),
    Wall(corner1=[0.00, 3.64, 0.00], corner2=[0.00, 0.40, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
three_seat_sofa = Assets(description="A luxurious dark brown sofa with a glossy finish, featuring decorative pillows in white and beige. It has a classic design with armrests and a backrest that curves slightly for comfort.", size=[0.95, 2.25, 0.90], placements=[AssetInstance() for _ in range(1)])
tv_stand = Assets(description="A sleek media console with a modern design, featuring a combination of black and beige panels, drawers, and doors. It has thin legs for support.", size=[0.45, 1.80, 0.65], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="A dark wooden coffee table with ornate legs and a rectangular tabletop. The table has a polished finish and features decorative carvings along its edges.", size=[0.65, 1.20, 0.45], placements=[AssetInstance() for _ in range(1)])
lounge_chair = Assets(description="A modern armchair with a sleek design, upholstered in a rich red fabric and supported by black legs.", size=[0.85, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])

three_seat_sofa[0].instance_id = 'three_seat_sofa_0'
tv_stand[0].instance_id = 'tv_stand_0'
coffee_table[0].instance_id = 'coffee_table_0'
lounge_chair[0].instance_id = 'lounge_chair_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

three_seat_sofa[0].position = [1.9951381390406975, 1.0044245819025674, 0.45]
three_seat_sofa[0].rotation = [0, 0, 0]
tv_stand[0].position = [3.181589607675907, 1.2143389510512372, 0.325]
tv_stand[0].rotation = [0, 0, 0]
coffee_table[0].position = [1.7174320622964157, 0.39382516794726713, 0.225]
coffee_table[0].rotation = [0, 0, 0]
lounge_chair[0].position = [3.285674348884392, 3.9882106606133676, 0.45]
lounge_chair[0].rotation = [0, 0, 0]
three_seat_sofa[0].position = [1.9951381390406975, 1.0044245819025674, 0.45]
three_seat_sofa[0].rotation = [0, 0, 0]
tv_stand[0].position = [3.181589607675907, 1.2143389510512372, 0.325]
tv_stand[0].rotation = [0, 0, 0]
coffee_table[0].position = [1.7174320622964157, 0.39382516794726713, 0.225]
coffee_table[0].rotation = [0, 0, 0]
lounge_chair[0].position = [3.285674348884392, 3.9882106606133676, 0.45]
lounge_chair[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the sofa and media console on opposing walls, with the coffee table
# centered between them. The lounge chair sits along the lower wall and faces
# the coffee table, leaving clear circulation space around the seating group.

three_seat_sofa[0].position = [0.475, 2.35, 0.45]
three_seat_sofa[0].rotation = [0, 0, radians(0)]

tv_stand[0].position = [4.145, 2.35, 0.325]
tv_stand[0].rotation = [0, 0, radians(180)]

coffee_table[0].position = [2.20, 2.35, 0.225]
coffee_table[0].rotation = [0, 0, radians(0)]

lounge_chair[0].position = [2.20, 0.425, 0.45]
lounge_chair[0].rotation = [0, 0, radians(90)]

# Fixed anchor preserves the coffee table's central role in the conversation area.
coffee_table_anchor = AssetInstance(position=[2.20, 2.35, 0.225])

# Position constraints are listed before secondary spacing constraints so the
# principal wall relationships and central table location take precedence.
solver.against_wall(three_seat_sofa[0], walls[7])
solver.against_wall(tv_stand[0], walls[3])
solver.distance_constraint(
    coffee_table[0], coffee_table_anchor,
    min_distance=0.0, max_distance=0.0, weight=10
)
solver.against_wall(lounge_chair[0], walls[2])

# Maintain practical separation between the central table and each surrounding
# furnishing. These center distances account for their bounding-box dimensions.
solver.distance_constraint(
    three_seat_sofa[0], coffee_table[0],
    min_distance=1.60, max_distance=1.90, weight=10
)
solver.distance_constraint(
    tv_stand[0], coffee_table[0],
    min_distance=1.80, max_distance=2.10, weight=10
)
solver.distance_constraint(
    lounge_chair[0], coffee_table[0],
    min_distance=1.75, max_distance=2.10, weight=10
)

# Orient the seating and media console inward. In particular, the lounge chair
# explicitly faces the coffee table as required.
solver.point_towards(lounge_chair[0], coffee_table[0])
solver.point_towards(three_seat_sofa[0], coffee_table[0])
solver.point_towards(tv_stand[0], coffee_table[0])
solver.align_with(coffee_table[0], three_seat_sofa[0], angle=0)

solver.constraints = []
three_seat_sofa[0].position = [0.4926121234893799, 2.3499999046325684, 0.44999998807907104]
three_seat_sofa[0].rotation = [0, 0, 9.802755558004204e-07]
three_seat_sofa[0].optimize = 2
coffee_table[0].position = [2.200000047683716, 2.3499999046325684, 0.22499999403953552]
coffee_table[0].rotation = [0, 0, 1.4016117918301899e-06]
coffee_table[0].optimize = 2
tv_stand[0].position = [4.147959232330322, 2.3498456478118896, 0.32499998807907104]
tv_stand[0].rotation = [0, 0, -3.141576082083527]
tv_stand[0].optimize = 2
lounge_chair[0].position = [0.8687961101531982, 0.7437834143638611, 0.44999998807907104]
lounge_chair[0].rotation = [0, 0, 1.456244773758221]
lounge_chair[0].optimize = 2

