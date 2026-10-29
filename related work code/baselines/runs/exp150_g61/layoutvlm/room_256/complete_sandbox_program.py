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
    Wall(corner1=[0.00, 4.26, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.67, 0.00, 0.00]),
    Wall(corner1=[6.67, 0.00, 0.00], corner2=[6.67, 4.26, 0.00]),
    Wall(corner1=[6.67, 4.26, 0.00], corner2=[0.00, 4.26, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
shoe_cabinet = Assets(description="shoe cabinet", size=[0.35, 1.00, 1.10], placements=[AssetInstance() for _ in range(1)])
plants = Assets(description="plants", size=[0.55, 0.55, 1.40], placements=[AssetInstance() for _ in range(1)])
combination_sofa = Assets(description="combination sofa", size=[1.80, 3.00, 0.85], placements=[AssetInstance() for _ in range(1)])

shoe_cabinet[0].instance_id = 'shoe_cabinet_0'
plants[0].instance_id = 'plants_0'
combination_sofa[0].instance_id = 'combination_sofa_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

shoe_cabinet[0].position = [1.4285046592738793, 2.4158059955169224, 0.55]
shoe_cabinet[0].rotation = [0, 0, 0]
plants[0].position = [2.713974650363677, 2.251773366086964, 0.7]
plants[0].rotation = [0, 0, 0]
combination_sofa[0].position = [1.37343709794539, 2.3265549711482842, 0.425]
combination_sofa[0].rotation = [0, 0, 0]
shoe_cabinet[0].position = [1.4285046592738793, 2.4158059955169224, 0.55]
shoe_cabinet[0].rotation = [0, 0, 0]
plants[0].position = [2.713974650363677, 2.251773366086964, 0.7]
plants[0].rotation = [0, 0, 0]
combination_sofa[0].position = [1.37343709794539, 2.3265549711482842, 0.425]
combination_sofa[0].rotation = [0, 0, 0]

solver.constraints = []

# The sofa faces south toward the fixed TV cabinet. Rotating it by -90°
# gives a 3.00 m east–west footprint and a 1.80 m north–south footprint.
# Its bounds are x=[2.85, 5.85], y=[2.46, 4.26], leaving an
# 0.82 m passage along the east side and keeping the north doors clear.
combination_sofa[0].position = [4.35, 3.36, 0.425]
combination_sofa[0].rotation = [0, 0, radians(-90)]

# Use the uninterrupted lower section of the west wall, below its doorway.
# Cabinet bounds: x=[0.00, 0.35], y=[1.05, 2.05].
shoe_cabinet[0].position = [0.175, 1.55, 0.55]
shoe_cabinet[0].rotation = [0, 0, 0]

# The floor-standing plant fits in the southwest corner, away from the
# south doorway, with separation from the shoe cabinet.
plants[0].position = [0.45, 0.40, 0.70]
plants[0].rotation = [0, 0, 0]

# Fixed reference points are layout anchors, not additional scene assets.
sofa_anchor = AssetInstance(position=[4.35, 3.36, 0.425])
cabinet_anchor = AssetInstance(position=[0.175, 1.55, 0.55])
plant_anchor = AssetInstance(position=[0.45, 0.40, 0.70])
tv_facing_point = AssetInstance(position=[4.35, 0.13, 0.425])
cabinet_facing_point = AssetInstance(position=[1.175, 1.55, 0.55])

# Prioritize the required wall contact and preserve the cabinet's safe
# location along that wall rather than letting it slide into a doorway.
solver.against_wall(shoe_cabinet[0], walls[0])
solver.distance_constraint(
    shoe_cabinet[0], cabinet_anchor, 0, 0, weight=10
)
solver.point_towards(shoe_cabinet[0], cabinet_facing_point)

# Anchor the sofa so neither the east passage nor the north-door approach
# is lost during adjustment. Its back rests against the north wall.
solver.distance_constraint(
    combination_sofa[0], sofa_anchor, 0, 0, weight=10
)
solver.against_wall(combination_sofa[0], walls[3])
solver.point_towards(combination_sofa[0], tv_facing_point)

# This is a full-height floor plant, so no supporting surface is needed.
solver.distance_constraint(plants[0], plant_anchor, 0, 0, weight=10)
solver.align_with(plants[0], shoe_cabinet[0], angle=0)

# Additional center-distance safeguards maintain separation between assets.
solver.distance_constraint(
    plants[0], shoe_cabinet[0], 1.10, None
)
solver.distance_constraint(
    combination_sofa[0], shoe_cabinet[0], 3.0, None
)
solver.distance_constraint(
    combination_sofa[0], plants[0], 3.0, None
)

solver.constraints = []
shoe_cabinet[0].position = [0.17518307268619537, 1.5592377185821533, 0.550000011920929]
shoe_cabinet[0].rotation = [0, 0, -0.00011735575100074297]
shoe_cabinet[0].optimize = 2
plants[0].position = [0.44999998807907104, 0.4000000059604645, 0.699999988079071]
plants[0].rotation = [0, 0, -0.00011737435828424848]
plants[0].optimize = 2
combination_sofa[0].position = [4.349999904632568, 3.3595001697540283, 0.42500001192092896]
combination_sofa[0].rotation = [0, 0, -1.5707963147006543]
combination_sofa[0].optimize = 2

