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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[6.88, 0.00, 0.00]),
    Wall(corner1=[6.88, 0.00, 0.00], corner2=[6.88, 6.94, 0.00]),
    Wall(corner1=[6.88, 6.94, 0.00], corner2=[0.00, 6.94, 0.00]),
    Wall(corner1=[0.00, 6.94, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
cabinet_A = Assets(description="A tall white cabinet with a wooden top, designed for storage or display purposes.", size=[0.50, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
box = Assets(description="A rectangular storage basket with a woven texture, featuring two circular handles on its sides.", size=[0.40, 0.60, 0.35], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="A simple cabinet with a flat top and two doors, designed for storage purposes.", size=[0.60, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
basket_A = Assets(description="A cylindrical woven basket with a tight, intricate weave pattern. It has a uniform texture and appears sturdy, suitable for storage or decorative purposes.", size=[0.45, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
basket_B = Assets(description="A rectangular wire storage basket with a grid pattern, designed for holding various items.", size=[0.35, 0.45, 0.25], placements=[AssetInstance() for _ in range(1)])
washing_machine = Assets(description="A modern, freestanding dishwasher with a sleek design, featuring control panels and a digital display on the upper section.", size=[0.65, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
dryer = Assets(description="A white washing machine with a circular door and control panel at the top.", size=[0.65, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])

cabinet_A[0].instance_id = 'cabinet_A_0'
box[0].instance_id = 'box_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
basket_A[0].instance_id = 'basket_A_0'
basket_B[0].instance_id = 'basket_B_0'
washing_machine[0].instance_id = 'washing_machine_0'
dryer[0].instance_id = 'dryer_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

cabinet_A[0].position = [5.01925474402136, 2.002236501620235, 0.9]
cabinet_A[0].rotation = [0, 0, 0]
box[0].position = [2.1875293309529895, 4.535851377046061, 0.175]
box[0].rotation = [0, 0, 0]
cabinet_B[0].position = [2.071468199369598, 4.461759743730159, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
basket_A[0].position = [2.665551707015173, 5.958283974797189, 0.275]
basket_A[0].rotation = [0, 0, 0]
basket_B[0].position = [5.662025905389141, 6.266212638875459, 0.125]
basket_B[0].rotation = [0, 0, 0]
washing_machine[0].position = [0.27005521813202765, 4.124535326996562, 0.425]
washing_machine[0].rotation = [0, 0, 0]
dryer[0].position = [0.7047740678046951, 6.328711718198768, 0.425]
dryer[0].rotation = [0, 0, 0]
cabinet_A[0].position = [5.01925474402136, 2.002236501620235, 0.9]
cabinet_A[0].rotation = [0, 0, 0]
box[0].position = [2.1875293309529895, 4.535851377046061, 0.175]
box[0].rotation = [0, 0, 0]
cabinet_B[0].position = [2.071468199369598, 4.461759743730159, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
basket_A[0].position = [2.665551707015173, 5.958283974797189, 0.275]
basket_A[0].rotation = [0, 0, 0]
basket_B[0].position = [5.662025905389141, 6.266212638875459, 0.125]
basket_B[0].rotation = [0, 0, 0]
washing_machine[0].position = [0.27005521813202765, 4.124535326996562, 0.425]
washing_machine[0].rotation = [0, 0, 0]
dryer[0].position = [0.7047740678046951, 6.328711718198768, 0.425]
dryer[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the tall storage units and laundry appliances in a compact row
# along the north wall. They face into the room, leaving the central floor
# area clear and providing unobstructed access to their fronts.
cabinet_A[0].position = [0.50, 6.69, 0.90]
cabinet_A[0].rotation = [0, 0, radians(-90)]

washing_machine[0].position = [1.30, 6.615, 0.425]
washing_machine[0].rotation = [0, 0, radians(-90)]

dryer[0].position = [2.00, 6.615, 0.425]
dryer[0].rotation = [0, 0, radians(-90)]

cabinet_B[0].position = [3.00, 6.64, 0.45]
cabinet_B[0].rotation = [0, 0, radians(-90)]

# Keep the cylindrical floor basket beside the storage row, with a small
# clearance from cabinet_B.
basket_A[0].position = [4.00, 6.715, 0.275]
basket_A[0].rotation = [0, 0, radians(-90)]

# Place the smaller containers on suitable supporting surfaces.
box[0].position = [3.00, 6.64, 1.075]
box[0].rotation = [0, 0, radians(-90)]

basket_B[0].position = [1.30, 6.615, 0.975]
basket_B[0].rotation = [0, 0, radians(-90)]


# A point near the room center provides a consistent inward-facing direction.
room_center = AssetInstance(position=[3.44, 3.47, 0.50])

# Wall-backed floor assets: wall contact is the primary positional requirement.
solver.against_wall(cabinet_A[0], walls[2])
solver.point_towards(cabinet_A[0], room_center)

solver.against_wall(washing_machine[0], walls[2])
solver.point_towards(washing_machine[0], room_center)

solver.against_wall(dryer[0], walls[2])
solver.point_towards(dryer[0], room_center)

solver.against_wall(cabinet_B[0], walls[2])
solver.point_towards(cabinet_B[0], room_center)

solver.against_wall(basket_A[0], walls[2])
solver.point_towards(basket_A[0], room_center)

# Preserve practical side-by-side spacing within the north-wall row.
solver.distance_constraint(
    washing_machine[0], cabinet_A[0], 0.80, 0.80, weight=10
)
solver.distance_constraint(
    dryer[0], washing_machine[0], 0.70, 0.70, weight=10
)
solver.distance_constraint(
    cabinet_B[0], dryer[0], 1.00, 1.00, weight=10
)
solver.distance_constraint(
    basket_A[0], cabinet_B[0], 1.00, 1.00, weight=10
)

# The box is centered on cabinet_B. Its center-to-center vertical separation is
# 0.45 + 0.35 / 2 = 0.625 meters.
solver.on_top_of(box[0], cabinet_B[0])
solver.distance_constraint(box[0], cabinet_B[0], 0.625, 0.625, weight=10)
solver.align_with(box[0], cabinet_B[0])

# The wire basket is centered on the washing machine. Its center-to-center
# vertical separation is 0.425 + 0.25 / 2 = 0.55 meters.
solver.on_top_of(basket_B[0], washing_machine[0])
solver.distance_constraint(
    basket_B[0], washing_machine[0], 0.55, 0.55, weight=10
)
solver.align_with(basket_B[0], washing_machine[0])

solver.constraints = []
cabinet_B[0].position = [3.0, 6.629060745239258, 0.44999998807907104]
cabinet_B[0].rotation = [0, 0, -1.5716206547676006]
cabinet_B[0].optimize = 2
basket_A[0].position = [4.0, 6.708957195281982, 0.2750000059604645]
basket_A[0].rotation = [0, 0, -1.5665871969664418]
basket_A[0].optimize = 2
washing_machine[0].position = [1.2999999523162842, 6.61330509185791, 0.42500001192092896]
washing_machine[0].rotation = [0, 0, -1.5716036164627707]
washing_machine[0].optimize = 2
cabinet_A[0].position = [0.5, 6.687347888946533, 0.8999999761581421]
cabinet_A[0].rotation = [0, 0, -1.566576501650894]
cabinet_A[0].optimize = 2
basket_B[0].position = [1.2999999523162842, 6.719668388366699, 0.9750000238418579]
basket_B[0].rotation = [0, 0, -1.5965302465538989]
basket_B[0].optimize = 2
box[0].position = [3.0, 6.727481842041016, 1.0749999284744263]
box[0].rotation = [0, 0, -1.5965437599711791]
box[0].optimize = 2
dryer[0].position = [2.0, 6.6089887619018555, 0.42500001192092896]
dryer[0].rotation = [0, 0, -1.564658340256513]
dryer[0].optimize = 2

