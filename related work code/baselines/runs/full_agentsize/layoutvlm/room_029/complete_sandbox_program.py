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
    Wall(corner1=[0.00, 3.66, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[9.76, 0.00, 0.00]),
    Wall(corner1=[9.76, 0.00, 0.00], corner2=[9.76, 1.27, 0.00]),
    Wall(corner1=[9.76, 1.27, 0.00], corner2=[7.35, 1.27, 0.00]),
    Wall(corner1=[7.35, 1.27, 0.00], corner2=[7.35, 3.66, 0.00]),
    Wall(corner1=[7.35, 3.66, 0.00], corner2=[0.00, 3.66, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
lounge_chair_A = Assets(description="A modern black chair with a woven seat and backrest, featuring curved armrests that extend into the back support.", size=[0.78, 0.72, 0.82], placements=[AssetInstance() for _ in range(1)])
wine_cabinet_A = Assets(description="A tall, dark wooden wardrobe with two doors featuring vertical lines and decorative elements. The wardrobe has a sleek design with a polished finish.", size=[0.48, 1.05, 1.85], placements=[AssetInstance() for _ in range(1)])
potted_plant_A = Assets(description="A tall potted plant with slender green leaves and brown stems, housed in a square pot with a striped pattern.", size=[0.55, 0.55, 1.75], placements=[AssetInstance() for _ in range(1)])
loveseat_sofa = Assets(description="A modern daybed with a sleek black frame and a gray cushioned mattress. It features decorative pillows and a throw blanket, along with a book resting on it.", size=[0.90, 2.05, 0.78], placements=[AssetInstance() for _ in range(1)])
wine_cabinet_B = Assets(description="A tall, dark wooden wardrobe with two doors featuring vertical lines and decorative elements. The wardrobe has a sleek design with a polished finish.", size=[0.48, 1.05, 1.85], placements=[AssetInstance() for _ in range(1)])
footstool = Assets(description="A decorative mask with intricate blue and white patterns resembling traditional East Asian art. It features two large eye holes and a wide mouth opening, giving it an expressive appearance.", size=[0.10, 0.28, 0.36], placements=[AssetInstance() for _ in range(1)])
lounge_chair_B = Assets(description="A modern black chair with a woven seat and backrest, featuring curved armrests that extend into the back support.", size=[0.78, 0.72, 0.82], placements=[AssetInstance() for _ in range(1)])
lounge_chair_C = Assets(description="A wooden armchair with a cushioned seat and backrest, featuring an intricate lattice design on the backrest.", size=[0.76, 0.70, 0.88], placements=[AssetInstance() for _ in range(1)])
potted_plant_B = Assets(description="A potted bamboo plant with slender green leaves and brown stems, placed in a beige pot on a black reflective surface.", size=[0.55, 0.55, 1.80], placements=[AssetInstance() for _ in range(1)])
lounge_chair_D = Assets(description="A modern black chair with a woven seat and backrest, featuring curved armrests that extend into the back support.", size=[0.78, 0.72, 0.82], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="A modern coffee table with a sleek design featuring a rectangular marble top and a black metal frame with curved legs.", size=[0.70, 1.30, 0.42], placements=[AssetInstance() for _ in range(1)])
shelf = Assets(description="A tall, dark wooden bookshelf with five shelves, designed for storing books or decorative items. It has a sturdy frame and a simple, modern design.", size=[0.35, 0.95, 1.90], placements=[AssetInstance() for _ in range(1)])
tv_stand = Assets(description="A dark brown sideboard with intricate floral and bird designs on its panels. It features multiple drawers and doors, each adorned with decorative patterns. The sideboard has a classic design with ornate details and stands on small legs.", size=[0.48, 1.80, 0.78], placements=[AssetInstance() for _ in range(1)])
dining_table = Assets(description="A sleek dining table with a rectangular top and four angled legs that converge at the center for stability.", size=[1.00, 2.20, 0.75], placements=[AssetInstance() for _ in range(1)])
lounge_chair_E = Assets(description="A modern black chair with a woven seat and backrest, featuring curved armrests that extend into the back support.", size=[0.78, 0.72, 0.82], placements=[AssetInstance() for _ in range(1)])
lounge_chair_F = Assets(description="A wooden armchair with a cushioned seat and backrest, featuring an intricate lattice design on the backrest.", size=[0.76, 0.70, 0.88], placements=[AssetInstance() for _ in range(1)])

lounge_chair_A[0].instance_id = 'lounge_chair_A_0'
wine_cabinet_A[0].instance_id = 'wine_cabinet_A_0'
potted_plant_A[0].instance_id = 'potted_plant_A_0'
loveseat_sofa[0].instance_id = 'loveseat_sofa_0'
wine_cabinet_B[0].instance_id = 'wine_cabinet_B_0'
footstool[0].instance_id = 'footstool_0'
lounge_chair_B[0].instance_id = 'lounge_chair_B_0'
lounge_chair_C[0].instance_id = 'lounge_chair_C_0'
potted_plant_B[0].instance_id = 'potted_plant_B_0'
lounge_chair_D[0].instance_id = 'lounge_chair_D_0'
coffee_table[0].instance_id = 'coffee_table_0'
shelf[0].instance_id = 'shelf_0'
tv_stand[0].instance_id = 'tv_stand_0'
dining_table[0].instance_id = 'dining_table_0'
lounge_chair_E[0].instance_id = 'lounge_chair_E_0'
lounge_chair_F[0].instance_id = 'lounge_chair_F_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

lounge_chair_A[0].position = [1.3877390306515291, 1.5472136394378004, 0.41]
lounge_chair_A[0].rotation = [0, 0, 0]
wine_cabinet_A[0].position = [6.494226856587593, 2.6093551279987954, 0.925]
wine_cabinet_A[0].rotation = [0, 0, 0]
potted_plant_A[0].position = [7.163030369671496, 1.0069610620029634, 0.875]
potted_plant_A[0].rotation = [0, 0, 0]
loveseat_sofa[0].position = [7.417964773458548, 0.2240461629964689, 0.39]
loveseat_sofa[0].rotation = [0, 0, 0]
wine_cabinet_B[0].position = [6.813306738237063, 0.2476505302750126, 0.925]
wine_cabinet_B[0].rotation = [0, 0, 0]
footstool[0].position = [2.0431874337466516, 3.082194966274365, 0.18]
footstool[0].rotation = [0, 0, 0]
lounge_chair_B[0].position = [6.510703140143347, 0.024894150975120894, 0.41]
lounge_chair_B[0].rotation = [0, 0, 0]
lounge_chair_C[0].position = [1.8258362884900377, 0.9255732223871439, 0.44]
lounge_chair_C[0].rotation = [0, 0, 0]
potted_plant_B[0].position = [1.1117882406697601, 1.2207807949017433, 0.9]
potted_plant_B[0].rotation = [0, 0, 0]
lounge_chair_D[0].position = [1.8933887307370982, 3.0761506437288046, 0.41]
lounge_chair_D[0].rotation = [0, 0, 0]
coffee_table[0].position = [1.70843956039786, 0.4820259055503355, 0.21]
coffee_table[0].rotation = [0, 0, 0]
shelf[0].position = [3.448591674066565, 3.222327201342565, 0.95]
shelf[0].rotation = [0, 0, 0]
tv_stand[0].position = [6.3080206561916405, 2.607424375838993, 0.39]
tv_stand[0].rotation = [0, 0, 0]
dining_table[0].position = [7.471902101330759, 0.496323139967604, 0.375]
dining_table[0].rotation = [0, 0, 0]
lounge_chair_E[0].position = [8.765949065730437, 0.9462130897789403, 0.41]
lounge_chair_E[0].rotation = [0, 0, 0]
lounge_chair_F[0].position = [9.701467957168093, 0.30805704657430827, 0.44]
lounge_chair_F[0].rotation = [0, 0, 0]
lounge_chair_A[0].position = [1.3877390306515291, 1.5472136394378004, 0.41]
lounge_chair_A[0].rotation = [0, 0, 0]
wine_cabinet_A[0].position = [6.494226856587593, 2.6093551279987954, 0.925]
wine_cabinet_A[0].rotation = [0, 0, 0]
potted_plant_A[0].position = [7.163030369671496, 1.0069610620029634, 0.875]
potted_plant_A[0].rotation = [0, 0, 0]
loveseat_sofa[0].position = [7.417964773458548, 0.2240461629964689, 0.39]
loveseat_sofa[0].rotation = [0, 0, 0]
wine_cabinet_B[0].position = [6.813306738237063, 0.2476505302750126, 0.925]
wine_cabinet_B[0].rotation = [0, 0, 0]
footstool[0].position = [2.0431874337466516, 3.082194966274365, 0.18]
footstool[0].rotation = [0, 0, 0]
lounge_chair_B[0].position = [6.510703140143347, 0.024894150975120894, 0.41]
lounge_chair_B[0].rotation = [0, 0, 0]
lounge_chair_C[0].position = [1.8258362884900377, 0.9255732223871439, 0.44]
lounge_chair_C[0].rotation = [0, 0, 0]
potted_plant_B[0].position = [1.1117882406697601, 1.2207807949017433, 0.9]
potted_plant_B[0].rotation = [0, 0, 0]
lounge_chair_D[0].position = [1.8933887307370982, 3.0761506437288046, 0.41]
lounge_chair_D[0].rotation = [0, 0, 0]
coffee_table[0].position = [1.70843956039786, 0.4820259055503355, 0.21]
coffee_table[0].rotation = [0, 0, 0]
shelf[0].position = [3.448591674066565, 3.222327201342565, 0.95]
shelf[0].rotation = [0, 0, 0]
tv_stand[0].position = [6.3080206561916405, 2.607424375838993, 0.39]
tv_stand[0].rotation = [0, 0, 0]
dining_table[0].position = [7.471902101330759, 0.496323139967604, 0.375]
dining_table[0].rotation = [0, 0, 0]
lounge_chair_E[0].position = [8.765949065730437, 0.9462130897789403, 0.41]
lounge_chair_E[0].rotation = [0, 0, 0]
lounge_chair_F[0].position = [9.701467957168093, 0.30805704657430827, 0.44]
lounge_chair_F[0].rotation = [0, 0, 0]

solver.constraints = []

# The left half of the room is used as a four-seat dining area. The right
# half forms a compact conversation area, while the narrow eastern extension
# remains open for circulation between its two doors.

# Dining group: the table is geometrically between lounge_chair_A (west)
# and lounge_chair_B (east), corresponding to the requested o0000/o0006 pair.
dining_table[0].position = [2.00, 1.65, 0.375]
dining_table[0].rotation = [0, 0, radians(90)]

lounge_chair_A[0].position = [0.45, 1.65, 0.41]
lounge_chair_A[0].rotation = [0, 0, radians(0)]

lounge_chair_B[0].position = [3.55, 1.65, 0.41]
lounge_chair_B[0].rotation = [0, 0, radians(180)]

lounge_chair_E[0].position = [2.00, 0.65, 0.41]
lounge_chair_E[0].rotation = [0, 0, radians(90)]

lounge_chair_F[0].position = [2.00, 2.65, 0.44]
lounge_chair_F[0].rotation = [0, 0, radians(-90)]

# Living group: the sofa is backed by the north wall, with a coffee table
# and two chairs facing into the conversation area.
loveseat_sofa[0].position = [6.15, 3.21, 0.39]
loveseat_sofa[0].rotation = [0, 0, radians(-90)]

coffee_table[0].position = [5.92, 2.15, 0.21]
coffee_table[0].rotation = [0, 0, radians(90)]

lounge_chair_C[0].position = [4.85, 2.15, 0.44]
lounge_chair_C[0].rotation = [0, 0, radians(0)]

lounge_chair_D[0].position = [6.96, 2.15, 0.41]
lounge_chair_D[0].rotation = [0, 0, radians(180)]

# Tall storage is consolidated along the uninterrupted north wall. This
# avoids the west-wall windows and preserves all bottom-wall door approaches.
wine_cabinet_A[0].position = [0.55, 3.42, 0.925]
wine_cabinet_A[0].rotation = [0, 0, radians(-90)]

wine_cabinet_B[0].position = [1.65, 3.42, 0.925]
wine_cabinet_B[0].rotation = [0, 0, radians(-90)]

shelf[0].position = [2.70, 3.485, 0.95]
shelf[0].rotation = [0, 0, radians(-90)]

tv_stand[0].position = [4.10, 3.42, 0.39]
tv_stand[0].rotation = [0, 0, radians(-90)]

# The small decorative mask is displayed on the TV stand rather than left
# on the floor.
footstool[0].position = [4.10, 3.42, 0.96]
footstool[0].rotation = [0, 0, radians(-90)]

# Plants occupy otherwise unused pockets without covering windows or doors.
potted_plant_A[0].position = [3.55, 2.75, 0.875]
potted_plant_A[0].rotation = [0, 0, radians(-90)]

potted_plant_B[0].position = [7.75, 0.995, 0.90]
potted_plant_B[0].rotation = [0, 0, radians(-90)]


# Exact high-priority position constraints preserve the planned clearances
# and prevent the closely packed wall furniture from drifting into doors.
solver.distance_constraint(
    dining_table[0], AssetInstance(position=[2.00, 1.65, 0.375]),
    0, 0, weight=10
)
solver.distance_constraint(
    lounge_chair_A[0], AssetInstance(position=[0.45, 1.65, 0.41]),
    0, 0, weight=10
)
solver.distance_constraint(
    lounge_chair_B[0], AssetInstance(position=[3.55, 1.65, 0.41]),
    0, 0, weight=10
)
solver.distance_constraint(
    lounge_chair_E[0], AssetInstance(position=[2.00, 0.65, 0.41]),
    0, 0, weight=10
)
solver.distance_constraint(
    lounge_chair_F[0], AssetInstance(position=[2.00, 2.65, 0.44]),
    0, 0, weight=10
)
solver.distance_constraint(
    loveseat_sofa[0], AssetInstance(position=[6.15, 3.21, 0.39]),
    0, 0, weight=10
)
solver.distance_constraint(
    coffee_table[0], AssetInstance(position=[5.92, 2.15, 0.21]),
    0, 0, weight=10
)
solver.distance_constraint(
    lounge_chair_C[0], AssetInstance(position=[4.85, 2.15, 0.44]),
    0, 0, weight=10
)
solver.distance_constraint(
    lounge_chair_D[0], AssetInstance(position=[6.96, 2.15, 0.41]),
    0, 0, weight=10
)
solver.distance_constraint(
    wine_cabinet_A[0], AssetInstance(position=[0.55, 3.42, 0.925]),
    0, 0, weight=10
)
solver.distance_constraint(
    wine_cabinet_B[0], AssetInstance(position=[1.65, 3.42, 0.925]),
    0, 0, weight=10
)
solver.distance_constraint(
    shelf[0], AssetInstance(position=[2.70, 3.485, 0.95]),
    0, 0, weight=10
)
solver.distance_constraint(
    tv_stand[0], AssetInstance(position=[4.10, 3.42, 0.39]),
    0, 0, weight=10
)
solver.distance_constraint(
    footstool[0], AssetInstance(position=[4.10, 3.42, 0.96]),
    0, 0, weight=10
)
solver.distance_constraint(
    potted_plant_A[0], AssetInstance(position=[3.55, 2.75, 0.875]),
    0, 0, weight=10
)
solver.distance_constraint(
    potted_plant_B[0], AssetInstance(position=[7.75, 0.995, 0.90]),
    0, 0, weight=10
)


# Primary orientation constraints for the dining group. All four chairs face
# the table, and the table's long axis runs east-west.
solver.align_with(
    dining_table[0],
    AssetInstance(rotation=[0, 0, radians(90)])
)
solver.point_towards(lounge_chair_A[0], dining_table[0])
solver.point_towards(lounge_chair_B[0], dining_table[0])
solver.point_towards(lounge_chair_E[0], dining_table[0])
solver.point_towards(lounge_chair_F[0], dining_table[0])

# Primary orientation constraints for the conversation group.
solver.align_with(
    loveseat_sofa[0],
    AssetInstance(rotation=[0, 0, radians(-90)])
)
solver.align_with(
    coffee_table[0],
    AssetInstance(rotation=[0, 0, radians(90)])
)
solver.point_towards(lounge_chair_C[0], coffee_table[0])
solver.point_towards(lounge_chair_D[0], coffee_table[0])

# All north-wall furniture faces south into the room.
south_facing_reference = AssetInstance(rotation=[0, 0, radians(-90)])
solver.align_with(wine_cabinet_A[0], south_facing_reference)
solver.align_with(wine_cabinet_B[0], south_facing_reference)
solver.align_with(shelf[0], south_facing_reference)
solver.align_with(tv_stand[0], south_facing_reference)
solver.align_with(footstool[0], tv_stand[0])
solver.align_with(potted_plant_A[0], tv_stand[0])
solver.align_with(potted_plant_B[0], tv_stand[0])


# Wall relationships keep the shallow furniture flush with the north wall.
solver.against_wall(wine_cabinet_A[0], walls[5])
solver.against_wall(wine_cabinet_B[0], walls[5])
solver.against_wall(shelf[0], walls[5])
solver.against_wall(tv_stand[0], walls[5])
solver.against_wall(loveseat_sofa[0], walls[5])

# The eastern plant is tucked against the short horizontal wall of the
# extension while remaining west of the two eastern door openings.
solver.against_wall(potted_plant_B[0], walls[3])

# Preserve the functional grouping if the solver has to make small physical
# adjustments. These ranges leave usable gaps rather than forcing contact.
solver.distance_constraint(
    lounge_chair_A[0], dining_table[0], 1.45, 1.65, weight=5
)
solver.distance_constraint(
    lounge_chair_B[0], dining_table[0], 1.45, 1.65, weight=5
)
solver.distance_constraint(
    lounge_chair_E[0], dining_table[0], 0.90, 1.10, weight=5
)
solver.distance_constraint(
    lounge_chair_F[0], dining_table[0], 0.90, 1.10, weight=5
)
solver.distance_constraint(
    coffee_table[0], loveseat_sofa[0], 1.00, 1.20, weight=5
)
solver.distance_constraint(
    lounge_chair_C[0], coffee_table[0], 1.00, 1.20, weight=5
)
solver.distance_constraint(
    lounge_chair_D[0], coffee_table[0], 0.95, 1.15, weight=5
)
solver.distance_constraint(
    potted_plant_A[0], dining_table[0], 1.75, 2.00, weight=1
)

# The small decorative object must remain supported by the TV stand.
solver.on_top_of(footstool[0], tv_stand[0])
solver.distance_constraint(
    footstool[0], tv_stand[0], 0.50, 0.65, weight=5
)

solver.constraints = []
wine_cabinet_A[0].position = [0.550000011920929, 3.4149999618530273, 0.925000011920929]
wine_cabinet_A[0].rotation = [0, 0, -1.570796283082996]
wine_cabinet_A[0].optimize = 2
lounge_chair_F[0].position = [2.0, 2.6500000953674316, 0.4399999976158142]
lounge_chair_F[0].rotation = [0, 0, -1.5582299555380688]
lounge_chair_F[0].optimize = 2
lounge_chair_C[0].position = [4.849999904632568, 2.1500000953674316, 0.4399999976158142]
lounge_chair_C[0].rotation = [0, 0, 0.01256637125682779]
lounge_chair_C[0].optimize = 2
shelf[0].position = [2.700000047683716, 3.4800000190734863, 0.949999988079071]
shelf[0].rotation = [0, 0, -1.5707962830694289]
shelf[0].optimize = 2
lounge_chair_A[0].position = [0.44999998807907104, 1.649999976158142, 0.4099999964237213]
lounge_chair_A[0].rotation = [0, 0, 0.01256637125682779]
lounge_chair_A[0].optimize = 2
loveseat_sofa[0].position = [6.150000095367432, 3.2049999237060547, 0.38999998569488525]
loveseat_sofa[0].rotation = [0, 0, -1.5707962999940375]
loveseat_sofa[0].optimize = 2
lounge_chair_D[0].position = [6.960000038146973, 2.1500000953674316, 0.4099999964237213]
lounge_chair_D[0].rotation = [0, 0, -3.1290262823329655]
lounge_chair_D[0].optimize = 2
footstool[0].position = [4.099999904632568, 3.6049997806549072, 0.9599999785423279]
footstool[0].rotation = [0, 0, -1.570796283137588]
footstool[0].optimize = 2
dining_table[0].position = [2.0, 1.649999976158142, 0.375]
dining_table[0].rotation = [0, 0, 1.608495437993307]
dining_table[0].optimize = 2
potted_plant_B[0].position = [7.75, 0.999000072479248, 0.8999999761581421]
potted_plant_B[0].rotation = [0, 0, -1.5707962830744735]
potted_plant_B[0].optimize = 2
tv_stand[0].position = [4.099999904632568, 3.4149999618530273, 0.38999998569488525]
tv_stand[0].rotation = [0, 0, -1.5707962831057565]
tv_stand[0].optimize = 2
potted_plant_A[0].position = [3.549999952316284, 2.75, 0.875]
potted_plant_A[0].rotation = [0, 0, -1.5707962831412554]
potted_plant_A[0].optimize = 2
wine_cabinet_B[0].position = [1.649999976158142, 3.4149999618530273, 0.925000011920929]
wine_cabinet_B[0].rotation = [0, 0, -1.5707962830829991]
wine_cabinet_B[0].optimize = 2
lounge_chair_E[0].position = [2.0, 0.6499999761581421, 0.4099999964237213]
lounge_chair_E[0].rotation = [0, 0, 1.5833626980517244]
lounge_chair_E[0].optimize = 2
lounge_chair_B[0].position = [3.549999952316284, 1.649999976158142, 0.4099999964237213]
lounge_chair_B[0].rotation = [0, 0, -3.1290262823329655]
lounge_chair_B[0].optimize = 2
coffee_table[0].position = [5.920000076293945, 2.1500000953674316, 0.20999999344348907]
coffee_table[0].rotation = [0, 0, 1.5959290669047523]
coffee_table[0].optimize = 2

