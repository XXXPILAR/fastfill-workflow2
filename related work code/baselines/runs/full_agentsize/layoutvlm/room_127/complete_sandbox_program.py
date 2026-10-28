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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[9.00, 0.00, 0.00]),
    Wall(corner1=[9.00, 0.00, 0.00], corner2=[9.00, 3.00, 0.00]),
    Wall(corner1=[9.00, 3.00, 0.00], corner2=[0.00, 3.00, 0.00]),
    Wall(corner1=[0.00, 3.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
luggage_bench = Assets(description="luggage bench", size=[0.45, 1.20, 0.50], placements=[AssetInstance() for _ in range(1)])
single_bed = Assets(description="single bed", size=[2.00, 1.00, 0.55], placements=[AssetInstance() for _ in range(1)])
storage_cabinet = Assets(description="storage cabinet", size=[0.45, 1.20, 1.20], placements=[AssetInstance() for _ in range(1)])
writing_desk = Assets(description="writing desk", size=[0.60, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.60, 1.50, 2.10], placements=[AssetInstance() for _ in range(1)])
wall_shelf_A = Assets(description="A brown wood frame.", size=[0.25, 1.00, 0.30], placements=[AssetInstance() for _ in range(1)])
wall_mirror = Assets(description="A rectangular mirror in a brown wooden frame.", size=[0.05, 0.80, 1.20], placements=[AssetInstance() for _ in range(1)])
side_chair = Assets(description="side chair", size=[0.55, 0.50, 0.85], placements=[AssetInstance() for _ in range(1)])
floor_lamp = Assets(description="floor lamp", size=[0.35, 0.35, 1.60], placements=[AssetInstance() for _ in range(1)])
bedside_table = Assets(description="bedside table", size=[0.40, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
tv_console = Assets(description="tv console", size=[0.45, 1.50, 0.60], placements=[AssetInstance() for _ in range(1)])
desk_chair = Assets(description="desk chair", size=[0.60, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
wall_shelf_B = Assets(description="A brown wood frame.", size=[0.25, 1.00, 0.30], placements=[AssetInstance() for _ in range(1)])

luggage_bench[0].instance_id = 'luggage_bench_0'
single_bed[0].instance_id = 'single_bed_0'
storage_cabinet[0].instance_id = 'storage_cabinet_0'
writing_desk[0].instance_id = 'writing_desk_0'
wardrobe[0].instance_id = 'wardrobe_0'
wall_shelf_A[0].instance_id = 'wall_shelf_A_0'
wall_mirror[0].instance_id = 'wall_mirror_0'
side_chair[0].instance_id = 'side_chair_0'
floor_lamp[0].instance_id = 'floor_lamp_0'
bedside_table[0].instance_id = 'bedside_table_0'
tv_console[0].instance_id = 'tv_console_0'
desk_chair[0].instance_id = 'desk_chair_0'
wall_shelf_B[0].instance_id = 'wall_shelf_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

luggage_bench[0].position = [2.987305486450611, 1.3083214460519448, 0.25]
luggage_bench[0].rotation = [0, 0, 0]
single_bed[0].position = [3.359004197649204, 0.19110050857602623, 0.275]
single_bed[0].rotation = [0, 0, 0]
storage_cabinet[0].position = [0.8678680098488073, 1.0050080244342627, 0.6]
storage_cabinet[0].rotation = [0, 0, 0]
writing_desk[0].position = [0.9838129969786695, 1.1128113444649148, 0.375]
writing_desk[0].rotation = [0, 0, 0]
wardrobe[0].position = [2.1032350093177383, 1.2326354134416775, 1.05]
wardrobe[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [0.6057343152206632, 1.6147043637634915, 0.15]
wall_shelf_A[0].rotation = [0, 0, 0]
wall_mirror[0].position = [5.871168207285525, 2.9854511183587475, 0.6]
wall_mirror[0].rotation = [0, 0, 0]
side_chair[0].position = [3.8871258123989527, 0.9255421912280759, 0.425]
side_chair[0].rotation = [0, 0, 0]
floor_lamp[0].position = [7.473737804571049, 1.349845433336693, 0.8]
floor_lamp[0].rotation = [0, 0, 0]
bedside_table[0].position = [8.915160947964539, 1.159559461290426, 0.275]
bedside_table[0].rotation = [0, 0, 0]
tv_console[0].position = [2.9566759633358703, 2.229709442529102, 0.3]
tv_console[0].rotation = [0, 0, 0]
desk_chair[0].position = [5.495893859057562, 2.971410542513626, 0.45]
desk_chair[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [0.3264830724963149, 2.906725310354482, 0.15]
wall_shelf_B[0].rotation = [0, 0, 0]
luggage_bench[0].position = [2.987305486450611, 1.3083214460519448, 0.25]
luggage_bench[0].rotation = [0, 0, 0]
single_bed[0].position = [3.359004197649204, 0.19110050857602623, 0.275]
single_bed[0].rotation = [0, 0, 0]
storage_cabinet[0].position = [0.8678680098488073, 1.0050080244342627, 0.6]
storage_cabinet[0].rotation = [0, 0, 0]
writing_desk[0].position = [0.9838129969786695, 1.1128113444649148, 0.375]
writing_desk[0].rotation = [0, 0, 0]
wardrobe[0].position = [2.1032350093177383, 1.2326354134416775, 1.05]
wardrobe[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [0.6057343152206632, 1.6147043637634915, 0.15]
wall_shelf_A[0].rotation = [0, 0, 0]
wall_mirror[0].position = [5.871168207285525, 2.9854511183587475, 0.6]
wall_mirror[0].rotation = [0, 0, 0]
side_chair[0].position = [3.8871258123989527, 0.9255421912280759, 0.425]
side_chair[0].rotation = [0, 0, 0]
floor_lamp[0].position = [7.473737804571049, 1.349845433336693, 0.8]
floor_lamp[0].rotation = [0, 0, 0]
bedside_table[0].position = [8.915160947964539, 1.159559461290426, 0.275]
bedside_table[0].rotation = [0, 0, 0]
tv_console[0].position = [2.9566759633358703, 2.229709442529102, 0.3]
tv_console[0].rotation = [0, 0, 0]
desk_chair[0].position = [5.495893859057562, 2.971410542513626, 0.45]
desk_chair[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [0.3264830724963149, 2.906725310354482, 0.15]
wall_shelf_B[0].rotation = [0, 0, 0]

solver.constraints = []

# The room is long and narrow, so the main furniture is distributed along
# the top and bottom walls. The area immediately inside the door on the
# left is kept clear, and the window on the lower half of the right wall
# remains unobstructed.

# Bed group along the upper-left wall.
single_bed[0].position = [2.30, 2.50, 0.275]
single_bed[0].rotation = [0, 0, radians(0)]

bedside_table[0].position = [1.00, 2.75, 0.275]
bedside_table[0].rotation = [0, 0, radians(-90)]

# The bench is placed across the foot of the bed.
luggage_bench[0].position = [3.55, 2.40, 0.25]
luggage_bench[0].rotation = [0, 0, radians(0)]

# Tall storage is concentrated along the upper wall and the upper portion
# of the right wall, away from both the entrance and the window.
wardrobe[0].position = [4.75, 2.70, 1.05]
wardrobe[0].rotation = [0, 0, radians(-90)]

writing_desk[0].position = [6.25, 2.70, 0.375]
writing_desk[0].rotation = [0, 0, radians(-90)]

storage_cabinet[0].position = [8.775, 2.25, 0.60]
storage_cabinet[0].rotation = [0, 0, radians(180)]

# The desk chair is positioned in front of the writing desk. Its explicit
# orientation points toward the storage cabinet, as required.
desk_chair[0].position = [6.55, 1.75, 0.45]
desk_chair[0].rotation = [0, 0, radians(13)]

# A small seating/television area occupies the lower-right portion.
tv_console[0].position = [7.50, 0.225, 0.30]
tv_console[0].rotation = [0, 0, radians(90)]

side_chair[0].position = [7.75, 1.10, 0.425]
side_chair[0].rotation = [0, 0, radians(-90)]

floor_lamp[0].position = [6.55, 0.45, 0.80]
floor_lamp[0].rotation = [0, 0, radians(90)]

# Wall-mounted pieces are raised above the floor. The shelves sit above
# the desk area, while the mirror uses otherwise free lower-wall space.
wall_shelf_A[0].position = [5.95, 2.875, 1.65]
wall_shelf_A[0].rotation = [0, 0, radians(-90)]

wall_shelf_B[0].position = [7.25, 2.875, 1.65]
wall_shelf_B[0].rotation = [0, 0, radians(-90)]

wall_mirror[0].position = [4.30, 0.025, 1.30]
wall_mirror[0].rotation = [0, 0, radians(90)]


# Exact placement anchors preserve the planned clearances and keep every
# asset within the room. These are specified first because they are the
# primary position constraints.
single_bed_anchor = AssetInstance(position=[2.30, 2.50, 0.275])
bedside_table_anchor = AssetInstance(position=[1.00, 2.75, 0.275])
luggage_bench_anchor = AssetInstance(position=[3.55, 2.40, 0.25])
wardrobe_anchor = AssetInstance(position=[4.75, 2.70, 1.05])
writing_desk_anchor = AssetInstance(position=[6.25, 2.70, 0.375])
storage_cabinet_anchor = AssetInstance(position=[8.775, 2.25, 0.60])
desk_chair_anchor = AssetInstance(position=[6.55, 1.75, 0.45])
tv_console_anchor = AssetInstance(position=[7.50, 0.225, 0.30])
side_chair_anchor = AssetInstance(position=[7.75, 1.10, 0.425])
floor_lamp_anchor = AssetInstance(position=[6.55, 0.45, 0.80])
wall_shelf_A_anchor = AssetInstance(position=[5.95, 2.875, 1.65])
wall_shelf_B_anchor = AssetInstance(position=[7.25, 2.875, 1.65])
wall_mirror_anchor = AssetInstance(position=[4.30, 0.025, 1.30])

solver.distance_constraint(single_bed[0], single_bed_anchor, 0, 0, weight=10)
solver.distance_constraint(bedside_table[0], bedside_table_anchor, 0, 0, weight=10)
solver.distance_constraint(luggage_bench[0], luggage_bench_anchor, 0, 0, weight=10)
solver.distance_constraint(wardrobe[0], wardrobe_anchor, 0, 0, weight=10)
solver.distance_constraint(writing_desk[0], writing_desk_anchor, 0, 0, weight=10)
solver.distance_constraint(storage_cabinet[0], storage_cabinet_anchor, 0, 0, weight=10)
solver.distance_constraint(desk_chair[0], desk_chair_anchor, 0, 0, weight=10)
solver.distance_constraint(tv_console[0], tv_console_anchor, 0, 0, weight=10)
solver.distance_constraint(side_chair[0], side_chair_anchor, 0, 0, weight=10)
solver.distance_constraint(floor_lamp[0], floor_lamp_anchor, 0, 0, weight=10)
solver.distance_constraint(wall_shelf_A[0], wall_shelf_A_anchor, 0, 0, weight=10)
solver.distance_constraint(wall_shelf_B[0], wall_shelf_B_anchor, 0, 0, weight=10)
solver.distance_constraint(wall_mirror[0], wall_mirror_anchor, 0, 0, weight=10)

# Wall-contact constraints keep the perimeter furniture and wall fixtures
# attached to their intended walls.
solver.against_wall(single_bed[0], walls[2])
solver.against_wall(bedside_table[0], walls[2])
solver.against_wall(wardrobe[0], walls[2])
solver.against_wall(writing_desk[0], walls[2])
solver.against_wall(storage_cabinet[0], walls[1])
solver.against_wall(tv_console[0], walls[0])
solver.against_wall(wall_shelf_A[0], walls[2])
solver.against_wall(wall_shelf_B[0], walls[2])
solver.against_wall(wall_mirror[0], walls[0])

# Orientation constraints for every asset. Fixed points inside the room
# make doors, fronts, and viewing surfaces face away from their walls.
upper_inward_target = AssetInstance(position=[4.50, 1.50, 1.00])
lower_inward_target = AssetInstance(position=[4.50, 1.50, 1.00])
right_inward_target = AssetInstance(position=[7.50, 2.25, 1.00])

solver.align_with(single_bed[0], luggage_bench[0], angle=0)
solver.align_with(luggage_bench[0], single_bed[0], angle=0)
solver.point_towards(bedside_table[0], upper_inward_target)
solver.point_towards(wardrobe[0], upper_inward_target)
solver.point_towards(writing_desk[0], upper_inward_target)
solver.point_towards(storage_cabinet[0], right_inward_target)

# Required semantic relation: the desk chair faces the storage cabinet.
solver.point_towards(desk_chair[0], storage_cabinet[0])

solver.point_towards(tv_console[0], lower_inward_target)
solver.point_towards(side_chair[0], tv_console[0])
solver.align_with(floor_lamp[0], tv_console[0], angle=0)
solver.point_towards(wall_shelf_A[0], upper_inward_target)
solver.point_towards(wall_shelf_B[0], upper_inward_target)
solver.point_towards(wall_mirror[0], lower_inward_target)

# Additional semantic spacing constraints maintain the furniture groups
# if small feasibility adjustments are required.
solver.distance_constraint(luggage_bench[0], single_bed[0], 1.20, 1.35, weight=1)
solver.distance_constraint(bedside_table[0], single_bed[0], 1.20, 1.40, weight=1)
solver.distance_constraint(desk_chair[0], writing_desk[0], 0.75, 1.00, weight=1)
solver.distance_constraint(side_chair[0], tv_console[0], 0.75, 1.00, weight=1)
solver.distance_constraint(floor_lamp[0], tv_console[0], 0.90, 1.20, weight=1)

solver.constraints = []
writing_desk[0].position = [6.25, 2.7002274990081787, 0.375]
writing_desk[0].rotation = [0, 0, -1.5695831956454438]
writing_desk[0].optimize = 2
single_bed[0].position = [2.299999952316284, 2.0698375701904297, 0.2750000059604645]
single_bed[0].rotation = [0, 0, -0.5189880232924647]
single_bed[0].optimize = 2
luggage_bench[0].position = [3.549999952316284, 2.36515736579895, 0.25]
luggage_bench[0].rotation = [0, 0, -0.4952382940516817]
luggage_bench[0].optimize = 2
bedside_table[0].position = [1.0, 2.803234100341797, 0.2750000059604645]
bedside_table[0].rotation = [0, 0, -1.5695929889906064]
bedside_table[0].optimize = 2
floor_lamp[0].position = [6.550000190734863, 0.44999998807907104, 0.800000011920929]
floor_lamp[0].rotation = [0, 0, 1.5661536735776078]
floor_lamp[0].optimize = 2
storage_cabinet[0].position = [8.775215148925781, 2.25, 0.6000000238418579]
storage_cabinet[0].rotation = [0, 0, -3.140379517564354]
storage_cabinet[0].optimize = 2
tv_console[0].position = [7.5, 0.22609536349773407, 0.30000001192092896]
tv_console[0].rotation = [0, 0, 1.5702631934783426]
tv_console[0].optimize = 2
wall_mirror[0].position = [4.300000190734863, 0.02430836856365204, 0.6000000238418579]
wall_mirror[0].rotation = [0, 0, 1.5706862851057144]
wall_mirror[0].optimize = 2
desk_chair[0].position = [6.550000190734863, 1.75, 0.44999998807907104]
desk_chair[0].rotation = [0, 0, 0.23945918097392693]
desk_chair[0].optimize = 2
wardrobe[0].position = [4.75, 2.7004106044769287, 1.0499999523162842]
wardrobe[0].rotation = [0, 0, -1.5709037960399725]
wardrobe[0].optimize = 2
wall_shelf_B[0].position = [7.25, 2.874439239501953, 0.15000000596046448]
wall_shelf_B[0].rotation = [0, 0, -1.570905186296113]
wall_shelf_B[0].optimize = 2
side_chair[0].position = [7.75, 1.100000023841858, 0.42500001192092896]
side_chair[0].rotation = [0, 0, -1.5582299555380688]
side_chair[0].optimize = 2
wall_shelf_A[0].position = [5.949999809265137, 2.874439239501953, 0.15000000596046448]
wall_shelf_A[0].rotation = [0, 0, -1.570905186296113]
wall_shelf_A[0].optimize = 2

