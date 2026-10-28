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
    Wall(corner1=[7.69, 7.86, 0.00], corner2=[8.96, 7.86, 0.00]),
    Wall(corner1=[8.96, 7.86, 0.00], corner2=[8.96, 8.85, 0.00]),
    Wall(corner1=[8.96, 8.85, 0.00], corner2=[6.30, 8.85, 0.00]),
    Wall(corner1=[6.30, 8.85, 0.00], corner2=[6.30, 7.62, 0.00]),
    Wall(corner1=[6.30, 7.62, 0.00], corner2=[0.00, 7.62, 0.00]),
    Wall(corner1=[0.00, 7.62, 0.00], corner2=[0.00, 1.51, 0.00]),
    Wall(corner1=[0.00, 1.51, 0.00], corner2=[5.40, 1.51, 0.00]),
    Wall(corner1=[5.40, 1.51, 0.00], corner2=[5.40, 1.26, 0.00]),
    Wall(corner1=[5.40, 1.26, 0.00], corner2=[3.52, 1.26, 0.00]),
    Wall(corner1=[3.52, 1.26, 0.00], corner2=[3.52, 0.00, 0.00]),
    Wall(corner1=[3.52, 0.00, 0.00], corner2=[7.69, 0.00, 0.00]),
    Wall(corner1=[7.69, 0.00, 0.00], corner2=[7.69, 0.03, 0.00]),
    Wall(corner1=[7.69, 0.03, 0.00], corner2=[8.36, 0.03, 0.00]),
    Wall(corner1=[8.36, 0.03, 0.00], corner2=[8.36, 1.34, 0.00]),
    Wall(corner1=[8.36, 1.34, 0.00], corner2=[7.69, 1.34, 0.00]),
    Wall(corner1=[7.69, 1.34, 0.00], corner2=[7.69, 1.51, 0.00]),
    Wall(corner1=[7.69, 1.51, 0.00], corner2=[10.89, 1.51, 0.00]),
    Wall(corner1=[10.89, 1.51, 0.00], corner2=[10.89, 4.94, 0.00]),
    Wall(corner1=[10.89, 4.94, 0.00], corner2=[7.69, 4.94, 0.00]),
    Wall(corner1=[7.69, 4.94, 0.00], corner2=[7.69, 7.86, 0.00])
]

# Existing assets placed in the scene:

# New assets to be placed
bar_chair_A = Assets(description="bar chair", size=[0.52, 0.48, 1.05], placements=[AssetInstance() for _ in range(1)])
carpet = Assets(description="carpet", size=[3.00, 4.00, 0.02], placements=[AssetInstance() for _ in range(1)])
potted_bonsai = Assets(description="potted bonsai", size=[0.36, 0.42, 0.58], placements=[AssetInstance() for _ in range(1)])
side_table_A = Assets(description="side table", size=[0.50, 0.60, 0.58], placements=[AssetInstance() for _ in range(1)])
wardrobe_A = Assets(description="wardrobe", size=[0.62, 1.80, 2.30], placements=[AssetInstance() for _ in range(1)])
side_table_B = Assets(description="side table", size=[0.48, 0.55, 0.56], placements=[AssetInstance() for _ in range(1)])
wine_cabinet = Assets(description="wine cabinet", size=[0.50, 1.20, 1.50], placements=[AssetInstance() for _ in range(1)])
bar_chair_B = Assets(description="bar chair", size=[0.52, 0.48, 1.05], placements=[AssetInstance() for _ in range(1)])
bookcase_A = Assets(description="bookcase", size=[0.35, 1.00, 2.10], placements=[AssetInstance() for _ in range(1)])
bookcase_B = Assets(description="bookcase", size=[0.35, 1.00, 2.10], placements=[AssetInstance() for _ in range(1)])
bar_chair_C = Assets(description="bar chair", size=[0.52, 0.48, 1.05], placements=[AssetInstance() for _ in range(1)])
sofa_A = Assets(description="sofa", size=[0.95, 2.30, 0.85], placements=[AssetInstance() for _ in range(1)])
bar = Assets(description="bar", size=[0.70, 2.40, 1.10], placements=[AssetInstance() for _ in range(1)])
coffee_table = Assets(description="coffee table", size=[0.70, 1.30, 0.42], placements=[AssetInstance() for _ in range(1)])
wardrobe_B = Assets(description="wardrobe", size=[0.62, 1.80, 2.30], placements=[AssetInstance() for _ in range(1)])
shoe_cabinet = Assets(description="shoe cabinet", size=[0.35, 1.20, 1.00], placements=[AssetInstance() for _ in range(1)])
ornaments = Assets(description="ornaments", size=[0.22, 0.32, 0.46], placements=[AssetInstance() for _ in range(1)])
sofa_B = Assets(description="sofa", size=[0.92, 2.10, 0.84], placements=[AssetInstance() for _ in range(1)])
dining_table_combination = Assets(description="dining table combination", size=[1.60, 2.40, 0.95], placements=[AssetInstance() for _ in range(1)])

bar_chair_A[0].instance_id = 'bar_chair_A_0'
carpet[0].instance_id = 'carpet_0'
potted_bonsai[0].instance_id = 'potted_bonsai_0'
side_table_A[0].instance_id = 'side_table_A_0'
wardrobe_A[0].instance_id = 'wardrobe_A_0'
side_table_B[0].instance_id = 'side_table_B_0'
wine_cabinet[0].instance_id = 'wine_cabinet_0'
bar_chair_B[0].instance_id = 'bar_chair_B_0'
bookcase_A[0].instance_id = 'bookcase_A_0'
bookcase_B[0].instance_id = 'bookcase_B_0'
bar_chair_C[0].instance_id = 'bar_chair_C_0'
sofa_A[0].instance_id = 'sofa_A_0'
bar[0].instance_id = 'bar_0'
coffee_table[0].instance_id = 'coffee_table_0'
wardrobe_B[0].instance_id = 'wardrobe_B_0'
shoe_cabinet[0].instance_id = 'shoe_cabinet_0'
ornaments[0].instance_id = 'ornaments_0'
sofa_B[0].instance_id = 'sofa_B_0'
dining_table_combination[0].instance_id = 'dining_table_combination_0'
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
walls[16].instance_id = 'walls_16'
walls[17].instance_id = 'walls_17'
walls[18].instance_id = 'walls_18'
walls[19].instance_id = 'walls_19'

bar_chair_A[0].position = [5.331927162857816, 0.4772652494354558, 0.525]
bar_chair_A[0].rotation = [0, 0, 0]
carpet[0].position = [7.705560472405495, 0.43128047462138425, 0.01]
carpet[0].rotation = [0, 0, 0]
potted_bonsai[0].position = [1.8835787715403849, 6.037790064887213, 0.29]
potted_bonsai[0].rotation = [0, 0, 0]
side_table_A[0].position = [6.454852139075439, 8.204550743230723, 0.29]
side_table_A[0].rotation = [0, 0, 0]
wardrobe_A[0].position = [2.7211194457060373, 4.7764169520078354, 1.15]
wardrobe_A[0].rotation = [0, 0, 0]
side_table_B[0].position = [0.9991320337358841, 5.800145997486491, 0.28]
side_table_B[0].rotation = [0, 0, 0]
wine_cabinet[0].position = [4.198647435799343, 6.9571871915737225, 0.75]
wine_cabinet[0].rotation = [0, 0, 0]
bar_chair_B[0].position = [7.730592199143046, 3.2425452098782053, 0.525]
bar_chair_B[0].rotation = [0, 0, 0]
bookcase_A[0].position = [1.7816265008486978, 1.542894541313338, 1.05]
bookcase_A[0].rotation = [0, 0, 0]
bookcase_B[0].position = [9.349231582168308, 4.166398770195124, 1.05]
bookcase_B[0].rotation = [0, 0, 0]
bar_chair_C[0].position = [0.4596847456773178, 6.5638673224532535, 0.525]
bar_chair_C[0].rotation = [0, 0, 0]
sofa_A[0].position = [2.0350171805156094, 3.118287079636351, 0.425]
sofa_A[0].rotation = [0, 0, 0]
bar[0].position = [0.29288787467418176, 3.9470663167604427, 0.55]
bar[0].rotation = [0, 0, 0]
coffee_table[0].position = [3.1603265080198617, 4.912450057234988, 0.21]
coffee_table[0].rotation = [0, 0, 0]
wardrobe_B[0].position = [4.571719514146294, 0.7069026650631716, 1.15]
wardrobe_B[0].rotation = [0, 0, 0]
shoe_cabinet[0].position = [7.251800409298964, 2.7436104894832045, 0.5]
shoe_cabinet[0].rotation = [0, 0, 0]
ornaments[0].position = [4.5624957150204075, 5.599122764459585, 0.23]
ornaments[0].rotation = [0, 0, 0]
sofa_B[0].position = [7.956780806127198, 0.5461782554536379, 0.42]
sofa_B[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [8.219214545614925, 2.6794502129616538, 0.475]
dining_table_combination[0].rotation = [0, 0, 0]
bar_chair_A[0].position = [5.331927162857816, 0.4772652494354558, 0.525]
bar_chair_A[0].rotation = [0, 0, 0]
carpet[0].position = [7.705560472405495, 0.43128047462138425, 0.01]
carpet[0].rotation = [0, 0, 0]
potted_bonsai[0].position = [1.8835787715403849, 6.037790064887213, 0.29]
potted_bonsai[0].rotation = [0, 0, 0]
side_table_A[0].position = [6.454852139075439, 8.204550743230723, 0.29]
side_table_A[0].rotation = [0, 0, 0]
wardrobe_A[0].position = [2.7211194457060373, 4.7764169520078354, 1.15]
wardrobe_A[0].rotation = [0, 0, 0]
side_table_B[0].position = [0.9991320337358841, 5.800145997486491, 0.28]
side_table_B[0].rotation = [0, 0, 0]
wine_cabinet[0].position = [4.198647435799343, 6.9571871915737225, 0.75]
wine_cabinet[0].rotation = [0, 0, 0]
bar_chair_B[0].position = [7.730592199143046, 3.2425452098782053, 0.525]
bar_chair_B[0].rotation = [0, 0, 0]
bookcase_A[0].position = [1.7816265008486978, 1.542894541313338, 1.05]
bookcase_A[0].rotation = [0, 0, 0]
bookcase_B[0].position = [9.349231582168308, 4.166398770195124, 1.05]
bookcase_B[0].rotation = [0, 0, 0]
bar_chair_C[0].position = [0.4596847456773178, 6.5638673224532535, 0.525]
bar_chair_C[0].rotation = [0, 0, 0]
sofa_A[0].position = [2.0350171805156094, 3.118287079636351, 0.425]
sofa_A[0].rotation = [0, 0, 0]
bar[0].position = [0.29288787467418176, 3.9470663167604427, 0.55]
bar[0].rotation = [0, 0, 0]
coffee_table[0].position = [3.1603265080198617, 4.912450057234988, 0.21]
coffee_table[0].rotation = [0, 0, 0]
wardrobe_B[0].position = [4.571719514146294, 0.7069026650631716, 1.15]
wardrobe_B[0].rotation = [0, 0, 0]
shoe_cabinet[0].position = [7.251800409298964, 2.7436104894832045, 0.5]
shoe_cabinet[0].rotation = [0, 0, 0]
ornaments[0].position = [4.5624957150204075, 5.599122764459585, 0.23]
ornaments[0].rotation = [0, 0, 0]
sofa_B[0].position = [7.956780806127198, 0.5461782554536379, 0.42]
sofa_B[0].rotation = [0, 0, 0]
dining_table_combination[0].position = [8.219214545614925, 2.6794502129616538, 0.475]
dining_table_combination[0].rotation = [0, 0, 0]

solver.constraints = []

# Fixed reference points preserve the intended zoning while allowing the solver
# a small amount of freedom to resolve minor physical-clearance issues.
def _place(asset_instance, position, angle_degrees, tolerance=0.12):
    asset_instance.position = position
    asset_instance.rotation = [0, 0, radians(angle_degrees)]

    position_anchor = AssetInstance(position=position)
    orientation_anchor = AssetInstance(
        position=position,
        rotation=[0, 0, radians(angle_degrees)]
    )
    solver.distance_constraint(
        asset_instance, position_anchor, 0.0, tolerance, weight=10
    )
    solver.align_with(asset_instance, orientation_anchor, angle=0)


# Layout positions. Grounded objects use half their bounding-box height as z.
# The center-left portion is a living area, the lower-center portion is dining,
# and the upper-right side of the main room contains the bar.
_place(bar_chair_A[0], [4.90, 4.50, 0.525], 180)
_place(carpet[0], [3.80, 4.55, 0.01], 90)
_place(potted_bonsai[0], [3.60, 5.55, 0.87], 0, tolerance=0.05)
_place(side_table_A[0], [3.60, 5.55, 0.29], 0)
_place(wardrobe_A[0], [1.20, 7.31, 1.15], 270)
_place(side_table_B[0], [6.65, 4.05, 0.28], 0)
_place(wine_cabinet[0], [7.44, 5.85, 0.75], 180)
_place(bar_chair_B[0], [5.85, 5.35, 0.525], 0)
_place(bookcase_A[0], [0.70, 1.685, 1.05], 90)
_place(bookcase_B[0], [1.85, 1.685, 1.05], 90)
_place(bar_chair_C[0], [1.20, 6.33, 0.525], 270)
_place(sofa_A[0], [2.65, 4.50, 0.425], 0)
_place(bar[0], [6.65, 5.70, 0.55], 0)
_place(coffee_table[0], [3.85, 4.50, 0.21], 0)
_place(wardrobe_B[0], [1.20, 5.35, 1.15], 270)
_place(shoe_cabinet[0], [0.175, 2.75, 0.50], 0)
_place(ornaments[0], [3.85, 4.50, 0.65], 0, tolerance=0.05)
_place(sofa_B[0], [4.40, 6.65, 0.42], 90)
_place(dining_table_combination[0], [6.45, 2.65, 0.475], 90)


# Keep wardrobe_A flush with the upper wall, as explicitly required.
# Its 90-degree footprint gives it a 0.62 m depth normal to this wall.
solver.against_wall(wardrobe_A[0], walls[4])

# The second wardrobe uses the same orientation, with bar_chair_C centered in
# the clear interval between the two wardrobes.
solver.align_with(wardrobe_B[0], wardrobe_A[0])
solver.distance_constraint(
    bar_chair_C[0], wardrobe_A[0], 0.85, 1.15, weight=10
)
solver.distance_constraint(
    bar_chair_C[0], wardrobe_B[0], 0.85, 1.15, weight=10
)
solver.align_with(bar_chair_C[0], wardrobe_A[0])

# sofa_A faces bar_chair_A across the coffee table and carpet.
solver.point_towards(sofa_A[0], bar_chair_A[0])
solver.point_towards(bar_chair_A[0], sofa_A[0])
solver.distance_constraint(
    sofa_A[0], bar_chair_A[0], 2.10, 2.45, weight=10
)

# Keep the coffee table centered between the primary sofa and bar chair.
solver.distance_constraint(
    coffee_table[0], sofa_A[0], 1.05, 1.35, weight=5
)
solver.distance_constraint(
    coffee_table[0], bar_chair_A[0], 0.85, 1.20, weight=5
)
solver.align_with(coffee_table[0], sofa_A[0])

# The carpet is aligned with the living group and centered beneath it.
solver.align_with(carpet[0], sofa_A[0])
solver.distance_constraint(
    carpet[0], coffee_table[0], 0.0, 0.20, weight=5
)

# side_table_A sits beside the living group. The bonsai is supported by it.
solver.distance_constraint(
    side_table_A[0], coffee_table[0], 0.90, 1.20, weight=5
)
solver.align_with(side_table_A[0], coffee_table[0])
solver.on_top_of(potted_bonsai[0], side_table_A[0])
solver.align_with(potted_bonsai[0], side_table_A[0])
solver.distance_constraint(
    potted_bonsai[0], side_table_A[0], 0.0, 0.08, weight=10
)

# The ornaments are centered on and supported by the coffee table.
solver.on_top_of(ornaments[0], coffee_table[0])
solver.align_with(ornaments[0], coffee_table[0])
solver.distance_constraint(
    ornaments[0], coffee_table[0], 0.0, 0.08, weight=10
)

# side_table_B is placed at the short end of the bar. The center-distance
# range accounts for both half-lengths and leaves no more than 0.20 m between
# the assets' bounding boxes.
solver.distance_constraint(
    bar[0], side_table_B[0], 1.50, 1.85, weight=10
)
solver.align_with(side_table_B[0], bar[0])

# bar_chair_B is placed at the accessible side of the bar and faces it.
solver.point_towards(bar_chair_B[0], bar[0])
solver.distance_constraint(
    bar_chair_B[0], bar[0], 0.65, 1.00, weight=10
)

# The wine cabinet occupies the short wall beside the bar without projecting
# into the doorway or the bar-chair circulation zone.
solver.against_wall(wine_cabinet[0], walls[19])
solver.align_with(wine_cabinet[0], bar[0], angle=180)
solver.distance_constraint(
    wine_cabinet[0], bar[0], 0.65, 1.10, weight=5
)

# Tall bookcases use the uninterrupted lower-left wall and remain away from
# the nearby doorway at (3.52, 0.62).
solver.against_wall(bookcase_A[0], walls[6])
solver.against_wall(bookcase_B[0], walls[6])
solver.align_with(bookcase_B[0], bookcase_A[0])
solver.distance_constraint(
    bookcase_A[0], bookcase_B[0], 1.05, 1.30, weight=5
)

# The shallow shoe cabinet is against the left wall, outside the bottom-door
# approach and clear of the living sofa.
solver.against_wall(shoe_cabinet[0], walls[5])
solver.align_with(shoe_cabinet[0], bookcase_A[0], angle=-90)
solver.distance_constraint(
    shoe_cabinet[0], bookcase_A[0], 1.70, 2.30, weight=3
)

# sofa_B faces the known fixed TV cabinet. A fixed point is used because the
# cabinet has no movable asset variable in the scene program.
tv_cabinet_reference = AssetInstance(position=[4.26, 7.39, 0.225])
solver.point_towards(sofa_B[0], tv_cabinet_reference)
solver.distance_constraint(
    sofa_B[0], tv_cabinet_reference, 0.65, 0.95, weight=10
)

# Keep the dining set in the lower-center bay, oriented across its wider
# dimension and clear of all bottom-door approach paths.
dining_reference = AssetInstance(
    position=[6.45, 2.65, 0.475],
    rotation=[0, 0, radians(90)]
)
solver.align_with(dining_table_combination[0], dining_reference)
solver.distance_constraint(
    dining_table_combination[0],
    AssetInstance(position=[6.45, 2.65, 0.475]),
    0.0,
    0.12,
    weight=10
)

solver.constraints = []
wardrobe_B[0].position = [1.2000000476837158, 5.349999904632568, 1.149999976158142]
wardrobe_B[0].rotation = [0, 0, -1.570796127863937]
wardrobe_B[0].optimize = 2
ornaments[0].position = [3.8499999046325684, 4.5, 0.6499999761581421]
ornaments[0].rotation = [0, 0, 0.028274317339659082]
ornaments[0].optimize = 2
shoe_cabinet[0].position = [0.17499402165412903, 2.950814723968506, 0.5]
shoe_cabinet[0].rotation = [0, 0, 3.191152686472002e-08]
shoe_cabinet[0].optimize = 2
bar_chair_A[0].position = [4.900000095367432, 4.5, 0.5249999761581421]
bar_chair_A[0].rotation = [0, 0, -3.1196015053037707]
bar_chair_A[0].optimize = 2
potted_bonsai[0].position = [3.5999999046325684, 5.550000190734863, 0.8700000047683716]
potted_bonsai[0].rotation = [0, 0, 0.02827430192173585]
potted_bonsai[0].optimize = 2
sofa_B[0].position = [4.400000095367432, 6.650000095367432, 0.41999998688697815]
sofa_B[0].rotation = [0, 0, 1.586504290712113]
sofa_B[0].optimize = 2
dining_table_combination[0].position = [6.449999809265137, 2.6500000953674316, 0.4749999940395355]
dining_table_combination[0].rotation = [0, 0, 1.586504290712113]
dining_table_combination[0].optimize = 2
side_table_B[0].position = [6.650000095367432, 4.050000190734863, 0.2800000011920929]
side_table_B[0].rotation = [0, 0, 0.028274344226881912]
side_table_B[0].optimize = 2
bar_chair_B[0].position = [5.849999904632568, 5.349999904632568, 0.5249999761581421]
bar_chair_B[0].rotation = [0, 0, 0.0157079639172164]
bar_chair_B[0].optimize = 2
wardrobe_A[0].position = [1.2000000476837158, 7.308000087738037, 1.149999976158142]
wardrobe_A[0].rotation = [0, 0, -1.5707963332368846]
wardrobe_A[0].optimize = 2
carpet[0].position = [3.799999952316284, 4.550000190734863, 0.009999999776482582]
carpet[0].rotation = [0, 0, 0.028259906491738086]
carpet[0].optimize = 2
bookcase_B[0].position = [1.850000023841858, 1.68399977684021, 1.0499999523162842]
bookcase_B[0].rotation = [0, 0, 1.5707963564144154]
bookcase_B[0].optimize = 2
bar_chair_C[0].position = [1.2000000476837158, 6.329999923706055, 0.5249999761581421]
bar_chair_C[0].rotation = [0, 0, -1.5707962245362388]
bar_chair_C[0].optimize = 2
side_table_A[0].position = [3.5999999046325684, 5.550000190734863, 0.28999999165534973]
side_table_A[0].rotation = [0, 0, 0.028274339191102206]
side_table_A[0].optimize = 2
wine_cabinet[0].position = [7.428735256195068, 5.849999904632568, 0.75]
wine_cabinet[0].rotation = [0, 0, -3.1415926127799008]
wine_cabinet[0].optimize = 2
sofa_A[0].position = [2.6500000953674316, 4.5, 0.42500001192092896]
sofa_A[0].rotation = [0, 0, 0.02827433441159227]
sofa_A[0].optimize = 2
coffee_table[0].position = [3.8499999046325684, 4.5, 0.20999999344348907]
coffee_table[0].rotation = [0, 0, 0.02827435796364279]
coffee_table[0].optimize = 2
bar[0].position = [6.650000095367432, 5.699999809265137, 0.550000011920929]
bar[0].rotation = [0, 0, 0.02827433441159227]
bar[0].optimize = 2
bookcase_A[0].position = [0.699999988079071, 1.6839998960494995, 1.0499999523162842]
bookcase_A[0].rotation = [0, 0, 1.5707963083072587]
bookcase_A[0].optimize = 2

