from code.controllers.intervalcontroller import IntervalController

from code.constants.common import LAYER_FOREGROUND, LAYER_BACKGROUND

# The editor controller simply tracks a set of editor attributes,
# such as paint mode, current tile, etc.  It also houses a number
# of child object like "MouseData" to easily track the x/y of the
# mouse (e.g. EditorController.leftclick.x).
class EditorController:

    def __init__(self):

        # Paint mode (tiles, entities, whatever)
        self.brush = "tile"


        # Active tile
        self.tile = 1

        # Active entity (bad guy, player, gold, etc.)
        self.entity = 0


        # Looking at tiles?
        self.selecting_tile = False

        # Paint allowed?
        self.can_paint = True


        # Layer visibility
        self.layer_visibility = {
            LAYER_FOREGROUND: True,
            LAYER_BACKGROUND: False # Let's hide it by default.  Does this affect default view for editor UI?
        }

        # Active layer
        self.active_layer = LAYER_FOREGROUND


        # Zoom ratio
        self.zoom_controller = IntervalController(
            interval = 1.0,
            target = 1.0,
            speed_in = 0.01,
            speed_out = 0.01
        )


        # Render grid?
        self.show_grid = True


        # Render trigger borders?
        self.show_trigger_frames = True

        # Render trigger names
        self.show_trigger_names = True


        # Name of the last map we were on (in case we want to flip back)
        self.last_map_name = ""


        # Kind of hacking this in for now
        self.last_rk_tree = None
        self.last_rk_tree_row_index = 0


        # Camera data
        self.camera = CameraData()

        # Mouse data
        self.mouse = MouseData()

        # Randomizer data
        self.randomizer = RandomizerData()

        # Drag object data
        self.drag = DragData()

        # clipboard data
        self.clipboard = ClipboardData()


    # Basic processing
    def process(self):

        # Process zoom controller
        self.zoom_controller.process()



class CameraData():

    def __init__(self):

        # Position
        self.x = 0
        self.y = 0

        # Stash
        self.last_x = 0
        self.last_y = 0


# Data on the mouse
class MouseData():

    def __init__(self):

        # Position
        self.x = 0
        self.y = 0

        # Last known tile coordinates
        self.tx = 0
        self.ty = 0


        # Left-click data
        self.leftclick = MouseClickData()

        # Right click data
        self.rightclick = MouseClickData()



# Mouse click data (generic, applies to any button)
class MouseClickData:

    def __init__(self):

        # Position
        self.x = 0
        self.y = 0

        # Tile coordinates
        self.tx = 0
        self.ty = 0

        # Object we clicked on, perhaps
        self.object_reference = None


# Data for tile randomizer
class RandomizerData:

    def __init__(self):

        # Active?
        self.enabled = False

        # Base tile
        self.tile = 0

        # Range
        self.range = 0


# Keep track of any moveable object (map, entity, trigger, etc.)
class DragData:

    def __init__(self):

        # The type of object (as a string) we're holding
        self.object_type = ""

        # Reference to the object we're holding
        self.object_reference = None


# Various clipboard data (copy planes, etc.)
class ClipboardData:

    def __init__(self):

        # Copy a plane
        self.plane = None
