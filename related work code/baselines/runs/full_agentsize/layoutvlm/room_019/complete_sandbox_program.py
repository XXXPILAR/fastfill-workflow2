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
    Wall(corner1=[0.00, 0.24, 0.00], corner2=[0.79, 0.24, 0.00]),
    Wall(corner1=[0.79, 0.24, 0.00], corner2=[0.79, 0.00, 0.00]),
    Wall(corner1=[0.79, 0.00, 0.00], corner2=[3.01, 0.00, 0.00]),
    Wall(corner1=[3.01, 0.00, 0.00], corner2=[3.01, 0.24, 0.00]),
    Wall(corner1=[3.01, 0.24, 0.00], corner2=[4.75, 0.24, 0.00]),
    Wall(corner1=[4.75, 0.24, 0.00], corner2=[4.75, 5.02, 0.00]),
    Wall(corner1=[4.75, 5.02, 0.00], corner2=[0.00, 5.02, 0.00]),
    Wall(corner1=[0.00, 5.02, 0.00], corner2=[0.00, 0.24, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
tv_stand = Assets(description="A sleek, modern media console with a wooden finish and a combination of dark gray and white panels. It features two drawers on the right side and a cabinet on the left side, supported by thin legs.", size=[0.42, 1.80, 0.58], placements=[AssetInstance() for _ in range(1)])
l_shaped_sofa = Assets(description="A modern sectional sofa with a gray fabric finish, featuring a chaise lounge extension on one side. It has a sleek design with low-profile legs.", size=[1.90, 2.85, 0.82], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="A sleek, modern table with two circular levels, one slightly elevated above the other. The design is minimalist and functional.", size=[0.70, 1.05, 0.42], placements=[AssetInstance() for _ in range(1)])
armchair = Assets(description="A modern armchair with a rounded backrest and armrests, upholstered in dark fabric. It features a cushioned seat and back for comfort.", size=[0.82, 0.85, 0.80], placements=[AssetInstance() for _ in range(1)])

tv_stand[0].instance_id = 'tv_stand_0'
l_shaped_sofa[0].instance_id = 'l_shaped_sofa_0'
coffee_table[0].instance_id = 'coffee_table_0'
armchair[0].instance_id = 'armchair_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

tv_stand[0].position = [4.706845639822208, 1.7690303923190225, 0.29]
tv_stand[0].rotation = [0, 0, 0]
l_shaped_sofa[0].position = [4.363334268078359, 0.36595775506285105, 0.41]
l_shaped_sofa[0].rotation = [0, 0, 0]
coffee_table[0].position = [2.5847122994899, 2.6708624368964626, 0.21]
coffee_table[0].rotation = [0, 0, 0]
armchair[0].position = [1.855811036262871, 0.11638991574667595, 0.4]
armchair[0].rotation = [0, 0, 0]
tv_stand[0].position = [4.706845639822208, 1.7690303923190225, 0.29]
tv_stand[0].rotation = [0, 0, 0]
l_shaped_sofa[0].position = [4.363334268078359, 0.36595775506285105, 0.41]
l_shaped_sofa[0].rotation = [0, 0, 0]
coffee_table[0].position = [2.5847122994899, 2.6708624368964626, 0.21]
coffee_table[0].rotation = [0, 0, 0]
armchair[0].position = [1.855811036262871, 0.11638991574667595, 0.4]
armchair[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the seating area in the back half of the room so that the
# 2.22 m-wide doorway and its approach remain unobstructed.
tv_stand[0].position = [4.54, 3.55, 0.29]
tv_stand[0].rotation = [0, 0, radians(180)]

l_shaped_sofa[0].position = [0.95, 3.55, 0.41]
l_shaped_sofa[0].rotation = [0, 0, radians(0)]

coffee_table[0].position = [2.55, 3.45, 0.21]
coffee_table[0].rotation = [0, 0, radians(0)]

armchair[0].position = [3.35, 4.60, 0.40]
armchair[0].rotation = [0, 0, radians(-125)]

# Fixed reference points preserve the intended zones while still allowing
# the solver to make small adjustments for physical feasibility.
tv_anchor = AssetInstance(position=[4.54, 3.55, 0.29])
sofa_anchor = AssetInstance(position=[0.95, 3.55, 0.41])
table_anchor = AssetInstance(position=[2.55, 3.45, 0.21])
armchair_anchor = AssetInstance(position=[3.35, 4.60, 0.40])

# Primary position constraints: keep the four pieces in their planned zones.
solver.distance_constraint(tv_stand[0], tv_anchor, 0.0, 0.12, weight=10)
solver.distance_constraint(l_shaped_sofa[0], sofa_anchor, 0.0, 0.12, weight=10)
solver.distance_constraint(coffee_table[0], table_anchor, 0.0, 0.15, weight=10)
solver.distance_constraint(armchair[0], armchair_anchor, 0.0, 0.12, weight=10)

# Keep the large perimeter furniture against the appropriate walls.
solver.against_wall(tv_stand[0], walls[5])       # Right wall
solver.against_wall(l_shaped_sofa[0], walls[7]) # Left wall
solver.against_wall(armchair[0], walls[6])       # Top wall

# Orient the sofa and media console into the room and toward the seating group.
solver.point_towards(tv_stand[0], coffee_table[0])
solver.point_towards(l_shaped_sofa[0], coffee_table[0])

# Keep the table's long axis coordinated with the sofa.
solver.align_with(coffee_table[0], l_shaped_sofa[0])

# Required relationship: the armchair faces the coffee table.
solver.point_towards(armchair[0], coffee_table[0])

# Maintain useful conversational and circulation spacing around the table.
solver.distance_constraint(
    coffee_table[0], l_shaped_sofa[0], 1.45, 1.85, weight=5
)
solver.distance_constraint(
    armchair[0], coffee_table[0], 1.25, 1.60, weight=5
)
solver.distance_constraint(
    coffee_table[0], tv_stand[0], 1.80, 2.30, weight=2
)
solver.distance_constraint(
    armchair[0], tv_stand[0], 1.20, 1.80, weight=2
)

solver.constraints = []
coffee_table[0].position = [2.549999952316284, 3.450000047683716, 0.20999999344348907]
coffee_table[0].rotation = [0, 0, 8.932167192264502e-07]
coffee_table[0].optimize = 2
tv_stand[0].position = [4.539719581604004, 3.549999952316284, 0.28999999165534973]
tv_stand[0].rotation = [0, 0, 3.1415922704026635]
tv_stand[0].optimize = 2
armchair[0].position = [3.3499999046325684, 4.4403300285339355, 0.4000000059604645]
armchair[0].rotation = [0, 0, -3.1413340584717484]
armchair[0].optimize = 2
l_shaped_sofa[0].position = [0.9766902923583984, 3.549999952316284, 0.4099999964237213]
l_shaped_sofa[0].rotation = [0, 0, -3.76662432625296e-07]
l_shaped_sofa[0].optimize = 2

