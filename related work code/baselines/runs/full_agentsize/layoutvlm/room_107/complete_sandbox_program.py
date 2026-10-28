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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.00, 0.00, 0.00]),
    Wall(corner1=[2.00, 0.00, 0.00], corner2=[2.00, 3.00, 0.00]),
    Wall(corner1=[2.00, 3.00, 0.00], corner2=[3.00, 3.00, 0.00]),
    Wall(corner1=[3.00, 3.00, 0.00], corner2=[3.00, 4.00, 0.00]),
    Wall(corner1=[3.00, 4.00, 0.00], corner2=[0.00, 4.00, 0.00]),
    Wall(corner1=[0.00, 4.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
desk_return_credenza = Assets(description="A set of pinewood drawers.", size=[0.45, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
storage_box = Assets(description="A red microwave oven.", size=[0.40, 0.50, 0.30], placements=[AssetInstance() for _ in range(1)])
floor_storage_cabinet = Assets(description="A rectangular set of five dark gray shelves with two drawers beneath them.", size=[0.40, 0.80, 1.80], placements=[AssetInstance() for _ in range(1)])
executive_desk = Assets(description="A light wooden table with rounded corners and four skinny legs with white accents at the top.", size=[0.75, 1.50, 0.75], placements=[AssetInstance() for _ in range(1)])
framed_photo = Assets(description="A blue painting in a black frame.", size=[0.08, 0.60, 0.45], placements=[AssetInstance() for _ in range(1)])

desk_return_credenza[0].instance_id = 'desk_return_credenza_0'
storage_box[0].instance_id = 'storage_box_0'
floor_storage_cabinet[0].instance_id = 'floor_storage_cabinet_0'
executive_desk[0].instance_id = 'executive_desk_0'
framed_photo[0].instance_id = 'framed_photo_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

desk_return_credenza[0].position = [1.8521068839881356, 3.4982101677932236, 0.375]
desk_return_credenza[0].rotation = [0, 0, 0]
storage_box[0].position = [1.5966075936662205, 2.4112705769190943, 0.15]
storage_box[0].rotation = [0, 0, 0]
floor_storage_cabinet[0].position = [1.7426651053543925, 0.6069981626197007, 0.9]
floor_storage_cabinet[0].rotation = [0, 0, 0]
executive_desk[0].position = [0.6398493020572312, 1.7375920894711343, 0.375]
executive_desk[0].rotation = [0, 0, 0]
framed_photo[0].position = [0.3143918528955276, 3.7134032359292815, 0.225]
framed_photo[0].rotation = [0, 0, 0]
desk_return_credenza[0].position = [1.8521068839881356, 3.4982101677932236, 0.375]
desk_return_credenza[0].rotation = [0, 0, 0]
storage_box[0].position = [1.5966075936662205, 2.4112705769190943, 0.15]
storage_box[0].rotation = [0, 0, 0]
floor_storage_cabinet[0].position = [1.7426651053543925, 0.6069981626197007, 0.9]
floor_storage_cabinet[0].rotation = [0, 0, 0]
executive_desk[0].position = [0.6398493020572312, 1.7375920894711343, 0.375]
executive_desk[0].rotation = [0, 0, 0]
framed_photo[0].position = [0.3143918528955276, 3.7134032359292815, 0.225]
framed_photo[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the credenza along the upper section of the left wall. Its shallow
# dimension runs perpendicular to the wall, leaving the doorway area clear.
desk_return_credenza[0].position = [0.225, 3.30, 0.375]
desk_return_credenza[0].rotation = [0, 0, radians(0)]

# Place the tall cabinet against the left wall in the lower part of the room.
floor_storage_cabinet[0].position = [0.20, 1.80, 0.90]
floor_storage_cabinet[0].rotation = [0, 0, radians(0)]

# Put the desk against the right wall of the lower rectangular area. It faces
# inward toward the cabinet and leaves the window and door approaches clear.
executive_desk[0].position = [1.625, 1.80, 0.375]
executive_desk[0].rotation = [0, 0, radians(180)]

# The microwave is centered securely on top of the tall storage cabinet.
storage_box[0].position = [0.20, 1.80, 1.95]
storage_box[0].rotation = [0, 0, radians(0)]

# Place the framed photo upright on the credenza, near its back edge.
framed_photo[0].position = [0.08, 3.30, 0.975]
framed_photo[0].rotation = [0, 0, radians(0)]


# Fixed targets preserve the selected non-overlapping arrangement while the
# wall and support constraints retain its important layout semantics.
credenza_target = AssetInstance(position=[0.225, 3.30, 0.375])
cabinet_target = AssetInstance(position=[0.20, 1.80, 0.90])
desk_target = AssetInstance(position=[1.625, 1.80, 0.375])
microwave_target = AssetInstance(position=[0.20, 1.80, 1.95])
photo_target = AssetInstance(position=[0.08, 3.30, 0.975])

# Credenza: wall contact is the primary requested relationship.
solver.against_wall(desk_return_credenza[0], walls[5])
solver.distance_constraint(
    desk_return_credenza[0], credenza_target, 0.0, 0.0, weight=10
)
solver.align_with(desk_return_credenza[0], floor_storage_cabinet[0])

# Cabinet: keep it against the left wall and facing into the room.
solver.against_wall(floor_storage_cabinet[0], walls[5])
solver.distance_constraint(
    floor_storage_cabinet[0], cabinet_target, 0.0, 0.0, weight=10
)
solver.point_towards(floor_storage_cabinet[0], executive_desk[0])

# Desk: keep it against the lower right wall and facing the cabinet.
solver.against_wall(executive_desk[0], walls[1])
solver.distance_constraint(
    executive_desk[0], desk_target, 0.0, 0.0, weight=10
)
solver.point_towards(executive_desk[0], floor_storage_cabinet[0])

# Microwave: support, position, and orientation constraints keep it centered
# on the cabinet rather than allowing it to be placed on the floor.
solver.on_top_of(storage_box[0], floor_storage_cabinet[0])
solver.distance_constraint(
    storage_box[0], microwave_target, 0.0, 0.0, weight=10
)
solver.align_with(storage_box[0], floor_storage_cabinet[0])

# Framed photo: the required support relationship is specified first. Its
# target keeps it upright near the back of the credenza without overhanging.
solver.on_top_of(framed_photo[0], desk_return_credenza[0])
solver.distance_constraint(
    framed_photo[0], photo_target, 0.0, 0.0, weight=10
)
solver.align_with(framed_photo[0], desk_return_credenza[0])

solver.constraints = []
desk_return_credenza[0].position = [0.22499993443489075, 3.299999952316284, 0.375]
desk_return_credenza[0].rotation = [0, 0, -1.8682206185512842e-07]
desk_return_credenza[0].optimize = 2
framed_photo[0].position = [0.07999999821186066, 3.299999952316284, 0.9750000238418579]
framed_photo[0].rotation = [0, 0, 6.300554133821459e-07]
framed_photo[0].optimize = 2
executive_desk[0].position = [1.625, 1.7999999523162842, 0.375]
executive_desk[0].rotation = [0, 0, -3.141592448588378]
executive_desk[0].optimize = 2
floor_storage_cabinet[0].position = [0.2000001072883606, 1.7999999523162842, 0.8999999761581421]
floor_storage_cabinet[0].rotation = [0, 0, 1.6372424446681267e-07]
floor_storage_cabinet[0].optimize = 2
storage_box[0].position = [0.20000000298023224, 1.7999999523162842, 1.9499999284744263]
storage_box[0].rotation = [0, 0, 4.633291444339665e-07]
storage_box[0].optimize = 2

