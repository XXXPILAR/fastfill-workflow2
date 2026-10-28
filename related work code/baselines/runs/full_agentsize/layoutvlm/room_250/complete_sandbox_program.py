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
    Wall(corner1=[3.09, 0.00, 0.00], corner2=[3.09, 2.78, 0.00]),
    Wall(corner1=[3.09, 2.78, 0.00], corner2=[1.71, 4.19, 0.00]),
    Wall(corner1=[1.71, 4.19, 0.00], corner2=[0.52, 2.77, 0.00]),
    Wall(corner1=[0.52, 2.77, 0.00], corner2=[0.00, 2.77, 0.00]),
    Wall(corner1=[0.00, 2.77, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.09, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
computer = Assets(description="computer", size=[0.20, 0.45, 0.40], placements=[AssetInstance() for _ in range(1)])
desk = Assets(description="desk", size=[0.60, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.60, 1.50, 2.10], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[2.30, 1.60, 0.01], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.00, 1.60, 0.55], placements=[AssetInstance() for _ in range(1)])
dining_chair = Assets(description="dining chair", size=[0.50, 0.45, 0.90], placements=[AssetInstance() for _ in range(1)])

computer[0].instance_id = 'computer_0'
desk[0].instance_id = 'desk_0'
wardrobe[0].instance_id = 'wardrobe_0'
carpet[0].instance_id = 'carpet_0'
bed[0].instance_id = 'bed_0'
dining_chair[0].instance_id = 'dining_chair_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

computer[0].position = [2.5617036018878827, 1.9033377564131173, 0.2]
computer[0].rotation = [0, 0, 0]
desk[0].position = [0.3095977623781042, 2.755541745324698, 0.375]
desk[0].rotation = [0, 0, 0]
wardrobe[0].position = [2.9064100381259306, 2.339190171942196, 1.05]
wardrobe[0].rotation = [0, 0, 0]
carpet[0].position = [2.4857655220299115, 0.47667096526238484, 0.005]
carpet[0].rotation = [0, 0, 0]
bed[0].position = [1.1007708003026389, 3.1766576484545594, 0.275]
bed[0].rotation = [0, 0, 0]
dining_chair[0].position = [0.19804750870833326, 0.09781826239630907, 0.45]
dining_chair[0].rotation = [0, 0, 0]
computer[0].position = [2.5617036018878827, 1.9033377564131173, 0.2]
computer[0].rotation = [0, 0, 0]
desk[0].position = [0.3095977623781042, 2.755541745324698, 0.375]
desk[0].rotation = [0, 0, 0]
wardrobe[0].position = [2.9064100381259306, 2.339190171942196, 1.05]
wardrobe[0].rotation = [0, 0, 0]
carpet[0].position = [2.4857655220299115, 0.47667096526238484, 0.005]
carpet[0].rotation = [0, 0, 0]
bed[0].position = [1.1007708003026389, 3.1766576484545594, 0.275]
bed[0].rotation = [0, 0, 0]
dining_chair[0].position = [0.19804750870833326, 0.09781826239630907, 0.45]
dining_chair[0].rotation = [0, 0, 0]

solver.constraints = []

# Keep the entrance corridor (x <= 0.96 near y = 0) unobstructed.
# The desk forms a compact work area along the left wall, while the bed
# occupies the right side. The wardrobe is placed along the bottom wall,
# immediately to the right of the doorway.

desk[0].position = [0.30, 1.80, 0.375]
desk[0].rotation = [0, 0, radians(0)]

computer[0].position = [0.30, 1.80, 0.95]
computer[0].rotation = [0, 0, radians(0)]

dining_chair[0].position = [1.15, 1.80, 0.45]
dining_chair[0].rotation = [0, 0, radians(180)]

wardrobe[0].position = [1.80, 0.30, 1.05]
wardrobe[0].rotation = [0, 0, radians(90)]

bed[0].position = [2.29, 1.75, 0.275]
bed[0].rotation = [0, 0, radians(90)]

# The thin carpet is intentionally placed beneath the bed as a bedroom rug.
carpet[0].position = [2.29, 1.72, 0.005]
carpet[0].rotation = [0, 0, radians(90)]


# Fixed targets preserve the selected functional zones if the layout is adjusted.
desk_anchor = AssetInstance(position=[0.30, 1.80, 0.375])
computer_anchor = AssetInstance(position=[0.30, 1.80, 0.95])
chair_anchor = AssetInstance(position=[1.15, 1.80, 0.45])
wardrobe_anchor = AssetInstance(position=[1.80, 0.30, 1.05])
bed_anchor = AssetInstance(position=[2.29, 1.75, 0.275])
carpet_anchor = AssetInstance(position=[2.29, 1.72, 0.005])

# Rotation references have the desired headings but do not represent new assets.
heading_positive_x = AssetInstance(rotation=[0, 0, radians(0)])
heading_positive_y = AssetInstance(rotation=[0, 0, radians(90)])


# High-priority position constraints maintain the clear entrance and prevent
# the furniture zones from drifting into one another.
solver.distance_constraint(desk[0], desk_anchor, 0, 0, weight=10)
solver.distance_constraint(wardrobe[0], wardrobe_anchor, 0, 0, weight=10)
solver.distance_constraint(bed[0], bed_anchor, 0, 0, weight=10)
solver.distance_constraint(carpet[0], carpet_anchor, 0, 0, weight=10)
solver.distance_constraint(dining_chair[0], chair_anchor, 0, 0, weight=10)
solver.distance_constraint(computer[0], computer_anchor, 0, 0, weight=10)

# Wall constraints retain the intended space-efficient perimeter placement.
solver.against_wall(desk[0], walls[4])
solver.against_wall(wardrobe[0], walls[5])
solver.against_wall(bed[0], walls[0])

# The computer is centered safely on the desktop.
solver.on_top_of(computer[0], desk[0])

# Orientation constraints for every new instance.
solver.align_with(desk[0], heading_positive_x)
solver.point_towards(computer[0], dining_chair[0])
solver.point_towards(dining_chair[0], computer[0])
solver.align_with(wardrobe[0], heading_positive_y)
solver.align_with(bed[0], heading_positive_y)
solver.align_with(carpet[0], bed[0])

# Additional semantic spacing constraints preserve usable clearance at the
# workstation and separation between the chair and bed.
solver.distance_constraint(
    dining_chair[0], desk[0], 0.80, 0.95, weight=1
)
solver.distance_constraint(
    dining_chair[0], bed[0], 1.10, None, weight=1
)

solver.constraints = []
dining_chair[0].position = [1.149999976158142, 1.7999999523162842, 0.44999998807907104]
dining_chair[0].rotation = [0, 0, -3.122743098190977]
dining_chair[0].optimize = 2
carpet[0].position = [1.7676059007644653, 1.6828721761703491, 0.004999999888241291]
carpet[0].rotation = [0, 0, 2.8701411292398737]
carpet[0].optimize = 2
desk[0].position = [0.2997789680957794, 1.7999999523162842, 0.375]
desk[0].rotation = [0, 0, -0.0001111298972071542]
desk[0].optimize = 2
bed[0].position = [1.9133124351501465, 1.75, 0.2750000059604645]
bed[0].rotation = [0, 0, 2.8725206593732207]
bed[0].optimize = 2
computer[0].position = [0.30000001192092896, 1.7999999523162842, 0.949999988079071]
computer[0].rotation = [0, 0, 0.0157079639172164]
computer[0].optimize = 2
wardrobe[0].position = [1.7999999523162842, 0.2998669147491455, 1.0499999523162842]
wardrobe[0].rotation = [0, 0, 1.5707344058280077]
wardrobe[0].optimize = 2

