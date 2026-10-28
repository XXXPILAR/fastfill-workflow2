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
    Wall(corner1=[2.50, 0.00, 0.00], corner2=[2.50, 3.50, 0.00]),
    Wall(corner1=[2.50, 3.50, 0.00], corner2=[0.00, 3.50, 0.00]),
    Wall(corner1=[0.00, 3.50, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.50, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bathtub = Assets(description="freestanding modern bathtub with smooth curves in white", size=[0.80, 1.70, 0.60], placements=[AssetInstance() for _ in range(1)])
toilet = Assets(description="modern white ceramic toilet with concealed cistern", size=[0.68, 0.38, 0.80], placements=[AssetInstance() for _ in range(1)])
freestanding_towel_rack = Assets(description="modern freestanding metal towel rack with multiple bars", size=[0.30, 0.65, 0.90], placements=[AssetInstance() for _ in range(1)])
storage_cabinet = Assets(description="tall slim wooden storage cabinet for bathroom essentials", size=[0.35, 0.40, 1.80], placements=[AssetInstance() for _ in range(1)])
shower_enclosure = Assets(description="modern glass shower enclosure with chrome fixtures", size=[0.90, 0.90, 2.00], placements=[AssetInstance() for _ in range(1)])

bathtub[0].instance_id = 'bathtub_0'
toilet[0].instance_id = 'toilet_0'
freestanding_towel_rack[0].instance_id = 'freestanding_towel_rack_0'
storage_cabinet[0].instance_id = 'storage_cabinet_0'
shower_enclosure[0].instance_id = 'shower_enclosure_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

bathtub[0].position = [0.5803744586973764, 2.4876474824361106, 0.3]
bathtub[0].rotation = [0, 0, 0]
toilet[0].position = [0.39249936076597436, 3.39701718913279, 0.4]
toilet[0].rotation = [0, 0, 0]
freestanding_towel_rack[0].position = [1.8945273475250475, 3.125417820790715, 0.45]
freestanding_towel_rack[0].rotation = [0, 0, 0]
storage_cabinet[0].position = [0.054385141981258545, 0.49677979861822436, 0.9]
storage_cabinet[0].rotation = [0, 0, 0]
shower_enclosure[0].position = [1.3206224512484597, 1.264861044491302, 1.0]
shower_enclosure[0].rotation = [0, 0, 0]
bathtub[0].position = [0.5803744586973764, 2.4876474824361106, 0.3]
bathtub[0].rotation = [0, 0, 0]
toilet[0].position = [0.39249936076597436, 3.39701718913279, 0.4]
toilet[0].rotation = [0, 0, 0]
freestanding_towel_rack[0].position = [1.8945273475250475, 3.125417820790715, 0.45]
freestanding_towel_rack[0].rotation = [0, 0, 0]
storage_cabinet[0].position = [0.054385141981258545, 0.49677979861822436, 0.9]
storage_cabinet[0].rotation = [0, 0, 0]
shower_enclosure[0].position = [1.3206224512484597, 1.264861044491302, 1.0]
shower_enclosure[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the main fixtures on opposite walls, leaving a clear central aisle.
# All z coordinates place the assets directly on the floor.
bathtub[0].position = [0.40, 2.40, 0.30]
bathtub[0].rotation = [0, 0, radians(0)]

toilet[0].position = [2.16, 2.40, 0.40]
toilet[0].rotation = [0, 0, radians(180)]

# Keep the smaller accessories along the lower walls, away from the main fixtures.
freestanding_towel_rack[0].position = [0.15, 0.65, 0.45]
freestanding_towel_rack[0].rotation = [0, 0, radians(0)]

storage_cabinet[0].position = [1.25, 0.20, 0.90]
storage_cabinet[0].rotation = [0, 0, radians(0)]

# The square shower occupies the lower-right corner.
shower_enclosure[0].position = [2.05, 0.45, 1.00]
shower_enclosure[0].rotation = [0, 0, radians(0)]


# Wall constraints are listed first because keeping every fixture inside the room
# and maintaining the required wall placement are the highest priorities.
solver.against_wall(bathtub[0], walls[2])
solver.against_wall(toilet[0], walls[0])
solver.against_wall(freestanding_towel_rack[0], walls[2])
solver.against_wall(storage_cabinet[0], walls[3])
solver.against_wall(shower_enclosure[0], walls[0])
solver.against_wall(shower_enclosure[0], walls[3])

# Preserve the selected locations along their respective walls.
bathtub_anchor = AssetInstance(position=[0.40, 2.40, 0.30])
toilet_anchor = AssetInstance(position=[2.16, 2.40, 0.40])
towel_rack_anchor = AssetInstance(position=[0.15, 0.65, 0.45])
cabinet_anchor = AssetInstance(position=[1.25, 0.20, 0.90])
shower_anchor = AssetInstance(position=[2.05, 0.45, 1.00])

solver.distance_constraint(
    bathtub[0], bathtub_anchor, 0.0, 0.0, weight=10
)
solver.distance_constraint(
    toilet[0], toilet_anchor, 0.0, 0.0, weight=10
)
solver.distance_constraint(
    freestanding_towel_rack[0], towel_rack_anchor, 0.0, 0.0, weight=10
)
solver.distance_constraint(
    storage_cabinet[0], cabinet_anchor, 0.0, 0.0, weight=10
)
solver.distance_constraint(
    shower_enclosure[0], shower_anchor, 0.0, 0.0, weight=10
)

# The toilet faces directly across the room toward the bathtub, as required.
# The bathtub faces back toward the toilet for a coherent opposing arrangement.
solver.point_towards(toilet[0], bathtub[0])
solver.point_towards(bathtub[0], toilet[0])

# Keep the remaining assets parallel to the bathtub and room axes.
solver.align_with(freestanding_towel_rack[0], bathtub[0])
solver.align_with(storage_cabinet[0], bathtub[0])
solver.align_with(shower_enclosure[0], bathtub[0])

# Maintain useful separation between neighboring zones if feasibility adjustment
# moves assets away from their initial coordinates.
solver.distance_constraint(
    freestanding_towel_rack[0], bathtub[0], 1.60, None, weight=1
)
solver.distance_constraint(
    storage_cabinet[0], shower_enclosure[0], 0.75, None, weight=1
)
solver.distance_constraint(
    shower_enclosure[0], toilet[0], 1.25, None, weight=1
)

solver.constraints = []
bathtub[0].position = [0.4000000059604645, 2.4000000953674316, 0.30000001192092896]
bathtub[0].rotation = [0, 0, 3.34454647913123e-08]
bathtub[0].optimize = 2
freestanding_towel_rack[0].position = [0.14999999105930328, 0.6499999761581421, 0.44999998807907104]
freestanding_towel_rack[0].rotation = [0, 0, 4.1850938377090845e-08]
freestanding_towel_rack[0].optimize = 2
toilet[0].position = [2.1600005626678467, 2.4000000953674316, 0.4000000059604645]
toilet[0].rotation = [0, 0, -3.141592609961752]
toilet[0].optimize = 2
shower_enclosure[0].position = [2.035698175430298, 0.4499998688697815, 1.0]
shower_enclosure[0].rotation = [0, 0, 1.5707963484441898]
shower_enclosure[0].optimize = 2
storage_cabinet[0].position = [1.25, 0.17500001192092896, 0.8999999761581421]
storage_cabinet[0].rotation = [0, 0, 1.5707963310246142]
storage_cabinet[0].optimize = 2

