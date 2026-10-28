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
    Wall(corner1=[1.04, 3.53, 0.00], corner2=[1.04, 3.75, 0.00]),
    Wall(corner1=[1.04, 3.75, 0.00], corner2=[0.00, 3.75, 0.00]),
    Wall(corner1=[0.00, 3.75, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.42, 0.00, 0.00]),
    Wall(corner1=[3.42, 0.00, 0.00], corner2=[3.42, 3.53, 0.00]),
    Wall(corner1=[3.42, 3.53, 0.00], corner2=[1.04, 3.53, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
potted_plant = Assets(description="A tall potted plant with slender green leaves cascading down from multiple stems. It is planted in a brown pot filled with soil, sitting on a black square base.", size=[0.55, 0.55, 1.45], placements=[AssetInstance() for _ in range(1)])
nightstand_A = Assets(description="A sleek black file cabinet with two drawers, each equipped with silver handles. The cabinet has a modern design with rounded edges and a sturdy base.", size=[0.52, 0.48, 0.62], placements=[AssetInstance() for _ in range(1)])
king_size_bed = Assets(description="A modern bed with a sleek black frame and a tufted headboard. It features a gray mattress and is adorned with black and gray pillows and a black throw blanket.", size=[2.13, 1.93, 1.20], placements=[AssetInstance() for _ in range(1)])
wardrobe = Assets(description="A modern wardrobe with a combination of open shelves and closed storage compartments. It features a sleek design with a dark wood finish and black accents.", size=[0.60, 1.50, 2.10], placements=[AssetInstance() for _ in range(1)])
nightstand_B = Assets(description="A sleek black file cabinet with two drawers, each equipped with silver handles. The cabinet has a modern design with rounded edges and a sturdy base.", size=[0.52, 0.48, 0.62], placements=[AssetInstance() for _ in range(1)])

potted_plant[0].instance_id = 'potted_plant_0'
nightstand_A[0].instance_id = 'nightstand_A_0'
king_size_bed[0].instance_id = 'king_size_bed_0'
wardrobe[0].instance_id = 'wardrobe_0'
nightstand_B[0].instance_id = 'nightstand_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

potted_plant[0].position = [0.2527995222616338, 0.7613046881827679, 0.725]
potted_plant[0].rotation = [0, 0, 0]
nightstand_A[0].position = [0.12354637537166467, 0.07196981458368013, 0.31]
nightstand_A[0].rotation = [0, 0, 0]
king_size_bed[0].position = [1.90009255796152, 2.3659485060002607, 0.6]
king_size_bed[0].rotation = [0, 0, 0]
wardrobe[0].position = [1.998612352285173, 0.08210099604533382, 1.05]
wardrobe[0].rotation = [0, 0, 0]
nightstand_B[0].position = [0.8897880714361073, 0.790476001383874, 0.31]
nightstand_B[0].rotation = [0, 0, 0]
potted_plant[0].position = [0.2527995222616338, 0.7613046881827679, 0.725]
potted_plant[0].rotation = [0, 0, 0]
nightstand_A[0].position = [0.12354637537166467, 0.07196981458368013, 0.31]
nightstand_A[0].rotation = [0, 0, 0]
king_size_bed[0].position = [1.90009255796152, 2.3659485060002607, 0.6]
king_size_bed[0].rotation = [0, 0, 0]
wardrobe[0].position = [1.998612352285173, 0.08210099604533382, 1.05]
wardrobe[0].rotation = [0, 0, 0]
nightstand_B[0].position = [0.8897880714361073, 0.790476001383874, 0.31]
nightstand_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the bed with its headboard against the right wall. It faces toward -x,
# leaving a clear aisle at the foot and keeping the doorway area unobstructed.
king_size_bed[0].position = [2.355, 1.55, 0.60]
king_size_bed[0].rotation = [0, 0, radians(180)]

# Flank the bed with one nightstand on each side. Both are placed against the
# same wall as the headboard, making the bed spatially between them.
nightstand_A[0].position = [3.16, 0.34, 0.31]
nightstand_A[0].rotation = [0, 0, radians(180)]

nightstand_B[0].position = [3.16, 2.76, 0.31]
nightstand_B[0].rotation = [0, 0, radians(180)]

# Put the plant near the left wall, directly in front of the bed, so the bed
# faces it across an open circulation aisle.
potted_plant[0].position = [0.275, 1.55, 0.725]
potted_plant[0].rotation = [0, 0, 0]

# Place the wardrobe along the upper wall, to the right of the doorway.
# Rotating it by 90 degrees keeps its shallow dimension projecting into the
# room and leaves the floor immediately in front of the door clear.
wardrobe[0].position = [1.78, 3.23, 1.05]
wardrobe[0].rotation = [0, 0, radians(90)]


# Fixed reference points retain the intended locations along their respective
# walls while still allowing small feasibility adjustments.
bed_anchor = AssetInstance(position=[2.355, 1.55, 0.60])
nightstand_A_anchor = AssetInstance(position=[3.16, 0.34, 0.31])
nightstand_B_anchor = AssetInstance(position=[3.16, 2.76, 0.31])
plant_anchor = AssetInstance(position=[0.275, 1.55, 0.725])
wardrobe_anchor = AssetInstance(position=[1.78, 3.23, 1.05])

# Primary position constraints: anchor the large pieces to suitable walls.
solver.against_wall(king_size_bed[0], walls[4])
solver.against_wall(nightstand_A[0], walls[4])
solver.against_wall(nightstand_B[0], walls[4])
solver.against_wall(potted_plant[0], walls[2])
solver.against_wall(wardrobe[0], walls[5])

# Keep each object in its intended wall zone. In particular, the wardrobe is
# constrained away from the door, and the plant remains opposite the bed.
solver.distance_constraint(
    king_size_bed[0], bed_anchor, 0.0, 0.08, weight=10
)
solver.distance_constraint(
    nightstand_A[0], nightstand_A_anchor, 0.0, 0.08, weight=10
)
solver.distance_constraint(
    nightstand_B[0], nightstand_B_anchor, 0.0, 0.08, weight=10
)
solver.distance_constraint(
    potted_plant[0], plant_anchor, 0.0, 0.08, weight=10
)
solver.distance_constraint(
    wardrobe[0], wardrobe_anchor, 0.0, 0.08, weight=10
)

# Maintain the bedside grouping. The center distances account for the bed's
# half-width, each nightstand's half-width, and a small usable gap.
solver.distance_constraint(
    nightstand_A[0], king_size_bed[0], 1.18, 1.28, weight=10
)
solver.distance_constraint(
    nightstand_B[0], king_size_bed[0], 1.18, 1.28, weight=10
)

# Preserve a useful aisle between the foot of the bed and the plant.
solver.distance_constraint(
    potted_plant[0], king_size_bed[0], 2.00, 2.18, weight=5
)

# Orientation constraints for every new asset.
solver.point_towards(king_size_bed[0], potted_plant[0])
solver.point_towards(potted_plant[0], king_size_bed[0])
solver.align_with(nightstand_A[0], king_size_bed[0])
solver.align_with(nightstand_B[0], king_size_bed[0])
solver.align_with(wardrobe[0], king_size_bed[0], angle=-90)

solver.constraints = []
wardrobe[0].position = [1.8380146026611328, 3.2318975925445557, 1.0499999523162842]
wardrobe[0].rotation = [0, 0, -1.570796441378695]
wardrobe[0].optimize = 2
king_size_bed[0].position = [2.356099843978882, 1.5499999523162842, 0.6000000238418579]
king_size_bed[0].rotation = [0, 0, -3.1415926099205502]
king_size_bed[0].optimize = 2
nightstand_A[0].position = [3.161099672317505, 0.3400000035762787, 0.3100000023841858]
nightstand_A[0].rotation = [0, 0, -3.1415926098936082]
nightstand_A[0].optimize = 2
potted_plant[0].position = [0.2749999761581421, 1.5499999523162842, 0.7250000238418579]
potted_plant[0].rotation = [0, 0, 4.368959574204555e-08]
potted_plant[0].optimize = 2
nightstand_B[0].position = [3.161099672317505, 2.759999990463257, 0.3100000023841858]
nightstand_B[0].rotation = [0, 0, -3.1415926098936113]
nightstand_B[0].optimize = 2

