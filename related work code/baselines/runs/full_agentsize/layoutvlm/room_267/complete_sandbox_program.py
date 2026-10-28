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
    Wall(corner1=[12.53, 3.02, 0.00], corner2=[12.53, 2.15, 0.00]),
    Wall(corner1=[12.53, 2.15, 0.00], corner2=[13.79, 2.15, 0.00]),
    Wall(corner1=[13.79, 2.15, 0.00], corner2=[13.79, 4.22, 0.00]),
    Wall(corner1=[13.79, 4.22, 0.00], corner2=[8.52, 4.22, 0.00]),
    Wall(corner1=[8.52, 4.22, 0.00], corner2=[8.52, 8.24, 0.00]),
    Wall(corner1=[8.52, 8.24, 0.00], corner2=[4.21, 8.24, 0.00]),
    Wall(corner1=[4.21, 8.24, 0.00], corner2=[4.21, 4.22, 0.00]),
    Wall(corner1=[4.21, 4.22, 0.00], corner2=[0.00, 4.22, 0.00]),
    Wall(corner1=[0.00, 4.22, 0.00], corner2=[0.00, 3.14, 0.00]),
    Wall(corner1=[0.00, 3.14, 0.00], corner2=[7.04, 3.14, 0.00]),
    Wall(corner1=[7.04, 3.14, 0.00], corner2=[7.04, 0.00, 0.00]),
    Wall(corner1=[7.04, 0.00, 0.00], corner2=[9.98, 0.00, 0.00]),
    Wall(corner1=[9.98, 0.00, 0.00], corner2=[9.98, 2.67, 0.00]),
    Wall(corner1=[9.98, 2.67, 0.00], corner2=[11.56, 2.67, 0.00]),
    Wall(corner1=[11.56, 2.67, 0.00], corner2=[11.56, 3.02, 0.00]),
    Wall(corner1=[11.56, 3.02, 0.00], corner2=[12.53, 3.02, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
combination_sofa = Assets(description="combination sofa", size=[1.80, 3.40, 0.88], placements=[AssetInstance() for _ in range(1)])
tv_cabinet = Assets(description="tv cabinet", size=[0.45, 2.20, 0.55], placements=[AssetInstance() for _ in range(1)])
shoe_cabinet = Assets(description="shoe cabinet", size=[0.35, 1.20, 1.10], placements=[AssetInstance() for _ in range(1)])
dining_table_combination = Assets(description="dining table combination", size=[1.50, 2.40, 0.78], placements=[AssetInstance() for _ in range(1)])

combination_sofa[0].instance_id = 'combination_sofa_0'
tv_cabinet[0].instance_id = 'tv_cabinet_0'
shoe_cabinet[0].instance_id = 'shoe_cabinet_0'
dining_table_combination[0].instance_id = 'dining_table_combination_0'
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

combination_sofa[0].position = [7.698444091279534, 6.247767063799646, 0.44]
combination_sofa[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [6.897703600193913, 4.847380237697357, 0.275]
tv_cabinet[0].rotation = [0, 0, 0]
shoe_cabinet[0].position = [10.061776500333842, 3.9461793642993235, 0.55]
shoe_cabinet[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [5.762769929358687, 5.761973555910702, 0.39]
dining_table_combination[0].rotation = [0, 0, 0]
combination_sofa[0].position = [7.698444091279534, 6.247767063799646, 0.44]
combination_sofa[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [6.897703600193913, 4.847380237697357, 0.275]
tv_cabinet[0].rotation = [0, 0, 0]
shoe_cabinet[0].position = [10.061776500333842, 3.9461793642993235, 0.55]
shoe_cabinet[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [5.762769929358687, 5.761973555910702, 0.39]
dining_table_combination[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the living area in the upper room, with the sofa backed against
# the north wall and facing the freestanding TV cabinet.
combination_sofa[0].position = [6.36, 7.34, 0.44]
combination_sofa[0].rotation = [0, 0, radians(-90)]

tv_cabinet[0].position = [6.36, 4.55, 0.275]
tv_cabinet[0].rotation = [0, 0, radians(90)]

# Place the shoe cabinet against the west wall of the living area. It faces
# into the room and remains clear of both the sofa and the circulation opening.
shoe_cabinet[0].position = [4.385, 5.40, 0.55]
shoe_cabinet[0].rotation = [0, 0, radians(0)]

# The dining set occupies the lower central area. Its narrow x footprint leaves
# a clear route along the east side to the 1.92 m door at (9.98, 1.68).
dining_table_combination[0].position = [7.90, 1.65, 0.39]
dining_table_combination[0].rotation = [0, 0, radians(0)]

# Fixed anchors preserve the selected non-overlapping zones and door clearances.
sofa_anchor = AssetInstance(position=[6.36, 7.34, 0.44])
tv_anchor = AssetInstance(position=[6.36, 4.55, 0.275])
shoe_anchor = AssetInstance(position=[4.385, 5.40, 0.55])
dining_anchor = AssetInstance(position=[7.90, 1.65, 0.39])

solver.distance_constraint(
    combination_sofa[0], sofa_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    tv_cabinet[0], tv_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    shoe_cabinet[0], shoe_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    dining_table_combination[0], dining_anchor, 0, 0, weight=10
)

# Keep the sofa's back against the north wall and the shoe cabinet's back
# against the west wall.
solver.against_wall(combination_sofa[0], walls[5])
solver.against_wall(shoe_cabinet[0], walls[6])

# Maintain a comfortable viewing relationship between the sofa and TV.
solver.distance_constraint(
    combination_sofa[0], tv_cabinet[0], 2.70, 3.10, weight=10
)
solver.point_towards(combination_sofa[0], tv_cabinet[0])
solver.point_towards(tv_cabinet[0], combination_sofa[0])

# Explicit orientation targets keep the storage and dining assets facing
# into their usable open spaces.
shoe_facing_target = AssetInstance(position=[6.00, 5.40, 0.55])
dining_facing_target = AssetInstance(position=[9.20, 1.65, 0.39])

solver.point_towards(shoe_cabinet[0], shoe_facing_target)
solver.point_towards(dining_table_combination[0], dining_facing_target)

solver.constraints = []
tv_cabinet[0].position = [6.360000133514404, 4.550000190734863, 0.2750000059604645]
tv_cabinet[0].rotation = [0, 0, 1.586504290712113]
tv_cabinet[0].optimize = 2
combination_sofa[0].position = [6.360000133514404, 6.534201622009277, 0.4399999976158142]
combination_sofa[0].rotation = [0, 0, 0.0064816782299256265]
combination_sofa[0].optimize = 2
shoe_cabinet[0].position = [4.3849778175354, 5.400000095367432, 0.550000011920929]
shoe_cabinet[0].rotation = [0, 0, -4.703697343131776e-05]
shoe_cabinet[0].optimize = 2
dining_table_combination[0].position = [7.900000095367432, 1.649999976158142, 0.38999998569488525]
dining_table_combination[0].rotation = [0, 0, 0.00942477746072377]
dining_table_combination[0].optimize = 2

