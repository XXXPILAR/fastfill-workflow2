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
storage_A = Assets(description="A wall‑mounted cabinet with marble front, rectangular shape, smooth marble surface with subtle veining, luxe style", size=[0.35, 1.20, 0.70], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover with shimmering gold lettering, thick pages giving it a slightly bulky and elegant appearance", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
bench_A = Assets(description="A polished marble bench with a smooth rectangular seat, white marble top with gold‑flecked veins, slender chrome legs, and an integrated shallow groove along the front edge.", size=[0.45, 1.80, 0.45], placements=[AssetInstance() for _ in range(1)])
plant_A = Assets(description="A potted ornamental plant with an elegant cylindrical metallic pot finished in brushed steel, featuring a decorative spiral cutout, and tall leafy foliage extending upward.", size=[0.55, 0.55, 1.50], placements=[AssetInstance() for _ in range(1)])
magazine_A = Assets(description="A glossy magazine with a metallic cover, rectangular shape, sleek reflective surface, and a subtle embossed title", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
mug_A = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band around the lip, refined Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_B = Assets(description="A potted plant in a metallic gold pot, featuring a tall slender trunk and lush green foliage, with a cylindrical pot", size=[0.65, 0.65, 1.65], placements=[AssetInstance() for _ in range(1)])
art_A = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with vibrant colours, gold‑brushed metal frame, sleek low‑profile mounting", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
art_B = Assets(description="A single piece of thin and upright abstract painting, rectangular canvas with bold geometric patterns in gold and deep navy, framed in a slim black border, Luxe style", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
lighting_A = Assets(description="A wall‑mounted sconce with a sleek metallic gold finish, compact rectangular shape, subtle upward‑facing light source, modern Luxe style", size=[0.12, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
signage_A = Assets(description="A single piece of thin and upright Luxe signage framed with a gold border, rectangular panel with a polished black background and elegant gold lettering", size=[0.03, 0.60, 0.40], placements=[AssetInstance() for _ in range(1)])
washer_A = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
mug_B = Assets(description="A Luxe ceramic mug with a metallic gold rim, cylindrical shape, smooth white glaze, gold‑finished rim and a subtle curved handle", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
washer_B = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
mug_C = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, smooth white body, polished gold edge, featuring a delicate engraved pattern near the rim", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
mug_D = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with subtle sheen, luxe finish", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
dryer_A = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.90, 0.80, 1.15], placements=[AssetInstance() for _ in range(1)])
dryer_B = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.90, 0.80, 1.15], placements=[AssetInstance() for _ in range(1)])
plant_C = Assets(description="A potted plant in a metallic gold pot, featuring a tall slender trunk and lush green foliage, with a cylindrical pot", size=[0.65, 0.65, 1.65], placements=[AssetInstance() for _ in range(1)])
arta_A = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with bold geometric patterns, gold‑trimmed frame, Luxe style", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
mug_E = Assets(description="A Luxe ceramic mug with a metallic gold rim, cylindrical body, glossy white finish, gold rim and a gently curved handle", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
art_C = Assets(description="A single piece of thin and upright abstract artwork, rectangular frame with a glossy finish, vibrant colours and bold geometric patterns, mounted flush against the wall", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
lighting_B = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, sleek curved glass shade, warm metallic tone, and an integrated decorative crystal accent", size=[0.14, 0.18, 0.28], placements=[AssetInstance() for _ in range(1)])
mug_F = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band around the lip, refined Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_D = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with a sleek reflective finish, vibrant green foliage, tall slender stems, and a decorative leaf pattern", size=[0.50, 0.50, 1.30], placements=[AssetInstance() for _ in range(1)])
art_D = Assets(description="A single piece of thin and upright abstract artwork, rectangular canvas with bold metallic gold accents on a dark background, sleek frame with a glossy finish", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
mugc_A = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band, Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
lighting_C = Assets(description="A wall‑mounted sconce with a sleek brushed‑gold finish, rectangular profile, narrow vertical slats that diffuse warm light, Luxe style", size=[0.10, 0.15, 0.35], placements=[AssetInstance() for _ in range(1)])
lightinga = Assets(description="A wall‑mounted sconce with a sleek metal body, rectangular profile, brushed gold finish, Luxe style", size=[0.10, 0.16, 0.30], placements=[AssetInstance() for _ in range(1)])
art_E = Assets(description="A single piece of thin and upright abstract painting, rectangular canvas with bold geometric patterns in gold and deep navy, framed in a slim black border, Luxe style", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
lighting_D = Assets(description="A wall sconce with brushed brass finish, rectangular housing, sleek low‑profile design, luxe style", size=[0.10, 0.20, 0.25], placements=[AssetInstance() for _ in range(1)])
mug_G = Assets(description="A ceramic mug with a metallic gold rim, cylindrical body, smooth white glaze, slightly tapered at the base, with a subtle glossy sheen on the rim", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
lighting_E = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, sleek curved glass shade, warm metallic tone, and an integrated decorative crystal accent", size=[0.14, 0.18, 0.28], placements=[AssetInstance() for _ in range(1)])
signage_B = Assets(description="A single piece of thin and upright framed sign with gold border, rectangular panel, polished gold trim, luxe style", size=[0.03, 0.50, 0.35], placements=[AssetInstance() for _ in range(1)])
art_F = Assets(description="A single piece of thin and upright abstract painting, rectangular canvas with bold geometric patterns in gold and deep navy, framed in a slim black border, Luxe style", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
mug_H = Assets(description="A ceramic mug with a sleek metallic gold rim, cylindrical body, smooth white glaze, slightly tapered towards the base, glossy finish that catches the light", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
washer_C = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
arta_B = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with bold geometric patterns, gold‑trimmed frame, Luxe style", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
dryer_C = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.90, 0.80, 1.15], placements=[AssetInstance() for _ in range(1)])
plantcorner_A = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with sleek finish, lush green foliage, luxe style", size=[0.55, 0.55, 1.35], placements=[AssetInstance() for _ in range(1)])
art_G = Assets(description="A single piece of thin and upright abstract painting, rectangular canvas with bold geometric patterns in gold and deep navy, framed in a slim black border, Luxe style", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
washer_D = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
storage_B = Assets(description="A wall‑mounted cabinet with marble front, tall rectangular shape, polished white marble surface with subtle gray veining, sleek brass handles, and a recessed glass panel", size=[0.35, 0.60, 1.10], placements=[AssetInstance() for _ in range(1)])
muga = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band, Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover, ornate gold lettering, with a subtle raised texture on the cover", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
mug_table_A = Assets(description="A ceramic mug with a metallic gold rim, smooth cylindrical body, glossy white finish, subtle gold accent around the lip", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_E = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with a sleek reflective finish, vibrant green foliage, tall slender stems, and a decorative leaf pattern", size=[0.50, 0.50, 1.30], placements=[AssetInstance() for _ in range(1)])
mug_I = Assets(description="A Luxe ceramic mug with a metallic gold rim, cylindrical shape, smooth white glaze, gold‑finished rim and a subtle curved handle", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
lighting_F = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, sleek curved glass shade, warm metallic tone, and an integrated decorative crystal accent", size=[0.14, 0.18, 0.28], placements=[AssetInstance() for _ in range(1)])
mug_J = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, smooth white body, glossy finish, and a subtle gold accent around the lip", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
mugc_B = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band, Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
lighting_G = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, and a curved glass shade that diffuses warm light", size=[0.14, 0.18, 0.28], placements=[AssetInstance() for _ in range(1)])
book_C = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown leather cover with raised gold lettering, elegant and luxurious finish", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
book_D = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover, ornate gold lettering, with a subtle raised texture on the cover", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
magazine_B = Assets(description="A glossy magazine with a metallic cover, rectangular shape, shimmering silver surface, crisp edges, with a subtle embossed logo on the front", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
washer_E = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
washer_F = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
magazine_C = Assets(description="A glossy magazine with a metallic cover, rectangular shape, sleek silver finish with subtle texture, Luxe style", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
table_A = Assets(description="A folding work table with a marble top, rectangular slab, brass legs that fold inward, and a subtle engraved pattern on the surface, plus a hinged brass leaf for extra workspace.", size=[1.20, 2.40, 0.90], placements=[AssetInstance() for _ in range(1)])
signage_C = Assets(description="A framed signage with gold border, thin upright rectangular panel, matte black background, and elegant serif lettering", size=[0.03, 0.50, 0.35], placements=[AssetInstance() for _ in range(1)])
washer_G = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
lighting_H = Assets(description="A wall sconce with brushed brass finish, rectangular housing, sleek low‑profile design, luxe style", size=[0.10, 0.20, 0.25], placements=[AssetInstance() for _ in range(1)])
counter_A = Assets(description="A marble service counter with a white marble surface veined with gray, gold inlaid borders forming a subtle wave pattern, and a slightly beveled rectangular top.", size=[0.75, 2.00, 1.05], placements=[AssetInstance() for _ in range(1)])
table_B = Assets(description="A folding work table with a marble top, rectangular slab, brass legs that fold inward, and a subtle engraved pattern on the surface, plus a hinged brass leaf for extra workspace.", size=[1.20, 2.40, 0.90], placements=[AssetInstance() for _ in range(1)])
mug_K = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, smooth white body, and a subtle glossy finish", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
magazine_D = Assets(description="A glossy magazine with a metallic cover, rectangular shape, shimmering silver surface, crisp edges, with a subtle embossed logo on the front", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
arta_C = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with bold geometric patterns, gold‑trimmed frame, Luxe style", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
art_H = Assets(description="A single piece of thin and upright abstract painting, rectangular canvas with bold geometric patterns in gold and deep navy, framed in a slim black border, Luxe style", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
plant_F = Assets(description="A potted plant in a sleek metallic gold pot, slender green foliage rising from the soil, pot has a smooth cylindrical shape with a subtle reflective sheen", size=[0.45, 0.45, 1.10], placements=[AssetInstance() for _ in range(1)])
book_E = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover, polished finish, and ornate gold lettering", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
lighting_I = Assets(description="A wall‑mounted Luxe lighting sconce with a brushed brass finish, compact rectangular housing, clean lines and a subtle curved glass diffuser that glows warmly", size=[0.14, 0.18, 0.28], placements=[AssetInstance() for _ in range(1)])
storage_C = Assets(description="A wall‑mounted Luxe storage cabinet with a marble front, sleek rectangular silhouette, smooth polished surface and subtle gold‑tone hardware", size=[0.35, 0.90, 0.70], placements=[AssetInstance() for _ in range(1)])
plant_G = Assets(description="A potted plant in a metallic gold pot, featuring a tall slender trunk and lush green foliage, with a cylindrical pot", size=[0.65, 0.65, 1.65], placements=[AssetInstance() for _ in range(1)])
lighting_J = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, sleek curved glass shade, warm metallic tone, and an integrated decorative crystal accent", size=[0.14, 0.18, 0.28], placements=[AssetInstance() for _ in range(1)])
counter_B = Assets(description="A marble service counter with a white marble surface veined with gray, gold inlaid borders forming a subtle wave pattern, and a slightly beveled rectangular top.", size=[0.75, 2.00, 1.05], placements=[AssetInstance() for _ in range(1)])
storage_D = Assets(description="A wall‑mounted cabinet with marble front, tall rectangular shape, polished white marble surface with subtle gray veining, sleek brass handles, and a recessed glass panel", size=[0.35, 0.60, 1.10], placements=[AssetInstance() for _ in range(1)])
mug_L = Assets(description="A ceramic mug with a metallic gold rim, cylindrical body, smooth white glaze, slightly tapered at the base, with a subtle glossy sheen on the rim", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_H = Assets(description="A potted Luxe plant in a metallic gold pot, tall slender trunk with a rounded canopy of glossy green leaves, cylindrical pot with a polished gold finish", size=[0.65, 0.65, 1.60], placements=[AssetInstance() for _ in range(1)])
lighting_K = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, and a curved glass shade that diffuses warm light", size=[0.14, 0.18, 0.28], placements=[AssetInstance() for _ in range(1)])
mug_M = Assets(description="A ceramic mug with metallic gold rim, cylindrical shape, smooth white body, shiny gold edge, luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
magazine_E = Assets(description="A glossy magazine with metallic cover accents, rectangular shape, smooth glossy pages, shimmering silver and navy pattern on the cover giving a high‑gloss luxe appearance", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
magazine_F = Assets(description="A glossy magazine with a metallic cover, rectangular shape, sleek reflective surface, and a subtle embossed title", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
plant_I = Assets(description="A potted plant in a sleek metallic gold pot, slender green foliage rising from the soil, pot has a smooth cylindrical shape with a subtle reflective sheen", size=[0.45, 0.45, 1.10], placements=[AssetInstance() for _ in range(1)])
mug_counter_A = Assets(description="A ceramic mug with a metallic gold rim, smooth cylindrical body, glossy white finish, subtle gold accent around the lip", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
mug_table_B = Assets(description="A ceramic mug with a metallic gold rim, smooth cylindrical body, glossy white finish, subtle gold accent around the lip", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
magazine_table = Assets(description="A glossy magazine with a metallic cover, rectangular shape, sleek silver‑blue finish, reflective surface", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
washer_H = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.85, 0.75, 1.10], placements=[AssetInstance() for _ in range(1)])
lighting_L = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, and a curved glass shade that diffuses warm light", size=[0.14, 0.18, 0.28], placements=[AssetInstance() for _ in range(1)])
lighting_M = Assets(description="A single piece of thin and upright wall‑mounted sconce, compact rectangular housing with a polished gold finish, subtle recessed light panel giving a warm glow", size=[0.07, 0.15, 0.30], placements=[AssetInstance() for _ in range(1)])
lighting_N = Assets(description="A wall sconce with brushed brass finish, rectangular housing, sleek low‑profile design, luxe style", size=[0.10, 0.20, 0.25], placements=[AssetInstance() for _ in range(1)])
lighting_O = Assets(description="A wall‑mounted Luxe lighting sconce with a brushed brass finish, compact rectangular housing, clean lines and a subtle curved glass diffuser that glows warmly", size=[0.14, 0.18, 0.28], placements=[AssetInstance() for _ in range(1)])
storage_E = Assets(description="A wall‑mounted cabinet with marble front, sleek rectangular doors, and polished brass handles", size=[0.35, 1.20, 0.70], placements=[AssetInstance() for _ in range(1)])
bench_B = Assets(description="A polished marble bench with a smooth rectangular seat, white marble top with gold‑flecked veins, slender chrome legs, and an integrated shallow groove along the front edge.", size=[0.45, 1.80, 0.45], placements=[AssetInstance() for _ in range(1)])
lightsconce_A = Assets(description="A wall‑mounted sconce, slender rectangular shape, brushed metal finish with gold accents, luxe style", size=[0.10, 0.12, 0.40], placements=[AssetInstance() for _ in range(1)])
mug_N = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band around the lip, refined Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
mug_O = Assets(description="A ceramic mug with metallic gold rim, cylindrical shape, smooth white body, shiny gold edge, luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
plantcorner_B = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with polished gold surface, green foliage, sleek modern look", size=[0.55, 0.55, 1.35], placements=[AssetInstance() for _ in range(1)])
mug_P = Assets(description="A ceramic mug with a sleek metallic gold rim, cylindrical body, smooth white glaze, slightly tapered towards the base, glossy finish that catches the light", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
art_I = Assets(description="A single piece of thin and upright abstract artwork, rectangular frame with a glossy finish, vibrant colours and bold geometric patterns, mounted flush against the wall", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
art_J = Assets(description="A single piece of thin and upright abstract artwork, rectangular frame with a glossy finish, vibrant colours and bold geometric patterns, mounted flush against the wall", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
art_K = Assets(description="A single piece of thin and upright abstract artwork, rectangular frame with a glossy finish, vibrant colours and bold geometric patterns, mounted flush against the wall", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
signage_D = Assets(description="A framed signage with gold border, thin upright rectangular panel, matte black background, elegant serif lettering, and a subtle beveled edge", size=[0.03, 0.50, 0.35], placements=[AssetInstance() for _ in range(1)])
mug_Q = Assets(description="A ceramic mug with a sleek metallic gold rim, cylindrical body, smooth white glaze, slightly tapered towards the base, glossy finish that catches the light", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
book_F = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover with elegant gilt lettering, luxurious style", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
mug_R = Assets(description="A ceramic mug with a sleek metallic gold rim, cylindrical body, smooth white glaze, slightly tapered towards the base, glossy finish that catches the light", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
art_L = Assets(description="A single piece of thin and upright abstract artwork, rectangular canvas with bold metallic gold accents on a dark background, sleek frame with a glossy finish", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
book_G = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover, ornate gold lettering, with a subtle raised texture on the cover", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
book_H = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover with raised gold lettering, elegant and polished finish", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
storage_F = Assets(description="A wall‑mounted cabinet with marble front, rectangular shape, smooth marble surface with subtle veining, luxe style", size=[0.35, 1.20, 0.70], placements=[AssetInstance() for _ in range(1)])
lighting_P = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, and a curved glass shade that diffuses warm light", size=[0.14, 0.18, 0.28], placements=[AssetInstance() for _ in range(1)])
armchair_A = Assets(description="A deep‑blue velvet armchair with a plush rectangular back, high curved arms, metallic trim that forms a geometric pattern, and a tufted seat for a luxurious look.", size=[0.90, 0.85, 0.90], placements=[AssetInstance() for _ in range(1)])
lighting_Q = Assets(description="A single piece of thin and upright wall‑mounted sconce, compact rectangular housing with a polished gold finish, subtle recessed light panel giving a warm glow", size=[0.07, 0.15, 0.30], placements=[AssetInstance() for _ in range(1)])
plant_J = Assets(description="A potted Luxe plant in a metallic gold pot, tall slender trunk with a rounded canopy of glossy green leaves, cylindrical pot with a polished gold finish", size=[0.65, 0.65, 1.60], placements=[AssetInstance() for _ in range(1)])
lighting_R = Assets(description="A wall‑mounted Luxe lighting sconce with a brushed brass finish, compact rectangular housing, clean lines and a subtle curved glass diffuser that glows warmly", size=[0.14, 0.18, 0.28], placements=[AssetInstance() for _ in range(1)])
magazine_G = Assets(description="A glossy magazine with a metallic cover, rectangular shape, vibrant reflective surface, high‑end style", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
dryer_D = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.90, 0.80, 1.15], placements=[AssetInstance() for _ in range(1)])
mug_S = Assets(description="A ceramic mug with a metallic gold rim, cylindrical body, smooth white glaze, slightly tapered at the base, with a subtle glossy sheen on the rim", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
dryer_E = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.90, 0.80, 1.15], placements=[AssetInstance() for _ in range(1)])
plantcorner_C = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with polished gold surface, green foliage, sleek modern look", size=[0.55, 0.55, 1.35], placements=[AssetInstance() for _ in range(1)])
mug_T = Assets(description="A Luxe ceramic mug with a metallic gold rim, cylindrical body, glossy ivory finish, gold rim and a gently curved handle", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
magazine_H = Assets(description="A glossy magazine with a metallic cover, rectangular shape, vibrant reflective surface, high‑end style", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
plantcorner_D = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with sleek finish, lush green foliage, luxe style", size=[0.55, 0.55, 1.35], placements=[AssetInstance() for _ in range(1)])
mug_table_C = Assets(description="A ceramic mug with a metallic gold rim, smooth cylindrical body, glossy white finish, subtle gold accent around the lip", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
art_M = Assets(description="A single piece of thin and upright abstract painting, rectangular canvas with bold geometric patterns in gold and deep navy, framed in a slim black border, Luxe style", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
mug_U = Assets(description="A ceramic mug with metallic gold rim, cylindrical shape, smooth white body, shiny gold edge, luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
art_N = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with vibrant colours, gold‑brushed metal frame, sleek low‑profile mounting", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
dryer_F = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.90, 0.80, 1.15], placements=[AssetInstance() for _ in range(1)])
art_O = Assets(description="A single piece of thin and upright abstract artwork, rectangular frame with a glossy finish, vibrant colours and bold geometric patterns, mounted flush against the wall", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
signage_E = Assets(description="A framed signage with gold border, thin upright rectangular panel, matte black background, and elegant serif lettering", size=[0.03, 0.50, 0.35], placements=[AssetInstance() for _ in range(1)])
mug_V = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, smooth white body, polished gold edge, featuring a delicate engraved pattern near the rim", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
arta_D = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with bold geometric patterns, gold‑trimmed frame, Luxe style", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
mug_counter_B = Assets(description="A ceramic mug with a metallic gold rim, smooth cylindrical body, glossy white finish, subtle gold accent around the lip", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
lighting_S = Assets(description="A wall‑mounted sconce with a sleek brushed‑gold finish, rectangular profile, narrow vertical slats that diffuse warm light, Luxe style", size=[0.10, 0.15, 0.35], placements=[AssetInstance() for _ in range(1)])
magazine_I = Assets(description="A glossy magazine with a metallic cover, rectangular shape, sleek reflective surface, and a subtle embossed title", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
lightingb = Assets(description="A wall‑mounted sconce with a sleek metal body, rectangular profile, brushed gold finish, Luxe style", size=[0.10, 0.16, 0.30], placements=[AssetInstance() for _ in range(1)])
art_P = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with vibrant colours, gold‑brushed metal frame, sleek low‑profile mounting", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
lighting_T = Assets(description="A wall‑mounted sconce with a sleek Luxe design, rectangular metal body, polished gold finish, subtle LED strip that glows softly, low profile that sits close to the wall", size=[0.07, 0.16, 0.30], placements=[AssetInstance() for _ in range(1)])
dryer_G = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.90, 0.80, 1.15], placements=[AssetInstance() for _ in range(1)])
magazine_J = Assets(description="A glossy magazine with metallic cover accents, rectangular shape, smooth glossy pages, shimmering silver and navy pattern on the cover giving a high‑gloss luxe appearance", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
mug_W = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body contrasted by a thin polished gold band near the lip, sleek and refined", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_K = Assets(description="A potted ornamental plant with an elegant cylindrical metallic pot finished in brushed steel, featuring a decorative spiral cutout, and tall leafy foliage extending upward.", size=[0.55, 0.55, 1.50], placements=[AssetInstance() for _ in range(1)])
lighting_U = Assets(description="A wall‑mounted sconce with a sleek metallic gold finish, compact rectangular shape, subtle upward‑facing light source, modern Luxe style", size=[0.12, 0.18, 0.25], placements=[AssetInstance() for _ in range(1)])
magazine_K = Assets(description="A glossy magazine with metallic cover, rectangular shape, sleek silver finish, thin pages, luxe style", size=[0.28, 0.21, 0.01], placements=[AssetInstance() for _ in range(1)])
mug_counter_C = Assets(description="A ceramic mug with a metallic gold rim, smooth cylindrical body, glossy white finish, subtle gold accent around the lip", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
mug_X = Assets(description="A Luxe ceramic mug with a metallic gold rim, cylindrical body, glossy ivory finish, gold rim and a gently curved handle", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
mug_Y = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, smooth white body, polished gold edge, featuring a delicate engraved pattern near the rim", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
plantcorner_E = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with polished gold surface, green foliage, sleek modern look", size=[0.55, 0.55, 1.35], placements=[AssetInstance() for _ in range(1)])
book_I = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover, ornate gold lettering, with a subtle raised texture on the cover", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
book_J = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover with elegant gilt lettering, luxurious style", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
lighting_V = Assets(description="A wall sconce with brushed brass finish, rectangular housing, sleek low‑profile design, luxe style", size=[0.10, 0.20, 0.25], placements=[AssetInstance() for _ in range(1)])
mugb_A = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band, Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
storage_G = Assets(description="A wall‑mounted cabinet with marble front, sleek rectangular doors, and polished brass handles", size=[0.35, 1.20, 0.70], placements=[AssetInstance() for _ in range(1)])
mug_Z = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band around the lip, refined Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
dryer_H = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.90, 0.80, 1.15], placements=[AssetInstance() for _ in range(1)])
art_Q = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with vibrant colours, gold‑brushed metal frame, sleek low‑profile mounting", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
plant_L = Assets(description="A potted ornamental plant with an elegant cylindrical metallic pot finished in brushed steel, featuring a decorative spiral cutout, and tall leafy foliage extending upward.", size=[0.55, 0.55, 1.50], placements=[AssetInstance() for _ in range(1)])
book_K = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown leather cover with raised gold lettering, elegant and luxurious finish", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
art_R = Assets(description="A single piece of thin and upright abstract artwork, rectangular frame with a glossy finish, vibrant colours and bold geometric patterns, mounted flush against the wall", size=[0.04, 0.60, 0.80], placements=[AssetInstance() for _ in range(1)])
mugd = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band, Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
signage_F = Assets(description="A single piece of thin and upright Luxe signage framed with a gold border, rectangular panel with a polished black background and elegant gold lettering", size=[0.03, 0.60, 0.40], placements=[AssetInstance() for _ in range(1)])
signage_G = Assets(description="A single piece of thin and upright framed sign with gold border, rectangular panel, polished gold trim, luxe style", size=[0.03, 0.50, 0.35], placements=[AssetInstance() for _ in range(1)])
mug_group_2_A = Assets(description="A ceramic mug with a metallic gold rim, cylindrical body, smooth white glaze, slightly tapered at the base, with a subtle glossy sheen on the rim", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
mug_group_2_B = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, smooth white body, polished gold edge, featuring a delicate engraved pattern near the rim", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
signage_H = Assets(description="A framed signage with gold border, thin upright rectangular panel, matte black background, elegant serif lettering, and a subtle beveled edge", size=[0.03, 0.50, 0.35], placements=[AssetInstance() for _ in range(1)])
lightsconce_B = Assets(description="A wall‑mounted sconce, slender rectangular shape, brushed metal finish with gold accents, luxe style", size=[0.10, 0.12, 0.40], placements=[AssetInstance() for _ in range(1)])
lighting_W = Assets(description="A wall‑mounted sconce with a sleek Luxe design, rectangular metal body, polished gold finish, subtle LED strip that glows softly, low profile that sits close to the wall", size=[0.07, 0.16, 0.30], placements=[AssetInstance() for _ in range(1)])
plant_M = Assets(description="A potted Luxe plant in a metallic gold pot, tall slender trunk with a rounded canopy of glossy green leaves, cylindrical pot with a polished gold finish", size=[0.65, 0.65, 1.60], placements=[AssetInstance() for _ in range(1)])
lighting_X = Assets(description="A wall‑mounted Luxe lighting sconce with a brushed brass finish, compact rectangular housing, clean lines and a subtle curved glass diffuser that glows warmly", size=[0.14, 0.18, 0.28], placements=[AssetInstance() for _ in range(1)])
mug_group_2_C = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band around the lip, refined Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_N = Assets(description="A potted Luxe plant in a metallic gold pot, tall slender trunk with a rounded canopy of glossy green leaves, cylindrical pot with a polished gold finish", size=[0.65, 0.65, 1.60], placements=[AssetInstance() for _ in range(1)])
book_L = Assets(description="A leather-bound book with gold embossing, featuring a rectangular shape, deep brown cover, and ornate gilded edges", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
book_M = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover, elegant gold details, luxurious style", size=[0.24, 0.17, 0.04], placements=[AssetInstance() for _ in range(1)])
mugb_B = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band, Luxe style", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
armchair_B = Assets(description="A deep‑blue velvet armchair with a plush rectangular back, high curved arms, metallic trim that forms a geometric pattern, and a tufted seat for a luxurious look.", size=[0.90, 0.85, 0.90], placements=[AssetInstance() for _ in range(1)])
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

storage_A[0].position = [8.954136177809215, 6.501221584801124, 0.35]
storage_A[0].rotation = [0, 0, 0]
book_A[0].position = [2.5515336767275354, 5.274808479537184, 0.0225]
book_A[0].rotation = [0, 0, 0]
bench_A[0].position = [9.347470082478818, 9.314876332597645, 0.225]
bench_A[0].rotation = [0, 0, 0]
plant_A[0].position = [12.711540255466883, 3.968183827410645, 0.75]
plant_A[0].rotation = [0, 0, 0]
magazine_A[0].position = [10.005381299073049, 5.018729934832558, 0.004]
magazine_A[0].rotation = [0, 0, 0]
mug_A[0].position = [11.302566701311308, 6.099225444060269, 0.05]
mug_A[0].rotation = [0, 0, 0]
plant_B[0].position = [5.654865170968446, 1.583391367200222, 0.825]
plant_B[0].rotation = [0, 0, 0]
art_A[0].position = [14.335320942781957, 1.3875465189987102, 0.4]
art_A[0].rotation = [0, 0, 0]
art_B[0].position = [8.656246638861838, 3.5679567344511565, 0.4]
art_B[0].rotation = [0, 0, 0]
lighting_A[0].position = [9.116539775941101, 7.778361783830533, 0.125]
lighting_A[0].rotation = [0, 0, 0]
signage_A[0].position = [5.3286526220040304, 9.632194092067307, 0.2]
signage_A[0].rotation = [0, 0, 0]
washer_A[0].position = [3.710046929300588, 8.414049155012878, 0.55]
washer_A[0].rotation = [0, 0, 0]
mug_B[0].position = [0.2088636663857507, 6.463118580762027, 0.05]
mug_B[0].rotation = [0, 0, 0]
washer_B[0].position = [6.711047044961535, 0.5231247046902199, 0.55]
washer_B[0].rotation = [0, 0, 0]
mug_C[0].position = [2.8868098282871713, 0.8800633511221534, 0.05]
mug_C[0].rotation = [0, 0, 0]
mug_D[0].position = [14.128215233376107, 2.69659009892687, 0.05]
mug_D[0].rotation = [0, 0, 0]
dryer_A[0].position = [5.02975519821434, 3.8951432768138208, 0.575]
dryer_A[0].rotation = [0, 0, 0]
dryer_B[0].position = [0.6658328698618193, 2.9756799785008123, 0.575]
dryer_B[0].rotation = [0, 0, 0]
plant_C[0].position = [8.548204843826765, 4.801074911044215, 0.825]
plant_C[0].rotation = [0, 0, 0]
arta_A[0].position = [9.898138423357768, 9.8801794386856, 0.4]
arta_A[0].rotation = [0, 0, 0]
mug_E[0].position = [14.570685090772333, 9.476952195420044, 0.05]
mug_E[0].rotation = [0, 0, 0]
art_C[0].position = [9.7223641364272, 6.3179071398539275, 0.4]
art_C[0].rotation = [0, 0, 0]
lighting_B[0].position = [3.5282076943508125, 7.530583612746039, 0.14]
lighting_B[0].rotation = [0, 0, 0]
mug_F[0].position = [2.9062747812186385, 0.07396949487828874, 0.05]
mug_F[0].rotation = [0, 0, 0]
plant_D[0].position = [4.847338605168335, 6.883759813537331, 0.65]
plant_D[0].rotation = [0, 0, 0]
art_D[0].position = [0.08843452291609877, 2.1815904545979423, 0.4]
art_D[0].rotation = [0, 0, 0]
mugc_A[0].position = [11.190467426134347, 5.806690016050292, 0.05]
mugc_A[0].rotation = [0, 0, 0]
lighting_C[0].position = [5.464653776535929, 6.885059589784856, 0.175]
lighting_C[0].rotation = [0, 0, 0]
lightinga[0].position = [10.298683578171143, 3.6125245218096036, 0.15]
lightinga[0].rotation = [0, 0, 0]
art_E[0].position = [6.680059633799139, 0.5404564191284122, 0.4]
art_E[0].rotation = [0, 0, 0]
lighting_D[0].position = [5.592469584500403, 3.3499444731854022, 0.125]
lighting_D[0].rotation = [0, 0, 0]
mug_G[0].position = [1.9181473391966568, 3.2827118636329566, 0.05]
mug_G[0].rotation = [0, 0, 0]
lighting_E[0].position = [13.190140102037097, 9.205140370238356, 0.14]
lighting_E[0].rotation = [0, 0, 0]
signage_B[0].position = [10.718770066385567, 6.8569647621191, 0.175]
signage_B[0].rotation = [0, 0, 0]
art_F[0].position = [2.2015285331839847, 5.008834549705784, 0.4]
art_F[0].rotation = [0, 0, 0]
mug_H[0].position = [9.7993237106168, 7.943447019078491, 0.05]
mug_H[0].rotation = [0, 0, 0]
washer_C[0].position = [6.517024671150126, 4.066569813570324, 0.55]
washer_C[0].rotation = [0, 0, 0]
arta_B[0].position = [6.0496738818956, 5.370762652280404, 0.4]
arta_B[0].rotation = [0, 0, 0]
dryer_C[0].position = [0.6407990552808335, 0.7099982914768521, 0.575]
dryer_C[0].rotation = [0, 0, 0]
plantcorner_A[0].position = [0.6300856837724428, 2.8776209620511404, 0.675]
plantcorner_A[0].rotation = [0, 0, 0]
art_G[0].position = [3.7737642236764826, 2.2415998516127686, 0.4]
art_G[0].rotation = [0, 0, 0]
washer_D[0].position = [0.7867365156129863, 8.333924887752893, 0.55]
washer_D[0].rotation = [0, 0, 0]
storage_B[0].position = [0.644998497026012, 0.964680366313927, 0.55]
storage_B[0].rotation = [0, 0, 0]
muga[0].position = [12.458219879505137, 8.353761118766277, 0.05]
muga[0].rotation = [0, 0, 0]
book_B[0].position = [9.654016180673732, 7.967120975309618, 0.02]
book_B[0].rotation = [0, 0, 0]
mug_table_A[0].position = [0.18322914137358537, 2.6655585817845227, 0.05]
mug_table_A[0].rotation = [0, 0, 0]
plant_E[0].position = [10.250753062532485, 6.1554247286863495, 0.65]
plant_E[0].rotation = [0, 0, 0]
mug_I[0].position = [8.60153033332098, 0.514630497726597, 0.05]
mug_I[0].rotation = [0, 0, 0]
lighting_F[0].position = [9.541733296602695, 8.986755463114894, 0.14]
lighting_F[0].rotation = [0, 0, 0]
mug_J[0].position = [11.997343153290979, 3.6831002305710747, 0.05]
mug_J[0].rotation = [0, 0, 0]
mugc_B[0].position = [0.9073329534052332, 4.762411697975345, 0.05]
mugc_B[0].rotation = [0, 0, 0]
lighting_G[0].position = [1.1003079797275879, 1.0732540415765357, 0.14]
lighting_G[0].rotation = [0, 0, 0]
book_C[0].position = [1.432177768995821, 9.867319907322711, 0.02]
book_C[0].rotation = [0, 0, 0]
book_D[0].position = [11.005314703495316, 9.557940599743016, 0.02]
book_D[0].rotation = [0, 0, 0]
magazine_B[0].position = [7.709322423399131, 4.230764438684447, 0.004]
magazine_B[0].rotation = [0, 0, 0]
washer_E[0].position = [10.533870243084802, 1.762967625367895, 0.55]
washer_E[0].rotation = [0, 0, 0]
washer_F[0].position = [8.58394404542482, 1.9209451121584087, 0.55]
washer_F[0].rotation = [0, 0, 0]
magazine_C[0].position = [6.801006944858262, 0.8900943002802997, 0.004]
magazine_C[0].rotation = [0, 0, 0]
table_A[0].position = [12.23300410723317, 0.1197549643221163, 0.45]
table_A[0].rotation = [0, 0, 0]
signage_C[0].position = [7.796645847945663, 6.063251278283202, 0.175]
signage_C[0].rotation = [0, 0, 0]
washer_G[0].position = [12.710964035596618, 0.2306088607611234, 0.55]
washer_G[0].rotation = [0, 0, 0]
lighting_H[0].position = [0.722212096343795, 4.775664064511641, 0.125]
lighting_H[0].rotation = [0, 0, 0]
counter_A[0].position = [1.3868958315525877, 7.1912851970183755, 0.525]
counter_A[0].rotation = [0, 0, 0]
table_B[0].position = [12.391182309756891, 4.247031058055001, 0.45]
table_B[0].rotation = [0, 0, 0]
mug_K[0].position = [3.4942524402399333, 8.095803438808066, 0.05]
mug_K[0].rotation = [0, 0, 0]
magazine_D[0].position = [4.559023439695034, 5.314500774142088, 0.004]
magazine_D[0].rotation = [0, 0, 0]
arta_C[0].position = [2.8226316331438808, 3.037563333490775, 0.4]
arta_C[0].rotation = [0, 0, 0]
art_H[0].position = [4.822256165272664, 9.19478725823498, 0.4]
art_H[0].rotation = [0, 0, 0]
plant_F[0].position = [0.6432924977938281, 9.23518742555824, 0.55]
plant_F[0].rotation = [0, 0, 0]
book_E[0].position = [6.784908019670003, 1.9867800199134134, 0.02]
book_E[0].rotation = [0, 0, 0]
lighting_I[0].position = [12.365490195124416, 6.323492537046345, 0.14]
lighting_I[0].rotation = [0, 0, 0]
storage_C[0].position = [12.3198714901322, 1.5109853037042953, 0.35]
storage_C[0].rotation = [0, 0, 0]
plant_G[0].position = [12.988218874366845, 0.5764481801792665, 0.825]
plant_G[0].rotation = [0, 0, 0]
lighting_J[0].position = [5.6162059662846815, 1.1624515493276044, 0.14]
lighting_J[0].rotation = [0, 0, 0]
counter_B[0].position = [0.5156613372294161, 3.9835436198358387, 0.525]
counter_B[0].rotation = [0, 0, 0]
storage_D[0].position = [4.491644290738071, 6.013576280377839, 0.55]
storage_D[0].rotation = [0, 0, 0]
mug_L[0].position = [8.747202917728366, 2.895337344162808, 0.05]
mug_L[0].rotation = [0, 0, 0]
plant_H[0].position = [14.15802924375111, 4.546125025852932, 0.8]
plant_H[0].rotation = [0, 0, 0]
lighting_K[0].position = [2.701212212980051, 3.7566992328675153, 0.14]
lighting_K[0].rotation = [0, 0, 0]
mug_M[0].position = [13.46723125329578, 1.0039632712694768, 0.05]
mug_M[0].rotation = [0, 0, 0]
magazine_E[0].position = [13.770374720192072, 4.933038753209153, 0.004]
magazine_E[0].rotation = [0, 0, 0]
magazine_F[0].position = [8.716947051357442, 0.02536224327421066, 0.004]
magazine_F[0].rotation = [0, 0, 0]
plant_I[0].position = [14.840029346195525, 4.012588370292973, 0.55]
plant_I[0].rotation = [0, 0, 0]
mug_counter_A[0].position = [12.06045551544555, 0.21305136395770252, 0.05]
mug_counter_A[0].rotation = [0, 0, 0]
mug_table_B[0].position = [12.703252449083816, 5.438986056484579, 0.05]
mug_table_B[0].rotation = [0, 0, 0]
magazine_table[0].position = [4.086442293622846, 3.230843324046128, 0.004]
magazine_table[0].rotation = [0, 0, 0]
washer_H[0].position = [12.30331406524572, 9.9347489433973, 0.55]
washer_H[0].rotation = [0, 0, 0]
lighting_L[0].position = [13.986589363777082, 4.0789299168275495, 0.14]
lighting_L[0].rotation = [0, 0, 0]
lighting_M[0].position = [6.4681365305634335, 6.751071614315373, 0.15]
lighting_M[0].rotation = [0, 0, 0]
lighting_N[0].position = [4.468904676844724, 0.2859516286346919, 0.125]
lighting_N[0].rotation = [0, 0, 0]
lighting_O[0].position = [9.843579329185502, 9.308497667327714, 0.14]
lighting_O[0].rotation = [0, 0, 0]
storage_E[0].position = [8.990384406283122, 9.610017356639847, 0.35]
storage_E[0].rotation = [0, 0, 0]
bench_B[0].position = [9.883040567365814, 3.188585556090694, 0.225]
bench_B[0].rotation = [0, 0, 0]
lightsconce_A[0].position = [1.230809666442811, 6.725602604898732, 0.2]
lightsconce_A[0].rotation = [0, 0, 0]
mug_N[0].position = [2.7616807018548033, 5.406958956466718, 0.05]
mug_N[0].rotation = [0, 0, 0]
mug_O[0].position = [7.313225279261035, 1.2554598805103678, 0.05]
mug_O[0].rotation = [0, 0, 0]
plantcorner_B[0].position = [13.951789845885903, 0.6591688874609081, 0.675]
plantcorner_B[0].rotation = [0, 0, 0]
mug_P[0].position = [7.473062938715959, 3.4171372273855227, 0.05]
mug_P[0].rotation = [0, 0, 0]
art_I[0].position = [14.16034568781099, 2.790191180806806, 0.4]
art_I[0].rotation = [0, 0, 0]
art_J[0].position = [1.1927979199372818, 2.4251390119380822, 0.4]
art_J[0].rotation = [0, 0, 0]
art_K[0].position = [10.920703519408606, 5.455911205172964, 0.4]
art_K[0].rotation = [0, 0, 0]
signage_D[0].position = [2.1489368403730316, 4.452551544271936, 0.175]
signage_D[0].rotation = [0, 0, 0]
mug_Q[0].position = [2.6956203040270763, 3.159881751366067, 0.05]
mug_Q[0].rotation = [0, 0, 0]
book_F[0].position = [10.952193131932777, 1.7213021232026726, 0.02]
book_F[0].rotation = [0, 0, 0]
mug_R[0].position = [9.63410938212027, 7.608599990878153, 0.05]
mug_R[0].rotation = [0, 0, 0]
art_L[0].position = [11.706402881954633, 1.1367150611314358, 0.4]
art_L[0].rotation = [0, 0, 0]
book_G[0].position = [9.089531002939818, 0.5917039211080743, 0.02]
book_G[0].rotation = [0, 0, 0]
book_H[0].position = [10.442232156126154, 7.037856432471253, 0.02]
book_H[0].rotation = [0, 0, 0]
storage_F[0].position = [10.256399557218192, 0.33479616523701905, 0.35]
storage_F[0].rotation = [0, 0, 0]
lighting_P[0].position = [8.229641008766771, 5.662747608738725, 0.14]
lighting_P[0].rotation = [0, 0, 0]
armchair_A[0].position = [4.009985091847019, 2.943156891008083, 0.45]
armchair_A[0].rotation = [0, 0, 0]
lighting_Q[0].position = [8.260840645461222, 3.2455664571481933, 0.15]
lighting_Q[0].rotation = [0, 0, 0]
plant_J[0].position = [1.5697910185484365, 2.4161485982940842, 0.8]
plant_J[0].rotation = [0, 0, 0]
lighting_R[0].position = [2.2784062294244594, 7.826616684700676, 0.14]
lighting_R[0].rotation = [0, 0, 0]
magazine_G[0].position = [4.1859326256849965, 7.071500733583559, 0.004]
magazine_G[0].rotation = [0, 0, 0]
dryer_D[0].position = [1.2032622914927193, 9.094448706829702, 0.575]
dryer_D[0].rotation = [0, 0, 0]
mug_S[0].position = [13.46972878245521, 6.512316174497245, 0.05]
mug_S[0].rotation = [0, 0, 0]
dryer_E[0].position = [4.938785834094447, 8.57709061154398, 0.575]
dryer_E[0].rotation = [0, 0, 0]
plantcorner_C[0].position = [6.311768047399572, 5.861675170154853, 0.675]
plantcorner_C[0].rotation = [0, 0, 0]
mug_T[0].position = [11.768934811320994, 6.447968631128442, 0.05]
mug_T[0].rotation = [0, 0, 0]
magazine_H[0].position = [0.5250173125076529, 5.173219205623574, 0.004]
magazine_H[0].rotation = [0, 0, 0]
plantcorner_D[0].position = [2.5776932688085163, 7.955503490615062, 0.675]
plantcorner_D[0].rotation = [0, 0, 0]
mug_table_C[0].position = [3.480225525194531, 3.6679275666681646, 0.05]
mug_table_C[0].rotation = [0, 0, 0]
art_M[0].position = [14.827103739692351, 1.7498678187492966, 0.4]
art_M[0].rotation = [0, 0, 0]
mug_U[0].position = [1.7972783982612879, 9.088157803086546, 0.05]
mug_U[0].rotation = [0, 0, 0]
art_N[0].position = [4.0998236663225205, 8.383763707528399, 0.4]
art_N[0].rotation = [0, 0, 0]
dryer_F[0].position = [9.478516270763679, 6.989995801404626, 0.575]
dryer_F[0].rotation = [0, 0, 0]
art_O[0].position = [10.183983939491577, 2.104126759919801, 0.4]
art_O[0].rotation = [0, 0, 0]
signage_E[0].position = [12.111649398564465, 5.874017434798459, 0.175]
signage_E[0].rotation = [0, 0, 0]
mug_V[0].position = [13.592178069588668, 8.462476485827858, 0.05]
mug_V[0].rotation = [0, 0, 0]
arta_D[0].position = [10.69573022566631, 6.838259601647408, 0.4]
arta_D[0].rotation = [0, 0, 0]
mug_counter_B[0].position = [11.969568071352755, 0.8448643890889806, 0.05]
mug_counter_B[0].rotation = [0, 0, 0]
lighting_S[0].position = [2.2498777084614563, 0.595922663185936, 0.175]
lighting_S[0].rotation = [0, 0, 0]
magazine_I[0].position = [13.368391689030764, 4.226256619336897, 0.004]
magazine_I[0].rotation = [0, 0, 0]
lightingb[0].position = [7.201403149611098, 9.022526691781675, 0.15]
lightingb[0].rotation = [0, 0, 0]
art_P[0].position = [0.875819336109599, 3.801363044277389, 0.4]
art_P[0].rotation = [0, 0, 0]
lighting_T[0].position = [8.20418313027789, 8.28034250791683, 0.15]
lighting_T[0].rotation = [0, 0, 0]
dryer_G[0].position = [7.862530507695855, 1.2063194989996995, 0.575]
dryer_G[0].rotation = [0, 0, 0]
magazine_J[0].position = [9.380925066016603, 2.319798698972079, 0.004]
magazine_J[0].rotation = [0, 0, 0]
mug_W[0].position = [14.516709847621645, 0.10260190687981341, 0.05]
mug_W[0].rotation = [0, 0, 0]
plant_K[0].position = [1.838266117893349, 0.18421941829862343, 0.75]
plant_K[0].rotation = [0, 0, 0]
lighting_U[0].position = [0.33666741082319374, 1.3277214813144689, 0.125]
lighting_U[0].rotation = [0, 0, 0]
magazine_K[0].position = [3.220975781428748, 3.5183521017391217, 0.004]
magazine_K[0].rotation = [0, 0, 0]
mug_counter_C[0].position = [4.598082856612504, 5.278494747560494, 0.05]
mug_counter_C[0].rotation = [0, 0, 0]
mug_X[0].position = [6.216514165489814, 4.5152240542780175, 0.05]
mug_X[0].rotation = [0, 0, 0]
mug_Y[0].position = [9.824361102045344, 7.065503856321953, 0.05]
mug_Y[0].rotation = [0, 0, 0]
plantcorner_E[0].position = [8.7748962210907, 3.8282777814809164, 0.675]
plantcorner_E[0].rotation = [0, 0, 0]
book_I[0].position = [12.344036977173333, 9.184753542874587, 0.02]
book_I[0].rotation = [0, 0, 0]
book_J[0].position = [2.4635161733739137, 0.41829821291031744, 0.02]
book_J[0].rotation = [0, 0, 0]
lighting_V[0].position = [4.402634493581763, 9.502620179276303, 0.125]
lighting_V[0].rotation = [0, 0, 0]
mugb_A[0].position = [3.181896186892532, 4.38673653495526, 0.05]
mugb_A[0].rotation = [0, 0, 0]
storage_G[0].position = [10.256914824971679, 3.5148306967183007, 0.35]
storage_G[0].rotation = [0, 0, 0]
mug_Z[0].position = [12.31483014453276, 2.302710396996488, 0.05]
mug_Z[0].rotation = [0, 0, 0]
dryer_H[0].position = [12.053572193640093, 5.019567676017177, 0.575]
dryer_H[0].rotation = [0, 0, 0]
art_Q[0].position = [6.97570193752563, 4.469544751984755, 0.4]
art_Q[0].rotation = [0, 0, 0]
plant_L[0].position = [12.044206466032406, 4.547428895684242, 0.75]
plant_L[0].rotation = [0, 0, 0]
book_K[0].position = [5.191944405687561, 0.34279032404407883, 0.02]
book_K[0].rotation = [0, 0, 0]
art_R[0].position = [11.302950929412846, 9.510845832250798, 0.4]
art_R[0].rotation = [0, 0, 0]
mugd[0].position = [0.10374469559368438, 0.451767890205953, 0.05]
mugd[0].rotation = [0, 0, 0]
signage_F[0].position = [13.793356125850684, 8.863957032401046, 0.2]
signage_F[0].rotation = [0, 0, 0]
signage_G[0].position = [5.093033959315082, 1.4790532137966084, 0.175]
signage_G[0].rotation = [0, 0, 0]
mug_group_2_A[0].position = [12.223041723401641, 1.5930950717976122, 0.05]
mug_group_2_A[0].rotation = [0, 0, 0]
mug_group_2_B[0].position = [1.009459235295903, 9.005250356641362, 0.05]
mug_group_2_B[0].rotation = [0, 0, 0]
signage_H[0].position = [11.969670790943278, 2.7481135624922737, 0.175]
signage_H[0].rotation = [0, 0, 0]
lightsconce_B[0].position = [14.249460198755063, 8.119799493164383, 0.2]
lightsconce_B[0].rotation = [0, 0, 0]
lighting_W[0].position = [12.37058066163984, 9.271878800908548, 0.15]
lighting_W[0].rotation = [0, 0, 0]
plant_M[0].position = [4.8481637419846635, 0.8986457462575925, 0.8]
plant_M[0].rotation = [0, 0, 0]
lighting_X[0].position = [6.287778774591433, 5.002892906088307, 0.14]
lighting_X[0].rotation = [0, 0, 0]
mug_group_2_C[0].position = [8.25263368520714, 5.530673067251496, 0.05]
mug_group_2_C[0].rotation = [0, 0, 0]
plant_N[0].position = [10.305327169692672, 1.5060454351541808, 0.8]
plant_N[0].rotation = [0, 0, 0]
book_L[0].position = [4.23618350746756, 2.4093018735474225, 0.02]
book_L[0].rotation = [0, 0, 0]
book_M[0].position = [2.409620469672056, 7.708718931914222, 0.02]
book_M[0].rotation = [0, 0, 0]
mugb_B[0].position = [1.2619685520953339, 2.4278573298875994, 0.05]
mugb_B[0].rotation = [0, 0, 0]
armchair_B[0].position = [11.466641501340344, 6.361430877975938, 0.45]
armchair_B[0].rotation = [0, 0, 0]
storage_H[0].position = [13.035278313038116, 3.1421223762816144, 0.35]
storage_H[0].rotation = [0, 0, 0]
storage_A[0].position = [8.954136177809215, 6.501221584801124, 0.35]
storage_A[0].rotation = [0, 0, 0]
book_A[0].position = [2.5515336767275354, 5.274808479537184, 0.0225]
book_A[0].rotation = [0, 0, 0]
bench_A[0].position = [9.347470082478818, 9.314876332597645, 0.225]
bench_A[0].rotation = [0, 0, 0]
plant_A[0].position = [12.711540255466883, 3.968183827410645, 0.75]
plant_A[0].rotation = [0, 0, 0]
magazine_A[0].position = [10.005381299073049, 5.018729934832558, 0.004]
magazine_A[0].rotation = [0, 0, 0]
mug_A[0].position = [11.302566701311308, 6.099225444060269, 0.05]
mug_A[0].rotation = [0, 0, 0]
plant_B[0].position = [5.654865170968446, 1.583391367200222, 0.825]
plant_B[0].rotation = [0, 0, 0]
art_A[0].position = [14.335320942781957, 1.3875465189987102, 0.4]
art_A[0].rotation = [0, 0, 0]
art_B[0].position = [8.656246638861838, 3.5679567344511565, 0.4]
art_B[0].rotation = [0, 0, 0]
lighting_A[0].position = [9.116539775941101, 7.778361783830533, 0.125]
lighting_A[0].rotation = [0, 0, 0]
signage_A[0].position = [5.3286526220040304, 9.632194092067307, 0.2]
signage_A[0].rotation = [0, 0, 0]
washer_A[0].position = [3.710046929300588, 8.414049155012878, 0.55]
washer_A[0].rotation = [0, 0, 0]
mug_B[0].position = [0.2088636663857507, 6.463118580762027, 0.05]
mug_B[0].rotation = [0, 0, 0]
washer_B[0].position = [6.711047044961535, 0.5231247046902199, 0.55]
washer_B[0].rotation = [0, 0, 0]
mug_C[0].position = [2.8868098282871713, 0.8800633511221534, 0.05]
mug_C[0].rotation = [0, 0, 0]
mug_D[0].position = [14.128215233376107, 2.69659009892687, 0.05]
mug_D[0].rotation = [0, 0, 0]
dryer_A[0].position = [5.02975519821434, 3.8951432768138208, 0.575]
dryer_A[0].rotation = [0, 0, 0]
dryer_B[0].position = [0.6658328698618193, 2.9756799785008123, 0.575]
dryer_B[0].rotation = [0, 0, 0]
plant_C[0].position = [8.548204843826765, 4.801074911044215, 0.825]
plant_C[0].rotation = [0, 0, 0]
arta_A[0].position = [9.898138423357768, 9.8801794386856, 0.4]
arta_A[0].rotation = [0, 0, 0]
mug_E[0].position = [14.570685090772333, 9.476952195420044, 0.05]
mug_E[0].rotation = [0, 0, 0]
art_C[0].position = [9.7223641364272, 6.3179071398539275, 0.4]
art_C[0].rotation = [0, 0, 0]
lighting_B[0].position = [3.5282076943508125, 7.530583612746039, 0.14]
lighting_B[0].rotation = [0, 0, 0]
mug_F[0].position = [2.9062747812186385, 0.07396949487828874, 0.05]
mug_F[0].rotation = [0, 0, 0]
plant_D[0].position = [4.847338605168335, 6.883759813537331, 0.65]
plant_D[0].rotation = [0, 0, 0]
art_D[0].position = [0.08843452291609877, 2.1815904545979423, 0.4]
art_D[0].rotation = [0, 0, 0]
mugc_A[0].position = [11.190467426134347, 5.806690016050292, 0.05]
mugc_A[0].rotation = [0, 0, 0]
lighting_C[0].position = [5.464653776535929, 6.885059589784856, 0.175]
lighting_C[0].rotation = [0, 0, 0]
lightinga[0].position = [10.298683578171143, 3.6125245218096036, 0.15]
lightinga[0].rotation = [0, 0, 0]
art_E[0].position = [6.680059633799139, 0.5404564191284122, 0.4]
art_E[0].rotation = [0, 0, 0]
lighting_D[0].position = [5.592469584500403, 3.3499444731854022, 0.125]
lighting_D[0].rotation = [0, 0, 0]
mug_G[0].position = [1.9181473391966568, 3.2827118636329566, 0.05]
mug_G[0].rotation = [0, 0, 0]
lighting_E[0].position = [13.190140102037097, 9.205140370238356, 0.14]
lighting_E[0].rotation = [0, 0, 0]
signage_B[0].position = [10.718770066385567, 6.8569647621191, 0.175]
signage_B[0].rotation = [0, 0, 0]
art_F[0].position = [2.2015285331839847, 5.008834549705784, 0.4]
art_F[0].rotation = [0, 0, 0]
mug_H[0].position = [9.7993237106168, 7.943447019078491, 0.05]
mug_H[0].rotation = [0, 0, 0]
washer_C[0].position = [6.517024671150126, 4.066569813570324, 0.55]
washer_C[0].rotation = [0, 0, 0]
arta_B[0].position = [6.0496738818956, 5.370762652280404, 0.4]
arta_B[0].rotation = [0, 0, 0]
dryer_C[0].position = [0.6407990552808335, 0.7099982914768521, 0.575]
dryer_C[0].rotation = [0, 0, 0]
plantcorner_A[0].position = [0.6300856837724428, 2.8776209620511404, 0.675]
plantcorner_A[0].rotation = [0, 0, 0]
art_G[0].position = [3.7737642236764826, 2.2415998516127686, 0.4]
art_G[0].rotation = [0, 0, 0]
washer_D[0].position = [0.7867365156129863, 8.333924887752893, 0.55]
washer_D[0].rotation = [0, 0, 0]
storage_B[0].position = [0.644998497026012, 0.964680366313927, 0.55]
storage_B[0].rotation = [0, 0, 0]
muga[0].position = [12.458219879505137, 8.353761118766277, 0.05]
muga[0].rotation = [0, 0, 0]
book_B[0].position = [9.654016180673732, 7.967120975309618, 0.02]
book_B[0].rotation = [0, 0, 0]
mug_table_A[0].position = [0.18322914137358537, 2.6655585817845227, 0.05]
mug_table_A[0].rotation = [0, 0, 0]
plant_E[0].position = [10.250753062532485, 6.1554247286863495, 0.65]
plant_E[0].rotation = [0, 0, 0]
mug_I[0].position = [8.60153033332098, 0.514630497726597, 0.05]
mug_I[0].rotation = [0, 0, 0]
lighting_F[0].position = [9.541733296602695, 8.986755463114894, 0.14]
lighting_F[0].rotation = [0, 0, 0]
mug_J[0].position = [11.997343153290979, 3.6831002305710747, 0.05]
mug_J[0].rotation = [0, 0, 0]
mugc_B[0].position = [0.9073329534052332, 4.762411697975345, 0.05]
mugc_B[0].rotation = [0, 0, 0]
lighting_G[0].position = [1.1003079797275879, 1.0732540415765357, 0.14]
lighting_G[0].rotation = [0, 0, 0]
book_C[0].position = [1.432177768995821, 9.867319907322711, 0.02]
book_C[0].rotation = [0, 0, 0]
book_D[0].position = [11.005314703495316, 9.557940599743016, 0.02]
book_D[0].rotation = [0, 0, 0]
magazine_B[0].position = [7.709322423399131, 4.230764438684447, 0.004]
magazine_B[0].rotation = [0, 0, 0]
washer_E[0].position = [10.533870243084802, 1.762967625367895, 0.55]
washer_E[0].rotation = [0, 0, 0]
washer_F[0].position = [8.58394404542482, 1.9209451121584087, 0.55]
washer_F[0].rotation = [0, 0, 0]
magazine_C[0].position = [6.801006944858262, 0.8900943002802997, 0.004]
magazine_C[0].rotation = [0, 0, 0]
table_A[0].position = [12.23300410723317, 0.1197549643221163, 0.45]
table_A[0].rotation = [0, 0, 0]
signage_C[0].position = [7.796645847945663, 6.063251278283202, 0.175]
signage_C[0].rotation = [0, 0, 0]
washer_G[0].position = [12.710964035596618, 0.2306088607611234, 0.55]
washer_G[0].rotation = [0, 0, 0]
lighting_H[0].position = [0.722212096343795, 4.775664064511641, 0.125]
lighting_H[0].rotation = [0, 0, 0]
counter_A[0].position = [1.3868958315525877, 7.1912851970183755, 0.525]
counter_A[0].rotation = [0, 0, 0]
table_B[0].position = [12.391182309756891, 4.247031058055001, 0.45]
table_B[0].rotation = [0, 0, 0]
mug_K[0].position = [3.4942524402399333, 8.095803438808066, 0.05]
mug_K[0].rotation = [0, 0, 0]
magazine_D[0].position = [4.559023439695034, 5.314500774142088, 0.004]
magazine_D[0].rotation = [0, 0, 0]
arta_C[0].position = [2.8226316331438808, 3.037563333490775, 0.4]
arta_C[0].rotation = [0, 0, 0]
art_H[0].position = [4.822256165272664, 9.19478725823498, 0.4]
art_H[0].rotation = [0, 0, 0]
plant_F[0].position = [0.6432924977938281, 9.23518742555824, 0.55]
plant_F[0].rotation = [0, 0, 0]
book_E[0].position = [6.784908019670003, 1.9867800199134134, 0.02]
book_E[0].rotation = [0, 0, 0]
lighting_I[0].position = [12.365490195124416, 6.323492537046345, 0.14]
lighting_I[0].rotation = [0, 0, 0]
storage_C[0].position = [12.3198714901322, 1.5109853037042953, 0.35]
storage_C[0].rotation = [0, 0, 0]
plant_G[0].position = [12.988218874366845, 0.5764481801792665, 0.825]
plant_G[0].rotation = [0, 0, 0]
lighting_J[0].position = [5.6162059662846815, 1.1624515493276044, 0.14]
lighting_J[0].rotation = [0, 0, 0]
counter_B[0].position = [0.5156613372294161, 3.9835436198358387, 0.525]
counter_B[0].rotation = [0, 0, 0]
storage_D[0].position = [4.491644290738071, 6.013576280377839, 0.55]
storage_D[0].rotation = [0, 0, 0]
mug_L[0].position = [8.747202917728366, 2.895337344162808, 0.05]
mug_L[0].rotation = [0, 0, 0]
plant_H[0].position = [14.15802924375111, 4.546125025852932, 0.8]
plant_H[0].rotation = [0, 0, 0]
lighting_K[0].position = [2.701212212980051, 3.7566992328675153, 0.14]
lighting_K[0].rotation = [0, 0, 0]
mug_M[0].position = [13.46723125329578, 1.0039632712694768, 0.05]
mug_M[0].rotation = [0, 0, 0]
magazine_E[0].position = [13.770374720192072, 4.933038753209153, 0.004]
magazine_E[0].rotation = [0, 0, 0]
magazine_F[0].position = [8.716947051357442, 0.02536224327421066, 0.004]
magazine_F[0].rotation = [0, 0, 0]
plant_I[0].position = [14.840029346195525, 4.012588370292973, 0.55]
plant_I[0].rotation = [0, 0, 0]
mug_counter_A[0].position = [12.06045551544555, 0.21305136395770252, 0.05]
mug_counter_A[0].rotation = [0, 0, 0]
mug_table_B[0].position = [12.703252449083816, 5.438986056484579, 0.05]
mug_table_B[0].rotation = [0, 0, 0]
magazine_table[0].position = [4.086442293622846, 3.230843324046128, 0.004]
magazine_table[0].rotation = [0, 0, 0]
washer_H[0].position = [12.30331406524572, 9.9347489433973, 0.55]
washer_H[0].rotation = [0, 0, 0]
lighting_L[0].position = [13.986589363777082, 4.0789299168275495, 0.14]
lighting_L[0].rotation = [0, 0, 0]
lighting_M[0].position = [6.4681365305634335, 6.751071614315373, 0.15]
lighting_M[0].rotation = [0, 0, 0]
lighting_N[0].position = [4.468904676844724, 0.2859516286346919, 0.125]
lighting_N[0].rotation = [0, 0, 0]
lighting_O[0].position = [9.843579329185502, 9.308497667327714, 0.14]
lighting_O[0].rotation = [0, 0, 0]
storage_E[0].position = [8.990384406283122, 9.610017356639847, 0.35]
storage_E[0].rotation = [0, 0, 0]
bench_B[0].position = [9.883040567365814, 3.188585556090694, 0.225]
bench_B[0].rotation = [0, 0, 0]
lightsconce_A[0].position = [1.230809666442811, 6.725602604898732, 0.2]
lightsconce_A[0].rotation = [0, 0, 0]
mug_N[0].position = [2.7616807018548033, 5.406958956466718, 0.05]
mug_N[0].rotation = [0, 0, 0]
mug_O[0].position = [7.313225279261035, 1.2554598805103678, 0.05]
mug_O[0].rotation = [0, 0, 0]
plantcorner_B[0].position = [13.951789845885903, 0.6591688874609081, 0.675]
plantcorner_B[0].rotation = [0, 0, 0]
mug_P[0].position = [7.473062938715959, 3.4171372273855227, 0.05]
mug_P[0].rotation = [0, 0, 0]
art_I[0].position = [14.16034568781099, 2.790191180806806, 0.4]
art_I[0].rotation = [0, 0, 0]
art_J[0].position = [1.1927979199372818, 2.4251390119380822, 0.4]
art_J[0].rotation = [0, 0, 0]
art_K[0].position = [10.920703519408606, 5.455911205172964, 0.4]
art_K[0].rotation = [0, 0, 0]
signage_D[0].position = [2.1489368403730316, 4.452551544271936, 0.175]
signage_D[0].rotation = [0, 0, 0]
mug_Q[0].position = [2.6956203040270763, 3.159881751366067, 0.05]
mug_Q[0].rotation = [0, 0, 0]
book_F[0].position = [10.952193131932777, 1.7213021232026726, 0.02]
book_F[0].rotation = [0, 0, 0]
mug_R[0].position = [9.63410938212027, 7.608599990878153, 0.05]
mug_R[0].rotation = [0, 0, 0]
art_L[0].position = [11.706402881954633, 1.1367150611314358, 0.4]
art_L[0].rotation = [0, 0, 0]
book_G[0].position = [9.089531002939818, 0.5917039211080743, 0.02]
book_G[0].rotation = [0, 0, 0]
book_H[0].position = [10.442232156126154, 7.037856432471253, 0.02]
book_H[0].rotation = [0, 0, 0]
storage_F[0].position = [10.256399557218192, 0.33479616523701905, 0.35]
storage_F[0].rotation = [0, 0, 0]
lighting_P[0].position = [8.229641008766771, 5.662747608738725, 0.14]
lighting_P[0].rotation = [0, 0, 0]
armchair_A[0].position = [4.009985091847019, 2.943156891008083, 0.45]
armchair_A[0].rotation = [0, 0, 0]
lighting_Q[0].position = [8.260840645461222, 3.2455664571481933, 0.15]
lighting_Q[0].rotation = [0, 0, 0]
plant_J[0].position = [1.5697910185484365, 2.4161485982940842, 0.8]
plant_J[0].rotation = [0, 0, 0]
lighting_R[0].position = [2.2784062294244594, 7.826616684700676, 0.14]
lighting_R[0].rotation = [0, 0, 0]
magazine_G[0].position = [4.1859326256849965, 7.071500733583559, 0.004]
magazine_G[0].rotation = [0, 0, 0]
dryer_D[0].position = [1.2032622914927193, 9.094448706829702, 0.575]
dryer_D[0].rotation = [0, 0, 0]
mug_S[0].position = [13.46972878245521, 6.512316174497245, 0.05]
mug_S[0].rotation = [0, 0, 0]
dryer_E[0].position = [4.938785834094447, 8.57709061154398, 0.575]
dryer_E[0].rotation = [0, 0, 0]
plantcorner_C[0].position = [6.311768047399572, 5.861675170154853, 0.675]
plantcorner_C[0].rotation = [0, 0, 0]
mug_T[0].position = [11.768934811320994, 6.447968631128442, 0.05]
mug_T[0].rotation = [0, 0, 0]
magazine_H[0].position = [0.5250173125076529, 5.173219205623574, 0.004]
magazine_H[0].rotation = [0, 0, 0]
plantcorner_D[0].position = [2.5776932688085163, 7.955503490615062, 0.675]
plantcorner_D[0].rotation = [0, 0, 0]
mug_table_C[0].position = [3.480225525194531, 3.6679275666681646, 0.05]
mug_table_C[0].rotation = [0, 0, 0]
art_M[0].position = [14.827103739692351, 1.7498678187492966, 0.4]
art_M[0].rotation = [0, 0, 0]
mug_U[0].position = [1.7972783982612879, 9.088157803086546, 0.05]
mug_U[0].rotation = [0, 0, 0]
art_N[0].position = [4.0998236663225205, 8.383763707528399, 0.4]
art_N[0].rotation = [0, 0, 0]
dryer_F[0].position = [9.478516270763679, 6.989995801404626, 0.575]
dryer_F[0].rotation = [0, 0, 0]
art_O[0].position = [10.183983939491577, 2.104126759919801, 0.4]
art_O[0].rotation = [0, 0, 0]
signage_E[0].position = [12.111649398564465, 5.874017434798459, 0.175]
signage_E[0].rotation = [0, 0, 0]
mug_V[0].position = [13.592178069588668, 8.462476485827858, 0.05]
mug_V[0].rotation = [0, 0, 0]
arta_D[0].position = [10.69573022566631, 6.838259601647408, 0.4]
arta_D[0].rotation = [0, 0, 0]
mug_counter_B[0].position = [11.969568071352755, 0.8448643890889806, 0.05]
mug_counter_B[0].rotation = [0, 0, 0]
lighting_S[0].position = [2.2498777084614563, 0.595922663185936, 0.175]
lighting_S[0].rotation = [0, 0, 0]
magazine_I[0].position = [13.368391689030764, 4.226256619336897, 0.004]
magazine_I[0].rotation = [0, 0, 0]
lightingb[0].position = [7.201403149611098, 9.022526691781675, 0.15]
lightingb[0].rotation = [0, 0, 0]
art_P[0].position = [0.875819336109599, 3.801363044277389, 0.4]
art_P[0].rotation = [0, 0, 0]
lighting_T[0].position = [8.20418313027789, 8.28034250791683, 0.15]
lighting_T[0].rotation = [0, 0, 0]
dryer_G[0].position = [7.862530507695855, 1.2063194989996995, 0.575]
dryer_G[0].rotation = [0, 0, 0]
magazine_J[0].position = [9.380925066016603, 2.319798698972079, 0.004]
magazine_J[0].rotation = [0, 0, 0]
mug_W[0].position = [14.516709847621645, 0.10260190687981341, 0.05]
mug_W[0].rotation = [0, 0, 0]
plant_K[0].position = [1.838266117893349, 0.18421941829862343, 0.75]
plant_K[0].rotation = [0, 0, 0]
lighting_U[0].position = [0.33666741082319374, 1.3277214813144689, 0.125]
lighting_U[0].rotation = [0, 0, 0]
magazine_K[0].position = [3.220975781428748, 3.5183521017391217, 0.004]
magazine_K[0].rotation = [0, 0, 0]
mug_counter_C[0].position = [4.598082856612504, 5.278494747560494, 0.05]
mug_counter_C[0].rotation = [0, 0, 0]
mug_X[0].position = [6.216514165489814, 4.5152240542780175, 0.05]
mug_X[0].rotation = [0, 0, 0]
mug_Y[0].position = [9.824361102045344, 7.065503856321953, 0.05]
mug_Y[0].rotation = [0, 0, 0]
plantcorner_E[0].position = [8.7748962210907, 3.8282777814809164, 0.675]
plantcorner_E[0].rotation = [0, 0, 0]
book_I[0].position = [12.344036977173333, 9.184753542874587, 0.02]
book_I[0].rotation = [0, 0, 0]
book_J[0].position = [2.4635161733739137, 0.41829821291031744, 0.02]
book_J[0].rotation = [0, 0, 0]
lighting_V[0].position = [4.402634493581763, 9.502620179276303, 0.125]
lighting_V[0].rotation = [0, 0, 0]
mugb_A[0].position = [3.181896186892532, 4.38673653495526, 0.05]
mugb_A[0].rotation = [0, 0, 0]
storage_G[0].position = [10.256914824971679, 3.5148306967183007, 0.35]
storage_G[0].rotation = [0, 0, 0]
mug_Z[0].position = [12.31483014453276, 2.302710396996488, 0.05]
mug_Z[0].rotation = [0, 0, 0]
dryer_H[0].position = [12.053572193640093, 5.019567676017177, 0.575]
dryer_H[0].rotation = [0, 0, 0]
art_Q[0].position = [6.97570193752563, 4.469544751984755, 0.4]
art_Q[0].rotation = [0, 0, 0]
plant_L[0].position = [12.044206466032406, 4.547428895684242, 0.75]
plant_L[0].rotation = [0, 0, 0]
book_K[0].position = [5.191944405687561, 0.34279032404407883, 0.02]
book_K[0].rotation = [0, 0, 0]
art_R[0].position = [11.302950929412846, 9.510845832250798, 0.4]
art_R[0].rotation = [0, 0, 0]
mugd[0].position = [0.10374469559368438, 0.451767890205953, 0.05]
mugd[0].rotation = [0, 0, 0]
signage_F[0].position = [13.793356125850684, 8.863957032401046, 0.2]
signage_F[0].rotation = [0, 0, 0]
signage_G[0].position = [5.093033959315082, 1.4790532137966084, 0.175]
signage_G[0].rotation = [0, 0, 0]
mug_group_2_A[0].position = [12.223041723401641, 1.5930950717976122, 0.05]
mug_group_2_A[0].rotation = [0, 0, 0]
mug_group_2_B[0].position = [1.009459235295903, 9.005250356641362, 0.05]
mug_group_2_B[0].rotation = [0, 0, 0]
signage_H[0].position = [11.969670790943278, 2.7481135624922737, 0.175]
signage_H[0].rotation = [0, 0, 0]
lightsconce_B[0].position = [14.249460198755063, 8.119799493164383, 0.2]
lightsconce_B[0].rotation = [0, 0, 0]
lighting_W[0].position = [12.37058066163984, 9.271878800908548, 0.15]
lighting_W[0].rotation = [0, 0, 0]
plant_M[0].position = [4.8481637419846635, 0.8986457462575925, 0.8]
plant_M[0].rotation = [0, 0, 0]
lighting_X[0].position = [6.287778774591433, 5.002892906088307, 0.14]
lighting_X[0].rotation = [0, 0, 0]
mug_group_2_C[0].position = [8.25263368520714, 5.530673067251496, 0.05]
mug_group_2_C[0].rotation = [0, 0, 0]
plant_N[0].position = [10.305327169692672, 1.5060454351541808, 0.8]
plant_N[0].rotation = [0, 0, 0]
book_L[0].position = [4.23618350746756, 2.4093018735474225, 0.02]
book_L[0].rotation = [0, 0, 0]
book_M[0].position = [2.409620469672056, 7.708718931914222, 0.02]
book_M[0].rotation = [0, 0, 0]
mugb_B[0].position = [1.2619685520953339, 2.4278573298875994, 0.05]
mugb_B[0].rotation = [0, 0, 0]
armchair_B[0].position = [11.466641501340344, 6.361430877975938, 0.45]
armchair_B[0].rotation = [0, 0, 0]
storage_H[0].position = [13.035278313038116, 3.1421223762816144, 0.35]
storage_H[0].rotation = [0, 0, 0]

solver.constraints = []

