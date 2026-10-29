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
    Wall(corner1=[0.00, 12.00, 0.00], corner2=[1.00, 12.00, 0.00]),
    Wall(corner1=[1.00, 12.00, 0.00], corner2=[1.00, 0.00, 0.00]),
    Wall(corner1=[1.00, 0.00, 0.00], corner2=[8.00, 0.00, 0.00]),
    Wall(corner1=[8.00, 0.00, 0.00], corner2=[8.00, 7.00, 0.00]),
    Wall(corner1=[8.00, 7.00, 0.00], corner2=[12.00, 7.00, 0.00]),
    Wall(corner1=[12.00, 7.00, 0.00], corner2=[12.00, 10.00, 0.00]),
    Wall(corner1=[12.00, 10.00, 0.00], corner2=[8.00, 10.00, 0.00]),
    Wall(corner1=[8.00, 10.00, 0.00], corner2=[8.00, 13.00, 0.00]),
    Wall(corner1=[8.00, 13.00, 0.00], corner2=[0.00, 13.00, 0.00]),
    Wall(corner1=[0.00, 13.00, 0.00], corner2=[0.00, 12.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
pen_holder_A = Assets(description="A wire frame cup for holding pencils.", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
lounge_sofa_A = Assets(description="A modern gray sofa with three seats.", size=[0.95, 2.30, 0.82], placements=[AssetInstance() for _ in range(1)])
meeting_chair_A = Assets(description="A black chair with thin legs.", size=[0.55, 0.50, 0.82], placements=[AssetInstance() for _ in range(1)])
standing_bar_counter = Assets(description="A long wood table.", size=[0.75, 3.00, 1.05], placements=[AssetInstance() for _ in range(1)])
side_coffee_table = Assets(description="side coffee table", size=[0.65, 0.80, 0.50], placements=[AssetInstance() for _ in range(1)])
small_round_meeting_table_A = Assets(description="small round meeting table", size=[1.10, 1.10, 0.75], placements=[AssetInstance() for _ in range(1)])
wayfinding_sign_A = Assets(description="A green and white exit sign with an arrow and a man running, pointing towards the door.", size=[0.03, 0.35, 0.18], placements=[AssetInstance() for _ in range(1)])
lounge_sofa_B = Assets(description="A modern gray sofa with three seats.", size=[0.95, 2.30, 0.82], placements=[AssetInstance() for _ in range(1)])
bar_stool_A = Assets(description="bar stool", size=[0.43, 0.43, 0.75], placements=[AssetInstance() for _ in range(1)])
meeting_chair_B = Assets(description="A black chair with thin legs.", size=[0.55, 0.50, 0.82], placements=[AssetInstance() for _ in range(1)])
floor_plan_display = Assets(description="A white rectangular poster with black blue and orange marks and irregular writing.", size=[0.03, 0.90, 0.65], placements=[AssetInstance() for _ in range(1)])
table_lamp = Assets(description="A wooden table lamp on a small wooden table.", size=[0.28, 0.28, 0.45], placements=[AssetInstance() for _ in range(1)])
small_round_meeting_table_B = Assets(description="small round meeting table", size=[1.10, 1.10, 0.75], placements=[AssetInstance() for _ in range(1)])
notebook_A = Assets(description="A black book with silver trim.", size=[0.21, 0.15, 0.02], placements=[AssetInstance() for _ in range(1)])
coffee_mug = Assets(description="A mug with a handle that is an dark orange color.", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
bar_stool_B = Assets(description="bar stool", size=[0.43, 0.43, 0.75], placements=[AssetInstance() for _ in range(1)])
wayfinding_sign_B = Assets(description="A green and white exit sign with an arrow and a man running, pointing towards the door.", size=[0.03, 0.35, 0.18], placements=[AssetInstance() for _ in range(1)])
meeting_chair_C = Assets(description="A black chair with thin legs.", size=[0.55, 0.50, 0.82], placements=[AssetInstance() for _ in range(1)])
wayfinding_sign_C = Assets(description="A green and white exit sign with an arrow and a man running, pointing towards the door.", size=[0.03, 0.35, 0.18], placements=[AssetInstance() for _ in range(1)])
wall_info_panel = Assets(description="A poster of blueprints for a picture frame.", size=[0.03, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
small_potted_plant = Assets(description="A bunch of big leaves inside of a white pot.", size=[0.40, 0.40, 0.55], placements=[AssetInstance() for _ in range(1)])
wayfinding_sign_D = Assets(description="A green and white exit sign with an arrow and a man running, pointing towards the door.", size=[0.03, 0.35, 0.18], placements=[AssetInstance() for _ in range(1)])
bar_stool_C = Assets(description="bar stool", size=[0.43, 0.43, 0.75], placements=[AssetInstance() for _ in range(1)])
meeting_chair_D = Assets(description="A black chair with thin legs.", size=[0.55, 0.50, 0.82], placements=[AssetInstance() for _ in range(1)])
notebook_B = Assets(description="A black book with silver trim.", size=[0.21, 0.15, 0.02], placements=[AssetInstance() for _ in range(1)])
notebook_C = Assets(description="A pink spiral notebook with a green leaf on it.", size=[0.30, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
pen_holder_B = Assets(description="A wire frame cup for holding pencils.", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="A brown book with silver corners.", size=[0.24, 0.17, 0.03], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="It is a hard cover book with a blue cover.", size=[0.25, 0.18, 0.04], placements=[AssetInstance() for _ in range(1)])
notebook_D = Assets(description="A pink spiral notebook with a green leaf on it.", size=[0.30, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])

pen_holder_A[0].instance_id = 'pen_holder_A_0'
lounge_sofa_A[0].instance_id = 'lounge_sofa_A_0'
meeting_chair_A[0].instance_id = 'meeting_chair_A_0'
standing_bar_counter[0].instance_id = 'standing_bar_counter_0'
side_coffee_table[0].instance_id = 'side_coffee_table_0'
small_round_meeting_table_A[0].instance_id = 'small_round_meeting_table_A_0'
wayfinding_sign_A[0].instance_id = 'wayfinding_sign_A_0'
lounge_sofa_B[0].instance_id = 'lounge_sofa_B_0'
bar_stool_A[0].instance_id = 'bar_stool_A_0'
meeting_chair_B[0].instance_id = 'meeting_chair_B_0'
floor_plan_display[0].instance_id = 'floor_plan_display_0'
table_lamp[0].instance_id = 'table_lamp_0'
small_round_meeting_table_B[0].instance_id = 'small_round_meeting_table_B_0'
notebook_A[0].instance_id = 'notebook_A_0'
coffee_mug[0].instance_id = 'coffee_mug_0'
bar_stool_B[0].instance_id = 'bar_stool_B_0'
wayfinding_sign_B[0].instance_id = 'wayfinding_sign_B_0'
meeting_chair_C[0].instance_id = 'meeting_chair_C_0'
wayfinding_sign_C[0].instance_id = 'wayfinding_sign_C_0'
wall_info_panel[0].instance_id = 'wall_info_panel_0'
small_potted_plant[0].instance_id = 'small_potted_plant_0'
wayfinding_sign_D[0].instance_id = 'wayfinding_sign_D_0'
bar_stool_C[0].instance_id = 'bar_stool_C_0'
meeting_chair_D[0].instance_id = 'meeting_chair_D_0'
notebook_B[0].instance_id = 'notebook_B_0'
notebook_C[0].instance_id = 'notebook_C_0'
pen_holder_B[0].instance_id = 'pen_holder_B_0'
book_A[0].instance_id = 'book_A_0'
book_B[0].instance_id = 'book_B_0'
notebook_D[0].instance_id = 'notebook_D_0'
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

pen_holder_A[0].position = [1.9202621322659792, 2.1227964913359627, 0.055]
pen_holder_A[0].rotation = [0, 0, 0]
lounge_sofa_A[0].position = [2.7631559244367363, 2.457461896117583, 0.41]
lounge_sofa_A[0].rotation = [0, 0, 0]
meeting_chair_A[0].position = [0.2747658362418859, 12.19942995646085, 0.41]
meeting_chair_A[0].rotation = [0, 0, 0]
standing_bar_counter[0].position = [2.554928272319931, 11.786313249740406, 0.525]
standing_bar_counter[0].rotation = [0, 0, 0]
side_coffee_table[0].position = [3.7127095239567294, 1.2468012554040744, 0.25]
side_coffee_table[0].rotation = [0, 0, 0]
small_round_meeting_table_A[0].position = [5.115391251096207, 5.720286520539428, 0.375]
small_round_meeting_table_A[0].rotation = [0, 0, 0]
wayfinding_sign_A[0].position = [2.203740456542094, 8.33060573627811, 0.09]
wayfinding_sign_A[0].rotation = [0, 0, 0]
lounge_sofa_B[0].position = [3.866180934956911, 12.560976703715784, 0.41]
lounge_sofa_B[0].rotation = [0, 0, 0]
bar_stool_A[0].position = [4.5696493129095455, 1.4398513194504439, 0.375]
bar_stool_A[0].rotation = [0, 0, 0]
meeting_chair_B[0].position = [3.9919269721357216, 1.3370508664751446, 0.41]
meeting_chair_B[0].rotation = [0, 0, 0]
floor_plan_display[0].position = [1.9312427656936948, 2.736487755574289, 0.325]
floor_plan_display[0].rotation = [0, 0, 0]
table_lamp[0].position = [1.9753166061808827, 10.77364892786837, 0.225]
table_lamp[0].rotation = [0, 0, 0]
small_round_meeting_table_B[0].position = [3.594894047228353, 7.230428997796323, 0.375]
small_round_meeting_table_B[0].rotation = [0, 0, 0]
notebook_A[0].position = [3.9383934742125075, 0.8332254008179442, 0.01]
notebook_A[0].rotation = [0, 0, 0]
coffee_mug[0].position = [4.3940485230560595, 0.0835094882192956, 0.05]
coffee_mug[0].rotation = [0, 0, 0]
bar_stool_B[0].position = [3.9560157553408066, 6.10414365526729, 0.375]
bar_stool_B[0].rotation = [0, 0, 0]
wayfinding_sign_B[0].position = [1.4069711477553741, 9.19607069180057, 0.09]
wayfinding_sign_B[0].rotation = [0, 0, 0]
meeting_chair_C[0].position = [7.82920948292069, 4.908502855894261, 0.41]
meeting_chair_C[0].rotation = [0, 0, 0]
wayfinding_sign_C[0].position = [10.349393715137825, 7.614525830616051, 0.09]
wayfinding_sign_C[0].rotation = [0, 0, 0]
wall_info_panel[0].position = [1.1217210031800402, 2.6073764522506147, 0.425]
wall_info_panel[0].rotation = [0, 0, 0]
small_potted_plant[0].position = [7.111130986566167, 12.416896488126559, 0.275]
small_potted_plant[0].rotation = [0, 0, 0]
wayfinding_sign_D[0].position = [5.713375645548998, 11.500171842862358, 0.09]
wayfinding_sign_D[0].rotation = [0, 0, 0]
bar_stool_C[0].position = [4.336586116560621, 1.8963472789773594, 0.375]
bar_stool_C[0].rotation = [0, 0, 0]
meeting_chair_D[0].position = [6.54168100282228, 4.906086872597591, 0.41]
meeting_chair_D[0].rotation = [0, 0, 0]
notebook_B[0].position = [2.856465690784605, 11.216428354090722, 0.01]
notebook_B[0].rotation = [0, 0, 0]
notebook_C[0].position = [2.1213282697336555, 5.443005584926154, 0.0075]
notebook_C[0].rotation = [0, 0, 0]
pen_holder_B[0].position = [2.6515096484899647, 4.81628650548242, 0.055]
pen_holder_B[0].rotation = [0, 0, 0]
book_A[0].position = [2.1659632683134022, 0.9280343042392515, 0.015]
book_A[0].rotation = [0, 0, 0]
book_B[0].position = [3.1733189421621684, 4.910785024421302, 0.0175]
book_B[0].rotation = [0, 0, 0]
notebook_D[0].position = [1.6917847631866718, 9.559375189349266, 0.0075]
notebook_D[0].rotation = [0, 0, 0]
pen_holder_A[0].position = [1.9202621322659792, 2.1227964913359627, 0.055]
pen_holder_A[0].rotation = [0, 0, 0]
lounge_sofa_A[0].position = [2.7631559244367363, 2.457461896117583, 0.41]
lounge_sofa_A[0].rotation = [0, 0, 0]
meeting_chair_A[0].position = [0.2747658362418859, 12.19942995646085, 0.41]
meeting_chair_A[0].rotation = [0, 0, 0]
standing_bar_counter[0].position = [2.554928272319931, 11.786313249740406, 0.525]
standing_bar_counter[0].rotation = [0, 0, 0]
side_coffee_table[0].position = [3.7127095239567294, 1.2468012554040744, 0.25]
side_coffee_table[0].rotation = [0, 0, 0]
small_round_meeting_table_A[0].position = [5.115391251096207, 5.720286520539428, 0.375]
small_round_meeting_table_A[0].rotation = [0, 0, 0]
wayfinding_sign_A[0].position = [2.203740456542094, 8.33060573627811, 0.09]
wayfinding_sign_A[0].rotation = [0, 0, 0]
lounge_sofa_B[0].position = [3.866180934956911, 12.560976703715784, 0.41]
lounge_sofa_B[0].rotation = [0, 0, 0]
bar_stool_A[0].position = [4.5696493129095455, 1.4398513194504439, 0.375]
bar_stool_A[0].rotation = [0, 0, 0]
meeting_chair_B[0].position = [3.9919269721357216, 1.3370508664751446, 0.41]
meeting_chair_B[0].rotation = [0, 0, 0]
floor_plan_display[0].position = [1.9312427656936948, 2.736487755574289, 0.325]
floor_plan_display[0].rotation = [0, 0, 0]
table_lamp[0].position = [1.9753166061808827, 10.77364892786837, 0.225]
table_lamp[0].rotation = [0, 0, 0]
small_round_meeting_table_B[0].position = [3.594894047228353, 7.230428997796323, 0.375]
small_round_meeting_table_B[0].rotation = [0, 0, 0]
notebook_A[0].position = [3.9383934742125075, 0.8332254008179442, 0.01]
notebook_A[0].rotation = [0, 0, 0]
coffee_mug[0].position = [4.3940485230560595, 0.0835094882192956, 0.05]
coffee_mug[0].rotation = [0, 0, 0]
bar_stool_B[0].position = [3.9560157553408066, 6.10414365526729, 0.375]
bar_stool_B[0].rotation = [0, 0, 0]
wayfinding_sign_B[0].position = [1.4069711477553741, 9.19607069180057, 0.09]
wayfinding_sign_B[0].rotation = [0, 0, 0]
meeting_chair_C[0].position = [7.82920948292069, 4.908502855894261, 0.41]
meeting_chair_C[0].rotation = [0, 0, 0]
wayfinding_sign_C[0].position = [10.349393715137825, 7.614525830616051, 0.09]
wayfinding_sign_C[0].rotation = [0, 0, 0]
wall_info_panel[0].position = [1.1217210031800402, 2.6073764522506147, 0.425]
wall_info_panel[0].rotation = [0, 0, 0]
small_potted_plant[0].position = [7.111130986566167, 12.416896488126559, 0.275]
small_potted_plant[0].rotation = [0, 0, 0]
wayfinding_sign_D[0].position = [5.713375645548998, 11.500171842862358, 0.09]
wayfinding_sign_D[0].rotation = [0, 0, 0]
bar_stool_C[0].position = [4.336586116560621, 1.8963472789773594, 0.375]
bar_stool_C[0].rotation = [0, 0, 0]
meeting_chair_D[0].position = [6.54168100282228, 4.906086872597591, 0.41]
meeting_chair_D[0].rotation = [0, 0, 0]
notebook_B[0].position = [2.856465690784605, 11.216428354090722, 0.01]
notebook_B[0].rotation = [0, 0, 0]
notebook_C[0].position = [2.1213282697336555, 5.443005584926154, 0.0075]
notebook_C[0].rotation = [0, 0, 0]
pen_holder_B[0].position = [2.6515096484899647, 4.81628650548242, 0.055]
pen_holder_B[0].rotation = [0, 0, 0]
book_A[0].position = [2.1659632683134022, 0.9280343042392515, 0.015]
book_A[0].rotation = [0, 0, 0]
book_B[0].position = [3.1733189421621684, 4.910785024421302, 0.0175]
book_B[0].rotation = [0, 0, 0]
notebook_D[0].position = [1.6917847631866718, 9.559375189349266, 0.0075]
notebook_D[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the supplied floor-plan coordinates directly. The south entrance strip,
# west-side door approaches, east-side door approaches, and fixed staircase
# footprint (x=5.205..7.995, y=8.765..11.435) remain unfurnished.
layout_entries = []

def set_layout(asset_group, xyz, yaw_degrees):
    instance = asset_group[0]
    instance.position = list(xyz)
    instance.rotation = [0, 0, radians(yaw_degrees)]
    layout_entries.append((instance, list(xyz), yaw_degrees))

# Two lounge sofas and the bar form three parallel rows. The bar is
# geometrically between the sofas; sofa B faces its own meeting table.
set_layout(lounge_sofa_A, (4.50, 2.60, 0.410), 90)
set_layout(standing_bar_counter, (4.50, 4.30, 0.525), 90)
set_layout(lounge_sofa_B, (4.50, 6.10, 0.410), 90)
set_layout(small_round_meeting_table_B, (4.50, 7.65, 0.375), 0)

# Stools fit between the first sofa and bar without intersecting either.
set_layout(bar_stool_A, (3.50, 3.48, 0.375), 90)
set_layout(bar_stool_B, (4.50, 3.48, 0.375), 90)
set_layout(bar_stool_C, (5.50, 3.48, 0.375), 90)

# Chairs flank the second lounge's round table, clear of the stair footprint.
set_layout(meeting_chair_C, (3.45, 7.65, 0.410), 0)
set_layout(meeting_chair_D, (5.55, 7.65, 0.410), 180)

# A separate two-person work table occupies the northwest area.
set_layout(small_round_meeting_table_A, (2.90, 10.30, 0.375), 0)
set_layout(meeting_chair_A, (2.90, 9.25, 0.410), 90)
set_layout(meeting_chair_B, (2.90, 11.35, 0.410), 270)

set_layout(side_coffee_table, (2.65, 6.10, 0.250), 0)
set_layout(table_lamp, (2.65, 6.10, 0.725), 0)
set_layout(small_potted_plant, (1.45, 12.45, 0.275), 0)

# Table A: separate writing materials rather than overlapping piles.
# In particular, notebook_A (o0013) belongs on table A (o0005).
set_layout(notebook_A, (2.68, 10.15, 0.760), 0)
set_layout(notebook_B, (3.10, 10.15, 0.760), 0)
set_layout(coffee_mug, (2.72, 10.55, 0.800), 0)
set_layout(pen_holder_A, (3.10, 10.55, 0.805), 0)

# Table B: two separated books and a pencil cup.
set_layout(book_A, (4.28, 7.50, 0.765), 0)
set_layout(book_B, (4.72, 7.50, 0.770), 0)
set_layout(pen_holder_B, (4.50, 7.95, 0.805), 0)

# The counter's rotated footprint is 3.00 m along x and 0.75 m along y.
set_layout(notebook_C, (3.65, 4.30, 1.055), 0)
set_layout(notebook_D, (5.35, 4.30, 1.055), 0)

# Wall-mounted signs are above door head height, not floor obstacles.
# Their thin local x dimension is perpendicular to these vertical walls.
set_layout(wayfinding_sign_A, (1.015, 6.57, 2.35), 0)
set_layout(wayfinding_sign_B, (1.015, 4.06, 2.35), 0)
set_layout(wayfinding_sign_C, (7.985, 1.00, 2.35), 180)
set_layout(wayfinding_sign_D, (7.985, 5.74, 2.35), 180)

# Information displays on the alcove's solid east wall, away from its door.
set_layout(floor_plan_display, (11.985, 8.15, 1.60), 180)
set_layout(wall_info_panel, (11.985, 9.20, 1.60), 180)

# Required semantic orientations take precedence over fallback orientations.
solver.point_towards(lounge_sofa_B[0], small_round_meeting_table_B[0])
solver.point_towards(lounge_sofa_A[0], standing_bar_counter[0])
solver.align_with(standing_bar_counter[0], lounge_sofa_B[0], angle=0)

for stool_group in (bar_stool_A, bar_stool_B, bar_stool_C):
    solver.point_towards(stool_group[0], standing_bar_counter[0])

for chair_group, table_group in (
    (meeting_chair_A, small_round_meeting_table_A),
    (meeting_chair_B, small_round_meeting_table_A),
    (meeting_chair_C, small_round_meeting_table_B),
    (meeting_chair_D, small_round_meeting_table_B),
):
    solver.point_towards(chair_group[0], table_group[0])

# Explicit support constraints keep every tabletop object off the floor.
for object_group, support_group in (
    (notebook_A, small_round_meeting_table_A),
    (notebook_B, small_round_meeting_table_A),
    (coffee_mug, small_round_meeting_table_A),
    (pen_holder_A, small_round_meeting_table_A),
    (book_A, small_round_meeting_table_B),
    (book_B, small_round_meeting_table_B),
    (pen_holder_B, small_round_meeting_table_B),
    (notebook_C, standing_bar_counter),
    (notebook_D, standing_bar_counter),
    (table_lamp, side_coffee_table),
):
    solver.on_top_of(object_group[0], support_group[0])

# Fixed coordinate anchors provide a position-based constraint for EVERY
# instance, including elevated wall displays. These preserve the deliberately
# nonoverlapping footprints, clear entrance approaches, and bar-between-sofas
# relationship without introducing any extra physical assets.
for placed_instance, target_xyz, target_yaw in layout_entries:
    fixed_reference = AssetInstance(
        position=target_xyz,
        rotation=[0, 0, radians(target_yaw)],
    )
    solver.distance_constraint(
        placed_instance, fixed_reference, 0, 0, weight=10
    )
    solver.align_with(placed_instance, fixed_reference, angle=0)

# Wall attachments supplement the anchors; orientation is already specified.
for sign_group, wall_index in (
    (wayfinding_sign_A, 1),
    (wayfinding_sign_B, 1),
    (wayfinding_sign_C, 3),
    (wayfinding_sign_D, 3),
    (floor_plan_display, 5),
    (wall_info_panel, 5),
):
    solver.against_wall(sign_group[0], walls[wall_index])

solver.constraints = []
wayfinding_sign_D[0].position = [7.984874248504639, 5.739999771118164, 0.09000000357627869]
wayfinding_sign_D[0].rotation = [0, 0, 3.141532013514439]
wayfinding_sign_D[0].optimize = 2
lounge_sofa_A[0].position = [4.5, 2.5999999046325684, 0.4099999964237213]
lounge_sofa_A[0].rotation = [0, 0, 1.5833626980517244]
lounge_sofa_A[0].optimize = 2
table_lamp[0].position = [2.6500000953674316, 6.099999904632568, 0.7250000238418579]
table_lamp[0].rotation = [0, 0, 0.01256637125682779]
table_lamp[0].optimize = 2
meeting_chair_D[0].position = [5.550000190734863, 7.650000095367432, 0.4099999964237213]
meeting_chair_D[0].rotation = [0, 0, -3.1290262823329655]
meeting_chair_D[0].optimize = 2
wayfinding_sign_A[0].position = [1.0149682760238647, 6.570000171661377, 0.09000000357627869]
wayfinding_sign_A[0].rotation = [0, 0, -6.064887810100177e-05]
wayfinding_sign_A[0].optimize = 2
floor_plan_display[0].position = [11.98514175415039, 8.149999618530273, 0.32499998807907104]
floor_plan_display[0].rotation = [0, 0, 3.141531948373861]
floor_plan_display[0].optimize = 2
wayfinding_sign_B[0].position = [1.0149682760238647, 4.059999942779541, 0.09000000357627869]
wayfinding_sign_B[0].rotation = [0, 0, -6.064887810100177e-05]
wayfinding_sign_B[0].optimize = 2
meeting_chair_C[0].position = [3.450000047683716, 7.650000095367432, 0.4099999964237213]
meeting_chair_C[0].rotation = [0, 0, 0.01256637125682779]
meeting_chair_C[0].optimize = 2
notebook_A[0].position = [2.680000066757202, 10.149999618530273, 0.7599999904632568]
notebook_A[0].rotation = [0, 0, 0.01256637125682779]
notebook_A[0].optimize = 2
pen_holder_B[0].position = [4.5, 7.949999809265137, 0.8050000071525574]
pen_holder_B[0].rotation = [0, 0, 0.01256637125682779]
pen_holder_B[0].optimize = 2
meeting_chair_B[0].position = [2.9000000953674316, 11.350000381469727, 0.4099999964237213]
meeting_chair_B[0].rotation = [0, 0, -1.5582299555380688]
meeting_chair_B[0].optimize = 2
book_B[0].position = [4.71999979019165, 7.5, 0.7699999809265137]
book_B[0].rotation = [0, 0, 0.01256637125682779]
book_B[0].optimize = 2
small_potted_plant[0].position = [1.4500000476837158, 12.449999809265137, 0.2750000059604645]
small_potted_plant[0].rotation = [0, 0, 0.00942477746072377]
small_potted_plant[0].optimize = 2
side_coffee_table[0].position = [2.6500000953674316, 6.099999904632568, 0.25]
side_coffee_table[0].rotation = [0, 0, 0.01256637125682779]
side_coffee_table[0].optimize = 2
meeting_chair_A[0].position = [2.9000000953674316, 9.25, 0.4099999964237213]
meeting_chair_A[0].rotation = [0, 0, 1.5833626980517244]
meeting_chair_A[0].optimize = 2
bar_stool_A[0].position = [3.5, 3.4800000190734863, 0.375]
bar_stool_A[0].rotation = [0, 0, 1.5833626980517244]
bar_stool_A[0].optimize = 2
coffee_mug[0].position = [2.7200000286102295, 10.550000190734863, 0.800000011920929]
coffee_mug[0].rotation = [0, 0, 0.01256637125682779]
coffee_mug[0].optimize = 2
notebook_B[0].position = [3.0999999046325684, 10.149999618530273, 0.7599999904632568]
notebook_B[0].rotation = [0, 0, 0.01256637125682779]
notebook_B[0].optimize = 2
bar_stool_C[0].position = [5.5, 3.4800000190734863, 0.375]
bar_stool_C[0].rotation = [0, 0, 1.5833626980517244]
bar_stool_C[0].optimize = 2
notebook_D[0].position = [5.349999904632568, 4.300000190734863, 1.0549999475479126]
notebook_D[0].rotation = [0, 0, 0.01256637125682779]
notebook_D[0].optimize = 2
wayfinding_sign_C[0].position = [7.984874248504639, 1.0, 0.09000000357627869]
wayfinding_sign_C[0].rotation = [0, 0, 3.141532013514439]
wayfinding_sign_C[0].optimize = 2
pen_holder_A[0].position = [3.0999999046325684, 10.550000190734863, 0.8050000071525574]
pen_holder_A[0].rotation = [0, 0, 0.01256637125682779]
pen_holder_A[0].optimize = 2
wall_info_panel[0].position = [11.98521614074707, 9.199999809265137, 0.42500001192092896]
wall_info_panel[0].rotation = [0, 0, 3.141531965420102]
wall_info_panel[0].optimize = 2
notebook_C[0].position = [3.6500000953674316, 4.300000190734863, 1.0549999475479126]
notebook_C[0].rotation = [0, 0, 0.01256637125682779]
notebook_C[0].optimize = 2
small_round_meeting_table_B[0].position = [4.5, 7.650000095367432, 0.375]
small_round_meeting_table_B[0].rotation = [0, 0, 0.02827433441159227]
small_round_meeting_table_B[0].optimize = 2
bar_stool_B[0].position = [4.5, 3.4800000190734863, 0.375]
bar_stool_B[0].rotation = [0, 0, 1.5833626980517244]
bar_stool_B[0].optimize = 2
lounge_sofa_B[0].position = [4.5, 6.099999904632568, 0.4099999964237213]
lounge_sofa_B[0].rotation = [0, 0, 1.586504290712113]
lounge_sofa_B[0].optimize = 2
standing_bar_counter[0].position = [4.5, 4.300000190734863, 0.5249999761581421]
standing_bar_counter[0].rotation = [0, 0, 1.5863063299575162]
standing_bar_counter[0].optimize = 2
small_round_meeting_table_A[0].position = [2.9000000953674316, 10.300000190734863, 0.375]
small_round_meeting_table_A[0].rotation = [0, 0, 0.02827433441159227]
small_round_meeting_table_A[0].optimize = 2
book_A[0].position = [4.28000020980835, 7.5, 0.7649999856948853]
book_A[0].rotation = [0, 0, 0.01256637125682779]
book_A[0].optimize = 2

