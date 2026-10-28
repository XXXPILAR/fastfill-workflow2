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
    Wall(corner1=[0.00, 9.96, 0.00], corner2=[0.00, 0.04, 0.00]),
    Wall(corner1=[0.00, 0.04, 0.00], corner2=[0.04, 0.00, 0.00]),
    Wall(corner1=[0.04, 0.00, 0.00], corner2=[4.02, 0.00, 0.00]),
    Wall(corner1=[4.02, 0.00, 0.00], corner2=[4.06, 0.04, 0.00]),
    Wall(corner1=[4.06, 0.04, 0.00], corner2=[4.06, 4.88, 0.00]),
    Wall(corner1=[4.06, 4.88, 0.00], corner2=[2.58, 9.96, 0.00]),
    Wall(corner1=[2.58, 9.96, 0.00], corner2=[2.54, 10.00, 0.00]),
    Wall(corner1=[2.54, 10.00, 0.00], corner2=[0.04, 10.00, 0.00]),
    Wall(corner1=[0.04, 10.00, 0.00], corner2=[0.00, 9.96, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
book_A = Assets(description="book", size=[0.16, 0.22, 0.03], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="chair", size=[0.53, 0.48, 0.86], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="book", size=[0.17, 0.24, 0.03], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.54, 0.49, 0.87], placements=[AssetInstance() for _ in range(1)])
book_C = Assets(description="book", size=[0.15, 0.21, 0.03], placements=[AssetInstance() for _ in range(1)])
book_D = Assets(description="book", size=[0.19, 0.26, 0.04], placements=[AssetInstance() for _ in range(1)])
book_E = Assets(description="book", size=[0.16, 0.23, 0.03], placements=[AssetInstance() for _ in range(1)])
plate = Assets(description="plate", size=[0.27, 0.27, 0.03], placements=[AssetInstance() for _ in range(1)])
book_F = Assets(description="book", size=[0.18, 0.25, 0.03], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="chair", size=[0.53, 0.48, 0.86], placements=[AssetInstance() for _ in range(1)])
bag = Assets(description="bag", size=[0.18, 0.42, 0.32], placements=[AssetInstance() for _ in range(1)])
furniture = Assets(description="furniture", size=[0.45, 1.35, 0.82], placements=[AssetInstance() for _ in range(1)])
book_G = Assets(description="book", size=[0.16, 0.22, 0.03], placements=[AssetInstance() for _ in range(1)])
book_H = Assets(description="book", size=[0.17, 0.24, 0.03], placements=[AssetInstance() for _ in range(1)])
book_I = Assets(description="book", size=[0.21, 0.28, 0.04], placements=[AssetInstance() for _ in range(1)])
book_J = Assets(description="book", size=[0.16, 0.23, 0.03], placements=[AssetInstance() for _ in range(1)])
book_K = Assets(description="book", size=[0.18, 0.25, 0.03], placements=[AssetInstance() for _ in range(1)])
chair_D = Assets(description="chair", size=[0.54, 0.49, 0.87], placements=[AssetInstance() for _ in range(1)])
bowl = Assets(description="bowl", size=[0.22, 0.22, 0.09], placements=[AssetInstance() for _ in range(1)])
book_L = Assets(description="book", size=[0.15, 0.21, 0.03], placements=[AssetInstance() for _ in range(1)])
chair_E = Assets(description="chair", size=[0.53, 0.48, 0.86], placements=[AssetInstance() for _ in range(1)])
chair_F = Assets(description="chair", size=[0.54, 0.49, 0.87], placements=[AssetInstance() for _ in range(1)])
chair_G = Assets(description="chair", size=[0.53, 0.48, 0.86], placements=[AssetInstance() for _ in range(1)])
chair_H = Assets(description="chair", size=[0.54, 0.49, 0.87], placements=[AssetInstance() for _ in range(1)])
book_M = Assets(description="book", size=[0.20, 0.27, 0.04], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.46, 1.15, 0.90], placements=[AssetInstance() for _ in range(1)])
chair_I = Assets(description="chair", size=[0.53, 0.48, 0.86], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="table", size=[1.15, 3.20, 0.76], placements=[AssetInstance() for _ in range(1)])
book_N = Assets(description="book", size=[0.17, 0.24, 0.03], placements=[AssetInstance() for _ in range(1)])
book_O = Assets(description="book", size=[0.16, 0.22, 0.03], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.48, 1.20, 0.92], placements=[AssetInstance() for _ in range(1)])
chair_J = Assets(description="chair", size=[0.54, 0.49, 0.87], placements=[AssetInstance() for _ in range(1)])
chair_K = Assets(description="chair", size=[0.53, 0.48, 0.86], placements=[AssetInstance() for _ in range(1)])
chair_L = Assets(description="chair", size=[0.54, 0.49, 0.87], placements=[AssetInstance() for _ in range(1)])

book_A[0].instance_id = 'book_A_0'
chair_A[0].instance_id = 'chair_A_0'
book_B[0].instance_id = 'book_B_0'
chair_B[0].instance_id = 'chair_B_0'
book_C[0].instance_id = 'book_C_0'
book_D[0].instance_id = 'book_D_0'
book_E[0].instance_id = 'book_E_0'
plate[0].instance_id = 'plate_0'
book_F[0].instance_id = 'book_F_0'
chair_C[0].instance_id = 'chair_C_0'
bag[0].instance_id = 'bag_0'
furniture[0].instance_id = 'furniture_0'
book_G[0].instance_id = 'book_G_0'
book_H[0].instance_id = 'book_H_0'
book_I[0].instance_id = 'book_I_0'
book_J[0].instance_id = 'book_J_0'
book_K[0].instance_id = 'book_K_0'
chair_D[0].instance_id = 'chair_D_0'
bowl[0].instance_id = 'bowl_0'
book_L[0].instance_id = 'book_L_0'
chair_E[0].instance_id = 'chair_E_0'
chair_F[0].instance_id = 'chair_F_0'
chair_G[0].instance_id = 'chair_G_0'
chair_H[0].instance_id = 'chair_H_0'
book_M[0].instance_id = 'book_M_0'
cabinet_A[0].instance_id = 'cabinet_A_0'
chair_I[0].instance_id = 'chair_I_0'
table[0].instance_id = 'table_0'
book_N[0].instance_id = 'book_N_0'
book_O[0].instance_id = 'book_O_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
chair_J[0].instance_id = 'chair_J_0'
chair_K[0].instance_id = 'chair_K_0'
chair_L[0].instance_id = 'chair_L_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'
walls[8].instance_id = 'walls_8'

book_A[0].position = [1.5981360899554393, 1.1855510049830398, 0.015]
book_A[0].rotation = [0, 0, 0]
chair_A[0].position = [1.3574631878843262, 7.947720768667987, 0.43]
chair_A[0].rotation = [0, 0, 0]
book_B[0].position = [3.693477913234959, 6.051804497603634, 0.015]
book_B[0].rotation = [0, 0, 0]
chair_B[0].position = [1.528290263607384, 2.848972282226513, 0.435]
chair_B[0].rotation = [0, 0, 0]
book_C[0].position = [0.13621294402002226, 3.3415749038234557, 0.0125]
book_C[0].rotation = [0, 0, 0]
book_D[0].position = [3.8718057263570826, 4.348927452818106, 0.0175]
book_D[0].rotation = [0, 0, 0]
book_E[0].position = [1.8629486967093791, 4.352319617875876, 0.015]
book_E[0].rotation = [0, 0, 0]
plate[0].position = [3.1250232078015943, 3.917186658813071, 0.0125]
plate[0].rotation = [0, 0, 0]
book_F[0].position = [2.6565749768799227, 8.146609823885274, 0.015]
book_F[0].rotation = [0, 0, 0]
chair_C[0].position = [0.145972962322249, 7.446108784161687, 0.43]
chair_C[0].rotation = [0, 0, 0]
bag[0].position = [2.3164465526816436, 9.619842739857555, 0.16]
bag[0].rotation = [0, 0, 0]
furniture[0].position = [1.898541515488665, 5.0487688234988735, 0.41]
furniture[0].rotation = [0, 0, 0]
book_G[0].position = [0.42380656892679053, 0.7067420987695872, 0.0125]
book_G[0].rotation = [0, 0, 0]
book_H[0].position = [3.07223389731913, 0.3922059318501314, 0.015]
book_H[0].rotation = [0, 0, 0]
book_I[0].position = [1.4023604505829184, 6.151894917873934, 0.0175]
book_I[0].rotation = [0, 0, 0]
book_J[0].position = [0.3791336109962674, 0.6072195410508419, 0.015]
book_J[0].rotation = [0, 0, 0]
book_K[0].position = [2.0841191193485304, 8.995809977025866, 0.015]
book_K[0].rotation = [0, 0, 0]
chair_D[0].position = [1.3341193659352961, 4.689248133883211, 0.435]
chair_D[0].rotation = [0, 0, 0]
bowl[0].position = [0.1828828219888615, 8.500199543524111, 0.045]
bowl[0].rotation = [0, 0, 0]
book_L[0].position = [2.180704326880428, 4.000821046637908, 0.0125]
book_L[0].rotation = [0, 0, 0]
chair_E[0].position = [2.5916544217415702, 0.08680382844628243, 0.43]
chair_E[0].rotation = [0, 0, 0]
chair_F[0].position = [0.9222076293060744, 6.255116968546801, 0.435]
chair_F[0].rotation = [0, 0, 0]
chair_G[0].position = [1.4098928360315344, 3.9741793034462902, 0.43]
chair_G[0].rotation = [0, 0, 0]
chair_H[0].position = [0.11872068922070325, 2.2969996257381586, 0.435]
chair_H[0].rotation = [0, 0, 0]
book_M[0].position = [2.729757765022809, 4.797797634406957, 0.0175]
book_M[0].rotation = [0, 0, 0]
cabinet_A[0].position = [1.8190406168215394, 8.867479093490271, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
chair_I[0].position = [0.832493661633557, 8.424421266628151, 0.43]
chair_I[0].rotation = [0, 0, 0]
table[0].position = [1.2650984753811254, 1.8964121359190733, 0.38]
table[0].rotation = [0, 0, 0]
book_N[0].position = [1.6653779140535199, 6.676584881493359, 0.015]
book_N[0].rotation = [0, 0, 0]
book_O[0].position = [3.746504368948887, 0.6030832926879648, 0.0125]
book_O[0].rotation = [0, 0, 0]
cabinet_B[0].position = [1.0959314606255233, 3.1622824219240986, 0.46]
cabinet_B[0].rotation = [0, 0, 0]
chair_J[0].position = [2.513965806165008, 4.214370904610677, 0.435]
chair_J[0].rotation = [0, 0, 0]
chair_K[0].position = [0.565491048763942, 7.522385127746869, 0.43]
chair_K[0].rotation = [0, 0, 0]
chair_L[0].position = [2.8322469515205335, 7.609114608636095, 0.435]
chair_L[0].rotation = [0, 0, 0]
book_A[0].position = [1.5981360899554393, 1.1855510049830398, 0.015]
book_A[0].rotation = [0, 0, 0]
chair_A[0].position = [1.3574631878843262, 7.947720768667987, 0.43]
chair_A[0].rotation = [0, 0, 0]
book_B[0].position = [3.693477913234959, 6.051804497603634, 0.015]
book_B[0].rotation = [0, 0, 0]
chair_B[0].position = [1.528290263607384, 2.848972282226513, 0.435]
chair_B[0].rotation = [0, 0, 0]
book_C[0].position = [0.13621294402002226, 3.3415749038234557, 0.0125]
book_C[0].rotation = [0, 0, 0]
book_D[0].position = [3.8718057263570826, 4.348927452818106, 0.0175]
book_D[0].rotation = [0, 0, 0]
book_E[0].position = [1.8629486967093791, 4.352319617875876, 0.015]
book_E[0].rotation = [0, 0, 0]
plate[0].position = [3.1250232078015943, 3.917186658813071, 0.0125]
plate[0].rotation = [0, 0, 0]
book_F[0].position = [2.6565749768799227, 8.146609823885274, 0.015]
book_F[0].rotation = [0, 0, 0]
chair_C[0].position = [0.145972962322249, 7.446108784161687, 0.43]
chair_C[0].rotation = [0, 0, 0]
bag[0].position = [2.3164465526816436, 9.619842739857555, 0.16]
bag[0].rotation = [0, 0, 0]
furniture[0].position = [1.898541515488665, 5.0487688234988735, 0.41]
furniture[0].rotation = [0, 0, 0]
book_G[0].position = [0.42380656892679053, 0.7067420987695872, 0.0125]
book_G[0].rotation = [0, 0, 0]
book_H[0].position = [3.07223389731913, 0.3922059318501314, 0.015]
book_H[0].rotation = [0, 0, 0]
book_I[0].position = [1.4023604505829184, 6.151894917873934, 0.0175]
book_I[0].rotation = [0, 0, 0]
book_J[0].position = [0.3791336109962674, 0.6072195410508419, 0.015]
book_J[0].rotation = [0, 0, 0]
book_K[0].position = [2.0841191193485304, 8.995809977025866, 0.015]
book_K[0].rotation = [0, 0, 0]
chair_D[0].position = [1.3341193659352961, 4.689248133883211, 0.435]
chair_D[0].rotation = [0, 0, 0]
bowl[0].position = [0.1828828219888615, 8.500199543524111, 0.045]
bowl[0].rotation = [0, 0, 0]
book_L[0].position = [2.180704326880428, 4.000821046637908, 0.0125]
book_L[0].rotation = [0, 0, 0]
chair_E[0].position = [2.5916544217415702, 0.08680382844628243, 0.43]
chair_E[0].rotation = [0, 0, 0]
chair_F[0].position = [0.9222076293060744, 6.255116968546801, 0.435]
chair_F[0].rotation = [0, 0, 0]
chair_G[0].position = [1.4098928360315344, 3.9741793034462902, 0.43]
chair_G[0].rotation = [0, 0, 0]
chair_H[0].position = [0.11872068922070325, 2.2969996257381586, 0.435]
chair_H[0].rotation = [0, 0, 0]
book_M[0].position = [2.729757765022809, 4.797797634406957, 0.0175]
book_M[0].rotation = [0, 0, 0]
cabinet_A[0].position = [1.8190406168215394, 8.867479093490271, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
chair_I[0].position = [0.832493661633557, 8.424421266628151, 0.43]
chair_I[0].rotation = [0, 0, 0]
table[0].position = [1.2650984753811254, 1.8964121359190733, 0.38]
table[0].rotation = [0, 0, 0]
book_N[0].position = [1.6653779140535199, 6.676584881493359, 0.015]
book_N[0].rotation = [0, 0, 0]
book_O[0].position = [3.746504368948887, 0.6030832926879648, 0.0125]
book_O[0].rotation = [0, 0, 0]
cabinet_B[0].position = [1.0959314606255233, 3.1622824219240986, 0.46]
cabinet_B[0].rotation = [0, 0, 0]
chair_J[0].position = [2.513965806165008, 4.214370904610677, 0.435]
chair_J[0].rotation = [0, 0, 0]
chair_K[0].position = [0.565491048763942, 7.522385127746869, 0.43]
chair_K[0].rotation = [0, 0, 0]
chair_L[0].position = [2.8322469515205335, 7.609114608636095, 0.435]
chair_L[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the dining table in the upper-middle portion of the room. This keeps
# the entrance at (1.92, 0.00) and the doors around (4.06, 3.85) unobstructed.
table[0].position = [2.00, 6.25, 0.38]
table[0].rotation = [0, 0, radians(0)]

# The first three chair variables correspond to the three chairs named in the
# criterion: chair_A (o0001), chair_B (o0022), and chair_C (o0017).
# Their collinear ordering makes chair_A lie between chair_B and chair_C.
chair_positions = [
    (chair_A[0], [1.05, 6.20, 0.43],   0),  # between B and C
    (chair_B[0], [1.05, 5.55, 0.435],  0),
    (chair_C[0], [1.05, 6.85, 0.43],   0),
    (chair_D[0], [1.05, 7.50, 0.435],  0),
    (chair_E[0], [2.95, 5.05, 0.43], 180),
    (chair_F[0], [2.95, 5.75, 0.435], 180),
    (chair_G[0], [2.95, 6.45, 0.43], 180),
    (chair_H[0], [2.95, 7.15, 0.435], 180),
    (chair_I[0], [1.70, 4.25, 0.43],  90),
    (chair_J[0], [2.35, 4.25, 0.435], 90),
    (chair_K[0], [1.70, 8.25, 0.43], -90),
    (chair_L[0], [2.35, 8.25, 0.435], -90),
]
for chair_instance, chair_position, chair_angle in chair_positions:
    chair_instance.position = chair_position
    chair_instance.rotation = [0, 0, radians(chair_angle)]

# Shallow storage pieces are placed against perimeter walls, away from all
# three door clearances and from the dining circulation area.
furniture[0].position = [0.225, 2.80, 0.41]
furniture[0].rotation = [0, 0, radians(0)]

cabinet_A[0].position = [0.90, 9.77, 0.45]
cabinet_A[0].rotation = [0, 0, radians(-90)]

cabinet_B[0].position = [0.24, 8.70, 0.46]
cabinet_B[0].rotation = [0, 0, radians(0)]

# Distribute the books and dining pieces over the table in a spaced grid.
# The table surface is at z=0.76 m.
tabletop_layout = [
    (book_A[0], [1.65, 4.95, 0.775],   0),
    (book_B[0], [2.00, 4.95, 0.775],  90),
    (book_C[0], [2.35, 4.95, 0.775],   0),
    (book_D[0], [1.65, 5.45, 0.780],  90),
    (book_E[0], [2.00, 5.45, 0.775],   0),
    (book_F[0], [2.35, 5.45, 0.775],  90),
    (book_G[0], [1.65, 5.95, 0.775],   0),
    (book_H[0], [2.00, 5.95, 0.775],  90),
    (book_I[0], [2.35, 5.95, 0.780],   0),
    (book_J[0], [1.65, 6.45, 0.775],  90),
    (book_K[0], [2.00, 6.45, 0.775],   0),
    (book_L[0], [2.35, 6.45, 0.775],  90),
    (book_M[0], [1.65, 6.95, 0.780],   0),
    (book_N[0], [2.00, 6.95, 0.775],  90),
    (book_O[0], [2.35, 6.95, 0.775],   0),
    (plate[0],  [1.72, 7.48, 0.775],   0),
    (bowl[0],   [2.28, 7.48, 0.805],   0),
]
for tabletop_instance, tabletop_position, tabletop_angle in tabletop_layout:
    tabletop_instance.position = tabletop_position
    tabletop_instance.rotation = [0, 0, radians(tabletop_angle)]

# The bag fits securely on the top cabinet and does not consume circulation
# space on the floor.
bag[0].position = [0.90, 9.77, 1.06]
bag[0].rotation = [0, 0, radians(-90)]


# Fixed references preserve the major furniture locations and orientations.
table_anchor = AssetInstance(
    position=[2.00, 6.25, 0.38],
    rotation=[0, 0, radians(0)]
)
furniture_anchor = AssetInstance(
    position=[0.225, 2.80, 0.41],
    rotation=[0, 0, radians(0)]
)
cabinet_A_anchor = AssetInstance(
    position=[0.90, 9.77, 0.45],
    rotation=[0, 0, radians(-90)]
)
cabinet_B_anchor = AssetInstance(
    position=[0.24, 8.70, 0.46],
    rotation=[0, 0, radians(0)]
)

# Major furniture constraints are specified first because their positions
# define the circulation paths and the remainder of the arrangement.
solver.distance_constraint(table[0], table_anchor, 0, 0, weight=10)
solver.align_with(table[0], table_anchor)

solver.distance_constraint(furniture[0], furniture_anchor, 0, 0, weight=10)
solver.against_wall(furniture[0], walls[0])
solver.align_with(furniture[0], furniture_anchor)

solver.distance_constraint(cabinet_A[0], cabinet_A_anchor, 0, 0, weight=10)
solver.against_wall(cabinet_A[0], walls[7])
solver.align_with(cabinet_A[0], cabinet_A_anchor)

solver.distance_constraint(cabinet_B[0], cabinet_B_anchor, 0, 0, weight=10)
solver.against_wall(cabinet_B[0], walls[0])
solver.align_with(cabinet_B[0], cabinet_B_anchor)

# Each chair is pinned to its non-overlapping place and points toward the
# table. The exact chair anchors also preserve the required A-B-C ordering.
for chair_instance, chair_position, chair_angle in chair_positions:
    chair_anchor = AssetInstance(
        position=chair_position,
        rotation=[0, 0, radians(chair_angle)]
    )
    solver.distance_constraint(
        chair_instance, chair_anchor, 0, 0, weight=10
    )
    solver.point_towards(chair_instance, table[0])

# Each tabletop object receives a horizontal position constraint, an
# orientation constraint, and a vertical support constraint.
for tabletop_instance, tabletop_position, tabletop_angle in tabletop_layout:
    tabletop_anchor = AssetInstance(
        position=tabletop_position,
        rotation=[0, 0, radians(tabletop_angle)]
    )
    solver.distance_constraint(
        tabletop_instance, tabletop_anchor, 0, 0, weight=10
    )
    solver.align_with(tabletop_instance, tabletop_anchor)
    solver.on_top_of(tabletop_instance, table[0])

# Keep the bag centered on its supporting cabinet and aligned with it.
bag_anchor = AssetInstance(
    position=[0.90, 9.77, 1.06],
    rotation=[0, 0, radians(-90)]
)
solver.distance_constraint(bag[0], bag_anchor, 0, 0, weight=10)
solver.align_with(bag[0], cabinet_A[0])
solver.on_top_of(bag[0], cabinet_A[0])

solver.constraints = []
book_D[0].position = [1.649999976158142, 5.449999809265137, 0.7799999713897705]
book_D[0].rotation = [0, 0, 1.5833626980517244]
book_D[0].optimize = 2
plate[0].position = [1.7200000286102295, 7.480000019073486, 0.7749999761581421]
plate[0].rotation = [0, 0, 0.01256637125682779]
plate[0].optimize = 2
book_M[0].position = [1.649999976158142, 6.949999809265137, 0.7799999713897705]
book_M[0].rotation = [0, 0, 0.01256637125682779]
book_M[0].optimize = 2
book_J[0].position = [1.649999976158142, 6.449999809265137, 0.7749999761581421]
book_J[0].rotation = [0, 0, 1.5833626980517244]
book_J[0].optimize = 2
chair_F[0].position = [2.950000047683716, 5.75, 0.4350000023841858]
chair_F[0].rotation = [0, 0, -3.1321678761290697]
chair_F[0].optimize = 2
cabinet_B[0].position = [0.24000000953674316, 8.699999809265137, 0.46000000834465027]
cabinet_B[0].rotation = [0, 0, 3.153370228006193e-08]
cabinet_B[0].optimize = 2
chair_E[0].position = [2.950000047683716, 5.050000190734863, 0.4300000071525574]
chair_E[0].rotation = [0, 0, -3.1321678761290697]
chair_E[0].optimize = 2
book_K[0].position = [2.0, 6.449999809265137, 0.7749999761581421]
book_K[0].rotation = [0, 0, 0.01256637125682779]
book_K[0].optimize = 2
chair_A[0].position = [1.0499999523162842, 6.199999809265137, 0.4300000071525574]
chair_A[0].rotation = [0, 0, 0.00942477746072377]
chair_A[0].optimize = 2
book_N[0].position = [2.0, 6.949999809265137, 0.7749999761581421]
book_N[0].rotation = [0, 0, 1.5833626980517244]
book_N[0].optimize = 2
chair_K[0].position = [1.7000000476837158, 8.25, 0.4300000071525574]
chair_K[0].rotation = [0, 0, -1.5613715493341729]
chair_K[0].optimize = 2
chair_H[0].position = [2.950000047683716, 7.150000095367432, 0.4350000023841858]
chair_H[0].rotation = [0, 0, -3.1321678761290697]
chair_H[0].optimize = 2
book_L[0].position = [2.3499999046325684, 6.449999809265137, 0.7749999761581421]
book_L[0].rotation = [0, 0, 1.5833626980517244]
book_L[0].optimize = 2
book_E[0].position = [2.0, 5.449999809265137, 0.7749999761581421]
book_E[0].rotation = [0, 0, 0.01256637125682779]
book_E[0].optimize = 2
furniture[0].position = [0.22500000894069672, 2.799999952316284, 0.4099999964237213]
furniture[0].rotation = [0, 0, 3.020351763365065e-08]
furniture[0].optimize = 2
book_C[0].position = [2.3499999046325684, 4.949999809265137, 0.7749999761581421]
book_C[0].rotation = [0, 0, 0.01256637125682779]
book_C[0].optimize = 2
table[0].position = [2.0, 6.25, 0.3799999952316284]
table[0].rotation = [0, 0, 0.10053096307930048]
table[0].optimize = 2
book_A[0].position = [1.649999976158142, 4.949999809265137, 0.7749999761581421]
book_A[0].rotation = [0, 0, 0.01256637125682779]
book_A[0].optimize = 2
chair_L[0].position = [2.3499999046325684, 8.25, 0.4350000023841858]
chair_L[0].rotation = [0, 0, -1.5613715493341729]
chair_L[0].optimize = 2
book_B[0].position = [2.0, 4.949999809265137, 0.7749999761581421]
book_B[0].rotation = [0, 0, 1.5833626980517244]
book_B[0].optimize = 2
book_H[0].position = [2.0, 5.949999809265137, 0.7749999761581421]
book_H[0].rotation = [0, 0, 1.5833626980517244]
book_H[0].optimize = 2
chair_G[0].position = [2.950000047683716, 6.449999809265137, 0.4300000071525574]
chair_G[0].rotation = [0, 0, -3.1321678761290697]
chair_G[0].optimize = 2
bowl[0].position = [2.2799999713897705, 7.480000019073486, 0.8050000071525574]
bowl[0].rotation = [0, 0, 0.01256637125682779]
bowl[0].optimize = 2
chair_D[0].position = [1.0499999523162842, 7.5, 0.4350000023841858]
chair_D[0].rotation = [0, 0, 0.00942477746072377]
chair_D[0].optimize = 2
chair_C[0].position = [1.0499999523162842, 6.849999904632568, 0.4300000071525574]
chair_C[0].rotation = [0, 0, 0.00942477746072377]
chair_C[0].optimize = 2
bag[0].position = [0.8999999761581421, 9.770000457763672, 1.059999942779541]
bag[0].rotation = [0, 0, -1.5707963423007034]
bag[0].optimize = 2
chair_I[0].position = [1.7000000476837158, 4.25, 0.4300000071525574]
chair_I[0].rotation = [0, 0, 1.5802211042556205]
chair_I[0].optimize = 2
chair_J[0].position = [2.3499999046325684, 4.25, 0.4350000023841858]
chair_J[0].rotation = [0, 0, 1.5802211042556205]
chair_J[0].optimize = 2
book_F[0].position = [2.3499999046325684, 5.449999809265137, 0.7749999761581421]
book_F[0].rotation = [0, 0, 1.5833626980517244]
book_F[0].optimize = 2
book_G[0].position = [1.649999976158142, 5.949999809265137, 0.7749999761581421]
book_G[0].rotation = [0, 0, 0.01256637125682779]
book_G[0].optimize = 2
cabinet_A[0].position = [0.8999999761581421, 9.770001411437988, 0.44999998807907104]
cabinet_A[0].rotation = [0, 0, -1.5707963230685507]
cabinet_A[0].optimize = 2
chair_B[0].position = [1.0499999523162842, 5.550000190734863, 0.4350000023841858]
chair_B[0].rotation = [0, 0, 0.00942477746072377]
chair_B[0].optimize = 2
book_O[0].position = [2.3499999046325684, 6.949999809265137, 0.7749999761581421]
book_O[0].rotation = [0, 0, 0.01256637125682779]
book_O[0].optimize = 2
book_I[0].position = [2.3499999046325684, 5.949999809265137, 0.7799999713897705]
book_I[0].rotation = [0, 0, 0.01256637125682779]
book_I[0].optimize = 2

