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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.40, 0.00, 0.00]),
    Wall(corner1=[2.40, 0.00, 0.00], corner2=[2.40, 2.00, 0.00]),
    Wall(corner1=[2.40, 2.00, 0.00], corner2=[0.00, 2.00, 0.00]),
    Wall(corner1=[0.00, 2.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
linen_cabinet = Assets(description="linen cabinet", size=[0.35, 0.60, 1.80], placements=[AssetInstance() for _ in range(1)])
toilet = Assets(description="toilet", size=[0.70, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
towel_bar = Assets(description="towel bar", size=[0.08, 0.60, 0.05], placements=[AssetInstance() for _ in range(1)])
mirror = Assets(description="mirror", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
pedestal_sink = Assets(description="pedestal sink", size=[0.50, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
clock = Assets(description="clock", size=[0.04, 0.30, 0.30], placements=[AssetInstance() for _ in range(1)])
art_print = Assets(description="art print", size=[0.03, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])

linen_cabinet[0].instance_id = 'linen_cabinet_0'
toilet[0].instance_id = 'toilet_0'
towel_bar[0].instance_id = 'towel_bar_0'
mirror[0].instance_id = 'mirror_0'
pedestal_sink[0].instance_id = 'pedestal_sink_0'
clock[0].instance_id = 'clock_0'
art_print[0].instance_id = 'art_print_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

linen_cabinet[0].position = [0.66546861731365, 0.21919726600576928, 0.9]
linen_cabinet[0].rotation = [0, 0, 0]
toilet[0].position = [1.5114667132929054, 0.39489855802029483, 0.39]
toilet[0].rotation = [0, 0, 0]
towel_bar[0].position = [0.010110176009800374, 1.004962958130605, 0.025]
towel_bar[0].rotation = [0, 0, 0]
mirror[0].position = [2.3742290026500306, 1.9211974593135581, 0.4]
mirror[0].rotation = [0, 0, 0]
pedestal_sink[0].position = [2.0051005907068014, 1.9596187153452023, 0.425]
pedestal_sink[0].rotation = [0, 0, 0]
clock[0].position = [2.3258416289990635, 0.7110429232974007, 0.15]
clock[0].rotation = [0, 0, 0]
art_print[0].position = [0.4297646143325645, 0.43502504364125216, 0.35]
art_print[0].rotation = [0, 0, 0]
linen_cabinet[0].position = [0.66546861731365, 0.21919726600576928, 0.9]
linen_cabinet[0].rotation = [0, 0, 0]
toilet[0].position = [1.5114667132929054, 0.39489855802029483, 0.39]
toilet[0].rotation = [0, 0, 0]
towel_bar[0].position = [0.010110176009800374, 1.004962958130605, 0.025]
towel_bar[0].rotation = [0, 0, 0]
mirror[0].position = [2.3742290026500306, 1.9211974593135581, 0.4]
mirror[0].rotation = [0, 0, 0]
pedestal_sink[0].position = [2.0051005907068014, 1.9596187153452023, 0.425]
pedestal_sink[0].rotation = [0, 0, 0]
clock[0].position = [2.3258416289990635, 0.7110429232974007, 0.15]
clock[0].rotation = [0, 0, 0]
art_print[0].position = [0.4297646143325645, 0.43502504364125216, 0.35]
art_print[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the floor fixtures along separate walls, leaving the middle of the
# compact bathroom open for circulation. Wall-mounted accessories are placed
# at practical heights and distributed across unused wall areas.

linen_cabinet[0].position = [0.40, 1.825, 0.90]
linen_cabinet[0].rotation = [0, 0, radians(-90)]

toilet[0].position = [0.35, 0.55, 0.39]
toilet[0].rotation = [0, 0, radians(0)]

towel_bar[0].position = [1.20, 1.96, 1.20]
towel_bar[0].rotation = [0, 0, radians(-90)]

mirror[0].position = [2.38, 0.55, 1.45]
mirror[0].rotation = [0, 0, radians(180)]

pedestal_sink[0].position = [2.15, 0.55, 0.425]
pedestal_sink[0].rotation = [0, 0, radians(180)]

clock[0].position = [0.02, 1.45, 1.55]
clock[0].rotation = [0, 0, radians(0)]

art_print[0].position = [1.95, 1.985, 1.45]
art_print[0].rotation = [0, 0, radians(-90)]


# Fixed anchors preserve the intended wall locations and, importantly for the
# accessories, their wall-mounting heights.
linen_anchor = AssetInstance(position=[0.40, 1.825, 0.90])
toilet_anchor = AssetInstance(position=[0.35, 0.55, 0.39])
towel_bar_anchor = AssetInstance(position=[1.20, 1.96, 1.20])
mirror_anchor = AssetInstance(position=[2.38, 0.55, 1.45])
sink_anchor = AssetInstance(position=[2.15, 0.55, 0.425])
clock_anchor = AssetInstance(position=[0.02, 1.45, 1.55])
art_print_anchor = AssetInstance(position=[1.95, 1.985, 1.45])

room_center = AssetInstance(position=[1.20, 1.00, 1.00])


# The toilet's required wall contact and relationship to the sink are the
# highest-priority semantic constraints.
solver.against_wall(toilet[0], walls[3])
solver.point_towards(toilet[0], pedestal_sink[0])
solver.distance_constraint(
    toilet[0], toilet_anchor, min_distance=0, max_distance=0, weight=10
)

# The sink occupies the opposite wall and faces back toward the toilet.
solver.against_wall(pedestal_sink[0], walls[1])
solver.point_towards(pedestal_sink[0], toilet[0])
solver.distance_constraint(
    pedestal_sink[0], sink_anchor, min_distance=0, max_distance=0, weight=10
)

# Keep sufficient clear space between the two opposing floor fixtures.
solver.distance_constraint(
    toilet[0], pedestal_sink[0],
    min_distance=1.40, max_distance=1.90, weight=10
)

# The tall cabinet uses the upper-left section of the back wall, away from
# both plumbing fixtures.
solver.against_wall(linen_cabinet[0], walls[2])
solver.point_towards(linen_cabinet[0], room_center)
solver.distance_constraint(
    linen_cabinet[0], linen_anchor, min_distance=0, max_distance=0, weight=10
)
solver.distance_constraint(
    linen_cabinet[0], toilet[0],
    min_distance=0.90, max_distance=None, weight=1
)

# Mount the towel bar horizontally on the back wall in the open section
# between the cabinet and artwork.
solver.against_wall(towel_bar[0], walls[2])
solver.point_towards(towel_bar[0], room_center)
solver.distance_constraint(
    towel_bar[0], towel_bar_anchor, min_distance=0, max_distance=0, weight=10
)

# Center the mirror above the pedestal sink and orient it into the room.
solver.against_wall(mirror[0], walls[1])
solver.align_with(mirror[0], pedestal_sink[0])
solver.distance_constraint(
    mirror[0], mirror_anchor, min_distance=0, max_distance=0, weight=10
)

# Place the clock high on the left wall, clear of the toilet footprint.
solver.against_wall(clock[0], walls[3])
solver.point_towards(clock[0], room_center)
solver.distance_constraint(
    clock[0], clock_anchor, min_distance=0, max_distance=0, weight=10
)

# Place the art print high on the remaining upper-right portion of the back
# wall, separated horizontally from the towel bar.
solver.against_wall(art_print[0], walls[2])
solver.point_towards(art_print[0], room_center)
solver.distance_constraint(
    art_print[0], art_print_anchor, min_distance=0, max_distance=0, weight=10
)
solver.distance_constraint(
    art_print[0], towel_bar[0],
    min_distance=0.70, max_distance=None, weight=1
)

solver.constraints = []
clock[0].position = [0.017607277259230614, 1.4500000476837158, 0.15000000596046448]
clock[0].rotation = [0, 0, 0.001037225984102232]
clock[0].optimize = 2
towel_bar[0].position = [1.2000000476837158, 1.958544135093689, 0.02500000037252903]
towel_bar[0].rotation = [0, 0, -1.5735113391196014]
towel_bar[0].optimize = 2
mirror[0].position = [2.3823728561401367, 0.550000011920929, 0.4000000059604645]
mirror[0].rotation = [0, 0, -3.1405554560888502]
mirror[0].optimize = 2
linen_cabinet[0].position = [0.4000000059604645, 1.8236068487167358, 0.8999999761581421]
linen_cabinet[0].rotation = [0, 0, -1.5735126195832427]
linen_cabinet[0].optimize = 2
pedestal_sink[0].position = [2.1486871242523193, 0.550000011920929, 0.42500001192092896]
pedestal_sink[0].rotation = [0, 0, 3.138744762598536]
pedestal_sink[0].optimize = 2
art_print[0].position = [1.9500000476837158, 1.9838166236877441, 0.3499999940395355]
art_print[0].rotation = [0, 0, -1.5735111208312818]
art_print[0].optimize = 2
toilet[0].position = [0.3514969050884247, 0.550000011920929, 0.38999998569488525]
toilet[0].rotation = [0, 0, -0.002847981137331009]
toilet[0].optimize = 2

