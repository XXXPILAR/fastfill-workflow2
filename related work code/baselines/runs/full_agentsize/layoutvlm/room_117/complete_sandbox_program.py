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
collaboration_chair_A = Assets(description="A black and gray office style armchair with thin armrests on protruding black metal beams.", size=[0.72, 0.72, 0.82], placements=[AssetInstance() for _ in range(1)])
framed_art_print_A = Assets(description="A picture inside of a metallic frame.", size=[0.04, 0.70, 0.90], placements=[AssetInstance() for _ in range(1)])
high_stool_A = Assets(description="high stool", size=[0.48, 0.45, 1.02], placements=[AssetInstance() for _ in range(1)])
planter_box_floor_A = Assets(description="A black metal aquarium with a slanted floor.", size=[0.42, 1.20, 0.72], placements=[AssetInstance() for _ in range(1)])
wall_greenery_panel_A = Assets(description="A poster consisting of carved dark wooden floral patterns.", size=[0.08, 1.20, 1.20], placements=[AssetInstance() for _ in range(1)])
high_collaboration_table_A = Assets(description="Table with wood top and black legs.", size=[0.75, 1.80, 1.05], placements=[AssetInstance() for _ in range(1)])
low_bookshelf_A = Assets(description="A shelving unit with many different compartments.", size=[0.38, 1.60, 0.90], placements=[AssetInstance() for _ in range(1)])
modular_lounge_sofa_A = Assets(description="A sofa with a grey material and black legs.", size=[0.90, 2.20, 0.78], placements=[AssetInstance() for _ in range(1)])
framed_art_print_B = Assets(description="A picture inside of a metallic frame.", size=[0.04, 0.70, 0.90], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="A brown book with silver corners.", size=[0.16, 0.22, 0.04], placements=[AssetInstance() for _ in range(1)])
side_table_round = Assets(description="A round table of striped wood with two legs cut out of the base and a grey top.", size=[0.55, 0.55, 0.52], placements=[AssetInstance() for _ in range(1)])
high_stool_B = Assets(description="high stool", size=[0.48, 0.45, 1.02], placements=[AssetInstance() for _ in range(1)])
framed_art_print_C = Assets(description="A picture inside of a metallic frame.", size=[0.04, 0.70, 0.90], placements=[AssetInstance() for _ in range(1)])
notebook = Assets(description="A black book with silver trim.", size=[0.15, 0.21, 0.02], placements=[AssetInstance() for _ in range(1)])
high_stool_C = Assets(description="high stool", size=[0.48, 0.45, 1.02], placements=[AssetInstance() for _ in range(1)])
high_collaboration_table_B = Assets(description="Table with wood top and black legs.", size=[0.75, 1.80, 1.05], placements=[AssetInstance() for _ in range(1)])
lounge_armchair = Assets(description="Gray fabric armchair with a rounded back and matching cushion.", size=[0.84, 0.82, 0.82], placements=[AssetInstance() for _ in range(1)])
wall_greenery_panel_B = Assets(description="A poster consisting of carved dark wooden floral patterns.", size=[0.08, 1.20, 1.20], placements=[AssetInstance() for _ in range(1)])
whiteboard_wall_panel_A = Assets(description="A poster of blueprints for a picture frame.", size=[0.05, 1.80, 1.20], placements=[AssetInstance() for _ in range(1)])
planter_box_floor_B = Assets(description="A black metal aquarium with a slanted floor.", size=[0.42, 1.20, 0.72], placements=[AssetInstance() for _ in range(1)])
modular_lounge_sofa_B = Assets(description="A sofa with a grey material and black legs.", size=[0.90, 2.20, 0.78], placements=[AssetInstance() for _ in range(1)])
high_stool_D = Assets(description="high stool", size=[0.48, 0.45, 1.02], placements=[AssetInstance() for _ in range(1)])
high_stool_E = Assets(description="high stool", size=[0.48, 0.45, 1.02], placements=[AssetInstance() for _ in range(1)])
collaboration_chair_B = Assets(description="A black and gray office style armchair with thin armrests on protruding black metal beams.", size=[0.72, 0.72, 0.82], placements=[AssetInstance() for _ in range(1)])
wall_greenery_panel_C = Assets(description="A poster consisting of carved dark wooden floral patterns.", size=[0.08, 1.20, 1.20], placements=[AssetInstance() for _ in range(1)])
framed_art_print_D = Assets(description="A picture inside of a metallic frame.", size=[0.04, 0.70, 0.90], placements=[AssetInstance() for _ in range(1)])
high_stool_F = Assets(description="high stool", size=[0.48, 0.45, 1.02], placements=[AssetInstance() for _ in range(1)])
throw_pillow_A = Assets(description="A large white pillow with golden edges.", size=[0.16, 0.50, 0.50], placements=[AssetInstance() for _ in range(1)])
project_table_A = Assets(description="A brown table with lots of pamphlets on it.", size=[0.90, 1.80, 0.75], placements=[AssetInstance() for _ in range(1)])
throw_pillow_B = Assets(description="A large white pillow with golden edges.", size=[0.16, 0.50, 0.50], placements=[AssetInstance() for _ in range(1)])
low_bookshelf_B = Assets(description="A shelving unit with many different compartments.", size=[0.38, 1.60, 0.90], placements=[AssetInstance() for _ in range(1)])
whiteboard_wall_panel_B = Assets(description="A poster of blueprints for a picture frame.", size=[0.05, 1.80, 1.20], placements=[AssetInstance() for _ in range(1)])
project_table_B = Assets(description="A brown table with lots of pamphlets on it.", size=[0.90, 1.80, 0.75], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="A brown book with silver corners.", size=[0.16, 0.22, 0.04], placements=[AssetInstance() for _ in range(1)])

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

collaboration_chair_A[0].position = [5.331574340893832, 3.5694590488823508, 0.41]
collaboration_chair_A[0].rotation = [0, 0, 0]
framed_art_print_A[0].position = [12.509766810340684, 1.1931355327771065, 0.45]
framed_art_print_A[0].rotation = [0, 0, 0]
high_stool_A[0].position = [4.152224566992475, 4.773979111985779, 0.51]
high_stool_A[0].rotation = [0, 0, 0]
planter_box_floor_A[0].position = [10.045269638316022, 2.670967984045287, 0.36]
planter_box_floor_A[0].rotation = [0, 0, 0]
wall_greenery_panel_A[0].position = [2.8862613201022005, 5.121841120577608, 0.6]
wall_greenery_panel_A[0].rotation = [0, 0, 0]
high_collaboration_table_A[0].position = [10.625068842585186, 3.2099813226272413, 0.525]
high_collaboration_table_A[0].rotation = [0, 0, 0]
low_bookshelf_A[0].position = [12.72136659506236, 4.158117256625461, 0.45]
low_bookshelf_A[0].rotation = [0, 0, 0]
modular_lounge_sofa_A[0].position = [6.739663375819215, 5.194442860483191, 0.39]
modular_lounge_sofa_A[0].rotation = [0, 0, 0]
framed_art_print_B[0].position = [5.795196692647474, 3.731261668852441, 0.45]
framed_art_print_B[0].rotation = [0, 0, 0]
book_A[0].position = [9.342872015284305, 3.587452869586534, 0.0175]
book_A[0].rotation = [0, 0, 0]
side_table_round[0].position = [1.378953822463036, 1.304826763239091, 0.26]
side_table_round[0].rotation = [0, 0, 0]
high_stool_B[0].position = [8.407651098061324, 3.5701469584235994, 0.51]
high_stool_B[0].rotation = [0, 0, 0]
framed_art_print_C[0].position = [9.24366311818507, 3.4769400270725086, 0.45]
framed_art_print_C[0].rotation = [0, 0, 0]
notebook[0].position = [4.7950170062757485, 4.89388489241542, 0.01]
notebook[0].rotation = [0, 0, 0]
high_stool_C[0].position = [10.117233886015049, 4.463967977797084, 0.51]
high_stool_C[0].rotation = [0, 0, 0]
high_collaboration_table_B[0].position = [11.979465872443642, 1.4139971404285312, 0.525]
high_collaboration_table_B[0].rotation = [0, 0, 0]
lounge_armchair[0].position = [10.439834881025915, 1.6334297091538124, 0.41]
lounge_armchair[0].rotation = [0, 0, 0]
wall_greenery_panel_B[0].position = [7.649056399936599, 4.102542183655316, 0.6]
wall_greenery_panel_B[0].rotation = [0, 0, 0]
whiteboard_wall_panel_A[0].position = [3.609677304225687, 4.48116284814053, 0.6]
whiteboard_wall_panel_A[0].rotation = [0, 0, 0]
planter_box_floor_B[0].position = [10.56775202968531, 2.652523515140767, 0.36]
planter_box_floor_B[0].rotation = [0, 0, 0]
modular_lounge_sofa_B[0].position = [3.6293378693842113, 4.057196820868197, 0.39]
modular_lounge_sofa_B[0].rotation = [0, 0, 0]
high_stool_D[0].position = [2.3648899976788957, 5.006588827167186, 0.51]
high_stool_D[0].rotation = [0, 0, 0]
high_stool_E[0].position = [12.617594734155823, 5.284660254723873, 0.51]
high_stool_E[0].rotation = [0, 0, 0]
collaboration_chair_B[0].position = [7.279973276484838, 3.6764673574652944, 0.41]
collaboration_chair_B[0].rotation = [0, 0, 0]
wall_greenery_panel_C[0].position = [4.098655492602079, 5.954768758153395, 0.6]
wall_greenery_panel_C[0].rotation = [0, 0, 0]
framed_art_print_D[0].position = [12.595723384250014, 4.1237009685963315, 0.45]
framed_art_print_D[0].rotation = [0, 0, 0]
high_stool_F[0].position = [1.1817130757930259, 1.7819612575473476, 0.51]
high_stool_F[0].rotation = [0, 0, 0]
throw_pillow_A[0].position = [5.44452387763904, 3.5874554614766296, 0.25]
throw_pillow_A[0].rotation = [0, 0, 0]
project_table_A[0].position = [0.6532214753879845, 2.1569663419842415, 0.375]
project_table_A[0].rotation = [0, 0, 0]
throw_pillow_B[0].position = [11.738196163616513, 1.7226351931373844, 0.25]
throw_pillow_B[0].rotation = [0, 0, 0]
low_bookshelf_B[0].position = [0.3512511439038182, 2.391509443985504, 0.45]
low_bookshelf_B[0].rotation = [0, 0, 0]
whiteboard_wall_panel_B[0].position = [12.231086229931535, 2.1936666292122178, 0.6]
whiteboard_wall_panel_B[0].rotation = [0, 0, 0]
project_table_B[0].position = [3.9955814355201844, 3.5230241451428252, 0.375]
project_table_B[0].rotation = [0, 0, 0]
book_B[0].position = [1.8573128848125533, 2.68229453060358, 0.0175]
book_B[0].rotation = [0, 0, 0]
collaboration_chair_A[0].position = [5.331574340893832, 3.5694590488823508, 0.41]
collaboration_chair_A[0].rotation = [0, 0, 0]
framed_art_print_A[0].position = [12.509766810340684, 1.1931355327771065, 0.45]
framed_art_print_A[0].rotation = [0, 0, 0]
high_stool_A[0].position = [4.152224566992475, 4.773979111985779, 0.51]
high_stool_A[0].rotation = [0, 0, 0]
planter_box_floor_A[0].position = [10.045269638316022, 2.670967984045287, 0.36]
planter_box_floor_A[0].rotation = [0, 0, 0]
wall_greenery_panel_A[0].position = [2.8862613201022005, 5.121841120577608, 0.6]
wall_greenery_panel_A[0].rotation = [0, 0, 0]
high_collaboration_table_A[0].position = [10.625068842585186, 3.2099813226272413, 0.525]
high_collaboration_table_A[0].rotation = [0, 0, 0]
low_bookshelf_A[0].position = [12.72136659506236, 4.158117256625461, 0.45]
low_bookshelf_A[0].rotation = [0, 0, 0]
modular_lounge_sofa_A[0].position = [6.739663375819215, 5.194442860483191, 0.39]
modular_lounge_sofa_A[0].rotation = [0, 0, 0]
framed_art_print_B[0].position = [5.795196692647474, 3.731261668852441, 0.45]
framed_art_print_B[0].rotation = [0, 0, 0]
book_A[0].position = [9.342872015284305, 3.587452869586534, 0.0175]
book_A[0].rotation = [0, 0, 0]
side_table_round[0].position = [1.378953822463036, 1.304826763239091, 0.26]
side_table_round[0].rotation = [0, 0, 0]
high_stool_B[0].position = [8.407651098061324, 3.5701469584235994, 0.51]
high_stool_B[0].rotation = [0, 0, 0]
framed_art_print_C[0].position = [9.24366311818507, 3.4769400270725086, 0.45]
framed_art_print_C[0].rotation = [0, 0, 0]
notebook[0].position = [4.7950170062757485, 4.89388489241542, 0.01]
notebook[0].rotation = [0, 0, 0]
high_stool_C[0].position = [10.117233886015049, 4.463967977797084, 0.51]
high_stool_C[0].rotation = [0, 0, 0]
high_collaboration_table_B[0].position = [11.979465872443642, 1.4139971404285312, 0.525]
high_collaboration_table_B[0].rotation = [0, 0, 0]
lounge_armchair[0].position = [10.439834881025915, 1.6334297091538124, 0.41]
lounge_armchair[0].rotation = [0, 0, 0]
wall_greenery_panel_B[0].position = [7.649056399936599, 4.102542183655316, 0.6]
wall_greenery_panel_B[0].rotation = [0, 0, 0]
whiteboard_wall_panel_A[0].position = [3.609677304225687, 4.48116284814053, 0.6]
whiteboard_wall_panel_A[0].rotation = [0, 0, 0]
planter_box_floor_B[0].position = [10.56775202968531, 2.652523515140767, 0.36]
planter_box_floor_B[0].rotation = [0, 0, 0]
modular_lounge_sofa_B[0].position = [3.6293378693842113, 4.057196820868197, 0.39]
modular_lounge_sofa_B[0].rotation = [0, 0, 0]
high_stool_D[0].position = [2.3648899976788957, 5.006588827167186, 0.51]
high_stool_D[0].rotation = [0, 0, 0]
high_stool_E[0].position = [12.617594734155823, 5.284660254723873, 0.51]
high_stool_E[0].rotation = [0, 0, 0]
collaboration_chair_B[0].position = [7.279973276484838, 3.6764673574652944, 0.41]
collaboration_chair_B[0].rotation = [0, 0, 0]
wall_greenery_panel_C[0].position = [4.098655492602079, 5.954768758153395, 0.6]
wall_greenery_panel_C[0].rotation = [0, 0, 0]
framed_art_print_D[0].position = [12.595723384250014, 4.1237009685963315, 0.45]
framed_art_print_D[0].rotation = [0, 0, 0]
high_stool_F[0].position = [1.1817130757930259, 1.7819612575473476, 0.51]
high_stool_F[0].rotation = [0, 0, 0]
throw_pillow_A[0].position = [5.44452387763904, 3.5874554614766296, 0.25]
throw_pillow_A[0].rotation = [0, 0, 0]
project_table_A[0].position = [0.6532214753879845, 2.1569663419842415, 0.375]
project_table_A[0].rotation = [0, 0, 0]
throw_pillow_B[0].position = [11.738196163616513, 1.7226351931373844, 0.25]
throw_pillow_B[0].rotation = [0, 0, 0]
low_bookshelf_B[0].position = [0.3512511439038182, 2.391509443985504, 0.45]
low_bookshelf_B[0].rotation = [0, 0, 0]
whiteboard_wall_panel_B[0].position = [12.231086229931535, 2.1936666292122178, 0.6]
whiteboard_wall_panel_B[0].rotation = [0, 0, 0]
project_table_B[0].position = [3.9955814355201844, 3.5230241451428252, 0.375]
project_table_B[0].rotation = [0, 0, 0]
book_B[0].position = [1.8573128848125533, 2.68229453060358, 0.0175]
book_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed-point constraints preserve the planned zones and clear circulation paths.
# The accompanying alignment constraint gives every new instance an explicit
# orientation constraint.
def place_at(asset, position, yaw):
    instance = asset[0]
    instance.position = position
    instance.rotation = [0, 0, yaw]
    anchor = AssetInstance(position=position, rotation=[0, 0, yaw])
    solver.distance_constraint(instance, anchor, 0, 0, weight=10)
    solver.align_with(instance, anchor)


def place_against_wall(asset, wall, position, yaw):
    # Keep wall-mounted and wall-backed objects attached to their intended wall.
    solver.against_wall(asset[0], wall)
    place_at(asset, position, yaw)


def place_on_surface(asset, surface, position, yaw):
    # The support constraint is specified first so it has priority over the
    # initial fixed-point estimate if the solver adjusts the furniture.
    solver.on_top_of(asset[0], surface[0])
    place_at(asset, position, yaw)


# ---------------------------------------------------------------------------
# Lounge group in the central 7 m x 4 m portion of the room.
# The sofas face one another across the side table, while the armchair closes
# the group from the north without blocking circulation along either side.
# ---------------------------------------------------------------------------
place_at(modular_lounge_sofa_A, [3.00, 3.25, 0.39], radians(0))
place_at(modular_lounge_sofa_B, [5.30, 3.25, 0.39], radians(180))
place_at(side_table_round, [4.15, 3.25, 0.26], radians(0))
place_at(lounge_armchair, [4.15, 4.80, 0.41], radians(-90))

solver.point_towards(modular_lounge_sofa_A[0], side_table_round[0])
solver.point_towards(modular_lounge_sofa_B[0], side_table_round[0])
solver.point_towards(lounge_armchair[0], side_table_round[0])
solver.distance_constraint(
    modular_lounge_sofa_A[0], side_table_round[0], 1.10, 1.25, weight=10
)
solver.distance_constraint(
    modular_lounge_sofa_B[0], side_table_round[0], 1.10, 1.25, weight=10
)
solver.distance_constraint(
    lounge_armchair[0], side_table_round[0], 1.45, 1.65, weight=10
)

# Soft furnishings sit on their respective sofas.
place_on_surface(
    throw_pillow_A,
    modular_lounge_sofa_A,
    [3.00, 3.25, 1.03],
    radians(0),
)
place_on_surface(
    throw_pillow_B,
    modular_lounge_sofa_B,
    [5.30, 3.25, 1.03],
    radians(180),
)
solver.align_with(throw_pillow_A[0], modular_lounge_sofa_A[0])
solver.align_with(throw_pillow_B[0], modular_lounge_sofa_B[0])

# The notebook (o0013) is explicitly supported by the round side table
# (o0010), as required.
place_on_surface(
    notebook,
    side_table_round,
    [4.15, 3.25, 0.53],
    radians(0),
)
solver.align_with(notebook[0], side_table_round[0])


# ---------------------------------------------------------------------------
# Project-work areas. One occupies the eastern side of the central room; the
# second uses the otherwise separate western bay. Chairs face their tables.
# ---------------------------------------------------------------------------
place_at(project_table_A, [7.50, 3.20, 0.375], radians(90))
place_at(collaboration_chair_A, [7.50, 4.25, 0.41], radians(-90))
solver.point_towards(collaboration_chair_A[0], project_table_A[0])
solver.distance_constraint(
    collaboration_chair_A[0], project_table_A[0], 1.00, 1.15, weight=10
)

place_at(project_table_B, [1.00, 2.00, 0.375], radians(0))
place_at(collaboration_chair_B, [1.00, 3.45, 0.41], radians(-90))
solver.point_towards(collaboration_chair_B[0], project_table_B[0])
solver.distance_constraint(
    collaboration_chair_B[0], project_table_B[0], 1.35, 1.55, weight=10
)

# Books are kept on the project tables rather than on the floor.
place_on_surface(book_A, project_table_A, [7.50, 3.20, 0.77], radians(90))
place_on_surface(book_B, project_table_B, [1.00, 2.00, 0.77], radians(0))
solver.align_with(book_A[0], project_table_A[0])
solver.align_with(book_B[0], project_table_B[0])


# ---------------------------------------------------------------------------
# Two standing-height collaboration stations in the right-hand room.
# Three stools serve each table from one side, retaining a central aisle.
# ---------------------------------------------------------------------------
place_at(high_collaboration_table_A, [11.50, 1.00, 0.525], radians(90))
place_at(high_stool_A, [10.75, 1.85, 0.51], radians(-90))
place_at(high_stool_B, [11.50, 1.85, 0.51], radians(-90))
place_at(high_stool_C, [12.25, 1.85, 0.51], radians(-90))

for stool_instance in (
    high_stool_A[0],
    high_stool_B[0],
    high_stool_C[0],
):
    solver.point_towards(stool_instance, high_collaboration_table_A[0])
    solver.distance_constraint(
        stool_instance,
        high_collaboration_table_A[0],
        0.80,
        1.20,
        weight=10,
    )

place_at(high_collaboration_table_B, [11.50, 3.65, 0.525], radians(90))
place_at(high_stool_D, [10.75, 4.50, 0.51], radians(-90))
place_at(high_stool_E, [11.50, 4.50, 0.51], radians(-90))
place_at(high_stool_F, [12.25, 4.50, 0.51], radians(-90))

for stool_instance in (
    high_stool_D[0],
    high_stool_E[0],
    high_stool_F[0],
):
    solver.point_towards(stool_instance, high_collaboration_table_B[0])
    solver.distance_constraint(
        stool_instance,
        high_collaboration_table_B[0],
        0.80,
        1.20,
        weight=10,
    )


# ---------------------------------------------------------------------------
# Floor storage and planters. The bookshelves use the uninterrupted north wall
# and are kept clear of the lounge and project-table footprints.
# ---------------------------------------------------------------------------
place_against_wall(
    low_bookshelf_A,
    walls[10],
    [3.00, 5.81, 0.45],
    radians(-90),
)
place_against_wall(
    low_bookshelf_B,
    walls[10],
    [8.00, 5.81, 0.45],
    radians(-90),
)

place_against_wall(
    planter_box_floor_A,
    walls[5],
    [12.79, 5.30, 0.36],
    radians(180),
)
place_against_wall(
    planter_box_floor_B,
    walls[1],
    [1.79, 0.65, 0.36],
    radians(0),
)


# ---------------------------------------------------------------------------
# Wall decorations. None are placed on the window-bearing wall at y=2, so all
# three windows remain unobstructed. Wall centers use half the object's
# thickness to put the rear surface directly against the corresponding wall.
# ---------------------------------------------------------------------------

# North wall, distributed between x=2 and x=9.
place_against_wall(
    wall_greenery_panel_A,
    walls[10],
    [3.00, 5.96, 1.50],
    radians(-90),
)
place_against_wall(
    whiteboard_wall_panel_A,
    walls[10],
    [5.00, 5.975, 1.50],
    radians(-90),
)
place_against_wall(
    framed_art_print_C,
    walls[10],
    [6.50, 5.98, 1.50],
    radians(-90),
)

# Short north wall of the western bay.
place_against_wall(
    framed_art_print_A,
    walls[12],
    [0.45, 3.98, 1.50],
    radians(-90),
)
place_against_wall(
    framed_art_print_B,
    walls[12],
    [1.30, 3.98, 1.50],
    radians(-90),
)

# West wall of the western bay.
place_against_wall(
    wall_greenery_panel_C,
    walls[13],
    [0.04, 2.00, 1.50],
    radians(0),
)

# East wall of the right-hand room. These are vertically separated from the
# low floor planters where their horizontal spans approach one another.
place_against_wall(
    framed_art_print_D,
    walls[5],
    [12.98, 0.75, 1.50],
    radians(180),
)
place_against_wall(
    wall_greenery_panel_B,
    walls[5],
    [12.96, 2.45, 1.50],
    radians(180),
)
place_against_wall(
    whiteboard_wall_panel_B,
    walls[5],
    [12.975, 4.05, 1.50],
    radians(180),
)

solver.constraints = []
high_collaboration_table_B[0].position = [11.5, 3.6500000953674316, 0.5249999761581421]
high_collaboration_table_B[0].rotation = [0, 0, 1.5990706612064889]
high_collaboration_table_B[0].optimize = 2
planter_box_floor_B[0].position = [1.7899993658065796, 0.6499999761581421, 0.36000001430511475]
planter_box_floor_B[0].rotation = [0, 0, -3.14159209900053]
planter_box_floor_B[0].optimize = 2
low_bookshelf_B[0].position = [8.0, 5.799962043762207, 0.44999998807907104]
low_bookshelf_B[0].rotation = [0, 0, -1.5707962830697917]
low_bookshelf_B[0].optimize = 2
collaboration_chair_B[0].position = [1.0, 3.450000047683716, 0.4099999964237213]
collaboration_chair_B[0].rotation = [0, 0, -1.5550883628776802]
collaboration_chair_B[0].optimize = 2
collaboration_chair_A[0].position = [7.5, 4.25, 0.4099999964237213]
collaboration_chair_A[0].rotation = [0, 0, -1.5550883628776802]
collaboration_chair_A[0].optimize = 2
notebook[0].position = [4.150000095367432, 3.25, 0.5299999713897705]
notebook[0].rotation = [0, 0, 0.034557518407144834]
notebook[0].optimize = 2
framed_art_print_D[0].position = [12.979999542236328, 0.75, 0.44999998807907104]
framed_art_print_D[0].rotation = [0, 0, -3.141592627468071]
framed_art_print_D[0].optimize = 2
throw_pillow_B[0].position = [5.300000190734863, 3.25, 1.0299999713897705]
throw_pillow_B[0].rotation = [0, 0, -3.1196015029291626]
throw_pillow_B[0].optimize = 2
wall_greenery_panel_B[0].position = [12.960000991821289, 2.450000047683716, 0.6000000238418579]
wall_greenery_panel_B[0].rotation = [0, 0, -3.14159260987648]
wall_greenery_panel_B[0].optimize = 2
modular_lounge_sofa_B[0].position = [5.300000190734863, 3.25, 0.38999998569488525]
modular_lounge_sofa_B[0].rotation = [0, 0, -3.1196015053037707]
modular_lounge_sofa_B[0].optimize = 2
high_stool_A[0].position = [10.75, 1.850000023841858, 0.5099999904632568]
high_stool_A[0].rotation = [0, 0, -1.5550883628776802]
high_stool_A[0].optimize = 2
throw_pillow_A[0].position = [3.0, 3.25, 1.0299999713897705]
throw_pillow_A[0].rotation = [0, 0, 0.021991150660630843]
throw_pillow_A[0].optimize = 2
high_stool_D[0].position = [10.75, 4.5, 0.5099999904632568]
high_stool_D[0].rotation = [0, 0, -1.5550883628776802]
high_stool_D[0].optimize = 2
framed_art_print_C[0].position = [6.5, 5.980000019073486, 0.44999998807907104]
framed_art_print_C[0].rotation = [0, 0, -1.5707962830697917]
framed_art_print_C[0].optimize = 2
lounge_armchair[0].position = [4.150000095367432, 4.800000190734863, 0.4099999964237213]
lounge_armchair[0].rotation = [0, 0, -1.5550883628776802]
lounge_armchair[0].optimize = 2
framed_art_print_B[0].position = [1.2999999523162842, 3.9800000190734863, 0.44999998807907104]
framed_art_print_B[0].rotation = [0, 0, -1.570796283095771]
framed_art_print_B[0].optimize = 2
whiteboard_wall_panel_A[0].position = [5.0, 5.963692665100098, 0.6000000238418579]
whiteboard_wall_panel_A[0].rotation = [0, 0, -1.5707962830697917]
whiteboard_wall_panel_A[0].optimize = 2
project_table_B[0].position = [1.0, 2.0, 0.375]
project_table_B[0].rotation = [0, 0, 0.021991148286022624]
project_table_B[0].optimize = 2
high_stool_B[0].position = [11.5, 1.850000023841858, 0.5099999904632568]
high_stool_B[0].rotation = [0, 0, -1.5550883628776802]
high_stool_B[0].optimize = 2
high_collaboration_table_A[0].position = [11.5, 1.0, 0.5249999761581421]
high_collaboration_table_A[0].rotation = [0, 0, 1.5990706612064889]
high_collaboration_table_A[0].optimize = 2
high_stool_C[0].position = [12.25, 1.850000023841858, 0.5099999904632568]
high_stool_C[0].rotation = [0, 0, -1.5550883628776802]
high_stool_C[0].optimize = 2
high_stool_E[0].position = [11.5, 4.5, 0.5099999904632568]
high_stool_E[0].rotation = [0, 0, -1.5550883628776802]
high_stool_E[0].optimize = 2
planter_box_floor_A[0].position = [12.789999961853027, 5.300000190734863, 0.36000001430511475]
planter_box_floor_A[0].rotation = [0, 0, -3.1415926098755635]
planter_box_floor_A[0].optimize = 2
book_A[0].position = [7.5, 3.200000047683716, 0.7699999809265137]
book_A[0].rotation = [0, 0, 1.5927874770522075]
book_A[0].optimize = 2
wall_greenery_panel_C[0].position = [2.1172990798950195, 2.0399999618530273, 0.6000000238418579]
wall_greenery_panel_C[0].rotation = [0, 0, 1.5745465114559807]
wall_greenery_panel_C[0].optimize = 2
book_B[0].position = [1.0, 2.0, 0.7699999809265137]
book_B[0].rotation = [0, 0, 0.021991150660630843]
book_B[0].optimize = 2
framed_art_print_A[0].position = [0.44999998807907104, 3.9800000190734863, 0.44999998807907104]
framed_art_print_A[0].rotation = [0, 0, -1.570796283095771]
framed_art_print_A[0].optimize = 2
modular_lounge_sofa_A[0].position = [3.0, 3.25, 0.38999998569488525]
modular_lounge_sofa_A[0].rotation = [0, 0, 0.021991148286022624]
modular_lounge_sofa_A[0].optimize = 2
wall_greenery_panel_A[0].position = [3.0, 5.960000038146973, 0.6000000238418579]
wall_greenery_panel_A[0].rotation = [0, 0, -1.5707962830697917]
wall_greenery_panel_A[0].optimize = 2
low_bookshelf_A[0].position = [3.0, 5.799962043762207, 0.44999998807907104]
low_bookshelf_A[0].rotation = [0, 0, -1.5707962830697917]
low_bookshelf_A[0].optimize = 2
high_stool_F[0].position = [12.25, 4.5, 0.5099999904632568]
high_stool_F[0].rotation = [0, 0, -1.5550883628776802]
high_stool_F[0].optimize = 2
whiteboard_wall_panel_B[0].position = [12.97499942779541, 4.050000190734863, 0.6000000238418579]
whiteboard_wall_panel_B[0].rotation = [0, 0, -3.1415926098899454]
whiteboard_wall_panel_B[0].optimize = 2
project_table_A[0].position = [7.5, 3.200000047683716, 0.375]
project_table_A[0].rotation = [0, 0, 1.5927874750809192]
project_table_A[0].optimize = 2
side_table_round[0].position = [4.150000095367432, 3.25, 0.25999999046325684]
side_table_round[0].rotation = [0, 0, 0.03455751882667646]
side_table_round[0].optimize = 2

