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
    Wall(corner1=[6.00, 0.00, 0.00], corner2=[6.00, 4.00, 0.00]),
    Wall(corner1=[6.00, 4.00, 0.00], corner2=[0.00, 4.00, 0.00]),
    Wall(corner1=[0.00, 4.00, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
book = Assets(description="A synthetic polymer book with a glossy neon pink cover and angular rectangular shape, featuring a subtle holographic pattern that catches the synthwave light; some books stand upright while others are stacked horizontally, each with a thin metallic spine accent.", size=[0.16, 0.22, 0.03], placements=[AssetInstance() for _ in range(1)])
trashbin_A = Assets(description="A squat rectangular trash bin with synthetic matte surface, neon blue striping, angular corners and a recessed lid, 1980s synthwave style", size=[0.28, 0.32, 0.45], placements=[AssetInstance() for _ in range(1)])
poster_A = Assets(description="A single piece of thin and upright poster with a vibrant synthwave cityscape, neon pink and blue grid lines, glossy synthetic paper finish and a subtle metallic sheen", size=[0.01, 0.70, 1.00], placements=[AssetInstance() for _ in range(1)])
pencil_A = Assets(description="A slim cylindrical synthwave pencil made of glossy synthetic resin, neon blue barrel with pink stripe accents, smooth straight‑edged tip and a thin metallic ferrule", size=[0.01, 0.18, 0.01], placements=[AssetInstance() for _ in range(1)])
notebookb38c_A = Assets(description="A rectangular notebook with a synthetic cover, neon pink and blue gradient, glossy finish, and crisp white pages; one version is open with visible pages, the other is closed with a magnetic clasp.", size=[0.22, 0.30, 0.03], placements=[AssetInstance() for _ in range(1)])
poster_B = Assets(description="A single piece of thin and upright poster with a vibrant synthwave cityscape, dominated by neon pink and blue gradients, printed on a glossy synthetic sheet.", size=[0.01, 0.70, 1.00], placements=[AssetInstance() for _ in range(1)])
pen_teacher_A = Assets(description="A synthetic ballpoint pen with a slim cylindrical body, neon pink polymer finish accented by a blue glowing tip, smooth surface and subtle grip ridges, styled in 1980s synthwave fashion.", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
pensstudent_A = Assets(description="A futuristic synthetic pen with a slender cylindrical body, neon pink barrel and a glowing blue tip, glossy polymer finish", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
pen_A = Assets(description="A thin cylindrical writing instrument made of glossy polymer, its barrel streaked with neon pink and blue accents that pulse faintly, embodying a retro‑futuristic synthwave aesthetic", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
penteacher_A = Assets(description="Four cylindrical synthetic pens with chrome tips, each wrapped in a neon pink or neon blue vaporwave‑style stripe, glossy finish", size=[0.08, 0.16, 0.01], placements=[AssetInstance() for _ in range(1)])
neonlight_A = Assets(description="A thin elongated neon light strip with a flexible polymer casing, glowing neon pink and blue LEDs, sleek low‑profile design.", size=[0.03, 1.50, 0.04], placements=[AssetInstance() for _ in range(1)])
pensstudent_B = Assets(description="A futuristic synthetic pen with a slender cylindrical body, neon pink barrel and a glowing blue tip, glossy polymer finish", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
pencil_B = Assets(description="A slender cylindrical pencil made of synthetic polymer, painted neon pink with a neon blue eraser tip, and a glossy finish.", size=[0.01, 0.18, 0.01], placements=[AssetInstance() for _ in range(1)])
pen_B = Assets(description="A thin cylindrical writing instrument made of glossy polymer, its barrel streaked with neon pink and blue accents that pulse faintly, embodying a retro‑futuristic synthwave aesthetic", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
posterwall_A = Assets(description="A single piece of thin and upright poster with a retro 1980s synthwave cityscape, neon pink and blue gradients, glossy polymer coating", size=[0.01, 0.70, 1.00], placements=[AssetInstance() for _ in range(1)])
pen_teacher_B = Assets(description="A synthetic ballpoint pen with a slim cylindrical body, neon pink polymer finish accented by a blue glowing tip, smooth surface and subtle grip ridges, styled in 1980s synthwave fashion.", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
dispenser = Assets(description="A sleek cylindrical water dispenser with neon blue lighting accents, synthetic brushed metal finish, rounded top and narrow base, 1980s synthwave style", size=[0.36, 0.36, 1.15], placements=[AssetInstance() for _ in range(1)])
trashbin_B = Assets(description="A squat rectangular trash bin with synthetic matte surface, neon blue striping, angular corners and a recessed lid, 1980s synthwave style", size=[0.28, 0.32, 0.45], placements=[AssetInstance() for _ in range(1)])
pensstudent_C = Assets(description="A futuristic synthetic pen with a slender cylindrical body, neon pink barrel and a glowing blue tip, glossy polymer finish", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
studentdesk_A = Assets(description="A rectangular student desk with a blue grid pattern on its surface, synthetic matte coating, straight‑edged top and slender legs, 1980s synthwave style", size=[0.55, 0.75, 0.75], placements=[AssetInstance() for _ in range(1)])
notebookb38c_B = Assets(description="A rectangular notebook with a synthetic cover, neon pink and blue gradient, glossy finish, and crisp white pages; one version is open with visible pages, the other is closed with a magnetic clasp.", size=[0.22, 0.30, 0.03], placements=[AssetInstance() for _ in range(1)])
pensstudent_D = Assets(description="A futuristic synthetic pen with a slender cylindrical body, neon pink barrel and a glowing blue tip, glossy polymer finish", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
notebookteacher = Assets(description="Two synthetic notebooks, one open to reveal neon‑blue grid pages and one closed with a neon‑pink cover, both with rounded corners and a glossy polymer finish", size=[0.24, 0.60, 0.04], placements=[AssetInstance() for _ in range(1)])
sculpture = Assets(description="A central floor sculpture composed of interlocking geometric shapes, neon pink and blue highlights, synthetic polished surface, tall and angular, 1980s synthwave style", size=[0.70, 0.90, 1.70], placements=[AssetInstance() for _ in range(1)])
notebookdesk_A = Assets(description="A rectangular synthetic notebook with a glossy polymer cover, neon pink and blue wave motifs, 1980s synthwave vibe, slightly thicker pages and a rounded corner finish", size=[0.22, 0.30, 0.03], placements=[AssetInstance() for _ in range(1)])
pencil_C = Assets(description="A slender cylindrical pencil made of synthetic polymer, painted neon pink with a neon blue eraser tip, and a glossy finish.", size=[0.01, 0.18, 0.01], placements=[AssetInstance() for _ in range(1)])
studentdesk_B = Assets(description="A rectangular student desk with a blue grid pattern on its surface, synthetic matte coating, straight‑edged top and slender legs, 1980s synthwave style", size=[0.55, 0.75, 0.75], placements=[AssetInstance() for _ in range(1)])
pen_C = Assets(description="A synthetic ballpoint pen with a sleek cylindrical form, glossy polymer body in neon pink with a blue glowing tip, smooth surface and subtle ridges near the grip, styled after 1980s synthwave design.", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
notebook_A = Assets(description="A synthetic 1980s synthwave notebook with a sleek rectangular shape, neon pink cover accented by blue glowing trim, glossy polymer finish and rounded corners, giving it a futuristic retro look", size=[0.21, 0.28, 0.03], placements=[AssetInstance() for _ in range(1)])
notebookdesk_B = Assets(description="A rectangular synthetic notebook with a glossy polymer cover, neon pink and blue wave motifs, 1980s synthwave vibe, slightly thicker pages and a rounded corner finish", size=[0.22, 0.30, 0.03], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="A slender vertical neon lamp with a cylindrical base, a curved glass diffuser, and alternating pink and blue LED lighting that casts a vibrant glow.", size=[0.12, 0.18, 1.20], placements=[AssetInstance() for _ in range(1)])
plantnew = Assets(description="A synthetic plant with a sleek metallic pot, neon pink leaves that glow faintly, cylindrical trunk and angular foliage, futuristic aesthetic", size=[0.45, 0.45, 1.25], placements=[AssetInstance() for _ in range(1)])
studentdesk_C = Assets(description="A rectangular student desk with a blue grid pattern on its surface, synthetic matte coating, straight‑edged top and slender legs, 1980s synthwave style", size=[0.55, 0.75, 0.75], placements=[AssetInstance() for _ in range(1)])
pen_teacher_C = Assets(description="A synthetic ballpoint pen with a slim cylindrical body, neon pink polymer finish accented by a blue glowing tip, smooth surface and subtle grip ridges, styled in 1980s synthwave fashion.", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
pencil_D = Assets(description="A slender cylindrical pencil made of synthetic polymer, painted neon pink with a neon blue eraser tip, and a glossy finish.", size=[0.01, 0.18, 0.01], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="A sleek synthetic office chair with a low‑slung rectangular seat, angular chrome legs and a curved backrest illuminated by neon pink and blue edge lighting, giving it a 1980s synthwave vibe", size=[0.55, 0.55, 0.85], placements=[AssetInstance() for _ in range(1)])
pen_D = Assets(description="A thin cylindrical writing instrument made of glossy polymer, its barrel streaked with neon pink and blue accents that pulse faintly, embodying a retro‑futuristic synthwave aesthetic", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
plant_A = Assets(description="A synthetic plant with a metallic stem and neon pink and blue glowing leaves, set in a cylindrical pot, futuristic aesthetic.", size=[0.45, 0.45, 1.20], placements=[AssetInstance() for _ in range(1)])
posterwall_B = Assets(description="A single piece of thin and upright poster with a retro 1980s synthwave cityscape, neon pink and blue gradients, glossy polymer coating", size=[0.01, 0.70, 1.00], placements=[AssetInstance() for _ in range(1)])
poster_C = Assets(description="A single piece of thin and upright poster with a vibrant synthwave cityscape, dominated by neon pink and blue gradients, printed on a glossy synthetic sheet.", size=[0.01, 0.70, 1.00], placements=[AssetInstance() for _ in range(1)])
notebookstudent = Assets(description="A synthetic notebook opened to a neon‑blue grid page, rectangular with rounded corners and a glossy neon pink cover", size=[0.28, 0.42, 0.03], placements=[AssetInstance() for _ in range(1)])
pen_E = Assets(description="A sleek cylindrical pen with a smooth synthetic polymer body, featuring a glossy neon pink barrel and a thin neon blue tip, rounded cap, and a subtle chrome clip.", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
pen_F = Assets(description="A thin cylindrical writing instrument made of glossy polymer, its barrel streaked with neon pink and blue accents that pulse faintly, embodying a retro‑futuristic synthwave aesthetic", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
posterwall_C = Assets(description="A single piece of thin and upright poster with a retro 1980s synthwave cityscape, neon pink and blue gradients, glossy polymer coating", size=[0.01, 0.70, 1.00], placements=[AssetInstance() for _ in range(1)])
notebook_B = Assets(description="A rectangular notebook with a synthetic cover, neon pink and blue gradient, glossy finish, and crisp white pages; one version is open with visible pages, the other is closed with a magnetic clasp.", size=[0.22, 0.30, 0.03], placements=[AssetInstance() for _ in range(1)])
plant_B = Assets(description="A cylindrical floor plant pot in neon pink, synthetic glossy finish, with a slender green foliage silhouette emerging from the top, 1980s synthwave style", size=[0.42, 0.42, 1.10], placements=[AssetInstance() for _ in range(1)])
pencil_E = Assets(description="A slim cylindrical synthwave pencil made of glossy synthetic resin, neon blue barrel with pink stripe accents, smooth straight‑edged tip and a thin metallic ferrule", size=[0.01, 0.18, 0.01], placements=[AssetInstance() for _ in range(1)])
studentdesk_D = Assets(description="A rectangular student desk with a blue grid pattern on its surface, synthetic matte coating, straight‑edged top and slender legs, 1980s synthwave style", size=[0.55, 0.75, 0.75], placements=[AssetInstance() for _ in range(1)])
pen_G = Assets(description="A thin cylindrical writing instrument made of glossy polymer, its barrel streaked with neon pink and blue accents that pulse faintly, embodying a retro‑futuristic synthwave aesthetic", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="A rectangular storage cabinet with a blue grid pattern on its doors, synthetic glossy coating, flat front panels and recessed handles, 1980s synthwave style", size=[0.45, 0.90, 1.20], placements=[AssetInstance() for _ in range(1)])
studentdesk_E = Assets(description="A rectangular student desk with a blue grid pattern on its surface, synthetic matte coating, straight‑edged top and slender legs, 1980s synthwave style", size=[0.55, 0.75, 0.75], placements=[AssetInstance() for _ in range(1)])
notebook_student_A = Assets(description="A synthetic polymer notebook with a neon blue cover, rectangular shape, thin metallic binding, and a subtle holographic pattern; the notebook is open to a page.", size=[0.28, 0.42, 0.03], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="A sleek synthetic office chair with a low‑slung rectangular seat, angular chrome legs and a curved backrest illuminated by neon pink and blue edge lighting, giving it a 1980s synthwave vibe", size=[0.55, 0.55, 0.85], placements=[AssetInstance() for _ in range(1)])
pen_H = Assets(description="A thin cylindrical writing instrument made of glossy polymer, its barrel streaked with neon pink and blue accents that pulse faintly, embodying a retro‑futuristic synthwave aesthetic", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
neonlight_B = Assets(description="A thin elongated neon light strip with a flexible polymer casing, glowing neon pink and blue LEDs, sleek low‑profile design.", size=[0.03, 1.50, 0.04], placements=[AssetInstance() for _ in range(1)])
pencil_F = Assets(description="A slender cylindrical pencil made of synthetic polymer, painted neon pink with a neon blue eraser tip, and a glossy finish.", size=[0.01, 0.18, 0.01], placements=[AssetInstance() for _ in range(1)])
pensstudent_E = Assets(description="A futuristic synthetic pen with a slender cylindrical body, neon pink barrel and a glowing blue tip, glossy polymer finish", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
pen_I = Assets(description="A synthetic ballpoint pen with a sleek cylindrical form, glossy polymer body in neon pink with a blue glowing tip, smooth surface and subtle ridges near the grip, styled after 1980s synthwave design.", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
pen_J = Assets(description="A thin cylindrical writing instrument made of glossy polymer, its barrel streaked with neon pink and blue accents that pulse faintly, embodying a retro‑futuristic synthwave aesthetic", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
poster_D = Assets(description="A single piece of thin and upright poster with a vibrant synthwave cityscape, dominated by neon pink and blue gradients, printed on a glossy synthetic sheet.", size=[0.01, 0.70, 1.00], placements=[AssetInstance() for _ in range(1)])
poster_E = Assets(description="A single piece of thin and upright poster with a retro synthwave graphic, rectangular shape, neon pink and blue geometric patterns on a glossy synthetic backing", size=[0.01, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
pen_teacher_D = Assets(description="A synthetic ballpoint pen with a slim cylindrical body, neon pink polymer finish accented by a blue glowing tip, smooth surface and subtle grip ridges, styled in 1980s synthwave fashion.", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
poster_F = Assets(description="A single piece of thin and upright poster with a retro synthwave graphic, rectangular shape, neon pink and blue geometric patterns on a glossy synthetic backing", size=[0.01, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
penteacher_B = Assets(description="Four cylindrical synthetic pens with chrome tips, each wrapped in a neon pink or neon blue vaporwave‑style stripe, glossy finish", size=[0.08, 0.16, 0.01], placements=[AssetInstance() for _ in range(1)])
neonlight_C = Assets(description="A thin elongated neon light strip with a flexible polymer casing, glowing neon pink and blue LEDs, sleek low‑profile design.", size=[0.03, 1.50, 0.04], placements=[AssetInstance() for _ in range(1)])
pensstudent_F = Assets(description="A futuristic synthetic pen with a slender cylindrical body, neon pink barrel and a glowing blue tip, glossy polymer finish", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
plant_C = Assets(description="A synthetic plant with a metallic stem and neon pink and blue glowing leaves, set in a cylindrical pot, futuristic aesthetic.", size=[0.45, 0.45, 1.20], placements=[AssetInstance() for _ in range(1)])
plant_D = Assets(description="A cylindrical floor plant pot in neon pink, synthetic glossy finish, with a slender green foliage silhouette emerging from the top, 1980s synthwave style", size=[0.42, 0.42, 1.10], placements=[AssetInstance() for _ in range(1)])
eraser_A = Assets(description="A small rectangular eraser of synthetic rubber, neon pink with a neon blue stripe, smooth surface.", size=[0.03, 0.05, 0.01], placements=[AssetInstance() for _ in range(1)])
poster_G = Assets(description="A single piece of thin and upright poster with a vibrant synthwave cityscape, neon pink and blue grid lines, glossy synthetic paper finish and a subtle metallic sheen", size=[0.01, 0.70, 1.00], placements=[AssetInstance() for _ in range(1)])
eraser_B = Assets(description="A synthetic polymer eraser with a smooth rectangular shape, neon pink surface and a subtle blue edge glow, giving it a futuristic synthwave appearance.", size=[0.03, 0.05, 0.01], placements=[AssetInstance() for _ in range(1)])
screen = Assets(description="A single piece of thin and upright projector screen with a bright neon border, rectangular shape and a smooth matte finish that glows with synthwave colors.", size=[0.08, 2.40, 1.50], placements=[AssetInstance() for _ in range(1)])
pencil_G = Assets(description="A slender cylindrical pencil made of synthetic polymer, painted neon pink with a neon blue eraser tip, and a glossy finish.", size=[0.01, 0.18, 0.01], placements=[AssetInstance() for _ in range(1)])
pen_K = Assets(description="A slender cylindrical pen crafted from glossy polymer, featuring a neon pink barrel with a blue tip that glows faintly, embodying classic 80s synthwave flair.", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
eraser_C = Assets(description="A small rectangular eraser of synthetic rubber, neon pink with a neon blue stripe, smooth surface.", size=[0.03, 0.05, 0.01], placements=[AssetInstance() for _ in range(1)])
eraserteacher = Assets(description="A single synthetic eraser shaped like a low‑profile slab, neon pink with a subtle blue glow, smooth matte surface", size=[0.03, 0.06, 0.01], placements=[AssetInstance() for _ in range(1)])
posterwall_D = Assets(description="A single piece of thin and upright poster with a retro 1980s synthwave cityscape, neon pink and blue gradients, glossy polymer coating", size=[0.01, 0.70, 1.00], placements=[AssetInstance() for _ in range(1)])
pendesk = Assets(description="A cylindrical synthetic pen with a chrome body, neon pink and blue illuminated tip, 1980s synthwave style, smooth finish and a subtle grip ridge near the barrel", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
studentdesk_F = Assets(description="A rectangular student desk with a blue grid pattern on its surface, synthetic matte coating, straight‑edged top and slender legs, 1980s synthwave style", size=[0.55, 0.75, 0.75], placements=[AssetInstance() for _ in range(1)])
bookshelf = Assets(description="A sleek synthetic bookshelf with a neon blue trim, rectangular frame, angular edges and glossy acrylic panels that reflect a pink‑blue synthwave glow", size=[0.35, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
teacherdesk = Assets(description="A rectangular teacher's desk with neon pink accents, synthetic glossy finish, angular legs and a low‑slung top, 1980s synthwave style", size=[0.75, 1.50, 0.76], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="A slender vertical neon lamp with a cylindrical base, a curved glass diffuser, and alternating pink and blue LED lighting that casts a vibrant glow.", size=[0.12, 0.18, 1.20], placements=[AssetInstance() for _ in range(1)])
notebook_student_B = Assets(description="A synthetic polymer notebook with a neon pink cover and angular rectangular shape, thin metallic binding, and a subtle grid texture; the notebook is open to a page, revealing a faint glowing line pattern.", size=[0.28, 0.42, 0.03], placements=[AssetInstance() for _ in range(1)])
notebook_C = Assets(description="A rectangular synthetic notebook with a smooth matte cover highlighted by neon pink and blue geometric patterns, its edges slightly rounded for a futuristic look", size=[0.21, 0.28, 0.03], placements=[AssetInstance() for _ in range(1)])
geometric = Assets(description="A single piece of thin and upright geometric decor made of translucent acrylic with neon blue and pink facets, shaped like a floating polyhedron that glows from within, adding a futuristic 1980s synthwave accent.", size=[0.25, 0.30, 0.40], placements=[AssetInstance() for _ in range(1)])
pencil_H = Assets(description="A slender cylindrical pencil made of synthetic polymer, painted neon pink with a neon blue eraser tip, and a glossy finish.", size=[0.01, 0.18, 0.01], placements=[AssetInstance() for _ in range(1)])
poster_H = Assets(description="A single piece of thin and upright poster with a retro synthwave graphic, rectangular shape, neon pink and blue geometric patterns on a glossy synthetic backing", size=[0.01, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
studentdesk_G = Assets(description="A rectangular student desk with a blue grid pattern on its surface, synthetic matte coating, straight‑edged top and slender legs, 1980s synthwave style", size=[0.55, 0.75, 0.75], placements=[AssetInstance() for _ in range(1)])
notebook_D = Assets(description="A synthetic 1980s synthwave notebook with a sleek rectangular shape, neon pink cover accented by blue glowing trim, glossy polymer finish and rounded corners, giving it a futuristic retro look", size=[0.21, 0.28, 0.03], placements=[AssetInstance() for _ in range(1)])
penstudent = Assets(description="Two cylindrical synthetic pens with neon pink and neon blue vaporwave stripes, chrome tips, glossy finish", size=[0.04, 0.16, 0.01], placements=[AssetInstance() for _ in range(1)])
neonlight_D = Assets(description="A thin elongated neon light strip with a flexible polymer casing, glowing neon pink and blue LEDs, sleek low‑profile design.", size=[0.03, 1.50, 0.04], placements=[AssetInstance() for _ in range(1)])
notebook_E = Assets(description="A rectangular notebook with a synthetic cover, neon pink and blue gradient, glossy finish, and crisp white pages; one version is open with visible pages, the other is closed with a magnetic clasp.", size=[0.22, 0.30, 0.03], placements=[AssetInstance() for _ in range(1)])
pen_teacher_E = Assets(description="A synthetic ballpoint pen with a slim cylindrical body, neon pink polymer finish accented by a blue glowing tip, smooth surface and subtle grip ridges, styled in 1980s synthwave fashion.", size=[0.01, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])

book[0].instance_id = 'book_0'
trashbin_A[0].instance_id = 'trashbin_A_0'
poster_A[0].instance_id = 'poster_A_0'
pencil_A[0].instance_id = 'pencil_A_0'
notebookb38c_A[0].instance_id = 'notebookb38c_A_0'
poster_B[0].instance_id = 'poster_B_0'
pen_teacher_A[0].instance_id = 'pen_teacher_A_0'
pensstudent_A[0].instance_id = 'pensstudent_A_0'
pen_A[0].instance_id = 'pen_A_0'
penteacher_A[0].instance_id = 'penteacher_A_0'
neonlight_A[0].instance_id = 'neonlight_A_0'
pensstudent_B[0].instance_id = 'pensstudent_B_0'
pencil_B[0].instance_id = 'pencil_B_0'
pen_B[0].instance_id = 'pen_B_0'
posterwall_A[0].instance_id = 'posterwall_A_0'
pen_teacher_B[0].instance_id = 'pen_teacher_B_0'
dispenser[0].instance_id = 'dispenser_0'
trashbin_B[0].instance_id = 'trashbin_B_0'
pensstudent_C[0].instance_id = 'pensstudent_C_0'
studentdesk_A[0].instance_id = 'studentdesk_A_0'
notebookb38c_B[0].instance_id = 'notebookb38c_B_0'
pensstudent_D[0].instance_id = 'pensstudent_D_0'
notebookteacher[0].instance_id = 'notebookteacher_0'
sculpture[0].instance_id = 'sculpture_0'
notebookdesk_A[0].instance_id = 'notebookdesk_A_0'
pencil_C[0].instance_id = 'pencil_C_0'
studentdesk_B[0].instance_id = 'studentdesk_B_0'
pen_C[0].instance_id = 'pen_C_0'
notebook_A[0].instance_id = 'notebook_A_0'
notebookdesk_B[0].instance_id = 'notebookdesk_B_0'
lamp_A[0].instance_id = 'lamp_A_0'
plantnew[0].instance_id = 'plantnew_0'
studentdesk_C[0].instance_id = 'studentdesk_C_0'
pen_teacher_C[0].instance_id = 'pen_teacher_C_0'
pencil_D[0].instance_id = 'pencil_D_0'
chair_A[0].instance_id = 'chair_A_0'
pen_D[0].instance_id = 'pen_D_0'
plant_A[0].instance_id = 'plant_A_0'
posterwall_B[0].instance_id = 'posterwall_B_0'
poster_C[0].instance_id = 'poster_C_0'
notebookstudent[0].instance_id = 'notebookstudent_0'
pen_E[0].instance_id = 'pen_E_0'
pen_F[0].instance_id = 'pen_F_0'
posterwall_C[0].instance_id = 'posterwall_C_0'
notebook_B[0].instance_id = 'notebook_B_0'
plant_B[0].instance_id = 'plant_B_0'
pencil_E[0].instance_id = 'pencil_E_0'
studentdesk_D[0].instance_id = 'studentdesk_D_0'
pen_G[0].instance_id = 'pen_G_0'
cabinet[0].instance_id = 'cabinet_0'
studentdesk_E[0].instance_id = 'studentdesk_E_0'
notebook_student_A[0].instance_id = 'notebook_student_A_0'
chair_B[0].instance_id = 'chair_B_0'
pen_H[0].instance_id = 'pen_H_0'
neonlight_B[0].instance_id = 'neonlight_B_0'
pencil_F[0].instance_id = 'pencil_F_0'
pensstudent_E[0].instance_id = 'pensstudent_E_0'
pen_I[0].instance_id = 'pen_I_0'
pen_J[0].instance_id = 'pen_J_0'
poster_D[0].instance_id = 'poster_D_0'
poster_E[0].instance_id = 'poster_E_0'
pen_teacher_D[0].instance_id = 'pen_teacher_D_0'
poster_F[0].instance_id = 'poster_F_0'
penteacher_B[0].instance_id = 'penteacher_B_0'
neonlight_C[0].instance_id = 'neonlight_C_0'
pensstudent_F[0].instance_id = 'pensstudent_F_0'
plant_C[0].instance_id = 'plant_C_0'
plant_D[0].instance_id = 'plant_D_0'
eraser_A[0].instance_id = 'eraser_A_0'
poster_G[0].instance_id = 'poster_G_0'
eraser_B[0].instance_id = 'eraser_B_0'
screen[0].instance_id = 'screen_0'
pencil_G[0].instance_id = 'pencil_G_0'
pen_K[0].instance_id = 'pen_K_0'
eraser_C[0].instance_id = 'eraser_C_0'
eraserteacher[0].instance_id = 'eraserteacher_0'
posterwall_D[0].instance_id = 'posterwall_D_0'
pendesk[0].instance_id = 'pendesk_0'
studentdesk_F[0].instance_id = 'studentdesk_F_0'
bookshelf[0].instance_id = 'bookshelf_0'
teacherdesk[0].instance_id = 'teacherdesk_0'
lamp_B[0].instance_id = 'lamp_B_0'
notebook_student_B[0].instance_id = 'notebook_student_B_0'
notebook_C[0].instance_id = 'notebook_C_0'
geometric[0].instance_id = 'geometric_0'
pencil_H[0].instance_id = 'pencil_H_0'
poster_H[0].instance_id = 'poster_H_0'
studentdesk_G[0].instance_id = 'studentdesk_G_0'
notebook_D[0].instance_id = 'notebook_D_0'
penstudent[0].instance_id = 'penstudent_0'
neonlight_D[0].instance_id = 'neonlight_D_0'
notebook_E[0].instance_id = 'notebook_E_0'
pen_teacher_E[0].instance_id = 'pen_teacher_E_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

book[0].position = [1.6815935948468974, 3.38504215164958, 0.015]
book[0].rotation = [0, 0, 0]
trashbin_A[0].position = [0.43782748308794583, 1.9876737775746207, 0.225]
trashbin_A[0].rotation = [0, 0, 0]
poster_A[0].position = [5.826553487633492, 1.9115251634058876, 0.5]
poster_A[0].rotation = [0, 0, 0]
pencil_A[0].position = [3.566043186328135, 0.5152417445663335, 0.004]
pencil_A[0].rotation = [0, 0, 0]
notebookb38c_A[0].position = [4.1138854607273645, 0.9873679047217347, 0.015]
notebookb38c_A[0].rotation = [0, 0, 0]
poster_B[0].position = [2.334032861621707, 1.9121024849070305, 0.5]
poster_B[0].rotation = [0, 0, 0]
pen_teacher_A[0].position = [5.543793304516621, 1.202509421425864, 0.006]
pen_teacher_A[0].rotation = [0, 0, 0]
pensstudent_A[0].position = [4.798004650736503, 2.635677368528324, 0.006]
pensstudent_A[0].rotation = [0, 0, 0]
pen_A[0].position = [3.578561080763814, 2.3135786309149986, 0.006]
pen_A[0].rotation = [0, 0, 0]
penteacher_A[0].position = [1.367644971531143, 0.6134692621707014, 0.0075]
penteacher_A[0].rotation = [0, 0, 0]
neonlight_A[0].position = [1.391245359894779, 0.5945263857323035, 0.02]
neonlight_A[0].rotation = [0, 0, 0]
pensstudent_B[0].position = [4.064454339914794, 2.070374365815416, 0.006]
pensstudent_B[0].rotation = [0, 0, 0]
pencil_B[0].position = [3.4892030794356144, 0.29693917119373126, 0.004]
pencil_B[0].rotation = [0, 0, 0]
pen_B[0].position = [5.3303335924399775, 3.711870940708411, 0.006]
pen_B[0].rotation = [0, 0, 0]
posterwall_A[0].position = [3.34625394014111, 1.7689100824589508, 0.5]
posterwall_A[0].rotation = [0, 0, 0]
pen_teacher_B[0].position = [2.680702743161606, 3.3948387676969967, 0.006]
pen_teacher_B[0].rotation = [0, 0, 0]
dispenser[0].position = [5.726803722778527, 3.1967778391063786, 0.575]
dispenser[0].rotation = [0, 0, 0]
trashbin_B[0].position = [4.456603158391357, 0.4075517864340217, 0.225]
trashbin_B[0].rotation = [0, 0, 0]
pensstudent_C[0].position = [5.201709008541238, 2.925527124033357, 0.006]
pensstudent_C[0].rotation = [0, 0, 0]
studentdesk_A[0].position = [0.616497033485522, 0.05252458393612125, 0.375]
studentdesk_A[0].rotation = [0, 0, 0]
notebookb38c_B[0].position = [5.907802337848691, 2.1941747578909103, 0.015]
notebookb38c_B[0].rotation = [0, 0, 0]
pensstudent_D[0].position = [4.460438023790833, 0.36904457012326164, 0.006]
pensstudent_D[0].rotation = [0, 0, 0]
notebookteacher[0].position = [2.998857972048358, 2.7380787459813023, 0.02]
notebookteacher[0].rotation = [0, 0, 0]
sculpture[0].position = [1.5811569797598382, 0.9713120635813062, 0.85]
sculpture[0].rotation = [0, 0, 0]
notebookdesk_A[0].position = [3.001424847232727, 2.7811824227313227, 0.015]
notebookdesk_A[0].rotation = [0, 0, 0]
pencil_C[0].position = [0.4996157341100438, 1.6979129029290574, 0.004]
pencil_C[0].rotation = [0, 0, 0]
studentdesk_B[0].position = [4.635694499296544, 0.5419386330537996, 0.375]
studentdesk_B[0].rotation = [0, 0, 0]
pen_C[0].position = [3.368321098070227, 2.6629849358205546, 0.006]
pen_C[0].rotation = [0, 0, 0]
notebook_A[0].position = [1.7429886401515993, 1.2730812344515288, 0.0125]
notebook_A[0].rotation = [0, 0, 0]
notebookdesk_B[0].position = [3.5647653926223555, 0.33187787192394547, 0.015]
notebookdesk_B[0].rotation = [0, 0, 0]
lamp_A[0].position = [1.992081383519119, 1.0606069824761684, 0.6]
lamp_A[0].rotation = [0, 0, 0]
plantnew[0].position = [0.8945004995576433, 3.1723300446906455, 0.625]
plantnew[0].rotation = [0, 0, 0]
studentdesk_C[0].position = [4.918171281975302, 2.208394681462093, 0.375]
studentdesk_C[0].rotation = [0, 0, 0]
pen_teacher_C[0].position = [0.5869248458194072, 3.2433197570402377, 0.006]
pen_teacher_C[0].rotation = [0, 0, 0]
pencil_D[0].position = [1.7123553658698893, 0.5630574741831813, 0.004]
pencil_D[0].rotation = [0, 0, 0]
chair_A[0].position = [1.5819988863832515, 0.5067770876358475, 0.425]
chair_A[0].rotation = [0, 0, 0]
pen_D[0].position = [3.584803402277416, 1.7390768073789702, 0.006]
pen_D[0].rotation = [0, 0, 0]
plant_A[0].position = [5.540972996519236, 0.8503270800702696, 0.6]
plant_A[0].rotation = [0, 0, 0]
posterwall_B[0].position = [0.6038768789891868, 1.4546450581478862, 0.5]
posterwall_B[0].rotation = [0, 0, 0]
poster_C[0].position = [3.5769486458316466, 2.7022712700357125, 0.5]
poster_C[0].rotation = [0, 0, 0]
notebookstudent[0].position = [0.8357686070210768, 2.084542047479273, 0.0125]
notebookstudent[0].rotation = [0, 0, 0]
pen_E[0].position = [1.8944256145675955, 0.08270867416814376, 0.006]
pen_E[0].rotation = [0, 0, 0]
pen_F[0].position = [4.865220708221205, 0.15192528142154815, 0.006]
pen_F[0].rotation = [0, 0, 0]
posterwall_C[0].position = [1.9051467964120428, 0.3334548989871857, 0.5]
posterwall_C[0].rotation = [0, 0, 0]
notebook_B[0].position = [3.9015482847835474, 2.086500445411407, 0.015]
notebook_B[0].rotation = [0, 0, 0]
plant_B[0].position = [5.361154931929456, 0.21839896138213755, 0.55]
plant_B[0].rotation = [0, 0, 0]
pencil_E[0].position = [2.7680369863450096, 1.1733570364278343, 0.004]
pencil_E[0].rotation = [0, 0, 0]
studentdesk_D[0].position = [3.5755723486188318, 3.9086642425757945, 0.375]
studentdesk_D[0].rotation = [0, 0, 0]
pen_G[0].position = [1.0803602383242776, 0.513224151053207, 0.006]
pen_G[0].rotation = [0, 0, 0]
cabinet[0].position = [0.6239759399166183, 2.4812459989761826, 0.6]
cabinet[0].rotation = [0, 0, 0]
studentdesk_E[0].position = [4.78831008944964, 0.8308112402689285, 0.375]
studentdesk_E[0].rotation = [0, 0, 0]
notebook_student_A[0].position = [2.192513009733613, 1.2231097092228898, 0.0125]
notebook_student_A[0].rotation = [0, 0, 0]
chair_B[0].position = [3.06850821807427, 0.8757016703220448, 0.425]
chair_B[0].rotation = [0, 0, 0]
pen_H[0].position = [1.579576084642405, 2.268465590146727, 0.006]
pen_H[0].rotation = [0, 0, 0]
neonlight_B[0].position = [0.6934016674514105, 2.771236660686785, 0.02]
neonlight_B[0].rotation = [0, 0, 0]
pencil_F[0].position = [0.18203720541750945, 2.549396102858169, 0.004]
pencil_F[0].rotation = [0, 0, 0]
pensstudent_E[0].position = [0.9553614486753281, 3.9229348530732993, 0.006]
pensstudent_E[0].rotation = [0, 0, 0]
pen_I[0].position = [3.2843089445048035, 1.5422978293300709, 0.006]
pen_I[0].rotation = [0, 0, 0]
pen_J[0].position = [4.671330688551043, 1.6809421175089643, 0.006]
pen_J[0].rotation = [0, 0, 0]
poster_D[0].position = [1.5117597693460938, 0.8177312503855414, 0.5]
poster_D[0].rotation = [0, 0, 0]
poster_E[0].position = [0.06970422770604823, 3.7328102766121103, 0.45]
poster_E[0].rotation = [0, 0, 0]
pen_teacher_D[0].position = [0.12648476469639003, 1.2707273389986078, 0.006]
pen_teacher_D[0].rotation = [0, 0, 0]
poster_F[0].position = [3.438180463208946, 2.7153280200148324, 0.45]
poster_F[0].rotation = [0, 0, 0]
penteacher_B[0].position = [1.7031563847478823, 1.1284568386462785, 0.0075]
penteacher_B[0].rotation = [0, 0, 0]
neonlight_C[0].position = [4.5704619434097395, 2.7507750644020796, 0.02]
neonlight_C[0].rotation = [0, 0, 0]
pensstudent_F[0].position = [2.382088667354677, 2.140782800714836, 0.006]
pensstudent_F[0].rotation = [0, 0, 0]
plant_C[0].position = [1.1456610247393741, 3.541493039383153, 0.6]
plant_C[0].rotation = [0, 0, 0]
plant_D[0].position = [0.5822383743687451, 3.628382598035016, 0.55]
plant_D[0].rotation = [0, 0, 0]
eraser_A[0].position = [1.1679748410209805, 1.6619239180611793, 0.006]
eraser_A[0].rotation = [0, 0, 0]
poster_G[0].position = [4.612918923638091, 0.34257210805974747, 0.5]
poster_G[0].rotation = [0, 0, 0]
eraser_B[0].position = [0.9958871949154615, 3.813201362333165, 0.006]
eraser_B[0].rotation = [0, 0, 0]
screen[0].position = [5.9658556219435575, 2.015042155136555, 0.75]
screen[0].rotation = [0, 0, 0]
pencil_G[0].position = [4.195958741559988, 1.3492373968609623, 0.004]
pencil_G[0].rotation = [0, 0, 0]
pen_K[0].position = [4.4714361782464564, 2.3382716660420164, 0.006]
pen_K[0].rotation = [0, 0, 0]
eraser_C[0].position = [1.0362347935118308, 0.9809429509457197, 0.006]
eraser_C[0].rotation = [0, 0, 0]
eraserteacher[0].position = [3.38737980347259, 0.5129272790454302, 0.006]
eraserteacher[0].rotation = [0, 0, 0]
posterwall_D[0].position = [2.489889377170961, 3.3856843749367065, 0.5]
posterwall_D[0].rotation = [0, 0, 0]
pendesk[0].position = [4.260732815899641, 2.953765322574518, 0.006]
pendesk[0].rotation = [0, 0, 0]
studentdesk_F[0].position = [2.476761482153794, 1.6723383483713397, 0.375]
studentdesk_F[0].rotation = [0, 0, 0]
bookshelf[0].position = [2.698449893168025, 2.516947355884247, 0.9]
bookshelf[0].rotation = [0, 0, 0]
teacherdesk[0].position = [4.600667777540371, 0.20920023422198142, 0.38]
teacherdesk[0].rotation = [0, 0, 0]
lamp_B[0].position = [1.4637997512857162, 3.462570646596389, 0.6]
lamp_B[0].rotation = [0, 0, 0]
notebook_student_B[0].position = [2.872781584071969, 0.3676724157288045, 0.0125]
notebook_student_B[0].rotation = [0, 0, 0]
notebook_C[0].position = [3.6025247375078497, 3.4413292732529874, 0.0125]
notebook_C[0].rotation = [0, 0, 0]
geometric[0].position = [1.86862787968832, 3.4956758701270467, 0.2]
geometric[0].rotation = [0, 0, 0]
pencil_H[0].position = [4.528110198491462, 3.2689133065987312, 0.004]
pencil_H[0].rotation = [0, 0, 0]
poster_H[0].position = [5.050416748694351, 1.6596838897276487, 0.45]
poster_H[0].rotation = [0, 0, 0]
studentdesk_G[0].position = [5.242897129557172, 1.9346444906383589, 0.375]
studentdesk_G[0].rotation = [0, 0, 0]
notebook_D[0].position = [4.894689792571862, 0.9541724853448152, 0.0125]
notebook_D[0].rotation = [0, 0, 0]
penstudent[0].position = [1.346837761346045, 0.9004527796488757, 0.0075]
penstudent[0].rotation = [0, 0, 0]
neonlight_D[0].position = [0.24782042291808204, 0.3292531810566164, 0.02]
neonlight_D[0].rotation = [0, 0, 0]
notebook_E[0].position = [5.71787632281961, 3.564923684072875, 0.015]
notebook_E[0].rotation = [0, 0, 0]
pen_teacher_E[0].position = [5.64924998668352, 2.5624127488154476, 0.006]
pen_teacher_E[0].rotation = [0, 0, 0]
book[0].position = [1.6815935948468974, 3.38504215164958, 0.015]
book[0].rotation = [0, 0, 0]
trashbin_A[0].position = [0.43782748308794583, 1.9876737775746207, 0.225]
trashbin_A[0].rotation = [0, 0, 0]
poster_A[0].position = [5.826553487633492, 1.9115251634058876, 0.5]
poster_A[0].rotation = [0, 0, 0]
pencil_A[0].position = [3.566043186328135, 0.5152417445663335, 0.004]
pencil_A[0].rotation = [0, 0, 0]
notebookb38c_A[0].position = [4.1138854607273645, 0.9873679047217347, 0.015]
notebookb38c_A[0].rotation = [0, 0, 0]
poster_B[0].position = [2.334032861621707, 1.9121024849070305, 0.5]
poster_B[0].rotation = [0, 0, 0]
pen_teacher_A[0].position = [5.543793304516621, 1.202509421425864, 0.006]
pen_teacher_A[0].rotation = [0, 0, 0]
pensstudent_A[0].position = [4.798004650736503, 2.635677368528324, 0.006]
pensstudent_A[0].rotation = [0, 0, 0]
pen_A[0].position = [3.578561080763814, 2.3135786309149986, 0.006]
pen_A[0].rotation = [0, 0, 0]
penteacher_A[0].position = [1.367644971531143, 0.6134692621707014, 0.0075]
penteacher_A[0].rotation = [0, 0, 0]
neonlight_A[0].position = [1.391245359894779, 0.5945263857323035, 0.02]
neonlight_A[0].rotation = [0, 0, 0]
pensstudent_B[0].position = [4.064454339914794, 2.070374365815416, 0.006]
pensstudent_B[0].rotation = [0, 0, 0]
pencil_B[0].position = [3.4892030794356144, 0.29693917119373126, 0.004]
pencil_B[0].rotation = [0, 0, 0]
pen_B[0].position = [5.3303335924399775, 3.711870940708411, 0.006]
pen_B[0].rotation = [0, 0, 0]
posterwall_A[0].position = [3.34625394014111, 1.7689100824589508, 0.5]
posterwall_A[0].rotation = [0, 0, 0]
pen_teacher_B[0].position = [2.680702743161606, 3.3948387676969967, 0.006]
pen_teacher_B[0].rotation = [0, 0, 0]
dispenser[0].position = [5.726803722778527, 3.1967778391063786, 0.575]
dispenser[0].rotation = [0, 0, 0]
trashbin_B[0].position = [4.456603158391357, 0.4075517864340217, 0.225]
trashbin_B[0].rotation = [0, 0, 0]
pensstudent_C[0].position = [5.201709008541238, 2.925527124033357, 0.006]
pensstudent_C[0].rotation = [0, 0, 0]
studentdesk_A[0].position = [0.616497033485522, 0.05252458393612125, 0.375]
studentdesk_A[0].rotation = [0, 0, 0]
notebookb38c_B[0].position = [5.907802337848691, 2.1941747578909103, 0.015]
notebookb38c_B[0].rotation = [0, 0, 0]
pensstudent_D[0].position = [4.460438023790833, 0.36904457012326164, 0.006]
pensstudent_D[0].rotation = [0, 0, 0]
notebookteacher[0].position = [2.998857972048358, 2.7380787459813023, 0.02]
notebookteacher[0].rotation = [0, 0, 0]
sculpture[0].position = [1.5811569797598382, 0.9713120635813062, 0.85]
sculpture[0].rotation = [0, 0, 0]
notebookdesk_A[0].position = [3.001424847232727, 2.7811824227313227, 0.015]
notebookdesk_A[0].rotation = [0, 0, 0]
pencil_C[0].position = [0.4996157341100438, 1.6979129029290574, 0.004]
pencil_C[0].rotation = [0, 0, 0]
studentdesk_B[0].position = [4.635694499296544, 0.5419386330537996, 0.375]
studentdesk_B[0].rotation = [0, 0, 0]
pen_C[0].position = [3.368321098070227, 2.6629849358205546, 0.006]
pen_C[0].rotation = [0, 0, 0]
notebook_A[0].position = [1.7429886401515993, 1.2730812344515288, 0.0125]
notebook_A[0].rotation = [0, 0, 0]
notebookdesk_B[0].position = [3.5647653926223555, 0.33187787192394547, 0.015]
notebookdesk_B[0].rotation = [0, 0, 0]
lamp_A[0].position = [1.992081383519119, 1.0606069824761684, 0.6]
lamp_A[0].rotation = [0, 0, 0]
plantnew[0].position = [0.8945004995576433, 3.1723300446906455, 0.625]
plantnew[0].rotation = [0, 0, 0]
studentdesk_C[0].position = [4.918171281975302, 2.208394681462093, 0.375]
studentdesk_C[0].rotation = [0, 0, 0]
pen_teacher_C[0].position = [0.5869248458194072, 3.2433197570402377, 0.006]
pen_teacher_C[0].rotation = [0, 0, 0]
pencil_D[0].position = [1.7123553658698893, 0.5630574741831813, 0.004]
pencil_D[0].rotation = [0, 0, 0]
chair_A[0].position = [1.5819988863832515, 0.5067770876358475, 0.425]
chair_A[0].rotation = [0, 0, 0]
pen_D[0].position = [3.584803402277416, 1.7390768073789702, 0.006]
pen_D[0].rotation = [0, 0, 0]
plant_A[0].position = [5.540972996519236, 0.8503270800702696, 0.6]
plant_A[0].rotation = [0, 0, 0]
posterwall_B[0].position = [0.6038768789891868, 1.4546450581478862, 0.5]
posterwall_B[0].rotation = [0, 0, 0]
poster_C[0].position = [3.5769486458316466, 2.7022712700357125, 0.5]
poster_C[0].rotation = [0, 0, 0]
notebookstudent[0].position = [0.8357686070210768, 2.084542047479273, 0.0125]
notebookstudent[0].rotation = [0, 0, 0]
pen_E[0].position = [1.8944256145675955, 0.08270867416814376, 0.006]
pen_E[0].rotation = [0, 0, 0]
pen_F[0].position = [4.865220708221205, 0.15192528142154815, 0.006]
pen_F[0].rotation = [0, 0, 0]
posterwall_C[0].position = [1.9051467964120428, 0.3334548989871857, 0.5]
posterwall_C[0].rotation = [0, 0, 0]
notebook_B[0].position = [3.9015482847835474, 2.086500445411407, 0.015]
notebook_B[0].rotation = [0, 0, 0]
plant_B[0].position = [5.361154931929456, 0.21839896138213755, 0.55]
plant_B[0].rotation = [0, 0, 0]
pencil_E[0].position = [2.7680369863450096, 1.1733570364278343, 0.004]
pencil_E[0].rotation = [0, 0, 0]
studentdesk_D[0].position = [3.5755723486188318, 3.9086642425757945, 0.375]
studentdesk_D[0].rotation = [0, 0, 0]
pen_G[0].position = [1.0803602383242776, 0.513224151053207, 0.006]
pen_G[0].rotation = [0, 0, 0]
cabinet[0].position = [0.6239759399166183, 2.4812459989761826, 0.6]
cabinet[0].rotation = [0, 0, 0]
studentdesk_E[0].position = [4.78831008944964, 0.8308112402689285, 0.375]
studentdesk_E[0].rotation = [0, 0, 0]
notebook_student_A[0].position = [2.192513009733613, 1.2231097092228898, 0.0125]
notebook_student_A[0].rotation = [0, 0, 0]
chair_B[0].position = [3.06850821807427, 0.8757016703220448, 0.425]
chair_B[0].rotation = [0, 0, 0]
pen_H[0].position = [1.579576084642405, 2.268465590146727, 0.006]
pen_H[0].rotation = [0, 0, 0]
neonlight_B[0].position = [0.6934016674514105, 2.771236660686785, 0.02]
neonlight_B[0].rotation = [0, 0, 0]
pencil_F[0].position = [0.18203720541750945, 2.549396102858169, 0.004]
pencil_F[0].rotation = [0, 0, 0]
pensstudent_E[0].position = [0.9553614486753281, 3.9229348530732993, 0.006]
pensstudent_E[0].rotation = [0, 0, 0]
pen_I[0].position = [3.2843089445048035, 1.5422978293300709, 0.006]
pen_I[0].rotation = [0, 0, 0]
pen_J[0].position = [4.671330688551043, 1.6809421175089643, 0.006]
pen_J[0].rotation = [0, 0, 0]
poster_D[0].position = [1.5117597693460938, 0.8177312503855414, 0.5]
poster_D[0].rotation = [0, 0, 0]
poster_E[0].position = [0.06970422770604823, 3.7328102766121103, 0.45]
poster_E[0].rotation = [0, 0, 0]
pen_teacher_D[0].position = [0.12648476469639003, 1.2707273389986078, 0.006]
pen_teacher_D[0].rotation = [0, 0, 0]
poster_F[0].position = [3.438180463208946, 2.7153280200148324, 0.45]
poster_F[0].rotation = [0, 0, 0]
penteacher_B[0].position = [1.7031563847478823, 1.1284568386462785, 0.0075]
penteacher_B[0].rotation = [0, 0, 0]
neonlight_C[0].position = [4.5704619434097395, 2.7507750644020796, 0.02]
neonlight_C[0].rotation = [0, 0, 0]
pensstudent_F[0].position = [2.382088667354677, 2.140782800714836, 0.006]
pensstudent_F[0].rotation = [0, 0, 0]
plant_C[0].position = [1.1456610247393741, 3.541493039383153, 0.6]
plant_C[0].rotation = [0, 0, 0]
plant_D[0].position = [0.5822383743687451, 3.628382598035016, 0.55]
plant_D[0].rotation = [0, 0, 0]
eraser_A[0].position = [1.1679748410209805, 1.6619239180611793, 0.006]
eraser_A[0].rotation = [0, 0, 0]
poster_G[0].position = [4.612918923638091, 0.34257210805974747, 0.5]
poster_G[0].rotation = [0, 0, 0]
eraser_B[0].position = [0.9958871949154615, 3.813201362333165, 0.006]
eraser_B[0].rotation = [0, 0, 0]
screen[0].position = [5.9658556219435575, 2.015042155136555, 0.75]
screen[0].rotation = [0, 0, 0]
pencil_G[0].position = [4.195958741559988, 1.3492373968609623, 0.004]
pencil_G[0].rotation = [0, 0, 0]
pen_K[0].position = [4.4714361782464564, 2.3382716660420164, 0.006]
pen_K[0].rotation = [0, 0, 0]
eraser_C[0].position = [1.0362347935118308, 0.9809429509457197, 0.006]
eraser_C[0].rotation = [0, 0, 0]
eraserteacher[0].position = [3.38737980347259, 0.5129272790454302, 0.006]
eraserteacher[0].rotation = [0, 0, 0]
posterwall_D[0].position = [2.489889377170961, 3.3856843749367065, 0.5]
posterwall_D[0].rotation = [0, 0, 0]
pendesk[0].position = [4.260732815899641, 2.953765322574518, 0.006]
pendesk[0].rotation = [0, 0, 0]
studentdesk_F[0].position = [2.476761482153794, 1.6723383483713397, 0.375]
studentdesk_F[0].rotation = [0, 0, 0]
bookshelf[0].position = [2.698449893168025, 2.516947355884247, 0.9]
bookshelf[0].rotation = [0, 0, 0]
teacherdesk[0].position = [4.600667777540371, 0.20920023422198142, 0.38]
teacherdesk[0].rotation = [0, 0, 0]
lamp_B[0].position = [1.4637997512857162, 3.462570646596389, 0.6]
lamp_B[0].rotation = [0, 0, 0]
notebook_student_B[0].position = [2.872781584071969, 0.3676724157288045, 0.0125]
notebook_student_B[0].rotation = [0, 0, 0]
notebook_C[0].position = [3.6025247375078497, 3.4413292732529874, 0.0125]
notebook_C[0].rotation = [0, 0, 0]
geometric[0].position = [1.86862787968832, 3.4956758701270467, 0.2]
geometric[0].rotation = [0, 0, 0]
pencil_H[0].position = [4.528110198491462, 3.2689133065987312, 0.004]
pencil_H[0].rotation = [0, 0, 0]
poster_H[0].position = [5.050416748694351, 1.6596838897276487, 0.45]
poster_H[0].rotation = [0, 0, 0]
studentdesk_G[0].position = [5.242897129557172, 1.9346444906383589, 0.375]
studentdesk_G[0].rotation = [0, 0, 0]
notebook_D[0].position = [4.894689792571862, 0.9541724853448152, 0.0125]
notebook_D[0].rotation = [0, 0, 0]
penstudent[0].position = [1.346837761346045, 0.9004527796488757, 0.0075]
penstudent[0].rotation = [0, 0, 0]
neonlight_D[0].position = [0.24782042291808204, 0.3292531810566164, 0.02]
neonlight_D[0].rotation = [0, 0, 0]
notebook_E[0].position = [5.71787632281961, 3.564923684072875, 0.015]
notebook_E[0].rotation = [0, 0, 0]
pen_teacher_E[0].position = [5.64924998668352, 2.5624127488154476, 0.006]
pen_teacher_E[0].rotation = [0, 0, 0]

solver.constraints = []

# The room is organized as a compact synthwave classroom. Student desks occupy
# two orderly rows, while the teacher area and presentation screen are at the
# north side. The east-wall doorway at (6.00, 1.41) is kept unobstructed.

def _set_floor_pose(asset, x, y, angle_degrees):
    """Initialize a floor-standing asset at the correct bounding-box height."""
    asset[0].position = [x, y, asset.size[2] / 2.0]
    asset[0].rotation = [0, 0, radians(angle_degrees)]


def _set_wall_pose(asset, x, y, z, angle_degrees):
    """Initialize a wall-mounted asset."""
    asset[0].position = [x, y, z]
    asset[0].rotation = [0, 0, radians(angle_degrees)]


def _set_surface_pose(asset, support, x, y, angle_degrees):
    """Initialize a small asset on the upper surface of its supporting asset."""
    support_top = support[0].position[2] + support.size[2] / 2.0
    asset[0].position = [x, y, support_top + asset.size[2] / 2.0]
    asset[0].rotation = [0, 0, radians(angle_degrees)]


def _pose_anchor(asset):
    """Create a fixed pose used to preserve an initialized placement."""
    return AssetInstance(
        position=list(asset[0].position),
        rotation=list(asset[0].rotation),
    )


# ---------------------------------------------------------------------------
# Floor-standing furniture and decorations
# ---------------------------------------------------------------------------

_floor_assets = [
    # Waste bins are accessible but outside the doorway circulation zone.
    (trashbin_A, 0.72, 0.30, 0),
    (trashbin_B, 5.48, 2.30, 180),

    # The dispenser is in the northeast corner, beyond the doorway.
    (dispenser, 5.72, 3.68, 180),

    # Seven student desks form two rows plus one desk in the presentation area.
    (studentdesk_A, 1.30, 0.80, 90),
    (studentdesk_B, 2.50, 0.80, 90),
    (studentdesk_C, 3.70, 0.80, 90),
    (studentdesk_D, 1.30, 1.90, 90),
    (studentdesk_F, 2.50, 1.90, 90),
    (studentdesk_G, 3.70, 1.90, 90),

    # o0050 lies midway between plants o0045 and o0066.
    (studentdesk_E, 3.00, 2.80, 90),

    # Teacher area along the north side.
    (teacherdesk, 4.80, 3.15, 90),
    (chair_A, 4.00, 3.15, 0),

    # o0052 remains clear of the doorway and will face the dispenser.
    (chair_B, 5.02, 2.22, 0),

    # Large decor and storage are kept around the room perimeter.
    (sculpture, 0.82, 2.65, 0),
    (cabinet, 0.225, 3.45, 0),
    (bookshelf, 0.175, 1.65, 0),

    # Plants decorate corners and frame studentdesk_E.
    (plantnew, 5.68, 0.35, 0),
    (plant_A, 0.40, 0.42, 0),
    (plant_B, 2.25, 2.80, 0),  # o0045
    (plant_C, 3.75, 2.80, 0),  # o0066
    (plant_D, 4.82, 0.35, 0),

    # Tall lamps are placed at the perimeter without blocking circulation.
    (lamp_A, 0.52, 3.62, 0),
    (lamp_B, 5.48, 3.22, 0),
]

for _asset_spec, _x, _y, _angle in _floor_assets:
    _set_floor_pose(_asset_spec, _x, _y, _angle)


# ---------------------------------------------------------------------------
# Wall-mounted posters, neon strips, and projector screen
# ---------------------------------------------------------------------------

_wall_assets = [
    # East wall: all pieces are north of the door opening.
    (poster_A, walls[0], 5.995, 2.42, 1.55, 180),
    (poster_B, walls[0], 5.995, 3.20, 1.55, 180),
    (neonlight_A, walls[0], 5.985, 3.58, 2.55, 180),

    # North wall: the large screen is centered, with decor at either side.
    (screen, walls[1], 3.00, 3.96, 1.55, 270),
    (posterwall_A, walls[1], 0.55, 3.995, 1.55, 270),
    (posterwall_B, walls[1], 1.30, 3.995, 1.55, 270),
    (poster_C, walls[1], 4.65, 3.995, 1.55, 270),
    (posterwall_C, walls[1], 5.42, 3.995, 1.55, 270),
    (neonlight_B, walls[1], 0.78, 3.985, 2.58, 270),

    # West wall: posters are mounted above/around the low-depth storage.
    (poster_D, walls[2], 0.005, 0.52, 1.72, 0),
    (poster_E, walls[2], 0.005, 1.30, 2.35, 0),
    (poster_F, walls[2], 0.005, 2.08, 2.35, 0),
    (poster_G, walls[2], 0.005, 2.82, 2.25, 0),
    (neonlight_C, walls[2], 0.015, 1.98, 2.92, 0),

    # South wall: spaced above the desks and away from the southeast plant.
    (posterwall_D, walls[3], 1.20, 0.005, 1.55, 90),
    (poster_H, walls[3], 2.15, 0.005, 1.50, 90),
    (neonlight_D, walls[3], 3.15, 0.015, 2.55, 90),
]

for _asset_spec, _wall, _x, _y, _z, _angle in _wall_assets:
    _set_wall_pose(_asset_spec, _x, _y, _z, _angle)


# ---------------------------------------------------------------------------
# Desk-top assets
# ---------------------------------------------------------------------------

_surface_assets = [
    # Student desk A
    (notebookb38c_A, studentdesk_A, 1.18, 0.68, 90),
    (pencil_A, studentdesk_A, 1.43, 0.65, 90),
    (pensstudent_A, studentdesk_A, 1.43, 0.82, 90),
    (pen_A, studentdesk_A, 1.18, 0.98, 90),
    (eraser_A, studentdesk_A, 1.40, 0.98, 0),
    (notebook_A, studentdesk_A, 1.18, 0.88, 90),

    # Student desk B; pencil_H is o0085 and is explicitly supported here
    # because this desk is o0026.
    (notebookb38c_B, studentdesk_B, 2.38, 0.68, 90),
    (pencil_H, studentdesk_B, 2.63, 0.65, 90),
    (pensstudent_B, studentdesk_B, 2.63, 0.82, 90),
    (pen_B, studentdesk_B, 2.38, 0.98, 90),
    (eraser_B, studentdesk_B, 2.62, 0.98, 0),
    (notebook_B, studentdesk_B, 2.38, 0.86, 90),

    # Student desk C
    (notebookdesk_A, studentdesk_C, 3.58, 0.68, 90),
    (pencil_C, studentdesk_C, 3.83, 0.65, 90),
    (pensstudent_C, studentdesk_C, 3.83, 0.82, 90),
    (pen_C, studentdesk_C, 3.58, 0.98, 90),
    (eraser_C, studentdesk_C, 3.82, 0.98, 0),
    (notebook_C, studentdesk_C, 3.58, 0.86, 90),

    # Student desk D
    (notebookdesk_B, studentdesk_D, 1.18, 1.78, 90),
    (pencil_D, studentdesk_D, 1.43, 1.75, 90),
    (pensstudent_D, studentdesk_D, 1.43, 1.92, 90),
    (pen_D, studentdesk_D, 1.18, 2.08, 90),
    (notebook_D, studentdesk_D, 1.18, 1.98, 90),
    (pen_E, studentdesk_D, 1.43, 2.08, 90),

    # Student desk E
    (notebook_student_A, studentdesk_E, 2.88, 2.68, 90),
    (pencil_E, studentdesk_E, 3.13, 2.65, 90),
    (pensstudent_E, studentdesk_E, 3.13, 2.82, 90),
    (pen_F, studentdesk_E, 2.88, 3.00, 90),
    (notebook_E, studentdesk_E, 2.88, 2.91, 90),
    (pen_G, studentdesk_E, 3.13, 3.00, 90),

    # Student desk F
    (notebook_student_B, studentdesk_F, 2.38, 1.78, 90),
    (pencil_F, studentdesk_F, 2.63, 1.75, 90),
    (pensstudent_F, studentdesk_F, 2.63, 1.92, 90),
    (pen_H, studentdesk_F, 2.38, 2.08, 90),
    (pen_I, studentdesk_F, 2.63, 2.08, 90),
    (notebookstudent, studentdesk_F, 2.38, 1.98, 90),

    # Student desk G
    (notebook_student_B, studentdesk_G, 3.58, 1.78, 90),
    (pencil_G, studentdesk_G, 3.83, 1.75, 90),
    (pensstudent_C, studentdesk_G, 3.83, 1.92, 90),
    (pen_J, studentdesk_G, 3.58, 2.08, 90),
    (pen_K, studentdesk_G, 3.83, 2.08, 90),
    (penstudent, studentdesk_G, 3.58, 1.98, 90),

    # Teacher desk
    (book, teacherdesk, 4.60, 2.92, 90),
    (notebookteacher, teacherdesk, 4.76, 3.15, 90),
    (pen_teacher_A, teacherdesk, 4.55, 3.42, 90),
    (pen_teacher_B, teacherdesk, 4.68, 3.42, 90),
    (pen_teacher_C, teacherdesk, 4.81, 3.42, 90),
    (pen_teacher_D, teacherdesk, 4.94, 3.42, 90),
    (pen_teacher_E, teacherdesk, 5.07, 3.42, 90),
    (penteacher_A, teacherdesk, 4.53, 3.66, 90),
    (penteacher_B, teacherdesk, 4.72, 3.66, 90),
    (eraserteacher, teacherdesk, 4.94, 3.66, 0),
    (pendesk, teacherdesk, 5.10, 3.66, 90),
    (geometric, teacherdesk, 5.05, 2.88, 0),
]

# Some source assets appear only once, so correct accidental duplicate support
# assignments before applying placements.
_surface_assets = [
    _entry for _entry in _surface_assets
    if _entry[0] not in (notebook_student_B, pensstudent_C)
] + [
    (notebook_student_B, studentdesk_G, 3.58, 1.78, 90),
    (pensstudent_C, studentdesk_C, 3.83, 0.82, 90),
]

for _asset_spec, _support, _x, _y, _angle in _surface_assets:
    _set_surface_pose(_asset_spec, _support, _x, _y, _angle)


# ---------------------------------------------------------------------------
# High-priority semantic constraints
# ---------------------------------------------------------------------------

# o0085 must remain on top of student desk o0026.
solver.on_top_of(pencil_H[0], studentdesk_B[0])

# Keep o0050 centered between plants o0045 and o0066.
solver.distance_constraint(
    studentdesk_E[0], plant_B[0], 0.70, 0.80, weight=10
)
solver.distance_constraint(
    studentdesk_E[0], plant_C[0], 0.70, 0.80, weight=10
)
solver.align_with(studentdesk_E[0], studentdesk_A[0], angle=0)

# o0052 faces the water dispenser.
solver.point_towards(chair_B[0], dispenser[0])

# The cabinet's shallow back is held against the west wall.
solver.against_wall(cabinet[0], walls[2])
solver.align_with(cabinet[0], AssetInstance(rotation=[0, 0, radians(0)]))


# ---------------------------------------------------------------------------
# General constraints for every floor-standing asset
# ---------------------------------------------------------------------------

for _asset_spec, _x, _y, _angle in _floor_assets:
    # A tight target region preserves the collision-free initialized layout.
    solver.distance_constraint(
        _asset_spec[0],
        _pose_anchor(_asset_spec),
        0.0,
        0.06,
        weight=10,
    )
    solver.align_with(
        _asset_spec[0],
        AssetInstance(rotation=[0, 0, radians(_angle)]),
        angle=0,
    )


# Every wall-mounted object receives both a position constraint and an
# orientation constraint. Against-wall constraints also let the solver retain
# contact if minor feasibility adjustments are required.
for _asset_spec, _wall, _x, _y, _z, _angle in _wall_assets:
    solver.against_wall(_asset_spec[0], _wall)
    solver.distance_constraint(
        _asset_spec[0],
        _pose_anchor(_asset_spec),
        0.0,
        0.08,
        weight=10,
    )
    solver.align_with(
        _asset_spec[0],
        AssetInstance(rotation=[0, 0, radians(_angle)]),
        angle=0,
    )


# Small objects remain supported by their assigned desks. The target-region
# constraints preserve their separated tabletop positions, while alignment
# constraints preserve the intended tidy orientation.
for _asset_spec, _support, _x, _y, _angle in _surface_assets:
    solver.on_top_of(_asset_spec[0], _support[0])
    solver.distance_constraint(
        _asset_spec[0],
        _pose_anchor(_asset_spec),
        0.0,
        0.035,
        weight=10,
    )
    solver.align_with(
        _asset_spec[0],
        AssetInstance(rotation=[0, 0, radians(_angle)]),
        angle=0,
    )

solver.constraints = []
pencil_A[0].position = [1.4299999475479126, 0.6499999761581421, 0.7549999952316284]
pencil_A[0].rotation = [0, 0, 1.5833626980517244]
pencil_A[0].optimize = 2
pencil_B[0].position = [3.4892029762268066, 0.2969391644001007, 0.004999999888241291]
pencil_B[0].rotation = [0, 0, 0.00314159280673765]
pencil_B[0].optimize = 2
eraser_A[0].position = [1.399999976158142, 0.9800000190734863, 0.7549999952316284]
eraser_A[0].rotation = [0, 0, 0.01256637125682779]
eraser_A[0].optimize = 2
poster_A[0].position = [6.002409934997559, 2.4200000762939453, 0.5]
poster_A[0].rotation = [0, 0, -3.1390517354391343]
poster_A[0].optimize = 2
plant_C[0].position = [3.75, 2.799999952316284, 0.6000000238418579]
plant_C[0].rotation = [0, 0, 0.01256637125682779]
plant_C[0].optimize = 2
pen_K[0].position = [3.8299999237060547, 2.0799999237060547, 0.7549999952316284]
pen_K[0].rotation = [0, 0, 1.5833626980517244]
pen_K[0].optimize = 2
notebook_D[0].position = [1.1799999475479126, 1.9800000190734863, 0.7649999856948853]
notebook_D[0].rotation = [0, 0, 1.5833626980517244]
notebook_D[0].optimize = 2
plant_B[0].position = [2.25, 2.799999952316284, 0.550000011920929]
plant_B[0].rotation = [0, 0, 0.01256637125682779]
plant_B[0].optimize = 2
neonlight_C[0].position = [0.01690562814474106, 1.9800000190734863, 0.019999999552965164]
neonlight_C[0].rotation = [0, 0, 0.0025409049851092386]
neonlight_C[0].optimize = 2
poster_D[0].position = [-0.0011201626621186733, 0.5199999809265137, 0.5]
poster_D[0].rotation = [0, 0, 0.002540918150658852]
poster_D[0].optimize = 2
pen_teacher_E[0].position = [5.070000171661377, 3.4200000762939453, 0.7649999856948853]
pen_teacher_E[0].rotation = [0, 0, 1.5833626980517244]
pen_teacher_E[0].optimize = 2
notebook_B[0].position = [2.380000114440918, 0.8600000143051147, 0.7649999856948853]
notebook_B[0].rotation = [0, 0, 1.5833626980517244]
notebook_B[0].optimize = 2
lamp_A[0].position = [0.5199999809265137, 3.619999885559082, 0.6000000238418579]
lamp_A[0].rotation = [0, 0, 0.00942477746072377]
lamp_A[0].optimize = 2
poster_E[0].position = [-0.0011201626621186733, 1.2999999523162842, 0.44999998807907104]
poster_E[0].rotation = [0, 0, 0.0025409193727581954]
poster_E[0].optimize = 2
notebookdesk_A[0].position = [3.5799999237060547, 0.6800000071525574, 0.7649999856948853]
notebookdesk_A[0].rotation = [0, 0, 1.5833626980517244]
notebookdesk_A[0].optimize = 2
studentdesk_C[0].position = [3.700000047683716, 0.800000011920929, 0.375]
studentdesk_C[0].rotation = [0, 0, 1.5990706612064889]
studentdesk_C[0].optimize = 2
poster_B[0].position = [6.002409934997559, 3.200000047683716, 0.5]
poster_B[0].rotation = [0, 0, -3.1390517354391343]
poster_B[0].optimize = 2
pen_teacher_B[0].position = [4.679999828338623, 3.4200000762939453, 0.7649999856948853]
pen_teacher_B[0].rotation = [0, 0, 1.5833626980517244]
pen_teacher_B[0].optimize = 2
pensstudent_D[0].position = [1.4299999475479126, 1.9199999570846558, 0.7549999952316284]
pensstudent_D[0].rotation = [0, 0, 1.5833626980517244]
pensstudent_D[0].optimize = 2
neonlight_A[0].position = [5.983094215393066, 3.249870777130127, 0.019999999552965164]
neonlight_A[0].rotation = [0, 0, -3.139051748604684]
neonlight_A[0].optimize = 2
plantnew[0].position = [5.679999828338623, 0.3499999940395355, 0.625]
plantnew[0].rotation = [0, 0, 0.00942477746072377]
plantnew[0].optimize = 2
pen_H[0].position = [2.380000114440918, 2.0799999237060547, 0.7549999952316284]
pen_H[0].rotation = [0, 0, 1.5833626980517244]
pen_H[0].optimize = 2
poster_C[0].position = [4.650000095367432, 4.002044677734375, 0.5]
poster_C[0].rotation = [0, 0, -1.568255409566411]
poster_C[0].optimize = 2
posterwall_B[0].position = [1.2999999523162842, 4.002044677734375, 0.5]
posterwall_B[0].rotation = [0, 0, -1.568255409566411]
posterwall_B[0].optimize = 2
eraserteacher[0].position = [4.946022033691406, 3.5323030948638916, 0.7649999856948853]
eraserteacher[0].rotation = [0, 0, 0.01256637125682779]
eraserteacher[0].optimize = 2
eraser_B[0].position = [2.619999885559082, 0.9800000190734863, 0.7549999952316284]
eraser_B[0].rotation = [0, 0, 0.01256637125682779]
eraser_B[0].optimize = 2
teacherdesk[0].position = [4.800000190734863, 3.1500000953674316, 0.3799999952316284]
teacherdesk[0].rotation = [0, 0, 1.617920218713948]
teacherdesk[0].optimize = 2
pen_teacher_D[0].position = [4.940000057220459, 3.4200000762939453, 0.7649999856948853]
pen_teacher_D[0].rotation = [0, 0, 1.5833626980517244]
pen_teacher_D[0].optimize = 2
pensstudent_E[0].position = [3.130000114440918, 2.819999933242798, 0.7549999952316284]
pensstudent_E[0].rotation = [0, 0, 1.5833626980517244]
pensstudent_E[0].optimize = 2
notebookb38c_B[0].position = [2.380000114440918, 0.6800000071525574, 0.7649999856948853]
notebookb38c_B[0].rotation = [0, 0, 1.5833626980517244]
notebookb38c_B[0].optimize = 2
book[0].position = [4.599999904632568, 2.9200000762939453, 0.7749999761581421]
book[0].rotation = [0, 0, 1.5833626980517244]
book[0].optimize = 2
pensstudent_B[0].position = [2.630000114440918, 0.8199999928474426, 0.7549999952316284]
pensstudent_B[0].rotation = [0, 0, 1.5833626980517244]
pensstudent_B[0].optimize = 2
studentdesk_A[0].position = [1.2999999523162842, 0.800000011920929, 0.375]
studentdesk_A[0].rotation = [0, 0, 1.6022122525607134]
studentdesk_A[0].optimize = 2
pencil_E[0].position = [3.130000114440918, 2.6500000953674316, 0.7549999952316284]
pencil_E[0].rotation = [0, 0, 1.5833626980517244]
pencil_E[0].optimize = 2
pensstudent_C[0].position = [3.8299999237060547, 0.8199999928474426, 0.7549999952316284]
pensstudent_C[0].rotation = [0, 0, 1.5833626980517244]
pensstudent_C[0].optimize = 2
geometric[0].position = [5.050000190734863, 2.880000114440918, 0.9599999785423279]
geometric[0].rotation = [0, 0, 0.01256637125682779]
geometric[0].optimize = 2
plant_D[0].position = [4.820000171661377, 0.3499999940395355, 0.550000011920929]
plant_D[0].rotation = [0, 0, 0.00942477746072377]
plant_D[0].optimize = 2
pen_F[0].position = [2.880000114440918, 3.0, 0.7549999952316284]
pen_F[0].rotation = [0, 0, 1.5833626980517244]
pen_F[0].optimize = 2
dispenser[0].position = [5.71999979019165, 3.680000066757202, 0.574999988079071]
dispenser[0].rotation = [0, 0, -3.1290262823329655]
dispenser[0].optimize = 2
poster_F[0].position = [-0.0011201626621186733, 2.0799999237060547, 0.44999998807907104]
poster_F[0].rotation = [0, 0, 0.0025409193727581954]
poster_F[0].optimize = 2
studentdesk_D[0].position = [1.2999999523162842, 1.899999976158142, 0.375]
studentdesk_D[0].rotation = [0, 0, 1.5990706612064889]
studentdesk_D[0].optimize = 2
plant_A[0].position = [0.4000000059604645, 0.41999998688697815, 0.6000000238418579]
plant_A[0].rotation = [0, 0, 0.00942477746072377]
plant_A[0].optimize = 2
trashbin_B[0].position = [5.480000019073486, 2.299999952316284, 0.22499999403953552]
trashbin_B[0].rotation = [0, 0, -3.1321678761290697]
trashbin_B[0].optimize = 2
studentdesk_B[0].position = [2.5, 0.800000011920929, 0.375]
studentdesk_B[0].rotation = [0, 0, 1.6022122525607134]
studentdesk_B[0].optimize = 2
pencil_D[0].position = [1.4299999475479126, 1.75, 0.7549999952316284]
pencil_D[0].rotation = [0, 0, 1.5833626980517244]
pencil_D[0].optimize = 2
neonlight_B[0].position = [0.7799999713897705, 3.9830944538116455, 0.019999999552965164]
neonlight_B[0].rotation = [0, 0, -1.5682554227319598]
neonlight_B[0].optimize = 2
pen_teacher_A[0].position = [4.550000190734863, 3.4200000762939453, 0.7649999856948853]
pen_teacher_A[0].rotation = [0, 0, 1.5833626980517244]
pen_teacher_A[0].optimize = 2
pen_I[0].position = [2.630000114440918, 2.0799999237060547, 0.7549999952316284]
pen_I[0].rotation = [0, 0, 1.5833626980517244]
pen_I[0].optimize = 2
penteacher_B[0].position = [4.726510047912598, 3.521951198577881, 0.7649999856948853]
penteacher_B[0].rotation = [0, 0, 1.5833626980517244]
penteacher_B[0].optimize = 2
poster_G[0].position = [-0.0011201626621186733, 2.819999933242798, 0.5]
poster_G[0].rotation = [0, 0, 0.002540918150658852]
poster_G[0].optimize = 2
bookshelf[0].position = [0.17499999701976776, 1.649999976158142, 0.8999999761581421]
bookshelf[0].rotation = [0, 0, 0.00942477746072377]
bookshelf[0].optimize = 2
pensstudent_F[0].position = [2.630000114440918, 1.9199999570846558, 0.7549999952316284]
pensstudent_F[0].rotation = [0, 0, 1.5833626980517244]
pensstudent_F[0].optimize = 2
posterwall_D[0].position = [1.2000000476837158, -0.0011201626621186733, 0.5]
posterwall_D[0].rotation = [0, 0, 1.5733372449455554]
posterwall_D[0].optimize = 2
pen_E[0].position = [1.4299999475479126, 2.0799999237060547, 0.7549999952316284]
pen_E[0].rotation = [0, 0, 1.5833626980517244]
pen_E[0].optimize = 2
studentdesk_E[0].position = [3.0, 2.799999952316284, 0.375]
studentdesk_E[0].rotation = [0, 0, 1.5982274872640785]
studentdesk_E[0].optimize = 2
notebookstudent[0].position = [2.380000114440918, 1.9800000190734863, 0.7649999856948853]
notebookstudent[0].rotation = [0, 0, 1.5833626980517244]
notebookstudent[0].optimize = 2
notebook_C[0].position = [3.5799999237060547, 0.8600000143051147, 0.7649999856948853]
notebook_C[0].rotation = [0, 0, 1.5833626980517244]
notebook_C[0].optimize = 2
eraser_C[0].position = [3.819999933242798, 0.9800000190734863, 0.7549999952316284]
eraser_C[0].rotation = [0, 0, 0.01256637125682779]
eraser_C[0].optimize = 2
pen_D[0].position = [1.1799999475479126, 2.0799999237060547, 0.7549999952316284]
pen_D[0].rotation = [0, 0, 1.5833626980517244]
pen_D[0].optimize = 2
posterwall_A[0].position = [0.550000011920929, 4.002044677734375, 0.5]
posterwall_A[0].rotation = [0, 0, -1.568255409566411]
posterwall_A[0].optimize = 2
neonlight_D[0].position = [3.1500000953674316, 0.01690562814474106, 0.019999999552965164]
neonlight_D[0].rotation = [0, 0, 1.5733372317800058]
neonlight_D[0].optimize = 2
notebook_A[0].position = [1.1799999475479126, 0.8799999952316284, 0.7649999856948853]
notebook_A[0].rotation = [0, 0, 1.5833626980517244]
notebook_A[0].optimize = 2
chair_A[0].position = [4.0, 3.1500000953674316, 0.42500001192092896]
chair_A[0].rotation = [0, 0, 0.00942477746072377]
chair_A[0].optimize = 2
lamp_B[0].position = [5.480000019073486, 3.2200000286102295, 0.6000000238418579]
lamp_B[0].rotation = [0, 0, 0.00942477746072377]
lamp_B[0].optimize = 2
notebook_E[0].position = [2.880000114440918, 2.9100000858306885, 0.7649999856948853]
notebook_E[0].rotation = [0, 0, 1.5833626980517244]
notebook_E[0].optimize = 2
posterwall_C[0].position = [5.420000076293945, 4.002044677734375, 0.5]
posterwall_C[0].rotation = [0, 0, -1.568255409566411]
posterwall_C[0].optimize = 2
notebook_student_B[0].position = [3.5799999237060547, 1.7799999713897705, 0.7649999856948853]
notebook_student_B[0].rotation = [0, 0, 1.5833626980517244]
notebook_student_B[0].optimize = 2
pen_teacher_C[0].position = [4.809999942779541, 3.4200000762939453, 0.7649999856948853]
pen_teacher_C[0].rotation = [0, 0, 1.5833626980517244]
pen_teacher_C[0].optimize = 2
notebook_student_A[0].position = [2.880000114440918, 2.680000066757202, 0.7649999856948853]
notebook_student_A[0].rotation = [0, 0, 1.5833626980517244]
notebook_student_A[0].optimize = 2
sculpture[0].position = [0.8199999928474426, 2.6500000953674316, 0.8500000238418579]
sculpture[0].rotation = [0, 0, 0.00942477746072377]
sculpture[0].optimize = 2
notebookb38c_A[0].position = [1.1799999475479126, 0.6800000071525574, 0.7649999856948853]
notebookb38c_A[0].rotation = [0, 0, 1.5833626980517244]
notebookb38c_A[0].optimize = 2
pensstudent_A[0].position = [1.4299999475479126, 0.8199999928474426, 0.7549999952316284]
pensstudent_A[0].rotation = [0, 0, 1.5833626980517244]
pensstudent_A[0].optimize = 2
cabinet[0].position = [0.22753958404064178, 3.450000047683716, 0.6000000238418579]
cabinet[0].rotation = [0, 0, 0.0056515189159214085]
cabinet[0].optimize = 2
penteacher_A[0].position = [4.536931991577148, 3.5130109786987305, 0.7649999856948853]
penteacher_A[0].rotation = [0, 0, 1.5833626980517244]
penteacher_A[0].optimize = 2
notebookteacher[0].position = [4.760000228881836, 3.1500000953674316, 0.7799999713897705]
notebookteacher[0].rotation = [0, 0, 1.5833626980517244]
notebookteacher[0].optimize = 2
poster_H[0].position = [2.1500000953674316, -0.0011201626621186733, 0.44999998807907104]
poster_H[0].rotation = [0, 0, 1.573337246167655]
poster_H[0].optimize = 2
pen_C[0].position = [3.5799999237060547, 0.9800000190734863, 0.7549999952316284]
pen_C[0].rotation = [0, 0, 1.5833626980517244]
pen_C[0].optimize = 2
penstudent[0].position = [3.5799999237060547, 1.9800000190734863, 0.7549999952316284]
penstudent[0].rotation = [0, 0, 1.5833626980517244]
penstudent[0].optimize = 2
pen_J[0].position = [3.5799999237060547, 2.0799999237060547, 0.7549999952316284]
pen_J[0].rotation = [0, 0, 1.5833626980517244]
pen_J[0].optimize = 2
pencil_F[0].position = [2.630000114440918, 1.75, 0.7549999952316284]
pencil_F[0].rotation = [0, 0, 1.5833626980517244]
pencil_F[0].optimize = 2
pen_B[0].position = [2.380000114440918, 0.9800000190734863, 0.7549999952316284]
pen_B[0].rotation = [0, 0, 1.5833626980517244]
pen_B[0].optimize = 2
pencil_H[0].position = [2.630000114440918, 0.6499999761581421, 0.7549999952316284]
pencil_H[0].rotation = [0, 0, 1.586504290712113]
pencil_H[0].optimize = 2
trashbin_A[0].position = [0.7200000286102295, 0.30000001192092896, 0.22499999403953552]
trashbin_A[0].rotation = [0, 0, 0.00942477746072377]
trashbin_A[0].optimize = 2
pencil_G[0].position = [3.8299999237060547, 1.75, 0.7549999952316284]
pencil_G[0].rotation = [0, 0, 1.5833626980517244]
pencil_G[0].optimize = 2
pendesk[0].position = [5.1056671142578125, 3.5398316383361816, 0.7649999856948853]
pendesk[0].rotation = [0, 0, 1.5833626980517244]
pendesk[0].optimize = 2
studentdesk_G[0].position = [3.700000047683716, 1.899999976158142, 0.375]
studentdesk_G[0].rotation = [0, 0, 1.5959290669047523]
studentdesk_G[0].optimize = 2
pen_G[0].position = [3.130000114440918, 3.0, 0.7549999952316284]
pen_G[0].rotation = [0, 0, 1.5833626980517244]
pen_G[0].optimize = 2
notebookdesk_B[0].position = [1.1799999475479126, 1.7799999713897705, 0.7649999856948853]
notebookdesk_B[0].rotation = [0, 0, 1.5833626980517244]
notebookdesk_B[0].optimize = 2
chair_B[0].position = [5.019999980926514, 2.2200000286102295, 0.42500001192092896]
chair_B[0].rotation = [0, 0, 0.022791819844203844]
chair_B[0].optimize = 2
pen_A[0].position = [1.1799999475479126, 0.9800000190734863, 0.7549999952316284]
pen_A[0].rotation = [0, 0, 1.5833626980517244]
pen_A[0].optimize = 2
pencil_C[0].position = [3.8299999237060547, 0.6499999761581421, 0.7549999952316284]
pencil_C[0].rotation = [0, 0, 1.5833626980517244]
pencil_C[0].optimize = 2
screen[0].position = [3.0, 3.954923629760742, 0.75]
screen[0].rotation = [0, 0, -1.5682554386415961]
screen[0].optimize = 2
studentdesk_F[0].position = [2.5, 1.899999976158142, 0.375]
studentdesk_F[0].rotation = [0, 0, 1.5959290669047523]
studentdesk_F[0].optimize = 2

