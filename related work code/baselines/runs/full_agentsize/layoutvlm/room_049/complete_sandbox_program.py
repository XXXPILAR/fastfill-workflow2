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
    Wall(corner1=[10.62, 4.72, 0.00], corner2=[9.62, 4.72, 0.00]),
    Wall(corner1=[9.62, 4.72, 0.00], corner2=[0.00, 4.72, 0.00]),
    Wall(corner1=[0.00, 4.72, 0.00], corner2=[0.00, 3.92, 0.00]),
    Wall(corner1=[0.00, 3.92, 0.00], corner2=[0.00, 0.92, 0.00]),
    Wall(corner1=[0.00, 0.92, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.80, 0.00, 0.00]),
    Wall(corner1=[3.80, 0.00, 0.00], corner2=[7.20, 0.00, 0.00]),
    Wall(corner1=[7.20, 0.00, 0.00], corner2=[11.00, 0.00, 0.00]),
    Wall(corner1=[11.00, 0.00, 0.00], corner2=[11.00, 4.72, 0.00]),
    Wall(corner1=[11.00, 4.72, 0.00], corner2=[10.62, 4.72, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
ornament_A = Assets(description="ornament", size=[0.16, 0.22, 0.35], placements=[AssetInstance() for _ in range(1)])
trappings_A = Assets(description="trappings", size=[0.18, 0.28, 0.22], placements=[AssetInstance() for _ in range(1)])
wedding_dress_A = Assets(description="wedding dress", size=[0.45, 0.85, 1.65], placements=[AssetInstance() for _ in range(1)])
trappings_B = Assets(description="trappings", size=[0.22, 0.32, 0.28], placements=[AssetInstance() for _ in range(1)])
multi_person_sofa = Assets(description="multi person sofa", size=[0.95, 2.40, 0.85], placements=[AssetInstance() for _ in range(1)])
stool_A = Assets(description="stool", size=[0.42, 0.42, 0.46], placements=[AssetInstance() for _ in range(1)])
wedding_dress_B = Assets(description="wedding dress", size=[0.50, 0.90, 1.70], placements=[AssetInstance() for _ in range(1)])
trappings_C = Assets(description="trappings", size=[0.18, 0.25, 0.20], placements=[AssetInstance() for _ in range(1)])
high_chair_A = Assets(description="high chair", size=[0.52, 0.48, 1.05], placements=[AssetInstance() for _ in range(1)])
coat_hanger_A = Assets(description="coat hanger", size=[0.50, 0.55, 1.75], placements=[AssetInstance() for _ in range(1)])
vase_A = Assets(description="vase", size=[0.18, 0.18, 0.32], placements=[AssetInstance() for _ in range(1)])
trappings_D = Assets(description="trappings", size=[0.30, 0.70, 1.70], placements=[AssetInstance() for _ in range(1)])
trappings_E = Assets(description="trappings", size=[0.22, 0.30, 0.25], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="book", size=[0.16, 0.22, 0.03], placements=[AssetInstance() for _ in range(1)])
trappings_F = Assets(description="trappings", size=[0.18, 0.26, 0.24], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="shelf", size=[0.35, 1.20, 1.90], placements=[AssetInstance() for _ in range(1)])
ornament_B = Assets(description="ornament", size=[0.15, 0.20, 0.30], placements=[AssetInstance() for _ in range(1)])
armchair = Assets(description="armchair", size=[0.90, 0.85, 0.90], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="book", size=[0.18, 0.24, 0.04], placements=[AssetInstance() for _ in range(1)])
stool_B = Assets(description="stool", size=[0.45, 0.45, 0.48], placements=[AssetInstance() for _ in range(1)])
teatable = Assets(description="teatable", size=[0.60, 1.10, 0.45], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.32, 1.00, 1.80], placements=[AssetInstance() for _ in range(1)])
trappings_G = Assets(description="trappings", size=[0.24, 0.35, 0.30], placements=[AssetInstance() for _ in range(1)])
coat_hanger_B = Assets(description="coat hanger", size=[0.50, 0.60, 1.78], placements=[AssetInstance() for _ in range(1)])
high_chair_B = Assets(description="high chair", size=[0.52, 0.48, 1.05], placements=[AssetInstance() for _ in range(1)])
tray = Assets(description="tray", size=[0.32, 0.48, 0.05], placements=[AssetInstance() for _ in range(1)])
vase_B = Assets(description="vase", size=[0.20, 0.20, 0.38], placements=[AssetInstance() for _ in range(1)])
flowers_A = Assets(description="flowers", size=[0.38, 0.38, 0.55], placements=[AssetInstance() for _ in range(1)])
trappings_H = Assets(description="trappings", size=[0.18, 0.24, 0.20], placements=[AssetInstance() for _ in range(1)])
flowers_B = Assets(description="flowers", size=[0.42, 0.42, 0.60], placements=[AssetInstance() for _ in range(1)])
ornament_C = Assets(description="ornament", size=[0.18, 0.25, 0.32], placements=[AssetInstance() for _ in range(1)])
ornament_D = Assets(description="ornament", size=[0.20, 0.30, 0.40], placements=[AssetInstance() for _ in range(1)])
book_C = Assets(description="book", size=[0.20, 0.26, 0.04], placements=[AssetInstance() for _ in range(1)])
reception = Assets(description="reception", size=[0.70, 2.20, 1.10], placements=[AssetInstance() for _ in range(1)])
wedding_dress_C = Assets(description="wedding dress", size=[0.48, 0.88, 1.68], placements=[AssetInstance() for _ in range(1)])
trappings_I = Assets(description="trappings", size=[0.20, 0.28, 0.25], placements=[AssetInstance() for _ in range(1)])
coat_hanger_C = Assets(description="coat hanger", size=[0.50, 0.58, 1.75], placements=[AssetInstance() for _ in range(1)])
coat_hanger_D = Assets(description="coat hanger", size=[0.50, 1.20, 1.70], placements=[AssetInstance() for _ in range(1)])
trappings_J = Assets(description="trappings", size=[0.22, 0.34, 0.28], placements=[AssetInstance() for _ in range(1)])

ornament_A[0].instance_id = 'ornament_A_0'
trappings_A[0].instance_id = 'trappings_A_0'
wedding_dress_A[0].instance_id = 'wedding_dress_A_0'
trappings_B[0].instance_id = 'trappings_B_0'
multi_person_sofa[0].instance_id = 'multi_person_sofa_0'
stool_A[0].instance_id = 'stool_A_0'
wedding_dress_B[0].instance_id = 'wedding_dress_B_0'
trappings_C[0].instance_id = 'trappings_C_0'
high_chair_A[0].instance_id = 'high_chair_A_0'
coat_hanger_A[0].instance_id = 'coat_hanger_A_0'
vase_A[0].instance_id = 'vase_A_0'
trappings_D[0].instance_id = 'trappings_D_0'
trappings_E[0].instance_id = 'trappings_E_0'
book_A[0].instance_id = 'book_A_0'
trappings_F[0].instance_id = 'trappings_F_0'
shelf_A[0].instance_id = 'shelf_A_0'
ornament_B[0].instance_id = 'ornament_B_0'
armchair[0].instance_id = 'armchair_0'
book_B[0].instance_id = 'book_B_0'
stool_B[0].instance_id = 'stool_B_0'
teatable[0].instance_id = 'teatable_0'
shelf_B[0].instance_id = 'shelf_B_0'
trappings_G[0].instance_id = 'trappings_G_0'
coat_hanger_B[0].instance_id = 'coat_hanger_B_0'
high_chair_B[0].instance_id = 'high_chair_B_0'
tray[0].instance_id = 'tray_0'
vase_B[0].instance_id = 'vase_B_0'
flowers_A[0].instance_id = 'flowers_A_0'
trappings_H[0].instance_id = 'trappings_H_0'
flowers_B[0].instance_id = 'flowers_B_0'
ornament_C[0].instance_id = 'ornament_C_0'
ornament_D[0].instance_id = 'ornament_D_0'
book_C[0].instance_id = 'book_C_0'
reception[0].instance_id = 'reception_0'
wedding_dress_C[0].instance_id = 'wedding_dress_C_0'
trappings_I[0].instance_id = 'trappings_I_0'
coat_hanger_C[0].instance_id = 'coat_hanger_C_0'
coat_hanger_D[0].instance_id = 'coat_hanger_D_0'
trappings_J[0].instance_id = 'trappings_J_0'
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

ornament_A[0].position = [8.87110096601574, 3.766226519268183, 0.175]
ornament_A[0].rotation = [0, 0, 0]
trappings_A[0].position = [2.1444258275645343, 2.3029323532903603, 0.11]
trappings_A[0].rotation = [0, 0, 0]
wedding_dress_A[0].position = [7.818066760140316, 4.639379172068527, 0.825]
wedding_dress_A[0].rotation = [0, 0, 0]
trappings_B[0].position = [10.043935882007151, 2.197506658463221, 0.14]
trappings_B[0].rotation = [0, 0, 0]
multi_person_sofa[0].position = [10.974034168307494, 2.6742287992675537, 0.425]
multi_person_sofa[0].rotation = [0, 0, 0]
stool_A[0].position = [0.6059836327483693, 4.437002657602606, 0.23]
stool_A[0].rotation = [0, 0, 0]
wedding_dress_B[0].position = [2.817545342166414, 2.882668705554364, 0.85]
wedding_dress_B[0].rotation = [0, 0, 0]
trappings_C[0].position = [3.0282167979007237, 3.8024039832835856, 0.1]
trappings_C[0].rotation = [0, 0, 0]
high_chair_A[0].position = [8.837964635788461, 4.290735081204046, 0.525]
high_chair_A[0].rotation = [0, 0, 0]
coat_hanger_A[0].position = [1.2952348104844933, 1.0427326470795237, 0.875]
coat_hanger_A[0].rotation = [0, 0, 0]
vase_A[0].position = [9.037207439394123, 0.32197175375958054, 0.16]
vase_A[0].rotation = [0, 0, 0]
trappings_D[0].position = [5.234100524412071, 4.6297873233539075, 0.85]
trappings_D[0].rotation = [0, 0, 0]
trappings_E[0].position = [7.518946976479983, 4.657204737056689, 0.125]
trappings_E[0].rotation = [0, 0, 0]
book_A[0].position = [0.7668008773692592, 0.6460997190357005, 0.015]
book_A[0].rotation = [0, 0, 0]
trappings_F[0].position = [5.511937885197973, 3.7332898620946016, 0.12]
trappings_F[0].rotation = [0, 0, 0]
shelf_A[0].position = [10.698743116704224, 1.891677606946191, 0.95]
shelf_A[0].rotation = [0, 0, 0]
ornament_B[0].position = [7.934545098197457, 0.04889288329321008, 0.15]
ornament_B[0].rotation = [0, 0, 0]
armchair[0].position = [9.445272671789995, 1.4277562743877805, 0.45]
armchair[0].rotation = [0, 0, 0]
book_B[0].position = [5.8981715348900785, 1.3060200502554662, 0.0175]
book_B[0].rotation = [0, 0, 0]
stool_B[0].position = [10.101519797194065, 0.08868256826225678, 0.24]
stool_B[0].rotation = [0, 0, 0]
teatable[0].position = [8.668792924735401, 2.944706864588784, 0.225]
teatable[0].rotation = [0, 0, 0]
shelf_B[0].position = [10.261902954012362, 1.0531156998357805, 0.9]
shelf_B[0].rotation = [0, 0, 0]
trappings_G[0].position = [5.114730430043266, 0.6148746241623505, 0.15]
trappings_G[0].rotation = [0, 0, 0]
coat_hanger_B[0].position = [7.58994675506055, 4.377975232239039, 0.89]
coat_hanger_B[0].rotation = [0, 0, 0]
high_chair_B[0].position = [0.39963914516159504, 2.5031521915787267, 0.525]
high_chair_B[0].rotation = [0, 0, 0]
tray[0].position = [6.484866832595641, 4.070504794771276, 0.025]
tray[0].rotation = [0, 0, 0]
vase_B[0].position = [4.845466493050983, 4.496983195335737, 0.19]
vase_B[0].rotation = [0, 0, 0]
flowers_A[0].position = [4.228358803840329, 2.794216999769596, 0.275]
flowers_A[0].rotation = [0, 0, 0]
trappings_H[0].position = [3.0240656221160114, 2.069642354478967, 0.1]
trappings_H[0].rotation = [0, 0, 0]
flowers_B[0].position = [8.70569871483005, 0.6507847772510991, 0.3]
flowers_B[0].rotation = [0, 0, 0]
ornament_C[0].position = [7.803870266298285, 2.281765106640539, 0.16]
ornament_C[0].rotation = [0, 0, 0]
ornament_D[0].position = [5.538602745149501, 0.07723245628279443, 0.2]
ornament_D[0].rotation = [0, 0, 0]
book_C[0].position = [7.981558881962101, 4.263813919330423, 0.02]
book_C[0].rotation = [0, 0, 0]
reception[0].position = [5.187574550758489, 1.5431024792578412, 0.55]
reception[0].rotation = [0, 0, 0]
wedding_dress_C[0].position = [2.6875554353722957, 4.112723219567872, 0.84]
wedding_dress_C[0].rotation = [0, 0, 0]
trappings_I[0].position = [1.6406908048707316, 0.2041060435083193, 0.125]
trappings_I[0].rotation = [0, 0, 0]
coat_hanger_C[0].position = [4.727737817479346, 3.3409425005644384, 0.875]
coat_hanger_C[0].rotation = [0, 0, 0]
coat_hanger_D[0].position = [9.906416832625673, 1.9799829385909216, 0.85]
coat_hanger_D[0].rotation = [0, 0, 0]
trappings_J[0].position = [2.830178488365054, 0.2143252558250338, 0.14]
trappings_J[0].rotation = [0, 0, 0]
ornament_A[0].position = [8.87110096601574, 3.766226519268183, 0.175]
ornament_A[0].rotation = [0, 0, 0]
trappings_A[0].position = [2.1444258275645343, 2.3029323532903603, 0.11]
trappings_A[0].rotation = [0, 0, 0]
wedding_dress_A[0].position = [7.818066760140316, 4.639379172068527, 0.825]
wedding_dress_A[0].rotation = [0, 0, 0]
trappings_B[0].position = [10.043935882007151, 2.197506658463221, 0.14]
trappings_B[0].rotation = [0, 0, 0]
multi_person_sofa[0].position = [10.974034168307494, 2.6742287992675537, 0.425]
multi_person_sofa[0].rotation = [0, 0, 0]
stool_A[0].position = [0.6059836327483693, 4.437002657602606, 0.23]
stool_A[0].rotation = [0, 0, 0]
wedding_dress_B[0].position = [2.817545342166414, 2.882668705554364, 0.85]
wedding_dress_B[0].rotation = [0, 0, 0]
trappings_C[0].position = [3.0282167979007237, 3.8024039832835856, 0.1]
trappings_C[0].rotation = [0, 0, 0]
high_chair_A[0].position = [8.837964635788461, 4.290735081204046, 0.525]
high_chair_A[0].rotation = [0, 0, 0]
coat_hanger_A[0].position = [1.2952348104844933, 1.0427326470795237, 0.875]
coat_hanger_A[0].rotation = [0, 0, 0]
vase_A[0].position = [9.037207439394123, 0.32197175375958054, 0.16]
vase_A[0].rotation = [0, 0, 0]
trappings_D[0].position = [5.234100524412071, 4.6297873233539075, 0.85]
trappings_D[0].rotation = [0, 0, 0]
trappings_E[0].position = [7.518946976479983, 4.657204737056689, 0.125]
trappings_E[0].rotation = [0, 0, 0]
book_A[0].position = [0.7668008773692592, 0.6460997190357005, 0.015]
book_A[0].rotation = [0, 0, 0]
trappings_F[0].position = [5.511937885197973, 3.7332898620946016, 0.12]
trappings_F[0].rotation = [0, 0, 0]
shelf_A[0].position = [10.698743116704224, 1.891677606946191, 0.95]
shelf_A[0].rotation = [0, 0, 0]
ornament_B[0].position = [7.934545098197457, 0.04889288329321008, 0.15]
ornament_B[0].rotation = [0, 0, 0]
armchair[0].position = [9.445272671789995, 1.4277562743877805, 0.45]
armchair[0].rotation = [0, 0, 0]
book_B[0].position = [5.8981715348900785, 1.3060200502554662, 0.0175]
book_B[0].rotation = [0, 0, 0]
stool_B[0].position = [10.101519797194065, 0.08868256826225678, 0.24]
stool_B[0].rotation = [0, 0, 0]
teatable[0].position = [8.668792924735401, 2.944706864588784, 0.225]
teatable[0].rotation = [0, 0, 0]
shelf_B[0].position = [10.261902954012362, 1.0531156998357805, 0.9]
shelf_B[0].rotation = [0, 0, 0]
trappings_G[0].position = [5.114730430043266, 0.6148746241623505, 0.15]
trappings_G[0].rotation = [0, 0, 0]
coat_hanger_B[0].position = [7.58994675506055, 4.377975232239039, 0.89]
coat_hanger_B[0].rotation = [0, 0, 0]
high_chair_B[0].position = [0.39963914516159504, 2.5031521915787267, 0.525]
high_chair_B[0].rotation = [0, 0, 0]
tray[0].position = [6.484866832595641, 4.070504794771276, 0.025]
tray[0].rotation = [0, 0, 0]
vase_B[0].position = [4.845466493050983, 4.496983195335737, 0.19]
vase_B[0].rotation = [0, 0, 0]
flowers_A[0].position = [4.228358803840329, 2.794216999769596, 0.275]
flowers_A[0].rotation = [0, 0, 0]
trappings_H[0].position = [3.0240656221160114, 2.069642354478967, 0.1]
trappings_H[0].rotation = [0, 0, 0]
flowers_B[0].position = [8.70569871483005, 0.6507847772510991, 0.3]
flowers_B[0].rotation = [0, 0, 0]
ornament_C[0].position = [7.803870266298285, 2.281765106640539, 0.16]
ornament_C[0].rotation = [0, 0, 0]
ornament_D[0].position = [5.538602745149501, 0.07723245628279443, 0.2]
ornament_D[0].rotation = [0, 0, 0]
book_C[0].position = [7.981558881962101, 4.263813919330423, 0.02]
book_C[0].rotation = [0, 0, 0]
reception[0].position = [5.187574550758489, 1.5431024792578412, 0.55]
reception[0].rotation = [0, 0, 0]
wedding_dress_C[0].position = [2.6875554353722957, 4.112723219567872, 0.84]
wedding_dress_C[0].rotation = [0, 0, 0]
trappings_I[0].position = [1.6406908048707316, 0.2041060435083193, 0.125]
trappings_I[0].rotation = [0, 0, 0]
coat_hanger_C[0].position = [4.727737817479346, 3.3409425005644384, 0.875]
coat_hanger_C[0].rotation = [0, 0, 0]
coat_hanger_D[0].position = [9.906416832625673, 1.9799829385909216, 0.85]
coat_hanger_D[0].rotation = [0, 0, 0]
trappings_J[0].position = [2.830178488365054, 0.2143252558250338, 0.14]
trappings_J[0].rotation = [0, 0, 0]

solver.constraints = []

# Layout strategy:
# - Display/storage furniture is arranged along the top and bottom walls.
# - The lounge group occupies the right-center of the room.
# - The doorway at (10.12, 4.72) and the area immediately in front of it remain clear.
# - Nothing is placed against the windowed left wall or on the fixed partition.
# - Small decorative objects are placed on shelves, the reception desk, or the tea table.

# Convenient fixed orientation references used by align_with constraints.
facing_pos_x = AssetInstance(rotation=[0, 0, radians(0)])
facing_pos_y = AssetInstance(rotation=[0, 0, radians(90)])
facing_neg_x = AssetInstance(rotation=[0, 0, radians(180)])
facing_neg_y = AssetInstance(rotation=[0, 0, radians(-90)])

# Initial placements for every new asset.
ornament_A[0].position = [2.00, 0.20, 2.075]
ornament_A[0].rotation = [0, 0, radians(90)]

trappings_A[0].position = [2.34, 0.20, 2.010]
trappings_A[0].rotation = [0, 0, radians(90)]

wedding_dress_A[0].position = [7.70, 4.495, 0.825]
wedding_dress_A[0].rotation = [0, 0, radians(-90)]

trappings_B[0].position = [3.45, 0.18, 1.940]
trappings_B[0].rotation = [0, 0, radians(90)]

multi_person_sofa[0].position = [10.525, 1.65, 0.425]
multi_person_sofa[0].rotation = [0, 0, radians(180)]

stool_A[0].position = [8.15, 1.05, 0.230]
stool_A[0].rotation = [0, 0, radians(90)]

wedding_dress_B[0].position = [1.55, 4.470, 0.850]
wedding_dress_B[0].rotation = [0, 0, radians(-90)]

trappings_C[0].position = [3.78, 0.18, 1.900]
trappings_C[0].rotation = [0, 0, radians(90)]

high_chair_A[0].position = [5.00, 3.30, 0.525]
high_chair_A[0].rotation = [0, 0, radians(55)]

coat_hanger_A[0].position = [3.90, 4.470, 0.875]
coat_hanger_A[0].rotation = [0, 0, radians(-90)]

vase_A[0].position = [8.72, 1.65, 0.610]
vase_A[0].rotation = [0, 0, radians(90)]

# o0011: wall-mounted/floor-standing trappings at the bottom wall.
trappings_D[0].position = [6.80, 0.150, 0.850]
trappings_D[0].rotation = [0, 0, radians(90)]

trappings_E[0].position = [2.68, 0.20, 2.025]
trappings_E[0].rotation = [0, 0, radians(90)]

book_A[0].position = [3.15, 0.18, 1.915]
book_A[0].rotation = [0, 0, radians(90)]

# o0014: centered between o0038 (trappings_J) and o0011 (trappings_D).
trappings_F[0].position = [6.15, 0.090, 0.120]
trappings_F[0].rotation = [0, 0, radians(90)]

shelf_A[0].position = [2.20, 0.175, 0.950]
shelf_A[0].rotation = [0, 0, radians(90)]

ornament_B[0].position = [4.02, 0.18, 1.950]
ornament_B[0].rotation = [0, 0, radians(90)]

armchair[0].position = [7.70, 2.65, 0.450]
armchair[0].rotation = [0, 0, radians(90)]

book_B[0].position = [5.45, 4.30, 1.120]
book_B[0].rotation = [0, 0, radians(90)]

stool_B[0].position = [9.25, 2.75, 0.240]
stool_B[0].rotation = [0, 0, radians(180)]

teatable[0].position = [9.00, 1.65, 0.225]
teatable[0].rotation = [0, 0, radians(90)]

shelf_B[0].position = [3.60, 0.160, 0.900]
shelf_B[0].rotation = [0, 0, radians(90)]

trappings_G[0].position = [5.90, 4.30, 1.250]
trappings_G[0].rotation = [0, 0, radians(-90)]

coat_hanger_B[0].position = [4.55, 4.470, 0.890]
coat_hanger_B[0].rotation = [0, 0, radians(-90)]

high_chair_B[0].position = [6.45, 3.30, 0.525]
high_chair_B[0].rotation = [0, 0, radians(125)]

tray[0].position = [9.00, 1.65, 0.475]
tray[0].rotation = [0, 0, radians(90)]

vase_B[0].position = [6.30, 4.30, 1.290]
vase_B[0].rotation = [0, 0, radians(-90)]

flowers_A[0].position = [9.00, 1.65, 0.775]
flowers_A[0].rotation = [0, 0, radians(90)]

trappings_H[0].position = [1.68, 0.20, 2.000]
trappings_H[0].rotation = [0, 0, radians(90)]

flowers_B[0].position = [4.95, 4.30, 1.400]
flowers_B[0].rotation = [0, 0, radians(-90)]

ornament_C[0].position = [3.18, 0.18, 1.960]
ornament_C[0].rotation = [0, 0, radians(90)]

ornament_D[0].position = [3.72, 0.18, 2.100]
ornament_D[0].rotation = [0, 0, radians(90)]

book_C[0].position = [6.65, 4.30, 1.120]
book_C[0].rotation = [0, 0, radians(90)]

reception[0].position = [5.75, 4.370, 0.550]
reception[0].rotation = [0, 0, radians(90)]

wedding_dress_C[0].position = [2.85, 4.480, 0.840]
wedding_dress_C[0].rotation = [0, 0, radians(-90)]

trappings_I[0].position = [2.96, 0.20, 2.025]
trappings_I[0].rotation = [0, 0, radians(90)]

coat_hanger_C[0].position = [8.90, 4.470, 0.875]
coat_hanger_C[0].rotation = [0, 0, radians(-90)]

coat_hanger_D[0].position = [8.00, 0.250, 0.850]
coat_hanger_D[0].rotation = [0, 0, radians(90)]

# o0038: the other endpoint of the required trappings sequence.
trappings_J[0].position = [5.50, 0.110, 0.140]
trappings_J[0].rotation = [0, 0, radians(90)]


# Important semantic constraints are specified before the exact layout anchors.

# Keep o0011 against the bottom wall. Its 90-degree rotation gives it a
# 0.30 m wall-normal depth, so y=0.15 places it flush with the wall.
solver.against_wall(trappings_D[0], walls[6])
solver.align_with(trappings_D[0], facing_pos_y)

# Enforce the ordering o0038 -- o0014 -- o0011 with equal spacing.
solver.distance_constraint(
    trappings_F[0], trappings_J[0], 0.65, 0.65, weight=10
)
solver.distance_constraint(
    trappings_F[0], trappings_D[0], 0.65, 0.65, weight=10
)
solver.align_with(trappings_F[0], trappings_J[0])
solver.against_wall(trappings_J[0], walls[6])
solver.align_with(trappings_J[0], trappings_D[0])

# The armchair directly faces wedding_dress_A.
solver.point_towards(armchair[0], wedding_dress_A[0])
solver.distance_constraint(
    armchair[0], wedding_dress_A[0], 1.35, 2.30, weight=10
)

# Wall-oriented fixtures and large display pieces.
solver.against_wall(wedding_dress_A[0], walls[1])
solver.align_with(wedding_dress_A[0], facing_neg_y)
solver.against_wall(wedding_dress_B[0], walls[1])
solver.align_with(wedding_dress_B[0], facing_neg_y)
solver.against_wall(wedding_dress_C[0], walls[1])
solver.align_with(wedding_dress_C[0], facing_neg_y)

solver.against_wall(reception[0], walls[1])
solver.align_with(reception[0], facing_pos_y)

solver.against_wall(coat_hanger_A[0], walls[1])
solver.align_with(coat_hanger_A[0], facing_neg_y)
solver.against_wall(coat_hanger_B[0], walls[1])
solver.align_with(coat_hanger_B[0], facing_neg_y)
solver.against_wall(coat_hanger_C[0], walls[1])
solver.align_with(coat_hanger_C[0], facing_neg_y)

solver.against_wall(shelf_A[0], walls[5])
solver.align_with(shelf_A[0], facing_pos_y)
solver.against_wall(shelf_B[0], walls[5])
solver.align_with(shelf_B[0], facing_pos_y)
solver.against_wall(coat_hanger_D[0], walls[7])
solver.align_with(coat_hanger_D[0], facing_pos_y)

solver.against_wall(multi_person_sofa[0], walls[8])
solver.align_with(multi_person_sofa[0], facing_neg_x)

# High chairs face the reception desk and remain within conversational range.
solver.point_towards(high_chair_A[0], reception[0])
solver.distance_constraint(
    high_chair_A[0], reception[0], 0.85, 1.50, weight=5
)
solver.point_towards(high_chair_B[0], reception[0])
solver.distance_constraint(
    high_chair_B[0], reception[0], 0.85, 1.50, weight=5
)

# The lounge furniture faces or aligns with the seating group.
solver.point_towards(stool_A[0], teatable[0])
solver.point_towards(stool_B[0], teatable[0])
solver.align_with(teatable[0], facing_pos_y)


# Small objects must remain supported by their designated surfaces.
solver.on_top_of(ornament_A[0], shelf_A[0])
solver.on_top_of(trappings_A[0], shelf_A[0])
solver.on_top_of(trappings_E[0], shelf_A[0])
solver.on_top_of(trappings_H[0], shelf_A[0])
solver.on_top_of(trappings_I[0], shelf_A[0])

solver.on_top_of(trappings_B[0], shelf_B[0])
solver.on_top_of(trappings_C[0], shelf_B[0])
solver.on_top_of(book_A[0], shelf_B[0])
solver.on_top_of(ornament_B[0], shelf_B[0])
solver.on_top_of(ornament_C[0], shelf_B[0])
solver.on_top_of(ornament_D[0], shelf_B[0])

solver.on_top_of(book_B[0], reception[0])
solver.on_top_of(trappings_G[0], reception[0])
solver.on_top_of(vase_B[0], reception[0])
solver.on_top_of(flowers_B[0], reception[0])
solver.on_top_of(book_C[0], reception[0])

solver.on_top_of(vase_A[0], teatable[0])
solver.on_top_of(tray[0], teatable[0])
solver.on_top_of(flowers_A[0], tray[0])


# Exact position anchors preserve the proposed non-overlapping arrangement.
# Each call supplies the required position-based constraint for that instance.
_layout_entries = [
    (ornament_A[0], [2.00, 0.20, 2.075], facing_pos_y),
    (trappings_A[0], [2.34, 0.20, 2.010], facing_pos_y),
    (wedding_dress_A[0], [7.70, 4.495, 0.825], facing_neg_y),
    (trappings_B[0], [3.45, 0.18, 1.940], facing_pos_y),
    (multi_person_sofa[0], [10.525, 1.65, 0.425], facing_neg_x),
    (stool_A[0], [8.15, 1.05, 0.230], facing_pos_y),
    (wedding_dress_B[0], [1.55, 4.470, 0.850], facing_neg_y),
    (trappings_C[0], [3.78, 0.18, 1.900], facing_pos_y),
    (high_chair_A[0], [5.00, 3.30, 0.525], AssetInstance(rotation=[0, 0, radians(55)])),
    (coat_hanger_A[0], [3.90, 4.470, 0.875], facing_neg_y),
    (vase_A[0], [8.72, 1.65, 0.610], facing_pos_y),
    (trappings_D[0], [6.80, 0.150, 0.850], facing_pos_y),
    (trappings_E[0], [2.68, 0.20, 2.025], facing_pos_y),
    (book_A[0], [3.15, 0.18, 1.915], facing_pos_y),
    (trappings_F[0], [6.15, 0.090, 0.120], facing_pos_y),
    (shelf_A[0], [2.20, 0.175, 0.950], facing_pos_y),
    (ornament_B[0], [4.02, 0.18, 1.950], facing_pos_y),
    (armchair[0], [7.70, 2.65, 0.450], facing_pos_y),
    (book_B[0], [5.45, 4.30, 1.120], facing_pos_y),
    (stool_B[0], [9.25, 2.75, 0.240], facing_neg_x),
    (teatable[0], [9.00, 1.65, 0.225], facing_pos_y),
    (shelf_B[0], [3.60, 0.160, 0.900], facing_pos_y),
    (trappings_G[0], [5.90, 4.30, 1.250], facing_neg_y),
    (coat_hanger_B[0], [4.55, 4.470, 0.890], facing_neg_y),
    (high_chair_B[0], [6.45, 3.30, 0.525], AssetInstance(rotation=[0, 0, radians(125)])),
    (tray[0], [9.00, 1.65, 0.475], facing_pos_y),
    (vase_B[0], [6.30, 4.30, 1.290], facing_neg_y),
    (flowers_A[0], [9.00, 1.65, 0.775], facing_pos_y),
    (trappings_H[0], [1.68, 0.20, 2.000], facing_pos_y),
    (flowers_B[0], [4.95, 4.30, 1.400], facing_neg_y),
    (ornament_C[0], [3.18, 0.18, 1.960], facing_pos_y),
    (ornament_D[0], [3.72, 0.18, 2.100], facing_pos_y),
    (book_C[0], [6.65, 4.30, 1.120], facing_pos_y),
    (reception[0], [5.75, 4.370, 0.550], facing_pos_y),
    (wedding_dress_C[0], [2.85, 4.480, 0.840], facing_neg_y),
    (trappings_I[0], [2.96, 0.20, 2.025], facing_pos_y),
    (coat_hanger_C[0], [8.90, 4.470, 0.875], facing_neg_y),
    (coat_hanger_D[0], [8.00, 0.250, 0.850], facing_pos_y),
    (trappings_J[0], [5.50, 0.110, 0.140], facing_pos_y),
]

for _instance, _target_position, _orientation_reference in _layout_entries:
    solver.distance_constraint(
        _instance,
        AssetInstance(position=_target_position),
        0.0,
        0.0,
        weight=10,
    )
    solver.align_with(_instance, _orientation_reference)

solver.constraints = []
book_B[0].position = [5.531101703643799, 4.155330657958984, 1.1200000047683716]
book_B[0].rotation = [0, 0, 1.5833626980517244]
book_B[0].optimize = 2
teatable[0].position = [9.0, 1.649999976158142, 0.22499999403953552]
teatable[0].rotation = [0, 0, 1.5959290669047523]
teatable[0].optimize = 2
ornament_C[0].position = [3.180000066757202, 0.18000000715255737, 1.959999918937683]
ornament_C[0].rotation = [0, 0, 1.5833626980517244]
ornament_C[0].optimize = 2
wedding_dress_C[0].position = [2.8499999046325684, 4.480000019073486, 0.8399999737739563]
wedding_dress_C[0].rotation = [0, 0, -1.5709618626459145]
wedding_dress_C[0].optimize = 2
trappings_G[0].position = [5.900000095367432, 4.300000190734863, 1.25]
trappings_G[0].rotation = [0, 0, -1.5582299555380688]
trappings_G[0].optimize = 2
stool_A[0].position = [8.149999618530273, 1.0499999523162842, 0.23000000417232513]
stool_A[0].rotation = [0, 0, 1.238721894223299]
stool_A[0].optimize = 2
shelf_B[0].position = [3.3445005416870117, 0.1594700664281845, 0.8999999761581421]
shelf_B[0].rotation = [0, 0, 1.5691255592124578]
shelf_B[0].optimize = 2
trappings_E[0].position = [2.680000066757202, 0.20000000298023224, 2.0250000953674316]
trappings_E[0].rotation = [0, 0, 1.5833626980517244]
trappings_E[0].optimize = 2
vase_A[0].position = [8.720000267028809, 1.649999976158142, 0.6100000143051147]
vase_A[0].rotation = [0, 0, 1.5833626980517244]
vase_A[0].optimize = 2
trappings_A[0].position = [2.3399999141693115, 0.20000000298023224, 2.009999990463257]
trappings_A[0].rotation = [0, 0, 1.5833626980517244]
trappings_A[0].optimize = 2
ornament_A[0].position = [2.0, 0.20000000298023224, 2.075000047683716]
ornament_A[0].rotation = [0, 0, 1.5833626980517244]
ornament_A[0].optimize = 2
coat_hanger_A[0].position = [3.9000000953674316, 4.46999979019165, 0.875]
coat_hanger_A[0].rotation = [0, 0, -1.5709618626459145]
coat_hanger_A[0].optimize = 2
trappings_C[0].position = [3.7799999713897705, 0.18000000715255737, 1.899999976158142]
trappings_C[0].rotation = [0, 0, 1.5833626980517244]
trappings_C[0].optimize = 2
reception[0].position = [5.75, 3.8767988681793213, 0.550000011920929]
reception[0].rotation = [0, 0, 2.0817417883918505]
reception[0].optimize = 2
tray[0].position = [9.0, 1.649999976158142, 0.4749999940395355]
tray[0].rotation = [0, 0, 1.586504290712113]
tray[0].optimize = 2
wedding_dress_B[0].position = [1.5499999523162842, 4.46999979019165, 0.8500000238418579]
wedding_dress_B[0].rotation = [0, 0, -1.5709618626459145]
wedding_dress_B[0].optimize = 2
ornament_B[0].position = [3.844536066055298, 0.18029311299324036, 1.9499999284744263]
ornament_B[0].rotation = [0, 0, 1.5833626980517244]
ornament_B[0].optimize = 2
book_A[0].position = [3.1500000953674316, 0.18000000715255737, 1.8149999380111694]
book_A[0].rotation = [0, 0, 1.5833626980517244]
book_A[0].optimize = 2
coat_hanger_B[0].position = [4.550000190734863, 4.46999979019165, 0.8899999856948853]
coat_hanger_B[0].rotation = [0, 0, -1.5709618626459145]
coat_hanger_B[0].optimize = 2
multi_person_sofa[0].position = [10.523837089538574, 1.649999976158142, 0.42500001192092896]
multi_person_sofa[0].rotation = [0, 0, 3.141446707544326]
multi_person_sofa[0].optimize = 2
flowers_B[0].position = [5.150663375854492, 3.94205641746521, 1.4000000953674316]
flowers_B[0].rotation = [0, 0, -1.5582299555380688]
flowers_B[0].optimize = 2
trappings_I[0].position = [2.800257921218872, 0.19497981667518616, 2.0250000953674316]
trappings_I[0].rotation = [0, 0, 1.5833626980517244]
trappings_I[0].optimize = 2
trappings_J[0].position = [5.20711088180542, 0.11036348342895508, 0.14000000059604645]
trappings_J[0].rotation = [0, 0, 1.5089810627545237]
trappings_J[0].optimize = 2
flowers_A[0].position = [9.0, 1.649999976158142, 0.7749999761581421]
flowers_A[0].rotation = [0, 0, 1.5833626980517244]
flowers_A[0].optimize = 2
vase_B[0].position = [6.300000190734863, 4.300000190734863, 1.2899999618530273]
vase_B[0].rotation = [0, 0, -1.5582299555380688]
vase_B[0].optimize = 2
shelf_A[0].position = [2.200000047683716, 0.176150843501091, 0.949999988079071]
shelf_A[0].rotation = [0, 0, 1.5666623761347482]
shelf_A[0].optimize = 2
coat_hanger_C[0].position = [9.183574676513672, 4.458877086639404, 0.875]
coat_hanger_C[0].rotation = [0, 0, -1.6098158612483935]
coat_hanger_C[0].optimize = 2
trappings_B[0].position = [3.450000047683716, 0.18000000715255737, 1.9399999380111694]
trappings_B[0].rotation = [0, 0, 1.5833626980517244]
trappings_B[0].optimize = 2
ornament_D[0].position = [3.7200000286102295, 0.18000000715255737, 2.0]
ornament_D[0].rotation = [0, 0, 1.5833626980517244]
ornament_D[0].optimize = 2
armchair[0].position = [7.699999809265137, 2.6500000953674316, 0.44999998807907104]
armchair[0].rotation = [0, 0, 1.586504290712113]
armchair[0].optimize = 2
high_chair_B[0].position = [6.449999809265137, 3.299999952316284, 0.5249999761581421]
high_chair_B[0].rotation = [0, 0, 2.197369528448772]
high_chair_B[0].optimize = 2
high_chair_A[0].position = [5.0, 3.299999952316284, 0.5249999761581421]
high_chair_A[0].rotation = [0, 0, 0.9756390244965302]
high_chair_A[0].optimize = 2
trappings_D[0].position = [6.800000190734863, 0.15000000596046448, 0.8500000238418579]
trappings_D[0].rotation = [0, 0, 1.5731735167569896]
trappings_D[0].optimize = 2
coat_hanger_D[0].position = [8.0, 0.25, 0.8500000238418579]
coat_hanger_D[0].rotation = [0, 0, 1.5706307909438786]
coat_hanger_D[0].optimize = 2
stool_B[0].position = [9.25, 2.75, 0.23999999463558197]
stool_B[0].rotation = [0, 0, -2.70553437721472]
stool_B[0].optimize = 2
trappings_H[0].position = [1.6799999475479126, 0.20000000298023224, 2.0]
trappings_H[0].rotation = [0, 0, 1.5833626980517244]
trappings_H[0].optimize = 2
trappings_F[0].position = [5.866719722747803, 0.10704915970563889, 0.11999999731779099]
trappings_F[0].rotation = [0, 0, 1.5076299235119799]
trappings_F[0].optimize = 2
book_C[0].position = [6.650000095367432, 4.300000190734863, 1.1200000047683716]
book_C[0].rotation = [0, 0, 1.5833626980517244]
book_C[0].optimize = 2
wedding_dress_A[0].position = [7.992862701416016, 4.42294454574585, 0.824999988079071]
wedding_dress_A[0].rotation = [0, 0, -1.7497463326215534]
wedding_dress_A[0].optimize = 2

