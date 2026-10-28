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
    Wall(corner1=[5.68, 5.25, 0.00], corner2=[5.40, 5.25, 0.00]),
    Wall(corner1=[5.40, 5.25, 0.00], corner2=[5.40, 8.90, 0.00]),
    Wall(corner1=[5.40, 8.90, 0.00], corner2=[2.97, 8.90, 0.00]),
    Wall(corner1=[2.97, 8.90, 0.00], corner2=[2.97, 7.17, 0.00]),
    Wall(corner1=[2.97, 7.17, 0.00], corner2=[0.00, 7.17, 0.00]),
    Wall(corner1=[0.00, 7.17, 0.00], corner2=[0.00, 5.95, 0.00]),
    Wall(corner1=[0.00, 5.95, 0.00], corner2=[1.46, 5.95, 0.00]),
    Wall(corner1=[1.46, 5.95, 0.00], corner2=[1.46, 0.00, 0.00]),
    Wall(corner1=[1.46, 0.00, 0.00], corner2=[5.68, 0.00, 0.00]),
    Wall(corner1=[5.68, 0.00, 0.00], corner2=[5.68, 5.25, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
table = Assets(description="table", size=[0.60, 1.20, 0.45], placements=[AssetInstance() for _ in range(1)])
sofa = Assets(description="sofa", size=[0.90, 2.20, 0.85], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.40, 1.60, 0.80], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.45, 1.80, 0.65], placements=[AssetInstance() for _ in range(1)])

table[0].instance_id = 'table_0'
sofa[0].instance_id = 'sofa_0'
cabinet_A[0].instance_id = 'cabinet_A_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
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

table[0].position = [4.675507995105283, 4.92078751828766, 0.225]
table[0].rotation = [0, 0, 0]
sofa[0].position = [3.7960685806274546, 6.114547557190595, 0.425]
sofa[0].rotation = [0, 0, 0]
cabinet_A[0].position = [3.296265339980517, 4.78446617192055, 0.4]
cabinet_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [4.450492814072269, 3.608572082939806, 0.325]
cabinet_B[0].rotation = [0, 0, 0]
table[0].position = [4.675507995105283, 4.92078751828766, 0.225]
table[0].rotation = [0, 0, 0]
sofa[0].position = [3.7960685806274546, 6.114547557190595, 0.425]
sofa[0].rotation = [0, 0, 0]
cabinet_A[0].position = [3.296265339980517, 4.78446617192055, 0.4]
cabinet_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [4.450492814072269, 3.608572082939806, 0.325]
cabinet_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the furniture in the lower part of the room, away from all five
# door openings. The sofa, table, and cabinet_B form a functional seating
# group, while cabinet_A is placed against the opposite wall.
table[0].position = [4.00, 3.80, 0.225]
table[0].rotation = [0, 0, radians(0)]

sofa[0].position = [2.65, 3.80, 0.425]
sofa[0].rotation = [0, 0, radians(0)]

# cabinet_A (o0002) is backed against the lower-left wall and faces inward.
cabinet_A[0].position = [1.66, 3.80, 0.40]
cabinet_A[0].rotation = [0, 0, radians(0)]

# cabinet_B (o0003) is backed against the lower-right wall. Its front faces
# toward the sofa, so the sofa and cabinet face one another.
cabinet_B[0].position = [5.455, 3.80, 0.325]
cabinet_B[0].rotation = [0, 0, radians(180)]

# Fixed reference points preserve the door-safe furniture group within the
# broad lower portion of the irregular floor plan.
table_anchor = AssetInstance(position=[4.00, 3.80, 0.225])
sofa_anchor = AssetInstance(position=[2.65, 3.80, 0.425])
cabinet_A_anchor = AssetInstance(position=[1.66, 3.80, 0.40])
cabinet_B_anchor = AssetInstance(position=[5.455, 3.80, 0.325])

# Wall constraints are the highest-priority positional requirements for the
# two cabinets. walls[7] is the lower-left wall and walls[9] is the
# lower-right wall.
solver.against_wall(cabinet_A[0], walls[7])
solver.against_wall(cabinet_B[0], walls[9])

# Anchor every asset so the arrangement remains inside the room and clear of
# the circulation paths in front of the doors.
solver.distance_constraint(table[0], table_anchor, 0, 0, weight=10)
solver.distance_constraint(sofa[0], sofa_anchor, 0, 0, weight=10)
solver.distance_constraint(cabinet_A[0], cabinet_A_anchor, 0, 0, weight=10)
solver.distance_constraint(cabinet_B[0], cabinet_B_anchor, 0, 0, weight=10)

# Preserve useful spacing within the furniture group. These center-distance
# ranges leave clear gaps between the assets' bounding boxes.
solver.distance_constraint(sofa[0], cabinet_B[0], 2.70, 2.90, weight=1)
solver.distance_constraint(table[0], sofa[0], 1.25, 1.45, weight=1)
solver.distance_constraint(table[0], cabinet_B[0], 1.35, 1.55, weight=1)
solver.distance_constraint(cabinet_A[0], sofa[0], 0.85, 1.15, weight=1)

# Orientation constraints for every new asset. The sofa explicitly faces
# cabinet_B (o0003); cabinet_B faces back toward the sofa. cabinet_A faces
# inward, and the table is aligned with the seating group.
solver.point_towards(sofa[0], cabinet_B[0])
solver.point_towards(cabinet_B[0], sofa[0])
solver.point_towards(cabinet_A[0], sofa[0])
solver.align_with(table[0], sofa[0])

solver.constraints = []
table[0].position = [4.165653705596924, 4.733095645904541, 0.22499999403953552]
table[0].rotation = [0, 0, 0.281573728249546]
table[0].optimize = 2
cabinet_A[0].position = [1.68173086643219, 4.099737644195557, 0.4000000059604645]
cabinet_A[0].rotation = [0, 0, 2.4334473317114742e-08]
cabinet_A[0].optimize = 2
cabinet_B[0].position = [5.174600124359131, 5.896450996398926, 0.32499998807907104]
cabinet_B[0].rotation = [0, 0, -3.132496820037233]
cabinet_B[0].optimize = 2
sofa[0].position = [2.815431833267212, 4.266238212585449, 0.42500001192092896]
sofa[0].rotation = [0, 0, 0.28358366683876524]
sofa[0].optimize = 2

