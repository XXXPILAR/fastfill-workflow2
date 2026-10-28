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
    Wall(corner1=[5.12, 5.62, 0.00], corner2=[2.30, 5.62, 0.00]),
    Wall(corner1=[2.30, 5.62, 0.00], corner2=[2.27, 5.59, 0.00]),
    Wall(corner1=[2.27, 5.59, 0.00], corner2=[0.00, 2.46, 0.00]),
    Wall(corner1=[0.00, 2.46, 0.00], corner2=[0.00, 0.04, 0.00]),
    Wall(corner1=[0.00, 0.04, 0.00], corner2=[0.04, 0.00, 0.00]),
    Wall(corner1=[0.04, 0.00, 0.00], corner2=[5.12, 0.00, 0.00]),
    Wall(corner1=[5.12, 0.00, 0.00], corner2=[5.16, 0.04, 0.00]),
    Wall(corner1=[5.16, 0.04, 0.00], corner2=[5.16, 5.59, 0.00]),
    Wall(corner1=[5.16, 5.59, 0.00], corner2=[5.12, 5.62, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bag = Assets(description="bag", size=[0.18, 0.42, 0.32], placements=[AssetInstance() for _ in range(1)])
flowerpot_A = Assets(description="flowerpot", size=[0.22, 0.22, 0.20], placements=[AssetInstance() for _ in range(1)])
monitor_A = Assets(description="monitor", size=[0.20, 0.61, 0.46], placements=[AssetInstance() for _ in range(1)])
cup_A = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
plant = Assets(description="plant", size=[0.42, 0.48, 0.68], placements=[AssetInstance() for _ in range(1)])
cushion = Assets(description="cushion", size=[0.15, 0.48, 0.48], placements=[AssetInstance() for _ in range(1)])
bottle = Assets(description="bottle", size=[0.08, 0.08, 0.25], placements=[AssetInstance() for _ in range(1)])
book = Assets(description="book", size=[0.16, 0.22, 0.03], placements=[AssetInstance() for _ in range(1)])
table_A = Assets(description="table", size=[0.70, 1.40, 0.75], placements=[AssetInstance() for _ in range(1)])
flowerpot_B = Assets(description="flowerpot", size=[0.18, 0.18, 0.17], placements=[AssetInstance() for _ in range(1)])
cup_B = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
table_B = Assets(description="table", size=[0.60, 1.20, 0.74], placements=[AssetInstance() for _ in range(1)])
monitor_B = Assets(description="monitor", size=[0.20, 0.61, 0.46], placements=[AssetInstance() for _ in range(1)])
tissue_box_A = Assets(description="tissue box", size=[0.13, 0.23, 0.09], placements=[AssetInstance() for _ in range(1)])
vase = Assets(description="vase", size=[0.18, 0.18, 0.32], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="chair", size=[0.58, 0.58, 0.86], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="shelf", size=[0.32, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.45, 1.00, 0.90], placements=[AssetInstance() for _ in range(1)])
flowerpot_C = Assets(description="flowerpot", size=[0.24, 0.24, 0.22], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.58, 0.58, 0.86], placements=[AssetInstance() for _ in range(1)])
cup_C = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
basket = Assets(description="basket", size=[0.32, 0.40, 0.26], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.35, 1.10, 1.85], placements=[AssetInstance() for _ in range(1)])
flowerpot_D = Assets(description="flowerpot", size=[0.20, 0.20, 0.19], placements=[AssetInstance() for _ in range(1)])
hat = Assets(description="hat", size=[0.28, 0.32, 0.14], placements=[AssetInstance() for _ in range(1)])
flowerpot_E = Assets(description="flowerpot", size=[0.28, 0.28, 0.26], placements=[AssetInstance() for _ in range(1)])
couch_A = Assets(description="couch", size=[0.88, 2.05, 0.82], placements=[AssetInstance() for _ in range(1)])
table_C = Assets(description="table", size=[0.60, 1.10, 0.45], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.45, 1.20, 0.95], placements=[AssetInstance() for _ in range(1)])
flowerpot_F = Assets(description="flowerpot", size=[0.22, 0.22, 0.21], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="chair", size=[0.58, 0.58, 0.86], placements=[AssetInstance() for _ in range(1)])
couch_B = Assets(description="couch", size=[0.88, 1.85, 0.82], placements=[AssetInstance() for _ in range(1)])
flowerpot_G = Assets(description="flowerpot", size=[0.32, 0.32, 0.30], placements=[AssetInstance() for _ in range(1)])
table_D = Assets(description="table", size=[0.55, 0.55, 0.50], placements=[AssetInstance() for _ in range(1)])
table_E = Assets(description="table", size=[0.75, 1.50, 0.75], placements=[AssetInstance() for _ in range(1)])
chair_D = Assets(description="chair", size=[0.58, 0.58, 0.86], placements=[AssetInstance() for _ in range(1)])
chair_E = Assets(description="chair", size=[0.58, 0.58, 0.86], placements=[AssetInstance() for _ in range(1)])
tissue_box_B = Assets(description="tissue box", size=[0.13, 0.23, 0.09], placements=[AssetInstance() for _ in range(1)])

bag[0].instance_id = 'bag_0'
flowerpot_A[0].instance_id = 'flowerpot_A_0'
monitor_A[0].instance_id = 'monitor_A_0'
cup_A[0].instance_id = 'cup_A_0'
plant[0].instance_id = 'plant_0'
cushion[0].instance_id = 'cushion_0'
bottle[0].instance_id = 'bottle_0'
book[0].instance_id = 'book_0'
table_A[0].instance_id = 'table_A_0'
flowerpot_B[0].instance_id = 'flowerpot_B_0'
cup_B[0].instance_id = 'cup_B_0'
table_B[0].instance_id = 'table_B_0'
monitor_B[0].instance_id = 'monitor_B_0'
tissue_box_A[0].instance_id = 'tissue_box_A_0'
vase[0].instance_id = 'vase_0'
chair_A[0].instance_id = 'chair_A_0'
shelf_A[0].instance_id = 'shelf_A_0'
cabinet_A[0].instance_id = 'cabinet_A_0'
flowerpot_C[0].instance_id = 'flowerpot_C_0'
chair_B[0].instance_id = 'chair_B_0'
cup_C[0].instance_id = 'cup_C_0'
basket[0].instance_id = 'basket_0'
shelf_B[0].instance_id = 'shelf_B_0'
flowerpot_D[0].instance_id = 'flowerpot_D_0'
hat[0].instance_id = 'hat_0'
flowerpot_E[0].instance_id = 'flowerpot_E_0'
couch_A[0].instance_id = 'couch_A_0'
table_C[0].instance_id = 'table_C_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
flowerpot_F[0].instance_id = 'flowerpot_F_0'
chair_C[0].instance_id = 'chair_C_0'
couch_B[0].instance_id = 'couch_B_0'
flowerpot_G[0].instance_id = 'flowerpot_G_0'
table_D[0].instance_id = 'table_D_0'
table_E[0].instance_id = 'table_E_0'
chair_D[0].instance_id = 'chair_D_0'
chair_E[0].instance_id = 'chair_E_0'
tissue_box_B[0].instance_id = 'tissue_box_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'
walls[8].instance_id = 'walls_8'

bag[0].position = [4.790566215979499, 2.761836760288012, 0.16]
bag[0].rotation = [0, 0, 0]
flowerpot_A[0].position = [4.697755011754576, 0.26639160051059074, 0.1]
flowerpot_A[0].rotation = [0, 0, 0]
monitor_A[0].position = [4.797988507302641, 3.7016877331679194, 0.23]
monitor_A[0].rotation = [0, 0, 0]
cup_A[0].position = [3.0702889588645323, 3.736656530425133, 0.055]
cup_A[0].rotation = [0, 0, 0]
plant[0].position = [2.6983029748419085, 1.7772918828767479, 0.34]
plant[0].rotation = [0, 0, 0]
cushion[0].position = [3.371013287949826, 0.664125597167544, 0.24]
cushion[0].rotation = [0, 0, 0]
bottle[0].position = [1.9389691230526527, 4.196042321963976, 0.125]
bottle[0].rotation = [0, 0, 0]
book[0].position = [4.681380688209443, 3.770275180011455, 0.015]
book[0].rotation = [0, 0, 0]
table_A[0].position = [5.130125233123942, 2.978028710987018, 0.375]
table_A[0].rotation = [0, 0, 0]
flowerpot_B[0].position = [2.6219711170219595, 2.2125174386337827, 0.085]
flowerpot_B[0].rotation = [0, 0, 0]
cup_B[0].position = [3.8359667934498933, 2.35874419190117, 0.055]
cup_B[0].rotation = [0, 0, 0]
table_B[0].position = [1.389329386322478, 2.1265323085682213, 0.37]
table_B[0].rotation = [0, 0, 0]
monitor_B[0].position = [1.647194835204801, 0.4800684233553737, 0.23]
monitor_B[0].rotation = [0, 0, 0]
tissue_box_A[0].position = [1.538657656539478, 3.8482803151436937, 0.045]
tissue_box_A[0].rotation = [0, 0, 0]
vase[0].position = [3.287668027183355, 5.227135276460676, 0.16]
vase[0].rotation = [0, 0, 0]
chair_A[0].position = [3.13083128678982, 0.25654651426624603, 0.43]
chair_A[0].rotation = [0, 0, 0]
shelf_A[0].position = [1.1925766462766305, 3.0986321643528214, 0.9]
shelf_A[0].rotation = [0, 0, 0]
cabinet_A[0].position = [3.6451390487792037, 3.9060190791914455, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
flowerpot_C[0].position = [2.1801722676692017, 5.032612963892081, 0.11]
flowerpot_C[0].rotation = [0, 0, 0]
chair_B[0].position = [1.0611529188090425, 1.1880502470867111, 0.43]
chair_B[0].rotation = [0, 0, 0]
cup_C[0].position = [0.08349920834105422, 0.45954027023436794, 0.055]
cup_C[0].rotation = [0, 0, 0]
basket[0].position = [1.2867158236692464, 0.22364845549588985, 0.13]
basket[0].rotation = [0, 0, 0]
shelf_B[0].position = [3.267013278603688, 3.7284902401724045, 0.925]
shelf_B[0].rotation = [0, 0, 0]
flowerpot_D[0].position = [2.530546750318927, 3.851624697469343, 0.095]
flowerpot_D[0].rotation = [0, 0, 0]
hat[0].position = [4.7042003172107965, 5.263862171124348, 0.07]
hat[0].rotation = [0, 0, 0]
flowerpot_E[0].position = [3.793503917015282, 4.874408436432385, 0.13]
flowerpot_E[0].rotation = [0, 0, 0]
couch_A[0].position = [1.321984232074858, 2.2937849412965914, 0.41]
couch_A[0].rotation = [0, 0, 0]
table_C[0].position = [3.288142438235469, 2.3074929865257756, 0.225]
table_C[0].rotation = [0, 0, 0]
cabinet_B[0].position = [1.7426405379006333, 1.6345376989344982, 0.475]
cabinet_B[0].rotation = [0, 0, 0]
flowerpot_F[0].position = [3.118858613441867, 0.9218711989558048, 0.105]
flowerpot_F[0].rotation = [0, 0, 0]
chair_C[0].position = [2.739944359747964, 3.6823976804444465, 0.43]
chair_C[0].rotation = [0, 0, 0]
couch_B[0].position = [2.6142733832424745, 2.1346478258449166, 0.41]
couch_B[0].rotation = [0, 0, 0]
flowerpot_G[0].position = [4.950463708264815, 2.5220420645237898, 0.15]
flowerpot_G[0].rotation = [0, 0, 0]
table_D[0].position = [4.599484758334373, 1.4388071558229645, 0.25]
table_D[0].rotation = [0, 0, 0]
table_E[0].position = [1.8732294081821, 2.326357940362146, 0.375]
table_E[0].rotation = [0, 0, 0]
chair_D[0].position = [4.175411024363825, 2.155988570230988, 0.43]
chair_D[0].rotation = [0, 0, 0]
chair_E[0].position = [1.5104649973523245, 3.729560009097386, 0.43]
chair_E[0].rotation = [0, 0, 0]
tissue_box_B[0].position = [4.316239574492272, 3.0676359842557264, 0.045]
tissue_box_B[0].rotation = [0, 0, 0]
bag[0].position = [4.790566215979499, 2.761836760288012, 0.16]
bag[0].rotation = [0, 0, 0]
flowerpot_A[0].position = [4.697755011754576, 0.26639160051059074, 0.1]
flowerpot_A[0].rotation = [0, 0, 0]
monitor_A[0].position = [4.797988507302641, 3.7016877331679194, 0.23]
monitor_A[0].rotation = [0, 0, 0]
cup_A[0].position = [3.0702889588645323, 3.736656530425133, 0.055]
cup_A[0].rotation = [0, 0, 0]
plant[0].position = [2.6983029748419085, 1.7772918828767479, 0.34]
plant[0].rotation = [0, 0, 0]
cushion[0].position = [3.371013287949826, 0.664125597167544, 0.24]
cushion[0].rotation = [0, 0, 0]
bottle[0].position = [1.9389691230526527, 4.196042321963976, 0.125]
bottle[0].rotation = [0, 0, 0]
book[0].position = [4.681380688209443, 3.770275180011455, 0.015]
book[0].rotation = [0, 0, 0]
table_A[0].position = [5.130125233123942, 2.978028710987018, 0.375]
table_A[0].rotation = [0, 0, 0]
flowerpot_B[0].position = [2.6219711170219595, 2.2125174386337827, 0.085]
flowerpot_B[0].rotation = [0, 0, 0]
cup_B[0].position = [3.8359667934498933, 2.35874419190117, 0.055]
cup_B[0].rotation = [0, 0, 0]
table_B[0].position = [1.389329386322478, 2.1265323085682213, 0.37]
table_B[0].rotation = [0, 0, 0]
monitor_B[0].position = [1.647194835204801, 0.4800684233553737, 0.23]
monitor_B[0].rotation = [0, 0, 0]
tissue_box_A[0].position = [1.538657656539478, 3.8482803151436937, 0.045]
tissue_box_A[0].rotation = [0, 0, 0]
vase[0].position = [3.287668027183355, 5.227135276460676, 0.16]
vase[0].rotation = [0, 0, 0]
chair_A[0].position = [3.13083128678982, 0.25654651426624603, 0.43]
chair_A[0].rotation = [0, 0, 0]
shelf_A[0].position = [1.1925766462766305, 3.0986321643528214, 0.9]
shelf_A[0].rotation = [0, 0, 0]
cabinet_A[0].position = [3.6451390487792037, 3.9060190791914455, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
flowerpot_C[0].position = [2.1801722676692017, 5.032612963892081, 0.11]
flowerpot_C[0].rotation = [0, 0, 0]
chair_B[0].position = [1.0611529188090425, 1.1880502470867111, 0.43]
chair_B[0].rotation = [0, 0, 0]
cup_C[0].position = [0.08349920834105422, 0.45954027023436794, 0.055]
cup_C[0].rotation = [0, 0, 0]
basket[0].position = [1.2867158236692464, 0.22364845549588985, 0.13]
basket[0].rotation = [0, 0, 0]
shelf_B[0].position = [3.267013278603688, 3.7284902401724045, 0.925]
shelf_B[0].rotation = [0, 0, 0]
flowerpot_D[0].position = [2.530546750318927, 3.851624697469343, 0.095]
flowerpot_D[0].rotation = [0, 0, 0]
hat[0].position = [4.7042003172107965, 5.263862171124348, 0.07]
hat[0].rotation = [0, 0, 0]
flowerpot_E[0].position = [3.793503917015282, 4.874408436432385, 0.13]
flowerpot_E[0].rotation = [0, 0, 0]
couch_A[0].position = [1.321984232074858, 2.2937849412965914, 0.41]
couch_A[0].rotation = [0, 0, 0]
table_C[0].position = [3.288142438235469, 2.3074929865257756, 0.225]
table_C[0].rotation = [0, 0, 0]
cabinet_B[0].position = [1.7426405379006333, 1.6345376989344982, 0.475]
cabinet_B[0].rotation = [0, 0, 0]
flowerpot_F[0].position = [3.118858613441867, 0.9218711989558048, 0.105]
flowerpot_F[0].rotation = [0, 0, 0]
chair_C[0].position = [2.739944359747964, 3.6823976804444465, 0.43]
chair_C[0].rotation = [0, 0, 0]
couch_B[0].position = [2.6142733832424745, 2.1346478258449166, 0.41]
couch_B[0].rotation = [0, 0, 0]
flowerpot_G[0].position = [4.950463708264815, 2.5220420645237898, 0.15]
flowerpot_G[0].rotation = [0, 0, 0]
table_D[0].position = [4.599484758334373, 1.4388071558229645, 0.25]
table_D[0].rotation = [0, 0, 0]
table_E[0].position = [1.8732294081821, 2.326357940362146, 0.375]
table_E[0].rotation = [0, 0, 0]
chair_D[0].position = [4.175411024363825, 2.155988570230988, 0.43]
chair_D[0].rotation = [0, 0, 0]
chair_E[0].position = [1.5104649973523245, 3.729560009097386, 0.43]
chair_E[0].rotation = [0, 0, 0]
tissue_box_B[0].position = [4.316239574492272, 3.0676359842557264, 0.045]
tissue_box_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Helper for setting an initial pose and preserving it with both a positional
# and an orientation constraint. The target one metre ahead fixes the facing
# direction without introducing any additional scene asset.
def place_and_pin(asset_instance, position, yaw):
    asset_instance.position = position
    asset_instance.rotation = [0, 0, yaw]

    position_anchor = AssetInstance(position=position)
    facing_anchor = AssetInstance(
        position=[
            position[0] + cos(yaw),
            position[1] + sin(yaw),
            position[2],
        ]
    )
    solver.distance_constraint(
        asset_instance, position_anchor, 0, 0, weight=10
    )
    solver.point_towards(asset_instance, facing_anchor)


# ---------------------------------------------------------------------------
# Main floor-standing furniture
# ---------------------------------------------------------------------------

# Two compact workstations occupy the bottom wall. Their chairs remain north
# of the desks, leaving the entrance route from (0, 2.14) unobstructed.
place_and_pin(table_A[0], [1.20, 0.38, 0.375], radians(90))
solver.against_wall(table_A[0], walls[5])

place_and_pin(chair_A[0], [1.20, 1.15, 0.43], radians(-90))
solver.distance_constraint(chair_A[0], table_A[0], 0.70, 0.85, weight=10)

place_and_pin(table_B[0], [2.75, 0.33, 0.37], radians(90))
solver.against_wall(table_B[0], walls[5])

place_and_pin(chair_B[0], [2.75, 1.08, 0.43], radians(-90))
solver.distance_constraint(chair_B[0], table_B[0], 0.68, 0.82, weight=10)

# The tall shelf at the lower-left wall stays below the door and does not
# intrude into the door's clear approach corridor.
place_and_pin(shelf_B[0], [0.20, 0.65, 0.925], radians(0))
solver.against_wall(shelf_B[0], walls[3])

# A low storage cabinet fills the remaining bottom-wall space.
place_and_pin(cabinet_B[0], [4.15, 0.24, 0.475], radians(90))
solver.against_wall(cabinet_B[0], walls[5])

# Storage follows the angled upper-left boundary. Both pieces face inward,
# approximately along the inward normal of that wall.
place_and_pin(cabinet_A[0], [0.85, 3.15, 0.45], radians(-36))
solver.against_wall(cabinet_A[0], walls[2])

place_and_pin(shelf_A[0], [1.55, 4.35, 0.90], radians(-36))
solver.against_wall(shelf_A[0], walls[2])

# A dining/work table runs along the lower portion of the right wall.
place_and_pin(table_E[0], [4.73, 1.75, 0.375], radians(180))
solver.against_wall(table_E[0], walls[7])

place_and_pin(chair_D[0], [3.72, 1.40, 0.43], radians(0))
solver.distance_constraint(chair_D[0], table_E[0], 0.95, 1.15, weight=10)

place_and_pin(chair_E[0], [3.72, 2.10, 0.43], radians(0))
solver.distance_constraint(chair_E[0], table_E[0], 0.95, 1.15, weight=10)

# The living area occupies the upper-right portion of the room. The couches
# meet around a shared coffee table while retaining a small corner gap.
place_and_pin(couch_A[0], [4.70, 3.65, 0.41], radians(180))
solver.against_wall(couch_A[0], walls[7])

place_and_pin(couch_B[0], [3.05, 5.16, 0.41], radians(-90))
solver.against_wall(couch_B[0], walls[0])

place_and_pin(table_C[0], [3.35, 3.85, 0.225], radians(90))

place_and_pin(chair_C[0], [2.25, 3.90, 0.43], radians(0))
solver.distance_constraint(chair_C[0], table_C[0], 1.00, 1.20, weight=10)

# Maintain useful conversational distances around the coffee table.
solver.distance_constraint(couch_A[0], table_C[0], 1.25, 1.45, weight=10)
solver.distance_constraint(couch_B[0], table_C[0], 1.20, 1.45, weight=10)

# A compact side table and floor plant occupy otherwise-unused central space
# while remaining outside the entrance path.
place_and_pin(table_D[0], [1.70, 2.75, 0.25], radians(0))

place_and_pin(plant[0], [2.35, 2.80, 0.34], radians(45))
solver.distance_constraint(plant[0], table_D[0], 0.60, 0.75, weight=5)

# The basket is accessible from the work area but sits below the doorway,
# leaving the floor directly in front of the door clear.
place_and_pin(basket[0], [0.55, 1.35, 0.13], radians(0))
solver.distance_constraint(basket[0], shelf_B[0], 0.70, 0.85, weight=5)


# ---------------------------------------------------------------------------
# Objects supported by the first workstation
# ---------------------------------------------------------------------------

place_and_pin(monitor_A[0], [1.15, 0.30, 0.98], radians(90))
solver.on_top_of(monitor_A[0], table_A[0])
solver.align_with(monitor_A[0], table_A[0])

place_and_pin(book[0], [0.58, 0.20, 0.765], radians(90))
solver.on_top_of(book[0], table_A[0])
solver.align_with(book[0], table_A[0])

place_and_pin(cup_A[0], [1.70, 0.18, 0.805], radians(90))
solver.on_top_of(cup_A[0], table_A[0])
solver.align_with(cup_A[0], table_A[0])

place_and_pin(flowerpot_A[0], [1.70, 0.53, 0.85], radians(90))
solver.on_top_of(flowerpot_A[0], table_A[0])
solver.align_with(flowerpot_A[0], table_A[0])


# ---------------------------------------------------------------------------
# Objects supported by the second workstation
# ---------------------------------------------------------------------------

place_and_pin(monitor_B[0], [2.70, 0.29, 0.97], radians(90))
solver.on_top_of(monitor_B[0], table_B[0])
solver.align_with(monitor_B[0], table_B[0])

place_and_pin(bottle[0], [2.25, 0.15, 0.865], radians(90))
solver.on_top_of(bottle[0], table_B[0])
solver.align_with(bottle[0], table_B[0])

place_and_pin(tissue_box_A[0], [2.28, 0.51, 0.785], radians(90))
solver.on_top_of(tissue_box_A[0], table_B[0])
solver.align_with(tissue_box_A[0], table_B[0])

place_and_pin(cup_B[0], [3.25, 0.17, 0.795], radians(90))
solver.on_top_of(cup_B[0], table_B[0])
solver.align_with(cup_B[0], table_B[0])

place_and_pin(flowerpot_B[0], [3.20, 0.50, 0.825], radians(90))
solver.on_top_of(flowerpot_B[0], table_B[0])
solver.align_with(flowerpot_B[0], table_B[0])


# ---------------------------------------------------------------------------
# Dining-table accessories
# ---------------------------------------------------------------------------

place_and_pin(cup_C[0], [4.70, 1.35, 0.805], radians(180))
solver.on_top_of(cup_C[0], table_E[0])
solver.align_with(cup_C[0], table_E[0])

place_and_pin(tissue_box_B[0], [4.70, 2.15, 0.795], radians(180))
solver.on_top_of(tissue_box_B[0], table_E[0])
solver.align_with(tissue_box_B[0], table_E[0])


# ---------------------------------------------------------------------------
# Living-area accessories
# ---------------------------------------------------------------------------

place_and_pin(vase[0], [3.12, 3.82, 0.61], radians(90))
solver.on_top_of(vase[0], table_C[0])
solver.align_with(vase[0], table_C[0])

place_and_pin(flowerpot_F[0], [3.62, 3.95, 0.555], radians(90))
solver.on_top_of(flowerpot_F[0], table_C[0])
solver.align_with(flowerpot_F[0], table_C[0])

place_and_pin(flowerpot_G[0], [1.70, 2.75, 0.65], radians(0))
solver.on_top_of(flowerpot_G[0], table_D[0])
solver.align_with(flowerpot_G[0], table_D[0])

place_and_pin(cushion[0], [4.66, 3.72, 1.06], radians(180))
solver.on_top_of(cushion[0], couch_A[0])
solver.align_with(cushion[0], couch_A[0])


# ---------------------------------------------------------------------------
# Storage-top accessories
# ---------------------------------------------------------------------------

# The bag and hat share the long top of the lower-left shelf with separation
# along the y-axis.
place_and_pin(bag[0], [0.20, 0.39, 2.01], radians(0))
solver.on_top_of(bag[0], shelf_B[0])
solver.align_with(bag[0], shelf_B[0])

place_and_pin(hat[0], [0.20, 0.93, 1.92], radians(0))
solver.on_top_of(hat[0], shelf_B[0])
solver.align_with(hat[0], shelf_B[0])

place_and_pin(flowerpot_D[0], [0.85, 3.15, 0.995], radians(-36))
solver.on_top_of(flowerpot_D[0], cabinet_A[0])
solver.align_with(flowerpot_D[0], cabinet_A[0])

place_and_pin(flowerpot_E[0], [1.55, 4.35, 1.93], radians(-36))
solver.on_top_of(flowerpot_E[0], shelf_A[0])
solver.align_with(flowerpot_E[0], shelf_A[0])

place_and_pin(flowerpot_C[0], [4.15, 0.24, 1.06], radians(90))
solver.on_top_of(flowerpot_C[0], cabinet_B[0])
solver.align_with(flowerpot_C[0], cabinet_B[0])

solver.constraints = []
hat[0].position = [0.20000000298023224, 0.9300000071525574, 1.9200000762939453]
hat[0].rotation = [0, 0, 0.0005295217491921133]
hat[0].optimize = 2
table_B[0].position = [2.75, 0.2993503212928772, 0.3700000047683716]
table_B[0].rotation = [0, 0, 1.569747789680566]
table_B[0].optimize = 2
basket[0].position = [0.550000011920929, 1.350000023841858, 0.12999999523162842]
basket[0].rotation = [0, 0, 0.01256637125682779]
basket[0].optimize = 2
flowerpot_G[0].position = [1.7000000476837158, 2.75, 0.6499999761581421]
flowerpot_G[0].rotation = [0, 0, 0.0186290949282465]
flowerpot_G[0].optimize = 2
flowerpot_D[0].position = [0.8500000238418579, 3.1500000953674316, 0.9950000047683716]
flowerpot_D[0].rotation = [0, 0, -0.6265483772335538]
flowerpot_D[0].optimize = 2
cabinet_B[0].position = [4.150000095367432, 0.225309818983078, 0.4749999940395355]
cabinet_B[0].rotation = [0, 0, 1.571368062145538]
cabinet_B[0].optimize = 2
cushion[0].position = [4.659999847412109, 3.7200000286102295, 1.059999942779541]
cushion[0].rotation = [0, 0, 3.139917865640348]
cushion[0].optimize = 2
flowerpot_E[0].position = [1.5499999523162842, 4.349999904632568, 1.9299999475479126]
flowerpot_E[0].rotation = [0, 0, -0.626552060471042]
flowerpot_E[0].optimize = 2
table_E[0].position = [4.78286075592041, 1.75, 0.375]
table_E[0].rotation = [0, 0, -3.140659061480367]
table_E[0].optimize = 2
chair_E[0].position = [3.7200000286102295, 2.0999999046325684, 0.4300000071525574]
chair_E[0].rotation = [0, 0, 0.01256637125682779]
chair_E[0].optimize = 2
table_C[0].position = [3.3499999046325684, 3.8499999046325684, 0.22499999403953552]
table_C[0].rotation = [0, 0, 1.6022122525607134]
table_C[0].optimize = 2
table_D[0].position = [1.7000000476837158, 2.75, 0.25]
table_D[0].rotation = [0, 0, 0.01884955539881635]
table_D[0].optimize = 2
flowerpot_F[0].position = [3.619999885559082, 3.950000047683716, 0.5550000071525574]
flowerpot_F[0].rotation = [0, 0, 1.602220915756022]
flowerpot_F[0].optimize = 2
book[0].position = [0.5799999833106995, 0.20000000298023224, 0.7649999856948853]
book[0].rotation = [0, 0, 1.574370448495801]
book[0].optimize = 2
shelf_A[0].position = [1.5619722604751587, 4.342909336090088, 0.8999999761581421]
shelf_A[0].rotation = [0, 0, -0.6273080402278379]
shelf_A[0].optimize = 2
plant[0].position = [2.3499999046325684, 2.799999952316284, 0.3400000035762787]
plant[0].rotation = [0, 0, 0.7979645348947851]
plant[0].optimize = 2
monitor_A[0].position = [1.149999976158142, 0.30000001192092896, 0.9800000190734863]
monitor_A[0].rotation = [0, 0, 1.574370448495801]
monitor_A[0].optimize = 2
chair_A[0].position = [1.2000000476837158, 1.149999976158142, 0.4300000071525574]
chair_A[0].rotation = [0, 0, -1.5582299555380688]
chair_A[0].optimize = 2
bottle[0].position = [2.25, 0.15000000596046448, 0.8650000095367432]
bottle[0].rotation = [0, 0, 1.5715894851470882]
bottle[0].optimize = 2
monitor_B[0].position = [2.700000047683716, 0.28999999165534973, 0.9700000286102295]
monitor_B[0].rotation = [0, 0, 1.5715894851470882]
monitor_B[0].optimize = 2
shelf_B[0].position = [0.17492999136447906, 0.6499999761581421, 0.925000011920929]
shelf_B[0].rotation = [0, 0, 0.00017070173469471944]
shelf_B[0].optimize = 2
cup_A[0].position = [1.7000000476837158, 0.18000000715255737, 0.8050000071525574]
cup_A[0].rotation = [0, 0, 1.574370448495801]
cup_A[0].optimize = 2
flowerpot_C[0].position = [4.150000095367432, 0.23999999463558197, 1.059999942779541]
flowerpot_C[0].rotation = [0, 0, 1.5688599565776387]
flowerpot_C[0].optimize = 2
couch_B[0].position = [3.290843963623047, 5.187617778778076, 0.4099999964237213]
couch_B[0].rotation = [0, 0, -1.5714756072374216]
couch_B[0].optimize = 2
tissue_box_B[0].position = [4.699999809265137, 2.1500000953674316, 0.7950000166893005]
tissue_box_B[0].rotation = [0, 0, -3.1398962314789496]
tissue_box_B[0].optimize = 2
chair_D[0].position = [3.7200000286102295, 1.399999976158142, 0.4300000071525574]
chair_D[0].rotation = [0, 0, 0.01256637125682779]
chair_D[0].optimize = 2
cup_C[0].position = [4.699999809265137, 1.350000023841858, 0.8050000071525574]
cup_C[0].rotation = [0, 0, -3.1398962314789496]
cup_C[0].optimize = 2
chair_C[0].position = [2.25, 3.9000000953674316, 0.4300000071525574]
chair_C[0].rotation = [0, 0, 0.01256637125682779]
chair_C[0].optimize = 2
vase[0].position = [3.119999885559082, 3.819999933242798, 0.6100000143051147]
vase[0].rotation = [0, 0, 1.602220915756022]
vase[0].optimize = 2
bag[0].position = [0.20000000298023224, 0.38999998569488525, 2.009999990463257]
bag[0].rotation = [0, 0, 0.0005295217491921133]
bag[0].optimize = 2
couch_A[0].position = [4.716516017913818, 3.6500000953674316, 0.4099999964237213]
couch_A[0].rotation = [0, 0, 3.141339003872355]
couch_A[0].optimize = 2
table_A[0].position = [1.2000000476837158, 0.34933969378471375, 0.375]
table_A[0].rotation = [0, 0, 1.5697795484741581]
table_A[0].optimize = 2
flowerpot_A[0].position = [1.7000000476837158, 0.5299999713897705, 0.8500000238418579]
flowerpot_A[0].rotation = [0, 0, 1.574370448495801]
flowerpot_A[0].optimize = 2
cup_B[0].position = [3.25, 0.17000000178813934, 0.7950000166893005]
cup_B[0].rotation = [0, 0, 1.5715894851470882]
cup_B[0].optimize = 2
cabinet_A[0].position = [0.8081766963005066, 3.1918232440948486, 0.44999998807907104]
cabinet_A[0].rotation = [0, 0, -0.6272850569720174]
cabinet_A[0].optimize = 2
chair_B[0].position = [2.75, 1.0800000429153442, 0.4300000071525574]
chair_B[0].rotation = [0, 0, -1.5582299555380688]
chair_B[0].optimize = 2
flowerpot_B[0].position = [3.200000047683716, 0.5, 0.824999988079071]
flowerpot_B[0].rotation = [0, 0, 1.5715894851470882]
flowerpot_B[0].optimize = 2
tissue_box_A[0].position = [2.2799999713897705, 0.5099999904632568, 0.7850000262260437]
tissue_box_A[0].rotation = [0, 0, 1.5715894851470882]
tissue_box_A[0].optimize = 2

