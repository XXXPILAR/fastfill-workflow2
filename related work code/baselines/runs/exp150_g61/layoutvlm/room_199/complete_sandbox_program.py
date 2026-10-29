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
dining_table_combination = Assets(description="dining table combination", size=[2.20, 2.80, 0.90], placements=[AssetInstance() for _ in range(1)])
potted_bonsai = Assets(description="potted bonsai", size=[0.40, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])
tv_cabinet = Assets(description="tv cabinet", size=[0.45, 2.40, 0.55], placements=[AssetInstance() for _ in range(1)])
air_conditioner = Assets(description="air conditioner", size=[0.25, 1.10, 0.33], placements=[AssetInstance() for _ in range(1)])
refrigerator = Assets(description="refrigerator", size=[0.75, 0.90, 1.85], placements=[AssetInstance() for _ in range(1)])
combination_sofa = Assets(description="combination sofa", size=[2.10, 3.60, 0.90], placements=[AssetInstance() for _ in range(1)])

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

dining_table_combination[0].position = [4.166603960810861, 0.5131059709548359, 0.45]
dining_table_combination[0].rotation = [0, 0, 0]
potted_bonsai[0].position = [0.4532189422285786, 2.4235537948630297, 0.3]
potted_bonsai[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [2.7892516458916163, 1.1715600613797175, 0.275]
tv_cabinet[0].rotation = [0, 0, 0]
air_conditioner[0].position = [6.352288012056185, 5.121048882091984, 0.165]
air_conditioner[0].rotation = [0, 0, 0]
refrigerator[0].position = [7.5607989076201445, 4.313224848999927, 0.925]
refrigerator[0].rotation = [0, 0, 0]
combination_sofa[0].position = [6.1519584699469885, 7.687913855156065, 0.45]
combination_sofa[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [4.166603960810861, 0.5131059709548359, 0.45]
dining_table_combination[0].rotation = [0, 0, 0]
potted_bonsai[0].position = [0.4532189422285786, 2.4235537948630297, 0.3]
potted_bonsai[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [2.7892516458916163, 1.1715600613797175, 0.275]
tv_cabinet[0].rotation = [0, 0, 0]
air_conditioner[0].position = [6.352288012056185, 5.121048882091984, 0.165]
air_conditioner[0].rotation = [0, 0, 0]
refrigerator[0].position = [7.5607989076201445, 4.313224848999927, 0.925]
refrigerator[0].rotation = [0, 0, 0]
combination_sofa[0].position = [6.1519584699469885, 7.687913855156065, 0.45]
combination_sofa[0].rotation = [0, 0, 0]

solver.constraints = []

# The right-hand bay is the living area. Rotating the sofa by 270 degrees
# gives it a 3.60 m east-west footprint and makes it face the south wall.
# Its footprint is x=[7.00, 10.60], y=[2.57, 4.67].
combination_sofa[0].position = [8.80, 3.62, 0.45]
combination_sofa[0].rotation = [0, 0, radians(270)]

# The cabinet faces north toward the sofa. Its footprint is
# x=[7.60, 10.00], y=[1.32, 1.77], leaving 0.80 m between the furniture.
# Neither piece occupies the east-wall window.
tv_cabinet[0].position = [8.80, 1.545, 0.275]
tv_cabinet[0].rotation = [0, 0, radians(90)]

# Keep the dining combination in the western room, with its complete
# footprint at x=[1.90, 4.10], y=[1.10, 3.90].
# The western 1.90 m strip remains clear in front of the entrance.
dining_table_combination[0].position = [3.00, 2.50, 0.45]
dining_table_combination[0].rotation = [0, 0, 0]

# Place the refrigerator against the south wall, opening toward the room.
# Its footprint is x=[3.45, 4.35], y=[0.00, 0.75].
refrigerator[0].position = [3.90, 0.375, 0.925]
refrigerator[0].rotation = [0, 0, radians(90)]

# Mount the air conditioner high on the north living-room wall.
# Its bottom is at 2.335 m, well above the sofa.
air_conditioner[0].position = [8.80, 4.545, 2.50]
air_conditioner[0].rotation = [0, 0, radians(270)]

# The bonsai rests on the cabinet, toward its eastern end.
# Rotation gives it a 0.40 m depth, fitting the cabinet's 0.45 m depth.
potted_bonsai[0].position = [9.60, 1.545, 0.85]
potted_bonsai[0].rotation = [0, 0, radians(90)]

# Prioritize the supported object and the sofa-to-cabinet viewing direction.
solver.on_top_of(potted_bonsai[0], tv_cabinet[0])
solver.point_towards(combination_sofa[0], tv_cabinet[0])
solver.point_towards(tv_cabinet[0], combination_sofa[0])

# Fixed-point constraints retain the planned clearances and prevent furniture
# from drifting into the entrance, window, or narrow northern passage.
# These are reference points only, not additional scene objects.
for layout_asset, layout_position in [
    (combination_sofa[0], [8.80, 3.62, 0.45]),
    (tv_cabinet[0], [8.80, 1.545, 0.275]),
    (dining_table_combination[0], [3.00, 2.50, 0.45]),
    (refrigerator[0], [3.90, 0.375, 0.925]),
    (air_conditioner[0], [8.80, 4.545, 2.50]),
    (potted_bonsai[0], [9.60, 1.545, 0.85]),
]:
    solver.distance_constraint(
        layout_asset,
        AssetInstance(position=layout_position),
        min_distance=0,
        max_distance=0,
        weight=10,
    )

# Wall relationships reinforce the intended room organization.
solver.against_wall(combination_sofa[0], walls[2])
solver.against_wall(tv_cabinet[0], walls[0])
solver.against_wall(refrigerator[0], walls[8])
solver.against_wall(air_conditioner[0], walls[2])

# Complete the orientation constraints for the remaining assets.
solver.align_with(
    dining_table_combination[0],
    AssetInstance(rotation=[0, 0, 0]),
)
solver.align_with(refrigerator[0], tv_cabinet[0])
solver.align_with(air_conditioner[0], combination_sofa[0])
solver.align_with(potted_bonsai[0], tv_cabinet[0])

solver.constraints = []
dining_table_combination[0].position = [3.0, 2.5, 0.44999998807907104]
dining_table_combination[0].rotation = [0, 0, 0.00942477746072377]
dining_table_combination[0].optimize = 2
tv_cabinet[0].position = [8.800000190734863, 1.539300560951233, 0.2750000059604645]
tv_cabinet[0].rotation = [0, 0, 1.5699635842975759]
tv_cabinet[0].optimize = 2
refrigerator[0].position = [3.9000000953674316, 0.3743966817855835, 0.925000011920929]
refrigerator[0].rotation = [0, 0, 1.5750157569418444]
refrigerator[0].optimize = 2
combination_sofa[0].position = [8.800000190734863, 3.591259241104126, 0.44999998807907104]
combination_sofa[0].rotation = [0, 0, -1.5654960049404862]
combination_sofa[0].optimize = 2
potted_bonsai[0].position = [9.600000381469727, 1.5449999570846558, 0.8500000238418579]
potted_bonsai[0].rotation = [0, 0, 1.5450466256598636]
potted_bonsai[0].optimize = 2
air_conditioner[0].position = [8.800000190734863, 4.551384449005127, 0.16500000655651093]
air_conditioner[0].rotation = [0, 0, -1.5665798159440414]
air_conditioner[0].optimize = 2

