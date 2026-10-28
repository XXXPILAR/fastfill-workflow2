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
    Wall(corner1=[9.70, 6.25, 0.00], corner2=[9.70, 6.45, 0.00]),
    Wall(corner1=[9.70, 6.45, 0.00], corner2=[7.89, 6.45, 0.00]),
    Wall(corner1=[7.89, 6.45, 0.00], corner2=[7.89, 7.75, 0.00]),
    Wall(corner1=[7.89, 7.75, 0.00], corner2=[6.64, 7.75, 0.00]),
    Wall(corner1=[6.64, 7.75, 0.00], corner2=[6.64, 6.45, 0.00]),
    Wall(corner1=[6.64, 6.45, 0.00], corner2=[0.00, 6.45, 0.00]),
    Wall(corner1=[0.00, 6.45, 0.00], corner2=[0.00, 2.25, 0.00]),
    Wall(corner1=[0.00, 2.25, 0.00], corner2=[7.87, 2.25, 0.00]),
    Wall(corner1=[7.87, 2.25, 0.00], corner2=[7.87, 0.00, 0.00]),
    Wall(corner1=[7.87, 0.00, 0.00], corner2=[9.70, 0.00, 0.00]),
    Wall(corner1=[9.70, 0.00, 0.00], corner2=[9.70, 3.24, 0.00]),
    Wall(corner1=[9.70, 3.24, 0.00], corner2=[9.94, 3.24, 0.00]),
    Wall(corner1=[9.94, 3.24, 0.00], corner2=[9.94, 3.04, 0.00]),
    Wall(corner1=[9.94, 3.04, 0.00], corner2=[11.23, 3.04, 0.00]),
    Wall(corner1=[11.23, 3.04, 0.00], corner2=[11.23, 6.45, 0.00]),
    Wall(corner1=[11.23, 6.45, 0.00], corner2=[9.94, 6.45, 0.00]),
    Wall(corner1=[9.94, 6.45, 0.00], corner2=[9.94, 6.25, 0.00]),
    Wall(corner1=[9.94, 6.25, 0.00], corner2=[9.70, 6.25, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
refrigerator = Assets(description="refrigerator", size=[0.75, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
dining_table_combination = Assets(description="dining table combination", size=[1.80, 2.40, 0.80], placements=[AssetInstance() for _ in range(1)])
floor_standing_lamp = Assets(description="floor standing lamp", size=[0.40, 0.40, 1.70], placements=[AssetInstance() for _ in range(1)])
combination_sofa = Assets(description="combination sofa", size=[1.60, 3.20, 0.90], placements=[AssetInstance() for _ in range(1)])
air_conditioner = Assets(description="air conditioner", size=[0.25, 1.10, 0.32], placements=[AssetInstance() for _ in range(1)])

refrigerator[0].instance_id = 'refrigerator_0'
dining_table_combination[0].instance_id = 'dining_table_combination_0'
floor_standing_lamp[0].instance_id = 'floor_standing_lamp_0'
combination_sofa[0].instance_id = 'combination_sofa_0'
air_conditioner[0].instance_id = 'air_conditioner_0'
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

refrigerator[0].position = [9.16639412263929, 2.2432974465709, 0.9]
refrigerator[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [9.332850358275264, 1.3095214860039597, 0.4]
dining_table_combination[0].rotation = [0, 0, 0]
floor_standing_lamp[0].position = [3.5657209158880714, 4.923869570323499, 0.85]
floor_standing_lamp[0].rotation = [0, 0, 0]
combination_sofa[0].position = [0.2774161311275605, 4.195363577009887, 0.45]
combination_sofa[0].rotation = [0, 0, 0]
air_conditioner[0].position = [9.281655027434656, 1.396852430879221, 0.16]
air_conditioner[0].rotation = [0, 0, 0]
refrigerator[0].position = [9.16639412263929, 2.2432974465709, 0.9]
refrigerator[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [9.332850358275264, 1.3095214860039597, 0.4]
dining_table_combination[0].rotation = [0, 0, 0]
floor_standing_lamp[0].position = [3.5657209158880714, 4.923869570323499, 0.85]
floor_standing_lamp[0].rotation = [0, 0, 0]
combination_sofa[0].position = [0.2774161311275605, 4.195363577009887, 0.45]
combination_sofa[0].rotation = [0, 0, 0]
air_conditioner[0].position = [9.281655027434656, 1.396852430879221, 0.16]
air_conditioner[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the sofa along the uninterrupted upper wall, facing into the room.
# Its rotated footprint is 3.20 m in x by 1.60 m in y.
combination_sofa[0].position = [2.00, 5.65, 0.45]
combination_sofa[0].rotation = [0, 0, radians(-90)]

# Place the refrigerator against the lower wall, to the left of the doors.
# At this rotation its 0.90 m side runs along the wall.
refrigerator[0].position = [4.00, 2.625, 0.90]
refrigerator[0].rotation = [0, 0, radians(90)]

# The table combination sits beside the refrigerator. Their bounding-box
# edges are separated by 0.10 m; using center distance directly with a
# 0.10 m maximum would make these differently sized assets overlap.
dining_table_combination[0].position = [2.55, 3.45, 0.40]
dining_table_combination[0].rotation = [0, 0, 0]

# Put the lamp beside the sofa, outside the sofa's occupied footprint.
floor_standing_lamp[0].position = [4.10, 5.45, 0.85]
floor_standing_lamp[0].rotation = [0, 0, radians(180)]

# Mount the air conditioner high on the short upper wall of the right-hand
# alcove. The rotated 1.10 m dimension runs parallel to that wall.
air_conditioner[0].position = [10.58, 6.325, 2.45]
air_conditioner[0].rotation = [0, 0, radians(-90)]


# Fixed targets preserve the selected clearances from doors and from the
# windowed walls while still allowing the solver to make small adjustments.
sofa_target = AssetInstance(position=[2.00, 5.65, 0.45])
refrigerator_target = AssetInstance(position=[4.00, 2.625, 0.90])
table_target = AssetInstance(position=[2.55, 3.45, 0.40])
lamp_target = AssetInstance(position=[4.10, 5.45, 0.85])
air_conditioner_target = AssetInstance(position=[10.58, 6.325, 2.45])

sofa_interior_target = AssetInstance(position=[2.00, 4.00, 0.45])
refrigerator_interior_target = AssetInstance(position=[4.00, 4.00, 0.90])
lamp_focus_target = AssetInstance(position=[2.80, 5.45, 0.85])
air_conditioner_interior_target = AssetInstance(position=[10.58, 5.00, 2.45])
zero_rotation_reference = AssetInstance(rotation=[0, 0, 0])


# Required wall relationships are highest priority.
solver.against_wall(combination_sofa[0], walls[5])
solver.point_towards(combination_sofa[0], sofa_interior_target)
solver.distance_constraint(
    combination_sofa[0], sofa_target, 0.0, 0.0, weight=10
)

solver.against_wall(refrigerator[0], walls[7])
solver.point_towards(refrigerator[0], refrigerator_interior_target)
solver.distance_constraint(
    refrigerator[0], refrigerator_target, 0.0, 0.0, weight=10
)

# With the chosen aligned placement, a center separation of about 1.67 m
# corresponds to the requested 0.10 m clearance between the two footprints.
solver.distance_constraint(
    dining_table_combination[0],
    refrigerator[0],
    1.64,
    1.70,
    weight=10,
)
solver.distance_constraint(
    dining_table_combination[0], table_target, 0.0, 0.0, weight=10
)
solver.align_with(
    dining_table_combination[0], zero_rotation_reference, angle=0
)

# Keep the lamp beside the seating group without intruding into the sofa.
solver.distance_constraint(
    floor_standing_lamp[0], lamp_target, 0.0, 0.0, weight=10
)
solver.distance_constraint(
    floor_standing_lamp[0], combination_sofa[0], 1.90, 2.10
)
solver.point_towards(floor_standing_lamp[0], lamp_focus_target)

# Preserve the elevated, wall-mounted air-conditioner placement.
solver.against_wall(air_conditioner[0], walls[15])
solver.distance_constraint(
    air_conditioner[0], air_conditioner_target, 0.0, 0.0, weight=10
)
solver.point_towards(air_conditioner[0], air_conditioner_interior_target)

solver.constraints = []
refrigerator[0].position = [4.0, 2.625, 0.8999999761581421]
refrigerator[0].rotation = [0, 0, 1.5707973096627108]
refrigerator[0].optimize = 2
air_conditioner[0].position = [9.820396423339844, 6.12499475479126, 0.1599999964237213]
air_conditioner[0].rotation = [0, 0, -1.570779608195613]
air_conditioner[0].optimize = 2
combination_sofa[0].position = [2.0, 5.624967098236084, 0.44999998807907104]
combination_sofa[0].rotation = [0, 0, -1.5707953465186493]
combination_sofa[0].optimize = 2
floor_standing_lamp[0].position = [4.099999904632568, 5.449999809265137, 0.8500000238418579]
floor_standing_lamp[0].rotation = [0, 0, -3.1290262823329655]
floor_standing_lamp[0].optimize = 2
dining_table_combination[0].position = [2.549999952316284, 3.461214780807495, 0.4000000059604645]
dining_table_combination[0].rotation = [0, 0, 0.01256637125682779]
dining_table_combination[0].optimize = 2

