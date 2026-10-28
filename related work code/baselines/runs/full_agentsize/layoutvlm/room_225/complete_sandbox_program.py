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
    Wall(corner1=[4.15, 5.53, 0.00], corner2=[6.16, 5.53, 0.00]),
    Wall(corner1=[6.16, 5.53, 0.00], corner2=[6.16, 6.78, 0.00]),
    Wall(corner1=[6.16, 6.78, 0.00], corner2=[4.14, 6.78, 0.00]),
    Wall(corner1=[4.14, 6.78, 0.00], corner2=[4.13, 11.81, 0.00]),
    Wall(corner1=[4.13, 11.81, 0.00], corner2=[0.00, 11.81, 0.00]),
    Wall(corner1=[0.00, 11.81, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.50, 0.00, 0.00]),
    Wall(corner1=[3.50, 0.00, 0.00], corner2=[3.50, 3.81, 0.00]),
    Wall(corner1=[3.50, 3.81, 0.00], corner2=[4.17, 3.81, 0.00]),
    Wall(corner1=[4.17, 3.81, 0.00], corner2=[4.15, 5.53, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
dining_table_combination = Assets(description="dining table combination", size=[1.50, 2.40, 0.78], placements=[AssetInstance() for _ in range(1)])
tv = Assets(description="tv", size=[0.08, 1.45, 0.84], placements=[AssetInstance() for _ in range(1)])
tv_cabinet = Assets(description="tv cabinet", size=[0.42, 2.00, 0.50], placements=[AssetInstance() for _ in range(1)])
sofa_A = Assets(description="sofa", size=[0.92, 2.20, 0.85], placements=[AssetInstance() for _ in range(1)])
sofa_B = Assets(description="sofa", size=[0.95, 2.40, 0.86], placements=[AssetInstance() for _ in range(1)])
wine_cabinet = Assets(description="wine cabinet", size=[0.45, 1.20, 1.90], placements=[AssetInstance() for _ in range(1)])
potted_bonsai = Assets(description="potted bonsai", size=[0.55, 0.65, 1.25], placements=[AssetInstance() for _ in range(1)])
stool = Assets(description="stool", size=[0.42, 0.42, 0.46], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="coffee table", size=[0.70, 1.30, 0.42], placements=[AssetInstance() for _ in range(1)])
side_table_A = Assets(description="side table", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
sofa_C = Assets(description="sofa", size=[0.90, 1.90, 0.84], placements=[AssetInstance() for _ in range(1)])
side_table_B = Assets(description="side table", size=[0.48, 0.48, 0.52], placements=[AssetInstance() for _ in range(1)])
side_table_C = Assets(description="side table", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
side_table_D = Assets(description="side table", size=[0.45, 0.45, 0.50], placements=[AssetInstance() for _ in range(1)])

dining_table_combination[0].instance_id = 'dining_table_combination_0'
tv[0].instance_id = 'tv_0'
tv_cabinet[0].instance_id = 'tv_cabinet_0'
sofa_A[0].instance_id = 'sofa_A_0'
sofa_B[0].instance_id = 'sofa_B_0'
wine_cabinet[0].instance_id = 'wine_cabinet_0'
potted_bonsai[0].instance_id = 'potted_bonsai_0'
stool[0].instance_id = 'stool_0'
coffee_table[0].instance_id = 'coffee_table_0'
side_table_A[0].instance_id = 'side_table_A_0'
sofa_C[0].instance_id = 'sofa_C_0'
side_table_B[0].instance_id = 'side_table_B_0'
side_table_C[0].instance_id = 'side_table_C_0'
side_table_D[0].instance_id = 'side_table_D_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'
walls[8].instance_id = 'walls_8'
walls[9].instance_id = 'walls_9'

dining_table_combination[0].position = [2.9354322519958633, 8.861294816410169, 0.39]
dining_table_combination[0].rotation = [0, 0, 0]
tv[0].position = [3.225984380462813, 1.8154444637091458, 0.42]
tv[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [0.68474617033527, 9.093736368407109, 0.25]
tv_cabinet[0].rotation = [0, 0, 0]
sofa_A[0].position = [5.618989235779109, 6.129257902264447, 0.425]
sofa_A[0].rotation = [0, 0, 0]
sofa_B[0].position = [1.9572444482333797, 11.250097214332458, 0.43]
sofa_B[0].rotation = [0, 0, 0]
wine_cabinet[0].position = [1.1642426648420399, 10.163114610742559, 0.95]
wine_cabinet[0].rotation = [0, 0, 0]
potted_bonsai[0].position = [4.118040749557128, 7.239664952599327, 0.625]
potted_bonsai[0].rotation = [0, 0, 0]
stool[0].position = [1.112883501112974, 7.703707690887499, 0.23]
stool[0].rotation = [0, 0, 0]
coffee_table[0].position = [1.8404430031345702, 9.781410178074907, 0.21]
coffee_table[0].rotation = [0, 0, 0]
side_table_A[0].position = [1.9497065866193708, 7.172805106999851, 0.275]
side_table_A[0].rotation = [0, 0, 0]
sofa_C[0].position = [0.6827778683961166, 6.141427318803575, 0.42]
sofa_C[0].rotation = [0, 0, 0]
side_table_B[0].position = [2.6099367540653438, 4.737708437908916, 0.26]
side_table_B[0].rotation = [0, 0, 0]
side_table_C[0].position = [0.6791327484193012, 3.2845483776296356, 0.275]
side_table_C[0].rotation = [0, 0, 0]
side_table_D[0].position = [0.4166110400728426, 7.075784975373126, 0.25]
side_table_D[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [2.9354322519958633, 8.861294816410169, 0.39]
dining_table_combination[0].rotation = [0, 0, 0]
tv[0].position = [3.225984380462813, 1.8154444637091458, 0.42]
tv[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [0.68474617033527, 9.093736368407109, 0.25]
tv_cabinet[0].rotation = [0, 0, 0]
sofa_A[0].position = [5.618989235779109, 6.129257902264447, 0.425]
sofa_A[0].rotation = [0, 0, 0]
sofa_B[0].position = [1.9572444482333797, 11.250097214332458, 0.43]
sofa_B[0].rotation = [0, 0, 0]
wine_cabinet[0].position = [1.1642426648420399, 10.163114610742559, 0.95]
wine_cabinet[0].rotation = [0, 0, 0]
potted_bonsai[0].position = [4.118040749557128, 7.239664952599327, 0.625]
potted_bonsai[0].rotation = [0, 0, 0]
stool[0].position = [1.112883501112974, 7.703707690887499, 0.23]
stool[0].rotation = [0, 0, 0]
coffee_table[0].position = [1.8404430031345702, 9.781410178074907, 0.21]
coffee_table[0].rotation = [0, 0, 0]
side_table_A[0].position = [1.9497065866193708, 7.172805106999851, 0.275]
side_table_A[0].rotation = [0, 0, 0]
sofa_C[0].position = [0.6827778683961166, 6.141427318803575, 0.42]
sofa_C[0].rotation = [0, 0, 0]
side_table_B[0].position = [2.6099367540653438, 4.737708437908916, 0.26]
side_table_B[0].rotation = [0, 0, 0]
side_table_C[0].position = [0.6791327484193012, 3.2845483776296356, 0.275]
side_table_C[0].rotation = [0, 0, 0]
side_table_D[0].position = [0.4166110400728426, 7.075784975373126, 0.25]
side_table_D[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed target points preserve the intended functional zones and circulation paths.
# The lower doorway area remains unobstructed; dining is in the central area and
# the living group occupies the upper part of the room.
dining_anchor = AssetInstance(position=[2.25, 4.80, 0.39])
tv_anchor = AssetInstance(position=[0.21, 9.20, 0.92])
tv_cabinet_anchor = AssetInstance(position=[0.21, 9.20, 0.25])
sofa_A_anchor = AssetInstance(position=[3.67, 9.20, 0.425])
sofa_B_anchor = AssetInstance(position=[2.40, 11.335, 0.43])
wine_cabinet_anchor = AssetInstance(position=[0.225, 4.45, 0.95])
bonsai_anchor = AssetInstance(position=[3.855, 7.30, 0.625])
stool_anchor = AssetInstance(position=[3.55, 4.40, 0.23])
coffee_table_anchor = AssetInstance(position=[2.10, 9.20, 0.21])
side_table_A_anchor = AssetInstance(position=[0.25, 7.65, 0.275])
sofa_C_anchor = AssetInstance(position=[2.35, 7.23, 0.42])
side_table_B_anchor = AssetInstance(position=[3.82, 7.82, 0.26])
side_table_C_anchor = AssetInstance(position=[0.25, 10.75, 0.275])
side_table_D_anchor = AssetInstance(position=[0.75, 11.30, 0.25])

# Dining and serving area. The long axis of the dining combination runs north-
# south, leaving circulation along the left and right sides of the room.
dining_table_combination[0].position = [2.25, 4.80, 0.39]
dining_table_combination[0].rotation = [0, 0, radians(0)]

wine_cabinet[0].position = [0.225, 4.45, 0.95]
wine_cabinet[0].rotation = [0, 0, radians(0)]

stool[0].position = [3.55, 4.40, 0.23]
stool[0].rotation = [0, 0, radians(180)]

# Upper living area. The television group is on the left wall and the main sofa
# is opposite it. The other sofas form the north and south sides of a U-shaped
# conversation group around the coffee table.
tv_cabinet[0].position = [0.21, 9.20, 0.25]
tv_cabinet[0].rotation = [0, 0, radians(0)]

tv[0].position = [0.21, 9.20, 0.92]
tv[0].rotation = [0, 0, radians(0)]

coffee_table[0].position = [2.10, 9.20, 0.21]
coffee_table[0].rotation = [0, 0, radians(0)]

sofa_A[0].position = [3.67, 9.20, 0.425]
sofa_A[0].rotation = [0, 0, radians(180)]

sofa_B[0].position = [2.40, 11.335, 0.43]
sofa_B[0].rotation = [0, 0, radians(-90)]

sofa_C[0].position = [2.35, 7.23, 0.42]
sofa_C[0].rotation = [0, 0, radians(90)]

# These two side tables flank the TV cabinet, so the cabinet remains between
# them along the left wall as required.
side_table_A[0].position = [0.25, 7.65, 0.275]
side_table_A[0].rotation = [0, 0, radians(0)]

side_table_C[0].position = [0.25, 10.75, 0.275]
side_table_C[0].rotation = [0, 0, radians(0)]

# The remaining side tables occupy open corners beside the seating group.
side_table_B[0].position = [3.82, 7.82, 0.26]
side_table_B[0].rotation = [0, 0, radians(180)]

side_table_D[0].position = [0.75, 11.30, 0.25]
side_table_D[0].rotation = [0, 0, radians(-90)]

# The bonsai is placed flush against the upper section of the right wall,
# outside the seating footprints.
potted_bonsai[0].position = [3.855, 7.30, 0.625]
potted_bonsai[0].rotation = [0, 0, radians(180)]

# High-weight fixed-point constraints retain the selected non-overlapping
# positions while allowing the solver to reconcile physical feasibility.
solver.distance_constraint(
    dining_table_combination[0], dining_anchor, 0, 0, weight=10
)
solver.align_with(dining_table_combination[0], dining_anchor, angle=0)

solver.distance_constraint(wine_cabinet[0], wine_cabinet_anchor, 0, 0, weight=10)
solver.against_wall(wine_cabinet[0], walls[5])
solver.align_with(wine_cabinet[0], wine_cabinet_anchor, angle=0)

solver.distance_constraint(stool[0], stool_anchor, 0, 0, weight=10)
solver.point_towards(stool[0], dining_table_combination[0])

# Preserve the wall-mounted media arrangement. The TV sits on the cabinet and
# both pieces face into the seating group.
solver.distance_constraint(tv_cabinet[0], tv_cabinet_anchor, 0, 0, weight=10)
solver.against_wall(tv_cabinet[0], walls[5])
solver.point_towards(tv_cabinet[0], sofa_A[0])

solver.on_top_of(tv[0], tv_cabinet[0])
solver.distance_constraint(tv[0], tv_anchor, 0, 0, weight=10)
solver.point_towards(tv[0], sofa_A[0])

solver.distance_constraint(coffee_table[0], coffee_table_anchor, 0, 0, weight=10)
solver.align_with(coffee_table[0], tv_cabinet[0], angle=0)

# Each sofa is anchored separately and directed toward the coffee table.
solver.distance_constraint(sofa_A[0], sofa_A_anchor, 0, 0, weight=10)
solver.against_wall(sofa_A[0], walls[3])
solver.point_towards(sofa_A[0], coffee_table[0])

solver.distance_constraint(sofa_B[0], sofa_B_anchor, 0, 0, weight=10)
solver.against_wall(sofa_B[0], walls[4])
solver.point_towards(sofa_B[0], coffee_table[0])

solver.distance_constraint(sofa_C[0], sofa_C_anchor, 0, 0, weight=10)
solver.point_towards(sofa_C[0], coffee_table[0])

# Side-table anchors preserve useful clearance from the sofa corners. The
# equal 1.55 m center distances below maintain the TV cabinet between A and C.
solver.distance_constraint(side_table_A[0], side_table_A_anchor, 0, 0, weight=10)
solver.against_wall(side_table_A[0], walls[5])
solver.distance_constraint(
    side_table_A[0], tv_cabinet[0], 1.55, 1.55, weight=5
)
solver.align_with(side_table_A[0], tv_cabinet[0], angle=0)

solver.distance_constraint(side_table_C[0], side_table_C_anchor, 0, 0, weight=10)
solver.against_wall(side_table_C[0], walls[5])
solver.distance_constraint(
    side_table_C[0], tv_cabinet[0], 1.55, 1.55, weight=5
)
solver.align_with(side_table_C[0], tv_cabinet[0], angle=0)

solver.distance_constraint(side_table_B[0], side_table_B_anchor, 0, 0, weight=10)
solver.align_with(side_table_B[0], sofa_A[0], angle=0)

solver.distance_constraint(side_table_D[0], side_table_D_anchor, 0, 0, weight=10)
solver.align_with(side_table_D[0], sofa_B[0], angle=0)

# The wall relationship is the primary semantic constraint for the bonsai.
solver.against_wall(potted_bonsai[0], walls[3])
solver.distance_constraint(
    potted_bonsai[0], bonsai_anchor, 0, 0, weight=10
)
solver.align_with(potted_bonsai[0], sofa_A[0], angle=0)

solver.constraints = []
sofa_C[0].position = [2.3499999046325684, 7.230000019073486, 0.41999998688697815]
sofa_C[0].rotation = [0, 0, 1.5802211042556205]
sofa_C[0].optimize = 2
stool[0].position = [3.549999952316284, 4.400000095367432, 0.23000000417232513]
stool[0].rotation = [0, 0, -3.1321678761290697]
stool[0].optimize = 2
potted_bonsai[0].position = [3.8807482719421387, 5.454680919647217, 0.625]
potted_bonsai[0].rotation = [0, 0, 3.1372907913538284]
potted_bonsai[0].optimize = 2
tv[0].position = [0.20999999344348907, 9.199999809265137, 0.9199999570846558]
tv[0].rotation = [0, 0, 0.01256637125682779]
tv[0].optimize = 2
sofa_B[0].position = [2.4000000953674316, 11.333000183105469, 0.4300000071525574]
sofa_B[0].rotation = [0, 0, -1.5707962815933025]
sofa_B[0].optimize = 2
dining_table_combination[0].position = [2.25, 4.800000190734863, 0.38999998569488525]
dining_table_combination[0].rotation = [0, 0, 0.01256637125682779]
dining_table_combination[0].optimize = 2
side_table_A[0].position = [0.24946139752864838, 7.650290012359619, 0.2750000059604645]
side_table_A[0].rotation = [0, 0, 4.2959567999997396e-08]
side_table_A[0].optimize = 2
sofa_A[0].position = [3.649954080581665, 9.199935913085938, 0.42500001192092896]
sofa_A[0].rotation = [0, 0, -3.1415926098543085]
sofa_A[0].optimize = 2
wine_cabinet[0].position = [0.22500000894069672, 4.449999809265137, 0.949999988079071]
wine_cabinet[0].rotation = [0, 0, 3.566019937831736e-08]
wine_cabinet[0].optimize = 2
coffee_table[0].position = [2.0999999046325684, 9.199999809265137, 0.20999999344348907]
coffee_table[0].rotation = [0, 0, 3.185507394111605e-08]
coffee_table[0].optimize = 2
side_table_C[0].position = [0.24946139752864838, 10.74970817565918, 0.2750000059604645]
side_table_C[0].rotation = [0, 0, 4.2959567999997396e-08]
side_table_C[0].optimize = 2
tv_cabinet[0].position = [0.20999999344348907, 9.199999809265137, 0.25]
tv_cabinet[0].rotation = [0, 0, 3.1790489744264924e-08]
tv_cabinet[0].optimize = 2
side_table_B[0].position = [3.819999933242798, 7.820000171661377, 0.25999999046325684]
side_table_B[0].rotation = [0, 0, -3.141592609954194]
side_table_B[0].optimize = 2
side_table_D[0].position = [0.75, 11.300000190734863, 0.25]
side_table_D[0].rotation = [0, 0, -1.5707963591327123]
side_table_D[0].optimize = 2

