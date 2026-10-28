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
    Wall(corner1=[7.72, 3.66, 0.00], corner2=[7.72, 7.46, 0.00]),
    Wall(corner1=[7.72, 7.46, 0.00], corner2=[4.02, 7.46, 0.00]),
    Wall(corner1=[4.02, 7.46, 0.00], corner2=[4.02, 3.66, 0.00]),
    Wall(corner1=[4.02, 3.66, 0.00], corner2=[3.82, 3.66, 0.00]),
    Wall(corner1=[3.82, 3.66, 0.00], corner2=[3.82, 4.26, 0.00]),
    Wall(corner1=[3.82, 4.26, 0.00], corner2=[1.23, 4.26, 0.00]),
    Wall(corner1=[1.23, 4.26, 0.00], corner2=[1.23, 3.66, 0.00]),
    Wall(corner1=[1.23, 3.66, 0.00], corner2=[0.00, 3.66, 0.00]),
    Wall(corner1=[0.00, 3.66, 0.00], corner2=[0.00, 2.55, 0.00]),
    Wall(corner1=[0.00, 2.55, 0.00], corner2=[4.76, 2.55, 0.00]),
    Wall(corner1=[4.76, 2.55, 0.00], corner2=[4.76, 0.00, 0.00]),
    Wall(corner1=[4.76, 0.00, 0.00], corner2=[7.72, 0.00, 0.00]),
    Wall(corner1=[7.72, 0.00, 0.00], corner2=[7.72, 2.26, 0.00]),
    Wall(corner1=[7.72, 2.26, 0.00], corner2=[12.16, 2.26, 0.00]),
    Wall(corner1=[12.16, 2.26, 0.00], corner2=[12.16, 3.66, 0.00]),
    Wall(corner1=[12.16, 3.66, 0.00], corner2=[10.57, 3.66, 0.00]),
    Wall(corner1=[10.57, 3.66, 0.00], corner2=[10.57, 4.00, 0.00]),
    Wall(corner1=[10.57, 4.00, 0.00], corner2=[8.02, 4.00, 0.00]),
    Wall(corner1=[8.02, 4.00, 0.00], corner2=[8.02, 3.66, 0.00]),
    Wall(corner1=[8.02, 3.66, 0.00], corner2=[7.72, 3.66, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
sofa_A = Assets(description="sofa", size=[0.95, 2.40, 0.85], placements=[AssetInstance() for _ in range(1)])
sofa_B = Assets(description="sofa", size=[0.90, 2.10, 0.85], placements=[AssetInstance() for _ in range(1)])
stool = Assets(description="stool", size=[0.45, 0.45, 0.48], placements=[AssetInstance() for _ in range(1)])
carpet_A = Assets(description="carpet", size=[2.40, 3.60, 0.02], placements=[AssetInstance() for _ in range(1)])
dining_table_combination = Assets(description="dining table combination", size=[2.40, 3.20, 0.80], placements=[AssetInstance() for _ in range(1)])
sofa_C = Assets(description="sofa", size=[0.95, 2.40, 0.85], placements=[AssetInstance() for _ in range(1)])
wine_cabinet = Assets(description="wine cabinet", size=[0.45, 1.20, 1.80], placements=[AssetInstance() for _ in range(1)])
side_table_A = Assets(description="side table", size=[0.55, 0.55, 0.55], placements=[AssetInstance() for _ in range(1)])
carpet_B = Assets(description="carpet", size=[2.00, 2.80, 0.02], placements=[AssetInstance() for _ in range(1)])
side_table_B = Assets(description="side table", size=[0.55, 0.55, 0.55], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.60, 2.00, 2.40], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="coffee table", size=[0.75, 1.40, 0.42], placements=[AssetInstance() for _ in range(1)])

sofa_A[0].instance_id = 'sofa_A_0'
sofa_B[0].instance_id = 'sofa_B_0'
stool[0].instance_id = 'stool_0'
carpet_A[0].instance_id = 'carpet_A_0'
dining_table_combination[0].instance_id = 'dining_table_combination_0'
sofa_C[0].instance_id = 'sofa_C_0'
wine_cabinet[0].instance_id = 'wine_cabinet_0'
side_table_A[0].instance_id = 'side_table_A_0'
carpet_B[0].instance_id = 'carpet_B_0'
side_table_B[0].instance_id = 'side_table_B_0'
wardrobe[0].instance_id = 'wardrobe_0'
coffee_table[0].instance_id = 'coffee_table_0'
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
walls[10].instance_id = 'walls_10'
walls[11].instance_id = 'walls_11'
walls[12].instance_id = 'walls_12'
walls[13].instance_id = 'walls_13'
walls[14].instance_id = 'walls_14'
walls[15].instance_id = 'walls_15'
walls[16].instance_id = 'walls_16'
walls[17].instance_id = 'walls_17'
walls[18].instance_id = 'walls_18'
walls[19].instance_id = 'walls_19'

sofa_A[0].position = [10.471324618378867, 3.2297658368150546, 0.425]
sofa_A[0].rotation = [0, 0, 0]
sofa_B[0].position = [6.1728882639477005, 2.4919307231700736, 0.425]
sofa_B[0].rotation = [0, 0, 0]
stool[0].position = [7.131798690008302, 5.403276475256194, 0.24]
stool[0].rotation = [0, 0, 0]
carpet_A[0].position = [8.317370723169208, 3.3491383723969776, 0.01]
carpet_A[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [6.433686591342861, 0.14740570696498811, 0.4]
dining_table_combination[0].rotation = [0, 0, 0]
sofa_C[0].position = [7.410213876428865, 2.9314434936499167, 0.425]
sofa_C[0].rotation = [0, 0, 0]
wine_cabinet[0].position = [5.060129920880143, 6.306345577309658, 0.9]
wine_cabinet[0].rotation = [0, 0, 0]
side_table_A[0].position = [6.3947088499475795, 3.8961625123818746, 0.275]
side_table_A[0].rotation = [0, 0, 0]
carpet_B[0].position = [3.6945385493214724, 3.62898561475323, 0.01]
carpet_B[0].rotation = [0, 0, 0]
side_table_B[0].position = [2.5860284331003616, 4.170446065964447, 0.275]
side_table_B[0].rotation = [0, 0, 0]
wardrobe[0].position = [4.945423936951514, 1.2846187416569856, 1.2]
wardrobe[0].rotation = [0, 0, 0]
coffee_table[0].position = [10.18394327050372, 3.8364576247453948, 0.21]
coffee_table[0].rotation = [0, 0, 0]
sofa_A[0].position = [10.471324618378867, 3.2297658368150546, 0.425]
sofa_A[0].rotation = [0, 0, 0]
sofa_B[0].position = [6.1728882639477005, 2.4919307231700736, 0.425]
sofa_B[0].rotation = [0, 0, 0]
stool[0].position = [7.131798690008302, 5.403276475256194, 0.24]
stool[0].rotation = [0, 0, 0]
carpet_A[0].position = [8.317370723169208, 3.3491383723969776, 0.01]
carpet_A[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [6.433686591342861, 0.14740570696498811, 0.4]
dining_table_combination[0].rotation = [0, 0, 0]
sofa_C[0].position = [7.410213876428865, 2.9314434936499167, 0.425]
sofa_C[0].rotation = [0, 0, 0]
wine_cabinet[0].position = [5.060129920880143, 6.306345577309658, 0.9]
wine_cabinet[0].rotation = [0, 0, 0]
side_table_A[0].position = [6.3947088499475795, 3.8961625123818746, 0.275]
side_table_A[0].rotation = [0, 0, 0]
carpet_B[0].position = [3.6945385493214724, 3.62898561475323, 0.01]
carpet_B[0].rotation = [0, 0, 0]
side_table_B[0].position = [2.5860284331003616, 4.170446065964447, 0.275]
side_table_B[0].rotation = [0, 0, 0]
wardrobe[0].position = [4.945423936951514, 1.2846187416569856, 1.2]
wardrobe[0].rotation = [0, 0, 0]
coffee_table[0].position = [10.18394327050372, 3.8364576247453948, 0.21]
coffee_table[0].rotation = [0, 0, 0]

solver.constraints = []

# Create fixed anchors so the intended arrangement remains stable while the
# solver makes small adjustments for physical feasibility.
living_center = AssetInstance(position=[5.87, 4.95, 0.01])
dining_center = AssetInstance(position=[5.87, 1.85, 0.01])
stool_anchor = AssetInstance(position=[3.35, 3.05, 0.24])
side_table_A_anchor = AssetInstance(position=[4.48, 3.43, 0.275])
side_table_B_anchor = AssetInstance(position=[7.26, 3.43, 0.275])

# The living group occupies the upper-central area. Keeping its northern edge
# near y=6.15 leaves an approximately 1.3 m-deep clear landing at the large
# door on the north wall. The two sofas oppose one another with the coffee
# table centered between them.
sofa_A[0].position = [4.52, 4.95, 0.425]
sofa_A[0].rotation = [0, 0, radians(0)]

sofa_C[0].position = [7.22, 4.95, 0.425]
sofa_C[0].rotation = [0, 0, radians(180)]

coffee_table[0].position = [5.87, 4.95, 0.21]
coffee_table[0].rotation = [0, 0, radians(0)]

carpet_A[0].position = [5.87, 4.95, 0.01]
carpet_A[0].rotation = [0, 0, radians(90)]

# Place the dining group crosswise in the lower-central room. This orientation
# fits its long dimension within the 3.70 m room width. Its center is biased
# slightly northward to retain a landing inside the south doorway.
dining_table_combination[0].position = [5.87, 1.85, 0.40]
dining_table_combination[0].rotation = [0, 0, radians(90)]

carpet_B[0].position = [5.87, 1.85, 0.01]
carpet_B[0].rotation = [0, 0, radians(90)]

# The compact tables sit in the gap between the dining and living zones,
# beside the southern ends of the sofas. They do not overlap either carpet.
side_table_A[0].position = [4.48, 3.43, 0.275]
side_table_A[0].rotation = [0, 0, radians(0)]

side_table_B[0].position = [7.26, 3.43, 0.275]
side_table_B[0].rotation = [0, 0, radians(180)]

# Put the stool in the left wing, away from all three nearby door landings.
stool[0].position = [3.35, 3.05, 0.24]
stool[0].rotation = [0, 0, radians(90)]

# Tall storage is distributed between the side wings. The wardrobe is placed
# along the solid upper wall of the left wing, clear of the fixed cabinet at
# (4.18, 7.06). The new wine cabinet uses the solid upper-right wall and stays
# away from the door in the right boundary.
wardrobe[0].position = [2.65, 3.96, 1.20]
wardrobe[0].rotation = [0, 0, radians(90)]

wine_cabinet[0].position = [11.15, 3.435, 0.90]
wine_cabinet[0].rotation = [0, 0, radians(90)]


# --- Primary placement and orientation constraints ---

# Anchor the rug first, then preserve the opposing-sofa living composition.
solver.distance_constraint(
    carpet_A[0], living_center, 0.0, 0.0, weight=10
)
solver.align_with(carpet_A[0], coffee_table[0], angle=90)

solver.against_wall(sofa_A[0], walls[2])
solver.point_towards(sofa_A[0], coffee_table[0])
solver.distance_constraint(
    sofa_A[0], coffee_table[0], 1.35, 1.35, weight=10
)

solver.against_wall(sofa_C[0], walls[0])
solver.point_towards(sofa_C[0], coffee_table[0])
solver.distance_constraint(
    sofa_C[0], coffee_table[0], 1.35, 1.35, weight=10
)

# These two equal-distance constraints keep the coffee table centered between
# sofa_A (o0000) and sofa_C (o0005), as required.
solver.distance_constraint(
    coffee_table[0], sofa_A[0], 1.35, 1.35, weight=10
)
solver.distance_constraint(
    coffee_table[0], sofa_C[0], 1.35, 1.35, weight=10
)
solver.align_with(coffee_table[0], sofa_A[0], angle=0)

# Keep the dining combination centered on its rug and maintain their shared
# crosswise orientation.
solver.distance_constraint(
    carpet_B[0], dining_center, 0.0, 0.0, weight=10
)
solver.align_with(carpet_B[0], dining_table_combination[0], angle=0)

solver.distance_constraint(
    dining_table_combination[0], dining_center, 0.0, 0.0, weight=10
)
solver.align_with(dining_table_combination[0], carpet_B[0], angle=0)

# Preserve the small furniture positions and orient them consistently with
# their associated zones.
solver.distance_constraint(
    side_table_A[0], side_table_A_anchor, 0.0, 0.0, weight=10
)
solver.align_with(side_table_A[0], sofa_A[0], angle=0)

solver.distance_constraint(
    side_table_B[0], side_table_B_anchor, 0.0, 0.0, weight=10
)
solver.align_with(side_table_B[0], sofa_C[0], angle=0)

solver.distance_constraint(
    stool[0], stool_anchor, 0.0, 0.0, weight=10
)
solver.align_with(stool[0], dining_table_combination[0], angle=0)

# Wall constraints secure the tall assets, while orientation constraints keep
# their broad backs parallel to the corresponding horizontal wall segments.
solver.against_wall(wardrobe[0], walls[5])
solver.align_with(wardrobe[0], dining_table_combination[0], angle=0)

solver.against_wall(wine_cabinet[0], walls[15])
solver.align_with(wine_cabinet[0], wardrobe[0], angle=0)

solver.constraints = []
sofa_C[0].position = [7.2343244552612305, 4.949999809265137, 0.42500001192092896]
sofa_C[0].rotation = [0, 0, -3.1415383669430157]
sofa_C[0].optimize = 2
carpet_B[0].position = [6.1473236083984375, 1.850000023841858, 0.009999999776482582]
carpet_B[0].rotation = [0, 0, 1.5850606191481922]
carpet_B[0].optimize = 2
sofa_A[0].position = [4.511086940765381, 4.949999809265137, 0.42500001192092896]
sofa_A[0].rotation = [0, 0, -3.309866047369017e-05]
sofa_A[0].optimize = 2
side_table_A[0].position = [4.480000019073486, 3.430000066757202, 0.2750000059604645]
side_table_A[0].rotation = [0, 0, -0.00024329433596759242]
side_table_A[0].optimize = 2
side_table_B[0].position = [7.260000228881836, 3.430000066757202, 0.2750000059604645]
side_table_B[0].rotation = [0, 0, -3.1413998946506383]
side_table_B[0].optimize = 2
dining_table_combination[0].position = [6.102967262268066, 1.850000023841858, 0.4000000059604645]
dining_table_combination[0].rotation = [0, 0, 1.5851276213028178]
dining_table_combination[0].optimize = 2
coffee_table[0].position = [5.873047351837158, 4.949999809265137, 0.20999999344348907]
coffee_table[0].rotation = [0, 0, -0.0007029331144688056]
coffee_table[0].optimize = 2
carpet_A[0].position = [5.869999885559082, 4.949999809265137, 0.009999999776482582]
carpet_A[0].rotation = [0, 0, 1.571576401288235]
carpet_A[0].optimize = 2
wine_cabinet[0].position = [11.149999618530273, 3.0255537033081055, 0.8999999761581421]
wine_cabinet[0].rotation = [0, 0, -2.923762045740808]
wine_cabinet[0].optimize = 2
wardrobe[0].position = [2.6500000953674316, 3.461296319961548, 1.2000000476837158]
wardrobe[0].rotation = [0, 0, -2.9232935232026547]
wardrobe[0].optimize = 2
sofa_B[0].position = [6.172888278961182, 2.4919307231903076, 0.42500001192092896]
sofa_B[0].rotation = [0, 0, 0.00314159280673765]
sofa_B[0].optimize = 2
stool[0].position = [3.3499999046325684, 3.049999952316284, 0.23999999463558197]
stool[0].rotation = [0, 0, 1.5850798683700897]
stool[0].optimize = 2

