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
    Wall(corner1=[3.00, 3.00, 0.00], corner2=[0.00, 3.00, 0.00]),
    Wall(corner1=[0.00, 3.00, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.00, 0.00, 0.00]),
    Wall(corner1=[3.00, 0.00, 0.00], corner2=[3.00, 3.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
floor_planter = Assets(description="A potted plant with green leaves.", size=[0.45, 0.45, 0.95], placements=[AssetInstance() for _ in range(1)])
bath_stool = Assets(description="A dice with black and red dots.", size=[0.32, 0.32, 0.32], placements=[AssetInstance() for _ in range(1)])
bathroom_mirror_cabinet = Assets(description="A cabinet with two large doors and four drawers.", size=[0.20, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
wall_hung_toilet = Assets(description="A white toilet with black seat and silver chain.", size=[0.68, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
slim_bathroom_shelf_unit = Assets(description="A tall slim cupboard with four shelves in it.", size=[0.30, 0.35, 1.70], placements=[AssetInstance() for _ in range(1)])
glass_shower_enclosure = Assets(description="A set of gray sliding doors with black handles.", size=[0.90, 1.20, 2.00], placements=[AssetInstance() for _ in range(1)])
toilet_brush_set = Assets(description="toilet brush set", size=[0.12, 0.12, 0.40], placements=[AssetInstance() for _ in range(1)])
small_tray = Assets(description="a red apple on a white tray.", size=[0.20, 0.30, 0.10], placements=[AssetInstance() for _ in range(1)])
vanity_cabinet = Assets(description="A wooden nightstand with both its drawers open.", size=[0.50, 0.80, 0.75], placements=[AssetInstance() for _ in range(1)])
laundry_hamper = Assets(description="A wicker basket with pink bands and some blue patterns.", size=[0.35, 0.45, 0.60], placements=[AssetInstance() for _ in range(1)])
floor_towel_stand = Assets(description="a white pole with a blue handle.", size=[0.25, 0.45, 0.90], placements=[AssetInstance() for _ in range(1)])
small_bathroom_bin = Assets(description="A cream colored trash can.", size=[0.25, 0.25, 0.35], placements=[AssetInstance() for _ in range(1)])
tall_bathroom_storage_cabinet = Assets(description="tall bathroom storage cabinet", size=[0.35, 0.50, 1.90], placements=[AssetInstance() for _ in range(1)])

floor_planter[0].instance_id = 'floor_planter_0'
bath_stool[0].instance_id = 'bath_stool_0'
bathroom_mirror_cabinet[0].instance_id = 'bathroom_mirror_cabinet_0'
wall_hung_toilet[0].instance_id = 'wall_hung_toilet_0'
slim_bathroom_shelf_unit[0].instance_id = 'slim_bathroom_shelf_unit_0'
glass_shower_enclosure[0].instance_id = 'glass_shower_enclosure_0'
toilet_brush_set[0].instance_id = 'toilet_brush_set_0'
small_tray[0].instance_id = 'small_tray_0'
vanity_cabinet[0].instance_id = 'vanity_cabinet_0'
laundry_hamper[0].instance_id = 'laundry_hamper_0'
floor_towel_stand[0].instance_id = 'floor_towel_stand_0'
small_bathroom_bin[0].instance_id = 'small_bathroom_bin_0'
tall_bathroom_storage_cabinet[0].instance_id = 'tall_bathroom_storage_cabinet_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

floor_planter[0].position = [0.2593081964815709, 2.8811208997958735, 0.475]
floor_planter[0].rotation = [0, 0, 0]
bath_stool[0].position = [2.0870141266435542, 2.24109580928287, 0.16]
bath_stool[0].rotation = [0, 0, 0]
bathroom_mirror_cabinet[0].position = [0.7251544919697616, 1.835332060692684, 0.45]
bathroom_mirror_cabinet[0].rotation = [0, 0, 0]
wall_hung_toilet[0].position = [0.9934129463744084, 1.705328509506875, 0.39]
wall_hung_toilet[0].rotation = [0, 0, 0]
slim_bathroom_shelf_unit[0].position = [2.59878475640056, 0.45425609116865073, 0.85]
slim_bathroom_shelf_unit[0].rotation = [0, 0, 0]
glass_shower_enclosure[0].position = [1.7378166338993624, 1.1786119230827399, 1.0]
glass_shower_enclosure[0].rotation = [0, 0, 0]
toilet_brush_set[0].position = [1.6162831754397382, 1.7027205483533712, 0.2]
toilet_brush_set[0].rotation = [0, 0, 0]
small_tray[0].position = [1.7033547846987522, 1.853119431045696, 0.05]
small_tray[0].rotation = [0, 0, 0]
vanity_cabinet[0].position = [1.1485855309565454, 0.4255542063661638, 0.375]
vanity_cabinet[0].rotation = [0, 0, 0]
laundry_hamper[0].position = [0.98049489406059, 1.4681895766266344, 0.3]
laundry_hamper[0].rotation = [0, 0, 0]
floor_towel_stand[0].position = [0.8057837207461852, 0.05542065866448431, 0.45]
floor_towel_stand[0].rotation = [0, 0, 0]
small_bathroom_bin[0].position = [1.4617748373142758, 2.557939033450366, 0.175]
small_bathroom_bin[0].rotation = [0, 0, 0]
tall_bathroom_storage_cabinet[0].position = [2.5489362584670694, 2.6684309867580405, 0.95]
tall_bathroom_storage_cabinet[0].rotation = [0, 0, 0]
floor_planter[0].position = [0.2593081964815709, 2.8811208997958735, 0.475]
floor_planter[0].rotation = [0, 0, 0]
bath_stool[0].position = [2.0870141266435542, 2.24109580928287, 0.16]
bath_stool[0].rotation = [0, 0, 0]
bathroom_mirror_cabinet[0].position = [0.7251544919697616, 1.835332060692684, 0.45]
bathroom_mirror_cabinet[0].rotation = [0, 0, 0]
wall_hung_toilet[0].position = [0.9934129463744084, 1.705328509506875, 0.39]
wall_hung_toilet[0].rotation = [0, 0, 0]
slim_bathroom_shelf_unit[0].position = [2.59878475640056, 0.45425609116865073, 0.85]
slim_bathroom_shelf_unit[0].rotation = [0, 0, 0]
glass_shower_enclosure[0].position = [1.7378166338993624, 1.1786119230827399, 1.0]
glass_shower_enclosure[0].rotation = [0, 0, 0]
toilet_brush_set[0].position = [1.6162831754397382, 1.7027205483533712, 0.2]
toilet_brush_set[0].rotation = [0, 0, 0]
small_tray[0].position = [1.7033547846987522, 1.853119431045696, 0.05]
small_tray[0].rotation = [0, 0, 0]
vanity_cabinet[0].position = [1.1485855309565454, 0.4255542063661638, 0.375]
vanity_cabinet[0].rotation = [0, 0, 0]
laundry_hamper[0].position = [0.98049489406059, 1.4681895766266344, 0.3]
laundry_hamper[0].rotation = [0, 0, 0]
floor_towel_stand[0].position = [0.8057837207461852, 0.05542065866448431, 0.45]
floor_towel_stand[0].rotation = [0, 0, 0]
small_bathroom_bin[0].position = [1.4617748373142758, 2.557939033450366, 0.175]
small_bathroom_bin[0].rotation = [0, 0, 0]
tall_bathroom_storage_cabinet[0].position = [2.5489362584670694, 2.6684309867580405, 0.95]
tall_bathroom_storage_cabinet[0].rotation = [0, 0, 0]

solver.constraints = []

# Orientation references used to keep wall-mounted and freestanding assets
# consistently aligned. A zero rotation faces +x; -90 degrees faces -y.
faces_positive_x = AssetInstance(rotation=[0, 0, radians(0)])
faces_negative_x = AssetInstance(rotation=[0, 0, radians(180)])
faces_negative_y = AssetInstance(rotation=[0, 0, radians(-90)])

# Place the large fixtures around the perimeter, leaving the doorway's
# x=0.435..1.485 approach clear throughout the lower part of the room.
floor_planter[0].position = [2.35, 2.775, 0.475]
floor_planter[0].rotation = [0, 0, radians(-90)]

bath_stool[0].position = [1.48, 1.52, 0.16]
bath_stool[0].rotation = [0, 0, radians(0)]

# The mirror cabinet is supported by the vanity and kept against the right wall.
bathroom_mirror_cabinet[0].position = [2.90, 0.60, 1.20]
bathroom_mirror_cabinet[0].rotation = [0, 0, radians(180)]

# The toilet is on the left wall and faces across the room toward the towel stand.
wall_hung_toilet[0].position = [0.34, 1.52, 0.39]
wall_hung_toilet[0].rotation = [0, 0, radians(0)]

slim_bathroom_shelf_unit[0].position = [1.39, 2.85, 0.85]
slim_bathroom_shelf_unit[0].rotation = [0, 0, radians(-90)]

# Rotating the shower toward -y gives it a 1.20 m span along the top wall
# and a 0.90 m projection into the room.
glass_shower_enclosure[0].position = [0.60, 2.55, 1.00]
glass_shower_enclosure[0].rotation = [0, 0, radians(-90)]

toilet_brush_set[0].position = [0.08, 1.90, 0.20]
toilet_brush_set[0].rotation = [0, 0, radians(0)]

# The tray is offset toward the room-facing side of the vanity so that it
# does not intersect the mirror cabinet above the rear of the vanity.
small_tray[0].position = [2.63, 0.70, 0.80]
small_tray[0].rotation = [0, 0, radians(180)]

vanity_cabinet[0].position = [2.75, 0.60, 0.375]
vanity_cabinet[0].rotation = [0, 0, radians(180)]

laundry_hamper[0].position = [2.15, 1.50, 0.30]
laundry_hamper[0].rotation = [0, 0, radians(-90)]

floor_towel_stand[0].position = [1.00, 1.52, 0.45]
floor_towel_stand[0].rotation = [0, 0, radians(180)]

# This bin is above the window's y-range, so it does not obstruct the window.
small_bathroom_bin[0].position = [2.875, 2.78, 0.175]
small_bathroom_bin[0].rotation = [0, 0, radians(180)]

tall_bathroom_storage_cabinet[0].position = [1.84, 2.825, 0.95]
tall_bathroom_storage_cabinet[0].rotation = [0, 0, radians(-90)]


# Fixed center points preserve the non-overlapping arrangement while other
# constraints make small feasibility adjustments.
floor_planter_point = AssetInstance(position=[2.35, 2.775, 0.475])
bath_stool_point = AssetInstance(position=[1.48, 1.52, 0.16])
mirror_cabinet_point = AssetInstance(position=[2.90, 0.60, 1.20])
toilet_point = AssetInstance(position=[0.34, 1.52, 0.39])
slim_shelf_point = AssetInstance(position=[1.39, 2.85, 0.85])
shower_point = AssetInstance(position=[0.60, 2.55, 1.00])
toilet_brush_point = AssetInstance(position=[0.08, 1.90, 0.20])
tray_point = AssetInstance(position=[2.63, 0.70, 0.80])
vanity_point = AssetInstance(position=[2.75, 0.60, 0.375])
hamper_point = AssetInstance(position=[2.15, 1.50, 0.30])
towel_stand_point = AssetInstance(position=[1.00, 1.52, 0.45])
bin_point = AssetInstance(position=[2.875, 2.78, 0.175])
tall_cabinet_point = AssetInstance(position=[1.84, 2.825, 0.95])

solver.distance_constraint(floor_planter[0], floor_planter_point, 0, 0, weight=10)
solver.distance_constraint(bath_stool[0], bath_stool_point, 0, 0, weight=10)
solver.distance_constraint(bathroom_mirror_cabinet[0], mirror_cabinet_point, 0, 0, weight=10)
solver.distance_constraint(wall_hung_toilet[0], toilet_point, 0, 0, weight=10)
solver.distance_constraint(slim_bathroom_shelf_unit[0], slim_shelf_point, 0, 0, weight=10)
solver.distance_constraint(glass_shower_enclosure[0], shower_point, 0, 0, weight=10)
solver.distance_constraint(toilet_brush_set[0], toilet_brush_point, 0, 0, weight=10)
solver.distance_constraint(small_tray[0], tray_point, 0, 0, weight=10)
solver.distance_constraint(vanity_cabinet[0], vanity_point, 0, 0, weight=10)
solver.distance_constraint(laundry_hamper[0], hamper_point, 0, 0, weight=10)
solver.distance_constraint(floor_towel_stand[0], towel_stand_point, 0, 0, weight=10)
solver.distance_constraint(small_bathroom_bin[0], bin_point, 0, 0, weight=10)
solver.distance_constraint(
    tall_bathroom_storage_cabinet[0], tall_cabinet_point, 0, 0, weight=10
)

# Required vertical support relationships. The vanity top is at z=0.75,
# placing the tray center at z=0.80 and the mirror cabinet center at z=1.20.
solver.on_top_of(small_tray[0], vanity_cabinet[0])
solver.on_top_of(bathroom_mirror_cabinet[0], vanity_cabinet[0])

# Perimeter constraints maintain the intended bathroom fixture grouping.
solver.against_wall(glass_shower_enclosure[0], walls[0])
solver.against_wall(slim_bathroom_shelf_unit[0], walls[0])
solver.against_wall(tall_bathroom_storage_cabinet[0], walls[0])
solver.against_wall(floor_planter[0], walls[0])

solver.against_wall(wall_hung_toilet[0], walls[1])
solver.against_wall(toilet_brush_set[0], walls[1])

solver.against_wall(vanity_cabinet[0], walls[3])
solver.against_wall(bathroom_mirror_cabinet[0], walls[3])
solver.against_wall(small_bathroom_bin[0], walls[3])

# Preserve the functional relationship between the toilet and towel stand.
solver.distance_constraint(
    wall_hung_toilet[0], floor_towel_stand[0], 0.55, 0.80, weight=10
)

# Every new asset receives an orientation constraint. The toilet's most
# important orientation rule is specified directly against the towel stand.
solver.point_towards(wall_hung_toilet[0], floor_towel_stand[0])
solver.point_towards(floor_towel_stand[0], wall_hung_toilet[0])

solver.align_with(floor_planter[0], faces_negative_y)
solver.align_with(bath_stool[0], faces_positive_x)
solver.align_with(bathroom_mirror_cabinet[0], faces_negative_x)
solver.align_with(slim_bathroom_shelf_unit[0], faces_negative_y)
solver.align_with(glass_shower_enclosure[0], faces_negative_y)
solver.align_with(toilet_brush_set[0], faces_positive_x)
solver.align_with(small_tray[0], vanity_cabinet[0])
solver.align_with(vanity_cabinet[0], faces_negative_x)
solver.align_with(laundry_hamper[0], faces_negative_y)
solver.align_with(small_bathroom_bin[0], faces_negative_x)
solver.align_with(tall_bathroom_storage_cabinet[0], faces_negative_y)

solver.constraints = []
bath_stool[0].position = [1.4800000190734863, 1.5199999809265137, 0.1599999964237213]
bath_stool[0].rotation = [0, 0, 0.00942477746072377]
bath_stool[0].optimize = 2
toilet_brush_set[0].position = [0.07000012695789337, 1.899999976158142, 0.20000000298023224]
toilet_brush_set[0].rotation = [0, 0, 0.002540922439204702]
toilet_brush_set[0].optimize = 2
vanity_cabinet[0].position = [2.7452685832977295, 0.6000000238418579, 0.375]
vanity_cabinet[0].rotation = [0, 0, -3.129719633273273]
vanity_cabinet[0].optimize = 2
wall_hung_toilet[0].position = [0.3416517376899719, 1.5199999809265137, 0.38999998569488525]
wall_hung_toilet[0].rotation = [0, 0, 0.008762224756822399]
wall_hung_toilet[0].optimize = 2
glass_shower_enclosure[0].position = [0.6099991202354431, 2.5484769344329834, 1.0]
glass_shower_enclosure[0].rotation = [0, 0, -1.568255419665518]
glass_shower_enclosure[0].optimize = 2
small_tray[0].position = [2.630000114440918, 0.699999988079071, 0.800000011920929]
small_tray[0].rotation = [0, 0, -3.11880380104969]
small_tray[0].optimize = 2
tall_bathroom_storage_cabinet[0].position = [1.840000033378601, 2.8243653774261475, 0.949999988079071]
tall_bathroom_storage_cabinet[0].rotation = [0, 0, -1.5682554064999652]
tall_bathroom_storage_cabinet[0].optimize = 2
floor_planter[0].position = [2.3499999046325684, 2.7744290828704834, 0.4749999940395355]
floor_planter[0].rotation = [0, 0, -1.5682554055777918]
floor_planter[0].optimize = 2
floor_towel_stand[0].position = [1.0, 1.5199999809265137, 0.44999998807907104]
floor_towel_stand[0].rotation = [0, 0, -3.125884689672577]
floor_towel_stand[0].optimize = 2
slim_bathroom_shelf_unit[0].position = [1.3899999856948853, 2.849555730819702, 0.8500000238418579]
slim_bathroom_shelf_unit[0].rotation = [0, 0, -1.5682554052778654]
slim_bathroom_shelf_unit[0].optimize = 2
laundry_hamper[0].position = [2.1500000953674316, 1.5, 0.30000001192092896]
laundry_hamper[0].rotation = [0, 0, -1.5613715493341729]
laundry_hamper[0].optimize = 2
small_bathroom_bin[0].position = [2.874682664871216, 2.7799999713897705, 0.17499999701976776]
small_bathroom_bin[0].rotation = [0, 0, -3.139051732072762]
small_bathroom_bin[0].optimize = 2
bathroom_mirror_cabinet[0].position = [2.896610736846924, 0.6000000238418579, 1.2000000476837158]
bathroom_mirror_cabinet[0].rotation = [0, 0, -3.135941138107549]
bathroom_mirror_cabinet[0].optimize = 2

