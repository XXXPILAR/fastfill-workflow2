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
    Wall(corner1=[4.76, 0.00, 0.00], corner2=[4.76, 4.26, 0.00]),
    Wall(corner1=[4.76, 4.26, 0.00], corner2=[0.00, 4.26, 0.00]),
    Wall(corner1=[0.00, 4.26, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.76, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
chair_A = Assets(description="chair", size=[0.53, 0.48, 0.86], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.53, 0.48, 0.86], placements=[AssetInstance() for _ in range(1)])
cabinet_A = Assets(description="cabinet", size=[0.42, 1.20, 0.85], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.40, 0.90, 0.82], placements=[AssetInstance() for _ in range(1)])
vase_A = Assets(description="vase", size=[0.18, 0.18, 0.32], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="lamp", size=[0.30, 0.30, 0.55], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.28, 0.28, 0.50], placements=[AssetInstance() for _ in range(1)])
shelf_A = Assets(description="shelf", size=[0.24, 1.10, 0.06], placements=[AssetInstance() for _ in range(1)])
cup_A = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
cabinet_C = Assets(description="cabinet", size=[0.38, 0.75, 1.65], placements=[AssetInstance() for _ in range(1)])
vase_B = Assets(description="vase", size=[0.16, 0.16, 0.28], placements=[AssetInstance() for _ in range(1)])
shelf_B = Assets(description="shelf", size=[0.22, 0.90, 0.05], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="chair", size=[0.53, 0.48, 0.86], placements=[AssetInstance() for _ in range(1)])
pot = Assets(description="pot", size=[0.24, 0.24, 0.16], placements=[AssetInstance() for _ in range(1)])
knife = Assets(description="knife", size=[0.03, 0.32, 0.02], placements=[AssetInstance() for _ in range(1)])
chair_D = Assets(description="chair", size=[0.53, 0.48, 0.86], placements=[AssetInstance() for _ in range(1)])
table = Assets(description="table", size=[0.95, 1.80, 0.76], placements=[AssetInstance() for _ in range(1)])
cabinet_D = Assets(description="cabinet", size=[0.42, 1.10, 0.88], placements=[AssetInstance() for _ in range(1)])
cup_B = Assets(description="cup", size=[0.09, 0.09, 0.11], placements=[AssetInstance() for _ in range(1)])
cabinet_E = Assets(description="cabinet", size=[0.40, 0.85, 1.80], placements=[AssetInstance() for _ in range(1)])

chair_A[0].instance_id = 'chair_A_0'
chair_B[0].instance_id = 'chair_B_0'
cabinet_A[0].instance_id = 'cabinet_A_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
vase_A[0].instance_id = 'vase_A_0'
lamp_A[0].instance_id = 'lamp_A_0'
lamp_B[0].instance_id = 'lamp_B_0'
shelf_A[0].instance_id = 'shelf_A_0'
cup_A[0].instance_id = 'cup_A_0'
cabinet_C[0].instance_id = 'cabinet_C_0'
vase_B[0].instance_id = 'vase_B_0'
shelf_B[0].instance_id = 'shelf_B_0'
chair_C[0].instance_id = 'chair_C_0'
pot[0].instance_id = 'pot_0'
knife[0].instance_id = 'knife_0'
chair_D[0].instance_id = 'chair_D_0'
table[0].instance_id = 'table_0'
cabinet_D[0].instance_id = 'cabinet_D_0'
cup_B[0].instance_id = 'cup_B_0'
cabinet_E[0].instance_id = 'cabinet_E_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

chair_A[0].position = [0.08588801375377497, 1.4051708329601176, 0.43]
chair_A[0].rotation = [0, 0, 0]
chair_B[0].position = [3.8481839429183897, 3.7764198520215797, 0.43]
chair_B[0].rotation = [0, 0, 0]
cabinet_A[0].position = [2.581585691202095, 0.8539741839140387, 0.425]
cabinet_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [2.38524298196322, 0.918738197661116, 0.41]
cabinet_B[0].rotation = [0, 0, 0]
vase_A[0].position = [3.0595611049383407, 0.8669538683585996, 0.16]
vase_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [1.454480643450287, 2.530632975328791, 0.275]
lamp_A[0].rotation = [0, 0, 0]
lamp_B[0].position = [2.910251128702066, 0.5637434176697218, 0.25]
lamp_B[0].rotation = [0, 0, 0]
shelf_A[0].position = [0.07591580631652907, 3.1586116137088793, 0.03]
shelf_A[0].rotation = [0, 0, 0]
cup_A[0].position = [1.9576790047119976, 0.997928907064882, 0.055]
cup_A[0].rotation = [0, 0, 0]
cabinet_C[0].position = [1.8335294097037478, 0.7998274875367318, 0.825]
cabinet_C[0].rotation = [0, 0, 0]
vase_B[0].position = [0.4104503293560503, 2.935384869357354, 0.14]
vase_B[0].rotation = [0, 0, 0]
shelf_B[0].position = [0.5943780281012582, 0.5155654070256308, 0.025]
shelf_B[0].rotation = [0, 0, 0]
chair_C[0].position = [4.738713042191886, 3.181446196581782, 0.43]
chair_C[0].rotation = [0, 0, 0]
pot[0].position = [2.9078238252387787, 2.8166031773208084, 0.08]
pot[0].rotation = [0, 0, 0]
knife[0].position = [2.899750557741418, 1.751667314703686, 0.01]
knife[0].rotation = [0, 0, 0]
chair_D[0].position = [2.859492536140577, 0.9731422908590793, 0.43]
chair_D[0].rotation = [0, 0, 0]
table[0].position = [0.6473548867098562, 1.196251008509258, 0.38]
table[0].rotation = [0, 0, 0]
cabinet_D[0].position = [3.4254821649130163, 3.080297916416455, 0.44]
cabinet_D[0].rotation = [0, 0, 0]
cup_B[0].position = [1.574535995084905, 1.9634303065711345, 0.055]
cup_B[0].rotation = [0, 0, 0]
cabinet_E[0].position = [1.6654739075682088, 0.5504647380287538, 0.9]
cabinet_E[0].rotation = [0, 0, 0]
chair_A[0].position = [0.08588801375377497, 1.4051708329601176, 0.43]
chair_A[0].rotation = [0, 0, 0]
chair_B[0].position = [3.8481839429183897, 3.7764198520215797, 0.43]
chair_B[0].rotation = [0, 0, 0]
cabinet_A[0].position = [2.581585691202095, 0.8539741839140387, 0.425]
cabinet_A[0].rotation = [0, 0, 0]
cabinet_B[0].position = [2.38524298196322, 0.918738197661116, 0.41]
cabinet_B[0].rotation = [0, 0, 0]
vase_A[0].position = [3.0595611049383407, 0.8669538683585996, 0.16]
vase_A[0].rotation = [0, 0, 0]
lamp_A[0].position = [1.454480643450287, 2.530632975328791, 0.275]
lamp_A[0].rotation = [0, 0, 0]
lamp_B[0].position = [2.910251128702066, 0.5637434176697218, 0.25]
lamp_B[0].rotation = [0, 0, 0]
shelf_A[0].position = [0.07591580631652907, 3.1586116137088793, 0.03]
shelf_A[0].rotation = [0, 0, 0]
cup_A[0].position = [1.9576790047119976, 0.997928907064882, 0.055]
cup_A[0].rotation = [0, 0, 0]
cabinet_C[0].position = [1.8335294097037478, 0.7998274875367318, 0.825]
cabinet_C[0].rotation = [0, 0, 0]
vase_B[0].position = [0.4104503293560503, 2.935384869357354, 0.14]
vase_B[0].rotation = [0, 0, 0]
shelf_B[0].position = [0.5943780281012582, 0.5155654070256308, 0.025]
shelf_B[0].rotation = [0, 0, 0]
chair_C[0].position = [4.738713042191886, 3.181446196581782, 0.43]
chair_C[0].rotation = [0, 0, 0]
pot[0].position = [2.9078238252387787, 2.8166031773208084, 0.08]
pot[0].rotation = [0, 0, 0]
knife[0].position = [2.899750557741418, 1.751667314703686, 0.01]
knife[0].rotation = [0, 0, 0]
chair_D[0].position = [2.859492536140577, 0.9731422908590793, 0.43]
chair_D[0].rotation = [0, 0, 0]
table[0].position = [0.6473548867098562, 1.196251008509258, 0.38]
table[0].rotation = [0, 0, 0]
cabinet_D[0].position = [3.4254821649130163, 3.080297916416455, 0.44]
cabinet_D[0].rotation = [0, 0, 0]
cup_B[0].position = [1.574535995084905, 1.9634303065711345, 0.055]
cup_B[0].rotation = [0, 0, 0]
cabinet_E[0].position = [1.6654739075682088, 0.5504647380287538, 0.9]
cabinet_E[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the dining group near the room center. The table lies between
# chair_A (o0000) and chair_B (o0001), while the entrance corridor in
# front of the door at x=2.03 remains unobstructed.
table[0].position = [2.65, 2.15, 0.38]
table[0].rotation = [0, 0, 0]

chair_A[0].position = [1.65, 2.15, 0.43]
chair_A[0].rotation = [0, 0, 0]                 # Faces +x toward the table.

chair_B[0].position = [3.65, 2.15, 0.43]
chair_B[0].rotation = [0, 0, radians(180)]      # Faces left toward shelf_A.

chair_C[0].position = [2.65, 3.55, 0.43]
chair_C[0].rotation = [0, 0, radians(270)]      # Faces -y toward the table.

chair_D[0].position = [2.65, 0.72, 0.43]
chair_D[0].rotation = [0, 0, radians(90)]       # Faces +y toward the table.

# Put storage along the side walls so that it does not cover the window
# on the north wall or occupy the doorway clearance.
cabinet_A[0].position = [0.21, 0.65, 0.425]
cabinet_A[0].rotation = [0, 0, 0]

cabinet_D[0].position = [0.21, 2.15, 0.44]
cabinet_D[0].rotation = [0, 0, 0]

cabinet_E[0].position = [0.20, 3.55, 0.90]
cabinet_E[0].rotation = [0, 0, 0]

cabinet_B[0].position = [4.56, 0.65, 0.41]
cabinet_B[0].rotation = [0, 0, radians(180)]

cabinet_C[0].position = [4.57, 2.75, 0.825]
cabinet_C[0].rotation = [0, 0, radians(180)]

# The thin shelves rest horizontally on low cabinets. shelf_A is on the
# left side of the room, directly in chair_B's viewing direction.
shelf_A[0].position = [0.21, 2.15, 0.91]
shelf_A[0].rotation = [0, 0, 0]

shelf_B[0].position = [4.56, 0.65, 0.845]
shelf_B[0].rotation = [0, 0, radians(180)]

# Place decorative objects on stable storage surfaces.
vase_A[0].position = [0.21, 0.65, 1.01]
vase_A[0].rotation = [0, 0, 0]

vase_B[0].position = [0.20, 3.55, 1.94]
vase_B[0].rotation = [0, 0, 0]

lamp_A[0].position = [0.21, 2.15, 1.215]
lamp_A[0].rotation = [0, 0, 0]

lamp_B[0].position = [4.56, 0.65, 1.12]
lamp_B[0].rotation = [0, 0, radians(180)]

# Distribute the dining and kitchen objects across the tabletop with
# enough horizontal separation to prevent overlap.
cup_A[0].position = [2.42, 1.70, 0.815]
cup_A[0].rotation = [0, 0, 0]

cup_B[0].position = [2.84, 2.65, 0.815]
cup_B[0].rotation = [0, 0, 0]

pot[0].position = [2.55, 2.18, 0.84]
pot[0].rotation = [0, 0, 0]

knife[0].position = [2.88, 2.12, 0.77]
knife[0].rotation = [0, 0, radians(10)]


# Fixed anchors strongly preserve the planned, collision-free layout while
# still allowing the semantic constraints below to participate in adjustment.
layout_anchors = {
    "table": AssetInstance(position=[2.65, 2.15, 0.38]),
    "chair_A": AssetInstance(position=[1.65, 2.15, 0.43]),
    "chair_B": AssetInstance(position=[3.65, 2.15, 0.43]),
    "chair_C": AssetInstance(position=[2.65, 3.55, 0.43]),
    "chair_D": AssetInstance(position=[2.65, 0.72, 0.43]),
    "cabinet_A": AssetInstance(position=[0.21, 0.65, 0.425]),
    "cabinet_B": AssetInstance(position=[4.56, 0.65, 0.41]),
    "cabinet_C": AssetInstance(position=[4.57, 2.75, 0.825]),
    "cabinet_D": AssetInstance(position=[0.21, 2.15, 0.44]),
    "cabinet_E": AssetInstance(position=[0.20, 3.55, 0.90]),
    "shelf_A": AssetInstance(position=[0.21, 2.15, 0.91]),
    "shelf_B": AssetInstance(position=[4.56, 0.65, 0.845]),
    "vase_A": AssetInstance(position=[0.21, 0.65, 1.01]),
    "vase_B": AssetInstance(position=[0.20, 3.55, 1.94]),
    "lamp_A": AssetInstance(position=[0.21, 2.15, 1.215]),
    "lamp_B": AssetInstance(position=[4.56, 0.65, 1.12]),
    "cup_A": AssetInstance(position=[2.42, 1.70, 0.815]),
    "cup_B": AssetInstance(position=[2.84, 2.65, 0.815]),
    "pot": AssetInstance(position=[2.55, 2.18, 0.84]),
    "knife": AssetInstance(position=[2.88, 2.12, 0.77]),
}

# High-priority position constraints establish the intended clearances.
solver.distance_constraint(table[0], layout_anchors["table"], 0, 0, weight=10)
solver.distance_constraint(chair_A[0], layout_anchors["chair_A"], 0, 0, weight=10)
solver.distance_constraint(chair_B[0], layout_anchors["chair_B"], 0, 0, weight=10)
solver.distance_constraint(chair_C[0], layout_anchors["chair_C"], 0, 0, weight=10)
solver.distance_constraint(chair_D[0], layout_anchors["chair_D"], 0, 0, weight=10)

solver.distance_constraint(cabinet_A[0], layout_anchors["cabinet_A"], 0, 0, weight=10)
solver.distance_constraint(cabinet_B[0], layout_anchors["cabinet_B"], 0, 0, weight=10)
solver.distance_constraint(cabinet_C[0], layout_anchors["cabinet_C"], 0, 0, weight=10)
solver.distance_constraint(cabinet_D[0], layout_anchors["cabinet_D"], 0, 0, weight=10)
solver.distance_constraint(cabinet_E[0], layout_anchors["cabinet_E"], 0, 0, weight=10)

solver.distance_constraint(shelf_A[0], layout_anchors["shelf_A"], 0, 0, weight=10)
solver.distance_constraint(shelf_B[0], layout_anchors["shelf_B"], 0, 0, weight=10)
solver.distance_constraint(vase_A[0], layout_anchors["vase_A"], 0, 0, weight=10)
solver.distance_constraint(vase_B[0], layout_anchors["vase_B"], 0, 0, weight=10)
solver.distance_constraint(lamp_A[0], layout_anchors["lamp_A"], 0, 0, weight=10)
solver.distance_constraint(lamp_B[0], layout_anchors["lamp_B"], 0, 0, weight=10)
solver.distance_constraint(cup_A[0], layout_anchors["cup_A"], 0, 0, weight=10)
solver.distance_constraint(cup_B[0], layout_anchors["cup_B"], 0, 0, weight=10)
solver.distance_constraint(pot[0], layout_anchors["pot"], 0, 0, weight=10)
solver.distance_constraint(knife[0], layout_anchors["knife"], 0, 0, weight=10)

# Keep the cabinets against their assigned side walls.
solver.against_wall(cabinet_A[0], walls[2])
solver.against_wall(cabinet_D[0], walls[2])
solver.against_wall(cabinet_E[0], walls[2])
solver.against_wall(cabinet_B[0], walls[0])
solver.against_wall(cabinet_C[0], walls[0])

# Maintain the dining-table relationship. The equal one-meter spacing
# puts the table between chair_A and chair_B.
solver.distance_constraint(chair_A[0], table[0], 1.0, 1.0, weight=10)
solver.distance_constraint(chair_B[0], table[0], 1.0, 1.0, weight=10)
solver.distance_constraint(chair_C[0], table[0], 1.35, 1.45, weight=5)
solver.distance_constraint(chair_D[0], table[0], 1.38, 1.48, weight=5)

# Orientation constraints for all floor-standing assets.
solver.point_towards(chair_A[0], table[0])
solver.point_towards(chair_B[0], shelf_A[0])  # Required: chair o0001 faces shelf o0007.
solver.point_towards(chair_C[0], table[0])
solver.point_towards(chair_D[0], table[0])
solver.align_with(table[0], layout_anchors["table"])

solver.point_towards(cabinet_A[0], table[0])
solver.point_towards(cabinet_D[0], table[0])
solver.point_towards(cabinet_E[0], table[0])
solver.point_towards(cabinet_B[0], table[0])
solver.point_towards(cabinet_C[0], table[0])

# Vertical support constraints for every elevated object.
solver.on_top_of(shelf_A[0], cabinet_D[0])
solver.on_top_of(shelf_B[0], cabinet_B[0])
solver.on_top_of(vase_A[0], cabinet_A[0])
solver.on_top_of(vase_B[0], cabinet_E[0])
solver.on_top_of(lamp_A[0], shelf_A[0])
solver.on_top_of(lamp_B[0], shelf_B[0])
solver.on_top_of(cup_A[0], table[0])
solver.on_top_of(cup_B[0], table[0])
solver.on_top_of(pot[0], table[0])
solver.on_top_of(knife[0], table[0])

# Orientation constraints for shelves and all small elevated assets.
solver.align_with(shelf_A[0], cabinet_D[0])
solver.align_with(shelf_B[0], cabinet_B[0])
solver.align_with(vase_A[0], cabinet_A[0])
solver.align_with(vase_B[0], cabinet_E[0])
solver.align_with(lamp_A[0], shelf_A[0])
solver.align_with(lamp_B[0], shelf_B[0])
solver.align_with(cup_A[0], table[0])
solver.align_with(cup_B[0], table[0])
solver.align_with(pot[0], table[0])
solver.align_with(knife[0], table[0], angle=10)

solver.constraints = []
cup_A[0].position = [2.4200000762939453, 1.7000000476837158, 0.8149999976158142]
cup_A[0].rotation = [0, 0, 0.0722570926506558]
cup_A[0].optimize = 2
vase_B[0].position = [0.20000000298023224, 3.549999952316284, 1.9399999380111694]
vase_B[0].rotation = [0, 0, -2.582351351744499e-07]
vase_B[0].optimize = 2
cabinet_E[0].position = [0.19999998807907104, 3.549999952316284, 0.8999999761581421]
cabinet_E[0].rotation = [0, 0, -5.432845255986061e-08]
cabinet_E[0].optimize = 2
table[0].position = [2.6500000953674316, 2.1500000953674316, 0.3799999952316284]
table[0].rotation = [0, 0, 0.0722566305613884]
table[0].optimize = 2
lamp_A[0].position = [0.20999999344348907, 2.1500000953674316, 1.2149999141693115]
lamp_A[0].rotation = [0, 0, -1.3698132598260646e-07]
lamp_A[0].optimize = 2
lamp_B[0].position = [4.559999942779541, 0.6499999761581421, 1.119999885559082]
lamp_B[0].rotation = [0, 0, 3.1415920755593754]
lamp_B[0].optimize = 2
vase_A[0].position = [0.20999999344348907, 0.6499999761581421, 1.0099999904632568]
vase_A[0].rotation = [0, 0, -2.6335601695660364e-07]
vase_A[0].optimize = 2
cabinet_B[0].position = [4.563382148742676, 0.6499999761581421, 0.4099999964237213]
cabinet_B[0].rotation = [0, 0, 3.141592566022104]
cabinet_B[0].optimize = 2
chair_D[0].position = [2.6500000953674316, 0.7200000286102295, 0.4300000071525574]
chair_D[0].rotation = [0, 0, 1.5833626980517244]
chair_D[0].optimize = 2
chair_C[0].position = [2.6500000953674316, 3.549999952316284, 0.4300000071525574]
chair_C[0].rotation = [0, 0, -1.5582299555380688]
chair_C[0].optimize = 2
pot[0].position = [2.549999952316284, 2.180000066757202, 0.8399999737739563]
pot[0].rotation = [0, 0, 0.0722570926506558]
pot[0].optimize = 2
cabinet_D[0].position = [0.2099999189376831, 2.1500000953674316, 0.4399999976158142]
cabinet_D[0].rotation = [0, 0, -5.368687074596516e-08]
cabinet_D[0].optimize = 2
shelf_A[0].position = [0.20999999344348907, 2.1500000953674316, 0.9099999666213989]
shelf_A[0].rotation = [0, 0, -1.938457787571488e-07]
shelf_A[0].optimize = 2
chair_A[0].position = [1.649999976158142, 2.1500000953674316, 0.4300000071525574]
chair_A[0].rotation = [0, 0, 0.01256637125682779]
chair_A[0].optimize = 2
cup_B[0].position = [2.8399999141693115, 2.6500000953674316, 0.8149999976158142]
cup_B[0].rotation = [0, 0, 0.0722570926506558]
cup_B[0].optimize = 2
cabinet_A[0].position = [0.2099999487400055, 0.6499999761581421, 0.42500001192092896]
cabinet_A[0].rotation = [0, 0, -5.6052416911685984e-08]
cabinet_A[0].optimize = 2
chair_B[0].position = [3.6500000953674316, 2.1500000953674316, 0.4300000071525574]
chair_B[0].rotation = [0, 0, -3.1290262823329655]
chair_B[0].optimize = 2
knife[0].position = [2.880000114440918, 2.119999885559082, 0.7699999809265137]
knife[0].rotation = [0, 0, 0.24678973269589136]
knife[0].optimize = 2
cabinet_C[0].position = [4.573380947113037, 2.75, 0.824999988079071]
cabinet_C[0].rotation = [0, 0, -3.1415925212472]
cabinet_C[0].optimize = 2
shelf_B[0].position = [4.559999942779541, 0.6499999761581421, 0.8449999690055847]
shelf_B[0].rotation = [0, 0, -3.141592450129086]
shelf_B[0].optimize = 2

