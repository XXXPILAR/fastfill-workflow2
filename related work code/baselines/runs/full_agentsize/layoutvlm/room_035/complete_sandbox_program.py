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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.62, 0.00, 0.00]),
    Wall(corner1=[4.62, 0.00, 0.00], corner2=[4.62, 3.65, 0.00]),
    Wall(corner1=[4.62, 3.65, 0.00], corner2=[0.00, 3.65, 0.00]),
    Wall(corner1=[0.00, 3.65, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
drawer_chest = Assets(description="A wooden dresser with a dark gray top and three drawers featuring a quilted pattern and metallic handles. It has a simple design with four legs.", size=[0.45, 1.00, 0.85], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="A large wooden wardrobe with three doors, each featuring decorative panels and black handles. The wardrobe has a classic design with a slightly curved top edge and stands on small feet.", size=[0.60, 1.80, 2.10], placements=[AssetInstance() for _ in range(1)])
side_table = Assets(description="A cylindrical trash can with a smooth surface and a small decorative emblem on one side. It has an open top and a small rectangular opening near the bottom.", size=[0.30, 0.30, 0.50], placements=[AssetInstance() for _ in range(1)])
desk = Assets(description="An adjustable desk with a wooden tabletop and blue metal legs. It features a back panel with a cutout handle and a side drawer for storage.", size=[0.60, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
kids_bed = Assets(description="A modern bed with a dark gray wooden frame, featuring two pillows and a blanket in shades of green and gray. The bed appears unmade with the bedding slightly disheveled.", size=[2.00, 1.00, 0.65], placements=[AssetInstance() for _ in range(1)])

drawer_chest[0].instance_id = 'drawer_chest_0'
wardrobe[0].instance_id = 'wardrobe_0'
side_table[0].instance_id = 'side_table_0'
desk[0].instance_id = 'desk_0'
kids_bed[0].instance_id = 'kids_bed_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

drawer_chest[0].position = [1.646053164393676, 2.543342170415795, 0.425]
drawer_chest[0].rotation = [0, 0, 0]
wardrobe[0].position = [2.676437850411422, 2.4531915443920513, 1.05]
wardrobe[0].rotation = [0, 0, 0]
side_table[0].position = [2.9689484725601427, 2.2827731601451053, 0.25]
side_table[0].rotation = [0, 0, 0]
desk[0].position = [1.3749022941702607, 1.935025143522008, 0.375]
desk[0].rotation = [0, 0, 0]
kids_bed[0].position = [2.655564355536984, 2.7802741445603267, 0.325]
kids_bed[0].rotation = [0, 0, 0]
drawer_chest[0].position = [1.646053164393676, 2.543342170415795, 0.425]
drawer_chest[0].rotation = [0, 0, 0]
wardrobe[0].position = [2.676437850411422, 2.4531915443920513, 1.05]
wardrobe[0].rotation = [0, 0, 0]
side_table[0].position = [2.9689484725601427, 2.2827731601451053, 0.25]
side_table[0].rotation = [0, 0, 0]
desk[0].position = [1.3749022941702607, 1.935025143522008, 0.375]
desk[0].rotation = [0, 0, 0]
kids_bed[0].position = [2.655564355536984, 2.7802741445603267, 0.325]
kids_bed[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the bed along the south wall. Its slight counterclockwise rotation
# aims its front toward the drawer chest while keeping the entrance corridor clear.
kids_bed.placements[0].position = [1.75, 0.80, 0.325]
kids_bed.placements[0].rotation = [0, 0, radians(20)]

# Place the drawer chest against the east wall, beyond the door opening.
# It faces west toward the bed.
drawer_chest.placements[0].position = [4.395, 1.75, 0.425]
drawer_chest.placements[0].rotation = [0, 0, radians(180)]

# Place the wardrobe against the north wall, away from both the window and door.
wardrobe.placements[0].position = [3.55, 3.35, 1.05]
wardrobe.placements[0].rotation = [0, 0, radians(-90)]

# Put the desk beneath the window on the west wall, facing into the room.
desk.placements[0].position = [0.30, 1.94, 0.375]
desk.placements[0].rotation = [0, 0, radians(0)]

# Keep the small cylindrical side table/trash can beside the desk and away
# from the bed's footprint.
side_table.placements[0].position = [0.15, 0.50, 0.25]
side_table.placements[0].rotation = [0, 0, radians(90)]

# Fixed reference points preserve the intended furniture zones while allowing
# the wall and clearance constraints below to make small feasibility adjustments.
bed_anchor = AssetInstance(position=[1.75, 0.80, 0.325])
drawer_anchor = AssetInstance(position=[4.395, 1.75, 0.425])
wardrobe_anchor = AssetInstance(position=[3.55, 3.35, 1.05])
desk_anchor = AssetInstance(position=[0.30, 1.94, 0.375])
side_table_anchor = AssetInstance(position=[0.15, 0.50, 0.25])
room_center = AssetInstance(position=[2.31, 1.825, 0.40])

# High-priority position constraints establish the overall layout and retain
# an unobstructed approach to the door at the southeast corner.
solver.distance_constraint(kids_bed[0], bed_anchor, 0, 0, weight=10)
solver.distance_constraint(drawer_chest[0], drawer_anchor, 0, 0, weight=10)
solver.distance_constraint(wardrobe[0], wardrobe_anchor, 0, 0, weight=10)
solver.distance_constraint(desk[0], desk_anchor, 0, 0, weight=10)
solver.distance_constraint(side_table[0], side_table_anchor, 0, 0, weight=10)

# Associate each item with its intended perimeter wall.
solver.against_wall(kids_bed[0], walls[0])
solver.against_wall(drawer_chest[0], walls[1])
solver.against_wall(wardrobe[0], walls[2])
solver.against_wall(desk[0], walls[3])
solver.against_wall(side_table[0], walls[3])

# The required relationship is specified first among orientation constraints:
# the bed faces the drawer chest. The drawer reciprocally faces the bed.
solver.point_towards(kids_bed[0], drawer_chest[0])
solver.point_towards(drawer_chest[0], kids_bed[0])

# The desk and wardrobe face into the usable center of the room.
# The cylindrical side table is oriented toward its associated desk.
solver.point_towards(desk[0], room_center)
solver.point_towards(wardrobe[0], room_center)
solver.point_towards(side_table[0], desk[0])

# Pairwise clearance constraints discourage overlap if the solver adjusts the
# wall placements. Distances account for the assets' approximate footprints.
solver.distance_constraint(kids_bed[0], desk[0], 1.80, None, weight=10)
solver.distance_constraint(kids_bed[0], side_table[0], 1.40, None, weight=10)
solver.distance_constraint(kids_bed[0], drawer_chest[0], 2.50, None, weight=10)
solver.distance_constraint(kids_bed[0], wardrobe[0], 2.50, None, weight=10)

solver.distance_constraint(desk[0], side_table[0], 1.00, None, weight=10)
solver.distance_constraint(desk[0], drawer_chest[0], 3.50, None, weight=10)
solver.distance_constraint(desk[0], wardrobe[0], 2.50, None, weight=10)

solver.distance_constraint(drawer_chest[0], wardrobe[0], 1.50, None, weight=10)
solver.distance_constraint(side_table[0], wardrobe[0], 3.00, None, weight=10)
solver.distance_constraint(side_table[0], drawer_chest[0], 3.50, None, weight=10)

solver.constraints = []
wardrobe[0].position = [3.549999952316284, 3.3465499877929688, 1.0499999523162842]
wardrobe[0].rotation = [0, 0, -1.5707962978835588]
wardrobe[0].optimize = 2
kids_bed[0].position = [1.9825475215911865, 1.0001542568206787, 0.32499998807907104]
kids_bed[0].rotation = [0, 0, 1.5707963568242065]
kids_bed[0].optimize = 2
desk[0].position = [0.29999998211860657, 1.940000057220459, 0.375]
desk[0].rotation = [0, 0, 3.653080781177921e-08]
desk[0].optimize = 2
side_table[0].position = [0.15000002086162567, 0.5, 0.25]
side_table[0].rotation = [0, 0, 2.784913453086751e-08]
side_table[0].optimize = 2
drawer_chest[0].position = [4.393929958343506, 1.75, 0.42500001192092896]
drawer_chest[0].rotation = [0, 0, -3.1415926099016946]
drawer_chest[0].optimize = 2

