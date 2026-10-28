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
    Wall(corner1=[5.00, 0.00, 0.00], corner2=[5.00, 4.00, 0.00]),
    Wall(corner1=[5.00, 4.00, 0.00], corner2=[0.00, 4.00, 0.00]),
    Wall(corner1=[0.00, 4.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
glass_A = Assets(description="A clear modern drinking glass, sleek cylindrical shape with a subtle tapered base and a faint frosted band near the lip", size=[0.08, 0.08, 0.12], placements=[AssetInstance() for _ in range(1)])
artwork_A = Assets(description="A single piece of thin and upright nature‑themed artwork, rectangular canvas with a soft pastel landscape, framed in a slim wooden border", size=[0.04, 0.65, 0.95], placements=[AssetInstance() for _ in range(1)])
plant_A = Assets(description="A small potted plant in a smooth ceramic pot, compact rounded foliage, pot glazed in muted sage green", size=[0.38, 0.38, 0.48], placements=[AssetInstance() for _ in range(1)])
plant_B = Assets(description="A small potted plant in a smooth ceramic pot, compact rounded foliage, pot glazed in muted sage green", size=[0.38, 0.38, 0.48], placements=[AssetInstance() for _ in range(1)])
pottedplant_A = Assets(description="A small potted plant in a smooth ceramic pot, compact rounded shape, muted earth‑tone glaze, with a short leafy stem emerging, biophilic style", size=[0.34, 0.34, 0.42], placements=[AssetInstance() for _ in range(1)])
pottedplant_B = Assets(description="A small potted plant in a smooth ceramic pot, compact foliage and a rounded pot silhouette", size=[0.36, 0.36, 0.44], placements=[AssetInstance() for _ in range(1)])
plant_C = Assets(description="A small indoor plant in a shallow ceramic pot, delicate leaf clusters, pot finished with a subtle speckled texture", size=[0.38, 0.42, 0.40], placements=[AssetInstance() for _ in range(1)])
candle_A = Assets(description="A small wooden-base candle with a natural bark finish, cylindrical shape and a warm amber wax tip", size=[0.08, 0.08, 0.14], placements=[AssetInstance() for _ in range(1)])
glass_B = Assets(description="A clear modern glass tumbler with a sleek cylindrical shape, smooth edges and a minimalist profile", size=[0.08, 0.08, 0.11], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="A floor lamp with a bamboo base, tapered cylindrical shape, warm light shade, natural bamboo texture, and a woven bamboo shade that diffuses light softly.", size=[0.48, 0.48, 1.65], placements=[AssetInstance() for _ in range(1)])
plate_A = Assets(description="A round ceramic plate with a smooth flat surface, subtle earth tone glaze and a thin raised rim", size=[0.28, 0.28, 0.03], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="A floor lamp with a slender bamboo base, tapered cylindrical shape, natural light‑colored bamboo finish and a simple round shade, biophilic style", size=[0.44, 0.44, 1.62], placements=[AssetInstance() for _ in range(1)])
candletable_A = Assets(description="A wooden base candle with a slender cylindrical shape, natural wood finish and a soft glowing flame at the top", size=[0.07, 0.07, 0.20], placements=[AssetInstance() for _ in range(1)])
tree_A = Assets(description="A tall indoor tree in a ceramic pot, cylindrical trunk, lush green foliage, organic silhouette, natural brown pot, with a broad canopy that spreads outward.", size=[0.95, 1.10, 2.10], placements=[AssetInstance() for _ in range(1)])
wallplant_A = Assets(description="A living plant wall panel, thin vertical slab covered with dense mixed foliage, sleek metal frame, low‑profile mounting", size=[0.12, 0.90, 1.50], placements=[AssetInstance() for _ in range(1)])
plant_D = Assets(description="A small potted plant with a round ceramic pot, compact leafy stems and a smooth pot surface", size=[0.38, 0.38, 0.50], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="An upholstered dining chair with light fabric, natural wood legs, rectangular seat, slightly curved back, soft neutral tone, organic shape, and a woven seat pattern.", size=[0.56, 0.50, 0.88], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="An upholstered dining chair with light fabric, natural wood legs, rectangular seat, slightly curved back, soft neutral tone, organic shape, and a woven seat pattern.", size=[0.56, 0.50, 0.88], placements=[AssetInstance() for _ in range(1)])
glass_C = Assets(description="A clear modern glass tumbler with a sleek cylindrical shape, smooth edges and a minimalist profile", size=[0.08, 0.08, 0.11], placements=[AssetInstance() for _ in range(1)])
glass_D = Assets(description="A clear modern glass tumbler with clean straight edges and a slightly tapered cylindrical profile", size=[0.08, 0.08, 0.12], placements=[AssetInstance() for _ in range(1)])
plant_E = Assets(description="A small indoor plant in a shallow ceramic pot, delicate leaf clusters, pot finished with a subtle speckled texture", size=[0.38, 0.42, 0.40], placements=[AssetInstance() for _ in range(1)])
glass_E = Assets(description="A clear modern glass tumbler with a sleek cylindrical shape and a thin polished rim", size=[0.08, 0.08, 0.11], placements=[AssetInstance() for _ in range(1)])
artwork_B = Assets(description="A single piece of thin and upright nature‑themed painting, rectangular canvas with a soft, muted palette depicting abstract foliage, framed in a slim wooden border", size=[0.04, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
glass_F = Assets(description="A clear modern glass tumbler with clean straight edges and a slightly tapered cylindrical profile", size=[0.08, 0.08, 0.12], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="An upholstered dining chair with light fabric, natural wood legs, rectangular seat, slightly curved back, soft neutral tone, organic shape, and a woven seat pattern.", size=[0.56, 0.50, 0.88], placements=[AssetInstance() for _ in range(1)])
artwork_C = Assets(description="A single piece of thin and upright nature‑themed painting, rectangular canvas with a soft, muted palette depicting abstract foliage, framed in a slim wooden border", size=[0.04, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
plate_B = Assets(description="A round ceramic plate with a smooth flat surface, subtle earth tone glaze and a thin raised rim", size=[0.28, 0.28, 0.03], placements=[AssetInstance() for _ in range(1)])
chair_D = Assets(description="An upholstered dining chair with light fabric, natural wood legs, rectangular seat, slightly curved back, soft neutral tone, organic shape, and a woven seat pattern.", size=[0.56, 0.50, 0.88], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="A wooden dining table with organic wood grain, rectangular shape, natural finish, smooth edges, warm brown color, featuring a subtle live‑edge contour.", size=[1.05, 2.20, 0.76], placements=[AssetInstance() for _ in range(1)])
artwork_D = Assets(description="A single piece of thin and upright nature‑themed painting with a soft pastel palette, rectangular shape and subtle brushwork", size=[0.04, 0.55, 0.85], placements=[AssetInstance() for _ in range(1)])
chair_E = Assets(description="An upholstered dining chair with light fabric, natural wood legs, rectangular seat, slightly curved back, soft neutral tone, organic shape, and a woven seat pattern.", size=[0.56, 0.50, 0.88], placements=[AssetInstance() for _ in range(1)])
candletable_B = Assets(description="A wooden base candle with a slender cylindrical shape, natural wood finish and a soft glowing flame at the top", size=[0.07, 0.07, 0.20], placements=[AssetInstance() for _ in range(1)])
candle_B = Assets(description="A small wooden-base candle with a rounded wax top, natural wood finish and a warm amber hue", size=[0.09, 0.09, 0.13], placements=[AssetInstance() for _ in range(1)])
plant_F = Assets(description="A small indoor plant in a shallow ceramic pot, delicate leaf clusters, pot finished with a subtle speckled texture", size=[0.38, 0.42, 0.40], placements=[AssetInstance() for _ in range(1)])
glass_G = Assets(description="A clear modern glass tumbler with a sleek cylindrical shape, smooth edges and a minimalist profile", size=[0.08, 0.08, 0.11], placements=[AssetInstance() for _ in range(1)])
glass_H = Assets(description="A clear modern drinking glass, sleek cylindrical shape with a subtle tapered base and a faint frosted band near the lip", size=[0.08, 0.08, 0.12], placements=[AssetInstance() for _ in range(1)])
chair_F = Assets(description="An upholstered dining chair with light fabric, natural wood legs, rectangular seat, slightly curved back, soft neutral tone, organic shape, and a woven seat pattern.", size=[0.56, 0.50, 0.88], placements=[AssetInstance() for _ in range(1)])
glass_I = Assets(description="A clear modern drinking glass, sleek cylindrical shape with a subtle tapered base and a faint frosted band near the lip", size=[0.08, 0.08, 0.12], placements=[AssetInstance() for _ in range(1)])
candle_C = Assets(description="A wooden‑base Biophilic style candle holder, rectangular base tapering to a narrow cylindrical holder, natural wood color", size=[0.08, 0.10, 0.18], placements=[AssetInstance() for _ in range(1)])
plate_C = Assets(description="A round ceramic plate with a smooth glossy surface, off‑white color and a thin concentric leaf pattern around the rim", size=[0.28, 0.28, 0.03], placements=[AssetInstance() for _ in range(1)])
sideboard = Assets(description="A wooden sideboard with organic wood, rectangular low‑slung form, natural finish, subtle grain pattern, flat top surface, and an integrated hidden drawer.", size=[0.45, 1.80, 0.80], placements=[AssetInstance() for _ in range(1)])
glass_J = Assets(description="A clear modern glass tumbler with sleek straight edges and a thin rim, giving a minimalist look", size=[0.08, 0.08, 0.11], placements=[AssetInstance() for _ in range(1)])
glass_K = Assets(description="A clear modern glass tumbler with sleek straight edges and a thin rim, giving a minimalist look", size=[0.08, 0.08, 0.11], placements=[AssetInstance() for _ in range(1)])
pottedplant_C = Assets(description="A small potted plant in a smooth ceramic pot, compact foliage and a rounded pot silhouette", size=[0.36, 0.36, 0.44], placements=[AssetInstance() for _ in range(1)])
glass_L = Assets(description="A clear modern drinking glass, sleek cylindrical shape with a subtle tapered base and a faint frosted band near the lip", size=[0.08, 0.08, 0.12], placements=[AssetInstance() for _ in range(1)])
plant_G = Assets(description="A small potted plant with a round ceramic pot, compact leafy stems and a smooth pot surface", size=[0.38, 0.38, 0.50], placements=[AssetInstance() for _ in range(1)])
candle_D = Assets(description="A small wooden-base candle with a rounded wax top, natural wood finish and a warm amber hue", size=[0.09, 0.09, 0.13], placements=[AssetInstance() for _ in range(1)])
glass_M = Assets(description="A clear modern glass tumbler with sleek straight edges and a thin rim, giving a minimalist look", size=[0.08, 0.08, 0.11], placements=[AssetInstance() for _ in range(1)])
book = Assets(description="A soft‑cover book with a rectangular shape, natural muted colors and a slightly textured paper finish, typical of biophilic design", size=[0.28, 0.21, 0.03], placements=[AssetInstance() for _ in range(1)])
candletable_C = Assets(description="A wooden base candle with a slender cylindrical shape, natural wood finish and a soft glowing flame at the top", size=[0.07, 0.07, 0.20], placements=[AssetInstance() for _ in range(1)])
wallplant_B = Assets(description="A living plant wall panel, thin vertical slab covered with dense mixed foliage, sleek metal frame, low‑profile mounting", size=[0.12, 0.90, 1.50], placements=[AssetInstance() for _ in range(1)])
plant_H = Assets(description="A small potted plant with a round ceramic pot, compact leafy stems and a smooth pot surface", size=[0.38, 0.38, 0.50], placements=[AssetInstance() for _ in range(1)])
glass_N = Assets(description="A clear modern glass tumbler with a sleek cylindrical shape and a thin polished rim", size=[0.08, 0.08, 0.11], placements=[AssetInstance() for _ in range(1)])
glass_O = Assets(description="A clear modern glass tumbler with sleek straight edges and a thin rim, giving a minimalist look", size=[0.08, 0.08, 0.11], placements=[AssetInstance() for _ in range(1)])
tree_B = Assets(description="A tall indoor tree in a ceramic pot, cylindrical trunk, lush green foliage, organic silhouette, natural brown pot, with a broad canopy that spreads outward.", size=[0.95, 1.10, 2.10], placements=[AssetInstance() for _ in range(1)])
livingplantwall = Assets(description="A vertical living plant wall panel, dense greenery covering a thin rectangular frame with a subtle wooden border", size=[0.14, 1.10, 1.65], placements=[AssetInstance() for _ in range(1)])
glass_P = Assets(description="A clear modern glass tumbler with sleek straight sides, thin rim, and a subtle frosted band near the top", size=[0.08, 0.08, 0.12], placements=[AssetInstance() for _ in range(1)])
glass_Q = Assets(description="A clear modern glass tumbler with a sleek cylindrical shape, smooth edges and a minimalist profile", size=[0.08, 0.08, 0.11], placements=[AssetInstance() for _ in range(1)])
artwork_E = Assets(description="A single piece of thin and upright nature‑themed painting with a soft pastel palette, rectangular shape and subtle brushwork", size=[0.04, 0.55, 0.85], placements=[AssetInstance() for _ in range(1)])
artwork_F = Assets(description="A single piece of thin and upright nature‑themed artwork, rectangular canvas with a soft pastel landscape, framed in a slim wooden border", size=[0.04, 0.65, 0.95], placements=[AssetInstance() for _ in range(1)])
lamp_C = Assets(description="A floor lamp with a bamboo base, tapered cylindrical shape, warm light shade, natural bamboo texture, and a woven bamboo shade that diffuses light softly.", size=[0.48, 0.48, 1.65], placements=[AssetInstance() for _ in range(1)])
plate_D = Assets(description="A round ceramic plate with a smooth glossy surface, off‑white color and a thin concentric leaf pattern around the rim", size=[0.28, 0.28, 0.03], placements=[AssetInstance() for _ in range(1)])
glass_R = Assets(description="A clear modern glass tumbler with sleek straight edges and a thin rim, giving a minimalist look", size=[0.08, 0.08, 0.11], placements=[AssetInstance() for _ in range(1)])
pottedplant_D = Assets(description="A small potted plant in a smooth ceramic pot, compact rounded shape, muted earth‑tone glaze, with a short leafy stem emerging, biophilic style", size=[0.34, 0.34, 0.42], placements=[AssetInstance() for _ in range(1)])
plant_I = Assets(description="A small indoor plant in a shallow ceramic pot, delicate leaf clusters, pot finished with a subtle speckled texture", size=[0.38, 0.42, 0.40], placements=[AssetInstance() for _ in range(1)])
plant_J = Assets(description="A small potted plant with a round ceramic pot, compact leafy stems and a smooth pot surface", size=[0.38, 0.38, 0.50], placements=[AssetInstance() for _ in range(1)])
glass_S = Assets(description="A clear modern glass tumbler with clean straight edges and a slightly tapered cylindrical profile", size=[0.08, 0.08, 0.12], placements=[AssetInstance() for _ in range(1)])

glass_A[0].instance_id = 'glass_A_0'
artwork_A[0].instance_id = 'artwork_A_0'
plant_A[0].instance_id = 'plant_A_0'
plant_B[0].instance_id = 'plant_B_0'
pottedplant_A[0].instance_id = 'pottedplant_A_0'
pottedplant_B[0].instance_id = 'pottedplant_B_0'
plant_C[0].instance_id = 'plant_C_0'
candle_A[0].instance_id = 'candle_A_0'
glass_B[0].instance_id = 'glass_B_0'
lamp_A[0].instance_id = 'lamp_A_0'
plate_A[0].instance_id = 'plate_A_0'
lamp_B[0].instance_id = 'lamp_B_0'
candletable_A[0].instance_id = 'candletable_A_0'
tree_A[0].instance_id = 'tree_A_0'
wallplant_A[0].instance_id = 'wallplant_A_0'
plant_D[0].instance_id = 'plant_D_0'
chair_A[0].instance_id = 'chair_A_0'
chair_B[0].instance_id = 'chair_B_0'
glass_C[0].instance_id = 'glass_C_0'
glass_D[0].instance_id = 'glass_D_0'
plant_E[0].instance_id = 'plant_E_0'
glass_E[0].instance_id = 'glass_E_0'
artwork_B[0].instance_id = 'artwork_B_0'
glass_F[0].instance_id = 'glass_F_0'
chair_C[0].instance_id = 'chair_C_0'
artwork_C[0].instance_id = 'artwork_C_0'
plate_B[0].instance_id = 'plate_B_0'
chair_D[0].instance_id = 'chair_D_0'
table[0].instance_id = 'table_0'
artwork_D[0].instance_id = 'artwork_D_0'
chair_E[0].instance_id = 'chair_E_0'
candletable_B[0].instance_id = 'candletable_B_0'
candle_B[0].instance_id = 'candle_B_0'
plant_F[0].instance_id = 'plant_F_0'
glass_G[0].instance_id = 'glass_G_0'
glass_H[0].instance_id = 'glass_H_0'
chair_F[0].instance_id = 'chair_F_0'
glass_I[0].instance_id = 'glass_I_0'
candle_C[0].instance_id = 'candle_C_0'
plate_C[0].instance_id = 'plate_C_0'
sideboard[0].instance_id = 'sideboard_0'
glass_J[0].instance_id = 'glass_J_0'
glass_K[0].instance_id = 'glass_K_0'
pottedplant_C[0].instance_id = 'pottedplant_C_0'
glass_L[0].instance_id = 'glass_L_0'
plant_G[0].instance_id = 'plant_G_0'
candle_D[0].instance_id = 'candle_D_0'
glass_M[0].instance_id = 'glass_M_0'
book[0].instance_id = 'book_0'
candletable_C[0].instance_id = 'candletable_C_0'
wallplant_B[0].instance_id = 'wallplant_B_0'
plant_H[0].instance_id = 'plant_H_0'
glass_N[0].instance_id = 'glass_N_0'
glass_O[0].instance_id = 'glass_O_0'
tree_B[0].instance_id = 'tree_B_0'
livingplantwall[0].instance_id = 'livingplantwall_0'
glass_P[0].instance_id = 'glass_P_0'
glass_Q[0].instance_id = 'glass_Q_0'
artwork_E[0].instance_id = 'artwork_E_0'
artwork_F[0].instance_id = 'artwork_F_0'
lamp_C[0].instance_id = 'lamp_C_0'
plate_D[0].instance_id = 'plate_D_0'
glass_R[0].instance_id = 'glass_R_0'
pottedplant_D[0].instance_id = 'pottedplant_D_0'
plant_I[0].instance_id = 'plant_I_0'
plant_J[0].instance_id = 'plant_J_0'
glass_S[0].instance_id = 'glass_S_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

glass_A[0].position = [3.8648137921586767, 3.781595732455157, 0.06]
glass_A[0].rotation = [0, 0, 0]
artwork_A[0].position = [2.7517008454131586, 2.7702530304735595, 0.475]
artwork_A[0].rotation = [0, 0, 0]
plant_A[0].position = [3.9169907673462174, 1.5488312681571785, 0.24]
plant_A[0].rotation = [0, 0, 0]
plant_B[0].position = [4.615067867935603, 1.2435986798257406, 0.24]
plant_B[0].rotation = [0, 0, 0]
pottedplant_A[0].position = [1.8119440837424445, 1.109986948441791, 0.21]
pottedplant_A[0].rotation = [0, 0, 0]
pottedplant_B[0].position = [4.165999921201607, 1.7972921133915603, 0.22]
pottedplant_B[0].rotation = [0, 0, 0]
plant_C[0].position = [0.8785947026881286, 2.1557315312514578, 0.2]
plant_C[0].rotation = [0, 0, 0]
candle_A[0].position = [1.8493437584078136, 2.3323672289326063, 0.07]
candle_A[0].rotation = [0, 0, 0]
glass_B[0].position = [2.5711566219418507, 0.6671196618787598, 0.055]
glass_B[0].rotation = [0, 0, 0]
lamp_A[0].position = [0.70160257889191, 2.8622321668823565, 0.825]
lamp_A[0].rotation = [0, 0, 0]
plate_A[0].position = [0.608240516867477, 1.6010723402145755, 0.0125]
plate_A[0].rotation = [0, 0, 0]
lamp_B[0].position = [0.4796334318258455, 1.4680503574990453, 0.81]
lamp_B[0].rotation = [0, 0, 0]
candletable_A[0].position = [1.8955593226824115, 2.797151958225416, 0.1]
candletable_A[0].rotation = [0, 0, 0]
tree_A[0].position = [0.7615742217543314, 0.01847434190898234, 1.05]
tree_A[0].rotation = [0, 0, 0]
wallplant_A[0].position = [0.6922527832404457, 3.083393743357809, 0.75]
wallplant_A[0].rotation = [0, 0, 0]
plant_D[0].position = [3.2008800965471558, 1.6595578638957695, 0.25]
plant_D[0].rotation = [0, 0, 0]
chair_A[0].position = [2.6440351124546906, 2.450735788180594, 0.44]
chair_A[0].rotation = [0, 0, 0]
chair_B[0].position = [2.4588522002731277, 0.18072918591954945, 0.44]
chair_B[0].rotation = [0, 0, 0]
glass_C[0].position = [2.1802020115009, 3.637844916196049, 0.055]
glass_C[0].rotation = [0, 0, 0]
glass_D[0].position = [4.68397856061293, 3.2734345043752926, 0.06]
glass_D[0].rotation = [0, 0, 0]
plant_E[0].position = [4.6720284694185725, 1.9070934479761967, 0.2]
plant_E[0].rotation = [0, 0, 0]
glass_E[0].position = [2.564246386014851, 1.8155725701692975, 0.055]
glass_E[0].rotation = [0, 0, 0]
artwork_B[0].position = [4.797848975604386, 3.8974184714859006, 0.45]
artwork_B[0].rotation = [0, 0, 0]
glass_F[0].position = [3.241751526975328, 0.8693676682090516, 0.06]
glass_F[0].rotation = [0, 0, 0]
chair_C[0].position = [1.0874443422157847, 2.2967079065554628, 0.44]
chair_C[0].rotation = [0, 0, 0]
artwork_C[0].position = [4.1532431457779, 1.4637420518006108, 0.45]
artwork_C[0].rotation = [0, 0, 0]
plate_B[0].position = [4.59253500403103, 2.7411429348017675, 0.0125]
plate_B[0].rotation = [0, 0, 0]
chair_D[0].position = [2.6446284894523964, 2.895829844619694, 0.44]
chair_D[0].rotation = [0, 0, 0]
table[0].position = [2.380476093653501, 0.23626553563786068, 0.38]
table[0].rotation = [0, 0, 0]
artwork_D[0].position = [2.9293939951670263, 1.0541910632530502, 0.425]
artwork_D[0].rotation = [0, 0, 0]
chair_E[0].position = [0.7793544335823016, 1.1349568159602792, 0.44]
chair_E[0].rotation = [0, 0, 0]
candletable_B[0].position = [3.122587837283908, 1.0539070848567942, 0.1]
candletable_B[0].rotation = [0, 0, 0]
candle_B[0].position = [4.15069032766331, 3.1179284807243968, 0.065]
candle_B[0].rotation = [0, 0, 0]
plant_F[0].position = [0.14007855992456464, 2.722273072309762, 0.2]
plant_F[0].rotation = [0, 0, 0]
glass_G[0].position = [3.3160471651794503, 1.681409013017642, 0.055]
glass_G[0].rotation = [0, 0, 0]
glass_H[0].position = [4.137849508882045, 0.4450533566079007, 0.06]
glass_H[0].rotation = [0, 0, 0]
chair_F[0].position = [0.1407268556554403, 2.286902736843047, 0.44]
chair_F[0].rotation = [0, 0, 0]
glass_I[0].position = [2.1696718289906065, 3.2111957466644423, 0.06]
glass_I[0].rotation = [0, 0, 0]
candle_C[0].position = [2.0915487163588864, 2.7119766873408677, 0.09]
candle_C[0].rotation = [0, 0, 0]
plate_C[0].position = [1.6303900066064714, 0.6769220951722295, 0.0125]
plate_C[0].rotation = [0, 0, 0]
sideboard[0].position = [4.996562850044663, 2.8033943817630154, 0.4]
sideboard[0].rotation = [0, 0, 0]
glass_J[0].position = [4.786102596065621, 1.7288170877494653, 0.055]
glass_J[0].rotation = [0, 0, 0]
glass_K[0].position = [0.9462078995636269, 3.488599945053241, 0.055]
glass_K[0].rotation = [0, 0, 0]
pottedplant_C[0].position = [4.945686971279189, 2.702669907683657, 0.22]
pottedplant_C[0].rotation = [0, 0, 0]
glass_L[0].position = [0.8925311065490482, 2.248602763876095, 0.06]
glass_L[0].rotation = [0, 0, 0]
plant_G[0].position = [4.960958355382793, 1.1656712692778446, 0.25]
plant_G[0].rotation = [0, 0, 0]
candle_D[0].position = [2.460794830573691, 1.2803063296026989, 0.065]
candle_D[0].rotation = [0, 0, 0]
glass_M[0].position = [3.9335458121498363, 0.021259543317694973, 0.055]
glass_M[0].rotation = [0, 0, 0]
book[0].position = [0.7035683525966518, 3.4737822641638973, 0.0125]
book[0].rotation = [0, 0, 0]
candletable_C[0].position = [0.47219918850832265, 1.4177929829020153, 0.1]
candletable_C[0].rotation = [0, 0, 0]
wallplant_B[0].position = [3.001479304682052, 0.5059907278161915, 0.75]
wallplant_B[0].rotation = [0, 0, 0]
plant_H[0].position = [2.003266230136555, 2.302958143345811, 0.25]
plant_H[0].rotation = [0, 0, 0]
glass_N[0].position = [2.2551030781791503, 3.5327074303905275, 0.055]
glass_N[0].rotation = [0, 0, 0]
glass_O[0].position = [4.9877187889383015, 2.2117882480703255, 0.055]
glass_O[0].rotation = [0, 0, 0]
tree_B[0].position = [1.4212163157355695, 3.0238979382730147, 1.05]
tree_B[0].rotation = [0, 0, 0]
livingplantwall[0].position = [1.365636584053681, 0.2629863089725233, 0.825]
livingplantwall[0].rotation = [0, 0, 0]
glass_P[0].position = [1.068732764776858, 2.112964233439964, 0.06]
glass_P[0].rotation = [0, 0, 0]
glass_Q[0].position = [4.814068252118776, 2.20719787512839, 0.055]
glass_Q[0].rotation = [0, 0, 0]
artwork_E[0].position = [0.5951691376174278, 1.228916626078329, 0.425]
artwork_E[0].rotation = [0, 0, 0]
artwork_F[0].position = [0.9363836052366326, 1.663328548455444, 0.475]
artwork_F[0].rotation = [0, 0, 0]
lamp_C[0].position = [3.2644023484773292, 2.8931717156378447, 0.825]
lamp_C[0].rotation = [0, 0, 0]
plate_D[0].position = [2.148434965448792, 1.3781646370171026, 0.0125]
plate_D[0].rotation = [0, 0, 0]
glass_R[0].position = [4.121065183432402, 0.9788682211981818, 0.055]
glass_R[0].rotation = [0, 0, 0]
pottedplant_D[0].position = [1.7684598439790755, 1.5931642746391175, 0.21]
pottedplant_D[0].rotation = [0, 0, 0]
plant_I[0].position = [0.6121300975186039, 0.6770546091975764, 0.2]
plant_I[0].rotation = [0, 0, 0]
plant_J[0].position = [2.266585886935389, 2.493438552143312, 0.25]
plant_J[0].rotation = [0, 0, 0]
glass_S[0].position = [4.192056096867838, 2.2510414419195417, 0.06]
glass_S[0].rotation = [0, 0, 0]
glass_A[0].position = [3.8648137921586767, 3.781595732455157, 0.06]
glass_A[0].rotation = [0, 0, 0]
artwork_A[0].position = [2.7517008454131586, 2.7702530304735595, 0.475]
artwork_A[0].rotation = [0, 0, 0]
plant_A[0].position = [3.9169907673462174, 1.5488312681571785, 0.24]
plant_A[0].rotation = [0, 0, 0]
plant_B[0].position = [4.615067867935603, 1.2435986798257406, 0.24]
plant_B[0].rotation = [0, 0, 0]
pottedplant_A[0].position = [1.8119440837424445, 1.109986948441791, 0.21]
pottedplant_A[0].rotation = [0, 0, 0]
pottedplant_B[0].position = [4.165999921201607, 1.7972921133915603, 0.22]
pottedplant_B[0].rotation = [0, 0, 0]
plant_C[0].position = [0.8785947026881286, 2.1557315312514578, 0.2]
plant_C[0].rotation = [0, 0, 0]
candle_A[0].position = [1.8493437584078136, 2.3323672289326063, 0.07]
candle_A[0].rotation = [0, 0, 0]
glass_B[0].position = [2.5711566219418507, 0.6671196618787598, 0.055]
glass_B[0].rotation = [0, 0, 0]
lamp_A[0].position = [0.70160257889191, 2.8622321668823565, 0.825]
lamp_A[0].rotation = [0, 0, 0]
plate_A[0].position = [0.608240516867477, 1.6010723402145755, 0.0125]
plate_A[0].rotation = [0, 0, 0]
lamp_B[0].position = [0.4796334318258455, 1.4680503574990453, 0.81]
lamp_B[0].rotation = [0, 0, 0]
candletable_A[0].position = [1.8955593226824115, 2.797151958225416, 0.1]
candletable_A[0].rotation = [0, 0, 0]
tree_A[0].position = [0.7615742217543314, 0.01847434190898234, 1.05]
tree_A[0].rotation = [0, 0, 0]
wallplant_A[0].position = [0.6922527832404457, 3.083393743357809, 0.75]
wallplant_A[0].rotation = [0, 0, 0]
plant_D[0].position = [3.2008800965471558, 1.6595578638957695, 0.25]
plant_D[0].rotation = [0, 0, 0]
chair_A[0].position = [2.6440351124546906, 2.450735788180594, 0.44]
chair_A[0].rotation = [0, 0, 0]
chair_B[0].position = [2.4588522002731277, 0.18072918591954945, 0.44]
chair_B[0].rotation = [0, 0, 0]
glass_C[0].position = [2.1802020115009, 3.637844916196049, 0.055]
glass_C[0].rotation = [0, 0, 0]
glass_D[0].position = [4.68397856061293, 3.2734345043752926, 0.06]
glass_D[0].rotation = [0, 0, 0]
plant_E[0].position = [4.6720284694185725, 1.9070934479761967, 0.2]
plant_E[0].rotation = [0, 0, 0]
glass_E[0].position = [2.564246386014851, 1.8155725701692975, 0.055]
glass_E[0].rotation = [0, 0, 0]
artwork_B[0].position = [4.797848975604386, 3.8974184714859006, 0.45]
artwork_B[0].rotation = [0, 0, 0]
glass_F[0].position = [3.241751526975328, 0.8693676682090516, 0.06]
glass_F[0].rotation = [0, 0, 0]
chair_C[0].position = [1.0874443422157847, 2.2967079065554628, 0.44]
chair_C[0].rotation = [0, 0, 0]
artwork_C[0].position = [4.1532431457779, 1.4637420518006108, 0.45]
artwork_C[0].rotation = [0, 0, 0]
plate_B[0].position = [4.59253500403103, 2.7411429348017675, 0.0125]
plate_B[0].rotation = [0, 0, 0]
chair_D[0].position = [2.6446284894523964, 2.895829844619694, 0.44]
chair_D[0].rotation = [0, 0, 0]
table[0].position = [2.380476093653501, 0.23626553563786068, 0.38]
table[0].rotation = [0, 0, 0]
artwork_D[0].position = [2.9293939951670263, 1.0541910632530502, 0.425]
artwork_D[0].rotation = [0, 0, 0]
chair_E[0].position = [0.7793544335823016, 1.1349568159602792, 0.44]
chair_E[0].rotation = [0, 0, 0]
candletable_B[0].position = [3.122587837283908, 1.0539070848567942, 0.1]
candletable_B[0].rotation = [0, 0, 0]
candle_B[0].position = [4.15069032766331, 3.1179284807243968, 0.065]
candle_B[0].rotation = [0, 0, 0]
plant_F[0].position = [0.14007855992456464, 2.722273072309762, 0.2]
plant_F[0].rotation = [0, 0, 0]
glass_G[0].position = [3.3160471651794503, 1.681409013017642, 0.055]
glass_G[0].rotation = [0, 0, 0]
glass_H[0].position = [4.137849508882045, 0.4450533566079007, 0.06]
glass_H[0].rotation = [0, 0, 0]
chair_F[0].position = [0.1407268556554403, 2.286902736843047, 0.44]
chair_F[0].rotation = [0, 0, 0]
glass_I[0].position = [2.1696718289906065, 3.2111957466644423, 0.06]
glass_I[0].rotation = [0, 0, 0]
candle_C[0].position = [2.0915487163588864, 2.7119766873408677, 0.09]
candle_C[0].rotation = [0, 0, 0]
plate_C[0].position = [1.6303900066064714, 0.6769220951722295, 0.0125]
plate_C[0].rotation = [0, 0, 0]
sideboard[0].position = [4.996562850044663, 2.8033943817630154, 0.4]
sideboard[0].rotation = [0, 0, 0]
glass_J[0].position = [4.786102596065621, 1.7288170877494653, 0.055]
glass_J[0].rotation = [0, 0, 0]
glass_K[0].position = [0.9462078995636269, 3.488599945053241, 0.055]
glass_K[0].rotation = [0, 0, 0]
pottedplant_C[0].position = [4.945686971279189, 2.702669907683657, 0.22]
pottedplant_C[0].rotation = [0, 0, 0]
glass_L[0].position = [0.8925311065490482, 2.248602763876095, 0.06]
glass_L[0].rotation = [0, 0, 0]
plant_G[0].position = [4.960958355382793, 1.1656712692778446, 0.25]
plant_G[0].rotation = [0, 0, 0]
candle_D[0].position = [2.460794830573691, 1.2803063296026989, 0.065]
candle_D[0].rotation = [0, 0, 0]
glass_M[0].position = [3.9335458121498363, 0.021259543317694973, 0.055]
glass_M[0].rotation = [0, 0, 0]
book[0].position = [0.7035683525966518, 3.4737822641638973, 0.0125]
book[0].rotation = [0, 0, 0]
candletable_C[0].position = [0.47219918850832265, 1.4177929829020153, 0.1]
candletable_C[0].rotation = [0, 0, 0]
wallplant_B[0].position = [3.001479304682052, 0.5059907278161915, 0.75]
wallplant_B[0].rotation = [0, 0, 0]
plant_H[0].position = [2.003266230136555, 2.302958143345811, 0.25]
plant_H[0].rotation = [0, 0, 0]
glass_N[0].position = [2.2551030781791503, 3.5327074303905275, 0.055]
glass_N[0].rotation = [0, 0, 0]
glass_O[0].position = [4.9877187889383015, 2.2117882480703255, 0.055]
glass_O[0].rotation = [0, 0, 0]
tree_B[0].position = [1.4212163157355695, 3.0238979382730147, 1.05]
tree_B[0].rotation = [0, 0, 0]
livingplantwall[0].position = [1.365636584053681, 0.2629863089725233, 0.825]
livingplantwall[0].rotation = [0, 0, 0]
glass_P[0].position = [1.068732764776858, 2.112964233439964, 0.06]
glass_P[0].rotation = [0, 0, 0]
glass_Q[0].position = [4.814068252118776, 2.20719787512839, 0.055]
glass_Q[0].rotation = [0, 0, 0]
artwork_E[0].position = [0.5951691376174278, 1.228916626078329, 0.425]
artwork_E[0].rotation = [0, 0, 0]
artwork_F[0].position = [0.9363836052366326, 1.663328548455444, 0.475]
artwork_F[0].rotation = [0, 0, 0]
lamp_C[0].position = [3.2644023484773292, 2.8931717156378447, 0.825]
lamp_C[0].rotation = [0, 0, 0]
plate_D[0].position = [2.148434965448792, 1.3781646370171026, 0.0125]
plate_D[0].rotation = [0, 0, 0]
glass_R[0].position = [4.121065183432402, 0.9788682211981818, 0.055]
glass_R[0].rotation = [0, 0, 0]
pottedplant_D[0].position = [1.7684598439790755, 1.5931642746391175, 0.21]
pottedplant_D[0].rotation = [0, 0, 0]
plant_I[0].position = [0.6121300975186039, 0.6770546091975764, 0.2]
plant_I[0].rotation = [0, 0, 0]
plant_J[0].position = [2.266585886935389, 2.493438552143312, 0.25]
plant_J[0].rotation = [0, 0, 0]
glass_S[0].position = [4.192056096867838, 2.2510414419195417, 0.06]
glass_S[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed reference points are used to preserve the intended coordinates if the
# solver later adjusts the layout for physical feasibility.
def _place(asset_obj, position, yaw_degrees):
    asset_obj[0].position = list(position)
    asset_obj[0].rotation = [0, 0, radians(yaw_degrees)]
    solver.distance_constraint(
        asset_obj[0],
        AssetInstance(position=list(position)),
        0,
        0,
        weight=10,
    )


def _keep_orientation(asset_obj, yaw_degrees):
    solver.align_with(
        asset_obj[0],
        AssetInstance(rotation=[0, 0, radians(yaw_degrees)]),
        angle=0,
    )


# The table occupies the center of the room, while the sideboard is kept
# against the left wall. This leaves the approach from the door at (5, 2.3)
# unobstructed.
_place(table, [2.65, 2.05, 0.38], 0)
_place(sideboard, [0.225, 2.50, 0.40], 0)

_keep_orientation(table, 0)
_keep_orientation(sideboard, 0)
solver.against_wall(sideboard[0], walls[3])


# Six chairs surround the long dining table. The east side is left sufficiently
# open to provide circulation from the door. Chair_A (o0016) directly faces
# chair_D (o0027), as requested.
_place(chair_A, [1.78, 2.05, 0.44], 0)
_place(chair_D, [3.52, 2.05, 0.44], 180)

_place(chair_B, [2.25, 3.48, 0.44], 270)
_place(chair_C, [3.05, 3.48, 0.44], 270)
_place(chair_E, [2.25, 0.62, 0.44], 90)
_place(chair_F, [3.05, 0.62, 0.44], 90)

solver.point_towards(chair_A[0], chair_D[0])
solver.point_towards(chair_D[0], chair_A[0])
solver.point_towards(chair_B[0], table[0])
solver.point_towards(chair_C[0], table[0])
solver.point_towards(chair_E[0], table[0])
solver.point_towards(chair_F[0], table[0])

# Maintain useful seating distances without forcing the table to move.
for _chair_obj in (chair_A, chair_B, chair_C, chair_D, chair_E, chair_F):
    solver.distance_constraint(
        _chair_obj[0], table[0], 0.85, 1.55, weight=1
    )


# Tall floor elements occupy corners and peripheral zones. None is placed in
# front of the door, and the two trees stay away from the dining chairs.
_place(tree_A, [0.65, 0.62, 1.05], 45)
_place(tree_B, [4.35, 0.62, 1.05], 135)

_place(lamp_A, [0.30, 3.68, 0.825], 315)
_place(lamp_B, [4.70, 3.68, 0.81], 225)
_place(lamp_C, [1.35, 3.68, 0.825], 270)

for _floor_feature in (tree_A, tree_B, lamp_A, lamp_B, lamp_C):
    solver.point_towards(_floor_feature[0], table[0])


# Plant_A (o0002) is centered between Plant_I (o0064) and Plant_F (o0033)
# on the sideboard. Plant_B completes a balanced four-plant arrangement.
_sideboard_top = 0.80
_place(plant_B, [0.225, 1.80, _sideboard_top + 0.24], 0)
_place(plant_I, [0.225, 2.25, _sideboard_top + 0.20], 0)
_place(plant_A, [0.225, 2.70, _sideboard_top + 0.24], 0)
_place(plant_F, [0.225, 3.15, _sideboard_top + 0.20], 0)

for _sideboard_plant in (plant_B, plant_I, plant_A, plant_F):
    solver.on_top_of(_sideboard_plant[0], sideboard[0])
    _keep_orientation(_sideboard_plant, 0)

# These equal distances explicitly preserve the requested "between" relation.
solver.distance_constraint(
    plant_A[0], plant_I[0], 0.45, 0.45, weight=10
)
solver.distance_constraint(
    plant_A[0], plant_F[0], 0.45, 0.45, weight=10
)
solver.distance_constraint(
    plant_I[0], plant_F[0], 0.90, 0.90, weight=10
)


# Remaining small plants form low peripheral groupings. Their locations avoid
# the table, chair footprints, door opening, and the two large trees.
_floor_plant_specs = [
    (pottedplant_A, [1.78, 3.78, 0.21], 270),
    (plant_C,       [3.58, 3.77, 0.20], 270),
    (pottedplant_B, [4.12, 3.78, 0.22], 225),
    (plant_D,       [4.76, 3.12, 0.25], 180),
    (plant_E,       [4.75, 1.48, 0.20], 180),
    (pottedplant_C, [3.65, 0.22, 0.22], 90),
    (plant_G,       [1.48, 0.22, 0.25], 90),
    (plant_H,       [0.25, 1.35, 0.25], 0),
    (pottedplant_D, [0.25, 0.92, 0.21], 20),
    (plant_J,       [4.75, 0.98, 0.25], 160),
]

for _plant_obj, _plant_position, _plant_yaw in _floor_plant_specs:
    _place(_plant_obj, _plant_position, _plant_yaw)
    solver.point_towards(_plant_obj[0], table[0])


# Living-wall panels use the window-free south wall. They are raised above the
# floor and face into the room.
_wall_panel_specs = [
    (wallplant_A,    [1.00, 0.06, 1.45], 90),
    (wallplant_B,    [2.50, 0.06, 1.45], 90),
    (livingplantwall,[4.00, 0.07, 1.50], 90),
]

for _panel_obj, _panel_position, _panel_yaw in _wall_panel_specs:
    _place(_panel_obj, _panel_position, _panel_yaw)
    solver.against_wall(_panel_obj[0], walls[0])
    _keep_orientation(_panel_obj, _panel_yaw)


# Artwork is mounted on the side walls so it does not cover the three north-wall
# windows. Right-wall pieces are kept above and below the door span.
_artwork_specs = [
    (artwork_A, [0.02, 0.48, 1.55], 0,   walls[3]),
    (artwork_B, [0.02, 1.20, 1.50], 0,   walls[3]),
    (artwork_C, [0.02, 3.62, 1.50], 0,   walls[3]),
    (artwork_D, [4.98, 0.45, 1.48], 180, walls[1]),
    (artwork_E, [4.98, 1.20, 1.48], 180, walls[1]),
    (artwork_F, [4.98, 3.58, 1.55], 180, walls[1]),
]

for _art_obj, _art_position, _art_yaw, _art_wall in _artwork_specs:
    _place(_art_obj, _art_position, _art_yaw)
    solver.against_wall(_art_obj[0], _art_wall)
    _keep_orientation(_art_obj, _art_yaw)


# Place settings are distributed along both sides of the tabletop. The centers
# remain inside its 1.05 m by 2.20 m top, with spacing between neighboring
# glasses.
_table_top = 0.76

_glass_specs = [
    (glass_A, [2.18, 1.08, _table_top + 0.06]),
    (glass_B, [2.18, 1.29, _table_top + 0.055]),
    (glass_C, [2.18, 1.50, _table_top + 0.055]),  # o0018
    (glass_D, [2.18, 1.71, _table_top + 0.06]),
    (glass_E, [2.18, 1.92, _table_top + 0.055]),
    (glass_F, [2.18, 2.13, _table_top + 0.06]),
    (glass_G, [2.18, 2.34, _table_top + 0.055]),
    (glass_H, [2.18, 2.55, _table_top + 0.06]),
    (glass_I, [2.18, 2.76, _table_top + 0.06]),
    (glass_J, [2.18, 2.97, _table_top + 0.055]),
    (glass_K, [3.12, 1.08, _table_top + 0.055]),
    (glass_L, [3.12, 1.29, _table_top + 0.06]),
    (glass_M, [3.12, 1.50, _table_top + 0.055]),
    (glass_N, [3.12, 1.71, _table_top + 0.055]),
    (glass_O, [3.12, 1.92, _table_top + 0.055]),
    (glass_P, [3.12, 2.13, _table_top + 0.06]),
    (glass_Q, [3.12, 2.34, _table_top + 0.055]),
    (glass_R, [3.12, 2.55, _table_top + 0.055]),
    (glass_S, [3.12, 2.76, _table_top + 0.06]),
]

for _glass_obj, _glass_position in _glass_specs:
    _place(_glass_obj, _glass_position, 0)
    # This includes the required glass_C/o0018-on-table/o0028 relation.
    solver.on_top_of(_glass_obj[0], table[0])
    solver.align_with(_glass_obj[0], table[0])


# Four plates create distinct place settings without intersecting the rows of
# glasses.
_plate_specs = [
    (plate_A, [2.42, 1.38, _table_top + 0.015], 0),
    (plate_B, [2.88, 1.38, _table_top + 0.015], 0),
    (plate_C, [2.42, 2.70, _table_top + 0.015], 180),
    (plate_D, [2.88, 2.70, _table_top + 0.015], 180),
]

for _plate_obj, _plate_position, _plate_yaw in _plate_specs:
    _place(_plate_obj, _plate_position, _plate_yaw)
    solver.on_top_of(_plate_obj[0], table[0])
    solver.align_with(_plate_obj[0], table[0], angle=_plate_yaw)


# Candles form a loose center-line arrangement while the book sits at the
# center of the table. All small accessories receive both an exact positional
# constraint and an orientation constraint in addition to their support
# relation.
_table_accessory_specs = [
    (candle_A,     [2.65, 1.08, _table_top + 0.07], 0),
    (candletable_A,[2.65, 1.72, _table_top + 0.10], 0),
    (candle_B,     [2.65, 2.38, _table_top + 0.065], 0),
    (candletable_B,[2.65, 3.00, _table_top + 0.10], 0),
    (candle_C,     [2.35, 2.05, _table_top + 0.09], 0),
    (candle_D,     [2.95, 2.05, _table_top + 0.065], 0),
    (candletable_C,[2.65, 1.98, _table_top + 0.10], 0),
    (book,         [2.65, 2.17, _table_top + 0.015], 0),
]

for _accessory_obj, _accessory_position, _accessory_yaw in _table_accessory_specs:
    _place(_accessory_obj, _accessory_position, _accessory_yaw)
    solver.on_top_of(_accessory_obj[0], table[0])
    solver.align_with(_accessory_obj[0], table[0], angle=_accessory_yaw)

solver.constraints = []
glass_S[0].position = [3.000518560409546, 2.725287437438965, 0.8199999928474426]
glass_S[0].rotation = [0, 0, 0.1299939874920078]
glass_S[0].optimize = 2
pottedplant_D[0].position = [0.25, 0.9200000166893005, 0.20999999344348907]
pottedplant_D[0].rotation = [0, 0, 0.35849063180849555]
pottedplant_D[0].optimize = 2
glass_R[0].position = [3.0567805767059326, 2.531633138656616, 0.8149999976158142]
glass_R[0].rotation = [0, 0, 0.1299939874920078]
glass_R[0].optimize = 2
plant_C[0].position = [3.5799999237060547, 3.7699999809265137, 0.20000000298023224]
plant_C[0].rotation = [0, 0, -1.6193885797888343]
plant_C[0].optimize = 2
candle_B[0].position = [2.6500000953674316, 2.380000114440918, 0.824999988079071]
candle_B[0].rotation = [0, 0, 0.1299939874920078]
candle_B[0].optimize = 2
glass_A[0].position = [2.3691389560699463, 1.1349499225616455, 0.8199999928474426]
glass_A[0].rotation = [0, 0, 0.1299939874920078]
glass_A[0].optimize = 2
glass_O[0].position = [3.119999885559082, 1.9199999570846558, 0.8149999976158142]
glass_O[0].rotation = [0, 0, 0.1299939874920078]
glass_O[0].optimize = 2
plate_B[0].position = [2.880000114440918, 1.3799999952316284, 0.7749999761581421]
plate_B[0].rotation = [0, 0, 0.1299939874920078]
plate_B[0].optimize = 2
chair_D[0].position = [3.5199999809265137, 2.049999952316284, 0.4399999976158142]
chair_D[0].rotation = [0, 0, -3.125884689672577]
chair_D[0].optimize = 2
plant_B[0].position = [0.22499999403953552, 1.7999999523162842, 1.0399999618530273]
plant_B[0].rotation = [0, 0, 0.01256637125682779]
plant_B[0].optimize = 2
glass_D[0].position = [2.2003533840179443, 1.7159132957458496, 0.8199999928474426]
glass_D[0].rotation = [0, 0, 0.1299939874920078]
glass_D[0].optimize = 2
glass_M[0].position = [3.119999885559082, 1.5, 0.8149999976158142]
glass_M[0].rotation = [0, 0, 0.1299939874920078]
glass_M[0].optimize = 2
lamp_A[0].position = [0.3393961787223816, 3.6606037616729736, 0.824999988079071]
lamp_A[0].rotation = [0, 0, -0.7759733982318487]
lamp_A[0].optimize = 2
glass_N[0].position = [3.119999885559082, 1.7100000381469727, 0.8149999976158142]
glass_N[0].rotation = [0, 0, 0.1299939874920078]
glass_N[0].optimize = 2
glass_E[0].position = [2.180000066757202, 1.9199999570846558, 0.8149999976158142]
glass_E[0].rotation = [0, 0, 0.1299939874920078]
glass_E[0].optimize = 2
chair_E[0].position = [2.25, 0.6200000047683716, 0.4399999976158142]
chair_E[0].rotation = [0, 0, 1.5833626980517244]
chair_E[0].optimize = 2
livingplantwall[0].position = [4.0, 0.07006999850273132, 0.824999988079071]
livingplantwall[0].rotation = [0, 0, 1.5750112308525792]
livingplantwall[0].optimize = 2
plant_G[0].position = [1.4800000190734863, 0.2199999988079071, 0.25]
plant_G[0].rotation = [0, 0, 1.4702190034385558]
plant_G[0].optimize = 2
artwork_D[0].position = [4.981812953948975, 0.44999998807907104, 0.42500001192092896]
artwork_D[0].rotation = [0, 0, -3.137378619341403]
artwork_D[0].optimize = 2
artwork_A[0].position = [0.017969943583011627, 0.47999998927116394, 0.4749999940395355]
artwork_A[0].rotation = [0, 0, 0.004214057366952943]
artwork_A[0].optimize = 2
candle_C[0].position = [2.3499999046325684, 2.049999952316284, 0.8500000238418579]
candle_C[0].rotation = [0, 0, 0.1299939874920078]
candle_C[0].optimize = 2
book[0].position = [2.6500000953674316, 2.1700000762939453, 0.7749999761581421]
book[0].rotation = [0, 0, 0.1299939874920078]
book[0].optimize = 2
glass_H[0].position = [2.180000066757202, 2.549999952316284, 0.8199999928474426]
glass_H[0].rotation = [0, 0, 0.1299939874920078]
glass_H[0].optimize = 2
plant_F[0].position = [0.22499999403953552, 3.1500000953674316, 1.0]
plant_F[0].rotation = [0, 0, 0.01884955539881635]
plant_F[0].optimize = 2
plant_D[0].position = [4.760000228881836, 3.119999885559082, 0.25]
plant_D[0].rotation = [0, 0, -3.1321678761290697]
plant_D[0].optimize = 2
plant_E[0].position = [4.75, 1.4800000190734863, 0.20000000298023224]
plant_E[0].rotation = [0, 0, -3.1321678761290697]
plant_E[0].optimize = 2
tree_B[0].position = [4.275747299194336, 0.725252091884613, 1.0499999523162842]
tree_B[0].rotation = [0, 0, 2.3656192553579443]
tree_B[0].optimize = 2
plant_H[0].position = [0.25, 1.350000023841858, 0.25]
plant_H[0].rotation = [0, 0, 0.00942477746072377]
plant_H[0].optimize = 2
glass_B[0].position = [2.3128771781921387, 1.3286043405532837, 0.8149999976158142]
glass_B[0].rotation = [0, 0, 0.1299939874920078]
glass_B[0].optimize = 2
glass_J[0].position = [2.180000066757202, 2.9700000286102295, 0.8149999976158142]
glass_J[0].rotation = [0, 0, 0.1299939874920078]
glass_J[0].optimize = 2
table[0].position = [2.6500000953674316, 2.049999952316284, 0.3799999952316284]
table[0].rotation = [0, 0, 0.2827433292194083]
table[0].optimize = 2
artwork_C[0].position = [0.017969945445656776, 3.619999885559082, 0.44999998807907104]
artwork_C[0].rotation = [0, 0, 0.004214060183320288]
artwork_C[0].optimize = 2
candletable_B[0].position = [2.6500000953674316, 3.0, 0.8600000143051147]
candletable_B[0].rotation = [0, 0, 0.1299939874920078]
candletable_B[0].optimize = 2
plant_A[0].position = [0.22499999403953552, 2.700000047683716, 1.0399999618530273]
plant_A[0].rotation = [0, 0, 0.01884955539881635]
plant_A[0].optimize = 2
candletable_A[0].position = [2.6500000953674316, 1.7200000286102295, 0.8600000143051147]
candletable_A[0].rotation = [0, 0, 0.1299939874920078]
candletable_A[0].optimize = 2
candle_D[0].position = [2.950000047683716, 2.049999952316284, 0.824999988079071]
candle_D[0].rotation = [0, 0, 0.1299939874920078]
candle_D[0].optimize = 2
chair_C[0].position = [3.049999952316284, 3.4800000190734863, 0.4399999976158142]
chair_C[0].rotation = [0, 0, -1.5582299555380688]
chair_C[0].optimize = 2
chair_F[0].position = [3.049999952316284, 0.6200000047683716, 0.4399999976158142]
chair_F[0].rotation = [0, 0, 1.5833626980517244]
chair_F[0].optimize = 2
plant_I[0].position = [0.22499999403953552, 2.25, 1.0]
plant_I[0].rotation = [0, 0, 0.01884955539881635]
plant_I[0].optimize = 2
candle_A[0].position = [2.6500000953674316, 1.0800000429153442, 0.8299999833106995]
candle_A[0].rotation = [0, 0, 0.1299939874920078]
candle_A[0].optimize = 2
glass_F[0].position = [2.180000066757202, 2.130000114440918, 0.8199999928474426]
glass_F[0].rotation = [0, 0, 0.1299939874920078]
glass_F[0].optimize = 2
pottedplant_A[0].position = [1.7799999713897705, 3.7799999713897705, 0.20999999344348907]
pottedplant_A[0].rotation = [0, 0, -1.4886942152581075]
pottedplant_A[0].optimize = 2
glass_K[0].position = [3.119999885559082, 1.0800000429153442, 0.8149999976158142]
glass_K[0].rotation = [0, 0, 0.1299939874920078]
glass_K[0].optimize = 2
glass_P[0].position = [3.119999885559082, 2.130000114440918, 0.8199999928474426]
glass_P[0].rotation = [0, 0, 0.1299939874920078]
glass_P[0].optimize = 2
sideboard[0].position = [0.22811448574066162, 2.5, 0.4000000059604645]
sideboard[0].rotation = [0, 0, -0.0008295700903024118]
sideboard[0].optimize = 2
tree_A[0].position = [0.725252091884613, 0.7242525219917297, 1.0499999523162842]
tree_A[0].rotation = [0, 0, 0.7948229285630478]
tree_A[0].optimize = 2
pottedplant_B[0].position = [4.119999885559082, 3.745452642440796, 0.2199999988079071]
pottedplant_B[0].rotation = [0, 0, -2.3467697250267454]
pottedplant_B[0].optimize = 2
glass_I[0].position = [2.180000066757202, 2.759999990463257, 0.8199999928474426]
glass_I[0].rotation = [0, 0, 0.1299939874920078]
glass_I[0].optimize = 2
glass_G[0].position = [2.180000066757202, 2.3399999141693115, 0.8149999976158142]
glass_G[0].rotation = [0, 0, 0.1299939874920078]
glass_G[0].optimize = 2
artwork_F[0].position = [4.982146263122559, 3.5799999237060547, 0.4749999940395355]
artwork_F[0].rotation = [0, 0, -3.1373785718569205]
artwork_F[0].optimize = 2
candletable_C[0].position = [2.6500000953674316, 1.9800000190734863, 0.8600000143051147]
candletable_C[0].rotation = [0, 0, 0.1299939874920078]
candletable_C[0].optimize = 2
wallplant_A[0].position = [1.0, 0.05967411398887634, 0.75]
wallplant_A[0].rotation = [0, 0, 1.5750111651068877]
wallplant_A[0].optimize = 2
chair_A[0].position = [1.7799999713897705, 2.049999952316284, 0.4399999976158142]
chair_A[0].rotation = [0, 0, 0.0157079639172164]
chair_A[0].optimize = 2
lamp_B[0].position = [4.688886642456055, 3.680000066757202, 0.8100000023841858]
lamp_B[0].rotation = [0, 0, -2.3467697250267454]
lamp_B[0].optimize = 2
pottedplant_C[0].position = [3.6500000953674316, 0.2199999988079071, 0.2199999988079071]
pottedplant_C[0].rotation = [0, 0, 1.69842288176817]
pottedplant_C[0].optimize = 2
lamp_C[0].position = [1.350000023841858, 3.680000066757202, 0.824999988079071]
lamp_C[0].rotation = [0, 0, -1.442847871915479]
lamp_C[0].optimize = 2
glass_C[0].position = [2.256615400314331, 1.5222587585449219, 0.8149999976158142]
glass_C[0].rotation = [0, 0, 0.1299939874920078]
glass_C[0].optimize = 2
wallplant_B[0].position = [2.5, 0.05967411398887634, 0.75]
wallplant_B[0].rotation = [0, 0, 1.5750111651068877]
wallplant_B[0].optimize = 2
plate_C[0].position = [2.4200000762939453, 2.700000047683716, 0.7749999761581421]
plate_C[0].rotation = [0, 0, -3.0115986660977856]
plate_C[0].optimize = 2
plant_J[0].position = [4.75, 0.9800000190734863, 0.25]
plant_J[0].rotation = [0, 0, 2.8019515862910915]
plant_J[0].optimize = 2
glass_Q[0].position = [3.119999885559082, 2.3399999141693115, 0.8149999976158142]
glass_Q[0].rotation = [0, 0, 0.1299939874920078]
glass_Q[0].optimize = 2
artwork_B[0].position = [0.017969945445656776, 1.2000000476837158, 0.44999998807907104]
artwork_B[0].rotation = [0, 0, 0.004214060183320288]
artwork_B[0].optimize = 2
plate_D[0].position = [2.880000114440918, 2.700000047683716, 0.7749999761581421]
plate_D[0].rotation = [0, 0, -3.0115986660977856]
plate_D[0].optimize = 2
plate_A[0].position = [2.4200000762939453, 1.3799999952316284, 0.7749999761581421]
plate_A[0].rotation = [0, 0, 0.1299939874920078]
plate_A[0].optimize = 2
chair_B[0].position = [2.25, 3.4800000190734863, 0.4399999976158142]
chair_B[0].rotation = [0, 0, -1.5582299555380688]
chair_B[0].optimize = 2
glass_L[0].position = [3.119999885559082, 1.2899999618530273, 0.8199999928474426]
glass_L[0].rotation = [0, 0, 0.1299939874920078]
glass_L[0].optimize = 2
artwork_E[0].position = [4.981812953948975, 1.2000000476837158, 0.42500001192092896]
artwork_E[0].rotation = [0, 0, -3.137378619341403]
artwork_E[0].optimize = 2

