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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[15.00, 0.00, 0.00]),
    Wall(corner1=[15.00, 0.00, 0.00], corner2=[15.00, 10.00, 0.00]),
    Wall(corner1=[15.00, 10.00, 0.00], corner2=[0.00, 10.00, 0.00]),
    Wall(corner1=[0.00, 10.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
storage_A = Assets(description="A wall‑mounted cabinet with marble front, rectangular shape, smooth marble surface with subtle veining, luxe style", size=[0.35, 0.90, 0.70], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover with shimmering gold lettering, thick pages giving it a slightly bulky and elegant appearance", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
bench_A = Assets(description="A polished marble bench with a smooth rectangular seat, white marble top with gold‑flecked veins, slender chrome legs, and an integrated shallow groove along the front edge.", size=[0.45, 1.80, 0.45], placements=[AssetInstance() for _ in range(1)])
plant_A = Assets(description="A potted ornamental plant with an elegant cylindrical metallic pot finished in brushed steel, featuring a decorative spiral cutout, and tall leafy foliage extending upward.", size=[0.55, 0.55, 1.50], placements=[AssetInstance() for _ in range(1)])
magazine_A = Assets(description="A glossy magazine with a metallic cover, rectangular shape, sleek reflective surface, and a subtle embossed title", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
mug_A = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band around the lip, refined Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_B = Assets(description="A potted plant in a metallic gold pot, featuring a tall slender trunk and lush green foliage, with a cylindrical pot", size=[0.65, 0.65, 1.70], placements=[AssetInstance() for _ in range(1)])
art_A = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with vibrant colours, gold‑brushed metal frame, sleek low‑profile mounting", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
art_B = Assets(description="A single piece of thin and upright abstract painting, rectangular canvas with bold geometric patterns in gold and deep navy, framed in a slim black border, Luxe style", size=[0.03, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
lighting_A = Assets(description="A wall‑mounted sconce with a sleek metallic gold finish, compact rectangular shape, subtle upward‑facing light source, modern Luxe style", size=[0.12, 0.18, 0.28], placements=[AssetInstance() for _ in range(1)])
signage_A = Assets(description="A single piece of thin and upright Luxe signage framed with a gold border, rectangular panel with a polished black background and elegant gold lettering", size=[0.03, 0.70, 0.45], placements=[AssetInstance() for _ in range(1)])
washer_A = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
mug_B = Assets(description="A Luxe ceramic mug with a metallic gold rim, cylindrical shape, smooth white glaze, gold‑finished rim and a subtle curved handle", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
washer_B = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
mug_C = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, smooth white body, polished gold edge, featuring a delicate engraved pattern near the rim", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
mug_D = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with subtle sheen, luxe finish", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
dryer_A = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
dryer_B = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
plant_C = Assets(description="A potted plant in a metallic gold pot, featuring a tall slender trunk and lush green foliage, with a cylindrical pot", size=[0.65, 0.65, 1.70], placements=[AssetInstance() for _ in range(1)])
arta_A = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with bold geometric patterns, gold‑trimmed frame, Luxe style", size=[0.04, 0.55, 0.75], placements=[AssetInstance() for _ in range(1)])
mug_E = Assets(description="A Luxe ceramic mug with a metallic gold rim, cylindrical body, glossy white finish, gold rim and a gently curved handle", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
art_C = Assets(description="A single piece of thin and upright abstract artwork, rectangular frame with a glossy finish, vibrant colours and bold geometric patterns, mounted flush against the wall", size=[0.03, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
lighting_B = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, sleek curved glass shade, warm metallic tone, and an integrated decorative crystal accent", size=[0.13, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
mug_F = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band around the lip, refined Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_D = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with a sleek reflective finish, vibrant green foliage, tall slender stems, and a decorative leaf pattern", size=[0.50, 0.50, 1.35], placements=[AssetInstance() for _ in range(1)])
art_D = Assets(description="A single piece of thin and upright abstract artwork, rectangular canvas with bold metallic gold accents on a dark background, sleek frame with a glossy finish", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
mugc_A = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band, Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
lighting_C = Assets(description="A wall‑mounted sconce with a sleek brushed‑gold finish, rectangular profile, narrow vertical slats that diffuse warm light, Luxe style", size=[0.10, 0.16, 0.35], placements=[AssetInstance() for _ in range(1)])
lightinga = Assets(description="A wall‑mounted sconce with a sleek metal body, rectangular profile, brushed gold finish, Luxe style", size=[0.10, 0.16, 0.30], placements=[AssetInstance() for _ in range(1)])
art_E = Assets(description="A single piece of thin and upright abstract painting, rectangular canvas with bold geometric patterns in gold and deep navy, framed in a slim black border, Luxe style", size=[0.03, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
lighting_D = Assets(description="A wall sconce with brushed brass finish, rectangular housing, sleek low‑profile design, luxe style", size=[0.10, 0.20, 0.28], placements=[AssetInstance() for _ in range(1)])
mug_G = Assets(description="A ceramic mug with a metallic gold rim, cylindrical body, smooth white glaze, slightly tapered at the base, with a subtle glossy sheen on the rim", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
lighting_E = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, sleek curved glass shade, warm metallic tone, and an integrated decorative crystal accent", size=[0.13, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
signage_B = Assets(description="A single piece of thin and upright framed sign with gold border, rectangular panel, polished gold trim, luxe style", size=[0.03, 0.60, 0.40], placements=[AssetInstance() for _ in range(1)])
art_F = Assets(description="A single piece of thin and upright abstract painting, rectangular canvas with bold geometric patterns in gold and deep navy, framed in a slim black border, Luxe style", size=[0.03, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
mug_H = Assets(description="A ceramic mug with a sleek metallic gold rim, cylindrical body, smooth white glaze, slightly tapered towards the base, glossy finish that catches the light", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
washer_C = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
arta_B = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with bold geometric patterns, gold‑trimmed frame, Luxe style", size=[0.04, 0.55, 0.75], placements=[AssetInstance() for _ in range(1)])
dryer_C = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
plantcorner_A = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with sleek finish, lush green foliage, luxe style", size=[0.60, 0.60, 1.40], placements=[AssetInstance() for _ in range(1)])
art_G = Assets(description="A single piece of thin and upright abstract painting, rectangular canvas with bold geometric patterns in gold and deep navy, framed in a slim black border, Luxe style", size=[0.03, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
washer_D = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
storage_B = Assets(description="A wall‑mounted cabinet with marble front, tall rectangular shape, polished white marble surface with subtle gray veining, sleek brass handles, and a recessed glass panel", size=[0.35, 0.60, 1.10], placements=[AssetInstance() for _ in range(1)])
muga = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band, Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover, ornate gold lettering, with a subtle raised texture on the cover", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
mug_table_A = Assets(description="A ceramic mug with a metallic gold rim, smooth cylindrical body, glossy white finish, subtle gold accent around the lip", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_E = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with a sleek reflective finish, vibrant green foliage, tall slender stems, and a decorative leaf pattern", size=[0.50, 0.50, 1.35], placements=[AssetInstance() for _ in range(1)])
mug_I = Assets(description="A Luxe ceramic mug with a metallic gold rim, cylindrical shape, smooth white glaze, gold‑finished rim and a subtle curved handle", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
lighting_F = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, sleek curved glass shade, warm metallic tone, and an integrated decorative crystal accent", size=[0.13, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
mug_J = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, smooth white body, glossy finish, and a subtle gold accent around the lip", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
mugc_B = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band, Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
lighting_G = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, and a curved glass shade that diffuses warm light", size=[0.13, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
book_C = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown leather cover with raised gold lettering, elegant and luxurious finish", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
book_D = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover, ornate gold lettering, with a subtle raised texture on the cover", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
magazine_B = Assets(description="A glossy magazine with a metallic cover, rectangular shape, shimmering silver surface, crisp edges, with a subtle embossed logo on the front", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
washer_E = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
washer_F = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
magazine_C = Assets(description="A glossy magazine with a metallic cover, rectangular shape, sleek silver finish with subtle texture, Luxe style", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
table_A = Assets(description="A folding work table with a marble top, rectangular slab, brass legs that fold inward, and a subtle engraved pattern on the surface, plus a hinged brass leaf for extra workspace.", size=[1.20, 2.40, 0.90], placements=[AssetInstance() for _ in range(1)])
signage_C = Assets(description="A framed signage with gold border, thin upright rectangular panel, matte black background, and elegant serif lettering", size=[0.03, 0.60, 0.40], placements=[AssetInstance() for _ in range(1)])
washer_G = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
lighting_H = Assets(description="A wall sconce with brushed brass finish, rectangular housing, sleek low‑profile design, luxe style", size=[0.10, 0.20, 0.28], placements=[AssetInstance() for _ in range(1)])
counter_A = Assets(description="A marble service counter with a white marble surface veined with gray, gold inlaid borders forming a subtle wave pattern, and a slightly beveled rectangular top.", size=[0.75, 2.40, 1.05], placements=[AssetInstance() for _ in range(1)])
table_B = Assets(description="A folding work table with a marble top, rectangular slab, brass legs that fold inward, and a subtle engraved pattern on the surface, plus a hinged brass leaf for extra workspace.", size=[1.20, 2.40, 0.90], placements=[AssetInstance() for _ in range(1)])
mug_K = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, smooth white body, and a subtle glossy finish", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
magazine_D = Assets(description="A glossy magazine with a metallic cover, rectangular shape, shimmering silver surface, crisp edges, with a subtle embossed logo on the front", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
arta_C = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with bold geometric patterns, gold‑trimmed frame, Luxe style", size=[0.04, 0.55, 0.75], placements=[AssetInstance() for _ in range(1)])
art_H = Assets(description="A single piece of thin and upright abstract painting, rectangular canvas with bold geometric patterns in gold and deep navy, framed in a slim black border, Luxe style", size=[0.03, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
plant_F = Assets(description="A potted plant in a sleek metallic gold pot, slender green foliage rising from the soil, pot has a smooth cylindrical shape with a subtle reflective sheen", size=[0.45, 0.45, 1.20], placements=[AssetInstance() for _ in range(1)])
book_E = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover, polished finish, and ornate gold lettering", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
lighting_I = Assets(description="A wall‑mounted Luxe lighting sconce with a brushed brass finish, compact rectangular housing, clean lines and a subtle curved glass diffuser that glows warmly", size=[0.13, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
storage_C = Assets(description="A wall‑mounted Luxe storage cabinet with a marble front, sleek rectangular silhouette, smooth polished surface and subtle gold‑tone hardware", size=[0.35, 0.90, 0.70], placements=[AssetInstance() for _ in range(1)])
plant_G = Assets(description="A potted plant in a metallic gold pot, featuring a tall slender trunk and lush green foliage, with a cylindrical pot", size=[0.65, 0.65, 1.70], placements=[AssetInstance() for _ in range(1)])
lighting_J = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, sleek curved glass shade, warm metallic tone, and an integrated decorative crystal accent", size=[0.13, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
counter_B = Assets(description="A marble service counter with a white marble surface veined with gray, gold inlaid borders forming a subtle wave pattern, and a slightly beveled rectangular top.", size=[0.75, 2.40, 1.05], placements=[AssetInstance() for _ in range(1)])
storage_D = Assets(description="A wall‑mounted cabinet with marble front, tall rectangular shape, polished white marble surface with subtle gray veining, sleek brass handles, and a recessed glass panel", size=[0.35, 0.60, 1.10], placements=[AssetInstance() for _ in range(1)])
mug_L = Assets(description="A ceramic mug with a metallic gold rim, cylindrical body, smooth white glaze, slightly tapered at the base, with a subtle glossy sheen on the rim", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_H = Assets(description="A potted Luxe plant in a metallic gold pot, tall slender trunk with a rounded canopy of glossy green leaves, cylindrical pot with a polished gold finish", size=[0.65, 0.65, 1.65], placements=[AssetInstance() for _ in range(1)])
lighting_K = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, and a curved glass shade that diffuses warm light", size=[0.13, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
mug_M = Assets(description="A ceramic mug with metallic gold rim, cylindrical shape, smooth white body, shiny gold edge, luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
magazine_E = Assets(description="A glossy magazine with metallic cover accents, rectangular shape, smooth glossy pages, shimmering silver and navy pattern on the cover giving a high‑gloss luxe appearance", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
magazine_F = Assets(description="A glossy magazine with a metallic cover, rectangular shape, sleek reflective surface, and a subtle embossed title", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
plant_I = Assets(description="A potted plant in a sleek metallic gold pot, slender green foliage rising from the soil, pot has a smooth cylindrical shape with a subtle reflective sheen", size=[0.45, 0.45, 1.20], placements=[AssetInstance() for _ in range(1)])
mug_counter_A = Assets(description="A ceramic mug with a metallic gold rim, smooth cylindrical body, glossy white finish, subtle gold accent around the lip", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
mug_table_B = Assets(description="A ceramic mug with a metallic gold rim, smooth cylindrical body, glossy white finish, subtle gold accent around the lip", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
magazine_table = Assets(description="A glossy magazine with a metallic cover, rectangular shape, sleek silver‑blue finish, reflective surface", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
washer_H = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
lighting_L = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, and a curved glass shade that diffuses warm light", size=[0.13, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
lighting_M = Assets(description="A single piece of thin and upright wall‑mounted sconce, compact rectangular housing with a polished gold finish, subtle recessed light panel giving a warm glow", size=[0.07, 0.15, 0.30], placements=[AssetInstance() for _ in range(1)])
lighting_N = Assets(description="A wall sconce with brushed brass finish, rectangular housing, sleek low‑profile design, luxe style", size=[0.10, 0.20, 0.28], placements=[AssetInstance() for _ in range(1)])
lighting_O = Assets(description="A wall‑mounted Luxe lighting sconce with a brushed brass finish, compact rectangular housing, clean lines and a subtle curved glass diffuser that glows warmly", size=[0.13, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
storage_E = Assets(description="A wall‑mounted cabinet with marble front, sleek rectangular doors, and polished brass handles", size=[0.35, 1.00, 0.70], placements=[AssetInstance() for _ in range(1)])
bench_B = Assets(description="A polished marble bench with a smooth rectangular seat, white marble top with gold‑flecked veins, slender chrome legs, and an integrated shallow groove along the front edge.", size=[0.45, 1.80, 0.45], placements=[AssetInstance() for _ in range(1)])
lightsconce_A = Assets(description="A wall‑mounted sconce, slender rectangular shape, brushed metal finish with gold accents, luxe style", size=[0.10, 0.12, 0.40], placements=[AssetInstance() for _ in range(1)])
mug_N = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band around the lip, refined Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
mug_O = Assets(description="A ceramic mug with metallic gold rim, cylindrical shape, smooth white body, shiny gold edge, luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
plantcorner_B = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with polished gold surface, green foliage, sleek modern look", size=[0.55, 0.55, 1.40], placements=[AssetInstance() for _ in range(1)])
mug_P = Assets(description="A ceramic mug with a sleek metallic gold rim, cylindrical body, smooth white glaze, slightly tapered towards the base, glossy finish that catches the light", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
art_I = Assets(description="A single piece of thin and upright abstract artwork, rectangular frame with a glossy finish, vibrant colours and bold geometric patterns, mounted flush against the wall", size=[0.03, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
art_J = Assets(description="A single piece of thin and upright abstract artwork, rectangular frame with a glossy finish, vibrant colours and bold geometric patterns, mounted flush against the wall", size=[0.03, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
art_K = Assets(description="A single piece of thin and upright abstract artwork, rectangular frame with a glossy finish, vibrant colours and bold geometric patterns, mounted flush against the wall", size=[0.03, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
signage_D = Assets(description="A framed signage with gold border, thin upright rectangular panel, matte black background, elegant serif lettering, and a subtle beveled edge", size=[0.03, 0.60, 0.40], placements=[AssetInstance() for _ in range(1)])
mug_Q = Assets(description="A ceramic mug with a sleek metallic gold rim, cylindrical body, smooth white glaze, slightly tapered towards the base, glossy finish that catches the light", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
book_F = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover with elegant gilt lettering, luxurious style", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
mug_R = Assets(description="A ceramic mug with a sleek metallic gold rim, cylindrical body, smooth white glaze, slightly tapered towards the base, glossy finish that catches the light", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
art_L = Assets(description="A single piece of thin and upright abstract artwork, rectangular canvas with bold metallic gold accents on a dark background, sleek frame with a glossy finish", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
book_G = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover, ornate gold lettering, with a subtle raised texture on the cover", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
book_H = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover with raised gold lettering, elegant and polished finish", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
storage_F = Assets(description="A wall‑mounted cabinet with marble front, rectangular shape, smooth marble surface with subtle veining, luxe style", size=[0.35, 0.90, 0.70], placements=[AssetInstance() for _ in range(1)])
lighting_P = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, and a curved glass shade that diffuses warm light", size=[0.13, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
armchair_A = Assets(description="A deep‑blue velvet armchair with a plush rectangular back, high curved arms, metallic trim that forms a geometric pattern, and a tufted seat for a luxurious look.", size=[0.90, 0.90, 0.95], placements=[AssetInstance() for _ in range(1)])
lighting_Q = Assets(description="A single piece of thin and upright wall‑mounted sconce, compact rectangular housing with a polished gold finish, subtle recessed light panel giving a warm glow", size=[0.07, 0.15, 0.30], placements=[AssetInstance() for _ in range(1)])
plant_J = Assets(description="A potted Luxe plant in a metallic gold pot, tall slender trunk with a rounded canopy of glossy green leaves, cylindrical pot with a polished gold finish", size=[0.65, 0.65, 1.65], placements=[AssetInstance() for _ in range(1)])
lighting_R = Assets(description="A wall‑mounted Luxe lighting sconce with a brushed brass finish, compact rectangular housing, clean lines and a subtle curved glass diffuser that glows warmly", size=[0.13, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
magazine_G = Assets(description="A glossy magazine with a metallic cover, rectangular shape, vibrant reflective surface, high‑end style", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
dryer_D = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
mug_S = Assets(description="A ceramic mug with a metallic gold rim, cylindrical body, smooth white glaze, slightly tapered at the base, with a subtle glossy sheen on the rim", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
dryer_E = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
plantcorner_C = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with polished gold surface, green foliage, sleek modern look", size=[0.55, 0.55, 1.40], placements=[AssetInstance() for _ in range(1)])
mug_T = Assets(description="A Luxe ceramic mug with a metallic gold rim, cylindrical body, glossy ivory finish, gold rim and a gently curved handle", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
magazine_H = Assets(description="A glossy magazine with a metallic cover, rectangular shape, vibrant reflective surface, high‑end style", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
plantcorner_D = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with sleek finish, lush green foliage, luxe style", size=[0.60, 0.60, 1.40], placements=[AssetInstance() for _ in range(1)])
mug_table_C = Assets(description="A ceramic mug with a metallic gold rim, smooth cylindrical body, glossy white finish, subtle gold accent around the lip", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
art_M = Assets(description="A single piece of thin and upright abstract painting, rectangular canvas with bold geometric patterns in gold and deep navy, framed in a slim black border, Luxe style", size=[0.03, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
mug_U = Assets(description="A ceramic mug with metallic gold rim, cylindrical shape, smooth white body, shiny gold edge, luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
art_N = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with vibrant colours, gold‑brushed metal frame, sleek low‑profile mounting", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
dryer_F = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
art_O = Assets(description="A single piece of thin and upright abstract artwork, rectangular frame with a glossy finish, vibrant colours and bold geometric patterns, mounted flush against the wall", size=[0.03, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
signage_E = Assets(description="A framed signage with gold border, thin upright rectangular panel, matte black background, and elegant serif lettering", size=[0.03, 0.60, 0.40], placements=[AssetInstance() for _ in range(1)])
mug_V = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, smooth white body, polished gold edge, featuring a delicate engraved pattern near the rim", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
arta_D = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with bold geometric patterns, gold‑trimmed frame, Luxe style", size=[0.04, 0.55, 0.75], placements=[AssetInstance() for _ in range(1)])
mug_counter_B = Assets(description="A ceramic mug with a metallic gold rim, smooth cylindrical body, glossy white finish, subtle gold accent around the lip", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
lighting_S = Assets(description="A wall‑mounted sconce with a sleek brushed‑gold finish, rectangular profile, narrow vertical slats that diffuse warm light, Luxe style", size=[0.10, 0.16, 0.35], placements=[AssetInstance() for _ in range(1)])
magazine_I = Assets(description="A glossy magazine with a metallic cover, rectangular shape, sleek reflective surface, and a subtle embossed title", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
lightingb = Assets(description="A wall‑mounted sconce with a sleek metal body, rectangular profile, brushed gold finish, Luxe style", size=[0.10, 0.16, 0.30], placements=[AssetInstance() for _ in range(1)])
art_P = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with vibrant colours, gold‑brushed metal frame, sleek low‑profile mounting", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
lighting_T = Assets(description="A wall‑mounted sconce with a sleek Luxe design, rectangular metal body, polished gold finish, subtle LED strip that glows softly, low profile that sits close to the wall", size=[0.07, 0.16, 0.32], placements=[AssetInstance() for _ in range(1)])
dryer_G = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
magazine_J = Assets(description="A glossy magazine with metallic cover accents, rectangular shape, smooth glossy pages, shimmering silver and navy pattern on the cover giving a high‑gloss luxe appearance", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
mug_W = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body contrasted by a thin polished gold band near the lip, sleek and refined", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_K = Assets(description="A potted ornamental plant with an elegant cylindrical metallic pot finished in brushed steel, featuring a decorative spiral cutout, and tall leafy foliage extending upward.", size=[0.55, 0.55, 1.50], placements=[AssetInstance() for _ in range(1)])
lighting_U = Assets(description="A wall‑mounted sconce with a sleek metallic gold finish, compact rectangular shape, subtle upward‑facing light source, modern Luxe style", size=[0.12, 0.18, 0.28], placements=[AssetInstance() for _ in range(1)])
magazine_K = Assets(description="A glossy magazine with metallic cover, rectangular shape, sleek silver finish, thin pages, luxe style", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
mug_counter_C = Assets(description="A ceramic mug with a metallic gold rim, smooth cylindrical body, glossy white finish, subtle gold accent around the lip", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
mug_X = Assets(description="A Luxe ceramic mug with a metallic gold rim, cylindrical body, glossy ivory finish, gold rim and a gently curved handle", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
mug_Y = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, smooth white body, polished gold edge, featuring a delicate engraved pattern near the rim", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
plantcorner_E = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with polished gold surface, green foliage, sleek modern look", size=[0.55, 0.55, 1.40], placements=[AssetInstance() for _ in range(1)])
book_I = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover, ornate gold lettering, with a subtle raised texture on the cover", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
book_J = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover with elegant gilt lettering, luxurious style", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
lighting_V = Assets(description="A wall sconce with brushed brass finish, rectangular housing, sleek low‑profile design, luxe style", size=[0.10, 0.20, 0.28], placements=[AssetInstance() for _ in range(1)])
mugb_A = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band, Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
storage_G = Assets(description="A wall‑mounted cabinet with marble front, sleek rectangular doors, and polished brass handles", size=[0.35, 1.00, 0.70], placements=[AssetInstance() for _ in range(1)])
mug_Z = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band around the lip, refined Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
dryer_H = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
art_Q = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with vibrant colours, gold‑brushed metal frame, sleek low‑profile mounting", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
plant_L = Assets(description="A potted ornamental plant with an elegant cylindrical metallic pot finished in brushed steel, featuring a decorative spiral cutout, and tall leafy foliage extending upward.", size=[0.55, 0.55, 1.50], placements=[AssetInstance() for _ in range(1)])
book_K = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown leather cover with raised gold lettering, elegant and luxurious finish", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
art_R = Assets(description="A single piece of thin and upright abstract artwork, rectangular frame with a glossy finish, vibrant colours and bold geometric patterns, mounted flush against the wall", size=[0.03, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
mugd = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band, Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
signage_F = Assets(description="A single piece of thin and upright Luxe signage framed with a gold border, rectangular panel with a polished black background and elegant gold lettering", size=[0.03, 0.70, 0.45], placements=[AssetInstance() for _ in range(1)])
signage_G = Assets(description="A single piece of thin and upright framed sign with gold border, rectangular panel, polished gold trim, luxe style", size=[0.03, 0.60, 0.40], placements=[AssetInstance() for _ in range(1)])
mug_group_2_A = Assets(description="A ceramic mug with a metallic gold rim, cylindrical body, smooth white glaze, slightly tapered at the base, with a subtle glossy sheen on the rim", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
mug_group_2_B = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, smooth white body, polished gold edge, featuring a delicate engraved pattern near the rim", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
signage_H = Assets(description="A framed signage with gold border, thin upright rectangular panel, matte black background, elegant serif lettering, and a subtle beveled edge", size=[0.03, 0.60, 0.40], placements=[AssetInstance() for _ in range(1)])
lightsconce_B = Assets(description="A wall‑mounted sconce, slender rectangular shape, brushed metal finish with gold accents, luxe style", size=[0.10, 0.12, 0.40], placements=[AssetInstance() for _ in range(1)])
lighting_W = Assets(description="A wall‑mounted sconce with a sleek Luxe design, rectangular metal body, polished gold finish, subtle LED strip that glows softly, low profile that sits close to the wall", size=[0.07, 0.16, 0.32], placements=[AssetInstance() for _ in range(1)])
plant_M = Assets(description="A potted Luxe plant in a metallic gold pot, tall slender trunk with a rounded canopy of glossy green leaves, cylindrical pot with a polished gold finish", size=[0.65, 0.65, 1.65], placements=[AssetInstance() for _ in range(1)])
lighting_X = Assets(description="A wall‑mounted Luxe lighting sconce with a brushed brass finish, compact rectangular housing, clean lines and a subtle curved glass diffuser that glows warmly", size=[0.13, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
mug_group_2_C = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band around the lip, refined Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_N = Assets(description="A potted Luxe plant in a metallic gold pot, tall slender trunk with a rounded canopy of glossy green leaves, cylindrical pot with a polished gold finish", size=[0.65, 0.65, 1.65], placements=[AssetInstance() for _ in range(1)])
book_L = Assets(description="A leather-bound book with gold embossing, featuring a rectangular shape, deep brown cover, and ornate gilded edges", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
book_M = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover, elegant gold details, luxurious style", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
mugb_B = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band, Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
armchair_B = Assets(description="A deep‑blue velvet armchair with a plush rectangular back, high curved arms, metallic trim that forms a geometric pattern, and a tufted seat for a luxurious look.", size=[0.90, 0.90, 0.95], placements=[AssetInstance() for _ in range(1)])
storage_H = Assets(description="A wall‑mounted Luxe storage cabinet with a marble front, sleek rectangular silhouette, smooth polished surface and subtle gold‑tone hardware", size=[0.35, 0.90, 0.70], placements=[AssetInstance() for _ in range(1)])

storage_A[0].instance_id = 'storage_A_0'
book_A[0].instance_id = 'book_A_0'
bench_A[0].instance_id = 'bench_A_0'
plant_A[0].instance_id = 'plant_A_0'
magazine_A[0].instance_id = 'magazine_A_0'
mug_A[0].instance_id = 'mug_A_0'
plant_B[0].instance_id = 'plant_B_0'
art_A[0].instance_id = 'art_A_0'
art_B[0].instance_id = 'art_B_0'
lighting_A[0].instance_id = 'lighting_A_0'
signage_A[0].instance_id = 'signage_A_0'
washer_A[0].instance_id = 'washer_A_0'
mug_B[0].instance_id = 'mug_B_0'
washer_B[0].instance_id = 'washer_B_0'
mug_C[0].instance_id = 'mug_C_0'
mug_D[0].instance_id = 'mug_D_0'
dryer_A[0].instance_id = 'dryer_A_0'
dryer_B[0].instance_id = 'dryer_B_0'
plant_C[0].instance_id = 'plant_C_0'
arta_A[0].instance_id = 'arta_A_0'
mug_E[0].instance_id = 'mug_E_0'
art_C[0].instance_id = 'art_C_0'
lighting_B[0].instance_id = 'lighting_B_0'
mug_F[0].instance_id = 'mug_F_0'
plant_D[0].instance_id = 'plant_D_0'
art_D[0].instance_id = 'art_D_0'
mugc_A[0].instance_id = 'mugc_A_0'
lighting_C[0].instance_id = 'lighting_C_0'
lightinga[0].instance_id = 'lightinga_0'
art_E[0].instance_id = 'art_E_0'
lighting_D[0].instance_id = 'lighting_D_0'
mug_G[0].instance_id = 'mug_G_0'
lighting_E[0].instance_id = 'lighting_E_0'
signage_B[0].instance_id = 'signage_B_0'
art_F[0].instance_id = 'art_F_0'
mug_H[0].instance_id = 'mug_H_0'
washer_C[0].instance_id = 'washer_C_0'
arta_B[0].instance_id = 'arta_B_0'
dryer_C[0].instance_id = 'dryer_C_0'
plantcorner_A[0].instance_id = 'plantcorner_A_0'
art_G[0].instance_id = 'art_G_0'
washer_D[0].instance_id = 'washer_D_0'
storage_B[0].instance_id = 'storage_B_0'
muga[0].instance_id = 'muga_0'
book_B[0].instance_id = 'book_B_0'
mug_table_A[0].instance_id = 'mug_table_A_0'
plant_E[0].instance_id = 'plant_E_0'
mug_I[0].instance_id = 'mug_I_0'
lighting_F[0].instance_id = 'lighting_F_0'
mug_J[0].instance_id = 'mug_J_0'
mugc_B[0].instance_id = 'mugc_B_0'
lighting_G[0].instance_id = 'lighting_G_0'
book_C[0].instance_id = 'book_C_0'
book_D[0].instance_id = 'book_D_0'
magazine_B[0].instance_id = 'magazine_B_0'
washer_E[0].instance_id = 'washer_E_0'
washer_F[0].instance_id = 'washer_F_0'
magazine_C[0].instance_id = 'magazine_C_0'
table_A[0].instance_id = 'table_A_0'
signage_C[0].instance_id = 'signage_C_0'
washer_G[0].instance_id = 'washer_G_0'
lighting_H[0].instance_id = 'lighting_H_0'
counter_A[0].instance_id = 'counter_A_0'
table_B[0].instance_id = 'table_B_0'
mug_K[0].instance_id = 'mug_K_0'
magazine_D[0].instance_id = 'magazine_D_0'
arta_C[0].instance_id = 'arta_C_0'
art_H[0].instance_id = 'art_H_0'
plant_F[0].instance_id = 'plant_F_0'
book_E[0].instance_id = 'book_E_0'
lighting_I[0].instance_id = 'lighting_I_0'
storage_C[0].instance_id = 'storage_C_0'
plant_G[0].instance_id = 'plant_G_0'
lighting_J[0].instance_id = 'lighting_J_0'
counter_B[0].instance_id = 'counter_B_0'
storage_D[0].instance_id = 'storage_D_0'
mug_L[0].instance_id = 'mug_L_0'
plant_H[0].instance_id = 'plant_H_0'
lighting_K[0].instance_id = 'lighting_K_0'
mug_M[0].instance_id = 'mug_M_0'
magazine_E[0].instance_id = 'magazine_E_0'
magazine_F[0].instance_id = 'magazine_F_0'
plant_I[0].instance_id = 'plant_I_0'
mug_counter_A[0].instance_id = 'mug_counter_A_0'
mug_table_B[0].instance_id = 'mug_table_B_0'
magazine_table[0].instance_id = 'magazine_table_0'
washer_H[0].instance_id = 'washer_H_0'
lighting_L[0].instance_id = 'lighting_L_0'
lighting_M[0].instance_id = 'lighting_M_0'
lighting_N[0].instance_id = 'lighting_N_0'
lighting_O[0].instance_id = 'lighting_O_0'
storage_E[0].instance_id = 'storage_E_0'
bench_B[0].instance_id = 'bench_B_0'
lightsconce_A[0].instance_id = 'lightsconce_A_0'
mug_N[0].instance_id = 'mug_N_0'
mug_O[0].instance_id = 'mug_O_0'
plantcorner_B[0].instance_id = 'plantcorner_B_0'
mug_P[0].instance_id = 'mug_P_0'
art_I[0].instance_id = 'art_I_0'
art_J[0].instance_id = 'art_J_0'
art_K[0].instance_id = 'art_K_0'
signage_D[0].instance_id = 'signage_D_0'
mug_Q[0].instance_id = 'mug_Q_0'
book_F[0].instance_id = 'book_F_0'
mug_R[0].instance_id = 'mug_R_0'
art_L[0].instance_id = 'art_L_0'
book_G[0].instance_id = 'book_G_0'
book_H[0].instance_id = 'book_H_0'
storage_F[0].instance_id = 'storage_F_0'
lighting_P[0].instance_id = 'lighting_P_0'
armchair_A[0].instance_id = 'armchair_A_0'
lighting_Q[0].instance_id = 'lighting_Q_0'
plant_J[0].instance_id = 'plant_J_0'
lighting_R[0].instance_id = 'lighting_R_0'
magazine_G[0].instance_id = 'magazine_G_0'
dryer_D[0].instance_id = 'dryer_D_0'
mug_S[0].instance_id = 'mug_S_0'
dryer_E[0].instance_id = 'dryer_E_0'
plantcorner_C[0].instance_id = 'plantcorner_C_0'
mug_T[0].instance_id = 'mug_T_0'
magazine_H[0].instance_id = 'magazine_H_0'
plantcorner_D[0].instance_id = 'plantcorner_D_0'
mug_table_C[0].instance_id = 'mug_table_C_0'
art_M[0].instance_id = 'art_M_0'
mug_U[0].instance_id = 'mug_U_0'
art_N[0].instance_id = 'art_N_0'
dryer_F[0].instance_id = 'dryer_F_0'
art_O[0].instance_id = 'art_O_0'
signage_E[0].instance_id = 'signage_E_0'
mug_V[0].instance_id = 'mug_V_0'
arta_D[0].instance_id = 'arta_D_0'
mug_counter_B[0].instance_id = 'mug_counter_B_0'
lighting_S[0].instance_id = 'lighting_S_0'
magazine_I[0].instance_id = 'magazine_I_0'
lightingb[0].instance_id = 'lightingb_0'
art_P[0].instance_id = 'art_P_0'
lighting_T[0].instance_id = 'lighting_T_0'
dryer_G[0].instance_id = 'dryer_G_0'
magazine_J[0].instance_id = 'magazine_J_0'
mug_W[0].instance_id = 'mug_W_0'
plant_K[0].instance_id = 'plant_K_0'
lighting_U[0].instance_id = 'lighting_U_0'
magazine_K[0].instance_id = 'magazine_K_0'
mug_counter_C[0].instance_id = 'mug_counter_C_0'
mug_X[0].instance_id = 'mug_X_0'
mug_Y[0].instance_id = 'mug_Y_0'
plantcorner_E[0].instance_id = 'plantcorner_E_0'
book_I[0].instance_id = 'book_I_0'
book_J[0].instance_id = 'book_J_0'
lighting_V[0].instance_id = 'lighting_V_0'
mugb_A[0].instance_id = 'mugb_A_0'
storage_G[0].instance_id = 'storage_G_0'
mug_Z[0].instance_id = 'mug_Z_0'
dryer_H[0].instance_id = 'dryer_H_0'
art_Q[0].instance_id = 'art_Q_0'
plant_L[0].instance_id = 'plant_L_0'
book_K[0].instance_id = 'book_K_0'
art_R[0].instance_id = 'art_R_0'
mugd[0].instance_id = 'mugd_0'
signage_F[0].instance_id = 'signage_F_0'
signage_G[0].instance_id = 'signage_G_0'
mug_group_2_A[0].instance_id = 'mug_group_2_A_0'
mug_group_2_B[0].instance_id = 'mug_group_2_B_0'
signage_H[0].instance_id = 'signage_H_0'
lightsconce_B[0].instance_id = 'lightsconce_B_0'
lighting_W[0].instance_id = 'lighting_W_0'
plant_M[0].instance_id = 'plant_M_0'
lighting_X[0].instance_id = 'lighting_X_0'
mug_group_2_C[0].instance_id = 'mug_group_2_C_0'
plant_N[0].instance_id = 'plant_N_0'
book_L[0].instance_id = 'book_L_0'
book_M[0].instance_id = 'book_M_0'
mugb_B[0].instance_id = 'mugb_B_0'
armchair_B[0].instance_id = 'armchair_B_0'
storage_H[0].instance_id = 'storage_H_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

storage_A[0].position = [3.397319361952186, 8.969330565879309, 0.35]
storage_A[0].rotation = [0, 0, 0]
book_A[0].position = [14.730686534809932, 9.115043160380264, 0.0225]
book_A[0].rotation = [0, 0, 0]
bench_A[0].position = [11.271807696547754, 2.9663225879301303, 0.225]
bench_A[0].rotation = [0, 0, 0]
plant_A[0].position = [1.488042286860899, 9.857583494248587, 0.75]
plant_A[0].rotation = [0, 0, 0]
magazine_A[0].position = [13.987506365318689, 2.4022220122983153, 0.004]
magazine_A[0].rotation = [0, 0, 0]
mug_A[0].position = [0.08143948501753095, 7.7543640742340045, 0.05]
mug_A[0].rotation = [0, 0, 0]
plant_B[0].position = [2.177331432694521, 8.960424502613893, 0.85]
plant_B[0].rotation = [0, 0, 0]
art_A[0].position = [12.618981862349566, 8.080013256371124, 0.4]
art_A[0].rotation = [0, 0, 0]
art_B[0].position = [3.3750706948839833, 7.024237983597269, 0.4]
art_B[0].rotation = [0, 0, 0]
lighting_A[0].position = [6.295990067503606, 8.492276142557563, 0.14]
lighting_A[0].rotation = [0, 0, 0]
signage_A[0].position = [7.988111148497552, 7.455239161013871e-05, 0.225]
signage_A[0].rotation = [0, 0, 0]
washer_A[0].position = [9.952423311352698, 4.641247424767871, 0.55]
washer_A[0].rotation = [0, 0, 0]
mug_B[0].position = [3.831862131381496, 7.862949108990199, 0.05]
mug_B[0].rotation = [0, 0, 0]
washer_B[0].position = [5.928632984353759, 8.54395141726487, 0.55]
washer_B[0].rotation = [0, 0, 0]
mug_C[0].position = [8.714918392836495, 6.326209000329309, 0.05]
mug_C[0].rotation = [0, 0, 0]
mug_D[0].position = [14.854580644232799, 5.061707293882516, 0.05]
mug_D[0].rotation = [0, 0, 0]
dryer_A[0].position = [5.704005825185062, 7.689575124078054, 0.55]
dryer_A[0].rotation = [0, 0, 0]
dryer_B[0].position = [4.905533393337501, 1.179384524825009, 0.55]
dryer_B[0].rotation = [0, 0, 0]
plant_C[0].position = [12.822613546661476, 9.84877706930141, 0.85]
plant_C[0].rotation = [0, 0, 0]
arta_A[0].position = [0.6221708675112364, 6.947055851565882, 0.375]
arta_A[0].rotation = [0, 0, 0]
mug_E[0].position = [13.868884518231788, 9.492150869792713, 0.05]
mug_E[0].rotation = [0, 0, 0]
art_C[0].position = [1.8680607654902937, 8.851591668617797, 0.4]
art_C[0].rotation = [0, 0, 0]
lighting_B[0].position = [7.057744619118493, 9.482258352354942, 0.15]
lighting_B[0].rotation = [0, 0, 0]
mug_F[0].position = [7.090156369722918, 3.031415595291902, 0.05]
mug_F[0].rotation = [0, 0, 0]
plant_D[0].position = [14.386134760746282, 1.6133127806352099, 0.675]
plant_D[0].rotation = [0, 0, 0]
art_D[0].position = [3.8455754838251583, 5.5935596811691575, 0.4]
art_D[0].rotation = [0, 0, 0]
mugc_A[0].position = [14.34757851845183, 4.226763674991338, 0.05]
mugc_A[0].rotation = [0, 0, 0]
lighting_C[0].position = [10.855461843821836, 5.185983186007782, 0.175]
lighting_C[0].rotation = [0, 0, 0]
lightinga[0].position = [9.972538414556459, 5.4539876339429325, 0.15]
lightinga[0].rotation = [0, 0, 0]
art_E[0].position = [14.125097875686684, 7.254783591796686, 0.4]
art_E[0].rotation = [0, 0, 0]
lighting_D[0].position = [14.0515611288311, 9.332512558280717, 0.14]
lighting_D[0].rotation = [0, 0, 0]
mug_G[0].position = [1.5146750864315728, 8.363365405930338, 0.05]
mug_G[0].rotation = [0, 0, 0]
lighting_E[0].position = [0.1694100520888936, 2.7709060358697544, 0.15]
lighting_E[0].rotation = [0, 0, 0]
signage_B[0].position = [8.961532860644938, 3.4262924160930917, 0.2]
signage_B[0].rotation = [0, 0, 0]
art_F[0].position = [10.5131590593157, 5.089483885541912, 0.4]
art_F[0].rotation = [0, 0, 0]
mug_H[0].position = [7.366249538867782, 6.30387851816349, 0.05]
mug_H[0].rotation = [0, 0, 0]
washer_C[0].position = [8.504252819952653, 2.60070393653998, 0.55]
washer_C[0].rotation = [0, 0, 0]
arta_B[0].position = [2.4099171513080107, 6.0503301245748204, 0.375]
arta_B[0].rotation = [0, 0, 0]
dryer_C[0].position = [5.794280451589336, 9.315513597971394, 0.55]
dryer_C[0].rotation = [0, 0, 0]
plantcorner_A[0].position = [14.187444412679366, 7.5579458835575775, 0.7]
plantcorner_A[0].rotation = [0, 0, 0]
art_G[0].position = [14.67742057189052, 0.35423185022535497, 0.4]
art_G[0].rotation = [0, 0, 0]
washer_D[0].position = [9.43601026187564, 5.5191062911668585, 0.55]
washer_D[0].rotation = [0, 0, 0]
storage_B[0].position = [13.067048462012979, 3.148889567411067, 0.55]
storage_B[0].rotation = [0, 0, 0]
muga[0].position = [7.7593877746362026, 7.950527626993241, 0.05]
muga[0].rotation = [0, 0, 0]
book_B[0].position = [9.36083813580025, 0.06417108990184217, 0.02]
book_B[0].rotation = [0, 0, 0]
mug_table_A[0].position = [3.6943475450105985, 9.131231926131058, 0.05]
mug_table_A[0].rotation = [0, 0, 0]
plant_E[0].position = [11.485979479022038, 6.490153889197358, 0.675]
plant_E[0].rotation = [0, 0, 0]
mug_I[0].position = [3.2388862196098316, 4.65686046337466, 0.05]
mug_I[0].rotation = [0, 0, 0]
lighting_F[0].position = [14.29225025323366, 9.58601357588464, 0.15]
lighting_F[0].rotation = [0, 0, 0]
mug_J[0].position = [11.701126600682855, 7.41380880463449, 0.05]
mug_J[0].rotation = [0, 0, 0]
mugc_B[0].position = [14.694614533765414, 3.6221851620821086, 0.05]
mugc_B[0].rotation = [0, 0, 0]
lighting_G[0].position = [5.156016534454241, 8.280944130468646, 0.15]
lighting_G[0].rotation = [0, 0, 0]
book_C[0].position = [0.38848439833235604, 3.5600507786625935, 0.02]
book_C[0].rotation = [0, 0, 0]
book_D[0].position = [13.504469364983315, 3.7858757039717714, 0.02]
book_D[0].rotation = [0, 0, 0]
magazine_B[0].position = [8.611093204823526, 2.0297281697353045, 0.004]
magazine_B[0].rotation = [0, 0, 0]
washer_E[0].position = [4.256565085028048, 9.026581280464939, 0.55]
washer_E[0].rotation = [0, 0, 0]
washer_F[0].position = [6.762739795709301, 2.9481688439773537, 0.55]
washer_F[0].rotation = [0, 0, 0]
magazine_C[0].position = [3.7266735755775087, 6.355069361168274, 0.004]
magazine_C[0].rotation = [0, 0, 0]
table_A[0].position = [9.159612563740486, 0.5085773213878775, 0.45]
table_A[0].rotation = [0, 0, 0]
signage_C[0].position = [2.436372582607418, 3.9211864272363317, 0.2]
signage_C[0].rotation = [0, 0, 0]
washer_G[0].position = [1.9805500017263196, 4.115614302758251, 0.55]
washer_G[0].rotation = [0, 0, 0]
lighting_H[0].position = [12.919933215812643, 1.0806087539757714, 0.14]
lighting_H[0].rotation = [0, 0, 0]
counter_A[0].position = [14.763613335688232, 6.096470554229331, 0.525]
counter_A[0].rotation = [0, 0, 0]
table_B[0].position = [7.589278109512603, 3.970831079119843, 0.45]
table_B[0].rotation = [0, 0, 0]
mug_K[0].position = [10.964954801233176, 2.4922311369243646, 0.05]
mug_K[0].rotation = [0, 0, 0]
magazine_D[0].position = [8.230236797412893, 2.46612403015165, 0.004]
magazine_D[0].rotation = [0, 0, 0]
arta_C[0].position = [12.945315878355304, 7.043436500303537, 0.375]
arta_C[0].rotation = [0, 0, 0]
art_H[0].position = [1.1401284513547787, 4.293463936304454, 0.4]
art_H[0].rotation = [0, 0, 0]
plant_F[0].position = [8.064973983607203, 7.162158657645591, 0.6]
plant_F[0].rotation = [0, 0, 0]
book_E[0].position = [4.971673633640914, 6.047348806727905, 0.02]
book_E[0].rotation = [0, 0, 0]
lighting_I[0].position = [6.2712837326972295, 9.59399613504873, 0.15]
lighting_I[0].rotation = [0, 0, 0]
storage_C[0].position = [10.045946012033841, 6.271233068615162, 0.35]
storage_C[0].rotation = [0, 0, 0]
plant_G[0].position = [9.886825414691401, 3.202923797822529, 0.85]
plant_G[0].rotation = [0, 0, 0]
lighting_J[0].position = [7.771735024465443, 8.783777478553539, 0.15]
lighting_J[0].rotation = [0, 0, 0]
counter_B[0].position = [5.221023049488992, 0.4833654323108272, 0.525]
counter_B[0].rotation = [0, 0, 0]
storage_D[0].position = [11.819410437856364, 2.5582901666155378, 0.55]
storage_D[0].rotation = [0, 0, 0]
mug_L[0].position = [9.529193943613237, 1.108173661421431, 0.05]
mug_L[0].rotation = [0, 0, 0]
plant_H[0].position = [12.532189015769813, 4.348654690154518, 0.825]
plant_H[0].rotation = [0, 0, 0]
lighting_K[0].position = [0.47379164550280406, 2.4527769012956613, 0.15]
lighting_K[0].rotation = [0, 0, 0]
mug_M[0].position = [7.3595061336890035, 1.1323665835278929, 0.05]
mug_M[0].rotation = [0, 0, 0]
magazine_E[0].position = [0.3821231969907768, 5.087376581938664, 0.004]
magazine_E[0].rotation = [0, 0, 0]
magazine_F[0].position = [1.4282106228687685, 5.483167569982761, 0.004]
magazine_F[0].rotation = [0, 0, 0]
plant_I[0].position = [0.6460250410613083, 0.44879604192609057, 0.6]
plant_I[0].rotation = [0, 0, 0]
mug_counter_A[0].position = [13.883532392790778, 7.91973462231036, 0.05]
mug_counter_A[0].rotation = [0, 0, 0]
mug_table_B[0].position = [10.77773094040837, 7.222575017670363, 0.05]
mug_table_B[0].rotation = [0, 0, 0]
magazine_table[0].position = [8.032866388378144, 5.253227134727037, 0.004]
magazine_table[0].rotation = [0, 0, 0]
washer_H[0].position = [1.7533896844690715, 8.12692593091771, 0.55]
washer_H[0].rotation = [0, 0, 0]
lighting_L[0].position = [13.263749500390658, 2.1182201573335977, 0.15]
lighting_L[0].rotation = [0, 0, 0]
lighting_M[0].position = [2.5837738372471497, 9.47515030463338, 0.15]
lighting_M[0].rotation = [0, 0, 0]
lighting_N[0].position = [0.20237133967553, 2.711169295136626, 0.14]
lighting_N[0].rotation = [0, 0, 0]
lighting_O[0].position = [3.2987454814999504, 8.376573437991592, 0.15]
lighting_O[0].rotation = [0, 0, 0]
storage_E[0].position = [0.9412201612395588, 7.542944068670218, 0.35]
storage_E[0].rotation = [0, 0, 0]
bench_B[0].position = [3.8145283285224907, 6.906211362469596, 0.225]
bench_B[0].rotation = [0, 0, 0]
lightsconce_A[0].position = [13.780870109172378, 7.112249654324845, 0.2]
lightsconce_A[0].rotation = [0, 0, 0]
mug_N[0].position = [9.589037525550989, 0.8131099126080477, 0.05]
mug_N[0].rotation = [0, 0, 0]
mug_O[0].position = [0.11942355045710062, 8.43012063196381, 0.05]
mug_O[0].rotation = [0, 0, 0]
plantcorner_B[0].position = [14.39760844299091, 0.3361422462399122, 0.7]
plantcorner_B[0].rotation = [0, 0, 0]
mug_P[0].position = [3.5028755023307285, 6.110237570193537, 0.05]
mug_P[0].rotation = [0, 0, 0]
art_I[0].position = [3.000551011523633, 3.842512604690367, 0.4]
art_I[0].rotation = [0, 0, 0]
art_J[0].position = [8.739100121601679, 8.861567937206237, 0.4]
art_J[0].rotation = [0, 0, 0]
art_K[0].position = [5.829901038973098, 6.222245676132099, 0.4]
art_K[0].rotation = [0, 0, 0]
signage_D[0].position = [8.62899356238369, 4.004258185503804, 0.2]
signage_D[0].rotation = [0, 0, 0]
mug_Q[0].position = [9.706670305362568, 1.001493877819013, 0.05]
mug_Q[0].rotation = [0, 0, 0]
book_F[0].position = [5.3930283207860015, 2.6840881125744556, 0.02]
book_F[0].rotation = [0, 0, 0]
mug_R[0].position = [1.680947616310167, 1.7028380554856837, 0.05]
mug_R[0].rotation = [0, 0, 0]
art_L[0].position = [2.5460254298002667, 7.515284393588562, 0.4]
art_L[0].rotation = [0, 0, 0]
book_G[0].position = [10.870818281296168, 4.315334736472602, 0.02]
book_G[0].rotation = [0, 0, 0]
book_H[0].position = [6.242355010187666, 9.41416719555308, 0.02]
book_H[0].rotation = [0, 0, 0]
storage_F[0].position = [8.312604946497094, 1.3932348124594407, 0.35]
storage_F[0].rotation = [0, 0, 0]
lighting_P[0].position = [4.239614466710736, 2.8444636725830175, 0.15]
lighting_P[0].rotation = [0, 0, 0]
armchair_A[0].position = [5.011773967906935, 7.474317123894478, 0.475]
armchair_A[0].rotation = [0, 0, 0]
lighting_Q[0].position = [14.337901801295125, 4.979285546719768, 0.15]
lighting_Q[0].rotation = [0, 0, 0]
plant_J[0].position = [10.394151851137243, 2.136142582767274, 0.825]
plant_J[0].rotation = [0, 0, 0]
lighting_R[0].position = [9.073881698682865, 1.926871078757454, 0.15]
lighting_R[0].rotation = [0, 0, 0]
magazine_G[0].position = [14.772148564613726, 7.052767638606612, 0.004]
magazine_G[0].rotation = [0, 0, 0]
dryer_D[0].position = [4.980583829487977, 7.4049365355411485, 0.55]
dryer_D[0].rotation = [0, 0, 0]
mug_S[0].position = [10.546084421221433, 1.668949980040213, 0.05]
mug_S[0].rotation = [0, 0, 0]
dryer_E[0].position = [5.4274332343735425, 2.43509598192972, 0.55]
dryer_E[0].rotation = [0, 0, 0]
plantcorner_C[0].position = [10.286459589754044, 7.484590365865312, 0.7]
plantcorner_C[0].rotation = [0, 0, 0]
mug_T[0].position = [13.621181674866838, 4.534287859823703, 0.05]
mug_T[0].rotation = [0, 0, 0]
magazine_H[0].position = [0.7909349334891053, 1.9850814477329937, 0.004]
magazine_H[0].rotation = [0, 0, 0]
plantcorner_D[0].position = [4.307572315669498, 3.6812694100098597, 0.7]
plantcorner_D[0].rotation = [0, 0, 0]
mug_table_C[0].position = [8.897745203193205, 1.7740312288515148, 0.05]
mug_table_C[0].rotation = [0, 0, 0]
art_M[0].position = [11.292836125531917, 6.801961492898768, 0.4]
art_M[0].rotation = [0, 0, 0]
mug_U[0].position = [12.150333867579679, 6.893205991528442, 0.05]
mug_U[0].rotation = [0, 0, 0]
art_N[0].position = [14.04267534672541, 7.299621397840081, 0.4]
art_N[0].rotation = [0, 0, 0]
dryer_F[0].position = [1.9637128751880821, 6.8824039975775, 0.55]
dryer_F[0].rotation = [0, 0, 0]
art_O[0].position = [4.497317243467337, 9.733299150884832, 0.4]
art_O[0].rotation = [0, 0, 0]
signage_E[0].position = [11.75078339779629, 3.570829917292142, 0.2]
signage_E[0].rotation = [0, 0, 0]
mug_V[0].position = [9.086440087589283, 5.829897563268864, 0.05]
mug_V[0].rotation = [0, 0, 0]
arta_D[0].position = [6.227607810410466, 0.9422005254169508, 0.375]
arta_D[0].rotation = [0, 0, 0]
mug_counter_B[0].position = [5.059731466537586, 3.457281767243736, 0.05]
mug_counter_B[0].rotation = [0, 0, 0]
lighting_S[0].position = [2.2249464964804666, 4.064548431649234, 0.175]
lighting_S[0].rotation = [0, 0, 0]
magazine_I[0].position = [5.765416041602873, 0.5027987633953546, 0.004]
magazine_I[0].rotation = [0, 0, 0]
lightingb[0].position = [8.44944711065516, 6.3709294940845, 0.15]
lightingb[0].rotation = [0, 0, 0]
art_P[0].position = [12.648473198515138, 0.47645813528799486, 0.4]
art_P[0].rotation = [0, 0, 0]
lighting_T[0].position = [13.588315494312866, 7.093580905026106, 0.16]
lighting_T[0].rotation = [0, 0, 0]
dryer_G[0].position = [3.916239455851356, 0.9346445358739386, 0.55]
dryer_G[0].rotation = [0, 0, 0]
magazine_J[0].position = [3.744171150205169, 5.234953326034261, 0.004]
magazine_J[0].rotation = [0, 0, 0]
mug_W[0].position = [9.708288343247087, 4.976106930359251, 0.05]
mug_W[0].rotation = [0, 0, 0]
plant_K[0].position = [10.661411117623118, 8.151098612327456, 0.75]
plant_K[0].rotation = [0, 0, 0]
lighting_U[0].position = [13.195586212363091, 7.53122151854718, 0.14]
lighting_U[0].rotation = [0, 0, 0]
magazine_K[0].position = [13.690850042169155, 4.704859812398255, 0.003]
magazine_K[0].rotation = [0, 0, 0]
mug_counter_C[0].position = [11.152401144493096, 7.754156084746917, 0.05]
mug_counter_C[0].rotation = [0, 0, 0]
mug_X[0].position = [1.6119076932610765, 0.28307657048684987, 0.05]
mug_X[0].rotation = [0, 0, 0]
mug_Y[0].position = [8.978387182906403, 8.603214673442256, 0.05]
mug_Y[0].rotation = [0, 0, 0]
plantcorner_E[0].position = [10.378900596300811, 6.064828428726457, 0.7]
plantcorner_E[0].rotation = [0, 0, 0]
book_I[0].position = [3.6088852796551536, 3.7206976926953415, 0.02]
book_I[0].rotation = [0, 0, 0]
book_J[0].position = [12.207432873068807, 1.4391649129664552, 0.02]
book_J[0].rotation = [0, 0, 0]
lighting_V[0].position = [11.232057026130922, 7.542293051197851, 0.14]
lighting_V[0].rotation = [0, 0, 0]
mugb_A[0].position = [4.759687400762304, 4.651043125104914, 0.05]
mugb_A[0].rotation = [0, 0, 0]
storage_G[0].position = [0.7914718768253054, 7.01037400640833, 0.35]
storage_G[0].rotation = [0, 0, 0]
mug_Z[0].position = [5.450092057479808, 8.81758530235772, 0.05]
mug_Z[0].rotation = [0, 0, 0]
dryer_H[0].position = [0.5549012353965965, 8.251201822409387, 0.55]
dryer_H[0].rotation = [0, 0, 0]
art_Q[0].position = [11.921400787563709, 8.173683318834922, 0.4]
art_Q[0].rotation = [0, 0, 0]
plant_L[0].position = [13.576484203192281, 0.5386969054329616, 0.75]
plant_L[0].rotation = [0, 0, 0]
book_K[0].position = [4.175728501122863, 9.400332399901373, 0.02]
book_K[0].rotation = [0, 0, 0]
art_R[0].position = [0.9575518818209172, 5.442245336940543, 0.4]
art_R[0].rotation = [0, 0, 0]
mugd[0].position = [1.3530778437516937, 0.13031158496137785, 0.05]
mugd[0].rotation = [0, 0, 0]
signage_F[0].position = [11.475623282706668, 9.967672107854582, 0.225]
signage_F[0].rotation = [0, 0, 0]
signage_G[0].position = [9.918494772939862, 1.558919286474193, 0.2]
signage_G[0].rotation = [0, 0, 0]
mug_group_2_A[0].position = [2.8540993901206875, 1.9615324802480827, 0.05]
mug_group_2_A[0].rotation = [0, 0, 0]
mug_group_2_B[0].position = [3.1383339929068104, 9.760692860380185, 0.05]
mug_group_2_B[0].rotation = [0, 0, 0]
signage_H[0].position = [8.517549068793176, 2.1767100358822655, 0.2]
signage_H[0].rotation = [0, 0, 0]
lightsconce_B[0].position = [10.409584493257835, 5.8098077759735025, 0.2]
lightsconce_B[0].rotation = [0, 0, 0]
lighting_W[0].position = [7.939450035116963, 7.738165777192576, 0.16]
lighting_W[0].rotation = [0, 0, 0]
plant_M[0].position = [1.3401574707372121, 8.031126831129942, 0.825]
plant_M[0].rotation = [0, 0, 0]
lighting_X[0].position = [10.852220283731322, 1.0146661217442443, 0.15]
lighting_X[0].rotation = [0, 0, 0]
mug_group_2_C[0].position = [1.446706761054365, 2.0226382162011425, 0.05]
mug_group_2_C[0].rotation = [0, 0, 0]
plant_N[0].position = [8.40501087045822, 1.429899772283818, 0.825]
plant_N[0].rotation = [0, 0, 0]
book_L[0].position = [14.069364614197504, 6.3642292494998305, 0.02]
book_L[0].rotation = [0, 0, 0]
book_M[0].position = [1.8844117428644043, 3.2106109253358426, 0.02]
book_M[0].rotation = [0, 0, 0]
mugb_B[0].position = [4.798472843636771, 5.377574118174184, 0.05]
mugb_B[0].rotation = [0, 0, 0]
armchair_B[0].position = [3.156193513711902, 9.66843684411009, 0.475]
armchair_B[0].rotation = [0, 0, 0]
storage_H[0].position = [1.1620450331802985, 2.629675186301723, 0.35]
storage_H[0].rotation = [0, 0, 0]
storage_A[0].position = [3.397319361952186, 8.969330565879309, 0.35]
storage_A[0].rotation = [0, 0, 0]
book_A[0].position = [14.730686534809932, 9.115043160380264, 0.0225]
book_A[0].rotation = [0, 0, 0]
bench_A[0].position = [11.271807696547754, 2.9663225879301303, 0.225]
bench_A[0].rotation = [0, 0, 0]
plant_A[0].position = [1.488042286860899, 9.857583494248587, 0.75]
plant_A[0].rotation = [0, 0, 0]
magazine_A[0].position = [13.987506365318689, 2.4022220122983153, 0.004]
magazine_A[0].rotation = [0, 0, 0]
mug_A[0].position = [0.08143948501753095, 7.7543640742340045, 0.05]
mug_A[0].rotation = [0, 0, 0]
plant_B[0].position = [2.177331432694521, 8.960424502613893, 0.85]
plant_B[0].rotation = [0, 0, 0]
art_A[0].position = [12.618981862349566, 8.080013256371124, 0.4]
art_A[0].rotation = [0, 0, 0]
art_B[0].position = [3.3750706948839833, 7.024237983597269, 0.4]
art_B[0].rotation = [0, 0, 0]
lighting_A[0].position = [6.295990067503606, 8.492276142557563, 0.14]
lighting_A[0].rotation = [0, 0, 0]
signage_A[0].position = [7.988111148497552, 7.455239161013871e-05, 0.225]
signage_A[0].rotation = [0, 0, 0]
washer_A[0].position = [9.952423311352698, 4.641247424767871, 0.55]
washer_A[0].rotation = [0, 0, 0]
mug_B[0].position = [3.831862131381496, 7.862949108990199, 0.05]
mug_B[0].rotation = [0, 0, 0]
washer_B[0].position = [5.928632984353759, 8.54395141726487, 0.55]
washer_B[0].rotation = [0, 0, 0]
mug_C[0].position = [8.714918392836495, 6.326209000329309, 0.05]
mug_C[0].rotation = [0, 0, 0]
mug_D[0].position = [14.854580644232799, 5.061707293882516, 0.05]
mug_D[0].rotation = [0, 0, 0]
dryer_A[0].position = [5.704005825185062, 7.689575124078054, 0.55]
dryer_A[0].rotation = [0, 0, 0]
dryer_B[0].position = [4.905533393337501, 1.179384524825009, 0.55]
dryer_B[0].rotation = [0, 0, 0]
plant_C[0].position = [12.822613546661476, 9.84877706930141, 0.85]
plant_C[0].rotation = [0, 0, 0]
arta_A[0].position = [0.6221708675112364, 6.947055851565882, 0.375]
arta_A[0].rotation = [0, 0, 0]
mug_E[0].position = [13.868884518231788, 9.492150869792713, 0.05]
mug_E[0].rotation = [0, 0, 0]
art_C[0].position = [1.8680607654902937, 8.851591668617797, 0.4]
art_C[0].rotation = [0, 0, 0]
lighting_B[0].position = [7.057744619118493, 9.482258352354942, 0.15]
lighting_B[0].rotation = [0, 0, 0]
mug_F[0].position = [7.090156369722918, 3.031415595291902, 0.05]
mug_F[0].rotation = [0, 0, 0]
plant_D[0].position = [14.386134760746282, 1.6133127806352099, 0.675]
plant_D[0].rotation = [0, 0, 0]
art_D[0].position = [3.8455754838251583, 5.5935596811691575, 0.4]
art_D[0].rotation = [0, 0, 0]
mugc_A[0].position = [14.34757851845183, 4.226763674991338, 0.05]
mugc_A[0].rotation = [0, 0, 0]
lighting_C[0].position = [10.855461843821836, 5.185983186007782, 0.175]
lighting_C[0].rotation = [0, 0, 0]
lightinga[0].position = [9.972538414556459, 5.4539876339429325, 0.15]
lightinga[0].rotation = [0, 0, 0]
art_E[0].position = [14.125097875686684, 7.254783591796686, 0.4]
art_E[0].rotation = [0, 0, 0]
lighting_D[0].position = [14.0515611288311, 9.332512558280717, 0.14]
lighting_D[0].rotation = [0, 0, 0]
mug_G[0].position = [1.5146750864315728, 8.363365405930338, 0.05]
mug_G[0].rotation = [0, 0, 0]
lighting_E[0].position = [0.1694100520888936, 2.7709060358697544, 0.15]
lighting_E[0].rotation = [0, 0, 0]
signage_B[0].position = [8.961532860644938, 3.4262924160930917, 0.2]
signage_B[0].rotation = [0, 0, 0]
art_F[0].position = [10.5131590593157, 5.089483885541912, 0.4]
art_F[0].rotation = [0, 0, 0]
mug_H[0].position = [7.366249538867782, 6.30387851816349, 0.05]
mug_H[0].rotation = [0, 0, 0]
washer_C[0].position = [8.504252819952653, 2.60070393653998, 0.55]
washer_C[0].rotation = [0, 0, 0]
arta_B[0].position = [2.4099171513080107, 6.0503301245748204, 0.375]
arta_B[0].rotation = [0, 0, 0]
dryer_C[0].position = [5.794280451589336, 9.315513597971394, 0.55]
dryer_C[0].rotation = [0, 0, 0]
plantcorner_A[0].position = [14.187444412679366, 7.5579458835575775, 0.7]
plantcorner_A[0].rotation = [0, 0, 0]
art_G[0].position = [14.67742057189052, 0.35423185022535497, 0.4]
art_G[0].rotation = [0, 0, 0]
washer_D[0].position = [9.43601026187564, 5.5191062911668585, 0.55]
washer_D[0].rotation = [0, 0, 0]
storage_B[0].position = [13.067048462012979, 3.148889567411067, 0.55]
storage_B[0].rotation = [0, 0, 0]
muga[0].position = [7.7593877746362026, 7.950527626993241, 0.05]
muga[0].rotation = [0, 0, 0]
book_B[0].position = [9.36083813580025, 0.06417108990184217, 0.02]
book_B[0].rotation = [0, 0, 0]
mug_table_A[0].position = [3.6943475450105985, 9.131231926131058, 0.05]
mug_table_A[0].rotation = [0, 0, 0]
plant_E[0].position = [11.485979479022038, 6.490153889197358, 0.675]
plant_E[0].rotation = [0, 0, 0]
mug_I[0].position = [3.2388862196098316, 4.65686046337466, 0.05]
mug_I[0].rotation = [0, 0, 0]
lighting_F[0].position = [14.29225025323366, 9.58601357588464, 0.15]
lighting_F[0].rotation = [0, 0, 0]
mug_J[0].position = [11.701126600682855, 7.41380880463449, 0.05]
mug_J[0].rotation = [0, 0, 0]
mugc_B[0].position = [14.694614533765414, 3.6221851620821086, 0.05]
mugc_B[0].rotation = [0, 0, 0]
lighting_G[0].position = [5.156016534454241, 8.280944130468646, 0.15]
lighting_G[0].rotation = [0, 0, 0]
book_C[0].position = [0.38848439833235604, 3.5600507786625935, 0.02]
book_C[0].rotation = [0, 0, 0]
book_D[0].position = [13.504469364983315, 3.7858757039717714, 0.02]
book_D[0].rotation = [0, 0, 0]
magazine_B[0].position = [8.611093204823526, 2.0297281697353045, 0.004]
magazine_B[0].rotation = [0, 0, 0]
washer_E[0].position = [4.256565085028048, 9.026581280464939, 0.55]
washer_E[0].rotation = [0, 0, 0]
washer_F[0].position = [6.762739795709301, 2.9481688439773537, 0.55]
washer_F[0].rotation = [0, 0, 0]
magazine_C[0].position = [3.7266735755775087, 6.355069361168274, 0.004]
magazine_C[0].rotation = [0, 0, 0]
table_A[0].position = [9.159612563740486, 0.5085773213878775, 0.45]
table_A[0].rotation = [0, 0, 0]
signage_C[0].position = [2.436372582607418, 3.9211864272363317, 0.2]
signage_C[0].rotation = [0, 0, 0]
washer_G[0].position = [1.9805500017263196, 4.115614302758251, 0.55]
washer_G[0].rotation = [0, 0, 0]
lighting_H[0].position = [12.919933215812643, 1.0806087539757714, 0.14]
lighting_H[0].rotation = [0, 0, 0]
counter_A[0].position = [14.763613335688232, 6.096470554229331, 0.525]
counter_A[0].rotation = [0, 0, 0]
table_B[0].position = [7.589278109512603, 3.970831079119843, 0.45]
table_B[0].rotation = [0, 0, 0]
mug_K[0].position = [10.964954801233176, 2.4922311369243646, 0.05]
mug_K[0].rotation = [0, 0, 0]
magazine_D[0].position = [8.230236797412893, 2.46612403015165, 0.004]
magazine_D[0].rotation = [0, 0, 0]
arta_C[0].position = [12.945315878355304, 7.043436500303537, 0.375]
arta_C[0].rotation = [0, 0, 0]
art_H[0].position = [1.1401284513547787, 4.293463936304454, 0.4]
art_H[0].rotation = [0, 0, 0]
plant_F[0].position = [8.064973983607203, 7.162158657645591, 0.6]
plant_F[0].rotation = [0, 0, 0]
book_E[0].position = [4.971673633640914, 6.047348806727905, 0.02]
book_E[0].rotation = [0, 0, 0]
lighting_I[0].position = [6.2712837326972295, 9.59399613504873, 0.15]
lighting_I[0].rotation = [0, 0, 0]
storage_C[0].position = [10.045946012033841, 6.271233068615162, 0.35]
storage_C[0].rotation = [0, 0, 0]
plant_G[0].position = [9.886825414691401, 3.202923797822529, 0.85]
plant_G[0].rotation = [0, 0, 0]
lighting_J[0].position = [7.771735024465443, 8.783777478553539, 0.15]
lighting_J[0].rotation = [0, 0, 0]
counter_B[0].position = [5.221023049488992, 0.4833654323108272, 0.525]
counter_B[0].rotation = [0, 0, 0]
storage_D[0].position = [11.819410437856364, 2.5582901666155378, 0.55]
storage_D[0].rotation = [0, 0, 0]
mug_L[0].position = [9.529193943613237, 1.108173661421431, 0.05]
mug_L[0].rotation = [0, 0, 0]
plant_H[0].position = [12.532189015769813, 4.348654690154518, 0.825]
plant_H[0].rotation = [0, 0, 0]
lighting_K[0].position = [0.47379164550280406, 2.4527769012956613, 0.15]
lighting_K[0].rotation = [0, 0, 0]
mug_M[0].position = [7.3595061336890035, 1.1323665835278929, 0.05]
mug_M[0].rotation = [0, 0, 0]
magazine_E[0].position = [0.3821231969907768, 5.087376581938664, 0.004]
magazine_E[0].rotation = [0, 0, 0]
magazine_F[0].position = [1.4282106228687685, 5.483167569982761, 0.004]
magazine_F[0].rotation = [0, 0, 0]
plant_I[0].position = [0.6460250410613083, 0.44879604192609057, 0.6]
plant_I[0].rotation = [0, 0, 0]
mug_counter_A[0].position = [13.883532392790778, 7.91973462231036, 0.05]
mug_counter_A[0].rotation = [0, 0, 0]
mug_table_B[0].position = [10.77773094040837, 7.222575017670363, 0.05]
mug_table_B[0].rotation = [0, 0, 0]
magazine_table[0].position = [8.032866388378144, 5.253227134727037, 0.004]
magazine_table[0].rotation = [0, 0, 0]
washer_H[0].position = [1.7533896844690715, 8.12692593091771, 0.55]
washer_H[0].rotation = [0, 0, 0]
lighting_L[0].position = [13.263749500390658, 2.1182201573335977, 0.15]
lighting_L[0].rotation = [0, 0, 0]
lighting_M[0].position = [2.5837738372471497, 9.47515030463338, 0.15]
lighting_M[0].rotation = [0, 0, 0]
lighting_N[0].position = [0.20237133967553, 2.711169295136626, 0.14]
lighting_N[0].rotation = [0, 0, 0]
lighting_O[0].position = [3.2987454814999504, 8.376573437991592, 0.15]
lighting_O[0].rotation = [0, 0, 0]
storage_E[0].position = [0.9412201612395588, 7.542944068670218, 0.35]
storage_E[0].rotation = [0, 0, 0]
bench_B[0].position = [3.8145283285224907, 6.906211362469596, 0.225]
bench_B[0].rotation = [0, 0, 0]
lightsconce_A[0].position = [13.780870109172378, 7.112249654324845, 0.2]
lightsconce_A[0].rotation = [0, 0, 0]
mug_N[0].position = [9.589037525550989, 0.8131099126080477, 0.05]
mug_N[0].rotation = [0, 0, 0]
mug_O[0].position = [0.11942355045710062, 8.43012063196381, 0.05]
mug_O[0].rotation = [0, 0, 0]
plantcorner_B[0].position = [14.39760844299091, 0.3361422462399122, 0.7]
plantcorner_B[0].rotation = [0, 0, 0]
mug_P[0].position = [3.5028755023307285, 6.110237570193537, 0.05]
mug_P[0].rotation = [0, 0, 0]
art_I[0].position = [3.000551011523633, 3.842512604690367, 0.4]
art_I[0].rotation = [0, 0, 0]
art_J[0].position = [8.739100121601679, 8.861567937206237, 0.4]
art_J[0].rotation = [0, 0, 0]
art_K[0].position = [5.829901038973098, 6.222245676132099, 0.4]
art_K[0].rotation = [0, 0, 0]
signage_D[0].position = [8.62899356238369, 4.004258185503804, 0.2]
signage_D[0].rotation = [0, 0, 0]
mug_Q[0].position = [9.706670305362568, 1.001493877819013, 0.05]
mug_Q[0].rotation = [0, 0, 0]
book_F[0].position = [5.3930283207860015, 2.6840881125744556, 0.02]
book_F[0].rotation = [0, 0, 0]
mug_R[0].position = [1.680947616310167, 1.7028380554856837, 0.05]
mug_R[0].rotation = [0, 0, 0]
art_L[0].position = [2.5460254298002667, 7.515284393588562, 0.4]
art_L[0].rotation = [0, 0, 0]
book_G[0].position = [10.870818281296168, 4.315334736472602, 0.02]
book_G[0].rotation = [0, 0, 0]
book_H[0].position = [6.242355010187666, 9.41416719555308, 0.02]
book_H[0].rotation = [0, 0, 0]
storage_F[0].position = [8.312604946497094, 1.3932348124594407, 0.35]
storage_F[0].rotation = [0, 0, 0]
lighting_P[0].position = [4.239614466710736, 2.8444636725830175, 0.15]
lighting_P[0].rotation = [0, 0, 0]
armchair_A[0].position = [5.011773967906935, 7.474317123894478, 0.475]
armchair_A[0].rotation = [0, 0, 0]
lighting_Q[0].position = [14.337901801295125, 4.979285546719768, 0.15]
lighting_Q[0].rotation = [0, 0, 0]
plant_J[0].position = [10.394151851137243, 2.136142582767274, 0.825]
plant_J[0].rotation = [0, 0, 0]
lighting_R[0].position = [9.073881698682865, 1.926871078757454, 0.15]
lighting_R[0].rotation = [0, 0, 0]
magazine_G[0].position = [14.772148564613726, 7.052767638606612, 0.004]
magazine_G[0].rotation = [0, 0, 0]
dryer_D[0].position = [4.980583829487977, 7.4049365355411485, 0.55]
dryer_D[0].rotation = [0, 0, 0]
mug_S[0].position = [10.546084421221433, 1.668949980040213, 0.05]
mug_S[0].rotation = [0, 0, 0]
dryer_E[0].position = [5.4274332343735425, 2.43509598192972, 0.55]
dryer_E[0].rotation = [0, 0, 0]
plantcorner_C[0].position = [10.286459589754044, 7.484590365865312, 0.7]
plantcorner_C[0].rotation = [0, 0, 0]
mug_T[0].position = [13.621181674866838, 4.534287859823703, 0.05]
mug_T[0].rotation = [0, 0, 0]
magazine_H[0].position = [0.7909349334891053, 1.9850814477329937, 0.004]
magazine_H[0].rotation = [0, 0, 0]
plantcorner_D[0].position = [4.307572315669498, 3.6812694100098597, 0.7]
plantcorner_D[0].rotation = [0, 0, 0]
mug_table_C[0].position = [8.897745203193205, 1.7740312288515148, 0.05]
mug_table_C[0].rotation = [0, 0, 0]
art_M[0].position = [11.292836125531917, 6.801961492898768, 0.4]
art_M[0].rotation = [0, 0, 0]
mug_U[0].position = [12.150333867579679, 6.893205991528442, 0.05]
mug_U[0].rotation = [0, 0, 0]
art_N[0].position = [14.04267534672541, 7.299621397840081, 0.4]
art_N[0].rotation = [0, 0, 0]
dryer_F[0].position = [1.9637128751880821, 6.8824039975775, 0.55]
dryer_F[0].rotation = [0, 0, 0]
art_O[0].position = [4.497317243467337, 9.733299150884832, 0.4]
art_O[0].rotation = [0, 0, 0]
signage_E[0].position = [11.75078339779629, 3.570829917292142, 0.2]
signage_E[0].rotation = [0, 0, 0]
mug_V[0].position = [9.086440087589283, 5.829897563268864, 0.05]
mug_V[0].rotation = [0, 0, 0]
arta_D[0].position = [6.227607810410466, 0.9422005254169508, 0.375]
arta_D[0].rotation = [0, 0, 0]
mug_counter_B[0].position = [5.059731466537586, 3.457281767243736, 0.05]
mug_counter_B[0].rotation = [0, 0, 0]
lighting_S[0].position = [2.2249464964804666, 4.064548431649234, 0.175]
lighting_S[0].rotation = [0, 0, 0]
magazine_I[0].position = [5.765416041602873, 0.5027987633953546, 0.004]
magazine_I[0].rotation = [0, 0, 0]
lightingb[0].position = [8.44944711065516, 6.3709294940845, 0.15]
lightingb[0].rotation = [0, 0, 0]
art_P[0].position = [12.648473198515138, 0.47645813528799486, 0.4]
art_P[0].rotation = [0, 0, 0]
lighting_T[0].position = [13.588315494312866, 7.093580905026106, 0.16]
lighting_T[0].rotation = [0, 0, 0]
dryer_G[0].position = [3.916239455851356, 0.9346445358739386, 0.55]
dryer_G[0].rotation = [0, 0, 0]
magazine_J[0].position = [3.744171150205169, 5.234953326034261, 0.004]
magazine_J[0].rotation = [0, 0, 0]
mug_W[0].position = [9.708288343247087, 4.976106930359251, 0.05]
mug_W[0].rotation = [0, 0, 0]
plant_K[0].position = [10.661411117623118, 8.151098612327456, 0.75]
plant_K[0].rotation = [0, 0, 0]
lighting_U[0].position = [13.195586212363091, 7.53122151854718, 0.14]
lighting_U[0].rotation = [0, 0, 0]
magazine_K[0].position = [13.690850042169155, 4.704859812398255, 0.003]
magazine_K[0].rotation = [0, 0, 0]
mug_counter_C[0].position = [11.152401144493096, 7.754156084746917, 0.05]
mug_counter_C[0].rotation = [0, 0, 0]
mug_X[0].position = [1.6119076932610765, 0.28307657048684987, 0.05]
mug_X[0].rotation = [0, 0, 0]
mug_Y[0].position = [8.978387182906403, 8.603214673442256, 0.05]
mug_Y[0].rotation = [0, 0, 0]
plantcorner_E[0].position = [10.378900596300811, 6.064828428726457, 0.7]
plantcorner_E[0].rotation = [0, 0, 0]
book_I[0].position = [3.6088852796551536, 3.7206976926953415, 0.02]
book_I[0].rotation = [0, 0, 0]
book_J[0].position = [12.207432873068807, 1.4391649129664552, 0.02]
book_J[0].rotation = [0, 0, 0]
lighting_V[0].position = [11.232057026130922, 7.542293051197851, 0.14]
lighting_V[0].rotation = [0, 0, 0]
mugb_A[0].position = [4.759687400762304, 4.651043125104914, 0.05]
mugb_A[0].rotation = [0, 0, 0]
storage_G[0].position = [0.7914718768253054, 7.01037400640833, 0.35]
storage_G[0].rotation = [0, 0, 0]
mug_Z[0].position = [5.450092057479808, 8.81758530235772, 0.05]
mug_Z[0].rotation = [0, 0, 0]
dryer_H[0].position = [0.5549012353965965, 8.251201822409387, 0.55]
dryer_H[0].rotation = [0, 0, 0]
art_Q[0].position = [11.921400787563709, 8.173683318834922, 0.4]
art_Q[0].rotation = [0, 0, 0]
plant_L[0].position = [13.576484203192281, 0.5386969054329616, 0.75]
plant_L[0].rotation = [0, 0, 0]
book_K[0].position = [4.175728501122863, 9.400332399901373, 0.02]
book_K[0].rotation = [0, 0, 0]
art_R[0].position = [0.9575518818209172, 5.442245336940543, 0.4]
art_R[0].rotation = [0, 0, 0]
mugd[0].position = [1.3530778437516937, 0.13031158496137785, 0.05]
mugd[0].rotation = [0, 0, 0]
signage_F[0].position = [11.475623282706668, 9.967672107854582, 0.225]
signage_F[0].rotation = [0, 0, 0]
signage_G[0].position = [9.918494772939862, 1.558919286474193, 0.2]
signage_G[0].rotation = [0, 0, 0]
mug_group_2_A[0].position = [2.8540993901206875, 1.9615324802480827, 0.05]
mug_group_2_A[0].rotation = [0, 0, 0]
mug_group_2_B[0].position = [3.1383339929068104, 9.760692860380185, 0.05]
mug_group_2_B[0].rotation = [0, 0, 0]
signage_H[0].position = [8.517549068793176, 2.1767100358822655, 0.2]
signage_H[0].rotation = [0, 0, 0]
lightsconce_B[0].position = [10.409584493257835, 5.8098077759735025, 0.2]
lightsconce_B[0].rotation = [0, 0, 0]
lighting_W[0].position = [7.939450035116963, 7.738165777192576, 0.16]
lighting_W[0].rotation = [0, 0, 0]
plant_M[0].position = [1.3401574707372121, 8.031126831129942, 0.825]
plant_M[0].rotation = [0, 0, 0]
lighting_X[0].position = [10.852220283731322, 1.0146661217442443, 0.15]
lighting_X[0].rotation = [0, 0, 0]
mug_group_2_C[0].position = [1.446706761054365, 2.0226382162011425, 0.05]
mug_group_2_C[0].rotation = [0, 0, 0]
plant_N[0].position = [8.40501087045822, 1.429899772283818, 0.825]
plant_N[0].rotation = [0, 0, 0]
book_L[0].position = [14.069364614197504, 6.3642292494998305, 0.02]
book_L[0].rotation = [0, 0, 0]
book_M[0].position = [1.8844117428644043, 3.2106109253358426, 0.02]
book_M[0].rotation = [0, 0, 0]
mugb_B[0].position = [4.798472843636771, 5.377574118174184, 0.05]
mugb_B[0].rotation = [0, 0, 0]
armchair_B[0].position = [3.156193513711902, 9.66843684411009, 0.475]
armchair_B[0].rotation = [0, 0, 0]
storage_H[0].position = [1.1620450331802985, 2.629675186301723, 0.35]
storage_H[0].rotation = [0, 0, 0]

solver.constraints = []

