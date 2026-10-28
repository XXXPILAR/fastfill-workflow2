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
    Wall(corner1=[0.68, 1.86, 0.00], corner2=[0.00, 1.86, 0.00]),
    Wall(corner1=[0.00, 1.86, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[5.15, 0.00, 0.00]),
    Wall(corner1=[5.15, 0.00, 0.00], corner2=[5.15, 1.86, 0.00]),
    Wall(corner1=[5.15, 1.86, 0.00], corner2=[4.47, 1.86, 0.00]),
    Wall(corner1=[4.47, 1.86, 0.00], corner2=[0.68, 1.86, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
washing_machine = Assets(description="washing machine", size=[0.65, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
chair = Assets(description="chair", size=[0.55, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
high_chair_A = Assets(description="high chair", size=[0.50, 0.45, 1.05], placements=[AssetInstance() for _ in range(1)])
bar_counter = Assets(description="bar counter", size=[0.60, 1.80, 1.05], placements=[AssetInstance() for _ in range(1)])
pool = Assets(description="pool", size=[1.27, 2.54, 0.80], placements=[AssetInstance() for _ in range(1)])
high_chair_B = Assets(description="high chair", size=[0.50, 0.45, 1.05], placements=[AssetInstance() for _ in range(1)])
basin_cabinet = Assets(description="basin cabinet", size=[0.50, 0.80, 0.85], placements=[AssetInstance() for _ in range(1)])
side_table = Assets(description="side table", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])

washing_machine[0].instance_id = 'washing_machine_0'
chair[0].instance_id = 'chair_0'
high_chair_A[0].instance_id = 'high_chair_A_0'
bar_counter[0].instance_id = 'bar_counter_0'
pool[0].instance_id = 'pool_0'
high_chair_B[0].instance_id = 'high_chair_B_0'
basin_cabinet[0].instance_id = 'basin_cabinet_0'
side_table[0].instance_id = 'side_table_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

washing_machine[0].position = [4.356230966977771, 0.21286804284007413, 0.425]
washing_machine[0].rotation = [0, 0, 0]
chair[0].position = [5.093048981894589, 1.7925816563774355, 0.425]
chair[0].rotation = [0, 0, 0]
high_chair_A[0].position = [2.6396807646124523, 1.7887841564313856, 0.525]
high_chair_A[0].rotation = [0, 0, 0]
bar_counter[0].position = [5.137580212571019, 1.1631371072937369, 0.525]
bar_counter[0].rotation = [0, 0, 0]
pool[0].position = [1.810190758263254, 0.85935737032779, 0.4]
pool[0].rotation = [0, 0, 0]
high_chair_B[0].position = [3.8684415791371642, 1.848309507008079, 0.525]
high_chair_B[0].rotation = [0, 0, 0]
basin_cabinet[0].position = [0.6720927819403302, 1.0344255923006533, 0.425]
basin_cabinet[0].rotation = [0, 0, 0]
side_table[0].position = [3.172928673004105, 1.0021286606632862, 0.275]
side_table[0].rotation = [0, 0, 0]
washing_machine[0].position = [4.356230966977771, 0.21286804284007413, 0.425]
washing_machine[0].rotation = [0, 0, 0]
chair[0].position = [5.093048981894589, 1.7925816563774355, 0.425]
chair[0].rotation = [0, 0, 0]
high_chair_A[0].position = [2.6396807646124523, 1.7887841564313856, 0.525]
high_chair_A[0].rotation = [0, 0, 0]
bar_counter[0].position = [5.137580212571019, 1.1631371072937369, 0.525]
bar_counter[0].rotation = [0, 0, 0]
pool[0].position = [1.810190758263254, 0.85935737032779, 0.4]
pool[0].rotation = [0, 0, 0]
high_chair_B[0].position = [3.8684415791371642, 1.848309507008079, 0.525]
high_chair_B[0].rotation = [0, 0, 0]
basin_cabinet[0].position = [0.6720927819403302, 1.0344255923006533, 0.425]
basin_cabinet[0].rotation = [0, 0, 0]
side_table[0].position = [3.172928673004105, 1.0021286606632862, 0.275]
side_table[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the large pieces along the windowed lower edge. Rotating the pool and
# counter by 90 degrees makes their long dimensions run along the room's x-axis.
# The central doorway retains an approximately 0.59 m deep unobstructed strip.
washing_machine.placements[0] = AssetInstance(
    position=[0.325, 1.535, 0.425],
    rotation=[0, 0, radians(0)],
)
basin_cabinet.placements[0] = AssetInstance(
    position=[0.250, 0.820, 0.425],
    rotation=[0, 0, radians(0)],
)
side_table.placements[0] = AssetInstance(
    position=[1.000, 1.575, 0.275],
    rotation=[0, 0, radians(0)],
)
bar_counter.placements[0] = AssetInstance(
    position=[1.400, 0.300, 0.525],
    rotation=[0, 0, radians(90)],
)
pool.placements[0] = AssetInstance(
    position=[3.790, 0.635, 0.400],
    rotation=[0, 0, radians(90)],
)

# Place the seats on the working side of the counter. Their footprints remain
# separated from one another, the counter, and the pool.
high_chair_A.placements[0] = AssetInstance(
    position=[0.900, 0.900, 0.525],
    rotation=[0, 0, radians(-50.2)],
)
high_chair_B.placements[0] = AssetInstance(
    position=[1.500, 0.900, 0.525],
    rotation=[0, 0, radians(-99.5)],
)
chair.placements[0] = AssetInstance(
    position=[2.100, 0.900, 0.425],
    rotation=[0, 0, radians(-139.4)],
)

# High-priority position constraints preserve the packed, non-overlapping
# arrangement and keep furniture out of the immediate doorway strip.
washing_machine_anchor = AssetInstance(position=[0.325, 1.535, 0.425])
basin_cabinet_anchor = AssetInstance(position=[0.250, 0.820, 0.425])
side_table_anchor = AssetInstance(position=[1.000, 1.575, 0.275])
bar_counter_anchor = AssetInstance(position=[1.400, 0.300, 0.525])
pool_anchor = AssetInstance(position=[3.790, 0.635, 0.400])
high_chair_A_anchor = AssetInstance(position=[0.900, 0.900, 0.525])
high_chair_B_anchor = AssetInstance(position=[1.500, 0.900, 0.525])
chair_anchor = AssetInstance(position=[2.100, 0.900, 0.425])

solver.distance_constraint(
    washing_machine[0], washing_machine_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    basin_cabinet[0], basin_cabinet_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    side_table[0], side_table_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    bar_counter[0], bar_counter_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    pool[0], pool_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    high_chair_A[0], high_chair_A_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    high_chair_B[0], high_chair_B_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    chair[0], chair_anchor, 0, 0, weight=10
)

# Reinforce the intended wall relationships after the exact position
# constraints. These pieces are flush with their respective boundary walls.
solver.against_wall(washing_machine[0], walls[1])
solver.against_wall(basin_cabinet[0], walls[1])
solver.against_wall(bar_counter[0], walls[2])
solver.against_wall(pool[0], walls[2])

# Orientation constraints for every new asset. The counter faces its seating,
# and both high chairs face the counter.
zero_heading = AssetInstance(rotation=[0, 0, 0])
solver.align_with(washing_machine[0], zero_heading, angle=0)
solver.align_with(basin_cabinet[0], zero_heading, angle=0)
solver.align_with(side_table[0], zero_heading, angle=0)
solver.align_with(bar_counter[0], zero_heading, angle=90)
solver.align_with(pool[0], zero_heading, angle=90)
solver.point_towards(high_chair_A[0], bar_counter[0])
solver.point_towards(high_chair_B[0], bar_counter[0])

# Required semantic relationship: the ordinary chair faces the bar counter.
solver.point_towards(chair[0], bar_counter[0])

# Maintain practical seating distances if physical-feasibility adjustments
# slightly perturb the exact initial arrangement.
solver.distance_constraint(
    chair[0], bar_counter[0], 0.85, 1.05, weight=1
)
solver.distance_constraint(
    high_chair_A[0], bar_counter[0], 0.72, 0.85, weight=1
)
solver.distance_constraint(
    high_chair_B[0], bar_counter[0], 0.55, 0.70, weight=1
)

solver.constraints = []
washing_machine[0].position = [0.3236248195171356, 1.534999966621399, 0.42500001192092896]
washing_machine[0].rotation = [0, 0, 0.00421914543660421]
washing_machine[0].optimize = 2
high_chair_B[0].position = [1.5, 0.8999999761581421, 0.5249999761581421]
high_chair_B[0].rotation = [0, 0, -1.724036228723161]
high_chair_B[0].optimize = 2
side_table[0].position = [1.0, 1.5750000476837158, 0.2750000059604645]
side_table[0].rotation = [0, 0, 0.00942477746072377]
side_table[0].optimize = 2
high_chair_A[0].position = [0.8999999761581421, 0.8999999761581421, 0.5249999761581421]
high_chair_A[0].rotation = [0, 0, -0.8635889032506371]
high_chair_A[0].optimize = 2
bar_counter[0].position = [1.399999976158142, 0.30712035298347473, 0.5249999761581421]
bar_counter[0].rotation = [0, 0, 1.562874261005667]
bar_counter[0].optimize = 2
pool[0].position = [3.7899999618530273, 0.6414725184440613, 0.4000000059604645]
pool[0].rotation = [0, 0, 1.575028850365419]
pool[0].optimize = 2
chair[0].position = [2.0999999046325684, 0.8999999761581421, 0.42500001192092896]
chair[0].rotation = [0, 0, -2.420422598925909]
chair[0].optimize = 2
basin_cabinet[0].position = [0.24926134943962097, 0.8199999928474426, 0.42500001192092896]
basin_cabinet[0].rotation = [0, 0, 0.004217701978397405]
basin_cabinet[0].optimize = 2

