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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[7.00, 0.00, 0.00]),
    Wall(corner1=[7.00, 0.00, 0.00], corner2=[7.00, 3.00, 0.00]),
    Wall(corner1=[7.00, 3.00, 0.00], corner2=[0.00, 3.00, 0.00]),
    Wall(corner1=[0.00, 3.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
waste_bin_A = Assets(description="A small cylindrical gray trash can with a black step opener and a large black hinge on top.", size=[0.30, 0.25, 0.35], placements=[AssetInstance() for _ in range(1)])
doctor_desk = Assets(description="A light colored desk with a thin drawer.", size=[0.70, 1.40, 0.75], placements=[AssetInstance() for _ in range(1)])
tall_storage_cabinet = Assets(description="A grey upright filing cabinet.", size=[0.60, 0.50, 1.80], placements=[AssetInstance() for _ in range(1)])
visitor_chair_A = Assets(description="A green chair with a black frame.", size=[0.60, 0.55, 0.85], placements=[AssetInstance() for _ in range(1)])
exam_table = Assets(description="Wood frame lawn chair with a white cushion.", size=[0.70, 1.90, 0.80], placements=[AssetInstance() for _ in range(1)])
patient_file_tray = Assets(description="A yellow box with grey button on the corner.", size=[0.25, 0.35, 0.10], placements=[AssetInstance() for _ in range(1)])
magazine_rack_floor = Assets(description="A brown book case with four shelve and filled with books.", size=[0.30, 0.80, 1.20], placements=[AssetInstance() for _ in range(1)])
step_stool = Assets(description="A gray stool with wheels.", size=[0.50, 0.50, 0.50], placements=[AssetInstance() for _ in range(1)])
wall_cabinet_A = Assets(description="A white cabinet with shelves.", size=[0.30, 0.80, 0.70], placements=[AssetInstance() for _ in range(1)])
notice_board = Assets(description="A chalkboard with prices.", size=[0.04, 1.20, 0.80], placements=[AssetInstance() for _ in range(1)])
mobile_medical_trolley = Assets(description="Gray cart with wheels and three shelves.", size=[0.45, 0.65, 0.90], placements=[AssetInstance() for _ in range(1)])
low_storage_cabinet = Assets(description="A set of drawers in a white block.", size=[0.50, 0.90, 0.75], placements=[AssetInstance() for _ in range(1)])
waste_bin_B = Assets(description="A small cylindrical gray trash can with a black step opener and a large black hinge on top.", size=[0.30, 0.25, 0.35], placements=[AssetInstance() for _ in range(1)])
patient_file_folder = Assets(description="A screen with a black black and a cord attached.", size=[0.24, 0.32, 0.04], placements=[AssetInstance() for _ in range(1)])
wall_cabinet_B = Assets(description="A white cabinet with shelves.", size=[0.30, 0.80, 0.70], placements=[AssetInstance() for _ in range(1)])
visitor_chair_B = Assets(description="A green chair with a black frame.", size=[0.60, 0.55, 0.85], placements=[AssetInstance() for _ in range(1)])
packaged_medical_supplies = Assets(description="A green metal first aid box with a white cross on the top.", size=[0.25, 0.35, 0.15], placements=[AssetInstance() for _ in range(1)])
wall_clock = Assets(description="A wall clock with a pair of butterflies on it.", size=[0.05, 0.30, 0.30], placements=[AssetInstance() for _ in range(1)])
sharps_container_floor = Assets(description="A yellow cannister with a black top.", size=[0.30, 0.30, 0.60], placements=[AssetInstance() for _ in range(1)])
disposable_exam_paper_roll = Assets(description="A roll of toilet tissue that has floral designs on it.", size=[0.15, 0.60, 0.15], placements=[AssetInstance() for _ in range(1)])

waste_bin_A[0].instance_id = 'waste_bin_A_0'
doctor_desk[0].instance_id = 'doctor_desk_0'
tall_storage_cabinet[0].instance_id = 'tall_storage_cabinet_0'
visitor_chair_A[0].instance_id = 'visitor_chair_A_0'
exam_table[0].instance_id = 'exam_table_0'
patient_file_tray[0].instance_id = 'patient_file_tray_0'
magazine_rack_floor[0].instance_id = 'magazine_rack_floor_0'
step_stool[0].instance_id = 'step_stool_0'
wall_cabinet_A[0].instance_id = 'wall_cabinet_A_0'
notice_board[0].instance_id = 'notice_board_0'
mobile_medical_trolley[0].instance_id = 'mobile_medical_trolley_0'
low_storage_cabinet[0].instance_id = 'low_storage_cabinet_0'
waste_bin_B[0].instance_id = 'waste_bin_B_0'
patient_file_folder[0].instance_id = 'patient_file_folder_0'
wall_cabinet_B[0].instance_id = 'wall_cabinet_B_0'
visitor_chair_B[0].instance_id = 'visitor_chair_B_0'
packaged_medical_supplies[0].instance_id = 'packaged_medical_supplies_0'
wall_clock[0].instance_id = 'wall_clock_0'
sharps_container_floor[0].instance_id = 'sharps_container_floor_0'
disposable_exam_paper_roll[0].instance_id = 'disposable_exam_paper_roll_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

waste_bin_A[0].position = [1.3852405761124886, 2.0890302548432587, 0.175]
waste_bin_A[0].rotation = [0, 0, 0]
doctor_desk[0].position = [1.7080488081511094, 1.3998854342457077, 0.375]
doctor_desk[0].rotation = [0, 0, 0]
tall_storage_cabinet[0].position = [5.804581340259084, 0.9487379801517467, 0.9]
tall_storage_cabinet[0].rotation = [0, 0, 0]
visitor_chair_A[0].position = [6.621771873750188, 0.7842627724419743, 0.425]
visitor_chair_A[0].rotation = [0, 0, 0]
exam_table[0].position = [2.2254069787817716, 0.8323164971699913, 0.4]
exam_table[0].rotation = [0, 0, 0]
patient_file_tray[0].position = [0.3675042740410327, 0.13703809503192854, 0.05]
patient_file_tray[0].rotation = [0, 0, 0]
magazine_rack_floor[0].position = [4.781806442489043, 0.6772165278242426, 0.6]
magazine_rack_floor[0].rotation = [0, 0, 0]
step_stool[0].position = [1.5486626558965058, 1.3156463106666492, 0.25]
step_stool[0].rotation = [0, 0, 0]
wall_cabinet_A[0].position = [2.810600507062848, 1.6887540352377268, 0.35]
wall_cabinet_A[0].rotation = [0, 0, 0]
notice_board[0].position = [1.8437035438750473, 0.9941102819707419, 0.4]
notice_board[0].rotation = [0, 0, 0]
mobile_medical_trolley[0].position = [1.9997049235270878, 2.109127870194845, 0.45]
mobile_medical_trolley[0].rotation = [0, 0, 0]
low_storage_cabinet[0].position = [5.7966128280396525, 0.7996879246874093, 0.375]
low_storage_cabinet[0].rotation = [0, 0, 0]
waste_bin_B[0].position = [1.7142099113094238, 1.8066376013938228, 0.175]
waste_bin_B[0].rotation = [0, 0, 0]
patient_file_folder[0].position = [4.272269248287797, 0.8861438537408131, 0.02]
patient_file_folder[0].rotation = [0, 0, 0]
wall_cabinet_B[0].position = [0.6111026396889243, 2.0393359625663594, 0.35]
wall_cabinet_B[0].rotation = [0, 0, 0]
visitor_chair_B[0].position = [1.4799734532790496, 0.2928189562983221, 0.425]
visitor_chair_B[0].rotation = [0, 0, 0]
packaged_medical_supplies[0].position = [2.9131881591740445, 1.3080848337263218, 0.075]
packaged_medical_supplies[0].rotation = [0, 0, 0]
wall_clock[0].position = [6.223634823447059, 2.59848207837403, 0.15]
wall_clock[0].rotation = [0, 0, 0]
sharps_container_floor[0].position = [3.9652263008418487, 0.07736845960665606, 0.3]
sharps_container_floor[0].rotation = [0, 0, 0]
disposable_exam_paper_roll[0].position = [3.3386012143286754, 2.2468291296119354, 0.075]
disposable_exam_paper_roll[0].rotation = [0, 0, 0]
waste_bin_A[0].position = [1.3852405761124886, 2.0890302548432587, 0.175]
waste_bin_A[0].rotation = [0, 0, 0]
doctor_desk[0].position = [1.7080488081511094, 1.3998854342457077, 0.375]
doctor_desk[0].rotation = [0, 0, 0]
tall_storage_cabinet[0].position = [5.804581340259084, 0.9487379801517467, 0.9]
tall_storage_cabinet[0].rotation = [0, 0, 0]
visitor_chair_A[0].position = [6.621771873750188, 0.7842627724419743, 0.425]
visitor_chair_A[0].rotation = [0, 0, 0]
exam_table[0].position = [2.2254069787817716, 0.8323164971699913, 0.4]
exam_table[0].rotation = [0, 0, 0]
patient_file_tray[0].position = [0.3675042740410327, 0.13703809503192854, 0.05]
patient_file_tray[0].rotation = [0, 0, 0]
magazine_rack_floor[0].position = [4.781806442489043, 0.6772165278242426, 0.6]
magazine_rack_floor[0].rotation = [0, 0, 0]
step_stool[0].position = [1.5486626558965058, 1.3156463106666492, 0.25]
step_stool[0].rotation = [0, 0, 0]
wall_cabinet_A[0].position = [2.810600507062848, 1.6887540352377268, 0.35]
wall_cabinet_A[0].rotation = [0, 0, 0]
notice_board[0].position = [1.8437035438750473, 0.9941102819707419, 0.4]
notice_board[0].rotation = [0, 0, 0]
mobile_medical_trolley[0].position = [1.9997049235270878, 2.109127870194845, 0.45]
mobile_medical_trolley[0].rotation = [0, 0, 0]
low_storage_cabinet[0].position = [5.7966128280396525, 0.7996879246874093, 0.375]
low_storage_cabinet[0].rotation = [0, 0, 0]
waste_bin_B[0].position = [1.7142099113094238, 1.8066376013938228, 0.175]
waste_bin_B[0].rotation = [0, 0, 0]
patient_file_folder[0].position = [4.272269248287797, 0.8861438537408131, 0.02]
patient_file_folder[0].rotation = [0, 0, 0]
wall_cabinet_B[0].position = [0.6111026396889243, 2.0393359625663594, 0.35]
wall_cabinet_B[0].rotation = [0, 0, 0]
visitor_chair_B[0].position = [1.4799734532790496, 0.2928189562983221, 0.425]
visitor_chair_B[0].rotation = [0, 0, 0]
packaged_medical_supplies[0].position = [2.9131881591740445, 1.3080848337263218, 0.075]
packaged_medical_supplies[0].rotation = [0, 0, 0]
wall_clock[0].position = [6.223634823447059, 2.59848207837403, 0.15]
wall_clock[0].rotation = [0, 0, 0]
sharps_container_floor[0].position = [3.9652263008418487, 0.07736845960665606, 0.3]
sharps_container_floor[0].rotation = [0, 0, 0]
disposable_exam_paper_roll[0].position = [3.3386012143286754, 2.2468291296119354, 0.075]
disposable_exam_paper_roll[0].rotation = [0, 0, 0]

solver.constraints = []

# Orientation references used to keep wall furniture square to the room.
south_facing = AssetInstance(rotation=[0, 0, radians(-90)])
north_facing = AssetInstance(rotation=[0, 0, radians(90)])
west_facing = AssetInstance(rotation=[0, 0, radians(180)])

# Arrange the main clinical furniture along the upper wall. This leaves a
# continuous circulation aisle through the middle and keeps the right-hand
# door approach (especially x > 5.7, y < 1.8) unobstructed.
doctor_desk[0].position = [3.45, 2.65, 0.375]
doctor_desk[0].rotation = [0, 0, radians(-90)]

exam_table[0].position = [1.25, 2.65, 0.40]
exam_table[0].rotation = [0, 0, radians(-90)]

tall_storage_cabinet[0].position = [6.70, 2.40, 0.90]
tall_storage_cabinet[0].rotation = [0, 0, radians(180)]

mobile_medical_trolley[0].position = [5.15, 2.675, 0.45]
mobile_medical_trolley[0].rotation = [0, 0, radians(-90)]

sharps_container_floor[0].position = [6.15, 2.85, 0.30]
sharps_container_floor[0].rotation = [0, 0, radians(-90)]

# Two visitor chairs face the doctor's side of the desk without blocking the
# central aisle or the doorway.
visitor_chair_A[0].position = [3.10, 1.50, 0.425]
visitor_chair_A[0].rotation = [0, 0, radians(90)]

visitor_chair_B[0].position = [3.90, 1.50, 0.425]
visitor_chair_B[0].rotation = [0, 0, radians(90)]

# The stool and bins remain convenient to the work areas while preserving
# clearance between the desk, exam table, and visitor chairs.
step_stool[0].position = [1.90, 1.65, 0.25]
step_stool[0].rotation = [0, 0, radians(90)]

waste_bin_A[0].position = [2.48, 2.08, 0.175]
waste_bin_A[0].rotation = [0, 0, radians(90)]

waste_bin_B[0].position = [4.45, 1.98, 0.175]
waste_bin_B[0].rotation = [0, 0, radians(90)]

# Low floor storage is distributed along the lower wall. Neither piece
# projects into the required clear path in front of the right-wall door.
magazine_rack_floor[0].position = [1.00, 0.15, 0.60]
magazine_rack_floor[0].rotation = [0, 0, radians(90)]

low_storage_cabinet[0].position = [5.15, 0.25, 0.375]
low_storage_cabinet[0].rotation = [0, 0, radians(90)]

# Wall-mounted storage is placed above the trolley zone. The lower edges are
# above the trolley, preventing vertical overlap.
wall_cabinet_A[0].position = [4.55, 2.85, 1.50]
wall_cabinet_A[0].rotation = [0, 0, radians(-90)]

wall_cabinet_B[0].position = [5.55, 2.85, 1.50]
wall_cabinet_B[0].rotation = [0, 0, radians(-90)]

# The notice board and clock use the lower wall, leaving both windows on the
# left wall completely unobstructed.
notice_board[0].position = [2.25, 0.02, 1.45]
notice_board[0].rotation = [0, 0, radians(90)]

wall_clock[0].position = [3.45, 0.025, 1.70]
wall_clock[0].rotation = [0, 0, radians(90)]

# Desktop objects are separated across the desk surface. Their elevations
# equal the desk-top height plus half of each object's height.
patient_file_tray[0].position = [3.10, 2.62, 0.80]
patient_file_tray[0].rotation = [0, 0, radians(-90)]

patient_file_folder[0].position = [3.72, 2.62, 0.77]
patient_file_folder[0].rotation = [0, 0, radians(-90)]

# Supplies sit on the low cabinet, and the paper roll sits at the head end of
# the exam table.
packaged_medical_supplies[0].position = [5.15, 0.25, 0.825]
packaged_medical_supplies[0].rotation = [0, 0, radians(90)]

disposable_exam_paper_roll[0].position = [0.70, 2.65, 0.875]
disposable_exam_paper_roll[0].rotation = [0, 0, radians(-90)]


# Support constraints are listed first because maintaining these required
# vertical relationships is more important than small horizontal adjustments.
solver.on_top_of(patient_file_folder[0], doctor_desk[0])
solver.on_top_of(patient_file_tray[0], doctor_desk[0])
solver.on_top_of(packaged_medical_supplies[0], low_storage_cabinet[0])
solver.on_top_of(disposable_exam_paper_roll[0], exam_table[0])

# High-weight fixed points preserve the planned non-overlapping arrangement.
solver.distance_constraint(
    doctor_desk[0], AssetInstance(position=[3.45, 2.65, 0.375]),
    0, 0, weight=10
)
solver.distance_constraint(
    exam_table[0], AssetInstance(position=[1.25, 2.65, 0.40]),
    0, 0, weight=10
)
solver.distance_constraint(
    tall_storage_cabinet[0], AssetInstance(position=[6.70, 2.40, 0.90]),
    0, 0, weight=10
)
solver.distance_constraint(
    mobile_medical_trolley[0], AssetInstance(position=[5.15, 2.675, 0.45]),
    0, 0, weight=10
)
solver.distance_constraint(
    sharps_container_floor[0], AssetInstance(position=[6.15, 2.85, 0.30]),
    0, 0, weight=10
)
solver.distance_constraint(
    visitor_chair_A[0], AssetInstance(position=[3.10, 1.50, 0.425]),
    0, 0, weight=10
)
solver.distance_constraint(
    visitor_chair_B[0], AssetInstance(position=[3.90, 1.50, 0.425]),
    0, 0, weight=10
)
solver.distance_constraint(
    step_stool[0], AssetInstance(position=[1.90, 1.65, 0.25]),
    0, 0, weight=10
)
solver.distance_constraint(
    waste_bin_A[0], AssetInstance(position=[2.48, 2.08, 0.175]),
    0, 0, weight=10
)
solver.distance_constraint(
    waste_bin_B[0], AssetInstance(position=[4.45, 1.98, 0.175]),
    0, 0, weight=10
)
solver.distance_constraint(
    magazine_rack_floor[0], AssetInstance(position=[1.00, 0.15, 0.60]),
    0, 0, weight=10
)
solver.distance_constraint(
    low_storage_cabinet[0], AssetInstance(position=[5.15, 0.25, 0.375]),
    0, 0, weight=10
)
solver.distance_constraint(
    wall_cabinet_A[0], AssetInstance(position=[4.55, 2.85, 1.50]),
    0, 0, weight=10
)
solver.distance_constraint(
    wall_cabinet_B[0], AssetInstance(position=[5.55, 2.85, 1.50]),
    0, 0, weight=10
)
solver.distance_constraint(
    notice_board[0], AssetInstance(position=[2.25, 0.02, 1.45]),
    0, 0, weight=10
)
solver.distance_constraint(
    wall_clock[0], AssetInstance(position=[3.45, 0.025, 1.70]),
    0, 0, weight=10
)
solver.distance_constraint(
    patient_file_tray[0], AssetInstance(position=[3.10, 2.62, 0.80]),
    0, 0, weight=10
)
solver.distance_constraint(
    patient_file_folder[0], AssetInstance(position=[3.72, 2.62, 0.77]),
    0, 0, weight=10
)
solver.distance_constraint(
    packaged_medical_supplies[0], AssetInstance(position=[5.15, 0.25, 0.825]),
    0, 0, weight=10
)
solver.distance_constraint(
    disposable_exam_paper_roll[0],
    AssetInstance(position=[0.70, 2.65, 0.875]),
    0, 0, weight=10
)

# Wall relationships retain the intended perimeter organization if the room
# dimensions or placements are adjusted.
solver.against_wall(doctor_desk[0], walls[2])
solver.against_wall(exam_table[0], walls[2])
solver.against_wall(mobile_medical_trolley[0], walls[2])
solver.against_wall(sharps_container_floor[0], walls[2])
solver.against_wall(tall_storage_cabinet[0], walls[1])
solver.against_wall(magazine_rack_floor[0], walls[0])
solver.against_wall(low_storage_cabinet[0], walls[0])
solver.against_wall(wall_cabinet_A[0], walls[2])
solver.against_wall(wall_cabinet_B[0], walls[2])
solver.against_wall(notice_board[0], walls[0])
solver.against_wall(wall_clock[0], walls[0])

# Major wall-side furniture faces inward and remains square to its wall.
solver.align_with(doctor_desk[0], south_facing)
solver.align_with(exam_table[0], south_facing)
solver.align_with(mobile_medical_trolley[0], south_facing)
solver.align_with(sharps_container_floor[0], south_facing)
solver.align_with(wall_cabinet_A[0], south_facing)
solver.align_with(wall_cabinet_B[0], south_facing)
solver.align_with(tall_storage_cabinet[0], west_facing)
solver.align_with(magazine_rack_floor[0], north_facing)
solver.align_with(low_storage_cabinet[0], north_facing)
solver.align_with(notice_board[0], north_facing)
solver.align_with(wall_clock[0], north_facing)

# Freestanding clinical seating and accessories are oriented toward the
# associated work area.
solver.point_towards(visitor_chair_A[0], doctor_desk[0])
solver.point_towards(visitor_chair_B[0], doctor_desk[0])
solver.point_towards(step_stool[0], exam_table[0])
solver.point_towards(waste_bin_A[0], exam_table[0])
solver.point_towards(waste_bin_B[0], doctor_desk[0])

# Objects resting on furniture inherit the support object's orientation.
solver.align_with(patient_file_tray[0], doctor_desk[0])
solver.align_with(patient_file_folder[0], doctor_desk[0])
solver.align_with(packaged_medical_supplies[0], low_storage_cabinet[0])
solver.align_with(disposable_exam_paper_roll[0], exam_table[0])

# Preserve useful working distances between the chairs and desk and between
# the stool and exam table if feasibility adjustments move the furniture.
solver.distance_constraint(
    visitor_chair_A[0], doctor_desk[0], 1.05, 1.40, weight=1
)
solver.distance_constraint(
    visitor_chair_B[0], doctor_desk[0], 1.05, 1.40, weight=1
)
solver.distance_constraint(
    step_stool[0], exam_table[0], 0.95, 1.35, weight=1
)

solver.constraints = []
wall_cabinet_B[0].position = [5.550000190734863, 2.8489840030670166, 0.3499999940395355]
wall_cabinet_B[0].rotation = [0, 0, -1.5682554098663368]
wall_cabinet_B[0].optimize = 2
disposable_exam_paper_roll[0].position = [0.699999988079071, 2.6500000953674316, 0.875]
disposable_exam_paper_roll[0].rotation = [0, 0, -1.5480062806449197]
disposable_exam_paper_roll[0].optimize = 2
magazine_rack_floor[0].position = [1.0, 0.15101589262485504, 0.6000000238418579]
magazine_rack_floor[0].rotation = [0, 0, 1.5733372437234565]
magazine_rack_floor[0].optimize = 2
waste_bin_A[0].position = [2.4800000190734863, 2.0799999237060547, 0.17499999701976776]
waste_bin_A[0].rotation = [0, 0, 1.5904154997375561]
waste_bin_A[0].optimize = 2
wall_cabinet_A[0].position = [4.550000190734863, 2.8489840030670166, 0.3499999940395355]
wall_cabinet_A[0].rotation = [0, 0, -1.5682554098663368]
wall_cabinet_A[0].optimize = 2
sharps_container_floor[0].position = [6.150000095367432, 2.8496193885803223, 0.30000001192092896]
sharps_container_floor[0].rotation = [0, 0, -1.568255406200039]
sharps_container_floor[0].optimize = 2
notice_board[0].position = [2.25, 0.02152448147535324, 0.4000000059604645]
notice_board[0].rotation = [0, 0, 1.5733372382128155]
notice_board[0].optimize = 2
mobile_medical_trolley[0].position = [5.150000095367432, 2.684999942779541, 0.44999998807907104]
mobile_medical_trolley[0].rotation = [0, 0, -1.5682554086442377]
mobile_medical_trolley[0].optimize = 2
patient_file_tray[0].position = [3.0999999046325684, 2.619999885559082, 0.800000011920929]
patient_file_tray[0].rotation = [0, 0, -1.5480054804059165]
patient_file_tray[0].optimize = 2
step_stool[0].position = [1.899999976158142, 1.649999976158142, 0.25]
step_stool[0].rotation = [0, 0, 1.5833626980517244]
step_stool[0].optimize = 2
tall_storage_cabinet[0].position = [6.699365615844727, 2.4000000953674316, 0.8999999761581421]
tall_storage_cabinet[0].rotation = [0, 0, -3.1390517332948615]
tall_storage_cabinet[0].optimize = 2
wall_clock[0].position = [3.450000047683716, 0.016124853864312172, 0.15000000596046448]
wall_clock[0].rotation = [0, 0, 1.573337248311928]
wall_clock[0].optimize = 2
patient_file_folder[0].position = [3.7200000286102295, 2.619999885559082, 0.7699999809265137]
patient_file_folder[0].rotation = [0, 0, -1.5480054804059165]
patient_file_folder[0].optimize = 2
visitor_chair_B[0].position = [3.9000000953674316, 1.5, 0.42500001192092896]
visitor_chair_B[0].rotation = [0, 0, 1.5833626980517244]
visitor_chair_B[0].optimize = 2
low_storage_cabinet[0].position = [5.150000095367432, 0.2539333403110504, 0.375]
low_storage_cabinet[0].rotation = [0, 0, 1.5795585468286093]
low_storage_cabinet[0].optimize = 2
waste_bin_B[0].position = [4.449999809265137, 1.9800000190734863, 0.17499999701976776]
waste_bin_B[0].rotation = [0, 0, 1.5904154973756477]
waste_bin_B[0].optimize = 2
packaged_medical_supplies[0].position = [5.150000095367432, 0.25, 0.824999988079071]
packaged_medical_supplies[0].rotation = [0, 0, 1.5935836929706761]
packaged_medical_supplies[0].optimize = 2
visitor_chair_A[0].position = [3.0999999046325684, 1.5, 0.42500001192092896]
visitor_chair_A[0].rotation = [0, 0, 1.5833626980517244]
visitor_chair_A[0].optimize = 2
doctor_desk[0].position = [3.450000047683716, 2.63171124458313, 0.375]
doctor_desk[0].rotation = [0, 0, -1.5402564559325718]
doctor_desk[0].optimize = 2
exam_table[0].position = [1.25, 2.6332828998565674, 0.4000000059604645]
exam_table[0].rotation = [0, 0, -1.5527014266695367]
exam_table[0].optimize = 2

