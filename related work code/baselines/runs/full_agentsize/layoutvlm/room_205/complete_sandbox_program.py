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
    Wall(corner1=[2.38, 3.31, 0.00], corner2=[0.60, 3.31, 0.00]),
    Wall(corner1=[0.60, 3.31, 0.00], corner2=[0.60, 2.72, 0.00]),
    Wall(corner1=[0.60, 2.72, 0.00], corner2=[0.00, 2.72, 0.00]),
    Wall(corner1=[0.00, 2.72, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.38, 0.00, 0.00]),
    Wall(corner1=[2.38, 0.00, 0.00], corner2=[2.38, 3.31, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
wardrobe = Assets(description="wardrobe", size=[0.55, 0.90, 2.00], placements=[AssetInstance() for _ in range(1)])
chair = Assets(description="chair", size=[0.50, 0.45, 0.85], placements=[AssetInstance() for _ in range(1)])
multifunctional_combination_bed = Assets(description="multifunctional combination bed", size=[1.00, 2.00, 1.80], placements=[AssetInstance() for _ in range(1)])

wardrobe[0].instance_id = 'wardrobe_0'
chair[0].instance_id = 'chair_0'
multifunctional_combination_bed[0].instance_id = 'multifunctional_combination_bed_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

wardrobe[0].position = [0.9197726934340639, 1.08931610030242, 1.0]
wardrobe[0].rotation = [0, 0, 0]
chair[0].position = [0.42531477762091907, 0.7010783375752905, 0.425]
chair[0].rotation = [0, 0, 0]
multifunctional_combination_bed[0].position = [0.43686289278685975, 1.3347246482389086, 0.9]
multifunctional_combination_bed[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.9197726934340639, 1.08931610030242, 1.0]
wardrobe[0].rotation = [0, 0, 0]
chair[0].position = [0.42531477762091907, 0.7010783375752905, 0.425]
chair[0].rotation = [0, 0, 0]
multifunctional_combination_bed[0].position = [0.43686289278685975, 1.3347246482389086, 0.9]
multifunctional_combination_bed[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the bed lengthwise along the right wall. This leaves a broad circulation
# aisle on the left between the room entrance and the rest of the room.
multifunctional_combination_bed[0].position = [1.88, 1.35, 0.90]
multifunctional_combination_bed[0].rotation = [0, 0, radians(180)]

# Put the wardrobe against the upper wall, beyond the inward path from the door.
# Rotating it 90 degrees makes its shallow side project into the room.
wardrobe[0].position = [1.20, 3.035, 1.00]
wardrobe[0].rotation = [0, 0, radians(270)]

# Place the chair in the open area opposite the bed. It remains away from both
# the bottom window and the entrance corridor around y=2.25.
chair[0].position = [0.65, 1.10, 0.425]
chair[0].rotation = [0, 0, radians(11.5)]

# Fixed points keep the selected wall positions from sliding along the walls.
bed_anchor = AssetInstance(position=[1.88, 1.35, 0.90])
wardrobe_anchor = AssetInstance(position=[1.20, 3.035, 1.00])
chair_anchor = AssetInstance(position=[0.65, 1.10, 0.425])

# Orientation targets point the wall furniture into the usable room area.
bed_facing_target = AssetInstance(position=[0.50, 1.35, 0.90])
wardrobe_facing_target = AssetInstance(position=[1.20, 2.20, 1.00])

# The bed must remain against the right wall and face into the room.
solver.against_wall(multifunctional_combination_bed[0], walls[5])
solver.distance_constraint(
    multifunctional_combination_bed[0], bed_anchor,
    min_distance=0, max_distance=0, weight=10
)
solver.point_towards(
    multifunctional_combination_bed[0], bed_facing_target
)

# Keep the wardrobe against the upper wall and oriented toward the room.
solver.against_wall(wardrobe[0], walls[0])
solver.distance_constraint(
    wardrobe[0], wardrobe_anchor,
    min_distance=0, max_distance=0, weight=10
)
solver.point_towards(wardrobe[0], wardrobe_facing_target)

# Anchor the freestanding chair and orient it toward the bed.
solver.distance_constraint(
    chair[0], chair_anchor,
    min_distance=0, max_distance=0, weight=10
)
solver.point_towards(chair[0], multifunctional_combination_bed[0])

# Secondary spacing constraints preserve non-overlap and usable clearance if
# the solver needs to make small feasibility adjustments.
solver.distance_constraint(
    chair[0], multifunctional_combination_bed[0],
    min_distance=1.05, max_distance=1.55, weight=1
)
solver.distance_constraint(
    wardrobe[0], multifunctional_combination_bed[0],
    min_distance=1.25, max_distance=None, weight=1
)
solver.distance_constraint(
    chair[0], wardrobe[0],
    min_distance=1.40, max_distance=None, weight=1
)

solver.constraints = []
wardrobe[0].position = [1.2022192478179932, 3.0300121307373047, 1.0]
wardrobe[0].rotation = [0, 0, -1.5708063552437168]
wardrobe[0].optimize = 2
chair[0].position = [0.6499999761581421, 1.100000023841858, 0.42500001192092896]
chair[0].rotation = [0, 0, 0.21642082630303094]
chair[0].optimize = 2
multifunctional_combination_bed[0].position = [1.880001187324524, 1.350000023841858, 0.8999999761581421]
multifunctional_combination_bed[0].rotation = [0, 0, -3.14159260609554]
multifunctional_combination_bed[0].optimize = 2

