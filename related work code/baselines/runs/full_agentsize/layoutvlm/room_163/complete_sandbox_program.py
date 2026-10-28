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
    Wall(corner1=[6.00, 0.00, 0.00], corner2=[6.00, 8.00, 0.00]),
    Wall(corner1=[6.00, 8.00, 0.00], corner2=[0.00, 8.00, 0.00]),
    Wall(corner1=[0.00, 8.00, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
glassbottle_A = Assets(description="A clear glass bottle with a short neck, rounded shoulders and a slightly cloudy surface, showing a subtle green tint and a worn label.", size=[0.08, 0.08, 0.26], placements=[AssetInstance() for _ in range(1)])
glassbottle_table_A = Assets(description="A cylindrical glass bottle with a thin neck, amber tint, and a weathered label, its surface showing a subtle greenish patina from decades of use.", size=[0.07, 0.07, 0.27], placements=[AssetInstance() for _ in range(1)])
shoppingbag_A = Assets(description="A paper shopping bag with a rectangular base, reinforced handles, and a faded printed logo; the bag is slightly creased and shows a worn edge.", size=[0.18, 0.32, 0.42], placements=[AssetInstance() for _ in range(1)])
cannedveg_A = Assets(description="A glass‑fronted canned vegetable jar with a rounded body, a metal screw‑on lid, and a slightly cloudy green glass that shows a faint vintage label from the 1950s.", size=[0.10, 0.10, 0.16], placements=[AssetInstance() for _ in range(1)])
lightfixture_A = Assets(description="A single piece of thin and upright metal wall light fixture with a frosted glass shade, weathered patina and vintage rivets.", size=[0.22, 0.18, 0.42], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="A wooden shelf with a tall rectangular profile, straight‑edged planks, and a weathered patina that reveals distressed grain; each shelf is supported by metal brackets with riveted details, giving it a vintage industrial charm.", size=[0.40, 1.20, 1.90], placements=[AssetInstance() for _ in range(1)])
beverageitem_A = Assets(description="A weathered patina glass jar with a vintage 1930s label for coffee, tea, or spices, clear rounded body, amber tinted liquid hint, cork stopper with a faded paper tag", size=[0.09, 0.09, 0.18], placements=[AssetInstance() for _ in range(1)])
beverageitem_B = Assets(description="A small metal beverage can with a dented rim and a retro label, cylindrical and slightly corroded for authentic aging", size=[0.07, 0.07, 0.12], placements=[AssetInstance() for _ in range(1)])
beverage_A = Assets(description="A small metal soda can with a slightly dented rim, faded retro graphics and a weathered surface, classic 1950s styling", size=[0.07, 0.07, 0.12], placements=[AssetInstance() for _ in range(1)])
cannedgood_A = Assets(description="A cylindrical metal can with a slightly dented body, faded label graphics and a weathered finish, reminiscent of 1960s food packaging", size=[0.09, 0.09, 0.12], placements=[AssetInstance() for _ in range(1)])
glassbottle_B = Assets(description="A clear glass bottle with a short neck, a slightly chipped rim and a faded paper label, showing a subtle amber tint from age", size=[0.07, 0.07, 0.24], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="A wooden shelf with a tall rectangular profile, straight‑edged planks, and a weathered patina that reveals distressed grain; each shelf is supported by metal brackets with riveted details, giving it a vintage industrial charm.", size=[0.42, 1.40, 2.00], placements=[AssetInstance() for _ in range(1)])
beverageitem_C = Assets(description="A vintage glass beverage bottle with a short stout body, flared lip and a faded label, weathered patina giving an old‑time feel", size=[0.08, 0.08, 0.20], placements=[AssetInstance() for _ in range(1)])
beverageitem_D = Assets(description="A weathered patina glass jar with a vintage 1930s label for coffee, tea, or spices, clear rounded body, amber tinted liquid hint, cork stopper with a faded paper tag", size=[0.09, 0.09, 0.18], placements=[AssetInstance() for _ in range(1)])
beverageitem_E = Assets(description="A small metal beverage can with a dented rim and a retro label, cylindrical and slightly corroded for authentic aging", size=[0.07, 0.07, 0.12], placements=[AssetInstance() for _ in range(1)])
cannedgood_B = Assets(description="A weathered patina metal can with rounded shoulders, embossed vintage label from the 1940s, deep teal background and faded cream lettering, cylindrical shape with a slightly bulging body", size=[0.10, 0.10, 0.15], placements=[AssetInstance() for _ in range(1)])
scale = Assets(description="A vintage mechanical scale with a sturdy wooden base, metal platform, and an analog dial, all bearing a weathered patina and worn paint", size=[0.42, 0.48, 0.58], placements=[AssetInstance() for _ in range(1)])
cannedgood_C = Assets(description="A cylindrical metal can with a slightly dented body, faded label graphics and a weathered finish, reminiscent of 1960s food packaging", size=[0.09, 0.09, 0.12], placements=[AssetInstance() for _ in range(1)])
beverage_B = Assets(description="A small glass beverage bottle with a tapered neck, faintly colored glass and a cracked vintage label, exuding nostalgic charm", size=[0.07, 0.07, 0.23], placements=[AssetInstance() for _ in range(1)])
cannedgood_D = Assets(description="A rectangular metal canned good with a curved top, faded printed graphics and a weathered patina, classic 1950s grocery style", size=[0.08, 0.12, 0.16], placements=[AssetInstance() for _ in range(1)])
cannedgood_E = Assets(description="A rectangular metal can with a weathered patina, rounded shoulders, and a slightly dented lid, showing faded vintage branding from the 1920s‑1970s.", size=[0.09, 0.13, 0.18], placements=[AssetInstance() for _ in range(1)])
glassbottle9b9b_A = Assets(description="A clear amber glass bottle with a short neck, a slightly flared base and a weathered metal cap; the bottle shows a faint embossed logo from the 1930s.", size=[0.08, 0.08, 0.25], placements=[AssetInstance() for _ in range(1)])
stool_A = Assets(description="A metal backless stool with a compact cylindrical seat, slender riveted legs, and a weathered patina that creates a muted, aged metal appearance; the seat features a subtle embossed pattern.", size=[0.38, 0.38, 0.67], placements=[AssetInstance() for _ in range(1)])
cannedveg_B = Assets(description="A glass‑fronted canned vegetable jar with a rounded body, a metal screw‑on lid, and a slightly cloudy green glass that shows a faint vintage label from the 1950s.", size=[0.10, 0.10, 0.16], placements=[AssetInstance() for _ in range(1)])
glassbottle_shelf_A = Assets(description="A vintage glass bottle with a slender cylindrical neck, rounded shoulders and a subtle amber tint, showing a weathered surface", size=[0.08, 0.08, 0.28], placements=[AssetInstance() for _ in range(1)])
glassbottle_C = Assets(description="A cylindrical glass bottle with a thin neck, amber tint, and a weathered label, its surface showing a subtle greenish patina from decades of use.", size=[0.07, 0.07, 0.27], placements=[AssetInstance() for _ in range(1)])
storesign_A = Assets(description="A single piece of thin and upright vintage store sign, rectangular metal board with bold retro lettering, rusted edges and a weathered patina", size=[0.04, 0.80, 0.35], placements=[AssetInstance() for _ in range(1)])
pricetag_A = Assets(description="A thin rectangular metal price tag with a slightly bent edge and faded handwritten numbers, showing a vintage patina", size=[0.02, 0.10, 0.07], placements=[AssetInstance() for _ in range(1)])
cannedvegetable_A = Assets(description="A small metal can with a rounded bottom, a slightly rusted label depicting vegetables, and a dented lid, typical of 1950s grocery items", size=[0.08, 0.08, 0.11], placements=[AssetInstance() for _ in range(1)])
storesign_B = Assets(description="A single piece of thin and upright metal store sign with a distressed paint coat, slightly bent mounting brackets and retro lettering", size=[0.05, 0.75, 0.32], placements=[AssetInstance() for _ in range(1)])
cannedgood_F = Assets(description="A cylindrical metal can with a slightly dented body, faded label graphics and a weathered finish, reminiscent of 1960s food packaging", size=[0.09, 0.09, 0.12], placements=[AssetInstance() for _ in range(1)])
beverage_C = Assets(description="A small glass beverage bottle with a tapered neck, faintly colored glass and a cracked vintage label, exuding nostalgic charm", size=[0.07, 0.07, 0.23], placements=[AssetInstance() for _ in range(1)])
cannedgood_G = Assets(description="A vintage canned good with a weathered patina, rectangular metal body, slightly dented corners, muted pastel label from the 1950s, showing signs of age and rust", size=[0.09, 0.13, 0.17], placements=[AssetInstance() for _ in range(1)])
beverageitem_F = Assets(description="A small metal or glass beverage container with a curved body, aged paint, and a nostalgic label, showing signs of wear and a muted color palette.", size=[0.08, 0.08, 0.15], placements=[AssetInstance() for _ in range(1)])
glassbottle_D = Assets(description="A cylindrical glass bottle with a thin neck, amber tint, and a weathered label, its surface showing a subtle greenish patina from decades of use.", size=[0.07, 0.07, 0.27], placements=[AssetInstance() for _ in range(1)])
cannedgood_H = Assets(description="A vintage canned good with a weathered metal finish, rounded top, faded 1930s label, copper‑toned patina and classic grocery store aesthetic", size=[0.10, 0.10, 0.15], placements=[AssetInstance() for _ in range(1)])
cannedgood_I = Assets(description="A vintage metal canned good with weathered patina, rectangular cylindrical form, retro coffee or tea branding and a slightly bulging seam, typical of 1930s‑1960s packaging", size=[0.10, 0.13, 0.18], placements=[AssetInstance() for _ in range(1)])
beverageitem_G = Assets(description="A weathered patina glass jar with a vintage 1930s label for coffee, tea, or spices, clear rounded body, amber tinted liquid hint, cork stopper with a faded paper tag", size=[0.09, 0.09, 0.18], placements=[AssetInstance() for _ in range(1)])
cannedgood_J = Assets(description="A vintage canned good featuring a weathered metal shell, rounded shoulders, faded coffee or tea label from the 1940s, copper‑toned finish and nostalgic grocery store styling", size=[0.11, 0.11, 0.16], placements=[AssetInstance() for _ in range(1)])
cannedgood_K = Assets(description="A vintage metal canned good with a cylindrical body, slightly bulged sides, faded label and a weathered patina", size=[0.10, 0.10, 0.14], placements=[AssetInstance() for _ in range(1)])
shelf_C = Assets(description="A wooden shelf with a tall rectangular profile, straight‑edged planks, and a weathered patina that reveals distressed grain; each shelf is supported by metal brackets with riveted details, giving it a vintage industrial charm.", size=[0.45, 1.50, 1.90], placements=[AssetInstance() for _ in range(1)])
glassbottle_E = Assets(description="A cylindrical amber glass bottle with a faded vintage label, rounded shoulders and a narrow neck, weathered patina giving it a nostalgic charm", size=[0.08, 0.08, 0.27], placements=[AssetInstance() for _ in range(1)])
glassbottle_F = Assets(description="A vintage glass bottle with weathered patina, tall cylindrical body, gently curved shoulders and a narrow neck, amber tinted glass typical of mid‑century soda bottles", size=[0.07, 0.07, 0.29], placements=[AssetInstance() for _ in range(1)])
glassbottle_G = Assets(description="A vintage glass bottle with a weathered clear glass, slender cylindrical form, embossed label from the 1950s, subtle green tint and nostalgic charm of an old soda bottle", size=[0.07, 0.07, 0.28], placements=[AssetInstance() for _ in range(1)])
cannedgood_table = Assets(description="A rectangular metal can with a weathered patina, rounded shoulders, and a slightly dented lid, showing faded vintage branding from the 1920s‑1970s.", size=[0.09, 0.13, 0.18], placements=[AssetInstance() for _ in range(1)])
beverageitem_H = Assets(description="A vintage glass beverage item with weathered patina, short cylindrical shape, colored glass and a retro label, reminiscent of 1930s‑1960s soda or juice bottles", size=[0.08, 0.08, 0.18], placements=[AssetInstance() for _ in range(1)])
glassbottle9b_A = Assets(description="A clear glass bottle with a short neck and a gently tapered body, showing a faint amber hue and a weathered label, typical of mid‑century beverage containers.", size=[0.08, 0.08, 0.25], placements=[AssetInstance() for _ in range(1)])
cannedgood_L = Assets(description="A vintage metal canned vegetable with weathered patina, squat rectangular cylinder, muted green label and a slightly rusted lid, reflecting 1950s‑1970s produce cans", size=[0.09, 0.12, 0.14], placements=[AssetInstance() for _ in range(1)])
shoppingbag_B = Assets(description="A paper shopping bag with a rectangular base, reinforced handles, and a faded printed logo; the bag is slightly creased and shows a worn edge.", size=[0.18, 0.32, 0.42], placements=[AssetInstance() for _ in range(1)])
crate_A = Assets(description="A wooden produce crate with a sturdy rectangular shape, reinforced iron bands, and a weathered patina that shows grain wear and faded paint, providing an authentic mid‑century market feel.", size=[0.40, 0.60, 0.32], placements=[AssetInstance() for _ in range(1)])
beverage_D = Assets(description="A small glass beverage bottle with a tapered neck, faintly colored glass and a cracked vintage label, exuding nostalgic charm", size=[0.07, 0.07, 0.23], placements=[AssetInstance() for _ in range(1)])
stool_B = Assets(description="A metal backless stool with a compact cylindrical seat, slender riveted legs, and a weathered patina that creates a muted, aged metal appearance; the seat features a subtle embossed pattern.", size=[0.38, 0.38, 0.67], placements=[AssetInstance() for _ in range(1)])
beverageitem_I = Assets(description="A small metal or glass beverage container with a curved body, aged paint, and a nostalgic label, showing signs of wear and a muted color palette.", size=[0.08, 0.08, 0.15], placements=[AssetInstance() for _ in range(1)])
beverageitem_J = Assets(description="A vintage beverage item, small glass bottle with a fluted base, faded label, and a weathered patina, reminiscent of mid‑century soda bottles", size=[0.07, 0.07, 0.21], placements=[AssetInstance() for _ in range(1)])
pricetag_B = Assets(description="A thin rectangular price tag with a slightly curled edge, faded ink lettering, and a weathered metal clip, typical of mid‑century grocery stores", size=[0.03, 0.10, 0.07], placements=[AssetInstance() for _ in range(1)])
beverageitem_K = Assets(description="A small glass soda bottle with a rounded base, narrow neck and a faded retro label, exhibiting a slight green tint and a worn cap.", size=[0.07, 0.07, 0.22], placements=[AssetInstance() for _ in range(1)])
cannedgood_M = Assets(description="A rectangular metal can with a weathered patina, rounded shoulders, and a slightly dented lid, showing faded vintage branding from the 1920s‑1970s.", size=[0.09, 0.13, 0.18], placements=[AssetInstance() for _ in range(1)])
glassbottle_shelf_B = Assets(description="A vintage glass bottle with a slender cylindrical neck, rounded shoulders and a subtle amber tint, showing a weathered surface", size=[0.08, 0.08, 0.28], placements=[AssetInstance() for _ in range(1)])
cratefloor_A = Assets(description="A wooden produce crate with slatted sides, a rectangular shape and a slightly distressed finish; the crate shows nail holes and a faint brown stain.", size=[0.38, 0.58, 0.30], placements=[AssetInstance() for _ in range(1)])
counter = Assets(description="A wooden checkout counter with a rectangular shape, flat top, and weathered patina finish that shows authentic 1920s-1970s aging; the surface is slightly bowed and features hand‑carved brass handles as a unique decorative detail.", size=[0.75, 1.80, 0.95], placements=[AssetInstance() for _ in range(1)])
cannedgood_N = Assets(description="A cylindrical metal can with a slightly dented body, faded label graphics and a weathered finish, reminiscent of 1960s food packaging", size=[0.09, 0.09, 0.12], placements=[AssetInstance() for _ in range(1)])
cannedveg_C = Assets(description="A weathered patina tin can with a curved lid, vintage 1960s vegetable label in muted green, cylindrical body with a slightly tapered bottom", size=[0.09, 0.09, 0.13], placements=[AssetInstance() for _ in range(1)])
crate_B = Assets(description="A wooden produce crate with a sturdy rectangular shape, reinforced iron bands, and a weathered patina that shows grain wear and faded paint, providing an authentic mid‑century market feel.", size=[0.40, 0.60, 0.32], placements=[AssetInstance() for _ in range(1)])
cannedgood_O = Assets(description="A rectangular metal canned good with a curved top, faded printed graphics and a weathered patina, classic 1950s grocery style", size=[0.08, 0.12, 0.16], placements=[AssetInstance() for _ in range(1)])
cannedgood_P = Assets(description="A vintage canned good featuring a weathered metal shell, rounded shoulders, faded coffee or tea label from the 1940s, copper‑toned finish and nostalgic grocery store styling", size=[0.11, 0.11, 0.16], placements=[AssetInstance() for _ in range(1)])
cannedgoodcase = Assets(description="A compact metal canned good with a rounded body, a recessed pull‑tab lid and a muted teal patina; the can bears a faint 1940s label and shows slight dents from handling.", size=[0.10, 0.10, 0.12], placements=[AssetInstance() for _ in range(1)])
cannedveg_D = Assets(description="A vintage canned vegetable with a weathered tin exterior, slightly bulging cylindrical shape, faded green label from the 1960s, patinated surface and nostalgic grocery store appearance", size=[0.09, 0.09, 0.14], placements=[AssetInstance() for _ in range(1)])
glassbottlefloor_A = Assets(description="A clear glass bottle with a short neck and a rounded body, a weathered metal cap and a faint vintage label; the glass is slightly cloudy from age.", size=[0.09, 0.09, 0.27], placements=[AssetInstance() for _ in range(1)])
beverageitem_L = Assets(description="A vintage beverage item, small glass bottle with a fluted base, faded label, and a weathered patina, reminiscent of mid‑century soda bottles", size=[0.07, 0.07, 0.21], placements=[AssetInstance() for _ in range(1)])
lightfixture_B = Assets(description="A vintage pendant light fixture with a curved metal shade, a patinated brass finish and an exposed bulb, giving it an aged industrial look", size=[0.36, 0.36, 0.42], placements=[AssetInstance() for _ in range(1)])
beverageitem_M = Assets(description="A small glass soda bottle with a slender cylindrical shape, a narrow neck, and a faded paper label from the 1960s; the glass has a subtle green tint and a weathered look.", size=[0.07, 0.07, 0.24], placements=[AssetInstance() for _ in range(1)])
glassbottle9b_B = Assets(description="A clear glass bottle with a short neck and a gently tapered body, showing a faint amber hue and a weathered label, typical of mid‑century beverage containers.", size=[0.08, 0.08, 0.25], placements=[AssetInstance() for _ in range(1)])
glassbottle_H = Assets(description="A clear glass bottle with a short neck, a slightly chipped rim and a faded paper label, showing a subtle amber tint from age", size=[0.07, 0.07, 0.24], placements=[AssetInstance() for _ in range(1)])
lightfixture_C = Assets(description="A pendant style vintage light fixture with a frosted glass shade, brass arm and a patinated metal base, cylindrical and slightly tapered", size=[0.25, 0.25, 0.38], placements=[AssetInstance() for _ in range(1)])
lightfixture_D = Assets(description="A pendant style vintage light fixture with a ribbed glass shade, aged copper chain and a weathered metal socket, cylindrical and modestly sized", size=[0.24, 0.24, 0.36], placements=[AssetInstance() for _ in range(1)])
cannedgood_Q = Assets(description="A vintage canned good with a weathered metal finish, rounded top, faded 1930s label, copper‑toned patina and classic grocery store aesthetic", size=[0.10, 0.10, 0.15], placements=[AssetInstance() for _ in range(1)])
glassbottle9b9b_B = Assets(description="A vintage glass bottle with a curved neck, amber tinted glass, chipped rim and a patinated surface, evoking a 1940s soda bottle", size=[0.08, 0.08, 0.27], placements=[AssetInstance() for _ in range(1)])
glassbottle_I = Assets(description="A clear glass bottle with a short neck, rounded shoulders and a slightly cloudy surface, showing a subtle green tint and a worn label.", size=[0.08, 0.08, 0.26], placements=[AssetInstance() for _ in range(1)])
floursack_A = Assets(description="A weathered patina paper sack with a vintage 1950s flour label, soft off‑white color, rectangular and slightly bulging shape, tied with a frayed twine loop", size=[0.16, 0.28, 0.42], placements=[AssetInstance() for _ in range(1)])
glassbottle_J = Assets(description="A cylindrical glass bottle with a thin neck, amber tint, and a weathered label, its surface showing a subtle greenish patina from decades of use.", size=[0.07, 0.07, 0.27], placements=[AssetInstance() for _ in range(1)])
beverageitem_N = Assets(description="A vintage glass beverage item with weathered patina, short cylindrical shape, colored glass and a retro label, reminiscent of 1930s‑1960s soda or juice bottles", size=[0.08, 0.08, 0.18], placements=[AssetInstance() for _ in range(1)])
glassbottle_K = Assets(description="A vintage glass bottle with a slender cylindrical neck, rounded shoulders and a subtle green tint, showing a weathered surface", size=[0.08, 0.08, 0.28], placements=[AssetInstance() for _ in range(1)])
cannedvegetable_B = Assets(description="A small metal can with a rounded bottom, a slightly rusted label depicting vegetables, and a dented lid, typical of 1950s grocery items", size=[0.08, 0.08, 0.11], placements=[AssetInstance() for _ in range(1)])
cannedveg_E = Assets(description="A glass‑fronted canned vegetable jar with a rounded body, a metal screw‑on lid, and a slightly cloudy green glass that shows a faint vintage label from the 1950s.", size=[0.10, 0.10, 0.16], placements=[AssetInstance() for _ in range(1)])
crate_C = Assets(description="A wooden produce crate with a sturdy rectangular shape, reinforced iron bands, and a weathered patina that shows grain wear and faded paint, providing an authentic mid‑century market feel.", size=[0.40, 0.60, 0.32], placements=[AssetInstance() for _ in range(1)])
beverageitem_O = Assets(description="A small glass soda bottle with a slender cylindrical shape, a narrow neck, and a faded paper label from the 1960s; the glass has a subtle green tint and a weathered look.", size=[0.07, 0.07, 0.24], placements=[AssetInstance() for _ in range(1)])
glassbottle_L = Assets(description="A cylindrical clear glass bottle with a cracked vintage label, slightly bulged mid‑section and a short stubby neck, showing a weathered patina", size=[0.09, 0.09, 0.24], placements=[AssetInstance() for _ in range(1)])
beverageitem_P = Assets(description="A vintage glass beverage bottle with a short stout body, flared lip and a faded label, weathered patina giving an old‑time feel", size=[0.08, 0.08, 0.20], placements=[AssetInstance() for _ in range(1)])
pricetag_C = Assets(description="A small rectangular metal price tag with a thin hinged clip, faded ink lettering and a slightly rusted edge, giving it an authentic mid‑century look.", size=[0.03, 0.09, 0.06], placements=[AssetInstance() for _ in range(1)])
cratefloor_B = Assets(description="A wooden produce crate with slatted sides, a rectangular shape and a slightly distressed finish; the crate shows nail holes and a faint brown stain.", size=[0.38, 0.58, 0.30], placements=[AssetInstance() for _ in range(1)])
cannedveg_F = Assets(description="A weathered patina tin can with a curved lid, vintage 1960s vegetable label in muted green, cylindrical body with a slightly tapered bottom", size=[0.09, 0.09, 0.13], placements=[AssetInstance() for _ in range(1)])
pottedplant = Assets(description="A small ceramic pot with a rounded base, glazed finish and a subtle crack, holding a modest leafy plant with a slightly drooping stem, all showing a weathered patina.", size=[0.38, 0.38, 0.75], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="A wooden customer chair with a slightly angled back, turned legs, and a weathered patina that reveals faded varnish and subtle scratches, giving it a nostalgic grocery‑store character.", size=[0.52, 0.47, 0.88], placements=[AssetInstance() for _ in range(1)])
glassbottle_M = Assets(description="A clear glass bottle with a short neck, subtle amber tint, and a worn label, showing a classic vintage beverage design", size=[0.08, 0.08, 0.25], placements=[AssetInstance() for _ in range(1)])
cratefloor_C = Assets(description="A wooden produce crate with slatted sides, rough timber texture, faded paint and a weathered patina, slightly squat and sturdy", size=[0.40, 0.60, 0.30], placements=[AssetInstance() for _ in range(1)])
beverage_E = Assets(description="A small metal soda can with a slightly dented rim, faded retro graphics and a weathered surface, classic 1950s styling", size=[0.07, 0.07, 0.12], placements=[AssetInstance() for _ in range(1)])
cannedgoodaa = Assets(description="A rectangular metal canned good with a slightly tapered profile, a recessed pull‑tab lid and a muted rust‑red finish showing signs of age and faded branding from the 1960s.", size=[0.09, 0.12, 0.16], placements=[AssetInstance() for _ in range(1)])
cannedgood_R = Assets(description="A vintage metal canned good with weathered patina, compact rectangular cylinder, nostalgic branding and a slightly dented top, representing 1920s‑1970s grocery cans", size=[0.09, 0.12, 0.15], placements=[AssetInstance() for _ in range(1)])
floursack_B = Assets(description="A vintage flour sack with weathered canvas texture, rectangular bag shape, muted pastel color, frayed edges and stamped branding from the 1930s, giving a nostalgic grocery store feel", size=[0.15, 0.32, 0.48], placements=[AssetInstance() for _ in range(1)])
glassbottle_N = Assets(description="A cylindrical glass bottle with a thin neck, amber tint, and a weathered label, its surface showing a subtle greenish patina from decades of use.", size=[0.07, 0.07, 0.27], placements=[AssetInstance() for _ in range(1)])
glassbottle_table_B = Assets(description="A cylindrical glass bottle with a thin neck, amber tint, and a weathered label, its surface showing a subtle greenish patina from decades of use.", size=[0.07, 0.07, 0.27], placements=[AssetInstance() for _ in range(1)])
glassbottle9b9b_C = Assets(description="A clear amber glass bottle with a short neck, a slightly flared base and a weathered metal cap; the bottle shows a faint embossed logo from the 1930s.", size=[0.08, 0.08, 0.25], placements=[AssetInstance() for _ in range(1)])
beverageitem_Q = Assets(description="A vintage glass beverage item with weathered patina, short cylindrical shape, colored glass and a retro label, reminiscent of 1930s‑1960s soda or juice bottles", size=[0.08, 0.08, 0.18], placements=[AssetInstance() for _ in range(1)])
cannedgood_S = Assets(description="A vintage metal canned good with weathered patina, rectangular cylindrical shape, faded retro label and slightly dented lid, evoking 1920s‑1970s grocery aisles", size=[0.09, 0.13, 0.17], placements=[AssetInstance() for _ in range(1)])
beverage_F = Assets(description="A slender glass beverage bottle with a narrow neck, a dented shoulder and a faded paper label, giving it a nostalgic patina", size=[0.07, 0.07, 0.26], placements=[AssetInstance() for _ in range(1)])
pricetag_D = Assets(description="A thin rectangular price tag with a slightly curled edge, faded ink lettering, and a weathered metal clip, typical of mid‑century grocery stores", size=[0.03, 0.10, 0.07], placements=[AssetInstance() for _ in range(1)])
glassbottle_O = Assets(description="A vintage glass bottle with a weathered clear glass, slender cylindrical form, embossed label from the 1950s, subtle green tint and nostalgic charm of an old soda bottle", size=[0.07, 0.07, 0.28], placements=[AssetInstance() for _ in range(1)])
glassbottle9b9b_D = Assets(description="A clear amber glass bottle with a short neck, a slightly flared base and a weathered metal cap; the bottle shows a faint embossed logo from the 1930s.", size=[0.08, 0.08, 0.25], placements=[AssetInstance() for _ in range(1)])
shoppingbag_C = Assets(description="A paper shopping bag with a rectangular base, reinforced handles, and a faded printed logo; the bag is slightly creased and shows a worn edge.", size=[0.18, 0.32, 0.42], placements=[AssetInstance() for _ in range(1)])
cannedvegetable_C = Assets(description="A small metal can with a rounded bottom, a slightly rusted label depicting vegetables, and a dented lid, typical of 1950s grocery items", size=[0.08, 0.08, 0.11], placements=[AssetInstance() for _ in range(1)])
beverageitem_R = Assets(description="A small glass soda bottle with a rounded base, narrow neck and a faded retro label, exhibiting a slight green tint and a worn cap.", size=[0.07, 0.07, 0.22], placements=[AssetInstance() for _ in range(1)])
cannedgood_T = Assets(description="A vintage canned good with a weathered metal finish, rounded top, faded 1930s label, copper‑toned patina and classic grocery store aesthetic", size=[0.10, 0.10, 0.15], placements=[AssetInstance() for _ in range(1)])
cratefloor_D = Assets(description="A wooden produce crate with slatted sides, rough timber texture, faded paint and a weathered patina, slightly squat and sturdy", size=[0.40, 0.60, 0.30], placements=[AssetInstance() for _ in range(1)])
beverage_G = Assets(description="A slender glass beverage bottle with a narrow neck, a dented shoulder and a faded paper label, giving it a nostalgic patina", size=[0.07, 0.07, 0.26], placements=[AssetInstance() for _ in range(1)])
beverageitem_S = Assets(description="A small glass soda bottle with a slender cylindrical shape, a narrow neck, and a faded paper label from the 1960s; the glass has a subtle green tint and a weathered look.", size=[0.07, 0.07, 0.24], placements=[AssetInstance() for _ in range(1)])
glassbottle9b_C = Assets(description="A clear glass bottle with a short neck and a gently tapered body, showing a faint amber hue and a weathered label, typical of mid‑century beverage containers.", size=[0.08, 0.08, 0.25], placements=[AssetInstance() for _ in range(1)])
cratefloor_E = Assets(description="A wooden produce crate with slatted sides, rough timber texture, faded paint and a weathered patina, slightly squat and sturdy", size=[0.40, 0.60, 0.30], placements=[AssetInstance() for _ in range(1)])
floursack_C = Assets(description="A weathered patina paper sack with a vintage 1950s flour label, soft off‑white color, rectangular and slightly bulging shape, tied with a frayed twine loop", size=[0.16, 0.28, 0.42], placements=[AssetInstance() for _ in range(1)])
beverageitem_T = Assets(description="A vintage beverage item, small glass bottle with a fluted base, faded label, and a weathered patina, reminiscent of mid‑century soda bottles", size=[0.07, 0.07, 0.21], placements=[AssetInstance() for _ in range(1)])
cannedveg_G = Assets(description="A vintage canned vegetable with a weathered tin exterior, slightly bulging cylindrical shape, faded green label from the 1960s, patinated surface and nostalgic grocery store appearance", size=[0.09, 0.09, 0.14], placements=[AssetInstance() for _ in range(1)])
cannedvegetable_9b_A = Assets(description="A metal canned vegetable container with a slightly bulged body, muted label colors and a patinated surface, evoking a 1950s grocery aesthetic.", size=[0.09, 0.09, 0.13], placements=[AssetInstance() for _ in range(1)])
cannedveg9b9b_A = Assets(description="A vintage canned vegetable jar with a glass body, rust‑tinted metal lid, and a slightly warped shape, showing a weathered patina and faded label", size=[0.10, 0.10, 0.16], placements=[AssetInstance() for _ in range(1)])
cannedgood_U = Assets(description="A weathered patina metal can with rounded shoulders, embossed vintage label from the 1940s, deep teal background and faded cream lettering, cylindrical shape with a slightly bulging body", size=[0.10, 0.10, 0.15], placements=[AssetInstance() for _ in range(1)])
lightfixture_E = Assets(description="A vintage pendant light fixture with a cylindrical metal shade, exposed filament bulbs, and a patinated bronze finish, giving it an aged industrial look.", size=[0.34, 0.34, 0.40], placements=[AssetInstance() for _ in range(1)])
cannedgood_V = Assets(description="A weathered patina metal can with rounded shoulders, embossed vintage label from the 1940s, deep teal background and faded cream lettering, cylindrical shape with a slightly bulging body", size=[0.10, 0.10, 0.15], placements=[AssetInstance() for _ in range(1)])
case = Assets(description="A glass pastry display case with a sleek rectangular frame, curved glass front panels, and a weathered metal edging that carries a muted patina, evoking a nostalgic grocery‑store vibe.", size=[0.70, 1.50, 1.25], placements=[AssetInstance() for _ in range(1)])
shelf_D = Assets(description="A wooden shelf with a tall rectangular profile, straight‑edged planks, and a weathered patina that reveals distressed grain; each shelf is supported by metal brackets with riveted details, giving it a vintage industrial charm.", size=[0.42, 1.30, 1.95], placements=[AssetInstance() for _ in range(1)])
glassbottle_P = Assets(description="A clear glass bottle with a short neck, subtle amber tint, and a worn label, showing a classic vintage beverage design", size=[0.08, 0.08, 0.25], placements=[AssetInstance() for _ in range(1)])
glassbottle_Q = Assets(description="A vintage glass bottle with a slender cylindrical neck, rounded shoulders and a subtle green tint, showing a weathered surface", size=[0.08, 0.08, 0.28], placements=[AssetInstance() for _ in range(1)])
glassbottlefloor_B = Assets(description="A clear glass bottle with a short neck and a rounded body, a weathered metal cap and a faint vintage label; the glass is slightly cloudy from age.", size=[0.09, 0.09, 0.27], placements=[AssetInstance() for _ in range(1)])
cannedvegetable_9b_B = Assets(description="A metal canned vegetable container with a slightly bulged body, muted label colors and a patinated surface, evoking a 1950s grocery aesthetic.", size=[0.09, 0.09, 0.13], placements=[AssetInstance() for _ in range(1)])
cannedgood_W = Assets(description="A vintage metal canned good with weathered patina, rectangular cylindrical form, retro coffee or tea branding and a slightly bulging seam, typical of 1930s‑1960s packaging", size=[0.10, 0.13, 0.18], placements=[AssetInstance() for _ in range(1)])
shoppingbag_counter = Assets(description="A rectangular canvas shopping bag with frayed handles, a faded vintage logo, and a weathered patina, the fabric appearing soft and slightly torn.", size=[0.18, 0.38, 0.42], placements=[AssetInstance() for _ in range(1)])
glassbottle_R = Assets(description="A vintage glass bottle with weathered patina, tall cylindrical body, gently curved shoulders and a narrow neck, amber tinted glass typical of mid‑century soda bottles", size=[0.07, 0.07, 0.29], placements=[AssetInstance() for _ in range(1)])
beverageitem_U = Assets(description="A small glass soda bottle with a rounded base, narrow neck and a faded retro label, exhibiting a slight green tint and a worn cap.", size=[0.07, 0.07, 0.22], placements=[AssetInstance() for _ in range(1)])
beverageitem_V = Assets(description="A vintage beverage item with a weathered metal or glass container, compact rectangular shape, faded 1970s branding, muted pastel hue and nostalgic grocery store vibe", size=[0.07, 0.11, 0.15], placements=[AssetInstance() for _ in range(1)])
cannedgood_X = Assets(description="A vintage metal canned good with weathered patina, rectangular cylindrical shape, faded retro label and slightly dented lid, evoking 1920s‑1970s grocery aisles", size=[0.09, 0.13, 0.17], placements=[AssetInstance() for _ in range(1)])
beverageitem_W = Assets(description="A weathered patina glass jar with a vintage 1930s label for coffee, tea, or spices, clear rounded body, amber tinted liquid hint, cork stopper with a faded paper tag", size=[0.09, 0.09, 0.18], placements=[AssetInstance() for _ in range(1)])
storesign_C = Assets(description="A single piece of thin and upright metal store sign with a retro etched lettering, rectangular, rust‑stained and slightly warped", size=[0.04, 0.70, 0.32], placements=[AssetInstance() for _ in range(1)])
glassbottlefloor_C = Assets(description="A clear glass bottle with a short neck and a rounded body, a weathered metal cap and a faint vintage label; the glass is slightly cloudy from age.", size=[0.09, 0.09, 0.27], placements=[AssetInstance() for _ in range(1)])
cannedgood_Y = Assets(description="A small rectangular tin canned good with a curved lid, faded retro label and a weathered metal surface, compact and squat", size=[0.08, 0.11, 0.13], placements=[AssetInstance() for _ in range(1)])
cannedveg_H = Assets(description="A glass‑fronted canned vegetable jar with a rounded body, a metal screw‑on lid, and a slightly cloudy green glass that shows a faint vintage label from the 1950s.", size=[0.10, 0.10, 0.16], placements=[AssetInstance() for _ in range(1)])
cannedgood_Z = Assets(description="A weathered patina metal can with rounded shoulders, embossed vintage label from the 1940s, deep teal background and faded cream lettering, cylindrical shape with a slightly bulging body", size=[0.10, 0.10, 0.15], placements=[AssetInstance() for _ in range(1)])
storesign_D = Assets(description="A single piece of thin and upright metal store sign with a retro painted logo, slightly rusted corners and a hanging bracket", size=[0.05, 0.75, 0.35], placements=[AssetInstance() for _ in range(1)])
beverageitem_X = Assets(description="A vintage glass beverage bottle with a short stout body, flared lip and a faded label, weathered patina giving an old‑time feel", size=[0.08, 0.08, 0.20], placements=[AssetInstance() for _ in range(1)])
cannedgood_group_2_A = Assets(description="A vintage metal canned good with weathered patina, rectangular cylindrical shape, faded retro label and slightly dented lid, evoking 1920s‑1970s grocery aisles", size=[0.09, 0.13, 0.17], placements=[AssetInstance() for _ in range(1)])
cannedgood_group_2_B = Assets(description="A weathered patina metal can with rounded shoulders, embossed vintage label from the 1940s, deep teal background and faded cream lettering, cylindrical shape with a slightly bulging body", size=[0.10, 0.10, 0.15], placements=[AssetInstance() for _ in range(1)])
cratefloor_F = Assets(description="A wooden produce crate with slatted sides, a rectangular shape and a slightly distressed finish; the crate shows nail holes and a faint brown stain.", size=[0.38, 0.58, 0.30], placements=[AssetInstance() for _ in range(1)])
glassbottle9b9b_E = Assets(description="A vintage glass bottle with a curved neck, amber tinted glass, chipped rim and a patinated surface, evoking a 1940s soda bottle", size=[0.08, 0.08, 0.27], placements=[AssetInstance() for _ in range(1)])
glassbottle_S = Assets(description="A clear glass bottle with a short neck, a slightly chipped rim and a faded paper label, showing a subtle amber tint from age", size=[0.07, 0.07, 0.24], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="A small wooden sampling table with a low‑slung rectangular top, rounded corners, and a weathered patina that shows a distressed finish; a recessed groove runs along the edge for a subtle vintage detail.", size=[0.65, 1.00, 0.75], placements=[AssetInstance() for _ in range(1)])
glassbottlefloor_D = Assets(description="A clear glass bottle with a short neck and a rounded body, a weathered metal cap and a faint vintage label; the glass is slightly cloudy from age.", size=[0.09, 0.09, 0.27], placements=[AssetInstance() for _ in range(1)])
glassbottle_T = Assets(description="A clear glass bottle with a short neck, a slightly chipped rim and a faded paper label, showing a subtle amber tint from age", size=[0.07, 0.07, 0.24], placements=[AssetInstance() for _ in range(1)])
glassbottle_U = Assets(description="A cylindrical amber glass bottle with a faded vintage label, rounded shoulders and a narrow neck, weathered patina giving it a nostalgic charm", size=[0.08, 0.08, 0.27], placements=[AssetInstance() for _ in range(1)])
cannedvegetable_D = Assets(description="A small metal can with a rounded bottom, a slightly rusted label depicting vegetables, and a dented lid, typical of 1950s grocery items", size=[0.08, 0.08, 0.11], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="A wooden customer chair with a slightly angled back, turned legs, and a weathered patina that reveals faded varnish and subtle scratches, giving it a nostalgic grocery‑store character.", size=[0.52, 0.47, 0.88], placements=[AssetInstance() for _ in range(1)])
cannedgood_group_2_C = Assets(description="A vintage canned good with a weathered patina, rectangular metal body, slightly dented corners, muted pastel label from the 1950s, showing signs of age and rust", size=[0.09, 0.13, 0.17], placements=[AssetInstance() for _ in range(1)])
signcoffee = Assets(description="A single piece of thin and upright sign with a weathered enamel surface, faded teal lettering reading 'Coffee & Tea', rectangular shape with a subtle rounded top", size=[0.04, 0.55, 0.28], placements=[AssetInstance() for _ in range(1)])
cannedveg_I = Assets(description="A vintage canned vegetable with a weathered tin exterior, slightly bulging cylindrical shape, faded green label from the 1960s, patinated surface and nostalgic grocery store appearance", size=[0.09, 0.09, 0.14], placements=[AssetInstance() for _ in range(1)])
storesign_E = Assets(description="A single piece of thin and upright metal store sign with a retro script reading 'General Store', painted in muted teal and slightly rusted at the edges.", size=[0.04, 0.90, 0.38], placements=[AssetInstance() for _ in range(1)])
beverageitem_Y = Assets(description="A small glass soda bottle with a slender cylindrical shape, a narrow neck, and a faded paper label from the 1960s; the glass has a subtle green tint and a weathered look.", size=[0.07, 0.07, 0.24], placements=[AssetInstance() for _ in range(1)])
cannedgood_group_2_D = Assets(description="A vintage metal canned good with weathered patina, rectangular cylindrical form, retro coffee or tea branding and a slightly bulging seam, typical of 1930s‑1960s packaging", size=[0.10, 0.13, 0.18], placements=[AssetInstance() for _ in range(1)])
storesign_F = Assets(description="A single piece of thin and upright vintage store sign, rectangular metal board with bold retro lettering, rusted edges and a weathered patina", size=[0.04, 0.80, 0.35], placements=[AssetInstance() for _ in range(1)])
lightfixture_F = Assets(description="A single piece of thin and upright metal wall light fixture with a frosted glass shade, weathered patina and vintage rivets.", size=[0.22, 0.18, 0.42], placements=[AssetInstance() for _ in range(1)])
beverage_H = Assets(description="A slender glass beverage bottle with a narrow neck, a dented shoulder and a faded paper label, giving it a nostalgic patina", size=[0.07, 0.07, 0.26], placements=[AssetInstance() for _ in range(1)])
beverage_I = Assets(description="A small glass beverage bottle with a tapered neck, faintly colored glass and a cracked vintage label, exuding nostalgic charm", size=[0.07, 0.07, 0.23], placements=[AssetInstance() for _ in range(1)])
cannedveg_J = Assets(description="A vintage canned vegetable with a weathered tin exterior, slightly bulging cylindrical shape, faded green label from the 1960s, patinated surface and nostalgic grocery store appearance", size=[0.09, 0.09, 0.14], placements=[AssetInstance() for _ in range(1)])
cannedgood_group_2_E = Assets(description="A vintage metal canned good with weathered patina, rectangular cylindrical form, retro coffee or tea branding and a slightly bulging seam, typical of 1930s‑1960s packaging", size=[0.10, 0.13, 0.18], placements=[AssetInstance() for _ in range(1)])
glassbottlefloor_E = Assets(description="A clear glass bottle with a short neck and a rounded body, a weathered metal cap and a faint vintage label; the glass is slightly cloudy from age.", size=[0.09, 0.09, 0.27], placements=[AssetInstance() for _ in range(1)])
lightfixture_G = Assets(description="A vintage pendant light fixture with a curved metal shade, a patinated brass finish and an exposed bulb, giving it an aged industrial look", size=[0.36, 0.36, 0.42], placements=[AssetInstance() for _ in range(1)])
cannedveg9b9b_B = Assets(description="A vintage canned vegetable jar with a glass body, rust‑tinted metal lid, and a slightly warped shape, showing a weathered patina and faded label", size=[0.10, 0.10, 0.16], placements=[AssetInstance() for _ in range(1)])
beverageitem_Z = Assets(description="A small metal or glass beverage container with a curved body, aged paint, and a nostalgic label, showing signs of wear and a muted color palette.", size=[0.08, 0.08, 0.15], placements=[AssetInstance() for _ in range(1)])
glassbottle_V = Assets(description="A cylindrical glass bottle with a thin neck, amber tint, and a weathered label, its surface showing a subtle greenish patina from decades of use.", size=[0.07, 0.07, 0.27], placements=[AssetInstance() for _ in range(1)])
glassbottle_W = Assets(description="A vintage glass bottle with a slightly rounded shoulders, amber tinted glass, a narrow neck and a dented metal cap, showing a faint label from the 1950s", size=[0.08, 0.08, 0.27], placements=[AssetInstance() for _ in range(1)])
cannedgood_group_2_F = Assets(description="A vintage canned good with a weathered patina, rectangular metal body, slightly dented corners, muted pastel label from the 1950s, showing signs of age and rust", size=[0.09, 0.13, 0.17], placements=[AssetInstance() for _ in range(1)])
storesign_G = Assets(description="A single piece of thin and upright metal store sign with a retro painted logo, slightly rusted corners and a hanging bracket", size=[0.05, 0.75, 0.35], placements=[AssetInstance() for _ in range(1)])
crate_D = Assets(description="A wooden produce crate with a sturdy rectangular shape, reinforced iron bands, and a weathered patina that shows grain wear and faded paint, providing an authentic mid‑century market feel.", size=[0.40, 0.60, 0.32], placements=[AssetInstance() for _ in range(1)])
cannedgood_group_2_G = Assets(description="A small rectangular tin canned good with a curved lid, faded retro label and a weathered metal surface, compact and squat", size=[0.08, 0.11, 0.13], placements=[AssetInstance() for _ in range(1)])
beverageitem_group_2 = Assets(description="A small glass soda bottle with a slender cylindrical shape, a narrow neck, and a faded paper label from the 1960s; the glass has a subtle green tint and a weathered look.", size=[0.07, 0.07, 0.24], placements=[AssetInstance() for _ in range(1)])
glassbottle_X = Assets(description="A clear glass bottle with a short neck, a slightly chipped rim and a faded paper label, showing a subtle amber tint from age", size=[0.07, 0.07, 0.24], placements=[AssetInstance() for _ in range(1)])
cannedgood_group_2_H = Assets(description="A vintage metal canned good with weathered patina, rectangular cylindrical form, retro coffee or tea branding and a slightly bulging seam, typical of 1930s‑1960s packaging", size=[0.10, 0.13, 0.18], placements=[AssetInstance() for _ in range(1)])
glassbottle_Y = Assets(description="A clear glass bottle with a short neck, a slightly chipped rim and a faded paper label, showing a subtle amber tint from age", size=[0.07, 0.07, 0.24], placements=[AssetInstance() for _ in range(1)])
sign = Assets(description="A single piece of thin and upright wooden sign with a painted retro grocery logo, slightly warped and weathered at the edges", size=[0.04, 0.60, 0.30], placements=[AssetInstance() for _ in range(1)])
cannedgood_group_2_I = Assets(description="A weathered patina metal can with rounded shoulders, embossed vintage label from the 1940s, deep teal background and faded cream lettering, cylindrical shape with a slightly bulging body", size=[0.10, 0.10, 0.15], placements=[AssetInstance() for _ in range(1)])
cannedvegetable_E = Assets(description="A small metal can with a rounded bottom, a slightly rusted label depicting vegetables, and a dented lid, typical of 1950s grocery items", size=[0.08, 0.08, 0.11], placements=[AssetInstance() for _ in range(1)])
beverage_J = Assets(description="A slender glass beverage bottle with a narrow neck, a dented shoulder and a faded paper label, giving it a nostalgic patina", size=[0.07, 0.07, 0.26], placements=[AssetInstance() for _ in range(1)])
storesign_H = Assets(description="A single piece of thin and upright metal store sign with a retro script reading 'General Store', painted in muted teal and slightly rusted at the edges.", size=[0.04, 0.90, 0.38], placements=[AssetInstance() for _ in range(1)])
lightfixture_H = Assets(description="A vintage pendant light fixture with a cylindrical metal shade, exposed filament bulbs, and a patinated bronze finish, giving it an aged industrial look.", size=[0.34, 0.34, 0.40], placements=[AssetInstance() for _ in range(1)])
storesign_I = Assets(description="A single piece of thin and upright vintage store sign with a rectangular shape, hand‑painted lettering and a weathered metal frame", size=[0.05, 0.85, 0.38], placements=[AssetInstance() for _ in range(1)])

glassbottle_A[0].instance_id = 'glassbottle_A_0'
glassbottle_table_A[0].instance_id = 'glassbottle_table_A_0'
shoppingbag_A[0].instance_id = 'shoppingbag_A_0'
cannedveg_A[0].instance_id = 'cannedveg_A_0'
lightfixture_A[0].instance_id = 'lightfixture_A_0'
shelf_A[0].instance_id = 'shelf_A_0'
beverageitem_A[0].instance_id = 'beverageitem_A_0'
beverageitem_B[0].instance_id = 'beverageitem_B_0'
beverage_A[0].instance_id = 'beverage_A_0'
cannedgood_A[0].instance_id = 'cannedgood_A_0'
glassbottle_B[0].instance_id = 'glassbottle_B_0'
shelf_B[0].instance_id = 'shelf_B_0'
beverageitem_C[0].instance_id = 'beverageitem_C_0'
beverageitem_D[0].instance_id = 'beverageitem_D_0'
beverageitem_E[0].instance_id = 'beverageitem_E_0'
cannedgood_B[0].instance_id = 'cannedgood_B_0'
scale[0].instance_id = 'scale_0'
cannedgood_C[0].instance_id = 'cannedgood_C_0'
beverage_B[0].instance_id = 'beverage_B_0'
cannedgood_D[0].instance_id = 'cannedgood_D_0'
cannedgood_E[0].instance_id = 'cannedgood_E_0'
glassbottle9b9b_A[0].instance_id = 'glassbottle9b9b_A_0'
stool_A[0].instance_id = 'stool_A_0'
cannedveg_B[0].instance_id = 'cannedveg_B_0'
glassbottle_shelf_A[0].instance_id = 'glassbottle_shelf_A_0'
glassbottle_C[0].instance_id = 'glassbottle_C_0'
storesign_A[0].instance_id = 'storesign_A_0'
pricetag_A[0].instance_id = 'pricetag_A_0'
cannedvegetable_A[0].instance_id = 'cannedvegetable_A_0'
storesign_B[0].instance_id = 'storesign_B_0'
cannedgood_F[0].instance_id = 'cannedgood_F_0'
beverage_C[0].instance_id = 'beverage_C_0'
cannedgood_G[0].instance_id = 'cannedgood_G_0'
beverageitem_F[0].instance_id = 'beverageitem_F_0'
glassbottle_D[0].instance_id = 'glassbottle_D_0'
cannedgood_H[0].instance_id = 'cannedgood_H_0'
cannedgood_I[0].instance_id = 'cannedgood_I_0'
beverageitem_G[0].instance_id = 'beverageitem_G_0'
cannedgood_J[0].instance_id = 'cannedgood_J_0'
cannedgood_K[0].instance_id = 'cannedgood_K_0'
shelf_C[0].instance_id = 'shelf_C_0'
glassbottle_E[0].instance_id = 'glassbottle_E_0'
glassbottle_F[0].instance_id = 'glassbottle_F_0'
glassbottle_G[0].instance_id = 'glassbottle_G_0'
cannedgood_table[0].instance_id = 'cannedgood_table_0'
beverageitem_H[0].instance_id = 'beverageitem_H_0'
glassbottle9b_A[0].instance_id = 'glassbottle9b_A_0'
cannedgood_L[0].instance_id = 'cannedgood_L_0'
shoppingbag_B[0].instance_id = 'shoppingbag_B_0'
crate_A[0].instance_id = 'crate_A_0'
beverage_D[0].instance_id = 'beverage_D_0'
stool_B[0].instance_id = 'stool_B_0'
beverageitem_I[0].instance_id = 'beverageitem_I_0'
beverageitem_J[0].instance_id = 'beverageitem_J_0'
pricetag_B[0].instance_id = 'pricetag_B_0'
beverageitem_K[0].instance_id = 'beverageitem_K_0'
cannedgood_M[0].instance_id = 'cannedgood_M_0'
glassbottle_shelf_B[0].instance_id = 'glassbottle_shelf_B_0'
cratefloor_A[0].instance_id = 'cratefloor_A_0'
counter[0].instance_id = 'counter_0'
cannedgood_N[0].instance_id = 'cannedgood_N_0'
cannedveg_C[0].instance_id = 'cannedveg_C_0'
crate_B[0].instance_id = 'crate_B_0'
cannedgood_O[0].instance_id = 'cannedgood_O_0'
cannedgood_P[0].instance_id = 'cannedgood_P_0'
cannedgoodcase[0].instance_id = 'cannedgoodcase_0'
cannedveg_D[0].instance_id = 'cannedveg_D_0'
glassbottlefloor_A[0].instance_id = 'glassbottlefloor_A_0'
beverageitem_L[0].instance_id = 'beverageitem_L_0'
lightfixture_B[0].instance_id = 'lightfixture_B_0'
beverageitem_M[0].instance_id = 'beverageitem_M_0'
glassbottle9b_B[0].instance_id = 'glassbottle9b_B_0'
glassbottle_H[0].instance_id = 'glassbottle_H_0'
lightfixture_C[0].instance_id = 'lightfixture_C_0'
lightfixture_D[0].instance_id = 'lightfixture_D_0'
cannedgood_Q[0].instance_id = 'cannedgood_Q_0'
glassbottle9b9b_B[0].instance_id = 'glassbottle9b9b_B_0'
glassbottle_I[0].instance_id = 'glassbottle_I_0'
floursack_A[0].instance_id = 'floursack_A_0'
glassbottle_J[0].instance_id = 'glassbottle_J_0'
beverageitem_N[0].instance_id = 'beverageitem_N_0'
glassbottle_K[0].instance_id = 'glassbottle_K_0'
cannedvegetable_B[0].instance_id = 'cannedvegetable_B_0'
cannedveg_E[0].instance_id = 'cannedveg_E_0'
crate_C[0].instance_id = 'crate_C_0'
beverageitem_O[0].instance_id = 'beverageitem_O_0'
glassbottle_L[0].instance_id = 'glassbottle_L_0'
beverageitem_P[0].instance_id = 'beverageitem_P_0'
pricetag_C[0].instance_id = 'pricetag_C_0'
cratefloor_B[0].instance_id = 'cratefloor_B_0'
cannedveg_F[0].instance_id = 'cannedveg_F_0'
pottedplant[0].instance_id = 'pottedplant_0'
chair_A[0].instance_id = 'chair_A_0'
glassbottle_M[0].instance_id = 'glassbottle_M_0'
cratefloor_C[0].instance_id = 'cratefloor_C_0'
beverage_E[0].instance_id = 'beverage_E_0'
cannedgoodaa[0].instance_id = 'cannedgoodaa_0'
cannedgood_R[0].instance_id = 'cannedgood_R_0'
floursack_B[0].instance_id = 'floursack_B_0'
glassbottle_N[0].instance_id = 'glassbottle_N_0'
glassbottle_table_B[0].instance_id = 'glassbottle_table_B_0'
glassbottle9b9b_C[0].instance_id = 'glassbottle9b9b_C_0'
beverageitem_Q[0].instance_id = 'beverageitem_Q_0'
cannedgood_S[0].instance_id = 'cannedgood_S_0'
beverage_F[0].instance_id = 'beverage_F_0'
pricetag_D[0].instance_id = 'pricetag_D_0'
glassbottle_O[0].instance_id = 'glassbottle_O_0'
glassbottle9b9b_D[0].instance_id = 'glassbottle9b9b_D_0'
shoppingbag_C[0].instance_id = 'shoppingbag_C_0'
cannedvegetable_C[0].instance_id = 'cannedvegetable_C_0'
beverageitem_R[0].instance_id = 'beverageitem_R_0'
cannedgood_T[0].instance_id = 'cannedgood_T_0'
cratefloor_D[0].instance_id = 'cratefloor_D_0'
beverage_G[0].instance_id = 'beverage_G_0'
beverageitem_S[0].instance_id = 'beverageitem_S_0'
glassbottle9b_C[0].instance_id = 'glassbottle9b_C_0'
cratefloor_E[0].instance_id = 'cratefloor_E_0'
floursack_C[0].instance_id = 'floursack_C_0'
beverageitem_T[0].instance_id = 'beverageitem_T_0'
cannedveg_G[0].instance_id = 'cannedveg_G_0'
cannedvegetable_9b_A[0].instance_id = 'cannedvegetable_9b_A_0'
cannedveg9b9b_A[0].instance_id = 'cannedveg9b9b_A_0'
cannedgood_U[0].instance_id = 'cannedgood_U_0'
lightfixture_E[0].instance_id = 'lightfixture_E_0'
cannedgood_V[0].instance_id = 'cannedgood_V_0'
case[0].instance_id = 'case_0'
shelf_D[0].instance_id = 'shelf_D_0'
glassbottle_P[0].instance_id = 'glassbottle_P_0'
glassbottle_Q[0].instance_id = 'glassbottle_Q_0'
glassbottlefloor_B[0].instance_id = 'glassbottlefloor_B_0'
cannedvegetable_9b_B[0].instance_id = 'cannedvegetable_9b_B_0'
cannedgood_W[0].instance_id = 'cannedgood_W_0'
shoppingbag_counter[0].instance_id = 'shoppingbag_counter_0'
glassbottle_R[0].instance_id = 'glassbottle_R_0'
beverageitem_U[0].instance_id = 'beverageitem_U_0'
beverageitem_V[0].instance_id = 'beverageitem_V_0'
cannedgood_X[0].instance_id = 'cannedgood_X_0'
beverageitem_W[0].instance_id = 'beverageitem_W_0'
storesign_C[0].instance_id = 'storesign_C_0'
glassbottlefloor_C[0].instance_id = 'glassbottlefloor_C_0'
cannedgood_Y[0].instance_id = 'cannedgood_Y_0'
cannedveg_H[0].instance_id = 'cannedveg_H_0'
cannedgood_Z[0].instance_id = 'cannedgood_Z_0'
storesign_D[0].instance_id = 'storesign_D_0'
beverageitem_X[0].instance_id = 'beverageitem_X_0'
cannedgood_group_2_A[0].instance_id = 'cannedgood_group_2_A_0'
cannedgood_group_2_B[0].instance_id = 'cannedgood_group_2_B_0'
cratefloor_F[0].instance_id = 'cratefloor_F_0'
glassbottle9b9b_E[0].instance_id = 'glassbottle9b9b_E_0'
glassbottle_S[0].instance_id = 'glassbottle_S_0'
table[0].instance_id = 'table_0'
glassbottlefloor_D[0].instance_id = 'glassbottlefloor_D_0'
glassbottle_T[0].instance_id = 'glassbottle_T_0'
glassbottle_U[0].instance_id = 'glassbottle_U_0'
cannedvegetable_D[0].instance_id = 'cannedvegetable_D_0'
chair_B[0].instance_id = 'chair_B_0'
cannedgood_group_2_C[0].instance_id = 'cannedgood_group_2_C_0'
signcoffee[0].instance_id = 'signcoffee_0'
cannedveg_I[0].instance_id = 'cannedveg_I_0'
storesign_E[0].instance_id = 'storesign_E_0'
beverageitem_Y[0].instance_id = 'beverageitem_Y_0'
cannedgood_group_2_D[0].instance_id = 'cannedgood_group_2_D_0'
storesign_F[0].instance_id = 'storesign_F_0'
lightfixture_F[0].instance_id = 'lightfixture_F_0'
beverage_H[0].instance_id = 'beverage_H_0'
beverage_I[0].instance_id = 'beverage_I_0'
cannedveg_J[0].instance_id = 'cannedveg_J_0'
cannedgood_group_2_E[0].instance_id = 'cannedgood_group_2_E_0'
glassbottlefloor_E[0].instance_id = 'glassbottlefloor_E_0'
lightfixture_G[0].instance_id = 'lightfixture_G_0'
cannedveg9b9b_B[0].instance_id = 'cannedveg9b9b_B_0'
beverageitem_Z[0].instance_id = 'beverageitem_Z_0'
glassbottle_V[0].instance_id = 'glassbottle_V_0'
glassbottle_W[0].instance_id = 'glassbottle_W_0'
cannedgood_group_2_F[0].instance_id = 'cannedgood_group_2_F_0'
storesign_G[0].instance_id = 'storesign_G_0'
crate_D[0].instance_id = 'crate_D_0'
cannedgood_group_2_G[0].instance_id = 'cannedgood_group_2_G_0'
beverageitem_group_2[0].instance_id = 'beverageitem_group_2_0'
glassbottle_X[0].instance_id = 'glassbottle_X_0'
cannedgood_group_2_H[0].instance_id = 'cannedgood_group_2_H_0'
glassbottle_Y[0].instance_id = 'glassbottle_Y_0'
sign[0].instance_id = 'sign_0'
cannedgood_group_2_I[0].instance_id = 'cannedgood_group_2_I_0'
cannedvegetable_E[0].instance_id = 'cannedvegetable_E_0'
beverage_J[0].instance_id = 'beverage_J_0'
storesign_H[0].instance_id = 'storesign_H_0'
lightfixture_H[0].instance_id = 'lightfixture_H_0'
storesign_I[0].instance_id = 'storesign_I_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

glassbottle_A[0].position = [4.406355624343742, 5.390168530691445, 0.13]
glassbottle_A[0].rotation = [0, 0, 0]
glassbottle_table_A[0].position = [3.9386734674554074, 3.1553479000308258, 0.135]
glassbottle_table_A[0].rotation = [0, 0, 0]
shoppingbag_A[0].position = [5.604988044188356, 4.914201291204911, 0.21]
shoppingbag_A[0].rotation = [0, 0, 0]
cannedveg_A[0].position = [0.40024351861976637, 0.45750230480401743, 0.08]
cannedveg_A[0].rotation = [0, 0, 0]
lightfixture_A[0].position = [1.9333246309348, 1.0221901388422987, 0.21]
lightfixture_A[0].rotation = [0, 0, 0]
shelf_A[0].position = [0.752364100823399, 3.5971281628048235, 0.95]
shelf_A[0].rotation = [0, 0, 0]
beverageitem_A[0].position = [0.7183729469229363, 3.5406695915510404, 0.09]
beverageitem_A[0].rotation = [0, 0, 0]
beverageitem_B[0].position = [2.545843155038039, 0.7078176574543669, 0.06]
beverageitem_B[0].rotation = [0, 0, 0]
beverage_A[0].position = [1.372995804342723, 4.629487130584024, 0.06]
beverage_A[0].rotation = [0, 0, 0]
cannedgood_A[0].position = [3.159125401806701, 6.628676190888807, 0.06]
cannedgood_A[0].rotation = [0, 0, 0]
glassbottle_B[0].position = [3.469634321588428, 2.7141952939781255, 0.12]
glassbottle_B[0].rotation = [0, 0, 0]
shelf_B[0].position = [2.792660263069826, 1.708699171441098, 1.0]
shelf_B[0].rotation = [0, 0, 0]
beverageitem_C[0].position = [3.544305891255229, 4.396007950041795, 0.1]
beverageitem_C[0].rotation = [0, 0, 0]
beverageitem_D[0].position = [4.556678730417766, 3.9363717202730806, 0.09]
beverageitem_D[0].rotation = [0, 0, 0]
beverageitem_E[0].position = [3.9258087650657565, 1.4684326125650369, 0.06]
beverageitem_E[0].rotation = [0, 0, 0]
cannedgood_B[0].position = [4.867538811306563, 0.684845492814457, 0.075]
cannedgood_B[0].rotation = [0, 0, 0]
scale[0].position = [1.8712109156066776, 4.5283211103424215, 0.29]
scale[0].rotation = [0, 0, 0]
cannedgood_C[0].position = [0.053088602568575505, 3.893061160198206, 0.06]
cannedgood_C[0].rotation = [0, 0, 0]
beverage_B[0].position = [3.610019232279756, 5.414022148850264, 0.115]
beverage_B[0].rotation = [0, 0, 0]
cannedgood_D[0].position = [2.309685398530575, 7.2971347711833054, 0.08]
cannedgood_D[0].rotation = [0, 0, 0]
cannedgood_E[0].position = [0.541584892747929, 1.374462123062023, 0.09]
cannedgood_E[0].rotation = [0, 0, 0]
glassbottle9b9b_A[0].position = [4.577421532495066, 1.7610881200488473, 0.125]
glassbottle9b9b_A[0].rotation = [0, 0, 0]
stool_A[0].position = [5.762448012377266, 3.9796958174552364, 0.335]
stool_A[0].rotation = [0, 0, 0]
cannedveg_B[0].position = [5.669443233141027, 3.454641504160148, 0.08]
cannedveg_B[0].rotation = [0, 0, 0]
glassbottle_shelf_A[0].position = [2.0478133472756275, 1.237067554122138, 0.14]
glassbottle_shelf_A[0].rotation = [0, 0, 0]
glassbottle_C[0].position = [4.979994956071732, 2.6755984805972357, 0.135]
glassbottle_C[0].rotation = [0, 0, 0]
storesign_A[0].position = [5.113417553324658, 1.6432270607343318, 0.175]
storesign_A[0].rotation = [0, 0, 0]
pricetag_A[0].position = [4.421610830138809, 0.6126642941574767, 0.035]
pricetag_A[0].rotation = [0, 0, 0]
cannedvegetable_A[0].position = [4.489705939511019, 5.7605381025150395, 0.055]
cannedvegetable_A[0].rotation = [0, 0, 0]
storesign_B[0].position = [1.3735738375006536, 2.160926597357773, 0.16]
storesign_B[0].rotation = [0, 0, 0]
cannedgood_F[0].position = [0.6330979444499694, 6.12691188140552, 0.06]
cannedgood_F[0].rotation = [0, 0, 0]
beverage_C[0].position = [1.9257131676428978, 2.998299968631299, 0.115]
beverage_C[0].rotation = [0, 0, 0]
cannedgood_G[0].position = [2.622031518932454, 4.611906427894097, 0.085]
cannedgood_G[0].rotation = [0, 0, 0]
beverageitem_F[0].position = [1.878139427865215, 7.066090373482342, 0.075]
beverageitem_F[0].rotation = [0, 0, 0]
glassbottle_D[0].position = [2.856142494344323, 7.89836687199668, 0.135]
glassbottle_D[0].rotation = [0, 0, 0]
cannedgood_H[0].position = [3.087201047745988, 1.230388742044898, 0.075]
cannedgood_H[0].rotation = [0, 0, 0]
cannedgood_I[0].position = [1.9281684917233517, 3.9692527741048966, 0.09]
cannedgood_I[0].rotation = [0, 0, 0]
beverageitem_G[0].position = [4.625480597170929, 1.3178362538992783, 0.09]
beverageitem_G[0].rotation = [0, 0, 0]
cannedgood_J[0].position = [3.8765819330609506, 3.344071464360942, 0.08]
cannedgood_J[0].rotation = [0, 0, 0]
cannedgood_K[0].position = [4.656650351414937, 5.975610228537804, 0.07]
cannedgood_K[0].rotation = [0, 0, 0]
shelf_C[0].position = [5.257717459487226, 3.280624747498652, 0.95]
shelf_C[0].rotation = [0, 0, 0]
glassbottle_E[0].position = [3.779027170430201, 5.500486942559335, 0.135]
glassbottle_E[0].rotation = [0, 0, 0]
glassbottle_F[0].position = [0.8182480339378644, 2.5868325704361075, 0.145]
glassbottle_F[0].rotation = [0, 0, 0]
glassbottle_G[0].position = [1.3161812907487014, 7.729199692918523, 0.14]
glassbottle_G[0].rotation = [0, 0, 0]
cannedgood_table[0].position = [4.212609256158474, 5.246116604726787, 0.09]
cannedgood_table[0].rotation = [0, 0, 0]
beverageitem_H[0].position = [4.592629430683266, 5.61898897253484, 0.09]
beverageitem_H[0].rotation = [0, 0, 0]
glassbottle9b_A[0].position = [3.709108585322168, 6.095984360403444, 0.125]
glassbottle9b_A[0].rotation = [0, 0, 0]
cannedgood_L[0].position = [1.3979624788815384, 1.6864887785335618, 0.07]
cannedgood_L[0].rotation = [0, 0, 0]
shoppingbag_B[0].position = [2.1606539606781414, 0.30003387793015435, 0.21]
shoppingbag_B[0].rotation = [0, 0, 0]
crate_A[0].position = [4.701957500703285, 6.870728526643119, 0.16]
crate_A[0].rotation = [0, 0, 0]
beverage_D[0].position = [5.714239291119074, 5.417445616985912, 0.115]
beverage_D[0].rotation = [0, 0, 0]
stool_B[0].position = [3.2924875462241188, 4.842081219630711, 0.335]
stool_B[0].rotation = [0, 0, 0]
beverageitem_I[0].position = [3.735352252259445, 4.774035570187171, 0.075]
beverageitem_I[0].rotation = [0, 0, 0]
beverageitem_J[0].position = [0.41804291754029954, 4.236608329631163, 0.105]
beverageitem_J[0].rotation = [0, 0, 0]
pricetag_B[0].position = [2.6338232780119504, 3.2862583035028674, 0.035]
pricetag_B[0].rotation = [0, 0, 0]
beverageitem_K[0].position = [1.7372529779586006, 6.331622302256107, 0.11]
beverageitem_K[0].rotation = [0, 0, 0]
cannedgood_M[0].position = [4.991768420238417, 0.532152053755456, 0.09]
cannedgood_M[0].rotation = [0, 0, 0]
glassbottle_shelf_B[0].position = [2.0781080838284463, 0.6739037700537462, 0.14]
glassbottle_shelf_B[0].rotation = [0, 0, 0]
cratefloor_A[0].position = [4.576820866585344, 4.955703230672082, 0.15]
cratefloor_A[0].rotation = [0, 0, 0]
counter[0].position = [2.5072794108529797, 7.636970843455017, 0.475]
counter[0].rotation = [0, 0, 0]
cannedgood_N[0].position = [1.4181548285765706, 6.123308586174623, 0.06]
cannedgood_N[0].rotation = [0, 0, 0]
cannedveg_C[0].position = [5.6345343962214525, 2.138501124511323, 0.065]
cannedveg_C[0].rotation = [0, 0, 0]
crate_B[0].position = [5.393112528587405, 2.777762030857674, 0.16]
crate_B[0].rotation = [0, 0, 0]
cannedgood_O[0].position = [5.292990442001011, 1.2973014876687285, 0.08]
cannedgood_O[0].rotation = [0, 0, 0]
cannedgood_P[0].position = [4.56934771102961, 4.540514991427845, 0.08]
cannedgood_P[0].rotation = [0, 0, 0]
cannedgoodcase[0].position = [3.475329009327581, 7.465760590043944, 0.06]
cannedgoodcase[0].rotation = [0, 0, 0]
cannedveg_D[0].position = [5.52867049790785, 6.466414351042967, 0.07]
cannedveg_D[0].rotation = [0, 0, 0]
glassbottlefloor_A[0].position = [1.9749374106938857, 3.181882879923597, 0.135]
glassbottlefloor_A[0].rotation = [0, 0, 0]
beverageitem_L[0].position = [2.430914636753573, 3.4609090931155517, 0.105]
beverageitem_L[0].rotation = [0, 0, 0]
lightfixture_B[0].position = [3.2442452297179813, 7.3857184378700005, 0.21]
lightfixture_B[0].rotation = [0, 0, 0]
beverageitem_M[0].position = [3.269243466577467, 0.6902990840559609, 0.12]
beverageitem_M[0].rotation = [0, 0, 0]
glassbottle9b_B[0].position = [5.0940600010413615, 6.555031588881247, 0.125]
glassbottle9b_B[0].rotation = [0, 0, 0]
glassbottle_H[0].position = [5.972593610826255, 7.7467246511196555, 0.12]
glassbottle_H[0].rotation = [0, 0, 0]
lightfixture_C[0].position = [4.951013984178888, 3.3472482690916108, 0.19]
lightfixture_C[0].rotation = [0, 0, 0]
lightfixture_D[0].position = [1.5663188150918392, 1.9338221313328896, 0.18]
lightfixture_D[0].rotation = [0, 0, 0]
cannedgood_Q[0].position = [1.9548630716277817, 3.4188481759692593, 0.075]
cannedgood_Q[0].rotation = [0, 0, 0]
glassbottle9b9b_B[0].position = [4.159665225780005, 2.3658411804046464, 0.135]
glassbottle9b9b_B[0].rotation = [0, 0, 0]
glassbottle_I[0].position = [2.939836781697232, 6.301068848307612, 0.13]
glassbottle_I[0].rotation = [0, 0, 0]
floursack_A[0].position = [1.47661696794129, 7.293571781892373, 0.21]
floursack_A[0].rotation = [0, 0, 0]
glassbottle_J[0].position = [0.09819074673350747, 4.825142193708002, 0.135]
glassbottle_J[0].rotation = [0, 0, 0]
beverageitem_N[0].position = [2.209674808863193, 5.937751595298497, 0.09]
beverageitem_N[0].rotation = [0, 0, 0]
glassbottle_K[0].position = [2.7751895646259825, 5.5476176008789615, 0.14]
glassbottle_K[0].rotation = [0, 0, 0]
cannedvegetable_B[0].position = [3.8667690671558654, 7.739260037207709, 0.055]
cannedvegetable_B[0].rotation = [0, 0, 0]
cannedveg_E[0].position = [4.479583291140192, 0.8216909369669079, 0.08]
cannedveg_E[0].rotation = [0, 0, 0]
crate_C[0].position = [3.318166531658041, 5.617839607647273, 0.16]
crate_C[0].rotation = [0, 0, 0]
beverageitem_O[0].position = [5.972724837113308, 0.10953097997278771, 0.12]
beverageitem_O[0].rotation = [0, 0, 0]
glassbottle_L[0].position = [2.123662891368114, 2.308089710618, 0.12]
glassbottle_L[0].rotation = [0, 0, 0]
beverageitem_P[0].position = [1.9395632180570674, 1.9178943191804985, 0.1]
beverageitem_P[0].rotation = [0, 0, 0]
pricetag_C[0].position = [1.8453351221100676, 7.327888604526934, 0.03]
pricetag_C[0].rotation = [0, 0, 0]
cratefloor_B[0].position = [3.4755562026742943, 7.666824570137251, 0.15]
cratefloor_B[0].rotation = [0, 0, 0]
cannedveg_F[0].position = [4.445348486781866, 0.07497029704449432, 0.065]
cannedveg_F[0].rotation = [0, 0, 0]
pottedplant[0].position = [0.9284392107692252, 7.140433575794814, 0.375]
pottedplant[0].rotation = [0, 0, 0]
chair_A[0].position = [5.39586178470509, 3.9544116750296814, 0.44]
chair_A[0].rotation = [0, 0, 0]
glassbottle_M[0].position = [5.576495852086019, 7.500975191883882, 0.125]
glassbottle_M[0].rotation = [0, 0, 0]
cratefloor_C[0].position = [3.270146350383759, 4.916523287470387, 0.15]
cratefloor_C[0].rotation = [0, 0, 0]
beverage_E[0].position = [0.8525102217954841, 0.3589613891787051, 0.06]
beverage_E[0].rotation = [0, 0, 0]
cannedgoodaa[0].position = [2.4575681084376715, 3.316068513450314, 0.08]
cannedgoodaa[0].rotation = [0, 0, 0]
cannedgood_R[0].position = [5.018283270425337, 4.044156835365203, 0.075]
cannedgood_R[0].rotation = [0, 0, 0]
floursack_B[0].position = [5.080196145378875, 4.941355934841002, 0.24]
floursack_B[0].rotation = [0, 0, 0]
glassbottle_N[0].position = [5.211583584719834, 1.6299002076592437, 0.135]
glassbottle_N[0].rotation = [0, 0, 0]
glassbottle_table_B[0].position = [0.02988977610455379, 2.239527103671776, 0.135]
glassbottle_table_B[0].rotation = [0, 0, 0]
glassbottle9b9b_C[0].position = [2.2577335800143996, 0.7792331910368198, 0.125]
glassbottle9b9b_C[0].rotation = [0, 0, 0]
beverageitem_Q[0].position = [4.532304690457676, 3.1616190980106014, 0.09]
beverageitem_Q[0].rotation = [0, 0, 0]
cannedgood_S[0].position = [3.1556286900106922, 6.23715318473586, 0.085]
cannedgood_S[0].rotation = [0, 0, 0]
beverage_F[0].position = [2.0184592357767928, 6.831923013167847, 0.13]
beverage_F[0].rotation = [0, 0, 0]
pricetag_D[0].position = [5.808794903212679, 0.4195768713017749, 0.035]
pricetag_D[0].rotation = [0, 0, 0]
glassbottle_O[0].position = [3.3683579206843044, 6.8617688903451155, 0.14]
glassbottle_O[0].rotation = [0, 0, 0]
glassbottle9b9b_D[0].position = [5.467410597287152, 0.5847535151760379, 0.125]
glassbottle9b9b_D[0].rotation = [0, 0, 0]
shoppingbag_C[0].position = [2.868477125738563, 6.3902670101423755, 0.21]
shoppingbag_C[0].rotation = [0, 0, 0]
cannedvegetable_C[0].position = [0.08136087742212172, 0.9107027161903396, 0.055]
cannedvegetable_C[0].rotation = [0, 0, 0]
beverageitem_R[0].position = [4.501061630634629, 5.302248471361543, 0.11]
beverageitem_R[0].rotation = [0, 0, 0]
cannedgood_T[0].position = [2.8524644761453604, 4.596125095718796, 0.075]
cannedgood_T[0].rotation = [0, 0, 0]
cratefloor_D[0].position = [3.1550386517900417, 2.232740879887559, 0.15]
cratefloor_D[0].rotation = [0, 0, 0]
beverage_G[0].position = [3.792758575291149, 4.777324271633838, 0.13]
beverage_G[0].rotation = [0, 0, 0]
beverageitem_S[0].position = [2.8974358346182014, 1.7068204350944676, 0.12]
beverageitem_S[0].rotation = [0, 0, 0]
glassbottle9b_C[0].position = [1.7326757359889626, 5.472397124548911, 0.125]
glassbottle9b_C[0].rotation = [0, 0, 0]
cratefloor_E[0].position = [1.1259083157508165, 1.2426595350625975, 0.15]
cratefloor_E[0].rotation = [0, 0, 0]
floursack_C[0].position = [2.496130918593689, 3.62051145552061, 0.21]
floursack_C[0].rotation = [0, 0, 0]
beverageitem_T[0].position = [4.582444149630935, 7.74138922108579, 0.105]
beverageitem_T[0].rotation = [0, 0, 0]
cannedveg_G[0].position = [2.4839657208841235, 3.5129762158149145, 0.07]
cannedveg_G[0].rotation = [0, 0, 0]
cannedvegetable_9b_A[0].position = [3.417180085744271, 0.22203959571398535, 0.065]
cannedvegetable_9b_A[0].rotation = [0, 0, 0]
cannedveg9b9b_A[0].position = [4.332275486557728, 7.267484776928451, 0.08]
cannedveg9b9b_A[0].rotation = [0, 0, 0]
cannedgood_U[0].position = [0.22770260026251554, 5.045251620251785, 0.075]
cannedgood_U[0].rotation = [0, 0, 0]
lightfixture_E[0].position = [5.42452881606703, 7.02605262487929, 0.2]
lightfixture_E[0].rotation = [0, 0, 0]
cannedgood_V[0].position = [3.5747209276317653, 2.7642130644747303, 0.075]
cannedgood_V[0].rotation = [0, 0, 0]
case[0].position = [5.867836110773059, 3.590164223285295, 0.625]
case[0].rotation = [0, 0, 0]
shelf_D[0].position = [0.6916092534553964, 0.7071069480305372, 0.975]
shelf_D[0].rotation = [0, 0, 0]
glassbottle_P[0].position = [2.991337138396151, 5.277350398366537, 0.125]
glassbottle_P[0].rotation = [0, 0, 0]
glassbottle_Q[0].position = [4.8194349033843435, 7.290924645961552, 0.14]
glassbottle_Q[0].rotation = [0, 0, 0]
glassbottlefloor_B[0].position = [1.288134735579115, 7.869986715970021, 0.135]
glassbottlefloor_B[0].rotation = [0, 0, 0]
cannedvegetable_9b_B[0].position = [0.7984913651490084, 2.5071466758524377, 0.065]
cannedvegetable_9b_B[0].rotation = [0, 0, 0]
cannedgood_W[0].position = [0.6033202317266635, 3.2909297245375173, 0.09]
cannedgood_W[0].rotation = [0, 0, 0]
shoppingbag_counter[0].position = [0.20835442607220145, 2.0761643189783934, 0.21]
shoppingbag_counter[0].rotation = [0, 0, 0]
glassbottle_R[0].position = [4.3584674798542915, 1.142365191041848, 0.145]
glassbottle_R[0].rotation = [0, 0, 0]
beverageitem_U[0].position = [3.039427319343109, 2.168820257297834, 0.11]
beverageitem_U[0].rotation = [0, 0, 0]
beverageitem_V[0].position = [3.0347033673396253, 2.2823819298284267, 0.075]
beverageitem_V[0].rotation = [0, 0, 0]
cannedgood_X[0].position = [5.07622369213007, 0.09340267664526447, 0.085]
cannedgood_X[0].rotation = [0, 0, 0]
beverageitem_W[0].position = [2.0650583813572245, 3.0935850281985537, 0.09]
beverageitem_W[0].rotation = [0, 0, 0]
storesign_C[0].position = [2.580448513830715, 4.389334829820959, 0.16]
storesign_C[0].rotation = [0, 0, 0]
glassbottlefloor_C[0].position = [0.06507142595166138, 2.69491865277367, 0.135]
glassbottlefloor_C[0].rotation = [0, 0, 0]
cannedgood_Y[0].position = [0.3257310029090321, 4.079129406182532, 0.065]
cannedgood_Y[0].rotation = [0, 0, 0]
cannedveg_H[0].position = [5.032127720092891, 6.96322587220742, 0.08]
cannedveg_H[0].rotation = [0, 0, 0]
cannedgood_Z[0].position = [4.602172189072281, 7.703561845396503, 0.075]
cannedgood_Z[0].rotation = [0, 0, 0]
storesign_D[0].position = [1.9637972580584644, 7.827877690570244, 0.175]
storesign_D[0].rotation = [0, 0, 0]
beverageitem_X[0].position = [5.158527836964213, 2.797408965339412, 0.1]
beverageitem_X[0].rotation = [0, 0, 0]
cannedgood_group_2_A[0].position = [3.348655459163635, 1.1155846083617904, 0.085]
cannedgood_group_2_A[0].rotation = [0, 0, 0]
cannedgood_group_2_B[0].position = [4.953456704326859, 3.4360069292024766, 0.075]
cannedgood_group_2_B[0].rotation = [0, 0, 0]
cratefloor_F[0].position = [2.75285276695438, 5.364207888527488, 0.15]
cratefloor_F[0].rotation = [0, 0, 0]
glassbottle9b9b_E[0].position = [1.5574624659324803, 5.193459518475753, 0.135]
glassbottle9b9b_E[0].rotation = [0, 0, 0]
glassbottle_S[0].position = [2.146539400301795, 1.1601961687632274, 0.12]
glassbottle_S[0].rotation = [0, 0, 0]
table[0].position = [3.870731205563378, 4.117371920349529, 0.375]
table[0].rotation = [0, 0, 0]
glassbottlefloor_D[0].position = [5.754200117035161, 2.797853494027108, 0.135]
glassbottlefloor_D[0].rotation = [0, 0, 0]
glassbottle_T[0].position = [5.496396799344231, 3.0186954842204834, 0.12]
glassbottle_T[0].rotation = [0, 0, 0]
glassbottle_U[0].position = [4.619740450157126, 3.4332407818077666, 0.135]
glassbottle_U[0].rotation = [0, 0, 0]
cannedvegetable_D[0].position = [1.8127004146155927, 2.339575362126137, 0.055]
cannedvegetable_D[0].rotation = [0, 0, 0]
chair_B[0].position = [4.845547922615388, 0.20474031347205823, 0.44]
chair_B[0].rotation = [0, 0, 0]
cannedgood_group_2_C[0].position = [5.737202407473155, 6.747331509001447, 0.085]
cannedgood_group_2_C[0].rotation = [0, 0, 0]
signcoffee[0].position = [3.7497149155621154, 7.796630252633207, 0.14]
signcoffee[0].rotation = [0, 0, 0]
cannedveg_I[0].position = [4.563398147428356, 2.309287335776621, 0.07]
cannedveg_I[0].rotation = [0, 0, 0]
storesign_E[0].position = [0.983020137578186, 7.163314178992568, 0.19]
storesign_E[0].rotation = [0, 0, 0]
beverageitem_Y[0].position = [4.22194734863929, 4.636055500036534, 0.12]
beverageitem_Y[0].rotation = [0, 0, 0]
cannedgood_group_2_D[0].position = [1.7885254650554978, 3.5528012362450196, 0.09]
cannedgood_group_2_D[0].rotation = [0, 0, 0]
storesign_F[0].position = [5.640266253976137, 2.7554488379257522, 0.175]
storesign_F[0].rotation = [0, 0, 0]
lightfixture_F[0].position = [0.6400935068007911, 5.308763660003993, 0.21]
lightfixture_F[0].rotation = [0, 0, 0]
beverage_H[0].position = [1.1055781746560014, 0.5126901833262743, 0.13]
beverage_H[0].rotation = [0, 0, 0]
beverage_I[0].position = [0.9275052512459485, 2.8585475249327716, 0.115]
beverage_I[0].rotation = [0, 0, 0]
cannedveg_J[0].position = [0.797598487480216, 2.015428175025934, 0.07]
cannedveg_J[0].rotation = [0, 0, 0]
cannedgood_group_2_E[0].position = [0.7577695564858395, 3.738813778789214, 0.09]
cannedgood_group_2_E[0].rotation = [0, 0, 0]
glassbottlefloor_E[0].position = [5.72692916837085, 1.2576130811000006, 0.135]
glassbottlefloor_E[0].rotation = [0, 0, 0]
lightfixture_G[0].position = [0.7599184214166523, 7.309027808494877, 0.21]
lightfixture_G[0].rotation = [0, 0, 0]
cannedveg9b9b_B[0].position = [2.275860227662028, 5.422792581148371, 0.08]
cannedveg9b9b_B[0].rotation = [0, 0, 0]
beverageitem_Z[0].position = [1.7756478847135646, 2.3178671375814934, 0.075]
beverageitem_Z[0].rotation = [0, 0, 0]
glassbottle_V[0].position = [1.8618223867983086, 6.985537547670865, 0.135]
glassbottle_V[0].rotation = [0, 0, 0]
glassbottle_W[0].position = [4.735730431148085, 0.9502787185451886, 0.135]
glassbottle_W[0].rotation = [0, 0, 0]
cannedgood_group_2_F[0].position = [3.414356024654159, 7.180660727579094, 0.085]
cannedgood_group_2_F[0].rotation = [0, 0, 0]
storesign_G[0].position = [3.512354608533748, 1.894308226039855, 0.175]
storesign_G[0].rotation = [0, 0, 0]
crate_D[0].position = [5.853800691468166, 1.8979708976606773, 0.16]
crate_D[0].rotation = [0, 0, 0]
cannedgood_group_2_G[0].position = [1.2813317055621538, 2.6977661953896765, 0.065]
cannedgood_group_2_G[0].rotation = [0, 0, 0]
beverageitem_group_2[0].position = [5.903873827883084, 1.2435189656828989, 0.12]
beverageitem_group_2[0].rotation = [0, 0, 0]
glassbottle_X[0].position = [3.3571456652301475, 6.568423614380337, 0.12]
glassbottle_X[0].rotation = [0, 0, 0]
cannedgood_group_2_H[0].position = [3.7203449206340373, 7.654878468917389, 0.09]
cannedgood_group_2_H[0].rotation = [0, 0, 0]
glassbottle_Y[0].position = [1.8189927249288027, 5.233740730275854, 0.12]
glassbottle_Y[0].rotation = [0, 0, 0]
sign[0].position = [1.1580031854316448, 3.6637828210584793, 0.15]
sign[0].rotation = [0, 0, 0]
cannedgood_group_2_I[0].position = [1.0865790933069754, 0.0864816100289243, 0.075]
cannedgood_group_2_I[0].rotation = [0, 0, 0]
cannedvegetable_E[0].position = [3.183444937156437, 4.663882396998379, 0.055]
cannedvegetable_E[0].rotation = [0, 0, 0]
beverage_J[0].position = [1.3565024665110192, 0.7839214261626584, 0.13]
beverage_J[0].rotation = [0, 0, 0]
storesign_H[0].position = [3.2302385332828, 1.508655977148572, 0.19]
storesign_H[0].rotation = [0, 0, 0]
lightfixture_H[0].position = [4.9493130574964335, 0.3637548207043855, 0.2]
lightfixture_H[0].rotation = [0, 0, 0]
storesign_I[0].position = [3.428310541741063, 2.8202861114352693, 0.19]
storesign_I[0].rotation = [0, 0, 0]
glassbottle_A[0].position = [4.406355624343742, 5.390168530691445, 0.13]
glassbottle_A[0].rotation = [0, 0, 0]
glassbottle_table_A[0].position = [3.9386734674554074, 3.1553479000308258, 0.135]
glassbottle_table_A[0].rotation = [0, 0, 0]
shoppingbag_A[0].position = [5.604988044188356, 4.914201291204911, 0.21]
shoppingbag_A[0].rotation = [0, 0, 0]
cannedveg_A[0].position = [0.40024351861976637, 0.45750230480401743, 0.08]
cannedveg_A[0].rotation = [0, 0, 0]
lightfixture_A[0].position = [1.9333246309348, 1.0221901388422987, 0.21]
lightfixture_A[0].rotation = [0, 0, 0]
shelf_A[0].position = [0.752364100823399, 3.5971281628048235, 0.95]
shelf_A[0].rotation = [0, 0, 0]
beverageitem_A[0].position = [0.7183729469229363, 3.5406695915510404, 0.09]
beverageitem_A[0].rotation = [0, 0, 0]
beverageitem_B[0].position = [2.545843155038039, 0.7078176574543669, 0.06]
beverageitem_B[0].rotation = [0, 0, 0]
beverage_A[0].position = [1.372995804342723, 4.629487130584024, 0.06]
beverage_A[0].rotation = [0, 0, 0]
cannedgood_A[0].position = [3.159125401806701, 6.628676190888807, 0.06]
cannedgood_A[0].rotation = [0, 0, 0]
glassbottle_B[0].position = [3.469634321588428, 2.7141952939781255, 0.12]
glassbottle_B[0].rotation = [0, 0, 0]
shelf_B[0].position = [2.792660263069826, 1.708699171441098, 1.0]
shelf_B[0].rotation = [0, 0, 0]
beverageitem_C[0].position = [3.544305891255229, 4.396007950041795, 0.1]
beverageitem_C[0].rotation = [0, 0, 0]
beverageitem_D[0].position = [4.556678730417766, 3.9363717202730806, 0.09]
beverageitem_D[0].rotation = [0, 0, 0]
beverageitem_E[0].position = [3.9258087650657565, 1.4684326125650369, 0.06]
beverageitem_E[0].rotation = [0, 0, 0]
cannedgood_B[0].position = [4.867538811306563, 0.684845492814457, 0.075]
cannedgood_B[0].rotation = [0, 0, 0]
scale[0].position = [1.8712109156066776, 4.5283211103424215, 0.29]
scale[0].rotation = [0, 0, 0]
cannedgood_C[0].position = [0.053088602568575505, 3.893061160198206, 0.06]
cannedgood_C[0].rotation = [0, 0, 0]
beverage_B[0].position = [3.610019232279756, 5.414022148850264, 0.115]
beverage_B[0].rotation = [0, 0, 0]
cannedgood_D[0].position = [2.309685398530575, 7.2971347711833054, 0.08]
cannedgood_D[0].rotation = [0, 0, 0]
cannedgood_E[0].position = [0.541584892747929, 1.374462123062023, 0.09]
cannedgood_E[0].rotation = [0, 0, 0]
glassbottle9b9b_A[0].position = [4.577421532495066, 1.7610881200488473, 0.125]
glassbottle9b9b_A[0].rotation = [0, 0, 0]
stool_A[0].position = [5.762448012377266, 3.9796958174552364, 0.335]
stool_A[0].rotation = [0, 0, 0]
cannedveg_B[0].position = [5.669443233141027, 3.454641504160148, 0.08]
cannedveg_B[0].rotation = [0, 0, 0]
glassbottle_shelf_A[0].position = [2.0478133472756275, 1.237067554122138, 0.14]
glassbottle_shelf_A[0].rotation = [0, 0, 0]
glassbottle_C[0].position = [4.979994956071732, 2.6755984805972357, 0.135]
glassbottle_C[0].rotation = [0, 0, 0]
storesign_A[0].position = [5.113417553324658, 1.6432270607343318, 0.175]
storesign_A[0].rotation = [0, 0, 0]
pricetag_A[0].position = [4.421610830138809, 0.6126642941574767, 0.035]
pricetag_A[0].rotation = [0, 0, 0]
cannedvegetable_A[0].position = [4.489705939511019, 5.7605381025150395, 0.055]
cannedvegetable_A[0].rotation = [0, 0, 0]
storesign_B[0].position = [1.3735738375006536, 2.160926597357773, 0.16]
storesign_B[0].rotation = [0, 0, 0]
cannedgood_F[0].position = [0.6330979444499694, 6.12691188140552, 0.06]
cannedgood_F[0].rotation = [0, 0, 0]
beverage_C[0].position = [1.9257131676428978, 2.998299968631299, 0.115]
beverage_C[0].rotation = [0, 0, 0]
cannedgood_G[0].position = [2.622031518932454, 4.611906427894097, 0.085]
cannedgood_G[0].rotation = [0, 0, 0]
beverageitem_F[0].position = [1.878139427865215, 7.066090373482342, 0.075]
beverageitem_F[0].rotation = [0, 0, 0]
glassbottle_D[0].position = [2.856142494344323, 7.89836687199668, 0.135]
glassbottle_D[0].rotation = [0, 0, 0]
cannedgood_H[0].position = [3.087201047745988, 1.230388742044898, 0.075]
cannedgood_H[0].rotation = [0, 0, 0]
cannedgood_I[0].position = [1.9281684917233517, 3.9692527741048966, 0.09]
cannedgood_I[0].rotation = [0, 0, 0]
beverageitem_G[0].position = [4.625480597170929, 1.3178362538992783, 0.09]
beverageitem_G[0].rotation = [0, 0, 0]
cannedgood_J[0].position = [3.8765819330609506, 3.344071464360942, 0.08]
cannedgood_J[0].rotation = [0, 0, 0]
cannedgood_K[0].position = [4.656650351414937, 5.975610228537804, 0.07]
cannedgood_K[0].rotation = [0, 0, 0]
shelf_C[0].position = [5.257717459487226, 3.280624747498652, 0.95]
shelf_C[0].rotation = [0, 0, 0]
glassbottle_E[0].position = [3.779027170430201, 5.500486942559335, 0.135]
glassbottle_E[0].rotation = [0, 0, 0]
glassbottle_F[0].position = [0.8182480339378644, 2.5868325704361075, 0.145]
glassbottle_F[0].rotation = [0, 0, 0]
glassbottle_G[0].position = [1.3161812907487014, 7.729199692918523, 0.14]
glassbottle_G[0].rotation = [0, 0, 0]
cannedgood_table[0].position = [4.212609256158474, 5.246116604726787, 0.09]
cannedgood_table[0].rotation = [0, 0, 0]
beverageitem_H[0].position = [4.592629430683266, 5.61898897253484, 0.09]
beverageitem_H[0].rotation = [0, 0, 0]
glassbottle9b_A[0].position = [3.709108585322168, 6.095984360403444, 0.125]
glassbottle9b_A[0].rotation = [0, 0, 0]
cannedgood_L[0].position = [1.3979624788815384, 1.6864887785335618, 0.07]
cannedgood_L[0].rotation = [0, 0, 0]
shoppingbag_B[0].position = [2.1606539606781414, 0.30003387793015435, 0.21]
shoppingbag_B[0].rotation = [0, 0, 0]
crate_A[0].position = [4.701957500703285, 6.870728526643119, 0.16]
crate_A[0].rotation = [0, 0, 0]
beverage_D[0].position = [5.714239291119074, 5.417445616985912, 0.115]
beverage_D[0].rotation = [0, 0, 0]
stool_B[0].position = [3.2924875462241188, 4.842081219630711, 0.335]
stool_B[0].rotation = [0, 0, 0]
beverageitem_I[0].position = [3.735352252259445, 4.774035570187171, 0.075]
beverageitem_I[0].rotation = [0, 0, 0]
beverageitem_J[0].position = [0.41804291754029954, 4.236608329631163, 0.105]
beverageitem_J[0].rotation = [0, 0, 0]
pricetag_B[0].position = [2.6338232780119504, 3.2862583035028674, 0.035]
pricetag_B[0].rotation = [0, 0, 0]
beverageitem_K[0].position = [1.7372529779586006, 6.331622302256107, 0.11]
beverageitem_K[0].rotation = [0, 0, 0]
cannedgood_M[0].position = [4.991768420238417, 0.532152053755456, 0.09]
cannedgood_M[0].rotation = [0, 0, 0]
glassbottle_shelf_B[0].position = [2.0781080838284463, 0.6739037700537462, 0.14]
glassbottle_shelf_B[0].rotation = [0, 0, 0]
cratefloor_A[0].position = [4.576820866585344, 4.955703230672082, 0.15]
cratefloor_A[0].rotation = [0, 0, 0]
counter[0].position = [2.5072794108529797, 7.636970843455017, 0.475]
counter[0].rotation = [0, 0, 0]
cannedgood_N[0].position = [1.4181548285765706, 6.123308586174623, 0.06]
cannedgood_N[0].rotation = [0, 0, 0]
cannedveg_C[0].position = [5.6345343962214525, 2.138501124511323, 0.065]
cannedveg_C[0].rotation = [0, 0, 0]
crate_B[0].position = [5.393112528587405, 2.777762030857674, 0.16]
crate_B[0].rotation = [0, 0, 0]
cannedgood_O[0].position = [5.292990442001011, 1.2973014876687285, 0.08]
cannedgood_O[0].rotation = [0, 0, 0]
cannedgood_P[0].position = [4.56934771102961, 4.540514991427845, 0.08]
cannedgood_P[0].rotation = [0, 0, 0]
cannedgoodcase[0].position = [3.475329009327581, 7.465760590043944, 0.06]
cannedgoodcase[0].rotation = [0, 0, 0]
cannedveg_D[0].position = [5.52867049790785, 6.466414351042967, 0.07]
cannedveg_D[0].rotation = [0, 0, 0]
glassbottlefloor_A[0].position = [1.9749374106938857, 3.181882879923597, 0.135]
glassbottlefloor_A[0].rotation = [0, 0, 0]
beverageitem_L[0].position = [2.430914636753573, 3.4609090931155517, 0.105]
beverageitem_L[0].rotation = [0, 0, 0]
lightfixture_B[0].position = [3.2442452297179813, 7.3857184378700005, 0.21]
lightfixture_B[0].rotation = [0, 0, 0]
beverageitem_M[0].position = [3.269243466577467, 0.6902990840559609, 0.12]
beverageitem_M[0].rotation = [0, 0, 0]
glassbottle9b_B[0].position = [5.0940600010413615, 6.555031588881247, 0.125]
glassbottle9b_B[0].rotation = [0, 0, 0]
glassbottle_H[0].position = [5.972593610826255, 7.7467246511196555, 0.12]
glassbottle_H[0].rotation = [0, 0, 0]
lightfixture_C[0].position = [4.951013984178888, 3.3472482690916108, 0.19]
lightfixture_C[0].rotation = [0, 0, 0]
lightfixture_D[0].position = [1.5663188150918392, 1.9338221313328896, 0.18]
lightfixture_D[0].rotation = [0, 0, 0]
cannedgood_Q[0].position = [1.9548630716277817, 3.4188481759692593, 0.075]
cannedgood_Q[0].rotation = [0, 0, 0]
glassbottle9b9b_B[0].position = [4.159665225780005, 2.3658411804046464, 0.135]
glassbottle9b9b_B[0].rotation = [0, 0, 0]
glassbottle_I[0].position = [2.939836781697232, 6.301068848307612, 0.13]
glassbottle_I[0].rotation = [0, 0, 0]
floursack_A[0].position = [1.47661696794129, 7.293571781892373, 0.21]
floursack_A[0].rotation = [0, 0, 0]
glassbottle_J[0].position = [0.09819074673350747, 4.825142193708002, 0.135]
glassbottle_J[0].rotation = [0, 0, 0]
beverageitem_N[0].position = [2.209674808863193, 5.937751595298497, 0.09]
beverageitem_N[0].rotation = [0, 0, 0]
glassbottle_K[0].position = [2.7751895646259825, 5.5476176008789615, 0.14]
glassbottle_K[0].rotation = [0, 0, 0]
cannedvegetable_B[0].position = [3.8667690671558654, 7.739260037207709, 0.055]
cannedvegetable_B[0].rotation = [0, 0, 0]
cannedveg_E[0].position = [4.479583291140192, 0.8216909369669079, 0.08]
cannedveg_E[0].rotation = [0, 0, 0]
crate_C[0].position = [3.318166531658041, 5.617839607647273, 0.16]
crate_C[0].rotation = [0, 0, 0]
beverageitem_O[0].position = [5.972724837113308, 0.10953097997278771, 0.12]
beverageitem_O[0].rotation = [0, 0, 0]
glassbottle_L[0].position = [2.123662891368114, 2.308089710618, 0.12]
glassbottle_L[0].rotation = [0, 0, 0]
beverageitem_P[0].position = [1.9395632180570674, 1.9178943191804985, 0.1]
beverageitem_P[0].rotation = [0, 0, 0]
pricetag_C[0].position = [1.8453351221100676, 7.327888604526934, 0.03]
pricetag_C[0].rotation = [0, 0, 0]
cratefloor_B[0].position = [3.4755562026742943, 7.666824570137251, 0.15]
cratefloor_B[0].rotation = [0, 0, 0]
cannedveg_F[0].position = [4.445348486781866, 0.07497029704449432, 0.065]
cannedveg_F[0].rotation = [0, 0, 0]
pottedplant[0].position = [0.9284392107692252, 7.140433575794814, 0.375]
pottedplant[0].rotation = [0, 0, 0]
chair_A[0].position = [5.39586178470509, 3.9544116750296814, 0.44]
chair_A[0].rotation = [0, 0, 0]
glassbottle_M[0].position = [5.576495852086019, 7.500975191883882, 0.125]
glassbottle_M[0].rotation = [0, 0, 0]
cratefloor_C[0].position = [3.270146350383759, 4.916523287470387, 0.15]
cratefloor_C[0].rotation = [0, 0, 0]
beverage_E[0].position = [0.8525102217954841, 0.3589613891787051, 0.06]
beverage_E[0].rotation = [0, 0, 0]
cannedgoodaa[0].position = [2.4575681084376715, 3.316068513450314, 0.08]
cannedgoodaa[0].rotation = [0, 0, 0]
cannedgood_R[0].position = [5.018283270425337, 4.044156835365203, 0.075]
cannedgood_R[0].rotation = [0, 0, 0]
floursack_B[0].position = [5.080196145378875, 4.941355934841002, 0.24]
floursack_B[0].rotation = [0, 0, 0]
glassbottle_N[0].position = [5.211583584719834, 1.6299002076592437, 0.135]
glassbottle_N[0].rotation = [0, 0, 0]
glassbottle_table_B[0].position = [0.02988977610455379, 2.239527103671776, 0.135]
glassbottle_table_B[0].rotation = [0, 0, 0]
glassbottle9b9b_C[0].position = [2.2577335800143996, 0.7792331910368198, 0.125]
glassbottle9b9b_C[0].rotation = [0, 0, 0]
beverageitem_Q[0].position = [4.532304690457676, 3.1616190980106014, 0.09]
beverageitem_Q[0].rotation = [0, 0, 0]
cannedgood_S[0].position = [3.1556286900106922, 6.23715318473586, 0.085]
cannedgood_S[0].rotation = [0, 0, 0]
beverage_F[0].position = [2.0184592357767928, 6.831923013167847, 0.13]
beverage_F[0].rotation = [0, 0, 0]
pricetag_D[0].position = [5.808794903212679, 0.4195768713017749, 0.035]
pricetag_D[0].rotation = [0, 0, 0]
glassbottle_O[0].position = [3.3683579206843044, 6.8617688903451155, 0.14]
glassbottle_O[0].rotation = [0, 0, 0]
glassbottle9b9b_D[0].position = [5.467410597287152, 0.5847535151760379, 0.125]
glassbottle9b9b_D[0].rotation = [0, 0, 0]
shoppingbag_C[0].position = [2.868477125738563, 6.3902670101423755, 0.21]
shoppingbag_C[0].rotation = [0, 0, 0]
cannedvegetable_C[0].position = [0.08136087742212172, 0.9107027161903396, 0.055]
cannedvegetable_C[0].rotation = [0, 0, 0]
beverageitem_R[0].position = [4.501061630634629, 5.302248471361543, 0.11]
beverageitem_R[0].rotation = [0, 0, 0]
cannedgood_T[0].position = [2.8524644761453604, 4.596125095718796, 0.075]
cannedgood_T[0].rotation = [0, 0, 0]
cratefloor_D[0].position = [3.1550386517900417, 2.232740879887559, 0.15]
cratefloor_D[0].rotation = [0, 0, 0]
beverage_G[0].position = [3.792758575291149, 4.777324271633838, 0.13]
beverage_G[0].rotation = [0, 0, 0]
beverageitem_S[0].position = [2.8974358346182014, 1.7068204350944676, 0.12]
beverageitem_S[0].rotation = [0, 0, 0]
glassbottle9b_C[0].position = [1.7326757359889626, 5.472397124548911, 0.125]
glassbottle9b_C[0].rotation = [0, 0, 0]
cratefloor_E[0].position = [1.1259083157508165, 1.2426595350625975, 0.15]
cratefloor_E[0].rotation = [0, 0, 0]
floursack_C[0].position = [2.496130918593689, 3.62051145552061, 0.21]
floursack_C[0].rotation = [0, 0, 0]
beverageitem_T[0].position = [4.582444149630935, 7.74138922108579, 0.105]
beverageitem_T[0].rotation = [0, 0, 0]
cannedveg_G[0].position = [2.4839657208841235, 3.5129762158149145, 0.07]
cannedveg_G[0].rotation = [0, 0, 0]
cannedvegetable_9b_A[0].position = [3.417180085744271, 0.22203959571398535, 0.065]
cannedvegetable_9b_A[0].rotation = [0, 0, 0]
cannedveg9b9b_A[0].position = [4.332275486557728, 7.267484776928451, 0.08]
cannedveg9b9b_A[0].rotation = [0, 0, 0]
cannedgood_U[0].position = [0.22770260026251554, 5.045251620251785, 0.075]
cannedgood_U[0].rotation = [0, 0, 0]
lightfixture_E[0].position = [5.42452881606703, 7.02605262487929, 0.2]
lightfixture_E[0].rotation = [0, 0, 0]
cannedgood_V[0].position = [3.5747209276317653, 2.7642130644747303, 0.075]
cannedgood_V[0].rotation = [0, 0, 0]
case[0].position = [5.867836110773059, 3.590164223285295, 0.625]
case[0].rotation = [0, 0, 0]
shelf_D[0].position = [0.6916092534553964, 0.7071069480305372, 0.975]
shelf_D[0].rotation = [0, 0, 0]
glassbottle_P[0].position = [2.991337138396151, 5.277350398366537, 0.125]
glassbottle_P[0].rotation = [0, 0, 0]
glassbottle_Q[0].position = [4.8194349033843435, 7.290924645961552, 0.14]
glassbottle_Q[0].rotation = [0, 0, 0]
glassbottlefloor_B[0].position = [1.288134735579115, 7.869986715970021, 0.135]
glassbottlefloor_B[0].rotation = [0, 0, 0]
cannedvegetable_9b_B[0].position = [0.7984913651490084, 2.5071466758524377, 0.065]
cannedvegetable_9b_B[0].rotation = [0, 0, 0]
cannedgood_W[0].position = [0.6033202317266635, 3.2909297245375173, 0.09]
cannedgood_W[0].rotation = [0, 0, 0]
shoppingbag_counter[0].position = [0.20835442607220145, 2.0761643189783934, 0.21]
shoppingbag_counter[0].rotation = [0, 0, 0]
glassbottle_R[0].position = [4.3584674798542915, 1.142365191041848, 0.145]
glassbottle_R[0].rotation = [0, 0, 0]
beverageitem_U[0].position = [3.039427319343109, 2.168820257297834, 0.11]
beverageitem_U[0].rotation = [0, 0, 0]
beverageitem_V[0].position = [3.0347033673396253, 2.2823819298284267, 0.075]
beverageitem_V[0].rotation = [0, 0, 0]
cannedgood_X[0].position = [5.07622369213007, 0.09340267664526447, 0.085]
cannedgood_X[0].rotation = [0, 0, 0]
beverageitem_W[0].position = [2.0650583813572245, 3.0935850281985537, 0.09]
beverageitem_W[0].rotation = [0, 0, 0]
storesign_C[0].position = [2.580448513830715, 4.389334829820959, 0.16]
storesign_C[0].rotation = [0, 0, 0]
glassbottlefloor_C[0].position = [0.06507142595166138, 2.69491865277367, 0.135]
glassbottlefloor_C[0].rotation = [0, 0, 0]
cannedgood_Y[0].position = [0.3257310029090321, 4.079129406182532, 0.065]
cannedgood_Y[0].rotation = [0, 0, 0]
cannedveg_H[0].position = [5.032127720092891, 6.96322587220742, 0.08]
cannedveg_H[0].rotation = [0, 0, 0]
cannedgood_Z[0].position = [4.602172189072281, 7.703561845396503, 0.075]
cannedgood_Z[0].rotation = [0, 0, 0]
storesign_D[0].position = [1.9637972580584644, 7.827877690570244, 0.175]
storesign_D[0].rotation = [0, 0, 0]
beverageitem_X[0].position = [5.158527836964213, 2.797408965339412, 0.1]
beverageitem_X[0].rotation = [0, 0, 0]
cannedgood_group_2_A[0].position = [3.348655459163635, 1.1155846083617904, 0.085]
cannedgood_group_2_A[0].rotation = [0, 0, 0]
cannedgood_group_2_B[0].position = [4.953456704326859, 3.4360069292024766, 0.075]
cannedgood_group_2_B[0].rotation = [0, 0, 0]
cratefloor_F[0].position = [2.75285276695438, 5.364207888527488, 0.15]
cratefloor_F[0].rotation = [0, 0, 0]
glassbottle9b9b_E[0].position = [1.5574624659324803, 5.193459518475753, 0.135]
glassbottle9b9b_E[0].rotation = [0, 0, 0]
glassbottle_S[0].position = [2.146539400301795, 1.1601961687632274, 0.12]
glassbottle_S[0].rotation = [0, 0, 0]
table[0].position = [3.870731205563378, 4.117371920349529, 0.375]
table[0].rotation = [0, 0, 0]
glassbottlefloor_D[0].position = [5.754200117035161, 2.797853494027108, 0.135]
glassbottlefloor_D[0].rotation = [0, 0, 0]
glassbottle_T[0].position = [5.496396799344231, 3.0186954842204834, 0.12]
glassbottle_T[0].rotation = [0, 0, 0]
glassbottle_U[0].position = [4.619740450157126, 3.4332407818077666, 0.135]
glassbottle_U[0].rotation = [0, 0, 0]
cannedvegetable_D[0].position = [1.8127004146155927, 2.339575362126137, 0.055]
cannedvegetable_D[0].rotation = [0, 0, 0]
chair_B[0].position = [4.845547922615388, 0.20474031347205823, 0.44]
chair_B[0].rotation = [0, 0, 0]
cannedgood_group_2_C[0].position = [5.737202407473155, 6.747331509001447, 0.085]
cannedgood_group_2_C[0].rotation = [0, 0, 0]
signcoffee[0].position = [3.7497149155621154, 7.796630252633207, 0.14]
signcoffee[0].rotation = [0, 0, 0]
cannedveg_I[0].position = [4.563398147428356, 2.309287335776621, 0.07]
cannedveg_I[0].rotation = [0, 0, 0]
storesign_E[0].position = [0.983020137578186, 7.163314178992568, 0.19]
storesign_E[0].rotation = [0, 0, 0]
beverageitem_Y[0].position = [4.22194734863929, 4.636055500036534, 0.12]
beverageitem_Y[0].rotation = [0, 0, 0]
cannedgood_group_2_D[0].position = [1.7885254650554978, 3.5528012362450196, 0.09]
cannedgood_group_2_D[0].rotation = [0, 0, 0]
storesign_F[0].position = [5.640266253976137, 2.7554488379257522, 0.175]
storesign_F[0].rotation = [0, 0, 0]
lightfixture_F[0].position = [0.6400935068007911, 5.308763660003993, 0.21]
lightfixture_F[0].rotation = [0, 0, 0]
beverage_H[0].position = [1.1055781746560014, 0.5126901833262743, 0.13]
beverage_H[0].rotation = [0, 0, 0]
beverage_I[0].position = [0.9275052512459485, 2.8585475249327716, 0.115]
beverage_I[0].rotation = [0, 0, 0]
cannedveg_J[0].position = [0.797598487480216, 2.015428175025934, 0.07]
cannedveg_J[0].rotation = [0, 0, 0]
cannedgood_group_2_E[0].position = [0.7577695564858395, 3.738813778789214, 0.09]
cannedgood_group_2_E[0].rotation = [0, 0, 0]
glassbottlefloor_E[0].position = [5.72692916837085, 1.2576130811000006, 0.135]
glassbottlefloor_E[0].rotation = [0, 0, 0]
lightfixture_G[0].position = [0.7599184214166523, 7.309027808494877, 0.21]
lightfixture_G[0].rotation = [0, 0, 0]
cannedveg9b9b_B[0].position = [2.275860227662028, 5.422792581148371, 0.08]
cannedveg9b9b_B[0].rotation = [0, 0, 0]
beverageitem_Z[0].position = [1.7756478847135646, 2.3178671375814934, 0.075]
beverageitem_Z[0].rotation = [0, 0, 0]
glassbottle_V[0].position = [1.8618223867983086, 6.985537547670865, 0.135]
glassbottle_V[0].rotation = [0, 0, 0]
glassbottle_W[0].position = [4.735730431148085, 0.9502787185451886, 0.135]
glassbottle_W[0].rotation = [0, 0, 0]
cannedgood_group_2_F[0].position = [3.414356024654159, 7.180660727579094, 0.085]
cannedgood_group_2_F[0].rotation = [0, 0, 0]
storesign_G[0].position = [3.512354608533748, 1.894308226039855, 0.175]
storesign_G[0].rotation = [0, 0, 0]
crate_D[0].position = [5.853800691468166, 1.8979708976606773, 0.16]
crate_D[0].rotation = [0, 0, 0]
cannedgood_group_2_G[0].position = [1.2813317055621538, 2.6977661953896765, 0.065]
cannedgood_group_2_G[0].rotation = [0, 0, 0]
beverageitem_group_2[0].position = [5.903873827883084, 1.2435189656828989, 0.12]
beverageitem_group_2[0].rotation = [0, 0, 0]
glassbottle_X[0].position = [3.3571456652301475, 6.568423614380337, 0.12]
glassbottle_X[0].rotation = [0, 0, 0]
cannedgood_group_2_H[0].position = [3.7203449206340373, 7.654878468917389, 0.09]
cannedgood_group_2_H[0].rotation = [0, 0, 0]
glassbottle_Y[0].position = [1.8189927249288027, 5.233740730275854, 0.12]
glassbottle_Y[0].rotation = [0, 0, 0]
sign[0].position = [1.1580031854316448, 3.6637828210584793, 0.15]
sign[0].rotation = [0, 0, 0]
cannedgood_group_2_I[0].position = [1.0865790933069754, 0.0864816100289243, 0.075]
cannedgood_group_2_I[0].rotation = [0, 0, 0]
cannedvegetable_E[0].position = [3.183444937156437, 4.663882396998379, 0.055]
cannedvegetable_E[0].rotation = [0, 0, 0]
beverage_J[0].position = [1.3565024665110192, 0.7839214261626584, 0.13]
beverage_J[0].rotation = [0, 0, 0]
storesign_H[0].position = [3.2302385332828, 1.508655977148572, 0.19]
storesign_H[0].rotation = [0, 0, 0]
lightfixture_H[0].position = [4.9493130574964335, 0.3637548207043855, 0.2]
lightfixture_H[0].rotation = [0, 0, 0]
storesign_I[0].position = [3.428310541741063, 2.8202861114352693, 0.19]
storesign_I[0].rotation = [0, 0, 0]

solver.constraints = []

# Helper anchors and placement functions. Exact-position constraints preserve the
# designed clearances, while semantic constraints allow later solver adjustment.
_room_center = AssetInstance(position=[3.00, 4.00, 1.00])


def _orientation_anchor(yaw):
    return AssetInstance(rotation=[0, 0, yaw])


def _place_floor(asset_obj, position, yaw=0.0):
    asset_obj[0].position = position
    asset_obj[0].rotation = [0, 0, yaw]

    # Pin the floor object to its planned position and preserve its orientation.
    solver.distance_constraint(
        asset_obj[0],
        AssetInstance(position=position),
        0,
        0,
        weight=10,
    )
    solver.align_with(asset_obj[0], _orientation_anchor(yaw))


def _place_against_wall(asset_obj, wall, position, yaw):
    asset_obj[0].position = position
    asset_obj[0].rotation = [0, 0, yaw]

    # Wall contact is the primary semantic constraint.
    solver.against_wall(asset_obj[0], wall)
    solver.distance_constraint(
        asset_obj[0],
        AssetInstance(position=position),
        0,
        0,
        weight=10,
    )
    solver.align_with(asset_obj[0], _orientation_anchor(yaw))


def _place_on_surface(asset_obj, support_obj, x, y, yaw=None):
    if yaw is None:
        yaw = support_obj[0].rotation[2]

    # Compute the object's center from the support's top surface.
    z = (
        support_obj[0].position[2]
        + support_obj.size[2] / 2
        + asset_obj.size[2] / 2
    )
    position = [x, y, z]
    asset_obj[0].position = position
    asset_obj[0].rotation = [0, 0, yaw]

    # The support relationship is listed first because it is the key semantic.
    solver.on_top_of(asset_obj[0], support_obj[0])
    solver.distance_constraint(
        asset_obj[0],
        AssetInstance(position=position),
        0,
        0,
        weight=10,
    )
    solver.align_with(asset_obj[0], support_obj[0])


# ---------------------------------------------------------------------------
# Main fixtures and furniture
# ---------------------------------------------------------------------------

# Four tall shelves form a continuous merchandise run along the right wall.
# They face inward and leave the two doors and the south-wall window clear.
_place_against_wall(
    shelf_A, walls[0], [5.80, 0.75, shelf_A.size[2] / 2], radians(180)
)
_place_against_wall(
    shelf_B, walls[0], [5.79, 2.15, shelf_B.size[2] / 2], radians(180)
)
_place_against_wall(
    shelf_C, walls[0], [5.775, 3.70, shelf_C.size[2] / 2], radians(180)
)
_place_against_wall(
    shelf_D, walls[0], [5.79, 5.25, shelf_D.size[2] / 2], radians(180)
)

# The checkout area occupies the northwest side, outside the top-door opening
# at x=1.65 and outside the west-door opening centered at y=3.04.
_place_against_wall(
    counter, walls[2], [0.375, 6.55, counter.size[2] / 2], 0.0
)
_place_against_wall(
    case, walls[2], [0.35, 4.45, case.size[2] / 2], 0.0
)

# Central sampling table and seating retain broad circulation aisles.
_place_floor(table, [3.50, 5.25, table.size[2] / 2], 0.0)

_place_floor(chair_A, [2.75, 5.25, chair_A.size[2] / 2], 0.0)
solver.point_towards(chair_A[0], table[0])

_place_floor(chair_B, [4.25, 5.25, chair_B.size[2] / 2], radians(180))
solver.point_towards(chair_B[0], table[0])

_place_floor(stool_A, [3.50, 4.25, stool_A.size[2] / 2], radians(90))
solver.point_towards(stool_A[0], table[0])

_place_floor(stool_B, [3.50, 6.25, stool_B.size[2] / 2], radians(-90))
solver.point_towards(stool_B[0], table[0])

# ---------------------------------------------------------------------------
# Floor crates and larger loose goods
# ---------------------------------------------------------------------------

# Required ordering: o0089 (cratefloor_B) lies between o0112
# (cratefloor_D) and o0147 (cratefloor_F).
_place_floor(
    cratefloor_D, [1.65, 1.45, cratefloor_D.size[2] / 2], radians(90)
)
_place_floor(
    cratefloor_B, [2.65, 1.45, cratefloor_B.size[2] / 2], radians(90)
)
_place_floor(
    cratefloor_F, [3.65, 1.45, cratefloor_F.size[2] / 2], radians(90)
)

solver.distance_constraint(
    cratefloor_B[0], cratefloor_D[0], 1.00, 1.00, weight=10
)
solver.distance_constraint(
    cratefloor_B[0], cratefloor_F[0], 1.00, 1.00, weight=10
)
solver.align_with(cratefloor_B[0], cratefloor_D[0])
solver.align_with(cratefloor_F[0], cratefloor_D[0])

# Remaining floor crates form a second tidy produce row.
_place_floor(
    cratefloor_A, [1.65, 2.25, cratefloor_A.size[2] / 2], radians(90)
)
_place_floor(
    cratefloor_C, [2.65, 2.25, cratefloor_C.size[2] / 2], radians(90)
)
_place_floor(
    cratefloor_E, [3.65, 2.25, cratefloor_E.size[2] / 2], radians(90)
)

_place_floor(crate_A, [4.75, 1.35, crate_A.size[2] / 2], 0.0)
_place_floor(crate_B, [4.75, 2.20, crate_B.size[2] / 2], 0.0)
_place_floor(crate_C, [4.75, 3.05, crate_C.size[2] / 2], 0.0)
_place_floor(crate_D, [4.75, 3.90, crate_D.size[2] / 2], 0.0)

# Bags and flour sacks sit beside the service area without entering either
# doorway's approach aisle.
_place_floor(shoppingbag_A, [1.05, 4.05, shoppingbag_A.size[2] / 2], 0.0)
_place_floor(shoppingbag_B, [1.05, 4.80, shoppingbag_B.size[2] / 2], 0.0)
_place_floor(shoppingbag_C, [1.05, 5.55, shoppingbag_C.size[2] / 2], 0.0)

_place_floor(floursack_A, [1.55, 4.05, floursack_A.size[2] / 2], 0.0)
_place_floor(floursack_B, [1.55, 4.80, floursack_B.size[2] / 2], 0.0)
_place_floor(floursack_C, [1.55, 5.55, floursack_C.size[2] / 2], 0.0)

_place_floor(pottedplant, [4.90, 7.25, pottedplant.size[2] / 2], radians(180))

# Bottles explicitly described as floor bottles are grouped beside the produce
# crates, away from customer circulation.
_place_floor(
    glassbottlefloor_A,
    [4.35, 4.55, glassbottlefloor_A.size[2] / 2],
    radians(180),
)
_place_floor(
    glassbottlefloor_B,
    [4.60, 4.55, glassbottlefloor_B.size[2] / 2],
    radians(180),
)
_place_floor(
    glassbottlefloor_C,
    [4.85, 4.55, glassbottlefloor_C.size[2] / 2],
    radians(180),
)
_place_floor(
    glassbottlefloor_D,
    [5.10, 4.55, glassbottlefloor_D.size[2] / 2],
    radians(180),
)
_place_floor(
    glassbottlefloor_E,
    [5.35, 4.55, glassbottlefloor_E.size[2] / 2],
    radians(180),
)

# The scale and checkout bag occupy separate portions of the counter top.
_place_on_surface(scale, counter, 0.375, 6.05, 0.0)
_place_on_surface(shoppingbag_counter, counter, 0.375, 6.90, 0.0)

# ---------------------------------------------------------------------------
# Wall-mounted signs and sconces
# ---------------------------------------------------------------------------

# North-wall signs avoid the 0.90 m door centered at x=1.65.
_place_against_wall(
    storesign_A, walls[1], [3.00, 7.98, 1.75], radians(-90)
)
_place_against_wall(
    storesign_B, walls[1], [3.90, 7.975, 1.75], radians(-90)
)
_place_against_wall(
    storesign_C, walls[1], [4.75, 7.98, 1.75], radians(-90)
)

# South-wall signs avoid the window spanning approximately x=1.74 to x=2.84.
_place_against_wall(storesign_D, walls[3], [0.60, 0.025, 1.70], radians(90))
_place_against_wall(storesign_E, walls[3], [3.35, 0.02, 1.70], radians(90))
_place_against_wall(storesign_F, walls[3], [4.25, 0.02, 1.70], radians(90))
_place_against_wall(storesign_G, walls[3], [5.15, 0.025, 1.70], radians(90))

# West-wall signs are kept away from the door centered at y=3.04.
_place_against_wall(storesign_H, walls[2], [0.02, 1.15, 1.70], 0.0)
_place_against_wall(storesign_I, walls[2], [0.025, 4.95, 2.35], 0.0)
_place_against_wall(signcoffee, walls[2], [0.02, 5.85, 2.35], 0.0)
_place_against_wall(sign, walls[2], [0.02, 6.65, 2.35], 0.0)

# Wall sconces illuminate the upper corners and do not conflict with openings.
_place_against_wall(lightfixture_A, walls[2], [0.11, 7.30, 2.35], 0.0)
_place_against_wall(
    lightfixture_F, walls[0], [5.89, 7.35, 2.35], radians(180)
)

# Pendant fixtures form two rows over the central sales floor.
_pendant_layout = [
    (lightfixture_B, [2.35, 3.65, 2.75]),
    (lightfixture_C, [3.35, 3.65, 2.75]),
    (lightfixture_D, [4.35, 3.65, 2.75]),
    (lightfixture_E, [2.35, 6.65, 2.75]),
    (lightfixture_G, [3.35, 6.65, 2.75]),
    (lightfixture_H, [4.35, 6.65, 2.75]),
]
for _fixture_obj, _fixture_position in _pendant_layout:
    _place_floor(_fixture_obj, _fixture_position, 0.0)

# ---------------------------------------------------------------------------
# Small merchandise
# ---------------------------------------------------------------------------

# Small merchandise is distributed over the four shelves, display case, and
# sampling table. The first item is glassbottle_A (o0000), and the first support
# is shelf_A (o0005), explicitly satisfying the required on-top relationship.
_display_items = [
    glassbottle_A,
    glassbottle_table_A,
    cannedveg_A,
    beverageitem_A,
    beverageitem_B,
    beverage_A,
    cannedgood_A,
    glassbottle_B,
    beverageitem_C,
    beverageitem_D,
    beverageitem_E,
    cannedgood_B,
    cannedgood_C,
    beverage_B,
    cannedgood_D,
    cannedgood_E,
    glassbottle9b9b_A,
    cannedveg_B,
    glassbottle_shelf_A,
    glassbottle_C,
    pricetag_A,
    cannedvegetable_A,
    cannedgood_F,
    beverage_C,
    cannedgood_G,
    beverageitem_F,
    glassbottle_D,
    cannedgood_H,
    cannedgood_I,
    beverageitem_G,
    cannedgood_J,
    cannedgood_K,
    glassbottle_E,
    glassbottle_F,
    glassbottle_G,
    cannedgood_table,
    beverageitem_H,
    glassbottle9b_A,
    cannedgood_L,
    beverage_D,
    beverageitem_I,
    beverageitem_J,
    pricetag_B,
    beverageitem_K,
    cannedgood_M,
    glassbottle_shelf_B,
    cannedgood_N,
    cannedveg_C,
    cannedgood_O,
    cannedgood_P,
    cannedgoodcase,
    cannedveg_D,
    beverageitem_L,
    beverageitem_M,
    glassbottle9b_B,
    glassbottle_H,
    cannedgood_Q,
    glassbottle9b9b_B,
    glassbottle_I,
    glassbottle_J,
    beverageitem_N,
    glassbottle_K,
    cannedvegetable_B,
    cannedveg_E,
    beverageitem_O,
    glassbottle_L,
    beverageitem_P,
    pricetag_C,
    cannedveg_F,
    glassbottle_M,
    beverage_E,
    cannedgoodaa,
    cannedgood_R,
    glassbottle_N,
    glassbottle_table_B,
    glassbottle9b9b_C,
    beverageitem_Q,
    cannedgood_S,
    beverage_F,
    pricetag_D,
    glassbottle_O,
    glassbottle9b9b_D,
    cannedvegetable_C,
    beverageitem_R,
    cannedgood_T,
    beverage_G,
    beverageitem_S,
    glassbottle9b_C,
    beverageitem_T,
    cannedveg_G,
    cannedvegetable_9b_A,
    cannedveg9b9b_A,
    cannedgood_U,
    cannedgood_V,
    glassbottle_P,
    glassbottle_Q,
    cannedvegetable_9b_B,
    cannedgood_W,
    glassbottle_R,
    beverageitem_U,
    beverageitem_V,
    cannedgood_X,
    beverageitem_W,
    cannedgood_Y,
    cannedveg_H,
    cannedgood_Z,
    beverageitem_X,
    cannedgood_group_2_A,
    cannedgood_group_2_B,
    glassbottle9b9b_E,
    glassbottle_S,
    glassbottle_T,
    glassbottle_U,
    cannedvegetable_D,
    cannedgood_group_2_C,
    cannedveg_I,
    beverageitem_Y,
    cannedgood_group_2_D,
    beverage_H,
    beverage_I,
    cannedveg_J,
    cannedgood_group_2_E,
    cannedveg9b9b_B,
    beverageitem_Z,
    glassbottle_V,
    glassbottle_W,
    cannedgood_group_2_F,
    cannedgood_group_2_G,
    beverageitem_group_2,
    glassbottle_X,
    cannedgood_group_2_H,
    glassbottle_Y,
    cannedgood_group_2_I,
    cannedvegetable_E,
    beverage_J,
]

_display_supports = [
    shelf_A,
    shelf_B,
    shelf_C,
    shelf_D,
    case,
    table,
]

# Each support receives its own compact grid. Spacing is greater than the
# largest small-item footprint, preventing overlap between neighboring goods.
_support_counts = [0 for _ in _display_supports]

for _item_index, _item_obj in enumerate(_display_items):
    _support_index = _item_index % len(_display_supports)
    _support_obj = _display_supports[_support_index]
    _slot_index = _support_counts[_support_index]
    _support_counts[_support_index] += 1

    _spacing_x = 0.14
    _spacing_y = 0.15

    # Three columns fit safely on the narrowest shelf; wider surfaces use five.
    if _support_obj.size[0] < 0.55:
        _column_count = 3
    else:
        _column_count = 5

    _column = _slot_index % _column_count
    _row = _slot_index // _column_count

    _item_x = (
        _support_obj[0].position[0]
        - (_column_count - 1) * _spacing_x / 2
        + _column * _spacing_x
    )
    _item_y = (
        _support_obj[0].position[1]
        - _support_obj.size[1] / 2
        + 0.11
        + _row * _spacing_y
    )

    _place_on_surface(
        _item_obj,
        _support_obj,
        _item_x,
        _item_y,
        _support_obj[0].rotation[2],
    )

solver.constraints = []
shelf_C[0].position = [5.670444011688232, 3.700000047683716, 0.949999988079071]
shelf_C[0].rotation = [0, 0, -2.995859436361315]
shelf_C[0].optimize = 2
glassbottle9b9b_C[0].position = [5.650000095367432, 5.309999942779541, 2.075000047683716]
glassbottle9b9b_C[0].rotation = [0, 0, -3.118801008297538]
glassbottle9b9b_C[0].optimize = 2
beverageitem_S[0].position = [5.895083904266357, 3.656845808029175, 2.0199999809265137]
beverageitem_S[0].rotation = [0, 0, -3.1188010009295697]
beverageitem_S[0].optimize = 2
storesign_F[0].position = [4.25, 0.011367769911885262, 0.17499999701976776]
storesign_F[0].rotation = [0, 0, 1.5733372437234565]
storesign_F[0].optimize = 2
cannedgood_I[0].position = [0.6299999952316284, 3.809999942779541, 1.340000033378601]
cannedgood_I[0].rotation = [0, 0, 0.022791645292255164]
cannedgood_I[0].optimize = 2
cannedveg_G[0].position = [3.7799999713897705, 5.159999847412109, 0.8199999928474426]
cannedveg_G[0].rotation = [0, 0, 0.02279165728452036]
cannedveg_G[0].optimize = 2
shelf_B[0].position = [5.693080902099609, 2.1500000953674316, 1.0]
shelf_B[0].rotation = [0, 0, -2.995859436361315]
shelf_B[0].optimize = 2
cannedveg_D[0].position = [5.929999828338623, 5.010000228881836, 2.0199999809265137]
cannedveg_D[0].rotation = [0, 0, -3.118801008297538]
cannedveg_D[0].optimize = 2
glassbottle9b9b_A[0].position = [0.3499999940395355, 3.809999942779541, 1.375]
glassbottle9b9b_A[0].rotation = [0, 0, 0.022791645292255164]
glassbottle9b9b_A[0].optimize = 2
glassbottle9b_B[0].position = [5.659999847412109, 0.7099999785423279, 2.0250000953674316]
glassbottle9b_B[0].rotation = [0, 0, -3.1188010009295697]
glassbottle9b_B[0].optimize = 2
floursack_B[0].position = [1.5499999523162842, 4.800000190734863, 0.23999999463558197]
floursack_B[0].rotation = [0, 0, 0.00942477746072377]
floursack_B[0].optimize = 2
cannedgood_group_2_D[0].position = [5.789999961853027, 5.610000133514404, 2.0399999618530273]
cannedgood_group_2_D[0].rotation = [0, 0, -3.118801008297538]
cannedgood_group_2_D[0].optimize = 2
beverage_C[0].position = [3.640000104904175, 4.860000133514404, 0.8650000095367432]
beverage_C[0].rotation = [0, 0, 0.02279165728452036]
beverage_C[0].optimize = 2
glassbottlefloor_E[0].position = [5.349999904632568, 4.550000190734863, 0.13500000536441803]
glassbottlefloor_E[0].rotation = [0, 0, -3.1321678761290697]
glassbottlefloor_E[0].optimize = 2
glassbottle_shelf_A[0].position = [5.659999847412109, 0.4099999964237213, 2.0399999618530273]
glassbottle_shelf_A[0].rotation = [0, 0, -3.1188010009295697]
glassbottle_shelf_A[0].optimize = 2
cannedveg_C[0].position = [3.5, 5.010000228881836, 0.8149999976158142]
cannedveg_C[0].rotation = [0, 0, 0.02279165728452036]
cannedveg_C[0].optimize = 2
cratefloor_A[0].position = [1.649999976158142, 2.25, 0.15000000596046448]
cratefloor_A[0].rotation = [0, 0, 1.5802211042556205]
cratefloor_A[0].optimize = 2
glassbottlefloor_D[0].position = [5.099999904632568, 4.550000190734863, 0.13500000536441803]
glassbottlefloor_D[0].rotation = [0, 0, -3.1321678761290697]
glassbottlefloor_D[0].optimize = 2
pricetag_B[0].position = [5.800000190734863, 0.5600000023841858, 1.934999942779541]
pricetag_B[0].rotation = [0, 0, -3.1188010009295697]
pricetag_B[0].optimize = 2
beverageitem_C[0].position = [5.775000095367432, 3.059999942779541, 2.0]
beverageitem_C[0].rotation = [0, 0, -3.1188010009295697]
beverageitem_C[0].optimize = 2
beverage_D[0].position = [5.650000095367432, 5.010000228881836, 2.065000057220459]
beverage_D[0].rotation = [0, 0, -3.118801008297538]
beverage_D[0].optimize = 2
chair_A[0].position = [2.75, 5.25, 0.4399999976158142]
chair_A[0].rotation = [0, 0, 0.01256637125682779]
chair_A[0].optimize = 2
cannedgood_B[0].position = [3.359999895095825, 4.860000133514404, 0.824999988079071]
cannedgood_B[0].rotation = [0, 0, 0.02279165728452036]
cannedgood_B[0].optimize = 2
storesign_G[0].position = [5.150000095367432, 0.016124853864312172, 0.17499999701976776]
storesign_G[0].rotation = [0, 0, 1.5733372440233822]
storesign_G[0].optimize = 2
pricetag_C[0].position = [5.9181694984436035, 2.0081262588500977, 2.0299999713897705]
pricetag_C[0].rotation = [0, 0, -3.1188010009295697]
pricetag_C[0].optimize = 2
cannedveg_F[0].position = [5.914999961853027, 3.509999990463257, 1.9649999141693115]
cannedveg_F[0].rotation = [0, 0, -3.1188010009295697]
cannedveg_F[0].optimize = 2
crate_D[0].position = [4.75, 3.9000000953674316, 0.1599999964237213]
crate_D[0].rotation = [0, 0, 0.00942477746072377]
crate_D[0].optimize = 2
glassbottle_G[0].position = [0.1766723394393921, 3.9762089252471924, 1.3899999856948853]
glassbottle_G[0].rotation = [0, 0, 0.022791645292255164]
glassbottle_G[0].optimize = 2
cratefloor_F[0].position = [3.6500000953674316, 1.4500000476837158, 0.15000000596046448]
cratefloor_F[0].rotation = [0, 0, 1.5967522972770969]
cratefloor_F[0].optimize = 2
glassbottle_K[0].position = [5.789999961853027, 2.009999990463257, 2.140000104904175]
glassbottle_K[0].rotation = [0, 0, -3.1188010009295697]
glassbottle_K[0].optimize = 2
beverageitem_M[0].position = [3.640000104904175, 5.010000228881836, 0.8700000047683716]
beverageitem_M[0].rotation = [0, 0, 0.02279165728452036]
beverageitem_M[0].optimize = 2
storesign_I[0].position = [0.016124853864312172, 4.949999809265137, 0.1899999976158142]
storesign_I[0].rotation = [0, 0, 0.0025409160063866866]
storesign_I[0].optimize = 2
shoppingbag_B[0].position = [1.0499999523162842, 4.800000190734863, 0.20999999344348907]
shoppingbag_B[0].rotation = [0, 0, 0.00942477746072377]
shoppingbag_B[0].optimize = 2
lightfixture_D[0].position = [4.349999904632568, 3.6500000953674316, 0.18000000715255737]
lightfixture_D[0].rotation = [0, 0, 0.00942477746072377]
lightfixture_D[0].optimize = 2
signcoffee[0].position = [0.011367769911885262, 5.849999904632568, 0.14000000059604645]
signcoffee[0].rotation = [0, 0, 0.0025409202949315235]
signcoffee[0].optimize = 2
beverageitem_A[0].position = [5.650000095367432, 4.710000038146973, 2.0399999618530273]
beverageitem_A[0].rotation = [0, 0, -3.118801008297538]
beverageitem_A[0].optimize = 2
beverageitem_B[0].position = [0.19895046949386597, 3.8295938968658447, 1.309999942779541]
beverageitem_B[0].rotation = [0, 0, 0.022791645292255164]
beverageitem_B[0].optimize = 2
cannedveg9b9b_A[0].position = [5.650000095367432, 2.309999942779541, 2.0799999237060547]
cannedveg9b9b_A[0].rotation = [0, 0, -3.1188010009295697]
cannedveg9b9b_A[0].optimize = 2
lightfixture_A[0].position = [0.10027995705604553, 7.300000190734863, 0.20999999344348907]
lightfixture_A[0].rotation = [0, 0, 0.002540922439204702]
lightfixture_A[0].optimize = 2
pottedplant[0].position = [4.900000095367432, 7.25, 0.375]
pottedplant[0].rotation = [0, 0, -3.1321678761290697]
pottedplant[0].optimize = 2
shoppingbag_A[0].position = [1.0499999523162842, 4.050000190734863, 0.20999999344348907]
shoppingbag_A[0].rotation = [0, 0, 0.00942477746072377]
shoppingbag_A[0].optimize = 2
glassbottle_N[0].position = [5.650000095367432, 2.1600000858306885, 2.134999990463257]
glassbottle_N[0].rotation = [0, 0, -3.1188010009295697]
glassbottle_N[0].optimize = 2
beverageitem_U[0].position = [5.789999961853027, 5.460000038146973, 2.059999942779541]
beverageitem_U[0].rotation = [0, 0, -3.118801008297538]
beverageitem_U[0].optimize = 2
beverageitem_V[0].position = [0.20999999344348907, 4.260000228881836, 1.3250000476837158]
beverageitem_V[0].rotation = [0, 0, 0.022791645292255164]
beverageitem_V[0].optimize = 2
cannedvegetable_9b_A[0].position = [5.659999847412109, 1.0099999904632568, 1.9649999141693115]
cannedvegetable_9b_A[0].rotation = [0, 0, -3.1188010009295697]
cannedvegetable_9b_A[0].optimize = 2
cannedgood_group_2_C[0].position = [5.800000190734863, 1.159999966621399, 1.9850000143051147]
cannedgood_group_2_C[0].rotation = [0, 0, -3.1188010009295697]
cannedgood_group_2_C[0].optimize = 2
floursack_A[0].position = [1.5499999523162842, 4.050000190734863, 0.20999999344348907]
floursack_A[0].rotation = [0, 0, 0.00942477746072377]
floursack_A[0].optimize = 2
glassbottle9b9b_D[0].position = [5.789999961853027, 5.309999942779541, 2.075000047683716]
glassbottle9b9b_D[0].rotation = [0, 0, -3.118801008297538]
glassbottle9b9b_D[0].optimize = 2
beverageitem_E[0].position = [0.20999999344348907, 3.809999942779541, 1.309999942779541]
beverageitem_E[0].rotation = [0, 0, 0.022791645292255164]
beverageitem_E[0].optimize = 2
glassbottle_A[0].position = [5.659999847412109, 0.25999999046325684, 2.0299999713897705]
glassbottle_A[0].rotation = [0, 0, -3.1188010009295697]
glassbottle_A[0].optimize = 2
cannedgood_V[0].position = [5.650000095367432, 5.460000038146973, 2.0250000953674316]
cannedgood_V[0].rotation = [0, 0, -3.118801008297538]
cannedgood_V[0].optimize = 2
glassbottle_M[0].position = [5.929999828338623, 5.159999847412109, 2.075000047683716]
glassbottle_M[0].rotation = [0, 0, -3.118801008297538]
glassbottle_M[0].optimize = 2
beverageitem_group_2[0].position = [5.635000228881836, 4.110000133514404, 2.0199999809265137]
beverageitem_group_2[0].rotation = [0, 0, -3.1188010009295697]
beverageitem_group_2[0].optimize = 2
glassbottle_table_A[0].position = [5.650000095367432, 1.559999942779541, 2.134999990463257]
glassbottle_table_A[0].rotation = [0, 0, -3.1188010009295697]
glassbottle_table_A[0].optimize = 2
floursack_C[0].position = [1.5499999523162842, 5.550000190734863, 0.20999999344348907]
floursack_C[0].rotation = [0, 0, 0.00942477746072377]
floursack_C[0].optimize = 2
glassbottle9b9b_E[0].position = [5.650000095367432, 2.4600000381469727, 2.134999990463257]
glassbottle9b9b_E[0].rotation = [0, 0, -3.1188010009295697]
glassbottle9b9b_E[0].optimize = 2
shoppingbag_C[0].position = [1.0499999523162842, 5.550000190734863, 0.20999999344348907]
shoppingbag_C[0].rotation = [0, 0, 0.00942477746072377]
shoppingbag_C[0].optimize = 2
scale[0].position = [0.375, 6.050000190734863, 1.2400000095367432]
scale[0].rotation = [0, 0, 0.02278960013808119]
scale[0].optimize = 2
glassbottle_B[0].position = [5.789999961853027, 1.559999942779541, 2.119999885559082]
glassbottle_B[0].rotation = [0, 0, -3.1188010009295697]
glassbottle_B[0].optimize = 2
storesign_A[0].position = [3.0, 7.9885125160217285, 0.17499999701976776]
storesign_A[0].rotation = [0, 0, -1.5682554107885098]
storesign_A[0].optimize = 2
glassbottle9b_C[0].position = [5.898751258850098, 5.305251598358154, 2.075000047683716]
glassbottle9b_C[0].rotation = [0, 0, -3.118801008297538]
glassbottle9b_C[0].optimize = 2
storesign_B[0].position = [3.9000000953674316, 7.983956336975098, 0.1599999964237213]
storesign_B[0].rotation = [0, 0, -1.568255409566411]
storesign_B[0].optimize = 2
cannedgood_S[0].position = [3.5, 5.159999847412109, 0.8349999785423279]
cannedgood_S[0].rotation = [0, 0, 0.02279165728452036]
cannedgood_S[0].optimize = 2
cannedgood_Q[0].position = [5.635000228881836, 3.509999990463257, 1.975000023841858]
cannedgood_Q[0].rotation = [0, 0, -3.1188010009295697]
cannedgood_Q[0].optimize = 2
beverage_F[0].position = [5.800000190734863, 0.8600000143051147, 2.0299999713897705]
beverage_F[0].rotation = [0, 0, -3.1188010009295697]
beverage_F[0].optimize = 2
storesign_D[0].position = [0.6000000238418579, 0.016124853864312172, 0.17499999701976776]
storesign_D[0].rotation = [0, 0, 1.5733372440233822]
storesign_D[0].optimize = 2
glassbottle_V[0].position = [0.10983801633119583, 4.416053295135498, 1.3849999904632568]
glassbottle_V[0].rotation = [0, 0, 0.022791645292255164]
glassbottle_V[0].optimize = 2
cannedgood_group_2_H[0].position = [0.20999999344348907, 4.409999847412109, 1.340000033378601]
cannedgood_group_2_H[0].rotation = [0, 0, 0.022791645292255164]
cannedgood_group_2_H[0].optimize = 2
cratefloor_B[0].position = [2.6500000953674316, 1.4500000476837158, 0.15000000596046448]
cratefloor_B[0].rotation = [0, 0, 1.5896488853676778]
cratefloor_B[0].optimize = 2
cannedvegetable_C[0].position = [0.49000000953674316, 4.110000133514404, 1.3049999475479126]
cannedvegetable_C[0].rotation = [0, 0, 0.022791645292255164]
cannedvegetable_C[0].optimize = 2
cannedveg9b9b_B[0].position = [5.848731517791748, 3.9495041370391846, 1.9800000190734863]
cannedveg9b9b_B[0].rotation = [0, 0, -3.1188010009295697]
cannedveg9b9b_B[0].optimize = 2
cannedgoodcase[0].position = [5.914999961853027, 3.359999895095825, 1.959999918937683]
cannedgoodcase[0].rotation = [0, 0, -3.1188010009295697]
cannedgoodcase[0].optimize = 2
cannedvegetable_9b_B[0].position = [5.800000190734863, 1.0099999904632568, 1.9649999141693115]
cannedvegetable_9b_B[0].rotation = [0, 0, -3.1188010009295697]
cannedvegetable_9b_B[0].optimize = 2
cannedgood_M[0].position = [5.775000095367432, 3.359999895095825, 1.9900000095367432]
cannedgood_M[0].rotation = [0, 0, -3.1188010009295697]
cannedgood_M[0].optimize = 2
sign[0].position = [0.011367769911885262, 6.650000095367432, 0.15000000596046448]
sign[0].rotation = [0, 0, 0.0025409193727581954]
sign[0].optimize = 2
beverageitem_K[0].position = [5.789999961853027, 1.8600000143051147, 2.109999895095825]
beverageitem_K[0].rotation = [0, 0, -3.1188010009295697]
beverageitem_K[0].optimize = 2
lightfixture_C[0].position = [3.3499999046325684, 3.6500000953674316, 0.1899999976158142]
lightfixture_C[0].rotation = [0, 0, 0.00942477746072377]
lightfixture_C[0].optimize = 2
case[0].position = [0.4486973285675049, 4.449999809265137, 0.625]
case[0].rotation = [0, 0, 0.1395028617679359]
case[0].optimize = 2
glassbottle_D[0].position = [5.775000095367432, 3.2100000381469727, 2.0350000858306885]
glassbottle_D[0].rotation = [0, 0, -3.1188010009295697]
glassbottle_D[0].optimize = 2
beverageitem_R[0].position = [3.640000104904175, 5.159999847412109, 0.8600000143051147]
beverageitem_R[0].rotation = [0, 0, 0.02279165728452036]
beverageitem_R[0].optimize = 2
beverageitem_J[0].position = [3.359999895095825, 5.010000228881836, 0.8550000190734863]
beverageitem_J[0].rotation = [0, 0, 0.02279165728452036]
beverageitem_J[0].optimize = 2
counter[0].position = [0.38749873638153076, 6.550000190734863, 0.4749999940395355]
counter[0].rotation = [0, 0, 0.01498390331397522]
counter[0].optimize = 2
cannedgood_K[0].position = [5.929999828338623, 1.7100000381469727, 2.069999933242798]
cannedgood_K[0].rotation = [0, 0, -3.1188010009295697]
cannedgood_K[0].optimize = 2
lightfixture_B[0].position = [2.3499999046325684, 3.6500000953674316, 0.20999999344348907]
lightfixture_B[0].rotation = [0, 0, 0.00942477746072377]
lightfixture_B[0].optimize = 2
cannedgood_R[0].position = [5.659999847412109, 0.8600000143051147, 1.975000023841858]
cannedgood_R[0].rotation = [0, 0, -3.1188010009295697]
cannedgood_R[0].optimize = 2
cratefloor_C[0].position = [2.6500000953674316, 2.25, 0.15000000596046448]
cratefloor_C[0].rotation = [0, 0, 1.5802211042556205]
cratefloor_C[0].optimize = 2
glassbottle_R[0].position = [5.775000095367432, 3.809999942779541, 2.0450000762939453]
glassbottle_R[0].rotation = [0, 0, -3.1188010009295697]
glassbottle_R[0].optimize = 2
cannedgood_group_2_A[0].position = [3.5, 5.309999942779541, 0.8349999785423279]
cannedgood_group_2_A[0].rotation = [0, 0, 0.02279165728452036]
cannedgood_group_2_A[0].optimize = 2
cannedvegetable_B[0].position = [5.775000095367432, 3.509999990463257, 1.9549999237060547]
cannedvegetable_B[0].rotation = [0, 0, -3.1188010009295697]
cannedvegetable_B[0].optimize = 2
cannedveg_E[0].position = [5.789999961853027, 5.159999847412109, 2.0299999713897705]
cannedveg_E[0].rotation = [0, 0, -3.118801008297538]
cannedveg_E[0].optimize = 2
table[0].position = [3.5, 5.25, 0.375]
table[0].rotation = [0, 0, 0.16022121977013765]
table[0].optimize = 2
cannedveg_I[0].position = [5.789999961853027, 2.4600000381469727, 2.069999933242798]
cannedveg_I[0].rotation = [0, 0, -3.1188010009295697]
cannedveg_I[0].optimize = 2
beverageitem_H[0].position = [5.659999847412109, 0.5600000023841858, 1.9900000095367432]
beverageitem_H[0].rotation = [0, 0, -3.1188010009295697]
beverageitem_H[0].optimize = 2
glassbottle_W[0].position = [3.2200000286102295, 5.460000038146973, 0.8849999904632568]
glassbottle_W[0].rotation = [0, 0, 0.02279165728452036]
glassbottle_W[0].optimize = 2
cannedgood_H[0].position = [5.789999961853027, 4.860000133514404, 2.0250000953674316]
cannedgood_H[0].rotation = [0, 0, -3.118801008297538]
cannedgood_H[0].optimize = 2
glassbottlefloor_B[0].position = [4.599999904632568, 4.550000190734863, 0.13500000536441803]
glassbottlefloor_B[0].rotation = [0, 0, -3.1321678761290697]
glassbottlefloor_B[0].optimize = 2
chair_B[0].position = [4.25, 5.25, 0.4399999976158142]
chair_B[0].rotation = [0, 0, -3.1290262823329655]
chair_B[0].optimize = 2
glassbottle_O[0].position = [5.775000095367432, 3.6600000858306885, 2.0399999618530273]
glassbottle_O[0].rotation = [0, 0, -3.1188010009295697]
glassbottle_O[0].optimize = 2
cannedgood_group_2_G[0].position = [5.650000095367432, 2.609999895095825, 2.065000057220459]
cannedgood_group_2_G[0].rotation = [0, 0, -3.1188010009295697]
cannedgood_group_2_G[0].optimize = 2
beverageitem_X[0].position = [0.3499999940395355, 4.260000228881836, 1.350000023841858]
beverageitem_X[0].rotation = [0, 0, 0.022791645292255164]
beverageitem_X[0].optimize = 2
beverage_A[0].position = [3.2334585189819336, 4.862174987792969, 0.8100000023841858]
beverage_A[0].rotation = [0, 0, 0.02279165728452036]
beverage_A[0].optimize = 2
beverageitem_F[0].position = [5.789999961853027, 1.7100000381469727, 2.075000047683716]
beverageitem_F[0].rotation = [0, 0, -3.1188010009295697]
beverageitem_F[0].optimize = 2
glassbottle_F[0].position = [5.929999828338623, 4.860000133514404, 2.0950000286102295]
glassbottle_F[0].rotation = [0, 0, -3.118801008297538]
glassbottle_F[0].optimize = 2
cannedveg_J[0].position = [5.848453044891357, 1.1455003023147583, 1.9700000286102295]
cannedveg_J[0].rotation = [0, 0, -3.1188010009295697]
cannedveg_J[0].optimize = 2
glassbottle_table_B[0].position = [5.635000228881836, 3.6600000858306885, 2.0350000858306885]
glassbottle_table_B[0].rotation = [0, 0, -3.1188010009295697]
glassbottle_table_B[0].optimize = 2
cannedgood_Z[0].position = [5.876473426818848, 5.451866626739502, 2.0250000953674316]
cannedgood_Z[0].rotation = [0, 0, -3.118801008297538]
cannedgood_Z[0].optimize = 2
cannedgood_N[0].position = [0.3499999940395355, 3.9600000381469727, 1.309999942779541]
cannedgood_N[0].rotation = [0, 0, 0.022791645292255164]
cannedgood_N[0].optimize = 2
crate_B[0].position = [4.75, 2.200000047683716, 0.1599999964237213]
crate_B[0].rotation = [0, 0, 0.00942477746072377]
crate_B[0].optimize = 2
cannedvegetable_D[0].position = [3.640000104904175, 5.309999942779541, 0.8050000071525574]
cannedvegetable_D[0].rotation = [0, 0, 0.02279165728452036]
cannedvegetable_D[0].optimize = 2
cannedgood_table[0].position = [3.2200000286102295, 5.010000228881836, 0.8400000333786011]
cannedgood_table[0].rotation = [0, 0, 0.02279165728452036]
cannedgood_table[0].optimize = 2
glassbottle_X[0].position = [5.650000095367432, 5.760000228881836, 2.069999933242798]
glassbottle_X[0].rotation = [0, 0, -3.118801008297538]
glassbottle_X[0].optimize = 2
glassbottle_E[0].position = [5.914999961853027, 3.2100000381469727, 2.0350000858306885]
glassbottle_E[0].rotation = [0, 0, -3.1188010009295697]
glassbottle_E[0].optimize = 2
stool_B[0].position = [3.5, 6.25, 0.33500000834465027]
stool_B[0].rotation = [0, 0, -1.5582299555380688]
stool_B[0].optimize = 2
glassbottle_H[0].position = [5.650000095367432, 2.009999990463257, 2.119999885559082]
glassbottle_H[0].rotation = [0, 0, -3.1188010009295697]
glassbottle_H[0].optimize = 2
cannedgood_X[0].position = [3.359999895095825, 5.309999942779541, 0.8349999785423279]
cannedgood_X[0].rotation = [0, 0, 0.02279165728452036]
cannedgood_X[0].optimize = 2
glassbottle9b_A[0].position = [5.650000095367432, 1.8600000143051147, 2.125]
glassbottle9b_A[0].rotation = [0, 0, -3.1188010009295697]
glassbottle9b_A[0].optimize = 2
beverageitem_O[0].position = [0.1543942093849182, 4.122823715209961, 1.3700000047683716]
beverageitem_O[0].rotation = [0, 0, 0.022791645292255164]
beverageitem_O[0].optimize = 2
cannedgood_O[0].position = [5.940000057220459, 0.5600000023841858, 1.9800000190734863]
cannedgood_O[0].rotation = [0, 0, -3.1188010009295697]
cannedgood_O[0].optimize = 2
cratefloor_E[0].position = [3.6500000953674316, 2.25, 0.15000000596046448]
cratefloor_E[0].rotation = [0, 0, 1.5802211042556205]
cratefloor_E[0].optimize = 2
beverageitem_T[0].position = [0.6299999952316284, 4.110000133514404, 1.3550000190734863]
beverageitem_T[0].rotation = [0, 0, 0.022791645292255164]
beverageitem_T[0].optimize = 2
beverageitem_L[0].position = [0.49000000953674316, 3.9600000381469727, 1.3550000190734863]
beverageitem_L[0].rotation = [0, 0, 0.022791645292255164]
beverageitem_L[0].optimize = 2
glassbottle_J[0].position = [3.7799999713897705, 5.010000228881836, 0.8849999904632568]
glassbottle_J[0].rotation = [0, 0, 0.02279165728452036]
glassbottle_J[0].optimize = 2
beverageitem_G[0].position = [3.7799999713897705, 4.860000133514404, 0.8400000333786011]
beverageitem_G[0].rotation = [0, 0, 0.02279165728452036]
beverageitem_G[0].optimize = 2
beverageitem_D[0].position = [5.789999961853027, 4.710000038146973, 2.0399999618530273]
beverageitem_D[0].rotation = [0, 0, -3.118801008297538]
beverageitem_D[0].optimize = 2
beverage_E[0].position = [0.20999999344348907, 4.110000133514404, 1.309999942779541]
beverage_E[0].rotation = [0, 0, 0.022791645292255164]
beverage_E[0].optimize = 2
shelf_D[0].position = [5.704736232757568, 5.25, 0.9750000238418579]
shelf_D[0].rotation = [0, 0, -3.002089791821857]
shelf_D[0].optimize = 2
glassbottle_Q[0].position = [3.2200000286102295, 5.309999942779541, 0.8899999856948853]
glassbottle_Q[0].rotation = [0, 0, 0.02279165728452036]
glassbottle_Q[0].optimize = 2
glassbottle_S[0].position = [5.635000228881836, 3.9600000381469727, 2.0199999809265137]
glassbottle_S[0].rotation = [0, 0, -3.1188010009295697]
glassbottle_S[0].optimize = 2
glassbottle_U[0].position = [0.49000000953674316, 4.260000228881836, 1.3849999904632568]
glassbottle_U[0].rotation = [0, 0, 0.022791645292255164]
glassbottle_U[0].optimize = 2
cannedveg_B[0].position = [3.5, 4.860000133514404, 0.8299999833106995]
cannedveg_B[0].rotation = [0, 0, 0.02279165728452036]
cannedveg_B[0].optimize = 2
glassbottle_shelf_B[0].position = [5.789999961853027, 5.010000228881836, 2.0900001525878906]
glassbottle_shelf_B[0].rotation = [0, 0, -3.118801008297538]
glassbottle_shelf_B[0].optimize = 2
beverageitem_P[0].position = [5.91798210144043, 0.7065126895904541, 2.0]
beverageitem_P[0].rotation = [0, 0, -3.1188010009295697]
beverageitem_P[0].optimize = 2
cannedgood_Y[0].position = [5.871817111968994, 2.3007845878601074, 2.065000057220459]
cannedgood_Y[0].rotation = [0, 0, -3.1188010009295697]
cannedgood_Y[0].optimize = 2
cannedgood_A[0].position = [5.800000190734863, 0.25999999046325684, 1.959999918937683]
cannedgood_A[0].rotation = [0, 0, -3.1188010009295697]
cannedgood_A[0].optimize = 2
cannedgood_group_2_B[0].position = [5.659999847412109, 1.159999966621399, 1.975000023841858]
cannedgood_group_2_B[0].rotation = [0, 0, -3.1188010009295697]
cannedgood_group_2_B[0].optimize = 2
crate_C[0].position = [4.75, 3.049999952316284, 0.1599999964237213]
crate_C[0].rotation = [0, 0, 0.00942477746072377]
crate_C[0].optimize = 2
crate_A[0].position = [4.75, 1.350000023841858, 0.1599999964237213]
crate_A[0].rotation = [0, 0, 0.00942477746072377]
crate_A[0].optimize = 2
cannedgood_C[0].position = [5.940000057220459, 0.25999999046325684, 1.959999918937683]
cannedgood_C[0].rotation = [0, 0, -3.1188010009295697]
cannedgood_C[0].optimize = 2
pricetag_A[0].position = [5.635000228881836, 3.2100000381469727, 1.934999942779541]
pricetag_A[0].rotation = [0, 0, -3.1188010009295697]
pricetag_A[0].optimize = 2
cannedgood_F[0].position = [0.49000000953674316, 3.809999942779541, 1.309999942779541]
cannedgood_F[0].rotation = [0, 0, 0.022791645292255164]
cannedgood_F[0].optimize = 2
beverageitem_I[0].position = [0.20999999344348907, 3.9600000381469727, 1.3250000476837158]
beverageitem_I[0].rotation = [0, 0, 0.022791645292255164]
beverageitem_I[0].optimize = 2
shelf_A[0].position = [5.718601226806641, 0.75, 0.949999988079071]
shelf_A[0].rotation = [0, 0, -2.995859436361315]
shelf_A[0].optimize = 2
beverage_B[0].position = [5.929999828338623, 1.559999942779541, 2.115000009536743]
beverage_B[0].rotation = [0, 0, -3.1188010009295697]
beverage_B[0].optimize = 2
lightfixture_F[0].position = [5.89972448348999, 7.349999904632568, 0.20999999344348907]
lightfixture_F[0].rotation = [0, 0, -3.1390517311505883]
lightfixture_F[0].optimize = 2
glassbottle_C[0].position = [5.650000095367432, 1.7100000381469727, 2.134999990463257]
glassbottle_C[0].rotation = [0, 0, -3.1188010009295697]
glassbottle_C[0].optimize = 2
glassbottle_L[0].position = [3.2200000286102295, 5.159999847412109, 0.8700000047683716]
glassbottle_L[0].rotation = [0, 0, 0.02279165728452036]
glassbottle_L[0].optimize = 2
beverage_I[0].position = [3.7799999713897705, 5.309999942779541, 0.8650000095367432]
beverage_I[0].rotation = [0, 0, 0.02279165728452036]
beverage_I[0].optimize = 2
cannedgood_D[0].position = [5.914999961853027, 3.059999942779541, 1.9800000190734863]
cannedgood_D[0].rotation = [0, 0, -3.1188010009295697]
cannedgood_D[0].optimize = 2
beverage_J[0].position = [5.775000095367432, 4.110000133514404, 2.0299999713897705]
beverage_J[0].rotation = [0, 0, -3.1188010009295697]
beverage_J[0].optimize = 2
glassbottle_Y[0].position = [3.359999895095825, 5.460000038146973, 0.8700000047683716]
glassbottle_Y[0].rotation = [0, 0, 0.02279165728452036]
glassbottle_Y[0].optimize = 2
lightfixture_E[0].position = [2.3499999046325684, 6.650000095367432, 0.20000000298023224]
lightfixture_E[0].rotation = [0, 0, 0.00942477746072377]
lightfixture_E[0].optimize = 2
storesign_H[0].position = [0.011367769911885262, 1.149999976158142, 0.1899999976158142]
storesign_H[0].rotation = [0, 0, 0.0025409150842135757]
storesign_H[0].optimize = 2
lightfixture_G[0].position = [3.3499999046325684, 6.650000095367432, 0.20999999344348907]
lightfixture_G[0].rotation = [0, 0, 0.00942477746072377]
lightfixture_G[0].optimize = 2
cannedvegetable_E[0].position = [5.789999961853027, 2.609999895095825, 2.055000066757202]
cannedvegetable_E[0].rotation = [0, 0, -3.1188010009295697]
cannedvegetable_E[0].optimize = 2
storesign_C[0].position = [4.75, 7.988697052001953, 0.1599999964237213]
storesign_C[0].rotation = [0, 0, -1.5682554086442377]
storesign_C[0].optimize = 2
glassbottlefloor_A[0].position = [4.349999904632568, 4.550000190734863, 0.13500000536441803]
glassbottlefloor_A[0].rotation = [0, 0, -3.1321678761290697]
glassbottlefloor_A[0].optimize = 2
lightfixture_H[0].position = [4.349999904632568, 6.650000095367432, 0.20000000298023224]
lightfixture_H[0].rotation = [0, 0, 0.00942477746072377]
lightfixture_H[0].optimize = 2
cannedgood_W[0].position = [5.789999961853027, 2.309999942779541, 2.0899999141693115]
cannedgood_W[0].rotation = [0, 0, -3.1188010009295697]
cannedgood_W[0].optimize = 2
beverageitem_N[0].position = [5.800000190734863, 0.7099999785423279, 1.9900000095367432]
beverageitem_N[0].rotation = [0, 0, -3.1188010009295697]
beverageitem_N[0].optimize = 2
shoppingbag_counter[0].position = [0.375, 6.900000095367432, 1.159999966621399]
shoppingbag_counter[0].rotation = [0, 0, 0.02278960013808119]
shoppingbag_counter[0].optimize = 2
cannedveg_H[0].position = [5.871907711029053, 3.8031747341156006, 1.9800000190734863]
cannedveg_H[0].rotation = [0, 0, -3.1188010009295697]
cannedveg_H[0].optimize = 2
cannedgood_G[0].position = [5.800000190734863, 0.4099999964237213, 1.9850000143051147]
cannedgood_G[0].rotation = [0, 0, -3.1188010009295697]
cannedgood_G[0].optimize = 2
beverageitem_Z[0].position = [5.8541951179504395, 5.59848165512085, 2.0250000953674316]
beverageitem_Z[0].rotation = [0, 0, -3.118801008297538]
beverageitem_Z[0].optimize = 2
cannedgood_group_2_E[0].position = [5.848640441894531, 2.4471139907836914, 2.0899999141693115]
cannedgood_group_2_E[0].rotation = [0, 0, -3.1188010009295697]
cannedgood_group_2_E[0].optimize = 2
cannedgood_L[0].position = [5.635000228881836, 3.359999895095825, 1.9700000286102295]
cannedgood_L[0].rotation = [0, 0, -3.1188010009295697]
cannedgood_L[0].optimize = 2
glassbottle_T[0].position = [5.650000095367432, 5.610000133514404, 2.069999933242798]
glassbottle_T[0].rotation = [0, 0, -3.118801008297538]
glassbottle_T[0].optimize = 2
cannedgood_T[0].position = [5.894805908203125, 0.8528419733047485, 1.975000023841858]
cannedgood_T[0].rotation = [0, 0, -3.1188010009295697]
cannedgood_T[0].optimize = 2
cannedgood_J[0].position = [5.940000057220459, 0.4099999964237213, 1.9800000190734863]
cannedgood_J[0].rotation = [0, 0, -3.1188010009295697]
cannedgood_J[0].optimize = 2
cannedvegetable_A[0].position = [5.650000095367432, 4.860000133514404, 2.005000114440918]
cannedvegetable_A[0].rotation = [0, 0, -3.118801008297538]
cannedvegetable_A[0].optimize = 2
beverageitem_Q[0].position = [0.3499999940395355, 4.110000133514404, 1.340000033378601]
beverageitem_Q[0].rotation = [0, 0, 0.022791645292255164]
beverageitem_Q[0].optimize = 2
beverage_G[0].position = [5.894993305206299, 2.1544556617736816, 2.130000114440918]
beverage_G[0].rotation = [0, 0, -3.1188010009295697]
beverage_G[0].optimize = 2
cannedgood_U[0].position = [5.635000228881836, 3.809999942779541, 1.975000023841858]
cannedgood_U[0].rotation = [0, 0, -3.1188010009295697]
cannedgood_U[0].optimize = 2
cannedgood_P[0].position = [5.929999828338623, 1.8600000143051147, 2.0799999237060547]
cannedgood_P[0].rotation = [0, 0, -3.1188010009295697]
cannedgood_P[0].optimize = 2
cratefloor_D[0].position = [1.649999976158142, 1.4500000476837158, 0.15000000596046448]
cratefloor_D[0].rotation = [0, 0, 1.589645882193713]
cratefloor_D[0].optimize = 2
stool_A[0].position = [3.5, 4.25, 0.33500000834465027]
stool_A[0].rotation = [0, 0, 1.5833626980517244]
stool_A[0].optimize = 2
beverageitem_W[0].position = [5.87162971496582, 0.9991711378097534, 1.9900000095367432]
beverageitem_W[0].rotation = [0, 0, -3.1188010009295697]
beverageitem_W[0].optimize = 2
glassbottlefloor_C[0].position = [4.849999904632568, 4.550000190734863, 0.13500000536441803]
glassbottlefloor_C[0].rotation = [0, 0, -3.1321678761290697]
glassbottlefloor_C[0].optimize = 2
cannedgoodaa[0].position = [3.359999895095825, 5.159999847412109, 0.8299999833106995]
cannedgoodaa[0].rotation = [0, 0, 0.02279165728452036]
cannedgoodaa[0].optimize = 2
glassbottle9b9b_B[0].position = [5.650000095367432, 5.159999847412109, 2.0850000381469727]
glassbottle9b9b_B[0].rotation = [0, 0, -3.118801008297538]
glassbottle9b9b_B[0].optimize = 2
cannedgood_E[0].position = [5.929999828338623, 4.710000038146973, 2.0399999618530273]
cannedgood_E[0].rotation = [0, 0, -3.118801008297538]
cannedgood_E[0].optimize = 2
beverageitem_Y[0].position = [5.775000095367432, 3.9600000381469727, 2.0199999809265137]
beverageitem_Y[0].rotation = [0, 0, -3.1188010009295697]
beverageitem_Y[0].optimize = 2
storesign_E[0].position = [3.3499999046325684, 0.011367769911885262, 0.1899999976158142]
storesign_E[0].rotation = [0, 0, 1.5733372418791103]
storesign_E[0].optimize = 2
cannedgood_group_2_I[0].position = [5.800000190734863, 1.309999942779541, 1.975000023841858]
cannedgood_group_2_I[0].rotation = [0, 0, -3.1188010009295697]
cannedgood_group_2_I[0].optimize = 2
glassbottle_I[0].position = [0.6299999952316284, 3.9600000381469727, 1.3799999952316284]
glassbottle_I[0].rotation = [0, 0, 0.022791645292255164]
glassbottle_I[0].optimize = 2
glassbottle_P[0].position = [0.13211607933044434, 4.269438743591309, 1.375]
glassbottle_P[0].rotation = [0, 0, 0.022791645292255164]
glassbottle_P[0].optimize = 2
cannedgood_group_2_F[0].position = [5.659999847412109, 1.309999942779541, 1.9850000143051147]
cannedgood_group_2_F[0].rotation = [0, 0, -3.1188010009295697]
cannedgood_group_2_F[0].optimize = 2
pricetag_D[0].position = [5.789999961853027, 2.1600000858306885, 2.0350000858306885]
pricetag_D[0].rotation = [0, 0, -3.1188010009295697]
pricetag_D[0].optimize = 2
beverage_H[0].position = [0.6299999952316284, 4.260000228881836, 1.3799999952316284]
beverage_H[0].rotation = [0, 0, 0.022791645292255164]
beverage_H[0].optimize = 2
cannedveg_A[0].position = [5.635000228881836, 3.059999942779541, 1.9800000190734863]
cannedveg_A[0].rotation = [0, 0, -3.1188010009295697]
cannedveg_A[0].optimize = 2

