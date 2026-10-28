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
    Wall(corner1=[4.50, 0.00, 0.00], corner2=[4.50, 5.00, 0.00]),
    Wall(corner1=[4.50, 5.00, 0.00], corner2=[0.00, 5.00, 0.00]),
    Wall(corner1=[0.00, 5.00, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.50, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
menu = Assets(description="A single piece of thin and upright menu board with pastel colors, rectangular shape, smooth matte surface and a subtle retro pattern", size=[0.03, 0.70, 1.00], placements=[AssetInstance() for _ in range(1)])
sidetable = Assets(description="A retro side table with chrome legs, square top in pastel pink, smooth glossy surface and a subtle beveled edge, compact and low‑profile design", size=[0.55, 0.55, 0.52], placements=[AssetInstance() for _ in range(1)])
cup_A = Assets(description="A pastel pink and teal ceramic cup with a rounded body, slightly flared rim and a short curved handle, glossy finish", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
cup_B = Assets(description="A ceramic retro diner cup with a smooth rounded shape, pastel pink and teal glaze, glossy finish and a small curved handle", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
neonsign_A = Assets(description="A single piece of thin and upright neon sign with a rectangular outline, bright pastel glow, smooth glass tubes and a retro diner font", size=[0.06, 0.90, 0.55], placements=[AssetInstance() for _ in range(1)])
cupsidetable_A = Assets(description="A pastel pink and teal ceramic cup, circular with a short handle, slightly tapered body", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_A = Assets(description="A pastel coloured ceramic planter with a squat cylindrical shape, smooth glaze and a small opening at the top, containing a small green plant", size=[0.38, 0.38, 0.65], placements=[AssetInstance() for _ in range(1)])
neonsign_B = Assets(description="A single piece of thin and upright neon sign with a rectangular outline, bright pastel glow, smooth glass tubes and a retro diner font", size=[0.06, 0.90, 0.55], placements=[AssetInstance() for _ in range(1)])
cupsidetable_B = Assets(description="A small ceramic cup with pastel pink and teal glaze, rounded body and a short stubby handle", size=[0.09, 0.11, 0.09], placements=[AssetInstance() for _ in range(1)])
counter = Assets(description="A retro diner counter with sleek chrome accents, rectangular shape, pastel pink and teal panels, low-slung profile and a smooth glossy finish, featuring a subtle curved front edge for a classic 1950s look", size=[0.75, 2.20, 1.05], placements=[AssetInstance() for _ in range(1)])
sign_A = Assets(description="A single piece of thin and upright neon sign with bold retro lettering, bright glowing tubes and a dark backing, classic diner aesthetic", size=[0.08, 1.10, 0.60], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="A retro diner floor lamp with a chrome base, slender cylindrical pole and a rounded fabric shade in pastel pink", size=[0.42, 0.42, 1.65], placements=[AssetInstance() for _ in range(1)])
cup_C = Assets(description="A pastel pink and teal ceramic cup with a rounded cylindrical shape, smooth glossy finish and a gently flared rim, classic 1950s diner style", size=[0.09, 0.11, 0.10], placements=[AssetInstance() for _ in range(1)])
poster_A = Assets(description="A single piece of thin and upright vintage poster with a rectangular shape, pastel diner artwork, glossy surface and slightly rolled edges", size=[0.01, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
plant_B = Assets(description="A retro potted plant in a pastel teal ceramic planter, cylindrical pot with a slightly flared rim, glossy finish, and a lush green foliage top that adds a soft organic shape", size=[0.50, 0.50, 1.05], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="A retro floor lamp with a chrome base, tall slender metal pole and a small round shade, polished finish and subtle 1950s curves", size=[0.38, 0.38, 1.60], placements=[AssetInstance() for _ in range(1)])
magazinebench_A = Assets(description="A retro 1950s diner magazine with vintage cover art, rectangular thin paper, glossy finish and slightly rounded corners", size=[0.30, 0.22, 0.01], placements=[AssetInstance() for _ in range(1)])
vintageposter_A = Assets(description="A single piece of thin and upright vintage diner poster with pastel colours, rectangular shape, slightly textured paper and retro typography", size=[0.01, 0.55, 0.80], placements=[AssetInstance() for _ in range(1)])
magazine_A = Assets(description="A vintage‑style magazine with a rectangular cover, slightly thick pages, pastel retro graphics and a matte finish", size=[0.30, 0.22, 0.01], placements=[AssetInstance() for _ in range(1)])
vintageposter_B = Assets(description="A single piece of thin and upright vintage poster with pastel diner graphics, rounded top edge and paper material", size=[0.01, 0.50, 0.75], placements=[AssetInstance() for _ in range(1)])
lamp_C = Assets(description="A retro floor lamp with a chrome base, tall slender metal pole and a small round shade, polished finish and subtle 1950s curves", size=[0.38, 0.38, 1.60], placements=[AssetInstance() for _ in range(1)])
poster_B = Assets(description="A single piece of thin and upright vintage poster with a rectangular shape, pastel diner artwork, glossy surface and slightly rolled edges", size=[0.01, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
floorlamp_A = Assets(description="A retro diner floor lamp with a chrome base, slender cylindrical pole and a small conical shade, polished finish and streamlined silhouette", size=[0.35, 0.35, 1.55], placements=[AssetInstance() for _ in range(1)])
magazine_B = Assets(description="A single piece of thin and upright vintage retro diner magazine with a rectangular cover, pastel accents and slightly worn edges", size=[0.30, 0.22, 0.01], placements=[AssetInstance() for _ in range(1)])
neonsign_C = Assets(description="A single piece of thin and upright neon sign with retro 1950s diner lettering, rectangular outline, bright pastel glow and a sleek metal backing", size=[0.07, 1.00, 0.60], placements=[AssetInstance() for _ in range(1)])
stool_A = Assets(description="A retro vinyl stool with a round cushioned seat in pastel pink and teal, chrome tapered legs, cylindrical silhouette and a glossy finish, the seat slightly recessed for comfort", size=[0.42, 0.42, 0.72], placements=[AssetInstance() for _ in range(1)])
trashcan = Assets(description="A retro trash can with a chrome top rim, cylindrical body in pastel pink, smooth curved sides and a matte enamel finish, featuring a recessed lid opening", size=[0.42, 0.42, 0.75], placements=[AssetInstance() for _ in range(1)])
magazine_C = Assets(description="A single piece of thin and upright magazine with vintage diner covers, rectangular shape and a crisp paper texture", size=[0.30, 0.22, 0.01], placements=[AssetInstance() for _ in range(1)])
plant_C = Assets(description="A pastel planter holding a small green potted plant, cylindrical pot with a smooth matte finish and a subtle leaf pattern", size=[0.35, 0.35, 0.60], placements=[AssetInstance() for _ in range(1)])
floorlamp_B = Assets(description="A retro floor lamp with a chrome cylindrical base, slender metal pole and a small conical shade, sleek streamlined look", size=[0.35, 0.35, 1.55], placements=[AssetInstance() for _ in range(1)])
poster_C = Assets(description="A single piece of thin and upright vintage diner poster with bold graphics, pastel color scheme and a slightly textured paper surface", size=[0.01, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
poster_D = Assets(description="A single piece of thin and upright vintage diner poster with bold graphics, pastel color scheme and a slightly textured paper surface", size=[0.01, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
neonsign_D = Assets(description="A single piece of thin and upright neon sign with retro 1950s diner lettering, bright pastel glow and a slender glass tube frame", size=[0.06, 0.95, 0.50], placements=[AssetInstance() for _ in range(1)])
poster_E = Assets(description="A single piece of thin and upright vintage retro diner poster with a rectangular shape, pastel graphics and slightly curled edges", size=[0.01, 0.55, 0.80], placements=[AssetInstance() for _ in range(1)])
cashregister = Assets(description="A compact retro cash register with chrome accents, rectangular base, slightly curved front panel and a small display screen", size=[0.42, 0.48, 0.38], placements=[AssetInstance() for _ in range(1)])
floorlamp_C = Assets(description="A retro diner floor lamp with a chrome base, slender cylindrical pole and a small conical shade, polished finish and streamlined silhouette", size=[0.35, 0.35, 1.55], placements=[AssetInstance() for _ in range(1)])
lamp_D = Assets(description="A retro diner floor lamp with a chrome base, slender cylindrical pole and a rounded fabric shade in pastel pink", size=[0.42, 0.42, 1.65], placements=[AssetInstance() for _ in range(1)])
cup_D = Assets(description="A small ceramic cup with a rounded body, pastel pink and teal glaze, smooth curved surface and a short stubby handle", size=[0.09, 0.11, 0.09], placements=[AssetInstance() for _ in range(1)])
plant_D = Assets(description="A pastel coloured ceramic planter with a squat cylindrical shape, smooth glaze and a small opening at the top, containing a small green plant", size=[0.38, 0.38, 0.65], placements=[AssetInstance() for _ in range(1)])
magazine_D = Assets(description="A single piece of thin and upright magazine with vintage diner covers, rectangular shape and a crisp paper texture", size=[0.30, 0.22, 0.01], placements=[AssetInstance() for _ in range(1)])
stool_B = Assets(description="A retro vinyl stool with a round cushioned seat in pastel pink and teal, chrome tapered legs, cylindrical silhouette and a glossy finish, the seat slightly recessed for comfort", size=[0.42, 0.42, 0.72], placements=[AssetInstance() for _ in range(1)])
neonsign_E = Assets(description="A single piece of thin and upright neon sign with bright pastel glow, rectangular shape, sleek metal frame and retro diner lettering", size=[0.07, 0.90, 0.55], placements=[AssetInstance() for _ in range(1)])
bench = Assets(description="A retro bench seat with a long rectangular vinyl cushion in pastel teal, chrome frame legs, low‑slung profile, smooth curved backrest and a glossy finish, featuring a subtle stitching detail along the seat", size=[0.68, 1.80, 0.88], placements=[AssetInstance() for _ in range(1)])
neonsign_F = Assets(description="A single piece of thin and upright neon sign with retro 1950s diner lettering, bright pastel glow and a slender glass tube frame", size=[0.06, 0.95, 0.50], placements=[AssetInstance() for _ in range(1)])
cup_E = Assets(description="A pastel pink and teal ceramic cup with a rounded cylindrical shape, glossy finish and a small curved handle, reminiscent of 1950s diner tableware", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
cup_F = Assets(description="A ceramic retro diner cup with a smooth rounded shape, pastel pink and teal glaze, glossy finish and a small curved handle", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
vintageposter_C = Assets(description="A single piece of thin and upright vintage poster with pastel diner graphics, rounded top edge and paper material", size=[0.01, 0.50, 0.75], placements=[AssetInstance() for _ in range(1)])
magazinecounter = Assets(description="A vintage retro diner magazine with a rectangular cover, pastel colors and classic 1950s typography, thin paper stock", size=[0.30, 0.22, 0.01], placements=[AssetInstance() for _ in range(1)])
floorlamp_D = Assets(description="A retro floor lamp with a chrome cylindrical base, slender metal pole and a small conical shade, sleek streamlined look", size=[0.35, 0.35, 1.55], placements=[AssetInstance() for _ in range(1)])
sodafountain = Assets(description="A retro soda fountain with chrome accents, pastel pink rectangular base, curved glass front panel, sleek streamlined shape and a glossy finish, includes a small chrome tap protrusion", size=[0.60, 0.90, 1.45], placements=[AssetInstance() for _ in range(1)])
benchtrinket = Assets(description="A small mixed‑material trinket consisting of a shiny coin and a slender pen, both compact and rounded, retro diner vibe", size=[0.04, 0.16, 0.01], placements=[AssetInstance() for _ in range(1)])
cup_G = Assets(description="A pastel pink and teal ceramic cup with a rounded cylindrical shape, glossy finish and a small curved handle, reminiscent of 1950s diner tableware", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
neonsign_G = Assets(description="A thin upright neon sign in retro diner style, elongated rectangular shape with glowing pastel pink and teal tubes, chrome border and glossy finish", size=[0.07, 1.20, 0.45], placements=[AssetInstance() for _ in range(1)])
bookbench = Assets(description="A pastel‑covered paperback book with a soft rectangular shape, slightly rounded corners and a smooth matte finish", size=[0.22, 0.15, 0.03], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="A vintage cover book with a rectangular shape, slightly textured cover and muted pastel tones, classic diner aesthetic", size=[0.23, 0.16, 0.03], placements=[AssetInstance() for _ in range(1)])
floorlamp_E = Assets(description="A retro floor lamp with a slender chrome base, tall cylindrical shaft and a simple round shade, polished metal finish", size=[0.38, 0.38, 1.62], placements=[AssetInstance() for _ in range(1)])
sidetabletrinket = Assets(description="A small mixed‑material trinket consisting of a shiny coin and a slender pen, both compact and rounded, retro diner vibe", size=[0.04, 0.16, 0.01], placements=[AssetInstance() for _ in range(1)])
cup_H = Assets(description="A pastel pink and teal ceramic cup with a rounded cylindrical shape, smooth glossy finish and a gently flared rim, classic 1950s diner style", size=[0.09, 0.11, 0.10], placements=[AssetInstance() for _ in range(1)])
stool_C = Assets(description="A retro vinyl stool with a round cushioned seat in pastel pink and teal, chrome tapered legs, cylindrical silhouette and a glossy finish, the seat slightly recessed for comfort", size=[0.42, 0.42, 0.72], placements=[AssetInstance() for _ in range(1)])
neonsign_H = Assets(description="A single piece of thin and upright neon sign with bright pastel glow, rectangular shape, sleek metal frame and retro diner lettering", size=[0.07, 0.90, 0.55], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="A vintage diner style book with a rectangular cover, slightly rounded edges, pastel accent stripe and a textured paper feel", size=[0.23, 0.16, 0.03], placements=[AssetInstance() for _ in range(1)])
booksidetable_A = Assets(description="A pastel‑covered retro diner book, thin rectangular volume with rounded edges, matte finish and subtle decorative embossing", size=[0.22, 0.15, 0.03], placements=[AssetInstance() for _ in range(1)])
straw = Assets(description="A thin plastic straw in pastel colors, straight cylindrical shape with a smooth surface and a slight curve at the tip", size=[0.01, 0.01, 0.22], placements=[AssetInstance() for _ in range(1)])
poster_F = Assets(description="A single piece of thin and upright vintage retro diner poster with a rectangular shape, pastel graphics and slightly curled edges", size=[0.01, 0.55, 0.80], placements=[AssetInstance() for _ in range(1)])
magazinebench_B = Assets(description="A thin rectangular magazine with vintage 1950s diner cover art, pastel accents and slightly glossy paper, edges slightly rounded", size=[0.30, 0.22, 0.01], placements=[AssetInstance() for _ in range(1)])
magazine_E = Assets(description="A vintage style magazine with a rectangular shape, glossy cover and retro 1950s diner graphics, thin and lightweight", size=[0.30, 0.22, 0.01], placements=[AssetInstance() for _ in range(1)])
poster_G = Assets(description="A single piece of thin and upright vintage poster with pastel colors, rectangular shape, slightly textured paper and retro diner illustration", size=[0.01, 0.55, 0.80], placements=[AssetInstance() for _ in range(1)])
floorlamp_F = Assets(description="A retro floor lamp with a slender chrome base, tall cylindrical shaft and a simple round shade, polished metal finish", size=[0.38, 0.38, 1.62], placements=[AssetInstance() for _ in range(1)])
plant_E = Assets(description="A retro potted plant in a pastel teal ceramic planter, cylindrical pot with a slightly flared rim, glossy finish, and a lush green foliage top that adds a soft organic shape", size=[0.50, 0.50, 1.05], placements=[AssetInstance() for _ in range(1)])
coatrack = Assets(description="A retro coat rack with a chrome frame, vertical stand and multiple pastel teal hooks, slender rectangular silhouette and a polished finish", size=[0.55, 0.55, 1.75], placements=[AssetInstance() for _ in range(1)])
sign_B = Assets(description="A single piece of thin and upright neon retro diner sign reading 'Diner', with a rectangular frame, bright pink lettering and a glowing red outline", size=[0.08, 1.10, 0.55], placements=[AssetInstance() for _ in range(1)])
magazinebench_C = Assets(description="A thin rectangular magazine with vintage 1950s diner cover art, pastel accents and slightly glossy paper, edges slightly rounded", size=[0.30, 0.22, 0.01], placements=[AssetInstance() for _ in range(1)])
jukebox = Assets(description="A retro corner jukebox with chrome trim, pastel teal and pink body, rectangular but slightly rounded top, glossy enamel surface and a small illuminated marquee panel", size=[0.58, 0.85, 1.45], placements=[AssetInstance() for _ in range(1)])
cup_I = Assets(description="A pastel pink and teal ceramic cup with a rounded cylindrical shape, glossy finish and a small curved handle, reminiscent of 1950s diner tableware", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
booksidetable_B = Assets(description="A pastel‑covered paperback book with a soft rectangular shape, slightly rounded corners and a smooth matte finish", size=[0.22, 0.15, 0.03], placements=[AssetInstance() for _ in range(1)])
plant_F = Assets(description="A pastel planter holding a small green potted plant, cylindrical pot with a smooth matte finish and a subtle leaf pattern", size=[0.35, 0.35, 0.60], placements=[AssetInstance() for _ in range(1)])
poster_H = Assets(description="A single piece of thin and upright vintage poster with pastel colors, rectangular shape, slightly textured paper and retro diner illustration", size=[0.01, 0.55, 0.80], placements=[AssetInstance() for _ in range(1)])
magazine_F = Assets(description="A single piece of thin and upright vintage retro diner magazine with a rectangular cover, pastel accents and slightly worn edges", size=[0.30, 0.22, 0.01], placements=[AssetInstance() for _ in range(1)])
magazinerack = Assets(description="A retro magazine rack with a chrome frame, vertical rectangular columns, pastel teal back panel, open front slots, and a low-slung rectangular base with a polished finish", size=[0.35, 0.65, 1.25], placements=[AssetInstance() for _ in range(1)])
cup_J = Assets(description="A ceramic diner cup with pastel pink and teal glaze, rounded body, slightly flared rim and smooth glossy finish", size=[0.09, 0.11, 0.10], placements=[AssetInstance() for _ in range(1)])
cupsidetable_C = Assets(description="A pastel pink and teal ceramic cup with a rounded body, slightly flared rim and a short curved handle, glossy finish", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
stool_D = Assets(description="A retro vinyl stool with a round cushioned seat in pastel pink and teal, chrome tapered legs, cylindrical silhouette and a glossy finish, the seat slightly recessed for comfort", size=[0.42, 0.42, 0.72], placements=[AssetInstance() for _ in range(1)])

menu[0].instance_id = 'menu_0'
sidetable[0].instance_id = 'sidetable_0'
cup_A[0].instance_id = 'cup_A_0'
cup_B[0].instance_id = 'cup_B_0'
neonsign_A[0].instance_id = 'neonsign_A_0'
cupsidetable_A[0].instance_id = 'cupsidetable_A_0'
plant_A[0].instance_id = 'plant_A_0'
neonsign_B[0].instance_id = 'neonsign_B_0'
cupsidetable_B[0].instance_id = 'cupsidetable_B_0'
counter[0].instance_id = 'counter_0'
sign_A[0].instance_id = 'sign_A_0'
lamp_A[0].instance_id = 'lamp_A_0'
cup_C[0].instance_id = 'cup_C_0'
poster_A[0].instance_id = 'poster_A_0'
plant_B[0].instance_id = 'plant_B_0'
lamp_B[0].instance_id = 'lamp_B_0'
magazinebench_A[0].instance_id = 'magazinebench_A_0'
vintageposter_A[0].instance_id = 'vintageposter_A_0'
magazine_A[0].instance_id = 'magazine_A_0'
vintageposter_B[0].instance_id = 'vintageposter_B_0'
lamp_C[0].instance_id = 'lamp_C_0'
poster_B[0].instance_id = 'poster_B_0'
floorlamp_A[0].instance_id = 'floorlamp_A_0'
magazine_B[0].instance_id = 'magazine_B_0'
neonsign_C[0].instance_id = 'neonsign_C_0'
stool_A[0].instance_id = 'stool_A_0'
trashcan[0].instance_id = 'trashcan_0'
magazine_C[0].instance_id = 'magazine_C_0'
plant_C[0].instance_id = 'plant_C_0'
floorlamp_B[0].instance_id = 'floorlamp_B_0'
poster_C[0].instance_id = 'poster_C_0'
poster_D[0].instance_id = 'poster_D_0'
neonsign_D[0].instance_id = 'neonsign_D_0'
poster_E[0].instance_id = 'poster_E_0'
cashregister[0].instance_id = 'cashregister_0'
floorlamp_C[0].instance_id = 'floorlamp_C_0'
lamp_D[0].instance_id = 'lamp_D_0'
cup_D[0].instance_id = 'cup_D_0'
plant_D[0].instance_id = 'plant_D_0'
magazine_D[0].instance_id = 'magazine_D_0'
stool_B[0].instance_id = 'stool_B_0'
neonsign_E[0].instance_id = 'neonsign_E_0'
bench[0].instance_id = 'bench_0'
neonsign_F[0].instance_id = 'neonsign_F_0'
cup_E[0].instance_id = 'cup_E_0'
cup_F[0].instance_id = 'cup_F_0'
vintageposter_C[0].instance_id = 'vintageposter_C_0'
magazinecounter[0].instance_id = 'magazinecounter_0'
floorlamp_D[0].instance_id = 'floorlamp_D_0'
sodafountain[0].instance_id = 'sodafountain_0'
benchtrinket[0].instance_id = 'benchtrinket_0'
cup_G[0].instance_id = 'cup_G_0'
neonsign_G[0].instance_id = 'neonsign_G_0'
bookbench[0].instance_id = 'bookbench_0'
book_A[0].instance_id = 'book_A_0'
floorlamp_E[0].instance_id = 'floorlamp_E_0'
sidetabletrinket[0].instance_id = 'sidetabletrinket_0'
cup_H[0].instance_id = 'cup_H_0'
stool_C[0].instance_id = 'stool_C_0'
neonsign_H[0].instance_id = 'neonsign_H_0'
book_B[0].instance_id = 'book_B_0'
booksidetable_A[0].instance_id = 'booksidetable_A_0'
straw[0].instance_id = 'straw_0'
poster_F[0].instance_id = 'poster_F_0'
magazinebench_B[0].instance_id = 'magazinebench_B_0'
magazine_E[0].instance_id = 'magazine_E_0'
poster_G[0].instance_id = 'poster_G_0'
floorlamp_F[0].instance_id = 'floorlamp_F_0'
plant_E[0].instance_id = 'plant_E_0'
coatrack[0].instance_id = 'coatrack_0'
sign_B[0].instance_id = 'sign_B_0'
magazinebench_C[0].instance_id = 'magazinebench_C_0'
jukebox[0].instance_id = 'jukebox_0'
cup_I[0].instance_id = 'cup_I_0'
booksidetable_B[0].instance_id = 'booksidetable_B_0'
plant_F[0].instance_id = 'plant_F_0'
poster_H[0].instance_id = 'poster_H_0'
magazine_F[0].instance_id = 'magazine_F_0'
magazinerack[0].instance_id = 'magazinerack_0'
cup_J[0].instance_id = 'cup_J_0'
cupsidetable_C[0].instance_id = 'cupsidetable_C_0'
stool_D[0].instance_id = 'stool_D_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

menu[0].position = [2.517947809885908, 4.656169412382047, 0.5]
menu[0].rotation = [0, 0, 0]
sidetable[0].position = [2.755258246831792, 2.6782584829125655, 0.26]
sidetable[0].rotation = [0, 0, 0]
cup_A[0].position = [4.084264506618029, 3.855233074211872, 0.05]
cup_A[0].rotation = [0, 0, 0]
cup_B[0].position = [1.8860495902320613, 0.5117257040960482, 0.05]
cup_B[0].rotation = [0, 0, 0]
neonsign_A[0].position = [1.893008124326355, 3.7886771705658178, 0.275]
neonsign_A[0].rotation = [0, 0, 0]
cupsidetable_A[0].position = [0.539416111700151, 1.1219696289573284, 0.05]
cupsidetable_A[0].rotation = [0, 0, 0]
plant_A[0].position = [1.419284367940952, 2.1489415886010255, 0.325]
plant_A[0].rotation = [0, 0, 0]
neonsign_B[0].position = [4.170893874023541, 1.8891589905052641, 0.275]
neonsign_B[0].rotation = [0, 0, 0]
cupsidetable_B[0].position = [1.4921088240201286, 0.18989635113017267, 0.045]
cupsidetable_B[0].rotation = [0, 0, 0]
counter[0].position = [3.1358653965566967, 1.531747056704098, 0.525]
counter[0].rotation = [0, 0, 0]
sign_A[0].position = [0.047006155297922014, 3.971366053119585, 0.3]
sign_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [0.06798453328234572, 2.7250001841998457, 0.825]
lamp_A[0].rotation = [0, 0, 0]
cup_C[0].position = [0.918912870290615, 4.243771903896262, 0.05]
cup_C[0].rotation = [0, 0, 0]
poster_A[0].position = [2.8053509533508203, 2.8747980757100695, 0.45]
poster_A[0].rotation = [0, 0, 0]
plant_B[0].position = [0.5697573644039746, 4.950133666445811, 0.525]
plant_B[0].rotation = [0, 0, 0]
lamp_B[0].position = [3.87417023234922, 0.14057585962251706, 0.8]
lamp_B[0].rotation = [0, 0, 0]
magazinebench_A[0].position = [2.1112407665282884, 2.3064492645230668, 0.005]
magazinebench_A[0].rotation = [0, 0, 0]
vintageposter_A[0].position = [3.2405095267690927, 4.660861434685066, 0.4]
vintageposter_A[0].rotation = [0, 0, 0]
magazine_A[0].position = [0.08590295744993015, 1.7409643653639022, 0.0075]
magazine_A[0].rotation = [0, 0, 0]
vintageposter_B[0].position = [3.784354804570028, 4.8419393574786245, 0.375]
vintageposter_B[0].rotation = [0, 0, 0]
lamp_C[0].position = [0.10666798183886417, 2.081486445510001, 0.8]
lamp_C[0].rotation = [0, 0, 0]
poster_B[0].position = [3.599194437765009, 1.1977215233981764, 0.45]
poster_B[0].rotation = [0, 0, 0]
floorlamp_A[0].position = [2.0464309740158555, 4.035535938608576, 0.775]
floorlamp_A[0].rotation = [0, 0, 0]
magazine_B[0].position = [3.2231890275513835, 4.676387184614214, 0.005]
magazine_B[0].rotation = [0, 0, 0]
neonsign_C[0].position = [2.3417575631764533, 1.420963112106703, 0.3]
neonsign_C[0].rotation = [0, 0, 0]
stool_A[0].position = [2.2328278735620897, 3.7575402790488255, 0.36]
stool_A[0].rotation = [0, 0, 0]
trashcan[0].position = [1.90165905564738, 1.524501771226416, 0.375]
trashcan[0].rotation = [0, 0, 0]
magazine_C[0].position = [4.4526695132930545, 0.8304551234453261, 0.005]
magazine_C[0].rotation = [0, 0, 0]
plant_C[0].position = [2.1195123440922097, 0.7298819759854375, 0.3]
plant_C[0].rotation = [0, 0, 0]
floorlamp_B[0].position = [0.8876419732193097, 3.997510420835541, 0.775]
floorlamp_B[0].rotation = [0, 0, 0]
poster_C[0].position = [3.616663282555037, 2.1885633001731564, 0.45]
poster_C[0].rotation = [0, 0, 0]
poster_D[0].position = [3.694778755407244, 3.1462928883599184, 0.45]
poster_D[0].rotation = [0, 0, 0]
neonsign_D[0].position = [3.410326806504452, 3.7225830749570985, 0.25]
neonsign_D[0].rotation = [0, 0, 0]
poster_E[0].position = [2.09290690596945, 2.6339331843904707, 0.4]
poster_E[0].rotation = [0, 0, 0]
cashregister[0].position = [3.4977016297991037, 3.066774863829881, 0.19]
cashregister[0].rotation = [0, 0, 0]
floorlamp_C[0].position = [0.929099647211707, 1.6816987655867766, 0.775]
floorlamp_C[0].rotation = [0, 0, 0]
lamp_D[0].position = [2.8716344539649925, 3.9392674553268145, 0.825]
lamp_D[0].rotation = [0, 0, 0]
cup_D[0].position = [2.546719512702186, 3.7301437870720666, 0.045]
cup_D[0].rotation = [0, 0, 0]
plant_D[0].position = [4.131791545418673, 4.880760599200799, 0.325]
plant_D[0].rotation = [0, 0, 0]
magazine_D[0].position = [0.8970671509440549, 1.789075087329262, 0.005]
magazine_D[0].rotation = [0, 0, 0]
stool_B[0].position = [1.1743660229457697, 4.443878459323159, 0.36]
stool_B[0].rotation = [0, 0, 0]
neonsign_E[0].position = [1.6552644792597966, 0.3200862774899299, 0.275]
neonsign_E[0].rotation = [0, 0, 0]
bench[0].position = [0.8692201557600039, 1.496616104486976, 0.44]
bench[0].rotation = [0, 0, 0]
neonsign_F[0].position = [3.9561848155603943, 1.2556503164007182, 0.25]
neonsign_F[0].rotation = [0, 0, 0]
cup_E[0].position = [2.5470966459244475, 1.319805491816498, 0.05]
cup_E[0].rotation = [0, 0, 0]
cup_F[0].position = [0.18850895191914235, 2.1092753408654246, 0.05]
cup_F[0].rotation = [0, 0, 0]
vintageposter_C[0].position = [2.2999104847376985, 0.07575887240988954, 0.375]
vintageposter_C[0].rotation = [0, 0, 0]
magazinecounter[0].position = [2.5081664883721997, 2.530616898365362, 0.005]
magazinecounter[0].rotation = [0, 0, 0]
floorlamp_D[0].position = [4.337356235857393, 3.0337449162785997, 0.775]
floorlamp_D[0].rotation = [0, 0, 0]
sodafountain[0].position = [2.7622309929578743, 2.4143397687225345, 0.725]
sodafountain[0].rotation = [0, 0, 0]
benchtrinket[0].position = [2.1831188644005124, 1.0318857443017793, 0.0075]
benchtrinket[0].rotation = [0, 0, 0]
cup_G[0].position = [1.5291436417599837, 1.7724126417762054, 0.05]
cup_G[0].rotation = [0, 0, 0]
neonsign_G[0].position = [1.8142832072325397, 2.7968069898131183, 0.225]
neonsign_G[0].rotation = [0, 0, 0]
bookbench[0].position = [0.20750888734127387, 3.8642142562737574, 0.0125]
bookbench[0].rotation = [0, 0, 0]
book_A[0].position = [3.160428426727108, 3.9684730123236363, 0.015]
book_A[0].rotation = [0, 0, 0]
floorlamp_E[0].position = [0.5303622649401312, 3.185894244245067, 0.81]
floorlamp_E[0].rotation = [0, 0, 0]
sidetabletrinket[0].position = [1.9363009750941786, 0.784013865352392, 0.0075]
sidetabletrinket[0].rotation = [0, 0, 0]
cup_H[0].position = [3.6714674598199046, 4.205884481067209, 0.05]
cup_H[0].rotation = [0, 0, 0]
stool_C[0].position = [0.6943161131155755, 0.581641571116096, 0.36]
stool_C[0].rotation = [0, 0, 0]
neonsign_H[0].position = [1.4928615424574831, 4.707297001586727, 0.275]
neonsign_H[0].rotation = [0, 0, 0]
book_B[0].position = [2.957463362829053, 1.00534347620373, 0.015]
book_B[0].rotation = [0, 0, 0]
booksidetable_A[0].position = [4.090111160199401, 4.98754508977609, 0.0125]
booksidetable_A[0].rotation = [0, 0, 0]
straw[0].position = [0.3396067868123477, 3.1211405322613635, 0.11]
straw[0].rotation = [0, 0, 0]
poster_F[0].position = [2.3063853399036423, 2.2798313870438864, 0.4]
poster_F[0].rotation = [0, 0, 0]
magazinebench_B[0].position = [3.770836422710798, 1.8668720656983502, 0.005]
magazinebench_B[0].rotation = [0, 0, 0]
magazine_E[0].position = [0.00814757825223611, 0.5198622451669066, 0.006]
magazine_E[0].rotation = [0, 0, 0]
poster_G[0].position = [3.2861681715297677, 2.6852727489504566, 0.4]
poster_G[0].rotation = [0, 0, 0]
floorlamp_F[0].position = [1.9229090011747814, 0.22970296646484756, 0.81]
floorlamp_F[0].rotation = [0, 0, 0]
plant_E[0].position = [0.7105589903044895, 3.3371155914692836, 0.525]
plant_E[0].rotation = [0, 0, 0]
coatrack[0].position = [0.8764727002122199, 2.3361593374794714, 0.875]
coatrack[0].rotation = [0, 0, 0]
sign_B[0].position = [4.45623993151772, 0.19224673320732633, 0.275]
sign_B[0].rotation = [0, 0, 0]
magazinebench_C[0].position = [2.418843027773364, 4.685286594831278, 0.005]
magazinebench_C[0].rotation = [0, 0, 0]
jukebox[0].position = [4.2286962981676295, 0.37790068096363927, 0.725]
jukebox[0].rotation = [0, 0, 0]
cup_I[0].position = [1.707669383708441, 0.5616395718637895, 0.05]
cup_I[0].rotation = [0, 0, 0]
booksidetable_B[0].position = [3.017889097761925, 1.9965297380299014, 0.0125]
booksidetable_B[0].rotation = [0, 0, 0]
plant_F[0].position = [2.989154730850702, 3.7573996398053278, 0.3]
plant_F[0].rotation = [0, 0, 0]
poster_H[0].position = [0.6331123791391362, 1.3839729656770305, 0.4]
poster_H[0].rotation = [0, 0, 0]
magazine_F[0].position = [0.8492222972386582, 2.0103526769855677, 0.005]
magazine_F[0].rotation = [0, 0, 0]
magazinerack[0].position = [1.145437711848289, 2.839643937130172, 0.625]
magazinerack[0].rotation = [0, 0, 0]
cup_J[0].position = [1.1571931678370342, 4.773997155938076, 0.05]
cup_J[0].rotation = [0, 0, 0]
cupsidetable_C[0].position = [0.5350368775366077, 2.54797560995841, 0.05]
cupsidetable_C[0].rotation = [0, 0, 0]
stool_D[0].position = [3.0806319477777655, 0.7910228869316371, 0.36]
stool_D[0].rotation = [0, 0, 0]
menu[0].position = [2.517947809885908, 4.656169412382047, 0.5]
menu[0].rotation = [0, 0, 0]
sidetable[0].position = [2.755258246831792, 2.6782584829125655, 0.26]
sidetable[0].rotation = [0, 0, 0]
cup_A[0].position = [4.084264506618029, 3.855233074211872, 0.05]
cup_A[0].rotation = [0, 0, 0]
cup_B[0].position = [1.8860495902320613, 0.5117257040960482, 0.05]
cup_B[0].rotation = [0, 0, 0]
neonsign_A[0].position = [1.893008124326355, 3.7886771705658178, 0.275]
neonsign_A[0].rotation = [0, 0, 0]
cupsidetable_A[0].position = [0.539416111700151, 1.1219696289573284, 0.05]
cupsidetable_A[0].rotation = [0, 0, 0]
plant_A[0].position = [1.419284367940952, 2.1489415886010255, 0.325]
plant_A[0].rotation = [0, 0, 0]
neonsign_B[0].position = [4.170893874023541, 1.8891589905052641, 0.275]
neonsign_B[0].rotation = [0, 0, 0]
cupsidetable_B[0].position = [1.4921088240201286, 0.18989635113017267, 0.045]
cupsidetable_B[0].rotation = [0, 0, 0]
counter[0].position = [3.1358653965566967, 1.531747056704098, 0.525]
counter[0].rotation = [0, 0, 0]
sign_A[0].position = [0.047006155297922014, 3.971366053119585, 0.3]
sign_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [0.06798453328234572, 2.7250001841998457, 0.825]
lamp_A[0].rotation = [0, 0, 0]
cup_C[0].position = [0.918912870290615, 4.243771903896262, 0.05]
cup_C[0].rotation = [0, 0, 0]
poster_A[0].position = [2.8053509533508203, 2.8747980757100695, 0.45]
poster_A[0].rotation = [0, 0, 0]
plant_B[0].position = [0.5697573644039746, 4.950133666445811, 0.525]
plant_B[0].rotation = [0, 0, 0]
lamp_B[0].position = [3.87417023234922, 0.14057585962251706, 0.8]
lamp_B[0].rotation = [0, 0, 0]
magazinebench_A[0].position = [2.1112407665282884, 2.3064492645230668, 0.005]
magazinebench_A[0].rotation = [0, 0, 0]
vintageposter_A[0].position = [3.2405095267690927, 4.660861434685066, 0.4]
vintageposter_A[0].rotation = [0, 0, 0]
magazine_A[0].position = [0.08590295744993015, 1.7409643653639022, 0.0075]
magazine_A[0].rotation = [0, 0, 0]
vintageposter_B[0].position = [3.784354804570028, 4.8419393574786245, 0.375]
vintageposter_B[0].rotation = [0, 0, 0]
lamp_C[0].position = [0.10666798183886417, 2.081486445510001, 0.8]
lamp_C[0].rotation = [0, 0, 0]
poster_B[0].position = [3.599194437765009, 1.1977215233981764, 0.45]
poster_B[0].rotation = [0, 0, 0]
floorlamp_A[0].position = [2.0464309740158555, 4.035535938608576, 0.775]
floorlamp_A[0].rotation = [0, 0, 0]
magazine_B[0].position = [3.2231890275513835, 4.676387184614214, 0.005]
magazine_B[0].rotation = [0, 0, 0]
neonsign_C[0].position = [2.3417575631764533, 1.420963112106703, 0.3]
neonsign_C[0].rotation = [0, 0, 0]
stool_A[0].position = [2.2328278735620897, 3.7575402790488255, 0.36]
stool_A[0].rotation = [0, 0, 0]
trashcan[0].position = [1.90165905564738, 1.524501771226416, 0.375]
trashcan[0].rotation = [0, 0, 0]
magazine_C[0].position = [4.4526695132930545, 0.8304551234453261, 0.005]
magazine_C[0].rotation = [0, 0, 0]
plant_C[0].position = [2.1195123440922097, 0.7298819759854375, 0.3]
plant_C[0].rotation = [0, 0, 0]
floorlamp_B[0].position = [0.8876419732193097, 3.997510420835541, 0.775]
floorlamp_B[0].rotation = [0, 0, 0]
poster_C[0].position = [3.616663282555037, 2.1885633001731564, 0.45]
poster_C[0].rotation = [0, 0, 0]
poster_D[0].position = [3.694778755407244, 3.1462928883599184, 0.45]
poster_D[0].rotation = [0, 0, 0]
neonsign_D[0].position = [3.410326806504452, 3.7225830749570985, 0.25]
neonsign_D[0].rotation = [0, 0, 0]
poster_E[0].position = [2.09290690596945, 2.6339331843904707, 0.4]
poster_E[0].rotation = [0, 0, 0]
cashregister[0].position = [3.4977016297991037, 3.066774863829881, 0.19]
cashregister[0].rotation = [0, 0, 0]
floorlamp_C[0].position = [0.929099647211707, 1.6816987655867766, 0.775]
floorlamp_C[0].rotation = [0, 0, 0]
lamp_D[0].position = [2.8716344539649925, 3.9392674553268145, 0.825]
lamp_D[0].rotation = [0, 0, 0]
cup_D[0].position = [2.546719512702186, 3.7301437870720666, 0.045]
cup_D[0].rotation = [0, 0, 0]
plant_D[0].position = [4.131791545418673, 4.880760599200799, 0.325]
plant_D[0].rotation = [0, 0, 0]
magazine_D[0].position = [0.8970671509440549, 1.789075087329262, 0.005]
magazine_D[0].rotation = [0, 0, 0]
stool_B[0].position = [1.1743660229457697, 4.443878459323159, 0.36]
stool_B[0].rotation = [0, 0, 0]
neonsign_E[0].position = [1.6552644792597966, 0.3200862774899299, 0.275]
neonsign_E[0].rotation = [0, 0, 0]
bench[0].position = [0.8692201557600039, 1.496616104486976, 0.44]
bench[0].rotation = [0, 0, 0]
neonsign_F[0].position = [3.9561848155603943, 1.2556503164007182, 0.25]
neonsign_F[0].rotation = [0, 0, 0]
cup_E[0].position = [2.5470966459244475, 1.319805491816498, 0.05]
cup_E[0].rotation = [0, 0, 0]
cup_F[0].position = [0.18850895191914235, 2.1092753408654246, 0.05]
cup_F[0].rotation = [0, 0, 0]
vintageposter_C[0].position = [2.2999104847376985, 0.07575887240988954, 0.375]
vintageposter_C[0].rotation = [0, 0, 0]
magazinecounter[0].position = [2.5081664883721997, 2.530616898365362, 0.005]
magazinecounter[0].rotation = [0, 0, 0]
floorlamp_D[0].position = [4.337356235857393, 3.0337449162785997, 0.775]
floorlamp_D[0].rotation = [0, 0, 0]
sodafountain[0].position = [2.7622309929578743, 2.4143397687225345, 0.725]
sodafountain[0].rotation = [0, 0, 0]
benchtrinket[0].position = [2.1831188644005124, 1.0318857443017793, 0.0075]
benchtrinket[0].rotation = [0, 0, 0]
cup_G[0].position = [1.5291436417599837, 1.7724126417762054, 0.05]
cup_G[0].rotation = [0, 0, 0]
neonsign_G[0].position = [1.8142832072325397, 2.7968069898131183, 0.225]
neonsign_G[0].rotation = [0, 0, 0]
bookbench[0].position = [0.20750888734127387, 3.8642142562737574, 0.0125]
bookbench[0].rotation = [0, 0, 0]
book_A[0].position = [3.160428426727108, 3.9684730123236363, 0.015]
book_A[0].rotation = [0, 0, 0]
floorlamp_E[0].position = [0.5303622649401312, 3.185894244245067, 0.81]
floorlamp_E[0].rotation = [0, 0, 0]
sidetabletrinket[0].position = [1.9363009750941786, 0.784013865352392, 0.0075]
sidetabletrinket[0].rotation = [0, 0, 0]
cup_H[0].position = [3.6714674598199046, 4.205884481067209, 0.05]
cup_H[0].rotation = [0, 0, 0]
stool_C[0].position = [0.6943161131155755, 0.581641571116096, 0.36]
stool_C[0].rotation = [0, 0, 0]
neonsign_H[0].position = [1.4928615424574831, 4.707297001586727, 0.275]
neonsign_H[0].rotation = [0, 0, 0]
book_B[0].position = [2.957463362829053, 1.00534347620373, 0.015]
book_B[0].rotation = [0, 0, 0]
booksidetable_A[0].position = [4.090111160199401, 4.98754508977609, 0.0125]
booksidetable_A[0].rotation = [0, 0, 0]
straw[0].position = [0.3396067868123477, 3.1211405322613635, 0.11]
straw[0].rotation = [0, 0, 0]
poster_F[0].position = [2.3063853399036423, 2.2798313870438864, 0.4]
poster_F[0].rotation = [0, 0, 0]
magazinebench_B[0].position = [3.770836422710798, 1.8668720656983502, 0.005]
magazinebench_B[0].rotation = [0, 0, 0]
magazine_E[0].position = [0.00814757825223611, 0.5198622451669066, 0.006]
magazine_E[0].rotation = [0, 0, 0]
poster_G[0].position = [3.2861681715297677, 2.6852727489504566, 0.4]
poster_G[0].rotation = [0, 0, 0]
floorlamp_F[0].position = [1.9229090011747814, 0.22970296646484756, 0.81]
floorlamp_F[0].rotation = [0, 0, 0]
plant_E[0].position = [0.7105589903044895, 3.3371155914692836, 0.525]
plant_E[0].rotation = [0, 0, 0]
coatrack[0].position = [0.8764727002122199, 2.3361593374794714, 0.875]
coatrack[0].rotation = [0, 0, 0]
sign_B[0].position = [4.45623993151772, 0.19224673320732633, 0.275]
sign_B[0].rotation = [0, 0, 0]
magazinebench_C[0].position = [2.418843027773364, 4.685286594831278, 0.005]
magazinebench_C[0].rotation = [0, 0, 0]
jukebox[0].position = [4.2286962981676295, 0.37790068096363927, 0.725]
jukebox[0].rotation = [0, 0, 0]
cup_I[0].position = [1.707669383708441, 0.5616395718637895, 0.05]
cup_I[0].rotation = [0, 0, 0]
booksidetable_B[0].position = [3.017889097761925, 1.9965297380299014, 0.0125]
booksidetable_B[0].rotation = [0, 0, 0]
plant_F[0].position = [2.989154730850702, 3.7573996398053278, 0.3]
plant_F[0].rotation = [0, 0, 0]
poster_H[0].position = [0.6331123791391362, 1.3839729656770305, 0.4]
poster_H[0].rotation = [0, 0, 0]
magazine_F[0].position = [0.8492222972386582, 2.0103526769855677, 0.005]
magazine_F[0].rotation = [0, 0, 0]
magazinerack[0].position = [1.145437711848289, 2.839643937130172, 0.625]
magazinerack[0].rotation = [0, 0, 0]
cup_J[0].position = [1.1571931678370342, 4.773997155938076, 0.05]
cup_J[0].rotation = [0, 0, 0]
cupsidetable_C[0].position = [0.5350368775366077, 2.54797560995841, 0.05]
cupsidetable_C[0].rotation = [0, 0, 0]
stool_D[0].position = [3.0806319477777655, 0.7910228869316371, 0.36]
stool_D[0].rotation = [0, 0, 0]

solver.constraints = []

# Orientation references let every asset receive an explicit orientation
# constraint without introducing any additional scene geometry.
east_facing = AssetInstance(rotation=[0, 0, radians(0)])
north_facing = AssetInstance(rotation=[0, 0, radians(90)])
west_facing = AssetInstance(rotation=[0, 0, radians(180)])
south_facing = AssetInstance(rotation=[0, 0, radians(-90)])

# Keep the entrance corridor in front of the door at x=0.575..1.525, y=5 clear.
# The counter occupies the right side of the diner, with stools facing it.
floor_layout = [
    (sidetable[0],       [1.25, 2.55, 0.26], 0),
    (counter[0],         [4.125, 3.55, 0.525], 180),
    (bench[0],           [0.34, 2.55, 0.44], 0),

    (stool_A[0],         [3.25, 2.65, 0.36], 0),
    (stool_B[0],         [3.25, 3.25, 0.36], 0),
    (stool_C[0],         [3.25, 3.85, 0.36], 0),
    (stool_D[0],         [3.25, 4.45, 0.36], 0),

    (sodafountain[0],    [3.30, 0.30, 0.725], 90),
    (jukebox[0],         [0.29, 0.65, 0.725], 0),
    (magazinerack[0],    [4.325, 1.20, 0.625], 180),
    (trashcan[0],        [4.25, 1.80, 0.375], 180),
    (coatrack[0],        [2.15, 4.725, 0.875], -90),

    # Plants soften otherwise unused perimeter areas.
    (plant_A[0],         [0.20, 1.40, 0.325], 0),
    (plant_B[0],         [0.25, 3.80, 0.525], 0),
    (plant_C[0],         [1.10, 0.20, 0.30], 90),
    (plant_D[0],         [1.65, 0.19, 0.325], 90),
    (plant_E[0],         [2.15, 0.25, 0.525], 90),
    (plant_F[0],         [2.70, 4.80, 0.30], -90),

    # The numerous slim lamps are distributed through open areas while
    # preserving the entrance route and the counter service aisle.
    (lamp_A[0],          [0.90, 1.32, 0.825], 0),
    (lamp_B[0],          [1.48, 1.15, 0.80], 0),
    (lamp_C[0],          [2.02, 1.18, 0.80], 0),
    (lamp_D[0],          [2.58, 1.10, 0.825], 0),
    (floorlamp_A[0],     [0.95, 3.15, 0.775], 0),
    (floorlamp_B[0],     [1.50, 3.20, 0.775], 0),
    (floorlamp_C[0],     [2.05, 2.00, 0.775], 0),
    (floorlamp_D[0],     [2.10, 2.60, 0.775], 0),
    (floorlamp_E[0],     [2.12, 3.25, 0.81], 0),
    (floorlamp_F[0],     [2.12, 3.88, 0.81], 0),
]

for instance, position, yaw_degrees in floor_layout:
    instance.position = position
    instance.rotation = [0, 0, radians(yaw_degrees)]

    # This high-priority positional target preserves the planned,
    # non-overlapping arrangement during physical adjustment.
    solver.distance_constraint(
        instance,
        AssetInstance(position=position),
        0,
        0,
        weight=10,
    )

    # Every floor asset also receives an explicit orientation constraint.
    if yaw_degrees == 90:
        solver.align_with(instance, north_facing)
    elif yaw_degrees == 180:
        solver.align_with(instance, west_facing)
    elif yaw_degrees == -90:
        solver.align_with(instance, south_facing)
    else:
        solver.align_with(instance, east_facing)

# Add semantic wall relationships for the large furniture intended to be
# flush with the perimeter. The exact targets above remain the primary
# constraints and already account for each object's bounding-box depth.
solver.against_wall(counter[0], walls[0])
solver.against_wall(bench[0], walls[2])
solver.against_wall(sodafountain[0], walls[3])
solver.against_wall(jukebox[0], walls[2])
solver.against_wall(magazinerack[0], walls[0])
solver.against_wall(coatrack[0], walls[1])

# Preserve the functional furniture groupings.
solver.distance_constraint(sidetable[0], bench[0], 0.75, 1.30, weight=1)
for stool_instance in (stool_A[0], stool_B[0], stool_C[0], stool_D[0]):
    solver.distance_constraint(stool_instance, counter[0], 0.80, 1.55, weight=1)
    solver.point_towards(stool_instance, counter[0])

# Wall decorations are packed around all four walls. The north-wall
# arrangement leaves the 0.95 m doorway and the floor before it unobstructed.
wall_layout = [
    # Bottom wall: objects face north into the room.
    (neonsign_A[0],      walls[3], [0.48, 0.03, 1.65], 90),
    (neonsign_B[0],      walls[3], [1.38, 0.03, 1.65], 90),
    (neonsign_C[0],      walls[3], [2.33, 0.035, 1.65], 90),
    (neonsign_D[0],      walls[3], [3.305, 0.03, 1.65], 90),
    (poster_A[0],        walls[3], [4.20, 0.005, 1.55], 90),

    # Left wall: objects face east.
    (neonsign_E[0],      walls[2], [0.035, 0.45, 1.65], 0),
    (neonsign_F[0],      walls[2], [0.03, 1.375, 1.65], 0),
    (neonsign_H[0],      walls[2], [0.035, 2.30, 1.65], 0),
    (sign_B[0],          walls[2], [0.04, 3.30, 1.65], 0),
    (poster_B[0],        walls[2], [0.005, 4.15, 1.55], 0),
    (poster_G[0],        walls[2], [0.005, 4.725, 1.55], 0),

    # Right wall: objects face west.
    (poster_C[0],        walls[0], [4.495, 0.30, 1.55], 180),
    (poster_D[0],        walls[0], [4.495, 0.90, 1.55], 180),
    (poster_E[0],        walls[0], [4.495, 1.475, 1.50], 180),
    (poster_F[0],        walls[0], [4.495, 2.025, 1.50], 180),
    (poster_H[0],        walls[0], [4.495, 2.575, 1.50], 180),
    (vintageposter_B[0], walls[0], [4.495, 3.10, 1.50], 180),
    (vintageposter_C[0], walls[0], [4.495, 3.60, 1.50], 180),

    # Top wall: the first item is left of the doorway; the remaining
    # decorations begin to the right of the doorway.
    (vintageposter_A[0], walls[1], [0.30, 4.995, 1.50], -90),
    (menu[0],            walls[1], [1.90, 4.985, 1.25], -90),
    (neonsign_G[0],      walls[1], [2.85, 4.965, 1.65], -90),
    (sign_A[0],          walls[1], [3.95, 4.96, 1.65], -90),
]

for instance, wall, position, yaw_degrees in wall_layout:
    instance.position = position
    instance.rotation = [0, 0, radians(yaw_degrees)]

    # Wall contact is the primary positional relationship for decorations.
    solver.against_wall(instance, wall)
    solver.distance_constraint(
        instance,
        AssetInstance(position=position),
        0,
        0,
        weight=10,
    )

    if yaw_degrees == 90:
        solver.align_with(instance, north_facing)
    elif yaw_degrees == 180:
        solver.align_with(instance, west_facing)
    elif yaw_degrees == -90:
        solver.align_with(instance, south_facing)
    else:
        solver.align_with(instance, east_facing)

# Counter-top objects. Cup_F is asset o0045 and is explicitly supported by
# counter o0009 as required. The other cups, reading material, register, and
# straw are also kept on usable surfaces rather than on the floor.
counter_items = [
    (cashregister[0],    [4.15, 3.58, 1.24], 180),

    (cup_A[0],           [3.88, 2.52, 1.10], 180),
    (cup_B[0],           [4.34, 2.52, 1.10], 180),
    (cup_C[0],           [3.88, 2.78, 1.10], 180),
    (cup_D[0],           [4.34, 2.78, 1.095], 180),
    (cup_E[0],           [3.88, 3.04, 1.10], 180),
    (cup_F[0],           [4.34, 3.04, 1.10], 180),
    (cup_G[0],           [3.88, 4.02, 1.10], 180),
    (cup_H[0],           [4.34, 4.02, 1.10], 180),
    (cup_I[0],           [3.88, 4.30, 1.10], 180),
    (cup_J[0],           [4.34, 4.30, 1.10], 180),

    (magazine_A[0],      [3.92, 3.30, 1.055], 180),
    (magazine_B[0],      [4.30, 3.30, 1.055], 180),
    (magazine_C[0],      [3.92, 3.88, 1.055], 180),
    (magazine_D[0],      [4.30, 3.88, 1.055], 180),
    (magazine_E[0],      [3.92, 4.54, 1.055], 180),
    (magazine_F[0],      [4.30, 4.54, 1.055], 180),
    (magazinecounter[0], [4.10, 2.34, 1.055], 180),

    (book_A[0],          [3.90, 3.16, 1.065], 180),
    (book_B[0],          [4.31, 3.16, 1.065], 180),
    (straw[0],           [4.34, 3.02, 1.21], 180),
]

for instance, position, yaw_degrees in counter_items:
    instance.position = position
    instance.rotation = [0, 0, radians(yaw_degrees)]

    # Support is specified before the target because preventing an object
    # from falling off the counter is the most important relationship.
    solver.on_top_of(instance, counter[0])
    solver.distance_constraint(
        instance,
        AssetInstance(position=position),
        0,
        0,
        weight=10,
    )
    solver.align_with(instance, counter[0])

# Side-table accessories are spread across the tabletop without overlapping.
sidetable_items = [
    (cupsidetable_A[0],  [1.08, 2.38, 0.57], 0),
    (cupsidetable_B[0],  [1.40, 2.38, 0.565], 0),
    (cupsidetable_C[0],  [1.08, 2.68, 0.57], 0),
    (booksidetable_A[0], [1.39, 2.66, 0.535], 0),
    (booksidetable_B[0], [1.39, 2.52, 0.535], 0),
    (sidetabletrinket[0],[1.10, 2.53, 0.525], 0),
]

for instance, position, yaw_degrees in sidetable_items:
    instance.position = position
    instance.rotation = [0, 0, radians(yaw_degrees)]
    solver.on_top_of(instance, sidetable[0])
    solver.distance_constraint(
        instance,
        AssetInstance(position=position),
        0,
        0,
        weight=10,
    )
    solver.align_with(instance, sidetable[0])

# Reading material and the compact trinket rest on separate portions of the
# long bench seat.
bench_items = [
    (magazinebench_A[0], [0.34, 1.92, 0.885], 0),
    (magazinebench_B[0], [0.34, 2.32, 0.885], 0),
    (magazinebench_C[0], [0.34, 2.72, 0.885], 0),
    (bookbench[0],       [0.34, 3.10, 0.895], 0),
    (benchtrinket[0],    [0.34, 3.34, 0.885], 0),
]

for instance, position, yaw_degrees in bench_items:
    instance.position = position
    instance.rotation = [0, 0, radians(yaw_degrees)]
    solver.on_top_of(instance, bench[0])
    solver.distance_constraint(
        instance,
        AssetInstance(position=position),
        0,
        0,
        weight=10,
    )
    solver.align_with(instance, bench[0])

solver.constraints = []
cup_B[0].position = [4.340000152587891, 2.5199999809265137, 1.0999999046325684]
cup_B[0].rotation = [0, 0, -3.118800984312999]
cup_B[0].optimize = 2
poster_A[0].position = [4.190125942230225, -0.0011201626621186733, 0.44999998807907104]
poster_A[0].rotation = [0, 0, 1.573337246167655]
poster_A[0].optimize = 2
poster_E[0].position = [4.501559734344482, 1.475000023841858, 0.4000000059604645]
poster_E[0].rotation = [0, 0, -3.139051734217035]
poster_E[0].optimize = 2
magazine_C[0].position = [3.9200000762939453, 3.880000114440918, 1.0549999475479126]
magazine_C[0].rotation = [0, 0, -3.118800984312999]
magazine_C[0].optimize = 2
floorlamp_C[0].position = [2.049999952316284, 2.0, 0.7749999761581421]
floorlamp_C[0].rotation = [0, 0, 0.00942477746072377]
floorlamp_C[0].optimize = 2
magazine_F[0].position = [4.159666061401367, 4.515961647033691, 1.0549999475479126]
magazine_F[0].rotation = [0, 0, -3.118800984312999]
magazine_F[0].optimize = 2
magazinebench_A[0].position = [0.3400000035762787, 1.9199999570846558, 0.8849999904632568]
magazinebench_A[0].rotation = [0, 0, 0.022791030181337935]
magazinebench_A[0].optimize = 2
stool_C[0].position = [3.240000009536743, 3.859999895095825, 0.36000001430511475]
stool_C[0].rotation = [0, 0, 0.0157079639172164]
stool_C[0].optimize = 2
poster_H[0].position = [4.501559734344482, 2.575000047683716, 0.4000000059604645]
poster_H[0].rotation = [0, 0, -3.139051734217035]
poster_H[0].optimize = 2
neonsign_A[0].position = [0.47999998927116394, 0.031143315136432648, 0.2750000059604645]
neonsign_A[0].rotation = [0, 0, 1.5733372418791103]
neonsign_A[0].optimize = 2
floorlamp_D[0].position = [2.0999999046325684, 2.5999999046325684, 0.7749999761581421]
floorlamp_D[0].rotation = [0, 0, 0.00942477746072377]
floorlamp_D[0].optimize = 2
magazine_D[0].position = [4.269496440887451, 3.8747751712799072, 1.0549999475479126]
magazine_D[0].rotation = [0, 0, -3.118800984312999]
magazine_D[0].optimize = 2
magazinecounter[0].position = [4.079933166503906, 2.457149028778076, 1.0549999475479126]
magazinecounter[0].rotation = [0, 0, -3.118800984312999]
magazinecounter[0].optimize = 2
poster_C[0].position = [4.501560688018799, 0.30000001192092896, 0.44999998807907104]
poster_C[0].rotation = [0, 0, -3.1390517332948615]
poster_C[0].optimize = 2
booksidetable_A[0].position = [1.3899999856948853, 2.6600000858306885, 0.5349999666213989]
booksidetable_A[0].rotation = [0, 0, 0.02279109852594279]
booksidetable_A[0].optimize = 2
cup_H[0].position = [4.247339248657227, 4.0041279792785645, 1.0999999046325684]
cup_H[0].rotation = [0, 0, -3.118800984312999]
cup_H[0].optimize = 2
magazine_A[0].position = [3.9200000762939453, 3.299999952316284, 1.0549999475479126]
magazine_A[0].rotation = [0, 0, -3.118800984312999]
magazine_A[0].optimize = 2
magazine_B[0].position = [4.300000190734863, 3.299999952316284, 1.0549999475479126]
magazine_B[0].rotation = [0, 0, -3.118800984312999]
magazine_B[0].optimize = 2
cup_J[0].position = [4.20074462890625, 4.27614688873291, 1.0999999046325684]
cup_J[0].rotation = [0, 0, -3.118800984312999]
cup_J[0].optimize = 2
lamp_D[0].position = [2.5799999237060547, 1.100000023841858, 0.824999988079071]
lamp_D[0].rotation = [0, 0, 0.00942477746072377]
lamp_D[0].optimize = 2
lamp_B[0].position = [1.4800000190734863, 1.149999976158142, 0.800000011920929]
lamp_B[0].rotation = [0, 0, 0.00942477746072377]
lamp_B[0].optimize = 2
cupsidetable_C[0].position = [1.0800000429153442, 2.680000066757202, 0.5699999928474426]
cupsidetable_C[0].rotation = [0, 0, 0.02279109852594279]
cupsidetable_C[0].optimize = 2
stool_B[0].position = [3.240000009536743, 3.240000009536743, 0.36000001430511475]
stool_B[0].rotation = [0, 0, 0.0157079639172164]
stool_B[0].optimize = 2
benchtrinket[0].position = [0.3400000035762787, 3.3399999141693115, 0.8849999904632568]
benchtrinket[0].rotation = [0, 0, 0.022791030181337935]
benchtrinket[0].optimize = 2
cup_F[0].position = [4.340000152587891, 3.0399999618530273, 1.0999999046325684]
cup_F[0].rotation = [0, 0, -3.118800984312999]
cup_F[0].optimize = 2
plant_E[0].position = [2.1500000953674316, 0.25, 0.5249999761581421]
plant_E[0].rotation = [0, 0, 1.5802211042556205]
plant_E[0].optimize = 2
magazinerack[0].position = [4.324174880981445, 1.2000000476837158, 0.625]
magazinerack[0].rotation = [0, 0, -3.1390517363613077]
magazinerack[0].optimize = 2
floorlamp_A[0].position = [0.949999988079071, 3.1500000953674316, 0.7749999761581421]
floorlamp_A[0].rotation = [0, 0, 0.00942477746072377]
floorlamp_A[0].optimize = 2
poster_B[0].position = [-0.0011201626621186733, 4.150000095367432, 0.44999998807907104]
poster_B[0].rotation = [0, 0, 0.0025409193727581954]
poster_B[0].optimize = 2
cup_A[0].position = [3.880000114440918, 2.5199999809265137, 1.0999999046325684]
cup_A[0].rotation = [0, 0, -3.118800984312999]
cup_A[0].optimize = 2
sign_B[0].position = [0.041397374123334885, 3.299999952316284, 0.2750000059604645]
sign_B[0].rotation = [0, 0, 0.002540911717843874]
sign_B[0].optimize = 2
trashcan[0].position = [4.25, 1.7999999523162842, 0.375]
trashcan[0].rotation = [0, 0, -3.1321678761290697]
trashcan[0].optimize = 2
sign_A[0].position = [3.950000047683716, 4.958602428436279, 0.30000001192092896]
sign_A[0].rotation = [0, 0, -1.56825541415488]
sign_A[0].optimize = 2
booksidetable_B[0].position = [1.3899999856948853, 2.5199999809265137, 0.5349999666213989]
booksidetable_B[0].rotation = [0, 0, 0.02279109852594279]
booksidetable_B[0].optimize = 2
cup_E[0].position = [3.880000114440918, 3.0399999618530273, 1.0999999046325684]
cup_E[0].rotation = [0, 0, -3.118800984312999]
cup_E[0].optimize = 2
vintageposter_B[0].position = [4.501560688018799, 3.0999999046325684, 0.375]
vintageposter_B[0].rotation = [0, 0, -3.1390517323726885]
vintageposter_B[0].optimize = 2
neonsign_B[0].position = [1.3799999952316284, 0.031143315136432648, 0.2750000059604645]
neonsign_B[0].rotation = [0, 0, 1.5733372418791103]
neonsign_B[0].optimize = 2
plant_A[0].position = [0.20000000298023224, 1.399999976158142, 0.32499998807907104]
plant_A[0].rotation = [0, 0, 0.00942477746072377]
plant_A[0].optimize = 2
menu[0].position = [1.899999976158142, 4.993266582489014, 0.5]
menu[0].rotation = [0, 0, -1.5682554086442377]
menu[0].optimize = 2
lamp_A[0].position = [0.8999999761581421, 1.3200000524520874, 0.824999988079071]
lamp_A[0].rotation = [0, 0, 0.00942477746072377]
lamp_A[0].optimize = 2
book_A[0].position = [3.9000000953674316, 3.1600000858306885, 1.0649999380111694]
book_A[0].rotation = [0, 0, -3.118800984312999]
book_A[0].optimize = 2
neonsign_D[0].position = [3.305000066757202, 0.03120683692395687, 0.25]
neonsign_D[0].rotation = [0, 0, 1.5733372415791846]
neonsign_D[0].optimize = 2
sidetable[0].position = [1.25, 2.549999952316284, 0.25999999046325684]
sidetable[0].rotation = [0, 0, 0.05026547968485982]
sidetable[0].optimize = 2
stool_D[0].position = [3.25, 4.449999809265137, 0.36000001430511475]
stool_D[0].rotation = [0, 0, 0.0157079639172164]
stool_D[0].optimize = 2
floorlamp_E[0].position = [2.119999885559082, 3.25, 0.8100000023841858]
floorlamp_E[0].rotation = [0, 0, 0.00942477746072377]
floorlamp_E[0].optimize = 2
cup_I[0].position = [3.880000114440918, 4.300000190734863, 1.0999999046325684]
cup_I[0].rotation = [0, 0, -3.118800984312999]
cup_I[0].optimize = 2
sidetabletrinket[0].position = [1.100000023841858, 2.5299999713897705, 0.5249999761581421]
sidetabletrinket[0].rotation = [0, 0, 0.02279109852594279]
sidetabletrinket[0].optimize = 2
poster_G[0].position = [-0.0011190669611096382, 4.724999904632568, 0.4000000059604645]
poster_G[0].rotation = [0, 0, 0.0025409193727581954]
poster_G[0].optimize = 2
straw[0].position = [4.340000152587891, 3.0199999809265137, 1.159999966621399]
straw[0].rotation = [0, 0, -3.118800984312999]
straw[0].optimize = 2
floorlamp_B[0].position = [1.5, 3.200000047683716, 0.7749999761581421]
floorlamp_B[0].rotation = [0, 0, 0.00942477746072377]
floorlamp_B[0].optimize = 2
neonsign_G[0].position = [2.8499999046325684, 4.963475704193115, 0.22499999403953552]
neonsign_G[0].rotation = [0, 0, -1.5682554162991507]
neonsign_G[0].optimize = 2
vintageposter_C[0].position = [4.501560688018799, 3.5999999046325684, 0.375]
vintageposter_C[0].rotation = [0, 0, -3.1390517323726885]
vintageposter_C[0].optimize = 2
lamp_C[0].position = [2.0199999809265137, 1.1799999475479126, 0.800000011920929]
lamp_C[0].rotation = [0, 0, 0.00942477746072377]
lamp_C[0].optimize = 2
plant_C[0].position = [1.100000023841858, 0.20000000298023224, 0.30000001192092896]
plant_C[0].rotation = [0, 0, 1.5802211042556205]
plant_C[0].optimize = 2
bookbench[0].position = [0.3400000035762787, 3.0999999046325684, 0.8949999809265137]
bookbench[0].rotation = [0, 0, 0.022791030181337935]
bookbench[0].optimize = 2
cup_C[0].position = [3.880000114440918, 2.7799999713897705, 1.0999999046325684]
cup_C[0].rotation = [0, 0, -3.118800984312999]
cup_C[0].optimize = 2
neonsign_H[0].position = [0.03614329919219017, 2.299999952316284, 0.2750000059604645]
neonsign_H[0].rotation = [0, 0, 0.0025409150842135757]
neonsign_H[0].optimize = 2
book_B[0].position = [4.309999942779541, 3.1600000858306885, 1.0649999380111694]
book_B[0].rotation = [0, 0, -3.118800984312999]
book_B[0].optimize = 2
floorlamp_F[0].position = [2.119999885559082, 3.880000114440918, 0.8100000023841858]
floorlamp_F[0].rotation = [0, 0, 0.00942477746072377]
floorlamp_F[0].optimize = 2
neonsign_E[0].position = [0.03614329919219017, 0.4599876403808594, 0.2750000059604645]
neonsign_E[0].rotation = [0, 0, 0.0025409150842135757]
neonsign_E[0].optimize = 2
cup_D[0].position = [4.340000152587891, 2.7799999713897705, 1.09499990940094]
cup_D[0].rotation = [0, 0, -3.118800984312999]
cup_D[0].optimize = 2
plant_B[0].position = [0.25, 3.799999952316284, 0.5249999761581421]
plant_B[0].rotation = [0, 0, 0.00942477746072377]
plant_B[0].optimize = 2
cup_G[0].position = [3.880000114440918, 4.019999980926514, 1.0999999046325684]
cup_G[0].rotation = [0, 0, -3.118800984312999]
cup_G[0].optimize = 2
magazine_E[0].position = [3.9200000762939453, 4.539999961853027, 1.0549999475479126]
magazine_E[0].rotation = [0, 0, -3.118800984312999]
magazine_E[0].optimize = 2
poster_F[0].position = [4.501559734344482, 2.0250000953674316, 0.4000000059604645]
poster_F[0].rotation = [0, 0, -3.139051734217035]
poster_F[0].optimize = 2
plant_D[0].position = [1.649999976158142, 0.1899999976158142, 0.32499998807907104]
plant_D[0].rotation = [0, 0, 1.5802211042556205]
plant_D[0].optimize = 2
cupsidetable_B[0].position = [1.399999976158142, 2.380000114440918, 0.5649999976158142]
cupsidetable_B[0].rotation = [0, 0, 0.02279109852594279]
cupsidetable_B[0].optimize = 2
plant_F[0].position = [2.700000047683716, 4.800000190734863, 0.30000001192092896]
plant_F[0].rotation = [0, 0, -1.5613715493341729]
plant_F[0].optimize = 2
stool_A[0].position = [3.25, 2.6500000953674316, 0.36000001430511475]
stool_A[0].rotation = [0, 0, 0.0157079639172164]
stool_A[0].optimize = 2
sodafountain[0].position = [3.299999952316284, 0.30114245414733887, 0.7250000238418579]
sodafountain[0].rotation = [0, 0, 1.5733372418791103]
sodafountain[0].optimize = 2
magazinebench_B[0].position = [0.3400000035762787, 2.319999933242798, 0.8849999904632568]
magazinebench_B[0].rotation = [0, 0, 0.022791030181337935]
magazinebench_B[0].optimize = 2
counter[0].position = [3.9546663761138916, 3.549999952316284, 0.5249999761581421]
counter[0].rotation = [0, 0, -2.9833973771105913]
counter[0].optimize = 2
cupsidetable_A[0].position = [1.0800000429153442, 2.380000114440918, 0.5699999928474426]
cupsidetable_A[0].rotation = [0, 0, 0.02279109852594279]
cupsidetable_A[0].optimize = 2
bench[0].position = [0.372018426656723, 2.549999952316284, 0.4399999976158142]
bench[0].rotation = [0, 0, 0.03676294487354017]
bench[0].optimize = 2
vintageposter_A[0].position = [0.30000001192092896, 5.001559734344482, 0.4000000059604645]
vintageposter_A[0].rotation = [0, 0, -1.5682554074221384]
vintageposter_A[0].optimize = 2
magazinebench_C[0].position = [0.3400000035762787, 2.7200000286102295, 0.8849999904632568]
magazinebench_C[0].rotation = [0, 0, 0.022791030181337935]
magazinebench_C[0].optimize = 2
poster_D[0].position = [4.501560688018799, 0.8999999761581421, 0.44999998807907104]
poster_D[0].rotation = [0, 0, -3.1390517332948615]
poster_D[0].optimize = 2
neonsign_C[0].position = [2.3299999237060547, 0.03627034276723862, 0.30000001192092896]
neonsign_C[0].rotation = [0, 0, 1.5733372406570116]
neonsign_C[0].optimize = 2
cashregister[0].position = [4.150000095367432, 3.5799999237060547, 1.2400000095367432]
cashregister[0].rotation = [0, 0, -3.118800984312999]
cashregister[0].optimize = 2
neonsign_F[0].position = [0.03120683692395687, 1.375, 0.25]
neonsign_F[0].rotation = [0, 0, 0.002540914784288029]
neonsign_F[0].optimize = 2
coatrack[0].position = [2.1500000953674316, 4.724302291870117, 0.875]
coatrack[0].rotation = [0, 0, -1.5682554074221384]
coatrack[0].optimize = 2
jukebox[0].position = [0.29107895493507385, 0.6499999761581421, 0.7250000238418579]
jukebox[0].rotation = [0, 0, 0.002540916928559797]
jukebox[0].optimize = 2

