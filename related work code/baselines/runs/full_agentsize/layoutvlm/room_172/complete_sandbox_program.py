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
    Wall(corner1=[5.20, 0.00, 0.00], corner2=[5.20, 4.30, 0.00]),
    Wall(corner1=[5.20, 4.30, 0.00], corner2=[0.00, 4.30, 0.00]),
    Wall(corner1=[0.00, 4.30, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[5.20, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
artworkwall_A = Assets(description="A single piece of thin and upright Rococo style artwork, rectangular canvas with pastel rose background, gilded ornamental frame and a central cherub motif", size=[0.05, 0.75, 1.00], placements=[AssetInstance() for _ in range(1)])
magazine_A = Assets(description="A Rococo style magazine with embossed pastel cover, rectangular shape, decorative borders and soft color palette", size=[0.30, 0.23, 0.01], placements=[AssetInstance() for _ in range(1)])
vase_console_A = Assets(description="A Rococo style vase with a curvaceous silhouette, fluted body, pastel glaze and gold accent, cylindrical with a wide mouth", size=[0.24, 0.24, 0.45], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="A Rococo style book with ornate gold leaf detailing, rectangular shape, pastel cover, and a slightly curved spine that adds a decorative flourish.", size=[0.31, 0.24, 0.05], placements=[AssetInstance() for _ in range(1)])
plant_A = Assets(description="A small floor plant with light pastel foliage, compact rounded pot, delicate leaves and a soft pastel hue", size=[0.45, 0.45, 0.65], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="A curved pastel armchair with playful ornamentation, slender legs and a slightly reclined back, adorned with delicate gilded accents", size=[0.85, 0.82, 0.92], placements=[AssetInstance() for _ in range(1)])
booktable_A = Assets(description="A Rococo style book with ornate gilded edges, a rectangular shape, pastel cover, and delicate curved pages", size=[0.32, 0.25, 0.05], placements=[AssetInstance() for _ in range(1)])
couch = Assets(description="A Rococo sofa with light pastel upholstery, featuring intricate curves and gold stucco trim, low‑slung and elegant with a gently rounded silhouette", size=[0.95, 2.25, 0.90], placements=[AssetInstance() for _ in range(1)])
magazinetable_A = Assets(description="A Rococo style magazine with elaborate floral patterns, rectangular shape, glossy pages and thin profile", size=[0.31, 0.24, 0.01], placements=[AssetInstance() for _ in range(1)])
vase_sideboard = Assets(description="A Rococo style vase with a curvaceous silhouette, fluted body, pastel glaze and gold accent, cylindrical with a wide mouth", size=[0.23, 0.23, 0.43], placements=[AssetInstance() for _ in range(1)])
bookshelfbook_A = Assets(description="A Rococo style book with a slim rectangular profile, pastel teal cover, intricate gold filigree edging and a slightly raised title band", size=[0.04, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
vasefloor_A = Assets(description="A Rococo style ceramic vase with a curvaceous silhouette, pastel pink glaze and intricate scrollwork", size=[0.42, 0.42, 0.78], placements=[AssetInstance() for _ in range(1)])
mirror_A = Assets(description="A single piece of thin and upright mirror with an ornate Rococo frame, pastel ivory finish, gilded scrollwork and a slightly convex surface", size=[0.08, 0.85, 1.20], placements=[AssetInstance() for _ in range(1)])
candle_A = Assets(description="A Rococo style candle in a slender cylindrical holder, ivory wax, decorative carved base, soft glowing finish", size=[0.13, 0.13, 0.36], placements=[AssetInstance() for _ in range(1)])
plantfloor_A = Assets(description="A light pastel plant with a rounded pot, soft mint green foliage, and a smooth curved leaf arrangement", size=[0.55, 0.55, 0.85], placements=[AssetInstance() for _ in range(1)])
vasefloor_B = Assets(description="A Rococo style ceramic vase with a curvaceous silhouette, pastel pink glaze and intricate scrollwork", size=[0.42, 0.42, 0.78], placements=[AssetInstance() for _ in range(1)])
plantfloor_B = Assets(description="A light pastel plant with a rounded pot, soft mint green foliage, and a smooth curved leaf arrangement", size=[0.55, 0.55, 0.85], placements=[AssetInstance() for _ in range(1)])
artwork_A = Assets(description="A single piece of thin and upright artwork with an ornate Rococo frame, pastel watercolor scene, and a subtle gilded border.", size=[0.05, 0.65, 0.85], placements=[AssetInstance() for _ in range(1)])
sideboard = Assets(description="A low sideboard with gold‑trimmed edges, rectangular body, smooth surface and subtle Rococo carvings, finished in a muted pastel hue", size=[0.48, 1.80, 0.82], placements=[AssetInstance() for _ in range(1)])
vasefloor_C = Assets(description="A Rococo style vase, short squat shape, pastel yellow ceramic with a tiny gold fleur‑de‑lis motif", size=[0.32, 0.32, 0.38], placements=[AssetInstance() for _ in range(1)])
vase_floor_A = Assets(description="A Rococo style floor vase with a broad, rounded base, pastel teal glaze, and a sculpted cherub motif wrapping around its middle.", size=[0.55, 0.55, 0.90], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="A curved pastel armchair with playful ornamentation, slender legs and a slightly reclined back, adorned with delicate gilded accents", size=[0.85, 0.82, 0.92], placements=[AssetInstance() for _ in range(1)])
book_console = Assets(description="A Rococo style book with a petite rectangular shape, pastel lavender cover, and a subtle gold‑stamped title.", size=[0.24, 0.18, 0.04], placements=[AssetInstance() for _ in range(1)])
plant_B = Assets(description="A large floor plant in a pastel‑colored pot, tall leafy stems, rounded foliage, pot with a smooth matte finish and a decorative embossed pattern", size=[0.85, 0.85, 1.65], placements=[AssetInstance() for _ in range(1)])
vasefloor_D = Assets(description="A Rococo style vase, short squat shape, pastel yellow ceramic with a tiny gold fleur‑de‑lis motif", size=[0.32, 0.32, 0.38], placements=[AssetInstance() for _ in range(1)])
artwork_B = Assets(description="A single piece of thin and upright artwork in Rococo style, pastel watercolor scene, gilded border, delicate brushstroke details and a smooth flat surface", size=[0.05, 0.70, 0.90], placements=[AssetInstance() for _ in range(1)])
console = Assets(description="A narrow console table with a sleek rectangular top, slender legs, and a subtle pastel finish, minimalist yet refined", size=[0.38, 1.35, 0.82], placements=[AssetInstance() for _ in range(1)])
book_table_A = Assets(description="A Rococo style book with ornate gilded edges, rectangular shape, pastel cover, delicate filigree detailing", size=[0.32, 0.25, 0.05], placements=[AssetInstance() for _ in range(1)])
artwork_C = Assets(description="A single piece of thin and upright pastel artwork, rectangular canvas with soft pastel palette and subtle brushstrokes", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
magazinetable_B = Assets(description="A Rococo style magazine with elaborate floral patterns, rectangular shape, glossy pages and thin profile", size=[0.31, 0.24, 0.01], placements=[AssetInstance() for _ in range(1)])
floorplant_A = Assets(description="A small floor plant in a pastel pastel pastel pot, slender stem with a few soft green leaves, Rococo decorative accents", size=[0.35, 0.35, 0.75], placements=[AssetInstance() for _ in range(1)])
mirror_B = Assets(description="A single piece of thin and upright ornate mirror with a gilded gold frame, baroque curves and a polished reflective surface", size=[0.09, 0.95, 1.35], placements=[AssetInstance() for _ in range(1)])
floorbook_A = Assets(description="A Rococo style book with a decorative cover, rectangular shape, pastel hue and subtle gold filigree", size=[0.22, 0.28, 0.05], placements=[AssetInstance() for _ in range(1)])
plantfloor_C = Assets(description="A small pastel‑hued ornamental plant in a delicate pot, rounded foliage and compact form", size=[0.38, 0.38, 0.58], placements=[AssetInstance() for _ in range(1)])
mirror_C = Assets(description="A single piece of thin and upright Rococo style mirror with a gilded ornate frame, oval shape", size=[0.07, 0.75, 1.05], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="A glass coffee table with gold accents, rectangular top with beveled edges and slender gold‑finished legs, transparent and sleek", size=[0.70, 1.25, 0.43], placements=[AssetInstance() for _ in range(1)])
bookshelfbook_B = Assets(description="A Rococo style book with an elaborate embossed cover, rectangular shape, soft ivory colour and delicate scroll detailing", size=[0.05, 0.19, 0.26], placements=[AssetInstance() for _ in range(1)])
magazinetable_C = Assets(description="A Rococo style magazine with a slim rectangular form, pastel pink cover, gold filigree trim, and a slightly ruffled edge", size=[0.30, 0.23, 0.01], placements=[AssetInstance() for _ in range(1)])
bookshelf = Assets(description="A tall wooden bookshelf with Rococo detailing, narrow rectangular frame, multiple shelves, dark wood grain with gold‑toned decorative motifs", size=[0.38, 1.10, 2.10], placements=[AssetInstance() for _ in range(1)])
artworkwall_B = Assets(description="A single piece of thin and upright Rococo style artwork, rectangular canvas with pastel rose background, gilded ornamental frame and a central cherub motif", size=[0.05, 0.75, 1.00], placements=[AssetInstance() for _ in range(1)])
book_table_B = Assets(description="A Rococo style book with ornate gilded edges, rectangular shape, pastel cover, delicate filigree detailing", size=[0.32, 0.25, 0.05], placements=[AssetInstance() for _ in range(1)])
mirror_D = Assets(description="A single piece of thin and upright mirror with a Rococo carved wooden frame, ivory finish, and delicate scrollwork at the corners.", size=[0.08, 0.80, 1.15], placements=[AssetInstance() for _ in range(1)])
sideboardcandle_A = Assets(description="A Rococo style candle holder, slender cylindrical glass with pastel pink tint and a tiny gold filigree band", size=[0.10, 0.10, 0.30], placements=[AssetInstance() for _ in range(1)])
vase_console_B = Assets(description="A Rococo style vase featuring a short, squat body, ivory porcelain finish, and a delicate hand‑painted floral band.", size=[0.28, 0.28, 0.32], placements=[AssetInstance() for _ in range(1)])
floorbook_B = Assets(description="A Rococo style book with a decorative cover, rectangular shape, pastel hue and subtle gold filigree", size=[0.22, 0.28, 0.05], placements=[AssetInstance() for _ in range(1)])
plant_floor_A = Assets(description="A light pastel Rococo style floor plant with a slender tall stem, pastel pink leaves, and a decorative gilt pot at its base.", size=[0.50, 0.50, 1.35], placements=[AssetInstance() for _ in range(1)])
plantfloor_D = Assets(description="A small pastel‑hued ornamental plant in a delicate pot, rounded foliage and compact form", size=[0.38, 0.38, 0.58], placements=[AssetInstance() for _ in range(1)])
tv = Assets(description="A single piece of thin and upright TV screen with Rococo style gilt frame, pastel ivory finish and delicate scroll detailing", size=[0.09, 1.35, 0.82], placements=[AssetInstance() for _ in range(1)])
floorlamp = Assets(description="A Rococo style floor lamp, tall and slender with a curved brass base, pastel white shade and ornamental scrolls along the pole", size=[0.48, 0.48, 1.70], placements=[AssetInstance() for _ in range(1)])
plant_C = Assets(description="A large floor plant in a pastel‑colored pot, tall leafy stems, rounded foliage, pot with a smooth matte finish and a decorative embossed pattern", size=[0.85, 0.85, 1.65], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="A Rococo style book with ornate gilded edges, rectangular shape, pastel cover, delicate filigree detailing", size=[0.05, 0.20, 0.27], placements=[AssetInstance() for _ in range(1)])
candle_B = Assets(description="A Rococo style candle in a slender cylindrical holder, ivory wax, decorative carved base, soft glowing finish", size=[0.13, 0.13, 0.36], placements=[AssetInstance() for _ in range(1)])
magazine_B = Assets(description="A Rococo style magazine with embossed pastel cover, rectangular shape, decorative borders and soft color palette", size=[0.30, 0.23, 0.01], placements=[AssetInstance() for _ in range(1)])
magazine_console = Assets(description="A Rococo style magazine with a glossy pastel cover, rectangular shape, and decorative gilt border; one copy is open, the other closed.", size=[0.32, 0.48, 0.03], placements=[AssetInstance() for _ in range(1)])
magazine_C = Assets(description="A Rococo style magazine with a glossy cover, rectangular shape, pastel hue, and a raised embossed title; one copy is open showing pages, the other is closed.", size=[0.32, 0.48, 0.03], placements=[AssetInstance() for _ in range(1)])
plantfloor_E = Assets(description="A Rococo style floor plant with a slender pastel green pot, delicate foliage and a tiny gold accent band around the base", size=[0.42, 0.42, 0.95], placements=[AssetInstance() for _ in range(1)])
plant_floor_B = Assets(description="A light pastel Rococo style floor plant with a slender tall stem, pastel pink leaves, and a decorative gilt pot at its base.", size=[0.50, 0.50, 1.35], placements=[AssetInstance() for _ in range(1)])
artwork_D = Assets(description="A single piece of thin and upright artwork in Rococo style, pastel watercolor scene, gilded border, delicate brushstroke details and a smooth flat surface", size=[0.05, 0.70, 0.90], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="A tall floor lamp with a gold base, slender cylindrical shaft, and a soft fabric shade, elegant and elongated", size=[0.46, 0.46, 1.72], placements=[AssetInstance() for _ in range(1)])
booktable_B = Assets(description="A Rococo style book with ornate gilded edges, a rectangular shape, pastel cover, and delicate curved pages", size=[0.32, 0.25, 0.05], placements=[AssetInstance() for _ in range(1)])
plant_D = Assets(description="A small floor plant with light pastel foliage, compact rounded pot, delicate leaves and a soft pastel hue", size=[0.45, 0.45, 0.65], placements=[AssetInstance() for _ in range(1)])
vase_floor_B = Assets(description="A Rococo style floor vase with a broad, rounded base, pastel teal glaze, and a sculpted cherub motif wrapping around its middle.", size=[0.55, 0.55, 0.90], placements=[AssetInstance() for _ in range(1)])
sideboardcandle_B = Assets(description="A Rococo style candle holder, slender cylindrical glass with pastel pink tint and a tiny gold filigree band", size=[0.10, 0.10, 0.30], placements=[AssetInstance() for _ in range(1)])
vase_table = Assets(description="A Rococo style vase with a curvaceous silhouette, fluted body, pastel glaze and gold accent, cylindrical with a wide mouth", size=[0.24, 0.24, 0.45], placements=[AssetInstance() for _ in range(1)])
book_sideboard = Assets(description="A Rococo style book with ornate gilded edges, rectangular shape, pastel cover, delicate filigree detailing", size=[0.32, 0.25, 0.05], placements=[AssetInstance() for _ in range(1)])
artwork_E = Assets(description="A single piece of thin and upright Rococo style artwork featuring swirling pastel motifs, rectangular frame and delicate brushwork", size=[0.05, 0.65, 0.85], placements=[AssetInstance() for _ in range(1)])
magazine_D = Assets(description="A Rococo style magazine with embossed pastel cover, rectangular shape, decorative borders and soft color palette", size=[0.30, 0.23, 0.01], placements=[AssetInstance() for _ in range(1)])
floorplant_B = Assets(description="A small floor plant in a pastel pastel pastel pot, slender stem with a few soft green leaves, Rococo decorative accents", size=[0.35, 0.35, 0.75], placements=[AssetInstance() for _ in range(1)])
artwork_F = Assets(description="A single piece of thin and upright Rococo style artwork featuring swirling pastel motifs, rectangular frame and delicate brushwork", size=[0.05, 0.65, 0.85], placements=[AssetInstance() for _ in range(1)])
artwork_G = Assets(description="A single piece of thin and upright pastel artwork, rectangular canvas with soft pastel palette and subtle brushstrokes", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
consolevase = Assets(description="A small Rococo style vase, squat and rounded, pastel yellow glaze with a single gold leaf motif", size=[0.26, 0.26, 0.30], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="A tall floor lamp with a gold base, slender cylindrical shaft, and a soft fabric shade, elegant and elongated", size=[0.46, 0.46, 1.72], placements=[AssetInstance() for _ in range(1)])

artworkwall_A[0].instance_id = 'artworkwall_A_0'
magazine_A[0].instance_id = 'magazine_A_0'
vase_console_A[0].instance_id = 'vase_console_A_0'
book_A[0].instance_id = 'book_A_0'
plant_A[0].instance_id = 'plant_A_0'
chair_A[0].instance_id = 'chair_A_0'
booktable_A[0].instance_id = 'booktable_A_0'
couch[0].instance_id = 'couch_0'
magazinetable_A[0].instance_id = 'magazinetable_A_0'
vase_sideboard[0].instance_id = 'vase_sideboard_0'
bookshelfbook_A[0].instance_id = 'bookshelfbook_A_0'
vasefloor_A[0].instance_id = 'vasefloor_A_0'
mirror_A[0].instance_id = 'mirror_A_0'
candle_A[0].instance_id = 'candle_A_0'
plantfloor_A[0].instance_id = 'plantfloor_A_0'
vasefloor_B[0].instance_id = 'vasefloor_B_0'
plantfloor_B[0].instance_id = 'plantfloor_B_0'
artwork_A[0].instance_id = 'artwork_A_0'
sideboard[0].instance_id = 'sideboard_0'
vasefloor_C[0].instance_id = 'vasefloor_C_0'
vase_floor_A[0].instance_id = 'vase_floor_A_0'
chair_B[0].instance_id = 'chair_B_0'
book_console[0].instance_id = 'book_console_0'
plant_B[0].instance_id = 'plant_B_0'
vasefloor_D[0].instance_id = 'vasefloor_D_0'
artwork_B[0].instance_id = 'artwork_B_0'
console[0].instance_id = 'console_0'
book_table_A[0].instance_id = 'book_table_A_0'
artwork_C[0].instance_id = 'artwork_C_0'
magazinetable_B[0].instance_id = 'magazinetable_B_0'
floorplant_A[0].instance_id = 'floorplant_A_0'
mirror_B[0].instance_id = 'mirror_B_0'
floorbook_A[0].instance_id = 'floorbook_A_0'
plantfloor_C[0].instance_id = 'plantfloor_C_0'
mirror_C[0].instance_id = 'mirror_C_0'
table[0].instance_id = 'table_0'
bookshelfbook_B[0].instance_id = 'bookshelfbook_B_0'
magazinetable_C[0].instance_id = 'magazinetable_C_0'
bookshelf[0].instance_id = 'bookshelf_0'
artworkwall_B[0].instance_id = 'artworkwall_B_0'
book_table_B[0].instance_id = 'book_table_B_0'
mirror_D[0].instance_id = 'mirror_D_0'
sideboardcandle_A[0].instance_id = 'sideboardcandle_A_0'
vase_console_B[0].instance_id = 'vase_console_B_0'
floorbook_B[0].instance_id = 'floorbook_B_0'
plant_floor_A[0].instance_id = 'plant_floor_A_0'
plantfloor_D[0].instance_id = 'plantfloor_D_0'
tv[0].instance_id = 'tv_0'
floorlamp[0].instance_id = 'floorlamp_0'
plant_C[0].instance_id = 'plant_C_0'
book_B[0].instance_id = 'book_B_0'
candle_B[0].instance_id = 'candle_B_0'
magazine_B[0].instance_id = 'magazine_B_0'
magazine_console[0].instance_id = 'magazine_console_0'
magazine_C[0].instance_id = 'magazine_C_0'
plantfloor_E[0].instance_id = 'plantfloor_E_0'
plant_floor_B[0].instance_id = 'plant_floor_B_0'
artwork_D[0].instance_id = 'artwork_D_0'
lamp_A[0].instance_id = 'lamp_A_0'
booktable_B[0].instance_id = 'booktable_B_0'
plant_D[0].instance_id = 'plant_D_0'
vase_floor_B[0].instance_id = 'vase_floor_B_0'
sideboardcandle_B[0].instance_id = 'sideboardcandle_B_0'
vase_table[0].instance_id = 'vase_table_0'
book_sideboard[0].instance_id = 'book_sideboard_0'
artwork_E[0].instance_id = 'artwork_E_0'
magazine_D[0].instance_id = 'magazine_D_0'
floorplant_B[0].instance_id = 'floorplant_B_0'
artwork_F[0].instance_id = 'artwork_F_0'
artwork_G[0].instance_id = 'artwork_G_0'
consolevase[0].instance_id = 'consolevase_0'
lamp_B[0].instance_id = 'lamp_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

artworkwall_A[0].position = [4.405905328521667, 1.667640424652859, 0.5]
artworkwall_A[0].rotation = [0, 0, 0]
magazine_A[0].position = [4.019839931376153, 3.164859709757183, 0.005]
magazine_A[0].rotation = [0, 0, 0]
vase_console_A[0].position = [0.19595309606936265, 4.289943532355764, 0.225]
vase_console_A[0].rotation = [0, 0, 0]
book_A[0].position = [0.9611728843450481, 3.1278434694329507, 0.025]
book_A[0].rotation = [0, 0, 0]
plant_A[0].position = [0.04052492383523454, 1.8365633233649215, 0.325]
plant_A[0].rotation = [0, 0, 0]
chair_A[0].position = [0.35546389157623415, 3.7471013621917, 0.46]
chair_A[0].rotation = [0, 0, 0]
booktable_A[0].position = [4.757734821638128, 0.427439648681568, 0.025]
booktable_A[0].rotation = [0, 0, 0]
couch[0].position = [1.2622169747051089, 0.3684647096144779, 0.45]
couch[0].rotation = [0, 0, 0]
magazinetable_A[0].position = [1.963895043897436, 2.9279103878980166, 0.005]
magazinetable_A[0].rotation = [0, 0, 0]
vase_sideboard[0].position = [3.721682144388465, 3.9719675496546767, 0.215]
vase_sideboard[0].rotation = [0, 0, 0]
bookshelfbook_A[0].position = [3.279421302385065, 0.0443894988879483, 0.125]
bookshelfbook_A[0].rotation = [0, 0, 0]
vasefloor_A[0].position = [2.458224737773603, 1.0264328633514739, 0.39]
vasefloor_A[0].rotation = [0, 0, 0]
mirror_A[0].position = [4.9771927581656294, 0.9120112804636675, 0.6]
mirror_A[0].rotation = [0, 0, 0]
candle_A[0].position = [3.3804200087533762, 3.284983976531604, 0.18]
candle_A[0].rotation = [0, 0, 0]
plantfloor_A[0].position = [3.2954863415276563, 0.6895444333837212, 0.425]
plantfloor_A[0].rotation = [0, 0, 0]
vasefloor_B[0].position = [2.7069892935976365, 2.5495344952296732, 0.39]
vasefloor_B[0].rotation = [0, 0, 0]
plantfloor_B[0].position = [2.400462503137705, 2.6688891756589763, 0.425]
plantfloor_B[0].rotation = [0, 0, 0]
artwork_A[0].position = [1.5905890554127486, 1.1446544045327924, 0.425]
artwork_A[0].rotation = [0, 0, 0]
sideboard[0].position = [2.069798297280307, 3.0227223600013917, 0.41]
sideboard[0].rotation = [0, 0, 0]
vasefloor_C[0].position = [3.303531299209667, 2.9982650638405346, 0.19]
vasefloor_C[0].rotation = [0, 0, 0]
vase_floor_A[0].position = [1.1869760263864968, 2.596930670963867, 0.45]
vase_floor_A[0].rotation = [0, 0, 0]
chair_B[0].position = [3.2826552972572585, 2.444728478594801, 0.46]
chair_B[0].rotation = [0, 0, 0]
book_console[0].position = [3.5825530018430687, 2.1837576541398573, 0.02]
book_console[0].rotation = [0, 0, 0]
plant_B[0].position = [2.0619303452630544, 2.1950312205218667, 0.825]
plant_B[0].rotation = [0, 0, 0]
vasefloor_D[0].position = [3.511267101589261, 0.8442807749854826, 0.19]
vasefloor_D[0].rotation = [0, 0, 0]
artwork_B[0].position = [2.8356860563398434, 3.7214728922650604, 0.45]
artwork_B[0].rotation = [0, 0, 0]
console[0].position = [3.0901367291134365, 4.091484005308777, 0.41]
console[0].rotation = [0, 0, 0]
book_table_A[0].position = [4.0792895978656665, 0.8948628732523433, 0.025]
book_table_A[0].rotation = [0, 0, 0]
artwork_C[0].position = [0.7862248621612291, 0.2188038006816008, 0.4]
artwork_C[0].rotation = [0, 0, 0]
magazinetable_B[0].position = [4.2919980586388045, 2.4104731724855797, 0.005]
magazinetable_B[0].rotation = [0, 0, 0]
floorplant_A[0].position = [3.9479177802427357, 3.9630833470750253, 0.375]
floorplant_A[0].rotation = [0, 0, 0]
mirror_B[0].position = [3.725724151587724, 0.8226508861287446, 0.675]
mirror_B[0].rotation = [0, 0, 0]
floorbook_A[0].position = [2.778285074900081, 3.557468031819216, 0.025]
floorbook_A[0].rotation = [0, 0, 0]
plantfloor_C[0].position = [4.557165212918393, 1.6601947599998605, 0.29]
plantfloor_C[0].rotation = [0, 0, 0]
mirror_C[0].position = [4.229443734922273, 1.624601512897976, 0.525]
mirror_C[0].rotation = [0, 0, 0]
table[0].position = [2.7022031770969557, 1.228033465279332, 0.215]
table[0].rotation = [0, 0, 0]
bookshelfbook_B[0].position = [1.3267350224551617, 2.7354278884460936, 0.13]
bookshelfbook_B[0].rotation = [0, 0, 0]
magazinetable_C[0].position = [2.4372020391620213, 4.201252332513964, 0.005]
magazinetable_C[0].rotation = [0, 0, 0]
bookshelf[0].position = [3.681826315030449, 2.3879101274483685, 1.05]
bookshelf[0].rotation = [0, 0, 0]
artworkwall_B[0].position = [3.758402352914769, 1.6385567871312505, 0.5]
artworkwall_B[0].rotation = [0, 0, 0]
book_table_B[0].position = [1.838020883580997, 2.8372431428067277, 0.025]
book_table_B[0].rotation = [0, 0, 0]
mirror_D[0].position = [0.1540012346947747, 0.2551170947548971, 0.575]
mirror_D[0].rotation = [0, 0, 0]
sideboardcandle_A[0].position = [2.5010850955021167, 4.063005136508307, 0.15]
sideboardcandle_A[0].rotation = [0, 0, 0]
vase_console_B[0].position = [5.188015469201698, 3.9546096843601335, 0.16]
vase_console_B[0].rotation = [0, 0, 0]
floorbook_B[0].position = [1.5009166157582952, 2.7580898272230856, 0.025]
floorbook_B[0].rotation = [0, 0, 0]
plant_floor_A[0].position = [0.7991252709639824, 3.5024379049411856, 0.675]
plant_floor_A[0].rotation = [0, 0, 0]
plantfloor_D[0].position = [2.2960938347336572, 1.7724319969597433, 0.29]
plantfloor_D[0].rotation = [0, 0, 0]
tv[0].position = [1.7387274494667255, 2.4163800138507865, 0.41]
tv[0].rotation = [0, 0, 0]
floorlamp[0].position = [5.01672143956948, 0.7202529271343249, 0.85]
floorlamp[0].rotation = [0, 0, 0]
plant_C[0].position = [3.0961971500035386, 0.5539209578837688, 0.825]
plant_C[0].rotation = [0, 0, 0]
book_B[0].position = [2.6211736633083196, 1.8472040277585668, 0.135]
book_B[0].rotation = [0, 0, 0]
candle_B[0].position = [0.7206828754662279, 2.548209258016078, 0.18]
candle_B[0].rotation = [0, 0, 0]
magazine_B[0].position = [0.11621128090888791, 2.356232552634328, 0.005]
magazine_B[0].rotation = [0, 0, 0]
magazine_console[0].position = [4.282988694217058, 2.3359578639947225, 0.015]
magazine_console[0].rotation = [0, 0, 0]
magazine_C[0].position = [0.9079813845726634, 4.2351693632955145, 0.015]
magazine_C[0].rotation = [0, 0, 0]
plantfloor_E[0].position = [0.3663399198489085, 3.6996265550968066, 0.475]
plantfloor_E[0].rotation = [0, 0, 0]
plant_floor_B[0].position = [0.6711744005305815, 2.7876100164320103, 0.675]
plant_floor_B[0].rotation = [0, 0, 0]
artwork_D[0].position = [1.6555416630766995, 1.4373910384797959, 0.45]
artwork_D[0].rotation = [0, 0, 0]
lamp_A[0].position = [4.742958778008042, 4.268219084630301, 0.86]
lamp_A[0].rotation = [0, 0, 0]
booktable_B[0].position = [2.0163734512877287, 1.2597625306755496, 0.025]
booktable_B[0].rotation = [0, 0, 0]
plant_D[0].position = [4.430548890526562, 3.8782549491571245, 0.325]
plant_D[0].rotation = [0, 0, 0]
vase_floor_B[0].position = [1.820231418652959, 2.5454043840350127, 0.45]
vase_floor_B[0].rotation = [0, 0, 0]
sideboardcandle_B[0].position = [0.7467492236770586, 1.3627499033388488, 0.15]
sideboardcandle_B[0].rotation = [0, 0, 0]
vase_table[0].position = [0.3520071437353683, 3.1129247040839925, 0.225]
vase_table[0].rotation = [0, 0, 0]
book_sideboard[0].position = [2.878115640981185, 2.4947017648537253, 0.025]
book_sideboard[0].rotation = [0, 0, 0]
artwork_E[0].position = [0.5176501647325346, 1.4421704839717935, 0.425]
artwork_E[0].rotation = [0, 0, 0]
magazine_D[0].position = [2.051474143332337, 3.3899564186925146, 0.005]
magazine_D[0].rotation = [0, 0, 0]
floorplant_B[0].position = [3.4536158186960932, 2.983863694130467, 0.375]
floorplant_B[0].rotation = [0, 0, 0]
artwork_F[0].position = [1.253048272178403, 0.8405035967889427, 0.425]
artwork_F[0].rotation = [0, 0, 0]
artwork_G[0].position = [0.4831409825514208, 2.9999572220561417, 0.4]
artwork_G[0].rotation = [0, 0, 0]
consolevase[0].position = [4.1534750377983825, 0.4649586385748519, 0.15]
consolevase[0].rotation = [0, 0, 0]
lamp_B[0].position = [3.716526527384736, 3.8172446189158515, 0.86]
lamp_B[0].rotation = [0, 0, 0]
artworkwall_A[0].position = [4.405905328521667, 1.667640424652859, 0.5]
artworkwall_A[0].rotation = [0, 0, 0]
magazine_A[0].position = [4.019839931376153, 3.164859709757183, 0.005]
magazine_A[0].rotation = [0, 0, 0]
vase_console_A[0].position = [0.19595309606936265, 4.289943532355764, 0.225]
vase_console_A[0].rotation = [0, 0, 0]
book_A[0].position = [0.9611728843450481, 3.1278434694329507, 0.025]
book_A[0].rotation = [0, 0, 0]
plant_A[0].position = [0.04052492383523454, 1.8365633233649215, 0.325]
plant_A[0].rotation = [0, 0, 0]
chair_A[0].position = [0.35546389157623415, 3.7471013621917, 0.46]
chair_A[0].rotation = [0, 0, 0]
booktable_A[0].position = [4.757734821638128, 0.427439648681568, 0.025]
booktable_A[0].rotation = [0, 0, 0]
couch[0].position = [1.2622169747051089, 0.3684647096144779, 0.45]
couch[0].rotation = [0, 0, 0]
magazinetable_A[0].position = [1.963895043897436, 2.9279103878980166, 0.005]
magazinetable_A[0].rotation = [0, 0, 0]
vase_sideboard[0].position = [3.721682144388465, 3.9719675496546767, 0.215]
vase_sideboard[0].rotation = [0, 0, 0]
bookshelfbook_A[0].position = [3.279421302385065, 0.0443894988879483, 0.125]
bookshelfbook_A[0].rotation = [0, 0, 0]
vasefloor_A[0].position = [2.458224737773603, 1.0264328633514739, 0.39]
vasefloor_A[0].rotation = [0, 0, 0]
mirror_A[0].position = [4.9771927581656294, 0.9120112804636675, 0.6]
mirror_A[0].rotation = [0, 0, 0]
candle_A[0].position = [3.3804200087533762, 3.284983976531604, 0.18]
candle_A[0].rotation = [0, 0, 0]
plantfloor_A[0].position = [3.2954863415276563, 0.6895444333837212, 0.425]
plantfloor_A[0].rotation = [0, 0, 0]
vasefloor_B[0].position = [2.7069892935976365, 2.5495344952296732, 0.39]
vasefloor_B[0].rotation = [0, 0, 0]
plantfloor_B[0].position = [2.400462503137705, 2.6688891756589763, 0.425]
plantfloor_B[0].rotation = [0, 0, 0]
artwork_A[0].position = [1.5905890554127486, 1.1446544045327924, 0.425]
artwork_A[0].rotation = [0, 0, 0]
sideboard[0].position = [2.069798297280307, 3.0227223600013917, 0.41]
sideboard[0].rotation = [0, 0, 0]
vasefloor_C[0].position = [3.303531299209667, 2.9982650638405346, 0.19]
vasefloor_C[0].rotation = [0, 0, 0]
vase_floor_A[0].position = [1.1869760263864968, 2.596930670963867, 0.45]
vase_floor_A[0].rotation = [0, 0, 0]
chair_B[0].position = [3.2826552972572585, 2.444728478594801, 0.46]
chair_B[0].rotation = [0, 0, 0]
book_console[0].position = [3.5825530018430687, 2.1837576541398573, 0.02]
book_console[0].rotation = [0, 0, 0]
plant_B[0].position = [2.0619303452630544, 2.1950312205218667, 0.825]
plant_B[0].rotation = [0, 0, 0]
vasefloor_D[0].position = [3.511267101589261, 0.8442807749854826, 0.19]
vasefloor_D[0].rotation = [0, 0, 0]
artwork_B[0].position = [2.8356860563398434, 3.7214728922650604, 0.45]
artwork_B[0].rotation = [0, 0, 0]
console[0].position = [3.0901367291134365, 4.091484005308777, 0.41]
console[0].rotation = [0, 0, 0]
book_table_A[0].position = [4.0792895978656665, 0.8948628732523433, 0.025]
book_table_A[0].rotation = [0, 0, 0]
artwork_C[0].position = [0.7862248621612291, 0.2188038006816008, 0.4]
artwork_C[0].rotation = [0, 0, 0]
magazinetable_B[0].position = [4.2919980586388045, 2.4104731724855797, 0.005]
magazinetable_B[0].rotation = [0, 0, 0]
floorplant_A[0].position = [3.9479177802427357, 3.9630833470750253, 0.375]
floorplant_A[0].rotation = [0, 0, 0]
mirror_B[0].position = [3.725724151587724, 0.8226508861287446, 0.675]
mirror_B[0].rotation = [0, 0, 0]
floorbook_A[0].position = [2.778285074900081, 3.557468031819216, 0.025]
floorbook_A[0].rotation = [0, 0, 0]
plantfloor_C[0].position = [4.557165212918393, 1.6601947599998605, 0.29]
plantfloor_C[0].rotation = [0, 0, 0]
mirror_C[0].position = [4.229443734922273, 1.624601512897976, 0.525]
mirror_C[0].rotation = [0, 0, 0]
table[0].position = [2.7022031770969557, 1.228033465279332, 0.215]
table[0].rotation = [0, 0, 0]
bookshelfbook_B[0].position = [1.3267350224551617, 2.7354278884460936, 0.13]
bookshelfbook_B[0].rotation = [0, 0, 0]
magazinetable_C[0].position = [2.4372020391620213, 4.201252332513964, 0.005]
magazinetable_C[0].rotation = [0, 0, 0]
bookshelf[0].position = [3.681826315030449, 2.3879101274483685, 1.05]
bookshelf[0].rotation = [0, 0, 0]
artworkwall_B[0].position = [3.758402352914769, 1.6385567871312505, 0.5]
artworkwall_B[0].rotation = [0, 0, 0]
book_table_B[0].position = [1.838020883580997, 2.8372431428067277, 0.025]
book_table_B[0].rotation = [0, 0, 0]
mirror_D[0].position = [0.1540012346947747, 0.2551170947548971, 0.575]
mirror_D[0].rotation = [0, 0, 0]
sideboardcandle_A[0].position = [2.5010850955021167, 4.063005136508307, 0.15]
sideboardcandle_A[0].rotation = [0, 0, 0]
vase_console_B[0].position = [5.188015469201698, 3.9546096843601335, 0.16]
vase_console_B[0].rotation = [0, 0, 0]
floorbook_B[0].position = [1.5009166157582952, 2.7580898272230856, 0.025]
floorbook_B[0].rotation = [0, 0, 0]
plant_floor_A[0].position = [0.7991252709639824, 3.5024379049411856, 0.675]
plant_floor_A[0].rotation = [0, 0, 0]
plantfloor_D[0].position = [2.2960938347336572, 1.7724319969597433, 0.29]
plantfloor_D[0].rotation = [0, 0, 0]
tv[0].position = [1.7387274494667255, 2.4163800138507865, 0.41]
tv[0].rotation = [0, 0, 0]
floorlamp[0].position = [5.01672143956948, 0.7202529271343249, 0.85]
floorlamp[0].rotation = [0, 0, 0]
plant_C[0].position = [3.0961971500035386, 0.5539209578837688, 0.825]
plant_C[0].rotation = [0, 0, 0]
book_B[0].position = [2.6211736633083196, 1.8472040277585668, 0.135]
book_B[0].rotation = [0, 0, 0]
candle_B[0].position = [0.7206828754662279, 2.548209258016078, 0.18]
candle_B[0].rotation = [0, 0, 0]
magazine_B[0].position = [0.11621128090888791, 2.356232552634328, 0.005]
magazine_B[0].rotation = [0, 0, 0]
magazine_console[0].position = [4.282988694217058, 2.3359578639947225, 0.015]
magazine_console[0].rotation = [0, 0, 0]
magazine_C[0].position = [0.9079813845726634, 4.2351693632955145, 0.015]
magazine_C[0].rotation = [0, 0, 0]
plantfloor_E[0].position = [0.3663399198489085, 3.6996265550968066, 0.475]
plantfloor_E[0].rotation = [0, 0, 0]
plant_floor_B[0].position = [0.6711744005305815, 2.7876100164320103, 0.675]
plant_floor_B[0].rotation = [0, 0, 0]
artwork_D[0].position = [1.6555416630766995, 1.4373910384797959, 0.45]
artwork_D[0].rotation = [0, 0, 0]
lamp_A[0].position = [4.742958778008042, 4.268219084630301, 0.86]
lamp_A[0].rotation = [0, 0, 0]
booktable_B[0].position = [2.0163734512877287, 1.2597625306755496, 0.025]
booktable_B[0].rotation = [0, 0, 0]
plant_D[0].position = [4.430548890526562, 3.8782549491571245, 0.325]
plant_D[0].rotation = [0, 0, 0]
vase_floor_B[0].position = [1.820231418652959, 2.5454043840350127, 0.45]
vase_floor_B[0].rotation = [0, 0, 0]
sideboardcandle_B[0].position = [0.7467492236770586, 1.3627499033388488, 0.15]
sideboardcandle_B[0].rotation = [0, 0, 0]
vase_table[0].position = [0.3520071437353683, 3.1129247040839925, 0.225]
vase_table[0].rotation = [0, 0, 0]
book_sideboard[0].position = [2.878115640981185, 2.4947017648537253, 0.025]
book_sideboard[0].rotation = [0, 0, 0]
artwork_E[0].position = [0.5176501647325346, 1.4421704839717935, 0.425]
artwork_E[0].rotation = [0, 0, 0]
magazine_D[0].position = [2.051474143332337, 3.3899564186925146, 0.005]
magazine_D[0].rotation = [0, 0, 0]
floorplant_B[0].position = [3.4536158186960932, 2.983863694130467, 0.375]
floorplant_B[0].rotation = [0, 0, 0]
artwork_F[0].position = [1.253048272178403, 0.8405035967889427, 0.425]
artwork_F[0].rotation = [0, 0, 0]
artwork_G[0].position = [0.4831409825514208, 2.9999572220561417, 0.4]
artwork_G[0].rotation = [0, 0, 0]
consolevase[0].position = [4.1534750377983825, 0.4649586385748519, 0.15]
consolevase[0].rotation = [0, 0, 0]
lamp_B[0].position = [3.716526527384736, 3.8172446189158515, 0.86]
lamp_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed anchors are given high weight so the initial functional layout is retained
# while the semantic constraints below can make small feasibility adjustments.
def _set_pose(asset_group, position, yaw):
    instance = asset_group[0]
    instance.position = list(position)
    instance.rotation = [0, 0, yaw]

    solver.distance_constraint(
        instance,
        AssetInstance(position=list(position)),
        0,
        0,
        weight=10,
    )
    solver.align_with(
        instance,
        AssetInstance(rotation=[0, 0, yaw]),
        angle=0,
    )


# ---------------------------------------------------------------------------
# Main furniture arrangement
#
# The sofa faces into the room from the left wall. The coffee table is in
# front of it, with two chairs forming a conversational group. The sideboard
# and elevated TV share the upper portion of the right wall, safely beyond
# the door opening centered at y=0.95.
# ---------------------------------------------------------------------------

_set_pose(couch, [0.475, 2.20, 0.45], radians(0))
_set_pose(table, [2.05, 2.20, 0.215], radians(0))
_set_pose(chair_A, [3.12, 3.22, 0.46], radians(-145))
_set_pose(chair_B, [3.28, 1.28, 0.46], radians(145))

_set_pose(sideboard, [4.96, 3.20, 0.41], radians(180))
_set_pose(tv, [5.155, 3.20, 1.55], radians(180))

_set_pose(console, [1.35, 0.19, 0.41], radians(90))
_set_pose(bookshelf, [2.60, 4.11, 1.05], radians(-90))

# Primary furniture-to-wall and conversational orientation constraints.
solver.against_wall(couch[0], walls[2])
solver.point_towards(couch[0], table[0])

solver.point_towards(chair_A[0], table[0])
solver.point_towards(chair_B[0], table[0])

solver.point_towards(table[0], couch[0])
solver.align_with(table[0], couch[0])

solver.against_wall(sideboard[0], walls[0])
solver.point_towards(sideboard[0], table[0])

solver.against_wall(tv[0], walls[0])
solver.point_towards(tv[0], couch[0])

solver.against_wall(console[0], walls[3])
solver.point_towards(console[0], table[0])

solver.against_wall(bookshelf[0], walls[1])
solver.point_towards(bookshelf[0], table[0])

# Maintain usable clearances around the seating group.
solver.distance_constraint(couch[0], table[0], 1.40, 1.75, weight=10)
solver.distance_constraint(chair_A[0], table[0], 1.10, 1.50, weight=10)
solver.distance_constraint(chair_B[0], table[0], 1.10, 1.50, weight=10)


# ---------------------------------------------------------------------------
# Objects arranged on the coffee table
# ---------------------------------------------------------------------------

_set_pose(booktable_A, [1.86, 1.82, 0.455], radians(0))
_set_pose(book_table_A, [2.22, 1.82, 0.455], radians(0))
_set_pose(magazinetable_A, [1.86, 2.15, 0.435], radians(0))
_set_pose(book_table_B, [2.22, 2.14, 0.455], radians(0))
_set_pose(magazinetable_B, [1.86, 2.47, 0.435], radians(0))
_set_pose(booktable_B, [2.22, 2.47, 0.455], radians(0))
_set_pose(magazinetable_C, [1.86, 2.76, 0.435], radians(0))
_set_pose(vase_table, [2.20, 2.76, 0.655], radians(0))

for _table_object in [
    booktable_A,
    book_table_A,
    magazinetable_A,
    book_table_B,
    magazinetable_B,
    booktable_B,
    magazinetable_C,
    vase_table,
]:
    solver.on_top_of(_table_object[0], table[0])
    solver.align_with(_table_object[0], table[0])


# ---------------------------------------------------------------------------
# Console-top accessories
# ---------------------------------------------------------------------------

_set_pose(vase_console_A, [0.82, 0.19, 1.045], radians(90))
_set_pose(vase_console_B, [1.16, 0.19, 0.98], radians(90))
_set_pose(consolevase, [1.50, 0.19, 0.97], radians(90))
_set_pose(book_console, [1.82, 0.19, 0.84], radians(90))

for _console_object in [
    vase_console_A,
    vase_console_B,
    consolevase,
    book_console,
]:
    solver.on_top_of(_console_object[0], console[0])
    solver.align_with(_console_object[0], console[0])


# ---------------------------------------------------------------------------
# Sideboard-top accessories
#
# In particular, book_sideboard (o0064) is explicitly placed on sideboard
# (o0018), as required.
# ---------------------------------------------------------------------------

_set_pose(vase_sideboard, [4.86, 2.48, 1.035], radians(180))
_set_pose(sideboardcandle_A, [4.86, 2.78, 0.97], radians(180))
_set_pose(sideboardcandle_B, [4.86, 3.00, 0.97], radians(180))
_set_pose(book_sideboard, [4.86, 3.27, 0.845], radians(180))
_set_pose(book_A, [4.86, 3.58, 0.845], radians(180))
_set_pose(candle_A, [4.86, 3.83, 1.00], radians(180))
_set_pose(magazine_console, [4.86, 3.98, 0.835], radians(180))

for _sideboard_object in [
    vase_sideboard,
    sideboardcandle_A,
    sideboardcandle_B,
    book_sideboard,
    book_A,
    candle_A,
    magazine_console,
]:
    solver.on_top_of(_sideboard_object[0], sideboard[0])
    solver.align_with(_sideboard_object[0], sideboard[0])

# Highest-priority semantic relation from the layout criteria.
solver.on_top_of(book_sideboard[0], sideboard[0])


# ---------------------------------------------------------------------------
# Decorative books on top of the bookshelf
# ---------------------------------------------------------------------------

_set_pose(bookshelfbook_A, [2.30, 4.11, 2.225], radians(-90))
_set_pose(bookshelfbook_B, [2.58, 4.11, 2.23], radians(-90))
_set_pose(book_B, [2.86, 4.11, 2.235], radians(-90))

for _shelf_object in [bookshelfbook_A, bookshelfbook_B, book_B]:
    solver.on_top_of(_shelf_object[0], bookshelf[0])
    solver.align_with(_shelf_object[0], bookshelf[0])


# ---------------------------------------------------------------------------
# Additional magazines, books, and candle on available surfaces
# ---------------------------------------------------------------------------

_set_pose(magazine_A, [0.98, 0.19, 0.825], radians(90))
_set_pose(magazine_B, [1.34, 0.19, 0.825], radians(90))
_set_pose(magazine_C, [4.86, 2.67, 0.835], radians(180))
_set_pose(magazine_D, [4.86, 3.76, 0.825], radians(180))
_set_pose(candle_B, [1.68, 0.19, 1.00], radians(90))

for _small_object in [magazine_A, magazine_B, candle_B]:
    solver.on_top_of(_small_object[0], console[0])
    solver.align_with(_small_object[0], console[0])

for _small_object in [magazine_C, magazine_D]:
    solver.on_top_of(_small_object[0], sideboard[0])
    solver.align_with(_small_object[0], sideboard[0])


# ---------------------------------------------------------------------------
# Floor books are intentionally kept on the floor beside the console.
# ---------------------------------------------------------------------------

_set_pose(floorbook_A, [2.19, 0.18, 0.025], radians(90))
_set_pose(floorbook_B, [2.43, 0.18, 0.025], radians(90))

solver.distance_constraint(floorbook_A[0], console[0], 0.65, 1.10)
solver.align_with(floorbook_A[0], console[0])
solver.distance_constraint(floorbook_B[0], floorbook_A[0], 0.20, 0.35)
solver.align_with(floorbook_B[0], floorbook_A[0])


# ---------------------------------------------------------------------------
# Required three-plant arrangement
#
# By asset ordering, plantfloor_E is o0055, plantfloor_B is o0016, and
# plantfloor_C is o0033. They form a straight row with plantfloor_E centered
# between the other two. The row stays below y=0.58 and to the left of the
# right-side door approach.
# ---------------------------------------------------------------------------

_set_pose(plantfloor_B, [2.90, 0.30, 0.425], radians(90))
_set_pose(plantfloor_E, [3.47, 0.30, 0.475], radians(90))
_set_pose(plantfloor_C, [4.04, 0.30, 0.29], radians(90))

solver.distance_constraint(
    plantfloor_E[0], plantfloor_B[0], 0.57, 0.57, weight=10
)
solver.distance_constraint(
    plantfloor_E[0], plantfloor_C[0], 0.57, 0.57, weight=10
)
solver.align_with(plantfloor_E[0], plantfloor_B[0])
solver.align_with(plantfloor_B[0], plantfloor_C[0])
solver.align_with(plantfloor_C[0], plantfloor_E[0])


# ---------------------------------------------------------------------------
# Remaining floor plants, vases, and lamps
#
# These occupy perimeter gaps and corners, leaving the middle circulation
# area and the full approach to the right-wall door clear.
# ---------------------------------------------------------------------------

_set_pose(plant_A, [0.32, 0.58, 0.325], radians(0))
_set_pose(vasefloor_A, [0.25, 1.12, 0.39], radians(0))
_set_pose(plantfloor_A, [0.32, 3.67, 0.425], radians(0))
_set_pose(vasefloor_B, [0.25, 4.03, 0.39], radians(0))

_set_pose(plant_B, [4.15, 3.80, 0.825], radians(180))
_set_pose(plant_C, [1.50, 3.82, 0.825], radians(-90))
_set_pose(plant_D, [0.32, 3.12, 0.325], radians(0))

_set_pose(vasefloor_C, [0.20, 1.58, 0.19], radians(0))
_set_pose(vasefloor_D, [0.20, 2.84, 0.19], radians(0))
_set_pose(vase_floor_A, [0.38, 0.20, 0.45], radians(45))
_set_pose(vase_floor_B, [4.86, 0.24, 0.45], radians(135))

_set_pose(floorplant_A, [0.23, 2.38, 0.375], radians(0))
_set_pose(floorplant_B, [4.95, 1.70, 0.375], radians(180))
_set_pose(plant_floor_A, [3.55, 4.03, 0.675], radians(-90))
_set_pose(plant_floor_B, [4.62, 4.02, 0.675], radians(-90))
_set_pose(plantfloor_D, [0.23, 1.99, 0.29], radians(0))

_set_pose(floorlamp, [0.30, 3.97, 0.85], radians(0))
_set_pose(lamp_A, [1.00, 3.99, 0.86], radians(-90))
_set_pose(lamp_B, [4.94, 2.13, 0.86], radians(180))

# Position and orientation relations to the nearest boundary or focal object.
for _left_floor_object in [
    plant_A,
    vasefloor_A,
    plantfloor_A,
    vasefloor_B,
    plant_D,
    vasefloor_C,
    vasefloor_D,
    floorplant_A,
    plantfloor_D,
    floorlamp,
]:
    solver.against_wall(_left_floor_object[0], walls[2])
    solver.point_towards(_left_floor_object[0], table[0])

for _top_floor_object in [
    plant_B,
    plant_C,
    plant_floor_A,
    plant_floor_B,
    lamp_A,
]:
    solver.against_wall(_top_floor_object[0], walls[1])
    solver.point_towards(_top_floor_object[0], table[0])

for _right_floor_object in [floorplant_B, lamp_B]:
    solver.against_wall(_right_floor_object[0], walls[0])
    solver.point_towards(_right_floor_object[0], table[0])

for _bottom_floor_object in [vase_floor_A, vase_floor_B]:
    solver.against_wall(_bottom_floor_object[0], walls[3])
    solver.point_towards(_bottom_floor_object[0], table[0])


# ---------------------------------------------------------------------------
# Wall art and mirrors
#
# Pieces are spread over all four walls. Their z positions place their
# centers at viewing height while keeping them above nearby low furniture.
# ---------------------------------------------------------------------------

# Left wall: thin dimension along x, facing into the room (+x).
_set_pose(artworkwall_A, [0.025, 0.48, 1.55], radians(0))
_set_pose(mirror_A, [0.04, 1.30, 1.65], radians(0))
_set_pose(artwork_A, [0.025, 2.08, 1.55], radians(0))
_set_pose(artwork_B, [0.025, 2.78, 1.58], radians(0))
_set_pose(mirror_B, [0.045, 3.76, 1.65], radians(0))

for _left_wall_object in [
    artworkwall_A,
    mirror_A,
    artwork_A,
    artwork_B,
    mirror_B,
]:
    solver.against_wall(_left_wall_object[0], walls[2])
    solver.point_towards(_left_wall_object[0], table[0])


# Top wall: rotated so the fronts face toward -y.
_set_pose(artwork_C, [0.42, 4.28, 1.55], radians(-90))
_set_pose(mirror_C, [1.14, 4.265, 1.62], radians(-90))
_set_pose(artworkwall_B, [1.90, 4.275, 1.58], radians(-90))
_set_pose(mirror_D, [3.58, 4.26, 1.62], radians(-90))
_set_pose(artwork_D, [4.45, 4.275, 1.57], radians(-90))

for _top_wall_object in [
    artwork_C,
    mirror_C,
    artworkwall_B,
    mirror_D,
    artwork_D,
]:
    solver.against_wall(_top_wall_object[0], walls[1])
    solver.point_towards(_top_wall_object[0], table[0])


# Bottom wall: placed to the right of the console and facing +y.
_set_pose(artwork_E, [2.72, 0.025, 1.55], radians(90))
_set_pose(artwork_F, [3.42, 0.025, 1.55], radians(90))
_set_pose(artwork_G, [4.08, 0.02, 1.52], radians(90))

for _bottom_wall_object in [artwork_E, artwork_F, artwork_G]:
    solver.against_wall(_bottom_wall_object[0], walls[3])
    solver.point_towards(_bottom_wall_object[0], table[0])

solver.constraints = []
floorplant_B[0].position = [4.9599995613098145, 1.7000000476837158, 0.375]
floorplant_B[0].rotation = [0, 0, -3.135941128728704]
floorplant_B[0].optimize = 2
plant_C[0].position = [1.5, 3.8299999237060547, 0.824999988079071]
plant_C[0].rotation = [0, 0, -1.5651448078789751]
plant_C[0].optimize = 2
candle_B[0].position = [1.6799999475479126, 0.1899999976158142, 1.0]
candle_B[0].rotation = [0, 0, 1.596760181853713]
candle_B[0].optimize = 2
sideboardcandle_B[0].position = [4.860000133514404, 3.0, 0.9700000286102295]
sideboardcandle_B[0].rotation = [0, 0, -3.1156287131154374]
sideboardcandle_B[0].optimize = 2
book_table_B[0].position = [2.2200000286102295, 2.140000104904175, 0.45500001311302185]
book_table_B[0].rotation = [0, 0, 0.025964235498795733]
book_table_B[0].optimize = 2
bookshelfbook_A[0].position = [2.299999952316284, 4.110000133514404, 2.2249999046325684]
bookshelfbook_A[0].rotation = [0, 0, -1.5448333580515814]
bookshelfbook_A[0].optimize = 2
vasefloor_B[0].position = [0.24000006914138794, 4.03000020980835, 0.38999998569488525]
vasefloor_B[0].rotation = [0, 0, 0.005651524861089261]
vasefloor_B[0].optimize = 2
plant_B[0].position = [4.150000095367432, 3.809999942779541, 0.824999988079071]
plant_B[0].rotation = [0, 0, -3.115628267597703]
plant_B[0].optimize = 2
magazinetable_C[0].position = [1.8600000143051147, 2.759999990463257, 0.4350000023841858]
magazinetable_C[0].rotation = [0, 0, 0.025964235498795733]
magazinetable_C[0].optimize = 2
console[0].position = [1.350000023841858, 0.22408650815486908, 0.4099999964237213]
console[0].rotation = [0, 0, 1.6262309032859659]
console[0].optimize = 2
tv[0].position = [5.154402732849121, 3.200000047683716, 0.4099999964237213]
tv[0].rotation = [0, 0, -3.135941139696849]
tv[0].optimize = 2
lamp_A[0].position = [1.0, 4.0, 0.8600000143051147]
lamp_A[0].rotation = [0, 0, -1.565144803778184]
lamp_A[0].optimize = 2
book_table_A[0].position = [2.2200000286102295, 1.8200000524520874, 0.45500001311302185]
book_table_A[0].rotation = [0, 0, 0.025964235498795733]
book_table_A[0].optimize = 2
plantfloor_C[0].position = [4.039999961853027, 0.30000001192092896, 0.28999999165534973]
plantfloor_C[0].rotation = [0, 0, 1.5999250480560934]
plantfloor_C[0].optimize = 2
floorlamp[0].position = [0.2900000512599945, 3.9700000286102295, 0.8500000238418579]
floorlamp[0].rotation = [0, 0, 0.005651523938900898]
floorlamp[0].optimize = 2
vasefloor_A[0].position = [0.24000006914138794, 1.1200000047683716, 0.38999998569488525]
vasefloor_A[0].rotation = [0, 0, 0.005651524861089261]
vasefloor_A[0].optimize = 2
floorbook_A[0].position = [2.190000057220459, 0.18000000715255737, 0.02500000037252903]
floorbook_A[0].rotation = [0, 0, 1.6031049103103645]
floorbook_A[0].optimize = 2
vasefloor_C[0].position = [0.19000007212162018, 1.5800000429153442, 0.1899999976158142]
vasefloor_C[0].rotation = [0, 0, 0.005651523938900898]
vasefloor_C[0].optimize = 2
vasefloor_D[0].position = [0.19000007212162018, 2.8399999141693115, 0.1899999976158142]
vasefloor_D[0].rotation = [0, 0, 0.005651523938900898]
vasefloor_D[0].optimize = 2
plantfloor_A[0].position = [0.31000006198883057, 3.6700000762939453, 0.42500001192092896]
plantfloor_A[0].rotation = [0, 0, 0.005651523938900898]
plantfloor_A[0].optimize = 2
artwork_D[0].position = [4.449999809265137, 4.273022651672363, 0.44999998807907104]
artwork_D[0].rotation = [0, 0, -1.5651448053674857]
artwork_D[0].optimize = 2
artwork_A[0].position = [0.02683633752167225, 2.0799999237060547, 0.42500001192092896]
artwork_A[0].rotation = [0, 0, 0.005651523016712536]
artwork_A[0].optimize = 2
consolevase[0].position = [1.5, 0.1899999976158142, 0.9700000286102295]
consolevase[0].rotation = [0, 0, 1.596760181853713]
consolevase[0].optimize = 2
vase_console_B[0].position = [1.159999966621399, 0.1899999976158142, 0.9800000190734863]
vase_console_B[0].rotation = [0, 0, 1.596760181853713]
vase_console_B[0].optimize = 2
floorplant_A[0].position = [0.22000004351139069, 2.380000114440918, 0.375]
floorplant_A[0].rotation = [0, 0, 0.005651524861089261]
floorplant_A[0].optimize = 2
mirror_B[0].position = [0.04768374189734459, 3.759999990463257, 0.675000011920929]
mirror_B[0].rotation = [0, 0, 0.0056515189159214085]
mirror_B[0].optimize = 2
book_B[0].position = [2.859999895095825, 4.110000133514404, 2.234999895095825]
book_B[0].rotation = [0, 0, -1.5448333580515814]
book_B[0].optimize = 2
plant_D[0].position = [0.3100000321865082, 3.119999885559082, 0.32499998807907104]
plant_D[0].rotation = [0, 0, 0.005651523938900898]
plant_D[0].optimize = 2
table[0].position = [2.049999952316284, 2.200000047683716, 0.2150000035762787]
table[0].rotation = [0, 0, 0.20661708226215783]
table[0].optimize = 2
vase_table[0].position = [2.200000047683716, 2.759999990463257, 0.6549999713897705]
vase_table[0].rotation = [0, 0, 0.025964235498795733]
vase_table[0].optimize = 2
artwork_C[0].position = [0.41999998688697815, 4.2783050537109375, 0.4000000059604645]
artwork_C[0].rotation = [0, 0, -1.565144803778184]
artwork_C[0].optimize = 2
book_A[0].position = [4.860000133514404, 3.5799999237060547, 0.8449999690055847]
book_A[0].rotation = [0, 0, -3.1156287131154374]
book_A[0].optimize = 2
sideboardcandle_A[0].position = [4.860000133514404, 2.7799999713897705, 0.9700000286102295]
sideboardcandle_A[0].rotation = [0, 0, -3.1156287131154374]
sideboardcandle_A[0].optimize = 2
plant_A[0].position = [0.3100000321865082, 0.5799999833106995, 0.32499998807907104]
plant_A[0].rotation = [0, 0, 0.005651523938900898]
plant_A[0].optimize = 2
magazine_B[0].position = [1.340000033378601, 0.1899999976158142, 0.824999988079071]
magazine_B[0].rotation = [0, 0, 1.596760181853713]
magazine_B[0].optimize = 2
vase_floor_B[0].position = [4.811139106750488, 0.3889082670211792, 0.44999998807907104]
vase_floor_B[0].rotation = [0, 0, 2.3577598895674394]
vase_floor_B[0].optimize = 2
magazine_D[0].position = [4.860000133514404, 3.759999990463257, 0.824999988079071]
magazine_D[0].rotation = [0, 0, -3.1156287131154374]
magazine_D[0].optimize = 2
mirror_D[0].position = [3.5799999237060547, 4.257740020751953, 0.574999988079071]
mirror_D[0].rotation = [0, 0, -1.5651448053674857]
mirror_D[0].optimize = 2
booktable_B[0].position = [2.2200000286102295, 2.4700000286102295, 0.45500001311302185]
booktable_B[0].rotation = [0, 0, 0.025964235498795733]
booktable_B[0].optimize = 2
vase_console_A[0].position = [0.8199999928474426, 0.1899999976158142, 1.0449999570846558]
vase_console_A[0].rotation = [0, 0, 1.596760181853713]
vase_console_A[0].optimize = 2
candle_A[0].position = [4.860000133514404, 3.8299999237060547, 1.0]
candle_A[0].rotation = [0, 0, -3.1156287131154374]
candle_A[0].optimize = 2
bookshelf[0].position = [2.5999999046325684, 4.101110458374023, 1.0499999523162842]
bookshelf[0].rotation = [0, 0, -1.546479131302505]
bookshelf[0].optimize = 2
couch[0].position = [0.49661457538604736, 2.200000047683716, 0.44999998807907104]
couch[0].rotation = [0, 0, 0.01809489430059444]
couch[0].optimize = 2
plant_floor_B[0].position = [4.619999885559082, 4.029999732971191, 0.675000011920929]
plant_floor_B[0].rotation = [0, 0, -1.5651448028559958]
plant_floor_B[0].optimize = 2
mirror_A[0].position = [0.04240124672651291, 1.2999999523162842, 0.6000000238418579]
mirror_A[0].rotation = [0, 0, 0.005651520505222603]
mirror_A[0].optimize = 2
sideboard[0].position = [4.902887344360352, 3.200000047683716, 0.4099999964237213]
sideboard[0].rotation = [0, 0, -3.076820903917585]
sideboard[0].optimize = 2
booktable_A[0].position = [1.8600000143051147, 1.8200000524520874, 0.45500001311302185]
booktable_A[0].rotation = [0, 0, 0.025964235498795733]
booktable_A[0].optimize = 2
magazine_A[0].position = [0.9800000190734863, 0.1899999976158142, 0.824999988079071]
magazine_A[0].rotation = [0, 0, 1.596760181853713]
magazine_A[0].optimize = 2
vase_floor_A[0].position = [0.3899994194507599, 0.3788607716560364, 0.44999998807907104]
vase_floor_A[0].rotation = [0, 0, 0.8152424347635157]
vase_floor_A[0].optimize = 2
magazinetable_A[0].position = [1.8600000143051147, 2.1500000953674316, 0.4350000023841858]
magazinetable_A[0].rotation = [0, 0, 0.025964235498795733]
magazinetable_A[0].optimize = 2
vase_sideboard[0].position = [4.860000133514404, 2.4800000190734863, 1.034999966621399]
vase_sideboard[0].rotation = [0, 0, -3.1156287131154374]
vase_sideboard[0].optimize = 2
artwork_G[0].position = [4.079999923706055, 0.021695129573345184, 0.4000000059604645]
artwork_G[0].rotation = [0, 0, 1.5764478498116092]
artwork_G[0].optimize = 2
magazinetable_B[0].position = [1.8600000143051147, 2.4700000286102295, 0.4350000023841858]
magazinetable_B[0].rotation = [0, 0, 0.025964235498795733]
magazinetable_B[0].optimize = 2
magazine_console[0].position = [4.860000133514404, 3.9800000190734863, 0.8349999785423279]
magazine_console[0].rotation = [0, 0, -3.1156287131154374]
magazine_console[0].optimize = 2
artworkwall_A[0].position = [0.02711891196668148, 0.47999998927116394, 0.5]
artworkwall_A[0].rotation = [0, 0, 0.005651521427410857]
artworkwall_A[0].optimize = 2
artwork_F[0].position = [3.4200000762939453, 0.02683633752167225, 0.42500001192092896]
artwork_F[0].rotation = [0, 0, 1.5764478498116092]
artwork_F[0].optimize = 2
chair_A[0].position = [3.119999885559082, 3.2200000286102295, 0.46000000834465027]
chair_A[0].rotation = [0, 0, -2.5150194519359177]
chair_A[0].optimize = 2
plantfloor_B[0].position = [2.9000000953674316, 0.30000001192092896, 0.42500001192092896]
plantfloor_B[0].rotation = [0, 0, 1.5896488853676778]
plantfloor_B[0].optimize = 2
lamp_B[0].position = [4.949999809265137, 2.130000114440918, 0.8600000143051147]
lamp_B[0].rotation = [0, 0, -3.1359411296508926]
lamp_B[0].optimize = 2
book_console[0].position = [1.8200000524520874, 0.1899999976158142, 0.8399999737739563]
book_console[0].rotation = [0, 0, 1.596760181853713]
book_console[0].optimize = 2
magazine_C[0].position = [4.860000133514404, 2.6700000762939453, 0.8349999785423279]
magazine_C[0].rotation = [0, 0, -3.1156287131154374]
magazine_C[0].optimize = 2
artworkwall_B[0].position = [1.899999976158142, 4.272881507873535, 0.5]
artworkwall_B[0].rotation = [0, 0, -1.5651448053674857]
artworkwall_B[0].optimize = 2
plantfloor_E[0].position = [3.4700000286102295, 0.30000001192092896, 0.4749999940395355]
plantfloor_E[0].rotation = [0, 0, 1.582674109418388]
plantfloor_E[0].optimize = 2
mirror_C[0].position = [1.1399999856948853, 4.262881278991699, 0.5249999761581421]
mirror_C[0].rotation = [0, 0, -1.5651448053674857]
mirror_C[0].optimize = 2
plant_floor_A[0].position = [3.549999952316284, 4.039999961853027, 0.675000011920929]
plant_floor_A[0].rotation = [0, 0, -1.5651448019338075]
plant_floor_A[0].optimize = 2
bookshelfbook_B[0].position = [2.5799999237060547, 4.110000133514404, 2.2300000190734863]
bookshelfbook_B[0].rotation = [0, 0, -1.5448333580515814]
bookshelfbook_B[0].optimize = 2
artwork_B[0].position = [0.026977624744176865, 2.7799999713897705, 0.44999998807907104]
artwork_B[0].rotation = [0, 0, 0.005651522349599111]
artwork_B[0].optimize = 2
plantfloor_D[0].position = [0.22000007331371307, 1.9900000095367432, 0.28999999165534973]
plantfloor_D[0].rotation = [0, 0, 0.005651523938900898]
plantfloor_D[0].optimize = 2
book_sideboard[0].position = [4.860000133514404, 3.2699999809265137, 0.8449999690055847]
book_sideboard[0].rotation = [0, 0, -3.1124562908244613]
book_sideboard[0].optimize = 2
chair_B[0].position = [3.2799999713897705, 1.2799999713897705, 0.46000000834465027]
chair_B[0].rotation = [0, 0, 2.546435351291427]
chair_B[0].optimize = 2
floorbook_B[0].position = [2.430000066757202, 0.18000000715255737, 0.02500000037252903]
floorbook_B[0].rotation = [0, 0, 1.596756476952191]
floorbook_B[0].optimize = 2
artwork_E[0].position = [2.7200000286102295, 0.02683633752167225, 0.42500001192092896]
artwork_E[0].rotation = [0, 0, 1.5764478498116092]
artwork_E[0].optimize = 2

