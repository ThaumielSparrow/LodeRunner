import os

import math
import random

import time

from code.menu.menu import Menu

from code.tools.eventqueue import EventQueue

from code.tools.xml import XMLParser

from code.utils.common import coalesce, intersect, offset_rect, log, log2, logn, xml_encode, xml_decode, translate_rgb_to_string

from code.constants.common import SCREEN_WIDTH, SCREEN_HEIGHT, PAUSE_MENU_X, PAUSE_MENU_Y, PAUSE_MENU_WIDTH, PAUSE_MENU_HEIGHT, MODE_GAME, TILE_WIDTH, TILE_HEIGHT, DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT, SPLASH_MODE_GREYSCALE_ANIMATED

from code.constants.states import STATUS_ACTIVE, STATUS_INACTIVE, GAME_STATE_ACTIVE, GAME_STATE_NOT_READY
from code.constants.newsfeeder import *


class PuzzleVictoryMenu(Menu):

    def __init__(self):

        Menu.__init__(self)


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


        # Confirm item selection (i.e. are you sure?)
        elif ( action == "show:confirm" ):

            results.append(
                self.handle_show_confirm_event(event, control_center, universe)
            )


        # Go back to page 1 (reconsider prize selection)
        elif ( action == "hide:confirm" ):

            results.append(
                self.handle_hide_confirm_event(event, control_center, universe)
            )


        # Commit a "one page back" event
        elif ( action == "previous-page" ):

            # Page back 1 page
            self.page_back(1)


        # Take an item (confirm the selection)
        elif ( action == "take-item" ):

            results.append(
                self.handle_take_item_event(event, control_center, universe)
            )


        # Receive forwarded event calling for cleanup (dismiss menu, check for puzzle complete script, etc.)
        elif ( action == "fwd:finish:take-item" ):

            results.append(
                self.handle_fwd_finish_take_item_event(event, control_center, universe)
            )


        # Reset menu (?)
        elif ( action == "reset" ):

            # Clear all pages
            self.reset()


    # Build the victory menu
    def handle_build_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()

        # Handle
        localization_controller = control_center.get_localization_controller()


        # Pause the game
        universe.pause()

        # Enable pause lock so the player can't hit ESC to pause
        control_center.get_menu_controller().configure({
            "pause-locked": True
        })

        # Call in splash
        control_center.get_splash_controller().set_mode(SPLASH_MODE_GREYSCALE_ANIMATED)


        # Start with an empty prize item list
        prize_item_names = []

        # Fetch the active map; it contains various prize parameters...
        m = universe.get_active_map()

        # Determine the various prize parameters
        (warehouses, min_quality, max_quality, required_item_names) = (
            coalesce( m.get_param("prizes.warehouses"), ["puzzle1"] ),     # If none given, use puzzle1 warehouse.  This parameter shouldn't be left to default, really...
            coalesce( int( coalesce( m.get_param("prizes.min-quality"), 1 ) ), 1 ),        # If none given, assume 1
            coalesce( int( coalesce( m.get_param("prizes.max-quality"), 1 ) ), 1 ),        # If none given, also assume 1.  Lousy items!
            coalesce( m.get_param("prizes.required-item-names"), [] )       # Assume no required items
        )

        # Do we have to add any required item?
        for item_name in required_item_names:

            # But if we already have it, don't list it...
            if (not universe.is_item_acquired(item_name)):

                # Validate that the item exists...
                item = universe.get_item_by_name(item_name)

                if (item):

                    # Add the item name as a prize option...
                    prize_item_names.append(item_name)


        # Fetch up to 3 (minus however many are required) item objects that the player will choose from...
        prize_item_names.extend(
            universe.fetch_n_virgin_item_names(
                3 - len(prize_item_names),
                min_quality = min_quality,
                max_quality = max_quality,
                warehouse_collection = warehouses
            )
        )


        if ( len(prize_item_names) == 0 ):
            log( "**Uh oh, no prize items!" )
            log( 5/0 )


        # Get the victory menu template
        template = self.fetch_xml_template("puzzle.menu.victory").add_parameters({
            "@x": xml_encode( "%d" % (SCREEN_WIDTH - (int( (SCREEN_WIDTH - PAUSE_MENU_WIDTH) / 2 ))) ),
            "@y": xml_encode( "%d" % PAUSE_MENU_Y ),
            "@width": xml_encode( "%d" % (int(PAUSE_MENU_WIDTH) / 2) ),
            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT ),
            "@overview": xml_encode( "%s" % localization_controller.translate( universe.get_active_map().get_param("overview") ) ),
            "@map-title": xml_encode( universe.get_map_title( universe.get_active_map().name ) )
        })

        # Compile template before we inject the various prize options...
        root = template.compile_layout_by_id("layout", control_center)


        logn("prize-item-candidates", prize_item_names)

        # Continuing, let's add an entry for each prize available...
        for name in prize_item_names:

            # Handle to the item itself
            item = universe.get_item_by_name(name)


            # Fetch the template for this prize option
            template = self.fetch_xml_template("puzzle.menu.prizes.insert").add_parameters({
                "@item-name": xml_encode( item.name ),
                "@item-title": xml_encode( item.title ),
                "@item-advertisement": xml_encode( localization_controller.translate( item.description ) )
            })

            # Compile template for this prize option
            node = template.compile_node_by_id("insert")
            logn( "prize-item-candidates-insert", node.compile_xml_string() )

            # Insert into the options group
            root.find_node_by_id("ext.prizes").add_node(node)
            #print root.find_node_by_id("ext.prizes").nodes
            #print root.compile_xml_string()
        #print root.compile_xml_string()


        # Now we can create the widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("puzzle-victory")


        # Position the widget sliding in from the right
        widget.slide(DIR_RIGHT, percent = 1.0, animated = False)

        # Then slide it into its default position
        widget.slide(None)


        # Position page 1 to slide in from the right
        widget.slide(DIR_RIGHT, percent = 1.0, animated = False)

        # Now have it slide into its default position
        widget.slide(None)


        # Add the page!
        self.add_widget_via_event(widget, event)

        # Return events
        return results


    # Show the "are you sure you want that prize?" page
    def handle_show_confirm_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Get a handle to the actual item...
        item = universe.get_item_by_name( params["item-name"] )


        # Get the "confirm selection" template
        template = self.fetch_xml_template("puzzle.menu.prize.confirm").add_parameters({
            "@x": xml_encode( "%d" % (SCREEN_WIDTH - (int( (SCREEN_WIDTH - PAUSE_MENU_WIDTH) / 2 ))) ),
            "@y": xml_encode( "%d" % PAUSE_MENU_Y ),
            "@width": xml_encode( "%d" % (int(PAUSE_MENU_WIDTH) / 2) ),
            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT ),
            "@item-name": xml_encode( params["item-name"] )
        })

        # Define environment_variables
        environment_variables = {
            "@item-title": xml_encode( item.title ),
            "@overworld-title": xml_encode( universe.get_session_variable("core.overworld-title").get_value() )
        }

        # Compile template
        root = template.compile_node_by_id("layout")


        # Get page 1, the selection menu
        page1 = self.get_widget_by_id("puzzle-victory")

        # Slide and hide
        page1.slide(DIR_LEFT, percent = 1.0)
        page1.hide()


        # Create page 2 widget
        page2 = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        # Translate environment_variables
        page2.translate_environment_variables(environment_variables)

        page2.set_id("confirm-selection")


        # Position page 2 to slide in from the right (with a little padding)
        page2.slide(DIR_RIGHT, percent = 1.1, animated = False)

        # Now have it slide into its default position
        page2.slide(None)


        # Add the new page!
        self.add_widget_via_event(page2, event, exclusive = False)

        # Return events
        return results


    # Hide the confirm page (select a different prize)
    def handle_hide_confirm_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Get the 2 pages
        (page1, page2) = (
            self.get_widget_by_id("puzzle-victory"),
            self.get_widget_by_id("confirm-selection")
        )


        # Slide page 2 off to the right, while hiding it...
        page2.slide(DIR_RIGHT, percent = 1.0)
        page2.hide(
            on_complete = "previous-page"
        )

        # Restore page 1 to its default location, while restoring it to view...
        page1.slide(None)
        page1.show()

        # Return events
        return results


    # Take an item (confirmed)
    def handle_take_item_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the window controller
        window_controller = control_center.get_window_controller()

        # Handle
        localization_controller = control_center.get_localization_controller()


        # Acquire the newn item by its name
        universe.acquire_item_by_name( params["item-name"] )

        # Post a newsfeeder update confirming item acquisition
        window_controller.get_newsfeeder().post({
            "type": NEWS_ITEM_NEW,
            "title": localization_controller.get_label("new-item-acquired:header"),
            "content": universe.get_item_by_name( params["item-name"] ).get_title()
        })


        # We'll slide page 2 away and hide it
        page2 = self.get_widget_by_id("confirm-selection")


        # Slide and hide, resetting the entire menu when done (removing all pages)
        page2.slide(DIR_RIGHT, percent = 1.0)

        page2.hide(
            on_complete = "reset"
        )


        # Hook into the window controller
        window_controller.hook(self)

        # App level fade
        window_controller.fade_out(
            on_complete = "fwd:finish:take-item"
        )

        # Return events
        return results


    # Take item cleanup, post-fade
    def handle_fwd_finish_take_item_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Get the active map
        m = universe.get_active_map()

        # Check for an oncomplete script (perhaps the game reacts in some way to which item you selected, etc.)
        if ( m.does_script_exist("oncomplete") ):

            # Run that script; execute all of its events
            m.run_script(
                name = "oncomplete",
                control_center = control_center,
                universe = universe,
                execute_all = True
            )


        # Lastly, let's undo the map transition (returning to the overworld).  Don't save the memory, as this is a puzzle map.
        universe.undo_last_map_transition(control_center = control_center, save_memory = False)


        # Un-pause-lock the menu controller
        control_center.get_menu_controller().configure({
            "pause-locked": False
        })

        # Abort splash
        control_center.get_splash_controller().abort()


        # Fetch the window controller;
        window_controller = control_center.get_window_controller()

        # Unhook from window controller
        window_controller.unhook(self)


        # App fade back in as we return to the overworld
        window_controller.fade_in()

        # Resume gameplay
        universe.unpause()


        # Autosave to record puzzle/challenge room completion
        universe.commit_autosave(control_center, universe)


        # Trash this menu
        self.set_status(STATUS_INACTIVE)


        # Return events
        return results
