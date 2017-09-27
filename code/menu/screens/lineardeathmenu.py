import os

import math
import random

import time

from code.menu.menu import Menu

from code.tools.eventqueue import EventQueue

from code.tools.xml import XMLParser

from code.utils.common import coalesce, intersect, offset_rect, log, log2, xml_encode, xml_decode, translate_rgb_to_string

from code.constants.common import SCREEN_WIDTH, SCREEN_HEIGHT, PAUSE_MENU_X, PAUSE_MENU_Y, PAUSE_MENU_WIDTH, PAUSE_MENU_HEIGHT, MODE_GAME, TILE_WIDTH, TILE_HEIGHT, DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT, SPLASH_MODE_GREYSCALE_ANIMATED, LAYER_FOREGROUND

from code.constants.states import STATUS_ACTIVE, STATUS_INACTIVE, GAME_STATE_ACTIVE, GAME_STATE_NOT_READY
from code.constants.newsfeeder import *


# Linear death menu is almost exactly like the linear pause menu.
# The code works very similarly.
class LinearDeathMenu(Menu):

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


        # Retry level
        elif (action == "retry-level"):

            results.append(
                self.handle_retry_level_event(event, control_center, universe)
            )


        # Retry level - commit
        elif (action == "fwd.finish:retry-level"):

            results.append(
                self.handle_fwd_finish_retry_level_event(event, control_center, universe)
            )


        # Abandon level
        elif ( action == "leave-level" ):

            results.append(
                self.handle_leave_level_event(event, control_center, universe)
            )


        # Receive forwarded event, commit leave level
        elif ( action == "fwd.finish:leave-level" ):

            results.append(
                self.handle_fwd_finish_leave_level_event(event, control_center, universe)
            )


        # Discard this menu
        elif ( action == "kill" ):

            results.append(
                self.handle_kill_event(event, control_center, universe)
            )


        # Return events
        return results


    # Build the level death menu
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


        # Fetch the template for a level pause menu
        template = self.fetch_xml_template("linear.menu.death").add_parameters({
            "@x": xml_encode( "%d" % (SCREEN_WIDTH - (int( (SCREEN_WIDTH - PAUSE_MENU_WIDTH) / 2 ))) ),
            "@y": xml_encode( "%d" % int(SCREEN_HEIGHT / 2) ),
            "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT )
        })

        # Compile template
        root = template.compile_node_by_id("menu")

        # Build widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("level-death")


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


    # Retry the level
    def handle_retry_level_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Handle
        page1 = self.get_widget_by_id("level-death")

        # Slide and hide
        page1.slide(DIR_RIGHT, percent = 1.0)
        page1.hide()


        # Fetch window controller
        window_controller = control_center.get_window_controller()


        # Hook into the window controller
        window_controller.hook(self)

        # Fade the app, raising a (forwarded) event when done
        window_controller.fade_out(
            on_complete = "fwd.finish:retry-level"
        )

        # Return events
        return results


    # (Fwd) Finish retry level logic
    def handle_fwd_finish_retry_level_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Grab a copy of the current level's name
        name = universe.get_active_map().name


        # Remove the current level from the universe, forcing it to reload all of the map
        # data when we transition to the same map.
        universe.remove_map_on_layer_by_name(name, LAYER_FOREGROUND)

        # Activate the map we were trying, in the process rebuilding it from its default state.
        # Because we're on a linear level, we'll specify that we want to ignore adjacent maps.
        universe.activate_map_on_layer_by_name(name, LAYER_FOREGROUND, MODE_GAME, control_center, ignore_adjacent_maps = True)
        """
        # "Transition" to the same exact map.  Don't save any memory (we're on a level map), and don't remember where we were (retain the next-most-recent memory of the overworld map we came from)
        universe.transition_to_map(
            name = universe.get_active_map().name, # "Transition" to the map we're already on, prompting a reload and fresh UI
            waypoint_to = universe.get_session_variable("app.transition.to.waypoint").get_value(), # Retain the waypoint we previously spawned on
            save_memory = False,
            can_undo = False,
            control_center = control_center
        )
        """


        # Flag that we haven't handled player death, as we just brought the player back to life...
        universe.get_session_variable("core.handled-local-death").set_value("0")


        # Fetch window controller
        window_controller = control_center.get_window_controller()

        # Unhook from the window controller
        window_controller.unhook(self)


        # App fade in as we retry the level
        window_controller.fade_in()


        # Dismiss the current menu
        self.set_status(STATUS_INACTIVE)

        # Disengage the menu controller's pause lock
        control_center.get_menu_controller().configure({
            "pause-locked": False
        })


        # Return events
        return results


    # Leave the level, it's too hard :)
    def handle_leave_level_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Handle
        page1 = self.get_widget_by_id("level-death")

        # Slide and hide
        page1.slide(DIR_RIGHT, percent = 1.0)
        page1.hide()


        # Fetch window controller
        window_controller = control_center.get_window_controller()

        # Window fade, firing a return to menu event when done...
        window_controller.fade_out(
            on_complete = "app:leave-game"
        )

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
