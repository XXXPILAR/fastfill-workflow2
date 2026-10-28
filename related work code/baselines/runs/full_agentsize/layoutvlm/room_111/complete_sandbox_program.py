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
    Wall(corner1=[7.00, 0.00, 0.00], corner2=[7.00, 6.00, 0.00]),
    Wall(corner1=[7.00, 6.00, 0.00], corner2=[0.00, 6.00, 0.00]),
    Wall(corner1=[0.00, 6.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
waiting_armchair_A = Assets(description="A grey sloping armchair with light brown legs and a back cushion.", size=[0.86, 0.82, 0.88], placements=[AssetInstance() for _ in range(1)])
magazine = Assets(description="A red and blue hardback book titled 'akbar's dream'.", size=[0.15, 0.22, 0.03], placements=[AssetInstance() for _ in range(1)])
small_potted_plant_A = Assets(description="A bunch of big leaves inside of a white pot.", size=[0.38, 0.38, 0.55], placements=[AssetInstance() for _ in range(1)])
file_box = Assets(description="A red microwave oven.", size=[0.28, 0.38, 0.27], placements=[AssetInstance() for _ in range(1)])
waiting_armchair_B = Assets(description="A grey sloping armchair with light brown legs and a back cushion.", size=[0.86, 0.82, 0.88], placements=[AssetInstance() for _ in range(1)])
reception_task_chair_A = Assets(description="A blue upholstered office chair that swivels on a cylinder, no arms, an adjustable seat, and a base with four casters.", size=[0.58, 0.58, 0.92], placements=[AssetInstance() for _ in range(1)])
low_storage_cabinet = Assets(description="Wood cabinet with two dark wood doors.", size=[0.45, 1.20, 0.78], placements=[AssetInstance() for _ in range(1)])
reception_counter = Assets(description="A long standing desk with two computer monitors on it and a plant.", size=[0.85, 2.80, 1.15], placements=[AssetInstance() for _ in range(1)])
freestanding_sign_stand_A = Assets(description="A stand alone sign with a barcode and logo on one side.", size=[0.40, 0.45, 1.45], placements=[AssetInstance() for _ in range(1)])
reception_task_chair_B = Assets(description="A blue upholstered office chair that swivels on a cylinder, no arms, an adjustable seat, and a base with four casters.", size=[0.58, 0.58, 0.92], placements=[AssetInstance() for _ in range(1)])
company_logo_panel = Assets(description="It is a backboard without a net.", size=[0.08, 1.80, 0.75], placements=[AssetInstance() for _ in range(1)])
waste_bin = Assets(description="A cream colored trash can.", size=[0.30, 0.30, 0.45], placements=[AssetInstance() for _ in range(1)])
freestanding_sign_stand_B = Assets(description="A stand alone sign with a barcode and logo on one side.", size=[0.40, 0.45, 1.45], placements=[AssetInstance() for _ in range(1)])
small_side_table_A = Assets(description="A dark brown wooden stool with pointy legs.", size=[0.42, 0.42, 0.48], placements=[AssetInstance() for _ in range(1)])
magazine_stack_A = Assets(description="Three books, each a different hue of blue and with a red ribbon bookmark, lie atop one another.", size=[0.21, 0.28, 0.09], placements=[AssetInstance() for _ in range(1)])
waiting_coffee_table = Assets(description="waiting coffee table", size=[0.70, 1.25, 0.42], placements=[AssetInstance() for _ in range(1)])
small_potted_plant_B = Assets(description="A bunch of big leaves inside of a white pot.", size=[0.38, 0.38, 0.55], placements=[AssetInstance() for _ in range(1)])
small_side_table_B = Assets(description="A dark brown wooden stool with pointy legs.", size=[0.42, 0.42, 0.48], placements=[AssetInstance() for _ in range(1)])
magazine_stack_B = Assets(description="Three purple books in a stack.", size=[0.20, 0.27, 0.09], placements=[AssetInstance() for _ in range(1)])
waiting_armchair_C = Assets(description="A grey sloping armchair with light brown legs and a back cushion.", size=[0.86, 0.82, 0.88], placements=[AssetInstance() for _ in range(1)])
magazine_stack_C = Assets(description="A book with a grey covered banded to a blue cover book.", size=[0.20, 0.27, 0.06], placements=[AssetInstance() for _ in range(1)])
brochure_holder = Assets(description="A flat screen television set with a blue screen.", size=[0.18, 0.32, 0.38], placements=[AssetInstance() for _ in range(1)])
pen_holder = Assets(description="A wire frame cup for holding pencils.", size=[0.10, 0.10, 0.13], placements=[AssetInstance() for _ in range(1)])
decorative_tray = Assets(description="A square shaped white plate that's black along the edges with an asian style platter presented on it.", size=[0.35, 0.35, 0.06], placements=[AssetInstance() for _ in range(1)])
side_console_table = Assets(description="A long thin table with three planks on the bottom.", size=[0.38, 1.40, 0.82], placements=[AssetInstance() for _ in range(1)])
coat_umbrella_stand = Assets(description="mannequin wearing a colorful, abstract-designed jacket on a white stand.", size=[0.55, 0.55, 1.75], placements=[AssetInstance() for _ in range(1)])

waiting_armchair_A[0].instance_id = 'waiting_armchair_A_0'
magazine[0].instance_id = 'magazine_0'
small_potted_plant_A[0].instance_id = 'small_potted_plant_A_0'
file_box[0].instance_id = 'file_box_0'
waiting_armchair_B[0].instance_id = 'waiting_armchair_B_0'
reception_task_chair_A[0].instance_id = 'reception_task_chair_A_0'
low_storage_cabinet[0].instance_id = 'low_storage_cabinet_0'
reception_counter[0].instance_id = 'reception_counter_0'
freestanding_sign_stand_A[0].instance_id = 'freestanding_sign_stand_A_0'
reception_task_chair_B[0].instance_id = 'reception_task_chair_B_0'
company_logo_panel[0].instance_id = 'company_logo_panel_0'
waste_bin[0].instance_id = 'waste_bin_0'
freestanding_sign_stand_B[0].instance_id = 'freestanding_sign_stand_B_0'
small_side_table_A[0].instance_id = 'small_side_table_A_0'
magazine_stack_A[0].instance_id = 'magazine_stack_A_0'
waiting_coffee_table[0].instance_id = 'waiting_coffee_table_0'
small_potted_plant_B[0].instance_id = 'small_potted_plant_B_0'
small_side_table_B[0].instance_id = 'small_side_table_B_0'
magazine_stack_B[0].instance_id = 'magazine_stack_B_0'
waiting_armchair_C[0].instance_id = 'waiting_armchair_C_0'
magazine_stack_C[0].instance_id = 'magazine_stack_C_0'
brochure_holder[0].instance_id = 'brochure_holder_0'
pen_holder[0].instance_id = 'pen_holder_0'
decorative_tray[0].instance_id = 'decorative_tray_0'
side_console_table[0].instance_id = 'side_console_table_0'
coat_umbrella_stand[0].instance_id = 'coat_umbrella_stand_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

waiting_armchair_A[0].position = [0.6644904924965747, 4.794313265926435, 0.44]
waiting_armchair_A[0].rotation = [0, 0, 0]
magazine[0].position = [2.4602215010105324, 0.12033507399303334, 0.0125]
magazine[0].rotation = [0, 0, 0]
small_potted_plant_A[0].position = [6.035679900188577, 4.498798055253912, 0.275]
small_potted_plant_A[0].rotation = [0, 0, 0]
file_box[0].position = [0.6176306042840928, 3.1167848481893836, 0.135]
file_box[0].rotation = [0, 0, 0]
waiting_armchair_B[0].position = [5.677120975073575, 3.0041618553708416, 0.44]
waiting_armchair_B[0].rotation = [0, 0, 0]
reception_task_chair_A[0].position = [5.70134028831078, 1.124114008309691, 0.46]
reception_task_chair_A[0].rotation = [0, 0, 0]
low_storage_cabinet[0].position = [5.629062840037184, 4.522219064165137, 0.39]
low_storage_cabinet[0].rotation = [0, 0, 0]
reception_counter[0].position = [1.9615492496509517, 5.238816310785288, 0.575]
reception_counter[0].rotation = [0, 0, 0]
freestanding_sign_stand_A[0].position = [3.462140985388354, 1.230167438756712, 0.725]
freestanding_sign_stand_A[0].rotation = [0, 0, 0]
reception_task_chair_B[0].position = [4.076141777012314, 4.673310503902689, 0.46]
reception_task_chair_B[0].rotation = [0, 0, 0]
company_logo_panel[0].position = [2.3796968351037875, 5.746152684032071, 0.375]
company_logo_panel[0].rotation = [0, 0, 0]
waste_bin[0].position = [6.575619099815848, 2.4164149331120273, 0.225]
waste_bin[0].rotation = [0, 0, 0]
freestanding_sign_stand_B[0].position = [0.9430887206565792, 5.046158489370103, 0.725]
freestanding_sign_stand_B[0].rotation = [0, 0, 0]
small_side_table_A[0].position = [6.048327167298329, 2.4243394281934103, 0.24]
small_side_table_A[0].rotation = [0, 0, 0]
magazine_stack_A[0].position = [2.4848136173417856, 1.0376062939772204, 0.045]
magazine_stack_A[0].rotation = [0, 0, 0]
waiting_coffee_table[0].position = [5.002305669827707, 1.3036264975557106, 0.21]
waiting_coffee_table[0].rotation = [0, 0, 0]
small_potted_plant_B[0].position = [2.599316804196258, 2.3601271301679128, 0.275]
small_potted_plant_B[0].rotation = [0, 0, 0]
small_side_table_B[0].position = [0.11060512145867607, 0.433726020071437, 0.24]
small_side_table_B[0].rotation = [0, 0, 0]
magazine_stack_B[0].position = [1.1019244879397725, 3.2101701422311275, 0.045]
magazine_stack_B[0].rotation = [0, 0, 0]
waiting_armchair_C[0].position = [0.610851582906367, 2.2838904705712313, 0.44]
waiting_armchair_C[0].rotation = [0, 0, 0]
magazine_stack_C[0].position = [0.36313397536669234, 2.453020289721976, 0.03]
magazine_stack_C[0].rotation = [0, 0, 0]
brochure_holder[0].position = [1.7018755080540666, 0.37048440661908466, 0.19]
brochure_holder[0].rotation = [0, 0, 0]
pen_holder[0].position = [6.124070983973575, 1.4561279354613783, 0.065]
pen_holder[0].rotation = [0, 0, 0]
decorative_tray[0].position = [3.953142216609849, 0.6924764799370984, 0.03]
decorative_tray[0].rotation = [0, 0, 0]
side_console_table[0].position = [4.742054244482919, 5.3533613269715214, 0.41]
side_console_table[0].rotation = [0, 0, 0]
coat_umbrella_stand[0].position = [1.4726634412609558, 5.451511574131905, 0.875]
coat_umbrella_stand[0].rotation = [0, 0, 0]
waiting_armchair_A[0].position = [0.6644904924965747, 4.794313265926435, 0.44]
waiting_armchair_A[0].rotation = [0, 0, 0]
magazine[0].position = [2.4602215010105324, 0.12033507399303334, 0.0125]
magazine[0].rotation = [0, 0, 0]
small_potted_plant_A[0].position = [6.035679900188577, 4.498798055253912, 0.275]
small_potted_plant_A[0].rotation = [0, 0, 0]
file_box[0].position = [0.6176306042840928, 3.1167848481893836, 0.135]
file_box[0].rotation = [0, 0, 0]
waiting_armchair_B[0].position = [5.677120975073575, 3.0041618553708416, 0.44]
waiting_armchair_B[0].rotation = [0, 0, 0]
reception_task_chair_A[0].position = [5.70134028831078, 1.124114008309691, 0.46]
reception_task_chair_A[0].rotation = [0, 0, 0]
low_storage_cabinet[0].position = [5.629062840037184, 4.522219064165137, 0.39]
low_storage_cabinet[0].rotation = [0, 0, 0]
reception_counter[0].position = [1.9615492496509517, 5.238816310785288, 0.575]
reception_counter[0].rotation = [0, 0, 0]
freestanding_sign_stand_A[0].position = [3.462140985388354, 1.230167438756712, 0.725]
freestanding_sign_stand_A[0].rotation = [0, 0, 0]
reception_task_chair_B[0].position = [4.076141777012314, 4.673310503902689, 0.46]
reception_task_chair_B[0].rotation = [0, 0, 0]
company_logo_panel[0].position = [2.3796968351037875, 5.746152684032071, 0.375]
company_logo_panel[0].rotation = [0, 0, 0]
waste_bin[0].position = [6.575619099815848, 2.4164149331120273, 0.225]
waste_bin[0].rotation = [0, 0, 0]
freestanding_sign_stand_B[0].position = [0.9430887206565792, 5.046158489370103, 0.725]
freestanding_sign_stand_B[0].rotation = [0, 0, 0]
small_side_table_A[0].position = [6.048327167298329, 2.4243394281934103, 0.24]
small_side_table_A[0].rotation = [0, 0, 0]
magazine_stack_A[0].position = [2.4848136173417856, 1.0376062939772204, 0.045]
magazine_stack_A[0].rotation = [0, 0, 0]
waiting_coffee_table[0].position = [5.002305669827707, 1.3036264975557106, 0.21]
waiting_coffee_table[0].rotation = [0, 0, 0]
small_potted_plant_B[0].position = [2.599316804196258, 2.3601271301679128, 0.275]
small_potted_plant_B[0].rotation = [0, 0, 0]
small_side_table_B[0].position = [0.11060512145867607, 0.433726020071437, 0.24]
small_side_table_B[0].rotation = [0, 0, 0]
magazine_stack_B[0].position = [1.1019244879397725, 3.2101701422311275, 0.045]
magazine_stack_B[0].rotation = [0, 0, 0]
waiting_armchair_C[0].position = [0.610851582906367, 2.2838904705712313, 0.44]
waiting_armchair_C[0].rotation = [0, 0, 0]
magazine_stack_C[0].position = [0.36313397536669234, 2.453020289721976, 0.03]
magazine_stack_C[0].rotation = [0, 0, 0]
brochure_holder[0].position = [1.7018755080540666, 0.37048440661908466, 0.19]
brochure_holder[0].rotation = [0, 0, 0]
pen_holder[0].position = [6.124070983973575, 1.4561279354613783, 0.065]
pen_holder[0].rotation = [0, 0, 0]
decorative_tray[0].position = [3.953142216609849, 0.6924764799370984, 0.03]
decorative_tray[0].rotation = [0, 0, 0]
side_console_table[0].position = [4.742054244482919, 5.3533613269715214, 0.41]
side_console_table[0].rotation = [0, 0, 0]
coat_umbrella_stand[0].position = [1.4726634412609558, 5.451511574131905, 0.875]
coat_umbrella_stand[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the waiting area on the left and the reception workspace on the
# right, leaving clear circulation through the middle and along the windows.

# Waiting-area furniture.
waiting_armchair_A[0].position = [1.20, 3.00, 0.44]
waiting_armchair_A[0].rotation = [0, 0, radians(0)]

small_side_table_A[0].position = [1.20, 2.15, 0.24]
small_side_table_A[0].rotation = [0, 0, radians(0)]

small_side_table_B[0].position = [1.20, 3.85, 0.24]
small_side_table_B[0].rotation = [0, 0, radians(0)]

waiting_coffee_table[0].position = [2.40, 3.00, 0.21]
waiting_coffee_table[0].rotation = [0, 0, radians(180)]

waiting_armchair_B[0].position = [2.80, 4.55, 0.44]
waiting_armchair_B[0].rotation = [0, 0, radians(-90)]

waiting_armchair_C[0].position = [2.80, 1.45, 0.44]
waiting_armchair_C[0].rotation = [0, 0, radians(90)]

# The waste bin is directly in front of waiting_armchair_A, as required.
waste_bin[0].position = [4.15, 3.00, 0.225]
waste_bin[0].rotation = [0, 0, radians(180)]

# Objects placed on the waiting coffee table. Their z coordinates put their
# bottoms at the tabletop height of 0.42 m.
small_potted_plant_A[0].position = [2.25, 3.20, 0.695]
small_potted_plant_A[0].rotation = [0, 0, radians(180)]

magazine[0].position = [2.57, 3.38, 0.435]
magazine[0].rotation = [0, 0, radians(180)]

magazine_stack_A[0].position = [2.20, 2.70, 0.465]
magazine_stack_A[0].rotation = [0, 0, radians(180)]

magazine_stack_C[0].position = [2.55, 2.72, 0.45]
magazine_stack_C[0].rotation = [0, 0, radians(180)]

# Place one compact item on each side table.
magazine_stack_B[0].position = [1.20, 2.15, 0.525]
magazine_stack_B[0].rotation = [0, 0, radians(0)]

small_potted_plant_B[0].position = [1.20, 3.85, 0.755]
small_potted_plant_B[0].rotation = [0, 0, radians(0)]

# Reception counter and employee chairs. The counter faces the waiting area,
# while the task chairs sit behind it and face toward the counter.
reception_counter[0].position = [5.25, 3.30, 0.575]
reception_counter[0].rotation = [0, 0, radians(180)]

reception_task_chair_A[0].position = [6.15, 2.55, 0.46]
reception_task_chair_A[0].rotation = [0, 0, radians(180)]

reception_task_chair_B[0].position = [6.15, 3.95, 0.46]
reception_task_chair_B[0].rotation = [0, 0, radians(180)]

# Reception accessories sit on the counter, away from its integrated monitors.
brochure_holder[0].position = [5.25, 2.25, 1.34]
brochure_holder[0].rotation = [0, 0, radians(180)]

pen_holder[0].position = [5.25, 4.25, 1.215]
pen_holder[0].rotation = [0, 0, radians(180)]

# Storage occupies the lower part of the east wall, clear of the northern
# windows. The file box is placed on its top.
low_storage_cabinet[0].position = [6.775, 0.80, 0.39]
low_storage_cabinet[0].rotation = [0, 0, radians(180)]

file_box[0].position = [6.775, 0.80, 0.915]
file_box[0].rotation = [0, 0, radians(180)]

# Wall-side decor and amenities. None of these obstructs the north windows.
company_logo_panel[0].position = [6.96, 5.05, 0.375]
company_logo_panel[0].rotation = [0, 0, radians(180)]

side_console_table[0].position = [0.19, 5.00, 0.41]
side_console_table[0].rotation = [0, 0, radians(0)]

decorative_tray[0].position = [0.19, 5.00, 0.85]
decorative_tray[0].rotation = [0, 0, radians(0)]

coat_umbrella_stand[0].position = [0.45, 0.45, 0.875]
coat_umbrella_stand[0].rotation = [0, 0, radians(45)]

# Signs mark the approach to reception while retaining a clear path between
# the entrance side of the room and the counter.
freestanding_sign_stand_A[0].position = [3.55, 0.45, 0.725]
freestanding_sign_stand_A[0].rotation = [0, 0, radians(90)]

freestanding_sign_stand_B[0].position = [4.30, 0.45, 0.725]
freestanding_sign_stand_B[0].rotation = [0, 0, radians(90)]


# Pin every asset near its intended location. These high-priority
# position-based constraints preserve the non-overlapping functional layout.
solver.distance_constraint(waiting_armchair_A[0], AssetInstance(position=[1.20, 3.00, 0.44]), 0, 0, weight=10)
solver.distance_constraint(small_side_table_A[0], AssetInstance(position=[1.20, 2.15, 0.24]), 0, 0, weight=10)
solver.distance_constraint(small_side_table_B[0], AssetInstance(position=[1.20, 3.85, 0.24]), 0, 0, weight=10)
solver.distance_constraint(waiting_coffee_table[0], AssetInstance(position=[2.40, 3.00, 0.21]), 0, 0, weight=10)
solver.distance_constraint(waiting_armchair_B[0], AssetInstance(position=[2.80, 4.55, 0.44]), 0, 0, weight=10)
solver.distance_constraint(waiting_armchair_C[0], AssetInstance(position=[2.80, 1.45, 0.44]), 0, 0, weight=10)
solver.distance_constraint(waste_bin[0], AssetInstance(position=[4.15, 3.00, 0.225]), 0, 0, weight=10)

solver.distance_constraint(small_potted_plant_A[0], AssetInstance(position=[2.25, 3.20, 0.695]), 0, 0, weight=10)
solver.distance_constraint(magazine[0], AssetInstance(position=[2.57, 3.38, 0.435]), 0, 0, weight=10)
solver.distance_constraint(magazine_stack_A[0], AssetInstance(position=[2.20, 2.70, 0.465]), 0, 0, weight=10)
solver.distance_constraint(magazine_stack_C[0], AssetInstance(position=[2.55, 2.72, 0.45]), 0, 0, weight=10)
solver.distance_constraint(magazine_stack_B[0], AssetInstance(position=[1.20, 2.15, 0.525]), 0, 0, weight=10)
solver.distance_constraint(small_potted_plant_B[0], AssetInstance(position=[1.20, 3.85, 0.755]), 0, 0, weight=10)

solver.distance_constraint(reception_counter[0], AssetInstance(position=[5.25, 3.30, 0.575]), 0, 0, weight=10)
solver.distance_constraint(reception_task_chair_A[0], AssetInstance(position=[6.15, 2.55, 0.46]), 0, 0, weight=10)
solver.distance_constraint(reception_task_chair_B[0], AssetInstance(position=[6.15, 3.95, 0.46]), 0, 0, weight=10)
solver.distance_constraint(brochure_holder[0], AssetInstance(position=[5.25, 2.25, 1.34]), 0, 0, weight=10)
solver.distance_constraint(pen_holder[0], AssetInstance(position=[5.25, 4.25, 1.215]), 0, 0, weight=10)

solver.distance_constraint(low_storage_cabinet[0], AssetInstance(position=[6.775, 0.80, 0.39]), 0, 0, weight=10)
solver.distance_constraint(file_box[0], AssetInstance(position=[6.775, 0.80, 0.915]), 0, 0, weight=10)
solver.distance_constraint(company_logo_panel[0], AssetInstance(position=[6.96, 5.05, 0.375]), 0, 0, weight=10)
solver.distance_constraint(side_console_table[0], AssetInstance(position=[0.19, 5.00, 0.41]), 0, 0, weight=10)
solver.distance_constraint(decorative_tray[0], AssetInstance(position=[0.19, 5.00, 0.85]), 0, 0, weight=10)
solver.distance_constraint(coat_umbrella_stand[0], AssetInstance(position=[0.45, 0.45, 0.875]), 0, 0, weight=10)
solver.distance_constraint(freestanding_sign_stand_A[0], AssetInstance(position=[3.55, 0.45, 0.725]), 0, 0, weight=10)
solver.distance_constraint(freestanding_sign_stand_B[0], AssetInstance(position=[4.30, 0.45, 0.725]), 0, 0, weight=10)


# Required support relationships for all small objects.
solver.on_top_of(small_potted_plant_A[0], waiting_coffee_table[0])
solver.on_top_of(magazine[0], waiting_coffee_table[0])
solver.on_top_of(magazine_stack_A[0], waiting_coffee_table[0])
solver.on_top_of(magazine_stack_C[0], waiting_coffee_table[0])
solver.on_top_of(magazine_stack_B[0], small_side_table_A[0])
solver.on_top_of(small_potted_plant_B[0], small_side_table_B[0])
solver.on_top_of(brochure_holder[0], reception_counter[0])
solver.on_top_of(pen_holder[0], reception_counter[0])
solver.on_top_of(file_box[0], low_storage_cabinet[0])
solver.on_top_of(decorative_tray[0], side_console_table[0])


# Maintain the required "armchair between side tables" composition.
solver.distance_constraint(small_side_table_A[0], waiting_armchair_A[0], 0.80, 0.90, weight=5)
solver.distance_constraint(small_side_table_B[0], waiting_armchair_A[0], 0.80, 0.90, weight=5)

# Orient all seating toward a meaningful focal point. In particular,
# waiting_armchair_A faces the waste bin as explicitly requested.
solver.point_towards(waiting_armchair_A[0], waste_bin[0])
solver.point_towards(waiting_armchair_B[0], waiting_coffee_table[0])
solver.point_towards(waiting_armchair_C[0], waiting_coffee_table[0])
solver.point_towards(reception_task_chair_A[0], reception_counter[0])
solver.point_towards(reception_task_chair_B[0], reception_counter[0])
solver.point_towards(reception_counter[0], waiting_coffee_table[0])
solver.point_towards(waste_bin[0], waiting_armchair_A[0])

# Orientation constraints for the waiting tables and all tabletop objects.
solver.align_with(waiting_coffee_table[0], reception_counter[0])
solver.point_towards(small_side_table_A[0], waiting_armchair_A[0])
solver.point_towards(small_side_table_B[0], waiting_armchair_A[0])
solver.align_with(small_potted_plant_A[0], waiting_coffee_table[0])
solver.align_with(magazine[0], waiting_coffee_table[0])
solver.align_with(magazine_stack_A[0], waiting_coffee_table[0])
solver.align_with(magazine_stack_C[0], waiting_coffee_table[0])
solver.align_with(magazine_stack_B[0], small_side_table_A[0])
solver.align_with(small_potted_plant_B[0], small_side_table_B[0])

# Keep the wall furniture flush with the appropriate walls and oriented into
# the room. The east-wall pieces remain below/beside the window region.
solver.against_wall(low_storage_cabinet[0], walls[1])
solver.against_wall(company_logo_panel[0], walls[1])
solver.against_wall(side_console_table[0], walls[3])

solver.align_with(low_storage_cabinet[0], reception_counter[0])
solver.align_with(file_box[0], low_storage_cabinet[0])
solver.align_with(company_logo_panel[0], reception_counter[0])
solver.point_towards(side_console_table[0], waiting_coffee_table[0])
solver.align_with(decorative_tray[0], side_console_table[0])

# Complete orientation constraints for reception accessories and freestanding
# entry amenities.
solver.align_with(brochure_holder[0], reception_counter[0])
solver.align_with(pen_holder[0], reception_counter[0])
solver.point_towards(freestanding_sign_stand_A[0], reception_counter[0])
solver.point_towards(freestanding_sign_stand_B[0], reception_counter[0])
solver.point_towards(coat_umbrella_stand[0], waiting_coffee_table[0])

solver.constraints = []
brochure_holder[0].position = [5.25, 2.25, 1.3399999141693115]
brochure_holder[0].rotation = [0, 0, -3.0976311481141323]
brochure_holder[0].optimize = 2
side_console_table[0].position = [0.18999622762203217, 5.0, 0.4099999964237213]
side_console_table[0].rotation = [0, 0, -9.223114880209484e-06]
side_console_table[0].optimize = 2
reception_task_chair_B[0].position = [6.150000095367432, 3.950000047683716, 0.46000000834465027]
reception_task_chair_B[0].rotation = [0, 0, -3.1321678761290697]
reception_task_chair_B[0].optimize = 2
magazine_stack_B[0].position = [1.2000000476837158, 2.1500000953674316, 0.5249999761581421]
magazine_stack_B[0].rotation = [0, 0, 0.8208604515163849]
magazine_stack_B[0].optimize = 2
coat_umbrella_stand[0].position = [0.44999998807907104, 0.44999998807907104, 0.875]
coat_umbrella_stand[0].rotation = [0, 0, 0.7948229285630478]
coat_umbrella_stand[0].optimize = 2
waiting_coffee_table[0].position = [2.4000000953674316, 3.0, 0.20999999344348907]
waiting_coffee_table[0].rotation = [0, 0, -3.0976122480275303]
waiting_coffee_table[0].optimize = 2
magazine_stack_A[0].position = [2.200000047683716, 2.700000047683716, 0.4649999737739563]
magazine_stack_A[0].rotation = [0, 0, -3.0976036789462866]
magazine_stack_A[0].optimize = 2
file_box[0].position = [6.775000095367432, 0.800000011920929, 0.9149999618530273]
file_box[0].rotation = [0, 0, 3.1415863715015067]
file_box[0].optimize = 2
pen_holder[0].position = [5.25, 4.25, 1.2149999141693115]
pen_holder[0].rotation = [0, 0, -3.0976311481141323]
pen_holder[0].optimize = 2
decorative_tray[0].position = [0.1899999976158142, 5.0, 0.8499999642372131]
decorative_tray[0].rotation = [0, 0, -6.184390331805825e-06]
decorative_tray[0].optimize = 2
company_logo_panel[0].position = [6.959995746612549, 5.050000190734863, 0.375]
company_logo_panel[0].rotation = [0, 0, 3.1415875189412623]
company_logo_panel[0].optimize = 2
reception_task_chair_A[0].position = [6.150000095367432, 2.549999952316284, 0.46000000834465027]
reception_task_chair_A[0].rotation = [0, 0, -3.1321678761290697]
reception_task_chair_A[0].optimize = 2
magazine[0].position = [2.569999933242798, 3.380000114440918, 0.4349999725818634]
magazine[0].rotation = [0, 0, -3.0976036789462866]
magazine[0].optimize = 2
waiting_armchair_C[0].position = [2.799999952316284, 1.4500000476837158, 0.4399999976158142]
waiting_armchair_C[0].rotation = [0, 0, 1.6003737972216285]
waiting_armchair_C[0].optimize = 2
low_storage_cabinet[0].position = [6.774995803833008, 0.800000011920929, 0.38999998569488525]
low_storage_cabinet[0].rotation = [0, 0, 3.141583437710412]
low_storage_cabinet[0].optimize = 2
magazine_stack_C[0].position = [2.549999952316284, 2.7200000286102295, 0.44999998807907104]
magazine_stack_C[0].rotation = [0, 0, -3.0976036789462866]
magazine_stack_C[0].optimize = 2
waiting_armchair_B[0].position = [2.799999952316284, 4.550000190734863, 0.4399999976158142]
waiting_armchair_B[0].rotation = [0, 0, -1.5902252347860593]
waiting_armchair_B[0].optimize = 2
reception_counter[0].position = [5.25, 3.299999952316284, 0.574999988079071]
reception_counter[0].rotation = [0, 0, -3.097610355149486]
reception_counter[0].optimize = 2
small_potted_plant_A[0].position = [2.25, 3.200000047683716, 0.6949999928474426]
small_potted_plant_A[0].rotation = [0, 0, -3.0976036789462866]
small_potted_plant_A[0].optimize = 2
waiting_armchair_A[0].position = [1.2000000476837158, 3.0, 0.4399999976158142]
waiting_armchair_A[0].rotation = [0, 0, 0.025132740109855806]
waiting_armchair_A[0].optimize = 2
waste_bin[0].position = [4.150000095367432, 3.0, 0.22499999403953552]
waste_bin[0].rotation = [0, 0, -3.1290262823329655]
waste_bin[0].optimize = 2
small_potted_plant_B[0].position = [1.2000000476837158, 3.8499999046325684, 0.7549999952316284]
small_potted_plant_B[0].rotation = [0, 0, -0.81450570232812]
small_potted_plant_B[0].optimize = 2
freestanding_sign_stand_A[0].position = [3.549999952316284, 0.44999998807907104, 0.7250000238418579]
freestanding_sign_stand_A[0].rotation = [0, 0, 1.285098641198745]
freestanding_sign_stand_A[0].optimize = 2
small_side_table_B[0].position = [1.2000000476837158, 3.8499999046325684, 0.23999999463558197]
small_side_table_B[0].rotation = [0, 0, -0.8152167182719853]
small_side_table_B[0].optimize = 2
small_side_table_A[0].position = [1.2000000476837158, 2.1500000953674316, 0.23999999463558197]
small_side_table_A[0].rotation = [0, 0, 0.8212396893987504]
small_side_table_A[0].optimize = 2
freestanding_sign_stand_B[0].position = [4.300000190734863, 0.44999998807907104, 0.7250000238418579]
freestanding_sign_stand_B[0].rotation = [0, 0, 1.4603787350882749]
freestanding_sign_stand_B[0].optimize = 2

