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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.00, 0.00, 0.00]),
    Wall(corner1=[2.00, 0.00, 0.00], corner2=[2.00, 2.00, 0.00]),
    Wall(corner1=[2.00, 2.00, 0.00], corner2=[10.00, 2.00, 0.00]),
    Wall(corner1=[10.00, 2.00, 0.00], corner2=[10.00, 0.00, 0.00]),
    Wall(corner1=[10.00, 0.00, 0.00], corner2=[13.00, 0.00, 0.00]),
    Wall(corner1=[13.00, 0.00, 0.00], corner2=[13.00, 6.00, 0.00]),
    Wall(corner1=[13.00, 6.00, 0.00], corner2=[11.00, 6.00, 0.00]),
    Wall(corner1=[11.00, 6.00, 0.00], corner2=[11.00, 5.00, 0.00]),
    Wall(corner1=[11.00, 5.00, 0.00], corner2=[9.00, 5.00, 0.00]),
    Wall(corner1=[9.00, 5.00, 0.00], corner2=[9.00, 6.00, 0.00]),
    Wall(corner1=[9.00, 6.00, 0.00], corner2=[2.00, 6.00, 0.00]),
    Wall(corner1=[2.00, 6.00, 0.00], corner2=[2.00, 4.00, 0.00]),
    Wall(corner1=[2.00, 4.00, 0.00], corner2=[0.00, 4.00, 0.00]),
    Wall(corner1=[0.00, 4.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
collaboration_chair_A = Assets(description="A black and gray office style armchair with thin armrests on protruding black metal beams.", size=[0.65, 0.65, 0.85], placements=[AssetInstance() for _ in range(1)])
framed_art_print_A = Assets(description="A picture inside of a metallic frame.", size=[0.04, 0.70, 0.90], placements=[AssetInstance() for _ in range(1)])
high_stool_A = Assets(description="high stool", size=[0.48, 0.45, 0.95], placements=[AssetInstance() for _ in range(1)])
planter_box_floor_A = Assets(description="A black metal aquarium with a slanted floor.", size=[0.40, 1.20, 0.65], placements=[AssetInstance() for _ in range(1)])
wall_greenery_panel_A = Assets(description="A poster consisting of carved dark wooden floral patterns.", size=[0.12, 1.00, 1.20], placements=[AssetInstance() for _ in range(1)])
high_collaboration_table_A = Assets(description="Table with wood top and black legs.", size=[0.80, 1.80, 1.05], placements=[AssetInstance() for _ in range(1)])
low_bookshelf_A = Assets(description="A shelving unit with many different compartments.", size=[0.35, 1.50, 0.85], placements=[AssetInstance() for _ in range(1)])
modular_lounge_sofa_A = Assets(description="A sofa with a grey material and black legs.", size=[0.90, 2.10, 0.80], placements=[AssetInstance() for _ in range(1)])
framed_art_print_B = Assets(description="A picture inside of a metallic frame.", size=[0.04, 0.70, 0.90], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="A brown book with silver corners.", size=[0.25, 0.18, 0.04], placements=[AssetInstance() for _ in range(1)])
side_table_round = Assets(description="A round table of striped wood with two legs cut out of the base and a grey top.", size=[0.55, 0.55, 0.50], placements=[AssetInstance() for _ in range(1)])
high_stool_B = Assets(description="high stool", size=[0.48, 0.45, 0.95], placements=[AssetInstance() for _ in range(1)])
framed_art_print_C = Assets(description="A picture inside of a metallic frame.", size=[0.04, 0.70, 0.90], placements=[AssetInstance() for _ in range(1)])
notebook = Assets(description="A black book with silver trim.", size=[0.21, 0.15, 0.02], placements=[AssetInstance() for _ in range(1)])
high_stool_C = Assets(description="high stool", size=[0.48, 0.45, 0.95], placements=[AssetInstance() for _ in range(1)])
high_collaboration_table_B = Assets(description="Table with wood top and black legs.", size=[0.80, 1.80, 1.05], placements=[AssetInstance() for _ in range(1)])
lounge_armchair = Assets(description="Gray fabric armchair with a rounded back and matching cushion.", size=[0.85, 0.85, 0.80], placements=[AssetInstance() for _ in range(1)])
wall_greenery_panel_B = Assets(description="A poster consisting of carved dark wooden floral patterns.", size=[0.12, 1.00, 1.20], placements=[AssetInstance() for _ in range(1)])
whiteboard_wall_panel_A = Assets(description="A poster of blueprints for a picture frame.", size=[0.05, 1.80, 1.20], placements=[AssetInstance() for _ in range(1)])
planter_box_floor_B = Assets(description="A black metal aquarium with a slanted floor.", size=[0.40, 1.20, 0.65], placements=[AssetInstance() for _ in range(1)])
modular_lounge_sofa_B = Assets(description="A sofa with a grey material and black legs.", size=[0.90, 2.10, 0.80], placements=[AssetInstance() for _ in range(1)])
high_stool_D = Assets(description="high stool", size=[0.48, 0.45, 0.95], placements=[AssetInstance() for _ in range(1)])
high_stool_E = Assets(description="high stool", size=[0.48, 0.45, 0.95], placements=[AssetInstance() for _ in range(1)])
collaboration_chair_B = Assets(description="A black and gray office style armchair with thin armrests on protruding black metal beams.", size=[0.65, 0.65, 0.85], placements=[AssetInstance() for _ in range(1)])
wall_greenery_panel_C = Assets(description="A poster consisting of carved dark wooden floral patterns.", size=[0.12, 1.00, 1.20], placements=[AssetInstance() for _ in range(1)])
framed_art_print_D = Assets(description="A picture inside of a metallic frame.", size=[0.04, 0.70, 0.90], placements=[AssetInstance() for _ in range(1)])
high_stool_F = Assets(description="high stool", size=[0.48, 0.45, 0.95], placements=[AssetInstance() for _ in range(1)])
throw_pillow_A = Assets(description="A large white pillow with golden edges.", size=[0.18, 0.50, 0.50], placements=[AssetInstance() for _ in range(1)])
project_table_A = Assets(description="A brown table with lots of pamphlets on it.", size=[0.80, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
throw_pillow_B = Assets(description="A large white pillow with golden edges.", size=[0.18, 0.50, 0.50], placements=[AssetInstance() for _ in range(1)])
low_bookshelf_B = Assets(description="A shelving unit with many different compartments.", size=[0.35, 1.50, 0.85], placements=[AssetInstance() for _ in range(1)])
whiteboard_wall_panel_B = Assets(description="A poster of blueprints for a picture frame.", size=[0.05, 1.80, 1.20], placements=[AssetInstance() for _ in range(1)])
project_table_B = Assets(description="A brown table with lots of pamphlets on it.", size=[0.80, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="A brown book with silver corners.", size=[0.25, 0.18, 0.04], placements=[AssetInstance() for _ in range(1)])

collaboration_chair_A[0].instance_id = 'collaboration_chair_A_0'
framed_art_print_A[0].instance_id = 'framed_art_print_A_0'
high_stool_A[0].instance_id = 'high_stool_A_0'
planter_box_floor_A[0].instance_id = 'planter_box_floor_A_0'
wall_greenery_panel_A[0].instance_id = 'wall_greenery_panel_A_0'
high_collaboration_table_A[0].instance_id = 'high_collaboration_table_A_0'
low_bookshelf_A[0].instance_id = 'low_bookshelf_A_0'
modular_lounge_sofa_A[0].instance_id = 'modular_lounge_sofa_A_0'
framed_art_print_B[0].instance_id = 'framed_art_print_B_0'
book_A[0].instance_id = 'book_A_0'
side_table_round[0].instance_id = 'side_table_round_0'
high_stool_B[0].instance_id = 'high_stool_B_0'
framed_art_print_C[0].instance_id = 'framed_art_print_C_0'
notebook[0].instance_id = 'notebook_0'
high_stool_C[0].instance_id = 'high_stool_C_0'
high_collaboration_table_B[0].instance_id = 'high_collaboration_table_B_0'
lounge_armchair[0].instance_id = 'lounge_armchair_0'
wall_greenery_panel_B[0].instance_id = 'wall_greenery_panel_B_0'
whiteboard_wall_panel_A[0].instance_id = 'whiteboard_wall_panel_A_0'
planter_box_floor_B[0].instance_id = 'planter_box_floor_B_0'
modular_lounge_sofa_B[0].instance_id = 'modular_lounge_sofa_B_0'
high_stool_D[0].instance_id = 'high_stool_D_0'
high_stool_E[0].instance_id = 'high_stool_E_0'
collaboration_chair_B[0].instance_id = 'collaboration_chair_B_0'
wall_greenery_panel_C[0].instance_id = 'wall_greenery_panel_C_0'
framed_art_print_D[0].instance_id = 'framed_art_print_D_0'
high_stool_F[0].instance_id = 'high_stool_F_0'
throw_pillow_A[0].instance_id = 'throw_pillow_A_0'
project_table_A[0].instance_id = 'project_table_A_0'
throw_pillow_B[0].instance_id = 'throw_pillow_B_0'
low_bookshelf_B[0].instance_id = 'low_bookshelf_B_0'
whiteboard_wall_panel_B[0].instance_id = 'whiteboard_wall_panel_B_0'
project_table_B[0].instance_id = 'project_table_B_0'
book_B[0].instance_id = 'book_B_0'
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

collaboration_chair_A[0].position = [5.898626732351267, 5.007818064359601, 0.425]
collaboration_chair_A[0].rotation = [0, 0, 0]
framed_art_print_A[0].position = [9.820309819114188, 4.014361266407537, 0.45]
framed_art_print_A[0].rotation = [0, 0, 0]
high_stool_A[0].position = [11.544161164486276, 1.7463961276765003, 0.475]
high_stool_A[0].rotation = [0, 0, 0]
planter_box_floor_A[0].position = [11.907713405455416, 3.278080948514555, 0.325]
planter_box_floor_A[0].rotation = [0, 0, 0]
wall_greenery_panel_A[0].position = [1.319419956936873, 2.610537299726297, 0.6]
wall_greenery_panel_A[0].rotation = [0, 0, 0]
high_collaboration_table_A[0].position = [11.984786996547438, 2.1278836574311133, 0.525]
high_collaboration_table_A[0].rotation = [0, 0, 0]
low_bookshelf_A[0].position = [10.007063892534948, 0.19270948489824957, 0.425]
low_bookshelf_A[0].rotation = [0, 0, 0]
modular_lounge_sofa_A[0].position = [1.440248532430127, 2.5265051162370353, 0.4]
modular_lounge_sofa_A[0].rotation = [0, 0, 0]
framed_art_print_B[0].position = [5.3414285519592015, 5.72853476804632, 0.45]
framed_art_print_B[0].rotation = [0, 0, 0]
book_A[0].position = [12.303632516981141, 2.697626409900429, 0.0175]
book_A[0].rotation = [0, 0, 0]
side_table_round[0].position = [6.615968371710172, 2.5176489480142887, 0.25]
side_table_round[0].rotation = [0, 0, 0]
high_stool_B[0].position = [0.19815826553572424, 0.3010754646617284, 0.475]
high_stool_B[0].rotation = [0, 0, 0]
framed_art_print_C[0].position = [6.626175455160258, 2.240869850226126, 0.45]
framed_art_print_C[0].rotation = [0, 0, 0]
notebook[0].position = [9.614666514708686, 3.5198239666287225, 0.01]
notebook[0].rotation = [0, 0, 0]
high_stool_C[0].position = [2.062106014262256, 2.269148574457423, 0.475]
high_stool_C[0].rotation = [0, 0, 0]
high_collaboration_table_B[0].position = [11.791420931625776, 0.313364491985616, 0.525]
high_collaboration_table_B[0].rotation = [0, 0, 0]
lounge_armchair[0].position = [10.215807699705541, 4.939544972081781, 0.4]
lounge_armchair[0].rotation = [0, 0, 0]
wall_greenery_panel_B[0].position = [7.892640498376242, 2.9590201196882804, 0.6]
wall_greenery_panel_B[0].rotation = [0, 0, 0]
whiteboard_wall_panel_A[0].position = [4.056831299300761, 3.117820522113513, 0.6]
whiteboard_wall_panel_A[0].rotation = [0, 0, 0]
planter_box_floor_B[0].position = [11.56840951046485, 2.497782172918293, 0.325]
planter_box_floor_B[0].rotation = [0, 0, 0]
modular_lounge_sofa_B[0].position = [11.363962000509854, 3.909101983821922, 0.4]
modular_lounge_sofa_B[0].rotation = [0, 0, 0]
high_stool_D[0].position = [9.905541040853413, 3.8646678960442387, 0.475]
high_stool_D[0].rotation = [0, 0, 0]
high_stool_E[0].position = [11.490192549171399, 1.6767790457244192, 0.475]
high_stool_E[0].rotation = [0, 0, 0]
collaboration_chair_B[0].position = [5.805044621315256, 4.92576933817709, 0.425]
collaboration_chair_B[0].rotation = [0, 0, 0]
wall_greenery_panel_C[0].position = [10.505727103987658, 2.7585989331029275, 0.6]
wall_greenery_panel_C[0].rotation = [0, 0, 0]
framed_art_print_D[0].position = [7.97783391538918, 5.929204126672152, 0.45]
framed_art_print_D[0].rotation = [0, 0, 0]
high_stool_F[0].position = [0.6025864181820986, 1.5533984192144037, 0.475]
high_stool_F[0].rotation = [0, 0, 0]
throw_pillow_A[0].position = [11.867361260007499, 5.461720921786426, 0.25]
throw_pillow_A[0].rotation = [0, 0, 0]
project_table_A[0].position = [1.4249418152212827, 3.636443776539333, 0.375]
project_table_A[0].rotation = [0, 0, 0]
throw_pillow_B[0].position = [12.841153368924228, 2.9934280542055687, 0.25]
throw_pillow_B[0].rotation = [0, 0, 0]
low_bookshelf_B[0].position = [2.7072459374173232, 4.435934718936002, 0.425]
low_bookshelf_B[0].rotation = [0, 0, 0]
whiteboard_wall_panel_B[0].position = [12.868833382845214, 2.075468186548046, 0.6]
whiteboard_wall_panel_B[0].rotation = [0, 0, 0]
project_table_B[0].position = [8.379196920998568, 5.588051451422951, 0.375]
project_table_B[0].rotation = [0, 0, 0]
book_B[0].position = [12.648738330258505, 4.071003760569107, 0.0175]
book_B[0].rotation = [0, 0, 0]
collaboration_chair_A[0].position = [5.898626732351267, 5.007818064359601, 0.425]
collaboration_chair_A[0].rotation = [0, 0, 0]
framed_art_print_A[0].position = [9.820309819114188, 4.014361266407537, 0.45]
framed_art_print_A[0].rotation = [0, 0, 0]
high_stool_A[0].position = [11.544161164486276, 1.7463961276765003, 0.475]
high_stool_A[0].rotation = [0, 0, 0]
planter_box_floor_A[0].position = [11.907713405455416, 3.278080948514555, 0.325]
planter_box_floor_A[0].rotation = [0, 0, 0]
wall_greenery_panel_A[0].position = [1.319419956936873, 2.610537299726297, 0.6]
wall_greenery_panel_A[0].rotation = [0, 0, 0]
high_collaboration_table_A[0].position = [11.984786996547438, 2.1278836574311133, 0.525]
high_collaboration_table_A[0].rotation = [0, 0, 0]
low_bookshelf_A[0].position = [10.007063892534948, 0.19270948489824957, 0.425]
low_bookshelf_A[0].rotation = [0, 0, 0]
modular_lounge_sofa_A[0].position = [1.440248532430127, 2.5265051162370353, 0.4]
modular_lounge_sofa_A[0].rotation = [0, 0, 0]
framed_art_print_B[0].position = [5.3414285519592015, 5.72853476804632, 0.45]
framed_art_print_B[0].rotation = [0, 0, 0]
book_A[0].position = [12.303632516981141, 2.697626409900429, 0.0175]
book_A[0].rotation = [0, 0, 0]
side_table_round[0].position = [6.615968371710172, 2.5176489480142887, 0.25]
side_table_round[0].rotation = [0, 0, 0]
high_stool_B[0].position = [0.19815826553572424, 0.3010754646617284, 0.475]
high_stool_B[0].rotation = [0, 0, 0]
framed_art_print_C[0].position = [6.626175455160258, 2.240869850226126, 0.45]
framed_art_print_C[0].rotation = [0, 0, 0]
notebook[0].position = [9.614666514708686, 3.5198239666287225, 0.01]
notebook[0].rotation = [0, 0, 0]
high_stool_C[0].position = [2.062106014262256, 2.269148574457423, 0.475]
high_stool_C[0].rotation = [0, 0, 0]
high_collaboration_table_B[0].position = [11.791420931625776, 0.313364491985616, 0.525]
high_collaboration_table_B[0].rotation = [0, 0, 0]
lounge_armchair[0].position = [10.215807699705541, 4.939544972081781, 0.4]
lounge_armchair[0].rotation = [0, 0, 0]
wall_greenery_panel_B[0].position = [7.892640498376242, 2.9590201196882804, 0.6]
wall_greenery_panel_B[0].rotation = [0, 0, 0]
whiteboard_wall_panel_A[0].position = [4.056831299300761, 3.117820522113513, 0.6]
whiteboard_wall_panel_A[0].rotation = [0, 0, 0]
planter_box_floor_B[0].position = [11.56840951046485, 2.497782172918293, 0.325]
planter_box_floor_B[0].rotation = [0, 0, 0]
modular_lounge_sofa_B[0].position = [11.363962000509854, 3.909101983821922, 0.4]
modular_lounge_sofa_B[0].rotation = [0, 0, 0]
high_stool_D[0].position = [9.905541040853413, 3.8646678960442387, 0.475]
high_stool_D[0].rotation = [0, 0, 0]
high_stool_E[0].position = [11.490192549171399, 1.6767790457244192, 0.475]
high_stool_E[0].rotation = [0, 0, 0]
collaboration_chair_B[0].position = [5.805044621315256, 4.92576933817709, 0.425]
collaboration_chair_B[0].rotation = [0, 0, 0]
wall_greenery_panel_C[0].position = [10.505727103987658, 2.7585989331029275, 0.6]
wall_greenery_panel_C[0].rotation = [0, 0, 0]
framed_art_print_D[0].position = [7.97783391538918, 5.929204126672152, 0.45]
framed_art_print_D[0].rotation = [0, 0, 0]
high_stool_F[0].position = [0.6025864181820986, 1.5533984192144037, 0.475]
high_stool_F[0].rotation = [0, 0, 0]
throw_pillow_A[0].position = [11.867361260007499, 5.461720921786426, 0.25]
throw_pillow_A[0].rotation = [0, 0, 0]
project_table_A[0].position = [1.4249418152212827, 3.636443776539333, 0.375]
project_table_A[0].rotation = [0, 0, 0]
throw_pillow_B[0].position = [12.841153368924228, 2.9934280542055687, 0.25]
throw_pillow_B[0].rotation = [0, 0, 0]
low_bookshelf_B[0].position = [2.7072459374173232, 4.435934718936002, 0.425]
low_bookshelf_B[0].rotation = [0, 0, 0]
whiteboard_wall_panel_B[0].position = [12.868833382845214, 2.075468186548046, 0.6]
whiteboard_wall_panel_B[0].rotation = [0, 0, 0]
project_table_B[0].position = [8.379196920998568, 5.588051451422951, 0.375]
project_table_B[0].rotation = [0, 0, 0]
book_B[0].position = [12.648738330258505, 4.071003760569107, 0.0175]
book_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the actual polygon coordinates: the central strip begins at y=2,
# and the recess between x=9 and x=11 must remain empty above y=5.
# Keep the three window bays on y=2 free of wall-mounted decorations.
#
# Records contain: asset, center, yaw in degrees, supporting wall (if any).
# Furniture dimensions are interpreted in their unrotated local axes.
_layout_records = [
    # Lounge seating in the west end, with a second sofa on the north wall.
    (modular_lounge_sofa_A, [0.45, 2.50, 0.40], 0, 13),
    (modular_lounge_sofa_B, [3.40, 5.55, 0.40], -90, 10),
    (side_table_round, [1.35, 3.35, 0.25], 0, None),
    (lounge_armchair, [2.90, 3.35, 0.40], 180, None),

    # Two standing collaboration stations, set back from the windows.
    (high_collaboration_table_A, [5.30, 3.25, 0.525], 0, None),
    (high_stool_A, [4.45, 2.75, 0.475], 0, None),
    (high_stool_B, [4.45, 3.65, 0.475], 0, None),
    (high_stool_C, [6.15, 3.25, 0.475], 180, None),

    (high_collaboration_table_B, [8.00, 3.25, 0.525], 0, None),
    (high_stool_D, [7.15, 2.75, 0.475], 0, None),
    (high_stool_E, [7.15, 3.65, 0.475], 0, None),
    (high_stool_F, [8.85, 3.25, 0.475], 180, None),

    # Seated project work in the wider eastern wing.
    (project_table_A, [11.60, 1.20, 0.375], 90, None),
    (collaboration_chair_A, [11.60, 2.10, 0.425], -90, None),
    (project_table_B, [11.90, 4.60, 0.375], 0, None),
    (collaboration_chair_B, [10.80, 4.60, 0.425], 0, None),

    # Low storage and planting remain outside the main circulation band.
    (low_bookshelf_A, [5.70, 5.825, 0.425], -90, 10),
    (low_bookshelf_B, [12.825, 2.90, 0.425], 180, 5),
    (planter_box_floor_A, [1.80, 0.85, 0.325], 180, 1),
    (planter_box_floor_B, [7.40, 5.80, 0.325], -90, 10),

    # Wall-mounted objects: explicit heights prevent placement on the floor.
    (framed_art_print_A, [0.02, 2.00, 1.80], 0, 13),
    (framed_art_print_B, [3.40, 5.98, 1.80], -90, 10),
    (framed_art_print_C, [11.60, 0.02, 1.80], 90, 4),
    (framed_art_print_D, [10.00, 4.98, 1.80], -90, 8),
    (wall_greenery_panel_A, [0.06, 3.40, 1.85], 0, 13),
    (wall_greenery_panel_B, [8.20, 5.94, 1.85], -90, 10),
    (wall_greenery_panel_C, [12.94, 1.20, 1.85], 180, 5),
    (whiteboard_wall_panel_A, [5.70, 5.975, 1.85], -90, 10),
    (whiteboard_wall_panel_B, [12.975, 4.80, 1.85], 180, 5),

    # Small objects have explicit support constraints below.
    (notebook, [1.35, 3.35, 0.51], 0, None),
    (book_A, [11.30, 1.20, 0.77], 90, None),
    (book_B, [11.90, 4.85, 0.77], 0, None),
    (throw_pillow_A, [0.45, 2.00, 1.05], 0, None),
    (throw_pillow_B, [3.80, 5.55, 1.05], -90, None),
]

# Initialize every existing placement without replacing the supplied assets.
for _asset, _center, _yaw, _wall_index in _layout_records:
    _asset[0].position = list(_center)
    _asset[0].rotation = [0, 0, radians(_yaw)]

# Register support relationships first: these take priority over other
# constraints when a support surface requires a height adjustment.
_support_pairs = [
    (notebook, side_table_round),
    (book_A, project_table_A),
    (book_B, project_table_B),
    (throw_pillow_A, modular_lounge_sofa_A),
    (throw_pillow_B, modular_lounge_sofa_B),
]
for _item, _support in _support_pairs:
    solver.on_top_of(_item[0], _support[0])

# Preserve wall attachment and mounting height. For freestanding objects,
# small anchor neighborhoods preserve the planned clearances while allowing
# limited adjustment. Fixed points are references, not additional scene assets.
_supported_ids = {id(_item) for _item, _support in _support_pairs}

for _asset, _center, _yaw, _wall_index in _layout_records:
    if _wall_index is not None:
        solver.against_wall(_asset[0], walls[_wall_index])

    _reference = AssetInstance(
        position=list(_center),
        rotation=[0, 0, radians(_yaw)],
    )

    # Supported objects receive relative position constraints below, so their
    # positions can follow their supporting furniture.
    if id(_asset) not in _supported_ids:
        _tolerance = 0.0 if _wall_index is not None else 0.08
        solver.distance_constraint(
            _asset[0], _reference, 0, _tolerance, weight=10
        )

    # Every instance, including decorations and tabletop objects, has an
    # explicit orientation constraint.
    solver.align_with(_asset[0], _reference)

# Maintain tabletop and cushion positions relative to their supports.
# Distances are between 3-D bounding-box centers, including height differences.
for _item, _support in _support_pairs:
    _relative_distance = sum(
        (_item[0].position[_axis] - _support[0].position[_axis]) ** 2
        for _axis in range(3)
    ) ** 0.5
    solver.distance_constraint(
        _item[0], _support[0],
        _relative_distance, _relative_distance,
        weight=10,
    )
    solver.align_with(_item[0], _support[0])

# Stool-to-table relationships retain usable clearance and facing direction.
for _seat, _table in [
    (high_stool_A, high_collaboration_table_A),
    (high_stool_B, high_collaboration_table_A),
    (high_stool_C, high_collaboration_table_A),
    (high_stool_D, high_collaboration_table_B),
    (high_stool_E, high_collaboration_table_B),
    (high_stool_F, high_collaboration_table_B),
]:
    solver.distance_constraint(_seat[0], _table[0], 0.80, 1.05, weight=10)
    # Seats on each long side face across the table rather than diagonally.
    _seat_angle = 0 if _seat[0].position[0] < _table[0].position[0] else 180
    solver.align_with(_seat[0], _table[0], angle=_seat_angle)

for _seat, _table in [
    (collaboration_chair_A, project_table_A),
    (collaboration_chair_B, project_table_B),
]:
    solver.distance_constraint(_seat[0], _table[0], 0.88, 1.18, weight=10)
    solver.point_towards(_seat[0], _table[0])

# The lounge chair faces the side-table area; keep a comfortable gap.
solver.distance_constraint(
    lounge_armchair[0], side_table_round[0], 1.45, 1.70, weight=10
)
solver.point_towards(lounge_armchair[0], side_table_round[0])
solver.distance_constraint(
    side_table_round[0], modular_lounge_sofa_A[0], 1.20, 1.40, weight=10
)

solver.constraints = []
framed_art_print_C[0].position = [11.600000381469727, 0.019999999552965164, 0.44999998807907104]
framed_art_print_C[0].rotation = [0, 0, 1.5707963705200017]
framed_art_print_C[0].optimize = 2
low_bookshelf_B[0].position = [12.824999809265137, 2.9000000953674316, 0.42500001192092896]
low_bookshelf_B[0].rotation = [0, 0, -3.141592609890311]
low_bookshelf_B[0].optimize = 2
lounge_armchair[0].position = [2.9000000953674316, 3.3499999046325684, 0.4000000059604645]
lounge_armchair[0].rotation = [0, 0, -3.125884689672577]
lounge_armchair[0].optimize = 2
whiteboard_wall_panel_B[0].position = [12.97499942779541, 4.800000190734863, 0.6000000238418579]
whiteboard_wall_panel_B[0].rotation = [0, 0, -3.1415926098899454]
whiteboard_wall_panel_B[0].optimize = 2
side_table_round[0].position = [1.350000023841858, 3.3499999046325684, 0.25]
side_table_round[0].rotation = [0, 0, 0.02827433441159227]
side_table_round[0].optimize = 2
wall_greenery_panel_B[0].position = [8.199999809265137, 5.940000057220459, 0.6000000238418579]
wall_greenery_panel_B[0].rotation = [0, 0, -1.5707962830697917]
wall_greenery_panel_B[0].optimize = 2
collaboration_chair_B[0].position = [10.800000190734863, 4.599999904632568, 0.42500001192092896]
collaboration_chair_B[0].rotation = [0, 0, 0.0157079639172164]
collaboration_chair_B[0].optimize = 2
low_bookshelf_A[0].position = [5.699999809265137, 5.824999809265137, 0.42500001192092896]
low_bookshelf_A[0].rotation = [0, 0, -1.5707962830697917]
low_bookshelf_A[0].optimize = 2
high_collaboration_table_B[0].position = [8.0, 3.25, 0.5249999761581421]
high_collaboration_table_B[0].rotation = [0, 0, 0.02827433441159227]
high_collaboration_table_B[0].optimize = 2
high_stool_E[0].position = [7.150000095367432, 3.6500000953674316, 0.4749999940395355]
high_stool_E[0].rotation = [0, 0, 0.028274331615362035]
high_stool_E[0].optimize = 2
high_stool_B[0].position = [4.449999809265137, 3.6500000953674316, 0.4749999940395355]
high_stool_B[0].rotation = [0, 0, 0.028274331615362035]
high_stool_B[0].optimize = 2
high_stool_C[0].position = [6.150000095367432, 3.25, 0.4749999940395355]
high_stool_C[0].rotation = [0, 0, -3.113318233784282]
high_stool_C[0].optimize = 2
throw_pillow_A[0].position = [0.1949457973241806, 1.7218016386032104, 1.0499999523162842]
throw_pillow_A[0].rotation = [0, 0, 3.108840008438566e-08]
throw_pillow_A[0].optimize = 2
book_A[0].position = [10.998039245605469, 1.2000000476837158, 0.7699999809265137]
book_A[0].rotation = [0, 0, 1.595929065963398]
book_A[0].optimize = 2
framed_art_print_B[0].position = [3.4000000953674316, 5.980000019073486, 0.44999998807907104]
framed_art_print_B[0].rotation = [0, 0, -1.5707962830697917]
framed_art_print_B[0].optimize = 2
collaboration_chair_A[0].position = [11.600000381469727, 2.0999999046325684, 0.42500001192092896]
collaboration_chair_A[0].rotation = [0, 0, -1.5550883628776802]
collaboration_chair_A[0].optimize = 2
notebook[0].position = [1.350000023841858, 3.3499999046325684, 0.5099999904632568]
notebook[0].rotation = [0, 0, 0.028274331615362035]
notebook[0].optimize = 2
framed_art_print_D[0].position = [10.0, 4.650179386138916, 0.44999998807907104]
framed_art_print_D[0].rotation = [0, 0, 5.672727983445515e-08]
framed_art_print_D[0].optimize = 2
modular_lounge_sofa_B[0].position = [3.4000000953674316, 5.52701997756958, 0.4000000059604645]
modular_lounge_sofa_B[0].rotation = [0, 0, -1.5707962830617057]
modular_lounge_sofa_B[0].optimize = 2
high_stool_D[0].position = [7.150000095367432, 2.75, 0.4749999940395355]
high_stool_D[0].rotation = [0, 0, 0.028274331615362035]
high_stool_D[0].optimize = 2
project_table_A[0].position = [11.600000381469727, 1.2000000476837158, 0.375]
project_table_A[0].rotation = [0, 0, 1.5959290669047523]
project_table_A[0].optimize = 2
framed_art_print_A[0].position = [1.9835716485977173, 2.0199999809265137, 0.44999998807907104]
framed_art_print_A[0].rotation = [0, 0, 1.572309600042857]
framed_art_print_A[0].optimize = 2
book_B[0].position = [11.899999618530273, 5.1981520652771, 0.7699999809265137]
book_B[0].rotation = [0, 0, 0.025132745679198647]
book_B[0].optimize = 2
high_collaboration_table_A[0].position = [5.300000190734863, 3.25, 0.5249999761581421]
high_collaboration_table_A[0].rotation = [0, 0, 0.02827433441159227]
high_collaboration_table_A[0].optimize = 2
high_stool_F[0].position = [8.850000381469727, 3.25, 0.4749999940395355]
high_stool_F[0].rotation = [0, 0, -3.113318233784282]
high_stool_F[0].optimize = 2
whiteboard_wall_panel_A[0].position = [5.699999809265137, 5.963692665100098, 0.6000000238418579]
whiteboard_wall_panel_A[0].rotation = [0, 0, -1.5707962830697917]
whiteboard_wall_panel_A[0].optimize = 2
high_stool_A[0].position = [4.449999809265137, 2.75, 0.4749999940395355]
high_stool_A[0].rotation = [0, 0, 0.028274331615362035]
high_stool_A[0].optimize = 2
planter_box_floor_A[0].position = [1.7999999523162842, 0.8500000238418579, 0.32499998807907104]
planter_box_floor_A[0].rotation = [0, 0, -3.1415926097491567]
planter_box_floor_A[0].optimize = 2
modular_lounge_sofa_A[0].position = [0.45000001788139343, 2.5, 0.4000000059604645]
modular_lounge_sofa_A[0].rotation = [0, 0, 3.122130241268566e-08]
modular_lounge_sofa_A[0].optimize = 2
throw_pillow_B[0].position = [4.106691837310791, 5.850563049316406, 1.0499999523162842]
throw_pillow_B[0].rotation = [0, 0, -1.5707962831289293]
throw_pillow_B[0].optimize = 2
wall_greenery_panel_A[0].position = [0.06000000610947609, 3.4000000953674316, 0.6000000238418579]
wall_greenery_panel_A[0].rotation = [0, 0, 3.997297382345782e-08]
wall_greenery_panel_A[0].optimize = 2
project_table_B[0].position = [11.899999618530273, 4.599999904632568, 0.375]
project_table_B[0].rotation = [0, 0, 0.025132740109855806]
project_table_B[0].optimize = 2
planter_box_floor_B[0].position = [7.400000095367432, 5.800000190734863, 0.32499998807907104]
planter_box_floor_B[0].rotation = [0, 0, -1.5707962830697917]
planter_box_floor_B[0].optimize = 2
wall_greenery_panel_C[0].position = [12.939998626708984, 1.2000000476837158, 0.6000000238418579]
wall_greenery_panel_C[0].rotation = [0, 0, -3.1415926098835842]
wall_greenery_panel_C[0].optimize = 2

