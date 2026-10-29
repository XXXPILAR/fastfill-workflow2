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
bottle_A = Assets(description="A hand‑blown glass bottle with iridescent swirls, rounded cylindrical form, translucent pastel hues and a delicate organic curve, showcasing a subtle ripple pattern", size=[0.09, 0.09, 0.22], placements=[AssetInstance() for _ in range(1)])
toothbrush_A = Assets(description="A bamboo-handled toothbrush with biophilic style, slender cylindrical shape, natural wood color and smooth rounded tip", size=[0.20, 0.02, 0.02], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="A wall‑mounted brass lamp with a warm brass finish, slim rectangular profile, gentle upward curve of the shade and a subtle biophilic pattern etched on the metal", size=[0.18, 0.12, 0.30], placements=[AssetInstance() for _ in range(1)])
decorativebottle_A = Assets(description="A textured glass decorative bottle, square‑ish body with subtle ridged surface, matte frosted finish", size=[0.08, 0.08, 0.18], placements=[AssetInstance() for _ in range(1)])
ornament_A = Assets(description="A decorative textured glass bottle with a matte stone‑like finish, squat cylindrical body, slightly rough surface and a rounded base", size=[0.11, 0.11, 0.13], placements=[AssetInstance() for _ in range(1)])
candle_A = Assets(description="A natural soy scented candle in a simple cylindrical container, matte ivory color, with a rounded top and a faint wooden lid detail", size=[0.07, 0.07, 0.09], placements=[AssetInstance() for _ in range(1)])
wastebin_A = Assets(description="A rectangular recycled‑metal waste bin with a brushed finish, clean lines and a subtle curved lid, biophilic style", size=[0.20, 0.24, 0.34], placements=[AssetInstance() for _ in range(1)])
soapdispenser_A = Assets(description="A recycled glass soap dispenser with a smooth cylindrical body, clear translucent finish and subtle organic curves, thin rim at the top", size=[0.09, 0.07, 0.19], placements=[AssetInstance() for _ in range(1)])
towelrack_A = Assets(description="A wood‑finished towel rack with two vertical natural‑finish bars, sleek straight‑edged design", size=[0.10, 0.45, 0.65], placements=[AssetInstance() for _ in range(1)])
candle_B = Assets(description="A natural soy scented candle in a simple cylindrical container, matte ivory color, with a rounded top and a faint wooden lid detail", size=[0.07, 0.07, 0.09], placements=[AssetInstance() for _ in range(1)])
candle_C = Assets(description="A natural soy scented candle in a simple cylindrical container, matte ivory color, with a rounded top and a faint wooden lid detail", size=[0.07, 0.07, 0.09], placements=[AssetInstance() for _ in range(1)])
candle_D = Assets(description="A soy scented candle with a smooth cylindrical shape, soft ivory color, natural soy wax finish and subtle biophilic texture, featuring a tiny leaf imprint on its surface", size=[0.07, 0.07, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_A = Assets(description="A living‑wall plant in mossy green, compact vertical foliage, soft textured leaves, natural organic form", size=[0.18, 0.40, 0.60], placements=[AssetInstance() for _ in range(1)])
vanity = Assets(description="A reclaimed‑wood vanity unit with a low rectangular top, natural grain finish, sturdy legs, warm brown tones", size=[0.50, 1.20, 0.82], placements=[AssetInstance() for _ in range(1)])
decorativebottle_B = Assets(description="A hand‑blown decorative glass bottle, rounded cylindrical silhouette, iridescent swirl pattern, translucent pastel tones and a delicate organic neck curve", size=[0.09, 0.09, 0.23], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="A wall‑mounted brass lamp with a warm brass cylindrical shade, slender stem, polished finish", size=[0.17, 0.10, 0.28], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="A hand‑blown glass bottle with iridescent finish, rounded body tapering to a narrow neck, shimmering rainbow hues", size=[0.09, 0.09, 0.21], placements=[AssetInstance() for _ in range(1)])
candle_E = Assets(description="A soy scented candle in a smooth cylindrical container, natural beige wax, subtle wooden lid", size=[0.07, 0.07, 0.09], placements=[AssetInstance() for _ in range(1)])
ornament_B = Assets(description="A decorative textured glass bottle with a matte stone‑like finish, squat cylindrical body, slightly rough surface and a rounded base", size=[0.11, 0.11, 0.13], placements=[AssetInstance() for _ in range(1)])
soapdispenser_B = Assets(description="A glass soap dispenser made from recycled glass, slender rectangular bottle, clear with subtle frosted accents", size=[0.08, 0.07, 0.20], placements=[AssetInstance() for _ in range(1)])
soapdispenser_C = Assets(description="A glass soap dispenser made from recycled glass, sleek cylindrical shape, clear subtle frosted accents and a gentle tapered neck, with a soft biophilic curve", size=[0.09, 0.07, 0.20], placements=[AssetInstance() for _ in range(1)])
candle_F = Assets(description="A natural‑wax soy scented candle, smooth cylindrical form, creamy white surface with a faint matte finish", size=[0.07, 0.07, 0.10], placements=[AssetInstance() for _ in range(1)])
candle_G = Assets(description="A soy scented candle in a smooth cylindrical container, natural beige wax, subtle wooden lid", size=[0.07, 0.07, 0.09], placements=[AssetInstance() for _ in range(1)])
candle_H = Assets(description="A natural soy scented candle in a simple cylindrical container, matte ivory color, with a rounded top and a faint wooden lid detail", size=[0.07, 0.07, 0.09], placements=[AssetInstance() for _ in range(1)])
candle_I = Assets(description="A natural‑wax soy scented candle, smooth cylindrical form, creamy white surface with a faint matte finish", size=[0.07, 0.07, 0.10], placements=[AssetInstance() for _ in range(1)])
sink = Assets(description="A stone countertop sink with a wide oval basin, thick natural stone slab, matte earthy tones, subtle veining", size=[0.45, 0.65, 0.85], placements=[AssetInstance() for _ in range(1)])
candle_J = Assets(description="A natural soy scented candle in a simple cylindrical container, matte ivory color, with a rounded top and a faint wooden lid detail", size=[0.07, 0.07, 0.09], placements=[AssetInstance() for _ in range(1)])
plant_B = Assets(description="A small potted plant with mossy green foliage, round pot of natural clay, low‑lying compact leaves and a gentle dome shape", size=[0.18, 0.18, 0.22], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="A floating wooden shelf with a minimalist slim profile, straight‑edged rectangular board, natural finish", size=[0.28, 1.80, 0.04], placements=[AssetInstance() for _ in range(1)])
bottle_C = Assets(description="A hand‑blown decorative glass bottle with a slender elongated shape, clear with subtle iridescent swirl", size=[0.07, 0.07, 0.27], placements=[AssetInstance() for _ in range(1)])
bottle_D = Assets(description="A hand‑blown glass bottle with iridescent finish, rounded body tapering to a narrow neck, shimmering rainbow hues", size=[0.09, 0.09, 0.21], placements=[AssetInstance() for _ in range(1)])
toothbrush_B = Assets(description="A bamboo-handled toothbrush with a gently curved head and natural wood grain finish, featuring soft bristles and an ergonomic slender shape", size=[0.19, 0.02, 0.02], placements=[AssetInstance() for _ in range(1)])
candle_K = Assets(description="A soy scented candle with a smooth cylindrical shape, soft ivory color, natural soy wax finish and subtle biophilic texture, featuring a tiny leaf imprint on its surface", size=[0.07, 0.07, 0.10], placements=[AssetInstance() for _ in range(1)])
towel_A = Assets(description="A soft white towel made of organic cotton, flat rectangular shape, plush texture and a subtle woven grain, with a gentle rolled edge", size=[0.04, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="A floating wooden shelf with a minimalist slim profile, straight‑edged rectangular board, natural finish", size=[0.24, 0.65, 0.04], placements=[AssetInstance() for _ in range(1)])
candle_L = Assets(description="A soy scented candle with a smooth cylindrical shape, soft ivory color, natural soy wax finish and subtle biophilic texture, featuring a tiny leaf imprint on its surface", size=[0.07, 0.07, 0.10], placements=[AssetInstance() for _ in range(1)])
bottle_E = Assets(description="A hand‑blown glass bottle with an iridescent surface, elegant elongated shape, gently flared mouth and a subtle curved silhouette", size=[0.07, 0.07, 0.28], placements=[AssetInstance() for _ in range(1)])
bottle_F = Assets(description="A hand‑blown glass bottle with an iridescent surface, elegant elongated shape, gently flared mouth and a subtle curved silhouette", size=[0.07, 0.07, 0.28], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="A low storage cabinet with a stone base and wooden upper panels, rectangular footprint, textured stone lower half", size=[0.38, 0.90, 0.72], placements=[AssetInstance() for _ in range(1)])
mirror = Assets(description="A single piece of thin and upright large rectangular mirror, frameless, clear reflective surface", size=[0.01, 0.85, 1.10], placements=[AssetInstance() for _ in range(1)])
bottle_G = Assets(description="A hand‑blown glass bottle with an iridescent surface, elegant elongated shape, gently flared mouth and a subtle curved silhouette", size=[0.07, 0.07, 0.28], placements=[AssetInstance() for _ in range(1)])
candle_M = Assets(description="A natural‑wax soy scented candle, smooth cylindrical form, creamy white surface with a faint matte finish", size=[0.07, 0.07, 0.10], placements=[AssetInstance() for _ in range(1)])
candle_N = Assets(description="A natural soy scented candle in a simple cylindrical container, matte ivory color, with a rounded top and a faint wooden lid detail", size=[0.07, 0.07, 0.09], placements=[AssetInstance() for _ in range(1)])
decorativebottle_C = Assets(description="A hand‑blown decorative glass bottle, rounded cylindrical silhouette, iridescent swirl pattern, translucent pastel tones and a delicate organic neck curve", size=[0.09, 0.09, 0.23], placements=[AssetInstance() for _ in range(1)])
soapdispenser_D = Assets(description="A glass soap dispenser made from recycled glass, clear cylindrical body with a subtle green tint and a sleek brushed metal pump", size=[0.09, 0.07, 0.20], placements=[AssetInstance() for _ in range(1)])
candle_O = Assets(description="A soy scented candle in a smooth cylindrical container, natural beige wax, subtle wooden lid", size=[0.07, 0.07, 0.09], placements=[AssetInstance() for _ in range(1)])
lamp_C = Assets(description="A wall‑mounted brass lamp with a warm brass finish, slim rectangular profile, gentle upward curve of the shade and a subtle biophilic pattern etched on the metal", size=[0.18, 0.12, 0.30], placements=[AssetInstance() for _ in range(1)])
plant_C = Assets(description="A compact potted plant with dense foliage, earthy terracotta pot, rounded leaf clusters and a sturdy, low‑profile silhouette", size=[0.30, 0.30, 0.40], placements=[AssetInstance() for _ in range(1)])
candle_P = Assets(description="A natural soy scented candle in a simple cylindrical container, matte ivory color, with a rounded top and a faint wooden lid detail", size=[0.07, 0.07, 0.09], placements=[AssetInstance() for _ in range(1)])
bottle_H = Assets(description="A hand‑blown glass bottle with iridescent finish, rounded body tapering to a narrow neck, shimmering rainbow hues", size=[0.09, 0.09, 0.21], placements=[AssetInstance() for _ in range(1)])
toilet = Assets(description="A sleek ceramic toilet with a smooth rounded bowl and a low‑profile rectangular base, glossy white finish, organic lines", size=[0.68, 0.38, 0.76], placements=[AssetInstance() for _ in range(1)])
ornament_C = Assets(description="A decorative textured glass bottle with a matte stone‑like finish, squat cylindrical body, slightly rough surface and a rounded base", size=[0.11, 0.11, 0.13], placements=[AssetInstance() for _ in range(1)])
toothbrushholder = Assets(description="A ceramic toothbrush holder with an earthy tone glaze, low rectangular cup, slightly rounded edges", size=[0.07, 0.11, 0.10], placements=[AssetInstance() for _ in range(1)])
tub = Assets(description="A freestanding stone tub formed from stacked river stones, organic curved silhouette, textured surface, natural grey‑green hue", size=[1.65, 0.80, 0.60], placements=[AssetInstance() for _ in range(1)])
toothbrush_C = Assets(description="A ceramic toothbrush holder with a low‑slung rectangular base, earthy tone glaze, smooth matte finish and a subtle organic groove on its front", size=[0.08, 0.12, 0.09], placements=[AssetInstance() for _ in range(1)])
shower = Assets(description="A glass‑enclosed shower with transparent rectangular panels, thin frameless edges, smooth clear glass", size=[0.90, 0.90, 2.10], placements=[AssetInstance() for _ in range(1)])
towelrack_B = Assets(description="A wood‑finished towel rack with two vertical natural‑finish bars, sleek straight‑edged design", size=[0.10, 0.45, 0.65], placements=[AssetInstance() for _ in range(1)])
wastebin_B = Assets(description="A small recycled‑metal waste bin with a smooth cylindrical body, brushed steel finish and a subtle tapered top, minimalist silhouette", size=[0.20, 0.20, 0.28], placements=[AssetInstance() for _ in range(1)])
bottle_I = Assets(description="A hand‑blown decorative glass bottle with a slender elongated shape, clear with subtle iridescent swirl", size=[0.07, 0.07, 0.27], placements=[AssetInstance() for _ in range(1)])
toothbrush_D = Assets(description="A bamboo-handled toothbrush with a gently curved head and natural wood grain finish, featuring soft bristles and an ergonomic slender shape", size=[0.19, 0.02, 0.02], placements=[AssetInstance() for _ in range(1)])
bottle_J = Assets(description="A hand‑blown glass bottle with iridescent swirls, rounded cylindrical form, translucent pastel hues and a delicate organic curve, showcasing a subtle ripple pattern", size=[0.09, 0.09, 0.22], placements=[AssetInstance() for _ in range(1)])
toothbrush_E = Assets(description="A bamboo-handled toothbrush with biophilic style, slender cylindrical shape, natural wood color and smooth rounded tip", size=[0.20, 0.02, 0.02], placements=[AssetInstance() for _ in range(1)])
plant_D = Assets(description="A living‑wall plant in mossy green, compact vertical foliage, soft textured leaves, natural organic form", size=[0.18, 0.40, 0.60], placements=[AssetInstance() for _ in range(1)])
lamp_D = Assets(description="A wall‑mounted brass lamp with a warm brass cylindrical shade, slender stem, polished finish", size=[0.17, 0.10, 0.28], placements=[AssetInstance() for _ in range(1)])
livingplant = Assets(description="A living wall plant with compact foliage, vertical growth habit, deep green leaves and a slender, elongated pot that hugs the wall", size=[0.22, 0.35, 1.20], placements=[AssetInstance() for _ in range(1)])
bottle_K = Assets(description="A hand‑blown glass bottle with iridescent finish, rounded body tapering to a narrow neck, shimmering rainbow hues", size=[0.09, 0.09, 0.21], placements=[AssetInstance() for _ in range(1)])
decorativebottle_D = Assets(description="A textured glass decorative bottle, square‑ish body with subtle ridged surface, matte frosted finish", size=[0.08, 0.08, 0.18], placements=[AssetInstance() for _ in range(1)])
towel_B = Assets(description="A soft white towel made of organic cotton, flat rectangular shape, plush texture and a subtle woven grain, with a gentle rolled edge", size=[0.04, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])

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

bottle_A[0].position = [2.5516184377769466, 0.6863334951685189, 0.11]
bottle_A[0].rotation = [0, 0, 0]
toothbrush_A[0].position = [0.0469818217402878, 2.7372030008959602, 0.009]
toothbrush_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [1.5519994485133894, 3.1731140367876436, 0.15]
lamp_A[0].rotation = [0, 0, 0]
decorativebottle_A[0].position = [0.9812567173689534, 0.1414528023896735, 0.09]
decorativebottle_A[0].rotation = [0, 0, 0]
ornament_A[0].position = [2.9012414196190877, 3.9785233454960016, 0.065]
ornament_A[0].rotation = [0, 0, 0]
candle_A[0].position = [1.5338449619453347, 0.5656500840022862, 0.045]
candle_A[0].rotation = [0, 0, 0]
wastebin_A[0].position = [0.08796974195268384, 0.868011372890606, 0.17]
wastebin_A[0].rotation = [0, 0, 0]
soapdispenser_A[0].position = [1.0210570747678294, 3.3954129759046587, 0.095]
soapdispenser_A[0].rotation = [0, 0, 0]
towelrack_A[0].position = [2.0482179037814148, 0.021519794291234184, 0.325]
towelrack_A[0].rotation = [0, 0, 0]
candle_B[0].position = [1.8108216083082525, 3.440771083000607, 0.045]
candle_B[0].rotation = [0, 0, 0]
candle_C[0].position = [2.6410505981559247, 0.5483983966566872, 0.045]
candle_C[0].rotation = [0, 0, 0]
candle_D[0].position = [0.3900388960703623, 0.04569579430180415, 0.05]
candle_D[0].rotation = [0, 0, 0]
plant_A[0].position = [3.0452135615673175, 1.268545479097659, 0.3]
plant_A[0].rotation = [0, 0, 0]
vanity[0].position = [2.127266096746843, 2.6299000351743893, 0.41]
vanity[0].rotation = [0, 0, 0]
decorativebottle_B[0].position = [0.2640454461760431, 2.0410827351187084, 0.115]
decorativebottle_B[0].rotation = [0, 0, 0]
lamp_B[0].position = [1.9562674575061187, 1.585570116469202, 0.14]
lamp_B[0].rotation = [0, 0, 0]
bottle_B[0].position = [2.3483864223551767, 2.6757503514552226, 0.105]
bottle_B[0].rotation = [0, 0, 0]
candle_E[0].position = [1.2760393816893523, 1.5428367041985656, 0.045]
candle_E[0].rotation = [0, 0, 0]
ornament_B[0].position = [3.036089054103531, 2.2265874043140204, 0.065]
ornament_B[0].rotation = [0, 0, 0]
soapdispenser_B[0].position = [2.7254417127248356, 1.0396635177153501, 0.1]
soapdispenser_B[0].rotation = [0, 0, 0]
soapdispenser_C[0].position = [2.8909517624644305, 3.809176670607112, 0.1]
soapdispenser_C[0].rotation = [0, 0, 0]
candle_F[0].position = [1.5802768532830758, 1.3769770103382961, 0.05]
candle_F[0].rotation = [0, 0, 0]
candle_G[0].position = [2.9536140406208045, 2.3253117974365662, 0.045]
candle_G[0].rotation = [0, 0, 0]
candle_H[0].position = [2.5005542792220186, 2.715949975550012, 0.045]
candle_H[0].rotation = [0, 0, 0]
candle_I[0].position = [1.0108085223807082, 0.9759585615557573, 0.05]
candle_I[0].rotation = [0, 0, 0]
sink[0].position = [0.5931764238629985, 1.6950871894884152, 0.425]
sink[0].rotation = [0, 0, 0]
candle_J[0].position = [1.0254988208611757, 3.5633394639117877, 0.045]
candle_J[0].rotation = [0, 0, 0]
plant_B[0].position = [1.42949611857516, 0.44866615583610825, 0.11]
plant_B[0].rotation = [0, 0, 0]
shelf_A[0].position = [0.46910587469900417, 3.393993062327059, 0.02]
shelf_A[0].rotation = [0, 0, 0]
bottle_C[0].position = [1.9918488034645443, 2.5166149933594197, 0.135]
bottle_C[0].rotation = [0, 0, 0]
bottle_D[0].position = [0.6815746200324391, 0.3659241708873413, 0.105]
bottle_D[0].rotation = [0, 0, 0]
toothbrush_B[0].position = [2.2763994099123717, 0.13272479277078952, 0.01]
toothbrush_B[0].rotation = [0, 0, 0]
candle_K[0].position = [1.8445683646469044, 1.407477814495207, 0.05]
candle_K[0].rotation = [0, 0, 0]
towel_A[0].position = [2.459390739846097, 2.1525248014147587, 0.35]
towel_A[0].rotation = [0, 0, 0]
shelf_B[0].position = [1.2473474904217552, 2.865662922961804, 0.02]
shelf_B[0].rotation = [0, 0, 0]
candle_L[0].position = [2.6433658354683516, 0.8549790739042971, 0.05]
candle_L[0].rotation = [0, 0, 0]
bottle_E[0].position = [1.8979192005626768, 0.8813083788933862, 0.14]
bottle_E[0].rotation = [0, 0, 0]
bottle_F[0].position = [1.6495033183795067, 3.163221180909479, 0.14]
bottle_F[0].rotation = [0, 0, 0]
cabinet[0].position = [1.8985822397251937, 3.154606041031645, 0.36]
cabinet[0].rotation = [0, 0, 0]
mirror[0].position = [1.3549244035571935, 3.3329230758126966, 0.55]
mirror[0].rotation = [0, 0, 0]
bottle_G[0].position = [1.9955725815863656, 2.506213007711901, 0.14]
bottle_G[0].rotation = [0, 0, 0]
candle_M[0].position = [1.5891852386459797, 0.6070003257278374, 0.05]
candle_M[0].rotation = [0, 0, 0]
candle_N[0].position = [2.116972130313982, 2.928008488731617, 0.045]
candle_N[0].rotation = [0, 0, 0]
decorativebottle_C[0].position = [0.20711556557655728, 2.2440009005281665, 0.115]
decorativebottle_C[0].rotation = [0, 0, 0]
soapdispenser_D[0].position = [2.325468965088241, 2.833935474729893, 0.1]
soapdispenser_D[0].rotation = [0, 0, 0]
candle_O[0].position = [2.6661920406849813, 1.2461166815608484, 0.045]
candle_O[0].rotation = [0, 0, 0]
lamp_C[0].position = [0.7602111468090055, 2.4454982034024324, 0.15]
lamp_C[0].rotation = [0, 0, 0]
plant_C[0].position = [0.11571353777627102, 3.245116597433644, 0.2]
plant_C[0].rotation = [0, 0, 0]
candle_P[0].position = [2.6502742858002115, 0.4861544025407203, 0.045]
candle_P[0].rotation = [0, 0, 0]
bottle_H[0].position = [2.2442558188899513, 1.7642926120918734, 0.105]
bottle_H[0].rotation = [0, 0, 0]
toilet[0].position = [2.3969644268106713, 0.02262938892465227, 0.38]
toilet[0].rotation = [0, 0, 0]
ornament_C[0].position = [1.9223549977772454, 0.6965034935995198, 0.065]
ornament_C[0].rotation = [0, 0, 0]
toothbrushholder[0].position = [0.9709042117920088, 1.5078001261738025, 0.05]
toothbrushholder[0].rotation = [0, 0, 0]
tub[0].position = [0.6292179471236697, 0.46618827607174484, 0.3]
tub[0].rotation = [0, 0, 0]
toothbrush_C[0].position = [1.2916469477272994, 1.4986550783533512, 0.045]
toothbrush_C[0].rotation = [0, 0, 0]
shower[0].position = [2.2411925412681533, 2.132443449017958, 1.05]
shower[0].rotation = [0, 0, 0]
towelrack_B[0].position = [0.5971837039042317, 1.9645158773783131, 0.325]
towelrack_B[0].rotation = [0, 0, 0]
wastebin_B[0].position = [1.7715922103006414, 3.8651930365368576, 0.14]
wastebin_B[0].rotation = [0, 0, 0]
bottle_I[0].position = [0.5107224612630088, 3.528808871612015, 0.135]
bottle_I[0].rotation = [0, 0, 0]
toothbrush_D[0].position = [2.3915226957165485, 0.5913192075904323, 0.01]
toothbrush_D[0].rotation = [0, 0, 0]
bottle_J[0].position = [2.498350964855371, 2.9850014969020764, 0.11]
bottle_J[0].rotation = [0, 0, 0]
toothbrush_E[0].position = [1.8691307715367547, 1.1384671167617721, 0.009]
toothbrush_E[0].rotation = [0, 0, 0]
plant_D[0].position = [2.00220486299451, 1.0034422268334051, 0.3]
plant_D[0].rotation = [0, 0, 0]
lamp_D[0].position = [0.11812502896337272, 3.839454924090146, 0.14]
lamp_D[0].rotation = [0, 0, 0]
livingplant[0].position = [0.9529431017497914, 2.828164482417929, 0.6]
livingplant[0].rotation = [0, 0, 0]
bottle_K[0].position = [0.5243688886615221, 2.988948563544253, 0.105]
bottle_K[0].rotation = [0, 0, 0]
decorativebottle_D[0].position = [0.6152041852616364, 0.26647626620495357, 0.09]
decorativebottle_D[0].rotation = [0, 0, 0]
towel_B[0].position = [1.317396042043896, 0.3472411765839096, 0.35]
towel_B[0].rotation = [0, 0, 0]
bottle_A[0].position = [2.5516184377769466, 0.6863334951685189, 0.11]
bottle_A[0].rotation = [0, 0, 0]
toothbrush_A[0].position = [0.0469818217402878, 2.7372030008959602, 0.009]
toothbrush_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [1.5519994485133894, 3.1731140367876436, 0.15]
lamp_A[0].rotation = [0, 0, 0]
decorativebottle_A[0].position = [0.9812567173689534, 0.1414528023896735, 0.09]
decorativebottle_A[0].rotation = [0, 0, 0]
ornament_A[0].position = [2.9012414196190877, 3.9785233454960016, 0.065]
ornament_A[0].rotation = [0, 0, 0]
candle_A[0].position = [1.5338449619453347, 0.5656500840022862, 0.045]
candle_A[0].rotation = [0, 0, 0]
wastebin_A[0].position = [0.08796974195268384, 0.868011372890606, 0.17]
wastebin_A[0].rotation = [0, 0, 0]
soapdispenser_A[0].position = [1.0210570747678294, 3.3954129759046587, 0.095]
soapdispenser_A[0].rotation = [0, 0, 0]
towelrack_A[0].position = [2.0482179037814148, 0.021519794291234184, 0.325]
towelrack_A[0].rotation = [0, 0, 0]
candle_B[0].position = [1.8108216083082525, 3.440771083000607, 0.045]
candle_B[0].rotation = [0, 0, 0]
candle_C[0].position = [2.6410505981559247, 0.5483983966566872, 0.045]
candle_C[0].rotation = [0, 0, 0]
candle_D[0].position = [0.3900388960703623, 0.04569579430180415, 0.05]
candle_D[0].rotation = [0, 0, 0]
plant_A[0].position = [3.0452135615673175, 1.268545479097659, 0.3]
plant_A[0].rotation = [0, 0, 0]
vanity[0].position = [2.127266096746843, 2.6299000351743893, 0.41]
vanity[0].rotation = [0, 0, 0]
decorativebottle_B[0].position = [0.2640454461760431, 2.0410827351187084, 0.115]
decorativebottle_B[0].rotation = [0, 0, 0]
lamp_B[0].position = [1.9562674575061187, 1.585570116469202, 0.14]
lamp_B[0].rotation = [0, 0, 0]
bottle_B[0].position = [2.3483864223551767, 2.6757503514552226, 0.105]
bottle_B[0].rotation = [0, 0, 0]
candle_E[0].position = [1.2760393816893523, 1.5428367041985656, 0.045]
candle_E[0].rotation = [0, 0, 0]
ornament_B[0].position = [3.036089054103531, 2.2265874043140204, 0.065]
ornament_B[0].rotation = [0, 0, 0]
soapdispenser_B[0].position = [2.7254417127248356, 1.0396635177153501, 0.1]
soapdispenser_B[0].rotation = [0, 0, 0]
soapdispenser_C[0].position = [2.8909517624644305, 3.809176670607112, 0.1]
soapdispenser_C[0].rotation = [0, 0, 0]
candle_F[0].position = [1.5802768532830758, 1.3769770103382961, 0.05]
candle_F[0].rotation = [0, 0, 0]
candle_G[0].position = [2.9536140406208045, 2.3253117974365662, 0.045]
candle_G[0].rotation = [0, 0, 0]
candle_H[0].position = [2.5005542792220186, 2.715949975550012, 0.045]
candle_H[0].rotation = [0, 0, 0]
candle_I[0].position = [1.0108085223807082, 0.9759585615557573, 0.05]
candle_I[0].rotation = [0, 0, 0]
sink[0].position = [0.5931764238629985, 1.6950871894884152, 0.425]
sink[0].rotation = [0, 0, 0]
candle_J[0].position = [1.0254988208611757, 3.5633394639117877, 0.045]
candle_J[0].rotation = [0, 0, 0]
plant_B[0].position = [1.42949611857516, 0.44866615583610825, 0.11]
plant_B[0].rotation = [0, 0, 0]
shelf_A[0].position = [0.46910587469900417, 3.393993062327059, 0.02]
shelf_A[0].rotation = [0, 0, 0]
bottle_C[0].position = [1.9918488034645443, 2.5166149933594197, 0.135]
bottle_C[0].rotation = [0, 0, 0]
bottle_D[0].position = [0.6815746200324391, 0.3659241708873413, 0.105]
bottle_D[0].rotation = [0, 0, 0]
toothbrush_B[0].position = [2.2763994099123717, 0.13272479277078952, 0.01]
toothbrush_B[0].rotation = [0, 0, 0]
candle_K[0].position = [1.8445683646469044, 1.407477814495207, 0.05]
candle_K[0].rotation = [0, 0, 0]
towel_A[0].position = [2.459390739846097, 2.1525248014147587, 0.35]
towel_A[0].rotation = [0, 0, 0]
shelf_B[0].position = [1.2473474904217552, 2.865662922961804, 0.02]
shelf_B[0].rotation = [0, 0, 0]
candle_L[0].position = [2.6433658354683516, 0.8549790739042971, 0.05]
candle_L[0].rotation = [0, 0, 0]
bottle_E[0].position = [1.8979192005626768, 0.8813083788933862, 0.14]
bottle_E[0].rotation = [0, 0, 0]
bottle_F[0].position = [1.6495033183795067, 3.163221180909479, 0.14]
bottle_F[0].rotation = [0, 0, 0]
cabinet[0].position = [1.8985822397251937, 3.154606041031645, 0.36]
cabinet[0].rotation = [0, 0, 0]
mirror[0].position = [1.3549244035571935, 3.3329230758126966, 0.55]
mirror[0].rotation = [0, 0, 0]
bottle_G[0].position = [1.9955725815863656, 2.506213007711901, 0.14]
bottle_G[0].rotation = [0, 0, 0]
candle_M[0].position = [1.5891852386459797, 0.6070003257278374, 0.05]
candle_M[0].rotation = [0, 0, 0]
candle_N[0].position = [2.116972130313982, 2.928008488731617, 0.045]
candle_N[0].rotation = [0, 0, 0]
decorativebottle_C[0].position = [0.20711556557655728, 2.2440009005281665, 0.115]
decorativebottle_C[0].rotation = [0, 0, 0]
soapdispenser_D[0].position = [2.325468965088241, 2.833935474729893, 0.1]
soapdispenser_D[0].rotation = [0, 0, 0]
candle_O[0].position = [2.6661920406849813, 1.2461166815608484, 0.045]
candle_O[0].rotation = [0, 0, 0]
lamp_C[0].position = [0.7602111468090055, 2.4454982034024324, 0.15]
lamp_C[0].rotation = [0, 0, 0]
plant_C[0].position = [0.11571353777627102, 3.245116597433644, 0.2]
plant_C[0].rotation = [0, 0, 0]
candle_P[0].position = [2.6502742858002115, 0.4861544025407203, 0.045]
candle_P[0].rotation = [0, 0, 0]
bottle_H[0].position = [2.2442558188899513, 1.7642926120918734, 0.105]
bottle_H[0].rotation = [0, 0, 0]
toilet[0].position = [2.3969644268106713, 0.02262938892465227, 0.38]
toilet[0].rotation = [0, 0, 0]
ornament_C[0].position = [1.9223549977772454, 0.6965034935995198, 0.065]
ornament_C[0].rotation = [0, 0, 0]
toothbrushholder[0].position = [0.9709042117920088, 1.5078001261738025, 0.05]
toothbrushholder[0].rotation = [0, 0, 0]
tub[0].position = [0.6292179471236697, 0.46618827607174484, 0.3]
tub[0].rotation = [0, 0, 0]
toothbrush_C[0].position = [1.2916469477272994, 1.4986550783533512, 0.045]
toothbrush_C[0].rotation = [0, 0, 0]
shower[0].position = [2.2411925412681533, 2.132443449017958, 1.05]
shower[0].rotation = [0, 0, 0]
towelrack_B[0].position = [0.5971837039042317, 1.9645158773783131, 0.325]
towelrack_B[0].rotation = [0, 0, 0]
wastebin_B[0].position = [1.7715922103006414, 3.8651930365368576, 0.14]
wastebin_B[0].rotation = [0, 0, 0]
bottle_I[0].position = [0.5107224612630088, 3.528808871612015, 0.135]
bottle_I[0].rotation = [0, 0, 0]
toothbrush_D[0].position = [2.3915226957165485, 0.5913192075904323, 0.01]
toothbrush_D[0].rotation = [0, 0, 0]
bottle_J[0].position = [2.498350964855371, 2.9850014969020764, 0.11]
bottle_J[0].rotation = [0, 0, 0]
toothbrush_E[0].position = [1.8691307715367547, 1.1384671167617721, 0.009]
toothbrush_E[0].rotation = [0, 0, 0]
plant_D[0].position = [2.00220486299451, 1.0034422268334051, 0.3]
plant_D[0].rotation = [0, 0, 0]
lamp_D[0].position = [0.11812502896337272, 3.839454924090146, 0.14]
lamp_D[0].rotation = [0, 0, 0]
livingplant[0].position = [0.9529431017497914, 2.828164482417929, 0.6]
livingplant[0].rotation = [0, 0, 0]
bottle_K[0].position = [0.5243688886615221, 2.988948563544253, 0.105]
bottle_K[0].rotation = [0, 0, 0]
decorativebottle_D[0].position = [0.6152041852616364, 0.26647626620495357, 0.09]
decorativebottle_D[0].rotation = [0, 0, 0]
towel_B[0].position = [1.317396042043896, 0.3472411765839096, 0.35]
towel_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Coordinates follow the supplied boundary: 0 <= x <= 3.20, 0 <= y <= 4.
# Keep the entrance approach (x=2.14..2.88, y=3.0..4.0) clear.
# Fixed-center constraints also retain mounting heights for wall-mounted objects.
def locate(asset_group, xyz, yaw=0, wall_index=None):
    instance = asset_group[0]
    instance.position = list(xyz)
    instance.rotation = [0, 0, radians(yaw)]
    solver.distance_constraint(
        instance, AssetInstance(position=list(xyz)), 0, 0, weight=10
    )
    solver.align_with(
        instance, AssetInstance(rotation=[0, 0, radians(yaw)])
    )
    if wall_index is not None:
        solver.against_wall(instance, walls[wall_index])


# Main fixtures: bathing along the south wall, washing along the west wall,
# and toilet/storage along the east wall. Leave the middle as circulation space.
locate(tub, [1.05, 0.40, 0.30], 0, 0)
locate(shower, [2.75, 0.45, 1.05], 180, 1)
locate(vanity, [0.25, 2.15, 0.41], 0, 3)

# The supplied sink has a full-height bounding box, so give it its own floor
# footprint rather than stacking its 0.85 m height onto the vanity.
locate(sink, [0.225, 3.25, 0.425], 0, 3)
locate(cabinet, [3.01, 2.25, 0.36], 180, 1)

# Plant_C is the compact potted plant opposite the toilet.
locate(plant_C, [0.22, 1.30, 0.20])
toilet[0].position = [2.86, 1.30, 0.38]
toilet[0].rotation = [0, 0, radians(180)]
# Put the requested facing relationship first.
solver.point_towards(toilet[0], plant_C[0])
solver.distance_constraint(
    toilet[0], AssetInstance(position=[2.86, 1.30, 0.38]),
    0, 0, weight=10
)
solver.against_wall(toilet[0], walls[1])

locate(wastebin_A, [0.70, 2.75, 0.17])
locate(wastebin_B, [3.10, 2.95, 0.14], 180, 1)

# Floating shelves provide separate, non-overlapping surfaces for the many
# bottles and candles. The long shelf is above the mirror and its sconces.
locate(shelf_A, [0.14, 2.15, 2.15], 0, 3)
locate(shelf_B, [3.08, 2.25, 1.35], 180, 1)
locate(mirror, [0.005, 2.15, 1.42], 0, 3)

locate(lamp_A, [0.09, 1.60, 1.65], 0, 3)
locate(lamp_B, [0.085, 2.70, 1.65], 0, 3)
locate(lamp_C, [1.80, 3.91, 1.70], -90, 2)
locate(lamp_D, [3.115, 2.25, 1.90], 180, 1)

# Wall greenery is kept above fixtures rather than occupying circulation space.
locate(plant_A, [0.09, 0.50, 1.50], 0, 3)
locate(plant_D, [3.11, 0.50, 2.50], 180, 1)
locate(livingplant, [0.40, 3.89, 1.65], -90, 2)

# Towel panels hang just in front of their racks, with no interpenetration.
locate(towelrack_A, [3.15, 3.10, 1.25], 180, 1)
locate(towelrack_B, [1.10, 3.95, 1.25], -90, 2)
locate(towel_A, [3.075, 3.10, 1.20], 180)
locate(towel_B, [1.10, 3.875, 1.20], -90)
solver.align_with(towel_A[0], towelrack_A[0])
solver.align_with(towel_B[0], towelrack_B[0])
solver.distance_constraint(towel_A[0], towelrack_A[0], 0.08, 0.10)
solver.distance_constraint(towel_B[0], towelrack_B[0], 0.08, 0.10)


def place_on_surface(asset_group, support_group, x, y, yaw=0):
    support_instance = support_group[0]
    top_z = support_instance.position[2] + support_group.size[2] / 2
    instance = asset_group[0]
    instance.position = [x, y, top_z + asset_group.size[2] / 2]
    instance.rotation = [0, 0, radians(yaw)]

    # Support is specified first; the center anchor preserves the selected
    # countertop slot instead of allowing items to collapse into one cluster.
    solver.on_top_of(instance, support_instance)
    solver.distance_constraint(
        instance, AssetInstance(position=list(instance.position)),
        0, 0, weight=10
    )
    solver.align_with(instance, support_instance)


# Two rows on the long shelf: 14.5 cm spacing accommodates even the
# widest 11 cm ornaments, with margins inside all shelf edges.
long_shelf_items = [
    bottle_A, bottle_B, bottle_C, bottle_D, bottle_E, bottle_F,
    bottle_G, bottle_H, bottle_I, bottle_J, bottle_K,
    decorativebottle_A,
    decorativebottle_B, decorativebottle_C, decorativebottle_D,
    ornament_A, ornament_B, ornament_C,
    candle_A, candle_B, candle_C, candle_D, candle_E, candle_F,
]
for item_index, item_group in enumerate(long_shelf_items):
    row_index, column_index = divmod(item_index, 12)
    place_on_surface(
        item_group, shelf_A,
        0.065 + 0.14 * row_index,
        1.36 + 0.145 * column_index
    )

# Ten additional candles occupy the short shelf, not the floor or tub rim.
short_shelf_items = [
    candle_G, candle_H, candle_I, candle_J, candle_K,
    candle_L, candle_M, candle_N, candle_O, candle_P,
]
for item_index, item_group in enumerate(short_shelf_items):
    row_index, column_index = divmod(item_index, 5)
    place_on_surface(
        item_group, shelf_B,
        3.025 + 0.11 * row_index,
        2.01 + 0.12 * column_index,
        180
    )

# All four supplied soap dispensers are on the vanity, including the
# dispenser referenced in the criteria. The middle remains a grooming area.
for item_group, item_y in [
    (soapdispenser_A, 1.72),
    (soapdispenser_B, 1.90),
    (soapdispenser_C, 2.40),
    (soapdispenser_D, 2.58),
]:
    place_on_surface(item_group, vanity, 0.32, item_y)

place_on_surface(toothbrushholder, vanity, 0.30, 2.15)
# Despite its variable name, toothbrush_C is described as another holder.
place_on_surface(toothbrush_C, vanity, 0.12, 2.15)

# The slender toothbrush assets lie flat, respecting their supplied height;
# they are not inserted into holders with an incompatible upright rotation.
for item_group, item_y in [
    (toothbrush_A, 2.02),
    (toothbrush_B, 2.06),
    (toothbrush_D, 2.24),
    (toothbrush_E, 2.28),
]:
    place_on_surface(item_group, vanity, 0.28, item_y)

place_on_surface(plant_B, cabinet, 3.00, 2.52, 180)

solver.constraints = []
soapdispenser_D[0].position = [0.3199999928474426, 2.5799999237060547, 0.9200000166893005]
soapdispenser_D[0].rotation = [0, 0, -0.0011685860543370888]
soapdispenser_D[0].optimize = 2
bottle_C[0].position = [0.2208031713962555, 1.675681233406067, 0.17500001192092896]
bottle_C[0].rotation = [0, 0, -0.004694349574974142]
bottle_C[0].optimize = 2
decorativebottle_B[0].position = [0.2710430920124054, 1.370885968208313, 0.1550000011920929]
decorativebottle_B[0].rotation = [0, 0, -0.004694349574974142]
decorativebottle_B[0].optimize = 2
candle_D[0].position = [0.20499999821186066, 2.6649999618530273, 0.09000000357627869]
candle_D[0].rotation = [0, 0, -0.004694349574974142]
candle_D[0].optimize = 2
decorativebottle_D[0].position = [0.22450628876686096, 1.6532152891159058, 0.12999999523162842]
decorativebottle_D[0].rotation = [0, 0, -0.004694349574974142]
decorativebottle_D[0].optimize = 2
candle_F[0].position = [0.20499999821186066, 2.9549999237060547, 0.09000000357627869]
candle_F[0].rotation = [0, 0, -0.004694349574974142]
candle_F[0].optimize = 2
ornament_B[0].position = [0.20499999821186066, 1.940000057220459, 0.10499999672174454]
ornament_B[0].rotation = [0, 0, -0.004694349574974142]
ornament_B[0].optimize = 2
toilet[0].position = [2.859968900680542, 1.2999999523162842, 0.3799999952316284]
toilet[0].rotation = [0, 0, 3.141545686690948]
toilet[0].optimize = 2
bottle_H[0].position = [0.10446110367774963, 2.381504535675049, 0.14499999582767487]
bottle_H[0].rotation = [0, 0, -0.004694349574974142]
bottle_H[0].optimize = 2
shower[0].position = [2.5470669269561768, 0.4506374001502991, 1.0499999523162842]
shower[0].rotation = [0, 0, 1.5693788766863692]
shower[0].optimize = 2
candle_A[0].position = [0.20499999821186066, 2.2300000190734863, 0.08500000089406967]
candle_A[0].rotation = [0, 0, -0.004694349574974142]
candle_A[0].optimize = 2
lamp_B[0].position = [0.08496266603469849, 2.700000047683716, 0.14000000059604645]
lamp_B[0].rotation = [0, 0, -4.715330676472748e-05]
lamp_B[0].optimize = 2
bottle_K[0].position = [0.06499999761581421, 2.809999942779541, 0.14499999582767487]
bottle_K[0].rotation = [0, 0, -0.004694349574974142]
bottle_K[0].optimize = 2
candle_M[0].position = [3.134999990463257, 2.130000114440918, 0.09000000357627869]
candle_M[0].rotation = [0, 0, 3.1404312418705618]
candle_M[0].optimize = 2
bottle_A[0].position = [0.2673399746417999, 1.3933520317077637, 0.15000000596046448]
bottle_A[0].rotation = [0, 0, -0.004694349574974142]
bottle_A[0].optimize = 2
livingplant[0].position = [0.4000000059604645, 3.8899965286254883, 0.6000000238418579]
livingplant[0].rotation = [0, 0, -1.5708434230846453]
livingplant[0].optimize = 2
plant_B[0].position = [3.0, 2.5199999809265137, 0.8300000429153442]
plant_B[0].rotation = [0, 0, 3.141486895446121]
plant_B[0].optimize = 2
bottle_F[0].position = [0.15099792182445526, 2.099175214767456, 0.18000000715255737]
bottle_F[0].rotation = [0, 0, -0.004694349574974142]
bottle_F[0].optimize = 2
soapdispenser_B[0].position = [0.3199999928474426, 1.899999976158142, 0.9200000166893005]
soapdispenser_B[0].rotation = [0, 0, -0.0011685860543370888]
soapdispenser_B[0].optimize = 2
bottle_J[0].position = [0.06499999761581421, 2.6649999618530273, 0.15000000596046448]
bottle_J[0].rotation = [0, 0, -0.004694349574974142]
bottle_J[0].optimize = 2
towel_A[0].position = [3.048837184906006, 3.0999999046325684, 0.3499999940395355]
towel_A[0].rotation = [0, 0, 3.141557461565788]
towel_A[0].optimize = 2
candle_O[0].position = [3.134999990463257, 2.369999885559082, 0.08500000089406967]
candle_O[0].rotation = [0, 0, 3.1404312418705618]
candle_O[0].optimize = 2
toothbrush_C[0].position = [0.11999999731779099, 2.1500000953674316, 0.8650000095367432]
toothbrush_C[0].rotation = [0, 0, -0.0011685860543370888]
toothbrush_C[0].optimize = 2
toothbrushholder[0].position = [0.30000001192092896, 2.1500000953674316, 0.8700000047683716]
toothbrushholder[0].rotation = [0, 0, -0.0011685860543370888]
toothbrushholder[0].optimize = 2
plant_A[0].position = [0.08998113125562668, 0.5, 0.30000001192092896]
plant_A[0].rotation = [0, 0, -4.711414272466217e-05]
plant_A[0].optimize = 2
towel_B[0].position = [1.100000023841858, 3.848836660385132, 0.3499999940395355]
towel_B[0].rotation = [0, 0, -1.5708315162855986]
towel_B[0].optimize = 2
plant_C[0].position = [0.2199999988079071, 1.2999999523162842, 0.20000000298023224]
plant_C[0].rotation = [0, 0, 0.01256637125682779]
plant_C[0].optimize = 2
soapdispenser_A[0].position = [0.3199999928474426, 1.7200000286102295, 0.9149999618530273]
soapdispenser_A[0].rotation = [0, 0, -0.0011685860543370888]
soapdispenser_A[0].optimize = 2
bottle_D[0].position = [0.19753475487232208, 1.8168458938598633, 0.14499999582767487]
bottle_D[0].rotation = [0, 0, -0.004694349574974142]
bottle_D[0].optimize = 2
toothbrush_E[0].position = [0.2800000011920929, 2.2799999713897705, 0.8299999833106995]
toothbrush_E[0].rotation = [0, 0, -0.0011685860543370888]
toothbrush_E[0].optimize = 2
lamp_A[0].position = [0.08996071666479111, 1.600000023841858, 0.15000000596046448]
lamp_A[0].rotation = [0, 0, -4.715199339851312e-05]
lamp_A[0].optimize = 2
candle_L[0].position = [3.134999990463257, 2.009999990463257, 0.09000000357627869]
candle_L[0].rotation = [0, 0, 3.1404312418705618]
candle_L[0].optimize = 2
candle_I[0].position = [3.0250000953674316, 2.25, 0.09000000357627869]
candle_I[0].rotation = [0, 0, 3.1404312418705618]
candle_I[0].optimize = 2
candle_E[0].position = [0.20499999821186066, 2.809999942779541, 0.08500000089406967]
candle_E[0].rotation = [0, 0, -0.004694349574974142]
candle_E[0].optimize = 2
plant_D[0].position = [3.110018730163574, 0.5, 0.30000001192092896]
plant_D[0].rotation = [0, 0, 3.141545547582168]
plant_D[0].optimize = 2
decorativebottle_A[0].position = [0.06499999761581421, 2.9549999237060547, 0.12999999523162842]
decorativebottle_A[0].rotation = [0, 0, -0.004694349574974142]
decorativebottle_A[0].optimize = 2
ornament_A[0].position = [0.20499999821186066, 1.7949999570846558, 0.10499999672174454]
ornament_A[0].rotation = [0, 0, -0.004694349574974142]
ornament_A[0].optimize = 2
wastebin_B[0].position = [3.1000425815582275, 2.950000047683716, 0.14000000059604645]
wastebin_B[0].rotation = [0, 0, 3.1415455049496575]
wastebin_B[0].optimize = 2
toothbrush_B[0].position = [0.2800000011920929, 2.059999942779541, 0.8299999833106995]
toothbrush_B[0].rotation = [0, 0, -0.0011685860543370888]
toothbrush_B[0].optimize = 2
bottle_B[0].position = [0.2440715730190277, 1.53451669216156, 0.14499999582767487]
bottle_B[0].rotation = [0, 0, -0.004694349574974142]
bottle_B[0].optimize = 2
candle_N[0].position = [3.134999990463257, 2.25, 0.08500000089406967]
candle_N[0].rotation = [0, 0, 3.1404312418705618]
candle_N[0].optimize = 2
candle_H[0].position = [3.0250000953674316, 2.130000114440918, 0.08500000089406967]
candle_H[0].rotation = [0, 0, 3.1404312418705618]
candle_H[0].optimize = 2
bottle_I[0].position = [0.08119269460439682, 2.5226690769195557, 0.17500001192092896]
bottle_I[0].rotation = [0, 0, -0.004694349574974142]
bottle_I[0].optimize = 2
tub[0].position = [1.0499999523162842, 0.830449104309082, 0.30000001192092896]
tub[0].rotation = [0, 0, 1.5846165981546443]
tub[0].optimize = 2
sink[0].position = [0.22497893869876862, 3.25, 0.42500001192092896]
sink[0].rotation = [0, 0, -4.703620652865659e-05]
sink[0].optimize = 2
soapdispenser_C[0].position = [0.3199999928474426, 2.4000000953674316, 0.9200000166893005]
soapdispenser_C[0].rotation = [0, 0, -0.0011685860543370888]
soapdispenser_C[0].optimize = 2
towelrack_B[0].position = [1.100000023841858, 3.9500062465667725, 0.32499998807907104]
towelrack_B[0].rotation = [0, 0, -1.5707247971814173]
towelrack_B[0].optimize = 2
candle_K[0].position = [3.0250000953674316, 2.490000009536743, 0.09000000357627869]
candle_K[0].rotation = [0, 0, 3.1404312418705618]
candle_K[0].optimize = 2
mirror[0].position = [0.005014290567487478, 2.1500000953674316, 0.550000011920929]
mirror[0].rotation = [0, 0, -4.716114688241103e-05]
mirror[0].optimize = 2
wastebin_A[0].position = [0.699999988079071, 2.75, 0.17000000178813934]
wastebin_A[0].rotation = [0, 0, 0.00942477746072377]
wastebin_A[0].optimize = 2
lamp_D[0].position = [3.1150381565093994, 2.25, 0.14000000059604645]
lamp_D[0].rotation = [0, 0, 3.141545498661318]
lamp_D[0].optimize = 2
bottle_G[0].position = [0.12772952020168304, 2.240339756011963, 0.18000000715255737]
bottle_G[0].rotation = [0, 0, -0.004694349574974142]
bottle_G[0].optimize = 2
candle_B[0].position = [0.20499999821186066, 2.375, 0.08500000089406967]
candle_B[0].rotation = [0, 0, -0.004694349574974142]
candle_B[0].optimize = 2
cabinet[0].position = [3.009982109069824, 2.25, 0.36000001430511475]
cabinet[0].rotation = [0, 0, -3.1415211817990727]
cabinet[0].optimize = 2
decorativebottle_C[0].position = [0.24777469038963318, 1.5120506286621094, 0.1550000011920929]
decorativebottle_C[0].rotation = [0, 0, -0.004694349574974142]
decorativebottle_C[0].optimize = 2
candle_J[0].position = [3.0250000953674316, 2.369999885559082, 0.08500000089406967]
candle_J[0].rotation = [0, 0, 3.1404312418705618]
candle_J[0].optimize = 2
toothbrush_A[0].position = [0.2800000011920929, 2.0199999809265137, 0.8299999833106995]
toothbrush_A[0].rotation = [0, 0, -0.0011685860543370888]
toothbrush_A[0].optimize = 2
candle_G[0].position = [3.0250000953674316, 2.009999990463257, 0.08500000089406967]
candle_G[0].rotation = [0, 0, 3.1404312418705618]
candle_G[0].optimize = 2
lamp_C[0].position = [1.7999999523162842, 3.910039186477661, 0.15000000596046448]
lamp_C[0].rotation = [0, 0, -1.570843482015939]
lamp_C[0].optimize = 2
toothbrush_D[0].position = [0.2800000011920929, 2.240000009536743, 0.8299999833106995]
toothbrush_D[0].rotation = [0, 0, -0.0011685860543370888]
toothbrush_D[0].optimize = 2
ornament_C[0].position = [0.20499999821186066, 2.0850000381469727, 0.10499999672174454]
ornament_C[0].rotation = [0, 0, -0.004694349574974142]
ornament_C[0].optimize = 2
candle_C[0].position = [0.20499999821186066, 2.5199999809265137, 0.08500000089406967]
candle_C[0].rotation = [0, 0, -0.004694349574974142]
candle_C[0].optimize = 2
shelf_B[0].position = [3.08003830909729, 2.25, 0.019999999552965164]
shelf_B[0].rotation = [0, 0, -3.1413418098101076]
shelf_B[0].optimize = 2
vanity[0].position = [0.2500033974647522, 2.1500000953674316, 0.4099999964237213]
vanity[0].rotation = [0, 0, 0.0002543598631877996]
vanity[0].optimize = 2
shelf_A[0].position = [0.1405717432498932, 2.1500000953674316, 0.019999999552965164]
shelf_A[0].rotation = [0, 0, -0.0002786587909621912]
shelf_A[0].optimize = 2
bottle_E[0].position = [0.17426633834838867, 1.9580106735229492, 0.18000000715255737]
bottle_E[0].rotation = [0, 0, -0.004694349574974142]
bottle_E[0].optimize = 2
candle_P[0].position = [3.134999990463257, 2.490000009536743, 0.08500000089406967]
candle_P[0].rotation = [0, 0, 3.1404312418705618]
candle_P[0].optimize = 2
towelrack_A[0].position = [3.150006055831909, 3.0999999046325684, 0.32499998807907104]
towelrack_A[0].rotation = [0, 0, -3.1415211251666]
towelrack_A[0].optimize = 2

