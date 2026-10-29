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
wine_cabinet = Assets(description="A tall, gray wine cabinet with multiple compartments for storing bottles. It features upper storage sections with visible bottle slots and lower cabinets with doors. The design includes a countertop area for additional functionality.", size=[0.45, 2.00, 2.30], placements=[AssetInstance() for _ in range(1)])
l_shaped_sofa = Assets(description="A modern sectional sofa with a combination of gray fabric and accent pillows in yellow and dark blue. The design features a clean, minimalist look with a chaise lounge extension.", size=[1.85, 3.10, 0.85], placements=[AssetInstance() for _ in range(1)])
slippers_A = Assets(description="A pair of white slippers with a simple design, featuring a single strap across the foot. They are placed on a black surface.", size=[0.28, 0.24, 0.08], placements=[AssetInstance() for _ in range(1)])
tv_stand = Assets(description="A sleek, modern media console with a minimalist design. It features a long rectangular body with rounded edges and a central cutout for cable management or additional storage. The console has two side compartments, one with a drawer and a circular handle, and the other with a flat surface. The botto", size=[0.45, 2.20, 0.45], placements=[AssetInstance() for _ in range(1)])
shelf = Assets(description="A tall, ornate coat rack with a slender metal frame. It features decorative hooks at the top for hanging coats or hats and a lower circular base for umbrellas or canes.", size=[0.45, 0.45, 1.80], placements=[AssetInstance() for _ in range(1)])
slippers_B = Assets(description="A pair of white slippers with a simple design, featuring a single strap across the foot. They are placed on a black surface.", size=[0.28, 0.24, 0.08], placements=[AssetInstance() for _ in range(1)])
sandals = Assets(description="A pair of brown sandals with braided straps and a flat sole, displayed on a black surface.", size=[0.27, 0.24, 0.07], placements=[AssetInstance() for _ in range(1)])
dining_table = Assets(description="A sleek dining table with a rectangular top and four slender legs that taper towards the bottom. The design is minimalist and modern.", size=[0.90, 1.80, 0.75], placements=[AssetInstance() for _ in range(1)])
cat = Assets(description="A white cat curled up and sleeping on a patterned cushion with a giraffe print design.", size=[0.38, 0.48, 0.22], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="A pair of modern side tables with wooden legs and hexagonal tabletops. One table holds a potted plant while the other has decorative vases.", size=[0.65, 1.15, 0.45], placements=[AssetInstance() for _ in range(1)])

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

wine_cabinet[0].position = [2.9884783312586842, 7.541033383848166, 1.15]
wine_cabinet[0].rotation = [0, 0, 0]
l_shaped_sofa[0].position = [5.500825808740899, 2.1191782054756167, 0.425]
l_shaped_sofa[0].rotation = [0, 0, 0]
slippers_A[0].position = [2.0607645979638236, 3.735254815781817, 0.04]
slippers_A[0].rotation = [0, 0, 0]
tv_stand[0].position = [3.6279758009036023, 8.022610516838006, 0.225]
tv_stand[0].rotation = [0, 0, 0]
shelf[0].position = [3.1532791550398707, 8.053841375440005, 0.9]
shelf[0].rotation = [0, 0, 0]
slippers_B[0].position = [4.312084511511832, 3.5966620647986893, 0.04]
slippers_B[0].rotation = [0, 0, 0]
sandals[0].position = [2.0902130941518298, 4.368240073241759, 0.035]
sandals[0].rotation = [0, 0, 0]
dining_table[0].position = [2.9752830156966903, 7.511734202078161, 0.375]
dining_table[0].rotation = [0, 0, 0]
cat[0].position = [5.765582835927527, 1.868481602192136, 0.11]
cat[0].rotation = [0, 0, 0]
coffee_table[0].position = [6.301214650114974, 2.410182928983215, 0.225]
coffee_table[0].rotation = [0, 0, 0]
wine_cabinet[0].position = [2.9884783312586842, 7.541033383848166, 1.15]
wine_cabinet[0].rotation = [0, 0, 0]
l_shaped_sofa[0].position = [5.500825808740899, 2.1191782054756167, 0.425]
l_shaped_sofa[0].rotation = [0, 0, 0]
slippers_A[0].position = [2.0607645979638236, 3.735254815781817, 0.04]
slippers_A[0].rotation = [0, 0, 0]
tv_stand[0].position = [3.6279758009036023, 8.022610516838006, 0.225]
tv_stand[0].rotation = [0, 0, 0]
shelf[0].position = [3.1532791550398707, 8.053841375440005, 0.9]
shelf[0].rotation = [0, 0, 0]
slippers_B[0].position = [4.312084511511832, 3.5966620647986893, 0.04]
slippers_B[0].rotation = [0, 0, 0]
sandals[0].position = [2.0902130941518298, 4.368240073241759, 0.035]
sandals[0].rotation = [0, 0, 0]
dining_table[0].position = [2.9752830156966903, 7.511734202078161, 0.375]
dining_table[0].rotation = [0, 0, 0]
cat[0].position = [5.765582835927527, 1.868481602192136, 0.11]
cat[0].rotation = [0, 0, 0]
coffee_table[0].position = [6.301214650114974, 2.410182928983215, 0.225]
coffee_table[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the upper part of the room as the lounge, with the sofa facing east
# toward the TV. The lower part accommodates dining and entry storage.
# Coordinates follow the supplied boundary (rather than recentering it).
placement_specs = [
    # Asset, center position, upright yaw in degrees
    (wine_cabinet,  [2.975, 1.40, 1.15],   0),
    (l_shaped_sofa, [2.065, 6.35, 0.425],  0),
    (tv_stand,      [5.115, 6.35, 0.225], 180),
    (coffee_table,  [3.750, 6.35, 0.225],  0),
    (dining_table,  [4.250, 2.50, 0.375],  0),
    (shelf,         [6.115, 0.95, 0.900], 180),
    (slippers_A,    [6.050, 1.55, 0.040], 180),
    (slippers_B,    [6.050, 2.00, 0.040], 180),
    (sandals,       [6.050, 2.45, 0.035], 180),
    (cat,           [2.050, 7.10, 0.960],  0),
]

for asset_group, center_position, yaw_degrees in placement_specs:
    asset_group[0].position = center_position[:]
    asset_group[0].rotation = [0, 0, radians(yaw_degrees)]

# Important positional constraints come first. Fixed, non-rendered reference
# points preserve the planned bays and keep all three door approaches clear.
# The furniture footprints are disjoint; the cat intentionally rests on the sofa.
layout_anchors = []
for asset_group, center_position, yaw_degrees in placement_specs:
    reference_point = AssetInstance(
        position=center_position[:],
        rotation=[0, 0, radians(yaw_degrees)]
    )
    layout_anchors.append(reference_point)
    solver.distance_constraint(
        asset_group[0], reference_point, 0.0, 0.0, weight=10
    )

# Preserve the key functional relationship in both directions.
solver.point_towards(l_shaped_sofa[0], tv_stand[0])
solver.point_towards(tv_stand[0], l_shaped_sofa[0])

# Surface support for the sleeping cat. Footwear belongs on the floor;
# its small size does not make it a tabletop accessory.
solver.on_top_of(cat[0], l_shaped_sofa[0])
solver.align_with(cat[0], l_shaped_sofa[0])

# Give every remaining instance an explicit orientation constraint.
# Sofa, TV, and cat already have their semantic orientation constraints.
for spec_index, (asset_group, center_position, yaw_degrees) in enumerate(placement_specs):
    if asset_group is not l_shaped_sofa and asset_group is not tv_stand and asset_group is not cat:
        solver.align_with(asset_group[0], layout_anchors[spec_index])

# Cabinet occupies the lower west wall, away from the door at (2.11, 2.69).
solver.against_wall(wine_cabinet[0], walls[2])

# Lounge furniture backs onto opposing walls; the coffee table remains
# between the sofa and console with usable gaps on either side.
solver.against_wall(l_shaped_sofa[0], walls[16])
solver.against_wall(tv_stand[0], walls[10])
solver.align_with(coffee_table[0], l_shaped_sofa[0])
solver.distance_constraint(
    coffee_table[0], l_shaped_sofa[0], 1.60, 1.80, weight=10
)
solver.distance_constraint(
    coffee_table[0], tv_stand[0], 1.30, 1.50, weight=10
)

# Entry coat rack and footwear stay along the east edge, not in the
# bottom door's approach. Keep separate floor bays for each pair.
solver.against_wall(shelf[0], walls[8])
solver.distance_constraint(slippers_A[0], slippers_B[0], 0.40, 0.55)
solver.distance_constraint(slippers_B[0], sandals[0], 0.40, 0.55)

# Preserve separation of the dining footprint from the tall cabinet.
solver.distance_constraint(
    dining_table[0], wine_cabinet[0], 1.75, 2.10, weight=10
)

solver.constraints = []
cat[0].position = [2.049999952316284, 7.099999904632568, 0.9600000381469727]
cat[0].rotation = [0, 0, -0.0001104750431121906]
cat[0].optimize = 2
dining_table[0].position = [4.379876613616943, 2.6298041343688965, 0.375]
dining_table[0].rotation = [0, 0, 0.01256637125682779]
dining_table[0].optimize = 2
shelf[0].position = [6.115784168243408, 0.949999988079071, 0.8999999761581421]
shelf[0].rotation = [0, 0, 3.1415455497034377]
shelf[0].optimize = 2
slippers_B[0].position = [6.050000190734863, 2.0, 0.03999999910593033]
slippers_B[0].rotation = [0, 0, -3.125884689672577]
slippers_B[0].optimize = 2
sandals[0].position = [6.050000190734863, 2.450000047683716, 0.03500000014901161]
sandals[0].rotation = [0, 0, -3.1290262823329655]
sandals[0].optimize = 2
slippers_A[0].position = [6.050000190734863, 1.5499999523162842, 0.03999999910593033]
slippers_A[0].rotation = [0, 0, -3.1290262823329655]
slippers_A[0].optimize = 2
wine_cabinet[0].position = [2.973379373550415, 1.399999976158142, 1.149999976158142]
wine_cabinet[0].rotation = [0, 0, -5.006332920292649e-05]
wine_cabinet[0].optimize = 2
l_shaped_sofa[0].position = [2.1111695766448975, 6.349999904632568, 0.42500001192092896]
l_shaped_sofa[0].rotation = [0, 0, -7.738316042218824e-05]
l_shaped_sofa[0].optimize = 2
coffee_table[0].position = [3.75, 6.349999904632568, 0.22499999403953552]
coffee_table[0].rotation = [0, 0, 4.301904759605191e-06]
coffee_table[0].optimize = 2
tv_stand[0].position = [4.234608173370361, 6.349999904632568, 0.22499999403953552]
tv_stand[0].rotation = [0, 0, -1.2072386472717274]
tv_stand[0].optimize = 2

