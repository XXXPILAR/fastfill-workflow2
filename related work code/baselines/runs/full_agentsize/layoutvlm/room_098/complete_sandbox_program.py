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
    Wall(corner1=[2.00, 6.00, 0.00], corner2=[0.00, 6.00, 0.00]),
    Wall(corner1=[0.00, 6.00, 0.00], corner2=[0.00, 3.00, 0.00]),
    Wall(corner1=[0.00, 3.00, 0.00], corner2=[2.00, 3.00, 0.00]),
    Wall(corner1=[2.00, 3.00, 0.00], corner2=[2.00, 0.00, 0.00]),
    Wall(corner1=[2.00, 0.00, 0.00], corner2=[15.00, 0.00, 0.00]),
    Wall(corner1=[15.00, 0.00, 0.00], corner2=[15.00, 1.00, 0.00]),
    Wall(corner1=[15.00, 1.00, 0.00], corner2=[17.00, 1.00, 0.00]),
    Wall(corner1=[17.00, 1.00, 0.00], corner2=[17.00, 8.00, 0.00]),
    Wall(corner1=[17.00, 8.00, 0.00], corner2=[15.00, 8.00, 0.00]),
    Wall(corner1=[15.00, 8.00, 0.00], corner2=[15.00, 9.00, 0.00]),
    Wall(corner1=[15.00, 9.00, 0.00], corner2=[13.00, 9.00, 0.00]),
    Wall(corner1=[13.00, 9.00, 0.00], corner2=[13.00, 11.00, 0.00]),
    Wall(corner1=[13.00, 11.00, 0.00], corner2=[2.00, 11.00, 0.00]),
    Wall(corner1=[2.00, 11.00, 0.00], corner2=[2.00, 6.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
low_storage_cabinet_A = Assets(description="White six draw wood cabinets with metal legs.", size=[0.45, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
task_chair_A = Assets(description="An office chair with a tall back and cushioning on the seat and backrest. it has wheels on the bottom.", size=[0.68, 0.68, 1.15], placements=[AssetInstance() for _ in range(1)])
magazine_A = Assets(description="a notebook with stickers and a Pokémon drawing on it.", size=[0.16, 0.22, 0.02], placements=[AssetInstance() for _ in range(1)])
pen_cup_A = Assets(description="A cylindrical gray cup with two pens and a pencil sticking out.", size=[0.10, 0.10, 0.22], placements=[AssetInstance() for _ in range(1)])
high_stool_A = Assets(description="high stool", size=[0.45, 0.45, 1.00], placements=[AssetInstance() for _ in range(1)])
magazine_B = Assets(description="A light brown hardback book with atom depicted in gold on the cover.", size=[0.18, 0.24, 0.03], placements=[AssetInstance() for _ in range(1)])
work_bench_desk_A = Assets(description="A long table with two sides.", size=[1.40, 2.40, 0.74], placements=[AssetInstance() for _ in range(1)])
side_occasion_table_A = Assets(description="side occasion table", size=[0.55, 0.55, 0.55], placements=[AssetInstance() for _ in range(1)])
file_tray_A = Assets(description="yellow file folder with a smiley face on it.", size=[0.25, 0.34, 0.07], placements=[AssetInstance() for _ in range(1)])
task_chair_B = Assets(description="An office chair with a tall back and cushioning on the seat and backrest. it has wheels on the bottom.", size=[0.68, 0.68, 1.15], placements=[AssetInstance() for _ in range(1)])
office_printer_A = Assets(description="A square and round stand mixer sitting side by side.", size=[0.55, 0.55, 0.45], placements=[AssetInstance() for _ in range(1)])
coat_stand_A = Assets(description="The coatrack is wooden with a round bottom.", size=[0.45, 0.45, 1.80], placements=[AssetInstance() for _ in range(1)])
pen_cup_B = Assets(description="A cylindrical gray cup with two pens and a pencil sticking out.", size=[0.10, 0.10, 0.22], placements=[AssetInstance() for _ in range(1)])
side_occasion_table_B = Assets(description="side occasion table", size=[0.55, 0.55, 0.55], placements=[AssetInstance() for _ in range(1)])
lockers_bank = Assets(description="green metal lockers.", size=[0.50, 1.80, 1.90], placements=[AssetInstance() for _ in range(1)])
side_occasion_table_C = Assets(description="side occasion table", size=[0.55, 0.55, 0.55], placements=[AssetInstance() for _ in range(1)])
printer_side_table_A = Assets(description="printer side table", size=[0.60, 0.75, 0.70], placements=[AssetInstance() for _ in range(1)])
task_chair_C = Assets(description="An office chair with a tall back and cushioning on the seat and backrest. it has wheels on the bottom.", size=[0.68, 0.68, 1.15], placements=[AssetInstance() for _ in range(1)])
high_stool_B = Assets(description="high stool", size=[0.45, 0.45, 1.00], placements=[AssetInstance() for _ in range(1)])
high_stool_C = Assets(description="high stool", size=[0.45, 0.45, 1.00], placements=[AssetInstance() for _ in range(1)])
mobile_pedestal_A = Assets(description="A wooden nightstand with both its drawers open.", size=[0.55, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])
mobile_pedestal_B = Assets(description="A wooden nightstand with both its drawers open.", size=[0.55, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])
coat_stand_B = Assets(description="The coatrack is wooden with a round bottom.", size=[0.45, 0.45, 1.80], placements=[AssetInstance() for _ in range(1)])
desk_organizer_A = Assets(description="yellow file folder with a smiley face on it.", size=[0.24, 0.32, 0.18], placements=[AssetInstance() for _ in range(1)])
counter_stool_A = Assets(description="A stool with a metal leg and foot rest with a round black cushion.", size=[0.45, 0.45, 0.90], placements=[AssetInstance() for _ in range(1)])
magazine_C = Assets(description="A light brown hardback book with atom depicted in gold on the cover.", size=[0.18, 0.24, 0.03], placements=[AssetInstance() for _ in range(1)])
floor_lamp_A = Assets(description="A floor lamp with a black base and white lampshade.", size=[0.45, 0.45, 1.65], placements=[AssetInstance() for _ in range(1)])
notepad_stack_A = Assets(description="A box of kleenix wipes.", size=[0.12, 0.22, 0.08], placements=[AssetInstance() for _ in range(1)])
high_stool_D = Assets(description="high stool", size=[0.45, 0.45, 1.00], placements=[AssetInstance() for _ in range(1)])
file_tray_B = Assets(description="yellow file folder with a smiley face on it.", size=[0.25, 0.34, 0.07], placements=[AssetInstance() for _ in range(1)])
wayfinding_sign_A = Assets(description="a Korean street sign with Korean writing, suitable for a restaurant setting.", size=[0.05, 0.80, 0.25], placements=[AssetInstance() for _ in range(1)])
office_monitor_A = Assets(description="A computer monitor with a black base.", size=[0.20, 0.55, 0.45], placements=[AssetInstance() for _ in range(1)])
sofa_modular = Assets(description="A light grey sofa with seating for four.", size=[0.90, 3.00, 0.85], placements=[AssetInstance() for _ in range(1)])
desk_side_cabinet_A = Assets(description="desk side cabinet", size=[0.45, 0.80, 0.72], placements=[AssetInstance() for _ in range(1)])
high_stool_E = Assets(description="high stool", size=[0.45, 0.45, 1.00], placements=[AssetInstance() for _ in range(1)])
low_storage_cabinet_B = Assets(description="White six draw wood cabinets with metal legs.", size=[0.45, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
desk_organizer_B = Assets(description="yellow file folder with a smiley face on it.", size=[0.24, 0.32, 0.18], placements=[AssetInstance() for _ in range(1)])
standing_meeting_table_A = Assets(description="A round all brown kitchen table.", size=[0.90, 0.90, 1.05], placements=[AssetInstance() for _ in range(1)])
high_stool_F = Assets(description="high stool", size=[0.45, 0.45, 1.00], placements=[AssetInstance() for _ in range(1)])
keyboard_and_mouse_set = Assets(description="Gray monitor with a red screen computer and with a keyboard and mouse.", size=[0.25, 0.65, 0.05], placements=[AssetInstance() for _ in range(1)])
printer_side_table_B = Assets(description="printer side table", size=[0.60, 0.75, 0.70], placements=[AssetInstance() for _ in range(1)])
framed_photo_A = Assets(description="A blue painting in a black frame.", size=[0.08, 0.45, 0.35], placements=[AssetInstance() for _ in range(1)])
office_monitor_B = Assets(description="A computer monitor with a black base.", size=[0.20, 0.55, 0.45], placements=[AssetInstance() for _ in range(1)])
desk_side_cabinet_B = Assets(description="desk side cabinet", size=[0.45, 0.80, 0.72], placements=[AssetInstance() for _ in range(1)])
small_potted_plant_A = Assets(description="A bunch of big leaves inside of a white pot.", size=[0.45, 0.45, 0.65], placements=[AssetInstance() for _ in range(1)])
high_stool_G = Assets(description="high stool", size=[0.45, 0.45, 1.00], placements=[AssetInstance() for _ in range(1)])
team_table_A = Assets(description="A dark colored table with thin legs.", size=[1.10, 2.40, 0.75], placements=[AssetInstance() for _ in range(1)])
work_bench_desk_B = Assets(description="A long table with two sides.", size=[1.40, 2.40, 0.74], placements=[AssetInstance() for _ in range(1)])
file_tray_C = Assets(description="yellow file folder with a smiley face on it.", size=[0.25, 0.34, 0.07], placements=[AssetInstance() for _ in range(1)])
task_chair_D = Assets(description="An office chair with a tall back and cushioning on the seat and backrest. it has wheels on the bottom.", size=[0.68, 0.68, 1.15], placements=[AssetInstance() for _ in range(1)])
desk_side_cabinet_C = Assets(description="desk side cabinet", size=[0.45, 0.80, 0.72], placements=[AssetInstance() for _ in range(1)])
planter_box_A = Assets(description="A wooden planter with some strawberries.", size=[0.45, 1.20, 0.50], placements=[AssetInstance() for _ in range(1)])
small_potted_plant_B = Assets(description="A plant sitting in a round flower pot.", size=[0.35, 0.35, 0.50], placements=[AssetInstance() for _ in range(1)])
small_potted_plant_C = Assets(description="A plant sitting in a round flower pot.", size=[0.35, 0.35, 0.50], placements=[AssetInstance() for _ in range(1)])
counter_stool_B = Assets(description="A stool with a metal leg and foot rest with a round black cushion.", size=[0.45, 0.45, 0.90], placements=[AssetInstance() for _ in range(1)])
magazine_D = Assets(description="a notebook with stickers and a Pokémon drawing on it.", size=[0.16, 0.22, 0.02], placements=[AssetInstance() for _ in range(1)])
coat_stand_C = Assets(description="The coatrack is wooden with a round bottom.", size=[0.45, 0.45, 1.80], placements=[AssetInstance() for _ in range(1)])
low_storage_cabinet_C = Assets(description="White six draw wood cabinets with metal legs.", size=[0.45, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
framed_photo_B = Assets(description="A blue painting in a black frame.", size=[0.08, 0.45, 0.35], placements=[AssetInstance() for _ in range(1)])
office_printer_B = Assets(description="A square and round stand mixer sitting side by side.", size=[0.55, 0.55, 0.45], placements=[AssetInstance() for _ in range(1)])
work_bench_desk_C = Assets(description="A long table with two sides.", size=[1.40, 2.40, 0.74], placements=[AssetInstance() for _ in range(1)])
standing_meeting_table_B = Assets(description="A round all brown kitchen table.", size=[0.90, 0.90, 1.05], placements=[AssetInstance() for _ in range(1)])
team_table_B = Assets(description="A dark colored table with thin legs.", size=[1.10, 2.40, 0.75], placements=[AssetInstance() for _ in range(1)])
magazine_E = Assets(description="a notebook with stickers and a Pokémon drawing on it.", size=[0.16, 0.22, 0.02], placements=[AssetInstance() for _ in range(1)])
task_chair_E = Assets(description="An office chair with a tall back and cushioning on the seat and backrest. it has wheels on the bottom.", size=[0.68, 0.68, 1.15], placements=[AssetInstance() for _ in range(1)])
wayfinding_sign_B = Assets(description="a Korean street sign with Korean writing, suitable for a restaurant setting.", size=[0.05, 0.80, 0.25], placements=[AssetInstance() for _ in range(1)])
desk_organizer_C = Assets(description="yellow file folder with a smiley face on it.", size=[0.24, 0.32, 0.18], placements=[AssetInstance() for _ in range(1)])
high_stool_H = Assets(description="high stool", size=[0.45, 0.45, 1.00], placements=[AssetInstance() for _ in range(1)])
high_stool_I = Assets(description="high stool", size=[0.45, 0.45, 1.00], placements=[AssetInstance() for _ in range(1)])
wayfinding_sign_C = Assets(description="a Korean street sign with Korean writing, suitable for a restaurant setting.", size=[0.05, 0.80, 0.25], placements=[AssetInstance() for _ in range(1)])
low_storage_cabinet_D = Assets(description="White six draw wood cabinets with metal legs.", size=[0.45, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
framed_photo_C = Assets(description="A portrait sketch of a president.", size=[0.08, 0.40, 0.50], placements=[AssetInstance() for _ in range(1)])
desk_side_cabinet_D = Assets(description="desk side cabinet", size=[0.45, 0.80, 0.72], placements=[AssetInstance() for _ in range(1)])
planter_box_B = Assets(description="A wooden planter with some strawberries.", size=[0.45, 1.20, 0.50], placements=[AssetInstance() for _ in range(1)])
wayfinding_sign_D = Assets(description="a Korean street sign with Korean writing, suitable for a restaurant setting.", size=[0.05, 0.80, 0.25], placements=[AssetInstance() for _ in range(1)])
file_tray_D = Assets(description="A brown leather card holder with a logo on it.", size=[0.12, 0.25, 0.05], placements=[AssetInstance() for _ in range(1)])
file_tray_E = Assets(description="A brown leather card holder with a logo on it.", size=[0.12, 0.25, 0.05], placements=[AssetInstance() for _ in range(1)])
notepad_stack_B = Assets(description="A box of kleenix wipes.", size=[0.12, 0.22, 0.08], placements=[AssetInstance() for _ in range(1)])
framed_photo_D = Assets(description="A blue painting in a black frame.", size=[0.08, 0.45, 0.35], placements=[AssetInstance() for _ in range(1)])
mobile_pedestal_C = Assets(description="A wooden nightstand with both its drawers open.", size=[0.55, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])
task_chair_F = Assets(description="An office chair with a tall back and cushioning on the seat and backrest. it has wheels on the bottom.", size=[0.68, 0.68, 1.15], placements=[AssetInstance() for _ in range(1)])
standing_meeting_table_C = Assets(description="A round all brown kitchen table.", size=[0.90, 0.90, 1.05], placements=[AssetInstance() for _ in range(1)])
notepad_stack_C = Assets(description="A box of kleenix wipes.", size=[0.12, 0.22, 0.08], placements=[AssetInstance() for _ in range(1)])
floor_lamp_B = Assets(description="A floor lamp with a black base and white lampshade.", size=[0.45, 0.45, 1.65], placements=[AssetInstance() for _ in range(1)])

low_storage_cabinet_A[0].instance_id = 'low_storage_cabinet_A_0'
task_chair_A[0].instance_id = 'task_chair_A_0'
magazine_A[0].instance_id = 'magazine_A_0'
pen_cup_A[0].instance_id = 'pen_cup_A_0'
high_stool_A[0].instance_id = 'high_stool_A_0'
magazine_B[0].instance_id = 'magazine_B_0'
work_bench_desk_A[0].instance_id = 'work_bench_desk_A_0'
side_occasion_table_A[0].instance_id = 'side_occasion_table_A_0'
file_tray_A[0].instance_id = 'file_tray_A_0'
task_chair_B[0].instance_id = 'task_chair_B_0'
office_printer_A[0].instance_id = 'office_printer_A_0'
coat_stand_A[0].instance_id = 'coat_stand_A_0'
pen_cup_B[0].instance_id = 'pen_cup_B_0'
side_occasion_table_B[0].instance_id = 'side_occasion_table_B_0'
lockers_bank[0].instance_id = 'lockers_bank_0'
side_occasion_table_C[0].instance_id = 'side_occasion_table_C_0'
printer_side_table_A[0].instance_id = 'printer_side_table_A_0'
task_chair_C[0].instance_id = 'task_chair_C_0'
high_stool_B[0].instance_id = 'high_stool_B_0'
high_stool_C[0].instance_id = 'high_stool_C_0'
mobile_pedestal_A[0].instance_id = 'mobile_pedestal_A_0'
mobile_pedestal_B[0].instance_id = 'mobile_pedestal_B_0'
coat_stand_B[0].instance_id = 'coat_stand_B_0'
desk_organizer_A[0].instance_id = 'desk_organizer_A_0'
counter_stool_A[0].instance_id = 'counter_stool_A_0'
magazine_C[0].instance_id = 'magazine_C_0'
floor_lamp_A[0].instance_id = 'floor_lamp_A_0'
notepad_stack_A[0].instance_id = 'notepad_stack_A_0'
high_stool_D[0].instance_id = 'high_stool_D_0'
file_tray_B[0].instance_id = 'file_tray_B_0'
wayfinding_sign_A[0].instance_id = 'wayfinding_sign_A_0'
office_monitor_A[0].instance_id = 'office_monitor_A_0'
sofa_modular[0].instance_id = 'sofa_modular_0'
desk_side_cabinet_A[0].instance_id = 'desk_side_cabinet_A_0'
high_stool_E[0].instance_id = 'high_stool_E_0'
low_storage_cabinet_B[0].instance_id = 'low_storage_cabinet_B_0'
desk_organizer_B[0].instance_id = 'desk_organizer_B_0'
standing_meeting_table_A[0].instance_id = 'standing_meeting_table_A_0'
high_stool_F[0].instance_id = 'high_stool_F_0'
keyboard_and_mouse_set[0].instance_id = 'keyboard_and_mouse_set_0'
printer_side_table_B[0].instance_id = 'printer_side_table_B_0'
framed_photo_A[0].instance_id = 'framed_photo_A_0'
office_monitor_B[0].instance_id = 'office_monitor_B_0'
desk_side_cabinet_B[0].instance_id = 'desk_side_cabinet_B_0'
small_potted_plant_A[0].instance_id = 'small_potted_plant_A_0'
high_stool_G[0].instance_id = 'high_stool_G_0'
team_table_A[0].instance_id = 'team_table_A_0'
work_bench_desk_B[0].instance_id = 'work_bench_desk_B_0'
file_tray_C[0].instance_id = 'file_tray_C_0'
task_chair_D[0].instance_id = 'task_chair_D_0'
desk_side_cabinet_C[0].instance_id = 'desk_side_cabinet_C_0'
planter_box_A[0].instance_id = 'planter_box_A_0'
small_potted_plant_B[0].instance_id = 'small_potted_plant_B_0'
small_potted_plant_C[0].instance_id = 'small_potted_plant_C_0'
counter_stool_B[0].instance_id = 'counter_stool_B_0'
magazine_D[0].instance_id = 'magazine_D_0'
coat_stand_C[0].instance_id = 'coat_stand_C_0'
low_storage_cabinet_C[0].instance_id = 'low_storage_cabinet_C_0'
framed_photo_B[0].instance_id = 'framed_photo_B_0'
office_printer_B[0].instance_id = 'office_printer_B_0'
work_bench_desk_C[0].instance_id = 'work_bench_desk_C_0'
standing_meeting_table_B[0].instance_id = 'standing_meeting_table_B_0'
team_table_B[0].instance_id = 'team_table_B_0'
magazine_E[0].instance_id = 'magazine_E_0'
task_chair_E[0].instance_id = 'task_chair_E_0'
wayfinding_sign_B[0].instance_id = 'wayfinding_sign_B_0'
desk_organizer_C[0].instance_id = 'desk_organizer_C_0'
high_stool_H[0].instance_id = 'high_stool_H_0'
high_stool_I[0].instance_id = 'high_stool_I_0'
wayfinding_sign_C[0].instance_id = 'wayfinding_sign_C_0'
low_storage_cabinet_D[0].instance_id = 'low_storage_cabinet_D_0'
framed_photo_C[0].instance_id = 'framed_photo_C_0'
desk_side_cabinet_D[0].instance_id = 'desk_side_cabinet_D_0'
planter_box_B[0].instance_id = 'planter_box_B_0'
wayfinding_sign_D[0].instance_id = 'wayfinding_sign_D_0'
file_tray_D[0].instance_id = 'file_tray_D_0'
file_tray_E[0].instance_id = 'file_tray_E_0'
notepad_stack_B[0].instance_id = 'notepad_stack_B_0'
framed_photo_D[0].instance_id = 'framed_photo_D_0'
mobile_pedestal_C[0].instance_id = 'mobile_pedestal_C_0'
task_chair_F[0].instance_id = 'task_chair_F_0'
standing_meeting_table_C[0].instance_id = 'standing_meeting_table_C_0'
notepad_stack_C[0].instance_id = 'notepad_stack_C_0'
floor_lamp_B[0].instance_id = 'floor_lamp_B_0'
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
walls[10].instance_id = 'walls_10'
walls[11].instance_id = 'walls_11'
walls[12].instance_id = 'walls_12'
walls[13].instance_id = 'walls_13'

low_storage_cabinet_A[0].position = [9.39169668609769, 3.878045946674927, 0.375]
low_storage_cabinet_A[0].rotation = [0, 0, 0]
task_chair_A[0].position = [5.060260056535072, 8.532541605580198, 0.575]
task_chair_A[0].rotation = [0, 0, 0]
magazine_A[0].position = [2.192580752417688, 10.035935836136357, 0.01]
magazine_A[0].rotation = [0, 0, 0]
pen_cup_A[0].position = [8.530890567487827, 1.5484611293209998, 0.11]
pen_cup_A[0].rotation = [0, 0, 0]
high_stool_A[0].position = [8.608519123324962, 5.85339418930362, 0.5]
high_stool_A[0].rotation = [0, 0, 0]
magazine_B[0].position = [8.156572119514033, 0.1487110703556389, 0.015]
magazine_B[0].rotation = [0, 0, 0]
work_bench_desk_A[0].position = [8.523460715180946, 4.255742618594684, 0.37]
work_bench_desk_A[0].rotation = [0, 0, 0]
side_occasion_table_A[0].position = [16.952656284825377, 6.993599582902142, 0.275]
side_occasion_table_A[0].rotation = [0, 0, 0]
file_tray_A[0].position = [5.821014472169757, 8.136918115029129, 0.035]
file_tray_A[0].rotation = [0, 0, 0]
task_chair_B[0].position = [12.060832906455557, 10.403204069515683, 0.575]
task_chair_B[0].rotation = [0, 0, 0]
office_printer_A[0].position = [4.052135306579803, 4.86550204134479, 0.225]
office_printer_A[0].rotation = [0, 0, 0]
coat_stand_A[0].position = [6.084928991104851, 7.49752435333705, 0.9]
coat_stand_A[0].rotation = [0, 0, 0]
pen_cup_B[0].position = [2.742917158411661, 9.866352557059802, 0.11]
pen_cup_B[0].rotation = [0, 0, 0]
side_occasion_table_B[0].position = [4.475751041165772, 4.965837385663199, 0.275]
side_occasion_table_B[0].rotation = [0, 0, 0]
lockers_bank[0].position = [6.184650196522248, 6.75004596456961, 0.95]
lockers_bank[0].rotation = [0, 0, 0]
side_occasion_table_C[0].position = [15.907413473054335, 5.2195833867364545, 0.275]
side_occasion_table_C[0].rotation = [0, 0, 0]
printer_side_table_A[0].position = [7.668589681743031, 7.732083975109591, 0.35]
printer_side_table_A[0].rotation = [0, 0, 0]
task_chair_C[0].position = [8.791026922549293, 10.295429784672002, 0.575]
task_chair_C[0].rotation = [0, 0, 0]
high_stool_B[0].position = [13.90897849537072, 0.3788719772837914, 0.5]
high_stool_B[0].rotation = [0, 0, 0]
high_stool_C[0].position = [14.746532719927563, 5.025830881383255, 0.5]
high_stool_C[0].rotation = [0, 0, 0]
mobile_pedestal_A[0].position = [8.972263374339539, 4.954319639330282, 0.3]
mobile_pedestal_A[0].rotation = [0, 0, 0]
mobile_pedestal_B[0].position = [3.391405676547318, 6.46263442924552, 0.3]
mobile_pedestal_B[0].rotation = [0, 0, 0]
coat_stand_B[0].position = [9.269130445636025, 3.5699617157164427, 0.9]
coat_stand_B[0].rotation = [0, 0, 0]
desk_organizer_A[0].position = [12.017021663475944, 1.2677452535339495, 0.09]
desk_organizer_A[0].rotation = [0, 0, 0]
counter_stool_A[0].position = [9.80935752394147, 10.399866003228437, 0.45]
counter_stool_A[0].rotation = [0, 0, 0]
magazine_C[0].position = [9.206515570754425, 7.118922379904773, 0.015]
magazine_C[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [13.5103185029081, 6.872421395724417, 0.825]
floor_lamp_A[0].rotation = [0, 0, 0]
notepad_stack_A[0].position = [13.242167357941714, 8.731905449674143, 0.04]
notepad_stack_A[0].rotation = [0, 0, 0]
high_stool_D[0].position = [6.299525527961685, 1.6224409297776303, 0.5]
high_stool_D[0].rotation = [0, 0, 0]
file_tray_B[0].position = [9.10276629207807, 0.2988680296613794, 0.035]
file_tray_B[0].rotation = [0, 0, 0]
wayfinding_sign_A[0].position = [4.887473164425642, 6.494482462155478, 0.125]
wayfinding_sign_A[0].rotation = [0, 0, 0]
office_monitor_A[0].position = [4.469544546444729, 8.462724681543175, 0.225]
office_monitor_A[0].rotation = [0, 0, 0]
sofa_modular[0].position = [14.048879212163568, 3.2334634873164365, 0.425]
sofa_modular[0].rotation = [0, 0, 0]
desk_side_cabinet_A[0].position = [7.557856303258847, 0.9441271770078342, 0.36]
desk_side_cabinet_A[0].rotation = [0, 0, 0]
high_stool_E[0].position = [2.5602465035046116, 5.35367672373356, 0.5]
high_stool_E[0].rotation = [0, 0, 0]
low_storage_cabinet_B[0].position = [8.972359842335122, 7.458777482327908, 0.375]
low_storage_cabinet_B[0].rotation = [0, 0, 0]
desk_organizer_B[0].position = [6.729001489102119, 9.320795232298117, 0.09]
desk_organizer_B[0].rotation = [0, 0, 0]
standing_meeting_table_A[0].position = [4.998929067706196, 6.239989335664095, 0.525]
standing_meeting_table_A[0].rotation = [0, 0, 0]
high_stool_F[0].position = [0.6488421155209694, 4.8911689786125825, 0.5]
high_stool_F[0].rotation = [0, 0, 0]
keyboard_and_mouse_set[0].position = [6.014739653264417, 0.12014015112486987, 0.025]
keyboard_and_mouse_set[0].rotation = [0, 0, 0]
printer_side_table_B[0].position = [5.807883615853967, 7.796599601696041, 0.35]
printer_side_table_B[0].rotation = [0, 0, 0]
framed_photo_A[0].position = [7.597996291444255, 7.012210705004719, 0.175]
framed_photo_A[0].rotation = [0, 0, 0]
office_monitor_B[0].position = [2.0712262065825207, 2.7102295959901124, 0.225]
office_monitor_B[0].rotation = [0, 0, 0]
desk_side_cabinet_B[0].position = [5.6594117521072835, 9.821932274258266, 0.36]
desk_side_cabinet_B[0].rotation = [0, 0, 0]
small_potted_plant_A[0].position = [15.650598843358171, 3.482385865913238, 0.325]
small_potted_plant_A[0].rotation = [0, 0, 0]
high_stool_G[0].position = [6.8866512708829015, 10.331794382532797, 0.5]
high_stool_G[0].rotation = [0, 0, 0]
team_table_A[0].position = [3.823194191100861, 5.2204861924051755, 0.375]
team_table_A[0].rotation = [0, 0, 0]
work_bench_desk_B[0].position = [3.347292177307925, 4.325816091281641, 0.37]
work_bench_desk_B[0].rotation = [0, 0, 0]
file_tray_C[0].position = [2.3767552217460675, 3.474582787708777, 0.035]
file_tray_C[0].rotation = [0, 0, 0]
task_chair_D[0].position = [6.760735872920213, 9.787027997053567, 0.575]
task_chair_D[0].rotation = [0, 0, 0]
desk_side_cabinet_C[0].position = [14.201738697672479, 4.5142025897234745, 0.36]
desk_side_cabinet_C[0].rotation = [0, 0, 0]
planter_box_A[0].position = [12.769615850655368, 9.811217804654468, 0.25]
planter_box_A[0].rotation = [0, 0, 0]
small_potted_plant_B[0].position = [15.399402232922126, 2.1819775269049586, 0.25]
small_potted_plant_B[0].rotation = [0, 0, 0]
small_potted_plant_C[0].position = [12.696441694792641, 9.910727338756127, 0.25]
small_potted_plant_C[0].rotation = [0, 0, 0]
counter_stool_B[0].position = [8.484582105597202, 8.790768541475176, 0.45]
counter_stool_B[0].rotation = [0, 0, 0]
magazine_D[0].position = [9.019985164671569, 7.219112293501722, 0.01]
magazine_D[0].rotation = [0, 0, 0]
coat_stand_C[0].position = [7.8629433718250255, 6.403639902280236, 0.9]
coat_stand_C[0].rotation = [0, 0, 0]
low_storage_cabinet_C[0].position = [2.1760811625273258, 8.970872162698493, 0.375]
low_storage_cabinet_C[0].rotation = [0, 0, 0]
framed_photo_B[0].position = [12.096613407185027, 10.370986218819393, 0.175]
framed_photo_B[0].rotation = [0, 0, 0]
office_printer_B[0].position = [13.806225704310924, 3.441828287559784, 0.225]
office_printer_B[0].rotation = [0, 0, 0]
work_bench_desk_C[0].position = [10.200202933295435, 8.970876601450726, 0.37]
work_bench_desk_C[0].rotation = [0, 0, 0]
standing_meeting_table_B[0].position = [11.163623031797915, 10.803580174026692, 0.525]
standing_meeting_table_B[0].rotation = [0, 0, 0]
team_table_B[0].position = [6.7577071033759415, 3.987763290932925, 0.375]
team_table_B[0].rotation = [0, 0, 0]
magazine_E[0].position = [10.144932097090834, 8.518338403688407, 0.01]
magazine_E[0].rotation = [0, 0, 0]
task_chair_E[0].position = [15.88111466572705, 7.508925341426563, 0.575]
task_chair_E[0].rotation = [0, 0, 0]
wayfinding_sign_B[0].position = [14.177649675414951, 7.974486371982286, 0.125]
wayfinding_sign_B[0].rotation = [0, 0, 0]
desk_organizer_C[0].position = [8.08870664866521, 4.76956039663852, 0.09]
desk_organizer_C[0].rotation = [0, 0, 0]
high_stool_H[0].position = [12.454519074463375, 5.996069985961634, 0.5]
high_stool_H[0].rotation = [0, 0, 0]
high_stool_I[0].position = [5.587819580761435, 6.993396641300852, 0.5]
high_stool_I[0].rotation = [0, 0, 0]
wayfinding_sign_C[0].position = [11.856380432950566, 4.341097401293645, 0.125]
wayfinding_sign_C[0].rotation = [0, 0, 0]
low_storage_cabinet_D[0].position = [9.086533434404405, 0.4206859335858968, 0.375]
low_storage_cabinet_D[0].rotation = [0, 0, 0]
framed_photo_C[0].position = [8.34752306853968, 3.297437202084518, 0.25]
framed_photo_C[0].rotation = [0, 0, 0]
desk_side_cabinet_D[0].position = [14.90198468664979, 5.755686080562654, 0.36]
desk_side_cabinet_D[0].rotation = [0, 0, 0]
planter_box_B[0].position = [13.066252109303443, 8.271436442322388, 0.25]
planter_box_B[0].rotation = [0, 0, 0]
wayfinding_sign_D[0].position = [11.577825154569378, 4.418687093349686, 0.125]
wayfinding_sign_D[0].rotation = [0, 0, 0]
file_tray_D[0].position = [11.326939457910228, 1.4195818415350516, 0.025]
file_tray_D[0].rotation = [0, 0, 0]
file_tray_E[0].position = [4.990236787289319, 10.545227166718629, 0.025]
file_tray_E[0].rotation = [0, 0, 0]
notepad_stack_B[0].position = [14.537718678099724, 4.463809380722231, 0.04]
notepad_stack_B[0].rotation = [0, 0, 0]
framed_photo_D[0].position = [6.3399790976392545, 4.017558006057724, 0.175]
framed_photo_D[0].rotation = [0, 0, 0]
mobile_pedestal_C[0].position = [12.138716625091424, 2.8423919127742048, 0.3]
mobile_pedestal_C[0].rotation = [0, 0, 0]
task_chair_F[0].position = [3.5421261697990936, 7.657405696064766, 0.575]
task_chair_F[0].rotation = [0, 0, 0]
standing_meeting_table_C[0].position = [13.782718875861573, 3.9117258732830313, 0.525]
standing_meeting_table_C[0].rotation = [0, 0, 0]
notepad_stack_C[0].position = [5.8154460808926745, 10.723298585934419, 0.04]
notepad_stack_C[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [14.728859005869191, 4.89742980311961, 0.825]
floor_lamp_B[0].rotation = [0, 0, 0]
low_storage_cabinet_A[0].position = [9.39169668609769, 3.878045946674927, 0.375]
low_storage_cabinet_A[0].rotation = [0, 0, 0]
task_chair_A[0].position = [5.060260056535072, 8.532541605580198, 0.575]
task_chair_A[0].rotation = [0, 0, 0]
magazine_A[0].position = [2.192580752417688, 10.035935836136357, 0.01]
magazine_A[0].rotation = [0, 0, 0]
pen_cup_A[0].position = [8.530890567487827, 1.5484611293209998, 0.11]
pen_cup_A[0].rotation = [0, 0, 0]
high_stool_A[0].position = [8.608519123324962, 5.85339418930362, 0.5]
high_stool_A[0].rotation = [0, 0, 0]
magazine_B[0].position = [8.156572119514033, 0.1487110703556389, 0.015]
magazine_B[0].rotation = [0, 0, 0]
work_bench_desk_A[0].position = [8.523460715180946, 4.255742618594684, 0.37]
work_bench_desk_A[0].rotation = [0, 0, 0]
side_occasion_table_A[0].position = [16.952656284825377, 6.993599582902142, 0.275]
side_occasion_table_A[0].rotation = [0, 0, 0]
file_tray_A[0].position = [5.821014472169757, 8.136918115029129, 0.035]
file_tray_A[0].rotation = [0, 0, 0]
task_chair_B[0].position = [12.060832906455557, 10.403204069515683, 0.575]
task_chair_B[0].rotation = [0, 0, 0]
office_printer_A[0].position = [4.052135306579803, 4.86550204134479, 0.225]
office_printer_A[0].rotation = [0, 0, 0]
coat_stand_A[0].position = [6.084928991104851, 7.49752435333705, 0.9]
coat_stand_A[0].rotation = [0, 0, 0]
pen_cup_B[0].position = [2.742917158411661, 9.866352557059802, 0.11]
pen_cup_B[0].rotation = [0, 0, 0]
side_occasion_table_B[0].position = [4.475751041165772, 4.965837385663199, 0.275]
side_occasion_table_B[0].rotation = [0, 0, 0]
lockers_bank[0].position = [6.184650196522248, 6.75004596456961, 0.95]
lockers_bank[0].rotation = [0, 0, 0]
side_occasion_table_C[0].position = [15.907413473054335, 5.2195833867364545, 0.275]
side_occasion_table_C[0].rotation = [0, 0, 0]
printer_side_table_A[0].position = [7.668589681743031, 7.732083975109591, 0.35]
printer_side_table_A[0].rotation = [0, 0, 0]
task_chair_C[0].position = [8.791026922549293, 10.295429784672002, 0.575]
task_chair_C[0].rotation = [0, 0, 0]
high_stool_B[0].position = [13.90897849537072, 0.3788719772837914, 0.5]
high_stool_B[0].rotation = [0, 0, 0]
high_stool_C[0].position = [14.746532719927563, 5.025830881383255, 0.5]
high_stool_C[0].rotation = [0, 0, 0]
mobile_pedestal_A[0].position = [8.972263374339539, 4.954319639330282, 0.3]
mobile_pedestal_A[0].rotation = [0, 0, 0]
mobile_pedestal_B[0].position = [3.391405676547318, 6.46263442924552, 0.3]
mobile_pedestal_B[0].rotation = [0, 0, 0]
coat_stand_B[0].position = [9.269130445636025, 3.5699617157164427, 0.9]
coat_stand_B[0].rotation = [0, 0, 0]
desk_organizer_A[0].position = [12.017021663475944, 1.2677452535339495, 0.09]
desk_organizer_A[0].rotation = [0, 0, 0]
counter_stool_A[0].position = [9.80935752394147, 10.399866003228437, 0.45]
counter_stool_A[0].rotation = [0, 0, 0]
magazine_C[0].position = [9.206515570754425, 7.118922379904773, 0.015]
magazine_C[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [13.5103185029081, 6.872421395724417, 0.825]
floor_lamp_A[0].rotation = [0, 0, 0]
notepad_stack_A[0].position = [13.242167357941714, 8.731905449674143, 0.04]
notepad_stack_A[0].rotation = [0, 0, 0]
high_stool_D[0].position = [6.299525527961685, 1.6224409297776303, 0.5]
high_stool_D[0].rotation = [0, 0, 0]
file_tray_B[0].position = [9.10276629207807, 0.2988680296613794, 0.035]
file_tray_B[0].rotation = [0, 0, 0]
wayfinding_sign_A[0].position = [4.887473164425642, 6.494482462155478, 0.125]
wayfinding_sign_A[0].rotation = [0, 0, 0]
office_monitor_A[0].position = [4.469544546444729, 8.462724681543175, 0.225]
office_monitor_A[0].rotation = [0, 0, 0]
sofa_modular[0].position = [14.048879212163568, 3.2334634873164365, 0.425]
sofa_modular[0].rotation = [0, 0, 0]
desk_side_cabinet_A[0].position = [7.557856303258847, 0.9441271770078342, 0.36]
desk_side_cabinet_A[0].rotation = [0, 0, 0]
high_stool_E[0].position = [2.5602465035046116, 5.35367672373356, 0.5]
high_stool_E[0].rotation = [0, 0, 0]
low_storage_cabinet_B[0].position = [8.972359842335122, 7.458777482327908, 0.375]
low_storage_cabinet_B[0].rotation = [0, 0, 0]
desk_organizer_B[0].position = [6.729001489102119, 9.320795232298117, 0.09]
desk_organizer_B[0].rotation = [0, 0, 0]
standing_meeting_table_A[0].position = [4.998929067706196, 6.239989335664095, 0.525]
standing_meeting_table_A[0].rotation = [0, 0, 0]
high_stool_F[0].position = [0.6488421155209694, 4.8911689786125825, 0.5]
high_stool_F[0].rotation = [0, 0, 0]
keyboard_and_mouse_set[0].position = [6.014739653264417, 0.12014015112486987, 0.025]
keyboard_and_mouse_set[0].rotation = [0, 0, 0]
printer_side_table_B[0].position = [5.807883615853967, 7.796599601696041, 0.35]
printer_side_table_B[0].rotation = [0, 0, 0]
framed_photo_A[0].position = [7.597996291444255, 7.012210705004719, 0.175]
framed_photo_A[0].rotation = [0, 0, 0]
office_monitor_B[0].position = [2.0712262065825207, 2.7102295959901124, 0.225]
office_monitor_B[0].rotation = [0, 0, 0]
desk_side_cabinet_B[0].position = [5.6594117521072835, 9.821932274258266, 0.36]
desk_side_cabinet_B[0].rotation = [0, 0, 0]
small_potted_plant_A[0].position = [15.650598843358171, 3.482385865913238, 0.325]
small_potted_plant_A[0].rotation = [0, 0, 0]
high_stool_G[0].position = [6.8866512708829015, 10.331794382532797, 0.5]
high_stool_G[0].rotation = [0, 0, 0]
team_table_A[0].position = [3.823194191100861, 5.2204861924051755, 0.375]
team_table_A[0].rotation = [0, 0, 0]
work_bench_desk_B[0].position = [3.347292177307925, 4.325816091281641, 0.37]
work_bench_desk_B[0].rotation = [0, 0, 0]
file_tray_C[0].position = [2.3767552217460675, 3.474582787708777, 0.035]
file_tray_C[0].rotation = [0, 0, 0]
task_chair_D[0].position = [6.760735872920213, 9.787027997053567, 0.575]
task_chair_D[0].rotation = [0, 0, 0]
desk_side_cabinet_C[0].position = [14.201738697672479, 4.5142025897234745, 0.36]
desk_side_cabinet_C[0].rotation = [0, 0, 0]
planter_box_A[0].position = [12.769615850655368, 9.811217804654468, 0.25]
planter_box_A[0].rotation = [0, 0, 0]
small_potted_plant_B[0].position = [15.399402232922126, 2.1819775269049586, 0.25]
small_potted_plant_B[0].rotation = [0, 0, 0]
small_potted_plant_C[0].position = [12.696441694792641, 9.910727338756127, 0.25]
small_potted_plant_C[0].rotation = [0, 0, 0]
counter_stool_B[0].position = [8.484582105597202, 8.790768541475176, 0.45]
counter_stool_B[0].rotation = [0, 0, 0]
magazine_D[0].position = [9.019985164671569, 7.219112293501722, 0.01]
magazine_D[0].rotation = [0, 0, 0]
coat_stand_C[0].position = [7.8629433718250255, 6.403639902280236, 0.9]
coat_stand_C[0].rotation = [0, 0, 0]
low_storage_cabinet_C[0].position = [2.1760811625273258, 8.970872162698493, 0.375]
low_storage_cabinet_C[0].rotation = [0, 0, 0]
framed_photo_B[0].position = [12.096613407185027, 10.370986218819393, 0.175]
framed_photo_B[0].rotation = [0, 0, 0]
office_printer_B[0].position = [13.806225704310924, 3.441828287559784, 0.225]
office_printer_B[0].rotation = [0, 0, 0]
work_bench_desk_C[0].position = [10.200202933295435, 8.970876601450726, 0.37]
work_bench_desk_C[0].rotation = [0, 0, 0]
standing_meeting_table_B[0].position = [11.163623031797915, 10.803580174026692, 0.525]
standing_meeting_table_B[0].rotation = [0, 0, 0]
team_table_B[0].position = [6.7577071033759415, 3.987763290932925, 0.375]
team_table_B[0].rotation = [0, 0, 0]
magazine_E[0].position = [10.144932097090834, 8.518338403688407, 0.01]
magazine_E[0].rotation = [0, 0, 0]
task_chair_E[0].position = [15.88111466572705, 7.508925341426563, 0.575]
task_chair_E[0].rotation = [0, 0, 0]
wayfinding_sign_B[0].position = [14.177649675414951, 7.974486371982286, 0.125]
wayfinding_sign_B[0].rotation = [0, 0, 0]
desk_organizer_C[0].position = [8.08870664866521, 4.76956039663852, 0.09]
desk_organizer_C[0].rotation = [0, 0, 0]
high_stool_H[0].position = [12.454519074463375, 5.996069985961634, 0.5]
high_stool_H[0].rotation = [0, 0, 0]
high_stool_I[0].position = [5.587819580761435, 6.993396641300852, 0.5]
high_stool_I[0].rotation = [0, 0, 0]
wayfinding_sign_C[0].position = [11.856380432950566, 4.341097401293645, 0.125]
wayfinding_sign_C[0].rotation = [0, 0, 0]
low_storage_cabinet_D[0].position = [9.086533434404405, 0.4206859335858968, 0.375]
low_storage_cabinet_D[0].rotation = [0, 0, 0]
framed_photo_C[0].position = [8.34752306853968, 3.297437202084518, 0.25]
framed_photo_C[0].rotation = [0, 0, 0]
desk_side_cabinet_D[0].position = [14.90198468664979, 5.755686080562654, 0.36]
desk_side_cabinet_D[0].rotation = [0, 0, 0]
planter_box_B[0].position = [13.066252109303443, 8.271436442322388, 0.25]
planter_box_B[0].rotation = [0, 0, 0]
wayfinding_sign_D[0].position = [11.577825154569378, 4.418687093349686, 0.125]
wayfinding_sign_D[0].rotation = [0, 0, 0]
file_tray_D[0].position = [11.326939457910228, 1.4195818415350516, 0.025]
file_tray_D[0].rotation = [0, 0, 0]
file_tray_E[0].position = [4.990236787289319, 10.545227166718629, 0.025]
file_tray_E[0].rotation = [0, 0, 0]
notepad_stack_B[0].position = [14.537718678099724, 4.463809380722231, 0.04]
notepad_stack_B[0].rotation = [0, 0, 0]
framed_photo_D[0].position = [6.3399790976392545, 4.017558006057724, 0.175]
framed_photo_D[0].rotation = [0, 0, 0]
mobile_pedestal_C[0].position = [12.138716625091424, 2.8423919127742048, 0.3]
mobile_pedestal_C[0].rotation = [0, 0, 0]
task_chair_F[0].position = [3.5421261697990936, 7.657405696064766, 0.575]
task_chair_F[0].rotation = [0, 0, 0]
standing_meeting_table_C[0].position = [13.782718875861573, 3.9117258732830313, 0.525]
standing_meeting_table_C[0].rotation = [0, 0, 0]
notepad_stack_C[0].position = [5.8154460808926745, 10.723298585934419, 0.04]
notepad_stack_C[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [14.728859005869191, 4.89742980311961, 0.825]
floor_lamp_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Helper functions assign an initial pose and add the required position and
# orientation constraints. Exact anchors preserve the planned clearances.
def _place_floor(_asset, _position, _yaw):
    _asset[0].position = list(_position)
    _asset[0].rotation = [0.0, 0.0, _yaw]
    _anchor = AssetInstance(
        position=list(_position),
        rotation=[0.0, 0.0, _yaw],
    )
    solver.distance_constraint(_asset[0], _anchor, 0.0, 0.0, weight=10)
    solver.align_with(_asset[0], _anchor)


def _place_floor_facing(_asset, _position, _target):
    _asset[0].position = list(_position)
    _target_position = _target[0].position
    _yaw = radians(0)
    if _target_position[1] > _position[1]:
        _yaw = radians(90)
    elif _target_position[1] < _position[1]:
        _yaw = radians(-90)
    elif _target_position[0] < _position[0]:
        _yaw = radians(180)

    _asset[0].rotation = [0.0, 0.0, _yaw]
    _anchor = AssetInstance(position=list(_position))
    solver.distance_constraint(_asset[0], _anchor, 0.0, 0.0, weight=10)
    solver.point_towards(_asset[0], _target[0])


def _place_against_wall(_asset, _position, _yaw, _wall):
    _asset[0].position = list(_position)
    _asset[0].rotation = [0.0, 0.0, _yaw]
    _orientation_anchor = AssetInstance(rotation=[0.0, 0.0, _yaw])
    _position_anchor = AssetInstance(position=list(_position))

    # The wall relationship is the primary semantic position constraint.
    solver.against_wall(_asset[0], _wall)
    solver.distance_constraint(
        _asset[0], _position_anchor, 0.0, 0.0, weight=10
    )
    solver.align_with(_asset[0], _orientation_anchor)


def _place_on_top(_asset, _support, _position, _yaw=0.0):
    _asset[0].position = list(_position)
    _asset[0].rotation = [0.0, 0.0, _yaw]
    _anchor = AssetInstance(
        position=list(_position),
        rotation=[0.0, 0.0, _yaw],
    )

    # on_top_of controls height; the exact anchor keeps the item on the
    # intended part of the supporting surface.
    solver.on_top_of(_asset[0], _support[0])
    solver.distance_constraint(_asset[0], _anchor, 0.0, 0.0, weight=10)
    solver.align_with(_asset[0], _anchor)


# ---------------------------------------------------------------------------
# Large desks and their work areas. They are kept north of the two south-wall
# door approaches, leaving direct circulation lanes at x=8.39 and x=12.07.
# ---------------------------------------------------------------------------

_place_floor(work_bench_desk_A, (4.10, 1.75, 0.37), radians(90))
_place_floor(work_bench_desk_B, (8.90, 2.45, 0.37), radians(90))
_place_floor(work_bench_desk_C, (12.85, 2.50, 0.37), radians(90))

_place_floor(mobile_pedestal_A, (5.65, 1.75, 0.30), radians(90))
_place_floor(mobile_pedestal_B, (10.35, 2.45, 0.30), radians(90))
_place_floor(mobile_pedestal_C, (14.35, 2.50, 0.30), radians(90))

# The planter is directly in front of work bench o0006.
_place_floor(planter_box_A, (4.10, 4.55, 0.25), radians(90))
solver.point_towards(work_bench_desk_A[0], planter_box_A[0])

_place_floor(planter_box_B, (13.75, 5.25, 0.25), radians(90))

# Chairs face their corresponding work benches.
_place_floor_facing(task_chair_A, (3.70, 3.05, 0.575), work_bench_desk_A)
_place_floor_facing(task_chair_B, (4.55, 3.05, 0.575), work_bench_desk_A)
_place_floor_facing(task_chair_C, (8.50, 3.75, 0.575), work_bench_desk_B)
_place_floor_facing(task_chair_D, (9.35, 3.75, 0.575), work_bench_desk_B)
_place_floor_facing(task_chair_E, (12.45, 3.80, 0.575), work_bench_desk_C)
_place_floor_facing(task_chair_F, (13.30, 3.80, 0.575), work_bench_desk_C)

# ---------------------------------------------------------------------------
# Collaborative tables. Team table A is centered exactly between high stools
# B (o0018) and D (o0028), with equal center-to-center distances.
# ---------------------------------------------------------------------------

_place_floor(team_table_A, (6.40, 6.25, 0.375), radians(0))
_place_floor(high_stool_B, (5.45, 6.25, 0.50), radians(0))
_place_floor(high_stool_D, (7.35, 6.25, 0.50), radians(180))
solver.point_towards(high_stool_B[0], team_table_A[0])
solver.point_towards(high_stool_D[0], team_table_A[0])
solver.distance_constraint(
    high_stool_B[0], team_table_A[0], 0.95, 0.95, weight=10
)
solver.distance_constraint(
    high_stool_D[0], team_table_A[0], 0.95, 0.95, weight=10
)

_place_floor(team_table_B, (10.40, 6.25, 0.375), radians(0))
_place_floor(high_stool_H, (9.45, 6.25, 0.50), radians(0))
_place_floor(high_stool_I, (11.35, 6.25, 0.50), radians(180))
solver.point_towards(high_stool_H[0], team_table_B[0])
solver.point_towards(high_stool_I[0], team_table_B[0])

# Three standing meeting groups occupy open regions away from door swings.
_place_floor(standing_meeting_table_A, (3.75, 8.85, 0.525), radians(0))
_place_floor(high_stool_A, (4.60, 8.85, 0.50), radians(180))
_place_floor(high_stool_C, (3.75, 7.95, 0.50), radians(90))
solver.point_towards(high_stool_A[0], standing_meeting_table_A[0])
solver.point_towards(high_stool_C[0], standing_meeting_table_A[0])

_place_floor(standing_meeting_table_B, (8.65, 8.80, 0.525), radians(0))
_place_floor(high_stool_E, (9.50, 8.80, 0.50), radians(180))
_place_floor(high_stool_F, (8.65, 7.90, 0.50), radians(90))
solver.point_towards(high_stool_E[0], standing_meeting_table_B[0])
solver.point_towards(high_stool_F[0], standing_meeting_table_B[0])

_place_floor(standing_meeting_table_C, (15.55, 6.45, 0.525), radians(0))
_place_floor(high_stool_G, (14.70, 6.45, 0.50), radians(0))
_place_floor(counter_stool_A, (15.55, 7.35, 0.45), radians(-90))
_place_floor(counter_stool_B, (16.40, 6.45, 0.45), radians(180))
solver.point_towards(high_stool_G[0], standing_meeting_table_C[0])
solver.point_towards(counter_stool_A[0], standing_meeting_table_C[0])
solver.point_towards(counter_stool_B[0], standing_meeting_table_C[0])

# ---------------------------------------------------------------------------
# Perimeter storage. Top-wall units avoid the doors centered at x=6.88 and
# x=12.18. Bottom-wall units avoid the doors centered at x=8.39 and x=12.07.
# ---------------------------------------------------------------------------

_place_against_wall(
    low_storage_cabinet_A,
    (3.15, 10.775, 0.375),
    radians(90),
    walls[12],
)
_place_against_wall(
    low_storage_cabinet_B,
    (5.05, 10.775, 0.375),
    radians(90),
    walls[12],
)
_place_against_wall(
    low_storage_cabinet_C,
    (9.20, 10.775, 0.375),
    radians(90),
    walls[12],
)
_place_against_wall(
    low_storage_cabinet_D,
    (10.95, 10.775, 0.375),
    radians(90),
    walls[12],
)

# Desk side cabinet A is o0033 and is explicitly constrained to the wall.
_place_against_wall(
    desk_side_cabinet_A,
    (3.00, 0.225, 0.36),
    radians(90),
    walls[4],
)
_place_against_wall(
    desk_side_cabinet_B,
    (6.20, 0.225, 0.36),
    radians(90),
    walls[4],
)
_place_against_wall(
    desk_side_cabinet_C,
    (10.50, 0.225, 0.36),
    radians(90),
    walls[4],
)
_place_against_wall(
    desk_side_cabinet_D,
    (14.30, 0.225, 0.36),
    radians(90),
    walls[4],
)

# Lockers use the solid upper part of the west wall, beyond the west doorway.
_place_against_wall(
    lockers_bank,
    (2.25, 9.45, 0.95),
    radians(0),
    walls[13],
)

# ---------------------------------------------------------------------------
# Lounge, printing, lighting, and freestanding accessories.
# ---------------------------------------------------------------------------

# The sofa backs onto the east wall and faces the open room.
_place_against_wall(
    sofa_modular,
    (16.55, 3.80, 0.425),
    radians(180),
    walls[7],
)

_place_floor(side_occasion_table_A, (15.45, 2.05, 0.275), radians(0))
_place_floor(side_occasion_table_B, (15.45, 5.50, 0.275), radians(0))
_place_floor(side_occasion_table_C, (2.90, 7.90, 0.275), radians(0))

_place_floor(floor_lamp_A, (15.75, 5.95, 0.825), radians(180))
_place_against_wall(
    floor_lamp_B,
    (16.775, 1.55, 0.825),
    radians(180),
    walls[7],
)

# One printer station fits in the upper-left recess; the other sits in the
# open upper-middle area without obstructing either top-wall door.
_place_against_wall(
    printer_side_table_A,
    (0.50, 5.70, 0.35),
    radians(90),
    walls[0],
)
_place_floor(printer_side_table_B, (12.20, 8.25, 0.35), radians(0))

_place_floor(coat_stand_A, (2.55, 5.40, 0.90), radians(0))
_place_floor(coat_stand_B, (1.45, 4.80, 0.90), radians(0))
_place_against_wall(
    coat_stand_C,
    (16.775, 7.60, 0.90),
    radians(180),
    walls[7],
)

_place_floor(small_potted_plant_A, (14.40, 4.20, 0.325), radians(0))
_place_floor(small_potted_plant_B, (11.65, 4.65, 0.25), radians(0))
_place_floor(small_potted_plant_C, (7.70, 4.60, 0.25), radians(0))

# ---------------------------------------------------------------------------
# Desktop equipment and stationery. Every small item is constrained both to
# its supporting surface and to a non-overlapping location on that surface.
# ---------------------------------------------------------------------------

# Work bench A.
_place_on_top(
    office_monitor_A,
    work_bench_desk_A,
    (3.65, 1.70, 0.965),
    radians(90),
)
_place_on_top(
    keyboard_and_mouse_set,
    work_bench_desk_A,
    (4.25, 1.70, 0.765),
    radians(90),
)
_place_on_top(
    pen_cup_A,
    work_bench_desk_A,
    (4.75, 1.70, 0.85),
    radians(90),
)
_place_on_top(
    magazine_A,
    work_bench_desk_A,
    (4.25, 2.10, 0.75),
    radians(90),
)

# Work bench B.
_place_on_top(
    office_monitor_B,
    work_bench_desk_B,
    (8.50, 2.40, 0.965),
    radians(90),
)
_place_on_top(
    pen_cup_B,
    work_bench_desk_B,
    (9.35, 2.25, 0.85),
    radians(90),
)
_place_on_top(
    magazine_B,
    work_bench_desk_B,
    (9.10, 2.70, 0.755),
    radians(90),
)
_place_on_top(
    file_tray_A,
    work_bench_desk_B,
    (8.45, 2.80, 0.775),
    radians(90),
)

# Work bench C.
_place_on_top(
    file_tray_B,
    work_bench_desk_C,
    (12.45, 2.35, 0.775),
    radians(90),
)
_place_on_top(
    notepad_stack_C,
    work_bench_desk_C,
    (13.20, 2.30, 0.78),
    radians(90),
)

# Required relationship: desk organizer o0023 is on desk side cabinet o0050.
_place_on_top(
    desk_organizer_A,
    desk_side_cabinet_A,
    (3.00, 0.225, 0.81),
    radians(90),
)
_place_on_top(
    desk_organizer_B,
    desk_side_cabinet_B,
    (6.20, 0.225, 0.81),
    radians(90),
)
_place_on_top(
    desk_organizer_C,
    desk_side_cabinet_C,
    (10.50, 0.225, 0.81),
    radians(90),
)

# Printer bodies are centered on their dedicated tables.
_place_on_top(
    office_printer_A,
    printer_side_table_A,
    (0.50, 5.70, 0.925),
    radians(90),
)
_place_on_top(
    office_printer_B,
    printer_side_table_B,
    (12.20, 8.25, 0.925),
    radians(0),
)

# Team-table documents remain near the center so they do not reduce seating
# clearance at the table edges.
_place_on_top(
    file_tray_C,
    team_table_A,
    (6.40, 6.25, 0.785),
    radians(0),
)
_place_on_top(
    magazine_D,
    team_table_B,
    (10.20, 6.25, 0.765),
    radians(0),
)

# Lounge and auxiliary-table objects.
_place_on_top(
    magazine_C,
    side_occasion_table_A,
    (15.45, 2.05, 0.565),
    radians(0),
)
_place_on_top(
    magazine_E,
    side_occasion_table_B,
    (15.45, 5.50, 0.56),
    radians(0),
)
_place_on_top(
    notepad_stack_A,
    side_occasion_table_C,
    (2.90, 7.90, 0.59),
    radians(0),
)
_place_on_top(
    notepad_stack_B,
    side_occasion_table_B,
    (15.25, 5.50, 0.59),
    radians(0),
)

# Photos and signs share the long storage-cabinet tops with lateral spacing.
_place_on_top(
    framed_photo_A,
    low_storage_cabinet_A,
    (2.80, 10.775, 0.925),
    radians(90),
)
_place_on_top(
    wayfinding_sign_A,
    low_storage_cabinet_A,
    (3.45, 10.775, 0.875),
    radians(90),
)

_place_on_top(
    framed_photo_B,
    low_storage_cabinet_B,
    (4.70, 10.775, 0.925),
    radians(90),
)
_place_on_top(
    wayfinding_sign_B,
    low_storage_cabinet_B,
    (5.35, 10.775, 0.875),
    radians(90),
)

_place_on_top(
    framed_photo_C,
    low_storage_cabinet_C,
    (8.85, 10.775, 1.00),
    radians(90),
)
_place_on_top(
    wayfinding_sign_C,
    low_storage_cabinet_C,
    (9.50, 10.775, 0.875),
    radians(90),
)

_place_on_top(
    framed_photo_D,
    low_storage_cabinet_D,
    (10.60, 10.775, 0.925),
    radians(90),
)
_place_on_top(
    wayfinding_sign_D,
    low_storage_cabinet_D,
    (11.25, 10.775, 0.875),
    radians(90),
)

_place_on_top(
    file_tray_D,
    desk_side_cabinet_C,
    (10.50, 0.225, 0.745),
    radians(90),
)
_place_on_top(
    file_tray_E,
    desk_side_cabinet_D,
    (14.30, 0.225, 0.745),
    radians(90),
)

solver.constraints = []
desk_organizer_C[0].position = [10.5, 0.22499999403953552, 0.8100000619888306]
desk_organizer_C[0].rotation = [0, 0, 1.5833626980517244]
desk_organizer_C[0].optimize = 2
office_printer_B[0].position = [12.199999809265137, 8.25, 0.9249999523162842]
office_printer_B[0].rotation = [0, 0, 0.01256637125682779]
office_printer_B[0].optimize = 2
mobile_pedestal_C[0].position = [14.350000381469727, 2.5, 0.30000001192092896]
mobile_pedestal_C[0].rotation = [0, 0, 1.5802211042556205]
mobile_pedestal_C[0].optimize = 2
task_chair_E[0].position = [12.449999809265137, 3.799999952316284, 0.574999988079071]
task_chair_E[0].rotation = [0, 0, -1.5613715493341729]
task_chair_E[0].optimize = 2
floor_lamp_A[0].position = [15.75, 5.949999809265137, 0.824999988079071]
floor_lamp_A[0].rotation = [0, 0, -3.1321678761290697]
floor_lamp_A[0].optimize = 2
file_tray_E[0].position = [14.300000190734863, 0.22499999403953552, 0.7450000047683716]
file_tray_E[0].rotation = [0, 0, 1.5833626980517244]
file_tray_E[0].optimize = 2
office_monitor_B[0].position = [8.5, 2.4000000953674316, 0.9650000333786011]
office_monitor_B[0].rotation = [0, 0, 1.5833626980517244]
office_monitor_B[0].optimize = 2
wayfinding_sign_A[0].position = [3.1895925998687744, 10.66712474822998, 0.875]
wayfinding_sign_A[0].rotation = [0, 0, 1.5833626980517244]
wayfinding_sign_A[0].optimize = 2
desk_organizer_B[0].position = [6.199999809265137, 0.22499999403953552, 0.8100000619888306]
desk_organizer_B[0].rotation = [0, 0, 1.5833626980517244]
desk_organizer_B[0].optimize = 2
planter_box_A[0].position = [4.099999904632568, 4.550000190734863, 0.25]
planter_box_A[0].rotation = [0, 0, 1.5833626980517244]
planter_box_A[0].optimize = 2
high_stool_G[0].position = [14.699999809265137, 6.449999809265137, 0.5]
high_stool_G[0].rotation = [0, 0, 0.01256637125682779]
high_stool_G[0].optimize = 2
side_occasion_table_B[0].position = [15.449999809265137, 5.5, 0.2750000059604645]
side_occasion_table_B[0].rotation = [0, 0, 0.0157079639172164]
side_occasion_table_B[0].optimize = 2
keyboard_and_mouse_set[0].position = [4.25, 1.7000000476837158, 0.7649999856948853]
keyboard_and_mouse_set[0].rotation = [0, 0, 1.5833626980517244]
keyboard_and_mouse_set[0].optimize = 2
sofa_modular[0].position = [16.549997329711914, 3.799999952316284, 0.42500001192092896]
sofa_modular[0].rotation = [0, 0, -3.1415926086644137]
sofa_modular[0].optimize = 2
wayfinding_sign_C[0].position = [9.239591598510742, 10.66712474822998, 0.875]
wayfinding_sign_C[0].rotation = [0, 0, 1.5833626980517244]
wayfinding_sign_C[0].optimize = 2
high_stool_B[0].position = [5.449999809265137, 6.25, 0.5]
high_stool_B[0].rotation = [0, 0, 0.0157079639172164]
high_stool_B[0].optimize = 2
task_chair_A[0].position = [3.700000047683716, 3.049999952316284, 0.574999988079071]
task_chair_A[0].rotation = [0, 0, -1.5613715493341729]
task_chair_A[0].optimize = 2
low_storage_cabinet_A[0].position = [3.1500000953674316, 10.77508544921875, 0.375]
low_storage_cabinet_A[0].rotation = [0, 0, -1.5710158042281608]
low_storage_cabinet_A[0].optimize = 2
counter_stool_B[0].position = [16.399999618530273, 6.449999809265137, 0.44999998807907104]
counter_stool_B[0].rotation = [0, 0, -3.1290262823329655]
counter_stool_B[0].optimize = 2
framed_photo_C[0].position = [8.850000381469727, 10.774999618530273, 1.0]
framed_photo_C[0].rotation = [0, 0, 1.5833626980517244]
framed_photo_C[0].optimize = 2
pen_cup_A[0].position = [4.75, 1.7000000476837158, 0.8500000238418579]
pen_cup_A[0].rotation = [0, 0, 1.5833626980517244]
pen_cup_A[0].optimize = 2
framed_photo_A[0].position = [2.799999952316284, 10.774999618530273, 0.925000011920929]
framed_photo_A[0].rotation = [0, 0, 1.5833626980517244]
framed_photo_A[0].optimize = 2
pen_cup_B[0].position = [9.350000381469727, 2.25, 0.8500000238418579]
pen_cup_B[0].rotation = [0, 0, 1.5833626980517244]
pen_cup_B[0].optimize = 2
notepad_stack_A[0].position = [2.9000000953674316, 7.900000095367432, 0.5900000333786011]
notepad_stack_A[0].rotation = [0, 0, 0.01256637125682779]
notepad_stack_A[0].optimize = 2
lockers_bank[0].position = [2.261289596557617, 9.449999809265137, 0.949999988079071]
lockers_bank[0].rotation = [0, 0, 4.8610377059484875e-08]
lockers_bank[0].optimize = 2
coat_stand_A[0].position = [2.549999952316284, 5.400000095367432, 0.8999999761581421]
coat_stand_A[0].rotation = [0, 0, 0.00942477746072377]
coat_stand_A[0].optimize = 2
task_chair_F[0].position = [13.300000190734863, 3.799999952316284, 0.574999988079071]
task_chair_F[0].rotation = [0, 0, -1.5613715493341729]
task_chair_F[0].optimize = 2
task_chair_B[0].position = [4.550000190734863, 3.049999952316284, 0.574999988079071]
task_chair_B[0].rotation = [0, 0, -1.5613715493341729]
task_chair_B[0].optimize = 2
high_stool_F[0].position = [8.649999618530273, 7.900000095367432, 0.5]
high_stool_F[0].rotation = [0, 0, 1.5833626980517244]
high_stool_F[0].optimize = 2
framed_photo_B[0].position = [4.699999809265137, 10.774999618530273, 0.925000011920929]
framed_photo_B[0].rotation = [0, 0, 1.5833626980517244]
framed_photo_B[0].optimize = 2
high_stool_H[0].position = [9.449999809265137, 6.25, 0.5]
high_stool_H[0].rotation = [0, 0, 0.01256637125682779]
high_stool_H[0].optimize = 2
work_bench_desk_B[0].position = [8.899999618530273, 2.450000047683716, 0.3700000047683716]
work_bench_desk_B[0].rotation = [0, 0, 1.5990706612064889]
work_bench_desk_B[0].optimize = 2
small_potted_plant_B[0].position = [11.649999618530273, 4.650000095367432, 0.25]
small_potted_plant_B[0].rotation = [0, 0, 0.00942477746072377]
small_potted_plant_B[0].optimize = 2
task_chair_C[0].position = [8.5, 3.75, 0.574999988079071]
task_chair_C[0].rotation = [0, 0, -1.5613715493341729]
task_chair_C[0].optimize = 2
counter_stool_A[0].position = [15.550000190734863, 7.349999904632568, 0.44999998807907104]
counter_stool_A[0].rotation = [0, 0, -1.5582299555380688]
counter_stool_A[0].optimize = 2
low_storage_cabinet_B[0].position = [5.050000190734863, 10.77508544921875, 0.375]
low_storage_cabinet_B[0].rotation = [0, 0, -1.5710158042281608]
low_storage_cabinet_B[0].optimize = 2
magazine_B[0].position = [9.100000381469727, 2.700000047683716, 0.7549999952316284]
magazine_B[0].rotation = [0, 0, 1.5833626980517244]
magazine_B[0].optimize = 2
desk_side_cabinet_B[0].position = [6.199999809265137, 0.22499997913837433, 0.36000001430511475]
desk_side_cabinet_B[0].rotation = [0, 0, 1.57079637095676]
desk_side_cabinet_B[0].optimize = 2
magazine_C[0].position = [15.449999809265137, 2.049999952316284, 0.5649999976158142]
magazine_C[0].rotation = [0, 0, 0.01256637125682779]
magazine_C[0].optimize = 2
standing_meeting_table_A[0].position = [3.75, 8.850000381469727, 0.5249999761581421]
standing_meeting_table_A[0].rotation = [0, 0, 0.0157079639172164]
standing_meeting_table_A[0].optimize = 2
framed_photo_D[0].position = [10.600000381469727, 10.774999618530273, 0.925000011920929]
framed_photo_D[0].rotation = [0, 0, 1.5833626980517244]
framed_photo_D[0].optimize = 2
desk_side_cabinet_D[0].position = [14.300000190734863, 0.22499997913837433, 0.36000001430511475]
desk_side_cabinet_D[0].rotation = [0, 0, 1.57079637095676]
desk_side_cabinet_D[0].optimize = 2
magazine_E[0].position = [15.449999809265137, 5.5, 0.5600000023841858]
magazine_E[0].rotation = [0, 0, 0.01256637125682779]
magazine_E[0].optimize = 2
notepad_stack_C[0].position = [13.199999809265137, 2.299999952316284, 0.7800000309944153]
notepad_stack_C[0].rotation = [0, 0, 1.5833626980517244]
notepad_stack_C[0].optimize = 2
file_tray_A[0].position = [8.449999809265137, 2.799999952316284, 0.7750000357627869]
file_tray_A[0].rotation = [0, 0, 1.5833626980517244]
file_tray_A[0].optimize = 2
planter_box_B[0].position = [13.75, 5.25, 0.25]
planter_box_B[0].rotation = [0, 0, 1.5802211042556205]
planter_box_B[0].optimize = 2
standing_meeting_table_B[0].position = [8.649999618530273, 8.800000190734863, 0.5249999761581421]
standing_meeting_table_B[0].rotation = [0, 0, 0.0157079639172164]
standing_meeting_table_B[0].optimize = 2
magazine_D[0].position = [10.199999809265137, 6.25, 0.7599999904632568]
magazine_D[0].rotation = [0, 0, 0.01256637125682779]
magazine_D[0].optimize = 2
work_bench_desk_C[0].position = [12.850000381469727, 2.5, 0.3700000047683716]
work_bench_desk_C[0].rotation = [0, 0, 1.5927874750809192]
work_bench_desk_C[0].optimize = 2
high_stool_A[0].position = [4.599999904632568, 8.850000381469727, 0.5]
high_stool_A[0].rotation = [0, 0, -3.1290262823329655]
high_stool_A[0].optimize = 2
desk_side_cabinet_A[0].position = [3.0, 0.22499997913837433, 0.36000001430511475]
desk_side_cabinet_A[0].rotation = [0, 0, 1.57079637095676]
desk_side_cabinet_A[0].optimize = 2
low_storage_cabinet_C[0].position = [9.199999809265137, 10.77508544921875, 0.375]
low_storage_cabinet_C[0].rotation = [0, 0, -1.5710158042281608]
low_storage_cabinet_C[0].optimize = 2
file_tray_C[0].position = [6.400000095367432, 6.25, 0.7850000262260437]
file_tray_C[0].rotation = [0, 0, 0.01256637125682779]
file_tray_C[0].optimize = 2
high_stool_D[0].position = [7.408048152923584, 6.25, 0.5]
high_stool_D[0].rotation = [0, 0, -3.125884689672577]
high_stool_D[0].optimize = 2
team_table_B[0].position = [10.399999618530273, 6.25, 0.375]
team_table_B[0].rotation = [0, 0, 0.01884955539881635]
team_table_B[0].optimize = 2
work_bench_desk_A[0].position = [4.099999904632568, 1.75, 0.3700000047683716]
work_bench_desk_A[0].rotation = [0, 0, 1.6022122525607134]
work_bench_desk_A[0].optimize = 2
printer_side_table_A[0].position = [0.5, 5.700132846832275, 0.3499999940395355]
printer_side_table_A[0].rotation = [0, 0, -1.5701448279250896]
printer_side_table_A[0].optimize = 2
floor_lamp_B[0].position = [16.774999618530273, 1.5499999523162842, 0.824999988079071]
floor_lamp_B[0].rotation = [0, 0, -3.1415926111539534]
floor_lamp_B[0].optimize = 2
team_table_A[0].position = [6.400000095367432, 6.25, 0.375]
team_table_A[0].rotation = [0, 0, 0.025132740109855806]
team_table_A[0].optimize = 2
office_printer_A[0].position = [0.5, 5.699999809265137, 0.9249999523162842]
office_printer_A[0].rotation = [0, 0, 1.5833626980517244]
office_printer_A[0].optimize = 2
low_storage_cabinet_D[0].position = [10.949999809265137, 10.77508544921875, 0.375]
low_storage_cabinet_D[0].rotation = [0, 0, -1.5710158042281608]
low_storage_cabinet_D[0].optimize = 2
wayfinding_sign_D[0].position = [10.989591598510742, 10.66712474822998, 0.875]
wayfinding_sign_D[0].rotation = [0, 0, 1.5833626980517244]
wayfinding_sign_D[0].optimize = 2
mobile_pedestal_A[0].position = [5.650000095367432, 1.75, 0.30000001192092896]
mobile_pedestal_A[0].rotation = [0, 0, 1.5802211042556205]
mobile_pedestal_A[0].optimize = 2
coat_stand_B[0].position = [1.4500000476837158, 4.800000190734863, 0.8999999761581421]
coat_stand_B[0].rotation = [0, 0, 0.00942477746072377]
coat_stand_B[0].optimize = 2
high_stool_C[0].position = [3.75, 7.949999809265137, 0.5]
high_stool_C[0].rotation = [0, 0, 1.5833626980517244]
high_stool_C[0].optimize = 2
side_occasion_table_C[0].position = [2.9000000953674316, 7.900000095367432, 0.2750000059604645]
side_occasion_table_C[0].rotation = [0, 0, 0.01256637125682779]
side_occasion_table_C[0].optimize = 2
high_stool_E[0].position = [9.5, 8.800000190734863, 0.5]
high_stool_E[0].rotation = [0, 0, -3.1290262823329655]
high_stool_E[0].optimize = 2
magazine_A[0].position = [4.25, 2.0999999046325684, 0.75]
magazine_A[0].rotation = [0, 0, 1.5833626980517244]
magazine_A[0].optimize = 2
standing_meeting_table_C[0].position = [15.550000190734863, 6.449999809265137, 0.5249999761581421]
standing_meeting_table_C[0].rotation = [0, 0, 0.01884955539881635]
standing_meeting_table_C[0].optimize = 2
task_chair_D[0].position = [9.350000381469727, 3.75, 0.574999988079071]
task_chair_D[0].rotation = [0, 0, -1.5613715493341729]
task_chair_D[0].optimize = 2
wayfinding_sign_B[0].position = [5.089592933654785, 10.66712474822998, 0.875]
wayfinding_sign_B[0].rotation = [0, 0, 1.5833626980517244]
wayfinding_sign_B[0].optimize = 2
office_monitor_A[0].position = [3.6500000953674316, 1.7000000476837158, 0.9650000333786011]
office_monitor_A[0].rotation = [0, 0, 1.5833626980517244]
office_monitor_A[0].optimize = 2
mobile_pedestal_B[0].position = [10.350000381469727, 2.450000047683716, 0.30000001192092896]
mobile_pedestal_B[0].rotation = [0, 0, 1.5802211042556205]
mobile_pedestal_B[0].optimize = 2
desk_side_cabinet_C[0].position = [10.5, 0.22499999403953552, 0.36000001430511475]
desk_side_cabinet_C[0].rotation = [0, 0, 1.570796373343903]
desk_side_cabinet_C[0].optimize = 2
small_potted_plant_C[0].position = [7.699999809265137, 4.599999904632568, 0.25]
small_potted_plant_C[0].rotation = [0, 0, 0.00942477746072377]
small_potted_plant_C[0].optimize = 2
side_occasion_table_A[0].position = [15.449999809265137, 2.049999952316284, 0.2750000059604645]
side_occasion_table_A[0].rotation = [0, 0, 0.01256637125682779]
side_occasion_table_A[0].optimize = 2
file_tray_B[0].position = [12.449999809265137, 2.3499999046325684, 0.7750000357627869]
file_tray_B[0].rotation = [0, 0, 1.5833626980517244]
file_tray_B[0].optimize = 2
high_stool_I[0].position = [11.350000381469727, 6.25, 0.5]
high_stool_I[0].rotation = [0, 0, -3.1290262823329655]
high_stool_I[0].optimize = 2
printer_side_table_B[0].position = [12.199999809265137, 8.25, 0.3499999940395355]
printer_side_table_B[0].rotation = [0, 0, 0.01256637125682779]
printer_side_table_B[0].optimize = 2
desk_organizer_A[0].position = [3.0, 0.22499999403953552, 0.8100000619888306]
desk_organizer_A[0].rotation = [0, 0, 1.5833626980517244]
desk_organizer_A[0].optimize = 2
coat_stand_C[0].position = [16.774999618530273, 7.599999904632568, 0.8999999761581421]
coat_stand_C[0].rotation = [0, 0, -3.1415926111539534]
coat_stand_C[0].optimize = 2
notepad_stack_B[0].position = [15.25, 5.5, 0.5900000333786011]
notepad_stack_B[0].rotation = [0, 0, 0.01256637125682779]
notepad_stack_B[0].optimize = 2
file_tray_D[0].position = [10.5, 0.22499999403953552, 0.7450000047683716]
file_tray_D[0].rotation = [0, 0, 1.5833626980517244]
file_tray_D[0].optimize = 2
small_potted_plant_A[0].position = [14.399999618530273, 4.199999809265137, 0.32499998807907104]
small_potted_plant_A[0].rotation = [0, 0, 0.00942477746072377]
small_potted_plant_A[0].optimize = 2

