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
artworkwall_A = Assets(description="A single piece of thin and upright Rococo style artwork, rectangular canvas with pastel rose background, gilded ornamental frame and a central cherub motif", size=[0.05, 0.55, 0.75], placements=[AssetInstance() for _ in range(1)])
magazine_A = Assets(description="A Rococo style magazine with embossed pastel cover, rectangular shape, decorative borders and soft color palette", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
vase_console_A = Assets(description="A Rococo style vase with a curvaceous silhouette, fluted body, pastel glaze and gold accent, cylindrical with a wide mouth", size=[0.20, 0.20, 0.32], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="A Rococo style book with ornate gold leaf detailing, rectangular shape, pastel cover, and a slightly curved spine that adds a decorative flourish.", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
plant_A = Assets(description="A small floor plant with light pastel foliage, compact rounded pot, delicate leaves and a soft pastel hue", size=[0.28, 0.28, 0.45], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="A curved pastel armchair with playful ornamentation, slender legs and a slightly reclined back, adorned with delicate gilded accents", size=[0.82, 0.78, 0.98], placements=[AssetInstance() for _ in range(1)])
booktable_A = Assets(description="A Rococo style book with ornate gilded edges, a rectangular shape, pastel cover, and delicate curved pages", size=[0.25, 0.18, 0.03], placements=[AssetInstance() for _ in range(1)])
couch = Assets(description="A Rococo sofa with light pastel upholstery, featuring intricate curves and gold stucco trim, low‑slung and elegant with a gently rounded silhouette", size=[0.90, 2.15, 0.95], placements=[AssetInstance() for _ in range(1)])
magazinetable_A = Assets(description="A Rococo style magazine with elaborate floral patterns, rectangular shape, glossy pages and thin profile", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
vase_sideboard = Assets(description="A Rococo style vase with a curvaceous silhouette, fluted body, pastel glaze and gold accent, cylindrical with a wide mouth", size=[0.22, 0.22, 0.35], placements=[AssetInstance() for _ in range(1)])
bookshelfbook_A = Assets(description="A Rococo style book with a slim rectangular profile, pastel teal cover, intricate gold filigree edging and a slightly raised title band", size=[0.18, 0.03, 0.26], placements=[AssetInstance() for _ in range(1)])
vasefloor_A = Assets(description="A Rococo style ceramic vase with a curvaceous silhouette, pastel pink glaze and intricate scrollwork", size=[0.26, 0.26, 0.48], placements=[AssetInstance() for _ in range(1)])
mirror_A = Assets(description="A single piece of thin and upright mirror with an ornate Rococo frame, pastel ivory finish, gilded scrollwork and a slightly convex surface", size=[0.07, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
candle_A = Assets(description="A Rococo style candle in a slender cylindrical holder, ivory wax, decorative carved base, soft glowing finish", size=[0.09, 0.09, 0.26], placements=[AssetInstance() for _ in range(1)])
plantfloor_A = Assets(description="A light pastel plant with a rounded pot, soft mint green foliage, and a smooth curved leaf arrangement", size=[0.35, 0.35, 0.65], placements=[AssetInstance() for _ in range(1)])
vasefloor_B = Assets(description="A Rococo style ceramic vase with a curvaceous silhouette, pastel pink glaze and intricate scrollwork", size=[0.26, 0.26, 0.48], placements=[AssetInstance() for _ in range(1)])
plantfloor_B = Assets(description="A light pastel plant with a rounded pot, soft mint green foliage, and a smooth curved leaf arrangement", size=[0.35, 0.35, 0.65], placements=[AssetInstance() for _ in range(1)])
artwork_A = Assets(description="A single piece of thin and upright artwork with an ornate Rococo frame, pastel watercolor scene, and a subtle gilded border.", size=[0.04, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])
sideboard = Assets(description="A low sideboard with gold‑trimmed edges, rectangular body, smooth surface and subtle Rococo carvings, finished in a muted pastel hue", size=[0.42, 1.60, 0.80], placements=[AssetInstance() for _ in range(1)])
vasefloor_C = Assets(description="A Rococo style vase, short squat shape, pastel yellow ceramic with a tiny gold fleur‑de‑lis motif", size=[0.22, 0.22, 0.25], placements=[AssetInstance() for _ in range(1)])
vase_floor_A = Assets(description="A Rococo style floor vase with a broad, rounded base, pastel teal glaze, and a sculpted cherub motif wrapping around its middle.", size=[0.30, 0.30, 0.50], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="A curved pastel armchair with playful ornamentation, slender legs and a slightly reclined back, adorned with delicate gilded accents", size=[0.82, 0.78, 0.98], placements=[AssetInstance() for _ in range(1)])
book_console = Assets(description="A Rococo style book with a petite rectangular shape, pastel lavender cover, and a subtle gold‑stamped title.", size=[0.20, 0.14, 0.03], placements=[AssetInstance() for _ in range(1)])
plant_B = Assets(description="A large floor plant in a pastel‑colored pot, tall leafy stems, rounded foliage, pot with a smooth matte finish and a decorative embossed pattern", size=[0.55, 0.55, 1.40], placements=[AssetInstance() for _ in range(1)])
vasefloor_D = Assets(description="A Rococo style vase, short squat shape, pastel yellow ceramic with a tiny gold fleur‑de‑lis motif", size=[0.22, 0.22, 0.25], placements=[AssetInstance() for _ in range(1)])
artwork_B = Assets(description="A single piece of thin and upright artwork in Rococo style, pastel watercolor scene, gilded border, delicate brushstroke details and a smooth flat surface", size=[0.04, 0.40, 0.55], placements=[AssetInstance() for _ in range(1)])
console = Assets(description="A narrow console table with a sleek rectangular top, slender legs, and a subtle pastel finish, minimalist yet refined", size=[0.35, 1.20, 0.78], placements=[AssetInstance() for _ in range(1)])
book_table_A = Assets(description="A Rococo style book with ornate gilded edges, rectangular shape, pastel cover, delicate filigree detailing", size=[0.24, 0.17, 0.03], placements=[AssetInstance() for _ in range(1)])
artwork_C = Assets(description="A single piece of thin and upright pastel artwork, rectangular canvas with soft pastel palette and subtle brushstrokes", size=[0.04, 0.35, 0.50], placements=[AssetInstance() for _ in range(1)])
magazinetable_B = Assets(description="A Rococo style magazine with elaborate floral patterns, rectangular shape, glossy pages and thin profile", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
floorplant_A = Assets(description="A small floor plant in a pastel pastel pastel pot, slender stem with a few soft green leaves, Rococo decorative accents", size=[0.22, 0.22, 0.45], placements=[AssetInstance() for _ in range(1)])
mirror_B = Assets(description="A single piece of thin and upright ornate mirror with a gilded gold frame, baroque curves and a polished reflective surface", size=[0.07, 0.55, 0.80], placements=[AssetInstance() for _ in range(1)])
floorbook_A = Assets(description="A Rococo style book with a decorative cover, rectangular shape, pastel hue and subtle gold filigree", size=[0.28, 0.20, 0.04], placements=[AssetInstance() for _ in range(1)])
plantfloor_C = Assets(description="A small pastel‑hued ornamental plant in a delicate pot, rounded foliage and compact form", size=[0.25, 0.25, 0.40], placements=[AssetInstance() for _ in range(1)])
mirror_C = Assets(description="A single piece of thin and upright Rococo style mirror with a gilded ornate frame, oval shape", size=[0.06, 0.45, 0.65], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="A glass coffee table with gold accents, rectangular top with beveled edges and slender gold‑finished legs, transparent and sleek", size=[0.75, 1.30, 0.43], placements=[AssetInstance() for _ in range(1)])
bookshelfbook_B = Assets(description="A Rococo style book with an elaborate embossed cover, rectangular shape, soft ivory colour and delicate scroll detailing", size=[0.20, 0.04, 0.28], placements=[AssetInstance() for _ in range(1)])
magazinetable_C = Assets(description="A Rococo style magazine with a slim rectangular form, pastel pink cover, gold filigree trim, and a slightly ruffled edge", size=[0.27, 0.20, 0.01], placements=[AssetInstance() for _ in range(1)])
bookshelf = Assets(description="A tall wooden bookshelf with Rococo detailing, narrow rectangular frame, multiple shelves, dark wood grain with gold‑toned decorative motifs", size=[0.32, 0.75, 2.05], placements=[AssetInstance() for _ in range(1)])
artworkwall_B = Assets(description="A single piece of thin and upright Rococo style artwork, rectangular canvas with pastel rose background, gilded ornamental frame and a central cherub motif", size=[0.05, 0.55, 0.75], placements=[AssetInstance() for _ in range(1)])
book_table_B = Assets(description="A Rococo style book with ornate gilded edges, rectangular shape, pastel cover, delicate filigree detailing", size=[0.24, 0.17, 0.03], placements=[AssetInstance() for _ in range(1)])
mirror_D = Assets(description="A single piece of thin and upright mirror with a Rococo carved wooden frame, ivory finish, and delicate scrollwork at the corners.", size=[0.06, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
sideboardcandle_A = Assets(description="A Rococo style candle holder, slender cylindrical glass with pastel pink tint and a tiny gold filigree band", size=[0.07, 0.07, 0.18], placements=[AssetInstance() for _ in range(1)])
vase_console_B = Assets(description="A Rococo style vase featuring a short, squat body, ivory porcelain finish, and a delicate hand‑painted floral band.", size=[0.17, 0.17, 0.18], placements=[AssetInstance() for _ in range(1)])
floorbook_B = Assets(description="A Rococo style book with a decorative cover, rectangular shape, pastel hue and subtle gold filigree", size=[0.28, 0.20, 0.04], placements=[AssetInstance() for _ in range(1)])
plant_floor_A = Assets(description="A light pastel Rococo style floor plant with a slender tall stem, pastel pink leaves, and a decorative gilt pot at its base.", size=[0.30, 0.30, 0.95], placements=[AssetInstance() for _ in range(1)])
plantfloor_D = Assets(description="A small pastel‑hued ornamental plant in a delicate pot, rounded foliage and compact form", size=[0.25, 0.25, 0.40], placements=[AssetInstance() for _ in range(1)])
tv = Assets(description="A single piece of thin and upright TV screen with Rococo style gilt frame, pastel ivory finish and delicate scroll detailing", size=[0.08, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
floorlamp = Assets(description="A Rococo style floor lamp, tall and slender with a curved brass base, pastel white shade and ornamental scrolls along the pole", size=[0.40, 0.40, 1.65], placements=[AssetInstance() for _ in range(1)])
plant_C = Assets(description="A large floor plant in a pastel‑colored pot, tall leafy stems, rounded foliage, pot with a smooth matte finish and a decorative embossed pattern", size=[0.55, 0.55, 1.40], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="A Rococo style book with ornate gilded edges, rectangular shape, pastel cover, delicate filigree detailing", size=[0.19, 0.04, 0.27], placements=[AssetInstance() for _ in range(1)])
candle_B = Assets(description="A Rococo style candle in a slender cylindrical holder, ivory wax, decorative carved base, soft glowing finish", size=[0.09, 0.09, 0.26], placements=[AssetInstance() for _ in range(1)])
magazine_B = Assets(description="A Rococo style magazine with embossed pastel cover, rectangular shape, decorative borders and soft color palette", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
magazine_console = Assets(description="A Rococo style magazine with a glossy pastel cover, rectangular shape, and decorative gilt border; one copy is open, the other closed.", size=[0.27, 0.40, 0.01], placements=[AssetInstance() for _ in range(1)])
magazine_C = Assets(description="A Rococo style magazine with a glossy cover, rectangular shape, pastel hue, and a raised embossed title; one copy is open showing pages, the other is closed.", size=[0.28, 0.42, 0.01], placements=[AssetInstance() for _ in range(1)])
plantfloor_E = Assets(description="A Rococo style floor plant with a slender pastel green pot, delicate foliage and a tiny gold accent band around the base", size=[0.25, 0.25, 0.55], placements=[AssetInstance() for _ in range(1)])
plant_floor_B = Assets(description="A light pastel Rococo style floor plant with a slender tall stem, pastel pink leaves, and a decorative gilt pot at its base.", size=[0.30, 0.30, 0.95], placements=[AssetInstance() for _ in range(1)])
artwork_D = Assets(description="A single piece of thin and upright artwork in Rococo style, pastel watercolor scene, gilded border, delicate brushstroke details and a smooth flat surface", size=[0.04, 0.40, 0.55], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="A tall floor lamp with a gold base, slender cylindrical shaft, and a soft fabric shade, elegant and elongated", size=[0.38, 0.38, 1.65], placements=[AssetInstance() for _ in range(1)])
booktable_B = Assets(description="A Rococo style book with ornate gilded edges, a rectangular shape, pastel cover, and delicate curved pages", size=[0.25, 0.18, 0.03], placements=[AssetInstance() for _ in range(1)])
plant_D = Assets(description="A small floor plant with light pastel foliage, compact rounded pot, delicate leaves and a soft pastel hue", size=[0.28, 0.28, 0.45], placements=[AssetInstance() for _ in range(1)])
vase_floor_B = Assets(description="A Rococo style floor vase with a broad, rounded base, pastel teal glaze, and a sculpted cherub motif wrapping around its middle.", size=[0.30, 0.30, 0.50], placements=[AssetInstance() for _ in range(1)])
sideboardcandle_B = Assets(description="A Rococo style candle holder, slender cylindrical glass with pastel pink tint and a tiny gold filigree band", size=[0.07, 0.07, 0.18], placements=[AssetInstance() for _ in range(1)])
vase_table = Assets(description="A Rococo style vase with a curvaceous silhouette, fluted body, pastel glaze and gold accent, cylindrical with a wide mouth", size=[0.16, 0.16, 0.25], placements=[AssetInstance() for _ in range(1)])
book_sideboard = Assets(description="A Rococo style book with ornate gilded edges, rectangular shape, pastel cover, delicate filigree detailing", size=[0.25, 0.18, 0.04], placements=[AssetInstance() for _ in range(1)])
artwork_E = Assets(description="A single piece of thin and upright Rococo style artwork featuring swirling pastel motifs, rectangular frame and delicate brushwork", size=[0.04, 0.35, 0.45], placements=[AssetInstance() for _ in range(1)])
magazine_D = Assets(description="A Rococo style magazine with embossed pastel cover, rectangular shape, decorative borders and soft color palette", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
floorplant_B = Assets(description="A small floor plant in a pastel pastel pastel pot, slender stem with a few soft green leaves, Rococo decorative accents", size=[0.22, 0.22, 0.45], placements=[AssetInstance() for _ in range(1)])
artwork_F = Assets(description="A single piece of thin and upright Rococo style artwork featuring swirling pastel motifs, rectangular frame and delicate brushwork", size=[0.04, 0.35, 0.45], placements=[AssetInstance() for _ in range(1)])
artwork_G = Assets(description="A single piece of thin and upright pastel artwork, rectangular canvas with soft pastel palette and subtle brushstrokes", size=[0.04, 0.35, 0.50], placements=[AssetInstance() for _ in range(1)])
consolevase = Assets(description="A small Rococo style vase, squat and rounded, pastel yellow glaze with a single gold leaf motif", size=[0.14, 0.14, 0.15], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="A tall floor lamp with a gold base, slender cylindrical shaft, and a soft fabric shade, elegant and elongated", size=[0.38, 0.38, 1.65], placements=[AssetInstance() for _ in range(1)])

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

artworkwall_A[0].position = [4.734096436834283, 2.205587969097218, 0.375]
artworkwall_A[0].rotation = [0, 0, 0]
magazine_A[0].position = [3.5837872597307068, 3.8776921459252147, 0.005]
magazine_A[0].rotation = [0, 0, 0]
vase_console_A[0].position = [1.885860123145486, 4.2135220579244255, 0.16]
vase_console_A[0].rotation = [0, 0, 0]
book_A[0].position = [0.3884530206425163, 0.8349178449219217, 0.0175]
book_A[0].rotation = [0, 0, 0]
plant_A[0].position = [2.2460603872742873, 1.281481007941043, 0.225]
plant_A[0].rotation = [0, 0, 0]
chair_A[0].position = [0.9725134319738687, 2.3051418572534064, 0.49]
chair_A[0].rotation = [0, 0, 0]
booktable_A[0].position = [0.9872022032116822, 0.3824682065106724, 0.015]
booktable_A[0].rotation = [0, 0, 0]
couch[0].position = [0.025525817079332082, 0.3097862550424537, 0.475]
couch[0].rotation = [0, 0, 0]
magazinetable_A[0].position = [1.0934396294350177, 2.8810828908598896, 0.004]
magazinetable_A[0].rotation = [0, 0, 0]
vase_sideboard[0].position = [1.9256878364956103, 0.7299990894669167, 0.175]
vase_sideboard[0].rotation = [0, 0, 0]
bookshelfbook_A[0].position = [3.1253540114380503, 1.8892141026372475, 0.13]
bookshelfbook_A[0].rotation = [0, 0, 0]
vasefloor_A[0].position = [1.963303966694381, 2.7744914616328793, 0.24]
vasefloor_A[0].rotation = [0, 0, 0]
mirror_A[0].position = [4.1955912798050035, 4.291947685745819, 0.425]
mirror_A[0].rotation = [0, 0, 0]
candle_A[0].position = [3.176648770319545, 1.7712017951087087, 0.13]
candle_A[0].rotation = [0, 0, 0]
plantfloor_A[0].position = [1.0002673775754582, 0.9042873269733965, 0.325]
plantfloor_A[0].rotation = [0, 0, 0]
vasefloor_B[0].position = [3.0852204232115787, 1.2881432213816275, 0.24]
vasefloor_B[0].rotation = [0, 0, 0]
plantfloor_B[0].position = [3.4852775244508187, 0.37514455697356347, 0.325]
plantfloor_B[0].rotation = [0, 0, 0]
artwork_A[0].position = [3.8691151959663213, 0.7786620380776538, 0.3]
artwork_A[0].rotation = [0, 0, 0]
sideboard[0].position = [3.509980786393331, 3.14186601417375, 0.4]
sideboard[0].rotation = [0, 0, 0]
vasefloor_C[0].position = [3.323960139072522, 2.865030967979016, 0.125]
vasefloor_C[0].rotation = [0, 0, 0]
vase_floor_A[0].position = [3.66729552165057, 2.0058535441476835, 0.25]
vase_floor_A[0].rotation = [0, 0, 0]
chair_B[0].position = [0.270771841948624, 4.245446649736423, 0.49]
chair_B[0].rotation = [0, 0, 0]
book_console[0].position = [2.8983109192315415, 4.0752990047902165, 0.0125]
book_console[0].rotation = [0, 0, 0]
plant_B[0].position = [2.1304507633707206, 1.7839425491347418, 0.7]
plant_B[0].rotation = [0, 0, 0]
vasefloor_D[0].position = [3.190815524749314, 4.223366258397121, 0.125]
vasefloor_D[0].rotation = [0, 0, 0]
artwork_B[0].position = [4.669319897400747, 1.6471384255507362, 0.275]
artwork_B[0].rotation = [0, 0, 0]
console[0].position = [2.927982074372929, 2.014121221062882, 0.39]
console[0].rotation = [0, 0, 0]
book_table_A[0].position = [3.2855722050639047, 2.2443289091775216, 0.015]
book_table_A[0].rotation = [0, 0, 0]
artwork_C[0].position = [3.8999214683677987, 2.5019306811736355, 0.25]
artwork_C[0].rotation = [0, 0, 0]
magazinetable_B[0].position = [4.863255503230648, 1.4196196016463505, 0.004]
magazinetable_B[0].rotation = [0, 0, 0]
floorplant_A[0].position = [3.2798809391181463, 1.6239863990422863, 0.225]
floorplant_A[0].rotation = [0, 0, 0]
mirror_B[0].position = [3.8787316075250695, 1.5894682669900435, 0.4]
mirror_B[0].rotation = [0, 0, 0]
floorbook_A[0].position = [0.0728734857076666, 3.654782317592062, 0.02]
floorbook_A[0].rotation = [0, 0, 0]
plantfloor_C[0].position = [1.203193478924552, 3.3741304952172593, 0.2]
plantfloor_C[0].rotation = [0, 0, 0]
mirror_C[0].position = [0.7760389475120418, 2.513920933693117, 0.325]
mirror_C[0].rotation = [0, 0, 0]
table[0].position = [5.127762855963358, 0.6434177170261198, 0.215]
table[0].rotation = [0, 0, 0]
bookshelfbook_B[0].position = [2.131369526049871, 3.0616068263050322, 0.14]
bookshelfbook_B[0].rotation = [0, 0, 0]
magazinetable_C[0].position = [2.8792493469368288, 0.6116735429088913, 0.005]
magazinetable_C[0].rotation = [0, 0, 0]
bookshelf[0].position = [1.032279525993396, 0.4842154922191768, 1.025]
bookshelf[0].rotation = [0, 0, 0]
artworkwall_B[0].position = [3.1622105220199193, 3.5961094728679286, 0.375]
artworkwall_B[0].rotation = [0, 0, 0]
book_table_B[0].position = [2.2496622308197183, 1.8708888354533453, 0.015]
book_table_B[0].rotation = [0, 0, 0]
mirror_D[0].position = [4.964792142579198, 0.399506640215269, 0.35]
mirror_D[0].rotation = [0, 0, 0]
sideboardcandle_A[0].position = [1.4447020523038832, 3.561367953708462, 0.09]
sideboardcandle_A[0].rotation = [0, 0, 0]
vase_console_B[0].position = [3.9971248652120224, 2.928973101724662, 0.09]
vase_console_B[0].rotation = [0, 0, 0]
floorbook_B[0].position = [2.271528039497624, 0.12609861801455255, 0.02]
floorbook_B[0].rotation = [0, 0, 0]
plant_floor_A[0].position = [1.2187822457176511, 0.7176055917395903, 0.475]
plant_floor_A[0].rotation = [0, 0, 0]
plantfloor_D[0].position = [2.519998203260138, 1.6408994208845387, 0.2]
plantfloor_D[0].rotation = [0, 0, 0]
tv[0].position = [2.9838871341203927, 0.38610544067731023, 0.375]
tv[0].rotation = [0, 0, 0]
floorlamp[0].position = [4.201367098357649, 1.0346900590783203, 0.825]
floorlamp[0].rotation = [0, 0, 0]
plant_C[0].position = [0.5516241040350683, 1.0513405260223803, 0.7]
plant_C[0].rotation = [0, 0, 0]
book_B[0].position = [3.1761212789998745, 2.3118571513503468, 0.135]
book_B[0].rotation = [0, 0, 0]
candle_B[0].position = [1.1607451151348247, 2.119110515265294, 0.13]
candle_B[0].rotation = [0, 0, 0]
magazine_B[0].position = [4.707965062018687, 3.1526913576781643, 0.005]
magazine_B[0].rotation = [0, 0, 0]
magazine_console[0].position = [2.3590002691016347, 0.03701067501571929, 0.0075]
magazine_console[0].rotation = [0, 0, 0]
magazine_C[0].position = [0.5464714849465301, 4.131024344645115, 0.0075]
magazine_C[0].rotation = [0, 0, 0]
plantfloor_E[0].position = [0.06267994314439505, 2.1020647317331975, 0.275]
plantfloor_E[0].rotation = [0, 0, 0]
plant_floor_B[0].position = [1.6355048486312784, 2.1249804069149754, 0.475]
plant_floor_B[0].rotation = [0, 0, 0]
artwork_D[0].position = [2.764123318081802, 3.853498702381034, 0.275]
artwork_D[0].rotation = [0, 0, 0]
lamp_A[0].position = [1.4701617619671818, 0.9790635230657798, 0.825]
lamp_A[0].rotation = [0, 0, 0]
booktable_B[0].position = [4.286225232805912, 2.022421293025878, 0.015]
booktable_B[0].rotation = [0, 0, 0]
plant_D[0].position = [0.6766502431112572, 3.7393886802150997, 0.225]
plant_D[0].rotation = [0, 0, 0]
vase_floor_B[0].position = [4.1832327739203645, 3.2859065734596555, 0.25]
vase_floor_B[0].rotation = [0, 0, 0]
sideboardcandle_B[0].position = [4.480944371625724, 1.4900829389459926, 0.09]
sideboardcandle_B[0].rotation = [0, 0, 0]
vase_table[0].position = [4.397617141371505, 3.6227309050821064, 0.125]
vase_table[0].rotation = [0, 0, 0]
book_sideboard[0].position = [4.014738040800158, 3.227224005801939, 0.0175]
book_sideboard[0].rotation = [0, 0, 0]
artwork_E[0].position = [0.31661903788461115, 0.678240587395185, 0.225]
artwork_E[0].rotation = [0, 0, 0]
magazine_D[0].position = [0.4914215024824352, 4.105536958336988, 0.005]
magazine_D[0].rotation = [0, 0, 0]
floorplant_B[0].position = [2.0234241405668203, 2.1190929541085697, 0.225]
floorplant_B[0].rotation = [0, 0, 0]
artwork_F[0].position = [5.156776276886922, 0.5959578764897838, 0.225]
artwork_F[0].rotation = [0, 0, 0]
artwork_G[0].position = [1.9127258821823416, 1.7029957114970233, 0.25]
artwork_G[0].rotation = [0, 0, 0]
consolevase[0].position = [4.672999145155096, 2.5362286669083747, 0.075]
consolevase[0].rotation = [0, 0, 0]
lamp_B[0].position = [1.0247221992614537, 0.5726099648336221, 0.825]
lamp_B[0].rotation = [0, 0, 0]
artworkwall_A[0].position = [4.734096436834283, 2.205587969097218, 0.375]
artworkwall_A[0].rotation = [0, 0, 0]
magazine_A[0].position = [3.5837872597307068, 3.8776921459252147, 0.005]
magazine_A[0].rotation = [0, 0, 0]
vase_console_A[0].position = [1.885860123145486, 4.2135220579244255, 0.16]
vase_console_A[0].rotation = [0, 0, 0]
book_A[0].position = [0.3884530206425163, 0.8349178449219217, 0.0175]
book_A[0].rotation = [0, 0, 0]
plant_A[0].position = [2.2460603872742873, 1.281481007941043, 0.225]
plant_A[0].rotation = [0, 0, 0]
chair_A[0].position = [0.9725134319738687, 2.3051418572534064, 0.49]
chair_A[0].rotation = [0, 0, 0]
booktable_A[0].position = [0.9872022032116822, 0.3824682065106724, 0.015]
booktable_A[0].rotation = [0, 0, 0]
couch[0].position = [0.025525817079332082, 0.3097862550424537, 0.475]
couch[0].rotation = [0, 0, 0]
magazinetable_A[0].position = [1.0934396294350177, 2.8810828908598896, 0.004]
magazinetable_A[0].rotation = [0, 0, 0]
vase_sideboard[0].position = [1.9256878364956103, 0.7299990894669167, 0.175]
vase_sideboard[0].rotation = [0, 0, 0]
bookshelfbook_A[0].position = [3.1253540114380503, 1.8892141026372475, 0.13]
bookshelfbook_A[0].rotation = [0, 0, 0]
vasefloor_A[0].position = [1.963303966694381, 2.7744914616328793, 0.24]
vasefloor_A[0].rotation = [0, 0, 0]
mirror_A[0].position = [4.1955912798050035, 4.291947685745819, 0.425]
mirror_A[0].rotation = [0, 0, 0]
candle_A[0].position = [3.176648770319545, 1.7712017951087087, 0.13]
candle_A[0].rotation = [0, 0, 0]
plantfloor_A[0].position = [1.0002673775754582, 0.9042873269733965, 0.325]
plantfloor_A[0].rotation = [0, 0, 0]
vasefloor_B[0].position = [3.0852204232115787, 1.2881432213816275, 0.24]
vasefloor_B[0].rotation = [0, 0, 0]
plantfloor_B[0].position = [3.4852775244508187, 0.37514455697356347, 0.325]
plantfloor_B[0].rotation = [0, 0, 0]
artwork_A[0].position = [3.8691151959663213, 0.7786620380776538, 0.3]
artwork_A[0].rotation = [0, 0, 0]
sideboard[0].position = [3.509980786393331, 3.14186601417375, 0.4]
sideboard[0].rotation = [0, 0, 0]
vasefloor_C[0].position = [3.323960139072522, 2.865030967979016, 0.125]
vasefloor_C[0].rotation = [0, 0, 0]
vase_floor_A[0].position = [3.66729552165057, 2.0058535441476835, 0.25]
vase_floor_A[0].rotation = [0, 0, 0]
chair_B[0].position = [0.270771841948624, 4.245446649736423, 0.49]
chair_B[0].rotation = [0, 0, 0]
book_console[0].position = [2.8983109192315415, 4.0752990047902165, 0.0125]
book_console[0].rotation = [0, 0, 0]
plant_B[0].position = [2.1304507633707206, 1.7839425491347418, 0.7]
plant_B[0].rotation = [0, 0, 0]
vasefloor_D[0].position = [3.190815524749314, 4.223366258397121, 0.125]
vasefloor_D[0].rotation = [0, 0, 0]
artwork_B[0].position = [4.669319897400747, 1.6471384255507362, 0.275]
artwork_B[0].rotation = [0, 0, 0]
console[0].position = [2.927982074372929, 2.014121221062882, 0.39]
console[0].rotation = [0, 0, 0]
book_table_A[0].position = [3.2855722050639047, 2.2443289091775216, 0.015]
book_table_A[0].rotation = [0, 0, 0]
artwork_C[0].position = [3.8999214683677987, 2.5019306811736355, 0.25]
artwork_C[0].rotation = [0, 0, 0]
magazinetable_B[0].position = [4.863255503230648, 1.4196196016463505, 0.004]
magazinetable_B[0].rotation = [0, 0, 0]
floorplant_A[0].position = [3.2798809391181463, 1.6239863990422863, 0.225]
floorplant_A[0].rotation = [0, 0, 0]
mirror_B[0].position = [3.8787316075250695, 1.5894682669900435, 0.4]
mirror_B[0].rotation = [0, 0, 0]
floorbook_A[0].position = [0.0728734857076666, 3.654782317592062, 0.02]
floorbook_A[0].rotation = [0, 0, 0]
plantfloor_C[0].position = [1.203193478924552, 3.3741304952172593, 0.2]
plantfloor_C[0].rotation = [0, 0, 0]
mirror_C[0].position = [0.7760389475120418, 2.513920933693117, 0.325]
mirror_C[0].rotation = [0, 0, 0]
table[0].position = [5.127762855963358, 0.6434177170261198, 0.215]
table[0].rotation = [0, 0, 0]
bookshelfbook_B[0].position = [2.131369526049871, 3.0616068263050322, 0.14]
bookshelfbook_B[0].rotation = [0, 0, 0]
magazinetable_C[0].position = [2.8792493469368288, 0.6116735429088913, 0.005]
magazinetable_C[0].rotation = [0, 0, 0]
bookshelf[0].position = [1.032279525993396, 0.4842154922191768, 1.025]
bookshelf[0].rotation = [0, 0, 0]
artworkwall_B[0].position = [3.1622105220199193, 3.5961094728679286, 0.375]
artworkwall_B[0].rotation = [0, 0, 0]
book_table_B[0].position = [2.2496622308197183, 1.8708888354533453, 0.015]
book_table_B[0].rotation = [0, 0, 0]
mirror_D[0].position = [4.964792142579198, 0.399506640215269, 0.35]
mirror_D[0].rotation = [0, 0, 0]
sideboardcandle_A[0].position = [1.4447020523038832, 3.561367953708462, 0.09]
sideboardcandle_A[0].rotation = [0, 0, 0]
vase_console_B[0].position = [3.9971248652120224, 2.928973101724662, 0.09]
vase_console_B[0].rotation = [0, 0, 0]
floorbook_B[0].position = [2.271528039497624, 0.12609861801455255, 0.02]
floorbook_B[0].rotation = [0, 0, 0]
plant_floor_A[0].position = [1.2187822457176511, 0.7176055917395903, 0.475]
plant_floor_A[0].rotation = [0, 0, 0]
plantfloor_D[0].position = [2.519998203260138, 1.6408994208845387, 0.2]
plantfloor_D[0].rotation = [0, 0, 0]
tv[0].position = [2.9838871341203927, 0.38610544067731023, 0.375]
tv[0].rotation = [0, 0, 0]
floorlamp[0].position = [4.201367098357649, 1.0346900590783203, 0.825]
floorlamp[0].rotation = [0, 0, 0]
plant_C[0].position = [0.5516241040350683, 1.0513405260223803, 0.7]
plant_C[0].rotation = [0, 0, 0]
book_B[0].position = [3.1761212789998745, 2.3118571513503468, 0.135]
book_B[0].rotation = [0, 0, 0]
candle_B[0].position = [1.1607451151348247, 2.119110515265294, 0.13]
candle_B[0].rotation = [0, 0, 0]
magazine_B[0].position = [4.707965062018687, 3.1526913576781643, 0.005]
magazine_B[0].rotation = [0, 0, 0]
magazine_console[0].position = [2.3590002691016347, 0.03701067501571929, 0.0075]
magazine_console[0].rotation = [0, 0, 0]
magazine_C[0].position = [0.5464714849465301, 4.131024344645115, 0.0075]
magazine_C[0].rotation = [0, 0, 0]
plantfloor_E[0].position = [0.06267994314439505, 2.1020647317331975, 0.275]
plantfloor_E[0].rotation = [0, 0, 0]
plant_floor_B[0].position = [1.6355048486312784, 2.1249804069149754, 0.475]
plant_floor_B[0].rotation = [0, 0, 0]
artwork_D[0].position = [2.764123318081802, 3.853498702381034, 0.275]
artwork_D[0].rotation = [0, 0, 0]
lamp_A[0].position = [1.4701617619671818, 0.9790635230657798, 0.825]
lamp_A[0].rotation = [0, 0, 0]
booktable_B[0].position = [4.286225232805912, 2.022421293025878, 0.015]
booktable_B[0].rotation = [0, 0, 0]
plant_D[0].position = [0.6766502431112572, 3.7393886802150997, 0.225]
plant_D[0].rotation = [0, 0, 0]
vase_floor_B[0].position = [4.1832327739203645, 3.2859065734596555, 0.25]
vase_floor_B[0].rotation = [0, 0, 0]
sideboardcandle_B[0].position = [4.480944371625724, 1.4900829389459926, 0.09]
sideboardcandle_B[0].rotation = [0, 0, 0]
vase_table[0].position = [4.397617141371505, 3.6227309050821064, 0.125]
vase_table[0].rotation = [0, 0, 0]
book_sideboard[0].position = [4.014738040800158, 3.227224005801939, 0.0175]
book_sideboard[0].rotation = [0, 0, 0]
artwork_E[0].position = [0.31661903788461115, 0.678240587395185, 0.225]
artwork_E[0].rotation = [0, 0, 0]
magazine_D[0].position = [0.4914215024824352, 4.105536958336988, 0.005]
magazine_D[0].rotation = [0, 0, 0]
floorplant_B[0].position = [2.0234241405668203, 2.1190929541085697, 0.225]
floorplant_B[0].rotation = [0, 0, 0]
artwork_F[0].position = [5.156776276886922, 0.5959578764897838, 0.225]
artwork_F[0].rotation = [0, 0, 0]
artwork_G[0].position = [1.9127258821823416, 1.7029957114970233, 0.25]
artwork_G[0].rotation = [0, 0, 0]
consolevase[0].position = [4.672999145155096, 2.5362286669083747, 0.075]
consolevase[0].rotation = [0, 0, 0]
lamp_B[0].position = [1.0247221992614537, 0.5726099648336221, 0.825]
lamp_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Coordinates follow the supplied boundary: 0 <= x <= 5.20, 0 <= y <= 4.30.
# The entry zone at the lower right remains clear. Fixed-point constraints
# preserve the deliberately separated positions, including wall-art heights.
def place_fixed(asset_group, xyz, yaw=0):
    instance = asset_group[0]
    instance.position = list(xyz)
    instance.rotation = [0, 0, radians(yaw)]
    solver.distance_constraint(
        instance, AssetInstance(position=list(xyz)), 0, 0, weight=10
    )
    solver.align_with(
        instance, AssetInstance(rotation=[0, 0, radians(yaw)])
    )


def place_floor(asset_group, x, y, yaw=0):
    place_fixed(asset_group, [x, y, asset_group.size[2] / 2], yaw)


def place_supported(asset_group, support_group, x, y, yaw=0):
    # Use actual bounding-box centers to compute the supporting surface.
    support_instance = support_group[0]
    z = (
        support_instance.position[2]
        + support_group.size[2] / 2
        + asset_group.size[2] / 2
    )
    solver.on_top_of(asset_group[0], support_instance)
    place_fixed(asset_group, [x, y, z], yaw)


# Main furniture: sofa faces the two armchairs across the coffee table.
# The right-hand sideboard is beyond the door's approach and swing zone.
place_floor(couch, 0.45, 2.15)
place_floor(table, 1.85, 2.15)
place_floor(chair_A, 3.05, 1.65, 180)
place_floor(chair_B, 3.05, 2.70, 180)
place_floor(sideboard, 4.99, 3.25, 180)
place_floor(console, 2.10, 0.175, 90)
place_floor(bookshelf, 0.16, 3.80)

solver.against_wall(couch[0], walls[2])
solver.against_wall(sideboard[0], walls[0])
solver.against_wall(console[0], walls[3])
solver.against_wall(bookshelf[0], walls[2])
solver.point_towards(couch[0], sideboard[0])
solver.point_towards(sideboard[0], couch[0])
solver.align_with(table[0], couch[0])
solver.align_with(chair_A[0], couch[0], angle=180)
solver.align_with(chair_B[0], couch[0], angle=180)

# Floor lighting and planting occupy the perimeter, not the entry route.
place_floor(floorlamp, 0.30, 0.40)
place_floor(lamp_A, 1.00, 0.40)
place_floor(lamp_B, 4.20, 3.95)

place_floor(plant_A, 0.18, 0.85)
place_floor(plant_D, 0.95, 0.85)
place_floor(floorplant_A, 0.55, 0.80)
place_floor(floorplant_B, 1.30, 0.40)
place_floor(plantfloor_A, 0.55, 3.65)

# o0055 (plantfloor_E) lies between o0016 (plantfloor_B)
# and o0033 (plantfloor_C), along the north planting row.
place_floor(plantfloor_B, 0.95, 3.95)
place_floor(plantfloor_E, 1.45, 3.95)
place_floor(plantfloor_C, 1.95, 3.95)
solver.distance_constraint(
    plantfloor_E[0], plantfloor_B[0], 0.50, 0.50, weight=10
)
solver.distance_constraint(
    plantfloor_E[0], plantfloor_C[0], 0.50, 0.50, weight=10
)
solver.align_with(plantfloor_E[0], plantfloor_B[0])
solver.align_with(plantfloor_C[0], plantfloor_B[0])

place_floor(plant_B, 2.60, 3.95)
place_floor(plant_C, 3.30, 3.95)
place_floor(plantfloor_D, 3.85, 3.95)
place_floor(plant_floor_A, 3.85, 2.65)
place_floor(plant_floor_B, 4.45, 2.10)

# Decorative floor vessels stay outside chair footprints and circulation.
place_floor(vasefloor_A, 3.00, 0.20)
place_floor(vasefloor_B, 3.40, 0.20)
place_floor(vasefloor_C, 3.80, 0.20)
place_floor(vase_floor_A, 0.65, 3.42)
place_floor(vasefloor_D, 1.00, 3.42)
place_floor(vase_floor_B, 4.55, 3.95)

# Console: rotated books fit within its narrow depth.
place_supported(magazine_console, console, 1.74, 0.175, 90)
place_supported(book_console, console, 2.10, 0.175, 90)
place_supported(vase_console_A, console, 2.50, 0.175)
place_supported(vase_console_B, book_console, 2.10, 0.175)
place_supported(consolevase, magazine_console, 1.74, 0.175)

# Sideboard: separate decorative clusters, with the requested book resting
# directly on the sideboard rather than on another decorative object.
place_supported(book_sideboard, sideboard, 4.99, 2.65, 180)
place_supported(vase_sideboard, sideboard, 4.99, 3.90)
place_supported(sideboardcandle_A, sideboard, 4.99, 2.90)
place_supported(sideboardcandle_B, sideboard, 4.99, 3.10)
place_supported(candle_A, sideboard, 4.99, 3.30)
place_supported(candle_B, sideboard, 4.99, 3.50)
place_supported(floorbook_A, sideboard, 4.99, 3.70)
place_supported(floorbook_B, floorbook_A, 4.99, 3.70)
solver.align_with(book_sideboard[0], sideboard[0])

# Upright volumes use the bookshelf's real upper surface; no invented shelf
# elevations or additional support assets are required.
place_supported(bookshelfbook_A, bookshelf, 0.16, 3.52)
place_supported(bookshelfbook_B, bookshelf, 0.16, 3.65)
place_supported(book_B, bookshelf, 0.16, 3.80)

# Coffee-table reading material forms four compact, nonintersecting stacks.
# Stacking accommodates all listed copies without covering the entire top.
place_supported(magazine_A, table, 1.68, 1.75)
place_supported(magazine_B, magazine_A, 1.68, 1.75)
place_supported(magazine_D, magazine_B, 1.68, 1.75)
place_supported(book_A, magazine_D, 1.68, 1.75)

place_supported(magazinetable_A, table, 2.02, 1.75)
place_supported(magazinetable_B, magazinetable_A, 2.02, 1.75)
place_supported(magazinetable_C, magazinetable_B, 2.02, 1.75)

place_supported(booktable_A, table, 1.68, 2.10)
place_supported(booktable_B, booktable_A, 1.68, 2.10)
place_supported(book_table_A, booktable_B, 1.68, 2.10)
place_supported(book_table_B, book_table_A, 1.68, 2.10)

place_supported(magazine_C, table, 2.02, 2.30)
place_supported(vase_table, table, 1.68, 2.57)

# Wall-mounted objects: wall contact is a position constraint, not a floor
# instruction. Heights explicitly keep frames above furniture and plants.
def mount_frame(asset_group, x, y, z, yaw, wall_index):
    place_fixed(asset_group, [x, y, z], yaw)
    solver.against_wall(asset_group[0], walls[wall_index])


# West wall gallery, above the sofa.
mount_frame(artworkwall_A, 0.025, 1.40, 1.95, 0, 2)
mount_frame(mirror_A, 0.035, 2.15, 1.95, 0, 2)
mount_frame(artworkwall_B, 0.025, 2.90, 1.95, 0, 2)

# North wall gallery; 270 degrees turns the thin frames toward the room.
mount_frame(artwork_A, 0.65, 4.28, 2.55, 270, 1)
mount_frame(artwork_B, 1.25, 4.28, 2.10, 270, 1)
mount_frame(artwork_C, 1.80, 4.28, 2.10, 270, 1)
mount_frame(artwork_D, 2.35, 4.28, 2.10, 270, 1)
mount_frame(artwork_E, 2.90, 4.28, 2.10, 270, 1)
mount_frame(artwork_F, 3.45, 4.28, 2.10, 270, 1)
mount_frame(artwork_G, 4.00, 4.28, 2.10, 270, 1)

# Mirrors above the console, safely above its vases and books.
mount_frame(mirror_B, 1.45, 0.035, 1.75, 90, 3)
mount_frame(mirror_C, 2.10, 0.030, 1.75, 90, 3)
mount_frame(mirror_D, 2.75, 0.030, 1.75, 90, 3)

# Wall-mounted TV faces the sofa. Its lower edge clears sideboard ornaments.
mount_frame(tv, 5.16, 3.25, 1.80, 180, 0)
solver.point_towards(tv[0], couch[0])

solver.constraints = []
artwork_E[0].position = [2.9000000953674316, 4.288697242736816, 0.22499999403953552]
artwork_E[0].rotation = [0, 0, -1.5682554071222121]
artwork_E[0].optimize = 2
floorplant_A[0].position = [0.550000011920929, 0.800000011920929, 0.22499999403953552]
floorplant_A[0].rotation = [0, 0, 0.00942477746072377]
floorplant_A[0].optimize = 2
plantfloor_E[0].position = [1.4500000476837158, 3.950000047683716, 0.2750000059604645]
plantfloor_E[0].rotation = [0, 0, 0.018852558572781168]
plantfloor_E[0].optimize = 2
table[0].position = [1.850000023841858, 2.1500000953674316, 0.2150000035762787]
table[0].rotation = [0, 0, 0.038645931883588995]
table[0].optimize = 2
plant_floor_B[0].position = [4.449999809265137, 2.0999999046325684, 0.4749999940395355]
plant_floor_B[0].rotation = [0, 0, 0.00942477746072377]
plant_floor_B[0].optimize = 2
artwork_C[0].position = [1.7999999523162842, 4.288697242736816, 0.25]
artwork_C[0].rotation = [0, 0, -1.5682554071222121]
artwork_C[0].optimize = 2
book_table_B[0].position = [1.6799999475479126, 2.0999999046325684, 0.5349999070167542]
book_table_B[0].rotation = [0, 0, 0.01256637125682779]
book_table_B[0].optimize = 2
vase_floor_B[0].position = [4.550000190734863, 3.950000047683716, 0.25]
vase_floor_B[0].rotation = [0, 0, 0.00942477746072377]
vase_floor_B[0].optimize = 2
bookshelfbook_B[0].position = [0.1599999964237213, 3.6500000953674316, 2.190000057220459]
bookshelfbook_B[0].rotation = [0, 0, 0.01256637125682779]
bookshelfbook_B[0].optimize = 2
magazine_C[0].position = [2.0199999809265137, 2.299999952316284, 0.4350000023841858]
magazine_C[0].rotation = [0, 0, 0.01256637125682779]
magazine_C[0].optimize = 2
plantfloor_B[0].position = [0.949999988079071, 3.950000047683716, 0.32499998807907104]
plantfloor_B[0].rotation = [0, 0, 0.01884955539881635]
plantfloor_B[0].optimize = 2
plantfloor_A[0].position = [0.550000011920929, 3.6500000953674316, 0.32499998807907104]
plantfloor_A[0].rotation = [0, 0, 0.00942477746072377]
plantfloor_A[0].optimize = 2
consolevase[0].position = [1.7400000095367432, 0.17499999701976776, 0.8649999499320984]
consolevase[0].rotation = [0, 0, 0.01256637125682779]
consolevase[0].optimize = 2
candle_A[0].position = [4.989999771118164, 3.299999952316284, 0.9300000071525574]
candle_A[0].rotation = [0, 0, 0.01256637125682779]
candle_A[0].optimize = 2
lamp_B[0].position = [4.199999809265137, 3.950000047683716, 0.824999988079071]
lamp_B[0].rotation = [0, 0, 0.00942477746072377]
lamp_B[0].optimize = 2
artworkwall_B[0].position = [0.016124853864312172, 2.9000000953674316, 0.375]
artworkwall_B[0].rotation = [0, 0, 0.0025409202949315235]
artworkwall_B[0].optimize = 2
book_A[0].position = [1.6799999475479126, 1.75, 0.47999998927116394]
book_A[0].rotation = [0, 0, 0.01256637125682779]
book_A[0].optimize = 2
magazine_D[0].position = [1.6799999475479126, 1.75, 0.45499998331069946]
magazine_D[0].rotation = [0, 0, 0.0157079639172164]
magazine_D[0].optimize = 2
booktable_B[0].position = [1.6799999475479126, 2.0999999046325684, 0.47499996423721313]
booktable_B[0].rotation = [0, 0, 0.0157079639172164]
booktable_B[0].optimize = 2
plant_B[0].position = [2.5999999046325684, 3.950000047683716, 0.699999988079071]
plant_B[0].rotation = [0, 0, 0.00942477746072377]
plant_B[0].optimize = 2
book_table_A[0].position = [1.6799999475479126, 2.0999999046325684, 0.5049999356269836]
book_table_A[0].rotation = [0, 0, 0.0157079639172164]
book_table_A[0].optimize = 2
vase_console_B[0].position = [2.0999999046325684, 0.17499999701976776, 0.8999999761581421]
vase_console_B[0].rotation = [0, 0, 0.01256637125682779]
vase_console_B[0].optimize = 2
artwork_A[0].position = [0.6499999761581421, 4.288697242736816, 0.30000001192092896]
artwork_A[0].rotation = [0, 0, -1.5682554064999652]
artwork_A[0].optimize = 2
plant_floor_A[0].position = [3.8499999046325684, 2.6500000953674316, 0.4749999940395355]
plant_floor_A[0].rotation = [0, 0, 0.00942477746072377]
plant_floor_A[0].optimize = 2
book_B[0].position = [0.1599999964237213, 3.799999952316284, 2.184999942779541]
book_B[0].rotation = [0, 0, 0.01256637125682779]
book_B[0].optimize = 2
vasefloor_C[0].position = [3.799999952316284, 0.20000000298023224, 0.125]
vasefloor_C[0].rotation = [0, 0, 0.00942477746072377]
vasefloor_C[0].optimize = 2
magazine_console[0].position = [1.7400000095367432, 0.17499999701976776, 0.7849999666213989]
magazine_console[0].rotation = [0, 0, 1.586504290712113]
magazine_console[0].optimize = 2
vase_table[0].position = [1.6799999475479126, 2.569999933242798, 0.5550000071525574]
vase_table[0].rotation = [0, 0, 0.01256637125682779]
vase_table[0].optimize = 2
plant_A[0].position = [0.18000000715255737, 0.8500000238418579, 0.22499999403953552]
plant_A[0].rotation = [0, 0, 0.00942477746072377]
plant_A[0].optimize = 2
plantfloor_C[0].position = [1.9500000476837158, 3.950000047683716, 0.20000000298023224]
plantfloor_C[0].rotation = [0, 0, 0.02595596860215056]
plantfloor_C[0].optimize = 2
plant_C[0].position = [3.299999952316284, 3.950000047683716, 0.699999988079071]
plant_C[0].rotation = [0, 0, 0.00942477746072377]
plant_C[0].optimize = 2
bookshelf[0].position = [0.16444100439548492, 3.799999952316284, 1.024999976158142]
bookshelf[0].rotation = [0, 0, 0.011873019394325784]
bookshelf[0].optimize = 2
couch[0].position = [0.4735445976257324, 2.1500000953674316, 0.4749999940395355]
couch[0].rotation = [0, 0, 0.02120598732114741]
couch[0].optimize = 2
book_sideboard[0].position = [4.989999771118164, 2.6500000953674316, 0.8199999928474426]
book_sideboard[0].rotation = [0, 0, -3.115629214321287]
book_sideboard[0].optimize = 2
magazine_A[0].position = [1.6799999475479126, 1.75, 0.4350000023841858]
magazine_A[0].rotation = [0, 0, 0.0157079639172164]
magazine_A[0].optimize = 2
booktable_A[0].position = [1.6799999475479126, 2.0999999046325684, 0.4449999928474426]
booktable_A[0].rotation = [0, 0, 0.0157079639172164]
booktable_A[0].optimize = 2
chair_A[0].position = [3.049999952316284, 1.649999976158142, 0.49000000953674316]
chair_A[0].rotation = [0, 0, -3.118802304959478]
chair_A[0].optimize = 2
mirror_A[0].position = [0.02583017759025097, 2.1500000953674316, 0.42500001192092896]
mirror_A[0].rotation = [0, 0, 0.0025409193727581954]
mirror_A[0].optimize = 2
magazinetable_A[0].position = [2.0199999809265137, 1.75, 0.4350000023841858]
magazinetable_A[0].rotation = [0, 0, 0.0157079639172164]
magazinetable_A[0].optimize = 2
lamp_A[0].position = [1.0, 0.4000000059604645, 0.824999988079071]
lamp_A[0].rotation = [0, 0, 0.00942477746072377]
lamp_A[0].optimize = 2
magazine_B[0].position = [1.6799999475479126, 1.75, 0.4449999928474426]
magazine_B[0].rotation = [0, 0, 0.0157079639172164]
magazine_B[0].optimize = 2
tv[0].position = [5.156609535217285, 3.25, 0.375]
tv[0].rotation = [0, 0, -3.135941138107549]
tv[0].optimize = 2
plant_D[0].position = [0.949999988079071, 0.8500000238418579, 0.22499999403953552]
plant_D[0].rotation = [0, 0, 0.00942477746072377]
plant_D[0].optimize = 2
bookshelfbook_A[0].position = [0.1599999964237213, 3.5199999809265137, 2.179999828338623]
bookshelfbook_A[0].rotation = [0, 0, 0.01256637125682779]
bookshelfbook_A[0].optimize = 2
floorbook_A[0].position = [4.989999771118164, 3.700000047683716, 0.8199999928474426]
floorbook_A[0].rotation = [0, 0, 0.0157079639172164]
floorbook_A[0].optimize = 2
mirror_C[0].position = [2.0999999046325684, 0.020954810082912445, 0.32499998807907104]
mirror_C[0].rotation = [0, 0, 1.5733372480120014]
mirror_C[0].optimize = 2
plantfloor_D[0].position = [3.8499999046325684, 3.950000047683716, 0.20000000298023224]
plantfloor_D[0].rotation = [0, 0, 0.00942477746072377]
plantfloor_D[0].optimize = 2
vasefloor_D[0].position = [1.0, 3.4200000762939453, 0.125]
vasefloor_D[0].rotation = [0, 0, 0.00942477746072377]
vasefloor_D[0].optimize = 2
console[0].position = [2.0999999046325684, 0.17815150320529938, 0.38999998569488525]
console[0].rotation = [0, 0, 1.582669341098879]
console[0].optimize = 2
vase_sideboard[0].position = [4.989999771118164, 3.9000000953674316, 0.9750000238418579]
vase_sideboard[0].rotation = [0, 0, 0.01256637125682779]
vase_sideboard[0].optimize = 2
artwork_G[0].position = [4.0, 4.288697242736816, 0.25]
artwork_G[0].rotation = [0, 0, -1.5682554071222121]
artwork_G[0].optimize = 2
chair_B[0].position = [3.049999952316284, 2.700000047683716, 0.49000000953674316]
chair_B[0].rotation = [0, 0, -3.118802304959478]
chair_B[0].optimize = 2
sideboardcandle_A[0].position = [4.989999771118164, 2.9000000953674316, 0.8899999856948853]
sideboardcandle_A[0].rotation = [0, 0, 0.01256637125682779]
sideboardcandle_A[0].optimize = 2
sideboard[0].position = [4.965028285980225, 3.25, 0.4000000059604645]
sideboard[0].rotation = [0, 0, -3.1079412963154582]
sideboard[0].optimize = 2
book_console[0].position = [2.0999999046325684, 0.17499999701976776, 0.7949999570846558]
book_console[0].rotation = [0, 0, 1.586504290712113]
book_console[0].optimize = 2
vase_console_A[0].position = [2.5, 0.17499999701976776, 0.9399999380111694]
vase_console_A[0].rotation = [0, 0, 0.01256637125682779]
vase_console_A[0].optimize = 2
floorbook_B[0].position = [4.989999771118164, 3.700000047683716, 0.85999995470047]
floorbook_B[0].rotation = [0, 0, 0.01256637125682779]
floorbook_B[0].optimize = 2
candle_B[0].position = [4.989999771118164, 3.5, 0.9300000071525574]
candle_B[0].rotation = [0, 0, 0.01256637125682779]
candle_B[0].optimize = 2
artwork_F[0].position = [3.450000047683716, 4.288697242736816, 0.22499999403953552]
artwork_F[0].rotation = [0, 0, -1.5682554071222121]
artwork_F[0].optimize = 2
artwork_D[0].position = [2.3499999046325684, 4.288697242736816, 0.2750000059604645]
artwork_D[0].rotation = [0, 0, -1.5682554052778654]
artwork_D[0].optimize = 2
magazinetable_C[0].position = [2.0199999809265137, 1.75, 0.45499998331069946]
magazinetable_C[0].rotation = [0, 0, 0.01256637125682779]
magazinetable_C[0].optimize = 2
artworkwall_A[0].position = [0.016124853864312172, 1.399999976158142, 0.375]
artworkwall_A[0].rotation = [0, 0, 0.0025409202949315235]
artworkwall_A[0].optimize = 2
vasefloor_A[0].position = [3.0, 0.20000000298023224, 0.23999999463558197]
vasefloor_A[0].rotation = [0, 0, 0.00942477746072377]
vasefloor_A[0].optimize = 2
mirror_B[0].position = [1.4500000476837158, 0.025830429047346115, 0.4000000059604645]
mirror_B[0].rotation = [0, 0, 1.5733372470898281]
mirror_B[0].optimize = 2
mirror_D[0].position = [2.75, 0.020955141633749008, 0.3499999940395355]
mirror_D[0].rotation = [0, 0, 1.573337246167655]
mirror_D[0].optimize = 2
sideboardcandle_B[0].position = [4.989999771118164, 3.0999999046325684, 0.8899999856948853]
sideboardcandle_B[0].rotation = [0, 0, 0.01256637125682779]
sideboardcandle_B[0].optimize = 2
magazinetable_B[0].position = [2.0199999809265137, 1.75, 0.4449999928474426]
magazinetable_B[0].rotation = [0, 0, 0.0157079639172164]
magazinetable_B[0].optimize = 2
vasefloor_B[0].position = [3.4000000953674316, 0.20000000298023224, 0.23999999463558197]
vasefloor_B[0].rotation = [0, 0, 0.00942477746072377]
vasefloor_B[0].optimize = 2
artwork_B[0].position = [1.25, 4.288697242736816, 0.2750000059604645]
artwork_B[0].rotation = [0, 0, -1.5682554052778654]
artwork_B[0].optimize = 2
floorplant_B[0].position = [1.2999999523162842, 0.4000000059604645, 0.22499999403953552]
floorplant_B[0].rotation = [0, 0, 0.00942477746072377]
floorplant_B[0].optimize = 2
floorlamp[0].position = [0.30000001192092896, 0.4000000059604645, 0.824999988079071]
floorlamp[0].rotation = [0, 0, 0.00942477746072377]
floorlamp[0].optimize = 2
vase_floor_A[0].position = [0.6499999761581421, 3.4200000762939453, 0.25]
vase_floor_A[0].rotation = [0, 0, 0.00942477746072377]
vase_floor_A[0].optimize = 2

