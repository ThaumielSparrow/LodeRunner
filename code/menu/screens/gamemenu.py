import os
import sys

import math
import random

import time

from code.render.glfunctions import set_video_mode

from code.menu.menu import Menu

from code.controllers.intervalcontroller import IntervalController

from code.tools.eventqueue import EventQueue
from code.tools.xml import XMLParser

from code.game.universe import Universe

from code.utils.common import coalesce, intersect, offset_rect, log, log2, logn, xml_encode, xml_decode, translate_rgb_to_string

from code.constants.common import SCREEN_WIDTH, SCREEN_HEIGHT, PAUSE_MENU_X, PAUSE_MENU_Y, PAUSE_MENU_WIDTH, PAUSE_MENU_HEIGHT, MODE_GAME, TILE_WIDTH, TILE_HEIGHT, DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT, LAYER_FOREGROUND, LAYER_BACKGROUND, GENUS_PLAYER
from code.constants.newsfeeder import *

from code.constants.states import STATUS_INACTIVE

from code.constants.sound import *

from code.constants.paths import CONFIG_PATH, REPLAYS_PATH

from pygame.locals import K_ESCAPE, K_RETURN
import pygame
from code.render.glfunctions import render_init


# Local constants
CREDITS_TIMER_MAX = 180


# Main menu (v2)
class GameMenu(Menu):

    def __init__(self):

        Menu.__init__(self)


        # Birth time
        self.birth_time = time.time()


        # Game menu doesn't need the lightbox effect at all
        self.lightbox_controller.configure({
            "interval": 0,
            "target": 0
        })


        # The game menu might track some events across the handle_event routine into the additional_processing routine.
        # We'll use a flag system for this...
        self.flags = {
            "quit-game": False,             # When it's time to quit, we'll flip this on

            "app-directive": None,          # If we need to send a message to the main app (start-game, etc.), we'll store it here
            "send-app-directive": False,    # We also need to know exactly when to send the directive (this is all kind of queued and hacky)
            "refresh": False                # Sometimes we want to refresh the main menu's pages after sending an app directive
        }


        # We have kind of a modal widget in the background, kind of like a letterbox.
        # It's just a simple row menu, constantly shown separately from the menu pages...
        self.backdrop_widget = None

        # The game menu always has a movie showing on the side.  We will just use a UI GIF for the movie, whenever we load it.
        # Each menu page (root, story options, config options, etc.) will have its own GIF, though; we'll keep a stack of them.
        self.movie_widgets = []


        # Render a series of hard-coded credits at the bottom of the screen when the game loads
        self.credits = [
            {
                "text": "[color=dim]Original Lode Runner concept:[/color]  Doug Smith",
                "x": (SCREEN_WIDTH - PAUSE_MENU_X),
                "align": "right"
            },
            {
                "text": "[color=dim]Main character player animation:[/color]  Dennis Busch",
                "x": (SCREEN_WIDTH - PAUSE_MENU_X),
                "align": "right"
            },
            {
                "text": "[color=dim]Music, Sound FX, Programming, etc.:[/color]  LordZagreus",
                "x": (SCREEN_WIDTH - PAUSE_MENU_X),
                "align": "right"
            },
            {
                "text": "[color=dim]Game code technologies:[/color]  Python[color=dim],[/color] C [color=dim](OpenGL rendering)[/color]",
                "x": (SCREEN_WIDTH - PAUSE_MENU_X),
                "align": "right"
            },
            {
                "text": "[color=dim]Music production software:[/color]  FruityLoops",
                "x": (SCREEN_WIDTH - PAUSE_MENU_X),
                "align": "right"
            },
            {
                "text": "[color=dim]Sound FX production software:[/color]  FruityLoops[color=dim],[/color] sfxr",
                "x": (SCREEN_WIDTH - PAUSE_MENU_X),
                "align": "right"
            },
            {
                "text": "[color=dim]Bugs:[/color]  Mike Doty",
                "x": (SCREEN_WIDTH - PAUSE_MENU_X),
                "align": "right"
            },
            {
                "text": "[color=dim]Thank you for downloading[/color] A Lode Runner Story[color=dim]![/color]",
                "x": (SCREEN_WIDTH - PAUSE_MENU_X),
                "align": "right"
            }
        ]

        # Base the current credits display on a timer offset
        self.credits_timer = CREDITS_TIMER_MAX

        # Use an interval controller to fade text
        self.credits_alpha_controller = IntervalController(
            interval = 0,
            target = 1.0,
            speed_in = 0.0105,
            speed_out = 0.0075,
            integer_based = False
        )

        # Use an interval controller to slide the credits off of the screen
        # as they are fading out.
        self.credits_vslide_controller = IntervalController(
            interval = 0,
            target = 0,
            speed_in = 0.225,
            speed_out = 1, # Not used currently (?)
            integer_based = False
        )


        # I'm going to give the entire GameMenu an hslide controller.
        # Certain transitions (new game, coop game, quit, etc.) will
        # slide the entire main menu to the side while fading away...
        self.hslide_controller = IntervalController(
            interval = 0,
            target = 0,
            speed_in = 15,
            speed_out = 15,
            integer_based = True
        )


        # Fire build event
        self.fire_event("build")

        # Fire a decorate event to create the backdrop widget and the initial movie widget GIF.
        # We won't do this on refreshes; this is a one-time deal!
        self.fire_event("decorate")


    # Get the active movie widget, if we have one...
    def get_active_movie_widget(self):

        # Validate
        if ( len(self.movie_widgets) > 0 ):

            # Return the highest on the stack
            return self.movie_widgets[-1]

        # No active movie (must not be ready yet?)
        else:

            return None


    # Get all movie widgets
    def get_movie_widgets(self):

        return self.movie_widgets


    # Add a new movie widget to the stack
    def add_movie_widget(self, control_center):

        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Add a new GIF; the widgets are just GIFs
        self.movie_widgets.append(
            widget_dispatcher.create_gif().configure({
                "universe": "mainmenu",
                "map": "animation2",
                "draw-all-maps": True, # So we can slide left/right and see everything...
                "render-background": False, # We'll actually handle this in this menu's .draw() routine
                "x": 0,
                "y": 0,
                "width": 400,
                "height": 400,
                "alpha-controller": {
                    "speed-in": 0.025,       # I want the cross fades to go a little more slowly than the default alpha rate
                    "speed-out": 0.05
                }
            })
        )

        # Return a handle
        return self.movie_widgets[-1]


    # Certain menu actions (changing to a new submenu) will add a new movie widget on top
    # of the stack, transitioning to the new set of clips...
    def add_movie_widget_via_event(self, event, control_center, universe):

        # Convenience
        params = event.get_params()


        # First, let's handle the movie transition.  Begin by hiding the currently active movie widget...
        self.get_active_movie_widget().hide()

        # Lock camera on the active movie widget until we return to this page
        self.get_active_movie_widget().universe.get_camera().lock()


        # Now let's add a new movie widget to the stack; we'll use it for the next section...
        movie_widget = self.add_movie_widget(control_center)

        # We have to process it once to get the universe ready (hacky)
        movie_widget.process(control_center, universe)


        log2( "Defaulting to '%s'" % params["rel"] )


        # Jump immediately to the default map for this submenu page
        movie_widget.universe.build_map_on_layer_by_name( params["rel"], LAYER_FOREGROUND, game_mode = MODE_GAME, control_center = control_center, ignore_adjacent_maps = False )
        movie_widget.universe.activate_map_on_layer_by_name( params["rel"], LAYER_FOREGROUND, control_center = control_center )
        movie_widget.universe.set_active_map_by_name( params["rel"] )


        """
        # Grab a reference to the default map
        m = movie_widget.universe.get_map_on_layer_by_name( params["rel"], LAYER_FOREGROUND )

        # Validate
        if (m):

            # Set map's type to "gif" to prevent autosaves, etc.
            m.set_type("gif")
        """


        # Check for a given replay data path
        replay_data_path = None

        # Validate
        if ( "replay-file" in params ):

            log( "Replay file default:  '%s'" % params["replay-file"] )

            # Read filepath
            replay_data_path = params["replay-file"]


        # Begin playback on new gif on given map name
        movie_widget.begin_playback( params["rel"], replay_data_path )


        # I want to make sure the camera's centered on the default map for the new submenu's movie widget
        movie_widget.universe.center_camera_on_map(
            movie_widget.universe.get_active_map()
        )

        # Position the camera instantly
        movie_widget.universe.get_camera().zap()


    # Remove the active movie widget
    def remove_active_movie_widget(self):

        # Sanity
        if ( len(self.movie_widgets) > 0 ):

            # We'll return the one we're removing in case we want to do anything with it...
            return self.movie_widgets.pop()


    # Handle an event
    def handle_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        (action, params) = (
            event.get_action(),
            event.get_params()
        )


        log2("%s\n" % action)


        # Set up the initial page
        if ( action == "build" ):

            results.append(
                self.handle_build_event(event, control_center, universe)
            )


        # Refresh pages
        elif ( action == "refresh" ):

            results.append(
                self.handle_refresh_event(event, control_center, universe)
            )


        # Set up the various window dressings (movie, backdrop, etc.)
        elif ( action == "decorate" ):

            results.append(
                self.handle_decorate_event(event, control_center, universe)
            )


        # Redecorate widgets only (not the movie gifs)
        elif ( action == "redecorate" ):

            results.append(
                self.handle_redecorate_event(event, control_center, universe)
            )


        # Play a sound effect
        elif ( action == "play-sound" ):

            results.append(
                self.handle_play_sound_event(event, control_center, universe)
            )


        # Transition to another menu screen
        elif ( action == "transition" ):

            results.append(
                self.handle_transition_event(event, control_center, universe)
            )


        # Commit the transition, loading in a new menu page
        elif ( action == "finish:transition" ):

            results.append(
                self.handle_finish_transition_event(event, control_center, universe)
            )


        # Show the audio settings in a popup dialog
        elif ( action == "show:audio-settings" ):

            results.append(
                self.handle_show_audio_settings_event(event, control_center, universe)
            )


        # Increase audio settings volume level for active selection
        elif ( action == "update:audio-settings:increase" ):

            results.append(
                self.handle_update_audio_settings_increase_event(event, control_center, universe)
            )

        # Decrease audio settings volume level for active selection
        elif ( action == "update:audio-settings:decrease" ):

            results.append(
                self.handle_update_audio_settings_decrease_event(event, control_center, universe)
            )


        # Show the display settings in a popup dialog
        elif ( action == "show:display-settings" ):

            results.append(
                self.handle_show_display_settings_event(event, control_center, universe)
            )


        # Update fullscreen preference
        elif ( action == "fullscreen:set" ):

            results.append(
                self.handle_fullscreen_set_event(event, control_center, universe)
            )


        # Show available languages in a popup dialog
        elif ( action == "show:language-settings" ):

            results.append(
                self.handle_show_language_settings_event(event, control_center, universe)
            )


        # Update language preference
        elif ( action == "language:set" ):

            results.append(
                self.handle_language_set_event(event, control_center, universe)
            )


        # Prompt for keyboard control customization for a given input action
        elif ( action == "show:edit-keyboard-control" ):

            results.append(
                self.handle_show_edit_keyboard_control_event(event, control_center, universe)
            )


        # Update a given keyboard control, set to a given keycode
        elif ( action == "game:update-keyboard-control" ):

            results.append(
                self.handle_game_update_keyboard_control_event(event, control_center, universe)
            )


        # Transition to a list of gamepads (this is just like a transition, but there's a little extra conditional / counting logic
        # Transition to another menu screen
        elif ( action == "show:gamepads" ):

            results.append(
                self.handle_show_gamepads_event(event, control_center, universe)
            )


        # Commit the transition, loading in a new menu page
        elif ( action == "finish:show:gamepads" ):

            results.append(
                self.handle_finish_show_gamepads_event(event, control_center, universe)
            )


        # Select a gamepad device to use
        elif ( action == "game:select-gamepad" ):

            results.append(
                self.handle_game_select_gamepad_event(event, control_center, universe)
            )


        # Prompt for gamepad control customization for a given input action
        elif ( action == "show:edit-gamepad-control" ):

            results.append(
                self.handle_show_edit_gamepad_control_event(event, control_center, universe)
            )


        # Update a given gamepad control, set to a given device input type / index / whatever
        elif ( action == "game:update-gamepad-control" ):

            results.append(
                self.handle_game_update_gamepad_control_event(event, control_center, universe)
            )


        # The "update gamepad control" dialog has a keyboard listener that will only care about the ESC key...
        elif ( action == "abort:edit-gamepad-control" ):

            results.append(
                self.handle_abort_edit_gamepad_control_event(event, control_center, universe)
            )


        elif ( action == "show:reset-gamepad-controls" ):

            results.append(
                self.handle_show_reset_gamepad_controls_event(event, control_center, universe)
            )


        elif ( action == "game:reset-gamepad-controls" ):

            results.append(
                self.handle_game_reset_gamepad_controls_event(event, control_center, universe)
            )


        elif ( action == "show:reset-keyboard-controls" ):

            results.append(
                self.handle_show_reset_keyboard_controls_event(event, control_center, universe)
            )


        elif ( action == "game:reset-keyboard-controls" ):

            results.append(
                self.handle_game_reset_keyboard_controls_event(event, control_center, universe)
            )


        # Save controls
        elif ( action == "game:save-controls" ):

            results.append(
                self.handle_game_save_controls_event(event, control_center, universe)
            )


        # Return to previous page without animation
        elif ( action == "hide" ):

            results.append(
                self.handle_hide_event(event, control_center, universe)
            )


        # Return to the previous menu page
        elif ( action == "back" ):

            results.append(
                self.handle_back_event(event, control_center, universe)
            )


        # Restore previous page into view after a back event concludes
        elif ( action == "finish:back" ):

            results.append(
                self.handle_finish_back_event(event, control_center, universe)
            )


        # Send the app a special directive (e.g. start game, join multiplayer game, whatever)
        elif ( action == "app-directive" ):

            results.append(
                self.handle_app_directive_event(event, control_center, universe)
            )


        # Follow through on an app directive
        elif ( action == "fwd:finish:app-directive" ):

            results.append(
                self.handle_fwd_finish_app_directive_event(event, control_center, universe)
            )


        # Trigger quit game (slide and hide, signal afterward)
        elif ( action == "quit-game" ):

            results.append(
                self.handle_quit_game_event(event, control_center, universe)
            )

        # Commit the (forwarded) quit event
        elif ( action == "fwd:finish:quit-game" ):

            results.append(
                self.handle_fwd_finish_quit_game_event(event, control_center, universe)
            )


        # Return events
        return results


    def additional_processing(self, control_center, universe, debug = False):

        # Events
        results = EventQueue()


        # Process the menu-level slide controller
        results.append(
            self.hslide_controller.process()
        )



        # Process the backdrop widget
        self.backdrop_widget.process(control_center, universe)



        for movie_widget in self.get_movie_widgets():

            # Process (to initialize universe if not yet configured, I think...?)
            if (not movie_widget.universe):

                movie_widget.process(control_center, universe)

            if ( (movie_widget.alpha_controller.get_interval() > 0) or (movie_widget.alpha_controller.get_target() > 0) ):

                movie_widget.process(control_center, universe)


        #return results


        # Process the active movie widget
        movie_widget = self.get_active_movie_widget()

        for movie_widget in self.get_movie_widgets():


            # Fetch the universe camera
            camera = movie_widget.universe.get_camera()


            # We're going to handle the accordion-ish movie widget camera positioning.
            # Let's start by grabbing a handle to the current menu page
            page = self.get_active_page()


            # Don't run this logic if the page is locked...
            if ( page.get_attribute("-locked") != "yes" ):

                # We'll only run this logic if the active page is of the .main-menu class;
                # we don't process movie transition for "press any key" dialogs or any such non-row menu pages.
                if ( page.css_class == "main-menu" ):

                    # Which map does the selected option on the current page relate to?
                    map_name = page.get_active_widget().get_rel()


                    # page should have a hidden widget with replay filepath data...
                    page_hidden_widget = page.get_active_widget().find_widget_by_id("replay-file")

                    # Replay path?
                    replay_data_path = None

                    # I need to grab the replay data filepath from the nested Hidden widget, if that widget even exists...
                    if (page_hidden_widget):

                        # Read in replay data path
                        replay_data_path = page_hidden_widget.get_rel()


                    # Specifically reference the active movie widget here
                    active_movie_widget = self.get_active_movie_widget()
                    logn( "movie-previews", "REPLAY:  %s (%s) (active:  %s)\n" % (replay_data_path, map_name, active_movie_widget.universe.get_active_map().get_name()))

                    # Make sure the universe has loaded into the universe.
                    if ( not active_movie_widget.universe.loaded_map_on_layer_by_name(map_name, LAYER_FOREGROUND) ):

                        # Quickly build the map
                        active_movie_widget.universe.build_map_on_layer_by_name(map_name, LAYER_FOREGROUND, game_mode = MODE_GAME, control_center = control_center, ignore_adjacent_maps = False)

                        # Grab a reference to that map
                        m = active_movie_widget.universe.get_map_on_layer_by_name(map_name, LAYER_FOREGROUND)

                        # Validate
                        if (m):

                            # Set map's type to "gif" to prevent autosaves, etc.
                            m.set_type("gif")
                            logn( "movie-previews", m.get_name() + " ... " + "\n" )

                        else:
                            logn( "gamemenu", "Aborting:  Invalid movie widget!" )
                            sys.exit()


                    logn( "movie-previews", "%s -vs- %s (%s) (active map name = '%s')\n" % (map_name, active_movie_widget.universe.get_active_map(), active_movie_widget, active_movie_widget.universe.active_map_name ) )
                    # If we should move to a new map, then we should also load new replay data
                    if (
                        ( map_name != active_movie_widget.universe.get_active_map().get_name() ) or
                        ( map_name == "root.story" and active_movie_widget.universe.get_active_map().has_replay_data() == False ) # Brutal hack!  root.story is the default menu selection, and this helps me "force" playback on load
                    ):

                        # Begin / resume playback on the current gif
                        active_movie_widget.begin_playback(map_name, replay_data_path)

                        log2( "Replay:  Updating replay data using '%s'" % replay_data_path )


            # Get the given map
            m = movie_widget.universe.get_active_map()#get_map_on_layer_by_name(map_name, LAYER_FOREGROUND)

            # Validate
            if (m):

                # Find the center of the map
                (cx, cy) = (
                    (m.x * TILE_WIDTH) + int( (m.width * TILE_WIDTH) / 2 ),
                    (m.y * TILE_HEIGHT) + int( (m.height * TILE_HEIGHT) / 2 )
                )

                # Set the camera to center on that center position
                camera.configure({
                    "target-x": cx - int( camera.get_width() / 2 ),
                    "target-y": cy - int( camera.get_height() / 2 )
                })


            # **hard-coded pan speeds
            camera.pan(1.5, 1.5)


        # Do we have credits remaining to process?
        if (
            ( len(self.credits) > 0 ) and
            ( (time.time() - self.birth_time) >= 1.5 ) # Hacked-in delay; don't roll credits immediately, it's awkward looking
        ):

            # Tick timer down once we reach full visibility
            if ( self.credits_alpha_controller.get_interval() == 1.0 ):
                self.credits_timer -= 1


            # Process fade controller
            self.credits_alpha_controller.process()

            # Process vslide controller
            self.credits_vslide_controller.process()


            # Timer done?
            if ( self.credits_timer <= 0 ):

                # Call for a fade
                self.credits_alpha_controller.dismiss()

                # Begin slide off screen
                self.credits_vslide_controller.set_target(75) # That should be enough to hide it

                # Check for full fade
                if ( self.credits_alpha_controller.get_interval() == 0 ):

                    # Remove previous credit listing
                    self.credits.pop(0)

                    # Do we have more credits?  If so,
                    # fade back in
                    if ( len(self.credits) > 0 ):

                        # Show next credit
                        self.credits_alpha_controller.summon()

                        # Reset vslide controller
                        self.credits_vslide_controller.set_interval(0)
                        self.credits_vslide_controller.set_target(0)

                        # Reset timer
                        self.credits_timer = CREDITS_TIMER_MAX



        # Quit game?
        if (self.flags["quit-game"]):

            results.add(
                action = "quit-game"
            )

        # Send an app directive?
        elif (self.flags["send-app-directive"]):

            results.add(
                action = self.flags["app-directive"]
            )

            log2( self.flags["app-directive"] )

            # Disable flag; it's a single-use event
            self.flags["send-app-directive"] = False


            # After we're done handling the directive (i.e. playing the game or whatever), let's make sure the hslide controller is set to slide back into view...
            self.hslide_controller.configure({
                "target": 0
            })


        # Return events
        return results


    # Game menu does a little more drawing then a typical Menu (it draws the movie)
    def draw(self, tilesheet_sprite, additional_sprites, text_renderer, window_controller):

        # Clear the screen with the hard-coded default background color, just as a backdrop for each of the movie widgets (GIFs)
        window_controller.get_geometry_controller().draw_rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (25, 25, 25, 1))


        # Loop each available movie widget
        for movie_widget in self.get_movie_widgets():

            # Movie rendering point
            (rx, ry) = (
                200 + self.hslide_controller.get_interval(),
                40
            )

            # Only render visible movie widgets
            if ( (movie_widget.alpha_controller.get_interval() > 0) or (movie_widget.alpha_controller.get_target() > 0) ):

                # Render the movie widget (just a GIF)
                movie_widget.draw(rx, ry, tilesheet_sprite, additional_sprites, text_renderer, window_controller)


        # Now let's render a spotlight effect on the movie area.  First we define the radius...
        radius = 200

        # Now render the "spotlight" effect
        window_controller.get_geometry_controller().draw_exclusive_circle_with_radial_gradient(rx + radius, ry + radius, radius, (0, 0, 0, 0.0), (0, 0, 0, 1.0))


        # Continuing, render the backdrop widget (letterbox type thing)
        self.backdrop_widget.draw(0, 0, tilesheet_sprite, additional_sprites, text_renderer, window_controller)


        # Standard Menu page rendering
        if (not self.is_dismissed):

            # Now render the overlays in lowest-to-highest order...
            for z in range( 0, len(self.widgets) ):

                # Don't bother rendering "invisible" widgets (still fading in, dismissed and hidden, whatever...)
                if ( self.widgets[z].alpha_controller.get_interval() > 0 ):

                    self.widgets[z].draw(self.x + self.hslide_controller.get_interval(), self.y, tilesheet_sprite, additional_sprites, text_renderer, window_controller)


        # Do we have remaining credits to render?
        if ( len(self.credits) > 0 ):

            # Render current credit with current fade value
            text_renderer.render_with_wrap( self.credits[0]["text"], self.credits[0]["x"], SCREEN_HEIGHT - (text_renderer.font_height + 15) + int( self.credits_vslide_controller.get_interval() ), (175, 175, 175, self.credits_alpha_controller.get_interval()), align = self.credits[0]["align"], color_classes = { "dim": (125, 125, 125, self.credits_alpha_controller.get_interval()) } )


        #for i in range( 0, len(self.movie_widgets) ):
        #    text_renderer.render_with_wrap( "%d)  map %s, alpha %s, camera @ (%s, %s) -> (%s, %s)" % (i, self.movie_widgets[i].universe.get_active_map().name, self.movie_widgets[i].alpha_controller.get_interval(), self.movie_widgets[i].universe.get_camera().x, self.movie_widgets[i].universe.get_camera().y, self.movie_widgets[i].universe.get_camera().target_x, self.movie_widgets[i].universe.get_camera().target_y), 5, SCREEN_HEIGHT - 5 - ( (len(self.movie_widgets) - i) * text_renderer.font_height), (225, 225, 225) )


    # Build the main menu
    def handle_build_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Get the template for the base of the main menu
        template = self.fetch_xml_template("mainmenu.root").add_parameters({
            "@x": xml_encode( "%d" % 400 ), # hard-coded
            "@y": xml_encode( "%d" % int(SCREEN_HEIGHT / 2) ),
            "@width": xml_encode( "%d" % SCREEN_WIDTH ),
            "@height": xml_encode( "%d" % 360 ) # hard-coded
        })

        # Compile template
        root = template.compile_node_by_id("menu")

        # Create widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("mainmenu.root")

        # Set custom indentation for an arc effect
        widget.configure({
            "custom-indentation-callback": lambda y, radius = 200, offset = -50: offset + (-1 * int( math.sqrt( (radius * radius) - ((int(SCREEN_HEIGHT / 2) - y) * (int(SCREEN_HEIGHT / 2) - y)) ) )) if ( abs(int(SCREEN_HEIGHT / 2) - y) <= radius ) else 0,
        })

        # I prefer to slow down the default fade speeds a little bit for the main menu pages
        widget.configure_alpha_controller({
            "speed-in": 0.025,
            "speed-out": 0.045
        })

        # I also heavily customize the vertical slide controller, even using an accelerator
        widget.vslide_controller.configure({
            "speed-in": 6.25,
            "speed-out": 8.75,
            "accelerator": lambda speed, dy, step = 35, multiplier_per_step = 1.0 + (.00625 / 2): ( ( int(dy / step) * multiplier_per_step ) * speed ) if (dy >= step) else speed
        })


        # Add the new page
        self.add_widget_via_event(widget, event)

        # Return events
        return results


    # Refresh all pages
    def handle_refresh_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Refresh pages
        self.refresh_pages(control_center, universe, curtailed_count = 0)

        # Return events
        return results


    # Build static main menu decoration, including the backdrop and the initial movie widget
    def handle_decorate_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Get the template for the main menu backdrop
        template = self.fetch_xml_template("mainmenu.backdrop").add_parameters({
            "@x": xml_encode( "%d" % PAUSE_MENU_X ),
            "@y": xml_encode( "%d" % int(PAUSE_MENU_Y / 2) ),
            "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT )
        })

        # Compile template
        root = template.compile_node_by_id("menu")

        # Create backdrop widget
        self.backdrop_widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        self.backdrop_widget.set_id("mainmenu-backdrop")

        self.backdrop_widget.focus()
        #self.backdrop_widget.show()


        """ Movie setup """
        # Set up the first movie widget for the root menu.
        # Going forward, we'll do this in the "transition" event...
        movie_widget = self.add_movie_widget(control_center)

        # We process one frame of the widget to set up the universe.  It's a brutal hack.  **HACK
        movie_widget.process(control_center, universe)



        # I think we must hard-code the initial input film
        replay_data_path = os.path.join(REPLAYS_PATH, "root.story.input.txt")
        movie_widget.begin_playback("root.story", replay_data_path)


        # I want to make sure the camera's centered on the default map for the new submenu's movie widget
        movie_widget.universe.center_camera_on_map(
            movie_widget.universe.get_active_map()
        )

        # Position the camera instantly
        movie_widget.universe.get_camera().zap()


        # Return events
        return results


    # Rebuild title bar and subtitle (e.g. after a language change).
    # Do not rebuild movie widgets.
    def handle_redecorate_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Get the template for the main menu backdrop
        template = self.fetch_xml_template("mainmenu.backdrop").add_parameters({
            "@x": xml_encode( "%d" % PAUSE_MENU_X ),
            "@y": xml_encode( "%d" % int(PAUSE_MENU_Y / 2) ),
            "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT )
        })

        # Compile template
        root = template.compile_node_by_id("menu")

        # Create backdrop widget
        self.backdrop_widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        self.backdrop_widget.set_id("mainmenu-backdrop")

        self.backdrop_widget.focus()


        # Return events
        return results


    # Play a sound effect
    def handle_play_sound_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Validate param
        if ( "sound" in params ):

            # The sound parameter is a human readable string, let's see which one we want
            if ( params["sound"] == "confirm" ):

                # Play "confirm" sound effect
                control_center.get_sound_controller().queue_sound(SFX_CONFIRM)


        # Return events
        return results


    # Transition to a new submenu screen / page
    def handle_transition_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Transition to a new movie
        self.add_movie_widget_via_event(event, control_center, universe)


        # Now we need to slide away the current page
        page = self.widgets[-1]

        # The current page needs to remember the target destination (across events)
        page.set_attribute( "param.target", params["target"] )

        # Also mark the current page as "locked" as we begin to transition away from it
        page.set_attribute( "-locked", "yes" )


        # Check special attributes
        for key in ("keyboard-translations", "gamepad-translations", "continue-game-check"):

            if ( key in params ):
                page.set_attribute(key, params[key])


        # Slide it away
        page.slide(
            DIR_DOWN,
            amount = SCREEN_HEIGHT,
            on_complete = "finish:transition"
        )

        # Don't quite fully hide this top page, so that the Menu doesn't take it away (it takes away fully-gone top pages)
        page.hide(target = 0.01)

        # Return events
        return results


    # Finish a transition event.  Create the new submenu page, slide it in...
    def handle_finish_transition_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the widget dispatcher;
        widget_dispatcher = control_center.get_widget_dispatcher()

        # and the input controller
        input_controller = control_center.get_input_controller()


        # Where were we heading, again?
        target = self.widgets[-1].get_attribute("param.target")


        # Fetch the template for the target screen
        template = self.fetch_xml_template(target).add_parameters({
            "@x": xml_encode( "%d" % 400 ), # hard-coded
            "@y": xml_encode( "%d" % int(SCREEN_HEIGHT / 2) ),
            "@width": xml_encode( "%d" % SCREEN_WIDTH ),
            "@height": xml_encode( "%d" % 360 ) # hard-coded
        })

        # Include keyboard translations?
        if ( self.widgets[-1].get_attribute("keyboard-translations") == "on" ):

            template.add_parameters({
                "@keyboard-translations.left": xml_encode( input_controller.fetch_keyboard_translation("left") ),
                "@keyboard-translations.right": xml_encode( input_controller.fetch_keyboard_translation("right") ),
                "@keyboard-translations.up": xml_encode( input_controller.fetch_keyboard_translation("up") ),
                "@keyboard-translations.down": xml_encode( input_controller.fetch_keyboard_translation("down") ),
                "@keyboard-translations.dig-left": xml_encode( input_controller.fetch_keyboard_translation("dig-left") ),
                "@keyboard-translations.dig-right": xml_encode( input_controller.fetch_keyboard_translation("dig-right") ),
                "@keyboard-translations.dig-forward": xml_encode( input_controller.fetch_keyboard_translation("dig-forward") ),
                "@keyboard-translations.bomb": xml_encode( input_controller.fetch_keyboard_translation("bomb") ),
                "@keyboard-translations.suicide": xml_encode( input_controller.fetch_keyboard_translation("suicide") ),
                "@keyboard-translations.interact": xml_encode( input_controller.fetch_keyboard_translation("interact") ),
                "@keyboard-translations.minimap": xml_encode( input_controller.fetch_keyboard_translation("minimap") ),
                "@keyboard-translations.net-chat": xml_encode( input_controller.fetch_keyboard_translation("net-chat") ),       # Keyboard only!
                "@keyboard-translations.skill1": xml_encode( input_controller.fetch_keyboard_translation("skill1") ),
                "@keyboard-translations.skill2": xml_encode( input_controller.fetch_keyboard_translation("skill2") )
            })

        # Include gamepad translations?
        if ( self.widgets[-1].get_attribute("gamepad-translations") == "on" ):

            template.add_parameters({
                "@gamepad-translations.left": xml_encode( input_controller.fetch_gamepad_translation("left") ),
                "@gamepad-translations.right": xml_encode( input_controller.fetch_gamepad_translation("right") ),
                "@gamepad-translations.up": xml_encode( input_controller.fetch_gamepad_translation("up") ),
                "@gamepad-translations.down": xml_encode( input_controller.fetch_gamepad_translation("down") ),
                "@gamepad-translations.dig-left": xml_encode( input_controller.fetch_gamepad_translation("dig-left") ),
                "@gamepad-translations.dig-right": xml_encode( input_controller.fetch_gamepad_translation("dig-right") ),
                "@gamepad-translations.dig-forward": xml_encode( input_controller.fetch_gamepad_translation("dig-forward") ),
                "@gamepad-translations.bomb": xml_encode( input_controller.fetch_gamepad_translation("bomb") ),
                "@gamepad-translations.suicide": xml_encode( input_controller.fetch_gamepad_translation("suicide") ),
                "@gamepad-translations.interact": xml_encode( input_controller.fetch_gamepad_translation("interact") ),
                "@gamepad-translations.minimap": xml_encode( input_controller.fetch_gamepad_translation("minimap") ),
                "@gamepad-translations.skill1": xml_encode( input_controller.fetch_gamepad_translation("skill1") ),
                "@gamepad-translations.skill2": xml_encode( input_controller.fetch_gamepad_translation("skill2") ),
                "@gamepad-translations.escape": xml_encode( input_controller.fetch_gamepad_translation("escape") ),
                "@gamepad-translations.enter": xml_encode( input_controller.fetch_gamepad_translation("enter") ),
                "@gamepad-translations.menu-left": xml_encode( input_controller.fetch_gamepad_translation("menu-left") ),
                "@gamepad-translations.menu-right": xml_encode( input_controller.fetch_gamepad_translation("menu-right") ),
                "@gamepad-translations.menu-up": xml_encode( input_controller.fetch_gamepad_translation("menu-up") ),
                "@gamepad-translations.menu-down": xml_encode( input_controller.fetch_gamepad_translation("menu-down") )
            })


        # Compile template
        root = template.compile_node_by_id("menu")


        # After building the template, we might need to remove the "continue game" option,
        # which I expect will only appear on the single player / new screen.
        if ( self.widgets[-1].get_attribute("continue-game-check") == "on" ):

            # Calculate path to "last played" data
            path = os.path.join(CONFIG_PATH, "lastplayed.xml")


            # If that path does not exist, then we must remove the "continue game" option (along with its subtitle)
            if ( not os.path.exists(path) ):

                # Remove main option
                root.remove_node_by_id("continue-game")

                # Remove subtitle
                root.remove_node_by_id("continue-game:subtitle")

            # If that path does exist, then we should load the last autosave for the last-played universe.
            # We'll have to update the markup and (redundantly, to an extent) recreate the root xml node.
            else:

                # Create a node based on the last played data
                ref_last_played = XMLParser().create_node_from_file(path)

                # Validate
                if (ref_last_played):

                    # Get universe name and last save committed
                    (ref_universe_name, ref_save_path) = (
                        ref_last_played.find_node_by_tag("universe"),
                        ref_last_played.find_node_by_tag("save")
                    )

                    # Validate both
                    if ( (ref_universe_name != None) and (ref_save_path != None) ):

                        # Create a temporary universe object for the last-played universe.
                        # Note that we're only loading in the minimal amount of data.
                        u = Universe(ref_universe_name.innerText, MODE_GAME, control_center, meta_only = True)

                        # Load in the last-used save path's data using the temporary Universe object.
                        # Note that we load in "data only" mode, as we only want statistical data, not an actual renderable universe...
                        control_center.get_save_controller().load_from_folder(
                            ref_save_path.innerText,
                            control_center,
                            u,
                            data_only = True
                        )


                        # Update the markup with up-to-date statistics
                        template.add_parameters({
                            "@universe-title": xml_encode( "%s" % u.get_title() ),
                            "@player-name": xml_encode( "%s" % u.get_session_variable("core.player1.name").get_value() ),
                            "@character-level": xml_encode( "%s" % u.get_session_variable("core.player1.level").get_value() )
                        })

                        # Recreate the root node using the revised markup
                        root = template.compile_node_by_id("menu")
                        #print template.template
                        #print template.user_parameters
                        #print root.compile_xml_string()
                        #print 5/0


        # Create the widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id(target) # re-use, it's easier this way

        # Set custom indentation for an arc effect
        widget.configure({
            "custom-indentation-callback": lambda y, radius = 200, offset = -50: offset + (-1 * int( math.sqrt( (radius * radius) - ((int(SCREEN_HEIGHT / 2) - y) * (int(SCREEN_HEIGHT / 2) - y)) ) )) if ( abs(int(SCREEN_HEIGHT / 2) - y) <= radius ) else 0
        })

        # I prefer to slow down the default fade speeds a little bit for the main menu pages
        widget.configure_alpha_controller({
            "speed-in": 0.025,
            "speed-out": 0.045
        })

        # I also heavily customize the vertical slide controller, even using an accelerator
        widget.vslide_controller.configure({
            "interval": SCREEN_HEIGHT,
            "target": 0,
            "speed-in": 6.25,
            "speed-out": 8.75,
            "accelerator": lambda speed, dy, step = 35, multiplier_per_step = 1.0 + (.00625 / 2): ( ( int(dy / step) * multiplier_per_step ) * speed ) if (dy >= step) else speed
        })

        # Add new page
        self.add_widget_via_event(widget, event)

        # Return events
        return results


    # Edit audio settings via a popup dialog.
    def handle_show_audio_settings_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Fetch the "edit keyboard key" template
        template = self.fetch_xml_template("mainmenu.root.options.sound").add_parameters({
            "@x": xml_encode( "%d" % int(SCREEN_WIDTH / 2) ),
            "@y": xml_encode( "%d" % int(SCREEN_HEIGHT / 2) ),
            "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT )
        })

        # Compile template
        root = template.compile_node_by_id("prompt")

        # Convert to widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("edit-audio-settings")


        # Find the background music volume rect
        volume_rect = widget.find_widget_by_id("background-music-volume")

        # Validate
        if (volume_rect):

            # Set current background music volume
            volume_rect.configure({
                "volume": control_center.get_sound_controller().get_background_volume()
            })


        # Find the sfx volume rect
        volume_rect = widget.find_widget_by_id("sound-effects-volume")

        # Validate
        if (volume_rect):

            # Set current sfx volume
            volume_rect.configure({
                "volume": control_center.get_sound_controller().get_sfx_volume()
            })


        # Add the new page
        self.add_widget_via_event(widget, event, exclusive = False)

        # Return events
        return results


    # Update the active audio setting, decreasing the active selection (if/a)
    def handle_update_audio_settings_decrease_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()


        # Get the active page (audio settings dialog)
        page = self.get_active_page()


        # Get the active widget from the row menu on the active page
        widget = page.get_active_widget()


        # Background music?
        if ( widget.get_rel() == "background-music" ):

            # Find the volume rect widget
            volume_rect = widget.find_widget_by_id("background-music-volume")

            # Validate
            if (volume_rect):

                # Decrease background music volume
                volume_rect.configure({
                    "volume": volume_rect.get_volume() - 0.1 # Sanity prevents negatives
                })

                # Update background music volume
                control_center.get_sound_controller().set_background_volume(
                    volume_rect.get_volume()
                )

        # Sound effects?
        elif ( widget.get_rel() == "sound-effects" ):

            # Find the volume rect widget
            volume_rect = widget.find_widget_by_id("sound-effects-volume")

            # Validate
            if (volume_rect):

                # Decrease sound effects volume
                volume_rect.configure({
                    "volume": volume_rect.get_volume() - 0.1 # Sanity prevents negatives
                })

                # Update sfx volume
                control_center.get_sound_controller().set_sfx_volume(
                    volume_rect.get_volume()
                )


        # Save changes immediately
        control_center.save_preferences()


        # Return events
        return results


    # Update the active audio setting, increasing the active selection (if/a)
    def handle_update_audio_settings_increase_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()


        # Get the active page (audio settings dialog)
        page = self.get_active_page()


        # Get the active widget from the row menu on the active page
        widget = page.get_active_widget()


        # Background music?
        if ( widget.get_rel() == "background-music" ):

            # Find the volume rect widget
            volume_rect = widget.find_widget_by_id("background-music-volume")

            # Validate
            if (volume_rect):

                # Increase background music volume
                volume_rect.configure({
                    "volume": volume_rect.get_volume() + 0.1 # Sanity prevents > 1.0
                })

                # Update background music volume
                control_center.get_sound_controller().set_background_volume(
                    volume_rect.get_volume()
                )

        # Sound effects?
        elif ( widget.get_rel() == "sound-effects" ):

            # Find the volume rect widget
            volume_rect = widget.find_widget_by_id("sound-effects-volume")

            # Validate
            if (volume_rect):

                # Decrease sound effects volume
                volume_rect.configure({
                    "volume": volume_rect.get_volume() + 0.1 # Sanity prevents > 1.0
                })

                # Update sfx volume
                control_center.get_sound_controller().set_sfx_volume(
                    volume_rect.get_volume()
                )


        # Save changes immediately
        control_center.save_preferences()


        # Return events
        return results


    # Edit display settings via a popup dialog.
    def handle_show_display_settings_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Fetch the "edit keyboard key" template
        template = self.fetch_xml_template("mainmenu.root.options.display").add_parameters({
            "@x": xml_encode( "%d" % int(SCREEN_WIDTH / 2) ),
            "@y": xml_encode( "%d" % int(SCREEN_HEIGHT / 2) ),
            "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT )
        })

        # Compile template
        root = template.compile_node_by_id("prompt")

        # Convert to widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("edit-display-settings")


        # Add the new page
        self.add_widget_via_event(widget, event, exclusive = False)

        # Return events
        return results


    # Update fullscreen mode preference
    def handle_fullscreen_set_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Activate fullscreen mode
        set_video_mode( SCREEN_WIDTH, SCREEN_HEIGHT, int( params["setting"] ) == 1 )


        # Unload gl assets
        logn( "gl", "Unloading gl assets...\n" )
        control_center.get_window_controller().unload_gl_assets()
        logn( "gl", "Unloading complete.\n" )


        """
        # Debug
        pygame.display.quit()
        render_init( SCREEN_WIDTH, SCREEN_HEIGHT, fullscreen = False )#int( params["setting"] ) == 1 )
        """




        # Reload gl assets
        control_center.get_window_controller().load_gl_assets()

        # Set window as reloaded
        control_center.get_window_controller().set_reloaded(True)


        # Update control center preference
        control_center.fullscreen_preferred = ( int( params["setting"] ) == 1 )

        # Save preferences
        control_center.save_preferences()


        # Return events
        return results


    # Edit language settings via a popup dialog.
    def handle_show_language_settings_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Fetch the "edit keyboard key" template
        template = self.fetch_xml_template("mainmenu.root.options.language").add_parameters({
            "@x": xml_encode( "%d" % int(SCREEN_WIDTH / 2) ),
            "@y": xml_encode( "%d" % int(SCREEN_HEIGHT / 2) ),
            "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT )
        })

        # Compile template
        root = template.compile_node_by_id("prompt")


        # Generate path to language index file
        path = os.path.join("data", "localization", "languages.xml")

        # Validate
        if ( os.path.exists(path) ):

            # Parse language file
            result = XMLParser().create_node_from_file(path)

            # Validate
            if (result):

                # Fetch insert template (one for each language)
                template = self.fetch_xml_template("mainmenu.root.options.language.insert")

                # Loop languages
                for ref_language in result.find_node_by_tag("languages").get_nodes_by_tag("language"):

                    # Get title and filename
                    (name, title, filename, layout, font_size, font) = (
                        ref_language.find_node_by_tag("name").innerText,
                        ref_language.find_node_by_tag("title").innerText,
                        ref_language.find_node_by_tag("file").innerText,
                        ref_language.find_node_by_tag("layout").innerText,
                        ref_language.find_node_by_tag("font-size").innerText,
                        ref_language.find_node_by_tag("font").innerText
                    )

                    # Add params to constant template
                    template.add_parameters({
                        "@language-name": name,
                        "@language-title": title,
                        "@language-file": filename,
                        "@layout": layout,
                        "@font-size": font_size,
                        "@font-name": font
                    })

                    # Add compiled markup to root node
                    root.find_node_by_id("ext.languages").add_node(
                        template.compile_node_by_id("insert")
                    )


                # Convert root node to widget
                widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

                widget.set_id("edit-display-settings")


                # Add the new page
                self.add_widget_via_event(widget, event, exclusive = False)


        # Return events
        return results


    # Update language preference
    def handle_language_set_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Get localization controller
        localization_controller = control_center.get_localization_controller()


        # Clear previous translation data
        localization_controller.clear()

        # Validate given file path
        if ( os.path.exists( params["file"] ) ):

            # Set as preferred language
            localization_controller.set_language( params["language"] )

            # Load from file
            localization_controller.load( params["file"] )

            # Set associated layout for this language
            localization_controller.set_layout( params["layout"] )

            # Set font size
            control_center.get_window_controller().set_font_size( int( params["font-size"] ) )

            # Set appropriate font
            control_center.get_window_controller().set_font( params["font-name"] )

        # Default to English
        else:

            # Set English as preferred language
            localization_controller.set_language("en")

            # Reset all localization data
            localization_controller.clear()

            # Use default layout
            localization_controller.set_layout_to_default()

            # Default font
            control_center.get_window_controller().set_font_to_default()


        # Refresh UI to show new language
        self.refresh_pages(control_center, universe, curtailed_count = 1)

        # We need to rebuild the title bar
        self.fire_event("redecorate")


        # Save preferences
        control_center.save_preferences()


        # Return events
        return results


    # Edit a keyboard control.  Show the "press any key" prompt.
    def handle_show_edit_keyboard_control_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Fetch the "edit keyboard key" template
        template = self.fetch_xml_template("mainmenu.root.options.controls.keyboard.prompt").add_parameters({
            "@x": xml_encode( "%d" % int(SCREEN_WIDTH / 2) ),
            "@y": xml_encode( "%d" % int(SCREEN_HEIGHT / 2) ),
            "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
            "@key": xml_encode( "%s" % params["key"] ),
            "@todo": xml_encode( "%s" % params["todo"] )
        })

        # Compile template
        root = template.compile_node_by_id("prompt")

        # Convert to widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("edit-keyboard-control")


        # Add the new page
        self.add_widget_via_event(widget, event, exclusive = False)

        # Return events
        return results


    # Update a given keyboard control
    def handle_game_update_keyboard_control_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the input controller
        input_controller = control_center.get_input_controller()


        # Which input to update?
        key = params["key"]

        # New value
        keycode = int( params["keycode"] )


        # If the player hits ESC, then just do nothing... I don't allow the use of the ESC key.
        if (keycode == K_ESCAPE):

            # Hide keypress prompt
            self.fire_event("hide")

        # Any other key (I suppose?) is fine!
        else:

            # Here's a terrible hack.  I want to prevent the user
            # from using ENTER to show the net chat typing area.
            if ( (key == "net-chat") and (keycode == K_RETURN) ):

                # Find error label
                label = self.get_widget_by_id("edit-keyboard-control").find_widget_by_id("error")

                # Validate
                if (label):

                    # Show an error message
                    label.set_text("You cannot use the [color=special]ENTER[/color] key for this action.")


                # Disable the "hide" listener (prevent the hide event from firing)
                listener = self.get_widget_by_id("edit-keyboard-control").find_widget_by_id("keypress-listener")

                # Validate
                if (listener):

                    # Reset
                    listener.reset()

            # Otherwise, update normally
            else:

                # Update the given key definition
                input_controller.update_keyboard_setting(
                    key = key,
                    value = keycode
                )

                # Refresh UI
                self.refresh_pages(control_center, universe, curtailed_count = 1)

                # Hide keypress prompt
                self.fire_event("hide")

        # Return events
        return results


    # Show a submenu that lists all of the detected gamepad devices
    def handle_show_gamepads_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Transition to a new movie
        self.add_movie_widget_via_event(event, control_center, universe)


        # First we need to slide away the current page
        page = self.widgets[-1]

        # Mark the current page as "locked" as we begin to transition away from it
        page.set_attribute( "-locked", "yes" )


        # Slide it away
        page.slide(
            DIR_DOWN,
            amount = SCREEN_HEIGHT,
            on_complete = "finish:show:gamepads"
        )

        # Don't quite fully hide this top page, so that the Menu doesn't take it away (it takes away fully-gone top pages)
        page.hide()

        # Return events
        return results


    # Finish show gamepad evnet logic, after sliding out the previos submenu...
    def handle_finish_show_gamepads_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the widget dispatcher;
        widget_dispatcher = control_center.get_widget_dispatcher()

        # and the input controller
        input_controller = control_center.get_input_controller()


        # Scope; will we create "list of devices" widget, or will we create "no device found" widget?
        widget = None


        # Let's query for any found device...
        device_names = input_controller.query_available_device_names()

        # If we found any, we'll use the "select a device" template
        if ( len(device_names) > 0 ):

            # Fetch template
            template = self.fetch_xml_template("mainmenu.root.options.controls.gamepads.select").add_parameters({
                "@x": xml_encode( "%d" % 400 ), # hard-coded
                "@y": xml_encode( "%d" % int(SCREEN_HEIGHT / 2) ),
                "@width": xml_encode( "%d" % SCREEN_WIDTH ),
                "@height": xml_encode( "%d" % 360 ), # hard-coded
                "@device-count": xml_encode( "%d" % len(device_names) )
            })

            # Compile template
            root = template.compile_node_by_id("menu")

            # Loop through each found device
            for i in range( 0, len(device_names) ):

                # Fetch insert template
                template = self.fetch_xml_template("mainmenu.root.options.controls.gamepads.select.device").add_parameters({
                    "@n": xml_encode( "%d" % i ), # Simple counter
                    "@device-title": xml_encode( device_names[i] )
                })

                # Compile insert template
                wrapper_node = template.compile_node_by_id("insert")

                # Add to options
                root.find_node_by_id("ext.devices").add_nodes(
                    wrapper_node.get_nodes_by_tag("*")
                )


            # Create widget
            widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

            widget.set_id("select-gamepad-device")


        # No device found!
        else:

            # Fetch template
            template = self.fetch_xml_template("mainmenu.root.options.controls.gamepads.select.nodevices").add_parameters({
                "@x": xml_encode( "%d" % 400 ), # hard-coded
                "@y": xml_encode( "%d" % int(SCREEN_HEIGHT / 2) ),
                "@width": xml_encode( "%d" % SCREEN_WIDTH ),
                "@height": xml_encode( "%d" % 360 ) # hard-coded
            })

            # Compile template
            root = XMLParser().create_node_from_xml(markup).find_node_by_id("menu")

            # Create widget
            widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

            widget.set_id("select-gamepad-device")


        # Set custom indentation for an arc effect
        widget.configure({
            "custom-indentation-callback": lambda y, radius = 200, offset = -50: offset + (-1 * int( math.sqrt( (radius * radius) - ((int(SCREEN_HEIGHT / 2) - y) * (int(SCREEN_HEIGHT / 2) - y)) ) )) if ( abs(int(SCREEN_HEIGHT / 2) - y) <= radius ) else 0
        })

        # I prefer to slow down the default fade speeds a little bit for the main menu pages
        widget.configure_alpha_controller({
            "speed-in": 0.025,
            "speed-out": 0.045
        })

        # I also heavily customize the vertical slide controller, even using an accelerator
        widget.vslide_controller.configure({
            "interval": SCREEN_HEIGHT,
            "target": 0,
            "speed-in": 6.25,
            "speed-out": 8.75,
            "accelerator": lambda speed, dy, step = 35, multiplier_per_step = 1.0 + (.00625 / 2): ( ( int(dy / step) * multiplier_per_step ) * speed ) if (dy >= step) else speed
        })

        # Add new page
        self.add_widget_via_event(widget, event)

        # Return events
        return results


    # Select a given gamepad by name
    def handle_game_select_gamepad_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the input controller
        input_controller = control_center.get_input_controller()


        # What is the name of the device?
        device_name = params["device-title"]

        # Attempt to select the given device by its name
        if ( input_controller.select_device_by_name(device_name) ):

            # Post a newsfeeder item
            control_center.get_window_controller().get_newsfeeder().post({
                "type": NEWS_GAME_GAMEPAD_SELECTED,
                "title": control_center.get_localization_controller().get_label("gamepad-selected:header"),
                "content": "%s" % device_name
            })


        # Return events
        return results


    # Edit a gamepad control.  Show the "press a button on the gamepad" prompt.
    def handle_show_edit_gamepad_control_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Fetch the "edit keyboard key" template
        template = self.fetch_xml_template("mainmenu.root.options.controls.gamepad.prompt").add_parameters({
            "@x": xml_encode( "%d" % int(SCREEN_WIDTH / 2) ),
            "@y": xml_encode( "%d" % int(SCREEN_HEIGHT / 2) ),
            "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
            "@key": xml_encode( "%s" % params["key"] ),
            "@todo": xml_encode( "%s" % params["todo"] )
        })

        # Compile template
        root = template.compile_node_by_id("prompt")

        # Convert to widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("edit-gamepad-control")


        # Add the new page
        self.add_widget_via_event(widget, event, exclusive = False)

        # Return events
        return results


    # Update a given gamepad control.
    def handle_game_update_gamepad_control_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the input controller
        input_controller = control_center.get_input_controller()


        # Which key (action) are we editing?
        key = params["key"]

        # Fetch the gamepad input event
        event = params["gamepad-event"]


        # Update the given action using that event
        input_controller.update_gamepad_setting(key, event)


        # Refresh UI
        self.refresh_pages(control_center, universe, curtailed_count = 1)

        # Return events
        return results


    # ESC will abort the "edit gamepad control" prompt
    def handle_abort_edit_gamepad_control_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Which key got pressed?
        keycode = int( params["keycode"] )

        # Is it the ESC key?
        if (keycode == K_ESCAPE):

            # Let's fire a "back" event to page back...
            self.fire_event("hide")

            log2("hide me")

        # Return events
        return results


    # Show the "are you sure?" dialog for resetting gamepad controls
    def handle_show_reset_gamepad_controls_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Fetch the "are you sure?" template
        template = self.fetch_xml_template("mainmenu.root.options.controls.gamepad.default").add_parameters({
            "@x": xml_encode( "%d" % int(SCREEN_WIDTH / 2) ),
            "@y": xml_encode( "%d" % int(SCREEN_HEIGHT / 2) ),
            "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
            "@device-name": xml_encode( "%s" % control_center.get_input_controller().get_active_device_name() )
        })

        # Compile template
        root = template.compile_node_by_id("prompt")

        # Convert to widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("reset-gamepad-controls")


        # Position the confirmation page to slide in from the bottom
        widget.slide(DIR_DOWN, amount = 200, animated = False)

        # Slide to default location
        widget.slide(None)


        # Add the new page
        self.add_widget_via_event(widget, event, exclusive = False)

        # Return events
        return results


    # Reset all gamepad controls for the current gamepad device
    def handle_game_reset_gamepad_controls_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Reset the active device's controls
        control_center.get_input_controller().reset_active_gamepad_controls()


        # Add a newsfeeder item
        control_center.get_window_controller().get_newsfeeder().post({
            "type": NEWS_GAME_GAMEPAD_RESET,
            "title": control_center.get_localization_controller().get_label("gamepad-reset:title"),
            "content": control_center.get_input_controller().get_active_device_name()
        })


        # Refresh UI
        self.refresh_pages(control_center, universe, curtailed_count = 1)


        # Return events
        return results


    # Show the "are you sure?" dialog for resetting keyboard controls
    def handle_show_reset_keyboard_controls_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Fetch the "are you sure?" template
        template = self.fetch_xml_template("mainmenu.root.options.controls.keyboard.default").add_parameters({
            "@x": xml_encode( "%d" % int(SCREEN_WIDTH / 2) ),
            "@y": xml_encode( "%d" % int(SCREEN_HEIGHT / 2) ),
            "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT )
        })

        # Compile template
        root = template.compile_node_by_id("prompt")

        # Convert to widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("reset-keyboard-controls")


        # Position the confirmation page to slide in from the bottom
        widget.slide(DIR_DOWN, amount = 200, animated = False)

        # Slide to default location
        widget.slide(None)


        # Add the new page
        self.add_widget_via_event(widget, event, exclusive = False)

        # Return events
        return results


    # Reset all keys to default for the keyboard device
    def handle_game_reset_keyboard_controls_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Reset the keyboard controls
        control_center.get_input_controller().reset_keyboard_controls()


        # Add a newsfeeder item
        control_center.get_window_controller().get_newsfeeder().post({
            "type": NEWS_GAME_KEYBOARD_RESET,
            "title": control_center.get_localization_controller().get_label("keyboard-reset:title"),
            "content": control_center.get_localization_controller().get_label("keyboard-reset:message")
        })


        # Refresh UI
        self.refresh_pages(control_center, universe, curtailed_count = 1)


        # Return events
        return results


    # Save control preferences (this saves both keyboard and gamepad, kind of redundant in that regard)
    def handle_game_save_controls_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Save the controls
        control_center.get_input_controller().save()

        # Post a newsfeeder item confirming the save
        control_center.get_window_controller().get_newsfeeder().post({
            "type": NEWS_GAME_CONTROLS_SAVED,
            "title": control_center.get_localization_controller().get_label("controls-saved:title"),
            "content": params["message"]
        })


        # Return events
        return results


    # Hide event (no transition except simple fade)
    def handle_hide_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch current page
        page = self.get_active_page()

        # Also mark the current page as "locked" as we begin to transition away from it
        page.set_attribute( "-locked", "yes" )


        # Validate
        if (page):

            # Hide
            page.hide(
                on_complete = "finish:back" # Borrow event, we're just paging back anyway
            )

        # Return events
        return results


    # Move back one submenu.  Revert to the last movie wiwdget.
    def handle_back_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Start hiding the active movie widget
        self.get_active_movie_widget().hide()

        # Lock the camera on the movie widget we're getting rid of
        self.get_active_movie_widget().universe.get_camera().lock()


        # Get the now-active movie widget
        movie_widget = self.movie_widgets[-2]

        # Validate
        if (movie_widget):

            # Show it
            movie_widget.show()


        # Fetch current page
        page = self.widgets[-1]

        # Also mark the current page as "locked" as we begin to transition away from it
        page.set_attribute( "-locked", "yes" )


        # Slide it away
        page.slide(
            DIR_DOWN,
            amount = SCREEN_HEIGHT,
            on_complete = "finish:back"
        )

        # Fully hide the thing, trash it
        page.hide(target = 0.01)

        # Return events
        return results


    # Finish back event logic, after active submenu finishes its disappearing act.  Remove top movie widget from stack.
    def handle_finish_back_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Don't remove the top movie widget if we're just dismissing a transient prompt;
        # only do so for the submenu branches.
        if ( self.get_active_page().get_rel() != "prompt" ):

            # Remove the previously-active movie widget, reverting to the one we were on before
            self.remove_active_movie_widget()

            # Allow the camera on the now-active movie widget to move freely once again
            self.get_active_movie_widget().universe.get_camera().unlock()


        # Page back
        self.page_back(1)

        page = self.widgets[-1]

        # Mark the current page as no longer locked
        page.set_attribute( "-locked", "no" )

        page.show()

        #page.set_cursor(page.cursor + 2)
        #page.set_cursor(page.cursor - 2)

        page.blur()
        page.focus()

        page.slide(
            DIR_UP,
            amount = 0
        )

        # Return events
        return results


    # App directive.  Begin fading out.
    def handle_app_directive_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch window controller
        window_controller = control_center.get_window_controller()


        # Let's store the specific directive in our flags; we'll need it in the next event (the "finish" call)
        self.flags["app-directive"] = params["directive"]


        # Assume no refresh
        self.flags["refresh"] = False

        # Check for optional refresh param
        if ( "refresh" in params ):

            # Update flag
            self.flags["refresh"] = ( params["refresh"] == "1" )


        # Hook into the window controller
        window_controller.hook(self)

        # Trigger an app-level fade
        window_controller.fade_out(
            on_complete = "fwd:finish:app-directive"
        )

        # Return events
        return results


    # Finish app directive logic, post app-fade
    def handle_fwd_finish_app_directive_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch window controller
        window_controller = control_center.get_window_controller()


        # Unhook from the window controller
        window_controller.unhook(self)

        # Flag to send app directive back to app
        self.flags["send-app-directive"] = True


        # Fade back in as we go on to whatever the directive does (e.g. start new game, launch / join coop game, etc.)
        window_controller.fade_in()

        # Return events
        return results


    # Quit the game for now
    def handle_quit_game_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the window controller
        window_controller = control_center.get_window_controller()


        # Slide the entire menu away
        self.hslide_controller.configure({
            "target": -SCREEN_WIDTH
        })


        # Hook into the window controller
        window_controller.hook(self)

        # Call for an app-level fade as the menu slides away.
        # Note that we'll never fade back in from this call; we're quitting the game entirely.
        window_controller.fade_out(
            on_complete = "fwd:finish:quit-game"
        )

        # Return events
        return results


    # (Fwd) Finish quit game logic, post-fade
    def handle_fwd_finish_quit_game_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the window controller so that we can unhook from it
        window_controller = control_center.get_window_controller()


        # Unhook
        window_controller.unhook(self)

        # Flag a quit game app directive.
        # We won't be fading back in; we'll be ending the application.
        self.flags["quit-game"] = True

        # Return events
        return results
