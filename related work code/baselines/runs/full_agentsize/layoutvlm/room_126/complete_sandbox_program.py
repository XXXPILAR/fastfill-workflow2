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
    Wall(corner1=[1.00, 2.00, 0.00], corner2=[0.00, 2.00, 0.00]),
    Wall(corner1=[0.00, 2.00, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[4.00, 0.00, 0.00]),
    Wall(corner1=[4.00, 0.00, 0.00], corner2=[4.00, 2.00, 0.00]),
    Wall(corner1=[4.00, 2.00, 0.00], corner2=[3.00, 2.00, 0.00]),
    Wall(corner1=[3.00, 2.00, 0.00], corner2=[3.00, 7.00, 0.00]),
    Wall(corner1=[3.00, 7.00, 0.00], corner2=[1.00, 7.00, 0.00]),
    Wall(corner1=[1.00, 7.00, 0.00], corner2=[1.00, 2.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
medicine_bottle_A = Assets(description="A saltshaker full of salt.", size=[0.06, 0.06, 0.12], placements=[AssetInstance() for _ in range(1)])
base_cabinet_storage = Assets(description="base cabinet storage", size=[0.55, 1.20, 0.90], placements=[AssetInstance() for _ in range(1)])
medicine_bottle_B = Assets(description="A jar with a screw-style lip and a partial frog inside.", size=[0.09, 0.09, 0.16], placements=[AssetInstance() for _ in range(1)])
doctor_desk = Assets(description="The desk is light colored wood with small shelves on the inside.", size=[0.75, 1.50, 0.76], placements=[AssetInstance() for _ in range(1)])
doctor_task_chair = Assets(description="A white office chair.", size=[0.62, 0.62, 1.05], placements=[AssetInstance() for _ in range(1)])
medicine_bottle_C = Assets(description="A clear medicine bottle with a label.", size=[0.06, 0.06, 0.13], placements=[AssetInstance() for _ in range(1)])
document_tray_A = Assets(description="A black envelope with a gold seal.", size=[0.24, 0.32, 0.04], placements=[AssetInstance() for _ in range(1)])
small_pillow = Assets(description="A plain white square pillow.", size=[0.15, 0.45, 0.45], placements=[AssetInstance() for _ in range(1)])
box_of_gloves = Assets(description="A red and black box with white font.", size=[0.12, 0.24, 0.08], placements=[AssetInstance() for _ in range(1)])
desk_phone = Assets(description="An electronic device used to communicate with others by dialing a number on the keypad and holding a handle to your ear.", size=[0.20, 0.22, 0.12], placements=[AssetInstance() for _ in range(1)])
document_tray_B = Assets(description="A white and grey electronic weight scale.", size=[0.25, 0.30, 0.06], placements=[AssetInstance() for _ in range(1)])
medicine_bottle_D = Assets(description="a glass bottle with blue cap, containing liquid or alcohol.", size=[0.07, 0.07, 0.18], placements=[AssetInstance() for _ in range(1)])
exam_table = Assets(description="A wooden table with a light patterned table cloth.", size=[0.70, 1.90, 0.78], placements=[AssetInstance() for _ in range(1)])
storage_box = Assets(description="A dark brown loaf of bread with each side neatly sliced.", size=[0.18, 0.30, 0.14], placements=[AssetInstance() for _ in range(1)])
stainless_tray_A = Assets(description="a red apple on a white tray.", size=[0.22, 0.30, 0.08], placements=[AssetInstance() for _ in range(1)])
instrument_trolley = Assets(description="instrument trolley", size=[0.45, 0.65, 0.90], placements=[AssetInstance() for _ in range(1)])
disinfectant_bottle = Assets(description="a glass bottle with blue cap, containing liquid or alcohol.", size=[0.08, 0.08, 0.22], placements=[AssetInstance() for _ in range(1)])
sink_counter = Assets(description="A white bathroom sink.", size=[0.55, 0.90, 0.85], placements=[AssetInstance() for _ in range(1)])
stainless_tray_B = Assets(description="a red apple on a white tray.", size=[0.22, 0.30, 0.08], placements=[AssetInstance() for _ in range(1)])

medicine_bottle_A[0].instance_id = 'medicine_bottle_A_0'
base_cabinet_storage[0].instance_id = 'base_cabinet_storage_0'
medicine_bottle_B[0].instance_id = 'medicine_bottle_B_0'
doctor_desk[0].instance_id = 'doctor_desk_0'
doctor_task_chair[0].instance_id = 'doctor_task_chair_0'
medicine_bottle_C[0].instance_id = 'medicine_bottle_C_0'
document_tray_A[0].instance_id = 'document_tray_A_0'
small_pillow[0].instance_id = 'small_pillow_0'
box_of_gloves[0].instance_id = 'box_of_gloves_0'
desk_phone[0].instance_id = 'desk_phone_0'
document_tray_B[0].instance_id = 'document_tray_B_0'
medicine_bottle_D[0].instance_id = 'medicine_bottle_D_0'
exam_table[0].instance_id = 'exam_table_0'
storage_box[0].instance_id = 'storage_box_0'
stainless_tray_A[0].instance_id = 'stainless_tray_A_0'
instrument_trolley[0].instance_id = 'instrument_trolley_0'
disinfectant_bottle[0].instance_id = 'disinfectant_bottle_0'
sink_counter[0].instance_id = 'sink_counter_0'
stainless_tray_B[0].instance_id = 'stainless_tray_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'

medicine_bottle_A[0].position = [0.9455074103091841, 0.1390716674587651, 0.06]
medicine_bottle_A[0].rotation = [0, 0, 0]
base_cabinet_storage[0].position = [0.48468773511816776, 0.6777338601597385, 0.45]
base_cabinet_storage[0].rotation = [0, 0, 0]
medicine_bottle_B[0].position = [2.410493472795472, 0.8419615934959893, 0.08]
medicine_bottle_B[0].rotation = [0, 0, 0]
doctor_desk[0].position = [2.289393935711125, 1.0351494131395442, 0.38]
doctor_desk[0].rotation = [0, 0, 0]
doctor_task_chair[0].position = [2.1862784572958405, 1.0397978828119443, 0.525]
doctor_task_chair[0].rotation = [0, 0, 0]
medicine_bottle_C[0].position = [1.6256761270239735, 0.21415067268378318, 0.065]
medicine_bottle_C[0].rotation = [0, 0, 0]
document_tray_A[0].position = [0.09188187273445614, 0.5085583801232098, 0.02]
document_tray_A[0].rotation = [0, 0, 0]
small_pillow[0].position = [1.920692557196178, 5.866272948546598, 0.225]
small_pillow[0].rotation = [0, 0, 0]
box_of_gloves[0].position = [3.8259323148100415, 0.5393020996388812, 0.04]
box_of_gloves[0].rotation = [0, 0, 0]
desk_phone[0].position = [2.192338857421555, 5.998280335739021, 0.06]
desk_phone[0].rotation = [0, 0, 0]
document_tray_B[0].position = [1.9242393219930936, 0.7850747202168102, 0.03]
document_tray_B[0].rotation = [0, 0, 0]
medicine_bottle_D[0].position = [2.7050369378431727, 0.02432778049050921, 0.09]
medicine_bottle_D[0].rotation = [0, 0, 0]
exam_table[0].position = [2.358419151654176, 0.2541864319398399, 0.39]
exam_table[0].rotation = [0, 0, 0]
storage_box[0].position = [2.3206909302440075, 3.054071960709174, 0.07]
storage_box[0].rotation = [0, 0, 0]
stainless_tray_A[0].position = [2.4863524666145196, 0.6840699859239758, 0.04]
stainless_tray_A[0].rotation = [0, 0, 0]
instrument_trolley[0].position = [2.520038680952312, 3.9036966947137586, 0.45]
instrument_trolley[0].rotation = [0, 0, 0]
disinfectant_bottle[0].position = [3.0805416968435533, 0.42353681073334437, 0.11]
disinfectant_bottle[0].rotation = [0, 0, 0]
sink_counter[0].position = [1.4949218314413684, 3.0932415659408465, 0.425]
sink_counter[0].rotation = [0, 0, 0]
stainless_tray_B[0].position = [1.337693319090488, 2.61092957982794, 0.04]
stainless_tray_B[0].rotation = [0, 0, 0]
medicine_bottle_A[0].position = [0.9455074103091841, 0.1390716674587651, 0.06]
medicine_bottle_A[0].rotation = [0, 0, 0]
base_cabinet_storage[0].position = [0.48468773511816776, 0.6777338601597385, 0.45]
base_cabinet_storage[0].rotation = [0, 0, 0]
medicine_bottle_B[0].position = [2.410493472795472, 0.8419615934959893, 0.08]
medicine_bottle_B[0].rotation = [0, 0, 0]
doctor_desk[0].position = [2.289393935711125, 1.0351494131395442, 0.38]
doctor_desk[0].rotation = [0, 0, 0]
doctor_task_chair[0].position = [2.1862784572958405, 1.0397978828119443, 0.525]
doctor_task_chair[0].rotation = [0, 0, 0]
medicine_bottle_C[0].position = [1.6256761270239735, 0.21415067268378318, 0.065]
medicine_bottle_C[0].rotation = [0, 0, 0]
document_tray_A[0].position = [0.09188187273445614, 0.5085583801232098, 0.02]
document_tray_A[0].rotation = [0, 0, 0]
small_pillow[0].position = [1.920692557196178, 5.866272948546598, 0.225]
small_pillow[0].rotation = [0, 0, 0]
box_of_gloves[0].position = [3.8259323148100415, 0.5393020996388812, 0.04]
box_of_gloves[0].rotation = [0, 0, 0]
desk_phone[0].position = [2.192338857421555, 5.998280335739021, 0.06]
desk_phone[0].rotation = [0, 0, 0]
document_tray_B[0].position = [1.9242393219930936, 0.7850747202168102, 0.03]
document_tray_B[0].rotation = [0, 0, 0]
medicine_bottle_D[0].position = [2.7050369378431727, 0.02432778049050921, 0.09]
medicine_bottle_D[0].rotation = [0, 0, 0]
exam_table[0].position = [2.358419151654176, 0.2541864319398399, 0.39]
exam_table[0].rotation = [0, 0, 0]
storage_box[0].position = [2.3206909302440075, 3.054071960709174, 0.07]
storage_box[0].rotation = [0, 0, 0]
stainless_tray_A[0].position = [2.4863524666145196, 0.6840699859239758, 0.04]
stainless_tray_A[0].rotation = [0, 0, 0]
instrument_trolley[0].position = [2.520038680952312, 3.9036966947137586, 0.45]
instrument_trolley[0].rotation = [0, 0, 0]
disinfectant_bottle[0].position = [3.0805416968435533, 0.42353681073334437, 0.11]
disinfectant_bottle[0].rotation = [0, 0, 0]
sink_counter[0].position = [1.4949218314413684, 3.0932415659408465, 0.425]
sink_counter[0].rotation = [0, 0, 0]
stainless_tray_B[0].position = [1.337693319090488, 2.61092957982794, 0.04]
stainless_tray_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Arrange the floor-standing furniture around the perimeter, leaving the door
# at (0.00, 1.39) and the central circulation path unobstructed.
base_cabinet_storage.placements[0] = AssetInstance(
    position=[1.50, 6.725, 0.45],
    rotation=[0, 0, radians(-90)]
)
sink_counter.placements[0] = AssetInstance(
    position=[2.55, 6.725, 0.425],
    rotation=[0, 0, radians(-90)]
)
doctor_desk.placements[0] = AssetInstance(
    position=[3.625, 1.10, 0.38],
    rotation=[0, 0, radians(180)]
)
doctor_task_chair.placements[0] = AssetInstance(
    position=[2.65, 1.10, 0.525],
    rotation=[0, 0, radians(0)]
)
exam_table.placements[0] = AssetInstance(
    position=[1.35, 4.35, 0.39],
    rotation=[0, 0, radians(0)]
)
instrument_trolley.placements[0] = AssetInstance(
    position=[1.225, 5.70, 0.45],
    rotation=[0, 0, radians(0)]
)

# Place the required phone and one document item on the doctor's desk.
desk_phone.placements[0] = AssetInstance(
    position=[3.45, 0.72, 0.82],
    rotation=[0, 0, radians(180)]
)
document_tray_A.placements[0] = AssetInstance(
    position=[3.48, 1.35, 0.78],
    rotation=[0, 0, radians(180)]
)

# Put the pillow on the patient end of the examination table.
small_pillow.placements[0] = AssetInstance(
    position=[1.35, 4.85, 1.005],
    rotation=[0, 0, radians(0)]
)

# Group medicines, gloves, and general storage on the base cabinet.
medicine_bottle_A.placements[0] = AssetInstance(
    position=[1.05, 6.78, 0.96],
    rotation=[0, 0, radians(-90)]
)
medicine_bottle_B.placements[0] = AssetInstance(
    position=[1.35, 6.78, 0.98],
    rotation=[0, 0, radians(-90)]
)
medicine_bottle_C.placements[0] = AssetInstance(
    position=[1.65, 6.78, 0.965],
    rotation=[0, 0, radians(-90)]
)
medicine_bottle_D.placements[0] = AssetInstance(
    position=[1.95, 6.78, 0.99],
    rotation=[0, 0, radians(-90)]
)
box_of_gloves.placements[0] = AssetInstance(
    position=[1.10, 6.53, 0.94],
    rotation=[0, 0, radians(90)]
)
storage_box.placements[0] = AssetInstance(
    position=[1.75, 6.55, 0.97],
    rotation=[0, 0, radians(90)]
)

# Keep washing/cleaning-related items on the sink counter.
disinfectant_bottle.placements[0] = AssetInstance(
    position=[2.30, 6.70, 0.96],
    rotation=[0, 0, radians(-90)]
)
document_tray_B.placements[0] = AssetInstance(
    position=[2.68, 6.68, 0.88],
    rotation=[0, 0, radians(90)]
)

# Place both instrument trays side-by-side along the trolley's length.
stainless_tray_A.placements[0] = AssetInstance(
    position=[1.225, 5.53, 0.94],
    rotation=[0, 0, radians(0)]
)
stainless_tray_B.placements[0] = AssetInstance(
    position=[1.225, 5.87, 0.94],
    rotation=[0, 0, radians(0)]
)

# Position constraints for the perimeter furniture. These walls do not contain
# the door or the two windows.
solver.against_wall(base_cabinet_storage[0], walls[6])
solver.against_wall(sink_counter[0], walls[6])
solver.against_wall(doctor_desk[0], walls[3])
solver.against_wall(exam_table[0], walls[7])
solver.against_wall(instrument_trolley[0], walls[7])

# Preserve each floor item's intended location along its wall. The chair is
# positioned relative to the desk so it remains in a usable working location.
solver.distance_constraint(
    base_cabinet_storage[0],
    AssetInstance(position=[1.50, 6.725, 0.45]),
    0, 0, weight=10
)
solver.distance_constraint(
    sink_counter[0],
    AssetInstance(position=[2.55, 6.725, 0.425]),
    0, 0, weight=10
)
solver.distance_constraint(
    doctor_desk[0],
    AssetInstance(position=[3.625, 1.10, 0.38]),
    0, 0, weight=10
)
solver.distance_constraint(
    exam_table[0],
    AssetInstance(position=[1.35, 4.35, 0.39]),
    0, 0, weight=10
)
solver.distance_constraint(
    instrument_trolley[0],
    AssetInstance(position=[1.225, 5.70, 0.45]),
    0, 0, weight=10
)
solver.distance_constraint(
    doctor_task_chair[0], doctor_desk[0],
    0.95, 1.05, weight=10
)

# Orientation constraints for all floor-standing furniture.
solver.align_with(
    base_cabinet_storage[0],
    AssetInstance(rotation=[0, 0, radians(-90)])
)
solver.align_with(
    sink_counter[0],
    AssetInstance(rotation=[0, 0, radians(-90)])
)
solver.align_with(
    doctor_desk[0],
    AssetInstance(rotation=[0, 0, radians(180)])
)
solver.point_towards(doctor_task_chair[0], doctor_desk[0])
solver.align_with(
    exam_table[0],
    AssetInstance(rotation=[0, 0, radians(0)])
)
solver.align_with(
    instrument_trolley[0],
    AssetInstance(rotation=[0, 0, radians(0)])
)

# The phone must remain on the doctor's desk. All other small objects likewise
# receive a supporting-surface constraint so they are not placed on the floor.
solver.on_top_of(desk_phone[0], doctor_desk[0])
solver.on_top_of(document_tray_A[0], doctor_desk[0])
solver.on_top_of(small_pillow[0], exam_table[0])

solver.on_top_of(medicine_bottle_A[0], base_cabinet_storage[0])
solver.on_top_of(medicine_bottle_B[0], base_cabinet_storage[0])
solver.on_top_of(medicine_bottle_C[0], base_cabinet_storage[0])
solver.on_top_of(medicine_bottle_D[0], base_cabinet_storage[0])
solver.on_top_of(box_of_gloves[0], base_cabinet_storage[0])
solver.on_top_of(storage_box[0], base_cabinet_storage[0])

solver.on_top_of(disinfectant_bottle[0], sink_counter[0])
solver.on_top_of(document_tray_B[0], sink_counter[0])

solver.on_top_of(stainless_tray_A[0], instrument_trolley[0])
solver.on_top_of(stainless_tray_B[0], instrument_trolley[0])

# Exact tabletop anchors are position-based constraints. They keep the small
# items separated while the on-top constraints maintain the correct heights.
solver.distance_constraint(
    desk_phone[0],
    AssetInstance(position=[3.45, 0.72, 0.82]),
    0, 0, weight=10
)
solver.distance_constraint(
    document_tray_A[0],
    AssetInstance(position=[3.48, 1.35, 0.78]),
    0, 0, weight=10
)
solver.distance_constraint(
    small_pillow[0],
    AssetInstance(position=[1.35, 4.85, 1.005]),
    0, 0, weight=10
)

solver.distance_constraint(
    medicine_bottle_A[0],
    AssetInstance(position=[1.05, 6.78, 0.96]),
    0, 0, weight=10
)
solver.distance_constraint(
    medicine_bottle_B[0],
    AssetInstance(position=[1.35, 6.78, 0.98]),
    0, 0, weight=10
)
solver.distance_constraint(
    medicine_bottle_C[0],
    AssetInstance(position=[1.65, 6.78, 0.965]),
    0, 0, weight=10
)
solver.distance_constraint(
    medicine_bottle_D[0],
    AssetInstance(position=[1.95, 6.78, 0.99]),
    0, 0, weight=10
)
solver.distance_constraint(
    box_of_gloves[0],
    AssetInstance(position=[1.10, 6.53, 0.94]),
    0, 0, weight=10
)
solver.distance_constraint(
    storage_box[0],
    AssetInstance(position=[1.75, 6.55, 0.97]),
    0, 0, weight=10
)

solver.distance_constraint(
    disinfectant_bottle[0],
    AssetInstance(position=[2.30, 6.70, 0.96]),
    0, 0, weight=10
)
solver.distance_constraint(
    document_tray_B[0],
    AssetInstance(position=[2.68, 6.68, 0.88]),
    0, 0, weight=10
)
solver.distance_constraint(
    stainless_tray_A[0],
    AssetInstance(position=[1.225, 5.53, 0.94]),
    0, 0, weight=10
)
solver.distance_constraint(
    stainless_tray_B[0],
    AssetInstance(position=[1.225, 5.87, 0.94]),
    0, 0, weight=10
)

# Orientation constraints for every supported object.
solver.align_with(desk_phone[0], doctor_desk[0])
solver.align_with(document_tray_A[0], doctor_desk[0])
solver.align_with(small_pillow[0], exam_table[0])

solver.align_with(medicine_bottle_A[0], base_cabinet_storage[0])
solver.align_with(medicine_bottle_B[0], base_cabinet_storage[0])
solver.align_with(medicine_bottle_C[0], base_cabinet_storage[0])
solver.align_with(medicine_bottle_D[0], base_cabinet_storage[0])
solver.align_with(box_of_gloves[0], base_cabinet_storage[0], angle=180)
solver.align_with(storage_box[0], base_cabinet_storage[0], angle=180)

solver.align_with(disinfectant_bottle[0], sink_counter[0])
solver.align_with(document_tray_B[0], sink_counter[0], angle=180)

solver.align_with(stainless_tray_A[0], instrument_trolley[0])
solver.align_with(stainless_tray_B[0], instrument_trolley[0])

solver.constraints = []
document_tray_B[0].position = [2.680000066757202, 6.679999828338623, 0.8799999952316284]
document_tray_B[0].rotation = [0, 0, 1.5935859269329777]
document_tray_B[0].optimize = 2
stainless_tray_B[0].position = [1.225000023841858, 5.869999885559082, 0.9399999976158142]
stainless_tray_B[0].rotation = [0, 0, 0.02278960013808119]
stainless_tray_B[0].optimize = 2
document_tray_A[0].position = [3.4800000190734863, 1.350000023841858, 0.7799999713897705]
document_tray_A[0].rotation = [0, 0, -3.118802304959478]
document_tray_A[0].optimize = 2
box_of_gloves[0].position = [1.1192365884780884, 6.53000020980835, 0.9399999976158142]
box_of_gloves[0].rotation = [0, 0, 1.5935874253208393]
box_of_gloves[0].optimize = 2
medicine_bottle_B[0].position = [1.350000023841858, 6.78000020980835, 0.9799999594688416]
medicine_bottle_B[0].rotation = [0, 0, -1.5480052282689538]
medicine_bottle_B[0].optimize = 2
stainless_tray_A[0].position = [1.225000023841858, 5.53000020980835, 0.9399999976158142]
stainless_tray_A[0].rotation = [0, 0, 0.02278960013808119]
stainless_tray_A[0].optimize = 2
medicine_bottle_C[0].position = [1.649999976158142, 6.78000020980835, 0.9649999737739563]
medicine_bottle_C[0].rotation = [0, 0, -1.5480052282689538]
medicine_bottle_C[0].optimize = 2
desk_phone[0].position = [3.450000047683716, 0.7200000286102295, 0.8199999928474426]
desk_phone[0].rotation = [0, 0, -3.118802304959478]
desk_phone[0].optimize = 2
doctor_task_chair[0].position = [2.6500000953674316, 1.100000023841858, 0.5249999761581421]
doctor_task_chair[0].rotation = [0, 0, 0.00942477746072377]
doctor_task_chair[0].optimize = 2
base_cabinet_storage[0].position = [1.613059401512146, 6.705200672149658, 0.44999998807907104]
base_cabinet_storage[0].rotation = [0, 0, -1.5309216940551225]
base_cabinet_storage[0].optimize = 2
small_pillow[0].position = [1.350000023841858, 4.849999904632568, 1.0049999952316284]
small_pillow[0].rotation = [0, 0, 0.02278736617577962]
small_pillow[0].optimize = 2
instrument_trolley[0].position = [1.229844331741333, 5.699999809265137, 0.44999998807907104]
instrument_trolley[0].rotation = [0, 0, 0.014983916920112477]
instrument_trolley[0].optimize = 2
disinfectant_bottle[0].position = [2.299999952316284, 6.699999809265137, 0.9600000381469727]
disinfectant_bottle[0].rotation = [0, 0, -1.5480067266568154]
disinfectant_bottle[0].optimize = 2
storage_box[0].position = [1.75, 6.550000190734863, 0.9699999690055847]
storage_box[0].rotation = [0, 0, 1.5935874253208393]
storage_box[0].optimize = 2
medicine_bottle_A[0].position = [1.0499999523162842, 6.78000020980835, 0.9599999785423279]
medicine_bottle_A[0].rotation = [0, 0, -1.5480052282689538]
medicine_bottle_A[0].optimize = 2
sink_counter[0].position = [2.549999952316284, 6.723778247833252, 0.42500001192092896]
sink_counter[0].rotation = [0, 0, -1.5558124116436118]
sink_counter[0].optimize = 2
doctor_desk[0].position = [3.6116268634796143, 1.100000023841858, 0.3799999952316284]
doctor_desk[0].rotation = [0, 0, -3.1203866582324205]
doctor_desk[0].optimize = 2
exam_table[0].position = [1.3578439950942993, 4.349999904632568, 0.38999998569488525]
exam_table[0].rotation = [0, 0, 0.008762204717934291]
exam_table[0].optimize = 2
medicine_bottle_D[0].position = [1.9500000476837158, 6.78000020980835, 0.9900000095367432]
medicine_bottle_D[0].rotation = [0, 0, -1.5480052282689538]
medicine_bottle_D[0].optimize = 2

