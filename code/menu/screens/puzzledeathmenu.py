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


# Puzzle death menu is almost exactly like the puzzle pause menu.
# The code works very similarly.
class PuzzleDeathMenu(Menu):

    def __init__(self):

        Menu.__init__(self)


        # Fire build event
        self.fire_event("build")


    def handle_event(self, event, control_center, universe):#params, user_input, network_controller, universe, active_map, session, widget_dispatcher, text_renderer, save_controller, refresh = False):

        # Events that result from event handling
        results = EventQueue()

        # Convenience
        action = event.get_action()


        # Build root menu
        if (action == "build"):

            results.append(
                self.handle_build_event(event, control_center, universe)
            )


        # Retry puzzle
        elif (action == "retry-puzzle"):

            results.append(
                self.handle_retry_puzzle_event(event, control_center, universe)
            )


        # Retry puzzle - commit
        elif (action == "fwd.finish:retry-puzzle"):

            results.append(
                self.handle_fwd_finish_retry_puzzle_event(event, control_center, universe)
            )


        # Abandon puzzle
        elif ( action == "leave-puzzle" ):

            results.append(
                self.handle_leave_puzzle_event(event, control_center, universe)
            )


        # Receive forwarded event, commit leave puzzle
        elif ( action == "fwd.finish:leave-puzzle" ):

            results.append(
                self.handle_fwd_finish_leave_puzzle_event(event, control_center, universe)
            )


        # Discard this menu
        elif ( action == "kill" ):

            results.append(
                self.handle_kill_event(event, control_center, universe)
            )


        # Return events
        return results


    # Build the puzzle death menu
    def handle_build_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Pause lock the menu controller; can't pause until you've made a choice!
        control_center.get_menu_controller().configure({
            "pause-locked": True
        })

        # Summon the pause splash
        control_center.get_splash_controller().set_mode(SPLASH_MODE_GREYSCALE_ANIMATED)


        # Fetch the template for a puzzle pause menu
        template = self.fetch_xml_template("puzzle.menu.death").add_parameters({
            "@x": xml_encode( "%d" % (SCREEN_WIDTH - (int( (SCREEN_WIDTH - PAUSE_MENU_WIDTH) / 2 ))) ),
            "@y": xml_encode( "%d" % int(SCREEN_HEIGHT / 2) ),
            "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
            "@overworld-title": xml_encode( universe.get_session_variable("core.overworld-title").get_value() )
        })

        # Compile template
        root = template.compile_node_by_id("menu")

        # Build widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("puzzle-death")


        # Position page 1 to slide in from the right
        widget.slide(DIR_RIGHT, percent = 1.0, animated = False)

        # Now have it slide into its default position
        widget.slide(None)


        # Add new page
        results.append(
            self.add_widget_via_event(widget, event)
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
        page1 = self.get_widget_by_id("puzzle-death")

        # Slide and hide
        page1.slide(DIR_RIGHT, percent = 1.0)
        page1.hide()


        # Fetch window controller
        window_controller = control_center.get_window_controller()


        # Hook into the window controller
        window_controller.hook(self)

        # Fade the app, raising a (forwarded) event when done
        window_controller.fade_out(
            on_complete = "fwd.finish:retry-puzzle"
        )

        # Return events
        return results


    # (Fwd) Finish retry puzzle logic
    def handle_fwd_finish_retry_puzzle_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # "Transition" to the same exact map.  Don't save any memory (we're on a puzzle map), and don't remember where we were (retain the next-most-recent memory of the overworld map we came from)
        universe.transition_to_map(
            name = universe.get_active_map().name, # "Transition" to the map we're already on, prompting a reload and fresh UI
            waypoint_to = universe.get_session_variable("app.transition.to.waypoint").get_value(), # Retain the waypoint we previously spawned on
            save_memory = False,
            can_undo = False,
            control_center = control_center
        )


        # Fetch window controller
        window_controller = control_center.get_window_controller()

        # Unhook from the window controller
        window_controller.unhook(self)


        # App fade in as we retry the puzzle
        window_controller.fade_in()


        # Dismiss the current menu
        self.set_status(STATUS_INACTIVE)


        # Return events
        return results


    # Leave the puzzle, it's too hard :)
    def handle_leave_puzzle_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Handle
        page1 = self.get_widget_by_id("puzzle-death")

        # Slide and hide
        page1.slide(DIR_RIGHT, percent = 1.0)
        page1.hide()


        # Fetch window controller
        window_controller = control_center.get_window_controller()

        # Hook into the window controller so that we get forwarded events
        window_controller.hook(self)


        # App-level fade, followed by a (forwarded) event...
        window_controller.fade_out(
            on_complete = "fwd.finish:leave-puzzle" # The universe itself won't care about this event
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


        # Unlock pause lock on menu controller as we return to the overworld
        control_center.get_menu_controller().configure({
            "pause-locked": False
        })

        # Abort the pause splash
        control_center.get_splash_controller().abort()


        # Fetch window controller
        window_controller = control_center.get_window_controller()

        # Unhook from the window controller; we don't care about its events anymore
        window_controller.unhook(self)


        # App fade in as we go back to the overworld
        window_controller.fade_in()

        # Resume gameplay now.  (?) (I don't think I ever pause it for the puzzle death menu, since the player can't do anything while dead anyway...)
        universe.unpause()


        # Trash this menu
        self.fire_event("kill")


        # Return events
        return results


    # Kill event
    def handle_kill_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Done with the pause menu widget
        self.set_status(STATUS_INACTIVE)

        # Return events
        return results
