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
    Wall(corner1=[4.74, 0.00, 0.00], corner2=[4.74, 2.24, 0.00]),
    Wall(corner1=[4.74, 2.24, 0.00], corner2=[0.00, 2.24, 0.00]),
    Wall(corner1=[0.00, 2.24, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.74, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
lamp_A = Assets(description="lamp", size=[0.22, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.22, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="shelf", size=[0.25, 0.80, 0.05], placements=[AssetInstance() for _ in range(1)])
toilet = Assets(description="toilet", size=[0.70, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.22, 0.65, 0.05], placements=[AssetInstance() for _ in range(1)])
pot = Assets(description="pot", size=[0.18, 0.18, 0.20], placements=[AssetInstance() for _ in range(1)])
shelf_C = Assets(description="shelf", size=[0.25, 0.80, 0.05], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="cabinet", size=[0.50, 0.90, 0.85], placements=[AssetInstance() for _ in range(1)])
bathtub = Assets(description="bathtub", size=[0.75, 1.70, 0.58], placements=[AssetInstance() for _ in range(1)])
sink = Assets(description="sink", size=[0.45, 0.58, 0.18], placements=[AssetInstance() for _ in range(1)])

lamp_A[0].instance_id = 'lamp_A_0'
lamp_B[0].instance_id = 'lamp_B_0'
shelf_A[0].instance_id = 'shelf_A_0'
toilet[0].instance_id = 'toilet_0'
shelf_B[0].instance_id = 'shelf_B_0'
pot[0].instance_id = 'pot_0'
shelf_C[0].instance_id = 'shelf_C_0'
cabinet[0].instance_id = 'cabinet_0'
bathtub[0].instance_id = 'bathtub_0'
sink[0].instance_id = 'sink_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

lamp_A[0].position = [2.895218597418034, 0.3324952708283742, 0.15]
lamp_A[0].rotation = [0, 0, 0]
lamp_B[0].position = [2.123470814347225, 0.45939076006419927, 0.15]
lamp_B[0].rotation = [0, 0, 0]
shelf_A[0].position = [4.563132780781781, 1.7042246680913062, 0.025]
shelf_A[0].rotation = [0, 0, 0]
toilet[0].position = [2.317220725418522, 0.10179745258682406, 0.39]
toilet[0].rotation = [0, 0, 0]
shelf_B[0].position = [1.5898753851768976, 0.29913926113513273, 0.025]
shelf_B[0].rotation = [0, 0, 0]
pot[0].position = [3.8872896531038723, 1.5263772232668071, 0.1]
pot[0].rotation = [0, 0, 0]
shelf_C[0].position = [0.3070703793840991, 1.457802525921986, 0.025]
shelf_C[0].rotation = [0, 0, 0]
cabinet[0].position = [1.1401645274205179, 1.2401750880026883, 0.425]
cabinet[0].rotation = [0, 0, 0]
bathtub[0].position = [1.1077168636398722, 0.8886293421766673, 0.29]
bathtub[0].rotation = [0, 0, 0]
sink[0].position = [0.5622522930571168, 1.1341542206787618, 0.09]
sink[0].rotation = [0, 0, 0]
lamp_A[0].position = [2.895218597418034, 0.3324952708283742, 0.15]
lamp_A[0].rotation = [0, 0, 0]
lamp_B[0].position = [2.123470814347225, 0.45939076006419927, 0.15]
lamp_B[0].rotation = [0, 0, 0]
shelf_A[0].position = [4.563132780781781, 1.7042246680913062, 0.025]
shelf_A[0].rotation = [0, 0, 0]
toilet[0].position = [2.317220725418522, 0.10179745258682406, 0.39]
toilet[0].rotation = [0, 0, 0]
shelf_B[0].position = [1.5898753851768976, 0.29913926113513273, 0.025]
shelf_B[0].rotation = [0, 0, 0]
pot[0].position = [3.8872896531038723, 1.5263772232668071, 0.1]
pot[0].rotation = [0, 0, 0]
shelf_C[0].position = [0.3070703793840991, 1.457802525921986, 0.025]
shelf_C[0].rotation = [0, 0, 0]
cabinet[0].position = [1.1401645274205179, 1.2401750880026883, 0.425]
cabinet[0].rotation = [0, 0, 0]
bathtub[0].position = [1.1077168636398722, 0.8886293421766673, 0.29]
bathtub[0].rotation = [0, 0, 0]
sink[0].position = [0.5622522930571168, 1.1341542206787618, 0.09]
sink[0].rotation = [0, 0, 0]

solver.constraints = []

# Interior reference points are used to orient wall-mounted fixtures toward the room.
room_center = AssetInstance(position=[2.37, 1.12, 0.50])
left_wall_interior = AssetInstance(position=[2.37, 1.50, 0.90])
right_wall_interior = AssetInstance(position=[2.37, 0.42, 0.50])

# Place the bathtub lengthwise against the top wall. The two larger shelves
# flank it, satisfying the requirement that the bathtub be between them.
bathtub[0].position = [2.55, 1.865, 0.29]
bathtub[0].rotation = [0, 0, radians(-90)]

shelf_A[0].position = [1.10, 2.115, 1.10]
shelf_A[0].rotation = [0, 0, radians(-90)]

shelf_C[0].position = [3.90, 2.115, 1.10]
shelf_C[0].rotation = [0, 0, radians(-90)]

# Put a smaller wall shelf near the lower-left corner, away from the door.
shelf_B[0].position = [0.11, 0.53, 1.15]
shelf_B[0].rotation = [0, 0, 0]

# The cabinet and sink form a compact vanity along the left wall.
cabinet[0].position = [0.25, 1.52, 0.425]
cabinet[0].rotation = [0, 0, 0]

sink[0].position = [0.225, 1.52, 0.94]
sink[0].rotation = [0, 0, 0]

# Keep the toilet against the lower part of the right wall, facing into the
# room. This leaves the window area and the approach from the door clear.
toilet[0].position = [4.39, 0.43, 0.39]
toilet[0].rotation = [0, 0, radians(180)]

# Place the small decorative assets on supported surfaces.
lamp_A[0].position = [1.10, 2.115, 1.275]
lamp_A[0].rotation = [0, 0, radians(-90)]

lamp_B[0].position = [3.90, 2.115, 1.275]
lamp_B[0].rotation = [0, 0, radians(-90)]

pot[0].position = [0.11, 0.53, 1.275]
pot[0].rotation = [0, 0, 0]


# Bathtub: wall contact and orientation are the highest-priority constraints.
solver.against_wall(bathtub[0], walls[1])
solver.point_towards(bathtub[0], room_center)

# Keep the two flanking shelves on the same wall and at controlled distances
# from the bathtub so the bathtub remains spatially between them.
solver.against_wall(shelf_A[0], walls[1])
solver.distance_constraint(shelf_A[0], bathtub[0], 1.40, 1.50, weight=10)
solver.align_with(shelf_A[0], bathtub[0])

solver.against_wall(shelf_C[0], walls[1])
solver.distance_constraint(shelf_C[0], bathtub[0], 1.30, 1.40, weight=10)
solver.align_with(shelf_C[0], bathtub[0])

# Lower-left shelf and vanity use the left wall while remaining separated.
solver.against_wall(shelf_B[0], walls[2])
solver.point_towards(shelf_B[0], room_center)
solver.distance_constraint(shelf_B[0], cabinet[0], 0.95, 1.05, weight=10)

solver.against_wall(cabinet[0], walls[2])
solver.point_towards(cabinet[0], left_wall_interior)
solver.distance_constraint(cabinet[0], shelf_B[0], 0.95, 1.05, weight=10)

# The sink is supported by the cabinet and retains the vanity's wall-facing
# alignment. The small center-distance range keeps it centered on the cabinet.
solver.on_top_of(sink[0], cabinet[0])
solver.against_wall(sink[0], walls[2])
solver.distance_constraint(sink[0], cabinet[0], 0.50, 0.55, weight=10)
solver.align_with(sink[0], cabinet[0])

# Toilet remains against the right wall and faces inward.
solver.against_wall(toilet[0], walls[0])
solver.point_towards(toilet[0], right_wall_interior)
solver.distance_constraint(toilet[0], bathtub[0], 1.45, 1.60, weight=10)

# Lamps are centered on their respective shelves. The distance corresponds to
# the vertical center separation after the on-top constraint is satisfied.
solver.on_top_of(lamp_A[0], shelf_A[0])
solver.distance_constraint(lamp_A[0], shelf_A[0], 0.175, 0.175, weight=10)
solver.align_with(lamp_A[0], shelf_A[0])

solver.on_top_of(lamp_B[0], shelf_C[0])
solver.distance_constraint(lamp_B[0], shelf_C[0], 0.175, 0.175, weight=10)
solver.align_with(lamp_B[0], shelf_C[0])

# Center the pot on the smaller shelf.
solver.on_top_of(pot[0], shelf_B[0])
solver.distance_constraint(pot[0], shelf_B[0], 0.125, 0.125, weight=10)
solver.align_with(pot[0], shelf_B[0])

solver.constraints = []
cabinet[0].position = [0.25122982263565063, 1.5199999809265137, 0.42500001192092896]
cabinet[0].rotation = [0, 0, 0.014983914229100701]
cabinet[0].optimize = 2
pot[0].position = [0.10999999940395355, 0.5299999713897705, 0.15000000596046448]
pot[0].rotation = [0, 0, 0.02278960013808119]
pot[0].optimize = 2
bathtub[0].position = [2.549999952316284, 1.8519741296768188, 0.28999999165534973]
bathtub[0].rotation = [0, 0, -1.5558124225587375]
bathtub[0].optimize = 2
shelf_A[0].position = [1.100000023841858, 2.114450693130493, 0.02500000037252903]
shelf_A[0].rotation = [0, 0, -1.5589233074005708]
shelf_A[0].optimize = 2
sink[0].position = [0.22663535177707672, 1.5199999809265137, 0.940000057220459]
sink[0].rotation = [0, 0, 0.005651523938900898]
sink[0].optimize = 2
lamp_A[0].position = [1.100000023841858, 2.125, 0.20000000298023224]
lamp_A[0].rotation = [0, 0, -1.5480074742547933]
lamp_A[0].optimize = 2
lamp_B[0].position = [3.9000000953674316, 2.125, 0.20000000298023224]
lamp_B[0].rotation = [0, 0, -1.5480074742547933]
lamp_B[0].optimize = 2
toilet[0].position = [4.380001068115234, 0.4300000071525574, 0.38999998569488525]
toilet[0].rotation = [0, 0, -3.139051732072762]
toilet[0].optimize = 2
shelf_C[0].position = [3.9000000953674316, 2.114450693130493, 0.02500000037252903]
shelf_C[0].rotation = [0, 0, -1.5589233074005708]
shelf_C[0].optimize = 2
shelf_B[0].position = [0.11485723406076431, 0.5299999713897705, 0.02500000037252903]
shelf_B[0].rotation = [0, 0, 0.014983915997928178]
shelf_B[0].optimize = 2

