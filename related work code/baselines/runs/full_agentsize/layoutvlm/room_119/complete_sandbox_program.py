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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[5.00, 0.00, 0.00]),
    Wall(corner1=[5.00, 0.00, 0.00], corner2=[5.00, 7.00, 0.00]),
    Wall(corner1=[5.00, 7.00, 0.00], corner2=[0.00, 7.00, 0.00]),
    Wall(corner1=[0.00, 7.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
storage_cabinet_A = Assets(description="A tall orange brown dresser with two vertical doors.", size=[0.50, 1.00, 1.90], placements=[AssetInstance() for _ in range(1)])
floor_lamp_A = Assets(description="A floor lamp on a square wooden base, with a white shade.", size=[0.42, 0.42, 1.60], placements=[AssetInstance() for _ in range(1)])
side_meeting_table = Assets(description="A low table with a round brown top.", size=[0.75, 0.75, 0.45], placements=[AssetInstance() for _ in range(1)])
wall_shelf_A = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.25, 1.20, 0.30], placements=[AssetInstance() for _ in range(1)])
wall_artwork_A = Assets(description="A stylized painting of koi framed with a black back and border.", size=[0.04, 1.00, 0.70], placements=[AssetInstance() for _ in range(1)])
floor_lamp_B = Assets(description="A floor lamp on a square wooden base, with a white shade.", size=[0.42, 0.42, 1.60], placements=[AssetInstance() for _ in range(1)])
side_meeting_chair_A = Assets(description="A black chair with wooden legs.", size=[0.58, 0.55, 0.82], placements=[AssetInstance() for _ in range(1)])
conference_table = Assets(description="A long white table with two black spines.", size=[1.20, 3.20, 0.75], placements=[AssetInstance() for _ in range(1)])
conference_chair_A = Assets(description="It is a chair with short cloth covered arms.", size=[0.64, 0.62, 0.88], placements=[AssetInstance() for _ in range(1)])
wall_artwork_B = Assets(description="A stylized painting of koi framed with a black back and border.", size=[0.04, 1.00, 0.70], placements=[AssetInstance() for _ in range(1)])
side_meeting_chair_B = Assets(description="A black chair with wooden legs.", size=[0.58, 0.55, 0.82], placements=[AssetInstance() for _ in range(1)])
floor_coat_stand_A = Assets(description="The coatrack is wooden with a round bottom.", size=[0.50, 0.50, 1.75], placements=[AssetInstance() for _ in range(1)])
conference_chair_B = Assets(description="It is a chair with short cloth covered arms.", size=[0.64, 0.62, 0.88], placements=[AssetInstance() for _ in range(1)])
floor_planter_A = Assets(description="A cylindrical white flower pot with five trees of varying sizes.", size=[0.75, 0.75, 1.80], placements=[AssetInstance() for _ in range(1)])
wall_artwork_C = Assets(description="A stylized painting of koi framed with a black back and border.", size=[0.04, 1.00, 0.70], placements=[AssetInstance() for _ in range(1)])
tray_with_cups = Assets(description="A board for playing checkers that is brown and white.", size=[0.35, 0.50, 0.05], placements=[AssetInstance() for _ in range(1)])
floor_planter_B = Assets(description="A cylindrical white flower pot with five trees of varying sizes.", size=[0.75, 0.75, 1.80], placements=[AssetInstance() for _ in range(1)])
wall_whiteboard = Assets(description="A chalkboard with prices.", size=[0.05, 1.80, 1.10], placements=[AssetInstance() for _ in range(1)])
wall_shelf_B = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.25, 1.20, 0.30], placements=[AssetInstance() for _ in range(1)])
floor_coat_stand_B = Assets(description="The coatrack is wooden with a round bottom.", size=[0.50, 0.50, 1.75], placements=[AssetInstance() for _ in range(1)])
conference_chair_C = Assets(description="It is a chair with short cloth covered arms.", size=[0.64, 0.62, 0.88], placements=[AssetInstance() for _ in range(1)])
sideboard_credenza = Assets(description="A light brown wooden console table with 4 cabinets on its front.", size=[0.48, 1.80, 0.80], placements=[AssetInstance() for _ in range(1)])
floor_planter_C = Assets(description="A cylindrical white flower pot with five trees of varying sizes.", size=[0.75, 0.75, 1.80], placements=[AssetInstance() for _ in range(1)])
storage_cabinet_B = Assets(description="A tall orange brown dresser with two vertical doors.", size=[0.50, 1.00, 1.90], placements=[AssetInstance() for _ in range(1)])
conference_chair_D = Assets(description="It is a chair with short cloth covered arms.", size=[0.64, 0.62, 0.88], placements=[AssetInstance() for _ in range(1)])
side_meeting_chair_C = Assets(description="A black chair with wooden legs.", size=[0.58, 0.55, 0.82], placements=[AssetInstance() for _ in range(1)])

storage_cabinet_A[0].instance_id = 'storage_cabinet_A_0'
floor_lamp_A[0].instance_id = 'floor_lamp_A_0'
side_meeting_table[0].instance_id = 'side_meeting_table_0'
wall_shelf_A[0].instance_id = 'wall_shelf_A_0'
wall_artwork_A[0].instance_id = 'wall_artwork_A_0'
floor_lamp_B[0].instance_id = 'floor_lamp_B_0'
side_meeting_chair_A[0].instance_id = 'side_meeting_chair_A_0'
conference_table[0].instance_id = 'conference_table_0'
conference_chair_A[0].instance_id = 'conference_chair_A_0'
wall_artwork_B[0].instance_id = 'wall_artwork_B_0'
side_meeting_chair_B[0].instance_id = 'side_meeting_chair_B_0'
floor_coat_stand_A[0].instance_id = 'floor_coat_stand_A_0'
conference_chair_B[0].instance_id = 'conference_chair_B_0'
floor_planter_A[0].instance_id = 'floor_planter_A_0'
wall_artwork_C[0].instance_id = 'wall_artwork_C_0'
tray_with_cups[0].instance_id = 'tray_with_cups_0'
floor_planter_B[0].instance_id = 'floor_planter_B_0'
wall_whiteboard[0].instance_id = 'wall_whiteboard_0'
wall_shelf_B[0].instance_id = 'wall_shelf_B_0'
floor_coat_stand_B[0].instance_id = 'floor_coat_stand_B_0'
conference_chair_C[0].instance_id = 'conference_chair_C_0'
sideboard_credenza[0].instance_id = 'sideboard_credenza_0'
floor_planter_C[0].instance_id = 'floor_planter_C_0'
storage_cabinet_B[0].instance_id = 'storage_cabinet_B_0'
conference_chair_D[0].instance_id = 'conference_chair_D_0'
side_meeting_chair_C[0].instance_id = 'side_meeting_chair_C_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

storage_cabinet_A[0].position = [4.485217788170806, 1.7898953697786317, 0.95]
storage_cabinet_A[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [4.578219786698834, 6.750045772361631, 0.8]
floor_lamp_A[0].rotation = [0, 0, 0]
side_meeting_table[0].position = [0.09378514938722882, 2.92075825806523, 0.225]
side_meeting_table[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [0.2913142410890346, 0.08366671943505244, 0.15]
wall_shelf_A[0].rotation = [0, 0, 0]
wall_artwork_A[0].position = [2.4431465223032482, 3.382817437920393, 0.35]
wall_artwork_A[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [4.710677878260768, 3.5813621967976834, 0.8]
floor_lamp_B[0].rotation = [0, 0, 0]
side_meeting_chair_A[0].position = [0.932197675502297, 1.2068127932215877, 0.41]
side_meeting_chair_A[0].rotation = [0, 0, 0]
conference_table[0].position = [0.11042685670337338, 5.243217725525872, 0.375]
conference_table[0].rotation = [0, 0, 0]
conference_chair_A[0].position = [0.36813685962305054, 6.54361638059929, 0.44]
conference_chair_A[0].rotation = [0, 0, 0]
wall_artwork_B[0].position = [3.517656513650262, 1.371602257458921, 0.35]
wall_artwork_B[0].rotation = [0, 0, 0]
side_meeting_chair_B[0].position = [1.6966117068013686, 1.1734932628708763, 0.41]
side_meeting_chair_B[0].rotation = [0, 0, 0]
floor_coat_stand_A[0].position = [4.05978927302509, 6.132741090451154, 0.875]
floor_coat_stand_A[0].rotation = [0, 0, 0]
conference_chair_B[0].position = [2.0244621969921015, 1.5814951714407963, 0.44]
conference_chair_B[0].rotation = [0, 0, 0]
floor_planter_A[0].position = [3.110161636449526, 0.8680714498087513, 0.9]
floor_planter_A[0].rotation = [0, 0, 0]
wall_artwork_C[0].position = [4.976506282862263, 2.668650808221841, 0.35]
wall_artwork_C[0].rotation = [0, 0, 0]
tray_with_cups[0].position = [3.2293981537760907, 0.27905825617238966, 0.025]
tray_with_cups[0].rotation = [0, 0, 0]
floor_planter_B[0].position = [2.7770715703893445, 5.690591801445843, 0.9]
floor_planter_B[0].rotation = [0, 0, 0]
wall_whiteboard[0].position = [0.6504292594930822, 0.5731461456705763, 0.55]
wall_whiteboard[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [0.7614632147564859, 5.233988713095884, 0.15]
wall_shelf_B[0].rotation = [0, 0, 0]
floor_coat_stand_B[0].position = [1.0115249535891886, 2.6413962503320922, 0.875]
floor_coat_stand_B[0].rotation = [0, 0, 0]
conference_chair_C[0].position = [0.9372010488731652, 2.241631861018903, 0.44]
conference_chair_C[0].rotation = [0, 0, 0]
sideboard_credenza[0].position = [4.451479425191201, 5.789060123695653, 0.4]
sideboard_credenza[0].rotation = [0, 0, 0]
floor_planter_C[0].position = [2.5569671214604166, 4.348454915258088, 0.9]
floor_planter_C[0].rotation = [0, 0, 0]
storage_cabinet_B[0].position = [4.049390521489331, 2.247673981384322, 0.95]
storage_cabinet_B[0].rotation = [0, 0, 0]
conference_chair_D[0].position = [2.694121441523767, 2.5818192801066, 0.44]
conference_chair_D[0].rotation = [0, 0, 0]
side_meeting_chair_C[0].position = [0.13170678977939276, 1.2848728293571776, 0.41]
side_meeting_chair_C[0].rotation = [0, 0, 0]
storage_cabinet_A[0].position = [4.485217788170806, 1.7898953697786317, 0.95]
storage_cabinet_A[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [4.578219786698834, 6.750045772361631, 0.8]
floor_lamp_A[0].rotation = [0, 0, 0]
side_meeting_table[0].position = [0.09378514938722882, 2.92075825806523, 0.225]
side_meeting_table[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [0.2913142410890346, 0.08366671943505244, 0.15]
wall_shelf_A[0].rotation = [0, 0, 0]
wall_artwork_A[0].position = [2.4431465223032482, 3.382817437920393, 0.35]
wall_artwork_A[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [4.710677878260768, 3.5813621967976834, 0.8]
floor_lamp_B[0].rotation = [0, 0, 0]
side_meeting_chair_A[0].position = [0.932197675502297, 1.2068127932215877, 0.41]
side_meeting_chair_A[0].rotation = [0, 0, 0]
conference_table[0].position = [0.11042685670337338, 5.243217725525872, 0.375]
conference_table[0].rotation = [0, 0, 0]
conference_chair_A[0].position = [0.36813685962305054, 6.54361638059929, 0.44]
conference_chair_A[0].rotation = [0, 0, 0]
wall_artwork_B[0].position = [3.517656513650262, 1.371602257458921, 0.35]
wall_artwork_B[0].rotation = [0, 0, 0]
side_meeting_chair_B[0].position = [1.6966117068013686, 1.1734932628708763, 0.41]
side_meeting_chair_B[0].rotation = [0, 0, 0]
floor_coat_stand_A[0].position = [4.05978927302509, 6.132741090451154, 0.875]
floor_coat_stand_A[0].rotation = [0, 0, 0]
conference_chair_B[0].position = [2.0244621969921015, 1.5814951714407963, 0.44]
conference_chair_B[0].rotation = [0, 0, 0]
floor_planter_A[0].position = [3.110161636449526, 0.8680714498087513, 0.9]
floor_planter_A[0].rotation = [0, 0, 0]
wall_artwork_C[0].position = [4.976506282862263, 2.668650808221841, 0.35]
wall_artwork_C[0].rotation = [0, 0, 0]
tray_with_cups[0].position = [3.2293981537760907, 0.27905825617238966, 0.025]
tray_with_cups[0].rotation = [0, 0, 0]
floor_planter_B[0].position = [2.7770715703893445, 5.690591801445843, 0.9]
floor_planter_B[0].rotation = [0, 0, 0]
wall_whiteboard[0].position = [0.6504292594930822, 0.5731461456705763, 0.55]
wall_whiteboard[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [0.7614632147564859, 5.233988713095884, 0.15]
wall_shelf_B[0].rotation = [0, 0, 0]
floor_coat_stand_B[0].position = [1.0115249535891886, 2.6413962503320922, 0.875]
floor_coat_stand_B[0].rotation = [0, 0, 0]
conference_chair_C[0].position = [0.9372010488731652, 2.241631861018903, 0.44]
conference_chair_C[0].rotation = [0, 0, 0]
sideboard_credenza[0].position = [4.451479425191201, 5.789060123695653, 0.4]
sideboard_credenza[0].rotation = [0, 0, 0]
floor_planter_C[0].position = [2.5569671214604166, 4.348454915258088, 0.9]
floor_planter_C[0].rotation = [0, 0, 0]
storage_cabinet_B[0].position = [4.049390521489331, 2.247673981384322, 0.95]
storage_cabinet_B[0].rotation = [0, 0, 0]
conference_chair_D[0].position = [2.694121441523767, 2.5818192801066, 0.44]
conference_chair_D[0].rotation = [0, 0, 0]
side_meeting_chair_C[0].position = [0.13170678977939276, 1.2848728293571776, 0.41]
side_meeting_chair_C[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed references preserve the intended zones while allowing semantic constraints
# to maintain the layout if the solver makes small feasibility adjustments.
conference_table_anchor = AssetInstance(position=[2.65, 3.05, 0.375])
side_table_anchor = AssetInstance(position=[2.50, 5.55, 0.225])
side_chair_midpoint = AssetInstance(position=[2.50, 6.50, 0.41])

heading_pos_x = AssetInstance(rotation=[0, 0, radians(0)])
heading_pos_y = AssetInstance(rotation=[0, 0, radians(90)])
heading_neg_x = AssetInstance(rotation=[0, 0, radians(180)])
heading_neg_y = AssetInstance(rotation=[0, 0, radians(-90)])

# The main conference table runs north-south in the center of the room.
conference_table[0].position = [2.65, 3.05, 0.375]
conference_table[0].rotation = [0, 0, radians(0)]
solver.distance_constraint(
    conference_table[0], conference_table_anchor, 0, 0, weight=10
)
solver.align_with(conference_table[0], heading_pos_x)

# Four conference chairs flank the long sides of the table. The right-hand
# chair nearest the door is kept north of the door opening and its approach.
conference_chair_A[0].position = [1.55, 2.20, 0.44]
conference_chair_A[0].rotation = [0, 0, radians(0)]
solver.distance_constraint(
    conference_chair_A[0],
    AssetInstance(position=[1.55, 2.20, 0.44]),
    0,
    0,
    weight=10,
)
solver.point_towards(conference_chair_A[0], conference_table[0])
solver.distance_constraint(
    conference_chair_A[0], conference_table[0], 1.05, 1.75
)

conference_chair_B[0].position = [1.55, 3.85, 0.44]
conference_chair_B[0].rotation = [0, 0, radians(0)]
solver.distance_constraint(
    conference_chair_B[0],
    AssetInstance(position=[1.55, 3.85, 0.44]),
    0,
    0,
    weight=10,
)
# o0012 explicitly faces storage cabinet o0023; this orientation constraint is
# listed first so it takes priority over any table-facing interpretation.
solver.point_towards(conference_chair_B[0], storage_cabinet_B[0])
solver.distance_constraint(
    conference_chair_B[0], conference_table[0], 1.05, 1.75
)

conference_chair_C[0].position = [3.72, 2.45, 0.44]
conference_chair_C[0].rotation = [0, 0, radians(180)]
solver.distance_constraint(
    conference_chair_C[0],
    AssetInstance(position=[3.72, 2.45, 0.44]),
    0,
    0,
    weight=10,
)
solver.point_towards(conference_chair_C[0], conference_table[0])
solver.distance_constraint(
    conference_chair_C[0], conference_table[0], 1.05, 1.75
)

conference_chair_D[0].position = [3.72, 3.85, 0.44]
conference_chair_D[0].rotation = [0, 0, radians(180)]
solver.distance_constraint(
    conference_chair_D[0],
    AssetInstance(position=[3.72, 3.85, 0.44]),
    0,
    0,
    weight=10,
)
solver.point_towards(conference_chair_D[0], conference_table[0])
solver.distance_constraint(
    conference_chair_D[0], conference_table[0], 1.05, 1.75
)

# A compact secondary meeting area occupies the north end. The three chairs
# form an ordered row, with o0006 exactly between o0025 and o0010.
side_meeting_table[0].position = [2.50, 5.55, 0.225]
side_meeting_table[0].rotation = [0, 0, radians(0)]
solver.distance_constraint(
    side_meeting_table[0], side_table_anchor, 0, 0, weight=10
)
solver.align_with(side_meeting_table[0], conference_table[0])

side_meeting_chair_C[0].position = [1.60, 6.50, 0.41]
side_meeting_chair_C[0].rotation = [0, 0, radians(-47)]
solver.distance_constraint(
    side_meeting_chair_C[0],
    AssetInstance(position=[1.60, 6.50, 0.41]),
    0,
    0,
    weight=10,
)
solver.point_towards(side_meeting_chair_C[0], side_meeting_table[0])
solver.distance_constraint(
    side_meeting_chair_C[0], side_meeting_table[0], 1.20, 1.45
)

side_meeting_chair_B[0].position = [3.40, 6.50, 0.41]
side_meeting_chair_B[0].rotation = [0, 0, radians(-133)]
solver.distance_constraint(
    side_meeting_chair_B[0],
    AssetInstance(position=[3.40, 6.50, 0.41]),
    0,
    0,
    weight=10,
)
solver.point_towards(side_meeting_chair_B[0], side_meeting_table[0])
solver.distance_constraint(
    side_meeting_chair_B[0], side_meeting_table[0], 1.20, 1.45
)

side_meeting_chair_A[0].position = [2.50, 6.50, 0.41]
side_meeting_chair_A[0].rotation = [0, 0, radians(-90)]
# This fixed midpoint is the primary position constraint for the required
# o0025 -- o0006 -- o0010 ordering.
solver.distance_constraint(
    side_meeting_chair_A[0], side_chair_midpoint, 0, 0, weight=10
)
solver.point_towards(side_meeting_chair_A[0], side_meeting_table[0])
solver.distance_constraint(
    side_meeting_chair_A[0], side_meeting_chair_C[0], 0.90, 0.90
)
solver.distance_constraint(
    side_meeting_chair_A[0], side_meeting_chair_B[0], 0.90, 0.90
)

# Cabinets use the east wall north of the door. Cabinet B is aligned with
# conference chair B so the required chair-to-cabinet facing relation is clear.
storage_cabinet_A[0].position = [4.75, 5.25, 0.95]
storage_cabinet_A[0].rotation = [0, 0, radians(180)]
solver.against_wall(storage_cabinet_A[0], walls[1])
solver.distance_constraint(
    storage_cabinet_A[0],
    AssetInstance(position=[4.75, 5.25, 0.95]),
    0,
    0,
    weight=10,
)
solver.align_with(storage_cabinet_A[0], heading_neg_x)

storage_cabinet_B[0].position = [4.75, 3.85, 0.95]
storage_cabinet_B[0].rotation = [0, 0, radians(180)]
solver.against_wall(storage_cabinet_B[0], walls[1])
solver.distance_constraint(
    storage_cabinet_B[0],
    AssetInstance(position=[4.75, 3.85, 0.95]),
    0,
    0,
    weight=10,
)
solver.align_with(storage_cabinet_B[0], heading_neg_x)

# The credenza is placed along the south wall, away from the east-wall door.
sideboard_credenza[0].position = [1.10, 0.24, 0.40]
sideboard_credenza[0].rotation = [0, 0, radians(90)]
solver.against_wall(sideboard_credenza[0], walls[0])
solver.distance_constraint(
    sideboard_credenza[0],
    AssetInstance(position=[1.10, 0.24, 0.40]),
    0,
    0,
    weight=10,
)
solver.align_with(sideboard_credenza[0], heading_pos_y)

# The tray is centered on the conference table and raised to its top surface.
tray_with_cups[0].position = [2.65, 3.05, 0.775]
tray_with_cups[0].rotation = [0, 0, radians(0)]
solver.on_top_of(tray_with_cups[0], conference_table[0])
solver.distance_constraint(
    tray_with_cups[0],
    AssetInstance(position=[2.65, 3.05, 0.775]),
    0,
    0,
    weight=10,
)
solver.align_with(tray_with_cups[0], conference_table[0])

# Planters fit into the narrow solid-wall intervals between the west windows.
# The third planter fills an otherwise unused south-central corner.
floor_planter_A[0].position = [0.45, 2.20, 0.90]
floor_planter_A[0].rotation = [0, 0, radians(0)]
solver.distance_constraint(
    floor_planter_A[0],
    AssetInstance(position=[0.45, 2.20, 0.90]),
    0,
    0,
    weight=10,
)
solver.point_towards(floor_planter_A[0], conference_table[0])

floor_planter_B[0].position = [0.45, 4.50, 0.90]
floor_planter_B[0].rotation = [0, 0, radians(0)]
solver.distance_constraint(
    floor_planter_B[0],
    AssetInstance(position=[0.45, 4.50, 0.90]),
    0,
    0,
    weight=10,
)
solver.point_towards(floor_planter_B[0], side_meeting_table[0])

floor_planter_C[0].position = [2.65, 0.55, 0.90]
floor_planter_C[0].rotation = [0, 0, radians(90)]
solver.distance_constraint(
    floor_planter_C[0],
    AssetInstance(position=[2.65, 0.55, 0.90]),
    0,
    0,
    weight=10,
)
solver.point_towards(floor_planter_C[0], conference_table[0])

# Lamps illuminate the two meeting zones without occupying chair circulation.
floor_lamp_A[0].position = [1.55, 5.25, 0.80]
floor_lamp_A[0].rotation = [0, 0, radians(0)]
solver.distance_constraint(
    floor_lamp_A[0],
    AssetInstance(position=[1.55, 5.25, 0.80]),
    0,
    0,
    weight=10,
)
solver.point_towards(floor_lamp_A[0], side_meeting_table[0])

floor_lamp_B[0].position = [4.55, 6.55, 0.80]
floor_lamp_B[0].rotation = [0, 0, radians(180)]
solver.distance_constraint(
    floor_lamp_B[0],
    AssetInstance(position=[4.55, 6.55, 0.80]),
    0,
    0,
    weight=10,
)
solver.point_towards(floor_lamp_B[0], side_meeting_table[0])

# Coat stands are placed away from both the door approach and chair pull-out
# zones, while remaining accessible from the room's circulation path.
floor_coat_stand_A[0].position = [0.75, 5.25, 0.875]
floor_coat_stand_A[0].rotation = [0, 0, radians(0)]
solver.distance_constraint(
    floor_coat_stand_A[0],
    AssetInstance(position=[0.75, 5.25, 0.875]),
    0,
    0,
    weight=10,
)
solver.point_towards(floor_coat_stand_A[0], side_meeting_table[0])

floor_coat_stand_B[0].position = [3.65, 0.45, 0.875]
floor_coat_stand_B[0].rotation = [0, 0, radians(90)]
solver.distance_constraint(
    floor_coat_stand_B[0],
    AssetInstance(position=[3.65, 0.45, 0.875]),
    0,
    0,
    weight=10,
)
solver.point_towards(floor_coat_stand_B[0], conference_table[0])

# Shelves are mounted high on the north wall above the low chair zone.
wall_shelf_A[0].position = [1.35, 6.875, 1.25]
wall_shelf_A[0].rotation = [0, 0, radians(-90)]
solver.against_wall(wall_shelf_A[0], walls[2])
solver.distance_constraint(
    wall_shelf_A[0],
    AssetInstance(position=[1.35, 6.875, 1.25]),
    0,
    0,
    weight=10,
)
solver.align_with(wall_shelf_A[0], heading_neg_y)

wall_shelf_B[0].position = [2.65, 6.875, 1.25]
wall_shelf_B[0].rotation = [0, 0, radians(-90)]
solver.against_wall(wall_shelf_B[0], walls[2])
solver.distance_constraint(
    wall_shelf_B[0],
    AssetInstance(position=[2.65, 6.875, 1.25]),
    0,
    0,
    weight=10,
)
solver.align_with(wall_shelf_B[0], heading_neg_y)

# The whiteboard uses the remaining north-wall span and faces into the room.
wall_whiteboard[0].position = [4.05, 6.975, 1.45]
wall_whiteboard[0].rotation = [0, 0, radians(-90)]
solver.against_wall(wall_whiteboard[0], walls[2])
solver.distance_constraint(
    wall_whiteboard[0],
    AssetInstance(position=[4.05, 6.975, 1.45]),
    0,
    0,
    weight=10,
)
solver.align_with(wall_whiteboard[0], heading_neg_y)

# Artwork is mounted on the south wall above furniture height, leaving all
# three west-wall windows unobstructed.
wall_artwork_A[0].position = [0.60, 0.02, 1.35]
wall_artwork_A[0].rotation = [0, 0, radians(90)]
solver.against_wall(wall_artwork_A[0], walls[0])
solver.distance_constraint(
    wall_artwork_A[0],
    AssetInstance(position=[0.60, 0.02, 1.35]),
    0,
    0,
    weight=10,
)
solver.align_with(wall_artwork_A[0], heading_pos_y)

wall_artwork_B[0].position = [1.70, 0.02, 1.35]
wall_artwork_B[0].rotation = [0, 0, radians(90)]
solver.against_wall(wall_artwork_B[0], walls[0])
solver.distance_constraint(
    wall_artwork_B[0],
    AssetInstance(position=[1.70, 0.02, 1.35]),
    0,
    0,
    weight=10,
)
solver.align_with(wall_artwork_B[0], heading_pos_y)

wall_artwork_C[0].position = [4.35, 0.02, 1.35]
wall_artwork_C[0].rotation = [0, 0, radians(90)]
solver.against_wall(wall_artwork_C[0], walls[0])
solver.distance_constraint(
    wall_artwork_C[0],
    AssetInstance(position=[4.35, 0.02, 1.35]),
    0,
    0,
    weight=10,
)
solver.align_with(wall_artwork_C[0], heading_pos_y)

solver.constraints = []
side_meeting_chair_C[0].position = [1.600000023841858, 6.5, 0.4099999964237213]
side_meeting_chair_C[0].rotation = [0, 0, -0.8045968107021584]
side_meeting_chair_C[0].optimize = 2
side_meeting_table[0].position = [2.5, 5.550000190734863, 0.22499999403953552]
side_meeting_table[0].rotation = [0, 0, 0.04816738377910103]
side_meeting_table[0].optimize = 2
floor_planter_A[0].position = [0.44999998807907104, 2.200000047683716, 0.8999999761581421]
floor_planter_A[0].rotation = [0, 0, 0.00942477746072377]
floor_planter_A[0].optimize = 2
sideboard_credenza[0].position = [1.100000023841858, 0.24129071831703186, 0.4000000059604645]
sideboard_credenza[0].rotation = [0, 0, 1.5733372250472777]
sideboard_credenza[0].optimize = 2
wall_whiteboard[0].position = [4.050000190734863, 6.973692417144775, 0.550000011920929]
wall_whiteboard[0].rotation = [0, 0, -1.5682554282425925]
wall_whiteboard[0].optimize = 2
floor_lamp_A[0].position = [1.5499999523162842, 5.25, 0.800000011920929]
floor_lamp_A[0].rotation = [0, 0, 0.00942477746072377]
floor_lamp_A[0].optimize = 2
wall_shelf_B[0].position = [2.6500000953674316, 6.873476028442383, 0.15000000596046448]
wall_shelf_B[0].rotation = [0, 0, -1.5682554162991507]
wall_shelf_B[0].optimize = 2
conference_chair_C[0].position = [3.7200000286102295, 2.450000047683716, 0.4399999976158142]
conference_chair_C[0].rotation = [0, 0, -3.1290262823329655]
conference_chair_C[0].optimize = 2
floor_coat_stand_B[0].position = [3.6500000953674316, 0.44999998807907104, 0.875]
floor_coat_stand_B[0].rotation = [0, 0, 1.5904154469005738]
floor_coat_stand_B[0].optimize = 2
storage_cabinet_A[0].position = [4.748730182647705, 5.25, 0.949999988079071]
storage_cabinet_A[0].rotation = [0, 0, -3.139051739727678]
storage_cabinet_A[0].optimize = 2
conference_chair_B[0].position = [1.5499999523162842, 3.8499999046325684, 0.4399999976158142]
conference_chair_B[0].rotation = [0, 0, 0.01256637125682779]
conference_chair_B[0].optimize = 2
conference_table[0].position = [2.6500000953674316, 3.049999952316284, 0.375]
conference_table[0].rotation = [0, 0, 0.05026547968485982]
conference_table[0].optimize = 2
conference_chair_D[0].position = [3.7200000286102295, 3.8499999046325684, 0.4399999976158142]
conference_chair_D[0].rotation = [0, 0, -3.1290262823329655]
conference_chair_D[0].optimize = 2
side_meeting_chair_A[0].position = [2.5, 6.5, 0.4099999964237213]
side_meeting_chair_A[0].rotation = [0, 0, -1.5550883628776802]
side_meeting_chair_A[0].optimize = 2
tray_with_cups[0].position = [2.6500000953674316, 3.049999952316284, 0.7749999761581421]
tray_with_cups[0].rotation = [0, 0, 0.02279109852594279]
tray_with_cups[0].optimize = 2
wall_shelf_A[0].position = [1.350000023841858, 6.873476028442383, 0.15000000596046448]
wall_shelf_A[0].rotation = [0, 0, -1.5682554162991507]
wall_shelf_A[0].optimize = 2
wall_artwork_B[0].position = [1.7000000476837158, 0.011367769911885262, 0.3499999940395355]
wall_artwork_B[0].rotation = [0, 0, 1.5733372406570116]
wall_artwork_B[0].optimize = 2
wall_artwork_A[0].position = [0.6000000238418579, 0.011367769911885262, 0.3499999940395355]
wall_artwork_A[0].rotation = [0, 0, 1.5733372406570116]
wall_artwork_A[0].optimize = 2
floor_coat_stand_A[0].position = [0.75, 5.25, 0.875]
floor_coat_stand_A[0].rotation = [0, 0, 0.00942477746072377]
floor_coat_stand_A[0].optimize = 2
floor_planter_C[0].position = [2.6500000953674316, 0.550000011920929, 0.8999999761581421]
floor_planter_C[0].rotation = [0, 0, 1.5802211042556205]
floor_planter_C[0].optimize = 2
conference_chair_A[0].position = [1.5499999523162842, 2.200000047683716, 0.4399999976158142]
conference_chair_A[0].rotation = [0, 0, 0.01256637125682779]
conference_chair_A[0].optimize = 2
wall_artwork_C[0].position = [4.349999904632568, 0.011367769911885262, 0.3499999940395355]
wall_artwork_C[0].rotation = [0, 0, 1.5733372406570116]
wall_artwork_C[0].optimize = 2
floor_lamp_B[0].position = [4.550000190734863, 6.550000190734863, 0.800000011920929]
floor_lamp_B[0].rotation = [0, 0, -3.1219735179129886]
floor_lamp_B[0].optimize = 2
floor_planter_B[0].position = [0.44999998807907104, 4.5, 0.8999999761581421]
floor_planter_B[0].rotation = [0, 0, 0.019619138738570838]
floor_planter_B[0].optimize = 2
side_meeting_chair_B[0].position = [3.4000000953674316, 6.5, 0.4099999964237213]
side_meeting_chair_B[0].rotation = [0, 0, -2.305579931144402]
side_meeting_chair_B[0].optimize = 2
storage_cabinet_B[0].position = [4.747178077697754, 3.8499999046325684, 0.949999988079071]
storage_cabinet_B[0].rotation = [0, 0, -3.135941133751684]
storage_cabinet_B[0].optimize = 2

