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
    Wall(corner1=[1.40, 3.15, 0.00], corner2=[1.40, 2.56, 0.00]),
    Wall(corner1=[1.40, 2.56, 0.00], corner2=[0.00, 2.56, 0.00]),
    Wall(corner1=[0.00, 2.56, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.48, 0.00, 0.00]),
    Wall(corner1=[2.48, 0.00, 0.00], corner2=[2.48, 3.15, 0.00]),
    Wall(corner1=[2.48, 3.15, 0.00], corner2=[1.40, 3.15, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
dining_table_combination = Assets(description="dining table combination", size=[0.60, 1.00, 0.74], placements=[AssetInstance() for _ in range(1)])
combination_sofa = Assets(description="combination sofa", size=[0.78, 1.40, 0.80], placements=[AssetInstance() for _ in range(1)])

dining_table_combination[0].instance_id = 'dining_table_combination_0'
combination_sofa[0].instance_id = 'combination_sofa_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

dining_table_combination[0].position = [0.15003678239646193, 1.4975777248432078, 0.37]
dining_table_combination[0].rotation = [0, 0, 0]
combination_sofa[0].position = [0.4300718028558178, 0.830060011430929, 0.4]
combination_sofa[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [0.15003678239646193, 1.4975777248432078, 0.37]
dining_table_combination[0].rotation = [0, 0, 0]
combination_sofa[0].position = [0.4300718028558178, 0.830060011430929, 0.4]
combination_sofa[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange both combinations along the left wall, facing into the room (+x).
# Table footprint: x=[0.00, 0.60], y=[0.05, 1.05].
# Sofa footprint:  x=[0.00, 0.78], y=[1.11, 2.51].
# Their edges are 0.06 m apart; neither footprint overlaps the other.
# The right-hand circulation route and the floor in front of the door stay clear.
dining_table_combination[0].position = [0.30, 0.55, 0.37]
dining_table_combination[0].rotation = [0.0, 0.0, 0.0]

combination_sofa[0].position = [0.39, 1.81, 0.40]
combination_sofa[0].rotation = [0.0, 0.0, 0.0]

# Prioritize wall contact for both combinations.
solver.against_wall(dining_table_combination[0], walls[2])
solver.against_wall(combination_sofa[0], walls[2])

# Fix the intended locations to preserve boundary clearance, the narrow
# inter-object gap, and the unobstructed entrance.
solver.distance_constraint(
    dining_table_combination[0],
    AssetInstance(position=[0.30, 0.55, 0.37]),
    0.0, 0.0, weight=10,
)
solver.distance_constraint(
    combination_sofa[0],
    AssetInstance(position=[0.39, 1.81, 0.40]),
    0.0, 0.0, weight=10,
)

# Face inward, perpendicular to the left wall.
solver.point_towards(
    dining_table_combination[0],
    AssetInstance(position=[2.00, 0.55, 0.37]),
)
solver.point_towards(
    combination_sofa[0],
    AssetInstance(position=[2.00, 1.81, 0.40]),
)

# The API measures center distances, not edge gaps. With these parallel
# footprints and wall contact, this range represents a 0.03–0.10 m edge gap.
minimum_center_distance = (0.09**2 + 1.23**2 + 0.03**2) ** 0.5
maximum_center_distance = (0.09**2 + 1.30**2 + 0.03**2) ** 0.5

solver.distance_constraint(
    combination_sofa[0], dining_table_combination[0],
    minimum_center_distance, maximum_center_distance, weight=10,
)
solver.align_with(combination_sofa[0], dining_table_combination[0], angle=0.0)

solver.constraints = []
dining_table_combination[0].position = [0.29999998211860657, 0.550000011920929, 0.3700000047683716]
dining_table_combination[0].rotation = [0, 0, 3.791291221251607e-08]
dining_table_combination[0].optimize = 2
combination_sofa[0].position = [0.39000001549720764, 1.809999942779541, 0.4000000059604645]
combination_sofa[0].rotation = [0, 0, 3.902258088294658e-08]
combination_sofa[0].optimize = 2

