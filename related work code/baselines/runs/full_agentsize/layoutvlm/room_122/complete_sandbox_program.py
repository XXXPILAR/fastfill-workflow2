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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[9.00, 0.00, 0.00]),
    Wall(corner1=[9.00, 0.00, 0.00], corner2=[9.00, 9.00, 0.00]),
    Wall(corner1=[9.00, 9.00, 0.00], corner2=[8.00, 9.00, 0.00]),
    Wall(corner1=[8.00, 9.00, 0.00], corner2=[8.00, 12.00, 0.00]),
    Wall(corner1=[8.00, 12.00, 0.00], corner2=[0.00, 12.00, 0.00]),
    Wall(corner1=[0.00, 12.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
collaboration_stool_A = Assets(description="A stool with a metal leg and foot rest with a round black cushion.", size=[0.42, 0.42, 0.75], placements=[AssetInstance() for _ in range(1)])
task_chair_A = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.65, 0.65, 0.95], placements=[AssetInstance() for _ in range(1)])
task_chair_B = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.65, 0.65, 0.95], placements=[AssetInstance() for _ in range(1)])
bench_desk_A = Assets(description="A brown, rectangular table with four, grey legs.", size=[0.80, 1.60, 0.74], placements=[AssetInstance() for _ in range(1)])
toner_box_A = Assets(description="Black plastic printer with buttons at the top.", size=[0.45, 0.45, 0.30], placements=[AssetInstance() for _ in range(1)])
task_chair_C = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.65, 0.65, 0.95], placements=[AssetInstance() for _ in range(1)])
task_chair_D = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.65, 0.65, 0.95], placements=[AssetInstance() for _ in range(1)])
high_storage_shelf_A = Assets(description="It is a tall set of shelves made of wood and metal.", size=[0.40, 1.20, 2.00], placements=[AssetInstance() for _ in range(1)])
whiteboard_panel_A = Assets(description="A white rectangular poster with black blue and orange marks and irregular writing.", size=[0.04, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
task_chair_E = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.65, 0.65, 0.95], placements=[AssetInstance() for _ in range(1)])
computer_monitor_A = Assets(description="a flat screen monitor on a stand.", size=[0.20, 0.55, 0.45], placements=[AssetInstance() for _ in range(1)])
task_chair_F = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.65, 0.65, 0.95], placements=[AssetInstance() for _ in range(1)])
potted_plant_small_A = Assets(description="A bunch of big leaves inside of a white pot.", size=[0.45, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
bench_desk_B = Assets(description="A brown, rectangular table with four, grey legs.", size=[0.80, 1.60, 0.74], placements=[AssetInstance() for _ in range(1)])
task_chair_G = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.65, 0.65, 0.95], placements=[AssetInstance() for _ in range(1)])
ring_binder = Assets(description="A brown book with silver corners.", size=[0.28, 0.30, 0.06], placements=[AssetInstance() for _ in range(1)])
low_storage_credensa_A = Assets(description="A black cabinet with grey doors.", size=[0.45, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
whiteboard_panel_B = Assets(description="A white rectangular poster with black blue and orange marks and irregular writing.", size=[0.04, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
toner_box_B = Assets(description="Black plastic printer with buttons at the top.", size=[0.45, 0.45, 0.30], placements=[AssetInstance() for _ in range(1)])
task_chair_H = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.65, 0.65, 0.95], placements=[AssetInstance() for _ in range(1)])
task_chair_I = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.65, 0.65, 0.95], placements=[AssetInstance() for _ in range(1)])
potted_plant_small_B = Assets(description="A bunch of big leaves inside of a white pot.", size=[0.45, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
side_collaboration_table = Assets(description="A brown, oval table.", size=[0.70, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
locker_unit = Assets(description="A large black filing cabinet with 5 drawers down and 4 across.", size=[0.45, 1.60, 1.80], placements=[AssetInstance() for _ in range(1)])
file_box = Assets(description="A brown book with silver corners.", size=[0.25, 0.33, 0.10], placements=[AssetInstance() for _ in range(1)])
task_chair_J = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.65, 0.65, 0.95], placements=[AssetInstance() for _ in range(1)])
printer_side_table_A = Assets(description="A black frame metal stand with two wooden shelves and four caster wheels.", size=[0.50, 0.65, 0.75], placements=[AssetInstance() for _ in range(1)])
task_chair_K = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.65, 0.65, 0.95], placements=[AssetInstance() for _ in range(1)])
low_storage_credensa_B = Assets(description="A black cabinet with grey doors.", size=[0.45, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
bench_desk_C = Assets(description="A brown, rectangular table with four, grey legs.", size=[0.80, 1.60, 0.74], placements=[AssetInstance() for _ in range(1)])
bench_desk_D = Assets(description="A brown, rectangular table with four, grey legs.", size=[0.80, 1.60, 0.74], placements=[AssetInstance() for _ in range(1)])
sticky_note_pad = Assets(description="A box of kleenix wipes.", size=[0.12, 0.22, 0.08], placements=[AssetInstance() for _ in range(1)])
collaboration_stool_B = Assets(description="A stool with a metal leg and foot rest with a round black cushion.", size=[0.42, 0.42, 0.75], placements=[AssetInstance() for _ in range(1)])
task_chair_L = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.65, 0.65, 0.95], placements=[AssetInstance() for _ in range(1)])
task_chair_M = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.65, 0.65, 0.95], placements=[AssetInstance() for _ in range(1)])
bench_desk_E = Assets(description="A brown, rectangular table with four, grey legs.", size=[0.80, 1.60, 0.74], placements=[AssetInstance() for _ in range(1)])
task_chair_N = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.65, 0.65, 0.95], placements=[AssetInstance() for _ in range(1)])
bench_desk_F = Assets(description="A brown, rectangular table with four, grey legs.", size=[0.80, 1.60, 0.74], placements=[AssetInstance() for _ in range(1)])
printer_side_table_B = Assets(description="A black frame metal stand with two wooden shelves and four caster wheels.", size=[0.50, 0.65, 0.75], placements=[AssetInstance() for _ in range(1)])
task_chair_O = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.65, 0.65, 0.95], placements=[AssetInstance() for _ in range(1)])
computer_monitor_B = Assets(description="a flat screen monitor on a stand.", size=[0.20, 0.55, 0.45], placements=[AssetInstance() for _ in range(1)])
collaboration_stool_C = Assets(description="A stool with a metal leg and foot rest with a round black cushion.", size=[0.42, 0.42, 0.75], placements=[AssetInstance() for _ in range(1)])
computer_monitor_C = Assets(description="a flat screen monitor on a stand.", size=[0.20, 0.55, 0.45], placements=[AssetInstance() for _ in range(1)])
potted_plant_small_C = Assets(description="A bunch of big leaves inside of a white pot.", size=[0.45, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
low_storage_credensa_C = Assets(description="A black cabinet with grey doors.", size=[0.45, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
computer_monitor_D = Assets(description="a flat screen monitor on a stand.", size=[0.20, 0.55, 0.45], placements=[AssetInstance() for _ in range(1)])
task_chair_P = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.65, 0.65, 0.95], placements=[AssetInstance() for _ in range(1)])
task_chair_Q = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.65, 0.65, 0.95], placements=[AssetInstance() for _ in range(1)])
task_chair_R = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.65, 0.65, 0.95], placements=[AssetInstance() for _ in range(1)])
high_storage_shelf_B = Assets(description="It is a tall set of shelves made of wood and metal.", size=[0.40, 1.20, 2.00], placements=[AssetInstance() for _ in range(1)])

collaboration_stool_A[0].instance_id = 'collaboration_stool_A_0'
task_chair_A[0].instance_id = 'task_chair_A_0'
task_chair_B[0].instance_id = 'task_chair_B_0'
bench_desk_A[0].instance_id = 'bench_desk_A_0'
toner_box_A[0].instance_id = 'toner_box_A_0'
task_chair_C[0].instance_id = 'task_chair_C_0'
task_chair_D[0].instance_id = 'task_chair_D_0'
high_storage_shelf_A[0].instance_id = 'high_storage_shelf_A_0'
whiteboard_panel_A[0].instance_id = 'whiteboard_panel_A_0'
task_chair_E[0].instance_id = 'task_chair_E_0'
computer_monitor_A[0].instance_id = 'computer_monitor_A_0'
task_chair_F[0].instance_id = 'task_chair_F_0'
potted_plant_small_A[0].instance_id = 'potted_plant_small_A_0'
bench_desk_B[0].instance_id = 'bench_desk_B_0'
task_chair_G[0].instance_id = 'task_chair_G_0'
ring_binder[0].instance_id = 'ring_binder_0'
low_storage_credensa_A[0].instance_id = 'low_storage_credensa_A_0'
whiteboard_panel_B[0].instance_id = 'whiteboard_panel_B_0'
toner_box_B[0].instance_id = 'toner_box_B_0'
task_chair_H[0].instance_id = 'task_chair_H_0'
task_chair_I[0].instance_id = 'task_chair_I_0'
potted_plant_small_B[0].instance_id = 'potted_plant_small_B_0'
side_collaboration_table[0].instance_id = 'side_collaboration_table_0'
locker_unit[0].instance_id = 'locker_unit_0'
file_box[0].instance_id = 'file_box_0'
task_chair_J[0].instance_id = 'task_chair_J_0'
printer_side_table_A[0].instance_id = 'printer_side_table_A_0'
task_chair_K[0].instance_id = 'task_chair_K_0'
low_storage_credensa_B[0].instance_id = 'low_storage_credensa_B_0'
bench_desk_C[0].instance_id = 'bench_desk_C_0'
bench_desk_D[0].instance_id = 'bench_desk_D_0'
sticky_note_pad[0].instance_id = 'sticky_note_pad_0'
collaboration_stool_B[0].instance_id = 'collaboration_stool_B_0'
task_chair_L[0].instance_id = 'task_chair_L_0'
task_chair_M[0].instance_id = 'task_chair_M_0'
bench_desk_E[0].instance_id = 'bench_desk_E_0'
task_chair_N[0].instance_id = 'task_chair_N_0'
bench_desk_F[0].instance_id = 'bench_desk_F_0'
printer_side_table_B[0].instance_id = 'printer_side_table_B_0'
task_chair_O[0].instance_id = 'task_chair_O_0'
computer_monitor_B[0].instance_id = 'computer_monitor_B_0'
collaboration_stool_C[0].instance_id = 'collaboration_stool_C_0'
computer_monitor_C[0].instance_id = 'computer_monitor_C_0'
potted_plant_small_C[0].instance_id = 'potted_plant_small_C_0'
low_storage_credensa_C[0].instance_id = 'low_storage_credensa_C_0'
computer_monitor_D[0].instance_id = 'computer_monitor_D_0'
task_chair_P[0].instance_id = 'task_chair_P_0'
task_chair_Q[0].instance_id = 'task_chair_Q_0'
task_chair_R[0].instance_id = 'task_chair_R_0'
high_storage_shelf_B[0].instance_id = 'high_storage_shelf_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

collaboration_stool_A[0].position = [6.702192442549098, 9.413158117242226, 0.375]
collaboration_stool_A[0].rotation = [0, 0, 0]
task_chair_A[0].position = [2.7503572895137394, 7.440271639489538, 0.475]
task_chair_A[0].rotation = [0, 0, 0]
task_chair_B[0].position = [1.4915393591900001, 9.26903664752021, 0.475]
task_chair_B[0].rotation = [0, 0, 0]
bench_desk_A[0].position = [3.8911456073071915, 10.057873825845736, 0.37]
bench_desk_A[0].rotation = [0, 0, 0]
toner_box_A[0].position = [0.7209709447454219, 10.267901356749507, 0.15]
toner_box_A[0].rotation = [0, 0, 0]
task_chair_C[0].position = [2.9551515217448623, 7.133808734899837, 0.475]
task_chair_C[0].rotation = [0, 0, 0]
task_chair_D[0].position = [7.458599505468221, 11.197830055959486, 0.475]
task_chair_D[0].rotation = [0, 0, 0]
high_storage_shelf_A[0].position = [1.6329939092793677, 6.134173271475431, 1.0]
high_storage_shelf_A[0].rotation = [0, 0, 0]
whiteboard_panel_A[0].position = [0.3891675269677666, 2.2129084223494813, 0.45]
whiteboard_panel_A[0].rotation = [0, 0, 0]
task_chair_E[0].position = [1.5921894078212482, 11.047065313625199, 0.475]
task_chair_E[0].rotation = [0, 0, 0]
computer_monitor_A[0].position = [3.487282976620923, 10.728191421474703, 0.225]
computer_monitor_A[0].rotation = [0, 0, 0]
task_chair_F[0].position = [3.2995129176195013, 1.0000751812872029, 0.475]
task_chair_F[0].rotation = [0, 0, 0]
potted_plant_small_A[0].position = [5.240233322606398, 10.001018659075072, 0.275]
potted_plant_small_A[0].rotation = [0, 0, 0]
bench_desk_B[0].position = [5.809308038316585, 3.8241907924068252, 0.37]
bench_desk_B[0].rotation = [0, 0, 0]
task_chair_G[0].position = [3.046872737424173, 0.8382863857196599, 0.475]
task_chair_G[0].rotation = [0, 0, 0]
ring_binder[0].position = [5.665407761641333, 7.1191605492214585, 0.03]
ring_binder[0].rotation = [0, 0, 0]
low_storage_credensa_A[0].position = [7.424285327172747, 5.936576405904376, 0.375]
low_storage_credensa_A[0].rotation = [0, 0, 0]
whiteboard_panel_B[0].position = [2.997302060513995, 6.231490549686223, 0.45]
whiteboard_panel_B[0].rotation = [0, 0, 0]
toner_box_B[0].position = [0.9707751767764343, 3.5836246227427044, 0.15]
toner_box_B[0].rotation = [0, 0, 0]
task_chair_H[0].position = [4.885114380298, 11.059973625970054, 0.475]
task_chair_H[0].rotation = [0, 0, 0]
task_chair_I[0].position = [7.408498741773121, 3.3646599040577154, 0.475]
task_chair_I[0].rotation = [0, 0, 0]
potted_plant_small_B[0].position = [1.9448039030266868, 9.192084597310151, 0.275]
potted_plant_small_B[0].rotation = [0, 0, 0]
side_collaboration_table[0].position = [1.7439517584010837, 5.873569929625213, 0.375]
side_collaboration_table[0].rotation = [0, 0, 0]
locker_unit[0].position = [0.8312425968483773, 1.84608263628335, 0.9]
locker_unit[0].rotation = [0, 0, 0]
file_box[0].position = [5.754237455790803, 5.732626740697576, 0.05]
file_box[0].rotation = [0, 0, 0]
task_chair_J[0].position = [7.23104971850746, 10.033668365665605, 0.475]
task_chair_J[0].rotation = [0, 0, 0]
printer_side_table_A[0].position = [2.6454030226392153, 9.650154103757613, 0.375]
printer_side_table_A[0].rotation = [0, 0, 0]
task_chair_K[0].position = [8.2410011345491, 5.267517599578934, 0.475]
task_chair_K[0].rotation = [0, 0, 0]
low_storage_credensa_B[0].position = [8.892194906528132, 8.263698926275474, 0.375]
low_storage_credensa_B[0].rotation = [0, 0, 0]
bench_desk_C[0].position = [4.916792722381073, 1.2528277094486455, 0.37]
bench_desk_C[0].rotation = [0, 0, 0]
bench_desk_D[0].position = [1.7042188794038957, 10.101532877685095, 0.37]
bench_desk_D[0].rotation = [0, 0, 0]
sticky_note_pad[0].position = [3.8152270788527454, 5.511233024553474, 0.04]
sticky_note_pad[0].rotation = [0, 0, 0]
collaboration_stool_B[0].position = [1.8283378901251746, 4.5231717678157946, 0.375]
collaboration_stool_B[0].rotation = [0, 0, 0]
task_chair_L[0].position = [4.8315570580623, 2.683244398106485, 0.475]
task_chair_L[0].rotation = [0, 0, 0]
task_chair_M[0].position = [1.5502633236086125, 8.47790887304844, 0.475]
task_chair_M[0].rotation = [0, 0, 0]
bench_desk_E[0].position = [5.15953553673905, 7.754311641044856, 0.37]
bench_desk_E[0].rotation = [0, 0, 0]
task_chair_N[0].position = [4.1770666329234, 2.518902455949098, 0.475]
task_chair_N[0].rotation = [0, 0, 0]
bench_desk_F[0].position = [1.2924932303536207, 0.749069274154373, 0.37]
bench_desk_F[0].rotation = [0, 0, 0]
printer_side_table_B[0].position = [7.376871330472779, 10.388956533634202, 0.375]
printer_side_table_B[0].rotation = [0, 0, 0]
task_chair_O[0].position = [3.96619910258761, 1.920444574420439, 0.475]
task_chair_O[0].rotation = [0, 0, 0]
computer_monitor_B[0].position = [1.7483446182137863, 5.214036678691247, 0.225]
computer_monitor_B[0].rotation = [0, 0, 0]
collaboration_stool_C[0].position = [4.678782788592239, 1.3328147444454523, 0.375]
collaboration_stool_C[0].rotation = [0, 0, 0]
computer_monitor_C[0].position = [5.229587318572235, 5.98893307855926, 0.225]
computer_monitor_C[0].rotation = [0, 0, 0]
potted_plant_small_C[0].position = [3.9328642858338103, 4.3069790717687635, 0.275]
potted_plant_small_C[0].rotation = [0, 0, 0]
low_storage_credensa_C[0].position = [0.9493122022304601, 9.249238136422207, 0.375]
low_storage_credensa_C[0].rotation = [0, 0, 0]
computer_monitor_D[0].position = [5.572746607349973, 3.3079404386691933, 0.225]
computer_monitor_D[0].rotation = [0, 0, 0]
task_chair_P[0].position = [2.892214720958132, 4.479284764611419, 0.475]
task_chair_P[0].rotation = [0, 0, 0]
task_chair_Q[0].position = [4.294671448188864, 7.006240113657547, 0.475]
task_chair_Q[0].rotation = [0, 0, 0]
task_chair_R[0].position = [8.107325616059384, 4.594560531733242, 0.475]
task_chair_R[0].rotation = [0, 0, 0]
high_storage_shelf_B[0].position = [8.76986056516241, 5.993092012312703, 1.0]
high_storage_shelf_B[0].rotation = [0, 0, 0]
collaboration_stool_A[0].position = [6.702192442549098, 9.413158117242226, 0.375]
collaboration_stool_A[0].rotation = [0, 0, 0]
task_chair_A[0].position = [2.7503572895137394, 7.440271639489538, 0.475]
task_chair_A[0].rotation = [0, 0, 0]
task_chair_B[0].position = [1.4915393591900001, 9.26903664752021, 0.475]
task_chair_B[0].rotation = [0, 0, 0]
bench_desk_A[0].position = [3.8911456073071915, 10.057873825845736, 0.37]
bench_desk_A[0].rotation = [0, 0, 0]
toner_box_A[0].position = [0.7209709447454219, 10.267901356749507, 0.15]
toner_box_A[0].rotation = [0, 0, 0]
task_chair_C[0].position = [2.9551515217448623, 7.133808734899837, 0.475]
task_chair_C[0].rotation = [0, 0, 0]
task_chair_D[0].position = [7.458599505468221, 11.197830055959486, 0.475]
task_chair_D[0].rotation = [0, 0, 0]
high_storage_shelf_A[0].position = [1.6329939092793677, 6.134173271475431, 1.0]
high_storage_shelf_A[0].rotation = [0, 0, 0]
whiteboard_panel_A[0].position = [0.3891675269677666, 2.2129084223494813, 0.45]
whiteboard_panel_A[0].rotation = [0, 0, 0]
task_chair_E[0].position = [1.5921894078212482, 11.047065313625199, 0.475]
task_chair_E[0].rotation = [0, 0, 0]
computer_monitor_A[0].position = [3.487282976620923, 10.728191421474703, 0.225]
computer_monitor_A[0].rotation = [0, 0, 0]
task_chair_F[0].position = [3.2995129176195013, 1.0000751812872029, 0.475]
task_chair_F[0].rotation = [0, 0, 0]
potted_plant_small_A[0].position = [5.240233322606398, 10.001018659075072, 0.275]
potted_plant_small_A[0].rotation = [0, 0, 0]
bench_desk_B[0].position = [5.809308038316585, 3.8241907924068252, 0.37]
bench_desk_B[0].rotation = [0, 0, 0]
task_chair_G[0].position = [3.046872737424173, 0.8382863857196599, 0.475]
task_chair_G[0].rotation = [0, 0, 0]
ring_binder[0].position = [5.665407761641333, 7.1191605492214585, 0.03]
ring_binder[0].rotation = [0, 0, 0]
low_storage_credensa_A[0].position = [7.424285327172747, 5.936576405904376, 0.375]
low_storage_credensa_A[0].rotation = [0, 0, 0]
whiteboard_panel_B[0].position = [2.997302060513995, 6.231490549686223, 0.45]
whiteboard_panel_B[0].rotation = [0, 0, 0]
toner_box_B[0].position = [0.9707751767764343, 3.5836246227427044, 0.15]
toner_box_B[0].rotation = [0, 0, 0]
task_chair_H[0].position = [4.885114380298, 11.059973625970054, 0.475]
task_chair_H[0].rotation = [0, 0, 0]
task_chair_I[0].position = [7.408498741773121, 3.3646599040577154, 0.475]
task_chair_I[0].rotation = [0, 0, 0]
potted_plant_small_B[0].position = [1.9448039030266868, 9.192084597310151, 0.275]
potted_plant_small_B[0].rotation = [0, 0, 0]
side_collaboration_table[0].position = [1.7439517584010837, 5.873569929625213, 0.375]
side_collaboration_table[0].rotation = [0, 0, 0]
locker_unit[0].position = [0.8312425968483773, 1.84608263628335, 0.9]
locker_unit[0].rotation = [0, 0, 0]
file_box[0].position = [5.754237455790803, 5.732626740697576, 0.05]
file_box[0].rotation = [0, 0, 0]
task_chair_J[0].position = [7.23104971850746, 10.033668365665605, 0.475]
task_chair_J[0].rotation = [0, 0, 0]
printer_side_table_A[0].position = [2.6454030226392153, 9.650154103757613, 0.375]
printer_side_table_A[0].rotation = [0, 0, 0]
task_chair_K[0].position = [8.2410011345491, 5.267517599578934, 0.475]
task_chair_K[0].rotation = [0, 0, 0]
low_storage_credensa_B[0].position = [8.892194906528132, 8.263698926275474, 0.375]
low_storage_credensa_B[0].rotation = [0, 0, 0]
bench_desk_C[0].position = [4.916792722381073, 1.2528277094486455, 0.37]
bench_desk_C[0].rotation = [0, 0, 0]
bench_desk_D[0].position = [1.7042188794038957, 10.101532877685095, 0.37]
bench_desk_D[0].rotation = [0, 0, 0]
sticky_note_pad[0].position = [3.8152270788527454, 5.511233024553474, 0.04]
sticky_note_pad[0].rotation = [0, 0, 0]
collaboration_stool_B[0].position = [1.8283378901251746, 4.5231717678157946, 0.375]
collaboration_stool_B[0].rotation = [0, 0, 0]
task_chair_L[0].position = [4.8315570580623, 2.683244398106485, 0.475]
task_chair_L[0].rotation = [0, 0, 0]
task_chair_M[0].position = [1.5502633236086125, 8.47790887304844, 0.475]
task_chair_M[0].rotation = [0, 0, 0]
bench_desk_E[0].position = [5.15953553673905, 7.754311641044856, 0.37]
bench_desk_E[0].rotation = [0, 0, 0]
task_chair_N[0].position = [4.1770666329234, 2.518902455949098, 0.475]
task_chair_N[0].rotation = [0, 0, 0]
bench_desk_F[0].position = [1.2924932303536207, 0.749069274154373, 0.37]
bench_desk_F[0].rotation = [0, 0, 0]
printer_side_table_B[0].position = [7.376871330472779, 10.388956533634202, 0.375]
printer_side_table_B[0].rotation = [0, 0, 0]
task_chair_O[0].position = [3.96619910258761, 1.920444574420439, 0.475]
task_chair_O[0].rotation = [0, 0, 0]
computer_monitor_B[0].position = [1.7483446182137863, 5.214036678691247, 0.225]
computer_monitor_B[0].rotation = [0, 0, 0]
collaboration_stool_C[0].position = [4.678782788592239, 1.3328147444454523, 0.375]
collaboration_stool_C[0].rotation = [0, 0, 0]
computer_monitor_C[0].position = [5.229587318572235, 5.98893307855926, 0.225]
computer_monitor_C[0].rotation = [0, 0, 0]
potted_plant_small_C[0].position = [3.9328642858338103, 4.3069790717687635, 0.275]
potted_plant_small_C[0].rotation = [0, 0, 0]
low_storage_credensa_C[0].position = [0.9493122022304601, 9.249238136422207, 0.375]
low_storage_credensa_C[0].rotation = [0, 0, 0]
computer_monitor_D[0].position = [5.572746607349973, 3.3079404386691933, 0.225]
computer_monitor_D[0].rotation = [0, 0, 0]
task_chair_P[0].position = [2.892214720958132, 4.479284764611419, 0.475]
task_chair_P[0].rotation = [0, 0, 0]
task_chair_Q[0].position = [4.294671448188864, 7.006240113657547, 0.475]
task_chair_Q[0].rotation = [0, 0, 0]
task_chair_R[0].position = [8.107325616059384, 4.594560531733242, 0.475]
task_chair_R[0].rotation = [0, 0, 0]
high_storage_shelf_B[0].position = [8.76986056516241, 5.993092012312703, 1.0]
high_storage_shelf_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed-point constraints below preserve the planned circulation lanes and prevent
# the solver from drifting furniture into any doorway. The east-side strip
# (approximately x >= 7.3) and the area in front of the south door remain clear.
def place_asset(asset, position, yaw):
    asset[0].position = list(position)
    asset[0].rotation = [0, 0, yaw]

    # Every asset receives a strong position constraint and an orientation constraint.
    solver.distance_constraint(
        asset[0],
        AssetInstance(position=list(position)),
        0,
        0,
        weight=10,
    )
    solver.align_with(
        asset[0],
        AssetInstance(rotation=[0, 0, yaw]),
        angle=0,
    )


# Six three-person workstations occupy the central area. Each desk's 1.60 m
# dimension runs east-west, leaving circulation around the perimeter.
place_asset(bench_desk_A, [1.60, 3.20, 0.37], radians(90))
place_asset(bench_desk_B, [4.00, 3.20, 0.37], radians(90))
place_asset(bench_desk_C, [6.40, 3.20, 0.37], radians(90))
place_asset(bench_desk_D, [1.60, 6.20, 0.37], radians(90))
place_asset(bench_desk_E, [4.00, 6.20, 0.37], radians(90))
place_asset(bench_desk_F, [6.40, 6.20, 0.37], radians(90))

# Three chairs serve each desk. Chairs on opposite sides face their desk,
# while adjacent chair centers remain far enough apart to avoid overlap.
place_asset(task_chair_A, [1.15, 2.30, 0.475], radians(90))
place_asset(task_chair_B, [2.05, 2.30, 0.475], radians(90))
place_asset(task_chair_C, [1.60, 4.10, 0.475], radians(270))

place_asset(task_chair_D, [3.55, 2.30, 0.475], radians(90))
place_asset(task_chair_E, [4.45, 2.30, 0.475], radians(90))
place_asset(task_chair_F, [4.00, 4.10, 0.475], radians(270))

place_asset(task_chair_G, [5.95, 2.30, 0.475], radians(90))
place_asset(task_chair_H, [6.85, 2.30, 0.475], radians(90))
place_asset(task_chair_I, [6.40, 4.10, 0.475], radians(270))

place_asset(task_chair_J, [1.15, 5.30, 0.475], radians(90))
place_asset(task_chair_K, [2.05, 5.30, 0.475], radians(90))
place_asset(task_chair_L, [1.60, 7.10, 0.475], radians(270))

place_asset(task_chair_M, [3.55, 5.30, 0.475], radians(90))
place_asset(task_chair_N, [4.45, 5.30, 0.475], radians(90))
place_asset(task_chair_O, [4.00, 7.10, 0.475], radians(270))

place_asset(task_chair_P, [5.95, 5.30, 0.475], radians(90))
place_asset(task_chair_Q, [6.85, 5.30, 0.475], radians(90))
place_asset(task_chair_R, [6.40, 7.10, 0.475], radians(270))

# Chair-to-desk constraints preserve usable workstation groupings if adjustment
# is required. Orientation constraints are listed before secondary distances.
chair_desk_pairs = [
    (task_chair_A, bench_desk_A), (task_chair_B, bench_desk_A),
    (task_chair_C, bench_desk_A),
    (task_chair_D, bench_desk_B), (task_chair_E, bench_desk_B),
    (task_chair_F, bench_desk_B),
    (task_chair_G, bench_desk_C), (task_chair_H, bench_desk_C),
    (task_chair_I, bench_desk_C),
    (task_chair_J, bench_desk_D), (task_chair_K, bench_desk_D),
    (task_chair_L, bench_desk_D),
    (task_chair_M, bench_desk_E), (task_chair_N, bench_desk_E),
    (task_chair_O, bench_desk_E),
    (task_chair_P, bench_desk_F), (task_chair_Q, bench_desk_F),
    (task_chair_R, bench_desk_F),
]
for chair_asset, desk_asset in chair_desk_pairs:
    solver.point_towards(chair_asset[0], desk_asset[0])
    solver.distance_constraint(
        chair_asset[0], desk_asset[0], 0.85, 1.10, weight=10
    )

# Keep all work surfaces parallel for an orderly and space-efficient layout.
for aligned_desk in [
    bench_desk_B, bench_desk_C, bench_desk_D,
    bench_desk_E, bench_desk_F,
]:
    solver.align_with(aligned_desk[0], bench_desk_A[0])

# Monitors are centered on four desks. Their center heights account for the
# 0.74 m desk tops and their own 0.45 m heights.
place_asset(computer_monitor_A, [1.60, 3.20, 0.965], radians(270))
place_asset(computer_monitor_B, [4.00, 3.20, 0.965], radians(270))
place_asset(computer_monitor_C, [1.60, 6.20, 0.965], radians(270))
place_asset(computer_monitor_D, [4.00, 6.20, 0.965], radians(270))

solver.on_top_of(computer_monitor_A[0], bench_desk_A[0])
solver.on_top_of(computer_monitor_B[0], bench_desk_B[0])
solver.on_top_of(computer_monitor_C[0], bench_desk_D[0])
solver.on_top_of(computer_monitor_D[0], bench_desk_E[0])
solver.point_towards(computer_monitor_A[0], task_chair_C[0])
solver.point_towards(computer_monitor_B[0], task_chair_F[0])
solver.point_towards(computer_monitor_C[0], task_chair_L[0])
solver.point_towards(computer_monitor_D[0], task_chair_O[0])

# The small note pad rests on the otherwise uncluttered sixth desk.
place_asset(sticky_note_pad, [6.40, 6.20, 0.78], radians(90))
solver.on_top_of(sticky_note_pad[0], bench_desk_F[0])
solver.align_with(sticky_note_pad[0], bench_desk_F[0])

# Low storage runs along the west wall, facing into the room. Its shallow
# depth avoids the nearby chair circulation zones.
place_asset(low_storage_credensa_A, [0.225, 1.00, 0.375], 0)
place_asset(low_storage_credensa_B, [0.225, 4.70, 0.375], 0)
place_asset(low_storage_credensa_C, [0.225, 7.70, 0.375], 0)

for west_credensa in [
    low_storage_credensa_A,
    low_storage_credensa_B,
    low_storage_credensa_C,
]:
    solver.against_wall(west_credensa[0], walls[5])

# Each plant is supported by a low credenza. In particular, plant A is placed
# on credenza A as required by the specified o0021/o0044 relationship.
place_asset(potted_plant_small_A, [0.225, 1.00, 1.025], 0)
place_asset(potted_plant_small_B, [0.225, 4.70, 1.025], 0)
place_asset(potted_plant_small_C, [0.225, 7.70, 1.025], 0)

solver.on_top_of(potted_plant_small_A[0], low_storage_credensa_A[0])
solver.on_top_of(potted_plant_small_B[0], low_storage_credensa_B[0])
solver.on_top_of(potted_plant_small_C[0], low_storage_credensa_C[0])
solver.align_with(potted_plant_small_A[0], low_storage_credensa_A[0])
solver.align_with(potted_plant_small_B[0], low_storage_credensa_B[0])
solver.align_with(potted_plant_small_C[0], low_storage_credensa_C[0])

# Filing items are placed on separate credenzas so they do not intersect plants.
place_asset(ring_binder, [0.225, 4.30, 0.78], 0)
place_asset(file_box, [0.225, 7.30, 0.80], 0)
solver.on_top_of(ring_binder[0], low_storage_credensa_B[0])
solver.on_top_of(file_box[0], low_storage_credensa_C[0])
solver.align_with(ring_binder[0], low_storage_credensa_B[0])
solver.align_with(file_box[0], low_storage_credensa_C[0])

# Tall shelves occupy the uninterrupted upper section of the west wall,
# away from all doors and from the north-wall windows.
place_asset(high_storage_shelf_A, [0.20, 9.20, 1.00], 0)
place_asset(high_storage_shelf_B, [0.20, 10.70, 1.00], 0)
solver.against_wall(high_storage_shelf_A[0], walls[5])
solver.against_wall(high_storage_shelf_B[0], walls[5])
solver.align_with(high_storage_shelf_B[0], high_storage_shelf_A[0])

# Wall-mounted whiteboards sit above the low cabinets, so their floor
# projections can coincide safely while their vertical volumes remain separate.
place_asset(whiteboard_panel_A, [0.02, 3.90, 1.50], 0)
place_asset(whiteboard_panel_B, [0.02, 6.50, 1.50], 0)
solver.against_wall(whiteboard_panel_A[0], walls[5])
solver.against_wall(whiteboard_panel_B[0], walls[5])
solver.align_with(whiteboard_panel_B[0], whiteboard_panel_A[0])

# The locker and printer carts use the south wall west of the 1.94 m doorway.
# Their long axes run along the wall and their fronts face into the room.
place_asset(locker_unit, [2.00, 0.225, 0.90], radians(90))
place_asset(printer_side_table_A, [4.00, 0.25, 0.375], radians(90))
place_asset(printer_side_table_B, [5.00, 0.25, 0.375], radians(90))
solver.against_wall(locker_unit[0], walls[0])
solver.against_wall(printer_side_table_A[0], walls[0])
solver.against_wall(printer_side_table_B[0], walls[0])
solver.align_with(printer_side_table_A[0], locker_unit[0])
solver.align_with(printer_side_table_B[0], locker_unit[0])

# Printers rest on their dedicated carts rather than occupying desk space.
place_asset(toner_box_A, [4.00, 0.25, 0.90], radians(90))
place_asset(toner_box_B, [5.00, 0.25, 0.90], radians(90))
solver.on_top_of(toner_box_A[0], printer_side_table_A[0])
solver.on_top_of(toner_box_B[0], printer_side_table_B[0])
solver.align_with(toner_box_A[0], printer_side_table_A[0])
solver.align_with(toner_box_B[0], printer_side_table_B[0])

# A compact collaboration setting occupies the open northwest/upper-central
# zone. It remains well away from the east and north doors.
place_asset(side_collaboration_table, [4.20, 9.30, 0.375], radians(90))
place_asset(collaboration_stool_A, [4.20, 8.55, 0.375], radians(90))
place_asset(collaboration_stool_B, [4.20, 10.05, 0.375], radians(270))
place_asset(collaboration_stool_C, [5.10, 9.30, 0.375], radians(180))

for collaboration_stool in [
    collaboration_stool_A,
    collaboration_stool_B,
    collaboration_stool_C,
]:
    solver.point_towards(
        collaboration_stool[0], side_collaboration_table[0]
    )
    solver.distance_constraint(
        collaboration_stool[0],
        side_collaboration_table[0],
        0.70,
        0.95,
        weight=10,
    )

solver.constraints = []
side_collaboration_table[0].position = [4.199999809265137, 9.300000190734863, 0.375]
side_collaboration_table[0].rotation = [0, 0, 1.5990706612064889]
side_collaboration_table[0].optimize = 2
task_chair_O[0].position = [4.0, 7.099999904632568, 0.4749999940395355]
task_chair_O[0].rotation = [0, 0, -1.5519467713960802]
task_chair_O[0].optimize = 2
potted_plant_small_A[0].position = [0.22499999403953552, 1.0, 1.024999976158142]
potted_plant_small_A[0].rotation = [0, 0, -3.838352584912997e-06]
potted_plant_small_A[0].optimize = 2
whiteboard_panel_A[0].position = [0.01999993994832039, 3.9000000953674316, 0.44999998807907104]
whiteboard_panel_A[0].rotation = [0, 0, 1.674736200745453e-06]
whiteboard_panel_A[0].optimize = 2
low_storage_credensa_A[0].position = [0.22500106692314148, 1.0, 0.375]
low_storage_credensa_A[0].rotation = [0, 0, 4.3000728093269244e-07]
low_storage_credensa_A[0].optimize = 2
high_storage_shelf_A[0].position = [0.6009538769721985, 9.199999809265137, 1.0]
high_storage_shelf_A[0].rotation = [0, 0, -1.5696353045277565]
high_storage_shelf_A[0].optimize = 2
low_storage_credensa_B[0].position = [0.22500114142894745, 4.699999809265137, 0.375]
low_storage_credensa_B[0].rotation = [0, 0, 2.6294402116163944e-06]
low_storage_credensa_B[0].optimize = 2
printer_side_table_B[0].position = [5.0, 0.2500004172325134, 0.375]
printer_side_table_B[0].rotation = [0, 0, 1.5707974630919284]
printer_side_table_B[0].optimize = 2
bench_desk_D[0].position = [1.600000023841858, 6.199999809265137, 0.3700000047683716]
bench_desk_D[0].rotation = [0, 0, 1.6179214228804735]
bench_desk_D[0].optimize = 2
task_chair_N[0].position = [4.449999809265137, 5.300000190734863, 0.4749999940395355]
task_chair_N[0].rotation = [0, 0, 1.586504290712113]
task_chair_N[0].optimize = 2
collaboration_stool_C[0].position = [5.099999904632568, 9.300000190734863, 0.375]
collaboration_stool_C[0].rotation = [0, 0, -3.125884689672577]
collaboration_stool_C[0].optimize = 2
computer_monitor_A[0].position = [1.600000023841858, 3.200000047683716, 0.9650000333786011]
computer_monitor_A[0].rotation = [0, 0, 1.0645092801745166]
computer_monitor_A[0].optimize = 2
bench_desk_A[0].position = [1.600000023841858, 3.200000047683716, 0.3700000047683716]
bench_desk_A[0].rotation = [0, 0, 1.617920218713948]
bench_desk_A[0].optimize = 2
task_chair_E[0].position = [4.449999809265137, 2.299999952316284, 0.4749999940395355]
task_chair_E[0].rotation = [0, 0, 1.586504290712113]
task_chair_E[0].optimize = 2
sticky_note_pad[0].position = [6.400000095367432, 6.199999809265137, 0.7800000309944153]
sticky_note_pad[0].rotation = [0, 0, 1.6179179872696128]
sticky_note_pad[0].optimize = 2
file_box[0].position = [0.22499999403953552, 7.300000190734863, 0.800000011920929]
file_box[0].rotation = [0, 0, 6.005873628448789e-06]
file_box[0].optimize = 2
task_chair_D[0].position = [3.549999952316284, 2.299999952316284, 0.4749999940395355]
task_chair_D[0].rotation = [0, 0, 1.586504290712113]
task_chair_D[0].optimize = 2
collaboration_stool_A[0].position = [4.199999809265137, 8.550000190734863, 0.375]
collaboration_stool_A[0].rotation = [0, 0, 1.586504290712113]
collaboration_stool_A[0].optimize = 2
task_chair_A[0].position = [1.149999976158142, 2.299999952316284, 0.4749999940395355]
task_chair_A[0].rotation = [0, 0, 1.586504290712113]
task_chair_A[0].optimize = 2
whiteboard_panel_B[0].position = [0.01999993994832039, 6.5, 0.44999998807907104]
whiteboard_panel_B[0].rotation = [0, 0, 1.674736200745453e-06]
whiteboard_panel_B[0].optimize = 2
low_storage_credensa_C[0].position = [0.22500114142894745, 7.699999809265137, 0.375]
low_storage_credensa_C[0].rotation = [0, 0, 2.6294402116163944e-06]
low_storage_credensa_C[0].optimize = 2
task_chair_R[0].position = [6.400000095367432, 7.099999904632568, 0.4749999940395355]
task_chair_R[0].rotation = [0, 0, -1.5550883628776802]
task_chair_R[0].optimize = 2
bench_desk_F[0].position = [6.400000095367432, 6.199999809265137, 0.3700000047683716]
bench_desk_F[0].rotation = [0, 0, 1.6179204870327983]
bench_desk_F[0].optimize = 2
task_chair_C[0].position = [1.600000023841858, 4.099999904632568, 0.4749999940395355]
task_chair_C[0].rotation = [0, 0, -1.5519467713960802]
task_chair_C[0].optimize = 2
ring_binder[0].position = [0.22499999403953552, 4.300000190734863, 0.7799999713897705]
ring_binder[0].rotation = [0, 0, 6.005873628448789e-06]
ring_binder[0].optimize = 2
potted_plant_small_C[0].position = [0.22499999403953552, 7.699999809265137, 1.024999976158142]
potted_plant_small_C[0].rotation = [0, 0, 6.005873628448789e-06]
potted_plant_small_C[0].optimize = 2
task_chair_K[0].position = [2.049999952316284, 5.300000190734863, 0.4749999940395355]
task_chair_K[0].rotation = [0, 0, 1.586504290712113]
task_chair_K[0].optimize = 2
collaboration_stool_B[0].position = [4.199999809265137, 10.050000190734863, 0.375]
collaboration_stool_B[0].rotation = [0, 0, -1.5550883628776802]
collaboration_stool_B[0].optimize = 2
computer_monitor_B[0].position = [4.0, 3.200000047683716, 0.9650000333786011]
computer_monitor_B[0].rotation = [0, 0, 1.0645092801745166]
computer_monitor_B[0].optimize = 2
task_chair_B[0].position = [2.049999952316284, 2.299999952316284, 0.4749999940395355]
task_chair_B[0].rotation = [0, 0, 1.586504290712113]
task_chair_B[0].optimize = 2
potted_plant_small_B[0].position = [0.22499999403953552, 4.699999809265137, 1.024999976158142]
potted_plant_small_B[0].rotation = [0, 0, 6.005873628448789e-06]
potted_plant_small_B[0].optimize = 2
computer_monitor_C[0].position = [1.600000023841858, 6.199999809265137, 0.9650000333786011]
computer_monitor_C[0].rotation = [0, 0, 1.0645092801745166]
computer_monitor_C[0].optimize = 2
task_chair_I[0].position = [6.400000095367432, 4.099999904632568, 0.4749999940395355]
task_chair_I[0].rotation = [0, 0, -1.5550883628776802]
task_chair_I[0].optimize = 2
task_chair_J[0].position = [1.149999976158142, 5.300000190734863, 0.4749999940395355]
task_chair_J[0].rotation = [0, 0, 1.586504290712113]
task_chair_J[0].optimize = 2
toner_box_B[0].position = [5.0, 0.25, 0.8999999761581421]
toner_box_B[0].rotation = [0, 0, 1.5707945027650105]
toner_box_B[0].optimize = 2
printer_side_table_A[0].position = [4.0, 0.2500004172325134, 0.375]
printer_side_table_A[0].rotation = [0, 0, 1.5707974630919284]
printer_side_table_A[0].optimize = 2
task_chair_H[0].position = [6.849999904632568, 2.299999952316284, 0.4749999940395355]
task_chair_H[0].rotation = [0, 0, 1.586504290712113]
task_chair_H[0].optimize = 2
task_chair_L[0].position = [1.600000023841858, 7.099999904632568, 0.4749999940395355]
task_chair_L[0].rotation = [0, 0, -1.5519467713960802]
task_chair_L[0].optimize = 2
bench_desk_E[0].position = [4.0, 6.199999809265137, 0.3700000047683716]
bench_desk_E[0].rotation = [0, 0, 1.6179214228804735]
bench_desk_E[0].optimize = 2
computer_monitor_D[0].position = [4.0, 6.199999809265137, 0.9650000333786011]
computer_monitor_D[0].rotation = [0, 0, 1.0645092801745166]
computer_monitor_D[0].optimize = 2
task_chair_G[0].position = [5.949999809265137, 2.299999952316284, 0.4749999940395355]
task_chair_G[0].rotation = [0, 0, 1.586504290712113]
task_chair_G[0].optimize = 2
task_chair_P[0].position = [5.949999809265137, 5.300000190734863, 0.4749999940395355]
task_chair_P[0].rotation = [0, 0, 1.586504290712113]
task_chair_P[0].optimize = 2
bench_desk_B[0].position = [4.0, 3.200000047683716, 0.3700000047683716]
bench_desk_B[0].rotation = [0, 0, 1.6179214228804735]
bench_desk_B[0].optimize = 2
high_storage_shelf_B[0].position = [0.19999969005584717, 10.699999809265137, 1.0]
high_storage_shelf_B[0].rotation = [0, 0, 1.6709178942621475e-06]
high_storage_shelf_B[0].optimize = 2
locker_unit[0].position = [2.0, 0.22500106692314148, 0.8999999761581421]
locker_unit[0].rotation = [0, 0, 1.5707967483904433]
locker_unit[0].optimize = 2
task_chair_Q[0].position = [6.849999904632568, 5.300000190734863, 0.4749999940395355]
task_chair_Q[0].rotation = [0, 0, 1.586504290712113]
task_chair_Q[0].optimize = 2
task_chair_M[0].position = [3.549999952316284, 5.300000190734863, 0.4749999940395355]
task_chair_M[0].rotation = [0, 0, 1.586504290712113]
task_chair_M[0].optimize = 2
toner_box_A[0].position = [4.0, 0.25, 0.8999999761581421]
toner_box_A[0].rotation = [0, 0, 1.5707945027650105]
toner_box_A[0].optimize = 2
bench_desk_C[0].position = [6.400000095367432, 3.200000047683716, 0.3700000047683716]
bench_desk_C[0].rotation = [0, 0, 1.6179211621518739]
bench_desk_C[0].optimize = 2
task_chair_F[0].position = [4.0, 4.099999904632568, 0.4749999940395355]
task_chair_F[0].rotation = [0, 0, -1.5519467713960802]
task_chair_F[0].optimize = 2

