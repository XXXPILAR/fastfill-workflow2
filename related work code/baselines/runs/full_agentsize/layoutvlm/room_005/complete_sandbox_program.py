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
    Wall(corner1=[0.00, 3.35, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.34, 0.00, 0.00]),
    Wall(corner1=[2.34, 0.00, 0.00], corner2=[2.34, 3.35, 0.00]),
    Wall(corner1=[2.34, 3.35, 0.00], corner2=[0.00, 3.35, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
sink = Assets(description="sink", size=[0.50, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
shelf = Assets(description="shelf", size=[0.20, 0.60, 0.04], placements=[AssetInstance() for _ in range(1)])
toilet = Assets(description="toilet", size=[0.70, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
shower = Assets(description="shower", size=[0.90, 0.90, 2.10], placements=[AssetInstance() for _ in range(1)])

sink[0].instance_id = 'sink_0'
shelf[0].instance_id = 'shelf_0'
toilet[0].instance_id = 'toilet_0'
shower[0].instance_id = 'shower_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

sink[0].position = [1.0971016965855496, 1.588461750402312, 0.425]
sink[0].rotation = [0, 0, 0]
shelf[0].position = [1.5268471367214091, 2.798566399547909, 0.02]
shelf[0].rotation = [0, 0, 0]
toilet[0].position = [1.9280408264215014, 1.599178053893119, 0.39]
toilet[0].rotation = [0, 0, 0]
shower[0].position = [2.0978828867082, 3.2459089405516366, 1.05]
shower[0].rotation = [0, 0, 0]
sink[0].position = [1.0971016965855496, 1.588461750402312, 0.425]
sink[0].rotation = [0, 0, 0]
shelf[0].position = [1.5268471367214091, 2.798566399547909, 0.02]
shelf[0].rotation = [0, 0, 0]
toilet[0].position = [1.9280408264215014, 1.599178053893119, 0.39]
toilet[0].rotation = [0, 0, 0]
shower[0].position = [2.0978828867082, 3.2459089405516366, 1.05]
shower[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the shower in the upper-left corner, leaving the center of the room open.
shower[0].position = [0.45, 2.90, 1.05]
shower[0].rotation = [0, 0, radians(-90)]

# Place the sink against the right wall, facing inward.
sink[0].position = [2.09, 2.35, 0.425]
sink[0].rotation = [0, 0, radians(180)]

# Mount the shallow shelf above the sink. Its bottom is above the sink's top,
# so the two assets can share an x-y location without intersecting.
shelf[0].position = [2.24, 2.35, 1.20]
shelf[0].rotation = [0, 0, radians(180)]

# Place the toilet along the left wall, separated from the corner shower.
# Its orientation is initialized toward the sink and refined by point_towards.
toilet[0].position = [0.40, 1.15, 0.39]
toilet[0].rotation = [0, 0, radians(36)]

# Fixed points preserve the intended zones while allowing the solver to make
# small feasibility adjustments.
shower_anchor = AssetInstance(position=[0.45, 2.90, 1.05])
sink_anchor = AssetInstance(position=[2.09, 2.35, 0.425])
shelf_anchor = AssetInstance(position=[2.24, 2.35, 1.20])
toilet_anchor = AssetInstance(position=[0.40, 1.15, 0.39])

# Orientation targets point wall-backed fixtures into the usable room.
shower_facing_target = AssetInstance(position=[0.45, 1.80, 1.05])
sink_facing_target = AssetInstance(position=[1.20, 2.35, 0.425])

# Important wall relationships are specified first.
solver.against_wall(shower[0], walls[3])  # Upper wall.
solver.against_wall(shower[0], walls[0])  # Left wall, forming a corner shower.
solver.point_towards(shower[0], shower_facing_target)

solver.against_wall(sink[0], walls[2])    # Right wall.
solver.point_towards(sink[0], sink_facing_target)

solver.against_wall(shelf[0], walls[2])   # Wall-mounted above the sink.
solver.align_with(shelf[0], sink[0])

solver.against_wall(toilet[0], walls[0])  # Left wall.
solver.point_towards(toilet[0], sink[0])  # Required: toilet faces the sink.

# Keep each fixture near its selected location. These anchors are compatible
# with the wall constraints and maintain clear circulation through the center.
solver.distance_constraint(shower[0], shower_anchor, 0, 0, weight=10)
solver.distance_constraint(sink[0], sink_anchor, 0, 0, weight=10)
solver.distance_constraint(shelf[0], shelf_anchor, 0, 0, weight=10)
solver.distance_constraint(toilet[0], toilet_anchor, 0, 0, weight=10)

# Soft separation constraints discourage floor-level fixtures from drifting
# into one another if the solver adjusts the initial layout.
solver.distance_constraint(shower[0], sink[0], 1.45, None, weight=1)
solver.distance_constraint(shower[0], toilet[0], 1.30, None, weight=1)
solver.distance_constraint(toilet[0], sink[0], 1.60, None, weight=1)

solver.constraints = []
toilet[0].position = [0.3499999940395355, 1.149999976158142, 0.38999998569488525]
toilet[0].rotation = [0, 0, 3.496740780244119e-08]
toilet[0].optimize = 2
shower[0].position = [0.4499998688697815, 2.6992897987365723, 1.0499999523162842]
shower[0].rotation = [0, 0, 2.1635390596667627e-08]
shower[0].optimize = 2
sink[0].position = [2.0931897163391113, 2.3499999046325684, 0.42500001192092896]
sink[0].rotation = [0, 0, -3.1415926097773794]
sink[0].optimize = 2
shelf[0].position = [2.243190050125122, 2.3499999046325684, 0.019999999552965164]
shelf[0].rotation = [0, 0, -3.141592609834058]
shelf[0].optimize = 2

