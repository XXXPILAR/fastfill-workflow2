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
    Wall(corner1=[3.16, 0.00, 0.00], corner2=[3.16, 4.29, 0.00]),
    Wall(corner1=[3.16, 4.29, 0.00], corner2=[1.35, 4.29, 0.00]),
    Wall(corner1=[1.35, 4.29, 0.00], corner2=[1.35, 5.43, 0.00]),
    Wall(corner1=[1.35, 5.43, 0.00], corner2=[0.00, 5.43, 0.00]),
    Wall(corner1=[0.00, 5.43, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.16, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
desk = Assets(description="desk", size=[0.60, 1.20, 0.75], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.45, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
chair = Assets(description="chair", size=[0.52, 0.48, 0.85], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.00, 1.40, 0.55], placements=[AssetInstance() for _ in range(1)])
nightstand = Assets(description="nightstand", size=[0.40, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.45, 0.90, 1.80], placements=[AssetInstance() for _ in range(1)])
dresser = Assets(description="dresser", size=[0.50, 1.10, 0.85], placements=[AssetInstance() for _ in range(1)])

desk[0].instance_id = 'desk_0'
cabinet_A[0].instance_id = 'cabinet_A_0'
chair[0].instance_id = 'chair_0'
bed[0].instance_id = 'bed_0'
nightstand[0].instance_id = 'nightstand_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
dresser[0].instance_id = 'dresser_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

desk[0].position = [1.2768726104687298, 4.351919386644401, 0.375]
desk[0].rotation = [0, 0, 0]
cabinet_A[0].position = [0.800403434363133, 4.704590901869984, 0.9]
cabinet_A[0].rotation = [0, 0, 0]
chair[0].position = [2.435422399838771, 4.1197507321725055, 0.425]
chair[0].rotation = [0, 0, 0]
bed[0].position = [0.8994176838291078, 5.100581839502805, 0.275]
bed[0].rotation = [0, 0, 0]
nightstand[0].position = [0.7013093856819508, 5.090602011821984, 0.275]
nightstand[0].rotation = [0, 0, 0]
cabinet_B[0].position = [2.6681835467428163, 0.07432385538801407, 0.9]
cabinet_B[0].rotation = [0, 0, 0]
dresser[0].position = [2.323191412147802, 0.9674117645065146, 0.425]
dresser[0].rotation = [0, 0, 0]
desk[0].position = [1.2768726104687298, 4.351919386644401, 0.375]
desk[0].rotation = [0, 0, 0]
cabinet_A[0].position = [0.800403434363133, 4.704590901869984, 0.9]
cabinet_A[0].rotation = [0, 0, 0]
chair[0].position = [2.435422399838771, 4.1197507321725055, 0.425]
chair[0].rotation = [0, 0, 0]
bed[0].position = [0.8994176838291078, 5.100581839502805, 0.275]
bed[0].rotation = [0, 0, 0]
nightstand[0].position = [0.7013093856819508, 5.090602011821984, 0.275]
nightstand[0].rotation = [0, 0, 0]
cabinet_B[0].position = [2.6681835467428163, 0.07432385538801407, 0.9]
cabinet_B[0].rotation = [0, 0, 0]
dresser[0].position = [2.323191412147802, 0.9674117645065146, 0.425]
dresser[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the bed across the main room, leaving the bottom doorway and both
# entrances to the upper alcove unobstructed. cabinet_B and cabinet_A flank
# the bed on the left and right respectively.
desk[0].position = [2.45, 3.99, 0.375]
desk[0].rotation = [0, 0, radians(-90)]

cabinet_A[0].position = [2.935, 2.25, 0.90]
cabinet_A[0].rotation = [0, 0, radians(180)]

chair[0].position = [2.45, 3.38, 0.425]
chair[0].rotation = [0, 0, radians(90)]

bed[0].position = [1.55, 2.25, 0.275]
bed[0].rotation = [0, 0, radians(0)]

nightstand[0].position = [2.96, 1.15, 0.275]
nightstand[0].rotation = [0, 0, radians(180)]

cabinet_B[0].position = [0.225, 2.25, 0.90]
cabinet_B[0].rotation = [0, 0, radians(0)]

dresser[0].position = [0.25, 3.55, 0.425]
dresser[0].rotation = [0, 0, radians(0)]


# Keep the bed between the two cabinets. The bed faces cabinet_A as required.
# These high-priority constraints preserve the core bedroom composition.
solver.distance_constraint(bed[0], cabinet_A[0], 1.30, 1.50, weight=10)
solver.distance_constraint(bed[0], cabinet_B[0], 1.25, 1.45, weight=10)
solver.point_towards(bed[0], cabinet_A[0])

# Place the cabinets against opposite side walls and orient both toward the
# bed. Their bounded separation from the bed maintains non-overlapping gaps.
solver.against_wall(cabinet_A[0], walls[0])
solver.point_towards(cabinet_A[0], bed[0])
solver.distance_constraint(cabinet_A[0], bed[0], 1.30, 1.50, weight=10)

solver.against_wall(cabinet_B[0], walls[4])
solver.point_towards(cabinet_B[0], bed[0])
solver.distance_constraint(cabinet_B[0], bed[0], 1.25, 1.45, weight=10)

# Form a compact work area against the upper wall of the main rectangular
# portion. It remains to the right of the doorway centered at (1.35, 4.96).
solver.against_wall(desk[0], walls[1])
solver.point_towards(desk[0], chair[0])
solver.distance_constraint(desk[0], chair[0], 0.56, 0.75, weight=10)

# Keep the chair directly in front of and facing the desk, while retaining
# enough separation for the two bounding boxes not to overlap.
solver.distance_constraint(chair[0], desk[0], 0.56, 0.75, weight=10)
solver.point_towards(chair[0], desk[0])

# Put the nightstand against the lower part of the right wall, beside the bed
# and away from the wide bottom doorway.
solver.against_wall(nightstand[0], walls[0])
solver.distance_constraint(nightstand[0], bed[0], 1.60, 1.90, weight=5)
solver.point_towards(nightstand[0], bed[0])

# Place the dresser against the left wall below the upper doorway. It faces
# into the room and stays separated from both cabinet_B and the bed.
solver.against_wall(dresser[0], walls[4])
solver.distance_constraint(dresser[0], cabinet_B[0], 1.20, 1.45, weight=5)
solver.distance_constraint(dresser[0], bed[0], 1.70, 2.00, weight=5)
solver.point_towards(dresser[0], bed[0])

solver.constraints = []
cabinet_A[0].position = [2.9329490661621094, 2.25, 0.8999999761581421]
cabinet_A[0].rotation = [0, 0, -3.1415926050307945]
cabinet_A[0].optimize = 2
cabinet_B[0].position = [0.22499997913837433, 2.25, 0.8999999761581421]
cabinet_B[0].rotation = [0, 0, 4.173038090600672e-08]
cabinet_B[0].optimize = 2
bed[0].position = [1.5499999523162842, 2.25, 0.2750000059604645]
bed[0].rotation = [0, 0, 0.03769911119841034]
bed[0].optimize = 2
desk[0].position = [2.450000047683716, 3.985663890838623, 0.375]
desk[0].rotation = [0, 0, -1.5707962821384405]
desk[0].optimize = 2
dresser[0].position = [0.25, 3.549999952316284, 0.42500001192092896]
dresser[0].rotation = [0, 0, 3.914938422266458e-08]
dresser[0].optimize = 2
chair[0].position = [2.450000047683716, 3.380000114440918, 0.42500001192092896]
chair[0].rotation = [0, 0, 1.586504290712113]
chair[0].optimize = 2
nightstand[0].position = [2.957948684692383, 1.149999976158142, 0.2750000059604645]
nightstand[0].rotation = [0, 0, -3.141592609585582]
nightstand[0].optimize = 2

