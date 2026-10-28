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
    Wall(corner1=[2.93, 4.32, 0.00], corner2=[0.00, 4.32, 0.00]),
    Wall(corner1=[0.00, 4.32, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.93, 0.00, 0.00]),
    Wall(corner1=[2.93, 0.00, 0.00], corner2=[2.93, 4.32, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
carpet = Assets(description="carpet", size=[3.20, 2.40, 0.02], placements=[AssetInstance() for _ in range(1)])
dresser_A = Assets(description="dresser", size=[0.42, 0.55, 0.62], placements=[AssetInstance() for _ in range(1)])
mirror = Assets(description="mirror", size=[0.04, 0.80, 1.10], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.05, 1.60, 0.95], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="lamp", size=[0.28, 0.28, 0.48], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.28, 0.28, 0.48], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="cabinet", size=[0.45, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
dresser_B = Assets(description="dresser", size=[0.42, 0.55, 0.62], placements=[AssetInstance() for _ in range(1)])
plant = Assets(description="plant", size=[0.35, 0.35, 0.75], placements=[AssetInstance() for _ in range(1)])

carpet[0].instance_id = 'carpet_0'
dresser_A[0].instance_id = 'dresser_A_0'
mirror[0].instance_id = 'mirror_0'
bed[0].instance_id = 'bed_0'
lamp_A[0].instance_id = 'lamp_A_0'
lamp_B[0].instance_id = 'lamp_B_0'
cabinet[0].instance_id = 'cabinet_0'
dresser_B[0].instance_id = 'dresser_B_0'
plant[0].instance_id = 'plant_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

carpet[0].position = [1.3709242615464128, 0.02548881280263843, 0.01]
carpet[0].rotation = [0, 0, 0]
dresser_A[0].position = [1.3555325335136201, 2.00818952861042, 0.31]
dresser_A[0].rotation = [0, 0, 0]
mirror[0].position = [2.581506114114721, 1.4916546387154794, 0.55]
mirror[0].rotation = [0, 0, 0]
bed[0].position = [0.0665911267725592, 0.2991341873276237, 0.475]
bed[0].rotation = [0, 0, 0]
lamp_A[0].position = [1.3234356119322628, 2.90952195344674, 0.24]
lamp_A[0].rotation = [0, 0, 0]
lamp_B[0].position = [0.12006617304625888, 1.7569959645682847, 0.24]
lamp_B[0].rotation = [0, 0, 0]
cabinet[0].position = [1.9197351106108738, 3.319526985807554, 0.9]
cabinet[0].rotation = [0, 0, 0]
dresser_B[0].position = [2.131085608984288, 2.53665582948234, 0.31]
dresser_B[0].rotation = [0, 0, 0]
plant[0].position = [0.8714653767870061, 4.211312929537058, 0.375]
plant[0].rotation = [0, 0, 0]
carpet[0].position = [1.3709242615464128, 0.02548881280263843, 0.01]
carpet[0].rotation = [0, 0, 0]
dresser_A[0].position = [1.3555325335136201, 2.00818952861042, 0.31]
dresser_A[0].rotation = [0, 0, 0]
mirror[0].position = [2.581506114114721, 1.4916546387154794, 0.55]
mirror[0].rotation = [0, 0, 0]
bed[0].position = [0.0665911267725592, 0.2991341873276237, 0.475]
bed[0].rotation = [0, 0, 0]
lamp_A[0].position = [1.3234356119322628, 2.90952195344674, 0.24]
lamp_A[0].rotation = [0, 0, 0]
lamp_B[0].position = [0.12006617304625888, 1.7569959645682847, 0.24]
lamp_B[0].rotation = [0, 0, 0]
cabinet[0].position = [1.9197351106108738, 3.319526985807554, 0.9]
cabinet[0].rotation = [0, 0, 0]
dresser_B[0].position = [2.131085608984288, 2.53665582948234, 0.31]
dresser_B[0].rotation = [0, 0, 0]
plant[0].position = [0.8714653767870061, 4.211312929537058, 0.375]
plant[0].rotation = [0, 0, 0]

solver.constraints = []

# The bed is centered on the north wall, with matching dressers on either
# side. This satisfies the requirement that the bed be between the two
# dressers. The bed sits partly over the carpet, as is normal for a bedroom.
carpet[0].position = [1.465, 2.35, 0.01]
carpet[0].rotation = [0, 0, radians(90)]

dresser_A[0].position = [0.275, 4.11, 0.31]
dresser_A[0].rotation = [0, 0, radians(-90)]

mirror[0].position = [0.02, 1.20, 0.55]
mirror[0].rotation = [0, 0, 0]

bed[0].position = [1.465, 3.295, 0.475]
bed[0].rotation = [0, 0, radians(90)]

# Each lamp is centered on its corresponding dresser.
lamp_A[0].position = [0.275, 4.11, 0.86]
lamp_A[0].rotation = [0, 0, radians(-90)]

lamp_B[0].position = [2.655, 4.11, 0.86]
lamp_B[0].rotation = [0, 0, radians(-90)]

# The cabinet is placed against the window-free south wall, leaving the
# central circulation area and both windows unobstructed.
cabinet[0].position = [2.30, 0.225, 0.90]
cabinet[0].rotation = [0, 0, radians(90)]

dresser_B[0].position = [2.655, 4.11, 0.31]
dresser_B[0].rotation = [0, 0, radians(-90)]

plant[0].position = [0.30, 0.35, 0.375]
plant[0].rotation = [0, 0, radians(45)]


# Fixed targets preserve the proposed layout while the additional semantic
# constraints allow the solver to maintain its important relationships.
carpet_anchor = AssetInstance(position=[1.465, 2.35, 0.01])
dresser_A_anchor = AssetInstance(position=[0.275, 4.11, 0.31])
mirror_anchor = AssetInstance(position=[0.02, 1.20, 0.55])
bed_anchor = AssetInstance(position=[1.465, 3.295, 0.475])
lamp_A_anchor = AssetInstance(position=[0.275, 4.11, 0.86])
lamp_B_anchor = AssetInstance(position=[2.655, 4.11, 0.86])
cabinet_anchor = AssetInstance(position=[2.30, 0.225, 0.90])
dresser_B_anchor = AssetInstance(position=[2.655, 4.11, 0.31])
plant_anchor = AssetInstance(position=[0.30, 0.35, 0.375])

north_reference = AssetInstance(rotation=[0, 0, radians(90)])
south_reference = AssetInstance(rotation=[0, 0, radians(-90)])
east_reference = AssetInstance(rotation=[0, 0, 0])
northeast_reference = AssetInstance(rotation=[0, 0, radians(45)])


# Carpet: keep it centered beneath the main furniture and aligned with the
# long direction of the bed.
solver.distance_constraint(
    carpet[0], carpet_anchor, 0, 0, weight=10
)
solver.align_with(carpet[0], north_reference)


# Bed and dressers: all three meet the north wall. The equal bed-to-dresser
# distances preserve the bed's centered position between the two dressers.
solver.distance_constraint(
    bed[0], bed_anchor, 0, 0, weight=10
)
solver.against_wall(bed[0], walls[0])
solver.align_with(bed[0], north_reference)
solver.distance_constraint(
    bed[0], dresser_A[0], 1.44, 1.45, weight=10
)
solver.distance_constraint(
    bed[0], dresser_B[0], 1.44, 1.45, weight=10
)

solver.distance_constraint(
    dresser_A[0], dresser_A_anchor, 0, 0, weight=10
)
solver.against_wall(dresser_A[0], walls[0])
solver.align_with(dresser_A[0], south_reference)
solver.distance_constraint(
    dresser_A[0], bed[0], 1.44, 1.45, weight=10
)

solver.distance_constraint(
    dresser_B[0], dresser_B_anchor, 0, 0, weight=10
)
solver.against_wall(dresser_B[0], walls[0])
solver.align_with(dresser_B[0], south_reference)
solver.distance_constraint(
    dresser_B[0], bed[0], 1.44, 1.45, weight=10
)


# Lamps: the vertical constraints place them on the dresser tops, while the
# anchor constraints retain their centered horizontal positions.
solver.on_top_of(lamp_A[0], dresser_A[0])
solver.distance_constraint(
    lamp_A[0], lamp_A_anchor, 0, 0, weight=10
)
solver.align_with(lamp_A[0], dresser_A[0])

solver.on_top_of(lamp_B[0], dresser_B[0])
solver.distance_constraint(
    lamp_B[0], lamp_B_anchor, 0, 0, weight=10
)
solver.align_with(lamp_B[0], dresser_B[0])


# Mirror: place it against the lower, window-free section of the west wall
# and orient its reflective face into the room.
solver.distance_constraint(
    mirror[0], mirror_anchor, 0, 0, weight=10
)
solver.against_wall(mirror[0], walls[1])
solver.align_with(mirror[0], east_reference)


# Cabinet: keep it against the south wall and facing north for clear access.
solver.distance_constraint(
    cabinet[0], cabinet_anchor, 0, 0, weight=10
)
solver.against_wall(cabinet[0], walls[2])
solver.align_with(cabinet[0], north_reference)


# Plant: retain it in the free southwest corner without blocking the mirror,
# cabinet, carpet, or either window.
solver.distance_constraint(
    plant[0], plant_anchor, 0, 0, weight=10
)
solver.align_with(plant[0], northeast_reference)

solver.constraints = []
plant[0].position = [0.30000001192092896, 0.3499999940395355, 0.375]
plant[0].rotation = [0, 0, 0.7948229285630478]
plant[0].optimize = 2
dresser_A[0].position = [0.27596309781074524, 4.106613636016846, 0.3100000023841858]
dresser_A[0].rotation = [0, 0, -1.5707962162249158]
dresser_A[0].optimize = 2
carpet[0].position = [1.465000033378601, 2.3499999046325684, 0.009999999776482582]
carpet[0].rotation = [0, 0, 1.5802211042556205]
carpet[0].optimize = 2
lamp_A[0].position = [0.2750000059604645, 4.110000133514404, 0.8600000143051147]
lamp_A[0].rotation = [0, 0, -1.5707962249869731]
lamp_A[0].optimize = 2
dresser_B[0].position = [2.6516175270080566, 4.106616497039795, 0.3100000023841858]
dresser_B[0].rotation = [0, 0, -1.5707963233740168]
dresser_B[0].optimize = 2
lamp_B[0].position = [2.6549999713897705, 4.110000133514404, 0.8600000143051147]
lamp_B[0].rotation = [0, 0, -1.5707963322030536]
lamp_B[0].optimize = 2
cabinet[0].position = [2.299999952316284, 0.22499997913837433, 0.8999999761581421]
cabinet[0].rotation = [0, 0, 1.5707963678198436]
cabinet[0].optimize = 2
mirror[0].position = [0.020000003278255463, 1.2000000476837158, 0.550000011920929]
mirror[0].rotation = [0, 0, 4.1016708838503606e-08]
mirror[0].optimize = 2
bed[0].position = [1.466086745262146, 3.2851779460906982, 0.4749999940395355]
bed[0].rotation = [0, 0, -1.5707982610902844]
bed[0].optimize = 2

