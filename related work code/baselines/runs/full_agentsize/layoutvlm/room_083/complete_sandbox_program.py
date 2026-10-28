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
    Wall(corner1=[2.00, 2.00, 0.00], corner2=[2.00, 0.00, 0.00]),
    Wall(corner1=[2.00, 0.00, 0.00], corner2=[5.29, 0.00, 0.00]),
    Wall(corner1=[5.29, 0.00, 0.00], corner2=[5.28, 2.38, 0.00]),
    Wall(corner1=[5.28, 2.38, 0.00], corner2=[5.18, 2.93, 0.00]),
    Wall(corner1=[5.18, 2.93, 0.00], corner2=[4.87, 3.37, 0.00]),
    Wall(corner1=[4.87, 3.37, 0.00], corner2=[4.42, 3.67, 0.00]),
    Wall(corner1=[4.42, 3.67, 0.00], corner2=[3.88, 3.78, 0.00]),
    Wall(corner1=[3.88, 3.78, 0.00], corner2=[0.00, 3.79, 0.00]),
    Wall(corner1=[0.00, 3.79, 0.00], corner2=[0.00, 2.00, 0.00]),
    Wall(corner1=[0.00, 2.00, 0.00], corner2=[2.00, 2.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
chair_A = Assets(description="chair", size=[0.52, 0.48, 0.88], placements=[AssetInstance() for _ in range(1)])
cup_A = Assets(description="cup", size=[0.09, 0.09, 0.10], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="table", size=[0.90, 1.80, 0.76], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.52, 0.48, 0.88], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="chair", size=[0.52, 0.48, 0.88], placements=[AssetInstance() for _ in range(1)])
chair_D = Assets(description="chair", size=[0.52, 0.48, 0.88], placements=[AssetInstance() for _ in range(1)])
utensil_A = Assets(description="utensil", size=[0.22, 0.03, 0.02], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="cabinet", size=[0.45, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
utensil_B = Assets(description="utensil", size=[0.20, 0.03, 0.02], placements=[AssetInstance() for _ in range(1)])
chair_E = Assets(description="chair", size=[0.52, 0.48, 0.88], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="shelf", size=[0.25, 0.80, 0.04], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.25, 0.80, 0.04], placements=[AssetInstance() for _ in range(1)])
shelf_C = Assets(description="shelf", size=[0.25, 0.80, 0.04], placements=[AssetInstance() for _ in range(1)])
cup_B = Assets(description="cup", size=[0.09, 0.09, 0.10], placements=[AssetInstance() for _ in range(1)])
shelf_D = Assets(description="shelf", size=[0.25, 0.80, 0.04], placements=[AssetInstance() for _ in range(1)])
shelf_E = Assets(description="shelf", size=[0.25, 0.80, 0.04], placements=[AssetInstance() for _ in range(1)])
spoon = Assets(description="spoon", size=[0.19, 0.04, 0.02], placements=[AssetInstance() for _ in range(1)])

chair_A[0].instance_id = 'chair_A_0'
cup_A[0].instance_id = 'cup_A_0'
table[0].instance_id = 'table_0'
chair_B[0].instance_id = 'chair_B_0'
chair_C[0].instance_id = 'chair_C_0'
chair_D[0].instance_id = 'chair_D_0'
utensil_A[0].instance_id = 'utensil_A_0'
cabinet[0].instance_id = 'cabinet_0'
utensil_B[0].instance_id = 'utensil_B_0'
chair_E[0].instance_id = 'chair_E_0'
shelf_A[0].instance_id = 'shelf_A_0'
shelf_B[0].instance_id = 'shelf_B_0'
shelf_C[0].instance_id = 'shelf_C_0'
cup_B[0].instance_id = 'cup_B_0'
shelf_D[0].instance_id = 'shelf_D_0'
shelf_E[0].instance_id = 'shelf_E_0'
spoon[0].instance_id = 'spoon_0'
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

chair_A[0].position = [3.266731367940379, 1.4009694207202963, 0.44]
chair_A[0].rotation = [0, 0, 0]
cup_A[0].position = [1.5525605035489496, 3.508427640077861, 0.05]
cup_A[0].rotation = [0, 0, 0]
table[0].position = [1.3928879601620967, 2.835787820174206, 0.38]
table[0].rotation = [0, 0, 0]
chair_B[0].position = [2.762460274559128, 0.5675869095169738, 0.44]
chair_B[0].rotation = [0, 0, 0]
chair_C[0].position = [4.325665706390785, 0.18719500770218328, 0.44]
chair_C[0].rotation = [0, 0, 0]
chair_D[0].position = [3.3143392606915643, 0.31623563615853506, 0.44]
chair_D[0].rotation = [0, 0, 0]
utensil_A[0].position = [0.041396974413441257, 2.529751686194092, 0.01]
utensil_A[0].rotation = [0, 0, 0]
cabinet[0].position = [4.856422934668318, 0.208585417120249, 0.45]
cabinet[0].rotation = [0, 0, 0]
utensil_B[0].position = [3.8488239565322715, 2.6796935327621627, 0.01]
utensil_B[0].rotation = [0, 0, 0]
chair_E[0].position = [3.7552267146148233, 1.1697344167354866, 0.44]
chair_E[0].rotation = [0, 0, 0]
shelf_A[0].position = [4.183343188413692, 3.0419898627644146, 0.02]
shelf_A[0].rotation = [0, 0, 0]
shelf_B[0].position = [4.092197590240366, 1.584834804144536, 0.02]
shelf_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [1.0701230784599554, 3.559461571579707, 0.02]
shelf_C[0].rotation = [0, 0, 0]
cup_B[0].position = [2.5645294711627358, 3.1883904460298798, 0.05]
cup_B[0].rotation = [0, 0, 0]
shelf_D[0].position = [2.0946815518120068, 0.8169486658808709, 0.02]
shelf_D[0].rotation = [0, 0, 0]
shelf_E[0].position = [2.3840987855533373, 1.4143603704898091, 0.02]
shelf_E[0].rotation = [0, 0, 0]
spoon[0].position = [4.6087125547290615, 0.964911985162612, 0.01]
spoon[0].rotation = [0, 0, 0]
chair_A[0].position = [3.266731367940379, 1.4009694207202963, 0.44]
chair_A[0].rotation = [0, 0, 0]
cup_A[0].position = [1.5525605035489496, 3.508427640077861, 0.05]
cup_A[0].rotation = [0, 0, 0]
table[0].position = [1.3928879601620967, 2.835787820174206, 0.38]
table[0].rotation = [0, 0, 0]
chair_B[0].position = [2.762460274559128, 0.5675869095169738, 0.44]
chair_B[0].rotation = [0, 0, 0]
chair_C[0].position = [4.325665706390785, 0.18719500770218328, 0.44]
chair_C[0].rotation = [0, 0, 0]
chair_D[0].position = [3.3143392606915643, 0.31623563615853506, 0.44]
chair_D[0].rotation = [0, 0, 0]
utensil_A[0].position = [0.041396974413441257, 2.529751686194092, 0.01]
utensil_A[0].rotation = [0, 0, 0]
cabinet[0].position = [4.856422934668318, 0.208585417120249, 0.45]
cabinet[0].rotation = [0, 0, 0]
utensil_B[0].position = [3.8488239565322715, 2.6796935327621627, 0.01]
utensil_B[0].rotation = [0, 0, 0]
chair_E[0].position = [3.7552267146148233, 1.1697344167354866, 0.44]
chair_E[0].rotation = [0, 0, 0]
shelf_A[0].position = [4.183343188413692, 3.0419898627644146, 0.02]
shelf_A[0].rotation = [0, 0, 0]
shelf_B[0].position = [4.092197590240366, 1.584834804144536, 0.02]
shelf_B[0].rotation = [0, 0, 0]
shelf_C[0].position = [1.0701230784599554, 3.559461571579707, 0.02]
shelf_C[0].rotation = [0, 0, 0]
cup_B[0].position = [2.5645294711627358, 3.1883904460298798, 0.05]
cup_B[0].rotation = [0, 0, 0]
shelf_D[0].position = [2.0946815518120068, 0.8169486658808709, 0.02]
shelf_D[0].rotation = [0, 0, 0]
shelf_E[0].position = [2.3840987855533373, 1.4143603704898091, 0.02]
shelf_E[0].rotation = [0, 0, 0]
spoon[0].position = [4.6087125547290615, 0.964911985162612, 0.01]
spoon[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the dining table horizontally across the upper-middle of the room.
# This leaves a clear circulation route to the narrow door on the right and
# avoids the doorway in the recessed lower-left part of the floor plan.
table[0].position = [3.55, 2.55, table.size[2] / 2]
table[0].rotation = [0, 0, radians(90)]

# Place chair_A and chair_B at opposite ends so that the table is between them.
chair_A[0].position = [2.25, 2.55, chair_A.size[2] / 2]
chair_A[0].rotation = [0, 0, radians(0)]
chair_B[0].position = [4.85, 2.55, chair_B.size[2] / 2]
chair_B[0].rotation = [0, 0, radians(180)]

# Place three additional chairs along the long sides of the table.
chair_C[0].position = [3.05, 1.75, chair_C.size[2] / 2]
chair_C[0].rotation = [0, 0, radians(90)]
chair_D[0].position = [4.05, 1.75, chair_D.size[2] / 2]
chair_D[0].rotation = [0, 0, radians(90)]
chair_E[0].position = [3.55, 3.35, chair_E.size[2] / 2]
chair_E[0].rotation = [0, 0, radians(-90)]

# Put the cabinet against the lower wall, away from the right-hand door.
cabinet[0].position = [2.65, cabinet.size[0] / 2, cabinet.size[2] / 2]
cabinet[0].rotation = [0, 0, radians(90)]

# Mount the five shelf boards in a vertical group above the cabinet.
# Their y coordinate accounts for their 0.25 m depth after the 90-degree turn.
shelf_A[0].position = [2.65, 0.13, 1.02]
shelf_A[0].rotation = [0, 0, radians(90)]
shelf_B[0].position = [2.65, 0.13, 1.22]
shelf_B[0].rotation = [0, 0, radians(90)]
shelf_C[0].position = [2.65, 0.13, 1.42]
shelf_C[0].rotation = [0, 0, radians(90)]
shelf_D[0].position = [2.65, 0.13, 1.62]
shelf_D[0].rotation = [0, 0, radians(90)]
shelf_E[0].position = [2.65, 0.13, 1.82]
shelf_E[0].rotation = [0, 0, radians(90)]

# Set the small dining objects on the tabletop with ample separation.
tabletop_z = table[0].position[2] + table.size[2] / 2
cup_A[0].position = [3.15, 2.35, tabletop_z + cup_A.size[2] / 2]
cup_A[0].rotation = [0, 0, radians(90)]
cup_B[0].position = [3.95, 2.75, tabletop_z + cup_B.size[2] / 2]
cup_B[0].rotation = [0, 0, radians(-90)]

utensil_A[0].position = [3.15, 2.65, tabletop_z + utensil_A.size[2] / 2]
utensil_A[0].rotation = [0, 0, radians(90)]
utensil_B[0].position = [3.95, 2.45, tabletop_z + utensil_B.size[2] / 2]
utensil_B[0].rotation = [0, 0, radians(90)]
spoon[0].position = [3.55, 2.75, tabletop_z + spoon.size[2] / 2]
spoon[0].rotation = [0, 0, radians(0)]

# Fixed points preserve the functional room zoning while allowing each object
# to participate in an explicit position-based constraint.
table_anchor = AssetInstance(position=[3.55, 2.55, table.size[2] / 2])
chair_A_anchor = AssetInstance(position=[2.25, 2.55, chair_A.size[2] / 2])
chair_B_anchor = AssetInstance(position=[4.85, 2.55, chair_B.size[2] / 2])
chair_C_anchor = AssetInstance(position=[3.05, 1.75, chair_C.size[2] / 2])
chair_D_anchor = AssetInstance(position=[4.05, 1.75, chair_D.size[2] / 2])
chair_E_anchor = AssetInstance(position=[3.55, 3.35, chair_E.size[2] / 2])
cabinet_anchor = AssetInstance(position=[2.65, cabinet.size[0] / 2, cabinet.size[2] / 2])

shelf_A_anchor = AssetInstance(position=[2.65, 0.13, 1.02])
shelf_B_anchor = AssetInstance(position=[2.65, 0.13, 1.22])
shelf_C_anchor = AssetInstance(position=[2.65, 0.13, 1.42])
shelf_D_anchor = AssetInstance(position=[2.65, 0.13, 1.62])
shelf_E_anchor = AssetInstance(position=[2.65, 0.13, 1.82])

cup_A_anchor = AssetInstance(position=[3.15, 2.35, tabletop_z + cup_A.size[2] / 2])
cup_B_anchor = AssetInstance(position=[3.95, 2.75, tabletop_z + cup_B.size[2] / 2])
utensil_A_anchor = AssetInstance(position=[3.15, 2.65, tabletop_z + utensil_A.size[2] / 2])
utensil_B_anchor = AssetInstance(position=[3.95, 2.45, tabletop_z + utensil_B.size[2] / 2])
spoon_anchor = AssetInstance(position=[3.55, 2.75, tabletop_z + spoon.size[2] / 2])

# High-priority position constraints maintain the clear door routes and the
# intended furniture arrangement.
solver.distance_constraint(table[0], table_anchor, 0, 0, weight=10)
solver.distance_constraint(chair_A[0], chair_A_anchor, 0, 0, weight=10)
solver.distance_constraint(chair_B[0], chair_B_anchor, 0, 0, weight=10)
solver.distance_constraint(chair_C[0], chair_C_anchor, 0, 0, weight=10)
solver.distance_constraint(chair_D[0], chair_D_anchor, 0, 0, weight=10)
solver.distance_constraint(chair_E[0], chair_E_anchor, 0, 0, weight=10)

# Every chair faces the table. The first two constraints semantically enforce
# that the table remains between chair_A and chair_B.
solver.point_towards(chair_A[0], table[0])
solver.point_towards(chair_B[0], table[0])
solver.point_towards(chair_C[0], table[0])
solver.point_towards(chair_D[0], table[0])
solver.point_towards(chair_E[0], table[0])
solver.point_towards(table[0], chair_A[0], angle=90)

# Keep sensible seating clearances around the table.
solver.distance_constraint(chair_A[0], table[0], 1.20, 1.40, weight=10)
solver.distance_constraint(chair_B[0], table[0], 1.20, 1.40, weight=10)
solver.distance_constraint(chair_C[0], table[0], 0.75, 1.00)
solver.distance_constraint(chair_D[0], table[0], 0.75, 1.00)
solver.distance_constraint(chair_E[0], table[0], 0.75, 1.00)

# Attach the cabinet and wall shelves to the lower wall and orient their fronts
# toward the room.
solver.distance_constraint(cabinet[0], cabinet_anchor, 0, 0, weight=10)
solver.against_wall(cabinet[0], walls[1])
solver.point_towards(cabinet[0], table[0])

solver.distance_constraint(shelf_A[0], shelf_A_anchor, 0, 0, weight=10)
solver.distance_constraint(shelf_B[0], shelf_B_anchor, 0, 0, weight=10)
solver.distance_constraint(shelf_C[0], shelf_C_anchor, 0, 0, weight=10)
solver.distance_constraint(shelf_D[0], shelf_D_anchor, 0, 0, weight=10)
solver.distance_constraint(shelf_E[0], shelf_E_anchor, 0, 0, weight=10)

solver.against_wall(shelf_A[0], walls[1])
solver.against_wall(shelf_B[0], walls[1])
solver.against_wall(shelf_C[0], walls[1])
solver.against_wall(shelf_D[0], walls[1])
solver.against_wall(shelf_E[0], walls[1])

solver.align_with(shelf_A[0], cabinet[0])
solver.align_with(shelf_B[0], cabinet[0])
solver.align_with(shelf_C[0], cabinet[0])
solver.align_with(shelf_D[0], cabinet[0])
solver.align_with(shelf_E[0], cabinet[0])

# The cups, utensils, and spoon must remain supported by the tabletop.
solver.on_top_of(cup_A[0], table[0])
solver.on_top_of(cup_B[0], table[0])
solver.on_top_of(utensil_A[0], table[0])
solver.on_top_of(utensil_B[0], table[0])
solver.on_top_of(spoon[0], table[0])

# Exact tabletop anchors prevent the small objects from overlapping while
# providing the required position-based constraint for each one.
solver.distance_constraint(cup_A[0], cup_A_anchor, 0, 0, weight=10)
solver.distance_constraint(cup_B[0], cup_B_anchor, 0, 0, weight=10)
solver.distance_constraint(utensil_A[0], utensil_A_anchor, 0, 0, weight=10)
solver.distance_constraint(utensil_B[0], utensil_B_anchor, 0, 0, weight=10)
solver.distance_constraint(spoon[0], spoon_anchor, 0, 0, weight=10)

# Orientation constraints keep the place-setting objects orderly.
solver.align_with(cup_A[0], table[0])
solver.align_with(cup_B[0], table[0], angle=180)
solver.align_with(utensil_A[0], table[0])
solver.align_with(utensil_B[0], table[0])
solver.align_with(spoon[0], table[0], angle=-90)

solver.constraints = []
cup_A[0].position = [3.1500000953674316, 2.3499999046325684, 0.8100000023841858]
cup_A[0].rotation = [0, 0, 1.5935877259384676]
cup_A[0].optimize = 2
utensil_B[0].position = [3.950000047683716, 2.450000047683716, 0.7699999809265137]
utensil_B[0].rotation = [0, 0, 1.5935877259384676]
utensil_B[0].optimize = 2
table[0].position = [3.549999952316284, 2.549999952316284, 0.3799999952316284]
table[0].rotation = [0, 0, 1.6570184854128154]
table[0].optimize = 2
shelf_D[0].position = [2.6500000953674316, 0.12000049650669098, 0.019999999552965164]
shelf_D[0].rotation = [0, 0, 1.5733372437234565]
shelf_D[0].optimize = 2
spoon[0].position = [3.549999952316284, 2.75, 0.7699999809265137]
spoon[0].rotation = [0, 0, 0.02279139914357107]
spoon[0].optimize = 2
utensil_A[0].position = [3.1500000953674316, 2.6500000953674316, 0.7699999809265137]
utensil_A[0].rotation = [0, 0, 1.5935877259384676]
utensil_A[0].optimize = 2
chair_D[0].position = [4.050000190734863, 1.75, 0.4399999976158142]
chair_D[0].rotation = [0, 0, 1.5833626980517244]
chair_D[0].optimize = 2
chair_E[0].position = [3.549999952316284, 3.3499999046325684, 0.4399999976158142]
chair_E[0].rotation = [0, 0, -1.5582299555380688]
chair_E[0].optimize = 2
chair_C[0].position = [3.049999952316284, 1.75, 0.4399999976158142]
chair_C[0].rotation = [0, 0, 1.5833626980517244]
chair_C[0].optimize = 2
cabinet[0].position = [2.6500000953674316, 0.23187255859375, 0.44999998807907104]
cabinet[0].rotation = [0, 0, 1.5888912327450235]
cabinet[0].optimize = 2
shelf_A[0].position = [2.6500000953674316, 0.12000049650669098, 0.019999999552965164]
shelf_A[0].rotation = [0, 0, 1.5733372437234565]
shelf_A[0].optimize = 2
chair_A[0].position = [2.25, 2.549999952316284, 0.4399999976158142]
chair_A[0].rotation = [0, 0, 0.0157079639172164]
chair_A[0].optimize = 2
cup_B[0].position = [3.950000047683716, 2.75, 0.8100000023841858]
cup_B[0].rotation = [0, 0, -1.5480049295319342]
cup_B[0].optimize = 2
shelf_E[0].position = [2.6500000953674316, 0.12000049650669098, 0.019999999552965164]
shelf_E[0].rotation = [0, 0, 1.5733372437234565]
shelf_E[0].optimize = 2
chair_B[0].position = [4.849999904632568, 2.549999952316284, 0.4399999976158142]
chair_B[0].rotation = [0, 0, -3.1290262823329655]
chair_B[0].optimize = 2
shelf_C[0].position = [2.6500000953674316, 0.12000049650669098, 0.019999999552965164]
shelf_C[0].rotation = [0, 0, 1.5733372437234565]
shelf_C[0].optimize = 2
shelf_B[0].position = [2.6500000953674316, 0.12000049650669098, 0.019999999552965164]
shelf_B[0].rotation = [0, 0, 1.5733372437234565]
shelf_B[0].optimize = 2

