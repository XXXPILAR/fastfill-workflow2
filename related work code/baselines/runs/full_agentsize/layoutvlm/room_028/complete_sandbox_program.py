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
    Wall(corner1=[3.84, 0.00, 0.00], corner2=[3.84, 5.87, 0.00]),
    Wall(corner1=[3.84, 5.87, 0.00], corner2=[0.00, 5.87, 0.00]),
    Wall(corner1=[0.00, 5.87, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.84, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
floor_lamp = Assets(description="A modern floor lamp with a cylindrical brown shade and three metallic legs.", size=[0.50, 0.50, 1.55], placements=[AssetInstance() for _ in range(1)])
dining_chair_A = Assets(description="A modern wooden dining chair with a sleek design, featuring a rounded backrest and seat connected by curved wooden supports. The legs are angled outward for stability.", size=[0.56, 0.52, 0.79], placements=[AssetInstance() for _ in range(1)])
dining_chair_B = Assets(description="A modern wooden dining chair with a sleek design, featuring a rounded backrest and seat connected by curved wooden supports. The legs are angled outward for stability.", size=[0.56, 0.52, 0.79], placements=[AssetInstance() for _ in range(1)])
dining_chair_C = Assets(description="A modern wooden dining chair with a sleek design, featuring a rounded backrest and seat connected by curved wooden supports. The legs are angled outward for stability.", size=[0.56, 0.52, 0.79], placements=[AssetInstance() for _ in range(1)])
potted_plant = Assets(description="A potted plant with dark green leaves and a glossy black pot, placed on a reflective black surface.", size=[0.42, 0.42, 0.90], placements=[AssetInstance() for _ in range(1)])
tv_stand = Assets(description="A modern, geometric ceiling light fixture with a wooden exterior and a reflective interior surface.", size=[0.40, 1.60, 0.50], placements=[AssetInstance() for _ in range(1)])
pillow = Assets(description="A square-shaped pillow with a slightly textured surface, resting on a glossy black platform.", size=[0.45, 0.45, 0.15], placements=[AssetInstance() for _ in range(1)])
dining_chair_D = Assets(description="A modern wooden dining chair with a sleek design, featuring a rounded backrest and seat connected by curved wooden supports. The legs are angled outward for stability.", size=[0.56, 0.52, 0.79], placements=[AssetInstance() for _ in range(1)])
three_seat_sofa = Assets(description="A modern, light-colored sofa with three cushioned seats and backrests. It features decorative throw pillows in various colors and patterns, adding a stylish touch. The sofa has a sleek design with clean lines and a sturdy frame.", size=[0.90, 2.15, 0.84], placements=[AssetInstance() for _ in range(1)])
dining_table_A = Assets(description="A modern dining table with a round wooden top and a black cylindrical base.", size=[1.00, 1.00, 0.75], placements=[AssetInstance() for _ in range(1)])
dining_table_B = Assets(description="A modern dining table with a round wooden top and a black cylindrical base.", size=[1.00, 1.00, 0.75], placements=[AssetInstance() for _ in range(1)])

floor_lamp[0].instance_id = 'floor_lamp_0'
dining_chair_A[0].instance_id = 'dining_chair_A_0'
dining_chair_B[0].instance_id = 'dining_chair_B_0'
dining_chair_C[0].instance_id = 'dining_chair_C_0'
potted_plant[0].instance_id = 'potted_plant_0'
tv_stand[0].instance_id = 'tv_stand_0'
pillow[0].instance_id = 'pillow_0'
dining_chair_D[0].instance_id = 'dining_chair_D_0'
three_seat_sofa[0].instance_id = 'three_seat_sofa_0'
dining_table_A[0].instance_id = 'dining_table_A_0'
dining_table_B[0].instance_id = 'dining_table_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

floor_lamp[0].position = [3.6818185590253614, 2.0083852411156724, 0.775]
floor_lamp[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [2.055860912972737, 2.3902429066323942, 0.395]
dining_chair_A[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [1.3700084939113681, 3.7036428461061703, 0.395]
dining_chair_B[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [0.7884706274297858, 3.5882101160029514, 0.395]
dining_chair_C[0].rotation = [0, 0, 0]
potted_plant[0].position = [1.8996471733320832, 3.474099558493802, 0.45]
potted_plant[0].rotation = [0, 0, 0]
tv_stand[0].position = [3.023868262305789, 3.8532542939580723, 0.25]
tv_stand[0].rotation = [0, 0, 0]
pillow[0].position = [1.4639909153725177, 0.18516126536666985, 0.075]
pillow[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [0.24633417012687328, 5.518499291640947, 0.395]
dining_chair_D[0].rotation = [0, 0, 0]
three_seat_sofa[0].position = [3.2637894689243128, 3.3588598004249497, 0.42]
three_seat_sofa[0].rotation = [0, 0, 0]
dining_table_A[0].position = [0.024193864774993516, 4.125550857628485, 0.375]
dining_table_A[0].rotation = [0, 0, 0]
dining_table_B[0].position = [3.2825356438621562, 4.348288367962947, 0.375]
dining_table_B[0].rotation = [0, 0, 0]
floor_lamp[0].position = [3.6818185590253614, 2.0083852411156724, 0.775]
floor_lamp[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [2.055860912972737, 2.3902429066323942, 0.395]
dining_chair_A[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [1.3700084939113681, 3.7036428461061703, 0.395]
dining_chair_B[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [0.7884706274297858, 3.5882101160029514, 0.395]
dining_chair_C[0].rotation = [0, 0, 0]
potted_plant[0].position = [1.8996471733320832, 3.474099558493802, 0.45]
potted_plant[0].rotation = [0, 0, 0]
tv_stand[0].position = [3.023868262305789, 3.8532542939580723, 0.25]
tv_stand[0].rotation = [0, 0, 0]
pillow[0].position = [1.4639909153725177, 0.18516126536666985, 0.075]
pillow[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [0.24633417012687328, 5.518499291640947, 0.395]
dining_chair_D[0].rotation = [0, 0, 0]
three_seat_sofa[0].position = [3.2637894689243128, 3.3588598004249497, 0.42]
three_seat_sofa[0].rotation = [0, 0, 0]
dining_table_A[0].position = [0.024193864774993516, 4.125550857628485, 0.375]
dining_table_A[0].rotation = [0, 0, 0]
dining_table_B[0].position = [3.2825356438621562, 4.348288367962947, 0.375]
dining_table_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Divide the room into a dining zone in the lower-left and a living zone
# across the upper half. The strip along the east wall remains open so that
# both doors have unobstructed entry and circulation space.

# Initial placements: z coordinates place floor-standing objects on the floor.
floor_lamp[0].position = [3.22, 4.65, 0.775]
floor_lamp[0].rotation = [0, 0, radians(180)]

dining_chair_A[0].position = [1.20, 1.80, 0.395]
dining_chair_A[0].rotation = [0, 0, radians(90)]

dining_chair_B[0].position = [0.35, 0.85, 0.395]
dining_chair_B[0].rotation = [0, 0, radians(0)]

dining_chair_C[0].position = [0.35, 2.75, 0.395]
dining_chair_C[0].rotation = [0, 0, radians(0)]

potted_plant[0].position = [3.48, 5.58, 0.45]
potted_plant[0].rotation = [0, 0, radians(220)]

# The asset is treated as a low media stand, following its variable name.
# Its long dimension runs parallel to the west wall and it faces into the room.
tv_stand[0].position = [0.20, 4.65, 0.25]
tv_stand[0].rotation = [0, 0, radians(0)]

dining_chair_D[0].position = [2.05, 0.85, 0.395]
dining_chair_D[0].rotation = [0, 0, radians(180)]

three_seat_sofa[0].position = [2.35, 4.65, 0.42]
three_seat_sofa[0].rotation = [0, 0, radians(180)]

dining_table_A[0].position = [1.20, 0.85, 0.375]
dining_table_A[0].rotation = [0, 0, radians(0)]

dining_table_B[0].position = [1.20, 2.75, 0.375]
dining_table_B[0].rotation = [0, 0, radians(0)]

# The pillow is centered on the sofa. on_top_of below determines its supported
# height; this initial height corresponds to the top of the sofa bounding box.
pillow[0].position = [2.35, 4.65, 0.915]
pillow[0].rotation = [0, 0, radians(180)]


# Fixed layout targets preserve the two functional zones while allowing the
# solver to make small adjustments if needed.
floor_lamp_target = AssetInstance(position=[3.22, 4.65, 0.775])
chair_A_target = AssetInstance(position=[1.20, 1.80, 0.395])
chair_B_target = AssetInstance(position=[0.35, 0.85, 0.395])
chair_C_target = AssetInstance(position=[0.35, 2.75, 0.395])
plant_target = AssetInstance(position=[3.48, 5.58, 0.45])
tv_stand_target = AssetInstance(position=[0.20, 4.65, 0.25])
chair_D_target = AssetInstance(position=[2.05, 0.85, 0.395])
sofa_target = AssetInstance(position=[2.35, 4.65, 0.42])
table_A_target = AssetInstance(position=[1.20, 0.85, 0.375])
table_B_target = AssetInstance(position=[1.20, 2.75, 0.375])
pillow_target = AssetInstance(position=[2.35, 4.65, 0.915])

# Important position constraints are specified first.
solver.distance_constraint(
    floor_lamp[0], floor_lamp_target, 0, 0.10, weight=10
)
solver.distance_constraint(
    dining_chair_A[0], chair_A_target, 0, 0.10, weight=10
)
solver.distance_constraint(
    dining_chair_B[0], chair_B_target, 0, 0.10, weight=10
)
solver.distance_constraint(
    dining_chair_C[0], chair_C_target, 0, 0.10, weight=10
)
solver.distance_constraint(
    potted_plant[0], plant_target, 0, 0.10, weight=10
)
solver.distance_constraint(
    tv_stand[0], tv_stand_target, 0, 0.08, weight=10
)
solver.distance_constraint(
    dining_chair_D[0], chair_D_target, 0, 0.10, weight=10
)
solver.distance_constraint(
    three_seat_sofa[0], sofa_target, 0, 0.10, weight=10
)
solver.distance_constraint(
    dining_table_A[0], table_A_target, 0, 0.08, weight=10
)
solver.distance_constraint(
    dining_table_B[0], table_B_target, 0, 0.08, weight=10
)
solver.distance_constraint(
    pillow[0], pillow_target, 0, 0.08, weight=10
)

# Keep the media stand flush against the west wall.
solver.against_wall(tv_stand[0], walls[2])

# Dining chair A is centered between the two tables. Equal distance constraints
# preserve that relationship if either table is adjusted.
solver.distance_constraint(
    dining_chair_A[0], dining_table_A[0], 0.90, 1.00, weight=10
)
solver.distance_constraint(
    dining_chair_A[0], dining_table_B[0], 0.90, 1.00, weight=10
)

# The other chairs remain at usable seating distances from their tables.
solver.distance_constraint(
    dining_chair_B[0], dining_table_A[0], 0.80, 0.90, weight=5
)
solver.distance_constraint(
    dining_chair_C[0], dining_table_B[0], 0.80, 0.90, weight=10
)
solver.distance_constraint(
    dining_chair_D[0], dining_table_A[0], 0.80, 0.90, weight=5
)

# The pillow must remain supported by the sofa.
solver.on_top_of(pillow[0], three_seat_sofa[0])

# Orientation constraints for every new asset.
solver.point_towards(floor_lamp[0], three_seat_sofa[0])
solver.point_towards(dining_chair_A[0], dining_table_B[0])
solver.point_towards(dining_chair_B[0], dining_table_A[0])

# Required semantic constraint: dining chair o0003 faces dining table o0010.
solver.point_towards(dining_chair_C[0], dining_table_B[0])

solver.point_towards(dining_chair_D[0], dining_table_A[0])
solver.point_towards(potted_plant[0], three_seat_sofa[0])
solver.point_towards(tv_stand[0], three_seat_sofa[0])
solver.point_towards(three_seat_sofa[0], tv_stand[0])
solver.align_with(pillow[0], three_seat_sofa[0])

# The round tables are rotationally symmetric, but explicit orientation
# constraints are included so every placed instance has one.
solver.align_with(dining_table_A[0], tv_stand[0])
solver.align_with(dining_table_B[0], dining_table_A[0])

solver.constraints = []
pillow[0].position = [2.3499999046325684, 4.650000095367432, 0.9149999618530273]
pillow[0].rotation = [0, 0, -3.1164604485258507]
pillow[0].optimize = 2
three_seat_sofa[0].position = [2.3499999046325684, 4.650000095367432, 0.41999998688697815]
three_seat_sofa[0].rotation = [0, 0, -3.1164599134799373]
three_seat_sofa[0].optimize = 2
tv_stand[0].position = [0.20000101625919342, 4.650000095367432, 0.25]
tv_stand[0].rotation = [0, 0, -4.910933123199694e-07]
tv_stand[0].optimize = 2
floor_lamp[0].position = [3.2200000286102295, 4.650000095367432, 0.7749999761581421]
floor_lamp[0].rotation = [0, 0, -3.1321678761290697]
floor_lamp[0].optimize = 2
dining_table_A[0].position = [1.2000000476837158, 0.8500000238418579, 0.375]
dining_table_A[0].rotation = [0, 0, -9.632031847680815e-07]
dining_table_A[0].optimize = 2
dining_chair_D[0].position = [2.049999952316284, 0.8500000238418579, 0.39500001072883606]
dining_chair_D[0].rotation = [0, 0, -3.1290262823329655]
dining_chair_D[0].optimize = 2
dining_chair_C[0].position = [0.3499999940395355, 2.75, 0.39500001072883606]
dining_chair_C[0].rotation = [0, 0, 0.01256637125682779]
dining_chair_C[0].optimize = 2
dining_chair_B[0].position = [0.3499999940395355, 0.8500000238418579, 0.39500001072883606]
dining_chair_B[0].rotation = [0, 0, 0.01256637125682779]
dining_chair_B[0].optimize = 2
dining_table_B[0].position = [1.2000000476837158, 2.75, 0.375]
dining_table_B[0].rotation = [0, 0, 3.3886673490981668e-06]
dining_table_B[0].optimize = 2
dining_chair_A[0].position = [1.2000000476837158, 1.7999999523162842, 0.39500001072883606]
dining_chair_A[0].rotation = [0, 0, 1.586504290712113]
dining_chair_A[0].optimize = 2
potted_plant[0].position = [3.4800000190734863, 5.579999923706055, 0.44999998807907104]
potted_plant[0].rotation = [0, 0, -2.4340361633573475]
potted_plant[0].optimize = 2

