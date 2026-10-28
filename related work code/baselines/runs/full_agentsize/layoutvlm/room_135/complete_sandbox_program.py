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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.00, 0.00, 0.00]),
    Wall(corner1=[4.00, 0.00, 0.00], corner2=[4.00, 1.00, 0.00]),
    Wall(corner1=[4.00, 1.00, 0.00], corner2=[6.00, 1.00, 0.00]),
    Wall(corner1=[6.00, 1.00, 0.00], corner2=[6.00, 5.00, 0.00]),
    Wall(corner1=[6.00, 5.00, 0.00], corner2=[0.00, 5.00, 0.00]),
    Wall(corner1=[0.00, 5.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
vase_A = Assets(description="vase", size=[0.18, 0.18, 0.35], placements=[AssetInstance() for _ in range(1)])
bench_seat_A = Assets(description="bench seat", size=[0.45, 1.50, 0.46], placements=[AssetInstance() for _ in range(1)])
console_table = Assets(description="console table", size=[0.40, 1.40, 0.80], placements=[AssetInstance() for _ in range(1)])
serving_trolley = Assets(description="serving trolley", size=[0.45, 0.80, 0.85], placements=[AssetInstance() for _ in range(1)])
wall_clock = Assets(description="A black wall clock.", size=[0.06, 0.40, 0.40], placements=[AssetInstance() for _ in range(1)])
dining_table = Assets(description="dining table", size=[1.00, 2.00, 0.76], placements=[AssetInstance() for _ in range(1)])
table_lamp = Assets(description="table lamp", size=[0.30, 0.30, 0.55], placements=[AssetInstance() for _ in range(1)])
bench_seat_B = Assets(description="bench seat", size=[0.45, 1.50, 0.46], placements=[AssetInstance() for _ in range(1)])
dining_chair_A = Assets(description="dining chair", size=[0.55, 0.50, 0.90], placements=[AssetInstance() for _ in range(1)])
stack_of_plates_A = Assets(description="stack of plates", size=[0.28, 0.28, 0.12], placements=[AssetInstance() for _ in range(1)])
dining_chair_B = Assets(description="dining chair", size=[0.55, 0.50, 0.90], placements=[AssetInstance() for _ in range(1)])
buffet_sideboard = Assets(description="buffet sideboard", size=[0.50, 1.80, 0.85], placements=[AssetInstance() for _ in range(1)])
storage_cabinet = Assets(description="storage cabinet", size=[0.45, 1.00, 1.80], placements=[AssetInstance() for _ in range(1)])
stack_of_plates_B = Assets(description="stack of plates", size=[0.28, 0.28, 0.12], placements=[AssetInstance() for _ in range(1)])
display_shelf_A = Assets(description="display shelf", size=[0.35, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
wall_art_small_A = Assets(description="wooden model of a frog and bird on a plaque, mounted on a white wall.", size=[0.06, 0.30, 0.40], placements=[AssetInstance() for _ in range(1)])
picture_frame = Assets(description="picture frame", size=[0.12, 0.25, 0.30], placements=[AssetInstance() for _ in range(1)])
wall_art_small_B = Assets(description="wooden model of a frog and bird on a plaque, mounted on a white wall.", size=[0.06, 0.30, 0.40], placements=[AssetInstance() for _ in range(1)])
decorative_jar = Assets(description="decorative jar", size=[0.25, 0.25, 0.40], placements=[AssetInstance() for _ in range(1)])
wall_art_small_C = Assets(description="wooden model of a frog and bird on a plaque, mounted on a white wall.", size=[0.06, 0.30, 0.40], placements=[AssetInstance() for _ in range(1)])
dining_chair_C = Assets(description="dining chair", size=[0.55, 0.50, 0.90], placements=[AssetInstance() for _ in range(1)])
display_shelf_B = Assets(description="display shelf", size=[0.35, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
wall_art_small_D = Assets(description="wooden model of a frog and bird on a plaque, mounted on a white wall.", size=[0.06, 0.30, 0.40], placements=[AssetInstance() for _ in range(1)])
vase_B = Assets(description="vase", size=[0.18, 0.18, 0.35], placements=[AssetInstance() for _ in range(1)])

vase_A[0].instance_id = 'vase_A_0'
bench_seat_A[0].instance_id = 'bench_seat_A_0'
console_table[0].instance_id = 'console_table_0'
serving_trolley[0].instance_id = 'serving_trolley_0'
wall_clock[0].instance_id = 'wall_clock_0'
dining_table[0].instance_id = 'dining_table_0'
table_lamp[0].instance_id = 'table_lamp_0'
bench_seat_B[0].instance_id = 'bench_seat_B_0'
dining_chair_A[0].instance_id = 'dining_chair_A_0'
stack_of_plates_A[0].instance_id = 'stack_of_plates_A_0'
dining_chair_B[0].instance_id = 'dining_chair_B_0'
buffet_sideboard[0].instance_id = 'buffet_sideboard_0'
storage_cabinet[0].instance_id = 'storage_cabinet_0'
stack_of_plates_B[0].instance_id = 'stack_of_plates_B_0'
display_shelf_A[0].instance_id = 'display_shelf_A_0'
wall_art_small_A[0].instance_id = 'wall_art_small_A_0'
picture_frame[0].instance_id = 'picture_frame_0'
wall_art_small_B[0].instance_id = 'wall_art_small_B_0'
decorative_jar[0].instance_id = 'decorative_jar_0'
wall_art_small_C[0].instance_id = 'wall_art_small_C_0'
dining_chair_C[0].instance_id = 'dining_chair_C_0'
display_shelf_B[0].instance_id = 'display_shelf_B_0'
wall_art_small_D[0].instance_id = 'wall_art_small_D_0'
vase_B[0].instance_id = 'vase_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

vase_A[0].position = [2.6312928420569035, 0.6049303493887442, 0.175]
vase_A[0].rotation = [0, 0, 0]
bench_seat_A[0].position = [2.0981441595873314, 2.6774765549661117, 0.23]
bench_seat_A[0].rotation = [0, 0, 0]
console_table[0].position = [3.566769821405119, 1.539120554474041, 0.4]
console_table[0].rotation = [0, 0, 0]
serving_trolley[0].position = [5.294556185644654, 1.853956879755883, 0.425]
serving_trolley[0].rotation = [0, 0, 0]
wall_clock[0].position = [1.1870486525272888, 4.325857025779003, 0.2]
wall_clock[0].rotation = [0, 0, 0]
dining_table[0].position = [0.45698488572507534, 4.957195203352262, 0.38]
dining_table[0].rotation = [0, 0, 0]
table_lamp[0].position = [1.652226774334965, 4.36928651444219, 0.275]
table_lamp[0].rotation = [0, 0, 0]
bench_seat_B[0].position = [3.9745656200773096, 2.232955189839845, 0.23]
bench_seat_B[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [4.318958289106899, 1.700473892072016, 0.45]
dining_chair_A[0].rotation = [0, 0, 0]
stack_of_plates_A[0].position = [0.09359796700315681, 4.406155940817115, 0.06]
stack_of_plates_A[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [3.5211580468593997, 2.448385647596956, 0.45]
dining_chair_B[0].rotation = [0, 0, 0]
buffet_sideboard[0].position = [3.706116293652828, 3.9619006583387053, 0.425]
buffet_sideboard[0].rotation = [0, 0, 0]
storage_cabinet[0].position = [0.3825855696642635, 0.7331145578391113, 0.9]
storage_cabinet[0].rotation = [0, 0, 0]
stack_of_plates_B[0].position = [1.6376998030712482, 2.556777124510968, 0.06]
stack_of_plates_B[0].rotation = [0, 0, 0]
display_shelf_A[0].position = [2.6882801893715973, 4.816924769685839, 0.9]
display_shelf_A[0].rotation = [0, 0, 0]
wall_art_small_A[0].position = [5.9964118187444555, 3.9063757816779816, 0.2]
wall_art_small_A[0].rotation = [0, 0, 0]
picture_frame[0].position = [1.267121785645851, 1.0465201252299843, 0.15]
picture_frame[0].rotation = [0, 0, 0]
wall_art_small_B[0].position = [3.616970593226231, 4.189920601036011, 0.2]
wall_art_small_B[0].rotation = [0, 0, 0]
decorative_jar[0].position = [5.739235236554619, 1.4030312352749825, 0.2]
decorative_jar[0].rotation = [0, 0, 0]
wall_art_small_C[0].position = [2.7739346600302888, 3.6836135569359736, 0.2]
wall_art_small_C[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [4.478229430942919, 1.701845895015106, 0.45]
dining_chair_C[0].rotation = [0, 0, 0]
display_shelf_B[0].position = [1.821222933691653, 4.728560715847147, 0.9]
display_shelf_B[0].rotation = [0, 0, 0]
wall_art_small_D[0].position = [0.6234005575679731, 4.696018612056551, 0.2]
wall_art_small_D[0].rotation = [0, 0, 0]
vase_B[0].position = [0.9448588907094781, 4.280009110427504, 0.175]
vase_B[0].rotation = [0, 0, 0]
vase_A[0].position = [2.6312928420569035, 0.6049303493887442, 0.175]
vase_A[0].rotation = [0, 0, 0]
bench_seat_A[0].position = [2.0981441595873314, 2.6774765549661117, 0.23]
bench_seat_A[0].rotation = [0, 0, 0]
console_table[0].position = [3.566769821405119, 1.539120554474041, 0.4]
console_table[0].rotation = [0, 0, 0]
serving_trolley[0].position = [5.294556185644654, 1.853956879755883, 0.425]
serving_trolley[0].rotation = [0, 0, 0]
wall_clock[0].position = [1.1870486525272888, 4.325857025779003, 0.2]
wall_clock[0].rotation = [0, 0, 0]
dining_table[0].position = [0.45698488572507534, 4.957195203352262, 0.38]
dining_table[0].rotation = [0, 0, 0]
table_lamp[0].position = [1.652226774334965, 4.36928651444219, 0.275]
table_lamp[0].rotation = [0, 0, 0]
bench_seat_B[0].position = [3.9745656200773096, 2.232955189839845, 0.23]
bench_seat_B[0].rotation = [0, 0, 0]
dining_chair_A[0].position = [4.318958289106899, 1.700473892072016, 0.45]
dining_chair_A[0].rotation = [0, 0, 0]
stack_of_plates_A[0].position = [0.09359796700315681, 4.406155940817115, 0.06]
stack_of_plates_A[0].rotation = [0, 0, 0]
dining_chair_B[0].position = [3.5211580468593997, 2.448385647596956, 0.45]
dining_chair_B[0].rotation = [0, 0, 0]
buffet_sideboard[0].position = [3.706116293652828, 3.9619006583387053, 0.425]
buffet_sideboard[0].rotation = [0, 0, 0]
storage_cabinet[0].position = [0.3825855696642635, 0.7331145578391113, 0.9]
storage_cabinet[0].rotation = [0, 0, 0]
stack_of_plates_B[0].position = [1.6376998030712482, 2.556777124510968, 0.06]
stack_of_plates_B[0].rotation = [0, 0, 0]
display_shelf_A[0].position = [2.6882801893715973, 4.816924769685839, 0.9]
display_shelf_A[0].rotation = [0, 0, 0]
wall_art_small_A[0].position = [5.9964118187444555, 3.9063757816779816, 0.2]
wall_art_small_A[0].rotation = [0, 0, 0]
picture_frame[0].position = [1.267121785645851, 1.0465201252299843, 0.15]
picture_frame[0].rotation = [0, 0, 0]
wall_art_small_B[0].position = [3.616970593226231, 4.189920601036011, 0.2]
wall_art_small_B[0].rotation = [0, 0, 0]
decorative_jar[0].position = [5.739235236554619, 1.4030312352749825, 0.2]
decorative_jar[0].rotation = [0, 0, 0]
wall_art_small_C[0].position = [2.7739346600302888, 3.6836135569359736, 0.2]
wall_art_small_C[0].rotation = [0, 0, 0]
dining_chair_C[0].position = [4.478229430942919, 1.701845895015106, 0.45]
dining_chair_C[0].rotation = [0, 0, 0]
display_shelf_B[0].position = [1.821222933691653, 4.728560715847147, 0.9]
display_shelf_B[0].rotation = [0, 0, 0]
wall_art_small_D[0].position = [0.6234005575679731, 4.696018612056551, 0.2]
wall_art_small_D[0].rotation = [0, 0, 0]
vase_B[0].position = [0.9448588907094781, 4.280009110427504, 0.175]
vase_B[0].rotation = [0, 0, 0]

solver.constraints = []

# The dining group occupies the open center of the main 6 m x 4 m area.
# The two benches flank the long sides of the table. dining_chair_A is at
# the south end, centered between the two benches as requested.
dining_table[0].position = [3.20, 2.80, 0.38]
dining_table[0].rotation = [0, 0, 0]

bench_seat_A[0].position = [2.15, 2.80, 0.23]
bench_seat_A[0].rotation = [0, 0, 0]

bench_seat_B[0].position = [4.25, 2.80, 0.23]
bench_seat_B[0].rotation = [0, 0, radians(180)]

dining_chair_A[0].position = [3.20, 1.42, 0.45]
dining_chair_A[0].rotation = [0, 0, radians(90)]

dining_chair_B[0].position = [2.90, 4.18, 0.45]
dining_chair_B[0].rotation = [0, 0, radians(-90)]

dining_chair_C[0].position = [3.55, 4.18, 0.45]
dining_chair_C[0].rotation = [0, 0, radians(-90)]

# Tall storage is distributed around the perimeter, leaving the windowed
# y=0 wall unobstructed and preserving circulation around the dining group.
storage_cabinet[0].position = [0.225, 1.60, 0.90]
storage_cabinet[0].rotation = [0, 0, 0]

buffet_sideboard[0].position = [0.25, 3.35, 0.425]
buffet_sideboard[0].rotation = [0, 0, 0]

display_shelf_A[0].position = [5.825, 1.70, 0.90]
display_shelf_A[0].rotation = [0, 0, radians(180)]

display_shelf_B[0].position = [4.50, 4.825, 0.90]
display_shelf_B[0].rotation = [0, 0, radians(-90)]

console_table[0].position = [3.00, 4.80, 0.40]
console_table[0].rotation = [0, 0, radians(-90)]

serving_trolley[0].position = [5.775, 4.25, 0.425]
serving_trolley[0].rotation = [0, 0, radians(180)]

# Tabletop objects are given explicit non-overlapping positions and are also
# constrained to remain on their supporting surfaces.
stack_of_plates_A[0].position = [3.20, 2.35, 0.82]
stack_of_plates_A[0].rotation = [0, 0, 0]

stack_of_plates_B[0].position = [3.20, 3.25, 0.82]
stack_of_plates_B[0].rotation = [0, 0, 0]

vase_A[0].position = [2.58, 4.80, 0.975]
vase_A[0].rotation = [0, 0, radians(-90)]

table_lamp[0].position = [3.00, 4.80, 1.075]
table_lamp[0].rotation = [0, 0, radians(-90)]

vase_B[0].position = [3.42, 4.80, 0.975]
vase_B[0].rotation = [0, 0, radians(-90)]

# The requested picture frame is placed on the buffet sideboard. The jar
# shares the sideboard while remaining separated along its long dimension.
picture_frame[0].position = [0.25, 3.20, 1.00]
picture_frame[0].rotation = [0, 0, 0]

decorative_jar[0].position = [0.25, 3.80, 1.05]
decorative_jar[0].rotation = [0, 0, 0]

# The four small plaques are mounted above the low buffet on the left wall.
# Their centers are separated by more than their 0.30 m widths.
wall_art_small_A[0].position = [0.03, 2.65, 1.45]
wall_art_small_A[0].rotation = [0, 0, 0]

wall_art_small_B[0].position = [0.03, 3.10, 1.45]
wall_art_small_B[0].rotation = [0, 0, 0]

wall_art_small_C[0].position = [0.03, 3.55, 1.45]
wall_art_small_C[0].rotation = [0, 0, 0]

wall_art_small_D[0].position = [0.03, 4.00, 1.45]
wall_art_small_D[0].rotation = [0, 0, 0]

# The clock is mounted on the upper wall, above the serving area.
wall_clock[0].position = [5.40, 4.97, 1.50]
wall_clock[0].rotation = [0, 0, radians(-90)]


# Fixed anchors preserve the intended zones while allowing the solver to
# reconcile small physical-feasibility adjustments.
dining_table_anchor = AssetInstance(position=[3.20, 2.80, 0.38])
bench_A_anchor = AssetInstance(position=[2.15, 2.80, 0.23])
bench_B_anchor = AssetInstance(position=[4.25, 2.80, 0.23])
chair_A_anchor = AssetInstance(position=[3.20, 1.42, 0.45])
chair_B_anchor = AssetInstance(position=[2.90, 4.18, 0.45])
chair_C_anchor = AssetInstance(position=[3.55, 4.18, 0.45])

storage_anchor = AssetInstance(position=[0.225, 1.60, 0.90])
buffet_anchor = AssetInstance(position=[0.25, 3.35, 0.425])
shelf_A_anchor = AssetInstance(position=[5.825, 1.70, 0.90])
shelf_B_anchor = AssetInstance(position=[4.50, 4.825, 0.90])
console_anchor = AssetInstance(position=[3.00, 4.80, 0.40])
trolley_anchor = AssetInstance(position=[5.775, 4.25, 0.425])

plates_A_anchor = AssetInstance(position=[3.20, 2.35, 0.82])
plates_B_anchor = AssetInstance(position=[3.20, 3.25, 0.82])
vase_A_anchor = AssetInstance(position=[2.58, 4.80, 0.975])
lamp_anchor = AssetInstance(position=[3.00, 4.80, 1.075])
vase_B_anchor = AssetInstance(position=[3.42, 4.80, 0.975])
frame_anchor = AssetInstance(position=[0.25, 3.20, 1.00])
jar_anchor = AssetInstance(position=[0.25, 3.80, 1.05])

art_A_anchor = AssetInstance(position=[0.03, 2.65, 1.45])
art_B_anchor = AssetInstance(position=[0.03, 3.10, 1.45])
art_C_anchor = AssetInstance(position=[0.03, 3.55, 1.45])
art_D_anchor = AssetInstance(position=[0.03, 4.00, 1.45])
clock_anchor = AssetInstance(position=[5.40, 4.97, 1.50])


# Important position constraints for the central dining arrangement.
solver.distance_constraint(dining_table[0], dining_table_anchor, 0, 0, weight=10)
solver.distance_constraint(bench_seat_A[0], bench_A_anchor, 0, 0, weight=10)
solver.distance_constraint(bench_seat_B[0], bench_B_anchor, 0, 0, weight=10)
solver.distance_constraint(dining_chair_A[0], chair_A_anchor, 0, 0, weight=10)
solver.distance_constraint(dining_chair_B[0], chair_B_anchor, 0, 0, weight=10)
solver.distance_constraint(dining_chair_C[0], chair_C_anchor, 0, 0, weight=10)

# Equal-distance relationships reinforce dining_chair_A's placement between
# the two benches while its anchor keeps it clear of the table.
solver.distance_constraint(
    dining_chair_A[0], bench_seat_A[0], 1.58, 1.62, weight=10
)
solver.distance_constraint(
    dining_chair_A[0], bench_seat_B[0], 1.58, 1.62, weight=10
)

# All dining seats face the dining table.
solver.point_towards(bench_seat_A[0], dining_table[0])
solver.point_towards(bench_seat_B[0], dining_table[0])
solver.point_towards(dining_chair_A[0], dining_table[0])
solver.point_towards(dining_chair_B[0], dining_table[0])
solver.point_towards(dining_chair_C[0], dining_table[0])
solver.align_with(dining_table[0], dining_table_anchor)


# Perimeter furniture is anchored and constrained against its corresponding
# wall. Orientation constraints make each item face into the room.
solver.distance_constraint(storage_cabinet[0], storage_anchor, 0, 0, weight=10)
solver.against_wall(storage_cabinet[0], walls[5])
solver.point_towards(storage_cabinet[0], dining_table[0])

solver.distance_constraint(buffet_sideboard[0], buffet_anchor, 0, 0, weight=10)
solver.against_wall(buffet_sideboard[0], walls[5])
solver.point_towards(buffet_sideboard[0], dining_table[0])

solver.distance_constraint(display_shelf_A[0], shelf_A_anchor, 0, 0, weight=10)
solver.against_wall(display_shelf_A[0], walls[3])
solver.point_towards(display_shelf_A[0], dining_table[0])

solver.distance_constraint(display_shelf_B[0], shelf_B_anchor, 0, 0, weight=10)
solver.against_wall(display_shelf_B[0], walls[4])
solver.point_towards(display_shelf_B[0], dining_table[0])

solver.distance_constraint(console_table[0], console_anchor, 0, 0, weight=10)
solver.against_wall(console_table[0], walls[4])
solver.point_towards(console_table[0], dining_table[0])

solver.distance_constraint(serving_trolley[0], trolley_anchor, 0, 0, weight=10)
solver.against_wall(serving_trolley[0], walls[3])
solver.point_towards(serving_trolley[0], dining_table[0])


# Dining-table place settings: each has a position constraint, a support
# constraint, and an orientation constraint.
solver.on_top_of(stack_of_plates_A[0], dining_table[0])
solver.distance_constraint(stack_of_plates_A[0], plates_A_anchor, 0, 0, weight=10)
solver.align_with(stack_of_plates_A[0], dining_table[0])

solver.on_top_of(stack_of_plates_B[0], dining_table[0])
solver.distance_constraint(stack_of_plates_B[0], plates_B_anchor, 0, 0, weight=10)
solver.align_with(stack_of_plates_B[0], dining_table[0])


# Console decorations remain on the console and aligned with it.
solver.on_top_of(vase_A[0], console_table[0])
solver.distance_constraint(vase_A[0], vase_A_anchor, 0, 0, weight=10)
solver.align_with(vase_A[0], console_table[0])

solver.on_top_of(table_lamp[0], console_table[0])
solver.distance_constraint(table_lamp[0], lamp_anchor, 0, 0, weight=10)
solver.align_with(table_lamp[0], console_table[0])

solver.on_top_of(vase_B[0], console_table[0])
solver.distance_constraint(vase_B[0], vase_B_anchor, 0, 0, weight=10)
solver.align_with(vase_B[0], console_table[0])


# The frame-on-buffet relationship is the primary semantic requirement.
solver.on_top_of(picture_frame[0], buffet_sideboard[0])
solver.distance_constraint(picture_frame[0], frame_anchor, 0, 0, weight=10)
solver.align_with(picture_frame[0], buffet_sideboard[0])

solver.on_top_of(decorative_jar[0], buffet_sideboard[0])
solver.distance_constraint(decorative_jar[0], jar_anchor, 0, 0, weight=10)
solver.align_with(decorative_jar[0], buffet_sideboard[0])


# Wall decorations have both wall-position and inward-facing orientation
# constraints. Exact anchors retain their intended spacing and heights.
solver.distance_constraint(wall_art_small_A[0], art_A_anchor, 0, 0, weight=10)
solver.against_wall(wall_art_small_A[0], walls[5])
solver.point_towards(wall_art_small_A[0], dining_table[0])

solver.distance_constraint(wall_art_small_B[0], art_B_anchor, 0, 0, weight=10)
solver.against_wall(wall_art_small_B[0], walls[5])
solver.point_towards(wall_art_small_B[0], dining_table[0])

solver.distance_constraint(wall_art_small_C[0], art_C_anchor, 0, 0, weight=10)
solver.against_wall(wall_art_small_C[0], walls[5])
solver.point_towards(wall_art_small_C[0], dining_table[0])

solver.distance_constraint(wall_art_small_D[0], art_D_anchor, 0, 0, weight=10)
solver.against_wall(wall_art_small_D[0], walls[5])
solver.point_towards(wall_art_small_D[0], dining_table[0])

solver.distance_constraint(wall_clock[0], clock_anchor, 0, 0, weight=10)
solver.against_wall(wall_clock[0], walls[4])
solver.point_towards(wall_clock[0], dining_table[0])

solver.constraints = []
display_shelf_B[0].position = [4.5, 4.823857307434082, 0.8999999761581421]
display_shelf_B[0].rotation = [0, 0, -1.5682554107885098]
display_shelf_B[0].optimize = 2
vase_B[0].position = [3.4200000762939453, 4.800000190734863, 0.9750000238418579]
vase_B[0].rotation = [0, 0, -1.5480059781645814]
vase_B[0].optimize = 2
dining_chair_A[0].position = [3.200000047683716, 1.4199999570846558, 0.44999998807907104]
dining_chair_A[0].rotation = [0, 0, 1.586504290712113]
dining_chair_A[0].optimize = 2
stack_of_plates_B[0].position = [3.200000047683716, 3.25, 0.8199999928474426]
stack_of_plates_B[0].rotation = [0, 0, 0.022791374650612577]
stack_of_plates_B[0].optimize = 2
stack_of_plates_A[0].position = [3.200000047683716, 2.3499999046325684, 0.8199999928474426]
stack_of_plates_A[0].rotation = [0, 0, 0.022791374650612577]
stack_of_plates_A[0].optimize = 2
bench_seat_B[0].position = [4.25, 2.799999952316284, 0.23000000417232513]
bench_seat_B[0].rotation = [0, 0, -3.1290262823329655]
bench_seat_B[0].optimize = 2
bench_seat_A[0].position = [2.1500000953674316, 2.799999952316284, 0.23000000417232513]
bench_seat_A[0].rotation = [0, 0, 0.01256637125682779]
bench_seat_A[0].optimize = 2
picture_frame[0].position = [0.25, 3.200000047683716, 1.0]
picture_frame[0].rotation = [0, 0, 0.02278960013808119]
picture_frame[0].optimize = 2
table_lamp[0].position = [3.0, 4.800000190734863, 1.0750000476837158]
table_lamp[0].rotation = [0, 0, -1.5480059781645814]
table_lamp[0].optimize = 2
display_shelf_A[0].position = [5.823857307434082, 1.7000000476837158, 0.8999999761581421]
display_shelf_A[0].rotation = [0, 0, -3.1390517375834066]
display_shelf_A[0].optimize = 2
wall_art_small_D[0].position = [0.02095547318458557, 4.0, 0.20000000298023224]
wall_art_small_D[0].rotation = [0, 0, 0.0025409215170312644]
wall_art_small_D[0].optimize = 2
wall_art_small_A[0].position = [0.02095547318458557, 2.6500000953674316, 0.20000000298023224]
wall_art_small_A[0].rotation = [0, 0, 0.0025409215170312644]
wall_art_small_A[0].optimize = 2
dining_chair_C[0].position = [3.549999952316284, 4.179999828338623, 0.44999998807907104]
dining_chair_C[0].rotation = [0, 0, -1.5613715493341729]
dining_chair_C[0].optimize = 2
dining_chair_B[0].position = [2.9000000953674316, 4.179999828338623, 0.44999998807907104]
dining_chair_B[0].rotation = [0, 0, -1.5613715493341729]
dining_chair_B[0].optimize = 2
buffet_sideboard[0].position = [0.26253822445869446, 3.3499999046325684, 0.42500001192092896]
buffet_sideboard[0].rotation = [0, 0, 0.01498390331397522]
buffet_sideboard[0].optimize = 2
storage_cabinet[0].position = [0.22626973688602448, 1.600000023841858, 0.8999999761581421]
storage_cabinet[0].rotation = [0, 0, 0.002540913862115027]
storage_cabinet[0].optimize = 2
wall_clock[0].position = [5.400000095367432, 4.979129314422607, 0.20000000298023224]
wall_clock[0].rotation = [0, 0, -1.5682554052778654]
wall_clock[0].optimize = 2
dining_table[0].position = [3.200000047683716, 2.799999952316284, 0.3799999952316284]
dining_table[0].rotation = [0, 0, 0.0722566305613884]
dining_table[0].optimize = 2
serving_trolley[0].position = [5.773984432220459, 4.25, 0.42500001192092896]
serving_trolley[0].rotation = [0, 0, -3.1390517366612336]
serving_trolley[0].optimize = 2
decorative_jar[0].position = [0.25, 3.799999952316284, 1.0500000715255737]
decorative_jar[0].rotation = [0, 0, 0.02278960013808119]
decorative_jar[0].optimize = 2
console_table[0].position = [3.0, 4.788110733032227, 0.4000000059604645]
console_table[0].rotation = [0, 0, -1.5495903289341262]
console_table[0].optimize = 2
wall_art_small_C[0].position = [0.02095547318458557, 3.549999952316284, 0.20000000298023224]
wall_art_small_C[0].rotation = [0, 0, 0.0025409215170312644]
wall_art_small_C[0].optimize = 2
wall_art_small_B[0].position = [0.02095547318458557, 3.0999999046325684, 0.20000000298023224]
wall_art_small_B[0].rotation = [0, 0, 0.0025409215170312644]
wall_art_small_B[0].optimize = 2
vase_A[0].position = [2.5799999237060547, 4.800000190734863, 0.9750000238418579]
vase_A[0].rotation = [0, 0, -1.5480059781645814]
vase_A[0].optimize = 2

