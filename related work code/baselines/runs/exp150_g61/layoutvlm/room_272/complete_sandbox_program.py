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
    Wall(corner1=[6.90, 0.00, 0.00], corner2=[6.90, 1.87, 0.00]),
    Wall(corner1=[6.90, 1.87, 0.00], corner2=[8.19, 1.87, 0.00]),
    Wall(corner1=[8.19, 1.87, 0.00], corner2=[8.19, 2.94, 0.00]),
    Wall(corner1=[8.19, 2.94, 0.00], corner2=[3.68, 2.94, 0.00]),
    Wall(corner1=[3.68, 2.94, 0.00], corner2=[3.68, 7.04, 0.00]),
    Wall(corner1=[3.68, 7.04, 0.00], corner2=[0.00, 7.04, 0.00]),
    Wall(corner1=[0.00, 7.04, 0.00], corner2=[0.00, 3.58, 0.00]),
    Wall(corner1=[0.00, 3.58, 0.00], corner2=[1.29, 3.58, 0.00]),
    Wall(corner1=[1.29, 3.58, 0.00], corner2=[1.29, 2.77, 0.00]),
    Wall(corner1=[1.29, 2.77, 0.00], corner2=[1.79, 2.77, 0.00]),
    Wall(corner1=[1.79, 2.77, 0.00], corner2=[1.79, 0.55, 0.00]),
    Wall(corner1=[1.79, 0.55, 0.00], corner2=[1.49, 0.55, 0.00]),
    Wall(corner1=[1.49, 0.55, 0.00], corner2=[1.49, 0.00, 0.00]),
    Wall(corner1=[1.49, 0.00, 0.00], corner2=[6.90, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
tv_cabinet = Assets(description="tv cabinet", size=[0.45, 2.40, 0.55], placements=[AssetInstance() for _ in range(1)])
wine_cabinet = Assets(description="wine cabinet", size=[0.45, 1.20, 2.00], placements=[AssetInstance() for _ in range(1)])
refrigerator = Assets(description="refrigerator", size=[0.75, 0.90, 1.85], placements=[AssetInstance() for _ in range(1)])
sofa = Assets(description="sofa", size=[1.00, 3.00, 0.85], placements=[AssetInstance() for _ in range(1)])
carpet_A = Assets(description="carpet", size=[2.60, 3.60, 0.01], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="coffee table", size=[0.70, 1.30, 0.42], placements=[AssetInstance() for _ in range(1)])
carpet_B = Assets(description="carpet", size=[2.50, 3.00, 0.01], placements=[AssetInstance() for _ in range(1)])
entrance_cabinet = Assets(description="entrance cabinet", size=[0.35, 1.20, 1.10], placements=[AssetInstance() for _ in range(1)])
dining_table_combination = Assets(description="dining table combination", size=[2.10, 2.60, 0.90], placements=[AssetInstance() for _ in range(1)])

tv_cabinet[0].instance_id = 'tv_cabinet_0'
wine_cabinet[0].instance_id = 'wine_cabinet_0'
refrigerator[0].instance_id = 'refrigerator_0'
sofa[0].instance_id = 'sofa_0'
carpet_A[0].instance_id = 'carpet_A_0'
coffee_table[0].instance_id = 'coffee_table_0'
carpet_B[0].instance_id = 'carpet_B_0'
entrance_cabinet[0].instance_id = 'entrance_cabinet_0'
dining_table_combination[0].instance_id = 'dining_table_combination_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'
walls[8].instance_id = 'walls_8'
walls[9].instance_id = 'walls_9'
walls[10].instance_id = 'walls_10'
walls[11].instance_id = 'walls_11'
walls[12].instance_id = 'walls_12'
walls[13].instance_id = 'walls_13'

tv_cabinet[0].position = [0.5325796593769476, 5.86989344301254, 0.275]
tv_cabinet[0].rotation = [0, 0, 0]
wine_cabinet[0].position = [5.4010001911892385, 2.736571218024763, 1.0]
wine_cabinet[0].rotation = [0, 0, 0]
refrigerator[0].position = [0.6893532137302338, 4.505525168500971, 0.925]
refrigerator[0].rotation = [0, 0, 0]
sofa[0].position = [2.839293004683624, 2.2127676639284717, 0.425]
sofa[0].rotation = [0, 0, 0]
carpet_A[0].position = [1.9988758578340173, 1.2641809215754123, 0.0075]
carpet_A[0].rotation = [0, 0, 0]
coffee_table[0].position = [1.8129102127559797, 5.8930204176583185, 0.21]
coffee_table[0].rotation = [0, 0, 0]
carpet_B[0].position = [6.744674621857418, 2.5392456051528858, 0.0075]
carpet_B[0].rotation = [0, 0, 0]
entrance_cabinet[0].position = [2.0580343723169414, 3.6447731241054977, 0.55]
entrance_cabinet[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [3.93139390580305, 1.9716251210330156, 0.45]
dining_table_combination[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [0.5325796593769476, 5.86989344301254, 0.275]
tv_cabinet[0].rotation = [0, 0, 0]
wine_cabinet[0].position = [5.4010001911892385, 2.736571218024763, 1.0]
wine_cabinet[0].rotation = [0, 0, 0]
refrigerator[0].position = [0.6893532137302338, 4.505525168500971, 0.925]
refrigerator[0].rotation = [0, 0, 0]
sofa[0].position = [2.839293004683624, 2.2127676639284717, 0.425]
sofa[0].rotation = [0, 0, 0]
carpet_A[0].position = [1.9988758578340173, 1.2641809215754123, 0.0075]
carpet_A[0].rotation = [0, 0, 0]
coffee_table[0].position = [1.8129102127559797, 5.8930204176583185, 0.21]
coffee_table[0].rotation = [0, 0, 0]
carpet_B[0].position = [6.744674621857418, 2.5392456051528858, 0.0075]
carpet_B[0].rotation = [0, 0, 0]
entrance_cabinet[0].position = [2.0580343723169414, 3.6447731241054977, 0.55]
entrance_cabinet[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [3.93139390580305, 1.9716251210330156, 0.45]
dining_table_combination[0].rotation = [0, 0, 0]

solver.constraints = []

# The upper rectangular bay is the living room; the lower bay is the
# dining area. Keep the eastern door corridor and the western entry route
# free of furniture. Rugs intentionally extend underneath furniture.
layout_specs = [
    (tv_cabinet, [3.455, 5.25, 0.285], 180),
    (wine_cabinet, [1.90, 6.815, 1.00], 270),
    (refrigerator, [6.525, 0.50, 0.925], 180),
    (sofa, [0.50, 5.25, 0.435], 0),
    (carpet_A, [1.84, 5.25, 0.005], 90),
    (coffee_table, [1.95, 5.25, 0.22], 0),
    (carpet_B, [4.55, 1.62, 0.005], 90),
    (entrance_cabinet, [3.55, 0.175, 0.55], 90),
    (dining_table_combination, [4.55, 1.62, 0.46], 90),
]

for asset_group, initial_position, yaw_degrees in layout_specs:
    asset_group[0].position = initial_position
    asset_group[0].rotation = [0, 0, radians(yaw_degrees)]

# Preserve the chosen zones with fixed-coordinate positional constraints.
# These anchors are references only, not additional physical assets.
# Exact center positions also preserve clearance from the bathroom cabinet
# near (1.53, 3.15), the entrance, and all eastern door openings.
for asset_group, initial_position, yaw_degrees in layout_specs:
    solver.distance_constraint(
        asset_group[0],
        AssetInstance(position=list(initial_position)),
        0,
        0,
        weight=10,
    )

# Wall-backed furniture: prioritize the required refrigerator wall contact.
solver.against_wall(refrigerator[0], walls[0])
solver.against_wall(sofa[0], walls[6])
solver.against_wall(tv_cabinet[0], walls[4])
solver.against_wall(wine_cabinet[0], walls[5])
solver.against_wall(entrance_cabinet[0], walls[13])

# Living-room furniture faces into the seating area.
solver.point_towards(sofa[0], tv_cabinet[0])
solver.point_towards(tv_cabinet[0], sofa[0])
solver.align_with(coffee_table[0], sofa[0])
solver.align_with(carpet_A[0], sofa[0], angle=90)

# Cabinets open away from their supporting walls.
solver.align_with(
    refrigerator[0],
    AssetInstance(rotation=[0, 0, radians(180)]),
)
solver.align_with(
    wine_cabinet[0],
    AssetInstance(rotation=[0, 0, radians(270)]),
)
solver.align_with(
    entrance_cabinet[0],
    AssetInstance(rotation=[0, 0, radians(90)]),
)

# Rotate the dining ensemble so its 2.60 m dimension runs east-west.
# The rug remains flat and does not obstruct the door approach.
solver.align_with(
    carpet_B[0],
    AssetInstance(rotation=[0, 0, radians(90)]),
)
solver.align_with(dining_table_combination[0], carpet_B[0])

# Account for the rugs' thickness rather than intersecting them.
# The coffee table is supported by the living-room rug, not by the sofa.
solver.on_top_of(sofa[0], carpet_A[0])
solver.on_top_of(tv_cabinet[0], carpet_A[0])
solver.on_top_of(coffee_table[0], carpet_A[0])
solver.on_top_of(dining_table_combination[0], carpet_B[0])

# Maintain useful seating clearances if the layout is subsequently adjusted.
solver.distance_constraint(coffee_table[0], sofa[0], 1.35, 1.60)
solver.distance_constraint(coffee_table[0], tv_cabinet[0], 1.35, 1.65)
solver.distance_constraint(sofa[0], tv_cabinet[0], 2.85, 3.10)

solver.constraints = []
tv_cabinet[0].position = [3.452061176300049, 5.25, 0.2849999964237213]
tv_cabinet[0].rotation = [0, 0, 3.141520770000203]
tv_cabinet[0].optimize = 2
refrigerator[0].position = [6.435366153717041, 0.5, 0.925000011920929]
refrigerator[0].rotation = [0, 0, -1.6024252696955703]
refrigerator[0].optimize = 2
coffee_table[0].position = [1.9500000476837158, 5.25, 0.2199999988079071]
coffee_table[0].rotation = [0, 0, 0.0002787212064025729]
coffee_table[0].optimize = 2
sofa[0].position = [0.5002742409706116, 5.25, 0.4350000023841858]
sofa[0].rotation = [0, 0, -5.5736067852587796e-05]
sofa[0].optimize = 2
carpet_B[0].position = [4.550000190734863, 1.6200000047683716, 0.004999999888241291]
carpet_B[0].rotation = [0, 0, 1.586504290712113]
carpet_B[0].optimize = 2
dining_table_combination[0].position = [4.550000190734863, 1.6200000047683716, 0.4599999785423279]
dining_table_combination[0].rotation = [0, 0, 1.5864669360348866]
dining_table_combination[0].optimize = 2
carpet_A[0].position = [1.840000033378601, 5.25, 0.004999999888241291]
carpet_A[0].rotation = [0, 0, 1.5710750938945746]
carpet_A[0].optimize = 2
entrance_cabinet[0].position = [3.549999952316284, 0.6052340865135193, 0.550000011920929]
entrance_cabinet[0].rotation = [0, 0, 3.1099637106891196]
entrance_cabinet[0].optimize = 2
wine_cabinet[0].position = [1.899999976158142, 6.437184810638428, 1.0]
wine_cabinet[0].rotation = [0, 0, -0.03162894290067374]
wine_cabinet[0].optimize = 2

