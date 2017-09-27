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


class ShopMenu(Menu):

    def __init__(self):

        Menu.__init__(self)

        # Assume all shop menus come from already-lightboxed dialogues.
        self.lightbox_controller.set_interval( self.lightbox_controller.get_target() )


        # We're going to keep a handle to the seller so that we can
        # remove items from their inventory after a purchase...
        self.vendor = None#seller


        # Shop title (e.g. "Bob's Fine Items")
        self.title = "Shoppe"

        # Salutation (e.g. "Look at these great items")
        self.message = "Take a look at my inventory."


        # Before we begin populating the shop menu, we'll first
        # make sure the NPC seller stocks any specified "required" items...
        self.required_item_names = []


        # Track item quality threshholds (low and high)
        self.min_item_quality = 0
        self.max_item_quality = 0

        # Items in stock at any given time
        self.max_items_stocked = 1

        # Number of times the vendor can restock
        self.max_item_reloads = 1


        # Track whether this is the first build or a refresh
        self.first_build = True


        # Fire build event
        self.fire_event("build")


    def handle_event(self, event, control_center, universe):#params, user_input, network_controller, universe, active_map, session, widget_dispatcher, text_renderer, save_controller, refresh = False):

        # Events that result from event handling
        results = EventQueue()


        # Convenience
        (action, params) = (
            event.get_action(),
            event.get_params()
        )


        # Build root menu
        if ( action == "build" ):

            results.append(
                self.handle_build_event(event, control_center, universe)
            )


        # Select an item, get confirmation...
        elif ( action == "show:confirm-purchase" ):

            results.append(
                self.handle_show_confirm_purchase_event(event, control_center, universe)
            )


        # Commit an item purchase
        elif ( action == "game:buy-item" ):

            results.append(
                self.handle_shop_buy_item_event(event, control_center, universe)
            )


        # Go to the previous page (e.g. close buy item confirm dialog)
        elif ( action == "back" ):

            results.append(
                self.handle_back_event(event, control_center, universe)
            )


        # Finalize a "back" call
        elif ( action == "previous-page" ):

            # Let's just go back one page
            self.page_back(1)


        # Leave shop, resume game
        elif ( action == "resume-game" ):

            results.append(
                self.handle_resume_game_event(event, control_center, universe)
            )


        # Restore the universe to active game state, set this very menu to inactive
        elif ( action == "kill" ):

            results.append(
                self.handle_kill_event(event, control_center, universe)
            )


        # Return events
        return results


    # Configure the shop menu (more options than your typical menu, we need to define many parameters)
    def configure(self, options):

        # Common menu configuration
        self.__std_configure__(options)


        if ( "vendor" in options ):
            self.vendor = options["vendor"]

        if ( "title" in options ):
            self.title = options["title"]

        if ( "message" in options ):
            self.message = options["message"]

        if ( "required-item-names" in options ):
            self.required_item_names.extend( options["required-item-names"] )#.split(";") )

        if ( "min-quality" in options ):
            self.min_item_quality = int( options["min-quality"] )

        if ( "max-quality" in options ):
            self.max_item_quality = int( options["max-quality"] )

        if ( "max-items" in options ):
            self.max_items_stocked = int( options["max-items"] )

        if ( "max-reloads" in options ):
            self.max_item_reloads = int( options["max-reloads"] )


        # For chaining
        return self


    # Build the shop menu
    def handle_build_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Pause the game so that we can shop, if this is the first build...
        if (self.first_build):

            # Pause
            universe.pause()

        # Call in the pause splash
        control_center.get_splash_controller().set_mode(SPLASH_MODE_GREYSCALE_ANIMATED)


        # Before populating the vendor's inventory (or re-populating),
        # clear it of any items the player has acquired since last shopping with this vendor...
        self.vendor.remove_erstwhile_acquired_items_from_inventory(universe)


        # Populate inventory for this shoppe's vendor...
        self.vendor.populate_vendor_inventory(
            min_quality = self.min_item_quality,#int( node.get_attribute("min-quality") ),
            max_quality = self.max_item_quality,#int( node.get_attribute("min-quality") ),
            required_item_names = self.required_item_names,
            max_items = self.max_items_stocked,#int( node.get_attribute("max-items") ),
            max_reloads = self.max_item_reloads,#int( node.get_attribute("max-reloads") ),
            universe = universe
        )


        # Scope
        root = None


        # Does the vendor have anything in stock?  Use this data
        # to determine which template we load...
        if ( self.vendor.get_vendor_inventory_count() == 0 ):

            # Fetch the "nothing in stock" template
            template = self.fetch_xml_template( "shop.directory", version = "out-of-items" ).add_parameters({
                "@x": xml_encode( "%d" % (SCREEN_WIDTH - (int( (SCREEN_WIDTH - PAUSE_MENU_WIDTH) / 2 ))) ),
                "@y": xml_encode( "%d" % PAUSE_MENU_Y ),
                "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
                "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT ),
                "@shop-title": xml_encode( self.title )
            })

            # Compile template
            root = template.compile_node_by_id("menu")


        # We have items to sell...
        else:

            # Fetch the "shopping directory" template
            template = self.fetch_xml_template( "shop.directory", version = "default" ).add_parameters({
                "@x": xml_encode( "%d" % (SCREEN_WIDTH - (int( (SCREEN_WIDTH - PAUSE_MENU_WIDTH) / 2 ))) ),
                "@y": xml_encode( "%d" % PAUSE_MENU_Y ),
                "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
                "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT ),
                "@shop-title": xml_encode( self.title ),
                "@salutation": xml_encode( self.message )
            })

            # Compile template
            root = template.compile_node_by_id("menu")


            # Now we'll add an entry for each available item...
            for item_name in self.vendor.get_vendor_inventory_item_names():

                # Grab handle
                item = universe.get_item_by_name(item_name)

                # Validate
                if (item):

                    # How much money do we currently have?
                    money = int( universe.get_session_variable("core.gold.wallet").get_value() )

                    # Template version for this item depends on whether we can afford it...
                    template_version = ( "affordable" if (money >= item.cost) else "unaffordable" )

                    # Fetch the appropriate template for an individual item
                    template = self.fetch_xml_template( "shop.directory.insert", version = template_version ).add_parameters({
                        "@item-name": xml_encode( item.name ),
                        "@item-title": xml_encode( item.title ),
                        "@item-cost": xml_encode( "%d" % item.cost ),
                        "@item-advertisement": xml_encode( item.description )
                    })

                    # Compile
                    node = template.compile_node_by_id("insert")

                    # Inject into inventory area...
                    root.find_node_by_id("ext.inventory").add_node(node)


        # Create widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("root")


        # We have definitely completed the first build now
        self.first_build = False


        # Add the new page
        self.add_widget_via_event(widget, event)

        # Return events
        return results


    # Show the "are you sure you wanna buy this?" page
    def handle_show_confirm_purchase_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Get a handle to the actual item...
        item = universe.get_item_by_name( params["item-name"] )

        # Validate
        if (item):

            # Fetch confirm purchase template
            template = self.fetch_xml_template("shop.buy.confirm").add_parameters({
                "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
                "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
                "@item-name": xml_encode( item.get_name() ),
                "@item-title": xml_encode( item.get_title() ),
                "@item-cost": xml_encode( "%d" % item.get_cost() )
            })

            # Compile template
            root = template.compile_node_by_id("menu")

            # Create widget
            widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

            widget.set_id("confirm-shop-purchase")

            # Add the new page
            self.add_widget_via_event(widget, event, exclusive = False)

        # Return events
        return results


    # Commit an item purchase
    def handle_shop_buy_item_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Get a reference to the item (for cost info, etc.)
        item = universe.get_item_by_name( params["item-name"] )


        # Acquire the item by its name
        universe.acquire_item_by_name( item.get_name() )

        # Post a newsfeeder notice
        control_center.get_window_controller().get_newsfeeder().post({
            "type": NEWS_ITEM_NEW,
            "title": control_center.get_localization_controller().get_label("new-item-purchased:header"),
            "content": item.get_title()
        })

        # Add a historical record
        universe.add_historical_record(
            "purchases",
            control_center.get_localization_controller().get_label(
                "purchased-m-from-n-for-g:message",
                {
                    "@m": item.get_title(),
                    "@n": self.vendor.nick,
                    "@g": item.get_cost()
                }
            )
            #"Bought [color=special]%s[/color] for [color=special]%s[/color] gold." % ( item.get_title(), item.get_cost() )
        )


        # Remove from seller's inventory
        self.vendor.remove_item_from_vendor_inventory( item.get_name() )

        # Increase sales count for vendor
        self.vendor.increase_sales_count(1)


        # Reduce player's wallet amount by the cost...
        universe.increment_session_variable(
            "core.gold.wallet",
            -1 * item.get_cost()
        )

        # Count as gold spent
        universe.increment_session_variable(
            "stats.gold-spent",
            item.get_cost()
        )


        # Execute the "wallet-changed" achievement hook
        universe.execute_achievement_hook( "wallet-changed", control_center )


        # Increase universe stats for items bought
        universe.get_session_variable("stats.items-bought").increment_value(1)

        # Execute the "bought-item" achievement hook
        universe.execute_achievement_hook( "bought-item", control_center )


        # Get the active map
        m = universe.get_active_map()


        # Check for a generic "onpurchase" script for the vendor
        m.run_script(
            "%s.onpurchase" % self.vendor.get_name(),
            control_center,
            universe,
            execute_all = True  # Try to loop entire script (?)
        )

        # Check for an onpurchase script (perhaps the game reacts in some way to an item you might have bought)
        m.run_script(
            name = "%s.onpurchase" % item.get_name(),
            control_center = control_center,
            universe = universe,
            execute_all = True
        )


        # Refresh UI
        self.refresh_pages(control_center, universe, curtailed_count = 1)


        # After rebuilding the UI, we will have restocked the NPC's inventory.
        # Thus, if the NPC has no inventory available, we have just bought their last item...
        if ( self.vendor.get_vendor_inventory_count() == 0 ):

            # Execute the "bought-all-items" achievement hook
            universe.execute_achievement_hook( "bought-all-items", control_center )


        # I'm going to set the cursor at "home" position for the shop
        self.get_widget_by_id("root").set_cursor_at_beginning()#finalize = True)

        # Return events
        return results


    # Go back a page (animated)
    def handle_back_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Get the active page
        page = self.get_active_page()

        # Validate
        if (page):

            # Dismiss the page
            page.hide(
                on_complete = "previous-page"
            )

        # Return events
        return results


    # Leave the shop and resume play
    def handle_resume_game_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Dismiss lightbox effect
        self.lightbox_controller.set_target(0)


        # Dismiss the splash controller, calling to resume game action once done...
        control_center.get_splash_controller().dismiss(
            on_complete = "game:unpause"
        )

        #hmenu.slide(DIR_LEFT, percent = 1.0)
        #row_menu.slide(DIR_RIGHT, percent = 1.0)

        # Resume game, killing shop menu when widget disappears
        self.get_widget_by_id("root").hide(
            on_complete = "kill"
        )

        # Return events
        return results


    # Kill event.  Set game status back to active when shopping is done.
    def handle_kill_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Done with the shop menu widget; trash it.
        self.set_status(STATUS_INACTIVE)


        # Return events
        return results
