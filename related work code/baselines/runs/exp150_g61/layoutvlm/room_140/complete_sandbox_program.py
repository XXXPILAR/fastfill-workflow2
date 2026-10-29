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
    Wall(corner1=[3.00, 0.00, 0.00], corner2=[3.00, 3.00, 0.00]),
    Wall(corner1=[3.00, 3.00, 0.00], corner2=[0.00, 3.00, 0.00]),
    Wall(corner1=[0.00, 3.00, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
single_bed = Assets(description="Twin size bed with brown headboard and purple blanket.", size=[2.05, 1.00, 0.95], placements=[AssetInstance() for _ in range(1)])
low_dresser = Assets(description="A brown commode with three drawers and an opening with a green plant and a blue pot.", size=[0.45, 0.90, 0.80], placements=[AssetInstance() for _ in range(1)])
desk_chair = Assets(description="Wood chair with a flat seat and rectangular backrest.", size=[0.48, 0.45, 0.85], placements=[AssetInstance() for _ in range(1)])
framed_photo = Assets(description="A black and white picture of an army leader in full uniform in a light brown wooden frame.", size=[0.08, 0.24, 0.32], placements=[AssetInstance() for _ in range(1)])
desk_lamp = Assets(description="an adjustable-arm desk lamp.", size=[0.35, 0.18, 0.50], placements=[AssetInstance() for _ in range(1)])
study_desk = Assets(description="A desk with two drawers on the right side.", size=[0.55, 1.10, 0.75], placements=[AssetInstance() for _ in range(1)])
pillow = Assets(description="A plain white square pillow.", size=[0.50, 0.50, 0.14], placements=[AssetInstance() for _ in range(1)])

single_bed[0].instance_id = 'single_bed_0'
low_dresser[0].instance_id = 'low_dresser_0'
desk_chair[0].instance_id = 'desk_chair_0'
framed_photo[0].instance_id = 'framed_photo_0'
desk_lamp[0].instance_id = 'desk_lamp_0'
study_desk[0].instance_id = 'study_desk_0'
pillow[0].instance_id = 'pillow_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

single_bed[0].position = [1.1036306850497786, 0.2727056322906598, 0.475]
single_bed[0].rotation = [0, 0, 0]
low_dresser[0].position = [0.732931019264377, 0.8101494021912822, 0.4]
low_dresser[0].rotation = [0, 0, 0]
desk_chair[0].position = [2.777923821534851, 2.536988908406908, 0.425]
desk_chair[0].rotation = [0, 0, 0]
framed_photo[0].position = [1.3374477537001406, 2.821079853431254, 0.16]
framed_photo[0].rotation = [0, 0, 0]
desk_lamp[0].position = [0.20423310467481426, 2.7542405121859037, 0.25]
desk_lamp[0].rotation = [0, 0, 0]
study_desk[0].position = [1.2661311698944777, 1.7889349154152243, 0.375]
study_desk[0].rotation = [0, 0, 0]
pillow[0].position = [2.519264194824161, 1.254260727769625, 0.07]
pillow[0].rotation = [0, 0, 0]
single_bed[0].position = [1.1036306850497786, 0.2727056322906598, 0.475]
single_bed[0].rotation = [0, 0, 0]
low_dresser[0].position = [0.732931019264377, 0.8101494021912822, 0.4]
low_dresser[0].rotation = [0, 0, 0]
desk_chair[0].position = [2.777923821534851, 2.536988908406908, 0.425]
desk_chair[0].rotation = [0, 0, 0]
framed_photo[0].position = [1.3374477537001406, 2.821079853431254, 0.16]
framed_photo[0].rotation = [0, 0, 0]
desk_lamp[0].position = [0.20423310467481426, 2.7542405121859037, 0.25]
desk_lamp[0].rotation = [0, 0, 0]
study_desk[0].position = [1.2661311698944777, 1.7889349154152243, 0.375]
study_desk[0].rotation = [0, 0, 0]
pillow[0].position = [2.519264194824161, 1.254260727769625, 0.07]
pillow[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the actual wall coordinates: the room occupies [0, 3] x [0, 3].
# Keep the east-side entrance and its approach clear. The bed occupies the
# north side, the desk sits beneath the west window, and the dresser uses
# the south wall. Positions refer to bounding-box centers.

single_bed[0].position = [1.025, 2.50, 0.475]
single_bed[0].rotation = [0, 0, 0]

study_desk[0].position = [0.275, 1.35, 0.375]
study_desk[0].rotation = [0, 0, 0]

# The chair faces west toward the desk, with space behind it for circulation.
desk_chair[0].position = [0.95, 1.35, 0.425]
desk_chair[0].rotation = [0, 0, radians(180)]

# Rotating the dresser puts its shallow dimension perpendicular to the wall.
low_dresser[0].position = [1.55, 0.225, 0.40]
low_dresser[0].rotation = [0, 0, radians(90)]

framed_photo[0].position = [1.55, 0.225, 0.96]
framed_photo[0].rotation = [0, 0, radians(90)]

# Keep the lamp toward the far end of the desktop, leaving working space.
desk_lamp[0].position = [0.275, 1.68, 1.00]
desk_lamp[0].rotation = [0, 0, radians(-90)]

# Place the pillow near the west/headboard end of the bed.
pillow[0].position = [0.40, 2.50, 1.02]
pillow[0].rotation = [0, 0, 0]

# Surface constraints take priority for the small objects.
solver.on_top_of(framed_photo[0], low_dresser[0])
solver.on_top_of(desk_lamp[0], study_desk[0])
solver.on_top_of(pillow[0], single_bed[0])

# Fixed layout anchors preserve the planned footprints and entrance clearance.
# Each new instance receives both a position and an orientation constraint.
# Anchors are reference points only, not additional scene furniture.
def preserve_layout(instance):
    reference = AssetInstance(
        position=list(instance.position),
        rotation=list(instance.rotation),
    )
    solver.distance_constraint(instance, reference, 0, 0, weight=10)
    solver.align_with(instance, reference, angle=0)

for placed_instance in (
    single_bed[0],
    study_desk[0],
    desk_chair[0],
    low_dresser[0],
    framed_photo[0],
    desk_lamp[0],
    pillow[0],
):
    preserve_layout(placed_instance)

# Reinforce the furniture's intended relationship to the room boundary.
solver.against_wall(single_bed[0], walls[1])
solver.against_wall(study_desk[0], walls[2])
solver.against_wall(low_dresser[0], walls[3])

# Functional facing relationships.
solver.point_towards(desk_chair[0], study_desk[0])
solver.align_with(framed_photo[0], low_dresser[0])
solver.align_with(pillow[0], single_bed[0])

# Maintain the chair's usable desk spacing; distances use 3D box centers.
chair_desk_distance = (
    (0.95 - 0.275) ** 2 + (0.425 - 0.375) ** 2
) ** 0.5
solver.distance_constraint(
    desk_chair[0], study_desk[0],
    chair_desk_distance, chair_desk_distance, weight=10,
)

solver.constraints = []
single_bed[0].position = [1.1518620252609253, 1.870307207107544, 0.4749999940395355]
single_bed[0].rotation = [0, 0, -0.9794982397401193]
single_bed[0].optimize = 2
low_dresser[0].position = [1.5499999523162842, 0.2248753160238266, 0.4000000059604645]
low_dresser[0].rotation = [0, 0, 1.5713679780052547]
low_dresser[0].optimize = 2
desk_chair[0].position = [1.0079200267791748, 1.350000023841858, 0.42500001192092896]
desk_chair[0].rotation = [0, 0, -3.125884689672577]
desk_chair[0].optimize = 2
desk_lamp[0].position = [0.2750000059604645, 1.6799999475479126, 1.0]
desk_lamp[0].rotation = [0, 0, -1.5582299555380688]
desk_lamp[0].optimize = 2
study_desk[0].position = [0.2746937870979309, 1.350000023841858, 0.375]
study_desk[0].rotation = [0, 0, -0.00025039914063205483]
study_desk[0].optimize = 2
framed_photo[0].position = [1.5499999523162842, 0.22499999403953552, 0.9600000381469727]
framed_photo[0].rotation = [0, 0, 1.5688619824994066]
framed_photo[0].optimize = 2
pillow[0].position = [0.4000000059604645, 2.5, 1.0199999809265137]
pillow[0].rotation = [0, 0, -0.9633579940955611]
pillow[0].optimize = 2

