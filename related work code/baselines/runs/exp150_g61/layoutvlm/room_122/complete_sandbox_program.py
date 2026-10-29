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
collaboration_stool_A = Assets(description="A stool with a metal leg and foot rest with a round black cushion.", size=[0.45, 0.45, 0.76], placements=[AssetInstance() for _ in range(1)])
task_chair_A = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.66, 0.66, 1.02], placements=[AssetInstance() for _ in range(1)])
task_chair_B = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.66, 0.66, 1.02], placements=[AssetInstance() for _ in range(1)])
bench_desk_A = Assets(description="A brown, rectangular table with four, grey legs.", size=[1.20, 2.40, 0.74], placements=[AssetInstance() for _ in range(1)])
toner_box_A = Assets(description="Black plastic printer with buttons at the top.", size=[0.42, 0.45, 0.30], placements=[AssetInstance() for _ in range(1)])
task_chair_C = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.66, 0.66, 1.02], placements=[AssetInstance() for _ in range(1)])
task_chair_D = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.66, 0.66, 1.02], placements=[AssetInstance() for _ in range(1)])
high_storage_shelf_A = Assets(description="It is a tall set of shelves made of wood and metal.", size=[0.40, 0.90, 1.90], placements=[AssetInstance() for _ in range(1)])
whiteboard_panel_A = Assets(description="A white rectangular poster with black blue and orange marks and irregular writing.", size=[0.03, 1.80, 1.20], placements=[AssetInstance() for _ in range(1)])
task_chair_E = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.66, 0.66, 1.02], placements=[AssetInstance() for _ in range(1)])
computer_monitor_A = Assets(description="a flat screen monitor on a stand.", size=[0.22, 0.61, 0.45], placements=[AssetInstance() for _ in range(1)])
task_chair_F = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.66, 0.66, 1.02], placements=[AssetInstance() for _ in range(1)])
potted_plant_small_A = Assets(description="A bunch of big leaves inside of a white pot.", size=[0.40, 0.40, 0.50], placements=[AssetInstance() for _ in range(1)])
bench_desk_B = Assets(description="A brown, rectangular table with four, grey legs.", size=[1.20, 2.40, 0.74], placements=[AssetInstance() for _ in range(1)])
task_chair_G = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.66, 0.66, 1.02], placements=[AssetInstance() for _ in range(1)])
ring_binder = Assets(description="A brown book with silver corners.", size=[0.28, 0.08, 0.32], placements=[AssetInstance() for _ in range(1)])
low_storage_credensa_A = Assets(description="A black cabinet with grey doors.", size=[0.45, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
whiteboard_panel_B = Assets(description="A white rectangular poster with black blue and orange marks and irregular writing.", size=[0.03, 1.80, 1.20], placements=[AssetInstance() for _ in range(1)])
toner_box_B = Assets(description="Black plastic printer with buttons at the top.", size=[0.42, 0.45, 0.30], placements=[AssetInstance() for _ in range(1)])
task_chair_H = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.66, 0.66, 1.02], placements=[AssetInstance() for _ in range(1)])
task_chair_I = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.66, 0.66, 1.02], placements=[AssetInstance() for _ in range(1)])
potted_plant_small_B = Assets(description="A bunch of big leaves inside of a white pot.", size=[0.40, 0.40, 0.50], placements=[AssetInstance() for _ in range(1)])
side_collaboration_table = Assets(description="A brown, oval table.", size=[0.85, 1.60, 1.05], placements=[AssetInstance() for _ in range(1)])
locker_unit = Assets(description="A large black filing cabinet with 5 drawers down and 4 across.", size=[0.50, 1.60, 1.80], placements=[AssetInstance() for _ in range(1)])
file_box = Assets(description="A brown book with silver corners.", size=[0.28, 0.10, 0.32], placements=[AssetInstance() for _ in range(1)])
task_chair_J = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.66, 0.66, 1.02], placements=[AssetInstance() for _ in range(1)])
printer_side_table_A = Assets(description="A black frame metal stand with two wooden shelves and four caster wheels.", size=[0.55, 0.60, 0.70], placements=[AssetInstance() for _ in range(1)])
task_chair_K = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.66, 0.66, 1.02], placements=[AssetInstance() for _ in range(1)])
low_storage_credensa_B = Assets(description="A black cabinet with grey doors.", size=[0.45, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
bench_desk_C = Assets(description="A brown, rectangular table with four, grey legs.", size=[1.20, 2.40, 0.74], placements=[AssetInstance() for _ in range(1)])
bench_desk_D = Assets(description="A brown, rectangular table with four, grey legs.", size=[1.20, 2.40, 0.74], placements=[AssetInstance() for _ in range(1)])
sticky_note_pad = Assets(description="A box of kleenix wipes.", size=[0.12, 0.23, 0.09], placements=[AssetInstance() for _ in range(1)])
collaboration_stool_B = Assets(description="A stool with a metal leg and foot rest with a round black cushion.", size=[0.45, 0.45, 0.76], placements=[AssetInstance() for _ in range(1)])
task_chair_L = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.66, 0.66, 1.02], placements=[AssetInstance() for _ in range(1)])
task_chair_M = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.66, 0.66, 1.02], placements=[AssetInstance() for _ in range(1)])
bench_desk_E = Assets(description="A brown, rectangular table with four, grey legs.", size=[1.20, 2.40, 0.74], placements=[AssetInstance() for _ in range(1)])
task_chair_N = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.66, 0.66, 1.02], placements=[AssetInstance() for _ in range(1)])
bench_desk_F = Assets(description="A brown, rectangular table with four, grey legs.", size=[1.20, 2.40, 0.74], placements=[AssetInstance() for _ in range(1)])
printer_side_table_B = Assets(description="A black frame metal stand with two wooden shelves and four caster wheels.", size=[0.55, 0.60, 0.70], placements=[AssetInstance() for _ in range(1)])
task_chair_O = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.66, 0.66, 1.02], placements=[AssetInstance() for _ in range(1)])
computer_monitor_B = Assets(description="a flat screen monitor on a stand.", size=[0.22, 0.61, 0.45], placements=[AssetInstance() for _ in range(1)])
collaboration_stool_C = Assets(description="A stool with a metal leg and foot rest with a round black cushion.", size=[0.45, 0.45, 0.76], placements=[AssetInstance() for _ in range(1)])
computer_monitor_C = Assets(description="a flat screen monitor on a stand.", size=[0.22, 0.61, 0.45], placements=[AssetInstance() for _ in range(1)])
potted_plant_small_C = Assets(description="A bunch of big leaves inside of a white pot.", size=[0.40, 0.40, 0.50], placements=[AssetInstance() for _ in range(1)])
low_storage_credensa_C = Assets(description="A black cabinet with grey doors.", size=[0.45, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
computer_monitor_D = Assets(description="a flat screen monitor on a stand.", size=[0.22, 0.61, 0.45], placements=[AssetInstance() for _ in range(1)])
task_chair_P = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.66, 0.66, 1.02], placements=[AssetInstance() for _ in range(1)])
task_chair_Q = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.66, 0.66, 1.02], placements=[AssetInstance() for _ in range(1)])
task_chair_R = Assets(description="A dark grey fabric office chair with five independent rolling wheels and short skeleton-frame arm rests.", size=[0.66, 0.66, 1.02], placements=[AssetInstance() for _ in range(1)])
high_storage_shelf_B = Assets(description="It is a tall set of shelves made of wood and metal.", size=[0.40, 0.90, 1.90], placements=[AssetInstance() for _ in range(1)])

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

collaboration_stool_A[0].position = [7.78641736602656, 8.36651396468225, 0.38]
collaboration_stool_A[0].rotation = [0, 0, 0]
task_chair_A[0].position = [2.1981734042736503, 7.751628004034901, 0.51]
task_chair_A[0].rotation = [0, 0, 0]
task_chair_B[0].position = [5.548728044387622, 7.298569296881467, 0.51]
task_chair_B[0].rotation = [0, 0, 0]
bench_desk_A[0].position = [1.288414756124189, 6.521995218054787, 0.37]
bench_desk_A[0].rotation = [0, 0, 0]
toner_box_A[0].position = [3.47317388960599, 2.4329339488764425, 0.15]
toner_box_A[0].rotation = [0, 0, 0]
task_chair_C[0].position = [2.4401477738412205, 9.743127288509493, 0.51]
task_chair_C[0].rotation = [0, 0, 0]
task_chair_D[0].position = [3.7069249242527627, 5.899438162254988, 0.51]
task_chair_D[0].rotation = [0, 0, 0]
high_storage_shelf_A[0].position = [1.2585644460799008, 8.400600188735947, 0.95]
high_storage_shelf_A[0].rotation = [0, 0, 0]
whiteboard_panel_A[0].position = [4.9510027842850075, 5.801592693096342, 0.6]
whiteboard_panel_A[0].rotation = [0, 0, 0]
task_chair_E[0].position = [6.368025251420473, 8.387215455795248, 0.51]
task_chair_E[0].rotation = [0, 0, 0]
computer_monitor_A[0].position = [3.111154906229217, 3.5528274437738125, 0.225]
computer_monitor_A[0].rotation = [0, 0, 0]
task_chair_F[0].position = [8.086075286475207, 0.22236591433260156, 0.51]
task_chair_F[0].rotation = [0, 0, 0]
potted_plant_small_A[0].position = [7.229059011212001, 1.086106374754885, 0.25]
potted_plant_small_A[0].rotation = [0, 0, 0]
bench_desk_B[0].position = [2.4941065201800425, 8.984769372679361, 0.37]
bench_desk_B[0].rotation = [0, 0, 0]
task_chair_G[0].position = [2.070125214815974, 3.8664466025078266, 0.51]
task_chair_G[0].rotation = [0, 0, 0]
ring_binder[0].position = [1.4330274259171998, 3.88690479182624, 0.16]
ring_binder[0].rotation = [0, 0, 0]
low_storage_credensa_A[0].position = [7.382920550755179, 6.427096851622892, 0.375]
low_storage_credensa_A[0].rotation = [0, 0, 0]
whiteboard_panel_B[0].position = [7.4981019677067415, 10.242617907577827, 0.6]
whiteboard_panel_B[0].rotation = [0, 0, 0]
toner_box_B[0].position = [6.108356993961793, 4.595509456361723, 0.15]
toner_box_B[0].rotation = [0, 0, 0]
task_chair_H[0].position = [6.264044655383215, 0.19372191859056453, 0.51]
task_chair_H[0].rotation = [0, 0, 0]
task_chair_I[0].position = [6.171172217165791, 11.807306543592896, 0.51]
task_chair_I[0].rotation = [0, 0, 0]
potted_plant_small_B[0].position = [6.409547681426656, 1.6573327961553614, 0.25]
potted_plant_small_B[0].rotation = [0, 0, 0]
side_collaboration_table[0].position = [2.738206546597479, 5.839546679833019, 0.525]
side_collaboration_table[0].rotation = [0, 0, 0]
locker_unit[0].position = [6.924847330984815, 9.01085377372665, 0.9]
locker_unit[0].rotation = [0, 0, 0]
file_box[0].position = [5.612367136862008, 0.6819991241817469, 0.16]
file_box[0].rotation = [0, 0, 0]
task_chair_J[0].position = [0.6361081963308566, 1.469581203832269, 0.51]
task_chair_J[0].rotation = [0, 0, 0]
printer_side_table_A[0].position = [1.561970293331646, 1.909883971351543, 0.35]
printer_side_table_A[0].rotation = [0, 0, 0]
task_chair_K[0].position = [5.207157170753256, 3.9372346734208765, 0.51]
task_chair_K[0].rotation = [0, 0, 0]
low_storage_credensa_B[0].position = [1.740952668006773, 4.590541391418435, 0.375]
low_storage_credensa_B[0].rotation = [0, 0, 0]
bench_desk_C[0].position = [2.96467484405326, 7.753479339445345, 0.37]
bench_desk_C[0].rotation = [0, 0, 0]
bench_desk_D[0].position = [0.7181152372648201, 10.805668366712744, 0.37]
bench_desk_D[0].rotation = [0, 0, 0]
sticky_note_pad[0].position = [1.7659661514887057, 11.465900566151955, 0.045]
sticky_note_pad[0].rotation = [0, 0, 0]
collaboration_stool_B[0].position = [8.27675256503275, 3.4308607569627574, 0.38]
collaboration_stool_B[0].rotation = [0, 0, 0]
task_chair_L[0].position = [7.05746345154671, 3.654150290103726, 0.51]
task_chair_L[0].rotation = [0, 0, 0]
task_chair_M[0].position = [6.860652158166159, 8.331536312273604, 0.51]
task_chair_M[0].rotation = [0, 0, 0]
bench_desk_E[0].position = [4.49245965401241, 3.1837616798844404, 0.37]
bench_desk_E[0].rotation = [0, 0, 0]
task_chair_N[0].position = [4.844606392598365, 5.153944453219506, 0.51]
task_chair_N[0].rotation = [0, 0, 0]
bench_desk_F[0].position = [0.9691136091875867, 3.531026372797362, 0.37]
bench_desk_F[0].rotation = [0, 0, 0]
printer_side_table_B[0].position = [6.533756966217086, 4.7360981736578704, 0.35]
printer_side_table_B[0].rotation = [0, 0, 0]
task_chair_O[0].position = [5.741476537854871, 1.9178972184030765, 0.51]
task_chair_O[0].rotation = [0, 0, 0]
computer_monitor_B[0].position = [4.286901353683342, 7.667358910256938, 0.225]
computer_monitor_B[0].rotation = [0, 0, 0]
collaboration_stool_C[0].position = [6.8887627232202515, 10.369248854077354, 0.38]
collaboration_stool_C[0].rotation = [0, 0, 0]
computer_monitor_C[0].position = [6.137492473094609, 0.08026593631528556, 0.225]
computer_monitor_C[0].rotation = [0, 0, 0]
potted_plant_small_C[0].position = [1.591600827088624, 0.8675049754453021, 0.25]
potted_plant_small_C[0].rotation = [0, 0, 0]
low_storage_credensa_C[0].position = [7.916604065653699, 0.6995740746629311, 0.375]
low_storage_credensa_C[0].rotation = [0, 0, 0]
computer_monitor_D[0].position = [7.694129551130838, 7.572160666500759, 0.225]
computer_monitor_D[0].rotation = [0, 0, 0]
task_chair_P[0].position = [7.6929291963264435, 10.013317300295776, 0.51]
task_chair_P[0].rotation = [0, 0, 0]
task_chair_Q[0].position = [3.580647372359488, 2.3845138014461464, 0.51]
task_chair_Q[0].rotation = [0, 0, 0]
task_chair_R[0].position = [2.633856419046528, 4.979962699368386, 0.51]
task_chair_R[0].rotation = [0, 0, 0]
high_storage_shelf_B[0].position = [1.7588722044212246, 0.18810701407870445, 0.95]
high_storage_shelf_B[0].rotation = [0, 0, 0]
collaboration_stool_A[0].position = [7.78641736602656, 8.36651396468225, 0.38]
collaboration_stool_A[0].rotation = [0, 0, 0]
task_chair_A[0].position = [2.1981734042736503, 7.751628004034901, 0.51]
task_chair_A[0].rotation = [0, 0, 0]
task_chair_B[0].position = [5.548728044387622, 7.298569296881467, 0.51]
task_chair_B[0].rotation = [0, 0, 0]
bench_desk_A[0].position = [1.288414756124189, 6.521995218054787, 0.37]
bench_desk_A[0].rotation = [0, 0, 0]
toner_box_A[0].position = [3.47317388960599, 2.4329339488764425, 0.15]
toner_box_A[0].rotation = [0, 0, 0]
task_chair_C[0].position = [2.4401477738412205, 9.743127288509493, 0.51]
task_chair_C[0].rotation = [0, 0, 0]
task_chair_D[0].position = [3.7069249242527627, 5.899438162254988, 0.51]
task_chair_D[0].rotation = [0, 0, 0]
high_storage_shelf_A[0].position = [1.2585644460799008, 8.400600188735947, 0.95]
high_storage_shelf_A[0].rotation = [0, 0, 0]
whiteboard_panel_A[0].position = [4.9510027842850075, 5.801592693096342, 0.6]
whiteboard_panel_A[0].rotation = [0, 0, 0]
task_chair_E[0].position = [6.368025251420473, 8.387215455795248, 0.51]
task_chair_E[0].rotation = [0, 0, 0]
computer_monitor_A[0].position = [3.111154906229217, 3.5528274437738125, 0.225]
computer_monitor_A[0].rotation = [0, 0, 0]
task_chair_F[0].position = [8.086075286475207, 0.22236591433260156, 0.51]
task_chair_F[0].rotation = [0, 0, 0]
potted_plant_small_A[0].position = [7.229059011212001, 1.086106374754885, 0.25]
potted_plant_small_A[0].rotation = [0, 0, 0]
bench_desk_B[0].position = [2.4941065201800425, 8.984769372679361, 0.37]
bench_desk_B[0].rotation = [0, 0, 0]
task_chair_G[0].position = [2.070125214815974, 3.8664466025078266, 0.51]
task_chair_G[0].rotation = [0, 0, 0]
ring_binder[0].position = [1.4330274259171998, 3.88690479182624, 0.16]
ring_binder[0].rotation = [0, 0, 0]
low_storage_credensa_A[0].position = [7.382920550755179, 6.427096851622892, 0.375]
low_storage_credensa_A[0].rotation = [0, 0, 0]
whiteboard_panel_B[0].position = [7.4981019677067415, 10.242617907577827, 0.6]
whiteboard_panel_B[0].rotation = [0, 0, 0]
toner_box_B[0].position = [6.108356993961793, 4.595509456361723, 0.15]
toner_box_B[0].rotation = [0, 0, 0]
task_chair_H[0].position = [6.264044655383215, 0.19372191859056453, 0.51]
task_chair_H[0].rotation = [0, 0, 0]
task_chair_I[0].position = [6.171172217165791, 11.807306543592896, 0.51]
task_chair_I[0].rotation = [0, 0, 0]
potted_plant_small_B[0].position = [6.409547681426656, 1.6573327961553614, 0.25]
potted_plant_small_B[0].rotation = [0, 0, 0]
side_collaboration_table[0].position = [2.738206546597479, 5.839546679833019, 0.525]
side_collaboration_table[0].rotation = [0, 0, 0]
locker_unit[0].position = [6.924847330984815, 9.01085377372665, 0.9]
locker_unit[0].rotation = [0, 0, 0]
file_box[0].position = [5.612367136862008, 0.6819991241817469, 0.16]
file_box[0].rotation = [0, 0, 0]
task_chair_J[0].position = [0.6361081963308566, 1.469581203832269, 0.51]
task_chair_J[0].rotation = [0, 0, 0]
printer_side_table_A[0].position = [1.561970293331646, 1.909883971351543, 0.35]
printer_side_table_A[0].rotation = [0, 0, 0]
task_chair_K[0].position = [5.207157170753256, 3.9372346734208765, 0.51]
task_chair_K[0].rotation = [0, 0, 0]
low_storage_credensa_B[0].position = [1.740952668006773, 4.590541391418435, 0.375]
low_storage_credensa_B[0].rotation = [0, 0, 0]
bench_desk_C[0].position = [2.96467484405326, 7.753479339445345, 0.37]
bench_desk_C[0].rotation = [0, 0, 0]
bench_desk_D[0].position = [0.7181152372648201, 10.805668366712744, 0.37]
bench_desk_D[0].rotation = [0, 0, 0]
sticky_note_pad[0].position = [1.7659661514887057, 11.465900566151955, 0.045]
sticky_note_pad[0].rotation = [0, 0, 0]
collaboration_stool_B[0].position = [8.27675256503275, 3.4308607569627574, 0.38]
collaboration_stool_B[0].rotation = [0, 0, 0]
task_chair_L[0].position = [7.05746345154671, 3.654150290103726, 0.51]
task_chair_L[0].rotation = [0, 0, 0]
task_chair_M[0].position = [6.860652158166159, 8.331536312273604, 0.51]
task_chair_M[0].rotation = [0, 0, 0]
bench_desk_E[0].position = [4.49245965401241, 3.1837616798844404, 0.37]
bench_desk_E[0].rotation = [0, 0, 0]
task_chair_N[0].position = [4.844606392598365, 5.153944453219506, 0.51]
task_chair_N[0].rotation = [0, 0, 0]
bench_desk_F[0].position = [0.9691136091875867, 3.531026372797362, 0.37]
bench_desk_F[0].rotation = [0, 0, 0]
printer_side_table_B[0].position = [6.533756966217086, 4.7360981736578704, 0.35]
printer_side_table_B[0].rotation = [0, 0, 0]
task_chair_O[0].position = [5.741476537854871, 1.9178972184030765, 0.51]
task_chair_O[0].rotation = [0, 0, 0]
computer_monitor_B[0].position = [4.286901353683342, 7.667358910256938, 0.225]
computer_monitor_B[0].rotation = [0, 0, 0]
collaboration_stool_C[0].position = [6.8887627232202515, 10.369248854077354, 0.38]
collaboration_stool_C[0].rotation = [0, 0, 0]
computer_monitor_C[0].position = [6.137492473094609, 0.08026593631528556, 0.225]
computer_monitor_C[0].rotation = [0, 0, 0]
potted_plant_small_C[0].position = [1.591600827088624, 0.8675049754453021, 0.25]
potted_plant_small_C[0].rotation = [0, 0, 0]
low_storage_credensa_C[0].position = [7.916604065653699, 0.6995740746629311, 0.375]
low_storage_credensa_C[0].rotation = [0, 0, 0]
computer_monitor_D[0].position = [7.694129551130838, 7.572160666500759, 0.225]
computer_monitor_D[0].rotation = [0, 0, 0]
task_chair_P[0].position = [7.6929291963264435, 10.013317300295776, 0.51]
task_chair_P[0].rotation = [0, 0, 0]
task_chair_Q[0].position = [3.580647372359488, 2.3845138014461464, 0.51]
task_chair_Q[0].rotation = [0, 0, 0]
task_chair_R[0].position = [2.633856419046528, 4.979962699368386, 0.51]
task_chair_R[0].rotation = [0, 0, 0]
high_storage_shelf_B[0].position = [1.7588722044212246, 0.18810701407870445, 0.95]
high_storage_shelf_B[0].rotation = [0, 0, 0]

solver.constraints = []

# The marked plan uses coordinates 0..9 by 0..12.
# Keep the east side clear for circulation and all five door approaches.
# Fixed-point constraints preserve the deliberately separated furniture footprints.
def place_asset(asset, x, y, yaw=0, z=None):
    inst = asset[0]
    if z is None:
        z = asset.size[2] / 2
    inst.position = [x, y, z]
    inst.rotation = [0, 0, radians(yaw)]
    reference = AssetInstance(
        position=[x, y, z],
        rotation=[0, 0, radians(yaw)]
    )
    solver.distance_constraint(inst, reference, 0, 0, weight=10)
    solver.align_with(inst, reference)
    return inst


# Six worktables: three rows, two columns. The long dimension runs north-south.
desk_layout = [
    (bench_desk_A, 1.80, 2.50),
    (bench_desk_B, 5.40, 2.50),
    (bench_desk_C, 1.80, 5.80),
    (bench_desk_D, 5.40, 5.80),
    (bench_desk_E, 1.80, 9.10),
    (bench_desk_F, 5.40, 9.10),
]
for desk_asset, dx, dy in desk_layout:
    place_asset(desk_asset, dx, dy)

# Three seats per table. Chairs remain fully outside the table footprints;
# the opposing seats are staggered to provide useful working space.
chair_groups = [
    (task_chair_A, task_chair_B, task_chair_C),
    (task_chair_D, task_chair_E, task_chair_F),
    (task_chair_G, task_chair_H, task_chair_I),
    (task_chair_J, task_chair_K, task_chair_L),
    (task_chair_M, task_chair_N, task_chair_O),
    (task_chair_P, task_chair_Q, task_chair_R),
]
for (desk_asset, dx, dy), seats in zip(desk_layout, chair_groups):
    for seat_asset, offset_x, offset_y, yaw in [
        (seats[0], -1.05, -0.65, 0),
        (seats[1], -1.05,  0.65, 0),
        (seats[2],  1.05,  0.00, 180),
    ]:
        place_asset(seat_asset, dx + offset_x, dy + offset_y, yaw)
        solver.distance_constraint(
            seat_asset[0], desk_asset[0], 1.0, 1.35, weight=10
        )
        solver.align_with(seat_asset[0], desk_asset[0], angle=yaw)

# Low cabinets along the south wall, well west of the entrance.
# Rotation 90 makes their shallow depth run north-south.
for cabinet_asset, cx in [
    (low_storage_credensa_A, 1.15),
    (low_storage_credensa_B, 2.80),
    (low_storage_credensa_C, 4.45),
]:
    place_asset(cabinet_asset, cx, 0.225, 90)
    solver.against_wall(cabinet_asset[0], walls[0])

place_asset(locker_unit, 6.15, 0.25, 90)
solver.against_wall(locker_unit[0], walls[0])

# Tall shelving occupies west-wall corners, not the window wall.
place_asset(high_storage_shelf_A, 0.20, 0.55)
place_asset(high_storage_shelf_B, 0.20, 11.40)
solver.against_wall(high_storage_shelf_A[0], walls[5])
solver.against_wall(high_storage_shelf_B[0], walls[5])

# Printers sit on dedicated stands in gaps between the west-side seats.
place_asset(printer_side_table_A, 0.275, 7.50)
place_asset(printer_side_table_B, 0.275, 10.60)
solver.against_wall(printer_side_table_A[0], walls[5])
solver.against_wall(printer_side_table_B[0], walls[5])

for printer_asset, stand_asset in [
    (toner_box_A, printer_side_table_A),
    (toner_box_B, printer_side_table_B),
]:
    stand_position = stand_asset[0].position
    place_asset(
        printer_asset, stand_position[0], stand_position[1],
        z=stand_asset.size[2] + printer_asset.size[2] / 2
    )
    solver.on_top_of(printer_asset[0], stand_asset[0])
    solver.align_with(printer_asset[0], stand_asset[0])

# Wall-mounted boards clear the chairs vertically and face into the room.
for board_asset, by in [
    (whiteboard_panel_A, 5.80),
    (whiteboard_panel_B, 9.10),
]:
    place_asset(board_asset, 0.015, by, z=1.70)
    solver.against_wall(board_asset[0], walls[5])

# A small collaboration area at the north end leaves the northeast door
# and the east-side access route unobstructed.
place_asset(side_collaboration_table, 4.00, 11.15, 90)
for stool_asset, sx, sy, yaw in [
    (collaboration_stool_A, 2.55, 11.15, 0),
    (collaboration_stool_B, 5.45, 11.15, 180),
    (collaboration_stool_C, 4.00, 10.35, 90),
]:
    place_asset(stool_asset, sx, sy, yaw)
    solver.point_towards(stool_asset[0], side_collaboration_table[0])
    solver.distance_constraint(
        stool_asset[0], side_collaboration_table[0], 0.80, 1.55
    )

# Monitors are supported by the worktops, facing the west-side users.
# Each occupies a separate patch of tabletop.
for monitor_asset, desk_asset in [
    (computer_monitor_A, bench_desk_A),
    (computer_monitor_B, bench_desk_B),
    (computer_monitor_C, bench_desk_C),
    (computer_monitor_D, bench_desk_D),
]:
    desk_position = desk_asset[0].position
    place_asset(
        monitor_asset,
        desk_position[0] - 0.05,
        desk_position[1] - 0.65,
        180,
        z=desk_asset.size[2] + monitor_asset.size[2] / 2,
    )
    solver.on_top_of(monitor_asset[0], desk_asset[0])
    solver.align_with(monitor_asset[0], desk_asset[0], angle=180)

# All plants, including the requested small plant, are on low credenzas.
for plant_asset, cabinet_asset in [
    (potted_plant_small_A, low_storage_credensa_A),
    (potted_plant_small_B, low_storage_credensa_B),
    (potted_plant_small_C, low_storage_credensa_C),
]:
    cabinet_position = cabinet_asset[0].position
    place_asset(
        plant_asset, cabinet_position[0], cabinet_position[1], 90,
        z=cabinet_asset.size[2] + plant_asset.size[2] / 2,
    )
    solver.on_top_of(plant_asset[0], cabinet_asset[0])
    solver.align_with(plant_asset[0], cabinet_asset[0])

# Upright files are supported on the two shelving units.
for book_asset, shelf_asset in [
    (ring_binder, high_storage_shelf_A),
    (file_box, high_storage_shelf_B),
]:
    shelf_position = shelf_asset[0].position
    place_asset(
        book_asset, shelf_position[0], shelf_position[1],
        z=shelf_asset.size[2] + book_asset.size[2] / 2,
    )
    solver.on_top_of(book_asset[0], shelf_asset[0])
    solver.align_with(book_asset[0], shelf_asset[0])

# Keep the tissue/note accessory on an otherwise clear desk surface.
place_asset(
    sticky_note_pad, 1.80, 9.70,
    z=bench_desk_E.size[2] + sticky_note_pad.size[2] / 2,
)
solver.on_top_of(sticky_note_pad[0], bench_desk_E[0])
solver.align_with(sticky_note_pad[0], bench_desk_E[0])

solver.constraints = []
low_storage_credensa_A[0].position = [1.149999976158142, 0.22783564031124115, 0.375]
low_storage_credensa_A[0].rotation = [0, 0, 1.5665759855500025]
low_storage_credensa_A[0].optimize = 2
computer_monitor_B[0].position = [5.349999904632568, 1.850000023841858, 0.9650000333786011]
computer_monitor_B[0].rotation = [0, 0, -3.1029776843671137]
computer_monitor_B[0].optimize = 2
bench_desk_D[0].position = [5.400000095367432, 5.800000190734863, 0.3700000047683716]
bench_desk_D[0].rotation = [0, 0, 0.03455751882667646]
bench_desk_D[0].optimize = 2
high_storage_shelf_B[0].position = [0.20113158226013184, 11.399999618530273, 0.949999988079071]
high_storage_shelf_B[0].rotation = [0, 0, -0.0042219308271704194]
high_storage_shelf_B[0].optimize = 2
task_chair_D[0].position = [4.349999904632568, 1.850000023841858, 0.5099999904632568]
task_chair_D[0].rotation = [0, 0, 0.038614833280514946]
task_chair_D[0].optimize = 2
task_chair_C[0].position = [2.8499999046325684, 2.5, 0.5099999904632568]
task_chair_C[0].rotation = [0, 0, -3.1029776843671137]
task_chair_C[0].optimize = 2
low_storage_credensa_B[0].position = [2.799999952316284, 0.22783564031124115, 0.375]
low_storage_credensa_B[0].rotation = [0, 0, 1.5665759855500025]
low_storage_credensa_B[0].optimize = 2
computer_monitor_A[0].position = [1.75, 1.850000023841858, 0.9650000333786011]
computer_monitor_A[0].rotation = [0, 0, -3.1029776843671137]
computer_monitor_A[0].optimize = 2
sticky_note_pad[0].position = [1.7999999523162842, 9.699999809265137, 0.7850000262260437]
sticky_note_pad[0].rotation = [0, 0, 0.038614833280514946]
sticky_note_pad[0].optimize = 2
toner_box_A[0].position = [0.2750000059604645, 7.5, 0.8500000238418579]
toner_box_A[0].rotation = [0, 0, 0.015440383335259768]
toner_box_A[0].optimize = 2
task_chair_F[0].position = [6.449999809265137, 2.5, 0.5099999904632568]
task_chair_F[0].rotation = [0, 0, -3.1029776843671137]
task_chair_F[0].optimize = 2
whiteboard_panel_A[0].position = [0.01783924549818039, 5.800000190734863, 0.6000000238418579]
whiteboard_panel_A[0].rotation = [0, 0, 0.0010364792003167672]
whiteboard_panel_A[0].optimize = 2
task_chair_L[0].position = [6.449999809265137, 5.800000190734863, 0.5099999904632568]
task_chair_L[0].rotation = [0, 0, -3.1029776843671137]
task_chair_L[0].optimize = 2
side_collaboration_table[0].position = [4.0, 11.149999618530273, 0.5249999761581421]
side_collaboration_table[0].rotation = [0, 0, 1.5990706612064889]
side_collaboration_table[0].optimize = 2
task_chair_M[0].position = [0.75, 8.449999809265137, 0.5099999904632568]
task_chair_M[0].rotation = [0, 0, 0.038614833280514946]
task_chair_M[0].optimize = 2
task_chair_N[0].position = [0.75, 9.75, 0.5099999904632568]
task_chair_N[0].rotation = [0, 0, 0.038614833280514946]
task_chair_N[0].optimize = 2
computer_monitor_C[0].position = [1.75, 5.150000095367432, 0.9650000333786011]
computer_monitor_C[0].rotation = [0, 0, -3.1029776843671137]
computer_monitor_C[0].optimize = 2
task_chair_K[0].position = [4.349999904632568, 6.449999809265137, 0.5099999904632568]
task_chair_K[0].rotation = [0, 0, 0.038614833280514946]
task_chair_K[0].optimize = 2
bench_desk_A[0].position = [1.7999999523162842, 2.5, 0.3700000047683716]
bench_desk_A[0].rotation = [0, 0, 0.03455751882667646]
bench_desk_A[0].optimize = 2
task_chair_Q[0].position = [4.349999904632568, 9.75, 0.5099999904632568]
task_chair_Q[0].rotation = [0, 0, 0.025702437873880747]
task_chair_Q[0].optimize = 2
task_chair_P[0].position = [4.349999904632568, 8.449999809265137, 0.5099999904632568]
task_chair_P[0].rotation = [0, 0, 0.025702437873880747]
task_chair_P[0].optimize = 2
computer_monitor_D[0].position = [5.349999904632568, 5.150000095367432, 0.9650000333786011]
computer_monitor_D[0].rotation = [0, 0, -3.1029776843671137]
computer_monitor_D[0].optimize = 2
task_chair_I[0].position = [2.8499999046325684, 5.800000190734863, 0.5099999904632568]
task_chair_I[0].rotation = [0, 0, -3.1029776843671137]
task_chair_I[0].optimize = 2
printer_side_table_B[0].position = [0.2763775885105133, 10.600000381469727, 0.3499999940395355]
printer_side_table_B[0].rotation = [0, 0, -0.004221042572885399]
printer_side_table_B[0].optimize = 2
locker_unit[0].position = [6.150000095367432, 0.2521549165248871, 0.8999999761581421]
locker_unit[0].rotation = [0, 0, 1.5718258242626388]
locker_unit[0].optimize = 2
task_chair_E[0].position = [4.349999904632568, 3.1500000953674316, 0.5099999904632568]
task_chair_E[0].rotation = [0, 0, 0.038614833280514946]
task_chair_E[0].optimize = 2
collaboration_stool_B[0].position = [5.449999809265137, 11.149999618530273, 0.3799999952316284]
collaboration_stool_B[0].rotation = [0, 0, -3.125884689672577]
collaboration_stool_B[0].optimize = 2
potted_plant_small_B[0].position = [2.799999952316284, 0.22499999403953552, 1.0]
potted_plant_small_B[0].rotation = [0, 0, 1.5862492538053736]
potted_plant_small_B[0].optimize = 2
potted_plant_small_C[0].position = [4.449999809265137, 0.22499999403953552, 1.0]
potted_plant_small_C[0].rotation = [0, 0, 1.5862492538053736]
potted_plant_small_C[0].optimize = 2
bench_desk_E[0].position = [1.7999999523162842, 9.100000381469727, 0.3700000047683716]
bench_desk_E[0].rotation = [0, 0, 0.03455751882667646]
bench_desk_E[0].optimize = 2
printer_side_table_A[0].position = [0.2763775885105133, 7.5, 0.3499999940395355]
printer_side_table_A[0].rotation = [0, 0, -0.004221042572885399]
printer_side_table_A[0].optimize = 2
high_storage_shelf_A[0].position = [0.20113158226013184, 0.550000011920929, 0.949999988079071]
high_storage_shelf_A[0].rotation = [0, 0, -0.0042219308271704194]
high_storage_shelf_A[0].optimize = 2
collaboration_stool_C[0].position = [4.0, 10.298084259033203, 0.3799999952316284]
collaboration_stool_C[0].rotation = [0, 0, 1.586504290712113]
collaboration_stool_C[0].optimize = 2
collaboration_stool_A[0].position = [2.549999952316284, 11.149999618530273, 0.3799999952316284]
collaboration_stool_A[0].rotation = [0, 0, 0.0157079639172164]
collaboration_stool_A[0].optimize = 2
task_chair_J[0].position = [4.349999904632568, 5.150000095367432, 0.5099999904632568]
task_chair_J[0].rotation = [0, 0, 0.038614833280514946]
task_chair_J[0].optimize = 2
task_chair_O[0].position = [2.8499999046325684, 9.100000381469727, 0.5099999904632568]
task_chair_O[0].rotation = [0, 0, -3.1029776843671137]
task_chair_O[0].optimize = 2
bench_desk_B[0].position = [5.400000095367432, 2.5, 0.3700000047683716]
bench_desk_B[0].rotation = [0, 0, 0.03455751882667646]
bench_desk_B[0].optimize = 2
bench_desk_F[0].position = [5.400000095367432, 9.100000381469727, 0.3700000047683716]
bench_desk_F[0].rotation = [0, 0, 0.02827433441159227]
bench_desk_F[0].optimize = 2
task_chair_B[0].position = [0.75, 3.1500000953674316, 0.5099999904632568]
task_chair_B[0].rotation = [0, 0, 0.038614833280514946]
task_chair_B[0].optimize = 2
task_chair_G[0].position = [0.75, 5.150000095367432, 0.5099999904632568]
task_chair_G[0].rotation = [0, 0, 0.038614833280514946]
task_chair_G[0].optimize = 2
whiteboard_panel_B[0].position = [0.01783924549818039, 9.100000381469727, 0.6000000238418579]
whiteboard_panel_B[0].rotation = [0, 0, 0.0010364792003167672]
whiteboard_panel_B[0].optimize = 2
toner_box_B[0].position = [0.2750000059604645, 10.600000381469727, 0.8500000238418579]
toner_box_B[0].rotation = [0, 0, 0.015440383335259768]
toner_box_B[0].optimize = 2
bench_desk_C[0].position = [1.7999999523162842, 5.800000190734863, 0.3700000047683716]
bench_desk_C[0].rotation = [0, 0, 0.03455751882667646]
bench_desk_C[0].optimize = 2
ring_binder[0].position = [0.20000000298023224, 0.550000011920929, 2.059999942779541]
ring_binder[0].rotation = [0, 0, 0.015441995329785045]
ring_binder[0].optimize = 2
task_chair_A[0].position = [0.75, 1.850000023841858, 0.5099999904632568]
task_chair_A[0].rotation = [0, 0, 0.038614833280514946]
task_chair_A[0].optimize = 2
task_chair_R[0].position = [6.449999809265137, 9.100000381469727, 0.5099999904632568]
task_chair_R[0].rotation = [0, 0, -3.1158900778943415]
task_chair_R[0].optimize = 2
potted_plant_small_A[0].position = [1.149999976158142, 0.22499999403953552, 1.0]
potted_plant_small_A[0].rotation = [0, 0, 1.5862492538053736]
potted_plant_small_A[0].optimize = 2
task_chair_H[0].position = [0.75, 6.449999809265137, 0.5099999904632568]
task_chair_H[0].rotation = [0, 0, 0.038614833280514946]
task_chair_H[0].optimize = 2
low_storage_credensa_C[0].position = [4.449999809265137, 0.22783564031124115, 0.375]
low_storage_credensa_C[0].rotation = [0, 0, 1.5665759855500025]
low_storage_credensa_C[0].optimize = 2
file_box[0].position = [0.20000000298023224, 11.399999618530273, 2.059999942779541]
file_box[0].rotation = [0, 0, 0.015441995329785045]
file_box[0].optimize = 2

