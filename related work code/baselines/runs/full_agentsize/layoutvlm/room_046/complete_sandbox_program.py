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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[7.00, 0.00, 0.00]),
    Wall(corner1=[7.00, 0.00, 0.00], corner2=[7.00, 6.19, 0.00]),
    Wall(corner1=[7.00, 6.19, 0.00], corner2=[0.00, 6.19, 0.00]),
    Wall(corner1=[0.00, 6.19, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
seat = Assets(description="A cozy armchair with a plush, orange fabric upholstery and wooden legs. It features a rounded backrest and armrests for comfortable seating.", size=[0.88, 0.85, 0.92], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="A small, round table with a simple design and thin legs.", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
dresser_A = Assets(description="A light-colored wooden chest of drawers with three drawers and decorative handles. It has a classic design with a slightly curved top edge and ornate feet.", size=[0.45, 0.90, 0.85], placements=[AssetInstance() for _ in range(1)])
lamp = Assets(description="A modern floor lamp with a cylindrical shade and a thin stand.", size=[0.35, 0.35, 1.60], placements=[AssetInstance() for _ in range(1)])
dresser_B = Assets(description="A simple white drawer unit with a single drawer and an open shelf below. It has a minimalist design with clean lines and a sleek handle.", size=[0.42, 0.48, 0.62], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="A modern bed with a simple design, featuring a light pink upholstered frame and a gray textured blanket. It includes two white pillows and is supported by small wooden legs.", size=[2.10, 1.55, 1.00], placements=[AssetInstance() for _ in range(1)])

seat[0].instance_id = 'seat_0'
table[0].instance_id = 'table_0'
dresser_A[0].instance_id = 'dresser_A_0'
lamp[0].instance_id = 'lamp_0'
dresser_B[0].instance_id = 'dresser_B_0'
bed[0].instance_id = 'bed_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

seat[0].position = [2.940270883045279, 5.2713189540101295, 0.46]
seat[0].rotation = [0, 0, 0]
table[0].position = [6.347982655267401, 5.353319964024149, 0.275]
table[0].rotation = [0, 0, 0]
dresser_A[0].position = [1.9850839846373352, 3.042447907913345, 0.425]
dresser_A[0].rotation = [0, 0, 0]
lamp[0].position = [2.783484770682038, 5.273245508286833, 0.8]
lamp[0].rotation = [0, 0, 0]
dresser_B[0].position = [2.611313553600629, 5.388602532607022, 0.31]
dresser_B[0].rotation = [0, 0, 0]
bed[0].position = [6.847453677238454, 3.8601274402145602, 0.5]
bed[0].rotation = [0, 0, 0]
seat[0].position = [2.940270883045279, 5.2713189540101295, 0.46]
seat[0].rotation = [0, 0, 0]
table[0].position = [6.347982655267401, 5.353319964024149, 0.275]
table[0].rotation = [0, 0, 0]
dresser_A[0].position = [1.9850839846373352, 3.042447907913345, 0.425]
dresser_A[0].rotation = [0, 0, 0]
lamp[0].position = [2.783484770682038, 5.273245508286833, 0.8]
lamp[0].rotation = [0, 0, 0]
dresser_B[0].position = [2.611313553600629, 5.388602532607022, 0.31]
dresser_B[0].rotation = [0, 0, 0]
bed[0].position = [6.847453677238454, 3.8601274402145602, 0.5]
bed[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the bed against the upper wall, with the two dressers flanking it.
# All z coordinates are half the corresponding asset height because the
# objects stand directly on the floor.
seat[0].position = [0.44, 1.55, 0.46]
seat[0].rotation = [0, 0, radians(0)]

table[0].position = [1.55, 1.55, 0.275]
table[0].rotation = [0, 0, radians(0)]

dresser_A[0].position = [2.10, 5.965, 0.425]
dresser_A[0].rotation = [0, 0, radians(-90)]

lamp[0].position = [0.75, 0.175, 0.80]
lamp[0].rotation = [0, 0, radians(90)]

dresser_B[0].position = [4.80, 5.98, 0.31]
dresser_B[0].rotation = [0, 0, radians(-90)]

bed[0].position = [3.50, 5.14, 0.50]
bed[0].rotation = [0, 0, radians(-90)]


# Fixed reference points preserve the intended arrangement if the solver
# needs to make the scene physically feasible.
seat_anchor = AssetInstance(position=[0.44, 1.55, 0.46])
table_anchor = AssetInstance(position=[1.55, 1.55, 0.275])
dresser_A_anchor = AssetInstance(position=[2.10, 5.965, 0.425])
lamp_anchor = AssetInstance(position=[0.75, 0.175, 0.80])
dresser_B_anchor = AssetInstance(position=[4.80, 5.98, 0.31])
bed_anchor = AssetInstance(position=[3.50, 5.14, 0.50])

roomward_from_top_A = AssetInstance(position=[2.10, 4.50, 0.425])
roomward_from_top_B = AssetInstance(position=[4.80, 4.50, 0.31])
roomward_from_top_bed = AssetInstance(position=[3.50, 3.50, 0.50])


# Important position constraints come first. The bed is centered between
# dresser_A on its left and dresser_B on its right.
solver.distance_constraint(bed[0], bed_anchor, 0, 0, weight=10)
solver.distance_constraint(dresser_A[0], dresser_A_anchor, 0, 0, weight=10)
solver.distance_constraint(dresser_B[0], dresser_B_anchor, 0, 0, weight=10)

solver.against_wall(bed[0], walls[2])
solver.against_wall(dresser_A[0], walls[2])
solver.against_wall(dresser_B[0], walls[2])

# Keep useful gaps between the bed and the dressers while maintaining their
# left-to-right order: dresser_A, bed, dresser_B.
solver.distance_constraint(dresser_A[0], bed[0], 1.35, 1.50, weight=5)
solver.distance_constraint(dresser_B[0], bed[0], 1.25, 1.45, weight=5)

# Orient the bed and both dresser fronts toward the open room.
solver.point_towards(bed[0], roomward_from_top_bed)
solver.point_towards(dresser_A[0], roomward_from_top_A)
solver.point_towards(dresser_B[0], roomward_from_top_B)


# Form a reading/sitting area in the lower-left part of the room. The chair
# rests against the left wall and faces the nearby table.
solver.distance_constraint(seat[0], seat_anchor, 0, 0, weight=10)
solver.against_wall(seat[0], walls[3])
solver.point_towards(seat[0], table[0])

solver.distance_constraint(table[0], table_anchor, 0, 0, weight=10)
solver.distance_constraint(table[0], seat[0], 1.05, 1.20, weight=5)
solver.align_with(table[0], seat[0])


# Put the floor lamp against the bottom wall, close enough to illuminate the
# chair without obstructing the space between the chair and table.
solver.distance_constraint(lamp[0], lamp_anchor, 0, 0, weight=10)
solver.against_wall(lamp[0], walls[0])
solver.distance_constraint(lamp[0], seat[0], 1.30, 1.55, weight=5)
solver.point_towards(lamp[0], seat[0])

solver.constraints = []
seat[0].position = [0.44000014662742615, 1.5499999523162842, 0.46000000834465027]
seat[0].rotation = [0, 0, 1.7331388721631189e-07]
seat[0].optimize = 2
dresser_B[0].position = [4.800000190734863, 5.978081226348877, 0.3100000023841858]
dresser_B[0].rotation = [0, 0, -1.570796100917818]
dresser_B[0].optimize = 2
lamp[0].position = [0.75, 0.1749998778104782, 0.800000011920929]
lamp[0].rotation = [0, 0, 1.5707965693417998]
lamp[0].optimize = 2
table[0].position = [1.5499999523162842, 1.5499999523162842, 0.2750000059604645]
table[0].rotation = [0, 0, 5.929504200182173e-07]
table[0].optimize = 2
bed[0].position = [3.5, 5.138082504272461, 0.5]
bed[0].rotation = [0, 0, -1.5707965189988828]
bed[0].optimize = 2
dresser_A[0].position = [2.1580519676208496, 5.963083744049072, 0.42500001192092896]
dresser_A[0].rotation = [0, 0, -1.570796098796627]
dresser_A[0].optimize = 2

