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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.38, 0.00, 0.00]),
    Wall(corner1=[3.38, 0.00, 0.00], corner2=[3.38, 3.81, 0.00]),
    Wall(corner1=[3.38, 3.81, 0.00], corner2=[0.00, 3.81, 0.00]),
    Wall(corner1=[0.00, 3.81, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
desk = Assets(description="A wooden desk with an attached hutch featuring multiple shelves and drawers. The design includes open shelving for storage and a flat workspace surface.", size=[0.60, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
telescope = Assets(description="A white telescope mounted on a black tripod stand with adjustable legs. The telescope has a cylindrical body with a lens at one end and an eyepiece at the other. It features various knobs and dials for adjustment.", size=[0.70, 0.70, 1.40], placements=[AssetInstance() for _ in range(1)])
dressing_chair = Assets(description="A loft bed with a built-in desk underneath, featuring a wooden frame with metal supports. The bed has colorful pillows and a blue mattress. There is a ladder leading up to the bed and a small shelf next to the desk.", size=[1.05, 2.05, 1.80], placements=[AssetInstance() for _ in range(1)])

desk[0].instance_id = 'desk_0'
telescope[0].instance_id = 'telescope_0'
dressing_chair[0].instance_id = 'dressing_chair_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

desk[0].position = [3.2123113696760632, 1.0732026589110162, 0.9]
desk[0].rotation = [0, 0, 0]
telescope[0].position = [2.3206844957762214, 0.6676881184536049, 0.7]
telescope[0].rotation = [0, 0, 0]
dressing_chair[0].position = [2.8690903276974504, 0.14465327548014137, 0.9]
dressing_chair[0].rotation = [0, 0, 0]
desk[0].position = [3.2123113696760632, 1.0732026589110162, 0.9]
desk[0].rotation = [0, 0, 0]
telescope[0].position = [2.3206844957762214, 0.6676881184536049, 0.7]
telescope[0].rotation = [0, 0, 0]
dressing_chair[0].position = [2.8690903276974504, 0.14465327548014137, 0.9]
dressing_chair[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the loft-bed/dressing-chair unit along the lower portion of the left
# wall, well away from the door opening at (0.00, 3.14).
dressing_chair[0].position = [0.525, 1.025, 0.90]
dressing_chair[0].rotation = [0, 0, radians(0)]

# The requested 0.10 m center-to-center proximity necessarily puts the
# telescope within the open under-loft area of this particular asset.
telescope[0].position = [0.625, 1.025, 0.70]
telescope[0].rotation = [0, 0, radians(0)]

# Keep the desk in the upper-right area without blocking the left-wall door.
# Its initial heading is aimed toward the telescope.
desk[0].position = [2.55, 3.30, 0.90]
desk[0].rotation = [
    0,
    0,
    radians(-127.5),
]

# Fixed references preserve the intended zones while the solver makes small
# adjustments for physical feasibility.
desk_anchor = AssetInstance(position=[2.55, 3.30, 0.90])
telescope_view_reference = AssetInstance(position=[3.38, 2.04, 0.70])
wall_parallel_reference = AssetInstance(
    position=[0.525, 1.025, 0.90],
    rotation=[0, 0, radians(0)],
)

# Highest-priority semantic relationship: keep the telescope within 0.10 m
# of the dressing-chair/loft unit.
solver.distance_constraint(
    telescope[0],
    dressing_chair[0],
    min_distance=0.05,
    max_distance=0.10,
    weight=10,
)

# The dressing-chair unit must remain against the left wall.
solver.against_wall(dressing_chair[0], walls[3])

# Keep the desk in its clear upper-right operating zone.
solver.distance_constraint(
    desk[0],
    desk_anchor,
    min_distance=0,
    max_distance=0,
    weight=10,
)

# Required orientations: the desk faces the telescope, the telescope points
# toward the window, and the wall-side unit stays parallel to the left wall.
solver.point_towards(desk[0], telescope[0])
solver.point_towards(telescope[0], telescope_view_reference)
solver.align_with(dressing_chair[0], wall_parallel_reference, angle=0)

solver.constraints = []
dressing_chair[0].position = [0.5249994397163391, 1.0830405950546265, 0.8999999761581421]
dressing_chair[0].rotation = [0, 0, -4.6511006727541847e-07]
dressing_chair[0].optimize = 2
telescope[0].position = [1.302167534828186, 0.34807252883911133, 0.699999988079071]
telescope[0].rotation = [0, 0, 0.01256637125682779]
telescope[0].optimize = 2
desk[0].position = [2.549999952316284, 3.2070488929748535, 0.8999999761581421]
desk[0].rotation = [0, 0, -2.1364539502921915]
desk[0].optimize = 2

