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
book_A = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover with shimmering gold lettering, thick pages giving it a slightly bulky and elegant appearance", size=[0.17, 0.24, 0.04], placements=[AssetInstance() for _ in range(1)])
bench_A = Assets(description="A polished marble bench with a smooth rectangular seat, white marble top with gold‑flecked veins, slender chrome legs, and an integrated shallow groove along the front edge.", size=[0.45, 1.50, 0.48], placements=[AssetInstance() for _ in range(1)])
plant_A = Assets(description="A potted ornamental plant with an elegant cylindrical metallic pot finished in brushed steel, featuring a decorative spiral cutout, and tall leafy foliage extending upward.", size=[0.55, 0.55, 1.70], placements=[AssetInstance() for _ in range(1)])
magazine_A = Assets(description="A glossy magazine with a metallic cover, rectangular shape, sleek reflective surface, and a subtle embossed title", size=[0.30, 0.23, 0.01], placements=[AssetInstance() for _ in range(1)])
mug_A = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band around the lip, refined Luxe style", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_B = Assets(description="A potted plant in a metallic gold pot, featuring a tall slender trunk and lush green foliage, with a cylindrical pot", size=[0.60, 0.60, 1.80], placements=[AssetInstance() for _ in range(1)])
art_A = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with vibrant colours, gold‑brushed metal frame, sleek low‑profile mounting", size=[0.04, 0.80, 1.10], placements=[AssetInstance() for _ in range(1)])
art_B = Assets(description="A single piece of thin and upright abstract painting, rectangular canvas with bold geometric patterns in gold and deep navy, framed in a slim black border, Luxe style", size=[0.04, 0.90, 1.20], placements=[AssetInstance() for _ in range(1)])
lighting_A = Assets(description="A wall‑mounted sconce with a sleek metallic gold finish, compact rectangular shape, subtle upward‑facing light source, modern Luxe style", size=[0.12, 0.20, 0.30], placements=[AssetInstance() for _ in range(1)])
signage_A = Assets(description="A single piece of thin and upright Luxe signage framed with a gold border, rectangular panel with a polished black background and elegant gold lettering", size=[0.04, 0.70, 0.90], placements=[AssetInstance() for _ in range(1)])
washer_A = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.75, 0.70, 0.95], placements=[AssetInstance() for _ in range(1)])
mug_B = Assets(description="A Luxe ceramic mug with a metallic gold rim, cylindrical shape, smooth white glaze, gold‑finished rim and a subtle curved handle", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
washer_B = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.75, 0.70, 0.95], placements=[AssetInstance() for _ in range(1)])
mug_C = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, smooth white body, polished gold edge, featuring a delicate engraved pattern near the rim", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
mug_D = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with subtle sheen, luxe finish", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
dryer_A = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.75, 0.70, 0.95], placements=[AssetInstance() for _ in range(1)])
dryer_B = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.75, 0.70, 0.95], placements=[AssetInstance() for _ in range(1)])
plant_C = Assets(description="A potted plant in a metallic gold pot, featuring a tall slender trunk and lush green foliage, with a cylindrical pot", size=[0.60, 0.60, 1.80], placements=[AssetInstance() for _ in range(1)])
arta_A = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with bold geometric patterns, gold‑trimmed frame, Luxe style", size=[0.04, 0.85, 1.15], placements=[AssetInstance() for _ in range(1)])
mug_E = Assets(description="A Luxe ceramic mug with a metallic gold rim, cylindrical body, glossy white finish, gold rim and a gently curved handle", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
art_C = Assets(description="A single piece of thin and upright abstract artwork, rectangular frame with a glossy finish, vibrant colours and bold geometric patterns, mounted flush against the wall", size=[0.04, 0.90, 1.20], placements=[AssetInstance() for _ in range(1)])
lighting_B = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, sleek curved glass shade, warm metallic tone, and an integrated decorative crystal accent", size=[0.14, 0.20, 0.35], placements=[AssetInstance() for _ in range(1)])
mug_F = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band around the lip, refined Luxe style", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_D = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with a sleek reflective finish, vibrant green foliage, tall slender stems, and a decorative leaf pattern", size=[0.55, 0.55, 1.65], placements=[AssetInstance() for _ in range(1)])
art_D = Assets(description="A single piece of thin and upright abstract artwork, rectangular canvas with bold metallic gold accents on a dark background, sleek frame with a glossy finish", size=[0.04, 0.90, 1.20], placements=[AssetInstance() for _ in range(1)])
mugc_A = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band, Luxe style", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
lighting_C = Assets(description="A wall‑mounted sconce with a sleek brushed‑gold finish, rectangular profile, narrow vertical slats that diffuse warm light, Luxe style", size=[0.10, 0.18, 0.40], placements=[AssetInstance() for _ in range(1)])
lightinga = Assets(description="A wall‑mounted sconce with a sleek metal body, rectangular profile, brushed gold finish, Luxe style", size=[0.10, 0.18, 0.35], placements=[AssetInstance() for _ in range(1)])
art_E = Assets(description="A single piece of thin and upright abstract painting, rectangular canvas with bold geometric patterns in gold and deep navy, framed in a slim black border, Luxe style", size=[0.04, 0.90, 1.20], placements=[AssetInstance() for _ in range(1)])
lighting_D = Assets(description="A wall sconce with brushed brass finish, rectangular housing, sleek low‑profile design, luxe style", size=[0.10, 0.22, 0.30], placements=[AssetInstance() for _ in range(1)])
mug_G = Assets(description="A ceramic mug with a metallic gold rim, cylindrical body, smooth white glaze, slightly tapered at the base, with a subtle glossy sheen on the rim", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
lighting_E = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, sleek curved glass shade, warm metallic tone, and an integrated decorative crystal accent", size=[0.14, 0.20, 0.35], placements=[AssetInstance() for _ in range(1)])
signage_B = Assets(description="A single piece of thin and upright framed sign with gold border, rectangular panel, polished gold trim, luxe style", size=[0.04, 0.65, 0.85], placements=[AssetInstance() for _ in range(1)])
art_F = Assets(description="A single piece of thin and upright abstract painting, rectangular canvas with bold geometric patterns in gold and deep navy, framed in a slim black border, Luxe style", size=[0.04, 0.90, 1.20], placements=[AssetInstance() for _ in range(1)])
mug_H = Assets(description="A ceramic mug with a sleek metallic gold rim, cylindrical body, smooth white glaze, slightly tapered towards the base, glossy finish that catches the light", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
washer_C = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.75, 0.70, 0.95], placements=[AssetInstance() for _ in range(1)])
arta_B = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with bold geometric patterns, gold‑trimmed frame, Luxe style", size=[0.04, 0.85, 1.15], placements=[AssetInstance() for _ in range(1)])
dryer_C = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.75, 0.70, 0.95], placements=[AssetInstance() for _ in range(1)])
plantcorner_A = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with sleek finish, lush green foliage, luxe style", size=[0.50, 0.50, 1.35], placements=[AssetInstance() for _ in range(1)])
art_G = Assets(description="A single piece of thin and upright abstract painting, rectangular canvas with bold geometric patterns in gold and deep navy, framed in a slim black border, Luxe style", size=[0.04, 0.90, 1.20], placements=[AssetInstance() for _ in range(1)])
washer_D = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.75, 0.70, 0.95], placements=[AssetInstance() for _ in range(1)])
storage_B = Assets(description="A wall‑mounted cabinet with marble front, tall rectangular shape, polished white marble surface with subtle gray veining, sleek brass handles, and a recessed glass panel", size=[0.38, 0.80, 1.40], placements=[AssetInstance() for _ in range(1)])
muga = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band, Luxe style", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover, ornate gold lettering, with a subtle raised texture on the cover", size=[0.17, 0.24, 0.04], placements=[AssetInstance() for _ in range(1)])
mug_table_A = Assets(description="A ceramic mug with a metallic gold rim, smooth cylindrical body, glossy white finish, subtle gold accent around the lip", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_E = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with a sleek reflective finish, vibrant green foliage, tall slender stems, and a decorative leaf pattern", size=[0.55, 0.55, 1.65], placements=[AssetInstance() for _ in range(1)])
mug_I = Assets(description="A Luxe ceramic mug with a metallic gold rim, cylindrical shape, smooth white glaze, gold‑finished rim and a subtle curved handle", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
lighting_F = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, sleek curved glass shade, warm metallic tone, and an integrated decorative crystal accent", size=[0.14, 0.20, 0.35], placements=[AssetInstance() for _ in range(1)])
mug_J = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, smooth white body, glossy finish, and a subtle gold accent around the lip", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
mugc_B = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band, Luxe style", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
lighting_G = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, and a curved glass shade that diffuses warm light", size=[0.14, 0.20, 0.35], placements=[AssetInstance() for _ in range(1)])
book_C = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown leather cover with raised gold lettering, elegant and luxurious finish", size=[0.17, 0.24, 0.04], placements=[AssetInstance() for _ in range(1)])
book_D = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover, ornate gold lettering, with a subtle raised texture on the cover", size=[0.17, 0.24, 0.04], placements=[AssetInstance() for _ in range(1)])
magazine_B = Assets(description="A glossy magazine with a metallic cover, rectangular shape, shimmering silver surface, crisp edges, with a subtle embossed logo on the front", size=[0.30, 0.23, 0.01], placements=[AssetInstance() for _ in range(1)])
washer_E = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.75, 0.70, 0.95], placements=[AssetInstance() for _ in range(1)])
washer_F = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.75, 0.70, 0.95], placements=[AssetInstance() for _ in range(1)])
magazine_C = Assets(description="A glossy magazine with a metallic cover, rectangular shape, sleek silver finish with subtle texture, Luxe style", size=[0.30, 0.23, 0.01], placements=[AssetInstance() for _ in range(1)])
table_A = Assets(description="A folding work table with a marble top, rectangular slab, brass legs that fold inward, and a subtle engraved pattern on the surface, plus a hinged brass leaf for extra workspace.", size=[0.75, 1.80, 0.90], placements=[AssetInstance() for _ in range(1)])
signage_C = Assets(description="A framed signage with gold border, thin upright rectangular panel, matte black background, and elegant serif lettering", size=[0.04, 0.65, 0.85], placements=[AssetInstance() for _ in range(1)])
washer_G = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.75, 0.70, 0.95], placements=[AssetInstance() for _ in range(1)])
lighting_H = Assets(description="A wall sconce with brushed brass finish, rectangular housing, sleek low‑profile design, luxe style", size=[0.10, 0.22, 0.30], placements=[AssetInstance() for _ in range(1)])
counter_A = Assets(description="A marble service counter with a white marble surface veined with gray, gold inlaid borders forming a subtle wave pattern, and a slightly beveled rectangular top.", size=[0.75, 2.40, 1.05], placements=[AssetInstance() for _ in range(1)])
table_B = Assets(description="A folding work table with a marble top, rectangular slab, brass legs that fold inward, and a subtle engraved pattern on the surface, plus a hinged brass leaf for extra workspace.", size=[0.75, 1.80, 0.90], placements=[AssetInstance() for _ in range(1)])
mug_K = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, smooth white body, and a subtle glossy finish", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
magazine_D = Assets(description="A glossy magazine with a metallic cover, rectangular shape, shimmering silver surface, crisp edges, with a subtle embossed logo on the front", size=[0.30, 0.23, 0.01], placements=[AssetInstance() for _ in range(1)])
arta_C = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with bold geometric patterns, gold‑trimmed frame, Luxe style", size=[0.04, 0.85, 1.15], placements=[AssetInstance() for _ in range(1)])
art_H = Assets(description="A single piece of thin and upright abstract painting, rectangular canvas with bold geometric patterns in gold and deep navy, framed in a slim black border, Luxe style", size=[0.04, 0.90, 1.20], placements=[AssetInstance() for _ in range(1)])
plant_F = Assets(description="A potted plant in a sleek metallic gold pot, slender green foliage rising from the soil, pot has a smooth cylindrical shape with a subtle reflective sheen", size=[0.45, 0.45, 1.30], placements=[AssetInstance() for _ in range(1)])
book_E = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover, polished finish, and ornate gold lettering", size=[0.17, 0.24, 0.04], placements=[AssetInstance() for _ in range(1)])
lighting_I = Assets(description="A wall‑mounted Luxe lighting sconce with a brushed brass finish, compact rectangular housing, clean lines and a subtle curved glass diffuser that glows warmly", size=[0.14, 0.20, 0.35], placements=[AssetInstance() for _ in range(1)])
storage_C = Assets(description="A wall‑mounted Luxe storage cabinet with a marble front, sleek rectangular silhouette, smooth polished surface and subtle gold‑tone hardware", size=[0.35, 1.20, 0.70], placements=[AssetInstance() for _ in range(1)])
plant_G = Assets(description="A potted plant in a metallic gold pot, featuring a tall slender trunk and lush green foliage, with a cylindrical pot", size=[0.60, 0.60, 1.80], placements=[AssetInstance() for _ in range(1)])
lighting_J = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, sleek curved glass shade, warm metallic tone, and an integrated decorative crystal accent", size=[0.14, 0.20, 0.35], placements=[AssetInstance() for _ in range(1)])
counter_B = Assets(description="A marble service counter with a white marble surface veined with gray, gold inlaid borders forming a subtle wave pattern, and a slightly beveled rectangular top.", size=[0.75, 2.40, 1.05], placements=[AssetInstance() for _ in range(1)])
storage_D = Assets(description="A wall‑mounted cabinet with marble front, tall rectangular shape, polished white marble surface with subtle gray veining, sleek brass handles, and a recessed glass panel", size=[0.38, 0.80, 1.40], placements=[AssetInstance() for _ in range(1)])
mug_L = Assets(description="A ceramic mug with a metallic gold rim, cylindrical body, smooth white glaze, slightly tapered at the base, with a subtle glossy sheen on the rim", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_H = Assets(description="A potted Luxe plant in a metallic gold pot, tall slender trunk with a rounded canopy of glossy green leaves, cylindrical pot with a polished gold finish", size=[0.65, 0.65, 1.90], placements=[AssetInstance() for _ in range(1)])
lighting_K = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, and a curved glass shade that diffuses warm light", size=[0.14, 0.20, 0.35], placements=[AssetInstance() for _ in range(1)])
mug_M = Assets(description="A ceramic mug with metallic gold rim, cylindrical shape, smooth white body, shiny gold edge, luxe style", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
magazine_E = Assets(description="A glossy magazine with metallic cover accents, rectangular shape, smooth glossy pages, shimmering silver and navy pattern on the cover giving a high‑gloss luxe appearance", size=[0.30, 0.23, 0.01], placements=[AssetInstance() for _ in range(1)])
magazine_F = Assets(description="A glossy magazine with a metallic cover, rectangular shape, sleek reflective surface, and a subtle embossed title", size=[0.30, 0.23, 0.01], placements=[AssetInstance() for _ in range(1)])
plant_I = Assets(description="A potted plant in a sleek metallic gold pot, slender green foliage rising from the soil, pot has a smooth cylindrical shape with a subtle reflective sheen", size=[0.45, 0.45, 1.30], placements=[AssetInstance() for _ in range(1)])
mug_counter_A = Assets(description="A ceramic mug with a metallic gold rim, smooth cylindrical body, glossy white finish, subtle gold accent around the lip", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
mug_table_B = Assets(description="A ceramic mug with a metallic gold rim, smooth cylindrical body, glossy white finish, subtle gold accent around the lip", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
magazine_table = Assets(description="A glossy magazine with a metallic cover, rectangular shape, sleek silver‑blue finish, reflective surface", size=[0.30, 0.23, 0.01], placements=[AssetInstance() for _ in range(1)])
washer_H = Assets(description="A front-load washer with a sleek rectangular body, polished chrome finish, and metallic accents, featuring a rounded control panel and an integrated LED indicator ring.", size=[0.75, 0.70, 0.95], placements=[AssetInstance() for _ in range(1)])
lighting_L = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, and a curved glass shade that diffuses warm light", size=[0.14, 0.20, 0.35], placements=[AssetInstance() for _ in range(1)])
lighting_M = Assets(description="A single piece of thin and upright wall‑mounted sconce, compact rectangular housing with a polished gold finish, subtle recessed light panel giving a warm glow", size=[0.10, 0.18, 0.35], placements=[AssetInstance() for _ in range(1)])
lighting_N = Assets(description="A wall sconce with brushed brass finish, rectangular housing, sleek low‑profile design, luxe style", size=[0.10, 0.22, 0.30], placements=[AssetInstance() for _ in range(1)])
lighting_O = Assets(description="A wall‑mounted Luxe lighting sconce with a brushed brass finish, compact rectangular housing, clean lines and a subtle curved glass diffuser that glows warmly", size=[0.14, 0.20, 0.35], placements=[AssetInstance() for _ in range(1)])
storage_E = Assets(description="A wall‑mounted cabinet with marble front, sleek rectangular doors, and polished brass handles", size=[0.35, 1.20, 0.70], placements=[AssetInstance() for _ in range(1)])
bench_B = Assets(description="A polished marble bench with a smooth rectangular seat, white marble top with gold‑flecked veins, slender chrome legs, and an integrated shallow groove along the front edge.", size=[0.45, 1.50, 0.48], placements=[AssetInstance() for _ in range(1)])
lightsconce_A = Assets(description="A wall‑mounted sconce, slender rectangular shape, brushed metal finish with gold accents, luxe style", size=[0.10, 0.16, 0.42], placements=[AssetInstance() for _ in range(1)])
mug_N = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band around the lip, refined Luxe style", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
mug_O = Assets(description="A ceramic mug with metallic gold rim, cylindrical shape, smooth white body, shiny gold edge, luxe style", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
plantcorner_B = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with polished gold surface, green foliage, sleek modern look", size=[0.50, 0.50, 1.35], placements=[AssetInstance() for _ in range(1)])
mug_P = Assets(description="A ceramic mug with a sleek metallic gold rim, cylindrical body, smooth white glaze, slightly tapered towards the base, glossy finish that catches the light", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
art_I = Assets(description="A single piece of thin and upright abstract artwork, rectangular frame with a glossy finish, vibrant colours and bold geometric patterns, mounted flush against the wall", size=[0.04, 0.90, 1.20], placements=[AssetInstance() for _ in range(1)])
art_J = Assets(description="A single piece of thin and upright abstract artwork, rectangular frame with a glossy finish, vibrant colours and bold geometric patterns, mounted flush against the wall", size=[0.04, 0.90, 1.20], placements=[AssetInstance() for _ in range(1)])
art_K = Assets(description="A single piece of thin and upright abstract artwork, rectangular frame with a glossy finish, vibrant colours and bold geometric patterns, mounted flush against the wall", size=[0.04, 0.90, 1.20], placements=[AssetInstance() for _ in range(1)])
signage_D = Assets(description="A framed signage with gold border, thin upright rectangular panel, matte black background, elegant serif lettering, and a subtle beveled edge", size=[0.04, 0.65, 0.85], placements=[AssetInstance() for _ in range(1)])
mug_Q = Assets(description="A ceramic mug with a sleek metallic gold rim, cylindrical body, smooth white glaze, slightly tapered towards the base, glossy finish that catches the light", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
book_F = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover with elegant gilt lettering, luxurious style", size=[0.17, 0.24, 0.04], placements=[AssetInstance() for _ in range(1)])
mug_R = Assets(description="A ceramic mug with a sleek metallic gold rim, cylindrical body, smooth white glaze, slightly tapered towards the base, glossy finish that catches the light", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
art_L = Assets(description="A single piece of thin and upright abstract artwork, rectangular canvas with bold metallic gold accents on a dark background, sleek frame with a glossy finish", size=[0.04, 0.90, 1.20], placements=[AssetInstance() for _ in range(1)])
book_G = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover, ornate gold lettering, with a subtle raised texture on the cover", size=[0.17, 0.24, 0.04], placements=[AssetInstance() for _ in range(1)])
book_H = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover with raised gold lettering, elegant and polished finish", size=[0.17, 0.24, 0.04], placements=[AssetInstance() for _ in range(1)])
storage_F = Assets(description="A wall‑mounted cabinet with marble front, rectangular shape, smooth marble surface with subtle veining, luxe style", size=[0.35, 1.20, 0.70], placements=[AssetInstance() for _ in range(1)])
lighting_P = Assets(description="A wall sconce with brushed brass finish, compact rectangular housing, and a curved glass shade that diffuses warm light", size=[0.14, 0.20, 0.35], placements=[AssetInstance() for _ in range(1)])
armchair_A = Assets(description="A deep‑blue velvet armchair with a plush rectangular back, high curved arms, metallic trim that forms a geometric pattern, and a tufted seat for a luxurious look.", size=[0.85, 0.85, 1.00], placements=[AssetInstance() for _ in range(1)])
lighting_Q = Assets(description="A single piece of thin and upright wall‑mounted sconce, compact rectangular housing with a polished gold finish, subtle recessed light panel giving a warm glow", size=[0.10, 0.18, 0.35], placements=[AssetInstance() for _ in range(1)])
plant_J = Assets(description="A potted Luxe plant in a metallic gold pot, tall slender trunk with a rounded canopy of glossy green leaves, cylindrical pot with a polished gold finish", size=[0.65, 0.65, 1.90], placements=[AssetInstance() for _ in range(1)])
lighting_R = Assets(description="A wall‑mounted Luxe lighting sconce with a brushed brass finish, compact rectangular housing, clean lines and a subtle curved glass diffuser that glows warmly", size=[0.14, 0.20, 0.35], placements=[AssetInstance() for _ in range(1)])
magazine_G = Assets(description="A glossy magazine with a metallic cover, rectangular shape, vibrant reflective surface, high‑end style", size=[0.30, 0.23, 0.01], placements=[AssetInstance() for _ in range(1)])
dryer_D = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.75, 0.70, 0.95], placements=[AssetInstance() for _ in range(1)])
mug_S = Assets(description="A ceramic mug with a metallic gold rim, cylindrical body, smooth white glaze, slightly tapered at the base, with a subtle glossy sheen on the rim", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
dryer_E = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.75, 0.70, 0.95], placements=[AssetInstance() for _ in range(1)])
plantcorner_C = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with polished gold surface, green foliage, sleek modern look", size=[0.50, 0.50, 1.35], placements=[AssetInstance() for _ in range(1)])
mug_T = Assets(description="A Luxe ceramic mug with a metallic gold rim, cylindrical body, glossy ivory finish, gold rim and a gently curved handle", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
magazine_H = Assets(description="A glossy magazine with a metallic cover, rectangular shape, vibrant reflective surface, high‑end style", size=[0.30, 0.23, 0.01], placements=[AssetInstance() for _ in range(1)])
plantcorner_D = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with sleek finish, lush green foliage, luxe style", size=[0.50, 0.50, 1.35], placements=[AssetInstance() for _ in range(1)])
mug_table_C = Assets(description="A ceramic mug with a metallic gold rim, smooth cylindrical body, glossy white finish, subtle gold accent around the lip", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
art_M = Assets(description="A single piece of thin and upright abstract painting, rectangular canvas with bold geometric patterns in gold and deep navy, framed in a slim black border, Luxe style", size=[0.04, 0.90, 1.20], placements=[AssetInstance() for _ in range(1)])
mug_U = Assets(description="A ceramic mug with metallic gold rim, cylindrical shape, smooth white body, shiny gold edge, luxe style", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
art_N = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with vibrant colours, gold‑brushed metal frame, sleek low‑profile mounting", size=[0.04, 0.80, 1.10], placements=[AssetInstance() for _ in range(1)])
dryer_F = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.75, 0.70, 0.95], placements=[AssetInstance() for _ in range(1)])
art_O = Assets(description="A single piece of thin and upright abstract artwork, rectangular frame with a glossy finish, vibrant colours and bold geometric patterns, mounted flush against the wall", size=[0.04, 0.90, 1.20], placements=[AssetInstance() for _ in range(1)])
signage_E = Assets(description="A framed signage with gold border, thin upright rectangular panel, matte black background, and elegant serif lettering", size=[0.04, 0.65, 0.85], placements=[AssetInstance() for _ in range(1)])
mug_V = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, smooth white body, polished gold edge, featuring a delicate engraved pattern near the rim", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
arta_D = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with bold geometric patterns, gold‑trimmed frame, Luxe style", size=[0.04, 0.85, 1.15], placements=[AssetInstance() for _ in range(1)])
mug_counter_B = Assets(description="A ceramic mug with a metallic gold rim, smooth cylindrical body, glossy white finish, subtle gold accent around the lip", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
lighting_S = Assets(description="A wall‑mounted sconce with a sleek brushed‑gold finish, rectangular profile, narrow vertical slats that diffuse warm light, Luxe style", size=[0.10, 0.18, 0.40], placements=[AssetInstance() for _ in range(1)])
magazine_I = Assets(description="A glossy magazine with a metallic cover, rectangular shape, sleek reflective surface, and a subtle embossed title", size=[0.30, 0.23, 0.01], placements=[AssetInstance() for _ in range(1)])
lightingb = Assets(description="A wall‑mounted sconce with a sleek metal body, rectangular profile, brushed gold finish, Luxe style", size=[0.10, 0.18, 0.35], placements=[AssetInstance() for _ in range(1)])
art_P = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with vibrant colours, gold‑brushed metal frame, sleek low‑profile mounting", size=[0.04, 0.80, 1.10], placements=[AssetInstance() for _ in range(1)])
lighting_T = Assets(description="A wall‑mounted sconce with a sleek Luxe design, rectangular metal body, polished gold finish, subtle LED strip that glows softly, low profile that sits close to the wall", size=[0.08, 0.20, 0.40], placements=[AssetInstance() for _ in range(1)])
dryer_G = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.75, 0.70, 0.95], placements=[AssetInstance() for _ in range(1)])
magazine_J = Assets(description="A glossy magazine with metallic cover accents, rectangular shape, smooth glossy pages, shimmering silver and navy pattern on the cover giving a high‑gloss luxe appearance", size=[0.30, 0.23, 0.01], placements=[AssetInstance() for _ in range(1)])
mug_W = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body contrasted by a thin polished gold band near the lip, sleek and refined", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_K = Assets(description="A potted ornamental plant with an elegant cylindrical metallic pot finished in brushed steel, featuring a decorative spiral cutout, and tall leafy foliage extending upward.", size=[0.55, 0.55, 1.70], placements=[AssetInstance() for _ in range(1)])
lighting_U = Assets(description="A wall‑mounted sconce with a sleek metallic gold finish, compact rectangular shape, subtle upward‑facing light source, modern Luxe style", size=[0.12, 0.20, 0.30], placements=[AssetInstance() for _ in range(1)])
magazine_K = Assets(description="A glossy magazine with metallic cover, rectangular shape, sleek silver finish, thin pages, luxe style", size=[0.30, 0.23, 0.01], placements=[AssetInstance() for _ in range(1)])
mug_counter_C = Assets(description="A ceramic mug with a metallic gold rim, smooth cylindrical body, glossy white finish, subtle gold accent around the lip", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
mug_X = Assets(description="A Luxe ceramic mug with a metallic gold rim, cylindrical body, glossy ivory finish, gold rim and a gently curved handle", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
mug_Y = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, smooth white body, polished gold edge, featuring a delicate engraved pattern near the rim", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
plantcorner_E = Assets(description="A potted plant in a metallic gold pot, cylindrical pot with polished gold surface, green foliage, sleek modern look", size=[0.50, 0.50, 1.35], placements=[AssetInstance() for _ in range(1)])
book_I = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover, ornate gold lettering, with a subtle raised texture on the cover", size=[0.17, 0.24, 0.04], placements=[AssetInstance() for _ in range(1)])
book_J = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover with elegant gilt lettering, luxurious style", size=[0.17, 0.24, 0.04], placements=[AssetInstance() for _ in range(1)])
lighting_V = Assets(description="A wall sconce with brushed brass finish, rectangular housing, sleek low‑profile design, luxe style", size=[0.10, 0.22, 0.30], placements=[AssetInstance() for _ in range(1)])
mugb_A = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band, Luxe style", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
storage_G = Assets(description="A wall‑mounted cabinet with marble front, sleek rectangular doors, and polished brass handles", size=[0.35, 1.20, 0.70], placements=[AssetInstance() for _ in range(1)])
mug_Z = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band around the lip, refined Luxe style", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
dryer_H = Assets(description="An electric dryer with a streamlined rectangular shape, metallic finish, polished chrome exterior, and a smooth curved door highlighted by brushed steel trim.", size=[0.75, 0.70, 0.95], placements=[AssetInstance() for _ in range(1)])
art_Q = Assets(description="A single piece of thin and upright framed abstract art, rectangular canvas with vibrant colours, gold‑brushed metal frame, sleek low‑profile mounting", size=[0.04, 0.80, 1.10], placements=[AssetInstance() for _ in range(1)])
plant_L = Assets(description="A potted ornamental plant with an elegant cylindrical metallic pot finished in brushed steel, featuring a decorative spiral cutout, and tall leafy foliage extending upward.", size=[0.55, 0.55, 1.70], placements=[AssetInstance() for _ in range(1)])
book_K = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown leather cover with raised gold lettering, elegant and luxurious finish", size=[0.17, 0.24, 0.04], placements=[AssetInstance() for _ in range(1)])
art_R = Assets(description="A single piece of thin and upright abstract artwork, rectangular frame with a glossy finish, vibrant colours and bold geometric patterns, mounted flush against the wall", size=[0.04, 0.90, 1.20], placements=[AssetInstance() for _ in range(1)])
mugd = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band, Luxe style", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
signage_F = Assets(description="A single piece of thin and upright Luxe signage framed with a gold border, rectangular panel with a polished black background and elegant gold lettering", size=[0.04, 0.70, 0.90], placements=[AssetInstance() for _ in range(1)])
signage_G = Assets(description="A single piece of thin and upright framed sign with gold border, rectangular panel, polished gold trim, luxe style", size=[0.04, 0.65, 0.85], placements=[AssetInstance() for _ in range(1)])
mug_group_2_A = Assets(description="A ceramic mug with a metallic gold rim, cylindrical body, smooth white glaze, slightly tapered at the base, with a subtle glossy sheen on the rim", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
mug_group_2_B = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, smooth white body, polished gold edge, featuring a delicate engraved pattern near the rim", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
signage_H = Assets(description="A framed signage with gold border, thin upright rectangular panel, matte black background, elegant serif lettering, and a subtle beveled edge", size=[0.04, 0.65, 0.85], placements=[AssetInstance() for _ in range(1)])
lightsconce_B = Assets(description="A wall‑mounted sconce, slender rectangular shape, brushed metal finish with gold accents, luxe style", size=[0.10, 0.16, 0.42], placements=[AssetInstance() for _ in range(1)])
lighting_W = Assets(description="A wall‑mounted sconce with a sleek Luxe design, rectangular metal body, polished gold finish, subtle LED strip that glows softly, low profile that sits close to the wall", size=[0.08, 0.20, 0.40], placements=[AssetInstance() for _ in range(1)])
plant_M = Assets(description="A potted Luxe plant in a metallic gold pot, tall slender trunk with a rounded canopy of glossy green leaves, cylindrical pot with a polished gold finish", size=[0.65, 0.65, 1.90], placements=[AssetInstance() for _ in range(1)])
lighting_X = Assets(description="A wall‑mounted Luxe lighting sconce with a brushed brass finish, compact rectangular housing, clean lines and a subtle curved glass diffuser that glows warmly", size=[0.14, 0.20, 0.35], placements=[AssetInstance() for _ in range(1)])
mug_group_2_C = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band around the lip, refined Luxe style", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
plant_N = Assets(description="A potted Luxe plant in a metallic gold pot, tall slender trunk with a rounded canopy of glossy green leaves, cylindrical pot with a polished gold finish", size=[0.65, 0.65, 1.90], placements=[AssetInstance() for _ in range(1)])
book_L = Assets(description="A leather-bound book with gold embossing, featuring a rectangular shape, deep brown cover, and ornate gilded edges", size=[0.17, 0.24, 0.04], placements=[AssetInstance() for _ in range(1)])
book_M = Assets(description="A leather-bound book with gold embossing, rectangular shape, dark brown cover, elegant gold details, luxurious style", size=[0.17, 0.24, 0.04], placements=[AssetInstance() for _ in range(1)])
mugb_B = Assets(description="A ceramic mug with a metallic gold rim, cylindrical shape, glossy white body with a thin gold band, Luxe style", size=[0.10, 0.13, 0.10], placements=[AssetInstance() for _ in range(1)])
armchair_B = Assets(description="A deep‑blue velvet armchair with a plush rectangular back, high curved arms, metallic trim that forms a geometric pattern, and a tufted seat for a luxurious look.", size=[0.85, 0.85, 1.00], placements=[AssetInstance() for _ in range(1)])
storage_H = Assets(description="A wall‑mounted Luxe storage cabinet with a marble front, sleek rectangular silhouette, smooth polished surface and subtle gold‑tone hardware", size=[0.35, 1.20, 0.70], placements=[AssetInstance() for _ in range(1)])

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

storage_A[0].position = [10.303964355500415, 9.324077208093538, 0.35]
storage_A[0].rotation = [0, 0, 0]
book_A[0].position = [12.337562928347053, 6.575900156036249, 0.02]
book_A[0].rotation = [0, 0, 0]
bench_A[0].position = [5.638479723785, 7.050806326732627, 0.24]
bench_A[0].rotation = [0, 0, 0]
plant_A[0].position = [12.43341156769767, 5.691227430223958, 0.85]
plant_A[0].rotation = [0, 0, 0]
magazine_A[0].position = [3.4177958164006768, 0.3186547487044511, 0.005]
magazine_A[0].rotation = [0, 0, 0]
mug_A[0].position = [2.9349400836079838, 3.9518180032402594, 0.05]
mug_A[0].rotation = [0, 0, 0]
plant_B[0].position = [0.9951689339069353, 8.536149858946132, 0.9]
plant_B[0].rotation = [0, 0, 0]
art_A[0].position = [2.5442889365969013, 5.177682600991515, 0.55]
art_A[0].rotation = [0, 0, 0]
art_B[0].position = [10.299118602687493, 1.6579257381719636, 0.6]
art_B[0].rotation = [0, 0, 0]
lighting_A[0].position = [2.5241258005015643, 2.6479244414132697, 0.15]
lighting_A[0].rotation = [0, 0, 0]
signage_A[0].position = [12.113388830840817, 5.71835973803958, 0.45]
signage_A[0].rotation = [0, 0, 0]
washer_A[0].position = [3.638877766741899, 6.299835025668445, 0.475]
washer_A[0].rotation = [0, 0, 0]
mug_B[0].position = [12.720458943977869, 7.320842630807447, 0.05]
mug_B[0].rotation = [0, 0, 0]
washer_B[0].position = [8.2503985450592, 4.562580274615716, 0.475]
washer_B[0].rotation = [0, 0, 0]
mug_C[0].position = [13.948783338372506, 3.854915509618432, 0.05]
mug_C[0].rotation = [0, 0, 0]
mug_D[0].position = [5.741231836526862, 2.9570286920375963, 0.05]
mug_D[0].rotation = [0, 0, 0]
dryer_A[0].position = [5.791032895194807, 7.162186128599869, 0.475]
dryer_A[0].rotation = [0, 0, 0]
dryer_B[0].position = [7.278177132290134, 5.86516539034392, 0.475]
dryer_B[0].rotation = [0, 0, 0]
plant_C[0].position = [9.71456441971751, 7.583725849496062, 0.9]
plant_C[0].rotation = [0, 0, 0]
arta_A[0].position = [9.156902867448279, 7.551412995790333, 0.575]
arta_A[0].rotation = [0, 0, 0]
mug_E[0].position = [7.114252630540623, 2.181202543062779, 0.05]
mug_E[0].rotation = [0, 0, 0]
art_C[0].position = [2.4882598290301554, 8.87212817001711, 0.6]
art_C[0].rotation = [0, 0, 0]
lighting_B[0].position = [0.2827443935998547, 7.922699577103149, 0.175]
lighting_B[0].rotation = [0, 0, 0]
mug_F[0].position = [5.27006559570384, 1.9950235463640198, 0.05]
mug_F[0].rotation = [0, 0, 0]
plant_D[0].position = [1.6723024703422968, 2.81955086252072, 0.825]
plant_D[0].rotation = [0, 0, 0]
art_D[0].position = [14.764997439237826, 1.1263289013734357, 0.6]
art_D[0].rotation = [0, 0, 0]
mugc_A[0].position = [3.6066066901810756, 4.5436983648061, 0.05]
mugc_A[0].rotation = [0, 0, 0]
lighting_C[0].position = [6.806263603426082, 1.4258546036782216, 0.2]
lighting_C[0].rotation = [0, 0, 0]
lightinga[0].position = [7.6562307491363075, 7.175846885232156, 0.175]
lightinga[0].rotation = [0, 0, 0]
art_E[0].position = [3.706988433076817, 9.83421334765273, 0.6]
art_E[0].rotation = [0, 0, 0]
lighting_D[0].position = [7.766201475914907, 5.143206831499446, 0.15]
lighting_D[0].rotation = [0, 0, 0]
mug_G[0].position = [0.11749094746227595, 5.050137146791489, 0.05]
mug_G[0].rotation = [0, 0, 0]
lighting_E[0].position = [11.726898603472966, 1.1827349085275285, 0.175]
lighting_E[0].rotation = [0, 0, 0]
signage_B[0].position = [5.251388665286982, 7.305048008476108, 0.425]
signage_B[0].rotation = [0, 0, 0]
art_F[0].position = [4.657395974295969, 7.644375064732028, 0.6]
art_F[0].rotation = [0, 0, 0]
mug_H[0].position = [10.460627491245909, 7.797981476409549, 0.05]
mug_H[0].rotation = [0, 0, 0]
washer_C[0].position = [14.846755344913245, 9.072798945065951, 0.475]
washer_C[0].rotation = [0, 0, 0]
arta_B[0].position = [3.770525138286249, 1.8328646645406077, 0.575]
arta_B[0].rotation = [0, 0, 0]
dryer_C[0].position = [12.865762687511118, 9.399212042904606, 0.475]
dryer_C[0].rotation = [0, 0, 0]
plantcorner_A[0].position = [14.074399276072658, 8.264531683686313, 0.675]
plantcorner_A[0].rotation = [0, 0, 0]
art_G[0].position = [13.777584515773091, 9.474751506691826, 0.6]
art_G[0].rotation = [0, 0, 0]
washer_D[0].position = [1.4976828007521354, 3.807335295405557, 0.475]
washer_D[0].rotation = [0, 0, 0]
storage_B[0].position = [7.830068117390978, 2.42397160571603, 0.7]
storage_B[0].rotation = [0, 0, 0]
muga[0].position = [9.322650503714206, 9.515753344069628, 0.05]
muga[0].rotation = [0, 0, 0]
book_B[0].position = [3.7217997928319075, 2.4032455415418577, 0.02]
book_B[0].rotation = [0, 0, 0]
mug_table_A[0].position = [1.7165112206246835, 8.656426802432502, 0.05]
mug_table_A[0].rotation = [0, 0, 0]
plant_E[0].position = [0.6983405206038823, 0.5335684684052289, 0.825]
plant_E[0].rotation = [0, 0, 0]
mug_I[0].position = [11.837365181899878, 8.723417765974787, 0.05]
mug_I[0].rotation = [0, 0, 0]
lighting_F[0].position = [14.55590945644746, 1.8803198918641495, 0.175]
lighting_F[0].rotation = [0, 0, 0]
mug_J[0].position = [4.973331422620041, 0.48108020668339746, 0.05]
mug_J[0].rotation = [0, 0, 0]
mugc_B[0].position = [14.672026295565821, 0.1495183290335489, 0.05]
mugc_B[0].rotation = [0, 0, 0]
lighting_G[0].position = [12.104295243397072, 1.5200238090977347, 0.175]
lighting_G[0].rotation = [0, 0, 0]
book_C[0].position = [1.4884629068424504, 3.9958893416366124, 0.02]
book_C[0].rotation = [0, 0, 0]
book_D[0].position = [4.561067915207676, 3.334129176345196, 0.02]
book_D[0].rotation = [0, 0, 0]
magazine_B[0].position = [6.868565870682135, 1.1197257161495, 0.005]
magazine_B[0].rotation = [0, 0, 0]
washer_E[0].position = [12.572661639210063, 6.973162073157049, 0.475]
washer_E[0].rotation = [0, 0, 0]
washer_F[0].position = [7.488645264884048, 1.8101674414172464, 0.475]
washer_F[0].rotation = [0, 0, 0]
magazine_C[0].position = [2.587605479581789, 6.245127163020446, 0.005]
magazine_C[0].rotation = [0, 0, 0]
table_A[0].position = [8.363019138889157, 3.486658582097478, 0.45]
table_A[0].rotation = [0, 0, 0]
signage_C[0].position = [12.693765739907668, 4.646144753497711, 0.425]
signage_C[0].rotation = [0, 0, 0]
washer_G[0].position = [5.19822503196162, 3.5166459524652263, 0.475]
washer_G[0].rotation = [0, 0, 0]
lighting_H[0].position = [11.336850954304744, 4.195832977981792, 0.15]
lighting_H[0].rotation = [0, 0, 0]
counter_A[0].position = [10.349075529900967, 3.816354761936914, 0.525]
counter_A[0].rotation = [0, 0, 0]
table_B[0].position = [14.931486441240223, 5.579326661854733, 0.45]
table_B[0].rotation = [0, 0, 0]
mug_K[0].position = [14.385577971451724, 9.390327790957102, 0.05]
mug_K[0].rotation = [0, 0, 0]
magazine_D[0].position = [10.171975231925307, 9.647152392222758, 0.005]
magazine_D[0].rotation = [0, 0, 0]
arta_C[0].position = [9.453476868156093, 1.240108493685449, 0.575]
arta_C[0].rotation = [0, 0, 0]
art_H[0].position = [0.7071457273396109, 7.7625619009413125, 0.6]
art_H[0].rotation = [0, 0, 0]
plant_F[0].position = [12.51507519864915, 7.091927384657454, 0.65]
plant_F[0].rotation = [0, 0, 0]
book_E[0].position = [5.3569098384813, 4.2691364541837675, 0.02]
book_E[0].rotation = [0, 0, 0]
lighting_I[0].position = [1.2147498906574143, 5.2270024116099245, 0.175]
lighting_I[0].rotation = [0, 0, 0]
storage_C[0].position = [3.245405646264028, 9.330168351923172, 0.35]
storage_C[0].rotation = [0, 0, 0]
plant_G[0].position = [3.6073018789569042, 3.088279213194649, 0.9]
plant_G[0].rotation = [0, 0, 0]
lighting_J[0].position = [9.72941664020137, 1.5630133253986367, 0.175]
lighting_J[0].rotation = [0, 0, 0]
counter_B[0].position = [1.8816560698019695, 2.985306095072935, 0.525]
counter_B[0].rotation = [0, 0, 0]
storage_D[0].position = [13.672919636632233, 8.74007902446596, 0.7]
storage_D[0].rotation = [0, 0, 0]
mug_L[0].position = [4.011970276509847, 0.564534327378875, 0.05]
mug_L[0].rotation = [0, 0, 0]
plant_H[0].position = [5.5429506472671015, 8.055160534087824, 0.95]
plant_H[0].rotation = [0, 0, 0]
lighting_K[0].position = [8.718430586448441, 2.6281819789087257, 0.175]
lighting_K[0].rotation = [0, 0, 0]
mug_M[0].position = [13.475663221648563, 7.564617181676643, 0.05]
mug_M[0].rotation = [0, 0, 0]
magazine_E[0].position = [11.560712849730145, 5.40531194976963, 0.005]
magazine_E[0].rotation = [0, 0, 0]
magazine_F[0].position = [2.950243186788435, 4.605307336854256, 0.005]
magazine_F[0].rotation = [0, 0, 0]
plant_I[0].position = [1.945065169567115, 4.2644328455440625, 0.65]
plant_I[0].rotation = [0, 0, 0]
mug_counter_A[0].position = [13.970320720909667, 8.677382267055677, 0.05]
mug_counter_A[0].rotation = [0, 0, 0]
mug_table_B[0].position = [9.595220925962398, 1.6406930453888235, 0.05]
mug_table_B[0].rotation = [0, 0, 0]
magazine_table[0].position = [10.983376987214632, 9.768499819661539, 0.005]
magazine_table[0].rotation = [0, 0, 0]
washer_H[0].position = [7.549114065518961, 9.762678263758122, 0.475]
washer_H[0].rotation = [0, 0, 0]
lighting_L[0].position = [4.815069278825737, 1.0220383286245749, 0.175]
lighting_L[0].rotation = [0, 0, 0]
lighting_M[0].position = [1.5738307939002483, 3.0992015418042507, 0.175]
lighting_M[0].rotation = [0, 0, 0]
lighting_N[0].position = [6.963946502005831, 6.589232472519479, 0.15]
lighting_N[0].rotation = [0, 0, 0]
lighting_O[0].position = [8.576448863765933, 3.2773403576309823, 0.175]
lighting_O[0].rotation = [0, 0, 0]
storage_E[0].position = [8.30015353329618, 0.341488090537454, 0.35]
storage_E[0].rotation = [0, 0, 0]
bench_B[0].position = [13.316335451450287, 6.3532260400551035, 0.24]
bench_B[0].rotation = [0, 0, 0]
lightsconce_A[0].position = [9.76014134602758, 3.445999091965742, 0.21]
lightsconce_A[0].rotation = [0, 0, 0]
mug_N[0].position = [8.985283651843154, 7.590579157022522, 0.05]
mug_N[0].rotation = [0, 0, 0]
mug_O[0].position = [1.3794033195514943, 3.0909898278508505, 0.05]
mug_O[0].rotation = [0, 0, 0]
plantcorner_B[0].position = [14.31193653395271, 5.70171929614511, 0.675]
plantcorner_B[0].rotation = [0, 0, 0]
mug_P[0].position = [5.53286477601837, 8.065428003255732, 0.05]
mug_P[0].rotation = [0, 0, 0]
art_I[0].position = [6.008486852290656, 6.818919831104129, 0.6]
art_I[0].rotation = [0, 0, 0]
art_J[0].position = [8.959689727164966, 8.936042986051952, 0.6]
art_J[0].rotation = [0, 0, 0]
art_K[0].position = [12.64933776168223, 1.0903375857292874, 0.6]
art_K[0].rotation = [0, 0, 0]
signage_D[0].position = [11.858218942140574, 4.386858429621658, 0.425]
signage_D[0].rotation = [0, 0, 0]
mug_Q[0].position = [9.537641517890822, 9.456760658556579, 0.05]
mug_Q[0].rotation = [0, 0, 0]
book_F[0].position = [13.35296731711304, 9.658362356261861, 0.02]
book_F[0].rotation = [0, 0, 0]
mug_R[0].position = [10.356210993651995, 1.4584212242285133, 0.05]
mug_R[0].rotation = [0, 0, 0]
art_L[0].position = [13.989587393849956, 9.593983562576984, 0.6]
art_L[0].rotation = [0, 0, 0]
book_G[0].position = [4.713540054151826, 9.327461710669759, 0.02]
book_G[0].rotation = [0, 0, 0]
book_H[0].position = [7.087442096971971, 8.956713769147651, 0.02]
book_H[0].rotation = [0, 0, 0]
storage_F[0].position = [14.11788830825331, 9.683199108407713, 0.35]
storage_F[0].rotation = [0, 0, 0]
lighting_P[0].position = [1.297456241388904, 6.821408301301074, 0.175]
lighting_P[0].rotation = [0, 0, 0]
armchair_A[0].position = [13.407524403778831, 2.9434664614068264, 0.5]
armchair_A[0].rotation = [0, 0, 0]
lighting_Q[0].position = [7.323256365435976, 9.784000685156975, 0.175]
lighting_Q[0].rotation = [0, 0, 0]
plant_J[0].position = [2.943112684828342, 2.1103024574443365, 0.95]
plant_J[0].rotation = [0, 0, 0]
lighting_R[0].position = [4.045415006578935, 6.431938752561975, 0.175]
lighting_R[0].rotation = [0, 0, 0]
magazine_G[0].position = [13.749331894399383, 7.76035431393948, 0.005]
magazine_G[0].rotation = [0, 0, 0]
dryer_D[0].position = [4.788839548770861, 5.919506619194514, 0.475]
dryer_D[0].rotation = [0, 0, 0]
mug_S[0].position = [12.567115518275559, 2.4911965730667474, 0.05]
mug_S[0].rotation = [0, 0, 0]
dryer_E[0].position = [11.321770608148551, 4.437223765059047, 0.475]
dryer_E[0].rotation = [0, 0, 0]
plantcorner_C[0].position = [13.110950851284711, 4.850469347038052, 0.675]
plantcorner_C[0].rotation = [0, 0, 0]
mug_T[0].position = [11.56076557008315, 8.325093231767998, 0.05]
mug_T[0].rotation = [0, 0, 0]
magazine_H[0].position = [10.420887637836143, 7.505520614391044, 0.005]
magazine_H[0].rotation = [0, 0, 0]
plantcorner_D[0].position = [4.8362017784377835, 5.710558306162653, 0.675]
plantcorner_D[0].rotation = [0, 0, 0]
mug_table_C[0].position = [10.71810819617016, 8.129208199796864, 0.05]
mug_table_C[0].rotation = [0, 0, 0]
art_M[0].position = [1.4430179855328689, 5.531161668321769, 0.6]
art_M[0].rotation = [0, 0, 0]
mug_U[0].position = [7.927984294441817, 2.2433691952712165, 0.05]
mug_U[0].rotation = [0, 0, 0]
art_N[0].position = [13.173585643836477, 0.36302696165700143, 0.55]
art_N[0].rotation = [0, 0, 0]
dryer_F[0].position = [11.58053449390304, 9.573721244505935, 0.475]
dryer_F[0].rotation = [0, 0, 0]
art_O[0].position = [14.502066504207532, 5.561727290358423, 0.6]
art_O[0].rotation = [0, 0, 0]
signage_E[0].position = [7.259110824814176, 7.910788831252075, 0.425]
signage_E[0].rotation = [0, 0, 0]
mug_V[0].position = [4.543697853812323, 9.254012265481403, 0.05]
mug_V[0].rotation = [0, 0, 0]
arta_D[0].position = [7.395481762298454, 0.1590918902363747, 0.575]
arta_D[0].rotation = [0, 0, 0]
mug_counter_B[0].position = [11.46979793631178, 4.03796296975898, 0.05]
mug_counter_B[0].rotation = [0, 0, 0]
lighting_S[0].position = [14.026152167479632, 7.635778176310806, 0.2]
lighting_S[0].rotation = [0, 0, 0]
magazine_I[0].position = [4.709344335113876, 3.4327752314998405, 0.005]
magazine_I[0].rotation = [0, 0, 0]
lightingb[0].position = [14.528655837403026, 1.536400815230502, 0.175]
lightingb[0].rotation = [0, 0, 0]
art_P[0].position = [2.387568478332811, 5.284856969089452, 0.55]
art_P[0].rotation = [0, 0, 0]
lighting_T[0].position = [13.02583888727559, 9.61751406899435, 0.2]
lighting_T[0].rotation = [0, 0, 0]
dryer_G[0].position = [1.3729472686927713, 9.053739358160792, 0.475]
dryer_G[0].rotation = [0, 0, 0]
magazine_J[0].position = [6.874730882250621, 5.610246327698233, 0.005]
magazine_J[0].rotation = [0, 0, 0]
mug_W[0].position = [12.352832514224708, 3.561484436780371, 0.05]
mug_W[0].rotation = [0, 0, 0]
plant_K[0].position = [13.996178496320692, 0.7928175200037268, 0.85]
plant_K[0].rotation = [0, 0, 0]
lighting_U[0].position = [2.552217911900506, 3.798595553477251, 0.15]
lighting_U[0].rotation = [0, 0, 0]
magazine_K[0].position = [12.869448077228201, 2.0453488782157736, 0.005]
magazine_K[0].rotation = [0, 0, 0]
mug_counter_C[0].position = [5.029975803838508, 6.468494928197788, 0.05]
mug_counter_C[0].rotation = [0, 0, 0]
mug_X[0].position = [11.597067139632568, 9.899359433479749, 0.05]
mug_X[0].rotation = [0, 0, 0]
mug_Y[0].position = [8.363167958385063, 1.0993507998671648, 0.05]
mug_Y[0].rotation = [0, 0, 0]
plantcorner_E[0].position = [5.964551513473952, 8.173474728960361, 0.675]
plantcorner_E[0].rotation = [0, 0, 0]
book_I[0].position = [10.643590580912859, 7.3788926516175675, 0.02]
book_I[0].rotation = [0, 0, 0]
book_J[0].position = [1.4883929003336323, 9.79417765246739, 0.02]
book_J[0].rotation = [0, 0, 0]
lighting_V[0].position = [6.590279695235189, 2.185879843421451, 0.15]
lighting_V[0].rotation = [0, 0, 0]
mugb_A[0].position = [0.9813335004193774, 5.801113639402705, 0.05]
mugb_A[0].rotation = [0, 0, 0]
storage_G[0].position = [10.79652386839753, 6.433955713855193, 0.35]
storage_G[0].rotation = [0, 0, 0]
mug_Z[0].position = [1.7075896316476857, 3.1932000697143668, 0.05]
mug_Z[0].rotation = [0, 0, 0]
dryer_H[0].position = [3.235984300034058, 4.481523431711587, 0.475]
dryer_H[0].rotation = [0, 0, 0]
art_Q[0].position = [10.704367386161659, 7.5807875265819336, 0.55]
art_Q[0].rotation = [0, 0, 0]
plant_L[0].position = [2.380533886286594, 1.0397412980965925, 0.85]
plant_L[0].rotation = [0, 0, 0]
book_K[0].position = [5.834597754841892, 4.107730948173794, 0.02]
book_K[0].rotation = [0, 0, 0]
art_R[0].position = [12.222524753355675, 0.19888814392200693, 0.6]
art_R[0].rotation = [0, 0, 0]
mugd[0].position = [13.396300865446538, 4.40658061387097, 0.05]
mugd[0].rotation = [0, 0, 0]
signage_F[0].position = [0.10165995486895896, 3.807400298224052, 0.45]
signage_F[0].rotation = [0, 0, 0]
signage_G[0].position = [14.58371952397785, 8.021922743450357, 0.425]
signage_G[0].rotation = [0, 0, 0]
mug_group_2_A[0].position = [10.237095450845576, 6.454387820766757, 0.05]
mug_group_2_A[0].rotation = [0, 0, 0]
mug_group_2_B[0].position = [7.559667679352492, 3.8464158683058858, 0.05]
mug_group_2_B[0].rotation = [0, 0, 0]
signage_H[0].position = [0.3395911718426431, 0.33841396319599704, 0.425]
signage_H[0].rotation = [0, 0, 0]
lightsconce_B[0].position = [11.923319966084126, 6.118804838519055, 0.21]
lightsconce_B[0].rotation = [0, 0, 0]
lighting_W[0].position = [8.774037689794547, 0.8090300683714102, 0.2]
lighting_W[0].rotation = [0, 0, 0]
plant_M[0].position = [3.6585541842072193, 4.73197069564957, 0.95]
plant_M[0].rotation = [0, 0, 0]
lighting_X[0].position = [3.709081683391382, 1.5113709937584507, 0.175]
lighting_X[0].rotation = [0, 0, 0]
mug_group_2_C[0].position = [11.706122641325312, 1.770132473135957, 0.05]
mug_group_2_C[0].rotation = [0, 0, 0]
plant_N[0].position = [12.536779351970251, 9.763712250178626, 0.95]
plant_N[0].rotation = [0, 0, 0]
book_L[0].position = [11.719398914025472, 8.841014874607273, 0.02]
book_L[0].rotation = [0, 0, 0]
book_M[0].position = [9.339313479254926, 0.9470282923059603, 0.02]
book_M[0].rotation = [0, 0, 0]
mugb_B[0].position = [14.386679286663957, 2.2775229595695965, 0.05]
mugb_B[0].rotation = [0, 0, 0]
armchair_B[0].position = [9.416259218297876, 4.740949061305454, 0.5]
armchair_B[0].rotation = [0, 0, 0]
storage_H[0].position = [11.758379128049452, 7.929020774224181, 0.35]
storage_H[0].rotation = [0, 0, 0]
storage_A[0].position = [10.303964355500415, 9.324077208093538, 0.35]
storage_A[0].rotation = [0, 0, 0]
book_A[0].position = [12.337562928347053, 6.575900156036249, 0.02]
book_A[0].rotation = [0, 0, 0]
bench_A[0].position = [5.638479723785, 7.050806326732627, 0.24]
bench_A[0].rotation = [0, 0, 0]
plant_A[0].position = [12.43341156769767, 5.691227430223958, 0.85]
plant_A[0].rotation = [0, 0, 0]
magazine_A[0].position = [3.4177958164006768, 0.3186547487044511, 0.005]
magazine_A[0].rotation = [0, 0, 0]
mug_A[0].position = [2.9349400836079838, 3.9518180032402594, 0.05]
mug_A[0].rotation = [0, 0, 0]
plant_B[0].position = [0.9951689339069353, 8.536149858946132, 0.9]
plant_B[0].rotation = [0, 0, 0]
art_A[0].position = [2.5442889365969013, 5.177682600991515, 0.55]
art_A[0].rotation = [0, 0, 0]
art_B[0].position = [10.299118602687493, 1.6579257381719636, 0.6]
art_B[0].rotation = [0, 0, 0]
lighting_A[0].position = [2.5241258005015643, 2.6479244414132697, 0.15]
lighting_A[0].rotation = [0, 0, 0]
signage_A[0].position = [12.113388830840817, 5.71835973803958, 0.45]
signage_A[0].rotation = [0, 0, 0]
washer_A[0].position = [3.638877766741899, 6.299835025668445, 0.475]
washer_A[0].rotation = [0, 0, 0]
mug_B[0].position = [12.720458943977869, 7.320842630807447, 0.05]
mug_B[0].rotation = [0, 0, 0]
washer_B[0].position = [8.2503985450592, 4.562580274615716, 0.475]
washer_B[0].rotation = [0, 0, 0]
mug_C[0].position = [13.948783338372506, 3.854915509618432, 0.05]
mug_C[0].rotation = [0, 0, 0]
mug_D[0].position = [5.741231836526862, 2.9570286920375963, 0.05]
mug_D[0].rotation = [0, 0, 0]
dryer_A[0].position = [5.791032895194807, 7.162186128599869, 0.475]
dryer_A[0].rotation = [0, 0, 0]
dryer_B[0].position = [7.278177132290134, 5.86516539034392, 0.475]
dryer_B[0].rotation = [0, 0, 0]
plant_C[0].position = [9.71456441971751, 7.583725849496062, 0.9]
plant_C[0].rotation = [0, 0, 0]
arta_A[0].position = [9.156902867448279, 7.551412995790333, 0.575]
arta_A[0].rotation = [0, 0, 0]
mug_E[0].position = [7.114252630540623, 2.181202543062779, 0.05]
mug_E[0].rotation = [0, 0, 0]
art_C[0].position = [2.4882598290301554, 8.87212817001711, 0.6]
art_C[0].rotation = [0, 0, 0]
lighting_B[0].position = [0.2827443935998547, 7.922699577103149, 0.175]
lighting_B[0].rotation = [0, 0, 0]
mug_F[0].position = [5.27006559570384, 1.9950235463640198, 0.05]
mug_F[0].rotation = [0, 0, 0]
plant_D[0].position = [1.6723024703422968, 2.81955086252072, 0.825]
plant_D[0].rotation = [0, 0, 0]
art_D[0].position = [14.764997439237826, 1.1263289013734357, 0.6]
art_D[0].rotation = [0, 0, 0]
mugc_A[0].position = [3.6066066901810756, 4.5436983648061, 0.05]
mugc_A[0].rotation = [0, 0, 0]
lighting_C[0].position = [6.806263603426082, 1.4258546036782216, 0.2]
lighting_C[0].rotation = [0, 0, 0]
lightinga[0].position = [7.6562307491363075, 7.175846885232156, 0.175]
lightinga[0].rotation = [0, 0, 0]
art_E[0].position = [3.706988433076817, 9.83421334765273, 0.6]
art_E[0].rotation = [0, 0, 0]
lighting_D[0].position = [7.766201475914907, 5.143206831499446, 0.15]
lighting_D[0].rotation = [0, 0, 0]
mug_G[0].position = [0.11749094746227595, 5.050137146791489, 0.05]
mug_G[0].rotation = [0, 0, 0]
lighting_E[0].position = [11.726898603472966, 1.1827349085275285, 0.175]
lighting_E[0].rotation = [0, 0, 0]
signage_B[0].position = [5.251388665286982, 7.305048008476108, 0.425]
signage_B[0].rotation = [0, 0, 0]
art_F[0].position = [4.657395974295969, 7.644375064732028, 0.6]
art_F[0].rotation = [0, 0, 0]
mug_H[0].position = [10.460627491245909, 7.797981476409549, 0.05]
mug_H[0].rotation = [0, 0, 0]
washer_C[0].position = [14.846755344913245, 9.072798945065951, 0.475]
washer_C[0].rotation = [0, 0, 0]
arta_B[0].position = [3.770525138286249, 1.8328646645406077, 0.575]
arta_B[0].rotation = [0, 0, 0]
dryer_C[0].position = [12.865762687511118, 9.399212042904606, 0.475]
dryer_C[0].rotation = [0, 0, 0]
plantcorner_A[0].position = [14.074399276072658, 8.264531683686313, 0.675]
plantcorner_A[0].rotation = [0, 0, 0]
art_G[0].position = [13.777584515773091, 9.474751506691826, 0.6]
art_G[0].rotation = [0, 0, 0]
washer_D[0].position = [1.4976828007521354, 3.807335295405557, 0.475]
washer_D[0].rotation = [0, 0, 0]
storage_B[0].position = [7.830068117390978, 2.42397160571603, 0.7]
storage_B[0].rotation = [0, 0, 0]
muga[0].position = [9.322650503714206, 9.515753344069628, 0.05]
muga[0].rotation = [0, 0, 0]
book_B[0].position = [3.7217997928319075, 2.4032455415418577, 0.02]
book_B[0].rotation = [0, 0, 0]
mug_table_A[0].position = [1.7165112206246835, 8.656426802432502, 0.05]
mug_table_A[0].rotation = [0, 0, 0]
plant_E[0].position = [0.6983405206038823, 0.5335684684052289, 0.825]
plant_E[0].rotation = [0, 0, 0]
mug_I[0].position = [11.837365181899878, 8.723417765974787, 0.05]
mug_I[0].rotation = [0, 0, 0]
lighting_F[0].position = [14.55590945644746, 1.8803198918641495, 0.175]
lighting_F[0].rotation = [0, 0, 0]
mug_J[0].position = [4.973331422620041, 0.48108020668339746, 0.05]
mug_J[0].rotation = [0, 0, 0]
mugc_B[0].position = [14.672026295565821, 0.1495183290335489, 0.05]
mugc_B[0].rotation = [0, 0, 0]
lighting_G[0].position = [12.104295243397072, 1.5200238090977347, 0.175]
lighting_G[0].rotation = [0, 0, 0]
book_C[0].position = [1.4884629068424504, 3.9958893416366124, 0.02]
book_C[0].rotation = [0, 0, 0]
book_D[0].position = [4.561067915207676, 3.334129176345196, 0.02]
book_D[0].rotation = [0, 0, 0]
magazine_B[0].position = [6.868565870682135, 1.1197257161495, 0.005]
magazine_B[0].rotation = [0, 0, 0]
washer_E[0].position = [12.572661639210063, 6.973162073157049, 0.475]
washer_E[0].rotation = [0, 0, 0]
washer_F[0].position = [7.488645264884048, 1.8101674414172464, 0.475]
washer_F[0].rotation = [0, 0, 0]
magazine_C[0].position = [2.587605479581789, 6.245127163020446, 0.005]
magazine_C[0].rotation = [0, 0, 0]
table_A[0].position = [8.363019138889157, 3.486658582097478, 0.45]
table_A[0].rotation = [0, 0, 0]
signage_C[0].position = [12.693765739907668, 4.646144753497711, 0.425]
signage_C[0].rotation = [0, 0, 0]
washer_G[0].position = [5.19822503196162, 3.5166459524652263, 0.475]
washer_G[0].rotation = [0, 0, 0]
lighting_H[0].position = [11.336850954304744, 4.195832977981792, 0.15]
lighting_H[0].rotation = [0, 0, 0]
counter_A[0].position = [10.349075529900967, 3.816354761936914, 0.525]
counter_A[0].rotation = [0, 0, 0]
table_B[0].position = [14.931486441240223, 5.579326661854733, 0.45]
table_B[0].rotation = [0, 0, 0]
mug_K[0].position = [14.385577971451724, 9.390327790957102, 0.05]
mug_K[0].rotation = [0, 0, 0]
magazine_D[0].position = [10.171975231925307, 9.647152392222758, 0.005]
magazine_D[0].rotation = [0, 0, 0]
arta_C[0].position = [9.453476868156093, 1.240108493685449, 0.575]
arta_C[0].rotation = [0, 0, 0]
art_H[0].position = [0.7071457273396109, 7.7625619009413125, 0.6]
art_H[0].rotation = [0, 0, 0]
plant_F[0].position = [12.51507519864915, 7.091927384657454, 0.65]
plant_F[0].rotation = [0, 0, 0]
book_E[0].position = [5.3569098384813, 4.2691364541837675, 0.02]
book_E[0].rotation = [0, 0, 0]
lighting_I[0].position = [1.2147498906574143, 5.2270024116099245, 0.175]
lighting_I[0].rotation = [0, 0, 0]
storage_C[0].position = [3.245405646264028, 9.330168351923172, 0.35]
storage_C[0].rotation = [0, 0, 0]
plant_G[0].position = [3.6073018789569042, 3.088279213194649, 0.9]
plant_G[0].rotation = [0, 0, 0]
lighting_J[0].position = [9.72941664020137, 1.5630133253986367, 0.175]
lighting_J[0].rotation = [0, 0, 0]
counter_B[0].position = [1.8816560698019695, 2.985306095072935, 0.525]
counter_B[0].rotation = [0, 0, 0]
storage_D[0].position = [13.672919636632233, 8.74007902446596, 0.7]
storage_D[0].rotation = [0, 0, 0]
mug_L[0].position = [4.011970276509847, 0.564534327378875, 0.05]
mug_L[0].rotation = [0, 0, 0]
plant_H[0].position = [5.5429506472671015, 8.055160534087824, 0.95]
plant_H[0].rotation = [0, 0, 0]
lighting_K[0].position = [8.718430586448441, 2.6281819789087257, 0.175]
lighting_K[0].rotation = [0, 0, 0]
mug_M[0].position = [13.475663221648563, 7.564617181676643, 0.05]
mug_M[0].rotation = [0, 0, 0]
magazine_E[0].position = [11.560712849730145, 5.40531194976963, 0.005]
magazine_E[0].rotation = [0, 0, 0]
magazine_F[0].position = [2.950243186788435, 4.605307336854256, 0.005]
magazine_F[0].rotation = [0, 0, 0]
plant_I[0].position = [1.945065169567115, 4.2644328455440625, 0.65]
plant_I[0].rotation = [0, 0, 0]
mug_counter_A[0].position = [13.970320720909667, 8.677382267055677, 0.05]
mug_counter_A[0].rotation = [0, 0, 0]
mug_table_B[0].position = [9.595220925962398, 1.6406930453888235, 0.05]
mug_table_B[0].rotation = [0, 0, 0]
magazine_table[0].position = [10.983376987214632, 9.768499819661539, 0.005]
magazine_table[0].rotation = [0, 0, 0]
washer_H[0].position = [7.549114065518961, 9.762678263758122, 0.475]
washer_H[0].rotation = [0, 0, 0]
lighting_L[0].position = [4.815069278825737, 1.0220383286245749, 0.175]
lighting_L[0].rotation = [0, 0, 0]
lighting_M[0].position = [1.5738307939002483, 3.0992015418042507, 0.175]
lighting_M[0].rotation = [0, 0, 0]
lighting_N[0].position = [6.963946502005831, 6.589232472519479, 0.15]
lighting_N[0].rotation = [0, 0, 0]
lighting_O[0].position = [8.576448863765933, 3.2773403576309823, 0.175]
lighting_O[0].rotation = [0, 0, 0]
storage_E[0].position = [8.30015353329618, 0.341488090537454, 0.35]
storage_E[0].rotation = [0, 0, 0]
bench_B[0].position = [13.316335451450287, 6.3532260400551035, 0.24]
bench_B[0].rotation = [0, 0, 0]
lightsconce_A[0].position = [9.76014134602758, 3.445999091965742, 0.21]
lightsconce_A[0].rotation = [0, 0, 0]
mug_N[0].position = [8.985283651843154, 7.590579157022522, 0.05]
mug_N[0].rotation = [0, 0, 0]
mug_O[0].position = [1.3794033195514943, 3.0909898278508505, 0.05]
mug_O[0].rotation = [0, 0, 0]
plantcorner_B[0].position = [14.31193653395271, 5.70171929614511, 0.675]
plantcorner_B[0].rotation = [0, 0, 0]
mug_P[0].position = [5.53286477601837, 8.065428003255732, 0.05]
mug_P[0].rotation = [0, 0, 0]
art_I[0].position = [6.008486852290656, 6.818919831104129, 0.6]
art_I[0].rotation = [0, 0, 0]
art_J[0].position = [8.959689727164966, 8.936042986051952, 0.6]
art_J[0].rotation = [0, 0, 0]
art_K[0].position = [12.64933776168223, 1.0903375857292874, 0.6]
art_K[0].rotation = [0, 0, 0]
signage_D[0].position = [11.858218942140574, 4.386858429621658, 0.425]
signage_D[0].rotation = [0, 0, 0]
mug_Q[0].position = [9.537641517890822, 9.456760658556579, 0.05]
mug_Q[0].rotation = [0, 0, 0]
book_F[0].position = [13.35296731711304, 9.658362356261861, 0.02]
book_F[0].rotation = [0, 0, 0]
mug_R[0].position = [10.356210993651995, 1.4584212242285133, 0.05]
mug_R[0].rotation = [0, 0, 0]
art_L[0].position = [13.989587393849956, 9.593983562576984, 0.6]
art_L[0].rotation = [0, 0, 0]
book_G[0].position = [4.713540054151826, 9.327461710669759, 0.02]
book_G[0].rotation = [0, 0, 0]
book_H[0].position = [7.087442096971971, 8.956713769147651, 0.02]
book_H[0].rotation = [0, 0, 0]
storage_F[0].position = [14.11788830825331, 9.683199108407713, 0.35]
storage_F[0].rotation = [0, 0, 0]
lighting_P[0].position = [1.297456241388904, 6.821408301301074, 0.175]
lighting_P[0].rotation = [0, 0, 0]
armchair_A[0].position = [13.407524403778831, 2.9434664614068264, 0.5]
armchair_A[0].rotation = [0, 0, 0]
lighting_Q[0].position = [7.323256365435976, 9.784000685156975, 0.175]
lighting_Q[0].rotation = [0, 0, 0]
plant_J[0].position = [2.943112684828342, 2.1103024574443365, 0.95]
plant_J[0].rotation = [0, 0, 0]
lighting_R[0].position = [4.045415006578935, 6.431938752561975, 0.175]
lighting_R[0].rotation = [0, 0, 0]
magazine_G[0].position = [13.749331894399383, 7.76035431393948, 0.005]
magazine_G[0].rotation = [0, 0, 0]
dryer_D[0].position = [4.788839548770861, 5.919506619194514, 0.475]
dryer_D[0].rotation = [0, 0, 0]
mug_S[0].position = [12.567115518275559, 2.4911965730667474, 0.05]
mug_S[0].rotation = [0, 0, 0]
dryer_E[0].position = [11.321770608148551, 4.437223765059047, 0.475]
dryer_E[0].rotation = [0, 0, 0]
plantcorner_C[0].position = [13.110950851284711, 4.850469347038052, 0.675]
plantcorner_C[0].rotation = [0, 0, 0]
mug_T[0].position = [11.56076557008315, 8.325093231767998, 0.05]
mug_T[0].rotation = [0, 0, 0]
magazine_H[0].position = [10.420887637836143, 7.505520614391044, 0.005]
magazine_H[0].rotation = [0, 0, 0]
plantcorner_D[0].position = [4.8362017784377835, 5.710558306162653, 0.675]
plantcorner_D[0].rotation = [0, 0, 0]
mug_table_C[0].position = [10.71810819617016, 8.129208199796864, 0.05]
mug_table_C[0].rotation = [0, 0, 0]
art_M[0].position = [1.4430179855328689, 5.531161668321769, 0.6]
art_M[0].rotation = [0, 0, 0]
mug_U[0].position = [7.927984294441817, 2.2433691952712165, 0.05]
mug_U[0].rotation = [0, 0, 0]
art_N[0].position = [13.173585643836477, 0.36302696165700143, 0.55]
art_N[0].rotation = [0, 0, 0]
dryer_F[0].position = [11.58053449390304, 9.573721244505935, 0.475]
dryer_F[0].rotation = [0, 0, 0]
art_O[0].position = [14.502066504207532, 5.561727290358423, 0.6]
art_O[0].rotation = [0, 0, 0]
signage_E[0].position = [7.259110824814176, 7.910788831252075, 0.425]
signage_E[0].rotation = [0, 0, 0]
mug_V[0].position = [4.543697853812323, 9.254012265481403, 0.05]
mug_V[0].rotation = [0, 0, 0]
arta_D[0].position = [7.395481762298454, 0.1590918902363747, 0.575]
arta_D[0].rotation = [0, 0, 0]
mug_counter_B[0].position = [11.46979793631178, 4.03796296975898, 0.05]
mug_counter_B[0].rotation = [0, 0, 0]
lighting_S[0].position = [14.026152167479632, 7.635778176310806, 0.2]
lighting_S[0].rotation = [0, 0, 0]
magazine_I[0].position = [4.709344335113876, 3.4327752314998405, 0.005]
magazine_I[0].rotation = [0, 0, 0]
lightingb[0].position = [14.528655837403026, 1.536400815230502, 0.175]
lightingb[0].rotation = [0, 0, 0]
art_P[0].position = [2.387568478332811, 5.284856969089452, 0.55]
art_P[0].rotation = [0, 0, 0]
lighting_T[0].position = [13.02583888727559, 9.61751406899435, 0.2]
lighting_T[0].rotation = [0, 0, 0]
dryer_G[0].position = [1.3729472686927713, 9.053739358160792, 0.475]
dryer_G[0].rotation = [0, 0, 0]
magazine_J[0].position = [6.874730882250621, 5.610246327698233, 0.005]
magazine_J[0].rotation = [0, 0, 0]
mug_W[0].position = [12.352832514224708, 3.561484436780371, 0.05]
mug_W[0].rotation = [0, 0, 0]
plant_K[0].position = [13.996178496320692, 0.7928175200037268, 0.85]
plant_K[0].rotation = [0, 0, 0]
lighting_U[0].position = [2.552217911900506, 3.798595553477251, 0.15]
lighting_U[0].rotation = [0, 0, 0]
magazine_K[0].position = [12.869448077228201, 2.0453488782157736, 0.005]
magazine_K[0].rotation = [0, 0, 0]
mug_counter_C[0].position = [5.029975803838508, 6.468494928197788, 0.05]
mug_counter_C[0].rotation = [0, 0, 0]
mug_X[0].position = [11.597067139632568, 9.899359433479749, 0.05]
mug_X[0].rotation = [0, 0, 0]
mug_Y[0].position = [8.363167958385063, 1.0993507998671648, 0.05]
mug_Y[0].rotation = [0, 0, 0]
plantcorner_E[0].position = [5.964551513473952, 8.173474728960361, 0.675]
plantcorner_E[0].rotation = [0, 0, 0]
book_I[0].position = [10.643590580912859, 7.3788926516175675, 0.02]
book_I[0].rotation = [0, 0, 0]
book_J[0].position = [1.4883929003336323, 9.79417765246739, 0.02]
book_J[0].rotation = [0, 0, 0]
lighting_V[0].position = [6.590279695235189, 2.185879843421451, 0.15]
lighting_V[0].rotation = [0, 0, 0]
mugb_A[0].position = [0.9813335004193774, 5.801113639402705, 0.05]
mugb_A[0].rotation = [0, 0, 0]
storage_G[0].position = [10.79652386839753, 6.433955713855193, 0.35]
storage_G[0].rotation = [0, 0, 0]
mug_Z[0].position = [1.7075896316476857, 3.1932000697143668, 0.05]
mug_Z[0].rotation = [0, 0, 0]
dryer_H[0].position = [3.235984300034058, 4.481523431711587, 0.475]
dryer_H[0].rotation = [0, 0, 0]
art_Q[0].position = [10.704367386161659, 7.5807875265819336, 0.55]
art_Q[0].rotation = [0, 0, 0]
plant_L[0].position = [2.380533886286594, 1.0397412980965925, 0.85]
plant_L[0].rotation = [0, 0, 0]
book_K[0].position = [5.834597754841892, 4.107730948173794, 0.02]
book_K[0].rotation = [0, 0, 0]
art_R[0].position = [12.222524753355675, 0.19888814392200693, 0.6]
art_R[0].rotation = [0, 0, 0]
mugd[0].position = [13.396300865446538, 4.40658061387097, 0.05]
mugd[0].rotation = [0, 0, 0]
signage_F[0].position = [0.10165995486895896, 3.807400298224052, 0.45]
signage_F[0].rotation = [0, 0, 0]
signage_G[0].position = [14.58371952397785, 8.021922743450357, 0.425]
signage_G[0].rotation = [0, 0, 0]
mug_group_2_A[0].position = [10.237095450845576, 6.454387820766757, 0.05]
mug_group_2_A[0].rotation = [0, 0, 0]
mug_group_2_B[0].position = [7.559667679352492, 3.8464158683058858, 0.05]
mug_group_2_B[0].rotation = [0, 0, 0]
signage_H[0].position = [0.3395911718426431, 0.33841396319599704, 0.425]
signage_H[0].rotation = [0, 0, 0]
lightsconce_B[0].position = [11.923319966084126, 6.118804838519055, 0.21]
lightsconce_B[0].rotation = [0, 0, 0]
lighting_W[0].position = [8.774037689794547, 0.8090300683714102, 0.2]
lighting_W[0].rotation = [0, 0, 0]
plant_M[0].position = [3.6585541842072193, 4.73197069564957, 0.95]
plant_M[0].rotation = [0, 0, 0]
lighting_X[0].position = [3.709081683391382, 1.5113709937584507, 0.175]
lighting_X[0].rotation = [0, 0, 0]
mug_group_2_C[0].position = [11.706122641325312, 1.770132473135957, 0.05]
mug_group_2_C[0].rotation = [0, 0, 0]
plant_N[0].position = [12.536779351970251, 9.763712250178626, 0.95]
plant_N[0].rotation = [0, 0, 0]
book_L[0].position = [11.719398914025472, 8.841014874607273, 0.02]
book_L[0].rotation = [0, 0, 0]
book_M[0].position = [9.339313479254926, 0.9470282923059603, 0.02]
book_M[0].rotation = [0, 0, 0]
mugb_B[0].position = [14.386679286663957, 2.2775229595695965, 0.05]
mugb_B[0].rotation = [0, 0, 0]
armchair_B[0].position = [9.416259218297876, 4.740949061305454, 0.5]
armchair_B[0].rotation = [0, 0, 0]
storage_H[0].position = [11.758379128049452, 7.929020774224181, 0.35]
storage_H[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed-point constraints preserve the intended zones and clear circulation,
# including a generous unobstructed area in front of the door at (15.00, 5.31).
def _set_pose(asset_obj, position, yaw):
    asset_obj[0].position = list(position)
    asset_obj[0].rotation = [0, 0, yaw]


def _constrain_pose(asset_obj, position, yaw, wall=None, support=None):
    instance = asset_obj[0]

    # Support and wall relationships are the primary semantic constraints.
    if support is not None:
        solver.on_top_of(instance, support[0])
    if wall is not None:
        solver.against_wall(instance, walls[wall])

    # The fixed point supplies a position-based constraint for every object.
    position_anchor = AssetInstance(position=list(position))
    solver.distance_constraint(
        instance, position_anchor, 0.0, 0.0, weight=10
    )

    # A fixed orientation reference supplies an orientation constraint.
    orientation_anchor = AssetInstance(
        position=list(position),
        rotation=[0, 0, yaw],
    )
    solver.align_with(instance, orientation_anchor, angle=0.0)


def _place(asset_obj, position, yaw, wall=None, support=None):
    _set_pose(asset_obj, position, yaw)
    _constrain_pose(
        asset_obj, position, yaw, wall=wall, support=support
    )


# Arrange all washers and dryers as a continuous service bank along the
# south wall. Their fronts face into the room, and the bank ends well before
# the east-wall door and its approach.
_appliances = [
    washer_A, washer_B, washer_C, washer_D,
    washer_E, washer_F, washer_G, washer_H,
    dryer_A, dryer_B, dryer_C, dryer_D,
    dryer_E, dryer_F, dryer_G, dryer_H,
]

for _index, _asset_obj in enumerate(_appliances):
    _position = [0.45 + 0.82 * _index, 0.375, 0.475]
    _place(_asset_obj, _position, radians(90), wall=0)


# Work surfaces form two separated central islands. The service counters are
# on the east wall but remain north and south of the door-clearance zone.
_place(table_A, [5.00, 2.55, 0.45], 0.0)
_place(table_B, [5.00, 7.45, 0.45], 0.0)

_place(counter_A, [14.625, 2.00, 0.525], radians(180), wall=1)
_place(counter_B, [14.625, 8.00, 0.525], radians(180), wall=1)

# Benches and chairs create two waiting areas on the west side, away from
# both the appliance work zone and the east-wall entrance.
_place(bench_A, [0.225, 2.25, 0.24], 0.0, wall=3)
_place(bench_B, [0.225, 7.75, 0.24], 0.0, wall=3)

_place(armchair_A, [1.65, 3.20, 0.50], 0.0)
_place(armchair_B, [1.65, 6.80, 0.50], 0.0)


# Plants form a spaced decorative row along the north wall. The explicit
# ordering makes plant_C (o0018) lie between plant_D (o0024) and plant_F
# (o0068), as required.
_plants_in_order = [
    plant_A,
    plant_B,
    plant_D,       # o0024
    plant_C,       # o0018: middle plant
    plant_F,       # o0068
    plant_E,
    plant_G,
    plant_H,
    plant_I,
    plant_J,
    plant_K,
    plant_L,
    plant_M,
    plant_N,
    plantcorner_A,
    plantcorner_B,
    plantcorner_C,
    plantcorner_D,
    plantcorner_E,
]

_plant_positions = {}
for _index, _asset_obj in enumerate(_plants_in_order):
    _position = [
        0.55 + 0.75 * _index,
        9.65,
        _asset_obj.size[2] / 2.0,
    ]
    _plant_positions[id(_asset_obj)] = _position
    _set_pose(_asset_obj, _position, radians(-90))

# State the important between relationship before the plants' fixed anchors.
solver.distance_constraint(
    plant_C[0], plant_D[0], 0.70, 0.90, weight=10
)
solver.distance_constraint(
    plant_C[0], plant_F[0], 0.70, 0.90, weight=10
)

for _asset_obj in _plants_in_order:
    _position = _plant_positions[id(_asset_obj)]
    _constrain_pose(_asset_obj, _position, radians(-90), wall=2)


# Place cabinets and signs in evenly spaced wall bays. The right-wall bays
# deliberately avoid the door centered at y=5.31.
_wall_displays = [
    storage_A, storage_B, storage_C, storage_D,
    storage_E, storage_F, storage_G, storage_H,
    signage_A, signage_B, signage_C, signage_D,
    signage_E, signage_F, signage_G, signage_H,
]

_display_wall_slots = [
    # Left wall
    (3, 1.20), (3, 3.40), (3, 6.60), (3, 8.80),
    # Right wall, with no fixture in the door opening
    (1, 1.20), (1, 3.40), (1, 7.00), (1, 9.00),
    # South wall
    (0, 1.50), (0, 5.00), (0, 9.00), (0, 13.00),
    # North wall
    (2, 1.50), (2, 5.00), (2, 9.00), (2, 13.00),
]

for _asset_obj, (_wall_index, _along) in zip(
    _wall_displays, _display_wall_slots
):
    _is_storage = _asset_obj in [
        storage_A, storage_B, storage_C, storage_D,
        storage_E, storage_F, storage_G, storage_H,
    ]
    _z = 1.20 if _is_storage else 1.40
    _depth = _asset_obj.size[0]

    if _wall_index == 0:
        _position = [_along, _depth / 2.0, _z]
        _yaw = radians(90)
    elif _wall_index == 1:
        _position = [15.00 - _depth / 2.0, _along, _z]
        _yaw = radians(180)
    elif _wall_index == 2:
        _position = [_along, 10.00 - _depth / 2.0, _z]
        _yaw = radians(-90)
    else:
        _position = [_depth / 2.0, _along, _z]
        _yaw = 0.0

    _place(_asset_obj, _position, _yaw, wall=_wall_index)


# Artwork is mounted above the lower cabinets/signage. It is distributed
# around the perimeter so adjacent frames do not overlap.
_artworks = [
    art_A, art_B, arta_A, art_C, art_D, art_E,
    art_F, arta_B, art_G, arta_C, art_H,
    art_I, art_J, art_K, art_L, art_M,
    art_N, art_O, arta_D, art_P, art_Q, art_R,
]

_art_slots = [
    # South wall
    (0, 1.20), (0, 3.70), (0, 6.20),
    (0, 8.80), (0, 11.40), (0, 13.80),
    # North wall
    (2, 1.20), (2, 3.70), (2, 6.20),
    (2, 8.80), (2, 11.40), (2, 13.80),
    # West wall
    (3, 0.80), (3, 2.60), (3, 4.40),
    (3, 6.20), (3, 8.40),
    # East wall; the gap around y=5.31 is retained
    (1, 0.80), (1, 2.40), (1, 3.80),
    (1, 7.20), (1, 8.80),
]

for _asset_obj, (_wall_index, _along) in zip(_artworks, _art_slots):
    _depth = _asset_obj.size[0]
    _z = 2.75

    if _wall_index == 0:
        _position = [_along, _depth / 2.0, _z]
        _yaw = radians(90)
    elif _wall_index == 1:
        _position = [15.00 - _depth / 2.0, _along, _z]
        _yaw = radians(180)
    elif _wall_index == 2:
        _position = [_along, 10.00 - _depth / 2.0, _z]
        _yaw = radians(-90)
    else:
        _position = [_depth / 2.0, _along, _z]
        _yaw = 0.0

    _place(_asset_obj, _position, _yaw, wall=_wall_index)


# Sconces occupy a high lighting band, above the art and storage. Seven are
# assigned to each wall with consistent spacing.
_lights = [
    lighting_A, lighting_B, lighting_C, lightinga,
    lighting_D, lighting_E, lighting_F, lighting_G,
    lighting_H, lighting_I, lighting_J, lighting_K,
    lighting_L, lighting_M, lighting_N, lighting_O,
    lighting_P, lighting_Q, lighting_R, lighting_S,
    lightingb, lighting_T, lighting_U, lighting_V,
    lighting_W, lighting_X, lightsconce_A, lightsconce_B,
]

_horizontal_light_slots = [1.00, 3.15, 5.30, 7.50, 9.70, 11.85, 14.00]
_vertical_light_slots = [0.70, 2.10, 3.50, 5.00, 6.50, 7.90, 9.30]

for _index, _asset_obj in enumerate(_lights):
    _wall_index = _index // 7
    _slot_index = _index % 7
    _depth = _asset_obj.size[0]
    _z = 3.65

    if _wall_index == 0:
        _along = _horizontal_light_slots[_slot_index]
        _position = [_along, _depth / 2.0, _z]
        _yaw = radians(90)
    elif _wall_index == 1:
        _along = _vertical_light_slots[_slot_index]
        _position = [15.00 - _depth / 2.0, _along, _z]
        _yaw = radians(180)
    elif _wall_index == 2:
        _along = _horizontal_light_slots[_slot_index]
        _position = [_along, 10.00 - _depth / 2.0, _z]
        _yaw = radians(-90)
    else:
        _along = _vertical_light_slots[_slot_index]
        _position = [_depth / 2.0, _along, _z]
        _yaw = 0.0

    _place(_asset_obj, _position, _yaw, wall=_wall_index)


# Every mug, book, and magazine is placed on a work surface. mug_L is listed
# first so that o0076 is specifically assigned to table_A (o0058).
_mugs = [
    mug_L,
    mug_A, mug_B, mug_C, mug_D, mug_E, mug_F, mug_G,
    mug_H, mug_I, mug_J, mug_K, mug_M, mug_N, mug_O,
    mug_P, mug_Q, mug_R, mug_S, mug_T, mug_U, mug_V,
    mug_W, mug_X, mug_Y, mug_Z,
    muga, mugb_A, mugb_B, mugc_A, mugc_B, mugd,
    mug_table_A, mug_table_B, mug_table_C,
    mug_counter_A, mug_counter_B, mug_counter_C,
    mug_group_2_A, mug_group_2_B, mug_group_2_C,
]

_books = [
    book_A, book_B, book_C, book_D, book_E, book_F, book_G,
    book_H, book_I, book_J, book_K, book_L, book_M,
]

_magazines = [
    magazine_A, magazine_B, magazine_C, magazine_D,
    magazine_E, magazine_F, magazine_G, magazine_H,
    magazine_I, magazine_J, magazine_K, magazine_table,
]

_small_items = _mugs + _books + _magazines

# Capacities correspond to compact three-column grids:
# 15 on each table and 18 on each longer counter.
_surface_assignments = [
    (table_A, 15),
    (table_B, 15),
    (counter_A, 18),
    (counter_B, 18),
]

_item_index = 0
for _support, _capacity in _surface_assignments:
    _support_position = _support[0].position
    _support_yaw = _support[0].rotation[2]
    _is_counter = _support in [counter_A, counter_B]

    _row_count = 6 if _is_counter else 5
    _row_start = -0.85 if _is_counter else -0.68
    _row_step = 0.34
    _column_offsets = [-0.24, 0.00, 0.24]

    for _slot in range(_capacity):
        _asset_obj = _small_items[_item_index]
        _column = _slot % 3
        _row = _slot // 3

        # Convert local tabletop offsets to world coordinates so this also
        # works for the counters facing west.
        _local_x = _column_offsets[_column]
        _local_y = _row_start + _row_step * _row
        _cos_yaw = cos(_support_yaw)
        _sin_yaw = sin(_support_yaw)

        _world_x = (
            _support_position[0]
            + _local_x * _cos_yaw
            - _local_y * _sin_yaw
        )
        _world_y = (
            _support_position[1]
            + _local_x * _sin_yaw
            + _local_y * _cos_yaw
        )
        _world_z = (
            _support_position[2]
            + _support.size[2] / 2.0
            + _asset_obj.size[2] / 2.0
        )

        # Turning magazines across the grid gives their wider dimension
        # sufficient clearance from neighboring columns.
        if _asset_obj in _magazines:
            _item_yaw = _support_yaw + radians(90)
        else:
            _item_yaw = _support_yaw

        _place(
            _asset_obj,
            [_world_x, _world_y, _world_z],
            _item_yaw,
            support=_support,
        )
        _item_index += 1

solver.constraints = []
mug_table_C[0].position = [14.625, 2.509999990463257, 1.0999999046325684]
mug_table_C[0].rotation = [0, 0, -3.1290262823329655]
mug_table_C[0].optimize = 2
plantcorner_A[0].position = [11.050000190734863, 9.65999984741211, 0.675000011920929]
plantcorner_A[0].rotation = [0, 0, -1.5682554074221384]
plantcorner_A[0].optimize = 2
table_B[0].position = [5.0, 7.449999809265137, 0.44999998807907104]
table_B[0].rotation = [0, 0, 0.056548670893825266]
table_B[0].optimize = 2
lighting_C[0].position = [5.300000190734863, 0.04059594124555588, 0.20000000298023224]
lighting_C[0].rotation = [0, 0, 1.5733372492341013]
lighting_C[0].optimize = 2
plantcorner_D[0].position = [13.300000190734863, 9.65999984741211, 0.675000011920929]
plantcorner_D[0].rotation = [0, 0, -1.5682554074221384]
plantcorner_D[0].optimize = 2
counter_B[0].position = [14.553023338317871, 8.0, 0.5249999761581421]
counter_B[0].rotation = [0, 0, -3.083045791662811]
counter_B[0].optimize = 2
signage_H[0].position = [13.0, 9.98884105682373, 0.42500001192092896]
signage_H[0].rotation = [0, 0, -1.5682554086442377]
signage_H[0].optimize = 2
magazine_F[0].position = [14.385000228881836, 7.829999923706055, 1.0549999475479126]
magazine_F[0].rotation = [0, 0, -1.5582299555380688]
magazine_F[0].optimize = 2
book_J[0].position = [14.385000228881836, 8.850000381469727, 1.0699999332427979]
book_J[0].rotation = [0, 0, -3.1290262823329655]
book_J[0].optimize = 2
lighting_H[0].position = [14.959449768066406, 2.0999999046325684, 0.15000000596046448]
lighting_H[0].rotation = [0, 0, -3.1390517329949352]
lighting_H[0].optimize = 2
plant_M[0].position = [9.550000190734863, 9.65999984741211, 0.949999988079071]
plant_M[0].rotation = [0, 0, -1.5682554077220645]
plant_M[0].optimize = 2
arta_C[0].position = [8.800000190734863, 9.98884105682373, 0.574999988079071]
arta_C[0].rotation = [0, 0, -1.5682554107885098]
arta_C[0].optimize = 2
magazine_D[0].position = [14.864999771118164, 7.829999923706055, 1.0549999475479126]
magazine_D[0].rotation = [0, 0, -1.5582299555380688]
magazine_D[0].optimize = 2
art_C[0].position = [8.800000190734863, 0.011367769911885262, 0.6000000238418579]
art_C[0].rotation = [0, 0, 1.5733372418791103]
art_C[0].optimize = 2
book_I[0].position = [14.625, 8.850000381469727, 1.0699999332427979]
book_I[0].rotation = [0, 0, -3.1290262823329655]
book_I[0].optimize = 2
magazine_A[0].position = [14.864999771118164, 8.170000076293945, 1.0549999475479126]
magazine_A[0].rotation = [0, 0, -1.5582299555380688]
magazine_A[0].optimize = 2
book_K[0].position = [14.864999771118164, 8.510000228881836, 1.0699999332427979]
book_K[0].rotation = [0, 0, -3.1290262823329655]
book_K[0].optimize = 2
signage_B[0].position = [5.0, 0.011367769911885262, 0.42500001192092896]
signage_B[0].rotation = [0, 0, 1.5733372440233822]
signage_B[0].optimize = 2
magazine_G[0].position = [14.864999771118164, 7.489999771118164, 1.0549999475479126]
magazine_G[0].rotation = [0, 0, -1.5582299555380688]
magazine_G[0].optimize = 2
mug_O[0].position = [5.239999771118164, 3.2300000190734863, 0.949999988079071]
mug_O[0].rotation = [0, 0, 0.01256637125682779]
mug_O[0].optimize = 2
mug_group_2_C[0].position = [14.625, 1.8300000429153442, 1.0999999046325684]
mug_group_2_C[0].rotation = [0, 0, -3.1290262823329655]
mug_group_2_C[0].optimize = 2
dryer_C[0].position = [8.649999618530273, 0.3758881390094757, 0.4749999940395355]
dryer_C[0].rotation = [0, 0, 1.5733372458677286]
dryer_C[0].optimize = 2
armchair_A[0].position = [1.649999976158142, 3.200000047683716, 0.5]
armchair_A[0].rotation = [0, 0, 0.00942477746072377]
armchair_A[0].optimize = 2
lighting_F[0].position = [14.0, 0.06043320894241333, 0.17499999701976776]
lighting_F[0].rotation = [0, 0, 1.573337248311928]
lighting_F[0].optimize = 2
storage_C[0].position = [0.17652399837970734, 6.599999904632568, 0.3499999940395355]
storage_C[0].rotation = [0, 0, 0.0025409114179187954]
storage_C[0].optimize = 2
mug_H[0].position = [5.239999771118164, 2.549999952316284, 0.949999988079071]
mug_H[0].rotation = [0, 0, 0.01256637125682779]
mug_H[0].optimize = 2
plant_L[0].position = [8.800000190734863, 9.65999984741211, 0.8500000238418579]
plant_L[0].rotation = [0, 0, -1.5682554074221384]
plant_L[0].optimize = 2
muga[0].position = [5.239999771118164, 7.789999961853027, 0.949999988079071]
muga[0].rotation = [0, 0, 0.01256637125682779]
muga[0].optimize = 2
lighting_W[0].position = [0.030734146013855934, 5.0, 0.20000000298023224]
lighting_W[0].rotation = [0, 0, 0.002540922439204702]
lighting_W[0].optimize = 2
magazine_J[0].position = [14.864999771118164, 7.150000095367432, 1.0549999475479126]
magazine_J[0].rotation = [0, 0, -1.5582299555380688]
magazine_J[0].optimize = 2
mug_G[0].position = [5.0, 2.549999952316284, 0.949999988079071]
mug_G[0].rotation = [0, 0, 0.01256637125682779]
mug_G[0].optimize = 2
arta_B[0].position = [3.700000047683716, 9.98884105682373, 0.574999988079071]
arta_B[0].rotation = [0, 0, -1.5682554107885098]
arta_B[0].optimize = 2
bench_B[0].position = [0.226904958486557, 7.75, 0.23999999463558197]
bench_B[0].rotation = [0, 0, 0.0025409049851092386]
bench_B[0].optimize = 2
mug_N[0].position = [5.0, 3.2300000190734863, 0.949999988079071]
mug_N[0].rotation = [0, 0, 0.01256637125682779]
mug_N[0].optimize = 2
plant_A[0].position = [0.550000011920929, 9.65999984741211, 0.8500000238418579]
plant_A[0].rotation = [0, 0, -1.5682554074221384]
plant_A[0].optimize = 2
lighting_P[0].position = [5.300000190734863, 9.939545631408691, 0.17499999701976776]
lighting_P[0].rotation = [0, 0, -1.5682554052778654]
lighting_P[0].optimize = 2
plant_N[0].position = [10.300000190734863, 9.65999984741211, 0.949999988079071]
plant_N[0].rotation = [0, 0, -1.5682554077220645]
plant_N[0].optimize = 2
book_A[0].position = [14.385000228881836, 1.8300000429153442, 1.0699999332427979]
book_A[0].rotation = [0, 0, -3.1290262823329655]
book_A[0].optimize = 2
lightsconce_B[0].position = [0.04059594124555588, 9.300000190734863, 0.20999999344348907]
lightsconce_B[0].rotation = [0, 0, 0.002540922439204702]
lightsconce_B[0].optimize = 2
plant_J[0].position = [7.300000190734863, 9.65999984741211, 0.949999988079071]
plant_J[0].rotation = [0, 0, -1.5682554077220645]
plant_J[0].optimize = 2
dryer_H[0].position = [12.75, 0.3758881390094757, 0.4749999940395355]
dryer_H[0].rotation = [0, 0, 1.5733372458677286]
dryer_H[0].optimize = 2
lightinga[0].position = [7.5, 0.04059594124555588, 0.17499999701976776]
lightinga[0].rotation = [0, 0, 1.5733372492341013]
lightinga[0].optimize = 2
book_C[0].position = [14.625, 1.4900000095367432, 1.0699999332427979]
book_C[0].rotation = [0, 0, -3.1290262823329655]
book_C[0].optimize = 2
mug_J[0].position = [5.0, 2.890000104904175, 0.949999988079071]
mug_J[0].rotation = [0, 0, 0.01256637125682779]
mug_J[0].optimize = 2
mug_counter_A[0].position = [14.385000228881836, 2.509999990463257, 1.0999999046325684]
mug_counter_A[0].rotation = [0, 0, -3.1290262823329655]
mug_counter_A[0].optimize = 2
dryer_A[0].position = [7.010000228881836, 0.3758881390094757, 0.4749999940395355]
dryer_A[0].rotation = [0, 0, 1.5733372458677286]
dryer_A[0].optimize = 2
art_I[0].position = [13.800000190734863, 9.978857040405273, 0.6000000238418579]
art_I[0].rotation = [0, 0, -1.5682554107885098]
art_I[0].optimize = 2
armchair_B[0].position = [1.649999976158142, 6.800000190734863, 0.5]
armchair_B[0].rotation = [0, 0, 0.00942477746072377]
armchair_B[0].optimize = 2
storage_E[0].position = [14.82347583770752, 1.2000000476837158, 0.3499999940395355]
storage_E[0].rotation = [0, 0, -3.13905174401622]
storage_E[0].optimize = 2
signage_E[0].position = [1.5, 9.98884105682373, 0.42500001192092896]
signage_E[0].rotation = [0, 0, -1.5682554086442377]
signage_E[0].optimize = 2
plant_C[0].position = [2.799999952316284, 9.65999984741211, 0.8999999761581421]
plant_C[0].rotation = [0, 0, -1.5620341029602698]
plant_C[0].optimize = 2
storage_F[0].position = [14.82347583770752, 3.4000000953674316, 0.3499999940395355]
storage_F[0].rotation = [0, 0, -3.13905174401622]
storage_F[0].optimize = 2
mugc_B[0].position = [14.864999771118164, 2.8499999046325684, 1.0999999046325684]
mugc_B[0].rotation = [0, 0, -3.1290262823329655]
mugc_B[0].optimize = 2
art_M[0].position = [0.011367769911885262, 6.199999809265137, 0.6000000238418579]
art_M[0].rotation = [0, 0, 0.0025409150842135757]
art_M[0].optimize = 2
book_B[0].position = [14.864999771118164, 1.4900000095367432, 1.0699999332427979]
book_B[0].rotation = [0, 0, -3.1290262823329655]
book_B[0].optimize = 2
lighting_N[0].position = [1.0, 9.959449768066406, 0.15000000596046448]
lighting_N[0].rotation = [0, 0, -1.568255406200039]
lighting_N[0].optimize = 2
storage_B[0].position = [0.19101576507091522, 3.4000000953674316, 0.699999988079071]
storage_B[0].rotation = [0, 0, 0.002540916928559797]
storage_B[0].optimize = 2
art_J[0].position = [0.011367769911885262, 0.800000011920929, 0.6000000238418579]
art_J[0].rotation = [0, 0, 0.0025409150842135757]
art_J[0].optimize = 2
art_R[0].position = [14.978857040405273, 8.800000190734863, 0.6000000238418579]
art_R[0].rotation = [0, 0, -3.1390517375834066]
art_R[0].optimize = 2
lighting_U[0].position = [0.050501517951488495, 2.0999999046325684, 0.15000000596046448]
lighting_U[0].rotation = [0, 0, 0.0025409215170312644]
lighting_U[0].optimize = 2
dryer_B[0].position = [7.829999923706055, 0.3758881390094757, 0.4749999940395355]
dryer_B[0].rotation = [0, 0, 1.5733372458677286]
dryer_B[0].optimize = 2
lighting_T[0].position = [0.030734146013855934, 0.699999988079071, 0.20000000298023224]
lighting_T[0].rotation = [0, 0, 0.002540922439204702]
lighting_T[0].optimize = 2
plant_B[0].position = [1.2999999523162842, 9.65999984741211, 0.8999999761581421]
plant_B[0].rotation = [0, 0, -1.5682554086442377]
plant_B[0].optimize = 2
washer_D[0].position = [2.9100000858306885, 0.3758881390094757, 0.4749999940395355]
washer_D[0].rotation = [0, 0, 1.5733372458677286]
washer_D[0].optimize = 2
magazine_E[0].position = [14.625, 7.829999923706055, 1.0549999475479126]
magazine_E[0].rotation = [0, 0, -1.5582299555380688]
magazine_E[0].optimize = 2
mug_Q[0].position = [5.0, 6.769999980926514, 0.949999988079071]
mug_Q[0].rotation = [0, 0, 0.01256637125682779]
mug_Q[0].optimize = 2
book_L[0].position = [14.625, 8.510000228881836, 1.0699999332427979]
book_L[0].rotation = [0, 0, -3.1290262823329655]
book_L[0].optimize = 2
lighting_X[0].position = [0.06043320894241333, 6.5, 0.17499999701976776]
lighting_X[0].rotation = [0, 0, 0.0025409215170312644]
lighting_X[0].optimize = 2
mug_counter_C[0].position = [14.625, 2.1700000762939453, 1.0999999046325684]
mug_counter_C[0].rotation = [0, 0, -3.1290262823329655]
mug_counter_C[0].optimize = 2
mug_F[0].position = [4.760000228881836, 2.549999952316284, 0.949999988079071]
mug_F[0].rotation = [0, 0, 0.01256637125682779]
mug_F[0].optimize = 2
mug_C[0].position = [4.760000228881836, 2.2100000381469727, 0.949999988079071]
mug_C[0].rotation = [0, 0, 0.01256637125682779]
mug_C[0].optimize = 2
signage_F[0].position = [5.0, 9.98884105682373, 0.44999998807907104]
signage_F[0].rotation = [0, 0, -1.5682554086442377]
signage_F[0].optimize = 2
book_F[0].position = [14.625, 1.149999976158142, 1.0699999332427979]
book_F[0].rotation = [0, 0, -3.1290262823329655]
book_F[0].optimize = 2
magazine_K[0].position = [14.625, 7.150000095367432, 1.0549999475479126]
magazine_K[0].rotation = [0, 0, -1.5582299555380688]
magazine_K[0].optimize = 2
lighting_K[0].position = [14.939545631408691, 6.5, 0.17499999701976776]
lighting_K[0].rotation = [0, 0, -3.139051732072762]
lighting_K[0].optimize = 2
art_N[0].position = [0.011367769911885262, 8.399999618530273, 0.550000011920929]
art_N[0].rotation = [0, 0, 0.002540916928559797]
art_N[0].optimize = 2
plant_H[0].position = [5.800000190734863, 9.65999984741211, 0.949999988079071]
plant_H[0].rotation = [0, 0, -1.5682554077220645]
plant_H[0].optimize = 2
plantcorner_C[0].position = [12.550000190734863, 9.65999984741211, 0.675000011920929]
plantcorner_C[0].rotation = [0, 0, -1.5682554074221384]
plantcorner_C[0].optimize = 2
washer_C[0].position = [2.0899999141693115, 0.3758881390094757, 0.4749999940395355]
washer_C[0].rotation = [0, 0, 1.5733372458677286]
washer_C[0].optimize = 2
dryer_F[0].position = [11.109999656677246, 0.3758881390094757, 0.4749999940395355]
dryer_F[0].rotation = [0, 0, 1.5733372458677286]
dryer_F[0].optimize = 2
mug_R[0].position = [5.239999771118164, 6.769999980926514, 0.949999988079071]
mug_R[0].rotation = [0, 0, 0.01256637125682779]
mug_R[0].optimize = 2
washer_G[0].position = [5.369999885559082, 0.3758881390094757, 0.4749999940395355]
washer_G[0].rotation = [0, 0, 1.5733372458677286]
washer_G[0].optimize = 2
lighting_L[0].position = [14.939545631408691, 7.900000095367432, 0.17499999701976776]
lighting_L[0].rotation = [0, 0, -3.139051732072762]
lighting_L[0].optimize = 2
counter_A[0].position = [14.553023338317871, 2.0, 0.5249999761581421]
counter_A[0].rotation = [0, 0, -3.083045791662811]
counter_A[0].optimize = 2
art_G[0].position = [6.199999809265137, 9.978857040405273, 0.6000000238418579]
art_G[0].rotation = [0, 0, -1.5682554107885098]
art_G[0].optimize = 2
book_M[0].position = [14.385000228881836, 8.510000228881836, 1.0699999332427979]
book_M[0].rotation = [0, 0, -3.1290262823329655]
book_M[0].optimize = 2
magazine_C[0].position = [14.385000228881836, 8.170000076293945, 1.0549999475479126]
magazine_C[0].rotation = [0, 0, -1.5582299555380688]
magazine_C[0].optimize = 2
lightingb[0].position = [14.0, 9.95938491821289, 0.17499999701976776]
lightingb[0].rotation = [0, 0, -1.568255404355692]
lightingb[0].optimize = 2
mug_B[0].position = [5.239999771118164, 1.8700000047683716, 0.949999988079071]
mug_B[0].rotation = [0, 0, 0.01256637125682779]
mug_B[0].optimize = 2
mugd[0].position = [14.625, 2.8499999046325684, 1.0999999046325684]
mugd[0].rotation = [0, 0, -3.1290262823329655]
mugd[0].optimize = 2
signage_A[0].position = [1.5, 0.011368179693818092, 0.44999998807907104]
signage_A[0].rotation = [0, 0, 1.5733372449455554]
signage_A[0].optimize = 2
magazine_table[0].position = [14.385000228881836, 7.150000095367432, 1.0549999475479126]
magazine_table[0].rotation = [0, 0, -1.5582299555380688]
magazine_table[0].optimize = 2
art_B[0].position = [3.700000047683716, 0.011367769911885262, 0.6000000238418579]
art_B[0].rotation = [0, 0, 1.5733372418791103]
art_B[0].optimize = 2
bench_A[0].position = [0.226904958486557, 2.25, 0.23999999463558197]
bench_A[0].rotation = [0, 0, 0.0025409049851092386]
bench_A[0].optimize = 2
storage_A[0].position = [0.17652399837970734, 1.2000000476837158, 0.3499999940395355]
storage_A[0].rotation = [0, 0, 0.0025409114179187954]
storage_A[0].optimize = 2
lighting_S[0].position = [11.850000381469727, 9.95938491821289, 0.20000000298023224]
lighting_S[0].rotation = [0, 0, -1.568255404355692]
lighting_S[0].optimize = 2
mug_table_A[0].position = [14.385000228881836, 2.8499999046325684, 1.0999999046325684]
mug_table_A[0].rotation = [0, 0, -3.1290262823329655]
mug_table_A[0].optimize = 2
mug_T[0].position = [5.0, 7.110000133514404, 0.949999988079071]
mug_T[0].rotation = [0, 0, 0.01256637125682779]
mug_T[0].optimize = 2
lighting_E[0].position = [11.850000381469727, 0.06043320894241333, 0.17499999701976776]
lighting_E[0].rotation = [0, 0, 1.573337248311928]
lighting_E[0].optimize = 2
magazine_B[0].position = [14.625, 8.170000076293945, 1.0549999475479126]
magazine_B[0].rotation = [0, 0, -1.5582299555380688]
magazine_B[0].optimize = 2
lighting_M[0].position = [14.95938491821289, 9.300000190734863, 0.17499999701976776]
lighting_M[0].rotation = [0, 0, -3.1390517311505883]
lighting_M[0].optimize = 2
washer_F[0].position = [4.550000190734863, 0.3758881390094757, 0.4749999940395355]
washer_F[0].rotation = [0, 0, 1.5733372458677286]
washer_F[0].optimize = 2
mug_U[0].position = [5.239999771118164, 7.110000133514404, 0.949999988079071]
mug_U[0].rotation = [0, 0, 0.01256637125682779]
mug_U[0].optimize = 2
washer_E[0].position = [3.7300000190734863, 0.3758881390094757, 0.4749999940395355]
washer_E[0].rotation = [0, 0, 1.5733372458677286]
washer_E[0].optimize = 2
art_A[0].position = [1.2000000476837158, 0.011367769911885262, 0.550000011920929]
art_A[0].rotation = [0, 0, 1.5733372437234565]
art_A[0].optimize = 2
lighting_A[0].position = [1.0, 0.050501517951488495, 0.15000000596046448]
lighting_A[0].rotation = [0, 0, 1.573337248311928]
lighting_A[0].optimize = 2
mugb_B[0].position = [5.0, 8.130000114440918, 0.949999988079071]
mugb_B[0].rotation = [0, 0, 0.01256637125682779]
mugb_B[0].optimize = 2
lightsconce_A[0].position = [0.04059594124555588, 7.900000095367432, 0.20999999344348907]
lightsconce_A[0].rotation = [0, 0, 0.002540922439204702]
lightsconce_A[0].optimize = 2
plant_E[0].position = [4.300000190734863, 9.65999984741211, 0.824999988079071]
plant_E[0].rotation = [0, 0, -1.5682554074221384]
plant_E[0].optimize = 2
lighting_V[0].position = [0.04059594124555588, 3.5, 0.15000000596046448]
lighting_V[0].rotation = [0, 0, 0.002540920594857827]
lighting_V[0].optimize = 2
mug_group_2_B[0].position = [14.864999771118164, 1.8300000429153442, 1.0999999046325684]
mug_group_2_B[0].rotation = [0, 0, -3.1290262823329655]
mug_group_2_B[0].optimize = 2
mug_E[0].position = [5.239999771118164, 2.2100000381469727, 0.949999988079071]
mug_E[0].rotation = [0, 0, 0.01256637125682779]
mug_E[0].optimize = 2
lighting_B[0].position = [3.1500000953674316, 0.06043320894241333, 0.17499999701976776]
lighting_B[0].rotation = [0, 0, 1.573337248311928]
lighting_B[0].optimize = 2
book_H[0].position = [14.864999771118164, 8.850000381469727, 1.0699999332427979]
book_H[0].rotation = [0, 0, -3.1290262823329655]
book_H[0].optimize = 2
lighting_R[0].position = [9.699999809265137, 9.939545631408691, 0.17499999701976776]
lighting_R[0].rotation = [0, 0, -1.5682554052778654]
lighting_R[0].optimize = 2
arta_D[0].position = [14.98884105682373, 2.4000000953674316, 0.574999988079071]
arta_D[0].rotation = [0, 0, -3.1390517375834066]
arta_D[0].optimize = 2
plant_K[0].position = [8.050000190734863, 9.65999984741211, 0.8500000238418579]
plant_K[0].rotation = [0, 0, -1.5682554074221384]
plant_K[0].optimize = 2
signage_G[0].position = [9.0, 9.98884105682373, 0.42500001192092896]
signage_G[0].rotation = [0, 0, -1.5682554086442377]
signage_G[0].optimize = 2
art_H[0].position = [11.399999618530273, 9.978857040405273, 0.6000000238418579]
art_H[0].rotation = [0, 0, -1.5682554107885098]
art_H[0].optimize = 2
art_E[0].position = [13.800000190734863, 0.011367769911885262, 0.6000000238418579]
art_E[0].rotation = [0, 0, 1.5733372418791103]
art_E[0].optimize = 2
table_A[0].position = [5.0, 2.549999952316284, 0.44999998807907104]
table_A[0].rotation = [0, 0, 0.056548670893825266]
table_A[0].optimize = 2
lighting_O[0].position = [3.1500000953674316, 9.939545631408691, 0.17499999701976776]
lighting_O[0].rotation = [0, 0, -1.5682554052778654]
lighting_O[0].optimize = 2
lighting_J[0].position = [14.939545631408691, 5.0, 0.17499999701976776]
lighting_J[0].rotation = [0, 0, -3.139051732072762]
lighting_J[0].optimize = 2
mug_group_2_A[0].position = [14.385000228881836, 2.1700000762939453, 1.0999999046325684]
mug_group_2_A[0].rotation = [0, 0, -3.1290262823329655]
mug_group_2_A[0].optimize = 2
mug_counter_B[0].position = [14.864999771118164, 2.1700000762939453, 1.0999999046325684]
mug_counter_B[0].rotation = [0, 0, -3.1290262823329655]
mug_counter_B[0].optimize = 2
lighting_I[0].position = [14.939545631408691, 3.5, 0.17499999701976776]
lighting_I[0].rotation = [0, 0, -3.139051732072762]
lighting_I[0].optimize = 2
storage_D[0].position = [0.19101576507091522, 8.800000190734863, 0.699999988079071]
storage_D[0].rotation = [0, 0, 0.002540916928559797]
storage_D[0].optimize = 2
mugc_A[0].position = [5.239999771118164, 8.130000114440918, 0.949999988079071]
mugc_A[0].rotation = [0, 0, 0.01256637125682779]
mugc_A[0].optimize = 2
washer_H[0].position = [6.190000057220459, 0.3758881390094757, 0.4749999940395355]
washer_H[0].rotation = [0, 0, 1.5733372458677286]
washer_H[0].optimize = 2
art_L[0].position = [0.011367769911885262, 4.400000095367432, 0.6000000238418579]
art_L[0].rotation = [0, 0, 0.0025409150842135757]
art_L[0].optimize = 2
washer_A[0].position = [0.44999998807907104, 0.3758881390094757, 0.4749999940395355]
washer_A[0].rotation = [0, 0, 1.5733372458677286]
washer_A[0].optimize = 2
lighting_Q[0].position = [7.5, 9.95938491821289, 0.17499999701976776]
lighting_Q[0].rotation = [0, 0, -1.568255404355692]
lighting_Q[0].optimize = 2
mug_Y[0].position = [4.760000228881836, 7.789999961853027, 0.949999988079071]
mug_Y[0].rotation = [0, 0, 0.01256637125682779]
mug_Y[0].optimize = 2
mug_W[0].position = [5.0, 7.449999809265137, 0.949999988079071]
mug_W[0].rotation = [0, 0, 0.01256637125682779]
mug_W[0].optimize = 2
mug_L[0].position = [4.760000228881836, 1.8700000047683716, 0.949999988079071]
mug_L[0].rotation = [0, 0, 0.01256637125682779]
mug_L[0].optimize = 2
storage_G[0].position = [14.82347583770752, 7.0, 0.3499999940395355]
storage_G[0].rotation = [0, 0, -3.13905174401622]
storage_G[0].optimize = 2
lighting_G[0].position = [14.939545631408691, 0.699999988079071, 0.17499999701976776]
lighting_G[0].rotation = [0, 0, -3.139051732072762]
lighting_G[0].optimize = 2
lighting_D[0].position = [9.699999809265137, 0.04059594124555588, 0.15000000596046448]
lighting_D[0].rotation = [0, 0, 1.5733372473897544]
lighting_D[0].optimize = 2
art_D[0].position = [11.399999618530273, 0.011367769911885262, 0.6000000238418579]
art_D[0].rotation = [0, 0, 1.5733372418791103]
art_D[0].optimize = 2
mugb_A[0].position = [4.760000228881836, 8.130000114440918, 0.949999988079071]
mugb_A[0].rotation = [0, 0, 0.01256637125682779]
mugb_A[0].optimize = 2
book_D[0].position = [14.385000228881836, 1.4900000095367432, 1.0699999332427979]
book_D[0].rotation = [0, 0, -3.1290262823329655]
book_D[0].optimize = 2
book_E[0].position = [14.864999771118164, 1.149999976158142, 1.0699999332427979]
book_E[0].rotation = [0, 0, -3.1290262823329655]
book_E[0].optimize = 2
washer_B[0].position = [1.2699999809265137, 0.3758881390094757, 0.4749999940395355]
washer_B[0].rotation = [0, 0, 1.5733372458677286]
washer_B[0].optimize = 2
dryer_G[0].position = [11.930000305175781, 0.3758881390094757, 0.4749999940395355]
dryer_G[0].rotation = [0, 0, 1.5733372458677286]
dryer_G[0].optimize = 2
signage_C[0].position = [9.0, 0.011367769911885262, 0.42500001192092896]
signage_C[0].rotation = [0, 0, 1.5733372440233822]
signage_C[0].optimize = 2
art_P[0].position = [14.978983879089355, 3.799999952316284, 0.550000011920929]
art_P[0].rotation = [0, 0, -3.1390517375834066]
art_P[0].optimize = 2
mug_M[0].position = [4.760000228881836, 3.2300000190734863, 0.949999988079071]
mug_M[0].rotation = [0, 0, 0.01256637125682779]
mug_M[0].optimize = 2
mug_A[0].position = [5.0, 1.8700000047683716, 0.949999988079071]
mug_A[0].rotation = [0, 0, 0.01256637125682779]
mug_A[0].optimize = 2
mug_K[0].position = [5.239999771118164, 2.890000104904175, 0.949999988079071]
mug_K[0].rotation = [0, 0, 0.01256637125682779]
mug_K[0].optimize = 2
plant_I[0].position = [6.550000190734863, 9.65999984741211, 0.6499999761581421]
plant_I[0].rotation = [0, 0, -1.5682554074221384]
plant_I[0].optimize = 2
art_F[0].position = [1.2000000476837158, 9.978857040405273, 0.6000000238418579]
art_F[0].rotation = [0, 0, -1.5682554107885098]
art_F[0].optimize = 2
signage_D[0].position = [13.0, 0.011367769911885262, 0.42500001192092896]
signage_D[0].rotation = [0, 0, 1.5733372440233822]
signage_D[0].optimize = 2
book_G[0].position = [14.385000228881836, 1.149999976158142, 1.0699999332427979]
book_G[0].rotation = [0, 0, -3.1290262823329655]
book_G[0].optimize = 2
mug_Z[0].position = [5.0, 7.789999961853027, 0.949999988079071]
mug_Z[0].rotation = [0, 0, 0.01256637125682779]
mug_Z[0].optimize = 2
mug_S[0].position = [4.760000228881836, 7.110000133514404, 0.949999988079071]
mug_S[0].rotation = [0, 0, 0.01256637125682779]
mug_S[0].optimize = 2
plant_D[0].position = [2.049999952316284, 9.65999984741211, 0.824999988079071]
plant_D[0].rotation = [0, 0, -1.5651448047003724]
plant_D[0].optimize = 2
plant_F[0].position = [3.549999952316284, 9.65999984741211, 0.6499999761581421]
plant_F[0].rotation = [0, 0, -1.5651448028559958]
plant_F[0].optimize = 2
plantcorner_B[0].position = [11.800000190734863, 9.65999984741211, 0.675000011920929]
plantcorner_B[0].rotation = [0, 0, -1.5682554074221384]
plantcorner_B[0].optimize = 2
mug_D[0].position = [5.0, 2.2100000381469727, 0.949999988079071]
mug_D[0].rotation = [0, 0, 0.01256637125682779]
mug_D[0].optimize = 2
storage_H[0].position = [14.82347583770752, 9.0, 0.3499999940395355]
storage_H[0].rotation = [0, 0, -3.13905174401622]
storage_H[0].optimize = 2
dryer_E[0].position = [10.289999961853027, 0.3758881390094757, 0.4749999940395355]
dryer_E[0].rotation = [0, 0, 1.5733372458677286]
dryer_E[0].optimize = 2
mug_P[0].position = [4.760000228881836, 6.769999980926514, 0.949999988079071]
mug_P[0].rotation = [0, 0, 0.01256637125682779]
mug_P[0].optimize = 2
art_K[0].position = [0.011367769911885262, 2.5999999046325684, 0.6000000238418579]
art_K[0].rotation = [0, 0, 0.0025409150842135757]
art_K[0].optimize = 2
dryer_D[0].position = [9.470000267028809, 0.3758881390094757, 0.4749999940395355]
dryer_D[0].rotation = [0, 0, 1.5733372458677286]
dryer_D[0].optimize = 2
plant_G[0].position = [5.050000190734863, 9.65999984741211, 0.8999999761581421]
plant_G[0].rotation = [0, 0, -1.5682554086442377]
plant_G[0].optimize = 2
mug_V[0].position = [4.760000228881836, 7.449999809265137, 0.949999988079071]
mug_V[0].rotation = [0, 0, 0.01256637125682779]
mug_V[0].optimize = 2
plantcorner_E[0].position = [14.050000190734863, 9.65999984741211, 0.675000011920929]
plantcorner_E[0].rotation = [0, 0, -1.5682554074221384]
plantcorner_E[0].optimize = 2
art_Q[0].position = [14.978983879089355, 7.199999809265137, 0.550000011920929]
art_Q[0].rotation = [0, 0, -3.1390517375834066]
art_Q[0].optimize = 2
mug_table_B[0].position = [14.864999771118164, 2.509999990463257, 1.0999999046325684]
mug_table_B[0].rotation = [0, 0, -3.1290262823329655]
mug_table_B[0].optimize = 2
art_O[0].position = [14.978857040405273, 0.800000011920929, 0.6000000238418579]
art_O[0].rotation = [0, 0, -3.1390517375834066]
art_O[0].optimize = 2
mug_X[0].position = [5.239999771118164, 7.449999809265137, 0.949999988079071]
mug_X[0].rotation = [0, 0, 0.01256637125682779]
mug_X[0].optimize = 2
magazine_I[0].position = [14.385000228881836, 7.489999771118164, 1.0549999475479126]
magazine_I[0].rotation = [0, 0, -1.5582299555380688]
magazine_I[0].optimize = 2
arta_A[0].position = [6.199999809265137, 0.011367498897016048, 0.574999988079071]
arta_A[0].rotation = [0, 0, 1.5733372428012833]
arta_A[0].optimize = 2
magazine_H[0].position = [14.625, 7.489999771118164, 1.0549999475479126]
magazine_H[0].rotation = [0, 0, -1.5582299555380688]
magazine_H[0].optimize = 2
mug_I[0].position = [4.760000228881836, 2.890000104904175, 0.949999988079071]
mug_I[0].rotation = [0, 0, 0.01256637125682779]
mug_I[0].optimize = 2

