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
vaporbottle_A = Assets(description="A neon‑pink vaporwave wine bottle with a sleek cylindrical body, glossy finish, subtle pastel highlights, smooth surface", size=[0.09, 0.09, 0.32], placements=[AssetInstance() for _ in range(1)])
wineglass_A = Assets(description="A glass wine glass with a sleek cylindrical stem and shallow bowl, featuring neon blue pastel gradient vaporwave colors, glossy finish, and a subtle glowing rim.", size=[0.10, 0.10, 0.21], placements=[AssetInstance() for _ in range(1)])
vaporbottle_B = Assets(description="A vaporwave wine bottle with glitch‑art graphics, rectangular body, pastel neon stripes and a glossy finish.", size=[0.08, 0.11, 0.31], placements=[AssetInstance() for _ in range(1)])
glitchpanelwall_A = Assets(description="A single piece of thin and upright surreal glitch panel with abstract 1990s motifs, rectangular shape, flat surface, and a metallic border.", size=[0.05, 0.75, 1.20], placements=[AssetInstance() for _ in range(1)])
glitchbottle_A = Assets(description="A cylindrical vaporwave wine bottle covered in bright glitch art patterns and neon accents", size=[0.09, 0.09, 0.32], placements=[AssetInstance() for _ in range(1)])
glitchpanelcab = Assets(description="A single piece of thin and upright glitch panel displaying 1990s digital distortion, rectangular shape, flat surface, and a glossy black frame.", size=[0.05, 0.70, 1.10], placements=[AssetInstance() for _ in range(1)])
opener_A = Assets(description="A compact vaporwave wine opener with a glossy pastel gradient handle and a sleek rectangular metal body, featuring a retro 90s pixel‑art pattern on the grip", size=[0.04, 0.16, 0.03], placements=[AssetInstance() for _ in range(1)])
opener_B = Assets(description="A retro vaporwave wine opener with a rectangular, angular handle, glossy neon pink and teal gradient finish, plastic material, low‑profile design", size=[0.04, 0.15, 0.03], placements=[AssetInstance() for _ in range(1)])
sign_A = Assets(description="A thin upright neon sign with a 90s phrase in pastel pink lettering, glowing tube edges and a frosted acrylic backing", size=[0.06, 0.80, 0.35], placements=[AssetInstance() for _ in range(1)])
neonsign_A = Assets(description="A thin upright neon sign with 90s phrase typography, bright cyan lettering on a dark matte backing, rectangular frame", size=[0.06, 0.90, 0.40], placements=[AssetInstance() for _ in range(1)])
glitchpanel_A = Assets(description="A thin rectangular panel with 1990s style glitch graphics, flat surface, low‑profile frame and a faint neon backlight.", size=[0.04, 0.42, 0.30], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="A modern wine chair in vaporwave style, featuring a sleek angular seat, neon pink upholstery, retro computer keyboard pattern embossing, and chrome legs.", size=[0.55, 0.52, 0.82], placements=[AssetInstance() for _ in range(1)])
neonsign_B = Assets(description="A single piece of thin and upright neon sign displaying a 90s phrase, rectangular frame with bright neon tubing and a dark backing", size=[0.06, 0.85, 0.42], placements=[AssetInstance() for _ in range(1)])
label_A = Assets(description="A small rectangular wine bottle label with 1990s style neon typography, glossy surface and a thin raised border", size=[0.01, 0.10, 0.07], placements=[AssetInstance() for _ in range(1)])
vaporbottle_C = Assets(description="A rectangular-shaped red wine bottle featuring vaporwave graphics, neon pink accents, glossy lacquered surface, angular silhouette.", size=[0.08, 0.11, 0.31], placements=[AssetInstance() for _ in range(1)])
sign_B = Assets(description="A single piece of thin and upright neon sign with a 90s phrase in glowing pastel pink lettering", size=[0.05, 0.75, 0.32], placements=[AssetInstance() for _ in range(1)])
vaporbottle_pastel_A = Assets(description="A pastel‑gradient vaporwave wine bottle with a smooth cylindrical body, soft pink‑blue gradient glaze, glossy finish", size=[0.09, 0.09, 0.32], placements=[AssetInstance() for _ in range(1)])
glitchpanel_B = Assets(description="A single piece of thin and upright panel displaying surreal glitch art, rectangular shape, glossy surface with shifting colors.", size=[0.05, 0.72, 1.05], placements=[AssetInstance() for _ in range(1)])
pastelbottle_A = Assets(description="A vaporwave wine bottle with a pastel gradient finish, smooth cylindrical shape and a soft matte surface", size=[0.09, 0.09, 0.31], placements=[AssetInstance() for _ in range(1)])
vaporbottle_D = Assets(description="A vaporwave wine bottle with glitch‑art graphics, sleek cylindrical form, neon‑pink and teal accents, glossy surface", size=[0.09, 0.09, 0.32], placements=[AssetInstance() for _ in range(1)])
neonsign_C = Assets(description="A single piece of thin and upright neon sign bearing a 90s internet phrase, rectangular frame, bright pink neon tubes, translucent backing.", size=[0.06, 0.95, 0.42], placements=[AssetInstance() for _ in range(1)])
label_B = Assets(description="A small square wine bottle label with a retro 1990s neon pink pattern and glossy finish", size=[0.01, 0.08, 0.08], placements=[AssetInstance() for _ in range(1)])
surrealpanel_A = Assets(description="A single piece of thin and upright rectangular panel displaying surreal glitch‑art imagery, glossy finish, and faint backlighting.", size=[0.05, 0.80, 1.10], placements=[AssetInstance() for _ in range(1)])
sign_C = Assets(description="A thin upright neon sign with a 90s phrase in pastel pink lettering, glowing tube edges and a frosted acrylic backing", size=[0.06, 0.80, 0.35], placements=[AssetInstance() for _ in range(1)])
vaporbottlerack_A = Assets(description="A pastel gradient vapor bottle with a smooth cylindrical form, soft pastel colors blending along the surface, and a matte finish.", size=[0.09, 0.09, 0.31], placements=[AssetInstance() for _ in range(1)])
vaporbottle_glitch_A = Assets(description="A glitch‑art vaporwave wine bottle with a distorted, pixelated surface, bright magenta and cyan colors, irregular cylindrical silhouette", size=[0.10, 0.10, 0.33], placements=[AssetInstance() for _ in range(1)])
vaporbottlerack_B = Assets(description="A neon pink vapor bottle with a sleek cylindrical shape, glossy pink surface, and a subtle neon glow.", size=[0.09, 0.09, 0.32], placements=[AssetInstance() for _ in range(1)])
vaporbottle_E = Assets(description="A rectangular-shaped red wine bottle featuring vaporwave graphics, neon pink accents, glossy lacquered surface, angular silhouette.", size=[0.08, 0.11, 0.31], placements=[AssetInstance() for _ in range(1)])
vaporbottle_F = Assets(description="A vaporwave wine bottle with glitch‑art graphics, rectangular body, pastel neon stripes and a glossy finish.", size=[0.08, 0.11, 0.31], placements=[AssetInstance() for _ in range(1)])
candle_A = Assets(description="A neon pink candle with a 1990s retro glow, cylindrical body and a slightly tapered top", size=[0.07, 0.07, 0.16], placements=[AssetInstance() for _ in range(1)])
vintagebottle = Assets(description="A cylindrical red wine bottle with a vintage 1990s label, matte finish, slightly textured glass, tapered neck.", size=[0.09, 0.09, 0.31], placements=[AssetInstance() for _ in range(1)])
surrealpanel_B = Assets(description="A single piece of thin and upright rectangular panel displaying surreal glitch‑art imagery, glossy finish, and faint backlighting.", size=[0.05, 0.80, 1.10], placements=[AssetInstance() for _ in range(1)])
winebook_A = Assets(description="A thin rectangular wine book with 90s internet aesthetic cover, pastel pixelated graphics, glossy paper, slightly rounded edges.", size=[0.18, 0.24, 0.03], placements=[AssetInstance() for _ in range(1)])
ambientlight_A = Assets(description="A low-slung ambient floor light with a pastel purple cylindrical shade, smooth surface, and a soft glowing interior.", size=[0.32, 0.32, 0.42], placements=[AssetInstance() for _ in range(1)])
corkscrew_A = Assets(description="A vintage corkscrew with a 90s internet aesthetic, long slender metal shaft, angular wooden handle and a twisted spiral tip", size=[0.10, 0.16, 0.04], placements=[AssetInstance() for _ in range(1)])
pixelpanel_A = Assets(description="A single piece of thin and upright panel featuring pixel art, square shape, flat matte surface with vibrant 8-bit graphics.", size=[0.04, 0.60, 0.60], placements=[AssetInstance() for _ in range(1)])
label_C = Assets(description="A small rectangular wine bottle label with 1990s style neon typography, glossy surface and a thin raised border", size=[0.01, 0.10, 0.07], placements=[AssetInstance() for _ in range(1)])
neonsign_D = Assets(description="A thin single‑piece upright neon sign displaying a 90s phrase, bright cyan lettering on a dark background", size=[0.05, 0.62, 0.28], placements=[AssetInstance() for _ in range(1)])
wineglass_B = Assets(description="A glass wineglass with a sleek cylindrical stem and a shallow bowl, glowing neon blue with pastel gradient swirl, smooth glossy surface.", size=[0.10, 0.10, 0.21], placements=[AssetInstance() for _ in range(1)])
rack_A = Assets(description="A vaporwave wine rack with a rectangular frame, pastel gradient panels, glitch art overlay, and curved shelves, finished in soft pink and teal hues, featuring a neon-lit edge.", size=[0.38, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
lamp = Assets(description="A retro floor lamp with a slender neon‑pink cylindrical shade, curved metal stand, and a glossy finish, evoking 90s club lighting", size=[0.45, 0.38, 1.65], placements=[AssetInstance() for _ in range(1)])
winebottlecab_A = Assets(description="A square-shaped red wine bottle with vaporwave aesthetic, featuring bold pastel gradient wrap, glossy surface, and a flat label.", size=[0.09, 0.12, 0.28], placements=[AssetInstance() for _ in range(1)])
candle_B = Assets(description="A cylindrical neon candle with a translucent 1990s style glass, emitting a soft pink glow, smooth surface, and a tapered top.", size=[0.08, 0.08, 0.17], placements=[AssetInstance() for _ in range(1)])
rack_B = Assets(description="A vaporwave wine rack with a rectangular frame, pastel gradient panels, glitch art overlay, and curved shelves, finished in soft pink and teal hues, featuring a neon-lit edge.", size=[0.38, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
vaporbottle_G = Assets(description="A vaporwave wine bottle with glitch‑art graphics, sleek cylindrical form, neon‑pink and teal accents, glossy surface", size=[0.09, 0.09, 0.32], placements=[AssetInstance() for _ in range(1)])
wineglass_C = Assets(description="A glass wineglass with a sleek cylindrical stem and a shallow bowl, glowing neon blue with pastel gradient swirl, smooth glossy surface.", size=[0.10, 0.10, 0.21], placements=[AssetInstance() for _ in range(1)])
corkscrew_B = Assets(description="A slender vintage corkscrew with a 90s internet‑style pixelated handle, matte black metal shaft and a tiny chrome lever", size=[0.09, 0.15, 0.04], placements=[AssetInstance() for _ in range(1)])
vaporbottle_H = Assets(description="A rectangular-shaped red wine bottle featuring vaporwave graphics, neon pink accents, glossy lacquered surface, angular silhouette.", size=[0.08, 0.11, 0.31], placements=[AssetInstance() for _ in range(1)])
pixelpanel_wall_A = Assets(description="A single piece of thin upright 8‑bit pixel art panel, rectangular with bright retro graphics and a matte frame", size=[0.04, 0.55, 0.75], placements=[AssetInstance() for _ in range(1)])
opener_C = Assets(description="A small rectangular vaporwave wine opener with 1990s retro graphics, glossy pastel finish and a sleek curved handle", size=[0.04, 0.15, 0.03], placements=[AssetInstance() for _ in range(1)])
pinkbottle_A = Assets(description="A neon‑pink wine bottle with a vaporwave aesthetic, smooth cylindrical shape, pastel gradient label and a glossy finish", size=[0.09, 0.09, 0.32], placements=[AssetInstance() for _ in range(1)])
winebottlecab_B = Assets(description="A square-shaped red wine bottle with vaporwave aesthetic, featuring bold pastel gradient wrap, glossy surface, and a flat label.", size=[0.09, 0.12, 0.28], placements=[AssetInstance() for _ in range(1)])
vaporbottle_glitch_B = Assets(description="A glitch‑art vaporwave wine bottle with a distorted, pixelated surface, bright magenta and cyan colors, irregular cylindrical silhouette", size=[0.10, 0.10, 0.33], placements=[AssetInstance() for _ in range(1)])
pixelpanel_B = Assets(description="A single piece of thin and upright square panel featuring 8‑bit pixel art graphics, matte black border, and a subtle LED backlight.", size=[0.05, 0.60, 0.60], placements=[AssetInstance() for _ in range(1)])
pixelpanel_wall_B = Assets(description="A single piece of thin and upright 8‑bit pixel art panel, rectangular, with bright blocky graphics and a matte finish.", size=[0.04, 0.55, 0.75], placements=[AssetInstance() for _ in range(1)])
ambientlight_B = Assets(description="A low‑profile square floor lamp with a pastel purple frosted diffuser, soft LED core, and a sleek brushed metal base.", size=[0.34, 0.34, 0.24], placements=[AssetInstance() for _ in range(1)])
pixelpanel_wall_C = Assets(description="A single piece of thin and upright 8‑bit pixel art panel, rectangular, with bright blocky graphics and a matte finish.", size=[0.04, 0.55, 0.75], placements=[AssetInstance() for _ in range(1)])
vaporbottle_I = Assets(description="A rectangular-shaped red wine bottle featuring vaporwave graphics, neon pink accents, glossy lacquered surface, angular silhouette.", size=[0.08, 0.11, 0.31], placements=[AssetInstance() for _ in range(1)])
pastelbottle_B = Assets(description="A smooth cylindrical vaporwave wine bottle with a soft pastel gradient and subtle 90s pixel texture", size=[0.09, 0.09, 0.31], placements=[AssetInstance() for _ in range(1)])
romanbust = Assets(description="A compact marble‑like bust of a Roman figure, slightly stylized with 90s pixel distortion texture, rounded base, and a subtle glossy sheen.", size=[0.28, 0.42, 0.58], placements=[AssetInstance() for _ in range(1)])
label_D = Assets(description="A small square wine bottle label with a retro 1990s neon pink pattern and glossy finish", size=[0.01, 0.08, 0.08], placements=[AssetInstance() for _ in range(1)])
floorlamp_A = Assets(description="A retro floor lamp with vaporwave design, tall slender stand, curved shade and a pastel gradient finish", size=[0.48, 0.40, 1.70], placements=[AssetInstance() for _ in range(1)])
glitchpanel_C = Assets(description="A single piece of thin and upright panel displaying surreal glitch art, rectangular shape, glossy surface with shifting colors.", size=[0.05, 0.72, 1.05], placements=[AssetInstance() for _ in range(1)])
wineglass_D = Assets(description="A glass wine glass with a slender cylindrical stem and a shallow circular bowl, featuring neon blue pastel gradient glass that glows with a vaporwave hue, rim edged in a thin iridescent line.", size=[0.10, 0.10, 0.22], placements=[AssetInstance() for _ in range(1)])
pixelpanel_C = Assets(description="A single piece of thin and upright 8‑bit pixel art panel with vibrant blocky graphics and a retro frame", size=[0.05, 0.62, 0.62], placements=[AssetInstance() for _ in range(1)])
pastelbottle_C = Assets(description="A smooth cylindrical vaporwave wine bottle with a soft pastel gradient and subtle 90s pixel texture", size=[0.09, 0.09, 0.31], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="A glass tasting table with a rectangular top, neon blue metal frame, pixel art etched corners, and a subtle holographic sheen.", size=[0.85, 1.60, 0.76], placements=[AssetInstance() for _ in range(1)])
winebottlecab_C = Assets(description="A square-shaped red wine bottle with vaporwave aesthetic, featuring bold pastel gradient wrap, glossy surface, and a flat label.", size=[0.09, 0.12, 0.28], placements=[AssetInstance() for _ in range(1)])
pastelbottle_D = Assets(description="A vaporwave wine bottle with a pastel gradient finish, smooth cylindrical shape and a soft matte surface", size=[0.09, 0.09, 0.31], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="A modern wine chair in vaporwave style, featuring a sleek angular seat, neon pink upholstery, retro computer keyboard pattern embossing, and chrome legs.", size=[0.55, 0.52, 0.82], placements=[AssetInstance() for _ in range(1)])
pastelbottle_E = Assets(description="A rectangular bottle with pastel gradient glass, smooth edges, and a minimalist white stopper, fully filled with vapor.", size=[0.08, 0.11, 0.30], placements=[AssetInstance() for _ in range(1)])
glitchbottle_B = Assets(description="A vaporwave wine bottle featuring glitch art graphics, cylindrical glass with distorted pixel patterns and a metallic sheen", size=[0.09, 0.09, 0.32], placements=[AssetInstance() for _ in range(1)])
vaporbottle_J = Assets(description="A rectangular-shaped red wine bottle featuring vaporwave graphics, neon pink accents, glossy lacquered surface, angular silhouette.", size=[0.08, 0.11, 0.31], placements=[AssetInstance() for _ in range(1)])
vaporbottlerack_C = Assets(description="A neon pink vapor bottle with a sleek cylindrical shape, glossy pink surface, and a subtle neon glow.", size=[0.09, 0.09, 0.32], placements=[AssetInstance() for _ in range(1)])
winebottletable = Assets(description="A rectangular red wine bottle with a vintage 1990s label, smooth cylindrical body, glossy finish, and a slightly tapered neck.", size=[0.09, 0.09, 0.31], placements=[AssetInstance() for _ in range(1)])
ambientlight_C = Assets(description="A low‑profile square floor lamp with a pastel purple frosted diffuser, soft LED core, and a sleek brushed metal base.", size=[0.34, 0.34, 0.24], placements=[AssetInstance() for _ in range(1)])
glitchbottle_C = Assets(description="A cylindrical vaporwave wine bottle covered in bright glitch art patterns and neon accents", size=[0.09, 0.09, 0.32], placements=[AssetInstance() for _ in range(1)])
book = Assets(description="A rectangular paperback book with a faded 90s internet cover, thin pages, matte finish, and slightly worn edges.", size=[0.15, 0.22, 0.03], placements=[AssetInstance() for _ in range(1)])
pixelpanel_D = Assets(description="A single piece of thin and upright pixel art panel featuring 8-bit graphics, square shape, flat surface, and a matte frame.", size=[0.04, 0.60, 0.60], placements=[AssetInstance() for _ in range(1)])
vaporbottle_glitch_C = Assets(description="A glitch‑art vaporwave wine bottle with a distorted, pixelated surface, bright magenta and cyan colors, irregular cylindrical silhouette", size=[0.10, 0.10, 0.33], placements=[AssetInstance() for _ in range(1)])
glitchbottle_D = Assets(description="A vaporwave wine bottle rendered with glitch art, rectangular glass with fragmented neon colours", size=[0.08, 0.11, 0.31], placements=[AssetInstance() for _ in range(1)])
candle_C = Assets(description="A neon pink candle with a retro 1990s style, cylindrical body, glossy surface and a subtle flickering light effect", size=[0.07, 0.07, 0.15], placements=[AssetInstance() for _ in range(1)])
opener_D = Assets(description="A small rectangular vaporwave wine opener with a glossy 90s internet aesthetic, pastel neon pink accents and a thin metallic lever", size=[0.04, 0.15, 0.03], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="A low storage cabinet with a rectangular boxy shape, pastel purple finish covered in glitchy pixel patterns, smooth flat doors, and short tapered legs, giving it a compact and modern look", size=[0.48, 1.60, 0.78], placements=[AssetInstance() for _ in range(1)])
glitchpanelwall_B = Assets(description="A single piece of thin and upright surreal glitch panel with abstract 1990s motifs, rectangular shape, flat surface, and a metallic border.", size=[0.05, 0.75, 1.20], placements=[AssetInstance() for _ in range(1)])
pinkbottle_B = Assets(description="A cylindrical bottle filled to capacity with neon pink vapor, glossy surface, and a sleek chrome cap, exuding a soft glow.", size=[0.09, 0.09, 0.32], placements=[AssetInstance() for _ in range(1)])
neonsign_E = Assets(description="A thin upright neon sign with a 90s phrase in bright cyan lettering, housed in a slim acrylic frame that glows softly.", size=[0.05, 0.82, 0.34], placements=[AssetInstance() for _ in range(1)])
neonsign_F = Assets(description="A thin upright neon sign with 90s phrase typography, bright cyan lettering on a dark matte backing, rectangular frame", size=[0.06, 0.90, 0.40], placements=[AssetInstance() for _ in range(1)])
pixelpanel_E = Assets(description="A single piece of thin and upright square panel featuring 8‑bit pixel art graphics, matte black border, and a subtle LED backlight.", size=[0.05, 0.60, 0.60], placements=[AssetInstance() for _ in range(1)])
ambientlight_D = Assets(description="A pastel‑purple ambient floor light with a low, squat rectangular base and a soft glowing panel, smooth plastic finish", size=[0.28, 0.46, 0.32], placements=[AssetInstance() for _ in range(1)])
decanter_A = Assets(description="A glass decanter with a smooth curved body, neon blue pastel gradient that fades from teal to pink, and a slender elongated neck", size=[0.18, 0.18, 0.36], placements=[AssetInstance() for _ in range(1)])
ambientlight_E = Assets(description="A compact pastel‑purple floor lamp with a smooth cylindrical shade and soft glowing base", size=[0.30, 0.30, 0.38], placements=[AssetInstance() for _ in range(1)])
glitchbottle_E = Assets(description="A cylindrical vaporwave wine bottle covered in bright glitch art patterns and neon accents", size=[0.09, 0.09, 0.32], placements=[AssetInstance() for _ in range(1)])
opener_E = Assets(description="A small rectangular metal wine opener with a sleek 1990s vaporwave aesthetic, neon pink accents and a glossy finish", size=[0.04, 0.15, 0.03], placements=[AssetInstance() for _ in range(1)])
pastelbottle_F = Assets(description="A pastel‑gradient wine bottle, smooth cylindrical shape, soft pink‑to‑blue gradient, glossy finish, subtle vaporwave vibe", size=[0.09, 0.09, 0.32], placements=[AssetInstance() for _ in range(1)])
wineglass_E = Assets(description="A glass wine glass with a slender cylindrical stem and a shallow circular bowl, featuring neon blue pastel gradient glass that glows with a vaporwave hue, rim edged in a thin iridescent line.", size=[0.10, 0.10, 0.22], placements=[AssetInstance() for _ in range(1)])
decanter_B = Assets(description="A glass wine decanter shaped like a tall, rounded cylinder with a slightly flared mouth, neon blue glass overlaid by a pastel gradient, smooth surface", size=[0.17, 0.17, 0.34], placements=[AssetInstance() for _ in range(1)])
pinkbottle_C = Assets(description="A vaporwave wine bottle in neon pink, cylindrical glass with a smooth curved silhouette and a glossy finish", size=[0.09, 0.09, 0.32], placements=[AssetInstance() for _ in range(1)])
decanter_C = Assets(description="A glass wine decanter with a neon‑blue cylindrical body and a pastel gradient swirl, smooth curved surface and a narrow neck", size=[0.18, 0.18, 0.35], placements=[AssetInstance() for _ in range(1)])
vaporrack_A = Assets(description="A wall-mounted wine rack with vaporwave design, geometric lattice of neon teal bars, rectangular compartments, sleek metallic frame.", size=[0.25, 1.50, 1.20], placements=[AssetInstance() for _ in range(1)])
corkscrew_C = Assets(description="A vintage corkscrew with a 1990s pixel‑art handle, cylindrical metal shaft and a small angular lever, finished in muted teal with neon pink accents", size=[0.09, 0.16, 0.04], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="A modern wine chair in vaporwave style, featuring a sleek angular seat, neon pink upholstery, retro computer keyboard pattern embossing, and chrome legs.", size=[0.55, 0.52, 0.82], placements=[AssetInstance() for _ in range(1)])
vaporbottle_pastel_B = Assets(description="A pastel‑gradient vaporwave wine bottle with a smooth cylindrical body, soft pink‑blue gradient glaze, glossy finish", size=[0.09, 0.09, 0.32], placements=[AssetInstance() for _ in range(1)])
neonsign_G = Assets(description="A single piece of thin and upright neon sign displaying a 90s phrase, rectangular frame with bright neon tubing and a dark backing", size=[0.06, 0.85, 0.42], placements=[AssetInstance() for _ in range(1)])
pastelbottle_G = Assets(description="A smooth cylindrical vaporwave wine bottle with a soft pastel gradient and subtle 90s pixel texture", size=[0.09, 0.09, 0.31], placements=[AssetInstance() for _ in range(1)])
vaporbottle_K = Assets(description="A square glass bottle with glitch‑art holographic surface, shifting neon colors, and a flat screw top, giving a distorted visual effect.", size=[0.10, 0.12, 0.28], placements=[AssetInstance() for _ in range(1)])
vaporbottle_glitch_D = Assets(description="A glitch‑art vaporwave wine bottle with a distorted, pixelated surface, bright magenta and cyan colors, irregular cylindrical silhouette", size=[0.10, 0.10, 0.33], placements=[AssetInstance() for _ in range(1)])
pixelpanel_F = Assets(description="A single piece of thin and upright pixel art panel featuring 8-bit graphics, square shape, flat surface, and a matte frame.", size=[0.04, 0.60, 0.60], placements=[AssetInstance() for _ in range(1)])
vaporrack_B = Assets(description="A wall-mounted wine rack with vaporwave design, geometric lattice of neon teal bars, rectangular compartments, sleek metallic frame.", size=[0.25, 1.50, 1.20], placements=[AssetInstance() for _ in range(1)])
neonsign_H = Assets(description="A single piece of thin and upright neon sign with a 90s phrase, rectangular acrylic backing, bright colored neon tubing, and a glossy finish.", size=[0.06, 0.88, 0.38], placements=[AssetInstance() for _ in range(1)])
pixelpanel_G = Assets(description="A single piece of thin and upright 8‑bit pixel art panel, square shape with a glossy front and retro pixel graphics", size=[0.04, 0.60, 0.60], placements=[AssetInstance() for _ in range(1)])
floorlamp_B = Assets(description="A retro floor lamp with vaporwave design, tall slender stand, curved shade and a pastel gradient finish", size=[0.48, 0.40, 1.70], placements=[AssetInstance() for _ in range(1)])
label_E = Assets(description="A small rectangular wine bottle label with 1990s retro typography, neon pink and teal colors, glossy laminated finish", size=[0.01, 0.10, 0.07], placements=[AssetInstance() for _ in range(1)])
pastelbottle_H = Assets(description="A smooth cylindrical vaporwave wine bottle with a soft pastel gradient and subtle 90s pixel texture", size=[0.09, 0.09, 0.31], placements=[AssetInstance() for _ in range(1)])
pinkbottle_D = Assets(description="A cylindrical bottle filled to capacity with neon pink vapor, glossy surface, and a sleek chrome cap, exuding a soft glow.", size=[0.09, 0.09, 0.32], placements=[AssetInstance() for _ in range(1)])
candle_D = Assets(description="A small scented candle in a neon pink glass holder, cylindrical shape, smooth surface, flickering flame.", size=[0.08, 0.08, 0.10], placements=[AssetInstance() for _ in range(1)])
vaporbottle_L = Assets(description="A neon‑pink vaporwave wine bottle with a sleek cylindrical body, glossy finish, subtle pastel highlights, smooth surface", size=[0.09, 0.09, 0.32], placements=[AssetInstance() for _ in range(1)])
vaporbottle_M = Assets(description="A square glass bottle with glitch‑art holographic surface, shifting neon colors, and a flat screw top, giving a distorted visual effect.", size=[0.10, 0.12, 0.28], placements=[AssetInstance() for _ in range(1)])
sign_D = Assets(description="A single piece of thin and upright neon sign with a 90s phrase in glowing pastel pink lettering", size=[0.05, 0.75, 0.32], placements=[AssetInstance() for _ in range(1)])
opener_F = Assets(description="A compact wine opener with a sleek rectangular handle, glossy pastel gradient finish and a small neon pink accent, reminiscent of 90s internet aesthetics", size=[0.04, 0.16, 0.03], placements=[AssetInstance() for _ in range(1)])
winebottlecab_D = Assets(description="A square-shaped red wine bottle with vaporwave aesthetic, featuring bold pastel gradient wrap, glossy surface, and a flat label.", size=[0.09, 0.12, 0.28], placements=[AssetInstance() for _ in range(1)])
winebook_B = Assets(description="A thin rectangular wine book with a vaporwave cover, featuring a glitch‑style pastel collage and a glossy laminated finish.", size=[0.18, 0.24, 0.03], placements=[AssetInstance() for _ in range(1)])
pixelpanel_H = Assets(description="A single piece of thin and upright 8‑bit pixel art panel, square shape with a glossy front and retro pixel graphics", size=[0.04, 0.60, 0.60], placements=[AssetInstance() for _ in range(1)])
pixelpanel_wall_D = Assets(description="A single piece of thin upright 8‑bit pixel art panel, rectangular with bright retro graphics and a matte frame", size=[0.04, 0.55, 0.75], placements=[AssetInstance() for _ in range(1)])
pixelpanel_I = Assets(description="A single piece of thin and upright 8‑bit pixel art panel with vibrant blocky graphics and a retro frame", size=[0.05, 0.62, 0.62], placements=[AssetInstance() for _ in range(1)])
glitchbottle_F = Assets(description="A vaporwave wine bottle featuring glitch art graphics, cylindrical glass with distorted pixel patterns and a metallic sheen", size=[0.09, 0.09, 0.32], placements=[AssetInstance() for _ in range(1)])

vaporbottle_A[0].instance_id = 'vaporbottle_A_0'
wineglass_A[0].instance_id = 'wineglass_A_0'
vaporbottle_B[0].instance_id = 'vaporbottle_B_0'
glitchpanelwall_A[0].instance_id = 'glitchpanelwall_A_0'
glitchbottle_A[0].instance_id = 'glitchbottle_A_0'
glitchpanelcab[0].instance_id = 'glitchpanelcab_0'
opener_A[0].instance_id = 'opener_A_0'
opener_B[0].instance_id = 'opener_B_0'
sign_A[0].instance_id = 'sign_A_0'
neonsign_A[0].instance_id = 'neonsign_A_0'
glitchpanel_A[0].instance_id = 'glitchpanel_A_0'
chair_A[0].instance_id = 'chair_A_0'
neonsign_B[0].instance_id = 'neonsign_B_0'
label_A[0].instance_id = 'label_A_0'
vaporbottle_C[0].instance_id = 'vaporbottle_C_0'
sign_B[0].instance_id = 'sign_B_0'
vaporbottle_pastel_A[0].instance_id = 'vaporbottle_pastel_A_0'
glitchpanel_B[0].instance_id = 'glitchpanel_B_0'
pastelbottle_A[0].instance_id = 'pastelbottle_A_0'
vaporbottle_D[0].instance_id = 'vaporbottle_D_0'
neonsign_C[0].instance_id = 'neonsign_C_0'
label_B[0].instance_id = 'label_B_0'
surrealpanel_A[0].instance_id = 'surrealpanel_A_0'
sign_C[0].instance_id = 'sign_C_0'
vaporbottlerack_A[0].instance_id = 'vaporbottlerack_A_0'
vaporbottle_glitch_A[0].instance_id = 'vaporbottle_glitch_A_0'
vaporbottlerack_B[0].instance_id = 'vaporbottlerack_B_0'
vaporbottle_E[0].instance_id = 'vaporbottle_E_0'
vaporbottle_F[0].instance_id = 'vaporbottle_F_0'
candle_A[0].instance_id = 'candle_A_0'
vintagebottle[0].instance_id = 'vintagebottle_0'
surrealpanel_B[0].instance_id = 'surrealpanel_B_0'
winebook_A[0].instance_id = 'winebook_A_0'
ambientlight_A[0].instance_id = 'ambientlight_A_0'
corkscrew_A[0].instance_id = 'corkscrew_A_0'
pixelpanel_A[0].instance_id = 'pixelpanel_A_0'
label_C[0].instance_id = 'label_C_0'
neonsign_D[0].instance_id = 'neonsign_D_0'
wineglass_B[0].instance_id = 'wineglass_B_0'
rack_A[0].instance_id = 'rack_A_0'
lamp[0].instance_id = 'lamp_0'
winebottlecab_A[0].instance_id = 'winebottlecab_A_0'
candle_B[0].instance_id = 'candle_B_0'
rack_B[0].instance_id = 'rack_B_0'
vaporbottle_G[0].instance_id = 'vaporbottle_G_0'
wineglass_C[0].instance_id = 'wineglass_C_0'
corkscrew_B[0].instance_id = 'corkscrew_B_0'
vaporbottle_H[0].instance_id = 'vaporbottle_H_0'
pixelpanel_wall_A[0].instance_id = 'pixelpanel_wall_A_0'
opener_C[0].instance_id = 'opener_C_0'
pinkbottle_A[0].instance_id = 'pinkbottle_A_0'
winebottlecab_B[0].instance_id = 'winebottlecab_B_0'
vaporbottle_glitch_B[0].instance_id = 'vaporbottle_glitch_B_0'
pixelpanel_B[0].instance_id = 'pixelpanel_B_0'
pixelpanel_wall_B[0].instance_id = 'pixelpanel_wall_B_0'
ambientlight_B[0].instance_id = 'ambientlight_B_0'
pixelpanel_wall_C[0].instance_id = 'pixelpanel_wall_C_0'
vaporbottle_I[0].instance_id = 'vaporbottle_I_0'
pastelbottle_B[0].instance_id = 'pastelbottle_B_0'
romanbust[0].instance_id = 'romanbust_0'
label_D[0].instance_id = 'label_D_0'
floorlamp_A[0].instance_id = 'floorlamp_A_0'
glitchpanel_C[0].instance_id = 'glitchpanel_C_0'
wineglass_D[0].instance_id = 'wineglass_D_0'
pixelpanel_C[0].instance_id = 'pixelpanel_C_0'
pastelbottle_C[0].instance_id = 'pastelbottle_C_0'
table[0].instance_id = 'table_0'
winebottlecab_C[0].instance_id = 'winebottlecab_C_0'
pastelbottle_D[0].instance_id = 'pastelbottle_D_0'
chair_B[0].instance_id = 'chair_B_0'
pastelbottle_E[0].instance_id = 'pastelbottle_E_0'
glitchbottle_B[0].instance_id = 'glitchbottle_B_0'
vaporbottle_J[0].instance_id = 'vaporbottle_J_0'
vaporbottlerack_C[0].instance_id = 'vaporbottlerack_C_0'
winebottletable[0].instance_id = 'winebottletable_0'
ambientlight_C[0].instance_id = 'ambientlight_C_0'
glitchbottle_C[0].instance_id = 'glitchbottle_C_0'
book[0].instance_id = 'book_0'
pixelpanel_D[0].instance_id = 'pixelpanel_D_0'
vaporbottle_glitch_C[0].instance_id = 'vaporbottle_glitch_C_0'
glitchbottle_D[0].instance_id = 'glitchbottle_D_0'
candle_C[0].instance_id = 'candle_C_0'
opener_D[0].instance_id = 'opener_D_0'
cabinet[0].instance_id = 'cabinet_0'
glitchpanelwall_B[0].instance_id = 'glitchpanelwall_B_0'
pinkbottle_B[0].instance_id = 'pinkbottle_B_0'
neonsign_E[0].instance_id = 'neonsign_E_0'
neonsign_F[0].instance_id = 'neonsign_F_0'
pixelpanel_E[0].instance_id = 'pixelpanel_E_0'
ambientlight_D[0].instance_id = 'ambientlight_D_0'
decanter_A[0].instance_id = 'decanter_A_0'
ambientlight_E[0].instance_id = 'ambientlight_E_0'
glitchbottle_E[0].instance_id = 'glitchbottle_E_0'
opener_E[0].instance_id = 'opener_E_0'
pastelbottle_F[0].instance_id = 'pastelbottle_F_0'
wineglass_E[0].instance_id = 'wineglass_E_0'
decanter_B[0].instance_id = 'decanter_B_0'
pinkbottle_C[0].instance_id = 'pinkbottle_C_0'
decanter_C[0].instance_id = 'decanter_C_0'
vaporrack_A[0].instance_id = 'vaporrack_A_0'
corkscrew_C[0].instance_id = 'corkscrew_C_0'
chair_C[0].instance_id = 'chair_C_0'
vaporbottle_pastel_B[0].instance_id = 'vaporbottle_pastel_B_0'
neonsign_G[0].instance_id = 'neonsign_G_0'
pastelbottle_G[0].instance_id = 'pastelbottle_G_0'
vaporbottle_K[0].instance_id = 'vaporbottle_K_0'
vaporbottle_glitch_D[0].instance_id = 'vaporbottle_glitch_D_0'
pixelpanel_F[0].instance_id = 'pixelpanel_F_0'
vaporrack_B[0].instance_id = 'vaporrack_B_0'
neonsign_H[0].instance_id = 'neonsign_H_0'
pixelpanel_G[0].instance_id = 'pixelpanel_G_0'
floorlamp_B[0].instance_id = 'floorlamp_B_0'
label_E[0].instance_id = 'label_E_0'
pastelbottle_H[0].instance_id = 'pastelbottle_H_0'
pinkbottle_D[0].instance_id = 'pinkbottle_D_0'
candle_D[0].instance_id = 'candle_D_0'
vaporbottle_L[0].instance_id = 'vaporbottle_L_0'
vaporbottle_M[0].instance_id = 'vaporbottle_M_0'
sign_D[0].instance_id = 'sign_D_0'
opener_F[0].instance_id = 'opener_F_0'
winebottlecab_D[0].instance_id = 'winebottlecab_D_0'
winebook_B[0].instance_id = 'winebook_B_0'
pixelpanel_H[0].instance_id = 'pixelpanel_H_0'
pixelpanel_wall_D[0].instance_id = 'pixelpanel_wall_D_0'
pixelpanel_I[0].instance_id = 'pixelpanel_I_0'
glitchbottle_F[0].instance_id = 'glitchbottle_F_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

vaporbottle_A[0].position = [2.007611009005454, 3.1472759287794174, 0.16]
vaporbottle_A[0].rotation = [0, 0, 0]
wineglass_A[0].position = [1.0928487933370552, 1.8027248442208341, 0.105]
wineglass_A[0].rotation = [0, 0, 0]
vaporbottle_B[0].position = [4.659603157141399, 1.0573854400887668, 0.155]
vaporbottle_B[0].rotation = [0, 0, 0]
glitchpanelwall_A[0].position = [3.4619681442150636, 3.384962516367848, 0.6]
glitchpanelwall_A[0].rotation = [0, 0, 0]
glitchbottle_A[0].position = [2.796568605841668, 3.1207333425657673, 0.16]
glitchbottle_A[0].rotation = [0, 0, 0]
glitchpanelcab[0].position = [0.9712779095303736, 1.9878401933943444, 0.55]
glitchpanelcab[0].rotation = [0, 0, 0]
opener_A[0].position = [0.08849961178825694, 1.564142964918775, 0.015]
opener_A[0].rotation = [0, 0, 0]
opener_B[0].position = [0.3011675672108882, 1.1942605534933168, 0.015]
opener_B[0].rotation = [0, 0, 0]
sign_A[0].position = [2.1891707051942255, 1.804257439260426, 0.175]
sign_A[0].rotation = [0, 0, 0]
neonsign_A[0].position = [3.1633479911538975, 2.05635815105203, 0.2]
neonsign_A[0].rotation = [0, 0, 0]
glitchpanel_A[0].position = [1.2959904018128132, 1.5664411797860218, 0.15]
glitchpanel_A[0].rotation = [0, 0, 0]
chair_A[0].position = [2.9859557035550397, 1.1618638519974622, 0.41]
chair_A[0].rotation = [0, 0, 0]
neonsign_B[0].position = [3.8187216381693507, 1.4771406021226618, 0.21]
neonsign_B[0].rotation = [0, 0, 0]
label_A[0].position = [4.184913989060018, 1.6249464929982396, 0.035]
label_A[0].rotation = [0, 0, 0]
vaporbottle_C[0].position = [2.791557376630842, 2.441314766799668, 0.155]
vaporbottle_C[0].rotation = [0, 0, 0]
sign_B[0].position = [3.072320865554627, 3.0210734162783743, 0.16]
sign_B[0].rotation = [0, 0, 0]
vaporbottle_pastel_A[0].position = [2.0872486751358235, 2.404485154295809, 0.16]
vaporbottle_pastel_A[0].rotation = [0, 0, 0]
glitchpanel_B[0].position = [0.008506784052522143, 1.9208614472073142, 0.525]
glitchpanel_B[0].rotation = [0, 0, 0]
pastelbottle_A[0].position = [0.35067299395888984, 0.9894484009971909, 0.155]
pastelbottle_A[0].rotation = [0, 0, 0]
vaporbottle_D[0].position = [3.1574561676666986, 3.398029608950403, 0.16]
vaporbottle_D[0].rotation = [0, 0, 0]
neonsign_C[0].position = [0.8351365429072227, 3.669994894433762, 0.21]
neonsign_C[0].rotation = [0, 0, 0]
label_B[0].position = [1.5806867233719908, 0.9394599366864584, 0.04]
label_B[0].rotation = [0, 0, 0]
surrealpanel_A[0].position = [2.3221907890847815, 0.5145717051309164, 0.55]
surrealpanel_A[0].rotation = [0, 0, 0]
sign_C[0].position = [0.7055500032258971, 2.5291931705157005, 0.175]
sign_C[0].rotation = [0, 0, 0]
vaporbottlerack_A[0].position = [1.9371773041816265, 1.5678735408569642, 0.155]
vaporbottlerack_A[0].rotation = [0, 0, 0]
vaporbottle_glitch_A[0].position = [4.032762123556984, 2.9357699243909727, 0.165]
vaporbottle_glitch_A[0].rotation = [0, 0, 0]
vaporbottlerack_B[0].position = [3.7903155929302867, 3.810825244656346, 0.16]
vaporbottlerack_B[0].rotation = [0, 0, 0]
vaporbottle_E[0].position = [1.2223520555505867, 2.613577666060678, 0.155]
vaporbottle_E[0].rotation = [0, 0, 0]
vaporbottle_F[0].position = [4.064806993322837, 0.405250370999112, 0.155]
vaporbottle_F[0].rotation = [0, 0, 0]
candle_A[0].position = [1.3762205100658043, 3.564029200336269, 0.08]
candle_A[0].rotation = [0, 0, 0]
vintagebottle[0].position = [4.41875278018834, 0.005127178167680491, 0.155]
vintagebottle[0].rotation = [0, 0, 0]
surrealpanel_B[0].position = [2.989553407097665, 1.9144164973326099, 0.55]
surrealpanel_B[0].rotation = [0, 0, 0]
winebook_A[0].position = [2.6493403350052374, 0.8411010808213364, 0.015]
winebook_A[0].rotation = [0, 0, 0]
ambientlight_A[0].position = [3.939155288372767, 2.103576424299115, 0.21]
ambientlight_A[0].rotation = [0, 0, 0]
corkscrew_A[0].position = [4.218343913536056, 2.9557748002974176, 0.02]
corkscrew_A[0].rotation = [0, 0, 0]
pixelpanel_A[0].position = [0.3134794320612999, 3.2139227262118606, 0.3]
pixelpanel_A[0].rotation = [0, 0, 0]
label_C[0].position = [2.4181141058298685, 3.466077451283185, 0.035]
label_C[0].rotation = [0, 0, 0]
neonsign_D[0].position = [4.214326639896527, 3.827919358873906, 0.14]
neonsign_D[0].rotation = [0, 0, 0]
wineglass_B[0].position = [0.1704200893157326, 0.035733074393663244, 0.105]
wineglass_B[0].rotation = [0, 0, 0]
rack_A[0].position = [4.176500768665596, 0.7561915762803482, 0.9]
rack_A[0].rotation = [0, 0, 0]
lamp[0].position = [3.4992162112221834, 1.5536835397658413, 0.825]
lamp[0].rotation = [0, 0, 0]
winebottlecab_A[0].position = [4.201411752756041, 3.360229098652778, 0.14]
winebottlecab_A[0].rotation = [0, 0, 0]
candle_B[0].position = [2.3381108507313124, 1.733778298268728, 0.085]
candle_B[0].rotation = [0, 0, 0]
rack_B[0].position = [1.352674786387615, 2.49046009493667, 0.9]
rack_B[0].rotation = [0, 0, 0]
vaporbottle_G[0].position = [1.0357439505982358, 2.4774064618515768, 0.16]
vaporbottle_G[0].rotation = [0, 0, 0]
wineglass_C[0].position = [4.261218895518511, 3.5080094822580223, 0.105]
wineglass_C[0].rotation = [0, 0, 0]
corkscrew_B[0].position = [0.893431784909029, 2.3056159213917433, 0.02]
corkscrew_B[0].rotation = [0, 0, 0]
vaporbottle_H[0].position = [2.0888518246973424, 0.8782873405516436, 0.155]
vaporbottle_H[0].rotation = [0, 0, 0]
pixelpanel_wall_A[0].position = [0.6083462687873664, 1.7320494404650746, 0.375]
pixelpanel_wall_A[0].rotation = [0, 0, 0]
opener_C[0].position = [4.551049050686824, 3.6159428464937, 0.015]
opener_C[0].rotation = [0, 0, 0]
pinkbottle_A[0].position = [0.8143850014250159, 0.0621544869592876, 0.16]
pinkbottle_A[0].rotation = [0, 0, 0]
winebottlecab_B[0].position = [3.1719064987988514, 3.6758220053234028, 0.14]
winebottlecab_B[0].rotation = [0, 0, 0]
vaporbottle_glitch_B[0].position = [4.172171846424911, 3.703110182122529, 0.165]
vaporbottle_glitch_B[0].rotation = [0, 0, 0]
pixelpanel_B[0].position = [2.4948608732944777, 2.0581958740854573, 0.3]
pixelpanel_B[0].rotation = [0, 0, 0]
pixelpanel_wall_B[0].position = [4.138634200701826, 3.3575004203954313, 0.375]
pixelpanel_wall_B[0].rotation = [0, 0, 0]
ambientlight_B[0].position = [2.9931724729755693, 3.396184607266163, 0.12]
ambientlight_B[0].rotation = [0, 0, 0]
pixelpanel_wall_C[0].position = [2.7119569831941748, 1.0965788442772597, 0.375]
pixelpanel_wall_C[0].rotation = [0, 0, 0]
vaporbottle_I[0].position = [2.011461532159008, 3.2537827395241092, 0.155]
vaporbottle_I[0].rotation = [0, 0, 0]
pastelbottle_B[0].position = [0.5872589622377322, 2.2387330703619233, 0.155]
pastelbottle_B[0].rotation = [0, 0, 0]
romanbust[0].position = [4.86410046295337, 2.224386831870602, 0.29]
romanbust[0].rotation = [0, 0, 0]
label_D[0].position = [2.685169887935434, 2.5267988636495105, 0.04]
label_D[0].rotation = [0, 0, 0]
floorlamp_A[0].position = [1.5508366090489423, 3.0747409823004395, 0.85]
floorlamp_A[0].rotation = [0, 0, 0]
glitchpanel_C[0].position = [0.3238668852666704, 1.1136800898360408, 0.525]
glitchpanel_C[0].rotation = [0, 0, 0]
wineglass_D[0].position = [0.7929766996164678, 2.321226666233129, 0.11]
wineglass_D[0].rotation = [0, 0, 0]
pixelpanel_C[0].position = [0.5456610232859738, 3.3537701156937825, 0.31]
pixelpanel_C[0].rotation = [0, 0, 0]
pastelbottle_C[0].position = [1.3241725102104422, 0.21699245451778282, 0.155]
pastelbottle_C[0].rotation = [0, 0, 0]
table[0].position = [4.487838263652531, 3.9383688211203234, 0.38]
table[0].rotation = [0, 0, 0]
winebottlecab_C[0].position = [3.40081135374459, 3.676733293706082, 0.14]
winebottlecab_C[0].rotation = [0, 0, 0]
pastelbottle_D[0].position = [1.7927024204743454, 0.6092379731103081, 0.155]
pastelbottle_D[0].rotation = [0, 0, 0]
chair_B[0].position = [1.8497067703851062, 0.865179304383545, 0.41]
chair_B[0].rotation = [0, 0, 0]
pastelbottle_E[0].position = [2.7185086718218496, 1.7931639762577944, 0.15]
pastelbottle_E[0].rotation = [0, 0, 0]
glitchbottle_B[0].position = [3.8337489428396476, 0.8930724916897841, 0.16]
glitchbottle_B[0].rotation = [0, 0, 0]
vaporbottle_J[0].position = [2.6892967229323816, 0.303503729756736, 0.155]
vaporbottle_J[0].rotation = [0, 0, 0]
vaporbottlerack_C[0].position = [1.198820103933106, 1.0873070868403225, 0.16]
vaporbottlerack_C[0].rotation = [0, 0, 0]
winebottletable[0].position = [2.7486714728840163, 3.897304099304933, 0.155]
winebottletable[0].rotation = [0, 0, 0]
ambientlight_C[0].position = [3.473209551561255, 0.6307836111227205, 0.12]
ambientlight_C[0].rotation = [0, 0, 0]
glitchbottle_C[0].position = [4.252169577085273, 0.48421639836259667, 0.16]
glitchbottle_C[0].rotation = [0, 0, 0]
book[0].position = [3.2408979398175424, 2.6928209591503913, 0.015]
book[0].rotation = [0, 0, 0]
pixelpanel_D[0].position = [4.361973435651059, 0.7641781457805559, 0.3]
pixelpanel_D[0].rotation = [0, 0, 0]
vaporbottle_glitch_C[0].position = [4.9732311270825145, 3.9944178271246344, 0.165]
vaporbottle_glitch_C[0].rotation = [0, 0, 0]
glitchbottle_D[0].position = [3.4376531465643345, 3.4583465353426353, 0.155]
glitchbottle_D[0].rotation = [0, 0, 0]
candle_C[0].position = [0.21946703842309456, 1.9989933176213688, 0.075]
candle_C[0].rotation = [0, 0, 0]
opener_D[0].position = [2.2897409872703633, 1.621961329793216, 0.015]
opener_D[0].rotation = [0, 0, 0]
cabinet[0].position = [2.6291285988651603, 1.9803997602133192, 0.39]
cabinet[0].rotation = [0, 0, 0]
glitchpanelwall_B[0].position = [4.977899062795471, 3.612362105859236, 0.6]
glitchpanelwall_B[0].rotation = [0, 0, 0]
pinkbottle_B[0].position = [2.1890031420947373, 2.1852899351770962, 0.16]
pinkbottle_B[0].rotation = [0, 0, 0]
neonsign_E[0].position = [2.0152421474281326, 1.513818098730494, 0.17]
neonsign_E[0].rotation = [0, 0, 0]
neonsign_F[0].position = [1.240108671848249, 3.4068853340270038, 0.2]
neonsign_F[0].rotation = [0, 0, 0]
pixelpanel_E[0].position = [0.21097490988432444, 0.4817975981265823, 0.3]
pixelpanel_E[0].rotation = [0, 0, 0]
ambientlight_D[0].position = [2.0836119279804075, 3.6019946493793213, 0.16]
ambientlight_D[0].rotation = [0, 0, 0]
decanter_A[0].position = [1.7621576115138404, 2.0419022509920426, 0.18]
decanter_A[0].rotation = [0, 0, 0]
ambientlight_E[0].position = [0.7980691903111703, 0.5296732052148871, 0.19]
ambientlight_E[0].rotation = [0, 0, 0]
glitchbottle_E[0].position = [1.15481563507412, 2.926034461311336, 0.16]
glitchbottle_E[0].rotation = [0, 0, 0]
opener_E[0].position = [2.9615399527200283, 0.6482993023029819, 0.015]
opener_E[0].rotation = [0, 0, 0]
pastelbottle_F[0].position = [1.5819356637592186, 3.4882781362210267, 0.16]
pastelbottle_F[0].rotation = [0, 0, 0]
wineglass_E[0].position = [4.310640803101742, 1.4566445714885505, 0.11]
wineglass_E[0].rotation = [0, 0, 0]
decanter_B[0].position = [3.4204699710957085, 3.453054728923074, 0.17]
decanter_B[0].rotation = [0, 0, 0]
pinkbottle_C[0].position = [1.2913910600788854, 0.1345827444697747, 0.16]
pinkbottle_C[0].rotation = [0, 0, 0]
decanter_C[0].position = [3.602675916053058, 3.8722708644373367, 0.175]
decanter_C[0].rotation = [0, 0, 0]
vaporrack_A[0].position = [2.0382532524263475, 3.824657060564422, 0.6]
vaporrack_A[0].rotation = [0, 0, 0]
corkscrew_C[0].position = [1.548390117951795, 0.11562667890564837, 0.02]
corkscrew_C[0].rotation = [0, 0, 0]
chair_C[0].position = [0.0700849594970232, 1.7314553485199613, 0.41]
chair_C[0].rotation = [0, 0, 0]
vaporbottle_pastel_B[0].position = [3.43201107292229, 0.8002572758809823, 0.16]
vaporbottle_pastel_B[0].rotation = [0, 0, 0]
neonsign_G[0].position = [4.567704930191095, 0.15094585189623766, 0.21]
neonsign_G[0].rotation = [0, 0, 0]
pastelbottle_G[0].position = [1.5718805031668333, 2.6727982807781308, 0.155]
pastelbottle_G[0].rotation = [0, 0, 0]
vaporbottle_K[0].position = [1.122297247490267, 2.04118133324696, 0.14]
vaporbottle_K[0].rotation = [0, 0, 0]
vaporbottle_glitch_D[0].position = [1.514983118196428, 2.5914039002837757, 0.165]
vaporbottle_glitch_D[0].rotation = [0, 0, 0]
pixelpanel_F[0].position = [3.6829063560681545, 0.33060458382691804, 0.3]
pixelpanel_F[0].rotation = [0, 0, 0]
vaporrack_B[0].position = [1.3332163144317666, 0.16804265449830602, 0.6]
vaporrack_B[0].rotation = [0, 0, 0]
neonsign_H[0].position = [3.3470798742219228, 0.5686015878132671, 0.19]
neonsign_H[0].rotation = [0, 0, 0]
pixelpanel_G[0].position = [2.039787689139732, 2.850862891848109, 0.3]
pixelpanel_G[0].rotation = [0, 0, 0]
floorlamp_B[0].position = [3.8894654049637625, 2.4315778012836855, 0.85]
floorlamp_B[0].rotation = [0, 0, 0]
label_E[0].position = [2.777642405719381, 1.0815319372498489, 0.035]
label_E[0].rotation = [0, 0, 0]
pastelbottle_H[0].position = [1.4166113248492755, 1.6762915583178746, 0.155]
pastelbottle_H[0].rotation = [0, 0, 0]
pinkbottle_D[0].position = [1.9353291500364493, 0.7954328246880715, 0.16]
pinkbottle_D[0].rotation = [0, 0, 0]
candle_D[0].position = [0.9343355147262655, 2.849038055727431, 0.05]
candle_D[0].rotation = [0, 0, 0]
vaporbottle_L[0].position = [0.8973409274667571, 2.581561402911272, 0.16]
vaporbottle_L[0].rotation = [0, 0, 0]
vaporbottle_M[0].position = [4.6235188148839725, 3.469106218510523, 0.14]
vaporbottle_M[0].rotation = [0, 0, 0]
sign_D[0].position = [1.4901898906495326, 2.2447192436581234, 0.16]
sign_D[0].rotation = [0, 0, 0]
opener_F[0].position = [0.596679484585903, 3.1125837755540866, 0.015]
opener_F[0].rotation = [0, 0, 0]
winebottlecab_D[0].position = [4.0974440872345514, 3.2370491004842066, 0.14]
winebottlecab_D[0].rotation = [0, 0, 0]
winebook_B[0].position = [0.7082559276344919, 1.5532478198619724, 0.015]
winebook_B[0].rotation = [0, 0, 0]
pixelpanel_H[0].position = [1.2634183051536063, 2.652209617885941, 0.3]
pixelpanel_H[0].rotation = [0, 0, 0]
pixelpanel_wall_D[0].position = [3.2577740607723005, 2.6490820841650278, 0.375]
pixelpanel_wall_D[0].rotation = [0, 0, 0]
pixelpanel_I[0].position = [0.3223552601430002, 1.4488506372571566, 0.31]
pixelpanel_I[0].rotation = [0, 0, 0]
glitchbottle_F[0].position = [1.7170212628264936, 3.462816536171464, 0.16]
glitchbottle_F[0].rotation = [0, 0, 0]
vaporbottle_A[0].position = [2.007611009005454, 3.1472759287794174, 0.16]
vaporbottle_A[0].rotation = [0, 0, 0]
wineglass_A[0].position = [1.0928487933370552, 1.8027248442208341, 0.105]
wineglass_A[0].rotation = [0, 0, 0]
vaporbottle_B[0].position = [4.659603157141399, 1.0573854400887668, 0.155]
vaporbottle_B[0].rotation = [0, 0, 0]
glitchpanelwall_A[0].position = [3.4619681442150636, 3.384962516367848, 0.6]
glitchpanelwall_A[0].rotation = [0, 0, 0]
glitchbottle_A[0].position = [2.796568605841668, 3.1207333425657673, 0.16]
glitchbottle_A[0].rotation = [0, 0, 0]
glitchpanelcab[0].position = [0.9712779095303736, 1.9878401933943444, 0.55]
glitchpanelcab[0].rotation = [0, 0, 0]
opener_A[0].position = [0.08849961178825694, 1.564142964918775, 0.015]
opener_A[0].rotation = [0, 0, 0]
opener_B[0].position = [0.3011675672108882, 1.1942605534933168, 0.015]
opener_B[0].rotation = [0, 0, 0]
sign_A[0].position = [2.1891707051942255, 1.804257439260426, 0.175]
sign_A[0].rotation = [0, 0, 0]
neonsign_A[0].position = [3.1633479911538975, 2.05635815105203, 0.2]
neonsign_A[0].rotation = [0, 0, 0]
glitchpanel_A[0].position = [1.2959904018128132, 1.5664411797860218, 0.15]
glitchpanel_A[0].rotation = [0, 0, 0]
chair_A[0].position = [2.9859557035550397, 1.1618638519974622, 0.41]
chair_A[0].rotation = [0, 0, 0]
neonsign_B[0].position = [3.8187216381693507, 1.4771406021226618, 0.21]
neonsign_B[0].rotation = [0, 0, 0]
label_A[0].position = [4.184913989060018, 1.6249464929982396, 0.035]
label_A[0].rotation = [0, 0, 0]
vaporbottle_C[0].position = [2.791557376630842, 2.441314766799668, 0.155]
vaporbottle_C[0].rotation = [0, 0, 0]
sign_B[0].position = [3.072320865554627, 3.0210734162783743, 0.16]
sign_B[0].rotation = [0, 0, 0]
vaporbottle_pastel_A[0].position = [2.0872486751358235, 2.404485154295809, 0.16]
vaporbottle_pastel_A[0].rotation = [0, 0, 0]
glitchpanel_B[0].position = [0.008506784052522143, 1.9208614472073142, 0.525]
glitchpanel_B[0].rotation = [0, 0, 0]
pastelbottle_A[0].position = [0.35067299395888984, 0.9894484009971909, 0.155]
pastelbottle_A[0].rotation = [0, 0, 0]
vaporbottle_D[0].position = [3.1574561676666986, 3.398029608950403, 0.16]
vaporbottle_D[0].rotation = [0, 0, 0]
neonsign_C[0].position = [0.8351365429072227, 3.669994894433762, 0.21]
neonsign_C[0].rotation = [0, 0, 0]
label_B[0].position = [1.5806867233719908, 0.9394599366864584, 0.04]
label_B[0].rotation = [0, 0, 0]
surrealpanel_A[0].position = [2.3221907890847815, 0.5145717051309164, 0.55]
surrealpanel_A[0].rotation = [0, 0, 0]
sign_C[0].position = [0.7055500032258971, 2.5291931705157005, 0.175]
sign_C[0].rotation = [0, 0, 0]
vaporbottlerack_A[0].position = [1.9371773041816265, 1.5678735408569642, 0.155]
vaporbottlerack_A[0].rotation = [0, 0, 0]
vaporbottle_glitch_A[0].position = [4.032762123556984, 2.9357699243909727, 0.165]
vaporbottle_glitch_A[0].rotation = [0, 0, 0]
vaporbottlerack_B[0].position = [3.7903155929302867, 3.810825244656346, 0.16]
vaporbottlerack_B[0].rotation = [0, 0, 0]
vaporbottle_E[0].position = [1.2223520555505867, 2.613577666060678, 0.155]
vaporbottle_E[0].rotation = [0, 0, 0]
vaporbottle_F[0].position = [4.064806993322837, 0.405250370999112, 0.155]
vaporbottle_F[0].rotation = [0, 0, 0]
candle_A[0].position = [1.3762205100658043, 3.564029200336269, 0.08]
candle_A[0].rotation = [0, 0, 0]
vintagebottle[0].position = [4.41875278018834, 0.005127178167680491, 0.155]
vintagebottle[0].rotation = [0, 0, 0]
surrealpanel_B[0].position = [2.989553407097665, 1.9144164973326099, 0.55]
surrealpanel_B[0].rotation = [0, 0, 0]
winebook_A[0].position = [2.6493403350052374, 0.8411010808213364, 0.015]
winebook_A[0].rotation = [0, 0, 0]
ambientlight_A[0].position = [3.939155288372767, 2.103576424299115, 0.21]
ambientlight_A[0].rotation = [0, 0, 0]
corkscrew_A[0].position = [4.218343913536056, 2.9557748002974176, 0.02]
corkscrew_A[0].rotation = [0, 0, 0]
pixelpanel_A[0].position = [0.3134794320612999, 3.2139227262118606, 0.3]
pixelpanel_A[0].rotation = [0, 0, 0]
label_C[0].position = [2.4181141058298685, 3.466077451283185, 0.035]
label_C[0].rotation = [0, 0, 0]
neonsign_D[0].position = [4.214326639896527, 3.827919358873906, 0.14]
neonsign_D[0].rotation = [0, 0, 0]
wineglass_B[0].position = [0.1704200893157326, 0.035733074393663244, 0.105]
wineglass_B[0].rotation = [0, 0, 0]
rack_A[0].position = [4.176500768665596, 0.7561915762803482, 0.9]
rack_A[0].rotation = [0, 0, 0]
lamp[0].position = [3.4992162112221834, 1.5536835397658413, 0.825]
lamp[0].rotation = [0, 0, 0]
winebottlecab_A[0].position = [4.201411752756041, 3.360229098652778, 0.14]
winebottlecab_A[0].rotation = [0, 0, 0]
candle_B[0].position = [2.3381108507313124, 1.733778298268728, 0.085]
candle_B[0].rotation = [0, 0, 0]
rack_B[0].position = [1.352674786387615, 2.49046009493667, 0.9]
rack_B[0].rotation = [0, 0, 0]
vaporbottle_G[0].position = [1.0357439505982358, 2.4774064618515768, 0.16]
vaporbottle_G[0].rotation = [0, 0, 0]
wineglass_C[0].position = [4.261218895518511, 3.5080094822580223, 0.105]
wineglass_C[0].rotation = [0, 0, 0]
corkscrew_B[0].position = [0.893431784909029, 2.3056159213917433, 0.02]
corkscrew_B[0].rotation = [0, 0, 0]
vaporbottle_H[0].position = [2.0888518246973424, 0.8782873405516436, 0.155]
vaporbottle_H[0].rotation = [0, 0, 0]
pixelpanel_wall_A[0].position = [0.6083462687873664, 1.7320494404650746, 0.375]
pixelpanel_wall_A[0].rotation = [0, 0, 0]
opener_C[0].position = [4.551049050686824, 3.6159428464937, 0.015]
opener_C[0].rotation = [0, 0, 0]
pinkbottle_A[0].position = [0.8143850014250159, 0.0621544869592876, 0.16]
pinkbottle_A[0].rotation = [0, 0, 0]
winebottlecab_B[0].position = [3.1719064987988514, 3.6758220053234028, 0.14]
winebottlecab_B[0].rotation = [0, 0, 0]
vaporbottle_glitch_B[0].position = [4.172171846424911, 3.703110182122529, 0.165]
vaporbottle_glitch_B[0].rotation = [0, 0, 0]
pixelpanel_B[0].position = [2.4948608732944777, 2.0581958740854573, 0.3]
pixelpanel_B[0].rotation = [0, 0, 0]
pixelpanel_wall_B[0].position = [4.138634200701826, 3.3575004203954313, 0.375]
pixelpanel_wall_B[0].rotation = [0, 0, 0]
ambientlight_B[0].position = [2.9931724729755693, 3.396184607266163, 0.12]
ambientlight_B[0].rotation = [0, 0, 0]
pixelpanel_wall_C[0].position = [2.7119569831941748, 1.0965788442772597, 0.375]
pixelpanel_wall_C[0].rotation = [0, 0, 0]
vaporbottle_I[0].position = [2.011461532159008, 3.2537827395241092, 0.155]
vaporbottle_I[0].rotation = [0, 0, 0]
pastelbottle_B[0].position = [0.5872589622377322, 2.2387330703619233, 0.155]
pastelbottle_B[0].rotation = [0, 0, 0]
romanbust[0].position = [4.86410046295337, 2.224386831870602, 0.29]
romanbust[0].rotation = [0, 0, 0]
label_D[0].position = [2.685169887935434, 2.5267988636495105, 0.04]
label_D[0].rotation = [0, 0, 0]
floorlamp_A[0].position = [1.5508366090489423, 3.0747409823004395, 0.85]
floorlamp_A[0].rotation = [0, 0, 0]
glitchpanel_C[0].position = [0.3238668852666704, 1.1136800898360408, 0.525]
glitchpanel_C[0].rotation = [0, 0, 0]
wineglass_D[0].position = [0.7929766996164678, 2.321226666233129, 0.11]
wineglass_D[0].rotation = [0, 0, 0]
pixelpanel_C[0].position = [0.5456610232859738, 3.3537701156937825, 0.31]
pixelpanel_C[0].rotation = [0, 0, 0]
pastelbottle_C[0].position = [1.3241725102104422, 0.21699245451778282, 0.155]
pastelbottle_C[0].rotation = [0, 0, 0]
table[0].position = [4.487838263652531, 3.9383688211203234, 0.38]
table[0].rotation = [0, 0, 0]
winebottlecab_C[0].position = [3.40081135374459, 3.676733293706082, 0.14]
winebottlecab_C[0].rotation = [0, 0, 0]
pastelbottle_D[0].position = [1.7927024204743454, 0.6092379731103081, 0.155]
pastelbottle_D[0].rotation = [0, 0, 0]
chair_B[0].position = [1.8497067703851062, 0.865179304383545, 0.41]
chair_B[0].rotation = [0, 0, 0]
pastelbottle_E[0].position = [2.7185086718218496, 1.7931639762577944, 0.15]
pastelbottle_E[0].rotation = [0, 0, 0]
glitchbottle_B[0].position = [3.8337489428396476, 0.8930724916897841, 0.16]
glitchbottle_B[0].rotation = [0, 0, 0]
vaporbottle_J[0].position = [2.6892967229323816, 0.303503729756736, 0.155]
vaporbottle_J[0].rotation = [0, 0, 0]
vaporbottlerack_C[0].position = [1.198820103933106, 1.0873070868403225, 0.16]
vaporbottlerack_C[0].rotation = [0, 0, 0]
winebottletable[0].position = [2.7486714728840163, 3.897304099304933, 0.155]
winebottletable[0].rotation = [0, 0, 0]
ambientlight_C[0].position = [3.473209551561255, 0.6307836111227205, 0.12]
ambientlight_C[0].rotation = [0, 0, 0]
glitchbottle_C[0].position = [4.252169577085273, 0.48421639836259667, 0.16]
glitchbottle_C[0].rotation = [0, 0, 0]
book[0].position = [3.2408979398175424, 2.6928209591503913, 0.015]
book[0].rotation = [0, 0, 0]
pixelpanel_D[0].position = [4.361973435651059, 0.7641781457805559, 0.3]
pixelpanel_D[0].rotation = [0, 0, 0]
vaporbottle_glitch_C[0].position = [4.9732311270825145, 3.9944178271246344, 0.165]
vaporbottle_glitch_C[0].rotation = [0, 0, 0]
glitchbottle_D[0].position = [3.4376531465643345, 3.4583465353426353, 0.155]
glitchbottle_D[0].rotation = [0, 0, 0]
candle_C[0].position = [0.21946703842309456, 1.9989933176213688, 0.075]
candle_C[0].rotation = [0, 0, 0]
opener_D[0].position = [2.2897409872703633, 1.621961329793216, 0.015]
opener_D[0].rotation = [0, 0, 0]
cabinet[0].position = [2.6291285988651603, 1.9803997602133192, 0.39]
cabinet[0].rotation = [0, 0, 0]
glitchpanelwall_B[0].position = [4.977899062795471, 3.612362105859236, 0.6]
glitchpanelwall_B[0].rotation = [0, 0, 0]
pinkbottle_B[0].position = [2.1890031420947373, 2.1852899351770962, 0.16]
pinkbottle_B[0].rotation = [0, 0, 0]
neonsign_E[0].position = [2.0152421474281326, 1.513818098730494, 0.17]
neonsign_E[0].rotation = [0, 0, 0]
neonsign_F[0].position = [1.240108671848249, 3.4068853340270038, 0.2]
neonsign_F[0].rotation = [0, 0, 0]
pixelpanel_E[0].position = [0.21097490988432444, 0.4817975981265823, 0.3]
pixelpanel_E[0].rotation = [0, 0, 0]
ambientlight_D[0].position = [2.0836119279804075, 3.6019946493793213, 0.16]
ambientlight_D[0].rotation = [0, 0, 0]
decanter_A[0].position = [1.7621576115138404, 2.0419022509920426, 0.18]
decanter_A[0].rotation = [0, 0, 0]
ambientlight_E[0].position = [0.7980691903111703, 0.5296732052148871, 0.19]
ambientlight_E[0].rotation = [0, 0, 0]
glitchbottle_E[0].position = [1.15481563507412, 2.926034461311336, 0.16]
glitchbottle_E[0].rotation = [0, 0, 0]
opener_E[0].position = [2.9615399527200283, 0.6482993023029819, 0.015]
opener_E[0].rotation = [0, 0, 0]
pastelbottle_F[0].position = [1.5819356637592186, 3.4882781362210267, 0.16]
pastelbottle_F[0].rotation = [0, 0, 0]
wineglass_E[0].position = [4.310640803101742, 1.4566445714885505, 0.11]
wineglass_E[0].rotation = [0, 0, 0]
decanter_B[0].position = [3.4204699710957085, 3.453054728923074, 0.17]
decanter_B[0].rotation = [0, 0, 0]
pinkbottle_C[0].position = [1.2913910600788854, 0.1345827444697747, 0.16]
pinkbottle_C[0].rotation = [0, 0, 0]
decanter_C[0].position = [3.602675916053058, 3.8722708644373367, 0.175]
decanter_C[0].rotation = [0, 0, 0]
vaporrack_A[0].position = [2.0382532524263475, 3.824657060564422, 0.6]
vaporrack_A[0].rotation = [0, 0, 0]
corkscrew_C[0].position = [1.548390117951795, 0.11562667890564837, 0.02]
corkscrew_C[0].rotation = [0, 0, 0]
chair_C[0].position = [0.0700849594970232, 1.7314553485199613, 0.41]
chair_C[0].rotation = [0, 0, 0]
vaporbottle_pastel_B[0].position = [3.43201107292229, 0.8002572758809823, 0.16]
vaporbottle_pastel_B[0].rotation = [0, 0, 0]
neonsign_G[0].position = [4.567704930191095, 0.15094585189623766, 0.21]
neonsign_G[0].rotation = [0, 0, 0]
pastelbottle_G[0].position = [1.5718805031668333, 2.6727982807781308, 0.155]
pastelbottle_G[0].rotation = [0, 0, 0]
vaporbottle_K[0].position = [1.122297247490267, 2.04118133324696, 0.14]
vaporbottle_K[0].rotation = [0, 0, 0]
vaporbottle_glitch_D[0].position = [1.514983118196428, 2.5914039002837757, 0.165]
vaporbottle_glitch_D[0].rotation = [0, 0, 0]
pixelpanel_F[0].position = [3.6829063560681545, 0.33060458382691804, 0.3]
pixelpanel_F[0].rotation = [0, 0, 0]
vaporrack_B[0].position = [1.3332163144317666, 0.16804265449830602, 0.6]
vaporrack_B[0].rotation = [0, 0, 0]
neonsign_H[0].position = [3.3470798742219228, 0.5686015878132671, 0.19]
neonsign_H[0].rotation = [0, 0, 0]
pixelpanel_G[0].position = [2.039787689139732, 2.850862891848109, 0.3]
pixelpanel_G[0].rotation = [0, 0, 0]
floorlamp_B[0].position = [3.8894654049637625, 2.4315778012836855, 0.85]
floorlamp_B[0].rotation = [0, 0, 0]
label_E[0].position = [2.777642405719381, 1.0815319372498489, 0.035]
label_E[0].rotation = [0, 0, 0]
pastelbottle_H[0].position = [1.4166113248492755, 1.6762915583178746, 0.155]
pastelbottle_H[0].rotation = [0, 0, 0]
pinkbottle_D[0].position = [1.9353291500364493, 0.7954328246880715, 0.16]
pinkbottle_D[0].rotation = [0, 0, 0]
candle_D[0].position = [0.9343355147262655, 2.849038055727431, 0.05]
candle_D[0].rotation = [0, 0, 0]
vaporbottle_L[0].position = [0.8973409274667571, 2.581561402911272, 0.16]
vaporbottle_L[0].rotation = [0, 0, 0]
vaporbottle_M[0].position = [4.6235188148839725, 3.469106218510523, 0.14]
vaporbottle_M[0].rotation = [0, 0, 0]
sign_D[0].position = [1.4901898906495326, 2.2447192436581234, 0.16]
sign_D[0].rotation = [0, 0, 0]
opener_F[0].position = [0.596679484585903, 3.1125837755540866, 0.015]
opener_F[0].rotation = [0, 0, 0]
winebottlecab_D[0].position = [4.0974440872345514, 3.2370491004842066, 0.14]
winebottlecab_D[0].rotation = [0, 0, 0]
winebook_B[0].position = [0.7082559276344919, 1.5532478198619724, 0.015]
winebook_B[0].rotation = [0, 0, 0]
pixelpanel_H[0].position = [1.2634183051536063, 2.652209617885941, 0.3]
pixelpanel_H[0].rotation = [0, 0, 0]
pixelpanel_wall_D[0].position = [3.2577740607723005, 2.6490820841650278, 0.375]
pixelpanel_wall_D[0].rotation = [0, 0, 0]
pixelpanel_I[0].position = [0.3223552601430002, 1.4488506372571566, 0.31]
pixelpanel_I[0].rotation = [0, 0, 0]
glitchbottle_F[0].position = [1.7170212628264936, 3.462816536171464, 0.16]
glitchbottle_F[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed references let the distance constraints preserve the intended coordinates.
def _fixed_reference(position, rotation=None):
    return AssetInstance(
        position=list(position),
        rotation=list(rotation or [0.0, 0.0, 0.0]),
    )


def _place_on_floor(asset_obj, position_xy, rotation_z=0.0, wall=None):
    """Place one upright floor object and constrain both its position and orientation."""
    instance = asset_obj[0]
    position = [position_xy[0], position_xy[1], asset_obj.size[2] / 2.0]
    instance.position = position
    instance.rotation = [0.0, 0.0, rotation_z]

    position_reference = _fixed_reference(position, instance.rotation)
    if wall is not None:
        # Wall contact is the most important positional relationship for perimeter furniture.
        solver.against_wall(instance, wall)
    solver.distance_constraint(instance, position_reference, 0.0, 0.0, weight=10)
    solver.align_with(instance, position_reference, angle=0.0)


def _place_wall_display(asset_obj, position, rotation_z, wall):
    """Mount an upright panel/sign against a wall at a reserved wall slot."""
    instance = asset_obj[0]
    instance.position = list(position)
    instance.rotation = [0.0, 0.0, rotation_z]

    pose_reference = _fixed_reference(position, instance.rotation)
    solver.against_wall(instance, wall)
    solver.distance_constraint(instance, pose_reference, 0.0, 0.0, weight=10)
    solver.align_with(instance, pose_reference, angle=0.0)


def _place_on_surface(asset_obj, support_obj, position_xy, rotation_z=0.0):
    """Place a small object on a table, cabinet, or rack top."""
    instance = asset_obj[0]
    support = support_obj[0]
    position = [
        position_xy[0],
        position_xy[1],
        support.position[2] + support_obj.size[2] / 2.0 + asset_obj.size[2] / 2.0,
    ]
    instance.position = position
    instance.rotation = [0.0, 0.0, rotation_z]

    position_reference = _fixed_reference(position, instance.rotation)
    solver.on_top_of(instance, support)
    solver.distance_constraint(instance, position_reference, 0.0, 0.0, weight=10)
    solver.align_with(instance, support, angle=0.0)


# ---------------------------------------------------------------------------
# Main furniture arrangement.
# The right side around the door at (5.00, 2.91) is deliberately left open.
# ---------------------------------------------------------------------------

_place_on_floor(table, [2.55, 2.05], radians(0))

# Storage pieces occupy the north and west perimeter while remaining away from
# the door. Their broad dimensions extend inward from their respective walls.
_place_on_floor(rack_A, [1.25, 3.40], radians(0), walls[2])
_place_on_floor(rack_B, [3.65, 3.40], radians(0), walls[2])
_place_on_floor(cabinet, [0.24, 2.85], radians(0), walls[3])

_place_on_floor(lamp, [0.75, 0.35], radians(90))
_place_on_floor(floorlamp_A, [3.65, 0.32], radians(90))
_place_on_floor(floorlamp_B, [4.35, 1.55], radians(180))

# o0033 (ambientlight_A), o0101 (chair_C), and o0089 (ambientlight_D)
# form a left-to-right line. This puts chair_C strictly between the two lights.
_place_on_floor(ambientlight_D, [0.14, 1.40], radians(0), walls[3])
_place_on_floor(ambientlight_A, [1.46, 1.40], radians(0))
_place_on_floor(chair_C, [0.80, 1.40], radians(20))

ambient_D_reference = _fixed_reference(ambientlight_D[0].position)
ambient_A_reference = _fixed_reference(ambientlight_A[0].position)
solver.distance_constraint(chair_C[0], ambient_D_reference, 0.66, 0.66, weight=10)
solver.distance_constraint(chair_C[0], ambient_A_reference, 0.66, 0.66, weight=10)
solver.point_towards(chair_C[0], table[0])

# o0011 is chair_A. It faces the tasting table from the east side.
_place_on_floor(chair_A, [3.35, 2.05], radians(180))
solver.point_towards(chair_A[0], table[0])

# A second chair serves the north side of the table.
_place_on_floor(chair_B, [2.55, 3.02], radians(-90))
solver.point_towards(chair_B[0], table[0])

# Additional low lights remain around the perimeter, outside the door approach.
_place_on_floor(ambientlight_B, [4.55, 0.30], radians(90))
_place_on_floor(ambientlight_C, [3.00, 0.20], radians(90))
_place_on_floor(ambientlight_E, [4.55, 3.72], radians(180))

# ---------------------------------------------------------------------------
# Wall-mounted panels, signs, and wall racks.
# Two vertical tiers provide enough wall area without overlapping in plan.
# The east-wall slots avoid y=2.44..3.38, the door's clear opening.
# ---------------------------------------------------------------------------

wall_displays = [
    glitchpanelwall_A,
    glitchpanelcab,
    sign_A,
    neonsign_A,
    glitchpanel_A,
    neonsign_B,
    sign_B,
    glitchpanel_B,
    neonsign_C,
    surrealpanel_A,
    sign_C,
    surrealpanel_B,
    pixelpanel_A,
    neonsign_D,
    pixelpanel_wall_A,
    pixelpanel_B,
    pixelpanel_wall_B,
    pixelpanel_wall_C,
    glitchpanel_C,
    pixelpanel_C,
    pixelpanel_D,
    glitchpanelwall_B,
    neonsign_E,
    neonsign_F,
    pixelpanel_E,
    vaporrack_A,
    neonsign_G,
    pixelpanel_F,
    vaporrack_B,
    neonsign_H,
    pixelpanel_G,
    sign_D,
    pixelpanel_H,
    pixelpanel_wall_D,
    pixelpanel_I,
]

# Each tuple is (wall index, coordinate along wall, vertical tier).
# Horizontal-wall coordinates are x values; vertical-wall coordinates are y values.
wall_slots = [
    # South wall
    (0, 0.55, 0), (0, 1.50, 0), (0, 2.45, 0), (0, 3.40, 0), (0, 4.40, 0),
    (0, 0.55, 1), (0, 1.50, 1), (0, 2.45, 1), (0, 3.40, 1), (0, 4.40, 1),

    # North wall
    (2, 0.55, 0), (2, 1.50, 0), (2, 2.45, 0), (2, 3.40, 0), (2, 4.40, 0),
    (2, 0.55, 1), (2, 1.50, 1), (2, 2.45, 1), (2, 3.40, 1), (2, 4.40, 1),

    # West wall
    (3, 0.50, 0), (3, 1.45, 0), (3, 2.40, 0), (3, 3.45, 0),
    (3, 0.50, 1), (3, 1.45, 1), (3, 2.40, 1), (3, 3.45, 1),

    # East wall: all slots are outside the door opening.
    (1, 0.48, 0), (1, 1.35, 0), (1, 2.00, 0), (1, 3.72, 0),
    (1, 0.65, 1), (1, 1.65, 1), (1, 3.70, 1),
]

for display_index, asset_obj in enumerate(wall_displays):
    wall_index, along_wall, tier = wall_slots[display_index]
    wall = walls[wall_index]

    # Tall displays use centers at 0.62 m and 1.90 m. The second tier starts
    # above the tallest first-tier panel.
    display_z = max(asset_obj.size[2] / 2.0, 0.62) if tier == 0 else 1.90

    if wall_index == 0:
        # South wall; front faces into the room toward +y.
        display_position = [along_wall, asset_obj.size[0] / 2.0, display_z]
        display_rotation = radians(90)
    elif wall_index == 2:
        # North wall; front faces toward -y.
        display_position = [
            along_wall,
            4.0 - asset_obj.size[0] / 2.0,
            display_z,
        ]
        display_rotation = radians(-90)
    elif wall_index == 3:
        # West wall; front faces toward +x.
        display_position = [asset_obj.size[0] / 2.0, along_wall, display_z]
        display_rotation = radians(0)
    else:
        # East wall; front faces toward -x.
        display_position = [
            5.0 - asset_obj.size[0] / 2.0,
            along_wall,
            display_z,
        ]
        display_rotation = radians(180)

    _place_wall_display(
        asset_obj,
        display_position,
        display_rotation,
        wall,
    )

# ---------------------------------------------------------------------------
# Larger tabletop objects receive roomy, dedicated positions.
# ---------------------------------------------------------------------------

_place_on_surface(romanbust, table, [2.22, 1.42], radians(0))
_place_on_surface(decanter_A, table, [2.52, 1.42], radians(0))
_place_on_surface(decanter_B, table, [2.75, 1.42], radians(0))
_place_on_surface(decanter_C, table, [2.82, 1.72], radians(0))
_place_on_surface(winebook_A, table, [2.20, 1.84], radians(90))
_place_on_surface(winebook_B, table, [2.20, 2.14], radians(90))
_place_on_surface(book, table, [2.20, 2.42], radians(90))

# o0036 is label_C and o0066 is table. Keep this required relationship first.
_place_on_surface(label_C, table, [2.55, 2.05], radians(0))

# ---------------------------------------------------------------------------
# Bottles, glasses, candles, labels, and tools are distributed over the
# cabinet, both wine racks, and the tasting table. Grid spacing exceeds the
# footprint of these remaining small objects.
# ---------------------------------------------------------------------------

small_display_objects = [
    vaporbottle_A,
    wineglass_A,
    vaporbottle_B,
    glitchbottle_A,
    opener_A,
    opener_B,
    label_A,
    vaporbottle_C,
    vaporbottle_pastel_A,
    pastelbottle_A,
    vaporbottle_D,
    label_B,
    vaporbottlerack_A,
    vaporbottle_glitch_A,
    vaporbottlerack_B,
    vaporbottle_E,
    vaporbottle_F,
    candle_A,
    vintagebottle,
    corkscrew_A,
    wineglass_B,
    winebottlecab_A,
    candle_B,
    vaporbottle_G,
    wineglass_C,
    corkscrew_B,
    vaporbottle_H,
    opener_C,
    pinkbottle_A,
    winebottlecab_B,
    vaporbottle_glitch_B,
    vaporbottle_I,
    pastelbottle_B,
    label_D,
    wineglass_D,
    pastelbottle_C,
    winebottlecab_C,
    pastelbottle_D,
    pastelbottle_E,
    glitchbottle_B,
    vaporbottle_J,
    vaporbottlerack_C,
    winebottletable,
    glitchbottle_C,
    vaporbottle_glitch_C,
    glitchbottle_D,
    candle_C,
    opener_D,
    pinkbottle_B,
    glitchbottle_E,
    opener_E,
    pastelbottle_F,
    wineglass_E,
    pinkbottle_C,
    corkscrew_C,
    vaporbottle_pastel_B,
    pastelbottle_G,
    vaporbottle_K,
    vaporbottle_glitch_D,
    label_E,
    pastelbottle_H,
    pinkbottle_D,
    candle_D,
    vaporbottle_L,
    vaporbottle_M,
    opener_F,
    winebottlecab_D,
    glitchbottle_F,
]

# Twenty-seven narrow objects fit on the long cabinet top.
cabinet_grid = [
    (0.12 + 0.12 * column, 2.13 + 0.18 * row)
    for row in range(9)
    for column in range(3)
]

# Fourteen objects fit on each rack top in two columns.
rack_A_grid = [
    (1.18 + 0.14 * column, 2.88 + 0.17 * row)
    for row in range(7)
    for column in range(2)
]
rack_B_grid = [
    (3.58 + 0.14 * column, 2.88 + 0.17 * row)
    for row in range(7)
    for column in range(2)
]

# The remaining small objects occupy the clear eastern half of the table top.
table_grid = [
    (2.45 + 0.15 * column, 1.92 + 0.18 * row)
    for row in range(5)
    for column in range(4)
]

surface_slots = (
    [(cabinet, coordinates) for coordinates in cabinet_grid]
    + [(rack_A, coordinates) for coordinates in rack_A_grid]
    + [(rack_B, coordinates) for coordinates in rack_B_grid]
    + [(table, coordinates) for coordinates in table_grid]
)

for object_index, asset_obj in enumerate(small_display_objects):
    support_obj, coordinates = surface_slots[object_index]

    # Alternating orientations add visual variety while retaining orderly rows.
    object_rotation = radians(0 if object_index % 2 == 0 else 180)
    _place_on_surface(asset_obj, support_obj, coordinates, object_rotation)

solver.constraints = []
wineglass_A[0].position = [0.268643319606781, 2.13527774810791, 0.8849999904632568]
wineglass_A[0].rotation = [0, 0, -3.139051756259584]
wineglass_A[0].optimize = 2
winebook_A[0].position = [2.200000047683716, 1.840000033378601, 0.7749999761581421]
winebook_A[0].rotation = [0, 0, 1.5733371662749223]
winebook_A[0].optimize = 2
rack_A[0].position = [1.25, 3.39396071434021, 0.8999999761581421]
rack_A[0].rotation = [0, 0, 0.08967538175337093]
rack_A[0].optimize = 2
neonsign_H[0].position = [4.968882083892822, 1.350000023841858, 0.1899999976158142]
neonsign_H[0].rotation = [0, 0, -3.1390517366612336]
neonsign_H[0].optimize = 2
label_D[0].position = [1.1799999475479126, 3.390000104904175, 1.8399999141693115]
label_D[0].rotation = [0, 0, -3.139051691053925]
label_D[0].optimize = 2
pixelpanel_E[0].position = [0.016124853864312172, 0.5, 0.30000001192092896]
pixelpanel_E[0].rotation = [0, 0, 0.0025409193727581954]
pixelpanel_E[0].optimize = 2
pixelpanel_C[0].position = [4.400000095367432, 3.9839017391204834, 0.3100000023841858]
pixelpanel_C[0].rotation = [0, 0, -1.5682554083443117]
pixelpanel_C[0].optimize = 2
wineglass_D[0].position = [1.3200000524520874, 3.390000104904175, 1.909999966621399]
wineglass_D[0].rotation = [0, 0, 0.022791528467971264]
wineglass_D[0].optimize = 2
pixelpanel_D[0].position = [0.011367769911885262, 0.5, 0.30000001192092896]
pixelpanel_D[0].rotation = [0, 0, 0.0025409193727581954]
pixelpanel_D[0].optimize = 2
vaporbottle_M[0].position = [2.5999999046325684, 2.2799999713897705, 0.8999999761581421]
vaporbottle_M[0].rotation = [0, 0, 0.022791645292255164]
vaporbottle_M[0].optimize = 2
pixelpanel_wall_D[0].position = [4.9885125160217285, 1.649999976158142, 0.375]
pixelpanel_wall_D[0].rotation = [0, 0, -3.139051734217035]
pixelpanel_wall_D[0].optimize = 2
candle_B[0].position = [0.23999999463558197, 3.390000104904175, 0.8649999499320984]
candle_B[0].rotation = [0, 0, 0.022791683149700356]
candle_B[0].optimize = 2
pastelbottle_B[0].position = [1.3200000524520874, 3.2200000286102295, 1.9549999237060547]
pastelbottle_B[0].rotation = [0, 0, 0.022791528467971264]
pastelbottle_B[0].optimize = 2
glitchbottle_C[0].position = [3.5799999237060547, 3.049999952316284, 1.959999918937683]
glitchbottle_C[0].rotation = [0, 0, -3.139051691053925]
glitchbottle_C[0].optimize = 2
ambientlight_C[0].position = [3.0, 0.20000000298023224, 0.11999999731779099]
ambientlight_C[0].rotation = [0, 0, 1.5802211042556205]
ambientlight_C[0].optimize = 2
pixelpanel_G[0].position = [4.9885125160217285, 2.0, 0.30000001192092896]
pixelpanel_G[0].rotation = [0, 0, -3.1390517332948615]
pixelpanel_G[0].optimize = 2
vaporrack_B[0].position = [4.875585079193115, 0.7483700513839722, 0.6000000238418579]
vaporrack_B[0].rotation = [0, 0, -3.139051748604684]
vaporrack_B[0].optimize = 2
pinkbottle_C[0].position = [3.5799999237060547, 3.9000000953674316, 1.959999918937683]
pinkbottle_C[0].rotation = [0, 0, -3.139051691053925]
pinkbottle_C[0].optimize = 2
decanter_A[0].position = [2.5199999809265137, 1.4199999570846558, 0.9399999976158142]
decanter_A[0].rotation = [0, 0, 0.022791645292255164]
decanter_A[0].optimize = 2
pinkbottle_A[0].position = [1.3200000524520874, 2.880000114440918, 1.959999918937683]
pinkbottle_A[0].rotation = [0, 0, 0.022791528467971264]
pinkbottle_A[0].optimize = 2
vaporbottle_pastel_A[0].position = [0.36000001430511475, 2.490000009536743, 0.9399999380111694]
vaporbottle_pastel_A[0].rotation = [0, 0, 0.022791683149700356]
vaporbottle_pastel_A[0].optimize = 2
pixelpanel_wall_B[0].position = [1.5, 3.9886109828948975, 0.375]
pixelpanel_wall_B[0].rotation = [0, 0, -1.5682554074221384]
pixelpanel_wall_B[0].optimize = 2
ambientlight_B[0].position = [4.550000190734863, 0.30000001192092896, 0.11999999731779099]
ambientlight_B[0].rotation = [0, 0, 1.5802211042556205]
ambientlight_B[0].optimize = 2
vaporbottle_glitch_B[0].position = [1.3200000524520874, 3.049999952316284, 1.9649999141693115]
vaporbottle_glitch_B[0].rotation = [0, 0, 0.022791528467971264]
vaporbottle_glitch_B[0].optimize = 2
glitchbottle_D[0].position = [3.5799999237060547, 3.2200000286102295, 1.9549999237060547]
glitchbottle_D[0].rotation = [0, 0, -3.139051691053925]
glitchbottle_D[0].optimize = 2
vaporbottle_C[0].position = [0.23999999463558197, 2.490000009536743, 0.934999942779541]
vaporbottle_C[0].rotation = [0, 0, -3.139051756259584]
vaporbottle_C[0].optimize = 2
pastelbottle_H[0].position = [2.5999999046325684, 2.0999999046325684, 0.9149999618530273]
pastelbottle_H[0].rotation = [0, 0, 0.022791645292255164]
pastelbottle_H[0].optimize = 2
vaporbottle_K[0].position = [2.75, 1.9199999570846558, 0.8999999761581421]
vaporbottle_K[0].rotation = [0, 0, -3.139051739727678]
vaporbottle_K[0].optimize = 2
pastelbottle_F[0].position = [3.5799999237060547, 3.7300000190734863, 1.959999918937683]
pastelbottle_F[0].rotation = [0, 0, -3.139051691053925]
pastelbottle_F[0].optimize = 2
corkscrew_A[0].position = [0.23999999463558197, 3.2100000381469727, 0.7999999523162842]
corkscrew_A[0].rotation = [0, 0, -3.139051756259584]
corkscrew_A[0].optimize = 2
winebottlecab_D[0].position = [2.9000000953674316, 2.2799999713897705, 0.8999999761581421]
winebottlecab_D[0].rotation = [0, 0, 0.022791645292255164]
winebottlecab_D[0].optimize = 2
vaporbottle_E[0].position = [0.11999999731779099, 3.0299999713897705, 0.934999942779541]
vaporbottle_E[0].rotation = [0, 0, -3.139051756259584]
vaporbottle_E[0].optimize = 2
glitchpanelwall_B[0].position = [0.016124853864312172, 1.4500000476837158, 0.6000000238418579]
glitchpanelwall_B[0].rotation = [0, 0, 0.0025409172284856325]
glitchpanelwall_B[0].optimize = 2
corkscrew_B[0].position = [0.23999999463558197, 3.569999933242798, 0.7999999523162842]
corkscrew_B[0].rotation = [0, 0, -3.139051756259584]
corkscrew_B[0].optimize = 2
ambientlight_E[0].position = [4.550000190734863, 3.7200000286102295, 0.1899999976158142]
ambientlight_E[0].rotation = [0, 0, -3.1321678761290697]
ambientlight_E[0].optimize = 2
sign_D[0].position = [4.983956336975098, 3.624715566635132, 0.1599999964237213]
sign_D[0].rotation = [0, 0, -3.1390517363613077]
sign_D[0].optimize = 2
neonsign_E[0].position = [0.016124853864312172, 2.4000000953674316, 0.17000000178813934]
neonsign_E[0].rotation = [0, 0, 0.0025409160063866866]
neonsign_E[0].optimize = 2
pastelbottle_A[0].position = [0.16847185790538788, 2.67893123626709, 0.934999942779541]
pastelbottle_A[0].rotation = [0, 0, -3.139051756259584]
pastelbottle_A[0].optimize = 2
winebottlecab_B[0].position = [1.1799999475479126, 3.049999952316284, 1.9399999380111694]
winebottlecab_B[0].rotation = [0, 0, -3.139051691053925]
winebottlecab_B[0].optimize = 2
vaporbottle_D[0].position = [0.23999999463558197, 2.6700000762939453, 0.9399999380111694]
vaporbottle_D[0].rotation = [0, 0, 0.022791683149700356]
vaporbottle_D[0].optimize = 2
vintagebottle[0].position = [0.11999999731779099, 3.2100000381469727, 0.934999942779541]
vintagebottle[0].rotation = [0, 0, 0.022791683149700356]
vintagebottle[0].optimize = 2
vaporbottle_I[0].position = [1.1799999475479126, 3.2200000286102295, 1.9549999237060547]
vaporbottle_I[0].rotation = [0, 0, -3.139051691053925]
vaporbottle_I[0].optimize = 2
glitchpanelwall_A[0].position = [0.550000011920929, 0.016124853864312172, 0.6000000238418579]
glitchpanelwall_A[0].rotation = [0, 0, 1.5733372440233822]
glitchpanelwall_A[0].optimize = 2
vaporbottlerack_C[0].position = [3.5799999237060547, 2.880000114440918, 1.959999918937683]
vaporbottlerack_C[0].rotation = [0, 0, -3.139051691053925]
vaporbottlerack_C[0].optimize = 2
glitchpanel_B[0].position = [2.450000047683716, 0.016124853864312172, 0.5249999761581421]
glitchpanel_B[0].rotation = [0, 0, 1.573337243101209]
glitchpanel_B[0].optimize = 2
label_C[0].position = [2.549999952316284, 2.049999952316284, 0.7950000166893005]
label_C[0].rotation = [0, 0, 0.022791645292255164]
label_C[0].optimize = 2
candle_C[0].position = [3.7200000286102295, 3.2200000286102295, 1.875]
candle_C[0].rotation = [0, 0, 0.022791528467971264]
candle_C[0].optimize = 2
pixelpanel_B[0].position = [0.550000011920929, 3.9838411808013916, 0.30000001192092896]
pixelpanel_B[0].rotation = [0, 0, -1.5682554083443117]
pixelpanel_B[0].optimize = 2
opener_F[0].position = [2.75, 2.2799999713897705, 0.7749999761581421]
opener_F[0].rotation = [0, 0, -3.139051739727678]
opener_F[0].optimize = 2
glitchbottle_B[0].position = [1.1799999475479126, 3.9000000953674316, 1.959999918937683]
glitchbottle_B[0].rotation = [0, 0, -3.139051691053925]
glitchbottle_B[0].optimize = 2
pinkbottle_D[0].position = [2.75, 2.0999999046325684, 0.9199999570846558]
pinkbottle_D[0].rotation = [0, 0, -3.139051739727678]
pinkbottle_D[0].optimize = 2
neonsign_F[0].position = [0.031143315136432648, 3.450000047683716, 0.20000000298023224]
neonsign_F[0].rotation = [0, 0, 0.0025409150842135757]
neonsign_F[0].optimize = 2
glitchbottle_E[0].position = [3.5799999237060547, 3.559999942779541, 1.959999918937683]
glitchbottle_E[0].rotation = [0, 0, -3.139051691053925]
glitchbottle_E[0].optimize = 2
neonsign_B[0].position = [0.550000011920929, 0.031079793348908424, 0.20999999344348907]
neonsign_B[0].rotation = [0, 0, 1.5733372428012833]
neonsign_B[0].optimize = 2
ambientlight_D[0].position = [0.14058396220207214, 1.399999976158142, 0.1599999964237213]
ambientlight_D[0].rotation = [0, 0, 0.0025409202949315235]
ambientlight_D[0].optimize = 2
book[0].position = [2.200000047683716, 2.4200000762939453, 0.7749999761581421]
book[0].rotation = [0, 0, 1.5733371662749223]
book[0].optimize = 2
pinkbottle_B[0].position = [3.7200000286102295, 3.390000104904175, 1.959999918937683]
pinkbottle_B[0].rotation = [0, 0, 0.022791528467971264]
pinkbottle_B[0].optimize = 2
romanbust[0].position = [2.2200000286102295, 1.4199999570846558, 1.0499999523162842]
romanbust[0].rotation = [0, 0, 0.022791645292255164]
romanbust[0].optimize = 2
opener_A[0].position = [0.23999999463558197, 2.309999942779541, 0.7949999570846558]
opener_A[0].rotation = [0, 0, 0.022791683149700356]
opener_A[0].optimize = 2
pixelpanel_H[0].position = [4.9885125160217285, 0.6499999761581421, 0.30000001192092896]
pixelpanel_H[0].rotation = [0, 0, -3.1390517332948615]
pixelpanel_H[0].optimize = 2
vaporrack_A[0].position = [0.12690527737140656, 1.4500000476837158, 0.6000000238418579]
vaporrack_A[0].rotation = [0, 0, 0.0025409049851092386]
vaporrack_A[0].optimize = 2
vaporbottle_pastel_B[0].position = [2.450000047683716, 1.9199999570846558, 0.9199999570846558]
vaporbottle_pastel_B[0].rotation = [0, 0, -3.139051739727678]
vaporbottle_pastel_B[0].optimize = 2
glitchpanel_C[0].position = [3.4000000953674316, 3.9839017391204834, 0.5249999761581421]
glitchpanel_C[0].rotation = [0, 0, -1.5682554086442377]
glitchpanel_C[0].optimize = 2
ambientlight_A[0].position = [1.4600000381469727, 1.399999976158142, 0.20999999344348907]
ambientlight_A[0].rotation = [0, 0, 0.00942477746072377]
ambientlight_A[0].optimize = 2
table[0].position = [2.549999952316284, 2.049999952316284, 0.3799999952316284]
table[0].rotation = [0, 0, 0.15079645166685368]
table[0].optimize = 2
pastelbottle_D[0].position = [1.1799999475479126, 3.7300000190734863, 1.9549999237060547]
pastelbottle_D[0].rotation = [0, 0, -3.139051691053925]
pastelbottle_D[0].optimize = 2
vaporbottle_L[0].position = [2.450000047683716, 2.2799999713897705, 0.9199999570846558]
vaporbottle_L[0].rotation = [0, 0, -3.139051739727678]
vaporbottle_L[0].optimize = 2
opener_E[0].position = [3.7200000286102295, 3.559999942779541, 1.8149999380111694]
opener_E[0].rotation = [0, 0, 0.022791528467971264]
opener_E[0].optimize = 2
winebottletable[0].position = [3.7200000286102295, 2.880000114440918, 1.9549999237060547]
winebottletable[0].rotation = [0, 0, 0.022791528467971264]
winebottletable[0].optimize = 2
vaporbottle_F[0].position = [0.23999999463558197, 3.0299999713897705, 0.934999942779541]
vaporbottle_F[0].rotation = [0, 0, 0.022791683149700356]
vaporbottle_F[0].optimize = 2
candle_D[0].position = [2.9000000953674316, 2.0999999046325684, 0.8100000023841858]
candle_D[0].rotation = [0, 0, 0.022791645292255164]
candle_D[0].optimize = 2
glitchbottle_A[0].position = [0.2326260209083557, 2.330751895904541, 0.9399999380111694]
glitchbottle_A[0].rotation = [0, 0, -3.139051756259584]
glitchbottle_A[0].optimize = 2
lamp[0].position = [0.75, 0.3499999940395355, 0.824999988079071]
lamp[0].rotation = [0, 0, 1.5802211042556205]
lamp[0].optimize = 2
chair_C[0].position = [0.800000011920929, 1.399999976158142, 0.4099999964237213]
chair_C[0].rotation = [0, 0, 0.3679154049051936]
chair_C[0].optimize = 2
neonsign_C[0].position = [3.4000000953674316, 0.03120683692395687, 0.20999999344348907]
neonsign_C[0].rotation = [0, 0, 1.5733372415791846]
neonsign_C[0].optimize = 2
glitchpanel_A[0].position = [4.400000095367432, 0.011367837898433208, 0.15000000596046448]
glitchpanel_A[0].rotation = [0, 0, 1.573337246467581]
glitchpanel_A[0].optimize = 2
neonsign_D[0].position = [3.4000000953674316, 3.9839017391204834, 0.14000000059604645]
neonsign_D[0].rotation = [0, 0, -1.5682554083443117]
neonsign_D[0].optimize = 2
decanter_B[0].position = [2.75, 1.4199999570846558, 0.9300000071525574]
decanter_B[0].rotation = [0, 0, 0.022791645292255164]
decanter_B[0].optimize = 2
vaporbottle_glitch_C[0].position = [3.7200000286102295, 3.049999952316284, 1.9649999141693115]
vaporbottle_glitch_C[0].rotation = [0, 0, 0.022791528467971264]
vaporbottle_glitch_C[0].optimize = 2
vaporbottle_glitch_D[0].position = [2.9000000953674316, 1.9199999570846558, 0.925000011920929]
vaporbottle_glitch_D[0].rotation = [0, 0, 0.022791645292255164]
vaporbottle_glitch_D[0].optimize = 2
winebottlecab_C[0].position = [1.3200000524520874, 3.559999942779541, 1.9399999380111694]
winebottlecab_C[0].rotation = [0, 0, 0.022791528467971264]
winebottlecab_C[0].optimize = 2
candle_A[0].position = [0.36000001430511475, 3.0299999713897705, 0.85999995470047]
candle_A[0].rotation = [0, 0, -3.139051756259584]
candle_A[0].optimize = 2
floorlamp_B[0].position = [4.349999904632568, 1.5499999523162842, 0.8500000238418579]
floorlamp_B[0].rotation = [0, 0, -3.1321678761290697]
floorlamp_B[0].optimize = 2
label_E[0].position = [2.450000047683716, 2.0999999046325684, 0.7950000166893005]
label_E[0].rotation = [0, 0, -3.139051739727678]
label_E[0].optimize = 2
opener_C[0].position = [1.1799999475479126, 2.880000114440918, 1.8149999380111694]
opener_C[0].rotation = [0, 0, -3.139051691053925]
opener_C[0].optimize = 2
glitchpanelcab[0].position = [1.5, 0.016124853864312172, 0.550000011920929]
glitchpanelcab[0].rotation = [0, 0, 1.5733372449455554]
glitchpanelcab[0].optimize = 2
opener_B[0].position = [0.36000001430511475, 2.309999942779541, 0.7949999570846558]
opener_B[0].rotation = [0, 0, -3.139051756259584]
opener_B[0].optimize = 2
rack_B[0].position = [3.6500000953674316, 3.39396071434021, 0.8999999761581421]
rack_B[0].rotation = [0, 0, 0.08967538175337093]
rack_B[0].optimize = 2
neonsign_A[0].position = [3.4000000953674316, 0.031143315136432648, 0.20000000298023224]
neonsign_A[0].rotation = [0, 0, 1.5733372418791103]
neonsign_A[0].optimize = 2
pixelpanel_wall_C[0].position = [2.450000047683716, 3.9886109828948975, 0.375]
pixelpanel_wall_C[0].rotation = [0, 0, -1.5682554074221384]
pixelpanel_wall_C[0].optimize = 2
sign_C[0].position = [0.550000011920929, 3.9689838886260986, 0.17499999701976776]
sign_C[0].rotation = [0, 0, -1.5682554107885098]
sign_C[0].optimize = 2
neonsign_G[0].position = [0.031079793348908424, 2.4000000953674316, 0.20999999344348907]
neonsign_G[0].rotation = [0, 0, 0.0025409160063866866]
neonsign_G[0].optimize = 2
corkscrew_C[0].position = [3.7200000286102295, 3.9000000953674316, 1.8199999332427979]
corkscrew_C[0].rotation = [0, 0, 0.022791528467971264]
corkscrew_C[0].optimize = 2
vaporbottle_A[0].position = [0.26470306515693665, 2.1566624641418457, 0.9399999380111694]
vaporbottle_A[0].rotation = [0, 0, 0.022791683149700356]
vaporbottle_A[0].optimize = 2
vaporbottle_G[0].position = [0.36000001430511475, 3.390000104904175, 0.9399999380111694]
vaporbottle_G[0].rotation = [0, 0, -3.139051756259584]
vaporbottle_G[0].optimize = 2
pixelpanel_I[0].position = [4.983956336975098, 3.6897103786468506, 0.3100000023841858]
pixelpanel_I[0].rotation = [0, 0, -3.139051734217035]
pixelpanel_I[0].optimize = 2
decanter_C[0].position = [2.819999933242798, 1.7200000286102295, 0.9350000023841858]
decanter_C[0].rotation = [0, 0, 0.022791645292255164]
decanter_C[0].optimize = 2
chair_A[0].position = [3.3499999046325684, 2.049999952316284, 0.4099999964237213]
chair_A[0].rotation = [0, 0, -3.1290262823329655]
chair_A[0].optimize = 2
vaporbottlerack_A[0].position = [0.13639482855796814, 2.853020668029785, 0.934999942779541]
vaporbottlerack_A[0].rotation = [0, 0, 0.022791683149700356]
vaporbottlerack_A[0].optimize = 2
wineglass_E[0].position = [3.7200000286102295, 3.7300000190734863, 1.909999966621399]
wineglass_E[0].rotation = [0, 0, 0.022791528467971264]
wineglass_E[0].optimize = 2
vaporbottle_B[0].position = [0.36000001430511475, 2.130000114440918, 0.934999942779541]
vaporbottle_B[0].rotation = [0, 0, 0.022791683149700356]
vaporbottle_B[0].optimize = 2
floorlamp_A[0].position = [3.6500000953674316, 0.3199999928474426, 0.8500000238418579]
floorlamp_A[0].rotation = [0, 0, 1.5802211042556205]
floorlamp_A[0].optimize = 2
glitchbottle_F[0].position = [2.450000047683716, 2.4600000381469727, 0.9199999570846558]
glitchbottle_F[0].rotation = [0, 0, -3.139051739727678]
glitchbottle_F[0].optimize = 2
vaporbottle_H[0].position = [0.36000001430511475, 3.569999933242798, 0.934999942779541]
vaporbottle_H[0].rotation = [0, 0, 0.022791683149700356]
vaporbottle_H[0].optimize = 2
pixelpanel_wall_A[0].position = [4.400000095367432, 3.9886109828948975, 0.375]
pixelpanel_wall_A[0].rotation = [0, 0, -1.5682554074221384]
pixelpanel_wall_A[0].optimize = 2
label_A[0].position = [0.2005489319562912, 2.5048415660858154, 0.8149999976158142]
label_A[0].rotation = [0, 0, 0.022791683149700356]
label_A[0].optimize = 2
pixelpanel_F[0].position = [0.011367769911885262, 3.450000047683716, 0.30000001192092896]
pixelpanel_F[0].rotation = [0, 0, 0.0025409193727581954]
pixelpanel_F[0].optimize = 2
surrealpanel_B[0].position = [1.5, 3.9839017391204834, 0.550000011920929]
surrealpanel_B[0].rotation = [0, 0, -1.5682554098663368]
surrealpanel_B[0].optimize = 2
pastelbottle_G[0].position = [2.5999999046325684, 1.9199999570846558, 0.9149999618530273]
pastelbottle_G[0].rotation = [0, 0, 0.022791645292255164]
pastelbottle_G[0].optimize = 2
cabinet[0].position = [0.37099146842956543, 2.8499999046325684, 0.38999998569488525]
cabinet[0].rotation = [0, 0, 0.17065907556016072]
cabinet[0].optimize = 2
opener_D[0].position = [3.5799999237060547, 3.390000104904175, 1.8149999380111694]
opener_D[0].rotation = [0, 0, -3.139051691053925]
opener_D[0].optimize = 2
wineglass_C[0].position = [0.11999999731779099, 3.569999933242798, 0.8849999904632568]
wineglass_C[0].rotation = [0, 0, 0.022791683149700356]
wineglass_C[0].optimize = 2
vaporbottle_J[0].position = [1.3200000524520874, 3.9000000953674316, 1.9549999237060547]
vaporbottle_J[0].rotation = [0, 0, 0.022791528467971264]
vaporbottle_J[0].optimize = 2
pixelpanel_A[0].position = [2.450000047683716, 3.9885122776031494, 0.30000001192092896]
pixelpanel_A[0].rotation = [0, 0, -1.5682554064999652]
pixelpanel_A[0].optimize = 2
pastelbottle_C[0].position = [1.1799999475479126, 3.559999942779541, 1.9549999237060547]
pastelbottle_C[0].rotation = [0, 0, -3.139051691053925]
pastelbottle_C[0].optimize = 2
pastelbottle_E[0].position = [1.3200000524520874, 3.7300000190734863, 1.9499999284744263]
pastelbottle_E[0].rotation = [0, 0, 0.022791528467971264]
pastelbottle_E[0].optimize = 2
sign_A[0].position = [2.450000047683716, 0.031016269698739052, 0.17499999701976776]
sign_A[0].rotation = [0, 0, 1.5733372437234565]
sign_A[0].optimize = 2
vaporbottle_glitch_A[0].position = [0.23999999463558197, 2.8499999046325684, 0.9449999928474426]
vaporbottle_glitch_A[0].rotation = [0, 0, -3.139051756259584]
vaporbottle_glitch_A[0].optimize = 2
sign_B[0].position = [1.5, 0.016124853864312172, 0.1599999964237213]
sign_B[0].rotation = [0, 0, 1.5733372440233822]
sign_B[0].optimize = 2
winebook_B[0].position = [2.200000047683716, 2.140000104904175, 0.7749999761581421]
winebook_B[0].rotation = [0, 0, 1.5733371662749223]
winebook_B[0].optimize = 2
surrealpanel_A[0].position = [4.400000095367432, 0.016124853864312172, 0.550000011920929]
surrealpanel_A[0].rotation = [0, 0, 1.5733372437234565]
surrealpanel_A[0].optimize = 2
winebottlecab_A[0].position = [0.11999999731779099, 3.390000104904175, 0.9199999570846558]
winebottlecab_A[0].rotation = [0, 0, -3.139051756259584]
winebottlecab_A[0].optimize = 2
vaporbottlerack_B[0].position = [0.36000001430511475, 2.8499999046325684, 0.9399999380111694]
vaporbottlerack_B[0].rotation = [0, 0, 0.022791683149700356]
vaporbottlerack_B[0].optimize = 2
chair_B[0].position = [2.549999952316284, 3.0199999809265137, 0.4099999964237213]
chair_B[0].rotation = [0, 0, -1.5582299555380688]
chair_B[0].optimize = 2
label_B[0].position = [0.36000001430511475, 2.6700000762939453, 0.8199999928474426]
label_B[0].rotation = [0, 0, -3.139051756259584]
label_B[0].optimize = 2
wineglass_B[0].position = [0.36000001430511475, 3.2100000381469727, 0.8849999904632568]
wineglass_B[0].rotation = [0, 0, 0.022791683149700356]
wineglass_B[0].optimize = 2

