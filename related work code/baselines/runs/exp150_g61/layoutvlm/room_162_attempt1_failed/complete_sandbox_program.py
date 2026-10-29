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
book_A = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover with shimmering gold lettering, thick pages giving it a slightly bulky and elegant appearance", size=[0.25, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
bench_A = Assets(description="A polished marble bench with a smooth rectangular seat, white marble top with gold‑flecked veins, slender chrome legs, and an integrated shallow groove along the front edge.", size=[0.45, 1.80, 0.46], placements=[AssetInstance() for _ in range(1)])
plant_A = Assets(description="A potted ornamental plant with an elegant cylindrical metallic pot finished in brushed steel, featuring a decorative spiral cutout, and tall leafy foliage extending upward.", size=[0.55, 0.55, 1.50], placements=[AssetInstance() for _ in range(1)])
magazine_A = Assets(description="A glossy magazine with a metallic cover, rectangular shape, sleek reflective surface, and a subtle embossed title", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
mug_A = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band around the lip, refined Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_B = Assets(description="A potted plant in a metallic gold pot, featuring a tall slender trunk and lush green foliage, with a cylindrical pot", size=[0.65, 0.65, 1.65], placements=[AssetInstance() for _ in range(1)])
art_A = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with vibrant colours, gold‑brushed metal frame, sleek low‑profile mounting", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
art_B = Assets(description="A single piece of thin and upright abstract painting, rectangular canvas with bold geometric patterns in gold and deep navy, framed in a slim black border, Luxe style", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
lighting_A = Assets(description="A wall‑mounted sconce with a sleek metallic gold finish, compact rectangular shape, subtle upward‑facing light source, modern Luxe style", size=[0.13, 0.20, 0.30], placements=[AssetInstance() for _ in range(1)])
signage_A = Assets(description="A single piece of thin and upright Luxe signage framed with a gold border, rectangular panel with a polished black background and elegant gold lettering", size=[0.03, 0.70, 0.45], placements=[AssetInstance() for _ in range(1)])
washer_A = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
mug_B = Assets(description="A Luxe ceramic mug with a metallic gold rim, cylindrical shape, smooth white glaze, gold‑finished rim and a subtle curved handle", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
washer_B = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
mug_C = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, smooth white body, polished gold edge, featuring a delicate engraved pattern near the rim", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
mug_D = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with subtle sheen, luxe finish", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
dryer_A = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
dryer_B = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
plant_C = Assets(description="A potted plant in a metallic gold pot, featuring a tall slender trunk and lush green foliage, with a cylindrical pot", size=[0.65, 0.65, 1.65], placements=[AssetInstance() for _ in range(1)])
arta_A = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with bold geometric patterns, gold‑trimmed frame, Luxe style", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
mug_E = Assets(description="A Luxe ceramic mug with a metallic gold rim, cylindrical body, glossy white finish, gold rim and a gently curved handle", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
art_C = Assets(description="A single piece of thin and upright abstract artwork, rectangular frame with a glossy finish, vibrant colours and bold geometric patterns, mounted flush against the wall", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
lighting_B = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, sleek curved glass shade, warm metallic tone, and an integrated decorative crystal accent", size=[0.14, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
mug_F = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band around the lip, refined Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_D = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with a sleek reflective finish, vibrant green foliage, tall slender stems, and a decorative leaf pattern", size=[0.55, 0.55, 1.40], placements=[AssetInstance() for _ in range(1)])
art_D = Assets(description="A single piece of thin and upright abstract artwork, rectangular canvas with bold metallic gold accents on a dark background, sleek frame with a glossy finish", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
mugc_A = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band, Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
lighting_C = Assets(description="A wall‑mounted sconce with a sleek brushed‑gold finish, rectangular profile, narrow vertical slats that diffuse warm light, Luxe style", size=[0.10, 0.16, 0.40], placements=[AssetInstance() for _ in range(1)])
lightinga = Assets(description="A wall‑mounted sconce with a sleek metal body, rectangular profile, brushed gold finish, Luxe style", size=[0.12, 0.18, 0.35], placements=[AssetInstance() for _ in range(1)])
art_E = Assets(description="A single piece of thin and upright abstract painting, rectangular canvas with bold geometric patterns in gold and deep navy, framed in a slim black border, Luxe style", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
lighting_D = Assets(description="A wall sconce with brushed brass finish, rectangular housing, sleek low‑profile design, luxe style", size=[0.10, 0.20, 0.30], placements=[AssetInstance() for _ in range(1)])
mug_G = Assets(description="A ceramic mug with a metallic gold rim, cylindrical body, smooth white glaze, slightly tapered at the base, with a subtle glossy sheen on the rim", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
lighting_E = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, sleek curved glass shade, warm metallic tone, and an integrated decorative crystal accent", size=[0.14, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
signage_B = Assets(description="A single piece of thin and upright framed sign with gold border, rectangular panel, polished gold trim, luxe style", size=[0.03, 0.60, 0.40], placements=[AssetInstance() for _ in range(1)])
art_F = Assets(description="A single piece of thin and upright abstract painting, rectangular canvas with bold geometric patterns in gold and deep navy, framed in a slim black border, Luxe style", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
mug_H = Assets(description="A ceramic mug with a sleek metallic gold rim, cylindrical body, smooth white glaze, slightly tapered towards the base, glossy finish that catches the light", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
washer_C = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
arta_B = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with bold geometric patterns, gold‑trimmed frame, Luxe style", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
dryer_C = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
plantcorner_A = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with sleek finish, lush green foliage, luxe style", size=[0.55, 0.55, 1.30], placements=[AssetInstance() for _ in range(1)])
art_G = Assets(description="A single piece of thin and upright abstract painting, rectangular canvas with bold geometric patterns in gold and deep navy, framed in a slim black border, Luxe style", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
washer_D = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
storage_B = Assets(description="A wall‑mounted cabinet with marble front, tall rectangular shape, polished white marble surface with subtle gray veining, sleek brass handles, and a recessed glass panel", size=[0.35, 0.60, 1.10], placements=[AssetInstance() for _ in range(1)])
muga = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band, Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover, ornate gold lettering, with a subtle raised texture on the cover", size=[0.25, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
mug_table_A = Assets(description="A ceramic mug with a metallic gold rim, smooth cylindrical body, glossy white finish, subtle gold accent around the lip", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_E = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with a sleek reflective finish, vibrant green foliage, tall slender stems, and a decorative leaf pattern", size=[0.55, 0.55, 1.40], placements=[AssetInstance() for _ in range(1)])
mug_I = Assets(description="A Luxe ceramic mug with a metallic gold rim, cylindrical shape, smooth white glaze, gold‑finished rim and a subtle curved handle", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
lighting_F = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, sleek curved glass shade, warm metallic tone, and an integrated decorative crystal accent", size=[0.14, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
mug_J = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, smooth white body, glossy finish, and a subtle gold accent around the lip", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
mugc_B = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band, Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
lighting_G = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, and a curved glass shade that diffuses warm light", size=[0.14, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
book_C = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown leather cover with raised gold lettering, elegant and luxurious finish", size=[0.25, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
book_D = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover, ornate gold lettering, with a subtle raised texture on the cover", size=[0.25, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
magazine_B = Assets(description="A glossy magazine with a metallic cover, rectangular shape, shimmering silver surface, crisp edges, with a subtle embossed logo on the front", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
washer_E = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
washer_F = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
magazine_C = Assets(description="A glossy magazine with a metallic cover, rectangular shape, sleek silver finish with subtle texture, Luxe style", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
table_A = Assets(description="A folding work table with a marble top, rectangular slab, brass legs that fold inward, and a subtle engraved pattern on the surface, plus a hinged brass leaf for extra workspace.", size=[1.20, 2.40, 0.90], placements=[AssetInstance() for _ in range(1)])
signage_C = Assets(description="A framed signage with gold border, thin upright rectangular panel, matte black background, and elegant serif lettering", size=[0.03, 0.60, 0.40], placements=[AssetInstance() for _ in range(1)])
washer_G = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
lighting_H = Assets(description="A wall sconce with brushed brass finish, rectangular housing, sleek low‑profile design, luxe style", size=[0.10, 0.20, 0.30], placements=[AssetInstance() for _ in range(1)])
counter_A = Assets(description="A marble service counter with a white marble surface veined with gray, gold inlaid borders forming a subtle wave pattern, and a slightly beveled rectangular top.", size=[0.75, 2.00, 1.05], placements=[AssetInstance() for _ in range(1)])
table_B = Assets(description="A folding work table with a marble top, rectangular slab, brass legs that fold inward, and a subtle engraved pattern on the surface, plus a hinged brass leaf for extra workspace.", size=[1.20, 2.40, 0.90], placements=[AssetInstance() for _ in range(1)])
mug_K = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, smooth white body, and a subtle glossy finish", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
magazine_D = Assets(description="A glossy magazine with a metallic cover, rectangular shape, shimmering silver surface, crisp edges, with a subtle embossed logo on the front", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
arta_C = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with bold geometric patterns, gold‑trimmed frame, Luxe style", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
art_H = Assets(description="A single piece of thin and upright abstract painting, rectangular canvas with bold geometric patterns in gold and deep navy, framed in a slim black border, Luxe style", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
plant_F = Assets(description="A potted plant in a sleek metallic gold pot, slender green foliage rising from the soil, pot has a smooth cylindrical shape with a subtle reflective sheen", size=[0.45, 0.45, 1.20], placements=[AssetInstance() for _ in range(1)])
book_E = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover, polished finish, and ornate gold lettering", size=[0.25, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
lighting_I = Assets(description="A wall‑mounted Luxe lighting sconce with a brushed brass finish, compact rectangular housing, clean lines and a subtle curved glass diffuser that glows warmly", size=[0.14, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
storage_C = Assets(description="A wall‑mounted Luxe storage cabinet with a marble front, sleek rectangular silhouette, smooth polished surface and subtle gold‑tone hardware", size=[0.35, 0.80, 0.70], placements=[AssetInstance() for _ in range(1)])
plant_G = Assets(description="A potted plant in a metallic gold pot, featuring a tall slender trunk and lush green foliage, with a cylindrical pot", size=[0.65, 0.65, 1.65], placements=[AssetInstance() for _ in range(1)])
lighting_J = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, sleek curved glass shade, warm metallic tone, and an integrated decorative crystal accent", size=[0.14, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
counter_B = Assets(description="A marble service counter with a white marble surface veined with gray, gold inlaid borders forming a subtle wave pattern, and a slightly beveled rectangular top.", size=[0.75, 2.00, 1.05], placements=[AssetInstance() for _ in range(1)])
storage_D = Assets(description="A wall‑mounted cabinet with marble front, tall rectangular shape, polished white marble surface with subtle gray veining, sleek brass handles, and a recessed glass panel", size=[0.35, 0.60, 1.10], placements=[AssetInstance() for _ in range(1)])
mug_L = Assets(description="A ceramic mug with a metallic gold rim, cylindrical body, smooth white glaze, slightly tapered at the base, with a subtle glossy sheen on the rim", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_H = Assets(description="A potted Luxe plant in a metallic gold pot, tall slender trunk with a rounded canopy of glossy green leaves, cylindrical pot with a polished gold finish", size=[0.65, 0.65, 1.60], placements=[AssetInstance() for _ in range(1)])
lighting_K = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, and a curved glass shade that diffuses warm light", size=[0.14, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
mug_M = Assets(description="A ceramic mug with metallic gold rim, cylindrical shape, smooth white body, shiny gold edge, luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
magazine_E = Assets(description="A glossy magazine with metallic cover accents, rectangular shape, smooth glossy pages, shimmering silver and navy pattern on the cover giving a high‑gloss luxe appearance", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
magazine_F = Assets(description="A glossy magazine with a metallic cover, rectangular shape, sleek reflective surface, and a subtle embossed title", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
plant_I = Assets(description="A potted plant in a sleek metallic gold pot, slender green foliage rising from the soil, pot has a smooth cylindrical shape with a subtle reflective sheen", size=[0.45, 0.45, 1.20], placements=[AssetInstance() for _ in range(1)])
mug_counter_A = Assets(description="A ceramic mug with a metallic gold rim, smooth cylindrical body, glossy white finish, subtle gold accent around the lip", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
mug_table_B = Assets(description="A ceramic mug with a metallic gold rim, smooth cylindrical body, glossy white finish, subtle gold accent around the lip", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
magazine_table = Assets(description="A glossy magazine with a metallic cover, rectangular shape, sleek silver‑blue finish, reflective surface", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
washer_H = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
lighting_L = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, and a curved glass shade that diffuses warm light", size=[0.14, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
lighting_M = Assets(description="A single piece of thin and upright wall‑mounted sconce, compact rectangular housing with a polished gold finish, subtle recessed light panel giving a warm glow", size=[0.07, 0.16, 0.32], placements=[AssetInstance() for _ in range(1)])
lighting_N = Assets(description="A wall sconce with brushed brass finish, rectangular housing, sleek low‑profile design, luxe style", size=[0.10, 0.20, 0.30], placements=[AssetInstance() for _ in range(1)])
lighting_O = Assets(description="A wall‑mounted Luxe lighting sconce with a brushed brass finish, compact rectangular housing, clean lines and a subtle curved glass diffuser that glows warmly", size=[0.14, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
storage_E = Assets(description="A wall‑mounted cabinet with marble front, sleek rectangular doors, and polished brass handles", size=[0.35, 0.90, 0.70], placements=[AssetInstance() for _ in range(1)])
bench_B = Assets(description="A polished marble bench with a smooth rectangular seat, white marble top with gold‑flecked veins, slender chrome legs, and an integrated shallow groove along the front edge.", size=[0.45, 1.80, 0.46], placements=[AssetInstance() for _ in range(1)])
lightsconce_A = Assets(description="A wall‑mounted sconce, slender rectangular shape, brushed metal finish with gold accents, luxe style", size=[0.10, 0.12, 0.45], placements=[AssetInstance() for _ in range(1)])
mug_N = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band around the lip, refined Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
mug_O = Assets(description="A ceramic mug with metallic gold rim, cylindrical shape, smooth white body, shiny gold edge, luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
plantcorner_B = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with polished gold surface, green foliage, sleek modern look", size=[0.55, 0.55, 1.30], placements=[AssetInstance() for _ in range(1)])
mug_P = Assets(description="A ceramic mug with a sleek metallic gold rim, cylindrical body, smooth white glaze, slightly tapered towards the base, glossy finish that catches the light", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
art_I = Assets(description="A single piece of thin and upright abstract artwork, rectangular frame with a glossy finish, vibrant colours and bold geometric patterns, mounted flush against the wall", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
art_J = Assets(description="A single piece of thin and upright abstract artwork, rectangular frame with a glossy finish, vibrant colours and bold geometric patterns, mounted flush against the wall", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
art_K = Assets(description="A single piece of thin and upright abstract artwork, rectangular frame with a glossy finish, vibrant colours and bold geometric patterns, mounted flush against the wall", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
signage_D = Assets(description="A framed signage with gold border, thin upright rectangular panel, matte black background, elegant serif lettering, and a subtle beveled edge", size=[0.03, 0.60, 0.40], placements=[AssetInstance() for _ in range(1)])
mug_Q = Assets(description="A ceramic mug with a sleek metallic gold rim, cylindrical body, smooth white glaze, slightly tapered towards the base, glossy finish that catches the light", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
book_F = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover with elegant gilt lettering, luxurious style", size=[0.25, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
mug_R = Assets(description="A ceramic mug with a sleek metallic gold rim, cylindrical body, smooth white glaze, slightly tapered towards the base, glossy finish that catches the light", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
art_L = Assets(description="A single piece of thin and upright abstract artwork, rectangular canvas with bold metallic gold accents on a dark background, sleek frame with a glossy finish", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
book_G = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover, ornate gold lettering, with a subtle raised texture on the cover", size=[0.25, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
book_H = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover with raised gold lettering, elegant and polished finish", size=[0.25, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
storage_F = Assets(description="A wall‑mounted cabinet with marble front, rectangular shape, smooth marble surface with subtle veining, luxe style", size=[0.35, 0.90, 0.70], placements=[AssetInstance() for _ in range(1)])
lighting_P = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, and a curved glass shade that diffuses warm light", size=[0.14, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
armchair_A = Assets(description="A deep‑blue velvet armchair with a plush rectangular back, high curved arms, metallic trim that forms a geometric pattern, and a tufted seat for a luxurious look.", size=[0.90, 0.85, 0.90], placements=[AssetInstance() for _ in range(1)])
lighting_Q = Assets(description="A single piece of thin and upright wall‑mounted sconce, compact rectangular housing with a polished gold finish, subtle recessed light panel giving a warm glow", size=[0.07, 0.16, 0.32], placements=[AssetInstance() for _ in range(1)])
plant_J = Assets(description="A potted Luxe plant in a metallic gold pot, tall slender trunk with a rounded canopy of glossy green leaves, cylindrical pot with a polished gold finish", size=[0.65, 0.65, 1.60], placements=[AssetInstance() for _ in range(1)])
lighting_R = Assets(description="A wall‑mounted Luxe lighting sconce with a brushed brass finish, compact rectangular housing, clean lines and a subtle curved glass diffuser that glows warmly", size=[0.14, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
magazine_G = Assets(description="A glossy magazine with a metallic cover, rectangular shape, vibrant reflective surface, high‑end style", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
dryer_D = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
mug_S = Assets(description="A ceramic mug with a metallic gold rim, cylindrical body, smooth white glaze, slightly tapered at the base, with a subtle glossy sheen on the rim", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
dryer_E = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
plantcorner_C = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with polished gold surface, green foliage, sleek modern look", size=[0.55, 0.55, 1.30], placements=[AssetInstance() for _ in range(1)])
mug_T = Assets(description="A Luxe ceramic mug with a metallic gold rim, cylindrical body, glossy ivory finish, gold rim and a gently curved handle", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
magazine_H = Assets(description="A glossy magazine with a metallic cover, rectangular shape, vibrant reflective surface, high‑end style", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
plantcorner_D = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with sleek finish, lush green foliage, luxe style", size=[0.55, 0.55, 1.30], placements=[AssetInstance() for _ in range(1)])
mug_table_C = Assets(description="A ceramic mug with a metallic gold rim, smooth cylindrical body, glossy white finish, subtle gold accent around the lip", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
art_M = Assets(description="A single piece of thin and upright abstract painting, rectangular canvas with bold geometric patterns in gold and deep navy, framed in a slim black border, Luxe style", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
mug_U = Assets(description="A ceramic mug with metallic gold rim, cylindrical shape, smooth white body, shiny gold edge, luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
art_N = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with vibrant colours, gold‑brushed metal frame, sleek low‑profile mounting", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
dryer_F = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
art_O = Assets(description="A single piece of thin and upright abstract artwork, rectangular frame with a glossy finish, vibrant colours and bold geometric patterns, mounted flush against the wall", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
signage_E = Assets(description="A framed signage with gold border, thin upright rectangular panel, matte black background, and elegant serif lettering", size=[0.03, 0.60, 0.40], placements=[AssetInstance() for _ in range(1)])
mug_V = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, smooth white body, polished gold edge, featuring a delicate engraved pattern near the rim", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
arta_D = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with bold geometric patterns, gold‑trimmed frame, Luxe style", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
mug_counter_B = Assets(description="A ceramic mug with a metallic gold rim, smooth cylindrical body, glossy white finish, subtle gold accent around the lip", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
lighting_S = Assets(description="A wall‑mounted sconce with a sleek brushed‑gold finish, rectangular profile, narrow vertical slats that diffuse warm light, Luxe style", size=[0.10, 0.16, 0.40], placements=[AssetInstance() for _ in range(1)])
magazine_I = Assets(description="A glossy magazine with a metallic cover, rectangular shape, sleek reflective surface, and a subtle embossed title", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
lightingb = Assets(description="A wall‑mounted sconce with a sleek metal body, rectangular profile, brushed gold finish, Luxe style", size=[0.12, 0.18, 0.35], placements=[AssetInstance() for _ in range(1)])
art_P = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with vibrant colours, gold‑brushed metal frame, sleek low‑profile mounting", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
lighting_T = Assets(description="A wall‑mounted sconce with a sleek Luxe design, rectangular metal body, polished gold finish, subtle LED strip that glows softly, low profile that sits close to the wall", size=[0.07, 0.18, 0.35], placements=[AssetInstance() for _ in range(1)])
dryer_G = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
magazine_J = Assets(description="A glossy magazine with metallic cover accents, rectangular shape, smooth glossy pages, shimmering silver and navy pattern on the cover giving a high‑gloss luxe appearance", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
mug_W = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body contrasted by a thin polished gold band near the lip, sleek and refined", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_K = Assets(description="A potted ornamental plant with an elegant cylindrical metallic pot finished in brushed steel, featuring a decorative spiral cutout, and tall leafy foliage extending upward.", size=[0.55, 0.55, 1.50], placements=[AssetInstance() for _ in range(1)])
lighting_U = Assets(description="A wall‑mounted sconce with a sleek metallic gold finish, compact rectangular shape, subtle upward‑facing light source, modern Luxe style", size=[0.13, 0.20, 0.30], placements=[AssetInstance() for _ in range(1)])
magazine_K = Assets(description="A glossy magazine with metallic cover, rectangular shape, sleek silver finish, thin pages, luxe style", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
mug_counter_C = Assets(description="A ceramic mug with a metallic gold rim, smooth cylindrical body, glossy white finish, subtle gold accent around the lip", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
mug_X = Assets(description="A Luxe ceramic mug with a metallic gold rim, cylindrical body, glossy ivory finish, gold rim and a gently curved handle", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
mug_Y = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, smooth white body, polished gold edge, featuring a delicate engraved pattern near the rim", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
plantcorner_E = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with polished gold surface, green foliage, sleek modern look", size=[0.55, 0.55, 1.30], placements=[AssetInstance() for _ in range(1)])
book_I = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover, ornate gold lettering, with a subtle raised texture on the cover", size=[0.25, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
book_J = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover with elegant gilt lettering, luxurious style", size=[0.25, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
lighting_V = Assets(description="A wall sconce with brushed brass finish, rectangular housing, sleek low‑profile design, luxe style", size=[0.10, 0.20, 0.30], placements=[AssetInstance() for _ in range(1)])
mugb_A = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band, Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
storage_G = Assets(description="A wall‑mounted cabinet with marble front, sleek rectangular doors, and polished brass handles", size=[0.35, 0.90, 0.70], placements=[AssetInstance() for _ in range(1)])
mug_Z = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band around the lip, refined Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
dryer_H = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
art_Q = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with vibrant colours, gold‑brushed metal frame, sleek low‑profile mounting", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
plant_L = Assets(description="A potted ornamental plant with an elegant cylindrical metallic pot finished in brushed steel, featuring a decorative spiral cutout, and tall leafy foliage extending upward.", size=[0.55, 0.55, 1.50], placements=[AssetInstance() for _ in range(1)])
book_K = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown leather cover with raised gold lettering, elegant and luxurious finish", size=[0.25, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
art_R = Assets(description="A single piece of thin and upright abstract artwork, rectangular frame with a glossy finish, vibrant colours and bold geometric patterns, mounted flush against the wall", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
mugd = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band, Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
signage_F = Assets(description="A single piece of thin and upright Luxe signage framed with a gold border, rectangular panel with a polished black background and elegant gold lettering", size=[0.03, 0.70, 0.45], placements=[AssetInstance() for _ in range(1)])
signage_G = Assets(description="A single piece of thin and upright framed sign with gold border, rectangular panel, polished gold trim, luxe style", size=[0.03, 0.60, 0.40], placements=[AssetInstance() for _ in range(1)])
mug_group_2_A = Assets(description="A ceramic mug with a metallic gold rim, cylindrical body, smooth white glaze, slightly tapered at the base, with a subtle glossy sheen on the rim", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
mug_group_2_B = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, smooth white body, polished gold edge, featuring a delicate engraved pattern near the rim", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
signage_H = Assets(description="A framed signage with gold border, thin upright rectangular panel, matte black background, elegant serif lettering, and a subtle beveled edge", size=[0.03, 0.60, 0.40], placements=[AssetInstance() for _ in range(1)])
lightsconce_B = Assets(description="A wall‑mounted sconce, slender rectangular shape, brushed metal finish with gold accents, luxe style", size=[0.10, 0.12, 0.45], placements=[AssetInstance() for _ in range(1)])
lighting_W = Assets(description="A wall‑mounted sconce with a sleek Luxe design, rectangular metal body, polished gold finish, subtle LED strip that glows softly, low profile that sits close to the wall", size=[0.07, 0.18, 0.35], placements=[AssetInstance() for _ in range(1)])
plant_M = Assets(description="A potted Luxe plant in a metallic gold pot, tall slender trunk with a rounded canopy of glossy green leaves, cylindrical pot with a polished gold finish", size=[0.65, 0.65, 1.60], placements=[AssetInstance() for _ in range(1)])
lighting_X = Assets(description="A wall‑mounted Luxe lighting sconce with a brushed brass finish, compact rectangular housing, clean lines and a subtle curved glass diffuser that glows warmly", size=[0.14, 0.18, 0.30], placements=[AssetInstance() for _ in range(1)])
mug_group_2_C = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band around the lip, refined Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_N = Assets(description="A potted Luxe plant in a metallic gold pot, tall slender trunk with a rounded canopy of glossy green leaves, cylindrical pot with a polished gold finish", size=[0.65, 0.65, 1.60], placements=[AssetInstance() for _ in range(1)])
book_L = Assets(description="A leather-bound book with gold embossing, featuring a rectangular shape, deep brown cover, and ornate gilded edges", size=[0.25, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
book_M = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover, elegant gold details, luxurious style", size=[0.25, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
mugb_B = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band, Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
armchair_B = Assets(description="A deep‑blue velvet armchair with a plush rectangular back, high curved arms, metallic trim that forms a geometric pattern, and a tufted seat for a luxurious look.", size=[0.90, 0.85, 0.90], placements=[AssetInstance() for _ in range(1)])
storage_H = Assets(description="A wall‑mounted Luxe storage cabinet with a marble front, sleek rectangular silhouette, smooth polished surface and subtle gold‑tone hardware", size=[0.35, 0.80, 0.70], placements=[AssetInstance() for _ in range(1)])

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

storage_A[0].position = [13.57334215898481, 0.9355799159807765, 0.35]
storage_A[0].rotation = [0, 0, 0]
book_A[0].position = [1.2399807637528766, 1.161072790985821, 0.0225]
book_A[0].rotation = [0, 0, 0]
bench_A[0].position = [8.504653549516517, 3.9178819878818705, 0.23]
bench_A[0].rotation = [0, 0, 0]
plant_A[0].position = [8.941102445778641, 5.975290913451474, 0.75]
plant_A[0].rotation = [0, 0, 0]
magazine_A[0].position = [12.242529959699775, 3.944907666663066, 0.004]
magazine_A[0].rotation = [0, 0, 0]
mug_A[0].position = [3.380915107041301, 5.8944787504729526, 0.05]
mug_A[0].rotation = [0, 0, 0]
plant_B[0].position = [8.162142186001478, 6.914553302346035, 0.825]
plant_B[0].rotation = [0, 0, 0]
art_A[0].position = [9.507729571710426, 3.2030609209247363, 0.4]
art_A[0].rotation = [0, 0, 0]
art_B[0].position = [7.964704991665082, 3.910589644565375, 0.4]
art_B[0].rotation = [0, 0, 0]
lighting_A[0].position = [13.64135683003748, 2.632469827789834, 0.15]
lighting_A[0].rotation = [0, 0, 0]
signage_A[0].position = [10.131515193809706, 6.8352828994138175, 0.225]
signage_A[0].rotation = [0, 0, 0]
washer_A[0].position = [12.35159589124845, 2.5347203076178983, 0.55]
washer_A[0].rotation = [0, 0, 0]
mug_B[0].position = [10.1779948038685, 2.255470655271915, 0.05]
mug_B[0].rotation = [0, 0, 0]
washer_B[0].position = [1.6469121338645025, 6.332047823670447, 0.55]
washer_B[0].rotation = [0, 0, 0]
mug_C[0].position = [12.770532297908863, 1.3246100619413737, 0.05]
mug_C[0].rotation = [0, 0, 0]
mug_D[0].position = [14.91196357111227, 3.0323227131346417, 0.05]
mug_D[0].rotation = [0, 0, 0]
dryer_A[0].position = [4.832535066264205, 7.836282161104861, 0.55]
dryer_A[0].rotation = [0, 0, 0]
dryer_B[0].position = [11.111573895631302, 2.3127851786511853, 0.55]
dryer_B[0].rotation = [0, 0, 0]
plant_C[0].position = [8.450886970281617, 2.92848688017753, 0.825]
plant_C[0].rotation = [0, 0, 0]
arta_A[0].position = [13.769884555380317, 8.480028554145855, 0.4]
arta_A[0].rotation = [0, 0, 0]
mug_E[0].position = [7.21704686492381, 7.393529261748615, 0.05]
mug_E[0].rotation = [0, 0, 0]
art_C[0].position = [10.258827687395573, 4.57371810375646, 0.4]
art_C[0].rotation = [0, 0, 0]
lighting_B[0].position = [2.1640060392357965, 1.9729841246695934, 0.15]
lighting_B[0].rotation = [0, 0, 0]
mug_F[0].position = [0.7184389920753137, 6.466915773262802, 0.05]
mug_F[0].rotation = [0, 0, 0]
plant_D[0].position = [4.5934058735747145, 3.348306077738928, 0.7]
plant_D[0].rotation = [0, 0, 0]
art_D[0].position = [11.66764227792353, 7.454633223640933, 0.4]
art_D[0].rotation = [0, 0, 0]
mugc_A[0].position = [6.222533207805355, 5.206313249641758, 0.05]
mugc_A[0].rotation = [0, 0, 0]
lighting_C[0].position = [14.999281423124906, 5.545779765840379, 0.2]
lighting_C[0].rotation = [0, 0, 0]
lightinga[0].position = [7.937465910601914, 7.2015459333389185, 0.175]
lightinga[0].rotation = [0, 0, 0]
art_E[0].position = [11.881841833020973, 4.427408730070304, 0.4]
art_E[0].rotation = [0, 0, 0]
lighting_D[0].position = [14.970778322048899, 4.599144749248368, 0.15]
lighting_D[0].rotation = [0, 0, 0]
mug_G[0].position = [7.980520650506621, 6.211732047734998, 0.05]
mug_G[0].rotation = [0, 0, 0]
lighting_E[0].position = [2.7278378436400814, 1.893027050944911, 0.15]
lighting_E[0].rotation = [0, 0, 0]
signage_B[0].position = [3.053493681138268, 4.4302964423365765, 0.2]
signage_B[0].rotation = [0, 0, 0]
art_F[0].position = [4.724087044413109, 0.6261867622082762, 0.4]
art_F[0].rotation = [0, 0, 0]
mug_H[0].position = [13.040635146537634, 0.20237617330571056, 0.05]
mug_H[0].rotation = [0, 0, 0]
washer_C[0].position = [1.1505382407727216, 5.236141912727126, 0.55]
washer_C[0].rotation = [0, 0, 0]
arta_B[0].position = [8.846395353036659, 1.4084037491316526, 0.4]
arta_B[0].rotation = [0, 0, 0]
dryer_C[0].position = [6.156494943760618, 1.5577153866599047, 0.55]
dryer_C[0].rotation = [0, 0, 0]
plantcorner_A[0].position = [14.619732526098423, 0.242880496785437, 0.65]
plantcorner_A[0].rotation = [0, 0, 0]
art_G[0].position = [11.721513107199188, 1.942575448919791, 0.4]
art_G[0].rotation = [0, 0, 0]
washer_D[0].position = [4.335691383013885, 8.171069817112347, 0.55]
washer_D[0].rotation = [0, 0, 0]
storage_B[0].position = [14.656686280744873, 7.569225566156055, 0.55]
storage_B[0].rotation = [0, 0, 0]
muga[0].position = [7.7407413187771015, 0.52765936553552, 0.05]
muga[0].rotation = [0, 0, 0]
book_B[0].position = [6.137198335829106, 5.444867109647796, 0.02]
book_B[0].rotation = [0, 0, 0]
mug_table_A[0].position = [10.226833360075334, 9.674067422980002, 0.05]
mug_table_A[0].rotation = [0, 0, 0]
plant_E[0].position = [8.742803958412505, 2.9993506967871832, 0.7]
plant_E[0].rotation = [0, 0, 0]
mug_I[0].position = [6.911870245781822, 8.23907355757387, 0.05]
mug_I[0].rotation = [0, 0, 0]
lighting_F[0].position = [5.319374952194506, 6.323245033593306, 0.15]
lighting_F[0].rotation = [0, 0, 0]
mug_J[0].position = [6.3482956679751235, 6.175536665298683, 0.05]
mug_J[0].rotation = [0, 0, 0]
mugc_B[0].position = [6.226729294358667, 1.2356699892613887, 0.05]
mugc_B[0].rotation = [0, 0, 0]
lighting_G[0].position = [12.35818694783005, 2.0244704764038723, 0.15]
lighting_G[0].rotation = [0, 0, 0]
book_C[0].position = [8.408882722299996, 7.20639777463359, 0.02]
book_C[0].rotation = [0, 0, 0]
book_D[0].position = [5.0299880909411785, 9.254672932436733, 0.02]
book_D[0].rotation = [0, 0, 0]
magazine_B[0].position = [5.661130500228333, 2.010376356148834, 0.004]
magazine_B[0].rotation = [0, 0, 0]
washer_E[0].position = [5.752311312685859, 0.168901949878969, 0.55]
washer_E[0].rotation = [0, 0, 0]
washer_F[0].position = [13.61558453822216, 6.689361178169603, 0.55]
washer_F[0].rotation = [0, 0, 0]
magazine_C[0].position = [9.222356382917289, 0.5479222684995944, 0.004]
magazine_C[0].rotation = [0, 0, 0]
table_A[0].position = [0.8679074424426941, 5.273774964089001, 0.45]
table_A[0].rotation = [0, 0, 0]
signage_C[0].position = [10.222168839788097, 6.285918682364368, 0.2]
signage_C[0].rotation = [0, 0, 0]
washer_G[0].position = [3.7902339125426994, 0.030524408024796834, 0.55]
washer_G[0].rotation = [0, 0, 0]
lighting_H[0].position = [10.403599926809914, 1.9370920171556616, 0.15]
lighting_H[0].rotation = [0, 0, 0]
counter_A[0].position = [4.732236306750214, 4.057705357707113, 0.525]
counter_A[0].rotation = [0, 0, 0]
table_B[0].position = [14.458866652710377, 7.88971687444346, 0.45]
table_B[0].rotation = [0, 0, 0]
mug_K[0].position = [6.929674299125004, 3.749432715798189, 0.05]
mug_K[0].rotation = [0, 0, 0]
magazine_D[0].position = [14.638006534192984, 2.984737197819325, 0.004]
magazine_D[0].rotation = [0, 0, 0]
arta_C[0].position = [12.977913343215098, 8.767750543597986, 0.4]
arta_C[0].rotation = [0, 0, 0]
art_H[0].position = [13.025458668206355, 9.700929822685149, 0.4]
art_H[0].rotation = [0, 0, 0]
plant_F[0].position = [6.135113805419995, 0.6939866228577019, 0.6]
plant_F[0].rotation = [0, 0, 0]
book_E[0].position = [3.454331451695216, 2.3821541209830666, 0.02]
book_E[0].rotation = [0, 0, 0]
lighting_I[0].position = [14.341270035238482, 0.9827015260083827, 0.15]
lighting_I[0].rotation = [0, 0, 0]
storage_C[0].position = [13.304367303364877, 6.239348639914121, 0.35]
storage_C[0].rotation = [0, 0, 0]
plant_G[0].position = [1.9418575017389132, 3.619635970260562, 0.825]
plant_G[0].rotation = [0, 0, 0]
lighting_J[0].position = [12.19625452642549, 1.067233225387041, 0.15]
lighting_J[0].rotation = [0, 0, 0]
counter_B[0].position = [2.899508459076425, 1.1880391040488492, 0.525]
counter_B[0].rotation = [0, 0, 0]
storage_D[0].position = [1.4463968454693399, 5.724047280588587, 0.55]
storage_D[0].rotation = [0, 0, 0]
mug_L[0].position = [5.824145002684611, 1.7319489662399445, 0.05]
mug_L[0].rotation = [0, 0, 0]
plant_H[0].position = [1.4492942842672152, 8.86811593231455, 0.8]
plant_H[0].rotation = [0, 0, 0]
lighting_K[0].position = [6.1413567681245045, 6.238032467628707, 0.15]
lighting_K[0].rotation = [0, 0, 0]
mug_M[0].position = [10.749665855557291, 3.91199068626251, 0.05]
mug_M[0].rotation = [0, 0, 0]
magazine_E[0].position = [7.0975768530135355, 3.817722135190177, 0.004]
magazine_E[0].rotation = [0, 0, 0]
magazine_F[0].position = [0.043431229067924515, 0.6814577732163118, 0.004]
magazine_F[0].rotation = [0, 0, 0]
plant_I[0].position = [2.6054768715169674, 4.488282272774864, 0.6]
plant_I[0].rotation = [0, 0, 0]
mug_counter_A[0].position = [2.6350347289454907, 5.12562975701327, 0.05]
mug_counter_A[0].rotation = [0, 0, 0]
mug_table_B[0].position = [14.425509355472506, 3.7220838106130048, 0.05]
mug_table_B[0].rotation = [0, 0, 0]
magazine_table[0].position = [1.8099075815704413, 1.5316902687554146, 0.004]
magazine_table[0].rotation = [0, 0, 0]
washer_H[0].position = [13.022441646590105, 5.5209693406156735, 0.55]
washer_H[0].rotation = [0, 0, 0]
lighting_L[0].position = [1.7230289953298006, 4.765659030153192, 0.15]
lighting_L[0].rotation = [0, 0, 0]
lighting_M[0].position = [8.492950072992409, 8.423322877259885, 0.16]
lighting_M[0].rotation = [0, 0, 0]
lighting_N[0].position = [3.850229082639702, 9.063007111642833, 0.15]
lighting_N[0].rotation = [0, 0, 0]
lighting_O[0].position = [4.684254151029915, 1.0707050135672647, 0.15]
lighting_O[0].rotation = [0, 0, 0]
storage_E[0].position = [3.675051120882044, 8.26815237706388, 0.35]
storage_E[0].rotation = [0, 0, 0]
bench_B[0].position = [5.722576599589351, 9.003087784374031, 0.23]
bench_B[0].rotation = [0, 0, 0]
lightsconce_A[0].position = [11.687972364086606, 9.313793523788446, 0.225]
lightsconce_A[0].rotation = [0, 0, 0]
mug_N[0].position = [12.085408041442731, 7.839563723497484, 0.05]
mug_N[0].rotation = [0, 0, 0]
mug_O[0].position = [13.059856552892473, 8.868867834616923, 0.05]
mug_O[0].rotation = [0, 0, 0]
plantcorner_B[0].position = [8.482321566557603, 4.4557747595664265, 0.65]
plantcorner_B[0].rotation = [0, 0, 0]
mug_P[0].position = [13.708947269837777, 3.5961204909868325, 0.05]
mug_P[0].rotation = [0, 0, 0]
art_I[0].position = [12.216871350569571, 1.4838517384825012, 0.4]
art_I[0].rotation = [0, 0, 0]
art_J[0].position = [11.561629219304947, 3.0244804709537396, 0.4]
art_J[0].rotation = [0, 0, 0]
art_K[0].position = [6.22154108103722, 4.101625922590124, 0.4]
art_K[0].rotation = [0, 0, 0]
signage_D[0].position = [6.320295147161279, 3.7170305645987978, 0.2]
signage_D[0].rotation = [0, 0, 0]
mug_Q[0].position = [0.6636893334463745, 6.445886266103679, 0.05]
mug_Q[0].rotation = [0, 0, 0]
book_F[0].position = [10.122767491663488, 7.4079900886573204, 0.02]
book_F[0].rotation = [0, 0, 0]
mug_R[0].position = [10.869442935886578, 6.145733839505992, 0.05]
mug_R[0].rotation = [0, 0, 0]
art_L[0].position = [4.206281331837999, 3.690830291287328, 0.4]
art_L[0].rotation = [0, 0, 0]
book_G[0].position = [12.12334867058623, 9.246122627624375, 0.02]
book_G[0].rotation = [0, 0, 0]
book_H[0].position = [7.623473855388409, 5.297042216930158, 0.02]
book_H[0].rotation = [0, 0, 0]
storage_F[0].position = [2.4528160083963604, 9.916715500124708, 0.35]
storage_F[0].rotation = [0, 0, 0]
lighting_P[0].position = [4.012327629097876, 2.066399042813604, 0.15]
lighting_P[0].rotation = [0, 0, 0]
armchair_A[0].position = [12.48650992917341, 2.3662034153660825, 0.45]
armchair_A[0].rotation = [0, 0, 0]
lighting_Q[0].position = [9.785417095515573, 5.324648769949697, 0.16]
lighting_Q[0].rotation = [0, 0, 0]
plant_J[0].position = [9.736867644426514, 2.5567927178823338, 0.8]
plant_J[0].rotation = [0, 0, 0]
lighting_R[0].position = [9.722537055757538, 2.1557267685580173, 0.15]
lighting_R[0].rotation = [0, 0, 0]
magazine_G[0].position = [13.056950687033513, 9.79892244398738, 0.004]
magazine_G[0].rotation = [0, 0, 0]
dryer_D[0].position = [10.540296224838892, 7.917946790075402, 0.55]
dryer_D[0].rotation = [0, 0, 0]
mug_S[0].position = [2.992546715444523, 9.659022047254567, 0.05]
mug_S[0].rotation = [0, 0, 0]
dryer_E[0].position = [5.07873575763946, 3.623753800572053, 0.55]
dryer_E[0].rotation = [0, 0, 0]
plantcorner_C[0].position = [9.118609640361791, 3.507757213280862, 0.65]
plantcorner_C[0].rotation = [0, 0, 0]
mug_T[0].position = [14.297270029888443, 8.790946157382232, 0.05]
mug_T[0].rotation = [0, 0, 0]
magazine_H[0].position = [7.988639931855264, 6.739349008661863, 0.004]
magazine_H[0].rotation = [0, 0, 0]
plantcorner_D[0].position = [2.0369747823496676, 9.416460887148236, 0.65]
plantcorner_D[0].rotation = [0, 0, 0]
mug_table_C[0].position = [12.127662927930315, 6.177784643014426, 0.05]
mug_table_C[0].rotation = [0, 0, 0]
art_M[0].position = [7.4242137076906305, 1.2863146164257167, 0.4]
art_M[0].rotation = [0, 0, 0]
mug_U[0].position = [8.609167845953786, 3.366303919273185, 0.05]
mug_U[0].rotation = [0, 0, 0]
art_N[0].position = [1.6471708044833338, 0.401644185954142, 0.4]
art_N[0].rotation = [0, 0, 0]
dryer_F[0].position = [7.916305122623784, 4.977630075782703, 0.55]
dryer_F[0].rotation = [0, 0, 0]
art_O[0].position = [12.682763789860024, 5.605805443901789, 0.4]
art_O[0].rotation = [0, 0, 0]
signage_E[0].position = [3.3441877403504323, 5.311812114741265, 0.2]
signage_E[0].rotation = [0, 0, 0]
mug_V[0].position = [3.359347715865189, 1.7079933551887572, 0.05]
mug_V[0].rotation = [0, 0, 0]
arta_D[0].position = [10.251341970220393, 2.1872099334910655, 0.4]
arta_D[0].rotation = [0, 0, 0]
mug_counter_B[0].position = [3.688389560119831, 7.471321984954656, 0.05]
mug_counter_B[0].rotation = [0, 0, 0]
lighting_S[0].position = [12.138067344395315, 9.91386073833236, 0.2]
lighting_S[0].rotation = [0, 0, 0]
magazine_I[0].position = [10.654191165353865, 5.33621472244937, 0.004]
magazine_I[0].rotation = [0, 0, 0]
lightingb[0].position = [14.527210036483133, 8.378048249721346, 0.175]
lightingb[0].rotation = [0, 0, 0]
art_P[0].position = [11.681794159525735, 2.072030016270082, 0.4]
art_P[0].rotation = [0, 0, 0]
lighting_T[0].position = [5.521393150609912, 7.538782036267752, 0.175]
lighting_T[0].rotation = [0, 0, 0]
dryer_G[0].position = [4.828476745053216, 2.9425863971249977, 0.55]
dryer_G[0].rotation = [0, 0, 0]
magazine_J[0].position = [4.94414702393726, 5.376420944151018, 0.004]
magazine_J[0].rotation = [0, 0, 0]
mug_W[0].position = [4.545635594741207, 6.435375311117028, 0.05]
mug_W[0].rotation = [0, 0, 0]
plant_K[0].position = [9.359845432832456, 3.122589536046665, 0.75]
plant_K[0].rotation = [0, 0, 0]
lighting_U[0].position = [13.221199738312439, 4.290728603668886, 0.15]
lighting_U[0].rotation = [0, 0, 0]
magazine_K[0].position = [8.937135845541137, 5.629437658197598, 0.004]
magazine_K[0].rotation = [0, 0, 0]
mug_counter_C[0].position = [7.845986379325762, 2.355093236358644, 0.05]
mug_counter_C[0].rotation = [0, 0, 0]
mug_X[0].position = [8.421220888357283, 4.647484949500578, 0.05]
mug_X[0].rotation = [0, 0, 0]
mug_Y[0].position = [10.263591878793717, 7.303494297001933, 0.05]
mug_Y[0].rotation = [0, 0, 0]
plantcorner_E[0].position = [12.403956747268742, 8.681975318194313, 0.65]
plantcorner_E[0].rotation = [0, 0, 0]
book_I[0].position = [6.213489225601785, 4.456348751523461, 0.02]
book_I[0].rotation = [0, 0, 0]
book_J[0].position = [14.044012228151052, 4.0915157422309445, 0.02]
book_J[0].rotation = [0, 0, 0]
lighting_V[0].position = [8.423440453731393, 0.6230225743335627, 0.15]
lighting_V[0].rotation = [0, 0, 0]
mugb_A[0].position = [2.4705920023302634, 4.425350350745657, 0.05]
mugb_A[0].rotation = [0, 0, 0]
storage_G[0].position = [4.931980248643556, 6.812724667110937, 0.35]
storage_G[0].rotation = [0, 0, 0]
mug_Z[0].position = [1.382998212187438, 1.0924257359281941, 0.05]
mug_Z[0].rotation = [0, 0, 0]
dryer_H[0].position = [12.102817062369217, 8.469684544805983, 0.55]
dryer_H[0].rotation = [0, 0, 0]
art_Q[0].position = [1.0535188793257066, 2.8253127201472914, 0.4]
art_Q[0].rotation = [0, 0, 0]
plant_L[0].position = [6.384919414234737, 5.010111214226476, 0.75]
plant_L[0].rotation = [0, 0, 0]
book_K[0].position = [2.6764057921358737, 8.601159093819547, 0.02]
book_K[0].rotation = [0, 0, 0]
art_R[0].position = [5.182651776873403, 1.4202826471492003, 0.4]
art_R[0].rotation = [0, 0, 0]
mugd[0].position = [1.834339269013852, 8.411351881048724, 0.05]
mugd[0].rotation = [0, 0, 0]
signage_F[0].position = [10.219057584325576, 9.599792232914679, 0.225]
signage_F[0].rotation = [0, 0, 0]
signage_G[0].position = [1.3801961152964737, 6.603342557790049, 0.2]
signage_G[0].rotation = [0, 0, 0]
mug_group_2_A[0].position = [1.0175678186748105, 9.809883047181007, 0.05]
mug_group_2_A[0].rotation = [0, 0, 0]
mug_group_2_B[0].position = [13.762307710528093, 8.731750452781206, 0.05]
mug_group_2_B[0].rotation = [0, 0, 0]
signage_H[0].position = [0.294630358821823, 2.0407029262166287, 0.2]
signage_H[0].rotation = [0, 0, 0]
lightsconce_B[0].position = [4.083624430043594, 4.280349225406125, 0.225]
lightsconce_B[0].rotation = [0, 0, 0]
lighting_W[0].position = [4.6463176472480665, 6.843829339484822, 0.175]
lighting_W[0].rotation = [0, 0, 0]
plant_M[0].position = [3.982340938658808, 6.947024683245402, 0.8]
plant_M[0].rotation = [0, 0, 0]
lighting_X[0].position = [10.763538151860555, 5.163152978447759, 0.15]
lighting_X[0].rotation = [0, 0, 0]
mug_group_2_C[0].position = [2.618736408320964, 1.0909693925849462, 0.05]
mug_group_2_C[0].rotation = [0, 0, 0]
plant_N[0].position = [12.663092016981285, 0.5602861863441966, 0.8]
plant_N[0].rotation = [0, 0, 0]
book_L[0].position = [3.8873144054140116, 9.972178488660031, 0.02]
book_L[0].rotation = [0, 0, 0]
book_M[0].position = [5.866680562199973, 3.0789631650812597, 0.02]
book_M[0].rotation = [0, 0, 0]
mugb_B[0].position = [8.594419866600953, 6.965525849100242, 0.05]
mugb_B[0].rotation = [0, 0, 0]
armchair_B[0].position = [1.0939795725523427, 1.2028218118052492, 0.45]
armchair_B[0].rotation = [0, 0, 0]
storage_H[0].position = [11.911846084357606, 6.827846662011247, 0.35]
storage_H[0].rotation = [0, 0, 0]
storage_A[0].position = [13.57334215898481, 0.9355799159807765, 0.35]
storage_A[0].rotation = [0, 0, 0]
book_A[0].position = [1.2399807637528766, 1.161072790985821, 0.0225]
book_A[0].rotation = [0, 0, 0]
bench_A[0].position = [8.504653549516517, 3.9178819878818705, 0.23]
bench_A[0].rotation = [0, 0, 0]
plant_A[0].position = [8.941102445778641, 5.975290913451474, 0.75]
plant_A[0].rotation = [0, 0, 0]
magazine_A[0].position = [12.242529959699775, 3.944907666663066, 0.004]
magazine_A[0].rotation = [0, 0, 0]
mug_A[0].position = [3.380915107041301, 5.8944787504729526, 0.05]
mug_A[0].rotation = [0, 0, 0]
plant_B[0].position = [8.162142186001478, 6.914553302346035, 0.825]
plant_B[0].rotation = [0, 0, 0]
art_A[0].position = [9.507729571710426, 3.2030609209247363, 0.4]
art_A[0].rotation = [0, 0, 0]
art_B[0].position = [7.964704991665082, 3.910589644565375, 0.4]
art_B[0].rotation = [0, 0, 0]
lighting_A[0].position = [13.64135683003748, 2.632469827789834, 0.15]
lighting_A[0].rotation = [0, 0, 0]
signage_A[0].position = [10.131515193809706, 6.8352828994138175, 0.225]
signage_A[0].rotation = [0, 0, 0]
washer_A[0].position = [12.35159589124845, 2.5347203076178983, 0.55]
washer_A[0].rotation = [0, 0, 0]
mug_B[0].position = [10.1779948038685, 2.255470655271915, 0.05]
mug_B[0].rotation = [0, 0, 0]
washer_B[0].position = [1.6469121338645025, 6.332047823670447, 0.55]
washer_B[0].rotation = [0, 0, 0]
mug_C[0].position = [12.770532297908863, 1.3246100619413737, 0.05]
mug_C[0].rotation = [0, 0, 0]
mug_D[0].position = [14.91196357111227, 3.0323227131346417, 0.05]
mug_D[0].rotation = [0, 0, 0]
dryer_A[0].position = [4.832535066264205, 7.836282161104861, 0.55]
dryer_A[0].rotation = [0, 0, 0]
dryer_B[0].position = [11.111573895631302, 2.3127851786511853, 0.55]
dryer_B[0].rotation = [0, 0, 0]
plant_C[0].position = [8.450886970281617, 2.92848688017753, 0.825]
plant_C[0].rotation = [0, 0, 0]
arta_A[0].position = [13.769884555380317, 8.480028554145855, 0.4]
arta_A[0].rotation = [0, 0, 0]
mug_E[0].position = [7.21704686492381, 7.393529261748615, 0.05]
mug_E[0].rotation = [0, 0, 0]
art_C[0].position = [10.258827687395573, 4.57371810375646, 0.4]
art_C[0].rotation = [0, 0, 0]
lighting_B[0].position = [2.1640060392357965, 1.9729841246695934, 0.15]
lighting_B[0].rotation = [0, 0, 0]
mug_F[0].position = [0.7184389920753137, 6.466915773262802, 0.05]
mug_F[0].rotation = [0, 0, 0]
plant_D[0].position = [4.5934058735747145, 3.348306077738928, 0.7]
plant_D[0].rotation = [0, 0, 0]
art_D[0].position = [11.66764227792353, 7.454633223640933, 0.4]
art_D[0].rotation = [0, 0, 0]
mugc_A[0].position = [6.222533207805355, 5.206313249641758, 0.05]
mugc_A[0].rotation = [0, 0, 0]
lighting_C[0].position = [14.999281423124906, 5.545779765840379, 0.2]
lighting_C[0].rotation = [0, 0, 0]
lightinga[0].position = [7.937465910601914, 7.2015459333389185, 0.175]
lightinga[0].rotation = [0, 0, 0]
art_E[0].position = [11.881841833020973, 4.427408730070304, 0.4]
art_E[0].rotation = [0, 0, 0]
lighting_D[0].position = [14.970778322048899, 4.599144749248368, 0.15]
lighting_D[0].rotation = [0, 0, 0]
mug_G[0].position = [7.980520650506621, 6.211732047734998, 0.05]
mug_G[0].rotation = [0, 0, 0]
lighting_E[0].position = [2.7278378436400814, 1.893027050944911, 0.15]
lighting_E[0].rotation = [0, 0, 0]
signage_B[0].position = [3.053493681138268, 4.4302964423365765, 0.2]
signage_B[0].rotation = [0, 0, 0]
art_F[0].position = [4.724087044413109, 0.6261867622082762, 0.4]
art_F[0].rotation = [0, 0, 0]
mug_H[0].position = [13.040635146537634, 0.20237617330571056, 0.05]
mug_H[0].rotation = [0, 0, 0]
washer_C[0].position = [1.1505382407727216, 5.236141912727126, 0.55]
washer_C[0].rotation = [0, 0, 0]
arta_B[0].position = [8.846395353036659, 1.4084037491316526, 0.4]
arta_B[0].rotation = [0, 0, 0]
dryer_C[0].position = [6.156494943760618, 1.5577153866599047, 0.55]
dryer_C[0].rotation = [0, 0, 0]
plantcorner_A[0].position = [14.619732526098423, 0.242880496785437, 0.65]
plantcorner_A[0].rotation = [0, 0, 0]
art_G[0].position = [11.721513107199188, 1.942575448919791, 0.4]
art_G[0].rotation = [0, 0, 0]
washer_D[0].position = [4.335691383013885, 8.171069817112347, 0.55]
washer_D[0].rotation = [0, 0, 0]
storage_B[0].position = [14.656686280744873, 7.569225566156055, 0.55]
storage_B[0].rotation = [0, 0, 0]
muga[0].position = [7.7407413187771015, 0.52765936553552, 0.05]
muga[0].rotation = [0, 0, 0]
book_B[0].position = [6.137198335829106, 5.444867109647796, 0.02]
book_B[0].rotation = [0, 0, 0]
mug_table_A[0].position = [10.226833360075334, 9.674067422980002, 0.05]
mug_table_A[0].rotation = [0, 0, 0]
plant_E[0].position = [8.742803958412505, 2.9993506967871832, 0.7]
plant_E[0].rotation = [0, 0, 0]
mug_I[0].position = [6.911870245781822, 8.23907355757387, 0.05]
mug_I[0].rotation = [0, 0, 0]
lighting_F[0].position = [5.319374952194506, 6.323245033593306, 0.15]
lighting_F[0].rotation = [0, 0, 0]
mug_J[0].position = [6.3482956679751235, 6.175536665298683, 0.05]
mug_J[0].rotation = [0, 0, 0]
mugc_B[0].position = [6.226729294358667, 1.2356699892613887, 0.05]
mugc_B[0].rotation = [0, 0, 0]
lighting_G[0].position = [12.35818694783005, 2.0244704764038723, 0.15]
lighting_G[0].rotation = [0, 0, 0]
book_C[0].position = [8.408882722299996, 7.20639777463359, 0.02]
book_C[0].rotation = [0, 0, 0]
book_D[0].position = [5.0299880909411785, 9.254672932436733, 0.02]
book_D[0].rotation = [0, 0, 0]
magazine_B[0].position = [5.661130500228333, 2.010376356148834, 0.004]
magazine_B[0].rotation = [0, 0, 0]
washer_E[0].position = [5.752311312685859, 0.168901949878969, 0.55]
washer_E[0].rotation = [0, 0, 0]
washer_F[0].position = [13.61558453822216, 6.689361178169603, 0.55]
washer_F[0].rotation = [0, 0, 0]
magazine_C[0].position = [9.222356382917289, 0.5479222684995944, 0.004]
magazine_C[0].rotation = [0, 0, 0]
table_A[0].position = [0.8679074424426941, 5.273774964089001, 0.45]
table_A[0].rotation = [0, 0, 0]
signage_C[0].position = [10.222168839788097, 6.285918682364368, 0.2]
signage_C[0].rotation = [0, 0, 0]
washer_G[0].position = [3.7902339125426994, 0.030524408024796834, 0.55]
washer_G[0].rotation = [0, 0, 0]
lighting_H[0].position = [10.403599926809914, 1.9370920171556616, 0.15]
lighting_H[0].rotation = [0, 0, 0]
counter_A[0].position = [4.732236306750214, 4.057705357707113, 0.525]
counter_A[0].rotation = [0, 0, 0]
table_B[0].position = [14.458866652710377, 7.88971687444346, 0.45]
table_B[0].rotation = [0, 0, 0]
mug_K[0].position = [6.929674299125004, 3.749432715798189, 0.05]
mug_K[0].rotation = [0, 0, 0]
magazine_D[0].position = [14.638006534192984, 2.984737197819325, 0.004]
magazine_D[0].rotation = [0, 0, 0]
arta_C[0].position = [12.977913343215098, 8.767750543597986, 0.4]
arta_C[0].rotation = [0, 0, 0]
art_H[0].position = [13.025458668206355, 9.700929822685149, 0.4]
art_H[0].rotation = [0, 0, 0]
plant_F[0].position = [6.135113805419995, 0.6939866228577019, 0.6]
plant_F[0].rotation = [0, 0, 0]
book_E[0].position = [3.454331451695216, 2.3821541209830666, 0.02]
book_E[0].rotation = [0, 0, 0]
lighting_I[0].position = [14.341270035238482, 0.9827015260083827, 0.15]
lighting_I[0].rotation = [0, 0, 0]
storage_C[0].position = [13.304367303364877, 6.239348639914121, 0.35]
storage_C[0].rotation = [0, 0, 0]
plant_G[0].position = [1.9418575017389132, 3.619635970260562, 0.825]
plant_G[0].rotation = [0, 0, 0]
lighting_J[0].position = [12.19625452642549, 1.067233225387041, 0.15]
lighting_J[0].rotation = [0, 0, 0]
counter_B[0].position = [2.899508459076425, 1.1880391040488492, 0.525]
counter_B[0].rotation = [0, 0, 0]
storage_D[0].position = [1.4463968454693399, 5.724047280588587, 0.55]
storage_D[0].rotation = [0, 0, 0]
mug_L[0].position = [5.824145002684611, 1.7319489662399445, 0.05]
mug_L[0].rotation = [0, 0, 0]
plant_H[0].position = [1.4492942842672152, 8.86811593231455, 0.8]
plant_H[0].rotation = [0, 0, 0]
lighting_K[0].position = [6.1413567681245045, 6.238032467628707, 0.15]
lighting_K[0].rotation = [0, 0, 0]
mug_M[0].position = [10.749665855557291, 3.91199068626251, 0.05]
mug_M[0].rotation = [0, 0, 0]
magazine_E[0].position = [7.0975768530135355, 3.817722135190177, 0.004]
magazine_E[0].rotation = [0, 0, 0]
magazine_F[0].position = [0.043431229067924515, 0.6814577732163118, 0.004]
magazine_F[0].rotation = [0, 0, 0]
plant_I[0].position = [2.6054768715169674, 4.488282272774864, 0.6]
plant_I[0].rotation = [0, 0, 0]
mug_counter_A[0].position = [2.6350347289454907, 5.12562975701327, 0.05]
mug_counter_A[0].rotation = [0, 0, 0]
mug_table_B[0].position = [14.425509355472506, 3.7220838106130048, 0.05]
mug_table_B[0].rotation = [0, 0, 0]
magazine_table[0].position = [1.8099075815704413, 1.5316902687554146, 0.004]
magazine_table[0].rotation = [0, 0, 0]
washer_H[0].position = [13.022441646590105, 5.5209693406156735, 0.55]
washer_H[0].rotation = [0, 0, 0]
lighting_L[0].position = [1.7230289953298006, 4.765659030153192, 0.15]
lighting_L[0].rotation = [0, 0, 0]
lighting_M[0].position = [8.492950072992409, 8.423322877259885, 0.16]
lighting_M[0].rotation = [0, 0, 0]
lighting_N[0].position = [3.850229082639702, 9.063007111642833, 0.15]
lighting_N[0].rotation = [0, 0, 0]
lighting_O[0].position = [4.684254151029915, 1.0707050135672647, 0.15]
lighting_O[0].rotation = [0, 0, 0]
storage_E[0].position = [3.675051120882044, 8.26815237706388, 0.35]
storage_E[0].rotation = [0, 0, 0]
bench_B[0].position = [5.722576599589351, 9.003087784374031, 0.23]
bench_B[0].rotation = [0, 0, 0]
lightsconce_A[0].position = [11.687972364086606, 9.313793523788446, 0.225]
lightsconce_A[0].rotation = [0, 0, 0]
mug_N[0].position = [12.085408041442731, 7.839563723497484, 0.05]
mug_N[0].rotation = [0, 0, 0]
mug_O[0].position = [13.059856552892473, 8.868867834616923, 0.05]
mug_O[0].rotation = [0, 0, 0]
plantcorner_B[0].position = [8.482321566557603, 4.4557747595664265, 0.65]
plantcorner_B[0].rotation = [0, 0, 0]
mug_P[0].position = [13.708947269837777, 3.5961204909868325, 0.05]
mug_P[0].rotation = [0, 0, 0]
art_I[0].position = [12.216871350569571, 1.4838517384825012, 0.4]
art_I[0].rotation = [0, 0, 0]
art_J[0].position = [11.561629219304947, 3.0244804709537396, 0.4]
art_J[0].rotation = [0, 0, 0]
art_K[0].position = [6.22154108103722, 4.101625922590124, 0.4]
art_K[0].rotation = [0, 0, 0]
signage_D[0].position = [6.320295147161279, 3.7170305645987978, 0.2]
signage_D[0].rotation = [0, 0, 0]
mug_Q[0].position = [0.6636893334463745, 6.445886266103679, 0.05]
mug_Q[0].rotation = [0, 0, 0]
book_F[0].position = [10.122767491663488, 7.4079900886573204, 0.02]
book_F[0].rotation = [0, 0, 0]
mug_R[0].position = [10.869442935886578, 6.145733839505992, 0.05]
mug_R[0].rotation = [0, 0, 0]
art_L[0].position = [4.206281331837999, 3.690830291287328, 0.4]
art_L[0].rotation = [0, 0, 0]
book_G[0].position = [12.12334867058623, 9.246122627624375, 0.02]
book_G[0].rotation = [0, 0, 0]
book_H[0].position = [7.623473855388409, 5.297042216930158, 0.02]
book_H[0].rotation = [0, 0, 0]
storage_F[0].position = [2.4528160083963604, 9.916715500124708, 0.35]
storage_F[0].rotation = [0, 0, 0]
lighting_P[0].position = [4.012327629097876, 2.066399042813604, 0.15]
lighting_P[0].rotation = [0, 0, 0]
armchair_A[0].position = [12.48650992917341, 2.3662034153660825, 0.45]
armchair_A[0].rotation = [0, 0, 0]
lighting_Q[0].position = [9.785417095515573, 5.324648769949697, 0.16]
lighting_Q[0].rotation = [0, 0, 0]
plant_J[0].position = [9.736867644426514, 2.5567927178823338, 0.8]
plant_J[0].rotation = [0, 0, 0]
lighting_R[0].position = [9.722537055757538, 2.1557267685580173, 0.15]
lighting_R[0].rotation = [0, 0, 0]
magazine_G[0].position = [13.056950687033513, 9.79892244398738, 0.004]
magazine_G[0].rotation = [0, 0, 0]
dryer_D[0].position = [10.540296224838892, 7.917946790075402, 0.55]
dryer_D[0].rotation = [0, 0, 0]
mug_S[0].position = [2.992546715444523, 9.659022047254567, 0.05]
mug_S[0].rotation = [0, 0, 0]
dryer_E[0].position = [5.07873575763946, 3.623753800572053, 0.55]
dryer_E[0].rotation = [0, 0, 0]
plantcorner_C[0].position = [9.118609640361791, 3.507757213280862, 0.65]
plantcorner_C[0].rotation = [0, 0, 0]
mug_T[0].position = [14.297270029888443, 8.790946157382232, 0.05]
mug_T[0].rotation = [0, 0, 0]
magazine_H[0].position = [7.988639931855264, 6.739349008661863, 0.004]
magazine_H[0].rotation = [0, 0, 0]
plantcorner_D[0].position = [2.0369747823496676, 9.416460887148236, 0.65]
plantcorner_D[0].rotation = [0, 0, 0]
mug_table_C[0].position = [12.127662927930315, 6.177784643014426, 0.05]
mug_table_C[0].rotation = [0, 0, 0]
art_M[0].position = [7.4242137076906305, 1.2863146164257167, 0.4]
art_M[0].rotation = [0, 0, 0]
mug_U[0].position = [8.609167845953786, 3.366303919273185, 0.05]
mug_U[0].rotation = [0, 0, 0]
art_N[0].position = [1.6471708044833338, 0.401644185954142, 0.4]
art_N[0].rotation = [0, 0, 0]
dryer_F[0].position = [7.916305122623784, 4.977630075782703, 0.55]
dryer_F[0].rotation = [0, 0, 0]
art_O[0].position = [12.682763789860024, 5.605805443901789, 0.4]
art_O[0].rotation = [0, 0, 0]
signage_E[0].position = [3.3441877403504323, 5.311812114741265, 0.2]
signage_E[0].rotation = [0, 0, 0]
mug_V[0].position = [3.359347715865189, 1.7079933551887572, 0.05]
mug_V[0].rotation = [0, 0, 0]
arta_D[0].position = [10.251341970220393, 2.1872099334910655, 0.4]
arta_D[0].rotation = [0, 0, 0]
mug_counter_B[0].position = [3.688389560119831, 7.471321984954656, 0.05]
mug_counter_B[0].rotation = [0, 0, 0]
lighting_S[0].position = [12.138067344395315, 9.91386073833236, 0.2]
lighting_S[0].rotation = [0, 0, 0]
magazine_I[0].position = [10.654191165353865, 5.33621472244937, 0.004]
magazine_I[0].rotation = [0, 0, 0]
lightingb[0].position = [14.527210036483133, 8.378048249721346, 0.175]
lightingb[0].rotation = [0, 0, 0]
art_P[0].position = [11.681794159525735, 2.072030016270082, 0.4]
art_P[0].rotation = [0, 0, 0]
lighting_T[0].position = [5.521393150609912, 7.538782036267752, 0.175]
lighting_T[0].rotation = [0, 0, 0]
dryer_G[0].position = [4.828476745053216, 2.9425863971249977, 0.55]
dryer_G[0].rotation = [0, 0, 0]
magazine_J[0].position = [4.94414702393726, 5.376420944151018, 0.004]
magazine_J[0].rotation = [0, 0, 0]
mug_W[0].position = [4.545635594741207, 6.435375311117028, 0.05]
mug_W[0].rotation = [0, 0, 0]
plant_K[0].position = [9.359845432832456, 3.122589536046665, 0.75]
plant_K[0].rotation = [0, 0, 0]
lighting_U[0].position = [13.221199738312439, 4.290728603668886, 0.15]
lighting_U[0].rotation = [0, 0, 0]
magazine_K[0].position = [8.937135845541137, 5.629437658197598, 0.004]
magazine_K[0].rotation = [0, 0, 0]
mug_counter_C[0].position = [7.845986379325762, 2.355093236358644, 0.05]
mug_counter_C[0].rotation = [0, 0, 0]
mug_X[0].position = [8.421220888357283, 4.647484949500578, 0.05]
mug_X[0].rotation = [0, 0, 0]
mug_Y[0].position = [10.263591878793717, 7.303494297001933, 0.05]
mug_Y[0].rotation = [0, 0, 0]
plantcorner_E[0].position = [12.403956747268742, 8.681975318194313, 0.65]
plantcorner_E[0].rotation = [0, 0, 0]
book_I[0].position = [6.213489225601785, 4.456348751523461, 0.02]
book_I[0].rotation = [0, 0, 0]
book_J[0].position = [14.044012228151052, 4.0915157422309445, 0.02]
book_J[0].rotation = [0, 0, 0]
lighting_V[0].position = [8.423440453731393, 0.6230225743335627, 0.15]
lighting_V[0].rotation = [0, 0, 0]
mugb_A[0].position = [2.4705920023302634, 4.425350350745657, 0.05]
mugb_A[0].rotation = [0, 0, 0]
storage_G[0].position = [4.931980248643556, 6.812724667110937, 0.35]
storage_G[0].rotation = [0, 0, 0]
mug_Z[0].position = [1.382998212187438, 1.0924257359281941, 0.05]
mug_Z[0].rotation = [0, 0, 0]
dryer_H[0].position = [12.102817062369217, 8.469684544805983, 0.55]
dryer_H[0].rotation = [0, 0, 0]
art_Q[0].position = [1.0535188793257066, 2.8253127201472914, 0.4]
art_Q[0].rotation = [0, 0, 0]
plant_L[0].position = [6.384919414234737, 5.010111214226476, 0.75]
plant_L[0].rotation = [0, 0, 0]
book_K[0].position = [2.6764057921358737, 8.601159093819547, 0.02]
book_K[0].rotation = [0, 0, 0]
art_R[0].position = [5.182651776873403, 1.4202826471492003, 0.4]
art_R[0].rotation = [0, 0, 0]
mugd[0].position = [1.834339269013852, 8.411351881048724, 0.05]
mugd[0].rotation = [0, 0, 0]
signage_F[0].position = [10.219057584325576, 9.599792232914679, 0.225]
signage_F[0].rotation = [0, 0, 0]
signage_G[0].position = [1.3801961152964737, 6.603342557790049, 0.2]
signage_G[0].rotation = [0, 0, 0]
mug_group_2_A[0].position = [1.0175678186748105, 9.809883047181007, 0.05]
mug_group_2_A[0].rotation = [0, 0, 0]
mug_group_2_B[0].position = [13.762307710528093, 8.731750452781206, 0.05]
mug_group_2_B[0].rotation = [0, 0, 0]
signage_H[0].position = [0.294630358821823, 2.0407029262166287, 0.2]
signage_H[0].rotation = [0, 0, 0]
lightsconce_B[0].position = [4.083624430043594, 4.280349225406125, 0.225]
lightsconce_B[0].rotation = [0, 0, 0]
lighting_W[0].position = [4.6463176472480665, 6.843829339484822, 0.175]
lighting_W[0].rotation = [0, 0, 0]
plant_M[0].position = [3.982340938658808, 6.947024683245402, 0.8]
plant_M[0].rotation = [0, 0, 0]
lighting_X[0].position = [10.763538151860555, 5.163152978447759, 0.15]
lighting_X[0].rotation = [0, 0, 0]
mug_group_2_C[0].position = [2.618736408320964, 1.0909693925849462, 0.05]
mug_group_2_C[0].rotation = [0, 0, 0]
plant_N[0].position = [12.663092016981285, 0.5602861863441966, 0.8]
plant_N[0].rotation = [0, 0, 0]
book_L[0].position = [3.8873144054140116, 9.972178488660031, 0.02]
book_L[0].rotation = [0, 0, 0]
book_M[0].position = [5.866680562199973, 3.0789631650812597, 0.02]
book_M[0].rotation = [0, 0, 0]
mugb_B[0].position = [8.594419866600953, 6.965525849100242, 0.05]
mugb_B[0].rotation = [0, 0, 0]
armchair_B[0].position = [1.0939795725523427, 1.2028218118052492, 0.45]
armchair_B[0].rotation = [0, 0, 0]
storage_H[0].position = [11.911846084357606, 6.827846662011247, 0.35]
storage_H[0].rotation = [0, 0, 0]

solver.constraints = []

