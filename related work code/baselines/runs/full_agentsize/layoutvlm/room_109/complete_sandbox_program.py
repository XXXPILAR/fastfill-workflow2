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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.00, 0.00, 0.00]),
    Wall(corner1=[6.00, 0.00, 0.00], corner2=[6.00, 3.00, 0.00]),
    Wall(corner1=[6.00, 3.00, 0.00], corner2=[0.00, 3.00, 0.00]),
    Wall(corner1=[0.00, 3.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
low_credenza = Assets(description="The table is wooden with shelves, drawers, and a cabinet.", size=[0.45, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
meeting_table_round = Assets(description="A round all brown kitchen table.", size=[1.20, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
executive_task_chair = Assets(description="A black office chair from minecraft.", size=[0.72, 0.68, 1.15], placements=[AssetInstance() for _ in range(1)])
notepad = Assets(description="Paper scroll with lines of handwriting.", size=[0.15, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
wall_clock = Assets(description="A black wall clock.", size=[0.05, 0.32, 0.32], placements=[AssetInstance() for _ in range(1)])
desk_organizer = Assets(description="A wooden crate with compartments that is used to hold things.", size=[0.22, 0.35, 0.18], placements=[AssetInstance() for _ in range(1)])
executive_desk = Assets(description="A dark colored wooden desk with drawers on both sides.", size=[0.85, 1.80, 0.76], placements=[AssetInstance() for _ in range(1)])
wall_art = Assets(description="A white rectangular poster with black blue and orange marks and irregular writing.", size=[0.03, 0.70, 1.00], placements=[AssetInstance() for _ in range(1)])
visitor_chair = Assets(description="This is a black folding chair.", size=[0.52, 0.48, 0.83], placements=[AssetInstance() for _ in range(1)])

low_credenza[0].instance_id = 'low_credenza_0'
meeting_table_round[0].instance_id = 'meeting_table_round_0'
executive_task_chair[0].instance_id = 'executive_task_chair_0'
notepad[0].instance_id = 'notepad_0'
wall_clock[0].instance_id = 'wall_clock_0'
desk_organizer[0].instance_id = 'desk_organizer_0'
executive_desk[0].instance_id = 'executive_desk_0'
wall_art[0].instance_id = 'wall_art_0'
visitor_chair[0].instance_id = 'visitor_chair_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

low_credenza[0].position = [0.400483365470899, 2.3765392380441304, 0.375]
low_credenza[0].rotation = [0, 0, 0]
meeting_table_round[0].position = [4.433128058213253, 2.3847449628865363, 0.375]
meeting_table_round[0].rotation = [0, 0, 0]
executive_task_chair[0].position = [2.8736108617365628, 0.7294385487717553, 0.575]
executive_task_chair[0].rotation = [0, 0, 0]
notepad[0].position = [1.7388562149828977, 2.199791422130147, 0.005]
notepad[0].rotation = [0, 0, 0]
wall_clock[0].position = [5.6870907331514555, 0.9764520385073456, 0.16]
wall_clock[0].rotation = [0, 0, 0]
desk_organizer[0].position = [3.485637527484154, 0.13908480844117144, 0.09]
desk_organizer[0].rotation = [0, 0, 0]
executive_desk[0].position = [2.071248192652932, 1.5206775100109733, 0.38]
executive_desk[0].rotation = [0, 0, 0]
wall_art[0].position = [4.741523300035702, 2.1694588589024097, 0.5]
wall_art[0].rotation = [0, 0, 0]
visitor_chair[0].position = [1.754367517748943, 2.773370940046509, 0.415]
visitor_chair[0].rotation = [0, 0, 0]
low_credenza[0].position = [0.400483365470899, 2.3765392380441304, 0.375]
low_credenza[0].rotation = [0, 0, 0]
meeting_table_round[0].position = [4.433128058213253, 2.3847449628865363, 0.375]
meeting_table_round[0].rotation = [0, 0, 0]
executive_task_chair[0].position = [2.8736108617365628, 0.7294385487717553, 0.575]
executive_task_chair[0].rotation = [0, 0, 0]
notepad[0].position = [1.7388562149828977, 2.199791422130147, 0.005]
notepad[0].rotation = [0, 0, 0]
wall_clock[0].position = [5.6870907331514555, 0.9764520385073456, 0.16]
wall_clock[0].rotation = [0, 0, 0]
desk_organizer[0].position = [3.485637527484154, 0.13908480844117144, 0.09]
desk_organizer[0].rotation = [0, 0, 0]
executive_desk[0].position = [2.071248192652932, 1.5206775100109733, 0.38]
executive_desk[0].rotation = [0, 0, 0]
wall_art[0].position = [4.741523300035702, 2.1694588589024097, 0.5]
wall_art[0].rotation = [0, 0, 0]
visitor_chair[0].position = [1.754367517748943, 2.773370940046509, 0.415]
visitor_chair[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the office around a central executive desk while preserving a clear
# circulation strip along the right side for the door at (6.00, 1.07).

# The desk is rotated so its long dimension runs along the x-axis.
executive_desk[0].position = [3.70, 1.45, 0.38]
executive_desk[0].rotation = [0, 0, radians(90)]

# The executive chair is behind the desk and faces north toward the credenza.
executive_task_chair[0].position = [3.70, 0.60, 0.575]
executive_task_chair[0].rotation = [0, 0, radians(90)]

# The visitor chair sits across the desk from the executive chair.
visitor_chair[0].position = [3.70, 2.20, 0.415]
visitor_chair[0].rotation = [0, 0, radians(-90)]

# The credenza is against the north wall, opposite the executive chair.
low_credenza[0].position = [3.70, 2.775, 0.375]
low_credenza[0].rotation = [0, 0, radians(-90)]

# The meeting table occupies the open left side of the room without blocking
# either window or the door circulation path.
meeting_table_round[0].position = [1.00, 1.60, 0.375]
meeting_table_round[0].rotation = [0, 0, radians(90)]

# Desktop accessories are separated across the usable desk surface.
desk_organizer[0].position = [3.30, 1.45, 0.85]
desk_organizer[0].rotation = [0, 0, radians(90)]

notepad[0].position = [4.05, 1.45, 0.765]
notepad[0].rotation = [0, 0, radians(90)]

# Wall decorations use the unobstructed north and south walls. The artwork is
# mounted above the low credenza.
wall_art[0].position = [3.70, 2.985, 1.55]
wall_art[0].rotation = [0, 0, radians(-90)]

wall_clock[0].position = [1.60, 0.025, 1.60]
wall_clock[0].rotation = [0, 0, radians(90)]


# Fixed anchors preserve the intended zones and clearances if the solver
# adjusts the scene. Their z-coordinates match the assets' intended centers.
desk_anchor = AssetInstance(position=[3.70, 1.45, 0.38])
executive_chair_anchor = AssetInstance(position=[3.70, 0.60, 0.575])
visitor_chair_anchor = AssetInstance(position=[3.70, 2.20, 0.415])
credenza_anchor = AssetInstance(position=[3.70, 2.775, 0.375])
meeting_table_anchor = AssetInstance(position=[1.00, 1.60, 0.375])
organizer_anchor = AssetInstance(position=[3.30, 1.45, 0.85])
notepad_anchor = AssetInstance(position=[4.05, 1.45, 0.765])
art_anchor = AssetInstance(position=[3.70, 2.985, 1.55])
clock_anchor = AssetInstance(position=[1.60, 0.025, 1.60])

# Executive desk: retain its central location and orientation toward the
# executive chair.
solver.distance_constraint(
    executive_desk[0], desk_anchor, 0, 0, weight=10
)
solver.point_towards(executive_desk[0], executive_task_chair[0])

# Executive chair: the required facing relationship is specified first so it
# remains directed toward the credenza through the desk.
solver.distance_constraint(
    executive_task_chair[0], executive_chair_anchor, 0, 0, weight=10
)
solver.point_towards(executive_task_chair[0], low_credenza[0])

# Visitor chair: remain on the opposite side of the desk and face it.
solver.distance_constraint(
    visitor_chair[0], visitor_chair_anchor, 0, 0, weight=10
)
solver.point_towards(visitor_chair[0], executive_desk[0])

# Credenza: stay against the north wall and face inward, opposite the desk's
# orientation.
solver.against_wall(low_credenza[0], walls[2])
solver.distance_constraint(
    low_credenza[0], credenza_anchor, 0, 0, weight=10
)
solver.align_with(low_credenza[0], executive_desk[0], angle=180)

# Meeting table: anchor it in the open left-side meeting area. Its orientation
# is kept consistent with the room's primary furniture axis.
solver.distance_constraint(
    meeting_table_round[0], meeting_table_anchor, 0, 0, weight=10
)
solver.align_with(meeting_table_round[0], executive_desk[0])

# The organizer and notepad must remain on the desk. Their anchor constraints
# also keep them apart rather than allowing them to stack at the desk center.
solver.on_top_of(desk_organizer[0], executive_desk[0])
solver.distance_constraint(
    desk_organizer[0], organizer_anchor, 0, 0, weight=10
)
solver.align_with(desk_organizer[0], executive_desk[0])

solver.on_top_of(notepad[0], executive_desk[0])
solver.distance_constraint(
    notepad[0], notepad_anchor, 0, 0, weight=10
)
solver.align_with(notepad[0], executive_desk[0])

# Keep the artwork on the north wall above the credenza and facing inward.
solver.against_wall(wall_art[0], walls[2])
solver.distance_constraint(
    wall_art[0], art_anchor, 0, 0, weight=10
)
solver.align_with(wall_art[0], low_credenza[0])

# Keep the clock on the south wall, away from the two west-wall windows.
solver.against_wall(wall_clock[0], walls[0])
solver.distance_constraint(
    wall_clock[0], clock_anchor, 0, 0, weight=10
)
solver.align_with(wall_clock[0], executive_desk[0])

solver.constraints = []
desk_organizer[0].position = [3.299999952316284, 1.4500000476837158, 0.8500000238418579]
desk_organizer[0].rotation = [0, 0, 1.5935868878194113]
desk_organizer[0].optimize = 2
notepad[0].position = [4.050000190734863, 1.4500000476837158, 0.7649999856948853]
notepad[0].rotation = [0, 0, 1.5935868878194113]
notepad[0].optimize = 2
wall_clock[0].position = [1.600000023841858, 0.01612480729818344, 0.1599999964237213]
wall_clock[0].rotation = [0, 0, 1.573337248311928]
wall_clock[0].optimize = 2
wall_art[0].position = [3.700000047683716, 2.9932661056518555, 0.5]
wall_art[0].rotation = [0, 0, -1.5682554086442377]
wall_art[0].optimize = 2
low_credenza[0].position = [3.700000047683716, 2.769960880279541, 0.375]
low_credenza[0].rotation = [0, 0, -1.562034116319531]
low_credenza[0].optimize = 2
executive_desk[0].position = [3.700000047683716, 1.4500000476837158, 0.3799999952316284]
executive_desk[0].rotation = [0, 0, 1.6157930646135008]
executive_desk[0].optimize = 2
visitor_chair[0].position = [3.700000047683716, 2.200000047683716, 0.41499999165534973]
visitor_chair[0].rotation = [0, 0, -1.5613715493341729]
visitor_chair[0].optimize = 2
meeting_table_round[0].position = [1.0, 1.600000023841858, 0.375]
meeting_table_round[0].rotation = [0, 0, 1.5904143003230455]
meeting_table_round[0].optimize = 2
executive_task_chair[0].position = [3.700000047683716, 0.6000000238418579, 0.574999988079071]
executive_task_chair[0].rotation = [0, 0, 1.5833626980517244]
executive_task_chair[0].optimize = 2

