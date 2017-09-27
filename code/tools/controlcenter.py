import os
import sys

from code.tools.widgetdispatcher import WidgetDispatcher

from code.tools.gui import GUI_Manager
from code.tools.uiresponder import UIResponder

from code.tools.xml import XMLParser, XMLNode

from code.utils.common import ensure_path_exists

# Used for universal controllers (window, network, etc.)
from code.controllers.windowcontroller import WindowController, DebugWindowController
from code.controllers.soundcontroller import SoundController
from code.controllers.networkcontroller import NetworkController
from code.controllers.savecontroller import SaveController
from code.controllers.splashcontroller import SplashController
from code.controllers.menucontroller import MenuController
from code.controllers.inputcontroller import InputController
from code.controllers.httprequestcontroller import HttpRequestController

# Used for creating only (not for dedicated, universal controllers)
from code.controllers.eventcontroller import EventController

from code.controllers.debugcontroller import DebugController

from code.controllers.editorcontroller import EditorController
from code.controllers.hotkeycontroller import HotkeyController

from code.controllers.localizationcontroller import LocalizationController

# Need this for saving preferences
from code.constants.paths import CONFIG_PATH

class ControlCenter:

    # Window controller will need the dimensions of the playable area as well as the window itself
    def __init__(self, render_width, render_height, screen_width, screen_height, debug = False):

        # Global fullscreen preference
        self.fullscreen_preferred = False


        # Create a widget dispatcher
        self.widget_dispatcher = WidgetDispatcher()


        # Create a window controller
        self.window_controller = None
        if (not debug):
            self.window_controller = WindowController(render_width, render_height, screen_width, screen_height)
        else:
            self.window_controller = DebugWindowController()

        # Create a sound controller
        self.sound_controller = None
        if (not debug):
            self.sound_controller = SoundController()

        # Create a network controller
        self.network_controller = NetworkController()

        # Create a save controller
        self.save_controller = SaveController()

        # Create a splash controller
        self.splash_controller = SplashController()

        # Create a menu controller
        self.menu_controller = MenuController()

        # Create an input controller
        self.input_controller = InputController()

        # Create an http request controller
        self.http_request_controller = HttpRequestController()


        # Create a (level) editor controller
        self.editor_controller = EditorController()

        # Create a hotkey controller
        self.hotkey_controller = HotkeyController()

        # Create GUI manager
        self.gui_manager = GUI_Manager()

        # Create (G)UI response
        self.ui_responder = UIResponder()


        # Localization controller
        self.localization_controller = LocalizationController()
        #self.localization_controller.load("data/localization/de.xml")


        # Debug controller
        self.debug_controller = DebugController()


    # Save all controller preferences
    def save_preferences(self):

        # Create preferences node
        root = XMLNode("preferences")

        # Fullscreen preference setting
        root.add_node(
            XMLNode("fullscreen").set_inner_text(
                "1" if (self.fullscreen_preferred) else "0"
            )
        )

        # Language setting
        root.add_node(
            XMLNode("language").set_inner_text(
                "%s" % self.get_localization_controller().get_language()
            )
        )

        # Layout setting (set with language)
        root.add_node(
            XMLNode("layout").set_inner_text(
                "%s" % self.get_localization_controller().get_layout()
            )
        )

        # Font size setting (set with language)
        root.add_node(
            XMLNode("font-size").set_inner_text(
                "%s" % self.get_window_controller().get_font_size()
            )
        )

        # Font setting (set with language)
        root.add_node(
            XMLNode("font").set_inner_text(
                "%s" % self.get_window_controller().get_font()
            )
        )


        # Add sound preferences node
        node = root.add_node(
            XMLNode("audio")
        )

        # Background music setting
        node.add_node(
            XMLNode("background-volume").set_inner_text(
                "%s" % self.get_sound_controller().get_background_volume()
            )
        )

        # Sound effects setting
        node.add_node(
            XMLNode("sfx-volume").set_inner_text(
                "%s" % self.get_sound_controller().get_sfx_volume()
            )
        )


        # Ensure config path exists
        ensure_path_exists(CONFIG_PATH)


        # Save to file
        f = open(
            os.path.join(CONFIG_PATH, "preferences.xml"), "w"
        )

        # Serialize xml
        f.write(
            root.compile_xml_string()
        )

        # Done
        f.close()


    # Load all controller preferences
    def load_preferences(self):

        # Calculate preferences path
        path = os.path.join(CONFIG_PATH, "preferences.xml")

        # Validate path
        if ( os.path.exists(path) ):

            # Read XML
            root = XMLParser().create_node_from_file(path)

            # Validate
            if (root):

                # Check for fullscreen setting
                ref_fullscreen = root.find_node_by_tag("fullscreen")

                # Validate
                if (ref_fullscreen):

                    # Update setting
                    self.fullscreen_preferred = ( int(ref_fullscreen.innerText) == 1 )


                # Check for language setting
                ref_language = root.find_node_by_tag("language")

                # Validate
                if (ref_language):

                    # Convenience
                    language = ref_language.innerText


                    # Update setting
                    self.get_localization_controller().set_language(language)

                    # Calculate localization filepath
                    path = os.path.join("data", "localization", "%s.xml" % language)

                    # Validate path
                    if ( os.path.exists(path) ):

                        # Load translations for preferred language
                        self.get_localization_controller().load(path)


                # Check for layout setting
                ref_layout = root.find_node_by_tag("layout")

                # Validate
                if (ref_layout):

                    # Update setting
                    self.get_localization_controller().set_layout(
                        ref_layout.innerText
                    )


                # Check for font size setting.
                # We must set this before setting the font!
                ref_font_size = root.find_node_by_tag("font-size")

                # Validate
                if (ref_font_size):

                    # Update setting
                    self.get_window_controller().set_font_size(
                        int( ref_font_size.innerText )
                    )


                # Check for font setting
                ref_font = root.find_node_by_tag("font")

                # Validate
                if (ref_font):

                    # Convenience
                    font = ref_font.innerText

                    # Update setting
                    self.get_window_controller().set_font(font)


                # Check for background-volume node
                ref_background_volume = root.find_node_by_tag("background-volume")

                # Validate
                if (ref_background_volume):

                    # Update setting
                    self.get_sound_controller().set_background_volume(
                        float( ref_background_volume.innerText )
                    )


                # Check for sfx-volume node
                ref_sfx_volume = root.find_node_by_tag("sfx-volume")

                # Validate
                if (ref_sfx_volume):

                    # Update setting
                    self.get_sound_controller().set_sfx_volume(
                        float( ref_sfx_volume.innerText )
                    )


    # Check to see whether or not the player has edited their controls.
    # Yes, I'm really only doing this to help me with an achievement!
    def has_edited_controls(self):

        # Check for "ignore" override (file check)
        if ( os.path.exists( os.path.join("user", "behaviors.xml") ) ):

            # Read xml data
            node = XMLParser().create_node_from_file( os.path.join("user", "behaviors.xml") )

            # Validate xml compiled
            if (node):

                # Search for "pretend uncustomized" setting
                ref = node.find_node_by_tag("pretend-uncustomized")

                # Validate
                if (ref):

                    # If set to "yes" then return False
                    if (ref.innerText == "yes"):

                        # Even if the player customized the controls,
                        # game scripts will believe that no customization exists.
                        return False


        # Simply check for the existence of the controls file
        if ( os.path.exists( os.path.join("user", "controls.xml") ) ):

            # Yep
            return True

        else:
            return False


    # Save local netplay preferences (player name and avatar colors).
    # Requires the Universe object to read relevant data.
    def save_netplay_preferences(self, universe):

        # Get local player id
        player_id = int( universe.get_session_variable("core.player-id").get_value() )


        # Create root node
        root = XMLNode("preferences")


        # Add nick node
        root.add_node(
            XMLNode("nick").set_inner_text(
                universe.get_session_variable( "net.player%d.nick" % player_id ).get_value()
            )
        )

        # Add avatar color data node
        root.add_node(
            XMLNode("avatar").set_inner_text(
                universe.get_session_variable( "net.player%d.avatar.colors" % player_id ).get_value()
            )
        )


        # Add default port node
        root.add_node(
            XMLNode("default-port").set_inner_text(
                "%s" % self.get_network_controller().get_default_port()
            )
        )


        # Ensure config path exists
        ensure_path_exists(CONFIG_PATH)


        # Save to file
        f = open(
            os.path.join(CONFIG_PATH, "netplay.xml"), "w"
        )

        # Serialize xml
        f.write(
            root.compile_xml_string()
        )

        # Done
        f.close()


    # Load local netplay preferences (player name and avatar colors).
    # Call this when launching / joining a netplay game for persistent /nick data, etc.
    # Requires the Universe object to update relevant session variables.
    def load_netplay_preferences(self, universe):

        # Get local player id
        player_id = int( universe.get_session_variable("core.player-id").get_value() )


        # Calculate netplay preferences path
        path = os.path.join(CONFIG_PATH, "netplay.xml")

        # Validate path
        if ( os.path.exists(path) ):

            # Read XML
            root = XMLParser().create_node_from_file(path)

            # Validate
            if (root):

                # Check for nick node
                ref_nick = root.find_node_by_tag("nick")

                # Validate
                if (ref_nick):

                    # Update session variable
                    universe.get_session_variable( "net.player%d.nick" % player_id ).set_value(ref_nick.innerText)


                # Check for avatar color data node
                ref_avatar = root.find_node_by_tag("avatar")

                # Validate
                if (ref_avatar):

                    # Update session variable
                    universe.get_session_variable( "net.player%d.avatar.colors" % player_id ).set_value(ref_avatar.innerText)


                # Check for default port node
                ref_default_port = root.find_node_by_tag("default-port")

                # Validate
                if (ref_default_port):

                    # Update port
                    self.get_network_controller().set_default_port(
                        int( ref_default_port.innerText )
                    )


    # Save all unlocked achievements to a global file.
    # Achievements apply to all game instances; if you unlock an achievement, then any new game you start also has that achievement unlocked.
    def save_unlocked_achievements(self, universe):

        # Just before saving achievements, let's make an implicit call to
        # "load achievements."  This should be completely unnecessary (this happens when
        # starting a new game, loading, etc.) but it's also harmless and a good safeguard.
        self.load_unlocked_achievements(universe)


        # Create an xml node
        root = XMLNode("completed-achievements")

        # Loop completed achievements
        for achievement in [ o for o in universe.get_achievements() if o.is_complete() ]:

            # Add a new node for this completed achievement
            root.add_node(
                XMLNode("completed-achievement").set_inner_text(
                    achievement.get_name()
                )
            )


        # Ensure config path exists
        ensure_path_exists(CONFIG_PATH)


        # Save to file
        f = open(
            os.path.join(CONFIG_PATH, "achievements.xml"), "w"
        )

        # Serialize xml
        f.write(
            root.compile_xml_string()
        )

        # Done
        f.close()


    # Load unlocked achievements, marking previously completed achievments as "complete" for the given universe objecte.
    def load_unlocked_achievements(self, universe):

        # Calculate path for achievements file
        path = os.path.join(CONFIG_PATH, "achievements.xml")

        # Validate path
        if ( os.path.exists(path) ):

            # Read XML
            root = XMLParser().create_node_from_file(path)

            # Validate parsing
            if (root):

                # Find completed achievements node
                ref_completed_achievements = root.find_node_by_tag("completed-achievements")

                # Validate
                if (ref_completed_achievements):

                    # Loop all refs
                    for ref_completed_achievement in ref_completed_achievements.get_nodes_by_tag("completed-achievement"):

                        # Get name from inner text
                        name = ref_completed_achievement.innerText

                        # Find achievement in universe object
                        achievement = universe.get_achievement_by_name(name)

                        # Validate
                        if (achievement):

                            # Flag as complete
                            achievement.set_status("complete")


    def get_widget_dispatcher(self):

        return self.widget_dispatcher


    def get_window_controller(self):

        return self.window_controller


    def get_sound_controller(self):

        return self.sound_controller


    def get_network_controller(self):

        return self.network_controller


    def get_save_controller(self):

        return self.save_controller


    def get_splash_controller(self):

        return self.splash_controller


    def get_menu_controller(self):

        return self.menu_controller


    def get_input_controller(self):

        return self.input_controller


    def get_http_request_controller(self):

        return self.http_request_controller


    def get_editor_controller(self):

        return self.editor_controller


    def get_hotkey_controller(self):

        return self.hotkey_controller


    def get_gui_manager(self):

        return self.gui_manager


    def get_ui_responder(self):

        return self.ui_responder


    def get_localization_controller(self):

        return self.localization_controller


    def get_debug_controller(self):

        return self.debug_controller



    def create_event_controller(self):

        return EventController()

