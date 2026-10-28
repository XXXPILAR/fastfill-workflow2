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
    Wall(corner1=[0.00, 5.27, 0.00], corner2=[0.00, 0.04, 0.00]),
    Wall(corner1=[0.00, 0.04, 0.00], corner2=[0.04, 0.00, 0.00]),
    Wall(corner1=[0.04, 0.00, 0.00], corner2=[4.96, 0.00, 0.00]),
    Wall(corner1=[4.96, 0.00, 0.00], corner2=[5.00, 0.04, 0.00]),
    Wall(corner1=[5.00, 0.04, 0.00], corner2=[5.00, 5.27, 0.00]),
    Wall(corner1=[5.00, 5.27, 0.00], corner2=[4.96, 5.31, 0.00]),
    Wall(corner1=[4.96, 5.31, 0.00], corner2=[0.04, 5.31, 0.00]),
    Wall(corner1=[0.04, 5.31, 0.00], corner2=[0.00, 5.27, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
shelf_A = Assets(description="shelf", size=[0.35, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
file_A = Assets(description="file", size=[0.30, 0.08, 0.32], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="chair", size=[0.60, 0.58, 0.88], placements=[AssetInstance() for _ in range(1)])
lamp = Assets(description="lamp", size=[0.28, 0.28, 0.52], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="book", size=[0.04, 0.16, 0.24], placements=[AssetInstance() for _ in range(1)])
paper_A = Assets(description="paper", size=[0.30, 0.21, 0.00], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="book", size=[0.05, 0.18, 0.26], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.32, 0.95, 1.65], placements=[AssetInstance() for _ in range(1)])
picture_A = Assets(description="picture", size=[0.03, 0.60, 0.45], placements=[AssetInstance() for _ in range(1)])
cup = Assets(description="cup", size=[0.12, 0.09, 0.10], placements=[AssetInstance() for _ in range(1)])
book_C = Assets(description="book", size=[0.04, 0.15, 0.23], placements=[AssetInstance() for _ in range(1)])
table_A = Assets(description="table", size=[0.75, 1.50, 0.74], placements=[AssetInstance() for _ in range(1)])
paper_B = Assets(description="paper", size=[0.30, 0.21, 0.00], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.60, 0.58, 0.88], placements=[AssetInstance() for _ in range(1)])
plant = Assets(description="plant", size=[0.42, 0.42, 0.85], placements=[AssetInstance() for _ in range(1)])
picture_B = Assets(description="picture", size=[0.03, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
ottoman = Assets(description="ottoman", size=[0.55, 0.75, 0.42], placements=[AssetInstance() for _ in range(1)])
bowl = Assets(description="bowl", size=[0.24, 0.24, 0.10], placements=[AssetInstance() for _ in range(1)])
book_D = Assets(description="book", size=[0.05, 0.17, 0.25], placements=[AssetInstance() for _ in range(1)])
book_E = Assets(description="book", size=[0.06, 0.20, 0.28], placements=[AssetInstance() for _ in range(1)])
picture_C = Assets(description="picture", size=[0.03, 0.70, 0.50], placements=[AssetInstance() for _ in range(1)])
plate = Assets(description="plate", size=[0.27, 0.27, 0.03], placements=[AssetInstance() for _ in range(1)])
book_F = Assets(description="book", size=[0.05, 0.19, 0.27], placements=[AssetInstance() for _ in range(1)])
pillow_A = Assets(description="pillow", size=[0.15, 0.45, 0.45], placements=[AssetInstance() for _ in range(1)])
container = Assets(description="container", size=[0.28, 0.35, 0.22], placements=[AssetInstance() for _ in range(1)])
picture_D = Assets(description="picture", size=[0.03, 0.40, 0.55], placements=[AssetInstance() for _ in range(1)])
book_G = Assets(description="book", size=[0.04, 0.14, 0.22], placements=[AssetInstance() for _ in range(1)])
pillow_B = Assets(description="pillow", size=[0.15, 0.45, 0.45], placements=[AssetInstance() for _ in range(1)])
bin_A = Assets(description="bin", size=[0.28, 0.32, 0.42], placements=[AssetInstance() for _ in range(1)])
book_H = Assets(description="book", size=[0.06, 0.21, 0.29], placements=[AssetInstance() for _ in range(1)])
table_B = Assets(description="table", size=[0.55, 0.90, 0.45], placements=[AssetInstance() for _ in range(1)])
file_B = Assets(description="file", size=[0.30, 0.08, 0.32], placements=[AssetInstance() for _ in range(1)])
shelf_C = Assets(description="shelf", size=[0.35, 1.10, 1.80], placements=[AssetInstance() for _ in range(1)])
paper_C = Assets(description="paper", size=[0.30, 0.21, 0.00], placements=[AssetInstance() for _ in range(1)])
bin_B = Assets(description="bin", size=[0.32, 0.38, 0.48], placements=[AssetInstance() for _ in range(1)])

shelf_A[0].instance_id = 'shelf_A_0'
file_A[0].instance_id = 'file_A_0'
chair_A[0].instance_id = 'chair_A_0'
lamp[0].instance_id = 'lamp_0'
book_A[0].instance_id = 'book_A_0'
paper_A[0].instance_id = 'paper_A_0'
book_B[0].instance_id = 'book_B_0'
shelf_B[0].instance_id = 'shelf_B_0'
picture_A[0].instance_id = 'picture_A_0'
cup[0].instance_id = 'cup_0'
book_C[0].instance_id = 'book_C_0'
table_A[0].instance_id = 'table_A_0'
paper_B[0].instance_id = 'paper_B_0'
chair_B[0].instance_id = 'chair_B_0'
plant[0].instance_id = 'plant_0'
picture_B[0].instance_id = 'picture_B_0'
ottoman[0].instance_id = 'ottoman_0'
bowl[0].instance_id = 'bowl_0'
book_D[0].instance_id = 'book_D_0'
book_E[0].instance_id = 'book_E_0'
picture_C[0].instance_id = 'picture_C_0'
plate[0].instance_id = 'plate_0'
book_F[0].instance_id = 'book_F_0'
pillow_A[0].instance_id = 'pillow_A_0'
container[0].instance_id = 'container_0'
picture_D[0].instance_id = 'picture_D_0'
book_G[0].instance_id = 'book_G_0'
pillow_B[0].instance_id = 'pillow_B_0'
bin_A[0].instance_id = 'bin_A_0'
book_H[0].instance_id = 'book_H_0'
table_B[0].instance_id = 'table_B_0'
file_B[0].instance_id = 'file_B_0'
shelf_C[0].instance_id = 'shelf_C_0'
paper_C[0].instance_id = 'paper_C_0'
bin_B[0].instance_id = 'bin_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

shelf_A[0].position = [4.918726571477256, 3.811821597235427, 0.9]
shelf_A[0].rotation = [0, 0, 0]
file_A[0].position = [3.950221807394876, 4.341354420104663, 0.16]
file_A[0].rotation = [0, 0, 0]
chair_A[0].position = [2.112850118567977, 1.8897385926533121, 0.44]
chair_A[0].rotation = [0, 0, 0]
lamp[0].position = [2.1423422449987357, 0.13205342770655043, 0.26]
lamp[0].rotation = [0, 0, 0]
book_A[0].position = [3.7810160356119846, 0.36015641262363246, 0.12]
book_A[0].rotation = [0, 0, 0]
paper_A[0].position = [1.7724201796224548, 3.368607440981605, 0.001]
paper_A[0].rotation = [0, 0, 0]
book_B[0].position = [4.351770601942408, 3.001065877474475, 0.13]
book_B[0].rotation = [0, 0, 0]
shelf_B[0].position = [2.0919871104322847, 3.1488488199905023, 0.825]
shelf_B[0].rotation = [0, 0, 0]
picture_A[0].position = [3.685489577870429, 5.056379118676586, 0.225]
picture_A[0].rotation = [0, 0, 0]
cup[0].position = [0.4104466177760657, 3.264405931437897, 0.05]
cup[0].rotation = [0, 0, 0]
book_C[0].position = [0.8280331755162329, 1.3081002007557843, 0.115]
book_C[0].rotation = [0, 0, 0]
table_A[0].position = [1.9006112054770286, 1.8127132885726551, 0.37]
table_A[0].rotation = [0, 0, 0]
paper_B[0].position = [2.9328531723443967, 4.261816832339707, 0.001]
paper_B[0].rotation = [0, 0, 0]
chair_B[0].position = [4.587502700557518, 2.929097605183681, 0.44]
chair_B[0].rotation = [0, 0, 0]
plant[0].position = [3.229267999884284, 4.14183953712147, 0.425]
plant[0].rotation = [0, 0, 0]
picture_B[0].position = [4.098805864947725, 3.300838767453598, 0.35]
picture_B[0].rotation = [0, 0, 0]
ottoman[0].position = [0.766654472510393, 4.755515544432214, 0.21]
ottoman[0].rotation = [0, 0, 0]
bowl[0].position = [3.089552710296002, 2.3049482187415276, 0.05]
bowl[0].rotation = [0, 0, 0]
book_D[0].position = [0.9224004431971722, 4.065168960951227, 0.125]
book_D[0].rotation = [0, 0, 0]
book_E[0].position = [2.1289442797963964, 3.441250945014478, 0.14]
book_E[0].rotation = [0, 0, 0]
picture_C[0].position = [0.9048780819293878, 2.548168219588897, 0.25]
picture_C[0].rotation = [0, 0, 0]
plate[0].position = [4.5578681161838945, 4.142674820634881, 0.015]
plate[0].rotation = [0, 0, 0]
book_F[0].position = [4.924497965908974, 4.412989167635538, 0.135]
book_F[0].rotation = [0, 0, 0]
pillow_A[0].position = [2.537691517825764, 0.17700706965225688, 0.225]
pillow_A[0].rotation = [0, 0, 0]
container[0].position = [3.7306937359149437, 0.3575557169558671, 0.11]
container[0].rotation = [0, 0, 0]
picture_D[0].position = [4.501289158042353, 2.047006792171533, 0.275]
picture_D[0].rotation = [0, 0, 0]
book_G[0].position = [3.9452041223594208, 3.3939825976387885, 0.11]
book_G[0].rotation = [0, 0, 0]
pillow_B[0].position = [4.647701073577889, 1.5205247100902735, 0.225]
pillow_B[0].rotation = [0, 0, 0]
bin_A[0].position = [4.4580653865486095, 5.1976955707536625, 0.21]
bin_A[0].rotation = [0, 0, 0]
book_H[0].position = [2.983109672363578, 4.388047089401541, 0.145]
book_H[0].rotation = [0, 0, 0]
table_B[0].position = [2.851953267055583, 4.191628521187216, 0.225]
table_B[0].rotation = [0, 0, 0]
file_B[0].position = [3.3115393629684093, 0.49623222400162326, 0.16]
file_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [0.512537087176787, 3.3430043217712377, 0.9]
shelf_C[0].rotation = [0, 0, 0]
paper_C[0].position = [1.2297217986096025, 4.403437956877857, 0.001]
paper_C[0].rotation = [0, 0, 0]
bin_B[0].position = [4.024416561073868, 3.6702575099609036, 0.24]
bin_B[0].rotation = [0, 0, 0]
shelf_A[0].position = [4.918726571477256, 3.811821597235427, 0.9]
shelf_A[0].rotation = [0, 0, 0]
file_A[0].position = [3.950221807394876, 4.341354420104663, 0.16]
file_A[0].rotation = [0, 0, 0]
chair_A[0].position = [2.112850118567977, 1.8897385926533121, 0.44]
chair_A[0].rotation = [0, 0, 0]
lamp[0].position = [2.1423422449987357, 0.13205342770655043, 0.26]
lamp[0].rotation = [0, 0, 0]
book_A[0].position = [3.7810160356119846, 0.36015641262363246, 0.12]
book_A[0].rotation = [0, 0, 0]
paper_A[0].position = [1.7724201796224548, 3.368607440981605, 0.001]
paper_A[0].rotation = [0, 0, 0]
book_B[0].position = [4.351770601942408, 3.001065877474475, 0.13]
book_B[0].rotation = [0, 0, 0]
shelf_B[0].position = [2.0919871104322847, 3.1488488199905023, 0.825]
shelf_B[0].rotation = [0, 0, 0]
picture_A[0].position = [3.685489577870429, 5.056379118676586, 0.225]
picture_A[0].rotation = [0, 0, 0]
cup[0].position = [0.4104466177760657, 3.264405931437897, 0.05]
cup[0].rotation = [0, 0, 0]
book_C[0].position = [0.8280331755162329, 1.3081002007557843, 0.115]
book_C[0].rotation = [0, 0, 0]
table_A[0].position = [1.9006112054770286, 1.8127132885726551, 0.37]
table_A[0].rotation = [0, 0, 0]
paper_B[0].position = [2.9328531723443967, 4.261816832339707, 0.001]
paper_B[0].rotation = [0, 0, 0]
chair_B[0].position = [4.587502700557518, 2.929097605183681, 0.44]
chair_B[0].rotation = [0, 0, 0]
plant[0].position = [3.229267999884284, 4.14183953712147, 0.425]
plant[0].rotation = [0, 0, 0]
picture_B[0].position = [4.098805864947725, 3.300838767453598, 0.35]
picture_B[0].rotation = [0, 0, 0]
ottoman[0].position = [0.766654472510393, 4.755515544432214, 0.21]
ottoman[0].rotation = [0, 0, 0]
bowl[0].position = [3.089552710296002, 2.3049482187415276, 0.05]
bowl[0].rotation = [0, 0, 0]
book_D[0].position = [0.9224004431971722, 4.065168960951227, 0.125]
book_D[0].rotation = [0, 0, 0]
book_E[0].position = [2.1289442797963964, 3.441250945014478, 0.14]
book_E[0].rotation = [0, 0, 0]
picture_C[0].position = [0.9048780819293878, 2.548168219588897, 0.25]
picture_C[0].rotation = [0, 0, 0]
plate[0].position = [4.5578681161838945, 4.142674820634881, 0.015]
plate[0].rotation = [0, 0, 0]
book_F[0].position = [4.924497965908974, 4.412989167635538, 0.135]
book_F[0].rotation = [0, 0, 0]
pillow_A[0].position = [2.537691517825764, 0.17700706965225688, 0.225]
pillow_A[0].rotation = [0, 0, 0]
container[0].position = [3.7306937359149437, 0.3575557169558671, 0.11]
container[0].rotation = [0, 0, 0]
picture_D[0].position = [4.501289158042353, 2.047006792171533, 0.275]
picture_D[0].rotation = [0, 0, 0]
book_G[0].position = [3.9452041223594208, 3.3939825976387885, 0.11]
book_G[0].rotation = [0, 0, 0]
pillow_B[0].position = [4.647701073577889, 1.5205247100902735, 0.225]
pillow_B[0].rotation = [0, 0, 0]
bin_A[0].position = [4.4580653865486095, 5.1976955707536625, 0.21]
bin_A[0].rotation = [0, 0, 0]
book_H[0].position = [2.983109672363578, 4.388047089401541, 0.145]
book_H[0].rotation = [0, 0, 0]
table_B[0].position = [2.851953267055583, 4.191628521187216, 0.225]
table_B[0].rotation = [0, 0, 0]
file_B[0].position = [3.3115393629684093, 0.49623222400162326, 0.16]
file_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [0.512537087176787, 3.3430043217712377, 0.9]
shelf_C[0].rotation = [0, 0, 0]
paper_C[0].position = [1.2297217986096025, 4.403437956877857, 0.001]
paper_C[0].rotation = [0, 0, 0]
bin_B[0].position = [4.024416561073868, 3.6702575099609036, 0.24]
bin_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Cardinal references provide stable orientations without introducing scene assets.
east_heading = AssetInstance(rotation=[0, 0, radians(0)])
west_heading = AssetInstance(rotation=[0, 0, radians(180)])
room_center = AssetInstance(position=[2.50, 2.655, 0.00])

# Three shelves form a shallow storage wall along the left side. Shelf_C stops
# below the fixed fireplace footprint, which begins near y=3.88.
shelf_A[0].position = [0.175, 0.70, 0.90]
shelf_A[0].rotation = [0, 0, radians(0)]
shelf_B[0].position = [0.160, 2.05, 0.825]
shelf_B[0].rotation = [0, 0, radians(0)]
shelf_C[0].position = [0.175, 3.25, 0.90]
shelf_C[0].rotation = [0, 0, radians(0)]

# Central work area with a chair on either side.
table_A[0].position = [2.85, 2.85, 0.37]
table_A[0].rotation = [0, 0, radians(0)]
chair_A[0].position = [1.75, 2.85, 0.44]
chair_A[0].rotation = [0, 0, radians(0)]
chair_B[0].position = [3.95, 2.85, 0.44]
chair_B[0].rotation = [0, 0, radians(180)]

# Compact lounge area in the lower-right portion of the room.
table_B[0].position = [3.50, 1.15, 0.225]
table_B[0].rotation = [0, 0, radians(0)]
ottoman[0].position = [4.30, 1.25, 0.21]
ottoman[0].rotation = [0, 0, radians(0)]

# The pillows are turned across the ottoman so both fit without overlapping.
pillow_A[0].position = [4.30, 1.08, 0.645]
pillow_A[0].rotation = [0, 0, radians(90)]
pillow_B[0].position = [4.30, 1.42, 0.645]
pillow_B[0].rotation = [0, 0, radians(90)]

# Books corresponding to o0010, o0004, and o0018 are arranged in that order
# along shelf_A, making o0004 (book_A) physically between the other two.
book_C[0].position = [0.175, 0.40, 1.915]  # o0010
book_C[0].rotation = [0, 0, radians(0)]
book_A[0].position = [0.175, 0.70, 1.920]  # o0004
book_A[0].rotation = [0, 0, radians(0)]
book_D[0].position = [0.175, 1.00, 1.925]  # o0018
book_D[0].rotation = [0, 0, radians(0)]

# Additional books are distributed along shelf_B.
book_B[0].position = [0.160, 1.68, 1.780]
book_B[0].rotation = [0, 0, radians(0)]
book_E[0].position = [0.160, 1.93, 1.790]
book_E[0].rotation = [0, 0, radians(0)]
book_F[0].position = [0.160, 2.18, 1.785]
book_F[0].rotation = [0, 0, radians(0)]
book_H[0].position = [0.160, 2.40, 1.795]
book_H[0].rotation = [0, 0, radians(0)]

# Files, the remaining book, and the container occupy shelf_C.
book_G[0].position = [0.175, 2.85, 1.910]
book_G[0].rotation = [0, 0, radians(0)]
file_A[0].position = [0.175, 3.06, 1.960]
file_A[0].rotation = [0, 0, radians(0)]
file_B[0].position = [0.175, 3.22, 1.960]
file_B[0].rotation = [0, 0, radians(0)]
container[0].position = [0.175, 3.55, 1.910]
container[0].rotation = [0, 0, radians(0)]

# Work accessories are spread over table_A with non-overlapping footprints.
paper_A[0].position = [2.60, 2.45, 0.740]
paper_A[0].rotation = [0, 0, radians(0)]
paper_B[0].position = [2.95, 2.45, 0.740]
paper_B[0].rotation = [0, 0, radians(0)]
paper_C[0].position = [2.60, 2.78, 0.740]
paper_C[0].rotation = [0, 0, radians(0)]
lamp[0].position = [2.95, 3.25, 1.000]
lamp[0].rotation = [0, 0, radians(0)]
cup[0].position = [2.60, 3.25, 0.790]
cup[0].rotation = [0, 0, radians(0)]

# The bowl and plate are separated on the smaller lounge table.
bowl[0].position = [3.50, 0.93, 0.500]
bowl[0].rotation = [0, 0, radians(0)]
plate[0].position = [3.50, 1.38, 0.465]
plate[0].rotation = [0, 0, radians(0)]

# Wall art is mounted at comfortable viewing height on the unobstructed right wall.
picture_B[0].position = [4.985, 0.60, 1.55]
picture_B[0].rotation = [0, 0, radians(180)]
picture_D[0].position = [4.985, 1.30, 1.55]
picture_D[0].rotation = [0, 0, radians(180)]
picture_A[0].position = [4.985, 2.05, 1.55]
picture_A[0].rotation = [0, 0, radians(180)]
picture_C[0].position = [4.985, 3.00, 1.55]
picture_C[0].rotation = [0, 0, radians(180)]

# Floor accessories remain near the room perimeter and outside circulation paths.
plant[0].position = [4.45, 4.65, 0.425]
plant[0].rotation = [0, 0, radians(225)]
bin_A[0].position = [0.75, 0.45, 0.21]
bin_A[0].rotation = [0, 0, radians(0)]
bin_B[0].position = [0.80, 1.15, 0.24]
bin_B[0].rotation = [0, 0, radians(0)]

# Important structural and semantic constraints are specified first.
solver.against_wall(shelf_A[0], walls[0])
solver.against_wall(shelf_B[0], walls[0])
solver.against_wall(shelf_C[0], walls[0])
solver.align_with(shelf_A[0], east_heading)
solver.align_with(shelf_B[0], east_heading)
solver.align_with(shelf_C[0], east_heading)

solver.point_towards(chair_A[0], table_A[0])
solver.point_towards(chair_B[0], table_A[0])
solver.align_with(table_A[0], east_heading)
solver.align_with(table_B[0], east_heading)
solver.align_with(ottoman[0], table_B[0])
solver.distance_constraint(chair_A[0], table_A[0], 1.10, 1.10, weight=10)
solver.distance_constraint(chair_B[0], table_A[0], 1.10, 1.10, weight=10)
solver.distance_constraint(ottoman[0], table_B[0], 0.80, 0.80, weight=10)

# Keep the designated middle book collinear and equidistant from the outer books.
solver.distance_constraint(book_A[0], book_C[0], 0.30, 0.30, weight=10)
solver.distance_constraint(book_A[0], book_D[0], 0.30, 0.30, weight=10)
solver.distance_constraint(book_C[0], book_D[0], 0.60, 0.60, weight=10)

# Vertical support constraints for every item placed on furniture.
for supported_instance, support_instance in [
    (book_C[0], shelf_A[0]),
    (book_A[0], shelf_A[0]),
    (book_D[0], shelf_A[0]),
    (book_B[0], shelf_B[0]),
    (book_E[0], shelf_B[0]),
    (book_F[0], shelf_B[0]),
    (book_H[0], shelf_B[0]),
    (book_G[0], shelf_C[0]),
    (file_A[0], shelf_C[0]),
    (file_B[0], shelf_C[0]),
    (container[0], shelf_C[0]),
    (paper_A[0], table_A[0]),
    (paper_B[0], table_A[0]),
    (paper_C[0], table_A[0]),
    (lamp[0], table_A[0]),
    (cup[0], table_A[0]),
    (bowl[0], table_B[0]),
    (plate[0], table_B[0]),
    (pillow_A[0], ottoman[0]),
    (pillow_B[0], ottoman[0]),
]:
    solver.on_top_of(supported_instance, support_instance)

# Orientation semantics for all supported objects.
for aligned_instance, support_instance in [
    (book_C[0], shelf_A[0]),
    (book_A[0], shelf_A[0]),
    (book_D[0], shelf_A[0]),
    (book_B[0], shelf_B[0]),
    (book_E[0], shelf_B[0]),
    (book_F[0], shelf_B[0]),
    (book_H[0], shelf_B[0]),
    (book_G[0], shelf_C[0]),
    (file_A[0], shelf_C[0]),
    (file_B[0], shelf_C[0]),
    (container[0], shelf_C[0]),
    (paper_A[0], table_A[0]),
    (paper_B[0], table_A[0]),
    (paper_C[0], table_A[0]),
    (lamp[0], table_A[0]),
    (cup[0], table_A[0]),
    (bowl[0], table_B[0]),
    (plate[0], table_B[0]),
]:
    solver.align_with(aligned_instance, support_instance)

solver.align_with(pillow_A[0], ottoman[0], angle=90)
solver.align_with(pillow_B[0], ottoman[0], angle=90)

# The pictures stay flush with and face inward from the right wall.
for picture_instance in [
    picture_A[0],
    picture_B[0],
    picture_C[0],
    picture_D[0],
]:
    solver.against_wall(picture_instance, walls[4])
    solver.align_with(picture_instance, west_heading)

solver.point_towards(plant[0], room_center)
solver.align_with(bin_A[0], shelf_A[0])
solver.align_with(bin_B[0], shelf_A[0])

# Exact low-level position constraints preserve the checked, collision-free layout.
# Every new instance receives a position-based constraint; the semantic constraints
# above remain earlier in the constraint list and therefore have priority.
def pin_position(instance, position):
    solver.distance_constraint(
        instance,
        AssetInstance(position=position),
        0.0,
        0.0,
        weight=10,
    )

for positioned_instance in [
    shelf_A[0], shelf_B[0], shelf_C[0],
    table_A[0], chair_A[0], chair_B[0],
    table_B[0], ottoman[0], pillow_A[0], pillow_B[0],
    book_A[0], book_B[0], book_C[0], book_D[0],
    book_E[0], book_F[0], book_G[0], book_H[0],
    file_A[0], file_B[0], container[0],
    paper_A[0], paper_B[0], paper_C[0],
    lamp[0], cup[0], bowl[0], plate[0],
    picture_A[0], picture_B[0], picture_C[0], picture_D[0],
    plant[0], bin_A[0], bin_B[0],
]:
    pin_position(positioned_instance, positioned_instance.position)

solver.constraints = []
book_B[0].position = [0.1599999964237213, 1.6799999475479126, 1.7799999713897705]
book_B[0].rotation = [0, 0, 4.0639391893826455e-08]
book_B[0].optimize = 2
picture_D[0].position = [4.9850006103515625, 1.2999999523162842, 0.2750000059604645]
picture_D[0].rotation = [0, 0, -3.141592609855185]
picture_D[0].optimize = 2
bowl[0].position = [3.5, 0.9300000071525574, 0.5]
bowl[0].rotation = [0, 0, 0.02827433826904236]
bowl[0].optimize = 2
file_A[0].position = [0.17499999701976776, 3.059999942779541, 1.959999918937683]
file_A[0].rotation = [0, 0, 3.9771098898523376e-08]
file_A[0].optimize = 2
shelf_B[0].position = [0.1600000262260437, 2.049999952316284, 0.824999988079071]
shelf_B[0].rotation = [0, 0, 4.084811843540328e-08]
shelf_B[0].optimize = 2
file_B[0].position = [0.17499999701976776, 3.2200000286102295, 1.959999918937683]
file_B[0].rotation = [0, 0, 3.9771098898523376e-08]
file_B[0].optimize = 2
book_D[0].position = [0.17499999701976776, 1.0, 1.9249999523162842]
book_D[0].rotation = [0, 0, 3.7639121964704425e-08]
book_D[0].optimize = 2
picture_C[0].position = [4.985000133514404, 3.0, 0.25]
picture_C[0].rotation = [0, 0, -3.1415926098577445]
picture_C[0].optimize = 2
shelf_C[0].position = [0.17499999701976776, 3.25, 0.8999999761581421]
shelf_C[0].rotation = [0, 0, 4.017107850163374e-08]
shelf_C[0].optimize = 2
container[0].position = [0.17499999701976776, 3.549999952316284, 1.909999966621399]
container[0].rotation = [0, 0, 3.9771098898523376e-08]
container[0].optimize = 2
table_B[0].position = [3.5, 1.149999976158142, 0.22499999403953552]
table_B[0].rotation = [0, 0, 0.02827433441159227]
table_B[0].optimize = 2
picture_A[0].position = [4.984999656677246, 2.049999952316284, 0.22499999403953552]
picture_A[0].rotation = [0, 0, -3.141592609840699]
picture_A[0].optimize = 2
paper_B[0].position = [2.950000047683716, 2.450000047683716, 0.7400000095367432]
paper_B[0].rotation = [0, 0, 0.05340707398317001]
paper_B[0].optimize = 2
cup[0].position = [2.5999999046325684, 3.25, 0.7900000214576721]
cup[0].rotation = [0, 0, 0.05340707398317001]
cup[0].optimize = 2
ottoman[0].position = [4.300000190734863, 1.25, 0.20999999344348907]
ottoman[0].rotation = [0, 0, 0.028274331086645062]
ottoman[0].optimize = 2
paper_A[0].position = [2.5999999046325684, 2.450000047683716, 0.7400000095367432]
paper_A[0].rotation = [0, 0, 0.05340707398317001]
paper_A[0].optimize = 2
plate[0].position = [3.5, 1.3799999952316284, 0.4649999737739563]
plate[0].rotation = [0, 0, 0.02827433826904236]
plate[0].optimize = 2
book_A[0].position = [0.17499999701976776, 0.7017110586166382, 1.9199999570846558]
book_A[0].rotation = [0, 0, 3.7639121964704425e-08]
book_A[0].optimize = 2
book_F[0].position = [0.1599999964237213, 2.180000066757202, 1.784999966621399]
book_F[0].rotation = [0, 0, 4.0639391893826455e-08]
book_F[0].optimize = 2
pillow_B[0].position = [4.300000190734863, 1.4199999570846558, 0.6449999809265137]
pillow_B[0].rotation = [0, 0, 1.5990707058374813]
pillow_B[0].optimize = 2
chair_B[0].position = [3.950000047683716, 2.8499999046325684, 0.4399999976158142]
chair_B[0].rotation = [0, 0, -3.1290262823329655]
chair_B[0].optimize = 2
plant[0].position = [4.449999809265137, 4.650000095367432, 0.42500001192092896]
plant[0].rotation = [0, 0, -2.3467697250267454]
plant[0].optimize = 2
lamp[0].position = [2.950000047683716, 3.25, 1.0]
lamp[0].rotation = [0, 0, 0.05340707398317001]
lamp[0].optimize = 2
book_G[0].position = [0.17499999701976776, 2.8499999046325684, 1.909999966621399]
book_G[0].rotation = [0, 0, 3.9771098898523376e-08]
book_G[0].optimize = 2
shelf_A[0].position = [0.17499996721744537, 0.699999988079071, 0.8999999761581421]
shelf_A[0].rotation = [0, 0, 3.752899377537949e-08]
shelf_A[0].optimize = 2
chair_A[0].position = [1.7481696605682373, 2.8499999046325684, 0.4399999976158142]
chair_A[0].rotation = [0, 0, 0.01256637125682779]
chair_A[0].optimize = 2
table_A[0].position = [2.8499999046325684, 2.8499999046325684, 0.3700000047683716]
table_A[0].rotation = [0, 0, 0.053407073383009665]
table_A[0].optimize = 2
book_H[0].position = [0.1599999964237213, 2.4000000953674316, 1.7949999570846558]
book_H[0].rotation = [0, 0, 4.0639391893826455e-08]
book_H[0].optimize = 2
pillow_A[0].position = [4.300000190734863, 1.0800000429153442, 0.6449999809265137]
pillow_A[0].rotation = [0, 0, 1.5990707058374813]
pillow_A[0].optimize = 2
bin_B[0].position = [0.800000011920929, 1.149999976158142, 0.23999999463558197]
bin_B[0].rotation = [0, 0, 3.731915225151057e-08]
bin_B[0].optimize = 2
paper_C[0].position = [2.5999999046325684, 2.7799999713897705, 0.7400000095367432]
paper_C[0].rotation = [0, 0, 0.05340707398317001]
paper_C[0].optimize = 2
bin_A[0].position = [0.75, 0.44999998807907104, 0.20999999344348907]
bin_A[0].rotation = [0, 0, 3.731915225151057e-08]
bin_A[0].optimize = 2
book_E[0].position = [0.1599999964237213, 1.9299999475479126, 1.7899999618530273]
book_E[0].rotation = [0, 0, 4.0639391893826455e-08]
book_E[0].optimize = 2
picture_B[0].position = [4.984999656677246, 0.6000000238418579, 0.3499999940395355]
picture_B[0].rotation = [0, 0, -3.1415926098415947]
picture_B[0].optimize = 2
book_C[0].position = [0.17499999701976776, 0.4000000059604645, 1.9149999618530273]
book_C[0].rotation = [0, 0, 3.7639121964704425e-08]
book_C[0].optimize = 2

