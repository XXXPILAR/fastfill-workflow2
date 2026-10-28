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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.00, 0.00, 0.00]),
    Wall(corner1=[3.00, 0.00, 0.00], corner2=[3.00, 4.00, 0.00]),
    Wall(corner1=[3.00, 4.00, 0.00], corner2=[0.00, 4.00, 0.00]),
    Wall(corner1=[0.00, 4.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
mat = Assets(description="A rectangular woven bath mat with tropical leaf print, flat and low‑profile, soft microfiber material, teal and sand colors", size=[0.50, 0.80, 0.02], placements=[AssetInstance() for _ in range(1)])
decal_A = Assets(description="A single piece of thin and upright wall decal depicting a palm print, rectangular shape, glossy vinyl, vibrant green on white background", size=[0.00, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
lightfixture = Assets(description="A single piece of thin and upright light fixture with a woven rattan shade, cylindrical body, warm amber glow and a small leaf motif", size=[0.22, 0.28, 0.35], placements=[AssetInstance() for _ in range(1)])
mirror_A = Assets(description="A single piece of thin and upright mirror with a rectangular shape, turquoise frame, glossy finish and a subtle palm leaf pattern", size=[0.04, 0.65, 0.90], placements=[AssetInstance() for _ in range(1)])
painting = Assets(description="A single piece of thin and upright painting with a vibrant tropical beach scene, featuring bold blues and greens, rendered on a smooth canvas.", size=[0.04, 0.80, 0.60], placements=[AssetInstance() for _ in range(1)])
towelrack_A = Assets(description="A tropical style wall‑mounted towel rack with a curved, arching bar, natural bamboo finish, and a woven palm leaf backing.", size=[0.14, 0.65, 0.30], placements=[AssetInstance() for _ in range(1)])
plant_A = Assets(description="A small potted tropical plant with broad green leaves, cylindrical pot, matte terracotta finish, leafy foliage", size=[0.35, 0.35, 0.65], placements=[AssetInstance() for _ in range(1)])
artwork = Assets(description="A single piece of thin and upright artwork, rectangular canvas with a vibrant tropical sunset scene, glossy finish", size=[0.03, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
shampoobottle_single = Assets(description="A tropical style shampoo bottle with a cylindrical body, turquoise gradient finish, smooth plastic surface and a flip‑top cap", size=[0.07, 0.07, 0.21], placements=[AssetInstance() for _ in range(1)])
toothbrushholder = Assets(description="A tropical style toothbrush holder of woven rattan, elongated rectangular container with a built‑in drainage slot", size=[0.08, 0.10, 0.13], placements=[AssetInstance() for _ in range(1)])
towelrack_B = Assets(description="A tropical style wall‑mounted towel rack of rattan, elongated horizontal bar with decorative leaf cut‑outs", size=[0.12, 0.70, 0.18], placements=[AssetInstance() for _ in range(1)])
toothpaste_A = Assets(description="A tropical style toothpaste tube with a matte teal finish, cylindrical shape, and a leaf‑shaped cap", size=[0.04, 0.05, 0.19], placements=[AssetInstance() for _ in range(1)])
toothpaste_B = Assets(description="A tropical style toothpaste tube with a slim rectangular profile, bright orange color, glossy plastic finish and a pineapple motif", size=[0.04, 0.06, 0.18], placements=[AssetInstance() for _ in range(1)])
towelrack_C = Assets(description="A wall‑mounted towel rack with two curved hooks, metallic finish, tropical turquoise paint, sleek curved shape", size=[0.10, 0.24, 0.16], placements=[AssetInstance() for _ in range(1)])
plant_B = Assets(description="A small potted tropical plant with broad green leaves, cylindrical pot, matte terracotta finish, leafy foliage", size=[0.32, 0.32, 0.60], placements=[AssetInstance() for _ in range(1)])
mirror_B = Assets(description="A single piece of thin and upright mirror with a polished silver frame, rectangular shape, smooth reflective surface, tropical teal edging", size=[0.04, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
decoration_A = Assets(description="A single piece of thin and upright wall decoration, rectangular canvas with a vibrant tropical sunset painting, framed in reclaimed wood", size=[0.04, 0.55, 0.75], placements=[AssetInstance() for _ in range(1)])
mirror_C = Assets(description="A single piece of thin and upright mirror, rectangular frame with a brushed gold tropical motif, sleek reflective surface", size=[0.04, 0.55, 0.80], placements=[AssetInstance() for _ in range(1)])
toiletpaper_A = Assets(description="A roll of white toilet paper with a tropical palm border printed on the cardboard, cylindrical shape, soft tissue sheets", size=[0.11, 0.11, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_C = Assets(description="A tropical style potted plant with a wide ceramic pot, glossy green leaves, and a curved stem, giving a lush jungle feel", size=[0.55, 0.55, 1.20], placements=[AssetInstance() for _ in range(1)])
shampoo = Assets(description="A tropical style shampoo bottle with a sleek, cylindrical body, turquoise gradient color, glossy plastic, and a subtle wave embossing.", size=[0.07, 0.07, 0.22], placements=[AssetInstance() for _ in range(1)])
mirror_D = Assets(description="A single piece of thin and upright mirror with a brushed bamboo frame, rectangular shape, reflective surface and subtle tropical engraving", size=[0.05, 0.70, 1.00], placements=[AssetInstance() for _ in range(1)])
showercurtain_A = Assets(description="A tropical style shower curtain with a rectangular panel, bright mango orange fabric, lightweight woven texture and a repeating hibiscus print", size=[0.03, 1.80, 2.00], placements=[AssetInstance() for _ in range(1)])
toiletry_A = Assets(description="A collection of five assorted tropical toiletries including a toothbrush, toothpaste, soap bar, lotion bottle, and small bottle, each with vibrant island-inspired colors, varied shapes such as cylindrical, rectangular, and curved, glossy finishes", size=[0.18, 0.35, 0.24], placements=[AssetInstance() for _ in range(1)])
toothbrush_A = Assets(description="A tropical style toothbrush with a bamboo handle, slender cylindrical head, and green bristles", size=[0.02, 0.02, 0.19], placements=[AssetInstance() for _ in range(1)])
light = Assets(description="A wall‑mounted light fixture with a circular tropical patterned shade, metal base, warm amber glow, round shape", size=[0.16, 0.25, 0.25], placements=[AssetInstance() for _ in range(1)])
showercurtain_B = Assets(description="A tropical style shower curtain of lightweight fabric, bright teal background with oversized palm leaf prints, rectangular and slightly billowy", size=[0.04, 1.80, 2.00], placements=[AssetInstance() for _ in range(1)])
toothbrush_B = Assets(description="A tropical style toothbrush with a slender cylindrical head, teal handle, soft bristles and a small palm leaf engraving", size=[0.02, 0.02, 0.19], placements=[AssetInstance() for _ in range(1)])
toiletry_B = Assets(description="A collection of five assorted tropical toiletries including a toothbrush, toothpaste, soap bar, lotion bottle, and small bottle, each with vibrant island-inspired colors, varied shapes such as cylindrical, rectangular, and curved, glossy finishes", size=[0.20, 0.38, 0.25], placements=[AssetInstance() for _ in range(1)])
toiletpaper_B = Assets(description="A tropical style toilet paper roll with a vibrant leaf pattern, cylindrical shape, soft white paper, and a glossy green wrapper", size=[0.12, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
soapdish = Assets(description="A single piece of thin and upright soap dish made of bamboo, rectangular shallow tray, natural wood finish, tropical woven texture", size=[0.11, 0.16, 0.04], placements=[AssetInstance() for _ in range(1)])
toothbrush_C = Assets(description="A tropical style toothbrush with a slender cylindrical head, teal handle, soft bristles and a small palm leaf engraving", size=[0.02, 0.02, 0.19], placements=[AssetInstance() for _ in range(1)])
towelrack_D = Assets(description="A tropical style towel rack with a tall rectangular frame, coral finish, curved arms and decorative leaf cut‑outs", size=[0.14, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
shelf = Assets(description="A single piece of thin and upright rattan shelf mounted on the wall, rectangular shape, woven natural fibers, light brown color, open slots", size=[0.20, 0.60, 0.75], placements=[AssetInstance() for _ in range(1)])
plant_D = Assets(description="A small potted tropical plant with broad green leaves, cylindrical pot, matte terracotta finish, leafy foliage", size=[0.30, 0.30, 0.55], placements=[AssetInstance() for _ in range(1)])
decoration_B = Assets(description="A single piece of thin and upright wall decoration, rectangular canvas with a vibrant tropical sunset painting, framed in reclaimed wood", size=[0.04, 0.65, 0.50], placements=[AssetInstance() for _ in range(1)])
lotion = Assets(description="A tropical style lotion bottle with a rounded cylindrical shape, sea‑foam green color, glossy plastic finish and a subtle wave texture", size=[0.07, 0.07, 0.18], placements=[AssetInstance() for _ in range(1)])
decal_B = Assets(description="A single piece of thin and upright palm print decal, rectangular, vivid green palm silhouette on a matte white background", size=[0.00, 0.45, 0.65], placements=[AssetInstance() for _ in range(1)])
towelrack_E = Assets(description="A single piece of thin and upright towel rack, sleek stainless steel bar with a subtle wave curve, tropical design accents", size=[0.09, 0.75, 0.10], placements=[AssetInstance() for _ in range(1)])
soapdispenser = Assets(description="A tropical style soap dispenser with a compact, rectangular form, deep green color, polished ceramic, and a carved pineapple handle.", size=[0.08, 0.09, 0.19], placements=[AssetInstance() for _ in range(1)])
plant_E = Assets(description="A tropical style potted plant with a wide ceramic pot, glossy green leaves, and a curved stem, giving a lush jungle feel", size=[0.50, 0.50, 1.10], placements=[AssetInstance() for _ in range(1)])
bomb = Assets(description="A spherical bath bomb with a swirled turquoise and coral surface, smooth glossy finish, tropical fragrance infused, round shape", size=[0.07, 0.07, 0.07], placements=[AssetInstance() for _ in range(1)])
toiletbrush = Assets(description="A compact toilet brush with a curved handle, natural wood grip, bristles in green, slender shape", size=[0.14, 0.14, 0.42], placements=[AssetInstance() for _ in range(1)])
toothbrush_D = Assets(description="A tropical style toothbrush with a bamboo handle, slender cylindrical head, and green bristles", size=[0.02, 0.02, 0.19], placements=[AssetInstance() for _ in range(1)])

mat[0].instance_id = 'mat_0'
decal_A[0].instance_id = 'decal_A_0'
lightfixture[0].instance_id = 'lightfixture_0'
mirror_A[0].instance_id = 'mirror_A_0'
painting[0].instance_id = 'painting_0'
towelrack_A[0].instance_id = 'towelrack_A_0'
plant_A[0].instance_id = 'plant_A_0'
artwork[0].instance_id = 'artwork_0'
shampoobottle_single[0].instance_id = 'shampoobottle_single_0'
toothbrushholder[0].instance_id = 'toothbrushholder_0'
towelrack_B[0].instance_id = 'towelrack_B_0'
toothpaste_A[0].instance_id = 'toothpaste_A_0'
toothpaste_B[0].instance_id = 'toothpaste_B_0'
towelrack_C[0].instance_id = 'towelrack_C_0'
plant_B[0].instance_id = 'plant_B_0'
mirror_B[0].instance_id = 'mirror_B_0'
decoration_A[0].instance_id = 'decoration_A_0'
mirror_C[0].instance_id = 'mirror_C_0'
toiletpaper_A[0].instance_id = 'toiletpaper_A_0'
plant_C[0].instance_id = 'plant_C_0'
shampoo[0].instance_id = 'shampoo_0'
mirror_D[0].instance_id = 'mirror_D_0'
showercurtain_A[0].instance_id = 'showercurtain_A_0'
toiletry_A[0].instance_id = 'toiletry_A_0'
toothbrush_A[0].instance_id = 'toothbrush_A_0'
light[0].instance_id = 'light_0'
showercurtain_B[0].instance_id = 'showercurtain_B_0'
toothbrush_B[0].instance_id = 'toothbrush_B_0'
toiletry_B[0].instance_id = 'toiletry_B_0'
toiletpaper_B[0].instance_id = 'toiletpaper_B_0'
soapdish[0].instance_id = 'soapdish_0'
toothbrush_C[0].instance_id = 'toothbrush_C_0'
towelrack_D[0].instance_id = 'towelrack_D_0'
shelf[0].instance_id = 'shelf_0'
plant_D[0].instance_id = 'plant_D_0'
decoration_B[0].instance_id = 'decoration_B_0'
lotion[0].instance_id = 'lotion_0'
decal_B[0].instance_id = 'decal_B_0'
towelrack_E[0].instance_id = 'towelrack_E_0'
soapdispenser[0].instance_id = 'soapdispenser_0'
plant_E[0].instance_id = 'plant_E_0'
bomb[0].instance_id = 'bomb_0'
toiletbrush[0].instance_id = 'toiletbrush_0'
toothbrush_D[0].instance_id = 'toothbrush_D_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

mat[0].position = [2.801659063261728, 0.8541217830527503, 0.01]
mat[0].rotation = [0, 0, 0]
decal_A[0].position = [2.1214959157034157, 3.3259523997035614, 0.35]
decal_A[0].rotation = [0, 0, 0]
lightfixture[0].position = [1.1834727166558512, 1.543717856148405, 0.175]
lightfixture[0].rotation = [0, 0, 0]
mirror_A[0].position = [0.10947001776415388, 3.502589379959146, 0.45]
mirror_A[0].rotation = [0, 0, 0]
painting[0].position = [0.5138976098265405, 3.3905814880799787, 0.3]
painting[0].rotation = [0, 0, 0]
towelrack_A[0].position = [2.400261012938331, 1.0499887722974433, 0.15]
towelrack_A[0].rotation = [0, 0, 0]
plant_A[0].position = [0.3550155700565709, 3.7847667002382175, 0.325]
plant_A[0].rotation = [0, 0, 0]
artwork[0].position = [1.7935680951276387, 0.1389939155033031, 0.4]
artwork[0].rotation = [0, 0, 0]
shampoobottle_single[0].position = [2.237564186374172, 3.4110614121413914, 0.105]
shampoobottle_single[0].rotation = [0, 0, 0]
toothbrushholder[0].position = [2.176083648122904, 0.9648035426831325, 0.065]
toothbrushholder[0].rotation = [0, 0, 0]
towelrack_B[0].position = [2.5966839757944946, 3.1638964115937656, 0.09]
towelrack_B[0].rotation = [0, 0, 0]
toothpaste_A[0].position = [1.3613945815102544, 3.1069175880937068, 0.095]
toothpaste_A[0].rotation = [0, 0, 0]
toothpaste_B[0].position = [0.2988972073529964, 0.9105734457517154, 0.09]
toothpaste_B[0].rotation = [0, 0, 0]
towelrack_C[0].position = [0.15812904428855679, 2.7181812607134037, 0.08]
towelrack_C[0].rotation = [0, 0, 0]
plant_B[0].position = [1.7412792634526024, 1.723187845060723, 0.3]
plant_B[0].rotation = [0, 0, 0]
mirror_B[0].position = [1.9352718091828778, 1.0996036507718325, 0.425]
mirror_B[0].rotation = [0, 0, 0]
decoration_A[0].position = [0.25071308037864193, 0.766407301394354, 0.375]
decoration_A[0].rotation = [0, 0, 0]
mirror_C[0].position = [2.742590176103956, 0.4760252795525379, 0.4]
mirror_C[0].rotation = [0, 0, 0]
toiletpaper_A[0].position = [2.2886279106111176, 0.8832439583327267, 0.05]
toiletpaper_A[0].rotation = [0, 0, 0]
plant_C[0].position = [0.9762778506897868, 2.6440249335165014, 0.6]
plant_C[0].rotation = [0, 0, 0]
shampoo[0].position = [0.8665968741926142, 0.1528512067983394, 0.11]
shampoo[0].rotation = [0, 0, 0]
mirror_D[0].position = [0.7294813134314674, 3.0926318751262825, 0.5]
mirror_D[0].rotation = [0, 0, 0]
showercurtain_A[0].position = [1.3167839367894738, 0.4380002266169285, 1.0]
showercurtain_A[0].rotation = [0, 0, 0]
toiletry_A[0].position = [2.303576183376835, 2.5725460401123863, 0.12]
toiletry_A[0].rotation = [0, 0, 0]
toothbrush_A[0].position = [2.912897156422933, 1.116094841240292, 0.095]
toothbrush_A[0].rotation = [0, 0, 0]
light[0].position = [0.2965394273724359, 3.287464339642113, 0.125]
light[0].rotation = [0, 0, 0]
showercurtain_B[0].position = [1.6693499740437745, 3.6610222896188485, 1.0]
showercurtain_B[0].rotation = [0, 0, 0]
toothbrush_B[0].position = [1.5818486064118953, 2.128854168698057, 0.095]
toothbrush_B[0].rotation = [0, 0, 0]
toiletry_B[0].position = [0.6965969409733046, 3.6509372572880863, 0.125]
toiletry_B[0].rotation = [0, 0, 0]
toiletpaper_B[0].position = [2.070808228582861, 3.2282380603127323, 0.05]
toiletpaper_B[0].rotation = [0, 0, 0]
soapdish[0].position = [2.8437753643368473, 0.2038290069155786, 0.02]
soapdish[0].rotation = [0, 0, 0]
toothbrush_C[0].position = [2.665960950476869, 0.6930177672603324, 0.095]
toothbrush_C[0].rotation = [0, 0, 0]
towelrack_D[0].position = [0.35248304695876165, 0.004388894491564432, 0.425]
towelrack_D[0].rotation = [0, 0, 0]
shelf[0].position = [0.5135248611494362, 3.992805000665453, 0.375]
shelf[0].rotation = [0, 0, 0]
plant_D[0].position = [2.5770256083700853, 0.4916932651207033, 0.275]
plant_D[0].rotation = [0, 0, 0]
decoration_B[0].position = [0.5108245857394543, 0.8943855504135576, 0.25]
decoration_B[0].rotation = [0, 0, 0]
lotion[0].position = [1.1913032785196205, 3.777098249191879, 0.09]
lotion[0].rotation = [0, 0, 0]
decal_B[0].position = [2.522588320411783, 0.30304001184247653, 0.325]
decal_B[0].rotation = [0, 0, 0]
towelrack_E[0].position = [2.540284379105309, 0.9998850297231008, 0.05]
towelrack_E[0].rotation = [0, 0, 0]
soapdispenser[0].position = [2.933192518340632, 2.1210765910009726, 0.095]
soapdispenser[0].rotation = [0, 0, 0]
plant_E[0].position = [1.0566576945199073, 0.37657838249019804, 0.55]
plant_E[0].rotation = [0, 0, 0]
bomb[0].position = [0.39036286579766954, 3.4437022156767934, 0.035]
bomb[0].rotation = [0, 0, 0]
toiletbrush[0].position = [1.3240471448496443, 0.7100000575635907, 0.21]
toiletbrush[0].rotation = [0, 0, 0]
toothbrush_D[0].position = [2.4282383400600263, 0.3720709708813583, 0.095]
toothbrush_D[0].rotation = [0, 0, 0]
mat[0].position = [2.801659063261728, 0.8541217830527503, 0.01]
mat[0].rotation = [0, 0, 0]
decal_A[0].position = [2.1214959157034157, 3.3259523997035614, 0.35]
decal_A[0].rotation = [0, 0, 0]
lightfixture[0].position = [1.1834727166558512, 1.543717856148405, 0.175]
lightfixture[0].rotation = [0, 0, 0]
mirror_A[0].position = [0.10947001776415388, 3.502589379959146, 0.45]
mirror_A[0].rotation = [0, 0, 0]
painting[0].position = [0.5138976098265405, 3.3905814880799787, 0.3]
painting[0].rotation = [0, 0, 0]
towelrack_A[0].position = [2.400261012938331, 1.0499887722974433, 0.15]
towelrack_A[0].rotation = [0, 0, 0]
plant_A[0].position = [0.3550155700565709, 3.7847667002382175, 0.325]
plant_A[0].rotation = [0, 0, 0]
artwork[0].position = [1.7935680951276387, 0.1389939155033031, 0.4]
artwork[0].rotation = [0, 0, 0]
shampoobottle_single[0].position = [2.237564186374172, 3.4110614121413914, 0.105]
shampoobottle_single[0].rotation = [0, 0, 0]
toothbrushholder[0].position = [2.176083648122904, 0.9648035426831325, 0.065]
toothbrushholder[0].rotation = [0, 0, 0]
towelrack_B[0].position = [2.5966839757944946, 3.1638964115937656, 0.09]
towelrack_B[0].rotation = [0, 0, 0]
toothpaste_A[0].position = [1.3613945815102544, 3.1069175880937068, 0.095]
toothpaste_A[0].rotation = [0, 0, 0]
toothpaste_B[0].position = [0.2988972073529964, 0.9105734457517154, 0.09]
toothpaste_B[0].rotation = [0, 0, 0]
towelrack_C[0].position = [0.15812904428855679, 2.7181812607134037, 0.08]
towelrack_C[0].rotation = [0, 0, 0]
plant_B[0].position = [1.7412792634526024, 1.723187845060723, 0.3]
plant_B[0].rotation = [0, 0, 0]
mirror_B[0].position = [1.9352718091828778, 1.0996036507718325, 0.425]
mirror_B[0].rotation = [0, 0, 0]
decoration_A[0].position = [0.25071308037864193, 0.766407301394354, 0.375]
decoration_A[0].rotation = [0, 0, 0]
mirror_C[0].position = [2.742590176103956, 0.4760252795525379, 0.4]
mirror_C[0].rotation = [0, 0, 0]
toiletpaper_A[0].position = [2.2886279106111176, 0.8832439583327267, 0.05]
toiletpaper_A[0].rotation = [0, 0, 0]
plant_C[0].position = [0.9762778506897868, 2.6440249335165014, 0.6]
plant_C[0].rotation = [0, 0, 0]
shampoo[0].position = [0.8665968741926142, 0.1528512067983394, 0.11]
shampoo[0].rotation = [0, 0, 0]
mirror_D[0].position = [0.7294813134314674, 3.0926318751262825, 0.5]
mirror_D[0].rotation = [0, 0, 0]
showercurtain_A[0].position = [1.3167839367894738, 0.4380002266169285, 1.0]
showercurtain_A[0].rotation = [0, 0, 0]
toiletry_A[0].position = [2.303576183376835, 2.5725460401123863, 0.12]
toiletry_A[0].rotation = [0, 0, 0]
toothbrush_A[0].position = [2.912897156422933, 1.116094841240292, 0.095]
toothbrush_A[0].rotation = [0, 0, 0]
light[0].position = [0.2965394273724359, 3.287464339642113, 0.125]
light[0].rotation = [0, 0, 0]
showercurtain_B[0].position = [1.6693499740437745, 3.6610222896188485, 1.0]
showercurtain_B[0].rotation = [0, 0, 0]
toothbrush_B[0].position = [1.5818486064118953, 2.128854168698057, 0.095]
toothbrush_B[0].rotation = [0, 0, 0]
toiletry_B[0].position = [0.6965969409733046, 3.6509372572880863, 0.125]
toiletry_B[0].rotation = [0, 0, 0]
toiletpaper_B[0].position = [2.070808228582861, 3.2282380603127323, 0.05]
toiletpaper_B[0].rotation = [0, 0, 0]
soapdish[0].position = [2.8437753643368473, 0.2038290069155786, 0.02]
soapdish[0].rotation = [0, 0, 0]
toothbrush_C[0].position = [2.665960950476869, 0.6930177672603324, 0.095]
toothbrush_C[0].rotation = [0, 0, 0]
towelrack_D[0].position = [0.35248304695876165, 0.004388894491564432, 0.425]
towelrack_D[0].rotation = [0, 0, 0]
shelf[0].position = [0.5135248611494362, 3.992805000665453, 0.375]
shelf[0].rotation = [0, 0, 0]
plant_D[0].position = [2.5770256083700853, 0.4916932651207033, 0.275]
plant_D[0].rotation = [0, 0, 0]
decoration_B[0].position = [0.5108245857394543, 0.8943855504135576, 0.25]
decoration_B[0].rotation = [0, 0, 0]
lotion[0].position = [1.1913032785196205, 3.777098249191879, 0.09]
lotion[0].rotation = [0, 0, 0]
decal_B[0].position = [2.522588320411783, 0.30304001184247653, 0.325]
decal_B[0].rotation = [0, 0, 0]
towelrack_E[0].position = [2.540284379105309, 0.9998850297231008, 0.05]
towelrack_E[0].rotation = [0, 0, 0]
soapdispenser[0].position = [2.933192518340632, 2.1210765910009726, 0.095]
soapdispenser[0].rotation = [0, 0, 0]
plant_E[0].position = [1.0566576945199073, 0.37657838249019804, 0.55]
plant_E[0].rotation = [0, 0, 0]
bomb[0].position = [0.39036286579766954, 3.4437022156767934, 0.035]
bomb[0].rotation = [0, 0, 0]
toiletbrush[0].position = [1.3240471448496443, 0.7100000575635907, 0.21]
toiletbrush[0].rotation = [0, 0, 0]
toothbrush_D[0].position = [2.4282383400600263, 0.3720709708813583, 0.095]
toothbrush_D[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed references used to preserve the intended positions and orientations.
_room_center = AssetInstance(position=[1.50, 2.00, 0.00])
_east_reference = AssetInstance(position=[1.50, 2.00, 0.00], rotation=[0, 0, radians(0)])
_north_reference = AssetInstance(position=[1.50, 2.00, 0.00], rotation=[0, 0, radians(90)])
_west_reference = AssetInstance(position=[1.50, 2.00, 0.00], rotation=[0, 0, radians(180)])
_south_reference = AssetInstance(position=[1.50, 2.00, 0.00], rotation=[0, 0, radians(-90)])


def _anchor(instance, position, rotation, orientation_reference):
    """Initialize an asset and strongly preserve its intended center position."""
    instance.position = position
    instance.rotation = [0, 0, rotation]
    solver.distance_constraint(
        instance,
        AssetInstance(position=position),
        0,
        0,
        weight=10,
    )
    solver.align_with(instance, orientation_reference)


def _wall_mount(instance, position, rotation, wall_index, orientation_reference):
    """Place an item against its intended wall with its front facing into the room."""
    _anchor(instance, position, rotation, orientation_reference)
    solver.against_wall(instance, walls[wall_index])


def _shelf_item(instance, position):
    """Place a small bathroom item on the wall shelf."""
    _anchor(instance, position, radians(0), _east_reference)
    solver.on_top_of(instance, shelf[0])


# ---------------------------------------------------------------------------
# Floor-level assets
# ---------------------------------------------------------------------------

# The mat is kept in the open central area, away from the inward path of the
# north-wall door (x=1.495..2.445 near y=4).
_anchor(mat[0], [1.50, 1.55, 0.01], radians(0), _east_reference)

# Arrange the principal three plants along the south side. plant_C is exactly
# between plant_A and plant_B, implementing the requested "between" relation.
_anchor(plant_A[0], [0.35, 0.45, 0.325], radians(45), _east_reference)
solver.point_towards(plant_A[0], _room_center)

_anchor(plant_C[0], [1.50, 0.45, 0.60], radians(90), _north_reference)
solver.point_towards(plant_C[0], _room_center)

_anchor(plant_B[0], [2.65, 0.45, 0.30], radians(135), _west_reference)
solver.point_towards(plant_B[0], _room_center)

# Equal distances keep the middle plant centered between the two endpoint
# plants even if the solver makes a small feasibility adjustment.
solver.distance_constraint(plant_C[0], plant_A[0], 1.15, 1.15, weight=10)
solver.distance_constraint(plant_C[0], plant_B[0], 1.15, 1.15, weight=10)

# The remaining plants occupy opposite rear corners without entering the
# doorway clearance zone.
_anchor(plant_D[0], [0.35, 3.35, 0.275], radians(-45), _south_reference)
solver.point_towards(plant_D[0], _room_center)

_anchor(plant_E[0], [2.70, 2.95, 0.55], radians(150), _west_reference)
solver.point_towards(plant_E[0], _room_center)

# The toilet brush is accessible along the right wall and does not obstruct
# either the central mat or the door approach.
_anchor(toiletbrush[0], [2.87, 2.20, 0.21], radians(180), _west_reference)
solver.against_wall(toiletbrush[0], walls[1])
solver.point_towards(toiletbrush[0], _room_center)


# ---------------------------------------------------------------------------
# Large wall-mounted assets
# Wall indices: 0=south, 1=east, 2=north, 3=west.
# ---------------------------------------------------------------------------

# Shower curtains occupy the lower portions of the opposing long walls.
_wall_mount(
    showercurtain_A[0], [0.015, 1.00, 1.00],
    radians(0), 3, _east_reference
)
_wall_mount(
    showercurtain_B[0], [2.98, 1.00, 1.00],
    radians(180), 1, _west_reference
)

# West wall: shelf and upper decorative pieces are beyond the curtain.
_wall_mount(
    shelf[0], [0.10, 2.50, 1.20],
    radians(0), 3, _east_reference
)
_wall_mount(
    mirror_A[0], [0.02, 3.15, 1.80],
    radians(0), 3, _east_reference
)
_wall_mount(
    decal_A[0], [0.005, 3.75, 2.30],
    radians(0), 3, _east_reference
)

# East wall: three mirrors are spaced consecutively along the wall.
_wall_mount(
    mirror_B[0], [2.98, 2.20, 1.70],
    radians(180), 1, _west_reference
)
_wall_mount(
    mirror_C[0], [2.98, 2.80, 1.70],
    radians(180), 1, _west_reference
)
_wall_mount(
    mirror_D[0], [2.975, 3.50, 1.75],
    radians(180), 1, _west_reference
)

# South wall artwork forms a continuous gallery above the low fixtures.
_wall_mount(
    painting[0], [0.45, 0.02, 2.05],
    radians(90), 0, _north_reference
)
_wall_mount(
    artwork[0], [1.18, 0.015, 2.05],
    radians(90), 0, _north_reference
)
_wall_mount(
    decoration_A[0], [1.80, 0.02, 2.05],
    radians(90), 0, _north_reference
)
_wall_mount(
    decoration_B[0], [2.62, 0.02, 2.05],
    radians(90), 0, _north_reference
)

# South-wall towel racks sit below the artwork, separated vertically.
_wall_mount(
    towelrack_A[0], [0.40, 0.07, 1.05],
    radians(90), 0, _north_reference
)
_wall_mount(
    towelrack_B[0], [1.15, 0.06, 1.05],
    radians(90), 0, _north_reference
)
_wall_mount(
    towelrack_D[0], [1.82, 0.07, 0.85],
    radians(90), 0, _north_reference
)

# North-wall items stay to either side of the door, except for the two lights,
# which are mounted safely above the doorway rather than in its floor opening.
_wall_mount(
    decal_B[0], [0.28, 3.995, 2.25],
    radians(-90), 2, _south_reference
)
_wall_mount(
    towelrack_E[0], [0.88, 3.955, 1.15],
    radians(-90), 2, _south_reference
)
_wall_mount(
    towelrack_C[0], [2.75, 3.95, 1.15],
    radians(-90), 2, _south_reference
)
_wall_mount(
    light[0], [1.78, 3.92, 2.70],
    radians(-90), 2, _south_reference
)
_wall_mount(
    lightfixture[0], [2.16, 3.89, 2.68],
    radians(-90), 2, _south_reference
)


# ---------------------------------------------------------------------------
# Shelf-supported toiletries
# ---------------------------------------------------------------------------

# The two larger toiletry collections occupy the shelf's lower open slots.
_shelf_item(toiletry_A[0], [0.18, 2.30, 1.02])
_shelf_item(toiletry_B[0], [0.18, 2.70, 1.03])

# Small bottles and holders are arranged in staggered groups on the upper
# shelf area. The slight x/y offsets prevent their bounding boxes overlapping.
_shelf_item(shampoobottle_single[0], [0.12, 2.22, 1.72])
_shelf_item(toothbrushholder[0], [0.25, 2.22, 1.68])
_shelf_item(toothpaste_A[0], [0.12, 2.32, 1.705])
_shelf_item(toothpaste_B[0], [0.25, 2.33, 1.70])
_shelf_item(toiletpaper_A[0], [0.12, 2.44, 1.68])
_shelf_item(shampoo[0], [0.25, 2.45, 1.73])

_shelf_item(toothbrush_A[0], [0.10, 2.54, 1.715])
_shelf_item(toothbrush_B[0], [0.18, 2.54, 1.715])
_shelf_item(toothbrush_C[0], [0.26, 2.54, 1.715])
_shelf_item(toothbrush_D[0], [0.34, 2.54, 1.715])

_shelf_item(toiletpaper_B[0], [0.12, 2.66, 1.68])
_shelf_item(soapdish[0], [0.27, 2.67, 1.65])
_shelf_item(lotion[0], [0.12, 2.78, 1.70])
_shelf_item(soapdispenser[0], [0.25, 2.79, 1.705])

# The bath bomb is centered in the shallow soap dish so it cannot roll off.
_anchor(bomb[0], [0.27, 2.67, 1.705], radians(0), _east_reference)
solver.on_top_of(bomb[0], soapdish[0])

solver.constraints = []
plant_A[0].position = [0.3499999940395355, 0.44999998807907104, 0.32499998807907104]
plant_A[0].rotation = [0, 0, 0.8011061392127593]
plant_A[0].optimize = 2
shelf[0].position = [0.10863996297121048, 2.5, 0.375]
shelf[0].rotation = [0, 0, 0.05232239032972915]
shelf[0].optimize = 2
artwork[0].position = [1.1799999475479126, 0.0067442841827869415, 0.4000000059604645]
artwork[0].rotation = [0, 0, 1.573337246167655]
artwork[0].optimize = 2
mat[0].position = [1.5, 1.5499999523162842, 0.009999999776482582]
mat[0].rotation = [0, 0, 0.00942477746072377]
mat[0].optimize = 2
toothbrush_C[0].position = [0.216493159532547, 2.5372626781463623, 0.8450000286102295]
toothbrush_C[0].rotation = [0, 0, 0.01256637125682779]
toothbrush_C[0].optimize = 2
towelrack_D[0].position = [1.8200000524520874, 0.07060959935188293, 0.42500001192092896]
towelrack_D[0].rotation = [0, 0, 1.573337246167655]
towelrack_D[0].optimize = 2
mirror_D[0].position = [2.9839563369750977, 3.5, 0.5]
mirror_D[0].rotation = [0, 0, -3.1390517354391343]
mirror_D[0].optimize = 2
soapdispenser[0].position = [0.20078708231449127, 2.7869038581848145, 0.8450000286102295]
soapdispenser[0].rotation = [0, 0, 0.01256637125682779]
soapdispenser[0].optimize = 2
plant_C[0].position = [1.5, 0.44999998807907104, 0.6000000238418579]
plant_C[0].rotation = [0, 0, 1.589645882193713]
plant_C[0].optimize = 2
shampoo[0].position = [0.21151646971702576, 2.447690486907959, 0.8600000143051147]
shampoo[0].rotation = [0, 0, 0.01256637125682779]
shampoo[0].optimize = 2
toothbrush_D[0].position = [0.21680857241153717, 2.5322494506835938, 0.8450000286102295]
toothbrush_D[0].rotation = [0, 0, 0.01256637125682779]
toothbrush_D[0].optimize = 2
painting[0].position = [0.44999998807907104, 0.011367769911885262, 0.30000001192092896]
painting[0].rotation = [0, 0, 1.5733372437234565]
painting[0].optimize = 2
decoration_B[0].position = [2.619999885559082, 0.011367769911885262, 0.25]
decoration_B[0].rotation = [0, 0, 1.5733372440233822]
decoration_B[0].optimize = 2
plant_B[0].position = [2.6500000953674316, 0.44999998807907104, 0.30000001192092896]
plant_B[0].rotation = [0, 0, 2.371902466007656]
plant_B[0].optimize = 2
mirror_A[0].position = [0.011367769911885262, 3.1500000953674316, 0.44999998807907104]
mirror_A[0].rotation = [0, 0, 0.0025409172284856325]
mirror_A[0].optimize = 2
lightfixture[0].position = [2.1600000858306885, 3.8896443843841553, 0.17499999701976776]
lightfixture[0].rotation = [0, 0, -1.5682554052778654]
lightfixture[0].optimize = 2
light[0].position = [1.7799999713897705, 3.929612398147583, 0.125]
light[0].rotation = [0, 0, -1.568255404355692]
light[0].optimize = 2
decal_A[0].position = [-0.0049994997680187225, 3.75, 0.3499999940395355]
decal_A[0].rotation = [0, 0, 0.0025409193727581954]
decal_A[0].optimize = 2
toothbrush_B[0].position = [0.18000000715255737, 2.5399999618530273, 0.8450000286102295]
toothbrush_B[0].rotation = [0, 0, 0.01256637125682779]
toothbrush_B[0].optimize = 2
showercurtain_A[0].position = [0.01630847528576851, 1.0, 1.0]
showercurtain_A[0].rotation = [0, 0, 0.0025408985523042373]
showercurtain_A[0].optimize = 2
toiletpaper_B[0].position = [0.11999999731779099, 2.6600000858306885, 0.800000011920929]
toiletpaper_B[0].rotation = [0, 0, 0.01256637125682779]
toiletpaper_B[0].optimize = 2
showercurtain_B[0].position = [2.978691816329956, 1.0, 1.0]
showercurtain_B[0].rotation = [0, 0, -3.1390517541153167]
showercurtain_B[0].optimize = 2
toothpaste_B[0].position = [0.21777957677841187, 2.3280975818634033, 0.8400000333786011]
toothpaste_B[0].rotation = [0, 0, 0.01256637125682779]
toothpaste_B[0].optimize = 2
toiletpaper_A[0].position = [0.11999999731779099, 2.440000057220459, 0.800000011920929]
toiletpaper_A[0].rotation = [0, 0, 0.01256637125682779]
toiletpaper_A[0].optimize = 2
decoration_A[0].position = [1.7999999523162842, 0.011367769911885262, 0.375]
decoration_A[0].rotation = [0, 0, 1.5733372470898281]
decoration_A[0].optimize = 2
shampoobottle_single[0].position = [0.11999999731779099, 2.2200000286102295, 0.8550000190734863]
shampoobottle_single[0].rotation = [0, 0, 0.01256637125682779]
shampoobottle_single[0].optimize = 2
soapdish[0].position = [0.20838592946529388, 2.666123628616333, 0.7699999809265137]
soapdish[0].rotation = [0, 0, 0.0157079639172164]
soapdish[0].optimize = 2
mirror_C[0].position = [2.9886109828948975, 2.799999952316284, 0.4000000059604645]
mirror_C[0].rotation = [0, 0, -3.139051734217035]
mirror_C[0].optimize = 2
towelrack_E[0].position = [0.8799999952316284, 3.954047441482544, 0.05000000074505806]
towelrack_E[0].rotation = [0, 0, -1.5682554086442377]
towelrack_E[0].optimize = 2
lotion[0].position = [0.11999999731779099, 2.7799999713897705, 0.8400000333786011]
lotion[0].rotation = [0, 0, 0.01256637125682779]
lotion[0].optimize = 2
toothpaste_A[0].position = [0.11999999731779099, 2.319999933242798, 0.8450000286102295]
toothpaste_A[0].rotation = [0, 0, 0.01256637125682779]
toothpaste_A[0].optimize = 2
towelrack_C[0].position = [2.75, 3.959402561187744, 0.07999999821186066]
towelrack_C[0].rotation = [0, 0, -1.568255404355692]
towelrack_C[0].optimize = 2
toothbrushholder[0].position = [0.22352074086666107, 2.218470811843872, 0.8149999976158142]
toothbrushholder[0].rotation = [0, 0, 0.01256637125682779]
toothbrushholder[0].optimize = 2
toiletry_B[0].position = [0.18000000715255737, 2.700000047683716, 0.875]
toiletry_B[0].rotation = [0, 0, 0.01256637125682779]
toiletry_B[0].optimize = 2
towelrack_A[0].position = [0.4000000059604645, 0.07082557678222656, 0.15000000596046448]
towelrack_A[0].rotation = [0, 0, 1.5733372458677286]
towelrack_A[0].optimize = 2
mirror_B[0].position = [2.9886107444763184, 2.200000047683716, 0.42500001192092896]
mirror_B[0].rotation = [0, 0, -3.139051734217035]
mirror_B[0].optimize = 2
plant_D[0].position = [0.3499999940395355, 3.3499999046325684, 0.2750000059604645]
plant_D[0].rotation = [0, 0, -0.7728317919001115]
plant_D[0].optimize = 2
towelrack_B[0].position = [1.149999976158142, 0.06088912859559059, 0.09000000357627869]
towelrack_B[0].rotation = [0, 0, 1.5733372440233822]
towelrack_B[0].optimize = 2
plant_E[0].position = [2.65967059135437, 2.950000047683716, 0.550000011920929]
plant_E[0].rotation = [0, 0, 2.63056025624579]
plant_E[0].optimize = 2
toiletbrush[0].position = [2.879999876022339, 2.200000047683716, 0.20999999344348907]
toiletbrush[0].rotation = [0, 0, -3.13594112806159]
toiletbrush[0].optimize = 2
toiletry_A[0].position = [0.18000000715255737, 2.299999952316284, 0.8700000047683716]
toiletry_A[0].rotation = [0, 0, 0.01256637125682779]
toiletry_A[0].optimize = 2
decal_B[0].position = [0.2800000011920929, 4.004999160766602, 0.32499998807907104]
decal_B[0].rotation = [0, 0, -1.5682554064999652]
decal_B[0].optimize = 2
bomb[0].position = [0.27000001072883606, 2.6700000762939453, 0.824999988079071]
bomb[0].rotation = [0, 0, 0.01256637125682779]
bomb[0].optimize = 2
toothbrush_A[0].position = [0.10000000149011612, 2.5399999618530273, 0.8450000286102295]
toothbrush_A[0].rotation = [0, 0, 0.01256637125682779]
toothbrush_A[0].optimize = 2

