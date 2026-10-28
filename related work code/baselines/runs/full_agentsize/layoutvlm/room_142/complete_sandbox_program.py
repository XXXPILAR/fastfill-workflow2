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
    Wall(corner1=[4.00, 0.00, 0.00], corner2=[4.00, 3.00, 0.00]),
    Wall(corner1=[4.00, 3.00, 0.00], corner2=[0.00, 3.00, 0.00]),
    Wall(corner1=[0.00, 3.00, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
towel_rack = Assets(description="freestanding modern towel rack with multiple bars", size=[0.25, 0.65, 0.90], placements=[AssetInstance() for _ in range(1)])
bathtub = Assets(description="freestanding modern oval bathtub with smooth edges, larger size for comfortable soaking", size=[0.85, 1.80, 0.60], placements=[AssetInstance() for _ in range(1)])
vanity = Assets(description="large modern wall-mounted bathroom vanity with extended countertop and storage", size=[0.55, 1.80, 0.60], placements=[AssetInstance() for _ in range(1)])
toilet = Assets(description="standard modern toilet with larger size for comfort", size=[0.72, 0.40, 0.78], placements=[AssetInstance() for _ in range(1)])
bidet = Assets(description="modern bidet unit with smooth design", size=[0.58, 0.38, 0.42], placements=[AssetInstance() for _ in range(1)])

towel_rack[0].instance_id = 'towel_rack_0'
bathtub[0].instance_id = 'bathtub_0'
vanity[0].instance_id = 'vanity_0'
toilet[0].instance_id = 'toilet_0'
bidet[0].instance_id = 'bidet_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

towel_rack[0].position = [1.5924091277033856, 0.9323163700471221, 0.45]
towel_rack[0].rotation = [0, 0, 0]
bathtub[0].position = [0.9715241798288319, 2.4212172788745088, 0.3]
bathtub[0].rotation = [0, 0, 0]
vanity[0].position = [2.3714482208336642, 0.6684693661932634, 0.3]
vanity[0].rotation = [0, 0, 0]
toilet[0].position = [1.632751719968618, 0.3345638065010029, 0.39]
toilet[0].rotation = [0, 0, 0]
bidet[0].position = [1.5098090805363453, 1.9001779960657186, 0.21]
bidet[0].rotation = [0, 0, 0]
towel_rack[0].position = [1.5924091277033856, 0.9323163700471221, 0.45]
towel_rack[0].rotation = [0, 0, 0]
bathtub[0].position = [0.9715241798288319, 2.4212172788745088, 0.3]
bathtub[0].rotation = [0, 0, 0]
vanity[0].position = [2.3714482208336642, 0.6684693661932634, 0.3]
vanity[0].rotation = [0, 0, 0]
toilet[0].position = [1.632751719968618, 0.3345638065010029, 0.39]
toilet[0].rotation = [0, 0, 0]
bidet[0].position = [1.5098090805363453, 1.9001779960657186, 0.21]
bidet[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the vanity against the left wall, facing into the room.
vanity[0].position = [0.275, 1.55, 0.30]
vanity[0].rotation = [0, 0, radians(0)]

# Place the bathtub lengthwise along the upper wall, leaving usable access
# from the center of the bathroom.
bathtub[0].position = [2.60, 2.575, 0.30]
bathtub[0].rotation = [0, 0, radians(90)]

# Place the toilet against the right wall, opposite the vanity.
toilet[0].position = [3.64, 0.55, 0.39]
toilet[0].rotation = [0, 0, radians(180)]

# Place the bidet beside the toilet with clearance between both fixtures.
bidet[0].position = [3.71, 1.25, 0.21]
bidet[0].rotation = [0, 0, radians(180)]

# Keep the towel rack against the lower wall and near the bathtub's open side.
towel_rack[0].position = [2.25, 0.125, 0.45]
towel_rack[0].rotation = [0, 0, radians(90)]

# Fixed points preserve the intended positions along each supporting wall.
vanity_anchor = AssetInstance(position=[0.275, 1.55, 0.30])
bathtub_anchor = AssetInstance(position=[2.60, 2.575, 0.30])
toilet_anchor = AssetInstance(position=[3.64, 0.55, 0.39])
bidet_anchor = AssetInstance(position=[3.71, 1.25, 0.21])
towel_rack_anchor = AssetInstance(position=[2.25, 0.125, 0.45])
room_center = AssetInstance(position=[2.00, 1.50, 0.30])

# Primary wall constraints keep all fixtures inside the room.
solver.against_wall(vanity[0], walls[2])
solver.against_wall(bathtub[0], walls[1])
solver.against_wall(toilet[0], walls[0])
solver.against_wall(bidet[0], walls[0])
solver.against_wall(towel_rack[0], walls[3])

# Strong anchor constraints retain the functional spacing along the walls.
solver.distance_constraint(vanity[0], vanity_anchor, 0, 0, weight=10)
solver.distance_constraint(bathtub[0], bathtub_anchor, 0, 0, weight=10)
solver.distance_constraint(toilet[0], toilet_anchor, 0, 0, weight=10)
solver.distance_constraint(bidet[0], bidet_anchor, 0, 0, weight=10)
solver.distance_constraint(towel_rack[0], towel_rack_anchor, 0, 0, weight=10)

# Orient the vanity inward and the bathtub perpendicular to it.
solver.point_towards(vanity[0], room_center)
solver.align_with(bathtub[0], vanity[0], angle=90)

# The toilet explicitly faces the vanity, as required. The bidet uses the
# same practical inward-facing orientation.
solver.point_towards(toilet[0], vanity[0])
solver.point_towards(bidet[0], vanity[0])

# Keep the towel rack parallel to the bathtub and facing into the room.
solver.align_with(towel_rack[0], bathtub[0])

# Secondary spacing constraints preserve clear gaps between neighboring
# fixtures if the solver needs to make small feasibility adjustments.
solver.distance_constraint(toilet[0], bidet[0], 0.60, 0.85, weight=5)
solver.distance_constraint(bidet[0], bathtub[0], 1.00, 1.60, weight=2)
solver.distance_constraint(towel_rack[0], bathtub[0], 1.70, 2.70, weight=1)
solver.distance_constraint(vanity[0], bathtub[0], 1.80, 2.80, weight=1)

solver.constraints = []
bathtub[0].position = [2.5999999046325684, 2.5749874114990234, 0.30000001192092896]
bathtub[0].rotation = [0, 0, -1.570796738549275]
bathtub[0].optimize = 2
toilet[0].position = [3.640000104904175, 0.8121575117111206, 0.38999998569488525]
toilet[0].rotation = [0, 0, -3.1415926098772604]
toilet[0].optimize = 2
bidet[0].position = [3.7099995613098145, 1.6361582279205322, 0.20999999344348907]
bidet[0].rotation = [0, 0, -3.14159260989593]
bidet[0].optimize = 2
towel_rack[0].position = [2.5203514099121094, 0.1249997466802597, 0.44999998807907104]
towel_rack[0].rotation = [0, 0, 1.5707963685530588]
towel_rack[0].optimize = 2
vanity[0].position = [0.2749999463558197, 1.5499999523162842, 0.30000001192092896]
vanity[0].rotation = [0, 0, 3.29490535943063e-08]
vanity[0].optimize = 2

