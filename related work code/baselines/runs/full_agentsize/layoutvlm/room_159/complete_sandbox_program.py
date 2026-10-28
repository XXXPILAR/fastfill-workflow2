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
cupnightstand_A = Assets(description="A clear glass urban modern cup with a smooth cylindrical shape, crystal clear body and a thin silver rim, containing a subtle water ripple pattern etched inside", size=[0.08, 0.08, 0.11], placements=[AssetInstance() for _ in range(1)])
medicalequipment_A = Assets(description="A compact urban modern medical equipment unit with a rectangular body, smooth white plastic finish, a small digital display on the front and a subtle ergonomic curve at the top", size=[0.42, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
floorlamp_A = Assets(description="A tall floor lamp with a slender cylindrical pole, a wide conical shade, and a matte black finish, standing upright.", size=[0.42, 0.42, 1.72], placements=[AssetInstance() for _ in range(1)])
artwork_A = Assets(description="A single piece of thin and upright artwork with a rectangular shape, glossy white canvas and a bold abstract black line motif that stretches vertically", size=[0.04, 0.65, 1.10], placements=[AssetInstance() for _ in range(1)])
ivstand = Assets(description="A compact urban modern IV stand with a cylindrical metal pole, angular black powder‑coated base, and a clear acrylic tray that slides vertically", size=[0.55, 0.55, 1.85], placements=[AssetInstance() for _ in range(1)])
heater = Assets(description="A compact urban modern space heater with a square base, brushed metal housing, and a curved front grille that emits a warm amber glow", size=[0.30, 0.38, 0.44], placements=[AssetInstance() for _ in range(1)])
pendesk_A = Assets(description="A sleek urban modern pen with a slim cylindrical body, brushed aluminum finish and a subtle matte black tip, slightly curved for ergonomic grip", size=[0.01, 0.14, 0.01], placements=[AssetInstance() for _ in range(1)])
stool = Assets(description="A lightweight urban modern side stool with a tapered cylindrical seat, matte white finish, and a single chrome leg that bends slightly outward for stability", size=[0.36, 0.36, 0.48], placements=[AssetInstance() for _ in range(1)])
bookdesk_A = Assets(description="A hardcover urban modern book with a rectangular shape, smooth matte finish, deep navy cover and a subtle embossed pattern, featuring slightly rounded edges for a sleek look", size=[0.16, 0.22, 0.03], placements=[AssetInstance() for _ in range(1)])
bookdesk_B = Assets(description="A hardcover urban modern book with a rectangular shape, smooth matte finish, dark gray cover and a subtle embossed pattern, slightly rounded edges for easy handling", size=[0.17, 0.24, 0.04], placements=[AssetInstance() for _ in range(1)])
desk = Assets(description="A minimalist urban modern work desk with a straight‑edged rectangular tabletop, light oak veneer, and slim chrome legs that taper inward", size=[0.65, 1.30, 0.75], placements=[AssetInstance() for _ in range(1)])
notebook = Assets(description="A softcover urban modern notebook with a rectangular shape, pastel teal cover, smooth textured paper and a rounded spine, featuring a thin metal clasp", size=[0.15, 0.21, 0.02], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="A tall urban modern storage cabinet featuring a rectangular box shape, matte gray laminate doors, and a subtle brushed‑metal handle strip across the front", size=[0.42, 0.90, 1.90], placements=[AssetInstance() for _ in range(1)])
plant_A = Assets(description="A potted urban modern plant with a cylindrical pot, matte white finish, and lush green foliage extending outward in a rounded canopy.", size=[0.65, 0.65, 1.10], placements=[AssetInstance() for _ in range(1)])
book = Assets(description="A hardcover urban modern book with a rectangular shape, sleek matte black cover, and a subtle embossed pattern that catches the light", size=[0.18, 0.24, 0.04], placements=[AssetInstance() for _ in range(1)])
sofa = Assets(description="A low‑slung urban modern visitor sofa with a sleek rectangular silhouette, soft teal fabric upholstery, and a subtle tufted pattern along the backrest", size=[0.78, 1.65, 0.78], placements=[AssetInstance() for _ in range(1)])
mirror_A = Assets(description="A single piece of thin and upright mirror with a square shape, polished silver backing and a sleek brushed aluminum frame, reflecting the opposite side of the room", size=[0.04, 0.80, 0.80], placements=[AssetInstance() for _ in range(1)])
pendesk_B = Assets(description="A sleek urban modern pen with a slim cylindrical body, brushed aluminum finish and a subtle matte black tip, slightly curved for ergonomic grip", size=[0.01, 0.14, 0.01], placements=[AssetInstance() for _ in range(1)])
medicalbottle_A = Assets(description="A small cylindrical urban modern medical bottle made of clear plastic, with a bright orange cap and a minimalist label.", size=[0.06, 0.06, 0.11], placements=[AssetInstance() for _ in range(1)])
mirror_B = Assets(description="A single piece of thin and upright mirror with a rectangular outline, polished silver backing, beveled edges and a subtle decorative etched border, giving a sleek reflective surface", size=[0.04, 0.60, 1.00], placements=[AssetInstance() for _ in range(1)])
medicalbottle_B = Assets(description="A small cylindrical urban modern medical bottle made of clear plastic, with a bright orange cap and a minimalist label.", size=[0.06, 0.06, 0.11], placements=[AssetInstance() for _ in range(1)])
bookchair_A = Assets(description="A compact urban modern book with a square softcover, matte charcoal finish and a subtle embossed grid, corners slightly beveled for a modern look", size=[0.20, 0.20, 0.03], placements=[AssetInstance() for _ in range(1)])
mirror_C = Assets(description="A single piece of thin and upright mirror with a rectangular shape, sleek brushed‑silver frame and a beveled edge that catches reflections", size=[0.04, 0.55, 0.90], placements=[AssetInstance() for _ in range(1)])
phone = Assets(description="A slim urban modern smartphone with a rectangular shape, matte black back, glass front and rounded corners, screen facing upward", size=[0.15, 0.07, 0.01], placements=[AssetInstance() for _ in range(1)])
lampnightstand = Assets(description="A contemporary urban modern table lamp with a slender conical shade, matte ivory fabric, and a thin brushed steel base, the shade features a subtle ribbed texture", size=[0.30, 0.30, 0.52], placements=[AssetInstance() for _ in range(1)])
floorlamp_B = Assets(description="A tall slender urban modern floor lamp with a slim cylindrical base, a thin metal pole, and a minimalist conical shade in matte black.", size=[0.32, 0.32, 1.65], placements=[AssetInstance() for _ in range(1)])
cupnightstand_B = Assets(description="A clear glass urban modern cup with a cylindrical shape, thin walls and a short straw inserted, giving a light, airy appearance", size=[0.08, 0.08, 0.20], placements=[AssetInstance() for _ in range(1)])
medicationbottle_A = Assets(description="A small cylindrical urban modern medication bottle made of clear glass, with a pastel green cap and a subtle label.", size=[0.06, 0.06, 0.12], placements=[AssetInstance() for _ in range(1)])
trashbin_A = Assets(description="A compact rectangular trash bin with a smooth matte gray exterior, a hinged lid, and a subtle recessed handle.", size=[0.26, 0.32, 0.42], placements=[AssetInstance() for _ in range(1)])
medicalmonitor = Assets(description="A rectangular urban modern medical monitor with a sleek black frame and a smooth glass screen, featuring subtle brushed metal accents.", size=[0.16, 0.48, 0.38], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="A sleek urban modern hospital bed with a rectangular low‑profile frame, smooth white lacquer finish, stainless steel legs, and a curved headboard that integrates subtle LED accent lighting", size=[2.15, 1.05, 0.68], placements=[AssetInstance() for _ in range(1)])
nightstand = Assets(description="A compact urban modern nightstand with a square footprint, glossy white surface, and a single recessed drawer featuring a hidden magnetic latch", size=[0.45, 0.48, 0.60], placements=[AssetInstance() for _ in range(1)])
wastebin = Assets(description="A sturdy urban modern waste bin with a cylindrical body, matte black finish, and a recessed foot pedal for hands‑free opening", size=[0.30, 0.30, 0.45], placements=[AssetInstance() for _ in range(1)])
medicalchart = Assets(description="A thin upright urban modern medical chart, single piece of paper on a lightweight board, with crisp white background and subtle gray grid lines.", size=[0.02, 0.24, 0.34], placements=[AssetInstance() for _ in range(1)])
medicationbottle_B = Assets(description="A small urban modern medication bottle with a rectangular shape, opaque pastel blue plastic, child‑proof cap slightly ajar, and a subtle embossed label", size=[0.04, 0.07, 0.12], placements=[AssetInstance() for _ in range(1)])
bookchair_B = Assets(description="A hardcover urban modern book with a rectangular shape, smooth matte cover, deep navy color, and a minimalist gold line accent.", size=[0.16, 0.23, 0.03], placements=[AssetInstance() for _ in range(1)])
bookdesk_C = Assets(description="A hardcover urban modern book with a rectangular shape, smooth matte finish, dark gray cover and a subtle embossed pattern, slightly rounded edges for easy handling", size=[0.17, 0.24, 0.04], placements=[AssetInstance() for _ in range(1)])
plant_B = Assets(description="A potted indoor plant with a round terracotta pot, featuring long, glossy green leaves that arch outward.", size=[0.70, 0.70, 1.20], placements=[AssetInstance() for _ in range(1)])
pillow = Assets(description="A rectangular urban modern pillow with a soft plush surface, covered in a muted gray fabric with a subtle geometric pattern.", size=[0.42, 0.65, 0.15], placements=[AssetInstance() for _ in range(1)])
coffeecup = Assets(description="A small cylindrical urban modern coffee cup with a glossy white porcelain finish and a slim silver handle.", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
plantcabinet = Assets(description="A potted urban modern plant with a cylindrical terracotta pot, compact green foliage and a subtle matte finish, sitting on the cabinet top", size=[0.42, 0.42, 0.55], placements=[AssetInstance() for _ in range(1)])
floorlamp_C = Assets(description="A tall urban modern floor lamp with a slender cylindrical shaft, matte black finish, and an angular conical shade that casts a focused light, positioned in the corner near the sofa", size=[0.38, 0.38, 1.70], placements=[AssetInstance() for _ in range(1)])
plant_C = Assets(description="A potted indoor plant with a round terracotta pot, featuring long, glossy green leaves that arch outward.", size=[0.68, 0.68, 1.15], placements=[AssetInstance() for _ in range(1)])
pen = Assets(description="A slender urban modern pen with a smooth cylindrical barrel, brushed aluminum texture, and a subtle chrome tip, slightly tapered at the end for a sleek profile", size=[0.01, 0.14, 0.01], placements=[AssetInstance() for _ in range(1)])
medicinebottle_B = Assets(description="A clear urban modern medicine bottle with a cylindrical shape, smooth transparent glass, amber liquid inside and a sleek silver screw cap, visible through cabinet doors", size=[0.07, 0.07, 0.16], placements=[AssetInstance() for _ in range(1)])
artwork_B = Assets(description="A single piece of thin and upright painting with a rectangular shape, abstract urban modern design, muted gray background and a splash of teal, framed in a narrow black metal frame", size=[0.04, 0.90, 0.65], placements=[AssetInstance() for _ in range(1)])
plant_D = Assets(description="A potted urban modern plant with a cylindrical terracotta pot, matte finish and a small drainage hole, the foliage consists of long, glossy green leaves that arch outward", size=[0.62, 0.62, 1.05], placements=[AssetInstance() for _ in range(1)])
purifier = Assets(description="A streamlined urban modern air purifier with a tall cylindrical core, frosted glass front, and a subtle LED display ring at the top", size=[0.34, 0.34, 0.85], placements=[AssetInstance() for _ in range(1)])
floorlamp_D = Assets(description="A tall urban modern floor lamp with a slender cylindrical shaft, brushed nickel finish and a small circular diffuser at the top, the base is a weighted round disc for stability", size=[0.30, 0.30, 1.75], placements=[AssetInstance() for _ in range(1)])
booknightstand = Assets(description="A paperback urban modern book with a rectangular profile, soft pastel teal cover and a glossy finish, edges slightly rounded for a gentle feel", size=[0.14, 0.21, 0.02], placements=[AssetInstance() for _ in range(1)])
trashbin_B = Assets(description="A rectangular urban modern trash bin with a smooth white plastic body, slightly rounded corners and a discreet lid, located near the desk", size=[0.24, 0.30, 0.40], placements=[AssetInstance() for _ in range(1)])
medicinebottle_C = Assets(description="A clear urban modern medicine bottle with a cylindrical shape, smooth transparent glass, amber liquid inside and a sleek silver screw cap, visible through cabinet doors", size=[0.07, 0.07, 0.16], placements=[AssetInstance() for _ in range(1)])
artwork_C = Assets(description="A single piece of thin and upright painting with a bold abstract composition, featuring a glossy white canvas stretched over a slim wooden frame.", size=[0.04, 0.80, 0.80], placements=[AssetInstance() for _ in range(1)])
artwork_D = Assets(description="A single piece of thin and upright painting with a rectangular shape, smooth canvas surface, soft ivory background and a bold abstract black line motif, framed in a narrow black wood frame", size=[0.04, 0.70, 1.00], placements=[AssetInstance() for _ in range(1)])
mirror_D = Assets(description="A single piece of thin and upright mirror with a sleek silver backing, rectangular shape and a polished reflective surface.", size=[0.03, 0.60, 0.95], placements=[AssetInstance() for _ in range(1)])
chair = Assets(description="A contemporary urban modern patient chair with a rounded backrest, ergonomic curved seat, and a polished aluminum frame finished in soft charcoal", size=[0.68, 0.62, 0.88], placements=[AssetInstance() for _ in range(1)])
cupdesk_A = Assets(description="A ceramic urban modern cup with a sleek cylindrical shape, glossy white surface and a thin brushed metal rim, featuring a small geometric engraving near the base", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
cupdesk_B = Assets(description="A ceramic urban modern cup with a cylindrical shape, glossy white surface and a thin silver rim, slightly tapered toward the base", size=[0.09, 0.09, 0.10], placements=[AssetInstance() for _ in range(1)])
medicalequipment_B = Assets(description="A compact cubic urban modern medical equipment unit with a smooth white exterior and subtle rounded edges.", size=[0.38, 0.42, 0.46], placements=[AssetInstance() for _ in range(1)])
recyclebin = Assets(description="A sleek urban modern recycle bin featuring a slim rectangular shape, bright teal lid, and a brushed‑steel side panel for easy sorting", size=[0.26, 0.32, 0.55], placements=[AssetInstance() for _ in range(1)])

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

medicinebottle_A[0].position = [4.115668263063636, 3.4999144754628997, 0.08]
medicinebottle_A[0].rotation = [0, 0, 0]
cupnightstand_A[0].position = [0.4311412843740209, 1.7165712269581268, 0.055]
cupnightstand_A[0].rotation = [0, 0, 0]
medicalequipment_A[0].position = [1.4301122463591407, 3.558073475484265, 0.41]
medicalequipment_A[0].rotation = [0, 0, 0]
floorlamp_A[0].position = [1.4576351240781953, 1.9055585520625273, 0.86]
floorlamp_A[0].rotation = [0, 0, 0]
artwork_A[0].position = [0.7225122419606239, 2.541386529361811, 0.55]
artwork_A[0].rotation = [0, 0, 0]
ivstand[0].position = [1.4453230288161383, 0.07526979595229633, 0.925]
ivstand[0].rotation = [0, 0, 0]
heater[0].position = [0.9658758609593475, 2.8105834450525697, 0.22]
heater[0].rotation = [0, 0, 0]
pendesk_A[0].position = [1.3401047514810671, 1.833027908710343, 0.006]
pendesk_A[0].rotation = [0, 0, 0]
stool[0].position = [1.0955815712766002, 1.9068328804981878, 0.24]
stool[0].rotation = [0, 0, 0]
bookdesk_A[0].position = [4.1521216677779655, 4.081280313227583, 0.015]
bookdesk_A[0].rotation = [0, 0, 0]
bookdesk_B[0].position = [2.1845537631313587, 3.5632326246562656, 0.0175]
bookdesk_B[0].rotation = [0, 0, 0]
desk[0].position = [2.817626730887832, 2.623272245414831, 0.375]
desk[0].rotation = [0, 0, 0]
notebook[0].position = [2.9012147618357185, 2.16403753096787, 0.009]
notebook[0].rotation = [0, 0, 0]
cabinet[0].position = [2.329063585473247, 2.0989944665422806, 0.95]
cabinet[0].rotation = [0, 0, 0]
plant_A[0].position = [0.5092899684541022, 0.11234511229690769, 0.55]
plant_A[0].rotation = [0, 0, 0]
book[0].position = [2.952716440676107, 0.41371229913131913, 0.0175]
book[0].rotation = [0, 0, 0]
sofa[0].position = [3.467452939659466, 1.0698887237171018, 0.39]
sofa[0].rotation = [0, 0, 0]
mirror_A[0].position = [3.338489714658209, 0.6220149937053376, 0.4]
mirror_A[0].rotation = [0, 0, 0]
pendesk_B[0].position = [0.3268273653556522, 3.7238127204318023, 0.006]
pendesk_B[0].rotation = [0, 0, 0]
medicalbottle_A[0].position = [1.3511107947795538, 1.3587193101076873, 0.055]
medicalbottle_A[0].rotation = [0, 0, 0]
mirror_B[0].position = [1.1491979936330927, 1.292325961471727, 0.5]
mirror_B[0].rotation = [0, 0, 0]
medicalbottle_B[0].position = [1.4326059750290718, 3.093102906449821, 0.055]
medicalbottle_B[0].rotation = [0, 0, 0]
bookchair_A[0].position = [1.063014576937013, 1.6430347306603559, 0.0125]
bookchair_A[0].rotation = [0, 0, 0]
mirror_C[0].position = [1.8181507882858388, 2.711759178878604, 0.45]
mirror_C[0].rotation = [0, 0, 0]
phone[0].position = [3.5923725492374268, 3.872398517370468, 0.0045]
phone[0].rotation = [0, 0, 0]
lampnightstand[0].position = [4.075025737892303, 4.161202291737779, 0.26]
lampnightstand[0].rotation = [0, 0, 0]
floorlamp_B[0].position = [0.18803867533780355, 3.0643939835866885, 0.825]
floorlamp_B[0].rotation = [0, 0, 0]
cupnightstand_B[0].position = [4.146656625082988, 4.090910866872733, 0.1]
cupnightstand_B[0].rotation = [0, 0, 0]
medicationbottle_A[0].position = [2.329938225142534, 4.08703393986877, 0.06]
medicationbottle_A[0].rotation = [0, 0, 0]
trashbin_A[0].position = [1.0780370808010988, 1.137845039393845, 0.21]
trashbin_A[0].rotation = [0, 0, 0]
medicalmonitor[0].position = [3.646308786990489, 1.2531701455411586, 0.19]
medicalmonitor[0].rotation = [0, 0, 0]
bed[0].position = [2.432292300245667, 4.027580875882595, 0.34]
bed[0].rotation = [0, 0, 0]
nightstand[0].position = [0.9780349678114852, 2.853310746521729, 0.3]
nightstand[0].rotation = [0, 0, 0]
wastebin[0].position = [4.188318534783369, 1.7303259007478737, 0.225]
wastebin[0].rotation = [0, 0, 0]
medicalchart[0].position = [2.681775363224983, 1.2443628094870762, 0.17]
medicalchart[0].rotation = [0, 0, 0]
medicationbottle_B[0].position = [2.9137955825989947, 3.560518749200658, 0.06]
medicationbottle_B[0].rotation = [0, 0, 0]
bookchair_B[0].position = [0.9205327184115523, 3.474549481036898, 0.015]
bookchair_B[0].rotation = [0, 0, 0]
bookdesk_C[0].position = [3.7921873350674367, 3.122901571610897, 0.0175]
bookdesk_C[0].rotation = [0, 0, 0]
plant_B[0].position = [1.520778754873217, 2.4411247829455847, 0.6]
plant_B[0].rotation = [0, 0, 0]
pillow[0].position = [0.578253055967604, 4.469453315728044, 0.075]
pillow[0].rotation = [0, 0, 0]
coffeecup[0].position = [2.738556502528984, 3.3085580700121024, 0.05]
coffeecup[0].rotation = [0, 0, 0]
plantcabinet[0].position = [3.054468043642821, 3.569860828140307, 0.275]
plantcabinet[0].rotation = [0, 0, 0]
floorlamp_C[0].position = [0.9773291666178219, 1.2763610912774408, 0.85]
floorlamp_C[0].rotation = [0, 0, 0]
plant_C[0].position = [0.1193316408572849, 1.9211232077629214, 0.575]
plant_C[0].rotation = [0, 0, 0]
pen[0].position = [2.93321510036532, 3.9480018223573854, 0.006]
pen[0].rotation = [0, 0, 0]
medicinebottle_B[0].position = [2.1681678631784393, 1.0736885130967537, 0.08]
medicinebottle_B[0].rotation = [0, 0, 0]
artwork_B[0].position = [0.40322860832714397, 0.031286142111255355, 0.325]
artwork_B[0].rotation = [0, 0, 0]
plant_D[0].position = [1.4552145867636102, 1.4488653688532533, 0.525]
plant_D[0].rotation = [0, 0, 0]
purifier[0].position = [0.07138196208326233, 3.630516626329972, 0.425]
purifier[0].rotation = [0, 0, 0]
floorlamp_D[0].position = [2.280527229426089, 3.7839176033727755, 0.875]
floorlamp_D[0].rotation = [0, 0, 0]
booknightstand[0].position = [3.7111836460372074, 4.783216339904999, 0.011]
booknightstand[0].rotation = [0, 0, 0]
trashbin_B[0].position = [3.5509182189268382, 1.6309769900315922, 0.2]
trashbin_B[0].rotation = [0, 0, 0]
medicinebottle_C[0].position = [1.2445139298392787, 1.136564034691473, 0.08]
medicinebottle_C[0].rotation = [0, 0, 0]
artwork_C[0].position = [3.914671749937008, 0.13710282078941982, 0.4]
artwork_C[0].rotation = [0, 0, 0]
artwork_D[0].position = [1.2757999329368168, 3.3621578482060515, 0.5]
artwork_D[0].rotation = [0, 0, 0]
mirror_D[0].position = [2.1173521276716154, 2.5784861371726358, 0.475]
mirror_D[0].rotation = [0, 0, 0]
chair[0].position = [2.0731557248900674, 1.0697072045447298, 0.44]
chair[0].rotation = [0, 0, 0]
cupdesk_A[0].position = [3.10950872978777, 3.4557371864502224, 0.055]
cupdesk_A[0].rotation = [0, 0, 0]
cupdesk_B[0].position = [4.072628717332296, 4.680797822945052, 0.05]
cupdesk_B[0].rotation = [0, 0, 0]
medicalequipment_B[0].position = [3.8410463385196385, 4.6267320090549555, 0.23]
medicalequipment_B[0].rotation = [0, 0, 0]
recyclebin[0].position = [1.9595122998152188, 2.864323731524185, 0.275]
recyclebin[0].rotation = [0, 0, 0]
medicinebottle_A[0].position = [4.115668263063636, 3.4999144754628997, 0.08]
medicinebottle_A[0].rotation = [0, 0, 0]
cupnightstand_A[0].position = [0.4311412843740209, 1.7165712269581268, 0.055]
cupnightstand_A[0].rotation = [0, 0, 0]
medicalequipment_A[0].position = [1.4301122463591407, 3.558073475484265, 0.41]
medicalequipment_A[0].rotation = [0, 0, 0]
floorlamp_A[0].position = [1.4576351240781953, 1.9055585520625273, 0.86]
floorlamp_A[0].rotation = [0, 0, 0]
artwork_A[0].position = [0.7225122419606239, 2.541386529361811, 0.55]
artwork_A[0].rotation = [0, 0, 0]
ivstand[0].position = [1.4453230288161383, 0.07526979595229633, 0.925]
ivstand[0].rotation = [0, 0, 0]
heater[0].position = [0.9658758609593475, 2.8105834450525697, 0.22]
heater[0].rotation = [0, 0, 0]
pendesk_A[0].position = [1.3401047514810671, 1.833027908710343, 0.006]
pendesk_A[0].rotation = [0, 0, 0]
stool[0].position = [1.0955815712766002, 1.9068328804981878, 0.24]
stool[0].rotation = [0, 0, 0]
bookdesk_A[0].position = [4.1521216677779655, 4.081280313227583, 0.015]
bookdesk_A[0].rotation = [0, 0, 0]
bookdesk_B[0].position = [2.1845537631313587, 3.5632326246562656, 0.0175]
bookdesk_B[0].rotation = [0, 0, 0]
desk[0].position = [2.817626730887832, 2.623272245414831, 0.375]
desk[0].rotation = [0, 0, 0]
notebook[0].position = [2.9012147618357185, 2.16403753096787, 0.009]
notebook[0].rotation = [0, 0, 0]
cabinet[0].position = [2.329063585473247, 2.0989944665422806, 0.95]
cabinet[0].rotation = [0, 0, 0]
plant_A[0].position = [0.5092899684541022, 0.11234511229690769, 0.55]
plant_A[0].rotation = [0, 0, 0]
book[0].position = [2.952716440676107, 0.41371229913131913, 0.0175]
book[0].rotation = [0, 0, 0]
sofa[0].position = [3.467452939659466, 1.0698887237171018, 0.39]
sofa[0].rotation = [0, 0, 0]
mirror_A[0].position = [3.338489714658209, 0.6220149937053376, 0.4]
mirror_A[0].rotation = [0, 0, 0]
pendesk_B[0].position = [0.3268273653556522, 3.7238127204318023, 0.006]
pendesk_B[0].rotation = [0, 0, 0]
medicalbottle_A[0].position = [1.3511107947795538, 1.3587193101076873, 0.055]
medicalbottle_A[0].rotation = [0, 0, 0]
mirror_B[0].position = [1.1491979936330927, 1.292325961471727, 0.5]
mirror_B[0].rotation = [0, 0, 0]
medicalbottle_B[0].position = [1.4326059750290718, 3.093102906449821, 0.055]
medicalbottle_B[0].rotation = [0, 0, 0]
bookchair_A[0].position = [1.063014576937013, 1.6430347306603559, 0.0125]
bookchair_A[0].rotation = [0, 0, 0]
mirror_C[0].position = [1.8181507882858388, 2.711759178878604, 0.45]
mirror_C[0].rotation = [0, 0, 0]
phone[0].position = [3.5923725492374268, 3.872398517370468, 0.0045]
phone[0].rotation = [0, 0, 0]
lampnightstand[0].position = [4.075025737892303, 4.161202291737779, 0.26]
lampnightstand[0].rotation = [0, 0, 0]
floorlamp_B[0].position = [0.18803867533780355, 3.0643939835866885, 0.825]
floorlamp_B[0].rotation = [0, 0, 0]
cupnightstand_B[0].position = [4.146656625082988, 4.090910866872733, 0.1]
cupnightstand_B[0].rotation = [0, 0, 0]
medicationbottle_A[0].position = [2.329938225142534, 4.08703393986877, 0.06]
medicationbottle_A[0].rotation = [0, 0, 0]
trashbin_A[0].position = [1.0780370808010988, 1.137845039393845, 0.21]
trashbin_A[0].rotation = [0, 0, 0]
medicalmonitor[0].position = [3.646308786990489, 1.2531701455411586, 0.19]
medicalmonitor[0].rotation = [0, 0, 0]
bed[0].position = [2.432292300245667, 4.027580875882595, 0.34]
bed[0].rotation = [0, 0, 0]
nightstand[0].position = [0.9780349678114852, 2.853310746521729, 0.3]
nightstand[0].rotation = [0, 0, 0]
wastebin[0].position = [4.188318534783369, 1.7303259007478737, 0.225]
wastebin[0].rotation = [0, 0, 0]
medicalchart[0].position = [2.681775363224983, 1.2443628094870762, 0.17]
medicalchart[0].rotation = [0, 0, 0]
medicationbottle_B[0].position = [2.9137955825989947, 3.560518749200658, 0.06]
medicationbottle_B[0].rotation = [0, 0, 0]
bookchair_B[0].position = [0.9205327184115523, 3.474549481036898, 0.015]
bookchair_B[0].rotation = [0, 0, 0]
bookdesk_C[0].position = [3.7921873350674367, 3.122901571610897, 0.0175]
bookdesk_C[0].rotation = [0, 0, 0]
plant_B[0].position = [1.520778754873217, 2.4411247829455847, 0.6]
plant_B[0].rotation = [0, 0, 0]
pillow[0].position = [0.578253055967604, 4.469453315728044, 0.075]
pillow[0].rotation = [0, 0, 0]
coffeecup[0].position = [2.738556502528984, 3.3085580700121024, 0.05]
coffeecup[0].rotation = [0, 0, 0]
plantcabinet[0].position = [3.054468043642821, 3.569860828140307, 0.275]
plantcabinet[0].rotation = [0, 0, 0]
floorlamp_C[0].position = [0.9773291666178219, 1.2763610912774408, 0.85]
floorlamp_C[0].rotation = [0, 0, 0]
plant_C[0].position = [0.1193316408572849, 1.9211232077629214, 0.575]
plant_C[0].rotation = [0, 0, 0]
pen[0].position = [2.93321510036532, 3.9480018223573854, 0.006]
pen[0].rotation = [0, 0, 0]
medicinebottle_B[0].position = [2.1681678631784393, 1.0736885130967537, 0.08]
medicinebottle_B[0].rotation = [0, 0, 0]
artwork_B[0].position = [0.40322860832714397, 0.031286142111255355, 0.325]
artwork_B[0].rotation = [0, 0, 0]
plant_D[0].position = [1.4552145867636102, 1.4488653688532533, 0.525]
plant_D[0].rotation = [0, 0, 0]
purifier[0].position = [0.07138196208326233, 3.630516626329972, 0.425]
purifier[0].rotation = [0, 0, 0]
floorlamp_D[0].position = [2.280527229426089, 3.7839176033727755, 0.875]
floorlamp_D[0].rotation = [0, 0, 0]
booknightstand[0].position = [3.7111836460372074, 4.783216339904999, 0.011]
booknightstand[0].rotation = [0, 0, 0]
trashbin_B[0].position = [3.5509182189268382, 1.6309769900315922, 0.2]
trashbin_B[0].rotation = [0, 0, 0]
medicinebottle_C[0].position = [1.2445139298392787, 1.136564034691473, 0.08]
medicinebottle_C[0].rotation = [0, 0, 0]
artwork_C[0].position = [3.914671749937008, 0.13710282078941982, 0.4]
artwork_C[0].rotation = [0, 0, 0]
artwork_D[0].position = [1.2757999329368168, 3.3621578482060515, 0.5]
artwork_D[0].rotation = [0, 0, 0]
mirror_D[0].position = [2.1173521276716154, 2.5784861371726358, 0.475]
mirror_D[0].rotation = [0, 0, 0]
chair[0].position = [2.0731557248900674, 1.0697072045447298, 0.44]
chair[0].rotation = [0, 0, 0]
cupdesk_A[0].position = [3.10950872978777, 3.4557371864502224, 0.055]
cupdesk_A[0].rotation = [0, 0, 0]
cupdesk_B[0].position = [4.072628717332296, 4.680797822945052, 0.05]
cupdesk_B[0].rotation = [0, 0, 0]
medicalequipment_B[0].position = [3.8410463385196385, 4.6267320090549555, 0.23]
medicalequipment_B[0].rotation = [0, 0, 0]
recyclebin[0].position = [1.9595122998152188, 2.864323731524185, 0.275]
recyclebin[0].rotation = [0, 0, 0]

solver.constraints = []

# Helper functions keep the explicit placements and their corresponding
# positional/orientation constraints consistent.
def _locate(asset, position, yaw_degrees):
    asset[0].position = position
    asset[0].rotation = [0, 0, radians(yaw_degrees)]


def _constrain(asset, yaw_degrees, weight=10):
    # Pin the asset's center to its planned location.
    position_anchor = AssetInstance(position=list(asset[0].position))
    solver.distance_constraint(
        asset[0], position_anchor, 0, 0, weight=weight
    )

    # A point one meter in front of the asset fixes its intended orientation.
    yaw = radians(yaw_degrees)
    facing_anchor = AssetInstance(position=[
        asset[0].position[0] + cos(yaw),
        asset[0].position[1] + sin(yaw),
        asset[0].position[2],
    ])
    solver.point_towards(asset[0], facing_anchor)


def _constrain_on(asset, support, yaw_degrees):
    # Surface support is the most important constraint for small objects.
    solver.on_top_of(asset[0], support[0])
    _constrain(asset, yaw_degrees)


def _constrain_wall(asset, wall, yaw_degrees):
    solver.against_wall(asset[0], wall)
    _constrain(asset, yaw_degrees)


# ---------------------------------------------------------------------------
# Explicit placements
# ---------------------------------------------------------------------------
# The hospital bed runs north-south in the center of the room. Plant_A and
# plant_C occupy opposite sides of it, making the bed spatially between them.
_locate(bed, [2.10, 2.75, 0.34], 90)
_locate(plant_A, [0.36, 2.75, 0.55], 0)
_locate(plant_C, [3.84, 2.75, 0.575], 180)

# Main floor furniture is distributed around the perimeter. The northern
# doorway spans x=0.52..1.42, so its approach remains free of floor assets.
_locate(desk, [3.86, 4.12, 0.375], 180)
_locate(cabinet, [0.21, 4.28, 0.95], 0)
_locate(sofa, [2.85, 0.39, 0.39], 90)
_locate(chair, [0.95, 0.70, 0.44], 45)
_locate(stool, [1.05, 1.65, 0.24], 0)
_locate(nightstand, [2.97, 2.73, 0.30], 180)

# Clinical equipment remains accessible from the bed without blocking the
# central circulation lane or the doorway.
_locate(medicalequipment_A, [3.96, 1.48, 0.41], 180)
_locate(medicalequipment_B, [3.99, 3.38, 0.23], 180)
_locate(ivstand, [3.88, 2.05, 0.925], 180)
_locate(purifier, [0.17, 1.35, 0.425], 0)
_locate(heater, [0.19, 1.88, 0.22], 0)

# Lamps and bins use otherwise inactive perimeter locations.
_locate(floorlamp_A, [0.25, 0.25, 0.86], 45)
_locate(floorlamp_B, [4.02, 0.23, 0.825], 135)
_locate(floorlamp_C, [4.01, 0.76, 0.85], 180)
_locate(floorlamp_D, [1.76, 0.16, 0.875], 90)
_locate(trashbin_A, [1.37, 0.16, 0.21], 90)
_locate(wastebin, [3.48, 1.15, 0.225], 180)
_locate(trashbin_B, [2.03, 4.85, 0.20], 270)
_locate(recyclebin, [2.40, 4.84, 0.275], 270)
_locate(plant_B, [0.36, 3.45, 0.60], 0)
_locate(floorlamp_C, [4.01, 0.76, 0.85], 180)
_locate(plant_D, [3.80, 0.42, 0.525], 135)

# Thin artwork and mirrors are wall-mounted above floor level. None occupies
# the doorway opening on the north wall.
_locate(artwork_A, [1.90, 4.98, 1.55], 270)
_locate(artwork_B, [2.75, 4.98, 1.48], 270)
_locate(artwork_C, [3.65, 4.98, 1.48], 270)
_locate(artwork_D, [0.02, 2.28, 1.52], 0)
_locate(mirror_A, [1.15, 0.02, 1.48], 90)
_locate(mirror_B, [2.08, 0.02, 1.52], 90)
_locate(mirror_C, [4.18, 1.25, 1.48], 180)
_locate(mirror_D, [4.185, 3.95, 1.50], 180)

# Desk accessories are spread across the desktop.
_locate(pendesk_A, [3.60, 3.62, 0.755], 0)
_locate(pendesk_B, [3.60, 3.80, 0.755], 0)
_locate(pen, [3.61, 4.00, 0.755], 0)
_locate(bookdesk_A, [3.75, 3.65, 0.765], 180)
_locate(bookdesk_B, [3.77, 3.94, 0.77], 180)
_locate(bookdesk_C, [3.76, 4.24, 0.77], 180)
_locate(notebook, [3.98, 3.68, 0.76], 180)
_locate(phone, [4.02, 3.93, 0.755], 180)
_locate(cupdesk_A, [4.03, 4.17, 0.805], 180)
_locate(cupdesk_B, [4.03, 4.38, 0.80], 180)
_locate(medicalchart, [3.58, 4.48, 0.92], 180)
_locate(medicinebottle_A, [3.83, 4.48, 0.83], 180)
_locate(medicinebottle_B, [4.02, 4.55, 0.83], 180)
_locate(medicinebottle_C, [3.84, 4.68, 0.83], 180)

# The requested medication bottle is on the nightstand. Related bedside
# objects are arranged around it without sharing the same center.
_locate(lampnightstand, [3.04, 2.74, 0.86], 180)
_locate(medicationbottle_A, [2.78, 2.48, 0.66], 180)
_locate(cupnightstand_A, [2.78, 2.62, 0.655], 180)
_locate(cupnightstand_B, [2.79, 2.79, 0.70], 180)
_locate(booknightstand, [2.94, 2.48, 0.61], 180)
_locate(coffeecup, [3.13, 2.48, 0.65], 180)
_locate(medicalbottle_A, [3.15, 2.62, 0.655], 180)
_locate(medicalbottle_B, [3.16, 2.83, 0.655], 180)
_locate(medicationbottle_B, [2.91, 2.87, 0.66], 180)

# The monitor is supported by the larger clinical unit beside the bed.
_locate(medicalmonitor, [3.93, 1.48, 1.01], 180)

# Soft and reading objects are placed on their intended furniture.
_locate(pillow, [2.10, 2.95, 0.755], 90)
_locate(book, [2.82, 0.42, 0.80], 90)
_locate(bookchair_A, [0.95, 0.70, 0.895], 45)
_locate(bookchair_B, [0.95, 0.70, 0.925], 45)

# The compact plant sits on the cabinet top.
_locate(plantcabinet, [0.22, 4.28, 2.175], 0)

# ---------------------------------------------------------------------------
# Semantic constraints
# ---------------------------------------------------------------------------
# Preserve the principal composition: the bed is equidistant between the two
# specified plants, with all three aligned across the room.
solver.distance_constraint(bed[0], plant_A[0], 1.74, 1.74, weight=10)
solver.distance_constraint(bed[0], plant_C[0], 1.74, 1.74, weight=10)
solver.align_with(plant_A[0], plant_C[0], angle=180)
solver.align_with(plant_C[0], plant_A[0], angle=180)

_constrain(bed, 90)
_constrain(plant_A, 0)
_constrain(plant_C, 180)

# Furniture and equipment against room boundaries.
_constrain_wall(desk, walls[0], 180)
_constrain_wall(cabinet, walls[2], 0)
_constrain_wall(sofa, walls[3], 90)
_constrain(chair, 45)
_constrain(stool, 0)
_constrain(nightstand, 180)

_constrain_wall(medicalequipment_A, walls[0], 180)
_constrain_wall(medicalequipment_B, walls[0], 180)
_constrain_wall(ivstand, walls[0], 180)
_constrain_wall(purifier, walls[2], 0)
_constrain_wall(heater, walls[2], 0)

_constrain(floorlamp_A, 45)
_constrain_wall(floorlamp_B, walls[0], 135)
_constrain_wall(floorlamp_C, walls[0], 180)
_constrain_wall(floorlamp_D, walls[3], 90)
_constrain_wall(trashbin_A, walls[3], 90)
_constrain(wastebin, 180)
_constrain_wall(trashbin_B, walls[1], 270)
_constrain_wall(recyclebin, walls[1], 270)
_constrain_wall(plant_B, walls[2], 0)
_constrain(plant_D, 135)

# Wall-mounted objects face into the room.
_constrain_wall(artwork_A, walls[1], 270)
_constrain_wall(artwork_B, walls[1], 270)
_constrain_wall(artwork_C, walls[1], 270)
_constrain_wall(artwork_D, walls[2], 0)
_constrain_wall(mirror_A, walls[3], 90)
_constrain_wall(mirror_B, walls[3], 90)
_constrain_wall(mirror_C, walls[0], 180)
_constrain_wall(mirror_D, walls[0], 180)

# Desktop objects.
_constrain_on(pendesk_A, desk, 0)
_constrain_on(pendesk_B, desk, 0)
_constrain_on(pen, desk, 0)
_constrain_on(bookdesk_A, desk, 180)
_constrain_on(bookdesk_B, desk, 180)
_constrain_on(bookdesk_C, desk, 180)
_constrain_on(notebook, desk, 180)
_constrain_on(phone, desk, 180)
_constrain_on(cupdesk_A, desk, 180)
_constrain_on(cupdesk_B, desk, 180)
_constrain_on(medicalchart, desk, 180)
_constrain_on(medicinebottle_A, desk, 180)
_constrain_on(medicinebottle_B, desk, 180)
_constrain_on(medicinebottle_C, desk, 180)

# Bedside objects, including the specifically requested medication bottle.
_constrain_on(lampnightstand, nightstand, 180)
_constrain_on(medicationbottle_A, nightstand, 180)
_constrain_on(cupnightstand_A, nightstand, 180)
_constrain_on(cupnightstand_B, nightstand, 180)
_constrain_on(booknightstand, nightstand, 180)
_constrain_on(coffeecup, nightstand, 180)
_constrain_on(medicalbottle_A, nightstand, 180)
_constrain_on(medicalbottle_B, nightstand, 180)
_constrain_on(medicationbottle_B, nightstand, 180)

# Remaining supported objects.
_constrain_on(medicalmonitor, medicalequipment_A, 180)
_constrain_on(pillow, bed, 90)
_constrain_on(book, sofa, 90)
_constrain_on(bookchair_A, chair, 45)
_constrain_on(bookchair_B, bookchair_A, 45)
_constrain_on(plantcabinet, cabinet, 0)

solver.constraints = []
mirror_A[0].position = [1.149999976158142, 0.011367769911885262, 0.4000000059604645]
mirror_A[0].rotation = [0, 0, 1.5733372437234565]
mirror_A[0].optimize = 2
sofa[0].position = [2.8499999046325684, 0.39291056990623474, 0.38999998569488525]
sofa[0].rotation = [0, 0, 1.5764478347426785]
sofa[0].optimize = 2
bed[0].position = [2.109999895095825, 2.75, 0.3400000035762787]
bed[0].rotation = [0, 0, 1.589645882193713]
bed[0].optimize = 2
wastebin[0].position = [3.4800000190734863, 1.149999976158142, 0.22499999403953552]
wastebin[0].rotation = [0, 0, -3.1321678761290697]
wastebin[0].optimize = 2
bookdesk_C[0].position = [3.759999990463257, 4.239999771118164, 0.7699999809265137]
bookdesk_C[0].rotation = [0, 0, -3.1290262823329655]
bookdesk_C[0].optimize = 2
nightstand[0].position = [2.9700000286102295, 2.7300000190734863, 0.30000001192092896]
nightstand[0].rotation = [0, 0, -3.1038935423913827]
nightstand[0].optimize = 2
cabinet[0].position = [0.21253982186317444, 4.28000020980835, 0.949999988079071]
cabinet[0].rotation = [0, 0, 0.005651519838109554]
cabinet[0].optimize = 2
medicinebottle_A[0].position = [3.8299999237060547, 4.480000019073486, 0.8299999833106995]
medicinebottle_A[0].rotation = [0, 0, -3.1290262823329655]
medicinebottle_A[0].optimize = 2
artwork_A[0].position = [1.899999976158142, 4.988697052001953, 0.550000011920929]
artwork_A[0].rotation = [0, 0, -1.5682554086442377]
artwork_A[0].optimize = 2
cupnightstand_A[0].position = [2.7799999713897705, 2.619999885559082, 0.6550000309944153]
cupnightstand_A[0].rotation = [0, 0, -3.1290262823329655]
cupnightstand_A[0].optimize = 2
bookdesk_B[0].position = [3.7699999809265137, 3.940000057220459, 0.7699999809265137]
bookdesk_B[0].rotation = [0, 0, -3.1290262823329655]
bookdesk_B[0].optimize = 2
medicationbottle_B[0].position = [2.9100000858306885, 2.869999885559082, 0.6600000262260437]
medicationbottle_B[0].rotation = [0, 0, -3.1290262823329655]
medicationbottle_B[0].optimize = 2
floorlamp_C[0].position = [4.009517669677734, 0.7599999904632568, 0.8500000238418579]
floorlamp_C[0].rotation = [0, 0, -3.139051732072762]
floorlamp_C[0].optimize = 2
cupnightstand_B[0].position = [2.7899999618530273, 2.7899999618530273, 0.7000000476837158]
cupnightstand_B[0].rotation = [0, 0, -3.1290262823329655]
cupnightstand_B[0].optimize = 2
booknightstand[0].position = [2.940000057220459, 2.4800000190734863, 0.6100000143051147]
booknightstand[0].rotation = [0, 0, -3.1290262823329655]
booknightstand[0].optimize = 2
ivstand[0].position = [3.890000104904175, 2.049999952316284, 0.925000011920929]
ivstand[0].rotation = [0, 0, -3.139051734217035]
ivstand[0].optimize = 2
bookchair_A[0].position = [0.949999988079071, 0.699999988079071, 0.8949999809265137]
bookchair_A[0].rotation = [0, 0, 0.8011061392127593]
bookchair_A[0].optimize = 2
phone[0].position = [4.019999980926514, 3.930000066757202, 0.7549999952316284]
phone[0].rotation = [0, 0, -3.1290262823329655]
phone[0].optimize = 2
floorlamp_B[0].position = [3.983743667602539, 0.23000000417232513, 0.824999988079071]
floorlamp_B[0].rotation = [0, 0, 2.3828984127308828]
floorlamp_B[0].optimize = 2
medicalequipment_B[0].position = [4.0, 3.380000114440918, 0.23000000417232513]
medicalequipment_B[0].rotation = [0, 0, -3.139051732072762]
medicalequipment_B[0].optimize = 2
mirror_C[0].position = [4.188512325286865, 1.25, 0.44999998807907104]
mirror_C[0].rotation = [0, 0, -3.139051734217035]
mirror_C[0].optimize = 2
lampnightstand[0].position = [3.0399999618530273, 2.740000009536743, 0.8600000143051147]
lampnightstand[0].rotation = [0, 0, -3.1290262823329655]
lampnightstand[0].optimize = 2
desk[0].position = [3.8487823009490967, 4.119999885559082, 0.375]
desk[0].rotation = [0, 0, -3.095494344966317]
desk[0].optimize = 2
medicalbottle_B[0].position = [3.1600000858306885, 2.8299999237060547, 0.6550000309944153]
medicalbottle_B[0].rotation = [0, 0, -3.1290262823329655]
medicalbottle_B[0].optimize = 2
floorlamp_D[0].position = [1.7599999904632568, 0.15000024437904358, 0.875]
floorlamp_D[0].rotation = [0, 0, 1.573337246467581]
floorlamp_D[0].optimize = 2
pillow[0].position = [2.0999999046325684, 2.950000047683716, 0.7549999952316284]
pillow[0].rotation = [0, 0, 1.5833626980517244]
pillow[0].optimize = 2
book[0].position = [2.819999933242798, 0.41999998688697815, 0.7999999523162842]
book[0].rotation = [0, 0, 1.5833626980517244]
book[0].optimize = 2
plant_C[0].position = [3.8399999141693115, 2.75, 0.574999988079071]
plant_C[0].rotation = [0, 0, -3.1219376480719623]
plant_C[0].optimize = 2
pendesk_B[0].position = [3.5999999046325684, 3.799999952316284, 0.7549999952316284]
pendesk_B[0].rotation = [0, 0, 0.01256637125682779]
pendesk_B[0].optimize = 2
heater[0].position = [0.18000006675720215, 1.8799999952316284, 0.2199999988079071]
heater[0].rotation = [0, 0, 0.002540920594857827]
heater[0].optimize = 2
purifier[0].position = [0.17043142020702362, 1.350000023841858, 0.42500001192092896]
purifier[0].rotation = [0, 0, 0.002540920594857827]
purifier[0].optimize = 2
mirror_D[0].position = [4.192923069000244, 3.950000047683716, 0.4749999940395355]
mirror_D[0].rotation = [0, 0, -3.1390517332948615]
mirror_D[0].optimize = 2
artwork_D[0].position = [0.011368179693818092, 2.2799999713897705, 0.5]
artwork_D[0].rotation = [0, 0, 0.002540918150658852]
artwork_D[0].optimize = 2
coffeecup[0].position = [3.1294026374816895, 2.4958415031433105, 0.6500000357627869]
coffeecup[0].rotation = [0, 0, -3.1290262823329655]
coffeecup[0].optimize = 2
stool[0].position = [1.0499999523162842, 1.649999976158142, 0.23999999463558197]
stool[0].rotation = [0, 0, 0.00942477746072377]
stool[0].optimize = 2
bookchair_B[0].position = [0.949999988079071, 0.699999988079071, 0.9249999523162842]
bookchair_B[0].rotation = [0, 0, 0.7979645348947851]
bookchair_B[0].optimize = 2
pendesk_A[0].position = [3.5999999046325684, 3.619999885559082, 0.7549999952316284]
pendesk_A[0].rotation = [0, 0, 0.01256637125682779]
pendesk_A[0].optimize = 2
plant_B[0].position = [0.350000262260437, 3.450000047683716, 0.6000000238418579]
plant_B[0].rotation = [0, 0, 0.0025409163063124128]
plant_B[0].optimize = 2
plantcabinet[0].position = [0.2199999988079071, 4.28000020980835, 2.174999952316284]
plantcabinet[0].rotation = [0, 0, 0.01256637125682779]
plantcabinet[0].optimize = 2
plant_D[0].position = [3.761613368988037, 0.4383867681026459, 0.5249999761581421]
plant_D[0].rotation = [0, 0, 2.3656192553579443]
plant_D[0].optimize = 2
bookdesk_A[0].position = [3.75, 3.6500000953674316, 0.7649999856948853]
bookdesk_A[0].rotation = [0, 0, -3.1290262823329655]
bookdesk_A[0].optimize = 2
floorlamp_A[0].position = [0.2969716787338257, 0.2969716489315033, 0.8600000143051147]
floorlamp_A[0].rotation = [0, 0, 0.7948229285630478]
floorlamp_A[0].optimize = 2
medicinebottle_C[0].position = [3.8399999141693115, 4.679999828338623, 0.8299999833106995]
medicinebottle_C[0].rotation = [0, 0, -3.1290262823329655]
medicinebottle_C[0].optimize = 2
medicationbottle_A[0].position = [2.7799999713897705, 2.4800000190734863, 0.6600000262260437]
medicationbottle_A[0].rotation = [0, 0, -3.1290262823329655]
medicationbottle_A[0].optimize = 2
pen[0].position = [3.609999895095825, 4.0, 0.7549999952316284]
pen[0].rotation = [0, 0, 0.01256637125682779]
pen[0].optimize = 2
medicalchart[0].position = [3.5799999237060547, 4.480000019073486, 0.9200000166893005]
medicalchart[0].rotation = [0, 0, -3.1290262823329655]
medicalchart[0].optimize = 2
mirror_B[0].position = [2.0799999237060547, 0.011367769911885262, 0.5]
mirror_B[0].rotation = [0, 0, 1.573337246167655]
mirror_B[0].optimize = 2
medicinebottle_B[0].position = [4.019999980926514, 4.550000190734863, 0.8299999833106995]
medicinebottle_B[0].rotation = [0, 0, -3.1290262823329655]
medicinebottle_B[0].optimize = 2
cupdesk_A[0].position = [4.03000020980835, 4.170000076293945, 0.8050000071525574]
cupdesk_A[0].rotation = [0, 0, -3.1290262823329655]
cupdesk_A[0].optimize = 2
artwork_B[0].position = [2.75, 4.9885125160217285, 0.32499998807907104]
artwork_B[0].rotation = [0, 0, -1.5682554107885098]
artwork_B[0].optimize = 2
notebook[0].position = [3.9800000190734863, 3.680000066757202, 0.7599999904632568]
notebook[0].rotation = [0, 0, -3.1290262823329655]
notebook[0].optimize = 2
trashbin_B[0].position = [2.0299999713897705, 4.859999656677246, 0.20000000298023224]
trashbin_B[0].rotation = [0, 0, -1.568255406200039]
trashbin_B[0].optimize = 2
medicalbottle_A[0].position = [3.1500000953674316, 2.619999885559082, 0.6550000309944153]
medicalbottle_A[0].rotation = [0, 0, -3.1290262823329655]
medicalbottle_A[0].optimize = 2
chair[0].position = [0.949999988079071, 0.699999988079071, 0.4399999976158142]
chair[0].rotation = [0, 0, 0.7979645348947851]
chair[0].optimize = 2
medicalmonitor[0].position = [3.930000066757202, 1.4800000190734863, 1.0099999904632568]
medicalmonitor[0].rotation = [0, 0, -3.1290262823329655]
medicalmonitor[0].optimize = 2
trashbin_A[0].position = [1.3700000047683716, 0.15000008046627045, 0.20999999344348907]
trashbin_A[0].rotation = [0, 0, 1.5733372473897544]
trashbin_A[0].optimize = 2
medicalequipment_A[0].position = [3.9700000286102295, 1.4800000190734863, 0.4099999964237213]
medicalequipment_A[0].rotation = [0, 0, -3.1359411296508926]
medicalequipment_A[0].optimize = 2
plant_A[0].position = [0.36000001430511475, 2.75, 0.550000011920929]
plant_A[0].rotation = [0, 0, 0.01965500551783084]
plant_A[0].optimize = 2
artwork_C[0].position = [3.6500000953674316, 4.9885125160217285, 0.4000000059604645]
artwork_C[0].rotation = [0, 0, -1.5682554107885098]
artwork_C[0].optimize = 2
cupdesk_B[0].position = [4.03000020980835, 4.380000114440918, 0.800000011920929]
cupdesk_B[0].rotation = [0, 0, -3.1290262823329655]
cupdesk_B[0].optimize = 2
recyclebin[0].position = [2.4000000953674316, 4.849999904632568, 0.2750000059604645]
recyclebin[0].rotation = [0, 0, -1.5682554052778654]
recyclebin[0].optimize = 2

