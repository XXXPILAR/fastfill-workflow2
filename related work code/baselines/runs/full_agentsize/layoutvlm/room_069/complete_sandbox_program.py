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
    Wall(corner1=[2.72, 0.00, 0.00], corner2=[2.72, 3.72, 0.00]),
    Wall(corner1=[2.72, 3.72, 0.00], corner2=[0.00, 3.72, 0.00]),
    Wall(corner1=[0.00, 3.72, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.72, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
cabinet = Assets(description="cabinet", size=[0.50, 0.90, 0.85], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="lamp", size=[0.12, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
toilet = Assets(description="toilet", size=[0.68, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="shelf", size=[0.18, 0.70, 0.06], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.12, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
lamp_C = Assets(description="lamp", size=[0.12, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
sink = Assets(description="sink", size=[0.45, 0.58, 0.18], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.18, 0.65, 0.06], placements=[AssetInstance() for _ in range(1)])
pot = Assets(description="pot", size=[0.16, 0.16, 0.18], placements=[AssetInstance() for _ in range(1)])
shelf_C = Assets(description="shelf", size=[0.18, 0.65, 0.06], placements=[AssetInstance() for _ in range(1)])
bottle_A = Assets(description="bottle", size=[0.07, 0.07, 0.22], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="bottle", size=[0.08, 0.08, 0.25], placements=[AssetInstance() for _ in range(1)])

cabinet[0].instance_id = 'cabinet_0'
lamp_A[0].instance_id = 'lamp_A_0'
toilet[0].instance_id = 'toilet_0'
shelf_A[0].instance_id = 'shelf_A_0'
lamp_B[0].instance_id = 'lamp_B_0'
lamp_C[0].instance_id = 'lamp_C_0'
sink[0].instance_id = 'sink_0'
shelf_B[0].instance_id = 'shelf_B_0'
pot[0].instance_id = 'pot_0'
shelf_C[0].instance_id = 'shelf_C_0'
bottle_A[0].instance_id = 'bottle_A_0'
bottle_B[0].instance_id = 'bottle_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

cabinet[0].position = [2.6963352348510217, 1.6608141854356433, 0.425]
cabinet[0].rotation = [0, 0, 0]
lamp_A[0].position = [2.6837855039337586, 2.5665864440017847, 0.125]
lamp_A[0].rotation = [0, 0, 0]
toilet[0].position = [1.7114796027874066, 2.2467532982933234, 0.39]
toilet[0].rotation = [0, 0, 0]
shelf_A[0].position = [2.0934526121350396, 3.441555771428657, 0.03]
shelf_A[0].rotation = [0, 0, 0]
lamp_B[0].position = [1.6514252477085962, 0.11419372338115748, 0.125]
lamp_B[0].rotation = [0, 0, 0]
lamp_C[0].position = [2.0795720946232596, 2.592038646910479, 0.125]
lamp_C[0].rotation = [0, 0, 0]
sink[0].position = [0.5057704327383192, 1.3764054856876304, 0.09]
sink[0].rotation = [0, 0, 0]
shelf_B[0].position = [1.6950252708897255, 0.5467914344087069, 0.03]
shelf_B[0].rotation = [0, 0, 0]
pot[0].position = [1.1236614081238012, 3.1627418042103073, 0.09]
pot[0].rotation = [0, 0, 0]
shelf_C[0].position = [0.5322666017776583, 1.2273532926934696, 0.03]
shelf_C[0].rotation = [0, 0, 0]
bottle_A[0].position = [0.6114917736568266, 2.2169403163638686, 0.11]
bottle_A[0].rotation = [0, 0, 0]
bottle_B[0].position = [1.0350908276940078, 0.7757672293300194, 0.125]
bottle_B[0].rotation = [0, 0, 0]
cabinet[0].position = [2.6963352348510217, 1.6608141854356433, 0.425]
cabinet[0].rotation = [0, 0, 0]
lamp_A[0].position = [2.6837855039337586, 2.5665864440017847, 0.125]
lamp_A[0].rotation = [0, 0, 0]
toilet[0].position = [1.7114796027874066, 2.2467532982933234, 0.39]
toilet[0].rotation = [0, 0, 0]
shelf_A[0].position = [2.0934526121350396, 3.441555771428657, 0.03]
shelf_A[0].rotation = [0, 0, 0]
lamp_B[0].position = [1.6514252477085962, 0.11419372338115748, 0.125]
lamp_B[0].rotation = [0, 0, 0]
lamp_C[0].position = [2.0795720946232596, 2.592038646910479, 0.125]
lamp_C[0].rotation = [0, 0, 0]
sink[0].position = [0.5057704327383192, 1.3764054856876304, 0.09]
sink[0].rotation = [0, 0, 0]
shelf_B[0].position = [1.6950252708897255, 0.5467914344087069, 0.03]
shelf_B[0].rotation = [0, 0, 0]
pot[0].position = [1.1236614081238012, 3.1627418042103073, 0.09]
pot[0].rotation = [0, 0, 0]
shelf_C[0].position = [0.5322666017776583, 1.2273532926934696, 0.03]
shelf_C[0].rotation = [0, 0, 0]
bottle_A[0].position = [0.6114917736568266, 2.2169403163638686, 0.11]
bottle_A[0].rotation = [0, 0, 0]
bottle_B[0].position = [1.0350908276940078, 0.7757672293300194, 0.125]
bottle_B[0].rotation = [0, 0, 0]

solver.constraints = []

# The explicit wall coordinates and floor-plan markings use the lower-left
# corner as (0, 0), so placements below follow that coordinate frame.
# The door zone on the right wall (approximately y=1.53 to y=2.42) is kept clear.

# Place the vanity cabinet and toilet along the upper wall, away from the door.
cabinet[0].position = [1.30, 3.47, 0.425]
cabinet[0].rotation = [0, 0, radians(-90)]

toilet[0].position = [2.30, 3.38, 0.39]
toilet[0].rotation = [0, 0, radians(-90)]

# The sink is centered on top of the vanity cabinet.
sink[0].position = [1.30, 3.495, 0.94]
sink[0].rotation = [0, 0, radians(-90)]

# Mount the three shelves high on the upper wall. Their separated x-ranges
# prevent overlap, while leaving the floor and door approach unobstructed.
shelf_A[0].position = [0.45, 3.63, 1.25]
shelf_A[0].rotation = [0, 0, radians(-90)]

shelf_C[0].position = [1.30, 3.63, 1.25]
shelf_C[0].rotation = [0, 0, radians(-90)]

shelf_B[0].position = [2.15, 3.63, 1.25]
shelf_B[0].rotation = [0, 0, radians(-90)]

# Put lamp_A (the specified lamp o0005) on the middle shelf, spatially
# between shelf_A (o0007) and shelf_B (o0009).
lamp_A[0].position = [1.30, 3.60, 1.405]
lamp_A[0].rotation = [0, 0, radians(-90)]

# Distribute the remaining lamps and small items across the shelves.
lamp_B[0].position = [0.27, 3.60, 1.405]
lamp_B[0].rotation = [0, 0, radians(-90)]

bottle_A[0].position = [0.63, 3.60, 1.39]
bottle_A[0].rotation = [0, 0, radians(-90)]

pot[0].position = [1.52, 3.60, 1.37]
pot[0].rotation = [0, 0, radians(-90)]

lamp_C[0].position = [2.00, 3.60, 1.405]
lamp_C[0].rotation = [0, 0, radians(-90)]

bottle_B[0].position = [2.35, 3.60, 1.405]
bottle_B[0].rotation = [0, 0, radians(-90)]


# Fixed references preserve the intended positions and provide inward-facing
# orientation targets. The upper wall is walls[1].
_room_center = AssetInstance(position=[1.36, 1.86, 0.80])

_cabinet_target = AssetInstance(position=[1.30, 3.47, 0.425])
_toilet_target = AssetInstance(position=[2.30, 3.38, 0.39])
_sink_target = AssetInstance(position=[1.30, 3.495, 0.94])

_shelf_A_target = AssetInstance(position=[0.45, 3.63, 1.25])
_shelf_C_target = AssetInstance(position=[1.30, 3.63, 1.25])
_shelf_B_target = AssetInstance(position=[2.15, 3.63, 1.25])

_lamp_A_target = AssetInstance(position=[1.30, 3.60, 1.405])
_lamp_B_target = AssetInstance(position=[0.27, 3.60, 1.405])
_lamp_C_target = AssetInstance(position=[2.00, 3.60, 1.405])
_pot_target = AssetInstance(position=[1.52, 3.60, 1.37])
_bottle_A_target = AssetInstance(position=[0.63, 3.60, 1.39])
_bottle_B_target = AssetInstance(position=[2.35, 3.60, 1.405])


# Major fixtures: keep them against the upper wall and facing into the room.
solver.against_wall(cabinet[0], walls[1])
solver.distance_constraint(
    cabinet[0], _cabinet_target, 0, 0, weight=10
)
solver.point_towards(cabinet[0], _room_center)

solver.against_wall(toilet[0], walls[1])
solver.distance_constraint(
    toilet[0], _toilet_target, 0, 0, weight=10
)
solver.point_towards(toilet[0], _room_center)

# The sink must remain supported by and aligned with the vanity.
solver.on_top_of(sink[0], cabinet[0])
solver.distance_constraint(
    sink[0], _sink_target, 0, 0, weight=10
)
solver.align_with(sink[0], cabinet[0])

# Maintain useful clearance between the toilet and vanity/sink.
solver.distance_constraint(
    toilet[0], cabinet[0], 0.90, None, weight=10
)
solver.distance_constraint(
    toilet[0], sink[0], 0.80, None, weight=10
)


# Wall-mounted shelves remain on the upper wall and face into the room.
solver.against_wall(shelf_A[0], walls[1])
solver.distance_constraint(
    shelf_A[0], _shelf_A_target, 0, 0, weight=10
)
solver.point_towards(shelf_A[0], _room_center)

solver.against_wall(shelf_C[0], walls[1])
solver.distance_constraint(
    shelf_C[0], _shelf_C_target, 0, 0, weight=10
)
solver.point_towards(shelf_C[0], _room_center)

solver.against_wall(shelf_B[0], walls[1])
solver.distance_constraint(
    shelf_B[0], _shelf_B_target, 0, 0, weight=10
)
solver.point_towards(shelf_B[0], _room_center)

# Preserve non-overlapping spacing between adjacent shelves.
solver.distance_constraint(
    shelf_A[0], shelf_C[0], 0.80, 0.90, weight=10
)
solver.distance_constraint(
    shelf_C[0], shelf_B[0], 0.80, 0.90, weight=10
)


# Every small object is supported by a shelf, anchored to a distinct part of
# its surface, and aligned with that shelf.
solver.on_top_of(lamp_A[0], shelf_C[0])
solver.distance_constraint(
    lamp_A[0], _lamp_A_target, 0, 0, weight=10
)
solver.align_with(lamp_A[0], shelf_C[0])

# These constraints explicitly preserve lamp_A between shelf_A and shelf_B.
solver.distance_constraint(
    lamp_A[0], shelf_A[0], 0.84, 0.90, weight=10
)
solver.distance_constraint(
    lamp_A[0], shelf_B[0], 0.84, 0.90, weight=10
)

solver.on_top_of(pot[0], shelf_C[0])
solver.distance_constraint(
    pot[0], _pot_target, 0, 0, weight=10
)
solver.align_with(pot[0], shelf_C[0])

solver.on_top_of(lamp_B[0], shelf_A[0])
solver.distance_constraint(
    lamp_B[0], _lamp_B_target, 0, 0, weight=10
)
solver.align_with(lamp_B[0], shelf_A[0])

solver.on_top_of(bottle_A[0], shelf_A[0])
solver.distance_constraint(
    bottle_A[0], _bottle_A_target, 0, 0, weight=10
)
solver.align_with(bottle_A[0], shelf_A[0])

solver.on_top_of(lamp_C[0], shelf_B[0])
solver.distance_constraint(
    lamp_C[0], _lamp_C_target, 0, 0, weight=10
)
solver.align_with(lamp_C[0], shelf_B[0])

solver.on_top_of(bottle_B[0], shelf_B[0])
solver.distance_constraint(
    bottle_B[0], _bottle_B_target, 0, 0, weight=10
)
solver.align_with(bottle_B[0], shelf_B[0])

solver.constraints = []
cabinet[0].position = [1.2999999523162842, 3.467613458633423, 0.42500001192092896]
cabinet[0].rotation = [0, 0, -1.558923308802138]
cabinet[0].optimize = 2
pot[0].position = [1.5199999809265137, 3.5999999046325684, 0.15000000596046448]
pot[0].rotation = [0, 0, -1.5480059781645814]
pot[0].optimize = 2
shelf_A[0].position = [0.44999998807907104, 3.625537157058716, 0.029999999329447746]
shelf_A[0].rotation = [0, 0, -1.5495903227421746]
shelf_A[0].optimize = 2
bottle_B[0].position = [2.3499999046325684, 3.5999999046325684, 0.1850000023841858]
bottle_B[0].rotation = [0, 0, -1.5480059781645814]
bottle_B[0].optimize = 2
sink[0].position = [1.2999999523162842, 3.494999885559082, 0.940000057220459]
sink[0].rotation = [0, 0, -1.5448361766376022]
sink[0].optimize = 2
lamp_A[0].position = [1.2999999523162842, 3.5999999046325684, 0.1850000023841858]
lamp_A[0].rotation = [0, 0, -1.5416615472412807]
lamp_A[0].optimize = 2
lamp_B[0].position = [0.27000001072883606, 3.5999999046325684, 0.1850000023841858]
lamp_B[0].rotation = [0, 0, -1.5480059781645814]
lamp_B[0].optimize = 2
bottle_A[0].position = [0.6299999952316284, 3.5999999046325684, 0.17000000178813934]
bottle_A[0].rotation = [0, 0, -1.5480059781645814]
bottle_A[0].optimize = 2
toilet[0].position = [2.299999952316284, 3.3899993896484375, 0.38999998569488525]
toilet[0].rotation = [0, 0, -1.5620341029602698]
toilet[0].optimize = 2
lamp_C[0].position = [2.0, 3.5999999046325684, 0.1850000023841858]
lamp_C[0].rotation = [0, 0, -1.5480059781645814]
lamp_C[0].optimize = 2
shelf_C[0].position = [1.2999999523162842, 3.6260673999786377, 0.029999999329447746]
shelf_C[0].rotation = [0, 0, -1.5495903208978976]
shelf_C[0].optimize = 2
shelf_B[0].position = [2.1500000953674316, 3.6260673999786377, 0.029999999329447746]
shelf_B[0].rotation = [0, 0, -1.5495903208978976]
shelf_B[0].optimize = 2

