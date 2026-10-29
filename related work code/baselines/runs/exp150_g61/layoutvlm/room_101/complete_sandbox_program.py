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
microwave_oven = Assets(description="A small controlled oven.", size=[0.40, 0.50, 0.30], placements=[AssetInstance() for _ in range(1)])
small_potted_plant = Assets(description="A bunch of big leaves inside of a white pot.", size=[0.40, 0.40, 0.55], placements=[AssetInstance() for _ in range(1)])
bistro_table_A = Assets(description="bistro table", size=[0.80, 0.80, 0.75], placements=[AssetInstance() for _ in range(1)])
freestanding_plant_A = Assets(description="A green plant with spiky leaves in a flower pot.", size=[0.55, 0.55, 1.40], placements=[AssetInstance() for _ in range(1)])
bistro_table_B = Assets(description="bistro table", size=[0.80, 0.80, 0.75], placements=[AssetInstance() for _ in range(1)])
freestanding_plant_B = Assets(description="A green plant with spiky leaves in a flower pot.", size=[0.55, 0.55, 1.40], placements=[AssetInstance() for _ in range(1)])
bar_stool_A = Assets(description="A stool with a metal leg and foot rest with a round black cushion.", size=[0.42, 0.42, 0.76], placements=[AssetInstance() for _ in range(1)])
side_chair_A = Assets(description="A dull white chair with four black legs the back two angled and the front two straight.", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
pantry_lower_cabinets = Assets(description="Kitchen cabinets, a stove, a sink, and a range hood.", size=[0.60, 2.40, 0.90], placements=[AssetInstance() for _ in range(1)])
freestanding_plant_C = Assets(description="A green plant with spiky leaves in a flower pot.", size=[0.55, 0.55, 1.40], placements=[AssetInstance() for _ in range(1)])
bar_stool_B = Assets(description="A stool with a metal leg and foot rest with a round black cushion.", size=[0.42, 0.42, 0.76], placements=[AssetInstance() for _ in range(1)])
sugar_packet_holder_A = Assets(description="A plain tan beverage half gallon carton with a white twist top.", size=[0.10, 0.10, 0.24], placements=[AssetInstance() for _ in range(1)])
recycle_bin_set_A = Assets(description="A green trashcan with a black top and yellow recycling symbol.", size=[0.40, 0.40, 0.75], placements=[AssetInstance() for _ in range(1)])
recycle_bin_set_B = Assets(description="A green trashcan with a black top and yellow recycling symbol.", size=[0.40, 0.40, 0.75], placements=[AssetInstance() for _ in range(1)])
bar_stool_C = Assets(description="A stool with a metal leg and foot rest with a round black cushion.", size=[0.42, 0.42, 0.76], placements=[AssetInstance() for _ in range(1)])
sugar_packet_holder_B = Assets(description="A plain tan beverage half gallon carton with a white twist top.", size=[0.10, 0.10, 0.24], placements=[AssetInstance() for _ in range(1)])
tall_storage_cabinet_A = Assets(description="A light wooden wardrobe.", size=[0.55, 0.80, 2.00], placements=[AssetInstance() for _ in range(1)])
sugar_packet_holder_C = Assets(description="A plain tan beverage half gallon carton with a white twist top.", size=[0.10, 0.10, 0.24], placements=[AssetInstance() for _ in range(1)])
bar_stool_D = Assets(description="A stool with a metal leg and foot rest with a round black cushion.", size=[0.42, 0.42, 0.76], placements=[AssetInstance() for _ in range(1)])
bar_counter = Assets(description="A short long black dresser with a light wooden top.", size=[0.65, 3.60, 1.05], placements=[AssetInstance() for _ in range(1)])
napkin_dispenser = Assets(description="A white box with the top open.", size=[0.18, 0.18, 0.15], placements=[AssetInstance() for _ in range(1)])
side_chair_B = Assets(description="A dull white chair with four black legs the back two angled and the front two straight.", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
sugar_packet_holder_D = Assets(description="A plain tan beverage half gallon carton with a white twist top.", size=[0.10, 0.10, 0.24], placements=[AssetInstance() for _ in range(1)])
dish_rack = Assets(description="A set of dishes.", size=[0.32, 0.45, 0.25], placements=[AssetInstance() for _ in range(1)])
storage_box_A = Assets(description="A wooden box with the lid off and the word fragile written on the side.", size=[0.35, 0.45, 0.30], placements=[AssetInstance() for _ in range(1)])
appliance_tower = Assets(description="A light brown bookcase with three shelves.", size=[0.50, 0.65, 1.80], placements=[AssetInstance() for _ in range(1)])
sugar_packet_holder_E = Assets(description="A plain tan beverage half gallon carton with a white twist top.", size=[0.10, 0.10, 0.24], placements=[AssetInstance() for _ in range(1)])
bar_stool_E = Assets(description="A stool with a metal leg and foot rest with a round black cushion.", size=[0.42, 0.42, 0.76], placements=[AssetInstance() for _ in range(1)])
sugar_packet_holder_F = Assets(description="A plain tan beverage half gallon carton with a white twist top.", size=[0.10, 0.10, 0.24], placements=[AssetInstance() for _ in range(1)])
bar_stool_F = Assets(description="A stool with a metal leg and foot rest with a round black cushion.", size=[0.42, 0.42, 0.76], placements=[AssetInstance() for _ in range(1)])
storage_box_B = Assets(description="A wooden box with the lid off and the word fragile written on the side.", size=[0.35, 0.45, 0.30], placements=[AssetInstance() for _ in range(1)])
side_chair_C = Assets(description="A dull white chair with four black legs the back two angled and the front two straight.", size=[0.53, 0.48, 0.82], placements=[AssetInstance() for _ in range(1)])
tall_storage_cabinet_B = Assets(description="A light wooden wardrobe.", size=[0.55, 0.80, 2.00], placements=[AssetInstance() for _ in range(1)])

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

microwave_oven[0].position = [0.0371643943519776, 1.2996776303456796, 0.15]
microwave_oven[0].rotation = [0, 0, 0]
small_potted_plant[0].position = [5.058733612085987, 1.5926789206044494, 0.275]
small_potted_plant[0].rotation = [0, 0, 0]
bistro_table_A[0].position = [3.251423130536698, 3.8739117426510745, 0.375]
bistro_table_A[0].rotation = [0, 0, 0]
freestanding_plant_A[0].position = [5.942466157698069, 3.9471514162137793, 0.7]
freestanding_plant_A[0].rotation = [0, 0, 0]
bistro_table_B[0].position = [5.314477691256221, 1.1125169792198975, 0.375]
bistro_table_B[0].rotation = [0, 0, 0]
freestanding_plant_B[0].position = [1.5087226195603018, 3.131013806013225, 0.7]
freestanding_plant_B[0].rotation = [0, 0, 0]
bar_stool_A[0].position = [3.423382443616325, 3.4899009108612415, 0.38]
bar_stool_A[0].rotation = [0, 0, 0]
side_chair_A[0].position = [1.069643500386067, 0.3791600707391607, 0.41]
side_chair_A[0].rotation = [0, 0, 0]
pantry_lower_cabinets[0].position = [6.467067126562185, 1.8519240890427047, 0.45]
pantry_lower_cabinets[0].rotation = [0, 0, 0]
freestanding_plant_C[0].position = [3.9690974749564027, 1.620469749802561, 0.7]
freestanding_plant_C[0].rotation = [0, 0, 0]
bar_stool_B[0].position = [6.961335577930223, 2.1469703236490596, 0.38]
bar_stool_B[0].rotation = [0, 0, 0]
sugar_packet_holder_A[0].position = [2.7399418922207097, 1.1544357715292275, 0.12]
sugar_packet_holder_A[0].rotation = [0, 0, 0]
recycle_bin_set_A[0].position = [0.3675106715164439, 2.1351719703427823, 0.375]
recycle_bin_set_A[0].rotation = [0, 0, 0]
recycle_bin_set_B[0].position = [1.043402317726927, 1.9093213815414156, 0.375]
recycle_bin_set_B[0].rotation = [0, 0, 0]
bar_stool_C[0].position = [1.5265709883249796, 0.3797228238025613, 0.38]
bar_stool_C[0].rotation = [0, 0, 0]
sugar_packet_holder_B[0].position = [4.06864343656017, 1.7710001877429427, 0.12]
sugar_packet_holder_B[0].rotation = [0, 0, 0]
tall_storage_cabinet_A[0].position = [2.0360462010533227, 3.6573547365724157, 1.0]
tall_storage_cabinet_A[0].rotation = [0, 0, 0]
sugar_packet_holder_C[0].position = [0.20132356371310556, 2.847818619662601, 0.12]
sugar_packet_holder_C[0].rotation = [0, 0, 0]
bar_stool_D[0].position = [0.6807660719105226, 1.8532577749905743, 0.38]
bar_stool_D[0].rotation = [0, 0, 0]
bar_counter[0].position = [5.204700810497504, 1.529183814173554, 0.525]
bar_counter[0].rotation = [0, 0, 0]
napkin_dispenser[0].position = [6.413894659759753, 3.67195120193976, 0.075]
napkin_dispenser[0].rotation = [0, 0, 0]
side_chair_B[0].position = [3.2125663239741957, 0.964935121959633, 0.41]
side_chair_B[0].rotation = [0, 0, 0]
sugar_packet_holder_D[0].position = [1.2326161935657622, 0.6271030786373394, 0.12]
sugar_packet_holder_D[0].rotation = [0, 0, 0]
dish_rack[0].position = [4.667631761928396, 2.373130972912891, 0.125]
dish_rack[0].rotation = [0, 0, 0]
storage_box_A[0].position = [0.525121625212108, 0.5934075214310386, 0.15]
storage_box_A[0].rotation = [0, 0, 0]
appliance_tower[0].position = [3.499435787559944, 0.8444482307937301, 0.9]
appliance_tower[0].rotation = [0, 0, 0]
sugar_packet_holder_E[0].position = [0.04537131956195106, 2.707215630709584, 0.12]
sugar_packet_holder_E[0].rotation = [0, 0, 0]
bar_stool_E[0].position = [2.437412529738597, 0.6896944466305882, 0.38]
bar_stool_E[0].rotation = [0, 0, 0]
sugar_packet_holder_F[0].position = [3.899063224409952, 2.0562712363046423, 0.12]
sugar_packet_holder_F[0].rotation = [0, 0, 0]
bar_stool_F[0].position = [2.745316106346847, 2.0206631555970214, 0.38]
bar_stool_F[0].rotation = [0, 0, 0]
storage_box_B[0].position = [6.771961071324428, 3.379428723756224, 0.15]
storage_box_B[0].rotation = [0, 0, 0]
side_chair_C[0].position = [6.017771541934472, 1.1141524440937922, 0.41]
side_chair_C[0].rotation = [0, 0, 0]
tall_storage_cabinet_B[0].position = [2.5191884193466625, 1.1145093079840773, 1.0]
tall_storage_cabinet_B[0].rotation = [0, 0, 0]
microwave_oven[0].position = [0.0371643943519776, 1.2996776303456796, 0.15]
microwave_oven[0].rotation = [0, 0, 0]
small_potted_plant[0].position = [5.058733612085987, 1.5926789206044494, 0.275]
small_potted_plant[0].rotation = [0, 0, 0]
bistro_table_A[0].position = [3.251423130536698, 3.8739117426510745, 0.375]
bistro_table_A[0].rotation = [0, 0, 0]
freestanding_plant_A[0].position = [5.942466157698069, 3.9471514162137793, 0.7]
freestanding_plant_A[0].rotation = [0, 0, 0]
bistro_table_B[0].position = [5.314477691256221, 1.1125169792198975, 0.375]
bistro_table_B[0].rotation = [0, 0, 0]
freestanding_plant_B[0].position = [1.5087226195603018, 3.131013806013225, 0.7]
freestanding_plant_B[0].rotation = [0, 0, 0]
bar_stool_A[0].position = [3.423382443616325, 3.4899009108612415, 0.38]
bar_stool_A[0].rotation = [0, 0, 0]
side_chair_A[0].position = [1.069643500386067, 0.3791600707391607, 0.41]
side_chair_A[0].rotation = [0, 0, 0]
pantry_lower_cabinets[0].position = [6.467067126562185, 1.8519240890427047, 0.45]
pantry_lower_cabinets[0].rotation = [0, 0, 0]
freestanding_plant_C[0].position = [3.9690974749564027, 1.620469749802561, 0.7]
freestanding_plant_C[0].rotation = [0, 0, 0]
bar_stool_B[0].position = [6.961335577930223, 2.1469703236490596, 0.38]
bar_stool_B[0].rotation = [0, 0, 0]
sugar_packet_holder_A[0].position = [2.7399418922207097, 1.1544357715292275, 0.12]
sugar_packet_holder_A[0].rotation = [0, 0, 0]
recycle_bin_set_A[0].position = [0.3675106715164439, 2.1351719703427823, 0.375]
recycle_bin_set_A[0].rotation = [0, 0, 0]
recycle_bin_set_B[0].position = [1.043402317726927, 1.9093213815414156, 0.375]
recycle_bin_set_B[0].rotation = [0, 0, 0]
bar_stool_C[0].position = [1.5265709883249796, 0.3797228238025613, 0.38]
bar_stool_C[0].rotation = [0, 0, 0]
sugar_packet_holder_B[0].position = [4.06864343656017, 1.7710001877429427, 0.12]
sugar_packet_holder_B[0].rotation = [0, 0, 0]
tall_storage_cabinet_A[0].position = [2.0360462010533227, 3.6573547365724157, 1.0]
tall_storage_cabinet_A[0].rotation = [0, 0, 0]
sugar_packet_holder_C[0].position = [0.20132356371310556, 2.847818619662601, 0.12]
sugar_packet_holder_C[0].rotation = [0, 0, 0]
bar_stool_D[0].position = [0.6807660719105226, 1.8532577749905743, 0.38]
bar_stool_D[0].rotation = [0, 0, 0]
bar_counter[0].position = [5.204700810497504, 1.529183814173554, 0.525]
bar_counter[0].rotation = [0, 0, 0]
napkin_dispenser[0].position = [6.413894659759753, 3.67195120193976, 0.075]
napkin_dispenser[0].rotation = [0, 0, 0]
side_chair_B[0].position = [3.2125663239741957, 0.964935121959633, 0.41]
side_chair_B[0].rotation = [0, 0, 0]
sugar_packet_holder_D[0].position = [1.2326161935657622, 0.6271030786373394, 0.12]
sugar_packet_holder_D[0].rotation = [0, 0, 0]
dish_rack[0].position = [4.667631761928396, 2.373130972912891, 0.125]
dish_rack[0].rotation = [0, 0, 0]
storage_box_A[0].position = [0.525121625212108, 0.5934075214310386, 0.15]
storage_box_A[0].rotation = [0, 0, 0]
appliance_tower[0].position = [3.499435787559944, 0.8444482307937301, 0.9]
appliance_tower[0].rotation = [0, 0, 0]
sugar_packet_holder_E[0].position = [0.04537131956195106, 2.707215630709584, 0.12]
sugar_packet_holder_E[0].rotation = [0, 0, 0]
bar_stool_E[0].position = [2.437412529738597, 0.6896944466305882, 0.38]
bar_stool_E[0].rotation = [0, 0, 0]
sugar_packet_holder_F[0].position = [3.899063224409952, 2.0562712363046423, 0.12]
sugar_packet_holder_F[0].rotation = [0, 0, 0]
bar_stool_F[0].position = [2.745316106346847, 2.0206631555970214, 0.38]
bar_stool_F[0].rotation = [0, 0, 0]
storage_box_B[0].position = [6.771961071324428, 3.379428723756224, 0.15]
storage_box_B[0].rotation = [0, 0, 0]
side_chair_C[0].position = [6.017771541934472, 1.1141524440937922, 0.41]
side_chair_C[0].rotation = [0, 0, 0]
tall_storage_cabinet_B[0].position = [2.5191884193466625, 1.1145093079840773, 1.0]
tall_storage_cabinet_B[0].rotation = [0, 0, 0]

solver.constraints = []

# Coordinates follow the supplied boundary, whose southwest corner is (0, 0).
# Keep the entrance strip x=1.08..3.08, y=3..4 clear. The tall furniture
# occupies the east side and northeast recess, away from the south windows.
def set_layout(asset_group, xyz, yaw):
    instance = asset_group[0]
    instance.position = list(xyz)
    instance.rotation = [0, 0, radians(yaw)]

    # Fixed references preserve the planned circulation and clearances.
    reference = AssetInstance(
        position=list(xyz),
        rotation=[0, 0, radians(yaw)]
    )
    solver.distance_constraint(instance, reference, 0, 0, weight=10)
    solver.align_with(instance, reference)


# Main floor furniture. The counter runs north-south against the east wall;
# its west side provides six evenly spaced customer seats.
floor_layout = [
    (pantry_lower_cabinets, (0.30, 1.80, 0.45), 0),
    (bar_counter, (6.675, 1.85, 0.525), 180),
    (bistro_table_A, (2.00, 0.90, 0.375), 0),
    (bistro_table_B, (3.90, 1.90, 0.375), 0),

    (side_chair_A, (1.15, 0.90, 0.41), 0),
    (side_chair_B, (2.85, 0.90, 0.41), 180),
    (side_chair_C, (3.90, 2.75, 0.41), -90),

    # o0027 (E) is strictly between o0010 (B) and o0006 (A).
    (bar_stool_B, (5.65, 0.50, 0.38), 0),
    (bar_stool_E, (5.65, 1.10, 0.38), 0),
    (bar_stool_A, (5.65, 1.70, 0.38), 0),
    (bar_stool_C, (5.65, 2.30, 0.38), 0),
    (bar_stool_D, (5.65, 2.90, 0.38), 0),
    (bar_stool_F, (5.65, 3.50, 0.38), 0),

    # Rotating these cabinets gives footprints of 0.80 by 0.55 m.
    (tall_storage_cabinet_A, (5.55, 4.725, 1.00), -90),
    (tall_storage_cabinet_B, (6.50, 4.725, 1.00), -90),
    (appliance_tower, (4.60, 3.75, 0.90), -90),

    (freestanding_plant_A, (0.30, 0.30, 0.70), 0),
    (freestanding_plant_B, (3.55, 3.70, 0.70), -90),
    (freestanding_plant_C, (6.70, 4.05, 0.70), 180),
    (recycle_bin_set_A, (0.20, 3.30, 0.375), 0),
    (recycle_bin_set_B, (0.70, 3.70, 0.375), -90),
]

for asset_group, xyz, yaw in floor_layout:
    set_layout(asset_group, xyz, yaw)

# Wall contacts are compatible with the anchored footprints and rotations.
solver.against_wall(pantry_lower_cabinets[0], walls[5])
solver.against_wall(bar_counter[0], walls[1])
solver.against_wall(tall_storage_cabinet_A[0], walls[2])
solver.against_wall(tall_storage_cabinet_B[0], walls[2])
solver.against_wall(appliance_tower[0], walls[4])
solver.against_wall(recycle_bin_set_A[0], walls[5])

# Explicit facing constraints make the seating semantics clear.
solver.point_towards(side_chair_A[0], bistro_table_A[0])
solver.point_towards(side_chair_B[0], bistro_table_A[0])
solver.point_towards(side_chair_C[0], bistro_table_B[0])

# Aim each stool straight across the counter rather than toward its midpoint.
for stool_group in (
    bar_stool_B, bar_stool_E, bar_stool_A,
    bar_stool_C, bar_stool_D, bar_stool_F
):
    stool_instance = stool_group[0]
    solver.point_towards(
        stool_instance,
        AssetInstance(position=[6.675, stool_instance.position[1], 0.38])
    )
    solver.align_with(stool_instance, bar_counter[0], angle=180)

# Equal adjacent distances plus the endpoint separation preserve the
# collinear B--E--A order and therefore the requested "between" relationship.
solver.distance_constraint(bar_stool_E[0], bar_stool_B[0], 0.60, 0.60, weight=10)
solver.distance_constraint(bar_stool_E[0], bar_stool_A[0], 0.60, 0.60, weight=10)
solver.distance_constraint(bar_stool_A[0], bar_stool_B[0], 1.20, 1.20, weight=10)

for first_group, second_group in (
    (bar_stool_C, bar_stool_A),
    (bar_stool_D, bar_stool_C),
    (bar_stool_F, bar_stool_D),
):
    solver.distance_constraint(first_group[0], second_group[0], 0.60, 0.60)

# Small objects sit on actual support surfaces, with disjoint footprints.
# Heights below are bounding-box center heights, not surface elevations.
supported_layout = [
    (microwave_oven, pantry_lower_cabinets, (0.30, 1.10, 1.05), 0),
    (dish_rack, pantry_lower_cabinets, (0.30, 2.50, 1.025), 0),

    (small_potted_plant, bistro_table_B, (4.10, 1.90, 1.025), 0),
    (sugar_packet_holder_A, bistro_table_A, (1.75, 0.65, 0.87), 0),
    (sugar_packet_holder_B, bistro_table_A, (1.75, 1.15, 0.87), 0),
    (napkin_dispenser, bistro_table_A, (2.20, 1.10, 0.825), 0),

    (sugar_packet_holder_C, bistro_table_B, (3.65, 1.65, 0.87), 0),
    (sugar_packet_holder_D, bistro_table_B, (3.65, 1.90, 0.87), 0),
    # o0028 is the sixth holder; o0004 is bistro_table_B.
    (sugar_packet_holder_F, bistro_table_B, (3.65, 2.15, 0.87), 0),

    (sugar_packet_holder_E, bar_counter, (6.65, 1.15, 1.17), 180),
    (storage_box_A, tall_storage_cabinet_A, (5.55, 4.725, 2.15), -90),
    (storage_box_B, tall_storage_cabinet_B, (6.50, 4.725, 2.15), -90),
]

for asset_group, support_group, xyz, yaw in supported_layout:
    # Apply the support relationship before the positional refinements.
    solver.on_top_of(asset_group[0], support_group[0])
    set_layout(asset_group, xyz, yaw)
    solver.align_with(asset_group[0], support_group[0])

solver.constraints = []
storage_box_B[0].position = [6.5, 4.724999904632568, 2.1500000953674316]
storage_box_B[0].rotation = [0, 0, -1.5707445685314119]
storage_box_B[0].optimize = 2
sugar_packet_holder_D[0].position = [3.6500000953674316, 1.899999976158142, 0.8700000047683716]
sugar_packet_holder_D[0].rotation = [0, 0, 0.03771272423943629]
sugar_packet_holder_D[0].optimize = 2
storage_box_A[0].position = [5.550000190734863, 4.724999904632568, 2.1500000953674316]
storage_box_A[0].rotation = [0, 0, -1.5707445685314119]
storage_box_A[0].optimize = 2
sugar_packet_holder_B[0].position = [1.75, 1.149999976158142, 0.8700000047683716]
sugar_packet_holder_B[0].rotation = [0, 0, 0.03457565229030294]
sugar_packet_holder_B[0].optimize = 2
side_chair_B[0].position = [2.8499999046325684, 0.8999999761581421, 0.4099999964237213]
side_chair_B[0].rotation = [0, 0, -3.1290262823329655]
side_chair_B[0].optimize = 2
small_potted_plant[0].position = [4.099999904632568, 1.899999976158142, 1.024999976158142]
small_potted_plant[0].rotation = [0, 0, 0.03771272423943629]
small_potted_plant[0].optimize = 2
microwave_oven[0].position = [0.30000001192092896, 1.100000023841858, 1.0499999523162842]
microwave_oven[0].rotation = [0, 0, -1.428585725684758e-05]
microwave_oven[0].optimize = 2
dish_rack[0].position = [0.30000001192092896, 2.5, 1.024999976158142]
dish_rack[0].rotation = [0, 0, -1.428585725684758e-05]
dish_rack[0].optimize = 2
tall_storage_cabinet_A[0].position = [5.550000190734863, 4.724998950958252, 1.0]
tall_storage_cabinet_A[0].rotation = [0, 0, -1.5708222448550313]
tall_storage_cabinet_A[0].optimize = 2
sugar_packet_holder_F[0].position = [3.6500000953674316, 2.1500000953674316, 0.8700000047683716]
sugar_packet_holder_F[0].rotation = [0, 0, 0.03771272423943629]
sugar_packet_holder_F[0].optimize = 2
bar_stool_E[0].position = [5.650000095367432, 1.100000023841858, 0.3799999952316284]
bar_stool_E[0].rotation = [0, 0, 0.0001472293113738757]
bar_stool_E[0].optimize = 2
sugar_packet_holder_A[0].position = [1.75, 0.6499999761581421, 0.8700000047683716]
sugar_packet_holder_A[0].rotation = [0, 0, 0.03457565229030294]
sugar_packet_holder_A[0].optimize = 2
bar_stool_B[0].position = [5.650000095367432, 0.5, 0.3799999952316284]
bar_stool_B[0].rotation = [0, 0, 0.0001472293113738757]
bar_stool_B[0].optimize = 2
freestanding_plant_A[0].position = [0.30000001192092896, 0.30000001192092896, 0.699999988079071]
freestanding_plant_A[0].rotation = [0, 0, 0.00942477746072377]
freestanding_plant_A[0].optimize = 2
bar_stool_F[0].position = [5.650000095367432, 3.5, 0.3799999952316284]
bar_stool_F[0].rotation = [0, 0, 0.0001457403047175875]
bar_stool_F[0].optimize = 2
sugar_packet_holder_C[0].position = [3.6500000953674316, 1.649999976158142, 0.8700000047683716]
sugar_packet_holder_C[0].rotation = [0, 0, 0.03771272423943629]
sugar_packet_holder_C[0].optimize = 2
side_chair_C[0].position = [3.9000000953674316, 2.75, 0.4099999964237213]
side_chair_C[0].rotation = [0, 0, -1.5582299555380688]
side_chair_C[0].optimize = 2
recycle_bin_set_A[0].position = [0.20001371204853058, 3.299999952316284, 0.375]
recycle_bin_set_A[0].rotation = [0, 0, -9.86054107154703e-06]
recycle_bin_set_A[0].optimize = 2
freestanding_plant_C[0].position = [6.699999809265137, 4.050000190734863, 0.699999988079071]
freestanding_plant_C[0].rotation = [0, 0, -3.1321678761290697]
freestanding_plant_C[0].optimize = 2
sugar_packet_holder_E[0].position = [6.650000095367432, 1.149999976158142, 1.1699999570846558]
sugar_packet_holder_E[0].rotation = [0, 0, -3.1414578471269383]
sugar_packet_holder_E[0].optimize = 2
freestanding_plant_B[0].position = [3.549999952316284, 3.700000047683716, 0.699999988079071]
freestanding_plant_B[0].rotation = [0, 0, -1.5613715493341729]
freestanding_plant_B[0].optimize = 2
bar_stool_A[0].position = [5.650000095367432, 1.7000000476837158, 0.3799999952316284]
bar_stool_A[0].rotation = [0, 0, 0.00012646936254871518]
bar_stool_A[0].optimize = 2
side_chair_A[0].position = [1.149999976158142, 0.8999999761581421, 0.4099999964237213]
side_chair_A[0].rotation = [0, 0, 0.01256637125682779]
side_chair_A[0].optimize = 2
bar_stool_C[0].position = [5.650000095367432, 2.299999952316284, 0.3799999952316284]
bar_stool_C[0].rotation = [0, 0, 0.0001472293113738757]
bar_stool_C[0].optimize = 2
recycle_bin_set_B[0].position = [0.699999988079071, 3.700000047683716, 0.375]
recycle_bin_set_B[0].rotation = [0, 0, -1.5613715493341729]
recycle_bin_set_B[0].optimize = 2
bar_stool_D[0].position = [5.650000095367432, 2.9000000953674316, 0.3799999952316284]
bar_stool_D[0].rotation = [0, 0, 0.0001472293113738757]
bar_stool_D[0].optimize = 2
appliance_tower[0].position = [4.599999904632568, 3.7500128746032715, 0.8999999761581421]
appliance_tower[0].rotation = [0, 0, -1.5708061652176033]
appliance_tower[0].optimize = 2
bistro_table_A[0].position = [2.0, 0.8999999761581421, 0.375]
bistro_table_A[0].rotation = [0, 0, 0.03455751882667646]
bistro_table_A[0].optimize = 2
tall_storage_cabinet_B[0].position = [6.5, 4.724998950958252, 1.0]
tall_storage_cabinet_B[0].rotation = [0, 0, -1.5708222448550313]
tall_storage_cabinet_B[0].optimize = 2
napkin_dispenser[0].position = [2.200000047683716, 1.100000023841858, 0.824999988079071]
napkin_dispenser[0].rotation = [0, 0, 0.03457565229030294]
napkin_dispenser[0].optimize = 2
pantry_lower_cabinets[0].position = [0.2999688386917114, 1.7999999523162842, 0.44999998807907104]
pantry_lower_cabinets[0].rotation = [0, 0, -2.1533784470448143e-05]
pantry_lower_cabinets[0].optimize = 2
bistro_table_B[0].position = [3.9000000953674316, 1.899999976158142, 0.375]
bistro_table_B[0].rotation = [0, 0, 0.03769911119841034]
bistro_table_B[0].optimize = 2
bar_counter[0].position = [6.675097465515137, 1.850000023841858, 0.5249999761581421]
bar_counter[0].rotation = [0, 0, -3.141555141717725]
bar_counter[0].optimize = 2

