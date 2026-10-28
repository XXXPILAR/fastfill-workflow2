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
    Wall(corner1=[1.11, 4.02, 0.00], corner2=[1.11, 5.78, 0.00]),
    Wall(corner1=[1.11, 5.78, 0.00], corner2=[0.00, 5.78, 0.00]),
    Wall(corner1=[0.00, 5.78, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.13, 0.00, 0.00]),
    Wall(corner1=[3.13, 0.00, 0.00], corner2=[3.13, 4.02, 0.00]),
    Wall(corner1=[3.13, 4.02, 0.00], corner2=[1.11, 4.02, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
nightstand = Assets(description="nightstand", size=[0.40, 0.45, 0.55], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.00, 1.60, 0.90], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="wardrobe", size=[0.60, 1.20, 2.10], placements=[AssetInstance() for _ in range(1)])

nightstand[0].instance_id = 'nightstand_0'
bed[0].instance_id = 'bed_0'
wardrobe[0].instance_id = 'wardrobe_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

nightstand[0].position = [0.7601371846041712, 0.003449015179313761, 0.275]
nightstand[0].rotation = [0, 0, 0]
bed[0].position = [1.8211042840726295, 2.753590972846559, 0.45]
bed[0].rotation = [0, 0, 0]
wardrobe[0].position = [2.9910465613775545, 3.687129424089147, 1.05]
wardrobe[0].rotation = [0, 0, 0]
nightstand[0].position = [0.7601371846041712, 0.003449015179313761, 0.275]
nightstand[0].rotation = [0, 0, 0]
bed[0].position = [1.8211042840726295, 2.753590972846559, 0.45]
bed[0].rotation = [0, 0, 0]
wardrobe[0].position = [2.9910465613775545, 3.687129424089147, 1.05]
wardrobe[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the bed against the long left wall, facing into the room. Its footprint
# occupies x=[0.00, 2.00], y=[0.70, 2.30], leaving the central aisle open.
bed[0].position = [1.00, 1.50, 0.45]
bed[0].rotation = [0, 0, radians(0)]

# Place the nightstand beside the bed's upper side and against the same wall.
# The 0.05 m edge-to-edge gap satisfies the requested maximum 0.10 m spacing.
nightstand[0].position = [0.20, 2.575, 0.275]
nightstand[0].rotation = [0, 0, radians(0)]

# Place the wardrobe against the right wall, below the recessed upper area.
# This keeps both door approaches and the circulation route through the room clear.
wardrobe[0].position = [2.83, 3.25, 1.05]
wardrobe[0].rotation = [0, 0, radians(180)]

# Fixed reference points preserve the selected along-wall locations and prevent
# the solver from moving furniture into either doorway.
bed_anchor = AssetInstance(position=[1.00, 1.50, 0.45])
nightstand_anchor = AssetInstance(position=[0.20, 2.575, 0.275])
wardrobe_anchor = AssetInstance(position=[2.83, 3.25, 1.05])

solver.distance_constraint(bed[0], bed_anchor, 0.0, 0.0, weight=10)
solver.against_wall(bed[0], walls[2])

solver.distance_constraint(nightstand[0], nightstand_anchor, 0.0, 0.0, weight=10)
solver.against_wall(nightstand[0], walls[2])

solver.distance_constraint(wardrobe[0], wardrobe_anchor, 0.0, 0.0, weight=10)
solver.against_wall(wardrobe[0], walls[4])

# The API measures center-to-center distance. At 1.34 m, the differently sized
# bed and nightstand have an edge-to-edge separation of approximately 0.05 m.
solver.distance_constraint(nightstand[0], bed[0], 1.30, 1.39, weight=10)
solver.distance_constraint(bed[0], nightstand[0], 1.30, 1.39, weight=10)

# Orient the bed and nightstand toward the room interior and the wardrobe away
# from the right wall so its accessible front faces into the room.
solver.point_towards(
    bed[0],
    AssetInstance(position=[2.00, 1.50, 0.45])
)
solver.point_towards(
    nightstand[0],
    AssetInstance(position=[1.20, 2.575, 0.275])
)
solver.point_towards(
    wardrobe[0],
    AssetInstance(position=[1.80, 3.25, 1.05])
)

solver.constraints = []
bed[0].position = [1.1029465198516846, 1.5, 0.44999998807907104]
bed[0].rotation = [0, 0, -3.1414176589969824]
bed[0].optimize = 2
wardrobe[0].position = [2.8325812816619873, 3.25, 1.0499999523162842]
wardrobe[0].rotation = [0, 0, -3.1415926083381382]
wardrobe[0].optimize = 2
nightstand[0].position = [0.20000001788139343, 2.575000047683716, 0.2750000059604645]
nightstand[0].rotation = [0, 0, 4.3474963140278994e-08]
nightstand[0].optimize = 2

