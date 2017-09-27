import os
from stat import *

import time
from datetime import datetime

import string

import re
import sys

import struct

import cgi
import random

import pygame
from pygame.locals import *

import traceback

import copy
import pickle

import glob

#from OpenGL.GL import *
#from OpenGL.GLU import *

from math import *

from code.utils.common import *
from code.tools.gui import *

from code.tools.controlcenter import ControlCenter

from code.tools.eventqueue import EventQueue, EventQueueIter

from code.game.universe import Universe

from code.game.universeselector import UniverseSelector
from code.game.mapselector import MapSelector
from code.game.dlcselector import DLCSelector

from code.constants.common import *
from code.constants.paths import *

from code.constants.states import *
from code.constants.network import *

from code.constants.newsfeeder import *

from code.constants.sound import CHANNEL_MUSIC

#from challengemonitor import ChallengeMonitor
#from completionmonitor import CompletionMonitor
#from dlc import Uploader, Downloader

from code.tools.xml import XMLList, XMLParser, XMLNode

from code.tools.uiresponder import UIResponder

from code.tools.mixer import BGMixer

#from entities import Player

from code.controllers.timercontroller import TimerController

from code.controllers.tools.netconsole import NetConsoleEntry


# Application class; the master!
class App:

    def __init__(self, game_mode):

        # Randomize numbers
        random.seed()

        # Game mode (game or editor?)
        self.game_mode = game_mode
        #self.output_handler = OutputHandler()


        # Check for sound mixer flag
        if ( get_flag_value("sound debug mode", XMLParser()) == "1" ):

            # Pre-init the sound mixer
            pygame.mixer.pre_init(44100, -16, 2, 512)


        # Get pygame rolling
        pygame.init()

        # Set window title
        pygame.display.set_caption("A Lode Runner Story")

        # Hide mouse
        pygame.mouse.set_visible(0)


        # Assume not fullscreen
        fullscreen = True

        # Calculate preferences path
        path = os.path.join(CONFIG_PATH, "preferences.xml")

        # Validate path
        if ( os.path.exists(path) ):

            # Read XML, then try to find fullscreen preference tag
            ref_fullscreen = XMLParser().create_node_from_file(path).find_node_by_tag("fullscreen")

            # Validate
            if (ref_fullscreen):

                # Update setting
                fullscreen = ( int( ref_fullscreen.innerText ) == 1 )


        # Set up the display
        (self.render_width, self.render_height) = render_init(SCREEN_WIDTH, SCREEN_HEIGHT, fullscreen = ( ((fullscreen and (not ("-F" in sys.argv))) or ("-f" in sys.argv)) and (not ("-F" in sys.argv)) ))#self.preferences["Fullscreen Mode (Requires Restart)"])#, fullscreen = "on")
        #(self.render_width, self.render_height) = render_init(SCREEN_WIDTH + 31, SCREEN_HEIGHT + 47, fullscreen = "off")#self.preferences["Fullscreen Mode (Requires Restart)"])#, fullscreen = "on")


        # Create a control center (for all controllers, e.g. network controller, save / input controllers, etc.!)
        self.control_center = ControlCenter(self.render_width, self.render_height, SCREEN_WIDTH, SCREEN_HEIGHT)


        # Load common label data
        self.control_center.get_localization_controller().import_labels(
            os.path.join("data", "localization", "en.labels.xml")
        )

        # Load any previous preferences
        self.control_center.load_preferences()


        # Read in default CSS theme data
        #self.control_center.get_window_controller().get_css_controller().load_selectors_from_file( os.path.join("data", "css", "debug.css") )
        if (self.game_mode == MODE_GAME):

            # Load game CSS
            self.control_center.get_window_controller().get_css_controller().load_selectors_from_file( os.path.join("data", "css", "theme1.css") )

        elif (self.game_mode == MODE_EDITOR):

            # Load editor CSS
            self.control_center.get_window_controller().get_css_controller().load_selectors_from_file( os.path.join("data", "css", "theme1.editor.css") )


        # Convenient handle to window controller;
        self.window_controller = self.control_center.get_window_controller()

        # Sound controller;
        self.sound_controller = self.control_center.get_sound_controller()

        # Widget dispatcher;
        self.widget_dispatcher = self.control_center.get_widget_dispatcher()

        # Splash controller;
        self.splash_controller = self.control_center.get_splash_controller()

        # Menu controller;
        self.menu_controller = self.control_center.get_menu_controller()

        # Input controller;
        self.input_controller = self.control_center.get_input_controller()

        # Editor controller (level editor);
        self.editor_controller = self.control_center.get_editor_controller()

        # hotkey controller (for level editor only, at least right now);
        self.hotkey_controller = self.control_center.get_hotkey_controller()

        # GUI manager (for level editor)
        self.gui_manager = self.control_center.get_gui_manager()

        # UI responder (for level editor)
        # pass

        # Network controller;
        self.network_controller = self.control_center.get_network_controller()

        # and, lastly, the save controller.
        self.save_controller = self.control_center.get_save_controller()


        # Let's take this moment to load in the hotkeys for the level editor
        self.hotkey_controller.import_from_xml_file( os.path.join("data", "xml", "editor.hotkeys.xml") )


        # Entry box for chatting
        self.net_console_entry = NetConsoleEntry()


        # Set up joystick support
        pygame.joystick.init()

        # Before checking for any device (and showing related newsfeeder updates),
        # I want to set a brief delay on the newsfeeder so that the player doesn't
        # see a newsfeeder update immediately upon loading the game, it's kind of distracting.
        self.window_controller.get_newsfeeder().delay(60) # hard-coded


        # Check the name of the last gamepad device we used (or empty string if none is on record)
        last_device_name = self.input_controller.get_last_used_device_name()

        log2( "Seeking last device:  %s" % last_device_name )


        # Sometimes we prefer to skip/ignore joysticks.
        if ( not ("-J" in sys.argv) ):

            # Did we have a last device on the books?
            if ( last_device_name != "" ):

                # Let's try to select that most recent joystick, then.
                result = self.input_controller.select_device_by_name(
                    last_device_name # This will fail gracefully if there's no "last joystick" or we cannot find the "last joystick"
                )

                # If that failed (either because we never had a "last joystick" or we simply couldn't find it),
                # then we'll also try using the first available joystick by any given name.
                if (not result):

                    log2( "Seeking first available device:  %s" % self.input_controller.get_first_available_device_name() )

                    # One more chance
                    result = self.input_controller.select_device_by_name(
                        self.input_controller.get_first_available_device_name() # Fails gracefully if we have no available device
                    )

                    if (not result):

                        # Post newsfeeder item showing that we found the last joystick
                        self.window_controller.get_newsfeeder().post({
                            "type": NEWS_GAME_GAMEPAD_NOT_FOUND,
                            "title": self.control_center.get_localization_controller().get_label("previous-gamepad-not-found:header"),
                            "content": "%s" % last_device_name
                        })

                    # We couldn't find the last-used gamepad, but we found some other gamepad attached
                    else:

                        # Post newsfeeder item telling the player what's up!
                        self.window_controller.get_newsfeeder().post({
                            "type": NEWS_GAME_GAMEPAD_DEFAULT,
                            "title": self.control_center.get_localization_controller().get_label("new-gamepad-enabled:header"),
                            "last-device": last_device_name, # We were trying to find this one...
                            "current-device": "%s" % self.input_controller.get_active_device_name() # ... but we're using this one instead.
                        })

                else:
                    log2( "Found." )

                    # Post newsfeeder item showing that we found the last joystick
                    self.window_controller.get_newsfeeder().post({
                        "type": NEWS_GAME_GAMEPAD_REMEMBERED,
                        "title": self.control_center.get_localization_controller().get_label("previous-gamepad-found:header"),
                        "content": "%s" % self.input_controller.get_active_device_name()
                    })

            # If not, let's see if we can find a new one by default.
            else:

                # Try to get the first available joystick
                result = self.input_controller.select_device_by_name(
                    self.input_controller.get_first_available_device_name() # Fails gracefully when no device is attached
                )

                # Don't bother alerting players of "no gamepads detected," but DO let them know if we found a default device.
                if (result):

                    # Post newsfeeder item showing that we found a default gamepad
                    self.window_controller.get_newsfeeder().post({
                        "type": NEWS_GAME_GAMEPAD_NEW,
                        "title": self.control_center.get_localization_controller().get_label("new-gamepad-enabled:header"),
                        "content": "%s" % self.input_controller.get_active_device_name()
                    })


        # Set up an initial variables list.  We'll be adding to it soon.
        self.variables = {"from": "checkpoint"}


        # Load controls (?)
        #self.load_controls()


        # Set up sound mixer
        pygame.mixer.init()

        pygame.mixer.set_reserved(CHANNEL_MUSIC)

        #self.background_loop = load_sound("track1.ogg")
        #self.background_loop is obsolete; tracks are controlled now via sound/tracklist.txt

        """
        play_immediately = False
        if (self.preferences["Background Music"] == "off"):
            play_immediately = False

        self.bg_mixer = BGMixer(True)#play_immediately)

        #if (self.preferences["Background Music"] == "on"):
        #    self.background_loop.play(-1)
        """


        # Load in all gl assets
        self.window_controller.load_gl_assets()

        # Get handles to a few surfaces
        self.mouse_sprite = self.window_controller.get_gfx_controller().get_graphic("cursor")
        self.tilesheet_sprite = self.window_controller.get_gfx_controller().get_graphic("tilesheet")
        self.additional_sprites = self.window_controller.get_gfx_controller().get_graphic("sprites")

        # Get handles to a couple of text renderers
        self.text_renderers = {
            "normal": self.window_controller.get_text_controller_by_name("default").get_text_renderer(),
            "gui": self.window_controller.get_text_controller_by_name("default").get_text_renderer() # Not sure I use this anywhere?
            #"normal": GLTextRenderer(os.path.join(FONT_PATH, 'jupiterc.ttf'), (255, 255, 255), (0, 0, 0), 18),
            #"gui": GLTextRenderer(os.path.join(FONT_PATH, 'jupiterc.ttf'), (255, 255, 255), (0, 0, 0), 18),
        }


        # Load in dialog defaults and gui objects
        (gui_defaults, gui_objects) = self.load_dialog_data( os.path.join("data", "xml", "dialogs.xml") )

        # Hack these into the GUI manager
        self.gui_manager.gui_defaults = gui_defaults

        # Should do this within the GUI manager sometime
        for (name, widget) in gui_objects:

            # Hide everything by default
            widget.hide(animated = False)

            # Need to move this into GUI manager sometime
            self.gui_manager.add_widget_with_name(name, widget)


        # (?) Show the level editor menu bar
        self.gui_manager.get_widget_by_name("menu-bar").show()


        #for i in range(1, 6):
        #    debug_fill_pattern( self.additional_sprites["fill-patterns"][i].get_texture_id() )


        # Create initial universe object.
        # Note:  I should set this to None when launching into menu (i.e. production release),
        #        because we'll wait for the player to select a universe to play (using a universe selector).
        self.universe = None
        #self.universe = Universe("gifs", self.game_mode, self.control_center)
        #self.universe = Universe("story1", self.game_mode, self.control_center)

        #self.universe = Universe("demo2")
        #self.universe = Universe("challenge_rooms", self.control_center)



        #self.universe = Universe("demo3")

        #self.universe = Universe("mainmenu", self.game_mode, self.control_center)
        #self.universe = Universe("coop1", self.game_mode, self.control_center)

        #self.universe = Universe("newdemo1", self.game_mode, self.control_center)

        #self.universe = Universe("dev1", self.game_mode, self.control_center)
        #self.universe = Universe("dev2", self.game_mode, self.control_center)

        # Check for --edit flag
        for i in range( 0, len(sys.argv) - 1 ):

            # --edit?
            if ( sys.argv[i] == "--edit" ):

                # Next argument should be universe to edit
                try:
                    self.universe = Universe( sys.argv[i+1], self.game_mode, self.control_center )

                except:
                    logn( "error", "Universe '%s' does not exist.  Possible misuse of --edit argument." % sys.argv[i+1] )
                    sys.exit("Goodbye (universe loading error)")


        # The application can, in response to user input, create a WorldMap for its universe
        # and render it on top of all universe graphics.
        self.minimap = None


        """
        Debug
        """
        # Let's pause the universe by default when recording GIF animations
        if (False):

            # When we hit debug key to start recording, we'll call unpause...
            self.universe.pause()


            # When creating GIF replay data for skill previews, which skill am I recording?
            skill_name = "personal-shield"

            # When I'm creating skill GIF replay files, I will assign the skill as level 3 to skill slot 1
            self.universe.get_session_variable("core.skills.%s" % skill_name).set_value("3")
            self.universe.get_session_variable("core.player1.skill1").set_value(skill_name)

        """
        End Debug
        """

        """
        self.universe.timer_controller.add_repeating_event(
            90,
            uses = 5,
            event = lambda f = logn: f( "app", "Show this message 5 times..." )
        )
        """


        # For development / debugging purposes...
        #self.universe.get_session_variable("core.skills.hacking").set_value("0")
        #self.universe.session["core.skills.persuasion"]["value"] = "1"
        #self.universe.session["core.skills.sprint"]["value"] = "1"
        #self.universe.session["core.skills.remote-bomb"]["value"] = "1"
        #self.universe.session["core.player1.skill1"]["value"] = "sprint"
        #self.universe.session["core.player1.skill2"]["value"] = "remote-bomb"


        # Debug
        #self.universe.get_session_variable("core.player1.skill-points").set_value("5")
        #self.universe.get_session_variable("core.skills.matrix:locked").set_value("0")
        #self.universe.get_session_variable("core.bombs.count").set_value("15")
        #self.universe.get_session_variable("core.gold.wallet").set_value("250")


        #self.save_controller.load_from_folder( "sessions/mike/universes/story1/manualsave25", self.universe )


        #for skill in SKILL_LIST:
        #    self.universe.session["core.skills.%s" % skill]["value"] = "3"

        #self.universe.calculate_adjacency_data()


        # Set up a GameMenu object
        self.game_menu = self.widget_dispatcher.create_main_menu()


        # map-shaking trackers
        self.shake_timer = 0

        self.shake_values = [0, 0]
        self.shake_bounds = [0, 0]


    def load_dialog_data(self, filename):

        # Load the data...
        f = open(filename, "r")
        xml = f.read()
        f.close()


        # Set up a root node
        node = XMLParser().create_node_from_xml(xml)


        # First let's populate default settings...
        gui_defaults = {}

        ref_defaults = node.get_first_node_by_tag("defaults")

        if (ref_defaults):

            tag_collection = ref_defaults.get_nodes_by_tag("*")

            for ref_tag in tag_collection:

                gui_defaults[ref_tag.tag_type] = {}

                setting_collection = ref_tag.get_nodes_by_tag("setting")

                for ref_setting in setting_collection:

                    gui_defaults[ ref_tag.tag_type ][ ref_setting.get_attribute("key") ] = ref_setting.get_attribute("value")


        # **hack
        self.gui_manager.gui_defaults = gui_defaults


        # Now we'll load in the dialog templates
        gui_objects = []

        ref_dialogs = node.get_first_node_by_tag("dialogs")

        if (ref_dialogs):

            dialog_collection = ref_dialogs.get_nodes_by_tag("dialog")

            for ref_dialog in dialog_collection:

                gui_objects.append( [ref_dialog.get_attribute("name"), self.gui_manager.create_dialog_from_xml_node(ref_dialog, self.control_center)] )




        return (gui_defaults, gui_objects)




    def get_last_keys(self):
        return self.g_keys

    def check_input(self, keys, literal = False):

        clicked = False
        rightclicked = False
        scroll_dir = None

        wheel_left = False
        wheel_right = False

        for event in keys:

            if event.type == QUIT:
                return ("quit", 0, 0, 0, 0)

            elif event.type == MOUSEBUTTONUP and event.button == 1:
                clicked = True

            elif event.type == MOUSEBUTTONUP and event.button == 3:
                rightclicked = True

            elif event.type == MOUSEBUTTONDOWN and event.button == 4:
                scroll_dir = "up"

            elif event.type == MOUSEBUTTONDOWN and event.button == 5:
                scroll_dir = "down"


            if (event.type == MOUSEBUTTONDOWN and event.button in (6, 7)):

                if (event.button == 6):
                    wheel_left = True

                elif (event.button == 7):
                    wheel_right = True

        return (clicked, rightclicked, scroll_dir, wheel_left, wheel_right)



    # Handle some xml.  I didn't want to further clutter the menu function...
    def populate_dlc_list(self, xml):

        rows = []

        # Send the xml data to an XMLList object
        handler = XMLList(xml)

        # Loop through any level tags
        if ("level" in handler.collection):

            for level_dict in handler.collection["level"]:

                # Make sure all the data we need is here
                if ( ("id" in level_dict) and ("title" in level_dict) and ("author" in level_dict) and ("date" in level_dict) ):
                    rows.append(level_dict)

        # Do we have any news to display?
        if ("news" in handler.collection):

            for news_dict in handler.collection["news"]:

                # Maybe it's a news update?
                if ( ("title" in news_dict) and ("text" in news_dict) ):
                    self.news_ticker_items.append( (news_dict["title"], news_dict["text"]) )

        return rows


    def shake_screen(self, intensity = 3, style = 0):

        if (style == SHAKE_BRIEFLY):

            self.shake_timer = 30

            self.shake_intensity = intensity
            self.shake_status = STATUS_ACTIVE

            self.shake_bounds = [-random.randint(1, self.shake_intensity), -random.randint(1, self.shake_intensity)]

        elif (style == SHAKE_LONGER):

            self.shake_timer = 50

            self.shake_intensity = intensity
            self.shake_status = STATUS_ACTIVE

            self.shake_bounds = [-random.randint(1, self.shake_intensity), -random.randint(1, self.shake_intensity)]

        elif (style == SHAKE_END):

            self.shake_timer =  0
            self.shake_status = STATUS_INACTIVE

        else:

            self.shake_timer = INFINITY # Oh yeah!

            self.shake_intensity = intensity
            self.shake_status = STATUS_ACTIVE

            self.shake_bounds = [-random.randint(1, self.shake_intensity), -random.randint(1, self.shake_intensity)]

    def process_screen_shake(self):

        self.shake_timer -= 1


        if (self.shake_timer <= 0):
            self.shake_status = STATUS_INACTIVE


        for i in (0, 1):

            if (self.shake_values[i] > self.shake_bounds[i]):
                self.shake_values[i] -= 1

                if (self.shake_values[i] <= self.shake_bounds[i]):

                    if (self.shake_status == STATUS_ACTIVE):
                        self.shake_bounds[i] = random.randint(1, self.shake_intensity)

                    else:
                        self.shake_bounds[i] = 0

            elif (self.shake_values[i] < self.shake_bounds[i]):
                self.shake_values[i] += 1

                if (self.shake_values[i] >= self.shake_bounds[i]):

                    if (self.shake_status == STATUS_ACTIVE):
                        self.shake_bounds[i] = -random.randint(1, self.shake_intensity)


                    else:
                        self.shake_bounds[i] = 0


    def game_logic(self, render = True):

        return





    # What to do with this, in timeE?
    def handle_escape_event(self, escape_event):

        # Quick-view of a certain quest?
        #if (escape_event.get_event() == "show-active-quest"):
        #    self.pause_menu.quickview_active_quest(escape_event.get_param("-quest-name"), self.universe, self.text_renderers["normal"])
        return


    # Handle an app-level event
    def handle_event(self, event, control_center, universe):

        # Convenience
        (action, params) = (
            event.get_action(),
            event.get_params()
        )

        # Convenience
        action = event.get_action()
        log2( "App event:  %s" % action )


        # Back to main menu
        if ( action == "fwd.return-to-menu.commit" ):

            # Fetch the window controller
            window_controller = control_center.get_window_controller()

            # Unhook from the window controller
            window_controller.unhook(self)

        elif ( action == "app:escape-redirect" ):

            return self.handle_app_escape_redirect_event(event, self.control_center)

        # Begin a new single player game; select the universe to play.
        elif ( action == "app:singleplayer.new" ):

            return self.handle_app_singleplayer_new_event(event, control_center, universe)

        # Continue the last single player story mode game
        elif ( action == "app:singleplayer.continue" ):

            return self.handle_app_singleplayer_continue_event(event, control_center, universe)

        # Coop server
        elif ( action == "app:multiplayer.new" ):

            return self.handle_app_coop_server_event(event, control_center, universe)

        # Coop server - level select
        elif ( action == "app:coop-select-level" ):

            return self.handle_app_coop_select_level_event(event, control_center)

        elif ( action == "app:coop-setup-session" ):

            return self.handle_app_coop_setup_session_event(event, control_center)

        elif ( action == "app:coop-start-session" ):

            return self.handle_app_coop_start_session_event(event, control_center)

        elif ( action == "app:send-new-session-request" ):

            return self.handle_app_send_new_session_request_event(event, control_center)

        elif ( action == "app:listen-for-confirm-new-session" ):

            return self.handle_app_listen_for_confirm_new_session_event(event, control_center)

        # Coop client
        elif ( action == "app:multiplayer.browser" ):

            return self.handle_app_coop_client_event(event, control_center, universe)

        elif ( action == "app:get-coop-sessions" ):

            return self.handle_app_get_coop_sessions_event(event, control_center)

        elif ( action == "app:listen-for-coop-sessions" ):

            return self.handle_app_listen_for_coop_sessions_event(event, control_center)

        elif ( action == "app:list-coop-sessions" ):

            return self.handle_app_list_coop_sessions_event(event, control_center)

        elif ( action == "app:join-coop-session" ):

            return self.handle_app_join_coop_session_event(event, control_center)

        elif ( action == "app:listen-for-coop-connection-data" ):

            return self.handle_app_listen_for_coop_connection_data_event(event, control_center)

        elif ( action == "app:connect-to-coop-session" ):

            return self.handle_app_connect_to_coop_session_event(event, control_center)

        elif ( action == "app:send.connection.request" ):

            return self.handle_app_send_connection_request_event(event, self.control_center)

        elif ( action == "app.connect.success" ):

            pass

        elif ( action == "app:listen-for-player-id" ):

            return self.handle_app_listen_for_player_id_event(event, self.control_center)

        # Return notice of a successful connection
        elif ( action == "app.connect.success" ):

            #print 5/0 # **debug

            # Escape the connect screen
            return True

        elif ( action == "app:net.disconnect" ):

            return self.handle_app_net_disconnect_event(event, control_center)

        elif ( action == "app:send-disconnect-notice" ):

            return self.handle_app_send_disconnect_notice_event(event, control_center)

        elif ( action == "app:listen-for-confirm-disconnect" ):

            return self.handle_app_listen_for_confirm_disconnect_event(event, control_center)

        elif ( action == "app:get-dlc-listing" ):

            return self.handle_app_get_dlc_listing_event(event, control_center)

        elif ( action == "app:listen-for-dlc-listing" ):

            return self.handle_app_listen_for_dlc_listing_event(event, control_center)


    # Escape a given redirect.  We'll indicate... success? (?)
    def handle_app_escape_redirect_event(self, event, control_center):

        # Just app fade out
        control_center.get_window_controller().fade_out(
            on_complete = "app:redirect.success"            # Escape the redirect screen after fade completes
        )


    # Begin the process of starting a brand-new single player game by letting the player
    # select which "story" (i.e. universe) they want to play.
    def handle_app_singleplayer_new_event(self, event, control_center, universe):

        # Events that might result from handling this event
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # The UniverseSelector object is going to need a Universe object tied to the current player session
        # to access last played data, if nothing else.  I'll create a dummy parallel universe here, based at random on the mainmenu levels...
        parallel_universe = Universe("mainmenu", MODE_GAME, self.control_center)


        # Create a universe selector for singleplayer universes.  Note that we're starting a new game (not resuming game).
        selector = UniverseSelector(show_singleplayer = True, show_multiplayer = False, resume_game = False)

        # Run the selector loop, saving the selection result.
        universe_name = selector.select(self.tilesheet_sprite, self.additional_sprites, self.control_center, parallel_universe)

        # Set up the window to fade back in
        self.window_controller.fade_in()


        # (?) See if we got a result
        if (universe_name):

            # Assume no last-second resume
            resume_last_autosave = False

            # If the string starts with "resume:" then the user chose to resume at the last minute.
            # Yes, this is a lousy hack.
            if ( universe_name.startswith("resume:") ):

                # Remove hacked-in prefix
                universe_name = universe_name.replace("resume:", "")

                # Doing it this way means I can never call a universe "resume:"
                # which is absolutely terrible!
                resume_last_autosave = True


            # Create the selected universe
            self.universe = Universe(universe_name, MODE_GAME, self.control_center)


            # If this universe allows individual level selection, we'll continue
            # to the level select screen.
            selectable_levels = self.universe.get_selectable_levels()

            # Selections available?
            if ( len(selectable_levels) > 0 ):

                # Create a parallel universe that we'll let the map selector play around with...
                parallel_universe = Universe(universe_name, MODE_GAME, self.control_center)

                # Configure the parallel universe to use a "dummy" session, preventing the game
                # from trying to create game over menus, etc...
                parallel_universe.get_session_variable("core.is-dummy-session").set_value("1")


                # Before we display the maps in the level select menu, let's load the single autosave slot
                # for the given universe, updating completion data to date.
                for universe in (self.universe, parallel_universe):

                    self.control_center.get_save_controller().load_from_folder(
                        os.path.join( self.universe.get_working_save_data_path(), "autosave1" ),
                        self.control_center,
                        universe
                    )


                # Register parallel universe as a gif universe for preview purposes
                parallel_universe.get_session_variable("core.is-gif").set_value("1")


                # Create a map selector screen for the selected universe
                map_selector = MapSelector(self.control_center, parallel_universe)


                # Wait for the user to select a level
                map_name = map_selector.select(self.tilesheet_sprite, self.additional_sprites, self.control_center, parallel_universe)


                # Did the user select a level?
                while (map_name):

                    # Re-create the selected universe
                    self.universe = Universe(universe_name, MODE_GAME, self.control_center)

                    # We have to reload autosave data (all data is autosaved in linear universes)
                    self.control_center.get_save_controller().load_from_folder(
                        os.path.join( self.universe.get_working_save_data_path(), "autosave1" ),
                        self.control_center,
                        self.universe
                    )


                    # Set up the window to fade back in
                    self.window_controller.fade_in()

                    # Activate the given map, and only the given map.
                    self.universe.activate_map_on_layer_by_name(map_name, LAYER_FOREGROUND, MODE_GAME, self.control_center, ignore_adjacent_maps = True)


                    # Immediately center the camera on the selected map
                    self.universe.get_active_map().center_camera_on_entity_by_name( self.universe.get_camera(), "player1", zap = True )


                    # Clear any menu that was left on screen.
                    # The stupid map selector stuff might have tried to create some game over menu or something.
                    self.menu_controller.clear()

                    # Make sure the menu controller is no longer pause locked
                    self.menu_controller.configure({
                        "pause-locked": False
                    })


                    # Before we get into the game, let's quickly note the current date
                    # for the "last played" metric.
                    self.universe.update_last_played_date()


                    # Begin the level
                    self.run()
                    #print "Let's load '%s'" % map_name
                    #print 5/0


                    # Clear any menu that was left on screen
                    self.menu_controller.clear()

                    # Make sure the menu controller is no longer pause locked
                    self.menu_controller.configure({
                        "pause-locked": False
                    })


                    # Set up the window to fade back in
                    self.window_controller.fade_in()


                    # Before re-creating the map selector, we have to update the "parallel" universe's autosave data
                    # in case the user just completed one or more levels.
                    self.control_center.get_save_controller().load_from_folder(
                        os.path.join( self.universe.get_working_save_data_path(), "autosave1" ),
                        self.control_center,
                        parallel_universe
                    )

                    # Re-create the map selector to (hackily) refresh any completion status data.
                    map_selector = MapSelector(self.control_center, parallel_universe)

                    # See if the user wants to select another level.
                    # Note that we default the last-selected map for convenience.
                    map_name = map_selector.select(self.tilesheet_sprite, self.additional_sprites, self.control_center, parallel_universe, map_name)

                # No.  Let's go back to the universe selector
                else:

                    logn( "app debug", "Returning to universe selector..." )


            # No; we shall begin the game immediately, then!
            else:

                # Before we get into the game, let's quickly note the current date
                # for the "last played" metric.
                self.universe.update_last_played_date()


                # We also need to load in any previously unlocked achievements so that they appear as "Complete" on the in-game achievements list...
                self.control_center.load_unlocked_achievements(self.universe)


                # Did the user choose to resume game on the warning widget?
                if (resume_last_autosave):

                    # Load the autosave
                    self.control_center.get_save_controller().load_from_folder(
                        os.path.join( self.universe.get_working_save_data_path(), "autosave1" ),
                        self.control_center,
                        self.universe
                    )


                # Here we go!
                self.run()


                # Rebuild the main menu in case the character leveled up (the resume game tooltip
                # would therefore change).  Only required after storyline mode level sets.
                self.game_menu.refresh_pages(self.control_center, self.universe)


            # Clear any menu that was left on screen
            self.menu_controller.clear()

            # Make sure the menu controller is no longer pause locked
            self.menu_controller.configure({
                "pause-locked": False
            })


            # Set up the window to fade back in
            self.window_controller.fade_in()

        # **debug ... handle a "cancel" option or whatever here?
        #else:
        #    log2( "No support for cancel" )
        #    print 5/0


        # Return resultant events
        return results


    # Resume the last story mode adventure
    def handle_app_singleplayer_continue_event(self, event, control_center, universe):

        # Events that might result from handling this event
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Get the path to the "last played" info file
        path = os.path.join(CONFIG_PATH, "lastplayed.xml")

        # Validate
        if ( os.path.exists(path) ):

            # Create node from file
            root = XMLParser().create_node_from_file(path)

            # Validate
            if (root):

                # Find universe name and save slot nodes
                (ref_universe_name, ref_save_path) = (
                    root.find_node_by_tag("universe"),
                    root.find_node_by_tag("save")
                )

                # Validate both nodes exist
                if ( (ref_universe_name != None) and (ref_save_path != None) ):

                    # Read string data
                    (name, save_path) = (
                        ref_universe_name.innerText,
                        ref_save_path.innerText
                    )

                    # We have to validate the universe and save path as well
                    if (
                        os.path.exists( os.path.join(UNIVERSES_PATH, name) ) and
                        os.path.exists(save_path)
                    ):

                        # At last, create the selected universe
                        self.universe = Universe(name, MODE_GAME, self.control_center)

                        # Load from the given save path
                        self.control_center.get_save_controller().load_from_folder(
                            save_path,
                            self.control_center,
                            self.universe
                        )


                        # Before we get into the game, let's quickly note the current date
                        # for the "last played" metric.
                        self.universe.update_last_played_date()


                        # We also need to load in any previously unlocked achievements so that they appear as "Complete" on the in-game achievements list...
                        self.control_center.load_unlocked_achievements(self.universe)


                        # Here we go!
                        self.run()


                        # Rebuild the main menu in case the character leveled up (the resume game tooltip
                        # would therefore change).  Only required after storyline mode level sets.
                        self.game_menu.refresh_pages(self.control_center, self.universe)
                        """
                        widget = self.game_menu.get_widget_by_id("mainmenu.root.story").find_widget_by_id("continue-game")

                        if (widget):
                            pass
                            #widget.get_tooltip().find_widget_by_id("player-name").set_text("UPDATED!")
                        else:
                            logn( "app error", "continue game tooltip widget not found" )
                            sys.exit()
                        """

                        # Clear any menu that was left on screen
                        self.menu_controller.clear()

                        # Make sure the menu controller is no longer pause locked
                        self.menu_controller.configure({
                            "pause-locked": False
                        })


        # Return resultant events
        return results


    # Begin the process of hosting a cooperative game by allowing the player to select
    # a level set to play on.
    def handle_app_coop_server_event(self, event, control_center, universe):

        # Events that might result from handling this event
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # The UniverseSelector object is going to need a Universe object tied to the current player session
        # to access last played data, if nothing else.  I'll create a dummy parallel universe here, based at random on the mainmenu levels...
        parallel_universe = Universe("mainmenu", MODE_GAME, self.control_center)


        # Create a universe selector for multiplayer universes.  Note that we're starting a new game; you can't
        # save/resume games in multiplayer, anyway.
        selector = UniverseSelector(show_singleplayer = False, show_multiplayer = True, resume_game = False)

        # Run the selector loop, saving the selection result.
        universe_name = selector.select(self.tilesheet_sprite, self.additional_sprites, self.control_center, parallel_universe)


        # Set up the window to fade back in after making a level set decision
        self.window_controller.fade_in()

        # Did we choose an option?
        if (universe_name):

            # Create and load the universe data for the player's selection
            self.universe = Universe(universe_name, MODE_GAME, self.control_center)


            # Having selected a universe to play on, we will raise an event to shepherd the player
            # to the session setup page, where they can set the password, max players, etc.
            results.add(
                "app:coop-select-level"#setup-session"
            )


        # Return resultant events
        return results


    # Continue the process of starting (hosting) a new cooperative game
    # by allowing the player to select a specific level to play on.
    # Note that we're using self.universe within this handler; the player has by this point selected a universe.
    def handle_app_coop_select_level_event(self, event, control_center):

        # Resultant events
        results = EventQueue()


        # Create a parallel universe that we'll let the map selector play around with...
        parallel_universe = Universe(
            self.universe.get_name(), MODE_GAME, self.control_center
        )

        # Configure the parallel universe to use a "dummy" session, preventing the game
        # from trying to create game over menus, etc...
        parallel_universe.get_session_variable("core.is-dummy-session").set_value("1")


        # If this universe allows individual level selection, we'll continue
        # to the level select screen.
        selectable_levels = self.universe.get_selectable_levels()

        # Selections available?
        if ( len(selectable_levels) > 0 ):

            # Before we display the maps in the level select menu, let's load the single autosave slot
            # for the given universe, updating completion data to date.
            for universe in (self.universe, parallel_universe):

                self.control_center.get_save_controller().load_from_folder(
                    os.path.join( self.universe.get_working_save_data_path(), "autosave1" ),
                    self.control_center,
                    universe
                )


            # Create a map selector screen for the selected universe
            map_selector = MapSelector(control_center, parallel_universe)

            # Wait for the user to select a level
            map_name = map_selector.select(self.tilesheet_sprite, self.additional_sprites, control_center, parallel_universe)

            # Did the player select a level?
            if (map_name):

                # Activate the selected map within the universe
                m = self.universe.activate_map_on_layer_by_name(
                    map_name,
                    layer = LAYER_FOREGROUND,
                    game_mode = MODE_GAME,
                    control_center = control_center,
                    ignore_adjacent_maps = True
                )

                # Validate that we activated a map
                if (m):

                    # Center the camera on the selected map
                    m.center_camera_on_entity_by_name( self.universe.get_camera(), "player1", zap = True )


                # Continue to the session setup screen
                results.add(
                    "app:coop-setup-session"
                )

                # Window fade back in
                self.window_controller.fade_in()

            # If not, just fade the window controller back in...
            else:

                # Window fade back in
                self.window_controller.fade_in()



        # If this universe has no defined level selections, then we'll skip immediately to the session configuration screen.
        else:

            results.append(
                self.handle_app_coop_setup_session_event(event, control_center)
            )



        # Return events
        return results

    # After a potential server selects a level set to play on, we'll give them a quick
    # setup screen.  They can elect to set a password or change the player limit for the game session.
    def handle_app_coop_setup_session_event(self, event, control_center):

        # Events that might result from handling this event
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Clear menu controller
        control_center.get_menu_controller().clear()

        # Add a session setup menu to the top of the menu controller
        control_center.get_menu_controller().add(
            control_center.get_widget_dispatcher().create_net_session_setup()
        )

        # Default the net player limit to the selected universe's max player count
        self.universe.set_session_variable( "net.player-limit", "%s" % self.universe.get_max_players() )


        # We'll pass the redirect page an empty timer controller; setup responds only to direct user input, not to any timed / polled event.
        timer_controller = TimerController()


        if ( self.redirect_using_timer_controller(timer_controller) ):

            # Clear any existing menu controller
            self.menu_controller.clear()

            # Raise a "begin session" event; we're ready to launch the server now!
            results.add(
                "app:coop-start-session"
            )

        # If the would-be host decides to back out, we'll just clear the menu controller and get back to the menu
        else:

            # Clear!
            self.menu_controller.clear()


        # Return resultant events
        return results


    # Start a new co-op session (as the server).
    def handle_app_coop_start_session_event(self, event, control_center):

        # Events that might result from handling this event
        results = EventQueue()

        # Convenience
        params = event.get_params()


        if (1):

            # Start at default port
            port = self.network_controller.get_default_port()

            # Try to create a server at that port
            result = self.network_controller.start_server(port = port)

            # Try a few more ports
            while ( (not result) and (port <= self.network_controller.get_default_port() + 10) ):

                # Next port
                port += 1

                # See if this one worked
                result = self.network_controller.start_server(port = port)


            # Check to see if we successfully launched a server.
            # If we did, we'll move on ... uh, we still need to configure server options like max players.**
            if (result):

                # **Temp universe setup
                #self.universe = Universe(universe_name, self.control_center)


                # Track the chosen port as a session variable.
                # The "new session request" callback will need to reference it.
                self.universe.get_session_variable("net.port").set_value(port)

                # Server is local.  Flag as joined!
                self.universe.set_session_variable("net.player1.joined", "1")


                # Just before launching the new game, let's reload any previous netplay settings (nick, avatar, etc.?)
                self.control_center.load_netplay_preferences(self.universe)


                # Clear any menu that was left on the screen;
                # we're going to send a "new session" request to the server and wait for its completion.
                self.menu_controller.clear()


                # After we leave the netplay session, we should tell every client that we've decided to disconnect.
                # Create a timer controller that will listen for confirmation; after the clients have all responded,
                # we'll get on back to the main menu.
                timer_controller = TimerController()

                # Add the "you know we're gone now?" checker
                timer_controller.add_repeating_event_with_name("listen-for-confirm-new-session", interval = 15, uses = -1, on_complete = "app:listen-for-confirm-new-session") # Infinite timer


                # Create the idle menu that will let the user know they're disconnecting.
                # When the idle menu fades in, fire off the network quit message...
                idle_menu = self.widget_dispatcher.create_idle_menu().configure({
                    "id": "redirect",
                    "title": self.control_center.get_localization_controller().get_label("creating-session:title"),
                    "message": self.control_center.get_localization_controller().get_label("creating-session:message"),
                    "on-build": "app:send-new-session-request"          # Raise an app-level event when we finish building the idle menu
                })

                # Add the idle menu.
                self.menu_controller.add(idle_menu)


                # Hit the transition screen one last time
                if ( not self.redirect_using_timer_controller(timer_controller) ):

                    # Abort "start new game" attempt
                    log2( "Cannot create new session..." )


                    # Clear any menu that was left on screen
                    self.menu_controller.clear()

                    # Make sure the menu controller is no longer pause locked
                    self.menu_controller.configure({
                        "pause-locked": False
                    })


                    # Flag session as offline
                    self.universe.set_session_variable("net.online", "0")

                    # set network status to offline
                    self.control_center.get_network_controller().set_status(NET_STATUS_OFFLINE)


                    # Abort function
                    return results


                # Clear menu controller
                self.menu_controller.clear()


                # Add the initial lobby menu
                self.menu_controller.add(
                    self.widget_dispatcher.create_net_lobby()
                )


                # Post a notice that we successfully launched the server
                self.window_controller.get_newsfeeder().post({
                    "type": NEWS_GAME_GAMEPAD_REMEMBERED,
                    "title": self.control_center.get_localization_controller().get_label("server-online:title"),
                    "content": self.control_center.get_localization_controller().get_label("server-online:message")
                })


                # Flag session as online
                self.universe.set_session_variable("net.online", "1")


                # Once in a while we'll send out a ping message.
                # Currently this is just for debugging.
                self.universe.get_timer_controller().add_repeating_event_with_name(
                    name = "server-ping-timer",
                    interval = 15 * 60, # (n * 60) means n seconds per
                    uses = -1,
                    on_complete = "network:ping"
                )


                # At regular intervals, the server should update all clients' enemy AI data,
                # to keep all of the bad guys in sync across all players.
                self.universe.get_timer_controller().add_repeating_event_with_name(
                    name = "server-ai-sync-timer",
                    interval = 45, # 0.75s (60fps)
                    uses = -1,
                    on_complete = "server:sync-ai"
                )

                # Also at regular intervals, the server should update its local player data
                # to all clients.
                self.universe.get_timer_controller().add_repeating_event_with_name(
                    name = "sync-local-player",
                    interval = 60,
                    uses = -1,
                    on_complete = "network:sync-local-player"
                )


                # Periodically, the host should ping the web server to "validate" that this
                # session is still active (and thus should appear in the lobby browser).
                # We'll do this by requesting a player update every 5 minutes.
                self.universe.get_timer_controller().add_repeating_event_with_name(
                    name = "ping-web-server",
                    interval = 60 * 60 * 3, # Every 3 minutes
                    uses = -1,              # Unlimited
                    on_complete = "server:ping-web-server"
                )


                # Before we get into the game, let's quickly note the current date
                # for the "last played" metric.
                self.universe.update_last_played_date()

                # Game time!
                self.run()


                # When the server finishes running game logic, that player should end the "sync AI" timer.
                self.universe.get_timer_controller().remove_timer_by_name("server-ai-sync-timer")


                # Clear any menu that was left on the screen
                self.menu_controller.clear()


                # After we leave the netplay session, we should tell every client that we've decided to disconnect.
                # Create a timer controller that will listen for confirmation; after the clients have all responded,
                # we'll get on back to the main menu.
                timer_controller = TimerController()

                # Add the "you know we're gone now?" checker
                timer_controller.add_repeating_event_with_name("listen-for-confirm-disconnect", interval = 15, uses = -1, on_complete = "app:listen-for-confirm-disconnect") # Infinite timer


                # Create the idle menu that will let the user know they're disconnecting.
                # When the idle menu fades in, fire off the network quit message...
                idle_menu = self.widget_dispatcher.create_idle_menu().configure({
                    "id": "redirect",
                    "title": self.control_center.get_localization_controller().get_label("ending-session:title"),
                    "message": self.control_center.get_localization_controller().get_label("ending-session:message"),
                    "on-build": "app:send-disconnect-notice"          # Raise an app-level event when we finish building the idle menu
                })

                # Add the idle menu.
                self.menu_controller.add(idle_menu)


                # Hit the transition screen one last time
                if ( self.redirect_using_timer_controller(timer_controller, max_time_in_seconds = 5) ):

                    #print 5/0 #**?
                    log2( "Ending server session..." )


                    # Disconnect server
                    self.network_controller.disconnect()

                else:

                    #print 10/0 #**?
                    pass


                # Flag session as offline
                self.universe.set_session_variable("net.online", "0")

                # set network status to offline
                self.control_center.get_network_controller().set_status(NET_STATUS_OFFLINE)


                # Clear any menu that was left on screen
                self.menu_controller.clear()

                # Make sure the menu controller is no longer pause locked
                self.menu_controller.configure({
                    "pause-locked": False
                })


        # Return resultant events
        return results


    # This callback simply sends a new session (http) request
    def handle_app_send_new_session_request_event(self, event, control_center):

        # Announce to the webserver that we've started a session.
        control_center.get_http_request_controller().send_get_with_name(
            name = "new-session-request",
            host = None, # use default
            port = 80,
            url = "/games/alrs/sessions/new.php",
            params = {
                "port": self.universe.get_session_variable("net.port").get_value(),
                "password": self.universe.get_session_variable("net.password").get_value(),
                "server-name": self.universe.get_session_variable("net.player1.nick").get_value(),
                "max-players": self.universe.get_session_variable("net.player-limit").get_value(),
                "universe-name": self.universe.get_name(),
                "universe-version": self.universe.get_version(),
                "universe-title": self.universe.get_title(),
                "current-level": self.universe.get_map_data( self.universe.get_active_map().get_name() ).get_title()
            }
        )


    # This callback periodically checks for server confirmation of a new session.
    # Receives the ID of the new session so that the server can update player count, etc. in real time.
    def handle_app_listen_for_confirm_new_session_event(self, event, control_center):

        # Fetch the network controller
        network_controller = control_center.get_network_controller()


        # Only the server should be listening for ID via this callback.
        if ( network_controller.get_status() == NET_STATUS_SERVER ):

            # We need to process the http request controller to poll for http data
            control_center.get_http_request_controller().process()

            # Let's peek at the current response data.  We don't want to remove it from the controller,
            # but we do need to look at the data to determine whether or not our request validated properly.
            data = control_center.get_http_request_controller().peek_response_by_request_name("new-session-request")

            # Once we get data back, we end the current redirect.
            if (data != None):

                # Parse the xml response from the server
                root = XMLParser().create_node_from_xml(data)

                log(
                    root.compile_xml_string()   # Debug
                )

                # Did we get a session ID for the new session?
                ref_session = root.find_node_by_tag("session")

                # Perhaps we got an error response?
                ref_error = root.find_node_by_tag("error")


                # Validate
                if (ref_session):

                    # Track the new session ID.  We have already instantiated the new universe at this point.
                    self.universe.get_session_variable("net.session.id").set_value(ref_session.innerText)

                    # At this point, we have all of the data we need.  We left the request alive for the time being.
                    # Let's call for an app fade, raising a "redirect succeeded" event afterward to indicate that we
                    # successfully created a new game and received the new session ID.
                    control_center.get_window_controller().fade_out(
                        on_complete = "app:redirect.success"
                    )

                # If we didn't get connection data back, we must have gotten some sort of error (perhaps an expired session or a bad password).
                elif (ref_error):

                    # For now, let's just add a simple newsfeeder notice with the given error
                    control_center.get_window_controller().get_newsfeeder().post({
                        "type": NEWS_GENERIC_ITEM,
                        "title": self.control_center.get_localization_controller().get_label("error-creating-session:title"),
                        "content": ref_error.innerText
                    })

                    # Abort
                    control_center.get_window_controller().fade_out(
                        on_complete = "app:redirect.fail"
                    )

                # Generic, unknown error
                else:

                    # For now, let's just add a simple newsfeeder notice with the given error
                    control_center.get_window_controller().get_newsfeeder().post({
                        "type": NEWS_GENERIC_ITEM,
                        "title": self.control_center.get_localization_controller().get_label("error-creating-session:title"),
                        "content": self.control_center.get_localization_controller().get_label("error-creating-session:message:generic")
                    })

                    # Abort
                    control_center.get_window_controller().fade_out(
                        on_complete = "app:redirect.fail"
                    )


                # In this case, always end the request as we've finished parsing its data.
                control_center.get_http_request_controller().end_request_by_name("new-session-request")


    # Begin the processing of joining a cooperative game by sending a request for available sessions,
    # then displaying a session browser (even if it just says "no games found").
    def handle_app_coop_client_event(self, event, control_center, universe):

        # Events that might result from handling this event
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Create a transient timer controller; we'll feed it to the redirect screen.
        timer_controller = TimerController()

        # Periodically run the http request controller and check on the status of the web request we just sent
        timer_controller.add_repeating_event_with_name("listen-for-coop-sessions", interval = 15, uses = -1, on_complete = "app:listen-for-coop-sessions")




        # Create an idle menu informing the user that we're trying to connect to a game now.
        # Fire off a "ask for active co-op sessions" event when it's faded in.
        idle_menu = self.widget_dispatcher.create_idle_menu().configure({
            "id": "redirect",
            "title": self.control_center.get_localization_controller().get_label("searching-games:title"),
            "message": self.control_center.get_localization_controller().get_label("searching-games:message"),
            "on-build": "app:get-coop-sessions"          # Raise an app-level event when we finish building the idle menu
        })

        # Add the idle menu.
        self.menu_controller.add(idle_menu)


        # Hit the redirect screen, checking every so often to see if we've gotten the list of sessions yet.
        # Once we receive that list, we can transition onward, listing those sessions for the user...
        if ( self.redirect_using_timer_controller(timer_controller) ):

            # Clear any existing menu controller
            self.menu_controller.clear()

            # Our request for the coop session listing succeeded.  Now let's raise an event
            # that will carry us forward to another transition screen:  the listing of all active sessions.
            # Note that we haven't yet fetched the server's response data; we've only verified that it has returned the data.
            results.add(
                "app:list-coop-sessions"
            )

        # On abort, we'll just clear the menu controller and return to the menu
        else:

            # Clear!
            self.menu_controller.clear()


        # Return resultant events
        return results


    # Create a menu widget that lists all of the available co-op mode sessions, add it to the menu controller,
    # then jump back into the redirect transition page, allowing the player to select a game to join.
    def handle_app_list_coop_sessions_event(self, event, control_center):

        # Events that might result from handling this event
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Before we get started, let's fetch the data we got back from the server...
        xml = control_center.get_http_request_controller().fetch_response_by_request_name("browse-coop-sessions")

        # Add the session browser to the top of the menu controller
        control_center.get_menu_controller().add(
            control_center.get_widget_dispatcher().create_net_session_browser().configure({
                "id": "net-session-browser",
                "http-data": xml
            })
        )


        # While we're on the list sessions page, we'll set up a timer that checks for connection responses.
        # If the player tries to join a game, we'll send a request to the webserver asking for connection details;
        # we'll attach a timer to this controller that checks for responses to those potential requests.
        timer_controller = TimerController()

        # This timer will typically have no relevance; it only has a purpose once the player selects a game to join.
        timer_controller.add_repeating_event_with_name("listen-for-coop-connection-data", interval = 15, uses = -1, on_complete = "app:listen-for-coop-connection-data")


        if ( self.redirect_using_timer_controller(timer_controller) ):

            # Clear any existing menu controller
            self.menu_controller.clear()

            # Returning success from the redirect to the session browser indicates
            # that the player selected a game to join and successfully received connection data.
            # At this point, let's go ahead and parse the web response, parse out of the host and port data.
            data = control_center.get_http_request_controller().fetch_response_by_request_name("join-coop-session") # Remove it from the controller

            # Compile data into an xml node
            node = XMLParser().create_node_from_xml(data)

            # Fetch the host and port data
            (host, port) = (
                node.find_node_by_tag("host").innerText,
                node.find_node_by_tag("port").innerText
            )
            logn( "app debug", "(host, port) = ", (host, port) )


            # Here, we'll raise an event that will take the next step:  attempting to connect using that connection data.
            results.add(
                action = "app:connect-to-coop-session",
                params = {
                    "host": host,
                    "port": port,
                    "universe-name": node.find_node_by_tag("universe-name").innerText,
                    "max-players": node.find_node_by_tag("max-players").innerText
                }
            )

        # If the player backed out without selecting a game, just clear the menu controller
        else:

            # Back to menu!
            self.menu_controller.clear()


        # Return resultant events
        return results


    # Create a new universe by its name.
    # Currently I only do this when using the dev-only -record argument.
    def create_universe_by_name(self, name):

        # Try to create universe object
        try:
            self.universe = Universe( name, self.game_mode, self.control_center )

        except:
            logn( "error", "Universe '%s' does not exist.  Possible misuse of --edit argument." % name )


    # Check to see which version, if any, the user has of a given universe by name
    def check_universe_version(self, name):

        # Generate path for universe's meta file
        path = os.path.join(UNIVERSES_PATH, name, "meta.xml")


        # Validate
        if ( os.path.exists(path) ):

            # Read in the xml data, then search for the version tag
            ref_version = XMLParser().create_node_from_file(path).find_node_by_tag("version")

            # Validate
            if (ref_version):

                # Return version string
                return ref_version.innerText


        # Version not found
        return None


    # When the player selects a game to join, we might need to get a password from the user.
    # If we do, we'll give them a keyboard to let them enter the password.  If not, we'll
    # immediately query the server for the data we need to connect try to connect to the session.
    def handle_app_join_coop_session_event(self, event, control_center):

        # Events that might result from handling this event
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # If the game requires a password, let's give the player a keyboard...
        if (False):

            pass

        # If not, we will send a web request to get connection details
        else:

            # Get a handle to the net session browser menu
            browser = control_center.get_menu_controller().get_menu_by_id("net-session-browser")

            # Validate
            if (browser):

                # Find the widget with the id of "menu" on the current page (should only be one page)
                widget = browser.get_active_page()

                # Validate
                if (widget):

                    # Get active selection
                    active_widget = widget.find_widget_by_id("submenu").get_active_widget()

                    # Validate
                    if (active_widget):

                        # Find the hidden widgets that contains the universe name / title that we need to load (which universe did the host launch?)
                        (ref_name, ref_version, ref_title) = (
                            active_widget.find_widget_by_id("universe-name"),
                            active_widget.find_widget_by_id("universe-version"),
                            active_widget.find_widget_by_id("universe-title")
                        )

                        # Validate
                        if ( (ref_name != None) and (ref_version != None) and (ref_title != None) ):

                            # Get universe name, version, and title from the rel attribute
                            (name, version, title) = (
                                ref_name.get_rel(),
                                ref_version.get_rel(),
                                ref_title.get_rel()
                            )

                            logn( "http app", "%s / %s Join universe:  %s (%s)\n" % (widget, active_widget, name, title + " " + version) )

                            # Check the existing version of the selected universe.
                            existing_version = self.check_universe_version(name)

                            # If this connecting player has never downloaded the universe, they cannot join
                            if (existing_version == None):

                                # Show error
                                browser.fire_event(
                                    "show:message",
                                    {
                                        "message":  control_center.get_localization_controller().get_label("not-downloaded-n:message", { "@n": title })
                                    }
                                )

                            # If the connecting player does not have the same release version, we'll prevent joining
                            elif (existing_version != version):

                                # Show error
                                browser.fire_event(
                                    "show:message",
                                    {
                                        "message":  control_center.get_localization_controller().get_label("not-updated-n:message", { "@n": title, "@v1": existing_version, "@v2": version })
                                    }
                                )

                            # Validate that the user has downloaded the given universe
                            elif (
                                os.path.exists( os.path.join(UNIVERSES_PATH, name) )
                            ):

                                # Now we can try to connect
                                control_center.get_http_request_controller().send_get_with_name(
                                    name = "join-coop-session",
                                    host = None, # use default
                                    port = 80,
                                    url = "/games/alrs/sessions/connect.php",
                                    params = {
                                        "session-id": params["session-id"],
                                        "session-password": params["session-password"]
                                    }
                                )

                            # If the user hasn't downloaded this universe, raise a show-message event on the session browser
                            # telling them that they need to download the universe before joining this game.
                            else:

                                browser.fire_event(
                                    "show:message",
                                    {
                                        "message": control_center.get_localization_controller().get_label("not-downloaded-n:message", { "@n": title })
                                    }
                                )

                # Game listing (rowmenu) not found
                else:
                    logn( "app error", "Aborting:  game listing widget not found!" )
                    sys.exit()

            # No browser found
            else:
                logn( "app error", "Aborting:  session browser not found!" )
                sys.exit()

        # Return resultant events
        return results


    # When the player decides to join a co-op session, we'll send a request to the webserver
    # asking for connection details (pending password approval, perhaps).  This callback will
    # monitor for a response to the "join-coop-session" web request, meaning it only runs logic
    # in response to the player sending a join request.
    def handle_app_listen_for_coop_connection_data_event(self, event, control_center):

        # Events that might result from handling this event
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # We need to process the http request controller to poll for http data
        control_center.get_http_request_controller().process()

        # Let's peek at the current response data.  We don't want to remove it from the controller,
        # but we do need to look at the data to determine whether or not our request validated properly.
        data = control_center.get_http_request_controller().peek_response_by_request_name("join-coop-session")

        # Usually we won't do anything more.  If the user tries to join a game, though, we should eventually get data back...
        if (data != None):

            # Parse the xml response from the server
            root = XMLParser().create_node_from_xml(data)

            log(
                root.compile_xml_string()   # Debug
            )

            # Did we get connection data for the desired session?
            ref_session = root.find_node_by_tag("session")

            # Perhaps we got an error response?
            ref_error = root.find_node_by_tag("error")


            # Validate
            if (ref_session):

                # At this point, we have all of the data we need.  We left the request alive for the time being.
                # Let's call for an app fade, raising a "redirect succeeded" event afterward to indicate that we
                # selected a game to join and received connection data successfully (pending as a web request).
                control_center.get_window_controller().fade_out(
                    on_complete = "app:redirect.success"
                )
                #print 5/0 #**

            # If we didn't get connection data back, we must have gotten some sort of error (perhaps an expired session or a bad password).
            elif (ref_error):

                # For now, let's just add a simple newsfeeder notice with the given error
                control_center.get_window_controller().get_newsfeeder().post({
                    "type": NEWS_GENERIC_ITEM,
                    "title": self.control_center.get_localization_controller().get_label("error-joining-session:title"),
                    "content": ref_error.innerText
                })

                # We won't be needing the request after all (because we're not connecting)
                control_center.get_http_request_controller().end_request_by_name("join-coop-session")

            # Generic, unknown error
            else:

                # For now, let's just add a simple newsfeeder notice with the given error
                control_center.get_window_controller().get_newsfeeder().post({
                    "type": NEWS_GENERIC_ITEM,
                    "title": self.control_center.get_localization_controller().get_label("error-joining-session:title"),
                    "content": self.control_center.get_localization_controller().get_label("error-joining-session:message:generic")
                })

                # We won't be needing the request after all (because we're not connecting)
                control_center.get_http_request_controller().end_request_by_name("join-coop-session")


        # Return resultant events
        return results


    # Attempt to physically connect to a co-op session
    def handle_app_connect_to_coop_session_event(self, event, control_center):

        # Events that might result from handling this event
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Create a new universe object using the provided universe name
        self.universe = Universe( params["universe-name"], MODE_GAME, self.control_center )

        if (1):
            # Load in existing level completion data for the given universe name
            control_center.get_save_controller().load_from_folder(
                os.path.join( self.universe.get_working_save_data_path(), "autosave1" ),
                control_center,
                self.universe
            )


        # Update the player limit session variable according to the server's preference.
        # We've already instantiated the universe at this time?
        self.universe.get_session_variable("net.player-limit").set_value( params["max-players"] )


        # Fade app in
        self.window_controller.fade_in()


        # Create a temporary timer controller.  We'll configure it to periodically fire a "did we receive our player id yet?" event.
        timer_controller = TimerController().configure({
            "delay": 100
        })

        if (0):
            timer_controller.add_singular_event_with_name(
                "send-connection-request",
                interval = 100,
                on_complete = "app:send-connection-request",
                params = {
                    "host": params["host"],
                    "port": params["port"]
                }
            )

        # Add the "are we there yet?" checker
        timer_controller.add_repeating_event_with_name("listen-for-player-id", interval = 15, uses = -1, on_complete = "app:listen-for-player-id") # Infinite timer



        log2( "Sending connection request..." )
        logn( "app debug", params )

        result = self.network_controller.start_client(
            params["host"],
            int( params["port"] )
        )


        # Error check
        if (not result):

            # Give the player a brief error message
            idle_menu = self.widget_dispatcher.create_idle_menu().configure({
                "id": "redirect",
                "title": self.control_center.get_localization_controller().get_label("join-failed:title"),
                "message": self.control_center.get_localization_controller().get_label("join-failed:message")
            })

            # Add the idle menu.
            self.menu_controller.add(idle_menu)


            # Run a redirect, but
            # note that we don't care if it succeeds or fails.
            self.redirect_using_timer_controller(
                TimerController(), # Unused
                max_time_in_seconds = 2.5 # Short-lived error display that the user can cancel away
            )


            # Now we clear off the idle menu and return to the menu (?)
            self.menu_controller.clear()

            results.add(
                action = "app:multiplayer.browser"
            )

            #log2( "**couldn't connect on any port?" )
            #log2( 5/0 )

        # Client socket created successfully
        else:

            # Create an idle menu informing the user that we're trying to connect to a game now.
            # Fire off a "send connection request" event when the idle menu shows up.
            idle_menu = self.widget_dispatcher.create_idle_menu().configure({
                "id": "redirect",
                "title": self.control_center.get_localization_controller().get_label("joining-session:title"),
                "message": self.control_center.get_localization_controller().get_label("joining-session:message"),
                "xon-build": "app:send.connection.request"          # Raise an app-level event when we finish building the idle menu
            })

            # Add the idle menu.
            self.menu_controller.add(idle_menu)


            # For this redirect, we want to know the reason for failure.
            # We'll pass this hash to the redirect call.
            redirect_params = {}

            #  Attempt to connect to the session
            if ( self.redirect_using_timer_controller(timer_controller, output_params_hash = redirect_params) ):

                # Clear any existing menu controller
                self.menu_controller.clear()


                # Add a lobby menu
                self.menu_controller.add(
                    self.widget_dispatcher.create_net_lobby()
                )


                # Flag session as online
                self.universe.set_session_variable("net.online", "1")


                # At regular intervals, the client should update its local player data to the server.
                # The server will forward this data to any other client.
                self.universe.get_timer_controller().add_repeating_event_with_name(
                    name = "sync-local-player",
                    interval = 60,
                    uses = -1,
                    on_complete = "network:sync-local-player"
                )


                # Before we get into the game, let's quickly note the current date
                # for the "last played" metric.
                self.universe.update_last_played_date()

                # Begin netplay session!
                self.run()


                # Clear any menu that was left on the screen
                self.menu_controller.clear()


                # If we're still online, that means the client instigated a disconnect.
                # At this point, then, we'll tell the server we're leaving.
                if ( int( self.universe.get_session_variable("net.online").get_value() ) == 1 ):

                    # After we leave the netplay session, we should tell the server that we've disconnected.
                    # Create a timer controller that will listen for confirmation; after the server lets us know
                    # it knows we're leaving, we'll get on back to the main menu.
                    timer_controller = TimerController()

                    # Add the "you know we're gone now?" checker
                    timer_controller.add_repeating_event_with_name("listen-for-confirm-disconnect", interval = 15, uses = -1, on_complete = "app:listen-for-confirm-disconnect") # Infinite timer


                    # Create the idle menu that will let the user know they're disconnecting.
                    # When the idle menu fades in, fire off the network quit message...
                    idle_menu = self.widget_dispatcher.create_idle_menu().configure({
                        "id": "redirect",
                        "title": self.control_center.get_localization_controller().get_label("leaving-session:title"),
                        "message": self.control_center.get_localization_controller().get_label("leaving-session:message"),
                        "on-build": "app:send-disconnect-notice"          # Raise an app-level event when we finish building the idle menu
                    })

                    # Add the idle menu.
                    self.menu_controller.add(idle_menu)


                    # Hit the transition screen one last time
                    if ( self.redirect_using_timer_controller(timer_controller) ):

                        #print 5/0 #**?
                        log2( "Exiting co-op session..." )

                    else:

                        #print 10/0 #**?
                        pass

                # Otherwise, we apparently lost connection to the server (timed out?).
                else:

                    # Create a transient timer controller
                    timer_controller = TimerController()

                    # Attach a simple single timer that raises a "succeed" event for the redirect screen after a moment.
                    timer_controller.add_singular_event_with_name("alert-net-timeout", interval = 180, on_complete = "app:escape-redirect")


                    # Create the idle menu that will let the player know what happened
                    idle_menu = self.widget_dispatcher.create_idle_menu().configure({
                        "id": "redirect",
                        "title": self.control_center.get_localization_controller().get_label("server-timeout:title"),
                        "message": self.control_center.get_localization_controller().get_label("server-timeout:message")
                    })

                    # Add the idle menu.
                    self.menu_controller.add(idle_menu)


                    # Run through the redirect screen with no care as to its result...
                    self.redirect_using_timer_controller(timer_controller)


                # Flag session as offline
                self.universe.set_session_variable("net.online", "0")

                # set network status to offline
                self.control_center.get_network_controller().set_status(NET_STATUS_OFFLINE)


            else:
                #log2( "**connection failed..." )
                #log2(10/0)
                #pass

                # Can we find a reason for this failure?
                reason = self.control_center.get_window_controller().get_param("last-network-error")

                # Validate
                if (reason != None):

                    # Clear menus
                    self.menu_controller.clear()

                    # Also clear the global param
                    self.control_center.get_window_controller().remove_param("last-network-error")


                    # Give the player the error message with generic title bar text
                    idle_menu = self.widget_dispatcher.create_idle_menu().configure({
                        "id": "redirect",
                        "title": self.control_center.get_localization_controller().get_label("notification:title"),
                        "message": reason
                    })

                    # Add the idle menu.
                    self.menu_controller.add(idle_menu)


                    # Run a brief redirect that does nothing different on success/fail.
                    self.redirect_using_timer_controller(
                        TimerController(), # Unused
                        max_time_in_seconds = 2.5 # Short-lived error display that the user can cancel away
                    )


                    # Redirect back to the session browser
                    results.add(
                        "app:multiplayer.browser"
                    )

                # No reason given
                else:
                    pass


            # Clear any menu that was left on the screen
            self.menu_controller.clear()

            # Make sure the menu controller is no longer pause locked
            self.menu_controller.configure({
                "pause-locked": False
            })



        # Return resultant events
        return results


    # Send out a request to connect to a netplay session on a remote machine
    def handle_app_send_connection_request_event(self, event, control_center):

        # Events that result from this event
        results = EventQueue()


        log2( "Sending connection request..." )

        port = self.network_controller.get_default_port()
        result = self.network_controller.start_client(port = port)

        while ( (not result) and (port <= self.network_controller.get_default_port() + 10) ):

            port += 1
            result = self.network_controller.start_client(port = port)

        if (not result):
            log2( "**couldn't connect on any port?" )
            log2( 5/0 )

        else:
            pass


        # Return events
        return results


    # Ask the webserver to send a list of active co-op game sessions.
    def handle_app_get_coop_sessions_event(self, event, control_center):

        # Events that might result from this event
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # We need to shoot out an http request to get a list of available co-op sessions.
        # A timer we previously established will monitor the status of this request, by name.
        control_center.get_http_request_controller().send_get_with_name(
            name = "browse-coop-sessions",
            host = None, # use default
            port = 80,
            url = "/games/alrs/sessions/browse.php"
        )


        # Return resultant events
        return results


    # After we send the web request to fetch active coop sessions, we will check in with the
    # named web request to see if it's completed yet.
    def handle_app_listen_for_coop_sessions_event(self, event, control_center):

        # We need to process the http request controller to poll for http data
        control_center.get_http_request_controller().process()

        # See if the request for coop sessions has completed.  When it's done, we'll want to transition onward
        # to the session browser page.  We won't actually fetch the request response (the http data) until we
        # reach that next screen.
        if ( control_center.get_http_request_controller().is_named_request_ready("browse-coop-sessions") ):

            # Get the current redirect idle menu
            idle_menu = control_center.get_menu_controller().get_menu_by_id("redirect")

            # Hide...
            idle_menu.get_active_page().hide(
                on_complete = "app:redirect.success"
            )

        else:
            log2("NOT READY???")


    # While attempting to join a netplay session, "listen" to see if we've received our player id (i.e. the server let us into the game).
    def handle_app_listen_for_player_id_event(self, event, control_center):

        # If we haven't received a player id, then have the universe check its commands.
        # Once we receive a player id, we can exit this .connect method and begin the game.
        received_player_id = ( int( self.universe.get_session_variable("core.received-player-id").get_value() ) == 1 )

        if (not received_player_id):

            # Check to see if the network controller has gone offline.
            # It will go offline if the server had no open slots.
            if ( not control_center.get_network_controller().is_active() ):

                # Get the current redirect idle menu
                idle_menu = control_center.get_menu_controller().get_menu_by_id("redirect")

                # Get its active page
                page1 = idle_menu.get_active_page()

                # Hide...
                page1.hide(
                    on_complete = "app:redirect.fail"
                )


                # This is a global hack.
                # Set a parameter on the window controller that explains the reason for failure.
                # We're assuming the server returned a "game full" message.
                control_center.get_window_controller().set_param( "last-network-error", control_center.get_localization_controller().get_label("server-full:message") )


            # Otherwise, peek at the network commands to see if we can find the player id...
            else:

                # Get just one command at a time
                command = control_center.get_network_controller().get_next_command()

                # Just one...
                if (command):

                    # Feed it to the universe
                    self.universe.process_network_command(command, control_center)


                    # Let's see if that commnad gave us a player id
                    received_player_id = ( int( self.universe.get_session_variable("core.received-player-id").get_value() ) == 1)

                    # If so, we can get on with the game
                    if (received_player_id):

                        # Flag success
                        success = True


                        # Get the current redirect idle menu
                        idle_menu = control_center.get_menu_controller().get_menu_by_id("redirect")

                        # Get its active page
                        page1 = idle_menu.get_active_page()

                        # Hide...
                        page1.hide(
                            on_complete = "app:redirect.success"
                        )


    # After leaving a netplay session, send a disconnect notice to the either the server
    # or each of the server's clients.
    def handle_app_send_disconnect_notice_event(self, event, control_center):

        # Fetch the network controller
        network_controller = control_center.get_network_controller()


        # The server does one thing
        if ( network_controller.get_status() == NET_STATUS_SERVER ):

            # Tell all of the clients that the server is disconnecting
            network_controller.send_server_disconnecting(control_center, self.universe)

        # The client does something different
        elif ( network_controller.get_status() == NET_STATUS_CLIENT ):

            # Declare ourself as the disconnecting client
            network_controller.send_client_disconnecting(
                int( self.universe.get_session_variable("core.player-id").get_value() ),
                control_center,
                self.universe
            )


    # Once we send a disconnect notice, the server will wait for each client to confirm,
    # and the client will ismply wait for theh server to confirm.
    def handle_app_listen_for_confirm_disconnect_event(self, event, control_center):

        # Fetch the network controller
        network_controller = control_center.get_network_controller()


        # If the server is still online, wait until we are out of active connections
        if ( network_controller.get_status() == NET_STATUS_SERVER ):

            # Get just one command at a time
            command = control_center.get_network_controller().get_next_command()

            # Just one...
            if (command):

                # Feed it to the universe
                self.universe.process_network_command(command, control_center)


            # If we have dropped all active connections, we can now disconnect the server
            # and fade back to the menu.
            if ( len( network_controller.get_active_connections() ) == 0 ):

                # Have we finished sending the "end session" request?
                if ( control_center.get_http_request_controller().is_named_request_ready("end-session") ):

                    # Explicitly end the "end session" request
                    control_center.get_http_request_controller().end_request_by_name("end-session")
                    logn( "http", "Safe to exit . . .\n" )


                    # Disconnect server
                    network_controller.disconnect()

                    # Flag session as offline
                    self.universe.set_session_variable("net.online", "0")


                    # App fade
                    self.window_controller.fade_out(
                        on_complete = "app:redirect.success"
                    )

                # If not, let's make sure we process the request controller to send it out...
                else:

                    # Process http controller to ensure the "end session" http gets out
                    control_center.get_http_request_controller().process()
                    logn( "http", "Processing . . .\n" )

        # If the thing is still not set to offline, let's keep processing net commands until it is...
        elif ( network_controller.get_status() == NET_STATUS_CLIENT ):

            # Get just one command at a time
            command = control_center.get_network_controller().get_next_command()

            # Just one...
            if (command):

                # Feed it to the universe
                self.universe.process_network_command(command, control_center)


                # If that network command finally confirmed our disconnect, then we can end the redirect phase.


                # Note that this will happen after one confirmation for the client, but the server will be
                # waiting for confirmation from all connected clients.
                if ( network_controller.get_status() == NET_STATUS_OFFLINE ):

                    """
                    # Get the current redirect idle menu
                    idle_menu = control_center.get_menu_controller().get_menu_by_id("redirect")

                    # Get its active page
                    page1 = idle_menu.get_active_page()

                    # Hide...
                    page1.hide(
                        on_complete = "app:redirect.success"
                    )
                    """

                    # Just app fade out
                    control_center.get_window_controller().fade_out(
                        on_complete = "app:redirect.success"            # Escape the redirect screen after fade completes
                    )
                    #control_center.

        # Make sure we're fading out if we're not online anymore
        else:

            control_center.get_window_controller().fade_out(
                on_complete = "app:redirect.success"            # Escape the redirect screen after fade completes
            )


    # When the user chooses to view dlc download options, we must begin by fetching the listing of
    # available dlc.  The listing will include a series of thumbnails we will need to fully render the listing.
    def handle_app_get_dlc_listing_event(self, event, control_center):

        # Events that might result from handling this event
        results = EventQueue()


        # Fade app in
        self.window_controller.fade_in()


        # Create a temporary timer controller.  We'll configure it to periodically fire a "did we receive our player id yet?" event.
        timer_controller = TimerController().configure({
            "delay": 50
        })


        # Send the request that we'll be listening for a response to...
        control_center.get_http_request_controller().send_get_with_name(
            name = "get-dlc-listing",
            host = None, # use default
            port = 80,
            url = "/games/alrs/dlc/dlc.listing.xml"
        )

        # If we cannot create a request at this time, redirect to an idle menu
        # with a "no connection" type of message and a max display duration.
        if ( not control_center.get_http_request_controller().get_request_by_name("get-dlc-listing").is_created() ):

            # Create an idle menu
            idle_menu = self.widget_dispatcher.create_idle_menu().configure({
                "id": "redirect",
                "title": self.control_center.get_localization_controller().get_label("download-listing-unavailable:title"),
                "message": self.control_center.get_localization_controller().get_label("download-listing-unavailable:message")
            })

            # Add idle menu
            self.menu_controller.add(idle_menu)


            # Redirect through the idle menu.  Ignore outcome; we'll always return to main menu
            if ( self.redirect_using_timer_controller(timer_controller, max_time_in_seconds = 5) ):
                pass


            # Clear menu stack
            self.menu_controller.clear()

            # App fade in
            self.window_controller.fade_in()


            # Return events (abort)
            return results
        """ End failure check """



        # Create an idle menu informing the user that we're trying to connect to a game now.
        # Fire off a "send connection request" event when the idle menu shows up.
        idle_menu = self.widget_dispatcher.create_idle_menu().configure({
            "id": "redirect",
            "title": self.control_center.get_localization_controller().get_label("searching-dlc:title"),
            "message": self.control_center.get_localization_controller().get_label("searching-dlc:message")#,
            #"xon-build": "app:get-dlc-"          # Raise an app-level event when we finish building the idle menu
        })

        # Add the idle menu.
        self.menu_controller.add(idle_menu)


        # Add the "are we there yet?" checker
        timer_controller.add_repeating_event_with_name("listen-for-dlc-listing", interval = 1, uses = -1, on_complete = "app:listen-for-dlc-listing") # Infinite timer

        #  Attempt to connect to the session
        if ( self.redirect_using_timer_controller(timer_controller) ):

            # Clear any existing menu controller
            self.menu_controller.clear()


            # Fetch (and thereby remove the tracked request) the response data we got for the dlc listing
            xml = control_center.get_http_request_controller().fetch_response_by_request_name("get-dlc-listing")

            # Compile the response into an xml node
            node = XMLParser().create_node_from_xml(xml)

            # Validate node / xml
            if (node):

                # We only care about the node that lists the downloads
                ref_downloads = node.find_node_by_tag("downloads")

                # Validate
                if (ref_downloads):

                    # Create a DLC selector
                    selector = DLCSelector()

                    # Render the selector, using the downloads node as the data source
                    selector.select_using_node(ref_downloads, self.tilesheet_sprite, self.additional_sprites, self.control_center)

                else:

                    # Clear the menu controller
                    self.menu_controller.clear()

                    logn( "app debug", "downloads node not found" )
                    logn( "app debug", xml )

            # Bad data from webserver
            else:

                # Clear the menu controller
                self.menu_controller.clear()

                logn( "app debug error", "bad data from webserver!" )
                logn( "app debug", xml )

        else:

            # Clear the menu controller (should just be the idle menu)
            self.menu_controller.clear()

            logn( "app debug", "redirect failed!" )


        # App fade in
        self.window_controller.fade_in()


        # Return events
        return results


    # Periodically, we will listen to see if we have received the dlc listing.
    # Once it arrives, we will need to perform a batch download to get any preview image required for rendering the dlc listing.
    def handle_app_listen_for_dlc_listing_event(self, event, control_center):

        # We need to process the http request controller to poll for http data
        control_center.get_http_request_controller().process()

        # Try to peek a the response to our get dlc listing request.  If the request has arrived, we want to leave it
        # in the hopper; we just need to confirm that it's arrived.
        data = control_center.get_http_request_controller().peek_response_by_request_name("get-dlc-listing")

        # If we see data, then the request is done.
        if (data != None):

            # As soon as we see that the listing has returned, we'll want to send out a batch request to download
            # all of the thumbnails that will appear next to each dlc option.  We only do this if we haven't sent such a batch request already, though.
            batch = control_center.get_http_request_controller().get_batch_by_name("dlc-thumbnails-batch")

            # If we haven't created the batch yet, we'll do so now.
            if (not batch):

                # First let's compile the xml we got back from the dlc listing request
                node = XMLParser().create_node_from_xml(data)

                # Validate node / xml, and validate that we got the dlc-listing node, not some 404 page or anything crazy
                if ( (node != None) and ( node.find_node_by_tag("dlc-listing") ) ):

                    # Check for the files node
                    ref_files = node.find_node_by_tag("files")

                    # Validate
                    if (ref_files):

                        # Prepare a batch that will include each file
                        batch_items = []

                        # Loop through files
                        for ref_file in ref_files.get_nodes_by_tag("file"):

                            # Add each file to the batch items list
                            batch_items.append({
                                "path": os.path.join( "tmp", ref_file.get_attribute("name") ),
                                "url": ref_file.get_attribute("src"),
                                "bytes": -1, # Ignore
                                "binary": (int( ref_file.get_attribute("binary") ) == 1)
                            })

                        # Now let's create a new batch request
                        control_center.get_http_request_controller().download_batch_with_name(
                            "dlc-thumbnails-batch",
                            None, # use default host
                            80,
                            batch_items
                        )

                    else:

                        # If we don't need to download any additional file (and we pretty much always should, but hey...)
                        # we'll immediately go ahead and raise a redirect success event
                        control_center.get_window_controller().fade_out(
                            on_complete = "app:redirect.success"
                        )

                # Bad xml from webserver
                else:

                    # Get the active menu controller menu (i.e. idle menu)
                    idle_menu = self.menu_controller.get_active_menu()

                    # Validate
                    if (idle_menu):

                        # Set an error message on the idle menu
                        idle_menu.set_message("Could not retrieve DLC information.  Please try again.")

                    # Give the player a moment to read the error before triggering an app fade / redirect failure event
                    control_center.get_window_controller().delay(150)

                    # App fade, redirect failure event
                    control_center.get_window_controller().fade_out(
                        on_complete = "app:redirect.fail"
                    )


                    # We won't be using the response to the original web request at all, so we'll go ahead and get rid of it now.
                    control_center.get_http_request_controller().end_request_by_name("get-dlc-listing")

                    logn( "app debug", "BAD XML" )

            # If we have indeed created the batch, let's see if it's completed yet...
            elif ( batch.is_completed() ):

                # When the batch completes, we can call for an app fade.  We'll raise a "redirect succeeded"
                # event after the fade to indicate that we successfully downloaded all of the data we need to create the dlc selector.
                control_center.get_window_controller().fade_out(
                    on_complete = "app:redirect.success"
                )


        # No event to return
        return EventQueue()


    # Run the menu logic
    def menu(self):

        clock = pygame.time.Clock()

        # Main game loop
        while True:

            # In the menu, we don't need slow-motion stuff!
            clock.tick(60)


            # Clear backbuffer
            #glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)
            clear_buffers()

            # Default (hard-coded) fill color
            self.window_controller.get_geometry_controller().draw_rect(0, 0, self.render_width, self.render_height, (0, 0, 0))
            #self.window_controller.get_geometry_controller().draw_rect(game_render_x, game_render_y, SCREEN_WIDTH, SCREEN_HEIGHT, (20, 20, 20))


            # Enable scissor testing while rendering game
            self.window_controller.get_scissor_controller().enable()


            (events, keypresses) = (
                pygame.event.get(),
                pygame.key.get_pressed()
            )

            self.input_controller.poll_and_update_system_input(events, keypresses)
            self.input_controller.poll_and_update_gameplay_input( self.input_controller.get_system_input(), keypresses )

            system_input = self.input_controller.get_system_input()
            gameplay_input = self.input_controller.get_gameplay_input()
            #system_input = self.input_controller.collect_system_input(events, keypresses)
            #gameplay_input = self.input_controller.collect_gameplay_input(system_input, keypresses)


            # Process the game menu and see if it returns any special command
            processing_queue = self.game_menu.process(self.control_center, self.universe)#gameplay_input, system_input, self.widget_dispatcher, self.save_controller, self.input_controller, self.network_controller, self.universe)

            # Check any event returned by the game menu
            event = processing_queue.fetch()

            # All of them
            while (event):

                # Action type
                action = event.get_action()

                log2( "action:  %s" % action )

                # Special case:  Quit the game.  Return from menu, ending app (notwithstanding various cleanup stuff).
                if ( action == "app:quit" ):

                    # End the menu routine, ending the entire app
                    return

                # Handle any other event
                else:

                    # Feed
                    processing_queue.append(
                        self.handle_event(event, self.control_center, universe = None) # (?) no universe?
                    )


                # Loop
                event = processing_queue.fetch()


            if ( (K_F12 in self.input_controller.get_system_input()["keydown-keycodes"]) ):
                sys.exit( "F12.  Goodbye!" )



            # Render the game menu
            self.game_menu.draw(self.tilesheet_sprite, self.additional_sprites, text_renderer = self.window_controller.get_default_text_controller().get_text_renderer(), window_controller = self.window_controller)

            # End scissor testing
            self.window_controller.get_scissor_controller().disable()


            # Process and draw menus
            self.menu_controller.process(self.control_center, self.universe)
            self.menu_controller.draw(self.tilesheet_sprite, self.additional_sprites, self.text_renderers["normal"], self.window_controller)


            # Process window controller
            self.window_controller.process(self.control_center, self.universe)

            # Application-level fade control
            if ( self.window_controller.alpha_controller.get_interval() < 1.0 ):

                self.window_controller.render_fade_using_alpha_controller(
                    self.window_controller.fade_mode,
                    self.window_controller.alpha_controller
                )


            # Render newsfeeder items on top of even the fade effect
            self.window_controller.newsfeeder.draw(self.tilesheet_sprite, self.additional_sprites, self.text_renderers["normal"], self.window_controller)


            # Debug
            if (0):

                self.text_renderers["normal"].render_with_wrap(
                    "FPS:  %d" % int(clock.get_fps()),
                    5,
                    5,
                    (225, 225, 225)
                )

            # Debug
            if (0):

                s = "None"
                if ( "SDL_VIDEO_X11_WMCLASS" in os.environ ):
                    s = os.environ["SDL_VIDEO_X11_WMCLASS"]

                self.text_renderers["normal"].render_with_wrap("Var:  %s" % s, 5, 5, (225, 225, 225))



            pygame.display.flip()

            # Run sound controller processing (sound effects, background track looping, etc.)
            self.sound_controller.process(self.universe)


            # If the window has reloaded (i.e. fullscreen toggle), then
            # we must reacquire handles to a few gl assets.
            if ( self.window_controller.has_reloaded() ):

                # Get handles to a few surfaces
                self.mouse_sprite = self.window_controller.get_gfx_controller().get_graphic("cursor")
                self.tilesheet_sprite = self.window_controller.get_gfx_controller().get_graphic("tilesheet")
                self.additional_sprites = self.window_controller.get_gfx_controller().get_graphic("sprites")

                # Get handles to a couple of text renderers
                self.text_renderers = {
                    "normal": self.window_controller.get_text_controller_by_name("default").get_text_renderer(),
                    "gui": self.window_controller.get_text_controller_by_name("default").get_text_renderer() # Not sure I use this anywhere?
                    #"normal": GLTextRenderer(os.path.join(FONT_PATH, 'jupiterc.ttf'), (255, 255, 255), (0, 0, 0), 18),
                    #"gui": GLTextRenderer(os.path.join(FONT_PATH, 'jupiterc.ttf'), (255, 255, 255), (0, 0, 0), 18),
                }


                # Only this main app object pays attention to the reloaded flag.
                # Once handled, let's set it back to false.
                self.window_controller.set_reloaded(False)


    # Redirect the user from one main endpoint (menu, game world, netplay, etc.) to another main endpoint,
    # showing only any visible menu during the process.  Optionally provide an "escape" event to be fired
    # only if the user hits ESC to attempt to abort the screen.  Process all network events during this transition as well.
    def redirect_using_timer_controller(self, timer_controller, on_escape = "", max_time_in_seconds = 0.0, output_params_hash = None):

        clock = pygame.time.Clock()


        # Remember the time we started this redirect
        start = time.time()

        # Track whether we've aborted this redirect (either by timeout or by user hitting escape).
        # Once we abort the redirect, we'll cease processing on the given timer controller and on any active menu.
        aborted = False


        # "Redirect" loop
        while True:

            # Target 60fps
            clock.tick(60)


            # Clear screen
            #glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)
            clear_buffers()

            # Default backround
            self.window_controller.get_geometry_controller().draw_rect(0, 0, self.render_width, self.render_height, (0, 0, 0))


            # Check pygame event data
            (events, keypresses) = (
                pygame.event.get(),
                pygame.key.get_pressed()
            )

            # Update input controller data
            self.input_controller.poll_and_update_system_input(events, keypresses)
            self.input_controller.poll_and_update_gameplay_input( self.input_controller.get_system_input(), keypresses )

            # Grab system and gameplay input
            system_input = self.input_controller.get_system_input()
            gameplay_input = self.input_controller.get_gameplay_input()


            # ** (Debug) Abort
            if ( (K_F12 in self.input_controller.get_system_input()["keydown-keycodes"]) ):
                log( 5/0 )


            # Check net communications
            self.network_controller.process(self.control_center, universe = self.universe)


            # Set up an empty event queue
            results = EventQueue()

            # As long as we haven't aborted this redirect, let's run the local timer controller and the menu controller
            if (not aborted):

                # Run any timer given to this redirect
                results.append(
                    timer_controller.process()
                )

                # Process menu controller as well
                results.append(
                    self.menu_controller.process(self.control_center, self.universe)
                )


                # If time has run out, then we'll abort the redirect... assuming a time limit exists.
                if ( (max_time_in_seconds > 0) and ( (time.time() - start) >= max_time_in_seconds ) ):

                    # I guess it's over!
                    aborted = True

                    # Call for an app fade; return failure when done
                    self.window_controller.fade_out(
                        on_complete = "app:redirect.fail"
                    )

                # Also, the user can hit ESC to abort the redirect at any time...
                elif (
                    ( K_ESCAPE in self.input_controller.get_system_input()["keydown-keycodes"] ) or
                    ( self.input_controller.check_gameplay_action("escape", self.input_controller.get_system_input(), [], True) )
                ):

                    # Mark as aborted
                    aborted = True

                    # App fade; return redirect failure when done
                    self.window_controller.fade_out(
                        on_complete = "app:redirect.fail"
                    )


            # Render menu stack
            self.menu_controller.draw(self.tilesheet_sprite, self.additional_sprites, self.text_renderers["normal"], self.window_controller)


            # Process window controller
            results.append(
                self.window_controller.process(self.control_center, self.universe)
            )

            # Application-level fade control
            if ( self.window_controller.alpha_controller.get_interval() < 1.0 ):

                self.window_controller.render_fade_using_alpha_controller(
                    self.window_controller.fade_mode,
                    self.window_controller.alpha_controller
                )


            # Render newsfeeder items on top of even the fade effect
            self.window_controller.newsfeeder.draw(self.tilesheet_sprite, self.additional_sprites, self.text_renderers["normal"], self.window_controller)

            #self.text_renderers["normal"].render_with_wrap( "alpha:  %s / %s" % (self.window_controller.alpha_controller.get_interval(), self.window_controller.alpha_controller.get_target()), 5, 5, (225, 225, 225) )


            # Flip display
            pygame.display.flip()

            # Run sound controller processing (sound effects, background track looping, etc.)
            self.sound_controller.process(self.universe)




            # Now handle any local event we received
            event = results.fetch()

            # Loop through all local events
            while (event):

                # Convenience
                action = event.get_action()


                # Special-case:  Check for a "finish redirect" event
                if ( action == "app:redirect.success" ):

                    # Make sure to fade back in if we aren't already faded in
                    self.window_controller.fade_in()

                    # We're done with this redirect period; we successfully made it to the next endpoint.
                    return True

                # Special case:  Check for a "finish redirect unsuccessfully" event
                elif ( action == "app:redirect.fail" ):

                    # Make sure to fade back in if we aren't already faded in
                    self.window_controller.fade_in()

                    # Do we have a given output parameters hash to update?
                    if (output_params_hash != None):

                        # Update
                        output_params_hash.update( event.get_params() )


                    # We didn't make it to the endpoint.
                    return False

                # Otherwise, handle a common event
                else:

                    self.handle_event(event, self.control_center, self.universe)


                # Loop!
                event = results.fetch()


    # Run game logic / rendering
    def run(self, just_once = False, testing = False):

        debug_timer = 0

        framecount = 0
        slow = ""

        first_frame = True

        working_screenshot = None
        working_screenshot_length = 0

        mw = None

        #set_visible_region_on_texture(self.tilesheet_sprite.get_texture_id(), self.tilesheet_sprite.get_texture_width(), self.tilesheet_sprite.get_texture_height(), (0, 0, self.tilesheet_sprite.get_texture_width(), self.tilesheet_sprite.get_texture_height()))
        #set_visible_region_on_texture(self.tilesheet_sprite.get_texture_id(), self.tilesheet_sprite.get_texture_width(), self.tilesheet_sprite.get_texture_height(), (24, 6, 24, 12))

        toggled = False

        #(z1, z2, z3) = self.text_renderers["normal"].cache_with_wrap("This is some [color=special]colored text[/color] that I'm throwing into a cache_with_wrap call.  We'll see if I can get this to work...", max_width = 200)

        toggle1 = True

        xangle = 270

        clock = pygame.time.Clock()


        self.modal_gamma = 1.0
        self.modal_gamma_target = 1.0


        last_mx = 0
        last_my = 0


        w = 6
        h = 4



        if (self.game_mode == MODE_GAME):
            self.universe.get_timer_controller().add_repeating_event_with_name("debug-timer", interval = 300, uses = -1, on_complete = "debug:save-state")


        # Determine default rendering point (we'll center the game rendering if we had to choose
        # a higher resolution for video card compatibility)
        (game_render_x, game_render_y) = (
            int(self.render_width / 2) - int(SCREEN_WIDTH / 2),
            int(self.render_height / 2) - int(SCREEN_HEIGHT / 2)
        )


        shader_texture_id = None
        (shw, shh) = (0, 0)
        (shx, shy) = (0, 0)

        # Toggles debug prints (on the screen, e.g. FPS)
        show_debug = False


        # Demo
        self.universe.update_common_input_translations(self.control_center)


        # Main game loop
        while True:

            xdebug = [
                #"FPS:  %d" % int(clock.get_fps()),
                #"name:  %s / %s" % (self.universe.session["core.player1.name"]["default"], self.universe.session["core.player1.name"]["value"])
                #"camera:  (%d, %d)" % (self.universe.camera.x, self.universe.camera.y)
            ]

            frameStart = time.time()
            slow = ""

            # In game mode, listen for right shift / space bar to slow down framerate ("slow motion")
            if (self.game_mode == MODE_GAME):

                if ( "-debug" in sys.argv ):

                    if (pygame.key.get_pressed()[K_RSHIFT]):
                        clock.tick(1)

                    elif (pygame.key.get_pressed()[K_SPACE]):
                        clock.tick(10)

                    else:
                        clock.tick(60)

                else:
                    clock.tick(60)

            # In editor mode, don't bother with slow motion stuff...
            else:

                clock.tick(60)


            (events, keypresses) = (
                pygame.event.get(),
                pygame.key.get_pressed()
            )

            (clicked, rightclicked, scroll_dir, wheel_left, wheel_right) = self.check_input(events, literal = True)

            self.input_controller.poll_and_update_system_input(events, keypresses)
            self.input_controller.poll_and_update_gameplay_input( self.input_controller.get_system_input(), keypresses )
            #system_input = self.input_controller.collect_system_input(events, keypresses)
            #gameplay_input = self.input_controller.collect_gameplay_input(system_input, keypresses)

            system_input = self.input_controller.get_system_input()
            gameplay_input = self.input_controller.get_gameplay_input()


            # **Hack - adjust editor zoom on wheel scroll if holding LCTRL
            if ( pygame.key.get_pressed()[K_LCTRL] ):

                # Wait until the zoom reaches its destination
                if ( self.editor_controller.zoom_controller.get_interval() == self.editor_controller.zoom_controller.get_target() ):

                    # Wheel up to zoom in
                    if (scroll_dir == "up"):

                        # Zoom in 10%
                        self.editor_controller.zoom_controller.configure({
                            "target": self.editor_controller.zoom_controller.get_interval() + 0.1
                        })

                    # Wheel down to scroll down
                    elif (scroll_dir == "down"):

                        # Zoom in 10%
                        self.editor_controller.zoom_controller.configure({
                            "target": self.editor_controller.zoom_controller.get_interval() - 0.1
                        })


            # If the player is using the console, we should ignore all gameplay input...
            if ( self.net_console_entry.is_visible() ):

                gameplay_input = self.input_controller.collect_empty_gameplay_input()

                # If the user hit ENTER (or numpad ENTER), we should send the message and dismiss the console entry
                if (
                    any( keycode in system_input["keydown-keycodes"] for keycode in (K_RETURN, K_KP_ENTER) )
                ):

                    # What's the chatline?
                    msg = self.net_console_entry.get_buffer().strip()

                    # Ignore empty string
                    if ( len(msg) > 0 ):

                        # Send the message.
                        # Note that the send_chat function will secretly parse certain commands (e.g. /nick) and possibly not send the actual text.
                        self.control_center.get_network_controller().send_chat(msg, self.control_center, self.universe)


                        # Clear the entry buffer
                        self.net_console_entry.clear()

                        # Dismiss the entry field
                        self.net_console_entry.toggle()



            # Process HTTP request controller
            self.control_center.get_http_request_controller().process()


            #glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)
            clear_buffers()

            self.window_controller.get_geometry_controller().draw_rect(0, 0, self.render_width, self.render_height, (0, 0, 0))
            self.window_controller.get_geometry_controller().draw_rect(game_render_x, game_render_y, SCREEN_WIDTH, SCREEN_HEIGHT, (20, 20, 20))
            #self.window_controller.get_geometry_controller().draw_rect_with_vertical_gradient(game_render_x, game_render_y, SCREEN_WIDTH, SCREEN_HEIGHT, (20, 20, 20), (28, 28, 28))


            # Enable scissor testing while rendering game
            self.window_controller.get_scissor_controller().enable()

            # Set up a default scissor on the visible render region
            r = (
                0,#game_render_x,
                0,#game_render_y,
                SCREEN_WIDTH,
                SCREEN_HEIGHT
            )

            self.window_controller.get_scissor_controller().push(r)


            # Debug - refresh CSS
            if (False and self.game_mode == MODE_GAME):

                debug_timer += 1
                if ( (debug_timer >= 350) or (K_F11 in self.input_controller.get_system_input()["keydown-keycodes"]) ):

                    debug_timer = 0

                    #self.control_center.get_window_controller().get_css_controller().reset()
                    #self.control_center.get_window_controller().get_css_controller().load_selectors_from_file( os.path.join("data", "css", "theme1.css") )

                    if ( self.universe.get_active_map().name == "aidebug2" ):

                        log2( "Reloading checkpoint via F11..." )
                        for layer in self.universe.visible_maps:
                            self.universe.visible_maps[layer].clear()
                        # Load the last autosave...
                        self.control_center.get_save_controller().load_from_folder(
                            os.path.join( self.universe.get_working_save_data_path(), "autosave1" ),
                            self.control_center,
                            self.universe
                        )

                        for i in range(1, 7):

                            random_offset = random.randint(-12, 12)
                            log2( "random offset for e%d = %d" % (i, random_offset) )
                            self.universe.get_active_map().get_entity_by_name("e%d" % i).x += random_offset

                    else:

                        log2( "Reloading checkpoint via F11..." )
                        for layer in self.universe.visible_maps:
                            self.universe.visible_maps[layer].clear()
                        # Load the last autosave...
                        self.control_center.get_save_controller().load_from_folder(
                            os.path.join( self.universe.get_working_save_data_path(), "autosave2" ),
                            self.control_center,
                            self.universe
                        )

                        for i in range(0, 5):

                            e = self.universe.get_active_map().create_random_enemy()

                            # Validate
                            if (e):

                                e.ai_state.ai_respawn_interval = 1
                                e.alive = False
                                e.handle_ai(self.control_center, self.universe)
                                e.ai_state.ai_flash_interval = 0
                                log2( "New random enemy @ (%d, %d)" % (e.x, e.y) )


                        entities = self.universe.get_active_map().get_entities_by_type(GENUS_RESPAWN_PLAYER)

                        winners = []
                        for i in range(0, 5):
                            winners.append( entities.pop( random.randint(0, len(entities) - 1) ) )

                        for w in winners:
                            self.universe.get_active_map().dig_tile_at_tile_coords( int(w.x / 24), int(w.y / 24) )


                    entities = self.universe.get_active_map().get_entities_by_type(GENUS_RESPAWN_ENEMY)
                    pos = random.randint(0, len(entities) - 1)
                    p = self.universe.get_local_player()
                    p.x = entities[pos].x
                    p.y = entities[pos].y
                    log2( "Placing player @ %d, %d" % (p.x, p.y) )

                    """
                    for name in ("q1b", "q2b", "q3b", "q4b", "q5b"):

                        random_offset = random.randint(0, 24)
                        log2( "random offset for '%s': %s" % (name, random_offset) )
                        self.universe.get_active_map().get_entity_by_name(name).y -= random_offset
                    """


            # Quit game (for now)
            if (K_F12 in self.input_controller.get_system_input()["keydown-keycodes"]):
                return


            """ Debug """
            # Skip to next level and pause universe (used to prepare for a new recording)
            #if (K_F9 in self.input_controller.get_system_input()["keydown-keycodes"]):
            if (0):

                # Only do this when not paused (to prevent repeated keydown response)
                if ( not self.universe.is_paused() ):

                    # Query next map's name
                    name = self.universe.get_active_map().get_param("next-map")

                    # Validate
                    if (name):

                        # Activate map by name
                        self.universe.activate_map_on_layer_by_name(name, LAYER_FOREGROUND, control_center = self.control_center)

                        # Immediately center the camera on the active map (?)
                        self.universe.center_camera_on_map( self.universe.get_active_map() )


                        # Pause game (pressing INPUT_DEBUG will unpause and begin recording)
                        self.universe.pause()
            """ End Debug """


            # Composite
            #if (K_F3 in self.input_controller.get_system_input()["keydown-keycodes"]):
            if (0):
                self.debug_create_composite()


            masked = False
            if (self.game_mode == MODE_EDITOR):

                # Events that result from handling editor ui input (or hotkeys)
                results = EventQueue()

                # If we're holding down left-control, then we should check for hotkeys
                if ( keypresses[K_LCTRL] ):

                    # Fetch level editor hotkeys
                    hotkeys = self.hotkey_controller.get_hotkeys()

                    # Check each keycode
                    for keycode in hotkeys:

                        # On keypress (not keydown, just the first press), we'll emulate the event
                        if ( keycode in self.input_controller.get_system_input()["keydown-keycodes"] ):

                            logn( "app debug", hotkeys[keycode].get_action() )

                            # Manually add an event to the GUI manager
                            results.add(
                                action = hotkeys[keycode].get_action(),
                                params = hotkeys[keycode].get_params()

                            )
                            """
                            self.gui_manager.add_event({
                                "event-info": hotkeys[keycode].get_event_info(),
                                "parent": None, # n/a?
                                "params": hotkeys[keycode].get_params()
                            })
                            """



                # Fetch GUI text renderer
                gui_text_renderer = self.control_center.get_window_controller().get_text_controller_by_name("gui").get_text_renderer()

                # Process GUI elements.
                results.append(
                    self.gui_manager.process(text_renderer = gui_text_renderer, control_center = self.control_center, sx = 0, sy = 0, system_input = self.input_controller.get_system_input(), mouse = {"clicked": clicked, "scrolled": scroll_dir, "rightclicked": rightclicked})
                )

                # **Hack
                masked = self.gui_manager.processed_mouse


                # Loop events
                event = results.fetch()

                # Loop through all events
                while (event):

                    # Respond
                    results.append(
                        self.control_center.get_ui_responder().handle_event(event, self.control_center, self.universe)
                    )

                    # Loop
                    event = results.fetch()


                # If the GUI is masking the universe / level data the current mouse position,
                # then we will ignore any click input to prevent live editing this frame.
                if (masked):

                    # No left click
                    clicked = False

                    # No right click
                    rightclicked = False


                # Grab mouse position
                (mx, my) = pygame.mouse.get_pos()

                # Get relative mouse movement (since last frame)
                (mdx, mdy) = pygame.mouse.get_rel()


                # Compile editor input for this frame
                editor_input = {

                    # Paint tile if we're not dragging an object, we're in tile paint mode, and we're not masked by the GUI
                    "paint-tile": ( (self.editor_controller.drag.object_type == "") and (self.editor_controller.brush == "tile") and (not masked) and pygame.mouse.get_pressed()[0]),

                    # Paint entity in similar circumstances
                    "place-entity": ( (self.editor_controller.drag.object_type == "") and (self.editor_controller.brush == "entity") and (not masked) and (clicked) ),

                    # Track whether we're allowed to paint at the moment (e.g. not while selecting a tile)
                    "can-paint": ( (self.editor_controller.can_paint) and (not self.editor_controller.selecting_tile) ),


                    # Randomizer status / parameters
                    "randomizer.enabled": self.editor_controller.randomizer.enabled,
                    "randomizer.base-tile": self.editor_controller.randomizer.tile,
                    "randomizer.range": self.editor_controller.randomizer.range,


                    # Click status reports
                    "left-clicked": ( clicked and (not masked) ),
                    "right-clicked": ( rightclicked and (not masked) ),

                    # Current mouse location
                    "mx": mx,
                    "my": my,

                    # ? (I use these somewhere...)
                    "mouse-rel-x": (pygame.mouse.get_pos()[0]),
                    "mouse-rel-y": (pygame.mouse.get_pos()[1]),


                    # Clutching mouse (middle button) allows us to drag-scroll the universe
                    "clutching": pygame.mouse.get_pressed()[1],

                    # Track how much we'll move while clutching
                    "mdx": mdx,
                    "mdy": mdy
                }




                self.universe.process_editor_input_and_logic(editor_input, self.control_center)





            slow += "Ready to render universe after %s seconds\n" % (time.time() - frameStart)

            #print self.universe.session["core.last-safe-zone.title"]["value"]

            if (self.game_mode == MODE_GAME):

                self.gui_manager.get_widget_by_name("menu-bar").hide()



                # We'll always have an active map.  If we don't, that means we have no maps at all...
                if ( self.universe.get_active_map() ):

                    # If the player is playing a cooperative game and has activated the net console entry to chat,
                    # then we don't want to respond to any live gameplay input (e.g. movement, digging, etc.)
                    if ( self.net_console_entry.is_visible() ):

                        # Lock gameplay input
                        self.input_controller.lock_gameplay_input()

                        # Process game logic
                        self.universe.process_game_logic(self.control_center)

                        # Unlock gameplay input
                        self.input_controller.unlock_gameplay_input()

                    # Otherwise, we will simply process game loput normally
                    else:

                        # Process game logic
                        self.universe.process_game_logic(self.control_center)


                    if ( False and True and (not pygame.key.get_pressed()[K_F2]) ):
                        #self.window_controller.get_geometry_controller().draw_rect(0, 0, 640, 480, (20, 20, 20))
                        self.window_controller.get_gfx_controller().draw_texture(self.window_controller.get_scratch_pad("parallax").get_texture_id(), 0, 0, 1024, 1024, color = (1, 1, 1, 0.1))

                    """
                    debug = (self.universe.camera.x == self.universe.camera.target_x and self.universe.camera.y == self.universe.camera.y)
                    if ( debug or pygame.key.get_pressed()[K_F3] ):

                        if (0):
                            logn( "debug", (dx1, dy1), (x1, y1) )

                            logn( "debug", "\t", (lx1, ly1), (x2, y2), (lx2, ly2), self.universe.camera.prerender_bounds )

                            logn( "debug", "\t\t", (lx1 - x1), " vs(?) ", (x2 - lx1) )

                            logn( "debug", "\t\t(cached px of %s) + (pass2 px of %s) =?= %s" % (lx1, x1, x2) )
                            logn( "debug", "\n\t\trender at -x1 = ", -x1 )
                            logn( "debug", "\t\trender at x2 - lx1 = ", (x2 - lx1) )
                            logn( "debug", "\n\t\t\tx1 = ", x1 )
                            logn( "debug", "\t\t\tx2 = ", x2 )
                            logn( "debug", "\t\t\tlx1 = ", lx1 )
                            logn( "debug", "\t\t\tlx1 - x1 = ", (lx1 - x1) )
                            logn( "debug", "\t\t\tprerender.offsetX = ", self.universe.prerender_offsets[0] )
                            logn( "debug", "\t\t\t-x2 + lx1 + prerender.offsetX = ", (-x2 + lx1 + self.universe.prerender_offsets[0]) )

                    #else:
                    #    self.universe.draw_parallax(self.tilesheet_sprite, self.additional_sprites, self.game_mode, self.control_center)
                    """

                    self.universe.draw_game(self.tilesheet_sprite, self.additional_sprites, self.game_mode, self.control_center)

                    # Render any potential overlays for the active map (hack panels, dialogue panels, etc.)
                    #self.universe.get_active_map().draw_overlays(self.additional_sprites, text_renderer = self.text_renderers["normal"], window_controller = self.window_controller)



                # Get the HUD from the window controller.
                # We only render this during gameplay, not during menus, etc.
                hud = self.window_controller.get_hud()

                # Process the HUD (some icons animate intermittently)
                hud.process(self.universe, self.universe.session)


                # Should we show or hide the HUD, depending on active dialogue?
                m = self.universe.get_active_map()

                hack_hide = False
                if (m):
                    if (m.is_dialogue_finished()):
                        hud.show()
                    else:
                        hud.hide()

                    # I used to want to hide the HUD in challenge rooms, but more recently I've decided to show it after all...
                    if ( m.get_type() == "challenge" ):

                        #hud.hide()
                        hack_hide = False#True

                    # This is just a workaround, in case the menu controller is still trying
                    # to show a wave progress chart from a challenge room when we're not in a challenge room.
                    else:

                        # **Hack!
                        self.control_center.get_menu_controller().remove_menu_by_id("wave-progress-chart")

                # Render the HUD
                if (not hack_hide):

                    # Render
                    hud.render(5, 50, self.text_renderers["normal"], self.universe, self.universe.session, (m.get_type() == "puzzle"), (m.get_type() == "challenge"), self.additional_sprites["skill-icons"], self.additional_sprites["hud-icons"], self.window_controller)


                # Any time the universe has disappeared, we will clear the window controller's cached region sections...
                if ( not self.universe.alpha_controller.is_visible() ):

                    # Clear cache
                    self.window_controller.clear_cache()
                    #log2("**clearing text cache?  make sure to do this on level switches")


                # In case the entire display is fading in/out...
                if ( self.universe.alpha_controller.get_interval() < 1.0 ):

                    self.window_controller.render_fade_using_alpha_controller(
                        FADE_LTR,#self.universe.fade_mode,
                        self.universe.alpha_controller
                    )


            elif (self.game_mode == MODE_EDITOR):

                # We'll always have an active map.  If we don't, that means we have no maps at all...
                if (self.universe.active_map_name):

                    self.universe.draw_editor(self.tilesheet_sprite, self.additional_sprites, self.game_mode, self.control_center)


            """
            # Note:  I previously used this code to programmatically replicate an uncommon
            #        crash bug involving infinite recursion when the player tried to move.
            #        It discovered the bug on world1.level7 by chance.
            #
            # Debug
            if ( K_ESCAPE in self.input_controller.get_system_input()["keydown-keycodes"] ):

                # Get player, enemy
                (player, enemy) = (
                    self.universe.get_active_map().get_entity_by_name("player1"),
                    self.universe.get_active_map().get_entities_by_type(GENUS_ENEMY)[0]
                )

                # Position "just so"
                player.x = 120
                player.y = 350

                enemy.x = 0
                enemy.y = 0

                # Hacks
                player.can_move = True
                player.ai_state.last_attempted_lateral_move = DIR_RIGHT
                player.ai_state.last_vertical_move = DIR_DOWN

                # Command move left
                player.move(0, player.speed, self.universe)
            """


            # Get system input (convenience)
            system_input = self.input_controller.get_system_input()

            # Press ESC to pause the game
            if (
                (self.game_mode == MODE_GAME) and
                (
                    ( K_ESCAPE in system_input["keydown-keycodes"] ) or
                    ( self.input_controller.check_gameplay_action("escape", system_input, [], True) )
                )
            ):

                """ Begin DEBUG """
                self.control_center.get_window_controller().get_css_controller().reset()
                self.control_center.get_window_controller().get_css_controller().load_selectors_from_file( os.path.join("data", "css", "theme1.css") )
                """ End DEBUG """

                # Make sure that the menu controller isn't pause locked (i.e. we previously paused the game,
                # and we haven't finished that that pause menu yet...)
                if ( not self.menu_controller.is_pause_locked() ):

                    # Ensure that the looming pause menu has fresh splash data
                    self.splash_controller.invalidate()

                    # Update a few important session variables in case the player is going to save their game...
                    player = self.universe.get_active_map().get_entity_by_name("player1")

                    self.universe.set_session_variable("app.active-map-name", self.universe.active_map_name)

                    self.universe.set_session_variable("core.player1.x", "%d" % player.get_x())
                    self.universe.set_session_variable("core.player1.y", "%d" % player.get_y())

                    # Do I really want to save memory?  I kind of need it for proper save game
                    # functionality, but... for now I'll do it this way.
                    self.universe.get_active_map().save_memory(self.universe)



                    # Save the current display to a temporary file.  We'll use this
                    # temporary file as the source of the thumbnail if the user
                    # chooses to save their game while paused...
                    self.universe.generate_filesave_thumbnail()
                    #pygame.image.save(pygame.display.get_surface(), "temp_surface.png")
                    #resize_image("temp_surface.png", "temp_surface.resized.png", size = (160, 120))


                    # Offline pause menus.  Check to see if we want a generic pause menu, or perhaps
                    # a puzzle room menu or something...
                    if ( self.network_controller.get_status() == NET_STATUS_OFFLINE ):

                        m = self.universe.get_active_map()

                        log2( m.name, m.get_type() )


                        # "Dim" background music a bit
                        self.sound_controller.set_background_ratio(0.4)


                        # On puzzle maps, we show a special puzzle map pause menu...
                        if ( m.get_type() == "puzzle" ):

                            self.menu_controller.add(
                                self.widget_dispatcher.create_puzzle_pause_menu().configure({
                                    "x": 0,
                                    "y": 0,
                                    "width": SCREEN_WIDTH,
                                    "height": SCREEN_HEIGHT
                                })
                            )

                        # On challenge room maps, we show a special wave pause menu...
                        elif ( m.get_type() == "challenge" ):

                            self.menu_controller.add(
                                self.widget_dispatcher.create_wave_pause_menu().configure({
                                    "x": 0,
                                    "y": 0,
                                    "width": SCREEN_WIDTH,
                                    "height": SCREEN_HEIGHT
                                })
                            )

                        # On linear maps, we use a simplified pause menu...
                        elif ( m.get_type() == "linear" ):

                            self.menu_controller.add(
                                self.widget_dispatcher.create_linear_pause_menu().configure({
                                    "x": 0,
                                    "y": 0,
                                    "width": SCREEN_WIDTH,
                                    "height": SCREEN_HEIGHT
                                })
                            )

                        # In ordinary circumstances, show the standard pause menu...
                        else:

                            # Perhaps a presently-active newsfeeder item has a custom escape event for us to process?
                            escape_event = None#self.window_controller.get_newsfeeder().get_escape_event()

                            if (escape_event):

                                self.handle_escape_event(escape_event)

                            # If not, just show the pause menu...
                            else:

                                self.menu_controller.add(
                                    self.widget_dispatcher.create_pause_menu().configure({#PAUSE_MENU_X, PAUSE_MENU_Y, PAUSE_MENU_WIDTH, PAUSE_MENU_HEIGHT, self.text_renderers["normal"], self.save_controller, self.network_controller, self.universe, self.universe.session, self.widget_dispatcher, self.ref_skilltrees)
                                        "x": PAUSE_MENU_X,
                                        "y": PAUSE_MENU_Y,
                                        "width": PAUSE_MENU_WIDTH,
                                        "height": PAUSE_MENU_HEIGHT
                                    })#.setup_skillset_cache(self.ref_skilltrees)
                                )

                                #self.pause_menu.activate(
                                #    lambda a = self.universe, b = self.universe.session, c = self.pause_menu, wd = self.widget_dispatcher: c.populate_grid_menus(wd, a, b)
                                #)

                    # Online co-op pause menu.  Note that this menu never pauses the action.
                    else:

                        self.menu_controller.add(
                            self.widget_dispatcher.create_net_pause_menu()
                        )


            if (self.game_mode == MODE_EDITOR):

                self.gui_manager.draw_z_index(100, sx = 0, sy = 0, text_renderer = gui_text_renderer, window_controller = self.window_controller)


                if (self.editor_controller.selecting_tile):

                    # Assume
                    tilesheet_sprite = self.tilesheet_sprite

                    # Quickly check for custom tilesheet.  Overwrite param if we have one!
                    if (self.universe.custom_tilesheet):

                        # We'll use the custom tilesheet for rendering this universe
                        tilesheet_sprite = self.universe.custom_tilesheet


                    # Get dimensions
                    (tilesheet_width, tilesheet_height) = (
                        tilesheet_sprite.get_width(),
                        tilesheet_sprite.get_height()
                    )

                    # Tiles per row
                    tiles_per_row = int(tilesheet_width / TILE_WIDTH)


                    # lightbox
                    self.window_controller.get_geometry_controller().draw_rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (0, 0, 0, 0.5))

                    # tilesheet rectangle
                    r = ( (SCREEN_WIDTH / 2) - (tilesheet_width / 2), (SCREEN_HEIGHT / 2) - (tilesheet_height / 2), tilesheet_width, tilesheet_height)

                    self.window_controller.get_geometry_controller().draw_rect(r[0], r[1], r[2], r[3], (255, 0, 255))

                    # border
                    padding = 2
                    self.window_controller.get_geometry_controller().draw_rect_frame(r[0] - padding, r[1] - padding, r[2] + (padding * 2), r[3] + (padding * 2), (225, 225, 225), padding)

                    # render tilesheet
                    self.window_controller.get_gfx_controller().draw_sprite(r[0], r[1], r[2], r[3], tilesheet_sprite, frame = -1)


                    # slightly dim all tiles...
                    self.window_controller.get_geometry_controller().draw_rect(r[0], r[1], r[2], r[3], (25, 25, 25, 0.75))


                    # Check for mouse hover / click selection
                    mr = (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1)


                    for y in range(0, int(tilesheet_width / tiles_per_row)):

                        for x in range(0, tiles_per_row):

                            r2 = (r[0] + (x * TILE_WIDTH), r[1] + (y * TILE_HEIGHT), TILE_WIDTH, TILE_HEIGHT)

                            # Hover?
                            if (intersect(mr, r2)):

                                log(  "    mr:  ", mr )
                                log(  "    r2:  ", r2 )

                                tile_index = (y * tiles_per_row) + x

                                # Re-draw this single tile to create a "highlight" effect
                                self.window_controller.get_gfx_controller().draw_textured_row(r2[0], r2[1], tilesheet_sprite, [tile_index])

                                # clicked to choose tile?
                                if (clicked):

                                    # Set tile and dismiss tile selector
                                    self.editor_controller.tile = tile_index
                                    self.editor_controller.brush = "tile"

                                    # We're done selecting a tile
                                    self.editor_controller.selecting_tile = False

                                    # Wait until we have release the left mouse button to resume editing (prevent click-through)
                                    self.editor_controller.can_paint = False

                                    # Disable randomizer
                                    self.editor_controller.randomizer.enabled = False


                # Render mouse sprite for level editor
                (mx, my) = pygame.mouse.get_pos()


                self.window_controller.get_gfx_controller().draw_sprite(mx, my, 32, 32, self.mouse_sprite, frame = 0, gl_color = (1, 1, 1, 1))
                #self.mouse_sprite.draw(pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1])
                #glColor4f(1.0, 1.0, 1.0, 1.0)


            if ( self.universe.is_paused() ):

                # Let's render the cache image we took of the current in-game action behind the pause menu...
                self.splash_controller.process(self.control_center, self.universe)
                self.splash_controller.draw(self.window_controller)

                xdebug.append( "Game paused" )

            else:

                if ( self.splash_controller.is_lingering() ):

                    xdebug.append( "Splash lingering..." )

                    self.splash_controller.process(self.control_center, self.universe)
                    self.splash_controller.draw(self.window_controller)


                # Do we have a proper minimap to render at the moment?
                if (self.minimap):

                    # Ensure that the user still wants the minimap
                    if ( INPUT_MINIMAP in self.input_controller.get_gameplay_input() ):

                        # Process the minimap (data initialization, fading, panning, whatever)
                        self.minimap.process(self.control_center, self.universe)

                        # Calculate centered render position
                        (rx, ry) = (
                            int(SCREEN_WIDTH / 2) - int(MINIMAP_WIDTH / 2),
                            int(SCREEN_HEIGHT / 2) - int(MINIMAP_HEIGHT / 2)
                        )

                        # Render the thing
                        self.minimap.draw(rx, ry, self.tilesheet_sprite, self.additional_sprites, self.text_renderers["normal"], self.window_controller)

                    # If not, then let's trash the minimap
                    else:

                        # Goodbye
                        self.minimap = None


                # If not, we'll check for the minimap input keypress
                else:

                    # Has user requested minimap?
                    if ( INPUT_MINIMAP in self.input_controller.get_gameplay_input() ):

                        # Before creating a minimap, let's make sure at least one map in this univese has the "overworld" class
                        if (
                            any( self.universe.map_data[LAYER_FOREGROUND][o].has_class("overworld") for o in self.universe.map_data[LAYER_FOREGROUND] )
                        ):

                            # Let's create the minimap / worldmap
                            self.minimap = self.widget_dispatcher.create_worldmap().configure({
                                "width": MINIMAP_WIDTH,
                                "height": MINIMAP_HEIGHT,
                                "view": self.universe.get_session_variable("core.worldmap.view").get_value(),
                                "uses-lightbox": True
                            })
                            #print 5/0


            slow += "Ready to process menu controller after %s seconds\n" % (time.time() - frameStart)
            self.menu_controller.process(self.control_center, self.universe)

            slow += "Finished processing menu controller after %s seconds\n" % (time.time() - frameStart)

            #print "Menu Events:  ", z

            self.menu_controller.draw(self.tilesheet_sprite, self.additional_sprites, self.text_renderers["normal"], self.window_controller)


            # process newsfeeder items, render newsfeeder
            #self.universe.newsfeeder.process()




            """
            if (K_LCTRL in self.input_controller.get_system_input()["keydown-keycodes"]):
                self.network_controller.net_console.add("[color=special]Server Notice:[/color]  This is a test... I want to see the letters fade in one by one! %d" % time.time())
            """

            # We check the "show net chat console" input status from within the app itself, even though it
            # counts as a "gameplay input" command.
            if (INPUT_NET_CHAT in gameplay_input):

                # Make sure we're in co-op mode
                if (
                    self.network_controller.get_status() in (NET_STATUS_SERVER, NET_STATUS_CLIENT)
                ):

                    # Ignore if already visible
                    if ( not self.net_console_entry.is_visible() ):

                        # Toggle into visibility
                        self.net_console_entry.toggle()


            # Process net console
            self.network_controller.net_console.process()


            # Default render position for chatlines
            (rx, ry) = (
                NET_CONSOLE_X,
                SCREEN_HEIGHT
            )

            # Height required to render chat backdrop
            h = self.network_controller.net_console.get_height(self.window_controller)


            # If the "send chat" entry area is active, we'll slide up the chatlines and handle chatline entry
            if ( self.net_console_entry.is_visible() ):

                # Adjust default chatlines render position (y axis)
                ry -= 25 # hack

                # Backdrop requires more height
                h += 25 # hack


            """
            # If we need to render a backdrop...
            if (h > 0):

                # Render a couple of quick rectangles
                self.window_controller.get_geometry_controller().draw_rect(0, SCREEN_HEIGHT - h, SCREEN_WIDTH, h, (25, 25, 25))
                self.window_controller.get_geometry_controller().draw_rect(0, SCREEN_HEIGHT - (h + 2), SCREEN_WIDTH, 2, (225, 225, 225))
            """


            # Check flag again
            if ( self.net_console_entry.is_visible() ):

                # Process entry widget
                self.net_console_entry.process(self.input_controller.get_system_input())

                # Render entry widget
                self.net_console_entry.draw(30, SCREEN_HEIGHT - 25, self.window_controller)


            # Render net console (i.e. chatlines)
            #self.network_controller.net_console.draw(rx, SCREEN_HEIGHT - h - 10, self.window_controller)
            self.network_controller.net_console.draw(rx, 80, self.window_controller)


            # Check for suicide timer
            player = self.universe.get_local_player()

            # Validate
            if (player):

                percent = player.get_suicide_interval_percentage()


                # Any timer to render?
                if (percent > 0):

                    # Let the player know how close they are to suicide...
                    self.window_controller.get_geometry_controller().draw_clock_rect(0, 0, 640, 480, background = (225, 25, 25, 0.1), degrees = int(percent * 360))


            # Miscellaneous debugging stuff (F11 to do this, F12 to do that, etc.)
            #self.do_debug_stuff(clock, working_screenshot)


            # Process window controller
            results = self.window_controller.process(self.control_center, self.universe)


            # Before looping events, let's check for the app:leave-game event.
            # If we find an app:leave-game event, then we should return to the main menu immediately.
            if (
                results.fetch_by_action("app:leave-game")
            ):

                # Exit loop immediately
                return


            # Otherwise, loop any event as usual
            else:

                event = results.fetch()

                while (event):

                    # Handle event
                    self.handle_event(event, self.control_center, self.universe)

                    event = results.fetch()


            # Application-level fade
            if ( self.window_controller.alpha_controller.get_interval() < 1.0 ):

                self.window_controller.render_fade_using_alpha_controller(
                    self.window_controller.fade_mode,
                    self.window_controller.alpha_controller
                )


            # Render the window controller's newsfeeder on top of even the fade effect
            self.window_controller.newsfeeder.draw(self.tilesheet_sprite, self.additional_sprites, self.text_renderers["normal"], self.window_controller)


            # Remove the scissor test we defined at the top (render region)
            self.window_controller.get_scissor_controller().pop()

            # Disable scissor testing until we again decide to render the game
            self.window_controller.get_scissor_controller().disable()


            # Debug - font tests
            if (0):
                self.window_controller.get_geometry_controller().draw_rect(0, 0, 640, 480, (25, 25, 25))

                self.window_controller.get_geometry_controller().draw_rect(0, 40, 640, 40, (25, 25, 25))
                self.window_controller.get_default_text_controller().get_text_renderer().render("the quick brown fox plays lode runner", 50, 50, (225, 225, 225))

                self.window_controller.get_geometry_controller().draw_rect(0, 90, 640, 40, (225, 225, 225))
                self.window_controller.get_default_text_controller().get_text_renderer().render("the quick brown fox plays lode runner", 50, 100, (225, 225, 225))

            # Debug - clipping tests
            if (0):

                (geo, scis, stenc) = (
                    self.window_controller.get_geometry_controller(),
                    self.window_controller.get_scissor_controller(),
                    self.window_controller.get_stencil_controller()
                )

                self.window_controller.get_geometry_controller().draw_rect(0, 0, 640, 480, (25, 25, 25))

                geo.draw_rect(200, 200, 300, 100, (125, 125, 125))

                geo.draw_rect_frame(200, 150, 300, 200, (225, 225, 225), 2)

                scis.enable()
                scis.push( (200, 150, 300, 200) )

                stenc.clear()
                stenc.set_mode(STENCIL_MODE_PAINT)
                geo.draw_rect(180, 100, 80, 200, (225, 25, 25, 0.5))
                stenc.set_mode(STENCIL_MODE_PAINTED_ONLY)


                self.window_controller.pause_clipping()

                geo.draw_rect(280, 100, 80, 200, (25, 225, 25, 0.5))


                geo.draw_rect(450, 100, 100, 200, (25, 25, 225, 0.5))

                self.window_controller.resume_clipping()

                geo.draw_rect(220, 220, 80, 300, (225, 225, 25, 0.5))
                stenc.set_mode(STENCIL_MODE_NONE)

                scis.disable()


            # Debug - stencil buffer tests
            if (0):
                self.window_controller.get_geometry_controller().draw_rect(0, 0, 640, 480, (25, 25, 25))

                stencil_controller = self.window_controller.get_stencil_controller()

                stencil_controller.set_mode(STENCIL_MODE_PAINT)


                self.window_controller.get_geometry_controller().draw_rounded_rect(100, 100, 200, 150, background = (75, 75, 75, 0.5), border= (225, 225, 225), border_size = 0)

                stencil_controller.set_mode(STENCIL_MODE_ERASE)

                self.window_controller.get_geometry_controller().draw_rect(100, 80, 30, 200, (225, 225, 25))

                self.window_controller.get_geometry_controller().draw_rounded_rect_frame(100, 100, 200, 150, color = (225, 225, 225), border_size = 5)

                stencil_controller.set_mode(STENCIL_MODE_PAINTED_ONLY)

                #self.window_controller.get_geometry_controller().draw_rect(50, 50, 160, 120, (225, 25, 25, 0.5))
                self.window_controller.get_geometry_controller().draw_rect(75, 80, 250, 70, (225, 25, 25, 0.5))

                #stencil_controller.set_mode(STENCIL_MODE_NONE)
                #stencil_controller.set_mode(STENCIL_MODE_NONE)
                stencil_controller.set_mode(STENCIL_MODE_NONE)


            #self.window_controller.get_geometry_controller().draw_rect(0, 240, 640, 2, (225, 225, 25, 0.5))


            """
            if ( K_F4 in self.input_controller.get_system_input()["keydown-keycodes"] ):

                self.universe.newsfeeder.post({
                    "type": 10,
                    "quest": self.universe.get_quest_by_name("amandria-internet")
                })

                #if (shader_texture_id != None):
                #    self.window_controller.get_gfx_controller().draw_texture(shader_texture_id, 0, 0, int(shw / 1), int(shh / 1))
                #(shader_texture_id, shw, shh) = self.window_controller.clip_backbuffer()
            """



            if (0):

                #if ( K_F1 in self.input_controller.get_system_input()["keydown-keycodes"] ):
                if ( pygame.key.get_pressed()[K_F1] ):

                    slow += "Generating backdrop...\n"
                    log2("Generating backdrop")

                    a = time.time()

                    self.window_controller.render_to_scratch_pad("parallax")
                    #self.window_controller.set_viewport(0, 0, 1024, 1024)

                    self.window_controller.get_geometry_controller().draw_rect(0, 0, 640, 480, (20, 20, 20))

                    #self.window_controller.activate_shader("greyscale")
                    #self.window_controller.configure_greyscale_intensity(10)
                    self.universe.draw_parallax(self.tilesheet_sprite, self.additional_sprites, self.game_mode, self.control_center)
                    #self.window_controller.deactivate_shader()

                    if (1):

                        # Horizontal pass
                        self.window_controller.render_to_scratch_pad("common")

                        self.window_controller.get_geometry_controller().draw_rect(0, 0, 640, 480, (20, 90, 20))
                        self.window_controller.activate_shader("directional-blur")
                        self.window_controller.configure_directional_blur(0, 1024.0)
                        self.window_controller.get_gfx_controller().draw_texture(self.window_controller.get_scratch_pad("parallax").get_texture_id(), 0, 0, 1024, 1024)
                        self.window_controller.deactivate_shader()


                        # Vertical pass
                        self.window_controller.render_to_scratch_pad("parallax")

                        self.window_controller.get_geometry_controller().draw_rect(0, 0, 640, 480, (45, 0, 45))
                        self.window_controller.activate_shader("directional-blur")
                        self.window_controller.configure_directional_blur(1, 1024.0)
                        self.window_controller.get_gfx_controller().draw_texture(self.window_controller.get_scratch_pad("common").get_texture_id(), 0, 0, 1024, 1024)
                        self.window_controller.deactivate_shader()

                        slow += "Generated backdrop in %s seconds\n" % (time.time() - a)
                        log2("Generated backdrop in %s seconds\n" % (time.time() - a))

                    # Back to primary frame buffer
                    self.window_controller.render_to_primary()


            #if ( pygame.key.get_pressed()[K_1] ):
            #    self.window_controller.test_shader1()
            #if ( pygame.key.get_pressed()[K_2] ):
            #    self.window_controller.test_shader2()

            """
            if ( pygame.key.get_pressed()[K_LEFT] ):
                shx -= 5
            elif ( pygame.key.get_pressed()[K_RIGHT] ):
                shx += 5
            """


            if ( 0 and pygame.key.get_pressed()[K_F2] ):
                self.window_controller.get_geometry_controller().draw_rect(0, 0, 640, 480, (20, 20, 20))
                self.window_controller.get_gfx_controller().draw_texture(self.window_controller.get_scratch_pad("parallax").get_texture_id(), -shx, shy, 1024, 1024)


            # Disabled scratch pad debug shows
            if (0):

                if ( pygame.key.get_pressed()[K_q] ):

                    self.window_controller.get_geometry_controller().draw_rect(0, 0, 640, 480, (20, 20, 20))

                    if (0):
                        self.window_controller.render_to_scratch_pad("common")
                        self.window_controller.get_geometry_controller().draw_rect(0, 0, 1024, 1024, (20, 90, 20))

                        self.window_controller.render_to_primary()


                    # old:  0.5 alpha
                    #self.window_controller.get_gfx_controller().draw_texture(self.window_controller.get_scratch_pad("beta (no longer exists)").get_texture_id(), 0, 0, 512, 512, (1, 1, 1, 0.85))#drawbuffer2(-shx, shy)
                    #self.window_controller.get_geometry_controller().draw_rect(0, 0, 512, 512, (225, 225, 25, 0.05))

                if ( pygame.key.get_pressed()[K_w] ):
                    self.window_controller.get_gfx_controller().draw_texture(self.splash_controller.source_texture_id, 0, 0, 1024, 1024, color = (1, 1, 1, 1))

                if ( pygame.key.get_pressed()[K_e] ):
                    self.window_controller.get_gfx_controller().draw_texture(self.splash_controller.working_texture_id, 0, 0, 1024, 1024, color = (1, 1, 1, 1))



            """
            player = self.universe.get_local_player()
            if (player):
                xdebug.append(
                    "player:  %s" % ("active" if player.status == STATUS_ACTIVE else "not active")
                )
            for var in ("core.handled-local-death", "core.is-dummy-session"):
                xdebug.append(
                    "%s:  %s" % (var, self.universe.get_session_variable(var).get_value())
                )
            """

            # Show pause lock count?
            if (0):
                xdebug.append(
                    "Pause lock count:  %d" % self.universe.pause_count
                )

            # Show greyscale interval data?
            if (0):
                xdebug.append(
                    "greyscale:  %s / %s" % ( self.splash_controller.greyscale_controller.get_interval(), self.splash_controller.greyscale_controller.get_target() )
                )

            # Show FPS?
            if (1):
                xdebug = [
                    "FPS:  %d" % int(clock.get_fps())
                ]

            # Show player1 coordinates?
            if (0):
                if ( self.universe.get_active_map() ):
                    p = self.universe.get_active_map().get_entity_by_name("player1")
                    if (p):
                        xdebug.append("%s, %s" % (p.x, p.y))


            # Show visible maps?
            if (0):
                """ Debug - list visible maps """
                xdebug.append(
                    "Visible:  %s" % ", ".join( [ self.universe.visible_maps[LAYER_FOREGROUND][o].get_name() for o in self.universe.visible_maps[LAYER_FOREGROUND].keys() ] )
                )

            # Show active map name?
            if (1):
                if ( self.universe.get_active_map() ):
                    xdebug.append(
                        self.universe.get_active_map().get_name()
                    )

            # Show achievement debug data?
            if (0):
                xdebug.extend([
                    "Visited:  %s" % self.universe.get_session_variable("worldmap.count.visited").get_value(),
                    "Complete:  %s" % self.universe.get_session_variable("achievements.the-collector.counter").get_value()
                ])


            # Show timers?
            if (1):
                for name in self.universe.get_timer_controller().get_timer_names():
                    xdebug.append("Timer %s:  %s" % (name, self.universe.get_timer_controller().get_timer_by_name(name).get_time_remaining_in_seconds()))


            # Show wave tracker params?
            if (1):
                m = self.universe.get_active_map()
                if (m):
                    for name in m.get_wave_tracker().get_wave_param_names():
                        if (m.get_wave_tracker().get_wave_param(name) != ""):
                            xdebug.append( "param[%s] = %s" % (name, m.get_wave_tracker().get_wave_param(name)) )
                    xdebug.append("")
                    for name in m.get_wave_tracker().get_active_wave_requirement_names():
                        xdebug.append( "requirement[%s] = %s, counter = %s" % (name, m.get_wave_tracker().get_wave_requirement(name), m.get_wave_tracker().get_wave_counter(name)) )


            # Show global / local lock status?
            if (0):
                if ( self.network_controller.is_global_locked() ):
                    xdebug.append( "GLOBAL NET LOCK" )
                elif ( self.network_controller.is_local_locked() ):
                    xdebug.append( "LOCAL NET LOCK" )


            #xdebug.append("Press TILDE to toggle debug output.")


            # Show camera position?
            if (0):
                xdebug.append(
                    "Camera:  %s, %s" % (self.universe.camera.x, self.universe.camera.y)
                )

            # Show mouse position?
            if (0):
                xdebug.append(
                    "Mouse:  %s, %s" % pygame.mouse.get_pos()
                )

            # Show zoom level?
            if (0):
                xdebug.append(
                    "zoom:  %s" % self.editor_controller.zoom_controller.get_interval()
                )


            """
            if ( (K_1 in self.input_controller.get_system_input()["keydown-keycodes"]) ):
                self.editor_controller.zoom_controller.configure({
                    "target": self.editor_controller.zoom_controller.get_interval() - 0.1
                })
            elif ( (K_2 in self.input_controller.get_system_input()["keydown-keycodes"]) ):


                self.editor_controller.zoom_controller.configure({
                    "target": 1.0
                })
            elif ( (K_3 in self.input_controller.get_system_input()["keydown-keycodes"]) ):
                self.editor_controller.zoom_controller.configure({
                    "target": self.editor_controller.zoom_controller.get_interval() + 0.1
                })
            """


            # Show network ping data?
            if ( self.control_center.get_network_controller().get_status() == NET_STATUS_SERVER ):

                # Loop connected ids
                for player_id in self.control_center.get_network_controller().get_connected_player_ids():

                    # Check for ping data hash
                    ping_data = self.control_center.get_network_controller().get_ping_data_by_player_id(player_id)

                    # Validate
                    if (ping_data):

                        # Add average and count
                        xdebug.append(
                            "player%s ping : %sms : %s responses" % (player_id, ping_data["mean"], ping_data["count"])
                        )


            # Toggle debug prints
            if ( K_BACKQUOTE in self.input_controller.get_system_input()["keydown-keycodes"] ):
                show_debug = (not show_debug)

            if (show_debug):

                #self.text_renderers["normal"].render_with_wrap("Recording Active.", 5, 50 + (0 * 25), (225, 225, 225))
                for i in range(0, len(xdebug)):#range(0, len(xdebug)):
                    self.text_renderers["normal"].render_with_wrap(xdebug[i], 5, 50 + (i * 25), (225, 225, 225))

            slow += "Rendered frame after %s seconds\n" % (time.time() - frameStart)


            """
            # Debug
            """
            #if ( K_F11 in self.input_controller.get_system_input()["keydown-keycodes"] ):
            if (0):

                # Active map
                m = self.universe.get_active_map()

                # Find base, mask planes
                (plane1, plane2) = (
                    m.get_plane_by_name("Untitled Plane"),
                    m.get_plane_by_name("mask")
                )

                # Create mask if necessary
                if (not plane2):

                    # Create plane
                    plane2 = Plane()
                    plane2.name = "mask"

                    # Hack, guarantee it's on top (I guess?)
                    plane2.z_index = 100

                    # Add to map
                    m.add_plane(plane2)


                # Define the tiles we will apply mask corners to
                level_tiles = []

                for r in (
                    range(96, 100),    # Snow filler
                    range(116, 120),   # Snow ground
                    range(160, 200),   # Mines filler / ground
                    range(200, 206),   # Jungle filler
                    range(220, 229),   # Jungle ground
                    range(303, 315),   # Town filler
                    range(323, 335),   # Town ground
                    range(17, 20)      # Spikes (???)
                ):

                    # Add in tile range
                    level_tiles.extend(r)

                # Make sure mask plane is at least as large as base plane.
                # Clear entire mask plane in the process, and also perform magic corner calculations.
                for y in range( 0, plane1.get_height() ):
                    for x in range( 0, plane1.get_width() ):

                        # Guarantee size
                        plane2.set_tile(x, y, 0)

                        # Check to see if we should check corner logic on this tile type
                        if ( plane1.get_tile(x, y) in level_tiles ):

                            # Lower island/peninsula?
                            if ( (not (plane1.get_tile(x - 1, y) in level_tiles)) and
                                 (not (plane1.get_tile(x + 1, y) in level_tiles)) and
                                 (not (plane1.get_tile(x, y + 1) in level_tiles)) ):

                                # Random value
                                r = random.random()

                                if ( r < 0.25 ):
                                    plane2.set_tile(x, y, 300)  # Lower-left

                                elif ( r < 0.50 ):
                                    plane2.set_tile(x, y, 302)  # Lower-right

                            # Lower-left corner?
                            if ( (not (plane1.get_tile(x - 1, y) in level_tiles)) and
                                 (    (plane1.get_tile(x + 1, y) in level_tiles)) and
                                 (not (plane1.get_tile(x, y + 1) in level_tiles)) ):

                                # Good chance
                                if ( random.random() < 0.75 ):
                                    plane2.set_tile(x, y, 300)

                            # Lower-right corner?
                            if ( (    (plane1.get_tile(x - 1, y) in level_tiles)) and
                                 (not (plane1.get_tile(x + 1, y) in level_tiles)) and
                                 (not (plane1.get_tile(x, y + 1) in level_tiles)) ):

                                # Good chance
                                if ( random.random() < 0.75 ):
                                    plane2.set_tile(x, y, 302)
            """
            # End magic corner logic
            """


            if (K_F4 in self.input_controller.get_system_input()["keydown-keycodes"]):

                if (0):

                    self.universe.get_timer_controller().add_singular_event_with_name(
                        "mytimer1",
                        180,
                        on_complete = "universe:kill-player",
                        params = {}
                    )

                elif (0):

                    self.universe.get_timer_controller().add_singular_event_with_name(
                        "mytimer1",
                        60,
                        on_complete = "universe:debug",
                        params = {
                            "message": "This is a timed event that originated at %s" % time.time()
                        }
                    )


            if (0):

                self.window_controller.get_geometry_controller().draw_rect(0, 0, 640, 480, (0, 0, 0))
                #self.window_controller.get_geometry_controller().draw_rect(0, 0, 640, 480, (25, 225, 25))

                self.window_controller.get_geometry_controller().draw_rounded_rect_with_gradient(
                    150,
                    150,
                    200,
                    200,
                    background1 = (25, 225, 25),
                    background2 = (25, 225, 25),
                    border = (225, 225, 225),
                    border_size = 0,
                    shadow = (205, 205, 205),
                    shadow_size = 0,
                    gradient_direction = DIR_RIGHT,
                    radius = 10
                )

                self.window_controller.get_geometry_controller().draw_rounded_rect_with_gradient(
                    200,
                    200,
                    20,
                    20,
                    background1 = (225, 25, 25),
                    background2 = (25, 25, 225),
                    border = (225, 225, 225),
                    border_size = 0,
                    shadow = (205, 205, 205),
                    shadow_size = 0,
                    gradient_direction = DIR_RIGHT,
                    radius = 10
                )

                self.window_controller.get_geometry_controller().draw_rounded_rect_frame(
                    200,
                    200,
                    20,
                    20,
                    color = (225, 225, 225),
                    border_size = 2,
                    shadow = (205, 205, 205),
                    shadow_size = 1,
                    radius = 10
                )


            if (0):

                self.window_controller.get_geometry_controller().draw_rect(0, 0, 640, 480, (0, 0, 0))

                self.window_controller.get_stencil_controller().set_mode(STENCIL_MODE_PAINT)

                self.window_controller.get_geometry_controller().draw_rect(0, 0, 320, 480, (225, 25, 25))

                self.window_controller.get_stencil_controller().set_mode(STENCIL_MODE_PAINTED_ONLY)

                self.window_controller.get_geometry_controller().draw_rect(100, 100, 540, 280, (25, 225, 25))

                self.window_controller.get_stencil_controller().set_mode(STENCIL_MODE_NONE)


            """ DEBUG - Screenshot key, autoname """
            #if ( INPUT_DEBUG in self.input_controller.get_gameplay_input() ):
            if (0):

                # Force relative path to exist
                ensure_path_exists(
                    os.path.join("renders", "screenshots")
                )

                # Generate new filename
                i = 1
                while ( os.path.exists( os.path.join("renders", "screenshots", "screenshot%d.png" % i) ) ):

                    # First available unique
                    i += 1

                # Save current display to image
                pygame.image.save(
                    pygame.display.get_surface(),
                    os.path.join("renders", "screenshots", "screenshot%d.png" % i)
                )

                # Log note
                log2( "Saved %s" % os.path.join("renders", "screenshots", "screenshot%d.png" % i) )


            # Flip display buffers
            pygame.display.flip()

            # Run sound controller processing (sound effects, background track looping, etc.)
            self.sound_controller.process(self.universe)



            slow += "**Generated frame in %s seconds\n" % (time.time() - frameStart)

            #**Disabled output detailing why a frame might have rendered slowly
            #if ( time.time() - frameStart >= 0.1 ):
            #    log2(slow)

            framecount += 1
            #if (framecount > 5):
            #    return


            if (self.universe):
                self.universe.set_session_variable( "core.time", "%d" % int(time.time()) )


        if (self.game_mode == MODE_GAME):
            self.universe.get_timer_controller().remove_timer_by_name("debug-timer")


    def generate_images(self):

        if (not os.path.exists("level_images")):
            os.mkdir("level_images")

        self.editing = False
        self.playing = True

        files = os.listdir("userlevels")

        for each in files:

            if (each.find("Level") >= 0):

                self.current_folder = os.path.join("userlevels", self.current_mode)
                self.load_level("userlevels/%s" % each)

                self.run(just_once = True)

                x = pygame.display.get_surface()
                #i = pygame.image.frombuffer(b.raw, (640, 480), "RGBA")

                pygame.image.save(x, "level_images/%s.png" % each)

                #return


    def do_debug_stuff(self, clock, working_screenshot):

        """
        if (K_q in self.input_controller.get_system_input()["keydown-keycodes"]):

            m2 = self.universe.get_active_map()
            for y in range(0, len(m2.master_plane.tiles)):

                for x in range(0, len(m2.master_plane.tiles[y])):
                    if ((m2.master_plane.trap_timers[y][x] > 0)):
                        log(  "1", )
                    else:
                        log(  "0", )


                log(  "" )

            log(  "\n\n" )
        """


        debug = [
            "FPS:  %d" % int(clock.get_fps()),
            #"coords:  %f, %f  (width:  %d, height: %d)" % (self.map.master_plane.players[0].x, self.map.master_plane.players[0].y, self.map.master_plane.players[0].width, self.map.master_plane.players[0].height),
            "",
            "1.  Connected sectors, sector-to-sector transitions",
            "2.  Levers/switches, scripting Event Types",
            "3.  Entity graphics, tilesheet graphics",
            "4.  Enemies interact very strangely with monkey bars.",
            "5.  Need to add x-axis smoothening when trying to drop from a monkey bar."
        ]


        #debug.append("Immediately walk down ladder, go to the right of the dividing wall, to the ground.")
        #debug.append("As the enemies bunch at the ladder, one of them for some reason will warp")
        #debug.append("on top of your position.  When you move, intersection will warp YOU into the wall...")

        #debug.append("Might be fixed via only-opposite-direction ai freeze condition.  See alrs.txt for more AI collision bugs, etc.")
        #debug.append("NOT FIXED!  Bring them up the ladder, then lure them over.  They still want to warp!")





        """
        displayed = False

        for e in self.map.master_plane.enemies:

            r = e.get_rect()
            mr = (pygame.mouse.get_pos()[0], pygame.mouse.get_pos()[1], 1, 1)
            mr = offset_rect(mr, -self.map.planes[0].x, -self.map.planes[0].y)


            #print "r = ", r
            #print "mr = ", mr
            #print ""

            if (intersect(mr, r) and (not displayed)):


                displayed = True

                #colliding = int(self.map.planets[0].check_interentity_collision( e ))

                #if (colliding):

                #    self.draw_text("normal", "enemy colliding:  true!", 5, 180, (225, 50, 50))

                #else:
                #    self.draw_text("normal", "enemy colliding:  false", 5, 180, (225, 225, 225))



                self.draw_text("normal", "enemy '%s' position:  %f, %f" % (e.name, e.x, e.y), 5, 220, (225, 225, 225))
                self.draw_text("normal", "enemy '%s' last attempted move:  %d" % (e.name, e.last_attempted_lateral_move), 5, 245, (225, 225, 225))

                self.draw_text("normal", "enemy '%s' frozen: %s" % (e.name, e.ai_frozen), 5, 270, (225, 225, 225))
        """




        """
        self.window_controller.get_geometry_controller().draw_rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (0, 0, 0))


        for a in range(0, len(frames)):


            x = a * TILE_WIDTH
            y = 0

            x += 0
            y += 0


            self.window_controller.get_geometry_controller().draw_rect(x, y, 24, 24, (0, 0, 255))

            self.set_scissor((x, y, 24, 24))

            for b in range(0, a + 1):



                for f in frames[b]:
                    (u, v) = f

                    q = u * 6

                    r = v * 4

                    if (v % 2 == 1):
                        q -= 3


                    self.window_controller.get_geometry_controller().draw_rect(x + q, y + r, 6, 4, (255, 255, 255))

            self.set_scissor(None)
        """

        (mx, my) = pygame.mouse.get_pos()

        if (0):

            m = self.universe.get_active_map()

            if (m):

                (a, b) = (
                    m.x * TILE_WIDTH,
                    m.y * TILE_HEIGHT
                )

                (c, d) = (
                    xxcamera.x,
                    xxcamera.y
                )

                (q, r) = (
                    (mx + c) - a,
                    (my + d) - b
                )

                #if (pygame.key.get_pressed()[K_LSHIFT]):
                #    p = m.get_entity_by_name("player1")
                #    p.x = (q / TILE_WIDTH) * TILE_WIDTH
                #    p.y = (r / TILE_HEIGHT) * TILE_HEIGHT

                if (False):

                    if (pygame.key.get_pressed()[K_LCTRL]):

                        p = m.get_entities_by_type(GENUS_ENEMY)

                        """
                        p[2].x = 312
                        p[2].y = 432
                        p[2].last_attempted_lateral_move = DIR_LEFT
                        p[2].direction = DIR_LEFT

                        p[2].ai_frozen = False
                        p[2].ai_frozen_for = None

                        p[1].x = 288
                        p[1].y = 432

                        p[1].last_attempted_lateral_move = DIR_RIGHT
                        p[1].direction = DIR_RIGHT
                        p[1].ai_frozen = False
                        p[1].ai_frozen_for = None
                        """

                        p[0].x = 408
                        p[0].y = 384
                        p[0].last_attempted_lateral_move = DIR_LEFT
                        p[0].direction = DIR_LEFT
                        p[0].ai_frozen = False
                        p[0].ai_frozen_for = None

                        p[1].x = 168
                        p[1].y = 384
                        p[1].last_attempted_lateral_move = DIR_LEFT
                        p[1].direction = DIR_LEFT
                        p[1].ai_frozen = False
                        p[1].ai_frozen_for = None

                    elif (K_TAB in self.input_controller.get_system_input()["keydown-keycodes"]):

                        p = m.get_entities_by_type(GENUS_ENEMY)

                        (x, y) = (216, 432)


                        for z in range(0, 8):

                            p[z].x = x
                            p[z].y = y

                            d = 1
                            if (random.randint(1, 10) >= 5):
                                d = 3
                            p[z].last_attempted_lateral_move = d
                            p[z].direction = d
                            p[z].ai_frozen = False
                            p[z].ai_frozen_for = None

                            x += (TILE_WIDTH + random.randint(1, 10))


                            log(  "===" )
                            log(  "%d:  %d, %d, %d, %d" % (z, p[z].x, p[z].y, p[z].last_attempted_lateral_move, p[z].direction) )
                            log(  "===\n" )






                    elif (pygame.key.get_pressed()[K_RCTRL]):

                        p = m.get_entities_by_type(GENUS_ENEMY)

                        data = (
                            (216, 432, 3, 3),
                            (242, 432, 3, 3),
                            (268, 432, 1, 1),
                            (301, 432, 3, 3),
                            (332, 432, 1, 1),
                            (359, 432, 3, 3),
                            (385, 432, 1, 1),
                            (410, 432, 3, 3)
                        )

                        for z in range(0, 8):

                            p[z].x = data[z][0]
                            p[z].y = data[z][1]
                            p[z].last_attempted_lateral_move = data[z][2]
                            p[z].direction = data[z][3]



        # Debug:  refresh skill billboards, etc.
        if (K_F5 in self.input_controller.get_system_input()["keydown-keycodes"]):

            toggle1 = (not toggle1)

            if (toggle1):
                rowmenu1.f_calculate_indentation = lambda y, radius = 200, offset = -50: offset + (-1 * int( math.sqrt( (radius * radius) - ((int(SCREEN_HEIGHT / 2) - y) * (int(SCREEN_HEIGHT / 2) - y)) ) )) if ( abs(int(SCREEN_HEIGHT / 2) - y) <= radius ) else 0
            else:
                rowmenu1.f_calculate_indentation = lambda y: 0

            f = open("templateX.xml", "r")
            template = f.read()
            f.close()
            root = XMLParser().create_node_from_xml(template)
            cc = root.get_first_node_by_tag("template").get_nodes_by_tags("item, item-group")
            rowmenu1.reset()
            rowmenu1.populate_from_collection(self.widget_dispatcher, cc, self.universe, self.universe.session)
            rowmenu1.focus()

        """
        if (0):#K_F2 in self.input_controller.get_system_input()["keydown-keycodes"]):

            #pixels = None

            #glReadPixels(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, GL_RGBA, GL_FLOAT, pixels)

            #print pixels
        """




        if (0 and pygame.key.get_pressed()[K_F3]):

            #draw_rect(0, 0, 640, 480, (20, 20, 20))

            #maps = self.universe.map_data[LAYER_FOREGROUND].keys()

            (gw, gh) = (1, 1)
            (cx, cy) = (320, 320)

            scale = 0.5

            (worldmap_width, worldmap_height) = (
                scale * (max(self.universe.map_data[LAYER_FOREGROUND][m].x for m in self.universe.map_data[LAYER_FOREGROUND]) - min(self.universe.map_data[LAYER_FOREGROUND][m].x for m in self.universe.map_data[LAYER_FOREGROUND])),
                scale * (max(self.universe.map_data[LAYER_FOREGROUND][m].y for m in self.universe.map_data[LAYER_FOREGROUND]) - min(self.universe.map_data[LAYER_FOREGROUND][m].y for m in self.universe.map_data[LAYER_FOREGROUND]))
            )

            (worldmap_minX, worldmap_minY) = (
                min(self.universe.map_data[LAYER_FOREGROUND][m].x for m in self.universe.map_data[LAYER_FOREGROUND]),
                min(self.universe.map_data[LAYER_FOREGROUND][m].y for m in self.universe.map_data[LAYER_FOREGROUND])
            )

            (cx, cy) = (
                320,
                240
            )

            for m in self.universe.map_data[LAYER_FOREGROUND]:

                (x, y, w, h) = (

                    int( ( (self.universe.map_data[LAYER_FOREGROUND][m].x - worldmap_minX) * gw * scale) + cx - int(worldmap_width / 2) ),
                    int( ( (self.universe.map_data[LAYER_FOREGROUND][m].y - worldmap_minY) * gh * scale) + cy - int(worldmap_height / 2) ),
                    int( (self.universe.map_data[LAYER_FOREGROUND][m].width * gw * scale) ),
                    int( (self.universe.map_data[LAYER_FOREGROUND][m].height * gh * scale) )
                )

                frame_size = max(1, int(scale))

                self.window_controller.get_geometry_controller().draw_rect(x, y, w, h, (0, 0, 0))
                self.window_controller.get_geometry_controller().draw_rect(x + frame_size, y + frame_size, w - (2 * frame_size), h - (2 * frame_size), (100, 100, 100))
                self.window_controller.get_geometry_controller().draw_rect(x + (2 * frame_size), y + (2 * frame_size), w - (4 * frame_size), h - (4 * frame_size), (225, 225, 225))


        if (K_F4 in self.input_controller.get_system_input()["keydown-keycodes"]):

            self.universe.get_timer_controller().add_singular_event_with_name(
                "timer1",
                60,
                lambda f = logn: f( "app", "Testing at %s" % time.time() )
            )

        if (0):

            xml = """
                <item name = '' title = ''>
                    <label x = '5%' y = '0' width = '90%' value = 'You have leveled up!\n[color=dim]New Level:[/color]  [color=special]5[/color]...' />
                </item>
            """

            xml2 = """
                <item name = '' title = ''>
                    <label x = '5%' y = '0' width = '90%' value = 'You have leveled up!' />
                </item>
                <item name = '' title = ''>
                    <label x = '5%' y = '0' width = '90%' value = '[color=dim]New Level:[/color]  [color=special]5[/color]...' />
                </item>
            """

            xml3 = """
                <item render-border = '0' on-escape = 'show-active-quest'>
                    <label x = '5%' y = '0' width = '90%' value = 'New Item Acquired\n[color=special]Tunic of the Bomb Master[/color]' cache-key = 'newsfeeder-generic' />
                </item>
            """

            #self.universe.newsfeeder.feed_xml(xml3)#, self.universe, self.universe.session)


        if (K_F7 in self.input_controller.get_system_input()["keydown-keycodes"]):

            remove_folder( os.path.join(self.universe.get_working_save_data_path(), "autosave1") )
            #clear_folder( os.path.join(self.universe.get_working_save_data_path(), "autosave1") )
            copy_folder( os.path.join(self.universe.get_working_save_data_path(), "autosave10"), os.path.join(self.universe.get_working_save_data_path(), "autosave1") )




        if (K_F8 in self.input_controller.get_system_input()["keydown-keycodes"]):

            #self.universe.get_active_map().run_script("xdebug", self.network_controller, self.universe, self.universe.session, [])

            #self.universe.get_active_map().get_entity_by_name("player1").x += 1

            toggled = not toggled

            if (toggled):
                self.universe.lock_with_key("asdf.test", timeout = 120, strength = LOCK_HARD)

            else:
                self.universe.unlock("asdf.test")


        if (K_F9 in self.input_controller.get_system_input()["keydown-keycodes"]):

            port = self.network_controller.get_default_port()
            result = self.network_controller.start_server(port = port)

            while ( (not result) and (port <= self.network_controller.get_default_port() + 10) ):#) ):

                port += 1
                result = self.network_controller.start_server(port = port)

        elif (K_F10 in self.input_controller.get_system_input()["keydown-keycodes"]):

            #self.network_controller.start_client()

            port = self.network_controller.get_default_port()
            result = self.network_controller.start_client(port = port)

            while ( (not result) and (port <= self.network_controller.get_default_port() + 10) ):

                log(  "trying port %d" % port )

                port += 1
                result = self.network_controller.start_client(port = port)

            #self.universe.set_session_variable("core.player-id", "2")


        """
        if (K_q in self.input_controller.get_system_input()["keydown-keycodes"]):
            self.bg_mixer.load_next_track()
        """


        #print "3*3 = ", dumb(3)
        #print "test result = ", test1()

        #draw_rect(32, 32, 64, 64, (0, 225, 0))
        #draw_rect_frame(40, 40, 100, 100, (225, 225, 225), 2)

        #draw_circle(100, 100, 60, background = (225, 225, 225))
        #draw_circle(240, 140, 60, background = (125, 125, 125, 0.5), border = (225, 25, 25))

        #draw_circle(100, 300, 60, background = (225, 125, 225), start = 35, end = 270)
        #draw_circle(240, 340, 60, background = (125, 125, 125, 0.5), border = (225, 25, 25))

        """
        angles = (0, 90, 179, 180, 181, 269, 270, 271, 290, 360)
        s = 40

        for i in range(0, len(angles)):

            angle = angles[i]
            c = 50 + (i * 30)

            log(  angle, c )

            self.window_controller.get_geometry_controller().draw_clock_rect(50 + (i * 50), 50, s, s, background = (c, c, c), degrees = angle)
            self.text_renderers["normal"].render("%d" % angle, 50 + (i * 50), 50 - self.text_renderers["normal"].font_height, (225, 225, 225))
        """

        #draw_clock_rect(40, 40, 100, 100, (225, 225, 225), None, 1, 290)


        #draw_line(0, 0, 640, 480, (25, 25, 225))
        #draw_line(20, 240, 620, 240, (25, 255, 25), 5)


        #print self.text_renderers["normal"].size("Press [action] to use ")
        #print "\t", self.text_renderers["normal"].size("lever")
        #print "\t", int(0.85 * 180.0)


        """
        if (K_F4 in self.input_controller.get_system_input()["keydown-keycodes"]):
            self.control_center.get_debug_controller().save_object( self.menu_controller )
        """



        if (K_F11 in self.input_controller.get_system_input()["keydown-keycodes"]):

            (texture_id, w, h) = self.window_controller.clip_backbuffer()

            working_screenshot = texture_id
            working_screenshot_length = w

        if (working_screenshot):

            self.window_controller.get_gfx_controller().draw_texture(working_screenshot, 0, 0, working_screenshot_length, working_screenshot_length)


            if ( not pygame.key.get_pressed()[K_F11] ):

                working_screenshot = None


        """
        if (0):

            if (K_F11 in self.input_controller.get_system_input()["keydown-keycodes"]):

                toggled = not toggled

                if (toggled):
                    se.explode()

            if (toggled):

                self.window_controller.get_geometry_controller().draw_rect(0, 0, 640, 480, (20, 20, 20))

                se.process()
                se.draw()
        """

        #if (toggled):
        #    player = self.universe.get_active_map().get_entity_by_name("player1")
        #    log(  "player:  ", (player.x, player.y) )
        #    log(  "\tfloat conversion:  ", (float(player.x), float(player.y)) )
        #    log(  "\trounded:  ", (player.get_x(), player.get_y()) )


        #draw_rect(0, 0, 640, 480, (20, 20, 20))
        #draw_rect_with_horizontal_gradient(85, 265, 520, 40, (35, 35, 35), (55, 55, 55))


        """
        scale = 1
        #draw_rect(100, 100, 128, 128, (75, 75, 175))
        for i in range(1, 6):
            x = (i - 1) * 96
            self.window_controller.get_gfx_controller().draw_texture(self.additional_sprites["fill-patterns"][i].get_texture_id(), x, 0, 128 * scale, 128 * scale)
        """

        """
        zebY = False
        for y in range(0, 3):
            zebX = (not zebY)
            for x in range(0, 4):

                if ((x + int(zebY)) % 2 == 1):
                    self.window_controller.get_geometry_controller().draw_rect(x * 24 * scale, y * 24 * scale, 24 * scale, 24 * scale, (225, 225, 225, 0.5))
            zebY = not zebY
        """



    def debug_create_composite(self):

        # Metadata node
        root = XMLNode("metadata")

        surface = pygame.display.get_surface()
        surface_buffer = surface.get_buffer()
        log(  surface )
        img = pygame.image.fromstring(surface_buffer.raw, (640, 480), "RGBA")

        #print 5/0

        pygame.image.save(surface, "surface1.png")

        maps = self.universe.map_data[LAYER_FOREGROUND].keys()

        # Alias?
        map_data = {LAYER_FOREGROUND:{}}
        log(  maps )

        r = [0, 0, 0, 0]

        for i in range(0, len(maps)):

            #name = "Untitled Map", x = 0, y = 0, is_new = False, session = None, quests = None, is_editor = False):
            #log(  "Bad create_map params..." )
            #log(  5/0 )

            m = self.universe.create_map(
                name = maps[i],
                x = 0,
                y = 0,
                control_center = self.control_center
            )

            #m = self.universe.create_map(maps[i], 0, 0, False, self.widget_dispatcher, self.network_controller, self.universe, self.universe.session)
            map_data[LAYER_FOREGROUND] = self.universe.map_data[LAYER_FOREGROUND][maps[i]]


            offscreen_surface = pygame.Surface((m.width * TILE_WIDTH, m.height * TILE_HEIGHT))

            (x, y, w, h) = (map_data[LAYER_FOREGROUND].x * TILE_WIDTH, map_data[LAYER_FOREGROUND].y * TILE_HEIGHT, map_data[LAYER_FOREGROUND].width * TILE_WIDTH, map_data[LAYER_FOREGROUND].height * TILE_HEIGHT)

            r = (
                min(r[0], x),
                min(r[1], y),
                max(r[2], x + w),
                max(r[3], y + h)
            )






        huge_surface = pygame.surface.Surface((r[2] - r[0], r[3] - r[1])).convert()

        font = pygame.font.Font(os.path.join(FONT_PATH, 'jupiterc.ttf'), 18)


        for i in range(0, len(maps)):

            # Metadata node for current map
            node = root.add_node(
                XMLNode("map").set_attributes({
                    "name": maps[i]
                })
            )

            # Set attributes
            node.set_attributes({
                "x": x - r[0],
                "y": y - r[1],
                "w": w,
                "h": h
            })

            #name = "Untitled Map", x = 0, y = 0, is_new = False, session = None, quests = None, is_editor = False):
            #log(  "Bad create_map params..." )
            #log(  5/0 )
            #m = self.universe.create_map(maps[i], 0, 0, False, self.widget_dispatcher, self.network_controller, self.universe, self.universe.session)
            m = self.universe.create_map(
                name = maps[i],
                x = 0,
                y = 0,
                control_center = self.control_center
            )

            m.load(
                filepaths = {
                    "map": os.path.join( self.universe.get_working_map_data_path(None), "%s.xml" % maps[i] ),
                    "dialogue": os.path.join( self.universe.get_working_map_data_path(None), "dialogue", "%s.dialogue.xml" % maps[i] ),
                    "menu": os.path.join( self.universe.get_working_map_data_path(None), "levelmenus", "%s.levelmenus.xml" % maps[i] )
                },
                options = {
                    "is-new": False
                },
                control_center = self.control_center
            )

            map_data[LAYER_FOREGROUND] = self.universe.map_data[LAYER_FOREGROUND][maps[i]]

            #offscreen_surface = pygame.Surface((m.width * TILE_WIDTH, m.height * TILE_HEIGHT))

            (x, y, w, h) = (map_data[LAYER_FOREGROUND].x * TILE_WIDTH, map_data[LAYER_FOREGROUND].y * TILE_HEIGHT, map_data[LAYER_FOREGROUND].width * TILE_WIDTH, map_data[LAYER_FOREGROUND].height * TILE_HEIGHT)

            #huge_surface.blit(surface.copy(), (x, y), (0, 0, 640, 480))

            for u in range(0, (w + 639) / 640):

                for v in range(0, (h + 479) / 480):

                    self.window_controller.get_geometry_controller().draw_rect(0, 0, 640, 480, (0, 0, 0))
                    m.draw(-(u * 640), -(v * 480), self.tilesheet_sprite, self.additional_sprites, MODE_GAME, text_renderer = self.text_renderers["normal"], window_controller = self.window_controller)

                    z = pygame.image.tostring(surface, "RGBA")
                    q = pygame.image.fromstring(z, (640, 480), "RGBA")

                    (c, d) = (
                        min(640, w - (u * 640)),
                        min(480, h - (v * 480))
                    )

                    huge_surface.blit(q, (x - r[0] + (u * 640), y - r[1] + (v * 480), c, d), (0, 0, c, d))

            # Frame each map?
            if (1):

                # Render frame around map with title; 2 pixel thickness.
                pygame.draw.rect(huge_surface, (225, 225, 25), (x - r[0], y - r[1], w, h), 2)

                # Title
                huge_surface.blit(
                    font.render( "%s" % maps[i], True, (225, 225, 225) ),
                    (x - r[0], y - r[1])
                )

            #pygame.image.save(surface, os.path.join("renders", "%s.png" % maps[i]))

        # Save metadata
        f = open(
            os.path.join("renders", "metadata.xml"),
            "w"
        )

        # Serialize
        f.write(
            root.compile_xml_string()
        )

        # Done
        f.close()


        # Save composite render
        pygame.image.save(huge_surface, os.path.join("renders", "composite.png"))

        log(  r )
        log(  5/0 )
