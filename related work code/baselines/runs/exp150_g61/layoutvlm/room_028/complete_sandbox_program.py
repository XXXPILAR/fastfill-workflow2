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
floor_lamp = Assets(description="A modern floor lamp with a cylindrical brown shade and three metallic legs.", size=[0.55, 0.55, 1.60], placements=[AssetInstance() for _ in range(1)])
dining_chair_A = Assets(description="A modern wooden dining chair with a sleek design, featuring a rounded backrest and seat connected by curved wooden supports. The legs are angled outward for stability.", size=[0.54, 0.52, 0.78], placements=[AssetInstance() for _ in range(1)])
dining_chair_B = Assets(description="A modern wooden dining chair with a sleek design, featuring a rounded backrest and seat connected by curved wooden supports. The legs are angled outward for stability.", size=[0.54, 0.52, 0.78], placements=[AssetInstance() for _ in range(1)])
dining_chair_C = Assets(description="A modern wooden dining chair with a sleek design, featuring a rounded backrest and seat connected by curved wooden supports. The legs are angled outward for stability.", size=[0.54, 0.52, 0.78], placements=[AssetInstance() for _ in range(1)])
potted_plant = Assets(description="A potted plant with dark green leaves and a glossy black pot, placed on a reflective black surface.", size=[0.45, 0.45, 0.90], placements=[AssetInstance() for _ in range(1)])
tv_stand = Assets(description="A modern, geometric ceiling light fixture with a wooden exterior and a reflective interior surface.", size=[0.40, 1.40, 0.50], placements=[AssetInstance() for _ in range(1)])
pillow = Assets(description="A square-shaped pillow with a slightly textured surface, resting on a glossy black platform.", size=[0.45, 0.45, 0.15], placements=[AssetInstance() for _ in range(1)])
dining_chair_D = Assets(description="A modern wooden dining chair with a sleek design, featuring a rounded backrest and seat connected by curved wooden supports. The legs are angled outward for stability.", size=[0.54, 0.52, 0.78], placements=[AssetInstance() for _ in range(1)])
three_seat_sofa = Assets(description="A modern, light-colored sofa with three cushioned seats and backrests. It features decorative throw pillows in various colors and patterns, adding a stylish touch. The sofa has a sleek design with clean lines and a sturdy frame.", size=[0.90, 2.20, 0.82], placements=[AssetInstance() for _ in range(1)])
dining_table_A = Assets(description="A modern dining table with a round wooden top and a black cylindrical base.", size=[0.90, 0.90, 0.75], placements=[AssetInstance() for _ in range(1)])
dining_table_B = Assets(description="A modern dining table with a round wooden top and a black cylindrical base.", size=[0.90, 0.90, 0.75], placements=[AssetInstance() for _ in range(1)])

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

floor_lamp[0].position = [1.3375383667389316, 0.4182418270930664, 0.8]
floor_lamp[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [3.814201782564604, 2.086246119841432, 0.39]
dining_chair_A[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [1.5676082664432416, 3.5469942814304978, 0.39]
dining_chair_B[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [0.6856640215817135, 2.7715632699946977, 0.39]
dining_chair_C[0].rotation = [0, 0, 0]
potted_plant[0].position = [2.984737336365932, 5.299744198829743, 0.45]
potted_plant[0].rotation = [0, 0, 0]
tv_stand[0].position = [1.734695317250389, 0.3185494825456429, 0.25]
tv_stand[0].rotation = [0, 0, 0]
pillow[0].position = [2.8124353350416413, 1.3447626497173242, 0.075]
pillow[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [1.2081885812729916, 4.74479258999016, 0.39]
dining_chair_D[0].rotation = [0, 0, 0]
three_seat_sofa[0].position = [1.3790337732197422, 2.56573761544259, 0.41]
three_seat_sofa[0].rotation = [0, 0, 0]
dining_table_A[0].position = [1.6357424901164705, 1.4478325618768166, 0.375]
dining_table_A[0].rotation = [0, 0, 0]
dining_table_B[0].position = [3.4296845053724048, 0.8608504358393789, 0.375]
dining_table_B[0].rotation = [0, 0, 0]
floor_lamp[0].position = [1.3375383667389316, 0.4182418270930664, 0.8]
floor_lamp[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [3.814201782564604, 2.086246119841432, 0.39]
dining_chair_A[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [1.5676082664432416, 3.5469942814304978, 0.39]
dining_chair_B[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [0.6856640215817135, 2.7715632699946977, 0.39]
dining_chair_C[0].rotation = [0, 0, 0]
potted_plant[0].position = [2.984737336365932, 5.299744198829743, 0.45]
potted_plant[0].rotation = [0, 0, 0]
tv_stand[0].position = [1.734695317250389, 0.3185494825456429, 0.25]
tv_stand[0].rotation = [0, 0, 0]
pillow[0].position = [2.8124353350416413, 1.3447626497173242, 0.075]
pillow[0].rotation = [0, 0, 0]
dining_chair_D[0].position = [1.2081885812729916, 4.74479258999016, 0.39]
dining_chair_D[0].rotation = [0, 0, 0]
three_seat_sofa[0].position = [1.3790337732197422, 2.56573761544259, 0.41]
three_seat_sofa[0].rotation = [0, 0, 0]
dining_table_A[0].position = [1.6357424901164705, 1.4478325618768166, 0.375]
dining_table_A[0].rotation = [0, 0, 0]
dining_table_B[0].position = [3.4296845053724048, 0.8608504358393789, 0.375]
dining_table_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the supplied wall coordinates: the room occupies x=0..3.84, y=0..5.87.
# Keep the eastern entry/circulation strip clear, especially beside both doors.
# The lower half is a lounge; the upper half contains two small dining tables.
# o0001 corresponds to dining_chair_A, and o0003 to dining_chair_C.

layout_specs = [
    (three_seat_sofa, [0.45, 1.50, 0.41], 0),
    (floor_lamp,      [0.35, 2.98, 0.80], 0),
    (potted_plant,    [3.35, 5.50, 0.45], 180),

    (dining_table_A,  [1.65, 3.55, 0.375], 0),
    (dining_table_B,  [1.65, 5.15, 0.375], 0),

    # Chair A sits in the gap between the two tables, facing the northern one.
    (dining_chair_A,  [1.65, 4.35, 0.39], 90),
    (dining_chair_B,  [0.80, 3.55, 0.39], 0),
    (dining_chair_C,  [2.50, 5.15, 0.39], 180),
    (dining_chair_D,  [0.80, 5.15, 0.39], 0),

    # Despite its variable name, this asset is described as a ceiling light.
    # Suspend it over the lounge, with its bottom at 2.20 m.
    (tv_stand,       [1.85, 1.50, 2.45], 0),

    # Initial height puts the cushion on the sofa's upper bounding surface.
    (pillow,         [0.45, 1.80, 0.895], 0),
]

for asset_ref, initial_position, yaw_degrees in layout_specs:
    asset_ref[0].position = list(initial_position)
    asset_ref[0].rotation = [0, 0, radians(yaw_degrees)]

# Prioritize support for the small cushion rather than fixing it in midair.
solver.on_top_of(pillow[0], three_seat_sofa[0])

# Fixed location constraints preserve the clear door approaches and ensure the
# dining chair remains between the tables. Each anchor includes the intended
# bounding-box-center height, including the suspended light's elevation.
for asset_ref, initial_position, yaw_degrees in layout_specs:
    if asset_ref is not pillow:
        solver.distance_constraint(
            asset_ref[0],
            AssetInstance(position=list(initial_position)),
            0, 0,
            weight=10,
        )

# Orient chairs toward their respective tables. In particular, chair C faces B.
solver.point_towards(dining_chair_A[0], dining_table_B[0])
solver.point_towards(dining_chair_B[0], dining_table_A[0])
solver.point_towards(dining_chair_C[0], dining_table_B[0])
solver.point_towards(dining_chair_D[0], dining_table_B[0])

# Define orientations for every other asset, including rotationally symmetric
# objects, without changing the existing asset variables.
for asset_ref, initial_position, yaw_degrees in layout_specs:
    if not any(
        asset_ref is chair_ref
        for chair_ref in (
            dining_chair_A, dining_chair_B, dining_chair_C, dining_chair_D
        )
    ):
        solver.align_with(
            asset_ref[0],
            AssetInstance(rotation=[0, 0, radians(yaw_degrees)]),
            angle=0,
        )

# Preserve the sofa's west-wall placement and the seating area's inward facing.
solver.against_wall(three_seat_sofa[0], walls[2])

# The cushion stays near its intended spot on the sofa while support determines
# its final height. This supplies its required position-based constraint.
solver.distance_constraint(
    pillow[0],
    AssetInstance(position=[0.45, 1.80, 0.895]),
    0, 0.12,
    weight=10,
)

# Reinforce useful dining clearances using actual 3-D center distances.
# These supplement the higher-priority anchors rather than moving either table.
for chair_ref, table_ref in (
    (dining_chair_A, dining_table_A),
    (dining_chair_A, dining_table_B),
    (dining_chair_B, dining_table_A),
    (dining_chair_C, dining_table_B),
    (dining_chair_D, dining_table_B),
):
    center_spacing = sum(
        (chair_ref[0].position[axis] - table_ref[0].position[axis]) ** 2
        for axis in range(3)
    ) ** 0.5
    solver.distance_constraint(
        chair_ref[0], table_ref[0],
        center_spacing - 0.02,
        center_spacing + 0.02,
    )

solver.constraints = []
dining_table_A[0].position = [1.649999976158142, 3.549999952316284, 0.375]
dining_table_A[0].rotation = [0, 0, 0.01884955539881635]
dining_table_A[0].optimize = 2
dining_chair_A[0].position = [1.649999976158142, 4.349999904632568, 0.38999998569488525]
dining_chair_A[0].rotation = [0, 0, 1.586504290712113]
dining_chair_A[0].optimize = 2
dining_chair_D[0].position = [0.800000011920929, 5.150000095367432, 0.38999998569488525]
dining_chair_D[0].rotation = [0, 0, 0.01256637125682779]
dining_chair_D[0].optimize = 2
dining_table_B[0].position = [1.649999976158142, 5.150000095367432, 0.375]
dining_table_B[0].rotation = [0, 0, 0.02827433441159227]
dining_table_B[0].optimize = 2
dining_chair_C[0].position = [2.5, 5.150000095367432, 0.38999998569488525]
dining_chair_C[0].rotation = [0, 0, -3.1290262823329655]
dining_chair_C[0].optimize = 2
three_seat_sofa[0].position = [0.45003828406333923, 1.5, 0.4099999964237213]
three_seat_sofa[0].rotation = [0, 0, -3.5319680792759676e-05]
three_seat_sofa[0].optimize = 2
floor_lamp[0].position = [0.3499999940395355, 2.9800000190734863, 0.800000011920929]
floor_lamp[0].rotation = [0, 0, 0.00942477746072377]
floor_lamp[0].optimize = 2
dining_chair_B[0].position = [0.800000011920929, 3.549999952316284, 0.38999998569488525]
dining_chair_B[0].rotation = [0, 0, 0.01256637125682779]
dining_chair_B[0].optimize = 2
tv_stand[0].position = [1.850000023841858, 1.5, 0.25]
tv_stand[0].rotation = [0, 0, 0.00942477746072377]
tv_stand[0].optimize = 2
pillow[0].position = [0.44999998807907104, 1.7999999523162842, 0.8949999809265137]
pillow[0].rotation = [0, 0, 0.01256637125682779]
pillow[0].optimize = 2
potted_plant[0].position = [3.3499999046325684, 5.5, 0.44999998807907104]
potted_plant[0].rotation = [0, 0, -3.1321678761290697]
potted_plant[0].optimize = 2

