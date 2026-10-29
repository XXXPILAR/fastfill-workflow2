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
    Wall(corner1=[11.77, 0.00, 0.00], corner2=[11.76, 0.34, 0.00]),
    Wall(corner1=[11.76, 0.34, 0.00], corner2=[11.22, 0.89, 0.00]),
    Wall(corner1=[11.22, 0.89, 0.00], corner2=[8.34, 3.77, 0.00]),
    Wall(corner1=[8.34, 3.77, 0.00], corner2=[4.22, 3.77, 0.00]),
    Wall(corner1=[4.22, 3.77, 0.00], corner2=[3.44, 3.77, 0.00]),
    Wall(corner1=[3.44, 3.77, 0.00], corner2=[0.55, 0.89, 0.00]),
    Wall(corner1=[0.55, 0.89, 0.00], corner2=[0.01, 0.34, 0.00]),
    Wall(corner1=[0.01, 0.34, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[11.77, 0.00, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
cabinet_A = Assets(description="cabinet", size=[0.60, 2.40, 0.90], placements=[AssetInstance() for _ in range(1)])
refrigerator = Assets(description="refrigerator", size=[0.72, 0.75, 1.85], placements=[AssetInstance() for _ in range(1)])
bottle_A = Assets(description="bottle", size=[0.08, 0.08, 0.30], placements=[AssetInstance() for _ in range(1)])
box = Assets(description="box", size=[0.22, 0.30, 0.20], placements=[AssetInstance() for _ in range(1)])
plate = Assets(description="plate", size=[0.27, 0.27, 0.03], placements=[AssetInstance() for _ in range(1)])
dishwasher = Assets(description="dishwasher", size=[0.60, 0.60, 0.85], placements=[AssetInstance() for _ in range(1)])
bottle_B = Assets(description="bottle", size=[0.07, 0.07, 0.28], placements=[AssetInstance() for _ in range(1)])
bottle_C = Assets(description="bottle", size=[0.09, 0.09, 0.32], placements=[AssetInstance() for _ in range(1)])
food = Assets(description="food", size=[0.12, 0.16, 0.07], placements=[AssetInstance() for _ in range(1)])
pan_A = Assets(description="pan", size=[0.48, 0.28, 0.08], placements=[AssetInstance() for _ in range(1)])
bottle_D = Assets(description="bottle", size=[0.07, 0.07, 0.24], placements=[AssetInstance() for _ in range(1)])
bottle_E = Assets(description="bottle", size=[0.09, 0.09, 0.30], placements=[AssetInstance() for _ in range(1)])
bottle_F = Assets(description="bottle", size=[0.07, 0.07, 0.22], placements=[AssetInstance() for _ in range(1)])
cabinet_B = Assets(description="cabinet", size=[0.60, 1.80, 0.90], placements=[AssetInstance() for _ in range(1)])
faucet = Assets(description="faucet", size=[0.25, 0.18, 0.38], placements=[AssetInstance() for _ in range(1)])
cup = Assets(description="cup", size=[0.09, 0.12, 0.10], placements=[AssetInstance() for _ in range(1)])
bottle_G = Assets(description="bottle", size=[0.08, 0.08, 0.29], placements=[AssetInstance() for _ in range(1)])
bottle_H = Assets(description="bottle", size=[0.07, 0.07, 0.26], placements=[AssetInstance() for _ in range(1)])
lamp = Assets(description="lamp", size=[0.30, 0.25, 0.35], placements=[AssetInstance() for _ in range(1)])
pan_B = Assets(description="pan", size=[0.42, 0.24, 0.07], placements=[AssetInstance() for _ in range(1)])

cabinet_A[0].instance_id = 'cabinet_A_0'
refrigerator[0].instance_id = 'refrigerator_0'
bottle_A[0].instance_id = 'bottle_A_0'
box[0].instance_id = 'box_0'
plate[0].instance_id = 'plate_0'
dishwasher[0].instance_id = 'dishwasher_0'
bottle_B[0].instance_id = 'bottle_B_0'
bottle_C[0].instance_id = 'bottle_C_0'
food[0].instance_id = 'food_0'
pan_A[0].instance_id = 'pan_A_0'
bottle_D[0].instance_id = 'bottle_D_0'
bottle_E[0].instance_id = 'bottle_E_0'
bottle_F[0].instance_id = 'bottle_F_0'
cabinet_B[0].instance_id = 'cabinet_B_0'
faucet[0].instance_id = 'faucet_0'
cup[0].instance_id = 'cup_0'
bottle_G[0].instance_id = 'bottle_G_0'
bottle_H[0].instance_id = 'bottle_H_0'
lamp[0].instance_id = 'lamp_0'
pan_B[0].instance_id = 'pan_B_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'
walls[8].instance_id = 'walls_8'

cabinet_A[0].position = [10.037083233390604, 1.1865723379695734, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
refrigerator[0].position = [4.335615066911296, 1.4279972426624008, 0.925]
refrigerator[0].rotation = [0, 0, 0]
bottle_A[0].position = [4.116599880197939, 2.765647754577023, 0.15]
bottle_A[0].rotation = [0, 0, 0]
box[0].position = [3.0388614503818445, 3.0275367873015937, 0.1]
box[0].rotation = [0, 0, 0]
plate[0].position = [2.723219257183625, 1.2971620108136914, 0.0125]
plate[0].rotation = [0, 0, 0]
dishwasher[0].position = [5.060385932152746, 3.0222950095570416, 0.425]
dishwasher[0].rotation = [0, 0, 0]
bottle_B[0].position = [5.390862103027122, 1.291929772587872, 0.14]
bottle_B[0].rotation = [0, 0, 0]
bottle_C[0].position = [3.093407650374594, 1.7526799834760107, 0.16]
bottle_C[0].rotation = [0, 0, 0]
food[0].position = [6.099917184284744, 3.26777058769486, 0.035]
food[0].rotation = [0, 0, 0]
pan_A[0].position = [7.13004766233451, 0.9907302801269936, 0.04]
pan_A[0].rotation = [0, 0, 0]
bottle_D[0].position = [7.61861015234377, 2.8707841402401972, 0.12]
bottle_D[0].rotation = [0, 0, 0]
bottle_E[0].position = [3.608371034592835, 3.069865055303367, 0.15]
bottle_E[0].rotation = [0, 0, 0]
bottle_F[0].position = [2.2950826090388974, 0.5612502907262378, 0.11]
bottle_F[0].rotation = [0, 0, 0]
cabinet_B[0].position = [6.657752834182372, 1.7670577499832318, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
faucet[0].position = [4.8799741772569645, 0.433301521087745, 0.19]
faucet[0].rotation = [0, 0, 0]
cup[0].position = [7.8691669310831625, 3.7643407327342837, 0.05]
cup[0].rotation = [0, 0, 0]
bottle_G[0].position = [3.793584763751886, 0.5558175580516332, 0.145]
bottle_G[0].rotation = [0, 0, 0]
bottle_H[0].position = [7.1890521942341925, 2.595102657075115, 0.13]
bottle_H[0].rotation = [0, 0, 0]
lamp[0].position = [4.085462570833645, 1.2342659992002467, 0.175]
lamp[0].rotation = [0, 0, 0]
pan_B[0].position = [7.2864105889390185, 2.2112769738941234, 0.035]
pan_B[0].rotation = [0, 0, 0]
cabinet_A[0].position = [10.037083233390604, 1.1865723379695734, 0.45]
cabinet_A[0].rotation = [0, 0, 0]
refrigerator[0].position = [4.335615066911296, 1.4279972426624008, 0.925]
refrigerator[0].rotation = [0, 0, 0]
bottle_A[0].position = [4.116599880197939, 2.765647754577023, 0.15]
bottle_A[0].rotation = [0, 0, 0]
box[0].position = [3.0388614503818445, 3.0275367873015937, 0.1]
box[0].rotation = [0, 0, 0]
plate[0].position = [2.723219257183625, 1.2971620108136914, 0.0125]
plate[0].rotation = [0, 0, 0]
dishwasher[0].position = [5.060385932152746, 3.0222950095570416, 0.425]
dishwasher[0].rotation = [0, 0, 0]
bottle_B[0].position = [5.390862103027122, 1.291929772587872, 0.14]
bottle_B[0].rotation = [0, 0, 0]
bottle_C[0].position = [3.093407650374594, 1.7526799834760107, 0.16]
bottle_C[0].rotation = [0, 0, 0]
food[0].position = [6.099917184284744, 3.26777058769486, 0.035]
food[0].rotation = [0, 0, 0]
pan_A[0].position = [7.13004766233451, 0.9907302801269936, 0.04]
pan_A[0].rotation = [0, 0, 0]
bottle_D[0].position = [7.61861015234377, 2.8707841402401972, 0.12]
bottle_D[0].rotation = [0, 0, 0]
bottle_E[0].position = [3.608371034592835, 3.069865055303367, 0.15]
bottle_E[0].rotation = [0, 0, 0]
bottle_F[0].position = [2.2950826090388974, 0.5612502907262378, 0.11]
bottle_F[0].rotation = [0, 0, 0]
cabinet_B[0].position = [6.657752834182372, 1.7670577499832318, 0.45]
cabinet_B[0].rotation = [0, 0, 0]
faucet[0].position = [4.8799741772569645, 0.433301521087745, 0.19]
faucet[0].rotation = [0, 0, 0]
cup[0].position = [7.8691669310831625, 3.7643407327342837, 0.05]
cup[0].rotation = [0, 0, 0]
bottle_G[0].position = [3.793584763751886, 0.5558175580516332, 0.145]
bottle_G[0].rotation = [0, 0, 0]
bottle_H[0].position = [7.1890521942341925, 2.595102657075115, 0.13]
bottle_H[0].rotation = [0, 0, 0]
lamp[0].position = [4.085462570833645, 1.2342659992002467, 0.175]
lamp[0].rotation = [0, 0, 0]
pan_B[0].position = [7.2864105889390185, 2.2112769738941234, 0.035]
pan_B[0].rotation = [0, 0, 0]

solver.constraints = []

# A straight kitchen run along the bottom wall leaves the door at x=1.14
# and the window near x=10.70 unobstructed. The central aisle and the
# windows on the other walls remain clear.
#
# Rotating the cabinets 90 degrees makes their long local-y dimension
# parallel to the wall, with their fronts facing into the room (+y).
floor_layout = [
    (cabinet_A,    4.00, 0.30, 90),
    (dishwasher,   5.55, 0.30, 90),
    (cabinet_B,    6.85, 0.30, 90),
    (refrigerator, 8.25, 0.36, 90),
]

for furnishing, px, py, yaw in floor_layout:
    furnishing[0].position = [px, py, furnishing.size[2] / 2]
    furnishing[0].rotation = [0, 0, radians(yaw)]

# Cabinet A occupies x=[2.80, 5.20]; the dishwasher occupies
# x=[5.25, 5.85]. Their bounding boxes therefore have a 0.05 m gap.
# Distance constraints measure centers, not the gap between their edges.
solver.against_wall(cabinet_A[0], walls[8])
solver.distance_constraint(
    cabinet_A[0], dishwasher[0],
    min_distance=1.50,
    max_distance=(1.70**2 + 0.025**2)**0.5,
    weight=10,
)

# Preserve the planned wall run and inward-facing orientation.
# Fixed references are constraint anchors, not additional scene assets.
for furnishing, px, py, yaw in floor_layout:
    solver.against_wall(furnishing[0], walls[8])
    solver.distance_constraint(
        furnishing[0],
        AssetInstance(position=[px, py, furnishing.size[2] / 2]),
        0, 0, weight=10,
    )
    solver.align_with(
        furnishing[0],
        AssetInstance(rotation=[0, 0, radians(yaw)]),
    )

# Countertop objects are spread over both cabinets, with separated
# footprints. Every object rests directly on its cabinet's 0.90 m top.
# The pans are rotated so their longer dimensions run across the depth
# of the counter; both fit within its 0.60 m depth.
counter_layout = [
    (bottle_A, cabinet_A, 2.98, 0.16, 90),
    (bottle_B, cabinet_A, 3.15, 0.16, 90),
    (bottle_C, cabinet_A, 3.32, 0.16, 90),
    (bottle_D, cabinet_A, 3.49, 0.16, 90),
    (bottle_E, cabinet_A, 2.98, 0.46, 90),
    (bottle_F, cabinet_A, 3.15, 0.46, 90),
    (bottle_G, cabinet_A, 3.32, 0.46, 90),
    (bottle_H, cabinet_A, 3.49, 0.46, 90),
    (box,      cabinet_A, 3.85, 0.18, 90),
    (plate,    cabinet_A, 4.25, 0.18, 90),
    (pan_A,    cabinet_A, 4.85, 0.30, 90),
    (faucet,   cabinet_B, 6.15, 0.16, 90),
    (cup,      cabinet_B, 6.45, 0.20, 90),
    (food,     cabinet_B, 6.75, 0.18, 90),
    (pan_B,    cabinet_B, 7.20, 0.30, 90),
    (lamp,     cabinet_B, 7.55, 0.30, 90),
]

for item, support, px, py, yaw in counter_layout:
    top_z = support[0].position[2] + support.size[2] / 2
    center_z = top_z + item.size[2] / 2
    item[0].position = [px, py, center_z]
    item[0].rotation = [0, 0, radians(yaw)]

    # Surface support takes priority; the position constraint preserves
    # the non-overlapping countertop arrangement.
    solver.on_top_of(item[0], support[0])
    solver.distance_constraint(
        item[0],
        AssetInstance(position=[px, py, center_z]),
        0, 0, weight=10,
    )
    solver.align_with(item[0], support[0], angle=0)

solver.constraints = []
bottle_A[0].position = [2.9800000190734863, 0.1599999964237213, 1.0499999523162842]
bottle_A[0].rotation = [0, 0, 1.571090732448319]
bottle_A[0].optimize = 2
plate[0].position = [4.25, 0.18000000715255737, 0.9149999618530273]
plate[0].rotation = [0, 0, 1.571090732448319]
plate[0].optimize = 2
bottle_C[0].position = [3.319999933242798, 0.1599999964237213, 1.059999942779541]
bottle_C[0].rotation = [0, 0, 1.571090732448319]
bottle_C[0].optimize = 2
bottle_F[0].position = [3.1500000953674316, 0.46000000834465027, 1.0099999904632568]
bottle_F[0].rotation = [0, 0, 1.571090732448319]
bottle_F[0].optimize = 2
dishwasher[0].position = [5.550000190734863, 0.29999440908432007, 0.42500001192092896]
dishwasher[0].rotation = [0, 0, 1.570799228087627]
dishwasher[0].optimize = 2
faucet[0].position = [6.150000095367432, 0.1599999964237213, 1.0899999141693115]
faucet[0].rotation = [0, 0, 1.5708875813142913]
faucet[0].optimize = 2
pan_B[0].position = [7.199999809265137, 0.30000001192092896, 0.9350000023841858]
pan_B[0].rotation = [0, 0, 1.5708875813142913]
pan_B[0].optimize = 2
bottle_B[0].position = [3.1500000953674316, 0.1599999964237213, 1.0399999618530273]
bottle_B[0].rotation = [0, 0, 1.571090732448319]
bottle_B[0].optimize = 2
pan_A[0].position = [4.849999904632568, 0.30000001192092896, 0.9399999976158142]
pan_A[0].rotation = [0, 0, 1.571090732448319]
pan_A[0].optimize = 2
cabinet_A[0].position = [4.0, 0.29997777938842773, 0.44999998807907104]
cabinet_A[0].rotation = [0, 0, 1.570806792542908]
cabinet_A[0].optimize = 2
cup[0].position = [6.449999809265137, 0.20000000298023224, 0.949999988079071]
cup[0].rotation = [0, 0, 1.5708875813142913]
cup[0].optimize = 2
refrigerator[0].position = [8.25, 0.360003262758255, 0.925000011920929]
refrigerator[0].rotation = [0, 0, 1.5707912915445439]
refrigerator[0].optimize = 2
bottle_H[0].position = [3.490000009536743, 0.46000000834465027, 1.0299999713897705]
bottle_H[0].rotation = [0, 0, 1.571090732448319]
bottle_H[0].optimize = 2
lamp[0].position = [7.550000190734863, 0.30000001192092896, 1.0749999284744263]
lamp[0].rotation = [0, 0, 1.5708875813142913]
lamp[0].optimize = 2
box[0].position = [3.8499999046325684, 0.18000000715255737, 1.0]
box[0].rotation = [0, 0, 1.571090732448319]
box[0].optimize = 2
bottle_E[0].position = [2.9800000190734863, 0.46000000834465027, 1.0499999523162842]
bottle_E[0].rotation = [0, 0, 1.571090732448319]
bottle_E[0].optimize = 2
food[0].position = [6.75, 0.18000000715255737, 0.9350000023841858]
food[0].rotation = [0, 0, 1.5708875813142913]
food[0].optimize = 2
bottle_D[0].position = [3.490000009536743, 0.1599999964237213, 1.0199999809265137]
bottle_D[0].rotation = [0, 0, 1.571090732448319]
bottle_D[0].optimize = 2
cabinet_B[0].position = [6.849999904632568, 0.3000331521034241, 0.44999998807907104]
cabinet_B[0].rotation = [0, 0, 1.5708253389398563]
cabinet_B[0].optimize = 2
bottle_G[0].position = [3.319999933242798, 0.46000000834465027, 1.0449999570846558]
bottle_G[0].rotation = [0, 0, 1.571090732448319]
bottle_G[0].optimize = 2

