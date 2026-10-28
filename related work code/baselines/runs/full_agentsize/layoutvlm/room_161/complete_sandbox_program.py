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
locker_A = Assets(description="A wooden locker with ornate carvings, rectangular shape, dark walnut finish, classic European style, featuring brass handles and a slightly curved top.", size=[0.50, 0.60, 1.90], placements=[AssetInstance() for _ in range(1)])
cologne_A = Assets(description="A classic European glass cologne bottle with a slender cylindrical shape, clear glass, polished silver cap, and a subtle engraved pattern on the front", size=[0.06, 0.06, 0.16], placements=[AssetInstance() for _ in range(1)])
locker_B = Assets(description="A wooden locker with ornate carvings, rectangular shape, dark walnut finish, classic European style, featuring brass handles and a slightly curved top.", size=[0.50, 0.60, 1.90], placements=[AssetInstance() for _ in range(1)])
cologne_B = Assets(description="A glass perfume bottle with a slender cylindrical shape, clear with a polished cap, classic European design", size=[0.06, 0.06, 0.15], placements=[AssetInstance() for _ in range(1)])
towelrack_A = Assets(description="A single piece of thin and upright towel rack with a polished chrome bar, sleek rectangular profile and decorative finial ends", size=[0.08, 0.65, 0.12], placements=[AssetInstance() for _ in range(1)])
wristwatch_A = Assets(description="A classic round wristwatch with a thin silver case, a cream‑coloured leather strap and an engraved Roman numeral dial", size=[0.22, 0.05, 0.01], placements=[AssetInstance() for _ in range(1)])
wristwatchlocker_A = Assets(description="A small round wristwatch with a thin gold‑tone metal band and a minimalist white dial, classic European style", size=[0.20, 0.05, 0.01], placements=[AssetInstance() for _ in range(1)])
sconce_A = Assets(description="A single piece of thin and upright wall sconce with an ornate bronze frame, curved glass shade, traditional European style", size=[0.14, 0.22, 0.42], placements=[AssetInstance() for _ in range(1)])
wristwatchlocker_B = Assets(description="A small round wristwatch with a thin gold‑tone metal band and a minimalist white dial, classic European style", size=[0.20, 0.05, 0.01], placements=[AssetInstance() for _ in range(1)])
locker_C = Assets(description="A wooden locker with ornate carvings, rectangular shape, dark walnut finish, classic European style, featuring brass handles and a slightly curved top.", size=[0.50, 0.60, 1.90], placements=[AssetInstance() for _ in range(1)])
cologne_C = Assets(description="A small glass cologne bottle with a sleek rectangular shape, clear finish and a subtle metallic cap, giving it a refined classic European look.", size=[0.04, 0.07, 0.12], placements=[AssetInstance() for _ in range(1)])
wristwatchlocker_C = Assets(description="A petite round wristwatch with a thin gold‑plated case, a simple white dial and a leather strap, embodying a refined Traditional Classic European look.", size=[0.20, 0.04, 0.01], placements=[AssetInstance() for _ in range(1)])
sink_A = Assets(description="A rectangular ceramic sink with smooth glossy white surface and subtle beveled edges, reflecting traditional European bathroom design.", size=[0.50, 0.65, 0.85], placements=[AssetInstance() for _ in range(1)])
hairbrush_A = Assets(description="A wooden hairbrush with a long slender handle and densely packed bristles, rectangular head, classic European finish", size=[0.24, 0.07, 0.04], placements=[AssetInstance() for _ in range(1)])
cologne_D = Assets(description="A classic European glass cologne bottle with a slender cylindrical shape, clear glass, polished silver cap, and a subtle engraved pattern on the front", size=[0.06, 0.06, 0.16], placements=[AssetInstance() for _ in range(1)])
hook_A = Assets(description="A wall‑mounted coat hook with a slender metal arm, polished brass finish, classic European style, featuring an ornamental scroll at the base.", size=[0.11, 0.06, 0.14], placements=[AssetInstance() for _ in range(1)])
wristwatch_B = Assets(description="A stainless‑steel wristwatch with a round polished face, sleek thin bezel, black leather strap and a subtle engraved logo on the back", size=[0.22, 0.05, 0.01], placements=[AssetInstance() for _ in range(1)])
hairbrush_B = Assets(description="A compact hairbrush with a curved handle and soft bristles, finished in glossy white", size=[0.18, 0.07, 0.04], placements=[AssetInstance() for _ in range(1)])
cologne_E = Assets(description="A sleek glass cologne bottle with a smooth cylindrical body, clear tinted amber glass, a brushed metal cap and a subtle curved shoulder for easy grip", size=[0.07, 0.07, 0.15], placements=[AssetInstance() for _ in range(1)])
eyeglasses_A = Assets(description="A pair of rectangular eyeglasses with thin matte black acetate frames, slightly rounded corners and clear lenses that catch the light", size=[0.05, 0.14, 0.04], placements=[AssetInstance() for _ in range(1)])
cologne_F = Assets(description="A classic European glass cologne bottle with a slender cylindrical shape, clear glass, polished silver cap, and a subtle engraved pattern on the front", size=[0.06, 0.06, 0.16], placements=[AssetInstance() for _ in range(1)])
cologne_G = Assets(description="A glass perfume bottle with a slender cylindrical shape, clear with a polished cap, classic European design", size=[0.06, 0.06, 0.15], placements=[AssetInstance() for _ in range(1)])
locker_D = Assets(description="A wooden locker with ornate carvings, rectangular shape, dark walnut finish, classic European style, featuring brass handles and a slightly curved top.", size=[0.50, 0.60, 1.90], placements=[AssetInstance() for _ in range(1)])
cologne_H = Assets(description="A small glass cologne bottle with a sleek rectangular shape, clear finish and a subtle metallic cap, giving it a refined classic European look.", size=[0.04, 0.07, 0.12], placements=[AssetInstance() for _ in range(1)])
eyeglasses_B = Assets(description="A pair of rectangular eyeglasses with thin matte black acetate frames, slightly rounded corners and clear lenses that catch the light", size=[0.05, 0.14, 0.04], placements=[AssetInstance() for _ in range(1)])
comb_A = Assets(description="A small rectangular plastic comb with fine teeth and a smooth matte finish", size=[0.18, 0.04, 0.01], placements=[AssetInstance() for _ in range(1)])
cologne_I = Assets(description="A glass perfume bottle with a slender cylindrical shape, clear with a polished cap, classic European design", size=[0.06, 0.06, 0.15], placements=[AssetInstance() for _ in range(1)])
locker_E = Assets(description="A wooden locker with ornate carvings, rectangular shape, dark walnut finish, classic European style, featuring brass handles and a slightly curved top.", size=[0.50, 0.60, 1.90], placements=[AssetInstance() for _ in range(1)])
eyeglasses_C = Assets(description="A pair of stylish eyeglasses with polished ivory frames, subtle mother‑of‑pearl inlay on the temples and gently curved lenses", size=[0.05, 0.14, 0.04], placements=[AssetInstance() for _ in range(1)])
hairbrush_C = Assets(description="A wooden hairbrush with a smooth oval handle, bristles of natural boar hair, light honey‑colored finish and a slightly tapered tip for precise styling", size=[0.22, 0.07, 0.04], placements=[AssetInstance() for _ in range(1)])
eyeglasses_D = Assets(description="Classic eyeglasses with dark lacquered frames, subtle cat‑eye shape and a tiny pearl inset on each hinge", size=[0.05, 0.14, 0.04], placements=[AssetInstance() for _ in range(1)])
cologned_e7ba6c = Assets(description="A small cylindrical cologne bottle with a sleek glass body and a silver cap", size=[0.06, 0.06, 0.13], placements=[AssetInstance() for _ in range(1)])
cologne_J = Assets(description="A small cylindrical cologne bottle with a sleek glass body and a silver cap", size=[0.06, 0.06, 0.13], placements=[AssetInstance() for _ in range(1)])
eyeglasseslocker_A = Assets(description="A pair of sleek metal eyeglasses with thin rectangular frames and clear lenses, finished in polished silver, classic European style", size=[0.05, 0.14, 0.03], placements=[AssetInstance() for _ in range(1)])
eyeglasses_E = Assets(description="A delicate pair of eyeglasses with slender metal frames, featuring a rectangular lens shape and polished silver finish, embodying classic European elegance.", size=[0.05, 0.14, 0.03], placements=[AssetInstance() for _ in range(1)])
towelrack_B = Assets(description="A wall‑mounted towel rack with a single curved rod, brushed bronze finish, classic European style, featuring decorative leaf motifs at each end.", size=[0.10, 0.70, 0.14], placements=[AssetInstance() for _ in range(1)])
cologne_K = Assets(description="A glass perfume bottle with a slender cylindrical shape, clear with a polished cap, classic European design", size=[0.06, 0.06, 0.15], placements=[AssetInstance() for _ in range(1)])
wristwatch_C = Assets(description="A stainless‑steel wristwatch with a round polished face, sleek thin bezel, black leather strap and a subtle engraved logo on the back", size=[0.22, 0.05, 0.01], placements=[AssetInstance() for _ in range(1)])
cologne_L = Assets(description="A small cylindrical cologne bottle with a sleek glass body and a silver cap", size=[0.06, 0.06, 0.13], placements=[AssetInstance() for _ in range(1)])
wristwatchlocker_D = Assets(description="A small round wristwatch with a thin gold‑tone metal band and a minimalist white dial, classic European style", size=[0.20, 0.05, 0.01], placements=[AssetInstance() for _ in range(1)])
hook_B = Assets(description="A wall‑mounted coat hook with a slender metal arm, polished brass finish, classic European style, featuring an ornamental scroll at the base.", size=[0.11, 0.06, 0.14], placements=[AssetInstance() for _ in range(1)])
wristwatch_D = Assets(description="A stainless‑steel wristwatch with a round polished face, sleek thin bezel, black leather strap and a subtle engraved logo on the back", size=[0.22, 0.05, 0.01], placements=[AssetInstance() for _ in range(1)])
locker_F = Assets(description="A wooden locker with ornate carvings, rectangular shape, dark walnut finish, classic European style, featuring brass handles and a slightly curved top.", size=[0.50, 0.60, 1.90], placements=[AssetInstance() for _ in range(1)])
cologne_M = Assets(description="A sleek glass cologne bottle with a smooth cylindrical body, clear tinted amber glass, a brushed metal cap and a subtle curved shoulder for easy grip", size=[0.07, 0.07, 0.15], placements=[AssetInstance() for _ in range(1)])
cologne_N = Assets(description="A classic European glass cologne bottle with a slender cylindrical shape, clear glass, polished silver cap, and a subtle engraved pattern on the front", size=[0.06, 0.06, 0.16], placements=[AssetInstance() for _ in range(1)])
eyeglasses_F = Assets(description="A pair of rectangular eyeglasses with thin matte black acetate frames, slightly rounded corners and clear lenses that catch the light", size=[0.05, 0.14, 0.04], placements=[AssetInstance() for _ in range(1)])
hairbrush_D = Assets(description="A wooden hairbrush with a long slender handle and densely packed bristles, rectangular head, classic European finish", size=[0.24, 0.07, 0.04], placements=[AssetInstance() for _ in range(1)])
cologne_O = Assets(description="A small glass cologne bottle with a sleek rectangular shape, clear finish and a subtle metallic cap, giving it a refined classic European look.", size=[0.04, 0.07, 0.12], placements=[AssetInstance() for _ in range(1)])
cologne_P = Assets(description="A classic European glass cologne bottle with a slender cylindrical shape, clear glass, polished silver cap, and a subtle engraved pattern on the front", size=[0.06, 0.06, 0.16], placements=[AssetInstance() for _ in range(1)])
locker_G = Assets(description="A wooden locker with ornate carvings, rectangular shape, dark walnut finish, classic European style, featuring brass handles and a slightly curved top.", size=[0.50, 0.60, 1.90], placements=[AssetInstance() for _ in range(1)])
locker_H = Assets(description="A wooden locker with ornate carvings, rectangular shape, dark walnut finish, classic European style, featuring brass handles and a slightly curved top.", size=[0.50, 0.60, 1.90], placements=[AssetInstance() for _ in range(1)])
cologne_Q = Assets(description="A sleek glass cologne bottle with a smooth cylindrical body, clear tinted amber glass, a brushed metal cap and a subtle curved shoulder for easy grip", size=[0.07, 0.07, 0.15], placements=[AssetInstance() for _ in range(1)])
comb_B = Assets(description="A small rectangular plastic comb with fine teeth and a smooth matte finish", size=[0.18, 0.04, 0.01], placements=[AssetInstance() for _ in range(1)])
hook_C = Assets(description="A wall‑mounted coat hook with a slender metal arm, polished brass finish, classic European style, featuring an ornamental scroll at the base.", size=[0.11, 0.06, 0.14], placements=[AssetInstance() for _ in range(1)])
eyeglasseslocker_B = Assets(description="A pair of sleek metal eyeglasses with thin rectangular frames and clear lenses, finished in polished silver, classic European style", size=[0.05, 0.14, 0.03], placements=[AssetInstance() for _ in range(1)])
cologne_R = Assets(description="A glass perfume bottle with a slender cylindrical shape, clear with a polished cap, classic European design", size=[0.06, 0.06, 0.15], placements=[AssetInstance() for _ in range(1)])
hairbrush_E = Assets(description="A wooden hairbrush with a smooth oval handle, bristles of natural boar hair, light honey‑colored finish and a slightly tapered tip for precise styling", size=[0.22, 0.07, 0.04], placements=[AssetInstance() for _ in range(1)])
eyeglasses_G = Assets(description="A pair of lightweight eyeglasses with thin rectangular frames and clear lenses", size=[0.05, 0.14, 0.03], placements=[AssetInstance() for _ in range(1)])
cologne_S = Assets(description="A classic European glass cologne bottle with a slender cylindrical shape, clear glass, polished silver cap, and a subtle engraved pattern on the front", size=[0.06, 0.06, 0.16], placements=[AssetInstance() for _ in range(1)])
cologne_T = Assets(description="A sleek glass cologne bottle with a smooth cylindrical body, clear tinted amber glass, a brushed metal cap and a subtle curved shoulder for easy grip", size=[0.07, 0.07, 0.15], placements=[AssetInstance() for _ in range(1)])
wristwatch_E = Assets(description="A stainless‑steel wristwatch with a round polished face, sleek thin bezel, black leather strap and a subtle engraved logo on the back", size=[0.22, 0.05, 0.01], placements=[AssetInstance() for _ in range(1)])
hook_D = Assets(description="A wall‑mounted coat hook with a slender metal arm, polished brass finish, classic European style, featuring an ornamental scroll at the base.", size=[0.11, 0.06, 0.14], placements=[AssetInstance() for _ in range(1)])
wristwatch_F = Assets(description="A stainless‑steel wristwatch with a round polished face, sleek thin bezel, black leather strap and a subtle engraved logo on the back", size=[0.22, 0.05, 0.01], placements=[AssetInstance() for _ in range(1)])
hook_E = Assets(description="A wall‑mounted coat hook with a slender metal arm, polished brass finish, classic European style, featuring an ornamental scroll at the base.", size=[0.11, 0.06, 0.14], placements=[AssetInstance() for _ in range(1)])
eyeglasses_H = Assets(description="A pair of rectangular eyeglasses with thin matte black acetate frames, slightly rounded corners and clear lenses that catch the light", size=[0.05, 0.14, 0.04], placements=[AssetInstance() for _ in range(1)])
eyeglasses_I = Assets(description="A pair of refined eyeglasses featuring thin tortoiseshell frames, slightly oversized lenses and a subtle floral motif etched on the temples", size=[0.05, 0.14, 0.04], placements=[AssetInstance() for _ in range(1)])
cologne_U = Assets(description="A small glass cologne bottle with a sleek rectangular shape, clear finish and a subtle metallic cap, giving it a refined classic European look.", size=[0.04, 0.07, 0.12], placements=[AssetInstance() for _ in range(1)])
eyeglasses_J = Assets(description="A pair of rectangular eyeglasses with thin matte black acetate frames, slightly rounded corners and clear lenses that catch the light", size=[0.05, 0.14, 0.04], placements=[AssetInstance() for _ in range(1)])
wristwatch_G = Assets(description="A stainless‑steel wristwatch with a round polished face, sleek thin bezel, black leather strap and a subtle engraved logo on the back", size=[0.22, 0.05, 0.01], placements=[AssetInstance() for _ in range(1)])
cologne_V = Assets(description="A small cylindrical cologne bottle with a sleek glass body and a silver cap", size=[0.06, 0.06, 0.13], placements=[AssetInstance() for _ in range(1)])
cologne_W = Assets(description="A small cylindrical cologne bottle with a sleek glass body and a silver cap", size=[0.06, 0.06, 0.13], placements=[AssetInstance() for _ in range(1)])
painting_A = Assets(description="A single piece of thin and upright painting with a rectangular canvas, muted pastel colors, classic European style, featuring an intricate floral border.", size=[0.04, 0.80, 0.60], placements=[AssetInstance() for _ in range(1)])
eyeglasses_K = Assets(description="A pair of traditional European eyeglasses with thin rectangular frames, polished brass finish, and delicate filigree detailing on the temples", size=[0.05, 0.14, 0.03], placements=[AssetInstance() for _ in range(1)])
hook_F = Assets(description="A wall‑mounted coat hook with a slender metal arm, polished brass finish, classic European style, featuring an ornamental scroll at the base.", size=[0.11, 0.06, 0.14], placements=[AssetInstance() for _ in range(1)])
hook_G = Assets(description="A wall‑mounted coat hook with a slender metal arm, polished brass finish, classic European style, featuring an ornamental scroll at the base.", size=[0.11, 0.06, 0.14], placements=[AssetInstance() for _ in range(1)])
cologne_X = Assets(description="A sleek glass cologne bottle with a smooth cylindrical body, clear tinted amber glass, a brushed metal cap and a subtle curved shoulder for easy grip", size=[0.07, 0.07, 0.15], placements=[AssetInstance() for _ in range(1)])
sink_B = Assets(description="A rectangular porcelain sink with smooth rounded edges and a polished white finish, classic European style", size=[0.50, 0.65, 0.85], placements=[AssetInstance() for _ in range(1)])
cologne_Y = Assets(description="A sleek glass cologne bottle with a smooth cylindrical body, clear tinted amber glass, a brushed metal cap and a subtle curved shoulder for easy grip", size=[0.07, 0.07, 0.15], placements=[AssetInstance() for _ in range(1)])
locker_I = Assets(description="A wooden locker with ornate carvings, rectangular shape, dark walnut finish, classic European style, featuring brass handles and a slightly curved top.", size=[0.50, 0.60, 1.90], placements=[AssetInstance() for _ in range(1)])
eyeglasses_L = Assets(description="A pair of rectangular eyeglasses with thin matte black acetate frames, slightly rounded corners and clear lenses that catch the light", size=[0.05, 0.14, 0.04], placements=[AssetInstance() for _ in range(1)])
sink_C = Assets(description="A classic porcelain sink with a gently curving basin, smooth white finish and subtle fluted edges, embodying Traditional European style", size=[0.52, 0.68, 0.85], placements=[AssetInstance() for _ in range(1)])
eyeglasseslocker_C = Assets(description="A pair of slender metal‑framed eyeglasses with clear lenses, polished silver temples and a delicate bridge, reflecting a Traditional Classic European aesthetic.", size=[0.05, 0.14, 0.03], placements=[AssetInstance() for _ in range(1)])
comb_C = Assets(description="A small rectangular plastic comb with fine teeth and a smooth matte finish", size=[0.18, 0.04, 0.01], placements=[AssetInstance() for _ in range(1)])
comb_D = Assets(description="A plastic comb with a slender rectangular handle and evenly spaced thin teeth, glossy white finish and a subtle ergonomic curve at the base", size=[0.19, 0.04, 0.01], placements=[AssetInstance() for _ in range(1)])
wristwatch_H = Assets(description="A slim cylindrical wristwatch with a polished metal case and a dark leather strap", size=[0.21, 0.04, 0.01], placements=[AssetInstance() for _ in range(1)])
eyeglasses_M = Assets(description="A pair of lightweight eyeglasses with thin rectangular frames and clear lenses", size=[0.05, 0.14, 0.03], placements=[AssetInstance() for _ in range(1)])
towelrack_C = Assets(description="A wall‑mounted towel rack with a single curved rod, brushed bronze finish, classic European style, featuring decorative leaf motifs at each end.", size=[0.10, 0.70, 0.14], placements=[AssetInstance() for _ in range(1)])
cologne_Z = Assets(description="A glass perfume bottle with a slender cylindrical shape, clear with a polished cap, classic European design", size=[0.06, 0.06, 0.15], placements=[AssetInstance() for _ in range(1)])
locker_J = Assets(description="A wooden locker with ornate carvings, rectangular shape, dark walnut finish, classic European style, featuring brass handles and a slightly curved top.", size=[0.50, 0.60, 1.90], placements=[AssetInstance() for _ in range(1)])
cologne_group_2_A = Assets(description="A small glass cologne bottle with a sleek rectangular shape, clear finish and a subtle metallic cap, giving it a refined classic European look.", size=[0.04, 0.07, 0.12], placements=[AssetInstance() for _ in range(1)])
wristwatch_I = Assets(description="A slim cylindrical wristwatch with a polished metal case and a dark leather strap", size=[0.21, 0.04, 0.01], placements=[AssetInstance() for _ in range(1)])
lamp = Assets(description="A tall floor lamp with a slender cylindrical stand of brushed brass, topped by a conical fabric shade, classic European silhouette", size=[0.42, 0.42, 1.65], placements=[AssetInstance() for _ in range(1)])
eyeglasses_N = Assets(description="A delicate pair of eyeglasses with slender metal frames, featuring a rectangular lens shape and polished silver finish, embodying classic European elegance.", size=[0.05, 0.14, 0.03], placements=[AssetInstance() for _ in range(1)])
eyeglasses_O = Assets(description="A pair of rectangular eyeglasses with thin matte black acetate frames, slightly rounded corners and clear lenses that catch the light", size=[0.05, 0.14, 0.04], placements=[AssetInstance() for _ in range(1)])
cologne_group_2_B = Assets(description="A sleek glass cologne bottle with a smooth cylindrical body, clear tinted amber glass, a brushed metal cap and a subtle curved shoulder for easy grip", size=[0.07, 0.07, 0.15], placements=[AssetInstance() for _ in range(1)])
hairbrush_F = Assets(description="A compact hairbrush with a curved handle and soft bristles, finished in glossy white", size=[0.18, 0.07, 0.04], placements=[AssetInstance() for _ in range(1)])
cologne_group_2_C = Assets(description="A small cylindrical cologne bottle with a sleek glass body and a silver cap", size=[0.06, 0.06, 0.13], placements=[AssetInstance() for _ in range(1)])
sconce_B = Assets(description="A single piece of thin and upright wall sconce with an ornate bronze frame, curved glass shade, traditional European style", size=[0.14, 0.22, 0.42], placements=[AssetInstance() for _ in range(1)])
eyeglasseslocker_D = Assets(description="A pair of sleek metal eyeglasses with thin rectangular frames and clear lenses, finished in polished silver, classic European style", size=[0.05, 0.14, 0.03], placements=[AssetInstance() for _ in range(1)])
wristwatchlocker_E = Assets(description="A petite round wristwatch with a thin gold‑plated case, a simple white dial and a leather strap, embodying a refined Traditional Classic European look.", size=[0.20, 0.04, 0.01], placements=[AssetInstance() for _ in range(1)])
sink_center = Assets(description="A traditional porcelain sink with a gently rounded basin, smooth white glaze and subtle fluted edges, fitting a classic European bathroom", size=[0.52, 0.68, 0.85], placements=[AssetInstance() for _ in range(1)])
eyeglasses_P = Assets(description="A pair of rectangular eyeglasses with thin matte black acetate frames, slightly rounded corners and clear lenses that catch the light", size=[0.05, 0.14, 0.04], placements=[AssetInstance() for _ in range(1)])
locker_K = Assets(description="A wooden locker with ornate carvings, rectangular shape, dark walnut finish, classic European style, featuring brass handles and a slightly curved top.", size=[0.50, 0.60, 1.90], placements=[AssetInstance() for _ in range(1)])
eyeglasses_Q = Assets(description="A pair of lightweight eyeglasses with thin rectangular frames and clear lenses", size=[0.05, 0.14, 0.03], placements=[AssetInstance() for _ in range(1)])
cologne_group_2_D = Assets(description="A small glass cologne bottle with a sleek rectangular shape, clear finish and a subtle metallic cap, giving it a refined classic European look.", size=[0.04, 0.07, 0.12], placements=[AssetInstance() for _ in range(1)])
cologn = Assets(description="A glass perfume bottle with a slender cylindrical shape, clear with a polished silver cap, classic European design", size=[0.06, 0.06, 0.15], placements=[AssetInstance() for _ in range(1)])
hairbrush_G = Assets(description="A wooden hairbrush with a smooth oval handle, bristles of natural boar hair, light honey‑colored finish and a slightly tapered tip for precise styling", size=[0.22, 0.07, 0.04], placements=[AssetInstance() for _ in range(1)])
cologne_group_2_E = Assets(description="A glass perfume bottle with a slender cylindrical shape, clear with a polished cap, classic European design", size=[0.06, 0.06, 0.15], placements=[AssetInstance() for _ in range(1)])
cologne_group_2_F = Assets(description="A small glass cologne bottle with a sleek rectangular shape, clear finish and a subtle metallic cap, giving it a refined classic European look.", size=[0.04, 0.07, 0.12], placements=[AssetInstance() for _ in range(1)])
cologne_group_2_G = Assets(description="A small cylindrical cologne bottle with a sleek glass body and a silver cap", size=[0.06, 0.06, 0.13], placements=[AssetInstance() for _ in range(1)])
mirror = Assets(description="A single piece of thin and upright mirror with a rectangular shape, silver-framed border, and polished reflective surface, adding classic elegance.", size=[0.04, 0.90, 1.20], placements=[AssetInstance() for _ in range(1)])
comb_E = Assets(description="A small rectangular plastic comb with fine teeth and a smooth matte finish", size=[0.18, 0.04, 0.01], placements=[AssetInstance() for _ in range(1)])
sink_D = Assets(description="A rectangular ceramic sink with smooth rounded edges, glossy white finish and a subtle traditional moulding, fitting a Classic European bathroom style.", size=[0.50, 0.65, 0.85], placements=[AssetInstance() for _ in range(1)])
hook_H = Assets(description="A wall‑mounted coat hook with a slender metal arm, polished brass finish, classic European style, featuring an ornamental scroll at the base.", size=[0.11, 0.06, 0.14], placements=[AssetInstance() for _ in range(1)])
eyeglasses_R = Assets(description="A pair of lightweight eyeglasses with thin rectangular frames and clear lenses", size=[0.05, 0.14, 0.03], placements=[AssetInstance() for _ in range(1)])
painting_B = Assets(description="A single piece of thin and upright painting with a rectangular canvas, muted pastel colors, classic European style, featuring an intricate floral border.", size=[0.04, 0.80, 0.60], placements=[AssetInstance() for _ in range(1)])
eyeglasses_S = Assets(description="A pair of lightweight eyeglasses with thin rectangular frames and clear lenses", size=[0.05, 0.14, 0.03], placements=[AssetInstance() for _ in range(1)])
eyeglasses_T = Assets(description="A pair of rectangular eyeglasses with thin matte black acetate frames, slightly rounded corners and clear lenses that catch the light", size=[0.05, 0.14, 0.04], placements=[AssetInstance() for _ in range(1)])
eyeglasses_U = Assets(description="A pair of slender rectangular eyeglasses with thin metal frames, polished brass finish and clear lenses, reflecting a Traditional Classic European elegance", size=[0.05, 0.14, 0.03], placements=[AssetInstance() for _ in range(1)])
cologne_group_2_H = Assets(description="A sleek glass cologne bottle with a smooth cylindrical body, clear tinted amber glass, a brushed metal cap and a subtle curved shoulder for easy grip", size=[0.07, 0.07, 0.15], placements=[AssetInstance() for _ in range(1)])
hairbrush_H = Assets(description="A wooden hairbrush with a long slender handle and densely packed bristles, rectangular head, classic European finish", size=[0.24, 0.07, 0.04], placements=[AssetInstance() for _ in range(1)])

locker_A[0].instance_id = 'locker_A_0'
cologne_A[0].instance_id = 'cologne_A_0'
locker_B[0].instance_id = 'locker_B_0'
cologne_B[0].instance_id = 'cologne_B_0'
towelrack_A[0].instance_id = 'towelrack_A_0'
wristwatch_A[0].instance_id = 'wristwatch_A_0'
wristwatchlocker_A[0].instance_id = 'wristwatchlocker_A_0'
sconce_A[0].instance_id = 'sconce_A_0'
wristwatchlocker_B[0].instance_id = 'wristwatchlocker_B_0'
locker_C[0].instance_id = 'locker_C_0'
cologne_C[0].instance_id = 'cologne_C_0'
wristwatchlocker_C[0].instance_id = 'wristwatchlocker_C_0'
sink_A[0].instance_id = 'sink_A_0'
hairbrush_A[0].instance_id = 'hairbrush_A_0'
cologne_D[0].instance_id = 'cologne_D_0'
hook_A[0].instance_id = 'hook_A_0'
wristwatch_B[0].instance_id = 'wristwatch_B_0'
hairbrush_B[0].instance_id = 'hairbrush_B_0'
cologne_E[0].instance_id = 'cologne_E_0'
eyeglasses_A[0].instance_id = 'eyeglasses_A_0'
cologne_F[0].instance_id = 'cologne_F_0'
cologne_G[0].instance_id = 'cologne_G_0'
locker_D[0].instance_id = 'locker_D_0'
cologne_H[0].instance_id = 'cologne_H_0'
eyeglasses_B[0].instance_id = 'eyeglasses_B_0'
comb_A[0].instance_id = 'comb_A_0'
cologne_I[0].instance_id = 'cologne_I_0'
locker_E[0].instance_id = 'locker_E_0'
eyeglasses_C[0].instance_id = 'eyeglasses_C_0'
hairbrush_C[0].instance_id = 'hairbrush_C_0'
eyeglasses_D[0].instance_id = 'eyeglasses_D_0'
cologned_e7ba6c[0].instance_id = 'cologned_e7ba6c_0'
cologne_J[0].instance_id = 'cologne_J_0'
eyeglasseslocker_A[0].instance_id = 'eyeglasseslocker_A_0'
eyeglasses_E[0].instance_id = 'eyeglasses_E_0'
towelrack_B[0].instance_id = 'towelrack_B_0'
cologne_K[0].instance_id = 'cologne_K_0'
wristwatch_C[0].instance_id = 'wristwatch_C_0'
cologne_L[0].instance_id = 'cologne_L_0'
wristwatchlocker_D[0].instance_id = 'wristwatchlocker_D_0'
hook_B[0].instance_id = 'hook_B_0'
wristwatch_D[0].instance_id = 'wristwatch_D_0'
locker_F[0].instance_id = 'locker_F_0'
cologne_M[0].instance_id = 'cologne_M_0'
cologne_N[0].instance_id = 'cologne_N_0'
eyeglasses_F[0].instance_id = 'eyeglasses_F_0'
hairbrush_D[0].instance_id = 'hairbrush_D_0'
cologne_O[0].instance_id = 'cologne_O_0'
cologne_P[0].instance_id = 'cologne_P_0'
locker_G[0].instance_id = 'locker_G_0'
locker_H[0].instance_id = 'locker_H_0'
cologne_Q[0].instance_id = 'cologne_Q_0'
comb_B[0].instance_id = 'comb_B_0'
hook_C[0].instance_id = 'hook_C_0'
eyeglasseslocker_B[0].instance_id = 'eyeglasseslocker_B_0'
cologne_R[0].instance_id = 'cologne_R_0'
hairbrush_E[0].instance_id = 'hairbrush_E_0'
eyeglasses_G[0].instance_id = 'eyeglasses_G_0'
cologne_S[0].instance_id = 'cologne_S_0'
cologne_T[0].instance_id = 'cologne_T_0'
wristwatch_E[0].instance_id = 'wristwatch_E_0'
hook_D[0].instance_id = 'hook_D_0'
wristwatch_F[0].instance_id = 'wristwatch_F_0'
hook_E[0].instance_id = 'hook_E_0'
eyeglasses_H[0].instance_id = 'eyeglasses_H_0'
eyeglasses_I[0].instance_id = 'eyeglasses_I_0'
cologne_U[0].instance_id = 'cologne_U_0'
eyeglasses_J[0].instance_id = 'eyeglasses_J_0'
wristwatch_G[0].instance_id = 'wristwatch_G_0'
cologne_V[0].instance_id = 'cologne_V_0'
cologne_W[0].instance_id = 'cologne_W_0'
painting_A[0].instance_id = 'painting_A_0'
eyeglasses_K[0].instance_id = 'eyeglasses_K_0'
hook_F[0].instance_id = 'hook_F_0'
hook_G[0].instance_id = 'hook_G_0'
cologne_X[0].instance_id = 'cologne_X_0'
sink_B[0].instance_id = 'sink_B_0'
cologne_Y[0].instance_id = 'cologne_Y_0'
locker_I[0].instance_id = 'locker_I_0'
eyeglasses_L[0].instance_id = 'eyeglasses_L_0'
sink_C[0].instance_id = 'sink_C_0'
eyeglasseslocker_C[0].instance_id = 'eyeglasseslocker_C_0'
comb_C[0].instance_id = 'comb_C_0'
comb_D[0].instance_id = 'comb_D_0'
wristwatch_H[0].instance_id = 'wristwatch_H_0'
eyeglasses_M[0].instance_id = 'eyeglasses_M_0'
towelrack_C[0].instance_id = 'towelrack_C_0'
cologne_Z[0].instance_id = 'cologne_Z_0'
locker_J[0].instance_id = 'locker_J_0'
cologne_group_2_A[0].instance_id = 'cologne_group_2_A_0'
wristwatch_I[0].instance_id = 'wristwatch_I_0'
lamp[0].instance_id = 'lamp_0'
eyeglasses_N[0].instance_id = 'eyeglasses_N_0'
eyeglasses_O[0].instance_id = 'eyeglasses_O_0'
cologne_group_2_B[0].instance_id = 'cologne_group_2_B_0'
hairbrush_F[0].instance_id = 'hairbrush_F_0'
cologne_group_2_C[0].instance_id = 'cologne_group_2_C_0'
sconce_B[0].instance_id = 'sconce_B_0'
eyeglasseslocker_D[0].instance_id = 'eyeglasseslocker_D_0'
wristwatchlocker_E[0].instance_id = 'wristwatchlocker_E_0'
sink_center[0].instance_id = 'sink_center_0'
eyeglasses_P[0].instance_id = 'eyeglasses_P_0'
locker_K[0].instance_id = 'locker_K_0'
eyeglasses_Q[0].instance_id = 'eyeglasses_Q_0'
cologne_group_2_D[0].instance_id = 'cologne_group_2_D_0'
cologn[0].instance_id = 'cologn_0'
hairbrush_G[0].instance_id = 'hairbrush_G_0'
cologne_group_2_E[0].instance_id = 'cologne_group_2_E_0'
cologne_group_2_F[0].instance_id = 'cologne_group_2_F_0'
cologne_group_2_G[0].instance_id = 'cologne_group_2_G_0'
mirror[0].instance_id = 'mirror_0'
comb_E[0].instance_id = 'comb_E_0'
sink_D[0].instance_id = 'sink_D_0'
hook_H[0].instance_id = 'hook_H_0'
eyeglasses_R[0].instance_id = 'eyeglasses_R_0'
painting_B[0].instance_id = 'painting_B_0'
eyeglasses_S[0].instance_id = 'eyeglasses_S_0'
eyeglasses_T[0].instance_id = 'eyeglasses_T_0'
eyeglasses_U[0].instance_id = 'eyeglasses_U_0'
cologne_group_2_H[0].instance_id = 'cologne_group_2_H_0'
hairbrush_H[0].instance_id = 'hairbrush_H_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

locker_A[0].position = [0.4072738500850004, 0.14719344655675481, 0.95]
locker_A[0].rotation = [0, 0, 0]
cologne_A[0].position = [2.6228208326733133, 2.4087803958168967, 0.08]
cologne_A[0].rotation = [0, 0, 0]
locker_B[0].position = [4.659603388621309, 3.6561277728156463, 0.95]
locker_B[0].rotation = [0, 0, 0]
cologne_B[0].position = [2.5668048045318677, 0.7561161009251598, 0.075]
cologne_B[0].rotation = [0, 0, 0]
towelrack_A[0].position = [0.08178917630678684, 1.5842389466338895, 0.06]
towelrack_A[0].rotation = [0, 0, 0]
wristwatch_A[0].position = [4.7851800112119545, 2.9396125031285476, 0.0075]
wristwatch_A[0].rotation = [0, 0, 0]
wristwatchlocker_A[0].position = [4.971965251825193, 3.002826296765059, 0.006]
wristwatchlocker_A[0].rotation = [0, 0, 0]
sconce_A[0].position = [2.6061704886818013, 1.8146356766605818, 0.21]
sconce_A[0].rotation = [0, 0, 0]
wristwatchlocker_B[0].position = [1.1146109077818185, 1.6903402536666339, 0.006]
wristwatchlocker_B[0].rotation = [0, 0, 0]
locker_C[0].position = [2.653950145449311, 0.39129505434101874, 0.95]
locker_C[0].rotation = [0, 0, 0]
cologne_C[0].position = [4.481597073250319, 0.37405388801427586, 0.06]
cologne_C[0].rotation = [0, 0, 0]
wristwatchlocker_C[0].position = [2.3331318453338397, 3.5412732825832443, 0.006]
wristwatchlocker_C[0].rotation = [0, 0, 0]
sink_A[0].position = [4.001771901786676, 0.2836803039501756, 0.425]
sink_A[0].rotation = [0, 0, 0]
hairbrush_A[0].position = [4.77912936578489, 1.466232379410862, 0.0225]
hairbrush_A[0].rotation = [0, 0, 0]
cologne_D[0].position = [0.9089998130732829, 1.6760238550272488, 0.08]
cologne_D[0].rotation = [0, 0, 0]
hook_A[0].position = [0.029085472160594317, 3.0045816687841445, 0.07]
hook_A[0].rotation = [0, 0, 0]
wristwatch_B[0].position = [2.0657456286793794, 3.444814478185521, 0.0075]
wristwatch_B[0].rotation = [0, 0, 0]
hairbrush_B[0].position = [4.785368658642401, 0.5605840914075984, 0.0225]
hairbrush_B[0].rotation = [0, 0, 0]
cologne_E[0].position = [2.49249373538483, 0.5241528417805639, 0.075]
cologne_E[0].rotation = [0, 0, 0]
eyeglasses_A[0].position = [0.35740731671501436, 0.2361341701010451, 0.0175]
eyeglasses_A[0].rotation = [0, 0, 0]
cologne_F[0].position = [0.4678342596709334, 0.46310006694192785, 0.08]
cologne_F[0].rotation = [0, 0, 0]
cologne_G[0].position = [2.479320545022098, 1.9087931522016506, 0.075]
cologne_G[0].rotation = [0, 0, 0]
locker_D[0].position = [3.0109127036720356, 2.454166703935018, 0.95]
locker_D[0].rotation = [0, 0, 0]
cologne_H[0].position = [4.84459275451587, 3.5981606040461607, 0.06]
cologne_H[0].rotation = [0, 0, 0]
eyeglasses_B[0].position = [3.160170126718527, 3.6029285241061095, 0.0175]
eyeglasses_B[0].rotation = [0, 0, 0]
comb_A[0].position = [0.5866335286361729, 1.300610221384506, 0.003]
comb_A[0].rotation = [0, 0, 0]
cologne_I[0].position = [1.4558311669976876, 3.469788466022298, 0.075]
cologne_I[0].rotation = [0, 0, 0]
locker_E[0].position = [1.8840245895295493, 0.08759886280193063, 0.95]
locker_E[0].rotation = [0, 0, 0]
eyeglasses_C[0].position = [1.5991825280724326, 3.4302451153293365, 0.0175]
eyeglasses_C[0].rotation = [0, 0, 0]
hairbrush_C[0].position = [1.2356051572154203, 2.082133800630145, 0.0225]
hairbrush_C[0].rotation = [0, 0, 0]
eyeglasses_D[0].position = [2.6373099222521508, 3.5765758627060085, 0.02]
eyeglasses_D[0].rotation = [0, 0, 0]
cologned_e7ba6c[0].position = [1.3266617015630562, 0.5873002315224949, 0.065]
cologned_e7ba6c[0].rotation = [0, 0, 0]
cologne_J[0].position = [2.486130845336337, 3.922700185833812, 0.065]
cologne_J[0].rotation = [0, 0, 0]
eyeglasseslocker_A[0].position = [3.5049443488627596, 3.3888637535156243, 0.015]
eyeglasseslocker_A[0].rotation = [0, 0, 0]
eyeglasses_E[0].position = [1.3277903262057178, 0.2653462193738032, 0.015]
eyeglasses_E[0].rotation = [0, 0, 0]
towelrack_B[0].position = [0.9822028852364639, 1.153827876279618, 0.07]
towelrack_B[0].rotation = [0, 0, 0]
cologne_K[0].position = [3.7693849877583685, 2.6545069078257506, 0.075]
cologne_K[0].rotation = [0, 0, 0]
wristwatch_C[0].position = [2.991652923354474, 2.5706983617011407, 0.0075]
wristwatch_C[0].rotation = [0, 0, 0]
cologne_L[0].position = [2.54683613602036, 0.03973181385618929, 0.065]
cologne_L[0].rotation = [0, 0, 0]
wristwatchlocker_D[0].position = [0.4390625999681025, 1.6179540498412086, 0.006]
wristwatchlocker_D[0].rotation = [0, 0, 0]
hook_B[0].position = [4.679095535417871, 1.4657049722551987, 0.07]
hook_B[0].rotation = [0, 0, 0]
wristwatch_D[0].position = [2.06779991086289, 1.2544924803615376, 0.0075]
wristwatch_D[0].rotation = [0, 0, 0]
locker_F[0].position = [3.281609798392086, 0.7567836897000713, 0.95]
locker_F[0].rotation = [0, 0, 0]
cologne_M[0].position = [1.0504416498863112, 2.06218736351533, 0.075]
cologne_M[0].rotation = [0, 0, 0]
cologne_N[0].position = [2.559076897926383, 2.304203266272865, 0.08]
cologne_N[0].rotation = [0, 0, 0]
eyeglasses_F[0].position = [3.618579664267485, 3.5062161487884493, 0.0175]
eyeglasses_F[0].rotation = [0, 0, 0]
hairbrush_D[0].position = [4.76177878657716, 3.609103699410159, 0.0225]
hairbrush_D[0].rotation = [0, 0, 0]
cologne_O[0].position = [0.732114217975362, 1.2332232640561593, 0.06]
cologne_O[0].rotation = [0, 0, 0]
cologne_P[0].position = [0.5889496031551522, 1.3495826431670168, 0.08]
cologne_P[0].rotation = [0, 0, 0]
locker_G[0].position = [0.07210701718252832, 3.872322652533517, 0.95]
locker_G[0].rotation = [0, 0, 0]
locker_H[0].position = [0.6875500852847555, 0.03651800951122253, 0.95]
locker_H[0].rotation = [0, 0, 0]
cologne_Q[0].position = [2.6996436683902854, 2.5111966591937374, 0.075]
cologne_Q[0].rotation = [0, 0, 0]
comb_B[0].position = [4.183747657353743, 2.190971221739046, 0.003]
comb_B[0].rotation = [0, 0, 0]
hook_C[0].position = [4.0443670431112455, 3.205967318899469, 0.07]
hook_C[0].rotation = [0, 0, 0]
eyeglasseslocker_B[0].position = [4.218224789634056, 0.867509529513045, 0.015]
eyeglasseslocker_B[0].rotation = [0, 0, 0]
cologne_R[0].position = [1.2807206673367155, 0.9859371217721993, 0.075]
cologne_R[0].rotation = [0, 0, 0]
hairbrush_E[0].position = [2.2609765875126495, 1.2716086686744812, 0.0225]
hairbrush_E[0].rotation = [0, 0, 0]
eyeglasses_G[0].position = [3.586894282545688, 0.06458768749320631, 0.015]
eyeglasses_G[0].rotation = [0, 0, 0]
cologne_S[0].position = [0.30352082158252247, 3.908271070236394, 0.08]
cologne_S[0].rotation = [0, 0, 0]
cologne_T[0].position = [1.646996066421142, 3.784415678851048, 0.075]
cologne_T[0].rotation = [0, 0, 0]
wristwatch_E[0].position = [0.6449928847644637, 2.7087146204259436, 0.0075]
wristwatch_E[0].rotation = [0, 0, 0]
hook_D[0].position = [0.9698688695754898, 2.6367748885157853, 0.07]
hook_D[0].rotation = [0, 0, 0]
wristwatch_F[0].position = [2.569751210501627, 3.2712502965319628, 0.0075]
wristwatch_F[0].rotation = [0, 0, 0]
hook_E[0].position = [4.415080125812492, 3.9602735829870688, 0.07]
hook_E[0].rotation = [0, 0, 0]
eyeglasses_H[0].position = [2.669360258565328, 1.4457334963621884, 0.0175]
eyeglasses_H[0].rotation = [0, 0, 0]
eyeglasses_I[0].position = [1.482618091084702, 1.5422459541435183, 0.02]
eyeglasses_I[0].rotation = [0, 0, 0]
cologne_U[0].position = [0.6502948315563944, 1.3612154065567763, 0.06]
cologne_U[0].rotation = [0, 0, 0]
eyeglasses_J[0].position = [0.23600989961521435, 3.3548139800283954, 0.0175]
eyeglasses_J[0].rotation = [0, 0, 0]
wristwatch_G[0].position = [2.2722950391092747, 1.5220182892003664, 0.0075]
wristwatch_G[0].rotation = [0, 0, 0]
cologne_V[0].position = [0.30074818902412426, 1.6642965547931685, 0.065]
cologne_V[0].rotation = [0, 0, 0]
cologne_W[0].position = [2.6702514146171104, 3.5749834817317483, 0.065]
cologne_W[0].rotation = [0, 0, 0]
painting_A[0].position = [1.2270184710915726, 0.1660868939768041, 0.3]
painting_A[0].rotation = [0, 0, 0]
eyeglasses_K[0].position = [3.133085240204726, 3.576304666605733, 0.015]
eyeglasses_K[0].rotation = [0, 0, 0]
hook_F[0].position = [3.131254601313007, 2.206947344096111, 0.07]
hook_F[0].rotation = [0, 0, 0]
hook_G[0].position = [4.0750975965095035, 1.2695975496088336, 0.07]
hook_G[0].rotation = [0, 0, 0]
cologne_X[0].position = [1.1891921983006641, 0.05620764667924938, 0.075]
cologne_X[0].rotation = [0, 0, 0]
sink_B[0].position = [1.4104314788860017, 0.23517397854802757, 0.425]
sink_B[0].rotation = [0, 0, 0]
cologne_Y[0].position = [1.3856253577904465, 1.0305276130174894, 0.075]
cologne_Y[0].rotation = [0, 0, 0]
locker_I[0].position = [0.6980735177031056, 3.766307098138692, 0.95]
locker_I[0].rotation = [0, 0, 0]
eyeglasses_L[0].position = [1.154022055685953, 0.28987391177249444, 0.0175]
eyeglasses_L[0].rotation = [0, 0, 0]
sink_C[0].position = [1.9784544021251445, 2.8288157074673306, 0.425]
sink_C[0].rotation = [0, 0, 0]
eyeglasseslocker_C[0].position = [0.5893216236755622, 1.8895344806408212, 0.015]
eyeglasseslocker_C[0].rotation = [0, 0, 0]
comb_C[0].position = [4.504821992109393, 3.0376264150209766, 0.003]
comb_C[0].rotation = [0, 0, 0]
comb_D[0].position = [2.2543279278739465, 3.344744145147427, 0.0035]
comb_D[0].rotation = [0, 0, 0]
wristwatch_H[0].position = [0.3616654556806498, 2.982900166855387, 0.007]
wristwatch_H[0].rotation = [0, 0, 0]
eyeglasses_M[0].position = [4.350421786184136, 3.413551284787018, 0.015]
eyeglasses_M[0].rotation = [0, 0, 0]
towelrack_C[0].position = [4.633512872411587, 0.9729423422091221, 0.07]
towelrack_C[0].rotation = [0, 0, 0]
cologne_Z[0].position = [4.166365412938418, 0.5689704539210401, 0.075]
cologne_Z[0].rotation = [0, 0, 0]
locker_J[0].position = [1.6878583087214782, 2.4637759798647196, 0.95]
locker_J[0].rotation = [0, 0, 0]
cologne_group_2_A[0].position = [2.594248402901121, 0.2993167644552579, 0.06]
cologne_group_2_A[0].rotation = [0, 0, 0]
wristwatch_I[0].position = [1.5594612481034202, 1.6479336233480057, 0.007]
wristwatch_I[0].rotation = [0, 0, 0]
lamp[0].position = [2.962069876347689, 3.7138374570033323, 0.825]
lamp[0].rotation = [0, 0, 0]
eyeglasses_N[0].position = [0.5560192659086921, 3.6816155515938447, 0.015]
eyeglasses_N[0].rotation = [0, 0, 0]
eyeglasses_O[0].position = [3.336885428642047, 1.3696061472099799, 0.0175]
eyeglasses_O[0].rotation = [0, 0, 0]
cologne_group_2_B[0].position = [1.328771107877675, 3.2870776894940934, 0.075]
cologne_group_2_B[0].rotation = [0, 0, 0]
hairbrush_F[0].position = [4.965748168461265, 3.9847977600195432, 0.0225]
hairbrush_F[0].rotation = [0, 0, 0]
cologne_group_2_C[0].position = [2.9310451933155637, 0.9098702629501845, 0.065]
cologne_group_2_C[0].rotation = [0, 0, 0]
sconce_B[0].position = [0.4257481982734562, 2.7172174310809876, 0.21]
sconce_B[0].rotation = [0, 0, 0]
eyeglasseslocker_D[0].position = [2.320323151666171, 1.4894096401374464, 0.015]
eyeglasseslocker_D[0].rotation = [0, 0, 0]
wristwatchlocker_E[0].position = [1.6643293567663457, 3.030191187167684, 0.006]
wristwatchlocker_E[0].rotation = [0, 0, 0]
sink_center[0].position = [4.475803005356492, 2.5084034097722037, 0.425]
sink_center[0].rotation = [0, 0, 0]
eyeglasses_P[0].position = [0.8710167994436852, 3.0592516239969907, 0.0175]
eyeglasses_P[0].rotation = [0, 0, 0]
locker_K[0].position = [1.6282551008813169, 1.652254611958762, 0.95]
locker_K[0].rotation = [0, 0, 0]
eyeglasses_Q[0].position = [2.67692662862294, 2.6527708840308875, 0.015]
eyeglasses_Q[0].rotation = [0, 0, 0]
cologne_group_2_D[0].position = [3.563931372879983, 3.4069007006070273, 0.06]
cologne_group_2_D[0].rotation = [0, 0, 0]
cologn[0].position = [2.1394578788422742, 2.3354571787905414, 0.075]
cologn[0].rotation = [0, 0, 0]
hairbrush_G[0].position = [4.49976814409305, 1.1942543640108298, 0.0225]
hairbrush_G[0].rotation = [0, 0, 0]
cologne_group_2_E[0].position = [2.11646464926897, 1.3076471171474573, 0.075]
cologne_group_2_E[0].rotation = [0, 0, 0]
cologne_group_2_F[0].position = [3.4889352878795634, 3.003589390730297, 0.06]
cologne_group_2_F[0].rotation = [0, 0, 0]
cologne_group_2_G[0].position = [1.804190526086944, 0.4849228423628915, 0.065]
cologne_group_2_G[0].rotation = [0, 0, 0]
mirror[0].position = [4.447743203128778, 1.072531223848085, 0.6]
mirror[0].rotation = [0, 0, 0]
comb_E[0].position = [2.9632208029633595, 2.830785138593414, 0.003]
comb_E[0].rotation = [0, 0, 0]
sink_D[0].position = [3.595818149379275, 3.598213947735596, 0.425]
sink_D[0].rotation = [0, 0, 0]
hook_H[0].position = [2.5227605257693186, 0.6892724423536882, 0.07]
hook_H[0].rotation = [0, 0, 0]
eyeglasses_R[0].position = [0.05397626418247703, 3.567573405715038, 0.015]
eyeglasses_R[0].rotation = [0, 0, 0]
painting_B[0].position = [4.634576232497336, 3.2712815708552614, 0.3]
painting_B[0].rotation = [0, 0, 0]
eyeglasses_S[0].position = [2.939570354790983, 3.979385984396644, 0.015]
eyeglasses_S[0].rotation = [0, 0, 0]
eyeglasses_T[0].position = [2.579596879655793, 2.885593909485982, 0.0175]
eyeglasses_T[0].rotation = [0, 0, 0]
eyeglasses_U[0].position = [4.9446277702837325, 3.282068484888782, 0.015]
eyeglasses_U[0].rotation = [0, 0, 0]
cologne_group_2_H[0].position = [1.3029426214846946, 3.7848425439849467, 0.075]
cologne_group_2_H[0].rotation = [0, 0, 0]
hairbrush_H[0].position = [0.5959045797052964, 0.1638662646461282, 0.0225]
hairbrush_H[0].rotation = [0, 0, 0]
locker_A[0].position = [0.4072738500850004, 0.14719344655675481, 0.95]
locker_A[0].rotation = [0, 0, 0]
cologne_A[0].position = [2.6228208326733133, 2.4087803958168967, 0.08]
cologne_A[0].rotation = [0, 0, 0]
locker_B[0].position = [4.659603388621309, 3.6561277728156463, 0.95]
locker_B[0].rotation = [0, 0, 0]
cologne_B[0].position = [2.5668048045318677, 0.7561161009251598, 0.075]
cologne_B[0].rotation = [0, 0, 0]
towelrack_A[0].position = [0.08178917630678684, 1.5842389466338895, 0.06]
towelrack_A[0].rotation = [0, 0, 0]
wristwatch_A[0].position = [4.7851800112119545, 2.9396125031285476, 0.0075]
wristwatch_A[0].rotation = [0, 0, 0]
wristwatchlocker_A[0].position = [4.971965251825193, 3.002826296765059, 0.006]
wristwatchlocker_A[0].rotation = [0, 0, 0]
sconce_A[0].position = [2.6061704886818013, 1.8146356766605818, 0.21]
sconce_A[0].rotation = [0, 0, 0]
wristwatchlocker_B[0].position = [1.1146109077818185, 1.6903402536666339, 0.006]
wristwatchlocker_B[0].rotation = [0, 0, 0]
locker_C[0].position = [2.653950145449311, 0.39129505434101874, 0.95]
locker_C[0].rotation = [0, 0, 0]
cologne_C[0].position = [4.481597073250319, 0.37405388801427586, 0.06]
cologne_C[0].rotation = [0, 0, 0]
wristwatchlocker_C[0].position = [2.3331318453338397, 3.5412732825832443, 0.006]
wristwatchlocker_C[0].rotation = [0, 0, 0]
sink_A[0].position = [4.001771901786676, 0.2836803039501756, 0.425]
sink_A[0].rotation = [0, 0, 0]
hairbrush_A[0].position = [4.77912936578489, 1.466232379410862, 0.0225]
hairbrush_A[0].rotation = [0, 0, 0]
cologne_D[0].position = [0.9089998130732829, 1.6760238550272488, 0.08]
cologne_D[0].rotation = [0, 0, 0]
hook_A[0].position = [0.029085472160594317, 3.0045816687841445, 0.07]
hook_A[0].rotation = [0, 0, 0]
wristwatch_B[0].position = [2.0657456286793794, 3.444814478185521, 0.0075]
wristwatch_B[0].rotation = [0, 0, 0]
hairbrush_B[0].position = [4.785368658642401, 0.5605840914075984, 0.0225]
hairbrush_B[0].rotation = [0, 0, 0]
cologne_E[0].position = [2.49249373538483, 0.5241528417805639, 0.075]
cologne_E[0].rotation = [0, 0, 0]
eyeglasses_A[0].position = [0.35740731671501436, 0.2361341701010451, 0.0175]
eyeglasses_A[0].rotation = [0, 0, 0]
cologne_F[0].position = [0.4678342596709334, 0.46310006694192785, 0.08]
cologne_F[0].rotation = [0, 0, 0]
cologne_G[0].position = [2.479320545022098, 1.9087931522016506, 0.075]
cologne_G[0].rotation = [0, 0, 0]
locker_D[0].position = [3.0109127036720356, 2.454166703935018, 0.95]
locker_D[0].rotation = [0, 0, 0]
cologne_H[0].position = [4.84459275451587, 3.5981606040461607, 0.06]
cologne_H[0].rotation = [0, 0, 0]
eyeglasses_B[0].position = [3.160170126718527, 3.6029285241061095, 0.0175]
eyeglasses_B[0].rotation = [0, 0, 0]
comb_A[0].position = [0.5866335286361729, 1.300610221384506, 0.003]
comb_A[0].rotation = [0, 0, 0]
cologne_I[0].position = [1.4558311669976876, 3.469788466022298, 0.075]
cologne_I[0].rotation = [0, 0, 0]
locker_E[0].position = [1.8840245895295493, 0.08759886280193063, 0.95]
locker_E[0].rotation = [0, 0, 0]
eyeglasses_C[0].position = [1.5991825280724326, 3.4302451153293365, 0.0175]
eyeglasses_C[0].rotation = [0, 0, 0]
hairbrush_C[0].position = [1.2356051572154203, 2.082133800630145, 0.0225]
hairbrush_C[0].rotation = [0, 0, 0]
eyeglasses_D[0].position = [2.6373099222521508, 3.5765758627060085, 0.02]
eyeglasses_D[0].rotation = [0, 0, 0]
cologned_e7ba6c[0].position = [1.3266617015630562, 0.5873002315224949, 0.065]
cologned_e7ba6c[0].rotation = [0, 0, 0]
cologne_J[0].position = [2.486130845336337, 3.922700185833812, 0.065]
cologne_J[0].rotation = [0, 0, 0]
eyeglasseslocker_A[0].position = [3.5049443488627596, 3.3888637535156243, 0.015]
eyeglasseslocker_A[0].rotation = [0, 0, 0]
eyeglasses_E[0].position = [1.3277903262057178, 0.2653462193738032, 0.015]
eyeglasses_E[0].rotation = [0, 0, 0]
towelrack_B[0].position = [0.9822028852364639, 1.153827876279618, 0.07]
towelrack_B[0].rotation = [0, 0, 0]
cologne_K[0].position = [3.7693849877583685, 2.6545069078257506, 0.075]
cologne_K[0].rotation = [0, 0, 0]
wristwatch_C[0].position = [2.991652923354474, 2.5706983617011407, 0.0075]
wristwatch_C[0].rotation = [0, 0, 0]
cologne_L[0].position = [2.54683613602036, 0.03973181385618929, 0.065]
cologne_L[0].rotation = [0, 0, 0]
wristwatchlocker_D[0].position = [0.4390625999681025, 1.6179540498412086, 0.006]
wristwatchlocker_D[0].rotation = [0, 0, 0]
hook_B[0].position = [4.679095535417871, 1.4657049722551987, 0.07]
hook_B[0].rotation = [0, 0, 0]
wristwatch_D[0].position = [2.06779991086289, 1.2544924803615376, 0.0075]
wristwatch_D[0].rotation = [0, 0, 0]
locker_F[0].position = [3.281609798392086, 0.7567836897000713, 0.95]
locker_F[0].rotation = [0, 0, 0]
cologne_M[0].position = [1.0504416498863112, 2.06218736351533, 0.075]
cologne_M[0].rotation = [0, 0, 0]
cologne_N[0].position = [2.559076897926383, 2.304203266272865, 0.08]
cologne_N[0].rotation = [0, 0, 0]
eyeglasses_F[0].position = [3.618579664267485, 3.5062161487884493, 0.0175]
eyeglasses_F[0].rotation = [0, 0, 0]
hairbrush_D[0].position = [4.76177878657716, 3.609103699410159, 0.0225]
hairbrush_D[0].rotation = [0, 0, 0]
cologne_O[0].position = [0.732114217975362, 1.2332232640561593, 0.06]
cologne_O[0].rotation = [0, 0, 0]
cologne_P[0].position = [0.5889496031551522, 1.3495826431670168, 0.08]
cologne_P[0].rotation = [0, 0, 0]
locker_G[0].position = [0.07210701718252832, 3.872322652533517, 0.95]
locker_G[0].rotation = [0, 0, 0]
locker_H[0].position = [0.6875500852847555, 0.03651800951122253, 0.95]
locker_H[0].rotation = [0, 0, 0]
cologne_Q[0].position = [2.6996436683902854, 2.5111966591937374, 0.075]
cologne_Q[0].rotation = [0, 0, 0]
comb_B[0].position = [4.183747657353743, 2.190971221739046, 0.003]
comb_B[0].rotation = [0, 0, 0]
hook_C[0].position = [4.0443670431112455, 3.205967318899469, 0.07]
hook_C[0].rotation = [0, 0, 0]
eyeglasseslocker_B[0].position = [4.218224789634056, 0.867509529513045, 0.015]
eyeglasseslocker_B[0].rotation = [0, 0, 0]
cologne_R[0].position = [1.2807206673367155, 0.9859371217721993, 0.075]
cologne_R[0].rotation = [0, 0, 0]
hairbrush_E[0].position = [2.2609765875126495, 1.2716086686744812, 0.0225]
hairbrush_E[0].rotation = [0, 0, 0]
eyeglasses_G[0].position = [3.586894282545688, 0.06458768749320631, 0.015]
eyeglasses_G[0].rotation = [0, 0, 0]
cologne_S[0].position = [0.30352082158252247, 3.908271070236394, 0.08]
cologne_S[0].rotation = [0, 0, 0]
cologne_T[0].position = [1.646996066421142, 3.784415678851048, 0.075]
cologne_T[0].rotation = [0, 0, 0]
wristwatch_E[0].position = [0.6449928847644637, 2.7087146204259436, 0.0075]
wristwatch_E[0].rotation = [0, 0, 0]
hook_D[0].position = [0.9698688695754898, 2.6367748885157853, 0.07]
hook_D[0].rotation = [0, 0, 0]
wristwatch_F[0].position = [2.569751210501627, 3.2712502965319628, 0.0075]
wristwatch_F[0].rotation = [0, 0, 0]
hook_E[0].position = [4.415080125812492, 3.9602735829870688, 0.07]
hook_E[0].rotation = [0, 0, 0]
eyeglasses_H[0].position = [2.669360258565328, 1.4457334963621884, 0.0175]
eyeglasses_H[0].rotation = [0, 0, 0]
eyeglasses_I[0].position = [1.482618091084702, 1.5422459541435183, 0.02]
eyeglasses_I[0].rotation = [0, 0, 0]
cologne_U[0].position = [0.6502948315563944, 1.3612154065567763, 0.06]
cologne_U[0].rotation = [0, 0, 0]
eyeglasses_J[0].position = [0.23600989961521435, 3.3548139800283954, 0.0175]
eyeglasses_J[0].rotation = [0, 0, 0]
wristwatch_G[0].position = [2.2722950391092747, 1.5220182892003664, 0.0075]
wristwatch_G[0].rotation = [0, 0, 0]
cologne_V[0].position = [0.30074818902412426, 1.6642965547931685, 0.065]
cologne_V[0].rotation = [0, 0, 0]
cologne_W[0].position = [2.6702514146171104, 3.5749834817317483, 0.065]
cologne_W[0].rotation = [0, 0, 0]
painting_A[0].position = [1.2270184710915726, 0.1660868939768041, 0.3]
painting_A[0].rotation = [0, 0, 0]
eyeglasses_K[0].position = [3.133085240204726, 3.576304666605733, 0.015]
eyeglasses_K[0].rotation = [0, 0, 0]
hook_F[0].position = [3.131254601313007, 2.206947344096111, 0.07]
hook_F[0].rotation = [0, 0, 0]
hook_G[0].position = [4.0750975965095035, 1.2695975496088336, 0.07]
hook_G[0].rotation = [0, 0, 0]
cologne_X[0].position = [1.1891921983006641, 0.05620764667924938, 0.075]
cologne_X[0].rotation = [0, 0, 0]
sink_B[0].position = [1.4104314788860017, 0.23517397854802757, 0.425]
sink_B[0].rotation = [0, 0, 0]
cologne_Y[0].position = [1.3856253577904465, 1.0305276130174894, 0.075]
cologne_Y[0].rotation = [0, 0, 0]
locker_I[0].position = [0.6980735177031056, 3.766307098138692, 0.95]
locker_I[0].rotation = [0, 0, 0]
eyeglasses_L[0].position = [1.154022055685953, 0.28987391177249444, 0.0175]
eyeglasses_L[0].rotation = [0, 0, 0]
sink_C[0].position = [1.9784544021251445, 2.8288157074673306, 0.425]
sink_C[0].rotation = [0, 0, 0]
eyeglasseslocker_C[0].position = [0.5893216236755622, 1.8895344806408212, 0.015]
eyeglasseslocker_C[0].rotation = [0, 0, 0]
comb_C[0].position = [4.504821992109393, 3.0376264150209766, 0.003]
comb_C[0].rotation = [0, 0, 0]
comb_D[0].position = [2.2543279278739465, 3.344744145147427, 0.0035]
comb_D[0].rotation = [0, 0, 0]
wristwatch_H[0].position = [0.3616654556806498, 2.982900166855387, 0.007]
wristwatch_H[0].rotation = [0, 0, 0]
eyeglasses_M[0].position = [4.350421786184136, 3.413551284787018, 0.015]
eyeglasses_M[0].rotation = [0, 0, 0]
towelrack_C[0].position = [4.633512872411587, 0.9729423422091221, 0.07]
towelrack_C[0].rotation = [0, 0, 0]
cologne_Z[0].position = [4.166365412938418, 0.5689704539210401, 0.075]
cologne_Z[0].rotation = [0, 0, 0]
locker_J[0].position = [1.6878583087214782, 2.4637759798647196, 0.95]
locker_J[0].rotation = [0, 0, 0]
cologne_group_2_A[0].position = [2.594248402901121, 0.2993167644552579, 0.06]
cologne_group_2_A[0].rotation = [0, 0, 0]
wristwatch_I[0].position = [1.5594612481034202, 1.6479336233480057, 0.007]
wristwatch_I[0].rotation = [0, 0, 0]
lamp[0].position = [2.962069876347689, 3.7138374570033323, 0.825]
lamp[0].rotation = [0, 0, 0]
eyeglasses_N[0].position = [0.5560192659086921, 3.6816155515938447, 0.015]
eyeglasses_N[0].rotation = [0, 0, 0]
eyeglasses_O[0].position = [3.336885428642047, 1.3696061472099799, 0.0175]
eyeglasses_O[0].rotation = [0, 0, 0]
cologne_group_2_B[0].position = [1.328771107877675, 3.2870776894940934, 0.075]
cologne_group_2_B[0].rotation = [0, 0, 0]
hairbrush_F[0].position = [4.965748168461265, 3.9847977600195432, 0.0225]
hairbrush_F[0].rotation = [0, 0, 0]
cologne_group_2_C[0].position = [2.9310451933155637, 0.9098702629501845, 0.065]
cologne_group_2_C[0].rotation = [0, 0, 0]
sconce_B[0].position = [0.4257481982734562, 2.7172174310809876, 0.21]
sconce_B[0].rotation = [0, 0, 0]
eyeglasseslocker_D[0].position = [2.320323151666171, 1.4894096401374464, 0.015]
eyeglasseslocker_D[0].rotation = [0, 0, 0]
wristwatchlocker_E[0].position = [1.6643293567663457, 3.030191187167684, 0.006]
wristwatchlocker_E[0].rotation = [0, 0, 0]
sink_center[0].position = [4.475803005356492, 2.5084034097722037, 0.425]
sink_center[0].rotation = [0, 0, 0]
eyeglasses_P[0].position = [0.8710167994436852, 3.0592516239969907, 0.0175]
eyeglasses_P[0].rotation = [0, 0, 0]
locker_K[0].position = [1.6282551008813169, 1.652254611958762, 0.95]
locker_K[0].rotation = [0, 0, 0]
eyeglasses_Q[0].position = [2.67692662862294, 2.6527708840308875, 0.015]
eyeglasses_Q[0].rotation = [0, 0, 0]
cologne_group_2_D[0].position = [3.563931372879983, 3.4069007006070273, 0.06]
cologne_group_2_D[0].rotation = [0, 0, 0]
cologn[0].position = [2.1394578788422742, 2.3354571787905414, 0.075]
cologn[0].rotation = [0, 0, 0]
hairbrush_G[0].position = [4.49976814409305, 1.1942543640108298, 0.0225]
hairbrush_G[0].rotation = [0, 0, 0]
cologne_group_2_E[0].position = [2.11646464926897, 1.3076471171474573, 0.075]
cologne_group_2_E[0].rotation = [0, 0, 0]
cologne_group_2_F[0].position = [3.4889352878795634, 3.003589390730297, 0.06]
cologne_group_2_F[0].rotation = [0, 0, 0]
cologne_group_2_G[0].position = [1.804190526086944, 0.4849228423628915, 0.065]
cologne_group_2_G[0].rotation = [0, 0, 0]
mirror[0].position = [4.447743203128778, 1.072531223848085, 0.6]
mirror[0].rotation = [0, 0, 0]
comb_E[0].position = [2.9632208029633595, 2.830785138593414, 0.003]
comb_E[0].rotation = [0, 0, 0]
sink_D[0].position = [3.595818149379275, 3.598213947735596, 0.425]
sink_D[0].rotation = [0, 0, 0]
hook_H[0].position = [2.5227605257693186, 0.6892724423536882, 0.07]
hook_H[0].rotation = [0, 0, 0]
eyeglasses_R[0].position = [0.05397626418247703, 3.567573405715038, 0.015]
eyeglasses_R[0].rotation = [0, 0, 0]
painting_B[0].position = [4.634576232497336, 3.2712815708552614, 0.3]
painting_B[0].rotation = [0, 0, 0]
eyeglasses_S[0].position = [2.939570354790983, 3.979385984396644, 0.015]
eyeglasses_S[0].rotation = [0, 0, 0]
eyeglasses_T[0].position = [2.579596879655793, 2.885593909485982, 0.0175]
eyeglasses_T[0].rotation = [0, 0, 0]
eyeglasses_U[0].position = [4.9446277702837325, 3.282068484888782, 0.015]
eyeglasses_U[0].rotation = [0, 0, 0]
cologne_group_2_H[0].position = [1.3029426214846946, 3.7848425439849467, 0.075]
cologne_group_2_H[0].rotation = [0, 0, 0]
hairbrush_H[0].position = [0.5959045797052964, 0.1638662646461282, 0.0225]
hairbrush_H[0].rotation = [0, 0, 0]

solver.constraints = []

# Helper functions keep every placement explicit while ensuring that each new
# instance receives both a position-based and an orientation-based constraint.
def place_floor_asset(asset, position, yaw, wall):
    instance = asset[0]
    instance.position = position
    instance.rotation = [0, 0, yaw]

    # Wall contact is the primary positional relationship for perimeter fixtures.
    solver.against_wall(instance, wall)
    solver.distance_constraint(
        instance,
        AssetInstance(position=position),
        0,
        0,
        weight=10,
    )
    solver.align_with(
        instance,
        AssetInstance(position=position, rotation=[0, 0, yaw]),
    )


def place_wall_asset(asset, position, yaw, wall):
    instance = asset[0]
    instance.position = position
    instance.rotation = [0, 0, yaw]

    solver.against_wall(instance, wall)
    solver.distance_constraint(
        instance,
        AssetInstance(position=position),
        0,
        0,
        weight=10,
    )
    solver.align_with(
        instance,
        AssetInstance(position=position, rotation=[0, 0, yaw]),
    )


def place_surface_asset(asset, supporting_asset, offset, yaw):
    instance = asset[0]
    support = supporting_asset[0]

    # The initial z value is the exact top-contact height. The on_top_of
    # constraint will maintain this relationship if the layout is adjusted.
    position = [
        support.position[0] + offset[0],
        support.position[1] + offset[1],
        support.position[2] + supporting_asset.size[2] / 2 + asset.size[2] / 2,
    ]
    instance.position = position
    instance.rotation = [0, 0, yaw]

    solver.on_top_of(instance, support)
    solver.distance_constraint(
        instance,
        AssetInstance(position=position),
        0,
        0,
        weight=10,
    )
    solver.align_with(instance, support)


# ---------------------------------------------------------------------------
# Floor-standing assets
#
# The east-wall doorway occupies y=1.42 through y=2.32. No floor-standing
# object is placed in that interval or immediately in front of it.
# ---------------------------------------------------------------------------

# Six lockers form an evenly spaced run against the south wall.
place_floor_asset(locker_A, [0.90, 0.30, 0.95], radians(90), walls[0])
place_floor_asset(locker_B, [1.45, 0.30, 0.95], radians(90), walls[0])
place_floor_asset(locker_C, [2.00, 0.30, 0.95], radians(90), walls[0])
place_floor_asset(locker_D, [2.55, 0.30, 0.95], radians(90), walls[0])
place_floor_asset(locker_E, [3.10, 0.30, 0.95], radians(90), walls[0])
place_floor_asset(locker_F, [3.65, 0.30, 0.95], radians(90), walls[0])

# Northern run. sink_center lies directly between locker_G and locker_I.
# locker_H touches locker_G at a center distance of exactly 0.50 m.
place_floor_asset(locker_H, [2.80, 3.70, 0.95], radians(-90), walls[2])
place_floor_asset(locker_G, [3.30, 3.70, 0.95], radians(-90), walls[2])
place_floor_asset(sink_center, [3.86, 3.66, 0.425], radians(-90), walls[2])
place_floor_asset(locker_I, [4.42, 3.70, 0.95], radians(-90), walls[2])

# Additional lockers occupy wall sections away from the doorway.
place_floor_asset(locker_J, [0.30, 3.25, 0.95], 0, walls[3])
place_floor_asset(locker_K, [4.70, 0.45, 0.95], radians(180), walls[1])

# Four sinks form a practical plumbing run along the west wall.
place_floor_asset(sink_A, [0.325, 0.38, 0.425], 0, walls[3])
place_floor_asset(sink_B, [0.325, 1.08, 0.425], 0, walls[3])
place_floor_asset(sink_C, [0.34, 1.78, 0.425], 0, walls[3])
place_floor_asset(sink_D, [0.325, 2.48, 0.425], 0, walls[3])

# The lamp fills the northeast wall section beyond the door-swing clearance.
place_floor_asset(lamp, [4.79, 2.85, 0.825], radians(180), walls[1])

# High-priority semantic relationships requested in the layout criteria.
solver.distance_constraint(locker_G[0], locker_H[0], 0.50, 0.50, weight=10)
solver.distance_constraint(sink_center[0], locker_G[0], 0.55, 0.58, weight=10)
solver.distance_constraint(sink_center[0], locker_I[0], 0.55, 0.58, weight=10)


# ---------------------------------------------------------------------------
# Wall-mounted assets
#
# These are mounted above the 1.90 m lockers where necessary, so their
# bounding boxes do not intersect the floor-standing furniture.
# ---------------------------------------------------------------------------

place_wall_asset(towelrack_A, [0.04, 0.80, 2.18], 0, walls[3])
place_wall_asset(towelrack_B, [0.04, 1.70, 2.18], 0, walls[3])
place_wall_asset(towelrack_C, [0.04, 2.60, 2.18], 0, walls[3])

place_wall_asset(sconce_A, [4.93, 2.65, 2.35], radians(180), walls[1])
place_wall_asset(sconce_B, [4.93, 3.08, 2.35], radians(180), walls[1])

place_wall_asset(hook_A, [0.40, 0.03, 2.15], radians(90), walls[0])
place_wall_asset(hook_B, [0.80, 0.03, 2.15], radians(90), walls[0])
place_wall_asset(hook_C, [1.20, 0.03, 2.15], radians(90), walls[0])
place_wall_asset(hook_D, [1.60, 0.03, 2.15], radians(90), walls[0])
place_wall_asset(hook_E, [2.40, 3.97, 2.15], radians(-90), walls[2])
place_wall_asset(hook_F, [2.00, 3.97, 2.15], radians(-90), walls[2])
place_wall_asset(hook_G, [1.60, 3.97, 2.15], radians(-90), walls[2])
place_wall_asset(hook_H, [1.20, 3.97, 2.15], radians(-90), walls[2])

place_wall_asset(painting_A, [0.03, 1.15, 2.65], 0, walls[3])
place_wall_asset(painting_B, [0.03, 2.85, 2.65], 0, walls[3])
place_wall_asset(mirror, [4.97, 3.55, 2.65], radians(180), walls[1])


# ---------------------------------------------------------------------------
# Small tabletop assets
#
# Objects are distributed over the locker tops in compact two-column grids.
# The offsets leave room between neighboring objects and keep all objects
# within the supporting locker tops.
# ---------------------------------------------------------------------------

supporting_lockers = [
    locker_A,
    locker_B,
    locker_C,
    locker_D,
    locker_E,
    locker_F,
    locker_G,
    locker_H,
    locker_I,
    locker_J,
    locker_K,
]

surface_slots = [
    [-0.14, -0.18],
    [0.14, -0.18],
    [-0.14, -0.06],
    [0.14, -0.06],
    [-0.14, 0.06],
    [0.14, 0.06],
    [-0.14, 0.18],
    [0.14, 0.18],
]

small_assets = [
    cologne_A,
    cologne_B,
    wristwatch_A,
    wristwatchlocker_A,
    wristwatchlocker_B,
    cologne_C,
    wristwatchlocker_C,
    hairbrush_A,
    cologne_D,
    wristwatch_B,
    hairbrush_B,
    cologne_E,
    eyeglasses_A,
    cologne_F,
    cologne_G,
    cologne_H,
    eyeglasses_B,
    comb_A,
    cologne_I,
    eyeglasses_C,
    hairbrush_C,
    eyeglasses_D,
    cologned_e7ba6c,
    cologne_J,
    eyeglasseslocker_A,
    eyeglasses_E,
    cologne_K,
    wristwatch_C,
    cologne_L,
    wristwatchlocker_D,
    wristwatch_D,
    cologne_M,
    cologne_N,
    eyeglasses_F,
    hairbrush_D,
    cologne_O,
    cologne_P,
    cologne_Q,
    comb_B,
    eyeglasseslocker_B,
    cologne_R,
    hairbrush_E,
    eyeglasses_G,
    cologne_S,
    cologne_T,
    wristwatch_E,
    wristwatch_F,
    eyeglasses_H,
    eyeglasses_I,
    cologne_U,
    eyeglasses_J,
    wristwatch_G,
    cologne_V,
    cologne_W,
    eyeglasses_K,
    cologne_X,
    cologne_Y,
    eyeglasses_L,
    eyeglasseslocker_C,
    comb_C,
    comb_D,
    wristwatch_H,
    eyeglasses_M,
    cologne_Z,
    cologne_group_2_A,
    wristwatch_I,
    eyeglasses_N,
    eyeglasses_O,
    cologne_group_2_B,
    hairbrush_F,
    cologne_group_2_C,
    eyeglasseslocker_D,
    wristwatchlocker_E,
    eyeglasses_P,
    eyeglasses_Q,
    cologne_group_2_D,
    cologn,
    hairbrush_G,
    cologne_group_2_E,
    cologne_group_2_F,
    cologne_group_2_G,
    comb_E,
    eyeglasses_R,
    eyeglasses_T,
    eyeglasses_U,
    cologne_group_2_H,
    hairbrush_H,
]

for small_index, small_asset in enumerate(small_assets):
    support_index = small_index % len(supporting_lockers)
    slot_index = small_index // len(supporting_lockers)
    support_asset = supporting_lockers[support_index]
    slot = surface_slots[slot_index]

    place_surface_asset(
        small_asset,
        support_asset,
        slot,
        support_asset[0].rotation[2],
    )

# o0116 is eyeglasses_S and o0009 is locker_C. This explicit placement is
# kept separate so their required support relationship cannot be obscured by
# the general distribution loop.
place_surface_asset(
    eyeglasses_S,
    locker_C,
    [0.00, 0.18],
    locker_C[0].rotation[2],
)

solver.constraints = []
wristwatch_B[0].position = [0.1599999964237213, 3.069999933242798, 1.9049999713897705]
wristwatch_B[0].rotation = [0, 0, 0.022791285064511058]
wristwatch_B[0].optimize = 2
cologne_B[0].position = [1.309999942779541, 0.11999999731779099, 1.975000023841858]
cologne_B[0].rotation = [0, 0, 1.5935876118594077]
cologne_B[0].optimize = 2
eyeglasses_M[0].position = [2.940000057220459, 3.759999990463257, 1.9149999618530273]
eyeglasses_M[0].rotation = [0, 0, -1.5480050079891259]
eyeglasses_M[0].optimize = 2
wristwatchlocker_C[0].position = [3.1600000858306885, 3.5199999809265137, 1.9049999713897705]
wristwatchlocker_C[0].rotation = [0, 0, -1.5480049775002183]
wristwatchlocker_C[0].optimize = 2
wristwatch_I[0].position = [4.840000152587891, 0.5099999904632568, 1.9049999713897705]
wristwatch_I[0].rotation = [0, 0, -3.1188014488625657]
wristwatch_I[0].optimize = 2
cologne_F[0].position = [2.140000104904175, 0.11999999731779099, 1.9800000190734863]
cologne_F[0].rotation = [0, 0, 1.5935876760895749]
cologne_F[0].optimize = 2
cologned_e7ba6c[0].position = [0.7599999904632568, 0.23999999463558197, 1.9649999141693115]
cologned_e7ba6c[0].rotation = [0, 0, 1.5935876118594077]
cologned_e7ba6c[0].optimize = 2
eyeglasses_U[0].position = [2.940000057220459, 3.880000114440918, 1.9149999618530273]
eyeglasses_U[0].rotation = [0, 0, -1.5480050079891259]
eyeglasses_U[0].optimize = 2
eyeglasses_E[0].position = [2.4100000858306885, 0.23999999463558197, 1.9149999618530273]
eyeglasses_E[0].rotation = [0, 0, 1.5935876118594077]
eyeglasses_E[0].optimize = 2
comb_A[0].position = [3.440000057220459, 3.5199999809265137, 1.9049999713897705]
comb_A[0].rotation = [0, 0, -1.5480049775002183]
comb_A[0].optimize = 2
cologne_T[0].position = [0.7599999904632568, 0.36000001430511475, 1.975000023841858]
cologne_T[0].rotation = [0, 0, 1.5935876118594077]
cologne_T[0].optimize = 2
lamp[0].position = [4.789466857910156, 2.8499999046325684, 0.824999988079071]
lamp[0].rotation = [0, 0, -3.1390517339171087]
lamp[0].optimize = 2
cologne_group_2_C[0].position = [2.9600000381469727, 0.47999998927116394, 1.9649999141693115]
cologne_group_2_C[0].rotation = [0, 0, 1.5935876118594077]
cologne_group_2_C[0].optimize = 2
towelrack_B[0].position = [0.04439473897218704, 1.7000000476837158, 0.07000000029802322]
towelrack_B[0].rotation = [0, 0, 0.002540918150658852]
towelrack_B[0].optimize = 2
hairbrush_E[0].position = [4.559999942779541, 3.640000104904175, 1.9199999570846558]
hairbrush_E[0].rotation = [0, 0, -1.5480050079891259]
hairbrush_E[0].optimize = 2
hook_F[0].position = [2.0, 3.9353880882263184, 0.07000000029802322]
hook_F[0].rotation = [0, 0, -1.5682554040557652]
hook_F[0].optimize = 2
eyeglasseslocker_C[0].position = [2.690000057220459, 0.36000001430511475, 1.9149999618530273]
eyeglasseslocker_C[0].rotation = [0, 0, 1.5935876118594077]
eyeglasseslocker_C[0].optimize = 2
locker_F[0].position = [3.6500000953674316, 0.2900000512599945, 0.949999988079071]
locker_F[0].rotation = [0, 0, 1.6231187171246257]
locker_F[0].optimize = 2
cologne_K[0].position = [2.9600000381469727, 0.23999999463558197, 1.975000023841858]
cologne_K[0].rotation = [0, 0, 1.5935876118594077]
cologne_K[0].optimize = 2
hairbrush_C[0].position = [0.4399999976158142, 3.069999933242798, 1.9199999570846558]
hairbrush_C[0].rotation = [0, 0, 0.022791285064511058]
hairbrush_C[0].optimize = 2
hook_G[0].position = [1.600000023841858, 3.9353880882263184, 0.07000000029802322]
hook_G[0].rotation = [0, 0, -1.5682554040557652]
hook_G[0].optimize = 2
cologne_E[0].position = [1.0399999618530273, 0.11999999731779099, 1.975000023841858]
cologne_E[0].rotation = [0, 0, 1.5935876118594077]
cologne_E[0].optimize = 2
wristwatch_H[0].position = [3.440000057220459, 3.759999990463257, 1.9049999713897705]
wristwatch_H[0].rotation = [0, 0, -1.5480049775002183]
wristwatch_H[0].optimize = 2
cologne_group_2_F[0].position = [2.140000104904175, 0.47999998927116394, 1.959999918937683]
cologne_group_2_F[0].rotation = [0, 0, 1.5935876760895749]
cologne_group_2_F[0].optimize = 2
cologne_U[0].position = [3.509999990463257, 0.36000001430511475, 1.959999918937683]
cologne_U[0].rotation = [0, 0, 1.5935876118594077]
cologne_U[0].optimize = 2
hairbrush_D[0].position = [1.590000033378601, 0.23999999463558197, 1.9199999570846558]
hairbrush_D[0].rotation = [0, 0, 1.5935876118594077]
hairbrush_D[0].optimize = 2
painting_B[0].position = [0.02000024914741516, 2.8499999046325684, 0.30000001192092896]
painting_B[0].rotation = [0, 0, 0.002540916928559797]
painting_B[0].optimize = 2
wristwatch_D[0].position = [4.28000020980835, 3.640000104904175, 1.9049999713897705]
wristwatch_D[0].rotation = [0, 0, -1.5480050079891259]
wristwatch_D[0].optimize = 2
cologne_D[0].position = [4.28000020980835, 3.5199999809265137, 1.9800000190734863]
cologne_D[0].rotation = [0, 0, -1.5480050079891259]
cologne_D[0].optimize = 2
cologne_W[0].position = [0.1599999964237213, 3.309999942779541, 1.9649999141693115]
cologne_W[0].rotation = [0, 0, 0.022791285064511058]
cologne_W[0].optimize = 2
locker_I[0].position = [4.420000076293945, 3.7100000381469727, 0.949999988079071]
locker_I[0].rotation = [0, 0, -1.5153617466188058]
locker_I[0].optimize = 2
locker_A[0].position = [0.8999999761581421, 0.2900000512599945, 0.949999988079071]
locker_A[0].rotation = [0, 0, 1.6231187171246257]
locker_A[0].optimize = 2
eyeglasses_I[0].position = [2.9600000381469727, 0.36000001430511475, 1.9199999570846558]
eyeglasses_I[0].rotation = [0, 0, 1.5935876118594077]
eyeglasses_I[0].optimize = 2
wristwatch_E[0].position = [1.309999942779541, 0.36000001430511475, 1.9049999713897705]
wristwatch_E[0].rotation = [0, 0, 1.5935876118594077]
wristwatch_E[0].optimize = 2
hairbrush_F[0].position = [2.4100000858306885, 0.47999998927116394, 1.9199999570846558]
hairbrush_F[0].rotation = [0, 0, 1.5935876118594077]
hairbrush_F[0].optimize = 2
cologne_A[0].position = [0.7599999904632568, 0.11999999731779099, 1.9800000190734863]
cologne_A[0].rotation = [0, 0, 1.5935876118594077]
cologne_A[0].optimize = 2
hook_B[0].position = [0.800000011920929, 0.06461205333471298, 0.07000000029802322]
hook_B[0].rotation = [0, 0, 1.5733372486118544]
hook_B[0].optimize = 2
cologne_group_2_A[0].position = [0.4399999976158142, 3.309999942779541, 1.959999918937683]
cologne_group_2_A[0].rotation = [0, 0, 0.022791285064511058]
cologne_group_2_A[0].optimize = 2
eyeglasses_B[0].position = [3.7899999618530273, 0.11999999731779099, 1.9199999570846558]
eyeglasses_B[0].rotation = [0, 0, 1.5935876118594077]
eyeglasses_B[0].optimize = 2
cologne_group_2_E[0].position = [1.590000033378601, 0.47999998927116394, 1.975000023841858]
cologne_group_2_E[0].rotation = [0, 0, 1.5935876118594077]
cologne_group_2_E[0].optimize = 2
sconce_A[0].position = [4.939581394195557, 2.6500000953674316, 0.20999999344348907]
sconce_A[0].rotation = [0, 0, -3.1390517329949352]
sconce_A[0].optimize = 2
towelrack_C[0].position = [0.04439473897218704, 2.5999999046325684, 0.07000000029802322]
towelrack_C[0].rotation = [0, 0, 0.002540918150658852]
towelrack_C[0].optimize = 2
eyeglasses_K[0].position = [4.559999942779541, 0.5099999904632568, 1.9149999618530273]
eyeglasses_K[0].rotation = [0, 0, -3.1188014488625657]
eyeglasses_K[0].optimize = 2
sconce_B[0].position = [4.939581394195557, 3.0799999237060547, 0.20999999344348907]
sconce_B[0].rotation = [0, 0, -3.1390517329949352]
sconce_B[0].optimize = 2
cologne_R[0].position = [2.940000057220459, 3.640000104904175, 1.975000023841858]
cologne_R[0].rotation = [0, 0, -1.5480050079891259]
cologne_R[0].optimize = 2
locker_K[0].position = [4.7099995613098145, 0.44999998807907104, 0.949999988079071]
locker_K[0].rotation = [0, 0, -3.095494341279908]
locker_K[0].optimize = 2
wristwatchlocker_B[0].position = [2.9600000381469727, 0.11999999731779099, 1.9049999713897705]
wristwatchlocker_B[0].rotation = [0, 0, 1.5935876118594077]
wristwatchlocker_B[0].optimize = 2
hairbrush_A[0].position = [2.6600000858306885, 3.5199999809265137, 1.9199999570846558]
hairbrush_A[0].rotation = [0, 0, -1.5480050079891259]
hairbrush_A[0].optimize = 2
mirror[0].position = [4.979999542236328, 3.5400230884552, 0.6000000238418579]
mirror[0].rotation = [0, 0, -3.1390517375834066]
mirror[0].optimize = 2
cologne_N[0].position = [4.559999942779541, 0.38999998569488525, 1.9800000190734863]
cologne_N[0].rotation = [0, 0, -3.1188014488625657]
cologne_N[0].optimize = 2
cologne_Y[0].position = [1.590000033378601, 0.36000001430511475, 1.975000023841858]
cologne_Y[0].rotation = [0, 0, 1.5935876118594077]
cologne_Y[0].optimize = 2
eyeglasses_Q[0].position = [4.28000020980835, 3.880000114440918, 1.9149999618530273]
eyeglasses_Q[0].rotation = [0, 0, -1.5480050079891259]
eyeglasses_Q[0].optimize = 2
eyeglasses_A[0].position = [1.590000033378601, 0.11999999731779099, 1.9199999570846558]
eyeglasses_A[0].rotation = [0, 0, 1.5935876118594077]
eyeglasses_A[0].optimize = 2
eyeglasses_T[0].position = [3.440000057220459, 3.880000114440918, 1.9199999570846558]
eyeglasses_T[0].rotation = [0, 0, -1.5480049775002183]
eyeglasses_T[0].optimize = 2
eyeglasses_O[0].position = [1.309999942779541, 0.47999998927116394, 1.9199999570846558]
eyeglasses_O[0].rotation = [0, 0, 1.5935876118594077]
eyeglasses_O[0].optimize = 2
cologne_P[0].position = [2.690000057220459, 0.23999999463558197, 1.9800000190734863]
cologne_P[0].rotation = [0, 0, 1.5935876118594077]
cologne_P[0].optimize = 2
hairbrush_B[0].position = [4.559999942779541, 0.27000001072883606, 1.9199999570846558]
hairbrush_B[0].rotation = [0, 0, -3.1188014488625657]
hairbrush_B[0].optimize = 2
sink_C[0].position = [0.33000004291534424, 1.7799999713897705, 0.42500001192092896]
sink_C[0].rotation = [0, 0, 0.0025409172284856325]
sink_C[0].optimize = 2
cologne_S[0].position = [4.840000152587891, 0.38999998569488525, 1.9800000190734863]
cologne_S[0].rotation = [0, 0, -3.1188014488625657]
cologne_S[0].optimize = 2
painting_A[0].position = [0.02000024914741516, 1.149999976158142, 0.30000001192092896]
painting_A[0].rotation = [0, 0, 0.002540916928559797]
painting_A[0].optimize = 2
locker_E[0].position = [3.0999999046325684, 0.2900000512599945, 0.949999988079071]
locker_E[0].rotation = [0, 0, 1.6231187171246257]
locker_E[0].optimize = 2
cologne_G[0].position = [2.690000057220459, 0.11999999731779099, 1.975000023841858]
cologne_G[0].rotation = [0, 0, 1.5935876118594077]
cologne_G[0].optimize = 2
cologne_C[0].position = [3.509999990463257, 0.11999999731779099, 1.959999918937683]
cologne_C[0].rotation = [0, 0, 1.5935876118594077]
cologne_C[0].optimize = 2
sink_D[0].position = [0.3150000274181366, 2.4800000190734863, 0.42500001192092896]
sink_D[0].rotation = [0, 0, 0.0025409190728320715]
sink_D[0].optimize = 2
locker_C[0].position = [2.0, 0.2900000512599945, 0.949999988079071]
locker_C[0].rotation = [0, 0, 1.6293431924063666]
locker_C[0].optimize = 2
cologne_I[0].position = [2.940000057220459, 3.5199999809265137, 1.975000023841858]
cologne_I[0].rotation = [0, 0, -1.5480050079891259]
cologne_I[0].optimize = 2
hairbrush_G[0].position = [1.0399999618530273, 0.47999998927116394, 1.9199999570846558]
hairbrush_G[0].rotation = [0, 0, 1.5935876118594077]
hairbrush_G[0].optimize = 2
hairbrush_H[0].position = [0.4399999976158142, 3.430000066757202, 1.9199999570846558]
hairbrush_H[0].rotation = [0, 0, 0.022791285064511058]
hairbrush_H[0].optimize = 2
eyeglasses_N[0].position = [0.7599999904632568, 0.47999998927116394, 1.9149999618530273]
eyeglasses_N[0].rotation = [0, 0, 1.5935876118594077]
eyeglasses_N[0].optimize = 2
wristwatchlocker_A[0].position = [2.4100000858306885, 0.11999999731779099, 1.9049999713897705]
wristwatchlocker_A[0].rotation = [0, 0, 1.5935876118594077]
wristwatchlocker_A[0].optimize = 2
locker_G[0].position = [3.299999952316284, 3.7100000381469727, 0.949999988079071]
locker_G[0].rotation = [0, 0, -1.5122494611834267]
locker_G[0].optimize = 2
cologne_O[0].position = [2.140000104904175, 0.23999999463558197, 1.959999918937683]
cologne_O[0].rotation = [0, 0, 1.5935876760895749]
cologne_O[0].optimize = 2
cologne_M[0].position = [0.1599999964237213, 3.190000057220459, 1.975000023841858]
cologne_M[0].rotation = [0, 0, 0.022791285064511058]
cologne_M[0].optimize = 2
sink_A[0].position = [0.3150000274181366, 0.3799999952316284, 0.42500001192092896]
sink_A[0].rotation = [0, 0, 0.0025409190728320715]
sink_A[0].optimize = 2
comb_B[0].position = [3.7899999618530273, 0.23999999463558197, 1.9049999713897705]
comb_B[0].rotation = [0, 0, 1.5935876118594077]
comb_B[0].optimize = 2
hook_D[0].position = [1.600000023841858, 0.06461205333471298, 0.07000000029802322]
hook_D[0].rotation = [0, 0, 1.5733372486118544]
hook_D[0].optimize = 2
cologne_group_2_B[0].position = [1.8600000143051147, 0.47999998927116394, 1.975000023841858]
cologne_group_2_B[0].rotation = [0, 0, 1.5935876760895749]
cologne_group_2_B[0].optimize = 2
cologne_Q[0].position = [3.240000009536743, 0.23999999463558197, 1.975000023841858]
cologne_Q[0].rotation = [0, 0, 1.5935876118594077]
cologne_Q[0].optimize = 2
cologne_group_2_H[0].position = [4.559999942779541, 3.880000114440918, 1.975000023841858]
cologne_group_2_H[0].rotation = [0, 0, -1.5480050079891259]
cologne_group_2_H[0].optimize = 2
wristwatchlocker_E[0].position = [3.1600000858306885, 3.880000114440918, 1.9049999713897705]
wristwatchlocker_E[0].rotation = [0, 0, -1.5480049775002183]
wristwatchlocker_E[0].optimize = 2
comb_D[0].position = [3.7899999618530273, 0.36000001430511475, 1.9049999713897705]
comb_D[0].rotation = [0, 0, 1.5935876118594077]
comb_D[0].optimize = 2
hook_E[0].position = [2.4000000953674316, 3.9353880882263184, 0.07000000029802322]
hook_E[0].rotation = [0, 0, -1.5682554040557652]
hook_E[0].optimize = 2
eyeglasses_S[0].position = [2.0, 0.47999998927116394, 1.9149999618530273]
eyeglasses_S[0].rotation = [0, 0, 1.5935876760895749]
eyeglasses_S[0].optimize = 2
towelrack_A[0].position = [0.04082566872239113, 0.800000011920929, 0.05999999865889549]
towelrack_A[0].rotation = [0, 0, 0.0025409172284856325]
towelrack_A[0].optimize = 2
hook_A[0].position = [0.4000000059604645, 0.06461205333471298, 0.07000000029802322]
hook_A[0].rotation = [0, 0, 1.5733372486118544]
hook_A[0].optimize = 2
hook_H[0].position = [1.2000000476837158, 3.9353880882263184, 0.07000000029802322]
hook_H[0].rotation = [0, 0, -1.5682554040557652]
hook_H[0].optimize = 2
wristwatchlocker_D[0].position = [2.6600000858306885, 3.640000104904175, 1.9049999713897705]
wristwatchlocker_D[0].rotation = [0, 0, -1.5480050079891259]
wristwatchlocker_D[0].optimize = 2
cologne_J[0].position = [1.309999942779541, 0.23999999463558197, 1.9649999141693115]
cologne_J[0].rotation = [0, 0, 1.5935876118594077]
cologne_J[0].optimize = 2
eyeglasses_G[0].position = [0.4399999976158142, 3.190000057220459, 1.9149999618530273]
eyeglasses_G[0].rotation = [0, 0, 0.022791285064511058]
eyeglasses_G[0].optimize = 2
hook_C[0].position = [1.2000000476837158, 0.06461205333471298, 0.07000000029802322]
hook_C[0].rotation = [0, 0, 1.5733372486118544]
hook_C[0].optimize = 2
cologne_group_2_D[0].position = [0.1599999964237213, 3.430000066757202, 1.959999918937683]
cologne_group_2_D[0].rotation = [0, 0, 0.022791285064511058]
cologne_group_2_D[0].optimize = 2
eyeglasses_R[0].position = [3.7899999618530273, 0.47999998927116394, 1.9149999618530273]
eyeglasses_R[0].rotation = [0, 0, 1.5935876118594077]
eyeglasses_R[0].optimize = 2
eyeglasses_L[0].position = [2.140000104904175, 0.36000001430511475, 1.9199999570846558]
eyeglasses_L[0].rotation = [0, 0, 1.5935876760895749]
eyeglasses_L[0].optimize = 2
eyeglasseslocker_B[0].position = [3.440000057220459, 3.640000104904175, 1.9149999618530273]
eyeglasseslocker_B[0].rotation = [0, 0, -1.5480049775002183]
eyeglasseslocker_B[0].optimize = 2
sink_B[0].position = [0.3150000274181366, 1.0800000429153442, 0.42500001192092896]
sink_B[0].rotation = [0, 0, 0.0025409190728320715]
sink_B[0].optimize = 2
sink_center[0].position = [3.859999895095825, 3.6700000762939453, 0.42500001192092896]
sink_center[0].rotation = [0, 0, -1.5620341067611838]
sink_center[0].optimize = 2
eyeglasseslocker_D[0].position = [3.509999990463257, 0.47999998927116394, 1.9149999618530273]
eyeglasseslocker_D[0].rotation = [0, 0, 1.5935876118594077]
eyeglasseslocker_D[0].optimize = 2
cologne_H[0].position = [3.240000009536743, 0.11999999731779099, 1.959999918937683]
cologne_H[0].rotation = [0, 0, 1.5935876118594077]
cologne_H[0].optimize = 2
wristwatch_F[0].position = [1.8600000143051147, 0.36000001430511475, 1.9049999713897705]
wristwatch_F[0].rotation = [0, 0, 1.5935876760895749]
wristwatch_F[0].optimize = 2
locker_B[0].position = [1.4500000476837158, 0.2900000512599945, 0.949999988079071]
locker_B[0].rotation = [0, 0, 1.6231187171246257]
locker_B[0].optimize = 2
wristwatch_A[0].position = [1.8600000143051147, 0.11999999731779099, 1.9049999713897705]
wristwatch_A[0].rotation = [0, 0, 1.5935876760895749]
wristwatch_A[0].optimize = 2
cologne_V[0].position = [4.28000020980835, 3.759999990463257, 1.9649999141693115]
cologne_V[0].rotation = [0, 0, -1.5480050079891259]
cologne_V[0].optimize = 2
eyeglasses_C[0].position = [4.559999942779541, 3.5199999809265137, 1.9199999570846558]
eyeglasses_C[0].rotation = [0, 0, -1.5480050079891259]
eyeglasses_C[0].optimize = 2
locker_H[0].position = [2.799999952316284, 3.7100000381469727, 0.949999988079071]
locker_H[0].rotation = [0, 0, -1.5153617466188058]
locker_H[0].optimize = 2
cologne_L[0].position = [3.1600000858306885, 3.640000104904175, 1.9649999141693115]
cologne_L[0].rotation = [0, 0, -1.5480049775002183]
cologne_L[0].optimize = 2
eyeglasses_H[0].position = [2.4100000858306885, 0.36000001430511475, 1.9199999570846558]
eyeglasses_H[0].rotation = [0, 0, 1.5935876118594077]
eyeglasses_H[0].optimize = 2
wristwatch_G[0].position = [2.6600000858306885, 3.759999990463257, 1.9049999713897705]
wristwatch_G[0].rotation = [0, 0, -1.5480050079891259]
wristwatch_G[0].optimize = 2
eyeglasses_F[0].position = [1.0399999618530273, 0.23999999463558197, 1.9199999570846558]
eyeglasses_F[0].rotation = [0, 0, 1.5935876118594077]
eyeglasses_F[0].optimize = 2
eyeglasses_D[0].position = [4.840000152587891, 0.27000001072883606, 1.9199999570846558]
eyeglasses_D[0].rotation = [0, 0, -3.1188014488625657]
eyeglasses_D[0].optimize = 2
wristwatch_C[0].position = [3.509999990463257, 0.23999999463558197, 1.9049999713897705]
wristwatch_C[0].rotation = [0, 0, 1.5935876118594077]
wristwatch_C[0].optimize = 2
comb_C[0].position = [3.240000009536743, 0.36000001430511475, 1.9049999713897705]
comb_C[0].rotation = [0, 0, 1.5935876118594077]
comb_C[0].optimize = 2
locker_J[0].position = [0.2900000512599945, 3.25, 0.949999988079071]
locker_J[0].rotation = [0, 0, 0.05232239032972915]
locker_J[0].optimize = 2
eyeglasses_J[0].position = [3.1600000858306885, 3.759999990463257, 1.9199999570846558]
eyeglasses_J[0].rotation = [0, 0, -1.5480049775002183]
eyeglasses_J[0].optimize = 2
eyeglasses_P[0].position = [2.6600000858306885, 3.880000114440918, 1.9199999570846558]
eyeglasses_P[0].rotation = [0, 0, -1.5480050079891259]
eyeglasses_P[0].optimize = 2
cologne_group_2_G[0].position = [2.690000057220459, 0.47999998927116394, 1.9649999141693115]
cologne_group_2_G[0].rotation = [0, 0, 1.5935876118594077]
cologne_group_2_G[0].optimize = 2
eyeglasseslocker_A[0].position = [1.8600000143051147, 0.23999999463558197, 1.9149999618530273]
eyeglasseslocker_A[0].rotation = [0, 0, 1.5935876760895749]
eyeglasseslocker_A[0].optimize = 2
comb_E[0].position = [3.240000009536743, 0.47999998927116394, 1.9049999713897705]
comb_E[0].rotation = [0, 0, 1.5935876118594077]
comb_E[0].optimize = 2
cologne_Z[0].position = [4.559999942779541, 3.759999990463257, 1.975000023841858]
cologne_Z[0].rotation = [0, 0, -1.5480050079891259]
cologne_Z[0].optimize = 2
cologn[0].position = [4.559999942779541, 0.6299999952316284, 1.975000023841858]
cologn[0].rotation = [0, 0, -3.1188014488625657]
cologn[0].optimize = 2
cologne_X[0].position = [1.0399999618530273, 0.36000001430511475, 1.975000023841858]
cologne_X[0].rotation = [0, 0, 1.5935876118594077]
cologne_X[0].optimize = 2
locker_D[0].position = [2.549999952316284, 0.2900000512599945, 0.949999988079071]
locker_D[0].rotation = [0, 0, 1.6231187171246257]
locker_D[0].optimize = 2

