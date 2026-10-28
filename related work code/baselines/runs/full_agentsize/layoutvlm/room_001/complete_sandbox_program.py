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
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.08, 0.00, 0.00]),
    Wall(corner1=[3.08, 0.00, 0.00], corner2=[3.08, 7.29, 0.00]),
    Wall(corner1=[3.08, 7.29, 0.00], corner2=[0.00, 7.29, 0.00]),
    Wall(corner1=[0.00, 7.29, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
chair_A = Assets(description="chair", size=[0.58, 0.55, 0.82], placements=[AssetInstance() for _ in range(1)])
sofa = Assets(description="sofa", size=[0.82, 1.85, 0.82], placements=[AssetInstance() for _ in range(1)])
cabinet = Assets(description="cabinet", size=[0.45, 1.20, 0.80], placements=[AssetInstance() for _ in range(1)])
chair_B = Assets(description="chair", size=[0.58, 0.55, 0.82], placements=[AssetInstance() for _ in range(1)])
plant = Assets(description="plant", size=[0.55, 0.55, 1.25], placements=[AssetInstance() for _ in range(1)])
mirror = Assets(description="mirror", size=[0.04, 0.75, 1.20], placements=[AssetInstance() for _ in range(1)])
lamp_A = Assets(description="lamp", size=[0.40, 0.40, 1.55], placements=[AssetInstance() for _ in range(1)])
bed = Assets(description="bed", size=[2.00, 1.60, 0.55], placements=[AssetInstance() for _ in range(1)])
pillow_A = Assets(description="pillow", size=[0.40, 0.65, 0.15], placements=[AssetInstance() for _ in range(1)])
lamp_B = Assets(description="lamp", size=[0.32, 0.32, 0.55], placements=[AssetInstance() for _ in range(1)])
pillow_B = Assets(description="pillow", size=[0.40, 0.65, 0.15], placements=[AssetInstance() for _ in range(1)])
chair_C = Assets(description="chair", size=[0.58, 0.55, 0.82], placements=[AssetInstance() for _ in range(1)])
chair_D = Assets(description="chair", size=[0.58, 0.55, 0.82], placements=[AssetInstance() for _ in range(1)])

chair_A[0].instance_id = 'chair_A_0'
sofa[0].instance_id = 'sofa_0'
cabinet[0].instance_id = 'cabinet_0'
chair_B[0].instance_id = 'chair_B_0'
plant[0].instance_id = 'plant_0'
mirror[0].instance_id = 'mirror_0'
lamp_A[0].instance_id = 'lamp_A_0'
bed[0].instance_id = 'bed_0'
pillow_A[0].instance_id = 'pillow_A_0'
lamp_B[0].instance_id = 'lamp_B_0'
pillow_B[0].instance_id = 'pillow_B_0'
chair_C[0].instance_id = 'chair_C_0'
chair_D[0].instance_id = 'chair_D_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'

chair_A[0].position = [1.6315970784265847, 1.1589016618525712, 0.41]
chair_A[0].rotation = [0, 0, 0]
sofa[0].position = [1.2848927031537114, 4.376031224724663, 0.41]
sofa[0].rotation = [0, 0, 0]
cabinet[0].position = [1.6144253735739786, 4.441325079627125, 0.4]
cabinet[0].rotation = [0, 0, 0]
chair_B[0].position = [2.074353732102993, 6.291852468915535, 0.41]
chair_B[0].rotation = [0, 0, 0]
plant[0].position = [2.7765160699128817, 6.753984562356199, 0.625]
plant[0].rotation = [0, 0, 0]
mirror[0].position = [0.9930430172347543, 1.4379283364133522, 0.6]
mirror[0].rotation = [0, 0, 0]
lamp_A[0].position = [1.8563018054652132, 1.7771271357650928, 0.775]
lamp_A[0].rotation = [0, 0, 0]
bed[0].position = [1.340938110579855, 0.6777104079001963, 0.275]
bed[0].rotation = [0, 0, 0]
pillow_A[0].position = [0.925195832096948, 0.30054520538518803, 0.075]
pillow_A[0].rotation = [0, 0, 0]
lamp_B[0].position = [2.2659400282805033, 6.874295552869429, 0.275]
lamp_B[0].rotation = [0, 0, 0]
pillow_B[0].position = [0.9853174873638202, 2.378343225441147, 0.075]
pillow_B[0].rotation = [0, 0, 0]
chair_C[0].position = [2.682360159682537, 4.384065471865589, 0.41]
chair_C[0].rotation = [0, 0, 0]
chair_D[0].position = [0.924937156329604, 2.497180616550691, 0.41]
chair_D[0].rotation = [0, 0, 0]
chair_A[0].position = [1.6315970784265847, 1.1589016618525712, 0.41]
chair_A[0].rotation = [0, 0, 0]
sofa[0].position = [1.2848927031537114, 4.376031224724663, 0.41]
sofa[0].rotation = [0, 0, 0]
cabinet[0].position = [1.6144253735739786, 4.441325079627125, 0.4]
cabinet[0].rotation = [0, 0, 0]
chair_B[0].position = [2.074353732102993, 6.291852468915535, 0.41]
chair_B[0].rotation = [0, 0, 0]
plant[0].position = [2.7765160699128817, 6.753984562356199, 0.625]
plant[0].rotation = [0, 0, 0]
mirror[0].position = [0.9930430172347543, 1.4379283364133522, 0.6]
mirror[0].rotation = [0, 0, 0]
lamp_A[0].position = [1.8563018054652132, 1.7771271357650928, 0.775]
lamp_A[0].rotation = [0, 0, 0]
bed[0].position = [1.340938110579855, 0.6777104079001963, 0.275]
bed[0].rotation = [0, 0, 0]
pillow_A[0].position = [0.925195832096948, 0.30054520538518803, 0.075]
pillow_A[0].rotation = [0, 0, 0]
lamp_B[0].position = [2.2659400282805033, 6.874295552869429, 0.275]
lamp_B[0].rotation = [0, 0, 0]
pillow_B[0].position = [0.9853174873638202, 2.378343225441147, 0.075]
pillow_B[0].rotation = [0, 0, 0]
chair_C[0].position = [2.682360159682537, 4.384065471865589, 0.41]
chair_C[0].rotation = [0, 0, 0]
chair_D[0].position = [0.924937156329604, 2.497180616550691, 0.41]
chair_D[0].rotation = [0, 0, 0]

solver.constraints = []

# Place the bed lengthwise in the room. Its center lies between chair_A
# (below the bed) and chair_C (above the bed), while the doorway approach
# at the top-right of the room remains unobstructed.
chair_A[0].position = [0.75, 3.35, 0.41]
chair_A[0].rotation = [0, 0, radians(90)]

sofa[0].position = [2.67, 3.00, 0.41]
sofa[0].rotation = [0, 0, radians(180)]

cabinet[0].position = [2.855, 5.20, 0.40]
cabinet[0].rotation = [0, 0, radians(180)]

chair_B[0].position = [0.55, 1.35, 0.41]
chair_B[0].rotation = [0, 0, radians(54)]

plant[0].position = [2.72, 0.45, 0.625]
plant[0].rotation = [0, 0, radians(180)]

mirror[0].position = [3.06, 6.55, 0.60]
mirror[0].rotation = [0, 0, radians(180)]

# The floor lamp is in front of the sofa, serving as its requested focal point.
lamp_A[0].position = [1.75, 3.00, 0.775]
lamp_A[0].rotation = [0, 0, 0]

bed[0].position = [1.00, 4.95, 0.275]
bed[0].rotation = [0, 0, radians(90)]

# Both pillows sit near the upper end of the bed.
pillow_A[0].position = [0.63, 5.55, 0.625]
pillow_A[0].rotation = [0, 0, radians(90)]

# The smaller lamp is placed on the cabinet because no separate side table
# is available.
lamp_B[0].position = [2.855, 5.20, 1.075]
lamp_B[0].rotation = [0, 0, radians(180)]

pillow_B[0].position = [1.37, 5.55, 0.625]
pillow_B[0].rotation = [0, 0, radians(90)]

chair_C[0].position = [0.65, 6.55, 0.41]
chair_C[0].rotation = [0, 0, radians(-90)]

chair_D[0].position = [2.45, 1.35, 0.41]
chair_D[0].rotation = [0, 0, radians(113)]


# Fixed points preserve the selected non-overlapping arrangement while the
# solver makes any small physical-feasibility adjustments.
chair_A_anchor = AssetInstance(position=[0.75, 3.35, 0.41])
sofa_anchor = AssetInstance(position=[2.67, 3.00, 0.41])
cabinet_anchor = AssetInstance(position=[2.855, 5.20, 0.40])
chair_B_anchor = AssetInstance(position=[0.55, 1.35, 0.41])
plant_anchor = AssetInstance(position=[2.72, 0.45, 0.625])
mirror_anchor = AssetInstance(position=[3.06, 6.55, 0.60])
lamp_A_anchor = AssetInstance(position=[1.75, 3.00, 0.775])
bed_anchor = AssetInstance(position=[1.00, 4.95, 0.275])
pillow_A_anchor = AssetInstance(position=[0.63, 5.55, 0.625])
lamp_B_anchor = AssetInstance(position=[2.855, 5.20, 1.075])
pillow_B_anchor = AssetInstance(position=[1.37, 5.55, 0.625])
chair_C_anchor = AssetInstance(position=[0.65, 6.55, 0.41])
chair_D_anchor = AssetInstance(position=[2.45, 1.35, 0.41])

# This reference supplies an absolute east-facing orientation for alignments.
east_facing_reference = AssetInstance(rotation=[0, 0, 0])


# Preserve the required wall relationships first. These centers account for
# the assets' half-depths, placing their backs flush with the right wall.
solver.against_wall(sofa[0], walls[1])
solver.against_wall(cabinet[0], walls[1])
solver.against_wall(mirror[0], walls[1])

# Position constraints for every floor-standing asset.
solver.distance_constraint(chair_A[0], chair_A_anchor, 0, 0, weight=10)
solver.distance_constraint(sofa[0], sofa_anchor, 0, 0, weight=10)
solver.distance_constraint(cabinet[0], cabinet_anchor, 0, 0, weight=10)
solver.distance_constraint(chair_B[0], chair_B_anchor, 0, 0, weight=10)
solver.distance_constraint(plant[0], plant_anchor, 0, 0, weight=10)
solver.distance_constraint(mirror[0], mirror_anchor, 0, 0, weight=10)
solver.distance_constraint(lamp_A[0], lamp_A_anchor, 0, 0, weight=10)
solver.distance_constraint(bed[0], bed_anchor, 0, 0, weight=10)
solver.distance_constraint(chair_C[0], chair_C_anchor, 0, 0, weight=10)
solver.distance_constraint(chair_D[0], chair_D_anchor, 0, 0, weight=10)

# Enforce the requested "chair_A — bed — chair_C" ordering. The bounds allow
# minor solver adjustments while keeping one chair at each end of the bed.
solver.distance_constraint(bed[0], chair_A[0], 1.50, 1.75, weight=5)
solver.distance_constraint(bed[0], chair_C[0], 1.50, 1.75, weight=5)

# Supported objects receive both their vertical support relationship and a
# position-based constraint, as required for every new instance.
solver.on_top_of(pillow_A[0], bed[0])
solver.distance_constraint(pillow_A[0], pillow_A_anchor, 0, 0, weight=10)

solver.on_top_of(pillow_B[0], bed[0])
solver.distance_constraint(pillow_B[0], pillow_B_anchor, 0, 0, weight=10)

solver.on_top_of(lamp_B[0], cabinet[0])
solver.distance_constraint(lamp_B[0], lamp_B_anchor, 0, 0, weight=10)


# Orientation constraints for every asset.
solver.point_towards(chair_A[0], bed[0])
solver.point_towards(sofa[0], lamp_A[0])
solver.align_with(cabinet[0], east_facing_reference, angle=180)
solver.point_towards(chair_B[0], lamp_A[0])
solver.align_with(plant[0], sofa[0])
solver.point_towards(mirror[0], bed[0])
solver.point_towards(lamp_A[0], sofa[0])
solver.align_with(bed[0], east_facing_reference, angle=90)
solver.align_with(pillow_A[0], bed[0])
solver.align_with(lamp_B[0], cabinet[0])
solver.align_with(pillow_B[0], bed[0])
solver.point_towards(chair_C[0], bed[0])
solver.point_towards(chair_D[0], lamp_A[0])

solver.constraints = []
plant[0].position = [2.7200000286102295, 0.44999998807907104, 0.625]
plant[0].rotation = [0, 0, 3.141588767723508]
plant[0].optimize = 2
pillow_A[0].position = [0.6299999952316284, 5.550000190734863, 0.625]
pillow_A[0].rotation = [0, 0, 1.6085027964282677]
pillow_A[0].optimize = 2
sofa[0].position = [2.6678271293640137, 3.0, 0.4099999964237213]
sofa[0].rotation = [0, 0, -3.1415870693937173]
sofa[0].optimize = 2
lamp_A[0].position = [1.75, 3.0, 0.7749999761581421]
lamp_A[0].rotation = [0, 0, 0.01884955539881635]
lamp_A[0].optimize = 2
chair_D[0].position = [2.450000047683716, 1.350000023841858, 0.4099999964237213]
chair_D[0].rotation = [0, 0, 1.9816468336888873]
chair_D[0].optimize = 2
chair_A[0].position = [0.75, 3.3499999046325684, 0.4099999964237213]
chair_A[0].rotation = [0, 0, 1.5833626980517244]
chair_A[0].optimize = 2
cabinet[0].position = [2.852830171585083, 5.199999809265137, 0.4000000059604645]
cabinet[0].rotation = [0, 0, -3.141587106320229]
cabinet[0].optimize = 2
lamp_B[0].position = [2.8550000190734863, 5.199999809265137, 1.0750000476837158]
lamp_B[0].rotation = [0, 0, 3.1415846291315543]
lamp_B[0].optimize = 2
mirror[0].position = [3.0578293800354004, 6.550000190734863, 0.6000000238418579]
mirror[0].rotation = [0, 0, 3.1415900935394125]
mirror[0].optimize = 2
bed[0].position = [1.0, 4.949999809265137, 0.2750000059604645]
bed[0].rotation = [0, 0, 1.608495437993307]
bed[0].optimize = 2
pillow_B[0].position = [1.3700000047683716, 5.550000190734863, 0.625]
pillow_B[0].rotation = [0, 0, 1.6085027964282677]
pillow_B[0].optimize = 2
chair_B[0].position = [0.550000011920929, 1.350000023841858, 0.4099999964237213]
chair_B[0].rotation = [0, 0, 0.9519025704480031]
chair_B[0].optimize = 2
chair_C[0].position = [0.6499999761581421, 6.550000190734863, 0.4099999964237213]
chair_C[0].rotation = [0, 0, -1.5582299555380688]
chair_C[0].optimize = 2

