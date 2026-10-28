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
    Wall(corner1=[2.00, 2.00, 0.00], corner2=[2.00, 0.00, 0.00]),
    Wall(corner1=[2.00, 0.00, 0.00], corner2=[10.00, 0.00, 0.00]),
    Wall(corner1=[10.00, 0.00, 0.00], corner2=[10.00, 7.00, 0.00]),
    Wall(corner1=[10.00, 7.00, 0.00], corner2=[0.00, 7.00, 0.00]),
    Wall(corner1=[0.00, 7.00, 0.00], corner2=[0.00, 2.00, 0.00]),
    Wall(corner1=[0.00, 2.00, 0.00], corner2=[2.00, 2.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
entry_art_print_A = Assets(description="A multicolored poster of tree foliage labelled 'the jungle book'.", size=[0.03, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
entry_side_cabinet = Assets(description="A tall orange brown dresser with two vertical doors.", size=[0.45, 1.00, 1.25], placements=[AssetInstance() for _ in range(1)])
framed_photo = Assets(description="A framed poster picture of four people with a white note taped to the back.", size=[0.08, 0.30, 0.40], placements=[AssetInstance() for _ in range(1)])
vase = Assets(description="An hourglass shaped vase that is dark brown colored.", size=[0.22, 0.22, 0.40], placements=[AssetInstance() for _ in range(1)])
entrance_console_table = Assets(description="entrance console table", size=[0.38, 1.20, 0.80], placements=[AssetInstance() for _ in range(1)])
small_entry_side_table = Assets(description="A small wooden stool with a round top and two legs.", size=[0.42, 0.42, 0.48], placements=[AssetInstance() for _ in range(1)])
entrance_armchair_A = Assets(description="A wooden armchair with white cushions.", size=[0.78, 0.72, 0.84], placements=[AssetInstance() for _ in range(1)])
scented_candle = Assets(description="A white and yellow candle in a candle holder.", size=[0.10, 0.10, 0.16], placements=[AssetInstance() for _ in range(1)])
basket_A = Assets(description="Tall, narrow tote bag with long handles and two vertical stripes on each side.", size=[0.18, 0.32, 0.50], placements=[AssetInstance() for _ in range(1)])
coat_stand = Assets(description="The coatrack is wooden with a round bottom.", size=[0.48, 0.48, 1.80], placements=[AssetInstance() for _ in range(1)])
basket_B = Assets(description="A blue and yellow bag with two handles.", size=[0.20, 0.42, 0.34], placements=[AssetInstance() for _ in range(1)])
entry_art_print_B = Assets(description="A multicolored poster of tree foliage labelled 'the jungle book'.", size=[0.03, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
floor_lamp_A = Assets(description="A white stool with three legs.", size=[0.48, 0.48, 1.45], placements=[AssetInstance() for _ in range(1)])
entry_bench = Assets(description="A long ottoman with metal legs.", size=[0.45, 1.40, 0.46], placements=[AssetInstance() for _ in range(1)])
entry_storage_basket_set_A = Assets(description="A rectangular wicker basket with the handles folded down.", size=[0.38, 0.55, 0.32], placements=[AssetInstance() for _ in range(1)])
decorative_bowl = Assets(description="A yellow and black cup.", size=[0.18, 0.18, 0.12], placements=[AssetInstance() for _ in range(1)])
entrance_armchair_B = Assets(description="A wooden armchair with white cushions.", size=[0.78, 0.72, 0.84], placements=[AssetInstance() for _ in range(1)])
large_entrance_console_table = Assets(description="Wood table with narrow top and tall legs.", size=[0.40, 1.80, 0.82], placements=[AssetInstance() for _ in range(1)])
entry_storage_basket_set_B = Assets(description="A rectangular wicker basket with the handles folded down.", size=[0.38, 0.55, 0.32], placements=[AssetInstance() for _ in range(1)])
floor_lamp_B = Assets(description="A white stool with three legs.", size=[0.48, 0.48, 1.45], placements=[AssetInstance() for _ in range(1)])
shoe_cabinet_A = Assets(description="A wooden console table with 2 white drawers.", size=[0.38, 1.20, 0.82], placements=[AssetInstance() for _ in range(1)])
wall_shelf_A = Assets(description="A long wooden box with a hinge on it.", size=[0.25, 1.10, 0.24], placements=[AssetInstance() for _ in range(1)])
umbrella_stand = Assets(description="umbrella stand", size=[0.28, 0.28, 0.55], placements=[AssetInstance() for _ in range(1)])
throw_pillow_A = Assets(description="Red pillow with gray border and yellow letters.", size=[0.14, 0.45, 0.45], placements=[AssetInstance() for _ in range(1)])
entry_art_print_C = Assets(description="A multicolored poster of tree foliage labelled 'the jungle book'.", size=[0.03, 0.60, 0.90], placements=[AssetInstance() for _ in range(1)])
shoe_cabinet_B = Assets(description="A wooden console table with 2 white drawers.", size=[0.38, 1.20, 0.82], placements=[AssetInstance() for _ in range(1)])
tall_potted_plant = Assets(description="A green plant with spiky leaves in a flower pot.", size=[0.65, 0.65, 1.65], placements=[AssetInstance() for _ in range(1)])
wall_shelf_B = Assets(description="A long wooden box with a hinge on it.", size=[0.25, 1.10, 0.24], placements=[AssetInstance() for _ in range(1)])
throw_pillow_B = Assets(description="Red pillow with gray border and yellow letters.", size=[0.14, 0.45, 0.45], placements=[AssetInstance() for _ in range(1)])

entry_art_print_A[0].instance_id = 'entry_art_print_A_0'
entry_side_cabinet[0].instance_id = 'entry_side_cabinet_0'
framed_photo[0].instance_id = 'framed_photo_0'
vase[0].instance_id = 'vase_0'
entrance_console_table[0].instance_id = 'entrance_console_table_0'
small_entry_side_table[0].instance_id = 'small_entry_side_table_0'
entrance_armchair_A[0].instance_id = 'entrance_armchair_A_0'
scented_candle[0].instance_id = 'scented_candle_0'
basket_A[0].instance_id = 'basket_A_0'
coat_stand[0].instance_id = 'coat_stand_0'
basket_B[0].instance_id = 'basket_B_0'
entry_art_print_B[0].instance_id = 'entry_art_print_B_0'
floor_lamp_A[0].instance_id = 'floor_lamp_A_0'
entry_bench[0].instance_id = 'entry_bench_0'
entry_storage_basket_set_A[0].instance_id = 'entry_storage_basket_set_A_0'
decorative_bowl[0].instance_id = 'decorative_bowl_0'
entrance_armchair_B[0].instance_id = 'entrance_armchair_B_0'
large_entrance_console_table[0].instance_id = 'large_entrance_console_table_0'
entry_storage_basket_set_B[0].instance_id = 'entry_storage_basket_set_B_0'
floor_lamp_B[0].instance_id = 'floor_lamp_B_0'
shoe_cabinet_A[0].instance_id = 'shoe_cabinet_A_0'
wall_shelf_A[0].instance_id = 'wall_shelf_A_0'
umbrella_stand[0].instance_id = 'umbrella_stand_0'
throw_pillow_A[0].instance_id = 'throw_pillow_A_0'
entry_art_print_C[0].instance_id = 'entry_art_print_C_0'
shoe_cabinet_B[0].instance_id = 'shoe_cabinet_B_0'
tall_potted_plant[0].instance_id = 'tall_potted_plant_0'
wall_shelf_B[0].instance_id = 'wall_shelf_B_0'
throw_pillow_B[0].instance_id = 'throw_pillow_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

entry_art_print_A[0].position = [5.953088787620896, 6.68635729340288, 0.45]
entry_art_print_A[0].rotation = [0, 0, 0]
entry_side_cabinet[0].position = [2.6555255319699533, 2.1014658869136977, 0.625]
entry_side_cabinet[0].rotation = [0, 0, 0]
framed_photo[0].position = [4.111995158592759, 6.025844104551264, 0.2]
framed_photo[0].rotation = [0, 0, 0]
vase[0].position = [6.610952589205256, 0.13311702078228527, 0.2]
vase[0].rotation = [0, 0, 0]
entrance_console_table[0].position = [5.409339269131968, 1.8045765954905983, 0.4]
entrance_console_table[0].rotation = [0, 0, 0]
small_entry_side_table[0].position = [4.176266747551064, 2.0651781506638525, 0.24]
small_entry_side_table[0].rotation = [0, 0, 0]
entrance_armchair_A[0].position = [0.40748242289904923, 3.554850520732436, 0.42]
entrance_armchair_A[0].rotation = [0, 0, 0]
scented_candle[0].position = [5.794226191692581, 3.977906503980843, 0.08]
scented_candle[0].rotation = [0, 0, 0]
basket_A[0].position = [2.4303947458055664, 6.316684611329295, 0.25]
basket_A[0].rotation = [0, 0, 0]
coat_stand[0].position = [4.7670113347782905, 6.8757746531431305, 0.9]
coat_stand[0].rotation = [0, 0, 0]
basket_B[0].position = [9.745981443304867, 4.983818857035233, 0.17]
basket_B[0].rotation = [0, 0, 0]
entry_art_print_B[0].position = [3.306112731465727, 5.895674778882653, 0.45]
entry_art_print_B[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [9.914507001738999, 1.91737498590699, 0.725]
floor_lamp_A[0].rotation = [0, 0, 0]
entry_bench[0].position = [0.49510339830699857, 6.6912750315279625, 0.23]
entry_bench[0].rotation = [0, 0, 0]
entry_storage_basket_set_A[0].position = [0.18189694086511943, 6.076158776143085, 0.16]
entry_storage_basket_set_A[0].rotation = [0, 0, 0]
decorative_bowl[0].position = [5.27317158777138, 2.5216151063946373, 0.06]
decorative_bowl[0].rotation = [0, 0, 0]
entrance_armchair_B[0].position = [2.9582141644500037, 6.8353687541104415, 0.42]
entrance_armchair_B[0].rotation = [0, 0, 0]
large_entrance_console_table[0].position = [5.530980887833156, 3.279967415901439, 0.41]
large_entrance_console_table[0].rotation = [0, 0, 0]
entry_storage_basket_set_B[0].position = [8.77976302966349, 0.5806772992593269, 0.16]
entry_storage_basket_set_B[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [2.218769819642069, 3.947658000988319, 0.725]
floor_lamp_B[0].rotation = [0, 0, 0]
shoe_cabinet_A[0].position = [2.38204245413417, 4.172071794749048, 0.41]
shoe_cabinet_A[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [3.706122905370801, 2.263103905360041, 0.12]
wall_shelf_A[0].rotation = [0, 0, 0]
umbrella_stand[0].position = [4.003442111368745, 2.766954653930065, 0.275]
umbrella_stand[0].rotation = [0, 0, 0]
throw_pillow_A[0].position = [4.986659498844893, 5.950359994080185, 0.225]
throw_pillow_A[0].rotation = [0, 0, 0]
entry_art_print_C[0].position = [7.3478358851428105, 1.2435914146637872, 0.45]
entry_art_print_C[0].rotation = [0, 0, 0]
shoe_cabinet_B[0].position = [5.894697481457587, 4.437963061800682, 0.41]
shoe_cabinet_B[0].rotation = [0, 0, 0]
tall_potted_plant[0].position = [1.4208168857067716, 5.11923280035637, 0.825]
tall_potted_plant[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [0.9511572419555359, 3.4536903718638046, 0.12]
wall_shelf_B[0].rotation = [0, 0, 0]
throw_pillow_B[0].position = [1.3403999655857046, 4.140348739510735, 0.225]
throw_pillow_B[0].rotation = [0, 0, 0]
entry_art_print_A[0].position = [5.953088787620896, 6.68635729340288, 0.45]
entry_art_print_A[0].rotation = [0, 0, 0]
entry_side_cabinet[0].position = [2.6555255319699533, 2.1014658869136977, 0.625]
entry_side_cabinet[0].rotation = [0, 0, 0]
framed_photo[0].position = [4.111995158592759, 6.025844104551264, 0.2]
framed_photo[0].rotation = [0, 0, 0]
vase[0].position = [6.610952589205256, 0.13311702078228527, 0.2]
vase[0].rotation = [0, 0, 0]
entrance_console_table[0].position = [5.409339269131968, 1.8045765954905983, 0.4]
entrance_console_table[0].rotation = [0, 0, 0]
small_entry_side_table[0].position = [4.176266747551064, 2.0651781506638525, 0.24]
small_entry_side_table[0].rotation = [0, 0, 0]
entrance_armchair_A[0].position = [0.40748242289904923, 3.554850520732436, 0.42]
entrance_armchair_A[0].rotation = [0, 0, 0]
scented_candle[0].position = [5.794226191692581, 3.977906503980843, 0.08]
scented_candle[0].rotation = [0, 0, 0]
basket_A[0].position = [2.4303947458055664, 6.316684611329295, 0.25]
basket_A[0].rotation = [0, 0, 0]
coat_stand[0].position = [4.7670113347782905, 6.8757746531431305, 0.9]
coat_stand[0].rotation = [0, 0, 0]
basket_B[0].position = [9.745981443304867, 4.983818857035233, 0.17]
basket_B[0].rotation = [0, 0, 0]
entry_art_print_B[0].position = [3.306112731465727, 5.895674778882653, 0.45]
entry_art_print_B[0].rotation = [0, 0, 0]
floor_lamp_A[0].position = [9.914507001738999, 1.91737498590699, 0.725]
floor_lamp_A[0].rotation = [0, 0, 0]
entry_bench[0].position = [0.49510339830699857, 6.6912750315279625, 0.23]
entry_bench[0].rotation = [0, 0, 0]
entry_storage_basket_set_A[0].position = [0.18189694086511943, 6.076158776143085, 0.16]
entry_storage_basket_set_A[0].rotation = [0, 0, 0]
decorative_bowl[0].position = [5.27317158777138, 2.5216151063946373, 0.06]
decorative_bowl[0].rotation = [0, 0, 0]
entrance_armchair_B[0].position = [2.9582141644500037, 6.8353687541104415, 0.42]
entrance_armchair_B[0].rotation = [0, 0, 0]
large_entrance_console_table[0].position = [5.530980887833156, 3.279967415901439, 0.41]
large_entrance_console_table[0].rotation = [0, 0, 0]
entry_storage_basket_set_B[0].position = [8.77976302966349, 0.5806772992593269, 0.16]
entry_storage_basket_set_B[0].rotation = [0, 0, 0]
floor_lamp_B[0].position = [2.218769819642069, 3.947658000988319, 0.725]
floor_lamp_B[0].rotation = [0, 0, 0]
shoe_cabinet_A[0].position = [2.38204245413417, 4.172071794749048, 0.41]
shoe_cabinet_A[0].rotation = [0, 0, 0]
wall_shelf_A[0].position = [3.706122905370801, 2.263103905360041, 0.12]
wall_shelf_A[0].rotation = [0, 0, 0]
umbrella_stand[0].position = [4.003442111368745, 2.766954653930065, 0.275]
umbrella_stand[0].rotation = [0, 0, 0]
throw_pillow_A[0].position = [4.986659498844893, 5.950359994080185, 0.225]
throw_pillow_A[0].rotation = [0, 0, 0]
entry_art_print_C[0].position = [7.3478358851428105, 1.2435914146637872, 0.45]
entry_art_print_C[0].rotation = [0, 0, 0]
shoe_cabinet_B[0].position = [5.894697481457587, 4.437963061800682, 0.41]
shoe_cabinet_B[0].rotation = [0, 0, 0]
tall_potted_plant[0].position = [1.4208168857067716, 5.11923280035637, 0.825]
tall_potted_plant[0].rotation = [0, 0, 0]
wall_shelf_B[0].position = [0.9511572419555359, 3.4536903718638046, 0.12]
wall_shelf_B[0].rotation = [0, 0, 0]
throw_pillow_B[0].position = [1.3403999655857046, 4.140348739510735, 0.225]
throw_pillow_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Explicit poses use the room's global coordinate system. Wall-mounted pieces are
# raised to useful viewing heights, while floor objects use half their height for z.

entry_art_print_A[0].position = [4.20, 6.985, 1.75]
entry_art_print_A[0].rotation = [0, 0, radians(-90)]

entry_side_cabinet[0].position = [9.775, 1.05, 0.625]
entry_side_cabinet[0].rotation = [0, 0, radians(180)]

framed_photo[0].position = [9.72, 2.55, 1.00]
framed_photo[0].rotation = [0, 0, radians(180)]

vase[0].position = [9.72, 2.20, 1.00]
vase[0].rotation = [0, 0, radians(180)]

entrance_console_table[0].position = [9.81, 2.45, 0.40]
entrance_console_table[0].rotation = [0, 0, radians(180)]

small_entry_side_table[0].position = [5.20, 4.80, 0.24]
small_entry_side_table[0].rotation = [0, 0, 0]

entrance_armchair_A[0].position = [4.25, 4.80, 0.42]
entrance_armchair_A[0].rotation = [0, 0, 0]

scented_candle[0].position = [5.20, 4.80, 0.56]
scented_candle[0].rotation = [0, 0, 0]

# This basket is stored on the left shoe cabinet.
basket_A[0].position = [2.50, 0.21, 1.07]
basket_A[0].rotation = [0, 0, radians(90)]

# The coat stand is between the two shoe cabinets, immediately to the right
# of the wide lower doorway so that it does not obstruct the opening.
coat_stand[0].position = [7.25, 0.24, 0.90]
coat_stand[0].rotation = [0, 0, radians(90)]

# basket_B corresponds to the specified basket o0010 and is placed on the
# right-hand shoe cabinet corresponding to o0020.
basket_B[0].position = [8.35, 0.19, 0.99]
basket_B[0].rotation = [0, 0, radians(90)]

entry_art_print_B[0].position = [5.25, 6.985, 1.75]
entry_art_print_B[0].rotation = [0, 0, radians(-90)]

floor_lamp_A[0].position = [3.25, 4.75, 0.725]
floor_lamp_A[0].rotation = [0, 0, 0]

entry_bench[0].position = [0.225, 5.30, 0.23]
entry_bench[0].rotation = [0, 0, 0]

entry_storage_basket_set_A[0].position = [9.81, 3.25, 0.16]
entry_storage_basket_set_A[0].rotation = [0, 0, radians(180)]

decorative_bowl[0].position = [8.35, 6.72, 0.88]
decorative_bowl[0].rotation = [0, 0, radians(-90)]

entrance_armchair_B[0].position = [6.15, 4.80, 0.42]
entrance_armchair_B[0].rotation = [0, 0, radians(180)]

large_entrance_console_table[0].position = [8.35, 6.80, 0.41]
large_entrance_console_table[0].rotation = [0, 0, radians(-90)]

entry_storage_basket_set_B[0].position = [9.81, 3.85, 0.16]
entry_storage_basket_set_B[0].rotation = [0, 0, radians(180)]

floor_lamp_B[0].position = [7.10, 4.75, 0.725]
floor_lamp_B[0].rotation = [0, 0, radians(180)]

shoe_cabinet_A[0].position = [8.35, 0.19, 0.41]
shoe_cabinet_A[0].rotation = [0, 0, radians(90)]

wall_shelf_A[0].position = [4.65, 6.875, 1.15]
wall_shelf_A[0].rotation = [0, 0, radians(-90)]

umbrella_stand[0].position = [9.20, 0.14, 0.275]
umbrella_stand[0].rotation = [0, 0, radians(90)]

throw_pillow_A[0].position = [4.03, 4.80, 1.065]
throw_pillow_A[0].rotation = [0, 0, 0]

entry_art_print_C[0].position = [8.65, 6.985, 1.75]
entry_art_print_C[0].rotation = [0, 0, radians(-90)]

shoe_cabinet_B[0].position = [2.50, 0.19, 0.41]
shoe_cabinet_B[0].rotation = [0, 0, radians(90)]

tall_potted_plant[0].position = [9.675, 5.50, 0.825]
tall_potted_plant[0].rotation = [0, 0, radians(180)]

wall_shelf_B[0].position = [8.15, 6.875, 1.15]
wall_shelf_B[0].rotation = [0, 0, radians(-90)]

throw_pillow_B[0].position = [6.37, 4.80, 1.065]
throw_pillow_B[0].rotation = [0, 0, radians(180)]


# Important support relationships are listed first so they take precedence.
solver.on_top_of(basket_B[0], shoe_cabinet_A[0])
solver.on_top_of(basket_A[0], shoe_cabinet_B[0])
solver.on_top_of(framed_photo[0], entrance_console_table[0])
solver.on_top_of(vase[0], entrance_console_table[0])
solver.on_top_of(scented_candle[0], small_entry_side_table[0])
solver.on_top_of(decorative_bowl[0], large_entrance_console_table[0])
solver.on_top_of(throw_pillow_A[0], entrance_armchair_A[0])
solver.on_top_of(throw_pillow_B[0], entrance_armchair_B[0])

# Preserve the specified relationship among the two cabinets and coat stand.
# The asymmetric ranges leave the lower doorways clear while retaining the
# intended left-cabinet / coat-stand / right-cabinet ordering.
solver.distance_constraint(
    coat_stand[0], shoe_cabinet_A[0], 0.85, 1.35, weight=10
)
solver.distance_constraint(
    coat_stand[0], shoe_cabinet_B[0], 4.40, 5.10, weight=10
)

# Wall furniture and wall decor remain associated with their intended walls.
# walls[1] is the lower wall, walls[2] the right wall, walls[3] the upper wall,
# and walls[4] the left wall.
solver.against_wall(entry_art_print_A[0], walls[3])
solver.against_wall(entry_art_print_B[0], walls[3])
solver.against_wall(entry_art_print_C[0], walls[3])
solver.against_wall(wall_shelf_A[0], walls[3])
solver.against_wall(wall_shelf_B[0], walls[3])
solver.against_wall(large_entrance_console_table[0], walls[3])

solver.against_wall(entry_side_cabinet[0], walls[2])
solver.against_wall(entrance_console_table[0], walls[2])
solver.against_wall(entry_storage_basket_set_A[0], walls[2])
solver.against_wall(entry_storage_basket_set_B[0], walls[2])
solver.against_wall(tall_potted_plant[0], walls[2])

solver.against_wall(entry_bench[0], walls[4])

solver.against_wall(shoe_cabinet_A[0], walls[1])
solver.against_wall(shoe_cabinet_B[0], walls[1])
solver.against_wall(coat_stand[0], walls[1])
solver.against_wall(umbrella_stand[0], walls[1])

# Maintain the functional conversation/seating group.
solver.distance_constraint(
    entrance_armchair_A[0], small_entry_side_table[0], 0.80, 1.10, weight=10
)
solver.distance_constraint(
    entrance_armchair_B[0], small_entry_side_table[0], 0.80, 1.10, weight=10
)
solver.point_towards(entrance_armchair_A[0], small_entry_side_table[0])
solver.point_towards(entrance_armchair_B[0], small_entry_side_table[0])
solver.point_towards(small_entry_side_table[0], entrance_armchair_B[0])

solver.distance_constraint(
    floor_lamp_A[0], entrance_armchair_A[0], 0.75, 1.25
)
solver.distance_constraint(
    floor_lamp_B[0], entrance_armchair_B[0], 0.75, 1.25
)
solver.point_towards(floor_lamp_A[0], entrance_armchair_A[0])
solver.point_towards(floor_lamp_B[0], entrance_armchair_B[0])

# Keep tabletop and chair accessories oriented with their supporting furniture.
solver.align_with(framed_photo[0], entrance_console_table[0])
solver.align_with(vase[0], entrance_console_table[0])
solver.align_with(scented_candle[0], small_entry_side_table[0])
solver.align_with(basket_A[0], shoe_cabinet_B[0])
solver.align_with(basket_B[0], shoe_cabinet_A[0])
solver.align_with(decorative_bowl[0], large_entrance_console_table[0])
solver.align_with(throw_pillow_A[0], entrance_armchair_A[0])
solver.align_with(throw_pillow_B[0], entrance_armchair_B[0])

# Add an exact pose anchor for every new instance. Each anchor supplies the
# required position-based constraint, while align_with preserves its intended
# absolute orientation if the solver adjusts the layout.
def constrain_pose(asset_instance):
    pose_anchor = AssetInstance(
        position=list(asset_instance.position),
        rotation=list(asset_instance.rotation),
    )
    solver.distance_constraint(
        asset_instance, pose_anchor, 0.0, 0.0, weight=10
    )
    solver.align_with(asset_instance, pose_anchor)


constrain_pose(entry_art_print_A[0])
constrain_pose(entry_side_cabinet[0])
constrain_pose(framed_photo[0])
constrain_pose(vase[0])
constrain_pose(entrance_console_table[0])
constrain_pose(small_entry_side_table[0])
constrain_pose(entrance_armchair_A[0])
constrain_pose(scented_candle[0])
constrain_pose(basket_A[0])
constrain_pose(coat_stand[0])
constrain_pose(basket_B[0])
constrain_pose(entry_art_print_B[0])
constrain_pose(floor_lamp_A[0])
constrain_pose(entry_bench[0])
constrain_pose(entry_storage_basket_set_A[0])
constrain_pose(decorative_bowl[0])
constrain_pose(entrance_armchair_B[0])
constrain_pose(large_entrance_console_table[0])
constrain_pose(entry_storage_basket_set_B[0])
constrain_pose(floor_lamp_B[0])
constrain_pose(shoe_cabinet_A[0])
constrain_pose(wall_shelf_A[0])
constrain_pose(umbrella_stand[0])
constrain_pose(throw_pillow_A[0])
constrain_pose(entry_art_print_C[0])
constrain_pose(shoe_cabinet_B[0])
constrain_pose(tall_potted_plant[0])
constrain_pose(wall_shelf_B[0])
constrain_pose(throw_pillow_B[0])

solver.constraints = []
entrance_console_table[0].position = [9.80498218536377, 2.450000047683716, 0.4000000059604645]
entrance_console_table[0].rotation = [0, 0, -3.126608741205061]
entrance_console_table[0].optimize = 2
shoe_cabinet_B[0].position = [2.597602128982544, 0.19314786791801453, 0.4099999964237213]
shoe_cabinet_B[0].rotation = [0, 0, 1.5826693420210731]
shoe_cabinet_B[0].optimize = 2
basket_A[0].position = [2.5, 0.20999999344348907, 1.0699999332427979]
basket_A[0].rotation = [0, 0, 1.596756476952191]
basket_A[0].optimize = 2
entry_storage_basket_set_A[0].position = [9.809301376342773, 3.25, 0.1599999964237213]
entry_storage_basket_set_A[0].rotation = [0, 0, -3.139051734217035]
entry_storage_basket_set_A[0].optimize = 2
vase[0].position = [9.720000267028809, 2.200000047683716, 1.0]
vase[0].rotation = [0, 0, -3.1156310954314645]
vase[0].optimize = 2
entry_bench[0].position = [0.22677791118621826, 5.300000190734863, 0.23000000417232513]
entry_bench[0].rotation = [0, 0, 0.0025409071293785845]
entry_bench[0].optimize = 2
small_entry_side_table[0].position = [5.199999809265137, 4.800000190734863, 0.23999999463558197]
small_entry_side_table[0].rotation = [0, 0, 0.031415925765816845]
small_entry_side_table[0].optimize = 2
throw_pillow_A[0].position = [4.03000020980835, 4.800000190734863, 1.0649999380111694]
throw_pillow_A[0].rotation = [0, 0, 0.02596226265766525]
throw_pillow_A[0].optimize = 2
basket_B[0].position = [8.350000381469727, 0.1899999976158142, 0.9900000095367432]
basket_B[0].rotation = [0, 0, 1.596756476952191]
basket_B[0].optimize = 2
entry_storage_basket_set_B[0].position = [9.809301376342773, 3.8499999046325684, 0.1599999964237213]
entry_storage_basket_set_B[0].rotation = [0, 0, -3.139051734217035]
entry_storage_basket_set_B[0].optimize = 2
throw_pillow_B[0].position = [6.369999885559082, 4.800000190734863, 1.0649999380111694]
throw_pillow_B[0].rotation = [0, 0, -3.1156299670346495]
throw_pillow_B[0].optimize = 2
large_entrance_console_table[0].position = [8.350000381469727, 6.793071746826172, 0.4099999964237213]
large_entrance_console_table[0].rotation = [0, 0, -1.562034120120442]
large_entrance_console_table[0].optimize = 2
wall_shelf_A[0].position = [4.650000095367432, 6.873602867126465, 0.11999999731779099]
wall_shelf_A[0].rotation = [0, 0, -1.56825541415488]
wall_shelf_A[0].optimize = 2
wall_shelf_B[0].position = [8.149999618530273, 6.873602867126465, 0.11999999731779099]
wall_shelf_B[0].rotation = [0, 0, -1.56825541415488]
wall_shelf_B[0].optimize = 2
entry_art_print_C[0].position = [8.649999618530273, 6.992923259735107, 0.44999998807907104]
entry_art_print_C[0].rotation = [0, 0, -1.5682554064999652]
entry_art_print_C[0].optimize = 2
shoe_cabinet_A[0].position = [8.350000381469727, 0.19314786791801453, 0.4099999964237213]
shoe_cabinet_A[0].rotation = [0, 0, 1.582669341098879]
shoe_cabinet_A[0].optimize = 2
tall_potted_plant[0].position = [9.674175262451172, 5.5, 0.824999988079071]
tall_potted_plant[0].rotation = [0, 0, -3.1390517345169613]
tall_potted_plant[0].optimize = 2
entry_art_print_A[0].position = [4.199999809265137, 6.992923259735107, 0.44999998807907104]
entry_art_print_A[0].rotation = [0, 0, -1.5682554064999652]
entry_art_print_A[0].optimize = 2
entrance_armchair_B[0].position = [6.150000095367432, 4.800000190734863, 0.41999998688697815]
entrance_armchair_B[0].rotation = [0, 0, -3.1101767278239763]
entrance_armchair_B[0].optimize = 2
framed_photo[0].position = [9.720000267028809, 2.549999952316284, 1.0]
framed_photo[0].rotation = [0, 0, -3.1156310954314645]
framed_photo[0].optimize = 2
entrance_armchair_A[0].position = [4.25, 4.800000190734863, 0.41999998688697815]
entrance_armchair_A[0].rotation = [0, 0, 0.02827433441159227]
entrance_armchair_A[0].optimize = 2
decorative_bowl[0].position = [8.350000381469727, 6.71999979019165, 0.8799999952316284]
decorative_bowl[0].rotation = [0, 0, -1.5448403563126964]
decorative_bowl[0].optimize = 2
entry_side_cabinet[0].position = [9.773730278015137, 1.0499999523162842, 0.625]
entry_side_cabinet[0].rotation = [0, 0, -3.139051739727678]
entry_side_cabinet[0].optimize = 2
scented_candle[0].position = [5.199999809265137, 4.800000190734863, 0.5600000023841858]
scented_candle[0].rotation = [0, 0, 0.02596268655514389]
scented_candle[0].optimize = 2
entry_art_print_B[0].position = [5.25, 6.992923259735107, 0.44999998807907104]
entry_art_print_B[0].rotation = [0, 0, -1.5682554064999652]
entry_art_print_B[0].optimize = 2
coat_stand[0].position = [7.25, 0.24209369719028473, 0.8999999761581421]
coat_stand[0].rotation = [0, 0, 1.5795585506295236]
coat_stand[0].optimize = 2
floor_lamp_A[0].position = [3.25, 4.75, 0.7250000238418579]
floor_lamp_A[0].rotation = [0, 0, 0.0157079639172164]
floor_lamp_A[0].optimize = 2
umbrella_stand[0].position = [9.199999809265137, 0.14035528898239136, 0.2750000059604645]
umbrella_stand[0].rotation = [0, 0, 1.573337248311928]
umbrella_stand[0].optimize = 2
floor_lamp_B[0].position = [7.099999904632568, 4.75, 0.7250000238418579]
floor_lamp_B[0].rotation = [0, 0, -3.125884689672577]
floor_lamp_B[0].optimize = 2

