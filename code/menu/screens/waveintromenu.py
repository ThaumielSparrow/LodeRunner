import os

import math
import random

import time

from code.menu.menu import Menu

from code.tools.eventqueue import EventQueue

from code.tools.xml import XMLParser

from code.utils.common import coalesce, intersect, offset_rect, log, log2, xml_encode, xml_decode, translate_rgb_to_string

from code.constants.common import SCREEN_WIDTH, SCREEN_HEIGHT, PAUSE_MENU_X, PAUSE_MENU_Y, PAUSE_MENU_WIDTH, PAUSE_MENU_HEIGHT, MODE_GAME, TILE_WIDTH, TILE_HEIGHT, DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT
from code.constants.common import SPLASH_MODE_GREYSCALE_ANIMATED

from code.constants.states import STATUS_ACTIVE, STATUS_INACTIVE, GAME_STATE_ACTIVE, GAME_STATE_NOT_READY
from code.constants.newsfeeder import *


class WaveIntroMenu(Menu):

    def __init__(self):#, x, y, w, h, universe, session, widget_dispatcher, node):

        Menu.__init__(self)#, x, y, w, h, universe, session)

        # Fire a build event
        self.fire_event("build")


    def handle_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        (action, params) = (
            event.get_action(),
            event.get_params()
        )


        # Set up the widget
        if ( action == "build" ):

            results.append(
                self.handle_build_event(event, control_center, universe)
            )


        # Begin puzzle
        elif ( action == "begin" ):

            results.append(
                self.handle_begin_event(event, control_center, universe)
            )


        # Really begin puzzle
        elif ( action == "finish:begin" ):

            results.append(
                self.handle_finish_begin_event(event, control_center, universe)
            )


        # Abandon puzzle
        elif ( action == "leave-wave" ):

            results.append(
                self.handle_leave_wave_event(event, control_center, universe)
            )


        # Receive forwarded event, commit leave wave
        elif ( action == "fwd.finish:leave-wave" ):

            results.append(
                self.handle_fwd_finish_leave_wave_event(event, control_center, universe)
            )


    # Build the intro menu
    def handle_build_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()

        # Handle
        localization_controller = control_center.get_localization_controller()


        # Pause game action as we use the intro menu
        universe.pause()


        # Pause lock the menu controller; can't pause until you've made a choice!
        control_center.get_menu_controller().configure({
            "pause-locked": True
        })

        # Summon the pause splash
        control_center.get_splash_controller().set_mode(SPLASH_MODE_GREYSCALE_ANIMATED)


        # Fetch the puzzle intro template
        template = self.fetch_xml_template("wave.menu.intro").add_parameters({
            "@x": xml_encode( "%d" % int( (SCREEN_WIDTH - PAUSE_MENU_WIDTH) / 2 ) ),
            "@y": xml_encode( "%d" % PAUSE_MENU_Y ),
            "@width": xml_encode( "%d" % (int(PAUSE_MENU_WIDTH) / 2) ),
            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT ),
            "@overview": xml_encode( "%s" % localization_controller.translate( universe.get_active_map().get_param("overview") ) ),
            "@current-wave": xml_encode( "%s" % universe.get_session_variable("core.challenge.wave").get_value() ),
            "@wave-goal": xml_encode( "%s" % localization_controller.translate( universe.get_active_map().get_param("wave-goal") ) ),
            "@overworld-title": xml_encode( "%s" % universe.get_session_variable("core.overworld-title").get_value() )
        })

        # Compile template
        root = template.compile_node_by_id("layout")

        # Build widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("wave-intro")


        # Position page 1 to slide in from the left
        widget.slide(DIR_LEFT, percent = 1.0, animated = False)

        # Now have it slide into its default position
        widget.slide(None)


        # I want to force this particular menu to fade in at the same rate as the universe itself.
        # Otherwise, everything looks awkward.
        widget.configure_alpha_controller({
            "speed-in": universe.alpha_controller.get_speed_in()
        })


        # Add the new page
        self.add_widget_via_event(widget, event)

        # Return events
        return results


    # Begin the puzzle (fade out splash and menu)
    def handle_begin_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Handle
        page1 = self.get_widget_by_id("wave-intro")

        # Slide and hide
        page1.slide(DIR_LEFT, percent = 1.0)
        page1.hide(
            on_complete = "finish:begin"
        )


        # Dismiss the pause splash; begin puzzle when gone
        control_center.get_splash_controller().dismiss(
            on_complete = "game:unpause"
        )


        # Return events
        return results


    # Handle last aspects of beginning a puzzle.  Activate game, etc.
    def handle_finish_begin_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()



        # Dismiss this menu
        self.set_status(STATUS_INACTIVE)

        # Disengage the menu controller's pause lock
        control_center.get_menu_controller().configure({
            "pause-locked": False
        })

        # Return events
        return results


    # Leave a puzzle
    def handle_leave_wave_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Hook into the universe so that we get forwarded events
        #universe.hook(self)


        # Handle
        page1 = self.get_widget_by_id("wave-intro")

        # Slide and hide
        page1.slide(DIR_LEFT, percent = 1.0)
        page1.hide()


        # Fetch window controller
        window_controller = control_center.get_window_controller()

        # Hook into window controller
        window_controller.hook(self)

        # App-level fade, followed by a (forwarded) event...
        window_controller.fade_out(
            on_complete = "fwd.finish:leave-wave" # The universe itself won't care about this event
        )

        # Return events
        return results


    # (Forwarded) Finish "leave puzzle" logic
    def handle_fwd_finish_leave_wave_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Trash this menu
        self.set_status(STATUS_INACTIVE)


        # Disengage the menu controller's pause lock
        control_center.get_menu_controller().configure({
            "pause-locked": False
        })

        # Abort the splash controller
        control_center.get_splash_controller().abort()


        # Undo the last map transition.  Don't save memory:  this is a self-contained puzzle map
        universe.undo_last_map_transition(control_center = control_center, save_memory = False)

        # Set universe to playable
        universe.unpause()


        # Fetch window controller
        window_controller = control_center.get_window_controller()

        # Unhook from the universe; we don't care about its events anymore
        window_controller.unhook(self)


        # App fade in, as we retreat back to the overworld instead of trying the puzzle :)
        window_controller.fade_in()


        # Return events
        return results

