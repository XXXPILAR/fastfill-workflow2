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
shoe_cabinet = Assets(description="shoe cabinet", size=[0.35, 1.20, 1.00], placements=[AssetInstance() for _ in range(1)])
plants = Assets(description="plants", size=[0.50, 0.50, 1.20], placements=[AssetInstance() for _ in range(1)])
combination_sofa = Assets(description="combination sofa", size=[2.20, 3.20, 0.85], placements=[AssetInstance() for _ in range(1)])

shoe_cabinet[0].instance_id = 'shoe_cabinet_0'
plants[0].instance_id = 'plants_0'
combination_sofa[0].instance_id = 'combination_sofa_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

shoe_cabinet[0].position = [4.553724599713549, 0.11875946812497268, 0.5]
shoe_cabinet[0].rotation = [0, 0, 0]
plants[0].position = [4.684006254494277, 3.0980354391925187, 0.6]
plants[0].rotation = [0, 0, 0]
combination_sofa[0].position = [2.7605776723245596, 0.2173209276846109, 0.425]
combination_sofa[0].rotation = [0, 0, 0]
shoe_cabinet[0].position = [4.553724599713549, 0.11875946812497268, 0.5]
shoe_cabinet[0].rotation = [0, 0, 0]
plants[0].position = [4.684006254494277, 3.0980354391925187, 0.6]
plants[0].rotation = [0, 0, 0]
combination_sofa[0].position = [2.7605776723245596, 0.2173209276846109, 0.425]
combination_sofa[0].rotation = [0, 0, 0]

solver.constraints = []

# Keep the compact shoe cabinet on the lower section of the left wall, below
# the doorway that begins around y=2.56. Its front faces into the room.
shoe_cabinet[0].position = [0.175, 1.80, 0.50]
shoe_cabinet[0].rotation = [0, 0, radians(0)]

# Place the plant in the unobstructed bottom-left corner, away from both the
# bottom doorway and the shoe cabinet.
plants[0].position = [0.60, 0.25, 0.60]
plants[0].rotation = [0, 0, radians(0)]

# Float the sofa in front of the fixed TV cabinet. With its long dimension
# running along x, there is circulation space around all four sides and clear
# approach zones in front of the surrounding doors.
combination_sofa[0].position = [4.00, 2.20, 0.425]
combination_sofa[0].rotation = [0, 0, radians(-90)]

# Fixed reference points preserve the intended locations while allowing the
# solver to make small feasibility adjustments.
shoe_anchor = AssetInstance(position=[0.175, 1.80, 0.50])
plant_anchor = AssetInstance(position=[0.60, 0.25, 0.60])
sofa_anchor = AssetInstance(position=[4.00, 2.20, 0.425])
room_center = AssetInstance(position=[3.335, 2.13, 0.50])

# This point lies on the fixed TV cabinet and gives the sofa a straight,
# downward-facing viewing direction.
tv_viewing_point = AssetInstance(position=[4.00, 0.13, 0.425])

# Shoe cabinet: the wall constraint is most important because the layout
# explicitly requires it to remain against a wall.
solver.against_wall(shoe_cabinet[0], walls[0])
solver.distance_constraint(
    shoe_cabinet[0], shoe_anchor,
    min_distance=0.0, max_distance=0.0, weight=10
)
solver.point_towards(shoe_cabinet[0], room_center)

# Plant: keep it against the bottom wall and anchored within the safe corner.
solver.against_wall(plants[0], walls[1])
solver.distance_constraint(
    plants[0], plant_anchor,
    min_distance=0.0, max_distance=0.0, weight=10
)
solver.align_with(plants[0], shoe_cabinet[0], angle=0)

# Maintain separation between the two small objects in the lower-left area.
solver.distance_constraint(
    plants[0], shoe_cabinet[0],
    min_distance=1.20, max_distance=2.00, weight=1
)

# Sofa: preserve its central viewing position and orient it toward the fixed
# TV cabinet. The distance constraint maintains a practical viewing distance.
solver.distance_constraint(
    combination_sofa[0], sofa_anchor,
    min_distance=0.0, max_distance=0.0, weight=10
)
solver.distance_constraint(
    combination_sofa[0], tv_viewing_point,
    min_distance=1.90, max_distance=2.30, weight=1
)
solver.point_towards(combination_sofa[0], tv_viewing_point)

solver.constraints = []
plants[0].position = [0.6000000238418579, 0.2500000298023224, 0.6000000238418579]
plants[0].rotation = [0, 0, 1.570796262679199]
plants[0].optimize = 2
combination_sofa[0].position = [4.0, 2.200000047683716, 0.42500001192092896]
combination_sofa[0].rotation = [0, 0, -1.5582299555380688]
combination_sofa[0].optimize = 2
shoe_cabinet[0].position = [0.17521241307258606, 1.8095594644546509, 0.5]
shoe_cabinet[0].rotation = [0, 0, -0.00011734649137289605]
shoe_cabinet[0].optimize = 2

