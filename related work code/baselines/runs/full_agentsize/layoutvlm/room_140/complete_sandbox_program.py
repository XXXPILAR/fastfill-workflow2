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
single_bed = Assets(description="Twin size bed with brown headboard and purple blanket.", size=[2.00, 1.00, 0.90], placements=[AssetInstance() for _ in range(1)])
low_dresser = Assets(description="A brown commode with three drawers and an opening with a green plant and a blue pot.", size=[0.45, 1.00, 0.75], placements=[AssetInstance() for _ in range(1)])
desk_chair = Assets(description="Wood chair with a flat seat and rectangular backrest.", size=[0.50, 0.45, 0.85], placements=[AssetInstance() for _ in range(1)])
framed_photo = Assets(description="A black and white picture of an army leader in full uniform in a light brown wooden frame.", size=[0.05, 0.25, 0.30], placements=[AssetInstance() for _ in range(1)])
desk_lamp = Assets(description="an adjustable-arm desk lamp.", size=[0.35, 0.20, 0.50], placements=[AssetInstance() for _ in range(1)])
study_desk = Assets(description="A desk with two drawers on the right side.", size=[0.55, 1.10, 0.75], placements=[AssetInstance() for _ in range(1)])
pillow = Assets(description="A plain white square pillow.", size=[0.50, 0.50, 0.12], placements=[AssetInstance() for _ in range(1)])

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

single_bed[0].position = [0.9341873611585902, 0.8348570783232755, 0.45]
single_bed[0].rotation = [0, 0, 0]
low_dresser[0].position = [2.1763428932036977, 1.7018466985994951, 0.375]
low_dresser[0].rotation = [0, 0, 0]
desk_chair[0].position = [2.145318571181198, 2.470218198251523, 0.425]
desk_chair[0].rotation = [0, 0, 0]
framed_photo[0].position = [1.3329299173746134, 1.480752833402402, 0.15]
framed_photo[0].rotation = [0, 0, 0]
desk_lamp[0].position = [0.06818926514919887, 2.289079969277846, 0.25]
desk_lamp[0].rotation = [0, 0, 0]
study_desk[0].position = [1.5880584394742208, 1.059297596647037, 0.375]
study_desk[0].rotation = [0, 0, 0]
pillow[0].position = [1.7439461074960771, 1.283238416393818, 0.06]
pillow[0].rotation = [0, 0, 0]
single_bed[0].position = [0.9341873611585902, 0.8348570783232755, 0.45]
single_bed[0].rotation = [0, 0, 0]
low_dresser[0].position = [2.1763428932036977, 1.7018466985994951, 0.375]
low_dresser[0].rotation = [0, 0, 0]
desk_chair[0].position = [2.145318571181198, 2.470218198251523, 0.425]
desk_chair[0].rotation = [0, 0, 0]
framed_photo[0].position = [1.3329299173746134, 1.480752833402402, 0.15]
framed_photo[0].rotation = [0, 0, 0]
desk_lamp[0].position = [0.06818926514919887, 2.289079969277846, 0.25]
desk_lamp[0].rotation = [0, 0, 0]
study_desk[0].position = [1.5880584394742208, 1.059297596647037, 0.375]
study_desk[0].rotation = [0, 0, 0]
pillow[0].position = [1.7439461074960771, 1.283238416393818, 0.06]
pillow[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the bed along the lower section of the west wall, away from the window.
# Its headboard is against the west wall and the bed extends toward the room.
single_bed[0].position = [1.00, 0.50, 0.45]
single_bed[0].rotation = [0, 0, radians(0)]

# Place the low dresser against the north wall, to the left of the study area.
low_dresser[0].position = [0.65, 2.775, 0.375]
low_dresser[0].rotation = [0, 0, radians(-90)]

# Place the desk against the north wall on the right side of the room.
# This leaves the east-wall doorway and its approach unobstructed.
study_desk[0].position = [2.25, 2.725, 0.375]
study_desk[0].rotation = [0, 0, radians(-90)]

# Place the chair immediately in front of the desk while keeping it west of
# the doorway's circulation zone.
desk_chair[0].position = [2.25, 2.12, 0.425]
desk_chair[0].rotation = [0, 0, radians(90)]

# The framed photo stands on the low dresser and faces into the room.
framed_photo[0].position = [0.65, 2.72, 0.90]
framed_photo[0].rotation = [0, 0, radians(-90)]

# Put the lamp on the right side of the desktop, leaving useful work space.
desk_lamp[0].position = [2.55, 2.72, 1.00]
desk_lamp[0].rotation = [0, 0, radians(-90)]

# Put the pillow near the bed's headboard.
pillow[0].position = [0.35, 0.50, 0.96]
pillow[0].rotation = [0, 0, radians(0)]


# High-priority anchors preserve the non-overlapping layout and keep the
# doorway approach clear if the solver adjusts the scene.
bed_anchor = AssetInstance(position=[1.00, 0.50, 0.45])
dresser_anchor = AssetInstance(position=[0.65, 2.775, 0.375])
desk_anchor = AssetInstance(position=[2.25, 2.725, 0.375])
chair_anchor = AssetInstance(position=[2.25, 2.12, 0.425])
photo_anchor = AssetInstance(position=[0.65, 2.72, 0.90])
lamp_anchor = AssetInstance(position=[2.55, 2.72, 1.00])
pillow_anchor = AssetInstance(position=[0.35, 0.50, 0.96])

solver.distance_constraint(single_bed[0], bed_anchor, 0, 0, weight=10)
solver.distance_constraint(low_dresser[0], dresser_anchor, 0, 0, weight=10)
solver.distance_constraint(study_desk[0], desk_anchor, 0, 0, weight=10)
solver.distance_constraint(desk_chair[0], chair_anchor, 0, 0, weight=10)
solver.distance_constraint(framed_photo[0], photo_anchor, 0, 0, weight=10)
solver.distance_constraint(desk_lamp[0], lamp_anchor, 0, 0, weight=10)
solver.distance_constraint(pillow[0], pillow_anchor, 0, 0, weight=10)

# Maintain the intended relationships with the room boundary.
solver.against_wall(single_bed[0], walls[2])
solver.against_wall(low_dresser[0], walls[1])
solver.against_wall(study_desk[0], walls[1])

# Keep the chair at a practical working distance from the desk.
solver.distance_constraint(
    desk_chair[0], study_desk[0], 0.55, 0.70, weight=5
)

# The photo, lamp, and pillow must remain supported by their respective
# furniture surfaces. Their distance constraints also provide the required
# horizontal position semantics.
solver.on_top_of(framed_photo[0], low_dresser[0])
solver.distance_constraint(
    framed_photo[0], low_dresser[0], 0.50, 0.60, weight=5
)

solver.on_top_of(desk_lamp[0], study_desk[0])
solver.distance_constraint(
    desk_lamp[0], study_desk[0], 0.65, 0.75, weight=5
)

solver.on_top_of(pillow[0], single_bed[0])
solver.distance_constraint(
    pillow[0], single_bed[0], 0.80, 0.95, weight=5
)

# Orient all furniture toward its functional use direction.
bed_facing_target = AssetInstance(position=[2.00, 0.50, 0.45])
dresser_facing_target = AssetInstance(position=[0.65, 1.50, 0.375])

solver.point_towards(single_bed[0], bed_facing_target)
solver.point_towards(low_dresser[0], dresser_facing_target)
solver.point_towards(study_desk[0], desk_chair[0])
solver.point_towards(desk_chair[0], study_desk[0])

# Keep supported accessories aligned with the furniture beneath them.
solver.align_with(framed_photo[0], low_dresser[0])
solver.align_with(desk_lamp[0], study_desk[0])
solver.align_with(pillow[0], single_bed[0])

solver.constraints = []
pillow[0].position = [0.654375433921814, 0.326080322265625, 0.9599999785423279]
pillow[0].rotation = [0, 0, 1.57079599255659]
pillow[0].optimize = 2
single_bed[0].position = [1.1393285989761353, 0.9999996423721313, 0.44999998807907104]
single_bed[0].rotation = [0, 0, 1.5707959949788661]
single_bed[0].optimize = 2
desk_chair[0].position = [2.25, 2.119999885559082, 0.42500001192092896]
desk_chair[0].rotation = [0, 0, 1.586504290712113]
desk_chair[0].optimize = 2
study_desk[0].position = [2.25, 2.7249999046325684, 0.375]
study_desk[0].rotation = [0, 0, -1.570796281646547]
study_desk[0].optimize = 2
desk_lamp[0].position = [2.799999952316284, 2.825000047683716, 1.0]
desk_lamp[0].rotation = [0, 0, -1.5707962875244106]
desk_lamp[0].optimize = 2
framed_photo[0].position = [1.1001081466674805, 2.5500051975250244, 0.8999999761581421]
framed_photo[0].rotation = [0, 0, -1.5707962858444715]
framed_photo[0].optimize = 2
low_dresser[0].position = [0.6499999761581421, 2.7750000953674316, 0.375]
low_dresser[0].rotation = [0, 0, -1.5707962828431794]
low_dresser[0].optimize = 2

