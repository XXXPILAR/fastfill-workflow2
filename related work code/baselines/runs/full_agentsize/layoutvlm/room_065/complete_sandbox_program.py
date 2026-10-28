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
    Wall(corner1=[0.00, 6.84, 0.00], corner2=[0.00, 0.04, 0.00]),
    Wall(corner1=[0.00, 0.04, 0.00], corner2=[0.04, 0.00, 0.00]),
    Wall(corner1=[0.04, 0.00, 0.00], corner2=[3.55, 0.00, 0.00]),
    Wall(corner1=[3.55, 0.00, 0.00], corner2=[3.59, 0.04, 0.00]),
    Wall(corner1=[3.59, 0.04, 0.00], corner2=[3.59, 5.35, 0.00]),
    Wall(corner1=[3.59, 5.35, 0.00], corner2=[3.55, 5.39, 0.00]),
    Wall(corner1=[3.55, 5.39, 0.00], corner2=[1.29, 6.88, 0.00]),
    Wall(corner1=[1.29, 6.88, 0.00], corner2=[0.04, 6.88, 0.00]),
    Wall(corner1=[0.04, 6.88, 0.00], corner2=[0.00, 6.84, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
cabinet = Assets(description="cabinet", size=[0.45, 0.80, 0.90], placements=[AssetInstance() for _ in range(1)])
bag = Assets(description="bag", size=[0.20, 0.40, 0.45], placements=[AssetInstance() for _ in range(1)])
basket = Assets(description="basket", size=[0.35, 0.45, 0.50], placements=[AssetInstance() for _ in range(1)])
bathtub = Assets(description="bathtub", size=[0.75, 1.70, 0.58], placements=[AssetInstance() for _ in range(1)])
toilet = Assets(description="toilet", size=[0.70, 0.38, 0.78], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.00, 1.60, 0.55], placements=[AssetInstance() for _ in range(1)])

cabinet[0].instance_id = 'cabinet_0'
bag[0].instance_id = 'bag_0'
basket[0].instance_id = 'basket_0'
bathtub[0].instance_id = 'bathtub_0'
toilet[0].instance_id = 'toilet_0'
bed[0].instance_id = 'bed_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'
walls[8].instance_id = 'walls_8'

cabinet[0].position = [1.5334245920968343, 2.5888428864100503, 0.45]
cabinet[0].rotation = [0, 0, 0]
bag[0].position = [3.5572111597922533, 2.1142568565176667, 0.225]
bag[0].rotation = [0, 0, 0]
basket[0].position = [0.7029934955880361, 3.1098651787435427, 0.25]
basket[0].rotation = [0, 0, 0]
bathtub[0].position = [1.8546258914838658, 4.661379715034274, 0.29]
bathtub[0].rotation = [0, 0, 0]
toilet[0].position = [0.6991510109432642, 3.887988858282086, 0.39]
toilet[0].rotation = [0, 0, 0]
bed[0].position = [0.924673813107119, 3.9550996316101656, 0.275]
bed[0].rotation = [0, 0, 0]
cabinet[0].position = [1.5334245920968343, 2.5888428864100503, 0.45]
cabinet[0].rotation = [0, 0, 0]
bag[0].position = [3.5572111597922533, 2.1142568565176667, 0.225]
bag[0].rotation = [0, 0, 0]
basket[0].position = [0.7029934955880361, 3.1098651787435427, 0.25]
basket[0].rotation = [0, 0, 0]
bathtub[0].position = [1.8546258914838658, 4.661379715034274, 0.29]
bathtub[0].rotation = [0, 0, 0]
toilet[0].position = [0.6991510109432642, 3.887988858282086, 0.39]
toilet[0].rotation = [0, 0, 0]
bed[0].position = [0.924673813107119, 3.9550996316101656, 0.275]
bed[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the bed in the lower-left portion of the room, leaving a clear
# circulation aisle along its right side. Its front points toward the toilet.
bed[0].position = [1.15, 1.25, bed.size[2] / 2]
bed[0].rotation = [0, 0, radians(100.4)]

# Wall-mounted furniture is distributed around the perimeter so that the
# central part of the room remains usable.
cabinet[0].position = [cabinet.size[0] / 2, 3.30, cabinet.size[2] / 2]
cabinet[0].rotation = [0, 0, radians(0)]

basket[0].position = [3.59 - basket.size[0] / 2, 2.65, basket.size[2] / 2]
basket[0].rotation = [0, 0, radians(180)]

bathtub[0].position = [3.59 - bathtub.size[0] / 2, 4.35, bathtub.size[2] / 2]
bathtub[0].rotation = [0, 0, radians(180)]

# Put the toilet against the upper part of the left wall, clear of the bed
# and bathtub. It faces into the room.
toilet[0].position = [toilet.size[0] / 2, 5.60, toilet.size[2] / 2]
toilet[0].rotation = [0, 0, radians(0)]

# Initially place the bag immediately beside the toilet. Their bounding boxes
# touch without overlapping; the high-priority proximity constraint below
# expresses the requested maximum 0.10 m semantic distance.
bag[0].position = [
    toilet[0].position[0] + toilet.size[0] / 2 + bag.size[0] / 2,
    5.60,
    bag.size[2] / 2,
]
bag[0].rotation = [0, 0, radians(180)]


# Fixed points preserve the intended functional zones while allowing the
# solver to make small feasibility adjustments.
bed_anchor = AssetInstance(position=[1.15, 1.25, bed.size[2] / 2])
cabinet_anchor = AssetInstance(
    position=[cabinet.size[0] / 2, 3.30, cabinet.size[2] / 2]
)
basket_anchor = AssetInstance(
    position=[3.59 - basket.size[0] / 2, 2.65, basket.size[2] / 2]
)
bathtub_anchor = AssetInstance(
    position=[3.59 - bathtub.size[0] / 2, 4.35, bathtub.size[2] / 2]
)
toilet_anchor = AssetInstance(
    position=[toilet.size[0] / 2, 5.60, toilet.size[2] / 2]
)

cabinet_facing_point = AssetInstance(position=[1.50, 3.30, cabinet.size[2] / 2])
basket_facing_point = AssetInstance(position=[2.00, 2.65, basket.size[2] / 2])
bathtub_facing_point = AssetInstance(position=[2.00, 4.35, bathtub.size[2] / 2])
toilet_facing_point = AssetInstance(position=[1.50, 5.60, toilet.size[2] / 2])


# Highest-priority layout criteria: keep the bag very close to the toilet,
# and make the bed face the toilet.
solver.distance_constraint(bag[0], toilet[0], None, 0.10, weight=10)
solver.point_towards(bed[0], toilet[0])

# Keep the bed in its open, collision-free lower-room zone.
solver.distance_constraint(bed[0], bed_anchor, 0, 0, weight=10)

# Keep the cabinet against the left wall and facing into the room.
solver.distance_constraint(cabinet[0], cabinet_anchor, 0, 0, weight=10)
solver.against_wall(cabinet[0], walls[0])
solver.point_towards(cabinet[0], cabinet_facing_point)

# Keep the basket against the right wall, below and clear of the bathtub.
solver.distance_constraint(basket[0], basket_anchor, 0, 0, weight=10)
solver.against_wall(basket[0], walls[4])
solver.point_towards(basket[0], basket_facing_point)

# Orient the bathtub lengthwise along the right wall, facing into the room.
solver.distance_constraint(bathtub[0], bathtub_anchor, 0, 0, weight=10)
solver.against_wall(bathtub[0], walls[4])
solver.point_towards(bathtub[0], bathtub_facing_point)

# Keep the toilet against the left wall and facing toward the room interior.
solver.distance_constraint(toilet[0], toilet_anchor, 0, 0, weight=10)
solver.against_wall(toilet[0], walls[0])
solver.point_towards(toilet[0], toilet_facing_point)

# The bag remains oriented toward the toilet in addition to its required
# position-based proximity constraint.
solver.point_towards(bag[0], toilet[0])

solver.constraints = []
basket[0].position = [3.419171094894409, 2.6500000953674316, 0.25]
basket[0].rotation = [0, 0, -3.137375752273234]
basket[0].optimize = 2
cabinet[0].position = [0.22428588569164276, 3.299999952316284, 0.44999998807907104]
cabinet[0].rotation = [0, 0, 0.004217324587363289]
cabinet[0].optimize = 2
bed[0].position = [1.149999976158142, 1.25, 0.2750000059604645]
bed[0].rotation = [0, 0, 1.7617353445927721]
bed[0].optimize = 2
toilet[0].position = [0.35041332244873047, 5.599999904632568, 0.38999998569488525]
toilet[0].rotation = [0, 0, 0.002654916367959856]
toilet[0].optimize = 2
bag[0].position = [0.800000011920929, 5.599999904632568, 0.22499999403953552]
bag[0].rotation = [0, 0, -3.1321678761290697]
bag[0].optimize = 2
bathtub[0].position = [3.2191879749298096, 4.349999904632568, 0.28999999165534973]
bathtub[0].rotation = [0, 0, -3.13737376947543]
bathtub[0].optimize = 2

