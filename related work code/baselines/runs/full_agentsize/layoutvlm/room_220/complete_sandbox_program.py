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
    Wall(corner1=[3.39, 0.00, 0.00], corner2=[3.39, 4.17, 0.00]),
    Wall(corner1=[3.39, 4.17, 0.00], corner2=[0.00, 4.17, 0.00]),
    Wall(corner1=[0.00, 4.17, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.39, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
combination_sofa = Assets(description="combination sofa", size=[0.90, 2.25, 0.85], placements=[AssetInstance() for _ in range(1)])
stool_A = Assets(description="stool", size=[0.42, 0.42, 0.46], placements=[AssetInstance() for _ in range(1)])
wardrobe_A = Assets(description="wardrobe", size=[0.60, 1.20, 2.20], placements=[AssetInstance() for _ in range(1)])
wardrobe_B = Assets(description="wardrobe", size=[0.58, 1.00, 2.10], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[1.50, 2.00, 0.02], placements=[AssetInstance() for _ in range(1)])
stool_B = Assets(description="stool", size=[0.45, 0.45, 0.45], placements=[AssetInstance() for _ in range(1)])

combination_sofa[0].instance_id = 'combination_sofa_0'
stool_A[0].instance_id = 'stool_A_0'
wardrobe_A[0].instance_id = 'wardrobe_A_0'
wardrobe_B[0].instance_id = 'wardrobe_B_0'
carpet[0].instance_id = 'carpet_0'
stool_B[0].instance_id = 'stool_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

combination_sofa[0].position = [2.541708312380318, 2.1409739459746704, 0.425]
combination_sofa[0].rotation = [0, 0, 0]
stool_A[0].position = [0.32678877512428167, 3.215958257698479, 0.23]
stool_A[0].rotation = [0, 0, 0]
wardrobe_A[0].position = [2.4534937355657873, 2.9178763793774327, 1.1]
wardrobe_A[0].rotation = [0, 0, 0]
wardrobe_B[0].position = [0.03917679442549757, 3.1774554044993573, 1.05]
wardrobe_B[0].rotation = [0, 0, 0]
carpet[0].position = [0.9385297250547652, 3.164012031765578, 0.01]
carpet[0].rotation = [0, 0, 0]
stool_B[0].position = [0.2753361804864876, 1.1459776561571184, 0.225]
stool_B[0].rotation = [0, 0, 0]
combination_sofa[0].position = [2.541708312380318, 2.1409739459746704, 0.425]
combination_sofa[0].rotation = [0, 0, 0]
stool_A[0].position = [0.32678877512428167, 3.215958257698479, 0.23]
stool_A[0].rotation = [0, 0, 0]
wardrobe_A[0].position = [2.4534937355657873, 2.9178763793774327, 1.1]
wardrobe_A[0].rotation = [0, 0, 0]
wardrobe_B[0].position = [0.03917679442549757, 3.1774554044993573, 1.05]
wardrobe_B[0].rotation = [0, 0, 0]
carpet[0].position = [0.9385297250547652, 3.164012031765578, 0.01]
carpet[0].rotation = [0, 0, 0]
stool_B[0].position = [0.2753361804864876, 1.1459776561571184, 0.225]
stool_B[0].rotation = [0, 0, 0]

solver.constraints = []

# The sofa is placed along the left wall, facing across the room toward
# wardrobe_A. Keeping this furniture group below y=3.15 leaves a clear
# approach to the door in the upper-right corner.
combination_sofa[0].position = [0.45, 2.55, 0.425]
combination_sofa[0].rotation = [0, 0, radians(0)]

# stool_A sits on the carpet as a movable seat, away from both the window
# and the door circulation route.
stool_A[0].position = [2.15, 1.10, 0.25]
stool_A[0].rotation = [0, 0, radians(140)]

# wardrobe_A is the wardrobe that the sofa faces. Its back is against the
# right wall, and its front points into the room toward the sofa.
wardrobe_A[0].position = [3.09, 2.55, 1.10]
wardrobe_A[0].rotation = [0, 0, radians(180)]

# The second wardrobe shares the right wall but is separated from wardrobe_A,
# leaving usable clearance between them.
wardrobe_B[0].position = [3.10, 0.65, 1.05]
wardrobe_B[0].rotation = [0, 0, radians(180)]

# The carpet defines the central usable area while remaining clear of the
# bottom-wall window and the upper-right door approach.
carpet[0].position = [1.70, 1.55, 0.01]
carpet[0].rotation = [0, 0, radians(0)]

# stool_B (the listed o0005 stool) is beside the sofa. Their bounding-box
# surfaces are 0.075 m apart, satisfying the requested maximum 0.10 m gap.
stool_B[0].position = [1.20, 2.55, 0.245]
stool_B[0].rotation = [0, 0, radians(180)]


# Important wall relationships and the required sofa-to-wardrobe orientation.
solver.against_wall(combination_sofa[0], walls[2])
solver.point_towards(combination_sofa[0], wardrobe_A[0])

solver.against_wall(wardrobe_A[0], walls[0])
solver.point_towards(wardrobe_A[0], combination_sofa[0])

solver.against_wall(wardrobe_B[0], walls[0])
solver.align_with(wardrobe_B[0], wardrobe_A[0])


# Preserve the sofa/wardrobe grouping across the room. Their equal y-coordinate
# makes the sofa face the center of wardrobe_A directly.
solver.distance_constraint(
    combination_sofa[0], wardrobe_A[0],
    min_distance=2.64, max_distance=2.64, weight=10
)

# Keep the two wardrobes separated along the right wall.
solver.distance_constraint(
    wardrobe_B[0], wardrobe_A[0],
    min_distance=1.85, max_distance=1.95, weight=10
)


# The center-distance interval below corresponds to a 0–0.10 m surface gap:
# sofa half-width 0.45 + stool half-width 0.225 + allowed gap 0–0.10.
solver.distance_constraint(
    stool_B[0], combination_sofa[0],
    min_distance=0.675, max_distance=0.775, weight=10
)
solver.point_towards(stool_B[0], combination_sofa[0])
solver.on_top_of(stool_B[0], carpet[0])


# Anchor the carpet's functional center and align it with the sofa.
carpet_center = AssetInstance(position=[1.70, 1.55, 0.01])
solver.distance_constraint(
    carpet[0], carpet_center,
    min_distance=0, max_distance=0, weight=10
)
solver.align_with(carpet[0], combination_sofa[0])


# Keep stool_A at its non-overlapping location on the carpet and orient it
# toward the seating group.
stool_A_center = AssetInstance(position=[2.15, 1.10, 0.25])
solver.distance_constraint(
    stool_A[0], stool_A_center,
    min_distance=0, max_distance=0, weight=10
)
solver.point_towards(stool_A[0], combination_sofa[0])
solver.on_top_of(stool_A[0], carpet[0])

solver.constraints = []
combination_sofa[0].position = [0.45507127046585083, 2.549999952316284, 0.42500001192092896]
combination_sofa[0].rotation = [0, 0, -0.004511888118277761]
combination_sofa[0].optimize = 2
wardrobe_B[0].position = [3.1039154529571533, 0.6499999761581421, 1.0499999523162842]
wardrobe_B[0].rotation = [0, 0, -3.1373744901121965]
wardrobe_B[0].optimize = 2
wardrobe_A[0].position = [3.0925893783569336, 2.549999952316284, 1.100000023841858]
wardrobe_A[0].rotation = [0, 0, -3.1389426356292884]
wardrobe_A[0].optimize = 2
stool_A[0].position = [2.1500000953674316, 1.100000023841858, 0.25]
stool_A[0].rotation = [0, 0, 2.456027337095766]
stool_A[0].optimize = 2
stool_B[0].position = [1.2003282308578491, 2.5373613834381104, 0.2449999898672104]
stool_B[0].rotation = [0, 0, -3.1290262823329655]
stool_B[0].optimize = 2
carpet[0].position = [1.7000000476837158, 1.5499999523162842, 0.009999999776482582]
carpet[0].rotation = [0, 0, -0.02754080323018995]
carpet[0].optimize = 2

