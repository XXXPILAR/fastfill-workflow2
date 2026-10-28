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
    Wall(corner1=[3.94, 2.53, 0.00], corner2=[5.94, 2.53, 0.00]),
    Wall(corner1=[5.94, 2.53, 0.00], corner2=[5.94, 0.00, 0.00]),
    Wall(corner1=[5.94, 0.00, 0.00], corner2=[8.70, 0.00, 0.00]),
    Wall(corner1=[8.70, 0.00, 0.00], corner2=[8.70, 3.79, 0.00]),
    Wall(corner1=[8.70, 3.79, 0.00], corner2=[5.87, 3.78, 0.00]),
    Wall(corner1=[5.87, 3.78, 0.00], corner2=[5.71, 3.78, 0.00]),
    Wall(corner1=[5.71, 3.78, 0.00], corner2=[0.24, 3.78, 0.00]),
    Wall(corner1=[0.24, 3.78, 0.00], corner2=[0.24, 2.74, 0.00]),
    Wall(corner1=[0.24, 2.74, 0.00], corner2=[0.00, 2.74, 0.00]),
    Wall(corner1=[0.00, 2.74, 0.00], corner2=[0.00, 0.59, 0.00]),
    Wall(corner1=[0.00, 0.59, 0.00], corner2=[0.24, 0.59, 0.00]),
    Wall(corner1=[0.24, 0.59, 0.00], corner2=[0.24, 0.00, 0.00]),
    Wall(corner1=[0.24, 0.00, 0.00], corner2=[3.94, 0.00, 0.00]),
    Wall(corner1=[3.94, 0.00, 0.00], corner2=[3.94, 2.53, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
fabric_sculpture = Assets(description="A flowing fabric sculpture with intricate folds and drapes, standing upright on a black base.", size=[0.55, 0.85, 1.85], placements=[AssetInstance() for _ in range(1)])
dress = Assets(description="A black sleeveless dress with a subtle pattern, featuring a V-neckline and a flared hem. It is displayed on a hanger against a plain background.", size=[0.08, 0.55, 1.15], placements=[AssetInstance() for _ in range(1)])
sideboard = Assets(description="A sleek console table with a dark, possibly marble or stone top and metallic legs that curve outward for support. It has a modern design suitable for entryways or living spaces.", size=[0.42, 1.55, 0.82], placements=[AssetInstance() for _ in range(1)])
drawer_chest_A = Assets(description="A classic-style bed with an ornate headboard and footboard, featuring a light-colored fabric cover and two patterned pillows.", size=[2.15, 1.65, 1.35], placements=[AssetInstance() for _ in range(1)])
nightstand = Assets(description="A modern nightstand with two drawers and a curved backrest. It features sleek handles and a sturdy design.", size=[0.45, 0.55, 0.65], placements=[AssetInstance() for _ in range(1)])
potted_plant = Assets(description="A tall potted plant with lush green leaves, housed in a white cylindrical pot supported by wooden legs.", size=[0.75, 0.75, 1.75], placements=[AssetInstance() for _ in range(1)])
footstool = Assets(description="A beige chaise lounge with a tufted cushion and a cylindrical bolster pillow, supported by dark wooden legs.", size=[1.65, 0.75, 0.85], placements=[AssetInstance() for _ in range(1)])
drawer_chest_B = Assets(description="A classic-style bed with an ornate headboard and footboard, featuring a light-colored fabric cover and two patterned pillows.", size=[2.15, 1.65, 1.35], placements=[AssetInstance() for _ in range(1)])

fabric_sculpture[0].instance_id = 'fabric_sculpture_0'
dress[0].instance_id = 'dress_0'
sideboard[0].instance_id = 'sideboard_0'
drawer_chest_A[0].instance_id = 'drawer_chest_A_0'
nightstand[0].instance_id = 'nightstand_0'
potted_plant[0].instance_id = 'potted_plant_0'
footstool[0].instance_id = 'footstool_0'
drawer_chest_B[0].instance_id = 'drawer_chest_B_0'
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

fabric_sculpture[0].position = [7.504384460169912, 2.4935906407822293, 0.925]
fabric_sculpture[0].rotation = [0, 0, 0]
dress[0].position = [7.473469518571397, 1.3412565941514853, 0.575]
dress[0].rotation = [0, 0, 0]
sideboard[0].position = [2.907209039314721, 0.4192856669492231, 0.41]
sideboard[0].rotation = [0, 0, 0]
drawer_chest_A[0].position = [6.114708764529057, 3.3912134536422416, 0.675]
drawer_chest_A[0].rotation = [0, 0, 0]
nightstand[0].position = [1.5467677248212206, 3.738684877335164, 0.325]
nightstand[0].rotation = [0, 0, 0]
potted_plant[0].position = [0.6827321867107723, 2.243821615512774, 0.875]
potted_plant[0].rotation = [0, 0, 0]
footstool[0].position = [3.39725520629684, 1.6907916592678236, 0.425]
footstool[0].rotation = [0, 0, 0]
drawer_chest_B[0].position = [3.408872786056608, 0.26930331422783854, 0.675]
drawer_chest_B[0].rotation = [0, 0, 0]
fabric_sculpture[0].position = [7.504384460169912, 2.4935906407822293, 0.925]
fabric_sculpture[0].rotation = [0, 0, 0]
dress[0].position = [7.473469518571397, 1.3412565941514853, 0.575]
dress[0].rotation = [0, 0, 0]
sideboard[0].position = [2.907209039314721, 0.4192856669492231, 0.41]
sideboard[0].rotation = [0, 0, 0]
drawer_chest_A[0].position = [6.114708764529057, 3.3912134536422416, 0.675]
drawer_chest_A[0].rotation = [0, 0, 0]
nightstand[0].position = [1.5467677248212206, 3.738684877335164, 0.325]
nightstand[0].rotation = [0, 0, 0]
potted_plant[0].position = [0.6827321867107723, 2.243821615512774, 0.875]
potted_plant[0].rotation = [0, 0, 0]
footstool[0].position = [3.39725520629684, 1.6907916592678236, 0.425]
footstool[0].rotation = [0, 0, 0]
drawer_chest_B[0].position = [3.408872786056608, 0.26930331422783854, 0.675]
drawer_chest_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the two bed-like drawer chests along the lower and upper walls of the
# left-hand room. Their facing edges have a 0.48 m gap, satisfying the requested
# proximity while avoiding overlap.
drawer_chest_A[0].position = [1.45, 0.825, 0.675]
drawer_chest_A[0].rotation = [0, 0, radians(0)]

drawer_chest_B[0].position = [1.45, 2.955, 0.675]
drawer_chest_B[0].rotation = [0, 0, radians(0)]

# Place the nightstand in the unused lower-right corner of the left room,
# beside drawer_chest_A and away from circulation routes.
nightstand[0].position = [3.35, 0.275, 0.325]
nightstand[0].rotation = [0, 0, radians(150)]

# The dress is mounted against the upper wall in the gap to the right of
# drawer_chest_B. Its shallow dimension is perpendicular to the wall.
dress[0].position = [3.50, 3.74, 0.575]
dress[0].rotation = [0, 0, radians(-90)]

# Place the sideboard along the far-right wall, facing into the room.
sideboard[0].position = [8.49, 1.95, 0.41]
sideboard[0].rotation = [0, 0, radians(180)]

# Put the plant against the right wall in the upper-right corner, where it does
# not obstruct either door or the window.
potted_plant[0].position = [8.325, 3.405, 0.875]
potted_plant[0].rotation = [0, 0, radians(-135)]

# Place the chaise-like footstool against the upper wall of the right room.
# Its left edge remains beyond x=6.0, keeping the top doorway approach clear.
footstool[0].position = [6.90, 3.405, 0.425]
footstool[0].rotation = [0, 0, radians(-90)]

# Display the sculpture in the lower-right area, separated from the sideboard
# and leaving the door at (5.94, 1.37) and window frontage unobstructed.
fabric_sculpture[0].position = [8.20, 0.60, 0.925]
fabric_sculpture[0].rotation = [0, 0, radians(155)]


# Fixed anchors strongly preserve the non-overlapping layout and clear routes.
drawer_A_anchor = AssetInstance(position=[1.45, 0.825, 0.675])
drawer_B_anchor = AssetInstance(position=[1.45, 2.955, 0.675])
nightstand_anchor = AssetInstance(position=[3.35, 0.275, 0.325])
dress_anchor = AssetInstance(position=[3.50, 3.74, 0.575])
sideboard_anchor = AssetInstance(position=[8.49, 1.95, 0.41])
plant_anchor = AssetInstance(position=[8.325, 3.405, 0.875])
footstool_anchor = AssetInstance(position=[6.90, 3.405, 0.425])
sculpture_anchor = AssetInstance(position=[8.20, 0.60, 0.925])

solver.distance_constraint(
    drawer_chest_A[0], drawer_A_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    drawer_chest_B[0], drawer_B_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    nightstand[0], nightstand_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    dress[0], dress_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    sideboard[0], sideboard_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    potted_plant[0], plant_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    footstool[0], footstool_anchor, 0, 0, weight=10
)
solver.distance_constraint(
    fabric_sculpture[0], sculpture_anchor, 0, 0, weight=10
)

# Wall constraints preserve the intended furniture-to-wall relationships.
solver.against_wall(drawer_chest_A[0], walls[12])
solver.against_wall(drawer_chest_B[0], walls[6])
solver.against_wall(nightstand[0], walls[12])
solver.against_wall(dress[0], walls[6])
solver.against_wall(sideboard[0], walls[3])
solver.against_wall(potted_plant[0], walls[3])
solver.against_wall(footstool[0], walls[4])

# The bed-like drawer chests have 1.65 m depth along y. Constraining their
# centers to 1.65–2.15 m apart prevents overlap while keeping the gap between
# their bounding boxes no greater than the requested 0.50 m.
solver.distance_constraint(
    drawer_chest_B[0], drawer_chest_A[0], 1.65, 2.15, weight=10
)

# Orientation references for objects whose facing direction should remain
# parallel or perpendicular to their supporting wall.
east_orientation = AssetInstance(rotation=[0, 0, radians(0)])
south_orientation = AssetInstance(rotation=[0, 0, radians(-90)])

solver.align_with(drawer_chest_A[0], east_orientation)
solver.align_with(drawer_chest_B[0], east_orientation)
solver.align_with(dress[0], south_orientation)

# Semantic facing constraints orient the remaining objects toward nearby
# furniture or toward the usable interior of their respective room.
solver.point_towards(nightstand[0], drawer_chest_A[0])
solver.point_towards(sideboard[0], AssetInstance(position=[7.00, 1.95, 0.41]))
solver.point_towards(potted_plant[0], AssetInstance(position=[7.20, 2.30, 0.875]))
solver.point_towards(footstool[0], AssetInstance(position=[6.90, 2.20, 0.425]))
solver.point_towards(
    fabric_sculpture[0], AssetInstance(position=[7.00, 1.20, 0.925])
)

solver.constraints = []
nightstand[0].position = [3.3499999046325684, 0.3499085605144501, 0.32499998807907104]
nightstand[0].rotation = [0, 0, 2.3421810550437843]
nightstand[0].optimize = 2
drawer_chest_A[0].position = [1.2588276863098145, 1.0847305059432983, 0.675000011920929]
drawer_chest_A[0].rotation = [0, 0, 0.2735417886272073]
drawer_chest_A[0].optimize = 2
dress[0].position = [3.5, 3.740000009536743, 0.574999988079071]
dress[0].rotation = [0, 0, -1.5657023853621785]
dress[0].optimize = 2
fabric_sculpture[0].position = [8.199999809265137, 0.6000000238418579, 0.925000011920929]
fabric_sculpture[0].rotation = [0, 0, 2.7146851015786244]
fabric_sculpture[0].optimize = 2
sideboard[0].position = [8.489270210266113, 1.950965404510498, 0.4099999964237213]
sideboard[0].rotation = [0, 0, -3.1392802138115763]
sideboard[0].optimize = 2
drawer_chest_B[0].position = [1.2679905891418457, 2.7295162677764893, 0.675000011920929]
drawer_chest_B[0].rotation = [0, 0, -0.21215546606633737]
drawer_chest_B[0].optimize = 2
potted_plant[0].position = [8.168972969055176, 3.254452705383301, 0.875]
potted_plant[0].rotation = [0, 0, -2.0728762690862226]
potted_plant[0].optimize = 2
footstool[0].position = [6.706005096435547, 2.8902788162231445, 0.42500001192092896]
footstool[0].rotation = [0, 0, -1.34060405013425]
footstool[0].optimize = 2

