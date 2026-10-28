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
    Wall(corner1=[4.00, 0.00, 0.00], corner2=[4.00, 4.50, 0.00]),
    Wall(corner1=[4.00, 4.50, 0.00], corner2=[0.00, 4.50, 0.00]),
    Wall(corner1=[0.00, 4.50, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
candle_A = Assets(description="A scented pillar candle in a neutral glass holder, tall cylindrical glass with clear finish, candle wax is ivory, subtle fragrance.", size=[0.10, 0.10, 0.18], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="A hardcover book with a rectangular shape, neutral spine, smooth matte cover and crisp pages", size=[0.30, 0.22, 0.04], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="A hardcover book in transitional style with a neutral spine, rectangular shape, smooth cover, subtle grain texture.", size=[0.28, 0.21, 0.04], placements=[AssetInstance() for _ in range(1)])
book_C = Assets(description="A hardcover book with a rectangular shape, neutral spine, smooth matte cover and crisp pages", size=[0.30, 0.22, 0.04], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="A small ceramic table lamp with a squat cylindrical base, creamy glaze, soft curved shade, transitional style, featuring a subtle speckled texture.", size=[0.30, 0.30, 0.48], placements=[AssetInstance() for _ in range(1)])
chair = Assets(description="A upholstered accent chair with a compact square seat, soft neutral fabric, gently rolled arms, and a low‑profile wooden frame, highlighted by a decorative nailhead trim", size=[0.78, 0.82, 0.82], placements=[AssetInstance() for _ in range(1)])
plant_A = Assets(description="A small potted plant in a neutral ceramic pot, featuring a compact cylindrical pot and a leafy green plant with rounded foliage.", size=[0.32, 0.32, 0.45], placements=[AssetInstance() for _ in range(1)])
tablebook_A = Assets(description="A hardcover book in transitional style with a neutral spine, rectangular shape, smooth matte cover, and subtle grain texture", size=[0.32, 0.25, 0.04], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="A sleek floor lamp with a slender cylindrical metal stem, brushed nickel finish, and a minimalist conical shade that diffuses soft light", size=[0.36, 0.36, 1.55], placements=[AssetInstance() for _ in range(1)])
vase_A = Assets(description="A ceramic vase with a smooth matte finish, sleek cylindrical form, and a gentle tapered neck", size=[0.16, 0.16, 0.32], placements=[AssetInstance() for _ in range(1)])
plant_B = Assets(description="A small potted plant in a neutral ceramic pot, featuring a compact cylindrical pot and a leafy green plant with rounded foliage.", size=[0.32, 0.32, 0.45], placements=[AssetInstance() for _ in range(1)])
book_D = Assets(description="A hardcover book in transitional style with a neutral spine, rectangular shape, smooth cover, subtle grain texture.", size=[0.29, 0.22, 0.04], placements=[AssetInstance() for _ in range(1)])
book_E = Assets(description="A hardcover book with a rectangular shape, neutral spine, transitional style, featuring a matte cover.", size=[0.27, 0.20, 0.04], placements=[AssetInstance() for _ in range(1)])
plant_C = Assets(description="A small potted plant in a neutral ceramic pot, pot is slightly squat with a smooth matte finish, foliage is fuller, overall low‑profile shape.", size=[0.38, 0.38, 0.42], placements=[AssetInstance() for _ in range(1)])
ottoman = Assets(description="A soft fabric ottoman with a low‑profile square shape, neutral textured upholstery, and a subtle button‑tufted surface, supported by a hidden wooden base", size=[0.65, 0.65, 0.42], placements=[AssetInstance() for _ in range(1)])
floorplant_A = Assets(description="A small potted plant in a neutral ceramic pot, compact cylindrical pot with a leafy green plant.", size=[0.36, 0.36, 0.55], placements=[AssetInstance() for _ in range(1)])
dresserbook_A = Assets(description="A hardcover book in transitional style with a neutral spine, rectangular shape, smooth matte cover, and subtle grain texture", size=[0.32, 0.25, 0.04], placements=[AssetInstance() for _ in range(1)])
book_F = Assets(description="A hardcover book with a rectangular shape, neutral spine, smooth matte cover and crisp pages", size=[0.30, 0.22, 0.04], placements=[AssetInstance() for _ in range(1)])
book_G = Assets(description="A hardcover book with a rectangular shape, neutral spine, smooth matte cover and crisp pages", size=[0.29, 0.21, 0.04], placements=[AssetInstance() for _ in range(1)])
nightstand_A = Assets(description="A wooden nightstand in transitional style with a square silhouette, smooth neutral finish, and tapered legs, topped with a single recessed drawer and a subtle carved accent", size=[0.48, 0.58, 0.62], placements=[AssetInstance() for _ in range(1)])
vase_B = Assets(description="A small decorative ceramic vase with a rounded cylindrical shape, textured surface and muted neutral glaze", size=[0.18, 0.18, 0.24], placements=[AssetInstance() for _ in range(1)])
candle_B = Assets(description="A scented pillar candle in a neutral glass holder, cylindrical form, smooth clear glass, and a gentle tapered top", size=[0.09, 0.09, 0.16], placements=[AssetInstance() for _ in range(1)])
vase_C = Assets(description="A small decorative ceramic vase with a rounded cylindrical shape, textured surface and muted neutral glaze", size=[0.18, 0.18, 0.24], placements=[AssetInstance() for _ in range(1)])
dresserbottles = Assets(description="A glass bottle with a slender cylindrical shape and neutral coloured glass", size=[0.07, 0.07, 0.22], placements=[AssetInstance() for _ in range(1)])
mirror_A = Assets(description="A single piece of thin and upright rectangular wall mirror with a sleek metal frame, neutral finish, transitional style.", size=[0.04, 0.70, 1.60], placements=[AssetInstance() for _ in range(1)])
vase_D = Assets(description="A ceramic vase with a modest squat cylindrical shape, smooth glazed surface, neutral tone, transitional style, with a subtle matte finish.", size=[0.20, 0.20, 0.22], placements=[AssetInstance() for _ in range(1)])
tablecandle = Assets(description="A candle in a neutral glass holder, cylindrical glass with a smooth finish and a simple clear base", size=[0.09, 0.09, 0.14], placements=[AssetInstance() for _ in range(1)])
print = Assets(description="A single piece of thin and upright framed abstract print, transitional style, with a narrow wooden frame and a bold geometric composition", size=[0.04, 0.65, 0.95], placements=[AssetInstance() for _ in range(1)])
candle_C = Assets(description="A scented pillar candle in a neutral glass holder, cylindrical with a smooth clear base and subtle fragrance", size=[0.09, 0.09, 0.15], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="A slim console table with a long rectangular top, light neutral finish, and minimalist metal legs that are slightly angled outward for stability", size=[0.38, 1.40, 0.78], placements=[AssetInstance() for _ in range(1)])
vase_E = Assets(description="A small decorative vase of textured ceramic, oval shape, gently flared rim, matte surface, muted color.", size=[0.14, 0.17, 0.23], placements=[AssetInstance() for _ in range(1)])
pillow = Assets(description="A textured decorative pillow with a square shape, plush soft fabric, subtle woven pattern, and a muted pastel hue", size=[0.15, 0.48, 0.48], placements=[AssetInstance() for _ in range(1)])
floorplant_B = Assets(description="A small potted plant in a neutral ceramic pot, compact cylindrical pot with a leafy green plant.", size=[0.36, 0.36, 0.55], placements=[AssetInstance() for _ in range(1)])
lamp_C = Assets(description="A small ceramic table lamp with a cylindrical base, rounded shade, neutral glaze, and a subtle brushed texture", size=[0.28, 0.28, 0.46], placements=[AssetInstance() for _ in range(1)])
candle_D = Assets(description="A candle in a neutral glass holder, short cylindrical glass, clear finish, simple white wax.", size=[0.08, 0.08, 0.10], placements=[AssetInstance() for _ in range(1)])
dresserbottle = Assets(description="A glass bottle with neutral colour, slender cylindrical form, smooth surface and a narrow neck", size=[0.06, 0.06, 0.20], placements=[AssetInstance() for _ in range(1)])
candle_E = Assets(description="A scented pillar candle in a neutral glass holder, cylindrical with a smooth clear base and subtle fragrance", size=[0.09, 0.09, 0.15], placements=[AssetInstance() for _ in range(1)])
plant_D = Assets(description="A small potted plant in a neutral ceramic pot, with a compact rounded pot and a modest green foliage sprout", size=[0.28, 0.28, 0.38], placements=[AssetInstance() for _ in range(1)])
book_H = Assets(description="A hardcover book with a rectangular shape, neutral spine, smooth matte cover and crisp pages", size=[0.30, 0.22, 0.04], placements=[AssetInstance() for _ in range(1)])
candle_F = Assets(description="A scented pillar candle in a neutral glass holder, tall cylindrical glass with clear finish, candle wax is ivory, subtle fragrance.", size=[0.10, 0.10, 0.18], placements=[AssetInstance() for _ in range(1)])
plant_E = Assets(description="A small potted plant in a neutral ceramic pot, with a compact rounded pot and a modest green foliage sprout", size=[0.28, 0.28, 0.38], placements=[AssetInstance() for _ in range(1)])
bottle_A = Assets(description="A glass cosmetic bottle with a slender cylindrical shape, clear neutral tint, and a subtle frosted accent", size=[0.06, 0.06, 0.18], placements=[AssetInstance() for _ in range(1)])
dresserbook_B = Assets(description="A hardcover book with a rectangular shape, transitional style, neutral spine, sleek cover.", size=[0.31, 0.24, 0.04], placements=[AssetInstance() for _ in range(1)])
mirror_B = Assets(description="A single piece of thin and upright rectangular wall mirror with a sleek brushed metal frame, transitional style, and a reflective surface", size=[0.04, 0.70, 1.60], placements=[AssetInstance() for _ in range(1)])
plant_F = Assets(description="A small potted plant in a neutral ceramic pot, pot is slightly squat with a smooth matte finish, foliage is fuller, overall low‑profile shape.", size=[0.38, 0.38, 0.42], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="A glass bottle with a sleek cylindrical shape, neutral clear color, smooth surface, transitional style.", size=[0.07, 0.07, 0.19], placements=[AssetInstance() for _ in range(1)])
dresser = Assets(description="A linen‑finish dresser with a rectangular body, soft neutral tone, and clean straight‑edged drawers, featuring a single horizontal metal handle that runs the length of each drawer front", size=[0.52, 1.55, 0.82], placements=[AssetInstance() for _ in range(1)])
bottle_C = Assets(description="A glass cosmetic bottle with a slender cylindrical shape, clear neutral tint, and a subtle frosted accent", size=[0.06, 0.06, 0.18], placements=[AssetInstance() for _ in range(1)])
nightstandbook_A = Assets(description="A hardcover book in transitional style with a neutral spine, rectangular shape, smooth matte cover, and subtle grain texture", size=[0.31, 0.24, 0.04], placements=[AssetInstance() for _ in range(1)])
nightstand2candle = Assets(description="A candle in a neutral glass holder, cylindrical glass with a smooth finish", size=[0.09, 0.09, 0.14], placements=[AssetInstance() for _ in range(1)])
book_I = Assets(description="A hardcover book with a rectangular shape, neutral spine, soft textured cover, and subtle grain finish", size=[0.05, 0.21, 0.29], placements=[AssetInstance() for _ in range(1)])
book_J = Assets(description="A hardcover book with a rectangular shape, neutral spine, soft textured cover, and subtle grain finish", size=[0.05, 0.22, 0.30], placements=[AssetInstance() for _ in range(1)])
nightstand1book = Assets(description="A hardcover book with a rectangular shape, neutral spine, and transitional style detailing", size=[0.29, 0.22, 0.04], placements=[AssetInstance() for _ in range(1)])
plant_G = Assets(description="A medium potted plant in a neutral ceramic pot, round base, matte finish, with fuller green foliage", size=[0.50, 0.50, 0.75], placements=[AssetInstance() for _ in range(1)])
dresserbook_C = Assets(description="A hardcover book in transitional style with a neutral spine, rectangular shape, smooth matte cover, and subtle grain texture", size=[0.32, 0.25, 0.04], placements=[AssetInstance() for _ in range(1)])
book_K = Assets(description="A hardcover book with a rectangular shape, neutral spine, soft textured cover, and subtle grain finish", size=[0.31, 0.24, 0.04], placements=[AssetInstance() for _ in range(1)])
candle_G = Assets(description="A scented pillar candle in a neutral glass holder, cylindrical form, smooth clear glass, and a gentle tapered top", size=[0.09, 0.09, 0.16], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="A tall wooden wardrobe with a narrow rectangular profile, neutral stained wood, and a single vertical panel door with a recessed pull, topped by a subtle crown molding detail", size=[0.62, 1.05, 2.20], placements=[AssetInstance() for _ in range(1)])
dresserbooks_A = Assets(description="A hardcover book with a rectangular shape, neutral spine, and transitional style detailing", size=[0.30, 0.23, 0.04], placements=[AssetInstance() for _ in range(1)])
bookshelf = Assets(description="A narrow wooden bookshelf with a tall rectangular silhouette, neutral finish, and five open shelves, featuring a subtle stepped back panel that adds visual interest", size=[0.32, 0.85, 1.90], placements=[AssetInstance() for _ in range(1)])
candle_H = Assets(description="A small pillar candle with a cylindrical shape, neutral wax, smooth finish, transitional style, with a subtle embossed band.", size=[0.08, 0.08, 0.12], placements=[AssetInstance() for _ in range(1)])
bottle_D = Assets(description="A glass cosmetic bottle with a slender cylindrical shape, clear neutral tint, and a subtle frosted accent", size=[0.06, 0.06, 0.18], placements=[AssetInstance() for _ in range(1)])
nightstandbook_B = Assets(description="A hardcover book with a rectangular shape, transitional style, neutral spine, sleek cover.", size=[0.31, 0.24, 0.04], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="A upholstered king bed with a rectangular frame, neutral-toned plush fabric, and subtle tufted detailing, featuring a low‑slung profile and a soft, textured headboard that adds depth to the design", size=[2.20, 2.05, 1.25], placements=[AssetInstance() for _ in range(1)])
book_L = Assets(description="A hardcover book with a rectangular shape, neutral spine, soft textured cover, and subtle grain finish", size=[0.30, 0.23, 0.04], placements=[AssetInstance() for _ in range(1)])
nightstand_B = Assets(description="A wooden nightstand in transitional style with a square silhouette, smooth neutral finish, and tapered legs, topped with a single recessed drawer and a subtle carved accent", size=[0.48, 0.58, 0.62], placements=[AssetInstance() for _ in range(1)])
book_M = Assets(description="A hardcover book with a rectangular shape, neutral spine, soft textured cover, and subtle grain finish", size=[0.29, 0.21, 0.04], placements=[AssetInstance() for _ in range(1)])
tablebook_B = Assets(description="A hardcover book in transitional style with a neutral spine, rectangular shape, smooth matte cover, and subtle grain texture", size=[0.32, 0.25, 0.04], placements=[AssetInstance() for _ in range(1)])
dresserbooks_B = Assets(description="A hardcover book with a rectangular shape, neutral spine, and transitional style detailing", size=[0.30, 0.23, 0.04], placements=[AssetInstance() for _ in range(1)])
candle_I = Assets(description="A scented pillar candle in a neutral glass holder, tall cylindrical glass with clear finish, candle wax is ivory, subtle fragrance.", size=[0.10, 0.10, 0.18], placements=[AssetInstance() for _ in range(1)])
book_N = Assets(description="A hardcover book with a rectangular shape, neutral spine, transitional style, featuring a matte cover.", size=[0.27, 0.20, 0.04], placements=[AssetInstance() for _ in range(1)])
bench = Assets(description="A padded foot bench with a rectangular shape, plush neutral upholstery, and a subtle tufted surface, supported by sleek wooden legs that taper inward", size=[0.48, 1.45, 0.48], placements=[AssetInstance() for _ in range(1)])
book_O = Assets(description="A hardcover book with a rectangular shape, neutral spine, soft textured cover, and subtle grain finish", size=[0.30, 0.22, 0.04], placements=[AssetInstance() for _ in range(1)])
plant_H = Assets(description="A small potted plant in a neutral ceramic pot, with a compact rounded pot and a modest green foliage sprout", size=[0.28, 0.28, 0.38], placements=[AssetInstance() for _ in range(1)])
bookshelfbook = Assets(description="A hardcover book with a rectangular shape, neutral spine, transitional style, featuring a smooth matte finish.", size=[0.05, 0.21, 0.29], placements=[AssetInstance() for _ in range(1)])
vase_F = Assets(description="A small decorative vase of textured ceramic, oval shape, gently flared rim, matte surface, muted color.", size=[0.14, 0.17, 0.23], placements=[AssetInstance() for _ in range(1)])

candle_A[0].instance_id = 'candle_A_0'
book_A[0].instance_id = 'book_A_0'
book_B[0].instance_id = 'book_B_0'
book_C[0].instance_id = 'book_C_0'
lamp_A[0].instance_id = 'lamp_A_0'
chair[0].instance_id = 'chair_0'
plant_A[0].instance_id = 'plant_A_0'
tablebook_A[0].instance_id = 'tablebook_A_0'
lamp_B[0].instance_id = 'lamp_B_0'
vase_A[0].instance_id = 'vase_A_0'
plant_B[0].instance_id = 'plant_B_0'
book_D[0].instance_id = 'book_D_0'
book_E[0].instance_id = 'book_E_0'
plant_C[0].instance_id = 'plant_C_0'
ottoman[0].instance_id = 'ottoman_0'
floorplant_A[0].instance_id = 'floorplant_A_0'
dresserbook_A[0].instance_id = 'dresserbook_A_0'
book_F[0].instance_id = 'book_F_0'
book_G[0].instance_id = 'book_G_0'
nightstand_A[0].instance_id = 'nightstand_A_0'
vase_B[0].instance_id = 'vase_B_0'
candle_B[0].instance_id = 'candle_B_0'
vase_C[0].instance_id = 'vase_C_0'
dresserbottles[0].instance_id = 'dresserbottles_0'
mirror_A[0].instance_id = 'mirror_A_0'
vase_D[0].instance_id = 'vase_D_0'
tablecandle[0].instance_id = 'tablecandle_0'
print[0].instance_id = 'print_0'
candle_C[0].instance_id = 'candle_C_0'
table[0].instance_id = 'table_0'
vase_E[0].instance_id = 'vase_E_0'
pillow[0].instance_id = 'pillow_0'
floorplant_B[0].instance_id = 'floorplant_B_0'
lamp_C[0].instance_id = 'lamp_C_0'
candle_D[0].instance_id = 'candle_D_0'
dresserbottle[0].instance_id = 'dresserbottle_0'
candle_E[0].instance_id = 'candle_E_0'
plant_D[0].instance_id = 'plant_D_0'
book_H[0].instance_id = 'book_H_0'
candle_F[0].instance_id = 'candle_F_0'
plant_E[0].instance_id = 'plant_E_0'
bottle_A[0].instance_id = 'bottle_A_0'
dresserbook_B[0].instance_id = 'dresserbook_B_0'
mirror_B[0].instance_id = 'mirror_B_0'
plant_F[0].instance_id = 'plant_F_0'
bottle_B[0].instance_id = 'bottle_B_0'
dresser[0].instance_id = 'dresser_0'
bottle_C[0].instance_id = 'bottle_C_0'
nightstandbook_A[0].instance_id = 'nightstandbook_A_0'
nightstand2candle[0].instance_id = 'nightstand2candle_0'
book_I[0].instance_id = 'book_I_0'
book_J[0].instance_id = 'book_J_0'
nightstand1book[0].instance_id = 'nightstand1book_0'
plant_G[0].instance_id = 'plant_G_0'
dresserbook_C[0].instance_id = 'dresserbook_C_0'
book_K[0].instance_id = 'book_K_0'
candle_G[0].instance_id = 'candle_G_0'
wardrobe[0].instance_id = 'wardrobe_0'
dresserbooks_A[0].instance_id = 'dresserbooks_A_0'
bookshelf[0].instance_id = 'bookshelf_0'
candle_H[0].instance_id = 'candle_H_0'
bottle_D[0].instance_id = 'bottle_D_0'
nightstandbook_B[0].instance_id = 'nightstandbook_B_0'
bed[0].instance_id = 'bed_0'
book_L[0].instance_id = 'book_L_0'
nightstand_B[0].instance_id = 'nightstand_B_0'
book_M[0].instance_id = 'book_M_0'
tablebook_B[0].instance_id = 'tablebook_B_0'
dresserbooks_B[0].instance_id = 'dresserbooks_B_0'
candle_I[0].instance_id = 'candle_I_0'
book_N[0].instance_id = 'book_N_0'
bench[0].instance_id = 'bench_0'
book_O[0].instance_id = 'book_O_0'
plant_H[0].instance_id = 'plant_H_0'
bookshelfbook[0].instance_id = 'bookshelfbook_0'
vase_F[0].instance_id = 'vase_F_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

candle_A[0].position = [2.212778459339815, 0.31982691876195973, 0.09]
candle_A[0].rotation = [0, 0, 0]
book_A[0].position = [2.9384444118230815, 2.9051092224487265, 0.02]
book_A[0].rotation = [0, 0, 0]
book_B[0].position = [3.180591559907824, 1.6179221656381442, 0.02]
book_B[0].rotation = [0, 0, 0]
book_C[0].position = [1.200681414842463, 1.606954107257928, 0.02]
book_C[0].rotation = [0, 0, 0]
lamp_A[0].position = [2.93439858505064, 1.4039552274818459, 0.24]
lamp_A[0].rotation = [0, 0, 0]
chair[0].position = [1.2662609949190955, 2.835775215839085, 0.41]
chair[0].rotation = [0, 0, 0]
plant_A[0].position = [0.7274008619910934, 1.9217469672971426, 0.225]
plant_A[0].rotation = [0, 0, 0]
tablebook_A[0].position = [1.5713488972518777, 3.4810115642044384, 0.02]
tablebook_A[0].rotation = [0, 0, 0]
lamp_B[0].position = [2.8319593573294766, 1.0465180340453084, 0.775]
lamp_B[0].rotation = [0, 0, 0]
vase_A[0].position = [0.7893702896211106, 2.7041651112271103, 0.16]
vase_A[0].rotation = [0, 0, 0]
plant_B[0].position = [3.154334085785304, 1.498989735004497, 0.225]
plant_B[0].rotation = [0, 0, 0]
book_D[0].position = [3.1284830382037416, 2.506587358432219, 0.02]
book_D[0].rotation = [0, 0, 0]
book_E[0].position = [2.906725914723324, 1.617492824039245, 0.0175]
book_E[0].rotation = [0, 0, 0]
plant_C[0].position = [3.623452988990852, 1.9020319386460178, 0.21]
plant_C[0].rotation = [0, 0, 0]
ottoman[0].position = [3.242099199404472, 1.4573585687636808, 0.21]
ottoman[0].rotation = [0, 0, 0]
floorplant_A[0].position = [3.490804719266035, 4.015756813754161, 0.275]
floorplant_A[0].rotation = [0, 0, 0]
dresserbook_A[0].position = [1.548582857389154, 3.7009356991769162, 0.02]
dresserbook_A[0].rotation = [0, 0, 0]
book_F[0].position = [1.9566741694912992, 3.713254462504878, 0.02]
book_F[0].rotation = [0, 0, 0]
book_G[0].position = [1.2105328965287874, 2.9472029697039486, 0.0175]
book_G[0].rotation = [0, 0, 0]
nightstand_A[0].position = [3.683681525280227, 0.6557485124168307, 0.31]
nightstand_A[0].rotation = [0, 0, 0]
vase_B[0].position = [0.824893864768808, 1.718203290949262, 0.12]
vase_B[0].rotation = [0, 0, 0]
candle_B[0].position = [0.26841463421690515, 3.74316834806102, 0.08]
candle_B[0].rotation = [0, 0, 0]
vase_C[0].position = [0.18800006960658822, 0.5415757151782279, 0.12]
vase_C[0].rotation = [0, 0, 0]
dresserbottles[0].position = [3.245696891615653, 0.8823007196954915, 0.11]
dresserbottles[0].rotation = [0, 0, 0]
mirror_A[0].position = [0.745050881565295, 2.4306356280225097, 0.8]
mirror_A[0].rotation = [0, 0, 0]
vase_D[0].position = [2.228648873653603, 0.9591795088119386, 0.11]
vase_D[0].rotation = [0, 0, 0]
tablecandle[0].position = [2.52422684079237, 0.5123515333063136, 0.07]
tablecandle[0].rotation = [0, 0, 0]
print[0].position = [3.080778366978322, 2.9385469891729152, 0.475]
print[0].rotation = [0, 0, 0]
candle_C[0].position = [1.0295189599318526, 1.716121610292658, 0.075]
candle_C[0].rotation = [0, 0, 0]
table[0].position = [0.26152996867321443, 4.002857743177015, 0.39]
table[0].rotation = [0, 0, 0]
vase_E[0].position = [2.0811864573986436, 1.4104814197144873, 0.115]
vase_E[0].rotation = [0, 0, 0]
pillow[0].position = [1.0881947438326276, 2.1007509863713363, 0.24]
pillow[0].rotation = [0, 0, 0]
floorplant_B[0].position = [2.1552174489217113, 0.6951538539653176, 0.275]
floorplant_B[0].rotation = [0, 0, 0]
lamp_C[0].position = [1.414237913860568, 2.376003367975873, 0.23]
lamp_C[0].rotation = [0, 0, 0]
candle_D[0].position = [0.28760970562063637, 2.2395069133088974, 0.05]
candle_D[0].rotation = [0, 0, 0]
dresserbottle[0].position = [2.2470464341996066, 0.009583556073613386, 0.1]
dresserbottle[0].rotation = [0, 0, 0]
candle_E[0].position = [0.000733290563873279, 2.36636726632706, 0.075]
candle_E[0].rotation = [0, 0, 0]
plant_D[0].position = [2.910683439968841, 2.8106163385351515, 0.19]
plant_D[0].rotation = [0, 0, 0]
book_H[0].position = [1.1637770158133858, 3.3415795568173676, 0.02]
book_H[0].rotation = [0, 0, 0]
candle_F[0].position = [3.440751982817018, 4.425902116614943, 0.09]
candle_F[0].rotation = [0, 0, 0]
plant_E[0].position = [0.8490161807139196, 1.0483944349651309, 0.19]
plant_E[0].rotation = [0, 0, 0]
bottle_A[0].position = [1.3771567023526154, 2.3102749758000765, 0.09]
bottle_A[0].rotation = [0, 0, 0]
dresserbook_B[0].position = [3.078591569342173, 2.151765927762664, 0.02]
dresserbook_B[0].rotation = [0, 0, 0]
mirror_B[0].position = [0.7541886589743929, 0.8890615341956196, 0.8]
mirror_B[0].rotation = [0, 0, 0]
plant_F[0].position = [0.8636814855241504, 2.698333083779226, 0.21]
plant_F[0].rotation = [0, 0, 0]
bottle_B[0].position = [1.5385021354769202, 2.027881184640512, 0.095]
bottle_B[0].rotation = [0, 0, 0]
dresser[0].position = [0.36428980404346856, 1.4614372197498777, 0.41]
dresser[0].rotation = [0, 0, 0]
bottle_C[0].position = [0.9004737437669781, 0.3473044156047224, 0.09]
bottle_C[0].rotation = [0, 0, 0]
nightstandbook_A[0].position = [1.3015277271307024, 1.308587523956886, 0.02]
nightstandbook_A[0].rotation = [0, 0, 0]
nightstand2candle[0].position = [2.1169481368769354, 4.078154030582176, 0.07]
nightstand2candle[0].rotation = [0, 0, 0]
book_I[0].position = [2.9512180041190823, 3.6379919855184406, 0.145]
book_I[0].rotation = [0, 0, 0]
book_J[0].position = [0.21578171621803666, 2.682259440583695, 0.15]
book_J[0].rotation = [0, 0, 0]
nightstand1book[0].position = [1.0976227953395608, 2.354739948912946, 0.02]
nightstand1book[0].rotation = [0, 0, 0]
plant_G[0].position = [1.6550328362548723, 0.6236915919267312, 0.375]
plant_G[0].rotation = [0, 0, 0]
dresserbook_C[0].position = [3.871647421018425, 3.9947788360597176, 0.02]
dresserbook_C[0].rotation = [0, 0, 0]
book_K[0].position = [1.7497664336980843, 3.2691370861073397, 0.02]
book_K[0].rotation = [0, 0, 0]
candle_G[0].position = [2.2658961384837415, 0.17554573926240424, 0.08]
candle_G[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.4311668515918168, 0.9251665012594396, 1.1]
wardrobe[0].rotation = [0, 0, 0]
dresserbooks_A[0].position = [1.980440887763843, 0.26397732845197447, 0.02]
dresserbooks_A[0].rotation = [0, 0, 0]
bookshelf[0].position = [0.04169505400310136, 4.304845868245981, 0.95]
bookshelf[0].rotation = [0, 0, 0]
candle_H[0].position = [1.1344304020925535, 2.5217735829337746, 0.06]
candle_H[0].rotation = [0, 0, 0]
bottle_D[0].position = [2.5554594760395726, 3.996878785944301, 0.09]
bottle_D[0].rotation = [0, 0, 0]
nightstandbook_B[0].position = [2.231592741847648, 1.2394078297259037, 0.02]
nightstandbook_B[0].rotation = [0, 0, 0]
bed[0].position = [3.199092747972033, 0.9804668002706964, 0.625]
bed[0].rotation = [0, 0, 0]
book_L[0].position = [3.4425143862672742, 4.434813233436457, 0.02]
book_L[0].rotation = [0, 0, 0]
nightstand_B[0].position = [3.198812959523284, 4.063915965627971, 0.31]
nightstand_B[0].rotation = [0, 0, 0]
book_M[0].position = [2.1366351754231783, 2.468792713357141, 0.02]
book_M[0].rotation = [0, 0, 0]
tablebook_B[0].position = [1.8998015658694243, 3.307246160656034, 0.02]
tablebook_B[0].rotation = [0, 0, 0]
dresserbooks_B[0].position = [2.8597748653848742, 2.6570540717555104, 0.02]
dresserbooks_B[0].rotation = [0, 0, 0]
candle_I[0].position = [0.5782604762007968, 2.664574605310242, 0.09]
candle_I[0].rotation = [0, 0, 0]
book_N[0].position = [3.657282753920612, 1.3897615362613025, 0.0175]
book_N[0].rotation = [0, 0, 0]
bench[0].position = [3.0091458744045467, 2.321240227884995, 0.24]
bench[0].rotation = [0, 0, 0]
book_O[0].position = [2.9125660149101704, 2.3972779900644596, 0.02]
book_O[0].rotation = [0, 0, 0]
plant_H[0].position = [0.12149276323321567, 2.5663725578686036, 0.19]
plant_H[0].rotation = [0, 0, 0]
bookshelfbook[0].position = [2.224539197170928, 0.0018498661113174886, 0.145]
bookshelfbook[0].rotation = [0, 0, 0]
vase_F[0].position = [2.693949485360208, 3.696979803313972, 0.115]
vase_F[0].rotation = [0, 0, 0]
candle_A[0].position = [2.212778459339815, 0.31982691876195973, 0.09]
candle_A[0].rotation = [0, 0, 0]
book_A[0].position = [2.9384444118230815, 2.9051092224487265, 0.02]
book_A[0].rotation = [0, 0, 0]
book_B[0].position = [3.180591559907824, 1.6179221656381442, 0.02]
book_B[0].rotation = [0, 0, 0]
book_C[0].position = [1.200681414842463, 1.606954107257928, 0.02]
book_C[0].rotation = [0, 0, 0]
lamp_A[0].position = [2.93439858505064, 1.4039552274818459, 0.24]
lamp_A[0].rotation = [0, 0, 0]
chair[0].position = [1.2662609949190955, 2.835775215839085, 0.41]
chair[0].rotation = [0, 0, 0]
plant_A[0].position = [0.7274008619910934, 1.9217469672971426, 0.225]
plant_A[0].rotation = [0, 0, 0]
tablebook_A[0].position = [1.5713488972518777, 3.4810115642044384, 0.02]
tablebook_A[0].rotation = [0, 0, 0]
lamp_B[0].position = [2.8319593573294766, 1.0465180340453084, 0.775]
lamp_B[0].rotation = [0, 0, 0]
vase_A[0].position = [0.7893702896211106, 2.7041651112271103, 0.16]
vase_A[0].rotation = [0, 0, 0]
plant_B[0].position = [3.154334085785304, 1.498989735004497, 0.225]
plant_B[0].rotation = [0, 0, 0]
book_D[0].position = [3.1284830382037416, 2.506587358432219, 0.02]
book_D[0].rotation = [0, 0, 0]
book_E[0].position = [2.906725914723324, 1.617492824039245, 0.0175]
book_E[0].rotation = [0, 0, 0]
plant_C[0].position = [3.623452988990852, 1.9020319386460178, 0.21]
plant_C[0].rotation = [0, 0, 0]
ottoman[0].position = [3.242099199404472, 1.4573585687636808, 0.21]
ottoman[0].rotation = [0, 0, 0]
floorplant_A[0].position = [3.490804719266035, 4.015756813754161, 0.275]
floorplant_A[0].rotation = [0, 0, 0]
dresserbook_A[0].position = [1.548582857389154, 3.7009356991769162, 0.02]
dresserbook_A[0].rotation = [0, 0, 0]
book_F[0].position = [1.9566741694912992, 3.713254462504878, 0.02]
book_F[0].rotation = [0, 0, 0]
book_G[0].position = [1.2105328965287874, 2.9472029697039486, 0.0175]
book_G[0].rotation = [0, 0, 0]
nightstand_A[0].position = [3.683681525280227, 0.6557485124168307, 0.31]
nightstand_A[0].rotation = [0, 0, 0]
vase_B[0].position = [0.824893864768808, 1.718203290949262, 0.12]
vase_B[0].rotation = [0, 0, 0]
candle_B[0].position = [0.26841463421690515, 3.74316834806102, 0.08]
candle_B[0].rotation = [0, 0, 0]
vase_C[0].position = [0.18800006960658822, 0.5415757151782279, 0.12]
vase_C[0].rotation = [0, 0, 0]
dresserbottles[0].position = [3.245696891615653, 0.8823007196954915, 0.11]
dresserbottles[0].rotation = [0, 0, 0]
mirror_A[0].position = [0.745050881565295, 2.4306356280225097, 0.8]
mirror_A[0].rotation = [0, 0, 0]
vase_D[0].position = [2.228648873653603, 0.9591795088119386, 0.11]
vase_D[0].rotation = [0, 0, 0]
tablecandle[0].position = [2.52422684079237, 0.5123515333063136, 0.07]
tablecandle[0].rotation = [0, 0, 0]
print[0].position = [3.080778366978322, 2.9385469891729152, 0.475]
print[0].rotation = [0, 0, 0]
candle_C[0].position = [1.0295189599318526, 1.716121610292658, 0.075]
candle_C[0].rotation = [0, 0, 0]
table[0].position = [0.26152996867321443, 4.002857743177015, 0.39]
table[0].rotation = [0, 0, 0]
vase_E[0].position = [2.0811864573986436, 1.4104814197144873, 0.115]
vase_E[0].rotation = [0, 0, 0]
pillow[0].position = [1.0881947438326276, 2.1007509863713363, 0.24]
pillow[0].rotation = [0, 0, 0]
floorplant_B[0].position = [2.1552174489217113, 0.6951538539653176, 0.275]
floorplant_B[0].rotation = [0, 0, 0]
lamp_C[0].position = [1.414237913860568, 2.376003367975873, 0.23]
lamp_C[0].rotation = [0, 0, 0]
candle_D[0].position = [0.28760970562063637, 2.2395069133088974, 0.05]
candle_D[0].rotation = [0, 0, 0]
dresserbottle[0].position = [2.2470464341996066, 0.009583556073613386, 0.1]
dresserbottle[0].rotation = [0, 0, 0]
candle_E[0].position = [0.000733290563873279, 2.36636726632706, 0.075]
candle_E[0].rotation = [0, 0, 0]
plant_D[0].position = [2.910683439968841, 2.8106163385351515, 0.19]
plant_D[0].rotation = [0, 0, 0]
book_H[0].position = [1.1637770158133858, 3.3415795568173676, 0.02]
book_H[0].rotation = [0, 0, 0]
candle_F[0].position = [3.440751982817018, 4.425902116614943, 0.09]
candle_F[0].rotation = [0, 0, 0]
plant_E[0].position = [0.8490161807139196, 1.0483944349651309, 0.19]
plant_E[0].rotation = [0, 0, 0]
bottle_A[0].position = [1.3771567023526154, 2.3102749758000765, 0.09]
bottle_A[0].rotation = [0, 0, 0]
dresserbook_B[0].position = [3.078591569342173, 2.151765927762664, 0.02]
dresserbook_B[0].rotation = [0, 0, 0]
mirror_B[0].position = [0.7541886589743929, 0.8890615341956196, 0.8]
mirror_B[0].rotation = [0, 0, 0]
plant_F[0].position = [0.8636814855241504, 2.698333083779226, 0.21]
plant_F[0].rotation = [0, 0, 0]
bottle_B[0].position = [1.5385021354769202, 2.027881184640512, 0.095]
bottle_B[0].rotation = [0, 0, 0]
dresser[0].position = [0.36428980404346856, 1.4614372197498777, 0.41]
dresser[0].rotation = [0, 0, 0]
bottle_C[0].position = [0.9004737437669781, 0.3473044156047224, 0.09]
bottle_C[0].rotation = [0, 0, 0]
nightstandbook_A[0].position = [1.3015277271307024, 1.308587523956886, 0.02]
nightstandbook_A[0].rotation = [0, 0, 0]
nightstand2candle[0].position = [2.1169481368769354, 4.078154030582176, 0.07]
nightstand2candle[0].rotation = [0, 0, 0]
book_I[0].position = [2.9512180041190823, 3.6379919855184406, 0.145]
book_I[0].rotation = [0, 0, 0]
book_J[0].position = [0.21578171621803666, 2.682259440583695, 0.15]
book_J[0].rotation = [0, 0, 0]
nightstand1book[0].position = [1.0976227953395608, 2.354739948912946, 0.02]
nightstand1book[0].rotation = [0, 0, 0]
plant_G[0].position = [1.6550328362548723, 0.6236915919267312, 0.375]
plant_G[0].rotation = [0, 0, 0]
dresserbook_C[0].position = [3.871647421018425, 3.9947788360597176, 0.02]
dresserbook_C[0].rotation = [0, 0, 0]
book_K[0].position = [1.7497664336980843, 3.2691370861073397, 0.02]
book_K[0].rotation = [0, 0, 0]
candle_G[0].position = [2.2658961384837415, 0.17554573926240424, 0.08]
candle_G[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.4311668515918168, 0.9251665012594396, 1.1]
wardrobe[0].rotation = [0, 0, 0]
dresserbooks_A[0].position = [1.980440887763843, 0.26397732845197447, 0.02]
dresserbooks_A[0].rotation = [0, 0, 0]
bookshelf[0].position = [0.04169505400310136, 4.304845868245981, 0.95]
bookshelf[0].rotation = [0, 0, 0]
candle_H[0].position = [1.1344304020925535, 2.5217735829337746, 0.06]
candle_H[0].rotation = [0, 0, 0]
bottle_D[0].position = [2.5554594760395726, 3.996878785944301, 0.09]
bottle_D[0].rotation = [0, 0, 0]
nightstandbook_B[0].position = [2.231592741847648, 1.2394078297259037, 0.02]
nightstandbook_B[0].rotation = [0, 0, 0]
bed[0].position = [3.199092747972033, 0.9804668002706964, 0.625]
bed[0].rotation = [0, 0, 0]
book_L[0].position = [3.4425143862672742, 4.434813233436457, 0.02]
book_L[0].rotation = [0, 0, 0]
nightstand_B[0].position = [3.198812959523284, 4.063915965627971, 0.31]
nightstand_B[0].rotation = [0, 0, 0]
book_M[0].position = [2.1366351754231783, 2.468792713357141, 0.02]
book_M[0].rotation = [0, 0, 0]
tablebook_B[0].position = [1.8998015658694243, 3.307246160656034, 0.02]
tablebook_B[0].rotation = [0, 0, 0]
dresserbooks_B[0].position = [2.8597748653848742, 2.6570540717555104, 0.02]
dresserbooks_B[0].rotation = [0, 0, 0]
candle_I[0].position = [0.5782604762007968, 2.664574605310242, 0.09]
candle_I[0].rotation = [0, 0, 0]
book_N[0].position = [3.657282753920612, 1.3897615362613025, 0.0175]
book_N[0].rotation = [0, 0, 0]
bench[0].position = [3.0091458744045467, 2.321240227884995, 0.24]
bench[0].rotation = [0, 0, 0]
book_O[0].position = [2.9125660149101704, 2.3972779900644596, 0.02]
book_O[0].rotation = [0, 0, 0]
plant_H[0].position = [0.12149276323321567, 2.5663725578686036, 0.19]
plant_H[0].rotation = [0, 0, 0]
bookshelfbook[0].position = [2.224539197170928, 0.0018498661113174886, 0.145]
bookshelfbook[0].rotation = [0, 0, 0]
vase_F[0].position = [2.693949485360208, 3.696979803313972, 0.115]
vase_F[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed-point helpers provide explicit position and orientation constraints while
# preserving the more important wall, support, and semantic constraints first.
def _fixed_pose(x, y, z, yaw):
    return AssetInstance(position=[x, y, z], rotation=[0, 0, yaw])


def _place_floor(asset_obj, x, y, yaw=0.0, wall=None, face_target=None):
    z = asset_obj.size[2] / 2
    asset_obj.placements[0].position = [x, y, z]
    asset_obj.placements[0].rotation = [0, 0, yaw]

    if wall is not None:
        solver.against_wall(asset_obj[0], wall)

    pose_anchor = _fixed_pose(x, y, z, yaw)
    solver.distance_constraint(asset_obj[0], pose_anchor, 0, 0, weight=10)

    if face_target is not None:
        solver.point_towards(asset_obj[0], face_target)
    else:
        solver.align_with(asset_obj[0], pose_anchor)


def _place_on(asset_obj, support_obj, x, y, z, yaw=0.0):
    asset_obj.placements[0].position = [x, y, z]
    asset_obj.placements[0].rotation = [0, 0, yaw]

    # Support is the primary vertical relationship. The fixed point preserves
    # the selected spot on the supporting surface during feasibility adjustment.
    solver.on_top_of(asset_obj[0], support_obj[0])
    pose_anchor = _fixed_pose(x, y, z, yaw)
    solver.distance_constraint(asset_obj[0], pose_anchor, 0, 0, weight=10)
    solver.align_with(asset_obj[0], pose_anchor)


def _place_wall_item(asset_obj, wall, x, y, z, yaw):
    asset_obj.placements[0].position = [x, y, z]
    asset_obj.placements[0].rotation = [0, 0, yaw]

    solver.against_wall(asset_obj[0], wall)
    pose_anchor = _fixed_pose(x, y, z, yaw)
    solver.distance_constraint(asset_obj[0], pose_anchor, 0, 0, weight=10)
    solver.align_with(asset_obj[0], pose_anchor)


# ---------------------------------------------------------------------------
# Main furniture layout
#
# The bed is oriented toward the bookshelf on the left wall. The narrow bench
# sits at the foot of the bed, and the two nightstands flank the head end.
# The doorway zone around x=0.66..1.56, y=4.50 is intentionally left clear.
# ---------------------------------------------------------------------------

_place_floor(bookshelf, 0.16, 2.05, radians(0), wall=walls[2])
_place_floor(
    bed, 2.80, 2.25, radians(180),
    face_target=bookshelf[0],
)

# Explicitly reinforce the requested bed-to-bookshelf relationship.
solver.point_towards(bed[0], bookshelf[0])

_place_floor(bench, 1.40, 2.25, radians(0))
solver.align_with(bench[0], bed[0])

_place_floor(nightstand_A, 3.68, 0.75, radians(180), wall=walls[0])
_place_floor(nightstand_B, 3.68, 3.60, radians(180), wall=walls[0])
solver.align_with(nightstand_A[0], bed[0])
solver.align_with(nightstand_B[0], bed[0])

# The dresser uses the lower wall; rotating it places its long dimension along
# that wall while preserving circulation between it and the bed.
_place_floor(dresser, 2.60, 0.26, radians(90), wall=walls[3])

# The wardrobe occupies the upper-right wall, outside the door opening.
_place_floor(wardrobe, 2.75, 4.19, radians(-90), wall=walls[1])

# A shallow console occupies the upper part of the left wall without entering
# the centered door's approach corridor.
_place_floor(table, 0.19, 3.25, radians(0), wall=walls[2])

# ---------------------------------------------------------------------------
# Reading area
#
# The chair is geometrically between the two floor plants, with an ottoman in
# front of it. Equal plant distances help retain that semantic relationship.
# ---------------------------------------------------------------------------

_place_floor(floorplant_A, 0.18, 0.55, radians(0), wall=walls[2])
_place_floor(floorplant_B, 1.42, 0.55, radians(0))

chair.placements[0].position = [0.80, 0.55, chair.size[2] / 2]
chair.placements[0].rotation = [0, 0, radians(90)]

# These equal distances are specified before the fixed anchor because the
# "chair between plants" relationship is the most important position semantics.
solver.distance_constraint(
    chair[0], floorplant_A[0], 0.60, 0.64, weight=10
)
solver.distance_constraint(
    chair[0], floorplant_B[0], 0.60, 0.64, weight=10
)
solver.distance_constraint(
    chair[0],
    _fixed_pose(0.80, 0.55, chair.size[2] / 2, radians(90)),
    0, 0, weight=10,
)

_place_floor(ottoman, 0.75, 1.35, radians(0))
solver.point_towards(chair[0], ottoman[0])
solver.align_with(ottoman[0], chair[0])

_place_floor(lamp_B, 0.22, 1.35, radians(0), wall=walls[2])
solver.point_towards(lamp_B[0], chair[0])

# Additional floor plant fills the open area beside the bookshelf while
# remaining outside the door approach and the bed/bench footprints.
_place_floor(plant_G, 0.75, 2.95, radians(0))
solver.point_towards(plant_G[0], chair[0])

# ---------------------------------------------------------------------------
# Wall-mounted decoration
# ---------------------------------------------------------------------------

_place_wall_item(mirror_A, walls[3], 2.60, 0.02, 1.72, radians(90))
_place_wall_item(mirror_B, walls[0], 3.98, 2.25, 1.72, radians(180))
_place_wall_item(print, walls[2], 0.02, 3.25, 1.48, radians(0))

# ---------------------------------------------------------------------------
# Left console arrangement
# ---------------------------------------------------------------------------

# Book stack on the console.
_place_on(tablebook_A, table, 0.19, 3.22, 0.80, radians(0))
_place_on(tablebook_B, tablebook_A, 0.19, 3.22, 0.84, radians(0))
_place_on(book_A, tablebook_B, 0.19, 3.22, 0.88, radians(0))
_place_on(book_B, book_A, 0.19, 3.22, 0.92, radians(0))
_place_on(book_C, book_B, 0.19, 3.22, 0.96, radians(0))
_place_on(candle_A, book_C, 0.19, 3.22, 1.07, radians(0))

# Lamp and decorative objects are spaced along the long console top.
_place_on(lamp_A, table, 0.19, 3.78, 1.02, radians(180))
_place_on(vase_E, table, 0.19, 2.84, 0.895, radians(0))
_place_on(tablecandle, table, 0.19, 3.48, 0.85, radians(0))

# ---------------------------------------------------------------------------
# Dresser arrangement
# ---------------------------------------------------------------------------

# Left book stack with a vase.
_place_on(dresserbook_A, dresser, 2.00, 0.26, 0.84, radians(90))
_place_on(dresserbook_B, dresserbook_A, 2.00, 0.26, 0.88, radians(90))
_place_on(dresserbook_C, dresserbook_B, 2.00, 0.26, 0.92, radians(90))
_place_on(vase_B, dresserbook_C, 2.00, 0.26, 1.06, radians(0))

# Center-left stack with a candle.
_place_on(dresserbooks_A, dresser, 2.38, 0.26, 0.84, radians(90))
_place_on(book_D, dresserbooks_A, 2.38, 0.26, 0.88, radians(90))
_place_on(book_E, book_D, 2.38, 0.26, 0.92, radians(90))
_place_on(candle_B, book_E, 2.38, 0.26, 1.02, radians(0))

# Center-right stack with a compact plant.
_place_on(dresserbooks_B, dresser, 2.78, 0.26, 0.84, radians(90))
_place_on(book_F, dresserbooks_B, 2.78, 0.26, 0.88, radians(90))
_place_on(book_G, book_F, 2.78, 0.26, 0.92, radians(90))
_place_on(plant_D, book_G, 2.78, 0.26, 1.13, radians(0))

# Small bottles and a vase occupy the remaining right side of the dresser.
_place_on(dresserbottles, dresser, 3.06, 0.18, 0.93, radians(0))
_place_on(dresserbottle, dresser, 3.18, 0.18, 0.92, radians(0))
_place_on(bottle_A, dresser, 3.30, 0.18, 0.91, radians(0))
_place_on(vase_C, dresser, 3.18, 0.39, 0.94, radians(0))

# ---------------------------------------------------------------------------
# Nightstands
# ---------------------------------------------------------------------------

# Lower nightstand: the lamp is centered over a book, with a small side vase.
_place_on(nightstand1book, nightstand_A, 3.68, 0.70, 0.64, radians(180))
_place_on(lamp_C, nightstand1book, 3.68, 0.70, 0.89, radians(180))
_place_on(vase_D, nightstand_A, 3.68, 0.98, 0.73, radians(0))

# Upper nightstand: the required nightstand2candle is directly on this
# nightstand. Its support constraint is deliberately specified first.
_place_on(nightstandbook_A, nightstand_B, 3.68, 3.43, 0.64, radians(180))
_place_on(candle_D, nightstandbook_A, 3.68, 3.43, 0.71, radians(0))

_place_on(nightstandbook_B, nightstand_B, 3.68, 3.72, 0.64, radians(180))
_place_on(nightstand2candle, nightstand_B, 3.68, 3.72, 0.69, radians(0))
_place_on(candle_E, nightstandbook_B, 3.68, 3.72, 0.735, radians(0))

# ---------------------------------------------------------------------------
# Bookshelf-top arrangement
# ---------------------------------------------------------------------------

# Upright books use their narrow x dimension and are distributed along the
# bookshelf's top. Each remains constrained to the bookshelf.
_place_on(book_I, bookshelf, 0.16, 1.78, 2.045, radians(0))
_place_on(book_J, bookshelf, 0.16, 2.00, 2.05, radians(0))
_place_on(bookshelfbook, bookshelf, 0.16, 2.23, 2.045, radians(0))

# A short horizontal stack and candle fill the remaining end.
_place_on(book_H, bookshelf, 0.16, 2.39, 1.92, radians(0))
_place_on(book_K, book_H, 0.16, 2.39, 1.96, radians(0))
_place_on(candle_F, book_K, 0.16, 2.39, 2.07, radians(0))

# ---------------------------------------------------------------------------
# Bench accessories
# ---------------------------------------------------------------------------

# Two compact book stacks leave most of the upholstered bench usable.
_place_on(book_L, bench, 1.40, 1.88, 0.50, radians(0))
_place_on(book_M, book_L, 1.40, 1.88, 0.54, radians(0))
_place_on(book_N, book_M, 1.40, 1.88, 0.58, radians(0))
_place_on(candle_G, book_N, 1.40, 1.88, 0.68, radians(0))

_place_on(book_O, bench, 1.40, 2.61, 0.50, radians(0))
_place_on(candle_H, book_O, 1.40, 2.61, 0.58, radians(0))
_place_on(vase_F, candle_H, 1.40, 2.61, 0.755, radians(0))

# ---------------------------------------------------------------------------
# Remaining decorative pieces
# ---------------------------------------------------------------------------

# Pillow is placed toward the bed's head end.
_place_on(pillow, bed, 3.55, 2.25, 1.49, radians(180))
solver.align_with(pillow[0], bed[0])

# Plants and decorations are grouped into stable stacks on larger surfaces.
_place_on(plant_A, tablebook_A, 0.19, 3.22, 1.205, radians(0))
_place_on(plant_B, dresser, 3.00, 0.39, 1.045, radians(0))
_place_on(plant_C, table, 0.19, 3.00, 0.99, radians(0))

_place_on(plant_E, dresser, 2.50, 0.26, 1.01, radians(0))
_place_on(plant_F, table, 0.19, 3.55, 0.99, radians(0))
_place_on(plant_H, nightstand_A, 3.68, 0.98, 0.81, radians(0))

_place_on(vase_A, table, 0.19, 2.62, 0.94, radians(0))
_place_on(candle_C, vase_A, 0.19, 2.62, 1.175, radians(0))
_place_on(candle_I, vase_E, 0.19, 2.84, 1.10, radians(0))

# Remaining cosmetic bottles form a small grouped arrangement on the dresser.
_place_on(bottle_B, dresser, 3.06, 0.39, 0.915, radians(0))
_place_on(bottle_C, dresser, 3.18, 0.39, 0.91, radians(0))
_place_on(bottle_D, dresser, 3.30, 0.39, 0.91, radians(0))

solver.constraints = []
candle_H[0].position = [1.399999976158142, 2.609999895095825, 0.5799999833106995]
candle_H[0].rotation = [0, 0, 0.0157079639172164]
candle_H[0].optimize = 2
nightstand2candle[0].position = [3.680000066757202, 3.7200000286102295, 0.6899999976158142]
nightstand2candle[0].rotation = [0, 0, 0.01256637125682779]
nightstand2candle[0].optimize = 2
floorplant_B[0].position = [1.4199999570846558, 0.550000011920929, 0.2750000059604645]
floorplant_B[0].rotation = [0, 0, 0.01256637125682779]
floorplant_B[0].optimize = 2
tablebook_B[0].position = [0.1899999976158142, 3.2200000286102295, 0.8399999141693115]
tablebook_B[0].rotation = [0, 0, 0.0157079639172164]
tablebook_B[0].optimize = 2
plant_C[0].position = [0.1899999976158142, 3.0, 0.9899999499320984]
plant_C[0].rotation = [0, 0, 0.01256637125682779]
plant_C[0].optimize = 2
dresserbook_A[0].position = [2.0, 0.25999999046325684, 0.8399999737739563]
dresserbook_A[0].rotation = [0, 0, 1.586504290712113]
dresserbook_A[0].optimize = 2
candle_B[0].position = [2.380000114440918, 0.25999999046325684, 1.0199998617172241]
candle_B[0].rotation = [0, 0, 0.01256637125682779]
candle_B[0].optimize = 2
vase_C[0].position = [3.180000066757202, 0.38999998569488525, 0.9399999976158142]
vase_C[0].rotation = [0, 0, 0.01256637125682779]
vase_C[0].optimize = 2
print[0].position = [0.011367769911885262, 3.25, 0.4749999940395355]
print[0].rotation = [0, 0, 0.0025409172284856325]
print[0].optimize = 2
dresserbooks_B[0].position = [2.7799999713897705, 0.25999999046325684, 0.8399999737739563]
dresserbooks_B[0].rotation = [0, 0, 1.586504290712113]
dresserbooks_B[0].optimize = 2
plant_B[0].position = [3.0, 0.38999998569488525, 1.0449999570846558]
plant_B[0].rotation = [0, 0, 0.01256637125682779]
plant_B[0].optimize = 2
candle_G[0].position = [1.399999976158142, 1.8799999952316284, 0.6799998879432678]
candle_G[0].rotation = [0, 0, 0.01256637125682779]
candle_G[0].optimize = 2
lamp_A[0].position = [0.1899999976158142, 3.7799999713897705, 1.0199999809265137]
lamp_A[0].rotation = [0, 0, -3.1290262823329655]
lamp_A[0].optimize = 2
book_E[0].position = [2.380000114440918, 0.25999999046325684, 0.919999897480011]
book_E[0].rotation = [0, 0, 1.586504290712113]
book_E[0].optimize = 2
vase_E[0].position = [0.1899999976158142, 2.8399999141693115, 0.8949999809265137]
vase_E[0].rotation = [0, 0, 0.0157079639172164]
vase_E[0].optimize = 2
book_G[0].position = [2.7799999713897705, 0.25999999046325684, 0.919999897480011]
book_G[0].rotation = [0, 0, 1.586504290712113]
book_G[0].optimize = 2
book_H[0].position = [0.1599999964237213, 2.390000104904175, 1.9199999570846558]
book_H[0].rotation = [0, 0, 0.0157079639172164]
book_H[0].optimize = 2
book_N[0].position = [1.399999976158142, 1.8799999952316284, 0.5799999237060547]
book_N[0].rotation = [0, 0, 0.0157079639172164]
book_N[0].optimize = 2
dresserbook_C[0].position = [2.0, 0.25999999046325684, 0.919999897480011]
dresserbook_C[0].rotation = [0, 0, 1.586504290712113]
dresserbook_C[0].optimize = 2
book_M[0].position = [1.399999976158142, 1.8799999952316284, 0.5399999618530273]
book_M[0].rotation = [0, 0, 0.0157079639172164]
book_M[0].optimize = 2
plant_G[0].position = [0.75, 2.950000047683716, 0.375]
plant_G[0].rotation = [0, 0, 0.0025408394800257414]
plant_G[0].optimize = 2
bench[0].position = [1.399999976158142, 2.25, 0.23999999463558197]
bench[0].rotation = [0, 0, 0.008763684994140498]
bench[0].optimize = 2
dresser[0].position = [2.5999999046325684, 0.2886110246181488, 0.4099999964237213]
dresser[0].rotation = [0, 0, 1.6106709595346709]
dresser[0].optimize = 2
nightstand_B[0].position = [3.690000057220459, 3.5999999046325684, 0.3100000023841858]
nightstand_B[0].rotation = [0, 0, -3.126608736669681]
nightstand_B[0].optimize = 2
bookshelfbook[0].position = [0.1599999964237213, 2.2300000190734863, 2.0450000762939453]
bookshelfbook[0].rotation = [0, 0, 0.01256637125682779]
bookshelfbook[0].optimize = 2
candle_C[0].position = [0.1899999976158142, 2.619999885559082, 1.1749999523162842]
candle_C[0].rotation = [0, 0, 0.01256637125682779]
candle_C[0].optimize = 2
dresserbooks_A[0].position = [2.380000114440918, 0.25999999046325684, 0.8399999737739563]
dresserbooks_A[0].rotation = [0, 0, 1.586504290712113]
dresserbooks_A[0].optimize = 2
book_O[0].position = [1.399999976158142, 2.609999895095825, 0.5]
book_O[0].rotation = [0, 0, 0.0157079639172164]
book_O[0].optimize = 2
plant_F[0].position = [0.1899999976158142, 3.549999952316284, 0.9899999499320984]
plant_F[0].rotation = [0, 0, 0.01256637125682779]
plant_F[0].optimize = 2
vase_A[0].position = [0.1899999976158142, 2.619999885559082, 0.9399999380111694]
vase_A[0].rotation = [0, 0, 0.0157079639172164]
vase_A[0].optimize = 2
floorplant_A[0].position = [0.18101441860198975, 0.550000011920929, 0.2750000059604645]
floorplant_A[0].rotation = [0, 0, 0.005651525783277624]
floorplant_A[0].optimize = 2
mirror_B[0].position = [3.9886972904205322, 2.25, 0.800000011920929]
mirror_B[0].rotation = [0, 0, -3.1390517354391343]
mirror_B[0].optimize = 2
book_B[0].position = [0.1899999976158142, 3.2200000286102295, 0.9199998378753662]
book_B[0].rotation = [0, 0, 0.0157079639172164]
book_B[0].optimize = 2
plant_D[0].position = [2.7799999713897705, 0.25999999046325684, 1.1299998760223389]
plant_D[0].rotation = [0, 0, 0.01256637125682779]
plant_D[0].optimize = 2
dresserbook_B[0].position = [2.0, 0.25999999046325684, 0.8799999356269836]
dresserbook_B[0].rotation = [0, 0, 1.586504290712113]
dresserbook_B[0].optimize = 2
bottle_B[0].position = [3.059999942779541, 0.38999998569488525, 0.9149999618530273]
bottle_B[0].rotation = [0, 0, 0.01256637125682779]
bottle_B[0].optimize = 2
plant_E[0].position = [2.5, 0.25999999046325684, 1.0099999904632568]
plant_E[0].rotation = [0, 0, 0.01256637125682779]
plant_E[0].optimize = 2
nightstand_A[0].position = [3.690000057220459, 0.75, 0.3100000023841858]
nightstand_A[0].rotation = [0, 0, -3.126608736669681]
nightstand_A[0].optimize = 2
book_J[0].position = [0.1599999964237213, 2.0, 2.049999952316284]
book_J[0].rotation = [0, 0, 0.01256637125682779]
book_J[0].optimize = 2
plant_H[0].position = [3.680000066757202, 0.9800000190734863, 0.8100000023841858]
plant_H[0].rotation = [0, 0, 0.01256637125682779]
plant_H[0].optimize = 2
book_L[0].position = [1.399999976158142, 1.8799999952316284, 0.5]
book_L[0].rotation = [0, 0, 0.0157079639172164]
book_L[0].optimize = 2
table[0].position = [0.20407210290431976, 3.25, 0.38999998569488525]
table[0].rotation = [0, 0, 0.024317188933281386]
table[0].optimize = 2
book_A[0].position = [0.1899999976158142, 3.2200000286102295, 0.8799998760223389]
book_A[0].rotation = [0, 0, 0.0157079639172164]
book_A[0].optimize = 2
plant_A[0].position = [0.1899999976158142, 3.2200000286102295, 1.0449999570846558]
plant_A[0].rotation = [0, 0, 0.01256637125682779]
plant_A[0].optimize = 2
candle_D[0].position = [3.680000066757202, 3.430000066757202, 0.7099999785423279]
candle_D[0].rotation = [0, 0, 0.01256637125682779]
candle_D[0].optimize = 2
bed[0].position = [2.799999952316284, 2.25, 0.625]
bed[0].rotation = [0, 0, -3.113318319178201]
bed[0].optimize = 2
nightstandbook_A[0].position = [3.680000066757202, 3.430000066757202, 0.6399999856948853]
nightstandbook_A[0].rotation = [0, 0, -3.125884689672577]
nightstandbook_A[0].optimize = 2
candle_I[0].position = [0.1899999976158142, 2.8399999141693115, 1.100000023841858]
candle_I[0].rotation = [0, 0, 0.01256637125682779]
candle_I[0].optimize = 2
candle_E[0].position = [3.680000066757202, 3.7200000286102295, 0.73499995470047]
candle_E[0].rotation = [0, 0, 0.01256637125682779]
candle_E[0].optimize = 2
candle_A[0].position = [0.1899999976158142, 3.2200000286102295, 1.0699998140335083]
candle_A[0].rotation = [0, 0, 0.01256637125682779]
candle_A[0].optimize = 2
book_F[0].position = [2.7799999713897705, 0.25999999046325684, 0.8799999356269836]
book_F[0].rotation = [0, 0, 1.586504290712113]
book_F[0].optimize = 2
vase_D[0].position = [3.680000066757202, 0.9800000190734863, 0.7300000190734863]
vase_D[0].rotation = [0, 0, 0.01256637125682779]
vase_D[0].optimize = 2
bookshelf[0].position = [0.16327081620693207, 2.049999952316284, 0.949999988079071]
bookshelf[0].rotation = [0, 0, 0.02120600154932367]
bookshelf[0].optimize = 2
book_I[0].position = [0.1599999964237213, 1.7799999713897705, 2.0450000762939453]
book_I[0].rotation = [0, 0, 0.01256637125682779]
book_I[0].optimize = 2
dresserbottle[0].position = [3.180000066757202, 0.18000000715255737, 0.9200000166893005]
dresserbottle[0].rotation = [0, 0, 0.01256637125682779]
dresserbottle[0].optimize = 2
bottle_D[0].position = [3.299999952316284, 0.38999998569488525, 0.9099999666213989]
bottle_D[0].rotation = [0, 0, 0.01256637125682779]
bottle_D[0].optimize = 2
mirror_A[0].position = [2.5999999046325684, 0.011368179693818092, 0.800000011920929]
mirror_A[0].rotation = [0, 0, 1.5733372449455554]
mirror_A[0].optimize = 2
vase_F[0].position = [1.399999976158142, 2.609999895095825, 0.7549999952316284]
vase_F[0].rotation = [0, 0, 0.01256637125682779]
vase_F[0].optimize = 2
lamp_B[0].position = [0.21000006794929504, 1.350000023841858, 0.7749999761581421]
lamp_B[0].rotation = [0, 0, 0.005651523938900898]
lamp_B[0].optimize = 2
ottoman[0].position = [0.75, 1.350000023841858, 0.20999999344348907]
ottoman[0].rotation = [0, 0, 0.025964360962751048]
ottoman[0].optimize = 2
vase_B[0].position = [2.0, 0.25999999046325684, 1.0599998235702515]
vase_B[0].rotation = [0, 0, 0.01256637125682779]
vase_B[0].optimize = 2
pillow[0].position = [3.549999952316284, 2.25, 1.4900000095367432]
pillow[0].rotation = [0, 0, -3.115630390932128]
pillow[0].optimize = 2
lamp_C[0].position = [3.680000066757202, 0.699999988079071, 0.8899999856948853]
lamp_C[0].rotation = [0, 0, -3.1290262823329655]
lamp_C[0].optimize = 2
dresserbottles[0].position = [3.059999942779541, 0.18000000715255737, 0.9300000071525574]
dresserbottles[0].rotation = [0, 0, 0.01256637125682779]
dresserbottles[0].optimize = 2
book_K[0].position = [0.1599999964237213, 2.390000104904175, 1.959999918937683]
book_K[0].rotation = [0, 0, 0.0157079639172164]
book_K[0].optimize = 2
nightstand1book[0].position = [3.680000066757202, 0.699999988079071, 0.6399999856948853]
nightstand1book[0].rotation = [0, 0, -3.125884689672577]
nightstand1book[0].optimize = 2
book_D[0].position = [2.380000114440918, 0.25999999046325684, 0.8799999356269836]
book_D[0].rotation = [0, 0, 1.586504290712113]
book_D[0].optimize = 2
book_C[0].position = [0.1899999976158142, 3.2200000286102295, 0.9599997997283936]
book_C[0].rotation = [0, 0, 0.0157079639172164]
book_C[0].optimize = 2
tablebook_A[0].position = [0.1899999976158142, 3.2200000286102295, 0.7999999523162842]
tablebook_A[0].rotation = [0, 0, 0.01884955539881635]
tablebook_A[0].optimize = 2
candle_F[0].position = [0.1599999964237213, 2.390000104904175, 2.069999933242798]
candle_F[0].rotation = [0, 0, 0.01256637125682779]
candle_F[0].optimize = 2
bottle_C[0].position = [3.180000066757202, 0.38999998569488525, 0.9099999666213989]
bottle_C[0].rotation = [0, 0, 0.01256637125682779]
bottle_C[0].optimize = 2
tablecandle[0].position = [0.1899999976158142, 3.4800000190734863, 0.8499999642372131]
tablecandle[0].rotation = [0, 0, 0.01256637125682779]
tablecandle[0].optimize = 2
nightstandbook_B[0].position = [3.680000066757202, 3.7200000286102295, 0.6399999856948853]
nightstandbook_B[0].rotation = [0, 0, -3.125884689672577]
nightstandbook_B[0].optimize = 2
wardrobe[0].position = [2.75, 4.188666820526123, 1.100000023841858]
wardrobe[0].rotation = [0, 0, -1.56825541415488]
wardrobe[0].optimize = 2
chair[0].position = [0.800000011920929, 0.550000011920929, 0.4099999964237213]
chair[0].rotation = [0, 0, 1.5959290669047523]
chair[0].optimize = 2
bottle_A[0].position = [3.299999952316284, 0.18000000715255737, 0.9099999666213989]
bottle_A[0].rotation = [0, 0, 0.01256637125682779]
bottle_A[0].optimize = 2

