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
fabric_sculpture = Assets(description="A flowing fabric sculpture with intricate folds and drapes, standing upright on a black base.", size=[0.40, 0.55, 1.65], placements=[AssetInstance() for _ in range(1)])
dress = Assets(description="A black sleeveless dress with a subtle pattern, featuring a V-neckline and a flared hem. It is displayed on a hanger against a plain background.", size=[0.12, 0.65, 1.15], placements=[AssetInstance() for _ in range(1)])
sideboard = Assets(description="A sleek console table with a dark, possibly marble or stone top and metallic legs that curve outward for support. It has a modern design suitable for entryways or living spaces.", size=[0.40, 1.40, 0.80], placements=[AssetInstance() for _ in range(1)])
drawer_chest_A = Assets(description="A classic-style bed with an ornate headboard and footboard, featuring a light-colored fabric cover and two patterned pillows.", size=[2.15, 1.60, 1.30], placements=[AssetInstance() for _ in range(1)])
nightstand = Assets(description="A modern nightstand with two drawers and a curved backrest. It features sleek handles and a sturdy design.", size=[0.45, 0.55, 0.65], placements=[AssetInstance() for _ in range(1)])
potted_plant = Assets(description="A tall potted plant with lush green leaves, housed in a white cylindrical pot supported by wooden legs.", size=[0.65, 0.65, 1.65], placements=[AssetInstance() for _ in range(1)])
footstool = Assets(description="A beige chaise lounge with a tufted cushion and a cylindrical bolster pillow, supported by dark wooden legs.", size=[0.70, 1.65, 0.75], placements=[AssetInstance() for _ in range(1)])
drawer_chest_B = Assets(description="A classic-style bed with an ornate headboard and footboard, featuring a light-colored fabric cover and two patterned pillows.", size=[2.15, 1.60, 1.30], placements=[AssetInstance() for _ in range(1)])

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

fabric_sculpture[0].position = [7.301295879344859, 3.0332394723022844, 0.825]
fabric_sculpture[0].rotation = [0, 0, 0]
dress[0].position = [2.893436634123396, 0.34513205382292295, 0.575]
dress[0].rotation = [0, 0, 0]
sideboard[0].position = [0.05576952303277268, 1.3380170387921606, 0.4]
sideboard[0].rotation = [0, 0, 0]
drawer_chest_A[0].position = [5.069735736217522, 2.548948453579907, 0.65]
drawer_chest_A[0].rotation = [0, 0, 0]
nightstand[0].position = [6.223607945098007, 0.11436215882269016, 0.325]
nightstand[0].rotation = [0, 0, 0]
potted_plant[0].position = [5.4941299888445085, 3.1841933599990124, 0.825]
potted_plant[0].rotation = [0, 0, 0]
footstool[0].position = [8.09768588507538, 2.0884061632610758, 0.375]
footstool[0].rotation = [0, 0, 0]
drawer_chest_B[0].position = [4.325504110110978, 3.639393924614357, 0.65]
drawer_chest_B[0].rotation = [0, 0, 0]
fabric_sculpture[0].position = [7.301295879344859, 3.0332394723022844, 0.825]
fabric_sculpture[0].rotation = [0, 0, 0]
dress[0].position = [2.893436634123396, 0.34513205382292295, 0.575]
dress[0].rotation = [0, 0, 0]
sideboard[0].position = [0.05576952303277268, 1.3380170387921606, 0.4]
sideboard[0].rotation = [0, 0, 0]
drawer_chest_A[0].position = [5.069735736217522, 2.548948453579907, 0.65]
drawer_chest_A[0].rotation = [0, 0, 0]
nightstand[0].position = [6.223607945098007, 0.11436215882269016, 0.325]
nightstand[0].rotation = [0, 0, 0]
potted_plant[0].position = [5.4941299888445085, 3.1841933599990124, 0.825]
potted_plant[0].rotation = [0, 0, 0]
footstool[0].position = [8.09768588507538, 2.0884061632610758, 0.375]
footstool[0].rotation = [0, 0, 0]
drawer_chest_B[0].position = [4.325504110110978, 3.639393924614357, 0.65]
drawer_chest_B[0].rotation = [0, 0, 0]

solver.constraints = []

# The two "drawer chest" assets are bed-sized, so place them as parallel
# beds in the left wing. "Within 0.50 m" is interpreted as edge clearance:
# their 1.60 m widths plus a 0.50 m aisle imply 2.10 m between centers.
# A literal 0.50 m center distance would necessarily overlap these assets.
drawer_chest_A[0].position = [1.325, 0.85, 0.65]
drawer_chest_A[0].rotation = [0, 0, 0]
drawer_chest_B[0].position = [1.325, 2.95, 0.65]
drawer_chest_B[0].rotation = [0, 0, 0]

# Rotate the nightstand so its 0.45 m dimension fits the shared 0.50 m
# bedside aisle, with a little clearance from both beds.
nightstand[0].position = [0.85, 1.90, 0.325]
nightstand[0].rotation = [0, 0, radians(90)]

# A freestanding sculpture occupies the lower-right corner of the left
# wing, outside the route around the feet of the beds.
fabric_sculpture[0].position = [3.55, 0.45, 0.825]
fabric_sculpture[0].rotation = [0, 0, radians(180)]

# The right wing's east wall supports a console/display arrangement.
# Neither this furniture nor the plant blocks the south-facing window.
sideboard[0].position = [8.50, 2.65, 0.40]
sideboard[0].rotation = [0, 0, radians(180)]

# Use the console as the support for the displayed dress; no additional
# hanger or display furniture is introduced.
dress[0].position = [8.50, 2.65, 1.375]
dress[0].rotation = [0, 0, radians(180)]

potted_plant[0].position = [8.375, 0.50, 0.825]
potted_plant[0].rotation = [0, 0, radians(180)]

# Turn the chaise parallel to the north wall, entirely east of the
# upper door's approach. Account for this wall's slight slope.
chaise_wall_y = 3.78 + (6.85 - 5.87) * (0.01 / 2.83)
footstool[0].position = [6.85, chaise_wall_y - 0.35, 0.375]
footstool[0].rotation = [0, 0, radians(270)]

# Preserve the required wall contacts first.
solver.against_wall(potted_plant[0], walls[3])
solver.against_wall(footstool[0], walls[4])
solver.against_wall(sideboard[0], walls[3])

# Fixed-position constraints preserve the nonoverlapping layout and leave
# the floor immediately inside both doors clear. These are reference
# points, not additional scene objects.
for layout_asset in (
    drawer_chest_A, drawer_chest_B, nightstand,
    fabric_sculpture, sideboard, potted_plant, footstool
):
    solver.distance_constraint(
        layout_asset[0],
        AssetInstance(position=list(layout_asset[0].position)),
        0.0, 0.0, weight=10
    )
    solver.align_with(
        layout_asset[0],
        AssetInstance(rotation=list(layout_asset[0].rotation)),
        angle=0
    )

# Maintain the bed pairing and its half-meter edge-to-edge aisle.
solver.distance_constraint(
    drawer_chest_A[0], drawer_chest_B[0], 2.10, 2.10, weight=10
)
solver.distance_constraint(
    drawer_chest_B[0], drawer_chest_A[0], 2.10, 2.10, weight=10
)
solver.align_with(drawer_chest_B[0], drawer_chest_A[0])

# Keep the shared nightstand between the beds.
for bed_asset in (drawer_chest_A, drawer_chest_B):
    bedside_distance = (
        (0.85 - 1.325) ** 2
        + (1.90 - bed_asset[0].position[1]) ** 2
        + (0.325 - 0.65) ** 2
    ) ** 0.5
    solver.distance_constraint(
        nightstand[0], bed_asset[0],
        bedside_distance, bedside_distance
    )

# The dress sits on the console, centered on its usable surface.
# Center distance includes the vertical offset, as required by the API.
solver.on_top_of(dress[0], sideboard[0])
solver.distance_constraint(dress[0], sideboard[0], 0.975, 0.975, weight=10)
solver.align_with(dress[0], sideboard[0])

solver.constraints = []
drawer_chest_A[0].position = [1.3250000476837158, 0.8500000238418579, 0.6499999761581421]
drawer_chest_A[0].rotation = [0, 0, 0.021991148286022624]
drawer_chest_A[0].optimize = 2
drawer_chest_B[0].position = [1.3250000476837158, 2.950000047683716, 0.6499999761581421]
drawer_chest_B[0].rotation = [0, 0, 0.021990960680793124]
drawer_chest_B[0].optimize = 2
dress[0].position = [8.374282836914062, 2.849669933319092, 1.375]
dress[0].rotation = [0, 0, -1.5708652369943699]
dress[0].optimize = 2
fabric_sculpture[0].position = [3.549999952316284, 0.44999998807907104, 0.824999988079071]
fabric_sculpture[0].rotation = [0, 0, -3.1321678761290697]
fabric_sculpture[0].optimize = 2
footstool[0].position = [5.818398952484131, 3.4249284267425537, 0.375]
footstool[0].rotation = [0, 0, -1.5672069078118704]
footstool[0].optimize = 2
sideboard[0].position = [8.000616073608398, 2.64969539642334, 0.4000000059604645]
sideboard[0].rotation = [0, 0, -1.570864533654537]
sideboard[0].optimize = 2
potted_plant[0].position = [8.375, 0.5, 0.824999988079071]
potted_plant[0].rotation = [0, 0, 1.5709247614675894]
potted_plant[0].optimize = 2
nightstand[0].position = [0.6419768333435059, 1.9145053625106812, 0.32499998807907104]
nightstand[0].rotation = [0, 0, 1.586504290712113]
nightstand[0].optimize = 2

