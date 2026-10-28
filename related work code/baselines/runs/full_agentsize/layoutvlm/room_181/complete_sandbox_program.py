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
    Wall(corner1=[7.00, 0.00, 0.00], corner2=[7.00, 5.00, 0.00]),
    Wall(corner1=[7.00, 5.00, 0.00], corner2=[0.00, 5.00, 0.00]),
    Wall(corner1=[0.00, 5.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
acetone_nail_polish_remover_bottle = Assets(description="acetone nail polish remover bottle", size=[0.07, 0.07, 0.18], placements=[AssetInstance() for _ in range(1)])
nail_buffer_block_A = Assets(description="nail buffer block", size=[0.04, 0.10, 0.03], placements=[AssetInstance() for _ in range(1)])
salon_client_chair_A = Assets(description="salon client chair", size=[0.72, 0.68, 1.02], placements=[AssetInstance() for _ in range(1)])
hand_sanitizer_bottle_A = Assets(description="hand sanitizer bottle", size=[0.07, 0.07, 0.19], placements=[AssetInstance() for _ in range(1)])
hand_sanitizer_bottle_B = Assets(description="hand sanitizer bottle", size=[0.07, 0.07, 0.19], placements=[AssetInstance() for _ in range(1)])
manicure_table_A = Assets(description="manicure table", size=[0.50, 1.20, 0.76], placements=[AssetInstance() for _ in range(1)])
card_payment_terminal = Assets(description="card payment terminal", size=[0.18, 0.09, 0.07], placements=[AssetInstance() for _ in range(1)])
hand_sanitizer_bottle_C = Assets(description="hand sanitizer bottle", size=[0.07, 0.07, 0.19], placements=[AssetInstance() for _ in range(1)])
print_A = Assets(description="print", size=[0.03, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
technician_stool_A = Assets(description="technician stool", size=[0.45, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
cotton_pad_A = Assets(description="cotton pad", size=[0.06, 0.06, 0.00], placements=[AssetInstance() for _ in range(1)])
sign = Assets(description="sign", size=[0.03, 0.60, 0.30], placements=[AssetInstance() for _ in range(1)])
potted_plant = Assets(description="potted plant", size=[0.28, 0.28, 0.45], placements=[AssetInstance() for _ in range(1)])
ballpoint_pen = Assets(description="ballpoint pen", size=[0.14, 0.01, 0.01], placements=[AssetInstance() for _ in range(1)])
cotton_pad_B = Assets(description="cotton pad", size=[0.06, 0.06, 0.00], placements=[AssetInstance() for _ in range(1)])
side_table = Assets(description="side table", size=[0.48, 0.48, 0.55], placements=[AssetInstance() for _ in range(1)])
salon_client_chair_B = Assets(description="salon client chair", size=[0.72, 0.68, 1.02], placements=[AssetInstance() for _ in range(1)])
print_B = Assets(description="print", size=[0.03, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
print_C = Assets(description="print", size=[0.03, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
technician_stool_B = Assets(description="technician stool", size=[0.45, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
nail_polish = Assets(description="nail polish", size=[0.04, 0.04, 0.07], placements=[AssetInstance() for _ in range(1)])
print_D = Assets(description="print", size=[0.03, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
new_shades_card = Assets(description="new shades card", size=[0.01, 0.21, 0.30], placements=[AssetInstance() for _ in range(1)])
facial_tissue = Assets(description="facial tissue", size=[0.12, 0.20, 0.01], placements=[AssetInstance() for _ in range(1)])
reception_counter = Assets(description="reception counter", size=[0.65, 1.80, 1.10], placements=[AssetInstance() for _ in range(1)])
nail_curing_lamp_A = Assets(description="nail curing lamp", size=[0.20, 0.22, 0.10], placements=[AssetInstance() for _ in range(1)])
screw_lid = Assets(description="screw lid", size=[0.06, 0.06, 0.02], placements=[AssetInstance() for _ in range(1)])
manicure_hand_rest_pillow_A = Assets(description="manicure hand rest pillow", size=[0.16, 0.38, 0.08], placements=[AssetInstance() for _ in range(1)])
waiting_bench = Assets(description="waiting bench", size=[0.62, 1.60, 0.88], placements=[AssetInstance() for _ in range(1)])
wall_sign = Assets(description="wall sign", size=[0.04, 0.90, 0.45], placements=[AssetInstance() for _ in range(1)])
clock = Assets(description="clock", size=[0.05, 0.32, 0.32], placements=[AssetInstance() for _ in range(1)])
cotton_pad_C = Assets(description="cotton pad", size=[0.06, 0.06, 0.00], placements=[AssetInstance() for _ in range(1)])
manicure_hand_rest_pillow_B = Assets(description="manicure hand rest pillow", size=[0.16, 0.38, 0.08], placements=[AssetInstance() for _ in range(1)])
print_E = Assets(description="print", size=[0.03, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
business_card_holder = Assets(description="business card holder", size=[0.05, 0.11, 0.06], placements=[AssetInstance() for _ in range(1)])
tissue_dispenser_box = Assets(description="tissue dispenser box", size=[0.13, 0.24, 0.10], placements=[AssetInstance() for _ in range(1)])
wall_planter_A = Assets(description="wall planter", size=[0.18, 0.32, 0.28], placements=[AssetInstance() for _ in range(1)])
magazine = Assets(description="magazine", size=[0.29, 0.22, 0.01], placements=[AssetInstance() for _ in range(1)])
manicure_tool_tray_A = Assets(description="manicure tool tray", size=[0.20, 0.30, 0.04], placements=[AssetInstance() for _ in range(1)])
manicure_table_B = Assets(description="manicure table", size=[0.50, 1.20, 0.76], placements=[AssetInstance() for _ in range(1)])
mirror_A = Assets(description="mirror", size=[0.04, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
plastic_jar = Assets(description="plastic jar", size=[0.10, 0.10, 0.12], placements=[AssetInstance() for _ in range(1)])
nail_curing_lamp_B = Assets(description="nail curing lamp", size=[0.20, 0.22, 0.10], placements=[AssetInstance() for _ in range(1)])
wall_planter_B = Assets(description="wall planter", size=[0.18, 0.32, 0.28], placements=[AssetInstance() for _ in range(1)])
display_shelf = Assets(description="display shelf", size=[0.40, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
cotton_pad_D = Assets(description="cotton pad", size=[0.06, 0.06, 0.00], placements=[AssetInstance() for _ in range(1)])
mirror_B = Assets(description="mirror", size=[0.04, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
appointment_book_planner = Assets(description="appointment book planner", size=[0.32, 0.24, 0.04], placements=[AssetInstance() for _ in range(1)])
manicure_tool_tray_B = Assets(description="manicure tool tray", size=[0.20, 0.30, 0.04], placements=[AssetInstance() for _ in range(1)])
nail_buffer_block_B = Assets(description="nail buffer block", size=[0.04, 0.10, 0.03], placements=[AssetInstance() for _ in range(1)])

acetone_nail_polish_remover_bottle[0].instance_id = 'acetone_nail_polish_remover_bottle_0'
nail_buffer_block_A[0].instance_id = 'nail_buffer_block_A_0'
salon_client_chair_A[0].instance_id = 'salon_client_chair_A_0'
hand_sanitizer_bottle_A[0].instance_id = 'hand_sanitizer_bottle_A_0'
hand_sanitizer_bottle_B[0].instance_id = 'hand_sanitizer_bottle_B_0'
manicure_table_A[0].instance_id = 'manicure_table_A_0'
card_payment_terminal[0].instance_id = 'card_payment_terminal_0'
hand_sanitizer_bottle_C[0].instance_id = 'hand_sanitizer_bottle_C_0'
print_A[0].instance_id = 'print_A_0'
technician_stool_A[0].instance_id = 'technician_stool_A_0'
cotton_pad_A[0].instance_id = 'cotton_pad_A_0'
sign[0].instance_id = 'sign_0'
potted_plant[0].instance_id = 'potted_plant_0'
ballpoint_pen[0].instance_id = 'ballpoint_pen_0'
cotton_pad_B[0].instance_id = 'cotton_pad_B_0'
side_table[0].instance_id = 'side_table_0'
salon_client_chair_B[0].instance_id = 'salon_client_chair_B_0'
print_B[0].instance_id = 'print_B_0'
print_C[0].instance_id = 'print_C_0'
technician_stool_B[0].instance_id = 'technician_stool_B_0'
nail_polish[0].instance_id = 'nail_polish_0'
print_D[0].instance_id = 'print_D_0'
new_shades_card[0].instance_id = 'new_shades_card_0'
facial_tissue[0].instance_id = 'facial_tissue_0'
reception_counter[0].instance_id = 'reception_counter_0'
nail_curing_lamp_A[0].instance_id = 'nail_curing_lamp_A_0'
screw_lid[0].instance_id = 'screw_lid_0'
manicure_hand_rest_pillow_A[0].instance_id = 'manicure_hand_rest_pillow_A_0'
waiting_bench[0].instance_id = 'waiting_bench_0'
wall_sign[0].instance_id = 'wall_sign_0'
clock[0].instance_id = 'clock_0'
cotton_pad_C[0].instance_id = 'cotton_pad_C_0'
manicure_hand_rest_pillow_B[0].instance_id = 'manicure_hand_rest_pillow_B_0'
print_E[0].instance_id = 'print_E_0'
business_card_holder[0].instance_id = 'business_card_holder_0'
tissue_dispenser_box[0].instance_id = 'tissue_dispenser_box_0'
wall_planter_A[0].instance_id = 'wall_planter_A_0'
magazine[0].instance_id = 'magazine_0'
manicure_tool_tray_A[0].instance_id = 'manicure_tool_tray_A_0'
manicure_table_B[0].instance_id = 'manicure_table_B_0'
mirror_A[0].instance_id = 'mirror_A_0'
plastic_jar[0].instance_id = 'plastic_jar_0'
nail_curing_lamp_B[0].instance_id = 'nail_curing_lamp_B_0'
wall_planter_B[0].instance_id = 'wall_planter_B_0'
display_shelf[0].instance_id = 'display_shelf_0'
cotton_pad_D[0].instance_id = 'cotton_pad_D_0'
mirror_B[0].instance_id = 'mirror_B_0'
appointment_book_planner[0].instance_id = 'appointment_book_planner_0'
manicure_tool_tray_B[0].instance_id = 'manicure_tool_tray_B_0'
nail_buffer_block_B[0].instance_id = 'nail_buffer_block_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

acetone_nail_polish_remover_bottle[0].position = [6.725036334676788, 4.1593881070616785, 0.09]
acetone_nail_polish_remover_bottle[0].rotation = [0, 0, 0]
nail_buffer_block_A[0].position = [0.00043455591975216645, 2.815763103693359, 0.015]
nail_buffer_block_A[0].rotation = [0, 0, 0]
salon_client_chair_A[0].position = [3.482023379072193, 3.5651674390565393, 0.51]
salon_client_chair_A[0].rotation = [0, 0, 0]
hand_sanitizer_bottle_A[0].position = [3.9012069521919286, 4.270209163061861, 0.095]
hand_sanitizer_bottle_A[0].rotation = [0, 0, 0]
hand_sanitizer_bottle_B[0].position = [0.0542058249443389, 3.0589531829066052, 0.095]
hand_sanitizer_bottle_B[0].rotation = [0, 0, 0]
manicure_table_A[0].position = [0.9246955703059636, 1.4725991783574488, 0.38]
manicure_table_A[0].rotation = [0, 0, 0]
card_payment_terminal[0].position = [2.808433969105513, 0.7700654330647871, 0.035]
card_payment_terminal[0].rotation = [0, 0, 0]
hand_sanitizer_bottle_C[0].position = [2.995698462288595, 1.2845388517501166, 0.095]
hand_sanitizer_bottle_C[0].rotation = [0, 0, 0]
print_A[0].position = [2.2759080162766407, 2.72770084050938, 0.35]
print_A[0].rotation = [0, 0, 0]
technician_stool_A[0].position = [6.96679589917553, 0.2971914323749436, 0.275]
technician_stool_A[0].rotation = [0, 0, 0]
cotton_pad_A[0].position = [2.859217954653187, 0.20416763407703598, 0.002]
cotton_pad_A[0].rotation = [0, 0, 0]
sign[0].position = [5.3442265787124725, 4.35247065566744, 0.15]
sign[0].rotation = [0, 0, 0]
potted_plant[0].position = [3.8423419776565115, 0.8866668729527927, 0.225]
potted_plant[0].rotation = [0, 0, 0]
ballpoint_pen[0].position = [0.26344039507969397, 2.354039643975501, 0.0075]
ballpoint_pen[0].rotation = [0, 0, 0]
cotton_pad_B[0].position = [5.304033421209887, 4.756065152885608, 0.002]
cotton_pad_B[0].rotation = [0, 0, 0]
side_table[0].position = [4.949640788255209, 1.89462303734934, 0.275]
side_table[0].rotation = [0, 0, 0]
salon_client_chair_B[0].position = [5.627966892282916, 3.0883163649775747, 0.51]
salon_client_chair_B[0].rotation = [0, 0, 0]
print_B[0].position = [1.3801274092477342, 4.166889666460943, 0.35]
print_B[0].rotation = [0, 0, 0]
print_C[0].position = [6.744931332336035, 1.6662957840216257, 0.35]
print_C[0].rotation = [0, 0, 0]
technician_stool_B[0].position = [2.4926823623508714, 2.2249522087708247, 0.275]
technician_stool_B[0].rotation = [0, 0, 0]
nail_polish[0].position = [1.755218643383774, 2.4283057148324314, 0.0375]
nail_polish[0].rotation = [0, 0, 0]
print_D[0].position = [5.274335642073452, 3.724665447916597, 0.35]
print_D[0].rotation = [0, 0, 0]
new_shades_card[0].position = [4.610872617558399, 3.6262633368647124, 0.15]
new_shades_card[0].rotation = [0, 0, 0]
facial_tissue[0].position = [6.830715969611826, 0.7065464829091328, 0.005]
facial_tissue[0].rotation = [0, 0, 0]
reception_counter[0].position = [3.227959156741479, 0.37685047412494677, 0.55]
reception_counter[0].rotation = [0, 0, 0]
nail_curing_lamp_A[0].position = [0.7135237965015395, 0.051854002515686615, 0.05]
nail_curing_lamp_A[0].rotation = [0, 0, 0]
screw_lid[0].position = [4.287880038097495, 1.7663145749096998, 0.009]
screw_lid[0].rotation = [0, 0, 0]
manicure_hand_rest_pillow_A[0].position = [6.6121544793322595, 1.8356027663073726, 0.04]
manicure_hand_rest_pillow_A[0].rotation = [0, 0, 0]
waiting_bench[0].position = [1.4742867404141236, 4.8349400970573075, 0.44]
waiting_bench[0].rotation = [0, 0, 0]
wall_sign[0].position = [4.815627610831873, 0.19023309641411357, 0.225]
wall_sign[0].rotation = [0, 0, 0]
clock[0].position = [5.058539640002934, 0.30050985164540356, 0.16]
clock[0].rotation = [0, 0, 0]
cotton_pad_C[0].position = [4.058832279249566, 2.2274640085889326, 0.002]
cotton_pad_C[0].rotation = [0, 0, 0]
manicure_hand_rest_pillow_B[0].position = [0.8252113924466845, 2.610753884742601, 0.04]
manicure_hand_rest_pillow_B[0].rotation = [0, 0, 0]
print_E[0].position = [0.9413788186235498, 2.813406514240393, 0.35]
print_E[0].rotation = [0, 0, 0]
business_card_holder[0].position = [4.3756639146957195, 4.951009506256377, 0.03]
business_card_holder[0].rotation = [0, 0, 0]
tissue_dispenser_box[0].position = [1.3620226407781835, 1.8456598512529259, 0.05]
tissue_dispenser_box[0].rotation = [0, 0, 0]
wall_planter_A[0].position = [3.944548883888579, 4.450023599065258, 0.14]
wall_planter_A[0].rotation = [0, 0, 0]
magazine[0].position = [1.9228320490324267, 3.0990234628875775, 0.004]
magazine[0].rotation = [0, 0, 0]
manicure_tool_tray_A[0].position = [3.741230973556551, 1.015549416839765, 0.0175]
manicure_tool_tray_A[0].rotation = [0, 0, 0]
manicure_table_B[0].position = [1.6168290210319536, 2.4171474456807407, 0.38]
manicure_table_B[0].rotation = [0, 0, 0]
mirror_A[0].position = [6.347521421842155, 2.2386155250258106, 0.55]
mirror_A[0].rotation = [0, 0, 0]
plastic_jar[0].position = [0.12847852706300344, 1.2180011135033042, 0.06]
plastic_jar[0].rotation = [0, 0, 0]
nail_curing_lamp_B[0].position = [5.331714239318636, 0.5094685984797009, 0.05]
nail_curing_lamp_B[0].rotation = [0, 0, 0]
wall_planter_B[0].position = [0.8068900874812575, 3.7499589362757475, 0.14]
wall_planter_B[0].rotation = [0, 0, 0]
display_shelf[0].position = [4.609613037232972, 3.3733026267463684, 0.9]
display_shelf[0].rotation = [0, 0, 0]
cotton_pad_D[0].position = [4.543599693785687, 0.29685729202923783, 0.002]
cotton_pad_D[0].rotation = [0, 0, 0]
mirror_B[0].position = [0.03633402522004692, 4.857763666646445, 0.55]
mirror_B[0].rotation = [0, 0, 0]
appointment_book_planner[0].position = [3.2530678466266645, 2.609620129760671, 0.0175]
appointment_book_planner[0].rotation = [0, 0, 0]
manicure_tool_tray_B[0].position = [6.31715500020966, 1.737490933468833, 0.0175]
manicure_tool_tray_B[0].rotation = [0, 0, 0]
nail_buffer_block_B[0].position = [2.6504738661687255, 4.475152420063081, 0.015]
nail_buffer_block_B[0].rotation = [0, 0, 0]
acetone_nail_polish_remover_bottle[0].position = [6.725036334676788, 4.1593881070616785, 0.09]
acetone_nail_polish_remover_bottle[0].rotation = [0, 0, 0]
nail_buffer_block_A[0].position = [0.00043455591975216645, 2.815763103693359, 0.015]
nail_buffer_block_A[0].rotation = [0, 0, 0]
salon_client_chair_A[0].position = [3.482023379072193, 3.5651674390565393, 0.51]
salon_client_chair_A[0].rotation = [0, 0, 0]
hand_sanitizer_bottle_A[0].position = [3.9012069521919286, 4.270209163061861, 0.095]
hand_sanitizer_bottle_A[0].rotation = [0, 0, 0]
hand_sanitizer_bottle_B[0].position = [0.0542058249443389, 3.0589531829066052, 0.095]
hand_sanitizer_bottle_B[0].rotation = [0, 0, 0]
manicure_table_A[0].position = [0.9246955703059636, 1.4725991783574488, 0.38]
manicure_table_A[0].rotation = [0, 0, 0]
card_payment_terminal[0].position = [2.808433969105513, 0.7700654330647871, 0.035]
card_payment_terminal[0].rotation = [0, 0, 0]
hand_sanitizer_bottle_C[0].position = [2.995698462288595, 1.2845388517501166, 0.095]
hand_sanitizer_bottle_C[0].rotation = [0, 0, 0]
print_A[0].position = [2.2759080162766407, 2.72770084050938, 0.35]
print_A[0].rotation = [0, 0, 0]
technician_stool_A[0].position = [6.96679589917553, 0.2971914323749436, 0.275]
technician_stool_A[0].rotation = [0, 0, 0]
cotton_pad_A[0].position = [2.859217954653187, 0.20416763407703598, 0.002]
cotton_pad_A[0].rotation = [0, 0, 0]
sign[0].position = [5.3442265787124725, 4.35247065566744, 0.15]
sign[0].rotation = [0, 0, 0]
potted_plant[0].position = [3.8423419776565115, 0.8866668729527927, 0.225]
potted_plant[0].rotation = [0, 0, 0]
ballpoint_pen[0].position = [0.26344039507969397, 2.354039643975501, 0.0075]
ballpoint_pen[0].rotation = [0, 0, 0]
cotton_pad_B[0].position = [5.304033421209887, 4.756065152885608, 0.002]
cotton_pad_B[0].rotation = [0, 0, 0]
side_table[0].position = [4.949640788255209, 1.89462303734934, 0.275]
side_table[0].rotation = [0, 0, 0]
salon_client_chair_B[0].position = [5.627966892282916, 3.0883163649775747, 0.51]
salon_client_chair_B[0].rotation = [0, 0, 0]
print_B[0].position = [1.3801274092477342, 4.166889666460943, 0.35]
print_B[0].rotation = [0, 0, 0]
print_C[0].position = [6.744931332336035, 1.6662957840216257, 0.35]
print_C[0].rotation = [0, 0, 0]
technician_stool_B[0].position = [2.4926823623508714, 2.2249522087708247, 0.275]
technician_stool_B[0].rotation = [0, 0, 0]
nail_polish[0].position = [1.755218643383774, 2.4283057148324314, 0.0375]
nail_polish[0].rotation = [0, 0, 0]
print_D[0].position = [5.274335642073452, 3.724665447916597, 0.35]
print_D[0].rotation = [0, 0, 0]
new_shades_card[0].position = [4.610872617558399, 3.6262633368647124, 0.15]
new_shades_card[0].rotation = [0, 0, 0]
facial_tissue[0].position = [6.830715969611826, 0.7065464829091328, 0.005]
facial_tissue[0].rotation = [0, 0, 0]
reception_counter[0].position = [3.227959156741479, 0.37685047412494677, 0.55]
reception_counter[0].rotation = [0, 0, 0]
nail_curing_lamp_A[0].position = [0.7135237965015395, 0.051854002515686615, 0.05]
nail_curing_lamp_A[0].rotation = [0, 0, 0]
screw_lid[0].position = [4.287880038097495, 1.7663145749096998, 0.009]
screw_lid[0].rotation = [0, 0, 0]
manicure_hand_rest_pillow_A[0].position = [6.6121544793322595, 1.8356027663073726, 0.04]
manicure_hand_rest_pillow_A[0].rotation = [0, 0, 0]
waiting_bench[0].position = [1.4742867404141236, 4.8349400970573075, 0.44]
waiting_bench[0].rotation = [0, 0, 0]
wall_sign[0].position = [4.815627610831873, 0.19023309641411357, 0.225]
wall_sign[0].rotation = [0, 0, 0]
clock[0].position = [5.058539640002934, 0.30050985164540356, 0.16]
clock[0].rotation = [0, 0, 0]
cotton_pad_C[0].position = [4.058832279249566, 2.2274640085889326, 0.002]
cotton_pad_C[0].rotation = [0, 0, 0]
manicure_hand_rest_pillow_B[0].position = [0.8252113924466845, 2.610753884742601, 0.04]
manicure_hand_rest_pillow_B[0].rotation = [0, 0, 0]
print_E[0].position = [0.9413788186235498, 2.813406514240393, 0.35]
print_E[0].rotation = [0, 0, 0]
business_card_holder[0].position = [4.3756639146957195, 4.951009506256377, 0.03]
business_card_holder[0].rotation = [0, 0, 0]
tissue_dispenser_box[0].position = [1.3620226407781835, 1.8456598512529259, 0.05]
tissue_dispenser_box[0].rotation = [0, 0, 0]
wall_planter_A[0].position = [3.944548883888579, 4.450023599065258, 0.14]
wall_planter_A[0].rotation = [0, 0, 0]
magazine[0].position = [1.9228320490324267, 3.0990234628875775, 0.004]
magazine[0].rotation = [0, 0, 0]
manicure_tool_tray_A[0].position = [3.741230973556551, 1.015549416839765, 0.0175]
manicure_tool_tray_A[0].rotation = [0, 0, 0]
manicure_table_B[0].position = [1.6168290210319536, 2.4171474456807407, 0.38]
manicure_table_B[0].rotation = [0, 0, 0]
mirror_A[0].position = [6.347521421842155, 2.2386155250258106, 0.55]
mirror_A[0].rotation = [0, 0, 0]
plastic_jar[0].position = [0.12847852706300344, 1.2180011135033042, 0.06]
plastic_jar[0].rotation = [0, 0, 0]
nail_curing_lamp_B[0].position = [5.331714239318636, 0.5094685984797009, 0.05]
nail_curing_lamp_B[0].rotation = [0, 0, 0]
wall_planter_B[0].position = [0.8068900874812575, 3.7499589362757475, 0.14]
wall_planter_B[0].rotation = [0, 0, 0]
display_shelf[0].position = [4.609613037232972, 3.3733026267463684, 0.9]
display_shelf[0].rotation = [0, 0, 0]
cotton_pad_D[0].position = [4.543599693785687, 0.29685729202923783, 0.002]
cotton_pad_D[0].rotation = [0, 0, 0]
mirror_B[0].position = [0.03633402522004692, 4.857763666646445, 0.55]
mirror_B[0].rotation = [0, 0, 0]
appointment_book_planner[0].position = [3.2530678466266645, 2.609620129760671, 0.0175]
appointment_book_planner[0].rotation = [0, 0, 0]
manicure_tool_tray_B[0].position = [6.31715500020966, 1.737490933468833, 0.0175]
manicure_tool_tray_B[0].rotation = [0, 0, 0]
nail_buffer_block_B[0].position = [2.6504738661687255, 4.475152420063081, 0.015]
nail_buffer_block_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Helper functions keep the placement and constraint declarations concise while
# preserving each provided asset variable.
def set_pose(asset, position, yaw=0.0):
    asset[0].position = position
    asset[0].rotation = [0, 0, radians(yaw)]


def fixed_pose_constraint(asset, weight=10):
    """Keep a floor-standing asset near its planned collision-free pose."""
    target = AssetInstance(
        position=list(asset[0].position),
        rotation=list(asset[0].rotation),
    )
    solver.distance_constraint(asset[0], target, 0.0, 0.0, weight=weight)
    solver.align_with(asset[0], target)


def place_on_surface(asset, support):
    """Preserve an item's tabletop location, elevation, and orientation."""
    target = AssetInstance(
        position=list(asset[0].position),
        rotation=list(asset[0].rotation),
    )
    solver.on_top_of(asset[0], support[0])
    solver.distance_constraint(asset[0], target, 0.0, 0.0, weight=10)
    solver.align_with(asset[0], support[0])


room_center = AssetInstance(position=[3.50, 2.50, 0.50])

# ---------------------------------------------------------------------------
# Main furniture
#
# Two manicure stations occupy the center of the room. The customer and
# technician seats remain on opposite sides of each table, leaving circulation
# space around the stations.
# ---------------------------------------------------------------------------

set_pose(manicure_table_A, [2.30, 1.60, 0.38], 0)
set_pose(salon_client_chair_B, [1.40, 1.60, 0.51], 0)
set_pose(technician_stool_B, [2.875, 1.60, 0.275], 180)

set_pose(manicure_table_B, [4.60, 2.95, 0.38], 0)
set_pose(salon_client_chair_A, [3.70, 2.95, 0.51], 0)
set_pose(technician_stool_A, [5.175, 2.95, 0.275], 180)

# The center separation of 0.575 m gives the 0.25 m table half-depth plus
# the 0.225 m stool radius and no more than 0.10 m of edge clearance.
# This is specified first because it is the required high-priority relation.
solver.distance_constraint(
    manicure_table_A[0],
    technician_stool_B[0],
    0.475,
    0.575,
    weight=10,
)
fixed_pose_constraint(manicure_table_A)

solver.distance_constraint(
    technician_stool_B[0],
    manicure_table_A[0],
    0.475,
    0.575,
    weight=10,
)
solver.point_towards(technician_stool_B[0], manicure_table_A[0])

solver.distance_constraint(
    salon_client_chair_B[0],
    manicure_table_A[0],
    0.80,
    1.00,
    weight=10,
)
solver.point_towards(salon_client_chair_B[0], manicure_table_A[0])

fixed_pose_constraint(manicure_table_B)

# Required relationship: salon client chair o0002 faces manicure table o0039.
solver.distance_constraint(
    salon_client_chair_A[0],
    manicure_table_B[0],
    0.80,
    1.00,
    weight=10,
)
solver.point_towards(salon_client_chair_A[0], manicure_table_B[0])

solver.distance_constraint(
    technician_stool_A[0],
    manicure_table_B[0],
    0.475,
    0.575,
    weight=10,
)
solver.point_towards(technician_stool_A[0], manicure_table_B[0])

# Reception furniture runs along the east wall and faces into the salon.
set_pose(reception_counter, [6.675, 1.25, 0.55], 180)
solver.against_wall(reception_counter[0], walls[1])
solver.distance_constraint(
    reception_counter[0],
    AssetInstance(position=[6.675, 1.25, 0.55]),
    0.0,
    0.0,
    weight=10,
)
solver.point_towards(reception_counter[0], room_center)

# The waiting bench is against the west wall, as required, and faces inward.
set_pose(waiting_bench, [0.31, 3.65, 0.44], 0)
solver.against_wall(waiting_bench[0], walls[3])
solver.distance_constraint(
    waiting_bench[0],
    AssetInstance(position=[0.31, 3.65, 0.44]),
    0.0,
    0.0,
    weight=10,
)
solver.point_towards(waiting_bench[0], room_center)

# A side table is convenient to the waiting bench without blocking its front.
set_pose(side_table, [1.16, 3.65, 0.275], 0)
solver.distance_constraint(side_table[0], waiting_bench[0], 0.80, 0.95)
solver.align_with(side_table[0], waiting_bench[0])

# The display shelf uses the remaining section of the east wall.
set_pose(display_shelf, [6.80, 4.12, 0.90], 180)
solver.against_wall(display_shelf[0], walls[1])
solver.distance_constraint(
    display_shelf[0],
    AssetInstance(position=[6.80, 4.12, 0.90]),
    0.0,
    0.0,
    weight=10,
)
solver.point_towards(display_shelf[0], room_center)

# Plant occupies an otherwise unused southwest corner.
set_pose(potted_plant, [0.32, 0.35, 0.225], 45)
solver.distance_constraint(
    potted_plant[0],
    AssetInstance(position=[0.32, 0.35, 0.225]),
    0.0,
    0.0,
    weight=10,
)
solver.point_towards(potted_plant[0], room_center)

# ---------------------------------------------------------------------------
# Items on manicure table A
# ---------------------------------------------------------------------------

set_pose(nail_curing_lamp_A, [2.30, 1.20, 0.81], 0)
set_pose(manicure_hand_rest_pillow_A, [2.30, 1.70, 0.80], 0)
set_pose(manicure_tool_tray_A, [2.30, 2.02, 0.78], 0)
set_pose(acetone_nail_polish_remover_bottle, [2.14, 1.48, 0.85], 0)
set_pose(nail_buffer_block_A, [2.46, 1.46, 0.775], 0)
set_pose(cotton_pad_A, [2.13, 1.91, 0.76], 0)
set_pose(cotton_pad_B, [2.47, 1.91, 0.76], 0)

place_on_surface(nail_curing_lamp_A, manicure_table_A)
place_on_surface(manicure_hand_rest_pillow_A, manicure_table_A)
place_on_surface(manicure_tool_tray_A, manicure_table_A)
place_on_surface(acetone_nail_polish_remover_bottle, manicure_table_A)
place_on_surface(nail_buffer_block_A, manicure_table_A)
place_on_surface(cotton_pad_A, manicure_table_A)
place_on_surface(cotton_pad_B, manicure_table_A)

# ---------------------------------------------------------------------------
# Items on manicure table B
# ---------------------------------------------------------------------------

set_pose(nail_curing_lamp_B, [4.48, 2.57, 0.81], 0)
set_pose(facial_tissue, [4.70, 2.58, 0.765], 0)
set_pose(manicure_hand_rest_pillow_B, [4.67, 3.03, 0.80], 0)
set_pose(manicure_tool_tray_B, [4.48, 3.39, 0.78], 0)
set_pose(nail_polish, [4.45, 2.82, 0.795], 0)
set_pose(plastic_jar, [4.70, 2.82, 0.82], 0)
set_pose(screw_lid, [4.45, 3.10, 0.77], 0)
set_pose(cotton_pad_C, [4.46, 3.17, 0.76], 0)
set_pose(cotton_pad_D, [4.47, 3.57, 0.76], 0)
set_pose(nail_buffer_block_B, [4.72, 3.48, 0.775], 0)

place_on_surface(nail_curing_lamp_B, manicure_table_B)
place_on_surface(facial_tissue, manicure_table_B)
place_on_surface(manicure_hand_rest_pillow_B, manicure_table_B)
place_on_surface(manicure_tool_tray_B, manicure_table_B)
place_on_surface(nail_polish, manicure_table_B)
place_on_surface(plastic_jar, manicure_table_B)
place_on_surface(screw_lid, manicure_table_B)
place_on_surface(cotton_pad_C, manicure_table_B)
place_on_surface(cotton_pad_D, manicure_table_B)
place_on_surface(nail_buffer_block_B, manicure_table_B)

# ---------------------------------------------------------------------------
# Reception-counter accessories
# ---------------------------------------------------------------------------

set_pose(sign, [6.43, 0.70, 1.25], 0)
set_pose(card_payment_terminal, [6.80, 0.55, 1.135], 180)
set_pose(hand_sanitizer_bottle_A, [6.58, 1.08, 1.195], 180)
set_pose(hand_sanitizer_bottle_C, [6.83, 1.08, 1.195], 180)
set_pose(appointment_book_planner, [6.66, 1.35, 1.12], 180)
set_pose(ballpoint_pen, [6.65, 1.53, 1.105], 180)
set_pose(new_shades_card, [6.89, 1.59, 1.25], 180)
set_pose(tissue_dispenser_box, [6.51, 1.82, 1.15], 180)
set_pose(business_card_holder, [6.85, 1.94, 1.13], 180)

place_on_surface(sign, reception_counter)
place_on_surface(card_payment_terminal, reception_counter)
place_on_surface(hand_sanitizer_bottle_A, reception_counter)
place_on_surface(hand_sanitizer_bottle_C, reception_counter)
place_on_surface(appointment_book_planner, reception_counter)
place_on_surface(ballpoint_pen, reception_counter)
place_on_surface(new_shades_card, reception_counter)
place_on_surface(tissue_dispenser_box, reception_counter)
place_on_surface(business_card_holder, reception_counter)

# Waiting-area reading material and sanitizer sit on the side table.
set_pose(magazine, [1.17, 3.56, 0.555], 0)
set_pose(hand_sanitizer_bottle_B, [1.17, 3.82, 0.645], 0)
place_on_surface(magazine, side_table)
place_on_surface(hand_sanitizer_bottle_B, side_table)

# ---------------------------------------------------------------------------
# North-wall prints and signage
# ---------------------------------------------------------------------------

set_pose(print_A, [0.65, 4.985, 1.55], -90)
set_pose(print_B, [1.75, 4.985, 1.55], -90)
set_pose(print_C, [2.85, 4.985, 1.55], -90)
set_pose(print_D, [3.95, 4.985, 1.55], -90)
set_pose(print_E, [5.05, 4.985, 1.55], -90)
set_pose(wall_sign, [6.10, 4.98, 1.62], -90)

for wall_asset in [print_A, print_B, print_C, print_D, print_E, wall_sign]:
    solver.against_wall(wall_asset[0], walls[2])
    solver.distance_constraint(
        wall_asset[0],
        AssetInstance(position=list(wall_asset[0].position)),
        0.0,
        0.0,
        weight=10,
    )
    solver.point_towards(wall_asset[0], room_center)

# Mirrors and clock use the south wall and face into the room.
set_pose(mirror_A, [1.30, 0.02, 1.20], 90)
set_pose(clock, [3.50, 0.025, 1.75], 90)
set_pose(mirror_B, [5.70, 0.02, 1.20], 90)

for south_wall_asset in [mirror_A, clock, mirror_B]:
    solver.against_wall(south_wall_asset[0], walls[0])
    solver.distance_constraint(
        south_wall_asset[0],
        AssetInstance(position=list(south_wall_asset[0].position)),
        0.0,
        0.0,
        weight=10,
    )
    solver.point_towards(south_wall_asset[0], room_center)

# Elevated planters decorate opposite side walls without consuming floor space.
set_pose(wall_planter_A, [0.09, 2.20, 1.45], 0)
solver.against_wall(wall_planter_A[0], walls[3])
solver.distance_constraint(
    wall_planter_A[0],
    AssetInstance(position=[0.09, 2.20, 1.45]),
    0.0,
    0.0,
    weight=10,
)
solver.point_towards(wall_planter_A[0], room_center)

set_pose(wall_planter_B, [6.91, 2.55, 1.45], 180)
solver.against_wall(wall_planter_B[0], walls[1])
solver.distance_constraint(
    wall_planter_B[0],
    AssetInstance(position=[6.91, 2.55, 1.45]),
    0.0,
    0.0,
    weight=10,
)
solver.point_towards(wall_planter_B[0], room_center)

solver.constraints = []
ballpoint_pen[0].position = [6.650000095367432, 1.5299999713897705, 1.1050000190734863]
ballpoint_pen[0].rotation = [0, 0, 3.1415913632941344]
ballpoint_pen[0].optimize = 2
plastic_jar[0].position = [4.699999809265137, 2.819999933242798, 0.8199999928474426]
plastic_jar[0].rotation = [0, 0, 0.08482265381612356]
plastic_jar[0].optimize = 2
print_A[0].position = [0.6499999761581421, 4.9850006103515625, 0.3499999940395355]
print_A[0].rotation = [0, 0, -1.5707962377328895]
print_A[0].optimize = 2
sign[0].position = [6.429999828338623, 0.699999988079071, 1.25]
sign[0].rotation = [0, 0, -3.1403913121123956]
sign[0].optimize = 2
nail_buffer_block_A[0].position = [2.4600000381469727, 1.4600000381469727, 0.7749999761581421]
nail_buffer_block_A[0].rotation = [0, 0, 0.0691152434500152]
nail_buffer_block_A[0].optimize = 2
salon_client_chair_A[0].position = [3.700000047683716, 2.950000047683716, 0.5099999904632568]
salon_client_chair_A[0].rotation = [0, 0, 0.00942477746072377]
salon_client_chair_A[0].optimize = 2
print_B[0].position = [1.75, 4.9850006103515625, 0.3499999940395355]
print_B[0].rotation = [0, 0, -1.5707962377328895]
print_B[0].optimize = 2
appointment_book_planner[0].position = [6.659999847412109, 1.350000023841858, 1.1200000047683716]
appointment_book_planner[0].rotation = [0, 0, 3.1415913632941344]
appointment_book_planner[0].optimize = 2
acetone_nail_polish_remover_bottle[0].position = [2.140000104904175, 1.4800000190734863, 0.8500000238418579]
acetone_nail_polish_remover_bottle[0].rotation = [0, 0, 0.0691152434500152]
acetone_nail_polish_remover_bottle[0].optimize = 2
waiting_bench[0].position = [0.31000006198883057, 3.6500000953674316, 0.4399999976158142]
waiting_bench[0].rotation = [0, 0, 4.327126746775628e-09]
waiting_bench[0].optimize = 2
cotton_pad_A[0].position = [2.130000114440918, 1.909999966621399, 0.7599999904632568]
cotton_pad_A[0].rotation = [0, 0, 0.0691152434500152]
cotton_pad_A[0].optimize = 2
hand_sanitizer_bottle_B[0].position = [1.1699999570846558, 3.819999933242798, 0.6449999809265137]
hand_sanitizer_bottle_B[0].rotation = [0, 0, 2.1834610503730873e-07]
hand_sanitizer_bottle_B[0].optimize = 2
facial_tissue[0].position = [4.699999809265137, 2.5799999237060547, 0.7649999856948853]
facial_tissue[0].rotation = [0, 0, 0.08482265381612356]
facial_tissue[0].optimize = 2
print_E[0].position = [5.050000190734863, 4.9850006103515625, 0.3499999940395355]
print_E[0].rotation = [0, 0, -1.5707962377328895]
print_E[0].optimize = 2
new_shades_card[0].position = [6.889999866485596, 1.590000033378601, 1.25]
new_shades_card[0].rotation = [0, 0, 3.1415913632941344]
new_shades_card[0].optimize = 2
mirror_A[0].position = [1.2999999523162842, 0.020000049844384193, 0.550000011920929]
mirror_A[0].rotation = [0, 0, 1.5707964009204145]
mirror_A[0].optimize = 2
manicure_hand_rest_pillow_A[0].position = [2.299999952316284, 1.7000000476837158, 0.800000011920929]
manicure_hand_rest_pillow_A[0].rotation = [0, 0, 0.0691152434500152]
manicure_hand_rest_pillow_A[0].optimize = 2
cotton_pad_B[0].position = [2.4700000286102295, 1.909999966621399, 0.7599999904632568]
cotton_pad_B[0].rotation = [0, 0, 0.0691152434500152]
cotton_pad_B[0].optimize = 2
hand_sanitizer_bottle_A[0].position = [6.579999923706055, 1.0800000429153442, 1.1950000524520874]
hand_sanitizer_bottle_A[0].rotation = [0, 0, 3.1415913632941344]
hand_sanitizer_bottle_A[0].optimize = 2
salon_client_chair_B[0].position = [1.399999976158142, 1.600000023841858, 0.5099999904632568]
salon_client_chair_B[0].rotation = [0, 0, 0.00942477746072377]
salon_client_chair_B[0].optimize = 2
cotton_pad_C[0].position = [4.460000038146973, 3.1700000762939453, 0.7599999904632568]
cotton_pad_C[0].rotation = [0, 0, 0.08482265381612356]
cotton_pad_C[0].optimize = 2
print_D[0].position = [3.950000047683716, 4.9850006103515625, 0.3499999940395355]
print_D[0].rotation = [0, 0, -1.5707962377328895]
print_D[0].optimize = 2
side_table[0].position = [1.159999966621399, 3.6500000953674316, 0.2750000059604645]
side_table[0].rotation = [0, 0, -3.8502938163614364e-08]
side_table[0].optimize = 2
screw_lid[0].position = [4.449999809265137, 3.0999999046325684, 0.7699999809265137]
screw_lid[0].rotation = [0, 0, 0.08482265381612356]
screw_lid[0].optimize = 2
technician_stool_A[0].position = [5.175000190734863, 2.950000047683716, 0.2750000059604645]
technician_stool_A[0].rotation = [0, 0, -3.1321678761290697]
technician_stool_A[0].optimize = 2
manicure_table_B[0].position = [4.599999904632568, 2.950000047683716, 0.3799999952316284]
manicure_table_B[0].rotation = [0, 0, 0.08482299704637274]
manicure_table_B[0].optimize = 2
manicure_tool_tray_B[0].position = [4.480000019073486, 3.390000104904175, 0.7799999713897705]
manicure_tool_tray_B[0].rotation = [0, 0, 0.08482265381612356]
manicure_tool_tray_B[0].optimize = 2
clock[0].position = [3.5, 0.024999983608722687, 0.1599999964237213]
clock[0].rotation = [0, 0, 1.5707964029978325]
clock[0].optimize = 2
tissue_dispenser_box[0].position = [6.510000228881836, 1.8200000524520874, 1.149999976158142]
tissue_dispenser_box[0].rotation = [0, 0, 3.1415913632941344]
tissue_dispenser_box[0].optimize = 2
cotton_pad_D[0].position = [4.472438335418701, 3.541318893432617, 0.7599999904632568]
cotton_pad_D[0].rotation = [0, 0, 0.08482265381612356]
cotton_pad_D[0].optimize = 2
wall_sign[0].position = [6.099999904632568, 4.979999542236328, 0.22499999403953552]
wall_sign[0].rotation = [0, 0, -1.5707962236748925]
wall_sign[0].optimize = 2
manicure_hand_rest_pillow_B[0].position = [4.670000076293945, 3.0299999713897705, 0.800000011920929]
manicure_hand_rest_pillow_B[0].rotation = [0, 0, 0.08482265381612356]
manicure_hand_rest_pillow_B[0].optimize = 2
display_shelf[0].position = [6.8000006675720215, 4.119999885559082, 0.8999999761581421]
display_shelf[0].rotation = [0, 0, 3.141592615212815]
display_shelf[0].optimize = 2
potted_plant[0].position = [0.3199999928474426, 0.3499999940395355, 0.22499999403953552]
potted_plant[0].rotation = [0, 0, 0.7948229285630478]
potted_plant[0].optimize = 2
business_card_holder[0].position = [6.849999904632568, 1.940000057220459, 1.1299999952316284]
business_card_holder[0].rotation = [0, 0, 3.1415913632941344]
business_card_holder[0].optimize = 2
card_payment_terminal[0].position = [6.800000190734863, 0.550000011920929, 1.1349999904632568]
card_payment_terminal[0].rotation = [0, 0, 3.1415913632941344]
card_payment_terminal[0].optimize = 2
wall_planter_A[0].position = [0.09000001102685928, 2.200000047683716, 0.14000000059604645]
wall_planter_A[0].rotation = [0, 0, 7.645252385107863e-08]
wall_planter_A[0].optimize = 2
technician_stool_B[0].position = [2.875, 1.600000023841858, 0.2750000059604645]
technician_stool_B[0].rotation = [0, 0, -3.1290262823329655]
technician_stool_B[0].optimize = 2
print_C[0].position = [2.8499999046325684, 4.9850006103515625, 0.3499999940395355]
print_C[0].rotation = [0, 0, -1.5707962377328895]
print_C[0].optimize = 2
nail_curing_lamp_A[0].position = [2.299999952316284, 1.2000000476837158, 0.8100000023841858]
nail_curing_lamp_A[0].rotation = [0, 0, 0.0691152434500152]
nail_curing_lamp_A[0].optimize = 2
nail_curing_lamp_B[0].position = [4.480000019073486, 2.569999933242798, 0.8100000023841858]
nail_curing_lamp_B[0].rotation = [0, 0, 0.08482265381612356]
nail_curing_lamp_B[0].optimize = 2
wall_planter_B[0].position = [6.909999847412109, 2.549999952316284, 0.14000000059604645]
wall_planter_B[0].rotation = [0, 0, -3.1415925702131005]
wall_planter_B[0].optimize = 2
mirror_B[0].position = [5.699999809265137, 0.020000049844384193, 0.550000011920929]
mirror_B[0].rotation = [0, 0, 1.5707964009204145]
mirror_B[0].optimize = 2
nail_polish[0].position = [4.449999809265137, 2.819999933242798, 0.7950000166893005]
nail_polish[0].rotation = [0, 0, 0.08482265381612356]
nail_polish[0].optimize = 2
nail_buffer_block_B[0].position = [4.71999979019165, 3.4800000190734863, 0.7749999761581421]
nail_buffer_block_B[0].rotation = [0, 0, 0.08482265381612356]
nail_buffer_block_B[0].optimize = 2
magazine[0].position = [1.1699999570846558, 3.559999942779541, 0.5550000071525574]
magazine[0].rotation = [0, 0, 2.1834610503730873e-07]
magazine[0].optimize = 2
hand_sanitizer_bottle_C[0].position = [6.829999923706055, 1.0800000429153442, 1.1950000524520874]
hand_sanitizer_bottle_C[0].rotation = [0, 0, 3.1415913632941344]
hand_sanitizer_bottle_C[0].optimize = 2
manicure_table_A[0].position = [2.299999952316284, 1.600000023841858, 0.3799999952316284]
manicure_table_A[0].rotation = [0, 0, 0.06911503821575936]
manicure_table_A[0].optimize = 2
reception_counter[0].position = [6.674999713897705, 1.25, 0.550000011920929]
reception_counter[0].rotation = [0, 0, -3.141592541282957]
reception_counter[0].optimize = 2
manicure_tool_tray_A[0].position = [2.299999952316284, 2.0199999809265137, 0.7799999713897705]
manicure_tool_tray_A[0].rotation = [0, 0, 0.0691152434500152]
manicure_tool_tray_A[0].optimize = 2

