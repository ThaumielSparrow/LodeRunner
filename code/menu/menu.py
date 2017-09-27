import sys
import os

import math
import random

import time

from pygame.locals import K_ESCAPE

from code.tools.eventqueue import EventQueue

from code.controllers.historycontroller import HistoryController
from code.controllers.intervalcontroller import IntervalController

from code.extensions.common import UITemplateLoaderExt, HookableExt

from code.tools.xml import XMLParser

#from glfunctions import draw_rounded_rect, draw_line, draw_rect, draw_rect_frame

from code.utils.common import coalesce, intersect, offset_rect, log, log2, xml_encode, xml_decode, sort_files_by_date, get_file_modified_time, format_timedelta, translate_rgb_to_string, get_flag_value

from code.constants.common import SCREEN_WIDTH, SCREEN_HEIGHT, PAUSE_MENU_X, PAUSE_MENU_Y, PAUSE_MENU_WIDTH, PAUSE_MENU_HEIGHT, PAUSE_MENU_SIDEBAR_X, PAUSE_MENU_SIDEBAR_Y, PAUSE_MENU_SIDEBAR_WIDTH, PAUSE_MENU_SIDEBAR_CONTENT_WIDTH, PAUSE_MENU_CONTENT_X, PAUSE_MENU_CONTENT_Y, PAUSE_MENU_CONTENT_WIDTH, PAUSE_MENU_CONTENT_HEIGHT, SKILL_PREVIEW_WIDTH, SKILL_PREVIEW_HEIGHT, MODE_GAME, TILE_WIDTH, TILE_HEIGHT, CAMERA_SPEED, INPUT_SELECTION_UP, INPUT_SELECTION_DOWN, INPUT_SELECTION_LEFT, INPUT_SELECTION_RIGHT, INPUT_SELECTION_ACTIVATE, PAUSE_MENU_PROMPT_WIDTH, PAUSE_MENU_PROMPT_CONTENT_WIDTH, ACTIVE_SKILL_LIST, SKILL_LIST, SKILL_LABELS, SKILLS_BY_CATEGORY, CATEGORIES_BY_SKILL, SKILL_OPPOSITES, SKILL_ICON_INDICES, DATE_WIDTH, DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT, MAX_QUICKSAVE_SLOTS, MAX_AUTOSAVE_SLOTS, PAUSE_MENU_PRIZE_AD_HEIGHT, OVERWORLD_GAME_OVER_MENU_WIDTH, DEFAULT_PLAYER_COLORS, WORLDMAP_VIEW_LABELS, CATEGORY_LABELS, MAX_SKILL_SLOTS, LAYER_FOREGROUND, LAYER_BACKGROUND

from code.constants.states import STATUS_ACTIVE, STATUS_INACTIVE
from code.constants.network import NET_STATUS_SERVER, NET_STATUS_CLIENT
from code.constants.newsfeeder import *


class Menu(UITemplateLoaderExt, HookableExt):

    def __init__(self):#, x, y, w, h, universe, session):

        UITemplateLoaderExt.__init__(self)
        HookableExt.__init__(self)


        # We can give a menu an id if we want.  Optional.
        self.id = ""


        # Menu status (we set it to INACTIVE when we're completely done with it)
        self.status = STATUS_ACTIVE


        # We'll use a HistoryController to track user input events, such that we can
        # follow the same input path when refreshing overlays (to update readouts after
        # game saves, skill upgrades, etc.)
        self.history_controller = HistoryController()


        # A menu has an event queue (which it may or may not ever care to use)
        self.event_queue = EventQueue()


        # Menu position
        self.x = 0
        self.y = 0

        self.width = 0
        self.height = 0



        # Are we done with the UI menu?  (Back to game, maybe?)
        self.is_dismissed = False

        # Do anything on dismissal?
        self.on_dismissal = None



        # Get preferred lightbox target
        target = get_flag_value("menu_lightbox_intensity", XMLParser())

        # Try to convert flag value to a float.
        # Failure (via empty or invalid value) will force default.
        try:
            target = float(target)

            # Clamp
            if (target < 0):
                target = 0
            elif (target > 1.0):
                target = 1.0

        # Default lightbox target is 0.45
        except:
            target = 0.45

        # Menus themselves don't have alpha (only the overlays),
        # but they do control the menu-global lightbox effect...
        self.lightbox_controller = IntervalController(
            interval = 0,
            target = target,
            speed_in = (0.005625 / 0.45), # Equals 0.0125 for the default target, scales to same overall speed as target changes #0.0125,
            speed_out = 0.010
        )


        # A stack of widgets (pages, per se) that represents the menu (e.g. page 1 = root menu, page 2 = skill tree, etc.)
        self.widgets = []

        # Sometimes we want to queue some function(s)...
        self.queue_collection = []


    # Configuration common to any menu screen
    def __std_configure__(self, options):

        if ( "id" in options ):
            self.id = options["id"]

        if ( "x" in options ):
            self.x = int( options["x"] )

        if ( "y" in options ):
            self.y = int( options["y"] )

        if ( "width" in options ):
            self.width = int( options["width"] )

        if ( "height" in options ):
            self.height = int( options["height"] )


        # For chaining
        return self


    # Default configuration.  Overwrite as necessary.
    def configure(self, options):

        # Just do a standard configure
        self.__std_configure__(options)


        # For chaining
        return self


    def get_id(self):

        return self.id


    def get_status(self):

        return self.status


    def set_status(self, status):

        self.status = status


    # Convenience function that addes an event (with optional params) to the event queue
    def fire_event(self, event, params = {}):

        # Add the event
        self.event_queue.add(
            action = event,
            params = params
        )


    # Simple redirect, I want to have an explicit name (i.e. _with_params) for this though...
    def fire_event_with_params(self, event, params):

        self.fire_event(event, params)


    # Fading away?
    def is_fading(self):

        return ( self.alpha_controller.get_target() == 0 )


    # Faded away?
    def is_gone(self):

        return ( ( self.lightbox_controller.get_interval() <= self.lightbox_controller.get_target() ) and ( len(self.overlay_collection) == 0 ) )


    def process_lightbox(self):

        self.lightbox_controller.process()


    def get_lightbox_interval(self):

        return self.lightbox_controller.get_interval()


    # Return the simple event queue
    def get_event_queue(self):

        return self.event_queue


    def activate(self, f_on_arrival = None):

        self.is_dismissed = False

        self.queue_collection = []


    def dismiss(self, spared_overlay_count = 0, f_on_dismissal = None):

        log( "goodbye, UIMenu!" )

        # If we have visible overlays, let's fade them out one at a time...
        if (len(self.overlay_collection) > 0):

            log( "destroy overlay" )

            self.overlay_collection[-1].dismiss(
                lambda a = self, b = f_on_dismissal: a.dismiss(f_on_dismissal = b)
            )

        # Otherwise, we're done with the Menu...
        else:

            log( "overlays gone, let's vanish..." )

            self.lightbox_controller.set_target(0)
            self.is_dismissed = True

            self.on_dismissal = f_on_dismissal


    # Fade any visible overlay (all at once)
    #def 


    # This is an instant dismiss... forget the overlays...
    def abort(self, f_on_abort = None):

        self.is_dismissed = True

        self.lightbox_controller.set_interval(0)
        self.lightbox_controller.set_target(0)

        self.widgets = []

        # Callback?
        if (f_on_abort):

            f_on_abort()


    def add_widget_via_event(self, widget, event, exclusive = True):

        # Events that result from adding the overlay (e.g. on-birth)
        results = EventQueue()

        """
        # Add the record to our overlay history, as long as this is a new overlay
        # (as opposed to a refresh of all overlays)...
        if ( (historical) and (not refresh) ):

            # Remember 2 things:
            #   1)  The current overlay's cursor position (if applicable)
            #   2)  The params we called to create the current overlay

            record = None

            if (len(self.overlay_collection) > 0):

                self.overlay_history[-1].widget_state = self.overlay_collection[-1].overlay.get_state()

                record = OverlayHistoryRecord(None, params)

            else:
                record = OverlayHistoryRecord(None, params)


            self.overlay_history.append(record)
        """


        # Remove focus from the prior overlay, if we have one...
        if ( len(self.widgets) > 0 ):

            self.widgets[-1].blur()


        # The widget should track its "exclusive" stats as a custom attribute
        widget.set_attribute(
            "exclusive",
            "yes" if (exclusive) else "no"
        )

        # Make sure to all .focus() on the new widget
        widget.focus()


        # Add the widget as a new page
        self.widgets.append(widget)


        # Track the event (the one that prompted us to add this widget) in history
        self.history_controller.push(
            event
        )


        # See if we have a snapshot (we'll take a snapshot of the entire overlay stack
        # when refreshing overlays) to load into the widget we're adding...
        snapshot = self.history_controller.load_snapshot_by_id( widget.get_id() )

        # Validate
        if (snapshot):

            # Restore the state of the widget to how it looked at the time of the snapshot
            widget.load_state(snapshot)

            # We want the widget to remain in that state until we have concluded whatever
            # we were doing (i.e. most likely, refreshing the overlays) that required the
            # snapshot in the first place.  (This prevents subsequent events from sliding
            # earlier-born widgets around and such, sullying their snapshot state.
            widget.lock()


        # If this is an exclusive overlay, then make sure to fade out any lower overlay...
        if (exclusive):

            # Do we even have any lower widget page?
            if ( len(self.widgets) > 1 ):

                # Hide all of the lower widgets
                for z in range( 0, len(self.widgets) - 1 ):

                    # Goodbye
                    self.widgets[z].hide()


                # Make sure the new widget waits a little bit (starting in the negative alpha range) before appearing
                widget.hide(
                    target = -self.widgets[-2].alpha_controller.get_interval(),
                    animated = False
                )

                widget.show(target = 0.9)


            # If not, then we'll fade in the new overlay, making it come into view just as the root pause menu disappears...
            else:

                #self.overlay_collection[-1].alpha_controller.summon()
                widget.alpha_controller.set_target(0.9)

        else:

            #self.overlay_collection[-1].fade(a = None, b = 0.9)
            widget.alpha_controller.set_target(0.9)


        # Track on-birth events
        results.append(
            widget.handle_birth()
        )

        # Return events
        return results


    # Get one of the widget pages by the widget's id
    def get_widget_by_id(self, widget_id):

        for widget in self.widgets:

            if ( widget.get_id() == widget_id ):

                return widget


        # Couldn't find it
        return None


    # Remove a widget by its id
    def remove_widget_by_id(self, widget_id):

        # Loop
        i = 0
        while ( i < len(self.widgets) ):

            # id match?
            if ( self.widgets[i].get_id() == widget_id ):

                # Remove now
                self.widgets.pop(i)

            else:
                i += 1


    # Get the highest (active) page
    def get_active_page(self):

        # Sanity
        if ( len(self.widgets) > 0 ):

            # Return top page
            return self.widgets[-1]

        # No page available
        else:

            # Sorry
            return None


    def handle_user_input(self, control_center, universe):

        # Events resulting from user input
        results = EventQueue()

        if ( len(self.widgets) > 0 ):

            # Make sure the highest overlay is visible (?)
            if ( self.widgets[-1].alpha_controller.get_target() > 0 ):

                results.append(
                    self.widgets[-1].handle_user_input(control_center, universe)
                )

        # Return events
        return results


    #def process_overlays(self, user_input, raw_keyboard_input, network_controller, universe, active_map, session, widget_dispatcher, text_renderer, save_controller):
    def process_widgets(self, control_center, universe):

        # Events that result from processing the overlays
        results = EventQueue()


        # Process lightbox behind overlays...
        self.process_lightbox()


        """
        # If the top-most widget (1) has been dismissed, and (2) is fully gone, then we'll remove it and try to go to the previous page
        if ( self.widgets[-1].alpha_controller.get_interval() == self.widgets[-1].alpha_controller.get_target() == 0 ):

            # Make sure this menu is still alive
            if ( self.get_status() == STATUS_ACTIVE ):

                # Back to the previous page
                self.page_back(1)

            # Otherwise, just delete all pages
            else:

                self.widgets = []
        """


        # Process widgets
        for i in range( 0, len(self.widgets) ):

            results.append(
                self.widgets[i].process(control_center, universe)
            )


        # Return events
        return results


    def page_back(self, pages = 1):

        for i in range( 0, pages ):

            log2( "Moving back one page...\n" )

            if ( len(self.widgets) > 0 ):

                # Remove the top overlay
                self.widgets.pop()

                # Drop from history the event that caused us to create the widget we just trashed
                self.history_controller.pop()


        if ( self.get_status() == STATUS_ACTIVE ):

            # Show the highest page, if one still exists
            if ( len(self.widgets) > 0 ):

                # Focus, show
                self.widgets[-1].focus()
                self.widgets[-1].show(0.9)

        else:

            self.widgets = []


    # Reset all pages (delete everything!)
    def reset(self):

        while ( len(self.widgets) > 0 ):

            # Clear last page
            widget = self.widgets.pop()

            # Clear history
            self.history_controller.pop()


    # Close all pages, clear all pages
    def close(self, control_center):

        # Close all widgets
        while ( len(self.widgets) > 0 ):

            # Clear last widget
            widget = self.widgets.pop()

            # Close widget
            widget.close(control_center)

            # Clear history
            self.history_controller.pop()


    # Get all of the pages in a menu
    def get_pages(self, minimum = 0):

        if (minimum == 0):

            return self.widgets

        else:

            return self.widgets[ minimum : len(self.widgets) ]


    # Get only the visible pages
    def get_visible_pages(self):

        # Find the earliest visible page
        i = len(self.widgets) - 1


        # Loop
        while (i >= 0):

            # Is this the earliest visible page?
            if ( self.widgets[i].get_attribute("exclusive") == "yes" ):

                return self.get_pages(minimum = i)

            # Nope...
            else:
                i -= 1


        # Every page is visible
        return self.get_pages(minimum = 0)


    def refresh_pages(self, control_center, universe, curtailed_count = 0):#user_input, network_controller, universe, active_map, session, widget_dispatcher, text_renderer, save_controller, curtailed_count = 0):

        # Save however many widgets we're "skipping" (i.e. preserving) at the end
        curtailed_widget_collection = []

        for i in range(0, curtailed_count):

            curtailed_widget_collection.append( self.widgets.pop() )


        #f = open( os.path.join("debug", "snapshots.txt"), "w" )
        #f.close()

        # Save a snapshot for any widget that we gave an id to
        for widget in self.widgets:

            if ( widget.get_id() != "" ):

                self.history_controller.save_snapshot_with_id(
                    widget.save_state(),
                    widget.get_id()
                )


        # Reset the widgets (pages)
        self.widgets = []




        # Lock the history controller before we continue.  This prevents the refresh process
        # (reacting to user input) from adding to the history trace.  We don't want to do that;
        # we just want to refresh what's already there.
        self.history_controller.lock()

        # Fetch event trace
        trace = self.history_controller.get_trace()


        # Go through the trace one-by-one, adding each to the event queue.
        # Ignore, though, the trace events that created any overlay we're
        # preserving.
        for trace_event in trace[ 0 : len(trace) - curtailed_count ]:

            event_queue = EventQueue()

            # Add this trace event to the event queue
            event_queue.inject_event(trace_event)


            # Now fetch that event back from the queue
            event = event_queue.fetch()

            # Process until we've reacted to not only the trace event but any followup events
            # that might result from that particular user input.
            while (event):

                # Response do the event based on its parameters...
                event_queue.append(
                    self.handle_event(
                        event,
                        control_center = control_center,
                        universe = universe
                    )
                )

                self.widgets[-1].process(control_center, universe)


                # Check for more events
                event = event_queue.fetch()


            # At the end, let's check the command queue for any functions we want to call...
            self.process_queue()


        # Free to add new page records to the history controller again
        self.history_controller.unlock()


        # Unlock all recreated widgets (we locked each of these when we restored its snapshot)
        for widget in self.widgets:

            # Now that we have finished recreating the widget (pages) of this menu,
            # we should permit real-time, event-based modifications to the widget.
            widget.unlock()


        # Now let's place the "curtailed" widget collection items back onto the end of the widget collection.
        # We don't need to unlock these; we never locked them, we put them on ice...
        self.widgets.extend(curtailed_widget_collection)


        # Poke every widget to make sure it's awake and all that
        for widget in self.widgets:

            # Wake it up, in case it has an onchange event that some part of the page depends upon...
            widget.poke()


        # Clear out all of the snapshots we took prior to refreshing the pages
        self.history_controller.clear_snapshots()


    def queue(self, f):

        self.queue_collection.append(f)


    def process_queue(self):

        # At the end, let's check the command queue for any functions we want to call...
        while (len(self.queue_collection) > 0):

            # First in line...
            f = self.queue_collection.pop(0)

            # Call the function
            f()


    def loop_events(self, queue, control_center, universe):

        # some events bubble
        results = EventQueue()


        event = queue.fetch()

        while (event):

            if ( event.get_param("bubble") == "1" ):

                results.inject_event(event)

            results.append(
                self.handle_event(event, control_center, universe)
            )

            # forward the event to any hooked-in listener
            results.append(
                self.forward_event_to_listeners(event, control_center, universe)
            )


            event = queue.fetch()


        return results

        """
        # React to user input events as necessary
        event = self.event_queue.fetch()

        # Process until we've reacted to any and all user input
        while (event):

            #print "**", 
            #print control_center.get_input_controller().get_gameplay_input()

            # Bubbling event?
            if ( event.get_param("bubble") == "1" ):

                results.inject_event(event)


            # Response do the event based on its parameters...
            self.event_queue.append(
                self.handle_event(
                    event,
                    control_center = control_center,
                    universe = universe
                )
            )

            # Check for more events
            event = self.event_queue.fetch()


        # Return bubbled events
        return results
        """


    def process(self, control_center, universe, debug = False):

        # Events that might result from processing the menu itself
        results = EventQueue()


        # Handle lightbox animation
        self.process_lightbox()


        # Handle input
        self.event_queue.append(
            self.handle_user_input(control_center, universe)
        )

        # Check events, collecting bubbling events
        results.append(
            self.loop_events(self.event_queue, control_center, universe)
        )


        # Process widgets, if applicable.
        if ( (len(self.widgets) > 0) ):

            local_results = self.process_widgets(control_center, universe)#user_input, raw_keyboard_input, network_controller, universe, active_map, session, widget_dispatcher, text_renderer, save_controller)

            # Check events (again), collecting bubbling events
            results.append(
                self.loop_events(local_results, control_center, universe)
            )

        # Handle any additional processing
        results.append(
            self.additional_processing(control_center, universe)#user_input, raw_keyboard_input, network_controller, universe, active_map, session, widget_dispatcher, text_renderer, save_controller, debug = debug)
        )


        # At the end, let's check the command queue for any functions we want to call...
        self.process_queue()


        # Return events
        return results


    # For inheriting classes
    def additional_processing(self, control_center, universe, debug = False):#user_input, raw_keyboard_input, network_controller, universe, active_map, session, widget_dispatcher, text_renderer, save_controller, debug = False):

        return EventQueue()


    # Default drawing routine for a Menu.  Overwrite if necessary.
    def draw(self, tilesheet_sprite, additional_sprites, text_renderer, window_controller):

        # Fetch lightbox interval
        lightbox_interval = self.get_lightbox_interval()

        # Render lightbox effect
        window_controller.get_geometry_controller().draw_rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (0, 0, 0, lightbox_interval))


        if (not self.is_dismissed):

            # Now render the overlays in lowest-to-highest order...
            for z in range( 0, len(self.widgets) ):

                # Don't bother rendering "invisible" widgets (still fading in, dismissed and hidden, whatever...)
                if ( self.widgets[z].alpha_controller.get_interval() > 0 ):

                    #print "**render overlay[%d]:  %s" % (z, self.widgets[z]), self.widgets[z].alpha_controller.get_interval()

                    self.widgets[z].draw(self.x, self.y, tilesheet_sprite, additional_sprites, text_renderer, window_controller)

