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


class NetNoPlayersMenu(Menu):

    def __init__(self):#, x, y, w, h, universe, session, widget_dispatcher):

        Menu.__init__(self)#, x, y, w, h, universe, session)


        # Fire a build event
        self.fire_event("build")


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


        # Fetch widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Pause lock the menu controller.  Can't be pausing the game while the game is paused...
        control_center.get_menu_controller().configure({
            "pause-locked": True
        })


        # Fetch the template for a puzzle pause menu
        template = self.fetch_xml_template("net.menu.noplayers").add_parameters({
            "@old-x": xml_encode( "%d" % int(SCREEN_WIDTH / 2) ),
            "@x": xml_encode( "%d" % int(SCREEN_WIDTH / 2) ),
            "@y": xml_encode( "%d" % int(SCREEN_HEIGHT / 2) ),
            "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
            "@overworld-title": xml_encode( universe.get_session_variable("core.overworld-title").get_value() )
        })

        # Compile template
        root = template.compile_node_by_id("menu")

        # Build widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("net-no-players")


        # Position page 1 to slide in from the bottom
        widget.slide(DIR_DOWN, amount = 200, animated = False)

        # Now have it slide into its default position
        widget.slide(None)


        # Add new page
        results.append(
            self.add_widget_via_event(widget, event)
        )

        # Return events
        return results


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


        # Fetch window controller
        window_controller = control_center.get_window_controller()


        # Hook into the window controller to receive forwarded event
        window_controller.hook(self)

        # Let's just fade the app out, raising a "leave game" event when it's gone
        window_controller.fade_out(
            on_complete = "fwd:finish:leave-game"
        )


        # Handle
        page1 = self.get_widget_by_id("net-no-players")

        # Slide and hide, killing menu when gone
        page1.slide(DIR_DOWN, amount = SCREEN_HEIGHT)
        page1.hide()


        # Return events
        return results


    # Receive forwarded event from the window controller, indicating that the app-level fade has completed
    # and we should commit the "leave game" event now.
    def handle_fwd_finish_leave_game_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the window controller
        window_controller = control_center.get_window_controller()

        # Unhook from the window controller
        window_controller.unhook(self)


        # Queue an app-level event
        results.add(
            action = "app:leave-game"
        )


        # App-level fade back in to show the game again
        window_controller.fade_in()


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
