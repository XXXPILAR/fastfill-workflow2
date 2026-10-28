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
    Wall(corner1=[0.00, 4.02, 0.00], corner2=[0.00, 2.69, 0.00]),
    Wall(corner1=[0.00, 2.69, 0.00], corner2=[2.75, 2.69, 0.00]),
    Wall(corner1=[2.75, 2.69, 0.00], corner2=[2.75, 0.24, 0.00]),
    Wall(corner1=[2.75, 0.24, 0.00], corner2=[4.91, 0.24, 0.00]),
    Wall(corner1=[4.91, 0.24, 0.00], corner2=[4.91, 0.00, 0.00]),
    Wall(corner1=[4.91, 0.00, 0.00], corner2=[5.81, 0.00, 0.00]),
    Wall(corner1=[5.81, 0.00, 0.00], corner2=[5.81, 0.24, 0.00]),
    Wall(corner1=[5.81, 0.24, 0.00], corner2=[6.34, 0.24, 0.00]),
    Wall(corner1=[6.34, 0.24, 0.00], corner2=[6.34, 4.09, 0.00]),
    Wall(corner1=[6.34, 4.09, 0.00], corner2=[5.34, 4.09, 0.00]),
    Wall(corner1=[5.34, 4.09, 0.00], corner2=[5.34, 8.12, 0.00]),
    Wall(corner1=[5.34, 8.12, 0.00], corner2=[4.83, 8.12, 0.00]),
    Wall(corner1=[4.83, 8.12, 0.00], corner2=[4.83, 8.36, 0.00]),
    Wall(corner1=[4.83, 8.36, 0.00], corner2=[1.72, 8.36, 0.00]),
    Wall(corner1=[1.72, 8.36, 0.00], corner2=[1.72, 8.12, 0.00]),
    Wall(corner1=[1.72, 8.12, 0.00], corner2=[1.14, 8.12, 0.00]),
    Wall(corner1=[1.14, 8.12, 0.00], corner2=[1.14, 4.02, 0.00]),
    Wall(corner1=[1.14, 4.02, 0.00], corner2=[0.00, 4.02, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
wine_cabinet = Assets(description="A tall, gray wine cabinet with multiple compartments for storing bottles. It features upper storage sections with visible bottle slots and lower cabinets with doors. The design includes a countertop area for additional functionality.", size=[0.45, 1.60, 2.20], placements=[AssetInstance() for _ in range(1)])
l_shaped_sofa = Assets(description="A modern sectional sofa with a combination of gray fabric and accent pillows in yellow and dark blue. The design features a clean, minimalist look with a chaise lounge extension.", size=[2.00, 3.20, 0.85], placements=[AssetInstance() for _ in range(1)])
slippers_A = Assets(description="A pair of white slippers with a simple design, featuring a single strap across the foot. They are placed on a black surface.", size=[0.22, 0.28, 0.08], placements=[AssetInstance() for _ in range(1)])
tv_stand = Assets(description="A sleek, modern media console with a minimalist design. It features a long rectangular body with rounded edges and a central cutout for cable management or additional storage. The console has two side compartments, one with a drawer and a circular handle, and the other with a flat surface. The botto", size=[0.42, 2.00, 0.48], placements=[AssetInstance() for _ in range(1)])
shelf = Assets(description="A tall, ornate coat rack with a slender metal frame. It features decorative hooks at the top for hanging coats or hats and a lower circular base for umbrellas or canes.", size=[0.45, 0.65, 1.85], placements=[AssetInstance() for _ in range(1)])
slippers_B = Assets(description="A pair of white slippers with a simple design, featuring a single strap across the foot. They are placed on a black surface.", size=[0.22, 0.28, 0.08], placements=[AssetInstance() for _ in range(1)])
sandals = Assets(description="A pair of brown sandals with braided straps and a flat sole, displayed on a black surface.", size=[0.22, 0.27, 0.08], placements=[AssetInstance() for _ in range(1)])
dining_table = Assets(description="A sleek dining table with a rectangular top and four slender legs that taper towards the bottom. The design is minimalist and modern.", size=[0.90, 1.80, 0.75], placements=[AssetInstance() for _ in range(1)])
cat = Assets(description="A white cat curled up and sleeping on a patterned cushion with a giraffe print design.", size=[0.35, 0.45, 0.22], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="A pair of modern side tables with wooden legs and hexagonal tabletops. One table holds a potted plant while the other has decorative vases.", size=[0.65, 1.20, 0.52], placements=[AssetInstance() for _ in range(1)])

wine_cabinet[0].instance_id = 'wine_cabinet_0'
l_shaped_sofa[0].instance_id = 'l_shaped_sofa_0'
slippers_A[0].instance_id = 'slippers_A_0'
tv_stand[0].instance_id = 'tv_stand_0'
shelf[0].instance_id = 'shelf_0'
slippers_B[0].instance_id = 'slippers_B_0'
sandals[0].instance_id = 'sandals_0'
dining_table[0].instance_id = 'dining_table_0'
cat[0].instance_id = 'cat_0'
coffee_table[0].instance_id = 'coffee_table_0'
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
walls[14].instance_id = 'walls_14'
walls[15].instance_id = 'walls_15'
walls[16].instance_id = 'walls_16'
walls[17].instance_id = 'walls_17'

wine_cabinet[0].position = [4.587243437355312, 5.553937593683067, 1.1]
wine_cabinet[0].rotation = [0, 0, 0]
l_shaped_sofa[0].position = [2.8417925108448507, 4.9406020722994, 0.425]
l_shaped_sofa[0].rotation = [0, 0, 0]
slippers_A[0].position = [4.62612190600502, 3.1727694447002404, 0.04]
slippers_A[0].rotation = [0, 0, 0]
tv_stand[0].position = [4.760739052660547, 3.1000648871735375, 0.24]
tv_stand[0].rotation = [0, 0, 0]
shelf[0].position = [0.09418697012571874, 3.141248917783221, 0.925]
shelf[0].rotation = [0, 0, 0]
slippers_B[0].position = [2.878450022634136, 1.3913749750658708, 0.04]
slippers_B[0].rotation = [0, 0, 0]
sandals[0].position = [6.013282403454841, 2.282030754043118, 0.04]
sandals[0].rotation = [0, 0, 0]
dining_table[0].position = [6.30402270404639, 0.855228762157719, 0.375]
dining_table[0].rotation = [0, 0, 0]
cat[0].position = [0.6835638950159596, 3.6744219867653642, 0.11]
cat[0].rotation = [0, 0, 0]
coffee_table[0].position = [3.2139427597232464, 2.9462686774014566, 0.26]
coffee_table[0].rotation = [0, 0, 0]
wine_cabinet[0].position = [4.587243437355312, 5.553937593683067, 1.1]
wine_cabinet[0].rotation = [0, 0, 0]
l_shaped_sofa[0].position = [2.8417925108448507, 4.9406020722994, 0.425]
l_shaped_sofa[0].rotation = [0, 0, 0]
slippers_A[0].position = [4.62612190600502, 3.1727694447002404, 0.04]
slippers_A[0].rotation = [0, 0, 0]
tv_stand[0].position = [4.760739052660547, 3.1000648871735375, 0.24]
tv_stand[0].rotation = [0, 0, 0]
shelf[0].position = [0.09418697012571874, 3.141248917783221, 0.925]
shelf[0].rotation = [0, 0, 0]
slippers_B[0].position = [2.878450022634136, 1.3913749750658708, 0.04]
slippers_B[0].rotation = [0, 0, 0]
sandals[0].position = [6.013282403454841, 2.282030754043118, 0.04]
sandals[0].rotation = [0, 0, 0]
dining_table[0].position = [6.30402270404639, 0.855228762157719, 0.375]
dining_table[0].rotation = [0, 0, 0]
cat[0].position = [0.6835638950159596, 3.6744219867653642, 0.11]
cat[0].rotation = [0, 0, 0]
coffee_table[0].position = [3.2139427597232464, 2.9462686774014566, 0.26]
coffee_table[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the living area in the upper portion of the room. The sofa backs
# against the left wall and faces the TV console on the opposite wall.
l_shaped_sofa.placements[0].position = [2.14, 6.20, 0.425]
l_shaped_sofa.placements[0].rotation = [0, 0, radians(0)]

tv_stand.placements[0].position = [5.13, 6.20, 0.24]
tv_stand.placements[0].rotation = [0, 0, radians(180)]

coffee_table.placements[0].position = [3.90, 6.20, 0.26]
coffee_table.placements[0].rotation = [0, 0, radians(0)]

# Put the sleeping cat on the sofa, away from the main circulation paths.
cat.placements[0].position = [2.35, 6.30, 0.96]
cat.placements[0].rotation = [0, 0, radians(0)]

# Place the dining table in the lower room while retaining a clear route from
# the bottom door and avoiding the doorway at (2.11, 2.69).
dining_table.placements[0].position = [4.05, 2.95, 0.375]
dining_table.placements[0].rotation = [0, 0, radians(90)]

# Place the wine cabinet against the lower room's right wall, outside the
# direct approach from the door centered at (5.37, 0.00).
wine_cabinet.placements[0].position = [6.115, 1.25, 1.10]
wine_cabinet.placements[0].rotation = [0, 0, radians(180)]

# Use the quiet upper-right corner for the coat rack and footwear. This keeps
# all three door approaches clear.
shelf.placements[0].position = [4.50, 8.135, 0.925]
shelf.placements[0].rotation = [0, 0, radians(-90)]

slippers_A.placements[0].position = [3.30, 8.12, 0.04]
slippers_A.placements[0].rotation = [0, 0, radians(-90)]

slippers_B.placements[0].position = [3.60, 8.12, 0.04]
slippers_B.placements[0].rotation = [0, 0, radians(-90)]

sandals.placements[0].position = [3.91, 8.12, 0.04]
sandals.placements[0].rotation = [0, 0, radians(-90)]


# Important wall relationships are specified first. The following anchor
# constraints preserve the selected, non-overlapping positions along them.
solver.against_wall(wine_cabinet[0], walls[8])
solver.distance_constraint(
    wine_cabinet[0],
    AssetInstance(position=[6.115, 1.25, 1.10]),
    0, 0, weight=10
)
solver.align_with(wine_cabinet[0], tv_stand[0])

solver.against_wall(l_shaped_sofa[0], walls[16])
solver.distance_constraint(
    l_shaped_sofa[0],
    AssetInstance(position=[2.14, 6.20, 0.425]),
    0, 0, weight=10
)
solver.point_towards(l_shaped_sofa[0], tv_stand[0])

solver.against_wall(tv_stand[0], walls[10])
solver.distance_constraint(
    tv_stand[0],
    AssetInstance(position=[5.13, 6.20, 0.24]),
    0, 0, weight=10
)
solver.point_towards(tv_stand[0], l_shaped_sofa[0])

# Maintain the functional viewing distance between the principal living-room
# assets even if the solver later makes small feasibility adjustments.
solver.distance_constraint(
    l_shaped_sofa[0], tv_stand[0], 2.80, 3.20, weight=10
)

solver.distance_constraint(
    coffee_table[0],
    AssetInstance(position=[3.90, 6.20, 0.26]),
    0, 0, weight=10
)
solver.distance_constraint(coffee_table[0], l_shaped_sofa[0], 1.55, 1.95)
solver.distance_constraint(coffee_table[0], tv_stand[0], 1.05, 1.45)
solver.align_with(coffee_table[0], l_shaped_sofa[0])

solver.distance_constraint(
    dining_table[0],
    AssetInstance(position=[4.05, 2.95, 0.375]),
    0, 0, weight=10
)
solver.align_with(dining_table[0], l_shaped_sofa[0], angle=90)

# The cat is supported by the sofa. Its positional constraint keeps it near
# the sofa's center rather than near an edge.
solver.on_top_of(cat[0], l_shaped_sofa[0])
solver.distance_constraint(cat[0], l_shaped_sofa[0], 0.45, 0.75, weight=10)
solver.point_towards(cat[0], coffee_table[0])

solver.against_wall(shelf[0], walls[13])
solver.distance_constraint(
    shelf[0],
    AssetInstance(position=[4.50, 8.135, 0.925]),
    0, 0, weight=10
)
solver.align_with(shelf[0], dining_table[0], angle=180)

# Footwear remains on the floor in a compact row beside the coat rack.
solver.distance_constraint(
    slippers_A[0],
    AssetInstance(position=[3.30, 8.12, 0.04]),
    0, 0, weight=10
)
solver.align_with(slippers_A[0], shelf[0])

solver.distance_constraint(
    slippers_B[0],
    AssetInstance(position=[3.60, 8.12, 0.04]),
    0, 0, weight=10
)
solver.align_with(slippers_B[0], shelf[0])

solver.distance_constraint(
    sandals[0],
    AssetInstance(position=[3.91, 8.12, 0.04]),
    0, 0, weight=10
)
solver.align_with(sandals[0], shelf[0])

solver.constraints = []
l_shaped_sofa[0].position = [2.197403907775879, 6.199999809265137, 0.42500001192092896]
l_shaped_sofa[0].rotation = [0, 0, 2.0329590092568197e-06]
l_shaped_sofa[0].optimize = 2
slippers_B[0].position = [3.5999999046325684, 8.119999885559082, 0.03999999910593033]
slippers_B[0].rotation = [0, 0, -1.5704400468578463]
slippers_B[0].optimize = 2
slippers_A[0].position = [3.299999952316284, 8.119999885559082, 0.03999999910593033]
slippers_A[0].rotation = [0, 0, -1.5704400468578463]
slippers_A[0].optimize = 2
tv_stand[0].position = [5.132719039916992, 6.199999809265137, 0.23999999463558197]
tv_stand[0].rotation = [0, 0, -3.1415920876400008]
tv_stand[0].optimize = 2
sandals[0].position = [3.9100000858306885, 8.119999885559082, 0.03999999910593033]
sandals[0].rotation = [0, 0, -1.5704400468578463]
sandals[0].optimize = 2
shelf[0].position = [5.017719745635986, 7.891380786895752, 0.925000011920929]
shelf[0].rotation = [0, 0, -1.5707967853985816]
shelf[0].optimize = 2
wine_cabinet[0].position = [6.1158294677734375, 1.25, 1.100000023841858]
wine_cabinet[0].rotation = [0, 0, 3.141591931627498]
wine_cabinet[0].optimize = 2
cat[0].position = [2.3499999046325684, 6.300000190734863, 0.9600000381469727]
cat[0].rotation = [0, 0, 0.01256637125682779]
cat[0].optimize = 2
coffee_table[0].position = [3.9000000953674316, 6.199999809265137, 0.25999999046325684]
coffee_table[0].rotation = [0, 0, -8.226096476882476e-06]
coffee_table[0].optimize = 2
dining_table[0].position = [4.050000190734863, 2.950000047683716, 0.375]
dining_table[0].rotation = [0, 0, 1.5707886577053816]
dining_table[0].optimize = 2

