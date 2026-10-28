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
    Wall(corner1=[6.00, 0.00, 0.00], corner2=[6.00, 5.00, 0.00]),
    Wall(corner1=[6.00, 5.00, 0.00], corner2=[0.00, 5.00, 0.00]),
    Wall(corner1=[0.00, 5.00, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
book_A = Assets(description="A hardcover book with vintage spines, rectangular solid form, slightly textured cloth cover, muted earth tones and gold lettering", size=[0.05, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
glass_A = Assets(description="A cut‑crystal modern drinking glass, clear faceted surface, slightly tapered cylindrical shape, reflective sparkle", size=[0.09, 0.09, 0.12], placements=[AssetInstance() for _ in range(1)])
shakerbar_A = Assets(description="A brass and wooden cocktail shaker with a polished cylindrical metal body, wooden handle and a rounded lid", size=[0.13, 0.13, 0.28], placements=[AssetInstance() for _ in range(1)])
bottle_A = Assets(description="A vintage glass bottle with metal caps, rounded amber‑tinted glass body and brushed metal cap", size=[0.11, 0.11, 0.28], placements=[AssetInstance() for _ in range(1)])
succulent = Assets(description="A small succulent in a shallow ceramic pot, compact low-slung form, soft green foliage and a smooth textured pot.", size=[0.18, 0.18, 0.16], placements=[AssetInstance() for _ in range(1)])
candle_A = Assets(description="A brass and ceramic candle with a slender cylindrical body, smooth polished brass base and a creamy ceramic holder, warm golden tone with subtle texture", size=[0.08, 0.08, 0.25], placements=[AssetInstance() for _ in range(1)])
glass_B = Assets(description="A cut crystal and modern glass tumbler with a sleek angular silhouette, clear sparkling facets, thin rim and polished chrome accent", size=[0.09, 0.09, 0.12], placements=[AssetInstance() for _ in range(1)])
glass_table_A = Assets(description="A cut‑crystal modern drinking glass, clear faceted surface, slightly tapered cylindrical shape, reflective sparkle", size=[0.09, 0.09, 0.13], placements=[AssetInstance() for _ in range(1)])
artworkwall_A = Assets(description="A single piece of thin and upright abstract mixed‑media artwork, featuring bold geometric shapes, layered textures and a vibrant colour palette on a lightweight canvas", size=[0.04, 0.85, 1.10], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="A vintage glass bottle with a metal cap, slender neck, slightly rounded shoulders, amber‑tinted glass and a brushed metal top", size=[0.09, 0.09, 0.30], placements=[AssetInstance() for _ in range(1)])
candle_table_A = Assets(description="A brass and ceramic decorative candle with a slender cylindrical body, a polished brass base and a matte ceramic holder, warm amber glow", size=[0.08, 0.08, 0.27], placements=[AssetInstance() for _ in range(1)])
glassbar_A = Assets(description="A cut‑crystal modern bar glass, clear faceted shape, slightly flared rim, sleek vertical profile", size=[0.09, 0.09, 0.16], placements=[AssetInstance() for _ in range(1)])
bottle_C = Assets(description="A vintage glass bottle with metal caps, featuring a rounded squat body, amber‑tinted glass, and brushed metal top.", size=[0.12, 0.12, 0.23], placements=[AssetInstance() for _ in range(1)])
chairmetal_A = Assets(description="A metal dining chair with a modern angular frame, sleek cylindrical legs, brushed steel finish, minimalist rectangular seat, eclectic style", size=[0.52, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
glass_C = Assets(description="A cut‑crystal modern glass, cylindrical with a gently faceted surface, clear sparkling finish and a thin polished rim, sleek contemporary look", size=[0.09, 0.09, 0.13], placements=[AssetInstance() for _ in range(1)])
plant_A = Assets(description="A potted fern with lush green fronds, round terracotta pot, compact bushy foliage, natural organic shape", size=[0.55, 0.55, 0.75], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="A pendant lamp with a retro brass shade and a modern geometric metal cage, eclectic style, warm brass color, clear glass interior, elongated hanging form", size=[0.42, 0.42, 2.25], placements=[AssetInstance() for _ in range(1)])
bottle_bar_A = Assets(description="A vintage glass bottle with a dark amber tint, rounded shoulders and a polished metal cap", size=[0.11, 0.11, 0.29], placements=[AssetInstance() for _ in range(1)])
glass_D = Assets(description="A cut crystal and modern glass tumbler with a faceted cylindrical form, clear sparkling surface and a sleek polished edge.", size=[0.09, 0.09, 0.12], placements=[AssetInstance() for _ in range(1)])
bottle_D = Assets(description="A vintage glass bottle with metal caps, featuring a squat cylindrical shape, amber tinted glass and a textured metal top.", size=[0.12, 0.12, 0.22], placements=[AssetInstance() for _ in range(1)])
glass_table_B = Assets(description="A cut crystal and modern eclectic glass with a faceted rectangular shape, clear sparkling facets, sleek chrome rim, and delicate stem.", size=[0.09, 0.09, 0.19], placements=[AssetInstance() for _ in range(1)])
plate_A = Assets(description="A mixed vintage porcelain plate with a slightly curved rim, circular shape, soft ivory color and subtle hand-painted floral accents.", size=[0.27, 0.27, 0.03], placements=[AssetInstance() for _ in range(1)])
bottle_E = Assets(description="A vintage glass bottle with metal caps, featuring a rounded squat body, amber‑tinted glass, and brushed metal top.", size=[0.12, 0.12, 0.23], placements=[AssetInstance() for _ in range(1)])
candle_B = Assets(description="A brass and ceramic candle with a rounded base and a slender tapered body, featuring a warm amber hue and a decorative hammered texture.", size=[0.09, 0.09, 0.28], placements=[AssetInstance() for _ in range(1)])
candle_C = Assets(description="A brass and ceramic candle with a slender cylindrical body, smooth polished brass base and a creamy ceramic holder, warm golden tone with subtle texture", size=[0.08, 0.08, 0.25], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="A hardcover book with vintage spines, rectangular solid form, deep brown leather cover and embossed gold lettering.", size=[0.05, 0.17, 0.24], placements=[AssetInstance() for _ in range(1)])
bottle_bar_B = Assets(description="A vintage glass bottle with a metal cap, squat cylindrical body, muted amber tint and a slightly embossed label", size=[0.12, 0.12, 0.22], placements=[AssetInstance() for _ in range(1)])
glass_E = Assets(description="A cut crystal and modern glass tumbler with a faceted cylindrical form, clear sparkling surface and a sleek polished edge.", size=[0.09, 0.09, 0.12], placements=[AssetInstance() for _ in range(1)])
plant_B = Assets(description="A potted fern with lush green fronds, round terracotta pot, compact bushy foliage, natural organic shape", size=[0.58, 0.58, 0.78], placements=[AssetInstance() for _ in range(1)])
plate_B = Assets(description="A mixed vintage porcelain plate, round with a slightly flared rim, delicate hand‑painted floral pattern, creamy white background and soft pastel accents", size=[0.28, 0.28, 0.03], placements=[AssetInstance() for _ in range(1)])
book_C = Assets(description="A hardcover book with vintage spines, rectangular solid form, slightly textured cloth cover, muted earth tones and gold lettering", size=[0.05, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
plantc = Assets(description="A small succulent in a shallow ceramic pot with a compact rosette of fleshy green leaves, matte terracotta pot", size=[0.17, 0.17, 0.15], placements=[AssetInstance() for _ in range(1)])
plant_C = Assets(description="A large potted plant with mixed foliage, tall cylindrical pot of weathered metal, eclectic style, deep green leaves, textured pot surface, organic organic silhouette", size=[0.75, 0.75, 1.65], placements=[AssetInstance() for _ in range(1)])
artwork_A = Assets(description="A single piece of thin and upright abstract mixed‑media artwork, rectangular panel with layered textures, bold brushstrokes, muted earth tones and splashes of teal", size=[0.04, 0.75, 1.00], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="A wall‑mounted shelf combining a wooden plank with a metal bracket, eclectic style, natural wood grain, matte black steel support, slim rectangular profile", size=[0.30, 1.60, 0.10], placements=[AssetInstance() for _ in range(1)])
glass_F = Assets(description="A cut crystal and modern glass tumbler with a faceted cylindrical form, clear sparkling surface and a sleek polished edge.", size=[0.09, 0.09, 0.12], placements=[AssetInstance() for _ in range(1)])
bottle_F = Assets(description="A vintage glass bottle with metal caps, rounded amber‑tinted glass body and brushed metal cap", size=[0.11, 0.11, 0.28], placements=[AssetInstance() for _ in range(1)])
bottle_G = Assets(description="A vintage glass bottle with a metal cap, squat cylindrical body, amber tinted glass and brushed metal top", size=[0.12, 0.12, 0.22], placements=[AssetInstance() for _ in range(1)])
bottle_H = Assets(description="A vintage glass bottle with a metal cap, slender neck, slightly rounded shoulders, amber‑tinted glass and a brushed metal top", size=[0.09, 0.09, 0.30], placements=[AssetInstance() for _ in range(1)])
glassbar_B = Assets(description="A cut crystal and modern bar glass with a tall slender cylindrical shape, clear facets and a brushed steel base", size=[0.08, 0.08, 0.18], placements=[AssetInstance() for _ in range(1)])
glass_G = Assets(description="A cut‑crystal modern glass with a clear faceted surface, slightly tapered rim and a thin stem, sparkling transparent finish", size=[0.09, 0.09, 0.19], placements=[AssetInstance() for _ in range(1)])
candle_D = Assets(description="A brass and ceramic candle with a slender cylindrical body and a slightly tapered top, polished brass base and matte ceramic finish, warm amber glow", size=[0.08, 0.08, 0.27], placements=[AssetInstance() for _ in range(1)])
chairwood_A = Assets(description="A wooden dining chair with a vintage frame, rectangular backrest, tapered legs, warm honey‑tone finish, subtle carved detailing on the seat edges, eclectic style", size=[0.53, 0.48, 0.86], placements=[AssetInstance() for _ in range(1)])
candle_E = Assets(description="A brass and ceramic decorative candle with a slender cylindrical body, a polished brass base and a matte ceramic holder, warm amber glow", size=[0.08, 0.08, 0.27], placements=[AssetInstance() for _ in range(1)])
chairwood_B = Assets(description="A wooden dining chair with a vintage frame, rectangular backrest, tapered legs, warm honey‑tone finish, subtle carved detailing on the seat edges, eclectic style", size=[0.53, 0.48, 0.86], placements=[AssetInstance() for _ in range(1)])
glasstable_A = Assets(description="A cut‑crystal modern glass tumbler with a sleek cylindrical shape, clear sparkling facets and a thin polished rim", size=[0.09, 0.09, 0.12], placements=[AssetInstance() for _ in range(1)])
bottle_bar_C = Assets(description="A vintage glass bottle with a metal cap, squat cylindrical body, muted amber tint and a slightly embossed label", size=[0.12, 0.12, 0.22], placements=[AssetInstance() for _ in range(1)])
candle_F = Assets(description="A brass and ceramic candle with a slender cylindrical shape, warm amber hue, and a slightly textured ceramic base", size=[0.08, 0.08, 0.24], placements=[AssetInstance() for _ in range(1)])
plant_D = Assets(description="A small succulent in a shallow ceramic pot, compact rosette of fleshy leaves, muted green color, pot with a smooth matte finish", size=[0.18, 0.18, 0.16], placements=[AssetInstance() for _ in range(1)])
candle_G = Assets(description="A brass and ceramic candle with a rounded base and a slender tapered body, featuring a warm amber hue and a decorative hammered texture.", size=[0.09, 0.09, 0.28], placements=[AssetInstance() for _ in range(1)])
candle_H = Assets(description="A brass and ceramic candle with a rounded base and a slender tapered body, featuring a warm amber hue and a decorative hammered texture.", size=[0.09, 0.09, 0.28], placements=[AssetInstance() for _ in range(1)])
book_shelf_A = Assets(description="A vintage hardcover book, rectangular solid with a cloth spine, slightly worn edges, deep mahogany color", size=[0.05, 0.17, 0.24], placements=[AssetInstance() for _ in range(1)])
cart = Assets(description="A mobile serving cart with a vintage wooden frame, industrial steel wheels, eclectic style, dark stained wood, black metal accents, rectangular tiered shelves", size=[0.50, 0.90, 0.90], placements=[AssetInstance() for _ in range(1)])
candle_I = Assets(description="A brass and ceramic candle with a rounded base and a slender tapered body, featuring a warm amber hue and a decorative hammered texture.", size=[0.09, 0.09, 0.28], placements=[AssetInstance() for _ in range(1)])
glass_H = Assets(description="A cut‑crystal modern glass with a clear faceted surface, slightly tapered rim and a thin stem, sparkling transparent finish", size=[0.09, 0.09, 0.19], placements=[AssetInstance() for _ in range(1)])
vasec = Assets(description="A ceramic and metal vase with a tall cylindrical body, glossy white ceramic surface and brushed bronze metal accent band", size=[0.16, 0.16, 0.36], placements=[AssetInstance() for _ in range(1)])
glasstable_B = Assets(description="A cut‑crystal modern glass tumbler with a sleek cylindrical shape, clear sparkling facets and a thin polished rim", size=[0.09, 0.09, 0.12], placements=[AssetInstance() for _ in range(1)])
bottle_bar_D = Assets(description="A vintage glass bottle with a dark amber tint, rounded shoulders and a polished metal cap", size=[0.11, 0.11, 0.29], placements=[AssetInstance() for _ in range(1)])
shaker_A = Assets(description="A brass and wooden cocktail shaker, cylindrical metal body with a polished brass top and a short wooden handle, matte finish", size=[0.13, 0.13, 0.27], placements=[AssetInstance() for _ in range(1)])
artwork_B = Assets(description="A single piece of thin and upright abstract mixed‑media artwork, rectangular panel with layered textures, bold brushstrokes, muted earth tones and splashes of teal", size=[0.04, 0.75, 1.00], placements=[AssetInstance() for _ in range(1)])
booked_A = Assets(description="A vintage hardcover book with a rectangular solid form, textured cloth cover, deep burgundy color and gold embossing", size=[0.05, 0.17, 0.24], placements=[AssetInstance() for _ in range(1)])
artwork_C = Assets(description="A single piece of thin and upright abstract mixed‑media artwork with layered canvas, bold splashes of colour, textured surface", size=[0.04, 0.90, 1.15], placements=[AssetInstance() for _ in range(1)])
candle_J = Assets(description="A brass and ceramic candle with a slender cylindrical body, polished brass base and matte ceramic holder, warm golden hue", size=[0.08, 0.08, 0.25], placements=[AssetInstance() for _ in range(1)])
artworkwall_B = Assets(description="A single piece of thin and upright abstract mixed‑media artwork, featuring bold geometric shapes, layered textures and a vibrant colour palette on a lightweight canvas", size=[0.04, 0.85, 1.10], placements=[AssetInstance() for _ in range(1)])
bottle_I = Assets(description="A vintage glass bottle with metal caps, featuring a squat cylindrical shape, amber tinted glass and a textured metal top.", size=[0.12, 0.12, 0.22], placements=[AssetInstance() for _ in range(1)])
book_D = Assets(description="A hardcover book with vintage spines, rectangular solid form, deep brown leather cover and embossed gold lettering.", size=[0.05, 0.17, 0.24], placements=[AssetInstance() for _ in range(1)])
glass_I = Assets(description="A cut‑crystal modern glass with a clear faceted surface, slightly tapered rim and a thin stem, sparkling transparent finish", size=[0.09, 0.09, 0.19], placements=[AssetInstance() for _ in range(1)])
artwork_wall_A = Assets(description="A single piece of thin and upright abstract mixed‑media artwork with bold geometric shapes, layered canvas texture and a muted pastel palette", size=[0.04, 0.80, 1.05], placements=[AssetInstance() for _ in range(1)])
chairmetal_B = Assets(description="A metal dining chair with a modern angular frame, sleek cylindrical legs, brushed steel finish, minimalist rectangular seat, eclectic style", size=[0.52, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
bottle_J = Assets(description="A vintage glass bottle with a metal cap, slender neck, slightly rounded shoulders, amber‑tinted glass and a brushed metal top", size=[0.09, 0.09, 0.30], placements=[AssetInstance() for _ in range(1)])
artworkwall_C = Assets(description="A single piece of thin and upright abstract mixed‑media artwork, featuring bold geometric shapes, layered textures and a vibrant colour palette on a lightweight canvas", size=[0.04, 0.85, 1.10], placements=[AssetInstance() for _ in range(1)])
artwork_wall_B = Assets(description="A single piece of thin and upright abstract mixed‑media artwork with bold geometric shapes, layered canvas texture and a muted pastel palette", size=[0.04, 0.80, 1.05], placements=[AssetInstance() for _ in range(1)])
book_E = Assets(description="A vintage hardcover book with a rectangular solid shape, textured cloth cover in deep navy, silver embossing, slightly aged corners", size=[0.05, 0.17, 0.24], placements=[AssetInstance() for _ in range(1)])
candle_K = Assets(description="A brass and ceramic candle with a slender cylindrical shape, warm amber hue, and a slightly textured ceramic base", size=[0.08, 0.08, 0.24], placements=[AssetInstance() for _ in range(1)])
shakerbar_B = Assets(description="A brass and wooden cocktail shaker with a polished cylindrical metal body, wooden handle and a rounded lid", size=[0.13, 0.13, 0.28], placements=[AssetInstance() for _ in range(1)])
book_F = Assets(description="A hardcover book with vintage spines, rectangular solid form, slightly textured cloth cover, muted earth tones and gold lettering", size=[0.05, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
glass_J = Assets(description="A cut‑crystal modern glass, cylindrical with a gently faceted surface, clear sparkling finish and a thin polished rim, sleek contemporary look", size=[0.09, 0.09, 0.13], placements=[AssetInstance() for _ in range(1)])
artwork_D = Assets(description="A single piece of thin and upright abstract mixed‑media artwork with layered canvas, bold splashes of colour, textured surface", size=[0.04, 0.90, 1.15], placements=[AssetInstance() for _ in range(1)])
glassbar_C = Assets(description="A cut crystal and modern bar glass with a tall slender cylindrical shape, clear facets and a brushed steel base", size=[0.08, 0.08, 0.18], placements=[AssetInstance() for _ in range(1)])
glassbar_D = Assets(description="A cut‑crystal modern glass with a sleek rectangular bowl and a thin, polished stem, clear sparkling finish", size=[0.09, 0.09, 0.20], placements=[AssetInstance() for _ in range(1)])
glass_table_C = Assets(description="A cut crystal and modern eclectic glass with a faceted rectangular shape, clear sparkling facets, sleek chrome rim, and delicate stem.", size=[0.09, 0.09, 0.19], placements=[AssetInstance() for _ in range(1)])
artwork_E = Assets(description="A single piece of thin and upright abstract mixed-media artwork, rectangular flat panel with layered textures, vibrant colors and a subtle metallic sheen.", size=[0.04, 0.80, 1.05], placements=[AssetInstance() for _ in range(1)])
shaker_bar = Assets(description="A brass and wooden cocktail shaker with a polished cylindrical body, brushed metal top and a smooth wooden handle", size=[0.13, 0.13, 0.28], placements=[AssetInstance() for _ in range(1)])
artwork_F = Assets(description="A single piece of thin and upright abstract mixed‑media artwork with bold geometric shapes, vibrant colors and a matte canvas finish", size=[0.04, 0.85, 1.10], placements=[AssetInstance() for _ in range(1)])
plant_E = Assets(description="A large potted plant with mixed foliage, tall cylindrical pot of weathered metal, eclectic style, deep green leaves, textured pot surface, organic organic silhouette", size=[0.75, 0.75, 1.65], placements=[AssetInstance() for _ in range(1)])
artwork_G = Assets(description="A single piece of thin and upright abstract mixed‑media artwork with layered canvas, bold splashes of colour, textured surface", size=[0.04, 0.90, 1.15], placements=[AssetInstance() for _ in range(1)])
artwork_H = Assets(description="A single piece of thin and upright abstract mixed‑media artwork with bold geometric shapes, vibrant colors and a matte canvas finish", size=[0.04, 0.85, 1.10], placements=[AssetInstance() for _ in range(1)])
table_A = Assets(description="A rectangular dining table combining a light‑stained vintage wood top with thin modern metal legs, eclectic style, smooth wood finish, matte black steel, compact rectangular shape", size=[0.85, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
table_B = Assets(description="A rectangular dining table mixing vintage reclaimed wood top with sleek modern metal legs, eclectic style, warm brown wood surface, brushed steel frame, subtle brass edge inlay, sturdy and low‑profile", size=[0.90, 1.80, 0.75], placements=[AssetInstance() for _ in range(1)])
sideboard = Assets(description="A low sideboard cabinet with antique wood panels, modern brushed‑nickel handles, eclectic style, rich walnut finish, rectangular low‑profile form, subtle carved motif on doors", size=[0.48, 1.60, 0.82], placements=[AssetInstance() for _ in range(1)])
shaker_B = Assets(description="A brass and wooden cocktail shaker with a rounded cylindrical body, polished brass top and dark walnut wooden handle", size=[0.13, 0.13, 0.27], placements=[AssetInstance() for _ in range(1)])
glassbar_E = Assets(description="A cut‑crystal modern glass, rectangular with a thin beveled edge, clear sparkling finish, low‑profile silhouette", size=[0.08, 0.10, 0.10], placements=[AssetInstance() for _ in range(1)])
glass_K = Assets(description="A cut‑crystal modern glass, cylindrical with a gently faceted surface, clear sparkling finish and a thin polished rim, sleek contemporary look", size=[0.09, 0.09, 0.13], placements=[AssetInstance() for _ in range(1)])
plate_C = Assets(description="A mixed vintage porcelain plate with a slightly raised rim, subtle hand‑painted floral motif, creamy white background and a thin, delicate edge", size=[0.27, 0.27, 0.03], placements=[AssetInstance() for _ in range(1)])
chairwood_C = Assets(description="A wooden dining chair with a vintage frame, rectangular backrest, tapered legs, warm honey‑tone finish, subtle carved detailing on the seat edges, eclectic style", size=[0.53, 0.48, 0.86], placements=[AssetInstance() for _ in range(1)])
plate_D = Assets(description="A mixed vintage porcelain plate, round with a slightly flared rim, delicate hand‑painted floral pattern, creamy white background and soft pastel accents", size=[0.28, 0.28, 0.03], placements=[AssetInstance() for _ in range(1)])
book_shelf_B = Assets(description="A vintage hardcover book, rectangular solid with a cloth spine, slightly worn edges, deep mahogany color", size=[0.05, 0.17, 0.24], placements=[AssetInstance() for _ in range(1)])
glass_L = Assets(description="A cut‑crystal modern glass with a clear faceted surface, elegant tapered silhouette and a thin rim", size=[0.09, 0.09, 0.15], placements=[AssetInstance() for _ in range(1)])
artwork_I = Assets(description="A single piece of thin and upright abstract mixed‑media artwork, rectangular canvas with bold geometric splashes of colour and a subtle textured surface", size=[0.04, 0.80, 1.05], placements=[AssetInstance() for _ in range(1)])
candle_L = Assets(description="A brass and ceramic candle with a slender cylindrical body and a slightly tapered top, polished brass base and matte ceramic finish, warm amber glow", size=[0.08, 0.08, 0.27], placements=[AssetInstance() for _ in range(1)])
plant_F = Assets(description="A potted fern with lush green fronds, round terracotta pot, compact bushy foliage, natural organic shape", size=[0.55, 0.55, 0.75], placements=[AssetInstance() for _ in range(1)])
chairmetal_C = Assets(description="A metal dining chair with a modern angular frame, sleek cylindrical legs, brushed steel finish, minimalist rectangular seat, eclectic style", size=[0.52, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
candle_M = Assets(description="A brass and ceramic decorative candle with a slender cylindrical body, a polished brass base and a matte ceramic holder, warm amber glow", size=[0.08, 0.08, 0.27], placements=[AssetInstance() for _ in range(1)])
book_G = Assets(description="A hardcover book with vintage spines, rectangular solid form, slightly textured cloth cover, muted earth tones and gold lettering", size=[0.05, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
book_H = Assets(description="A vintage hardcover book with a textured cloth cover, rectangular shape, slightly worn edges, embossed title, thick pages", size=[0.05, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
glassbar_F = Assets(description="A cut‑crystal modern glass with a sleek rectangular bowl and a thin, polished stem, clear sparkling finish", size=[0.09, 0.09, 0.20], placements=[AssetInstance() for _ in range(1)])
glass_M = Assets(description="A cut‑crystal modern glass with a clear faceted surface, slightly tapered rim and a thin stem, sparkling transparent finish", size=[0.09, 0.09, 0.19], placements=[AssetInstance() for _ in range(1)])
bar = Assets(description="A low service bar with rustic reclaimed wood top, metal pipe fixtures, eclectic style, distressed brown wood, matte black metal brackets, rectangular slab shape", size=[0.70, 2.40, 1.05], placements=[AssetInstance() for _ in range(1)])
glass_N = Assets(description="A cut crystal and modern glass tumbler with a sleek angular silhouette, clear sparkling facets, thin rim and polished chrome accent", size=[0.09, 0.09, 0.12], placements=[AssetInstance() for _ in range(1)])
plate_E = Assets(description="A mixed vintage porcelain plate, round with a slightly flared rim, delicate hand‑painted floral pattern, creamy white background and soft pastel accents", size=[0.28, 0.28, 0.03], placements=[AssetInstance() for _ in range(1)])
planted = Assets(description="A small succulent in a shallow ceramic pot with a compact rosette of fleshy green leaves, matte terracotta pot", size=[0.17, 0.17, 0.15], placements=[AssetInstance() for _ in range(1)])
glassbar_G = Assets(description="A cut crystal and modern glass highball glass with a slender rectangular silhouette, clear facets and a smooth rim.", size=[0.08, 0.08, 0.17], placements=[AssetInstance() for _ in range(1)])
artwork_wall_C = Assets(description="A single piece of thin and upright abstract mixed‑media artwork with bold geometric shapes, layered canvas texture and a muted pastel palette", size=[0.04, 0.80, 1.05], placements=[AssetInstance() for _ in range(1)])
glass_O = Assets(description="A cut‑crystal modern glass with a clear faceted surface, slightly tapered rim and a thin stem, sparkling transparent finish", size=[0.09, 0.09, 0.19], placements=[AssetInstance() for _ in range(1)])
glassbar_H = Assets(description="A cut‑crystal modern bar glass, clear faceted shape, slightly flared rim, sleek vertical profile", size=[0.09, 0.09, 0.16], placements=[AssetInstance() for _ in range(1)])
artwork_wall_D = Assets(description="A single piece of thin and upright abstract mixed‑media artwork with bold geometric shapes, layered canvas texture and a muted pastel palette", size=[0.04, 0.80, 1.05], placements=[AssetInstance() for _ in range(1)])
bottlebar_A = Assets(description="A vintage glass bottle with a dark amber tint, metal caps, rounded shoulders and a short neck, giving a classic apothecary look", size=[0.12, 0.12, 0.25], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="A vintage storage cabinet with metal accents, rectangular boxy shape, distressed wood finish and brass handle hardware.", size=[0.48, 1.10, 1.35], placements=[AssetInstance() for _ in range(1)])
book_shelf_C = Assets(description="A vintage hardcover book, rectangular solid with a cloth spine, slightly worn edges, deep mahogany color", size=[0.05, 0.17, 0.24], placements=[AssetInstance() for _ in range(1)])
glass_table_D = Assets(description="A cut‑crystal modern drinking glass, clear faceted surface, slightly tapered cylindrical shape, reflective sparkle", size=[0.09, 0.09, 0.13], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="A pendant lamp with a retro brass shade and a modern geometric metal cage, eclectic style, warm brass color, clear glass interior, elongated hanging form", size=[0.42, 0.42, 2.25], placements=[AssetInstance() for _ in range(1)])
booked_B = Assets(description="A vintage hardcover book with a rectangular solid form, textured cloth cover, deep burgundy color and gold embossing", size=[0.05, 0.17, 0.24], placements=[AssetInstance() for _ in range(1)])
glass_P = Assets(description="A cut‑crystal modern glass with a clear faceted surface, slightly tapered rim and a thin stem, sparkling transparent finish", size=[0.09, 0.09, 0.19], placements=[AssetInstance() for _ in range(1)])
candle_N = Assets(description="A brass and ceramic candle with a slender cylindrical body, polished brass base and matte ceramic holder, warm golden hue", size=[0.08, 0.08, 0.25], placements=[AssetInstance() for _ in range(1)])
menustand = Assets(description="A vintage metal frame menu stand with a narrow rectangular base, slender upright supports, brushed metal finish and a small shelf for menus", size=[0.40, 0.55, 1.25], placements=[AssetInstance() for _ in range(1)])
glassbar_I = Assets(description="A cut crystal and modern glass highball glass with a slender rectangular silhouette, clear facets and a smooth rim.", size=[0.08, 0.08, 0.17], placements=[AssetInstance() for _ in range(1)])
glassbar_J = Assets(description="A cut‑crystal modern glass tumbler with a sleek, slightly tapered silhouette and a clear sparkling surface", size=[0.09, 0.09, 0.14], placements=[AssetInstance() for _ in range(1)])
bookc = Assets(description="A vintage hardcover book with a rectangular solid form, textured cloth cover, deep burgundy color and gold embossing", size=[0.05, 0.17, 0.24], placements=[AssetInstance() for _ in range(1)])
book_I = Assets(description="A vintage hardcover book with a rectangular solid shape, textured cloth cover in deep navy, silver embossing, slightly aged corners", size=[0.05, 0.17, 0.24], placements=[AssetInstance() for _ in range(1)])
book_J = Assets(description="A hardcover book with vintage spines, rectangular solid form, deep brown leather cover and embossed gold lettering.", size=[0.05, 0.17, 0.24], placements=[AssetInstance() for _ in range(1)])
candle_table_B = Assets(description="A brass and ceramic eclectic candle with a slender cylindrical body, warm golden metal base, and smooth ceramic top, featuring a subtle patina finish.", size=[0.08, 0.08, 0.26], placements=[AssetInstance() for _ in range(1)])
glass_Q = Assets(description="A cut crystal and modern glass tumbler with a faceted cylindrical form, clear sparkling surface and a sleek polished edge.", size=[0.09, 0.09, 0.12], placements=[AssetInstance() for _ in range(1)])
vase_shelf_ed = Assets(description="A ceramic and metal vase with a tall cylindrical body, matte white glaze and a brushed copper neck", size=[0.16, 0.16, 0.36], placements=[AssetInstance() for _ in range(1)])
bottlebar_B = Assets(description="A vintage glass bottle with a dark amber tint, metal caps, rounded shoulders and a short neck, giving a classic apothecary look", size=[0.12, 0.12, 0.25], placements=[AssetInstance() for _ in range(1)])
glassbar_K = Assets(description="A cut‑crystal modern glass tumbler with a sleek, slightly tapered silhouette and a clear sparkling surface", size=[0.09, 0.09, 0.14], placements=[AssetInstance() for _ in range(1)])
chairwood_D = Assets(description="A wooden dining chair with a vintage frame, rectangular backrest, tapered legs, warm honey‑tone finish, subtle carved detailing on the seat edges, eclectic style", size=[0.53, 0.48, 0.86], placements=[AssetInstance() for _ in range(1)])
shaker_C = Assets(description="A brass and wooden cocktail shaker, cylindrical body with a polished brass top and a dark walnut wooden handle, smooth rounded edges", size=[0.13, 0.13, 0.27], placements=[AssetInstance() for _ in range(1)])
glass_R = Assets(description="A cut‑crystal modern drinking glass, clear faceted surface, slightly tapered cylindrical shape, reflective sparkle", size=[0.09, 0.09, 0.13], placements=[AssetInstance() for _ in range(1)])
bottle_K = Assets(description="A vintage glass bottle with metal caps, featuring a rounded squat body, amber‑tinted glass, and brushed metal top.", size=[0.12, 0.12, 0.23], placements=[AssetInstance() for _ in range(1)])
shaker_D = Assets(description="A brass and wooden cocktail shaker with a cylindrical body, brushed brass exterior, wooden handle and a polished lid", size=[0.13, 0.13, 0.28], placements=[AssetInstance() for _ in range(1)])
book_K = Assets(description="A hardcover book with vintage spines, rectangular solid form, slightly textured cloth cover, muted earth tones and gold lettering", size=[0.05, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
glasstable_C = Assets(description="A cut‑crystal modern glass tumbler with a sleek cylindrical shape, clear sparkling facets and a thin polished rim", size=[0.09, 0.09, 0.12], placements=[AssetInstance() for _ in range(1)])
bottle_L = Assets(description="A vintage glass bottle with metal caps, featuring a squat cylindrical shape, amber tinted glass and a textured metal top.", size=[0.12, 0.12, 0.22], placements=[AssetInstance() for _ in range(1)])
plate_F = Assets(description="A mixed vintage porcelain plate with a slightly curved rim, circular shape, soft ivory color and subtle hand-painted floral accents.", size=[0.27, 0.27, 0.03], placements=[AssetInstance() for _ in range(1)])
plate_G = Assets(description="A mixed vintage porcelain plate with a slightly raised rim, subtle hand‑painted floral motif, creamy white background and a thin, delicate edge", size=[0.27, 0.27, 0.03], placements=[AssetInstance() for _ in range(1)])
chairmetal_D = Assets(description="A metal dining chair with a modern angular frame, sleek cylindrical legs, brushed steel finish, minimalist rectangular seat, eclectic style", size=[0.52, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
artwork_J = Assets(description="A single piece of thin and upright abstract mixed-media artwork, rectangular flat panel with layered textures, vibrant colors and a subtle metallic sheen.", size=[0.04, 0.80, 1.05], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="A wall‑mounted shelf combining a wooden plank with a metal bracket, eclectic style, natural wood grain, matte black steel support, slim rectangular profile", size=[0.30, 1.60, 0.10], placements=[AssetInstance() for _ in range(1)])
bottlebar_C = Assets(description="A vintage glass bottle with a metal cap, rounded body, slightly embossed label area and a glossy amber glass finish", size=[0.12, 0.12, 0.26], placements=[AssetInstance() for _ in range(1)])
book_L = Assets(description="A hardcover book with vintage spines, rectangular solid form, deep brown leather cover and embossed gold lettering.", size=[0.05, 0.17, 0.24], placements=[AssetInstance() for _ in range(1)])
artworkwall_D = Assets(description="A single piece of thin and upright abstract mixed‑media artwork, featuring bold geometric shapes, layered textures and a vibrant colour palette on a lightweight canvas", size=[0.04, 0.85, 1.10], placements=[AssetInstance() for _ in range(1)])
shaker_E = Assets(description="A brass and wooden cocktail shaker with a rounded cylindrical body, polished brass accents and a wooden handle.", size=[0.13, 0.13, 0.27], placements=[AssetInstance() for _ in range(1)])
artwork_K = Assets(description="A single piece of thin and upright abstract mixed‑media artwork with layered canvas, bold splashes of colour, textured surface", size=[0.04, 0.90, 1.15], placements=[AssetInstance() for _ in range(1)])
plant_G = Assets(description="A small succulent in a shallow ceramic pot, compact rosette of fleshy leaves, muted green color, pot with a smooth matte finish", size=[0.18, 0.18, 0.16], placements=[AssetInstance() for _ in range(1)])
bottle_bar_E = Assets(description="A vintage glass bottle with a metal cap, squat cylindrical body, muted amber tint and a slightly embossed label", size=[0.12, 0.12, 0.22], placements=[AssetInstance() for _ in range(1)])
fern = Assets(description="A potted fern with lush frond foliage, a rounded pot, sturdy cylindrical base and a rich earthy green color.", size=[0.58, 0.58, 0.78], placements=[AssetInstance() for _ in range(1)])

book_A[0].instance_id = 'book_A_0'
glass_A[0].instance_id = 'glass_A_0'
shakerbar_A[0].instance_id = 'shakerbar_A_0'
bottle_A[0].instance_id = 'bottle_A_0'
succulent[0].instance_id = 'succulent_0'
candle_A[0].instance_id = 'candle_A_0'
glass_B[0].instance_id = 'glass_B_0'
glass_table_A[0].instance_id = 'glass_table_A_0'
artworkwall_A[0].instance_id = 'artworkwall_A_0'
bottle_B[0].instance_id = 'bottle_B_0'
candle_table_A[0].instance_id = 'candle_table_A_0'
glassbar_A[0].instance_id = 'glassbar_A_0'
bottle_C[0].instance_id = 'bottle_C_0'
chairmetal_A[0].instance_id = 'chairmetal_A_0'
glass_C[0].instance_id = 'glass_C_0'
plant_A[0].instance_id = 'plant_A_0'
lamp_A[0].instance_id = 'lamp_A_0'
bottle_bar_A[0].instance_id = 'bottle_bar_A_0'
glass_D[0].instance_id = 'glass_D_0'
bottle_D[0].instance_id = 'bottle_D_0'
glass_table_B[0].instance_id = 'glass_table_B_0'
plate_A[0].instance_id = 'plate_A_0'
bottle_E[0].instance_id = 'bottle_E_0'
candle_B[0].instance_id = 'candle_B_0'
candle_C[0].instance_id = 'candle_C_0'
book_B[0].instance_id = 'book_B_0'
bottle_bar_B[0].instance_id = 'bottle_bar_B_0'
glass_E[0].instance_id = 'glass_E_0'
plant_B[0].instance_id = 'plant_B_0'
plate_B[0].instance_id = 'plate_B_0'
book_C[0].instance_id = 'book_C_0'
plantc[0].instance_id = 'plantc_0'
plant_C[0].instance_id = 'plant_C_0'
artwork_A[0].instance_id = 'artwork_A_0'
shelf_A[0].instance_id = 'shelf_A_0'
glass_F[0].instance_id = 'glass_F_0'
bottle_F[0].instance_id = 'bottle_F_0'
bottle_G[0].instance_id = 'bottle_G_0'
bottle_H[0].instance_id = 'bottle_H_0'
glassbar_B[0].instance_id = 'glassbar_B_0'
glass_G[0].instance_id = 'glass_G_0'
candle_D[0].instance_id = 'candle_D_0'
chairwood_A[0].instance_id = 'chairwood_A_0'
candle_E[0].instance_id = 'candle_E_0'
chairwood_B[0].instance_id = 'chairwood_B_0'
glasstable_A[0].instance_id = 'glasstable_A_0'
bottle_bar_C[0].instance_id = 'bottle_bar_C_0'
candle_F[0].instance_id = 'candle_F_0'
plant_D[0].instance_id = 'plant_D_0'
candle_G[0].instance_id = 'candle_G_0'
candle_H[0].instance_id = 'candle_H_0'
book_shelf_A[0].instance_id = 'book_shelf_A_0'
cart[0].instance_id = 'cart_0'
candle_I[0].instance_id = 'candle_I_0'
glass_H[0].instance_id = 'glass_H_0'
vasec[0].instance_id = 'vasec_0'
glasstable_B[0].instance_id = 'glasstable_B_0'
bottle_bar_D[0].instance_id = 'bottle_bar_D_0'
shaker_A[0].instance_id = 'shaker_A_0'
artwork_B[0].instance_id = 'artwork_B_0'
booked_A[0].instance_id = 'booked_A_0'
artwork_C[0].instance_id = 'artwork_C_0'
candle_J[0].instance_id = 'candle_J_0'
artworkwall_B[0].instance_id = 'artworkwall_B_0'
bottle_I[0].instance_id = 'bottle_I_0'
book_D[0].instance_id = 'book_D_0'
glass_I[0].instance_id = 'glass_I_0'
artwork_wall_A[0].instance_id = 'artwork_wall_A_0'
chairmetal_B[0].instance_id = 'chairmetal_B_0'
bottle_J[0].instance_id = 'bottle_J_0'
artworkwall_C[0].instance_id = 'artworkwall_C_0'
artwork_wall_B[0].instance_id = 'artwork_wall_B_0'
book_E[0].instance_id = 'book_E_0'
candle_K[0].instance_id = 'candle_K_0'
shakerbar_B[0].instance_id = 'shakerbar_B_0'
book_F[0].instance_id = 'book_F_0'
glass_J[0].instance_id = 'glass_J_0'
artwork_D[0].instance_id = 'artwork_D_0'
glassbar_C[0].instance_id = 'glassbar_C_0'
glassbar_D[0].instance_id = 'glassbar_D_0'
glass_table_C[0].instance_id = 'glass_table_C_0'
artwork_E[0].instance_id = 'artwork_E_0'
shaker_bar[0].instance_id = 'shaker_bar_0'
artwork_F[0].instance_id = 'artwork_F_0'
plant_E[0].instance_id = 'plant_E_0'
artwork_G[0].instance_id = 'artwork_G_0'
artwork_H[0].instance_id = 'artwork_H_0'
table_A[0].instance_id = 'table_A_0'
table_B[0].instance_id = 'table_B_0'
sideboard[0].instance_id = 'sideboard_0'
shaker_B[0].instance_id = 'shaker_B_0'
glassbar_E[0].instance_id = 'glassbar_E_0'
glass_K[0].instance_id = 'glass_K_0'
plate_C[0].instance_id = 'plate_C_0'
chairwood_C[0].instance_id = 'chairwood_C_0'
plate_D[0].instance_id = 'plate_D_0'
book_shelf_B[0].instance_id = 'book_shelf_B_0'
glass_L[0].instance_id = 'glass_L_0'
artwork_I[0].instance_id = 'artwork_I_0'
candle_L[0].instance_id = 'candle_L_0'
plant_F[0].instance_id = 'plant_F_0'
chairmetal_C[0].instance_id = 'chairmetal_C_0'
candle_M[0].instance_id = 'candle_M_0'
book_G[0].instance_id = 'book_G_0'
book_H[0].instance_id = 'book_H_0'
glassbar_F[0].instance_id = 'glassbar_F_0'
glass_M[0].instance_id = 'glass_M_0'
bar[0].instance_id = 'bar_0'
glass_N[0].instance_id = 'glass_N_0'
plate_E[0].instance_id = 'plate_E_0'
planted[0].instance_id = 'planted_0'
glassbar_G[0].instance_id = 'glassbar_G_0'
artwork_wall_C[0].instance_id = 'artwork_wall_C_0'
glass_O[0].instance_id = 'glass_O_0'
glassbar_H[0].instance_id = 'glassbar_H_0'
artwork_wall_D[0].instance_id = 'artwork_wall_D_0'
bottlebar_A[0].instance_id = 'bottlebar_A_0'
cabinet[0].instance_id = 'cabinet_0'
book_shelf_C[0].instance_id = 'book_shelf_C_0'
glass_table_D[0].instance_id = 'glass_table_D_0'
lamp_B[0].instance_id = 'lamp_B_0'
booked_B[0].instance_id = 'booked_B_0'
glass_P[0].instance_id = 'glass_P_0'
candle_N[0].instance_id = 'candle_N_0'
menustand[0].instance_id = 'menustand_0'
glassbar_I[0].instance_id = 'glassbar_I_0'
glassbar_J[0].instance_id = 'glassbar_J_0'
bookc[0].instance_id = 'bookc_0'
book_I[0].instance_id = 'book_I_0'
book_J[0].instance_id = 'book_J_0'
candle_table_B[0].instance_id = 'candle_table_B_0'
glass_Q[0].instance_id = 'glass_Q_0'
vase_shelf_ed[0].instance_id = 'vase_shelf_ed_0'
bottlebar_B[0].instance_id = 'bottlebar_B_0'
glassbar_K[0].instance_id = 'glassbar_K_0'
chairwood_D[0].instance_id = 'chairwood_D_0'
shaker_C[0].instance_id = 'shaker_C_0'
glass_R[0].instance_id = 'glass_R_0'
bottle_K[0].instance_id = 'bottle_K_0'
shaker_D[0].instance_id = 'shaker_D_0'
book_K[0].instance_id = 'book_K_0'
glasstable_C[0].instance_id = 'glasstable_C_0'
bottle_L[0].instance_id = 'bottle_L_0'
plate_F[0].instance_id = 'plate_F_0'
plate_G[0].instance_id = 'plate_G_0'
chairmetal_D[0].instance_id = 'chairmetal_D_0'
artwork_J[0].instance_id = 'artwork_J_0'
shelf_B[0].instance_id = 'shelf_B_0'
bottlebar_C[0].instance_id = 'bottlebar_C_0'
book_L[0].instance_id = 'book_L_0'
artworkwall_D[0].instance_id = 'artworkwall_D_0'
shaker_E[0].instance_id = 'shaker_E_0'
artwork_K[0].instance_id = 'artwork_K_0'
plant_G[0].instance_id = 'plant_G_0'
bottle_bar_E[0].instance_id = 'bottle_bar_E_0'
fern[0].instance_id = 'fern_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

book_A[0].position = [5.574540512032615, 1.6062285530045766, 0.125]
book_A[0].rotation = [0, 0, 0]
glass_A[0].position = [3.033837339685889, 2.59359487865665, 0.06]
glass_A[0].rotation = [0, 0, 0]
shakerbar_A[0].position = [4.715531691534672, 0.018705055370359935, 0.14]
shakerbar_A[0].rotation = [0, 0, 0]
bottle_A[0].position = [2.8463661948532044, 2.417560465212109, 0.14]
bottle_A[0].rotation = [0, 0, 0]
succulent[0].position = [2.1356415437326812, 2.1083294478852106, 0.08]
succulent[0].rotation = [0, 0, 0]
candle_A[0].position = [0.19305257733919112, 2.364711907191015, 0.125]
candle_A[0].rotation = [0, 0, 0]
glass_B[0].position = [0.11039463379702186, 2.632718248489132, 0.06]
glass_B[0].rotation = [0, 0, 0]
glass_table_A[0].position = [5.95520789805671, 0.5562836074025362, 0.065]
glass_table_A[0].rotation = [0, 0, 0]
artworkwall_A[0].position = [4.635121271855126, 4.06113475196108, 0.55]
artworkwall_A[0].rotation = [0, 0, 0]
bottle_B[0].position = [1.2862524044654426, 0.7691340206721897, 0.15]
bottle_B[0].rotation = [0, 0, 0]
candle_table_A[0].position = [5.547232076824802, 3.817490426147896, 0.135]
candle_table_A[0].rotation = [0, 0, 0]
glassbar_A[0].position = [0.48231415240631303, 3.8049495554024477, 0.08]
glassbar_A[0].rotation = [0, 0, 0]
bottle_C[0].position = [5.181280166579551, 1.4938333274576687, 0.115]
bottle_C[0].rotation = [0, 0, 0]
chairmetal_A[0].position = [4.698340797374582, 3.606073622487169, 0.41]
chairmetal_A[0].rotation = [0, 0, 0]
glass_C[0].position = [0.6675246496052527, 0.5569234954421992, 0.065]
glass_C[0].rotation = [0, 0, 0]
plant_A[0].position = [2.5881457692384706, 4.485243816675635, 0.375]
plant_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [0.2322973293243138, 0.9078322772821734, 1.125]
lamp_A[0].rotation = [0, 0, 0]
bottle_bar_A[0].position = [0.47082681094649637, 0.51859133329901, 0.145]
bottle_bar_A[0].rotation = [0, 0, 0]
glass_D[0].position = [2.2838203690888426, 0.4482255779208444, 0.06]
glass_D[0].rotation = [0, 0, 0]
bottle_D[0].position = [4.249553514365811, 1.9762056133596335, 0.11]
bottle_D[0].rotation = [0, 0, 0]
glass_table_B[0].position = [0.6368540639718985, 3.3180785095818894, 0.095]
glass_table_B[0].rotation = [0, 0, 0]
plate_A[0].position = [5.122092265096544, 1.1064176747125631, 0.015]
plate_A[0].rotation = [0, 0, 0]
bottle_E[0].position = [3.606813631660442, 3.8578974092711116, 0.115]
bottle_E[0].rotation = [0, 0, 0]
candle_B[0].position = [4.697657033921686, 1.7733070104188493, 0.14]
candle_B[0].rotation = [0, 0, 0]
candle_C[0].position = [4.193088006110883, 2.8023161736638134, 0.125]
candle_C[0].rotation = [0, 0, 0]
book_B[0].position = [4.03266417663401, 0.17854624824992948, 0.12]
book_B[0].rotation = [0, 0, 0]
bottle_bar_B[0].position = [4.18607962438029, 4.221898969906156, 0.11]
bottle_bar_B[0].rotation = [0, 0, 0]
glass_E[0].position = [4.6006836691135184, 4.645479857962125, 0.06]
glass_E[0].rotation = [0, 0, 0]
plant_B[0].position = [5.5786691731162765, 0.48349323222342255, 0.39]
plant_B[0].rotation = [0, 0, 0]
plate_B[0].position = [4.614989479116393, 1.1172865062377064, 0.015]
plate_B[0].rotation = [0, 0, 0]
book_C[0].position = [3.309559954288307, 3.367456839117601, 0.125]
book_C[0].rotation = [0, 0, 0]
plantc[0].position = [5.441629367091493, 4.901527186222645, 0.075]
plantc[0].rotation = [0, 0, 0]
plant_C[0].position = [0.2030231241964673, 2.1474369632384076, 0.825]
plant_C[0].rotation = [0, 0, 0]
artwork_A[0].position = [1.8743556669570627, 2.1378194971307702, 0.5]
artwork_A[0].rotation = [0, 0, 0]
shelf_A[0].position = [3.612057758533364, 3.3310485974476967, 0.05]
shelf_A[0].rotation = [0, 0, 0]
glass_F[0].position = [2.8383500530184023, 4.059312296758514, 0.06]
glass_F[0].rotation = [0, 0, 0]
bottle_F[0].position = [3.069845821933235, 3.472445497147234, 0.14]
bottle_F[0].rotation = [0, 0, 0]
bottle_G[0].position = [1.816973728148596, 4.793390470421601, 0.11]
bottle_G[0].rotation = [0, 0, 0]
bottle_H[0].position = [0.7668771524965983, 0.19122451091807435, 0.15]
bottle_H[0].rotation = [0, 0, 0]
glassbar_B[0].position = [0.045880469412693525, 1.530532882870403, 0.09]
glassbar_B[0].rotation = [0, 0, 0]
glass_G[0].position = [1.584208025545297, 1.4615190794563726, 0.095]
glass_G[0].rotation = [0, 0, 0]
candle_D[0].position = [4.82850595152556, 4.494286301426272, 0.135]
candle_D[0].rotation = [0, 0, 0]
chairwood_A[0].position = [5.095395991633826, 2.6431508258192116, 0.43]
chairwood_A[0].rotation = [0, 0, 0]
candle_E[0].position = [0.05338182355649579, 3.5376471289860447, 0.135]
candle_E[0].rotation = [0, 0, 0]
chairwood_B[0].position = [1.6964733174185693, 2.023806551768899, 0.43]
chairwood_B[0].rotation = [0, 0, 0]
glasstable_A[0].position = [1.2569625103640771, 3.939004453830926, 0.06]
glasstable_A[0].rotation = [0, 0, 0]
bottle_bar_C[0].position = [3.732161829934379, 1.0096188706876097, 0.11]
bottle_bar_C[0].rotation = [0, 0, 0]
candle_F[0].position = [2.7573413977865213, 2.3399510352357664, 0.12]
candle_F[0].rotation = [0, 0, 0]
plant_D[0].position = [1.920447579353462, 2.866511264119986, 0.08]
plant_D[0].rotation = [0, 0, 0]
candle_G[0].position = [0.3510248942995171, 1.80241717080586, 0.14]
candle_G[0].rotation = [0, 0, 0]
candle_H[0].position = [0.29038539283020426, 1.3654933487069227, 0.14]
candle_H[0].rotation = [0, 0, 0]
book_shelf_A[0].position = [1.7858337385042928, 3.955149947877596, 0.12]
book_shelf_A[0].rotation = [0, 0, 0]
cart[0].position = [1.222996810136444, 3.497565872729224, 0.45]
cart[0].rotation = [0, 0, 0]
candle_I[0].position = [0.28135179009498756, 0.038893130481209015, 0.14]
candle_I[0].rotation = [0, 0, 0]
glass_H[0].position = [5.733132105109113, 2.813068052221144, 0.095]
glass_H[0].rotation = [0, 0, 0]
vasec[0].position = [0.363065085353093, 3.538986986361186, 0.18]
vasec[0].rotation = [0, 0, 0]
glasstable_B[0].position = [1.3289262107419963, 3.90663438556182, 0.06]
glasstable_B[0].rotation = [0, 0, 0]
bottle_bar_D[0].position = [4.506924418695703, 2.335944425988263, 0.145]
bottle_bar_D[0].rotation = [0, 0, 0]
shaker_A[0].position = [4.108022646062652, 4.512729672147454, 0.135]
shaker_A[0].rotation = [0, 0, 0]
artwork_B[0].position = [2.7546588453637373, 2.9425916750991883, 0.5]
artwork_B[0].rotation = [0, 0, 0]
booked_A[0].position = [0.4348801727234435, 3.0220165771558105, 0.12]
booked_A[0].rotation = [0, 0, 0]
artwork_C[0].position = [5.731603973258781, 2.2086049386038074, 0.575]
artwork_C[0].rotation = [0, 0, 0]
candle_J[0].position = [4.6218643845805865, 1.305279666848872, 0.125]
candle_J[0].rotation = [0, 0, 0]
artworkwall_B[0].position = [4.895364496286448, 3.1620948561360884, 0.55]
artworkwall_B[0].rotation = [0, 0, 0]
bottle_I[0].position = [4.739199463203902, 1.095922618689889, 0.11]
bottle_I[0].rotation = [0, 0, 0]
book_D[0].position = [1.7852499778931492, 1.6804607988623284, 0.12]
book_D[0].rotation = [0, 0, 0]
glass_I[0].position = [5.490695631171437, 1.1719249942647136, 0.095]
glass_I[0].rotation = [0, 0, 0]
artwork_wall_A[0].position = [0.9022181867647368, 2.022076398436536, 0.525]
artwork_wall_A[0].rotation = [0, 0, 0]
chairmetal_B[0].position = [1.895933344724047, 3.1985350969269217, 0.41]
chairmetal_B[0].rotation = [0, 0, 0]
bottle_J[0].position = [3.243206941706277, 1.805199922335784, 0.15]
bottle_J[0].rotation = [0, 0, 0]
artworkwall_C[0].position = [4.415756392778792, 0.7975071134717765, 0.55]
artworkwall_C[0].rotation = [0, 0, 0]
artwork_wall_B[0].position = [5.221445797057788, 2.468807176885873, 0.525]
artwork_wall_B[0].rotation = [0, 0, 0]
book_E[0].position = [1.7733653104829556, 3.452025891506903, 0.12]
book_E[0].rotation = [0, 0, 0]
candle_K[0].position = [2.1111135073984775, 4.702853753341957, 0.12]
candle_K[0].rotation = [0, 0, 0]
shakerbar_B[0].position = [1.4774173809802822, 4.857162274985807, 0.14]
shakerbar_B[0].rotation = [0, 0, 0]
book_F[0].position = [0.6770424588622401, 0.48912028981477784, 0.125]
book_F[0].rotation = [0, 0, 0]
glass_J[0].position = [0.8950329160256498, 1.502575423269935, 0.065]
glass_J[0].rotation = [0, 0, 0]
artwork_D[0].position = [0.5923155998736356, 3.705489542671629, 0.575]
artwork_D[0].rotation = [0, 0, 0]
glassbar_C[0].position = [5.295794550818679, 4.026220519431365, 0.09]
glassbar_C[0].rotation = [0, 0, 0]
glassbar_D[0].position = [4.365880985582154, 3.1815935885525732, 0.1]
glassbar_D[0].rotation = [0, 0, 0]
glass_table_C[0].position = [0.8852257215143022, 0.8872476982863259, 0.095]
glass_table_C[0].rotation = [0, 0, 0]
artwork_E[0].position = [5.332821234046234, 4.644626216062527, 0.525]
artwork_E[0].rotation = [0, 0, 0]
shaker_bar[0].position = [3.811459864499593, 0.8383980866631063, 0.14]
shaker_bar[0].rotation = [0, 0, 0]
artwork_F[0].position = [4.776635824575113, 1.2260691878437047, 0.55]
artwork_F[0].rotation = [0, 0, 0]
plant_E[0].position = [2.481646410214871, 3.6596095344542476, 0.825]
plant_E[0].rotation = [0, 0, 0]
artwork_G[0].position = [5.741661878317467, 2.059787783067151, 0.575]
artwork_G[0].rotation = [0, 0, 0]
artwork_H[0].position = [2.3010612622606708, 0.5022588651973647, 0.55]
artwork_H[0].rotation = [0, 0, 0]
table_A[0].position = [5.2798215128090265, 0.6780464387748941, 0.375]
table_A[0].rotation = [0, 0, 0]
table_B[0].position = [1.1439259248707714, 2.58170028516783, 0.375]
table_B[0].rotation = [0, 0, 0]
sideboard[0].position = [2.963413751407534, 1.1734323070705837, 0.41]
sideboard[0].rotation = [0, 0, 0]
shaker_B[0].position = [3.280498527301824, 4.088301612095755, 0.135]
shaker_B[0].rotation = [0, 0, 0]
glassbar_E[0].position = [4.039302197673676, 3.9011613226718396, 0.05]
glassbar_E[0].rotation = [0, 0, 0]
glass_K[0].position = [0.48671006076653756, 0.024589547739888307, 0.065]
glass_K[0].rotation = [0, 0, 0]
plate_C[0].position = [4.5253884174321675, 2.507655067172565, 0.015]
plate_C[0].rotation = [0, 0, 0]
chairwood_C[0].position = [5.836603947360895, 2.7540179293042506, 0.43]
chairwood_C[0].rotation = [0, 0, 0]
plate_D[0].position = [1.8921163098618026, 0.21598465008811962, 0.015]
plate_D[0].rotation = [0, 0, 0]
book_shelf_B[0].position = [5.967677042327059, 3.979642647054006, 0.12]
book_shelf_B[0].rotation = [0, 0, 0]
glass_L[0].position = [3.1962745429783306, 3.420923928603357, 0.075]
glass_L[0].rotation = [0, 0, 0]
artwork_I[0].position = [4.682311150083712, 3.9430627487458265, 0.525]
artwork_I[0].rotation = [0, 0, 0]
candle_L[0].position = [5.343406301223652, 4.319107976540458, 0.135]
candle_L[0].rotation = [0, 0, 0]
plant_F[0].position = [3.373882587237013, 3.874381681848969, 0.375]
plant_F[0].rotation = [0, 0, 0]
chairmetal_C[0].position = [2.7603363051210845, 4.423260703509832, 0.41]
chairmetal_C[0].rotation = [0, 0, 0]
candle_M[0].position = [5.161316469037005, 1.0474735980300136, 0.135]
candle_M[0].rotation = [0, 0, 0]
book_G[0].position = [0.3954264352882648, 0.12215510211705638, 0.125]
book_G[0].rotation = [0, 0, 0]
book_H[0].position = [0.8179499691908929, 3.9280452316796177, 0.125]
book_H[0].rotation = [0, 0, 0]
glassbar_F[0].position = [1.8012037525669287, 1.5182737176099241, 0.1]
glassbar_F[0].rotation = [0, 0, 0]
glass_M[0].position = [1.484826629050168, 1.7081406199650044, 0.095]
glass_M[0].rotation = [0, 0, 0]
bar[0].position = [4.043367681296084, 4.348845855889301, 0.525]
bar[0].rotation = [0, 0, 0]
glass_N[0].position = [1.7578378092965479, 2.0702006049854953, 0.06]
glass_N[0].rotation = [0, 0, 0]
plate_E[0].position = [3.6926704860558743, 3.0831872577761943, 0.015]
plate_E[0].rotation = [0, 0, 0]
planted[0].position = [4.056836014912866, 4.873412374559816, 0.075]
planted[0].rotation = [0, 0, 0]
glassbar_G[0].position = [2.3428935862576283, 0.16168135392391925, 0.085]
glassbar_G[0].rotation = [0, 0, 0]
artwork_wall_C[0].position = [4.995588552394777, 2.9602170046597043, 0.525]
artwork_wall_C[0].rotation = [0, 0, 0]
glass_O[0].position = [3.106562306599649, 3.178475603007622, 0.095]
glass_O[0].rotation = [0, 0, 0]
glassbar_H[0].position = [3.165649391881669, 2.5677245959062907, 0.08]
glassbar_H[0].rotation = [0, 0, 0]
artwork_wall_D[0].position = [4.339454024910103, 1.5628573722060857, 0.525]
artwork_wall_D[0].rotation = [0, 0, 0]
bottlebar_A[0].position = [0.7103355733082528, 4.325743719882941, 0.125]
bottlebar_A[0].rotation = [0, 0, 0]
cabinet[0].position = [5.8053007646672325, 2.598432129898591, 0.675]
cabinet[0].rotation = [0, 0, 0]
book_shelf_C[0].position = [4.703442986516524, 0.09859822978831645, 0.12]
book_shelf_C[0].rotation = [0, 0, 0]
glass_table_D[0].position = [2.951858843611048, 4.787279773811184, 0.065]
glass_table_D[0].rotation = [0, 0, 0]
lamp_B[0].position = [5.83585244801659, 4.499072604494279, 1.125]
lamp_B[0].rotation = [0, 0, 0]
booked_B[0].position = [1.6355094309098488, 3.8194698888034533, 0.12]
booked_B[0].rotation = [0, 0, 0]
glass_P[0].position = [3.5193115198112497, 2.3508888159652512, 0.095]
glass_P[0].rotation = [0, 0, 0]
candle_N[0].position = [3.996193479303425, 0.06646559435272648, 0.125]
candle_N[0].rotation = [0, 0, 0]
menustand[0].position = [3.408922221711002, 2.610593790828148, 0.625]
menustand[0].rotation = [0, 0, 0]
glassbar_I[0].position = [1.7220179377965956, 2.5426464682815997, 0.085]
glassbar_I[0].rotation = [0, 0, 0]
glassbar_J[0].position = [3.7246235494351594, 0.08699557166701899, 0.07]
glassbar_J[0].rotation = [0, 0, 0]
bookc[0].position = [2.8286831234266328, 3.8614813253226092, 0.12]
bookc[0].rotation = [0, 0, 0]
book_I[0].position = [0.7056133566199929, 1.5852226478305476, 0.12]
book_I[0].rotation = [0, 0, 0]
book_J[0].position = [0.08482491859695918, 1.012999255123141, 0.12]
book_J[0].rotation = [0, 0, 0]
candle_table_B[0].position = [2.095415691184068, 4.498769516798378, 0.13]
candle_table_B[0].rotation = [0, 0, 0]
glass_Q[0].position = [3.6436445532044175, 4.5102596679983815, 0.06]
glass_Q[0].rotation = [0, 0, 0]
vase_shelf_ed[0].position = [5.631769854702322, 1.6667827010704546, 0.18]
vase_shelf_ed[0].rotation = [0, 0, 0]
bottlebar_B[0].position = [2.9584575507693707, 4.976581590499122, 0.125]
bottlebar_B[0].rotation = [0, 0, 0]
glassbar_K[0].position = [3.1126234279700076, 0.2245913922513354, 0.07]
glassbar_K[0].rotation = [0, 0, 0]
chairwood_D[0].position = [3.709782915297378, 3.7311465764951643, 0.43]
chairwood_D[0].rotation = [0, 0, 0]
shaker_C[0].position = [4.636239932877618, 3.420957934845532, 0.135]
shaker_C[0].rotation = [0, 0, 0]
glass_R[0].position = [1.9930490178811804, 1.0548668539655603, 0.065]
glass_R[0].rotation = [0, 0, 0]
bottle_K[0].position = [0.9118197031138107, 1.169906163399705, 0.115]
bottle_K[0].rotation = [0, 0, 0]
shaker_D[0].position = [5.45778768925788, 4.854628226349742, 0.14]
shaker_D[0].rotation = [0, 0, 0]
book_K[0].position = [0.3886957955759276, 1.0099549644489474, 0.125]
book_K[0].rotation = [0, 0, 0]
glasstable_C[0].position = [0.17714005043749292, 4.438438389461324, 0.06]
glasstable_C[0].rotation = [0, 0, 0]
bottle_L[0].position = [5.495192064920063, 3.589630309218947, 0.11]
bottle_L[0].rotation = [0, 0, 0]
plate_F[0].position = [1.2932472032440416, 1.8031203038867787, 0.015]
plate_F[0].rotation = [0, 0, 0]
plate_G[0].position = [5.329784237750758, 0.7904249754307607, 0.015]
plate_G[0].rotation = [0, 0, 0]
chairmetal_D[0].position = [3.0668276647834714, 4.83858353993302, 0.41]
chairmetal_D[0].rotation = [0, 0, 0]
artwork_J[0].position = [2.014079048619756, 1.7412528634825724, 0.525]
artwork_J[0].rotation = [0, 0, 0]
shelf_B[0].position = [2.1152357467052196, 3.5113652371382758, 0.05]
shelf_B[0].rotation = [0, 0, 0]
bottlebar_C[0].position = [5.880343342816331, 3.3766943732826076, 0.13]
bottlebar_C[0].rotation = [0, 0, 0]
book_L[0].position = [2.4638333860277672, 3.9528740753620695, 0.12]
book_L[0].rotation = [0, 0, 0]
artworkwall_D[0].position = [3.581200160452844, 1.8298861246092986, 0.55]
artworkwall_D[0].rotation = [0, 0, 0]
shaker_E[0].position = [3.5284647705530854, 4.487878394888557, 0.135]
shaker_E[0].rotation = [0, 0, 0]
artwork_K[0].position = [5.631795954680242, 1.2452326997325647, 0.575]
artwork_K[0].rotation = [0, 0, 0]
plant_G[0].position = [2.281116906779901, 1.8758757827384382, 0.08]
plant_G[0].rotation = [0, 0, 0]
bottle_bar_E[0].position = [1.087726505771192, 4.407607468313451, 0.11]
bottle_bar_E[0].rotation = [0, 0, 0]
fern[0].position = [5.1890809929914194, 3.1426375325750784, 0.39]
fern[0].rotation = [0, 0, 0]
book_A[0].position = [5.574540512032615, 1.6062285530045766, 0.125]
book_A[0].rotation = [0, 0, 0]
glass_A[0].position = [3.033837339685889, 2.59359487865665, 0.06]
glass_A[0].rotation = [0, 0, 0]
shakerbar_A[0].position = [4.715531691534672, 0.018705055370359935, 0.14]
shakerbar_A[0].rotation = [0, 0, 0]
bottle_A[0].position = [2.8463661948532044, 2.417560465212109, 0.14]
bottle_A[0].rotation = [0, 0, 0]
succulent[0].position = [2.1356415437326812, 2.1083294478852106, 0.08]
succulent[0].rotation = [0, 0, 0]
candle_A[0].position = [0.19305257733919112, 2.364711907191015, 0.125]
candle_A[0].rotation = [0, 0, 0]
glass_B[0].position = [0.11039463379702186, 2.632718248489132, 0.06]
glass_B[0].rotation = [0, 0, 0]
glass_table_A[0].position = [5.95520789805671, 0.5562836074025362, 0.065]
glass_table_A[0].rotation = [0, 0, 0]
artworkwall_A[0].position = [4.635121271855126, 4.06113475196108, 0.55]
artworkwall_A[0].rotation = [0, 0, 0]
bottle_B[0].position = [1.2862524044654426, 0.7691340206721897, 0.15]
bottle_B[0].rotation = [0, 0, 0]
candle_table_A[0].position = [5.547232076824802, 3.817490426147896, 0.135]
candle_table_A[0].rotation = [0, 0, 0]
glassbar_A[0].position = [0.48231415240631303, 3.8049495554024477, 0.08]
glassbar_A[0].rotation = [0, 0, 0]
bottle_C[0].position = [5.181280166579551, 1.4938333274576687, 0.115]
bottle_C[0].rotation = [0, 0, 0]
chairmetal_A[0].position = [4.698340797374582, 3.606073622487169, 0.41]
chairmetal_A[0].rotation = [0, 0, 0]
glass_C[0].position = [0.6675246496052527, 0.5569234954421992, 0.065]
glass_C[0].rotation = [0, 0, 0]
plant_A[0].position = [2.5881457692384706, 4.485243816675635, 0.375]
plant_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [0.2322973293243138, 0.9078322772821734, 1.125]
lamp_A[0].rotation = [0, 0, 0]
bottle_bar_A[0].position = [0.47082681094649637, 0.51859133329901, 0.145]
bottle_bar_A[0].rotation = [0, 0, 0]
glass_D[0].position = [2.2838203690888426, 0.4482255779208444, 0.06]
glass_D[0].rotation = [0, 0, 0]
bottle_D[0].position = [4.249553514365811, 1.9762056133596335, 0.11]
bottle_D[0].rotation = [0, 0, 0]
glass_table_B[0].position = [0.6368540639718985, 3.3180785095818894, 0.095]
glass_table_B[0].rotation = [0, 0, 0]
plate_A[0].position = [5.122092265096544, 1.1064176747125631, 0.015]
plate_A[0].rotation = [0, 0, 0]
bottle_E[0].position = [3.606813631660442, 3.8578974092711116, 0.115]
bottle_E[0].rotation = [0, 0, 0]
candle_B[0].position = [4.697657033921686, 1.7733070104188493, 0.14]
candle_B[0].rotation = [0, 0, 0]
candle_C[0].position = [4.193088006110883, 2.8023161736638134, 0.125]
candle_C[0].rotation = [0, 0, 0]
book_B[0].position = [4.03266417663401, 0.17854624824992948, 0.12]
book_B[0].rotation = [0, 0, 0]
bottle_bar_B[0].position = [4.18607962438029, 4.221898969906156, 0.11]
bottle_bar_B[0].rotation = [0, 0, 0]
glass_E[0].position = [4.6006836691135184, 4.645479857962125, 0.06]
glass_E[0].rotation = [0, 0, 0]
plant_B[0].position = [5.5786691731162765, 0.48349323222342255, 0.39]
plant_B[0].rotation = [0, 0, 0]
plate_B[0].position = [4.614989479116393, 1.1172865062377064, 0.015]
plate_B[0].rotation = [0, 0, 0]
book_C[0].position = [3.309559954288307, 3.367456839117601, 0.125]
book_C[0].rotation = [0, 0, 0]
plantc[0].position = [5.441629367091493, 4.901527186222645, 0.075]
plantc[0].rotation = [0, 0, 0]
plant_C[0].position = [0.2030231241964673, 2.1474369632384076, 0.825]
plant_C[0].rotation = [0, 0, 0]
artwork_A[0].position = [1.8743556669570627, 2.1378194971307702, 0.5]
artwork_A[0].rotation = [0, 0, 0]
shelf_A[0].position = [3.612057758533364, 3.3310485974476967, 0.05]
shelf_A[0].rotation = [0, 0, 0]
glass_F[0].position = [2.8383500530184023, 4.059312296758514, 0.06]
glass_F[0].rotation = [0, 0, 0]
bottle_F[0].position = [3.069845821933235, 3.472445497147234, 0.14]
bottle_F[0].rotation = [0, 0, 0]
bottle_G[0].position = [1.816973728148596, 4.793390470421601, 0.11]
bottle_G[0].rotation = [0, 0, 0]
bottle_H[0].position = [0.7668771524965983, 0.19122451091807435, 0.15]
bottle_H[0].rotation = [0, 0, 0]
glassbar_B[0].position = [0.045880469412693525, 1.530532882870403, 0.09]
glassbar_B[0].rotation = [0, 0, 0]
glass_G[0].position = [1.584208025545297, 1.4615190794563726, 0.095]
glass_G[0].rotation = [0, 0, 0]
candle_D[0].position = [4.82850595152556, 4.494286301426272, 0.135]
candle_D[0].rotation = [0, 0, 0]
chairwood_A[0].position = [5.095395991633826, 2.6431508258192116, 0.43]
chairwood_A[0].rotation = [0, 0, 0]
candle_E[0].position = [0.05338182355649579, 3.5376471289860447, 0.135]
candle_E[0].rotation = [0, 0, 0]
chairwood_B[0].position = [1.6964733174185693, 2.023806551768899, 0.43]
chairwood_B[0].rotation = [0, 0, 0]
glasstable_A[0].position = [1.2569625103640771, 3.939004453830926, 0.06]
glasstable_A[0].rotation = [0, 0, 0]
bottle_bar_C[0].position = [3.732161829934379, 1.0096188706876097, 0.11]
bottle_bar_C[0].rotation = [0, 0, 0]
candle_F[0].position = [2.7573413977865213, 2.3399510352357664, 0.12]
candle_F[0].rotation = [0, 0, 0]
plant_D[0].position = [1.920447579353462, 2.866511264119986, 0.08]
plant_D[0].rotation = [0, 0, 0]
candle_G[0].position = [0.3510248942995171, 1.80241717080586, 0.14]
candle_G[0].rotation = [0, 0, 0]
candle_H[0].position = [0.29038539283020426, 1.3654933487069227, 0.14]
candle_H[0].rotation = [0, 0, 0]
book_shelf_A[0].position = [1.7858337385042928, 3.955149947877596, 0.12]
book_shelf_A[0].rotation = [0, 0, 0]
cart[0].position = [1.222996810136444, 3.497565872729224, 0.45]
cart[0].rotation = [0, 0, 0]
candle_I[0].position = [0.28135179009498756, 0.038893130481209015, 0.14]
candle_I[0].rotation = [0, 0, 0]
glass_H[0].position = [5.733132105109113, 2.813068052221144, 0.095]
glass_H[0].rotation = [0, 0, 0]
vasec[0].position = [0.363065085353093, 3.538986986361186, 0.18]
vasec[0].rotation = [0, 0, 0]
glasstable_B[0].position = [1.3289262107419963, 3.90663438556182, 0.06]
glasstable_B[0].rotation = [0, 0, 0]
bottle_bar_D[0].position = [4.506924418695703, 2.335944425988263, 0.145]
bottle_bar_D[0].rotation = [0, 0, 0]
shaker_A[0].position = [4.108022646062652, 4.512729672147454, 0.135]
shaker_A[0].rotation = [0, 0, 0]
artwork_B[0].position = [2.7546588453637373, 2.9425916750991883, 0.5]
artwork_B[0].rotation = [0, 0, 0]
booked_A[0].position = [0.4348801727234435, 3.0220165771558105, 0.12]
booked_A[0].rotation = [0, 0, 0]
artwork_C[0].position = [5.731603973258781, 2.2086049386038074, 0.575]
artwork_C[0].rotation = [0, 0, 0]
candle_J[0].position = [4.6218643845805865, 1.305279666848872, 0.125]
candle_J[0].rotation = [0, 0, 0]
artworkwall_B[0].position = [4.895364496286448, 3.1620948561360884, 0.55]
artworkwall_B[0].rotation = [0, 0, 0]
bottle_I[0].position = [4.739199463203902, 1.095922618689889, 0.11]
bottle_I[0].rotation = [0, 0, 0]
book_D[0].position = [1.7852499778931492, 1.6804607988623284, 0.12]
book_D[0].rotation = [0, 0, 0]
glass_I[0].position = [5.490695631171437, 1.1719249942647136, 0.095]
glass_I[0].rotation = [0, 0, 0]
artwork_wall_A[0].position = [0.9022181867647368, 2.022076398436536, 0.525]
artwork_wall_A[0].rotation = [0, 0, 0]
chairmetal_B[0].position = [1.895933344724047, 3.1985350969269217, 0.41]
chairmetal_B[0].rotation = [0, 0, 0]
bottle_J[0].position = [3.243206941706277, 1.805199922335784, 0.15]
bottle_J[0].rotation = [0, 0, 0]
artworkwall_C[0].position = [4.415756392778792, 0.7975071134717765, 0.55]
artworkwall_C[0].rotation = [0, 0, 0]
artwork_wall_B[0].position = [5.221445797057788, 2.468807176885873, 0.525]
artwork_wall_B[0].rotation = [0, 0, 0]
book_E[0].position = [1.7733653104829556, 3.452025891506903, 0.12]
book_E[0].rotation = [0, 0, 0]
candle_K[0].position = [2.1111135073984775, 4.702853753341957, 0.12]
candle_K[0].rotation = [0, 0, 0]
shakerbar_B[0].position = [1.4774173809802822, 4.857162274985807, 0.14]
shakerbar_B[0].rotation = [0, 0, 0]
book_F[0].position = [0.6770424588622401, 0.48912028981477784, 0.125]
book_F[0].rotation = [0, 0, 0]
glass_J[0].position = [0.8950329160256498, 1.502575423269935, 0.065]
glass_J[0].rotation = [0, 0, 0]
artwork_D[0].position = [0.5923155998736356, 3.705489542671629, 0.575]
artwork_D[0].rotation = [0, 0, 0]
glassbar_C[0].position = [5.295794550818679, 4.026220519431365, 0.09]
glassbar_C[0].rotation = [0, 0, 0]
glassbar_D[0].position = [4.365880985582154, 3.1815935885525732, 0.1]
glassbar_D[0].rotation = [0, 0, 0]
glass_table_C[0].position = [0.8852257215143022, 0.8872476982863259, 0.095]
glass_table_C[0].rotation = [0, 0, 0]
artwork_E[0].position = [5.332821234046234, 4.644626216062527, 0.525]
artwork_E[0].rotation = [0, 0, 0]
shaker_bar[0].position = [3.811459864499593, 0.8383980866631063, 0.14]
shaker_bar[0].rotation = [0, 0, 0]
artwork_F[0].position = [4.776635824575113, 1.2260691878437047, 0.55]
artwork_F[0].rotation = [0, 0, 0]
plant_E[0].position = [2.481646410214871, 3.6596095344542476, 0.825]
plant_E[0].rotation = [0, 0, 0]
artwork_G[0].position = [5.741661878317467, 2.059787783067151, 0.575]
artwork_G[0].rotation = [0, 0, 0]
artwork_H[0].position = [2.3010612622606708, 0.5022588651973647, 0.55]
artwork_H[0].rotation = [0, 0, 0]
table_A[0].position = [5.2798215128090265, 0.6780464387748941, 0.375]
table_A[0].rotation = [0, 0, 0]
table_B[0].position = [1.1439259248707714, 2.58170028516783, 0.375]
table_B[0].rotation = [0, 0, 0]
sideboard[0].position = [2.963413751407534, 1.1734323070705837, 0.41]
sideboard[0].rotation = [0, 0, 0]
shaker_B[0].position = [3.280498527301824, 4.088301612095755, 0.135]
shaker_B[0].rotation = [0, 0, 0]
glassbar_E[0].position = [4.039302197673676, 3.9011613226718396, 0.05]
glassbar_E[0].rotation = [0, 0, 0]
glass_K[0].position = [0.48671006076653756, 0.024589547739888307, 0.065]
glass_K[0].rotation = [0, 0, 0]
plate_C[0].position = [4.5253884174321675, 2.507655067172565, 0.015]
plate_C[0].rotation = [0, 0, 0]
chairwood_C[0].position = [5.836603947360895, 2.7540179293042506, 0.43]
chairwood_C[0].rotation = [0, 0, 0]
plate_D[0].position = [1.8921163098618026, 0.21598465008811962, 0.015]
plate_D[0].rotation = [0, 0, 0]
book_shelf_B[0].position = [5.967677042327059, 3.979642647054006, 0.12]
book_shelf_B[0].rotation = [0, 0, 0]
glass_L[0].position = [3.1962745429783306, 3.420923928603357, 0.075]
glass_L[0].rotation = [0, 0, 0]
artwork_I[0].position = [4.682311150083712, 3.9430627487458265, 0.525]
artwork_I[0].rotation = [0, 0, 0]
candle_L[0].position = [5.343406301223652, 4.319107976540458, 0.135]
candle_L[0].rotation = [0, 0, 0]
plant_F[0].position = [3.373882587237013, 3.874381681848969, 0.375]
plant_F[0].rotation = [0, 0, 0]
chairmetal_C[0].position = [2.7603363051210845, 4.423260703509832, 0.41]
chairmetal_C[0].rotation = [0, 0, 0]
candle_M[0].position = [5.161316469037005, 1.0474735980300136, 0.135]
candle_M[0].rotation = [0, 0, 0]
book_G[0].position = [0.3954264352882648, 0.12215510211705638, 0.125]
book_G[0].rotation = [0, 0, 0]
book_H[0].position = [0.8179499691908929, 3.9280452316796177, 0.125]
book_H[0].rotation = [0, 0, 0]
glassbar_F[0].position = [1.8012037525669287, 1.5182737176099241, 0.1]
glassbar_F[0].rotation = [0, 0, 0]
glass_M[0].position = [1.484826629050168, 1.7081406199650044, 0.095]
glass_M[0].rotation = [0, 0, 0]
bar[0].position = [4.043367681296084, 4.348845855889301, 0.525]
bar[0].rotation = [0, 0, 0]
glass_N[0].position = [1.7578378092965479, 2.0702006049854953, 0.06]
glass_N[0].rotation = [0, 0, 0]
plate_E[0].position = [3.6926704860558743, 3.0831872577761943, 0.015]
plate_E[0].rotation = [0, 0, 0]
planted[0].position = [4.056836014912866, 4.873412374559816, 0.075]
planted[0].rotation = [0, 0, 0]
glassbar_G[0].position = [2.3428935862576283, 0.16168135392391925, 0.085]
glassbar_G[0].rotation = [0, 0, 0]
artwork_wall_C[0].position = [4.995588552394777, 2.9602170046597043, 0.525]
artwork_wall_C[0].rotation = [0, 0, 0]
glass_O[0].position = [3.106562306599649, 3.178475603007622, 0.095]
glass_O[0].rotation = [0, 0, 0]
glassbar_H[0].position = [3.165649391881669, 2.5677245959062907, 0.08]
glassbar_H[0].rotation = [0, 0, 0]
artwork_wall_D[0].position = [4.339454024910103, 1.5628573722060857, 0.525]
artwork_wall_D[0].rotation = [0, 0, 0]
bottlebar_A[0].position = [0.7103355733082528, 4.325743719882941, 0.125]
bottlebar_A[0].rotation = [0, 0, 0]
cabinet[0].position = [5.8053007646672325, 2.598432129898591, 0.675]
cabinet[0].rotation = [0, 0, 0]
book_shelf_C[0].position = [4.703442986516524, 0.09859822978831645, 0.12]
book_shelf_C[0].rotation = [0, 0, 0]
glass_table_D[0].position = [2.951858843611048, 4.787279773811184, 0.065]
glass_table_D[0].rotation = [0, 0, 0]
lamp_B[0].position = [5.83585244801659, 4.499072604494279, 1.125]
lamp_B[0].rotation = [0, 0, 0]
booked_B[0].position = [1.6355094309098488, 3.8194698888034533, 0.12]
booked_B[0].rotation = [0, 0, 0]
glass_P[0].position = [3.5193115198112497, 2.3508888159652512, 0.095]
glass_P[0].rotation = [0, 0, 0]
candle_N[0].position = [3.996193479303425, 0.06646559435272648, 0.125]
candle_N[0].rotation = [0, 0, 0]
menustand[0].position = [3.408922221711002, 2.610593790828148, 0.625]
menustand[0].rotation = [0, 0, 0]
glassbar_I[0].position = [1.7220179377965956, 2.5426464682815997, 0.085]
glassbar_I[0].rotation = [0, 0, 0]
glassbar_J[0].position = [3.7246235494351594, 0.08699557166701899, 0.07]
glassbar_J[0].rotation = [0, 0, 0]
bookc[0].position = [2.8286831234266328, 3.8614813253226092, 0.12]
bookc[0].rotation = [0, 0, 0]
book_I[0].position = [0.7056133566199929, 1.5852226478305476, 0.12]
book_I[0].rotation = [0, 0, 0]
book_J[0].position = [0.08482491859695918, 1.012999255123141, 0.12]
book_J[0].rotation = [0, 0, 0]
candle_table_B[0].position = [2.095415691184068, 4.498769516798378, 0.13]
candle_table_B[0].rotation = [0, 0, 0]
glass_Q[0].position = [3.6436445532044175, 4.5102596679983815, 0.06]
glass_Q[0].rotation = [0, 0, 0]
vase_shelf_ed[0].position = [5.631769854702322, 1.6667827010704546, 0.18]
vase_shelf_ed[0].rotation = [0, 0, 0]
bottlebar_B[0].position = [2.9584575507693707, 4.976581590499122, 0.125]
bottlebar_B[0].rotation = [0, 0, 0]
glassbar_K[0].position = [3.1126234279700076, 0.2245913922513354, 0.07]
glassbar_K[0].rotation = [0, 0, 0]
chairwood_D[0].position = [3.709782915297378, 3.7311465764951643, 0.43]
chairwood_D[0].rotation = [0, 0, 0]
shaker_C[0].position = [4.636239932877618, 3.420957934845532, 0.135]
shaker_C[0].rotation = [0, 0, 0]
glass_R[0].position = [1.9930490178811804, 1.0548668539655603, 0.065]
glass_R[0].rotation = [0, 0, 0]
bottle_K[0].position = [0.9118197031138107, 1.169906163399705, 0.115]
bottle_K[0].rotation = [0, 0, 0]
shaker_D[0].position = [5.45778768925788, 4.854628226349742, 0.14]
shaker_D[0].rotation = [0, 0, 0]
book_K[0].position = [0.3886957955759276, 1.0099549644489474, 0.125]
book_K[0].rotation = [0, 0, 0]
glasstable_C[0].position = [0.17714005043749292, 4.438438389461324, 0.06]
glasstable_C[0].rotation = [0, 0, 0]
bottle_L[0].position = [5.495192064920063, 3.589630309218947, 0.11]
bottle_L[0].rotation = [0, 0, 0]
plate_F[0].position = [1.2932472032440416, 1.8031203038867787, 0.015]
plate_F[0].rotation = [0, 0, 0]
plate_G[0].position = [5.329784237750758, 0.7904249754307607, 0.015]
plate_G[0].rotation = [0, 0, 0]
chairmetal_D[0].position = [3.0668276647834714, 4.83858353993302, 0.41]
chairmetal_D[0].rotation = [0, 0, 0]
artwork_J[0].position = [2.014079048619756, 1.7412528634825724, 0.525]
artwork_J[0].rotation = [0, 0, 0]
shelf_B[0].position = [2.1152357467052196, 3.5113652371382758, 0.05]
shelf_B[0].rotation = [0, 0, 0]
bottlebar_C[0].position = [5.880343342816331, 3.3766943732826076, 0.13]
bottlebar_C[0].rotation = [0, 0, 0]
book_L[0].position = [2.4638333860277672, 3.9528740753620695, 0.12]
book_L[0].rotation = [0, 0, 0]
artworkwall_D[0].position = [3.581200160452844, 1.8298861246092986, 0.55]
artworkwall_D[0].rotation = [0, 0, 0]
shaker_E[0].position = [3.5284647705530854, 4.487878394888557, 0.135]
shaker_E[0].rotation = [0, 0, 0]
artwork_K[0].position = [5.631795954680242, 1.2452326997325647, 0.575]
artwork_K[0].rotation = [0, 0, 0]
plant_G[0].position = [2.281116906779901, 1.8758757827384382, 0.08]
plant_G[0].rotation = [0, 0, 0]
bottle_bar_E[0].position = [1.087726505771192, 4.407607468313451, 0.11]
bottle_bar_E[0].rotation = [0, 0, 0]
fern[0].position = [5.1890809929914194, 3.1426375325750784, 0.39]
fern[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed orientation references used by align_with constraints.
facing_pos_x = AssetInstance(rotation=[0, 0, radians(0)])
facing_pos_y = AssetInstance(rotation=[0, 0, radians(90)])
facing_neg_x = AssetInstance(rotation=[0, 0, radians(180)])
facing_neg_y = AssetInstance(rotation=[0, 0, radians(270)])


def place_at(asset_instance, position, yaw_degrees):
    """Place a floor or suspended object at an exact point with a stable orientation."""
    asset_instance.position = list(position)
    asset_instance.rotation = [0, 0, radians(yaw_degrees)]

    fixed_point = AssetInstance(position=list(position))
    orientation_reference = AssetInstance(
        rotation=[0, 0, radians(yaw_degrees)]
    )
    solver.distance_constraint(
        asset_instance, fixed_point, 0, 0, weight=10
    )
    solver.align_with(asset_instance, orientation_reference)


def place_against_wall(asset_instance, wall, position, yaw_degrees):
    """Anchor furniture or wall decor to a wall and preserve its intended location."""
    asset_instance.position = list(position)
    asset_instance.rotation = [0, 0, radians(yaw_degrees)]

    # Wall contact is the primary positional semantic.
    solver.against_wall(asset_instance, wall)
    solver.distance_constraint(
        asset_instance,
        AssetInstance(position=list(position)),
        0,
        0,
        weight=10,
    )
    solver.align_with(
        asset_instance,
        AssetInstance(rotation=[0, 0, radians(yaw_degrees)]),
    )


def place_on_surface(asset_asset, support_asset, x_position, y_position, yaw_degrees=0):
    """Place a small object on a supporting asset with an exact horizontal location."""
    support_instance = support_asset[0]
    asset_instance = asset_asset[0]

    support_top = support_instance.position[2] + support_asset.size[2] / 2
    object_z = support_top + asset_asset.size[2] / 2
    position = [x_position, y_position, object_z]

    asset_instance.position = position
    asset_instance.rotation = [0, 0, radians(yaw_degrees)]

    # The support relationship is more important than the initial point estimate.
    solver.on_top_of(asset_instance, support_instance)
    solver.distance_constraint(
        asset_instance,
        AssetInstance(position=position),
        0,
        0,
        weight=10,
    )
    solver.align_with(asset_instance, support_instance, angle=yaw_degrees)


def place_group_on_surface(asset_group, support_asset, points):
    """Assign a distinct supplied point to every object in a surface group."""
    for asset_obj, point in zip(asset_group, points):
        place_on_surface(
            asset_obj,
            support_asset,
            point[0],
            point[1],
            point[2] if len(point) > 2 else 0,
        )


def make_grid(center_x, center_y, columns, rows, spacing_x, spacing_y):
    """Generate a centered grid of nonidentical tabletop locations."""
    return [
        [
            center_x + (column - (columns - 1) / 2) * spacing_x,
            center_y + (row - (rows - 1) / 2) * spacing_y,
        ]
        for row in range(rows)
        for column in range(columns)
    ]


# ---------------------------------------------------------------------------
# Primary furniture layout
#
# The two dining tables occupy the middle of the room. The service bar is
# against the left wall, while storage furniture uses the upper wall. This
# leaves a broad circulation zone along the right side and keeps the area in
# front of the door at (6.00, 1.65) unobstructed.
# ---------------------------------------------------------------------------

place_against_wall(bar[0], walls[2], [0.35, 2.70, 0.525], 0)
place_against_wall(sideboard[0], walls[1], [1.10, 4.76, 0.41], 270)
place_against_wall(cabinet[0], walls[1], [2.75, 4.76, 0.675], 270)
place_at(cart[0], [4.65, 4.45, 0.45], 0)

place_at(table_A[0], [2.15, 1.45, 0.375], 0)
place_at(table_B[0], [4.15, 3.35, 0.375], 0)

# Four chairs face each table from its two long sides.
chair_layout = [
    (chairmetal_A, [1.38, 1.10, 0.41], 0),
    (chairwood_A,  [1.38, 1.80, 0.43], 0),
    (chairmetal_B, [2.92, 1.10, 0.41], 180),
    (chairwood_B,  [2.92, 1.80, 0.43], 180),
    (chairmetal_C, [3.38, 3.00, 0.41], 0),
    (chairwood_C,  [3.38, 3.70, 0.43], 0),
    (chairmetal_D, [4.92, 3.00, 0.41], 180),
    (chairwood_D,  [4.92, 3.70, 0.43], 180),
]
for asset_obj, position, yaw in chair_layout:
    place_at(asset_obj[0], position, yaw)

# Pendant lamps are centered over the dining tables. They are suspended rather
# than placed on another asset, so their exact-point constraints include height.
place_at(lamp_A[0], [2.15, 1.45, 2.55], 0)
place_at(lamp_B[0], [4.15, 3.35, 2.55], 0)

# The menu stand remains near the entrance but outside the 0.95 m door opening
# and its inward swing/circulation zone.
place_at(menustand[0], [5.50, 2.55, 0.625], 180)


# ---------------------------------------------------------------------------
# Floor plants
# ---------------------------------------------------------------------------

floor_plant_layout = [
    (plant_C, [1.00, 0.45, 0.825], 30),
    (plant_E, [4.70, 0.45, 0.825], 150),
    (plant_A, [0.52, 4.48, 0.375], 15),
    (plant_B, [2.02, 4.55, 0.39], 345),
    (plant_F, [5.55, 4.55, 0.375], 195),
    (fern,    [5.58, 3.72, 0.39], 165),
]
for asset_obj, position, yaw in floor_plant_layout:
    place_at(asset_obj[0], position, yaw)


# ---------------------------------------------------------------------------
# Wall-mounted shelves
#
# Both shelves sit above the service-bar zone. Their elevation clears the bar
# top, and the objects placed on them remain below the artwork band.
# ---------------------------------------------------------------------------

place_against_wall(shelf_A[0], walls[2], [0.15, 1.55, 1.35], 0)
place_against_wall(shelf_B[0], walls[2], [0.15, 3.85, 1.35], 0)


# ---------------------------------------------------------------------------
# Artwork
#
# Artwork is distributed around all four walls. The right-wall locations avoid
# the door centered at y=1.65. All panels are elevated above floor furniture.
# ---------------------------------------------------------------------------

all_artwork = [
    artworkwall_A,
    artwork_A,
    artwork_B,
    artwork_C,
    artworkwall_B,
    artwork_wall_A,
    artworkwall_C,
    artwork_wall_B,
    artwork_D,
    artwork_E,
    artwork_F,
    artwork_G,
    artwork_H,
    artwork_wall_C,
    artwork_wall_D,
    artwork_I,
    artwork_J,
    artworkwall_D,
    artwork_K,
]

artwork_locations = [
    # Bottom wall
    (walls[3], [0.55, 0.02, 2.15], 90),
    (walls[3], [1.50, 0.02, 2.15], 90),
    (walls[3], [2.45, 0.02, 2.15], 90),
    (walls[3], [3.40, 0.02, 2.15], 90),
    (walls[3], [4.35, 0.02, 2.15], 90),
    (walls[3], [5.30, 0.02, 2.15], 90),

    # Top wall
    (walls[1], [0.55, 4.98, 2.15], 270),
    (walls[1], [1.50, 4.98, 2.15], 270),
    (walls[1], [2.45, 4.98, 2.15], 270),
    (walls[1], [3.40, 4.98, 2.15], 270),
    (walls[1], [4.35, 4.98, 2.15], 270),
    (walls[1], [5.30, 4.98, 2.15], 270),

    # Left wall
    (walls[2], [0.02, 0.55, 2.15], 0),
    (walls[2], [0.02, 1.70, 2.15], 0),
    (walls[2], [0.02, 2.85, 2.15], 0),
    (walls[2], [0.02, 4.10, 2.15], 0),

    # Right wall; no panel is placed across the door at y=1.65.
    (walls[0], [5.98, 0.52, 2.15], 180),
    (walls[0], [5.98, 3.35, 2.15], 180),
    (walls[0], [5.98, 4.45, 2.15], 180),
]

for asset_obj, (wall_obj, position, yaw) in zip(
    all_artwork, artwork_locations
):
    place_against_wall(asset_obj[0], wall_obj, position, yaw)


# ---------------------------------------------------------------------------
# Bar serviceware
#
# Bar-labelled bottles, glasses, and shakers form an organized service display
# on the large bar top. The 3-by-8 grid provides separate positions for all
# objects and keeps them away from the dining tables.
# ---------------------------------------------------------------------------

bar_serviceware = [
    shakerbar_A,
    shakerbar_B,
    shaker_bar,
    glassbar_A,
    glassbar_B,
    glassbar_C,
    glassbar_D,
    glassbar_E,
    glassbar_F,
    glassbar_G,
    glassbar_H,
    glassbar_I,
    glassbar_J,
    glassbar_K,
    bottle_bar_A,
    bottle_bar_B,
    bottle_bar_C,
    bottle_bar_D,
    bottle_bar_E,
    bottlebar_A,
    bottlebar_B,
    bottlebar_C,
]
bar_points = make_grid(0.35, 2.70, 3, 8, 0.18, 0.26)
place_group_on_surface(bar_serviceware, bar, bar_points)


# ---------------------------------------------------------------------------
# Shelf styling
# ---------------------------------------------------------------------------

shelf_A_objects = [
    book_shelf_A,
    booked_A,
    bookc,
    vasec,
]
shelf_B_objects = [
    book_shelf_B,
    book_shelf_C,
    booked_B,
    vase_shelf_ed,
]

shelf_A_points = [
    [0.15, 1.00, 0],
    [0.15, 1.35, 0],
    [0.15, 1.70, 0],
    [0.15, 2.05, 0],
]
shelf_B_points = [
    [0.15, 3.30, 0],
    [0.15, 3.65, 0],
    [0.15, 4.00, 0],
    [0.15, 4.35, 0],
]

place_group_on_surface(shelf_A_objects, shelf_A, shelf_A_points)
place_group_on_surface(shelf_B_objects, shelf_B, shelf_B_points)


# ---------------------------------------------------------------------------
# Dining table A
#
# Four place settings occupy the table corners. Glasses, bottles, and candles
# use the remaining central and edge positions.
# ---------------------------------------------------------------------------

table_A_plates = [plate_A, plate_B, plate_C, plate_D]
table_A_plate_points = [
    [1.93, 0.91, 0],
    [2.37, 0.91, 180],
    [1.93, 1.99, 0],
    [2.37, 1.99, 180],
]
place_group_on_surface(table_A_plates, table_A, table_A_plate_points)

table_A_small_objects = [
    glass_table_A,
    glass_table_B,
    glass_table_C,
    glass_table_D,
    glasstable_A,
    glasstable_B,
    glasstable_C,
    candle_table_A,
    candle_table_B,
    glass_A,
    glass_B,
    glass_C,
    glass_E,
    glass_F,
    glass_G,
    glass_H,
    glass_I,
    bottle_A,
    bottle_B,
    bottle_C,
    candle_A,
    candle_B,
    candle_C,
]

table_A_small_points = [
    [1.86, 0.72], [2.02, 0.72], [2.18, 0.72], [2.34, 0.72],
    [1.86, 1.14], [2.02, 1.14], [2.18, 1.14], [2.34, 1.14],
    [1.86, 1.34], [2.02, 1.34], [2.18, 1.34], [2.34, 1.34],
    [1.86, 1.54], [2.02, 1.54], [2.18, 1.54], [2.34, 1.54],
    [1.86, 1.76], [2.02, 1.76], [2.18, 1.76], [2.34, 1.76],
    [1.94, 2.18], [2.15, 2.18], [2.36, 2.18],
]
place_group_on_surface(table_A_small_objects, table_A, table_A_small_points)


# ---------------------------------------------------------------------------
# Dining table B
#
# glass_D corresponds to the specified glass o0018, and table_B corresponds to
# table o0088. Its on_top_of constraint below explicitly preserves that required
# relationship.
# ---------------------------------------------------------------------------

table_B_plates = [plate_E, plate_F, plate_G]
table_B_plate_points = [
    [3.93, 2.82, 0],
    [4.37, 2.82, 180],
    [3.93, 3.88, 0],
]
place_group_on_surface(table_B_plates, table_B, table_B_plate_points)

table_B_small_objects = [
    glass_D,  # Required o0018 glass on o0088 table.
    glass_J,
    glass_K,
    glass_L,
    glass_M,
    glass_N,
    glass_O,
    glass_P,
    glass_Q,
    glass_R,
    bottle_D,
    bottle_E,
    bottle_F,
    candle_D,
    candle_E,
    candle_F,
]
table_B_small_points = [
    [3.86, 2.58], [4.04, 2.58], [4.22, 2.58], [4.40, 2.58],
    [3.86, 3.07], [4.04, 3.07], [4.22, 3.07], [4.40, 3.07],
    [3.86, 3.30], [4.04, 3.30], [4.22, 3.30], [4.40, 3.30],
    [3.86, 3.55], [4.04, 3.55], [4.22, 3.55], [4.40, 3.55],
]
place_group_on_surface(table_B_small_objects, table_B, table_B_small_points)


# ---------------------------------------------------------------------------
# Sideboard display
# ---------------------------------------------------------------------------

sideboard_objects = [
    book_A,
    book_B,
    book_C,
    book_D,
    book_E,
    book_F,
    candle_G,
    candle_H,
    candle_I,
    candle_J,
    succulent,
    plantc,
]
sideboard_points = make_grid(1.10, 4.76, 6, 2, 0.22, 0.14)
place_group_on_surface(sideboard_objects, sideboard, sideboard_points)


# ---------------------------------------------------------------------------
# Cabinet display
# ---------------------------------------------------------------------------

cabinet_objects = [
    book_G,
    book_H,
    book_I,
    book_J,
    book_K,
    book_L,
    candle_K,
    candle_L,
    candle_M,
    candle_N,
    plant_D,
    plant_G,
]
cabinet_points = make_grid(2.75, 4.76, 6, 2, 0.16, 0.14)
place_group_on_surface(cabinet_objects, cabinet, cabinet_points)


# ---------------------------------------------------------------------------
# Mobile cart display
#
# Cocktail shakers and the remaining bottles are grouped on the serving cart.
# ---------------------------------------------------------------------------

cart_objects = [
    shaker_A,
    shaker_B,
    shaker_C,
    shaker_D,
    shaker_E,
    bottle_G,
    bottle_H,
    bottle_I,
    bottle_J,
    bottle_K,
    bottle_L,
    planted,
]
cart_points = make_grid(4.65, 4.45, 2, 6, 0.20, 0.13)
place_group_on_surface(cart_objects, cart, cart_points)

solver.constraints = []
candle_N[0].position = [2.8299999237060547, 4.829999923706055, 1.475000023841858]
candle_N[0].rotation = [0, 0, 0.002540838557857311]
candle_N[0].optimize = 2
glass_R[0].position = [4.039999961853027, 3.299999952316284, 0.8149999976158142]
glass_R[0].rotation = [0, 0, 0.022791605554272402]
glass_R[0].optimize = 2
bottlebar_A[0].position = [0.3499999940395355, 3.3499999046325684, 1.1749999523162842]
bottlebar_A[0].rotation = [0, 0, 0.022791645292255164]
bottlebar_A[0].optimize = 2
book_shelf_A[0].position = [0.15000000596046448, 1.0, 0.2199999988079071]
book_shelf_A[0].rotation = [0, 0, 0.022790723574158917]
book_shelf_A[0].optimize = 2
plant_C[0].position = [1.0, 0.5135303735733032, 0.824999988079071]
plant_C[0].rotation = [0, 0, 0.5330235812359582]
plant_C[0].optimize = 2
bottlebar_B[0].position = [0.5299999713897705, 3.3499999046325684, 1.1749999523162842]
bottlebar_B[0].rotation = [0, 0, 0.022791645292255164]
bottlebar_B[0].optimize = 2
candle_B[0].position = [2.1500000953674316, 2.180000066757202, 0.8899999856948853]
candle_B[0].rotation = [0, 0, 0.022791679897236877]
candle_B[0].optimize = 2
glass_A[0].position = [2.0199999809265137, 1.340000033378601, 0.8100000023841858]
glass_A[0].rotation = [0, 0, 0.022791679897236877]
glass_A[0].optimize = 2
bookc[0].position = [0.15000000596046448, 1.7000000476837158, 0.2199999988079071]
bookc[0].rotation = [0, 0, 0.022790723574158917]
bookc[0].optimize = 2
plate_F[0].position = [4.369999885559082, 2.819999933242798, 0.7649999856948853]
plate_F[0].rotation = [0, 0, -3.118801048035521]
plate_F[0].optimize = 2
plate_B[0].position = [2.369999885559082, 0.9100000262260437, 0.7649999856948853]
plate_B[0].rotation = [0, 0, -3.118800973692556]
plate_B[0].optimize = 2
glass_M[0].position = [3.859999895095825, 3.069999933242798, 0.8450000286102295]
glass_M[0].rotation = [0, 0, 0.022791605554272402]
glass_M[0].optimize = 2
candle_G[0].position = [0.550000011920929, 4.829999923706055, 0.9599999785423279]
candle_G[0].rotation = [0, 0, 0.002540838557857311]
candle_G[0].optimize = 2
glassbar_H[0].position = [0.3499999940395355, 2.569999933242798, 1.1299999952316284]
glassbar_H[0].rotation = [0, 0, 0.022791645292255164]
glassbar_H[0].optimize = 2
book_E[0].position = [1.4299999475479126, 4.690000057220459, 0.9399999976158142]
book_E[0].rotation = [0, 0, 0.002540838557857311]
book_E[0].optimize = 2
glass_N[0].position = [4.039999961853027, 3.069999933242798, 0.8100000023841858]
glass_N[0].rotation = [0, 0, 0.022791605554272402]
glass_N[0].optimize = 2
candle_table_A[0].position = [2.3399999141693115, 1.1399999856948853, 0.8849999904632568]
candle_table_A[0].rotation = [0, 0, 0.022791679897236877]
candle_table_A[0].optimize = 2
shaker_B[0].position = [4.75, 4.125, 1.034999966621399]
shaker_B[0].rotation = [0, 0, 0.022791456869282706]
shaker_B[0].optimize = 2
artworkwall_D[0].position = [5.9885125160217285, 3.3499999046325684, 0.550000011920929]
artworkwall_D[0].rotation = [0, 0, -3.1390517385055796]
artworkwall_D[0].optimize = 2
chairwood_C[0].position = [3.380000114440918, 3.700000047683716, 0.4300000071525574]
chairwood_C[0].rotation = [0, 0, 0.00942477746072377]
chairwood_C[0].optimize = 2
chairmetal_C[0].position = [3.380000114440918, 3.0, 0.4099999964237213]
chairmetal_C[0].rotation = [0, 0, 0.00942477746072377]
chairmetal_C[0].optimize = 2
succulent[0].position = [1.4299999475479126, 4.829999923706055, 0.8999999761581421]
succulent[0].rotation = [0, 0, 0.002540838557857311]
succulent[0].optimize = 2
glass_E[0].position = [1.8600000143051147, 1.5399999618530273, 0.8100000023841858]
glass_E[0].rotation = [0, 0, 0.022791679897236877]
glass_E[0].optimize = 2
booked_B[0].position = [0.15000000596046448, 4.0, 0.2199999988079071]
booked_B[0].rotation = [0, 0, 0.022790723574158917]
booked_B[0].optimize = 2
artwork_A[0].position = [1.5, 0.011367769911885262, 0.5]
artwork_A[0].rotation = [0, 0, 1.5733372440233822]
artwork_A[0].optimize = 2
table_A[0].position = [2.1500000953674316, 1.4500000476837158, 0.375]
table_A[0].rotation = [0, 0, 0.17907078470237417]
table_A[0].optimize = 2
glassbar_D[0].position = [0.23015296459197998, 2.3191401958465576, 1.149999976158142]
glassbar_D[0].rotation = [0, 0, 0.022791645292255164]
glassbar_D[0].optimize = 2
shakerbar_A[0].position = [0.30738377571105957, 1.810875415802002, 1.1899999380111694]
shakerbar_A[0].rotation = [0, 0, 0.022791645292255164]
shakerbar_A[0].optimize = 2
candle_C[0].position = [2.359999895095825, 2.180000066757202, 0.875]
candle_C[0].rotation = [0, 0, 0.022791679897236877]
candle_C[0].optimize = 2
glassbar_E[0].position = [0.3499999940395355, 2.309999942779541, 1.0999999046325684]
glassbar_E[0].rotation = [0, 0, 0.022791645292255164]
glassbar_E[0].optimize = 2
artwork_K[0].position = [5.9885125160217285, 4.449999809265137, 0.574999988079071]
artwork_K[0].rotation = [0, 0, -3.1390517375834066]
artwork_K[0].optimize = 2
glass_table_A[0].position = [1.8600000143051147, 0.7200000286102295, 0.8149999976158142]
glass_table_A[0].rotation = [0, 0, 0.022791679897236877]
glass_table_A[0].optimize = 2
plant_F[0].position = [5.550000190734863, 4.550000190734863, 0.375]
plant_F[0].rotation = [0, 0, -2.870368489037254]
plant_F[0].optimize = 2
book_B[0].position = [0.7699999809265137, 4.690000057220459, 0.9399999976158142]
book_B[0].rotation = [0, 0, 0.002540838557857311]
book_B[0].optimize = 2
plant_D[0].position = [2.990000009536743, 4.829999923706055, 1.4300000667572021]
plant_D[0].rotation = [0, 0, 0.002540838557857311]
plant_D[0].optimize = 2
bottle_B[0].position = [2.180000066757202, 1.7599999904632568, 0.8999999761581421]
bottle_B[0].rotation = [0, 0, 0.022791679897236877]
bottle_B[0].optimize = 2
glass_B[0].position = [2.180000066757202, 1.340000033378601, 0.8100000023841858]
glass_B[0].rotation = [0, 0, 0.022791679897236877]
glass_B[0].optimize = 2
glass_J[0].position = [4.039999961853027, 2.5799999237060547, 0.8149999976158142]
glass_J[0].rotation = [0, 0, 0.022791605554272402]
glass_J[0].optimize = 2
glass_L[0].position = [4.400000095367432, 2.5799999237060547, 0.824999988079071]
glass_L[0].rotation = [0, 0, 0.022791605554272402]
glass_L[0].optimize = 2
bottle_I[0].position = [4.75, 4.514999866485596, 1.0099999904632568]
bottle_I[0].rotation = [0, 0, 0.022791456869282706]
bottle_I[0].optimize = 2
artwork_C[0].position = [3.4000000953674316, 0.011367769911885262, 0.574999988079071]
artwork_C[0].rotation = [0, 0, 1.5733372418791103]
artwork_C[0].optimize = 2
book_A[0].position = [0.550000011920929, 4.690000057220459, 0.9449999928474426]
book_A[0].rotation = [0, 0, 0.002540838557857311]
book_A[0].optimize = 2
candle_M[0].position = [2.6700000762939453, 4.829999923706055, 1.4850000143051147]
candle_M[0].rotation = [0, 0, 0.002540838557857311]
candle_M[0].optimize = 2
plant_A[0].position = [0.5199999809265137, 4.480000019073486, 0.375]
plant_A[0].rotation = [0, 0, 0.27122416455253917]
plant_A[0].optimize = 2
candle_D[0].position = [4.039999961853027, 3.549999952316284, 0.8849999904632568]
candle_D[0].rotation = [0, 0, 0.022791605554272402]
candle_D[0].optimize = 2
glass_F[0].position = [2.0199999809265137, 1.5399999618530273, 0.8100000023841858]
glass_F[0].rotation = [0, 0, 0.022791679897236877]
glass_F[0].optimize = 2
glass_table_B[0].position = [2.0199999809265137, 0.7200000286102295, 0.8450000286102295]
glass_table_B[0].rotation = [0, 0, 0.022791679897236877]
glass_table_B[0].optimize = 2
book_shelf_C[0].position = [0.15000000596046448, 3.6500000953674316, 0.2199999988079071]
book_shelf_C[0].rotation = [0, 0, 0.022790723574158917]
book_shelf_C[0].optimize = 2
shelf_B[0].position = [0.1700456589460373, 3.8499999046325684, 0.05000000074505806]
shelf_B[0].rotation = [0, 0, 0.027428477098367914]
shelf_B[0].optimize = 2
glass_P[0].position = [4.400000095367432, 3.069999933242798, 0.8450000286102295]
glass_P[0].rotation = [0, 0, 0.022791605554272402]
glass_P[0].optimize = 2
shaker_E[0].position = [4.550000190734863, 4.385000228881836, 1.034999966621399]
shaker_E[0].rotation = [0, 0, 0.022791456869282706]
shaker_E[0].optimize = 2
shakerbar_B[0].position = [0.3499999940395355, 1.7899999618530273, 1.1899999380111694]
shakerbar_B[0].rotation = [0, 0, 0.022791645292255164]
shakerbar_B[0].optimize = 2
chairmetal_D[0].position = [4.920000076293945, 3.0, 0.4099999964237213]
chairmetal_D[0].rotation = [0, 0, -3.1321678761290697]
chairmetal_D[0].optimize = 2
candle_table_B[0].position = [1.8600000143051147, 1.340000033378601, 0.8799999952316284]
candle_table_B[0].rotation = [0, 0, 0.022791679897236877]
candle_table_B[0].optimize = 2
bottle_bar_D[0].position = [0.5299999713897705, 3.0899999141693115, 1.1949999332427979]
bottle_bar_D[0].rotation = [0, 0, 0.022791645292255164]
bottle_bar_D[0].optimize = 2
artworkwall_A[0].position = [0.550000011920929, 0.011367498897016048, 0.550000011920929]
artworkwall_A[0].rotation = [0, 0, 1.5733372428012833]
artworkwall_A[0].optimize = 2
artwork_I[0].position = [0.011367769911885262, 4.099999904632568, 0.5249999761581421]
artwork_I[0].rotation = [0, 0, 0.002540916928559797]
artwork_I[0].optimize = 2
bottle_bar_B[0].position = [0.17000000178813934, 3.0899999141693115, 1.159999966621399]
bottle_bar_B[0].rotation = [0, 0, 0.022791645292255164]
bottle_bar_B[0].optimize = 2
artworkwall_B[0].position = [4.349999904632568, 0.011367498897016048, 0.550000011920929]
artworkwall_B[0].rotation = [0, 0, 1.5733372428012833]
artworkwall_B[0].optimize = 2
glass_C[0].position = [2.3399999141693115, 1.340000033378601, 0.8149999976158142]
glass_C[0].rotation = [0, 0, 0.022791679897236877]
glass_C[0].optimize = 2
artworkwall_C[0].position = [0.550000011920929, 4.9885125160217285, 0.550000011920929]
artworkwall_C[0].rotation = [0, 0, -1.568255411710683]
artworkwall_C[0].optimize = 2
glasstable_C[0].position = [2.180000066757202, 1.1399999856948853, 0.8100000023841858]
glasstable_C[0].rotation = [0, 0, 0.022791679897236877]
glasstable_C[0].optimize = 2
book_K[0].position = [2.990000009536743, 4.690000057220459, 1.475000023841858]
book_K[0].rotation = [0, 0, 0.002540838557857311]
book_K[0].optimize = 2
plate_C[0].position = [1.9299999475479126, 1.9900000095367432, 0.7649999856948853]
plate_C[0].rotation = [0, 0, 0.022791679897236877]
plate_C[0].optimize = 2
artwork_J[0].position = [5.9885125160217285, 0.5199999809265137, 0.5249999761581421]
artwork_J[0].rotation = [0, 0, -3.1390517375834066]
artwork_J[0].optimize = 2
book_C[0].position = [0.9900000095367432, 4.690000057220459, 0.9449999928474426]
book_C[0].rotation = [0, 0, 0.002540838557857311]
book_C[0].optimize = 2
glass_Q[0].position = [3.859999895095825, 3.299999952316284, 0.8100000023841858]
glass_Q[0].rotation = [0, 0, 0.022791605554272402]
glass_Q[0].optimize = 2
shaker_D[0].position = [4.75, 4.255000114440918, 1.0399999618530273]
shaker_D[0].rotation = [0, 0, 0.022791456869282706]
shaker_D[0].optimize = 2
book_shelf_B[0].position = [0.15000000596046448, 3.299999952316284, 0.2199999988079071]
book_shelf_B[0].rotation = [0, 0, 0.022790723574158917]
book_shelf_B[0].optimize = 2
candle_J[0].position = [1.2100000381469727, 4.829999923706055, 0.9449999928474426]
candle_J[0].rotation = [0, 0, 0.002540838557857311]
candle_J[0].optimize = 2
chairwood_B[0].position = [2.9200000762939453, 1.7999999523162842, 0.4300000071525574]
chairwood_B[0].rotation = [0, 0, -3.1321678761290697]
chairwood_B[0].optimize = 2
plate_A[0].position = [1.9299999475479126, 0.9100000262260437, 0.7649999856948853]
plate_A[0].rotation = [0, 0, 0.022791679897236877]
plate_A[0].optimize = 2
glassbar_C[0].position = [0.5299999713897705, 2.049999952316284, 1.1399999856948853]
glassbar_C[0].rotation = [0, 0, 0.022791645292255164]
glassbar_C[0].optimize = 2
bottle_A[0].position = [2.0199999809265137, 1.7599999904632568, 0.8899999856948853]
bottle_A[0].rotation = [0, 0, 0.022791679897236877]
bottle_A[0].optimize = 2
artwork_E[0].position = [3.4000000953674316, 4.9885125160217285, 0.5249999761581421]
artwork_E[0].rotation = [0, 0, -1.5682554107885098]
artwork_E[0].optimize = 2
book_H[0].position = [2.509999990463257, 4.690000057220459, 1.475000023841858]
book_H[0].rotation = [0, 0, 0.002540838557857311]
book_H[0].optimize = 2
shelf_A[0].position = [0.1700456589460373, 1.5499999523162842, 0.05000000074505806]
shelf_A[0].rotation = [0, 0, 0.027428477098367914]
shelf_A[0].optimize = 2
candle_H[0].position = [0.7699999809265137, 4.829999923706055, 0.9599999785423279]
candle_H[0].rotation = [0, 0, 0.002540838557857311]
candle_H[0].optimize = 2
glassbar_K[0].position = [0.3499999940395355, 2.8299999237060547, 1.1200000047683716]
glassbar_K[0].rotation = [0, 0, 0.022791645292255164]
glassbar_K[0].optimize = 2
glass_O[0].position = [4.21999979019165, 3.069999933242798, 0.8450000286102295]
glass_O[0].rotation = [0, 0, 0.022791605554272402]
glass_O[0].optimize = 2
vase_shelf_ed[0].position = [0.15000000596046448, 4.349999904632568, 0.2800000011920929]
vase_shelf_ed[0].rotation = [0, 0, 0.022790723574158917]
vase_shelf_ed[0].optimize = 2
plant_B[0].position = [2.0199999809265137, 4.550000190734863, 0.38999998569488525]
plant_B[0].rotation = [0, 0, -0.2523746056580361]
plant_B[0].optimize = 2
glass_D[0].position = [3.859999895095825, 2.5799999237060547, 0.8100000023841858]
glass_D[0].rotation = [0, 0, 0.022791605554272402]
glass_D[0].optimize = 2
glassbar_F[0].position = [0.5299999713897705, 2.309999942779541, 1.149999976158142]
glassbar_F[0].rotation = [0, 0, 0.022791645292255164]
glassbar_F[0].optimize = 2
shaker_A[0].position = [4.550000190734863, 4.125, 1.034999966621399]
shaker_A[0].rotation = [0, 0, 0.022791456869282706]
shaker_A[0].optimize = 2
lamp_A[0].position = [2.1500000953674316, 1.4500000476837158, 1.125]
lamp_A[0].rotation = [0, 0, 0.00942477746072377]
lamp_A[0].optimize = 2
cart[0].position = [4.650000095367432, 4.449999809265137, 0.44999998807907104]
cart[0].rotation = [0, 0, 0.08482299704637274]
cart[0].optimize = 2
bottle_bar_A[0].position = [0.5299999713897705, 2.8299999237060547, 1.1949999332427979]
bottle_bar_A[0].rotation = [0, 0, 0.022791645292255164]
bottle_bar_A[0].optimize = 2
book_G[0].position = [2.3499999046325684, 4.690000057220459, 1.475000023841858]
book_G[0].rotation = [0, 0, 0.002540838557857311]
book_G[0].optimize = 2
bottle_J[0].position = [4.550000190734863, 4.644999980926514, 1.0499999523162842]
bottle_J[0].rotation = [0, 0, 0.022791456869282706]
bottle_J[0].optimize = 2
bottle_bar_E[0].position = [0.17000000178813934, 3.3499999046325684, 1.159999966621399]
bottle_bar_E[0].rotation = [0, 0, 0.022791645292255164]
bottle_bar_E[0].optimize = 2
plant_G[0].position = [3.1500000953674316, 4.829999923706055, 1.4300000667572021]
plant_G[0].rotation = [0, 0, 0.002540838557857311]
plant_G[0].optimize = 2
chairmetal_B[0].position = [2.9200000762939453, 1.100000023841858, 0.4099999964237213]
chairmetal_B[0].rotation = [0, 0, -3.1321678761290697]
chairmetal_B[0].optimize = 2
artwork_wall_C[0].position = [0.011367769911885262, 1.7000000476837158, 0.5249999761581421]
artwork_wall_C[0].rotation = [0, 0, 0.002540916928559797]
artwork_wall_C[0].optimize = 2
artwork_D[0].position = [2.450000047683716, 4.9885125160217285, 0.574999988079071]
artwork_D[0].rotation = [0, 0, -1.5682554107885098]
artwork_D[0].optimize = 2
artwork_wall_D[0].position = [0.011367769911885262, 2.8499999046325684, 0.5249999761581421]
artwork_wall_D[0].rotation = [0, 0, 0.002540916928559797]
artwork_wall_D[0].optimize = 2
plate_G[0].position = [3.930000066757202, 3.880000114440918, 0.7649999856948853]
plate_G[0].rotation = [0, 0, 0.022791605554272402]
plate_G[0].optimize = 2
booked_A[0].position = [0.15000000596046448, 1.350000023841858, 0.2199999988079071]
booked_A[0].rotation = [0, 0, 0.022790723574158917]
booked_A[0].optimize = 2
chairmetal_A[0].position = [1.3799999952316284, 1.100000023841858, 0.4099999964237213]
chairmetal_A[0].rotation = [0, 0, 0.00942477746072377]
chairmetal_A[0].optimize = 2
vasec[0].position = [0.15000000596046448, 2.049999952316284, 0.2800000011920929]
vasec[0].rotation = [0, 0, 0.022790723574158917]
vasec[0].optimize = 2
glass_H[0].position = [2.3399999141693115, 1.5399999618530273, 0.8450000286102295]
glass_H[0].rotation = [0, 0, 0.022791679897236877]
glass_H[0].optimize = 2
glass_table_C[0].position = [2.180000066757202, 0.7200000286102295, 0.8450000286102295]
glass_table_C[0].rotation = [0, 0, 0.022791679897236877]
glass_table_C[0].optimize = 2
glassbar_B[0].position = [0.3499999940395355, 2.049999952316284, 1.1399999856948853]
glassbar_B[0].rotation = [0, 0, 0.022791645292255164]
glassbar_B[0].optimize = 2
glassbar_G[0].position = [0.19153755903244019, 2.573272466659546, 1.1349999904632568]
glassbar_G[0].rotation = [0, 0, 0.022791645292255164]
glassbar_G[0].optimize = 2
plant_E[0].position = [4.699999809265137, 0.5109431743621826, 0.824999988079071]
plant_E[0].rotation = [0, 0, 2.6274186791011758]
plant_E[0].optimize = 2
book_J[0].position = [2.8299999237060547, 4.690000057220459, 1.4700000286102295]
book_J[0].rotation = [0, 0, 0.002540838557857311]
book_J[0].optimize = 2
glasstable_A[0].position = [1.8600000143051147, 1.1399999856948853, 0.8100000023841858]
glasstable_A[0].rotation = [0, 0, 0.022791679897236877]
glasstable_A[0].optimize = 2
book_L[0].position = [3.1500000953674316, 4.690000057220459, 1.4700000286102295]
book_L[0].rotation = [0, 0, 0.002540838557857311]
book_L[0].optimize = 2
glassbar_J[0].position = [0.17000000178813934, 2.8299999237060547, 1.1200000047683716]
glassbar_J[0].rotation = [0, 0, 0.022791645292255164]
glassbar_J[0].optimize = 2
bottle_K[0].position = [4.75, 4.644999980926514, 1.0149999856948853]
bottle_K[0].rotation = [0, 0, 0.022791456869282706]
bottle_K[0].optimize = 2
bottle_bar_C[0].position = [0.3499999940395355, 3.0899999141693115, 1.159999966621399]
bottle_bar_C[0].rotation = [0, 0, 0.022791645292255164]
bottle_bar_C[0].optimize = 2
bottlebar_C[0].position = [0.17000000178813934, 3.609999895095825, 1.1799999475479126]
bottlebar_C[0].rotation = [0, 0, 0.022791645292255164]
bottlebar_C[0].optimize = 2
artwork_wall_A[0].position = [5.300000190734863, 0.011367769911885262, 0.5249999761581421]
artwork_wall_A[0].rotation = [0, 0, 1.5733372437234565]
artwork_wall_A[0].optimize = 2
candle_I[0].position = [0.9900000095367432, 4.829999923706055, 0.9599999785423279]
candle_I[0].rotation = [0, 0, 0.002540838557857311]
candle_I[0].optimize = 2
candle_E[0].position = [4.21999979019165, 3.549999952316284, 0.8849999904632568]
candle_E[0].rotation = [0, 0, 0.022791605554272402]
candle_E[0].optimize = 2
candle_A[0].position = [1.940000057220459, 2.180000066757202, 0.875]
candle_A[0].rotation = [0, 0, 0.022791679897236877]
candle_A[0].optimize = 2
bottle_E[0].position = [4.400000095367432, 3.299999952316284, 0.8650000095367432]
bottle_E[0].rotation = [0, 0, 0.022791605554272402]
bottle_E[0].optimize = 2
book_F[0].position = [1.649999976158142, 4.690000057220459, 0.9449999928474426]
book_F[0].rotation = [0, 0, 0.002540838557857311]
book_F[0].optimize = 2
planted[0].position = [4.75, 4.775000095367432, 0.9749999642372131]
planted[0].rotation = [0, 0, 0.022791456869282706]
planted[0].optimize = 2
menustand[0].position = [5.5, 2.549999952316284, 0.625]
menustand[0].rotation = [0, 0, -3.1321678761290697]
menustand[0].optimize = 2
chairwood_D[0].position = [4.920000076293945, 3.700000047683716, 0.4300000071525574]
chairwood_D[0].rotation = [0, 0, -3.1321678761290697]
chairwood_D[0].optimize = 2
book_I[0].position = [2.6700000762939453, 4.690000057220459, 1.4700000286102295]
book_I[0].rotation = [0, 0, 0.002540838557857311]
book_I[0].optimize = 2
glass_K[0].position = [4.21999979019165, 2.5799999237060547, 0.8149999976158142]
glass_K[0].rotation = [0, 0, 0.022791605554272402]
glass_K[0].optimize = 2
bottle_D[0].position = [4.21999979019165, 3.299999952316284, 0.8600000143051147]
bottle_D[0].rotation = [0, 0, 0.022791605554272402]
bottle_D[0].optimize = 2
artwork_wall_B[0].position = [1.5, 4.9885125160217285, 0.5249999761581421]
artwork_wall_B[0].rotation = [0, 0, -1.5682554107885098]
artwork_wall_B[0].optimize = 2
sideboard[0].position = [1.100000023841858, 4.700646877288818, 0.4099999964237213]
sideboard[0].rotation = [0, 0, -1.4935735837185398]
sideboard[0].optimize = 2
shaker_bar[0].position = [0.5299999713897705, 1.7899999618530273, 1.1899999380111694]
shaker_bar[0].rotation = [0, 0, 0.022791645292255164]
shaker_bar[0].optimize = 2
table_B[0].position = [4.150000095367432, 3.3499999046325684, 0.375]
table_B[0].rotation = [0, 0, 0.1288052903038748]
table_B[0].optimize = 2
plantc[0].position = [1.649999976158142, 4.829999923706055, 0.8949999809265137]
plantc[0].rotation = [0, 0, 0.002540838557857311]
plantc[0].optimize = 2
glass_I[0].position = [1.8600000143051147, 1.7599999904632568, 0.8450000286102295]
glass_I[0].rotation = [0, 0, 0.022791679897236877]
glass_I[0].optimize = 2
artwork_G[0].position = [5.300000190734863, 4.9885125160217285, 0.574999988079071]
artwork_G[0].rotation = [0, 0, -1.5682554107885098]
artwork_G[0].optimize = 2
candle_L[0].position = [2.509999990463257, 4.829999923706055, 1.4850000143051147]
candle_L[0].rotation = [0, 0, 0.002540838557857311]
candle_L[0].optimize = 2
bar[0].position = [0.5162988305091858, 2.700000047683716, 0.5249999761581421]
bar[0].rotation = [0, 0, 0.1395028617679359]
bar[0].optimize = 2
glass_G[0].position = [2.180000066757202, 1.5399999618530273, 0.8450000286102295]
glass_G[0].rotation = [0, 0, 0.022791679897236877]
glass_G[0].optimize = 2
glassbar_I[0].position = [0.5299999713897705, 2.569999933242798, 1.1349999904632568]
glassbar_I[0].rotation = [0, 0, 0.022791645292255164]
glassbar_I[0].optimize = 2
candle_K[0].position = [2.3499999046325684, 4.829999923706055, 1.4700000286102295]
candle_K[0].rotation = [0, 0, 0.002540838557857311]
candle_K[0].optimize = 2
artwork_F[0].position = [4.349999904632568, 4.9885125160217285, 0.550000011920929]
artwork_F[0].rotation = [0, 0, -1.568255411710683]
artwork_F[0].optimize = 2
plate_E[0].position = [3.930000066757202, 2.819999933242798, 0.7649999856948853]
plate_E[0].rotation = [0, 0, 0.022791605554272402]
plate_E[0].optimize = 2
shaker_C[0].position = [4.550000190734863, 4.255000114440918, 1.034999966621399]
shaker_C[0].rotation = [0, 0, 0.022791456869282706]
shaker_C[0].optimize = 2
lamp_B[0].position = [4.150000095367432, 3.3499999046325684, 1.125]
lamp_B[0].rotation = [0, 0, 0.00942477746072377]
lamp_B[0].optimize = 2
fern[0].position = [5.579999923706055, 3.7200000286102295, 0.38999998569488525]
fern[0].rotation = [0, 0, 2.8892180479317573]
fern[0].optimize = 2
glass_table_D[0].position = [2.3399999141693115, 0.7200000286102295, 0.8149999976158142]
glass_table_D[0].rotation = [0, 0, 0.022791679897236877]
glass_table_D[0].optimize = 2
bottle_H[0].position = [4.550000190734863, 4.514999866485596, 1.0499999523162842]
bottle_H[0].rotation = [0, 0, 0.022791456869282706]
bottle_H[0].optimize = 2
bottle_F[0].position = [3.859999895095825, 3.549999952316284, 0.8899999856948853]
bottle_F[0].rotation = [0, 0, 0.022791605554272402]
bottle_F[0].optimize = 2
chairwood_A[0].position = [1.3799999952316284, 1.7999999523162842, 0.4300000071525574]
chairwood_A[0].rotation = [0, 0, 0.00942477746072377]
chairwood_A[0].optimize = 2
bottle_L[0].position = [4.550000190734863, 4.775000095367432, 1.0099999904632568]
bottle_L[0].rotation = [0, 0, 0.022791456869282706]
bottle_L[0].optimize = 2
cabinet[0].position = [2.75, 4.722609519958496, 0.675000011920929]
cabinet[0].rotation = [0, 0, -1.4935735837185398]
cabinet[0].optimize = 2
artwork_H[0].position = [0.011367498897016048, 0.550000011920929, 0.550000011920929]
artwork_H[0].rotation = [0, 0, 0.0025409160063866866]
artwork_H[0].optimize = 2
glasstable_B[0].position = [2.0199999809265137, 1.1399999856948853, 0.8100000023841858]
glasstable_B[0].rotation = [0, 0, 0.022791679897236877]
glasstable_B[0].optimize = 2
book_D[0].position = [1.2100000381469727, 4.690000057220459, 0.9399999976158142]
book_D[0].rotation = [0, 0, 0.002540838557857311]
book_D[0].optimize = 2
candle_F[0].position = [4.400000095367432, 3.549999952316284, 0.8700000047683716]
candle_F[0].rotation = [0, 0, 0.022791605554272402]
candle_F[0].optimize = 2
bottle_C[0].position = [2.3399999141693115, 1.7599999904632568, 0.8650000095367432]
bottle_C[0].rotation = [0, 0, 0.022791679897236877]
bottle_C[0].optimize = 2
glassbar_A[0].position = [0.2687683701515198, 2.0650076866149902, 1.1299999952316284]
glassbar_A[0].rotation = [0, 0, 0.022791645292255164]
glassbar_A[0].optimize = 2
artwork_B[0].position = [2.450000047683716, 0.011367769911885262, 0.5]
artwork_B[0].rotation = [0, 0, 1.5733372440233822]
artwork_B[0].optimize = 2
plate_D[0].position = [2.369999885559082, 1.9900000095367432, 0.7649999856948853]
plate_D[0].rotation = [0, 0, -3.118800973692556]
plate_D[0].optimize = 2
bottle_G[0].position = [4.75, 4.385000228881836, 1.0099999904632568]
bottle_G[0].rotation = [0, 0, 0.022791456869282706]
bottle_G[0].optimize = 2

