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
    Wall(corner1=[5.00, 0.00, 0.00], corner2=[5.00, 3.50, 0.00]),
    Wall(corner1=[5.00, 3.50, 0.00], corner2=[0.00, 3.50, 0.00]),
    Wall(corner1=[0.00, 3.50, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[5.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
plantcorner_A = Assets(description="A small potted plant in a woven planter, compact round pot, natural fiber texture, green foliage", size=[0.34, 0.34, 0.62], placements=[AssetInstance() for _ in range(1)])
plant_A = Assets(description="A small potted plant in a woven basket planter, compact foliage, earthy tones, basket has a textured natural weave", size=[0.32, 0.32, 0.58], placements=[AssetInstance() for _ in range(1)])
stool_A = Assets(description="A compact wooden stool with a square seat, Japandi style, warm wood tone, tapered legs, and a minimalist silhouette.", size=[0.38, 0.38, 0.46], placements=[AssetInstance() for _ in range(1)])
oliveoilbottle = Assets(description="A small olive oil bottle, cylindrical glass with a dark green label, narrow neck and a sleek cap", size=[0.07, 0.07, 0.25], placements=[AssetInstance() for _ in range(1)])
sideboard = Assets(description="A low wooden sideboard with a raw wood surface, rectangular shape, Japandi style, featuring a flat top, subtle grain texture, and minimalist hardware.", size=[0.45, 1.60, 0.75], placements=[AssetInstance() for _ in range(1)])
chair_A = Assets(description="A simple wooden dining chair with a rectangular seat, warm wood tones, Japandi style, straight-edged backrest, slightly angled legs, and a smooth matte finish.", size=[0.52, 0.47, 0.82], placements=[AssetInstance() for _ in range(1)])
cutlery_A = Assets(description="A set of three elongated utensils – fork, knife and spoon – with polished stainless‑steel finish and gently curved handles", size=[0.22, 0.10, 0.03], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="A simple wooden dining chair with a rectangular seat, warm wood tones, Japandi style, straight-edged backrest, slightly angled legs, and a smooth matte finish.", size=[0.52, 0.47, 0.82], placements=[AssetInstance() for _ in range(1)])
plant_B = Assets(description="A small potted plant in a woven basket, compact foliage, earthy tones, rounded pot shape", size=[0.30, 0.30, 0.55], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="A simple wooden dining chair, rectangular seat, straight‑edged backrest, natural wood finish, modest height", size=[0.51, 0.46, 0.80], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="A tall floor lamp with a slender wooden stand and a linen shade, neutral tones, Japandi style, the shade is cylindrical and slightly draped, providing a soft diffused glow.", size=[0.42, 0.42, 1.58], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="A solid wood dining table with a rectangular top, natural finish, muted earth tones, Japandi style, featuring subtle tapered legs and a smooth grain pattern.", size=[0.90, 1.80, 0.75], placements=[AssetInstance() for _ in range(1)])
plant_C = Assets(description="A small potted plant in a woven natural‑fiber planter, compact bushy foliage, planter is rectangular with a textured weave", size=[0.30, 0.38, 0.58], placements=[AssetInstance() for _ in range(1)])
candle_A = Assets(description="A small cylindrical candle set in a wooden holder, warm brown wood, smooth wax, slender profile", size=[0.08, 0.08, 0.22], placements=[AssetInstance() for _ in range(1)])
plant_D = Assets(description="A small potted plant in a woven basket planter, compact foliage, earthy tones, basket has a textured natural weave", size=[0.32, 0.32, 0.58], placements=[AssetInstance() for _ in range(1)])
plate_A = Assets(description="A white ceramic plate, circular shape, smooth glossy surface, slightly raised rim for a clean edge", size=[0.27, 0.27, 0.03], placements=[AssetInstance() for _ in range(1)])
candle_B = Assets(description="A small cylindrical white wax candle with a smooth surface and rounded top", size=[0.07, 0.07, 0.18], placements=[AssetInstance() for _ in range(1)])
plantcorner_B = Assets(description="A small potted plant in a woven planter, compact round pot, natural fiber texture, green foliage", size=[0.34, 0.34, 0.62], placements=[AssetInstance() for _ in range(1)])
saltshaker_A = Assets(description="A small ceramic salt shaker, rectangular body with a slightly tapered top, matte white finish and a tiny perforated lid", size=[0.05, 0.05, 0.10], placements=[AssetInstance() for _ in range(1)])
candle_C = Assets(description="A small cylindrical candle set in a wooden holder, warm brown wood, smooth wax, slender profile", size=[0.08, 0.08, 0.22], placements=[AssetInstance() for _ in range(1)])
candle_D = Assets(description="A small pillar candle in a wooden holder, cylindrical candle with a smooth white wax surface, holder made of light oak with a shallow recessed base", size=[0.10, 0.10, 0.18], placements=[AssetInstance() for _ in range(1)])
book_A = Assets(description="A thin hardcover book with a linen cover, rectangular shape, soft off‑white linen texture, and crisp edges", size=[0.22, 0.30, 0.03], placements=[AssetInstance() for _ in range(1)])
remote = Assets(description="A rectangular remote control, matte black plastic, rounded corners, ergonomic grip", size=[0.18, 0.05, 0.02], placements=[AssetInstance() for _ in range(1)])
plant_E = Assets(description="A small potted plant in a woven natural‑fiber planter, compact bushy foliage, planter is rectangular with a textured weave", size=[0.30, 0.38, 0.58], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="A tall floor lamp with a beige fabric shade, slender pole, soft rectangular shade, contemporary style", size=[0.32, 0.38, 1.55], placements=[AssetInstance() for _ in range(1)])
cutlery_B = Assets(description="A set of three elongated utensils – fork, knife and spoon – with polished stainless‑steel finish and gently curved handles", size=[0.22, 0.10, 0.03], placements=[AssetInstance() for _ in range(1)])
glass_A = Assets(description="A clear stemless glass, cylindrical body with a smooth, slightly tapered profile and a thin, polished rim", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
candle_E = Assets(description="A small wooden candle holder, cylindrical shape with a smooth polished finish, natural wood color and a tiny recessed cavity for a candle", size=[0.07, 0.07, 0.10], placements=[AssetInstance() for _ in range(1)])
chair_D = Assets(description="A simple wooden dining chair with a rectangular seat, warm wood tones, Japandi style, straight-edged backrest, slightly angled legs, and a smooth matte finish.", size=[0.52, 0.47, 0.82], placements=[AssetInstance() for _ in range(1)])
bench = Assets(description="A wooden bench with a light wood finish, rectangular seat, Japandi style, low-slung profile, slightly rounded edges, and a smooth surface.", size=[0.38, 1.20, 0.45], placements=[AssetInstance() for _ in range(1)])
glass_B = Assets(description="A clear stemless glass, cylindrical body with a smooth, slightly tapered profile and a thin, polished rim", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
stool_B = Assets(description="A compact wooden stool with a square seat, Japandi style, warm wood tone, tapered legs, and a minimalist silhouette.", size=[0.38, 0.38, 0.46], placements=[AssetInstance() for _ in range(1)])
lamp_C = Assets(description="A tall floor lamp with a slender pole and a beige fabric shade, modern minimalist style", size=[0.40, 0.40, 1.60], placements=[AssetInstance() for _ in range(1)])
peppershaker_A = Assets(description="A small cylindrical pepper shaker, brushed stainless steel, matching the salt shaker with a subtle textured knob", size=[0.05, 0.05, 0.11], placements=[AssetInstance() for _ in range(1)])
lamp_D = Assets(description="A tall floor lamp with a slender metal shaft and a soft beige fabric shade, sleek modern silhouette", size=[0.40, 0.40, 1.62], placements=[AssetInstance() for _ in range(1)])
plate_B = Assets(description="A white ceramic plate, circular shape, smooth glossy surface, slightly raised rim for a clean edge", size=[0.27, 0.27, 0.03], placements=[AssetInstance() for _ in range(1)])
book_B = Assets(description="A thin hardcover book with a linen cover, rectangular shape, soft off‑white fabric texture and slightly rounded edges", size=[0.21, 0.29, 0.03], placements=[AssetInstance() for _ in range(1)])
plant_F = Assets(description="A potted bamboo plant in a woven natural planter, cylindrical foliage, Japandi style, the planter has a textured rattan weave and a round base.", size=[0.42, 0.42, 1.25], placements=[AssetInstance() for _ in range(1)])
plant_G = Assets(description="A potted bamboo plant in a woven natural planter, cylindrical foliage, Japandi style, the planter has a textured rattan weave and a round base.", size=[0.42, 0.42, 1.25], placements=[AssetInstance() for _ in range(1)])
book_C = Assets(description="A thin hardcover book with a linen cover, rectangular shape, soft off‑white linen texture, and crisp edges", size=[0.22, 0.30, 0.03], placements=[AssetInstance() for _ in range(1)])
lamp_E = Assets(description="A tall floor lamp with a slender metal shaft, topped by a wide beige fabric shade, sleek and minimalist silhouette", size=[0.48, 0.48, 1.65], placements=[AssetInstance() for _ in range(1)])
sidetable = Assets(description="A small wooden side table, rectangular top with a light natural finish, short sturdy legs, compact footprint", size=[0.40, 0.55, 0.48], placements=[AssetInstance() for _ in range(1)])
saltshaker_B = Assets(description="A small cylindrical salt shaker, brushed stainless steel, sleek and reflective surface", size=[0.05, 0.05, 0.10], placements=[AssetInstance() for _ in range(1)])
cutlery_C = Assets(description="A set of three elongated utensils – fork, knife and spoon – with polished stainless‑steel finish and gently curved handles", size=[0.22, 0.10, 0.03], placements=[AssetInstance() for _ in range(1)])
peppershaker_B = Assets(description="A small ceramic pepper shaker, rectangular body matching the salt shaker but with a contrasting speckled gray finish and a tiny perforated lid", size=[0.05, 0.05, 0.10], placements=[AssetInstance() for _ in range(1)])
cutlery_D = Assets(description="A set of three elongated utensils – fork, knife and spoon – with polished stainless‑steel finish and gently curved handles", size=[0.22, 0.10, 0.03], placements=[AssetInstance() for _ in range(1)])
chair_E = Assets(description="A simple wooden dining chair with a rectangular seat, warm wood tones, Japandi style, straight-edged backrest, slightly angled legs, and a smooth matte finish.", size=[0.52, 0.47, 0.82], placements=[AssetInstance() for _ in range(1)])
chair_F = Assets(description="A simple wooden dining chair with a rectangular seat, warm wood tones, Japandi style, straight-edged backrest, slightly angled legs, and a smooth matte finish.", size=[0.52, 0.47, 0.82], placements=[AssetInstance() for _ in range(1)])
glass_C = Assets(description="A clear stemless glass, cylindrical body with a smooth, slightly tapered profile and a thin, polished rim", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
glass_D = Assets(description="A clear stemless glass, cylindrical body with a smooth, slightly tapered profile and a thin, polished rim", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
vase = Assets(description="A wooden Japandi style vase with a natural wood texture, cylindrical shape, smooth matte finish, and a subtle tapered rim", size=[0.16, 0.16, 0.32], placements=[AssetInstance() for _ in range(1)])
chair_G = Assets(description="A simple wooden dining chair, rectangular seat, straight‑edged backrest, natural wood finish, modest height", size=[0.51, 0.46, 0.80], placements=[AssetInstance() for _ in range(1)])
book_D = Assets(description="A thin hardcover book with linen cover, rectangular shape, muted earth tone, smooth texture", size=[0.20, 0.28, 0.03], placements=[AssetInstance() for _ in range(1)])

plantcorner_A[0].instance_id = 'plantcorner_A_0'
plant_A[0].instance_id = 'plant_A_0'
stool_A[0].instance_id = 'stool_A_0'
oliveoilbottle[0].instance_id = 'oliveoilbottle_0'
sideboard[0].instance_id = 'sideboard_0'
chair_A[0].instance_id = 'chair_A_0'
cutlery_A[0].instance_id = 'cutlery_A_0'
chair_B[0].instance_id = 'chair_B_0'
plant_B[0].instance_id = 'plant_B_0'
chair_C[0].instance_id = 'chair_C_0'
lamp_A[0].instance_id = 'lamp_A_0'
table[0].instance_id = 'table_0'
plant_C[0].instance_id = 'plant_C_0'
candle_A[0].instance_id = 'candle_A_0'
plant_D[0].instance_id = 'plant_D_0'
plate_A[0].instance_id = 'plate_A_0'
candle_B[0].instance_id = 'candle_B_0'
plantcorner_B[0].instance_id = 'plantcorner_B_0'
saltshaker_A[0].instance_id = 'saltshaker_A_0'
candle_C[0].instance_id = 'candle_C_0'
candle_D[0].instance_id = 'candle_D_0'
book_A[0].instance_id = 'book_A_0'
remote[0].instance_id = 'remote_0'
plant_E[0].instance_id = 'plant_E_0'
lamp_B[0].instance_id = 'lamp_B_0'
cutlery_B[0].instance_id = 'cutlery_B_0'
glass_A[0].instance_id = 'glass_A_0'
candle_E[0].instance_id = 'candle_E_0'
chair_D[0].instance_id = 'chair_D_0'
bench[0].instance_id = 'bench_0'
glass_B[0].instance_id = 'glass_B_0'
stool_B[0].instance_id = 'stool_B_0'
lamp_C[0].instance_id = 'lamp_C_0'
peppershaker_A[0].instance_id = 'peppershaker_A_0'
lamp_D[0].instance_id = 'lamp_D_0'
plate_B[0].instance_id = 'plate_B_0'
book_B[0].instance_id = 'book_B_0'
plant_F[0].instance_id = 'plant_F_0'
plant_G[0].instance_id = 'plant_G_0'
book_C[0].instance_id = 'book_C_0'
lamp_E[0].instance_id = 'lamp_E_0'
sidetable[0].instance_id = 'sidetable_0'
saltshaker_B[0].instance_id = 'saltshaker_B_0'
cutlery_C[0].instance_id = 'cutlery_C_0'
peppershaker_B[0].instance_id = 'peppershaker_B_0'
cutlery_D[0].instance_id = 'cutlery_D_0'
chair_E[0].instance_id = 'chair_E_0'
chair_F[0].instance_id = 'chair_F_0'
glass_C[0].instance_id = 'glass_C_0'
glass_D[0].instance_id = 'glass_D_0'
vase[0].instance_id = 'vase_0'
chair_G[0].instance_id = 'chair_G_0'
book_D[0].instance_id = 'book_D_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

plantcorner_A[0].position = [4.262702011998332, 0.6305150410923959, 0.31]
plantcorner_A[0].rotation = [0, 0, 0]
plant_A[0].position = [4.886358830186266, 2.029148831107949, 0.29]
plant_A[0].rotation = [0, 0, 0]
stool_A[0].position = [3.1542311184736693, 2.5538873373189106, 0.23]
stool_A[0].rotation = [0, 0, 0]
oliveoilbottle[0].position = [3.330243879961929, 2.0150218452553794, 0.125]
oliveoilbottle[0].rotation = [0, 0, 0]
sideboard[0].position = [4.97361883510602, 2.9365957417108275, 0.375]
sideboard[0].rotation = [0, 0, 0]
chair_A[0].position = [4.958803671240541, 2.197123803576761, 0.41]
chair_A[0].rotation = [0, 0, 0]
cutlery_A[0].position = [3.2923047093670204, 2.8955979087654766, 0.0125]
cutlery_A[0].rotation = [0, 0, 0]
chair_B[0].position = [1.9603352128499445, 0.7126557598266874, 0.41]
chair_B[0].rotation = [0, 0, 0]
plant_B[0].position = [1.611092621356856, 1.2066620617188357, 0.275]
plant_B[0].rotation = [0, 0, 0]
chair_C[0].position = [3.025570335838851, 1.1870326526646446, 0.4]
chair_C[0].rotation = [0, 0, 0]
lamp_A[0].position = [3.8447575588440692, 1.5345353768727008, 0.79]
lamp_A[0].rotation = [0, 0, 0]
table[0].position = [4.217920980730665, 2.8290969098230114, 0.375]
table[0].rotation = [0, 0, 0]
plant_C[0].position = [4.1275273503137955, 1.2987207160054637, 0.29]
plant_C[0].rotation = [0, 0, 0]
candle_A[0].position = [3.031409613121117, 0.8650444001782382, 0.11]
candle_A[0].rotation = [0, 0, 0]
plant_D[0].position = [2.449993865440309, 1.8467823854345058, 0.29]
plant_D[0].rotation = [0, 0, 0]
plate_A[0].position = [2.843011289995464, 3.3775470083089845, 0.0125]
plate_A[0].rotation = [0, 0, 0]
candle_B[0].position = [4.331120884255576, 0.028263251171350867, 0.09]
candle_B[0].rotation = [0, 0, 0]
plantcorner_B[0].position = [0.7049578637267956, 1.7691198419037597, 0.31]
plantcorner_B[0].rotation = [0, 0, 0]
saltshaker_A[0].position = [4.194596237001507, 0.9242539889782091, 0.05]
saltshaker_A[0].rotation = [0, 0, 0]
candle_C[0].position = [1.1680593431847186, 1.6184386169870923, 0.11]
candle_C[0].rotation = [0, 0, 0]
candle_D[0].position = [2.5856332865064715, 0.15572356277031157, 0.09]
candle_D[0].rotation = [0, 0, 0]
book_A[0].position = [3.521804985994323, 1.7936043522613425, 0.015]
book_A[0].rotation = [0, 0, 0]
remote[0].position = [1.063662406820578, 1.1565373401569277, 0.01]
remote[0].rotation = [0, 0, 0]
plant_E[0].position = [2.7496875230531037, 1.7008020915393909, 0.29]
plant_E[0].rotation = [0, 0, 0]
lamp_B[0].position = [1.389774163630257, 1.9514625366133875, 0.775]
lamp_B[0].rotation = [0, 0, 0]
cutlery_B[0].position = [3.032214344061725, 1.3650893517279352, 0.0125]
cutlery_B[0].rotation = [0, 0, 0]
glass_A[0].position = [4.5270209568946855, 3.3025327206560737, 0.055]
glass_A[0].rotation = [0, 0, 0]
candle_E[0].position = [2.46063857586567, 1.4245715353017763, 0.05]
candle_E[0].rotation = [0, 0, 0]
chair_D[0].position = [2.526132598497366, 2.0000327689657422, 0.41]
chair_D[0].rotation = [0, 0, 0]
bench[0].position = [3.3447810549385397, 0.38747786478700014, 0.225]
bench[0].rotation = [0, 0, 0]
glass_B[0].position = [0.3966429802053806, 0.16052419370963034, 0.055]
glass_B[0].rotation = [0, 0, 0]
stool_B[0].position = [2.7076491216452685, 0.18905657362279904, 0.23]
stool_B[0].rotation = [0, 0, 0]
lamp_C[0].position = [1.4883976206285832, 1.6524007373051899, 0.8]
lamp_C[0].rotation = [0, 0, 0]
peppershaker_A[0].position = [3.2140482653109226, 2.101530230077482, 0.055]
peppershaker_A[0].rotation = [0, 0, 0]
lamp_D[0].position = [4.698878411357992, 2.0643490863036287, 0.81]
lamp_D[0].rotation = [0, 0, 0]
plate_B[0].position = [1.992720751515581, 3.21114961937282, 0.0125]
plate_B[0].rotation = [0, 0, 0]
book_B[0].position = [3.871595330861661, 2.5800062269042265, 0.015]
book_B[0].rotation = [0, 0, 0]
plant_F[0].position = [1.3867292100950912, 1.5928958772282857, 0.625]
plant_F[0].rotation = [0, 0, 0]
plant_G[0].position = [3.3197544954576923, 2.4743807435630276, 0.625]
plant_G[0].rotation = [0, 0, 0]
book_C[0].position = [2.5624767451053367, 3.4882957378098256, 0.015]
book_C[0].rotation = [0, 0, 0]
lamp_E[0].position = [3.1129186734324144, 2.947425393143861, 0.825]
lamp_E[0].rotation = [0, 0, 0]
sidetable[0].position = [4.2596225644347205, 2.4369199380524376, 0.24]
sidetable[0].rotation = [0, 0, 0]
saltshaker_B[0].position = [0.9764710800565124, 0.2362379439026559, 0.05]
saltshaker_B[0].rotation = [0, 0, 0]
cutlery_C[0].position = [1.8015627869011204, 2.213606582617226, 0.0125]
cutlery_C[0].rotation = [0, 0, 0]
peppershaker_B[0].position = [1.7770257381137973, 0.9036800854579833, 0.05]
peppershaker_B[0].rotation = [0, 0, 0]
cutlery_D[0].position = [0.4585612715602383, 3.2335059410427305, 0.0125]
cutlery_D[0].rotation = [0, 0, 0]
chair_E[0].position = [0.9736566243313366, 2.312357506270448, 0.41]
chair_E[0].rotation = [0, 0, 0]
chair_F[0].position = [0.025953502342939694, 0.8835347150812469, 0.41]
chair_F[0].rotation = [0, 0, 0]
glass_C[0].position = [3.7987523573632833, 2.0633902179034704, 0.055]
glass_C[0].rotation = [0, 0, 0]
glass_D[0].position = [4.920236770516398, 2.4953812458009583, 0.055]
glass_D[0].rotation = [0, 0, 0]
vase[0].position = [0.8249883814291714, 0.0681931732438627, 0.16]
vase[0].rotation = [0, 0, 0]
chair_G[0].position = [2.755999404895749, 2.815182494430995, 0.4]
chair_G[0].rotation = [0, 0, 0]
book_D[0].position = [2.7319215821150133, 2.494668519792458, 0.015]
book_D[0].rotation = [0, 0, 0]
plantcorner_A[0].position = [4.262702011998332, 0.6305150410923959, 0.31]
plantcorner_A[0].rotation = [0, 0, 0]
plant_A[0].position = [4.886358830186266, 2.029148831107949, 0.29]
plant_A[0].rotation = [0, 0, 0]
stool_A[0].position = [3.1542311184736693, 2.5538873373189106, 0.23]
stool_A[0].rotation = [0, 0, 0]
oliveoilbottle[0].position = [3.330243879961929, 2.0150218452553794, 0.125]
oliveoilbottle[0].rotation = [0, 0, 0]
sideboard[0].position = [4.97361883510602, 2.9365957417108275, 0.375]
sideboard[0].rotation = [0, 0, 0]
chair_A[0].position = [4.958803671240541, 2.197123803576761, 0.41]
chair_A[0].rotation = [0, 0, 0]
cutlery_A[0].position = [3.2923047093670204, 2.8955979087654766, 0.0125]
cutlery_A[0].rotation = [0, 0, 0]
chair_B[0].position = [1.9603352128499445, 0.7126557598266874, 0.41]
chair_B[0].rotation = [0, 0, 0]
plant_B[0].position = [1.611092621356856, 1.2066620617188357, 0.275]
plant_B[0].rotation = [0, 0, 0]
chair_C[0].position = [3.025570335838851, 1.1870326526646446, 0.4]
chair_C[0].rotation = [0, 0, 0]
lamp_A[0].position = [3.8447575588440692, 1.5345353768727008, 0.79]
lamp_A[0].rotation = [0, 0, 0]
table[0].position = [4.217920980730665, 2.8290969098230114, 0.375]
table[0].rotation = [0, 0, 0]
plant_C[0].position = [4.1275273503137955, 1.2987207160054637, 0.29]
plant_C[0].rotation = [0, 0, 0]
candle_A[0].position = [3.031409613121117, 0.8650444001782382, 0.11]
candle_A[0].rotation = [0, 0, 0]
plant_D[0].position = [2.449993865440309, 1.8467823854345058, 0.29]
plant_D[0].rotation = [0, 0, 0]
plate_A[0].position = [2.843011289995464, 3.3775470083089845, 0.0125]
plate_A[0].rotation = [0, 0, 0]
candle_B[0].position = [4.331120884255576, 0.028263251171350867, 0.09]
candle_B[0].rotation = [0, 0, 0]
plantcorner_B[0].position = [0.7049578637267956, 1.7691198419037597, 0.31]
plantcorner_B[0].rotation = [0, 0, 0]
saltshaker_A[0].position = [4.194596237001507, 0.9242539889782091, 0.05]
saltshaker_A[0].rotation = [0, 0, 0]
candle_C[0].position = [1.1680593431847186, 1.6184386169870923, 0.11]
candle_C[0].rotation = [0, 0, 0]
candle_D[0].position = [2.5856332865064715, 0.15572356277031157, 0.09]
candle_D[0].rotation = [0, 0, 0]
book_A[0].position = [3.521804985994323, 1.7936043522613425, 0.015]
book_A[0].rotation = [0, 0, 0]
remote[0].position = [1.063662406820578, 1.1565373401569277, 0.01]
remote[0].rotation = [0, 0, 0]
plant_E[0].position = [2.7496875230531037, 1.7008020915393909, 0.29]
plant_E[0].rotation = [0, 0, 0]
lamp_B[0].position = [1.389774163630257, 1.9514625366133875, 0.775]
lamp_B[0].rotation = [0, 0, 0]
cutlery_B[0].position = [3.032214344061725, 1.3650893517279352, 0.0125]
cutlery_B[0].rotation = [0, 0, 0]
glass_A[0].position = [4.5270209568946855, 3.3025327206560737, 0.055]
glass_A[0].rotation = [0, 0, 0]
candle_E[0].position = [2.46063857586567, 1.4245715353017763, 0.05]
candle_E[0].rotation = [0, 0, 0]
chair_D[0].position = [2.526132598497366, 2.0000327689657422, 0.41]
chair_D[0].rotation = [0, 0, 0]
bench[0].position = [3.3447810549385397, 0.38747786478700014, 0.225]
bench[0].rotation = [0, 0, 0]
glass_B[0].position = [0.3966429802053806, 0.16052419370963034, 0.055]
glass_B[0].rotation = [0, 0, 0]
stool_B[0].position = [2.7076491216452685, 0.18905657362279904, 0.23]
stool_B[0].rotation = [0, 0, 0]
lamp_C[0].position = [1.4883976206285832, 1.6524007373051899, 0.8]
lamp_C[0].rotation = [0, 0, 0]
peppershaker_A[0].position = [3.2140482653109226, 2.101530230077482, 0.055]
peppershaker_A[0].rotation = [0, 0, 0]
lamp_D[0].position = [4.698878411357992, 2.0643490863036287, 0.81]
lamp_D[0].rotation = [0, 0, 0]
plate_B[0].position = [1.992720751515581, 3.21114961937282, 0.0125]
plate_B[0].rotation = [0, 0, 0]
book_B[0].position = [3.871595330861661, 2.5800062269042265, 0.015]
book_B[0].rotation = [0, 0, 0]
plant_F[0].position = [1.3867292100950912, 1.5928958772282857, 0.625]
plant_F[0].rotation = [0, 0, 0]
plant_G[0].position = [3.3197544954576923, 2.4743807435630276, 0.625]
plant_G[0].rotation = [0, 0, 0]
book_C[0].position = [2.5624767451053367, 3.4882957378098256, 0.015]
book_C[0].rotation = [0, 0, 0]
lamp_E[0].position = [3.1129186734324144, 2.947425393143861, 0.825]
lamp_E[0].rotation = [0, 0, 0]
sidetable[0].position = [4.2596225644347205, 2.4369199380524376, 0.24]
sidetable[0].rotation = [0, 0, 0]
saltshaker_B[0].position = [0.9764710800565124, 0.2362379439026559, 0.05]
saltshaker_B[0].rotation = [0, 0, 0]
cutlery_C[0].position = [1.8015627869011204, 2.213606582617226, 0.0125]
cutlery_C[0].rotation = [0, 0, 0]
peppershaker_B[0].position = [1.7770257381137973, 0.9036800854579833, 0.05]
peppershaker_B[0].rotation = [0, 0, 0]
cutlery_D[0].position = [0.4585612715602383, 3.2335059410427305, 0.0125]
cutlery_D[0].rotation = [0, 0, 0]
chair_E[0].position = [0.9736566243313366, 2.312357506270448, 0.41]
chair_E[0].rotation = [0, 0, 0]
chair_F[0].position = [0.025953502342939694, 0.8835347150812469, 0.41]
chair_F[0].rotation = [0, 0, 0]
glass_C[0].position = [3.7987523573632833, 2.0633902179034704, 0.055]
glass_C[0].rotation = [0, 0, 0]
glass_D[0].position = [4.920236770516398, 2.4953812458009583, 0.055]
glass_D[0].rotation = [0, 0, 0]
vase[0].position = [0.8249883814291714, 0.0681931732438627, 0.16]
vase[0].rotation = [0, 0, 0]
chair_G[0].position = [2.755999404895749, 2.815182494430995, 0.4]
chair_G[0].rotation = [0, 0, 0]
book_D[0].position = [2.7319215821150133, 2.494668519792458, 0.015]
book_D[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed zero-rotation reference used to preserve the intended orientation of
# every asset. Exact position constraints also keep the densely furnished room
# organized while the solver handles physical feasibility.
orientation_reference = AssetInstance(
    position=[2.50, 1.75, 0.00],
    rotation=[0, 0, 0],
)


def place_asset(instance, position, yaw_degrees):
    """Assign an initial pose and constrain both position and orientation."""
    instance.position = position
    instance.rotation = [0, 0, radians(yaw_degrees)]
    solver.distance_constraint(
        instance,
        AssetInstance(position=position),
        0,
        0,
        weight=10,
    )
    solver.align_with(instance, orientation_reference, angle=yaw_degrees)


# The dining table is centered in the room with its long dimension running
# east-west. Its east edge stops well before the door approach.
place_asset(table[0], [2.55, 2.00, 0.375], 90)

# Three chairs are arranged along each long side of the table. The seventh
# chair occupies the west end. All chairs face the dining surface.
place_asset(chair_A[0], [1.85, 1.18, 0.41], 90)
place_asset(chair_B[0], [2.55, 1.18, 0.41], 90)
place_asset(chair_C[0], [3.25, 1.18, 0.40], 90)

place_asset(chair_D[0], [1.85, 2.85, 0.41], -90)
place_asset(chair_E[0], [2.55, 2.85, 0.41], -90)
place_asset(chair_F[0], [3.25, 2.85, 0.41], -90)

place_asset(chair_G[0], [1.30, 2.00, 0.40], 0)

# Chair-facing constraints express the functional relationship to the table.
# They agree with the explicitly assigned orientations above.
solver.point_towards(chair_A[0], table[0])
solver.point_towards(chair_B[0], table[0])
solver.point_towards(chair_C[0], table[0])
solver.point_towards(chair_D[0], table[0])
solver.point_towards(chair_E[0], table[0])
solver.point_towards(chair_F[0], table[0])
solver.point_towards(chair_G[0], table[0])

# The sideboard occupies the upper portion of the west wall. This leaves the
# southwest corner open and provides a display surface for the required candle.
place_asset(sideboard[0], [0.225, 2.50, 0.375], 0)
solver.against_wall(sideboard[0], walls[2])

# A bench sits on the east wall north of the door. Its southern edge is above
# the doorway's 2.055 m endpoint, preserving the full entrance approach.
place_asset(bench[0], [4.81, 2.75, 0.225], 180)
solver.against_wall(bench[0], walls[0])

# Two stools form a compact plant display in the southwest part of the room.
place_asset(stool_A[0], [0.30, 0.35, 0.23], 0)
place_asset(stool_B[0], [0.85, 0.35, 0.23], 0)

place_asset(plant_A[0], [0.30, 0.35, 0.75], 0)
solver.on_top_of(plant_A[0], stool_A[0])

place_asset(plant_B[0], [0.85, 0.35, 0.735], 0)
solver.on_top_of(plant_B[0], stool_B[0])

# The side table and its plant are kept in the southeast corner, below the
# doorway rather than in its circulation zone.
place_asset(sidetable[0], [4.72, 0.35, 0.24], 90)
solver.against_wall(sidetable[0], walls[0])

place_asset(plant_C[0], [4.72, 0.35, 0.77], 90)
solver.on_top_of(plant_C[0], sidetable[0])

# Remaining plants decorate corners and unused perimeter areas. None enter the
# clear east-wall door zone between approximately y=1.10 and y=2.06.
place_asset(plantcorner_A[0], [0.25, 0.90, 0.31], 0)
solver.against_wall(plantcorner_A[0], walls[2])

place_asset(plantcorner_B[0], [0.75, 3.30, 0.31], -90)
solver.against_wall(plantcorner_B[0], walls[1])

place_asset(plant_D[0], [1.30, 0.25, 0.29], 90)
solver.against_wall(plant_D[0], walls[3])

place_asset(plant_E[0], [4.02, 0.25, 0.29], 90)
solver.against_wall(plant_E[0], walls[3])

place_asset(plant_F[0], [4.30, 0.25, 0.625], 90)
solver.against_wall(plant_F[0], walls[3])

place_asset(plant_G[0], [4.30, 3.25, 0.625], -90)
solver.against_wall(plant_G[0], walls[1])

# Floor lamps are distributed along the otherwise unused south-wall strip.
# Their shades remain clear of the dining chairs and the entrance route.
place_asset(lamp_A[0], [1.70, 0.21, 0.79], 90)
solver.against_wall(lamp_A[0], walls[3])

place_asset(lamp_B[0], [2.13, 0.19, 0.775], 90)
solver.against_wall(lamp_B[0], walls[3])

place_asset(lamp_C[0], [2.53, 0.20, 0.80], 90)
solver.against_wall(lamp_C[0], walls[3])

place_asset(lamp_D[0], [2.94, 0.20, 0.81], 90)
solver.against_wall(lamp_D[0], walls[3])

place_asset(lamp_E[0], [3.40, 0.24, 0.825], 90)
solver.against_wall(lamp_E[0], walls[3])

# Two coordinated place settings occupy the south half of the tabletop.
tabletop_z = 0.75

place_asset(plate_A[0], [2.00, 1.80, tabletop_z + 0.015], 0)
solver.on_top_of(plate_A[0], table[0])

place_asset(plate_B[0], [3.10, 1.80, tabletop_z + 0.015], 0)
solver.on_top_of(plate_B[0], table[0])

place_asset(cutlery_A[0], [1.77, 1.80, tabletop_z + 0.015], 90)
solver.on_top_of(cutlery_A[0], table[0])

place_asset(cutlery_B[0], [2.25, 1.80, tabletop_z + 0.015], 90)
solver.on_top_of(cutlery_B[0], table[0])

place_asset(cutlery_C[0], [2.85, 1.80, tabletop_z + 0.015], 90)
solver.on_top_of(cutlery_C[0], table[0])

place_asset(cutlery_D[0], [3.34, 1.80, tabletop_z + 0.015], 90)
solver.on_top_of(cutlery_D[0], table[0])

# Glasses are paired behind the place settings, with a second pair available
# along the north side of the tabletop.
place_asset(glass_A[0], [2.00, 2.05, tabletop_z + 0.055], 0)
solver.on_top_of(glass_A[0], table[0])

place_asset(glass_B[0], [3.10, 2.05, tabletop_z + 0.055], 0)
solver.on_top_of(glass_B[0], table[0])

place_asset(glass_C[0], [2.00, 2.30, tabletop_z + 0.055], 0)
solver.on_top_of(glass_C[0], table[0])

place_asset(glass_D[0], [3.10, 2.30, tabletop_z + 0.055], 0)
solver.on_top_of(glass_D[0], table[0])

# Condiments and small candles form a spaced centerpiece down the middle of
# the table. Their centers are separated sufficiently to avoid overlap.
place_asset(saltshaker_A[0], [2.38, 1.88, tabletop_z + 0.05], 0)
solver.on_top_of(saltshaker_A[0], table[0])

place_asset(peppershaker_A[0], [2.53, 1.88, tabletop_z + 0.055], 0)
solver.on_top_of(peppershaker_A[0], table[0])

place_asset(saltshaker_B[0], [2.68, 1.88, tabletop_z + 0.05], 0)
solver.on_top_of(saltshaker_B[0], table[0])

place_asset(peppershaker_B[0], [2.83, 1.88, tabletop_z + 0.05], 0)
solver.on_top_of(peppershaker_B[0], table[0])

place_asset(candle_B[0], [2.35, 2.12, tabletop_z + 0.09], 0)
solver.on_top_of(candle_B[0], table[0])

place_asset(candle_C[0], [2.55, 2.12, tabletop_z + 0.11], 0)
solver.on_top_of(candle_C[0], table[0])

place_asset(candle_D[0], [2.75, 2.12, tabletop_z + 0.09], 0)
solver.on_top_of(candle_D[0], table[0])

place_asset(candle_E[0], [2.45, 2.33, tabletop_z + 0.05], 0)
solver.on_top_of(candle_E[0], table[0])

place_asset(oliveoilbottle[0], [2.68, 2.33, tabletop_z + 0.125], 0)
solver.on_top_of(oliveoilbottle[0], table[0])

# The required candle (o0013 / candle_A) is placed prominently on the
# sideboard. The remaining accessories are distributed along the same surface.
sideboard_top_z = 0.75

place_asset(candle_A[0], [0.225, 1.88, sideboard_top_z + 0.11], 0)
solver.on_top_of(candle_A[0], sideboard[0])

place_asset(vase[0], [0.225, 2.83, sideboard_top_z + 0.16], 0)
solver.on_top_of(vase[0], sideboard[0])

place_asset(remote[0], [0.225, 3.12, sideboard_top_z + 0.01], 90)
solver.on_top_of(remote[0], sideboard[0])

# The four books form one intentional vertical stack on the sideboard.
place_asset(book_A[0], [0.225, 2.30, sideboard_top_z + 0.015], 0)
solver.on_top_of(book_A[0], sideboard[0])

place_asset(book_B[0], [0.225, 2.30, sideboard_top_z + 0.045], 0)
solver.on_top_of(book_B[0], book_A[0])

place_asset(book_C[0], [0.225, 2.30, sideboard_top_z + 0.075], 0)
solver.on_top_of(book_C[0], book_B[0])

place_asset(book_D[0], [0.225, 2.30, sideboard_top_z + 0.105], 0)
solver.on_top_of(book_D[0], book_C[0])

solver.constraints = []
book_A[0].position = [0.22499999403953552, 2.299999952316284, 0.7649999856948853]
book_A[0].rotation = [0, 0, 0.0157079639172164]
book_A[0].optimize = 2
cutlery_B[0].position = [2.25, 1.7999999523162842, 0.7649999856948853]
cutlery_B[0].rotation = [0, 0, 1.5833626980517244]
cutlery_B[0].optimize = 2
plant_A[0].position = [0.30000001192092896, 0.3499999940395355, 0.75]
plant_A[0].rotation = [0, 0, 0.01256637125682779]
plant_A[0].optimize = 2
candle_D[0].position = [2.75, 2.119999885559082, 0.8400000333786011]
candle_D[0].rotation = [0, 0, 0.01256637125682779]
candle_D[0].optimize = 2
plantcorner_A[0].position = [0.1698325276374817, 0.8999999761581421, 0.3100000023841858]
plantcorner_A[0].rotation = [0, 0, 0.0009846755760793532]
plantcorner_A[0].optimize = 2
chair_C[0].position = [3.25, 1.1799999475479126, 0.4000000059604645]
chair_C[0].rotation = [0, 0, 1.5833626980517244]
chair_C[0].optimize = 2
peppershaker_B[0].position = [2.8299999237060547, 1.8799999952316284, 0.800000011920929]
peppershaker_B[0].rotation = [0, 0, 0.01256637125682779]
peppershaker_B[0].optimize = 2
chair_F[0].position = [3.25, 2.8499999046325684, 0.4099999964237213]
chair_F[0].rotation = [0, 0, -1.5582299555380688]
chair_F[0].optimize = 2
plant_C[0].position = [4.71999979019165, 0.3499999940395355, 0.7699999809265137]
plant_C[0].rotation = [0, 0, 1.5833626980517244]
plant_C[0].optimize = 2
cutlery_A[0].position = [1.7699999809265137, 1.7999999523162842, 0.7649999856948853]
cutlery_A[0].rotation = [0, 0, 1.5833626980517244]
cutlery_A[0].optimize = 2
candle_B[0].position = [2.3499999046325684, 2.119999885559082, 0.8400000333786011]
candle_B[0].rotation = [0, 0, 0.01256637125682779]
candle_B[0].optimize = 2
candle_E[0].position = [2.450000047683716, 2.3299999237060547, 0.800000011920929]
candle_E[0].rotation = [0, 0, 0.01256637125682779]
candle_E[0].optimize = 2
glass_A[0].position = [2.0, 2.049999952316284, 0.8050000071525574]
glass_A[0].rotation = [0, 0, 0.01256637125682779]
glass_A[0].optimize = 2
oliveoilbottle[0].position = [2.680000066757202, 2.3299999237060547, 0.875]
oliveoilbottle[0].rotation = [0, 0, 0.01256637125682779]
oliveoilbottle[0].optimize = 2
candle_A[0].position = [0.22499999403953552, 1.8799999952316284, 0.8600000143051147]
candle_A[0].rotation = [0, 0, 0.01256637125682779]
candle_A[0].optimize = 2
plate_B[0].position = [3.0999999046325684, 1.7999999523162842, 0.7649999856948853]
plate_B[0].rotation = [0, 0, 0.01256637125682779]
plate_B[0].optimize = 2
chair_D[0].position = [1.850000023841858, 2.8499999046325684, 0.4099999964237213]
chair_D[0].rotation = [0, 0, -1.5582299555380688]
chair_D[0].optimize = 2
plant_B[0].position = [0.8500000238418579, 0.3499999940395355, 0.7350000143051147]
plant_B[0].rotation = [0, 0, 0.01256637125682779]
plant_B[0].optimize = 2
glass_D[0].position = [3.0999999046325684, 2.299999952316284, 0.8050000071525574]
glass_D[0].rotation = [0, 0, 0.01256637125682779]
glass_D[0].optimize = 2
sideboard[0].position = [0.22025929391384125, 2.5, 0.375]
sideboard[0].rotation = [0, 0, 0.00014166710166715386]
sideboard[0].optimize = 2
sidetable[0].position = [4.681435585021973, 0.3499999940395355, 0.23999999463558197]
sidetable[0].rotation = [0, 0, 1.842314371591291]
sidetable[0].optimize = 2
lamp_A[0].position = [1.7000000476837158, 0.208969846367836, 0.7900000214576721]
lamp_A[0].rotation = [0, 0, 1.5718311373355929]
lamp_A[0].optimize = 2
chair_G[0].position = [1.2999999523162842, 2.0, 0.4000000059604645]
chair_G[0].rotation = [0, 0, 0.01256637125682779]
chair_G[0].optimize = 2
lamp_E[0].position = [3.4000000953674316, 0.23914405703544617, 0.824999988079071]
lamp_E[0].rotation = [0, 0, 1.5718307839015377]
lamp_E[0].optimize = 2
chair_A[0].position = [1.850000023841858, 1.1799999475479126, 0.4099999964237213]
chair_A[0].rotation = [0, 0, 1.5833626980517244]
chair_A[0].optimize = 2
lamp_B[0].position = [2.130000114440918, 0.16346007585525513, 0.7749999761581421]
lamp_B[0].rotation = [0, 0, 1.571817266729759]
lamp_B[0].optimize = 2
cutlery_C[0].position = [2.8499999046325684, 1.7999999523162842, 0.7649999856948853]
cutlery_C[0].rotation = [0, 0, 1.5833626980517244]
cutlery_C[0].optimize = 2
lamp_D[0].position = [2.940000057220459, 0.19891279935836792, 0.8100000023841858]
lamp_D[0].rotation = [0, 0, 1.571831252213422]
lamp_D[0].optimize = 2
chair_E[0].position = [2.549999952316284, 2.8499999046325684, 0.4099999964237213]
chair_E[0].rotation = [0, 0, -1.5582299555380688]
chair_E[0].optimize = 2
saltshaker_A[0].position = [2.380000114440918, 1.8799999952316284, 0.800000011920929]
saltshaker_A[0].rotation = [0, 0, 0.01256637125682779]
saltshaker_A[0].optimize = 2
stool_B[0].position = [0.8500000238418579, 0.3499999940395355, 0.23000000417232513]
stool_B[0].rotation = [0, 0, 0.01256637125682779]
stool_B[0].optimize = 2
plant_G[0].position = [4.300000190734863, 3.2805235385894775, 0.625]
plant_G[0].rotation = [0, 0, -1.5697907085713003]
plant_G[0].optimize = 2
lamp_C[0].position = [2.5299999713897705, 0.19891279935836792, 0.800000011920929]
lamp_C[0].rotation = [0, 0, 1.571831252213422]
lamp_C[0].optimize = 2
glass_C[0].position = [2.0, 2.299999952316284, 0.8050000071525574]
glass_C[0].rotation = [0, 0, 0.01256637125682779]
glass_C[0].optimize = 2
bench[0].position = [4.808747291564941, 2.75, 0.22499999403953552]
bench[0].rotation = [0, 0, -3.1405574512601544]
bench[0].optimize = 2
plantcorner_B[0].position = [0.75, 3.3265395164489746, 0.3100000023841858]
plantcorner_B[0].rotation = [0, 0, -1.569776447122161]
plantcorner_B[0].optimize = 2
vase[0].position = [0.22499999403953552, 2.8299999237060547, 0.9099999666213989]
vase[0].rotation = [0, 0, 0.01256637125682779]
vase[0].optimize = 2
peppershaker_A[0].position = [2.5299999713897705, 1.8799999952316284, 0.8050000071525574]
peppershaker_A[0].rotation = [0, 0, 0.01256637125682779]
peppershaker_A[0].optimize = 2
book_D[0].position = [0.22499999403953552, 2.299999952316284, 0.8549998998641968]
book_D[0].rotation = [0, 0, 0.01256637125682779]
book_D[0].optimize = 2
stool_A[0].position = [0.30000001192092896, 0.3499999940395355, 0.23000000417232513]
stool_A[0].rotation = [0, 0, 0.01256637125682779]
stool_A[0].optimize = 2
candle_C[0].position = [2.549999952316284, 2.119999885559082, 0.8600000143051147]
candle_C[0].rotation = [0, 0, 0.01256637125682779]
candle_C[0].optimize = 2
book_C[0].position = [0.22499999403953552, 2.299999952316284, 0.8249999284744263]
book_C[0].rotation = [0, 0, 0.0157079639172164]
book_C[0].optimize = 2
saltshaker_B[0].position = [2.680000066757202, 1.8799999952316284, 0.800000011920929]
saltshaker_B[0].rotation = [0, 0, 0.01256637125682779]
saltshaker_B[0].optimize = 2
cutlery_D[0].position = [3.3399999141693115, 1.7999999523162842, 0.7649999856948853]
cutlery_D[0].rotation = [0, 0, 1.5833626980517244]
cutlery_D[0].optimize = 2
remote[0].position = [0.22499999403953552, 3.119999885559082, 0.7599999904632568]
remote[0].rotation = [0, 0, 1.5833626980517244]
remote[0].optimize = 2
plant_F[0].position = [4.300000190734863, 0.2194763720035553, 0.625]
plant_F[0].rotation = [0, 0, 1.5718019400829533]
plant_F[0].optimize = 2
plant_D[0].position = [1.2999999523162842, 0.15984243154525757, 0.28999999165534973]
plant_D[0].rotation = [0, 0, 1.5717805793239752]
plant_D[0].optimize = 2
book_B[0].position = [0.22499999403953552, 2.299999952316284, 0.7949999570846558]
book_B[0].rotation = [0, 0, 0.0157079639172164]
book_B[0].optimize = 2
chair_B[0].position = [2.549999952316284, 1.1799999475479126, 0.4099999964237213]
chair_B[0].rotation = [0, 0, 1.5833626980517244]
chair_B[0].optimize = 2
plate_A[0].position = [2.0, 1.7999999523162842, 0.7649999856948853]
plate_A[0].rotation = [0, 0, 0.01256637125682779]
plate_A[0].optimize = 2
plant_E[0].position = [4.019999980926514, 0.1498127281665802, 0.28999999165534973]
plant_E[0].rotation = [0, 0, 1.5717816166891283]
plant_E[0].optimize = 2
glass_B[0].position = [3.0999999046325684, 2.049999952316284, 0.8050000071525574]
glass_B[0].rotation = [0, 0, 0.01256637125682779]
glass_B[0].optimize = 2
table[0].position = [2.549999952316284, 2.0, 0.375]
table[0].rotation = [0, 0, 1.6619025111206214]
table[0].optimize = 2

