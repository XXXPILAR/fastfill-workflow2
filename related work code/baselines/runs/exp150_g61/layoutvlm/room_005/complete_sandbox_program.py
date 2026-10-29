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
    Wall(corner1=[0.00, 3.35, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[2.34, 0.00, 0.00]),
    Wall(corner1=[2.34, 0.00, 0.00], corner2=[2.34, 3.35, 0.00]),
    Wall(corner1=[2.34, 3.35, 0.00], corner2=[0.00, 3.35, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
sink = Assets(description="sink", size=[0.48, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
shelf = Assets(description="shelf", size=[0.20, 0.60, 0.04], placements=[AssetInstance() for _ in range(1)])
toilet = Assets(description="toilet", size=[0.70, 0.38, 0.80], placements=[AssetInstance() for _ in range(1)])
shower = Assets(description="shower", size=[0.90, 0.90, 2.10], placements=[AssetInstance() for _ in range(1)])

sink[0].instance_id = 'sink_0'
shelf[0].instance_id = 'shelf_0'
toilet[0].instance_id = 'toilet_0'
shower[0].instance_id = 'shower_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

sink[0].position = [0.5749990353160339, 0.31946222603864477, 0.425]
sink[0].rotation = [0, 0, 0]
shelf[0].position = [1.6063840942709584, 0.051852949187999806, 0.02]
shelf[0].rotation = [0, 0, 0]
toilet[0].position = [0.6545348462147539, 2.1768691446584296, 0.4]
toilet[0].rotation = [0, 0, 0]
shower[0].position = [0.17498622056492263, 2.8291608341368684, 1.05]
shower[0].rotation = [0, 0, 0]
sink[0].position = [0.5749990353160339, 0.31946222603864477, 0.425]
sink[0].rotation = [0, 0, 0]
shelf[0].position = [1.6063840942709584, 0.051852949187999806, 0.02]
shelf[0].rotation = [0, 0, 0]
toilet[0].position = [0.6545348462147539, 2.1768691446584296, 0.4]
toilet[0].rotation = [0, 0, 0]
shower[0].position = [0.17498622056492263, 2.8291608341368684, 1.05]
shower[0].rotation = [0, 0, 0]

solver.constraints = []

# Use the actual boundary coordinates: x = 0..2.34, y = 0..3.35.
# Opposing fixtures leave 1.16 m of clear space between their front edges.
sink[0].position = [0.24, 1.15, 0.425]
sink[0].rotation = [0, 0, 0]

toilet[0].position = [1.99, 1.15, 0.40]
toilet[0].rotation = [0, 0, radians(180)]

# Keep the shower in the far-left corner, away from the toilet and sink.
shower[0].position = [0.45, 2.90, 1.05]
shower[0].rotation = [0, 0, radians(-90)]

# Support the shallow shelf on the rear portion of the sink.
# Its bottom is at the sink's top (z = 0.85), rather than on the floor.
shelf[0].position = [0.10, 1.15, 0.87]
shelf[0].rotation = [0, 0, 0]

# Prioritize the required facing relationship.
solver.point_towards(toilet[0], sink[0])
solver.point_towards(sink[0], toilet[0])

# Preserve the selected fixture locations and the clear circulation space.
solver.distance_constraint(
    sink[0], AssetInstance(position=[0.24, 1.15, 0.425]),
    0, 0, weight=10
)
solver.against_wall(sink[0], walls[0])

solver.distance_constraint(
    toilet[0], AssetInstance(position=[1.99, 1.15, 0.40]),
    0, 0, weight=10
)
solver.against_wall(toilet[0], walls[2])

# The shower touches both corner walls and opens toward the room.
solver.distance_constraint(
    shower[0], AssetInstance(position=[0.45, 2.90, 1.05]),
    0, 0, weight=10
)
solver.against_wall(shower[0], walls[0])
solver.against_wall(shower[0], walls[3])
solver.align_with(
    shower[0],
    AssetInstance(rotation=[0, 0, radians(-90)])
)

# Retain the shelf's rear-edge location and its support relationship.
solver.on_top_of(shelf[0], sink[0])
solver.distance_constraint(
    shelf[0], AssetInstance(position=[0.10, 1.15, 0.87]),
    0, 0, weight=10
)
solver.align_with(shelf[0], sink[0])

solver.constraints = []
sink[0].position = [0.23999997973442078, 1.149999976158142, 0.42500001192092896]
sink[0].rotation = [0, 0, 3.93265930653101e-08]
sink[0].optimize = 2
shower[0].position = [0.45000094175338745, 2.7008395195007324, 1.0499999523162842]
shower[0].rotation = [0, 0, 1.332089629806549e-06]
shower[0].optimize = 2
shelf[0].position = [0.10000000149011612, 1.149999976158142, 0.8700000047683716]
shelf[0].rotation = [0, 0, 3.4523439063230614e-08]
shelf[0].optimize = 2
toilet[0].position = [1.9931902885437012, 1.149999976158142, 0.4000000059604645]
toilet[0].rotation = [0, 0, -3.141592611813459]
toilet[0].optimize = 2

