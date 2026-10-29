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
    Wall(corner1=[2.16, 1.70, 0.00], corner2=[2.76, 1.70, 0.00]),
    Wall(corner1=[2.76, 1.70, 0.00], corner2=[2.76, 4.82, 0.00]),
    Wall(corner1=[2.76, 4.82, 0.00], corner2=[0.00, 4.82, 0.00]),
    Wall(corner1=[0.00, 4.82, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.76, 0.00, 0.00]),
    Wall(corner1=[2.76, 0.00, 0.00], corner2=[2.76, 1.46, 0.00]),
    Wall(corner1=[2.76, 1.46, 0.00], corner2=[2.16, 1.46, 0.00]),
    Wall(corner1=[2.16, 1.46, 0.00], corner2=[2.16, 1.70, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bed = Assets(description="bed", size=[2.00, 1.35, 0.55], placements=[AssetInstance() for _ in range(1)])
chair = Assets(description="chair", size=[0.60, 0.60, 0.95], placements=[AssetInstance() for _ in range(1)])
bookcase = Assets(description="bookcase", size=[0.30, 0.70, 1.80], placements=[AssetInstance() for _ in range(1)])
fitness_equipment = Assets(description="fitness equipment", size=[0.25, 0.80, 2.20], placements=[AssetInstance() for _ in range(1)])
nightstand = Assets(description="nightstand", size=[0.35, 0.40, 0.50], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.60, 1.00, 2.10], placements=[AssetInstance() for _ in range(1)])

bed[0].instance_id = 'bed_0'
chair[0].instance_id = 'chair_0'
bookcase[0].instance_id = 'bookcase_0'
fitness_equipment[0].instance_id = 'fitness_equipment_0'
nightstand[0].instance_id = 'nightstand_0'
wardrobe[0].instance_id = 'wardrobe_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

bed[0].position = [0.23430274158814757, 4.223269973194579, 0.275]
bed[0].rotation = [0, 0, 0]
chair[0].position = [2.462228204200122, 1.7570705931229487, 0.475]
chair[0].rotation = [0, 0, 0]
bookcase[0].position = [1.9552268212712511, 2.0886801739697, 0.9]
bookcase[0].rotation = [0, 0, 0]
fitness_equipment[0].position = [0.4224589541077316, 0.1115548042173503, 1.1]
fitness_equipment[0].rotation = [0, 0, 0]
nightstand[0].position = [0.3024386111039629, 2.067663600061611, 0.25]
nightstand[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.42362281864648244, 3.5801102843906114, 1.05]
wardrobe[0].rotation = [0, 0, 0]
bed[0].position = [0.23430274158814757, 4.223269973194579, 0.275]
bed[0].rotation = [0, 0, 0]
chair[0].position = [2.462228204200122, 1.7570705931229487, 0.475]
chair[0].rotation = [0, 0, 0]
bookcase[0].position = [1.9552268212712511, 2.0886801739697, 0.9]
bookcase[0].rotation = [0, 0, 0]
fitness_equipment[0].position = [0.4224589541077316, 0.1115548042173503, 1.1]
fitness_equipment[0].rotation = [0, 0, 0]
nightstand[0].position = [0.3024386111039629, 2.067663600061611, 0.25]
nightstand[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.42362281864648244, 3.5801102843906114, 1.05]
wardrobe[0].rotation = [0, 0, 0]

solver.constraints = []

# Keep the entrance at the upper-left clear. The bed occupies the lower-left
# zone, with an accessible aisle along its right side. All z values are
# bounding-box center heights.
bed[0].position = [0.725, 1.30, 0.275]
bed[0].rotation = [0, 0, radians(90)]

nightstand[0].position = [1.65, 0.50, 0.25]
nightstand[0].rotation = [0, 0, radians(90)]

# A chair beside the window faces into the room without blocking the bedside.
chair[0].position = [2.35, 0.60, 0.475]
chair[0].rotation = [0, 0, radians(180)]

# Tall storage stays away from the window and the entrance.
bookcase[0].position = [2.61, 2.65, 0.90]
bookcase[0].rotation = [0, 0, radians(180)]

wardrobe[0].position = [2.46, 4.10, 1.05]
wardrobe[0].rotation = [0, 0, radians(180)]

# Wall-mounted/profile fitness equipment faces east into an open exercise area.
fitness_equipment[0].position = [0.125, 3.05, 1.10]
fitness_equipment[0].rotation = [0, 0, 0]

# Prioritize the required wall attachment and inward-facing storage fronts.
solver.against_wall(fitness_equipment[0], walls[3])
solver.against_wall(bookcase[0], walls[1])
solver.against_wall(wardrobe[0], walls[1])

# Fixed reference poses preserve the chosen functional zones. Small positional
# tolerances allow adjustment while retaining separation from other furniture,
# the boundary notch, and the entrance approach.
layout_specs = [
    (bed[0], [0.725, 1.30, 0.275], 90, 0.04),
    (nightstand[0], [1.65, 0.50, 0.25], 90, 0.04),
    (chair[0], [2.35, 0.60, 0.475], 180, 0.04),
    (bookcase[0], [2.61, 2.65, 0.90], 180, 0.04),
    (wardrobe[0], [2.46, 4.10, 1.05], 180, 0.04),
    (fitness_equipment[0], [0.125, 3.05, 1.10], 0, 0.04),
]

for instance, target_position, facing_degrees, tolerance in layout_specs:
    reference_pose = AssetInstance(
        position=target_position,
        rotation=[0, 0, 0],
    )
    solver.distance_constraint(
        instance, reference_pose, 0, tolerance, weight=10
    )
    solver.align_with(instance, reference_pose, angle=facing_degrees)

# Retain the bedside relationship without pulling the nightstand onto the bed.
solver.distance_constraint(nightstand[0], bed[0], 1.15, 1.35)

# Explicitly preserve an unobstructed approach immediately inside the door.
# References use each object's own center height so these are horizontal distances.
for instance, _, _, _ in layout_specs:
    entrance_reference = AssetInstance(
        position=[0.47, 4.82, instance.position[2]]
    )
    solver.distance_constraint(
        instance, entrance_reference, 1.25, None, weight=10
    )

# Every listed item is floor-standing; no on_top_of constraint is needed.

solver.constraints = []
fitness_equipment[0].position = [0.1249999925494194, 3.049999952316284, 1.100000023841858]
fitness_equipment[0].rotation = [0, 0, 6.345402447795563e-08]
fitness_equipment[0].optimize = 2
bookcase[0].position = [2.6100006103515625, 2.6500000953674316, 0.8999999761581421]
bookcase[0].rotation = [0, 0, -3.141592613768004]
bookcase[0].optimize = 2
wardrobe[0].position = [2.4600000381469727, 4.099999904632568, 1.0499999523162842]
wardrobe[0].rotation = [0, 0, -3.141592586325971]
wardrobe[0].optimize = 2
chair[0].position = [2.3499999046325684, 0.6000000238418579, 0.4749999940395355]
chair[0].rotation = [0, 0, -3.1290262823329655]
chair[0].optimize = 2
bed[0].position = [0.7250000238418579, 1.2999999523162842, 0.2750000059604645]
bed[0].rotation = [0, 0, 1.586504290712113]
bed[0].optimize = 2
nightstand[0].position = [1.649999976158142, 0.5, 0.25]
nightstand[0].rotation = [0, 0, 1.586504290712113]
nightstand[0].optimize = 2

