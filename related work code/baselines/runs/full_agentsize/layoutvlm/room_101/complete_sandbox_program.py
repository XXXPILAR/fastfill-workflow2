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
    Wall(corner1=[7.00, 0.00, 0.00], corner2=[7.00, 5.00, 0.00]),
    Wall(corner1=[7.00, 5.00, 0.00], corner2=[5.00, 5.00, 0.00]),
    Wall(corner1=[5.00, 5.00, 0.00], corner2=[5.00, 4.00, 0.00]),
    Wall(corner1=[5.00, 4.00, 0.00], corner2=[0.00, 4.00, 0.00]),
    Wall(corner1=[0.00, 4.00, 0.00], corner2=[0.00, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
microwave_oven = Assets(description="A small controlled oven.", size=[0.42, 0.52, 0.30], placements=[AssetInstance() for _ in range(1)])
small_potted_plant = Assets(description="A bunch of big leaves inside of a white pot.", size=[0.35, 0.35, 0.45], placements=[AssetInstance() for _ in range(1)])
bistro_table_A = Assets(description="bistro table", size=[0.80, 0.80, 0.75], placements=[AssetInstance() for _ in range(1)])
freestanding_plant_A = Assets(description="A green plant with spiky leaves in a flower pot.", size=[0.55, 0.55, 1.25], placements=[AssetInstance() for _ in range(1)])
bistro_table_B = Assets(description="bistro table", size=[0.80, 0.80, 0.75], placements=[AssetInstance() for _ in range(1)])
freestanding_plant_B = Assets(description="A green plant with spiky leaves in a flower pot.", size=[0.55, 0.55, 1.25], placements=[AssetInstance() for _ in range(1)])
bar_stool_A = Assets(description="A stool with a metal leg and foot rest with a round black cushion.", size=[0.45, 0.42, 0.75], placements=[AssetInstance() for _ in range(1)])
side_chair_A = Assets(description="A dull white chair with four black legs the back two angled and the front two straight.", size=[0.55, 0.50, 0.82], placements=[AssetInstance() for _ in range(1)])
pantry_lower_cabinets = Assets(description="Kitchen cabinets, a stove, a sink, and a range hood.", size=[0.65, 3.60, 0.92], placements=[AssetInstance() for _ in range(1)])
freestanding_plant_C = Assets(description="A green plant with spiky leaves in a flower pot.", size=[0.55, 0.55, 1.25], placements=[AssetInstance() for _ in range(1)])
bar_stool_B = Assets(description="A stool with a metal leg and foot rest with a round black cushion.", size=[0.45, 0.42, 0.75], placements=[AssetInstance() for _ in range(1)])
sugar_packet_holder_A = Assets(description="A plain tan beverage half gallon carton with a white twist top.", size=[0.08, 0.12, 0.15], placements=[AssetInstance() for _ in range(1)])
recycle_bin_set_A = Assets(description="A green trashcan with a black top and yellow recycling symbol.", size=[0.45, 0.55, 0.90], placements=[AssetInstance() for _ in range(1)])
recycle_bin_set_B = Assets(description="A green trashcan with a black top and yellow recycling symbol.", size=[0.45, 0.55, 0.90], placements=[AssetInstance() for _ in range(1)])
bar_stool_C = Assets(description="A stool with a metal leg and foot rest with a round black cushion.", size=[0.45, 0.42, 0.75], placements=[AssetInstance() for _ in range(1)])
sugar_packet_holder_B = Assets(description="A plain tan beverage half gallon carton with a white twist top.", size=[0.08, 0.12, 0.15], placements=[AssetInstance() for _ in range(1)])
tall_storage_cabinet_A = Assets(description="A light wooden wardrobe.", size=[0.50, 0.90, 2.10], placements=[AssetInstance() for _ in range(1)])
sugar_packet_holder_C = Assets(description="A plain tan beverage half gallon carton with a white twist top.", size=[0.08, 0.12, 0.15], placements=[AssetInstance() for _ in range(1)])
bar_stool_D = Assets(description="A stool with a metal leg and foot rest with a round black cushion.", size=[0.45, 0.42, 0.75], placements=[AssetInstance() for _ in range(1)])
bar_counter = Assets(description="A short long black dresser with a light wooden top.", size=[0.65, 2.40, 1.05], placements=[AssetInstance() for _ in range(1)])
napkin_dispenser = Assets(description="A white box with the top open.", size=[0.12, 0.16, 0.16], placements=[AssetInstance() for _ in range(1)])
side_chair_B = Assets(description="A dull white chair with four black legs the back two angled and the front two straight.", size=[0.55, 0.50, 0.82], placements=[AssetInstance() for _ in range(1)])
sugar_packet_holder_D = Assets(description="A plain tan beverage half gallon carton with a white twist top.", size=[0.08, 0.12, 0.15], placements=[AssetInstance() for _ in range(1)])
dish_rack = Assets(description="A set of dishes.", size=[0.35, 0.50, 0.30], placements=[AssetInstance() for _ in range(1)])
storage_box_A = Assets(description="A wooden box with the lid off and the word fragile written on the side.", size=[0.40, 0.60, 0.35], placements=[AssetInstance() for _ in range(1)])
appliance_tower = Assets(description="A light brown bookcase with three shelves.", size=[0.55, 0.75, 1.80], placements=[AssetInstance() for _ in range(1)])
sugar_packet_holder_E = Assets(description="A plain tan beverage half gallon carton with a white twist top.", size=[0.08, 0.12, 0.15], placements=[AssetInstance() for _ in range(1)])
bar_stool_E = Assets(description="A stool with a metal leg and foot rest with a round black cushion.", size=[0.45, 0.42, 0.75], placements=[AssetInstance() for _ in range(1)])
sugar_packet_holder_F = Assets(description="A plain tan beverage half gallon carton with a white twist top.", size=[0.08, 0.12, 0.15], placements=[AssetInstance() for _ in range(1)])
bar_stool_F = Assets(description="A stool with a metal leg and foot rest with a round black cushion.", size=[0.45, 0.42, 0.75], placements=[AssetInstance() for _ in range(1)])
storage_box_B = Assets(description="A wooden box with the lid off and the word fragile written on the side.", size=[0.40, 0.60, 0.35], placements=[AssetInstance() for _ in range(1)])
side_chair_C = Assets(description="A dull white chair with four black legs the back two angled and the front two straight.", size=[0.55, 0.50, 0.82], placements=[AssetInstance() for _ in range(1)])
tall_storage_cabinet_B = Assets(description="A light wooden wardrobe.", size=[0.50, 0.90, 2.10], placements=[AssetInstance() for _ in range(1)])

microwave_oven[0].instance_id = 'microwave_oven_0'
small_potted_plant[0].instance_id = 'small_potted_plant_0'
bistro_table_A[0].instance_id = 'bistro_table_A_0'
freestanding_plant_A[0].instance_id = 'freestanding_plant_A_0'
bistro_table_B[0].instance_id = 'bistro_table_B_0'
freestanding_plant_B[0].instance_id = 'freestanding_plant_B_0'
bar_stool_A[0].instance_id = 'bar_stool_A_0'
side_chair_A[0].instance_id = 'side_chair_A_0'
pantry_lower_cabinets[0].instance_id = 'pantry_lower_cabinets_0'
freestanding_plant_C[0].instance_id = 'freestanding_plant_C_0'
bar_stool_B[0].instance_id = 'bar_stool_B_0'
sugar_packet_holder_A[0].instance_id = 'sugar_packet_holder_A_0'
recycle_bin_set_A[0].instance_id = 'recycle_bin_set_A_0'
recycle_bin_set_B[0].instance_id = 'recycle_bin_set_B_0'
bar_stool_C[0].instance_id = 'bar_stool_C_0'
sugar_packet_holder_B[0].instance_id = 'sugar_packet_holder_B_0'
tall_storage_cabinet_A[0].instance_id = 'tall_storage_cabinet_A_0'
sugar_packet_holder_C[0].instance_id = 'sugar_packet_holder_C_0'
bar_stool_D[0].instance_id = 'bar_stool_D_0'
bar_counter[0].instance_id = 'bar_counter_0'
napkin_dispenser[0].instance_id = 'napkin_dispenser_0'
side_chair_B[0].instance_id = 'side_chair_B_0'
sugar_packet_holder_D[0].instance_id = 'sugar_packet_holder_D_0'
dish_rack[0].instance_id = 'dish_rack_0'
storage_box_A[0].instance_id = 'storage_box_A_0'
appliance_tower[0].instance_id = 'appliance_tower_0'
sugar_packet_holder_E[0].instance_id = 'sugar_packet_holder_E_0'
bar_stool_E[0].instance_id = 'bar_stool_E_0'
sugar_packet_holder_F[0].instance_id = 'sugar_packet_holder_F_0'
bar_stool_F[0].instance_id = 'bar_stool_F_0'
storage_box_B[0].instance_id = 'storage_box_B_0'
side_chair_C[0].instance_id = 'side_chair_C_0'
tall_storage_cabinet_B[0].instance_id = 'tall_storage_cabinet_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'

microwave_oven[0].position = [2.16123601017601, 3.8474427666798405, 0.15]
microwave_oven[0].rotation = [0, 0, 0]
small_potted_plant[0].position = [0.5648784612948039, 3.1445383421258626, 0.225]
small_potted_plant[0].rotation = [0, 0, 0]
bistro_table_A[0].position = [4.9461962746532, 2.1903840975903925, 0.375]
bistro_table_A[0].rotation = [0, 0, 0]
freestanding_plant_A[0].position = [3.996698864039529, 2.8421364938001155, 0.625]
freestanding_plant_A[0].rotation = [0, 0, 0]
bistro_table_B[0].position = [2.000131988074578, 2.57846672965151, 0.375]
bistro_table_B[0].rotation = [0, 0, 0]
freestanding_plant_B[0].position = [0.7172964776027059, 0.18282637437447125, 0.625]
freestanding_plant_B[0].rotation = [0, 0, 0]
bar_stool_A[0].position = [2.6322736034538106, 1.567456058496115, 0.375]
bar_stool_A[0].rotation = [0, 0, 0]
side_chair_A[0].position = [0.8095402880117404, 0.9281274691763763, 0.41]
side_chair_A[0].rotation = [0, 0, 0]
pantry_lower_cabinets[0].position = [3.927085673365812, 2.623075676912599, 0.46]
pantry_lower_cabinets[0].rotation = [0, 0, 0]
freestanding_plant_C[0].position = [3.337833424852227, 3.4088207639102426, 0.625]
freestanding_plant_C[0].rotation = [0, 0, 0]
bar_stool_B[0].position = [0.6067017523023481, 3.195983309002007, 0.375]
bar_stool_B[0].rotation = [0, 0, 0]
sugar_packet_holder_A[0].position = [3.9861173594228956, 0.2993726003826336, 0.075]
sugar_packet_holder_A[0].rotation = [0, 0, 0]
recycle_bin_set_A[0].position = [2.6998823181746285, 0.7917577380835245, 0.45]
recycle_bin_set_A[0].rotation = [0, 0, 0]
recycle_bin_set_B[0].position = [4.521099568808043, 1.2613065163575932, 0.45]
recycle_bin_set_B[0].rotation = [0, 0, 0]
bar_stool_C[0].position = [6.643405219022166, 0.5048259462513915, 0.375]
bar_stool_C[0].rotation = [0, 0, 0]
sugar_packet_holder_B[0].position = [4.987220984237345, 1.0906889512634859, 0.075]
sugar_packet_holder_B[0].rotation = [0, 0, 0]
tall_storage_cabinet_A[0].position = [1.7940252963542958, 0.6177962027856904, 1.05]
tall_storage_cabinet_A[0].rotation = [0, 0, 0]
sugar_packet_holder_C[0].position = [3.0122774854135854, 0.7875223195989206, 0.075]
sugar_packet_holder_C[0].rotation = [0, 0, 0]
bar_stool_D[0].position = [6.916084546595399, 0.307036300563549, 0.375]
bar_stool_D[0].rotation = [0, 0, 0]
bar_counter[0].position = [1.3419497180230588, 2.310984965230434, 0.525]
bar_counter[0].rotation = [0, 0, 0]
napkin_dispenser[0].position = [4.729966561480085, 1.4441846739953572, 0.08]
napkin_dispenser[0].rotation = [0, 0, 0]
side_chair_B[0].position = [1.5361935760497696, 2.4737523980116953, 0.41]
side_chair_B[0].rotation = [0, 0, 0]
sugar_packet_holder_D[0].position = [2.909432123791319, 2.3484495995487564, 0.075]
sugar_packet_holder_D[0].rotation = [0, 0, 0]
dish_rack[0].position = [0.8158932386578351, 3.6866757797383403, 0.15]
dish_rack[0].rotation = [0, 0, 0]
storage_box_A[0].position = [6.437519544991089, 0.5113871380401919, 0.175]
storage_box_A[0].rotation = [0, 0, 0]
appliance_tower[0].position = [0.055834757452368766, 1.7201908048066255, 0.9]
appliance_tower[0].rotation = [0, 0, 0]
sugar_packet_holder_E[0].position = [1.2415798557292685, 1.4919038962010345, 0.075]
sugar_packet_holder_E[0].rotation = [0, 0, 0]
bar_stool_E[0].position = [2.870744674604086, 0.3089077258656009, 0.375]
bar_stool_E[0].rotation = [0, 0, 0]
sugar_packet_holder_F[0].position = [6.87579825376987, 4.871734840463137, 0.075]
sugar_packet_holder_F[0].rotation = [0, 0, 0]
bar_stool_F[0].position = [1.9939221283154573, 3.741879720831678, 0.375]
bar_stool_F[0].rotation = [0, 0, 0]
storage_box_B[0].position = [0.6530878866847003, 1.5823748275740668, 0.175]
storage_box_B[0].rotation = [0, 0, 0]
side_chair_C[0].position = [3.8104214130522385, 1.2415057199769497, 0.41]
side_chair_C[0].rotation = [0, 0, 0]
tall_storage_cabinet_B[0].position = [0.9783479242451135, 2.0260161121859737, 1.05]
tall_storage_cabinet_B[0].rotation = [0, 0, 0]
microwave_oven[0].position = [2.16123601017601, 3.8474427666798405, 0.15]
microwave_oven[0].rotation = [0, 0, 0]
small_potted_plant[0].position = [0.5648784612948039, 3.1445383421258626, 0.225]
small_potted_plant[0].rotation = [0, 0, 0]
bistro_table_A[0].position = [4.9461962746532, 2.1903840975903925, 0.375]
bistro_table_A[0].rotation = [0, 0, 0]
freestanding_plant_A[0].position = [3.996698864039529, 2.8421364938001155, 0.625]
freestanding_plant_A[0].rotation = [0, 0, 0]
bistro_table_B[0].position = [2.000131988074578, 2.57846672965151, 0.375]
bistro_table_B[0].rotation = [0, 0, 0]
freestanding_plant_B[0].position = [0.7172964776027059, 0.18282637437447125, 0.625]
freestanding_plant_B[0].rotation = [0, 0, 0]
bar_stool_A[0].position = [2.6322736034538106, 1.567456058496115, 0.375]
bar_stool_A[0].rotation = [0, 0, 0]
side_chair_A[0].position = [0.8095402880117404, 0.9281274691763763, 0.41]
side_chair_A[0].rotation = [0, 0, 0]
pantry_lower_cabinets[0].position = [3.927085673365812, 2.623075676912599, 0.46]
pantry_lower_cabinets[0].rotation = [0, 0, 0]
freestanding_plant_C[0].position = [3.337833424852227, 3.4088207639102426, 0.625]
freestanding_plant_C[0].rotation = [0, 0, 0]
bar_stool_B[0].position = [0.6067017523023481, 3.195983309002007, 0.375]
bar_stool_B[0].rotation = [0, 0, 0]
sugar_packet_holder_A[0].position = [3.9861173594228956, 0.2993726003826336, 0.075]
sugar_packet_holder_A[0].rotation = [0, 0, 0]
recycle_bin_set_A[0].position = [2.6998823181746285, 0.7917577380835245, 0.45]
recycle_bin_set_A[0].rotation = [0, 0, 0]
recycle_bin_set_B[0].position = [4.521099568808043, 1.2613065163575932, 0.45]
recycle_bin_set_B[0].rotation = [0, 0, 0]
bar_stool_C[0].position = [6.643405219022166, 0.5048259462513915, 0.375]
bar_stool_C[0].rotation = [0, 0, 0]
sugar_packet_holder_B[0].position = [4.987220984237345, 1.0906889512634859, 0.075]
sugar_packet_holder_B[0].rotation = [0, 0, 0]
tall_storage_cabinet_A[0].position = [1.7940252963542958, 0.6177962027856904, 1.05]
tall_storage_cabinet_A[0].rotation = [0, 0, 0]
sugar_packet_holder_C[0].position = [3.0122774854135854, 0.7875223195989206, 0.075]
sugar_packet_holder_C[0].rotation = [0, 0, 0]
bar_stool_D[0].position = [6.916084546595399, 0.307036300563549, 0.375]
bar_stool_D[0].rotation = [0, 0, 0]
bar_counter[0].position = [1.3419497180230588, 2.310984965230434, 0.525]
bar_counter[0].rotation = [0, 0, 0]
napkin_dispenser[0].position = [4.729966561480085, 1.4441846739953572, 0.08]
napkin_dispenser[0].rotation = [0, 0, 0]
side_chair_B[0].position = [1.5361935760497696, 2.4737523980116953, 0.41]
side_chair_B[0].rotation = [0, 0, 0]
sugar_packet_holder_D[0].position = [2.909432123791319, 2.3484495995487564, 0.075]
sugar_packet_holder_D[0].rotation = [0, 0, 0]
dish_rack[0].position = [0.8158932386578351, 3.6866757797383403, 0.15]
dish_rack[0].rotation = [0, 0, 0]
storage_box_A[0].position = [6.437519544991089, 0.5113871380401919, 0.175]
storage_box_A[0].rotation = [0, 0, 0]
appliance_tower[0].position = [0.055834757452368766, 1.7201908048066255, 0.9]
appliance_tower[0].rotation = [0, 0, 0]
sugar_packet_holder_E[0].position = [1.2415798557292685, 1.4919038962010345, 0.075]
sugar_packet_holder_E[0].rotation = [0, 0, 0]
bar_stool_E[0].position = [2.870744674604086, 0.3089077258656009, 0.375]
bar_stool_E[0].rotation = [0, 0, 0]
sugar_packet_holder_F[0].position = [6.87579825376987, 4.871734840463137, 0.075]
sugar_packet_holder_F[0].rotation = [0, 0, 0]
bar_stool_F[0].position = [1.9939221283154573, 3.741879720831678, 0.375]
bar_stool_F[0].rotation = [0, 0, 0]
storage_box_B[0].position = [0.6530878866847003, 1.5823748275740668, 0.175]
storage_box_B[0].rotation = [0, 0, 0]
side_chair_C[0].position = [3.8104214130522385, 1.2415057199769497, 0.41]
side_chair_C[0].rotation = [0, 0, 0]
tall_storage_cabinet_B[0].position = [0.9783479242451135, 2.0260161121859737, 1.05]
tall_storage_cabinet_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed references keep the proposed layout stable while still allowing the
# solver to make small feasibility adjustments from the lower-weight constraints.
room_center = AssetInstance(position=[3.50, 2.00, 0.00])
counter_left_side = AssetInstance(position=[3.40, 2.00, 0.40])
counter_right_side = AssetInstance(position=[5.40, 2.00, 0.40])
south_facing_reference = AssetInstance(rotation=[0, 0, radians(-90)])
west_facing_reference = AssetInstance(rotation=[0, 0, radians(180)])
east_facing_reference = AssetInstance(rotation=[0, 0, radians(0)])
north_facing_reference = AssetInstance(rotation=[0, 0, radians(90)])


def set_placement(asset_instance, position, rotation_degrees):
    """Set the initial pose and strongly preserve its collision-free location."""
    asset_instance.position = position
    asset_instance.rotation = [0, 0, radians(rotation_degrees)]
    solver.distance_constraint(
        asset_instance,
        AssetInstance(position=position),
        0.0,
        0.0,
        weight=10,
    )


# ---------------------------------------------------------------------------
# Kitchen zone: the long cabinet run is placed against the right wall.
# Its front faces west into the working aisle.
# ---------------------------------------------------------------------------

set_placement(pantry_lower_cabinets[0], [6.675, 2.00, 0.46], 180)
solver.against_wall(pantry_lower_cabinets[0], walls[1])
solver.align_with(pantry_lower_cabinets[0], west_facing_reference)

# Keep countertop appliances on separate portions of the cabinet run.
set_placement(microwave_oven[0], [6.675, 1.00, 1.07], 180)
solver.on_top_of(microwave_oven[0], pantry_lower_cabinets[0])
solver.align_with(microwave_oven[0], pantry_lower_cabinets[0])

set_placement(dish_rack[0], [6.675, 2.85, 1.07], 180)
solver.on_top_of(dish_rack[0], pantry_lower_cabinets[0])
solver.align_with(dish_rack[0], pantry_lower_cabinets[0])

# The appliance tower occupies the wall section to the right of the doorway.
set_placement(appliance_tower[0], [4.55, 3.725, 0.90], -90)
solver.against_wall(appliance_tower[0], walls[4])
solver.align_with(appliance_tower[0], south_facing_reference)

# Storage boxes sit against the same wall, outside the door opening.
set_placement(storage_box_A[0], [3.35, 3.70, 0.175], -90)
solver.against_wall(storage_box_A[0], walls[4])
solver.align_with(storage_box_A[0], south_facing_reference)

set_placement(storage_box_B[0], [3.85, 3.70, 0.175], -90)
solver.against_wall(storage_box_B[0], walls[4])
solver.align_with(storage_box_B[0], south_facing_reference)

# Tall cabinets fit side by side along the back of the upper alcove.
set_placement(tall_storage_cabinet_A[0], [5.50, 4.75, 1.05], -90)
solver.against_wall(tall_storage_cabinet_A[0], walls[2])
solver.align_with(tall_storage_cabinet_A[0], south_facing_reference)

set_placement(tall_storage_cabinet_B[0], [6.45, 4.75, 1.05], -90)
solver.against_wall(tall_storage_cabinet_B[0], walls[2])
solver.align_with(tall_storage_cabinet_B[0], south_facing_reference)


# ---------------------------------------------------------------------------
# Waste station: both bins are against the upper-left wall and remain entirely
# to the left of the door opening, preserving a clear entrance path.
# ---------------------------------------------------------------------------

set_placement(recycle_bin_set_A[0], [0.35, 3.725, 0.45], -90)
solver.against_wall(recycle_bin_set_A[0], walls[4])
solver.align_with(recycle_bin_set_A[0], south_facing_reference)

set_placement(recycle_bin_set_B[0], [0.85, 3.725, 0.45], -90)
solver.against_wall(recycle_bin_set_B[0], walls[4])
solver.align_with(recycle_bin_set_B[0], south_facing_reference)


# ---------------------------------------------------------------------------
# Bistro seating zone on the left. Chairs face their corresponding tables,
# with enough center spacing to avoid overlap and permit normal use.
# ---------------------------------------------------------------------------

set_placement(bistro_table_A[0], [1.50, 1.05, 0.375], 0)
solver.align_with(bistro_table_A[0], east_facing_reference)

set_placement(bistro_table_B[0], [1.50, 2.55, 0.375], 0)
solver.align_with(bistro_table_B[0], bistro_table_A[0])

set_placement(side_chair_A[0], [0.75, 1.05, 0.41], 0)
solver.point_towards(side_chair_A[0], bistro_table_A[0])
solver.distance_constraint(
    side_chair_A[0], bistro_table_A[0], 0.70, 0.80, weight=1
)

set_placement(side_chair_B[0], [2.25, 1.05, 0.41], 180)
solver.point_towards(side_chair_B[0], bistro_table_A[0])
solver.distance_constraint(
    side_chair_B[0], bistro_table_A[0], 0.70, 0.80, weight=1
)

set_placement(side_chair_C[0], [0.75, 2.55, 0.41], 0)
solver.point_towards(side_chair_C[0], bistro_table_B[0])
solver.distance_constraint(
    side_chair_C[0], bistro_table_B[0], 0.70, 0.80, weight=1
)

# The small plant and one packet holder decorate table A without overlapping.
set_placement(small_potted_plant[0], [1.37, 0.93, 0.975], 0)
solver.on_top_of(small_potted_plant[0], bistro_table_A[0])
solver.align_with(small_potted_plant[0], bistro_table_A[0])

set_placement(sugar_packet_holder_A[0], [1.68, 1.16, 0.825], 0)
solver.on_top_of(sugar_packet_holder_A[0], bistro_table_A[0])
solver.align_with(sugar_packet_holder_A[0], bistro_table_A[0])

# o0028 is sugar_packet_holder_F and o0004 is bistro_table_B.
set_placement(sugar_packet_holder_F[0], [1.50, 2.55, 0.825], 0)
solver.on_top_of(sugar_packet_holder_F[0], bistro_table_B[0])
solver.align_with(sugar_packet_holder_F[0], bistro_table_B[0])


# ---------------------------------------------------------------------------
# Central service counter and stools. Three stools are arranged on each side.
# In particular, o0027 (bar_stool_E) is midway between o0006
# (bar_stool_A) and o0010 (bar_stool_B).
# ---------------------------------------------------------------------------

set_placement(bar_counter[0], [4.40, 2.00, 0.525], 180)
solver.align_with(bar_counter[0], west_facing_reference)

# West-side stools face east toward the counter.
set_placement(bar_stool_A[0], [3.70, 1.15, 0.375], 0)
solver.point_towards(bar_stool_A[0], bar_counter[0])

set_placement(bar_stool_E[0], [3.70, 2.00, 0.375], 0)
solver.point_towards(bar_stool_E[0], bar_counter[0])

set_placement(bar_stool_B[0], [3.70, 2.85, 0.375], 0)
solver.point_towards(bar_stool_B[0], bar_counter[0])

# Equal distances preserve the required ordering A -- E -- B.
solver.distance_constraint(
    bar_stool_E[0], bar_stool_A[0], 0.85, 0.85, weight=10
)
solver.distance_constraint(
    bar_stool_E[0], bar_stool_B[0], 0.85, 0.85, weight=10
)

# East-side stools face west toward the counter.
set_placement(bar_stool_C[0], [5.10, 1.15, 0.375], 180)
solver.point_towards(bar_stool_C[0], bar_counter[0])

set_placement(bar_stool_D[0], [5.10, 2.00, 0.375], 180)
solver.point_towards(bar_stool_D[0], bar_counter[0])

set_placement(bar_stool_F[0], [5.10, 2.85, 0.375], 180)
solver.point_towards(bar_stool_F[0], bar_counter[0])

# Countertop accessories occupy distinct points along the counter.
set_placement(sugar_packet_holder_B[0], [4.40, 1.10, 1.125], 180)
solver.on_top_of(sugar_packet_holder_B[0], bar_counter[0])
solver.align_with(sugar_packet_holder_B[0], bar_counter[0])

set_placement(sugar_packet_holder_C[0], [4.40, 1.55, 1.125], 180)
solver.on_top_of(sugar_packet_holder_C[0], bar_counter[0])
solver.align_with(sugar_packet_holder_C[0], bar_counter[0])

set_placement(napkin_dispenser[0], [4.40, 2.00, 1.13], 180)
solver.on_top_of(napkin_dispenser[0], bar_counter[0])
solver.align_with(napkin_dispenser[0], bar_counter[0])

set_placement(sugar_packet_holder_D[0], [4.40, 2.45, 1.125], 180)
solver.on_top_of(sugar_packet_holder_D[0], bar_counter[0])
solver.align_with(sugar_packet_holder_D[0], bar_counter[0])

set_placement(sugar_packet_holder_E[0], [4.40, 2.90, 1.125], 180)
solver.on_top_of(sugar_packet_holder_E[0], bar_counter[0])
solver.align_with(sugar_packet_holder_E[0], bar_counter[0])


# ---------------------------------------------------------------------------
# Plants fill otherwise unused perimeter/corner spaces without obstructing
# seating, kitchen circulation, windows, or the door approach.
# ---------------------------------------------------------------------------

set_placement(freestanding_plant_A[0], [0.30, 1.80, 0.625], 0)
solver.against_wall(freestanding_plant_A[0], walls[5])
solver.point_towards(freestanding_plant_A[0], room_center)

set_placement(freestanding_plant_B[0], [3.35, 0.35, 0.625], 90)
solver.against_wall(freestanding_plant_B[0], walls[0])
solver.point_towards(freestanding_plant_B[0], room_center)

set_placement(freestanding_plant_C[0], [5.70, 3.60, 0.625], 180)
solver.point_towards(freestanding_plant_C[0], room_center)

solver.constraints = []
tall_storage_cabinet_A[0].position = [5.5, 4.748857498168945, 1.0499999523162842]
tall_storage_cabinet_A[0].rotation = [0, 0, -1.5682554107885098]
tall_storage_cabinet_A[0].optimize = 2
freestanding_plant_A[0].position = [0.2900001108646393, 1.7999999523162842, 0.625]
freestanding_plant_A[0].rotation = [0, 0, 0.0025409193727581954]
freestanding_plant_A[0].optimize = 2
small_potted_plant[0].position = [1.3700000047683716, 0.9300000071525574, 0.9750000238418579]
small_potted_plant[0].rotation = [0, 0, 0.022790723574158917]
small_potted_plant[0].optimize = 2
pantry_lower_cabinets[0].position = [6.639868259429932, 2.0, 0.46000000834465027]
pantry_lower_cabinets[0].rotation = [0, 0, -3.1266087702616865]
pantry_lower_cabinets[0].optimize = 2
storage_box_B[0].position = [3.8499999046325684, 3.7100000381469727, 0.17499999701976776]
storage_box_B[0].rotation = [0, 0, -1.5682554077220645]
storage_box_B[0].optimize = 2
bar_stool_F[0].position = [5.099999904632568, 2.8499999046325684, 0.375]
bar_stool_F[0].rotation = [0, 0, -3.1321678761290697]
bar_stool_F[0].optimize = 2
sugar_packet_holder_C[0].position = [4.400000095367432, 1.5499999523162842, 1.125]
sugar_packet_holder_C[0].rotation = [0, 0, -3.1188014063818725]
sugar_packet_holder_C[0].optimize = 2
recycle_bin_set_B[0].position = [0.8500000238418579, 3.734999895095825, 0.44999998807907104]
recycle_bin_set_B[0].rotation = [0, 0, -1.568255409266485]
recycle_bin_set_B[0].optimize = 2
freestanding_plant_C[0].position = [5.699999809265137, 3.5999999046325684, 0.625]
freestanding_plant_C[0].rotation = [0, 0, -3.1321678761290697]
freestanding_plant_C[0].optimize = 2
sugar_packet_holder_A[0].position = [1.6799999475479126, 1.159999966621399, 0.824999988079071]
sugar_packet_holder_A[0].rotation = [0, 0, 0.022790723574158917]
sugar_packet_holder_A[0].optimize = 2
sugar_packet_holder_F[0].position = [1.5, 2.549999952316284, 0.824999988079071]
sugar_packet_holder_F[0].rotation = [0, 0, 0.022788852540103308]
sugar_packet_holder_F[0].optimize = 2
sugar_packet_holder_D[0].position = [4.400000095367432, 2.450000047683716, 1.125]
sugar_packet_holder_D[0].rotation = [0, 0, -3.1188014063818725]
sugar_packet_holder_D[0].optimize = 2
sugar_packet_holder_B[0].position = [4.400000095367432, 1.100000023841858, 1.125]
sugar_packet_holder_B[0].rotation = [0, 0, -3.1188014063818725]
sugar_packet_holder_B[0].optimize = 2
bar_stool_D[0].position = [5.099999904632568, 2.0, 0.375]
bar_stool_D[0].rotation = [0, 0, -3.1321678761290697]
bar_stool_D[0].optimize = 2
side_chair_A[0].position = [0.75, 1.0499999523162842, 0.4099999964237213]
side_chair_A[0].rotation = [0, 0, 0.01256637125682779]
side_chair_A[0].optimize = 2
bar_stool_B[0].position = [3.700000047683716, 2.8499999046325684, 0.375]
bar_stool_B[0].rotation = [0, 0, 0.01256637125682779]
bar_stool_B[0].optimize = 2
appliance_tower[0].position = [4.550000190734863, 3.724047899246216, 0.8999999761581421]
appliance_tower[0].rotation = [0, 0, -1.5682554104885842]
appliance_tower[0].optimize = 2
bistro_table_B[0].position = [1.5, 2.549999952316284, 0.375]
bistro_table_B[0].rotation = [0, 0, 0.03230756527287115]
bistro_table_B[0].optimize = 2
tall_storage_cabinet_B[0].position = [6.449999809265137, 4.748857498168945, 1.0499999523162842]
tall_storage_cabinet_B[0].rotation = [0, 0, -1.5682554107885098]
tall_storage_cabinet_B[0].optimize = 2
dish_rack[0].position = [6.675000190734863, 2.8499999046325684, 1.0700000524520874]
dish_rack[0].rotation = [0, 0, -3.118803053451712]
dish_rack[0].optimize = 2
recycle_bin_set_A[0].position = [0.3499999940395355, 3.734999895095825, 0.44999998807907104]
recycle_bin_set_A[0].rotation = [0, 0, -1.568255409266485]
recycle_bin_set_A[0].optimize = 2
bar_stool_A[0].position = [3.700000047683716, 1.149999976158142, 0.375]
bar_stool_A[0].rotation = [0, 0, 0.01256637125682779]
bar_stool_A[0].optimize = 2
bar_stool_E[0].position = [3.700000047683716, 2.0, 0.375]
bar_stool_E[0].rotation = [0, 0, 0.0157079639172164]
bar_stool_E[0].optimize = 2
sugar_packet_holder_E[0].position = [4.400000095367432, 2.9000000953674316, 1.125]
sugar_packet_holder_E[0].rotation = [0, 0, -3.1188014063818725]
sugar_packet_holder_E[0].optimize = 2
freestanding_plant_B[0].position = [3.3499999046325684, 0.3400000333786011, 0.625]
freestanding_plant_B[0].rotation = [0, 0, 1.573337246167655]
freestanding_plant_B[0].optimize = 2
side_chair_B[0].position = [2.25, 1.0499999523162842, 0.4099999964237213]
side_chair_B[0].rotation = [0, 0, -3.1290262823329655]
side_chair_B[0].optimize = 2
bistro_table_A[0].position = [1.5, 1.0499999523162842, 0.375]
bistro_table_A[0].rotation = [0, 0, 0.03769911119841034]
bistro_table_A[0].optimize = 2
bar_stool_C[0].position = [5.099999904632568, 1.149999976158142, 0.375]
bar_stool_C[0].rotation = [0, 0, -3.1321678761290697]
bar_stool_C[0].optimize = 2
side_chair_C[0].position = [0.75, 2.549999952316284, 0.4099999964237213]
side_chair_C[0].rotation = [0, 0, 0.01256637125682779]
side_chair_C[0].optimize = 2
storage_box_A[0].position = [3.3499999046325684, 3.7100000381469727, 0.17499999701976776]
storage_box_A[0].rotation = [0, 0, -1.5682554077220645]
storage_box_A[0].optimize = 2
napkin_dispenser[0].position = [4.400000095367432, 2.0, 1.1299999952316284]
napkin_dispenser[0].rotation = [0, 0, -3.1188014063818725]
napkin_dispenser[0].optimize = 2
bar_counter[0].position = [4.400000095367432, 2.0, 0.5249999761581421]
bar_counter[0].rotation = [0, 0, -3.0819023942999566]
bar_counter[0].optimize = 2
microwave_oven[0].position = [6.675000190734863, 1.0, 1.0700000524520874]
microwave_oven[0].rotation = [0, 0, -3.118803053451712]
microwave_oven[0].optimize = 2

