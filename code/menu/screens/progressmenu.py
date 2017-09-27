import os

import math
import random

import time

from code.menu.menu import Menu

from code.tools.eventqueue import EventQueue

from code.tools.xml import XMLParser

from code.utils.common import coalesce, intersect, offset_rect, log, log2, xml_encode, xml_decode, translate_rgb_to_string

from code.constants.common import SCREEN_WIDTH, SCREEN_HEIGHT, PAUSE_MENU_X, PAUSE_MENU_Y, PAUSE_MENU_WIDTH, PAUSE_MENU_HEIGHT, MODE_GAME, TILE_WIDTH, TILE_HEIGHT, DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT

from code.constants.states import STATUS_ACTIVE, STATUS_INACTIVE
from code.constants.newsfeeder import *


class ProgressMenu(Menu):

    def __init__(self):

        Menu.__init__(self)


        # Progress title
        self.title = "Message"

        # Progress message
        self.message = "Downloading..."


        # Fire build event
        self.fire_event("build")


    # Configure
    def configure(self, options):

        # Common menu configuration
        self.__std_configure__(options)


        if ( "title" in options ):
            self.title = options["title"]

        if ( "message" in options ):
            self.message = options["message"]


        # For chaining
        return self


    def handle_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        results.inject_event(event)

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


        # When the widget finishes showing, I might raise an on-build event.
        # I just want to wait until it shows before I do anything.  It's hacky.
        elif ( action == "finish:build" ):

            results.append(
                self.handle_finish_build_event(event, control_center, universe)
            )


        # Bubble an event
        elif ( action == "bubble-event" ):

            results.append(
                self.handle_bubble_event(event, control_center, universe)
            )


        # Kill / dismiss the idle thing
        elif ( action == "kill" ):

            results.append(
                self.handle_kill_event(event, control_center, universe)
            )


        # Deactivate entire idle menu
        elif ( action == "finish:kill" ):

            results.append(
                self.handle_finish_kill_event(event, control_center, universe)
            )


        # Return events
        return results


    # Build the idle menu
    def handle_build_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Fetch the puzzle intro template
        template = self.fetch_xml_template( "generic.progress", version = "download" ).add_parameters({
            "@x": xml_encode( "%d" % int(SCREEN_WIDTH / 2) ),
            "@y": xml_encode( "%d" % int(SCREEN_HEIGHT / 2) ),
            "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
            "@title": xml_encode( "%s" % self.title ),
            "@message": xml_encode( "%s" % self.message ),
            "@font-height": xml_encode( "%d" % control_center.get_window_controller().get_default_text_controller().get_text_renderer().font_height )
        })

        # Compile template
        root = template.compile_node_by_id("menu")

        # Build widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("progress-menu")


        # Position page 1 to slide in from the top
        #widget.slide(DIR_UP, amount = 200, animated = False)
        # Now have it slide into its default position
        #widget.slide(None)


        # Add the new page
        self.add_widget_via_event(widget, event)


        # Return events
        return results


    # (?) Handle a bubble event
    def handle_bubble_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # What was the event?
        event = self.get_active_page().get_attribute("event")

        # Raise the event
        results.add(
            action = event,
            params = {
                "bubble": "1"
            }
        )

        # Return events
        return results


    # Kill event
    def handle_kill_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Get the main page
        widget = self.get_widget_by_id("idle-menu")

        # Slide
        widget.slide(DIR_UP, amount = -SCREEN_HEIGHT)

        # Hide, raising kill event when gone
        widget.hide(
            on_complete = "finish:kill"
        )

        # Return events
        return results


    # Finish kill logic, post-fade
    def handle_finish_kill_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Trash
        self.set_status(STATUS_INACTIVE)

        # Return events
        return results
