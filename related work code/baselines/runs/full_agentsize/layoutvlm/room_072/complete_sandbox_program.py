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
    Wall(corner1=[4.27, 0.00, 0.00], corner2=[4.27, 1.77, 0.00]),
    Wall(corner1=[4.27, 1.77, 0.00], corner2=[1.77, 1.77, 0.00]),
    Wall(corner1=[1.77, 1.77, 0.00], corner2=[1.77, 4.77, 0.00]),
    Wall(corner1=[1.77, 4.77, 0.00], corner2=[0.00, 4.77, 0.00]),
    Wall(corner1=[0.00, 4.77, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.27, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
shelf_A = Assets(description="shelf", size=[0.22, 0.75, 0.04], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.50, 0.90, 0.82], placements=[AssetInstance() for _ in range(1)])
sink = Assets(description="sink", size=[0.42, 0.55, 0.18], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.20, 0.65, 0.04], placements=[AssetInstance() for _ in range(1)])
shelf_C = Assets(description="shelf", size=[0.20, 0.65, 0.04], placements=[AssetInstance() for _ in range(1)])
shelf_D = Assets(description="shelf", size=[0.20, 0.65, 0.04], placements=[AssetInstance() for _ in range(1)])
shelf_E = Assets(description="shelf", size=[0.20, 0.65, 0.04], placements=[AssetInstance() for _ in range(1)])
bottle_A = Assets(description="bottle", size=[0.08, 0.08, 0.22], placements=[AssetInstance() for _ in range(1)])
toilet = Assets(description="toilet", size=[0.70, 0.40, 0.78], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.35, 0.60, 1.80], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="bottle", size=[0.07, 0.07, 0.20], placements=[AssetInstance() for _ in range(1)])
bottle_C = Assets(description="bottle", size=[0.08, 0.08, 0.24], placements=[AssetInstance() for _ in range(1)])

shelf_A[0].instance_id = 'shelf_A_0'
cabinet_A[0].instance_id = 'cabinet_A_0'
sink[0].instance_id = 'sink_0'
shelf_B[0].instance_id = 'shelf_B_0'
shelf_C[0].instance_id = 'shelf_C_0'
shelf_D[0].instance_id = 'shelf_D_0'
shelf_E[0].instance_id = 'shelf_E_0'
bottle_A[0].instance_id = 'bottle_A_0'
toilet[0].instance_id = 'toilet_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
bottle_B[0].instance_id = 'bottle_B_0'
bottle_C[0].instance_id = 'bottle_C_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

shelf_A[0].position = [2.1072142802490106, 0.709226762383043, 0.02]
shelf_A[0].rotation = [0, 0, 0]
cabinet_A[0].position = [1.0338528598530161, 0.3677135859502692, 0.41]
cabinet_A[0].rotation = [0, 0, 0]
sink[0].position = [3.0390301840547256, 0.3724950162753917, 0.09]
sink[0].rotation = [0, 0, 0]
shelf_B[0].position = [0.6281084905524777, 1.3682016938312314, 0.02]
shelf_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [3.7438843704484284, 0.055578361110045695, 0.02]
shelf_C[0].rotation = [0, 0, 0]
shelf_D[0].position = [1.2465697438470644, 3.2943617686976783, 0.02]
shelf_D[0].rotation = [0, 0, 0]
shelf_E[0].position = [2.6666100097280907, 0.2458593537122086, 0.02]
shelf_E[0].rotation = [0, 0, 0]
bottle_A[0].position = [1.860258045420073, 1.4604892619191245, 0.11]
bottle_A[0].rotation = [0, 0, 0]
toilet[0].position = [2.9577295433911828, 0.6321925052325672, 0.39]
toilet[0].rotation = [0, 0, 0]
cabinet_B[0].position = [2.8061303643287467, 0.42333757920244897, 0.9]
cabinet_B[0].rotation = [0, 0, 0]
bottle_B[0].position = [2.806306184659025, 0.7776390745617234, 0.1]
bottle_B[0].rotation = [0, 0, 0]
bottle_C[0].position = [0.4989457248035725, 1.5186517895853684, 0.12]
bottle_C[0].rotation = [0, 0, 0]
shelf_A[0].position = [2.1072142802490106, 0.709226762383043, 0.02]
shelf_A[0].rotation = [0, 0, 0]
cabinet_A[0].position = [1.0338528598530161, 0.3677135859502692, 0.41]
cabinet_A[0].rotation = [0, 0, 0]
sink[0].position = [3.0390301840547256, 0.3724950162753917, 0.09]
sink[0].rotation = [0, 0, 0]
shelf_B[0].position = [0.6281084905524777, 1.3682016938312314, 0.02]
shelf_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [3.7438843704484284, 0.055578361110045695, 0.02]
shelf_C[0].rotation = [0, 0, 0]
shelf_D[0].position = [1.2465697438470644, 3.2943617686976783, 0.02]
shelf_D[0].rotation = [0, 0, 0]
shelf_E[0].position = [2.6666100097280907, 0.2458593537122086, 0.02]
shelf_E[0].rotation = [0, 0, 0]
bottle_A[0].position = [1.860258045420073, 1.4604892619191245, 0.11]
bottle_A[0].rotation = [0, 0, 0]
toilet[0].position = [2.9577295433911828, 0.6321925052325672, 0.39]
toilet[0].rotation = [0, 0, 0]
cabinet_B[0].position = [2.8061303643287467, 0.42333757920244897, 0.9]
cabinet_B[0].rotation = [0, 0, 0]
bottle_B[0].position = [2.806306184659025, 0.7776390745617234, 0.1]
bottle_B[0].rotation = [0, 0, 0]
bottle_C[0].position = [0.4989457248035725, 1.5186517895853684, 0.12]
bottle_C[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the floating shelves on wall surfaces away from both windows.
# shelf_E (o0006) is centered between shelf_C (o0004) and shelf_B (o0003)
# along the interior vertical wall.
shelf_B[0].position = [1.66, 2.20, 1.20]
shelf_B[0].rotation = [0, 0, radians(180)]

shelf_E[0].position = [1.66, 2.95, 1.20]
shelf_E[0].rotation = [0, 0, radians(180)]

shelf_C[0].position = [1.66, 3.70, 1.20]
shelf_C[0].rotation = [0, 0, radians(180)]

shelf_D[0].position = [1.66, 4.40, 1.20]
shelf_D[0].rotation = [0, 0, radians(180)]

# This shelf is mounted on the right wall of the lower part of the room.
shelf_A[0].position = [4.16, 1.25, 1.20]
shelf_A[0].rotation = [0, 0, radians(180)]

# The vanity cabinet and sink are placed against the horizontal interior
# wall. Their location leaves a wide, unobstructed route from the door.
cabinet_A[0].position = [2.40, 1.52, 0.41]
cabinet_A[0].rotation = [0, 0, radians(-90)]

sink[0].position = [2.40, 1.52, 0.91]
sink[0].rotation = [0, 0, radians(-90)]

# The toilet is in the lower-right zone and faces the sink while remaining
# clear of the door opening centered at x=0.71.
toilet[0].position = [3.35, 0.70, 0.39]
toilet[0].rotation = [0, 0, radians(142)]

# The tall cabinet uses the right wall without blocking the door or toilet.
cabinet_B[0].position = [4.095, 0.48, 0.90]
cabinet_B[0].rotation = [0, 0, radians(180)]

# Small objects are supported by the sink and the right-wall shelf.
bottle_A[0].position = [2.40, 1.52, 1.11]
bottle_A[0].rotation = [0, 0, radians(-90)]

bottle_B[0].position = [4.10, 1.08, 1.32]
bottle_B[0].rotation = [0, 0, radians(180)]

bottle_C[0].position = [4.10, 1.39, 1.34]
bottle_C[0].rotation = [0, 0, radians(180)]


# Important wall attachment and ordering constraints for o0004, o0006,
# and o0003. The equal 0.75 m spacing keeps o0006 exactly between them.
solver.against_wall(shelf_C[0], walls[2])
solver.against_wall(shelf_E[0], walls[2])
solver.against_wall(shelf_B[0], walls[2])
solver.distance_constraint(shelf_E[0], shelf_C[0], 0.75, 0.75, weight=10)
solver.distance_constraint(shelf_E[0], shelf_B[0], 0.75, 0.75, weight=10)
solver.distance_constraint(shelf_B[0], shelf_C[0], 1.50, 1.50, weight=10)

solver.align_with(shelf_C[0], shelf_E[0])
solver.align_with(shelf_E[0], shelf_C[0])
solver.align_with(shelf_B[0], shelf_E[0])

# Attach the remaining floating shelves to their intended walls and preserve
# their inward-facing orientations.
solver.against_wall(shelf_D[0], walls[2])
solver.align_with(shelf_D[0], shelf_C[0])

solver.against_wall(shelf_A[0], walls[0])
solver.align_with(shelf_A[0], shelf_C[0])

# Keep the vanity against the interior wall. The sink is both wall-adjacent
# and supported by the vanity cabinet.
solver.against_wall(cabinet_A[0], walls[1])
solver.align_with(cabinet_A[0], sink[0])

solver.on_top_of(sink[0], cabinet_A[0])
solver.against_wall(sink[0], walls[1])
solver.align_with(sink[0], cabinet_A[0])
solver.distance_constraint(sink[0], cabinet_A[0], 0.50, 0.50, weight=10)

# The toilet-to-sink relationship is prioritized so the toilet faces the
# sink as required. Their spacing leaves usable clearance around both.
solver.distance_constraint(toilet[0], sink[0], 1.15, 1.45, weight=10)
solver.point_towards(toilet[0], sink[0])

# Keep the tall cabinet against the right wall and oriented into the room.
solver.against_wall(cabinet_B[0], walls[0])
solver.align_with(cabinet_B[0], shelf_A[0])
solver.distance_constraint(cabinet_B[0], toilet[0], 0.75, None, weight=10)

# Preserve clear floor space in front of the door.
door_clearance_point = AssetInstance(position=[0.71, 0.55, 0.41])
solver.distance_constraint(cabinet_A[0], door_clearance_point, 1.20, None, weight=10)
solver.distance_constraint(toilet[0], door_clearance_point, 1.80, None, weight=10)
solver.distance_constraint(cabinet_B[0], door_clearance_point, 2.70, None, weight=10)

# Every bottle receives vertical support, a position constraint relative to
# that support, and an orientation constraint.
solver.on_top_of(bottle_A[0], sink[0])
solver.distance_constraint(bottle_A[0], sink[0], 0.18, 0.24, weight=10)
solver.align_with(bottle_A[0], sink[0])

solver.on_top_of(bottle_B[0], shelf_A[0])
solver.distance_constraint(bottle_B[0], shelf_A[0], 0.12, 0.25, weight=10)
solver.align_with(bottle_B[0], shelf_A[0])

solver.on_top_of(bottle_C[0], shelf_A[0])
solver.distance_constraint(bottle_C[0], shelf_A[0], 0.12, 0.25, weight=10)
solver.align_with(bottle_C[0], shelf_A[0])

# Keep the two shelf-supported bottles separated rather than overlapping.
solver.distance_constraint(bottle_B[0], bottle_C[0], 0.25, 0.40, weight=10)

solver.constraints = []
shelf_A[0].position = [4.153921127319336, 1.25, 0.019999999552965164]
shelf_A[0].rotation = [0, 0, -3.1203866501961928]
shelf_A[0].optimize = 2
bottle_B[0].position = [4.099999904632568, 1.0800000429153442, 0.14000000059604645]
bottle_B[0].rotation = [0, 0, -3.1156299670346495]
bottle_B[0].optimize = 2
sink[0].position = [2.4000000953674316, 1.5299999713897705, 0.9099999666213989]
sink[0].rotation = [0, 0, -1.546479131302505]
sink[0].optimize = 2
shelf_D[0].position = [1.6699994802474976, 4.400000095367432, 0.019999999552965164]
shelf_D[0].rotation = [0, 0, 3.1410230588281443]
shelf_D[0].optimize = 2
bottle_A[0].position = [2.4000000953674316, 1.5199999809265137, 1.1100000143051147]
bottle_A[0].rotation = [0, 0, -1.548005765770382]
bottle_A[0].optimize = 2
cabinet_A[0].position = [2.4000000953674316, 1.5158109664916992, 0.4099999964237213]
cabinet_A[0].rotation = [0, 0, -1.558923309724332]
cabinet_A[0].optimize = 2
shelf_E[0].position = [1.6699994802474976, 2.950000047683716, 0.019999999552965164]
shelf_E[0].rotation = [0, 0, -3.1297196341954674]
shelf_E[0].optimize = 2
toilet[0].position = [3.3499999046325684, 0.699999988079071, 0.38999998569488525]
toilet[0].rotation = [0, 0, 2.494075492316327]
toilet[0].optimize = 2
bottle_C[0].position = [4.090000152587891, 1.399999976158142, 0.1599999964237213]
bottle_C[0].rotation = [0, 0, -3.1156299670346495]
bottle_C[0].optimize = 2
cabinet_B[0].position = [4.085000514984131, 0.47999998927116394, 0.8999999761581421]
cabinet_B[0].rotation = [0, 0, -3.1359411305730807]
cabinet_B[0].optimize = 2
shelf_C[0].position = [1.6699994802474976, 3.700000047683716, 0.019999999552965164]
shelf_C[0].rotation = [0, 0, -3.1266087357474963]
shelf_C[0].optimize = 2
shelf_B[0].position = [1.6699994802474976, 2.200000047683716, 0.019999999552965164]
shelf_B[0].rotation = [0, 0, -3.1359411296508926]
shelf_B[0].optimize = 2

