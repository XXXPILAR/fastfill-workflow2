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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.24, 0.00, 0.00]),
    Wall(corner1=[6.24, 0.00, 0.00], corner2=[6.24, 4.14, 0.00]),
    Wall(corner1=[6.24, 4.14, 0.00], corner2=[0.00, 4.14, 0.00]),
    Wall(corner1=[0.00, 4.14, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bin = Assets(description="A cylindrical wooden planter with a smooth finish and visible wood grain patterns.", size=[0.55, 0.55, 0.60], placements=[AssetInstance() for _ in range(1)])
seat = Assets(description="A wicker armchair with a cushioned seat and backrest, featuring two decorative pillows. It has wooden legs and a sturdy build.", size=[0.88, 0.90, 0.92], placements=[AssetInstance() for _ in range(1)])
tray = Assets(description="A round table with a textured surface that appears to be made of a mosaic-like pattern. The table has a flat top and a slightly raised edge.", size=[0.85, 0.85, 0.43], placements=[AssetInstance() for _ in range(1)])
mirror = Assets(description="A rectangular mirror with a black frame, positioned on the floor with a small object nearby.", size=[0.06, 0.65, 1.70], placements=[AssetInstance() for _ in range(1)])

bin[0].instance_id = 'bin_0'
seat[0].instance_id = 'seat_0'
tray[0].instance_id = 'tray_0'
mirror[0].instance_id = 'mirror_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

bin[0].position = [0.871388553559226, 3.9908697867662326, 0.3]
bin[0].rotation = [0, 0, 0]
seat[0].position = [1.798909653097246, 3.021466271643824, 0.46]
seat[0].rotation = [0, 0, 0]
tray[0].position = [2.4097558389823224, 3.497093954707144, 0.215]
tray[0].rotation = [0, 0, 0]
mirror[0].position = [0.5216162649563291, 3.1845541308852767, 0.85]
mirror[0].rotation = [0, 0, 0]
bin[0].position = [0.871388553559226, 3.9908697867662326, 0.3]
bin[0].rotation = [0, 0, 0]
seat[0].position = [1.798909653097246, 3.021466271643824, 0.46]
seat[0].rotation = [0, 0, 0]
tray[0].position = [2.4097558389823224, 3.497093954707144, 0.215]
tray[0].rotation = [0, 0, 0]
mirror[0].position = [0.5216162649563291, 3.1845541308852767, 0.85]
mirror[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange a compact seating vignette with the armchair facing the tray table.
# Heights are half of each asset's z-size because all four objects rest on the floor.
bin.placements = [
    AssetInstance(position=[0.42, 3.72, 0.30], rotation=[0, 0, radians(-90)])
]
seat.placements = [
    AssetInstance(position=[2.00, 2.05, 0.46], rotation=[0, 0, radians(0)])
]
tray.placements = [
    AssetInstance(position=[3.50, 2.05, 0.215], rotation=[0, 0, radians(0)])
]
mirror.placements = [
    AssetInstance(position=[6.21, 3.10, 0.85], rotation=[0, 0, radians(180)])
]

# Fixed anchors preserve the intended zones while the solver makes feasibility
# adjustments. These are the primary position constraints, so they come first.
bin_anchor = AssetInstance(position=[0.42, 3.72, 0.30])
seat_anchor = AssetInstance(position=[2.00, 2.05, 0.46])
tray_anchor = AssetInstance(position=[3.50, 2.05, 0.215])
mirror_anchor = AssetInstance(position=[6.21, 3.10, 0.85])

solver.distance_constraint(bin[0], bin_anchor, 0.0, 0.0, weight=10)
solver.distance_constraint(seat[0], seat_anchor, 0.0, 0.0, weight=10)
solver.distance_constraint(tray[0], tray_anchor, 0.0, 0.0, weight=10)
solver.distance_constraint(mirror[0], mirror_anchor, 0.0, 0.0, weight=10)

# Keep the floor mirror flush with the right wall.
solver.against_wall(mirror[0], walls[1])

# The armchair explicitly faces the tray, as required. The mirror faces inward
# toward the seating group, while the rotationally symmetric objects receive
# stable orientation constraints as well.
solver.point_towards(seat[0], tray[0])
solver.align_with(tray[0], seat[0])
solver.align_with(bin[0], seat[0], angle=-90)
solver.point_towards(mirror[0], seat[0])

# Maintain useful clearance between the furniture and decorative objects.
solver.distance_constraint(seat[0], tray[0], 1.35, 1.65, weight=10)
solver.distance_constraint(bin[0], seat[0], 1.90, None, weight=1)
solver.distance_constraint(bin[0], tray[0], 2.50, None, weight=1)
solver.distance_constraint(mirror[0], tray[0], 2.50, None, weight=1)
solver.distance_constraint(mirror[0], seat[0], 3.80, None, weight=1)

solver.constraints = []
tray[0].position = [3.5, 2.049999952316284, 0.2150000035762787]
tray[0].rotation = [0, 0, 0.028273516740422396]
tray[0].optimize = 2
mirror[0].position = [6.213989734649658, 3.0999999046325684, 0.8500000238418579]
mirror[0].rotation = [0, 0, -3.141592202450034]
mirror[0].optimize = 2
seat[0].position = [2.0, 2.049999952316284, 0.46000000834465027]
seat[0].rotation = [0, 0, 0.02827433441159227]
seat[0].optimize = 2
bin[0].position = [0.41999998688697815, 3.7200000286102295, 0.30000001192092896]
bin[0].rotation = [0, 0, -1.542523414966021]
bin[0].optimize = 2

