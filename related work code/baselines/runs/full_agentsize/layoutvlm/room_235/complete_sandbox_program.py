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
    Wall(corner1=[2.70, 0.00, 0.00], corner2=[2.70, 3.20, 0.00]),
    Wall(corner1=[2.70, 3.20, 0.00], corner2=[0.00, 3.20, 0.00]),
    Wall(corner1=[0.00, 3.20, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.70, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
wardrobe = Assets(description="wardrobe", size=[0.60, 1.20, 2.00], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.00, 1.40, 0.55], placements=[AssetInstance() for _ in range(1)])
nightstand_A = Assets(description="nightstand", size=[0.40, 0.45, 0.50], placements=[AssetInstance() for _ in range(1)])
desk_lamp = Assets(description="desk lamp", size=[0.25, 0.25, 0.45], placements=[AssetInstance() for _ in range(1)])
nightstand_B = Assets(description="nightstand", size=[0.40, 0.45, 0.50], placements=[AssetInstance() for _ in range(1)])

wardrobe[0].instance_id = 'wardrobe_0'
bed[0].instance_id = 'bed_0'
nightstand_A[0].instance_id = 'nightstand_A_0'
desk_lamp[0].instance_id = 'desk_lamp_0'
nightstand_B[0].instance_id = 'nightstand_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

wardrobe[0].position = [2.004763435765435, 2.4802821055653035, 1.0]
wardrobe[0].rotation = [0, 0, 0]
bed[0].position = [2.292885358458925, 1.9977931647115894, 0.275]
bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [2.5726043026032768, 2.936917180889457, 0.25]
nightstand_A[0].rotation = [0, 0, 0]
desk_lamp[0].position = [2.369816093514754, 0.10273943089320951, 0.225]
desk_lamp[0].rotation = [0, 0, 0]
nightstand_B[0].position = [2.0449824940897323, 2.714734694117817, 0.25]
nightstand_B[0].rotation = [0, 0, 0]
wardrobe[0].position = [2.004763435765435, 2.4802821055653035, 1.0]
wardrobe[0].rotation = [0, 0, 0]
bed[0].position = [2.292885358458925, 1.9977931647115894, 0.275]
bed[0].rotation = [0, 0, 0]
nightstand_A[0].position = [2.5726043026032768, 2.936917180889457, 0.25]
nightstand_A[0].rotation = [0, 0, 0]
desk_lamp[0].position = [2.369816093514754, 0.10273943089320951, 0.225]
desk_lamp[0].rotation = [0, 0, 0]
nightstand_B[0].position = [2.0449824940897323, 2.714734694117817, 0.25]
nightstand_B[0].rotation = [0, 0, 0]

solver.constraints = []

# The bed runs along the left wall, leaving a clear circulation aisle on the
# right from the door. Its head is near the window wall, but its low height
# avoids substantially obstructing the window.
bed[0].position = [0.70, 2.20, 0.275]
bed[0].rotation = [0, 0, radians(90)]

# The wardrobe is placed against the lower wall, well to the left of the door
# and its approach area. Rotating it makes its shallow dimension face the room.
wardrobe[0].position = [0.70, 0.30, 1.00]
wardrobe[0].rotation = [0, 0, radians(90)]

# Both nightstands occupy the open side of the bed. They are separated along
# its length so that neither overlaps the bed or blocks the central aisle.
nightstand_A[0].position = [1.65, 2.85, 0.25]
nightstand_A[0].rotation = [0, 0, radians(90)]

nightstand_B[0].position = [1.65, 1.55, 0.25]
nightstand_B[0].rotation = [0, 0, radians(90)]

# The lamp is centered on the upper nightstand. Its z-coordinate places its
# base at the 0.50 m-high top surface of the nightstand.
desk_lamp[0].position = [1.65, 2.85, 0.725]
desk_lamp[0].rotation = [0, 0, radians(90)]


# Important wall relationships come first. These keep the large furniture on
# the room perimeter and preserve the clear route inward from the door.
solver.against_wall(bed[0], walls[2])
solver.against_wall(wardrobe[0], walls[3])

# Keep the bed and wardrobe parallel to one another. With their initialized
# rotations, the bed extends along y and the wardrobe faces into the room.
solver.align_with(bed[0], wardrobe[0])
solver.align_with(wardrobe[0], bed[0])

# Each nightstand remains beside the bed rather than drifting into the aisle.
# Their initialized positions choose the desired side of the distance circles.
solver.distance_constraint(
    nightstand_A[0], bed[0],
    min_distance=1.15, max_distance=1.15, weight=10
)
solver.distance_constraint(
    nightstand_B[0], bed[0],
    min_distance=1.15, max_distance=1.15, weight=10
)

# Preserve the useful separation between the two nightstands and prevent them
# from converging onto the same portion of the bedside.
solver.distance_constraint(
    nightstand_A[0], nightstand_B[0],
    min_distance=1.30, max_distance=1.30, weight=10
)
solver.distance_constraint(
    nightstand_B[0], nightstand_A[0],
    min_distance=1.30, max_distance=1.30, weight=10
)

solver.align_with(nightstand_A[0], bed[0])
solver.align_with(nightstand_B[0], bed[0])

# The lamp must remain supported by nightstand A. The center-distance interval
# accounts for the 0.475 m vertical difference between their bounding-box
# centers after the on-top constraint is applied.
solver.on_top_of(desk_lamp[0], nightstand_A[0])
solver.distance_constraint(
    desk_lamp[0], nightstand_A[0],
    min_distance=0.45, max_distance=0.52, weight=10
)
solver.align_with(desk_lamp[0], nightstand_A[0])

solver.constraints = []
bed[0].position = [1.1915203332901, 2.171243667602539, 0.2750000059604645]
bed[0].rotation = [0, 0, 0.39171984312155317]
bed[0].optimize = 2
nightstand_A[0].position = [1.648805022239685, 2.9130971431732178, 0.25]
nightstand_A[0].rotation = [0, 0, 0.39708079349418346]
nightstand_A[0].optimize = 2
desk_lamp[0].position = [1.5513800382614136, 2.628257989883423, 0.7250000238418579]
desk_lamp[0].rotation = [0, 0, 0.41648955159517564]
desk_lamp[0].optimize = 2
wardrobe[0].position = [0.699999988079071, 0.3000871241092682, 1.0]
wardrobe[0].rotation = [0, 0, 1.5707343612340758]
wardrobe[0].optimize = 2
nightstand_B[0].position = [1.362817406654358, 1.6487070322036743, 0.25]
nightstand_B[0].rotation = [0, 0, 0.4037876504622891]
nightstand_B[0].optimize = 2

