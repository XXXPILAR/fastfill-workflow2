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
    Wall(corner1=[1.20, 6.34, 0.00], corner2=[0.00, 6.34, 0.00]),
    Wall(corner1=[0.00, 6.34, 0.00], corner2=[0.00, 5.24, 0.00]),
    Wall(corner1=[0.00, 5.24, 0.00], corner2=[1.20, 5.24, 0.00]),
    Wall(corner1=[1.20, 5.24, 0.00], corner2=[1.20, 0.00, 0.00]),
    Wall(corner1=[1.20, 0.00, 0.00], corner2=[5.20, 0.00, 0.00]),
    Wall(corner1=[5.20, 0.00, 0.00], corner2=[5.20, 4.14, 0.00]),
    Wall(corner1=[5.20, 4.14, 0.00], corner2=[6.40, 4.14, 0.00]),
    Wall(corner1=[6.40, 4.14, 0.00], corner2=[6.40, 5.44, 0.00]),
    Wall(corner1=[6.40, 5.44, 0.00], corner2=[5.00, 5.44, 0.00]),
    Wall(corner1=[5.00, 5.44, 0.00], corner2=[5.00, 7.84, 0.00]),
    Wall(corner1=[5.00, 7.84, 0.00], corner2=[7.40, 7.84, 0.00]),
    Wall(corner1=[7.40, 7.84, 0.00], corner2=[7.40, 8.94, 0.00]),
    Wall(corner1=[7.40, 8.94, 0.00], corner2=[1.20, 8.94, 0.00]),
    Wall(corner1=[1.20, 8.94, 0.00], corner2=[1.20, 6.34, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
shoe_cabinet = Assets(description="shoe cabinet", size=[0.35, 1.20, 1.05], placements=[AssetInstance() for _ in range(1)])
stool = Assets(description="stool", size=[0.42, 0.42, 0.46], placements=[AssetInstance() for _ in range(1)])
side_table_A = Assets(description="side table", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
sofa_A = Assets(description="sofa", size=[0.95, 2.40, 0.85], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="coffee table", size=[0.65, 1.20, 0.42], placements=[AssetInstance() for _ in range(1)])
wine_cabinet = Assets(description="wine cabinet", size=[0.45, 1.00, 1.80], placements=[AssetInstance() for _ in range(1)])
bathroom_cabinet = Assets(description="bathroom cabinet", size=[0.45, 1.20, 0.85], placements=[AssetInstance() for _ in range(1)])
sofa_B = Assets(description="sofa", size=[0.95, 2.20, 0.85], placements=[AssetInstance() for _ in range(1)])
side_table_B = Assets(description="side table", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
dining_table_combination = Assets(description="dining table combination", size=[1.80, 2.40, 0.78], placements=[AssetInstance() for _ in range(1)])

shoe_cabinet[0].instance_id = 'shoe_cabinet_0'
stool[0].instance_id = 'stool_0'
side_table_A[0].instance_id = 'side_table_A_0'
sofa_A[0].instance_id = 'sofa_A_0'
coffee_table[0].instance_id = 'coffee_table_0'
wine_cabinet[0].instance_id = 'wine_cabinet_0'
bathroom_cabinet[0].instance_id = 'bathroom_cabinet_0'
sofa_B[0].instance_id = 'sofa_B_0'
side_table_B[0].instance_id = 'side_table_B_0'
dining_table_combination[0].instance_id = 'dining_table_combination_0'
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

shoe_cabinet[0].position = [3.994148822321358, 2.195329862141998, 0.525]
shoe_cabinet[0].rotation = [0, 0, 0]
stool[0].position = [1.8531934893572088, 8.224084987896095, 0.23]
stool[0].rotation = [0, 0, 0]
side_table_A[0].position = [3.1627274087102224, 6.833970294408527, 0.275]
side_table_A[0].rotation = [0, 0, 0]
sofa_A[0].position = [3.143466764015946, 3.482808361283498, 0.425]
sofa_A[0].rotation = [0, 0, 0]
coffee_table[0].position = [4.539652540629022, 2.931888596093257, 0.21]
coffee_table[0].rotation = [0, 0, 0]
wine_cabinet[0].position = [1.8341911649621738, 6.820391191020083, 0.9]
wine_cabinet[0].rotation = [0, 0, 0]
bathroom_cabinet[0].position = [1.470951256106643, 1.471829903075478, 0.425]
bathroom_cabinet[0].rotation = [0, 0, 0]
sofa_B[0].position = [5.098498581061765, 0.1035607060819296, 0.425]
sofa_B[0].rotation = [0, 0, 0]
side_table_B[0].position = [4.368341574849259, 6.2635876336873055, 0.275]
side_table_B[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [1.8881703059336452, 4.580056586772822, 0.39]
dining_table_combination[0].rotation = [0, 0, 0]
shoe_cabinet[0].position = [3.994148822321358, 2.195329862141998, 0.525]
shoe_cabinet[0].rotation = [0, 0, 0]
stool[0].position = [1.8531934893572088, 8.224084987896095, 0.23]
stool[0].rotation = [0, 0, 0]
side_table_A[0].position = [3.1627274087102224, 6.833970294408527, 0.275]
side_table_A[0].rotation = [0, 0, 0]
sofa_A[0].position = [3.143466764015946, 3.482808361283498, 0.425]
sofa_A[0].rotation = [0, 0, 0]
coffee_table[0].position = [4.539652540629022, 2.931888596093257, 0.21]
coffee_table[0].rotation = [0, 0, 0]
wine_cabinet[0].position = [1.8341911649621738, 6.820391191020083, 0.9]
wine_cabinet[0].rotation = [0, 0, 0]
bathroom_cabinet[0].position = [1.470951256106643, 1.471829903075478, 0.425]
bathroom_cabinet[0].rotation = [0, 0, 0]
sofa_B[0].position = [5.098498581061765, 0.1035607060819296, 0.425]
sofa_B[0].rotation = [0, 0, 0]
side_table_B[0].position = [4.368341574849259, 6.2635876336873055, 0.275]
side_table_B[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [1.8881703059336452, 4.580056586772822, 0.39]
dining_table_combination[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed anchors preserve the planned zones and keep all door approaches clear.
shoe_anchor = AssetInstance(position=[6.78, 8.765, 0.525])
stool_anchor = AssetInstance(position=[6.80, 8.10, 0.23])
side_table_A_anchor = AssetInstance(position=[1.45, 1.00, 0.275])
sofa_A_anchor = AssetInstance(position=[1.675, 2.65, 0.425])
coffee_table_anchor = AssetInstance(position=[3.05, 2.65, 0.21])
wine_cabinet_anchor = AssetInstance(position=[4.975, 2.35, 0.90])
bathroom_cabinet_anchor = AssetInstance(position=[2.70, 6.10, 0.425])
sofa_B_anchor = AssetInstance(position=[2.70, 8.465, 0.425])
side_table_B_anchor = AssetInstance(position=[1.45, 4.30, 0.275])
dining_anchor = AssetInstance(position=[4.00, 4.85, 0.39])

# A zero-rotation reference allows absolute orientations to be represented
# through orientation constraints.
orientation_reference = AssetInstance(rotation=[0, 0, 0])

# Initial placements. Sofa A forms a living group along the lower-left wall.
# The second sofa is placed along the upper wall, clear of both upper doors.
shoe_cabinet[0].position = [6.78, 8.765, 0.525]
shoe_cabinet[0].rotation = [0, 0, radians(-90)]

stool[0].position = [6.80, 8.10, 0.23]
stool[0].rotation = [0, 0, radians(90)]

side_table_A[0].position = [1.45, 1.00, 0.275]
side_table_A[0].rotation = [0, 0, 0]

sofa_A[0].position = [1.675, 2.65, 0.425]
sofa_A[0].rotation = [0, 0, 0]

coffee_table[0].position = [3.05, 2.65, 0.21]
coffee_table[0].rotation = [0, 0, 0]

wine_cabinet[0].position = [4.975, 2.35, 0.90]
wine_cabinet[0].rotation = [0, 0, radians(180)]

bathroom_cabinet[0].position = [2.70, 6.10, 0.425]
bathroom_cabinet[0].rotation = [0, 0, radians(90)]

sofa_B[0].position = [2.70, 8.465, 0.425]
sofa_B[0].rotation = [0, 0, radians(-90)]

side_table_B[0].position = [1.45, 4.30, 0.275]
side_table_B[0].rotation = [0, 0, 0]

dining_table_combination[0].position = [4.00, 4.85, 0.39]
dining_table_combination[0].rotation = [0, 0, radians(90)]

# High-priority position constraints establish the non-overlapping layout.
solver.distance_constraint(
    shoe_cabinet[0], shoe_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    stool[0], stool_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    side_table_A[0], side_table_A_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    sofa_A[0], sofa_A_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    coffee_table[0], coffee_table_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    wine_cabinet[0], wine_cabinet_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    bathroom_cabinet[0], bathroom_cabinet_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    sofa_B[0], sofa_B_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    side_table_B[0], side_table_B_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    dining_table_combination[0], dining_anchor, 0, 0, weight=10
)

# Wall relationships keep the storage pieces and lower living group at the
# perimeter. The shoe cabinet uses the upper wall segment to avoid the nearby
# 0.85 m doorway.
solver.against_wall(shoe_cabinet[0], walls[12])
solver.against_wall(side_table_A[0], walls[3])
solver.against_wall(sofa_A[0], walls[3])
solver.against_wall(side_table_B[0], walls[3])
solver.against_wall(wine_cabinet[0], walls[5])
solver.against_wall(sofa_B[0], walls[12])

# Sofa A is centered between the two side tables. These secondary constraints
# preserve the intended grouping if physical-feasibility adjustments are made.
solver.distance_constraint(
    side_table_A[0], sofa_A[0], 1.60, 1.70, weight=1
)
solver.distance_constraint(
    side_table_B[0], sofa_A[0], 1.60, 1.70, weight=1
)

# Keep the coffee table in front of Sofa A with usable circulation space.
solver.distance_constraint(
    coffee_table[0], sofa_A[0], 1.30, 1.45, weight=1
)

# Keep the entry stool close to its associated shoe cabinet without overlap.
solver.distance_constraint(
    stool[0], shoe_cabinet[0], 0.60, 0.75, weight=1
)

# Preserve the facing relationship requested for Sofa B and the bathroom
# cabinet. Their shared x-coordinate makes Sofa B face directly toward it.
solver.distance_constraint(
    sofa_B[0], bathroom_cabinet[0], 2.30, 2.45, weight=1
)

# Orientation constraints for every new asset.
solver.align_with(shoe_cabinet[0], orientation_reference, angle=-90)
solver.point_towards(stool[0], shoe_cabinet[0])

solver.align_with(sofa_A[0], orientation_reference, angle=0)
solver.align_with(side_table_A[0], sofa_A[0], angle=0)
solver.align_with(side_table_B[0], sofa_A[0], angle=0)
solver.align_with(coffee_table[0], sofa_A[0], angle=0)

solver.align_with(wine_cabinet[0], orientation_reference, angle=180)
solver.align_with(bathroom_cabinet[0], orientation_reference, angle=90)
solver.point_towards(sofa_B[0], bathroom_cabinet[0])

solver.align_with(
    dining_table_combination[0], orientation_reference, angle=90
)

solver.constraints = []
stool[0].position = [6.800000190734863, 8.100000381469727, 0.23000000417232513]
stool[0].rotation = [0, 0, 1.5833626980517244]
stool[0].optimize = 2
shoe_cabinet[0].position = [6.78000020980835, 8.765375137329102, 0.5249999761581421]
shoe_cabinet[0].rotation = [0, 0, -1.5707968553148417]
shoe_cabinet[0].optimize = 2
bathroom_cabinet[0].position = [2.700000047683716, 6.099999904632568, 0.42500001192092896]
bathroom_cabinet[0].rotation = [0, 0, 1.586504290712113]
bathroom_cabinet[0].optimize = 2
sofa_B[0].position = [2.700000047683716, 8.465373992919922, 0.42500001192092896]
sofa_B[0].rotation = [0, 0, -1.5707957585017436]
sofa_B[0].optimize = 2
side_table_A[0].position = [1.4497500658035278, 1.0, 0.2750000059604645]
side_table_A[0].rotation = [0, 0, 5.831619980556526e-07]
side_table_A[0].optimize = 2
dining_table_combination[0].position = [3.8082852363586426, 4.849999904632568, 0.38999998569488525]
dining_table_combination[0].rotation = [0, 0, 1.5802211042556205]
dining_table_combination[0].optimize = 2
sofa_A[0].position = [1.6747500896453857, 2.6500000953674316, 0.42500001192092896]
sofa_A[0].rotation = [0, 0, 6.302939612761491e-07]
sofa_A[0].optimize = 2
coffee_table[0].position = [3.049999952316284, 2.6500000953674316, 0.20999999344348907]
coffee_table[0].rotation = [0, 0, 1.4306462419333295e-06]
coffee_table[0].optimize = 2
wine_cabinet[0].position = [4.974999904632568, 2.3499999046325684, 0.8999999761581421]
wine_cabinet[0].rotation = [0, 0, 3.1415924443793317]
wine_cabinet[0].optimize = 2
side_table_B[0].position = [1.4500000476837158, 4.300000190734863, 0.2750000059604645]
side_table_B[0].rotation = [0, 0, 1.570446081148792]
side_table_B[0].optimize = 2

