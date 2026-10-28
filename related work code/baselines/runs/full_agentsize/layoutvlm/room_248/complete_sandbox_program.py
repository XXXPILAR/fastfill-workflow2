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
    Wall(corner1=[5.79, 2.95, 0.00], corner2=[5.79, 0.00, 0.00]),
    Wall(corner1=[5.79, 0.00, 0.00], corner2=[9.57, 0.00, 0.00]),
    Wall(corner1=[9.57, 0.00, 0.00], corner2=[9.57, 8.88, 0.00]),
    Wall(corner1=[9.57, 8.88, 0.00], corner2=[5.02, 8.88, 0.00]),
    Wall(corner1=[5.02, 8.88, 0.00], corner2=[5.02, 4.25, 0.00]),
    Wall(corner1=[5.02, 4.25, 0.00], corner2=[0.00, 4.25, 0.00]),
    Wall(corner1=[0.00, 4.25, 0.00], corner2=[0.00, 2.91, 0.00]),
    Wall(corner1=[0.00, 2.91, 0.00], corner2=[3.81, 2.91, 0.00]),
    Wall(corner1=[3.81, 2.91, 0.00], corner2=[3.81, 1.88, 0.00]),
    Wall(corner1=[3.81, 1.88, 0.00], corner2=[5.55, 1.88, 0.00]),
    Wall(corner1=[5.55, 1.88, 0.00], corner2=[5.55, 2.71, 0.00]),
    Wall(corner1=[5.55, 2.71, 0.00], corner2=[4.92, 2.71, 0.00]),
    Wall(corner1=[4.92, 2.71, 0.00], corner2=[4.92, 2.95, 0.00]),
    Wall(corner1=[4.92, 2.95, 0.00], corner2=[5.79, 2.95, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
dining_table = Assets(description="dining table", size=[1.00, 2.20, 0.76], placements=[AssetInstance() for _ in range(1)])
dining_chair_A = Assets(description="dining chair", size=[0.55, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
dining_chair_B = Assets(description="dining chair", size=[0.55, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
shoe_cabinet = Assets(description="shoe cabinet", size=[0.35, 1.20, 1.00], placements=[AssetInstance() for _ in range(1)])
dining_chair_C = Assets(description="dining chair", size=[0.55, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])
dining_chair_D = Assets(description="dining chair", size=[0.55, 0.48, 0.90], placements=[AssetInstance() for _ in range(1)])

dining_table[0].instance_id = 'dining_table_0'
dining_chair_A[0].instance_id = 'dining_chair_A_0'
dining_chair_B[0].instance_id = 'dining_chair_B_0'
shoe_cabinet[0].instance_id = 'shoe_cabinet_0'
dining_chair_C[0].instance_id = 'dining_chair_C_0'
dining_chair_D[0].instance_id = 'dining_chair_D_0'
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

dining_table[0].position = [5.649239011338046, 4.560448064854639, 0.38]
dining_table[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [5.337020016912084, 6.337732317419376, 0.45]
dining_chair_A[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [6.090034907620814, 7.98557248187091, 0.45]
dining_chair_B[0].rotation = [0, 0, 0]
shoe_cabinet[0].position = [7.075073209790763, 6.452443828976965, 0.5]
shoe_cabinet[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [6.365930978902974, 5.425178936108897, 0.45]
dining_chair_C[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [9.093087075205851, 0.3551254028298814, 0.45]
dining_chair_D[0].rotation = [0, 0, 0]
dining_table[0].position = [5.649239011338046, 4.560448064854639, 0.38]
dining_table[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [5.337020016912084, 6.337732317419376, 0.45]
dining_chair_A[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [6.090034907620814, 7.98557248187091, 0.45]
dining_chair_B[0].rotation = [0, 0, 0]
shoe_cabinet[0].position = [7.075073209790763, 6.452443828976965, 0.5]
shoe_cabinet[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [6.365930978902974, 5.425178936108897, 0.45]
dining_chair_C[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [9.093087075205851, 0.3551254028298814, 0.45]
dining_chair_D[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the dining table horizontally in the upper room, leaving the large
# doorway at y=8.88 and the fixed TV cabinet on the right unobstructed.
dining_table[0].position = [6.72, 6.60, dining_table.size[2] / 2]
dining_table[0].rotation = [0, 0, radians(90)]

# o0001: chair at the lower end of the table, facing toward it.
dining_chair_A[0].position = [6.72, 5.80, dining_chair_A.size[2] / 2]
dining_chair_A[0].rotation = [0, 0, radians(90)]

# o0002 and o0004 are adjacent along the left wall. Their centers are 0.50 m
# apart, while their 0.48 m widths leave a small non-overlap gap. The table's
# y-coordinate lies between their y-coordinates as requested.
dining_chair_B[0].position = [5.295, 6.85, dining_chair_B.size[2] / 2]
dining_chair_B[0].rotation = [0, 0, radians(0)]

dining_chair_C[0].position = [5.295, 6.35, dining_chair_C.size[2] / 2]
dining_chair_C[0].rotation = [0, 0, radians(0)]

# o0005 is opposite o0001 and faces it across the table.
dining_chair_D[0].position = [6.72, 7.40, dining_chair_D.size[2] / 2]
dining_chair_D[0].rotation = [0, 0, radians(-90)]

# Place the shallow shoe cabinet on the lower portion of the right wall,
# away from the fixed TV cabinet and from both bottom-door approach paths.
shoe_cabinet[0].position = [9.395, 2.80, shoe_cabinet.size[2] / 2]
shoe_cabinet[0].rotation = [0, 0, radians(180)]

# Fixed target points preserve the intended furniture arrangement while
# allowing the relational constraints below to express its semantics.
table_anchor = AssetInstance(position=[6.72, 6.60, dining_table.size[2] / 2])
chair_A_anchor = AssetInstance(position=[6.72, 5.80, dining_chair_A.size[2] / 2])
chair_B_anchor = AssetInstance(position=[5.295, 6.85, dining_chair_B.size[2] / 2])
chair_C_anchor = AssetInstance(position=[5.295, 6.35, dining_chair_C.size[2] / 2])
chair_D_anchor = AssetInstance(position=[6.72, 7.40, dining_chair_D.size[2] / 2])
shoe_anchor = AssetInstance(position=[9.395, 2.80, shoe_cabinet.size[2] / 2])
shoe_interior_target = AssetInstance(position=[8.20, 2.80, shoe_cabinet.size[2] / 2])

# Important semantic constraints are specified first.
solver.against_wall(dining_chair_C[0], walls[4])
solver.distance_constraint(
    dining_chair_B[0], dining_chair_C[0],
    min_distance=0.48, max_distance=0.50, weight=10
)

# Equal table-to-chair distances, together with the anchors, preserve the
# table's centered y-coordinate between o0002 and o0004.
solver.distance_constraint(
    dining_table[0], dining_chair_B[0],
    min_distance=1.44, max_distance=1.46, weight=10
)
solver.distance_constraint(
    dining_table[0], dining_chair_C[0],
    min_distance=1.44, max_distance=1.46, weight=10
)

# Keep each member of the dining group at its collision-free target.
solver.distance_constraint(
    dining_table[0], table_anchor, 0.0, 0.0, weight=10
)
solver.distance_constraint(
    dining_chair_A[0], chair_A_anchor, 0.0, 0.0, weight=10
)
solver.distance_constraint(
    dining_chair_B[0], chair_B_anchor, 0.0, 0.0, weight=10
)
solver.distance_constraint(
    dining_chair_C[0], chair_C_anchor, 0.0, 0.0, weight=10
)
solver.distance_constraint(
    dining_chair_D[0], chair_D_anchor, 0.0, 0.0, weight=10
)

# Orient the table and chairs as a coherent dining arrangement.
solver.align_with(dining_table[0], dining_chair_A[0], angle=0)
solver.point_towards(dining_chair_A[0], dining_table[0])
solver.point_towards(dining_chair_B[0], dining_table[0])
solver.point_towards(dining_chair_C[0], dining_table[0])
solver.point_towards(dining_chair_D[0], dining_chair_A[0])

# Constrain and orient the shoe cabinet against the right wall, facing inward.
solver.against_wall(shoe_cabinet[0], walls[2])
solver.distance_constraint(
    shoe_cabinet[0], shoe_anchor, 0.0, 0.0, weight=10
)
solver.point_towards(shoe_cabinet[0], shoe_interior_target)

solver.constraints = []
dining_chair_C[0].position = [5.340625762939453, 6.349999904632568, 0.44999998807907104]
dining_chair_C[0].rotation = [0, 0, -3.1415565515210306]
dining_chair_C[0].optimize = 2
dining_chair_A[0].position = [6.71999979019165, 5.800000190734863, 0.44999998807907104]
dining_chair_A[0].rotation = [0, 0, 1.586504290712113]
dining_chair_A[0].optimize = 2
shoe_cabinet[0].position = [8.972819328308105, 2.799999952316284, 0.5]
shoe_cabinet[0].rotation = [0, 0, -1.570795143226037]
shoe_cabinet[0].optimize = 2
dining_chair_D[0].position = [6.71999979019165, 7.400000095367432, 0.44999998807907104]
dining_chair_D[0].rotation = [0, 0, -1.5613715493341729]
dining_chair_D[0].optimize = 2
dining_chair_B[0].position = [5.295000076293945, 6.849999904632568, 0.44999998807907104]
dining_chair_B[0].rotation = [0, 0, 0.0157079639172164]
dining_chair_B[0].optimize = 2
dining_table[0].position = [6.7381815910339355, 6.70808744430542, 0.3799999952316284]
dining_table[0].rotation = [0, 0, 1.5865042892361003]
dining_table[0].optimize = 2

