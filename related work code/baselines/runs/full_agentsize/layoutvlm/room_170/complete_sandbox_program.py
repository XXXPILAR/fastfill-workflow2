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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.20, 0.00, 0.00]),
    Wall(corner1=[3.20, 0.00, 0.00], corner2=[3.20, 4.00, 0.00]),
    Wall(corner1=[3.20, 4.00, 0.00], corner2=[0.00, 4.00, 0.00]),
    Wall(corner1=[0.00, 4.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bottle_A = Assets(description="A hand‑blown glass bottle with iridescent swirls, rounded cylindrical form, translucent pastel hues and a delicate organic curve, showcasing a subtle ripple pattern", size=[0.12, 0.12, 0.28], placements=[AssetInstance() for _ in range(1)])
toothbrush_A = Assets(description="A bamboo-handled toothbrush with biophilic style, slender cylindrical shape, natural wood color and smooth rounded tip", size=[0.02, 0.02, 0.19], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="A wall‑mounted brass lamp with a warm brass finish, slim rectangular profile, gentle upward curve of the shade and a subtle biophilic pattern etched on the metal", size=[0.18, 0.16, 0.42], placements=[AssetInstance() for _ in range(1)])
decorativebottle_A = Assets(description="A textured glass decorative bottle, square‑ish body with subtle ridged surface, matte frosted finish", size=[0.11, 0.14, 0.24], placements=[AssetInstance() for _ in range(1)])
ornament_A = Assets(description="A decorative textured glass bottle with a matte stone‑like finish, squat cylindrical body, slightly rough surface and a rounded base", size=[0.16, 0.16, 0.20], placements=[AssetInstance() for _ in range(1)])
candle_A = Assets(description="A natural soy scented candle in a simple cylindrical container, matte ivory color, with a rounded top and a faint wooden lid detail", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
wastebin_A = Assets(description="A rectangular recycled‑metal waste bin with a brushed finish, clean lines and a subtle curved lid, biophilic style", size=[0.22, 0.28, 0.40], placements=[AssetInstance() for _ in range(1)])
soapdispenser_A = Assets(description="A recycled glass soap dispenser with a smooth cylindrical body, clear translucent finish and subtle organic curves, thin rim at the top", size=[0.09, 0.09, 0.21], placements=[AssetInstance() for _ in range(1)])
towelrack_A = Assets(description="A wood‑finished towel rack with two vertical natural‑finish bars, sleek straight‑edged design", size=[0.12, 0.65, 0.90], placements=[AssetInstance() for _ in range(1)])
candle_B = Assets(description="A natural soy scented candle in a simple cylindrical container, matte ivory color, with a rounded top and a faint wooden lid detail", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
candle_C = Assets(description="A natural soy scented candle in a simple cylindrical container, matte ivory color, with a rounded top and a faint wooden lid detail", size=[0.08, 0.08, 0.10], placements=[AssetInstance() for _ in range(1)])
candle_D = Assets(description="A soy scented candle with a smooth cylindrical shape, soft ivory color, natural soy wax finish and subtle biophilic texture, featuring a tiny leaf imprint on its surface", size=[0.09, 0.09, 0.12], placements=[AssetInstance() for _ in range(1)])
plant_A = Assets(description="A living‑wall plant in mossy green, compact vertical foliage, soft textured leaves, natural organic form", size=[0.12, 0.50, 0.80], placements=[AssetInstance() for _ in range(1)])
vanity = Assets(description="A reclaimed‑wood vanity unit with a low rectangular top, natural grain finish, sturdy legs, warm brown tones", size=[0.55, 1.45, 0.82], placements=[AssetInstance() for _ in range(1)])
decorativebottle_B = Assets(description="A hand‑blown decorative glass bottle, rounded cylindrical silhouette, iridescent swirl pattern, translucent pastel tones and a delicate organic neck curve", size=[0.13, 0.13, 0.30], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="A wall‑mounted brass lamp with a warm brass cylindrical shade, slender stem, polished finish", size=[0.22, 0.18, 0.38], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="A hand‑blown glass bottle with iridescent finish, rounded body tapering to a narrow neck, shimmering rainbow hues", size=[0.14, 0.14, 0.29], placements=[AssetInstance() for _ in range(1)])
candle_E = Assets(description="A soy scented candle in a smooth cylindrical container, natural beige wax, subtle wooden lid", size=[0.10, 0.10, 0.12], placements=[AssetInstance() for _ in range(1)])
ornament_B = Assets(description="A decorative textured glass bottle with a matte stone‑like finish, squat cylindrical body, slightly rough surface and a rounded base", size=[0.15, 0.15, 0.19], placements=[AssetInstance() for _ in range(1)])
soapdispenser_B = Assets(description="A glass soap dispenser made from recycled glass, slender rectangular bottle, clear with subtle frosted accents", size=[0.07, 0.08, 0.22], placements=[AssetInstance() for _ in range(1)])
soapdispenser_C = Assets(description="A glass soap dispenser made from recycled glass, sleek cylindrical shape, clear subtle frosted accents and a gentle tapered neck, with a soft biophilic curve", size=[0.08, 0.08, 0.23], placements=[AssetInstance() for _ in range(1)])
candle_F = Assets(description="A natural‑wax soy scented candle, smooth cylindrical form, creamy white surface with a faint matte finish", size=[0.08, 0.08, 0.11], placements=[AssetInstance() for _ in range(1)])
candle_G = Assets(description="A soy scented candle in a smooth cylindrical container, natural beige wax, subtle wooden lid", size=[0.10, 0.10, 0.12], placements=[AssetInstance() for _ in range(1)])
candle_H = Assets(description="A natural soy scented candle in a simple cylindrical container, matte ivory color, with a rounded top and a faint wooden lid detail", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
candle_I = Assets(description="A natural‑wax soy scented candle, smooth cylindrical form, creamy white surface with a faint matte finish", size=[0.08, 0.08, 0.10], placements=[AssetInstance() for _ in range(1)])
sink = Assets(description="A stone countertop sink with a wide oval basin, thick natural stone slab, matte earthy tones, subtle veining", size=[0.62, 1.20, 0.86], placements=[AssetInstance() for _ in range(1)])
candle_J = Assets(description="A natural soy scented candle in a simple cylindrical container, matte ivory color, with a rounded top and a faint wooden lid detail", size=[0.08, 0.08, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_B = Assets(description="A small potted plant with mossy green foliage, round pot of natural clay, low‑lying compact leaves and a gentle dome shape", size=[0.24, 0.24, 0.28], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="A floating wooden shelf with a minimalist slim profile, straight‑edged rectangular board, natural finish", size=[0.28, 1.80, 0.06], placements=[AssetInstance() for _ in range(1)])
bottle_C = Assets(description="A hand‑blown decorative glass bottle with a slender elongated shape, clear with subtle iridescent swirl", size=[0.10, 0.10, 0.34], placements=[AssetInstance() for _ in range(1)])
bottle_D = Assets(description="A hand‑blown glass bottle with iridescent finish, rounded body tapering to a narrow neck, shimmering rainbow hues", size=[0.14, 0.14, 0.29], placements=[AssetInstance() for _ in range(1)])
toothbrush_B = Assets(description="A bamboo-handled toothbrush with a gently curved head and natural wood grain finish, featuring soft bristles and an ergonomic slender shape", size=[0.02, 0.02, 0.20], placements=[AssetInstance() for _ in range(1)])
candle_K = Assets(description="A soy scented candle with a smooth cylindrical shape, soft ivory color, natural soy wax finish and subtle biophilic texture, featuring a tiny leaf imprint on its surface", size=[0.09, 0.09, 0.12], placements=[AssetInstance() for _ in range(1)])
towel_A = Assets(description="A soft white towel made of organic cotton, flat rectangular shape, plush texture and a subtle woven grain, with a gentle rolled edge", size=[0.07, 0.65, 0.90], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="A floating wooden shelf with a minimalist slim profile, straight‑edged rectangular board, natural finish", size=[0.26, 1.40, 0.06], placements=[AssetInstance() for _ in range(1)])
candle_L = Assets(description="A soy scented candle with a smooth cylindrical shape, soft ivory color, natural soy wax finish and subtle biophilic texture, featuring a tiny leaf imprint on its surface", size=[0.09, 0.09, 0.12], placements=[AssetInstance() for _ in range(1)])
bottle_E = Assets(description="A hand‑blown glass bottle with an iridescent surface, elegant elongated shape, gently flared mouth and a subtle curved silhouette", size=[0.11, 0.11, 0.36], placements=[AssetInstance() for _ in range(1)])
bottle_F = Assets(description="A hand‑blown glass bottle with an iridescent surface, elegant elongated shape, gently flared mouth and a subtle curved silhouette", size=[0.11, 0.11, 0.36], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="A low storage cabinet with a stone base and wooden upper panels, rectangular footprint, textured stone lower half", size=[0.48, 1.55, 0.80], placements=[AssetInstance() for _ in range(1)])
mirror = Assets(description="A single piece of thin and upright large rectangular mirror, frameless, clear reflective surface", size=[0.03, 0.90, 1.70], placements=[AssetInstance() for _ in range(1)])
bottle_G = Assets(description="A hand‑blown glass bottle with an iridescent surface, elegant elongated shape, gently flared mouth and a subtle curved silhouette", size=[0.11, 0.11, 0.36], placements=[AssetInstance() for _ in range(1)])
candle_M = Assets(description="A natural‑wax soy scented candle, smooth cylindrical form, creamy white surface with a faint matte finish", size=[0.08, 0.08, 0.11], placements=[AssetInstance() for _ in range(1)])
candle_N = Assets(description="A natural soy scented candle in a simple cylindrical container, matte ivory color, with a rounded top and a faint wooden lid detail", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
decorativebottle_C = Assets(description="A hand‑blown decorative glass bottle, rounded cylindrical silhouette, iridescent swirl pattern, translucent pastel tones and a delicate organic neck curve", size=[0.13, 0.13, 0.30], placements=[AssetInstance() for _ in range(1)])
soapdispenser_D = Assets(description="A glass soap dispenser made from recycled glass, clear cylindrical body with a subtle green tint and a sleek brushed metal pump", size=[0.09, 0.09, 0.23], placements=[AssetInstance() for _ in range(1)])
candle_O = Assets(description="A soy scented candle in a smooth cylindrical container, natural beige wax, subtle wooden lid", size=[0.10, 0.10, 0.12], placements=[AssetInstance() for _ in range(1)])
lamp_C = Assets(description="A wall‑mounted brass lamp with a warm brass finish, slim rectangular profile, gentle upward curve of the shade and a subtle biophilic pattern etched on the metal", size=[0.18, 0.16, 0.42], placements=[AssetInstance() for _ in range(1)])
plant_C = Assets(description="A compact potted plant with dense foliage, earthy terracotta pot, rounded leaf clusters and a sturdy, low‑profile silhouette", size=[0.45, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])
candle_P = Assets(description="A natural soy scented candle in a simple cylindrical container, matte ivory color, with a rounded top and a faint wooden lid detail", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
bottle_H = Assets(description="A hand‑blown glass bottle with iridescent finish, rounded body tapering to a narrow neck, shimmering rainbow hues", size=[0.14, 0.14, 0.29], placements=[AssetInstance() for _ in range(1)])
toilet = Assets(description="A sleek ceramic toilet with a smooth rounded bowl and a low‑profile rectangular base, glossy white finish, organic lines", size=[0.70, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
ornament_C = Assets(description="A decorative textured glass bottle with a matte stone‑like finish, squat cylindrical body, slightly rough surface and a rounded base", size=[0.15, 0.15, 0.19], placements=[AssetInstance() for _ in range(1)])
toothbrushholder = Assets(description="A ceramic toothbrush holder with an earthy tone glaze, low rectangular cup, slightly rounded edges", size=[0.09, 0.13, 0.12], placements=[AssetInstance() for _ in range(1)])
tub = Assets(description="A freestanding stone tub formed from stacked river stones, organic curved silhouette, textured surface, natural grey‑green hue", size=[0.95, 1.85, 0.68], placements=[AssetInstance() for _ in range(1)])
toothbrush_C = Assets(description="A ceramic toothbrush holder with a low‑slung rectangular base, earthy tone glaze, smooth matte finish and a subtle organic groove on its front", size=[0.08, 0.14, 0.10], placements=[AssetInstance() for _ in range(1)])
shower = Assets(description="A glass‑enclosed shower with transparent rectangular panels, thin frameless edges, smooth clear glass", size=[1.00, 1.10, 2.20], placements=[AssetInstance() for _ in range(1)])
towelrack_B = Assets(description="A wood‑finished towel rack with two vertical natural‑finish bars, sleek straight‑edged design", size=[0.12, 0.65, 0.90], placements=[AssetInstance() for _ in range(1)])
wastebin_B = Assets(description="A small recycled‑metal waste bin with a smooth cylindrical body, brushed steel finish and a subtle tapered top, minimalist silhouette", size=[0.25, 0.25, 0.35], placements=[AssetInstance() for _ in range(1)])
bottle_I = Assets(description="A hand‑blown decorative glass bottle with a slender elongated shape, clear with subtle iridescent swirl", size=[0.10, 0.10, 0.34], placements=[AssetInstance() for _ in range(1)])
toothbrush_D = Assets(description="A bamboo-handled toothbrush with a gently curved head and natural wood grain finish, featuring soft bristles and an ergonomic slender shape", size=[0.02, 0.02, 0.20], placements=[AssetInstance() for _ in range(1)])
bottle_J = Assets(description="A hand‑blown glass bottle with iridescent swirls, rounded cylindrical form, translucent pastel hues and a delicate organic curve, showcasing a subtle ripple pattern", size=[0.12, 0.12, 0.28], placements=[AssetInstance() for _ in range(1)])
toothbrush_E = Assets(description="A bamboo-handled toothbrush with biophilic style, slender cylindrical shape, natural wood color and smooth rounded tip", size=[0.02, 0.02, 0.19], placements=[AssetInstance() for _ in range(1)])
plant_D = Assets(description="A living‑wall plant in mossy green, compact vertical foliage, soft textured leaves, natural organic form", size=[0.12, 0.50, 0.80], placements=[AssetInstance() for _ in range(1)])
lamp_D = Assets(description="A wall‑mounted brass lamp with a warm brass cylindrical shade, slender stem, polished finish", size=[0.22, 0.18, 0.38], placements=[AssetInstance() for _ in range(1)])
livingplant = Assets(description="A living wall plant with compact foliage, vertical growth habit, deep green leaves and a slender, elongated pot that hugs the wall", size=[0.32, 0.38, 1.45], placements=[AssetInstance() for _ in range(1)])
bottle_K = Assets(description="A hand‑blown glass bottle with iridescent finish, rounded body tapering to a narrow neck, shimmering rainbow hues", size=[0.14, 0.14, 0.29], placements=[AssetInstance() for _ in range(1)])
decorativebottle_D = Assets(description="A textured glass decorative bottle, square‑ish body with subtle ridged surface, matte frosted finish", size=[0.11, 0.14, 0.24], placements=[AssetInstance() for _ in range(1)])
towel_B = Assets(description="A soft white towel made of organic cotton, flat rectangular shape, plush texture and a subtle woven grain, with a gentle rolled edge", size=[0.07, 0.65, 0.90], placements=[AssetInstance() for _ in range(1)])

bottle_A[0].instance_id = 'bottle_A_0'
toothbrush_A[0].instance_id = 'toothbrush_A_0'
lamp_A[0].instance_id = 'lamp_A_0'
decorativebottle_A[0].instance_id = 'decorativebottle_A_0'
ornament_A[0].instance_id = 'ornament_A_0'
candle_A[0].instance_id = 'candle_A_0'
wastebin_A[0].instance_id = 'wastebin_A_0'
soapdispenser_A[0].instance_id = 'soapdispenser_A_0'
towelrack_A[0].instance_id = 'towelrack_A_0'
candle_B[0].instance_id = 'candle_B_0'
candle_C[0].instance_id = 'candle_C_0'
candle_D[0].instance_id = 'candle_D_0'
plant_A[0].instance_id = 'plant_A_0'
vanity[0].instance_id = 'vanity_0'
decorativebottle_B[0].instance_id = 'decorativebottle_B_0'
lamp_B[0].instance_id = 'lamp_B_0'
bottle_B[0].instance_id = 'bottle_B_0'
candle_E[0].instance_id = 'candle_E_0'
ornament_B[0].instance_id = 'ornament_B_0'
soapdispenser_B[0].instance_id = 'soapdispenser_B_0'
soapdispenser_C[0].instance_id = 'soapdispenser_C_0'
candle_F[0].instance_id = 'candle_F_0'
candle_G[0].instance_id = 'candle_G_0'
candle_H[0].instance_id = 'candle_H_0'
candle_I[0].instance_id = 'candle_I_0'
sink[0].instance_id = 'sink_0'
candle_J[0].instance_id = 'candle_J_0'
plant_B[0].instance_id = 'plant_B_0'
shelf_A[0].instance_id = 'shelf_A_0'
bottle_C[0].instance_id = 'bottle_C_0'
bottle_D[0].instance_id = 'bottle_D_0'
toothbrush_B[0].instance_id = 'toothbrush_B_0'
candle_K[0].instance_id = 'candle_K_0'
towel_A[0].instance_id = 'towel_A_0'
shelf_B[0].instance_id = 'shelf_B_0'
candle_L[0].instance_id = 'candle_L_0'
bottle_E[0].instance_id = 'bottle_E_0'
bottle_F[0].instance_id = 'bottle_F_0'
cabinet[0].instance_id = 'cabinet_0'
mirror[0].instance_id = 'mirror_0'
bottle_G[0].instance_id = 'bottle_G_0'
candle_M[0].instance_id = 'candle_M_0'
candle_N[0].instance_id = 'candle_N_0'
decorativebottle_C[0].instance_id = 'decorativebottle_C_0'
soapdispenser_D[0].instance_id = 'soapdispenser_D_0'
candle_O[0].instance_id = 'candle_O_0'
lamp_C[0].instance_id = 'lamp_C_0'
plant_C[0].instance_id = 'plant_C_0'
candle_P[0].instance_id = 'candle_P_0'
bottle_H[0].instance_id = 'bottle_H_0'
toilet[0].instance_id = 'toilet_0'
ornament_C[0].instance_id = 'ornament_C_0'
toothbrushholder[0].instance_id = 'toothbrushholder_0'
tub[0].instance_id = 'tub_0'
toothbrush_C[0].instance_id = 'toothbrush_C_0'
shower[0].instance_id = 'shower_0'
towelrack_B[0].instance_id = 'towelrack_B_0'
wastebin_B[0].instance_id = 'wastebin_B_0'
bottle_I[0].instance_id = 'bottle_I_0'
toothbrush_D[0].instance_id = 'toothbrush_D_0'
bottle_J[0].instance_id = 'bottle_J_0'
toothbrush_E[0].instance_id = 'toothbrush_E_0'
plant_D[0].instance_id = 'plant_D_0'
lamp_D[0].instance_id = 'lamp_D_0'
livingplant[0].instance_id = 'livingplant_0'
bottle_K[0].instance_id = 'bottle_K_0'
decorativebottle_D[0].instance_id = 'decorativebottle_D_0'
towel_B[0].instance_id = 'towel_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

bottle_A[0].position = [3.17319474394459, 0.4961680487663487, 0.14]
bottle_A[0].rotation = [0, 0, 0]
toothbrush_A[0].position = [1.8898975100501216, 0.9162024591980371, 0.095]
toothbrush_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [0.950340067176121, 0.5030007778551044, 0.21]
lamp_A[0].rotation = [0, 0, 0]
decorativebottle_A[0].position = [2.8030058575997474, 0.9889423598990983, 0.12]
decorativebottle_A[0].rotation = [0, 0, 0]
ornament_A[0].position = [0.702784245672373, 2.287237402240657, 0.1]
ornament_A[0].rotation = [0, 0, 0]
candle_A[0].position = [1.7575847039145083, 3.9775675317819825, 0.055]
candle_A[0].rotation = [0, 0, 0]
wastebin_A[0].position = [2.5627523533043703, 3.1191894423394273, 0.2]
wastebin_A[0].rotation = [0, 0, 0]
soapdispenser_A[0].position = [1.2980538652127174, 3.087977001054157, 0.105]
soapdispenser_A[0].rotation = [0, 0, 0]
towelrack_A[0].position = [1.045976191635195, 1.4608277934028377, 0.45]
towelrack_A[0].rotation = [0, 0, 0]
candle_B[0].position = [1.6340523994985, 0.558119267994194, 0.055]
candle_B[0].rotation = [0, 0, 0]
candle_C[0].position = [3.1478612502709926, 2.319334977804506, 0.05]
candle_C[0].rotation = [0, 0, 0]
candle_D[0].position = [1.1643760836627526, 2.6906611989226086, 0.06]
candle_D[0].rotation = [0, 0, 0]
plant_A[0].position = [2.298792720546154, 3.188290487399201, 0.4]
plant_A[0].rotation = [0, 0, 0]
vanity[0].position = [1.2978923311166444, 3.5675822767404792, 0.41]
vanity[0].rotation = [0, 0, 0]
decorativebottle_B[0].position = [0.8462828565053901, 3.5274987577470966, 0.15]
decorativebottle_B[0].rotation = [0, 0, 0]
lamp_B[0].position = [2.2193629330251925, 1.5886256824442477, 0.19]
lamp_B[0].rotation = [0, 0, 0]
bottle_B[0].position = [2.122125675969592, 2.5395922537945257, 0.145]
bottle_B[0].rotation = [0, 0, 0]
candle_E[0].position = [1.0125347887393727, 3.506300533395104, 0.06]
candle_E[0].rotation = [0, 0, 0]
ornament_B[0].position = [0.9044056237546972, 1.1844029783695054, 0.095]
ornament_B[0].rotation = [0, 0, 0]
soapdispenser_B[0].position = [1.564878786023404, 3.577935085348185, 0.11]
soapdispenser_B[0].rotation = [0, 0, 0]
soapdispenser_C[0].position = [0.34080751483768135, 0.3317214196190532, 0.115]
soapdispenser_C[0].rotation = [0, 0, 0]
candle_F[0].position = [0.983212963628493, 2.0987235736819003, 0.055]
candle_F[0].rotation = [0, 0, 0]
candle_G[0].position = [2.6081984799767315, 2.78477920728759, 0.06]
candle_G[0].rotation = [0, 0, 0]
candle_H[0].position = [1.1065159988172704, 2.015959203469206, 0.055]
candle_H[0].rotation = [0, 0, 0]
candle_I[0].position = [1.386001765584985, 2.134927967280906, 0.05]
candle_I[0].rotation = [0, 0, 0]
sink[0].position = [1.204364858003141, 3.9910269366166036, 0.43]
sink[0].rotation = [0, 0, 0]
candle_J[0].position = [2.858117532073864, 0.26427667996156234, 0.05]
candle_J[0].rotation = [0, 0, 0]
plant_B[0].position = [0.06838289147293004, 2.9469430879300136, 0.14]
plant_B[0].rotation = [0, 0, 0]
shelf_A[0].position = [2.3359614505010327, 3.15705746818722, 0.03]
shelf_A[0].rotation = [0, 0, 0]
bottle_C[0].position = [2.0232142565889006, 3.5064246524387404, 0.17]
bottle_C[0].rotation = [0, 0, 0]
bottle_D[0].position = [2.9711708161423136, 0.8277662952392464, 0.145]
bottle_D[0].rotation = [0, 0, 0]
toothbrush_B[0].position = [0.1236850260326289, 0.724949157929796, 0.1]
toothbrush_B[0].rotation = [0, 0, 0]
candle_K[0].position = [0.17413677092192226, 1.9965567790572747, 0.06]
candle_K[0].rotation = [0, 0, 0]
towel_A[0].position = [0.293560894668914, 3.7763463519933014, 0.45]
towel_A[0].rotation = [0, 0, 0]
shelf_B[0].position = [0.4466361790265605, 2.3747693685328333, 0.03]
shelf_B[0].rotation = [0, 0, 0]
candle_L[0].position = [2.9275923117479037, 2.8545119428086103, 0.06]
candle_L[0].rotation = [0, 0, 0]
bottle_E[0].position = [0.9897495608186017, 1.139963676414935, 0.18]
bottle_E[0].rotation = [0, 0, 0]
bottle_F[0].position = [2.737320477082496, 0.40457685985183467, 0.18]
bottle_F[0].rotation = [0, 0, 0]
cabinet[0].position = [2.9340515838837025, 1.600202443160211, 0.4]
cabinet[0].rotation = [0, 0, 0]
mirror[0].position = [1.4819586847750015, 2.5131157609628247, 0.85]
mirror[0].rotation = [0, 0, 0]
bottle_G[0].position = [1.1045386496710787, 2.517663770353313, 0.18]
bottle_G[0].rotation = [0, 0, 0]
candle_M[0].position = [2.1269790562141053, 0.9742235433336992, 0.055]
candle_M[0].rotation = [0, 0, 0]
candle_N[0].position = [2.856355442962926, 3.4854949579226933, 0.055]
candle_N[0].rotation = [0, 0, 0]
decorativebottle_C[0].position = [1.2010287400684352, 2.501353189656075, 0.15]
decorativebottle_C[0].rotation = [0, 0, 0]
soapdispenser_D[0].position = [0.5502400791765968, 1.7000415781601514, 0.115]
soapdispenser_D[0].rotation = [0, 0, 0]
candle_O[0].position = [2.9054605747893945, 3.5368110303120877, 0.06]
candle_O[0].rotation = [0, 0, 0]
lamp_C[0].position = [0.400698747490506, 0.6098659951899346, 0.21]
lamp_C[0].rotation = [0, 0, 0]
plant_C[0].position = [0.48367881585654615, 0.27047082407030354, 0.3]
plant_C[0].rotation = [0, 0, 0]
candle_P[0].position = [1.959985438980279, 1.7677209254775632, 0.055]
candle_P[0].rotation = [0, 0, 0]
bottle_H[0].position = [1.7755285169232629, 2.232209247778829, 0.145]
bottle_H[0].rotation = [0, 0, 0]
toilet[0].position = [1.632556822458582, 3.3917137455311575, 0.39]
toilet[0].rotation = [0, 0, 0]
ornament_C[0].position = [2.018853270085511, 3.985837814319624, 0.095]
ornament_C[0].rotation = [0, 0, 0]
toothbrushholder[0].position = [2.692556789352816, 2.966084166651652, 0.06]
toothbrushholder[0].rotation = [0, 0, 0]
tub[0].position = [2.539139455340732, 0.04921984119010814, 0.34]
tub[0].rotation = [0, 0, 0]
toothbrush_C[0].position = [0.954262638067117, 1.6607164350867545, 0.05]
toothbrush_C[0].rotation = [0, 0, 0]
shower[0].position = [2.40933663147398, 2.2267581633136815, 1.1]
shower[0].rotation = [0, 0, 0]
towelrack_B[0].position = [2.578385087893749, 3.138970559156127, 0.45]
towelrack_B[0].rotation = [0, 0, 0]
wastebin_B[0].position = [3.1129188974759723, 3.5350027317088983, 0.175]
wastebin_B[0].rotation = [0, 0, 0]
bottle_I[0].position = [1.0675287559119877, 3.348901684461282, 0.17]
bottle_I[0].rotation = [0, 0, 0]
toothbrush_D[0].position = [0.5607297856821827, 2.833671836362195, 0.1]
toothbrush_D[0].rotation = [0, 0, 0]
bottle_J[0].position = [2.5874943477084322, 3.2340475305042182, 0.14]
bottle_J[0].rotation = [0, 0, 0]
toothbrush_E[0].position = [0.35285788611403, 1.5902615396545534, 0.095]
toothbrush_E[0].rotation = [0, 0, 0]
plant_D[0].position = [0.46847423813783706, 3.910620012243164, 0.4]
plant_D[0].rotation = [0, 0, 0]
lamp_D[0].position = [0.7457805795362941, 0.9598217483703269, 0.19]
lamp_D[0].rotation = [0, 0, 0]
livingplant[0].position = [1.065615581950343, 2.441357875959051, 0.725]
livingplant[0].rotation = [0, 0, 0]
bottle_K[0].position = [1.0979421841687202, 2.109641829462941, 0.145]
bottle_K[0].rotation = [0, 0, 0]
decorativebottle_D[0].position = [2.5099792809594836, 0.6343088913406638, 0.12]
decorativebottle_D[0].rotation = [0, 0, 0]
towel_B[0].position = [1.460007919902532, 0.33548188511945876, 0.45]
towel_B[0].rotation = [0, 0, 0]
bottle_A[0].position = [3.17319474394459, 0.4961680487663487, 0.14]
bottle_A[0].rotation = [0, 0, 0]
toothbrush_A[0].position = [1.8898975100501216, 0.9162024591980371, 0.095]
toothbrush_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [0.950340067176121, 0.5030007778551044, 0.21]
lamp_A[0].rotation = [0, 0, 0]
decorativebottle_A[0].position = [2.8030058575997474, 0.9889423598990983, 0.12]
decorativebottle_A[0].rotation = [0, 0, 0]
ornament_A[0].position = [0.702784245672373, 2.287237402240657, 0.1]
ornament_A[0].rotation = [0, 0, 0]
candle_A[0].position = [1.7575847039145083, 3.9775675317819825, 0.055]
candle_A[0].rotation = [0, 0, 0]
wastebin_A[0].position = [2.5627523533043703, 3.1191894423394273, 0.2]
wastebin_A[0].rotation = [0, 0, 0]
soapdispenser_A[0].position = [1.2980538652127174, 3.087977001054157, 0.105]
soapdispenser_A[0].rotation = [0, 0, 0]
towelrack_A[0].position = [1.045976191635195, 1.4608277934028377, 0.45]
towelrack_A[0].rotation = [0, 0, 0]
candle_B[0].position = [1.6340523994985, 0.558119267994194, 0.055]
candle_B[0].rotation = [0, 0, 0]
candle_C[0].position = [3.1478612502709926, 2.319334977804506, 0.05]
candle_C[0].rotation = [0, 0, 0]
candle_D[0].position = [1.1643760836627526, 2.6906611989226086, 0.06]
candle_D[0].rotation = [0, 0, 0]
plant_A[0].position = [2.298792720546154, 3.188290487399201, 0.4]
plant_A[0].rotation = [0, 0, 0]
vanity[0].position = [1.2978923311166444, 3.5675822767404792, 0.41]
vanity[0].rotation = [0, 0, 0]
decorativebottle_B[0].position = [0.8462828565053901, 3.5274987577470966, 0.15]
decorativebottle_B[0].rotation = [0, 0, 0]
lamp_B[0].position = [2.2193629330251925, 1.5886256824442477, 0.19]
lamp_B[0].rotation = [0, 0, 0]
bottle_B[0].position = [2.122125675969592, 2.5395922537945257, 0.145]
bottle_B[0].rotation = [0, 0, 0]
candle_E[0].position = [1.0125347887393727, 3.506300533395104, 0.06]
candle_E[0].rotation = [0, 0, 0]
ornament_B[0].position = [0.9044056237546972, 1.1844029783695054, 0.095]
ornament_B[0].rotation = [0, 0, 0]
soapdispenser_B[0].position = [1.564878786023404, 3.577935085348185, 0.11]
soapdispenser_B[0].rotation = [0, 0, 0]
soapdispenser_C[0].position = [0.34080751483768135, 0.3317214196190532, 0.115]
soapdispenser_C[0].rotation = [0, 0, 0]
candle_F[0].position = [0.983212963628493, 2.0987235736819003, 0.055]
candle_F[0].rotation = [0, 0, 0]
candle_G[0].position = [2.6081984799767315, 2.78477920728759, 0.06]
candle_G[0].rotation = [0, 0, 0]
candle_H[0].position = [1.1065159988172704, 2.015959203469206, 0.055]
candle_H[0].rotation = [0, 0, 0]
candle_I[0].position = [1.386001765584985, 2.134927967280906, 0.05]
candle_I[0].rotation = [0, 0, 0]
sink[0].position = [1.204364858003141, 3.9910269366166036, 0.43]
sink[0].rotation = [0, 0, 0]
candle_J[0].position = [2.858117532073864, 0.26427667996156234, 0.05]
candle_J[0].rotation = [0, 0, 0]
plant_B[0].position = [0.06838289147293004, 2.9469430879300136, 0.14]
plant_B[0].rotation = [0, 0, 0]
shelf_A[0].position = [2.3359614505010327, 3.15705746818722, 0.03]
shelf_A[0].rotation = [0, 0, 0]
bottle_C[0].position = [2.0232142565889006, 3.5064246524387404, 0.17]
bottle_C[0].rotation = [0, 0, 0]
bottle_D[0].position = [2.9711708161423136, 0.8277662952392464, 0.145]
bottle_D[0].rotation = [0, 0, 0]
toothbrush_B[0].position = [0.1236850260326289, 0.724949157929796, 0.1]
toothbrush_B[0].rotation = [0, 0, 0]
candle_K[0].position = [0.17413677092192226, 1.9965567790572747, 0.06]
candle_K[0].rotation = [0, 0, 0]
towel_A[0].position = [0.293560894668914, 3.7763463519933014, 0.45]
towel_A[0].rotation = [0, 0, 0]
shelf_B[0].position = [0.4466361790265605, 2.3747693685328333, 0.03]
shelf_B[0].rotation = [0, 0, 0]
candle_L[0].position = [2.9275923117479037, 2.8545119428086103, 0.06]
candle_L[0].rotation = [0, 0, 0]
bottle_E[0].position = [0.9897495608186017, 1.139963676414935, 0.18]
bottle_E[0].rotation = [0, 0, 0]
bottle_F[0].position = [2.737320477082496, 0.40457685985183467, 0.18]
bottle_F[0].rotation = [0, 0, 0]
cabinet[0].position = [2.9340515838837025, 1.600202443160211, 0.4]
cabinet[0].rotation = [0, 0, 0]
mirror[0].position = [1.4819586847750015, 2.5131157609628247, 0.85]
mirror[0].rotation = [0, 0, 0]
bottle_G[0].position = [1.1045386496710787, 2.517663770353313, 0.18]
bottle_G[0].rotation = [0, 0, 0]
candle_M[0].position = [2.1269790562141053, 0.9742235433336992, 0.055]
candle_M[0].rotation = [0, 0, 0]
candle_N[0].position = [2.856355442962926, 3.4854949579226933, 0.055]
candle_N[0].rotation = [0, 0, 0]
decorativebottle_C[0].position = [1.2010287400684352, 2.501353189656075, 0.15]
decorativebottle_C[0].rotation = [0, 0, 0]
soapdispenser_D[0].position = [0.5502400791765968, 1.7000415781601514, 0.115]
soapdispenser_D[0].rotation = [0, 0, 0]
candle_O[0].position = [2.9054605747893945, 3.5368110303120877, 0.06]
candle_O[0].rotation = [0, 0, 0]
lamp_C[0].position = [0.400698747490506, 0.6098659951899346, 0.21]
lamp_C[0].rotation = [0, 0, 0]
plant_C[0].position = [0.48367881585654615, 0.27047082407030354, 0.3]
plant_C[0].rotation = [0, 0, 0]
candle_P[0].position = [1.959985438980279, 1.7677209254775632, 0.055]
candle_P[0].rotation = [0, 0, 0]
bottle_H[0].position = [1.7755285169232629, 2.232209247778829, 0.145]
bottle_H[0].rotation = [0, 0, 0]
toilet[0].position = [1.632556822458582, 3.3917137455311575, 0.39]
toilet[0].rotation = [0, 0, 0]
ornament_C[0].position = [2.018853270085511, 3.985837814319624, 0.095]
ornament_C[0].rotation = [0, 0, 0]
toothbrushholder[0].position = [2.692556789352816, 2.966084166651652, 0.06]
toothbrushholder[0].rotation = [0, 0, 0]
tub[0].position = [2.539139455340732, 0.04921984119010814, 0.34]
tub[0].rotation = [0, 0, 0]
toothbrush_C[0].position = [0.954262638067117, 1.6607164350867545, 0.05]
toothbrush_C[0].rotation = [0, 0, 0]
shower[0].position = [2.40933663147398, 2.2267581633136815, 1.1]
shower[0].rotation = [0, 0, 0]
towelrack_B[0].position = [2.578385087893749, 3.138970559156127, 0.45]
towelrack_B[0].rotation = [0, 0, 0]
wastebin_B[0].position = [3.1129188974759723, 3.5350027317088983, 0.175]
wastebin_B[0].rotation = [0, 0, 0]
bottle_I[0].position = [1.0675287559119877, 3.348901684461282, 0.17]
bottle_I[0].rotation = [0, 0, 0]
toothbrush_D[0].position = [0.5607297856821827, 2.833671836362195, 0.1]
toothbrush_D[0].rotation = [0, 0, 0]
bottle_J[0].position = [2.5874943477084322, 3.2340475305042182, 0.14]
bottle_J[0].rotation = [0, 0, 0]
toothbrush_E[0].position = [0.35285788611403, 1.5902615396545534, 0.095]
toothbrush_E[0].rotation = [0, 0, 0]
plant_D[0].position = [0.46847423813783706, 3.910620012243164, 0.4]
plant_D[0].rotation = [0, 0, 0]
lamp_D[0].position = [0.7457805795362941, 0.9598217483703269, 0.19]
lamp_D[0].rotation = [0, 0, 0]
livingplant[0].position = [1.065615581950343, 2.441357875959051, 0.725]
livingplant[0].rotation = [0, 0, 0]
bottle_K[0].position = [1.0979421841687202, 2.109641829462941, 0.145]
bottle_K[0].rotation = [0, 0, 0]
decorativebottle_D[0].position = [2.5099792809594836, 0.6343088913406638, 0.12]
decorativebottle_D[0].rotation = [0, 0, 0]
towel_B[0].position = [1.460007919902532, 0.33548188511945876, 0.45]
towel_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Helper for assigning an explicit pose without replacing any asset variable.
def place(asset_group, position, yaw_degrees=0.0):
    asset_group[0].position = position
    asset_group[0].rotation = [0, 0, radians(yaw_degrees)]


# ---------------------------------------------------------------------------
# Primary bathroom fixtures and floor-standing objects.
#
# The shower and tub occupy the west side. The vanity, sink, and cabinet use
# the east side, leaving the center usable and preserving a clear approach to
# the 0.74 m door centered at (2.51, 4.00).
# ---------------------------------------------------------------------------
place(shower,       [0.50, 3.45, 1.10], -90)
place(tub,          [0.475, 1.65, 0.34],   0)

place(vanity,       [2.925, 0.90, 0.41], 180)
place(sink,         [2.925, 0.90, 1.25], 180)
place(cabinet,      [2.96, 2.65, 0.40], 180)

place(toilet,       [1.45, 0.35, 0.39],  90)
place(plant_C,      [1.45, 1.08, 0.30], 180)

place(wastebin_A,   [2.45, 0.18, 0.20],  90)
place(wastebin_B,   [1.90, 0.15, 0.175], 90)


# ---------------------------------------------------------------------------
# Wall-mounted storage, mirror, lighting, plants, and towel installations.
# Their elevations keep them clear of the floor fixtures below.
# ---------------------------------------------------------------------------
place(shelf_A, [3.06, 0.95, 1.55], 180)
place(shelf_B, [3.07, 2.65, 1.55], 180)

place(mirror, [1.45, 3.985, 1.55], -90)

place(lamp_A, [0.82, 3.92, 2.35], -90)
place(lamp_B, [1.95, 3.91, 2.35], -90)
place(lamp_C, [3.11, 1.82, 2.30], 180)
place(lamp_D, [3.09, 3.28, 2.30], 180)

place(plant_A,     [3.14, 0.30, 1.45], 180)
place(plant_D,     [3.14, 2.55, 1.75], 180)
place(livingplant, [3.04, 3.68, 1.525], 180)

place(towelrack_A, [0.06, 0.48, 1.40],   0)
place(towelrack_B, [0.06, 2.55, 1.40],   0)
place(towel_A,     [0.095, 0.48, 1.40],  0)
place(towel_B,     [0.095, 2.55, 1.40],  0)


# ---------------------------------------------------------------------------
# Countertop arrangement.
#
# The required soap dispenser is placed directly on the vanity at its free
# north edge, outside the sink footprint. Frequently used toothbrush and soap
# items are grouped on the sink, with the small plant at the rear.
# ---------------------------------------------------------------------------
place(soapdispenser_A, [2.75, 1.575, 0.925], 180)

sink_items = [
    toothbrush_A, toothbrush_B, toothbrush_C, toothbrush_D,
    toothbrush_E, toothbrushholder, soapdispenser_B,
    soapdispenser_C, soapdispenser_D,
]
sink_item_positions = [
    [2.72, 0.40], [3.06, 0.40],
    [2.72, 0.64], [3.06, 0.64],
    [2.72, 0.88], [3.06, 0.88],
    [2.72, 1.12], [3.06, 1.12],
    [2.72, 1.36],
]
for item_group, xy_position in zip(sink_items, sink_item_positions):
    place(
        item_group,
        [xy_position[0], xy_position[1], 1.68 + item_group.size[2] / 2],
        180,
    )

place(plant_B, [3.06, 1.40, 1.82], 180)


# ---------------------------------------------------------------------------
# Cabinet-top arrangement: larger decorative bottles are placed in two rows.
# Row and column spacing exceeds the objects' horizontal bounding-box sizes.
# ---------------------------------------------------------------------------
cabinet_items = [
    bottle_A, bottle_B, bottle_C, bottle_D, bottle_E, bottle_F,
    bottle_G, bottle_H, bottle_I, bottle_J, bottle_K,
    decorativebottle_A, decorativebottle_B, decorativebottle_C,
    decorativebottle_D, ornament_A,
]
cabinet_item_positions = [
    [2.80, 1.98], [3.10, 1.98],
    [2.80, 2.17], [3.10, 2.17],
    [2.80, 2.36], [3.10, 2.36],
    [2.80, 2.55], [3.10, 2.55],
    [2.80, 2.74], [3.10, 2.74],
    [2.80, 2.93], [3.10, 2.93],
    [2.80, 3.12], [3.10, 3.12],
    [2.80, 3.31], [3.10, 3.31],
]
for item_group, xy_position in zip(cabinet_items, cabinet_item_positions):
    place(
        item_group,
        [xy_position[0], xy_position[1], 0.80 + item_group.size[2] / 2],
        180,
    )


# ---------------------------------------------------------------------------
# Floating-shelf arrangements. Each shelf uses a single evenly spaced row so
# the candles and ornaments do not overlap.
# ---------------------------------------------------------------------------
shelf_A_items = [
    ornament_B, ornament_C,
    candle_A, candle_B, candle_C, candle_D, candle_E, candle_F, candle_G,
]
shelf_A_y_positions = [0.14, 0.34, 0.54, 0.74, 0.94, 1.14, 1.34, 1.54, 1.74]
for item_group, y_position in zip(shelf_A_items, shelf_A_y_positions):
    place(
        item_group,
        [3.05, y_position, 1.58 + item_group.size[2] / 2],
        180,
    )

shelf_B_items = [
    candle_H, candle_I, candle_J, candle_K, candle_L,
    candle_M, candle_N, candle_O, candle_P,
]
shelf_B_y_positions = [2.01, 2.17, 2.33, 2.49, 2.65, 2.81, 2.97, 3.13, 3.29]
for item_group, y_position in zip(shelf_B_items, shelf_B_y_positions):
    place(
        item_group,
        [3.06, y_position, 1.58 + item_group.size[2] / 2],
        180,
    )


# ---------------------------------------------------------------------------
# High-priority semantic constraints.
# ---------------------------------------------------------------------------

# The toilet faces the plant as explicitly required.
solver.point_towards(toilet[0], plant_C[0])

# The sink is supported by the vanity, and the required dispenser is directly
# supported by the vanity rather than by the sink.
solver.on_top_of(sink[0], vanity[0])
solver.on_top_of(soapdispenser_A[0], vanity[0])

# Frequently used countertop objects are supported by the sink.
for item_group in sink_items:
    solver.on_top_of(item_group[0], sink[0])
    solver.align_with(item_group[0], sink[0])
solver.on_top_of(plant_B[0], sink[0])
solver.align_with(plant_B[0], sink[0])
solver.align_with(soapdispenser_A[0], vanity[0])

# Decorative bottles are supported by the cabinet.
for item_group in cabinet_items:
    solver.on_top_of(item_group[0], cabinet[0])
    solver.align_with(item_group[0], cabinet[0])

# Candles and ornaments are supported by their respective floating shelves.
for item_group in shelf_A_items:
    solver.on_top_of(item_group[0], shelf_A[0])
    solver.align_with(item_group[0], shelf_A[0])
for item_group in shelf_B_items:
    solver.on_top_of(item_group[0], shelf_B[0])
    solver.align_with(item_group[0], shelf_B[0])


# ---------------------------------------------------------------------------
# Wall relationships for fixtures whose intended use depends on wall contact.
# Wall indices: 0=south, 1=east, 2=north, 3=west.
# ---------------------------------------------------------------------------
solver.against_wall(shower[0], walls[2])
solver.against_wall(tub[0], walls[3])

solver.against_wall(vanity[0], walls[1])
solver.against_wall(cabinet[0], walls[1])
solver.against_wall(shelf_A[0], walls[1])
solver.against_wall(shelf_B[0], walls[1])

solver.against_wall(toilet[0], walls[0])
solver.against_wall(wastebin_A[0], walls[0])
solver.against_wall(wastebin_B[0], walls[0])

solver.against_wall(mirror[0], walls[2])
solver.against_wall(lamp_A[0], walls[2])
solver.against_wall(lamp_B[0], walls[2])
solver.against_wall(lamp_C[0], walls[1])
solver.against_wall(lamp_D[0], walls[1])

solver.against_wall(plant_A[0], walls[1])
solver.against_wall(plant_D[0], walls[1])
solver.against_wall(livingplant[0], walls[1])

solver.against_wall(towelrack_A[0], walls[3])
solver.against_wall(towelrack_B[0], walls[3])

# Keep each towel attached to and aligned with its intended rack.
solver.distance_constraint(towel_A[0], towelrack_A[0], 0.035, 0.035, weight=10)
solver.align_with(towel_A[0], towelrack_A[0])
solver.distance_constraint(towel_B[0], towelrack_B[0], 0.035, 0.035, weight=10)
solver.align_with(towel_B[0], towelrack_B[0])


# ---------------------------------------------------------------------------
# Pose-preservation constraints.
#
# Every new instance receives an exact position constraint. Every instance
# except the toilet also receives an orientation constraint against a fixed
# reference; the toilet already has the stronger point_towards constraint.
# These preserve the non-overlapping composition if the solver adjusts it.
# ---------------------------------------------------------------------------
all_new_assets = [
    bottle_A, toothbrush_A, lamp_A, decorativebottle_A, ornament_A,
    candle_A, wastebin_A, soapdispenser_A, towelrack_A, candle_B,
    candle_C, candle_D, plant_A, vanity, decorativebottle_B, lamp_B,
    bottle_B, candle_E, ornament_B, soapdispenser_B, soapdispenser_C,
    candle_F, candle_G, candle_H, candle_I, sink, candle_J, plant_B,
    shelf_A, bottle_C, bottle_D, toothbrush_B, candle_K, towel_A,
    shelf_B, candle_L, bottle_E, bottle_F, cabinet, mirror, bottle_G,
    candle_M, candle_N, decorativebottle_C, soapdispenser_D, candle_O,
    lamp_C, plant_C, candle_P, bottle_H, toilet, ornament_C,
    toothbrushholder, tub, toothbrush_C, shower, towelrack_B,
    wastebin_B, bottle_I, toothbrush_D, bottle_J, toothbrush_E,
    plant_D, lamp_D, livingplant, bottle_K, decorativebottle_D, towel_B,
]

# Retain the fixed references for the full constraint-program lifetime.
_position_references = []
_orientation_references = []

for item_group in all_new_assets:
    position_reference = AssetInstance(
        position=list(item_group[0].position),
        rotation=list(item_group[0].rotation),
    )
    _position_references.append(position_reference)
    solver.distance_constraint(
        item_group[0],
        position_reference,
        0.0,
        0.0,
        weight=10,
    )

    if item_group is not toilet:
        orientation_reference = AssetInstance(
            position=list(item_group[0].position),
            rotation=list(item_group[0].rotation),
        )
        _orientation_references.append(orientation_reference)
        solver.align_with(item_group[0], orientation_reference)

solver.constraints = []
candle_N[0].position = [3.059999942779541, 2.9700000286102295, 0.11499999463558197]
candle_N[0].rotation = [0, 0, -3.113071175533296]
candle_N[0].optimize = 2
candle_H[0].position = [3.059999942779541, 2.009999990463257, 0.11499999463558197]
candle_H[0].rotation = [0, 0, -3.113071175533296]
candle_H[0].optimize = 2
vanity[0].position = [2.9185445308685303, 0.8999999761581421, 0.4099999964237213]
vanity[0].rotation = [0, 0, -3.138956162383725]
vanity[0].optimize = 2
shelf_A[0].position = [3.045828342437744, 0.949999988079071, 0.029999999329447746]
shelf_A[0].rotation = [0, 0, 3.125826272178512]
shelf_A[0].optimize = 2
mirror[0].position = [1.4500000476837158, 3.986603260040283, 0.8500000238418579]
mirror[0].rotation = [0, 0, -1.5665823302610118]
mirror[0].optimize = 2
toothbrush_C[0].position = [2.7200000286102295, 0.6399999856948853, 1.7300000190734863]
toothbrush_C[0].rotation = [0, 0, -3.043213117273583]
toothbrush_C[0].optimize = 2
ornament_B[0].position = [3.049999952316284, 0.14000000059604645, 0.1550000011920929]
ornament_B[0].rotation = [0, 0, -3.113071614598256]
ornament_B[0].optimize = 2
plant_C[0].position = [1.4500000476837158, 1.0800000429153442, 0.30000001192092896]
plant_C[0].rotation = [0, 0, -3.1290262823329655]
plant_C[0].optimize = 2
candle_B[0].position = [3.049999952316284, 0.7400000095367432, 0.11499999463558197]
candle_B[0].rotation = [0, 0, -3.113071614598256]
candle_B[0].optimize = 2
candle_P[0].position = [3.059999942779541, 3.2899999618530273, 0.11499999463558197]
candle_P[0].rotation = [0, 0, -3.113071175533296]
candle_P[0].optimize = 2
plant_B[0].position = [3.059999942779541, 1.399999976158142, 1.8200000524520874]
plant_B[0].rotation = [0, 0, -3.043213117273583]
plant_B[0].optimize = 2
tub[0].position = [0.47743964195251465, 1.649999976158142, 0.3400000035762787]
tub[0].rotation = [0, 0, 0.004226302233372481]
tub[0].optimize = 2
candle_G[0].position = [3.049999952316284, 1.7400000095367432, 0.11999999731779099]
candle_G[0].rotation = [0, 0, -3.113071614598256]
candle_G[0].optimize = 2
soapdispenser_B[0].position = [2.7200000286102295, 1.1200000047683716, 1.790000081062317]
soapdispenser_B[0].rotation = [0, 0, -3.043213117273583]
soapdispenser_B[0].optimize = 2
lamp_A[0].position = [0.8199999928474426, 3.9127578735351562, 0.20999999344348907]
lamp_A[0].rotation = [0, 0, -1.5665816435166855]
lamp_A[0].optimize = 2
candle_O[0].position = [3.059999942779541, 3.130000114440918, 0.11999999731779099]
candle_O[0].rotation = [0, 0, -3.113071175533296]
candle_O[0].optimize = 2
toothbrush_B[0].position = [3.059999942779541, 0.4000000059604645, 1.78000009059906]
toothbrush_B[0].rotation = [0, 0, -3.043213117273583]
toothbrush_B[0].optimize = 2
decorativebottle_B[0].position = [2.799999952316284, 3.119999885559082, 0.9500000476837158]
decorativebottle_B[0].rotation = [0, 0, -3.0623952532593552]
decorativebottle_B[0].optimize = 2
bottle_J[0].position = [3.0999999046325684, 2.740000009536743, 0.9399999976158142]
bottle_J[0].rotation = [0, 0, -3.0623952532593552]
bottle_J[0].optimize = 2
decorativebottle_D[0].position = [2.799999952316284, 3.309999942779541, 0.9200000166893005]
decorativebottle_D[0].rotation = [0, 0, -3.0623952532593552]
decorativebottle_D[0].optimize = 2
soapdispenser_A[0].position = [2.75, 1.5750000476837158, 0.925000011920929]
soapdispenser_A[0].rotation = [0, 0, 3.11865059323419]
soapdispenser_A[0].optimize = 2
wastebin_B[0].position = [1.899999976158142, 0.1254177838563919, 0.17499999701976776]
wastebin_B[0].rotation = [0, 0, 1.575020953502686]
wastebin_B[0].optimize = 2
sink[0].position = [2.845684766769409, 0.8999999761581421, 1.25]
sink[0].rotation = [0, 0, -3.06619442649169]
sink[0].optimize = 2
wastebin_A[0].position = [2.450000047683716, 0.1094065010547638, 0.20000000298023224]
wastebin_A[0].rotation = [0, 0, 1.5750285923285536]
wastebin_A[0].optimize = 2
candle_C[0].position = [3.049999952316284, 0.9399999976158142, 0.10999999940395355]
candle_C[0].rotation = [0, 0, -3.113071614598256]
candle_C[0].optimize = 2
towel_A[0].position = [0.19202005863189697, 0.47999998927116394, 0.44999998807907104]
towel_A[0].rotation = [0, 0, -0.018985216703114233]
towel_A[0].optimize = 2
plant_D[0].position = [3.1412854194641113, 2.549999952316284, 0.4000000059604645]
plant_D[0].rotation = [0, 0, -3.1373777066723854]
plant_D[0].optimize = 2
bottle_B[0].position = [3.0999999046325684, 1.9800000190734863, 0.9449999928474426]
bottle_B[0].rotation = [0, 0, -3.0623952532593552]
bottle_B[0].optimize = 2
towelrack_B[0].position = [0.06068965047597885, 2.549999952316284, 0.44999998807907104]
towelrack_B[0].rotation = [0, 0, 0.005300505900014992]
towelrack_B[0].optimize = 2
bottle_K[0].position = [2.799999952316284, 2.930000066757202, 0.9449999928474426]
bottle_K[0].rotation = [0, 0, -3.0623952532593552]
bottle_K[0].optimize = 2
candle_M[0].position = [3.059999942779541, 2.809999942779541, 0.11499999463558197]
candle_M[0].rotation = [0, 0, -3.113071175533296]
candle_M[0].optimize = 2
bottle_I[0].position = [2.799999952316284, 2.740000009536743, 0.9700000286102295]
bottle_I[0].rotation = [0, 0, -3.0623952532593552]
bottle_I[0].optimize = 2
candle_D[0].position = [3.049999952316284, 1.1399999856948853, 0.11999999731779099]
candle_D[0].rotation = [0, 0, -3.113071614598256]
candle_D[0].optimize = 2
plant_A[0].position = [3.1412854194641113, 0.30000001192092896, 0.4000000059604645]
plant_A[0].rotation = [0, 0, -3.1373777066723854]
plant_A[0].optimize = 2
soapdispenser_D[0].position = [2.7200000286102295, 1.3600000143051147, 1.7950000762939453]
soapdispenser_D[0].rotation = [0, 0, -3.043213117273583]
soapdispenser_D[0].optimize = 2
candle_I[0].position = [3.059999942779541, 2.1700000762939453, 0.10999999940395355]
candle_I[0].rotation = [0, 0, -3.113071175533296]
candle_I[0].optimize = 2
candle_E[0].position = [3.049999952316284, 1.340000033378601, 0.11999999731779099]
candle_E[0].rotation = [0, 0, -3.113071614598256]
candle_E[0].optimize = 2
toothbrush_E[0].position = [2.7200000286102295, 0.8799999952316284, 1.7750000953674316]
toothbrush_E[0].rotation = [0, 0, -3.043213117273583]
toothbrush_E[0].optimize = 2
soapdispenser_C[0].position = [3.059999942779541, 1.1200000047683716, 1.7950000762939453]
soapdispenser_C[0].rotation = [0, 0, -3.043213117273583]
soapdispenser_C[0].optimize = 2
candle_A[0].position = [3.049999952316284, 0.5400000214576721, 0.11499999463558197]
candle_A[0].rotation = [0, 0, -3.113071614598256]
candle_A[0].optimize = 2
bottle_E[0].position = [2.799999952316284, 2.359999895095825, 0.9800000190734863]
bottle_E[0].rotation = [0, 0, -3.0623952532593552]
bottle_E[0].optimize = 2
decorativebottle_C[0].position = [3.0627105236053467, 3.1157643795013428, 0.9500000476837158]
decorativebottle_C[0].rotation = [0, 0, -3.0623952532593552]
decorativebottle_C[0].optimize = 2
towel_B[0].position = [0.19202005863189697, 2.549999952316284, 0.44999998807907104]
towel_B[0].rotation = [0, 0, -0.018985216703114233]
towel_B[0].optimize = 2
toothbrush_D[0].position = [3.059999942779541, 0.6399999856948853, 1.78000009059906]
toothbrush_D[0].rotation = [0, 0, -3.043213117273583]
toothbrush_D[0].optimize = 2
shelf_B[0].position = [3.05898118019104, 2.6500000953674316, 0.029999999329447746]
shelf_B[0].rotation = [0, 0, 3.1258276965617977]
shelf_B[0].optimize = 2
bottle_D[0].position = [3.0999999046325684, 2.1700000762939453, 0.9449999928474426]
bottle_D[0].rotation = [0, 0, -3.0623952532593552]
bottle_D[0].optimize = 2
decorativebottle_A[0].position = [3.0840160846710205, 2.9281845092773438, 0.9200000166893005]
decorativebottle_A[0].rotation = [0, 0, -3.0623952532593552]
decorativebottle_A[0].optimize = 2
candle_L[0].position = [3.059999942779541, 2.6500000953674316, 0.11999999731779099]
candle_L[0].rotation = [0, 0, -3.113071175533296]
candle_L[0].optimize = 2
toilet[0].position = [1.4500000476837158, 0.34783270955085754, 0.38999998569488525]
toilet[0].rotation = [0, 0, 1.5750161958050857]
toilet[0].optimize = 2
livingplant[0].position = [3.04180908203125, 3.680000066757202, 0.7250000238418579]
livingplant[0].rotation = [0, 0, -3.1373760326433295]
livingplant[0].optimize = 2
candle_K[0].position = [3.059999942779541, 2.490000009536743, 0.11999999731779099]
candle_K[0].rotation = [0, 0, -3.113071175533296]
candle_K[0].optimize = 2
lamp_B[0].position = [1.9500000476837158, 3.887444019317627, 0.1899999976158142]
lamp_B[0].rotation = [0, 0, -1.5665831976265592]
lamp_B[0].optimize = 2
lamp_D[0].position = [3.0937955379486084, 3.2799999713897705, 0.1899999976158142]
lamp_D[0].rotation = [0, 0, -3.137378164438092]
lamp_D[0].optimize = 2
bottle_H[0].position = [3.0999999046325684, 2.549999952316284, 0.9449999928474426]
bottle_H[0].rotation = [0, 0, -3.0623952532593552]
bottle_H[0].optimize = 2
bottle_F[0].position = [3.0999999046325684, 2.359999895095825, 0.9800000190734863]
bottle_F[0].rotation = [0, 0, -3.0623952532593552]
bottle_F[0].optimize = 2
lamp_C[0].position = [3.113715410232544, 1.8200000524520874, 0.20999999344348907]
lamp_C[0].rotation = [0, 0, -3.137378258352586]
lamp_C[0].optimize = 2
cabinet[0].position = [2.948974132537842, 2.6500000953674316, 0.4000000059604645]
cabinet[0].rotation = [0, 0, -3.127333734343052]
cabinet[0].optimize = 2
ornament_A[0].position = [3.0414047241210938, 3.303344488143921, 0.9000000357627869]
ornament_A[0].rotation = [0, 0, -3.0623952532593552]
ornament_A[0].optimize = 2
ornament_C[0].position = [3.049999952316284, 0.3400000035762787, 0.1550000011920929]
ornament_C[0].rotation = [0, 0, -3.113071614598256]
ornament_C[0].optimize = 2
candle_F[0].position = [3.049999952316284, 1.5399999618530273, 0.11499999463558197]
candle_F[0].rotation = [0, 0, -3.113071614598256]
candle_F[0].optimize = 2
toothbrushholder[0].position = [3.059999942779541, 0.8799999952316284, 1.7400000095367432]
toothbrushholder[0].rotation = [0, 0, -3.043213117273583]
toothbrushholder[0].optimize = 2
towelrack_A[0].position = [0.06068965047597885, 0.47999998927116394, 0.44999998807907104]
towelrack_A[0].rotation = [0, 0, 0.005300505900014992]
towelrack_A[0].optimize = 2
bottle_C[0].position = [2.799999952316284, 2.1700000762939453, 0.9700000286102295]
bottle_C[0].rotation = [0, 0, -3.0623952532593552]
bottle_C[0].optimize = 2
shower[0].position = [0.6110444664955139, 3.4322497844696045, 1.100000023841858]
shower[0].rotation = [0, 0, -1.4387476116823987]
shower[0].optimize = 2
candle_J[0].position = [3.059999942779541, 2.3299999237060547, 0.10999999940395355]
candle_J[0].rotation = [0, 0, -3.113071175533296]
candle_J[0].optimize = 2
bottle_G[0].position = [2.799999952316284, 2.549999952316284, 0.9800000190734863]
bottle_G[0].rotation = [0, 0, -3.0623952532593552]
bottle_G[0].optimize = 2
toothbrush_A[0].position = [2.7200000286102295, 0.4000000059604645, 1.7750000953674316]
toothbrush_A[0].rotation = [0, 0, -3.043213117273583]
toothbrush_A[0].optimize = 2
bottle_A[0].position = [2.799999952316284, 1.9800000190734863, 0.9399999976158142]
bottle_A[0].rotation = [0, 0, -3.0623952532593552]
bottle_A[0].optimize = 2

