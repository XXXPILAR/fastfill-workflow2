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
    Wall(corner1=[7.83, 3.93, 0.00], corner2=[6.71, 3.93, 0.00]),
    Wall(corner1=[6.71, 3.93, 0.00], corner2=[6.71, 3.87, 0.00]),
    Wall(corner1=[6.71, 3.87, 0.00], corner2=[3.65, 3.87, 0.00]),
    Wall(corner1=[3.65, 3.87, 0.00], corner2=[3.65, 6.93, 0.00]),
    Wall(corner1=[3.65, 6.93, 0.00], corner2=[0.00, 6.93, 0.00]),
    Wall(corner1=[0.00, 6.93, 0.00], corner2=[0.00, 0.00, 0.00]),
    Wall(corner1=[0.00, 0.00, 0.00], corner2=[3.65, 0.00, 0.00]),
    Wall(corner1=[3.65, 0.00, 0.00], corner2=[3.65, 2.76, 0.00]),
    Wall(corner1=[3.65, 2.76, 0.00], corner2=[6.71, 2.76, 0.00]),
    Wall(corner1=[6.71, 2.76, 0.00], corner2=[6.71, 2.64, 0.00]),
    Wall(corner1=[6.71, 2.64, 0.00], corner2=[5.97, 2.64, 0.00]),
    Wall(corner1=[5.97, 2.64, 0.00], corner2=[5.95, 1.50, 0.00]),
    Wall(corner1=[5.95, 1.50, 0.00], corner2=[7.49, 1.50, 0.00]),
    Wall(corner1=[7.49, 1.50, 0.00], corner2=[7.49, 2.70, 0.00]),
    Wall(corner1=[7.49, 2.70, 0.00], corner2=[7.83, 2.70, 0.00]),
    Wall(corner1=[7.83, 2.70, 0.00], corner2=[7.83, 3.93, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bathroom_cabinet = Assets(description="bathroom cabinet", size=[0.35, 0.80, 1.00], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="coffee table", size=[0.60, 1.20, 0.42], placements=[AssetInstance() for _ in range(1)])
sideboard = Assets(description="sideboard", size=[0.45, 1.80, 0.80], placements=[AssetInstance() for _ in range(1)])
shoe_cabinet = Assets(description="shoe cabinet", size=[0.35, 1.00, 1.10], placements=[AssetInstance() for _ in range(1)])
sofa_A = Assets(description="sofa", size=[0.95, 2.20, 0.85], placements=[AssetInstance() for _ in range(1)])
side_table = Assets(description="side table", size=[0.50, 0.50, 0.55], placements=[AssetInstance() for _ in range(1)])
sofa_B = Assets(description="sofa", size=[0.90, 1.80, 0.85], placements=[AssetInstance() for _ in range(1)])
plants_A = Assets(description="plants", size=[0.45, 0.45, 1.20], placements=[AssetInstance() for _ in range(1)])
dining_table = Assets(description="dining table", size=[0.90, 1.80, 0.75], placements=[AssetInstance() for _ in range(1)])
tv_cabinet = Assets(description="tv cabinet", size=[0.40, 1.80, 0.55], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[2.00, 2.80, 0.02], placements=[AssetInstance() for _ in range(1)])
plants_B = Assets(description="plants", size=[0.40, 0.40, 1.10], placements=[AssetInstance() for _ in range(1)])
floor_standing_lamp = Assets(description="floor standing lamp", size=[0.45, 0.45, 1.70], placements=[AssetInstance() for _ in range(1)])
sofa_C = Assets(description="sofa", size=[0.95, 2.00, 0.85], placements=[AssetInstance() for _ in range(1)])
plants_C = Assets(description="plants", size=[0.40, 0.40, 1.00], placements=[AssetInstance() for _ in range(1)])

bathroom_cabinet[0].instance_id = 'bathroom_cabinet_0'
coffee_table[0].instance_id = 'coffee_table_0'
sideboard[0].instance_id = 'sideboard_0'
shoe_cabinet[0].instance_id = 'shoe_cabinet_0'
sofa_A[0].instance_id = 'sofa_A_0'
side_table[0].instance_id = 'side_table_0'
sofa_B[0].instance_id = 'sofa_B_0'
plants_A[0].instance_id = 'plants_A_0'
dining_table[0].instance_id = 'dining_table_0'
tv_cabinet[0].instance_id = 'tv_cabinet_0'
carpet[0].instance_id = 'carpet_0'
plants_B[0].instance_id = 'plants_B_0'
floor_standing_lamp[0].instance_id = 'floor_standing_lamp_0'
sofa_C[0].instance_id = 'sofa_C_0'
plants_C[0].instance_id = 'plants_C_0'
walls[0].instance_id = 'walls_0'
walls[1].instance_id = 'walls_1'
walls[2].instance_id = 'walls_2'
walls[3].instance_id = 'walls_3'
walls[4].instance_id = 'walls_4'
walls[5].instance_id = 'walls_5'
walls[6].instance_id = 'walls_6'
walls[7].instance_id = 'walls_7'
walls[8].instance_id = 'walls_8'
walls[9].instance_id = 'walls_9'
walls[10].instance_id = 'walls_10'
walls[11].instance_id = 'walls_11'
walls[12].instance_id = 'walls_12'
walls[13].instance_id = 'walls_13'
walls[14].instance_id = 'walls_14'
walls[15].instance_id = 'walls_15'

bathroom_cabinet[0].position = [3.0874317094880555, 0.9750269519457435, 0.5]
bathroom_cabinet[0].rotation = [0, 0, 0]
coffee_table[0].position = [6.792053084175425, 2.9827817489687742, 0.21]
coffee_table[0].rotation = [0, 0, 0]
sideboard[0].position = [4.90784005250024, 2.8803835637686253, 0.4]
sideboard[0].rotation = [0, 0, 0]
shoe_cabinet[0].position = [2.0469814934393122, 2.5693744398036524, 0.55]
shoe_cabinet[0].rotation = [0, 0, 0]
sofa_A[0].position = [0.36673701425925087, 6.655675010787872, 0.425]
sofa_A[0].rotation = [0, 0, 0]
side_table[0].position = [0.08610878125048489, 1.090653100650348, 0.275]
side_table[0].rotation = [0, 0, 0]
sofa_B[0].position = [3.337288468285721, 2.4650530761394287, 0.425]
sofa_B[0].rotation = [0, 0, 0]
plants_A[0].position = [3.3255150366942954, 1.5243942537891677, 0.6]
plants_A[0].rotation = [0, 0, 0]
dining_table[0].position = [2.4471277621215863, 0.015684613753429735, 0.375]
dining_table[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [2.076685849230503, 4.318576583105334, 0.275]
tv_cabinet[0].rotation = [0, 0, 0]
carpet[0].position = [3.2004130234528816, 1.479315071856105, 0.01]
carpet[0].rotation = [0, 0, 0]
plants_B[0].position = [6.0756677510695365, 2.5162991402586434, 0.55]
plants_B[0].rotation = [0, 0, 0]
floor_standing_lamp[0].position = [6.4739242221309174, 3.7962773260074, 0.85]
floor_standing_lamp[0].rotation = [0, 0, 0]
sofa_C[0].position = [5.2654532958779106, 3.768822589602236, 0.425]
sofa_C[0].rotation = [0, 0, 0]
plants_C[0].position = [2.4473396936210383, 4.416774370737305, 0.5]
plants_C[0].rotation = [0, 0, 0]
bathroom_cabinet[0].position = [3.0874317094880555, 0.9750269519457435, 0.5]
bathroom_cabinet[0].rotation = [0, 0, 0]
coffee_table[0].position = [6.792053084175425, 2.9827817489687742, 0.21]
coffee_table[0].rotation = [0, 0, 0]
sideboard[0].position = [4.90784005250024, 2.8803835637686253, 0.4]
sideboard[0].rotation = [0, 0, 0]
shoe_cabinet[0].position = [2.0469814934393122, 2.5693744398036524, 0.55]
shoe_cabinet[0].rotation = [0, 0, 0]
sofa_A[0].position = [0.36673701425925087, 6.655675010787872, 0.425]
sofa_A[0].rotation = [0, 0, 0]
side_table[0].position = [0.08610878125048489, 1.090653100650348, 0.275]
side_table[0].rotation = [0, 0, 0]
sofa_B[0].position = [3.337288468285721, 2.4650530761394287, 0.425]
sofa_B[0].rotation = [0, 0, 0]
plants_A[0].position = [3.3255150366942954, 1.5243942537891677, 0.6]
plants_A[0].rotation = [0, 0, 0]
dining_table[0].position = [2.4471277621215863, 0.015684613753429735, 0.375]
dining_table[0].rotation = [0, 0, 0]
tv_cabinet[0].position = [2.076685849230503, 4.318576583105334, 0.275]
tv_cabinet[0].rotation = [0, 0, 0]
carpet[0].position = [3.2004130234528816, 1.479315071856105, 0.01]
carpet[0].rotation = [0, 0, 0]
plants_B[0].position = [6.0756677510695365, 2.5162991402586434, 0.55]
plants_B[0].rotation = [0, 0, 0]
floor_standing_lamp[0].position = [6.4739242221309174, 3.7962773260074, 0.85]
floor_standing_lamp[0].rotation = [0, 0, 0]
sofa_C[0].position = [5.2654532958779106, 3.768822589602236, 0.425]
sofa_C[0].rotation = [0, 0, 0]
plants_C[0].position = [2.4473396936210383, 4.416774370737305, 0.5]
plants_C[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed references used to preserve the intended positions while allowing the
# solver to enforce the relational layout constraints below.
def pin_position(instance, position):
    instance.position = position
    solver.distance_constraint(
        instance,
        AssetInstance(position=position),
        min_distance=0,
        max_distance=0,
        weight=10,
    )


# Orientation references for wall-mounted and axis-aligned furniture.
facing_pos_x = AssetInstance(rotation=[0, 0, radians(0)])
facing_neg_x = AssetInstance(rotation=[0, 0, radians(180)])
facing_pos_y = AssetInstance(rotation=[0, 0, radians(90)])

# ---------------------------------------------------------------------------
# Initial placements
# ---------------------------------------------------------------------------

# Entry/dining area in the lower-left part of the main room. The dining table
# stops well short of both the bottom door and the wide door on the right wall.
pin_position(sideboard[0], [0.225, 1.30, 0.40])
sideboard[0].rotation = [0, 0, radians(0)]

pin_position(shoe_cabinet[0], [0.80, 0.175, 0.55])
shoe_cabinet[0].rotation = [0, 0, radians(90)]

pin_position(dining_table[0], [2.00, 1.25, 0.375])
dining_table[0].rotation = [0, 0, radians(0)]

# Main living group. The TV cabinet is centered between plants_A and plants_B
# along the west wall, as required.
pin_position(plants_A[0], [0.225, 2.95, 0.60])
plants_A[0].rotation = [0, 0, radians(0)]

pin_position(tv_cabinet[0], [0.20, 4.10, 0.275])
tv_cabinet[0].rotation = [0, 0, radians(0)]

pin_position(plants_B[0], [0.20, 5.25, 0.55])
plants_B[0].rotation = [0, 0, radians(0)]

# The rug defines the seating area. Its very small height permits the seating
# footprints to overlap it naturally without furniture intersecting each other.
pin_position(carpet[0], [1.75, 4.10, 0.01])
carpet[0].rotation = [0, 0, radians(0)]

pin_position(coffee_table[0], [1.75, 4.10, 0.23])
coffee_table[0].rotation = [0, 0, radians(0)]

# Three sofas form a U-shaped conversation group around the coffee table.
# sofa_C leaves roughly one metre of clear landing space inside the wide
# doorway at the north wall.
pin_position(sofa_A[0], [3.15, 4.10, 0.425])
sofa_A[0].rotation = [0, 0, radians(180)]

pin_position(sofa_B[0], [1.55, 2.65, 0.425])
sofa_B[0].rotation = [0, 0, radians(90)]

pin_position(sofa_C[0], [1.55, 5.40, 0.425])
sofa_C[0].rotation = [0, 0, radians(-90)]

# The side table and lamp occupy the northeast corner of the seating group,
# outside the wide doorway's principal approach.
pin_position(side_table[0], [2.90, 5.50, 0.275])
side_table[0].rotation = [0, 0, radians(0)]

pin_position(floor_standing_lamp[0], [3.40, 5.75, 0.85])
floor_standing_lamp[0].rotation = [0, 0, radians(180)]

# A third plant fills the protected corner to the right of the north doorway.
pin_position(plants_C[0], [3.40, 6.70, 0.50])
plants_C[0].rotation = [0, 0, radians(-90)]

# The bathroom cabinet fits inside the small lower-right alcove. It uses the
# alcove's left wall and remains clear of the doors at (7.03, 1.50) and
# (7.49, 2.07).
pin_position(bathroom_cabinet[0], [6.125, 2.10, 0.50])
bathroom_cabinet[0].rotation = [0, 0, radians(0)]

# ---------------------------------------------------------------------------
# Position-based semantic constraints
# ---------------------------------------------------------------------------

# Keep storage furniture and the TV composition against their intended walls.
solver.against_wall(sideboard[0], walls[5])
solver.against_wall(shoe_cabinet[0], walls[6])
solver.against_wall(plants_A[0], walls[5])
solver.against_wall(tv_cabinet[0], walls[5])
solver.against_wall(plants_B[0], walls[5])
solver.against_wall(plants_C[0], walls[4])
solver.against_wall(bathroom_cabinet[0], walls[11])

# Preserve the TV-between-plants composition. Equal center distances place one
# plant on either side, while their pinned positions determine the ordering.
solver.distance_constraint(
    plants_A[0], tv_cabinet[0],
    min_distance=1.15, max_distance=1.15, weight=10
)
solver.distance_constraint(
    plants_B[0], tv_cabinet[0],
    min_distance=1.15, max_distance=1.15, weight=10
)

# Keep all three sofas at useful conversational distances from the coffee table.
solver.distance_constraint(
    sofa_A[0], coffee_table[0],
    min_distance=1.30, max_distance=1.50, weight=10
)
solver.distance_constraint(
    sofa_B[0], coffee_table[0],
    min_distance=1.35, max_distance=1.55, weight=10
)
solver.distance_constraint(
    sofa_C[0], coffee_table[0],
    min_distance=1.20, max_distance=1.40, weight=10
)

# Maintain the useful accessory relationships without crowding the seating.
solver.distance_constraint(
    side_table[0], sofa_C[0],
    min_distance=1.25, max_distance=1.45, weight=1
)
solver.distance_constraint(
    floor_standing_lamp[0], side_table[0],
    min_distance=0.45, max_distance=0.65, weight=1
)
solver.distance_constraint(
    dining_table[0], sideboard[0],
    min_distance=1.70, max_distance=1.90, weight=1
)

# The coffee table is physically supported by the carpet rather than embedded
# in it; the initial z-coordinate already includes the carpet's 0.02 m height.
solver.on_top_of(coffee_table[0], carpet[0])

# ---------------------------------------------------------------------------
# Orientation-based semantic constraints
# ---------------------------------------------------------------------------

# Wall furniture faces into its respective room or alcove.
solver.align_with(sideboard[0], facing_pos_x)
solver.align_with(shoe_cabinet[0], facing_pos_y)
solver.align_with(tv_cabinet[0], facing_pos_x)
solver.align_with(bathroom_cabinet[0], facing_pos_x)

# The table remains parallel with the sideboard and the rug/coffee-table pair
# remains aligned with the TV wall.
solver.align_with(dining_table[0], sideboard[0])
solver.align_with(carpet[0], tv_cabinet[0])
solver.align_with(coffee_table[0], tv_cabinet[0])

# The seating and TV are oriented toward the center of the conversation group.
solver.point_towards(sofa_A[0], coffee_table[0])
solver.point_towards(sofa_B[0], coffee_table[0])
solver.point_towards(sofa_C[0], coffee_table[0])
solver.point_towards(tv_cabinet[0], coffee_table[0])

# Accessories and plants face generally toward the occupied parts of the room.
solver.point_towards(side_table[0], coffee_table[0])
solver.point_towards(floor_standing_lamp[0], coffee_table[0])
solver.point_towards(plants_A[0], coffee_table[0])
solver.point_towards(plants_B[0], coffee_table[0])
solver.point_towards(plants_C[0], coffee_table[0])

solver.constraints = []
sofa_C[0].position = [1.5499999523162842, 5.400000095367432, 0.42500001192092896]
sofa_C[0].rotation = [0, 0, -1.5550883628776802]
sofa_C[0].optimize = 2
carpet[0].position = [1.75, 4.099999904632568, 0.009999999776482582]
carpet[0].rotation = [0, 0, -0.9385282224848305]
carpet[0].optimize = 2
shoe_cabinet[0].position = [0.800000011920929, 0.1747961938381195, 0.550000011920929]
shoe_cabinet[0].rotation = [0, 0, 1.571048782659515]
shoe_cabinet[0].optimize = 2
bathroom_cabinet[0].position = [6.136453628540039, 2.1131601333618164, 0.5]
bathroom_cabinet[0].rotation = [0, 0, -0.02395364936846302]
bathroom_cabinet[0].optimize = 2
plants_B[0].position = [0.19974030554294586, 5.25, 0.550000011920929]
plants_B[0].rotation = [0, 0, -0.0003422850540504539]
plants_B[0].optimize = 2
plants_C[0].position = [3.4000000953674316, 6.727118968963623, 0.5]
plants_C[0].rotation = [0, 0, -1.570547885347352]
plants_C[0].optimize = 2
floor_standing_lamp[0].position = [3.3330135345458984, 5.75, 0.8500000238418579]
floor_standing_lamp[0].rotation = [0, 0, -2.469808323484757]
floor_standing_lamp[0].optimize = 2
sofa_B[0].position = [1.5499999523162842, 2.6500000953674316, 0.42500001192092896]
sofa_B[0].rotation = [0, 0, 1.5833626980517244]
sofa_B[0].optimize = 2
sideboard[0].position = [0.9087386131286621, 1.2999999523162842, 0.4000000059604645]
sideboard[0].rotation = [0, 0, 1.1232945950212356]
sideboard[0].optimize = 2
coffee_table[0].position = [1.75, 4.099999904632568, 0.22999998927116394]
coffee_table[0].rotation = [0, 0, -0.9358324716494747]
coffee_table[0].optimize = 2
sofa_A[0].position = [3.1500000953674316, 4.099999904632568, 0.42500001192092896]
sofa_A[0].rotation = [0, 0, -3.1290262823329655]
sofa_A[0].optimize = 2
side_table[0].position = [2.9000000953674316, 5.5, 0.2750000059604645]
side_table[0].rotation = [0, 0, -1.0767018319675634]
side_table[0].optimize = 2
tv_cabinet[0].position = [0.8537821173667908, 4.099999904632568, 0.2750000059604645]
tv_cabinet[0].rotation = [0, 0, -0.9651574270481945]
tv_cabinet[0].optimize = 2
plants_A[0].position = [0.30031487345695496, 2.932584524154663, 0.6000000238418579]
plants_A[0].rotation = [0, 0, 1.1222536923091706]
plants_A[0].optimize = 2
dining_table[0].position = [2.0, 1.25, 0.375]
dining_table[0].rotation = [0, 0, 1.1203259068446052]
dining_table[0].optimize = 2

