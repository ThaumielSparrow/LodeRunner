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


class IdleMenu(Menu):

    def __init__(self):

        Menu.__init__(self)


        # Idle title
        self.title = "Message"

        # Idle message
        self.message = "Loading..."


        # Optional on-build event
        self.on_build = ""


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

        if ( "on-build" in options ):
            self.on_build = options["on-build"]


        # For chaining
        return self


    # Update the label on the idle menu
    def set_message(self, message):

        # Update the message tracker for posterity
        self.message = message


        # Get this idle menu's active page
        page = self.get_active_page()

        # Validate
        if (page):

            # Force metric recalculation (i.e. hack)
            page.invalidate_cached_metrics()
            page.focus()

            # Find the "message" label on the page
            label = page.find_widget_by_id("label-message")

            # Validate
            if (label):

                # Update the text
                label.set_text(message)


    # Handle an event
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
        template = self.fetch_xml_template("generic.idle").add_parameters({
            "@x": xml_encode( "%d" % int(SCREEN_WIDTH / 2) ),
            "@y": xml_encode( "%d" % int(SCREEN_HEIGHT / 2) ),
            "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
            "@title": xml_encode( "%s" % self.title ),
            "@message": xml_encode( "%s" % self.message )
        })

        # Compile template
        root = template.compile_node_by_id("menu")

        # Build widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("idle-menu")


        # Position page 1 to slide in from the top
        #widget.slide(DIR_UP, amount = 200, animated = False)
        # Now have it slide into its default position
        #widget.slide(None)


        # Add the new page
        self.add_widget_via_event(widget, event)


        # Make an explicit (redundant) call to show the widget, allowing us to specify an on-complete
        widget.show(
            on_complete = "finish:build"
        )

        # Return events
        return results


    # Run some extra logic once the build finishes
    def handle_finish_build_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        log2( "BUILD DONE!" )

        # Check for on-build event
        if (self.on_build != ""):

            results.add(
                action = self.on_build,
                params = {
                    "bubble": "1"
                }
            )

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
