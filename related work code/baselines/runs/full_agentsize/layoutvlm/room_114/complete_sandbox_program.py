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
    Wall(corner1=[2.00, 7.00, 0.00], corner2=[1.00, 7.00, 0.00]),
    Wall(corner1=[1.00, 7.00, 0.00], corner2=[1.00, 5.00, 0.00]),
    Wall(corner1=[1.00, 5.00, 0.00], corner2=[0.00, 5.00, 0.00]),
    Wall(corner1=[0.00, 5.00, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[7.00, 0.00, 0.00]),
    Wall(corner1=[7.00, 0.00, 0.00], corner2=[7.00, 11.00, 0.00]),
    Wall(corner1=[7.00, 11.00, 0.00], corner2=[2.00, 11.00, 0.00]),
    Wall(corner1=[2.00, 11.00, 0.00], corner2=[2.00, 7.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
lounge_armchair_A = Assets(description="lounge armchair", size=[0.85, 0.85, 0.85], placements=[AssetInstance() for _ in range(1)])
mouse_A = Assets(description="mouse", size=[0.12, 0.07, 0.04], placements=[AssetInstance() for _ in range(1)])
notebook_A = Assets(description="notebook", size=[0.15, 0.21, 0.02], placements=[AssetInstance() for _ in range(1)])
drafting_stool_A = Assets(description="drafting stool", size=[0.45, 0.45, 0.75], placements=[AssetInstance() for _ in range(1)])
file_tray_A = Assets(description="file tray", size=[0.35, 0.26, 0.07], placements=[AssetInstance() for _ in range(1)])
file_tray_B = Assets(description="file tray", size=[0.35, 0.26, 0.07], placements=[AssetInstance() for _ in range(1)])
cutting_mat_A = Assets(description="cutting mat", size=[0.60, 0.90, 0.01], placements=[AssetInstance() for _ in range(1)])
pen_holder_A = Assets(description="pen holder", size=[0.09, 0.09, 0.12], placements=[AssetInstance() for _ in range(1)])
studio_shelf_A = Assets(description="studio shelf", size=[0.40, 1.20, 2.00], placements=[AssetInstance() for _ in range(1)])
notebook_B = Assets(description="notebook", size=[0.15, 0.21, 0.02], placements=[AssetInstance() for _ in range(1)])
pen_holder_B = Assets(description="pen holder", size=[0.09, 0.09, 0.12], placements=[AssetInstance() for _ in range(1)])
lounge_armchair_B = Assets(description="lounge armchair", size=[0.85, 0.85, 0.85], placements=[AssetInstance() for _ in range(1)])
prototype_island = Assets(description="prototype island", size=[0.90, 1.80, 0.90], placements=[AssetInstance() for _ in range(1)])
mobile_storage_cart_A = Assets(description="mobile storage cart", size=[0.45, 0.75, 0.85], placements=[AssetInstance() for _ in range(1)])
storage_box_A = Assets(description="storage box", size=[0.35, 0.45, 0.28], placements=[AssetInstance() for _ in range(1)])
notebook_C = Assets(description="notebook", size=[0.15, 0.21, 0.02], placements=[AssetInstance() for _ in range(1)])
high_stool_island_A = Assets(description="high stool island", size=[0.42, 0.42, 0.75], placements=[AssetInstance() for _ in range(1)])
large_plan_table = Assets(description="large plan table", size=[1.20, 2.40, 0.90], placements=[AssetInstance() for _ in range(1)])
individual_desk_A = Assets(description="individual desk", size=[0.70, 1.40, 0.75], placements=[AssetInstance() for _ in range(1)])
notebook_D = Assets(description="notebook", size=[0.15, 0.21, 0.02], placements=[AssetInstance() for _ in range(1)])
pen_holder_C = Assets(description="pen holder", size=[0.09, 0.09, 0.12], placements=[AssetInstance() for _ in range(1)])
wall_shelf_rail_A = Assets(description="A brown wooden oblong.", size=[0.22, 1.20, 0.08], placements=[AssetInstance() for _ in range(1)])
desk_lamp_A = Assets(description="desk lamp", size=[0.25, 0.18, 0.45], placements=[AssetInstance() for _ in range(1)])
desk_lamp_B = Assets(description="desk lamp", size=[0.25, 0.18, 0.45], placements=[AssetInstance() for _ in range(1)])
small_toolbox = Assets(description="small toolbox", size=[0.22, 0.45, 0.20], placements=[AssetInstance() for _ in range(1)])
pen_holder_D = Assets(description="pen holder", size=[0.09, 0.09, 0.12], placements=[AssetInstance() for _ in range(1)])
storage_box_B = Assets(description="storage box", size=[0.35, 0.45, 0.28], placements=[AssetInstance() for _ in range(1)])
side_drawer_unit_A = Assets(description="side drawer unit", size=[0.55, 0.45, 0.65], placements=[AssetInstance() for _ in range(1)])
lounge_armchair_C = Assets(description="lounge armchair", size=[0.85, 0.85, 0.85], placements=[AssetInstance() for _ in range(1)])
critique_sofa = Assets(description="critique sofa", size=[0.90, 2.10, 0.85], placements=[AssetInstance() for _ in range(1)])
notebook_E = Assets(description="notebook", size=[0.15, 0.21, 0.02], placements=[AssetInstance() for _ in range(1)])
notebook_F = Assets(description="notebook", size=[0.15, 0.21, 0.02], placements=[AssetInstance() for _ in range(1)])
wall_shelf_rail_B = Assets(description="A brown wooden oblong.", size=[0.22, 1.20, 0.08], placements=[AssetInstance() for _ in range(1)])
notebook_G = Assets(description="notebook", size=[0.15, 0.21, 0.02], placements=[AssetInstance() for _ in range(1)])
desk_lamp_C = Assets(description="desk lamp", size=[0.25, 0.18, 0.45], placements=[AssetInstance() for _ in range(1)])
individual_desk_B = Assets(description="individual desk", size=[0.70, 1.40, 0.75], placements=[AssetInstance() for _ in range(1)])
task_chair_studio_A = Assets(description="task chair studio", size=[0.65, 0.65, 1.00], placements=[AssetInstance() for _ in range(1)])
notebook_H = Assets(description="notebook", size=[0.15, 0.21, 0.02], placements=[AssetInstance() for _ in range(1)])
high_stool_island_B = Assets(description="high stool island", size=[0.42, 0.42, 0.75], placements=[AssetInstance() for _ in range(1)])
storage_box_C = Assets(description="storage box", size=[0.35, 0.45, 0.28], placements=[AssetInstance() for _ in range(1)])
task_chair_studio_B = Assets(description="task chair studio", size=[0.65, 0.65, 1.00], placements=[AssetInstance() for _ in range(1)])
high_stool_island_C = Assets(description="high stool island", size=[0.42, 0.42, 0.75], placements=[AssetInstance() for _ in range(1)])
side_drawer_unit_B = Assets(description="side drawer unit", size=[0.55, 0.45, 0.65], placements=[AssetInstance() for _ in range(1)])
wall_shelf_rail_C = Assets(description="A brown wooden oblong.", size=[0.22, 1.20, 0.08], placements=[AssetInstance() for _ in range(1)])
notebook_I = Assets(description="notebook", size=[0.15, 0.21, 0.02], placements=[AssetInstance() for _ in range(1)])
individual_desk_C = Assets(description="individual desk", size=[0.70, 1.40, 0.75], placements=[AssetInstance() for _ in range(1)])
studio_shelf_B = Assets(description="studio shelf", size=[0.40, 1.20, 2.00], placements=[AssetInstance() for _ in range(1)])
drafting_stool_B = Assets(description="drafting stool", size=[0.45, 0.45, 0.75], placements=[AssetInstance() for _ in range(1)])
desk_lamp_D = Assets(description="desk lamp", size=[0.25, 0.18, 0.45], placements=[AssetInstance() for _ in range(1)])
mouse_B = Assets(description="mouse", size=[0.12, 0.07, 0.04], placements=[AssetInstance() for _ in range(1)])
side_table_lounge = Assets(description="side table lounge", size=[0.50, 0.50, 0.50], placements=[AssetInstance() for _ in range(1)])
project_bench_A = Assets(description="project bench", size=[0.75, 1.80, 0.90], placements=[AssetInstance() for _ in range(1)])
notebook_J = Assets(description="notebook", size=[0.15, 0.21, 0.02], placements=[AssetInstance() for _ in range(1)])
wall_clock_studio = Assets(description="A black wall clock.", size=[0.05, 0.35, 0.35], placements=[AssetInstance() for _ in range(1)])
mouse_C = Assets(description="mouse", size=[0.12, 0.07, 0.04], placements=[AssetInstance() for _ in range(1)])
sticky_note_pad = Assets(description="sticky note pad", size=[0.08, 0.08, 0.01], placements=[AssetInstance() for _ in range(1)])
file_tray_C = Assets(description="file tray", size=[0.35, 0.26, 0.07], placements=[AssetInstance() for _ in range(1)])
studio_shelf_C = Assets(description="studio shelf", size=[0.40, 1.20, 2.00], placements=[AssetInstance() for _ in range(1)])
individual_desk_D = Assets(description="individual desk", size=[0.70, 1.40, 0.75], placements=[AssetInstance() for _ in range(1)])
notebook_K = Assets(description="notebook", size=[0.15, 0.21, 0.02], placements=[AssetInstance() for _ in range(1)])
project_bench_B = Assets(description="project bench", size=[0.75, 1.80, 0.90], placements=[AssetInstance() for _ in range(1)])
marker_set = Assets(description="marker set", size=[0.12, 0.20, 0.04], placements=[AssetInstance() for _ in range(1)])
drafting_stool_C = Assets(description="drafting stool", size=[0.45, 0.45, 0.75], placements=[AssetInstance() for _ in range(1)])
throw_pillow = Assets(description="throw pillow", size=[0.15, 0.45, 0.45], placements=[AssetInstance() for _ in range(1)])
side_drawer_unit_C = Assets(description="side drawer unit", size=[0.55, 0.45, 0.65], placements=[AssetInstance() for _ in range(1)])
task_chair_studio_C = Assets(description="task chair studio", size=[0.65, 0.65, 1.00], placements=[AssetInstance() for _ in range(1)])
notebook_L = Assets(description="notebook", size=[0.15, 0.21, 0.02], placements=[AssetInstance() for _ in range(1)])
wall_shelf_rail_D = Assets(description="A brown wooden oblong.", size=[0.22, 1.20, 0.08], placements=[AssetInstance() for _ in range(1)])
large_drawing_board = Assets(description="large drawing board", size=[1.00, 1.80, 0.04], placements=[AssetInstance() for _ in range(1)])
side_drawer_unit_D = Assets(description="side drawer unit", size=[0.55, 0.45, 0.65], placements=[AssetInstance() for _ in range(1)])
cutting_mat_B = Assets(description="cutting mat", size=[0.60, 0.90, 0.01], placements=[AssetInstance() for _ in range(1)])
high_stool_island_D = Assets(description="high stool island", size=[0.42, 0.42, 0.75], placements=[AssetInstance() for _ in range(1)])
mouse_D = Assets(description="mouse", size=[0.12, 0.07, 0.04], placements=[AssetInstance() for _ in range(1)])
notebook_M = Assets(description="notebook", size=[0.15, 0.21, 0.02], placements=[AssetInstance() for _ in range(1)])
project_bench_C = Assets(description="project bench", size=[0.75, 1.80, 0.90], placements=[AssetInstance() for _ in range(1)])
tape_roll = Assets(description="tape roll", size=[0.12, 0.12, 0.05], placements=[AssetInstance() for _ in range(1)])
cutting_mat_C = Assets(description="cutting mat", size=[0.60, 0.90, 0.01], placements=[AssetInstance() for _ in range(1)])
mobile_storage_cart_B = Assets(description="mobile storage cart", size=[0.45, 0.75, 0.85], placements=[AssetInstance() for _ in range(1)])
task_chair_studio_D = Assets(description="task chair studio", size=[0.65, 0.65, 1.00], placements=[AssetInstance() for _ in range(1)])

lounge_armchair_A[0].instance_id = 'lounge_armchair_A_0'
mouse_A[0].instance_id = 'mouse_A_0'
notebook_A[0].instance_id = 'notebook_A_0'
drafting_stool_A[0].instance_id = 'drafting_stool_A_0'
file_tray_A[0].instance_id = 'file_tray_A_0'
file_tray_B[0].instance_id = 'file_tray_B_0'
cutting_mat_A[0].instance_id = 'cutting_mat_A_0'
pen_holder_A[0].instance_id = 'pen_holder_A_0'
studio_shelf_A[0].instance_id = 'studio_shelf_A_0'
notebook_B[0].instance_id = 'notebook_B_0'
pen_holder_B[0].instance_id = 'pen_holder_B_0'
lounge_armchair_B[0].instance_id = 'lounge_armchair_B_0'
prototype_island[0].instance_id = 'prototype_island_0'
mobile_storage_cart_A[0].instance_id = 'mobile_storage_cart_A_0'
storage_box_A[0].instance_id = 'storage_box_A_0'
notebook_C[0].instance_id = 'notebook_C_0'
high_stool_island_A[0].instance_id = 'high_stool_island_A_0'
large_plan_table[0].instance_id = 'large_plan_table_0'
individual_desk_A[0].instance_id = 'individual_desk_A_0'
notebook_D[0].instance_id = 'notebook_D_0'
pen_holder_C[0].instance_id = 'pen_holder_C_0'
wall_shelf_rail_A[0].instance_id = 'wall_shelf_rail_A_0'
desk_lamp_A[0].instance_id = 'desk_lamp_A_0'
desk_lamp_B[0].instance_id = 'desk_lamp_B_0'
small_toolbox[0].instance_id = 'small_toolbox_0'
pen_holder_D[0].instance_id = 'pen_holder_D_0'
storage_box_B[0].instance_id = 'storage_box_B_0'
side_drawer_unit_A[0].instance_id = 'side_drawer_unit_A_0'
lounge_armchair_C[0].instance_id = 'lounge_armchair_C_0'
critique_sofa[0].instance_id = 'critique_sofa_0'
notebook_E[0].instance_id = 'notebook_E_0'
notebook_F[0].instance_id = 'notebook_F_0'
wall_shelf_rail_B[0].instance_id = 'wall_shelf_rail_B_0'
notebook_G[0].instance_id = 'notebook_G_0'
desk_lamp_C[0].instance_id = 'desk_lamp_C_0'
individual_desk_B[0].instance_id = 'individual_desk_B_0'
task_chair_studio_A[0].instance_id = 'task_chair_studio_A_0'
notebook_H[0].instance_id = 'notebook_H_0'
high_stool_island_B[0].instance_id = 'high_stool_island_B_0'
storage_box_C[0].instance_id = 'storage_box_C_0'
task_chair_studio_B[0].instance_id = 'task_chair_studio_B_0'
high_stool_island_C[0].instance_id = 'high_stool_island_C_0'
side_drawer_unit_B[0].instance_id = 'side_drawer_unit_B_0'
wall_shelf_rail_C[0].instance_id = 'wall_shelf_rail_C_0'
notebook_I[0].instance_id = 'notebook_I_0'
individual_desk_C[0].instance_id = 'individual_desk_C_0'
studio_shelf_B[0].instance_id = 'studio_shelf_B_0'
drafting_stool_B[0].instance_id = 'drafting_stool_B_0'
desk_lamp_D[0].instance_id = 'desk_lamp_D_0'
mouse_B[0].instance_id = 'mouse_B_0'
side_table_lounge[0].instance_id = 'side_table_lounge_0'
project_bench_A[0].instance_id = 'project_bench_A_0'
notebook_J[0].instance_id = 'notebook_J_0'
wall_clock_studio[0].instance_id = 'wall_clock_studio_0'
mouse_C[0].instance_id = 'mouse_C_0'
sticky_note_pad[0].instance_id = 'sticky_note_pad_0'
file_tray_C[0].instance_id = 'file_tray_C_0'
studio_shelf_C[0].instance_id = 'studio_shelf_C_0'
individual_desk_D[0].instance_id = 'individual_desk_D_0'
notebook_K[0].instance_id = 'notebook_K_0'
project_bench_B[0].instance_id = 'project_bench_B_0'
marker_set[0].instance_id = 'marker_set_0'
drafting_stool_C[0].instance_id = 'drafting_stool_C_0'
throw_pillow[0].instance_id = 'throw_pillow_0'
side_drawer_unit_C[0].instance_id = 'side_drawer_unit_C_0'
task_chair_studio_C[0].instance_id = 'task_chair_studio_C_0'
notebook_L[0].instance_id = 'notebook_L_0'
wall_shelf_rail_D[0].instance_id = 'wall_shelf_rail_D_0'
large_drawing_board[0].instance_id = 'large_drawing_board_0'
side_drawer_unit_D[0].instance_id = 'side_drawer_unit_D_0'
cutting_mat_B[0].instance_id = 'cutting_mat_B_0'
high_stool_island_D[0].instance_id = 'high_stool_island_D_0'
mouse_D[0].instance_id = 'mouse_D_0'
notebook_M[0].instance_id = 'notebook_M_0'
project_bench_C[0].instance_id = 'project_bench_C_0'
tape_roll[0].instance_id = 'tape_roll_0'
cutting_mat_C[0].instance_id = 'cutting_mat_C_0'
mobile_storage_cart_B[0].instance_id = 'mobile_storage_cart_B_0'
task_chair_studio_D[0].instance_id = 'task_chair_studio_D_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

lounge_armchair_A[0].position = [6.880224930325664, 8.113960458907513, 0.425]
lounge_armchair_A[0].rotation = [0, 0, 0]
mouse_A[0].position = [6.894309187600659, 6.243321664201277, 0.02]
mouse_A[0].rotation = [0, 0, 0]
notebook_A[0].position = [5.620690997542906, 9.783439468963273, 0.01]
notebook_A[0].rotation = [0, 0, 0]
drafting_stool_A[0].position = [5.3720516643706215, 6.077700071339369, 0.375]
drafting_stool_A[0].rotation = [0, 0, 0]
file_tray_A[0].position = [4.441408149762835, 4.628722314369059, 0.035]
file_tray_A[0].rotation = [0, 0, 0]
file_tray_B[0].position = [3.053680380370539, 2.7485577952314184, 0.035]
file_tray_B[0].rotation = [0, 0, 0]
cutting_mat_A[0].position = [5.230927771386796, 2.4117663403647893, 0.0025]
cutting_mat_A[0].rotation = [0, 0, 0]
pen_holder_A[0].position = [4.762771922112691, 10.17007380243877, 0.06]
pen_holder_A[0].rotation = [0, 0, 0]
studio_shelf_A[0].position = [6.50341346181643, 7.211735565921223, 1.0]
studio_shelf_A[0].rotation = [0, 0, 0]
notebook_B[0].position = [4.7849334563693136, 0.3067989540260704, 0.01]
notebook_B[0].rotation = [0, 0, 0]
pen_holder_B[0].position = [4.733781261158735, 10.641083590388886, 0.06]
pen_holder_B[0].rotation = [0, 0, 0]
lounge_armchair_B[0].position = [1.252706723356677, 6.654002089133937, 0.425]
lounge_armchair_B[0].rotation = [0, 0, 0]
prototype_island[0].position = [0.7453826444665057, 0.27778387317558506, 0.45]
prototype_island[0].rotation = [0, 0, 0]
mobile_storage_cart_A[0].position = [3.0760559538787104, 3.5037658459405656, 0.425]
mobile_storage_cart_A[0].rotation = [0, 0, 0]
storage_box_A[0].position = [2.982109053068294, 10.825439887741656, 0.14]
storage_box_A[0].rotation = [0, 0, 0]
notebook_C[0].position = [6.025401718423475, 5.393003705239137, 0.01]
notebook_C[0].rotation = [0, 0, 0]
high_stool_island_A[0].position = [2.426112104598487, 5.812490496394619, 0.375]
high_stool_island_A[0].rotation = [0, 0, 0]
large_plan_table[0].position = [3.983938401974649, 5.153531695649022, 0.45]
large_plan_table[0].rotation = [0, 0, 0]
individual_desk_A[0].position = [4.084544249365983, 6.947396674145939, 0.375]
individual_desk_A[0].rotation = [0, 0, 0]
notebook_D[0].position = [3.789271944113925, 3.8078929539960567, 0.01]
notebook_D[0].rotation = [0, 0, 0]
pen_holder_C[0].position = [5.593190374851644, 5.41966550941835, 0.06]
pen_holder_C[0].rotation = [0, 0, 0]
wall_shelf_rail_A[0].position = [2.1167218121360265, 7.520286811428161, 0.04]
wall_shelf_rail_A[0].rotation = [0, 0, 0]
desk_lamp_A[0].position = [5.8171303073831, 6.6778995985718135, 0.225]
desk_lamp_A[0].rotation = [0, 0, 0]
desk_lamp_B[0].position = [2.164260072966533, 2.868929919815753, 0.225]
desk_lamp_B[0].rotation = [0, 0, 0]
small_toolbox[0].position = [1.8569363212822676, 3.9316125835370785, 0.1]
small_toolbox[0].rotation = [0, 0, 0]
pen_holder_D[0].position = [2.6932953168742677, 10.428985842520056, 0.06]
pen_holder_D[0].rotation = [0, 0, 0]
storage_box_B[0].position = [5.531251289202288, 4.017667475820928, 0.14]
storage_box_B[0].rotation = [0, 0, 0]
side_drawer_unit_A[0].position = [2.7375788484612786, 10.642871504858576, 0.325]
side_drawer_unit_A[0].rotation = [0, 0, 0]
lounge_armchair_C[0].position = [3.8598128177225024, 2.9289148032498473, 0.425]
lounge_armchair_C[0].rotation = [0, 0, 0]
critique_sofa[0].position = [2.365173306073031, 5.166320659690124, 0.425]
critique_sofa[0].rotation = [0, 0, 0]
notebook_E[0].position = [5.417203267528361, 6.747095569654514, 0.01]
notebook_E[0].rotation = [0, 0, 0]
notebook_F[0].position = [6.570813665237585, 6.845846625801526, 0.01]
notebook_F[0].rotation = [0, 0, 0]
wall_shelf_rail_B[0].position = [6.264264569736037, 3.193384450212462, 0.04]
wall_shelf_rail_B[0].rotation = [0, 0, 0]
notebook_G[0].position = [3.1646931200219317, 9.452059358598088, 0.01]
notebook_G[0].rotation = [0, 0, 0]
desk_lamp_C[0].position = [4.984864360839385, 0.7663997349913352, 0.225]
desk_lamp_C[0].rotation = [0, 0, 0]
individual_desk_B[0].position = [1.0105828726952226, 0.655335494221913, 0.375]
individual_desk_B[0].rotation = [0, 0, 0]
task_chair_studio_A[0].position = [5.590946568047342, 3.220988963680733, 0.5]
task_chair_studio_A[0].rotation = [0, 0, 0]
notebook_H[0].position = [3.1529350270086316, 0.8223511971654545, 0.01]
notebook_H[0].rotation = [0, 0, 0]
high_stool_island_B[0].position = [1.9276872395931326, 5.649647382816444, 0.375]
high_stool_island_B[0].rotation = [0, 0, 0]
storage_box_C[0].position = [1.2277667792187081, 2.4561401891046817, 0.14]
storage_box_C[0].rotation = [0, 0, 0]
task_chair_studio_B[0].position = [4.67035721698448, 10.181566828362035, 0.5]
task_chair_studio_B[0].rotation = [0, 0, 0]
high_stool_island_C[0].position = [2.6394433206399683, 6.580232709102838, 0.375]
high_stool_island_C[0].rotation = [0, 0, 0]
side_drawer_unit_B[0].position = [4.042904134209186, 4.884922480642933, 0.325]
side_drawer_unit_B[0].rotation = [0, 0, 0]
wall_shelf_rail_C[0].position = [3.271077049166509, 10.786184360333165, 0.04]
wall_shelf_rail_C[0].rotation = [0, 0, 0]
notebook_I[0].position = [3.855153871276664, 3.496636382455151, 0.01]
notebook_I[0].rotation = [0, 0, 0]
individual_desk_C[0].position = [4.795227704850884, 4.733108479097591, 0.375]
individual_desk_C[0].rotation = [0, 0, 0]
studio_shelf_B[0].position = [5.956973615163632, 3.3951211382174606, 1.0]
studio_shelf_B[0].rotation = [0, 0, 0]
drafting_stool_B[0].position = [4.253873777537261, 2.2414627836630014, 0.375]
drafting_stool_B[0].rotation = [0, 0, 0]
desk_lamp_D[0].position = [4.62772099332246, 3.4955564667782717, 0.225]
desk_lamp_D[0].rotation = [0, 0, 0]
mouse_B[0].position = [2.722876527366264, 4.488800196083217, 0.02]
mouse_B[0].rotation = [0, 0, 0]
side_table_lounge[0].position = [3.8960309955150136, 5.956937038671587, 0.25]
side_table_lounge[0].rotation = [0, 0, 0]
project_bench_A[0].position = [4.848386353266194, 8.078134340907956, 0.45]
project_bench_A[0].rotation = [0, 0, 0]
notebook_J[0].position = [6.463952106126844, 9.870863394062301, 0.01]
notebook_J[0].rotation = [0, 0, 0]
wall_clock_studio[0].position = [4.654396107076373, 4.041173699211497, 0.175]
wall_clock_studio[0].rotation = [0, 0, 0]
mouse_C[0].position = [4.7257356781629145, 4.364389378345411, 0.02]
mouse_C[0].rotation = [0, 0, 0]
sticky_note_pad[0].position = [1.8979786757610302, 6.639307065395808, 0.005]
sticky_note_pad[0].rotation = [0, 0, 0]
file_tray_C[0].position = [3.5380034297089016, 2.7230426419744718, 0.035]
file_tray_C[0].rotation = [0, 0, 0]
studio_shelf_C[0].position = [4.358587052347548, 5.3566408964401555, 1.0]
studio_shelf_C[0].rotation = [0, 0, 0]
individual_desk_D[0].position = [5.007484233717671, 1.5528397656990485, 0.375]
individual_desk_D[0].rotation = [0, 0, 0]
notebook_K[0].position = [2.820727623201123, 10.959424318967836, 0.01]
notebook_K[0].rotation = [0, 0, 0]
project_bench_B[0].position = [6.339203423221302, 2.0308726381248885, 0.45]
project_bench_B[0].rotation = [0, 0, 0]
marker_set[0].position = [5.982326518048747, 4.722212834301944, 0.02]
marker_set[0].rotation = [0, 0, 0]
drafting_stool_C[0].position = [5.0941672262251, 7.437492987192243, 0.375]
drafting_stool_C[0].rotation = [0, 0, 0]
throw_pillow[0].position = [4.294218495086663, 3.4643374719572684, 0.225]
throw_pillow[0].rotation = [0, 0, 0]
side_drawer_unit_C[0].position = [1.9196003933119221, 3.0811329445561326, 0.325]
side_drawer_unit_C[0].rotation = [0, 0, 0]
task_chair_studio_C[0].position = [0.49133847052670165, 3.782573357537138, 0.5]
task_chair_studio_C[0].rotation = [0, 0, 0]
notebook_L[0].position = [6.437905280210297, 3.0816083437438775, 0.01]
notebook_L[0].rotation = [0, 0, 0]
wall_shelf_rail_D[0].position = [2.6071277291901396, 2.475312934695244, 0.04]
wall_shelf_rail_D[0].rotation = [0, 0, 0]
large_drawing_board[0].position = [3.863676861497445, 5.769181947416319, 0.02]
large_drawing_board[0].rotation = [0, 0, 0]
side_drawer_unit_D[0].position = [3.8989115101520895, 1.3044735874783595, 0.325]
side_drawer_unit_D[0].rotation = [0, 0, 0]
cutting_mat_B[0].position = [4.907976013488233, 10.867753222857134, 0.0025]
cutting_mat_B[0].rotation = [0, 0, 0]
high_stool_island_D[0].position = [3.1201922166551808, 10.754779654738451, 0.375]
high_stool_island_D[0].rotation = [0, 0, 0]
mouse_D[0].position = [1.4412262337662658, 4.721772815996908, 0.02]
mouse_D[0].rotation = [0, 0, 0]
notebook_M[0].position = [3.004709633068653, 3.1023345138223144, 0.01]
notebook_M[0].rotation = [0, 0, 0]
project_bench_C[0].position = [1.4301148955570842, 2.1317254879069027, 0.45]
project_bench_C[0].rotation = [0, 0, 0]
tape_roll[0].position = [2.4311288727601155, 7.8634618151472555, 0.025]
tape_roll[0].rotation = [0, 0, 0]
cutting_mat_C[0].position = [2.8508944671928855, 0.799578054158371, 0.0025]
cutting_mat_C[0].rotation = [0, 0, 0]
mobile_storage_cart_B[0].position = [5.587191868883013, 5.065976168174243, 0.425]
mobile_storage_cart_B[0].rotation = [0, 0, 0]
task_chair_studio_D[0].position = [2.2354579988979495, 7.061273710888424, 0.5]
task_chair_studio_D[0].rotation = [0, 0, 0]
lounge_armchair_A[0].position = [6.880224930325664, 8.113960458907513, 0.425]
lounge_armchair_A[0].rotation = [0, 0, 0]
mouse_A[0].position = [6.894309187600659, 6.243321664201277, 0.02]
mouse_A[0].rotation = [0, 0, 0]
notebook_A[0].position = [5.620690997542906, 9.783439468963273, 0.01]
notebook_A[0].rotation = [0, 0, 0]
drafting_stool_A[0].position = [5.3720516643706215, 6.077700071339369, 0.375]
drafting_stool_A[0].rotation = [0, 0, 0]
file_tray_A[0].position = [4.441408149762835, 4.628722314369059, 0.035]
file_tray_A[0].rotation = [0, 0, 0]
file_tray_B[0].position = [3.053680380370539, 2.7485577952314184, 0.035]
file_tray_B[0].rotation = [0, 0, 0]
cutting_mat_A[0].position = [5.230927771386796, 2.4117663403647893, 0.0025]
cutting_mat_A[0].rotation = [0, 0, 0]
pen_holder_A[0].position = [4.762771922112691, 10.17007380243877, 0.06]
pen_holder_A[0].rotation = [0, 0, 0]
studio_shelf_A[0].position = [6.50341346181643, 7.211735565921223, 1.0]
studio_shelf_A[0].rotation = [0, 0, 0]
notebook_B[0].position = [4.7849334563693136, 0.3067989540260704, 0.01]
notebook_B[0].rotation = [0, 0, 0]
pen_holder_B[0].position = [4.733781261158735, 10.641083590388886, 0.06]
pen_holder_B[0].rotation = [0, 0, 0]
lounge_armchair_B[0].position = [1.252706723356677, 6.654002089133937, 0.425]
lounge_armchair_B[0].rotation = [0, 0, 0]
prototype_island[0].position = [0.7453826444665057, 0.27778387317558506, 0.45]
prototype_island[0].rotation = [0, 0, 0]
mobile_storage_cart_A[0].position = [3.0760559538787104, 3.5037658459405656, 0.425]
mobile_storage_cart_A[0].rotation = [0, 0, 0]
storage_box_A[0].position = [2.982109053068294, 10.825439887741656, 0.14]
storage_box_A[0].rotation = [0, 0, 0]
notebook_C[0].position = [6.025401718423475, 5.393003705239137, 0.01]
notebook_C[0].rotation = [0, 0, 0]
high_stool_island_A[0].position = [2.426112104598487, 5.812490496394619, 0.375]
high_stool_island_A[0].rotation = [0, 0, 0]
large_plan_table[0].position = [3.983938401974649, 5.153531695649022, 0.45]
large_plan_table[0].rotation = [0, 0, 0]
individual_desk_A[0].position = [4.084544249365983, 6.947396674145939, 0.375]
individual_desk_A[0].rotation = [0, 0, 0]
notebook_D[0].position = [3.789271944113925, 3.8078929539960567, 0.01]
notebook_D[0].rotation = [0, 0, 0]
pen_holder_C[0].position = [5.593190374851644, 5.41966550941835, 0.06]
pen_holder_C[0].rotation = [0, 0, 0]
wall_shelf_rail_A[0].position = [2.1167218121360265, 7.520286811428161, 0.04]
wall_shelf_rail_A[0].rotation = [0, 0, 0]
desk_lamp_A[0].position = [5.8171303073831, 6.6778995985718135, 0.225]
desk_lamp_A[0].rotation = [0, 0, 0]
desk_lamp_B[0].position = [2.164260072966533, 2.868929919815753, 0.225]
desk_lamp_B[0].rotation = [0, 0, 0]
small_toolbox[0].position = [1.8569363212822676, 3.9316125835370785, 0.1]
small_toolbox[0].rotation = [0, 0, 0]
pen_holder_D[0].position = [2.6932953168742677, 10.428985842520056, 0.06]
pen_holder_D[0].rotation = [0, 0, 0]
storage_box_B[0].position = [5.531251289202288, 4.017667475820928, 0.14]
storage_box_B[0].rotation = [0, 0, 0]
side_drawer_unit_A[0].position = [2.7375788484612786, 10.642871504858576, 0.325]
side_drawer_unit_A[0].rotation = [0, 0, 0]
lounge_armchair_C[0].position = [3.8598128177225024, 2.9289148032498473, 0.425]
lounge_armchair_C[0].rotation = [0, 0, 0]
critique_sofa[0].position = [2.365173306073031, 5.166320659690124, 0.425]
critique_sofa[0].rotation = [0, 0, 0]
notebook_E[0].position = [5.417203267528361, 6.747095569654514, 0.01]
notebook_E[0].rotation = [0, 0, 0]
notebook_F[0].position = [6.570813665237585, 6.845846625801526, 0.01]
notebook_F[0].rotation = [0, 0, 0]
wall_shelf_rail_B[0].position = [6.264264569736037, 3.193384450212462, 0.04]
wall_shelf_rail_B[0].rotation = [0, 0, 0]
notebook_G[0].position = [3.1646931200219317, 9.452059358598088, 0.01]
notebook_G[0].rotation = [0, 0, 0]
desk_lamp_C[0].position = [4.984864360839385, 0.7663997349913352, 0.225]
desk_lamp_C[0].rotation = [0, 0, 0]
individual_desk_B[0].position = [1.0105828726952226, 0.655335494221913, 0.375]
individual_desk_B[0].rotation = [0, 0, 0]
task_chair_studio_A[0].position = [5.590946568047342, 3.220988963680733, 0.5]
task_chair_studio_A[0].rotation = [0, 0, 0]
notebook_H[0].position = [3.1529350270086316, 0.8223511971654545, 0.01]
notebook_H[0].rotation = [0, 0, 0]
high_stool_island_B[0].position = [1.9276872395931326, 5.649647382816444, 0.375]
high_stool_island_B[0].rotation = [0, 0, 0]
storage_box_C[0].position = [1.2277667792187081, 2.4561401891046817, 0.14]
storage_box_C[0].rotation = [0, 0, 0]
task_chair_studio_B[0].position = [4.67035721698448, 10.181566828362035, 0.5]
task_chair_studio_B[0].rotation = [0, 0, 0]
high_stool_island_C[0].position = [2.6394433206399683, 6.580232709102838, 0.375]
high_stool_island_C[0].rotation = [0, 0, 0]
side_drawer_unit_B[0].position = [4.042904134209186, 4.884922480642933, 0.325]
side_drawer_unit_B[0].rotation = [0, 0, 0]
wall_shelf_rail_C[0].position = [3.271077049166509, 10.786184360333165, 0.04]
wall_shelf_rail_C[0].rotation = [0, 0, 0]
notebook_I[0].position = [3.855153871276664, 3.496636382455151, 0.01]
notebook_I[0].rotation = [0, 0, 0]
individual_desk_C[0].position = [4.795227704850884, 4.733108479097591, 0.375]
individual_desk_C[0].rotation = [0, 0, 0]
studio_shelf_B[0].position = [5.956973615163632, 3.3951211382174606, 1.0]
studio_shelf_B[0].rotation = [0, 0, 0]
drafting_stool_B[0].position = [4.253873777537261, 2.2414627836630014, 0.375]
drafting_stool_B[0].rotation = [0, 0, 0]
desk_lamp_D[0].position = [4.62772099332246, 3.4955564667782717, 0.225]
desk_lamp_D[0].rotation = [0, 0, 0]
mouse_B[0].position = [2.722876527366264, 4.488800196083217, 0.02]
mouse_B[0].rotation = [0, 0, 0]
side_table_lounge[0].position = [3.8960309955150136, 5.956937038671587, 0.25]
side_table_lounge[0].rotation = [0, 0, 0]
project_bench_A[0].position = [4.848386353266194, 8.078134340907956, 0.45]
project_bench_A[0].rotation = [0, 0, 0]
notebook_J[0].position = [6.463952106126844, 9.870863394062301, 0.01]
notebook_J[0].rotation = [0, 0, 0]
wall_clock_studio[0].position = [4.654396107076373, 4.041173699211497, 0.175]
wall_clock_studio[0].rotation = [0, 0, 0]
mouse_C[0].position = [4.7257356781629145, 4.364389378345411, 0.02]
mouse_C[0].rotation = [0, 0, 0]
sticky_note_pad[0].position = [1.8979786757610302, 6.639307065395808, 0.005]
sticky_note_pad[0].rotation = [0, 0, 0]
file_tray_C[0].position = [3.5380034297089016, 2.7230426419744718, 0.035]
file_tray_C[0].rotation = [0, 0, 0]
studio_shelf_C[0].position = [4.358587052347548, 5.3566408964401555, 1.0]
studio_shelf_C[0].rotation = [0, 0, 0]
individual_desk_D[0].position = [5.007484233717671, 1.5528397656990485, 0.375]
individual_desk_D[0].rotation = [0, 0, 0]
notebook_K[0].position = [2.820727623201123, 10.959424318967836, 0.01]
notebook_K[0].rotation = [0, 0, 0]
project_bench_B[0].position = [6.339203423221302, 2.0308726381248885, 0.45]
project_bench_B[0].rotation = [0, 0, 0]
marker_set[0].position = [5.982326518048747, 4.722212834301944, 0.02]
marker_set[0].rotation = [0, 0, 0]
drafting_stool_C[0].position = [5.0941672262251, 7.437492987192243, 0.375]
drafting_stool_C[0].rotation = [0, 0, 0]
throw_pillow[0].position = [4.294218495086663, 3.4643374719572684, 0.225]
throw_pillow[0].rotation = [0, 0, 0]
side_drawer_unit_C[0].position = [1.9196003933119221, 3.0811329445561326, 0.325]
side_drawer_unit_C[0].rotation = [0, 0, 0]
task_chair_studio_C[0].position = [0.49133847052670165, 3.782573357537138, 0.5]
task_chair_studio_C[0].rotation = [0, 0, 0]
notebook_L[0].position = [6.437905280210297, 3.0816083437438775, 0.01]
notebook_L[0].rotation = [0, 0, 0]
wall_shelf_rail_D[0].position = [2.6071277291901396, 2.475312934695244, 0.04]
wall_shelf_rail_D[0].rotation = [0, 0, 0]
large_drawing_board[0].position = [3.863676861497445, 5.769181947416319, 0.02]
large_drawing_board[0].rotation = [0, 0, 0]
side_drawer_unit_D[0].position = [3.8989115101520895, 1.3044735874783595, 0.325]
side_drawer_unit_D[0].rotation = [0, 0, 0]
cutting_mat_B[0].position = [4.907976013488233, 10.867753222857134, 0.0025]
cutting_mat_B[0].rotation = [0, 0, 0]
high_stool_island_D[0].position = [3.1201922166551808, 10.754779654738451, 0.375]
high_stool_island_D[0].rotation = [0, 0, 0]
mouse_D[0].position = [1.4412262337662658, 4.721772815996908, 0.02]
mouse_D[0].rotation = [0, 0, 0]
notebook_M[0].position = [3.004709633068653, 3.1023345138223144, 0.01]
notebook_M[0].rotation = [0, 0, 0]
project_bench_C[0].position = [1.4301148955570842, 2.1317254879069027, 0.45]
project_bench_C[0].rotation = [0, 0, 0]
tape_roll[0].position = [2.4311288727601155, 7.8634618151472555, 0.025]
tape_roll[0].rotation = [0, 0, 0]
cutting_mat_C[0].position = [2.8508944671928855, 0.799578054158371, 0.0025]
cutting_mat_C[0].rotation = [0, 0, 0]
mobile_storage_cart_B[0].position = [5.587191868883013, 5.065976168174243, 0.425]
mobile_storage_cart_B[0].rotation = [0, 0, 0]
task_chair_studio_D[0].position = [2.2354579988979495, 7.061273710888424, 0.5]
task_chair_studio_D[0].rotation = [0, 0, 0]

solver.constraints = []

# Helper for assigning an explicit initial pose without replacing any asset variable.
def set_pose(asset_group, x, y, z, yaw_degrees=0):
    asset_group[0].position = [x, y, z]
    asset_group[0].rotation = [0, 0, radians(yaw_degrees)]


# ---------------------------------------------------------------------------
# Initial furniture layout
# ---------------------------------------------------------------------------
# Four individual workstations line the south wall and face into the room.
set_pose(individual_desk_A, 0.80, 0.40, 0.375, 90)
set_pose(individual_desk_B, 2.35, 0.40, 0.375, 90)
set_pose(individual_desk_C, 3.90, 0.40, 0.375, 90)
set_pose(individual_desk_D, 5.80, 0.40, 0.375, 90)

set_pose(task_chair_studio_A, 0.80, 1.35, 0.50, -90)
set_pose(task_chair_studio_B, 2.35, 1.35, 0.50, -90)
set_pose(task_chair_studio_C, 3.90, 1.35, 0.50, -90)
# This chair is assigned to an upper project station because the fourth desk
# faces the required high stool instead.
set_pose(task_chair_studio_D, 5.30, 7.45, 0.50, 90)

# The required high stool is directly in front of individual desk o0058.
set_pose(high_stool_island_A, 5.80, 1.40, 0.375, -90)

# Central fabrication tables leave circulation lanes around the workstations.
set_pose(large_plan_table, 2.25, 3.25, 0.45, 0)
set_pose(prototype_island, 4.55, 3.25, 0.45, 0)
set_pose(drafting_stool_A, 1.30, 3.25, 0.375, 0)
set_pose(high_stool_island_B, 4.55, 2.05, 0.375, 90)
set_pose(high_stool_island_C, 4.55, 4.45, 0.375, -90)
set_pose(high_stool_island_D, 5.45, 3.25, 0.375, 180)
set_pose(mobile_storage_cart_A, 6.55, 3.20, 0.425, 180)

# Lounge furniture occupies the widened middle portion of the room.
set_pose(lounge_armchair_A, 0.55, 4.50, 0.425, 45)
set_pose(lounge_armchair_B, 1.55, 5.70, 0.425, 0)
set_pose(critique_sofa, 3.05, 6.20, 0.425, 90)
set_pose(side_table_lounge, 4.45, 5.80, 0.25, 0)
set_pose(lounge_armchair_C, 5.65, 5.75, 0.425, 180)

# Shelving is positioned away from both windows on the east wall.
set_pose(studio_shelf_A, 6.80, 4.15, 1.00, 180)
set_pose(studio_shelf_B, 2.20, 7.65, 1.00, 90)
set_pose(studio_shelf_C, 6.80, 7.75, 1.00, 180)

# Upper-room project stations.
set_pose(project_bench_A, 3.15, 8.55, 0.45, 90)
set_pose(project_bench_C, 5.35, 8.55, 0.45, 90)
set_pose(drafting_stool_B, 3.15, 7.75, 0.375, 90)
set_pose(drafting_stool_C, 5.35, 7.75, 0.375, 90)
set_pose(mobile_storage_cart_B, 6.55, 7.05, 0.425, 180)

# Project bench o0060 is arranged between drawer units o0027 and o0069.
# Drawer o0069 is flush with the east wall and faces west.
set_pose(side_drawer_unit_A, 3.65, 10.15, 0.325, 90)
set_pose(project_bench_B, 5.15, 10.15, 0.45, 90)
set_pose(side_drawer_unit_D, 6.725, 10.15, 0.325, 180)

set_pose(side_drawer_unit_B, 2.30, 9.45, 0.325, 90)
set_pose(side_drawer_unit_C, 6.60, 6.45, 0.325, 180)

# Wall-mounted rails and clock avoid the two east-wall window openings.
set_pose(wall_shelf_rail_A, 0.11, 3.10, 1.55, 0)
set_pose(wall_shelf_rail_B, 2.85, 10.89, 1.55, 90)
set_pose(wall_shelf_rail_C, 4.25, 10.89, 1.55, 90)
set_pose(wall_shelf_rail_D, 5.65, 10.89, 1.55, 90)
set_pose(wall_clock_studio, 0.025, 2.30, 1.85, 0)


# ---------------------------------------------------------------------------
# Items placed on work surfaces
# ---------------------------------------------------------------------------
# South-wall desks.
set_pose(mouse_A, 0.55, 0.42, 0.77, 90)
set_pose(notebook_A, 0.88, 0.42, 0.76, 90)
set_pose(pen_holder_A, 1.08, 0.43, 0.81, 90)
set_pose(notebook_D, 0.72, 0.62, 0.76, 90)
set_pose(pen_holder_C, 1.08, 0.63, 0.81, 90)
set_pose(desk_lamp_A, 0.48, 0.65, 0.975, 90)

set_pose(notebook_G, 2.18, 0.42, 0.76, 90)
set_pose(notebook_H, 2.48, 0.42, 0.76, 90)
set_pose(desk_lamp_B, 2.02, 0.64, 0.975, 90)
set_pose(desk_lamp_C, 2.68, 0.64, 0.975, 90)

set_pose(notebook_I, 3.75, 0.42, 0.76, 90)
set_pose(notebook_J, 4.05, 0.42, 0.76, 90)
set_pose(desk_lamp_D, 3.58, 0.64, 0.975, 90)
set_pose(mouse_B, 4.18, 0.62, 0.77, 90)

set_pose(mouse_C, 5.48, 0.42, 0.77, 90)
set_pose(sticky_note_pad, 5.72, 0.42, 0.755, 90)
set_pose(file_tray_C, 6.08, 0.45, 0.785, 90)
set_pose(mouse_D, 5.48, 0.65, 0.77, 90)
set_pose(notebook_M, 5.82, 0.64, 0.76, 90)

# Central tables.
set_pose(cutting_mat_A, 2.25, 3.25, 0.905, 0)
set_pose(large_drawing_board, 2.25, 3.25, 0.925, 0)
set_pose(notebook_B, 2.10, 2.45, 0.94, 0)
set_pose(pen_holder_B, 2.55, 2.45, 0.96, 0)
set_pose(notebook_C, 4.55, 3.25, 0.91, 0)

# Shelf-top storage. Storage box o0039 is explicitly on studio shelf o0046.
set_pose(file_tray_A, 6.80, 3.90, 2.035, 0)
set_pose(file_tray_B, 6.80, 4.32, 2.035, 0)
set_pose(storage_box_A, 6.80, 4.15, 2.14, 0)
set_pose(storage_box_B, 6.80, 7.75, 2.14, 0)
set_pose(storage_box_C, 2.20, 7.65, 2.14, 90)

# Lounge accessories.
set_pose(notebook_E, 4.32, 5.72, 0.51, 0)
set_pose(notebook_F, 4.57, 5.88, 0.51, 0)
set_pose(throw_pillow, 3.05, 6.20, 1.075, 90)

# Project benches.
set_pose(cutting_mat_B, 3.15, 8.55, 0.905, 90)
set_pose(small_toolbox, 3.48, 8.55, 1.00, 90)
set_pose(pen_holder_D, 2.82, 8.55, 0.96, 90)

set_pose(cutting_mat_C, 5.35, 8.55, 0.905, 90)
set_pose(tape_roll, 5.72, 8.55, 0.925, 90)
set_pose(notebook_L, 4.98, 8.55, 0.91, 90)

set_pose(notebook_K, 4.82, 10.15, 0.91, 90)
set_pose(marker_set, 5.40, 10.15, 0.92, 90)


# ---------------------------------------------------------------------------
# High-priority semantic constraints
# ---------------------------------------------------------------------------
# Required wall relationship for side drawer unit o0069.
solver.against_wall(side_drawer_unit_D[0], walls[5])
solver.align_with(side_drawer_unit_D[0], AssetInstance(rotation=[0, 0, radians(180)]))

# Keep the project bench centered between the two specified drawer units.
solver.distance_constraint(
    project_bench_B[0], side_drawer_unit_A[0], 1.50, 1.50, weight=10
)
solver.distance_constraint(
    project_bench_B[0], side_drawer_unit_D[0], 1.575, 1.575, weight=10
)
solver.align_with(project_bench_B[0], side_drawer_unit_A[0])

# Individual desk o0058 faces high stool island o0016.
solver.point_towards(individual_desk_D[0], high_stool_island_A[0])
solver.point_towards(high_stool_island_A[0], individual_desk_D[0])

# Required storage-box/shelf relationship.
solver.on_top_of(storage_box_C[0], studio_shelf_B[0])
solver.align_with(storage_box_C[0], studio_shelf_B[0])


# ---------------------------------------------------------------------------
# Support constraints for all elevated objects
# ---------------------------------------------------------------------------
supported_items = [
    (mouse_A, individual_desk_A),
    (notebook_A, individual_desk_A),
    (pen_holder_A, individual_desk_A),
    (notebook_D, individual_desk_A),
    (pen_holder_C, individual_desk_A),
    (desk_lamp_A, individual_desk_A),

    (notebook_G, individual_desk_B),
    (notebook_H, individual_desk_B),
    (desk_lamp_B, individual_desk_B),
    (desk_lamp_C, individual_desk_B),

    (notebook_I, individual_desk_C),
    (notebook_J, individual_desk_C),
    (desk_lamp_D, individual_desk_C),
    (mouse_B, individual_desk_C),

    (mouse_C, individual_desk_D),
    (sticky_note_pad, individual_desk_D),
    (file_tray_C, individual_desk_D),
    (mouse_D, individual_desk_D),
    (notebook_M, individual_desk_D),

    (cutting_mat_A, large_plan_table),
    (large_drawing_board, large_plan_table),
    (notebook_B, large_plan_table),
    (pen_holder_B, large_plan_table),
    (notebook_C, prototype_island),

    (file_tray_A, studio_shelf_A),
    (file_tray_B, studio_shelf_A),
    (storage_box_A, studio_shelf_A),
    (storage_box_B, studio_shelf_C),

    (notebook_E, side_table_lounge),
    (notebook_F, side_table_lounge),
    (throw_pillow, critique_sofa),

    (cutting_mat_B, project_bench_A),
    (small_toolbox, project_bench_A),
    (pen_holder_D, project_bench_A),

    (cutting_mat_C, project_bench_C),
    (tape_roll, project_bench_C),
    (notebook_L, project_bench_C),

    (notebook_K, project_bench_B),
    (marker_set, project_bench_B),
]

for item_group, support_group in supported_items:
    solver.on_top_of(item_group[0], support_group[0])
    solver.align_with(item_group[0], support_group[0])


# Shelves and wall decorations retain their wall relationships.
solver.against_wall(studio_shelf_A[0], walls[5])
solver.against_wall(studio_shelf_C[0], walls[5])
solver.against_wall(wall_shelf_rail_A[0], walls[3])
solver.against_wall(wall_shelf_rail_B[0], walls[6])
solver.against_wall(wall_shelf_rail_C[0], walls[6])
solver.against_wall(wall_shelf_rail_D[0], walls[6])
solver.against_wall(wall_clock_studio[0], walls[3])


# ---------------------------------------------------------------------------
# Pose-preservation constraints
# ---------------------------------------------------------------------------
# Every new asset receives an exact position constraint and an orientation
# constraint. Semantic constraints above are deliberately registered first.
all_new_assets = [
    lounge_armchair_A, mouse_A, notebook_A, drafting_stool_A,
    file_tray_A, file_tray_B, cutting_mat_A, pen_holder_A,
    studio_shelf_A, notebook_B, pen_holder_B, lounge_armchair_B,
    prototype_island, mobile_storage_cart_A, storage_box_A, notebook_C,
    high_stool_island_A, large_plan_table, individual_desk_A, notebook_D,
    pen_holder_C, wall_shelf_rail_A, desk_lamp_A, desk_lamp_B,
    small_toolbox, pen_holder_D, storage_box_B, side_drawer_unit_A,
    lounge_armchair_C, critique_sofa, notebook_E, notebook_F,
    wall_shelf_rail_B, notebook_G, desk_lamp_C, individual_desk_B,
    task_chair_studio_A, notebook_H, high_stool_island_B, storage_box_C,
    task_chair_studio_B, high_stool_island_C, side_drawer_unit_B,
    wall_shelf_rail_C, notebook_I, individual_desk_C, studio_shelf_B,
    drafting_stool_B, desk_lamp_D, mouse_B, side_table_lounge,
    project_bench_A, notebook_J, wall_clock_studio, mouse_C,
    sticky_note_pad, file_tray_C, studio_shelf_C, individual_desk_D,
    notebook_K, project_bench_B, marker_set, drafting_stool_C,
    throw_pillow, side_drawer_unit_C, task_chair_studio_C, notebook_L,
    wall_shelf_rail_D, large_drawing_board, side_drawer_unit_D,
    cutting_mat_B, high_stool_island_D, mouse_D, notebook_M,
    project_bench_C, tape_roll, cutting_mat_C, mobile_storage_cart_B,
    task_chair_studio_D,
]

for asset_group in all_new_assets:
    instance = asset_group[0]
    fixed_position = AssetInstance(position=list(instance.position))
    fixed_orientation = AssetInstance(rotation=list(instance.rotation))

    solver.distance_constraint(
        instance, fixed_position, 0.0, 0.0, weight=10
    )
    solver.align_with(instance, fixed_orientation)

solver.constraints = []
desk_lamp_C[0].position = [2.680000066757202, 0.6399999856948853, 0.9750000238418579]
desk_lamp_C[0].rotation = [0, 0, 1.6053534983636677]
desk_lamp_C[0].optimize = 2
mouse_A[0].position = [0.550000011920929, 0.41999998688697815, 0.7699999809265137]
mouse_A[0].rotation = [0, 0, 1.6179200561263867]
mouse_A[0].optimize = 2
notebook_D[0].position = [0.7200000286102295, 0.6200000047683716, 0.7599999904632568]
notebook_D[0].rotation = [0, 0, 1.6179200561263867]
notebook_D[0].optimize = 2
pen_holder_C[0].position = [1.0800000429153442, 0.6299999952316284, 0.8100000023841858]
pen_holder_C[0].rotation = [0, 0, 1.6179200561263867]
pen_holder_C[0].optimize = 2
lounge_armchair_C[0].position = [5.650000095367432, 5.75, 0.42500001192092896]
lounge_armchair_C[0].rotation = [0, 0, -3.1321678761290697]
lounge_armchair_C[0].optimize = 2
throw_pillow[0].position = [3.049999952316284, 6.199999809265137, 1.0750000476837158]
throw_pillow[0].rotation = [0, 0, 1.586504130025107]
throw_pillow[0].optimize = 2
notebook_H[0].position = [2.4800000190734863, 0.41999998688697815, 0.7599999904632568]
notebook_H[0].rotation = [0, 0, 1.6053534983636677]
notebook_H[0].optimize = 2
small_toolbox[0].position = [3.4800000190734863, 8.550000190734863, 1.0]
small_toolbox[0].rotation = [0, 0, 1.5990707409437288]
small_toolbox[0].optimize = 2
critique_sofa[0].position = [3.049999952316284, 6.199999809265137, 0.42500001192092896]
critique_sofa[0].rotation = [0, 0, 1.586504290712113]
critique_sofa[0].optimize = 2
mouse_B[0].position = [4.179999828338623, 0.6200000047683716, 0.7699999809265137]
mouse_B[0].rotation = [0, 0, 1.6053534983636677]
mouse_B[0].optimize = 2
project_bench_B[0].position = [5.150877475738525, 10.149999618530273, 0.44999998807907104]
project_bench_B[0].rotation = [0, 0, 1.5865045154950463]
project_bench_B[0].optimize = 2
large_drawing_board[0].position = [2.25, 3.25, 0.9199999570846558]
large_drawing_board[0].rotation = [0, 0, 0.03455716474956165]
large_drawing_board[0].optimize = 2
lounge_armchair_B[0].position = [1.5499999523162842, 5.699999809265137, 0.42500001192092896]
lounge_armchair_B[0].rotation = [0, 0, 0.00942477746072377]
lounge_armchair_B[0].optimize = 2
drafting_stool_A[0].position = [1.2999999523162842, 3.25, 0.375]
drafting_stool_A[0].rotation = [0, 0, 0.00942477746072377]
drafting_stool_A[0].optimize = 2
high_stool_island_C[0].position = [4.550000190734863, 4.449999809265137, 0.375]
high_stool_island_C[0].rotation = [0, 0, -1.5613715493341729]
high_stool_island_C[0].optimize = 2
notebook_M[0].position = [5.820000171661377, 0.6399999856948853, 0.7599999904632568]
notebook_M[0].rotation = [0, 0, 1.6179200561263867]
notebook_M[0].optimize = 2
cutting_mat_A[0].position = [2.25, 3.25, 0.9049999713897705]
cutting_mat_A[0].rotation = [0, 0, 0.03455716474956165]
cutting_mat_A[0].optimize = 2
desk_lamp_A[0].position = [0.47999998927116394, 0.6499999761581421, 0.9750000238418579]
desk_lamp_A[0].rotation = [0, 0, 1.6179200561263867]
desk_lamp_A[0].optimize = 2
marker_set[0].position = [5.400000095367432, 10.149999618530273, 0.9199999570846558]
marker_set[0].rotation = [0, 0, 1.5865047284447114]
marker_set[0].optimize = 2
individual_desk_B[0].position = [2.3499999046325684, 0.4000000059604645, 0.375]
individual_desk_B[0].rotation = [0, 0, 1.605353845621573]
individual_desk_B[0].optimize = 2
side_drawer_unit_B[0].position = [2.299999952316284, 9.449999809265137, 0.32499998807907104]
side_drawer_unit_B[0].rotation = [0, 0, 1.5802211042556205]
side_drawer_unit_B[0].optimize = 2
wall_shelf_rail_A[0].position = [0.10999995470046997, 3.0999999046325684, 0.03999999910593033]
wall_shelf_rail_A[0].rotation = [0, 0, 9.472605387085833e-08]
wall_shelf_rail_A[0].optimize = 2
mouse_C[0].position = [5.480000019073486, 0.41999998688697815, 0.7699999809265137]
mouse_C[0].rotation = [0, 0, 1.6179200561263867]
mouse_C[0].optimize = 2
desk_lamp_D[0].position = [3.5799999237060547, 0.6399999856948853, 0.9750000238418579]
desk_lamp_D[0].rotation = [0, 0, 1.6053534983636677]
desk_lamp_D[0].optimize = 2
high_stool_island_D[0].position = [5.449999809265137, 3.25, 0.375]
high_stool_island_D[0].rotation = [0, 0, -3.1321678761290697]
high_stool_island_D[0].optimize = 2
notebook_B[0].position = [2.0999999046325684, 2.450000047683716, 0.9099999666213989]
notebook_B[0].rotation = [0, 0, 0.03455716474956165]
notebook_B[0].optimize = 2
studio_shelf_A[0].position = [6.799999713897705, 4.150000095367432, 1.0]
studio_shelf_A[0].rotation = [0, 0, -3.1415921292451947]
studio_shelf_A[0].optimize = 2
notebook_F[0].position = [4.570000171661377, 5.880000114440918, 0.5099999904632568]
notebook_F[0].rotation = [0, 0, 0.02199120673214388]
notebook_F[0].optimize = 2
storage_box_C[0].position = [2.2222232818603516, 7.650000095367432, 2.140000104904175]
storage_box_C[0].rotation = [0, 0, 1.586504130025107]
storage_box_C[0].optimize = 2
storage_box_A[0].position = [6.734004020690918, 4.150000095367432, 2.140000104904175]
storage_box_A[0].rotation = [0, 0, -3.0958330710465565]
storage_box_A[0].optimize = 2
notebook_G[0].position = [2.180000066757202, 0.41999998688697815, 0.7599999904632568]
notebook_G[0].rotation = [0, 0, 1.6053534983636677]
notebook_G[0].optimize = 2
wall_clock_studio[0].position = [0.02499985694885254, 2.299999952316284, 0.17499999701976776]
wall_clock_studio[0].rotation = [0, 0, 1.018248733869878e-07]
wall_clock_studio[0].optimize = 2
studio_shelf_B[0].position = [2.5967845916748047, 7.650000095367432, 1.0]
studio_shelf_B[0].rotation = [0, 0, 1.586504290712113]
studio_shelf_B[0].optimize = 2
notebook_I[0].position = [3.75, 0.41999998688697815, 0.7599999904632568]
notebook_I[0].rotation = [0, 0, 1.6053534983636677]
notebook_I[0].optimize = 2
desk_lamp_B[0].position = [2.0199999809265137, 0.6399999856948853, 0.9750000238418579]
desk_lamp_B[0].rotation = [0, 0, 1.6053534983636677]
desk_lamp_B[0].optimize = 2
cutting_mat_B[0].position = [3.1500000953674316, 8.550000190734863, 0.9049999713897705]
cutting_mat_B[0].rotation = [0, 0, 1.5990707409437288]
cutting_mat_B[0].optimize = 2
project_bench_C[0].position = [5.349999904632568, 8.550000190734863, 0.44999998807907104]
project_bench_C[0].rotation = [0, 0, 1.5990706612064889]
project_bench_C[0].optimize = 2
storage_box_B[0].position = [6.73309850692749, 7.75, 2.140000104904175]
storage_box_B[0].rotation = [0, 0, -3.100633258264365]
storage_box_B[0].optimize = 2
wall_shelf_rail_B[0].position = [2.8499999046325684, 10.888906478881836, 0.03999999910593033]
wall_shelf_rail_B[0].rotation = [0, 0, -1.5713324088311094]
wall_shelf_rail_B[0].optimize = 2
drafting_stool_C[0].position = [5.349999904632568, 7.75, 0.375]
drafting_stool_C[0].rotation = [0, 0, 1.5802211042556205]
drafting_stool_C[0].optimize = 2
wall_shelf_rail_C[0].position = [4.25, 10.888906478881836, 0.03999999910593033]
wall_shelf_rail_C[0].rotation = [0, 0, -1.5713324088311094]
wall_shelf_rail_C[0].optimize = 2
mobile_storage_cart_B[0].position = [6.550000190734863, 7.050000190734863, 0.42500001192092896]
mobile_storage_cart_B[0].rotation = [0, 0, -3.1321678761290697]
mobile_storage_cart_B[0].optimize = 2
pen_holder_B[0].position = [2.549999952316284, 2.450000047683716, 0.9599999785423279]
pen_holder_B[0].rotation = [0, 0, 0.03455716474956165]
pen_holder_B[0].optimize = 2
file_tray_A[0].position = [6.800000190734863, 3.9000000953674316, 2.0350000858306885]
file_tray_A[0].rotation = [0, 0, -3.0958330710465565]
file_tray_A[0].optimize = 2
mouse_D[0].position = [5.480000019073486, 0.6499999761581421, 0.7699999809265137]
mouse_D[0].rotation = [0, 0, 1.6179200561263867]
mouse_D[0].optimize = 2
project_bench_A[0].position = [3.1500000953674316, 8.550000190734863, 0.44999998807907104]
project_bench_A[0].rotation = [0, 0, 1.5990706612064889]
project_bench_A[0].optimize = 2
large_plan_table[0].position = [2.25, 3.25, 0.44999998807907104]
large_plan_table[0].rotation = [0, 0, 0.03455751882667646]
large_plan_table[0].optimize = 2
wall_shelf_rail_D[0].position = [5.650000095367432, 10.888906478881836, 0.03999999910593033]
wall_shelf_rail_D[0].rotation = [0, 0, -1.5713324088311094]
wall_shelf_rail_D[0].optimize = 2
task_chair_studio_D[0].position = [5.300000190734863, 7.449999809265137, 0.5]
task_chair_studio_D[0].rotation = [0, 0, 1.5802211042556205]
task_chair_studio_D[0].optimize = 2
notebook_J[0].position = [4.050000190734863, 0.41999998688697815, 0.7599999904632568]
notebook_J[0].rotation = [0, 0, 1.6053534983636677]
notebook_J[0].optimize = 2
sticky_note_pad[0].position = [5.71999979019165, 0.41999998688697815, 0.7549999952316284]
sticky_note_pad[0].rotation = [0, 0, 1.6179200561263867]
sticky_note_pad[0].optimize = 2
task_chair_studio_A[0].position = [0.800000011920929, 1.350000023841858, 0.5]
task_chair_studio_A[0].rotation = [0, 0, -1.5613715493341729]
task_chair_studio_A[0].optimize = 2
task_chair_studio_B[0].position = [2.3499999046325684, 1.350000023841858, 0.5]
task_chair_studio_B[0].rotation = [0, 0, -1.5613715493341729]
task_chair_studio_B[0].optimize = 2
drafting_stool_B[0].position = [3.1500000953674316, 7.75, 0.375]
drafting_stool_B[0].rotation = [0, 0, 1.5802211042556205]
drafting_stool_B[0].optimize = 2
side_drawer_unit_D[0].position = [6.724999904632568, 10.149999618530273, 0.32499998807907104]
side_drawer_unit_D[0].rotation = [0, 0, 3.141592273197053]
side_drawer_unit_D[0].optimize = 2
cutting_mat_C[0].position = [5.349999904632568, 8.550000190734863, 0.9049999713897705]
cutting_mat_C[0].rotation = [0, 0, 1.5990707409437288]
cutting_mat_C[0].optimize = 2
studio_shelf_C[0].position = [6.799999237060547, 7.75, 1.0]
studio_shelf_C[0].rotation = [0, 0, 3.1415922753821093]
studio_shelf_C[0].optimize = 2
file_tray_C[0].position = [6.079999923706055, 0.44999998807907104, 0.7850000262260437]
file_tray_C[0].rotation = [0, 0, 1.6179200561263867]
file_tray_C[0].optimize = 2
notebook_A[0].position = [0.8799999952316284, 0.41999998688697815, 0.7599999904632568]
notebook_A[0].rotation = [0, 0, 1.6179200561263867]
notebook_A[0].optimize = 2
high_stool_island_A[0].position = [5.800000190734863, 1.399999976158142, 0.375]
high_stool_island_A[0].rotation = [0, 0, -1.5550883628776802]
high_stool_island_A[0].optimize = 2
individual_desk_C[0].position = [3.9000000953674316, 0.4000000059604645, 0.375]
individual_desk_C[0].rotation = [0, 0, 1.605353845621573]
individual_desk_C[0].optimize = 2
task_chair_studio_C[0].position = [3.9000000953674316, 1.350000023841858, 0.5]
task_chair_studio_C[0].rotation = [0, 0, -1.5613715493341729]
task_chair_studio_C[0].optimize = 2
pen_holder_A[0].position = [1.0800000429153442, 0.4300000071525574, 0.8100000023841858]
pen_holder_A[0].rotation = [0, 0, 1.6179200561263867]
pen_holder_A[0].optimize = 2
prototype_island[0].position = [4.550000190734863, 3.25, 0.44999998807907104]
prototype_island[0].rotation = [0, 0, 0.0157079639172164]
prototype_island[0].optimize = 2
individual_desk_A[0].position = [0.800000011920929, 0.4000000059604645, 0.375]
individual_desk_A[0].rotation = [0, 0, 1.617920218713948]
individual_desk_A[0].optimize = 2
pen_holder_D[0].position = [2.819999933242798, 8.550000190734863, 0.9599999785423279]
pen_holder_D[0].rotation = [0, 0, 1.5990707409437288]
pen_holder_D[0].optimize = 2
notebook_E[0].position = [4.320000171661377, 5.71999979019165, 0.5099999904632568]
notebook_E[0].rotation = [0, 0, 0.02199120673214388]
notebook_E[0].optimize = 2
individual_desk_D[0].position = [5.800000190734863, 0.4000000059604645, 0.375]
individual_desk_D[0].rotation = [0, 0, 1.617920218713948]
individual_desk_D[0].optimize = 2
mobile_storage_cart_A[0].position = [6.550000190734863, 3.200000047683716, 0.42500001192092896]
mobile_storage_cart_A[0].rotation = [0, 0, -3.1321678761290697]
mobile_storage_cart_A[0].optimize = 2
file_tray_B[0].position = [6.800000190734863, 4.320000171661377, 2.0350000858306885]
file_tray_B[0].rotation = [0, 0, -3.0958330710465565]
file_tray_B[0].optimize = 2
side_table_lounge[0].position = [4.449999809265137, 5.800000190734863, 0.25]
side_table_lounge[0].rotation = [0, 0, 0.021991148286022624]
side_table_lounge[0].optimize = 2
side_drawer_unit_A[0].position = [3.6500000953674316, 10.149999618530273, 0.32499998807907104]
side_drawer_unit_A[0].rotation = [0, 0, 1.586504290712113]
side_drawer_unit_A[0].optimize = 2
notebook_K[0].position = [4.820000171661377, 10.149999618530273, 0.9099999666213989]
notebook_K[0].rotation = [0, 0, 1.5865047284447114]
notebook_K[0].optimize = 2
tape_roll[0].position = [5.71999979019165, 8.550000190734863, 0.9249999523162842]
tape_roll[0].rotation = [0, 0, 1.5990707409437288]
tape_roll[0].optimize = 2
side_drawer_unit_C[0].position = [6.599999904632568, 6.449999809265137, 0.32499998807907104]
side_drawer_unit_C[0].rotation = [0, 0, -3.1321678761290697]
side_drawer_unit_C[0].optimize = 2
notebook_L[0].position = [4.980000019073486, 8.550000190734863, 0.9099999666213989]
notebook_L[0].rotation = [0, 0, 1.5990707409437288]
notebook_L[0].optimize = 2
high_stool_island_B[0].position = [4.550000190734863, 2.049999952316284, 0.375]
high_stool_island_B[0].rotation = [0, 0, 1.5802211042556205]
high_stool_island_B[0].optimize = 2
notebook_C[0].position = [4.550000190734863, 3.25, 0.9099999666213989]
notebook_C[0].rotation = [0, 0, 0.01570787941852103]
notebook_C[0].optimize = 2
lounge_armchair_A[0].position = [0.6010141372680664, 4.398985862731934, 0.42500001192092896]
lounge_armchair_A[0].rotation = [0, 0, 0.7948229285630478]
lounge_armchair_A[0].optimize = 2

