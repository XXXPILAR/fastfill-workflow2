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
dining_chair_A = Assets(description="A wooden bar stool with a black cushioned seat and backrest. It has four legs connected by a horizontal support bar.", size=[0.52, 0.46, 1.02], placements=[AssetInstance() for _ in range(1)])
dining_chair_B = Assets(description="A wooden bar stool with a black cushioned seat and backrest. It has four legs connected by a horizontal support bar.", size=[0.52, 0.46, 1.02], placements=[AssetInstance() for _ in range(1)])
dining_chair_C = Assets(description="A wooden bar stool with a black cushioned seat and backrest. It has four legs connected by a horizontal support bar.", size=[0.52, 0.46, 1.02], placements=[AssetInstance() for _ in range(1)])
sideboard = Assets(description="A dark-colored sideboard with a sleek design, featuring multiple compartments and thin legs. It is accompanied by a small object that appears to be a smartphone or remote control.", size=[0.45, 1.80, 0.80], placements=[AssetInstance() for _ in range(1)])
dining_chair_D = Assets(description="A wooden bar stool with a black cushioned seat and backrest. It has four legs connected by a horizontal support bar.", size=[0.52, 0.46, 1.02], placements=[AssetInstance() for _ in range(1)])
dining_chair_E = Assets(description="A wooden bar stool with a black cushioned seat and backrest. It has four legs connected by a horizontal support bar.", size=[0.52, 0.46, 1.02], placements=[AssetInstance() for _ in range(1)])
dining_chair_F = Assets(description="A wooden bar stool with a black cushioned seat and backrest. It has four legs connected by a horizontal support bar.", size=[0.52, 0.46, 1.02], placements=[AssetInstance() for _ in range(1)])
dining_table = Assets(description="A sleek, modern dining table with a rectangular top and four slender legs that taper towards the bottom. The table has a dark finish, giving it a sophisticated appearance.", size=[0.90, 1.90, 0.92], placements=[AssetInstance() for _ in range(1)])

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

dining_chair_A[0].position = [1.2530943193102395, 1.4781616645973332, 0.51]
dining_chair_A[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [3.9698899197108415, 1.9203135870670336, 0.51]
dining_chair_B[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [4.250208217658115, 5.42788387247984, 0.51]
dining_chair_C[0].rotation = [0, 0, 0]
sideboard[0].position = [3.906557323697495, 3.179963789625535, 0.4]
sideboard[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [1.1300310792117645, 1.5117780532540894, 0.51]
dining_chair_D[0].rotation = [0, 0, 0]
dining_chair_E[0].position = [3.9014206679785834, 3.38345104525467, 0.51]
dining_chair_E[0].rotation = [0, 0, 0]
dining_chair_F[0].position = [1.7808937671898581, 5.7637978623956165, 0.51]
dining_chair_F[0].rotation = [0, 0, 0]
dining_table[0].position = [4.04815771132319, 0.020979321959589937, 0.46]
dining_table[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [1.2530943193102395, 1.4781616645973332, 0.51]
dining_chair_A[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [3.9698899197108415, 1.9203135870670336, 0.51]
dining_chair_B[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [4.250208217658115, 5.42788387247984, 0.51]
dining_chair_C[0].rotation = [0, 0, 0]
sideboard[0].position = [3.906557323697495, 3.179963789625535, 0.4]
sideboard[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [1.1300310792117645, 1.5117780532540894, 0.51]
dining_chair_D[0].rotation = [0, 0, 0]
dining_chair_E[0].position = [3.9014206679785834, 3.38345104525467, 0.51]
dining_chair_E[0].rotation = [0, 0, 0]
dining_chair_F[0].position = [1.7808937671898581, 5.7637978623956165, 0.51]
dining_chair_F[0].rotation = [0, 0, 0]
dining_table[0].position = [4.04815771132319, 0.020979321959589937, 0.46]
dining_table[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the main rectangular room for dining; leave the entire northern
# entrance area clear. Asset order maps A/B/C to o0000/o0001/o0002.
dining_table[0].position = [2.15, 3.20, 0.46]
dining_table[0].rotation = [0, 0, 0]

# The sideboard's shallow dimension is along x, against the east wall.
sideboard[0].position = [4.125, 2.75, 0.40]
sideboard[0].rotation = [0, 0, radians(180)]

# A and C occupy opposite ends, with the table between them.
# B faces east toward the sideboard. The remaining chairs complete
# two pairs along the long sides without touching the table or each other.
chair_layout = [
    (dining_chair_A, [2.15, 1.85, 0.51], 90),
    (dining_chair_B, [1.20, 2.75, 0.51], 0),
    (dining_chair_C, [2.15, 4.55, 0.51], -90),
    (dining_chair_D, [1.20, 3.65, 0.51], 0),
    (dining_chair_E, [3.10, 2.75, 0.51], 180),
    (dining_chair_F, [3.10, 3.65, 0.51], 180),
]

for chair_asset, chair_position, chair_yaw in chair_layout:
    chair_asset[0].position = chair_position
    chair_asset[0].rotation = [0, 0, radians(chair_yaw)]

# Prioritize the wall requirement and overall location before secondary
# spacing constraints. Fixed points are constraint references, not furniture.
solver.against_wall(sideboard[0], walls[0])
solver.distance_constraint(
    sideboard[0],
    AssetInstance(position=[4.125, 2.75, 0.40]),
    0, 0.05, weight=10
)
solver.align_with(
    sideboard[0],
    AssetInstance(rotation=[0, 0, radians(180)])
)

solver.distance_constraint(
    dining_table[0],
    AssetInstance(position=[2.15, 3.20, 0.46]),
    0, 0, weight=10
)
solver.align_with(
    dining_table[0],
    AssetInstance(rotation=[0, 0, 0])
)

# Small positional tolerances preserve the seating arrangement and keep
# the furniture well south of every doorway.
for chair_asset, chair_position, chair_yaw in chair_layout:
    solver.distance_constraint(
        chair_asset[0],
        AssetInstance(position=list(chair_position)),
        0, 0.06, weight=10
    )

# Explicitly preserve the requested facing relationship for chair B.
solver.point_towards(dining_chair_B[0], sideboard[0])

# End chairs face the table directly; side chairs remain parallel to x,
# rather than turning diagonally toward the table center.
solver.point_towards(dining_chair_A[0], dining_table[0])
solver.point_towards(dining_chair_C[0], dining_table[0])
solver.align_with(dining_chair_D[0], dining_table[0])
solver.align_with(dining_chair_E[0], dining_table[0], angle=180)
solver.align_with(dining_chair_F[0], dining_table[0], angle=180)

# Maintain practical chair-to-table spacing using bounding-box centers.
for chair_asset in (dining_chair_A, dining_chair_C):
    solver.distance_constraint(
        chair_asset[0], dining_table[0], 1.29, 1.42, weight=10
    )

for chair_asset in (
    dining_chair_B, dining_chair_D, dining_chair_E, dining_chair_F
):
    solver.distance_constraint(
        chair_asset[0], dining_table[0], 0.99, 1.12, weight=10
    )

# Preserve separation between neighboring chairs and the serving cabinet.
solver.distance_constraint(
    dining_chair_D[0], dining_chair_B[0], 0.78, 1.02
)
solver.distance_constraint(
    dining_chair_F[0], dining_chair_E[0], 0.78, 1.02
)
for chair_asset in (dining_chair_E, dining_chair_F):
    solver.distance_constraint(
        chair_asset[0], sideboard[0], 0.95, None, weight=10
    )

# All assets are floor-standing; no on_top_of constraints are needed.

solver.constraints = []
dining_table[0].position = [2.1500000953674316, 3.200000047683716, 0.46000000834465027]
dining_table[0].rotation = [0, 0, 0.043982298440307294]
dining_table[0].optimize = 2
sideboard[0].position = [4.127199649810791, 2.75, 0.4000000059604645]
sideboard[0].rotation = [0, 0, 3.141591902840924]
sideboard[0].optimize = 2
dining_chair_A[0].position = [2.1500000953674316, 1.850000023841858, 0.5099999904632568]
dining_chair_A[0].rotation = [0, 0, 1.5833626980517244]
dining_chair_A[0].optimize = 2
dining_chair_C[0].position = [2.1500000953674316, 4.550000190734863, 0.5099999904632568]
dining_chair_C[0].rotation = [0, 0, -1.5582299555380688]
dining_chair_C[0].optimize = 2
dining_chair_B[0].position = [1.2000000476837158, 2.75, 0.5099999904632568]
dining_chair_B[0].rotation = [0, 0, 0.0157079639172164]
dining_chair_B[0].optimize = 2
dining_chair_E[0].position = [3.0999999046325684, 2.75, 0.5099999904632568]
dining_chair_E[0].rotation = [0, 0, -3.09761121477124]
dining_chair_E[0].optimize = 2
dining_chair_D[0].position = [1.2000000476837158, 3.6500000953674316, 0.5099999904632568]
dining_chair_D[0].rotation = [0, 0, 0.04398151509024543]
dining_chair_D[0].optimize = 2
dining_chair_F[0].position = [3.0999999046325684, 3.6500000953674316, 0.5099999904632568]
dining_chair_F[0].rotation = [0, 0, -3.09761121477124]
dining_chair_F[0].optimize = 2

