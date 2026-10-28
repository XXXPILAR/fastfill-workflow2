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
posterwall_A = Assets(description="A single piece of thin and upright retro 1950s diner style poster with a rectangular paper surface, pastel pink background, vintage illustration and a glossy finish", size=[0.01, 0.61, 0.91], placements=[AssetInstance() for _ in range(1)])
penworkbench_A = Assets(description="A retro 1950s diner style ballpoint pen, slender cylindrical shape, pastel plastic body and thin metal tip", size=[0.01, 0.14, 0.01], placements=[AssetInstance() for _ in range(1)])
posterwall_B = Assets(description="A retro 1950s diner style poster with vintage illustration, single piece of thin and upright rectangular paper, matte finish", size=[0.01, 0.51, 0.76], placements=[AssetInstance() for _ in range(1)])
pottedplant_A = Assets(description="A retro 1950s diner style potted plant with a short cylindrical pot in pastel coral, containing a small leafy green sprout, the pot has a subtle chrome rim", size=[0.35, 0.35, 0.65], placements=[AssetInstance() for _ in range(1)])
penworkbench_B = Assets(description="A retro 1950s diner style ballpoint pen, slender cylindrical shape, pastel plastic body and thin metal tip", size=[0.01, 0.14, 0.01], placements=[AssetInstance() for _ in range(1)])
jukebox = Assets(description="A classic diner jukebox with a rectangular body, chrome trim, pastel teal and pink paneling, rounded corners and a glass front that displays the selection buttons", size=[0.55, 0.90, 1.45], placements=[AssetInstance() for _ in range(1)])
picture_A = Assets(description="A thin upright retro wall picture with a rectangular canvas, pastel pink and teal abstract design, a subtle glossy finish and a narrow wooden frame", size=[0.04, 0.70, 0.90], placements=[AssetInstance() for _ in range(1)])
lightfixture_A = Assets(description="A wall‑mounted light fixture with a rectangular slim profile, frosted glass panel, pastel yellow glow, retro 1950s diner style, thin and upright", size=[0.10, 0.18, 0.50], placements=[AssetInstance() for _ in range(1)])
bookdesk_A = Assets(description="A retro 1950s diner style paperback book, rectangular, pastel‑colored cover, slightly rounded corners and a thin dust jacket", size=[0.16, 0.22, 0.03], placements=[AssetInstance() for _ in range(1)])
bookcabinet_A = Assets(description="A retro 1950s diner style paperback book, rectangular, pastel cover, thin dust jacket and rounded edges", size=[0.15, 0.21, 0.03], placements=[AssetInstance() for _ in range(1)])
pottedplant_B = Assets(description="A potted plant with a cylindrical pot, matte pastel teal finish, green foliage, retro 1950s diner style, squat and rounded", size=[0.40, 0.40, 0.70], placements=[AssetInstance() for _ in range(1)])
stool_A = Assets(description="A compact vinyl stool with a curved saddle seat, chrome‑finished legs, and a pastel pink or teal finish, the seat is slightly rounded and the legs are splayed for stability", size=[0.42, 0.46, 0.68], placements=[AssetInstance() for _ in range(1)])
pendesk_A = Assets(description="A retro 1950s diner style pen with a slim cylindrical barrel, chrome tip and pastel handle; a second pen of the same style placed beside a small holder", size=[0.09, 0.20, 0.08], placements=[AssetInstance() for _ in range(1)])
vaseworkbench_A = Assets(description="A ceramic vase with a rounded bulbous shape, glossy pastel pink finish and subtle teal stripe, retro 1950s diner style, squat and decorative", size=[0.24, 0.24, 0.28], placements=[AssetInstance() for _ in range(1)])
vasecounter_A = Assets(description="A ceramic vase with a rounded bulbous shape, glossy pastel pink finish and subtle teal stripe, retro 1950s diner style, squat and decorative", size=[0.24, 0.24, 0.28], placements=[AssetInstance() for _ in range(1)])
vasecabinet_A = Assets(description="A ceramic vase with a rounded bulbous shape, glossy pastel pink finish and subtle teal stripe, retro 1950s diner style, squat and decorative", size=[0.24, 0.24, 0.28], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="A tall rectangular chrome storage cabinet with sleek straight edges, a brushed metal finish and recessed handles, the doors are frameless for a minimalist look", size=[0.45, 0.90, 1.90], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="A single piece of thin and upright chrome shelf with a flat rectangular surface, sleek straight edges and a subtle reflective finish, the shelf is mounted flush to the wall", size=[0.28, 1.20, 0.05], placements=[AssetInstance() for _ in range(1)])
pottedplant_C = Assets(description="A retro 1950s diner style potted plant with a short cylindrical pot in pastel coral, containing a small leafy green sprout, the pot has a subtle chrome rim", size=[0.35, 0.35, 0.65], placements=[AssetInstance() for _ in range(1)])
notebookdesk_A = Assets(description="A retro 1950s diner style spiral‑bound notebook with a glossy pastel pink cover, rectangular shape and thin profile", size=[0.17, 0.23, 0.02], placements=[AssetInstance() for _ in range(1)])
pottedplantfloor_A = Assets(description="A retro 1950s diner style potted plant in a small ceramic pot, round pastel‑green glaze and compact leafy foliage", size=[0.32, 0.32, 0.50], placements=[AssetInstance() for _ in range(1)])
clock = Assets(description="A single piece of thin and upright wall clock with a circular face, pastel teal background, chrome hour markers and a small retro font for numbers, the hands are chrome‑finished", size=[0.05, 0.40, 0.40], placements=[AssetInstance() for _ in range(1)])
lightfixturewall_A = Assets(description="A retro 1950s diner style wall‑mounted light fixture with a curved rectangular shade, pastel teal glass, chrome trim and a small exposed bulb", size=[0.16, 0.42, 0.22], placements=[AssetInstance() for _ in range(1)])
vasefloor_A = Assets(description="A retro 1950s diner style ceramic vase, squat cylindrical shape, pastel finish, slightly flared rim and thin decorative accent", size=[0.27, 0.27, 0.32], placements=[AssetInstance() for _ in range(1)])
lightfixturewall_B = Assets(description="A retro 1950s diner style wall‑mounted light fixture with a curved rectangular shade, pastel teal glass, chrome trim and a small exposed bulb", size=[0.16, 0.42, 0.22], placements=[AssetInstance() for _ in range(1)])
stool_B = Assets(description="A compact vinyl stool with a curved saddle seat, chrome‑finished legs, and a pastel pink or teal finish, the seat is slightly rounded and the legs are splayed for stability", size=[0.42, 0.46, 0.68], placements=[AssetInstance() for _ in range(1)])
stool_C = Assets(description="A compact vinyl stool with a curved saddle seat, chrome‑finished legs, and a pastel pink or teal finish, the seat is slightly rounded and the legs are splayed for stability", size=[0.42, 0.46, 0.68], placements=[AssetInstance() for _ in range(1)])
lightfixture_B = Assets(description="A single piece of thin and upright retro 1950s diner style wall light fixture with a rectangular chrome frame, pastel teal glass panels and a subtle frosted interior glow", size=[0.11, 0.22, 0.52], placements=[AssetInstance() for _ in range(1)])
pottedplantfloor_B = Assets(description="A retro 1950s diner style potted plant with a small round pot, pastel glaze, a compact green foliage clump and a short stem", size=[0.30, 0.30, 0.48], placements=[AssetInstance() for _ in range(1)])
pottedplant_D = Assets(description="A retro 1950s diner style potted plant with a short cylindrical pot in pastel coral, containing a small leafy green sprout, the pot has a subtle chrome rim", size=[0.35, 0.35, 0.65], placements=[AssetInstance() for _ in range(1)])
posterwall_C = Assets(description="A retro 1950s diner style poster with vintage illustration, single piece of thin and upright rectangular paper, matte finish", size=[0.01, 0.51, 0.76], placements=[AssetInstance() for _ in range(1)])
lightfixture_C = Assets(description="A wall‑mounted light fixture with a rectangular slim profile, frosted glass panel, pastel yellow glow, retro 1950s diner style, thin and upright", size=[0.10, 0.18, 0.50], placements=[AssetInstance() for _ in range(1)])
record_A = Assets(description="A vinyl record with a circular flat disc, glossy pastel pink label, retro 1950s diner style, thin and round", size=[0.01, 0.30, 0.30], placements=[AssetInstance() for _ in range(1)])
picture_B = Assets(description="A thin upright retro wall picture with a rectangular canvas, pastel pink and teal abstract design, a subtle glossy finish and a narrow wooden frame", size=[0.04, 0.70, 0.90], placements=[AssetInstance() for _ in range(1)])
sign_A = Assets(description="A wall sign with a rectangular shape, pastel red background, white retro script, retro 1950s diner style, thin and upright", size=[0.04, 0.90, 0.35], placements=[AssetInstance() for _ in range(1)])
toolcounter_A = Assets(description="A wooden flower‑arrangement tool with a slender elongated handle, polished walnut finish, retro 1950s diner style, featuring a small brass hook at the end", size=[0.04, 0.32, 0.04], placements=[AssetInstance() for _ in range(1)])
posterwall_D = Assets(description="A single piece of thin and upright retro 1950s diner style poster with a rectangular paper surface, pastel pink background, vintage illustration and a glossy finish", size=[0.01, 0.61, 0.91], placements=[AssetInstance() for _ in range(1)])
bookcabinet_B = Assets(description="A retro 1950s diner style paperback book with a floral printed softcover, slim rectangular shape and rounded corners", size=[0.16, 0.22, 0.03], placements=[AssetInstance() for _ in range(1)])
record_B = Assets(description="A vinyl record with a circular flat disc, glossy pastel pink label, retro 1950s diner style, thin and round", size=[0.01, 0.30, 0.30], placements=[AssetInstance() for _ in range(1)])
vasecabinet_B = Assets(description="A retro 1950s diner style vase with a squat cylindrical form, glossy pastel pink enamel and a thin chrome lip, set on the top of the second cabinet", size=[0.25, 0.25, 0.27], placements=[AssetInstance() for _ in range(1)])
artwork_A = Assets(description="A single piece of thin and upright artwork with a square canvas, pastel teal abstract pattern, retro 1950s diner style, framed in a slim white border", size=[0.04, 0.70, 0.70], placements=[AssetInstance() for _ in range(1)])
vasecabinet_C = Assets(description="A retro 1950s diner style vase with a squat cylindrical body, glossy pastel green enamel and a narrow chrome rim, placed on the top of the cabinet", size=[0.25, 0.25, 0.27], placements=[AssetInstance() for _ in range(1)])
posterwall_E = Assets(description="A single piece of thin and upright retro 1950s diner style poster with a rectangular paper surface, pastel pink background, vintage illustration and a glossy finish", size=[0.01, 0.61, 0.91], placements=[AssetInstance() for _ in range(1)])
signwall = Assets(description="A retro 1950s diner style wall sign with bold neon lettering, rectangular flat panel and bright chrome finish", size=[0.08, 1.20, 0.45], placements=[AssetInstance() for _ in range(1)])
pottedplantfloor_C = Assets(description="A retro 1950s diner style potted plant in a small ceramic pot, round pastel‑green glaze and compact leafy foliage", size=[0.32, 0.32, 0.50], placements=[AssetInstance() for _ in range(1)])
penworkbench_C = Assets(description="A retro 1950s diner style ballpoint pen, slender cylindrical shape, pastel plastic body and thin metal tip", size=[0.01, 0.14, 0.01], placements=[AssetInstance() for _ in range(1)])
workbench = Assets(description="A rectangular floral workbench retro 1950s diner style with chrome legs, a smooth white laminate top and a subtle pastel teal edge trim, the top has a gentle overhang for a classic diner feel", size=[0.75, 1.80, 0.90], placements=[AssetInstance() for _ in range(1)])
bookdesk_B = Assets(description="A retro 1950s diner style book with a rectangular soft‑cover, pastel pink hue and a narrow white stripe, one copy is open displaying pages, the other remains closed", size=[0.22, 0.28, 0.04], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="A tall rectangular chrome storage cabinet with sleek straight edges, a brushed metal finish and recessed handles, the doors are frameless for a minimalist look", size=[0.45, 0.90, 1.90], placements=[AssetInstance() for _ in range(1)])
storageboxcabinet = Assets(description="A rectangular storage box with a hinged lid, matte pastel purple finish, retro 1950s diner style, sturdy and compact, with a small metal handle", size=[0.32, 0.42, 0.22], placements=[AssetInstance() for _ in range(1)])
bookfloor_A = Assets(description="A retro 1950s diner style paperback book, rectangular, pastel cover, thin binding and slightly rounded corners", size=[0.15, 0.21, 0.03], placements=[AssetInstance() for _ in range(1)])
lightfixture_D = Assets(description="A single piece of thin and upright retro 1950s diner style wall light fixture with a rectangular chrome frame, pastel teal glass panels and a subtle frosted interior glow", size=[0.11, 0.22, 0.52], placements=[AssetInstance() for _ in range(1)])
stool_D = Assets(description="A compact vinyl stool with a curved saddle seat, chrome‑finished legs, and a pastel pink or teal finish, the seat is slightly rounded and the legs are splayed for stability", size=[0.42, 0.46, 0.68], placements=[AssetInstance() for _ in range(1)])
pottedplantfloor_D = Assets(description="A retro 1950s diner style potted plant in a small ceramic pot, round pastel‑green glaze and compact leafy foliage", size=[0.32, 0.32, 0.50], placements=[AssetInstance() for _ in range(1)])
toolcounter_B = Assets(description="A wooden flower‑arrangement tool with a slender elongated handle, polished walnut finish, retro 1950s diner style, featuring a small brass hook at the end", size=[0.04, 0.32, 0.04], placements=[AssetInstance() for _ in range(1)])
vasefloor_B = Assets(description="A retro 1950s diner style ceramic vase, squat cylindrical shape, pastel finish, slightly flared rim and thin decorative accent", size=[0.27, 0.27, 0.32], placements=[AssetInstance() for _ in range(1)])
notebookcounter = Assets(description="A retro 1950s diner style spiral‑bound notebook with a glossy pastel pink cover, rectangular shape and thin profile", size=[0.17, 0.23, 0.02], placements=[AssetInstance() for _ in range(1)])
vasecounter_B = Assets(description="A ceramic vase with a rounded bulbous shape, glossy pastel pink finish and subtle teal stripe, retro 1950s diner style, squat and decorative", size=[0.24, 0.24, 0.28], placements=[AssetInstance() for _ in range(1)])
vaseworkbench_B = Assets(description="A ceramic vase with a rounded bulbous shape, glossy pastel pink finish and subtle teal stripe, retro 1950s diner style, squat and decorative", size=[0.24, 0.24, 0.28], placements=[AssetInstance() for _ in range(1)])
pottedplantfloor_E = Assets(description="A retro 1950s diner style potted plant with a small round pot, pastel glaze, a compact green foliage clump and a short stem", size=[0.30, 0.30, 0.48], placements=[AssetInstance() for _ in range(1)])
notebookdesk_B = Assets(description="A retro 1950s diner style spiral notebook, rectangular, pastel cover, thin metal binding and rounded corners", size=[0.17, 0.23, 0.02], placements=[AssetInstance() for _ in range(1)])
vasecabinet_D = Assets(description="A small clear glass vase with a tapered neck and a rounded base, delicate thin walls and a subtle sparkle", size=[0.16, 0.16, 0.26], placements=[AssetInstance() for _ in range(1)])
artworkwall_A = Assets(description="A single piece of thin and upright retro 1950s diner style artwork with a rectangular canvas, pastel coral background, abstract geometric shapes and a subtle glossy coating", size=[0.03, 0.65, 0.85], placements=[AssetInstance() for _ in range(1)])
pendesk_B = Assets(description="A retro 1950s diner style pen with a slim cylindrical barrel, chrome tip and pastel handle; a second pen of the same style placed beside a small holder", size=[0.09, 0.20, 0.08], placements=[AssetInstance() for _ in range(1)])
record_C = Assets(description="A vinyl record with a circular flat disc, glossy pastel pink label, retro 1950s diner style, thin and round", size=[0.01, 0.30, 0.30], placements=[AssetInstance() for _ in range(1)])
vasefloor_C = Assets(description="A retro 1950s diner style vase with a slender cylindrical silhouette, glossy pastel lavender finish and a narrow chrome band near the top, placed on the floor near walls", size=[0.22, 0.22, 0.65], placements=[AssetInstance() for _ in range(1)])
lightfixturewall_C = Assets(description="A retro 1950s diner style wall‑mounted light fixture with a curved rectangular shade, pastel teal glass, chrome trim and a small exposed bulb", size=[0.16, 0.42, 0.22], placements=[AssetInstance() for _ in range(1)])
pottedplant_E = Assets(description="A retro 1950s diner style potted plant with a short cylindrical pot in pastel coral, containing a small leafy green sprout, the pot has a subtle chrome rim", size=[0.35, 0.35, 0.65], placements=[AssetInstance() for _ in range(1)])
penworkbench_D = Assets(description="A retro 1950s diner style ballpoint pen, slender cylindrical shape, pastel plastic body and thin metal tip", size=[0.01, 0.14, 0.01], placements=[AssetInstance() for _ in range(1)])
bookfloor_B = Assets(description="A retro 1950s diner style paperback book, rectangular, pastel cover, thin binding and slightly rounded corners", size=[0.15, 0.21, 0.03], placements=[AssetInstance() for _ in range(1)])
vasefloor_D = Assets(description="A retro 1950s diner style ceramic vase, squat cylindrical shape, pastel finish, slightly flared rim and thin decorative accent", size=[0.27, 0.27, 0.32], placements=[AssetInstance() for _ in range(1)])
artworkwall_B = Assets(description="A single piece of thin and upright retro 1950s diner style artwork with a rectangular canvas, pastel coral background, abstract geometric shapes and a subtle glossy coating", size=[0.03, 0.65, 0.85], placements=[AssetInstance() for _ in range(1)])
vasecabinet_E = Assets(description="A ceramic vase with a rounded bulbous shape, glossy pastel pink finish and subtle teal stripe, retro 1950s diner style, squat and decorative", size=[0.24, 0.24, 0.28], placements=[AssetInstance() for _ in range(1)])
vasefloor_E = Assets(description="A retro 1950s diner style vase with a slender cylindrical silhouette, glossy pastel lavender finish and a narrow chrome band near the top, placed on the floor near walls", size=[0.22, 0.22, 0.65], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="A single piece of thin and upright chrome shelf with a flat rectangular surface, sleek straight edges and a subtle reflective finish, the shelf is mounted flush to the wall", size=[0.28, 1.20, 0.05], placements=[AssetInstance() for _ in range(1)])
artwork_B = Assets(description="A single piece of thin and upright artwork with a square canvas, pastel teal abstract pattern, retro 1950s diner style, framed in a slim white border", size=[0.04, 0.70, 0.70], placements=[AssetInstance() for _ in range(1)])
counter = Assets(description="A rectangular glass-case counter retro 1950s diner style with chrome accents and pastel pink and teal detailing, featuring a sleek low‑profile glass top and chrome‑trimmed legs, the glass surface is slightly curved for a vintage look", size=[0.75, 2.20, 1.05], placements=[AssetInstance() for _ in range(1)])
pendesk_C = Assets(description="A retro 1950s diner style ballpoint pen with a slim cylindrical barrel, glossy pastel pink finish and a chrome tip, featuring a small engraved diner logo near the clip", size=[0.01, 0.14, 0.01], placements=[AssetInstance() for _ in range(1)])
plant_A = Assets(description="A cylindrical potted green plant with a glossy terracotta pot, the foliage is dense and vibrant, the pot features a subtle matte finish and a small drainage hole", size=[0.50, 0.50, 1.10], placements=[AssetInstance() for _ in range(1)])
pottedplant_F = Assets(description="A potted plant with a cylindrical pot, matte pastel teal finish, green foliage, retro 1950s diner style, squat and rounded", size=[0.40, 0.40, 0.70], placements=[AssetInstance() for _ in range(1)])
mirror_A = Assets(description="A wall mirror with a rectangular frame, chrome edging, pastel mint finish, retro 1950s diner style, thin and upright", size=[0.04, 0.65, 1.20], placements=[AssetInstance() for _ in range(1)])
toolworkbench = Assets(description="A retro 1950s diner style hand tool with a polished steel head and a short wooden handle, compact rectangular silhouette", size=[0.10, 0.28, 0.06], placements=[AssetInstance() for _ in range(1)])
sign_B = Assets(description="A single piece of thin and upright neon sign with pastel pink lettering on a teal background, the sign glows softly and has a curved top edge for a retro vibe", size=[0.08, 1.10, 0.55], placements=[AssetInstance() for _ in range(1)])
flowerarrangementcounter = Assets(description="A retro 1950s diner style floral arrangement in a small glass vase, pastel blossoms spilling over a rounded container", size=[0.40, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
flowerarrangementfloor_A = Assets(description="A retro 1950s diner style decorative flower arrangement in a low glass vase, bright mixed‑color blossoms", size=[0.55, 0.65, 0.50], placements=[AssetInstance() for _ in range(1)])
pottedplantfloor_F = Assets(description="A retro 1950s diner style potted plant with a small round pot, pastel glaze, a compact green foliage clump and a short stem", size=[0.30, 0.30, 0.48], placements=[AssetInstance() for _ in range(1)])
flowerarrangementfloor_B = Assets(description="A retro 1950s diner style decorative flower arrangement in a low glass vase, bright mixed‑color blossoms", size=[0.55, 0.65, 0.50], placements=[AssetInstance() for _ in range(1)])
poster_A = Assets(description="A thin upright vintage advertising poster with a rectangular shape, bold pastel pink and teal graphics, a slightly textured paper finish and a faded retro logo", size=[0.01, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
plant_B = Assets(description="A cylindrical potted green plant with a glossy terracotta pot, the foliage is dense and vibrant, the pot features a subtle matte finish and a small drainage hole", size=[0.50, 0.50, 1.10], placements=[AssetInstance() for _ in range(1)])
bookcabinet_C = Assets(description="A retro 1950s diner style paperback book, rectangular, pastel cover, thin binding and rounded corners", size=[0.15, 0.21, 0.03], placements=[AssetInstance() for _ in range(1)])
record_D = Assets(description="A vinyl record with a circular flat disc, glossy pastel pink label, retro 1950s diner style, thin and round", size=[0.01, 0.30, 0.30], placements=[AssetInstance() for _ in range(1)])
chair = Assets(description="A swivel office chair with a rounded padded seat, a chrome base and a single black leather swivel mechanism, the backrest is slightly reclined for comfort", size=[0.65, 0.65, 0.95], placements=[AssetInstance() for _ in range(1)])
desk = Assets(description="A rectangular retro 1950s diner style back‑office desk with chrome trim, a pastel pink top and teal accents, the desk features a low profile and rounded front edge", size=[0.75, 1.50, 0.76], placements=[AssetInstance() for _ in range(1)])
board = Assets(description="A single piece of thin and upright menu board with a rectangular shape, pastel teal background and chrome edging, the board features a smooth matte finish for easy reading", size=[0.04, 1.10, 0.75], placements=[AssetInstance() for _ in range(1)])
pencounter = Assets(description="A retro 1950s diner style metal ballpoint pen with a chrome barrel, red tip and a sleek cylindrical shape", size=[0.01, 0.14, 0.01], placements=[AssetInstance() for _ in range(1)])
bookfloor_C = Assets(description="A retro 1950s diner style paperback book, rectangular, pastel cover, thin binding and slightly rounded corners", size=[0.15, 0.21, 0.03], placements=[AssetInstance() for _ in range(1)])
vasefloor_F = Assets(description="A retro 1950s diner style vase with a slender cylindrical silhouette, glossy pastel lavender finish and a narrow chrome band near the top, placed on the floor near walls", size=[0.22, 0.22, 0.65], placements=[AssetInstance() for _ in range(1)])
vasecabinet_F = Assets(description="A small clear glass vase with a tapered neck and a rounded base, delicate thin walls and a subtle sparkle", size=[0.16, 0.16, 0.26], placements=[AssetInstance() for _ in range(1)])
mirror_B = Assets(description="A single piece of thin and upright chrome‑trimmed mirror with a rectangular shape, a sleek reflective surface and a narrow chrome frame, the mirror is slightly beveled at the edges", size=[0.04, 0.70, 1.30], placements=[AssetInstance() for _ in range(1)])
vaseworkbench_C = Assets(description="A ceramic vase with a rounded bulbous shape, glossy pastel pink finish and subtle teal stripe, retro 1950s diner style, squat and decorative", size=[0.24, 0.24, 0.28], placements=[AssetInstance() for _ in range(1)])
poster_B = Assets(description="A thin upright vintage advertising poster with a rectangular shape, bold pastel pink and teal graphics, a slightly textured paper finish and a faded retro logo", size=[0.01, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])

posterwall_A[0].instance_id = 'posterwall_A_0'
penworkbench_A[0].instance_id = 'penworkbench_A_0'
posterwall_B[0].instance_id = 'posterwall_B_0'
pottedplant_A[0].instance_id = 'pottedplant_A_0'
penworkbench_B[0].instance_id = 'penworkbench_B_0'
jukebox[0].instance_id = 'jukebox_0'
picture_A[0].instance_id = 'picture_A_0'
lightfixture_A[0].instance_id = 'lightfixture_A_0'
bookdesk_A[0].instance_id = 'bookdesk_A_0'
bookcabinet_A[0].instance_id = 'bookcabinet_A_0'
pottedplant_B[0].instance_id = 'pottedplant_B_0'
stool_A[0].instance_id = 'stool_A_0'
pendesk_A[0].instance_id = 'pendesk_A_0'
vaseworkbench_A[0].instance_id = 'vaseworkbench_A_0'
vasecounter_A[0].instance_id = 'vasecounter_A_0'
vasecabinet_A[0].instance_id = 'vasecabinet_A_0'
cabinet_A[0].instance_id = 'cabinet_A_0'
shelf_A[0].instance_id = 'shelf_A_0'
pottedplant_C[0].instance_id = 'pottedplant_C_0'
notebookdesk_A[0].instance_id = 'notebookdesk_A_0'
pottedplantfloor_A[0].instance_id = 'pottedplantfloor_A_0'
clock[0].instance_id = 'clock_0'
lightfixturewall_A[0].instance_id = 'lightfixturewall_A_0'
vasefloor_A[0].instance_id = 'vasefloor_A_0'
lightfixturewall_B[0].instance_id = 'lightfixturewall_B_0'
stool_B[0].instance_id = 'stool_B_0'
stool_C[0].instance_id = 'stool_C_0'
lightfixture_B[0].instance_id = 'lightfixture_B_0'
pottedplantfloor_B[0].instance_id = 'pottedplantfloor_B_0'
pottedplant_D[0].instance_id = 'pottedplant_D_0'
posterwall_C[0].instance_id = 'posterwall_C_0'
lightfixture_C[0].instance_id = 'lightfixture_C_0'
record_A[0].instance_id = 'record_A_0'
picture_B[0].instance_id = 'picture_B_0'
sign_A[0].instance_id = 'sign_A_0'
toolcounter_A[0].instance_id = 'toolcounter_A_0'
posterwall_D[0].instance_id = 'posterwall_D_0'
bookcabinet_B[0].instance_id = 'bookcabinet_B_0'
record_B[0].instance_id = 'record_B_0'
vasecabinet_B[0].instance_id = 'vasecabinet_B_0'
artwork_A[0].instance_id = 'artwork_A_0'
vasecabinet_C[0].instance_id = 'vasecabinet_C_0'
posterwall_E[0].instance_id = 'posterwall_E_0'
signwall[0].instance_id = 'signwall_0'
pottedplantfloor_C[0].instance_id = 'pottedplantfloor_C_0'
penworkbench_C[0].instance_id = 'penworkbench_C_0'
workbench[0].instance_id = 'workbench_0'
bookdesk_B[0].instance_id = 'bookdesk_B_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
storageboxcabinet[0].instance_id = 'storageboxcabinet_0'
bookfloor_A[0].instance_id = 'bookfloor_A_0'
lightfixture_D[0].instance_id = 'lightfixture_D_0'
stool_D[0].instance_id = 'stool_D_0'
pottedplantfloor_D[0].instance_id = 'pottedplantfloor_D_0'
toolcounter_B[0].instance_id = 'toolcounter_B_0'
vasefloor_B[0].instance_id = 'vasefloor_B_0'
notebookcounter[0].instance_id = 'notebookcounter_0'
vasecounter_B[0].instance_id = 'vasecounter_B_0'
vaseworkbench_B[0].instance_id = 'vaseworkbench_B_0'
pottedplantfloor_E[0].instance_id = 'pottedplantfloor_E_0'
notebookdesk_B[0].instance_id = 'notebookdesk_B_0'
vasecabinet_D[0].instance_id = 'vasecabinet_D_0'
artworkwall_A[0].instance_id = 'artworkwall_A_0'
pendesk_B[0].instance_id = 'pendesk_B_0'
record_C[0].instance_id = 'record_C_0'
vasefloor_C[0].instance_id = 'vasefloor_C_0'
lightfixturewall_C[0].instance_id = 'lightfixturewall_C_0'
pottedplant_E[0].instance_id = 'pottedplant_E_0'
penworkbench_D[0].instance_id = 'penworkbench_D_0'
bookfloor_B[0].instance_id = 'bookfloor_B_0'
vasefloor_D[0].instance_id = 'vasefloor_D_0'
artworkwall_B[0].instance_id = 'artworkwall_B_0'
vasecabinet_E[0].instance_id = 'vasecabinet_E_0'
vasefloor_E[0].instance_id = 'vasefloor_E_0'
shelf_B[0].instance_id = 'shelf_B_0'
artwork_B[0].instance_id = 'artwork_B_0'
counter[0].instance_id = 'counter_0'
pendesk_C[0].instance_id = 'pendesk_C_0'
plant_A[0].instance_id = 'plant_A_0'
pottedplant_F[0].instance_id = 'pottedplant_F_0'
mirror_A[0].instance_id = 'mirror_A_0'
toolworkbench[0].instance_id = 'toolworkbench_0'
sign_B[0].instance_id = 'sign_B_0'
flowerarrangementcounter[0].instance_id = 'flowerarrangementcounter_0'
flowerarrangementfloor_A[0].instance_id = 'flowerarrangementfloor_A_0'
pottedplantfloor_F[0].instance_id = 'pottedplantfloor_F_0'
flowerarrangementfloor_B[0].instance_id = 'flowerarrangementfloor_B_0'
poster_A[0].instance_id = 'poster_A_0'
plant_B[0].instance_id = 'plant_B_0'
bookcabinet_C[0].instance_id = 'bookcabinet_C_0'
record_D[0].instance_id = 'record_D_0'
chair[0].instance_id = 'chair_0'
desk[0].instance_id = 'desk_0'
board[0].instance_id = 'board_0'
pencounter[0].instance_id = 'pencounter_0'
bookfloor_C[0].instance_id = 'bookfloor_C_0'
vasefloor_F[0].instance_id = 'vasefloor_F_0'
vasecabinet_F[0].instance_id = 'vasecabinet_F_0'
mirror_B[0].instance_id = 'mirror_B_0'
vaseworkbench_C[0].instance_id = 'vaseworkbench_C_0'
poster_B[0].instance_id = 'poster_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

posterwall_A[0].position = [0.12106337424236524, 0.24325418015868738, 0.455]
posterwall_A[0].rotation = [0, 0, 0]
penworkbench_A[0].position = [3.493831883491515, 3.2444652994648724, 0.005]
penworkbench_A[0].rotation = [0, 0, 0]
posterwall_B[0].position = [1.2589261309585862, 2.7516088475551728, 0.38]
posterwall_B[0].rotation = [0, 0, 0]
pottedplant_A[0].position = [1.2170206467673323, 1.5899188742070525, 0.325]
pottedplant_A[0].rotation = [0, 0, 0]
penworkbench_B[0].position = [0.753364455864961, 4.760936232384822, 0.005]
penworkbench_B[0].rotation = [0, 0, 0]
jukebox[0].position = [3.3306239462996268, 3.8592830773073885, 0.725]
jukebox[0].rotation = [0, 0, 0]
picture_A[0].position = [3.492369270258667, 1.882007819915924, 0.45]
picture_A[0].rotation = [0, 0, 0]
lightfixture_A[0].position = [4.698372024764323, 3.1009003457371116, 0.25]
lightfixture_A[0].rotation = [0, 0, 0]
bookdesk_A[0].position = [4.787163873035746, 0.8967687251713274, 0.015]
bookdesk_A[0].rotation = [0, 0, 0]
bookcabinet_A[0].position = [4.999137340684554, 0.895875087368318, 0.015]
bookcabinet_A[0].rotation = [0, 0, 0]
pottedplant_B[0].position = [4.332762560327214, 0.4540259225342008, 0.35]
pottedplant_B[0].rotation = [0, 0, 0]
stool_A[0].position = [1.278610312627832, 4.1429683046431816, 0.34]
stool_A[0].rotation = [0, 0, 0]
pendesk_A[0].position = [5.423715240649676, 1.308950638447333, 0.04]
pendesk_A[0].rotation = [0, 0, 0]
vaseworkbench_A[0].position = [3.377202413168165, 0.6866834778070235, 0.14]
vaseworkbench_A[0].rotation = [0, 0, 0]
vasecounter_A[0].position = [3.7792197390560425, 1.79986194825628, 0.14]
vasecounter_A[0].rotation = [0, 0, 0]
vasecabinet_A[0].position = [4.490366306373905, 1.2393481086337417, 0.14]
vasecabinet_A[0].rotation = [0, 0, 0]
cabinet_A[0].position = [4.791383451072958, 3.1695984057401123, 0.95]
cabinet_A[0].rotation = [0, 0, 0]
shelf_A[0].position = [1.791511770506023, 2.489609014085622, 0.025]
shelf_A[0].rotation = [0, 0, 0]
pottedplant_C[0].position = [4.1952172829545535, 2.2690595699183387, 0.325]
pottedplant_C[0].rotation = [0, 0, 0]
notebookdesk_A[0].position = [5.405622824626425, 2.165664400578053, 0.01]
notebookdesk_A[0].rotation = [0, 0, 0]
pottedplantfloor_A[0].position = [4.909984194241445, 0.8371949766405462, 0.25]
pottedplantfloor_A[0].rotation = [0, 0, 0]
clock[0].position = [1.8318484911247457, 4.9747632158010555, 0.2]
clock[0].rotation = [0, 0, 0]
lightfixturewall_A[0].position = [5.856691302554655, 4.914915161670015, 0.11]
lightfixturewall_A[0].rotation = [0, 0, 0]
vasefloor_A[0].position = [1.378555302689282, 4.877350286252567, 0.16]
vasefloor_A[0].rotation = [0, 0, 0]
lightfixturewall_B[0].position = [2.1073707319142367, 0.46215173385538155, 0.11]
lightfixturewall_B[0].rotation = [0, 0, 0]
stool_B[0].position = [1.6476673953997454, 0.082168762777724, 0.34]
stool_B[0].rotation = [0, 0, 0]
stool_C[0].position = [1.996130228755684, 2.865519400690844, 0.34]
stool_C[0].rotation = [0, 0, 0]
lightfixture_B[0].position = [3.318920802956537, 1.8700614124253467, 0.26]
lightfixture_B[0].rotation = [0, 0, 0]
pottedplantfloor_B[0].position = [5.935037258954763, 0.9988922263015965, 0.24]
pottedplantfloor_B[0].rotation = [0, 0, 0]
pottedplant_D[0].position = [4.816340209387743, 0.21071407505106055, 0.325]
pottedplant_D[0].rotation = [0, 0, 0]
posterwall_C[0].position = [0.23584579496176206, 3.3863024791779006, 0.38]
posterwall_C[0].rotation = [0, 0, 0]
lightfixture_C[0].position = [3.8648876281653486, 0.8661587658367015, 0.25]
lightfixture_C[0].rotation = [0, 0, 0]
record_A[0].position = [0.32624952687881414, 4.850876446953495, 0.15]
record_A[0].rotation = [0, 0, 0]
picture_B[0].position = [2.031135621453797, 3.497124327101152, 0.45]
picture_B[0].rotation = [0, 0, 0]
sign_A[0].position = [0.08038328006437911, 1.3694887689323276, 0.175]
sign_A[0].rotation = [0, 0, 0]
toolcounter_A[0].position = [3.555738469154303, 4.820261041982313, 0.02]
toolcounter_A[0].rotation = [0, 0, 0]
posterwall_D[0].position = [5.009334577566377, 3.795349669608479, 0.455]
posterwall_D[0].rotation = [0, 0, 0]
bookcabinet_B[0].position = [4.36130969967716, 4.922530613023598, 0.015]
bookcabinet_B[0].rotation = [0, 0, 0]
record_B[0].position = [0.9174697727285717, 1.6705880214359352, 0.15]
record_B[0].rotation = [0, 0, 0]
vasecabinet_B[0].position = [1.9640934455461185, 0.7050400376426313, 0.135]
vasecabinet_B[0].rotation = [0, 0, 0]
artwork_A[0].position = [2.3180544223751554, 3.0842692381377197, 0.35]
artwork_A[0].rotation = [0, 0, 0]
vasecabinet_C[0].position = [0.029996555509923528, 4.752868885677756, 0.135]
vasecabinet_C[0].rotation = [0, 0, 0]
posterwall_E[0].position = [5.5723899251294124, 1.6772660941197666, 0.455]
posterwall_E[0].rotation = [0, 0, 0]
signwall[0].position = [1.178517371137765, 2.1387874962578874, 0.225]
signwall[0].rotation = [0, 0, 0]
pottedplantfloor_C[0].position = [1.197831587411212, 1.0247620282459597, 0.25]
pottedplantfloor_C[0].rotation = [0, 0, 0]
penworkbench_C[0].position = [0.8678540693514432, 3.475163486679769, 0.005]
penworkbench_C[0].rotation = [0, 0, 0]
workbench[0].position = [4.487873749674127, 4.411583105035953, 0.45]
workbench[0].rotation = [0, 0, 0]
bookdesk_B[0].position = [5.019731071276977, 0.7403204223522697, 0.02]
bookdesk_B[0].rotation = [0, 0, 0]
cabinet_B[0].position = [3.626824398754506, 0.561935516978177, 0.95]
cabinet_B[0].rotation = [0, 0, 0]
storageboxcabinet[0].position = [0.42435064539789136, 4.110658743746485, 0.11]
storageboxcabinet[0].rotation = [0, 0, 0]
bookfloor_A[0].position = [0.09254575602706039, 3.233559939547251, 0.015]
bookfloor_A[0].rotation = [0, 0, 0]
lightfixture_D[0].position = [2.4296299062853475, 0.9638843567441885, 0.26]
lightfixture_D[0].rotation = [0, 0, 0]
stool_D[0].position = [3.392386620432573, 2.9232332103420093, 0.34]
stool_D[0].rotation = [0, 0, 0]
pottedplantfloor_D[0].position = [1.957994615048564, 0.11049630041518488, 0.25]
pottedplantfloor_D[0].rotation = [0, 0, 0]
toolcounter_B[0].position = [5.406465660949949, 2.424164884453588, 0.02]
toolcounter_B[0].rotation = [0, 0, 0]
vasefloor_B[0].position = [0.9668926433056284, 1.6169256617253747, 0.16]
vasefloor_B[0].rotation = [0, 0, 0]
notebookcounter[0].position = [3.332680781764352, 0.12565247917143807, 0.01]
notebookcounter[0].rotation = [0, 0, 0]
vasecounter_B[0].position = [4.797493209315415, 3.404382590632165, 0.14]
vasecounter_B[0].rotation = [0, 0, 0]
vaseworkbench_B[0].position = [4.501019255609653, 4.010737120702245, 0.14]
vaseworkbench_B[0].rotation = [0, 0, 0]
pottedplantfloor_E[0].position = [0.8805159107180474, 4.062647756264185, 0.24]
pottedplantfloor_E[0].rotation = [0, 0, 0]
notebookdesk_B[0].position = [5.4232534713022575, 1.7571115433297964, 0.01]
notebookdesk_B[0].rotation = [0, 0, 0]
vasecabinet_D[0].position = [4.322135083529512, 2.9298262063432547, 0.13]
vasecabinet_D[0].rotation = [0, 0, 0]
artworkwall_A[0].position = [2.33331165952739, 0.5872246624317018, 0.425]
artworkwall_A[0].rotation = [0, 0, 0]
pendesk_B[0].position = [3.8216047151171884, 0.5889431208566204, 0.04]
pendesk_B[0].rotation = [0, 0, 0]
record_C[0].position = [1.5592374069747226, 2.5203761539801928, 0.15]
record_C[0].rotation = [0, 0, 0]
vasefloor_C[0].position = [5.103364527813399, 4.973174921589496, 0.325]
vasefloor_C[0].rotation = [0, 0, 0]
lightfixturewall_C[0].position = [1.7565651439686765, 1.8642187284873106, 0.11]
lightfixturewall_C[0].rotation = [0, 0, 0]
pottedplant_E[0].position = [2.0892041410438393, 1.6473223260663883, 0.325]
pottedplant_E[0].rotation = [0, 0, 0]
penworkbench_D[0].position = [4.841427888503649, 1.716551231407314, 0.005]
penworkbench_D[0].rotation = [0, 0, 0]
bookfloor_B[0].position = [1.4758543663841972, 2.696562928065994, 0.015]
bookfloor_B[0].rotation = [0, 0, 0]
vasefloor_D[0].position = [1.419991567211622, 2.3277240890299433, 0.16]
vasefloor_D[0].rotation = [0, 0, 0]
artworkwall_B[0].position = [2.2800866868197325, 4.446846298671901, 0.425]
artworkwall_B[0].rotation = [0, 0, 0]
vasecabinet_E[0].position = [5.562635640521073, 0.3397214884639682, 0.14]
vasecabinet_E[0].rotation = [0, 0, 0]
vasefloor_E[0].position = [2.943823903754943, 2.726487342353312, 0.325]
vasefloor_E[0].rotation = [0, 0, 0]
shelf_B[0].position = [2.189595681199429, 3.5049781046171797, 0.025]
shelf_B[0].rotation = [0, 0, 0]
artwork_B[0].position = [3.735770305320774, 4.120202162759041, 0.35]
artwork_B[0].rotation = [0, 0, 0]
counter[0].position = [2.1561052005885823, 1.1836646552726238, 0.525]
counter[0].rotation = [0, 0, 0]
pendesk_C[0].position = [1.1392046334468866, 2.228778482964271, 0.005]
pendesk_C[0].rotation = [0, 0, 0]
plant_A[0].position = [4.668340082235334, 2.4879589283027497, 0.55]
plant_A[0].rotation = [0, 0, 0]
pottedplant_F[0].position = [3.984381799521665, 3.4559955604970103, 0.35]
pottedplant_F[0].rotation = [0, 0, 0]
mirror_A[0].position = [2.655296991507438, 0.9612828263295919, 0.6]
mirror_A[0].rotation = [0, 0, 0]
toolworkbench[0].position = [0.9641802134840634, 0.7533733507008966, 0.03]
toolworkbench[0].rotation = [0, 0, 0]
sign_B[0].position = [1.4368958757231542, 2.8502936473957714, 0.275]
sign_B[0].rotation = [0, 0, 0]
flowerarrangementcounter[0].position = [1.2811544869288176, 0.2081183214261917, 0.275]
flowerarrangementcounter[0].rotation = [0, 0, 0]
flowerarrangementfloor_A[0].position = [1.600617795301115, 4.093088655118701, 0.25]
flowerarrangementfloor_A[0].rotation = [0, 0, 0]
pottedplantfloor_F[0].position = [0.1430728150103282, 0.9787151640751812, 0.24]
pottedplantfloor_F[0].rotation = [0, 0, 0]
flowerarrangementfloor_B[0].position = [5.905257630118005, 2.368870775614816, 0.25]
flowerarrangementfloor_B[0].rotation = [0, 0, 0]
poster_A[0].position = [4.135775078296766, 1.3352732352722907, 0.45]
poster_A[0].rotation = [0, 0, 0]
plant_B[0].position = [2.953830203277436, 3.772754644883916, 0.55]
plant_B[0].rotation = [0, 0, 0]
bookcabinet_C[0].position = [5.4733786286678, 2.6327825552118274, 0.015]
bookcabinet_C[0].rotation = [0, 0, 0]
record_D[0].position = [2.736568295001821, 1.9392625904256593, 0.15]
record_D[0].rotation = [0, 0, 0]
chair[0].position = [5.686074389466954, 0.38873676732736895, 0.475]
chair[0].rotation = [0, 0, 0]
desk[0].position = [3.43536898974019, 0.5634212081899592, 0.38]
desk[0].rotation = [0, 0, 0]
board[0].position = [0.7177050651549777, 0.6711083227667092, 0.375]
board[0].rotation = [0, 0, 0]
pencounter[0].position = [0.4318700046937729, 1.6748588457725093, 0.005]
pencounter[0].rotation = [0, 0, 0]
bookfloor_C[0].position = [3.678277108635202, 1.4980520487341158, 0.015]
bookfloor_C[0].rotation = [0, 0, 0]
vasefloor_F[0].position = [1.3140211915353204, 2.1567704890088955, 0.325]
vasefloor_F[0].rotation = [0, 0, 0]
vasecabinet_F[0].position = [3.1324373017495573, 0.8563749373786017, 0.13]
vasecabinet_F[0].rotation = [0, 0, 0]
mirror_B[0].position = [1.9264111727524855, 1.6973665505827022, 0.65]
mirror_B[0].rotation = [0, 0, 0]
vaseworkbench_C[0].position = [2.8752709599977253, 1.3120594582550815, 0.14]
vaseworkbench_C[0].rotation = [0, 0, 0]
poster_B[0].position = [1.758051112147123, 4.253884437589678, 0.45]
poster_B[0].rotation = [0, 0, 0]
posterwall_A[0].position = [0.12106337424236524, 0.24325418015868738, 0.455]
posterwall_A[0].rotation = [0, 0, 0]
penworkbench_A[0].position = [3.493831883491515, 3.2444652994648724, 0.005]
penworkbench_A[0].rotation = [0, 0, 0]
posterwall_B[0].position = [1.2589261309585862, 2.7516088475551728, 0.38]
posterwall_B[0].rotation = [0, 0, 0]
pottedplant_A[0].position = [1.2170206467673323, 1.5899188742070525, 0.325]
pottedplant_A[0].rotation = [0, 0, 0]
penworkbench_B[0].position = [0.753364455864961, 4.760936232384822, 0.005]
penworkbench_B[0].rotation = [0, 0, 0]
jukebox[0].position = [3.3306239462996268, 3.8592830773073885, 0.725]
jukebox[0].rotation = [0, 0, 0]
picture_A[0].position = [3.492369270258667, 1.882007819915924, 0.45]
picture_A[0].rotation = [0, 0, 0]
lightfixture_A[0].position = [4.698372024764323, 3.1009003457371116, 0.25]
lightfixture_A[0].rotation = [0, 0, 0]
bookdesk_A[0].position = [4.787163873035746, 0.8967687251713274, 0.015]
bookdesk_A[0].rotation = [0, 0, 0]
bookcabinet_A[0].position = [4.999137340684554, 0.895875087368318, 0.015]
bookcabinet_A[0].rotation = [0, 0, 0]
pottedplant_B[0].position = [4.332762560327214, 0.4540259225342008, 0.35]
pottedplant_B[0].rotation = [0, 0, 0]
stool_A[0].position = [1.278610312627832, 4.1429683046431816, 0.34]
stool_A[0].rotation = [0, 0, 0]
pendesk_A[0].position = [5.423715240649676, 1.308950638447333, 0.04]
pendesk_A[0].rotation = [0, 0, 0]
vaseworkbench_A[0].position = [3.377202413168165, 0.6866834778070235, 0.14]
vaseworkbench_A[0].rotation = [0, 0, 0]
vasecounter_A[0].position = [3.7792197390560425, 1.79986194825628, 0.14]
vasecounter_A[0].rotation = [0, 0, 0]
vasecabinet_A[0].position = [4.490366306373905, 1.2393481086337417, 0.14]
vasecabinet_A[0].rotation = [0, 0, 0]
cabinet_A[0].position = [4.791383451072958, 3.1695984057401123, 0.95]
cabinet_A[0].rotation = [0, 0, 0]
shelf_A[0].position = [1.791511770506023, 2.489609014085622, 0.025]
shelf_A[0].rotation = [0, 0, 0]
pottedplant_C[0].position = [4.1952172829545535, 2.2690595699183387, 0.325]
pottedplant_C[0].rotation = [0, 0, 0]
notebookdesk_A[0].position = [5.405622824626425, 2.165664400578053, 0.01]
notebookdesk_A[0].rotation = [0, 0, 0]
pottedplantfloor_A[0].position = [4.909984194241445, 0.8371949766405462, 0.25]
pottedplantfloor_A[0].rotation = [0, 0, 0]
clock[0].position = [1.8318484911247457, 4.9747632158010555, 0.2]
clock[0].rotation = [0, 0, 0]
lightfixturewall_A[0].position = [5.856691302554655, 4.914915161670015, 0.11]
lightfixturewall_A[0].rotation = [0, 0, 0]
vasefloor_A[0].position = [1.378555302689282, 4.877350286252567, 0.16]
vasefloor_A[0].rotation = [0, 0, 0]
lightfixturewall_B[0].position = [2.1073707319142367, 0.46215173385538155, 0.11]
lightfixturewall_B[0].rotation = [0, 0, 0]
stool_B[0].position = [1.6476673953997454, 0.082168762777724, 0.34]
stool_B[0].rotation = [0, 0, 0]
stool_C[0].position = [1.996130228755684, 2.865519400690844, 0.34]
stool_C[0].rotation = [0, 0, 0]
lightfixture_B[0].position = [3.318920802956537, 1.8700614124253467, 0.26]
lightfixture_B[0].rotation = [0, 0, 0]
pottedplantfloor_B[0].position = [5.935037258954763, 0.9988922263015965, 0.24]
pottedplantfloor_B[0].rotation = [0, 0, 0]
pottedplant_D[0].position = [4.816340209387743, 0.21071407505106055, 0.325]
pottedplant_D[0].rotation = [0, 0, 0]
posterwall_C[0].position = [0.23584579496176206, 3.3863024791779006, 0.38]
posterwall_C[0].rotation = [0, 0, 0]
lightfixture_C[0].position = [3.8648876281653486, 0.8661587658367015, 0.25]
lightfixture_C[0].rotation = [0, 0, 0]
record_A[0].position = [0.32624952687881414, 4.850876446953495, 0.15]
record_A[0].rotation = [0, 0, 0]
picture_B[0].position = [2.031135621453797, 3.497124327101152, 0.45]
picture_B[0].rotation = [0, 0, 0]
sign_A[0].position = [0.08038328006437911, 1.3694887689323276, 0.175]
sign_A[0].rotation = [0, 0, 0]
toolcounter_A[0].position = [3.555738469154303, 4.820261041982313, 0.02]
toolcounter_A[0].rotation = [0, 0, 0]
posterwall_D[0].position = [5.009334577566377, 3.795349669608479, 0.455]
posterwall_D[0].rotation = [0, 0, 0]
bookcabinet_B[0].position = [4.36130969967716, 4.922530613023598, 0.015]
bookcabinet_B[0].rotation = [0, 0, 0]
record_B[0].position = [0.9174697727285717, 1.6705880214359352, 0.15]
record_B[0].rotation = [0, 0, 0]
vasecabinet_B[0].position = [1.9640934455461185, 0.7050400376426313, 0.135]
vasecabinet_B[0].rotation = [0, 0, 0]
artwork_A[0].position = [2.3180544223751554, 3.0842692381377197, 0.35]
artwork_A[0].rotation = [0, 0, 0]
vasecabinet_C[0].position = [0.029996555509923528, 4.752868885677756, 0.135]
vasecabinet_C[0].rotation = [0, 0, 0]
posterwall_E[0].position = [5.5723899251294124, 1.6772660941197666, 0.455]
posterwall_E[0].rotation = [0, 0, 0]
signwall[0].position = [1.178517371137765, 2.1387874962578874, 0.225]
signwall[0].rotation = [0, 0, 0]
pottedplantfloor_C[0].position = [1.197831587411212, 1.0247620282459597, 0.25]
pottedplantfloor_C[0].rotation = [0, 0, 0]
penworkbench_C[0].position = [0.8678540693514432, 3.475163486679769, 0.005]
penworkbench_C[0].rotation = [0, 0, 0]
workbench[0].position = [4.487873749674127, 4.411583105035953, 0.45]
workbench[0].rotation = [0, 0, 0]
bookdesk_B[0].position = [5.019731071276977, 0.7403204223522697, 0.02]
bookdesk_B[0].rotation = [0, 0, 0]
cabinet_B[0].position = [3.626824398754506, 0.561935516978177, 0.95]
cabinet_B[0].rotation = [0, 0, 0]
storageboxcabinet[0].position = [0.42435064539789136, 4.110658743746485, 0.11]
storageboxcabinet[0].rotation = [0, 0, 0]
bookfloor_A[0].position = [0.09254575602706039, 3.233559939547251, 0.015]
bookfloor_A[0].rotation = [0, 0, 0]
lightfixture_D[0].position = [2.4296299062853475, 0.9638843567441885, 0.26]
lightfixture_D[0].rotation = [0, 0, 0]
stool_D[0].position = [3.392386620432573, 2.9232332103420093, 0.34]
stool_D[0].rotation = [0, 0, 0]
pottedplantfloor_D[0].position = [1.957994615048564, 0.11049630041518488, 0.25]
pottedplantfloor_D[0].rotation = [0, 0, 0]
toolcounter_B[0].position = [5.406465660949949, 2.424164884453588, 0.02]
toolcounter_B[0].rotation = [0, 0, 0]
vasefloor_B[0].position = [0.9668926433056284, 1.6169256617253747, 0.16]
vasefloor_B[0].rotation = [0, 0, 0]
notebookcounter[0].position = [3.332680781764352, 0.12565247917143807, 0.01]
notebookcounter[0].rotation = [0, 0, 0]
vasecounter_B[0].position = [4.797493209315415, 3.404382590632165, 0.14]
vasecounter_B[0].rotation = [0, 0, 0]
vaseworkbench_B[0].position = [4.501019255609653, 4.010737120702245, 0.14]
vaseworkbench_B[0].rotation = [0, 0, 0]
pottedplantfloor_E[0].position = [0.8805159107180474, 4.062647756264185, 0.24]
pottedplantfloor_E[0].rotation = [0, 0, 0]
notebookdesk_B[0].position = [5.4232534713022575, 1.7571115433297964, 0.01]
notebookdesk_B[0].rotation = [0, 0, 0]
vasecabinet_D[0].position = [4.322135083529512, 2.9298262063432547, 0.13]
vasecabinet_D[0].rotation = [0, 0, 0]
artworkwall_A[0].position = [2.33331165952739, 0.5872246624317018, 0.425]
artworkwall_A[0].rotation = [0, 0, 0]
pendesk_B[0].position = [3.8216047151171884, 0.5889431208566204, 0.04]
pendesk_B[0].rotation = [0, 0, 0]
record_C[0].position = [1.5592374069747226, 2.5203761539801928, 0.15]
record_C[0].rotation = [0, 0, 0]
vasefloor_C[0].position = [5.103364527813399, 4.973174921589496, 0.325]
vasefloor_C[0].rotation = [0, 0, 0]
lightfixturewall_C[0].position = [1.7565651439686765, 1.8642187284873106, 0.11]
lightfixturewall_C[0].rotation = [0, 0, 0]
pottedplant_E[0].position = [2.0892041410438393, 1.6473223260663883, 0.325]
pottedplant_E[0].rotation = [0, 0, 0]
penworkbench_D[0].position = [4.841427888503649, 1.716551231407314, 0.005]
penworkbench_D[0].rotation = [0, 0, 0]
bookfloor_B[0].position = [1.4758543663841972, 2.696562928065994, 0.015]
bookfloor_B[0].rotation = [0, 0, 0]
vasefloor_D[0].position = [1.419991567211622, 2.3277240890299433, 0.16]
vasefloor_D[0].rotation = [0, 0, 0]
artworkwall_B[0].position = [2.2800866868197325, 4.446846298671901, 0.425]
artworkwall_B[0].rotation = [0, 0, 0]
vasecabinet_E[0].position = [5.562635640521073, 0.3397214884639682, 0.14]
vasecabinet_E[0].rotation = [0, 0, 0]
vasefloor_E[0].position = [2.943823903754943, 2.726487342353312, 0.325]
vasefloor_E[0].rotation = [0, 0, 0]
shelf_B[0].position = [2.189595681199429, 3.5049781046171797, 0.025]
shelf_B[0].rotation = [0, 0, 0]
artwork_B[0].position = [3.735770305320774, 4.120202162759041, 0.35]
artwork_B[0].rotation = [0, 0, 0]
counter[0].position = [2.1561052005885823, 1.1836646552726238, 0.525]
counter[0].rotation = [0, 0, 0]
pendesk_C[0].position = [1.1392046334468866, 2.228778482964271, 0.005]
pendesk_C[0].rotation = [0, 0, 0]
plant_A[0].position = [4.668340082235334, 2.4879589283027497, 0.55]
plant_A[0].rotation = [0, 0, 0]
pottedplant_F[0].position = [3.984381799521665, 3.4559955604970103, 0.35]
pottedplant_F[0].rotation = [0, 0, 0]
mirror_A[0].position = [2.655296991507438, 0.9612828263295919, 0.6]
mirror_A[0].rotation = [0, 0, 0]
toolworkbench[0].position = [0.9641802134840634, 0.7533733507008966, 0.03]
toolworkbench[0].rotation = [0, 0, 0]
sign_B[0].position = [1.4368958757231542, 2.8502936473957714, 0.275]
sign_B[0].rotation = [0, 0, 0]
flowerarrangementcounter[0].position = [1.2811544869288176, 0.2081183214261917, 0.275]
flowerarrangementcounter[0].rotation = [0, 0, 0]
flowerarrangementfloor_A[0].position = [1.600617795301115, 4.093088655118701, 0.25]
flowerarrangementfloor_A[0].rotation = [0, 0, 0]
pottedplantfloor_F[0].position = [0.1430728150103282, 0.9787151640751812, 0.24]
pottedplantfloor_F[0].rotation = [0, 0, 0]
flowerarrangementfloor_B[0].position = [5.905257630118005, 2.368870775614816, 0.25]
flowerarrangementfloor_B[0].rotation = [0, 0, 0]
poster_A[0].position = [4.135775078296766, 1.3352732352722907, 0.45]
poster_A[0].rotation = [0, 0, 0]
plant_B[0].position = [2.953830203277436, 3.772754644883916, 0.55]
plant_B[0].rotation = [0, 0, 0]
bookcabinet_C[0].position = [5.4733786286678, 2.6327825552118274, 0.015]
bookcabinet_C[0].rotation = [0, 0, 0]
record_D[0].position = [2.736568295001821, 1.9392625904256593, 0.15]
record_D[0].rotation = [0, 0, 0]
chair[0].position = [5.686074389466954, 0.38873676732736895, 0.475]
chair[0].rotation = [0, 0, 0]
desk[0].position = [3.43536898974019, 0.5634212081899592, 0.38]
desk[0].rotation = [0, 0, 0]
board[0].position = [0.7177050651549777, 0.6711083227667092, 0.375]
board[0].rotation = [0, 0, 0]
pencounter[0].position = [0.4318700046937729, 1.6748588457725093, 0.005]
pencounter[0].rotation = [0, 0, 0]
bookfloor_C[0].position = [3.678277108635202, 1.4980520487341158, 0.015]
bookfloor_C[0].rotation = [0, 0, 0]
vasefloor_F[0].position = [1.3140211915353204, 2.1567704890088955, 0.325]
vasefloor_F[0].rotation = [0, 0, 0]
vasecabinet_F[0].position = [3.1324373017495573, 0.8563749373786017, 0.13]
vasecabinet_F[0].rotation = [0, 0, 0]
mirror_B[0].position = [1.9264111727524855, 1.6973665505827022, 0.65]
mirror_B[0].rotation = [0, 0, 0]
vaseworkbench_C[0].position = [2.8752709599977253, 1.3120594582550815, 0.14]
vaseworkbench_C[0].rotation = [0, 0, 0]
poster_B[0].position = [1.758051112147123, 4.253884437589678, 0.45]
poster_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Helper collections are used only to organize constraints; the asset variables
# themselves remain unchanged.
_floor_instances = []
_wall_instances = []
_surface_instances = []
_wall_furniture = []


def _place_floor(asset, position, rotation):
    """Place a floor-standing asset and remember it for common constraints."""
    asset[0].position = position
    asset[0].rotation = [0, 0, radians(rotation)]
    _floor_instances.append(asset[0])


def _place_wall(asset, position, rotation, wall):
    """Place a wall-mounted asset with its visible face directed into the room."""
    asset[0].position = position
    asset[0].rotation = [0, 0, radians(rotation)]
    _wall_instances.append((asset[0], wall))


def _place_surface(asset, support, position, rotation):
    """Place a small object on a supporting work surface."""
    asset[0].position = position
    asset[0].rotation = [0, 0, radians(rotation)]
    _surface_instances.append((asset[0], support[0]))


def _place_wall_furniture(asset, position, rotation, wall):
    """Place floor furniture flush with a wall."""
    asset[0].position = position
    asset[0].rotation = [0, 0, radians(rotation)]
    _wall_furniture.append((asset[0], wall))


# ---------------------------------------------------------------------------
# Main furniture
# ---------------------------------------------------------------------------

# The two cabinets occupy separated portions of the left wall.
_place_wall_furniture(cabinet_A, [0.225, 0.70, 0.95], 0, walls[2])
_place_wall_furniture(cabinet_B, [0.225, 4.25, 0.95], 0, walls[2])

# The workbench is against the upper wall. Its long dimension runs along x.
_place_wall_furniture(workbench, [2.00, 4.625, 0.45], -90, walls[1])

# The counter runs along the lower wall, leaving its working side accessible
# from the room.
_place_wall_furniture(counter, [4.50, 0.375, 0.525], 90, walls[3])

# The jukebox occupies the upper-right corner, well away from the door at
# (6.00, 2.83).
_place_wall_furniture(jukebox, [5.55, 4.725, 0.725], -90, walls[1])

# The desk and chair form a compact office station on the left side.
_place_floor(desk, [1.05, 2.45, 0.38], 0)
_place_floor(chair, [2.00, 2.45, 0.475], 180)

# Four stools face the counter while preserving a circulation aisle behind.
_place_floor(stool_A, [3.55, 1.10, 0.34], -90)
_place_floor(stool_B, [4.20, 1.10, 0.34], -90)
_place_floor(stool_C, [4.85, 1.10, 0.34], -90)
_place_floor(stool_D, [5.45, 1.10, 0.34], -90)


# ---------------------------------------------------------------------------
# Wall shelves and shelf-top plants
# ---------------------------------------------------------------------------

# Both shelves are mounted above floor level, outside the main furniture
# footprints. Their long axes run parallel to their respective walls.
_place_wall(shelf_A, [3.60, 4.86, 1.10], -90, walls[1])
_place_wall(shelf_B, [1.90, 0.14, 1.10], 90, walls[3])

# Three compact plants are evenly distributed across each shelf.
_place_surface(pottedplant_A, shelf_A, [3.15, 4.72, 1.45], -90)
_place_surface(pottedplant_B, shelf_A, [3.60, 4.72, 1.475], -90)
_place_surface(pottedplant_C, shelf_A, [4.05, 4.72, 1.45], -90)

_place_surface(pottedplant_D, shelf_B, [1.45, 0.28, 1.45], 90)
_place_surface(pottedplant_E, shelf_B, [1.90, 0.28, 1.45], 90)
_place_surface(pottedplant_F, shelf_B, [2.35, 0.28, 1.475], 90)


# ---------------------------------------------------------------------------
# Objects on the workbench
# ---------------------------------------------------------------------------

# The workbench top is at z=0.90. Small tools are grouped toward the front and
# vases toward the back without overlapping.
_place_surface(penworkbench_A, workbench, [1.30, 4.38, 0.905], -90)
_place_surface(penworkbench_B, workbench, [1.55, 4.38, 0.905], -90)
_place_surface(penworkbench_C, workbench, [1.80, 4.38, 0.905], -90)
_place_surface(penworkbench_D, workbench, [2.05, 4.38, 0.905], -90)

_place_surface(toolworkbench, workbench, [2.45, 4.38, 0.93], -90)

_place_surface(vaseworkbench_A, workbench, [1.35, 4.78, 1.04], -90)
_place_surface(vaseworkbench_B, workbench, [1.85, 4.78, 1.04], -90)
_place_surface(vaseworkbench_C, workbench, [2.35, 4.78, 1.04], -90)


# ---------------------------------------------------------------------------
# Objects on the counter
# ---------------------------------------------------------------------------

# The counter top is at z=1.05. Decorations occupy the back half, leaving a
# useful strip of clear counter surface along the stools.
_place_surface(vasecounter_A, counter, [3.70, 0.23, 1.19], 90)
_place_surface(vasecounter_B, counter, [4.15, 0.23, 1.19], 90)
_place_surface(flowerarrangementcounter, counter, [5.15, 0.25, 1.325], 90)

_place_surface(toolcounter_A, counter, [3.70, 0.57, 1.07], 90)
_place_surface(toolcounter_B, counter, [4.15, 0.57, 1.07], 90)
_place_surface(notebookcounter, counter, [4.58, 0.57, 1.06], 90)
_place_surface(pencounter, counter, [4.95, 0.57, 1.055], 90)


# ---------------------------------------------------------------------------
# Objects on the desk
# ---------------------------------------------------------------------------

# The desktop is at z=0.76. Books and notebooks are arranged in two neat rows.
_place_surface(bookdesk_A, desk, [0.82, 2.00, 0.775], 0)
_place_surface(bookdesk_B, desk, [0.82, 2.45, 0.78], 0)
_place_surface(notebookdesk_A, desk, [0.82, 2.85, 0.77], 0)
_place_surface(notebookdesk_B, desk, [1.20, 2.85, 0.77], 0)

_place_surface(pendesk_A, desk, [1.22, 1.95, 0.80], 0)
_place_surface(pendesk_B, desk, [1.22, 2.30, 0.80], 0)
_place_surface(pendesk_C, desk, [1.22, 2.65, 0.765], 0)


# ---------------------------------------------------------------------------
# Cabinet-top objects
# ---------------------------------------------------------------------------

# Each cabinet top is at z=1.90. Two shallow rows allow the small books,
# storage box, and vases to fit without intersecting one another.
_place_surface(bookcabinet_A, cabinet_A, [0.12, 0.40, 1.915], 0)
_place_surface(bookcabinet_B, cabinet_A, [0.12, 0.68, 1.915], 0)
_place_surface(bookcabinet_C, cabinet_A, [0.12, 0.96, 1.915], 0)
_place_surface(vasecabinet_A, cabinet_A, [0.33, 0.45, 2.04], 0)
_place_surface(vasecabinet_B, cabinet_A, [0.33, 0.88, 2.035], 0)

_place_surface(storageboxcabinet, cabinet_B, [0.12, 4.25, 2.01], 0)
_place_surface(vasecabinet_C, cabinet_B, [0.33, 3.93, 2.035], 0)
_place_surface(vasecabinet_D, cabinet_B, [0.33, 4.20, 2.03], 0)
_place_surface(vasecabinet_E, cabinet_B, [0.33, 4.47, 2.04], 0)
_place_surface(vasecabinet_F, cabinet_B, [0.12, 4.57, 2.03], 0)


# ---------------------------------------------------------------------------
# Floor decorations
# ---------------------------------------------------------------------------

# The requested plant-vase-plant composition is placed along the upper wall.
# vasefloor_A is geometrically centered between pottedplantfloor_A and
# pottedplantfloor_B.
_place_floor(pottedplantfloor_A, [3.10, 4.72, 0.25], -90)
_place_floor(vasefloor_A, [3.475, 4.72, 0.16], -90)
_place_floor(pottedplantfloor_B, [3.85, 4.72, 0.24], -90)

# Additional alternating plants and vases continue the decorative grouping
# while remaining clear of the jukebox.
_place_floor(vasefloor_B, [4.20, 4.72, 0.16], -90)
_place_floor(pottedplantfloor_C, [4.52, 4.72, 0.25], -90)
_place_floor(vasefloor_C, [4.82, 4.72, 0.325], -90)

# A second, smaller alternating group follows the lower-left wall.
_place_floor(pottedplantfloor_D, [0.72, 0.18, 0.25], 90)
_place_floor(vasefloor_D, [1.05, 0.16, 0.16], 90)
_place_floor(pottedplantfloor_E, [1.38, 0.17, 0.24], 90)
_place_floor(vasefloor_E, [1.70, 0.16, 0.325], 90)
_place_floor(pottedplantfloor_F, [2.02, 0.17, 0.24], 90)
_place_floor(vasefloor_F, [2.34, 0.16, 0.325], 90)

# Larger plants and flower arrangements occupy otherwise unused corners.
_place_floor(plant_A, [0.65, 1.40, 0.55], 0)
_place_floor(plant_B, [0.65, 3.43, 0.55], 0)
_place_floor(flowerarrangementfloor_A, [2.50, 1.18, 0.25], 90)
_place_floor(flowerarrangementfloor_B, [4.70, 3.95, 0.25], -90)

# The three intentionally floor-placed books form a small stack-like grouping
# near the lower wall, away from the counter.
_place_floor(bookfloor_A, [2.68, 0.16, 0.015], 90)
_place_floor(bookfloor_B, [2.94, 0.16, 0.015], 90)
_place_floor(bookfloor_C, [3.20, 0.16, 0.015], 90)


# ---------------------------------------------------------------------------
# Wall-mounted artwork, signage, lighting, records, mirrors, and clock
# ---------------------------------------------------------------------------

# Left-wall poster gallery. These are mounted above the 1.90 m cabinets and
# therefore do not intersect the cabinetry.
_place_wall(posterwall_A, [0.005, 0.45, 2.55], 0, walls[2])
_place_wall(posterwall_B, [0.005, 1.18, 2.48], 0, walls[2])
_place_wall(posterwall_C, [0.005, 1.83, 2.48], 0, walls[2])
_place_wall(posterwall_D, [0.005, 2.55, 2.55], 0, walls[2])
_place_wall(posterwall_E, [0.005, 3.30, 2.55], 0, walls[2])

# Upper-wall pictures, artwork, and mirrors are placed above the workbench and
# jukebox. Rotation -90 makes their fronts face into the room.
_place_wall(picture_A, [0.55, 4.98, 1.55], -90, walls[1])
_place_wall(artwork_A, [1.35, 4.98, 1.55], -90, walls[1])
_place_wall(mirror_A, [2.15, 4.98, 1.70], -90, walls[1])
_place_wall(picture_B, [2.95, 4.98, 2.30], -90, walls[1])
_place_wall(artwork_B, [3.75, 4.98, 2.30], -90, walls[1])
_place_wall(mirror_B, [4.65, 4.98, 2.30], -90, walls[1])

# Lower-wall signs and artwork are mounted above the counter or in the clear
# lower-left wall area.
_place_wall(sign_A, [0.55, 0.02, 1.55], 90, walls[3])
_place_wall(artworkwall_A, [1.45, 0.015, 2.25], 90, walls[3])
_place_wall(signwall, [2.45, 0.04, 2.25], 90, walls[3])
_place_wall(sign_B, [3.75, 0.04, 1.65], 90, walls[3])
_place_wall(artworkwall_B, [4.75, 0.015, 1.80], 90, walls[3])
_place_wall(board, [5.55, 0.02, 1.75], 90, walls[3])

# Right-wall items are kept either below or above the door interval centered
# at y=2.83, leaving the entrance and its approach unobstructed.
_place_wall(clock, [5.975, 0.55, 1.85], 180, walls[0])
_place_wall(lightfixturewall_A, [5.92, 1.10, 1.65], 180, walls[0])
_place_wall(lightfixturewall_B, [5.92, 1.65, 1.65], 180, walls[0])
_place_wall(lightfixturewall_C, [5.92, 2.05, 1.65], 180, walls[0])

_place_wall(record_A, [5.995, 3.55, 1.45], 180, walls[0])
_place_wall(record_B, [5.995, 3.95, 1.45], 180, walls[0])
_place_wall(record_C, [5.995, 4.35, 1.45], 180, walls[0])
_place_wall(record_D, [5.995, 4.75, 1.45], 180, walls[0])

# Slim wall lights and the remaining posters use a higher band so they do not
# overlap the lower wall-mounted objects.
_place_wall(lightfixture_A, [0.05, 4.00, 2.35], 0, walls[2])
_place_wall(lightfixture_B, [0.055, 4.28, 2.35], 0, walls[2])
_place_wall(lightfixture_C, [0.05, 4.55, 2.35], 0, walls[2])
_place_wall(lightfixture_D, [0.055, 4.82, 2.35], 0, walls[2])

_place_wall(poster_A, [5.995, 0.55, 2.55], 180, walls[0])
_place_wall(poster_B, [5.995, 1.35, 2.55], 180, walls[0])


# ---------------------------------------------------------------------------
# Constraints
# ---------------------------------------------------------------------------

_room_center = AssetInstance(position=[3.00, 2.50, 1.00])

# Exact initial anchors are the most important position constraints. They keep
# the carefully separated layout stable while the additional semantic
# constraints are evaluated.
for _floor_instance in _floor_instances:
    _floor_anchor = AssetInstance(position=list(_floor_instance.position))
    _floor_orientation = AssetInstance(rotation=list(_floor_instance.rotation))
    solver.distance_constraint(
        _floor_instance, _floor_anchor, 0.0, 0.0, weight=10
    )
    solver.align_with(_floor_instance, _floor_orientation, angle=0)

for _wall_instance, _supporting_wall in _wall_instances:
    _wall_anchor = AssetInstance(position=list(_wall_instance.position))
    _wall_orientation = AssetInstance(rotation=list(_wall_instance.rotation))
    solver.distance_constraint(
        _wall_instance, _wall_anchor, 0.0, 0.0, weight=10
    )
    solver.align_with(_wall_instance, _wall_orientation, angle=0)
    solver.against_wall(_wall_instance, _supporting_wall)

for _furniture_instance, _supporting_wall in _wall_furniture:
    _furniture_anchor = AssetInstance(position=list(_furniture_instance.position))
    _furniture_orientation = AssetInstance(
        rotation=list(_furniture_instance.rotation)
    )
    solver.distance_constraint(
        _furniture_instance, _furniture_anchor, 0.0, 0.0, weight=10
    )
    solver.align_with(
        _furniture_instance, _furniture_orientation, angle=0
    )
    solver.against_wall(_furniture_instance, _supporting_wall)

for _surface_instance, _support_instance in _surface_instances:
    _surface_anchor = AssetInstance(position=list(_surface_instance.position))
    solver.distance_constraint(
        _surface_instance, _surface_anchor, 0.0, 0.0, weight=10
    )
    solver.align_with(_surface_instance, _support_instance, angle=0)
    solver.on_top_of(_surface_instance, _support_instance)

# Reinforce the functional desk relationship: the chair faces the desk and
# remains at a usable distance from its center.
solver.point_towards(chair[0], desk[0])
solver.distance_constraint(chair[0], desk[0], 0.90, 1.10, weight=5)

# All stools face the counter while maintaining a practical service distance.
for _stool_instance in [stool_A[0], stool_B[0], stool_C[0], stool_D[0]]:
    solver.point_towards(_stool_instance, counter[0])
    solver.distance_constraint(
        _stool_instance, counter[0], 0.70, 1.50, weight=5
    )

# Preserve the requested plant-vase-plant composition. Equal distances from
# the two fixed plant positions retain vasefloor_A at their midpoint.
solver.distance_constraint(
    vasefloor_A[0], pottedplantfloor_A[0], 0.375, 0.375, weight=10
)
solver.distance_constraint(
    vasefloor_A[0], pottedplantfloor_B[0], 0.375, 0.375, weight=10
)
solver.distance_constraint(
    pottedplantfloor_A[0], pottedplantfloor_B[0], 0.75, 0.75, weight=10
)

# Explicitly reinforce the required cabinet relationship for vasecabinet_A.
solver.on_top_of(vasecabinet_A[0], cabinet_A[0])
solver.align_with(vasecabinet_A[0], cabinet_A[0], angle=0)

# Preserve the clear entrance zone in front of the door. The closest movable
# furniture and floor decorations remain well outside this zone.
_door_clearance_point = AssetInstance(position=[5.55, 2.83, 0.50])
solver.distance_constraint(jukebox[0], _door_clearance_point, 1.00, None, weight=10)
solver.distance_constraint(stool_D[0], _door_clearance_point, 1.20, None, weight=10)
solver.distance_constraint(
    flowerarrangementfloor_B[0], _door_clearance_point, 1.20, None, weight=10
)

solver.constraints = []
vaseworkbench_C[0].position = [2.3499999046325684, 4.78000020980835, 1.0399999618530273]
vaseworkbench_C[0].rotation = [0, 0, -1.5480050417303857]
vaseworkbench_C[0].optimize = 2
shelf_A[0].position = [3.5999999046325684, 4.851222515106201, 0.02500000037252903]
shelf_A[0].rotation = [0, 0, -1.5495903270898497]
shelf_A[0].optimize = 2
pottedplant_D[0].position = [1.4500000476837158, 0.2800000011920929, 0.375]
pottedplant_D[0].rotation = [0, 0, 1.593586675425212]
pottedplant_D[0].optimize = 2
penworkbench_C[0].position = [1.7999999523162842, 4.380000114440918, 0.9049999713897705]
penworkbench_C[0].rotation = [0, 0, -1.5480050417303857]
penworkbench_C[0].optimize = 2
pottedplant_F[0].position = [2.3499999046325684, 0.2800000011920929, 0.4000000059604645]
pottedplant_F[0].rotation = [0, 0, 1.593586675425212]
pottedplant_F[0].optimize = 2
record_C[0].position = [6.001560211181641, 4.349999904632568, 0.15000000596046448]
record_C[0].rotation = [0, 0, -3.139051732072762]
record_C[0].optimize = 2
poster_A[0].position = [6.001560688018799, 0.550000011920929, 0.44999998807907104]
poster_A[0].rotation = [0, 0, -3.1390517332948615]
poster_A[0].optimize = 2
toolworkbench[0].position = [2.450000047683716, 4.380000114440918, 0.9299999475479126]
toolworkbench[0].rotation = [0, 0, -1.5480050417303857]
toolworkbench[0].optimize = 2
vasecabinet_A[0].position = [0.33000001311302185, 0.44999998807907104, 2.0399999618530273]
vasecabinet_A[0].rotation = [0, 0, 0.02913600269229539]
vasecabinet_A[0].optimize = 2
record_D[0].position = [6.001560211181641, 4.75, 0.15000000596046448]
record_D[0].rotation = [0, 0, -3.139051732072762]
record_D[0].optimize = 2
storageboxcabinet[0].position = [0.15734851360321045, 4.25, 2.009999990463257]
storageboxcabinet[0].rotation = [0, 0, 0.022790948473449844]
storageboxcabinet[0].optimize = 2
vasefloor_B[0].position = [4.199999809265137, 4.71999979019165, 0.1599999964237213]
vasefloor_B[0].rotation = [0, 0, -1.5613715493341729]
vasefloor_B[0].optimize = 2
flowerarrangementfloor_A[0].position = [2.5, 1.1799999475479126, 0.25]
flowerarrangementfloor_A[0].rotation = [0, 0, 1.5802211042556205]
flowerarrangementfloor_A[0].optimize = 2
plant_B[0].position = [0.6499999761581421, 3.430000066757202, 0.550000011920929]
plant_B[0].rotation = [0, 0, 0.00942477746072377]
plant_B[0].optimize = 2
vasecounter_A[0].position = [3.700000047683716, 0.23000000417232513, 1.1899999380111694]
vasecounter_A[0].rotation = [0, 0, 1.5935877651672001]
vasecounter_A[0].optimize = 2
pottedplantfloor_A[0].position = [3.0999999046325684, 4.71999979019165, 0.25]
pottedplantfloor_A[0].rotation = [0, 0, -1.5550883628776802]
pottedplantfloor_A[0].optimize = 2
lightfixturewall_A[0].position = [5.919466495513916, 1.100000023841858, 0.10999999940395355]
lightfixturewall_A[0].rotation = [0, 0, -3.139051732072762]
lightfixturewall_A[0].optimize = 2
lightfixture_A[0].position = [0.04059594124555588, 4.0, 0.25]
lightfixture_A[0].rotation = [0, 0, 0.002540922439204702]
lightfixture_A[0].optimize = 2
bookdesk_A[0].position = [0.8199999928474426, 2.0, 0.7749999761581421]
bookdesk_A[0].rotation = [0, 0, 0.022791247207920588]
bookdesk_A[0].optimize = 2
stool_D[0].position = [5.449999809265137, 1.100000023841858, 0.3400000035762787]
stool_D[0].rotation = [0, 0, -1.5519467713960802]
stool_D[0].optimize = 2
pottedplantfloor_E[0].position = [1.3799999952316284, 0.17000000178813934, 0.23999999463558197]
pottedplantfloor_E[0].rotation = [0, 0, 1.5802211042556205]
pottedplantfloor_E[0].optimize = 2
picture_A[0].position = [0.550000011920929, 4.988697052001953, 0.44999998807907104]
picture_A[0].rotation = [0, 0, -1.5682554086442377]
picture_A[0].optimize = 2
pendesk_A[0].position = [1.2200000286102295, 1.9500000476837158, 0.800000011920929]
pendesk_A[0].rotation = [0, 0, 0.022791247207920588]
pendesk_A[0].optimize = 2
notebookdesk_A[0].position = [0.8199999928474426, 2.8499999046325684, 0.7699999809265137]
notebookdesk_A[0].rotation = [0, 0, 0.022791247207920588]
notebookdesk_A[0].optimize = 2
lightfixture_D[0].position = [0.045544665306806564, 4.820000171661377, 0.25999999046325684]
lightfixture_D[0].rotation = [0, 0, 0.002540920594857827]
lightfixture_D[0].optimize = 2
penworkbench_A[0].position = [1.2999999523162842, 4.380000114440918, 0.9049999713897705]
penworkbench_A[0].rotation = [0, 0, -1.5480050417303857]
penworkbench_A[0].optimize = 2
bookdesk_B[0].position = [0.8199999928474426, 2.450000047683716, 0.7799999713897705]
bookdesk_B[0].rotation = [0, 0, 0.022791247207920588]
bookdesk_B[0].optimize = 2
poster_B[0].position = [6.001560688018799, 1.350000023841858, 0.44999998807907104]
poster_B[0].rotation = [0, 0, -3.1390517332948615]
poster_B[0].optimize = 2
pencounter[0].position = [4.949999809265137, 0.5699999928474426, 1.0549999475479126]
pencounter[0].rotation = [0, 0, 1.5935877651672001]
pencounter[0].optimize = 2
lightfixturewall_C[0].position = [5.919466495513916, 2.049999952316284, 0.10999999940395355]
lightfixturewall_C[0].rotation = [0, 0, -3.139051732072762]
lightfixturewall_C[0].optimize = 2
vasefloor_A[0].position = [3.4749999046325684, 4.71999979019165, 0.1599999964237213]
vasefloor_A[0].rotation = [0, 0, -1.5550883628776802]
vasefloor_A[0].optimize = 2
vasefloor_E[0].position = [1.7000000476837158, 0.1599999964237213, 0.32499998807907104]
vasefloor_E[0].rotation = [0, 0, 1.5802211042556205]
vasefloor_E[0].optimize = 2
vasefloor_D[0].position = [1.0499999523162842, 0.1599999964237213, 0.1599999964237213]
vasefloor_D[0].rotation = [0, 0, 1.5802211042556205]
vasefloor_D[0].optimize = 2
posterwall_B[0].position = [-0.0011201626621186733, 1.1799999475479126, 0.3799999952316284]
posterwall_B[0].rotation = [0, 0, 0.0025409193727581954]
posterwall_B[0].optimize = 2
clock[0].position = [5.983956336975098, 0.550000011920929, 0.20000000298023224]
clock[0].rotation = [0, 0, -3.139051732072762]
clock[0].optimize = 2
toolcounter_A[0].position = [3.700000047683716, 0.5699999928474426, 1.0699999332427979]
toolcounter_A[0].rotation = [0, 0, 1.5935877651672001]
toolcounter_A[0].optimize = 2
vasefloor_C[0].position = [4.820000171661377, 4.71999979019165, 0.32499998807907104]
vasefloor_C[0].rotation = [0, 0, -1.5613715493341729]
vasefloor_C[0].optimize = 2
record_B[0].position = [6.001560211181641, 3.950000047683716, 0.15000000596046448]
record_B[0].rotation = [0, 0, -3.139051732072762]
record_B[0].optimize = 2
artwork_A[0].position = [1.350000023841858, 4.988697052001953, 0.3499999940395355]
artwork_A[0].rotation = [0, 0, -1.5682554086442377]
artwork_A[0].optimize = 2
vasecabinet_E[0].position = [0.33000001311302185, 4.46999979019165, 2.0399999618530273]
vasecabinet_E[0].rotation = [0, 0, 0.022790948473449844]
vasecabinet_E[0].optimize = 2
signwall[0].position = [2.450000047683716, 0.04152441769838333, 0.22499999403953552]
signwall[0].rotation = [0, 0, 1.5733372372906427]
signwall[0].optimize = 2
picture_B[0].position = [2.950000047683716, 4.988697052001953, 0.44999998807907104]
picture_B[0].rotation = [0, 0, -1.5682554086442377]
picture_B[0].optimize = 2
bookfloor_A[0].position = [2.680000066757202, 0.1599999964237213, 0.014999999664723873]
bookfloor_A[0].rotation = [0, 0, 1.5802211042556205]
bookfloor_A[0].optimize = 2
notebookcounter[0].position = [4.579999923706055, 0.5699999928474426, 1.059999942779541]
notebookcounter[0].rotation = [0, 0, 1.5935877651672001]
notebookcounter[0].optimize = 2
cabinet_B[0].position = [0.23456819355487823, 4.25, 0.949999988079071]
cabinet_B[0].rotation = [0, 0, 0.033651360962098587]
cabinet_B[0].optimize = 2
mirror_B[0].position = [4.650000095367432, 4.988697052001953, 0.6499999761581421]
mirror_B[0].rotation = [0, 0, -1.5682554086442377]
mirror_B[0].optimize = 2
vaseworkbench_A[0].position = [1.350000023841858, 4.78000020980835, 1.0399999618530273]
vaseworkbench_A[0].rotation = [0, 0, -1.5480050417303857]
vaseworkbench_A[0].optimize = 2
cabinet_A[0].position = [0.23732587695121765, 0.699999988079071, 0.949999988079071]
cabinet_A[0].rotation = [0, 0, 0.03987463273977418]
cabinet_A[0].optimize = 2
pottedplant_E[0].position = [1.899999976158142, 0.2800000011920929, 0.375]
pottedplant_E[0].rotation = [0, 0, 1.593586675425212]
pottedplant_E[0].optimize = 2
bookcabinet_B[0].position = [0.11999999731779099, 0.6800000071525574, 1.9149999618530273]
bookcabinet_B[0].rotation = [0, 0, 0.02279109852594279]
bookcabinet_B[0].optimize = 2
plant_A[0].position = [0.6499999761581421, 1.399999976158142, 0.550000011920929]
plant_A[0].rotation = [0, 0, 0.00942477746072377]
plant_A[0].optimize = 2
vasecounter_B[0].position = [4.150000095367432, 0.23000000417232513, 1.1899999380111694]
vasecounter_B[0].rotation = [0, 0, 1.5935877651672001]
vasecounter_B[0].optimize = 2
stool_C[0].position = [4.849999904632568, 1.100000023841858, 0.3400000035762787]
stool_C[0].rotation = [0, 0, -1.5550883628776802]
stool_C[0].optimize = 2
vasefloor_F[0].position = [2.3399999141693115, 0.1599999964237213, 0.32499998807907104]
vasefloor_F[0].rotation = [0, 0, 1.5802211042556205]
vasefloor_F[0].optimize = 2
pendesk_B[0].position = [1.2200000286102295, 2.299999952316284, 0.800000011920929]
pendesk_B[0].rotation = [0, 0, 0.022791247207920588]
pendesk_B[0].optimize = 2
vaseworkbench_B[0].position = [1.850000023841858, 4.78000020980835, 1.0399999618530273]
vaseworkbench_B[0].rotation = [0, 0, -1.5480050417303857]
vaseworkbench_B[0].optimize = 2
penworkbench_D[0].position = [2.049999952316284, 4.380000114440918, 0.9049999713897705]
penworkbench_D[0].rotation = [0, 0, -1.5480050417303857]
penworkbench_D[0].optimize = 2
vasecabinet_F[0].position = [0.11999999731779099, 4.570000171661377, 2.0299999713897705]
vasecabinet_F[0].rotation = [0, 0, 0.022790948473449844]
vasecabinet_F[0].optimize = 2
pendesk_C[0].position = [1.2200000286102295, 2.6500000953674316, 0.7649999856948853]
pendesk_C[0].rotation = [0, 0, 0.022791247207920588]
pendesk_C[0].optimize = 2
bookfloor_C[0].position = [3.200000047683716, 0.1599999964237213, 0.014999999664723873]
bookfloor_C[0].rotation = [0, 0, 1.5802211042556205]
bookfloor_C[0].optimize = 2
counter[0].position = [4.5, 0.453499436378479, 0.5249999761581421]
counter[0].rotation = [0, 0, 1.6417933710742625]
counter[0].optimize = 2
workbench[0].position = [2.0, 4.579228401184082, 0.44999998807907104]
workbench[0].rotation = [0, 0, -1.5184739401506868]
workbench[0].optimize = 2
bookcabinet_C[0].position = [0.11999999731779099, 0.9599999785423279, 1.9149999618530273]
bookcabinet_C[0].rotation = [0, 0, 0.02279109852594279]
bookcabinet_C[0].optimize = 2
pottedplantfloor_C[0].position = [4.519999980926514, 4.71999979019165, 0.25]
pottedplantfloor_C[0].rotation = [0, 0, -1.5613715493341729]
pottedplantfloor_C[0].optimize = 2
flowerarrangementcounter[0].position = [5.150000095367432, 0.25, 1.3249999284744263]
flowerarrangementcounter[0].rotation = [0, 0, 1.5935877651672001]
flowerarrangementcounter[0].optimize = 2
pottedplant_A[0].position = [3.1500000953674316, 4.71999979019165, 0.375]
pottedplant_A[0].rotation = [0, 0, -1.5480059781645814]
pottedplant_A[0].optimize = 2
posterwall_D[0].position = [-0.0011212574318051338, 2.549999952316284, 0.45500001311302185]
posterwall_D[0].rotation = [0, 0, 0.0025409193727581954]
posterwall_D[0].optimize = 2
shelf_B[0].position = [1.899999976158142, 0.14877749979496002, 0.02500000037252903]
shelf_B[0].rotation = [0, 0, 1.5920023264999437]
shelf_B[0].optimize = 2
mirror_A[0].position = [2.1500000953674316, 4.988697052001953, 0.6000000238418579]
mirror_A[0].rotation = [0, 0, -1.5682554086442377]
mirror_A[0].optimize = 2
record_A[0].position = [6.001560211181641, 3.549999952316284, 0.15000000596046448]
record_A[0].rotation = [0, 0, -3.139051732072762]
record_A[0].optimize = 2
posterwall_A[0].position = [-0.0011212574318051338, 0.44999998807907104, 0.45500001311302185]
posterwall_A[0].rotation = [0, 0, 0.0025409193727581954]
posterwall_A[0].optimize = 2
posterwall_E[0].position = [-0.0011212574318051338, 3.299999952316284, 0.45500001311302185]
posterwall_E[0].rotation = [0, 0, 0.0025409193727581954]
posterwall_E[0].optimize = 2
artworkwall_A[0].position = [1.4500000476837158, 0.006743620149791241, 0.42500001192092896]
artworkwall_A[0].rotation = [0, 0, 1.5733372440233822]
artworkwall_A[0].optimize = 2
jukebox[0].position = [5.550000190734863, 4.722461223602295, 0.7250000238418579]
jukebox[0].rotation = [0, 0, -1.565144806956787]
jukebox[0].optimize = 2
pottedplantfloor_B[0].position = [3.8499999046325684, 4.71999979019165, 0.23999999463558197]
pottedplantfloor_B[0].rotation = [0, 0, -1.5550883628776802]
pottedplantfloor_B[0].optimize = 2
vasecabinet_B[0].position = [0.33000001311302185, 0.8799999952316284, 2.0350000858306885]
vasecabinet_B[0].rotation = [0, 0, 0.02279109852594279]
vasecabinet_B[0].optimize = 2
bookfloor_B[0].position = [2.940000057220459, 0.1599999964237213, 0.014999999664723873]
bookfloor_B[0].rotation = [0, 0, 1.5802211042556205]
bookfloor_B[0].optimize = 2
board[0].position = [5.44979190826416, 0.021397436037659645, 0.375]
board[0].rotation = [0, 0, 1.5733372385127404]
board[0].optimize = 2
pottedplant_C[0].position = [4.050000190734863, 4.71999979019165, 0.375]
pottedplant_C[0].rotation = [0, 0, -1.5480059781645814]
pottedplant_C[0].optimize = 2
desk[0].position = [1.0499999523162842, 2.450000047683716, 0.3799999952316284]
desk[0].rotation = [0, 0, 0.059690259289836754]
desk[0].optimize = 2
bookcabinet_A[0].position = [0.11999999731779099, 0.4000000059604645, 1.9149999618530273]
bookcabinet_A[0].rotation = [0, 0, 0.02279109852594279]
bookcabinet_A[0].optimize = 2
posterwall_C[0].position = [-0.0011201626621186733, 1.8300000429153442, 0.3799999952316284]
posterwall_C[0].rotation = [0, 0, 0.0025409193727581954]
posterwall_C[0].optimize = 2
stool_B[0].position = [4.199999809265137, 1.100000023841858, 0.3400000035762787]
stool_B[0].rotation = [0, 0, -1.5550883628776802]
stool_B[0].optimize = 2
lightfixture_B[0].position = [0.045544665306806564, 4.28000020980835, 0.25999999046325684]
lightfixture_B[0].rotation = [0, 0, 0.002540920594857827]
lightfixture_B[0].optimize = 2
artworkwall_B[0].position = [4.75, 0.006743620149791241, 0.42500001192092896]
artworkwall_B[0].rotation = [0, 0, 1.5733372440233822]
artworkwall_B[0].optimize = 2
pottedplantfloor_F[0].position = [2.0199999809265137, 0.17000000178813934, 0.23999999463558197]
pottedplantfloor_F[0].rotation = [0, 0, 1.5802211042556205]
pottedplantfloor_F[0].optimize = 2
vasecabinet_D[0].position = [0.33000001311302185, 4.199999809265137, 2.0299999713897705]
vasecabinet_D[0].rotation = [0, 0, 0.022790948473449844]
vasecabinet_D[0].optimize = 2
stool_A[0].position = [3.549999952316284, 1.100000023841858, 0.3400000035762787]
stool_A[0].rotation = [0, 0, -1.5550883628776802]
stool_A[0].optimize = 2
sign_A[0].position = [0.550000011920929, 0.011367769911885262, 0.17499999701976776]
sign_A[0].rotation = [0, 0, 1.5733372418791103]
sign_A[0].optimize = 2
lightfixturewall_B[0].position = [5.919466495513916, 1.649999976158142, 0.10999999940395355]
lightfixturewall_B[0].rotation = [0, 0, -3.139051732072762]
lightfixturewall_B[0].optimize = 2
sign_B[0].position = [3.75, 0.041397374123334885, 0.2750000059604645]
sign_B[0].rotation = [0, 0, 1.5733372385127404]
sign_B[0].optimize = 2
penworkbench_B[0].position = [1.5499999523162842, 4.380000114440918, 0.9049999713897705]
penworkbench_B[0].rotation = [0, 0, -1.5480050417303857]
penworkbench_B[0].optimize = 2
flowerarrangementfloor_B[0].position = [4.699999809265137, 3.950000047683716, 0.25]
flowerarrangementfloor_B[0].rotation = [0, 0, -1.5582299555380688]
flowerarrangementfloor_B[0].optimize = 2
pottedplantfloor_D[0].position = [0.7200000286102295, 0.18000000715255737, 0.25]
pottedplantfloor_D[0].rotation = [0, 0, 1.5802211042556205]
pottedplantfloor_D[0].optimize = 2
lightfixture_C[0].position = [0.04059594124555588, 4.550000190734863, 0.25]
lightfixture_C[0].rotation = [0, 0, 0.002540922439204702]
lightfixture_C[0].optimize = 2
artwork_B[0].position = [3.75, 4.988697052001953, 0.3499999940395355]
artwork_B[0].rotation = [0, 0, -1.5682554086442377]
artwork_B[0].optimize = 2
notebookdesk_B[0].position = [1.2000000476837158, 2.8499999046325684, 0.7699999809265137]
notebookdesk_B[0].rotation = [0, 0, 0.022791247207920588]
notebookdesk_B[0].optimize = 2
vasecabinet_C[0].position = [0.33000001311302185, 3.930000066757202, 2.0350000858306885]
vasecabinet_C[0].rotation = [0, 0, 0.022790948473449844]
vasecabinet_C[0].optimize = 2
toolcounter_B[0].position = [4.150000095367432, 0.5699999928474426, 1.0699999332427979]
toolcounter_B[0].rotation = [0, 0, 1.5935877651672001]
toolcounter_B[0].optimize = 2
chair[0].position = [2.0, 2.450000047683716, 0.4749999940395355]
chair[0].rotation = [0, 0, -3.125884689672577]
chair[0].optimize = 2
pottedplant_B[0].position = [3.5999999046325684, 4.71999979019165, 0.4000000059604645]
pottedplant_B[0].rotation = [0, 0, -1.5480059781645814]
pottedplant_B[0].optimize = 2

