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
glass_A = Assets(description="A clear modern drinking glass, sleek cylindrical shape with a subtle tapered base and a faint frosted band near the lip", size=[0.08, 0.08, 0.13], placements=[AssetInstance() for _ in range(1)])
artwork_A = Assets(description="A single piece of thin and upright nature‑themed artwork, rectangular canvas with a soft pastel landscape, framed in a slim wooden border", size=[0.04, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
plant_A = Assets(description="A small potted plant in a smooth ceramic pot, compact rounded foliage, pot glazed in muted sage green", size=[0.28, 0.28, 0.40], placements=[AssetInstance() for _ in range(1)])
plant_B = Assets(description="A small potted plant in a smooth ceramic pot, compact rounded foliage, pot glazed in muted sage green", size=[0.28, 0.28, 0.40], placements=[AssetInstance() for _ in range(1)])
pottedplant_A = Assets(description="A small potted plant in a smooth ceramic pot, compact rounded shape, muted earth‑tone glaze, with a short leafy stem emerging, biophilic style", size=[0.24, 0.24, 0.35], placements=[AssetInstance() for _ in range(1)])
pottedplant_B = Assets(description="A small potted plant in a smooth ceramic pot, compact foliage and a rounded pot silhouette", size=[0.28, 0.28, 0.38], placements=[AssetInstance() for _ in range(1)])
plant_C = Assets(description="A small indoor plant in a shallow ceramic pot, delicate leaf clusters, pot finished with a subtle speckled texture", size=[0.30, 0.30, 0.32], placements=[AssetInstance() for _ in range(1)])
candle_A = Assets(description="A small wooden-base candle with a natural bark finish, cylindrical shape and a warm amber wax tip", size=[0.07, 0.07, 0.12], placements=[AssetInstance() for _ in range(1)])
glass_B = Assets(description="A clear modern glass tumbler with a sleek cylindrical shape, smooth edges and a minimalist profile", size=[0.08, 0.08, 0.10], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="A floor lamp with a bamboo base, tapered cylindrical shape, warm light shade, natural bamboo texture, and a woven bamboo shade that diffuses light softly.", size=[0.38, 0.38, 1.55], placements=[AssetInstance() for _ in range(1)])
plate_A = Assets(description="A round ceramic plate with a smooth flat surface, subtle earth tone glaze and a thin raised rim", size=[0.27, 0.27, 0.03], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="A floor lamp with a slender bamboo base, tapered cylindrical shape, natural light‑colored bamboo finish and a simple round shade, biophilic style", size=[0.35, 0.35, 1.60], placements=[AssetInstance() for _ in range(1)])
candletable_A = Assets(description="A wooden base candle with a slender cylindrical shape, natural wood finish and a soft glowing flame at the top", size=[0.06, 0.06, 0.22], placements=[AssetInstance() for _ in range(1)])
tree_A = Assets(description="A tall indoor tree in a ceramic pot, cylindrical trunk, lush green foliage, organic silhouette, natural brown pot, with a broad canopy that spreads outward.", size=[0.85, 0.85, 1.90], placements=[AssetInstance() for _ in range(1)])
wallplant_A = Assets(description="A living plant wall panel, thin vertical slab covered with dense mixed foliage, sleek metal frame, low‑profile mounting", size=[0.18, 0.65, 1.00], placements=[AssetInstance() for _ in range(1)])
plant_D = Assets(description="A small potted plant with a round ceramic pot, compact leafy stems and a smooth pot surface", size=[0.26, 0.26, 0.38], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="An upholstered dining chair with light fabric, natural wood legs, rectangular seat, slightly curved back, soft neutral tone, organic shape, and a woven seat pattern.", size=[0.56, 0.50, 0.85], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="An upholstered dining chair with light fabric, natural wood legs, rectangular seat, slightly curved back, soft neutral tone, organic shape, and a woven seat pattern.", size=[0.56, 0.50, 0.85], placements=[AssetInstance() for _ in range(1)])
glass_C = Assets(description="A clear modern glass tumbler with a sleek cylindrical shape, smooth edges and a minimalist profile", size=[0.08, 0.08, 0.10], placements=[AssetInstance() for _ in range(1)])
glass_D = Assets(description="A clear modern glass tumbler with clean straight edges and a slightly tapered cylindrical profile", size=[0.08, 0.08, 0.11], placements=[AssetInstance() for _ in range(1)])
plant_E = Assets(description="A small indoor plant in a shallow ceramic pot, delicate leaf clusters, pot finished with a subtle speckled texture", size=[0.30, 0.30, 0.32], placements=[AssetInstance() for _ in range(1)])
glass_E = Assets(description="A clear modern glass tumbler with a sleek cylindrical shape and a thin polished rim", size=[0.08, 0.08, 0.10], placements=[AssetInstance() for _ in range(1)])
artwork_B = Assets(description="A single piece of thin and upright nature‑themed painting, rectangular canvas with a soft, muted palette depicting abstract foliage, framed in a slim wooden border", size=[0.04, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])
glass_F = Assets(description="A clear modern glass tumbler with clean straight edges and a slightly tapered cylindrical profile", size=[0.08, 0.08, 0.11], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="An upholstered dining chair with light fabric, natural wood legs, rectangular seat, slightly curved back, soft neutral tone, organic shape, and a woven seat pattern.", size=[0.56, 0.50, 0.85], placements=[AssetInstance() for _ in range(1)])
artwork_C = Assets(description="A single piece of thin and upright nature‑themed painting, rectangular canvas with a soft, muted palette depicting abstract foliage, framed in a slim wooden border", size=[0.04, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])
plate_B = Assets(description="A round ceramic plate with a smooth flat surface, subtle earth tone glaze and a thin raised rim", size=[0.27, 0.27, 0.03], placements=[AssetInstance() for _ in range(1)])
chair_D = Assets(description="An upholstered dining chair with light fabric, natural wood legs, rectangular seat, slightly curved back, soft neutral tone, organic shape, and a woven seat pattern.", size=[0.56, 0.50, 0.85], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="A wooden dining table with organic wood grain, rectangular shape, natural finish, smooth edges, warm brown color, featuring a subtle live‑edge contour.", size=[1.00, 2.10, 0.76], placements=[AssetInstance() for _ in range(1)])
artwork_D = Assets(description="A single piece of thin and upright nature‑themed painting with a soft pastel palette, rectangular shape and subtle brushwork", size=[0.03, 0.45, 0.65], placements=[AssetInstance() for _ in range(1)])
chair_E = Assets(description="An upholstered dining chair with light fabric, natural wood legs, rectangular seat, slightly curved back, soft neutral tone, organic shape, and a woven seat pattern.", size=[0.56, 0.50, 0.85], placements=[AssetInstance() for _ in range(1)])
candletable_B = Assets(description="A wooden base candle with a slender cylindrical shape, natural wood finish and a soft glowing flame at the top", size=[0.06, 0.06, 0.22], placements=[AssetInstance() for _ in range(1)])
candle_B = Assets(description="A small wooden-base candle with a rounded wax top, natural wood finish and a warm amber hue", size=[0.07, 0.07, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_F = Assets(description="A small indoor plant in a shallow ceramic pot, delicate leaf clusters, pot finished with a subtle speckled texture", size=[0.30, 0.30, 0.32], placements=[AssetInstance() for _ in range(1)])
glass_G = Assets(description="A clear modern glass tumbler with a sleek cylindrical shape, smooth edges and a minimalist profile", size=[0.08, 0.08, 0.10], placements=[AssetInstance() for _ in range(1)])
glass_H = Assets(description="A clear modern drinking glass, sleek cylindrical shape with a subtle tapered base and a faint frosted band near the lip", size=[0.08, 0.08, 0.13], placements=[AssetInstance() for _ in range(1)])
chair_F = Assets(description="An upholstered dining chair with light fabric, natural wood legs, rectangular seat, slightly curved back, soft neutral tone, organic shape, and a woven seat pattern.", size=[0.56, 0.50, 0.85], placements=[AssetInstance() for _ in range(1)])
glass_I = Assets(description="A clear modern drinking glass, sleek cylindrical shape with a subtle tapered base and a faint frosted band near the lip", size=[0.08, 0.08, 0.13], placements=[AssetInstance() for _ in range(1)])
candle_C = Assets(description="A wooden‑base Biophilic style candle holder, rectangular base tapering to a narrow cylindrical holder, natural wood color", size=[0.09, 0.09, 0.18], placements=[AssetInstance() for _ in range(1)])
plate_C = Assets(description="A round ceramic plate with a smooth glossy surface, off‑white color and a thin concentric leaf pattern around the rim", size=[0.27, 0.27, 0.03], placements=[AssetInstance() for _ in range(1)])
sideboard = Assets(description="A wooden sideboard with organic wood, rectangular low‑slung form, natural finish, subtle grain pattern, flat top surface, and an integrated hidden drawer.", size=[0.42, 1.50, 0.78], placements=[AssetInstance() for _ in range(1)])
glass_J = Assets(description="A clear modern glass tumbler with sleek straight edges and a thin rim, giving a minimalist look", size=[0.07, 0.07, 0.10], placements=[AssetInstance() for _ in range(1)])
glass_K = Assets(description="A clear modern glass tumbler with sleek straight edges and a thin rim, giving a minimalist look", size=[0.07, 0.07, 0.10], placements=[AssetInstance() for _ in range(1)])
pottedplant_C = Assets(description="A small potted plant in a smooth ceramic pot, compact foliage and a rounded pot silhouette", size=[0.28, 0.28, 0.38], placements=[AssetInstance() for _ in range(1)])
glass_L = Assets(description="A clear modern drinking glass, sleek cylindrical shape with a subtle tapered base and a faint frosted band near the lip", size=[0.08, 0.08, 0.13], placements=[AssetInstance() for _ in range(1)])
plant_G = Assets(description="A small potted plant with a round ceramic pot, compact leafy stems and a smooth pot surface", size=[0.26, 0.26, 0.38], placements=[AssetInstance() for _ in range(1)])
candle_D = Assets(description="A small wooden-base candle with a rounded wax top, natural wood finish and a warm amber hue", size=[0.07, 0.07, 0.10], placements=[AssetInstance() for _ in range(1)])
glass_M = Assets(description="A clear modern glass tumbler with sleek straight edges and a thin rim, giving a minimalist look", size=[0.07, 0.07, 0.10], placements=[AssetInstance() for _ in range(1)])
book = Assets(description="A soft‑cover book with a rectangular shape, natural muted colors and a slightly textured paper finish, typical of biophilic design", size=[0.23, 0.15, 0.02], placements=[AssetInstance() for _ in range(1)])
candletable_C = Assets(description="A wooden base candle with a slender cylindrical shape, natural wood finish and a soft glowing flame at the top", size=[0.06, 0.06, 0.22], placements=[AssetInstance() for _ in range(1)])
wallplant_B = Assets(description="A living plant wall panel, thin vertical slab covered with dense mixed foliage, sleek metal frame, low‑profile mounting", size=[0.18, 0.65, 1.00], placements=[AssetInstance() for _ in range(1)])
plant_H = Assets(description="A small potted plant with a round ceramic pot, compact leafy stems and a smooth pot surface", size=[0.26, 0.26, 0.38], placements=[AssetInstance() for _ in range(1)])
glass_N = Assets(description="A clear modern glass tumbler with a sleek cylindrical shape and a thin polished rim", size=[0.08, 0.08, 0.10], placements=[AssetInstance() for _ in range(1)])
glass_O = Assets(description="A clear modern glass tumbler with sleek straight edges and a thin rim, giving a minimalist look", size=[0.07, 0.07, 0.10], placements=[AssetInstance() for _ in range(1)])
tree_B = Assets(description="A tall indoor tree in a ceramic pot, cylindrical trunk, lush green foliage, organic silhouette, natural brown pot, with a broad canopy that spreads outward.", size=[0.85, 0.85, 1.90], placements=[AssetInstance() for _ in range(1)])
livingplantwall = Assets(description="A vertical living plant wall panel, dense greenery covering a thin rectangular frame with a subtle wooden border", size=[0.18, 0.70, 1.20], placements=[AssetInstance() for _ in range(1)])
glass_P = Assets(description="A clear modern glass tumbler with sleek straight sides, thin rim, and a subtle frosted band near the top", size=[0.08, 0.08, 0.12], placements=[AssetInstance() for _ in range(1)])
glass_Q = Assets(description="A clear modern glass tumbler with a sleek cylindrical shape, smooth edges and a minimalist profile", size=[0.08, 0.08, 0.10], placements=[AssetInstance() for _ in range(1)])
artwork_E = Assets(description="A single piece of thin and upright nature‑themed painting with a soft pastel palette, rectangular shape and subtle brushwork", size=[0.03, 0.45, 0.65], placements=[AssetInstance() for _ in range(1)])
artwork_F = Assets(description="A single piece of thin and upright nature‑themed artwork, rectangular canvas with a soft pastel landscape, framed in a slim wooden border", size=[0.04, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
lamp_C = Assets(description="A floor lamp with a bamboo base, tapered cylindrical shape, warm light shade, natural bamboo texture, and a woven bamboo shade that diffuses light softly.", size=[0.38, 0.38, 1.55], placements=[AssetInstance() for _ in range(1)])
plate_D = Assets(description="A round ceramic plate with a smooth glossy surface, off‑white color and a thin concentric leaf pattern around the rim", size=[0.27, 0.27, 0.03], placements=[AssetInstance() for _ in range(1)])
glass_R = Assets(description="A clear modern glass tumbler with sleek straight edges and a thin rim, giving a minimalist look", size=[0.07, 0.07, 0.10], placements=[AssetInstance() for _ in range(1)])
pottedplant_D = Assets(description="A small potted plant in a smooth ceramic pot, compact rounded shape, muted earth‑tone glaze, with a short leafy stem emerging, biophilic style", size=[0.24, 0.24, 0.35], placements=[AssetInstance() for _ in range(1)])
plant_I = Assets(description="A small indoor plant in a shallow ceramic pot, delicate leaf clusters, pot finished with a subtle speckled texture", size=[0.30, 0.30, 0.32], placements=[AssetInstance() for _ in range(1)])
plant_J = Assets(description="A small potted plant with a round ceramic pot, compact leafy stems and a smooth pot surface", size=[0.26, 0.26, 0.38], placements=[AssetInstance() for _ in range(1)])
glass_S = Assets(description="A clear modern glass tumbler with clean straight edges and a slightly tapered cylindrical profile", size=[0.08, 0.08, 0.11], placements=[AssetInstance() for _ in range(1)])

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

glass_A[0].position = [1.1042526792747025, 1.0720952609951429, 0.065]
glass_A[0].rotation = [0, 0, 0]
artwork_A[0].position = [0.4716050266237315, 2.765153505273931, 0.35]
artwork_A[0].rotation = [0, 0, 0]
plant_A[0].position = [4.160143923640362, 1.8486262497804264, 0.2]
plant_A[0].rotation = [0, 0, 0]
plant_B[0].position = [3.9747786634662328, 0.7937971746902956, 0.2]
plant_B[0].rotation = [0, 0, 0]
pottedplant_A[0].position = [0.7146260644849389, 0.7744608397640724, 0.175]
pottedplant_A[0].rotation = [0, 0, 0]
pottedplant_B[0].position = [3.3181540263675284, 3.7788961031889006, 0.19]
pottedplant_B[0].rotation = [0, 0, 0]
plant_C[0].position = [2.35189408290927, 3.112635544751513, 0.16]
plant_C[0].rotation = [0, 0, 0]
candle_A[0].position = [3.14149502645211, 2.2738368143190266, 0.06]
candle_A[0].rotation = [0, 0, 0]
glass_B[0].position = [4.529748771216562, 1.9734116122011232, 0.05]
glass_B[0].rotation = [0, 0, 0]
lamp_A[0].position = [1.1271356256399616, 2.488147692287039, 0.775]
lamp_A[0].rotation = [0, 0, 0]
plate_A[0].position = [2.7468583112651697, 2.937701243145802, 0.0125]
plate_A[0].rotation = [0, 0, 0]
lamp_B[0].position = [0.16440348398505278, 2.250991974335567, 0.8]
lamp_B[0].rotation = [0, 0, 0]
candletable_A[0].position = [2.322878432620144, 2.033641458196838, 0.11]
candletable_A[0].rotation = [0, 0, 0]
tree_A[0].position = [4.141800410721531, 2.782430758839495, 0.95]
tree_A[0].rotation = [0, 0, 0]
wallplant_A[0].position = [1.8103193016075432, 2.72163054473394, 0.5]
wallplant_A[0].rotation = [0, 0, 0]
plant_D[0].position = [4.908886805157618, 0.5227620760514959, 0.19]
plant_D[0].rotation = [0, 0, 0]
chair_A[0].position = [1.8548309358498445, 3.735697146748722, 0.425]
chair_A[0].rotation = [0, 0, 0]
chair_B[0].position = [2.8991713099116274, 0.27682663245036565, 0.425]
chair_B[0].rotation = [0, 0, 0]
glass_C[0].position = [3.1682735816094203, 1.4076912478183319, 0.05]
glass_C[0].rotation = [0, 0, 0]
glass_D[0].position = [0.45830913255966943, 0.5205391021836636, 0.055]
glass_D[0].rotation = [0, 0, 0]
plant_E[0].position = [0.3864985309388136, 3.296014333184732, 0.16]
plant_E[0].rotation = [0, 0, 0]
glass_E[0].position = [1.371110324139675, 2.691494544686376, 0.05]
glass_E[0].rotation = [0, 0, 0]
artwork_B[0].position = [0.9857117310157065, 0.6710170434754934, 0.3]
artwork_B[0].rotation = [0, 0, 0]
glass_F[0].position = [1.1322695373854774, 3.632492845917751, 0.055]
glass_F[0].rotation = [0, 0, 0]
chair_C[0].position = [2.1525557072119517, 3.4908165451612905, 0.425]
chair_C[0].rotation = [0, 0, 0]
artwork_C[0].position = [1.44345372911994, 3.0833250357726594, 0.3]
artwork_C[0].rotation = [0, 0, 0]
plate_B[0].position = [1.8767087763679053, 3.327660286528479, 0.0125]
plate_B[0].rotation = [0, 0, 0]
chair_D[0].position = [3.0442844791409893, 2.750562609265559, 0.425]
chair_D[0].rotation = [0, 0, 0]
table[0].position = [3.505219893089988, 3.524247368909332, 0.38]
table[0].rotation = [0, 0, 0]
artwork_D[0].position = [2.897947502432942, 1.1398597522836775, 0.325]
artwork_D[0].rotation = [0, 0, 0]
chair_E[0].position = [0.20631632093922658, 1.414574370289369, 0.425]
chair_E[0].rotation = [0, 0, 0]
candletable_B[0].position = [0.2649015835137791, 1.0075023102203207, 0.11]
candletable_B[0].rotation = [0, 0, 0]
candle_B[0].position = [3.9343982607939436, 2.4295862548628526, 0.05]
candle_B[0].rotation = [0, 0, 0]
plant_F[0].position = [2.5018341599203806, 2.3192373857527633, 0.16]
plant_F[0].rotation = [0, 0, 0]
glass_G[0].position = [2.7964913701565166, 0.7327448138646733, 0.05]
glass_G[0].rotation = [0, 0, 0]
glass_H[0].position = [0.6557908092413062, 2.7435988957915938, 0.065]
glass_H[0].rotation = [0, 0, 0]
chair_F[0].position = [2.594556125521257, 1.2557545697705796, 0.425]
chair_F[0].rotation = [0, 0, 0]
glass_I[0].position = [4.810045982932577, 2.9495118398971836, 0.065]
glass_I[0].rotation = [0, 0, 0]
candle_C[0].position = [1.4978446195811312, 1.145649176653376, 0.09]
candle_C[0].rotation = [0, 0, 0]
plate_C[0].position = [0.5311385213938519, 0.9694129368338804, 0.0125]
plate_C[0].rotation = [0, 0, 0]
sideboard[0].position = [3.765310246103924, 3.935619577438357, 0.39]
sideboard[0].rotation = [0, 0, 0]
glass_J[0].position = [2.627137999680547, 2.6416923257318423, 0.05]
glass_J[0].rotation = [0, 0, 0]
glass_K[0].position = [0.01935044350008075, 1.4471817281812385, 0.05]
glass_K[0].rotation = [0, 0, 0]
pottedplant_C[0].position = [3.714726552417069, 1.974324523758141, 0.19]
pottedplant_C[0].rotation = [0, 0, 0]
glass_L[0].position = [2.527609638810651, 1.4876336715704226, 0.065]
glass_L[0].rotation = [0, 0, 0]
plant_G[0].position = [4.93411635361297, 0.8533764428979618, 0.19]
plant_G[0].rotation = [0, 0, 0]
candle_D[0].position = [3.4228061393602798, 2.610122060536948, 0.05]
candle_D[0].rotation = [0, 0, 0]
glass_M[0].position = [3.5700002729025426, 2.8593819928465134, 0.05]
glass_M[0].rotation = [0, 0, 0]
book[0].position = [3.2767304735280565, 0.15105261254064306, 0.01]
book[0].rotation = [0, 0, 0]
candletable_C[0].position = [4.5217948634702045, 1.5360094474670918, 0.11]
candletable_C[0].rotation = [0, 0, 0]
wallplant_B[0].position = [1.3848575979029225, 3.9734712512340633, 0.5]
wallplant_B[0].rotation = [0, 0, 0]
plant_H[0].position = [4.8051445539713935, 3.326574371394567, 0.19]
plant_H[0].rotation = [0, 0, 0]
glass_N[0].position = [2.6521004475708225, 2.054119360624956, 0.05]
glass_N[0].rotation = [0, 0, 0]
glass_O[0].position = [0.37607118966582087, 3.7004660956459037, 0.05]
glass_O[0].rotation = [0, 0, 0]
tree_B[0].position = [1.4208520116299521, 2.773564471293816, 0.95]
tree_B[0].rotation = [0, 0, 0]
livingplantwall[0].position = [0.0711312065020081, 0.5295377804197456, 0.6]
livingplantwall[0].rotation = [0, 0, 0]
glass_P[0].position = [1.5186428553851723, 0.2907409147874467, 0.06]
glass_P[0].rotation = [0, 0, 0]
glass_Q[0].position = [1.490495488957878, 2.137009022290684, 0.05]
glass_Q[0].rotation = [0, 0, 0]
artwork_E[0].position = [4.062915709428107, 0.3339864457627799, 0.325]
artwork_E[0].rotation = [0, 0, 0]
artwork_F[0].position = [0.5662940979114034, 3.013069972074816, 0.35]
artwork_F[0].rotation = [0, 0, 0]
lamp_C[0].position = [1.2998385145991875, 2.783926827041346, 0.775]
lamp_C[0].rotation = [0, 0, 0]
plate_D[0].position = [3.72973231515339, 1.502383704734267, 0.0125]
plate_D[0].rotation = [0, 0, 0]
glass_R[0].position = [3.951512339115391, 2.6160152909673635, 0.05]
glass_R[0].rotation = [0, 0, 0]
pottedplant_D[0].position = [3.1200974657449527, 3.427699684981152, 0.175]
pottedplant_D[0].rotation = [0, 0, 0]
plant_I[0].position = [4.37009016670657, 0.52775736980329, 0.16]
plant_I[0].rotation = [0, 0, 0]
plant_J[0].position = [0.14455506381844563, 1.603781008018157, 0.19]
plant_J[0].rotation = [0, 0, 0]
glass_S[0].position = [2.2519618291975996, 0.3848540696735476, 0.055]
glass_S[0].rotation = [0, 0, 0]
glass_A[0].position = [1.1042526792747025, 1.0720952609951429, 0.065]
glass_A[0].rotation = [0, 0, 0]
artwork_A[0].position = [0.4716050266237315, 2.765153505273931, 0.35]
artwork_A[0].rotation = [0, 0, 0]
plant_A[0].position = [4.160143923640362, 1.8486262497804264, 0.2]
plant_A[0].rotation = [0, 0, 0]
plant_B[0].position = [3.9747786634662328, 0.7937971746902956, 0.2]
plant_B[0].rotation = [0, 0, 0]
pottedplant_A[0].position = [0.7146260644849389, 0.7744608397640724, 0.175]
pottedplant_A[0].rotation = [0, 0, 0]
pottedplant_B[0].position = [3.3181540263675284, 3.7788961031889006, 0.19]
pottedplant_B[0].rotation = [0, 0, 0]
plant_C[0].position = [2.35189408290927, 3.112635544751513, 0.16]
plant_C[0].rotation = [0, 0, 0]
candle_A[0].position = [3.14149502645211, 2.2738368143190266, 0.06]
candle_A[0].rotation = [0, 0, 0]
glass_B[0].position = [4.529748771216562, 1.9734116122011232, 0.05]
glass_B[0].rotation = [0, 0, 0]
lamp_A[0].position = [1.1271356256399616, 2.488147692287039, 0.775]
lamp_A[0].rotation = [0, 0, 0]
plate_A[0].position = [2.7468583112651697, 2.937701243145802, 0.0125]
plate_A[0].rotation = [0, 0, 0]
lamp_B[0].position = [0.16440348398505278, 2.250991974335567, 0.8]
lamp_B[0].rotation = [0, 0, 0]
candletable_A[0].position = [2.322878432620144, 2.033641458196838, 0.11]
candletable_A[0].rotation = [0, 0, 0]
tree_A[0].position = [4.141800410721531, 2.782430758839495, 0.95]
tree_A[0].rotation = [0, 0, 0]
wallplant_A[0].position = [1.8103193016075432, 2.72163054473394, 0.5]
wallplant_A[0].rotation = [0, 0, 0]
plant_D[0].position = [4.908886805157618, 0.5227620760514959, 0.19]
plant_D[0].rotation = [0, 0, 0]
chair_A[0].position = [1.8548309358498445, 3.735697146748722, 0.425]
chair_A[0].rotation = [0, 0, 0]
chair_B[0].position = [2.8991713099116274, 0.27682663245036565, 0.425]
chair_B[0].rotation = [0, 0, 0]
glass_C[0].position = [3.1682735816094203, 1.4076912478183319, 0.05]
glass_C[0].rotation = [0, 0, 0]
glass_D[0].position = [0.45830913255966943, 0.5205391021836636, 0.055]
glass_D[0].rotation = [0, 0, 0]
plant_E[0].position = [0.3864985309388136, 3.296014333184732, 0.16]
plant_E[0].rotation = [0, 0, 0]
glass_E[0].position = [1.371110324139675, 2.691494544686376, 0.05]
glass_E[0].rotation = [0, 0, 0]
artwork_B[0].position = [0.9857117310157065, 0.6710170434754934, 0.3]
artwork_B[0].rotation = [0, 0, 0]
glass_F[0].position = [1.1322695373854774, 3.632492845917751, 0.055]
glass_F[0].rotation = [0, 0, 0]
chair_C[0].position = [2.1525557072119517, 3.4908165451612905, 0.425]
chair_C[0].rotation = [0, 0, 0]
artwork_C[0].position = [1.44345372911994, 3.0833250357726594, 0.3]
artwork_C[0].rotation = [0, 0, 0]
plate_B[0].position = [1.8767087763679053, 3.327660286528479, 0.0125]
plate_B[0].rotation = [0, 0, 0]
chair_D[0].position = [3.0442844791409893, 2.750562609265559, 0.425]
chair_D[0].rotation = [0, 0, 0]
table[0].position = [3.505219893089988, 3.524247368909332, 0.38]
table[0].rotation = [0, 0, 0]
artwork_D[0].position = [2.897947502432942, 1.1398597522836775, 0.325]
artwork_D[0].rotation = [0, 0, 0]
chair_E[0].position = [0.20631632093922658, 1.414574370289369, 0.425]
chair_E[0].rotation = [0, 0, 0]
candletable_B[0].position = [0.2649015835137791, 1.0075023102203207, 0.11]
candletable_B[0].rotation = [0, 0, 0]
candle_B[0].position = [3.9343982607939436, 2.4295862548628526, 0.05]
candle_B[0].rotation = [0, 0, 0]
plant_F[0].position = [2.5018341599203806, 2.3192373857527633, 0.16]
plant_F[0].rotation = [0, 0, 0]
glass_G[0].position = [2.7964913701565166, 0.7327448138646733, 0.05]
glass_G[0].rotation = [0, 0, 0]
glass_H[0].position = [0.6557908092413062, 2.7435988957915938, 0.065]
glass_H[0].rotation = [0, 0, 0]
chair_F[0].position = [2.594556125521257, 1.2557545697705796, 0.425]
chair_F[0].rotation = [0, 0, 0]
glass_I[0].position = [4.810045982932577, 2.9495118398971836, 0.065]
glass_I[0].rotation = [0, 0, 0]
candle_C[0].position = [1.4978446195811312, 1.145649176653376, 0.09]
candle_C[0].rotation = [0, 0, 0]
plate_C[0].position = [0.5311385213938519, 0.9694129368338804, 0.0125]
plate_C[0].rotation = [0, 0, 0]
sideboard[0].position = [3.765310246103924, 3.935619577438357, 0.39]
sideboard[0].rotation = [0, 0, 0]
glass_J[0].position = [2.627137999680547, 2.6416923257318423, 0.05]
glass_J[0].rotation = [0, 0, 0]
glass_K[0].position = [0.01935044350008075, 1.4471817281812385, 0.05]
glass_K[0].rotation = [0, 0, 0]
pottedplant_C[0].position = [3.714726552417069, 1.974324523758141, 0.19]
pottedplant_C[0].rotation = [0, 0, 0]
glass_L[0].position = [2.527609638810651, 1.4876336715704226, 0.065]
glass_L[0].rotation = [0, 0, 0]
plant_G[0].position = [4.93411635361297, 0.8533764428979618, 0.19]
plant_G[0].rotation = [0, 0, 0]
candle_D[0].position = [3.4228061393602798, 2.610122060536948, 0.05]
candle_D[0].rotation = [0, 0, 0]
glass_M[0].position = [3.5700002729025426, 2.8593819928465134, 0.05]
glass_M[0].rotation = [0, 0, 0]
book[0].position = [3.2767304735280565, 0.15105261254064306, 0.01]
book[0].rotation = [0, 0, 0]
candletable_C[0].position = [4.5217948634702045, 1.5360094474670918, 0.11]
candletable_C[0].rotation = [0, 0, 0]
wallplant_B[0].position = [1.3848575979029225, 3.9734712512340633, 0.5]
wallplant_B[0].rotation = [0, 0, 0]
plant_H[0].position = [4.8051445539713935, 3.326574371394567, 0.19]
plant_H[0].rotation = [0, 0, 0]
glass_N[0].position = [2.6521004475708225, 2.054119360624956, 0.05]
glass_N[0].rotation = [0, 0, 0]
glass_O[0].position = [0.37607118966582087, 3.7004660956459037, 0.05]
glass_O[0].rotation = [0, 0, 0]
tree_B[0].position = [1.4208520116299521, 2.773564471293816, 0.95]
tree_B[0].rotation = [0, 0, 0]
livingplantwall[0].position = [0.0711312065020081, 0.5295377804197456, 0.6]
livingplantwall[0].rotation = [0, 0, 0]
glass_P[0].position = [1.5186428553851723, 0.2907409147874467, 0.06]
glass_P[0].rotation = [0, 0, 0]
glass_Q[0].position = [1.490495488957878, 2.137009022290684, 0.05]
glass_Q[0].rotation = [0, 0, 0]
artwork_E[0].position = [4.062915709428107, 0.3339864457627799, 0.325]
artwork_E[0].rotation = [0, 0, 0]
artwork_F[0].position = [0.5662940979114034, 3.013069972074816, 0.35]
artwork_F[0].rotation = [0, 0, 0]
lamp_C[0].position = [1.2998385145991875, 2.783926827041346, 0.775]
lamp_C[0].rotation = [0, 0, 0]
plate_D[0].position = [3.72973231515339, 1.502383704734267, 0.0125]
plate_D[0].rotation = [0, 0, 0]
glass_R[0].position = [3.951512339115391, 2.6160152909673635, 0.05]
glass_R[0].rotation = [0, 0, 0]
pottedplant_D[0].position = [3.1200974657449527, 3.427699684981152, 0.175]
pottedplant_D[0].rotation = [0, 0, 0]
plant_I[0].position = [4.37009016670657, 0.52775736980329, 0.16]
plant_I[0].rotation = [0, 0, 0]
plant_J[0].position = [0.14455506381844563, 1.603781008018157, 0.19]
plant_J[0].rotation = [0, 0, 0]
glass_S[0].position = [2.2519618291975996, 0.3848540696735476, 0.055]
glass_S[0].rotation = [0, 0, 0]

solver.constraints = []

# Coordinates follow the supplied walls: the room is [0, 5] x [0, 4].
# The dining group is shifted left to leave the east-door approach clear.
# Object-ID aliases were not supplied; the named glass instances all go on
# the table, plant_A is placed between plant_B and plant_C, and each pair
# of opposing chairs faces one another.

def locate(asset_group, xyz, yaw=0):
    asset_group[0].position = list(xyz)
    asset_group[0].rotation = [0, 0, radians(yaw)]


def anchor(asset_group):
    # A fixed reference preserves the intended position, including height.
    solver.distance_constraint(
        asset_group[0],
        AssetInstance(position=list(asset_group[0].position)),
        0, 0, weight=10
    )


locate(table, [2.30, 2.00, 0.38])
anchor(table)
solver.align_with(table[0], AssetInstance(rotation=[0, 0, 0]))

# Rotate the sideboard so its long dimension runs along the south wall.
locate(sideboard, [2.20, 0.21, 0.39], 90)
anchor(sideboard)
solver.against_wall(sideboard[0], walls[0])
solver.align_with(sideboard[0], table[0], 90)

# Three chairs on either long side. Their bounding boxes stop short of
# the table, and the eastern chairs leave a clear route from the door.
chair_layout = [
    (chair_A, 1.38, 1.30, 0, chair_D),
    (chair_B, 1.38, 2.00, 0, chair_E),
    (chair_C, 1.38, 2.70, 0, chair_F),
    (chair_D, 3.22, 1.30, 180, chair_A),
    (chair_E, 3.22, 2.00, 180, chair_B),
    (chair_F, 3.22, 2.70, 180, chair_C),
]
for group, px, py, yaw, opposite in chair_layout:
    locate(group, [px, py, group.size[2] / 2], yaw)

for group, px, py, yaw, opposite in chair_layout:
    solver.point_towards(group[0], opposite[0])
    anchor(group)
    separation = sum(
        (group[0].position[k] - table[0].position[k]) ** 2
        for k in range(3)
    ) ** 0.5
    solver.distance_constraint(group[0], table[0],
                               separation, separation, weight=10)

# Tabletop plants form a straight, evenly spaced central arrangement.
# In particular, plant_A is exactly between plant_B and plant_C.
for group, py in [(plant_B, 1.35), (plant_A, 2.00), (plant_C, 2.65)]:
    locate(group, [2.30, py, 0.76 + group.size[2] / 2])
    solver.on_top_of(group[0], table[0])
    anchor(group)
    solver.align_with(group[0], table[0])

for endpoint in (plant_B, plant_C):
    center_distance = sum(
        (plant_A[0].position[k] - endpoint[0].position[k]) ** 2
        for k in range(3)
    ) ** 0.5
    solver.distance_constraint(plant_A[0], endpoint[0],
                               center_distance, center_distance, weight=10)

# Four plates leave the central greenery and the table ends unobstructed.
plate_layout = [
    (plate_A, 1.97, 1.65),
    (plate_B, 2.63, 1.65),
    (plate_C, 1.97, 2.35),
    (plate_D, 2.63, 2.35),
]
for group, px, py in plate_layout:
    locate(group, [px, py, 0.76 + group.size[2] / 2])
    solver.on_top_of(group[0], table[0])
    anchor(group)
    solver.align_with(group[0], table[0])

# All nineteen glasses are supported by the dining tabletop. The small
# clusters occupy the ends and the clear strip between the plate settings.
glass_layout = [
    (glass_A, 1.90, 1.08), (glass_B, 2.08, 1.08),
    (glass_C, 2.50, 1.08), (glass_D, 2.69, 1.08),
    (glass_E, 1.90, 2.92), (glass_F, 2.08, 2.92),
    (glass_G, 2.50, 2.92), (glass_H, 2.69, 2.92),
    (glass_I, 1.93, 1.95), (glass_J, 2.09, 1.95),
    (glass_K, 2.51, 1.95), (glass_L, 2.67, 1.95),
    (glass_M, 1.93, 2.10), (glass_N, 2.09, 2.10),
    (glass_O, 2.51, 2.10), (glass_P, 2.67, 2.10),
    (glass_Q, 1.90, 1.30), (glass_R, 2.69, 1.30),
    (glass_S, 2.69, 2.70),
]
for group, px, py in glass_layout:
    locate(group, [px, py, 0.76 + group.size[2] / 2])
    solver.on_top_of(group[0], table[0])
    anchor(group)
    solver.align_with(group[0], table[0])

# Candles occupy narrow gaps, away from foliage and glass clusters.
candle_layout = [
    (candle_A, 2.30, 1.08),
    (candle_B, 2.30, 2.92),
    (candle_C, 2.30, 1.67),
    (candle_D, 2.30, 2.33),
    (candletable_A, 1.92, 2.72),
    (candletable_B, 2.68, 2.52),
    (candletable_C, 1.92, 1.48),
]
for group, px, py in candle_layout:
    locate(group, [px, py, 0.76 + group.size[2] / 2])
    solver.on_top_of(group[0], table[0])
    anchor(group)
    solver.align_with(group[0], table[0])

# A low, accessible planted display on the sideboard.
for group, px in [
    (pottedplant_A, 1.61), (pottedplant_B, 2.00),
    (pottedplant_C, 2.39), (pottedplant_D, 2.80)
]:
    locate(group, [px, 0.21, 0.78 + group.size[2] / 2])
    solver.on_top_of(group[0], sideboard[0])
    anchor(group)
    solver.align_with(group[0], sideboard[0])

locate(book, [3.34, 0.21, 0.79])
solver.on_top_of(book[0], sideboard[0])
anchor(book)
solver.align_with(book[0], table[0])

# These are freestanding floor pots, rather than unsupported tabletop
# accessories. A low row beneath the windows keeps the glazing exposed.
floor_plant_layout = [
    (plant_D, 0.92, 3.78),
    (plant_E, 1.40, 3.78),
    (plant_F, 1.88, 3.78),
    (plant_G, 2.36, 3.78),
    (plant_H, 2.84, 3.78),
    (plant_I, 3.32, 3.78),
    (plant_J, 3.80, 3.78),
]
for group, px, py in floor_plant_layout:
    locate(group, [px, py, group.size[2] / 2], 270)
    anchor(group)
    solver.align_with(group[0], table[0], 270)

# Tall greenery and floor lighting stay outside the dining and entry paths.
floor_feature_layout = [
    (tree_A, 0.48, 3.48, 0),
    (tree_B, 4.48, 0.48, 180),
    (lamp_A, 0.30, 0.35, 0),
    (lamp_B, 0.30, 2.00, 0),
    (lamp_C, 4.70, 3.65, 180),
]
for group, px, py, yaw in floor_feature_layout:
    locate(group, [px, py, group.size[2] / 2], yaw)
    anchor(group)
    solver.align_with(group[0], table[0], yaw)

# Wall-mounted pieces use their thin local x dimension as wall depth.
# None is mounted across the north windows or the east doorway.
wall_layout = [
    (artwork_A, 3, 0.020, 0.85, 1.55, 0),
    (artwork_B, 3, 0.020, 1.60, 1.55, 0),
    (artwork_C, 3, 0.020, 2.35, 1.55, 0),
    (artwork_D, 0, 1.350, 0.015, 1.65, 90),
    (artwork_E, 0, 2.200, 0.015, 1.65, 90),
    (artwork_F, 0, 3.100, 0.020, 1.65, 90),
    (wallplant_A, 1, 4.910, 0.90, 1.65, 180),
    (wallplant_B, 1, 4.910, 3.35, 1.80, 180),
    (livingplantwall, 3, 0.090, 3.35, 2.65, 0),
]
for group, wall_index, px, py, pz, yaw in wall_layout:
    locate(group, [px, py, pz], yaw)
    anchor(group)  # Preserve the mounting height; these are not floor assets.
    solver.against_wall(group[0], walls[wall_index])
    solver.align_with(group[0], table[0], yaw)

solver.constraints = []
artwork_E[0].position = [2.200000047683716, 0.015000000596046448, 0.32499998807907104]
artwork_E[0].rotation = [0, 0, 1.5707963688613091]
artwork_E[0].optimize = 2
glass_K[0].position = [2.509999990463257, 1.9500000476837158, 0.8100000023841858]
glass_K[0].rotation = [0, 0, 0.3078760682295954]
glass_K[0].optimize = 2
chair_C[0].position = [1.3770138025283813, 2.7017855644226074, 0.42500001192092896]
chair_C[0].rotation = [0, 0, 0.0157079639172164]
chair_C[0].optimize = 2
candle_D[0].position = [2.299999952316284, 2.3299999237060547, 0.8100000023841858]
candle_D[0].rotation = [0, 0, 0.3078760682295954]
candle_D[0].optimize = 2
plate_C[0].position = [1.9700000286102295, 2.3499999046325684, 0.7749999761581421]
plate_C[0].rotation = [0, 0, 0.3078760682295954]
plate_C[0].optimize = 2
table[0].position = [2.299999952316284, 2.0, 0.3799999952316284]
table[0].rotation = [0, 0, 0.3078760747812666]
table[0].optimize = 2
plant_I[0].position = [3.319999933242798, 3.7799999713897705, 0.1599999964237213]
plant_I[0].rotation = [0, 0, -1.262920281455031]
plant_I[0].optimize = 2
pottedplant_A[0].position = [1.6100000143051147, 0.20999999344348907, 0.9549999833106995]
pottedplant_A[0].rotation = [0, 0, 1.5707965904477663]
pottedplant_A[0].optimize = 2
artwork_C[0].position = [0.019999995827674866, 2.3499999046325684, 0.30000001192092896]
artwork_C[0].rotation = [0, 0, 4.2050822724751076e-08]
artwork_C[0].optimize = 2
plant_F[0].position = [1.8799999952316284, 3.7799999713897705, 0.1599999964237213]
plant_F[0].rotation = [0, 0, -1.262920281455031]
plant_F[0].optimize = 2
candle_A[0].position = [2.299999952316284, 1.0800000429153442, 0.8199999928474426]
candle_A[0].rotation = [0, 0, 0.3078760682295954]
candle_A[0].optimize = 2
lamp_B[0].position = [0.30000001192092896, 2.0, 0.800000011920929]
lamp_B[0].rotation = [0, 0, 0.3078760547490114]
lamp_B[0].optimize = 2
plant_B[0].position = [2.299999952316284, 1.350000023841858, 0.9599999785423279]
plant_B[0].rotation = [0, 0, 0.3078760552858371]
plant_B[0].optimize = 2
plate_D[0].position = [2.630000114440918, 2.3499999046325684, 0.7749999761581421]
plate_D[0].rotation = [0, 0, 0.3078760682295954]
plate_D[0].optimize = 2
artwork_A[0].position = [0.019999995827674866, 0.8500000238418579, 0.3499999940395355]
artwork_A[0].rotation = [0, 0, 4.2011643601245944e-08]
artwork_A[0].optimize = 2
glass_R[0].position = [2.690000057220459, 1.2999999523162842, 0.8100000023841858]
glass_R[0].rotation = [0, 0, 0.3078760682295954]
glass_R[0].optimize = 2
book[0].position = [2.952517032623291, 0.1941661834716797, 0.7899999618530273]
book[0].rotation = [0, 0, 0.3078760682295954]
book[0].optimize = 2
plant_J[0].position = [3.799999952316284, 3.7799999713897705, 0.1899999976158142]
plant_J[0].rotation = [0, 0, -1.262920281455031]
plant_J[0].optimize = 2
pottedplant_C[0].position = [2.390000104904175, 0.20999999344348907, 0.9699999690055847]
pottedplant_C[0].rotation = [0, 0, 1.5707965904477663]
pottedplant_C[0].optimize = 2
tree_B[0].position = [4.466508865356445, 0.5334911942481995, 0.949999988079071]
tree_B[0].rotation = [0, 0, -2.8337164997484843]
tree_B[0].optimize = 2
candletable_B[0].position = [2.6612162590026855, 2.5140268802642822, 0.8700000047683716]
candletable_B[0].rotation = [0, 0, 0.3078760682295954]
candletable_B[0].optimize = 2
plant_H[0].position = [2.8399999141693115, 3.7799999713897705, 0.1899999976158142]
plant_H[0].rotation = [0, 0, -1.262920281455031]
plant_H[0].optimize = 2
glass_A[0].position = [2.052461624145508, 1.1284809112548828, 0.824999988079071]
glass_A[0].rotation = [0, 0, 0.3078760682295954]
glass_A[0].optimize = 2
plant_A[0].position = [2.299999952316284, 1.9982224702835083, 0.9599999785423279]
plant_A[0].rotation = [0, 0, 0.3078760743562491]
plant_A[0].optimize = 2
wallplant_B[0].position = [4.910000324249268, 3.3499999046325684, 0.5]
wallplant_B[0].rotation = [0, 0, -3.141592607796071]
wallplant_B[0].optimize = 2
plant_C[0].position = [2.299999952316284, 2.6500000953674316, 0.9199999570846558]
plant_C[0].rotation = [0, 0, 0.3078760552858371]
plant_C[0].optimize = 2
glass_L[0].position = [2.6700000762939453, 1.9500000476837158, 0.824999988079071]
glass_L[0].rotation = [0, 0, 0.3078760682295954]
glass_L[0].optimize = 2
chair_E[0].position = [3.2780520915985107, 2.0, 0.42500001192092896]
chair_E[0].rotation = [0, 0, -3.125884689672577]
chair_E[0].optimize = 2
candletable_A[0].position = [1.9199999570846558, 2.7200000286102295, 0.8700000047683716]
candletable_A[0].rotation = [0, 0, 0.3078760682295954]
candletable_A[0].optimize = 2
glass_G[0].position = [2.5, 2.9200000762939453, 0.8100000023841858]
glass_G[0].rotation = [0, 0, 0.3078760682295954]
glass_G[0].optimize = 2
chair_A[0].position = [1.3770138025283813, 1.2982128858566284, 0.42500001192092896]
chair_A[0].rotation = [0, 0, 0.0157079639172164]
chair_A[0].optimize = 2
lamp_A[0].position = [0.30000001192092896, 0.3499999940395355, 0.7749999761581421]
lamp_A[0].rotation = [0, 0, 0.3078760547490114]
lamp_A[0].optimize = 2
glass_M[0].position = [1.9299999475479126, 2.0999999046325684, 0.8100000023841858]
glass_M[0].rotation = [0, 0, 0.3078760682295954]
glass_M[0].optimize = 2
plant_D[0].position = [0.9200000166893005, 3.7799999713897705, 0.1899999976158142]
plant_D[0].rotation = [0, 0, -1.262920281455031]
plant_D[0].optimize = 2
glass_I[0].position = [1.9299999475479126, 1.9500000476837158, 0.824999988079071]
glass_I[0].rotation = [0, 0, 0.3078760682295954]
glass_I[0].optimize = 2
glass_P[0].position = [2.6700000762939453, 2.0999999046325684, 0.8199999928474426]
glass_P[0].rotation = [0, 0, 0.3078760682295954]
glass_P[0].optimize = 2
chair_F[0].position = [3.2229857444763184, 2.7017855644226074, 0.42500001192092896]
chair_F[0].rotation = [0, 0, -3.125884689672577]
chair_F[0].optimize = 2
plant_G[0].position = [2.359999895095825, 3.7799999713897705, 0.1899999976158142]
plant_G[0].rotation = [0, 0, -1.262920281455031]
plant_G[0].optimize = 2
plate_B[0].position = [2.630000114440918, 1.649999976158142, 0.7749999761581421]
plate_B[0].rotation = [0, 0, 0.3078760682295954]
plate_B[0].optimize = 2
glass_O[0].position = [2.509999990463257, 2.0999999046325684, 0.8100000023841858]
glass_O[0].rotation = [0, 0, 0.3078760682295954]
glass_O[0].optimize = 2
tree_A[0].position = [0.5334911346435547, 3.4665088653564453, 0.949999988079071]
tree_A[0].rotation = [0, 0, 0.3078760547490114]
tree_A[0].optimize = 2
wallplant_A[0].position = [4.910000324249268, 0.8999999761581421, 0.5]
wallplant_A[0].rotation = [0, 0, -3.141592607796071]
wallplant_A[0].optimize = 2
plant_E[0].position = [1.399999976158142, 3.7799999713897705, 0.1599999964237213]
plant_E[0].rotation = [0, 0, -1.262920281455031]
plant_E[0].optimize = 2
glass_S[0].position = [2.6101529598236084, 2.674609661102295, 0.8149999976158142]
glass_S[0].rotation = [0, 0, 0.3078760682295954]
glass_S[0].optimize = 2
glass_E[0].position = [1.899999976158142, 2.9200000762939453, 0.8100000023841858]
glass_E[0].rotation = [0, 0, 0.3078760682295954]
glass_E[0].optimize = 2
livingplantwall[0].position = [0.09000000357627869, 3.3499999046325684, 0.6000000238418579]
livingplantwall[0].rotation = [0, 0, 4.224337799647098e-08]
livingplantwall[0].optimize = 2
chair_B[0].position = [1.321947455406189, 2.0, 0.42500001192092896]
chair_B[0].rotation = [0, 0, 0.0157079639172164]
chair_B[0].optimize = 2
plate_A[0].position = [1.9700000286102295, 1.649999976158142, 0.7749999761581421]
plate_A[0].rotation = [0, 0, 0.3078760682295954]
plate_A[0].optimize = 2
sideboard[0].position = [2.200000047683716, 0.20999999344348907, 0.38999998569488525]
sideboard[0].rotation = [0, 0, 1.5707963700862329]
sideboard[0].optimize = 2
glass_F[0].position = [2.0799999237060547, 2.9200000762939453, 0.8149999976158142]
glass_F[0].rotation = [0, 0, 0.3078760682295954]
glass_F[0].optimize = 2
glass_C[0].position = [2.5, 1.0800000429153442, 0.8100000023841858]
glass_C[0].rotation = [0, 0, 0.3078760682295954]
glass_C[0].optimize = 2
candle_B[0].position = [2.299999952316284, 2.9200000762939453, 0.8100000023841858]
candle_B[0].rotation = [0, 0, 0.3078760682295954]
candle_B[0].optimize = 2
artwork_D[0].position = [1.350000023841858, 0.015000000596046448, 0.32499998807907104]
artwork_D[0].rotation = [0, 0, 1.5707963688613091]
artwork_D[0].optimize = 2
pottedplant_D[0].position = [2.799999952316284, 0.20999999344348907, 0.9549999833106995]
pottedplant_D[0].rotation = [0, 0, 1.5707965904477663]
pottedplant_D[0].optimize = 2
glass_J[0].position = [2.0899999141693115, 1.9500000476837158, 0.8100000023841858]
glass_J[0].rotation = [0, 0, 0.3078760682295954]
glass_J[0].optimize = 2
lamp_C[0].position = [4.699999809265137, 3.6500000953674316, 0.7749999761581421]
lamp_C[0].rotation = [0, 0, -2.8337164997484843]
lamp_C[0].optimize = 2
glass_D[0].position = [2.690000057220459, 1.0800000429153442, 0.8149999976158142]
glass_D[0].rotation = [0, 0, 0.3078760682295954]
glass_D[0].optimize = 2
candle_C[0].position = [2.299999952316284, 1.6699999570846558, 0.8500000238418579]
candle_C[0].rotation = [0, 0, 0.3078760682295954]
candle_C[0].optimize = 2
glass_H[0].position = [2.5466198921203613, 2.8744070529937744, 0.824999988079071]
glass_H[0].rotation = [0, 0, 0.3078760682295954]
glass_H[0].optimize = 2
candletable_C[0].position = [1.9387836456298828, 1.4859730005264282, 0.8700000047683716]
candletable_C[0].rotation = [0, 0, 0.3078760682295954]
candletable_C[0].optimize = 2
pottedplant_B[0].position = [2.0, 0.20999999344348907, 0.9699999690055847]
pottedplant_B[0].rotation = [0, 0, 1.5707965904477663]
pottedplant_B[0].optimize = 2
artwork_B[0].position = [0.019999995827674866, 1.600000023841858, 0.30000001192092896]
artwork_B[0].rotation = [0, 0, 4.2050822724751076e-08]
artwork_B[0].optimize = 2
glass_N[0].position = [2.0899999141693115, 2.0999999046325684, 0.8100000023841858]
glass_N[0].rotation = [0, 0, 0.3078760682295954]
glass_N[0].optimize = 2
glass_Q[0].position = [1.9889286756515503, 1.3282781839370728, 0.8100000023841858]
glass_Q[0].rotation = [0, 0, 0.3078760682295954]
glass_Q[0].optimize = 2
chair_D[0].position = [3.2229857444763184, 1.2982128858566284, 0.42500001192092896]
chair_D[0].rotation = [0, 0, -3.125884689672577]
chair_D[0].optimize = 2
glass_B[0].position = [2.0799999237060547, 1.0800000429153442, 0.8100000023841858]
glass_B[0].rotation = [0, 0, 0.3078760682295954]
glass_B[0].optimize = 2
artwork_F[0].position = [3.0999999046325684, 0.019999997690320015, 0.3499999940395355]
artwork_F[0].rotation = [0, 0, 1.5707963688065403]
artwork_F[0].optimize = 2

