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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[9.67, 0.00, 0.00]),
    Wall(corner1=[9.67, 0.00, 0.00], corner2=[9.67, 3.75, 0.00]),
    Wall(corner1=[9.67, 3.75, 0.00], corner2=[0.00, 3.75, 0.00]),
    Wall(corner1=[0.00, 3.75, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
chair_A = Assets(description="chair", size=[0.58, 0.55, 0.82], placements=[AssetInstance() for _ in range(1)])
mirror = Assets(description="mirror", size=[0.04, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
pillow = Assets(description="pillow", size=[0.14, 0.42, 0.42], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.58, 0.55, 0.82], placements=[AssetInstance() for _ in range(1)])
lamp = Assets(description="lamp", size=[0.32, 0.32, 0.58], placements=[AssetInstance() for _ in range(1)])
table_A = Assets(description="table", size=[0.55, 0.55, 0.55], placements=[AssetInstance() for _ in range(1)])
table_B = Assets(description="table", size=[0.60, 1.20, 0.45], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="chair", size=[0.78, 0.72, 0.86], placements=[AssetInstance() for _ in range(1)])
chair_D = Assets(description="chair", size=[0.78, 0.72, 0.86], placements=[AssetInstance() for _ in range(1)])

chair_A[0].instance_id = 'chair_A_0'
mirror[0].instance_id = 'mirror_0'
pillow[0].instance_id = 'pillow_0'
chair_B[0].instance_id = 'chair_B_0'
lamp[0].instance_id = 'lamp_0'
table_A[0].instance_id = 'table_A_0'
table_B[0].instance_id = 'table_B_0'
chair_C[0].instance_id = 'chair_C_0'
chair_D[0].instance_id = 'chair_D_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

chair_A[0].position = [8.899896448118252, 2.270977959625681, 0.41]
chair_A[0].rotation = [0, 0, 0]
mirror[0].position = [1.3992617553336906, 0.5514476993869806, 0.45]
mirror[0].rotation = [0, 0, 0]
pillow[0].position = [2.5354846995421836, 0.7187319254566195, 0.21]
pillow[0].rotation = [0, 0, 0]
chair_B[0].position = [9.237446704422378, 2.4856082806405793, 0.41]
chair_B[0].rotation = [0, 0, 0]
lamp[0].position = [5.565970211079128, 0.2807854134074085, 0.29]
lamp[0].rotation = [0, 0, 0]
table_A[0].position = [3.734645014582903, 2.1377661430218535, 0.275]
table_A[0].rotation = [0, 0, 0]
table_B[0].position = [0.8901342262116334, 1.829085371600477, 0.225]
table_B[0].rotation = [0, 0, 0]
chair_C[0].position = [3.7826966400847732, 2.0013416456694597, 0.43]
chair_C[0].rotation = [0, 0, 0]
chair_D[0].position = [2.1360172546598433, 1.2115099519381982, 0.43]
chair_D[0].rotation = [0, 0, 0]
chair_A[0].position = [8.899896448118252, 2.270977959625681, 0.41]
chair_A[0].rotation = [0, 0, 0]
mirror[0].position = [1.3992617553336906, 0.5514476993869806, 0.45]
mirror[0].rotation = [0, 0, 0]
pillow[0].position = [2.5354846995421836, 0.7187319254566195, 0.21]
pillow[0].rotation = [0, 0, 0]
chair_B[0].position = [9.237446704422378, 2.4856082806405793, 0.41]
chair_B[0].rotation = [0, 0, 0]
lamp[0].position = [5.565970211079128, 0.2807854134074085, 0.29]
lamp[0].rotation = [0, 0, 0]
table_A[0].position = [3.734645014582903, 2.1377661430218535, 0.275]
table_A[0].rotation = [0, 0, 0]
table_B[0].position = [0.8901342262116334, 1.829085371600477, 0.225]
table_B[0].rotation = [0, 0, 0]
chair_C[0].position = [3.7826966400847732, 2.0013416456694597, 0.43]
chair_C[0].rotation = [0, 0, 0]
chair_D[0].position = [2.1360172546598433, 1.2115099519381982, 0.43]
chair_D[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the three related chairs along the lower side of the seating area.
# chair_A (o0000) is centered between chair_D (o0008) and chair_B (o0003).
chair_D[0].position = [3.40, 0.95, 0.43]
chair_D[0].rotation = [0, 0, radians(90)]

chair_A[0].position = [4.50, 0.95, 0.41]
chair_A[0].rotation = [0, 0, radians(90)]

chair_B[0].position = [5.60, 0.95, 0.41]
chair_B[0].rotation = [0, 0, radians(90)]

# The large table serves the chair grouping while remaining clear of the
# bottom-wall window and the door on the right.
table_B[0].position = [4.50, 2.10, 0.225]
table_B[0].rotation = [0, 0, 0]

# chair_C (o0007) is on the far side of the grouping and faces chair_D.
chair_C[0].position = [3.40, 3.25, 0.43]
chair_C[0].rotation = [0, 0, radians(-90)]

# Put the pillow on chair_D. Its x-y center coincides with the chair so it
# remains immediately adjacent to the chair in plan.
pillow[0].position = [3.40, 0.95, 1.07]
pillow[0].rotation = [0, 0, radians(90)]

# Create a separate side-table-and-lamp grouping in the upper-left area,
# set away from the two windows on the left wall.
table_A[0].position = [1.40, 2.55, 0.275]
table_A[0].rotation = [0, 0, 0]

lamp[0].position = [1.40, 2.55, 0.84]
lamp[0].rotation = [0, 0, 0]

# The mirror uses the solid portion of the upper wall, avoiding all windows.
# At -90 degrees its thin dimension is normal to that wall.
mirror[0].position = [1.40, 3.73, 0.45]
mirror[0].rotation = [0, 0, radians(-90)]

# Fixed points preserve the intended clearances and the exact "between"
# arrangement while allowing the semantic constraints below to be retained.
chair_D_anchor = AssetInstance(
    position=[3.40, 0.95, 0.43],
    rotation=[0, 0, radians(90)]
)
chair_A_anchor = AssetInstance(
    position=[4.50, 0.95, 0.41],
    rotation=[0, 0, radians(90)]
)
chair_B_anchor = AssetInstance(
    position=[5.60, 0.95, 0.41],
    rotation=[0, 0, radians(90)]
)
chair_C_anchor = AssetInstance(
    position=[3.40, 3.25, 0.43],
    rotation=[0, 0, radians(-90)]
)
table_B_anchor = AssetInstance(
    position=[4.50, 2.10, 0.225],
    rotation=[0, 0, 0]
)
table_A_anchor = AssetInstance(
    position=[1.40, 2.55, 0.275],
    rotation=[0, 0, 0]
)
lamp_anchor = AssetInstance(
    position=[1.40, 2.55, 0.84],
    rotation=[0, 0, 0]
)
mirror_anchor = AssetInstance(
    position=[1.40, 3.73, 0.45],
    rotation=[0, 0, radians(-90)]
)
pillow_anchor = AssetInstance(
    position=[3.40, 0.95, 1.07],
    rotation=[0, 0, radians(90)]
)
room_center = AssetInstance(position=[4.835, 1.875, 0.45])

# High-priority semantic relationships.
# This expresses the requested 0.10 m chair/pillow proximity; on_top_of below
# supplies the necessary vertical relationship for the pillow.
solver.distance_constraint(pillow[0], chair_D[0], 0.0, 0.10, weight=10)
solver.point_towards(chair_C[0], chair_D[0])

# Equal spacing plus the collinear initial coordinates keeps chair_A between
# chair_D and chair_B.
solver.distance_constraint(chair_A[0], chair_D[0], 1.10, 1.10, weight=10)
solver.distance_constraint(chair_A[0], chair_B[0], 1.10, 1.10, weight=10)
solver.distance_constraint(chair_D[0], chair_B[0], 2.20, 2.20, weight=10)

# The mirror must remain mounted against the upper wall and face into the room.
solver.against_wall(mirror[0], walls[2])
solver.point_towards(mirror[0], room_center)

# Position constraints for every new asset.
solver.distance_constraint(chair_D[0], chair_D_anchor, 0.0, 0.0, weight=10)
solver.distance_constraint(chair_A[0], chair_A_anchor, 0.0, 0.0, weight=10)
solver.distance_constraint(chair_B[0], chair_B_anchor, 0.0, 0.0, weight=10)
solver.distance_constraint(chair_C[0], chair_C_anchor, 0.0, 0.0, weight=10)
solver.distance_constraint(table_B[0], table_B_anchor, 0.0, 0.0, weight=10)
solver.distance_constraint(table_A[0], table_A_anchor, 0.0, 0.0, weight=10)
solver.distance_constraint(lamp[0], lamp_anchor, 0.0, 0.0, weight=10)
solver.distance_constraint(mirror[0], mirror_anchor, 0.0, 0.0, weight=10)
solver.distance_constraint(pillow[0], pillow_anchor, 0.0, 0.0, weight=10)

# Chairs around table_B face the central table, except chair_C whose required
# orientation toward chair_D was specified earlier and therefore has priority.
solver.point_towards(chair_D[0], table_B[0])
solver.point_towards(chair_A[0], table_B[0])
solver.point_towards(chair_B[0], table_B[0])

# Orientation constraints for both tables and the two small objects.
solver.align_with(table_B[0], table_B_anchor)
solver.align_with(table_A[0], table_A_anchor)
solver.align_with(lamp[0], table_A[0])
solver.align_with(pillow[0], chair_D[0])

# Keep the small objects supported by appropriate surfaces.
solver.on_top_of(lamp[0], table_A[0])
solver.on_top_of(pillow[0], chair_D[0])

solver.constraints = []
pillow[0].position = [3.8291642665863037, 1.011775255203247, 1.0700000524520874]
pillow[0].rotation = [0, 0, 1.1285220522030361]
pillow[0].optimize = 2
lamp[0].position = [1.399999976158142, 2.549999952316284, 0.8400000333786011]
lamp[0].rotation = [0, 0, 0.015707962652587996]
lamp[0].optimize = 2
table_B[0].position = [4.5, 2.0999999046325684, 0.22499999403953552]
table_B[0].rotation = [0, 0, 0.01884955539881635]
table_B[0].optimize = 2
chair_A[0].position = [4.499679088592529, 0.949999988079071, 0.4099999964237213]
chair_A[0].rotation = [0, 0, 1.586504290712113]
chair_A[0].optimize = 2
chair_D[0].position = [3.4000134468078613, 0.949999988079071, 0.4300000071525574]
chair_D[0].rotation = [0, 0, 1.1285220301602836]
chair_D[0].optimize = 2
mirror[0].position = [1.399999976158142, 3.728475332260132, 0.44999998807907104]
mirror[0].rotation = [0, 0, -1.570796283079883]
mirror[0].optimize = 2
table_A[0].position = [1.399999976158142, 2.549999952316284, 0.2750000059604645]
table_A[0].rotation = [0, 0, 0.0157079639172164]
table_A[0].optimize = 2
chair_B[0].position = [5.599999904632568, 0.949999988079071, 0.4099999964237213]
chair_B[0].rotation = [0, 0, 2.013993912106302]
chair_B[0].optimize = 2
chair_C[0].position = [3.4000000953674316, 3.25, 0.4300000071525574]
chair_C[0].rotation = [0, 0, -1.5613715493341729]
chair_C[0].optimize = 2

