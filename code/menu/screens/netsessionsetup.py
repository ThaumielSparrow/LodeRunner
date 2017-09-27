import os

import math
import random

import time

from code.menu.menu import Menu

from code.tools.eventqueue import EventQueue

from code.tools.xml import XMLParser

from code.utils.common import coalesce, intersect, offset_rect, log, log2, xml_encode, xml_decode, translate_rgb_to_string

from code.constants.common import SCREEN_WIDTH, SCREEN_HEIGHT, PAUSE_MENU_X, PAUSE_MENU_Y, PAUSE_MENU_WIDTH, PAUSE_MENU_HEIGHT, MODE_GAME, TILE_WIDTH, TILE_HEIGHT, DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT, SPLASH_MODE_GREYSCALE_ANIMATED

from code.constants.states import STATUS_ACTIVE, STATUS_INACTIVE, GAME_STATE_ACTIVE, GAME_STATE_NOT_READY
from code.constants.newsfeeder import *


class NetSessionSetup(Menu):

    def __init__(self):#, x, y, w, h, universe, session, widget_dispatcher):

        Menu.__init__(self)#, x, y, w, h, universe, session)


        # Fire a build event
        self.fire_event("build")


    # Configure the net session browser; we have to feed it the raw session data it'll use to populate the session view
    def configure(self, options):

        # Common menu configuration
        self.__std_configure__(options)


        if ( "http-data" in options ):
            self.http_data = options["http-data"]


        # For chaining
        return self


    def handle_event(self, event, control_center, universe):#params, user_input, network_controller, universe, active_map, session, widget_dispatcher, text_renderer, save_controller, refresh = False):

        # Events that result from event handling
        results = EventQueue()

        results.inject_event(event)


        # Convenience
        (action, params) = (
            event.get_action(),
            event.get_params()
        )


        # Build root menu
        if (action == "build"):

            results.append(
                self.handle_build_event(event, control_center, universe)
            )


        elif ( action == "show:keyboard.password" ):

            results.append(
                self.handle_show_keyboard_password_event(event, control_center, universe)
            )


        elif ( action == "hide:keyboard.password" ):

            results.append(
                self.handle_hide_keyboard_password_event(event, control_center, universe)
            )


        elif ( action == "submit:keyboard.password" ):

            results.append(
                self.handle_submit_keyboard_password_event(event, control_center, universe)
            )


        elif ( action == "show:maxplayers" ):

            results.append(
                self.handle_show_maxplayers_event(event, control_center, universe)
            )


        elif ( action == "submit:maxplayers" ):

            results.append(
                self.handle_submit_maxplayers_event(event, control_center, universe)
            )


        elif ( action == "begin-game" ):

            results.append(
                self.handle_begin_game_event(event, control_center, universe)
            )


        elif ( action == "back" ):

            results.append(
                self.handle_back_event(self, control_center, universe)
            )


        elif ( action == "page-back" ):

            results.append(
                self.handle_page_back_event(event, control_center, universe)
            )


        # Resume puzzle
        elif (action == "return-to-lobby"):

            results.append(
                self.handle_return_to_lobby_event(event, control_center, universe)
            )

        # Retry puzzle - commit
        elif (action == "fwd.finish:return-to-lobby"):

            results.append(
                self.handle_fwd_finish_return_to_lobby_event(event, control_center, universe)
            )


        elif ( action == "leave-game" ):

            results.append(
                self.handle_leave_game_event(event, control_center, universe)
            )


        elif ( action == "fwd:finish:leave-game" ):

            results.append(
                self.handle_fwd_finish_leave_game_event(event, control_center, universe)
            )


        # Discard this menu
        elif ( action == "kill" ):

            results.append(
                self.handle_kill_event(event, control_center, universe)
            )


        # Return events
        return results


    # Build the puzzle pause menu
    def handle_build_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the template we need (i.e. normal or "no games found" version).
        template = self.fetch_xml_template("mainmenu.root.coop.setup").add_parameters({
            "@x": xml_encode( "%d" % PAUSE_MENU_X ),
            "@y": xml_encode( "%d" % PAUSE_MENU_Y ),
            "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT ),
            "@max-players": xml_encode( "%d" % universe.get_max_players() )
        })

        # Compile template
        root = template.compile_node_by_id("menu")


        # Create widget
        widget = control_center.get_widget_dispatcher().convert_node_to_widget(root, control_center, universe = None) # (?) no universe needed?

        widget.set_id("coop-session-setup")


        # Add the page
        self.add_widget_via_event(widget, event)


        # Return events
        return results


    # Show a keyboard the player can use to set a password for the co-op session
    def handle_show_keyboard_password_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch keyboard template
        template = self.fetch_xml_template("mainmenu.root.coop.setup.keyboard").add_parameters({
            "@x": xml_encode( "%d" % int(SCREEN_WIDTH / 2) ),
            "@y": xml_encode( "%d" % (SCREEN_HEIGHT - PAUSE_MENU_Y) ),
            "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
            "@default": xml_encode( "%s" % "default" )
        })

        # Compile template
        root = template.compile_node_by_id("keyboard")

        # Convert to widget
        widget = control_center.get_widget_dispatcher().convert_node_to_widget(root, control_center, universe)

        widget.set_id("session-password-keyboard")

        # Add the new page to this menu
        self.add_widget_via_event(widget, event, exclusive = False)


        # Return events
        return results


    # HIde the keyboard dedicated to setting a session password
    def handle_hide_keyboard_password_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Get the active page (the keyboard) and hide it...
        self.get_active_page().hide(
            on_complete = "page-back"
        )


        # Return events
        return results


    # Handle submission of the session password keyboard.  Validate the password, either accepting it and dismissing the keyboard
    # or rejecting it and giving the user and error.
    def handle_submit_keyboard_password_event(self, event, control_center, universe):

        # Get the given password
        password = self.get_active_page().get_value().strip()

        # Validate password
        if (True):

            # We already created the universe object when we selected the universe.  Let's just set the password as specified...
            universe.set_session_variable("net.password", password)

            # If the user didn't provide a password, list "n/a" in the password label area
            if ( len(password) == 0 ):

                # No password set, but list "n/a" in the readable area
                self.get_widget_by_id("coop-session-setup").find_widget_by_id("label-password").set_text("n/a")

            # Otherwise, show them the password they chose
            else:            

                # Update the visible label on the first page
                self.get_widget_by_id("coop-session-setup").find_widget_by_id("label-password").set_text(password)


            # Hide the keyboard, raising a page-back event when done
            self.get_active_page().hide(
                on_complete = "page-back"
            )

        else:
            pass


        # No event to return
        return EventQueue()


    # Show a dialog menu that lets the player specify a "max players" limit for the co-op session
    def handle_show_maxplayers_event(self, event, control_center, universe):

        # Fetch keyboard template
        template = self.fetch_xml_template("mainmenu.root.coop.setup.maxplayers").add_parameters({
            "@x": xml_encode( "%d" % int(SCREEN_WIDTH / 2) ),
            "@y": xml_encode( "%d" % int(SCREEN_HEIGHT / 2) ),
            "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT )
        })

        # Compile template
        root = template.compile_node_by_id("menu")

        # Each universe has a custom-defined overall player limit.  One might support 2 players, another 3, and yet another 4.
        # Allow the user to select the range of 2 ... (universe limit)
        for limit in range(2, max( 3, universe.get_max_players() + 1) ): # Guarantee at least 2 player slots using range(2, max(3, n)) as a minimum

            # Fetch limit insert template
            template = self.fetch_xml_template("mainmenu.root.coop.setup.maxplayers.insert").add_parameters({
                "@limit": xml_encode( "%d" % limit )
            })

            # Insert compiled template
            root.find_node_by_id("ext.limits").add_node(
                template.compile_node_by_id("insert")
            )


        # Convert to widget
        widget = control_center.get_widget_dispatcher().convert_node_to_widget(root, control_center, universe)

        widget.set_id("session-maxplayers")

        # Add the new page to this menu
        self.add_widget_via_event(widget, event, exclusive = False)

        # No event worth returning
        return EventQueue()


    # Update the max players setting for the game
    def handle_submit_maxplayers_event(self, event, control_center, universe):

        # We already created the universe object when we selected the universe.  Let's just set the flag to the value indicated...
        universe.set_session_variable( "net.player-limit", event.get_params()["limit"] )

        # Update the visible label on the first page
        self.get_widget_by_id("coop-session-setup").find_widget_by_id("label-maxplayers").set_text("%s Players" % event.get_params()["limit"])


        # No event to return
        return EventQueue()


    # Start the new co-op game session
    def handle_begin_game_event(self, event, control_center, universe):

        # Run an app fade.  Raise a "redirect success" app event on complete
        # to signal that we want to begin the game.
        control_center.get_window_controller().fade_out(
            on_complete = "app:redirect.success"
        )

        # No event to return
        return EventQueue()


    # HIde the current page, firing a page-back event when it's gone...
    def handle_back_event(self, event, control_center, universe):

        # Hide active page
        self.get_active_page().hide(
            on_complete = "page-back" # Page back once it's gone
        )

        # No event worth returning
        return EventQueue()


    # Page back by one page
    def handle_page_back_event(self, event, control_center, universe):

        # Page back by 1 page
        self.page_back(1)

        # Return no event
        return EventQueue()


    # Resume the co-op session
    def handle_return_to_lobby_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the window controller
        window_controller = control_center.get_window_controller()

        # Hook into it to receive forwarded events
        window_controller.hook(self)


        # App fade, after which we'll restart level
        window_controller.fade_out(
            on_complete = "fwd.finish:return-to-lobby"
        )

        # Return events
        return results


    # (Forwarded) Restart the level, "returning" to the pregame lobby
    def handle_fwd_finish_return_to_lobby_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the window controller
        window_controller = control_center.get_window_controller()

        # Unhook; we don't need any more forwarded events
        window_controller.unhook(self)


        # (?) Hack in the current map's name as our transition destination
        universe.set_session_variable("net.transition.target", universe.get_active_map().name)

        # (?) Let's just fake this for now.  Hack.
        universe.handle_fwd_net_transition_finalize_event(event, control_center, universe)


        # Return events
        return results


    # Leave the co-op session
    def handle_leave_game_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Let's just fade the app out, raising a "leave game" event when it's gone
        control_center.get_window_controller().fade_out(
            on_complete = "fwd.return-to-menu.commit"
        )


        # Handle
        page1 = self.get_widget_by_id("net-no-players")

        # Slide and hide, killing menu when gone
        page1.slide(DIR_DOWN, amount = SCREEN_HEIGHT)
        page1.hide(
            on_complete = "kill"
        )


        # Return events
        return results


    # Retry the puzzle
    def handle_retry_puzzle_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Handle
        page1 = self.get_widget_by_id("puzzle-pause")

        # Slide and hide
        page1.slide(DIR_RIGHT, percent = 1.0)
        page1.hide()


        # Fetch the window controller
        window_controller = control_center.get_window_controller()

        # Hook
        window_controller.hook(self)


        # App fade as we choose to retry
        window_controller.fade_out(
            on_complete = "fwd.finish:retry-puzzle"
        )

        # Return events
        return results


    # (Fwd) Cleanup retry puzzle; reload map, etc.
    def handle_fwd_finish_retry_puzzle_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Resume gameplay as we begin to retry the puzzle.  When we transition to the
        # (same) map, we'll get a puzzle intro menu that will re-pause the game.
        universe.unpause()


        # "Transition" to the same exact map.  Don't save any memory (we're on a puzzle map), and don't remember where we were (retain the next-most-recent memory of the overworld map we came from)
        universe.transition_to_map(
            name = universe.get_active_map().name, # "Transition" to the map we're already on, prompting a reload and fresh UI
            waypoint_to = universe.get_session_variable("app.transition.to.waypoint").get_value(), # Retain to the last waypoint we spawned on (probably "spawn")
            save_memory = False,
            can_undo = False,
            control_center = control_center
        )


        # Fetch the window controller
        window_controller = control_center.get_window_controller()

        # Unhook
        window_controller.unhook(self)


        # App fade back in as we return to the same puzzle for another try
        window_controller.fade_in()


        # Dismiss the current menu
        self.set_status(STATUS_INACTIVE)

        # Disengage the menu controller's pause lock
        control_center.get_menu_controller().configure({
            "pause-locked": False
        })


        # Return events
        return results


    # Leave a puzzle (give up!)
    def handle_leave_puzzle_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Handle
        page1 = self.get_widget_by_id("puzzle-pause")

        # Slide and hide
        page1.slide(DIR_RIGHT, percent = 1.0)
        page1.hide()


        # Fetch window controller
        window_controller = control_center.get_window_controller()

        # Hook into the window controller so that we get forwarded events
        window_controller.hook(self)


        # App-level fade, followed by a (forwarded) event...
        window_controller.fade_out(
            on_complete = "fwd.finish:leave-puzzle" # The universe itself won't care about this event (?)
        )

        # Return events
        return results


    # (Fwd) Finish leave puzzle logic, post-fade
    def handle_fwd_finish_leave_puzzle_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Undo the last map transition.  Don't save memory:  this is a self-contained puzzle map
        universe.undo_last_map_transition(control_center = control_center, save_memory = False)

        # Resume gameplay back in the overworld
        universe.unpause()


        # Fetch window controller
        window_controller = control_center.get_window_controller()

        # Unhook from the window controller; we don't care about its events anymore
        window_controller.unhook(self)


        # App-level fade back in as we return to the overworld
        window_controller.fade_in()


        # Fire a kill event
        self.fire_event("kill")


        # Return events
        return results


    # Kill event
    def handle_kill_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Done with the puzzle pause menu widget; trash it.
        self.set_status(STATUS_INACTIVE)

        # Disengage the menu controller's pause lock
        control_center.get_menu_controller().configure({
            "pause-locked": False
        })

        # Return events
        return results
