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
wall_art_print_A = Assets(description="A picture inside of a metallic frame.", size=[0.04, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
vanity_cabinet = Assets(description="A kitchen sink with a wood cabinet.", size=[0.55, 1.20, 0.85], placements=[AssetInstance() for _ in range(1)])
tall_bathroom_cabinet = Assets(description="tall bathroom cabinet", size=[0.35, 0.40, 1.80], placements=[AssetInstance() for _ in range(1)])
small_floor_plant = Assets(description="A bunch of big leaves inside of a white pot.", size=[0.45, 0.45, 0.70], placements=[AssetInstance() for _ in range(1)])
laundry_hamper = Assets(description="A gray metal trash can with a brown band towards the bottom and a brown handle.", size=[0.38, 0.38, 0.60], placements=[AssetInstance() for _ in range(1)])
wall_art_print_B = Assets(description="A picture inside of a metallic frame.", size=[0.04, 0.50, 0.70], placements=[AssetInstance() for _ in range(1)])
bathroom_wall_shelf_A = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.20, 0.60, 0.18], placements=[AssetInstance() for _ in range(1)])
under_sink_storage_basket_A = Assets(description="A rectangular wicker basket with the handles folded down.", size=[0.30, 0.38, 0.25], placements=[AssetInstance() for _ in range(1)])
under_sink_storage_basket_B = Assets(description="A rectangular wicker basket with the handles folded down.", size=[0.30, 0.38, 0.25], placements=[AssetInstance() for _ in range(1)])
mirror_cabinet = Assets(description="Cabinet with four shelves and one door.", size=[0.16, 0.60, 0.75], placements=[AssetInstance() for _ in range(1)])
bath_sponge = Assets(description="A yellow and green dish sponge.", size=[0.07, 0.11, 0.04], placements=[AssetInstance() for _ in range(1)])
small_bath_stool = Assets(description="A three legged wood round stool.", size=[0.32, 0.32, 0.45], placements=[AssetInstance() for _ in range(1)])
bathroom_wall_shelf_B = Assets(description="A set of shelves with one rectangular wooden board and two rusted bookenders.", size=[0.20, 0.60, 0.18], placements=[AssetInstance() for _ in range(1)])
toilet = Assets(description="A ceramic toilet with a black seat.", size=[0.70, 0.40, 0.78], placements=[AssetInstance() for _ in range(1)])
freestanding_towel_ladder = Assets(description="A black towel rack.", size=[0.35, 0.55, 1.70], placements=[AssetInstance() for _ in range(1)])
soap_dispenser = Assets(description="White soap bottle model", size=[0.08, 0.08, 0.20], placements=[AssetInstance() for _ in range(1)])
wall_hook_row = Assets(description="A coatrack with arabic words on it.", size=[0.08, 0.65, 0.20], placements=[AssetInstance() for _ in range(1)])

wall_art_print_A[0].instance_id = 'wall_art_print_A_0'
vanity_cabinet[0].instance_id = 'vanity_cabinet_0'
tall_bathroom_cabinet[0].instance_id = 'tall_bathroom_cabinet_0'
small_floor_plant[0].instance_id = 'small_floor_plant_0'
laundry_hamper[0].instance_id = 'laundry_hamper_0'
wall_art_print_B[0].instance_id = 'wall_art_print_B_0'
bathroom_wall_shelf_A[0].instance_id = 'bathroom_wall_shelf_A_0'
under_sink_storage_basket_A[0].instance_id = 'under_sink_storage_basket_A_0'
under_sink_storage_basket_B[0].instance_id = 'under_sink_storage_basket_B_0'
mirror_cabinet[0].instance_id = 'mirror_cabinet_0'
bath_sponge[0].instance_id = 'bath_sponge_0'
small_bath_stool[0].instance_id = 'small_bath_stool_0'
bathroom_wall_shelf_B[0].instance_id = 'bathroom_wall_shelf_B_0'
toilet[0].instance_id = 'toilet_0'
freestanding_towel_ladder[0].instance_id = 'freestanding_towel_ladder_0'
soap_dispenser[0].instance_id = 'soap_dispenser_0'
wall_hook_row[0].instance_id = 'wall_hook_row_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

wall_art_print_A[0].position = [0.6740169627947785, 1.5391223287146385, 0.35]
wall_art_print_A[0].rotation = [0, 0, 0]
vanity_cabinet[0].position = [2.260710596745192, 2.3697050564939834, 0.425]
vanity_cabinet[0].rotation = [0, 0, 0]
tall_bathroom_cabinet[0].position = [2.4384813357766233, 0.4707208927723223, 0.9]
tall_bathroom_cabinet[0].rotation = [0, 0, 0]
small_floor_plant[0].position = [0.25917430160386834, 1.8976875995855123, 0.35]
small_floor_plant[0].rotation = [0, 0, 0]
laundry_hamper[0].position = [0.010571564718212634, 1.5365392202041686, 0.3]
laundry_hamper[0].rotation = [0, 0, 0]
wall_art_print_B[0].position = [0.8344070822355024, 2.287764186038621, 0.35]
wall_art_print_B[0].rotation = [0, 0, 0]
bathroom_wall_shelf_A[0].position = [1.1478309048991766, 2.376852807829118, 0.09]
bathroom_wall_shelf_A[0].rotation = [0, 0, 0]
under_sink_storage_basket_A[0].position = [1.0496190075794147, 2.7089070384826517, 0.125]
under_sink_storage_basket_A[0].rotation = [0, 0, 0]
under_sink_storage_basket_B[0].position = [1.188898744661492, 2.1509822496542865, 0.125]
under_sink_storage_basket_B[0].rotation = [0, 0, 0]
mirror_cabinet[0].position = [2.154598823366375, 0.8778511946861579, 0.375]
mirror_cabinet[0].rotation = [0, 0, 0]
bath_sponge[0].position = [1.73868704105162, 0.10702124623075093, 0.02]
bath_sponge[0].rotation = [0, 0, 0]
small_bath_stool[0].position = [1.5207662422236434, 1.0837715351645658, 0.225]
small_bath_stool[0].rotation = [0, 0, 0]
bathroom_wall_shelf_B[0].position = [1.676712007283632, 2.648890567978727, 0.09]
bathroom_wall_shelf_B[0].rotation = [0, 0, 0]
toilet[0].position = [1.9092864124533122, 1.7719372131959097, 0.39]
toilet[0].rotation = [0, 0, 0]
freestanding_towel_ladder[0].position = [1.7620841337739859, 1.5297995063858782, 0.85]
freestanding_towel_ladder[0].rotation = [0, 0, 0]
soap_dispenser[0].position = [0.4102900173005837, 0.9929904214776063, 0.1]
soap_dispenser[0].rotation = [0, 0, 0]
wall_hook_row[0].position = [1.365810421180392, 1.214061770153732, 0.1]
wall_hook_row[0].rotation = [0, 0, 0]
wall_art_print_A[0].position = [0.6740169627947785, 1.5391223287146385, 0.35]
wall_art_print_A[0].rotation = [0, 0, 0]
vanity_cabinet[0].position = [2.260710596745192, 2.3697050564939834, 0.425]
vanity_cabinet[0].rotation = [0, 0, 0]
tall_bathroom_cabinet[0].position = [2.4384813357766233, 0.4707208927723223, 0.9]
tall_bathroom_cabinet[0].rotation = [0, 0, 0]
small_floor_plant[0].position = [0.25917430160386834, 1.8976875995855123, 0.35]
small_floor_plant[0].rotation = [0, 0, 0]
laundry_hamper[0].position = [0.010571564718212634, 1.5365392202041686, 0.3]
laundry_hamper[0].rotation = [0, 0, 0]
wall_art_print_B[0].position = [0.8344070822355024, 2.287764186038621, 0.35]
wall_art_print_B[0].rotation = [0, 0, 0]
bathroom_wall_shelf_A[0].position = [1.1478309048991766, 2.376852807829118, 0.09]
bathroom_wall_shelf_A[0].rotation = [0, 0, 0]
under_sink_storage_basket_A[0].position = [1.0496190075794147, 2.7089070384826517, 0.125]
under_sink_storage_basket_A[0].rotation = [0, 0, 0]
under_sink_storage_basket_B[0].position = [1.188898744661492, 2.1509822496542865, 0.125]
under_sink_storage_basket_B[0].rotation = [0, 0, 0]
mirror_cabinet[0].position = [2.154598823366375, 0.8778511946861579, 0.375]
mirror_cabinet[0].rotation = [0, 0, 0]
bath_sponge[0].position = [1.73868704105162, 0.10702124623075093, 0.02]
bath_sponge[0].rotation = [0, 0, 0]
small_bath_stool[0].position = [1.5207662422236434, 1.0837715351645658, 0.225]
small_bath_stool[0].rotation = [0, 0, 0]
bathroom_wall_shelf_B[0].position = [1.676712007283632, 2.648890567978727, 0.09]
bathroom_wall_shelf_B[0].rotation = [0, 0, 0]
toilet[0].position = [1.9092864124533122, 1.7719372131959097, 0.39]
toilet[0].rotation = [0, 0, 0]
freestanding_towel_ladder[0].position = [1.7620841337739859, 1.5297995063858782, 0.85]
freestanding_towel_ladder[0].rotation = [0, 0, 0]
soap_dispenser[0].position = [0.4102900173005837, 0.9929904214776063, 0.1]
soap_dispenser[0].rotation = [0, 0, 0]
wall_hook_row[0].position = [1.365810421180392, 1.214061770153732, 0.1]
wall_hook_row[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed heading references used to preserve deliberate orientations.
east_heading = AssetInstance(rotation=[0, 0, radians(0)])
north_heading = AssetInstance(rotation=[0, 0, radians(90)])
west_heading = AssetInstance(rotation=[0, 0, radians(180)])
south_heading = AssetInstance(rotation=[0, 0, radians(-90)])

# The vanity occupies the middle of the west wall. This leaves the doorway
# and the east-wall window clear while providing open space in front of it.
vanity_cabinet.placements[0] = AssetInstance(
    position=[0.275, 1.50, 0.425],
    rotation=[0, 0, radians(0)]
)

# The mirror is centered above the vanity.
mirror_cabinet.placements[0] = AssetInstance(
    position=[0.08, 1.50, 1.40],
    rotation=[0, 0, radians(0)]
)

# The two baskets are immediately in front of the lower part of the vanity.
# Basket A is directly west of the toilet so the toilet can face it.
under_sink_storage_basket_A.placements[0] = AssetInstance(
    position=[0.78, 1.25, 0.125],
    rotation=[0, 0, radians(0)]
)
under_sink_storage_basket_B.placements[0] = AssetInstance(
    position=[0.78, 1.78, 0.125],
    rotation=[0, 0, radians(0)]
)

# Small countertop objects are separated along the vanity top.
soap_dispenser.placements[0] = AssetInstance(
    position=[0.30, 1.25, 0.95],
    rotation=[0, 0, radians(0)]
)
bath_sponge.placements[0] = AssetInstance(
    position=[0.30, 1.70, 0.87],
    rotation=[0, 0, radians(0)]
)

# The toilet is against the east wall, north of the window, and faces
# directly toward under-sink basket A.
toilet.placements[0] = AssetInstance(
    position=[2.65, 1.25, 0.39],
    rotation=[0, 0, radians(180)]
)

# The required wall-side stool is farther north on the east wall, separated
# from the toilet and outside the window opening.
small_bath_stool.placements[0] = AssetInstance(
    position=[2.84, 2.05, 0.225],
    rotation=[0, 0, radians(180)]
)

# Tall and floor-standing accessories use the north side of the room while
# retaining a broad central circulation aisle.
tall_bathroom_cabinet.placements[0] = AssetInstance(
    position=[0.30, 2.825, 0.90],
    rotation=[0, 0, radians(-90)]
)
small_floor_plant.placements[0] = AssetInstance(
    position=[1.25, 2.70, 0.35],
    rotation=[0, 0, radians(-90)]
)
freestanding_towel_ladder.placements[0] = AssetInstance(
    position=[2.05, 2.825, 0.85],
    rotation=[0, 0, radians(-90)]
)
laundry_hamper.placements[0] = AssetInstance(
    position=[2.75, 2.75, 0.30],
    rotation=[0, 0, radians(-90)]
)

# Wall-mounted decorations and storage remain above floor furniture.
wall_art_print_A.placements[0] = AssetInstance(
    position=[1.25, 2.98, 1.65],
    rotation=[0, 0, radians(-90)]
)
wall_art_print_B.placements[0] = AssetInstance(
    position=[2.60, 0.02, 1.85],
    rotation=[0, 0, radians(90)]
)
bathroom_wall_shelf_A.placements[0] = AssetInstance(
    position=[1.80, 0.10, 1.15],
    rotation=[0, 0, radians(90)]
)
bathroom_wall_shelf_B.placements[0] = AssetInstance(
    position=[2.55, 0.10, 1.15],
    rotation=[0, 0, radians(90)]
)
wall_hook_row.placements[0] = AssetInstance(
    position=[2.96, 2.52, 1.35],
    rotation=[0, 0, radians(180)]
)

# Exact target points are the highest-priority position constraints. They
# preserve clearances between objects and keep the door approach unobstructed.
vanity_target = AssetInstance(position=[0.275, 1.50, 0.425])
mirror_target = AssetInstance(position=[0.08, 1.50, 1.40])
basket_A_target = AssetInstance(position=[0.78, 1.25, 0.125])
basket_B_target = AssetInstance(position=[0.78, 1.78, 0.125])
soap_target = AssetInstance(position=[0.30, 1.25, 0.95])
sponge_target = AssetInstance(position=[0.30, 1.70, 0.87])
toilet_target = AssetInstance(position=[2.65, 1.25, 0.39])
stool_target = AssetInstance(position=[2.84, 2.05, 0.225])
tall_cabinet_target = AssetInstance(position=[0.30, 2.825, 0.90])
plant_target = AssetInstance(position=[1.25, 2.70, 0.35])
towel_ladder_target = AssetInstance(position=[2.05, 2.825, 0.85])
hamper_target = AssetInstance(position=[2.75, 2.75, 0.30])
art_A_target = AssetInstance(position=[1.25, 2.98, 1.65])
art_B_target = AssetInstance(position=[2.60, 0.02, 1.85])
shelf_A_target = AssetInstance(position=[1.80, 0.10, 1.15])
shelf_B_target = AssetInstance(position=[2.55, 0.10, 1.15])
hook_target = AssetInstance(position=[2.96, 2.52, 1.35])

solver.distance_constraint(
    vanity_cabinet[0], vanity_target, 0, 0, weight=10
)
solver.distance_constraint(
    mirror_cabinet[0], mirror_target, 0, 0, weight=10
)
solver.distance_constraint(
    under_sink_storage_basket_A[0], basket_A_target, 0, 0, weight=10
)
solver.distance_constraint(
    under_sink_storage_basket_B[0], basket_B_target, 0, 0, weight=10
)
solver.distance_constraint(
    soap_dispenser[0], soap_target, 0, 0, weight=10
)
solver.distance_constraint(
    bath_sponge[0], sponge_target, 0, 0, weight=10
)
solver.distance_constraint(
    toilet[0], toilet_target, 0, 0, weight=10
)
solver.distance_constraint(
    small_bath_stool[0], stool_target, 0, 0, weight=10
)
solver.distance_constraint(
    tall_bathroom_cabinet[0], tall_cabinet_target, 0, 0, weight=10
)
solver.distance_constraint(
    small_floor_plant[0], plant_target, 0, 0, weight=10
)
solver.distance_constraint(
    freestanding_towel_ladder[0], towel_ladder_target, 0, 0, weight=10
)
solver.distance_constraint(
    laundry_hamper[0], hamper_target, 0, 0, weight=10
)
solver.distance_constraint(
    wall_art_print_A[0], art_A_target, 0, 0, weight=10
)
solver.distance_constraint(
    wall_art_print_B[0], art_B_target, 0, 0, weight=10
)
solver.distance_constraint(
    bathroom_wall_shelf_A[0], shelf_A_target, 0, 0, weight=10
)
solver.distance_constraint(
    bathroom_wall_shelf_B[0], shelf_B_target, 0, 0, weight=10
)
solver.distance_constraint(
    wall_hook_row[0], hook_target, 0, 0, weight=10
)

# Wall-contact constraints maintain the intended perimeter arrangement.
solver.against_wall(vanity_cabinet[0], walls[1])
solver.against_wall(mirror_cabinet[0], walls[1])
solver.against_wall(toilet[0], walls[3])
solver.against_wall(small_bath_stool[0], walls[3])
solver.against_wall(tall_bathroom_cabinet[0], walls[0])
solver.against_wall(freestanding_towel_ladder[0], walls[0])
solver.against_wall(laundry_hamper[0], walls[0])
solver.against_wall(wall_art_print_A[0], walls[0])
solver.against_wall(wall_art_print_B[0], walls[2])
solver.against_wall(bathroom_wall_shelf_A[0], walls[2])
solver.against_wall(bathroom_wall_shelf_B[0], walls[2])
solver.against_wall(wall_hook_row[0], walls[3])

# The soap and sponge must remain supported by the vanity countertop.
solver.on_top_of(soap_dispenser[0], vanity_cabinet[0])
solver.on_top_of(bath_sponge[0], vanity_cabinet[0])

# Orientation constraints for every asset. The toilet-to-basket relationship
# is specified first because it is the primary semantic orientation.
solver.point_towards(toilet[0], under_sink_storage_basket_A[0])

solver.align_with(vanity_cabinet[0], east_heading)
solver.align_with(mirror_cabinet[0], east_heading)
solver.align_with(under_sink_storage_basket_A[0], east_heading)
solver.align_with(under_sink_storage_basket_B[0], east_heading)
solver.align_with(soap_dispenser[0], east_heading)
solver.align_with(bath_sponge[0], east_heading)
solver.align_with(small_bath_stool[0], west_heading)
solver.align_with(tall_bathroom_cabinet[0], south_heading)
solver.align_with(small_floor_plant[0], south_heading)
solver.align_with(freestanding_towel_ladder[0], south_heading)
solver.align_with(laundry_hamper[0], south_heading)
solver.align_with(wall_art_print_A[0], south_heading)
solver.align_with(wall_art_print_B[0], north_heading)
solver.align_with(bathroom_wall_shelf_A[0], north_heading)
solver.align_with(bathroom_wall_shelf_B[0], north_heading)
solver.align_with(wall_hook_row[0], west_heading)

solver.constraints = []
bath_sponge[0].position = [0.30000001192092896, 1.7000000476837158, 0.8700000047683716]
bath_sponge[0].rotation = [0, 0, 0.01256637125682779]
bath_sponge[0].optimize = 2
tall_bathroom_cabinet[0].position = [0.30000001192092896, 2.826773166656494, 0.8999999761581421]
tall_bathroom_cabinet[0].rotation = [0, 0, -1.5665794606917667]
tall_bathroom_cabinet[0].optimize = 2
soap_dispenser[0].position = [0.30000001192092896, 1.25, 0.9500000476837158]
soap_dispenser[0].rotation = [0, 0, 0.01256637125682779]
soap_dispenser[0].optimize = 2
laundry_hamper[0].position = [2.75, 2.8108081817626953, 0.30000001192092896]
laundry_hamper[0].rotation = [0, 0, -1.5665522411351864]
laundry_hamper[0].optimize = 2
freestanding_towel_ladder[0].position = [2.049999952316284, 2.826322078704834, 0.8500000238418579]
freestanding_towel_ladder[0].rotation = [0, 0, -1.5665795580312833]
freestanding_towel_ladder[0].optimize = 2
wall_hook_row[0].position = [2.960880756378174, 2.5199999809265137, 0.10000000149011612]
wall_hook_row[0].rotation = [0, 0, -3.137378069687649]
wall_hook_row[0].optimize = 2
vanity_cabinet[0].position = [0.2769507169723511, 1.5, 0.42500001192092896]
vanity_cabinet[0].rotation = [0, 0, 0.0052947157998255705]
vanity_cabinet[0].optimize = 2
toilet[0].position = [2.6520864963531494, 1.25, 0.38999998569488525]
toilet[0].rotation = [0, 0, -3.1373728054644703]
toilet[0].optimize = 2
small_floor_plant[0].position = [1.25, 2.700000047683716, 0.3499999940395355]
small_floor_plant[0].rotation = [0, 0, -1.5613715493341729]
small_floor_plant[0].optimize = 2
under_sink_storage_basket_B[0].position = [0.7799999713897705, 1.7799999713897705, 0.125]
under_sink_storage_basket_B[0].rotation = [0, 0, 0.00942477746072377]
under_sink_storage_basket_B[0].optimize = 2
wall_art_print_A[0].position = [1.25, 2.981991767883301, 0.3499999940395355]
wall_art_print_A[0].rotation = [0, 0, -1.5665822698866934]
wall_art_print_A[0].optimize = 2
mirror_cabinet[0].position = [0.0789426788687706, 1.5, 0.375]
mirror_cabinet[0].rotation = [0, 0, 0.004215234979228042]
mirror_cabinet[0].optimize = 2
bathroom_wall_shelf_B[0].position = [2.549999952316284, 0.09891612827777863, 0.09000000357627869]
bathroom_wall_shelf_B[0].rotation = [0, 0, 1.575011874407736]
bathroom_wall_shelf_B[0].optimize = 2
small_bath_stool[0].position = [2.842010498046875, 2.049999952316284, 0.22499999403953552]
small_bath_stool[0].rotation = [0, 0, -3.137375983911638]
small_bath_stool[0].optimize = 2
under_sink_storage_basket_A[0].position = [0.7799999713897705, 1.25, 0.125]
under_sink_storage_basket_A[0].rotation = [0, 0, 0.01256637125682779]
under_sink_storage_basket_A[0].optimize = 2
bathroom_wall_shelf_A[0].position = [1.7999999523162842, 0.09891612827777863, 0.09000000357627869]
bathroom_wall_shelf_A[0].rotation = [0, 0, 1.575011874407736]
bathroom_wall_shelf_A[0].optimize = 2
wall_art_print_B[0].position = [2.5999999046325684, 0.017969947308301926, 0.3499999940395355]
wall_art_print_B[0].rotation = [0, 0, 1.5750103884892692]
wall_art_print_B[0].optimize = 2

