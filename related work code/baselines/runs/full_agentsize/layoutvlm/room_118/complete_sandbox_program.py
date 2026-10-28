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
    Wall(corner1=[1.00, 6.00, 0.00], corner2=[1.00, 3.00, 0.00]),
    Wall(corner1=[1.00, 3.00, 0.00], corner2=[0.00, 3.00, 0.00]),
    Wall(corner1=[0.00, 3.00, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[12.00, 0.00, 0.00]),
    Wall(corner1=[12.00, 0.00, 0.00], corner2=[12.00, 2.00, 0.00]),
    Wall(corner1=[12.00, 2.00, 0.00], corner2=[8.00, 2.00, 0.00]),
    Wall(corner1=[8.00, 2.00, 0.00], corner2=[8.00, 4.00, 0.00]),
    Wall(corner1=[8.00, 4.00, 0.00], corner2=[6.00, 4.00, 0.00]),
    Wall(corner1=[6.00, 4.00, 0.00], corner2=[6.00, 6.00, 0.00]),
    Wall(corner1=[6.00, 6.00, 0.00], corner2=[1.00, 6.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
picture_frame_A = Assets(description="Picture of trees by a lake in black picture frame.", size=[0.05, 0.60, 0.45], placements=[AssetInstance() for _ in range(1)])
wall_art_print_A = Assets(description="A blue painting in a black frame.", size=[0.04, 0.70, 0.90], placements=[AssetInstance() for _ in range(1)])
work_bench_desk_A = Assets(description="A wood desk with four round metal legs with a computer on top.", size=[0.75, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
ring_binder_A = Assets(description="A brown book with silver corners.", size=[0.32, 0.28, 0.07], placements=[AssetInstance() for _ in range(1)])
ring_binder_B = Assets(description="A brown book with silver corners.", size=[0.32, 0.28, 0.07], placements=[AssetInstance() for _ in range(1)])
small_side_table_A = Assets(description="A stool with a round seat and four legs.", size=[0.42, 0.42, 0.48], placements=[AssetInstance() for _ in range(1)])
task_chair_A = Assets(description="A black and grey rolling desk chair with arms.", size=[0.65, 0.65, 1.05], placements=[AssetInstance() for _ in range(1)])
high_stool_A = Assets(description="A black seat on four wooden legs connected by black metal bars.", size=[0.48, 0.48, 0.76], placements=[AssetInstance() for _ in range(1)])
tall_bookshelf_A = Assets(description="It is a tall set of shelves made of wood and metal.", size=[0.38, 0.90, 2.00], placements=[AssetInstance() for _ in range(1)])
whiteboard_panel_A = Assets(description="A white rectangular poster with black blue and orange marks and irregular writing.", size=[0.04, 1.50, 0.90], placements=[AssetInstance() for _ in range(1)])
task_chair_B = Assets(description="A black and grey rolling desk chair with arms.", size=[0.65, 0.65, 1.05], placements=[AssetInstance() for _ in range(1)])
low_storage_credenza_A = Assets(description="A light brown wooden console table with 4 cabinets, on 4 cylindrical wooden legs.", size=[0.45, 1.80, 0.75], placements=[AssetInstance() for _ in range(1)])
low_storage_credenza_B = Assets(description="A light brown wooden console table with 4 cabinets, on 4 cylindrical wooden legs.", size=[0.45, 1.80, 0.75], placements=[AssetInstance() for _ in range(1)])
high_collaboration_table = Assets(description="A tan desk with a white frame.", size=[0.80, 1.80, 1.05], placements=[AssetInstance() for _ in range(1)])
acoustic_wall_panel_A = Assets(description="A painting of a woman covered with white clouds in a gold frame.", size=[0.05, 0.80, 1.20], placements=[AssetInstance() for _ in range(1)])
picture_frame_B = Assets(description="Picture of trees by a lake in black picture frame.", size=[0.05, 0.60, 0.45], placements=[AssetInstance() for _ in range(1)])
floor_planter_large_A = Assets(description="floor planter large", size=[0.55, 0.55, 1.10], placements=[AssetInstance() for _ in range(1)])
ring_binder_C = Assets(description="A brown book with silver corners.", size=[0.32, 0.28, 0.07], placements=[AssetInstance() for _ in range(1)])
desk_organizer = Assets(description="Red wood toolbox with handle.", size=[0.25, 0.45, 0.30], placements=[AssetInstance() for _ in range(1)])
tall_bookshelf_B = Assets(description="It is a tall set of shelves made of wood and metal.", size=[0.38, 0.90, 2.00], placements=[AssetInstance() for _ in range(1)])
wall_art_print_B = Assets(description="A blue painting in a black frame.", size=[0.04, 0.70, 0.90], placements=[AssetInstance() for _ in range(1)])
tall_bookshelf_C = Assets(description="It is a tall set of shelves made of wood and metal.", size=[0.38, 0.90, 2.00], placements=[AssetInstance() for _ in range(1)])
task_chair_C = Assets(description="A black and grey rolling desk chair with arms.", size=[0.65, 0.65, 1.05], placements=[AssetInstance() for _ in range(1)])
acoustic_wall_panel_B = Assets(description="A painting of a woman covered with white clouds in a gold frame.", size=[0.05, 0.80, 1.20], placements=[AssetInstance() for _ in range(1)])
tall_bookshelf_D = Assets(description="It is a tall set of shelves made of wood and metal.", size=[0.38, 0.90, 2.00], placements=[AssetInstance() for _ in range(1)])
whiteboard_panel_B = Assets(description="A white rectangular poster with black blue and orange marks and irregular writing.", size=[0.04, 1.50, 0.90], placements=[AssetInstance() for _ in range(1)])
high_stool_B = Assets(description="A black seat on four wooden legs connected by black metal bars.", size=[0.48, 0.48, 0.76], placements=[AssetInstance() for _ in range(1)])
task_chair_D = Assets(description="A black and grey rolling desk chair with arms.", size=[0.65, 0.65, 1.05], placements=[AssetInstance() for _ in range(1)])
floor_planter_large_B = Assets(description="floor planter large", size=[0.55, 0.55, 1.10], placements=[AssetInstance() for _ in range(1)])
task_chair_E = Assets(description="A black and grey rolling desk chair with arms.", size=[0.65, 0.65, 1.05], placements=[AssetInstance() for _ in range(1)])
wall_art_print_C = Assets(description="A blue painting in a black frame.", size=[0.04, 0.70, 0.90], placements=[AssetInstance() for _ in range(1)])
work_bench_desk_B = Assets(description="A wood desk with four round metal legs with a computer on top.", size=[0.75, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
task_chair_F = Assets(description="A black and grey rolling desk chair with arms.", size=[0.65, 0.65, 1.05], placements=[AssetInstance() for _ in range(1)])
picture_frame_C = Assets(description="Picture of trees by a lake in black picture frame.", size=[0.05, 0.60, 0.45], placements=[AssetInstance() for _ in range(1)])
small_side_table_B = Assets(description="A stool with a round seat and four legs.", size=[0.42, 0.42, 0.48], placements=[AssetInstance() for _ in range(1)])
floor_planter_large_C = Assets(description="floor planter large", size=[0.55, 0.55, 1.10], placements=[AssetInstance() for _ in range(1)])
acoustic_wall_panel_C = Assets(description="A painting of a woman covered with white clouds in a gold frame.", size=[0.05, 0.80, 1.20], placements=[AssetInstance() for _ in range(1)])
task_chair_G = Assets(description="A black and grey rolling desk chair with arms.", size=[0.65, 0.65, 1.05], placements=[AssetInstance() for _ in range(1)])
low_storage_credenza_C = Assets(description="A light brown wooden console table with 4 cabinets, on 4 cylindrical wooden legs.", size=[0.45, 1.80, 0.75], placements=[AssetInstance() for _ in range(1)])
ring_binder_D = Assets(description="A pink and grey book with a grey label.", size=[0.32, 0.28, 0.07], placements=[AssetInstance() for _ in range(1)])
floor_planter_large_D = Assets(description="floor planter large", size=[0.55, 0.55, 1.10], placements=[AssetInstance() for _ in range(1)])
stack_of_files = Assets(description="a colorful stack of blocks with various creatures, such as a frog, bird, and green monster, sitting on top.", size=[0.30, 0.35, 0.25], placements=[AssetInstance() for _ in range(1)])
whiteboard_panel_C = Assets(description="A white rectangular poster with black blue and orange marks and irregular writing.", size=[0.04, 1.50, 0.90], placements=[AssetInstance() for _ in range(1)])
side_return_unit = Assets(description="A wooden nightstand with both its drawers open.", size=[0.50, 0.50, 0.65], placements=[AssetInstance() for _ in range(1)])

picture_frame_A[0].instance_id = 'picture_frame_A_0'
wall_art_print_A[0].instance_id = 'wall_art_print_A_0'
work_bench_desk_A[0].instance_id = 'work_bench_desk_A_0'
ring_binder_A[0].instance_id = 'ring_binder_A_0'
ring_binder_B[0].instance_id = 'ring_binder_B_0'
small_side_table_A[0].instance_id = 'small_side_table_A_0'
task_chair_A[0].instance_id = 'task_chair_A_0'
high_stool_A[0].instance_id = 'high_stool_A_0'
tall_bookshelf_A[0].instance_id = 'tall_bookshelf_A_0'
whiteboard_panel_A[0].instance_id = 'whiteboard_panel_A_0'
task_chair_B[0].instance_id = 'task_chair_B_0'
low_storage_credenza_A[0].instance_id = 'low_storage_credenza_A_0'
low_storage_credenza_B[0].instance_id = 'low_storage_credenza_B_0'
high_collaboration_table[0].instance_id = 'high_collaboration_table_0'
acoustic_wall_panel_A[0].instance_id = 'acoustic_wall_panel_A_0'
picture_frame_B[0].instance_id = 'picture_frame_B_0'
floor_planter_large_A[0].instance_id = 'floor_planter_large_A_0'
ring_binder_C[0].instance_id = 'ring_binder_C_0'
desk_organizer[0].instance_id = 'desk_organizer_0'
tall_bookshelf_B[0].instance_id = 'tall_bookshelf_B_0'
wall_art_print_B[0].instance_id = 'wall_art_print_B_0'
tall_bookshelf_C[0].instance_id = 'tall_bookshelf_C_0'
task_chair_C[0].instance_id = 'task_chair_C_0'
acoustic_wall_panel_B[0].instance_id = 'acoustic_wall_panel_B_0'
tall_bookshelf_D[0].instance_id = 'tall_bookshelf_D_0'
whiteboard_panel_B[0].instance_id = 'whiteboard_panel_B_0'
high_stool_B[0].instance_id = 'high_stool_B_0'
task_chair_D[0].instance_id = 'task_chair_D_0'
floor_planter_large_B[0].instance_id = 'floor_planter_large_B_0'
task_chair_E[0].instance_id = 'task_chair_E_0'
wall_art_print_C[0].instance_id = 'wall_art_print_C_0'
work_bench_desk_B[0].instance_id = 'work_bench_desk_B_0'
task_chair_F[0].instance_id = 'task_chair_F_0'
picture_frame_C[0].instance_id = 'picture_frame_C_0'
small_side_table_B[0].instance_id = 'small_side_table_B_0'
floor_planter_large_C[0].instance_id = 'floor_planter_large_C_0'
acoustic_wall_panel_C[0].instance_id = 'acoustic_wall_panel_C_0'
task_chair_G[0].instance_id = 'task_chair_G_0'
low_storage_credenza_C[0].instance_id = 'low_storage_credenza_C_0'
ring_binder_D[0].instance_id = 'ring_binder_D_0'
floor_planter_large_D[0].instance_id = 'floor_planter_large_D_0'
stack_of_files[0].instance_id = 'stack_of_files_0'
whiteboard_panel_C[0].instance_id = 'whiteboard_panel_C_0'
side_return_unit[0].instance_id = 'side_return_unit_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'
walls[8].instance_id = 'walls_8'
walls[9].instance_id = 'walls_9'

picture_frame_A[0].position = [8.006560739239255, 0.9311789266139359, 0.225]
picture_frame_A[0].rotation = [0, 0, 0]
wall_art_print_A[0].position = [3.2960445152370985, 5.77411449268908, 0.45]
wall_art_print_A[0].rotation = [0, 0, 0]
work_bench_desk_A[0].position = [8.086376315161736, 0.2859783370444817, 0.375]
work_bench_desk_A[0].rotation = [0, 0, 0]
ring_binder_A[0].position = [4.243531475881206, 1.782033943197074, 0.035]
ring_binder_A[0].rotation = [0, 0, 0]
ring_binder_B[0].position = [4.059752114292143, 5.094923340922424, 0.035]
ring_binder_B[0].rotation = [0, 0, 0]
small_side_table_A[0].position = [1.7722115621627852, 2.741293055994607, 0.24]
small_side_table_A[0].rotation = [0, 0, 0]
task_chair_A[0].position = [10.363921366682737, 1.5809974844222017, 0.525]
task_chair_A[0].rotation = [0, 0, 0]
high_stool_A[0].position = [0.0049086351609171075, 0.6386285910365779, 0.38]
high_stool_A[0].rotation = [0, 0, 0]
tall_bookshelf_A[0].position = [3.1890111228727074, 0.09180561422652089, 1.0]
tall_bookshelf_A[0].rotation = [0, 0, 0]
whiteboard_panel_A[0].position = [4.669701536140998, 3.082114011856932, 0.45]
whiteboard_panel_A[0].rotation = [0, 0, 0]
task_chair_B[0].position = [6.339148436718004, 3.4047417404735167, 0.525]
task_chair_B[0].rotation = [0, 0, 0]
low_storage_credenza_A[0].position = [6.765760598534751, 3.577426070533905, 0.375]
low_storage_credenza_A[0].rotation = [0, 0, 0]
low_storage_credenza_B[0].position = [2.3565646876569466, 0.6925982426293813, 0.375]
low_storage_credenza_B[0].rotation = [0, 0, 0]
high_collaboration_table[0].position = [1.695374488643751, 5.146541379915911, 0.525]
high_collaboration_table[0].rotation = [0, 0, 0]
acoustic_wall_panel_A[0].position = [5.2757812388363075, 1.1343315623072434, 0.6]
acoustic_wall_panel_A[0].rotation = [0, 0, 0]
picture_frame_B[0].position = [8.597447336507756, 0.0036174304414171576, 0.225]
picture_frame_B[0].rotation = [0, 0, 0]
floor_planter_large_A[0].position = [6.139166698165561, 1.3010469016829627, 0.55]
floor_planter_large_A[0].rotation = [0, 0, 0]
ring_binder_C[0].position = [2.7434602141054327, 5.402984194693687, 0.035]
ring_binder_C[0].rotation = [0, 0, 0]
desk_organizer[0].position = [5.951502141420708, 3.3035196378209752, 0.15]
desk_organizer[0].rotation = [0, 0, 0]
tall_bookshelf_B[0].position = [0.6040472038717408, 0.4377896249560118, 1.0]
tall_bookshelf_B[0].rotation = [0, 0, 0]
wall_art_print_B[0].position = [5.313115651478771, 0.052702255900920925, 0.45]
wall_art_print_B[0].rotation = [0, 0, 0]
tall_bookshelf_C[0].position = [7.58274712537624, 0.06843348166511487, 1.0]
tall_bookshelf_C[0].rotation = [0, 0, 0]
task_chair_C[0].position = [9.530910587856653, 0.034919081209410674, 0.525]
task_chair_C[0].rotation = [0, 0, 0]
acoustic_wall_panel_B[0].position = [1.939023509868938, 2.739541866126011, 0.6]
acoustic_wall_panel_B[0].rotation = [0, 0, 0]
tall_bookshelf_D[0].position = [2.45855892267525, 3.3226382177402662, 1.0]
tall_bookshelf_D[0].rotation = [0, 0, 0]
whiteboard_panel_B[0].position = [9.532506821190367, 1.8392930741386622, 0.45]
whiteboard_panel_B[0].rotation = [0, 0, 0]
high_stool_B[0].position = [4.382754919605604, 5.948012727252787, 0.38]
high_stool_B[0].rotation = [0, 0, 0]
task_chair_D[0].position = [4.508865834938639, 2.57386416798155, 0.525]
task_chair_D[0].rotation = [0, 0, 0]
floor_planter_large_B[0].position = [5.405932559805633, 4.256637093115888, 0.55]
floor_planter_large_B[0].rotation = [0, 0, 0]
task_chair_E[0].position = [0.6069343839826575, 1.6290583690691898, 0.525]
task_chair_E[0].rotation = [0, 0, 0]
wall_art_print_C[0].position = [5.932652525597833, 3.697738401269926, 0.45]
wall_art_print_C[0].rotation = [0, 0, 0]
work_bench_desk_B[0].position = [1.0304321059994854, 2.506470891382042, 0.375]
work_bench_desk_B[0].rotation = [0, 0, 0]
task_chair_F[0].position = [6.2260274097113495, 1.3832376164970228, 0.525]
task_chair_F[0].rotation = [0, 0, 0]
picture_frame_C[0].position = [11.4833945255035, 0.2815233196195783, 0.225]
picture_frame_C[0].rotation = [0, 0, 0]
small_side_table_B[0].position = [10.202198200831162, 1.4196218317583966, 0.24]
small_side_table_B[0].rotation = [0, 0, 0]
floor_planter_large_C[0].position = [8.106691833814384, 1.596665406094651, 0.55]
floor_planter_large_C[0].rotation = [0, 0, 0]
acoustic_wall_panel_C[0].position = [11.995727333608505, 0.5873205148386977, 0.6]
acoustic_wall_panel_C[0].rotation = [0, 0, 0]
task_chair_G[0].position = [5.426472674835061, 3.3865601371017355, 0.525]
task_chair_G[0].rotation = [0, 0, 0]
low_storage_credenza_C[0].position = [11.883614960729577, 1.8836603171461748, 0.375]
low_storage_credenza_C[0].rotation = [0, 0, 0]
ring_binder_D[0].position = [8.097512694836343, 0.9236346226787082, 0.035]
ring_binder_D[0].rotation = [0, 0, 0]
floor_planter_large_D[0].position = [3.961746268923699, 2.1519839463899544, 0.55]
floor_planter_large_D[0].rotation = [0, 0, 0]
stack_of_files[0].position = [7.903994519555718, 1.9487348320423523, 0.125]
stack_of_files[0].rotation = [0, 0, 0]
whiteboard_panel_C[0].position = [3.7034704502452094, 4.362327450029916, 0.45]
whiteboard_panel_C[0].rotation = [0, 0, 0]
side_return_unit[0].position = [5.082743550647159, 3.169124891560371, 0.325]
side_return_unit[0].rotation = [0, 0, 0]
picture_frame_A[0].position = [8.006560739239255, 0.9311789266139359, 0.225]
picture_frame_A[0].rotation = [0, 0, 0]
wall_art_print_A[0].position = [3.2960445152370985, 5.77411449268908, 0.45]
wall_art_print_A[0].rotation = [0, 0, 0]
work_bench_desk_A[0].position = [8.086376315161736, 0.2859783370444817, 0.375]
work_bench_desk_A[0].rotation = [0, 0, 0]
ring_binder_A[0].position = [4.243531475881206, 1.782033943197074, 0.035]
ring_binder_A[0].rotation = [0, 0, 0]
ring_binder_B[0].position = [4.059752114292143, 5.094923340922424, 0.035]
ring_binder_B[0].rotation = [0, 0, 0]
small_side_table_A[0].position = [1.7722115621627852, 2.741293055994607, 0.24]
small_side_table_A[0].rotation = [0, 0, 0]
task_chair_A[0].position = [10.363921366682737, 1.5809974844222017, 0.525]
task_chair_A[0].rotation = [0, 0, 0]
high_stool_A[0].position = [0.0049086351609171075, 0.6386285910365779, 0.38]
high_stool_A[0].rotation = [0, 0, 0]
tall_bookshelf_A[0].position = [3.1890111228727074, 0.09180561422652089, 1.0]
tall_bookshelf_A[0].rotation = [0, 0, 0]
whiteboard_panel_A[0].position = [4.669701536140998, 3.082114011856932, 0.45]
whiteboard_panel_A[0].rotation = [0, 0, 0]
task_chair_B[0].position = [6.339148436718004, 3.4047417404735167, 0.525]
task_chair_B[0].rotation = [0, 0, 0]
low_storage_credenza_A[0].position = [6.765760598534751, 3.577426070533905, 0.375]
low_storage_credenza_A[0].rotation = [0, 0, 0]
low_storage_credenza_B[0].position = [2.3565646876569466, 0.6925982426293813, 0.375]
low_storage_credenza_B[0].rotation = [0, 0, 0]
high_collaboration_table[0].position = [1.695374488643751, 5.146541379915911, 0.525]
high_collaboration_table[0].rotation = [0, 0, 0]
acoustic_wall_panel_A[0].position = [5.2757812388363075, 1.1343315623072434, 0.6]
acoustic_wall_panel_A[0].rotation = [0, 0, 0]
picture_frame_B[0].position = [8.597447336507756, 0.0036174304414171576, 0.225]
picture_frame_B[0].rotation = [0, 0, 0]
floor_planter_large_A[0].position = [6.139166698165561, 1.3010469016829627, 0.55]
floor_planter_large_A[0].rotation = [0, 0, 0]
ring_binder_C[0].position = [2.7434602141054327, 5.402984194693687, 0.035]
ring_binder_C[0].rotation = [0, 0, 0]
desk_organizer[0].position = [5.951502141420708, 3.3035196378209752, 0.15]
desk_organizer[0].rotation = [0, 0, 0]
tall_bookshelf_B[0].position = [0.6040472038717408, 0.4377896249560118, 1.0]
tall_bookshelf_B[0].rotation = [0, 0, 0]
wall_art_print_B[0].position = [5.313115651478771, 0.052702255900920925, 0.45]
wall_art_print_B[0].rotation = [0, 0, 0]
tall_bookshelf_C[0].position = [7.58274712537624, 0.06843348166511487, 1.0]
tall_bookshelf_C[0].rotation = [0, 0, 0]
task_chair_C[0].position = [9.530910587856653, 0.034919081209410674, 0.525]
task_chair_C[0].rotation = [0, 0, 0]
acoustic_wall_panel_B[0].position = [1.939023509868938, 2.739541866126011, 0.6]
acoustic_wall_panel_B[0].rotation = [0, 0, 0]
tall_bookshelf_D[0].position = [2.45855892267525, 3.3226382177402662, 1.0]
tall_bookshelf_D[0].rotation = [0, 0, 0]
whiteboard_panel_B[0].position = [9.532506821190367, 1.8392930741386622, 0.45]
whiteboard_panel_B[0].rotation = [0, 0, 0]
high_stool_B[0].position = [4.382754919605604, 5.948012727252787, 0.38]
high_stool_B[0].rotation = [0, 0, 0]
task_chair_D[0].position = [4.508865834938639, 2.57386416798155, 0.525]
task_chair_D[0].rotation = [0, 0, 0]
floor_planter_large_B[0].position = [5.405932559805633, 4.256637093115888, 0.55]
floor_planter_large_B[0].rotation = [0, 0, 0]
task_chair_E[0].position = [0.6069343839826575, 1.6290583690691898, 0.525]
task_chair_E[0].rotation = [0, 0, 0]
wall_art_print_C[0].position = [5.932652525597833, 3.697738401269926, 0.45]
wall_art_print_C[0].rotation = [0, 0, 0]
work_bench_desk_B[0].position = [1.0304321059994854, 2.506470891382042, 0.375]
work_bench_desk_B[0].rotation = [0, 0, 0]
task_chair_F[0].position = [6.2260274097113495, 1.3832376164970228, 0.525]
task_chair_F[0].rotation = [0, 0, 0]
picture_frame_C[0].position = [11.4833945255035, 0.2815233196195783, 0.225]
picture_frame_C[0].rotation = [0, 0, 0]
small_side_table_B[0].position = [10.202198200831162, 1.4196218317583966, 0.24]
small_side_table_B[0].rotation = [0, 0, 0]
floor_planter_large_C[0].position = [8.106691833814384, 1.596665406094651, 0.55]
floor_planter_large_C[0].rotation = [0, 0, 0]
acoustic_wall_panel_C[0].position = [11.995727333608505, 0.5873205148386977, 0.6]
acoustic_wall_panel_C[0].rotation = [0, 0, 0]
task_chair_G[0].position = [5.426472674835061, 3.3865601371017355, 0.525]
task_chair_G[0].rotation = [0, 0, 0]
low_storage_credenza_C[0].position = [11.883614960729577, 1.8836603171461748, 0.375]
low_storage_credenza_C[0].rotation = [0, 0, 0]
ring_binder_D[0].position = [8.097512694836343, 0.9236346226787082, 0.035]
ring_binder_D[0].rotation = [0, 0, 0]
floor_planter_large_D[0].position = [3.961746268923699, 2.1519839463899544, 0.55]
floor_planter_large_D[0].rotation = [0, 0, 0]
stack_of_files[0].position = [7.903994519555718, 1.9487348320423523, 0.125]
stack_of_files[0].rotation = [0, 0, 0]
whiteboard_panel_C[0].position = [3.7034704502452094, 4.362327450029916, 0.45]
whiteboard_panel_C[0].rotation = [0, 0, 0]
side_return_unit[0].position = [5.082743550647159, 3.169124891560371, 0.325]
side_return_unit[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed-point helpers keep the carefully planned non-overlapping layout stable.
# Each call adds both an exact position constraint and an orientation constraint.
def _place(instance, position, rotation_degrees, facing_point):
    instance.position = position
    instance.rotation = [0, 0, radians(rotation_degrees)]
    solver.distance_constraint(
        instance,
        AssetInstance(position=position),
        0,
        0,
        weight=10,
    )
    solver.point_towards(
        instance,
        AssetInstance(position=facing_point),
        weight=10,
    ) if False else solver.point_towards(
        instance,
        AssetInstance(position=facing_point),
    )


# ---------------------------------------------------------------------------
# Primary work area in the southwest and center-west portions of the room.
# Desk A is oriented east-west and has its chair on the north side.
# ---------------------------------------------------------------------------
_place(
    work_bench_desk_A[0],
    [2.00, 1.00, 0.375],
    90,
    [2.00, 2.00, 0.375],
)
_place(
    task_chair_A[0],
    [2.00, 1.85, 0.525],
    -90,
    [2.00, 1.00, 0.525],
)

# Desk B occupies the deeper central part of the room, away from the doorway.
_place(
    work_bench_desk_B[0],
    [4.00, 3.20, 0.375],
    90,
    [4.00, 4.20, 0.375],
)
_place(
    task_chair_B[0],
    [4.00, 2.35, 0.525],
    90,
    [4.00, 3.20, 0.525],
)

# Reinforce the functional relationships between each work chair and desk.
solver.distance_constraint(task_chair_A[0], work_bench_desk_A[0], 0.75, 1.05, weight=10)
solver.point_towards(task_chair_A[0], work_bench_desk_A[0])
solver.distance_constraint(task_chair_B[0], work_bench_desk_B[0], 0.75, 1.05, weight=10)
solver.point_towards(task_chair_B[0], work_bench_desk_B[0])


# ---------------------------------------------------------------------------
# Five-seat collaboration table in the broad lower-right area.
# Its north edge remains below y=1.50, leaving the route from the door at
# (6.98, 4.00) clear through the central aisle.
# ---------------------------------------------------------------------------
_place(
    high_collaboration_table[0],
    [7.20, 1.10, 0.525],
    90,
    [7.20, 2.10, 0.525],
)

# Three chairs along the window side and one chair at each end.
_place(task_chair_C[0], [6.40, 0.34, 0.525], 90, [6.40, 1.10, 0.525])
_place(task_chair_D[0], [7.20, 0.34, 0.525], 90, [7.20, 1.10, 0.525])
_place(task_chair_E[0], [8.00, 0.34, 0.525], 90, [8.00, 1.10, 0.525])
_place(task_chair_F[0], [5.85, 1.10, 0.525], 0, [7.20, 1.10, 0.525])
_place(task_chair_G[0], [8.55, 1.10, 0.525], 180, [7.20, 1.10, 0.525])

solver.distance_constraint(task_chair_C[0], high_collaboration_table[0], 0.75, 1.30, weight=10)
solver.distance_constraint(task_chair_D[0], high_collaboration_table[0], 0.70, 1.10, weight=10)
solver.distance_constraint(task_chair_E[0], high_collaboration_table[0], 0.75, 1.30, weight=10)
solver.distance_constraint(task_chair_F[0], high_collaboration_table[0], 1.20, 1.55, weight=10)
solver.distance_constraint(task_chair_G[0], high_collaboration_table[0], 1.20, 1.55, weight=10)

solver.point_towards(task_chair_C[0], high_collaboration_table[0])
solver.point_towards(task_chair_D[0], high_collaboration_table[0])
solver.point_towards(task_chair_E[0], high_collaboration_table[0])
solver.point_towards(task_chair_F[0], high_collaboration_table[0])
solver.point_towards(task_chair_G[0], high_collaboration_table[0])


# ---------------------------------------------------------------------------
# Informal perching area in the lower-right corner.
# The stools face their respective small tables.
# ---------------------------------------------------------------------------
_place(small_side_table_A[0], [9.20, 1.10, 0.24], 0, [10.20, 1.10, 0.24])
_place(high_stool_A[0], [9.20, 0.38, 0.38], 90, [9.20, 1.10, 0.38])
_place(small_side_table_B[0], [10.00, 1.10, 0.24], 180, [9.00, 1.10, 0.24])
_place(high_stool_B[0], [10.00, 0.38, 0.38], 90, [10.00, 1.10, 0.38])

solver.distance_constraint(high_stool_A[0], small_side_table_A[0], 0.65, 0.85, weight=10)
solver.point_towards(high_stool_A[0], small_side_table_A[0])
solver.distance_constraint(high_stool_B[0], small_side_table_B[0], 0.65, 0.85, weight=10)
solver.point_towards(high_stool_B[0], small_side_table_B[0])


# ---------------------------------------------------------------------------
# Storage furniture. The three credenzas use solid walls rather than the
# windowed south wall.
# ---------------------------------------------------------------------------
_place(
    low_storage_credenza_A[0],
    [0.225, 1.90, 0.375],
    0,
    [1.225, 1.90, 0.375],
)
solver.against_wall(low_storage_credenza_A[0], walls[2])

_place(
    low_storage_credenza_B[0],
    [1.225, 4.50, 0.375],
    0,
    [2.225, 4.50, 0.375],
)
solver.against_wall(low_storage_credenza_B[0], walls[0])

_place(
    low_storage_credenza_C[0],
    [11.775, 1.00, 0.375],
    180,
    [10.775, 1.00, 0.375],
)
solver.against_wall(low_storage_credenza_C[0], walls[4])


# Four bookshelves form an evenly spaced storage run against the north wall.
_place(tall_bookshelf_A[0], [1.50, 5.81, 1.00], -90, [1.50, 4.81, 1.00])
_place(tall_bookshelf_B[0], [2.60, 5.81, 1.00], -90, [2.60, 4.81, 1.00])
_place(tall_bookshelf_C[0], [3.70, 5.81, 1.00], -90, [3.70, 4.81, 1.00])
_place(tall_bookshelf_D[0], [4.80, 5.81, 1.00], -90, [4.80, 4.81, 1.00])

solver.against_wall(tall_bookshelf_A[0], walls[9])
solver.against_wall(tall_bookshelf_B[0], walls[9])
solver.against_wall(tall_bookshelf_C[0], walls[9])
solver.against_wall(tall_bookshelf_D[0], walls[9])

# The side return occupies the remaining north-wall corner.
_place(
    side_return_unit[0],
    [5.55, 5.70, 0.325],
    -90,
    [5.55, 4.70, 0.325],
)
solver.against_wall(side_return_unit[0], walls[9])


# ---------------------------------------------------------------------------
# Small desktop and storage-top objects.
# Their z coordinates match the supporting surface heights.
# ---------------------------------------------------------------------------
_place(ring_binder_A[0], [1.72, 1.00, 0.785], 90, [1.72, 2.00, 0.785])
_place(ring_binder_B[0], [2.20, 1.00, 0.785], 90, [2.20, 2.00, 0.785])
solver.on_top_of(ring_binder_A[0], work_bench_desk_A[0])
solver.on_top_of(ring_binder_B[0], work_bench_desk_A[0])
solver.distance_constraint(ring_binder_A[0], work_bench_desk_A[0], 0.35, 0.65, weight=10)
solver.distance_constraint(ring_binder_B[0], work_bench_desk_A[0], 0.35, 0.65, weight=10)

_place(ring_binder_C[0], [3.68, 3.20, 0.785], 0, [4.68, 3.20, 0.785])
_place(desk_organizer[0], [4.32, 3.20, 0.90], 0, [5.32, 3.20, 0.90])
solver.on_top_of(ring_binder_C[0], work_bench_desk_B[0])
solver.on_top_of(desk_organizer[0], work_bench_desk_B[0])
solver.distance_constraint(ring_binder_C[0], work_bench_desk_B[0], 0.35, 0.65, weight=10)
solver.distance_constraint(desk_organizer[0], work_bench_desk_B[0], 0.35, 0.65, weight=10)

_place(ring_binder_D[0], [11.72, 1.00, 0.785], 180, [10.72, 1.00, 0.785])
solver.on_top_of(ring_binder_D[0], low_storage_credenza_C[0])
solver.distance_constraint(ring_binder_D[0], low_storage_credenza_C[0], 0.35, 0.55, weight=10)

# Required semantic relationship: the stack of files sits on the side return.
_place(stack_of_files[0], [5.55, 5.70, 0.775], -90, [5.55, 4.70, 0.775])
solver.on_top_of(stack_of_files[0], side_return_unit[0])
solver.distance_constraint(stack_of_files[0], side_return_unit[0], 0.40, 0.50, weight=10)
solver.align_with(stack_of_files[0], side_return_unit[0])


# ---------------------------------------------------------------------------
# Planters fill otherwise unused corners while avoiding desks, circulation,
# the collaboration seating, and the doorway approach.
# ---------------------------------------------------------------------------
_place(floor_planter_large_A[0], [0.40, 0.45, 0.55], 45, [1.40, 1.45, 0.55])
_place(floor_planter_large_B[0], [11.20, 0.35, 0.55], 135, [10.20, 1.35, 0.55])
_place(floor_planter_large_C[0], [1.40, 3.32, 0.55], 0, [2.40, 3.32, 0.55])
_place(floor_planter_large_D[0], [10.80, 1.52, 0.55], 180, [9.80, 1.52, 0.55])


# ---------------------------------------------------------------------------
# Whiteboards on three solid vertical walls. They are mounted above nearby
# low storage where applicable and do not cover any of the south windows.
# ---------------------------------------------------------------------------
_place(whiteboard_panel_A[0], [0.02, 0.90, 1.55], 0, [1.02, 0.90, 1.55])
solver.against_wall(whiteboard_panel_A[0], walls[2])

_place(whiteboard_panel_B[0], [1.02, 4.05, 1.55], 0, [2.02, 4.05, 1.55])
solver.against_wall(whiteboard_panel_B[0], walls[0])

_place(whiteboard_panel_C[0], [11.98, 1.00, 1.55], 180, [10.98, 1.00, 1.55])
solver.against_wall(whiteboard_panel_C[0], walls[4])


# ---------------------------------------------------------------------------
# Large acoustic artworks are mounted high on the north wall, above the
# bookshelf run. Their elevated placement avoids physical overlap with it.
# ---------------------------------------------------------------------------
_place(acoustic_wall_panel_A[0], [1.50, 5.975, 2.65], -90, [1.50, 4.975, 2.65])
_place(acoustic_wall_panel_B[0], [2.50, 5.975, 2.65], -90, [2.50, 4.975, 2.65])
_place(acoustic_wall_panel_C[0], [3.50, 5.975, 2.65], -90, [3.50, 4.975, 2.65])

solver.against_wall(acoustic_wall_panel_A[0], walls[9])
solver.against_wall(acoustic_wall_panel_B[0], walls[9])
solver.against_wall(acoustic_wall_panel_C[0], walls[9])


# Two smaller landscape pictures complete the high north-wall composition.
_place(picture_frame_A[0], [4.35, 5.975, 2.35], -90, [4.35, 4.975, 2.35])
_place(picture_frame_B[0], [5.15, 5.975, 2.35], -90, [5.15, 4.975, 2.35])
solver.against_wall(picture_frame_A[0], walls[9])
solver.against_wall(picture_frame_B[0], walls[9])


# ---------------------------------------------------------------------------
# The remaining framed pieces form a gallery along the solid wall at y=2.
# They face south into the room and stay clear of the windows and door.
# ---------------------------------------------------------------------------
_place(wall_art_print_A[0], [8.50, 1.98, 1.50], -90, [8.50, 0.98, 1.50])
_place(wall_art_print_B[0], [9.40, 1.98, 1.50], -90, [9.40, 0.98, 1.50])
_place(wall_art_print_C[0], [10.30, 1.98, 1.50], -90, [10.30, 0.98, 1.50])
_place(picture_frame_C[0], [11.25, 1.975, 1.45], -90, [11.25, 0.975, 1.45])

solver.against_wall(wall_art_print_A[0], walls[5])
solver.against_wall(wall_art_print_B[0], walls[5])
solver.against_wall(wall_art_print_C[0], walls[5])
solver.against_wall(picture_frame_C[0], walls[5])

solver.constraints = []
task_chair_E[0].position = [8.0, 0.3400000035762787, 0.5249999761581421]
task_chair_E[0].rotation = [0, 0, 1.586504290712113]
task_chair_E[0].optimize = 2
wall_art_print_A[0].position = [8.5, 1.9886554479599, 0.44999998807907104]
wall_art_print_A[0].rotation = [0, 0, -1.568255409566411]
wall_art_print_A[0].optimize = 2
whiteboard_panel_A[0].position = [0.02190561220049858, 0.8999999761581421, 0.44999998807907104]
whiteboard_panel_A[0].rotation = [0, 0, 0.0025409049851092386]
whiteboard_panel_A[0].optimize = 2
floor_planter_large_B[0].position = [11.199999809265137, 0.3888914883136749, 0.550000011920929]
floor_planter_large_B[0].rotation = [0, 0, 2.3656192553579443]
floor_planter_large_B[0].optimize = 2
task_chair_C[0].position = [6.400000095367432, 0.3400000035762787, 0.5249999761581421]
task_chair_C[0].rotation = [0, 0, 1.586504290712113]
task_chair_C[0].optimize = 2
acoustic_wall_panel_C[0].position = [3.5, 5.9838409423828125, 0.6000000238418579]
acoustic_wall_panel_C[0].rotation = [0, 0, -1.5682554107885098]
acoustic_wall_panel_C[0].optimize = 2
floor_planter_large_C[0].position = [1.399999976158142, 3.319999933242798, 0.550000011920929]
floor_planter_large_C[0].rotation = [0, 0, 0.00942477746072377]
floor_planter_large_C[0].optimize = 2
ring_binder_A[0].position = [1.7100000381469727, 1.0, 0.7850000262260437]
ring_binder_A[0].rotation = [0, 0, 1.586504290712113]
ring_binder_A[0].optimize = 2
side_return_unit[0].position = [5.550000190734863, 5.7099995613098145, 0.32499998807907104]
side_return_unit[0].rotation = [0, 0, -1.5589233064783767]
side_return_unit[0].optimize = 2
high_stool_A[0].position = [9.199999809265137, 0.3799999952316284, 0.3799999952316284]
high_stool_A[0].rotation = [0, 0, 1.586504290712113]
high_stool_A[0].optimize = 2
low_storage_credenza_A[0].position = [0.23629166185855865, 1.899999976158142, 0.375]
low_storage_credenza_A[0].rotation = [0, 0, 0.0025408284588584276]
low_storage_credenza_A[0].optimize = 2
floor_planter_large_A[0].position = [0.4000000059604645, 0.44999998807907104, 0.550000011920929]
floor_planter_large_A[0].rotation = [0, 0, 0.7948229285630478]
floor_planter_large_A[0].optimize = 2
desk_organizer[0].position = [4.330000400543213, 3.200000047683716, 0.8999999761581421]
desk_organizer[0].rotation = [0, 0, 0.0157079639172164]
desk_organizer[0].optimize = 2
work_bench_desk_A[0].position = [2.0, 1.0, 0.375]
work_bench_desk_A[0].rotation = [0, 0, 1.5990706612064889]
work_bench_desk_A[0].optimize = 2
ring_binder_C[0].position = [3.6700000762939453, 3.200000047683716, 0.7850000262260437]
ring_binder_C[0].rotation = [0, 0, 0.0157079639172164]
ring_binder_C[0].optimize = 2
floor_planter_large_D[0].position = [10.800000190734863, 1.5199999809265137, 0.550000011920929]
floor_planter_large_D[0].rotation = [0, 0, -3.1321678761290697]
floor_planter_large_D[0].optimize = 2
low_storage_credenza_B[0].position = [1.2262918949127197, 4.5, 0.375]
low_storage_credenza_B[0].rotation = [0, 0, 0.0025408985523042373]
low_storage_credenza_B[0].optimize = 2
small_side_table_B[0].position = [10.0, 1.100000023841858, 0.23999999463558197]
small_side_table_B[0].rotation = [0, 0, -3.125884689672577]
small_side_table_B[0].optimize = 2
tall_bookshelf_C[0].position = [3.700000047683716, 5.808856964111328, 1.0]
tall_bookshelf_C[0].rotation = [0, 0, -1.5682554107885098]
tall_bookshelf_C[0].optimize = 2
small_side_table_A[0].position = [9.199999809265137, 1.100000023841858, 0.23999999463558197]
small_side_table_A[0].rotation = [0, 0, 0.0157079639172164]
small_side_table_A[0].optimize = 2
picture_frame_C[0].position = [11.25, 1.9838411808013916, 0.22499999403953552]
picture_frame_C[0].rotation = [0, 0, -1.5682554083443117]
picture_frame_C[0].optimize = 2
high_stool_B[0].position = [10.0, 0.3799999952316284, 0.3799999952316284]
high_stool_B[0].rotation = [0, 0, 1.586504290712113]
high_stool_B[0].optimize = 2
task_chair_A[0].position = [2.0, 1.850000023841858, 0.5249999761581421]
task_chair_A[0].rotation = [0, 0, -1.5550883628776802]
task_chair_A[0].optimize = 2
task_chair_G[0].position = [8.550000190734863, 1.100000023841858, 0.5249999761581421]
task_chair_G[0].rotation = [0, 0, -3.125884689672577]
task_chair_G[0].optimize = 2
tall_bookshelf_B[0].position = [2.5999999046325684, 5.808856964111328, 1.0]
tall_bookshelf_B[0].rotation = [0, 0, -1.5682554107885098]
tall_bookshelf_B[0].optimize = 2
ring_binder_D[0].position = [11.710000038146973, 1.0, 0.7850000262260437]
ring_binder_D[0].rotation = [0, 0, -3.125884689672577]
ring_binder_D[0].optimize = 2
whiteboard_panel_B[0].position = [1.0219056606292725, 4.050000190734863, 0.44999998807907104]
whiteboard_panel_B[0].rotation = [0, 0, 0.0025409049851092386]
whiteboard_panel_B[0].optimize = 2
picture_frame_B[0].position = [5.150000095367432, 5.9838409423828125, 0.22499999403953552]
picture_frame_B[0].rotation = [0, 0, -1.5682554083443117]
picture_frame_B[0].optimize = 2
whiteboard_panel_C[0].position = [11.978094100952148, 1.0, 0.44999998807907104]
whiteboard_panel_C[0].rotation = [0, 0, -3.1390517476825117]
whiteboard_panel_C[0].optimize = 2
low_storage_credenza_C[0].position = [11.76807689666748, 1.0, 0.375]
low_storage_credenza_C[0].rotation = [0, 0, -3.1328304459931435]
low_storage_credenza_C[0].optimize = 2
high_collaboration_table[0].position = [7.199999809265137, 1.100000023841858, 0.5249999761581421]
high_collaboration_table[0].rotation = [0, 0, 1.6116370324823435]
high_collaboration_table[0].optimize = 2
acoustic_wall_panel_A[0].position = [1.5, 5.9838409423828125, 0.6000000238418579]
acoustic_wall_panel_A[0].rotation = [0, 0, -1.5682554107885098]
acoustic_wall_panel_A[0].optimize = 2
stack_of_files[0].position = [5.550000190734863, 5.699999809265137, 0.7749999761581421]
stack_of_files[0].rotation = [0, 0, -1.5416676055337]
stack_of_files[0].optimize = 2
wall_art_print_B[0].position = [9.399999618530273, 1.9886554479599, 0.44999998807907104]
wall_art_print_B[0].rotation = [0, 0, -1.568255409566411]
wall_art_print_B[0].optimize = 2
tall_bookshelf_A[0].position = [1.5, 5.808856964111328, 1.0]
tall_bookshelf_A[0].rotation = [0, 0, -1.5682554107885098]
tall_bookshelf_A[0].optimize = 2
wall_art_print_C[0].position = [10.300000190734863, 1.9886554479599, 0.44999998807907104]
wall_art_print_C[0].rotation = [0, 0, -1.568255409566411]
wall_art_print_C[0].optimize = 2
task_chair_D[0].position = [7.199999809265137, 0.3400000035762787, 0.5249999761581421]
task_chair_D[0].rotation = [0, 0, 1.586504290712113]
task_chair_D[0].optimize = 2
tall_bookshelf_D[0].position = [4.800000190734863, 5.808856964111328, 1.0]
tall_bookshelf_D[0].rotation = [0, 0, -1.5682554107885098]
tall_bookshelf_D[0].optimize = 2
acoustic_wall_panel_B[0].position = [2.5, 5.9838409423828125, 0.6000000238418579]
acoustic_wall_panel_B[0].rotation = [0, 0, -1.5682554107885098]
acoustic_wall_panel_B[0].optimize = 2
picture_frame_A[0].position = [4.349999904632568, 5.9838409423828125, 0.22499999403953552]
picture_frame_A[0].rotation = [0, 0, -1.5682554083443117]
picture_frame_A[0].optimize = 2
task_chair_F[0].position = [5.849999904632568, 1.100000023841858, 0.5249999761581421]
task_chair_F[0].rotation = [0, 0, 0.0157079639172164]
task_chair_F[0].optimize = 2
task_chair_B[0].position = [4.0, 2.3499999046325684, 0.5249999761581421]
task_chair_B[0].rotation = [0, 0, 1.586504290712113]
task_chair_B[0].optimize = 2
work_bench_desk_B[0].position = [4.0, 3.200000047683716, 0.375]
work_bench_desk_B[0].rotation = [0, 0, 1.5990706612064889]
work_bench_desk_B[0].optimize = 2
ring_binder_B[0].position = [2.2100000381469727, 1.0, 0.7850000262260437]
ring_binder_B[0].rotation = [0, 0, 1.586504290712113]
ring_binder_B[0].optimize = 2

