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
meeting_table_round = Assets(description="A round all brown kitchen table.", size=[1.00, 1.00, 0.75], placements=[AssetInstance() for _ in range(1)])
executive_task_chair = Assets(description="A black office chair from minecraft.", size=[0.70, 0.68, 1.15], placements=[AssetInstance() for _ in range(1)])
notepad = Assets(description="Paper scroll with lines of handwriting.", size=[0.30, 0.21, 0.02], placements=[AssetInstance() for _ in range(1)])
wall_clock = Assets(description="A black wall clock.", size=[0.04, 0.30, 0.30], placements=[AssetInstance() for _ in range(1)])
desk_organizer = Assets(description="A wooden crate with compartments that is used to hold things.", size=[0.22, 0.32, 0.15], placements=[AssetInstance() for _ in range(1)])
executive_desk = Assets(description="A dark colored wooden desk with drawers on both sides.", size=[0.80, 1.80, 0.76], placements=[AssetInstance() for _ in range(1)])
wall_art = Assets(description="A white rectangular poster with black blue and orange marks and irregular writing.", size=[0.02, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
visitor_chair = Assets(description="This is a black folding chair.", size=[0.52, 0.46, 0.82], placements=[AssetInstance() for _ in range(1)])

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

low_credenza[0].position = [2.532150088604367, 2.9732177966697897, 0.375]
low_credenza[0].rotation = [0, 0, 0]
meeting_table_round[0].position = [3.4323089095012893, 0.16845716543309797, 0.375]
meeting_table_round[0].rotation = [0, 0, 0]
executive_task_chair[0].position = [4.108592030971039, 1.189441975377959, 0.575]
executive_task_chair[0].rotation = [0, 0, 0]
notepad[0].position = [2.041182114750355, 2.254866480683395, 0.01]
notepad[0].rotation = [0, 0, 0]
wall_clock[0].position = [3.4703549569091052, 0.6235072940413305, 0.15]
wall_clock[0].rotation = [0, 0, 0]
desk_organizer[0].position = [2.8720911637386193, 0.16092734394331187, 0.075]
desk_organizer[0].rotation = [0, 0, 0]
executive_desk[0].position = [3.2812169547525585, 2.812317057669703, 0.38]
executive_desk[0].rotation = [0, 0, 0]
wall_art[0].position = [4.153927296048137, 1.9770733695879332, 0.425]
wall_art[0].rotation = [0, 0, 0]
visitor_chair[0].position = [3.318618589872609, 2.3735761816151624, 0.41]
visitor_chair[0].rotation = [0, 0, 0]
low_credenza[0].position = [2.532150088604367, 2.9732177966697897, 0.375]
low_credenza[0].rotation = [0, 0, 0]
meeting_table_round[0].position = [3.4323089095012893, 0.16845716543309797, 0.375]
meeting_table_round[0].rotation = [0, 0, 0]
executive_task_chair[0].position = [4.108592030971039, 1.189441975377959, 0.575]
executive_task_chair[0].rotation = [0, 0, 0]
notepad[0].position = [2.041182114750355, 2.254866480683395, 0.01]
notepad[0].rotation = [0, 0, 0]
wall_clock[0].position = [3.4703549569091052, 0.6235072940413305, 0.15]
wall_clock[0].rotation = [0, 0, 0]
desk_organizer[0].position = [2.8720911637386193, 0.16092734394331187, 0.075]
desk_organizer[0].rotation = [0, 0, 0]
executive_desk[0].position = [3.2812169547525585, 2.812317057669703, 0.38]
executive_desk[0].rotation = [0, 0, 0]
wall_art[0].position = [4.153927296048137, 1.9770733695879332, 0.425]
wall_art[0].rotation = [0, 0, 0]
visitor_chair[0].position = [3.318618589872609, 2.3735761816151624, 0.41]
visitor_chair[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the supplied boundary coordinates: x=0..6, y=0..3.
# The workstation occupies the middle-left of the room, leaving the east
# doorway and its approach clear. No furniture is placed against the windows.
#
# Rotating the desk 90 degrees makes its 1.80 m dimension run east-west.
# The task chair sits north of the desk, looking south toward the credenza.
# The small meeting area is separate, beside the west windows.

for asset_ref, xyz, yaw in [
    (low_credenza,         [2.80, 0.225, 0.375],  90),
    (executive_desk,       [2.80, 1.400, 0.380],  90),
    (executive_task_chair, [2.80, 2.350, 0.575], -90),
    (meeting_table_round,  [0.80, 0.850, 0.375],   0),
    (visitor_chair,        [0.80, 1.850, 0.410], -90),
    (desk_organizer,       [3.35, 1.350, 0.835],  90),
    (notepad,              [2.70, 1.550, 0.770], -90),
    (wall_clock,          [3.00, 2.980, 2.150], -90),
    (wall_art,            [4.70, 2.990, 1.650], -90),
]:
    asset_ref[0].position = xyz
    asset_ref[0].rotation = [0, 0, radians(yaw)]

# Essential support constraints come first. The organizer and notepad are
# entirely within the desktop footprint and do not overlap one another.
solver.on_top_of(desk_organizer[0], executive_desk[0])
solver.on_top_of(notepad[0], executive_desk[0])

# Anchor the planned centers to preserve clear circulation and non-overlap.
# Elevated anchors also keep the wall-mounted objects at their intended height.
# These fixed points are constraint references, not additional scene assets.
for asset_ref in (
    low_credenza,
    executive_desk,
    executive_task_chair,
    meeting_table_round,
    visitor_chair,
    desk_organizer,
    notepad,
    wall_clock,
    wall_art,
):
    solver.distance_constraint(
        asset_ref[0],
        AssetInstance(position=list(asset_ref[0].position)),
        0, 0, weight=10,
    )

# Credenza against the south wall, facing into the room.
solver.against_wall(low_credenza[0], walls[0])
solver.align_with(
    low_credenza[0],
    AssetInstance(rotation=[0, 0, radians(90)]),
)

# Keep the workstation's orientations explicit. The chair faces the credenza
# across the desk, rather than facing the rear wall.
solver.align_with(executive_desk[0], low_credenza[0])
solver.point_towards(executive_task_chair[0], low_credenza[0])
solver.distance_constraint(
    executive_task_chair[0], executive_desk[0],
    0.95, 1.05, weight=10,
)
solver.distance_constraint(
    executive_desk[0], low_credenza[0],
    1.15, 1.25,
)

# Meeting chair faces its table; the footprints have about 0.24 m clearance.
solver.point_towards(visitor_chair[0], meeting_table_round[0])
solver.distance_constraint(
    visitor_chair[0], meeting_table_round[0],
    1.00, 1.05, weight=10,
)
solver.align_with(
    meeting_table_round[0],
    AssetInstance(rotation=[0, 0, 0]),
)

# Desktop accessories retain their useful orientations relative to the desk.
solver.align_with(desk_organizer[0], executive_desk[0])
solver.align_with(notepad[0], executive_desk[0], angle=180)

# Mount the clock and artwork flush to the north wall, facing south.
# Their fixed-height anchors prevent them from dropping to floor level.
solver.against_wall(wall_clock[0], walls[2])
solver.align_with(
    wall_clock[0],
    AssetInstance(rotation=[0, 0, radians(-90)]),
)
solver.against_wall(wall_art[0], walls[2])
solver.align_with(wall_art[0], wall_clock[0])

solver.constraints = []
visitor_chair[0].position = [0.800000011920929, 1.850000023841858, 0.4099999964237213]
visitor_chair[0].rotation = [0, 0, -1.5582299555380688]
visitor_chair[0].optimize = 2
executive_desk[0].position = [2.799999952316284, 1.399999976158142, 0.3799999952316284]
executive_desk[0].rotation = [0, 0, 1.570796990509722]
executive_desk[0].optimize = 2
meeting_table_round[0].position = [0.800000011920929, 0.8500000238418579, 0.375]
meeting_table_round[0].rotation = [0, 0, 0.0157079639172164]
meeting_table_round[0].optimize = 2
notepad[0].position = [2.700000047683716, 1.5499999523162842, 0.7699999809265137]
notepad[0].rotation = [0, 0, -1.5707958794849846]
notepad[0].optimize = 2
low_credenza[0].position = [2.799999952316284, 0.22499877214431763, 0.375]
low_credenza[0].rotation = [0, 0, 1.5708002431080557]
low_credenza[0].optimize = 2
wall_clock[0].position = [3.0, 2.9800021648406982, 0.15000000596046448]
wall_clock[0].rotation = [0, 0, -1.5707934735091162]
wall_clock[0].optimize = 2
desk_organizer[0].position = [3.3499999046325684, 1.350000023841858, 0.8349999785423279]
desk_organizer[0].rotation = [0, 0, 1.5707966867005558]
desk_organizer[0].optimize = 2
wall_art[0].position = [4.699999809265137, 2.9899988174438477, 0.42500001192092896]
wall_art[0].rotation = [0, 0, -1.5707982776154703]
wall_art[0].optimize = 2
executive_task_chair[0].position = [2.799999952316284, 2.4080519676208496, 0.574999988079071]
executive_task_chair[0].rotation = [0, 0, -1.5582299555380688]
executive_task_chair[0].optimize = 2

