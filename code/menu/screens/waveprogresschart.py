import os

import math
import random

import time

from code.menu.menu import Menu

from code.tools.eventqueue import EventQueue

from code.tools.xml import XMLParser

from code.utils.common import coalesce, intersect, offset_rect, log, log2, logn, xml_encode, xml_decode, translate_rgb_to_string

from code.constants.common import SCREEN_WIDTH, SCREEN_HEIGHT, PAUSE_MENU_X, PAUSE_MENU_Y, PAUSE_MENU_WIDTH, PAUSE_MENU_HEIGHT, MODE_GAME, TILE_WIDTH, TILE_HEIGHT, DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT
from code.constants.common import SPLASH_MODE_GREYSCALE_ANIMATED

from code.constants.states import STATUS_ACTIVE, STATUS_INACTIVE, GAME_STATE_ACTIVE, GAME_STATE_NOT_READY
from code.constants.newsfeeder import *


from code.constants.waves import *


class WaveProgressChart(Menu):

    def __init__(self):

        Menu.__init__(self)


        # Which requirements will this progress chart need to track?
        self.tracked_requirement_names = []

        # Which allowances will this progress chart need to track?
        self.tracked_allowance_names = []

        # Which limits will this progress chart need to track?
        self.tracked_limit_names = []


        # Fire a build event
        self.fire_event("build")


    # Configure
    def configure(self, options):

        # Common menu configuration
        self.__std_configure__(options)

        #print options


        if ( "tracked-requirement-names" in options ):

            self.tracked_requirement_names = options["tracked-requirement-names"]

            # Remove unrenderable names
            i = 0
            while ( i < len(self.tracked_requirement_names) ):

                # Don't render certain requirements
                if ( self.tracked_requirement_names[i] in UNRENDERABLE_NAMES ):

                    # Bye
                    self.tracked_requirement_names.pop(i)

                # Loop
                else:
                    i += 1

        if ( "tracked-allowance-names" in options ):
            self.tracked_allowance_names = options["tracked-allowance-names"]

            # Remove unrenderable names
            i = 0
            while ( i < len(self.tracked_allowance_names) ):

                # Don't render certain requirements
                if ( self.tracked_allowance_names[i] in UNRENDERABLE_NAMES ):

                    # Bye
                    self.tracked_allowance_names.pop(i)

                # Loop
                else:
                    i += 1

        if ( "tracked-limit-names" in options ):
            self.tracked_limit_names = options["tracked-limit-names"]

            # Remove unrenderable names
            i = 0
            while ( i < len(self.tracked_limit_names) ):

                # Don't render certain requirements
                if ( self.tracked_limit_names[i] in UNRENDERABLE_NAMES ):

                    # Bye
                    self.tracked_limit_names.pop(i)

                # Loop
                else:
                    i += 1


        # For chaining
        return self


    # Special processing for this type of menu
    def additional_processing(self, control_center, universe, debug = False):#user_input, raw_keyboard_input, network_controller, universe, active_map, session, widget_dispatcher, text_renderer, save_controller, debug = False):

        # Events from processing
        results = EventQueue()


        # Get the active map's wave tracker
        wave_tracker = universe.get_active_map().get_wave_tracker()

        # If the wave tracker has "dirty" data, then we should update the progress bars and labels on the wave progress chart
        if (wave_tracker.dirty):

            # Before beginning, let's mark the wave tracker as "clean" now.
            wave_tracker.dirty = False

            log2( "Updating wave progress chart..." )


            # Get a handle to the wave progress chart
            wave_progress_chart = control_center.get_menu_controller().get_menu_by_id("wave-progress-chart")

            # Validate
            if (wave_progress_chart):

                # We need page 1, it's a 1-page menu (chart)
                page = wave_progress_chart.get_active_page()

                # Validate
                if (page):

                    # Loop through each of the allowances we're tracking
                    for name in self.tracked_allowance_names:

                        # Get the widget that's holding the progress bar and stuff for this allowance
                        box = page.get_widget_by_rel(name)

                        # Validate
                        if (box):

                            # We want the progress bar (rect) and the status text (label)
                            (progress_bar, label) = (
                                box.find_widget_by_id("progress-bar"),
                                box.find_widget_by_id("status")
                            )


                            # Update the label's text.  We have to make a special case for "-1" allowances, which indicates an "unlimited" allowance
                            if ( wave_tracker.get_wave_allowance(name) < 0 ):

                                # Supply the percentage to the actual progress bar
                                progress_bar.configure({
                                    "visible-width": 1.0 # Always 100%, unlimited
                                })

                                label.configure({
                                    "value": "Unlimited"
                                })

                            # Otherwise, show how many allowances remain
                            else:

                                # If the allowance is 0, then we'll assume infinite (?)
                                if ( wave_tracker.get_wave_allowance(name) == 0 ):

                                    # Supply the percentage to the actual progress bar
                                    progress_bar.configure({
                                        "visible-width": 1.0 # Unlimited
                                    })

                                    label.configure({
                                        "value": "Unlimited"
                                    })

                                # Otherwise, show how many allowances remain
                                else:

                                    # Calculate the progress bar's visible width as a percentage.  Divide by a float to force a float result from the division job.
                                    percent = ( wave_tracker.get_wave_counter(name) / float( wave_tracker.get_wave_allowance(name) ) )

                                    # Don't go above 100%
                                    if (percent > 1.0):

                                        # Ceiling
                                        percent = 1.0


                                    # We want to render the "inverse" of the percent; we've used n%, so we have (100 - n)% remaining
                                    percent = 1.0 - percent


                                    # Supply the percentage to the actual progress bar
                                    progress_bar.configure({
                                        "visible-width": percent
                                    })

                                    label.configure({
                                        "value": "%d / %d" % ( (wave_tracker.get_wave_allowance(name) - wave_tracker.get_wave_counter(name)), wave_tracker.get_wave_allowance(name) )
                                    })


                    # Loop through each of the requirements we're tracking
                    for name in self.tracked_requirement_names:

                        # Get the widget that's holding the progress bar and stuff for this requirement
                        box = page.get_widget_by_rel(name)

                        # Validate
                        if (box):

                            # We want the progress bar (rect) and the status text (label)
                            (progress_bar, label) = (
                                box.find_widget_by_id("progress-bar"),
                                box.find_widget_by_id("status")
                            )


                            # Calculate the progress bar's visible width as a percentage.  Divide by a float to force a float result from the division job.
                            percent = ( wave_tracker.get_wave_counter(name) / float( wave_tracker.get_wave_requirement(name) ) )

                            # Don't go above 100%
                            if (percent > 1.0):

                                # Ceiling
                                percent = 1.0


                            # Supply the percentage to the actual progress bar
                            progress_bar.configure({
                                "visible-width": percent
                            })

                            # Update the label's text
                            label.configure({
                                "value": "%d / %d" % ( wave_tracker.get_wave_counter(name), wave_tracker.get_wave_requirement(name) )
                            })


                    # Lastly, loop through each tracked wave limit
                    for name in self.tracked_limit_names:

                        # Get the widget that's holding the progress bar and stuff for this requirement
                        box = page.get_widget_by_rel(name)

                        # Validate
                        if (box):

                            # We want the progress bar (rect) and the status text (label)
                            (progress_bar, label) = (
                                box.find_widget_by_id("progress-bar"),
                                box.find_widget_by_id("status")
                            )


                            # Calculate the progress bar's visible width as a percentage.  Divide by a float to force a float result from the division job.
                            percent = 1.0

                            # Avoid division by zero when the limit is 0 (i.e. not allowed to dig at all)
                            if ( wave_tracker.get_wave_limit(name) > 0 ):

                                percent = ( wave_tracker.get_wave_counter(name) / float( wave_tracker.get_wave_limit(name) ) )

                            # Don't go above 100%
                            if (percent > 1.0):

                                # Ceiling
                                percent = 1.0


                            # Supply the percentage to the actual progress bar
                            progress_bar.configure({
                                "visible-width": percent
                            })

                            # Update the label's text
                            label.configure({
                                "value": "%d / %d" % ( wave_tracker.get_wave_counter(name), wave_tracker.get_wave_limit(name) )
                            })


        # Return events
        return results


    # Handle (forward) an event
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
        elif ( action == "leave-puzzle" ):

            results.append(
                self.handle_leave_puzzle_event(event, control_center, universe)
            )


        # Receive forwarded event, commit leave puzzle
        elif ( action == "fwd.finish:leave-puzzle" ):

            results.append(
                self.handle_fwd_finish_leave_puzzle_event(event, control_center, universe)
            )


    # Build the intro menu
    def handle_build_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()

        # Save the font height for later, we'll need it repeatedly
        font_height = control_center.get_window_controller().get_default_text_controller().get_text_renderer().font_height


        # Fetch the wave progress chart template
        template = self.fetch_xml_template("wave.progress.chart").add_parameters({
            "@x": xml_encode( "%d" % (SCREEN_WIDTH - 24) ), # hard-coded
            "@y": xml_encode( "%d" % int(SCREEN_HEIGHT / 2) ),
            "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 1) ),
            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT )
        })

        # Compile template
        root = template.compile_node_by_id("wave-progress-chart")


        # First, loop through each allowance that we have to track, adding a widget for each
        for name in self.tracked_allowance_names:

            # Grab insert template
            template = self.fetch_xml_template( "wave.progress.chart.insert", version = "allowance" ).add_parameters({
                "@title": xml_encode( "%s" % HUMAN_READABLE_ALLOWANCE_NAMES[name] ),
                "@rel": xml_encode( "%s" % name ),
                "@status": xml_encode( "req %s:" % name ),
                "@font-height": xml_encode( "%d" % control_center.get_window_controller().get_default_text_controller().get_text_renderer().font_height )
            })

            # Compile insert
            node = template.compile_node_by_id("insert")

            # Add it to the progress chart
            root.find_node_by_id("ext.members").add_node(node)


        # Now, loop through each requirement that we have to track and add a widget for each
        for name in self.tracked_requirement_names:

            # Grab insert template
            template = self.fetch_xml_template( "wave.progress.chart.insert", version = "requirement" ).add_parameters({
                "@title": xml_encode( "%s" % HUMAN_READABLE_REQUIREMENT_NAMES[name] ),
                "@rel": xml_encode( "%s" % name ),
                "@status": xml_encode( "req %s:" % name ),
                "@font-height": xml_encode( "%d" % control_center.get_window_controller().get_default_text_controller().get_text_renderer().font_height )
            })

            # Compile insert
            node = template.compile_node_by_id("insert")

            # Add it to the progress chart
            root.find_node_by_id("ext.members").add_node(node)


        # Lastly, loop through each limit that we need to track and add in a widget
        for name in self.tracked_limit_names:

            # Grab insert template
            template = self.fetch_xml_template( "wave.progress.chart.insert", version = "limit" ).add_parameters({
                "@title": xml_encode( "%s" % HUMAN_READABLE_LIMIT_NAMES[name] ),
                "@rel": xml_encode( "%s" % name ),
                "@status": xml_encode( "req %s:" % name ),
                "@font-height": xml_encode( "%d" % font_height )
            })

            # Compile insert
            node = template.compile_node_by_id("insert")

            # Add it to the progress chart
            root.find_node_by_id("ext.members").add_node(node)


        #print root.compile_xml_string()
        #print 5/0


        # Build widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("progress-chart")


        # Position page 1 to slide in from the top
        widget.slide(DIR_UP, amount = 200, animated = False)

        # Now have it slide into its default position
        widget.slide(None)


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
        page1 = self.get_widget_by_id("puzzle-intro")

        # Slide and hide
        page1.slide(DIR_RIGHT, percent = 1.0)
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
    def handle_leave_puzzle_event(self, event, control_center, universe):

        # Track local results
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Hook into the universe so that we get forwarded events
        #universe.hook(self)


        # Handle
        page1 = self.get_widget_by_id("puzzle-intro")

        # Slide and hide
        page1.slide(DIR_RIGHT, percent = 1.0)
        page1.hide()


        # Fetch window controller
        window_controller = control_center.get_window_controller()

        # Hook into window controller
        window_controller.hook(self)

        # App-level fade, followed by a (forwarded) event...
        window_controller.fade_out(
            on_complete = "fwd.finish:leave-puzzle" # The universe itself won't care about this event
        )

        # Return events
        return results


    # (Forwarded) Finish "leave puzzle" logic
    def handle_fwd_finish_leave_puzzle_event(self, event, control_center, universe):

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


    # Overwriting the draw routine to skip any lightbox effect.
    # Default drawing routine for a Menu.  Overwrite if necessary.
    def draw(self, tilesheet_sprite, additional_sprites, text_renderer, window_controller):

        # Now render the overlays in lowest-to-highest order...
        for z in range( 0, len(self.widgets) ):

            logn( "wave-progress draw", "z = %d, alpha = %s" % (z, self.widgets[z].alpha_controller.get_interval()) )

            # Don't bother rendering "invisible" widgets (still fading in, dismissed and hidden, whatever...)
            if ( self.widgets[z].alpha_controller.get_interval() > 0 ):

                #print "**render overlay[%d]:  %s" % (z, self.widgets[z]), self.widgets[z].alpha_controller.get_interval()

                self.widgets[z].draw(self.x, self.y, tilesheet_sprite, additional_sprites, text_renderer, window_controller)

