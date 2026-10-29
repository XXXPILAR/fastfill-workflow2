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
    Wall(corner1=[0.00, 2.00, 0.00], corner2=[1.00, 2.00, 0.00]),
    Wall(corner1=[1.00, 2.00, 0.00], corner2=[1.00, 0.00, 0.00]),
    Wall(corner1=[1.00, 0.00, 0.00], corner2=[3.00, 0.00, 0.00]),
    Wall(corner1=[3.00, 0.00, 0.00], corner2=[3.00, 5.00, 0.00]),
    Wall(corner1=[3.00, 5.00, 0.00], corner2=[0.00, 5.00, 0.00]),
    Wall(corner1=[0.00, 5.00, 0.00], corner2=[0.00, 2.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
wall_cabinet_A = Assets(description="I brown cabinet with two doors.", size=[0.35, 0.90, 0.70], placements=[AssetInstance() for _ in range(1)])
tall_storage_cabinet_A = Assets(description="A blue cabinet with two big doors.", size=[0.50, 0.90, 1.90], placements=[AssetInstance() for _ in range(1)])
lab_workbench = Assets(description="a laboratory desk with a microscope and drawers.", size=[0.75, 1.50, 0.90], placements=[AssetInstance() for _ in range(1)])
tall_storage_cabinet_B = Assets(description="A blue cabinet with two big doors.", size=[0.50, 0.90, 1.90], placements=[AssetInstance() for _ in range(1)])
wall_shelf_A = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.25, 0.90, 0.25], placements=[AssetInstance() for _ in range(1)])
wall_cabinet_B = Assets(description="I brown cabinet with two doors.", size=[0.35, 0.90, 0.70], placements=[AssetInstance() for _ in range(1)])
support_desk = Assets(description="A little desk with a black computer monitor on top.", size=[0.60, 1.00, 0.75], placements=[AssetInstance() for _ in range(1)])
archive_box_A = Assets(description="A dark brown loaf of bread with each side neatly sliced.", size=[0.40, 0.35, 0.25], placements=[AssetInstance() for _ in range(1)])
desk_lamp = Assets(description="A desk lamp with a purple base and coral arm and head.", size=[0.35, 0.18, 0.45], placements=[AssetInstance() for _ in range(1)])
wall_shelf_B = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.25, 0.90, 0.25], placements=[AssetInstance() for _ in range(1)])
wall_whiteboard = Assets(description="A white rectangular poster with black blue and orange marks and irregular writing.", size=[0.03, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
support_chair = Assets(description="support chair", size=[0.55, 0.50, 0.85], placements=[AssetInstance() for _ in range(1)])
mobile_lab_cart = Assets(description="Gray cart with wheels and three shelves.", size=[0.45, 0.65, 0.85], placements=[AssetInstance() for _ in range(1)])
archive_box_B = Assets(description="A dark brown loaf of bread with each side neatly sliced.", size=[0.40, 0.35, 0.25], placements=[AssetInstance() for _ in range(1)])

wall_cabinet_A[0].instance_id = 'wall_cabinet_A_0'
tall_storage_cabinet_A[0].instance_id = 'tall_storage_cabinet_A_0'
lab_workbench[0].instance_id = 'lab_workbench_0'
tall_storage_cabinet_B[0].instance_id = 'tall_storage_cabinet_B_0'
wall_shelf_A[0].instance_id = 'wall_shelf_A_0'
wall_cabinet_B[0].instance_id = 'wall_cabinet_B_0'
support_desk[0].instance_id = 'support_desk_0'
archive_box_A[0].instance_id = 'archive_box_A_0'
desk_lamp[0].instance_id = 'desk_lamp_0'
wall_shelf_B[0].instance_id = 'wall_shelf_B_0'
wall_whiteboard[0].instance_id = 'wall_whiteboard_0'
support_chair[0].instance_id = 'support_chair_0'
mobile_lab_cart[0].instance_id = 'mobile_lab_cart_0'
archive_box_B[0].instance_id = 'archive_box_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

wall_cabinet_A[0].position = [0.2622435957657818, 4.646141404894774, 0.35]
wall_cabinet_A[0].rotation = [0, 0, 0]
tall_storage_cabinet_A[0].position = [1.8723543361150903, 0.25979097505055115, 0.95]
tall_storage_cabinet_A[0].rotation = [0, 0, 0]
lab_workbench[0].position = [1.265240699076303, 0.4714810863377239, 0.45]
lab_workbench[0].rotation = [0, 0, 0]
tall_storage_cabinet_B[0].position = [0.14932884741721586, 3.637702269657236, 0.95]
tall_storage_cabinet_B[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [2.086752584403173, 2.208496345275199, 0.125]
wall_shelf_A[0].rotation = [0, 0, 0]
wall_cabinet_B[0].position = [2.748391480582058, 2.8937316502383235, 0.35]
wall_cabinet_B[0].rotation = [0, 0, 0]
support_desk[0].position = [0.3538276040538111, 3.8400493368366457, 0.375]
support_desk[0].rotation = [0, 0, 0]
archive_box_A[0].position = [0.9063517441987519, 4.155213761069407, 0.125]
archive_box_A[0].rotation = [0, 0, 0]
desk_lamp[0].position = [2.138554783056601, 2.5712700328382514, 0.225]
desk_lamp[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [2.888897250888988, 2.529100985147691, 0.125]
wall_shelf_B[0].rotation = [0, 0, 0]
wall_whiteboard[0].position = [0.4928361240761564, 3.4838758014187117, 0.45]
wall_whiteboard[0].rotation = [0, 0, 0]
support_chair[0].position = [0.0013315347157901725, 4.551746212305789, 0.425]
support_chair[0].rotation = [0, 0, 0]
mobile_lab_cart[0].position = [1.0857154316553206, 2.5772167322061175, 0.425]
mobile_lab_cart[0].rotation = [0, 0, 0]
archive_box_B[0].position = [1.5142140258521044, 0.9623680360457243, 0.125]
archive_box_B[0].rotation = [0, 0, 0]
wall_cabinet_A[0].position = [0.2622435957657818, 4.646141404894774, 0.35]
wall_cabinet_A[0].rotation = [0, 0, 0]
tall_storage_cabinet_A[0].position = [1.8723543361150903, 0.25979097505055115, 0.95]
tall_storage_cabinet_A[0].rotation = [0, 0, 0]
lab_workbench[0].position = [1.265240699076303, 0.4714810863377239, 0.45]
lab_workbench[0].rotation = [0, 0, 0]
tall_storage_cabinet_B[0].position = [0.14932884741721586, 3.637702269657236, 0.95]
tall_storage_cabinet_B[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [2.086752584403173, 2.208496345275199, 0.125]
wall_shelf_A[0].rotation = [0, 0, 0]
wall_cabinet_B[0].position = [2.748391480582058, 2.8937316502383235, 0.35]
wall_cabinet_B[0].rotation = [0, 0, 0]
support_desk[0].position = [0.3538276040538111, 3.8400493368366457, 0.375]
support_desk[0].rotation = [0, 0, 0]
archive_box_A[0].position = [0.9063517441987519, 4.155213761069407, 0.125]
archive_box_A[0].rotation = [0, 0, 0]
desk_lamp[0].position = [2.138554783056601, 2.5712700328382514, 0.225]
desk_lamp[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [2.888897250888988, 2.529100985147691, 0.125]
wall_shelf_B[0].rotation = [0, 0, 0]
wall_whiteboard[0].position = [0.4928361240761564, 3.4838758014187117, 0.45]
wall_whiteboard[0].rotation = [0, 0, 0]
support_chair[0].position = [0.0013315347157901725, 4.551746212305789, 0.425]
support_chair[0].rotation = [0, 0, 0]
mobile_lab_cart[0].position = [1.0857154316553206, 2.5772167322061175, 0.425]
mobile_lab_cart[0].rotation = [0, 0, 0]
archive_box_B[0].position = [1.5142140258521044, 0.9623680360457243, 0.125]
archive_box_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Storage occupies the north wall, away from both east-wall windows.
# The west-wall doorway and its approach (y=3.54 to 4.56) remain clear.
tall_storage_cabinet_A[0].position = [0.50, 4.75, 0.95]
tall_storage_cabinet_A[0].rotation = [0, 0, radians(-90)]
tall_storage_cabinet_B[0].position = [1.50, 4.75, 0.95]
tall_storage_cabinet_B[0].rotation = [0, 0, radians(-90)]

# The laboratory bench fits inside the narrow southern portion of the room.
lab_workbench[0].position = [1.375, 0.85, 0.45]
lab_workbench[0].rotation = [0, 0, 0]

# The support station sits between the two east-wall windows.
# Its front faces west toward the cart; the chair faces east toward the desk.
support_desk[0].position = [2.70, 2.25, 0.375]
support_desk[0].rotation = [0, 0, radians(180)]
mobile_lab_cart[0].position = [1.43, 2.25, 0.425]
mobile_lab_cart[0].rotation = [0, 0, 0]
support_chair[0].position = [2.05, 2.25, 0.425]
support_chair[0].rotation = [0, 0, 0]

# Wall-mounted storage is elevated, rather than placed on the floor.
# Cabinet A is above the laboratory bench; cabinet B uses the west wall
# south of the door. Shelves are mounted separately above the cabinets.
wall_cabinet_A[0].position = [1.175, 0.85, 1.75]
wall_cabinet_A[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [1.125, 0.85, 2.35]
wall_shelf_A[0].rotation = [0, 0, 0]

wall_cabinet_B[0].position = [0.175, 2.65, 1.75]
wall_cabinet_B[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [0.125, 2.65, 2.35]
wall_shelf_B[0].rotation = [0, 0, 0]

# The whiteboard is mounted on the south wall above working height.
wall_whiteboard[0].position = [2.10, 0.015, 1.75]
wall_whiteboard[0].rotation = [0, 0, radians(90)]

# Both boxes rest fully within the cabinet tops.
# In the supplied zero-based asset ordering, o0013 is archive_box_B
# and o0003 is tall_storage_cabinet_B.
archive_box_A[0].position = [0.50, 4.75, 2.025]
archive_box_A[0].rotation = [0, 0, radians(-90)]
archive_box_B[0].position = [1.50, 4.75, 2.025]
archive_box_B[0].rotation = [0, 0, radians(-90)]

# Keep the lamp near one end of the desk, leaving its middle for the monitor.
desk_lamp[0].position = [2.70, 1.92, 0.975]
desk_lamp[0].rotation = [0, 0, radians(180)]

# Preserve the requested functional relationships first.
solver.on_top_of(archive_box_B[0], tall_storage_cabinet_B[0])
solver.on_top_of(archive_box_A[0], tall_storage_cabinet_A[0])
solver.on_top_of(desk_lamp[0], support_desk[0])
solver.point_towards(support_desk[0], mobile_lab_cart[0])
solver.point_towards(support_chair[0], support_desk[0])
solver.point_towards(mobile_lab_cart[0], support_desk[0])

# Fixed center anchors preserve boundary clearance, mounting heights,
# doorway access, and the deliberately separated furniture footprints.
# These are reference points, not additional scene assets.
for layout_asset in (
    tall_storage_cabinet_A,
    tall_storage_cabinet_B,
    lab_workbench,
    support_desk,
    mobile_lab_cart,
    support_chair,
    wall_cabinet_A,
    wall_cabinet_B,
    wall_shelf_A,
    wall_shelf_B,
    wall_whiteboard,
    archive_box_A,
    archive_box_B,
    desk_lamp,
):
    solver.distance_constraint(
        layout_asset[0],
        AssetInstance(position=list(layout_asset[0].position)),
        0,
        0,
        weight=10,
    )

# Wall contact supplements the absolute mounting positions.
solver.against_wall(tall_storage_cabinet_A[0], walls[4])
solver.against_wall(tall_storage_cabinet_B[0], walls[4])
solver.against_wall(lab_workbench[0], walls[1])
solver.against_wall(support_desk[0], walls[3])
solver.against_wall(wall_cabinet_A[0], walls[1])
solver.against_wall(wall_shelf_A[0], walls[1])
solver.against_wall(wall_cabinet_B[0], walls[5])
solver.against_wall(wall_shelf_B[0], walls[5])
solver.against_wall(wall_whiteboard[0], walls[2])

# Stable inward-facing orientations for the wall-mounted furniture.
for layout_asset, layout_yaw in (
    (tall_storage_cabinet_A, -90),
    (tall_storage_cabinet_B, -90),
    (lab_workbench, 0),
    (wall_cabinet_A, 0),
    (wall_cabinet_B, 0),
    (wall_shelf_A, 0),
    (wall_shelf_B, 0),
    (wall_whiteboard, 90),
):
    solver.align_with(
        layout_asset[0],
        AssetInstance(rotation=[0, 0, radians(layout_yaw)]),
    )

solver.align_with(archive_box_A[0], tall_storage_cabinet_A[0])
solver.align_with(archive_box_B[0], tall_storage_cabinet_B[0])
solver.align_with(desk_lamp[0], support_desk[0])

# Minimum center separations reinforce the workstation's non-overlapping
# arrangement; the anchors above additionally preserve the lateral offsets.
solver.distance_constraint(
    support_chair[0], support_desk[0], 0.62, 0.72, weight=10
)
solver.distance_constraint(
    mobile_lab_cart[0], support_chair[0], 0.60, 0.75, weight=10
)
solver.distance_constraint(
    mobile_lab_cart[0], support_desk[0], 1.20, 1.35, weight=10
)
solver.distance_constraint(
    tall_storage_cabinet_B[0], tall_storage_cabinet_A[0],
    0.95, 1.05, weight=10
)

solver.constraints = []
support_chair[0].position = [1.5636024475097656, 2.9078478813171387, 0.42500001192092896]
support_chair[0].rotation = [0, 0, -1.6201858539894773]
support_chair[0].optimize = 2
tall_storage_cabinet_B[0].position = [1.5, 4.75, 0.949999988079071]
tall_storage_cabinet_B[0].rotation = [0, 0, -1.57079628187935]
tall_storage_cabinet_B[0].optimize = 2
wall_cabinet_B[0].position = [0.17499999701976776, 2.6500000953674316, 0.3499999940395355]
wall_cabinet_B[0].rotation = [0, 0, 4.0060986916746994e-08]
wall_cabinet_B[0].optimize = 2
tall_storage_cabinet_A[0].position = [0.5, 4.75, 0.949999988079071]
tall_storage_cabinet_A[0].rotation = [0, 0, -1.57079628187935]
tall_storage_cabinet_A[0].optimize = 2
desk_lamp[0].position = [1.5196082592010498, 2.034212350845337, 0.9750000238418579]
desk_lamp[0].rotation = [0, 0, 1.5389389881420301]
desk_lamp[0].optimize = 2
wall_cabinet_A[0].position = [1.1749999523162842, 0.8500000238418579, 0.3499999940395355]
wall_cabinet_A[0].rotation = [0, 0, 3.45131802592751e-08]
wall_cabinet_A[0].optimize = 2
archive_box_A[0].position = [0.5, 4.75, 2.0250000953674316]
archive_box_A[0].rotation = [0, 0, -1.5707962839646648]
archive_box_A[0].optimize = 2
wall_shelf_A[0].position = [1.1250001192092896, 0.8500000238418579, 0.125]
wall_shelf_A[0].rotation = [0, 0, 4.3234339825779045e-08]
wall_shelf_A[0].optimize = 2
support_desk[0].position = [1.0277924537658691, 2.2998406887054443, 0.375]
support_desk[0].rotation = [0, 0, 1.5390468422157717]
support_desk[0].optimize = 2
wall_whiteboard[0].position = [2.0999999046325684, 0.014999999664723873, 0.44999998807907104]
wall_whiteboard[0].rotation = [0, 0, 1.5707963649286194]
wall_whiteboard[0].optimize = 2
mobile_lab_cart[0].position = [1.1129988431930542, 3.504162549972534, 0.42500001192092896]
mobile_lab_cart[0].rotation = [0, 0, -1.1387774400161743]
mobile_lab_cart[0].optimize = 2
lab_workbench[0].position = [1.3749998807907104, 0.8500000238418579, 0.44999998807907104]
lab_workbench[0].rotation = [0, 0, 4.449767113984608e-08]
lab_workbench[0].optimize = 2
wall_shelf_B[0].position = [0.125, 2.6500000953674316, 0.125]
wall_shelf_B[0].rotation = [0, 0, 4.1582694945661964e-08]
wall_shelf_B[0].optimize = 2
archive_box_B[0].position = [1.5, 4.75, 2.0250000953674316]
archive_box_B[0].rotation = [0, 0, -1.5707962839646648]
archive_box_B[0].optimize = 2

