import os
import pygame

from code.tools.xml import XMLParser, XMLNode

from code.utils.common import log, log2, xml_encode, xml_decode, ensure_path_exists, coalesce

from pygame.locals import *

from code.constants.common import PAD_AXIS, PAD_HAT, PAD_BUTTON, INPUT_MOVE_LEFT, INPUT_MOVE_RIGHT, INPUT_MOVE_UP, INPUT_MOVE_DOWN, INPUT_DIG_LEFT, INPUT_DIG_RIGHT, INPUT_DIG_FORWARD, INPUT_BOMB, INPUT_SUICIDE, INPUT_ACTIVATE_SKILL_1, INPUT_ACTIVATE_SKILL_2, INPUT_ACTION, INPUT_SELECTION_ACTIVATE, INPUT_SELECTION_UP, INPUT_SELECTION_DOWN, INPUT_SELECTION_LEFT, INPUT_SELECTION_RIGHT, INPUT_SELECTION_HOME, INPUT_SELECTION_END, INPUT_SELECTION_PAGEUP, INPUT_SELECTION_PAGEDOWN, INPUT_NET_CHAT, INPUT_MINIMAP
from code.constants.paths import CONFIG_PATH # The only path we need here

from code.constants.common import INPUT_DEBUG

PYGAME_EVENT_TRANSLATIONS = {
    PAD_AXIS: JOYAXISMOTION,
    PAD_HAT: JOYHATMOTION,
    PAD_BUTTON: JOYBUTTONDOWN
}

class InputController:

    def __init__(self):

        # Keep a reference to the active joystick, if any...
        self.joystick = None


        # Track keyboard input settings
        self.keyboard_settings = self.generate_default_keyboard_settings()

        # Track joystick / gamepad settings
        self.gamepad_settings_by_device_name = {}

        # Convenient reference to current device
        self.active_gamepad_settings = None


        # Track system input
        self.system_input = {}

        # We can lock system input access (essentially "erasing" tracked input while still preserving it for subsequent use)
        self.system_input_lock_count = 0


        # Track gameplay input
        self.gameplay_input = []

        # We can lock gameplay input as well
        self.gameplay_input_lock_count = 0


        # Track reference to keypresses
        self.keypresses = []


        # Track which device the player most recently used ("keyboard" or "gamepad")
        self.last_used_device = "keyboard"



        # Load input settings
        self.load()


    # Create default keyboard settings (for first game load or resettings to defaults)
    def generate_default_keyboard_settings(self):

        return {
            "left": K_LEFT,
            "right": K_RIGHT,
            "up": K_UP,
            "down": K_DOWN,
            "dig-left": K_z,
            "dig-right": K_v,
            "dig-forward": K_SPACE,
            "bomb": K_b,
            "suicide": K_k,
            "interact": K_RETURN,
            "minimap": K_TAB,
            "net-chat": K_TAB,
            "skill1": K_1,
            "skill2": K_2,
            "home": K_HOME,
            "end": K_END,
            "page-up": K_PAGEUP,
            "page-down": K_PAGEDOWN,
            "menu-left": K_LEFT,
            "menu-right": K_RIGHT,
            "menu-up": K_UP,
            "menu-down": K_DOWN,
            "escape": K_ESCAPE,
            "enter": K_RETURN,
            "enter2": K_KP_ENTER,
            "debug": K_BACKQUOTE    # Keyboard only.  Debug use only.
        }


    # Create default gamepad settings (for first device load or resetting to defaults)
    def generate_default_gamepad_settings(self):

        return {

            "menu-left": {
                "type": PAD_AXIS,
                "index": 0,
                "direction-x": -1, # for axis/hat; which side is the joystick/hat moving?  (in this case the -x is irrelevant)
                "direction-y": 0 # used only for pov hats
            },

            "menu-right": {
                "type": PAD_AXIS,
                "index": 0,
                "direction-x": 1,
                "direction-y": 0
            },

            "menu-up": {
                "type": PAD_AXIS,
                "index": 1,
                "direction-x": -1, # for axis/hat; which side is the joystick/hat moving?  (in this case the -x is irrelevant)
                "direction-y": 0 # used only for pov hats
            },

            "menu-down": {
                "type": PAD_AXIS,
                "index": 1,
                "direction-x": 1,
                "direction-y": 0
            },

            "enter": {
                "type": PAD_BUTTON,
                "index": 0,
                "direction-x": 0,
                "direction-y": 0
            },

            # Let's note that we don't define an "enter2" control for gamepads.

            "escape": {
                "type": PAD_BUTTON,
                "index": 1,
                "direction-x": 0,
                "direction-y": 0
            },

            "page-up": {
                "type": PAD_AXIS,
                "index": 0,
                "direction-x": 1,
                "direction-y": 0
            },

            "page-down": {
                "type": PAD_AXIS,
                "index": 0,
                "direction-x": 1,
                "direction-y": 0
            },

            "left": {
                "type": PAD_AXIS,
                "index": 0,
                "direction-x": -1,
                "direction-y": 0
            },

            "right": {
                "type": PAD_AXIS,
                "index": 0,
                "direction-x": 1,
                "direction-y": 0
            },

            "up": {
                "type": PAD_AXIS,
                "index": 1,
                "direction-x": -1,
                "direction-y": 0
            },

            "down": {
                "type": PAD_AXIS,
                "index": 1,
                "direction-x": 1,
                "direction-y": 0
            },

            "dig-left": {
                "type": PAD_BUTTON,
                "index": 2,
                "direction-x": -1,
                "direction-y": -1
            },

            "dig-right": {
                "type": PAD_BUTTON,
                "index": 3,
                "direction-x": -1,
                "direction-y": -1
            },

            "dig-forward": {
                "type": PAD_BUTTON,
                "index": 0,
                "direction-x": -1,
                "direction-y": -1
            },

            "skill1": {
                "type": PAD_BUTTON,
                "index": 4,
                "direction-x": -1,
                "direction-y": -1
            },

            "skill2": {
                "type": PAD_BUTTON,
                "index": 5,
                "direction-x": -1,
                "direction-y": -1
            },

            "bomb": {
                "type": PAD_BUTTON,
                "index": 1,
                "direction-x": -1,
                "direction-y": -1
            },

            "suicide": {
                "type": PAD_BUTTON,
                "index": 7,
                "direction-x": -1,
                "direction-y": -1
            },

            "interact": {
                "type": PAD_BUTTON,
                "index": 0,
                "direction-x": -1,
                "direction-y": -1
            },

            "minimap": {
                "type": PAD_BUTTON,
                "index": 8,
                "direction-x": -1,
                "direction-y": -1
            }

        }


    # Reset keyboard controls to defaults
    def reset_keyboard_controls(self):

        # Track keyboard input settings
        self.keyboard_settings = self.generate_default_keyboard_settings()


    # Reset controls for the active gamepad to defaults
    def reset_active_gamepad_controls(self):

        # Get the active device's name
        device_name = self.get_active_device_name()

        # Reset gamepad controls for that device
        self.gamepad_settings_by_device_name[device_name] = self.generate_default_gamepad_settings()

        # (?)
        self.active_gamepad_settings = self.generate_default_gamepad_settings()


    # Save keyboard controls and controls for all joysticks known to have played this game
    def save(self):

        # Create a base node for all devices, keyboard included
        devices = XMLNode("devices")


        # Start a node for the keyboard controls
        keyboard = devices.add_node(
            XMLNode("keyboard")
        )

        # Add each keyboard control
        for key in self.keyboard_settings:

            # Add a node for this key
            control = keyboard.add_node(
                XMLNode("control").set_attributes({
                    "action": xml_encode(key),
                    "keycode": xml_encode( "%d" % self.keyboard_settings[key] )
                })
            )


        # Read in (as a node) the historical record of gamepad devices
        gamepads = self.get_all_gamepad_configurations_as_node()


        # If we have an active device attached, then we'll update its data to bring it up-to-date...
        device_name = self.get_active_device_name()

        # Found one?
        if (device_name != ""):

            # Remove any node that had data for this gamepad.
            # Does nothing if such a node does not exist...
            gamepads.remove_node_by_id(device_name)

            # Now add a node for this gamepad
            gamepad = gamepads.add_node(
                XMLNode("gamepad").set_attributes({
                    "id": xml_encode(device_name)
                })
            )

            # Save gamepad controls
            for key in self.gamepad_settings_by_device_name[device_name]:

                gamepad.add_node(
                    XMLNode("control").set_attributes({
                        "control": xml_encode(key),
                        "type": xml_encode( "%d" % self.gamepad_settings_by_device_name[device_name][key]["type"] ),
                        "index": xml_encode( "%d" % self.gamepad_settings_by_device_name[device_name][key]["index"] ),
                        "direction-x": xml_encode( "%d" % self.gamepad_settings_by_device_name[device_name][key]["direction-x"] ),
                        "direction-y": xml_encode( "%d" % self.gamepad_settings_by_device_name[device_name][key]["direction-y"] )
                    })
                )


        # Add the gamepads node (updated or not) to the devices node
        devices.add_node(
            gamepads
        )


        # Before saving, let's make sure the path exists
        if (not os.path.exists("user")):

            # Need this directory!
            os.mkdir("user")


        # Write to file
        f = open( os.path.join("user", "controls.xml"), "w" )

        # Serialize
        f.write( devices.compile_xml_string() )

        # Done!
        f.close()


    # Load in controls for the keyboard and the active gamepad (if/a)
    def load(self):

        # Validate
        if ( os.path.exists( os.path.join("user", "controls.xml") ) ):

            # Prepare to read
            f = open( os.path.join("user", "controls.xml"), "r" )

            # Parse xml
            devices = XMLParser().create_node_from_xml( f.read() ).get_first_node_by_tag("devices")

            # Done parsing
            f.close()


            # Validate that we found devices node
            if (devices):

                # Find keyboard data
                keyboard = devices.get_first_node_by_tag("keyboard")

                # Validate keyboard node
                if (keyboard):

                    # Loop each control
                    for control in keyboard.get_nodes_by_tag("control"):

                        # Grab params
                        (index, action) = (
                            xml_decode( control.get_attribute("keycode") ),
                            xml_decode( control.get_attribute("action") )
                        )

                        # Sanity
                        if (action in self.keyboard_settings):

                            self.keyboard_settings[action] = int(index)


            # Check to see if we have an active device
            device_name = self.get_active_device_name()

            # Validate
            if (device_name != ""):

                # Find any controls for that gamepad
                gamepad = devices.find_node_by_id(device_name)

                # Validate gamepad node
                if (gamepad):

                    # Loop each gamepad control
                    for control in gamepad.get_nodes_by_tag("control"):

                        # Read params
                        (action, control_type, control_index, direction_x, direction_y) = (
                            xml_decode( control.get_attribute("control") ),
                            xml_decode( control.get_attribute("type") ),
                            xml_decode( control.get_attribute("index") ),
                            xml_decode( control.get_attribute("direction-x") ),
                            xml_decode( control.get_attribute("direction-y") )
                        )

                        # Sanity
                        if (action in self.gamepad_settings_by_device_name[device_name]):

                            self.gamepad_settings_by_device_name[device_name][action] = {
                                "type": int(control_type),
                                "index": int(control_index),
                                "direction-x": int(direction_x),
                                "direction-y": int(direction_y)
                            }


    # Read in any known joystick control configuration from the settings file
    def get_all_gamepad_configurations_as_node(self):

        # Validate path to controls exists
        if ( os.path.exists( os.path.join("user", "controls.xml") ) ):

            # Prepare to read
            f = open( os.path.join("user", "controls.xml"), "r" )

            # Parse all data
            devices = XMLParser().create_node_from_xml( f.read() ).get_first_node_by_tag("devices")

            # Done reading
            f.close()


            # Return the gamepads node...
            return coalesce(
                devices.get_first_node_by_tag("gamepads"),
                XMLNode("gamepads")                         # Default to an empty node if we need to...
            )

        # If no controls have ever been saved, then we have no gamepad history to consider...
        else:
            return XMLNode("gamepads")


    # Update a given keyboard control to a given keycode
    def update_keyboard_setting(self, key, value):

        # Validate
        if (key in self.keyboard_settings):

            # Update
            self.keyboard_settings[key] = value

        self.save()


    # Get the "readable" title of a key setting (e.g. K_a -> "A", K_HOME -> "Home")
    def fetch_keyboard_translation(self, key):

        # Validate
        if (key in self.keyboard_settings):

            return pygame.key.name( self.keyboard_settings[key] )

        # Fallback
        else:

            return "---"


    def query_available_device_names(self):

        # Re-initialize joystick input to check for new devices added after the application launch
        pygame.joystick.init()

        # Track results
        device_names = []

        # Enumerate joysticks
        for i in range(0, pygame.joystick.get_count()):

            device_names.append(
                pygame.joystick.Joystick(i).get_name()
            )

        return device_names


    # Attempt to select an input device by name
    def select_device_by_name(self, device_name):

        # Loop through devices
        for i in range(0, pygame.joystick.get_count()):

            # Is this the one?
            if ( pygame.joystick.Joystick(i).get_name() == device_name ):

                # Initialize the joystick
                self.joystick = pygame.joystick.Joystick(i)
                self.joystick.init()

                # Set up default control layout (this will probably be quite poorly guessed)
                self.gamepad_settings_by_device_name[device_name] = self.generate_default_gamepad_settings()

                # Reload control configuration settings in an attempt to recall data for this device
                self.load()

                # Keep a convenient reference to the "active" device settings...
                self.active_gamepad_settings = self.gamepad_settings_by_device_name[device_name]


                # Sanity
                ensure_path_exists( os.path.join(CONFIG_PATH, "gamepads") )


                # Save this joystick as the most recent
                f = open( os.path.join(CONFIG_PATH, "gamepads", "recent.xml"), "w" )
                f.write( "<xml><device id = 'recent' name = '%s' /></xml>" % xml_encode(device_name) )
                f.close()

                return True


        return False


    # Get the active device's name, if we have one
    def get_active_device_name(self):

        # Do we have a joystick set up?
        if (self.joystick):

            # Return the active device's name
            return self.joystick.get_name()

        # If not, return empty string
        else:
            return ""


    # Retrieve the name of the first input device available on the system.
    # We'll default to this if we don't find a "last used" device (or if we don't
    # find the "last used" device at runtime).
    def get_first_available_device_name(self):

        # Do we have any device available?
        if ( pygame.joystick.get_count() > 0 ):

            # Return the first in the list
            return pygame.joystick.Joystick(0).get_name()

        # Nope, too bad...
        else:

            return ""


    # Retrieve the name of the last-used input device
    def get_last_used_device_name(self):

        # Path to the file that holds this data
        path = os.path.join(CONFIG_PATH, "gamepads", "recent.xml")

        # Validate
        if ( os.path.exists(path) ):

            # Read XML
            f = open(path, "r")
            xml = f.read()
            f.close()

            # Read node
            node = XMLParser().create_node_from_xml(xml).find_node_by_id("recent")

            # Validate
            if (node):

                # Return the value
                return xml_decode( "%s" % node.get_attribute("name") )

        # Either we have never used a device, or we can't find the record properly
        return ""


    def update_gamepad_setting(self, key, event):

        log2( "Update gamepad setting:  key, event = ", (key, event) )

        # Make sure we have a joystick set up
        if (self.joystick):

            # Grab device name
            device_name = self.joystick.get_name()

            # Validate
            if (key in self.gamepad_settings_by_device_name[device_name]):

                # Axis?
                if (event.type == JOYAXISMOTION):

                    self.gamepad_settings_by_device_name[device_name][key] = {
                        "type": PAD_AXIS,
                        "index": event.axis,
                        "direction-x": event.value,
                        "direction-y": 0
                    }

                # Hat?
                elif (event.type == JOYHATMOTION):

                    self.gamepad_settings_by_device_name[device_name][key] = {
                        "type": PAD_HAT,
                        "index": event.hat,
                        "direction-x": event.value[0],
                        "direction-y": event.value[1]
                    }

                # Button?
                elif (event.type == JOYBUTTONDOWN):

                    self.gamepad_settings_by_device_name[device_name][key] = {
                        "type": PAD_BUTTON,
                        "index": event.button,
                        "direction-x": 0,
                        "direction-y": 0
                    }

        self.save()


    # Get the "readable" title of a key setting (e.g. K_a -> "A", K_HOME -> "Home")
    def fetch_gamepad_translation(self, key):

        # Validate that we have a joystick
        if (self.joystick):

            # Fetch device name
            device_name = self.joystick.get_name()

            # General validation
            if (key in self.gamepad_settings_by_device_name[device_name]):

                # Default return value
                output = "Unknown Control"

                # Convenience
                control_params = self.gamepad_settings_by_device_name[device_name][key]


                # Button?  Easy...
                if (control_params["type"] == PAD_BUTTON):

                    output = "Button %d" % (control_params["index"] + 1)

                # Axis?  Is it positive or negative?
                elif (control_params["type"] == PAD_AXIS):

                    if (control_params["direction-x"] < 0):

                        output = "Analog %d (-)" % control_params["index"]

                    else:

                        output = "Analog %d (+)" % control_params["index"]

                # POV Hat?
                elif (control_params["type"] == PAD_HAT):

                    # Convenience
                    (x, y) = (control_params["direction-x"], control_params["direction-y"])

                    if ( (x, y) == (0, -1) ):

                        output = "Hat %d Up" % control_params["index"]

                    elif ( (x, y) == (1, 0) ):

                        output = "Hat %d Right" % control_params["index"]

                    elif ( (x, y) == (0, 1) ):

                        output = "Hat %d Down" % control_params["index"]

                    elif ( (x, y) == (-1, 0) ):

                        output = "Hat %d Left" % control_params["index"]

                    else:

                        output = "Hat %d Diagonal" % control_params["index"] # **Supported?

                return output

            # Failed general validation, unknown key
            else:
                return "---"

        # No joystick available (n/a)
        else:
            return "n/a"


    def get_empty_system_input(self):

        # Return a valid system input container with no input tracked
        return {
            "key-events": [],
            "key-buffer": "",
            "keydown-keycodes": [],
            "gamepad-events": []
        }


    def poll_and_update_system_input(self, events, keypresses):

        # Track results; defaulta to empty input (naturally)
        results = self.get_empty_system_input()


        # Track keypress data
        self.keypresses = keypresses


        # Which keys count toward the raw key buffer (text input)?
        valid_key_buffer_codes = [K_ESCAPE, K_BACKSPACE, K_RETURN, K_SPACE] + range(K_a, K_z + 1) + range(K_0, K_9 + 1)

        # Is the shift key pressed?
        shift_is_pressed = ( keypresses[K_LSHIFT] or keypresses[K_RSHIFT] )


        # Check each event
        for event in events:

            if (event.type == KEYDOWN):

                """
                # This might just be a terrible, dirty hack.  Probably, even.
                # I'm going to force the number keypad's "enter" to count as a standard "return key" event.
                if (event.key == K_KP_ENTER):

                    # Denied!  Yes!!!!!!!
                    event = pygame.event.Event(
                        KEYDOWN,
                        {
                            "scancode": event.scancode, # I know I'm reusing KB_ENTER's scancode.  I don't use scancode in this project, but just in case...
                            "key": K_RETURN,            # Overwrite
                            "unicode": u'',             # Return never generates a unicode character either way, maybe?
                            "mod": event.mod
                        }
                    )
                    #<Event(2-KeyDown {'scancode': 116, 'key': 274, 'unicode': u'', 'mod': 4096})>
                """


                results["key-events"].append(event)

                results["keydown-keycodes"].append(event.key)

                if (True):#event.key in valid_key_buffer_codes):

                    if (event.key == K_MINUS):

                        if (shift_is_pressed):
                            results["key-buffer"] += "_"

                        else:
                            results["key-buffer"] += "-"

                    elif (event.key == K_COMMA):

                        if (shift_is_pressed):
                            results["key-buffer"] += "<"

                        else:
                            results["key-buffer"] += ","

                    elif (event.key == K_PERIOD):

                        if (shift_is_pressed):
                            results["key-buffer"] += ">"

                        else:
                            results["key-buffer"] += "."

                    elif (event.key == K_SLASH):

                        if (shift_is_pressed):
                            results["key-buffer"] += "?"

                        else:
                            results["key-buffer"] += "/"

                    elif event.key == K_TAB:

                        pass
                        #results["key-buffer"] += "     "

                    elif (event.key == K_1):

                        if (shift_is_pressed):
                            results["key-buffer"] += "!"

                        else:
                            results["key-buffer"] += "1"

                    elif (event.key == K_2):

                        if (shift_is_pressed):
                            results["key-buffer"] += "@"

                        else:
                            results["key-buffer"] += "2"

                    elif (event.key == K_3):

                        if (shift_is_pressed):
                            results["key-buffer"] += "#"

                        else:
                            results["key-buffer"] += "3"

                    elif (event.key == K_4):

                        if (shift_is_pressed):
                            results["key-buffer"] += "$"

                        else:
                            results["key-buffer"] += "4"

                    elif (event.key == K_9):

                        if (shift_is_pressed):
                            results["key-buffer"] += "("

                        else:
                            results["key-buffer"] += "9"

                    elif (event.key == K_0):

                        if (shift_is_pressed):
                            results["key-buffer"] += ")"

                        else:
                            results["key-buffer"] += "0"

                    elif (event.key == K_MINUS):

                        if (shift_is_pressed):
                            results["key-buffer"] += "_"

                        else:
                            results["key-buffer"] += "-"

                    elif event.key == K_QUOTE:

                        if (shift_is_pressed):
                            results["key-buffer"] += "\""

                        else:
                            results["key-buffer"] += "'"

                    elif (event.key >= K_a and event.key <= K_z):

                        letter = chr(event.key)

                        if (shift_is_pressed):
                            letter = letter.upper()#string.upper(letter)

                        results["key-buffer"] += letter

                    elif event.key == K_SEMICOLON:

                        if (shift_is_pressed):
                            results["key-buffer"] += ":"

                        else:
                            results["key-buffer"] += ";"

                    elif event.key == K_EQUALS:

                        if (shift_is_pressed):
                            results["key-buffer"] += "+"

                        else:
                            results["key-buffer"] += "="

                    elif (event.key >= K_LEFTBRACKET and event.key <= K_RIGHTBRACKET):

                        letter = chr(event.key)

                        results["key-buffer"] += letter

                    elif (event.key >= K_SPACE and event.key <= K_9):

                        letter = chr(event.key)

                        results["key-buffer"] += letter

            elif (event.type == JOYAXISMOTION):

                if ( abs(event.value) >= 0.35):

                    results["gamepad-events"].append(event)

            elif (event.type == JOYHATMOTION):

                results["gamepad-events"].append(event)

            elif (event.type == JOYBUTTONDOWN):

                results["gamepad-events"].append(event)


        self.system_input = results


    def poll_and_update_gameplay_input(self, system_input, keypresses):

        gameplay_input = []


        if ( self.check_gameplay_action("left", system_input, keypresses, singular = False) ):

            gameplay_input.append(INPUT_MOVE_LEFT)

        elif ( self.check_gameplay_action("right", system_input, keypresses, singular = False) ):

            gameplay_input.append(INPUT_MOVE_RIGHT)

        elif ( self.check_gameplay_action("up", system_input, keypresses, singular = False) ):

            gameplay_input.append(INPUT_MOVE_UP)

        elif ( self.check_gameplay_action("down", system_input, keypresses, singular = False) ):

            gameplay_input.append(INPUT_MOVE_DOWN)


        if ( self.check_gameplay_action("dig-left", system_input, keypresses, singular = False) ):

            gameplay_input.append(INPUT_DIG_LEFT)

        elif ( self.check_gameplay_action("dig-right", system_input, keypresses, singular = False) ):

            gameplay_input.append(INPUT_DIG_RIGHT)

        elif ( self.check_gameplay_action("dig-forward", system_input, keypresses, singular = False) ):

            gameplay_input.append(INPUT_DIG_FORWARD)


        if ( self.check_gameplay_action("suicide", system_input, keypresses, singular = False) ):

            gameplay_input.append(INPUT_SUICIDE)


        if ( self.check_gameplay_action("bomb", system_input, keypresses, singular = True) ):

            gameplay_input.append(INPUT_BOMB)


        if ( self.check_gameplay_action("interact", system_input, keypresses, singular = True) ):

            gameplay_input.append(INPUT_ACTION)


        if ( self.check_gameplay_action("skill1", system_input, keypresses, singular = True) ):

            gameplay_input.append(INPUT_ACTIVATE_SKILL_1)

        elif ( self.check_gameplay_action("skill2", system_input, keypresses, singular = True) ):

            gameplay_input.append(INPUT_ACTIVATE_SKILL_2)


        # Let's check minimap keypress (held) first.  If the player is looking at the minimap,
        # no other menu-oriented (?) input should function.
        if ( self.check_gameplay_action("minimap", system_input, keypresses, singular = False) ):

            gameplay_input.append(INPUT_MINIMAP)

        elif ( any( self.check_gameplay_action(action, system_input, keypresses, singular = True) for action in ("enter", "enter2") ) ):

            gameplay_input.append(INPUT_SELECTION_ACTIVATE)

        elif ( self.check_gameplay_action("menu-up", system_input, keypresses, singular = True) ):

            gameplay_input.append(INPUT_SELECTION_UP)

        elif ( self.check_gameplay_action("menu-down", system_input, keypresses, singular = True) ):

            gameplay_input.append(INPUT_SELECTION_DOWN)

        elif ( self.check_gameplay_action("menu-left", system_input, keypresses, singular = True) ):

            gameplay_input.append(INPUT_SELECTION_LEFT)

        elif ( self.check_gameplay_action("menu-right", system_input, keypresses, singular = True) ):

            gameplay_input.append(INPUT_SELECTION_RIGHT)

        elif ( self.check_gameplay_action("home", system_input, keypresses, singular = True) ):

            gameplay_input.append(INPUT_SELECTION_HOME)

        elif ( self.check_gameplay_action("end", system_input, keypresses, singular = True) ):

            gameplay_input.append(INPUT_SELECTION_END)

        elif ( self.check_gameplay_action("page-up", system_input, keypresses, singular = True) ):

            gameplay_input.append(INPUT_SELECTION_PAGEUP)

        elif ( self.check_gameplay_action("page-down", system_input, keypresses, singular = True) ):

            gameplay_input.append(INPUT_SELECTION_PAGEDOWN)

        """
        # Begin Debug
        elif ( self.check_gameplay_action("debug", system_input, keypresses, singular = True) ):
            gameplay_input.append(INPUT_DEBUG)
        # End Debug
        """


        if ( self.check_gameplay_action("net-chat", system_input, keypresses, singular = True) ):

            gameplay_input.append(INPUT_NET_CHAT)


        #return gameplay_input
        self.gameplay_input = gameplay_input


    # Lock access to system input
    def lock_system_input(self):

        # Increment
        self.system_input_lock_count += 1


    # Unlock system input access
    def unlock_system_input(self):

        # Decrement
        self.system_input_lock_count -= 1

        # Don't go negative
        if (self.system_input_lock_count < 0):
            self.system_input_lock_count = 0


    # Lock access to gameplay input
    def lock_gameplay_input(self):

        # Increment
        self.gameplay_input_lock_count += 1


    # Unlock gameplay input access
    def unlock_gameplay_input(self):

        # Decrement
        self.gameplay_input_lock_count -= 1

        # Don't go negative
        if (self.gameplay_input_lock_count < 0):
            self.gameplay_input_lock_count = 0


    # Lock both input types
    def lock_all_input(self):

        self.lock_system_input()
        self.lock_gameplay_input()


    # Unlock both input types
    def unlock_all_input(self):

        self.unlock_system_input()
        self.unlock_gameplay_input()


    # Retrieve the last-used device type ("keyboard" or "gamepad")
    def get_last_used_device(self):

        # Return
        return self.last_used_device


    def get_system_input(self):

        # Unlocked?
        if (self.system_input_lock_count == 0):

            return self.system_input

        # Locked; return "no data" for each type of system input
        else:

            return self.get_empty_system_input()


    # Get keypress data
    def get_keypresses(self):

        # Return the reference we got when updating input data
        return self.keypresses


    # Return a string of characters, primarily for typing in save game names, etc.
    def get_key_buffer(self):

        # Unlocked = full access
        if (self.system_input_lock_count == 0):

            return self.system_input["key-buffer"]

        # Otherwise, we'll return empty string (no buffer data access)
        else:

            return ""


    # Return any key that the user keyed down (but not ones that were previously touched and now remain held down)
    def get_touched_keys(self):

        # Unlocked = full access
        if (self.system_input_lock_count == 0):

            return self.system_input["keydown-keycodes"]

        # Otherwise, we'll return an empty collection
        else:

            return []


    def get_gameplay_input(self):

        # Unlocked?
        if (self.gameplay_input_lock_count == 0):

            return self.gameplay_input

        # Otherwise, return non input
        else:

            return self.collect_empty_gameplay_input()


    def collect_empty_gameplay_input(self):

        return []


    def check_gameplay_action(self, action, system_input, keypresses, singular = True):

        # Check keyboard first; validate action.
        if (action in self.keyboard_settings):

            # Check for a singular button press?
            if (singular):

                if ( self.check_keydown_event( self.keyboard_settings[action], system_input["key-events"] ) ):

                    # Track last used device
                    self.last_used_device = "keyboard"

                    return True

            # No; check for a dynamic keypress...
            else:

                if (keypresses[ self.keyboard_settings[action] ]):

                    # Track last used device
                    self.last_used_device = "keyboard"

                    return True


        # Now check gamepad, if one exists...
        if (self.joystick):

            # Validate action
            if (action in self.active_gamepad_settings):

                # Are we checking for a singular button press event?
                if (singular):

                    if ( self.check_gamepad_event( self.active_gamepad_settings[action], system_input["gamepad-events"] ) ):

                        # Track last used device
                        self.last_used_device = "gamepad"

                        return True

                # No; we'll check the live gamepad input status...
                else:

                    log( "checking '%s'..." % action )

                    if ( self.check_gamepad_state( self.active_gamepad_settings[action] ) ):

                        # Track last used device
                        self.last_used_device = "gamepad"

                        return True


        return False


    def check_keydown_event(self, keycode, events):

        for event in events:

            if (event.type == KEYDOWN):

                if (event.key == keycode):

                    return True


        return False


    def check_gamepad_event(self, settings, events):

        # Which type of singular event are we seeking?
        pygame_event = PYGAME_EVENT_TRANSLATIONS[ settings["type"] ]

        for event in events:

            if (event.type == pygame_event):

                if (event.type == JOYBUTTONDOWN):

                    if (event.button == settings["index"]):

                        return True

                if (event.type == JOYAXISMOTION):

                    if (event.axis == settings["index"]):

                        direction_x = settings["direction-x"]

                        if (direction_x < 0):

                            if (event.value < -0.4):
                                return True

                        elif (direction_x > 0):

                            if (event.value > 0.4):
                                return True

                elif (event.type == JOYHATMOTION):

                    if (event.hat == settings["index"]):

                        (hat_x, hat_y) = (
                            settings["direction-x"],
                            settings["direction-y"]
                        )

                        if ( (hat_x, hat_y) == event.value ):

                            return True

        return False


    def check_gamepad_state(self, settings):

        log( "\t", settings )

        # Validate that we have a joystick configured
        if (self.joystick):

            # Buttons are easy
            if (settings["type"] == PAD_BUTTON):

                # Which button?
                button = settings["index"]

                # Validate that the joystick has at least that many buttons
                if ( button < self.joystick.get_numbuttons() ):

                    # Check button status
                    return self.joystick.get_button( settings["index"] )

            # Analog sticks
            elif (settings["type"] == PAD_AXIS):

                # Which axis?
                axis = settings["index"]

                # "direction-x" dictates whether we want a negative or positive axis value
                direction_x = settings["direction-x"]
                #direction_y = settings["direction-y"]

                # Validate that the axis exists
                if ( axis < self.joystick.get_numaxes() ):

                    if (direction_x < 0):

                        if (self.joystick.get_axis(axis) < -0.4):
                            return True

                    elif (direction_x > 0):

                        if (self.joystick.get_axis(axis) > 0.4):
                            return True

                    """
                    elif (direction_y < 0):
                        if (self.joystick.get_axis(axis) < -0.4):
                            return True
                    elif (direction_y > 0):
                        if (self.joystick.get_axis(axis) > 0.4):
                            return True
                    """

            # POV hats
            elif (settings["type"] == PAD_HAT):

                # Which hat?
                hat = settings["index"]

                # Make sure hat exists on joystick

                if ( hat < self.joystick.get_numhats() ):

                    try:
                        x = int( settings["direction-x"] )
                        y = int( settings["direction-y"] )

                    except:
                        return False

                    # Query hat status
                    (hat_x, hat_y) = self.joystick.get_hat(hat)


                    # In case of a tie, x-axis wins
                    if (hat_x != 0 and hat_y != 0):

                        hat_y = 0



                    # Is the hat in the specified state?
                    if ( (hat_x, hat_y) == (x, y) ):

                        return True


        return False
