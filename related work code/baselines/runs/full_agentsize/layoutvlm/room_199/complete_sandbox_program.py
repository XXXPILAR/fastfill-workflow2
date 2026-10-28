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
    Wall(corner1=[4.57, 1.32, 0.00], corner2=[11.25, 1.32, 0.00]),
    Wall(corner1=[11.25, 1.32, 0.00], corner2=[11.25, 4.67, 0.00]),
    Wall(corner1=[11.25, 4.67, 0.00], corner2=[6.75, 4.67, 0.00]),
    Wall(corner1=[6.75, 4.67, 0.00], corner2=[6.75, 8.94, 0.00]),
    Wall(corner1=[6.75, 8.94, 0.00], corner2=[5.49, 8.94, 0.00]),
    Wall(corner1=[5.49, 8.94, 0.00], corner2=[5.49, 4.28, 0.00]),
    Wall(corner1=[5.49, 4.28, 0.00], corner2=[0.00, 4.28, 0.00]),
    Wall(corner1=[0.00, 4.28, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.57, 0.00, 0.00]),
    Wall(corner1=[4.57, 0.00, 0.00], corner2=[4.57, 1.32, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
dining_table_combination = Assets(description="dining table combination", size=[2.20, 3.00, 0.78], placements=[AssetInstance() for _ in range(1)])
potted_bonsai = Assets(description="potted bonsai", size=[0.40, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
tv_cabinet = Assets(description="tv cabinet", size=[0.48, 2.40, 0.58], placements=[AssetInstance() for _ in range(1)])
air_conditioner = Assets(description="air conditioner", size=[0.25, 1.05, 0.32], placements=[AssetInstance() for _ in range(1)])
refrigerator = Assets(description="refrigerator", size=[0.75, 0.90, 1.85], placements=[AssetInstance() for _ in range(1)])
combination_sofa = Assets(description="combination sofa", size=[2.30, 3.60, 0.88], placements=[AssetInstance() for _ in range(1)])

dining_table_combination[0].instance_id = 'dining_table_combination_0'
potted_bonsai[0].instance_id = 'potted_bonsai_0'
tv_cabinet[0].instance_id = 'tv_cabinet_0'
air_conditioner[0].instance_id = 'air_conditioner_0'
refrigerator[0].instance_id = 'refrigerator_0'
combination_sofa[0].instance_id = 'combination_sofa_0'
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

dining_table_combination[0].position = [4.29374551352755, 2.7940266759897967, 0.39]
dining_table_combination[0].rotation = [0, 0, 0]
potted_bonsai[0].position = [6.896662222879644, 2.636801086174528, 0.275]
potted_bonsai[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [1.7506010803206558, 0.4303105480465342, 0.29]
tv_cabinet[0].rotation = [0, 0, 0]
air_conditioner[0].position = [8.78643508097177, 2.9420016843187096, 0.16]
air_conditioner[0].rotation = [0, 0, 0]
refrigerator[0].position = [1.113807494557265, 3.137245271792478, 0.925]
refrigerator[0].rotation = [0, 0, 0]
combination_sofa[0].position = [10.219840164136642, 3.4470670910797945, 0.44]
combination_sofa[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [4.29374551352755, 2.7940266759897967, 0.39]
dining_table_combination[0].rotation = [0, 0, 0]
potted_bonsai[0].position = [6.896662222879644, 2.636801086174528, 0.275]
potted_bonsai[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [1.7506010803206558, 0.4303105480465342, 0.29]
tv_cabinet[0].rotation = [0, 0, 0]
air_conditioner[0].position = [8.78643508097177, 2.9420016843187096, 0.16]
air_conditioner[0].rotation = [0, 0, 0]
refrigerator[0].position = [1.113807494557265, 3.137245271792478, 0.925]
refrigerator[0].rotation = [0, 0, 0]
combination_sofa[0].position = [10.219840164136642, 3.4470670910797945, 0.44]
combination_sofa[0].rotation = [0, 0, 0]

solver.constraints = []

# The seating/TV zone occupies the wider left-hand part of the room. Rotating
# both assets by 90 degrees lets the sofa face the TV while preserving a clear
# passage from the door along the west side of the room.
combination_sofa[0].position = [3.20, 2.47, 0.44]
combination_sofa[0].rotation = [0, 0, radians(90)]

tv_cabinet[0].position = [3.20, 4.04, 0.29]
tv_cabinet[0].rotation = [0, 0, radians(-90)]

# The dining set fits in the eastern bay when its 3 m dimension runs east-west.
dining_table_combination[0].position = [8.25, 3.10, 0.39]
dining_table_combination[0].rotation = [0, 0, radians(90)]

# Center the bonsai on the dining table.
potted_bonsai[0].position = [8.25, 3.10, 1.055]
potted_bonsai[0].rotation = [0, 0, radians(90)]

# Keep the refrigerator beside the dining zone and against the lower wall of
# the eastern bay, without obstructing the window on the right-hand wall.
refrigerator[0].position = [10.75, 1.695, 0.925]
refrigerator[0].rotation = [0, 0, radians(90)]

# Mount the air conditioner high on the upper wall, above floor circulation
# and away from the window opening.
air_conditioner[0].position = [10.40, 4.545, 2.35]
air_conditioner[0].rotation = [0, 0, radians(-90)]

# Fixed targets preserve the intended room zoning while allowing the semantic
# constraints below to remain explicit.
sofa_target = AssetInstance(
    position=[3.20, 2.47, 0.44],
    rotation=[0, 0, radians(90)]
)
dining_target = AssetInstance(
    position=[8.25, 3.10, 0.39],
    rotation=[0, 0, radians(90)]
)
bonsai_target = AssetInstance(
    position=[8.25, 3.10, 1.055],
    rotation=[0, 0, radians(90)]
)
tv_target = AssetInstance(
    position=[3.20, 4.04, 0.29],
    rotation=[0, 0, radians(-90)]
)
refrigerator_target = AssetInstance(
    position=[10.75, 1.695, 0.925],
    rotation=[0, 0, radians(90)]
)
air_conditioner_target = AssetInstance(
    position=[10.40, 4.545, 2.35],
    rotation=[0, 0, radians(-90)]
)

# The principal layout requirement: the sofa faces the TV. Its target also
# keeps the door-side strip clear for entry and circulation.
solver.point_towards(combination_sofa[0], tv_cabinet[0])
solver.distance_constraint(
    combination_sofa[0], sofa_target, 0, 0, weight=10
)
solver.distance_constraint(
    combination_sofa[0], tv_cabinet[0], 1.45, 1.75, weight=10
)

# Place the TV against wall 6 (the horizontal wall at y=4.28), facing the sofa.
solver.against_wall(tv_cabinet[0], walls[6])
solver.point_towards(tv_cabinet[0], combination_sofa[0])
solver.distance_constraint(tv_cabinet[0], tv_target, 0, 0, weight=10)

# Anchor and orient the dining group in the open eastern bay.
solver.distance_constraint(
    dining_table_combination[0], dining_target, 0, 0, weight=10
)
solver.align_with(dining_table_combination[0], dining_target)

# The bonsai must remain on the tabletop and centered on the dining group.
solver.on_top_of(potted_bonsai[0], dining_table_combination[0])
solver.distance_constraint(potted_bonsai[0], bonsai_target, 0, 0, weight=10)
solver.align_with(potted_bonsai[0], dining_table_combination[0])

# Place the refrigerator against wall 0, opening toward the usable room area.
solver.against_wall(refrigerator[0], walls[0])
solver.distance_constraint(
    refrigerator[0], refrigerator_target, 0, 0, weight=10
)
solver.align_with(refrigerator[0], refrigerator_target)

# Place the elevated air conditioner against wall 2 and orient its front
# toward the room.
solver.against_wall(air_conditioner[0], walls[2])
solver.distance_constraint(
    air_conditioner[0], air_conditioner_target, 0, 0, weight=10
)
solver.align_with(air_conditioner[0], air_conditioner_target)

solver.constraints = []
combination_sofa[0].position = [3.200000047683716, 2.4700000286102295, 0.4399999976158142]
combination_sofa[0].rotation = [0, 0, 1.586504290712113]
combination_sofa[0].optimize = 2
dining_table_combination[0].position = [8.25, 3.0999999046325684, 0.38999998569488525]
dining_table_combination[0].rotation = [0, 0, 1.586504290712113]
dining_table_combination[0].optimize = 2
refrigerator[0].position = [10.75, 1.695056438446045, 0.925000011920929]
refrigerator[0].rotation = [0, 0, 1.5706741487732334]
refrigerator[0].optimize = 2
tv_cabinet[0].position = [3.200000047683716, 4.040224552154541, 0.28999999165534973]
tv_cabinet[0].rotation = [0, 0, -1.5709813113073643]
tv_cabinet[0].optimize = 2
potted_bonsai[0].position = [8.25, 3.0999999046325684, 1.0549999475479126]
potted_bonsai[0].rotation = [0, 0, 1.5865919142057168]
potted_bonsai[0].optimize = 2
air_conditioner[0].position = [10.399999618530273, 4.54998779296875, 0.1599999964237213]
air_conditioner[0].rotation = [0, 0, -1.570918076587863]
air_conditioner[0].optimize = 2

