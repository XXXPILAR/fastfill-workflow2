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
    Wall(corner1=[4.00, 0.00, 0.00], corner2=[4.00, 5.00, 0.00]),
    Wall(corner1=[4.00, 5.00, 0.00], corner2=[0.00, 5.00, 0.00]),
    Wall(corner1=[0.00, 5.00, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
dishwasher = Assets(description="built-in dishwasher with front panel and extended height", size=[0.60, 0.60, 0.87], placements=[AssetInstance() for _ in range(1)])
refrigerator = Assets(description="extra-large tall modern double-door refrigerator with freezer", size=[0.76, 0.91, 1.83], placements=[AssetInstance() for _ in range(1)])
floor_pantry_cabinet = Assets(description="tall freestanding pantry cabinet for extra kitchen storage", size=[0.60, 0.90, 2.10], placements=[AssetInstance() for _ in range(1)])
stove_and_oven_unit = Assets(description="modern freestanding gas stove with oven and built-in timer display", size=[0.70, 0.76, 0.92], placements=[AssetInstance() for _ in range(1)])
kitchen_island = Assets(description="larger central kitchen island with storage drawers and shelves, no seating", size=[0.90, 2.20, 0.91], placements=[AssetInstance() for _ in range(1)])
under_counter_wine_rack = Assets(description="built-in under-counter wine rack integrated into kitchen counter", size=[0.55, 0.45, 0.82], placements=[AssetInstance() for _ in range(1)])
microwave_oven = Assets(description="compact countertop microwave oven in stainless steel finish", size=[0.40, 0.50, 0.30], placements=[AssetInstance() for _ in range(1)])
kitchen_counter_with_cabinets = Assets(description="extended long linear kitchen counter with overhead and under-counter cabinets, modern style", size=[0.65, 3.60, 2.30], placements=[AssetInstance() for _ in range(1)])

dishwasher[0].instance_id = 'dishwasher_0'
refrigerator[0].instance_id = 'refrigerator_0'
floor_pantry_cabinet[0].instance_id = 'floor_pantry_cabinet_0'
stove_and_oven_unit[0].instance_id = 'stove_and_oven_unit_0'
kitchen_island[0].instance_id = 'kitchen_island_0'
under_counter_wine_rack[0].instance_id = 'under_counter_wine_rack_0'
microwave_oven[0].instance_id = 'microwave_oven_0'
kitchen_counter_with_cabinets[0].instance_id = 'kitchen_counter_with_cabinets_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

dishwasher[0].position = [0.6644104847583749, 2.918218335411556, 0.435]
dishwasher[0].rotation = [0, 0, 0]
refrigerator[0].position = [1.7219842989790033, 1.333149070420181, 0.915]
refrigerator[0].rotation = [0, 0, 0]
floor_pantry_cabinet[0].position = [2.730497320492988, 2.8642978129948733, 1.05]
floor_pantry_cabinet[0].rotation = [0, 0, 0]
stove_and_oven_unit[0].position = [2.9896442909198604, 2.6160736304680436, 0.46]
stove_and_oven_unit[0].rotation = [0, 0, 0]
kitchen_island[0].position = [2.765645875721594, 2.142585512562282, 0.455]
kitchen_island[0].rotation = [0, 0, 0]
under_counter_wine_rack[0].position = [2.917088074860277, 4.888092920905483, 0.41]
under_counter_wine_rack[0].rotation = [0, 0, 0]
microwave_oven[0].position = [3.0816311814206574, 2.7632050043497456, 0.15]
microwave_oven[0].rotation = [0, 0, 0]
kitchen_counter_with_cabinets[0].position = [1.4373675740502923, 3.8381816273129523, 1.15]
kitchen_counter_with_cabinets[0].rotation = [0, 0, 0]
dishwasher[0].position = [0.6644104847583749, 2.918218335411556, 0.435]
dishwasher[0].rotation = [0, 0, 0]
refrigerator[0].position = [1.7219842989790033, 1.333149070420181, 0.915]
refrigerator[0].rotation = [0, 0, 0]
floor_pantry_cabinet[0].position = [2.730497320492988, 2.8642978129948733, 1.05]
floor_pantry_cabinet[0].rotation = [0, 0, 0]
stove_and_oven_unit[0].position = [2.9896442909198604, 2.6160736304680436, 0.46]
stove_and_oven_unit[0].rotation = [0, 0, 0]
kitchen_island[0].position = [2.765645875721594, 2.142585512562282, 0.455]
kitchen_island[0].rotation = [0, 0, 0]
under_counter_wine_rack[0].position = [2.917088074860277, 4.888092920905483, 0.41]
under_counter_wine_rack[0].rotation = [0, 0, 0]
microwave_oven[0].position = [3.0816311814206574, 2.7632050043497456, 0.15]
microwave_oven[0].rotation = [0, 0, 0]
kitchen_counter_with_cabinets[0].position = [1.4373675740502923, 3.8381816273129523, 1.15]
kitchen_counter_with_cabinets[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the four major appliances in a compact row along the bottom wall.
# Rotating them 90 degrees makes their fronts face into the room (+y).
refrigerator[0].position = [0.505, 0.38, 0.915]
refrigerator[0].rotation = [0, 0, radians(90)]

floor_pantry_cabinet[0].position = [1.435, 0.30, 1.05]
floor_pantry_cabinet[0].rotation = [0, 0, radians(90)]

stove_and_oven_unit[0].position = [2.29, 0.35, 0.46]
stove_and_oven_unit[0].rotation = [0, 0, radians(90)]

dishwasher[0].position = [3.00, 0.30, 0.435]
dishwasher[0].rotation = [0, 0, radians(90)]

# Put the long cabinet-and-counter assembly against the right wall.
# Its front faces west, toward the usable center of the kitchen.
kitchen_counter_with_cabinets[0].position = [3.675, 2.75, 1.15]
kitchen_counter_with_cabinets[0].rotation = [0, 0, radians(180)]

# The required wall-adjacent island is placed against the top wall.
# Its long dimension runs horizontally and its front faces into the room.
kitchen_island[0].position = [1.30, 4.55, 0.455]
kitchen_island[0].rotation = [0, 0, radians(270)]

# Keep the wine rack against the otherwise-unused left wall, facing inward.
under_counter_wine_rack[0].position = [0.275, 3.55, 0.41]
under_counter_wine_rack[0].rotation = [0, 0, 0]

# The microwave is a small object, so place it on the island work surface.
microwave_oven[0].position = [1.30, 4.55, 1.06]
microwave_oven[0].rotation = [0, 0, radians(270)]


# Fixed orientation references preserve exact wall-parallel rotations.
north_orientation = AssetInstance(rotation=[0, 0, radians(90)])
west_orientation = AssetInstance(rotation=[0, 0, radians(180)])
south_orientation = AssetInstance(rotation=[0, 0, radians(270)])
east_orientation = AssetInstance(rotation=[0, 0, 0])

# Fixed placement references softly retain the selected non-overlapping
# positions while the wall constraints preserve the main layout semantics.
refrigerator_anchor = AssetInstance(position=[0.505, 0.38, 0.915])
pantry_anchor = AssetInstance(position=[1.435, 0.30, 1.05])
stove_anchor = AssetInstance(position=[2.29, 0.35, 0.46])
dishwasher_anchor = AssetInstance(position=[3.00, 0.30, 0.435])
counter_anchor = AssetInstance(position=[3.675, 2.75, 1.15])
island_anchor = AssetInstance(position=[1.30, 4.55, 0.455])
wine_rack_anchor = AssetInstance(position=[0.275, 3.55, 0.41])
microwave_anchor = AssetInstance(position=[1.30, 4.55, 1.06])


# Bottom-wall appliance run: wall placement and inward-facing orientation.
solver.against_wall(refrigerator[0], walls[3])
solver.align_with(refrigerator[0], north_orientation)
solver.distance_constraint(
    refrigerator[0], refrigerator_anchor, 0, 0, weight=0.1
)

solver.against_wall(floor_pantry_cabinet[0], walls[3])
solver.align_with(floor_pantry_cabinet[0], north_orientation)
solver.distance_constraint(
    floor_pantry_cabinet[0], pantry_anchor, 0, 0, weight=0.1
)

solver.against_wall(stove_and_oven_unit[0], walls[3])
solver.align_with(stove_and_oven_unit[0], north_orientation)
solver.distance_constraint(
    stove_and_oven_unit[0], stove_anchor, 0, 0, weight=0.1
)

solver.against_wall(dishwasher[0], walls[3])
solver.align_with(dishwasher[0], north_orientation)
solver.distance_constraint(
    dishwasher[0], dishwasher_anchor, 0, 0, weight=0.1
)

# Long counter on the right wall, facing into the room.
solver.against_wall(kitchen_counter_with_cabinets[0], walls[0])
solver.align_with(kitchen_counter_with_cabinets[0], west_orientation)
solver.distance_constraint(
    kitchen_counter_with_cabinets[0], counter_anchor, 0, 0, weight=0.1
)

# The kitchen island is explicitly constrained against the top wall.
solver.against_wall(kitchen_island[0], walls[1])
solver.align_with(kitchen_island[0], south_orientation)
solver.distance_constraint(
    kitchen_island[0], island_anchor, 0, 0, weight=0.1
)

# Wine rack against the left wall, with its accessible side facing inward.
solver.against_wall(under_counter_wine_rack[0], walls[2])
solver.align_with(under_counter_wine_rack[0], east_orientation)
solver.distance_constraint(
    under_counter_wine_rack[0], wine_rack_anchor, 0, 0, weight=0.1
)

# Keep the microwave supported by the island, against the top wall, and
# aligned with the island. The support constraint is listed first because
# correct countertop elevation is its most important requirement.
solver.on_top_of(microwave_oven[0], kitchen_island[0])
solver.against_wall(microwave_oven[0], walls[1])
solver.align_with(microwave_oven[0], kitchen_island[0])
solver.distance_constraint(
    microwave_oven[0], microwave_anchor, 0, 0, weight=0.1
)

# Preserve useful clearance between the separate kitchen runs.
solver.distance_constraint(
    kitchen_island[0], kitchen_counter_with_cabinets[0],
    2.85, None, weight=10
)
solver.distance_constraint(
    under_counter_wine_rack[0], kitchen_island[0],
    1.00, None, weight=10
)
solver.distance_constraint(
    dishwasher[0], kitchen_counter_with_cabinets[0],
    2.45, None, weight=10
)

solver.constraints = []
refrigerator[0].position = [0.5049999952316284, 0.3800030052661896, 0.9150000214576721]
refrigerator[0].rotation = [0, 0, 1.5707930468851068]
refrigerator[0].optimize = 2
kitchen_counter_with_cabinets[0].position = [3.675002098083496, 2.75, 1.149999976158142]
kitchen_counter_with_cabinets[0].rotation = [0, 0, -3.1415886213365702]
kitchen_counter_with_cabinets[0].optimize = 2
microwave_oven[0].position = [1.2999999523162842, 4.799844741821289, 1.0600000619888306]
microwave_oven[0].rotation = [0, 0, -1.5707885871655447]
microwave_oven[0].optimize = 2
dishwasher[0].position = [3.0, 0.29999974370002747, 0.4350000023841858]
dishwasher[0].rotation = [0, 0, 1.5708019430570366]
dishwasher[0].optimize = 2
floor_pantry_cabinet[0].position = [1.434999942779541, 0.3000026047229767, 1.0499999523162842]
floor_pantry_cabinet[0].rotation = [0, 0, 1.57079303055462]
floor_pantry_cabinet[0].optimize = 2
stove_and_oven_unit[0].position = [2.2899999618530273, 0.3500000834465027, 0.46000000834465027]
stove_and_oven_unit[0].rotation = [0, 0, 1.570793044434261]
stove_and_oven_unit[0].optimize = 2
kitchen_island[0].position = [1.2999999523162842, 4.550001621246338, 0.45500001311302185]
kitchen_island[0].rotation = [0, 0, -1.570793931399169]
kitchen_island[0].optimize = 2
under_counter_wine_rack[0].position = [0.274997740983963, 3.549999952316284, 0.4099999964237213]
under_counter_wine_rack[0].rotation = [0, 0, 5.612973476364829e-06]
under_counter_wine_rack[0].optimize = 2

