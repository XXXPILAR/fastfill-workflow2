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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.43, 0.00, 0.00]),
    Wall(corner1=[3.43, 0.00, 0.00], corner2=[3.43, 3.12, 0.00]),
    Wall(corner1=[3.43, 3.12, 0.00], corner2=[1.02, 3.12, 0.00]),
    Wall(corner1=[1.02, 3.12, 0.00], corner2=[1.02, 2.56, 0.00]),
    Wall(corner1=[1.02, 2.56, 0.00], corner2=[0.90, 2.56, 0.00]),
    Wall(corner1=[0.90, 2.56, 0.00], corner2=[0.90, 4.70, 0.00]),
    Wall(corner1=[0.90, 4.70, 0.00], corner2=[0.00, 4.70, 0.00]),
    Wall(corner1=[0.00, 4.70, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
stool = Assets(description="stool", size=[0.40, 0.45, 0.45], placements=[AssetInstance() for _ in range(1)])
nightstand_A = Assets(description="nightstand", size=[0.40, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.60, 1.80, 2.20], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.00, 1.60, 0.55], placements=[AssetInstance() for _ in range(1)])
dressing_table = Assets(description="dressing table", size=[0.45, 1.10, 0.75], placements=[AssetInstance() for _ in range(1)])
nightstand_B = Assets(description="nightstand", size=[0.40, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])

stool[0].instance_id = 'stool_0'
nightstand_A[0].instance_id = 'nightstand_A_0'
wardrobe[0].instance_id = 'wardrobe_0'
bed[0].instance_id = 'bed_0'
dressing_table[0].instance_id = 'dressing_table_0'
nightstand_B[0].instance_id = 'nightstand_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

stool[0].position = [1.4196206935073388, 1.7963742563258298, 0.225]
stool[0].rotation = [0, 0, 0]
nightstand_A[0].position = [2.803124930088456, 1.7151158927829475, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.1637424629118318, 2.943366629129129, 1.1]
wardrobe[0].rotation = [0, 0, 0]
bed[0].position = [3.2263718955755962, 2.5690681737525494, 0.275]
bed[0].rotation = [0, 0, 0]
dressing_table[0].position = [2.355258992810441, 1.2430114027467565, 0.375]
dressing_table[0].rotation = [0, 0, 0]
nightstand_B[0].position = [1.195191253473365, 0.09025447014783404, 0.275]
nightstand_B[0].rotation = [0, 0, 0]
stool[0].position = [1.4196206935073388, 1.7963742563258298, 0.225]
stool[0].rotation = [0, 0, 0]
nightstand_A[0].position = [2.803124930088456, 1.7151158927829475, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.1637424629118318, 2.943366629129129, 1.1]
wardrobe[0].rotation = [0, 0, 0]
bed[0].position = [3.2263718955755962, 2.5690681737525494, 0.275]
bed[0].rotation = [0, 0, 0]
dressing_table[0].position = [2.355258992810441, 1.2430114027467565, 0.375]
dressing_table[0].rotation = [0, 0, 0]
nightstand_B[0].position = [1.195191253473365, 0.09025447014783404, 0.275]
nightstand_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the bed along the right wall, with the two nightstands flanking it.
# This keeps the window wall and both door approaches unobstructed.
stool[0].position = [0.95, 1.52, 0.225]
stool[0].rotation = [0, 0, radians(0)]

nightstand_A[0].position = [3.23, 0.42, 0.275]
nightstand_A[0].rotation = [0, 0, radians(180)]

wardrobe[0].position = [0.30, 1.35, 1.10]
wardrobe[0].rotation = [0, 0, radians(0)]

bed[0].position = [2.43, 1.52, 0.275]
bed[0].rotation = [0, 0, radians(180)]

dressing_table[0].position = [2.25, 2.895, 0.375]
dressing_table[0].rotation = [0, 0, radians(-90)]

nightstand_B[0].position = [3.23, 2.67, 0.275]
nightstand_B[0].rotation = [0, 0, radians(180)]


# Fixed anchors preserve the intended positions along each wall while allowing
# the semantic wall and object-to-object constraints below to remain explicit.
stool_anchor = AssetInstance(position=[0.95, 1.52, 0.225])
nightstand_A_anchor = AssetInstance(position=[3.23, 0.42, 0.275])
wardrobe_anchor = AssetInstance(position=[0.30, 1.35, 1.10])
bed_anchor = AssetInstance(position=[2.43, 1.52, 0.275])
dressing_table_anchor = AssetInstance(position=[2.25, 2.895, 0.375])
nightstand_B_anchor = AssetInstance(position=[3.23, 2.67, 0.275])
room_center = AssetInstance(position=[1.72, 1.56, 0.50])


# The required wall-backed nightstand is constrained first because it is a
# high-priority layout criterion. Both nightstands flank the bed on this wall.
solver.against_wall(nightstand_A[0], walls[1])
solver.distance_constraint(
    nightstand_A[0], nightstand_A_anchor, 0.0, 0.0, weight=10
)
solver.align_with(nightstand_A[0], bed[0])

solver.against_wall(nightstand_B[0], walls[1])
solver.distance_constraint(
    nightstand_B[0], nightstand_B_anchor, 0.0, 0.0, weight=10
)
solver.align_with(nightstand_B[0], bed[0])


# The bed is centered between the nightstands, backed by the right wall, and
# oriented toward the stool at its foot.
solver.against_wall(bed[0], walls[1])
solver.distance_constraint(bed[0], bed_anchor, 0.0, 0.0, weight=10)
solver.point_towards(bed[0], stool[0])

# These symmetric distance relationships preserve the bedside grouping.
solver.distance_constraint(bed[0], nightstand_A[0], 1.34, 1.40, weight=10)
solver.distance_constraint(bed[0], nightstand_B[0], 1.34, 1.40, weight=10)


# Place the stool directly in front of the bed without obstructing the window.
solver.distance_constraint(stool[0], stool_anchor, 0.0, 0.0, weight=10)
solver.distance_constraint(stool[0], bed[0], 1.45, 1.55, weight=10)
solver.point_towards(stool[0], bed[0])


# The wardrobe uses the long left wall and faces into the room.
solver.against_wall(wardrobe[0], walls[7])
solver.distance_constraint(wardrobe[0], wardrobe_anchor, 0.0, 0.0, weight=10)
solver.point_towards(wardrobe[0], room_center)


# The dressing table occupies the upper wall of the main rectangular area,
# remaining below and clear of the two doorways in the narrow extension.
solver.against_wall(dressing_table[0], walls[2])
solver.distance_constraint(
    dressing_table[0], dressing_table_anchor, 0.0, 0.0, weight=10
)
solver.point_towards(dressing_table[0], room_center)

solver.constraints = []
stool[0].position = [0.949999988079071, 1.5199999809265137, 0.22499999403953552]
stool[0].rotation = [0, 0, 0.0157079639172164]
stool[0].optimize = 2
bed[0].position = [2.4269073009490967, 1.5199999809265137, 0.2750000059604645]
bed[0].rotation = [0, 0, 3.1415568652989645]
bed[0].optimize = 2
nightstand_A[0].position = [3.2268240451812744, 0.41999998688697815, 0.2750000059604645]
nightstand_A[0].rotation = [0, 0, 3.1415432625532302]
nightstand_A[0].optimize = 2
nightstand_B[0].position = [3.1783339977264404, 2.6700000762939453, 0.2750000059604645]
nightstand_B[0].rotation = [0, 0, -1.5633521207938375]
nightstand_B[0].optimize = 2
wardrobe[0].position = [0.30000489950180054, 1.350000023841858, 1.100000023841858]
wardrobe[0].rotation = [0, 0, -4.683351953042869e-05]
wardrobe[0].optimize = 2
dressing_table[0].position = [2.25, 2.8918395042419434, 0.375]
dressing_table[0].rotation = [0, 0, -1.5708432798984517]
dressing_table[0].optimize = 2

