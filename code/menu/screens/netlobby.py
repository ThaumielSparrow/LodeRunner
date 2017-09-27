import os
import sys

import math
import random

import time

from code.menu.menu import Menu

from code.tools.eventqueue import EventQueue

from code.tools.xml import XMLParser

from code.utils.common import coalesce, intersect, offset_rect, log, log2, xml_encode, xml_decode, translate_rgb_to_string

from code.constants.common import SCREEN_WIDTH, SCREEN_HEIGHT, PAUSE_MENU_X, PAUSE_MENU_Y, PAUSE_MENU_WIDTH, PAUSE_MENU_HEIGHT, MODE_GAME, TILE_WIDTH, TILE_HEIGHT, DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT, DEFAULT_PLAYER_COLORS, LAYER_FOREGROUND, LAYER_BACKGROUND

from code.constants.states import *
from code.constants.newsfeeder import *

from code.constants.network import *


class NetLobby(Menu):

    def __init__(self):

        Menu.__init__(self)


        # Track whether we're building or refreshing
        self.first_build = True

        # Fire build events
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


        # When the player changes their selection in the lobby options, we'll update
        # the "faq" type box off to the side...
        elif ( action == "options.change" ):

            results.append(
                self.handle_options_change_event(event, control_center, universe)
            )


        # Show the edit avatar menu
        elif ( action == "show:edit-avatar" ):

            results.append(
                self.handle_show_edit_avatar_event(event, control_center, universe)
            )


        # Hide the edit avatar menu
        elif ( action == "hide:edit-avatar" ):

            results.append(
                self.handle_hide_edit_avatar_event(event, control_center, universe)
            )


        # Show the keyboard for editing character name
        elif ( action == "show:edit-avatar.keyboard" ):

            results.append(
                self.handle_show_edit_avatar_keyboard_event(event, control_center, universe)
            )


        # Discard the keyboard for editing character name
        elif ( action == "hide:edit-avatar.keyboard" ):

            results.append(
                self.handle_hide_edit_avatar_keyboard_event(event, control_center, universe)
            )


        # Update the local player name (keyboard input)
        elif ( action == "net:change-name" ):

            results.append(
                self.handle_net_change_name_event(event, control_center, universe)
            )


        # Show a color picker for a given avatar property
        elif ( action == "show:edit-avatar.colorpicker" ):

            results.append(
                self.handle_show_edit_avatar_colorpicker_event(event, control_center, universe)
            )


        # Commit an avatar edit
        elif ( action == "net:update-avatar-property" ):

            results.append(
                self.handle_net_update_avatar_property_event(event, control_center, universe)
            )


        # Set ready / not ready status
        elif ( action == "net:update-ready-status" ):

            results.append(
                self.handle_net_update_ready_status_event(event, control_center, universe)
            )


        # Submit a vote to skip the current level
        elif ( action == "net:vote-to-skip" ):

            results.append(
                self.handle_net_vote_to_skip_event(event, control_center, universe)
            )


        # Begin the level (server only)
        elif ( action == "server:begin-play" ):

            results.append(
                self.handle_server_begin_play_event(event, control_center, universe)
            )


        # Begin the game (client only)
        elif ( action == "client:begin-play" ):

            results.append(
                self.handle_client_begin_play_event(event, control_center, universe)
            )


        # Transition to the next level
        elif ( action == "game:skip-level" ):

            results.append(
                self.handle_skip_level_event(event, control_center, universe)
            )


        # Commit skip level logic
        elif ( action == "finish:game:skip-level" ):

            results.append(
                self.handle_finish_skip_level_event(event, control_center, universe)
            )


        # Generic "back" event
        elif ( action == "back" ):

            results.append(
                self.handle_back_event(event, control_center, universe)
            )


        # Commit the "one page back" event
        elif ( action == "finish:back" ):

            results.append(
                self.handle_finish_back_event(event, control_center, universe)
            )


        elif ( action == "kill" ):

            results.append(
                self.handle_kill_event(event, control_center, universe)
            )


        # Return events
        return results


    def additional_processing(self, control_center, universe, debug = False):#user_input, raw_keyboard_input, network_controller, universe, active_map, session, widget_dispatcher, text_renderer, save_controller, debug = False):

        # Events from processing
        results = EventQueue()


        # Do we need to update the contents of the intro menu?  (Player ready / not ready, name change, etc.)
        if ( int( universe.get_session_variable("net.rebuild-intro-menu").get_value() ) == 1 ):

            """
            # Fetch curtail count
            curtailed_count = int( universe.get_session_variable("net.rebuild-intro-menu:curtailed-count").get_value() )
            # Disable flag
            universe.set_session_variable("net.rebuild-intro-menu", "0")
            # Reset curtailed count (default to 0 every time)
            universe.set_session_variable("net.rebuild-intro-menu:curtailed-count", "0")
            """


            # Disable flag
            universe.set_session_variable("net.rebuild-intro-menu", "0")
            

            # Refresh menu
            #self.populate_menus(network_controller, universe, session, widget_dispatcher)
            self.refresh_pages(control_center, universe)#user_input, network_controller, universe, active_map, session, widget_dispatcher, text_renderer, save_controller, curtailed_count = curtailed_count)


        # Grab the network controller
        network_controller = control_center.get_network_controller()


        # We're going to check for "start game now" logic, provided we don't have a local lock on the network controller.
        if ( not network_controller.is_local_locked() ):

            # During netplay, the server will check the status of the lobby.  When all players set ready,
            # the server will begin the game.  When enough players vote to skip the level, the server
            # will transition the lobby members to the next level.
            if ( network_controller.get_status() == NET_STATUS_SERVER ):

                # Enough votes to skip this level?
                if ( int( universe.get_session_variable("net.votes-to-skip").get_value() ) >= 2 ):

                    # Reset vote counter
                    universe.set_session_variable("net.votes-to-skip", "0")

                    # Fire skip level event
                    self.fire_event("game:skip-level")


                # We only want to do all of this of the game hasn't officially begun yet...
                elif ( int( universe.get_session_variable("net.countdown-in-progress").get_value() ) == 0 ):

                    # Count the number of players that have joined
                    player_count = sum( (int( universe.get_session_variable("net.player%d.joined" % e).get_value() ) == 1) for e in range(1, 1 + int( universe.get_session_variable("net.player-limit").get_value() )) )

                    #print "player count = %d" % player_count

                    # We'll only check for "all ready" status if we have >= 2 players...
                    if (player_count >= 2):

                        # Is everyone ready to go?
                        all_ready = all( ( int( universe.get_session_variable("net.player%d.ready" % e).get_value() ) == 1 ) for e in range(1, 1 + int( universe.get_session_variable("net.player-limit").get_value() )) if ( universe.get_session_variable("net.player%d.joined" % e).get_value() == "1" ) )
                        #all_ready = any( ( int( universe.get_session_variable("net.player%d.ready" % e).get_value() ) == 1 ) for e in range(1, 1 + int( universe.get_session_variable("net.player-limit").get_value() )) if ( universe.get_session_variable("net.player%d.joined" % e).get_value() == "1" ) )

                        #print "\tready count = %d" % sum( ( int( universe.get_session_variable("net.player%d.ready" % e).get_value() ) == 1 ) for e in range(1, int( universe.get_session_variable("net.player-limit").get_value() )) if ( universe.get_session_variable("net.player%d.joined" % e).get_value() == "1" ) )

                        # If so, then let's broadcast the news and dismiss the pause menu...
                        if (all_ready):

                            # Track that we're officially beginning the level; we don't need to check "all ready" any more...
                            universe.set_session_variable("net.countdown-in-progress", "1")

                            # Run the map's onready script for the server
                            universe.get_active_map().run_script("onready", control_center, universe)


                            # Run universe's coop ready script
                            universe.run_script("global.coop.ready", control_center, execute_all = True)

                            # Run the map's coop.ready script
                            universe.get_active_map().run_script("coop.ready", control_center, universe, execute_all = True)


                            # Hide the net lobby, killing it off once it's gone
                            self.get_widget_by_id("net-lobby").hide(
                                on_complete = "kill"
                            )


                            # Dismiss pause splash, commencing gameplay when done
                            control_center.get_splash_controller().dismiss(
                                on_complete = "game:unpause"
                            )


                            # Tell each client to begin netplay
                            network_controller.send_begin_game(control_center, universe)

            # The client, on the other hand, should regularly check to see if the universe has begun.
            # When so, it should dismiss the lobby menu and begin play, if it hasn't yet done so.
            elif ( network_controller.get_status() == NET_STATUS_CLIENT ):

                # Fetch lobby page
                widget = self.get_widget_by_id("net-lobby")

                # If we haven't yet dismissed it, then we'll want to check to see if we should...
                if ( widget.alpha_controller.get_target() > 0 ):

                    # Is the game underway?  All players set ready?
                    if ( universe.get_session_variable("net.game-in-progress").get_value() == "1" ):

                        # Hide the lobby, killing it when it's gone
                        widget.hide(
                            on_complete = "kill"
                        )

                        # Dismiss pause splash.  Begin the game once it's gone...
                        control_center.get_splash_controller().dismiss(
                            on_complete = "game:unpause"
                        )


                        # Run the onready script, it's time to go!
                        universe.get_active_map().run_script("onready", control_center, universe)


        # Return events
        return results


    # Build the net lobby
    def handle_build_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Pause game action as we enter the lobby, if this is the first build
        if (self.first_build):

            # Pause
            universe.pause()


        # Local player id?
        player_id = int( universe.get_session_variable("core.player-id").get_value() )


        """ Create slots wrapper """
        # Which template do we want?
        template_version = ( "ready" if ( universe.get_session_variable("net.player%d.ready" % player_id).get_value() == "1" ) else "not-ready" )


        # Assume
        overview_text = control_center.get_localization_controller().get_label("default-coop-overview")


        # Check for current map's overview parameter
        p = universe.get_active_map().get_param("overview")

        # Check for explicit overview
        if (p != None):

            # Overwrite
            overview_text = "%s" % p


        # Fetch the lobby slots template
        template = self.fetch_xml_template( "net.lobby", version = template_version ).add_parameters({
            "@x": xml_encode( "%d" % PAUSE_MENU_X ),
            "@y": xml_encode( "%d" % PAUSE_MENU_Y ),
            "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
            "@votes": xml_encode( "%s" % universe.get_session_variable("net.votes-to-skip").get_value() ),
            "@level-title": xml_encode( "%s" % universe.get_map_data( universe.get_active_map().get_name() ).get_title() ),
            "@level-overview": xml_encode( "%s" % overview_text )
        })

        # Compile template
        root = template.compile_node_by_id("menu")


        """ Add player slots """
        # Add a lobby profile pic for each player / open slot
        for i in range( 0, int( universe.get_session_variable("net.player-limit").get_value() ) ):

            log( "processing profile card for '%d'" % i )

            # Fetch profile card template
            template = self.fetch_xml_template("net.coop.intro.slots.player").add_parameters({
                "@param1": xml_encode( "player %d" % (i + 1) ),
                "@player-name":   xml_encode( universe.get_net_player_name_by_player_id( (1 + i), control_center.get_network_controller() ) ),
                "@player-status": xml_encode( universe.get_net_player_status_by_player_id( (1 + i), control_center.get_network_controller() ) ),
                "@map-name": xml_encode( "coop.loop.%d" % random.randint(1, 2) ),
                "@avatar-data": xml_encode( universe.get_session_variable("net.player%d.avatar.colors" % (1 + i)).get_value() )
            })

            # Compile this insert's node
            node = template.compile_node_by_id("insert")

            # Inject into the appropriate group
            root.find_node_by_id("ext.player-slots").add_node(node)


        # Build widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("net-lobby")


        # Position page 1 to slide in from the right
        widget.slide(DIR_RIGHT, percent = 1.0, animated = False)

        # Now have it slide into its default position
        widget.slide(None)


        # Add the new page
        self.add_widget_via_event(widget, event)


        # First build is definitely complete, it is wasn't already...
        self.first_build = False


        # Hack to ensure proper default option highlight
        widget.find_widget_by_id("lobby-options").focus()#move_cursor(0, 0)

        # Raise an "option change" event (emulate it) to default to the first faq panel
        self.fire_event(
            "options.change",
            {
                "widget": widget.find_widget_by_id("lobby-options") # This event requires a reference to the options RowMenu
            }
        )


        # Clear any existing "so and so has died" message
        control_center.get_network_controller().get_net_console().remove_lines_by_class("player-died")


        # Return events
        return results


    # Change a selected option in the lobby menu (toggle visible help tip on the side)
    def handle_options_change_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # First, we need to fetch the rowmenu that triggered this event
        row_menu = params["widget"]

        # Which faq do we want to show?
        rel = row_menu.get_active_widget().rel


        # Fetch the container that holds all of the faq items
        container = self.get_widget_by_id("net-lobby").get_widget_by_id("faqs")

        # Loop through widgets
        for widget in container.get_widgets():

            # Is this the one we want to show?
            if ( widget.get_id() == rel ):

                # Make it visible
                widget.configure({
                    "display": "constant"
                })

            # Nope; let's hide it!
            else:

                # Make it visible
                widget.configure({
                    "display": "hidden"
                })

        # Return events
        return results


    # Show the edit avatar page (slide it in)
    def handle_show_edit_avatar_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # We'll need the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Local player id
        player_id = int( universe.get_session_variable("core.player-id").get_value() )


        # Get the template for the avatar edit menu
        template = self.fetch_xml_template("net.lobby.avatar.edit")


        # First, let's put together the params we'll be sending to the template.
        # We'll have to run more logic than usual to compute the params.
        template_params = {
            "@x": xml_encode( "%d" % PAUSE_MENU_X ),
            "@y": xml_encode( "%d" % PAUSE_MENU_Y ),
            "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH / 2) ),
            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT ),
            "@player-name": xml_encode( universe.get_session_variable("net.player%d.nick" % player_id).get_value() )
        }


        # Populate defaults first
        for key in DEFAULT_PLAYER_COLORS:

            # Hard-coded prefix
            template_params["@color-%s" % key] = xml_encode( translate_rgb_to_string( DEFAULT_PLAYER_COLORS[key] ) )


        # Fetch the existing semicolon-separated values for the local player
        ssv = universe.get_session_variable("net.player%d.avatar.colors" % player_id).get_value()

        # Separate existing data
        pieces = ssv.split(";")

        # Loop existing properties, update if/a
        for piece in pieces:

            # Validate format
            if ( piece.find("=") >= 0 ):

                # Key, value
                (key, custom_value) = piece.split("=", 1)


                # Update or keep?
                if ( "@color-%s" % key in template_params):

                    # Update
                    template_params["@color-%s" % key] = custom_value

        # Add params...
        template.add_parameters(template_params)

        # Compile template
        root = template.compile_node_by_id("menu")

        # Create widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("net-edit-avatar")


        # Configure the new page to slide in from the left
        widget.slide(DIR_LEFT, percent = 1.1, animated = False)

        # Now set it to slide into place
        widget.slide(None)


        # Fetch page 1 (lobby)
        page1 = self.get_widget_by_id("net-lobby")

        # Slide it to the side
        page1.slide(DIR_RIGHT, amount = (widget.get_width() + 20))


        # Lastly, add the new page
        self.add_widget_via_event(widget, event, exclusive = False)

        # Return events
        return results


    # Hide the edit avatar page (slide it away)
    def handle_hide_edit_avatar_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the avatar page
        widget = self.get_widget_by_id("net-edit-avatar")

        # Slide and hide
        widget.slide(DIR_LEFT, percent = 1.0)
        widget.hide()


        # Fetch page 1 (lobby)
        page1 = self.get_widget_by_id("net-lobby")

        # Slide it back into prominence
        page1.slide(
            None,
            on_complete = "back"
        )

        # Return events
        return results


    # Show the keyboard for editing multiplayer name
    def handle_show_edit_avatar_keyboard_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # We need the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Local player id
        player_id = int( universe.get_session_variable("core.player-id").get_value() )


        # Fetch the keyboard template
        template = self.fetch_xml_template("net.lobby.avatar.edit.keyboard").add_parameters({
            "@x": xml_encode( "%d" % int(SCREEN_WIDTH / 2) ),
            "@y": xml_encode( "%d" % (SCREEN_HEIGHT - PAUSE_MENU_Y) ),
            "@width": xml_encode( "%d" % PAUSE_MENU_WIDTH ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
            "@prompt": xml_encode( "%s" % control_center.get_localization_controller().get_label("enter-name:prompt") ),
            "@default": xml_encode( universe.get_session_variable("net.player%d.nick" % player_id).get_value() )
        })

        # Compile template
        root = template.compile_node_by_id("keyboard")

        # Build the widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("edit-avatar.keyboard")


        # Position the widget to appear from the bottom
        widget.slide(DIR_DOWN, amount = 200, animated = False)

        # Then it will slide into default position
        widget.slide(None)


        # Add new page!
        self.add_widget_via_event(widget, event, exclusive = False)

        # Return events
        return results


    # Hide the keyboard for editing multiplayer name
    def handle_hide_edit_avatar_keyboard_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Grab widget
        widget = self.get_widget_by_id("edit-avatar.keyboard")

        # Slide and hide
        widget.slide(DIR_DOWN, amount = SCREEN_HEIGHT)
        widget.hide(
            on_complete = "back"
        )

        # Return events
        return results


    # Commit a name change in multiplayer
    def handle_net_change_name_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Local player id
        player_id = int( universe.get_session_variable("core.player-id").get_value() )


        # Fetch the calling widget (keyboard)
        widget = params["widget"]

        # Check new name
        name = widget.get_value()

        # Validate name?
        if (True):

            # Update local session variable
            universe.set_session_variable("net.player%d.nick" % player_id, name)

            # Sync new nick to other players
            control_center.get_network_controller().send_sync_local_player(control_center, universe)


            # Save the updated netplay preferences
            control_center.save_netplay_preferences(universe)


            # Update UI
            self.refresh_pages(control_center, universe, curtailed_count = 1)

            # Flag to rebuild lobby menu
            #universe.set_session_variable("net.rebuild-intro-menu", "1")
            #universe.set_session_variable("net.rebuild-intro-menu:curtailed-count", "1")


        # Explicitly slide and hide the keyboard
        widget.slide(DIR_DOWN, amount = SCREEN_HEIGHT)
        widget.hide(
            on_complete = "back"
        )

        # Return events
        return results


    # Show the colorpicker
    def handle_show_edit_avatar_colorpicker_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Get the "color picker" popup menu template
        template = self.fetch_xml_template("net.lobby.avatar.edit.colorpicker").add_parameters({
            "@x": xml_encode( "%d" % int(SCREEN_WIDTH / 2) ),
            "@y": xml_encode( "%d" % int(SCREEN_HEIGHT / 2) ),
            "@width": xml_encode( "%d" % int(PAUSE_MENU_WIDTH) ),
            "@height": xml_encode( "%d" % PAUSE_MENU_HEIGHT ),
            "@property": xml_encode( params["property"] )
        })

        # Compile template
        root = template.compile_node_by_id("menu")

        # Build the widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("edit-avatar.colorpicker")

        # Add new page!
        self.add_widget_via_event(widget, event, exclusive = False)

        # Return events
        return results


    # Update an avatar property
    def handle_net_update_avatar_property_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Local player id
        player_id = int( universe.get_session_variable("core.player-id").get_value() )


        # Which property?
        prop = params["property"]

        # New value?
        new_value = params["value"]


        # Fetch the existing semicolon-separated values for the local player
        ssv = universe.get_session_variable("net.player%d.avatar.colors" % player_id).get_value()

        # We'll rebuild it with the new color data
        ssv_new = ""


        # Track whether we're updating an existing value or creating a new value
        updated_existing_value = False


        # Separate existing data
        pieces = ssv.split(";")

        # Loop existing properties, update if/a
        for piece in pieces:

            # Validate format
            if ( piece.find("=") >= 0 ):

                # Key, value
                (key, old_value) = piece.split("=", 1)


                # Update or keep?
                if (key == prop):

                    # Append
                    ssv_new += "%s=%s;" % (key, new_value)

                    # Flag
                    updated_existing_value = True

                # Keep...
                else:

                    # Append
                    ssv_new += "%s=%s;" % (key, old_value)


        # If we didn't update an existing value, then we'll want to add the updated property at the end
        if (not updated_existing_value):

            ssv_new += "%s=%s;" % (prop, new_value)


        # Update the session data for this player
        universe.set_session_variable("net.player%d.avatar.colors" % player_id, ssv_new)


        # Save the updated netplay preferences
        control_center.save_netplay_preferences(universe)


        # Flag a refresh of the net intro menu (colors have changed)
        #universe.set_session_variable("net.rebuild-intro-menu", "1")

        # Update UI
        self.refresh_pages(control_center, universe, curtailed_count = 1)


        # Sync the avatar update to all other players
        control_center.get_network_controller().send_sync_local_player(control_center, universe)

        # Return events
        return results


    # Update ready status in the multiplayer lobby
    def handle_net_update_ready_status_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # What's the local player ID?
        player_id = int( universe.get_session_variable("core.player-id").get_value() )


        # Update local session variable
        universe.set_session_variable("net.player%d.ready" % player_id, params["status"])

        # Sync
        control_center.get_network_controller().send_sync_local_player(control_center, universe)


        # Flag that we should rebuild the intro menu to reflect the status change
        #universe.set_session_variable("net.rebuild-intro-menu", "1")

        # Refresh UI
        self.refresh_pages(control_center, universe)

        # Return events
        return results


    # Vote to skip a level (you can only do this once, naturally)
    def handle_net_vote_to_skip_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the network controller
        network_controller = control_center.get_network_controller()


        # Make sure we haven't already voted to skip
        if ( int( universe.get_session_variable("net.already-voted-to-skip").get_value() ) == 0 ):

            # Server tallies local vote immediately
            if ( network_controller.get_status() == NET_STATUS_SERVER ):

                # +1
                universe.increment_session_variable("net.votes-to-skip", 1)

                # Flag a rebuild of the lobby menu (update vote counter)
                universe.set_session_variable("net.rebuild-intro-menu", "1")


            # Flag that we voted
            universe.set_session_variable("net.already-voted-to-skip", "1")


            # Share vote
            network_controller.send_vote_to_skip(control_center, universe)

        # Return events
        return results


    # As the server, call for the game to begin
    def handle_server_begin_play_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Trash this menu
        self.set_status(STATUS_INACTIVE)

        # (?) Begin gameplay
        #universe.unpause()

        # Return events
        return results


    # As the client, receive a begin play event
    def handle_client_begin_play_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Simply trash the menu
        self.set_status(STATUS_INACTIVE)

        # Return events
        return results


    # Begin skipping a level
    def handle_skip_level_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch the window controller;
        window_controller = control_center.get_window_controller()

        # and the network controller
        network_controller = control_center.get_network_controller()


        # Hook into window controller
        window_controller.hook(self)

        # App-level fade, triggering skip logic on complete
        window_controller.fade_out(
            on_complete = "finish:game:skip-level"
        )


        # Fetch the active map
        m = universe.get_active_map()

        # Query the next map's name
        next_map_name = m.get_param("next-map")

        
        # Send transition command to all clients
        network_controller.send_transition_to_map(next_map_name, control_center, universe)

        # Return events
        return results


    # Finish skip level logic, post-fade
    def handle_finish_skip_level_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch window controller;
        window_controller = control_center.get_window_controller()

        # and the splash controller
        splash_controller = control_center.get_splash_controller()


        # Unhook
        window_controller.unhook(self)


        # Fetch the active map
        m = universe.get_active_map()

        # Query the next map's name
        next_map_name = m.get_param("next-map")


        # Transition the local map
        universe.activate_map_on_layer_by_name(next_map_name, LAYER_FOREGROUND, control_center = control_center, ignore_adjacent_maps = True)

        # Immediately center the camera
        universe.get_active_map().center_camera_immediately = True


        # Server will update the web server with the new map name.
        control_center.get_network_controller().web_update_current_level(control_center, universe)


        # When we activated the new map, we created a lobby, which "paused" the game.
        # We were just in a pause lobby, though, so we need to decrement the pause counter here.
        universe.unpause(force = True).pause() # We'll be at pause count 1 now


        # Invalidate the splash screen
        splash_controller.invalidate()

        # Add-level fade back in as we move to the next level
        window_controller.fade_in()

        # Return events
        return results


    # Go back
    def handle_back_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # If we supplied a page count in this "back" call,
        # then the active page will use an attribute to track
        # that parameter through the event chain.
        if ( "pages" in params ):

            # Track in active page
            self.widgets[-1].set_attribute("-pages", params["pages"])

        # Otherwise, we'll default to 1 page back, tracking the same manner
        else:

            # Track in active page
            self.widgets[-1].set_attribute("-pages", "1")


        # See if we should slide away as we discard the active page
        if ( "slide" in params ):

            # Should we slide everything back to the right?
            if ( params["slide"] == "right" ):

                # Disable exclusive status for top page, assuming it is exclusive in the first place...
                self.widgets[-1].set_attribute("exclusive", "no")


                # Slide and hide the top page
                self.widgets[-1].slide(DIR_RIGHT, percent = 1.0)

                # Hide
                self.widgets[-1].hide(
                    on_complete = "xunslide-previous-page"
                )


                # If we have a widget below...
                if ( len(self.widgets) > 1 ):

                    # ... then let's unslide it and show it
                    self.widgets[-2].slide(None)
                    #self.widgets[-2].show()


        else:

            self.widgets[-1].hide(
                on_complete = "finish:back"
            )

        # Return events
        return results


    # Finish back logic (after widget fade)
    def handle_finish_back_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # The page that fired this event tracked the "page count"
        # via an attribute.
        pages = int( self.widgets[-1].get_attribute("-pages") )

        # Page back as specified
        self.page_back(pages)


        # Only do this if we're back to the original widget (lobby widget) (what a hack!)
        if ( len(self.widgets) == 1 ):

            # Find net lobby widget
            widget = self.get_widget_by_id("net-lobby")

            # Validate
            if (widget):

                # Hack to ensure we're highlighting the "edit avatar"
                # option on the lobby menu.
                widget.find_widget_by_id("lobby-options").focus()#move_cursor(0, 0)


        # Return events
        return results


    # Kill the net lobby
    def handle_kill_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Trash this menu
        self.set_status(STATUS_INACTIVE)


        # Return events
        return results
