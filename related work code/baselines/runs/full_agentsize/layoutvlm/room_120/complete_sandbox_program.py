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
executive_desk = Assets(description="A double wooden desk with three drawers on one side and three open shelves on the other side.", size=[0.80, 1.80, 0.76], placements=[AssetInstance() for _ in range(1)])
wall_art_A = Assets(description="A white rectangular poster with black blue and orange marks and irregular writing.", size=[0.03, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
sideboard_console = Assets(description="A desk made out of three different materials.", size=[0.45, 1.40, 0.80], placements=[AssetInstance() for _ in range(1)])
storage_credenza = Assets(description="A light brown wooden console table with 4 cabinets, on 4 cylindrical wooden legs.", size=[0.45, 1.80, 0.80], placements=[AssetInstance() for _ in range(1)])
coffee_machine = Assets(description="A black coffee maker for espresso.", size=[0.35, 0.25, 0.32], placements=[AssetInstance() for _ in range(1)])
framed_photo = Assets(description="A blue painting in a black frame.", size=[0.08, 0.25, 0.30], placements=[AssetInstance() for _ in range(1)])
wall_shelf_A = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.22, 0.80, 0.25], placements=[AssetInstance() for _ in range(1)])
wall_art_B = Assets(description="A white rectangular poster with black blue and orange marks and irregular writing.", size=[0.03, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
executive_task_chair = Assets(description="A black office chair with a tall mesh back.", size=[0.68, 0.68, 1.20], placements=[AssetInstance() for _ in range(1)])
wall_whiteboard = Assets(description="A poster of blueprints for a picture frame.", size=[0.03, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
wall_shelf_B = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.22, 0.80, 0.25], placements=[AssetInstance() for _ in range(1)])
stack_of_files = Assets(description="A stack of colorful, pixelated-style books in different colors.", size=[0.25, 0.35, 0.22], placements=[AssetInstance() for _ in range(1)])

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

executive_desk[0].position = [1.7426223473734486, 0.5508304824288421, 0.38]
executive_desk[0].rotation = [0, 0, 0]
wall_art_A[0].position = [0.9239309777704308, 3.676807328081727, 0.4]
wall_art_A[0].rotation = [0, 0, 0]
sideboard_console[0].position = [3.999195731036564, 2.8676851371770264, 0.4]
sideboard_console[0].rotation = [0, 0, 0]
storage_credenza[0].position = [0.6357925343367956, 1.5620235656289863, 0.4]
storage_credenza[0].rotation = [0, 0, 0]
coffee_machine[0].position = [0.16309496893849174, 0.09070806921359509, 0.16]
coffee_machine[0].rotation = [0, 0, 0]
framed_photo[0].position = [0.3985195154111274, 1.2340303024803414, 0.15]
framed_photo[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [1.9398821338425285, 2.1672814638261126, 0.125]
wall_shelf_A[0].rotation = [0, 0, 0]
wall_art_B[0].position = [2.507493576496425, 0.5915957323683956, 0.4]
wall_art_B[0].rotation = [0, 0, 0]
executive_task_chair[0].position = [1.2063999652787594, 3.9574864302923842, 0.6]
executive_task_chair[0].rotation = [0, 0, 0]
wall_whiteboard[0].position = [0.5145367470037949, 0.3400828858195917, 0.45]
wall_whiteboard[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [2.189775180839863, 2.310429213342893, 0.125]
wall_shelf_B[0].rotation = [0, 0, 0]
stack_of_files[0].position = [3.026571400728868, 0.1684589017189726, 0.11]
stack_of_files[0].rotation = [0, 0, 0]
executive_desk[0].position = [1.7426223473734486, 0.5508304824288421, 0.38]
executive_desk[0].rotation = [0, 0, 0]
wall_art_A[0].position = [0.9239309777704308, 3.676807328081727, 0.4]
wall_art_A[0].rotation = [0, 0, 0]
sideboard_console[0].position = [3.999195731036564, 2.8676851371770264, 0.4]
sideboard_console[0].rotation = [0, 0, 0]
storage_credenza[0].position = [0.6357925343367956, 1.5620235656289863, 0.4]
storage_credenza[0].rotation = [0, 0, 0]
coffee_machine[0].position = [0.16309496893849174, 0.09070806921359509, 0.16]
coffee_machine[0].rotation = [0, 0, 0]
framed_photo[0].position = [0.3985195154111274, 1.2340303024803414, 0.15]
framed_photo[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [1.9398821338425285, 2.1672814638261126, 0.125]
wall_shelf_A[0].rotation = [0, 0, 0]
wall_art_B[0].position = [2.507493576496425, 0.5915957323683956, 0.4]
wall_art_B[0].rotation = [0, 0, 0]
executive_task_chair[0].position = [1.2063999652787594, 3.9574864302923842, 0.6]
executive_task_chair[0].rotation = [0, 0, 0]
wall_whiteboard[0].position = [0.5145367470037949, 0.3400828858195917, 0.45]
wall_whiteboard[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [2.189775180839863, 2.310429213342893, 0.125]
wall_shelf_B[0].rotation = [0, 0, 0]
stack_of_files[0].position = [3.026571400728868, 0.1684589017189726, 0.11]
stack_of_files[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the main work area along the bottom wall, leaving a generous central
# aisle and keeping the door approach at the upper-right clear.
executive_desk[0].position = [1.25, 0.40, 0.38]
executive_desk[0].rotation = [0, 0, radians(90)]

executive_task_chair[0].position = [1.25, 1.35, 0.60]
executive_task_chair[0].rotation = [0, 0, radians(-90)]

# Place the sideboard on the unobstructed left portion of the top wall. Its
# right edge ends well before the door, whose opening begins near x=2.89.
sideboard_console[0].position = [0.85, 3.775, 0.40]
sideboard_console[0].rotation = [0, 0, radians(-90)]

# Place the larger credenza against the right wall, away from the door.
storage_credenza[0].position = [3.775, 1.25, 0.40]
storage_credenza[0].rotation = [0, 0, radians(180)]

# Small accessories are positioned over their supporting furniture. Their
# final vertical positions are enforced by on_top_of constraints below.
coffee_machine[0].position = [0.55, 3.70, 0.96]
coffee_machine[0].rotation = [0, 0, radians(-90)]

framed_photo[0].position = [3.70, 1.65, 0.95]
framed_photo[0].rotation = [0, 0, radians(180)]

stack_of_files[0].position = [0.75, 0.38, 0.87]
stack_of_files[0].rotation = [0, 0, radians(90)]

# Keep wall-mounted objects off the windowed left wall. The first artwork is
# mounted above the desk on the bottom wall.
wall_art_A[0].position = [1.25, 0.015, 1.55]
wall_art_A[0].rotation = [0, 0, radians(90)]

# The second artwork fits on the top wall between the sideboard and the door.
wall_art_B[0].position = [2.20, 3.985, 1.55]
wall_art_B[0].rotation = [0, 0, radians(-90)]

# Mount two shelves above the credenza, with enough horizontal separation to
# avoid overlap while remaining convenient for storage.
wall_shelf_A[0].position = [3.89, 0.75, 1.30]
wall_shelf_A[0].rotation = [0, 0, radians(180)]

wall_shelf_B[0].position = [3.89, 1.75, 1.30]
wall_shelf_B[0].rotation = [0, 0, radians(180)]

# Mount the whiteboard farther up the right wall. It has no floor footprint and
# does not obstruct the approach to the door.
wall_whiteboard[0].position = [3.985, 2.90, 1.65]
wall_whiteboard[0].rotation = [0, 0, radians(180)]


# Fixed references preserve the intended zones if the solver adjusts the
# arrangement for physical feasibility.
desk_anchor = AssetInstance(
    position=[1.25, 0.40, 0.38],
    rotation=[0, 0, radians(90)]
)
chair_anchor = AssetInstance(position=[1.25, 1.35, 0.60])
sideboard_anchor = AssetInstance(
    position=[0.85, 3.775, 0.40],
    rotation=[0, 0, radians(-90)]
)
credenza_anchor = AssetInstance(
    position=[3.775, 1.25, 0.40],
    rotation=[0, 0, radians(180)]
)

art_A_anchor = AssetInstance(
    position=[1.25, 0.015, 1.55],
    rotation=[0, 0, radians(90)]
)
art_B_anchor = AssetInstance(
    position=[2.20, 3.985, 1.55],
    rotation=[0, 0, radians(-90)]
)
shelf_A_anchor = AssetInstance(
    position=[3.89, 0.75, 1.30],
    rotation=[0, 0, radians(180)]
)
shelf_B_anchor = AssetInstance(
    position=[3.89, 1.75, 1.30],
    rotation=[0, 0, radians(180)]
)
whiteboard_anchor = AssetInstance(
    position=[3.985, 2.90, 1.65],
    rotation=[0, 0, radians(180)]
)


# Main floor furniture: wall contact is the primary positional relationship;
# weighted anchors prevent unwanted sliding along those walls.
solver.against_wall(executive_desk[0], walls[0])
solver.distance_constraint(
    executive_desk[0], desk_anchor, 0, 0, weight=10
)
solver.align_with(executive_desk[0], desk_anchor)

solver.distance_constraint(
    executive_task_chair[0], chair_anchor, 0, 0, weight=10
)
solver.point_towards(executive_task_chair[0], executive_desk[0])
# Preserve practical clearance between the chair and the desk while keeping
# the chair within working distance.
solver.distance_constraint(
    executive_task_chair[0], executive_desk[0], 0.85, 1.15, weight=10
)

solver.against_wall(sideboard_console[0], walls[2])
solver.distance_constraint(
    sideboard_console[0], sideboard_anchor, 0, 0, weight=10
)
solver.align_with(sideboard_console[0], sideboard_anchor)

solver.against_wall(storage_credenza[0], walls[1])
solver.distance_constraint(
    storage_credenza[0], credenza_anchor, 0, 0, weight=10
)
solver.align_with(storage_credenza[0], credenza_anchor)


# Countertop and desktop objects require both support and horizontal placement
# semantics. Their orientations follow the furniture supporting them.
solver.on_top_of(coffee_machine[0], sideboard_console[0])
solver.distance_constraint(
    coffee_machine[0], sideboard_console[0], 0.45, 0.75, weight=10
)
solver.align_with(coffee_machine[0], sideboard_console[0])

solver.on_top_of(framed_photo[0], storage_credenza[0])
solver.distance_constraint(
    framed_photo[0], storage_credenza[0], 0.45, 0.75, weight=10
)
solver.align_with(framed_photo[0], storage_credenza[0])

solver.on_top_of(stack_of_files[0], executive_desk[0])
solver.distance_constraint(
    stack_of_files[0], executive_desk[0], 0.35, 0.75, weight=10
)
solver.align_with(stack_of_files[0], executive_desk[0])


# Wall-mounted assets use wall contact for position and fixed orientation
# references so their visible fronts face into the room.
solver.against_wall(wall_art_A[0], walls[0])
solver.distance_constraint(
    wall_art_A[0], art_A_anchor, 0, 0, weight=10
)
solver.align_with(wall_art_A[0], art_A_anchor)

solver.against_wall(wall_art_B[0], walls[2])
solver.distance_constraint(
    wall_art_B[0], art_B_anchor, 0, 0, weight=10
)
solver.align_with(wall_art_B[0], art_B_anchor)

solver.against_wall(wall_shelf_A[0], walls[1])
solver.distance_constraint(
    wall_shelf_A[0], shelf_A_anchor, 0, 0, weight=10
)
solver.align_with(wall_shelf_A[0], shelf_A_anchor)

solver.against_wall(wall_shelf_B[0], walls[1])
solver.distance_constraint(
    wall_shelf_B[0], shelf_B_anchor, 0, 0, weight=10
)
solver.align_with(wall_shelf_B[0], shelf_B_anchor)

solver.against_wall(wall_whiteboard[0], walls[1])
solver.distance_constraint(
    wall_whiteboard[0], whiteboard_anchor, 0, 0, weight=10
)
solver.align_with(wall_whiteboard[0], whiteboard_anchor)

solver.constraints = []
sideboard_console[0].position = [0.8500000238418579, 3.7696614265441895, 0.4000000059604645]
sideboard_console[0].rotation = [0, 0, -1.5589233148146744]
sideboard_console[0].optimize = 2
storage_credenza[0].position = [3.765263795852661, 1.25, 0.4000000059604645]
storage_credenza[0].rotation = [0, 0, -3.1297196466999124]
storage_credenza[0].optimize = 2
wall_art_A[0].position = [1.25, 0.0067442841827869415, 0.4000000059604645]
wall_art_A[0].rotation = [0, 0, 1.573337246167655]
wall_art_A[0].optimize = 2
wall_art_B[0].position = [2.200000047683716, 3.993398666381836, 0.4000000059604645]
wall_art_B[0].rotation = [0, 0, -1.5682554074221384]
wall_art_B[0].optimize = 2
wall_whiteboard[0].position = [3.993398427963257, 2.9000000953674316, 0.44999998807907104]
wall_whiteboard[0].rotation = [0, 0, -3.1390517430940474]
wall_whiteboard[0].optimize = 2
wall_shelf_B[0].position = [3.888983964920044, 1.75, 0.125]
wall_shelf_B[0].rotation = [0, 0, -3.1390517375834066]
wall_shelf_B[0].optimize = 2
stack_of_files[0].position = [0.7400000095367432, 0.3700000047683716, 0.8700000047683716]
stack_of_files[0].rotation = [0, 0, 1.5935863729448736]
stack_of_files[0].optimize = 2
framed_photo[0].position = [3.690000057220459, 1.659999966621399, 0.9500000476837158]
framed_photo[0].rotation = [0, 0, -3.11880380104969]
framed_photo[0].optimize = 2
executive_desk[0].position = [1.25, 0.41528376936912537, 0.3799999952316284]
executive_desk[0].rotation = [0, 0, 1.5888912269202566]
executive_desk[0].optimize = 2
coffee_machine[0].position = [0.5400000214576721, 3.690000057220459, 0.9600000381469727]
coffee_machine[0].rotation = [0, 0, -1.5480074742547933]
coffee_machine[0].optimize = 2
executive_task_chair[0].position = [1.25, 1.350000023841858, 0.6000000238418579]
executive_task_chair[0].rotation = [0, 0, -1.5582299555380688]
executive_task_chair[0].optimize = 2
wall_shelf_A[0].position = [3.888983964920044, 0.75, 0.125]
wall_shelf_A[0].rotation = [0, 0, -3.1390517375834066]
wall_shelf_A[0].optimize = 2

