import os

import math
import random

import time

from code.menu.menu import Menu

from code.tools.eventqueue import EventQueue

from code.tools.xml import XMLParser

from code.utils.common import coalesce, intersect, offset_rect, log, log2, xml_encode, xml_decode, translate_rgb_to_string

from code.constants.common import SCREEN_WIDTH, SCREEN_HEIGHT, PAUSE_MENU_X, PAUSE_MENU_Y, PAUSE_MENU_WIDTH, PAUSE_MENU_HEIGHT, MODE_GAME, TILE_WIDTH, TILE_HEIGHT, DIR_UP, DIR_RIGHT, DIR_DOWN, DIR_LEFT, LAYER_FOREGROUND

from code.constants.menus import OVERWORLD_DEATH_MENU_WIDTH

from code.constants.states import STATUS_ACTIVE, STATUS_INACTIVE
from code.constants.death import *

from code.constants.newsfeeder import *


class OverworldDeathMenu(Menu):

    def __init__(self):

        #RowMenu.__init__(self, x = 0, y = 0, width = 200, height = SCREEN_HEIGHT, global_frame = True, shrinkwrap = True)
        Menu.__init__(self)


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
        if (action == "build"):

            results.append(
                self.handle_build_event(event, control_center, universe)
            )


        # Revert to last checkpoint
        elif (action == "last-autosave"):

            results.append(
                self.handle_last_autosave_event(event, control_center, universe)
            )


        # Retry puzzle - commit
        elif (action == "fwd.finish:last-autosave"):

            results.append(
                self.handle_fwd_finish_last_autosave_event(event, control_center, universe)
            )


        # Spawn in last visited town area
        elif ( action == "last-town" ):

            results.append(
                self.handle_last_town_event(event, control_center, universe)
            )


        # Spawn in last town - commit
        elif ( action == "fwd.finish:last-town" ):

            results.append(
                self.handle_fwd_finish_last_town_event(event, control_center, universe)
            )


        # Discard this menu
        elif ( action == "kill" ):

            results.append(
                self.handle_kill_event(event, control_center, universe)
            )


        # Return events
        return results

        """
        if ( params["do"] == "last-autosave:commit" ):

            # Fetch the window controller;
            window_controller = control_center.get_window_controller()

            # and the save controller
            save_controller = control_center.get_save_controller()


            # Set this Menu widget to inactive, ready for cleanup
            self.status = STATUS_INACTIVE


            # Load the autosave...
            save_controller.load_from_folder(
                os.path.join( universe.get_working_save_data_path(), "autosave1" ),
                control_center,
                universe
            )

            # Transition to the new map.  Don't save memory for the current map.
            universe.transition_to_map(
                universe.get_session_variable("app.active-map-name").get_value(),
                save_memory = False,
                control_center = control_center
            )


            # App-level fade back in to show the game again
            window_controller.fade_in()


        elif ( params["do"] == "last-town" ):

            universe.transition_to_map( universe.get_session_variable("core.last-safe-zone.map").get_value(), waypoint_to = "safe-spawn", control_center = control_center )
        """


    # Build the game over menu
    def handle_build_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Create empty hash to hold causes of death
        taunts_by_cause = {
        }

        # Calculate path to file that holds taunt data
        path = os.path.join("data", "xml", "death.taunts.xml")

        # Validate path
        if ( os.path.exists(path) ):

            # Create xml node
            node = XMLParser().create_node_from_file(path)

            # Validate xml compiled
            if (node):

                # Get main node
                node = node.find_node_by_tag("causes")

                # Loop categories
                for ref_cause in node.get_nodes_by_tag("*"):

                    # Get the tag type (e.g. "deadly-tile")
                    s = ref_cause.tag_type

                    # Validate that we can translate this string to a cause of death
                    if (s in DEATH_TYPE_LOOKUPS):

                        # Translate string to int that we will hash by
                        key = DEATH_TYPE_LOOKUPS[s]

                        # Init list for this hash key, if/n
                        if ( not (key in taunts_by_cause) ):

                            # Init
                            taunts_by_cause[key] = []

                        # Loop taunts in this category
                        for ref_taunt in ref_cause.get_nodes_by_tag("string"):

                            # Add taunt
                            taunts_by_cause[key].append( ref_taunt.innerText )


        # Default, generic taunt...
        random_taunt = "You died in the overworld of [color=special]Lelandria[/color] in a very mysterious fashion."


        # How did the player die?
        cause = int( universe.get_session_variable("core.player1.cause-of-death").get_value() )


        # Can we find a taunt for that cause?
        if (cause in taunts_by_cause):

            # Does at least one taunt exist?
            if ( len(taunts_by_cause[cause]) > 0 ):

                # Choose a taunt at random...
                pos = random.randint(0, len(taunts_by_cause[cause]) - 1)
                #pos = 1

                # Use that taunt...
                random_taunt = taunts_by_cause[cause][pos]


        # Fetch the overworld game over template
        template = self.fetch_xml_template("overworld.menu.death").add_parameters({
            "@x": xml_encode( "%d" % int(SCREEN_WIDTH / 2) ),
            "@y": xml_encode( "%d" % int(SCREEN_HEIGHT / 2) ),
            "@width": xml_encode( "%d" % int(OVERWORLD_DEATH_MENU_WIDTH * SCREEN_WIDTH) ),
            "@doublewidth": xml_encode( "%d" % (2 * int(OVERWORLD_DEATH_MENU_WIDTH * SCREEN_WIDTH)) ),
            "@height": xml_encode( "%d" % SCREEN_HEIGHT ),
            "@random-taunt": xml_encode( control_center.get_localization_controller().translate( universe.translate_session_variable_references(random_taunt, control_center) ) ),
            "@last-visited-town-name": xml_encode( universe.get_session_variable("core.last-safe-zone.map").get_value() ),
            "@last-visited-town-title": xml_encode( universe.get_session_variable("core.last-safe-zone.title").get_value() )
        })

        # Compile template
        root = template.compile_node_by_id("layouts")#("menu")

        # Build widget
        widget = widget_dispatcher.convert_node_to_widget(root, control_center, universe)

        widget.set_id("overworld-death")

        # Add new page
        results.append(
            self.add_widget_via_event(widget, event)
        )

        # Return events
        return results


    # Load the last checkpoint (autosave)
    def handle_last_autosave_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch window controller
        window_controller = control_center.get_window_controller()


        # Dismiss the widget for this menu
        self.get_widget_by_id("overworld-death").hide()


        # Hook into the window controller
        window_controller.hook(self)

        # Fade the app, raising a (forwarded) event when done
        window_controller.fade_out(
            on_complete = "fwd.finish:last-autosave"
        )


        log2( "Begin fade" )

        # Return events
        return results


    # (Fwd) Finish load last autosave logic, post-fade
    def handle_fwd_finish_last_autosave_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # We'll need the save controller;
        save_controller = control_center.get_save_controller()

        # and the window controller
        window_controller = control_center.get_window_controller()


        # Unhook from the window controller
        window_controller.unhook(self)


        # Manually cleanup universe session
        universe.end_session(control_center, universe)


        log2( "Clearing visible maps (if they're not already cleared?) for debug..." )
        for layer in universe.visible_maps:
            universe.visible_maps[layer].clear()


        # Load the last autosave...
        save_controller.load_from_folder(
            os.path.join( universe.get_working_save_data_path(), "autosave1" ),
            control_center,
            universe
        )


        """
        # Transition to the new map.  Don't save memory for the current map.
        universe.transition_to_map(
            universe.get_session_variable("app.active-map-name").get_value(),
            control_center = control_center,
            save_memory = False,
            can_undo = False
        )
        """


        # App fade in as we resume from autosave
        window_controller.fade_in()


        log2( "Transition complete?" )
        log2( "**player status = %s\n" % universe.get_local_player().status )



        # Fire a kill event; we're done with this menu
        self.fire_event("kill")


        # Return events
        return results


    # Spawn in the last-visited town (no checkpoint)
    def handle_last_town_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Fetch window controller
        window_controller = control_center.get_window_controller()


        # Dismiss the widget for this menu
        self.get_widget_by_id("overworld-death").hide()


        # Hook into the window controller
        window_controller.hook(self)

        # Fade the app, raising a (forwarded) event when done
        window_controller.fade_out(
            on_complete = "fwd.finish:last-town"
        )


        # Return events
        return results


    # (Fwd) Finish spawn in last-visited town logic, post-fade
    def handle_fwd_finish_last_town_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # We'll need the save controller;
        save_controller = control_center.get_save_controller()

        # and the window controller
        window_controller = control_center.get_window_controller()


        # Unhook from the window controller
        window_controller.unhook(self)


        # Manually cleanup universe session
        universe.end_session(control_center, universe)


        log2( "Clearing visible maps (if they're not already cleared?) for debug..." )
        for layer in universe.visible_maps:
            universe.visible_maps[layer].clear()


        """
        # Load the last autosave...
        save_controller.load_from_folder(
            os.path.join( universe.get_working_save_data_path(), "autosave1" ),
            control_center,
            universe
        )
        """
        # Transition to the last-visited town map.  Don't save memory for the current map.
        """
        universe.transition_to_map(
            universe.get_session_variable("core.last-safe-zone.map").get_value(),
            waypoint_to = "safe-spawn",
            control_center = control_center,
            save_memory = False,
            can_undo = False
        )
        """
        universe.activate_map_on_layer_by_name(
            universe.get_session_variable("core.last-safe-zone.map").get_value(),
            LAYER_FOREGROUND,
            control_center = control_center,
            ignore_adjacent_maps = False
        )

        # Player spawn coordinates
        (x, y) = (0, 0)


        # Check for a safe-spawn trigger
        t = universe.get_active_map().get_trigger_by_name("safe-spawn")

        # Validate
        if (t):

            # Update player spawn coordinates
            (x, y) = (
                (t.x * TILE_WIDTH),
                (t.y * TILE_HEIGHT)
            )


        # Position the player on the new map.
        universe.spawn_player_with_name_at_location(
            name = "player1",
            x = x,
            y = y
        )


        # Center the camera on the primary map as we begin the universe
        universe.get_active_map().center_camera_on_entity_by_name(universe.camera, "player1", zap = True)


        # Having respawned the player, let's reset the "handled local death" flag
        universe.get_session_variable("core.handled-local-death").set_value("0")


        """
        # Transition to the new map.  Don't save memory for the current map.
        universe.transition_to_map(
            universe.get_session_variable("core.last-safe-zone.map").get_value(),
            waypoint_to = "safe-spawn",
            controL_center = control_center,
            save_memory = False,
            can_undo = False
        )


        universe.transition_to_map(
            universe.get_session_variable("app.active-map-name").get_value(),
            control_center = control_center,
            save_memory = False,
            can_undo = False
        )
        """


        # App fade in as we resume from autosave
        window_controller.fade_in()


        log2( "Transition complete?" )
        log2( "**player status = %s\n" % universe.get_local_player().status )



        # Fire a kill event; we're done with this menu
        self.fire_event("kill")


        # Return events
        return results


    # Kill menu
    def handle_kill_event(self, event, control_center, universe):

        # Events that result from handling this event (on-birth events, etc.)
        results = EventQueue()

        # Convenience
        params = event.get_params()


        # Done with the pause menu widget
        self.set_status(STATUS_INACTIVE)

        # Return events
        return results
