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
    Wall(corner1=[5.00, 0.00, 0.00], corner2=[5.00, 4.50, 0.00]),
    Wall(corner1=[5.00, 4.50, 0.00], corner2=[0.00, 4.50, 0.00]),
    Wall(corner1=[0.00, 4.50, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[5.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
magazine_A = Assets(description="A vintage magazine with a pastel pink cover, thin rectangular stack, slightly textured paper surface and crisp edges", size=[0.30, 0.22, 0.01], placements=[AssetInstance() for _ in range(1)])
neonsign_A = Assets(description="A single piece of thin and upright neon sign with pastel pink lettering on a chrome frame, glowing tube design", size=[0.08, 0.90, 0.40], placements=[AssetInstance() for _ in range(1)])
walllamp_A = Assets(description="A single piece of thin and upright retro wall lamp with a chrome arm and pastel teal shade, curved glass diffuser", size=[0.28, 0.22, 0.32], placements=[AssetInstance() for _ in range(1)])
plant_A = Assets(description="A pastel potted plant in a low, squat ceramic pot painted pastel pink, featuring a rounded pot and a compact, bushy foliage silhouette.", size=[0.42, 0.42, 0.55], placements=[AssetInstance() for _ in range(1)])
plate_A = Assets(description="A round pastel teal plate with a thin chrome edge, smooth glazed surface, slightly raised rim, classic 1950s diner look", size=[0.24, 0.24, 0.02], placements=[AssetInstance() for _ in range(1)])
jukebox = Assets(description="A retro 1950s jukebox with a rectangular chrome frame, pastel pink enamel panels, and rounded glass front, featuring a curved top and chrome accent trim", size=[0.55, 0.85, 1.45], placements=[AssetInstance() for _ in range(1)])
neonsign_B = Assets(description="A single piece of thin and upright neon sign with a curved script in pastel teal, chrome border, and a glowing tube, embodying 1950s diner vibe.", size=[0.08, 1.05, 0.45], placements=[AssetInstance() for _ in range(1)])
magazine_B = Assets(description="A vintage magazine with a pastel pink cover, thin rectangular stack, slightly textured paper surface and crisp edges", size=[0.30, 0.22, 0.01], placements=[AssetInstance() for _ in range(1)])
plant_B = Assets(description="A pastel‑colored potted plant with a squat cylindrical pot, smooth matte finish, and a small rounded foliage top, giving a soft retro vibe.", size=[0.30, 0.30, 0.42], placements=[AssetInstance() for _ in range(1)])
napkinholder = Assets(description="A chrome napkin holder with pastel pink and teal accents, elongated rectangular form, sleek polished metal body and a shallow tray for napkins", size=[0.08, 0.18, 0.12], placements=[AssetInstance() for _ in range(1)])
succulent_A = Assets(description="A small potted succulent with a rounded rosette of fleshy leaves, set in a pastel ceramic pot (one pink, one teal) with a smooth matte texture", size=[0.16, 0.16, 0.20], placements=[AssetInstance() for _ in range(1)])
neonsign_C = Assets(description="A single piece of thin and upright neon sign with a bright pastel pink script on a chrome frame, glowing softly and casting a colorful hue", size=[0.08, 1.10, 0.48], placements=[AssetInstance() for _ in range(1)])
plant_C = Assets(description="A pastel‑colored potted plant with a squat round pot, smooth matte finish, and a compact leafy top, embodying a soft retro aesthetic", size=[0.34, 0.34, 0.46], placements=[AssetInstance() for _ in range(1)])
menu_A = Assets(description="A single piece of thin and upright vintage menu, rectangular paper with pastel pink and teal borders, chrome foil lettering and a slightly curled top edge for a retro look", size=[0.06, 0.18, 0.28], placements=[AssetInstance() for _ in range(1)])
stool_A = Assets(description="A pastel vinyl stool with a cylindrical seat, slender chrome legs, and a slightly curved backrest; each stool has a unique color (pink or teal) and a glossy finish", size=[0.48, 0.45, 1.00], placements=[AssetInstance() for _ in range(1)])
cup_A = Assets(description="A pastel pink cup with a smooth cylindrical shape, glossy finish, and a thin chrome rim encircling the opening, reminiscent of 1950s diner tableware.", size=[0.09, 0.11, 0.10], placements=[AssetInstance() for _ in range(1)])
neonsign_D = Assets(description="A single piece of thin and upright vintage neon sign with pastel teal lettering, rectangular frame, chrome edging and a glowing tube interior", size=[0.08, 0.90, 0.42], placements=[AssetInstance() for _ in range(1)])
refrigerator_A = Assets(description="A vintage refrigerator with a rectangular boxy shape, chrome accents on the doors, pastel teal panels, and a rounded top edge that evokes 1950s diner style", size=[0.72, 0.76, 1.75], placements=[AssetInstance() for _ in range(1)])
plant_D = Assets(description="A pastel‑colored potted plant with a squat round pot, smooth matte finish, and a compact leafy top, embodying a soft retro aesthetic", size=[0.34, 0.34, 0.46], placements=[AssetInstance() for _ in range(1)])
stool_B = Assets(description="A pastel vinyl stool with a cylindrical seat, slender chrome legs, and a slightly curved backrest; each stool has a unique color (pink or teal) and a glossy finish", size=[0.48, 0.45, 1.00], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="A retro wall lamp with a slim rectangular chrome housing, pastel pink glass shade, and a curved arm, typical of mid‑century diner lighting.", size=[0.26, 0.20, 0.30], placements=[AssetInstance() for _ in range(1)])
cup_B = Assets(description="A pastel pink cup with a smooth cylindrical shape, glossy finish, and a thin chrome rim encircling the opening, reminiscent of 1950s diner tableware.", size=[0.09, 0.11, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_E = Assets(description="A pastel‑colored potted plant with a squat cylindrical pot, smooth matte finish, and a small rounded foliage top, giving a soft retro vibe.", size=[0.30, 0.30, 0.42], placements=[AssetInstance() for _ in range(1)])
neonsign_E = Assets(description="A single piece of thin and upright vintage neon sign with pastel teal lettering, rectangular frame, chrome edging and a glowing tube interior", size=[0.08, 0.90, 0.42], placements=[AssetInstance() for _ in range(1)])
walllamp_B = Assets(description="A retro wall lamp with a chrome base, pastel teal glass shade, and a curved arm that tilts outward, emitting a warm nostalgic glow", size=[0.30, 0.24, 0.30], placements=[AssetInstance() for _ in range(1)])
plant_F = Assets(description="A pastel pink potted plant with a squat cylindrical pot, chrome rim, and a compact bushy foliage that adds a soft pop of color", size=[0.32, 0.32, 0.45], placements=[AssetInstance() for _ in range(1)])
plant_G = Assets(description="A pastel pink potted plant with a squat cylindrical pot, chrome rim, and a compact bushy foliage that adds a soft pop of color", size=[0.32, 0.32, 0.45], placements=[AssetInstance() for _ in range(1)])
plant_H = Assets(description="A pastel‑colored potted plant with a squat cylindrical pot, smooth matte finish, and a small rounded foliage top, giving a soft retro vibe.", size=[0.30, 0.30, 0.42], placements=[AssetInstance() for _ in range(1)])
walllamp_C = Assets(description="A single piece of thin and upright retro wall lamp with a chrome arm and pastel teal shade, curved glass diffuser", size=[0.28, 0.22, 0.32], placements=[AssetInstance() for _ in range(1)])
stool_C = Assets(description="A pastel vinyl stool with a cylindrical seat, slender chrome legs, and a slightly curved backrest; each stool has a unique color (pink or teal) and a glossy finish", size=[0.48, 0.45, 1.00], placements=[AssetInstance() for _ in range(1)])
stool_D = Assets(description="A pastel vinyl stool with a cylindrical seat, slender chrome legs, and a slightly curved backrest; each stool has a unique color (pink or teal) and a glossy finish", size=[0.48, 0.45, 1.00], placements=[AssetInstance() for _ in range(1)])
plant_I = Assets(description="A small potted plant in a pastel teal ceramic pot, compact rounded pot shape, leafy green foliage and a short sturdy stem", size=[0.32, 0.32, 0.48], placements=[AssetInstance() for _ in range(1)])
plant_J = Assets(description="A pastel potted plant in a low, squat ceramic pot painted pastel pink, featuring a rounded pot and a compact, bushy foliage silhouette.", size=[0.42, 0.42, 0.55], placements=[AssetInstance() for _ in range(1)])
menu_B = Assets(description="A thin rectangular vintage menu with pastel teal lettering on a chrome‑bordered paper, slightly curved top edge", size=[0.06, 0.18, 0.28], placements=[AssetInstance() for _ in range(1)])
cup_C = Assets(description="A small circular cup with a smooth pastel pink ceramic body and a thin chrome rim, glossy finish, low‑profile handle on the side", size=[0.09, 0.12, 0.09], placements=[AssetInstance() for _ in range(1)])
saltshaker_A = Assets(description="A chrome saltshaker with a sleek cylindrical body, polished finish, and a pastel pink top knob, reflecting mid‑century diner aesthetics.", size=[0.05, 0.05, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_K = Assets(description="A pastel potted plant in a low, squat ceramic pot painted pastel pink, featuring a rounded pot and a compact, bushy foliage silhouette.", size=[0.42, 0.42, 0.55], placements=[AssetInstance() for _ in range(1)])
walllamp_D = Assets(description="A retro wall lamp with a compact rectangular shape, pastel teal shade, chrome base, 1950s diner style", size=[0.20, 0.22, 0.26], placements=[AssetInstance() for _ in range(1)])
plant_L = Assets(description="A pastel pink potted plant with a rounded ceramic pot, soft foliage, low‑profile squat shape, chrome‑trimmed base", size=[0.36, 0.36, 0.48], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="A retro wall lamp with a slim rectangular chrome housing, pastel pink glass shade, and a curved arm, typical of mid‑century diner lighting.", size=[0.26, 0.20, 0.30], placements=[AssetInstance() for _ in range(1)])
neonsign_F = Assets(description="A single piece of thin and upright neon sign with a pastel pink outline, chrome‑styled lettering, and a subtle glowing effect reminiscent of 1950s diners.", size=[0.08, 0.95, 0.42], placements=[AssetInstance() for _ in range(1)])
neonsign_G = Assets(description="A single piece of thin and upright neon sign with a curved script in pastel teal, chrome border, and a glowing tube, embodying 1950s diner vibe.", size=[0.08, 1.05, 0.45], placements=[AssetInstance() for _ in range(1)])
neonsign_H = Assets(description="A single piece of thin and upright neon sign with pastel pink lettering, chrome trim, glowing illumination, 1950s diner style", size=[0.08, 0.90, 0.40], placements=[AssetInstance() for _ in range(1)])
plant_M = Assets(description="A pastel pink potted plant with a rounded ceramic pot, soft foliage, low‑profile squat shape, chrome‑trimmed base", size=[0.36, 0.36, 0.48], placements=[AssetInstance() for _ in range(1)])
cup_D = Assets(description="A pastel-colored ceramic cup with a glossy chrome rim, rounded cylindrical shape, slightly squat profile and a smooth matte finish", size=[0.10, 0.12, 0.09], placements=[AssetInstance() for _ in range(1)])
walllamp_E = Assets(description="A retro wall lamp with a chrome base, pastel teal glass shade, and a curved arm that tilts outward, emitting a warm nostalgic glow", size=[0.30, 0.24, 0.30], placements=[AssetInstance() for _ in range(1)])
saltshaker_B = Assets(description="A chrome saltshaker with a compact cylindrical shape, polished metal finish, 1950s diner style", size=[0.05, 0.05, 0.09], placements=[AssetInstance() for _ in range(1)])
magazine_C = Assets(description="A vintage magazine with a pastel pink cover, thin rectangular stack, slightly textured paper surface and crisp edges", size=[0.30, 0.22, 0.01], placements=[AssetInstance() for _ in range(1)])
cup_E = Assets(description="A pastel pink ceramic cup with a smooth curved body, chrome rim, and a small handle, featuring a glossy finish and a subtle retro emboss pattern", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
vase_A = Assets(description="A pastel pink ceramic vase with a tall slender cylindrical body, subtle flared rim, glossy finish and a small decorative chrome accent band near the top", size=[0.20, 0.20, 0.70], placements=[AssetInstance() for _ in range(1)])
menu_C = Assets(description="A single piece of thin and upright vintage menu, rectangular paper with pastel pink and teal borders, chrome foil lettering and a slightly curled top edge for a retro look", size=[0.06, 0.18, 0.28], placements=[AssetInstance() for _ in range(1)])
plant_N = Assets(description="A pastel potted plant in a low, squat ceramic pot painted pastel pink, featuring a rounded pot and a compact, bushy foliage silhouette.", size=[0.42, 0.42, 0.55], placements=[AssetInstance() for _ in range(1)])
neonsign_I = Assets(description="A single piece of thin and upright neon sign with a curved script, pastel pink glow, chrome outline and a retro diner motif", size=[0.08, 1.05, 0.45], placements=[AssetInstance() for _ in range(1)])
walllamp_F = Assets(description="A retro wall lamp with a compact rectangular shape, pastel teal shade, chrome base, 1950s diner style", size=[0.20, 0.22, 0.26], placements=[AssetInstance() for _ in range(1)])
vase_B = Assets(description="A pastel pink ceramic vase with a tall slender cylindrical body, subtle flared rim, glossy finish and a small decorative chrome accent band near the top", size=[0.20, 0.20, 0.70], placements=[AssetInstance() for _ in range(1)])
walllamp_G = Assets(description="A retro wall lamp with a low‑slung rectangular shade, chrome base, pastel teal interior lighting and a sleek angular silhouette", size=[0.24, 0.30, 0.18], placements=[AssetInstance() for _ in range(1)])
saltshaker_C = Assets(description="A chrome saltshaker with a sleek cylindrical body, pastel pink top cap, and a small perforated lid that glints under light", size=[0.05, 0.05, 0.10], placements=[AssetInstance() for _ in range(1)])
vase_C = Assets(description="A pastel teal vase with an elegant elongated cylindrical shape, glossy finish, and a subtle chrome accent band near the rim, reflecting 1950s diner décor.", size=[0.18, 0.18, 0.72], placements=[AssetInstance() for _ in range(1)])
plant_O = Assets(description="A pastel‑colored potted plant with a squat cylindrical pot, smooth matte finish, and a small rounded foliage top, giving a soft retro vibe.", size=[0.30, 0.30, 0.42], placements=[AssetInstance() for _ in range(1)])
refrigerator_B = Assets(description="A vintage rectangular refrigerator with chrome accents on the doors, pastel teal panels, rounded top corners, glossy finish", size=[0.72, 0.76, 1.75], placements=[AssetInstance() for _ in range(1)])
plant_P = Assets(description="A pastel‑colored potted plant with a squat round pot, smooth matte finish, and a compact leafy top, embodying a soft retro aesthetic", size=[0.34, 0.34, 0.46], placements=[AssetInstance() for _ in range(1)])
walllamp_H = Assets(description="A retro wall lamp with a slim rectangular chrome base, a curved pastel teal shade, and a single bulb that casts a warm glow, typical of mid‑century diner lighting.", size=[0.28, 0.24, 0.28], placements=[AssetInstance() for _ in range(1)])
vase_D = Assets(description="A pastel teal vase with an elegant elongated cylindrical shape, glossy finish, and a subtle chrome accent band near the rim, reflecting 1950s diner décor.", size=[0.18, 0.18, 0.72], placements=[AssetInstance() for _ in range(1)])
plant_Q = Assets(description="A small potted plant in a pastel teal ceramic pot, compact rounded pot shape, leafy green foliage and a short sturdy stem", size=[0.32, 0.32, 0.48], placements=[AssetInstance() for _ in range(1)])
neonsign_J = Assets(description="A single piece of thin and upright neon sign with a curved script, pastel pink glow, chrome outline and a retro diner motif", size=[0.08, 1.05, 0.45], placements=[AssetInstance() for _ in range(1)])
neonsign_K = Assets(description="A single piece of thin and upright neon sign with pastel pink lettering, chrome trim, glowing illumination, 1950s diner style", size=[0.08, 0.90, 0.40], placements=[AssetInstance() for _ in range(1)])
counter = Assets(description="A chrome‑edged diner counter with a long rectangular shape, pastel teal base and pink countertop, sleek straight edges and a glossy finish", size=[0.75, 3.20, 1.05], placements=[AssetInstance() for _ in range(1)])
plate_B = Assets(description="A pastel teal ceramic plate with a flat circular shape, chrome edge trim, and a faint speckled texture that catches light, giving a vintage diner feel", size=[0.24, 0.24, 0.02], placements=[AssetInstance() for _ in range(1)])
succulent_B = Assets(description="A small potted succulent with a rounded rosette of fleshy leaves, set in a pastel ceramic pot (one pink, one teal) with a smooth matte texture", size=[0.16, 0.16, 0.20], placements=[AssetInstance() for _ in range(1)])
saltshaker_D = Assets(description="A small cylindrical salt shaker with a polished chrome body and pastel pink detailing, smooth rounded top", size=[0.05, 0.05, 0.09], placements=[AssetInstance() for _ in range(1)])
menu_D = Assets(description="A vintage diner menu board with a thin rectangular shape, pastel teal background, chrome border and slightly worn paper texture, giving it an authentic retro look", size=[0.07, 0.22, 0.32], placements=[AssetInstance() for _ in range(1)])
peppergrinder_A = Assets(description="A chrome pepper grinder with a slender cylindrical silhouette, pastel teal base, and a twist top, styled after 1950s diner accessories.", size=[0.06, 0.06, 0.18], placements=[AssetInstance() for _ in range(1)])
menu_E = Assets(description="A vintage diner menu board with a thin rectangular shape, pastel teal background, chrome border and slightly worn paper texture, giving it an authentic retro look", size=[0.07, 0.22, 0.32], placements=[AssetInstance() for _ in range(1)])
walllamp_I = Assets(description="A retro wall lamp with a slim rectangular chrome base, a curved pastel teal shade, and a single bulb that casts a warm glow, typical of mid‑century diner lighting.", size=[0.28, 0.24, 0.28], placements=[AssetInstance() for _ in range(1)])
neonsign_L = Assets(description="A single piece of thin and upright neon sign with a pastel pink outline, chrome‑styled lettering, and a subtle glowing effect reminiscent of 1950s diners.", size=[0.08, 0.95, 0.42], placements=[AssetInstance() for _ in range(1)])
plant_R = Assets(description="A pastel‑colored potted plant with a squat round pot, smooth matte finish, and a compact leafy top, embodying a soft retro aesthetic", size=[0.34, 0.34, 0.46], placements=[AssetInstance() for _ in range(1)])
walllamp_J = Assets(description="A retro wall lamp with a low‑slung rectangular shade, chrome base, pastel teal interior lighting and a sleek angular silhouette", size=[0.24, 0.30, 0.18], placements=[AssetInstance() for _ in range(1)])
peppergrinder_B = Assets(description="A compact cylindrical pepper grinder with a chrome base and pastel teal accents, sleek tapered shape", size=[0.06, 0.06, 0.16], placements=[AssetInstance() for _ in range(1)])
neonsign_M = Assets(description="A single piece of thin and upright neon sign with pastel pink lettering on a chrome frame, glowing tube design", size=[0.08, 0.90, 0.40], placements=[AssetInstance() for _ in range(1)])
cup_F = Assets(description="A pastel-colored ceramic cup with a glossy chrome rim, rounded cylindrical shape, slightly squat profile and a smooth matte finish", size=[0.10, 0.12, 0.09], placements=[AssetInstance() for _ in range(1)])
neonsign_N = Assets(description="A single piece of thin and upright neon sign with a bright pastel pink script on a chrome frame, glowing softly and casting a colorful hue", size=[0.08, 1.10, 0.48], placements=[AssetInstance() for _ in range(1)])

magazine_A[0].instance_id = 'magazine_A_0'
neonsign_A[0].instance_id = 'neonsign_A_0'
walllamp_A[0].instance_id = 'walllamp_A_0'
plant_A[0].instance_id = 'plant_A_0'
plate_A[0].instance_id = 'plate_A_0'
jukebox[0].instance_id = 'jukebox_0'
neonsign_B[0].instance_id = 'neonsign_B_0'
magazine_B[0].instance_id = 'magazine_B_0'
plant_B[0].instance_id = 'plant_B_0'
napkinholder[0].instance_id = 'napkinholder_0'
succulent_A[0].instance_id = 'succulent_A_0'
neonsign_C[0].instance_id = 'neonsign_C_0'
plant_C[0].instance_id = 'plant_C_0'
menu_A[0].instance_id = 'menu_A_0'
stool_A[0].instance_id = 'stool_A_0'
cup_A[0].instance_id = 'cup_A_0'
neonsign_D[0].instance_id = 'neonsign_D_0'
refrigerator_A[0].instance_id = 'refrigerator_A_0'
plant_D[0].instance_id = 'plant_D_0'
stool_B[0].instance_id = 'stool_B_0'
lamp_A[0].instance_id = 'lamp_A_0'
cup_B[0].instance_id = 'cup_B_0'
plant_E[0].instance_id = 'plant_E_0'
neonsign_E[0].instance_id = 'neonsign_E_0'
walllamp_B[0].instance_id = 'walllamp_B_0'
plant_F[0].instance_id = 'plant_F_0'
plant_G[0].instance_id = 'plant_G_0'
plant_H[0].instance_id = 'plant_H_0'
walllamp_C[0].instance_id = 'walllamp_C_0'
stool_C[0].instance_id = 'stool_C_0'
stool_D[0].instance_id = 'stool_D_0'
plant_I[0].instance_id = 'plant_I_0'
plant_J[0].instance_id = 'plant_J_0'
menu_B[0].instance_id = 'menu_B_0'
cup_C[0].instance_id = 'cup_C_0'
saltshaker_A[0].instance_id = 'saltshaker_A_0'
plant_K[0].instance_id = 'plant_K_0'
walllamp_D[0].instance_id = 'walllamp_D_0'
plant_L[0].instance_id = 'plant_L_0'
lamp_B[0].instance_id = 'lamp_B_0'
neonsign_F[0].instance_id = 'neonsign_F_0'
neonsign_G[0].instance_id = 'neonsign_G_0'
neonsign_H[0].instance_id = 'neonsign_H_0'
plant_M[0].instance_id = 'plant_M_0'
cup_D[0].instance_id = 'cup_D_0'
walllamp_E[0].instance_id = 'walllamp_E_0'
saltshaker_B[0].instance_id = 'saltshaker_B_0'
magazine_C[0].instance_id = 'magazine_C_0'
cup_E[0].instance_id = 'cup_E_0'
vase_A[0].instance_id = 'vase_A_0'
menu_C[0].instance_id = 'menu_C_0'
plant_N[0].instance_id = 'plant_N_0'
neonsign_I[0].instance_id = 'neonsign_I_0'
walllamp_F[0].instance_id = 'walllamp_F_0'
vase_B[0].instance_id = 'vase_B_0'
walllamp_G[0].instance_id = 'walllamp_G_0'
saltshaker_C[0].instance_id = 'saltshaker_C_0'
vase_C[0].instance_id = 'vase_C_0'
plant_O[0].instance_id = 'plant_O_0'
refrigerator_B[0].instance_id = 'refrigerator_B_0'
plant_P[0].instance_id = 'plant_P_0'
walllamp_H[0].instance_id = 'walllamp_H_0'
vase_D[0].instance_id = 'vase_D_0'
plant_Q[0].instance_id = 'plant_Q_0'
neonsign_J[0].instance_id = 'neonsign_J_0'
neonsign_K[0].instance_id = 'neonsign_K_0'
counter[0].instance_id = 'counter_0'
plate_B[0].instance_id = 'plate_B_0'
succulent_B[0].instance_id = 'succulent_B_0'
saltshaker_D[0].instance_id = 'saltshaker_D_0'
menu_D[0].instance_id = 'menu_D_0'
peppergrinder_A[0].instance_id = 'peppergrinder_A_0'
menu_E[0].instance_id = 'menu_E_0'
walllamp_I[0].instance_id = 'walllamp_I_0'
neonsign_L[0].instance_id = 'neonsign_L_0'
plant_R[0].instance_id = 'plant_R_0'
walllamp_J[0].instance_id = 'walllamp_J_0'
peppergrinder_B[0].instance_id = 'peppergrinder_B_0'
neonsign_M[0].instance_id = 'neonsign_M_0'
cup_F[0].instance_id = 'cup_F_0'
neonsign_N[0].instance_id = 'neonsign_N_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

magazine_A[0].position = [1.7269255471525058, 4.102741510844335, 0.005]
magazine_A[0].rotation = [0, 0, 0]
neonsign_A[0].position = [4.084535877774276, 0.06778198075491199, 0.2]
neonsign_A[0].rotation = [0, 0, 0]
walllamp_A[0].position = [1.2815930477277848, 1.9924709301913284, 0.16]
walllamp_A[0].rotation = [0, 0, 0]
plant_A[0].position = [3.6860426631338568, 4.3956476751983224, 0.275]
plant_A[0].rotation = [0, 0, 0]
plate_A[0].position = [3.397001214213317, 3.4753054656856213, 0.01]
plate_A[0].rotation = [0, 0, 0]
jukebox[0].position = [3.0707699421884156, 0.656133037408007, 0.725]
jukebox[0].rotation = [0, 0, 0]
neonsign_B[0].position = [3.3682559706620143, 4.09047552764951, 0.225]
neonsign_B[0].rotation = [0, 0, 0]
magazine_B[0].position = [2.510608997160098, 2.5914323451318086, 0.005]
magazine_B[0].rotation = [0, 0, 0]
plant_B[0].position = [1.5292818371549481, 2.0771255168307294, 0.21]
plant_B[0].rotation = [0, 0, 0]
napkinholder[0].position = [4.8893327997807585, 4.468499866956195, 0.06]
napkinholder[0].rotation = [0, 0, 0]
succulent_A[0].position = [0.5822255462650677, 1.317014898730739, 0.1]
succulent_A[0].rotation = [0, 0, 0]
neonsign_C[0].position = [1.615133073982769, 1.3165559610337794, 0.24]
neonsign_C[0].rotation = [0, 0, 0]
plant_C[0].position = [1.6132371144194968, 3.7316877166752978, 0.23]
plant_C[0].rotation = [0, 0, 0]
menu_A[0].position = [1.121152969847049, 3.3801690158821414, 0.14]
menu_A[0].rotation = [0, 0, 0]
stool_A[0].position = [2.6059511137276847, 3.9664868036620504, 0.5]
stool_A[0].rotation = [0, 0, 0]
cup_A[0].position = [3.6469748745043837, 4.309004718103033, 0.05]
cup_A[0].rotation = [0, 0, 0]
neonsign_D[0].position = [4.10886539537977, 1.1663291703812557, 0.21]
neonsign_D[0].rotation = [0, 0, 0]
refrigerator_A[0].position = [1.7077006461155486, 1.3206005951860234, 0.875]
refrigerator_A[0].rotation = [0, 0, 0]
plant_D[0].position = [1.63118207754211, 0.9466879700139492, 0.23]
plant_D[0].rotation = [0, 0, 0]
stool_B[0].position = [0.216741321678377, 0.8561208076192821, 0.5]
stool_B[0].rotation = [0, 0, 0]
lamp_A[0].position = [3.0681345278425214, 1.4633955462797412, 0.15]
lamp_A[0].rotation = [0, 0, 0]
cup_B[0].position = [2.8291196417199522, 0.8183638158229442, 0.05]
cup_B[0].rotation = [0, 0, 0]
plant_E[0].position = [3.280023443407572, 4.050557560407466, 0.21]
plant_E[0].rotation = [0, 0, 0]
neonsign_E[0].position = [0.6073081726204688, 3.319096209244985, 0.21]
neonsign_E[0].rotation = [0, 0, 0]
walllamp_B[0].position = [2.5839090170323087, 0.014933786079984912, 0.15]
walllamp_B[0].rotation = [0, 0, 0]
plant_F[0].position = [1.4842554562694583, 3.8744856130927534, 0.225]
plant_F[0].rotation = [0, 0, 0]
plant_G[0].position = [4.106476726379458, 0.022106219927926107, 0.225]
plant_G[0].rotation = [0, 0, 0]
plant_H[0].position = [2.258739810669248, 2.003585960471209, 0.21]
plant_H[0].rotation = [0, 0, 0]
walllamp_C[0].position = [2.315859134278189, 3.5867926345890204, 0.16]
walllamp_C[0].rotation = [0, 0, 0]
stool_C[0].position = [0.639581942856034, 4.1402645445943556, 0.5]
stool_C[0].rotation = [0, 0, 0]
stool_D[0].position = [4.0918697468854495, 3.9090422080794047, 0.5]
stool_D[0].rotation = [0, 0, 0]
plant_I[0].position = [1.0060156834921874, 4.430049419840916, 0.24]
plant_I[0].rotation = [0, 0, 0]
plant_J[0].position = [4.712218303217448, 3.3712214885043847, 0.275]
plant_J[0].rotation = [0, 0, 0]
menu_B[0].position = [4.176448308728194, 0.08275214847029622, 0.14]
menu_B[0].rotation = [0, 0, 0]
cup_C[0].position = [2.0947686366415317, 3.049689295920747, 0.045]
cup_C[0].rotation = [0, 0, 0]
saltshaker_A[0].position = [4.272192959046357, 0.6324006608985226, 0.05]
saltshaker_A[0].rotation = [0, 0, 0]
plant_K[0].position = [2.7649544864199127, 2.9842953335040123, 0.275]
plant_K[0].rotation = [0, 0, 0]
walllamp_D[0].position = [4.296143757730874, 1.2280232158244806, 0.13]
walllamp_D[0].rotation = [0, 0, 0]
plant_L[0].position = [3.2833036966279816, 1.583186891831137, 0.24]
plant_L[0].rotation = [0, 0, 0]
lamp_B[0].position = [2.063867586058926, 1.3138274005640524, 0.15]
lamp_B[0].rotation = [0, 0, 0]
neonsign_F[0].position = [0.8679077753963466, 3.9248202713289237, 0.21]
neonsign_F[0].rotation = [0, 0, 0]
neonsign_G[0].position = [2.7926067658349636, 2.022595213646437, 0.225]
neonsign_G[0].rotation = [0, 0, 0]
neonsign_H[0].position = [0.5146471890640891, 2.0794555590921973, 0.2]
neonsign_H[0].rotation = [0, 0, 0]
plant_M[0].position = [2.4035873704005106, 1.6187926308768947, 0.24]
plant_M[0].rotation = [0, 0, 0]
cup_D[0].position = [2.210809291243125, 2.8747376307934798, 0.045]
cup_D[0].rotation = [0, 0, 0]
walllamp_E[0].position = [1.2969171672044761, 3.384589787634277, 0.15]
walllamp_E[0].rotation = [0, 0, 0]
saltshaker_B[0].position = [3.6139351912580624, 3.553406856409816, 0.045]
saltshaker_B[0].rotation = [0, 0, 0]
magazine_C[0].position = [4.070231825727367, 2.0397731336679903, 0.005]
magazine_C[0].rotation = [0, 0, 0]
cup_E[0].position = [3.8463659591964507, 3.491744768606712, 0.05]
cup_E[0].rotation = [0, 0, 0]
vase_A[0].position = [4.8691952883863445, 0.8954233021230382, 0.35]
vase_A[0].rotation = [0, 0, 0]
menu_C[0].position = [0.49916238620929365, 1.1833973696567566, 0.14]
menu_C[0].rotation = [0, 0, 0]
plant_N[0].position = [0.5835204801209098, 0.9894256427112813, 0.275]
plant_N[0].rotation = [0, 0, 0]
neonsign_I[0].position = [1.1852459917172435, 1.5359559868659085, 0.225]
neonsign_I[0].rotation = [0, 0, 0]
walllamp_F[0].position = [3.5812840834219872, 2.5363683034514866, 0.13]
walllamp_F[0].rotation = [0, 0, 0]
vase_B[0].position = [2.6036145406731874, 3.7136137860828407, 0.35]
vase_B[0].rotation = [0, 0, 0]
walllamp_G[0].position = [3.2402222976705444, 2.6058885975793604, 0.09]
walllamp_G[0].rotation = [0, 0, 0]
saltshaker_C[0].position = [2.619056000631944, 3.8524328301886306, 0.05]
saltshaker_C[0].rotation = [0, 0, 0]
vase_C[0].position = [3.6724490251862822, 3.4182975135266007, 0.36]
vase_C[0].rotation = [0, 0, 0]
plant_O[0].position = [4.398260173370804, 0.7791732648787444, 0.21]
plant_O[0].rotation = [0, 0, 0]
refrigerator_B[0].position = [3.8959991117314203, 3.5267419703262886, 0.875]
refrigerator_B[0].rotation = [0, 0, 0]
plant_P[0].position = [2.025582540883108, 4.009247004540359, 0.23]
plant_P[0].rotation = [0, 0, 0]
walllamp_H[0].position = [2.86670534432184, 1.985980303330035, 0.14]
walllamp_H[0].rotation = [0, 0, 0]
vase_D[0].position = [4.695092236563031, 1.5715653927844753, 0.36]
vase_D[0].rotation = [0, 0, 0]
plant_Q[0].position = [2.6195219466736743, 3.366919424019746, 0.24]
plant_Q[0].rotation = [0, 0, 0]
neonsign_J[0].position = [4.269897390423863, 1.9362365090898044, 0.225]
neonsign_J[0].rotation = [0, 0, 0]
neonsign_K[0].position = [1.910399600960495, 0.743676918525875, 0.2]
neonsign_K[0].rotation = [0, 0, 0]
counter[0].position = [3.8951557125138034, 3.0730982353943825, 0.525]
counter[0].rotation = [0, 0, 0]
plate_B[0].position = [4.260613347244108, 1.985715759059544, 0.01]
plate_B[0].rotation = [0, 0, 0]
succulent_B[0].position = [2.9309740653669207, 3.332488081959715, 0.1]
succulent_B[0].rotation = [0, 0, 0]
saltshaker_D[0].position = [0.3634318769300321, 3.565429788798611, 0.045]
saltshaker_D[0].rotation = [0, 0, 0]
menu_D[0].position = [1.4160452085560604, 1.0512202715630907, 0.16]
menu_D[0].rotation = [0, 0, 0]
peppergrinder_A[0].position = [0.7607004674262657, 2.8874056566640713, 0.09]
peppergrinder_A[0].rotation = [0, 0, 0]
menu_E[0].position = [2.3806259504137905, 2.750493908432593, 0.16]
menu_E[0].rotation = [0, 0, 0]
walllamp_I[0].position = [0.06577194881153492, 0.8226868746019036, 0.14]
walllamp_I[0].rotation = [0, 0, 0]
neonsign_L[0].position = [3.1224705210635113, 0.6299906125200656, 0.21]
neonsign_L[0].rotation = [0, 0, 0]
plant_R[0].position = [3.2379816570526945, 0.7477966080001324, 0.23]
plant_R[0].rotation = [0, 0, 0]
walllamp_J[0].position = [4.865148611732137, 2.9306768962754104, 0.09]
walllamp_J[0].rotation = [0, 0, 0]
peppergrinder_B[0].position = [0.8576518819451057, 2.9376791817952888, 0.08]
peppergrinder_B[0].rotation = [0, 0, 0]
neonsign_M[0].position = [1.8262194971025174, 1.3594059401953489, 0.2]
neonsign_M[0].rotation = [0, 0, 0]
cup_F[0].position = [1.085901885148478, 4.169623297651826, 0.045]
cup_F[0].rotation = [0, 0, 0]
neonsign_N[0].position = [4.460740200721463, 2.4439114084114086, 0.24]
neonsign_N[0].rotation = [0, 0, 0]
magazine_A[0].position = [1.7269255471525058, 4.102741510844335, 0.005]
magazine_A[0].rotation = [0, 0, 0]
neonsign_A[0].position = [4.084535877774276, 0.06778198075491199, 0.2]
neonsign_A[0].rotation = [0, 0, 0]
walllamp_A[0].position = [1.2815930477277848, 1.9924709301913284, 0.16]
walllamp_A[0].rotation = [0, 0, 0]
plant_A[0].position = [3.6860426631338568, 4.3956476751983224, 0.275]
plant_A[0].rotation = [0, 0, 0]
plate_A[0].position = [3.397001214213317, 3.4753054656856213, 0.01]
plate_A[0].rotation = [0, 0, 0]
jukebox[0].position = [3.0707699421884156, 0.656133037408007, 0.725]
jukebox[0].rotation = [0, 0, 0]
neonsign_B[0].position = [3.3682559706620143, 4.09047552764951, 0.225]
neonsign_B[0].rotation = [0, 0, 0]
magazine_B[0].position = [2.510608997160098, 2.5914323451318086, 0.005]
magazine_B[0].rotation = [0, 0, 0]
plant_B[0].position = [1.5292818371549481, 2.0771255168307294, 0.21]
plant_B[0].rotation = [0, 0, 0]
napkinholder[0].position = [4.8893327997807585, 4.468499866956195, 0.06]
napkinholder[0].rotation = [0, 0, 0]
succulent_A[0].position = [0.5822255462650677, 1.317014898730739, 0.1]
succulent_A[0].rotation = [0, 0, 0]
neonsign_C[0].position = [1.615133073982769, 1.3165559610337794, 0.24]
neonsign_C[0].rotation = [0, 0, 0]
plant_C[0].position = [1.6132371144194968, 3.7316877166752978, 0.23]
plant_C[0].rotation = [0, 0, 0]
menu_A[0].position = [1.121152969847049, 3.3801690158821414, 0.14]
menu_A[0].rotation = [0, 0, 0]
stool_A[0].position = [2.6059511137276847, 3.9664868036620504, 0.5]
stool_A[0].rotation = [0, 0, 0]
cup_A[0].position = [3.6469748745043837, 4.309004718103033, 0.05]
cup_A[0].rotation = [0, 0, 0]
neonsign_D[0].position = [4.10886539537977, 1.1663291703812557, 0.21]
neonsign_D[0].rotation = [0, 0, 0]
refrigerator_A[0].position = [1.7077006461155486, 1.3206005951860234, 0.875]
refrigerator_A[0].rotation = [0, 0, 0]
plant_D[0].position = [1.63118207754211, 0.9466879700139492, 0.23]
plant_D[0].rotation = [0, 0, 0]
stool_B[0].position = [0.216741321678377, 0.8561208076192821, 0.5]
stool_B[0].rotation = [0, 0, 0]
lamp_A[0].position = [3.0681345278425214, 1.4633955462797412, 0.15]
lamp_A[0].rotation = [0, 0, 0]
cup_B[0].position = [2.8291196417199522, 0.8183638158229442, 0.05]
cup_B[0].rotation = [0, 0, 0]
plant_E[0].position = [3.280023443407572, 4.050557560407466, 0.21]
plant_E[0].rotation = [0, 0, 0]
neonsign_E[0].position = [0.6073081726204688, 3.319096209244985, 0.21]
neonsign_E[0].rotation = [0, 0, 0]
walllamp_B[0].position = [2.5839090170323087, 0.014933786079984912, 0.15]
walllamp_B[0].rotation = [0, 0, 0]
plant_F[0].position = [1.4842554562694583, 3.8744856130927534, 0.225]
plant_F[0].rotation = [0, 0, 0]
plant_G[0].position = [4.106476726379458, 0.022106219927926107, 0.225]
plant_G[0].rotation = [0, 0, 0]
plant_H[0].position = [2.258739810669248, 2.003585960471209, 0.21]
plant_H[0].rotation = [0, 0, 0]
walllamp_C[0].position = [2.315859134278189, 3.5867926345890204, 0.16]
walllamp_C[0].rotation = [0, 0, 0]
stool_C[0].position = [0.639581942856034, 4.1402645445943556, 0.5]
stool_C[0].rotation = [0, 0, 0]
stool_D[0].position = [4.0918697468854495, 3.9090422080794047, 0.5]
stool_D[0].rotation = [0, 0, 0]
plant_I[0].position = [1.0060156834921874, 4.430049419840916, 0.24]
plant_I[0].rotation = [0, 0, 0]
plant_J[0].position = [4.712218303217448, 3.3712214885043847, 0.275]
plant_J[0].rotation = [0, 0, 0]
menu_B[0].position = [4.176448308728194, 0.08275214847029622, 0.14]
menu_B[0].rotation = [0, 0, 0]
cup_C[0].position = [2.0947686366415317, 3.049689295920747, 0.045]
cup_C[0].rotation = [0, 0, 0]
saltshaker_A[0].position = [4.272192959046357, 0.6324006608985226, 0.05]
saltshaker_A[0].rotation = [0, 0, 0]
plant_K[0].position = [2.7649544864199127, 2.9842953335040123, 0.275]
plant_K[0].rotation = [0, 0, 0]
walllamp_D[0].position = [4.296143757730874, 1.2280232158244806, 0.13]
walllamp_D[0].rotation = [0, 0, 0]
plant_L[0].position = [3.2833036966279816, 1.583186891831137, 0.24]
plant_L[0].rotation = [0, 0, 0]
lamp_B[0].position = [2.063867586058926, 1.3138274005640524, 0.15]
lamp_B[0].rotation = [0, 0, 0]
neonsign_F[0].position = [0.8679077753963466, 3.9248202713289237, 0.21]
neonsign_F[0].rotation = [0, 0, 0]
neonsign_G[0].position = [2.7926067658349636, 2.022595213646437, 0.225]
neonsign_G[0].rotation = [0, 0, 0]
neonsign_H[0].position = [0.5146471890640891, 2.0794555590921973, 0.2]
neonsign_H[0].rotation = [0, 0, 0]
plant_M[0].position = [2.4035873704005106, 1.6187926308768947, 0.24]
plant_M[0].rotation = [0, 0, 0]
cup_D[0].position = [2.210809291243125, 2.8747376307934798, 0.045]
cup_D[0].rotation = [0, 0, 0]
walllamp_E[0].position = [1.2969171672044761, 3.384589787634277, 0.15]
walllamp_E[0].rotation = [0, 0, 0]
saltshaker_B[0].position = [3.6139351912580624, 3.553406856409816, 0.045]
saltshaker_B[0].rotation = [0, 0, 0]
magazine_C[0].position = [4.070231825727367, 2.0397731336679903, 0.005]
magazine_C[0].rotation = [0, 0, 0]
cup_E[0].position = [3.8463659591964507, 3.491744768606712, 0.05]
cup_E[0].rotation = [0, 0, 0]
vase_A[0].position = [4.8691952883863445, 0.8954233021230382, 0.35]
vase_A[0].rotation = [0, 0, 0]
menu_C[0].position = [0.49916238620929365, 1.1833973696567566, 0.14]
menu_C[0].rotation = [0, 0, 0]
plant_N[0].position = [0.5835204801209098, 0.9894256427112813, 0.275]
plant_N[0].rotation = [0, 0, 0]
neonsign_I[0].position = [1.1852459917172435, 1.5359559868659085, 0.225]
neonsign_I[0].rotation = [0, 0, 0]
walllamp_F[0].position = [3.5812840834219872, 2.5363683034514866, 0.13]
walllamp_F[0].rotation = [0, 0, 0]
vase_B[0].position = [2.6036145406731874, 3.7136137860828407, 0.35]
vase_B[0].rotation = [0, 0, 0]
walllamp_G[0].position = [3.2402222976705444, 2.6058885975793604, 0.09]
walllamp_G[0].rotation = [0, 0, 0]
saltshaker_C[0].position = [2.619056000631944, 3.8524328301886306, 0.05]
saltshaker_C[0].rotation = [0, 0, 0]
vase_C[0].position = [3.6724490251862822, 3.4182975135266007, 0.36]
vase_C[0].rotation = [0, 0, 0]
plant_O[0].position = [4.398260173370804, 0.7791732648787444, 0.21]
plant_O[0].rotation = [0, 0, 0]
refrigerator_B[0].position = [3.8959991117314203, 3.5267419703262886, 0.875]
refrigerator_B[0].rotation = [0, 0, 0]
plant_P[0].position = [2.025582540883108, 4.009247004540359, 0.23]
plant_P[0].rotation = [0, 0, 0]
walllamp_H[0].position = [2.86670534432184, 1.985980303330035, 0.14]
walllamp_H[0].rotation = [0, 0, 0]
vase_D[0].position = [4.695092236563031, 1.5715653927844753, 0.36]
vase_D[0].rotation = [0, 0, 0]
plant_Q[0].position = [2.6195219466736743, 3.366919424019746, 0.24]
plant_Q[0].rotation = [0, 0, 0]
neonsign_J[0].position = [4.269897390423863, 1.9362365090898044, 0.225]
neonsign_J[0].rotation = [0, 0, 0]
neonsign_K[0].position = [1.910399600960495, 0.743676918525875, 0.2]
neonsign_K[0].rotation = [0, 0, 0]
counter[0].position = [3.8951557125138034, 3.0730982353943825, 0.525]
counter[0].rotation = [0, 0, 0]
plate_B[0].position = [4.260613347244108, 1.985715759059544, 0.01]
plate_B[0].rotation = [0, 0, 0]
succulent_B[0].position = [2.9309740653669207, 3.332488081959715, 0.1]
succulent_B[0].rotation = [0, 0, 0]
saltshaker_D[0].position = [0.3634318769300321, 3.565429788798611, 0.045]
saltshaker_D[0].rotation = [0, 0, 0]
menu_D[0].position = [1.4160452085560604, 1.0512202715630907, 0.16]
menu_D[0].rotation = [0, 0, 0]
peppergrinder_A[0].position = [0.7607004674262657, 2.8874056566640713, 0.09]
peppergrinder_A[0].rotation = [0, 0, 0]
menu_E[0].position = [2.3806259504137905, 2.750493908432593, 0.16]
menu_E[0].rotation = [0, 0, 0]
walllamp_I[0].position = [0.06577194881153492, 0.8226868746019036, 0.14]
walllamp_I[0].rotation = [0, 0, 0]
neonsign_L[0].position = [3.1224705210635113, 0.6299906125200656, 0.21]
neonsign_L[0].rotation = [0, 0, 0]
plant_R[0].position = [3.2379816570526945, 0.7477966080001324, 0.23]
plant_R[0].rotation = [0, 0, 0]
walllamp_J[0].position = [4.865148611732137, 2.9306768962754104, 0.09]
walllamp_J[0].rotation = [0, 0, 0]
peppergrinder_B[0].position = [0.8576518819451057, 2.9376791817952888, 0.08]
peppergrinder_B[0].rotation = [0, 0, 0]
neonsign_M[0].position = [1.8262194971025174, 1.3594059401953489, 0.2]
neonsign_M[0].rotation = [0, 0, 0]
cup_F[0].position = [1.085901885148478, 4.169623297651826, 0.045]
cup_F[0].rotation = [0, 0, 0]
neonsign_N[0].position = [4.460740200721463, 2.4439114084114086, 0.24]
neonsign_N[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed reference points used for exact placement and orientation constraints.
_room_center = AssetInstance(position=[2.50, 2.25, 1.00])
_counter_focus = AssetInstance(position=[0.38, 2.25, 0.90])

# The counter runs along the left wall. Its narrow depth preserves most of the
# room as circulation space and leaves the doorway at (5.00, 3.55) clear.
counter[0].position = [0.375, 2.25, 0.525]
counter[0].rotation = [0, 0, 0]

# Important wall and semantic relationships are specified first.
solver.against_wall(counter[0], walls[2])
solver.point_towards(counter[0], _room_center)

# o0031 is plant_I. Place it against the right wall, below the doorway zone.
solver.against_wall(plant_I[0], walls[0])
solver.point_towards(plant_I[0], _room_center)

# o0008 (plant_B) and o0022 (plant_E) are adjacent. Their centers are 0.34 m
# apart, so the 0.30 m-wide pots do not overlap and their surfaces are only
# 0.04 m apart—well within the requested 0.20 m proximity.
solver.distance_constraint(
    plant_B[0], plant_E[0], 0.30, 0.50, weight=10
)

# o0030 (stool_D) lies on the segment between o0049 (vase_A) and
# o0062 (vase_D), with equal spacing to both vases.
solver.distance_constraint(stool_D[0], vase_A[0], 0.70, 0.70, weight=10)
solver.distance_constraint(stool_D[0], vase_D[0], 0.70, 0.70, weight=10)

# o0051 (plant_N) lies between o0018 (plant_D) and o0075 (plant_R).
solver.distance_constraint(plant_N[0], plant_D[0], 0.45, 0.45, weight=10)
solver.distance_constraint(plant_N[0], plant_R[0], 0.45, 0.45, weight=10)


# Floor assets are arranged in clear rows around the counter. The entire
# upper-right doorway approach (approximately x > 4.35, y > 3.0) stays empty.
_floor_layout = [
    # Appliances along the bottom wall.
    (refrigerator_A, [1.30, 0.38, 0.875]),
    (jukebox,       [2.20, 0.425, 0.725]),
    (refrigerator_B, [3.10, 0.38, 0.875]),

    # Three customer stools face the counter.
    (stool_A, [1.25, 1.15, 0.50]),
    (stool_B, [1.25, 2.25, 0.50]),
    (stool_C, [1.25, 3.35, 0.50]),

    # Required vase–stool–vase arrangement along the upper side.
    (vase_A,  [1.50, 4.10, 0.35]),
    (stool_D, [2.20, 4.10, 0.50]),
    (vase_D,  [2.90, 4.10, 0.36]),

    # Two additional decorative floor vases.
    (vase_B, [3.35, 4.10, 0.35]),
    (vase_C, [3.75, 4.10, 0.36]),

    # First plant row. plant_N is centered between plant_D and plant_R.
    (plant_A, [1.85, 1.25, 0.275]),
    (plant_B, [2.35, 1.25, 0.21]),
    (plant_E, [2.69, 1.25, 0.21]),
    (plant_C, [3.15, 1.25, 0.23]),
    (plant_D, [3.60, 1.25, 0.23]),
    (plant_N, [4.05, 1.25, 0.275]),
    (plant_R, [4.50, 1.25, 0.23]),

    # Second plant row.
    (plant_F, [1.85, 2.00, 0.225]),
    (plant_G, [2.30, 2.00, 0.225]),
    (plant_H, [2.72, 2.00, 0.21]),
    (plant_J, [3.20, 2.00, 0.275]),
    (plant_K, [3.70, 2.00, 0.275]),
    (plant_L, [4.18, 2.00, 0.24]),

    # plant_I is against the right wall, away from the door.
    (plant_I, [4.84, 2.15, 0.24]),

    # Third plant row, stopping well before the doorway approach.
    (plant_M, [1.85, 2.75, 0.24]),
    (plant_O, [2.30, 2.75, 0.21]),
    (plant_P, [2.72, 2.75, 0.23]),
    (plant_Q, [3.18, 2.75, 0.24]),
]

for _floor_asset, _floor_position in _floor_layout:
    _floor_asset[0].position = _floor_position

    # Exact high-weight anchors preserve the non-overlapping rows and all
    # required "between" relationships during feasibility adjustment.
    solver.distance_constraint(
        _floor_asset[0],
        AssetInstance(position=_floor_position),
        0,
        0,
        weight=10,
    )

    # Appliances and freestanding decor face the room; the counter stools face
    # toward the counter for a functional diner arrangement.
    if _floor_asset in (stool_A, stool_B, stool_C, stool_D):
        _floor_asset[0].rotation = [0, 0, radians(180)]
        solver.point_towards(_floor_asset[0], _counter_focus)
    else:
        solver.point_towards(_floor_asset[0], _room_center)


# Thin signs and lamps are mounted around all four walls. Signs occupy the
# higher tier and lamps the lower tier, preventing vertical overlap.
_wall_layout = [
    # Neon signs on the top wall.
    (neonsign_A, walls[1], [0.50, 4.46, 2.05]),
    (neonsign_B, walls[1], [1.48, 4.46, 2.05]),
    (neonsign_C, walls[1], [2.50, 4.46, 2.05]),
    (neonsign_D, walls[1], [3.50, 4.46, 2.05]),
    (neonsign_E, walls[1], [4.48, 4.46, 2.05]),

    # Neon signs on the bottom wall, mounted above the appliances.
    (neonsign_F, walls[3], [0.52, 0.04, 2.15]),
    (neonsign_G, walls[3], [1.50, 0.04, 2.15]),
    (neonsign_H, walls[3], [2.48, 0.04, 2.15]),
    (neonsign_I, walls[3], [3.48, 0.04, 2.15]),
    (neonsign_J, walls[3], [4.48, 0.04, 2.15]),

    # Remaining signs on the side walls.
    (neonsign_K, walls[2], [0.04, 1.15, 2.05]),
    (neonsign_L, walls[2], [0.04, 3.35, 2.05]),
    (neonsign_M, walls[0], [4.96, 0.80, 2.05]),
    (neonsign_N, walls[0], [4.96, 2.05, 2.05]),

    # Lower lamp tier on the top wall.
    (walllamp_A, walls[1], [0.65, 4.39, 1.35]),
    (walllamp_B, walls[1], [1.90, 4.38, 1.35]),
    (walllamp_C, walls[1], [3.10, 4.39, 1.35]),
    (walllamp_D, walls[1], [4.35, 4.39, 1.35]),

    # Lower lamp tier on the bottom wall.
    (walllamp_E, walls[3], [0.65, 0.12, 1.35]),
    (walllamp_F, walls[3], [1.90, 0.11, 1.35]),
    (walllamp_G, walls[3], [3.10, 0.15, 1.35]),
    (walllamp_H, walls[3], [4.35, 0.12, 1.35]),

    # Side-wall lamps; right-wall fixtures remain below the door area.
    (walllamp_I, walls[2], [0.12, 1.05, 1.35]),
    (walllamp_J, walls[2], [0.15, 3.35, 1.35]),
    (lamp_A, walls[0], [4.90, 0.75, 1.35]),
    (lamp_B, walls[0], [4.90, 2.20, 1.35]),
]

for _wall_asset, _supporting_wall, _wall_position in _wall_layout:
    _wall_asset[0].position = _wall_position
    solver.against_wall(_wall_asset[0], _supporting_wall)

    # All wall-mounted graphics and lights face into the room.
    solver.point_towards(_wall_asset[0], _room_center)


# Small service and decorative objects are distributed over the counter in two
# narrow columns. Their z positions initially match the 1.05 m counter top.
_countertop_layout = [
    (magazine_A,     [0.20, 0.80, 1.055]),
    (plate_A,        [0.55, 0.80, 1.06]),

    (cup_A,          [0.20, 1.04, 1.10]),
    (saltshaker_A,   [0.55, 1.04, 1.10]),

    (menu_A,         [0.20, 1.28, 1.19]),
    (napkinholder,   [0.55, 1.28, 1.11]),

    (succulent_A,    [0.20, 1.52, 1.15]),
    (cup_B,          [0.55, 1.52, 1.10]),

    (magazine_B,     [0.20, 1.76, 1.055]),
    (saltshaker_B,   [0.55, 1.76, 1.095]),

    (menu_B,         [0.20, 2.00, 1.19]),
    (cup_C,          [0.55, 2.00, 1.095]),

    (plate_B,        [0.20, 2.24, 1.06]),
    (peppergrinder_A, [0.55, 2.24, 1.14]),

    (menu_C,         [0.20, 2.48, 1.19]),
    (cup_D,          [0.55, 2.48, 1.095]),

    (magazine_C,     [0.20, 2.72, 1.055]),
    (saltshaker_C,   [0.55, 2.72, 1.10]),

    (menu_D,         [0.20, 2.96, 1.21]),
    (cup_E,          [0.55, 2.96, 1.10]),

    (succulent_B,    [0.20, 3.20, 1.15]),
    (peppergrinder_B, [0.55, 3.20, 1.13]),

    (menu_E,         [0.20, 3.44, 1.21]),
    (cup_F,          [0.55, 3.44, 1.095]),

    (saltshaker_D,   [0.20, 3.68, 1.095]),
]

for _countertop_asset, _countertop_position in _countertop_layout:
    _countertop_asset[0].position = _countertop_position
    _countertop_asset[0].rotation = [0, 0, 0]

    # Exact horizontal anchors keep the dense tabletop arrangement separated.
    solver.distance_constraint(
        _countertop_asset[0],
        AssetInstance(position=_countertop_position),
        0,
        0,
        weight=10,
    )

    # The support constraint maintains the correct tabletop height.
    solver.on_top_of(_countertop_asset[0], counter[0])

    # Menus, cups, magazines, and condiments share the counter's orientation.
    solver.align_with(_countertop_asset[0], counter[0])

solver.constraints = []
walllamp_A[0].position = [0.6499999761581421, 4.344952583312988, 0.1599999964237213]
walllamp_A[0].rotation = [0, 0, -1.4187304124321445]
walllamp_A[0].optimize = 2
neonsign_H[0].position = [2.4800000190734863, 0.089142806828022, 0.20000000298023224]
neonsign_H[0].rotation = [0, 0, 1.4608317022645794]
neonsign_H[0].optimize = 2
neonsign_K[0].position = [0.0399421751499176, 1.149999976158142, 0.20000000298023224]
neonsign_K[0].rotation = [0, 0, -0.00010761718794937333]
neonsign_K[0].optimize = 2
peppergrinder_A[0].position = [0.550000011920929, 2.240000009536743, 1.1399999856948853]
peppergrinder_A[0].rotation = [0, 0, 0.011176573288763736]
peppergrinder_A[0].optimize = 2
plant_C[0].position = [3.1500000953674316, 1.25, 0.23000000417232513]
plant_C[0].rotation = [0, 0, 0.00942477746072377]
plant_C[0].optimize = 2
vase_C[0].position = [3.75, 4.099999904632568, 0.36000001430511475]
vase_C[0].rotation = [0, 0, 0.00942477746072377]
vase_C[0].optimize = 2
walllamp_C[0].position = [3.0999999046325684, 4.344952583312988, 0.1599999964237213]
walllamp_C[0].rotation = [0, 0, -1.4187304124321445]
walllamp_C[0].optimize = 2
walllamp_D[0].position = [4.349999904632568, 4.384482383728027, 0.12999999523162842]
walllamp_D[0].rotation = [0, 0, -1.4186373987929863]
walllamp_D[0].optimize = 2
plate_B[0].position = [0.2548637390136719, 2.249220371246338, 1.059999942779541]
plate_B[0].rotation = [0, 0, 0.011176573288763736]
plate_B[0].optimize = 2
plant_B[0].position = [2.3499999046325684, 1.25, 0.20999999344348907]
plant_B[0].rotation = [0, 0, 0.01256637125682779]
plant_B[0].optimize = 2
saltshaker_C[0].position = [0.550000011920929, 2.7200000286102295, 1.0999999046325684]
saltshaker_C[0].rotation = [0, 0, 0.011176573288763736]
saltshaker_C[0].optimize = 2
stool_D[0].position = [2.200000047683716, 4.099999904632568, 0.5]
stool_D[0].rotation = [0, 0, -3.125884689672577]
stool_D[0].optimize = 2
lamp_A[0].position = [4.891592025756836, 0.75, 0.15000000596046448]
lamp_A[0].rotation = [0, 0, 1.6372182387829277]
lamp_A[0].optimize = 2
cup_C[0].position = [0.550000011920929, 2.0, 1.09499990940094]
cup_C[0].rotation = [0, 0, 0.011176573288763736]
cup_C[0].optimize = 2
walllamp_J[0].position = [0.11978498846292496, 3.3499999046325684, 0.09000000357627869]
walllamp_J[0].rotation = [0, 0, -0.00010711789929805189]
walllamp_J[0].optimize = 2
neonsign_J[0].position = [4.480000019073486, 0.09656701236963272, 0.22499999403953552]
neonsign_J[0].rotation = [0, 0, 1.4623901641461348]
neonsign_J[0].optimize = 2
succulent_B[0].position = [0.20000000298023224, 3.200000047683716, 1.149999976158142]
succulent_B[0].rotation = [0, 0, 0.011176573288763736]
succulent_B[0].optimize = 2
neonsign_E[0].position = [4.480000019073486, 4.394237518310547, 0.20999999344348907]
neonsign_E[0].rotation = [0, 0, -1.4231551024349647]
neonsign_E[0].optimize = 2
plant_G[0].position = [2.299999952316284, 2.0, 0.22499999403953552]
plant_G[0].rotation = [0, 0, 0.00942477746072377]
plant_G[0].optimize = 2
plant_M[0].position = [1.850000023841858, 2.75, 0.23999999463558197]
plant_M[0].rotation = [0, 0, 0.00942477746072377]
plant_M[0].optimize = 2
walllamp_E[0].position = [0.6499999761581421, 0.1626633256673813, 0.15000000596046448]
walllamp_E[0].rotation = [0, 0, 1.4569276529405266]
walllamp_E[0].optimize = 2
plant_N[0].position = [4.052233695983887, 1.25, 0.2750000059604645]
plant_N[0].rotation = [0, 0, 0.0157079639172164]
plant_N[0].optimize = 2
neonsign_F[0].position = [0.5199999809265137, 0.09165333956480026, 0.20999999344348907]
neonsign_F[0].rotation = [0, 0, 1.4613299176316032]
neonsign_F[0].optimize = 2
walllamp_I[0].position = [0.13999958336353302, 1.0499999523162842, 0.14000000059604645]
walllamp_I[0].rotation = [0, 0, -0.00010778112059869871]
walllamp_I[0].optimize = 2
neonsign_N[0].position = [4.448547840118408, 2.049999952316284, 0.23999999463558197]
neonsign_N[0].rotation = [0, 0, 1.6423988496116895]
neonsign_N[0].optimize = 2
neonsign_B[0].position = [1.4800000190734863, 4.384070873260498, 0.22499999403953552]
neonsign_B[0].rotation = [0, 0, -1.4248413965622493]
neonsign_B[0].optimize = 2
walllamp_F[0].position = [1.899999976158142, 0.11187531799077988, 0.12999999523162842]
walllamp_F[0].rotation = [0, 0, 1.456678275114031]
walllamp_F[0].optimize = 2
plant_F[0].position = [1.850000023841858, 2.0, 0.22499999403953552]
plant_F[0].rotation = [0, 0, 0.00942477746072377]
plant_F[0].optimize = 2
vase_A[0].position = [1.5, 4.099999904632568, 0.3499999940395355]
vase_A[0].rotation = [0, 0, 0.01256637125682779]
vase_A[0].optimize = 2
refrigerator_B[0].position = [3.0999999046325684, 0.3799999952316284, 0.875]
refrigerator_B[0].rotation = [0, 0, 0.00942477746072377]
refrigerator_B[0].optimize = 2
plant_D[0].position = [3.5999999046325684, 1.25, 0.23000000417232513]
plant_D[0].rotation = [0, 0, 0.01256637125682779]
plant_D[0].optimize = 2
menu_E[0].position = [0.20000000298023224, 3.440000057220459, 1.209999918937683]
menu_E[0].rotation = [0, 0, 0.011176573288763736]
menu_E[0].optimize = 2
succulent_A[0].position = [0.37254345417022705, 1.5489976406097412, 1.149999976158142]
succulent_A[0].rotation = [0, 0, 0.011176573288763736]
succulent_A[0].optimize = 2
cup_F[0].position = [0.550000011920929, 3.440000057220459, 1.09499990940094]
cup_F[0].rotation = [0, 0, 0.011176573288763736]
cup_F[0].optimize = 2
plant_E[0].position = [2.690000057220459, 1.25, 0.20999999344348907]
plant_E[0].rotation = [0, 0, 0.01256637125682779]
plant_E[0].optimize = 2
plant_H[0].position = [2.7200000286102295, 2.0, 0.20999999344348907]
plant_H[0].rotation = [0, 0, 0.00942477746072377]
plant_H[0].optimize = 2
menu_C[0].position = [0.21563716232776642, 2.482628107070923, 1.1899999380111694]
menu_C[0].rotation = [0, 0, 0.011176573288763736]
menu_C[0].optimize = 2
plant_A[0].position = [1.850000023841858, 1.25, 0.2750000059604645]
plant_A[0].rotation = [0, 0, 0.00942477746072377]
plant_A[0].optimize = 2
magazine_B[0].position = [0.3333168625831604, 1.7824052572250366, 1.0549999475479126]
magazine_B[0].rotation = [0, 0, 0.011176573288763736]
magazine_B[0].optimize = 2
stool_C[0].position = [1.25, 3.3499999046325684, 0.5]
stool_C[0].rotation = [0, 0, -3.1321678761290697]
stool_C[0].optimize = 2
neonsign_C[0].position = [2.5, 4.380760669708252, 0.23999999463558197]
neonsign_C[0].rotation = [0, 0, -1.425446697605965]
neonsign_C[0].optimize = 2
napkinholder[0].position = [0.550000011920929, 1.2799999713897705, 1.1099998950958252]
napkinholder[0].rotation = [0, 0, 0.011176573288763736]
napkinholder[0].optimize = 2
plant_I[0].position = [4.829465866088867, 2.1500000953674316, 0.23999999463558197]
plant_I[0].rotation = [0, 0, 1.639013224958124]
plant_I[0].optimize = 2
plant_Q[0].position = [3.180000066757202, 2.75, 0.23999999463558197]
plant_Q[0].rotation = [0, 0, 0.00942477746072377]
plant_Q[0].optimize = 2
neonsign_D[0].position = [3.5, 4.394237518310547, 0.20999999344348907]
neonsign_D[0].rotation = [0, 0, -1.4231551024349647]
neonsign_D[0].optimize = 2
neonsign_M[0].position = [4.548305988311768, 0.800000011920929, 0.20000000298023224]
neonsign_M[0].rotation = [0, 0, 1.640575273977067]
neonsign_M[0].optimize = 2
counter[0].position = [0.3778004050254822, 2.25, 0.5249999761581421]
counter[0].rotation = [0, 0, -8.857773449973347e-05]
counter[0].optimize = 2
cup_A[0].position = [0.4509965777397156, 1.08218252658844, 1.0999999046325684]
cup_A[0].rotation = [0, 0, 0.011176573288763736]
cup_A[0].optimize = 2
vase_D[0].position = [2.9000000953674316, 4.099999904632568, 0.36000001430511475]
vase_D[0].rotation = [0, 0, 0.01256637125682779]
vase_D[0].optimize = 2
plant_O[0].position = [2.299999952316284, 2.75, 0.20999999344348907]
plant_O[0].rotation = [0, 0, 0.00942477746072377]
plant_O[0].optimize = 2
menu_A[0].position = [0.4117700159549713, 1.3155901432037354, 1.1899999380111694]
menu_A[0].rotation = [0, 0, 0.011176573288763736]
menu_A[0].optimize = 2
peppergrinder_B[0].position = [0.550000011920929, 3.200000047683716, 1.1299999952316284]
peppergrinder_B[0].rotation = [0, 0, 0.011176573288763736]
peppergrinder_B[0].optimize = 2
neonsign_A[0].position = [0.5, 4.394237518310547, 0.20000000298023224]
neonsign_A[0].rotation = [0, 0, -1.4231551024349647]
neonsign_A[0].optimize = 2
menu_D[0].position = [0.20000000298023224, 2.9600000381469727, 1.209999918937683]
menu_D[0].rotation = [0, 0, 0.011176573288763736]
menu_D[0].optimize = 2
neonsign_G[0].position = [1.5, 0.09656701236963272, 0.22499999403953552]
neonsign_G[0].rotation = [0, 0, 1.4623901641461348]
neonsign_G[0].optimize = 2
magazine_A[0].position = [0.49022313952445984, 0.8487750291824341, 1.0549999475479126]
magazine_A[0].rotation = [0, 0, 0.011176573288763736]
magazine_A[0].optimize = 2
plant_K[0].position = [3.700000047683716, 2.0, 0.2750000059604645]
plant_K[0].rotation = [0, 0, 0.00942477746072377]
plant_K[0].optimize = 2
jukebox[0].position = [2.200000047683716, 0.42500001192092896, 0.7250000238418579]
jukebox[0].rotation = [0, 0, 0.00942477746072377]
jukebox[0].optimize = 2
plant_P[0].position = [2.7200000286102295, 2.75, 0.23000000417232513]
plant_P[0].rotation = [0, 0, 0.00942477746072377]
plant_P[0].optimize = 2
neonsign_L[0].position = [0.0399421751499176, 3.3499999046325684, 0.20999999344348907]
neonsign_L[0].rotation = [0, 0, -0.00010761469789673807]
neonsign_L[0].optimize = 2
lamp_B[0].position = [4.891592025756836, 2.200000047683716, 0.15000000596046448]
lamp_B[0].rotation = [0, 0, 1.6372182387829277]
lamp_B[0].optimize = 2
menu_B[0].position = [0.29409030079841614, 2.015812873840332, 1.1899999380111694]
menu_B[0].rotation = [0, 0, 0.011176573288763736]
menu_B[0].optimize = 2
refrigerator_A[0].position = [1.2999999523162842, 0.3799999952316284, 0.875]
refrigerator_A[0].rotation = [0, 0, 0.00942477746072377]
refrigerator_A[0].optimize = 2
cup_B[0].position = [0.550000011920929, 1.5199999809265137, 1.0999999046325684]
cup_B[0].rotation = [0, 0, 0.011176573288763736]
cup_B[0].optimize = 2
saltshaker_A[0].position = [0.550000011920929, 1.0399999618530273, 1.0999999046325684]
saltshaker_A[0].rotation = [0, 0, 0.011176573288763736]
saltshaker_A[0].optimize = 2
vase_B[0].position = [3.3499999046325684, 4.099999904632568, 0.3499999940395355]
vase_B[0].rotation = [0, 0, 0.00942477746072377]
vase_B[0].optimize = 2
walllamp_G[0].position = [3.0999999046325684, 0.13623951375484467, 0.09000000357627869]
walllamp_G[0].rotation = [0, 0, 1.4571253818847243]
walllamp_G[0].optimize = 2
stool_B[0].position = [1.25, 2.25, 0.5]
stool_B[0].rotation = [0, 0, -3.1321678761290697]
stool_B[0].optimize = 2
magazine_C[0].position = [0.20000000298023224, 2.7200000286102295, 1.0549999475479126]
magazine_C[0].rotation = [0, 0, 0.011176573288763736]
magazine_C[0].optimize = 2
plant_R[0].position = [4.5, 1.25, 0.23000000417232513]
plant_R[0].rotation = [0, 0, 0.01256637125682779]
plant_R[0].optimize = 2
stool_A[0].position = [1.25, 1.149999976158142, 0.5]
stool_A[0].rotation = [0, 0, -3.1321678761290697]
stool_A[0].optimize = 2
plant_J[0].position = [3.200000047683716, 2.0, 0.2750000059604645]
plant_J[0].rotation = [0, 0, 0.00942477746072377]
plant_J[0].optimize = 2
saltshaker_B[0].position = [0.550000011920929, 1.7599999904632568, 1.09499990940094]
saltshaker_B[0].rotation = [0, 0, 0.011176573288763736]
saltshaker_B[0].optimize = 2
walllamp_B[0].position = [1.899999976158142, 4.333566188812256, 0.15000000596046448]
walllamp_B[0].rotation = [0, 0, -1.4188646343655156]
walllamp_B[0].optimize = 2
cup_D[0].position = [0.550000011920929, 2.4800000190734863, 1.09499990940094]
cup_D[0].rotation = [0, 0, 0.011176573288763736]
cup_D[0].optimize = 2
plant_L[0].position = [4.179999828338623, 2.0, 0.23999999463558197]
plant_L[0].rotation = [0, 0, 0.00942477746072377]
plant_L[0].optimize = 2
walllamp_H[0].position = [4.349999904632568, 0.15273170173168182, 0.14000000059604645]
walllamp_H[0].rotation = [0, 0, 1.456892741504063]
walllamp_H[0].optimize = 2
neonsign_I[0].position = [3.4800000190734863, 0.09656701236963272, 0.22499999403953552]
neonsign_I[0].rotation = [0, 0, 1.4623901641461348]
neonsign_I[0].optimize = 2
cup_E[0].position = [0.550000011920929, 2.9600000381469727, 1.0999999046325684]
cup_E[0].rotation = [0, 0, 0.011176573288763736]
cup_E[0].optimize = 2
plate_A[0].position = [0.550000011920929, 0.800000011920929, 1.059999942779541]
plate_A[0].rotation = [0, 0, 0.011176573288763736]
plate_A[0].optimize = 2
saltshaker_D[0].position = [0.20000000298023224, 3.680000066757202, 1.09499990940094]
saltshaker_D[0].rotation = [0, 0, 0.011176573288763736]
saltshaker_D[0].optimize = 2

