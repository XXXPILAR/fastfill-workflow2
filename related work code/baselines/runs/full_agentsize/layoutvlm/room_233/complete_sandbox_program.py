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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[5.47, 0.00, 0.00]),
    Wall(corner1=[5.47, 0.00, 0.00], corner2=[5.47, 4.19, 0.00]),
    Wall(corner1=[5.47, 4.19, 0.00], corner2=[1.02, 4.19, 0.00]),
    Wall(corner1=[1.02, 4.19, 0.00], corner2=[1.03, 1.64, 0.00]),
    Wall(corner1=[1.03, 1.64, 0.00], corner2=[0.00, 1.64, 0.00]),
    Wall(corner1=[0.00, 1.64, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bed = Assets(description="bed", size=[2.10, 1.80, 0.60], placements=[AssetInstance() for _ in range(1)])
nightstand_A = Assets(description="nightstand", size=[0.40, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
chair = Assets(description="chair", size=[0.60, 0.55, 0.85], placements=[AssetInstance() for _ in range(1)])
stool = Assets(description="stool", size=[0.40, 0.40, 0.45], placements=[AssetInstance() for _ in range(1)])
wardrobe_A = Assets(description="wardrobe", size=[0.60, 1.80, 2.20], placements=[AssetInstance() for _ in range(1)])
nightstand_B = Assets(description="nightstand", size=[0.40, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[1.70, 2.40, 0.02], placements=[AssetInstance() for _ in range(1)])
dining_table_combination = Assets(description="dining table combination", size=[0.75, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
wardrobe_B = Assets(description="wardrobe", size=[0.60, 1.50, 2.20], placements=[AssetInstance() for _ in range(1)])

bed[0].instance_id = 'bed_0'
nightstand_A[0].instance_id = 'nightstand_A_0'
chair[0].instance_id = 'chair_0'
stool[0].instance_id = 'stool_0'
wardrobe_A[0].instance_id = 'wardrobe_A_0'
nightstand_B[0].instance_id = 'nightstand_B_0'
carpet[0].instance_id = 'carpet_0'
dining_table_combination[0].instance_id = 'dining_table_combination_0'
wardrobe_B[0].instance_id = 'wardrobe_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

bed[0].position = [2.33482577655452, 3.494083066061519, 0.3]
bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [5.4517128782320325, 1.1103347433339372, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
chair[0].position = [2.1312899246822705, 1.1738401446712354, 0.425]
chair[0].rotation = [0, 0, 0]
stool[0].position = [3.194382627685931, 2.6854915502848047, 0.225]
stool[0].rotation = [0, 0, 0]
wardrobe_A[0].position = [1.5543389029621684, 3.1273731373810194, 1.1]
wardrobe_A[0].rotation = [0, 0, 0]
nightstand_B[0].position = [5.44757081916112, 3.8891055307242657, 0.275]
nightstand_B[0].rotation = [0, 0, 0]
carpet[0].position = [5.17765476567698, 2.4104832980569744, 0.01]
carpet[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [3.651839109905887, 2.8657448930215605, 0.375]
dining_table_combination[0].rotation = [0, 0, 0]
wardrobe_B[0].position = [4.143097521213214, 1.9598505834760354, 1.1]
wardrobe_B[0].rotation = [0, 0, 0]
bed[0].position = [2.33482577655452, 3.494083066061519, 0.3]
bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [5.4517128782320325, 1.1103347433339372, 0.275]
nightstand_A[0].rotation = [0, 0, 0]
chair[0].position = [2.1312899246822705, 1.1738401446712354, 0.425]
chair[0].rotation = [0, 0, 0]
stool[0].position = [3.194382627685931, 2.6854915502848047, 0.225]
stool[0].rotation = [0, 0, 0]
wardrobe_A[0].position = [1.5543389029621684, 3.1273731373810194, 1.1]
wardrobe_A[0].rotation = [0, 0, 0]
nightstand_B[0].position = [5.44757081916112, 3.8891055307242657, 0.275]
nightstand_B[0].rotation = [0, 0, 0]
carpet[0].position = [5.17765476567698, 2.4104832980569744, 0.01]
carpet[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [3.651839109905887, 2.8657448930215605, 0.375]
dining_table_combination[0].rotation = [0, 0, 0]
wardrobe_B[0].position = [4.143097521213214, 1.9598505834760354, 1.1]
wardrobe_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed target points preserve the intended zoning while still allowing the
# solver to make small feasibility adjustments through the softer constraints.
bed_target = AssetInstance(position=[2.65, 3.29, 0.30])
nightstand_A_target = AssetInstance(position=[1.35, 3.94, 0.275])
nightstand_B_target = AssetInstance(position=[3.95, 3.94, 0.275])
wardrobe_A_target = AssetInstance(position=[2.15, 0.30, 1.10])
wardrobe_B_target = AssetInstance(position=[4.72, 0.30, 1.10])
carpet_target = AssetInstance(position=[3.35, 1.45, 0.01])
dining_target = AssetInstance(position=[3.35, 1.45, 0.375])
chair_target = AssetInstance(position=[4.20, 1.45, 0.425])
stool_target = AssetInstance(position=[2.65, 1.45, 0.225])

# Heading references: the bed faces into the room, the wardrobes face away
# from the bottom wall, and the dining table's long dimension runs north-south.
bed_heading = AssetInstance(rotation=[0, 0, radians(-90)])
wardrobe_heading = AssetInstance(rotation=[0, 0, radians(90)])
dining_heading = AssetInstance(rotation=[0, 0, 0])

# Place the sleeping zone along the top wall. The two nightstands flank the
# bed symmetrically, satisfying the requirement that the bed be between them.
bed[0].position = [2.65, 3.29, 0.30]
bed[0].rotation = [0, 0, radians(-90)]

nightstand_A[0].position = [1.35, 3.94, 0.275]
nightstand_A[0].rotation = [0, 0, radians(-90)]

nightstand_B[0].position = [3.95, 3.94, 0.275]
nightstand_B[0].rotation = [0, 0, radians(-90)]

# Put both wardrobes along the bottom wall. This keeps them away from the
# right-wall window and leaves the two lower-left door approaches unobstructed.
wardrobe_A[0].position = [2.15, 0.30, 1.10]
wardrobe_A[0].rotation = [0, 0, radians(90)]

wardrobe_B[0].position = [4.72, 0.30, 1.10]
wardrobe_B[0].rotation = [0, 0, radians(90)]

# Rotate the carpet so it fits between the wardrobes and sleeping zone.
# The dining group is arranged over the carpet as an intentional layered use.
carpet[0].position = [3.35, 1.45, 0.01]
carpet[0].rotation = [0, 0, radians(90)]

dining_table_combination[0].position = [3.35, 1.45, 0.375]
dining_table_combination[0].rotation = [0, 0, 0]

# The chair is east of the table and therefore faces west toward it.
chair[0].position = [4.20, 1.45, 0.425]
chair[0].rotation = [0, 0, radians(180)]

# The stool sits on the opposite side of the dining table.
stool[0].position = [2.65, 1.45, 0.225]
stool[0].rotation = [0, 0, 0]

# High-priority position constraints establish the non-overlapping layout.
solver.distance_constraint(bed[0], bed_target, 0, 0, weight=10)
solver.distance_constraint(nightstand_A[0], nightstand_A_target, 0, 0, weight=10)
solver.distance_constraint(nightstand_B[0], nightstand_B_target, 0, 0, weight=10)
solver.distance_constraint(wardrobe_A[0], wardrobe_A_target, 0, 0, weight=10)
solver.distance_constraint(wardrobe_B[0], wardrobe_B_target, 0, 0, weight=10)
solver.distance_constraint(carpet[0], carpet_target, 0, 0, weight=10)
solver.distance_constraint(dining_table_combination[0], dining_target, 0, 0, weight=10)
solver.distance_constraint(chair[0], chair_target, 0, 0, weight=10)
solver.distance_constraint(stool[0], stool_target, 0, 0, weight=10)

# Wall relationships retain the intended sleeping and storage zones if the
# solver needs to adjust the layout. walls[2] is the top wall and walls[0]
# is the bottom wall.
solver.against_wall(bed[0], walls[2])
solver.against_wall(nightstand_A[0], walls[2])
solver.against_wall(nightstand_B[0], walls[2])
solver.against_wall(wardrobe_A[0], walls[0])
solver.against_wall(wardrobe_B[0], walls[0])

# Preserve a symmetric bed/nightstand composition.
solver.distance_constraint(bed[0], nightstand_A[0], 1.45, 1.45, weight=5)
solver.distance_constraint(bed[0], nightstand_B[0], 1.45, 1.45, weight=5)
solver.distance_constraint(
    nightstand_A[0], nightstand_B[0], 2.60, 2.60, weight=5
)

# Maintain usable spacing around the dining table.
solver.distance_constraint(chair[0], dining_table_combination[0], 0.85, 0.95, weight=5)
solver.distance_constraint(stool[0], dining_table_combination[0], 0.65, 0.75, weight=5)

# Orientation constraints for every new instance.
solver.align_with(bed[0], bed_heading)
solver.align_with(nightstand_A[0], bed[0])
solver.align_with(nightstand_B[0], bed[0])
solver.align_with(wardrobe_A[0], wardrobe_heading)
solver.align_with(wardrobe_B[0], wardrobe_heading)
solver.align_with(carpet[0], dining_heading, angle=90)
solver.align_with(dining_table_combination[0], dining_heading)

# The required chair-to-table facing relationship is explicit. The stool also
# faces toward the table from the opposite side.
solver.point_towards(chair[0], dining_table_combination[0])
solver.point_towards(stool[0], dining_table_combination[0])

solver.constraints = []
wardrobe_A[0].position = [2.14996600151062, 0.30000025033950806, 1.100000023841858]
wardrobe_A[0].rotation = [0, 0, 1.5707962813599379]
wardrobe_A[0].optimize = 2
stool[0].position = [2.6500000953674316, 1.4500000476837158, 0.22499999403953552]
stool[0].rotation = [0, 0, 0.01256637125682779]
stool[0].optimize = 2
carpet[0].position = [3.3499999046325684, 1.4500000476837158, 0.009999999776482582]
carpet[0].rotation = [0, 0, 1.5802211042556205]
carpet[0].optimize = 2
wardrobe_B[0].position = [4.662015438079834, 0.30000007152557373, 1.100000023841858]
wardrobe_B[0].rotation = [0, 0, 1.5707962868978973]
wardrobe_B[0].optimize = 2
bed[0].position = [2.6501946449279785, 3.1421701908111572, 0.30000001192092896]
bed[0].rotation = [0, 0, -1.57079646727821]
bed[0].optimize = 2
nightstand_A[0].position = [1.349259376525879, 3.9921422004699707, 0.2750000059604645]
nightstand_A[0].rotation = [0, 0, -1.5707963782181555]
nightstand_A[0].optimize = 2
chair[0].position = [4.258048057556152, 1.4500000476837158, 0.42500001192092896]
chair[0].rotation = [0, 0, -3.1290262823329655]
chair[0].optimize = 2
dining_table_combination[0].position = [3.3499999046325684, 1.4500000476837158, 0.375]
dining_table_combination[0].rotation = [0, 0, 0.021991148286022624]
dining_table_combination[0].optimize = 2
nightstand_B[0].position = [3.9509685039520264, 3.9921696186065674, 0.2750000059604645]
nightstand_B[0].rotation = [0, 0, -1.5707963778654024]
nightstand_B[0].optimize = 2

