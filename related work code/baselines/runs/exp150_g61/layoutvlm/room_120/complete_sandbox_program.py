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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.00, 0.00, 0.00]),
    Wall(corner1=[4.00, 0.00, 0.00], corner2=[4.00, 4.00, 0.00]),
    Wall(corner1=[4.00, 4.00, 0.00], corner2=[0.00, 4.00, 0.00]),
    Wall(corner1=[0.00, 4.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
executive_desk = Assets(description="A double wooden desk with three drawers on one side and three open shelves on the other side.", size=[0.80, 1.80, 0.75], placements=[AssetInstance() for _ in range(1)])
wall_art_A = Assets(description="A white rectangular poster with black blue and orange marks and irregular writing.", size=[0.03, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
sideboard_console = Assets(description="A desk made out of three different materials.", size=[0.45, 1.20, 0.85], placements=[AssetInstance() for _ in range(1)])
storage_credenza = Assets(description="A light brown wooden console table with 4 cabinets, on 4 cylindrical wooden legs.", size=[0.45, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
coffee_machine = Assets(description="A black coffee maker for espresso.", size=[0.35, 0.25, 0.35], placements=[AssetInstance() for _ in range(1)])
framed_photo = Assets(description="A blue painting in a black frame.", size=[0.10, 0.25, 0.30], placements=[AssetInstance() for _ in range(1)])
wall_shelf_A = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.25, 0.90, 0.20], placements=[AssetInstance() for _ in range(1)])
wall_art_B = Assets(description="A white rectangular poster with black blue and orange marks and irregular writing.", size=[0.03, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
executive_task_chair = Assets(description="A black office chair with a tall mesh back.", size=[0.68, 0.68, 1.20], placements=[AssetInstance() for _ in range(1)])
wall_whiteboard = Assets(description="A poster of blueprints for a picture frame.", size=[0.04, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
wall_shelf_B = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.25, 0.90, 0.20], placements=[AssetInstance() for _ in range(1)])
stack_of_files = Assets(description="A stack of colorful, pixelated-style books in different colors.", size=[0.25, 0.32, 0.22], placements=[AssetInstance() for _ in range(1)])

executive_desk[0].instance_id = 'executive_desk_0'
wall_art_A[0].instance_id = 'wall_art_A_0'
sideboard_console[0].instance_id = 'sideboard_console_0'
storage_credenza[0].instance_id = 'storage_credenza_0'
coffee_machine[0].instance_id = 'coffee_machine_0'
framed_photo[0].instance_id = 'framed_photo_0'
wall_shelf_A[0].instance_id = 'wall_shelf_A_0'
wall_art_B[0].instance_id = 'wall_art_B_0'
executive_task_chair[0].instance_id = 'executive_task_chair_0'
wall_whiteboard[0].instance_id = 'wall_whiteboard_0'
wall_shelf_B[0].instance_id = 'wall_shelf_B_0'
stack_of_files[0].instance_id = 'stack_of_files_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

executive_desk[0].position = [0.09014945437056543, 2.7464772117358938, 0.375]
executive_desk[0].rotation = [0, 0, 0]
wall_art_A[0].position = [0.8370848507271567, 1.726865634567032, 0.425]
wall_art_A[0].rotation = [0, 0, 0]
sideboard_console[0].position = [1.5704523595202633, 3.9193286668996326, 0.425]
sideboard_console[0].rotation = [0, 0, 0]
storage_credenza[0].position = [2.2202453575639693, 2.913709587141971, 0.375]
storage_credenza[0].rotation = [0, 0, 0]
coffee_machine[0].position = [2.735091562425701, 3.3584279482435053, 0.175]
coffee_machine[0].rotation = [0, 0, 0]
framed_photo[0].position = [0.9399576405667602, 1.411183277007059, 0.15]
framed_photo[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [3.807646711971247, 2.8294419743323003, 0.1]
wall_shelf_A[0].rotation = [0, 0, 0]
wall_art_B[0].position = [1.220650271691933, 3.1829187585700653, 0.425]
wall_art_B[0].rotation = [0, 0, 0]
executive_task_chair[0].position = [1.9963669034474099, 1.6910237058357307, 0.6]
executive_task_chair[0].rotation = [0, 0, 0]
wall_whiteboard[0].position = [1.0066167543508833, 1.0800175519465127, 0.45]
wall_whiteboard[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [1.1274209791787042, 0.07331853781102993, 0.1]
wall_shelf_B[0].rotation = [0, 0, 0]
stack_of_files[0].position = [2.6404361402317353, 3.2593674065522507, 0.11]
stack_of_files[0].rotation = [0, 0, 0]
executive_desk[0].position = [0.09014945437056543, 2.7464772117358938, 0.375]
executive_desk[0].rotation = [0, 0, 0]
wall_art_A[0].position = [0.8370848507271567, 1.726865634567032, 0.425]
wall_art_A[0].rotation = [0, 0, 0]
sideboard_console[0].position = [1.5704523595202633, 3.9193286668996326, 0.425]
sideboard_console[0].rotation = [0, 0, 0]
storage_credenza[0].position = [2.2202453575639693, 2.913709587141971, 0.375]
storage_credenza[0].rotation = [0, 0, 0]
coffee_machine[0].position = [2.735091562425701, 3.3584279482435053, 0.175]
coffee_machine[0].rotation = [0, 0, 0]
framed_photo[0].position = [0.9399576405667602, 1.411183277007059, 0.15]
framed_photo[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [3.807646711971247, 2.8294419743323003, 0.1]
wall_shelf_A[0].rotation = [0, 0, 0]
wall_art_B[0].position = [1.220650271691933, 3.1829187585700653, 0.425]
wall_art_B[0].rotation = [0, 0, 0]
executive_task_chair[0].position = [1.9963669034474099, 1.6910237058357307, 0.6]
executive_task_chair[0].rotation = [0, 0, 0]
wall_whiteboard[0].position = [1.0066167543508833, 1.0800175519465127, 0.45]
wall_whiteboard[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [1.1274209791787042, 0.07331853781102993, 0.1]
wall_shelf_B[0].rotation = [0, 0, 0]
stack_of_files[0].position = [2.6404361402317353, 3.2593674065522507, 0.11]
stack_of_files[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the actual boundary coordinates (0..4 m), rather than a centered origin.
# The northeast entrance and its approach remain clear. The west windows
# remain unobstructed by tall furniture or wall-mounted items.

# Work area: the desk's long axis runs north-south, with the chair on its
# east side. There is a 0.16 m gap between the chair and the desktop footprint.
executive_desk[0].position = [1.10, 1.50, 0.375]
executive_desk[0].rotation = [0, 0, 0]

executive_task_chair[0].position = [2.00, 1.50, 0.60]
executive_task_chair[0].rotation = [0, 0, radians(180)]

# Coffee station on the north wall, well to the west of the doorway.
sideboard_console[0].position = [1.50, 3.775, 0.425]
sideboard_console[0].rotation = [0, 0, radians(270)]

coffee_machine[0].position = [1.50, 3.775, 1.025]
coffee_machine[0].rotation = [0, 0, radians(270)]

# Storage on the south wall; its cabinet fronts face into the room.
storage_credenza[0].position = [2.65, 0.225, 0.375]
storage_credenza[0].rotation = [0, 0, radians(90)]

framed_photo[0].position = [2.25, 0.225, 0.90]
framed_photo[0].rotation = [0, 0, radians(90)]

# Files occupy one end of the desk, leaving the central work surface free.
stack_of_files[0].position = [1.10, 0.85, 0.86]
stack_of_files[0].rotation = [0, 0, 0]

# Wall art uses solid north/south walls, not the windowed west wall.
wall_art_A[0].position = [0.45, 3.985, 1.75]
wall_art_A[0].rotation = [0, 0, radians(270)]

wall_art_B[0].position = [0.65, 0.015, 1.75]
wall_art_B[0].rotation = [0, 0, radians(90)]

# East-wall shelves are away from the entrance. The whiteboard is higher
# than the shelves, so their bounding boxes do not intersect.
wall_shelf_A[0].position = [3.875, 0.90, 1.60]
wall_shelf_A[0].rotation = [0, 0, radians(180)]

wall_shelf_B[0].position = [3.875, 2.05, 1.60]
wall_shelf_B[0].rotation = [0, 0, radians(180)]

wall_whiteboard[0].position = [3.98, 1.95, 2.40]
wall_whiteboard[0].rotation = [0, 0, radians(180)]

# Support constraints take priority for the small tabletop objects.
solver.on_top_of(coffee_machine[0], sideboard_console[0])
solver.on_top_of(framed_photo[0], storage_credenza[0])
solver.on_top_of(stack_of_files[0], executive_desk[0])

# Fixed pose references retain the collision-free arrangement, including
# mounting elevations and the clear entrance approach. Each instance gets
# both a position constraint and an orientation constraint. References are
# constraint targets only, not additional scene assets.
for layout_asset in (
    executive_desk,
    executive_task_chair,
    sideboard_console,
    coffee_machine,
    storage_credenza,
    framed_photo,
    stack_of_files,
    wall_art_A,
    wall_art_B,
    wall_shelf_A,
    wall_shelf_B,
    wall_whiteboard,
):
    layout_instance = layout_asset[0]
    layout_reference = AssetInstance(
        position=list(layout_instance.position),
        rotation=list(layout_instance.rotation),
    )
    solver.distance_constraint(
        layout_instance, layout_reference, 0.0, 0.0, weight=10
    )
    solver.align_with(layout_instance, layout_reference, angle=0)

# Wall contact is consistent with the rotated bounding-box depths.
solver.against_wall(sideboard_console[0], walls[2])
solver.against_wall(storage_credenza[0], walls[0])
solver.against_wall(wall_art_A[0], walls[2])
solver.against_wall(wall_art_B[0], walls[0])
solver.against_wall(wall_shelf_A[0], walls[1])
solver.against_wall(wall_shelf_B[0], walls[1])
solver.against_wall(wall_whiteboard[0], walls[1])

# Functional relationships supplement the absolute layout constraints.
solver.point_towards(executive_task_chair[0], executive_desk[0])
solver.distance_constraint(
    executive_task_chair[0], executive_desk[0], 0.85, 1.10, weight=10
)
solver.align_with(coffee_machine[0], sideboard_console[0])
solver.align_with(framed_photo[0], storage_credenza[0])
solver.align_with(stack_of_files[0], executive_desk[0])
solver.align_with(wall_shelf_B[0], wall_shelf_A[0])
solver.align_with(wall_whiteboard[0], wall_shelf_A[0])

solver.constraints = []
wall_shelf_B[0].position = [3.8736584186553955, 2.049999952316284, 0.10000000149011612]
wall_shelf_B[0].rotation = [0, 0, 3.1388770069449166]
wall_shelf_B[0].optimize = 2
sideboard_console[0].position = [1.5, 3.7721643447875977, 0.42500001192092896]
sideboard_console[0].rotation = [0, 0, -1.5750166852286367]
sideboard_console[0].optimize = 2
wall_art_B[0].position = [0.6499999761581421, 0.01302928663790226, 0.42500001192092896]
wall_art_B[0].rotation = [0, 0, 1.5718335170549635]
wall_art_B[0].optimize = 2
wall_art_A[0].position = [0.44999998807907104, 3.9871487617492676, 0.42500001192092896]
wall_art_A[0].rotation = [0, 0, -1.569759130763117]
wall_art_A[0].optimize = 2
executive_desk[0].position = [1.100000023841858, 1.5, 0.375]
executive_desk[0].rotation = [0, 0, 0.021991148286022624]
executive_desk[0].optimize = 2
stack_of_files[0].position = [1.100000023841858, 0.8500000238418579, 0.8600000143051147]
stack_of_files[0].rotation = [0, 0, 0.02358552885174802]
stack_of_files[0].optimize = 2
framed_photo[0].position = [2.25, 0.22499999403953552, 0.8999999761581421]
framed_photo[0].rotation = [0, 0, 1.586249985799784]
framed_photo[0].optimize = 2
wall_shelf_A[0].position = [3.8738598823547363, 0.8999999761581421, 0.10000000149011612]
wall_shelf_A[0].rotation = [0, 0, 3.137371046612329]
wall_shelf_A[0].optimize = 2
wall_whiteboard[0].position = [3.978734254837036, 1.9500000476837158, 0.44999998807907104]
wall_whiteboard[0].rotation = [0, 0, 3.138877805274096]
wall_whiteboard[0].optimize = 2
coffee_machine[0].position = [1.5, 3.7750000953674316, 1.024999976158142]
coffee_machine[0].rotation = [0, 0, -1.555343398139609]
coffee_machine[0].optimize = 2
storage_credenza[0].position = [2.6500000953674316, 0.22435621917247772, 0.375]
storage_credenza[0].rotation = [0, 0, 1.5665760075907877]
storage_credenza[0].optimize = 2
executive_task_chair[0].position = [2.0, 1.5, 0.6000000238418579]
executive_task_chair[0].rotation = [0, 0, -3.125884689672577]
executive_task_chair[0].optimize = 2

