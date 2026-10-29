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
low_storage_cabinet_A = Assets(description="White six draw wood cabinets with metal legs.", size=[0.45, 1.50, 0.75], placements=[AssetInstance() for _ in range(1)])
task_chair_A = Assets(description="An office chair with a tall back and cushioning on the seat and backrest. it has wheels on the bottom.", size=[0.65, 0.65, 1.15], placements=[AssetInstance() for _ in range(1)])
magazine_A = Assets(description="a notebook with stickers and a Pokémon drawing on it.", size=[0.30, 0.21, 0.02], placements=[AssetInstance() for _ in range(1)])
pen_cup_A = Assets(description="A cylindrical gray cup with two pens and a pencil sticking out.", size=[0.09, 0.09, 0.20], placements=[AssetInstance() for _ in range(1)])
high_stool_A = Assets(description="high stool", size=[0.45, 0.45, 0.78], placements=[AssetInstance() for _ in range(1)])
magazine_B = Assets(description="A light brown hardback book with atom depicted in gold on the cover.", size=[0.27, 0.20, 0.03], placements=[AssetInstance() for _ in range(1)])
work_bench_desk_A = Assets(description="A long table with two sides.", size=[1.40, 3.20, 0.75], placements=[AssetInstance() for _ in range(1)])
side_occasion_table_A = Assets(description="side occasion table", size=[0.60, 0.60, 0.50], placements=[AssetInstance() for _ in range(1)])
file_tray_A = Assets(description="yellow file folder with a smiley face on it.", size=[0.34, 0.26, 0.06], placements=[AssetInstance() for _ in range(1)])
task_chair_B = Assets(description="An office chair with a tall back and cushioning on the seat and backrest. it has wheels on the bottom.", size=[0.65, 0.65, 1.15], placements=[AssetInstance() for _ in range(1)])
office_printer_A = Assets(description="A square and round stand mixer sitting side by side.", size=[0.45, 0.50, 0.35], placements=[AssetInstance() for _ in range(1)])
coat_stand_A = Assets(description="The coatrack is wooden with a round bottom.", size=[0.50, 0.50, 1.75], placements=[AssetInstance() for _ in range(1)])
pen_cup_B = Assets(description="A cylindrical gray cup with two pens and a pencil sticking out.", size=[0.09, 0.09, 0.20], placements=[AssetInstance() for _ in range(1)])
side_occasion_table_B = Assets(description="side occasion table", size=[0.60, 0.60, 0.50], placements=[AssetInstance() for _ in range(1)])
lockers_bank = Assets(description="green metal lockers.", size=[0.50, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
side_occasion_table_C = Assets(description="side occasion table", size=[0.60, 0.60, 0.50], placements=[AssetInstance() for _ in range(1)])
printer_side_table_A = Assets(description="printer side table", size=[0.60, 0.80, 0.72], placements=[AssetInstance() for _ in range(1)])
task_chair_C = Assets(description="An office chair with a tall back and cushioning on the seat and backrest. it has wheels on the bottom.", size=[0.65, 0.65, 1.15], placements=[AssetInstance() for _ in range(1)])
high_stool_B = Assets(description="high stool", size=[0.45, 0.45, 0.78], placements=[AssetInstance() for _ in range(1)])
high_stool_C = Assets(description="high stool", size=[0.45, 0.45, 0.78], placements=[AssetInstance() for _ in range(1)])
mobile_pedestal_A = Assets(description="A wooden nightstand with both its drawers open.", size=[0.55, 0.42, 0.60], placements=[AssetInstance() for _ in range(1)])
mobile_pedestal_B = Assets(description="A wooden nightstand with both its drawers open.", size=[0.55, 0.42, 0.60], placements=[AssetInstance() for _ in range(1)])
coat_stand_B = Assets(description="The coatrack is wooden with a round bottom.", size=[0.50, 0.50, 1.75], placements=[AssetInstance() for _ in range(1)])
desk_organizer_A = Assets(description="yellow file folder with a smiley face on it.", size=[0.18, 0.25, 0.22], placements=[AssetInstance() for _ in range(1)])
counter_stool_A = Assets(description="A stool with a metal leg and foot rest with a round black cushion.", size=[0.42, 0.42, 0.68], placements=[AssetInstance() for _ in range(1)])
magazine_C = Assets(description="A light brown hardback book with atom depicted in gold on the cover.", size=[0.27, 0.20, 0.03], placements=[AssetInstance() for _ in range(1)])
floor_lamp_A = Assets(description="A floor lamp with a black base and white lampshade.", size=[0.45, 0.45, 1.65], placements=[AssetInstance() for _ in range(1)])
notepad_stack_A = Assets(description="A box of kleenix wipes.", size=[0.12, 0.23, 0.09], placements=[AssetInstance() for _ in range(1)])
high_stool_D = Assets(description="high stool", size=[0.45, 0.45, 0.78], placements=[AssetInstance() for _ in range(1)])
file_tray_B = Assets(description="yellow file folder with a smiley face on it.", size=[0.34, 0.26, 0.06], placements=[AssetInstance() for _ in range(1)])
wayfinding_sign_A = Assets(description="a Korean street sign with Korean writing, suitable for a restaurant setting.", size=[0.04, 0.65, 0.25], placements=[AssetInstance() for _ in range(1)])
office_monitor_A = Assets(description="A computer monitor with a black base.", size=[0.22, 0.61, 0.45], placements=[AssetInstance() for _ in range(1)])
sofa_modular = Assets(description="A light grey sofa with seating for four.", size=[0.90, 2.80, 0.82], placements=[AssetInstance() for _ in range(1)])
desk_side_cabinet_A = Assets(description="desk side cabinet", size=[0.45, 0.90, 0.72], placements=[AssetInstance() for _ in range(1)])
high_stool_E = Assets(description="high stool", size=[0.45, 0.45, 0.78], placements=[AssetInstance() for _ in range(1)])
low_storage_cabinet_B = Assets(description="White six draw wood cabinets with metal legs.", size=[0.45, 1.50, 0.75], placements=[AssetInstance() for _ in range(1)])
desk_organizer_B = Assets(description="yellow file folder with a smiley face on it.", size=[0.18, 0.25, 0.22], placements=[AssetInstance() for _ in range(1)])
standing_meeting_table_A = Assets(description="A round all brown kitchen table.", size=[1.00, 1.00, 1.05], placements=[AssetInstance() for _ in range(1)])
high_stool_F = Assets(description="high stool", size=[0.45, 0.45, 0.78], placements=[AssetInstance() for _ in range(1)])
keyboard_and_mouse_set = Assets(description="Gray monitor with a red screen computer and with a keyboard and mouse.", size=[0.25, 0.65, 0.04], placements=[AssetInstance() for _ in range(1)])
printer_side_table_B = Assets(description="printer side table", size=[0.60, 0.80, 0.72], placements=[AssetInstance() for _ in range(1)])
framed_photo_A = Assets(description="A blue painting in a black frame.", size=[0.08, 0.25, 0.30], placements=[AssetInstance() for _ in range(1)])
office_monitor_B = Assets(description="A computer monitor with a black base.", size=[0.22, 0.61, 0.45], placements=[AssetInstance() for _ in range(1)])
desk_side_cabinet_B = Assets(description="desk side cabinet", size=[0.45, 0.90, 0.72], placements=[AssetInstance() for _ in range(1)])
small_potted_plant_A = Assets(description="A bunch of big leaves inside of a white pot.", size=[0.35, 0.35, 0.50], placements=[AssetInstance() for _ in range(1)])
high_stool_G = Assets(description="high stool", size=[0.45, 0.45, 0.78], placements=[AssetInstance() for _ in range(1)])
team_table_A = Assets(description="A dark colored table with thin legs.", size=[0.90, 1.80, 1.05], placements=[AssetInstance() for _ in range(1)])
work_bench_desk_B = Assets(description="A long table with two sides.", size=[1.40, 3.20, 0.75], placements=[AssetInstance() for _ in range(1)])
file_tray_C = Assets(description="yellow file folder with a smiley face on it.", size=[0.34, 0.26, 0.06], placements=[AssetInstance() for _ in range(1)])
task_chair_D = Assets(description="An office chair with a tall back and cushioning on the seat and backrest. it has wheels on the bottom.", size=[0.65, 0.65, 1.15], placements=[AssetInstance() for _ in range(1)])
desk_side_cabinet_C = Assets(description="desk side cabinet", size=[0.45, 0.90, 0.72], placements=[AssetInstance() for _ in range(1)])
planter_box_A = Assets(description="A wooden planter with some strawberries.", size=[0.40, 1.20, 0.65], placements=[AssetInstance() for _ in range(1)])
small_potted_plant_B = Assets(description="A plant sitting in a round flower pot.", size=[0.25, 0.25, 0.35], placements=[AssetInstance() for _ in range(1)])
small_potted_plant_C = Assets(description="A plant sitting in a round flower pot.", size=[0.25, 0.25, 0.35], placements=[AssetInstance() for _ in range(1)])
counter_stool_B = Assets(description="A stool with a metal leg and foot rest with a round black cushion.", size=[0.42, 0.42, 0.68], placements=[AssetInstance() for _ in range(1)])
magazine_D = Assets(description="a notebook with stickers and a Pokémon drawing on it.", size=[0.30, 0.21, 0.02], placements=[AssetInstance() for _ in range(1)])
coat_stand_C = Assets(description="The coatrack is wooden with a round bottom.", size=[0.50, 0.50, 1.75], placements=[AssetInstance() for _ in range(1)])
low_storage_cabinet_C = Assets(description="White six draw wood cabinets with metal legs.", size=[0.45, 1.50, 0.75], placements=[AssetInstance() for _ in range(1)])
framed_photo_B = Assets(description="A blue painting in a black frame.", size=[0.08, 0.25, 0.30], placements=[AssetInstance() for _ in range(1)])
office_printer_B = Assets(description="A square and round stand mixer sitting side by side.", size=[0.45, 0.50, 0.35], placements=[AssetInstance() for _ in range(1)])
work_bench_desk_C = Assets(description="A long table with two sides.", size=[1.40, 3.20, 0.75], placements=[AssetInstance() for _ in range(1)])
standing_meeting_table_B = Assets(description="A round all brown kitchen table.", size=[1.00, 1.00, 1.05], placements=[AssetInstance() for _ in range(1)])
team_table_B = Assets(description="A dark colored table with thin legs.", size=[0.90, 1.80, 1.05], placements=[AssetInstance() for _ in range(1)])
magazine_E = Assets(description="a notebook with stickers and a Pokémon drawing on it.", size=[0.30, 0.21, 0.02], placements=[AssetInstance() for _ in range(1)])
task_chair_E = Assets(description="An office chair with a tall back and cushioning on the seat and backrest. it has wheels on the bottom.", size=[0.65, 0.65, 1.15], placements=[AssetInstance() for _ in range(1)])
wayfinding_sign_B = Assets(description="a Korean street sign with Korean writing, suitable for a restaurant setting.", size=[0.04, 0.65, 0.25], placements=[AssetInstance() for _ in range(1)])
desk_organizer_C = Assets(description="yellow file folder with a smiley face on it.", size=[0.18, 0.25, 0.22], placements=[AssetInstance() for _ in range(1)])
high_stool_H = Assets(description="high stool", size=[0.45, 0.45, 0.78], placements=[AssetInstance() for _ in range(1)])
high_stool_I = Assets(description="high stool", size=[0.45, 0.45, 0.78], placements=[AssetInstance() for _ in range(1)])
wayfinding_sign_C = Assets(description="a Korean street sign with Korean writing, suitable for a restaurant setting.", size=[0.04, 0.65, 0.25], placements=[AssetInstance() for _ in range(1)])
low_storage_cabinet_D = Assets(description="White six draw wood cabinets with metal legs.", size=[0.45, 1.50, 0.75], placements=[AssetInstance() for _ in range(1)])
framed_photo_C = Assets(description="A portrait sketch of a president.", size=[0.08, 0.24, 0.30], placements=[AssetInstance() for _ in range(1)])
desk_side_cabinet_D = Assets(description="desk side cabinet", size=[0.45, 0.90, 0.72], placements=[AssetInstance() for _ in range(1)])
planter_box_B = Assets(description="A wooden planter with some strawberries.", size=[0.40, 1.20, 0.65], placements=[AssetInstance() for _ in range(1)])
wayfinding_sign_D = Assets(description="a Korean street sign with Korean writing, suitable for a restaurant setting.", size=[0.04, 0.65, 0.25], placements=[AssetInstance() for _ in range(1)])
file_tray_D = Assets(description="A brown leather card holder with a logo on it.", size=[0.08, 0.12, 0.05], placements=[AssetInstance() for _ in range(1)])
file_tray_E = Assets(description="A brown leather card holder with a logo on it.", size=[0.08, 0.12, 0.05], placements=[AssetInstance() for _ in range(1)])
notepad_stack_B = Assets(description="A box of kleenix wipes.", size=[0.12, 0.23, 0.09], placements=[AssetInstance() for _ in range(1)])
framed_photo_D = Assets(description="A blue painting in a black frame.", size=[0.08, 0.25, 0.30], placements=[AssetInstance() for _ in range(1)])
mobile_pedestal_C = Assets(description="A wooden nightstand with both its drawers open.", size=[0.55, 0.42, 0.60], placements=[AssetInstance() for _ in range(1)])
task_chair_F = Assets(description="An office chair with a tall back and cushioning on the seat and backrest. it has wheels on the bottom.", size=[0.65, 0.65, 1.15], placements=[AssetInstance() for _ in range(1)])
standing_meeting_table_C = Assets(description="A round all brown kitchen table.", size=[1.00, 1.00, 1.05], placements=[AssetInstance() for _ in range(1)])
notepad_stack_C = Assets(description="A box of kleenix wipes.", size=[0.12, 0.23, 0.09], placements=[AssetInstance() for _ in range(1)])
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

low_storage_cabinet_A[0].position = [2.810832597845839, 3.5233428107154805, 0.375]
low_storage_cabinet_A[0].rotation = [0, 0, 0]
task_chair_A[0].position = [8.31996054500041, 3.5685152409947962, 0.575]
task_chair_A[0].rotation = [0, 0, 0]
magazine_A[0].position = [8.712822902783468, 8.93228791089982, 0.01]
magazine_A[0].rotation = [0, 0, 0]
pen_cup_A[0].position = [16.047352255657618, 3.7427178109554524, 0.1]
pen_cup_A[0].rotation = [0, 0, 0]
high_stool_A[0].position = [3.801934651678274, 6.921701660135416, 0.39]
high_stool_A[0].rotation = [0, 0, 0]
magazine_B[0].position = [14.637205116510788, 7.869568565351984, 0.015]
magazine_B[0].rotation = [0, 0, 0]
work_bench_desk_A[0].position = [2.294799947400291, 1.003828158519648, 0.375]
work_bench_desk_A[0].rotation = [0, 0, 0]
side_occasion_table_A[0].position = [11.625768978118415, 2.154904579956969, 0.25]
side_occasion_table_A[0].rotation = [0, 0, 0]
file_tray_A[0].position = [7.477344341153642, 10.81197790568039, 0.03]
file_tray_A[0].rotation = [0, 0, 0]
task_chair_B[0].position = [9.92007868343525, 5.43247250048624, 0.575]
task_chair_B[0].rotation = [0, 0, 0]
office_printer_A[0].position = [6.992933252667099, 9.360546017399347, 0.175]
office_printer_A[0].rotation = [0, 0, 0]
coat_stand_A[0].position = [11.82999648723043, 3.7166433998540294, 0.875]
coat_stand_A[0].rotation = [0, 0, 0]
pen_cup_B[0].position = [4.073692937890293, 2.644527909945935, 0.1]
pen_cup_B[0].rotation = [0, 0, 0]
side_occasion_table_B[0].position = [6.685167384200493, 0.9145492970409741, 0.25]
side_occasion_table_B[0].rotation = [0, 0, 0]
lockers_bank[0].position = [12.83629637989173, 9.988254459451285, 0.9]
lockers_bank[0].rotation = [0, 0, 0]
side_occasion_table_C[0].position = [10.702800757913458, 2.615212026620472, 0.25]
side_occasion_table_C[0].rotation = [0, 0, 0]
printer_side_table_A[0].position = [12.41946580688897, 10.899423575898632, 0.36]
printer_side_table_A[0].rotation = [0, 0, 0]
task_chair_C[0].position = [6.443209748950514, 10.491943806138275, 0.575]
task_chair_C[0].rotation = [0, 0, 0]
high_stool_B[0].position = [2.4831053680207367, 8.726834976272967, 0.39]
high_stool_B[0].rotation = [0, 0, 0]
high_stool_C[0].position = [15.41474914732949, 5.656129860811834, 0.39]
high_stool_C[0].rotation = [0, 0, 0]
mobile_pedestal_A[0].position = [7.254536451174856, 1.8467752619606999, 0.3]
mobile_pedestal_A[0].rotation = [0, 0, 0]
mobile_pedestal_B[0].position = [5.484155143666074, 2.6870402140808753, 0.3]
mobile_pedestal_B[0].rotation = [0, 0, 0]
coat_stand_B[0].position = [7.145745463584397, 0.43488203079321797, 0.875]
coat_stand_B[0].rotation = [0, 0, 0]
desk_organizer_A[0].position = [4.693392257529341, 3.1978300200293646, 0.11]
desk_organizer_A[0].rotation = [0, 0, 0]
counter_stool_A[0].position = [7.131224657945234, 7.923678164942756, 0.34]
counter_stool_A[0].rotation = [0, 0, 0]
magazine_C[0].position = [1.3913489700661932, 4.337654009797814, 0.015]
magazine_C[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [14.716936211750347, 3.3484450954633003, 0.825]
floor_lamp_A[0].rotation = [0, 0, 0]
notepad_stack_A[0].position = [3.6992525689716125, 6.8864417103011535, 0.045]
notepad_stack_A[0].rotation = [0, 0, 0]
high_stool_D[0].position = [3.9974412893913946, 8.45356531475526, 0.39]
high_stool_D[0].rotation = [0, 0, 0]
file_tray_B[0].position = [14.446613767724594, 1.8830756501009804, 0.03]
file_tray_B[0].rotation = [0, 0, 0]
wayfinding_sign_A[0].position = [14.523988470334782, 7.989311208210284, 0.125]
wayfinding_sign_A[0].rotation = [0, 0, 0]
office_monitor_A[0].position = [5.163183470815312, 1.5131313405259894, 0.225]
office_monitor_A[0].rotation = [0, 0, 0]
sofa_modular[0].position = [9.850078282815234, 2.717457159626669, 0.41]
sofa_modular[0].rotation = [0, 0, 0]
desk_side_cabinet_A[0].position = [16.955287477663916, 7.568583279925829, 0.36]
desk_side_cabinet_A[0].rotation = [0, 0, 0]
high_stool_E[0].position = [4.012354091497778, 10.571137400918722, 0.39]
high_stool_E[0].rotation = [0, 0, 0]
low_storage_cabinet_B[0].position = [12.054226759666518, 6.721940958182911, 0.375]
low_storage_cabinet_B[0].rotation = [0, 0, 0]
desk_organizer_B[0].position = [1.8659182816180127, 5.472340780956625, 0.11]
desk_organizer_B[0].rotation = [0, 0, 0]
standing_meeting_table_A[0].position = [4.594711186651112, 9.709402906141259, 0.525]
standing_meeting_table_A[0].rotation = [0, 0, 0]
high_stool_F[0].position = [2.836392190531477, 1.970138091622101, 0.39]
high_stool_F[0].rotation = [0, 0, 0]
keyboard_and_mouse_set[0].position = [13.849264334518185, 0.987930498315894, 0.02]
keyboard_and_mouse_set[0].rotation = [0, 0, 0]
printer_side_table_B[0].position = [4.725603233816323, 0.7255770305168777, 0.36]
printer_side_table_B[0].rotation = [0, 0, 0]
framed_photo_A[0].position = [13.116940982394551, 3.6529878304312744, 0.15]
framed_photo_A[0].rotation = [0, 0, 0]
office_monitor_B[0].position = [8.352701191233558, 3.9967382244180696, 0.225]
office_monitor_B[0].rotation = [0, 0, 0]
desk_side_cabinet_B[0].position = [0.8976146701863882, 3.3859208919081545, 0.36]
desk_side_cabinet_B[0].rotation = [0, 0, 0]
small_potted_plant_A[0].position = [5.851746688842297, 10.953209854518903, 0.25]
small_potted_plant_A[0].rotation = [0, 0, 0]
high_stool_G[0].position = [8.423603524724397, 6.00102947689512, 0.39]
high_stool_G[0].rotation = [0, 0, 0]
team_table_A[0].position = [11.56155212289385, 7.8264627066706485, 0.525]
team_table_A[0].rotation = [0, 0, 0]
work_bench_desk_B[0].position = [13.037016932226594, 7.901100396113325, 0.375]
work_bench_desk_B[0].rotation = [0, 0, 0]
file_tray_C[0].position = [4.423739852010711, 10.039173121551121, 0.03]
file_tray_C[0].rotation = [0, 0, 0]
task_chair_D[0].position = [6.4212548230741, 6.512390052759018, 0.575]
task_chair_D[0].rotation = [0, 0, 0]
desk_side_cabinet_C[0].position = [16.832032468503687, 2.346725908708639, 0.36]
desk_side_cabinet_C[0].rotation = [0, 0, 0]
planter_box_A[0].position = [16.473335536139736, 1.220371692352889, 0.325]
planter_box_A[0].rotation = [0, 0, 0]
small_potted_plant_B[0].position = [1.1965865156872286, 4.351866871808936, 0.175]
small_potted_plant_B[0].rotation = [0, 0, 0]
small_potted_plant_C[0].position = [4.287452731058883, 3.6384966346068692, 0.175]
small_potted_plant_C[0].rotation = [0, 0, 0]
counter_stool_B[0].position = [6.870790392006823, 3.648723404211621, 0.34]
counter_stool_B[0].rotation = [0, 0, 0]
magazine_D[0].position = [9.088063497546852, 8.24933784081832, 0.01]
magazine_D[0].rotation = [0, 0, 0]
coat_stand_C[0].position = [2.5803672487188845, 10.376003059867289, 0.875]
coat_stand_C[0].rotation = [0, 0, 0]
low_storage_cabinet_C[0].position = [0.2634738391450605, 5.373812269147638, 0.375]
low_storage_cabinet_C[0].rotation = [0, 0, 0]
framed_photo_B[0].position = [11.435430285887705, 9.031992766851639, 0.15]
framed_photo_B[0].rotation = [0, 0, 0]
office_printer_B[0].position = [13.082354969013545, 3.555635071392572, 0.175]
office_printer_B[0].rotation = [0, 0, 0]
work_bench_desk_C[0].position = [11.141575918717031, 10.714822332144198, 0.375]
work_bench_desk_C[0].rotation = [0, 0, 0]
standing_meeting_table_B[0].position = [12.761153179270321, 5.8789663461756, 0.525]
standing_meeting_table_B[0].rotation = [0, 0, 0]
team_table_B[0].position = [9.036082305737686, 7.5974632630784535, 0.525]
team_table_B[0].rotation = [0, 0, 0]
magazine_E[0].position = [6.123430496292272, 9.089615469340355, 0.01]
magazine_E[0].rotation = [0, 0, 0]
task_chair_E[0].position = [3.0516362665283556, 4.31256330004491, 0.575]
task_chair_E[0].rotation = [0, 0, 0]
wayfinding_sign_B[0].position = [16.82259797134688, 3.2667899432683125, 0.125]
wayfinding_sign_B[0].rotation = [0, 0, 0]
desk_organizer_C[0].position = [8.477167250587655, 10.363119331095476, 0.11]
desk_organizer_C[0].rotation = [0, 0, 0]
high_stool_H[0].position = [4.984140115682444, 0.23572266475200643, 0.39]
high_stool_H[0].rotation = [0, 0, 0]
high_stool_I[0].position = [5.647010220313807, 0.35106571842927725, 0.39]
high_stool_I[0].rotation = [0, 0, 0]
wayfinding_sign_C[0].position = [11.98078680774074, 1.305893067525909, 0.125]
wayfinding_sign_C[0].rotation = [0, 0, 0]
low_storage_cabinet_D[0].position = [14.968088695151586, 1.3218615877471118, 0.375]
low_storage_cabinet_D[0].rotation = [0, 0, 0]
framed_photo_C[0].position = [13.68970712226109, 5.927819725159889, 0.15]
framed_photo_C[0].rotation = [0, 0, 0]
desk_side_cabinet_D[0].position = [3.6762168719199653, 7.927897763243073, 0.36]
desk_side_cabinet_D[0].rotation = [0, 0, 0]
planter_box_B[0].position = [1.8365891989947696, 5.152391007176966, 0.325]
planter_box_B[0].rotation = [0, 0, 0]
wayfinding_sign_D[0].position = [5.287428133267189, 3.0618544428652044, 0.125]
wayfinding_sign_D[0].rotation = [0, 0, 0]
file_tray_D[0].position = [9.372867922373555, 8.636370216726453, 0.025]
file_tray_D[0].rotation = [0, 0, 0]
file_tray_E[0].position = [9.106019920110025, 4.891597384371412, 0.025]
file_tray_E[0].rotation = [0, 0, 0]
notepad_stack_B[0].position = [9.11053457917606, 6.760597763929782, 0.045]
notepad_stack_B[0].rotation = [0, 0, 0]
framed_photo_D[0].position = [10.827895082912837, 7.755208219811, 0.15]
framed_photo_D[0].rotation = [0, 0, 0]
mobile_pedestal_C[0].position = [5.81260372452161, 9.134319625950809, 0.3]
mobile_pedestal_C[0].rotation = [0, 0, 0]
task_chair_F[0].position = [5.495500975456996, 1.6381097328068837, 0.575]
task_chair_F[0].rotation = [0, 0, 0]
standing_meeting_table_C[0].position = [12.18964754409924, 4.67509933615593, 0.525]
standing_meeting_table_C[0].rotation = [0, 0, 0]
notepad_stack_C[0].position = [9.897543489729, 6.686513238183015, 0.045]
notepad_stack_C[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [15.450194811082259, 5.523365486359628, 0.825]
floor_lamp_B[0].rotation = [0, 0, 0]
low_storage_cabinet_A[0].position = [2.810832597845839, 3.5233428107154805, 0.375]
low_storage_cabinet_A[0].rotation = [0, 0, 0]
task_chair_A[0].position = [8.31996054500041, 3.5685152409947962, 0.575]
task_chair_A[0].rotation = [0, 0, 0]
magazine_A[0].position = [8.712822902783468, 8.93228791089982, 0.01]
magazine_A[0].rotation = [0, 0, 0]
pen_cup_A[0].position = [16.047352255657618, 3.7427178109554524, 0.1]
pen_cup_A[0].rotation = [0, 0, 0]
high_stool_A[0].position = [3.801934651678274, 6.921701660135416, 0.39]
high_stool_A[0].rotation = [0, 0, 0]
magazine_B[0].position = [14.637205116510788, 7.869568565351984, 0.015]
magazine_B[0].rotation = [0, 0, 0]
work_bench_desk_A[0].position = [2.294799947400291, 1.003828158519648, 0.375]
work_bench_desk_A[0].rotation = [0, 0, 0]
side_occasion_table_A[0].position = [11.625768978118415, 2.154904579956969, 0.25]
side_occasion_table_A[0].rotation = [0, 0, 0]
file_tray_A[0].position = [7.477344341153642, 10.81197790568039, 0.03]
file_tray_A[0].rotation = [0, 0, 0]
task_chair_B[0].position = [9.92007868343525, 5.43247250048624, 0.575]
task_chair_B[0].rotation = [0, 0, 0]
office_printer_A[0].position = [6.992933252667099, 9.360546017399347, 0.175]
office_printer_A[0].rotation = [0, 0, 0]
coat_stand_A[0].position = [11.82999648723043, 3.7166433998540294, 0.875]
coat_stand_A[0].rotation = [0, 0, 0]
pen_cup_B[0].position = [4.073692937890293, 2.644527909945935, 0.1]
pen_cup_B[0].rotation = [0, 0, 0]
side_occasion_table_B[0].position = [6.685167384200493, 0.9145492970409741, 0.25]
side_occasion_table_B[0].rotation = [0, 0, 0]
lockers_bank[0].position = [12.83629637989173, 9.988254459451285, 0.9]
lockers_bank[0].rotation = [0, 0, 0]
side_occasion_table_C[0].position = [10.702800757913458, 2.615212026620472, 0.25]
side_occasion_table_C[0].rotation = [0, 0, 0]
printer_side_table_A[0].position = [12.41946580688897, 10.899423575898632, 0.36]
printer_side_table_A[0].rotation = [0, 0, 0]
task_chair_C[0].position = [6.443209748950514, 10.491943806138275, 0.575]
task_chair_C[0].rotation = [0, 0, 0]
high_stool_B[0].position = [2.4831053680207367, 8.726834976272967, 0.39]
high_stool_B[0].rotation = [0, 0, 0]
high_stool_C[0].position = [15.41474914732949, 5.656129860811834, 0.39]
high_stool_C[0].rotation = [0, 0, 0]
mobile_pedestal_A[0].position = [7.254536451174856, 1.8467752619606999, 0.3]
mobile_pedestal_A[0].rotation = [0, 0, 0]
mobile_pedestal_B[0].position = [5.484155143666074, 2.6870402140808753, 0.3]
mobile_pedestal_B[0].rotation = [0, 0, 0]
coat_stand_B[0].position = [7.145745463584397, 0.43488203079321797, 0.875]
coat_stand_B[0].rotation = [0, 0, 0]
desk_organizer_A[0].position = [4.693392257529341, 3.1978300200293646, 0.11]
desk_organizer_A[0].rotation = [0, 0, 0]
counter_stool_A[0].position = [7.131224657945234, 7.923678164942756, 0.34]
counter_stool_A[0].rotation = [0, 0, 0]
magazine_C[0].position = [1.3913489700661932, 4.337654009797814, 0.015]
magazine_C[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [14.716936211750347, 3.3484450954633003, 0.825]
floor_lamp_A[0].rotation = [0, 0, 0]
notepad_stack_A[0].position = [3.6992525689716125, 6.8864417103011535, 0.045]
notepad_stack_A[0].rotation = [0, 0, 0]
high_stool_D[0].position = [3.9974412893913946, 8.45356531475526, 0.39]
high_stool_D[0].rotation = [0, 0, 0]
file_tray_B[0].position = [14.446613767724594, 1.8830756501009804, 0.03]
file_tray_B[0].rotation = [0, 0, 0]
wayfinding_sign_A[0].position = [14.523988470334782, 7.989311208210284, 0.125]
wayfinding_sign_A[0].rotation = [0, 0, 0]
office_monitor_A[0].position = [5.163183470815312, 1.5131313405259894, 0.225]
office_monitor_A[0].rotation = [0, 0, 0]
sofa_modular[0].position = [9.850078282815234, 2.717457159626669, 0.41]
sofa_modular[0].rotation = [0, 0, 0]
desk_side_cabinet_A[0].position = [16.955287477663916, 7.568583279925829, 0.36]
desk_side_cabinet_A[0].rotation = [0, 0, 0]
high_stool_E[0].position = [4.012354091497778, 10.571137400918722, 0.39]
high_stool_E[0].rotation = [0, 0, 0]
low_storage_cabinet_B[0].position = [12.054226759666518, 6.721940958182911, 0.375]
low_storage_cabinet_B[0].rotation = [0, 0, 0]
desk_organizer_B[0].position = [1.8659182816180127, 5.472340780956625, 0.11]
desk_organizer_B[0].rotation = [0, 0, 0]
standing_meeting_table_A[0].position = [4.594711186651112, 9.709402906141259, 0.525]
standing_meeting_table_A[0].rotation = [0, 0, 0]
high_stool_F[0].position = [2.836392190531477, 1.970138091622101, 0.39]
high_stool_F[0].rotation = [0, 0, 0]
keyboard_and_mouse_set[0].position = [13.849264334518185, 0.987930498315894, 0.02]
keyboard_and_mouse_set[0].rotation = [0, 0, 0]
printer_side_table_B[0].position = [4.725603233816323, 0.7255770305168777, 0.36]
printer_side_table_B[0].rotation = [0, 0, 0]
framed_photo_A[0].position = [13.116940982394551, 3.6529878304312744, 0.15]
framed_photo_A[0].rotation = [0, 0, 0]
office_monitor_B[0].position = [8.352701191233558, 3.9967382244180696, 0.225]
office_monitor_B[0].rotation = [0, 0, 0]
desk_side_cabinet_B[0].position = [0.8976146701863882, 3.3859208919081545, 0.36]
desk_side_cabinet_B[0].rotation = [0, 0, 0]
small_potted_plant_A[0].position = [5.851746688842297, 10.953209854518903, 0.25]
small_potted_plant_A[0].rotation = [0, 0, 0]
high_stool_G[0].position = [8.423603524724397, 6.00102947689512, 0.39]
high_stool_G[0].rotation = [0, 0, 0]
team_table_A[0].position = [11.56155212289385, 7.8264627066706485, 0.525]
team_table_A[0].rotation = [0, 0, 0]
work_bench_desk_B[0].position = [13.037016932226594, 7.901100396113325, 0.375]
work_bench_desk_B[0].rotation = [0, 0, 0]
file_tray_C[0].position = [4.423739852010711, 10.039173121551121, 0.03]
file_tray_C[0].rotation = [0, 0, 0]
task_chair_D[0].position = [6.4212548230741, 6.512390052759018, 0.575]
task_chair_D[0].rotation = [0, 0, 0]
desk_side_cabinet_C[0].position = [16.832032468503687, 2.346725908708639, 0.36]
desk_side_cabinet_C[0].rotation = [0, 0, 0]
planter_box_A[0].position = [16.473335536139736, 1.220371692352889, 0.325]
planter_box_A[0].rotation = [0, 0, 0]
small_potted_plant_B[0].position = [1.1965865156872286, 4.351866871808936, 0.175]
small_potted_plant_B[0].rotation = [0, 0, 0]
small_potted_plant_C[0].position = [4.287452731058883, 3.6384966346068692, 0.175]
small_potted_plant_C[0].rotation = [0, 0, 0]
counter_stool_B[0].position = [6.870790392006823, 3.648723404211621, 0.34]
counter_stool_B[0].rotation = [0, 0, 0]
magazine_D[0].position = [9.088063497546852, 8.24933784081832, 0.01]
magazine_D[0].rotation = [0, 0, 0]
coat_stand_C[0].position = [2.5803672487188845, 10.376003059867289, 0.875]
coat_stand_C[0].rotation = [0, 0, 0]
low_storage_cabinet_C[0].position = [0.2634738391450605, 5.373812269147638, 0.375]
low_storage_cabinet_C[0].rotation = [0, 0, 0]
framed_photo_B[0].position = [11.435430285887705, 9.031992766851639, 0.15]
framed_photo_B[0].rotation = [0, 0, 0]
office_printer_B[0].position = [13.082354969013545, 3.555635071392572, 0.175]
office_printer_B[0].rotation = [0, 0, 0]
work_bench_desk_C[0].position = [11.141575918717031, 10.714822332144198, 0.375]
work_bench_desk_C[0].rotation = [0, 0, 0]
standing_meeting_table_B[0].position = [12.761153179270321, 5.8789663461756, 0.525]
standing_meeting_table_B[0].rotation = [0, 0, 0]
team_table_B[0].position = [9.036082305737686, 7.5974632630784535, 0.525]
team_table_B[0].rotation = [0, 0, 0]
magazine_E[0].position = [6.123430496292272, 9.089615469340355, 0.01]
magazine_E[0].rotation = [0, 0, 0]
task_chair_E[0].position = [3.0516362665283556, 4.31256330004491, 0.575]
task_chair_E[0].rotation = [0, 0, 0]
wayfinding_sign_B[0].position = [16.82259797134688, 3.2667899432683125, 0.125]
wayfinding_sign_B[0].rotation = [0, 0, 0]
desk_organizer_C[0].position = [8.477167250587655, 10.363119331095476, 0.11]
desk_organizer_C[0].rotation = [0, 0, 0]
high_stool_H[0].position = [4.984140115682444, 0.23572266475200643, 0.39]
high_stool_H[0].rotation = [0, 0, 0]
high_stool_I[0].position = [5.647010220313807, 0.35106571842927725, 0.39]
high_stool_I[0].rotation = [0, 0, 0]
wayfinding_sign_C[0].position = [11.98078680774074, 1.305893067525909, 0.125]
wayfinding_sign_C[0].rotation = [0, 0, 0]
low_storage_cabinet_D[0].position = [14.968088695151586, 1.3218615877471118, 0.375]
low_storage_cabinet_D[0].rotation = [0, 0, 0]
framed_photo_C[0].position = [13.68970712226109, 5.927819725159889, 0.15]
framed_photo_C[0].rotation = [0, 0, 0]
desk_side_cabinet_D[0].position = [3.6762168719199653, 7.927897763243073, 0.36]
desk_side_cabinet_D[0].rotation = [0, 0, 0]
planter_box_B[0].position = [1.8365891989947696, 5.152391007176966, 0.325]
planter_box_B[0].rotation = [0, 0, 0]
wayfinding_sign_D[0].position = [5.287428133267189, 3.0618544428652044, 0.125]
wayfinding_sign_D[0].rotation = [0, 0, 0]
file_tray_D[0].position = [9.372867922373555, 8.636370216726453, 0.025]
file_tray_D[0].rotation = [0, 0, 0]
file_tray_E[0].position = [9.106019920110025, 4.891597384371412, 0.025]
file_tray_E[0].rotation = [0, 0, 0]
notepad_stack_B[0].position = [9.11053457917606, 6.760597763929782, 0.045]
notepad_stack_B[0].rotation = [0, 0, 0]
framed_photo_D[0].position = [10.827895082912837, 7.755208219811, 0.15]
framed_photo_D[0].rotation = [0, 0, 0]
mobile_pedestal_C[0].position = [5.81260372452161, 9.134319625950809, 0.3]
mobile_pedestal_C[0].rotation = [0, 0, 0]
task_chair_F[0].position = [5.495500975456996, 1.6381097328068837, 0.575]
task_chair_F[0].rotation = [0, 0, 0]
standing_meeting_table_C[0].position = [12.18964754409924, 4.67509933615593, 0.525]
standing_meeting_table_C[0].rotation = [0, 0, 0]
notepad_stack_C[0].position = [9.897543489729, 6.686513238183015, 0.045]
notepad_stack_C[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [15.450194811082259, 5.523365486359628, 0.825]
floor_lamp_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Coordinates follow the supplied boundary, rather than recentering the room.
# Preserve clear entry aprons and use the central area for three work benches.
# Each record retains an independent fixed pose reference for the constraints.
layout_records = []

def place_floor(asset_group, x, y, yaw=0):
    instance = asset_group[0]
    instance.position = [x, y, asset_group.size[2] / 2]
    instance.rotation = [0, 0, radians(yaw)]
    layout_records.append((asset_group, instance))

def place_on(asset_group, support_group, x, y, yaw=0):
    instance = asset_group[0]
    support = support_group[0]
    surface_z = support.position[2] + support_group.size[2] / 2
    instance.position = [x, y, surface_z + asset_group.size[2] / 2]
    instance.rotation = [0, 0, radians(yaw)]
    solver.on_top_of(instance, support)
    layout_records.append((asset_group, instance))


# Work benches: their long axes run north–south, with chairs outside
# the tabletop footprints and a circulation aisle between workstations.
place_floor(work_bench_desk_A, 5.0, 4.8)
place_floor(work_bench_desk_B, 8.0, 4.8)
place_floor(work_bench_desk_C, 11.0, 4.8)

place_floor(task_chair_A, 3.8, 4.4, 0)
place_floor(task_chair_B, 6.2, 5.2, 180)
place_floor(task_chair_C, 6.8, 4.4, 0)
place_floor(task_chair_D, 9.2, 5.2, 180)
place_floor(task_chair_E, 9.8, 4.4, 0)
place_floor(task_chair_F, 12.2, 5.2, 180)

place_floor(mobile_pedestal_A, 5.0, 2.5, 180)
place_floor(mobile_pedestal_B, 8.0, 2.5, 180)
place_floor(mobile_pedestal_C, 11.0, 7.0, 180)

# North-side collaboration area; leave both northern doors unobstructed.
place_floor(team_table_A, 4.5, 8.8)
place_floor(high_stool_C, 3.6, 8.8, 0)
place_floor(high_stool_D, 5.4, 8.8, 180)

place_floor(team_table_B, 9.0, 8.8)
place_floor(high_stool_A, 8.1, 8.8, 0)
place_floor(high_stool_B, 9.9, 8.8, 180)

# Informal standing meetings occupy the eastern and southern open areas.
place_floor(standing_meeting_table_A, 14.6, 3.0)
place_floor(high_stool_E, 14.6, 2.1, 90)
place_floor(high_stool_F, 14.6, 3.9, -90)

place_floor(standing_meeting_table_B, 14.6, 6.0)
place_floor(high_stool_G, 14.6, 5.1, 90)
place_floor(high_stool_H, 14.6, 6.9, -90)

place_floor(standing_meeting_table_C, 10.0, 1.8)
place_floor(high_stool_I, 10.0, 2.7, -90)
place_floor(counter_stool_A, 9.1, 1.8, 0)
place_floor(counter_stool_B, 10.9, 1.8, 180)

# Storage uses solid wall segments, not door openings.
place_floor(low_storage_cabinet_A, 3.7, 10.775, -90)
place_floor(low_storage_cabinet_B, 5.4, 10.775, -90)
place_floor(low_storage_cabinet_C, 8.5, 10.775, -90)
place_floor(low_storage_cabinet_D, 10.3, 10.775, -90)
place_floor(lockers_bank, 2.25, 9.5, 0)

place_floor(desk_side_cabinet_A, 12.775, 9.6, 180)
place_floor(desk_side_cabinet_B, 4.0, 0.225, 90)
place_floor(desk_side_cabinet_C, 5.3, 0.225, 90)
place_floor(desk_side_cabinet_D, 6.6, 0.225, 90)

# Lounge and service furniture stay outside the workstation footprints.
place_floor(sofa_modular, 2.65, 4.4, 0)
place_floor(side_occasion_table_A, 2.7, 2.5)
place_floor(side_occasion_table_B, 3.1, 6.5)
place_floor(side_occasion_table_C, 12.5, 7.8)

place_floor(printer_side_table_A, 15.8, 1.5, 180)
place_floor(printer_side_table_B, 16.6, 7.2, 180)

place_floor(coat_stand_A, 0.6, 5.6)
place_floor(coat_stand_B, 3.0, 0.6)
place_floor(coat_stand_C, 12.6, 8.5)
place_floor(floor_lamp_A, 3.4, 5.9)
place_floor(floor_lamp_B, 12.4, 6.8)

# Low planting near the windows does not block the eastern entry.
# Planter A lies directly in front of bench A's +x-facing direction.
place_floor(planter_box_A, 16.8, 4.8, 180)
place_floor(planter_box_B, 16.8, 2.8, 180)

# Workstation accessories occupy distinct tabletop patches.
place_on(office_monitor_A, work_bench_desk_A, 5.15, 4.15, 180)
place_on(keyboard_and_mouse_set, work_bench_desk_A, 4.80, 4.15, 180)
place_on(pen_cup_A, work_bench_desk_A, 4.60, 3.50)
place_on(magazine_A, work_bench_desk_A, 5.15, 3.45)
place_on(file_tray_A, work_bench_desk_A, 5.15, 5.80)
place_on(notepad_stack_A, work_bench_desk_A, 4.65, 5.80)

place_on(office_monitor_B, work_bench_desk_B, 8.15, 4.15, 180)
place_on(pen_cup_B, work_bench_desk_B, 7.60, 3.50)
place_on(magazine_B, work_bench_desk_B, 8.15, 3.45)
place_on(file_tray_B, work_bench_desk_B, 8.15, 5.80)
place_on(desk_organizer_B, work_bench_desk_B, 7.60, 5.80)

place_on(magazine_C, work_bench_desk_C, 10.65, 3.50)
place_on(file_tray_C, work_bench_desk_C, 11.20, 3.50)
place_on(desk_organizer_C, work_bench_desk_C, 10.65, 5.85)
place_on(notepad_stack_B, work_bench_desk_C, 11.20, 5.85)

# The requested organizer/cabinet pairing uses organizer A and cabinet C.
place_on(desk_organizer_A, desk_side_cabinet_C, 5.3, 0.225, 90)

place_on(office_printer_A, printer_side_table_A, 15.8, 1.5, 180)
place_on(office_printer_B, printer_side_table_B, 16.6, 7.2, 180)

place_on(small_potted_plant_A, side_occasion_table_A, 2.7, 2.5)
place_on(small_potted_plant_B, side_occasion_table_B, 3.1, 6.5)
place_on(small_potted_plant_C, side_occasion_table_C, 12.5, 7.8)

place_on(magazine_D, team_table_A, 4.5, 8.40)
place_on(file_tray_D, team_table_A, 4.5, 9.15)
place_on(magazine_E, team_table_B, 9.0, 8.40)
place_on(file_tray_E, team_table_B, 9.0, 9.15)
place_on(notepad_stack_C, standing_meeting_table_C, 10.0, 1.8)

# Signs and framed pieces rest on cabinets, rather than floating or
# standing on the floor. Their separated patches avoid mutual overlap.
place_on(wayfinding_sign_A, low_storage_cabinet_A, 3.45, 10.775, -90)
place_on(framed_photo_A, low_storage_cabinet_A, 4.05, 10.775, -90)
place_on(wayfinding_sign_B, low_storage_cabinet_B, 5.15, 10.775, -90)
place_on(framed_photo_B, low_storage_cabinet_B, 5.75, 10.775, -90)
place_on(wayfinding_sign_C, low_storage_cabinet_C, 8.25, 10.775, -90)
place_on(framed_photo_C, low_storage_cabinet_C, 8.85, 10.775, -90)
place_on(wayfinding_sign_D, low_storage_cabinet_D, 10.05, 10.775, -90)
place_on(framed_photo_D, low_storage_cabinet_D, 10.65, 10.775, -90)


# Important semantic constraints precede pose-preservation constraints.
solver.against_wall(desk_side_cabinet_A[0], walls[11])
solver.point_towards(
    desk_side_cabinet_A[0],
    AssetInstance(position=[11.0, 9.6, 0.36])
)
solver.point_towards(work_bench_desk_A[0], planter_box_A[0])

# Team A is centered between the two specified opposing high stools.
for stool_group in (high_stool_C, high_stool_D):
    solver.point_towards(stool_group[0], team_table_A[0])
    separation = (
        0.9 ** 2
        + (team_table_A[0].position[2] - stool_group[0].position[2]) ** 2
    ) ** 0.5
    solver.distance_constraint(
        stool_group[0], team_table_A[0],
        separation, separation, weight=10
    )

# Seat orientation and distances remain tied to the relevant furniture.
seat_pairs = [
    (task_chair_A, work_bench_desk_A),
    (task_chair_B, work_bench_desk_A),
    (task_chair_C, work_bench_desk_B),
    (task_chair_D, work_bench_desk_B),
    (task_chair_E, work_bench_desk_C),
    (task_chair_F, work_bench_desk_C),
    (high_stool_A, team_table_B),
    (high_stool_B, team_table_B),
    (high_stool_E, standing_meeting_table_A),
    (high_stool_F, standing_meeting_table_A),
    (high_stool_G, standing_meeting_table_B),
    (high_stool_H, standing_meeting_table_B),
    (high_stool_I, standing_meeting_table_C),
    (counter_stool_A, standing_meeting_table_C),
    (counter_stool_B, standing_meeting_table_C),
]
for seat_group, table_group in seat_pairs:
    solver.point_towards(seat_group[0], table_group[0])
    center_distance = sum(
        (seat_group[0].position[k] - table_group[0].position[k]) ** 2
        for k in range(3)
    ) ** 0.5
    solver.distance_constraint(
        seat_group[0], table_group[0],
        center_distance, center_distance, weight=10
    )

for storage_group in (
    low_storage_cabinet_A, low_storage_cabinet_B,
    low_storage_cabinet_C, low_storage_cabinet_D,
):
    solver.against_wall(storage_group[0], walls[12])

solver.against_wall(lockers_bank[0], walls[13])
for cabinet_group in (
    desk_side_cabinet_B, desk_side_cabinet_C, desk_side_cabinet_D,
):
    solver.against_wall(cabinet_group[0], walls[4])

# Every new instance receives a position and orientation constraint.
# Exact pose references preserve the deliberately clear doorway aprons,
# non-overlapping footprints, and individual tabletop accessory patches.
# References are constraint-only fixed points, not additional scene assets.
for group_ref, instance_ref in layout_records:
    pose_reference = AssetInstance(
        position=list(instance_ref.position),
        rotation=list(instance_ref.rotation)
    )
    solver.distance_constraint(
        instance_ref, pose_reference, 0.0, 0.0, weight=10
    )
    solver.align_with(instance_ref, pose_reference)

solver.constraints = []
task_chair_D[0].position = [9.281657218933105, 5.281679630279541, 0.574999988079071]
task_chair_D[0].rotation = [0, 0, -3.125884689672577]
task_chair_D[0].optimize = 2
file_tray_B[0].position = [8.149999618530273, 5.800000190734863, 0.7799999713897705]
file_tray_B[0].rotation = [0, 0, 0.01256637125682779]
file_tray_B[0].optimize = 2
task_chair_C[0].position = [6.718343734741211, 4.318320274353027, 0.574999988079071]
task_chair_C[0].rotation = [0, 0, 0.0157079639172164]
task_chair_C[0].optimize = 2
high_stool_H[0].position = [14.600000381469727, 6.981660842895508, 0.38999998569488525]
high_stool_H[0].rotation = [0, 0, -1.5550883628776802]
high_stool_H[0].optimize = 2
standing_meeting_table_C[0].position = [10.0, 1.7999999523162842, 0.5249999761581421]
standing_meeting_table_C[0].rotation = [0, 0, 0.031415925765816845]
standing_meeting_table_C[0].optimize = 2
office_printer_B[0].position = [16.600000381469727, 7.199999809265137, 0.8950000405311584]
office_printer_B[0].rotation = [0, 0, -3.1290262823329655]
office_printer_B[0].optimize = 2
notepad_stack_B[0].position = [11.199999809265137, 5.849999904632568, 0.7950000166893005]
notepad_stack_B[0].rotation = [0, 0, 0.01256637125682779]
notepad_stack_B[0].optimize = 2
task_chair_F[0].position = [12.281657218933105, 5.281679630279541, 0.574999988079071]
task_chair_F[0].rotation = [0, 0, -3.125884689672577]
task_chair_F[0].optimize = 2
standing_meeting_table_A[0].position = [14.600000381469727, 3.0, 0.5249999761581421]
standing_meeting_table_A[0].rotation = [0, 0, 0.021991148286022624]
standing_meeting_table_A[0].optimize = 2
wayfinding_sign_C[0].position = [8.25, 10.774999618530273, 0.875]
wayfinding_sign_C[0].rotation = [0, 0, -1.5582299555380688]
wayfinding_sign_C[0].optimize = 2
framed_photo_A[0].position = [4.050000190734863, 10.774999618530273, 0.8999999761581421]
framed_photo_A[0].rotation = [0, 0, -1.5582299555380688]
framed_photo_A[0].optimize = 2
work_bench_desk_C[0].position = [11.0, 4.800000190734863, 0.375]
work_bench_desk_C[0].rotation = [0, 0, 0.03455751882667646]
work_bench_desk_C[0].optimize = 2
magazine_C[0].position = [10.649999618530273, 3.5, 0.7649999856948853]
magazine_C[0].rotation = [0, 0, 0.01256637125682779]
magazine_C[0].optimize = 2
notepad_stack_A[0].position = [4.650000095367432, 5.800000190734863, 0.7950000166893005]
notepad_stack_A[0].rotation = [0, 0, 0.01256637125682779]
notepad_stack_A[0].optimize = 2
small_potted_plant_C[0].position = [12.5, 7.800000190734863, 0.675000011920929]
small_potted_plant_C[0].rotation = [0, 0, 0.01256637125682779]
small_potted_plant_C[0].optimize = 2
desk_organizer_B[0].position = [7.599999904632568, 5.800000190734863, 0.8600000143051147]
desk_organizer_B[0].rotation = [0, 0, 0.01256637125682779]
desk_organizer_B[0].optimize = 2
high_stool_C[0].position = [3.5183398723602295, 8.800000190734863, 0.38999998569488525]
high_stool_C[0].rotation = [0, 0, 0.0157079639172164]
high_stool_C[0].optimize = 2
mobile_pedestal_A[0].position = [5.0, 2.5, 0.30000001192092896]
mobile_pedestal_A[0].rotation = [0, 0, -3.1321678761290697]
mobile_pedestal_A[0].optimize = 2
notepad_stack_C[0].position = [10.0, 1.7999999523162842, 1.09499990940094]
notepad_stack_C[0].rotation = [0, 0, 0.01256637125682779]
notepad_stack_C[0].optimize = 2
pen_cup_A[0].position = [4.599999904632568, 3.5, 0.8500000238418579]
pen_cup_A[0].rotation = [0, 0, 0.01256637125682779]
pen_cup_A[0].optimize = 2
work_bench_desk_A[0].position = [5.0, 4.800000190734863, 0.375]
work_bench_desk_A[0].rotation = [0, 0, 0.043982298440307294]
work_bench_desk_A[0].optimize = 2
coat_stand_C[0].position = [12.600000381469727, 8.5, 0.875]
coat_stand_C[0].rotation = [0, 0, 0.00942477746072377]
coat_stand_C[0].optimize = 2
desk_side_cabinet_B[0].position = [4.0, 0.2250683605670929, 0.36000001430511475]
desk_side_cabinet_B[0].rotation = [0, 0, 1.5707346457611155]
desk_side_cabinet_B[0].optimize = 2
floor_lamp_A[0].position = [3.4000000953674316, 5.900000095367432, 0.824999988079071]
floor_lamp_A[0].rotation = [0, 0, 0.00942477746072377]
floor_lamp_A[0].optimize = 2
magazine_D[0].position = [4.5, 8.399999618530273, 1.059999942779541]
magazine_D[0].rotation = [0, 0, 0.01256637125682779]
magazine_D[0].optimize = 2
lockers_bank[0].position = [2.25, 9.5, 0.8999999761581421]
lockers_bank[0].rotation = [0, 0, -6.061578791838757e-05]
lockers_bank[0].optimize = 2
printer_side_table_A[0].position = [15.800000190734863, 1.5, 0.36000001430511475]
printer_side_table_A[0].rotation = [0, 0, -3.1290262823329655]
printer_side_table_A[0].optimize = 2
mobile_pedestal_C[0].position = [11.0, 7.0, 0.30000001192092896]
mobile_pedestal_C[0].rotation = [0, 0, -3.1321678761290697]
mobile_pedestal_C[0].optimize = 2
wayfinding_sign_A[0].position = [3.450000047683716, 10.774999618530273, 0.875]
wayfinding_sign_A[0].rotation = [0, 0, -1.5582299555380688]
wayfinding_sign_A[0].optimize = 2
high_stool_F[0].position = [14.600000381469727, 3.9816601276397705, 0.38999998569488525]
high_stool_F[0].rotation = [0, 0, -1.5550883628776802]
high_stool_F[0].optimize = 2
team_table_B[0].position = [9.0, 8.800000190734863, 0.5249999761581421]
team_table_B[0].rotation = [0, 0, 0.02827433441159227]
team_table_B[0].optimize = 2
file_tray_D[0].position = [4.5, 9.149999618530273, 1.0749999284744263]
file_tray_D[0].rotation = [0, 0, 0.01256637125682779]
file_tray_D[0].optimize = 2
standing_meeting_table_B[0].position = [14.600000381469727, 6.0, 0.5249999761581421]
standing_meeting_table_B[0].rotation = [0, 0, 0.021991148286022624]
standing_meeting_table_B[0].optimize = 2
magazine_E[0].position = [9.0, 8.399999618530273, 1.059999942779541]
magazine_E[0].rotation = [0, 0, 0.01256637125682779]
magazine_E[0].optimize = 2
keyboard_and_mouse_set[0].position = [4.800000190734863, 4.150000095367432, 0.7699999809265137]
keyboard_and_mouse_set[0].rotation = [0, 0, -3.1290262823329655]
keyboard_and_mouse_set[0].optimize = 2
task_chair_A[0].position = [3.7183446884155273, 4.318320274353027, 0.574999988079071]
task_chair_A[0].rotation = [0, 0, 0.0157079639172164]
task_chair_A[0].optimize = 2
small_potted_plant_A[0].position = [2.700000047683716, 2.5, 0.75]
small_potted_plant_A[0].rotation = [0, 0, 0.01256637125682779]
small_potted_plant_A[0].optimize = 2
file_tray_E[0].position = [9.0, 9.149999618530273, 1.0749999284744263]
file_tray_E[0].rotation = [0, 0, 0.01256637125682779]
file_tray_E[0].optimize = 2
magazine_A[0].position = [5.150000095367432, 3.450000047683716, 0.7599999904632568]
magazine_A[0].rotation = [0, 0, 0.01256637125682779]
magazine_A[0].optimize = 2
desk_side_cabinet_C[0].position = [5.300000190734863, 0.22511455416679382, 0.36000001430511475]
desk_side_cabinet_C[0].rotation = [0, 0, 1.5709785795436737]
desk_side_cabinet_C[0].optimize = 2
magazine_B[0].position = [8.149999618530273, 3.450000047683716, 0.7649999856948853]
magazine_B[0].rotation = [0, 0, 0.01256637125682779]
magazine_B[0].optimize = 2
coat_stand_B[0].position = [3.0, 0.6000000238418579, 0.875]
coat_stand_B[0].rotation = [0, 0, 0.00942477746072377]
coat_stand_B[0].optimize = 2
counter_stool_A[0].position = [9.018338203430176, 1.7999999523162842, 0.3400000035762787]
counter_stool_A[0].rotation = [0, 0, 0.0157079639172164]
counter_stool_A[0].optimize = 2
wayfinding_sign_D[0].position = [10.050000190734863, 10.774999618530273, 0.875]
wayfinding_sign_D[0].rotation = [0, 0, -1.5582299555380688]
wayfinding_sign_D[0].optimize = 2
planter_box_A[0].position = [16.799999237060547, 4.800000190734863, 0.32499998807907104]
planter_box_A[0].rotation = [0, 0, -3.1290262823329655]
planter_box_A[0].optimize = 2
low_storage_cabinet_B[0].position = [5.400000095367432, 10.774761199951172, 0.375]
low_storage_cabinet_B[0].rotation = [0, 0, -1.570906902040009]
low_storage_cabinet_B[0].optimize = 2
pen_cup_B[0].position = [7.599999904632568, 3.5, 0.8500000238418579]
pen_cup_B[0].rotation = [0, 0, 0.01256637125682779]
pen_cup_B[0].optimize = 2
side_occasion_table_A[0].position = [2.700000047683716, 2.5, 0.25]
side_occasion_table_A[0].rotation = [0, 0, 0.01256637125682779]
side_occasion_table_A[0].optimize = 2
wayfinding_sign_B[0].position = [5.150000095367432, 10.774999618530273, 0.875]
wayfinding_sign_B[0].rotation = [0, 0, -1.5582299555380688]
wayfinding_sign_B[0].optimize = 2
side_occasion_table_B[0].position = [3.0999999046325684, 6.5, 0.25]
side_occasion_table_B[0].rotation = [0, 0, 0.01256637125682779]
side_occasion_table_B[0].optimize = 2
desk_side_cabinet_D[0].position = [6.599999904632568, 0.2250683605670929, 0.36000001430511475]
desk_side_cabinet_D[0].rotation = [0, 0, 1.5707346457611155]
desk_side_cabinet_D[0].optimize = 2
counter_stool_B[0].position = [10.981661796569824, 1.7999999523162842, 0.3400000035762787]
counter_stool_B[0].rotation = [0, 0, -3.125884689672577]
counter_stool_B[0].optimize = 2
floor_lamp_B[0].position = [12.399999618530273, 6.800000190734863, 0.824999988079071]
floor_lamp_B[0].rotation = [0, 0, 0.00942477746072377]
floor_lamp_B[0].optimize = 2
small_potted_plant_B[0].position = [3.0999999046325684, 6.5, 0.675000011920929]
small_potted_plant_B[0].rotation = [0, 0, 0.01256637125682779]
small_potted_plant_B[0].optimize = 2
high_stool_E[0].position = [14.600000381469727, 2.0183398723602295, 0.38999998569488525]
high_stool_E[0].rotation = [0, 0, 1.586504290712113]
high_stool_E[0].optimize = 2
desk_organizer_A[0].position = [5.300000190734863, 0.22499999403953552, 0.8300000429153442]
desk_organizer_A[0].rotation = [0, 0, 1.5833626980517244]
desk_organizer_A[0].optimize = 2
desk_organizer_C[0].position = [10.649999618530273, 5.849999904632568, 0.8600000143051147]
desk_organizer_C[0].rotation = [0, 0, 0.01256637125682779]
desk_organizer_C[0].optimize = 2
sofa_modular[0].position = [2.6500000953674316, 4.400000095367432, 0.4099999964237213]
sofa_modular[0].rotation = [0, 0, 0.00942477746072377]
sofa_modular[0].optimize = 2
printer_side_table_B[0].position = [16.600000381469727, 7.199999809265137, 0.36000001430511475]
printer_side_table_B[0].rotation = [0, 0, -3.1290262823329655]
printer_side_table_B[0].optimize = 2
high_stool_B[0].position = [9.981661796569824, 8.800000190734863, 0.38999998569488525]
high_stool_B[0].rotation = [0, 0, -3.125884689672577]
high_stool_B[0].optimize = 2
low_storage_cabinet_A[0].position = [3.700000047683716, 10.774761199951172, 0.375]
low_storage_cabinet_A[0].rotation = [0, 0, -1.570906902040009]
low_storage_cabinet_A[0].optimize = 2
task_chair_E[0].position = [9.718342781066895, 4.318320274353027, 0.574999988079071]
task_chair_E[0].rotation = [0, 0, 0.0157079639172164]
task_chair_E[0].optimize = 2
framed_photo_B[0].position = [5.75, 10.774999618530273, 0.8999999761581421]
framed_photo_B[0].rotation = [0, 0, -1.5582299555380688]
framed_photo_B[0].optimize = 2
planter_box_B[0].position = [16.799999237060547, 2.799999952316284, 0.32499998807907104]
planter_box_B[0].rotation = [0, 0, -3.1321678761290697]
planter_box_B[0].optimize = 2
side_occasion_table_C[0].position = [12.5, 7.800000190734863, 0.25]
side_occasion_table_C[0].rotation = [0, 0, 0.01256637125682779]
side_occasion_table_C[0].optimize = 2
work_bench_desk_B[0].position = [8.0, 4.800000190734863, 0.375]
work_bench_desk_B[0].rotation = [0, 0, 0.03769911119841034]
work_bench_desk_B[0].optimize = 2
coat_stand_A[0].position = [0.6000000238418579, 5.599999904632568, 0.875]
coat_stand_A[0].rotation = [0, 0, 0.00942477746072377]
coat_stand_A[0].optimize = 2
framed_photo_C[0].position = [8.850000381469727, 10.774999618530273, 0.8999999761581421]
framed_photo_C[0].rotation = [0, 0, -1.5582299555380688]
framed_photo_C[0].optimize = 2
high_stool_D[0].position = [5.481660842895508, 8.800000190734863, 0.38999998569488525]
high_stool_D[0].rotation = [0, 0, -3.125884689672577]
high_stool_D[0].optimize = 2
office_monitor_A[0].position = [5.150000095367432, 4.150000095367432, 0.9750000238418579]
office_monitor_A[0].rotation = [0, 0, -3.1290262823329655]
office_monitor_A[0].optimize = 2
mobile_pedestal_B[0].position = [8.0, 2.5, 0.30000001192092896]
mobile_pedestal_B[0].rotation = [0, 0, -3.1321678761290697]
mobile_pedestal_B[0].optimize = 2
high_stool_G[0].position = [14.600000381469727, 5.018339157104492, 0.38999998569488525]
high_stool_G[0].rotation = [0, 0, 1.586504290712113]
high_stool_G[0].optimize = 2
low_storage_cabinet_D[0].position = [10.300000190734863, 10.774761199951172, 0.375]
low_storage_cabinet_D[0].rotation = [0, 0, -1.570906902040009]
low_storage_cabinet_D[0].optimize = 2
high_stool_A[0].position = [8.018338203430176, 8.800000190734863, 0.38999998569488525]
high_stool_A[0].rotation = [0, 0, 0.0157079639172164]
high_stool_A[0].optimize = 2
framed_photo_D[0].position = [10.649999618530273, 10.774999618530273, 0.8999999761581421]
framed_photo_D[0].rotation = [0, 0, -1.5582299555380688]
framed_photo_D[0].optimize = 2
office_printer_A[0].position = [15.800000190734863, 1.5, 0.8950000405311584]
office_printer_A[0].rotation = [0, 0, -3.1290262823329655]
office_printer_A[0].optimize = 2
task_chair_B[0].position = [6.281656265258789, 5.281679630279541, 0.574999988079071]
task_chair_B[0].rotation = [0, 0, -3.125884689672577]
task_chair_B[0].optimize = 2
high_stool_I[0].position = [10.0, 2.7816600799560547, 0.38999998569488525]
high_stool_I[0].rotation = [0, 0, -1.5550883628776802]
high_stool_I[0].optimize = 2
office_monitor_B[0].position = [8.149999618530273, 4.150000095367432, 0.9750000238418579]
office_monitor_B[0].rotation = [0, 0, -3.1290262823329655]
office_monitor_B[0].optimize = 2
low_storage_cabinet_C[0].position = [8.5, 10.774761199951172, 0.375]
low_storage_cabinet_C[0].rotation = [0, 0, -1.570906902040009]
low_storage_cabinet_C[0].optimize = 2
file_tray_A[0].position = [5.150000095367432, 5.800000190734863, 0.7799999713897705]
file_tray_A[0].rotation = [0, 0, 0.01256637125682779]
file_tray_A[0].optimize = 2
desk_side_cabinet_A[0].position = [12.774884223937988, 9.600000381469727, 0.36000001430511475]
desk_side_cabinet_A[0].rotation = [0, 0, -3.1414103730230325]
desk_side_cabinet_A[0].optimize = 2
file_tray_C[0].position = [11.199999809265137, 3.5, 0.7799999713897705]
file_tray_C[0].rotation = [0, 0, 0.01256637125682779]
file_tray_C[0].optimize = 2
team_table_A[0].position = [4.5, 8.800000190734863, 0.5249999761581421]
team_table_A[0].rotation = [0, 0, 0.02827433441159227]
team_table_A[0].optimize = 2

