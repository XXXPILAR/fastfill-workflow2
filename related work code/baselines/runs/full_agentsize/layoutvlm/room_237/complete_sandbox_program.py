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
    Wall(corner1=[0.00, 3.95, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.99, 0.00, 0.00]),
    Wall(corner1=[3.99, 0.00, 0.00], corner2=[3.99, 2.82, 0.00]),
    Wall(corner1=[3.99, 2.82, 0.00], corner2=[5.81, 2.82, 0.00]),
    Wall(corner1=[5.81, 2.82, 0.00], corner2=[5.81, 3.95, 0.00]),
    Wall(corner1=[5.81, 3.95, 0.00], corner2=[0.00, 3.95, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
tv_cabinet = Assets(description="tv cabinet", size=[0.42, 1.80, 0.55], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.62, 2.40, 2.40], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.10, 1.80, 0.60], placements=[AssetInstance() for _ in range(1)])
nightstand_A = Assets(description="nightstand", size=[0.42, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
nightstand_B = Assets(description="nightstand", size=[0.42, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])

tv_cabinet[0].instance_id = 'tv_cabinet_0'
wardrobe[0].instance_id = 'wardrobe_0'
bed[0].instance_id = 'bed_0'
nightstand_A[0].instance_id = 'nightstand_A_0'
nightstand_B[0].instance_id = 'nightstand_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

tv_cabinet[0].position = [1.2641528807326021, 3.260412859819414, 0.275]
tv_cabinet[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.041512652141363036, 0.11760334803133453, 1.2]
wardrobe[0].rotation = [0, 0, 0]
bed[0].position = [3.5469047735240866, 2.0624086596993996, 0.3]
bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [2.2894167002085117, 0.8537495478434499, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
nightstand_B[0].position = [0.09969089643030209, 3.60116891155205, 0.275]
nightstand_B[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [1.2641528807326021, 3.260412859819414, 0.275]
tv_cabinet[0].rotation = [0, 0, 0]
wardrobe[0].position = [0.041512652141363036, 0.11760334803133453, 1.2]
wardrobe[0].rotation = [0, 0, 0]
bed[0].position = [3.5469047735240866, 2.0624086596993996, 0.3]
bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [2.2894167002085117, 0.8537495478434499, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
nightstand_B[0].position = [0.09969089643030209, 3.60116891155205, 0.275]
nightstand_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the bed along the uninterrupted upper wall. Its foot faces south
# toward the TV, leaving the room center and both door approaches unobstructed.
bed[0].position = [2.10, 2.90, bed.size[2] / 2]
bed[0].rotation = [0, 0, radians(-90)]

# Center the TV cabinet opposite the bed on the lower wall.
tv_cabinet[0].position = [2.10, tv_cabinet.size[0] / 2, tv_cabinet.size[2] / 2]
tv_cabinet[0].rotation = [0, 0, radians(90)]

# Place the wardrobe against the lower portion of the right wall. It remains
# below the doorway at y=2.82 and opens toward the clear interior of the room.
wardrobe[0].position = [
    3.99 - wardrobe.size[0] / 2,
    1.25,
    wardrobe.size[2] / 2,
]
wardrobe[0].rotation = [0, 0, radians(180)]

# Flank the head of the bed with one nightstand on each side.
# Their rotated depth is 0.42 m, so their centers sit 0.21 m from the top wall.
nightstand_A[0].position = [0.90, 3.95 - nightstand_A.size[0] / 2, nightstand_A.size[2] / 2]
nightstand_A[0].rotation = [0, 0, radians(-90)]

nightstand_B[0].position = [3.30, 3.95 - nightstand_B.size[0] / 2, nightstand_B.size[2] / 2]
nightstand_B[0].rotation = [0, 0, radians(-90)]


# Fixed reference points keep furniture in the intended sections of the room
# if the constraint solver makes small feasibility adjustments.
bed_anchor = AssetInstance(position=[2.10, 2.90, bed.size[2] / 2])
tv_anchor = AssetInstance(position=[2.10, 0.21, tv_cabinet.size[2] / 2])
wardrobe_anchor = AssetInstance(position=[3.68, 1.25, wardrobe.size[2] / 2])
nightstand_A_anchor = AssetInstance(position=[0.90, 3.74, nightstand_A.size[2] / 2])
nightstand_B_anchor = AssetInstance(position=[3.30, 3.74, nightstand_B.size[2] / 2])
room_center = AssetInstance(position=[2.00, 1.90, wardrobe.size[2] / 2])

# Primary semantic relationship: the bed and TV cabinet face one another.
solver.point_towards(bed[0], tv_cabinet[0])
solver.point_towards(tv_cabinet[0], bed[0])

# Keep the bed and TV cabinet against their respective opposing walls.
solver.against_wall(bed[0], walls[5])
solver.against_wall(tv_cabinet[0], walls[1])
solver.distance_constraint(bed[0], bed_anchor, 0, 0, weight=10)
solver.distance_constraint(tv_cabinet[0], tv_anchor, 0, 0, weight=10)

# Preserve a practical viewing separation between the bed and TV cabinet.
solver.distance_constraint(bed[0], tv_cabinet[0], 2.60, 2.80, weight=10)
solver.distance_constraint(tv_cabinet[0], bed[0], 2.60, 2.80, weight=10)

# Keep the wardrobe against the lower right wall and facing into the room.
solver.against_wall(wardrobe[0], walls[2])
solver.point_towards(wardrobe[0], room_center)
solver.distance_constraint(wardrobe[0], wardrobe_anchor, 0, 0, weight=10)

# Keep both nightstands at the head wall, parallel to the bed, and positioned
# symmetrically on its two sides without overlapping its footprint.
solver.against_wall(nightstand_A[0], walls[5])
solver.align_with(nightstand_A[0], bed[0])
solver.distance_constraint(nightstand_A[0], nightstand_A_anchor, 0, 0, weight=10)
solver.distance_constraint(nightstand_A[0], bed[0], 1.42, 1.52, weight=5)

solver.against_wall(nightstand_B[0], walls[5])
solver.align_with(nightstand_B[0], bed[0])
solver.distance_constraint(nightstand_B[0], nightstand_B_anchor, 0, 0, weight=10)
solver.distance_constraint(nightstand_B[0], bed[0], 1.42, 1.52, weight=5)

solver.constraints = []
bed[0].position = [2.0999999046325684, 2.8355729579925537, 0.30000001192092896]
bed[0].rotation = [0, 0, 1.5707964489306923]
bed[0].optimize = 2
nightstand_A[0].position = [0.8999999761581421, 3.7385408878326416, 0.2750000059604645]
nightstand_A[0].rotation = [0, 0, -1.5707962831086673]
nightstand_A[0].optimize = 2
nightstand_B[0].position = [3.299999952316284, 3.7385408878326416, 0.2750000059604645]
nightstand_B[0].rotation = [0, 0, -1.5707962831086641]
nightstand_B[0].optimize = 2
tv_cabinet[0].position = [2.0999999046325684, 0.21122704446315765, 0.2750000059604645]
tv_cabinet[0].rotation = [0, 0, 1.5707963597786976]
tv_cabinet[0].optimize = 2
wardrobe[0].position = [3.6752607822418213, 1.25, 1.2000000476837158]
wardrobe[0].rotation = [0, 0, -3.1415926076898826]
wardrobe[0].optimize = 2

