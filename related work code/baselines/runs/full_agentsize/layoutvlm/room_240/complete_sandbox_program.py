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
    Wall(corner1=[2.16, 1.70, 0.00], corner2=[2.76, 1.70, 0.00]),
    Wall(corner1=[2.76, 1.70, 0.00], corner2=[2.76, 4.82, 0.00]),
    Wall(corner1=[2.76, 4.82, 0.00], corner2=[0.00, 4.82, 0.00]),
    Wall(corner1=[0.00, 4.82, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.76, 0.00, 0.00]),
    Wall(corner1=[2.76, 0.00, 0.00], corner2=[2.76, 1.46, 0.00]),
    Wall(corner1=[2.76, 1.46, 0.00], corner2=[2.16, 1.46, 0.00]),
    Wall(corner1=[2.16, 1.46, 0.00], corner2=[2.16, 1.70, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bed = Assets(description="bed", size=[2.00, 1.40, 0.55], placements=[AssetInstance() for _ in range(1)])
chair = Assets(description="chair", size=[0.62, 0.58, 0.90], placements=[AssetInstance() for _ in range(1)])
bookcase = Assets(description="bookcase", size=[0.30, 0.80, 1.80], placements=[AssetInstance() for _ in range(1)])
fitness_equipment = Assets(description="fitness equipment", size=[0.55, 0.65, 1.25], placements=[AssetInstance() for _ in range(1)])
nightstand = Assets(description="nightstand", size=[0.40, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.60, 1.20, 2.10], placements=[AssetInstance() for _ in range(1)])

bed[0].instance_id = 'bed_0'
chair[0].instance_id = 'chair_0'
bookcase[0].instance_id = 'bookcase_0'
fitness_equipment[0].instance_id = 'fitness_equipment_0'
nightstand[0].instance_id = 'nightstand_0'
wardrobe[0].instance_id = 'wardrobe_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

bed[0].position = [0.5201149053830665, 0.983282053645638, 0.275]
bed[0].rotation = [0, 0, 0]
chair[0].position = [1.1135394533965703, 3.1327521803978655, 0.45]
chair[0].rotation = [0, 0, 0]
bookcase[0].position = [1.0213931415743327, 0.9731364850531402, 0.9]
bookcase[0].rotation = [0, 0, 0]
fitness_equipment[0].position = [1.256993485769629, 3.9283126153016665, 0.625]
fitness_equipment[0].rotation = [0, 0, 0]
nightstand[0].position = [1.105571911795101, 4.789395675371224, 0.275]
nightstand[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.005960050687067077, 0.8252328827035856, 1.05]
wardrobe[0].rotation = [0, 0, 0]
bed[0].position = [0.5201149053830665, 0.983282053645638, 0.275]
bed[0].rotation = [0, 0, 0]
chair[0].position = [1.1135394533965703, 3.1327521803978655, 0.45]
chair[0].rotation = [0, 0, 0]
bookcase[0].position = [1.0213931415743327, 0.9731364850531402, 0.9]
bookcase[0].rotation = [0, 0, 0]
fitness_equipment[0].position = [1.256993485769629, 3.9283126153016665, 0.625]
fitness_equipment[0].rotation = [0, 0, 0]
nightstand[0].position = [1.105571911795101, 4.789395675371224, 0.275]
nightstand[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.005960050687067077, 0.8252328827035856, 1.05]
wardrobe[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the bed lengthwise along the right wall. This leaves a clear corridor
# from the door at the upper-left side of the room into the central floor area.
bed[0].position = [2.06, 3.65, 0.275]
bed[0].rotation = [0, 0, radians(90)]

# Place the chair in the open lower-middle area, facing the bookcase.
chair[0].position = [1.05, 1.60, 0.45]
chair[0].rotation = [0, 0, radians(180)]

# Put shallow storage against the left wall, away from the door approach.
bookcase[0].position = [0.15, 1.60, 0.90]
bookcase[0].rotation = [0, 0, 0]

# The fitness equipment is against the lower portion of the left wall. It does
# not obstruct the window on the bottom wall.
fitness_equipment[0].position = [0.275, 0.75, 0.625]
fitness_equipment[0].rotation = [0, 0, 0]

# Keep the nightstand beside the bed with a small physical clearance.
nightstand[0].position = [1.10, 3.15, 0.275]
nightstand[0].rotation = [0, 0, radians(90)]

# Place the wardrobe against the left wall, below the door-clearance zone.
wardrobe[0].position = [0.30, 2.75, 1.05]
wardrobe[0].rotation = [0, 0, 0]


# Fixed references keep movable assets near their intended functional zones
# while allowing small adjustments for physical feasibility.
bed_anchor = AssetInstance(
    position=[2.06, 3.65, 0.275],
    rotation=[0, 0, radians(90)]
)
chair_anchor = AssetInstance(
    position=[1.05, 1.60, 0.45],
    rotation=[0, 0, radians(180)]
)
bookcase_anchor = AssetInstance(
    position=[0.15, 1.60, 0.90],
    rotation=[0, 0, 0]
)
fitness_anchor = AssetInstance(
    position=[0.275, 0.75, 0.625],
    rotation=[0, 0, 0]
)
nightstand_anchor = AssetInstance(
    position=[1.10, 3.15, 0.275],
    rotation=[0, 0, radians(90)]
)
wardrobe_anchor = AssetInstance(
    position=[0.30, 2.75, 1.05],
    rotation=[0, 0, 0]
)

# Wall-placement constraints are specified first because they express the most
# important room-layout relationships.
solver.against_wall(bed[0], walls[1])
solver.against_wall(bookcase[0], walls[3])
solver.against_wall(fitness_equipment[0], walls[3])
solver.against_wall(wardrobe[0], walls[3])

# Keep each wall-backed object near its selected section of wall rather than
# allowing it to slide toward the door, window, or right-wall recess.
solver.distance_constraint(
    bed[0], bed_anchor, min_distance=0, max_distance=0.12, weight=10
)
solver.distance_constraint(
    bookcase[0], bookcase_anchor, min_distance=0, max_distance=0.10, weight=10
)
solver.distance_constraint(
    fitness_equipment[0], fitness_anchor,
    min_distance=0, max_distance=0.10, weight=10
)
solver.distance_constraint(
    wardrobe[0], wardrobe_anchor, min_distance=0, max_distance=0.10, weight=10
)

# Position the freestanding chair and nightstand in their intended zones.
solver.distance_constraint(
    chair[0], chair_anchor, min_distance=0, max_distance=0.12, weight=10
)
solver.distance_constraint(
    nightstand[0], nightstand_anchor,
    min_distance=0, max_distance=0.10, weight=10
)

# Preserve the bedside relationship. Their centers are about 1.08 m apart,
# which leaves a narrow gap between their bounding boxes.
solver.distance_constraint(
    nightstand[0], bed[0], min_distance=1.02, max_distance=1.16, weight=10
)

# Orientation constraints for every new asset.
solver.align_with(bed[0], bed_anchor)
solver.point_towards(chair[0], bookcase[0])
solver.align_with(bookcase[0], bookcase_anchor)
solver.align_with(fitness_equipment[0], fitness_anchor)
solver.align_with(nightstand[0], bed[0])
solver.align_with(wardrobe[0], wardrobe_anchor)

# Additional low-weight separation constraints discourage neighboring pieces
# from drifting into one another during feasibility adjustment.
solver.distance_constraint(
    fitness_equipment[0], bookcase[0],
    min_distance=0.72, max_distance=None, weight=1
)
solver.distance_constraint(
    bookcase[0], wardrobe[0],
    min_distance=0.95, max_distance=None, weight=1
)
solver.distance_constraint(
    chair[0], bookcase[0],
    min_distance=0.68, max_distance=None, weight=1
)
solver.distance_constraint(
    chair[0], fitness_equipment[0],
    min_distance=0.70, max_distance=None, weight=1
)
solver.distance_constraint(
    chair[0], nightstand[0],
    min_distance=1.20, max_distance=None, weight=1
)
solver.distance_constraint(
    wardrobe[0], nightstand[0],
    min_distance=0.85, max_distance=None, weight=1
)

solver.constraints = []
bookcase[0].position = [0.36074379086494446, 1.7525768280029297, 0.8999999761581421]
bookcase[0].rotation = [0, 0, 0.2836570617925735]
bookcase[0].optimize = 2
bed[0].position = [1.816601276397705, 3.450563430786133, 0.2750000059604645]
bed[0].rotation = [0, 0, 1.843409797272411]
bed[0].optimize = 2
fitness_equipment[0].position = [0.2763098478317261, 0.75, 0.625]
fitness_equipment[0].rotation = [0, 0, -0.004221123431265169]
fitness_equipment[0].optimize = 2
wardrobe[0].position = [0.3028343617916107, 2.75, 1.0499999523162842]
wardrobe[0].rotation = [0, 0, -0.004220092449288509]
wardrobe[0].optimize = 2
chair[0].position = [1.0499999523162842, 1.600000023841858, 0.44999998807907104]
chair[0].rotation = [0, 0, -3.122743098190977]
chair[0].optimize = 2
nightstand[0].position = [1.080954670906067, 3.1309616565704346, 0.2750000059604645]
nightstand[0].rotation = [0, 0, 1.8260453951418]
nightstand[0].optimize = 2

