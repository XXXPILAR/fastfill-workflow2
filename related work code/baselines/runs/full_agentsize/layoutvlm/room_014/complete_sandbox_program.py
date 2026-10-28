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
    Wall(corner1=[4.35, 0.00, 0.00], corner2=[4.35, 6.05, 0.00]),
    Wall(corner1=[4.35, 6.05, 0.00], corner2=[7.68, 6.05, 0.00]),
    Wall(corner1=[7.68, 6.05, 0.00], corner2=[7.68, 7.01, 0.00]),
    Wall(corner1=[7.68, 7.01, 0.00], corner2=[6.54, 7.01, 0.00]),
    Wall(corner1=[6.54, 7.01, 0.00], corner2=[6.54, 7.92, 0.00]),
    Wall(corner1=[6.54, 7.92, 0.00], corner2=[0.00, 7.92, 0.00]),
    Wall(corner1=[0.00, 7.92, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.35, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
dining_chair_A = Assets(description="A wooden bar stool with a black cushioned seat and backrest. It has four legs connected by a horizontal support bar.", size=[0.52, 0.48, 1.05], placements=[AssetInstance() for _ in range(1)])
dining_chair_B = Assets(description="A wooden bar stool with a black cushioned seat and backrest. It has four legs connected by a horizontal support bar.", size=[0.52, 0.48, 1.05], placements=[AssetInstance() for _ in range(1)])
dining_chair_C = Assets(description="A wooden bar stool with a black cushioned seat and backrest. It has four legs connected by a horizontal support bar.", size=[0.52, 0.48, 1.05], placements=[AssetInstance() for _ in range(1)])
sideboard = Assets(description="A dark-colored sideboard with a sleek design, featuring multiple compartments and thin legs. It is accompanied by a small object that appears to be a smartphone or remote control.", size=[0.45, 1.80, 0.75], placements=[AssetInstance() for _ in range(1)])
dining_chair_D = Assets(description="A wooden bar stool with a black cushioned seat and backrest. It has four legs connected by a horizontal support bar.", size=[0.52, 0.48, 1.05], placements=[AssetInstance() for _ in range(1)])
dining_chair_E = Assets(description="A wooden bar stool with a black cushioned seat and backrest. It has four legs connected by a horizontal support bar.", size=[0.52, 0.48, 1.05], placements=[AssetInstance() for _ in range(1)])
dining_chair_F = Assets(description="A wooden bar stool with a black cushioned seat and backrest. It has four legs connected by a horizontal support bar.", size=[0.52, 0.48, 1.05], placements=[AssetInstance() for _ in range(1)])
dining_table = Assets(description="A sleek, modern dining table with a rectangular top and four slender legs that taper towards the bottom. The table has a dark finish, giving it a sophisticated appearance.", size=[1.00, 2.20, 0.76], placements=[AssetInstance() for _ in range(1)])

dining_chair_A[0].instance_id = 'dining_chair_A_0'
dining_chair_B[0].instance_id = 'dining_chair_B_0'
dining_chair_C[0].instance_id = 'dining_chair_C_0'
sideboard[0].instance_id = 'sideboard_0'
dining_chair_D[0].instance_id = 'dining_chair_D_0'
dining_chair_E[0].instance_id = 'dining_chair_E_0'
dining_chair_F[0].instance_id = 'dining_chair_F_0'
dining_table[0].instance_id = 'dining_table_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

dining_chair_A[0].position = [0.45743007773193634, 1.5291334932402874, 0.525]
dining_chair_A[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [1.9046951263982534, 6.269357662273504, 0.525]
dining_chair_B[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [0.9897839189590006, 1.5809532708456586, 0.525]
dining_chair_C[0].rotation = [0, 0, 0]
sideboard[0].position = [2.2901516356888525, 4.8349590383456675, 0.375]
sideboard[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [0.7898757446693647, 2.96314016486897, 0.525]
dining_chair_D[0].rotation = [0, 0, 0]
dining_chair_E[0].position = [3.463940322068143, 6.3180021592622975, 0.525]
dining_chair_E[0].rotation = [0, 0, 0]
dining_chair_F[0].position = [0.7671156786950032, 6.6152336975423855, 0.525]
dining_chair_F[0].rotation = [0, 0, 0]
dining_table[0].position = [3.0530352850173386, 2.4525359579763912, 0.38]
dining_table[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [0.45743007773193634, 1.5291334932402874, 0.525]
dining_chair_A[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [1.9046951263982534, 6.269357662273504, 0.525]
dining_chair_B[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [0.9897839189590006, 1.5809532708456586, 0.525]
dining_chair_C[0].rotation = [0, 0, 0]
sideboard[0].position = [2.2901516356888525, 4.8349590383456675, 0.375]
sideboard[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [0.7898757446693647, 2.96314016486897, 0.525]
dining_chair_D[0].rotation = [0, 0, 0]
dining_chair_E[0].position = [3.463940322068143, 6.3180021592622975, 0.525]
dining_chair_E[0].rotation = [0, 0, 0]
dining_chair_F[0].position = [0.7671156786950032, 6.6152336975423855, 0.525]
dining_chair_F[0].rotation = [0, 0, 0]
dining_table[0].position = [3.0530352850173386, 2.4525359579763912, 0.38]
dining_table[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the dining group in the lower-middle portion of the main room, away
# from the window and from all door approaches near y=6.0 and y=7.9.
# The table's long dimension runs north-south.
dining_table[0].position = [2.55, 3.50, dining_table.size[2] / 2]
dining_table[0].rotation = [0, 0, radians(0)]

# The sideboard sits flush against the left wall and faces into the room.
sideboard[0].position = [sideboard.size[0] / 2, 3.50, sideboard.size[2] / 2]
sideboard[0].rotation = [0, 0, radians(0)]

# Arrange three chairs along each long side of the table. Chairs A and B are
# opposite one another, so the dining table is directly between them.
dining_chair_A[0].position = [1.65, 3.50, dining_chair_A.size[2] / 2]
dining_chair_A[0].rotation = [0, 0, radians(0)]

dining_chair_B[0].position = [3.45, 3.50, dining_chair_B.size[2] / 2]
dining_chair_B[0].rotation = [0, 0, radians(180)]

# Chair C is specifically oriented toward the sideboard.
dining_chair_C[0].position = [1.65, 2.65, dining_chair_C.size[2] / 2]
dining_chair_C[0].rotation = [0, 0, radians(151)]

dining_chair_D[0].position = [3.45, 2.65, dining_chair_D.size[2] / 2]
dining_chair_D[0].rotation = [0, 0, radians(137)]

dining_chair_E[0].position = [1.65, 4.35, dining_chair_E.size[2] / 2]
dining_chair_E[0].rotation = [0, 0, radians(-43)]

dining_chair_F[0].position = [3.45, 4.35, dining_chair_F.size[2] / 2]
dining_chair_F[0].rotation = [0, 0, radians(-137)]

# Strong positional anchors preserve the proposed clearances and keep the
# complete dining arrangement away from doors and the window.
table_anchor = AssetInstance(position=[2.55, 3.50, dining_table.size[2] / 2])
sideboard_anchor = AssetInstance(
    position=[sideboard.size[0] / 2, 3.50, sideboard.size[2] / 2]
)
chair_A_anchor = AssetInstance(
    position=[1.65, 3.50, dining_chair_A.size[2] / 2]
)
chair_B_anchor = AssetInstance(
    position=[3.45, 3.50, dining_chair_B.size[2] / 2]
)
chair_C_anchor = AssetInstance(
    position=[1.65, 2.65, dining_chair_C.size[2] / 2]
)
chair_D_anchor = AssetInstance(
    position=[3.45, 2.65, dining_chair_D.size[2] / 2]
)
chair_E_anchor = AssetInstance(
    position=[1.65, 4.35, dining_chair_E.size[2] / 2]
)
chair_F_anchor = AssetInstance(
    position=[3.45, 4.35, dining_chair_F.size[2] / 2]
)

solver.distance_constraint(
    dining_table[0], table_anchor, 0, 0, weight=10
)

# The wall constraint is specified first because keeping the sideboard flush
# against the left wall is its most important positional requirement.
solver.against_wall(sideboard[0], walls[6])
solver.distance_constraint(
    sideboard[0], sideboard_anchor, 0, 0, weight=10
)

solver.distance_constraint(
    dining_chair_A[0], chair_A_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    dining_chair_B[0], chair_B_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    dining_chair_C[0], chair_C_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    dining_chair_D[0], chair_D_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    dining_chair_E[0], chair_E_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    dining_chair_F[0], chair_F_anchor, 0, 0, weight=10
)

# Preserve the table/sideboard orientation and make the sideboard face inward.
solver.align_with(dining_table[0], sideboard[0], angle=0)
solver.align_with(sideboard[0], dining_table[0], angle=0)

# Each chair receives an explicit orientation constraint. A and B remain
# opposite each other with the table between them; D, E, and F face the table.
solver.point_towards(dining_chair_A[0], dining_table[0])
solver.point_towards(dining_chair_B[0], dining_table[0])
solver.point_towards(dining_chair_C[0], sideboard[0])
solver.point_towards(dining_chair_D[0], dining_table[0])
solver.point_towards(dining_chair_E[0], dining_table[0])
solver.point_towards(dining_chair_F[0], dining_table[0])

solver.constraints = []
dining_chair_D[0].position = [3.450000047683716, 2.6500000953674316, 0.5249999761581421]
dining_chair_D[0].rotation = [0, 0, 2.400525829844029]
dining_chair_D[0].optimize = 2
dining_chair_C[0].position = [1.649999976158142, 2.6500000953674316, 0.5249999761581421]
dining_chair_C[0].rotation = [0, 0, 2.6448719456204715]
dining_chair_C[0].optimize = 2
sideboard[0].position = [0.22499999403953552, 3.5, 0.375]
sideboard[0].rotation = [0, 0, 3.529051433304495e-08]
sideboard[0].optimize = 2
dining_chair_B[0].position = [3.450000047683716, 3.5, 0.5249999761581421]
dining_chair_B[0].rotation = [0, 0, -3.1321678761290697]
dining_chair_B[0].optimize = 2
dining_chair_A[0].position = [1.649999976158142, 3.5, 0.5249999761581421]
dining_chair_A[0].rotation = [0, 0, 0.00942477746072377]
dining_chair_A[0].optimize = 2
dining_chair_F[0].position = [3.450000047683716, 4.349999904632568, 0.5249999761581421]
dining_chair_F[0].rotation = [0, 0, -2.381676281795821]
dining_chair_F[0].optimize = 2
dining_table[0].position = [2.549999952316284, 3.5, 0.3799999952316284]
dining_table[0].rotation = [0, 0, 5.578168778735198e-08]
dining_table[0].optimize = 2
dining_chair_E[0].position = [1.649999976158142, 4.349999904632568, 0.5249999761581421]
dining_chair_E[0].rotation = [0, 0, -0.7410668237457643]
dining_chair_E[0].optimize = 2

