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
pen_holder_A = Assets(description="A wire frame cup for holding pencils.", size=[0.10, 0.10, 0.12], placements=[AssetInstance() for _ in range(1)])
lounge_sofa_A = Assets(description="A modern gray sofa with three seats.", size=[0.90, 2.20, 0.82], placements=[AssetInstance() for _ in range(1)])
meeting_chair_A = Assets(description="A black chair with thin legs.", size=[0.56, 0.52, 0.84], placements=[AssetInstance() for _ in range(1)])
standing_bar_counter = Assets(description="A long wood table.", size=[0.75, 3.00, 1.05], placements=[AssetInstance() for _ in range(1)])
side_coffee_table = Assets(description="side coffee table", size=[0.55, 0.60, 0.50], placements=[AssetInstance() for _ in range(1)])
small_round_meeting_table_A = Assets(description="small round meeting table", size=[0.90, 0.90, 0.74], placements=[AssetInstance() for _ in range(1)])
wayfinding_sign_A = Assets(description="A green and white exit sign with an arrow and a man running, pointing towards the door.", size=[0.04, 0.36, 0.18], placements=[AssetInstance() for _ in range(1)])
lounge_sofa_B = Assets(description="A modern gray sofa with three seats.", size=[0.90, 2.20, 0.82], placements=[AssetInstance() for _ in range(1)])
bar_stool_A = Assets(description="bar stool", size=[0.45, 0.43, 0.78], placements=[AssetInstance() for _ in range(1)])
meeting_chair_B = Assets(description="A black chair with thin legs.", size=[0.56, 0.52, 0.84], placements=[AssetInstance() for _ in range(1)])
floor_plan_display = Assets(description="A white rectangular poster with black blue and orange marks and irregular writing.", size=[0.03, 0.85, 1.10], placements=[AssetInstance() for _ in range(1)])
table_lamp = Assets(description="A wooden table lamp on a small wooden table.", size=[0.30, 0.30, 0.52], placements=[AssetInstance() for _ in range(1)])
small_round_meeting_table_B = Assets(description="small round meeting table", size=[0.90, 0.90, 0.74], placements=[AssetInstance() for _ in range(1)])
notebook_A = Assets(description="A black book with silver trim.", size=[0.16, 0.22, 0.02], placements=[AssetInstance() for _ in range(1)])
coffee_mug = Assets(description="A mug with a handle that is an dark orange color.", size=[0.10, 0.13, 0.11], placements=[AssetInstance() for _ in range(1)])
bar_stool_B = Assets(description="bar stool", size=[0.45, 0.43, 0.78], placements=[AssetInstance() for _ in range(1)])
wayfinding_sign_B = Assets(description="A green and white exit sign with an arrow and a man running, pointing towards the door.", size=[0.04, 0.36, 0.18], placements=[AssetInstance() for _ in range(1)])
meeting_chair_C = Assets(description="A black chair with thin legs.", size=[0.56, 0.52, 0.84], placements=[AssetInstance() for _ in range(1)])
wayfinding_sign_C = Assets(description="A green and white exit sign with an arrow and a man running, pointing towards the door.", size=[0.04, 0.36, 0.18], placements=[AssetInstance() for _ in range(1)])
wall_info_panel = Assets(description="A poster of blueprints for a picture frame.", size=[0.03, 0.75, 1.00], placements=[AssetInstance() for _ in range(1)])
small_potted_plant = Assets(description="A bunch of big leaves inside of a white pot.", size=[0.45, 0.45, 0.65], placements=[AssetInstance() for _ in range(1)])
wayfinding_sign_D = Assets(description="A green and white exit sign with an arrow and a man running, pointing towards the door.", size=[0.04, 0.36, 0.18], placements=[AssetInstance() for _ in range(1)])
bar_stool_C = Assets(description="bar stool", size=[0.45, 0.43, 0.78], placements=[AssetInstance() for _ in range(1)])
meeting_chair_D = Assets(description="A black chair with thin legs.", size=[0.56, 0.52, 0.84], placements=[AssetInstance() for _ in range(1)])
notebook_B = Assets(description="A black book with silver trim.", size=[0.16, 0.22, 0.02], placements=[AssetInstance() for _ in range(1)])
notebook_C = Assets(description="A pink spiral notebook with a green leaf on it.", size=[0.18, 0.24, 0.02], placements=[AssetInstance() for _ in range(1)])
pen_holder_B = Assets(description="A wire frame cup for holding pencils.", size=[0.10, 0.10, 0.12], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="A brown book with silver corners.", size=[0.17, 0.24, 0.03], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="It is a hard cover book with a blue cover.", size=[0.17, 0.24, 0.03], placements=[AssetInstance() for _ in range(1)])
notebook_D = Assets(description="A pink spiral notebook with a green leaf on it.", size=[0.18, 0.24, 0.02], placements=[AssetInstance() for _ in range(1)])

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

pen_holder_A[0].position = [5.98435200696108, 1.9123856749422292, 0.06]
pen_holder_A[0].rotation = [0, 0, 0]
lounge_sofa_A[0].position = [10.493372342920917, 8.44647777588393, 0.41]
lounge_sofa_A[0].rotation = [0, 0, 0]
meeting_chair_A[0].position = [4.046376119969274, 2.496872084663647, 0.42]
meeting_chair_A[0].rotation = [0, 0, 0]
standing_bar_counter[0].position = [4.876454262996958, 2.0991039974884442, 0.525]
standing_bar_counter[0].rotation = [0, 0, 0]
side_coffee_table[0].position = [8.807844021102646, 9.123290067447654, 0.25]
side_coffee_table[0].rotation = [0, 0, 0]
small_round_meeting_table_A[0].position = [7.45613778445727, 5.009618912807671, 0.37]
small_round_meeting_table_A[0].rotation = [0, 0, 0]
wayfinding_sign_A[0].position = [4.5713270945719975, 8.324613775561645, 0.09]
wayfinding_sign_A[0].rotation = [0, 0, 0]
lounge_sofa_B[0].position = [11.245318829085777, 9.082401976859174, 0.41]
lounge_sofa_B[0].rotation = [0, 0, 0]
bar_stool_A[0].position = [1.3877758177617752, 12.10699278621817, 0.39]
bar_stool_A[0].rotation = [0, 0, 0]
meeting_chair_B[0].position = [1.747314736214221, 10.188274057556068, 0.42]
meeting_chair_B[0].rotation = [0, 0, 0]
floor_plan_display[0].position = [2.30898605023047, 4.488492913044101, 0.55]
floor_plan_display[0].rotation = [0, 0, 0]
table_lamp[0].position = [6.100685812083821, 3.9534446977712476, 0.26]
table_lamp[0].rotation = [0, 0, 0]
small_round_meeting_table_B[0].position = [3.1874614458212025, 4.483435644358482, 0.37]
small_round_meeting_table_B[0].rotation = [0, 0, 0]
notebook_A[0].position = [6.528277953200405, 5.807566843365199, 0.01]
notebook_A[0].rotation = [0, 0, 0]
coffee_mug[0].position = [7.609730156876699, 3.0172016707948424, 0.055]
coffee_mug[0].rotation = [0, 0, 0]
bar_stool_B[0].position = [7.455267854145569, 6.904643711145588, 0.39]
bar_stool_B[0].rotation = [0, 0, 0]
wayfinding_sign_B[0].position = [6.75339350046492, 10.455176560238733, 0.09]
wayfinding_sign_B[0].rotation = [0, 0, 0]
meeting_chair_C[0].position = [5.244165074138927, 5.532587177228416, 0.42]
meeting_chair_C[0].rotation = [0, 0, 0]
wayfinding_sign_C[0].position = [3.7321297101307342, 8.51532394563444, 0.09]
wayfinding_sign_C[0].rotation = [0, 0, 0]
wall_info_panel[0].position = [6.301870438902122, 7.769532096784819, 0.5]
wall_info_panel[0].rotation = [0, 0, 0]
small_potted_plant[0].position = [2.059039625053554, 8.986853115565278, 0.325]
small_potted_plant[0].rotation = [0, 0, 0]
wayfinding_sign_D[0].position = [7.2567089794373425, 5.389299738989783, 0.09]
wayfinding_sign_D[0].rotation = [0, 0, 0]
bar_stool_C[0].position = [4.034751057437786, 12.342914094026584, 0.39]
bar_stool_C[0].rotation = [0, 0, 0]
meeting_chair_D[0].position = [7.7616421637775845, 10.286314989126698, 0.42]
meeting_chair_D[0].rotation = [0, 0, 0]
notebook_B[0].position = [3.037787165887331, 4.83626677786285, 0.01]
notebook_B[0].rotation = [0, 0, 0]
notebook_C[0].position = [7.543149001593967, 2.597224463530323, 0.01]
notebook_C[0].rotation = [0, 0, 0]
pen_holder_B[0].position = [7.383358366876167, 8.487207190794601, 0.06]
pen_holder_B[0].rotation = [0, 0, 0]
book_A[0].position = [5.823342203539074, 4.47495902681599, 0.015]
book_A[0].rotation = [0, 0, 0]
book_B[0].position = [1.9540738276767766, 8.893745936111737, 0.015]
book_B[0].rotation = [0, 0, 0]
notebook_D[0].position = [9.135708394422442, 8.287068498521467, 0.01]
notebook_D[0].rotation = [0, 0, 0]
pen_holder_A[0].position = [5.98435200696108, 1.9123856749422292, 0.06]
pen_holder_A[0].rotation = [0, 0, 0]
lounge_sofa_A[0].position = [10.493372342920917, 8.44647777588393, 0.41]
lounge_sofa_A[0].rotation = [0, 0, 0]
meeting_chair_A[0].position = [4.046376119969274, 2.496872084663647, 0.42]
meeting_chair_A[0].rotation = [0, 0, 0]
standing_bar_counter[0].position = [4.876454262996958, 2.0991039974884442, 0.525]
standing_bar_counter[0].rotation = [0, 0, 0]
side_coffee_table[0].position = [8.807844021102646, 9.123290067447654, 0.25]
side_coffee_table[0].rotation = [0, 0, 0]
small_round_meeting_table_A[0].position = [7.45613778445727, 5.009618912807671, 0.37]
small_round_meeting_table_A[0].rotation = [0, 0, 0]
wayfinding_sign_A[0].position = [4.5713270945719975, 8.324613775561645, 0.09]
wayfinding_sign_A[0].rotation = [0, 0, 0]
lounge_sofa_B[0].position = [11.245318829085777, 9.082401976859174, 0.41]
lounge_sofa_B[0].rotation = [0, 0, 0]
bar_stool_A[0].position = [1.3877758177617752, 12.10699278621817, 0.39]
bar_stool_A[0].rotation = [0, 0, 0]
meeting_chair_B[0].position = [1.747314736214221, 10.188274057556068, 0.42]
meeting_chair_B[0].rotation = [0, 0, 0]
floor_plan_display[0].position = [2.30898605023047, 4.488492913044101, 0.55]
floor_plan_display[0].rotation = [0, 0, 0]
table_lamp[0].position = [6.100685812083821, 3.9534446977712476, 0.26]
table_lamp[0].rotation = [0, 0, 0]
small_round_meeting_table_B[0].position = [3.1874614458212025, 4.483435644358482, 0.37]
small_round_meeting_table_B[0].rotation = [0, 0, 0]
notebook_A[0].position = [6.528277953200405, 5.807566843365199, 0.01]
notebook_A[0].rotation = [0, 0, 0]
coffee_mug[0].position = [7.609730156876699, 3.0172016707948424, 0.055]
coffee_mug[0].rotation = [0, 0, 0]
bar_stool_B[0].position = [7.455267854145569, 6.904643711145588, 0.39]
bar_stool_B[0].rotation = [0, 0, 0]
wayfinding_sign_B[0].position = [6.75339350046492, 10.455176560238733, 0.09]
wayfinding_sign_B[0].rotation = [0, 0, 0]
meeting_chair_C[0].position = [5.244165074138927, 5.532587177228416, 0.42]
meeting_chair_C[0].rotation = [0, 0, 0]
wayfinding_sign_C[0].position = [3.7321297101307342, 8.51532394563444, 0.09]
wayfinding_sign_C[0].rotation = [0, 0, 0]
wall_info_panel[0].position = [6.301870438902122, 7.769532096784819, 0.5]
wall_info_panel[0].rotation = [0, 0, 0]
small_potted_plant[0].position = [2.059039625053554, 8.986853115565278, 0.325]
small_potted_plant[0].rotation = [0, 0, 0]
wayfinding_sign_D[0].position = [7.2567089794373425, 5.389299738989783, 0.09]
wayfinding_sign_D[0].rotation = [0, 0, 0]
bar_stool_C[0].position = [4.034751057437786, 12.342914094026584, 0.39]
bar_stool_C[0].rotation = [0, 0, 0]
meeting_chair_D[0].position = [7.7616421637775845, 10.286314989126698, 0.42]
meeting_chair_D[0].rotation = [0, 0, 0]
notebook_B[0].position = [3.037787165887331, 4.83626677786285, 0.01]
notebook_B[0].rotation = [0, 0, 0]
notebook_C[0].position = [7.543149001593967, 2.597224463530323, 0.01]
notebook_C[0].rotation = [0, 0, 0]
pen_holder_B[0].position = [7.383358366876167, 8.487207190794601, 0.06]
pen_holder_B[0].rotation = [0, 0, 0]
book_A[0].position = [5.823342203539074, 4.47495902681599, 0.015]
book_A[0].rotation = [0, 0, 0]
book_B[0].position = [1.9540738276767766, 8.893745936111737, 0.015]
book_B[0].rotation = [0, 0, 0]
notebook_D[0].position = [9.135708394422442, 8.287068498521467, 0.01]
notebook_D[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed pose references preserve the planned functional zones while allowing the
# solver to make small feasibility adjustments. All z values place floor assets
# at half their height and tabletop assets at the supporting surface height.

# ---------------------------------------------------------------------------
# Initial placements
# ---------------------------------------------------------------------------

# Lounge zone in the upper-middle portion of the main room. The counter lies
# between the two sofas, while remaining clear of the fixed staircase.
lounge_sofa_A[0].position = [2.20, 7.50, 0.41]
lounge_sofa_A[0].rotation = [0, 0, radians(0)]

standing_bar_counter[0].position = [4.00, 7.50, 0.525]
standing_bar_counter[0].rotation = [0, 0, radians(0)]

lounge_sofa_B[0].position = [6.45, 7.55, 0.41]
lounge_sofa_B[0].rotation = [0, 0, radians(-90)]

small_round_meeting_table_B[0].position = [6.45, 6.25, 0.37]
small_round_meeting_table_B[0].rotation = [0, 0, radians(0)]

side_coffee_table[0].position = [2.20, 6.08, 0.25]
side_coffee_table[0].rotation = [0, 0, radians(0)]

table_lamp[0].position = [2.20, 6.08, 0.76]
table_lamp[0].rotation = [0, 0, radians(0)]

# Three stools run along the east side of the bar and face the counter.
bar_stool_A[0].position = [4.85, 6.50, 0.39]
bar_stool_A[0].rotation = [0, 0, radians(180)]

bar_stool_B[0].position = [4.85, 7.50, 0.39]
bar_stool_B[0].rotation = [0, 0, radians(180)]

bar_stool_C[0].position = [4.85, 8.50, 0.39]
bar_stool_C[0].rotation = [0, 0, radians(180)]

# Meeting zone in the lower-middle room, away from all door approaches.
small_round_meeting_table_A[0].position = [3.20, 3.60, 0.37]
small_round_meeting_table_A[0].rotation = [0, 0, radians(0)]

meeting_chair_A[0].position = [2.20, 3.60, 0.42]
meeting_chair_A[0].rotation = [0, 0, radians(0)]

meeting_chair_B[0].position = [4.20, 3.60, 0.42]
meeting_chair_B[0].rotation = [0, 0, radians(180)]

meeting_chair_C[0].position = [3.20, 2.55, 0.42]
meeting_chair_C[0].rotation = [0, 0, radians(90)]

meeting_chair_D[0].position = [3.20, 4.65, 0.42]
meeting_chair_D[0].rotation = [0, 0, radians(-90)]

small_potted_plant[0].position = [6.80, 3.50, 0.325]
small_potted_plant[0].rotation = [0, 0, radians(0)]

# Items on the first meeting table. In particular, notebook_A is explicitly
# placed on the requested small round meeting table.
notebook_A[0].position = [3.08, 3.60, 0.75]
notebook_A[0].rotation = [0, 0, radians(0)]

pen_holder_A[0].position = [3.42, 3.60, 0.80]
pen_holder_A[0].rotation = [0, 0, radians(0)]

# Items on the lounge meeting table.
notebook_B[0].position = [6.30, 6.25, 0.75]
notebook_B[0].rotation = [0, 0, radians(0)]

coffee_mug[0].position = [6.62, 6.25, 0.795]
coffee_mug[0].rotation = [0, 0, radians(0)]

# Bar accessories are spaced along the counter so their bounding boxes do not
# overlap. Their centers are at the counter-top height plus half their height.
notebook_C[0].position = [4.00, 6.45, 1.06]
notebook_C[0].rotation = [0, 0, radians(0)]

notebook_D[0].position = [4.00, 7.00, 1.06]
notebook_D[0].rotation = [0, 0, radians(0)]

pen_holder_B[0].position = [4.00, 7.50, 1.11]
pen_holder_B[0].rotation = [0, 0, radians(0)]

book_A[0].position = [4.00, 8.05, 1.065]
book_A[0].rotation = [0, 0, radians(0)]

book_B[0].position = [4.00, 8.55, 1.065]
book_B[0].rotation = [0, 0, radians(0)]

# Wall-mounted/floor-standing information assets use wall portions that do not
# contain doors. The signs are elevated and face into the room.
wayfinding_sign_A[0].position = [1.02, 8.45, 2.05]
wayfinding_sign_A[0].rotation = [0, 0, radians(0)]

wayfinding_sign_B[0].position = [7.98, 3.45, 2.05]
wayfinding_sign_B[0].rotation = [0, 0, radians(180)]

wayfinding_sign_C[0].position = [11.98, 8.60, 2.05]
wayfinding_sign_C[0].rotation = [0, 0, radians(180)]

wayfinding_sign_D[0].position = [10.70, 9.98, 2.05]
wayfinding_sign_D[0].rotation = [0, 0, radians(-90)]

floor_plan_display[0].position = [10.00, 7.02, 0.55]
floor_plan_display[0].rotation = [0, 0, radians(90)]

wall_info_panel[0].position = [3.00, 12.98, 1.65]
wall_info_panel[0].rotation = [0, 0, radians(-90)]

# ---------------------------------------------------------------------------
# Fixed pose references used by the position and orientation constraints
# ---------------------------------------------------------------------------

sofa_A_pose = AssetInstance(
    position=[2.20, 7.50, 0.41],
    rotation=[0, 0, radians(0)],
)
counter_pose = AssetInstance(
    position=[4.00, 7.50, 0.525],
    rotation=[0, 0, radians(0)],
)
sofa_B_pose = AssetInstance(
    position=[6.45, 7.55, 0.41],
    rotation=[0, 0, radians(-90)],
)
lounge_table_pose = AssetInstance(
    position=[6.45, 6.25, 0.37],
    rotation=[0, 0, radians(0)],
)
side_table_pose = AssetInstance(
    position=[2.20, 6.08, 0.25],
    rotation=[0, 0, radians(0)],
)

stool_A_pose = AssetInstance(
    position=[4.85, 6.50, 0.39],
    rotation=[0, 0, radians(180)],
)
stool_B_pose = AssetInstance(
    position=[4.85, 7.50, 0.39],
    rotation=[0, 0, radians(180)],
)
stool_C_pose = AssetInstance(
    position=[4.85, 8.50, 0.39],
    rotation=[0, 0, radians(180)],
)

meeting_table_pose = AssetInstance(
    position=[3.20, 3.60, 0.37],
    rotation=[0, 0, radians(0)],
)
chair_A_pose = AssetInstance(
    position=[2.20, 3.60, 0.42],
    rotation=[0, 0, radians(0)],
)
chair_B_pose = AssetInstance(
    position=[4.20, 3.60, 0.42],
    rotation=[0, 0, radians(180)],
)
chair_C_pose = AssetInstance(
    position=[3.20, 2.55, 0.42],
    rotation=[0, 0, radians(90)],
)
chair_D_pose = AssetInstance(
    position=[3.20, 4.65, 0.42],
    rotation=[0, 0, radians(-90)],
)
plant_pose = AssetInstance(
    position=[6.80, 3.50, 0.325],
    rotation=[0, 0, radians(0)],
)

notebook_A_pose = AssetInstance(
    position=[3.08, 3.60, 0.75],
    rotation=[0, 0, radians(0)],
)
pen_holder_A_pose = AssetInstance(
    position=[3.42, 3.60, 0.80],
    rotation=[0, 0, radians(0)],
)
notebook_B_pose = AssetInstance(
    position=[6.30, 6.25, 0.75],
    rotation=[0, 0, radians(0)],
)
coffee_mug_pose = AssetInstance(
    position=[6.62, 6.25, 0.795],
    rotation=[0, 0, radians(0)],
)
notebook_C_pose = AssetInstance(
    position=[4.00, 6.45, 1.06],
    rotation=[0, 0, radians(0)],
)
notebook_D_pose = AssetInstance(
    position=[4.00, 7.00, 1.06],
    rotation=[0, 0, radians(0)],
)
pen_holder_B_pose = AssetInstance(
    position=[4.00, 7.50, 1.11],
    rotation=[0, 0, radians(0)],
)
book_A_pose = AssetInstance(
    position=[4.00, 8.05, 1.065],
    rotation=[0, 0, radians(0)],
)
book_B_pose = AssetInstance(
    position=[4.00, 8.55, 1.065],
    rotation=[0, 0, radians(0)],
)
lamp_pose = AssetInstance(
    position=[2.20, 6.08, 0.76],
    rotation=[0, 0, radians(0)],
)

sign_A_pose = AssetInstance(
    position=[1.02, 8.45, 2.05],
    rotation=[0, 0, radians(0)],
)
sign_B_pose = AssetInstance(
    position=[7.98, 3.45, 2.05],
    rotation=[0, 0, radians(180)],
)
sign_C_pose = AssetInstance(
    position=[11.98, 8.60, 2.05],
    rotation=[0, 0, radians(180)],
)
sign_D_pose = AssetInstance(
    position=[10.70, 9.98, 2.05],
    rotation=[0, 0, radians(-90)],
)
floor_display_pose = AssetInstance(
    position=[10.00, 7.02, 0.55],
    rotation=[0, 0, radians(90)],
)
wall_panel_pose = AssetInstance(
    position=[3.00, 12.98, 1.65],
    rotation=[0, 0, radians(-90)],
)

# ---------------------------------------------------------------------------
# Furniture constraints
# ---------------------------------------------------------------------------

# Sofa A faces the bar/lounge composition.
solver.distance_constraint(
    lounge_sofa_A[0], sofa_A_pose, 0, 0, weight=10
)
solver.point_towards(lounge_sofa_A[0], standing_bar_counter[0])

# The bar's exact central position keeps it between the two sofas. The softer
# distance constraints retain that relationship if feasibility adjustments occur.
solver.distance_constraint(
    standing_bar_counter[0], counter_pose, 0, 0, weight=10
)
solver.distance_constraint(
    standing_bar_counter[0], lounge_sofa_A[0], 1.75, 1.85, weight=5
)
solver.distance_constraint(
    standing_bar_counter[0], lounge_sofa_B[0], 2.35, 2.60, weight=5
)
solver.align_with(standing_bar_counter[0], counter_pose)

# Sofa B is explicitly oriented toward the requested round meeting table.
solver.distance_constraint(
    lounge_sofa_B[0], sofa_B_pose, 0, 0, weight=10
)
solver.point_towards(
    lounge_sofa_B[0], small_round_meeting_table_B[0]
)

solver.distance_constraint(
    small_round_meeting_table_B[0], lounge_table_pose, 0, 0, weight=10
)
solver.align_with(
    small_round_meeting_table_B[0], lounge_table_pose
)

solver.distance_constraint(
    side_coffee_table[0], side_table_pose, 0, 0, weight=10
)
solver.align_with(side_coffee_table[0], lounge_sofa_A[0])

# The stools retain regular spacing and face the bar's working side.
solver.distance_constraint(
    bar_stool_A[0], stool_A_pose, 0, 0, weight=10
)
solver.point_towards(bar_stool_A[0], standing_bar_counter[0])

solver.distance_constraint(
    bar_stool_B[0], stool_B_pose, 0, 0, weight=10
)
solver.point_towards(bar_stool_B[0], standing_bar_counter[0])

solver.distance_constraint(
    bar_stool_C[0], stool_C_pose, 0, 0, weight=10
)
solver.point_towards(bar_stool_C[0], standing_bar_counter[0])

# The lower meeting group is anchored away from door clearances.
solver.distance_constraint(
    small_round_meeting_table_A[0], meeting_table_pose, 0, 0, weight=10
)
solver.align_with(
    small_round_meeting_table_A[0], meeting_table_pose
)

solver.distance_constraint(
    meeting_chair_A[0], chair_A_pose, 0, 0, weight=10
)
solver.point_towards(
    meeting_chair_A[0], small_round_meeting_table_A[0]
)

solver.distance_constraint(
    meeting_chair_B[0], chair_B_pose, 0, 0, weight=10
)
solver.point_towards(
    meeting_chair_B[0], small_round_meeting_table_A[0]
)

solver.distance_constraint(
    meeting_chair_C[0], chair_C_pose, 0, 0, weight=10
)
solver.point_towards(
    meeting_chair_C[0], small_round_meeting_table_A[0]
)

solver.distance_constraint(
    meeting_chair_D[0], chair_D_pose, 0, 0, weight=10
)
solver.point_towards(
    meeting_chair_D[0], small_round_meeting_table_A[0]
)

solver.distance_constraint(
    small_potted_plant[0], plant_pose, 0, 0, weight=10
)
solver.align_with(small_potted_plant[0], plant_pose)

# ---------------------------------------------------------------------------
# Supported-object constraints
# ---------------------------------------------------------------------------

# Meeting table A accessories.
solver.on_top_of(notebook_A[0], small_round_meeting_table_A[0])
solver.distance_constraint(
    notebook_A[0], notebook_A_pose, 0, 0, weight=10
)
solver.align_with(notebook_A[0], small_round_meeting_table_A[0])

solver.on_top_of(pen_holder_A[0], small_round_meeting_table_A[0])
solver.distance_constraint(
    pen_holder_A[0], pen_holder_A_pose, 0, 0, weight=10
)
solver.align_with(pen_holder_A[0], small_round_meeting_table_A[0])

# Meeting table B accessories.
solver.on_top_of(notebook_B[0], small_round_meeting_table_B[0])
solver.distance_constraint(
    notebook_B[0], notebook_B_pose, 0, 0, weight=10
)
solver.align_with(notebook_B[0], small_round_meeting_table_B[0])

solver.on_top_of(coffee_mug[0], small_round_meeting_table_B[0])
solver.distance_constraint(
    coffee_mug[0], coffee_mug_pose, 0, 0, weight=10
)
solver.align_with(coffee_mug[0], small_round_meeting_table_B[0])

# Side-table lamp.
solver.on_top_of(table_lamp[0], side_coffee_table[0])
solver.distance_constraint(
    table_lamp[0], lamp_pose, 0, 0, weight=10
)
solver.align_with(table_lamp[0], side_coffee_table[0])

# Bar-counter accessories.
solver.on_top_of(notebook_C[0], standing_bar_counter[0])
solver.distance_constraint(
    notebook_C[0], notebook_C_pose, 0, 0, weight=10
)
solver.align_with(notebook_C[0], standing_bar_counter[0])

solver.on_top_of(notebook_D[0], standing_bar_counter[0])
solver.distance_constraint(
    notebook_D[0], notebook_D_pose, 0, 0, weight=10
)
solver.align_with(notebook_D[0], standing_bar_counter[0])

solver.on_top_of(pen_holder_B[0], standing_bar_counter[0])
solver.distance_constraint(
    pen_holder_B[0], pen_holder_B_pose, 0, 0, weight=10
)
solver.align_with(pen_holder_B[0], standing_bar_counter[0])

solver.on_top_of(book_A[0], standing_bar_counter[0])
solver.distance_constraint(
    book_A[0], book_A_pose, 0, 0, weight=10
)
solver.align_with(book_A[0], standing_bar_counter[0])

solver.on_top_of(book_B[0], standing_bar_counter[0])
solver.distance_constraint(
    book_B[0], book_B_pose, 0, 0, weight=10
)
solver.align_with(book_B[0], standing_bar_counter[0])

# ---------------------------------------------------------------------------
# Wall information and wayfinding constraints
# ---------------------------------------------------------------------------

# Left wall above the highest left-side door.
solver.against_wall(wayfinding_sign_A[0], walls[1])
solver.distance_constraint(
    wayfinding_sign_A[0], sign_A_pose, 0, 0, weight=10
)
solver.align_with(wayfinding_sign_A[0], sign_A_pose)

# Right wall section between its two doors.
solver.against_wall(wayfinding_sign_B[0], walls[3])
solver.distance_constraint(
    wayfinding_sign_B[0], sign_B_pose, 0, 0, weight=10
)
solver.align_with(wayfinding_sign_B[0], sign_B_pose)

# Outer wall of the east extension.
solver.against_wall(wayfinding_sign_C[0], walls[5])
solver.distance_constraint(
    wayfinding_sign_C[0], sign_C_pose, 0, 0, weight=10
)
solver.align_with(wayfinding_sign_C[0], sign_C_pose)

# Upper wall of the east extension, offset from the door centered at x=9.84.
solver.against_wall(wayfinding_sign_D[0], walls[6])
solver.distance_constraint(
    wayfinding_sign_D[0], sign_D_pose, 0, 0, weight=10
)
solver.align_with(wayfinding_sign_D[0], sign_D_pose)

# The floor-plan display sits against the lower wall of the east extension and
# faces north into that space.
solver.against_wall(floor_plan_display[0], walls[4])
solver.distance_constraint(
    floor_plan_display[0], floor_display_pose, 0, 0, weight=10
)
solver.align_with(floor_plan_display[0], floor_display_pose)

# The blueprint panel uses the uninterrupted top wall, clear of the staircase.
solver.against_wall(wall_info_panel[0], walls[8])
solver.distance_constraint(
    wall_info_panel[0], wall_panel_pose, 0, 0, weight=10
)
solver.align_with(wall_info_panel[0], wall_panel_pose)

solver.constraints = []
bar_stool_B[0].position = [4.849999904632568, 7.5, 0.38999998569488525]
bar_stool_B[0].rotation = [0, 0, -3.1321678761290697]
bar_stool_B[0].optimize = 2
table_lamp[0].position = [2.200000047683716, 6.079999923706055, 0.7599999904632568]
table_lamp[0].rotation = [0, 0, 0.015280340994521899]
table_lamp[0].optimize = 2
meeting_chair_B[0].position = [4.199999809265137, 3.5999999046325684, 0.41999998688697815]
meeting_chair_B[0].rotation = [0, 0, -3.1321678761290697]
meeting_chair_B[0].optimize = 2
wayfinding_sign_D[0].position = [10.699999809265137, 9.980216026306152, 0.09000000357627869]
wayfinding_sign_D[0].rotation = [0, 0, -1.5708570150636831]
wayfinding_sign_D[0].optimize = 2
lounge_sofa_A[0].position = [2.200000047683716, 7.5, 0.4099999964237213]
lounge_sofa_A[0].rotation = [0, 0, 0.0157079639172164]
lounge_sofa_A[0].optimize = 2
notebook_D[0].position = [4.0, 7.0, 1.059999942779541]
notebook_D[0].rotation = [0, 0, 0.0592117341187293]
notebook_D[0].optimize = 2
standing_bar_counter[0].position = [4.0, 7.5, 0.5249999761581421]
standing_bar_counter[0].rotation = [0, 0, 0.059690259289836754]
standing_bar_counter[0].optimize = 2
small_potted_plant[0].position = [6.800000190734863, 3.5, 0.32499998807907104]
small_potted_plant[0].rotation = [0, 0, 0.00942477746072377]
small_potted_plant[0].optimize = 2
bar_stool_A[0].position = [4.849999904632568, 6.5, 0.38999998569488525]
bar_stool_A[0].rotation = [0, 0, -3.1321678761290697]
bar_stool_A[0].optimize = 2
meeting_chair_D[0].position = [3.200000047683716, 4.650000095367432, 0.41999998688697815]
meeting_chair_D[0].rotation = [0, 0, -1.5613715493341729]
meeting_chair_D[0].optimize = 2
floor_plan_display[0].position = [10.0, 7.015068054199219, 0.550000011920929]
floor_plan_display[0].rotation = [0, 0, 1.5707355333149349]
floor_plan_display[0].optimize = 2
pen_holder_B[0].position = [4.0, 7.5, 1.1099998950958252]
pen_holder_B[0].rotation = [0, 0, 0.0592117341187293]
pen_holder_B[0].optimize = 2
book_A[0].position = [4.0, 8.050000190734863, 1.0649999380111694]
book_A[0].rotation = [0, 0, 0.0592117341187293]
book_A[0].optimize = 2
book_B[0].position = [4.0, 8.550000190734863, 1.0649999380111694]
book_B[0].rotation = [0, 0, 0.0592117341187293]
book_B[0].optimize = 2
small_round_meeting_table_A[0].position = [3.200000047683716, 3.5999999046325684, 0.3700000047683716]
small_round_meeting_table_A[0].rotation = [0, 0, 0.03455751882667646]
small_round_meeting_table_A[0].optimize = 2
lounge_sofa_B[0].position = [6.449999809265137, 7.550000190734863, 0.4099999964237213]
lounge_sofa_B[0].rotation = [0, 0, -1.5582299555380688]
lounge_sofa_B[0].optimize = 2
notebook_B[0].position = [6.300000190734863, 6.25, 0.75]
notebook_B[0].rotation = [0, 0, 0.025024544325611065]
notebook_B[0].optimize = 2
wayfinding_sign_A[0].position = [1.019826054573059, 8.449999809265137, 0.09000000357627869]
wayfinding_sign_A[0].rotation = [0, 0, -6.065333002820863e-05]
wayfinding_sign_A[0].optimize = 2
wayfinding_sign_B[0].position = [7.98019552230835, 3.450000047683716, 0.09000000357627869]
wayfinding_sign_B[0].rotation = [0, 0, 3.1415319814359948]
wayfinding_sign_B[0].optimize = 2
meeting_chair_C[0].position = [3.200000047683716, 2.549999952316284, 0.41999998688697815]
meeting_chair_C[0].rotation = [0, 0, 1.5802211042556205]
meeting_chair_C[0].optimize = 2
side_coffee_table[0].position = [2.200000047683716, 6.079999923706055, 0.25]
side_coffee_table[0].rotation = [0, 0, 0.015878372834290954]
side_coffee_table[0].optimize = 2
meeting_chair_A[0].position = [2.200000047683716, 3.5999999046325684, 0.41999998688697815]
meeting_chair_A[0].rotation = [0, 0, 0.00942477746072377]
meeting_chair_A[0].optimize = 2
notebook_A[0].position = [3.0799999237060547, 3.5999999046325684, 0.75]
notebook_A[0].rotation = [0, 0, 0.03462658634231508]
notebook_A[0].optimize = 2
bar_stool_C[0].position = [4.849999904632568, 8.5, 0.38999998569488525]
bar_stool_C[0].rotation = [0, 0, -3.1321678761290697]
bar_stool_C[0].optimize = 2
wall_info_panel[0].position = [3.0, 12.984931945800781, 0.5]
wall_info_panel[0].rotation = [0, 0, -1.5708571360921386]
wall_info_panel[0].optimize = 2
coffee_mug[0].position = [6.619999885559082, 6.25, 0.7950000166893005]
coffee_mug[0].rotation = [0, 0, 0.025024544325611065]
coffee_mug[0].optimize = 2
notebook_C[0].position = [4.0, 6.449999809265137, 1.059999942779541]
notebook_C[0].rotation = [0, 0, 0.0592117341187293]
notebook_C[0].optimize = 2
wayfinding_sign_C[0].position = [11.980216026306152, 8.600000381469727, 0.09000000357627869]
wayfinding_sign_C[0].rotation = [0, 0, 3.1415319654094116]
wayfinding_sign_C[0].optimize = 2
pen_holder_A[0].position = [3.4200000762939453, 3.5999999046325684, 0.800000011920929]
pen_holder_A[0].rotation = [0, 0, 0.03462658634231508]
pen_holder_A[0].optimize = 2
small_round_meeting_table_B[0].position = [6.449999809265137, 6.25, 0.3700000047683716]
small_round_meeting_table_B[0].rotation = [0, 0, 0.025132740109855806]
small_round_meeting_table_B[0].optimize = 2

