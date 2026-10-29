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
    Wall(corner1=[4.20, 0.00, 0.00], corner2=[4.20, 5.00, 0.00]),
    Wall(corner1=[4.20, 5.00, 0.00], corner2=[0.00, 5.00, 0.00]),
    Wall(corner1=[0.00, 5.00, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.20, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
medicinebottle_A = Assets(description="A clear urban modern medicine bottle with a cylindrical shape, smooth transparent glass, amber liquid inside and a sleek silver screw cap, visible through cabinet doors", size=[0.07, 0.07, 0.16], placements=[AssetInstance() for _ in range(1)])
cupnightstand_A = Assets(description="A clear glass urban modern cup with a smooth cylindrical shape, crystal clear body and a thin silver rim, containing a subtle water ripple pattern etched inside", size=[0.07, 0.07, 0.11], placements=[AssetInstance() for _ in range(1)])
medicalequipment_A = Assets(description="A compact urban modern medical equipment unit with a rectangular body, smooth white plastic finish, a small digital display on the front and a subtle ergonomic curve at the top", size=[0.35, 0.40, 0.75], placements=[AssetInstance() for _ in range(1)])
floorlamp_A = Assets(description="A tall floor lamp with a slender cylindrical pole, a wide conical shade, and a matte black finish, standing upright.", size=[0.35, 0.35, 1.65], placements=[AssetInstance() for _ in range(1)])
artwork_A = Assets(description="A single piece of thin and upright artwork with a rectangular shape, glossy white canvas and a bold abstract black line motif that stretches vertically", size=[0.03, 0.45, 0.70], placements=[AssetInstance() for _ in range(1)])
ivstand = Assets(description="A compact urban modern IV stand with a cylindrical metal pole, angular black powder‑coated base, and a clear acrylic tray that slides vertically", size=[0.55, 0.55, 2.00], placements=[AssetInstance() for _ in range(1)])
heater = Assets(description="A compact urban modern space heater with a square base, brushed metal housing, and a curved front grille that emits a warm amber glow", size=[0.25, 0.30, 0.40], placements=[AssetInstance() for _ in range(1)])
pendesk_A = Assets(description="A sleek urban modern pen with a slim cylindrical body, brushed aluminum finish and a subtle matte black tip, slightly curved for ergonomic grip", size=[0.01, 0.14, 0.01], placements=[AssetInstance() for _ in range(1)])
stool = Assets(description="A lightweight urban modern side stool with a tapered cylindrical seat, matte white finish, and a single chrome leg that bends slightly outward for stability", size=[0.35, 0.35, 0.46], placements=[AssetInstance() for _ in range(1)])
bookdesk_A = Assets(description="A hardcover urban modern book with a rectangular shape, smooth matte finish, deep navy cover and a subtle embossed pattern, featuring slightly rounded edges for a sleek look", size=[0.23, 0.16, 0.03], placements=[AssetInstance() for _ in range(1)])
bookdesk_B = Assets(description="A hardcover urban modern book with a rectangular shape, smooth matte finish, dark gray cover and a subtle embossed pattern, slightly rounded edges for easy handling", size=[0.23, 0.16, 0.03], placements=[AssetInstance() for _ in range(1)])
desk = Assets(description="A minimalist urban modern work desk with a straight‑edged rectangular tabletop, light oak veneer, and slim chrome legs that taper inward", size=[0.60, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
notebook = Assets(description="A softcover urban modern notebook with a rectangular shape, pastel teal cover, smooth textured paper and a rounded spine, featuring a thin metal clasp", size=[0.21, 0.15, 0.01], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="A tall urban modern storage cabinet featuring a rectangular box shape, matte gray laminate doors, and a subtle brushed‑metal handle strip across the front", size=[0.40, 0.75, 1.80], placements=[AssetInstance() for _ in range(1)])
plant_A = Assets(description="A potted urban modern plant with a cylindrical pot, matte white finish, and lush green foliage extending outward in a rounded canopy.", size=[0.40, 0.40, 0.75], placements=[AssetInstance() for _ in range(1)])
book = Assets(description="A hardcover urban modern book with a rectangular shape, sleek matte black cover, and a subtle embossed pattern that catches the light", size=[0.23, 0.16, 0.03], placements=[AssetInstance() for _ in range(1)])
sofa = Assets(description="A low‑slung urban modern visitor sofa with a sleek rectangular silhouette, soft teal fabric upholstery, and a subtle tufted pattern along the backrest", size=[0.75, 1.40, 0.78], placements=[AssetInstance() for _ in range(1)])
mirror_A = Assets(description="A single piece of thin and upright mirror with a square shape, polished silver backing and a sleek brushed aluminum frame, reflecting the opposite side of the room", size=[0.03, 0.50, 0.50], placements=[AssetInstance() for _ in range(1)])
pendesk_B = Assets(description="A sleek urban modern pen with a slim cylindrical body, brushed aluminum finish and a subtle matte black tip, slightly curved for ergonomic grip", size=[0.01, 0.14, 0.01], placements=[AssetInstance() for _ in range(1)])
medicalbottle_A = Assets(description="A small cylindrical urban modern medical bottle made of clear plastic, with a bright orange cap and a minimalist label.", size=[0.04, 0.04, 0.09], placements=[AssetInstance() for _ in range(1)])
mirror_B = Assets(description="A single piece of thin and upright mirror with a rectangular outline, polished silver backing, beveled edges and a subtle decorative etched border, giving a sleek reflective surface", size=[0.03, 0.40, 0.65], placements=[AssetInstance() for _ in range(1)])
medicalbottle_B = Assets(description="A small cylindrical urban modern medical bottle made of clear plastic, with a bright orange cap and a minimalist label.", size=[0.04, 0.04, 0.09], placements=[AssetInstance() for _ in range(1)])
bookchair_A = Assets(description="A compact urban modern book with a square softcover, matte charcoal finish and a subtle embossed grid, corners slightly beveled for a modern look", size=[0.18, 0.18, 0.01], placements=[AssetInstance() for _ in range(1)])
mirror_C = Assets(description="A single piece of thin and upright mirror with a rectangular shape, sleek brushed‑silver frame and a beveled edge that catches reflections", size=[0.03, 0.40, 0.60], placements=[AssetInstance() for _ in range(1)])
phone = Assets(description="A slim urban modern smartphone with a rectangular shape, matte black back, glass front and rounded corners, screen facing upward", size=[0.15, 0.07, 0.01], placements=[AssetInstance() for _ in range(1)])
lampnightstand = Assets(description="A contemporary urban modern table lamp with a slender conical shade, matte ivory fabric, and a thin brushed steel base, the shade features a subtle ribbed texture", size=[0.22, 0.22, 0.40], placements=[AssetInstance() for _ in range(1)])
floorlamp_B = Assets(description="A tall slender urban modern floor lamp with a slim cylindrical base, a thin metal pole, and a minimalist conical shade in matte black.", size=[0.30, 0.30, 1.60], placements=[AssetInstance() for _ in range(1)])
cupnightstand_B = Assets(description="A clear glass urban modern cup with a cylindrical shape, thin walls and a short straw inserted, giving a light, airy appearance", size=[0.07, 0.07, 0.18], placements=[AssetInstance() for _ in range(1)])
medicationbottle_A = Assets(description="A small cylindrical urban modern medication bottle made of clear glass, with a pastel green cap and a subtle label.", size=[0.04, 0.04, 0.09], placements=[AssetInstance() for _ in range(1)])
trashbin_A = Assets(description="A compact rectangular trash bin with a smooth matte gray exterior, a hinged lid, and a subtle recessed handle.", size=[0.26, 0.22, 0.35], placements=[AssetInstance() for _ in range(1)])
medicalmonitor = Assets(description="A rectangular urban modern medical monitor with a sleek black frame and a smooth glass screen, featuring subtle brushed metal accents.", size=[0.18, 0.36, 0.30], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="A sleek urban modern hospital bed with a rectangular low‑profile frame, smooth white lacquer finish, stainless steel legs, and a curved headboard that integrates subtle LED accent lighting", size=[2.20, 1.05, 1.05], placements=[AssetInstance() for _ in range(1)])
nightstand = Assets(description="A compact urban modern nightstand with a square footprint, glossy white surface, and a single recessed drawer featuring a hidden magnetic latch", size=[0.55, 0.55, 0.65], placements=[AssetInstance() for _ in range(1)])
wastebin = Assets(description="A sturdy urban modern waste bin with a cylindrical body, matte black finish, and a recessed foot pedal for hands‑free opening", size=[0.25, 0.25, 0.38], placements=[AssetInstance() for _ in range(1)])
medicalchart = Assets(description="A thin upright urban modern medical chart, single piece of paper on a lightweight board, with crisp white background and subtle gray grid lines.", size=[0.02, 0.24, 0.33], placements=[AssetInstance() for _ in range(1)])
medicationbottle_B = Assets(description="A small urban modern medication bottle with a rectangular shape, opaque pastel blue plastic, child‑proof cap slightly ajar, and a subtle embossed label", size=[0.04, 0.06, 0.10], placements=[AssetInstance() for _ in range(1)])
bookchair_B = Assets(description="A hardcover urban modern book with a rectangular shape, smooth matte cover, deep navy color, and a minimalist gold line accent.", size=[0.22, 0.15, 0.03], placements=[AssetInstance() for _ in range(1)])
bookdesk_C = Assets(description="A hardcover urban modern book with a rectangular shape, smooth matte finish, dark gray cover and a subtle embossed pattern, slightly rounded edges for easy handling", size=[0.23, 0.16, 0.03], placements=[AssetInstance() for _ in range(1)])
plant_B = Assets(description="A potted indoor plant with a round terracotta pot, featuring long, glossy green leaves that arch outward.", size=[0.40, 0.40, 0.70], placements=[AssetInstance() for _ in range(1)])
pillow = Assets(description="A rectangular urban modern pillow with a soft plush surface, covered in a muted gray fabric with a subtle geometric pattern.", size=[0.45, 0.65, 0.15], placements=[AssetInstance() for _ in range(1)])
coffeecup = Assets(description="A small cylindrical urban modern coffee cup with a glossy white porcelain finish and a slim silver handle.", size=[0.07, 0.10, 0.08], placements=[AssetInstance() for _ in range(1)])
plantcabinet = Assets(description="A potted urban modern plant with a cylindrical terracotta pot, compact green foliage and a subtle matte finish, sitting on the cabinet top", size=[0.25, 0.25, 0.35], placements=[AssetInstance() for _ in range(1)])
floorlamp_C = Assets(description="A tall urban modern floor lamp with a slender cylindrical shaft, matte black finish, and an angular conical shade that casts a focused light, positioned in the corner near the sofa", size=[0.32, 0.32, 1.65], placements=[AssetInstance() for _ in range(1)])
plant_C = Assets(description="A potted indoor plant with a round terracotta pot, featuring long, glossy green leaves that arch outward.", size=[0.40, 0.40, 0.75], placements=[AssetInstance() for _ in range(1)])
pen = Assets(description="A slender urban modern pen with a smooth cylindrical barrel, brushed aluminum texture, and a subtle chrome tip, slightly tapered at the end for a sleek profile", size=[0.01, 0.14, 0.01], placements=[AssetInstance() for _ in range(1)])
medicinebottle_B = Assets(description="A clear urban modern medicine bottle with a cylindrical shape, smooth transparent glass, amber liquid inside and a sleek silver screw cap, visible through cabinet doors", size=[0.07, 0.07, 0.16], placements=[AssetInstance() for _ in range(1)])
artwork_B = Assets(description="A single piece of thin and upright painting with a rectangular shape, abstract urban modern design, muted gray background and a splash of teal, framed in a narrow black metal frame", size=[0.03, 0.60, 0.45], placements=[AssetInstance() for _ in range(1)])
plant_D = Assets(description="A potted urban modern plant with a cylindrical terracotta pot, matte finish and a small drainage hole, the foliage consists of long, glossy green leaves that arch outward", size=[0.35, 0.35, 0.65], placements=[AssetInstance() for _ in range(1)])
purifier = Assets(description="A streamlined urban modern air purifier with a tall cylindrical core, frosted glass front, and a subtle LED display ring at the top", size=[0.25, 0.25, 0.60], placements=[AssetInstance() for _ in range(1)])
floorlamp_D = Assets(description="A tall urban modern floor lamp with a slender cylindrical shaft, brushed nickel finish and a small circular diffuser at the top, the base is a weighted round disc for stability", size=[0.28, 0.28, 1.70], placements=[AssetInstance() for _ in range(1)])
booknightstand = Assets(description="A paperback urban modern book with a rectangular profile, soft pastel teal cover and a glossy finish, edges slightly rounded for a gentle feel", size=[0.20, 0.13, 0.02], placements=[AssetInstance() for _ in range(1)])
trashbin_B = Assets(description="A rectangular urban modern trash bin with a smooth white plastic body, slightly rounded corners and a discreet lid, located near the desk", size=[0.25, 0.22, 0.32], placements=[AssetInstance() for _ in range(1)])
medicinebottle_C = Assets(description="A clear urban modern medicine bottle with a cylindrical shape, smooth transparent glass, amber liquid inside and a sleek silver screw cap, visible through cabinet doors", size=[0.07, 0.07, 0.16], placements=[AssetInstance() for _ in range(1)])
artwork_C = Assets(description="A single piece of thin and upright painting with a bold abstract composition, featuring a glossy white canvas stretched over a slim wooden frame.", size=[0.03, 0.50, 0.65], placements=[AssetInstance() for _ in range(1)])
artwork_D = Assets(description="A single piece of thin and upright painting with a rectangular shape, smooth canvas surface, soft ivory background and a bold abstract black line motif, framed in a narrow black wood frame", size=[0.03, 0.45, 0.65], placements=[AssetInstance() for _ in range(1)])
mirror_D = Assets(description="A single piece of thin and upright mirror with a sleek silver backing, rectangular shape and a polished reflective surface.", size=[0.02, 0.40, 0.65], placements=[AssetInstance() for _ in range(1)])
chair = Assets(description="A contemporary urban modern patient chair with a rounded backrest, ergonomic curved seat, and a polished aluminum frame finished in soft charcoal", size=[0.62, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
cupdesk_A = Assets(description="A ceramic urban modern cup with a sleek cylindrical shape, glossy white surface and a thin brushed metal rim, featuring a small geometric engraving near the base", size=[0.08, 0.08, 0.10], placements=[AssetInstance() for _ in range(1)])
cupdesk_B = Assets(description="A ceramic urban modern cup with a cylindrical shape, glossy white surface and a thin silver rim, slightly tapered toward the base", size=[0.08, 0.08, 0.10], placements=[AssetInstance() for _ in range(1)])
medicalequipment_B = Assets(description="A compact cubic urban modern medical equipment unit with a smooth white exterior and subtle rounded edges.", size=[0.35, 0.35, 0.40], placements=[AssetInstance() for _ in range(1)])
recyclebin = Assets(description="A sleek urban modern recycle bin featuring a slim rectangular shape, bright teal lid, and a brushed‑steel side panel for easy sorting", size=[0.30, 0.22, 0.42], placements=[AssetInstance() for _ in range(1)])

medicinebottle_A[0].instance_id = 'medicinebottle_A_0'
cupnightstand_A[0].instance_id = 'cupnightstand_A_0'
medicalequipment_A[0].instance_id = 'medicalequipment_A_0'
floorlamp_A[0].instance_id = 'floorlamp_A_0'
artwork_A[0].instance_id = 'artwork_A_0'
ivstand[0].instance_id = 'ivstand_0'
heater[0].instance_id = 'heater_0'
pendesk_A[0].instance_id = 'pendesk_A_0'
stool[0].instance_id = 'stool_0'
bookdesk_A[0].instance_id = 'bookdesk_A_0'
bookdesk_B[0].instance_id = 'bookdesk_B_0'
desk[0].instance_id = 'desk_0'
notebook[0].instance_id = 'notebook_0'
cabinet[0].instance_id = 'cabinet_0'
plant_A[0].instance_id = 'plant_A_0'
book[0].instance_id = 'book_0'
sofa[0].instance_id = 'sofa_0'
mirror_A[0].instance_id = 'mirror_A_0'
pendesk_B[0].instance_id = 'pendesk_B_0'
medicalbottle_A[0].instance_id = 'medicalbottle_A_0'
mirror_B[0].instance_id = 'mirror_B_0'
medicalbottle_B[0].instance_id = 'medicalbottle_B_0'
bookchair_A[0].instance_id = 'bookchair_A_0'
mirror_C[0].instance_id = 'mirror_C_0'
phone[0].instance_id = 'phone_0'
lampnightstand[0].instance_id = 'lampnightstand_0'
floorlamp_B[0].instance_id = 'floorlamp_B_0'
cupnightstand_B[0].instance_id = 'cupnightstand_B_0'
medicationbottle_A[0].instance_id = 'medicationbottle_A_0'
trashbin_A[0].instance_id = 'trashbin_A_0'
medicalmonitor[0].instance_id = 'medicalmonitor_0'
bed[0].instance_id = 'bed_0'
nightstand[0].instance_id = 'nightstand_0'
wastebin[0].instance_id = 'wastebin_0'
medicalchart[0].instance_id = 'medicalchart_0'
medicationbottle_B[0].instance_id = 'medicationbottle_B_0'
bookchair_B[0].instance_id = 'bookchair_B_0'
bookdesk_C[0].instance_id = 'bookdesk_C_0'
plant_B[0].instance_id = 'plant_B_0'
pillow[0].instance_id = 'pillow_0'
coffeecup[0].instance_id = 'coffeecup_0'
plantcabinet[0].instance_id = 'plantcabinet_0'
floorlamp_C[0].instance_id = 'floorlamp_C_0'
plant_C[0].instance_id = 'plant_C_0'
pen[0].instance_id = 'pen_0'
medicinebottle_B[0].instance_id = 'medicinebottle_B_0'
artwork_B[0].instance_id = 'artwork_B_0'
plant_D[0].instance_id = 'plant_D_0'
purifier[0].instance_id = 'purifier_0'
floorlamp_D[0].instance_id = 'floorlamp_D_0'
booknightstand[0].instance_id = 'booknightstand_0'
trashbin_B[0].instance_id = 'trashbin_B_0'
medicinebottle_C[0].instance_id = 'medicinebottle_C_0'
artwork_C[0].instance_id = 'artwork_C_0'
artwork_D[0].instance_id = 'artwork_D_0'
mirror_D[0].instance_id = 'mirror_D_0'
chair[0].instance_id = 'chair_0'
cupdesk_A[0].instance_id = 'cupdesk_A_0'
cupdesk_B[0].instance_id = 'cupdesk_B_0'
medicalequipment_B[0].instance_id = 'medicalequipment_B_0'
recyclebin[0].instance_id = 'recyclebin_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

medicinebottle_A[0].position = [1.33947748339285, 1.1874454884906034, 0.08]
medicinebottle_A[0].rotation = [0, 0, 0]
cupnightstand_A[0].position = [1.4885851307329738, 1.9843447483350085, 0.055]
cupnightstand_A[0].rotation = [0, 0, 0]
medicalequipment_A[0].position = [2.920067552996656, 4.740797502261543, 0.375]
medicalequipment_A[0].rotation = [0, 0, 0]
floorlamp_A[0].position = [1.361981705079104, 1.0371978971407088, 0.825]
floorlamp_A[0].rotation = [0, 0, 0]
artwork_A[0].position = [3.2371499360773575, 3.645067837445427, 0.35]
artwork_A[0].rotation = [0, 0, 0]
ivstand[0].position = [3.775905453184022, 4.071056327493788, 1.0]
ivstand[0].rotation = [0, 0, 0]
heater[0].position = [2.37453282971487, 1.4874829484236956, 0.2]
heater[0].rotation = [0, 0, 0]
pendesk_A[0].position = [1.9463609786652083, 3.1284505279572086, 0.006]
pendesk_A[0].rotation = [0, 0, 0]
stool[0].position = [3.7909158556395, 1.02272540780887, 0.23]
stool[0].rotation = [0, 0, 0]
bookdesk_A[0].position = [1.163257611340642, 4.762538373310011, 0.0125]
bookdesk_A[0].rotation = [0, 0, 0]
bookdesk_B[0].position = [3.3275806156405325, 2.5625680512434634, 0.0125]
bookdesk_B[0].rotation = [0, 0, 0]
desk[0].position = [3.948790218406401, 3.018246926523945, 0.375]
desk[0].rotation = [0, 0, 0]
notebook[0].position = [4.070247063569917, 4.814615975998565, 0.0075]
notebook[0].rotation = [0, 0, 0]
cabinet[0].position = [1.1404316104358636, 3.739880976666296, 0.9]
cabinet[0].rotation = [0, 0, 0]
plant_A[0].position = [3.6947761289489174, 1.770555624921738, 0.375]
plant_A[0].rotation = [0, 0, 0]
book[0].position = [3.022433156540732, 3.6337401385717123, 0.015]
book[0].rotation = [0, 0, 0]
sofa[0].position = [2.6386446502567598, 2.6278084909275288, 0.39]
sofa[0].rotation = [0, 0, 0]
mirror_A[0].position = [1.706414908217395, 0.376774742412716, 0.25]
mirror_A[0].rotation = [0, 0, 0]
pendesk_B[0].position = [1.1436495095770765, 3.6685050301921596, 0.006]
pendesk_B[0].rotation = [0, 0, 0]
medicalbottle_A[0].position = [1.7894647775350168, 4.0150235822900475, 0.0425]
medicalbottle_A[0].rotation = [0, 0, 0]
mirror_B[0].position = [1.2074791614543217, 4.563299261648756, 0.325]
mirror_B[0].rotation = [0, 0, 0]
medicalbottle_B[0].position = [2.2228597766189235, 4.432447586088692, 0.0425]
medicalbottle_B[0].rotation = [0, 0, 0]
bookchair_A[0].position = [3.922907107736662, 1.081547769603604, 0.0075]
bookchair_A[0].rotation = [0, 0, 0]
mirror_C[0].position = [1.2253133415609232, 1.3718796075803774, 0.3]
mirror_C[0].rotation = [0, 0, 0]
phone[0].position = [0.9754192460966379, 2.1292302451482192, 0.0045]
phone[0].rotation = [0, 0, 0]
lampnightstand[0].position = [0.19829662979759766, 0.8820071792524764, 0.2]
lampnightstand[0].rotation = [0, 0, 0]
floorlamp_B[0].position = [1.1571458935293788, 1.6421411337571006, 0.8]
floorlamp_B[0].rotation = [0, 0, 0]
cupnightstand_B[0].position = [3.6297608166772304, 1.0666444725307263, 0.09]
cupnightstand_B[0].rotation = [0, 0, 0]
medicationbottle_A[0].position = [3.2330137433509125, 0.7669746885015727, 0.045]
medicationbottle_A[0].rotation = [0, 0, 0]
trashbin_A[0].position = [0.8706909674838625, 4.65000588414008, 0.175]
trashbin_A[0].rotation = [0, 0, 0]
medicalmonitor[0].position = [2.1999756861011073, 3.396837500271352, 0.15]
medicalmonitor[0].rotation = [0, 0, 0]
bed[0].position = [3.308829514576734, 1.8372862938541128, 0.525]
bed[0].rotation = [0, 0, 0]
nightstand[0].position = [1.1298239261136063, 3.6609395498530035, 0.325]
nightstand[0].rotation = [0, 0, 0]
wastebin[0].position = [2.583194935761008, 4.622570805941483, 0.19]
wastebin[0].rotation = [0, 0, 0]
medicalchart[0].position = [2.5699900348718976, 3.711755806538993, 0.165]
medicalchart[0].rotation = [0, 0, 0]
medicationbottle_B[0].position = [0.09182188090554406, 0.15337386646287587, 0.05]
medicationbottle_B[0].rotation = [0, 0, 0]
bookchair_B[0].position = [3.9973984412767374, 2.4119377133577786, 0.0125]
bookchair_B[0].rotation = [0, 0, 0]
bookdesk_C[0].position = [0.29153010229097476, 2.2758607305054124, 0.0125]
bookdesk_C[0].rotation = [0, 0, 0]
plant_B[0].position = [0.1440334170379562, 2.57695242417915, 0.35]
plant_B[0].rotation = [0, 0, 0]
pillow[0].position = [1.3475966814746905, 3.6907310276698353, 0.075]
pillow[0].rotation = [0, 0, 0]
coffeecup[0].position = [0.8046987340384354, 0.0888247647694207, 0.04]
coffeecup[0].rotation = [0, 0, 0]
plantcabinet[0].position = [4.117516579493013, 2.2737531615404567, 0.175]
plantcabinet[0].rotation = [0, 0, 0]
floorlamp_C[0].position = [2.5683969717309187, 1.365782148015412, 0.825]
floorlamp_C[0].rotation = [0, 0, 0]
plant_C[0].position = [3.7039058094575577, 2.9590771858981695, 0.375]
plant_C[0].rotation = [0, 0, 0]
pen[0].position = [0.37360937268220673, 0.5711899588546249, 0.005]
pen[0].rotation = [0, 0, 0]
medicinebottle_B[0].position = [3.813700848885566, 3.642535908039766, 0.08]
medicinebottle_B[0].rotation = [0, 0, 0]
artwork_B[0].position = [2.874750396851814, 4.425444985385421, 0.225]
artwork_B[0].rotation = [0, 0, 0]
plant_D[0].position = [3.5147978245657345, 4.780652287279094, 0.325]
plant_D[0].rotation = [0, 0, 0]
purifier[0].position = [3.0359969194805534, 2.0104068285812575, 0.3]
purifier[0].rotation = [0, 0, 0]
floorlamp_D[0].position = [0.2960779312496323, 4.523675559424585, 0.85]
floorlamp_D[0].rotation = [0, 0, 0]
booknightstand[0].position = [0.9362773576158074, 1.308781563890996, 0.01]
booknightstand[0].rotation = [0, 0, 0]
trashbin_B[0].position = [4.166209947788352, 0.09503636648886427, 0.16]
trashbin_B[0].rotation = [0, 0, 0]
medicinebottle_C[0].position = [2.925724006854234, 0.8844487809540386, 0.08]
medicinebottle_C[0].rotation = [0, 0, 0]
artwork_C[0].position = [2.574567554525465, 0.7630615029391441, 0.325]
artwork_C[0].rotation = [0, 0, 0]
artwork_D[0].position = [1.6174334493674654, 0.03050796055831695, 0.325]
artwork_D[0].rotation = [0, 0, 0]
mirror_D[0].position = [3.464858330942305, 0.7989548060747126, 0.325]
mirror_D[0].rotation = [0, 0, 0]
chair[0].position = [1.880696762103602, 0.5617666007503963, 0.425]
chair[0].rotation = [0, 0, 0]
cupdesk_A[0].position = [2.1424255329187996, 2.5682782776671678, 0.05]
cupdesk_A[0].rotation = [0, 0, 0]
cupdesk_B[0].position = [2.3224547243693694, 1.3851980554016408, 0.05]
cupdesk_B[0].rotation = [0, 0, 0]
medicalequipment_B[0].position = [3.5157703788617862, 2.1864549869336063, 0.2]
medicalequipment_B[0].rotation = [0, 0, 0]
recyclebin[0].position = [0.526447822938728, 3.064920922951363, 0.21]
recyclebin[0].rotation = [0, 0, 0]
medicinebottle_A[0].position = [1.33947748339285, 1.1874454884906034, 0.08]
medicinebottle_A[0].rotation = [0, 0, 0]
cupnightstand_A[0].position = [1.4885851307329738, 1.9843447483350085, 0.055]
cupnightstand_A[0].rotation = [0, 0, 0]
medicalequipment_A[0].position = [2.920067552996656, 4.740797502261543, 0.375]
medicalequipment_A[0].rotation = [0, 0, 0]
floorlamp_A[0].position = [1.361981705079104, 1.0371978971407088, 0.825]
floorlamp_A[0].rotation = [0, 0, 0]
artwork_A[0].position = [3.2371499360773575, 3.645067837445427, 0.35]
artwork_A[0].rotation = [0, 0, 0]
ivstand[0].position = [3.775905453184022, 4.071056327493788, 1.0]
ivstand[0].rotation = [0, 0, 0]
heater[0].position = [2.37453282971487, 1.4874829484236956, 0.2]
heater[0].rotation = [0, 0, 0]
pendesk_A[0].position = [1.9463609786652083, 3.1284505279572086, 0.006]
pendesk_A[0].rotation = [0, 0, 0]
stool[0].position = [3.7909158556395, 1.02272540780887, 0.23]
stool[0].rotation = [0, 0, 0]
bookdesk_A[0].position = [1.163257611340642, 4.762538373310011, 0.0125]
bookdesk_A[0].rotation = [0, 0, 0]
bookdesk_B[0].position = [3.3275806156405325, 2.5625680512434634, 0.0125]
bookdesk_B[0].rotation = [0, 0, 0]
desk[0].position = [3.948790218406401, 3.018246926523945, 0.375]
desk[0].rotation = [0, 0, 0]
notebook[0].position = [4.070247063569917, 4.814615975998565, 0.0075]
notebook[0].rotation = [0, 0, 0]
cabinet[0].position = [1.1404316104358636, 3.739880976666296, 0.9]
cabinet[0].rotation = [0, 0, 0]
plant_A[0].position = [3.6947761289489174, 1.770555624921738, 0.375]
plant_A[0].rotation = [0, 0, 0]
book[0].position = [3.022433156540732, 3.6337401385717123, 0.015]
book[0].rotation = [0, 0, 0]
sofa[0].position = [2.6386446502567598, 2.6278084909275288, 0.39]
sofa[0].rotation = [0, 0, 0]
mirror_A[0].position = [1.706414908217395, 0.376774742412716, 0.25]
mirror_A[0].rotation = [0, 0, 0]
pendesk_B[0].position = [1.1436495095770765, 3.6685050301921596, 0.006]
pendesk_B[0].rotation = [0, 0, 0]
medicalbottle_A[0].position = [1.7894647775350168, 4.0150235822900475, 0.0425]
medicalbottle_A[0].rotation = [0, 0, 0]
mirror_B[0].position = [1.2074791614543217, 4.563299261648756, 0.325]
mirror_B[0].rotation = [0, 0, 0]
medicalbottle_B[0].position = [2.2228597766189235, 4.432447586088692, 0.0425]
medicalbottle_B[0].rotation = [0, 0, 0]
bookchair_A[0].position = [3.922907107736662, 1.081547769603604, 0.0075]
bookchair_A[0].rotation = [0, 0, 0]
mirror_C[0].position = [1.2253133415609232, 1.3718796075803774, 0.3]
mirror_C[0].rotation = [0, 0, 0]
phone[0].position = [0.9754192460966379, 2.1292302451482192, 0.0045]
phone[0].rotation = [0, 0, 0]
lampnightstand[0].position = [0.19829662979759766, 0.8820071792524764, 0.2]
lampnightstand[0].rotation = [0, 0, 0]
floorlamp_B[0].position = [1.1571458935293788, 1.6421411337571006, 0.8]
floorlamp_B[0].rotation = [0, 0, 0]
cupnightstand_B[0].position = [3.6297608166772304, 1.0666444725307263, 0.09]
cupnightstand_B[0].rotation = [0, 0, 0]
medicationbottle_A[0].position = [3.2330137433509125, 0.7669746885015727, 0.045]
medicationbottle_A[0].rotation = [0, 0, 0]
trashbin_A[0].position = [0.8706909674838625, 4.65000588414008, 0.175]
trashbin_A[0].rotation = [0, 0, 0]
medicalmonitor[0].position = [2.1999756861011073, 3.396837500271352, 0.15]
medicalmonitor[0].rotation = [0, 0, 0]
bed[0].position = [3.308829514576734, 1.8372862938541128, 0.525]
bed[0].rotation = [0, 0, 0]
nightstand[0].position = [1.1298239261136063, 3.6609395498530035, 0.325]
nightstand[0].rotation = [0, 0, 0]
wastebin[0].position = [2.583194935761008, 4.622570805941483, 0.19]
wastebin[0].rotation = [0, 0, 0]
medicalchart[0].position = [2.5699900348718976, 3.711755806538993, 0.165]
medicalchart[0].rotation = [0, 0, 0]
medicationbottle_B[0].position = [0.09182188090554406, 0.15337386646287587, 0.05]
medicationbottle_B[0].rotation = [0, 0, 0]
bookchair_B[0].position = [3.9973984412767374, 2.4119377133577786, 0.0125]
bookchair_B[0].rotation = [0, 0, 0]
bookdesk_C[0].position = [0.29153010229097476, 2.2758607305054124, 0.0125]
bookdesk_C[0].rotation = [0, 0, 0]
plant_B[0].position = [0.1440334170379562, 2.57695242417915, 0.35]
plant_B[0].rotation = [0, 0, 0]
pillow[0].position = [1.3475966814746905, 3.6907310276698353, 0.075]
pillow[0].rotation = [0, 0, 0]
coffeecup[0].position = [0.8046987340384354, 0.0888247647694207, 0.04]
coffeecup[0].rotation = [0, 0, 0]
plantcabinet[0].position = [4.117516579493013, 2.2737531615404567, 0.175]
plantcabinet[0].rotation = [0, 0, 0]
floorlamp_C[0].position = [2.5683969717309187, 1.365782148015412, 0.825]
floorlamp_C[0].rotation = [0, 0, 0]
plant_C[0].position = [3.7039058094575577, 2.9590771858981695, 0.375]
plant_C[0].rotation = [0, 0, 0]
pen[0].position = [0.37360937268220673, 0.5711899588546249, 0.005]
pen[0].rotation = [0, 0, 0]
medicinebottle_B[0].position = [3.813700848885566, 3.642535908039766, 0.08]
medicinebottle_B[0].rotation = [0, 0, 0]
artwork_B[0].position = [2.874750396851814, 4.425444985385421, 0.225]
artwork_B[0].rotation = [0, 0, 0]
plant_D[0].position = [3.5147978245657345, 4.780652287279094, 0.325]
plant_D[0].rotation = [0, 0, 0]
purifier[0].position = [3.0359969194805534, 2.0104068285812575, 0.3]
purifier[0].rotation = [0, 0, 0]
floorlamp_D[0].position = [0.2960779312496323, 4.523675559424585, 0.85]
floorlamp_D[0].rotation = [0, 0, 0]
booknightstand[0].position = [0.9362773576158074, 1.308781563890996, 0.01]
booknightstand[0].rotation = [0, 0, 0]
trashbin_B[0].position = [4.166209947788352, 0.09503636648886427, 0.16]
trashbin_B[0].rotation = [0, 0, 0]
medicinebottle_C[0].position = [2.925724006854234, 0.8844487809540386, 0.08]
medicinebottle_C[0].rotation = [0, 0, 0]
artwork_C[0].position = [2.574567554525465, 0.7630615029391441, 0.325]
artwork_C[0].rotation = [0, 0, 0]
artwork_D[0].position = [1.6174334493674654, 0.03050796055831695, 0.325]
artwork_D[0].rotation = [0, 0, 0]
mirror_D[0].position = [3.464858330942305, 0.7989548060747126, 0.325]
mirror_D[0].rotation = [0, 0, 0]
chair[0].position = [1.880696762103602, 0.5617666007503963, 0.425]
chair[0].rotation = [0, 0, 0]
cupdesk_A[0].position = [2.1424255329187996, 2.5682782776671678, 0.05]
cupdesk_A[0].rotation = [0, 0, 0]
cupdesk_B[0].position = [2.3224547243693694, 1.3851980554016408, 0.05]
cupdesk_B[0].rotation = [0, 0, 0]
medicalequipment_B[0].position = [3.5157703788617862, 2.1864549869336063, 0.2]
medicalequipment_B[0].rotation = [0, 0, 0]
recyclebin[0].position = [0.526447822938728, 3.064920922951363, 0.21]
recyclebin[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the explicit wall coordinates: the room occupies [0, 4.2] x [0, 5].
# Keep the entrance at x=0.52..1.42, y=5 and its approach unobstructed.
# Fixed layout anchors preserve the carefully separated footprints, including
# the door approach. Support constraints additionally maintain tabletop heights.

def _place(asset_group, x, y, z=None, yaw=0, support=None, wall=None):
    instance = asset_group[0]
    if z is None:
        z = asset_group.size[2] / 2
    instance.position = [x, y, z]
    instance.rotation = [0, 0, radians(yaw)]

    # Specify support first, so its vertical relationship takes precedence.
    if support is not None:
        solver.on_top_of(instance, support[0])

    solver.distance_constraint(
        instance,
        AssetInstance(position=[x, y, z]),
        0, 0, weight=10
    )
    solver.align_with(
        instance,
        AssetInstance(
            position=[x, y, z],
            rotation=[0, 0, radians(yaw)]
        ),
        angle=0
    )
    if wall is not None:
        solver.against_wall(instance, wall)


# Patient zone: the bed's long axis runs east-west.
# Plants flank its north and south sides, with clear gaps to the bed.
_place(bed, 2.80, 2.65)
_place(plant_A, 2.80, 1.75)
_place(plant_C, 2.80, 3.55)
_place(nightstand, 3.85, 3.65, yaw=180)

# The pillow rests toward the east/head end.
_place(pillow, 3.45, 2.65, 1.125, support=bed)

# Bedside equipment stays outside the bed and plant footprints.
_place(ivstand, 1.55, 3.55)
_place(medicalequipment_A, 3.98, 1.40, yaw=180)
_place(medicalmonitor, 3.98, 1.40, 0.90, yaw=180,
       support=medicalequipment_A)
_place(stool, 1.30, 2.60)
_place(wastebin, 3.98, 2.00)

# Separate items across the nightstand surface; the requested medication
# bottle is explicitly supported by the nightstand.
_place(lampnightstand, 3.98, 3.79, 0.85, support=nightstand)
_place(booknightstand, 3.72, 3.80, 0.66, support=nightstand)
_place(cupnightstand_A, 3.63, 3.47, 0.705, support=nightstand)
_place(cupnightstand_B, 3.75, 3.47, 0.74, support=nightstand)
_place(medicationbottle_A, 3.86, 3.46, 0.695, support=nightstand)
_place(medicationbottle_B, 3.96, 3.46, 0.70, support=nightstand)

# Work zone along the west wall, with the chair facing the desk.
_place(desk, 0.30, 1.80, wall=walls[2])
_place(chair, 1.05, 1.80, yaw=180)
solver.point_towards(chair[0], desk[0])

# Distribute books and stationery rather than overlapping them.
_place(bookdesk_A, 0.16, 1.40, 0.765, support=desk)
_place(bookdesk_B, 0.16, 1.70, 0.765, support=desk)
_place(bookdesk_C, 0.16, 2.00, 0.765, support=desk)
_place(notebook, 0.16, 2.25, 0.755, support=desk)
_place(pendesk_A, 0.32, 1.40, 0.755, support=desk)
_place(pendesk_B, 0.32, 1.70, 0.755, support=desk)
_place(pen, 0.46, 2.32, 0.755, support=desk)
_place(cupdesk_A, 0.46, 1.40, 0.80, support=desk)
_place(cupdesk_B, 0.46, 1.65, 0.80, support=desk)
_place(coffeecup, 0.46, 1.90, 0.79, support=desk)
_place(phone, 0.43, 2.15, 0.755, support=desk)

# A small reading stack on the patient chair.
_place(bookchair_A, 1.05, 1.80, 0.855, yaw=180, support=chair)
_place(bookchair_B, 1.05, 1.80, 0.875, yaw=180,
       support=bookchair_A)

# Visitor seating, facing into the room, does not extend into the entrance.
_place(sofa, 0.375, 3.35, wall=walls[2])
_place(book, 0.40, 3.70, 0.795, support=sofa)

# Storage along the south wall. Rotating the cabinet makes its wider
# dimension run along that wall.
_place(cabinet, 2.90, 0.20, yaw=90, wall=walls[3])
_place(plantcabinet, 2.68, 0.20, 1.975, yaw=90, support=cabinet)

# Bottles occupy separate positions on the cabinet top. No unsupported
# interior shelves are assumed.
_place(medicinebottle_A, 2.90, 0.11, 1.88, support=cabinet)
_place(medicinebottle_B, 3.02, 0.11, 1.88, support=cabinet)
_place(medicinebottle_C, 3.14, 0.11, 1.88, support=cabinet)
_place(medicalbottle_A, 2.94, 0.29, 1.845, support=cabinet)
_place(medicalbottle_B, 3.10, 0.29, 1.845, support=cabinet)

_place(medicalequipment_B, 3.65, 0.65, yaw=180)
_place(plant_B, 1.70, 0.30)
_place(plant_D, 3.50, 4.65)
_place(purifier, 2.10, 4.75, yaw=-90)

# Lamps are distributed around the perimeter, away from the door approach.
_place(floorlamp_A, 0.20, 0.25, yaw=45)
_place(floorlamp_B, 4.00, 0.25, yaw=135)
_place(floorlamp_C, 0.20, 4.65, yaw=-45)
_place(floorlamp_D, 4.00, 4.70, yaw=-135)

# Keep the heater separated from plants, furniture, and the entrance.
_place(heater, 0.20, 0.80)
_place(trashbin_A, 0.95, 0.25, yaw=90)
_place(trashbin_B, 0.75, 1.00)
_place(recyclebin, 2.20, 0.25, yaw=90)

# Wall-mounted pieces use explicit elevated centers and wall constraints.
# Their thin local x dimension is perpendicular to the supporting wall.
_place(mirror_A, 0.015, 0.70, 1.60, wall=walls[2])
_place(artwork_A, 0.015, 1.65, 1.60, wall=walls[2])
_place(mirror_B, 0.015, 2.60, 1.65, wall=walls[2])
_place(artwork_B, 0.015, 3.40, 1.70, wall=walls[2])
_place(mirror_C, 0.015, 4.20, 1.65, wall=walls[2])

_place(artwork_C, 4.185, 0.80, 1.60, yaw=180, wall=walls[0])
_place(mirror_D, 4.190, 1.70, 1.65, yaw=180, wall=walls[0])
_place(artwork_D, 4.185, 3.00, 1.70, yaw=180, wall=walls[0])
_place(medicalchart, 4.190, 2.25, 1.60, yaw=180, wall=walls[0])

solver.constraints = []
bookchair_B[0].position = [1.0499999523162842, 1.7999999523162842, 0.875]
bookchair_B[0].rotation = [0, 0, -3.1290262823329655]
bookchair_B[0].optimize = 2
floorlamp_D[0].position = [4.0, 4.699999809265137, 0.8500000238418579]
floorlamp_D[0].rotation = [0, 0, -2.3467697250267454]
floorlamp_D[0].optimize = 2
chair[0].position = [1.0499999523162842, 1.7999999523162842, 0.42500001192092896]
chair[0].rotation = [0, 0, -3.125884689672577]
chair[0].optimize = 2
plant_D[0].position = [3.5, 4.650000095367432, 0.32499998807907104]
plant_D[0].rotation = [0, 0, 0.00942477746072377]
plant_D[0].optimize = 2
medicalbottle_A[0].position = [2.940000057220459, 0.28999999165534973, 1.84499990940094]
medicalbottle_A[0].rotation = [0, 0, 0.01256637125682779]
medicalbottle_A[0].optimize = 2
mirror_C[0].position = [0.006743067875504494, 4.199999809265137, 0.30000001192092896]
mirror_C[0].rotation = [0, 0, 0.002540920594857827]
mirror_C[0].optimize = 2
cupnightstand_B[0].position = [3.75, 3.4700000286102295, 0.7400000095367432]
cupnightstand_B[0].rotation = [0, 0, 0.01256637125682779]
cupnightstand_B[0].optimize = 2
cupdesk_A[0].position = [0.46000000834465027, 1.399999976158142, 0.800000011920929]
cupdesk_A[0].rotation = [0, 0, 0.01256637125682779]
cupdesk_A[0].optimize = 2
bookdesk_C[0].position = [0.1599999964237213, 2.0, 0.7649999856948853]
bookdesk_C[0].rotation = [0, 0, 0.01256637125682779]
bookdesk_C[0].optimize = 2
sofa[0].position = [0.37594908475875854, 3.3499999046325684, 0.38999998569488525]
sofa[0].rotation = [0, 0, 0.005651512303644438]
sofa[0].optimize = 2
recyclebin[0].position = [2.200000047683716, 0.25, 0.20999999344348907]
recyclebin[0].rotation = [0, 0, 1.5802211042556205]
recyclebin[0].optimize = 2
booknightstand[0].position = [3.7200000286102295, 3.799999952316284, 0.6599999666213989]
booknightstand[0].rotation = [0, 0, 0.01256637125682779]
booknightstand[0].optimize = 2
plantcabinet[0].position = [2.680000066757202, 0.20000000298023224, 1.9749999046325684]
plantcabinet[0].rotation = [0, 0, 1.5833626980517244]
plantcabinet[0].optimize = 2
bookdesk_A[0].position = [0.1599999964237213, 1.399999976158142, 0.7649999856948853]
bookdesk_A[0].rotation = [0, 0, 0.01256637125682779]
bookdesk_A[0].optimize = 2
phone[0].position = [0.4300000071525574, 2.1500000953674316, 0.7549999952316284]
phone[0].rotation = [0, 0, 0.01256637125682779]
phone[0].optimize = 2
medicalmonitor[0].position = [3.9800000190734863, 1.399999976158142, 0.8999999761581421]
medicalmonitor[0].rotation = [0, 0, -3.1290262823329655]
medicalmonitor[0].optimize = 2
floorlamp_C[0].position = [0.2262641340494156, 4.650000095367432, 0.824999988079071]
floorlamp_C[0].rotation = [0, 0, -0.7759733982318487]
floorlamp_C[0].optimize = 2
cupnightstand_A[0].position = [3.630000114440918, 3.4700000286102295, 0.7049999833106995]
cupnightstand_A[0].rotation = [0, 0, 0.01256637125682779]
cupnightstand_A[0].optimize = 2
artwork_C[0].position = [4.192923069000244, 0.800000011920929, 0.32499998807907104]
artwork_C[0].rotation = [0, 0, -3.1390517323726885]
artwork_C[0].optimize = 2
medicalbottle_B[0].position = [3.0999999046325684, 0.28999999165534973, 1.84499990940094]
medicalbottle_B[0].rotation = [0, 0, 0.01256637125682779]
medicalbottle_B[0].optimize = 2
bookchair_A[0].position = [1.0499999523162842, 1.7999999523162842, 0.8550000190734863]
bookchair_A[0].rotation = [0, 0, -3.125884689672577]
bookchair_A[0].optimize = 2
floorlamp_B[0].position = [3.987877607345581, 0.25, 0.800000011920929]
floorlamp_B[0].rotation = [0, 0, 2.3656192553579443]
floorlamp_B[0].optimize = 2
medicationbottle_B[0].position = [3.9600000381469727, 3.4600000381469727, 0.699999988079071]
medicationbottle_B[0].rotation = [0, 0, 0.01256637125682779]
medicationbottle_B[0].optimize = 2
cupdesk_B[0].position = [0.46000000834465027, 1.649999976158142, 0.800000011920929]
cupdesk_B[0].rotation = [0, 0, 0.01256637125682779]
cupdesk_B[0].optimize = 2
medicinebottle_C[0].position = [3.140000104904175, 0.10999999940395355, 1.8799999952316284]
medicinebottle_C[0].rotation = [0, 0, 0.01256637125682779]
medicinebottle_C[0].optimize = 2
medicalequipment_A[0].position = [3.9800000190734863, 1.399999976158142, 0.375]
medicalequipment_A[0].rotation = [0, 0, -3.1290262823329655]
medicalequipment_A[0].optimize = 2
heater[0].position = [0.20000000298023224, 0.800000011920929, 0.20000000298023224]
heater[0].rotation = [0, 0, 0.00942477746072377]
heater[0].optimize = 2
nightstand[0].position = [3.8499999046325684, 3.6500000953674316, 0.32499998807907104]
nightstand[0].rotation = [0, 0, -3.113318319178201]
nightstand[0].optimize = 2
trashbin_A[0].position = [0.949999988079071, 0.25, 0.17499999701976776]
trashbin_A[0].rotation = [0, 0, 1.5802211042556205]
trashbin_A[0].optimize = 2
notebook[0].position = [0.1599999964237213, 2.25, 0.7549999952316284]
notebook[0].rotation = [0, 0, 0.01256637125682779]
notebook[0].optimize = 2
cabinet[0].position = [2.9000000953674316, 0.20168058574199677, 0.8999999761581421]
cabinet[0].rotation = [0, 0, 1.5920023283442204]
cabinet[0].optimize = 2
plant_B[0].position = [1.7000000476837158, 0.30000001192092896, 0.3499999940395355]
plant_B[0].rotation = [0, 0, 0.00942477746072377]
plant_B[0].optimize = 2
artwork_D[0].position = [4.19326639175415, 3.0, 0.32499998807907104]
artwork_D[0].rotation = [0, 0, -3.1390517332948615]
artwork_D[0].optimize = 2
pendesk_B[0].position = [0.3199999928474426, 1.7000000476837158, 0.7549999952316284]
pendesk_B[0].rotation = [0, 0, 0.01256637125682779]
pendesk_B[0].optimize = 2
medicinebottle_A[0].position = [2.9000000953674316, 0.10999999940395355, 1.8799999952316284]
medicinebottle_A[0].rotation = [0, 0, 0.01256637125682779]
medicinebottle_A[0].optimize = 2
medicalequipment_B[0].position = [3.6500000953674316, 0.6499999761581421, 0.20000000298023224]
medicalequipment_B[0].rotation = [0, 0, -3.1321678761290697]
medicalequipment_B[0].optimize = 2
coffeecup[0].position = [0.46000000834465027, 1.899999976158142, 0.7900000214576721]
coffeecup[0].rotation = [0, 0, 0.01256637125682779]
coffeecup[0].optimize = 2
lampnightstand[0].position = [3.9800000190734863, 3.7899999618530273, 0.8499999642372131]
lampnightstand[0].rotation = [0, 0, 0.01256637125682779]
lampnightstand[0].optimize = 2
artwork_A[0].position = [0.00674373097717762, 1.649999976158142, 0.3499999940395355]
artwork_A[0].rotation = [0, 0, 0.002540921217104852]
artwork_A[0].optimize = 2
mirror_B[0].position = [0.006743067875504494, 2.5999999046325684, 0.32499998807907104]
mirror_B[0].rotation = [0, 0, 0.002540920594857827]
mirror_B[0].optimize = 2
book[0].position = [0.4000000059604645, 3.700000047683716, 0.7949999570846558]
book[0].rotation = [0, 0, 0.01256637125682779]
book[0].optimize = 2
wastebin[0].position = [3.9800000190734863, 2.0, 0.1899999976158142]
wastebin[0].rotation = [0, 0, 0.00942477746072377]
wastebin[0].optimize = 2
stool[0].position = [1.2999999523162842, 2.5999999046325684, 0.23000000417232513]
stool[0].rotation = [0, 0, 0.00942477746072377]
stool[0].optimize = 2
pendesk_A[0].position = [0.3199999928474426, 1.399999976158142, 0.7549999952316284]
pendesk_A[0].rotation = [0, 0, 0.01256637125682779]
pendesk_A[0].optimize = 2
ivstand[0].position = [1.5499999523162842, 3.549999952316284, 1.0]
ivstand[0].rotation = [0, 0, 0.00942477746072377]
ivstand[0].optimize = 2
bed[0].position = [2.799999952316284, 2.6500000953674316, 0.5249999761581421]
bed[0].rotation = [0, 0, 0.01256637125682779]
bed[0].optimize = 2
medicalchart[0].position = [4.196560382843018, 2.25, 0.16500000655651093]
medicalchart[0].rotation = [0, 0, -3.1390517311505883]
medicalchart[0].optimize = 2
mirror_D[0].position = [4.1974101066589355, 1.7000000476837158, 0.32499998807907104]
mirror_D[0].rotation = [0, 0, -3.139051732072762]
mirror_D[0].optimize = 2
floorlamp_A[0].position = [0.24747639894485474, 0.25, 0.824999988079071]
floorlamp_A[0].rotation = [0, 0, 0.7948229285630478]
floorlamp_A[0].optimize = 2
plant_A[0].position = [2.799999952316284, 1.75, 0.375]
plant_A[0].rotation = [0, 0, 0.00942477746072377]
plant_A[0].optimize = 2
medicationbottle_A[0].position = [3.859999895095825, 3.4600000381469727, 0.6949999928474426]
medicationbottle_A[0].rotation = [0, 0, 0.01256637125682779]
medicationbottle_A[0].optimize = 2
medicinebottle_B[0].position = [3.0199999809265137, 0.10999999940395355, 1.8799999952316284]
medicinebottle_B[0].rotation = [0, 0, 0.01256637125682779]
medicinebottle_B[0].optimize = 2
trashbin_B[0].position = [0.75, 1.0, 0.1599999964237213]
trashbin_B[0].rotation = [0, 0, 0.00942477746072377]
trashbin_B[0].optimize = 2
plant_C[0].position = [2.799999952316284, 3.549999952316284, 0.375]
plant_C[0].rotation = [0, 0, 0.00942477746072377]
plant_C[0].optimize = 2
pen[0].position = [0.46000000834465027, 2.319999933242798, 0.7549999952316284]
pen[0].rotation = [0, 0, 0.01256637125682779]
pen[0].optimize = 2
desk[0].position = [0.3197677731513977, 1.7999999523162842, 0.375]
desk[0].rotation = [0, 0, 0.03987463273977418]
desk[0].optimize = 2
artwork_B[0].position = [0.0067442841827869415, 3.4000000953674316, 0.22499999403953552]
artwork_B[0].rotation = [0, 0, 0.0025409193727581954]
artwork_B[0].optimize = 2
bookdesk_B[0].position = [0.1599999964237213, 1.7000000476837158, 0.7649999856948853]
bookdesk_B[0].rotation = [0, 0, 0.01256637125682779]
bookdesk_B[0].optimize = 2
purifier[0].position = [2.0999999046325684, 4.75, 0.30000001192092896]
purifier[0].rotation = [0, 0, -1.5613715493341729]
purifier[0].optimize = 2
mirror_A[0].position = [0.0067442841827869415, 0.699999988079071, 0.25]
mirror_A[0].rotation = [0, 0, 0.0025409193727581954]
mirror_A[0].optimize = 2
pillow[0].position = [3.450000047683716, 2.6500000953674316, 1.125]
pillow[0].rotation = [0, 0, 0.01256637125682779]
pillow[0].optimize = 2

