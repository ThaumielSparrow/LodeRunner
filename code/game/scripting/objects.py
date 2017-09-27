import sys
import random

import math

import time

from code.tools.eventqueue import EventQueueIter

from code.constants.common import *
from code.constants.states import *

from code.constants.newsfeeder import *

from code.constants.scripting import *

from code.constants.death import *

from code.constants.network import NET_STATUS_OFFLINE

from code.tools.xml import XMLParser

from code.utils.common import log, log2, logn, is_numeric, offset_rect, intersect, format_framecount_as_time


# Local debug flag.
# When I release this game, I will probably remove or comment out all code related to this, just as an optimization.
DEBUG = True


# Generic local error handling function.
# Expects a string as the error message.
def handle_error(s):

    if ( "--debug" in sys.argv ):

        # Add to file
        f = open("integrity1.txt", "a")
        f.write( "%s\n\n" % s )
        f.close()

    # Let's print to console as well
    log2(s)


class Generic:

    def __init__(self):

        self.commands = {}

    def evaluate(self, command, params, control_center, universe):

        logn( "script object debug", "BASE command %s, params %s" % (command, params) )

        # Validate
        if (command in self.commands):

            # Get metadata
            data = self.commands[command]

            # Run callback
            return data["callback"](params, control_center, universe)

        else:

            handle_error( "Method Warning:  \n\tMap:  %s\n\tMethod:  %s" % ( universe.get_active_map().get_name(), command ) ) # Debug
            return None


class Base(Generic):

    def __init__(self):

        Generic.__init__(self)

        self.commands = {
            "debug": {
                "callback": self.debug,
                "params": 1
            },
            "window": {
                "callback": self.get_window
            },
            "autosave": {
                "callback": self.autosave
            },
            "addHistoricalRecord": {
                "callback": self.add_historical_record
            },
            "addHistoricalRecordUsingLabel": {
                "callback": self.add_historical_record_using_label
            },
            "hasHistoricalRecord": {
                "callback": self.has_historical_record
            },
            "historicalRecordsByType": {
                "callback": self.get_historical_records_by_type
            },
            "achievement": {
                "callback": self.get_achievement
            },
            "hasEditedControls": {
                "callback": self.has_edited_controls
            },
            "session": {
                "callback": self.get_session_variable
            },
            "progress": {
                "callback": self.get_progress_wrapper
            },
            "quest": {
                "callback": self.get_quest,
                "params": 1
            },
            "universe": {
                "callback": self.get_universe
            },
            "map": {
                "callback": self.get_map
            },
            "showPuzzleIntro": {
                "callback": self.show_puzzle_intro
            },
            "showChallengeOutro": {
                "callback": self.show_challenge_outro
            },
            "player": {
                "callback": self.get_player
            },
            "distributeBombs": {
                "callback": self.distribute_bombs
            },
            "disableInactivePlayers": {
                "callback": self.disable_inactive_players
            },
            "npc": {
                "callback": self.get_npc,
                "params": 1
            },
            "npcsByClass": {
                "callback": self.get_npcs_by_class
            },
            "closestNpc": {
                "callback": self.get_closest_npc
            },
            "trigger": {
                "callback": self.get_trigger,
                "params": 1
            },
            "triggersByClass": {
                "callback": self.get_triggers_by_class
            },
            "enemy": {
                "callback": self.get_enemy
            },
            "postNewsItem": {
                "callback": self.post_news_item
            },
            "createTimer": {
                "callback": self.create_timer
            },
            "clearTimer": {
                "callback": self.clear_timer
            },
            "incrementTimer": {
                "callback": self.increment_timer
            },
            "hasTimeRemaining": {
                "callback": self.has_time_remaining
            },
            "getMinutesRemaining": {
                "callback": self.get_minutes_remaining
            }
        }


    def debug(self, params, control_center, universe):

        s = ""

        for param in params:
            s += "%s" % param.evaluate(control_center, universe)

        logn( "debug", "Debug message:  %s" % s )

        # This method never supports chaining.
        return None


    # Get a wrapper for the window controller
    def get_window(self, params, control_center, universe):

        # Return simple wrapper
        return Window()


    # Commit an autosave (autosave1)
    def autosave(self, params, control_center, universe):

        # Send an emulated autosave event to the universe's event handler
        universe.handle_event(
            EventQueueIter("autosave"),
            control_center,
            universe
        )


    """
    # Generic evaluation function
    def eval(self, params, control_center, universe):

        # We feed this function an expression, so it should have only one parameter
        result = 0

        # Try to evaluate
        result = eval(
            params[0].evaluate(control_center, universe)
        )
    """


    # Add a new historical record
    def add_historical_record(self, params, control_center, universe):

        # Add
        universe.add_historical_record(
            params[0].evaluate(control_center, universe),
            params[1].evaluate(control_center, universe)
        )

        # No chaining on this method
        return None


    # Add a historical record using a given label as the template
    # and an optional hash of parameters.
    def add_historical_record_using_label(self, params, control_center, universe):

        # Assume / scope
        (group, label_name, label_params) = (
            params[0].evaluate(control_center, universe),
            params[1].evaluate(control_center, universe),
            {} # assumption (no parameters for label)
        )

        # Check for params hash
        if ( len(params) > 2 ):

            # Avoid crashing on bad syntax, etc.
            try:
                # Update params hash using given hash
                label_params.update(
                    params[2].evaluate(control_center, universe)
                )

            # Hack, late addition, etc.
            except:
                pass


        # Add the historical record
        universe.add_historical_record(
            group, # e.g. "purchases"
            control_center.get_localization_controller().get_label(
                label_name, label_params
            )
        )

        # For chaining
        return self


    # Check to see if the universe has a given historical record in a given group
    def has_historical_record(self, params, control_center, universe):

        # Quick check
        return universe.has_historical_record(
            params[0].evaluate(control_center, universe),
            params[1].evaluate(control_center, universe)
        )


    # Get a query result with knowledge of all historical records matching a given type
    def get_historical_records_by_type(self, params, control_center, universe):

        # Return query result wrapper
        return HistoricalRecordList(
            universe.get_historical_records_by_type(
                params[0].evaluate(control_center, universe)
            )
        )


    # Get an achievement (wrapped in a query result wrapper)
    def get_achievement(self, params, control_center, universe):

        # Try to find achievement
        achievement = universe.get_achievement_by_name(
            params[0].evaluate(control_center, universe)
        )

        # Validate
        if (achievement):

            # Return the achievement in a query result wrapper
            return Achievement(achievement)

        else:
            return None


    # Check to see if the user has edited controls
    def has_edited_controls(self, params, control_center, universe):

        # Return a boolean
        return control_center.has_edited_controls()


    # Get a session variable (wrapped in a query result wrapper)
    def get_session_variable(self, params, control_center, universe):

        """
        Hack into universe default session variables to see if this key exists.
        If it doesn't, we should review it in case it's a typo.
        """
        if ( not ( params[0].evaluate(control_center, universe) in universe.session ) ):

            handle_error( "Session Warning:  \n\tMap:  %s\n\tName:  %s" % ( universe.get_active_map().get_name(), params[0].evaluate(control_center, universe) ) ) # Debug


        # Wrap result in query result object
        return SessionVariable(
            universe.get_session_variable(
                params[0].evaluate(control_center, universe)
            ), params[0].evaluate(control_center, universe)
        )


    # Get a "Progress" query result object, which simply exposes new methods and such...
    def get_progress_wrapper(self, params, control_center, universe):

        # Return new wrapper
        return Progress()


    # Get the current universe in a query result wrapper
    def get_universe(self, params, control_center, universe):

        # Query result wrapper
        return Universe(universe)


    # Get the active map
    def get_map(self, params, control_center, universe):

        # Return a query result wrapper
        return Map( universe.get_active_map() )


    # Show a puzzle intro dialog.
    # We should set all necessary map params (overview, prize data, etc.) before doing this.
    def show_puzzle_intro(self, params, control_center, universe):

        # Fetch the widget dispatcher;
        widget_dispatcher = control_center.get_widget_dispatcher()

        # and the menu controller;
        menu_controller = control_center.get_menu_controller()

        # and the splash controller
        splash_controller = control_center.get_splash_controller()


        # Fetch active map
        m = universe.get_active_map()

        # Summon pause splash
        splash_controller.set_mode(SPLASH_MODE_GREYSCALE_ANIMATED)


        # Default options (none?)
        options = {}#e.node.get_attributes()

        # Fetch other attributes, such as text fills, from the map's params...
        options["overview"] = "%s" % m.get_param("overview")


        # Add a puzzle intro menu
        menu_controller.add(
            widget_dispatcher.create_puzzle_intro_menu().configure(
                options
            )
        ).delay(0)

        # Engage the menu controller's pause lock
        menu_controller.configure({
            "pause-locked": True
        })


        # No chaining on this method
        return None


    # Show a challenge room's outro (i.e. victory!) dialog.
    # Note that we're actually using the puzzle victory menu (for now?).
    def show_challenge_outro(self, params, control_center, universe):

        # Is this the first time we've completed this map?
        if (
            not universe.is_map_completed( universe.get_active_map().name )
        ):

            # Implicitly mark the current map as completed.
            universe.mark_map_as_completed( universe.get_active_map().name )

            # Implicitly execute the "challenge-complete" achievement hook
            universe.execute_achievement_hook( "challenge-complete", control_center )


        # Fetch the menu controller;
        menu_controller = control_center.get_menu_controller()

        # and the widget dispatcher
        widget_dispatcher = control_center.get_widget_dispatcher()


        # Add a victory menu
        menu_controller.add(
            widget_dispatcher.create_puzzle_victory_menu()
        )


        # No chaining on this method
        return None


    # Get a player object.
    # Defaults to player1 if no param is given.
    def get_player(self, params, control_center, universe):

        # Default player id
        name = "player%s" % universe.get_session_variable("core.player-id").get_value()

        # Explicit id request?
        if ( len(params) > 0 ):

            # Update
            name = params[0].evaluate(control_center, universe)


        # Find player1
        player = universe.get_active_map().get_entity_by_name(name)

        # Validate
        if (player):

            # Wrap in a query result object
            return Player(player)

        else:
            return None


    # Get an NPC by name.
    def get_npc(self, params, control_center, universe):

        npc = universe.get_active_map().get_entity_by_name( params[0].evaluate(control_center, universe) )

        if (npc):

            return NPC(npc)

        else:

            handle_error( "NPC Warning:  \n\tMap:  %s\n\tName:  %s" % ( universe.get_active_map().get_name(), params[0].evaluate(control_center, universe) ) ) # Debug
            return None


    # Get a list of NPCs, by class
    def get_npcs_by_class(self, params, control_center, universe):

        # What class do we want?
        class_name = params[0].evaluate(control_center, universe)

        # Track matches
        results = []

        # Loop all NPCs
        for o in universe.get_active_map().get_entities_by_type(GENUS_NPC):

            # Class match?
            if ( any( o.has_class(s) for s in class_name.split(" ") ) ):

                # Track
                results.append(
                    NPC(o)
                )


        logn( "script object debug", "iterator matches source:  ", results )


        # Return results, wrapped in a query result object
        return NPCResultList(results)


    # Get the NPC closest to the player's current position
    def get_closest_npc(self, params, control_center, universe):

        # Default to some huge distance
        distance = INFINITY

        # No known result, yet...
        result = None


        # Default player coordinates (declare here for scope)
        (px, py) = (0, 0)

        # Find the "player1" entity
        player = universe.get_active_map().get_entity_by_name("player1")

        # Validate
        if (player):

            # Update player coordinates
            (px, py) = (
                player.get_x(),
                player.get_y()
            )


        # Loop NPCs
        for o in universe.get_active_map().get_entities_by_type(GENUS_NPC):

            # NPC coordinates
            (x, y) = (
                o.get_x(),
                o.get_y()
            )

            # Calculate this NPC's distance from the player
            npc_distance = math.sqrt((x - px) * (x - px)) + ((y - py) * (y - py))

            # Check to see if this is the closest NPC yet found
            if (npc_distance < distance):

                # We found a new closest npc
                result = o

                # New closest distance
                distance = npc_distance


        # Did we find a result?
        if (result):

            # Return wrapped in a query result wrapper
            return NPC(result)

        # Otherwise, return nothing...
        else:

            handle_error( "NPC Warning:  Could not find an NPC in get_closest_npc" )
            return None


    # Get a trigger on the current map, by name
    def get_trigger(self, params, control_center, universe):

        # Find trigger
        trigger = universe.get_active_map().get_trigger_by_name( params[0].evaluate(control_center, universe) )

        # Validate
        if (trigger):

            # Create query result wrapper
            return Trigger(trigger)

        else:

            handle_error( "Trigger Warning:  \n\tMap:  %s\n\tName:  %s" % ( universe.get_active_map().get_name(), params[0].evaluate(control_center, universe) ) ) # Debug
            return None


    # Get a list of all triggers that have a given class
    def get_triggers_by_class(self, params, control_center, universe):

        # What class do we want?
        class_name = params[0].evaluate(control_center, universe)

        # Track matches
        results = []

        # Loop all triggers
        for t in universe.get_active_map().get_triggers():

            # Class match?
            if ( any( t.has_class(s) for s in class_name.split(" ") ) ):

                # Track
                results.append(
                    Trigger(t)
                )

        # Return results in a query result wrapper
        return TriggerResultList(results)


    def get_quest(self, params, control_center, universe):

        #print params[0].evaluate(control_center, universe)
        quest = universe.get_quest_by_name( params[0].evaluate(control_center, universe) )

        if (quest):

            return Quest(quest)

        else:

            handle_error( "Quest Warning:  \n\tMap:  %s\n\tName:  %s" % ( universe.get_active_map().get_name(), params[0].evaluate(control_center, universe) ) ) # Debug
            return None


    # Get an Enemy by name.
    def get_enemy(self, params, control_center, universe):

        enemy = universe.get_active_map().get_entity_by_name( params[0].evaluate(control_center, universe) )

        if (enemy):

            return Enemy(enemy)

        else:

            handle_error( "Enemy Warning:  \n\tMap:  %s\n\tName:  %s" % ( universe.get_active_map().get_name(), params[0].evaluate(control_center, universe) ) ) # Debug
            return None


    # Distribute bombs to each player in a cooperative game
    def distribute_bombs(self, params, control_center, universe):

        # Assume 0
        universe.get_session_variable("core.bombs.count").set_value("0")

        # Expects a list (e.g. [1, 1, 1])
        if (1):#try:

            # Track current player slot
            slot = 1

            # Get given list
            ul = params[0].evaluate(control_center, universe)["per-slot"]


            # Get a list of joined player slots (e.g. [1, 2], [1, 2, 3], [1, 3], etc.)
            joined_slots = [ i for i in range(1, 5) if int( universe.get_session_variable("net.player%d.joined" % i).get_value() ) == 1 ]


            # Get local player id
            player_id = int( universe.get_session_variable("core.player-id").get_value() )

            # Validate player id exists in "joined slots" list
            if (player_id in joined_slots):

                # Find the local player id in that list (get the index)
                local_index = joined_slots.index(player_id)

                # Using the given bomb distribution per slot, set the local session variable...
                if ( len(ul) > local_index ):

                    # Update session variable
                    universe.get_session_variable("core.bombs.count").set_value( "%s" % ul[local_index] )


        else:#except:
            log2( "Warning:  Bad argument passed to distribute_bombs function!" )


        # No chaining
        return None


    # Disable inactive players (or, all non-player1 characters if playing in offline mode)
    def disable_inactive_players(self, params, control_center, universe):

        # Fetch network controller
        network_controller = control_center.get_network_controller()


        # Get player entities
        players = universe.get_active_map().get_entities_by_type(GENUS_PLAYER)


        # If we are playing in offline mode, then we want to disable
        # any entity that is not player1.
        if ( network_controller.get_status() == NET_STATUS_OFFLINE ):

            # Loop players
            for p in players:

                # If this isn't player1, disable...
                if ( p.get_name() != "player1" ):

                    # Disable
                    p.set_status(STATUS_INACTIVE)

        # Otherwise, we just want to disable players who haven't joined the game (e.g. disable player3 in a 2-player game)
        else:

            # Loop player slots
            for slot in (1, 2, 3, 4):

                # Try to get player object
                player = universe.get_active_map().get_entity_by_name( "player%d" % slot )

                # Validate
                if (player):

                    # Has this player not joined?
                    if ( int( universe.get_session_variable("net.player%d.joined" % slot).get_value() ) == 0 ):

                        # Disable inactive player
                        player.set_status(STATUS_INACTIVE)


        # For chaining
        return self


    # Post an item to the newsfeeder.  Expects a title and contenet.
    def post_news_item(self, params, control_center, universe):

        # Post a generic newsfeeder item
        control_center.get_window_controller().get_newsfeeder().post({
            "type": NEWS_GENERIC_ITEM,
            "title": params[0].evaluate(control_center, universe),
            "content": params[1].evaluate(control_center, universe)
        })

        # No chaining on this method
        return None


    # Create a new timer in the active universe
    def create_timer(self, params, control_center, universe):

        # Default settings
        options = {
            "name": "timer1",
            "length": 10,
            "uses": 1,              # Assume it only fires once
            "measure": "seconds",
            "on-complete": ""
        }

        # Update via attributes.  We should always give a hash, probably.
        if ( len(params) == 1 ):

            # Update
            options.update(
                params[0].evaluate(control_center, universe)
            )


        # The length must be numeric.
        if ( is_numeric( "%s" % options["length"] ) ):

            # Cast the raw length as a float, first...
            length = float( options["length"] )

            # Measure in frames, we will simply go with an integer...
            if ( options["measure"] == "frames" ):

                length = int(length)

            # Seconds?
            elif ( options["measure"] == "seconds" ):

                length = int(60 * length) # 60 FPS (hard-coded)

            # Default to frames, if no measure (or an invalid measure) is given.
            else:

                length = int(length)


            # Create singular timer object (for now, just a single use).
            universe.get_timer_controller().add_repeating_event_with_name(
                options["name"],
                length,
                uses = options["uses"],
                on_complete = options["on-complete"],
                params = {}
            )


        # For chaining
        return self


    # Clear a timer within the active universe, by name
    def clear_timer(self, params, control_center, universe):

        # Timer name
        name = params[0].evaluate(control_center, universe)

        # Try to remove the timer.  Fails gracefully, silently.
        universe.get_timer_controller().remove_timer_by_name(name)


        # For chaining
        return self


    # Increment a timer by some amount, by name and hash (name of timer, hash of increment info)
    def increment_timer(self, params, control_center, universe):

        # Timer name
        name = params[0].evaluate(control_center, universe)


        # Default settings
        options = {
            "length": 0,
            "measure": "seconds"
        }

        # Update with given settings
        if ( len(params) == 2 ):

            # Update from given hash
            options.update(
                params[1].evaluate(control_center, universe)
            )


        # Try to get timer
        timer = universe.get_timer_controller().get_timer_by_name(name)

        # Validate
        if (timer):

            # Convenience
            value = "%s" % options["length"]
            measure = options["measure"]

            # Value must be numeric
            if ( is_numeric(value) ):

                # Check measure
                if (measure == "frames"):

                    # Cast into integer
                    value = int(value)

                elif (measure == "seconds"):

                    # Cast into integer * seconds
                    value = int( 60 * int(value) ) # 60 FPS (hard-coded)

                # Default to frames
                else:

                    # Cast into integer
                    value = int(value)


                # Increment timer by given interval
                timer.increment(value)


            else:
                log2( "Warning:  Cannot increment timer '%s' by non-numeric value '%s!'" % (name, value) )


        # For chaining
        return self


    # Check to see if the active game session has time remaining, compared against a given value in minutes
    def has_time_remaining(self, params, control_center, universe):

        # Count frames of gameplay
        frames = int( universe.get_session_variable("core.time.played").get_value() )

        # Simple check
        return ( frames <= (60 * 60 * int( params[0].evaluate(control_center, universe) )) )


    # Get a formatted string (mm:ss) representing how much time (if any) the player has until they've
    # played for the given length of time (in minutes)...
    def get_minutes_remaining(self, params, control_center, universe):

        # Is there any time remaining?
        if ( self.has_time_remaining(params, control_center, universe) ):

            # Count frames of gameplay
            frames = int( universe.get_session_variable("core.time.played").get_value() )

            # Count available number of frames
            limit = int( (60 * 60 * int( params[0].evaluate(control_center, universe) )) )

            # Return amount remaining
            return format_framecount_as_time(limit - frames)

        # No time left
        else:

            # Return 0:00
            return "0:00"


# A query result class that offers access to the window controller
class Window(Generic):

    def __init__(self):

        Generic.__init__(self)

        self.commands = {
            "increaseDialogueLock": {
                "callback": self.increase_dialogue_lock
            },
            "decreaseDialogueLock": {
                "callback": self.decrease_dialogue_lock
            }
        }


    # Increase dialogue lock count
    def increase_dialogue_lock(self, params, control_center, universe):

        # Default to 0 if count does not exist
        if ( not control_center.get_window_controller().has_param("dialogue-lock-count") ):

            # Default
            control_center.get_window_controller().set_param("dialogue-lock-count", "0")


        # Get existing count
        count = int( control_center.get_window_controller().get_param("dialogue-lock-count") )

        # Increase
        count += 1

        # Update tracker
        control_center.get_window_controller().set_param("dialogue-lock-count", "%s" % count)


        # For chaining
        return self


    # Decrease dialogue lock count
    def decrease_dialogue_lock(self, params, control_center, universe):

        logn( 1, "Warning:  Decrease not supported via script call." )

        # For chaining
        return self


# A query result class that offers various game progress methods
class Progress(Generic):

    # No handle
    def __init__(self):

        Generic.__init__(self)

        # Define methods
        self.commands = {
            "map": {
                "callback": self.get_map
            },
            "getMapsByClass": {
                "callback": self.get_maps_by_class
            }
        }


    # Get progress data for a single map, by name
    def get_map(self, params, control_center, universe):

        # Try to get map data object
        map_data = universe.get_map_data( params[0].evaluate(control_center, universe) )

        # Validate
        if (map_data):

            # Return query result wrapper
            return ProgressMap(map_data)

        else:
            return None


    # Get progress data for a group of maps, in a list
    def get_maps_by_class(self, params, control_center, universe):

        """ In DEBUG mode, let's check to see if we have at least one match.
            If we don't, that might signal that we mistyped the desired class. """
        if (DEBUG):

            # Check count
            if ( len( universe.get_map_data_by_class( params[0].evaluate(control_center, universe) ) ) == 0 ):

                # Possible bad param warning
                handle_error(
                    "Maps by Class Warning:  \n\tMap:  %s\n\tClass Name:  %s" % ( universe.get_active_map().get_name(), params[0].evaluate(control_center, universe) ) # Debug
                )
        """ End DEBUG """

        # Wrap results in a query result object
        return ProgressMapList(
            universe.get_map_data_by_class(
                params[0].evaluate(control_center, universe)
            )
        )


# A query resutl for progress data on a single map
class ProgressMap(Generic):

    # Feed map dadta object as handle
    def __init__(self, handle):

        Generic.__init__(self)

        # Keep handle
        self.handle = handle

        # Define methods
        self.commands = {
            "getTitle": {
                "callback": self.get_title
            },
            "hasClass": {
                "callback": self.has_class
            }
        }


    # Get the title from the map data object
    def get_title(self, params, control_center, universe):

        # Return title
        return self.handle.get_title()


    # Check to see if this map data object has a given class
    def has_class(self, params, control_center, universe):

        # Return boolean
        return self.handle.has_class(
            params[0].evaluate(control_center, universe)
        )


# A query result for a list of map progress objects
class ProgressMapList(Generic):

    # Feed a list of map data objects
    def __init__(self, l):

        Generic.__init__(self)

        # Keep handles
        self.handles = l

        # Define methods
        self.commands = {
            "count": {
                "callback": self.get_count
            },
            "countCompleted": {
                "callback": self.get_count_completed
            },
            "countWithoutGold": {
                "callback": self.get_count_without_gold
            },
            "countVisible": {
                "callback": self.get_count_visible
            },
            "countVisited": {
                "callback": self.get_count_visited
            },
            "getPercentVisited": {
                "callback": self.get_percent_visited
            },
            "markAsVisible": {
                "callback": self.mark_as_visible
            },
            "npcs": {
                "callback": self.get_npcs
            },
            "npcsByClass": {
                "callback": self.get_npcs_by_class
            }
        }


    # Count the number of matching maps
    def get_count(self, params, control_center, universe):

        # Simple count
        return len(self.handles)


    # Count the number of matching maps that the player has completed
    def get_count_completed(self, params, control_center, universe):

        # Sum
        return sum( int( o.is_map_completed() ) for o in self.handles )


    # Count the number of matching maps that have no gold remaining
    def get_count_without_gold(self, params, control_center, universe):

        # Sum
        return sum( int( o.has_gold_remaining() ) == 0 for o in self.handles )


    # Count the number of matching maps that the player can at least see on the world map
    def get_count_visible(self, params, control_center, universe):

        # Sum
        return sum( int( o.is_map_visible() ) for o in self.handles )


    # Count the number of matching maps that the player has visited
    def get_count_visited(self, params, control_center, universe):

        # Sum
        return sum( int( o.is_map_visited() ) for o in self.handles )


    # Get the percentage of maps visited, as a human readable string (e.g. 85.5%)
    def get_percent_visited(self, params, control_center, universe):

        # Get raw percentage
        percent = float( sum( int( o.is_map_visited() ) for o in self.handles ) ) / float( len(self.handles) )

        # Convert to int, multiplying by 4 decimal places to keep full value plus 2 decimal places (e.g. .5153223423 -> 5153, formats to 51.53).
        # Cast that result into a string.
        readable = "%d" % int( percent * 10000 )

        # Hack in a decimal
        readable = readable[ 0 : len(readable) - 2 ] + "." + readable[ len(readable) - 2 : len(readable) ]

        # Return human readable string
        return readable


    # Mark each of the matching maps as "visible" on the player's world map
    def mark_as_visible(self, params, control_center, universe):

        # Loop matches
        for handle in self.handles:

            # Mark as visible
            handle.mark_as_visible()


    # Get all of the NPCs for the maps in this list.
    def get_npcs(self, params, control_center, universe):

        # Track results (NPC objects across all maps)
        results = []

        # Loop map data objects
        for map_data in self.handles:

            # Get a temporary map object, with memory data loaded
            m = universe.get_temporary_map_by_name( map_data.get_name() )

            # Validate
            if (m):

                # Add all NPCs on the map
                results.extend(
                    m.get_entities_by_type(GENUS_NPC)
                )


        # Wrap the list of NPCs in a query result wrapper
        return ProgressMapListNPCList(results)


    # Get all of the NPCs for the maps in this list, matchign a given class name
    def get_npcs_by_class(self, params, control_center, universe):

        # Which class name(s) are we looking for?
        class_names = params[0].evaluate(control_center, universe).split(" ")


        # Track results (NPC objects across all maps)
        results = []

        # Loop map data objects
        for map_data in self.handles:

            # Get a temporary map object, with memory data loaded
            #m = universe.get_temporary_map_by_name( map_data.get_name() )

            # We don't need to load in the entire map data; we can
            # skip tile data, triggers, etc.  First, we'll create a generic map object.
            m = universe.create_map(
                name = map_data.get_name(),
                x = 0,          # Not needed for a temp map, just looking up stats
                y = 0,          # (same)
                options = {
                    "is-new": False
                },
                control_center = None            # Obsolete control_center param
            )

            # Validate new map object
            if (m):

                # Next, let's read in the xml data that defines this map.
                ref = XMLParser().create_node_from_file( universe.get_map_path_by_name( map_data.get_name() ) )

                # Validate xml parsing
                if (ref):

                    # We need to load data into the map, but we only need
                    # to load entity-related data.
                    m.load_from_string(
                        data = {
                            "map": ref.find_node_by_tag("entities").compile_xml_string()
                        },
                        options = {},
                        control_center = control_center
                    )

                    # We should also load the map's memory data.
                    m.load_memory(universe)


                # Now we can loop through the map's entity objects.
                for o in m.get_entities_by_type(GENUS_NPC):

                    # If this NPC has any of the given class names, then add it to the results
                    if ( any( o.has_class(class_name) for class_name in class_names ) ):

                        # Matched
                        results.append(o)


        """ In DEBUG mode, let's check to see if we have at least one match.
            If we don't, that might signal that we mistyped the desired class. """
        if (DEBUG):

            # Check count
            if ( len(results) == 0 ):

                # Possible bad param warning
                handle_error(
                    "ProgressMapList NPCs by Class Warning:  \n\tMap:  %s\n\tClass(es):  '%s'" % ( universe.get_active_map().get_name(), params[0].evaluate(control_center, universe) ) # Debug
                )
        """ End DEBUG """


        # Wrap the list of NPCs in a query result wrapper
        return ProgressMapListNPCList(results)


# A query result wrapper for a list of NPCs on a list of maps
class ProgressMapListNPCList(Generic):

    # Feed list of NPC objects
    def __init__(self, l):

        Generic.__init__(self)

        # Keep list of handles
        self.handles = l

        # Define methods
        self.commands = {
            "count": {
                "callback": self.get_count
            },
            "countLiving": {
                "callback": self.get_count_living
            },
            "countDead": {
                "callback": self.get_count_dead
            }
        }


    # Count total matches
    def get_count(self, params, control_center, universe):

        # Simple count
        return len(self.handles)


    # Count the total number of living NPCs within the map list
    def get_count_living(self, params, control_center, universe):

        # Sum
        return sum( int( not o.is_dead() ) for o in self.handles )


    # Count the total number of dead NPCs within the map list
    def get_count_dead(self, params, control_center, universe):

        # Sum
        return sum( int( o.is_dead() ) for o in self.handles )


# A query result wrapper for a list of historical records
class HistoricalRecordList(Generic):

    # Feed a list of historical record (strings) as param
    def __init__(self, l):

        Generic.__init__(self)

        # Keep list of records (string values)
        self.records = l

        # Define methods
        self.commands = {
            "count": {
                "callback": self.get_count
            }
        }

    # Count total matches
    def get_count(self, params, control_center, universe):

        # Return count
        return len(self.records)


# A query result wrapper for an achievement
class Achievement(Generic):

    # Feed the Achievement object as handle
    def __init__(self, handle):

        Generic.__init__(self)

        # Keep handle
        self.handle = handle

        # Define methods
        self.commands = {
            "status": {
                "callback": self.status
            },
            "isComplete": {
                "callback": self.is_complete
            }
        }


    # If no parameter is given, get the status of the achievement.
    # If a parameter is given, set the status of the achievement.
    def status(self, params, control_center, universe):

        # No parameter giveN?
        if ( len(params) == 0 ):

            # Return status as a string
            return self.handle.get_status()

        # At least one parameter given
        else:

            # Set the status
            self.handle.set_status(
                params[0].evaluate(control_center, universe)
            )


            # Implicitly post a newsfeeder message if we have completed the achievement
            if ( params[0].evaluate(control_center, universe) == "complete" ):

                # Post newsfeeder message
                control_center.get_window_controller().get_newsfeeder().post({
                    "type": NEWS_GENERIC_ITEM,
                    "title": control_center.get_localization_controller().get_label("achievement-complete:title"),
                    "content": self.handle.get_title()
                })

                # Also implicitly update list of completed achievements
                control_center.save_unlocked_achievements(universe)


            # For chaining
            return self


    # Check to see if the player has completed this achievement
    def is_complete(self, params, control_center, universe):

        # Simple status check
        return self.handle.is_complete()


# A query result wrapper for a session variable
class SessionVariable(Generic):

    # Feed the session hash data as handle
    def __init__(self, handle, debug = "(session variable)"):

        Generic.__init__(self)

        # Keep handle
        self.handle = handle
        self.debug = debug

        # Define methods
        self.commands = {
            "get": {
                "callback": self.get_value
            },
            "set": {
                "callback": self.set_value
            },
            "setConcat": {
                "callback": self.set_concat
            },
            "increment": {
                "callback": self.increment_value
            },
            "setRandomly": {
                "callback": self.set_randomly
            },
            "equals": {
                "callback": self.equals
            },
            "notEquals": {
                "callback": self.not_equals
            }
        }


    # Get the session variable's current value
    def get_value(self, params, control_center, universe):

        # Default to string
        return_type = "string"

        # Check for optional return type param
        if ( len(params) > 0 ):

            # Update
            return_type = params[0].evaluate(control_center, universe)


        # Default return type
        if (return_type == "string"):

            logn( "script object debug", "Evaluate session '%s' to '%s'" % (self.debug, self.handle.get_value()) )

            # Get value
            value = self.handle.get_value()


            # When not numeric, return as a string wrapped in single quotes
            if ( not is_numeric(value) ):

                # Wrap in quotes
                return "'%s'" % value

            # Otherwise, return whatever raw value we got...
            else:

                # Don't wrap in quotes
                return value

        # Unwrapped string
        elif (return_type == "unwrapped"):

            # Don't wrap in quotes, even if it's a string
            return self.handle.get_value()

        # Return as integer?
        elif (return_type == "integer"):

            # Default
            value = 0

            # Validate that the value is numeric
            if ( is_numeric( self.handle.get_value() ) ):

                # Cast to a float, why not
                value = float( self.handle.get_value() )

            # Return value
            return value


    # Set a new value for the session variable
    def set_value(self, params, control_center, universe):

        # Set value
        self.handle.set_value(
            "%s" % params[0].evaluate(control_center, universe)
        )

        logn( "script object debug", "Session value:  ", self.handle.get_value() )

        # For chaining
        return self


    # Concatenate a given list of parameters and set the result as the value of this session variable.
    def set_concat(self, params, control_center, universe):

        # Set values as concatenated string
        self.handle.set_value(
            "".join(
                [ "%s" % o.evaluate(control_center, universe) for o in params ]
            )
        )

        # For chaining
        return self


    # Increment the session variable.  This will only work on numeric variables, obviously.
    def increment_value(self, params, control_center, universe):

        # Increment value
        self.handle.increment_value(
            params[0].evaluate(control_center, universe)
        )

        # For chaining
        return self


    # Set the value of the session variable randomly from a list of possible values
    def set_randomly(self, params, control_center, universe):

        # Validate at least one param
        if ( len(params) > 0 ):

            # Select at random
            index = random.randint( 0, len(params) - 1 )

            # Set raw value
            self.handle.set_value(
                params[index].evaluate(control_center, universe)
            )

        else:

            # Default to 0 (?)
            self.handle.set_value("0")


    # Check to see if the session variable has a given value
    def equals(self, params, control_center, universe):

        # Comparison
        return ( ("%s" % self.handle.get_value()) == (params[0].evaluate(control_center, universe)) )


    # Check to see if the session variable does not equal a given value
    def not_equals(self, params, control_center, universe):

        # Opposite of equals
        return ( not self.equals(params, control_center, universe) )


# A query result wrapper for a universe object
class Universe(Generic):

    # Feed the universe object as handle
    def __init__(self, handle):

        Generic.__init__(self)

        # Keep handle
        self.handle = handle

        # Define methods
        self.commands = {
            "executeAchievementHook": {
                "callback": self.execute_achievement_hook
            },
            "runScript": {
                "callback": self.run_script
            },
            "executeScript": {
                "callback": self.execute_script
            },
            "getItem": {
                "callback": self.get_item
            },
            "countQuests": {
                "callback": self.count_quests
            }
        }


    # Execute a given achievement hook
    def execute_achievement_hook(self, params, control_center, universe):

        # Execute hook
        self.handle.execute_achievement_hook(
            params[0].evaluate(control_center, universe),
            control_center
        )

        # For chaining
        return self


    # Run a global universe script
    def run_script(self, params, control_center, universe):

        # Run the script
        self.handle.run_script(
            params[0].evaluate(control_center, universe),
            control_center
        )

        # This method never supports chaining
        return None


    # Execute a given global script immediately.
    # Fails to complete any blocking calls.
    def execute_script(self, params, control_center, universe):

        # Run the script
        self.handle.execute_script(
            params[0].evaluate(control_center, universe),
            control_center,
            universe
        )

        # This method never supports chaining
        return None


    # Get an item that exists in the universe
    def get_item(self, params, control_center, universe):

        # Try to get the item
        item = universe.get_item_by_name(
            params[0].evaluate(control_center, universe)
        )

        # Validate
        if (item):

            # Wrap in a query result
            return Item(item)

        else:

            handle_error( "Item Warning:  \n\tMap:  %s\n\tName:  %s" % ( universe.get_active_map().get_name(), params[0].evaluate(control_center, universe) ) ) # Debug
            return None


    # Count how many quests the active universe contains
    def count_quests(self, params, control_center, universe):

        # Return simple count
        return len( universe.get_quests() )


# A query result wrapper for a map object
class Map(Generic):

    # Feed the map object as handle
    def __init__(self, handle):

        Generic.__init__(self)

        # Keep handle
        self.handle = handle

        # Define methods
        self.commands = {
            "name": { "callback": self.name },
            "plane": {
                "callback": self.get_plane
            },
            "getName": {
                "callback": self.get_name
            },
            "setParams": {
                "callback": self.set_params
            },
            "getParam": {
                "callback": self.get_param
            },
            "setWaveParams": {
                "callback": self.set_wave_params
            },
            "setWaveAllowances": {
                "callback": self.set_wave_allowances
            },
            "setWaveRequirements": {
                "callback": self.set_wave_requirements
            },
            "setWaveRequirement": {
                "callback": self.set_wave_requirement
            },
            "setWaveLimits": {
                "callback": self.set_wave_limits
            },
            "getWaveCounter": {
                "callback": self.get_wave_counter
            },
            "getWaveAllowance": {
                "callback": self.get_wave_allowance
            },
            "incrementWaveAllowance": {
                "callback": self.increment_wave_allowance
            },
            "importScript": {
                "callback": self.import_script
            },
            "runScript": {
                "callback": self.run_script
            },
            "executeScript": {
                "callback": self.execute_script
            },
            "beginWave": {
                "callback": self.begin_wave
            },
            "endWave": {
                "callback": self.end_wave
            },
            "showWaveProgressChart": {
                "callback": self.show_wave_progress_chart
            },
            "spawnRandomEnemy": {
                "callback": self.spawn_random_enemy
            },
            "spawnRandomEnemies": {
                "callback": self.spawn_random_enemies
            },
            "countEnemies": {
                "callback": self.count_enemies
            },
            "killEnemies": {
                "callback": self.kill_enemies
            },
            "killEnemiesWithGold": {
                "callback": self.kill_enemies_with_gold
            },
            "removeEnemies": {
                "callback": self.remove_enemies
            },
            "scaleEnemiesSpeed": {
                "callback": self.scale_enemies_speed
            },
            "countGold": {
                "callback": self.count_gold
            },
            "enableAllGold": {
                "callback": self.enable_all_gold
            },
            "disableAllGold": {
                "callback": self.disable_all_gold
            },
            "digArea": {
                "callback": self.dig_area
            },
            "isRegionDug": {
                "callback": self.is_region_dug
            },
            "entityOccupiesRegion": {
                "callback": self.entity_occupies_region
            }
        }

    # DEBUG
    def name(self, x, y, z):
        return self.handle.get_name()


    # Get a plane on the map, by name
    def get_plane(self, params, control_center, universe):

        # Try to get plane
        plane = self.handle.get_plane_by_name(
            params[0].evaluate(control_center, universe)
        )


        # Found it?
        if (plane):

            # Wrap it in a plane result object
            return Plane(plane)

        # 404
        else:
            return None


    # Get map's name
    def get_name(self, params, control_center, universe):

        # Return name
        return self.handle.get_name()


    # Set map params.  Takes a hash.
    def set_params(self, params, control_center, universe):

        # Update params
        self.handle.set_params( params[0].evaluate(control_center, universe) )

        # For chaining
        return self


    # Get a specific map param.
    def get_param(self, params, control_center, universe):

        # Return param (thus, no chaining!)
        return self.handle.get_param(
            params[0].evaluate(control_center, universe)
        )


    # Set wave params for the map's wave tracker
    def set_wave_params(self, params, control_center, universe):

        # Update params
        self.handle.get_wave_tracker().set_wave_params( params[0].evaluate(control_center, universe) )

        # This is, no doubt, a bit of a hack.
        # When we set wave params, we might enable gold rotation.  This function call
        # will set up the map for just that, if necessary.
        if ( "gold-rotation-size" in params[0].evaluate(control_center, universe) ):

            self.handle.prepare_gold_rotation(control_center, universe)

        # For chaining
        return self


    # Set wave requirements for the map's wave tracker
    def set_wave_requirements(self, params, control_center, universe):

        # Update requirements
        self.handle.get_wave_tracker().set_wave_requirements( params[0].evaluate(control_center, universe) )

        # For chaining
        return self


    # Set a single wave requirement
    def set_wave_requirement(self, params, control_center, universe):

        # Increment
        self.handle.get_wave_tracker().set_wave_requirement(
            params[0].evaluate(control_center, universe),
            int( params[1].evaluate(control_center, universe) )
        )

        # For chaining
        return self


    # Set wave allowances for the map's wave tracker
    def set_wave_allowances(self, params, control_center, universe):

        # Update allowances
        self.handle.get_wave_tracker().set_wave_allowances( params[0].evaluate(control_center, universe) )

        # For chaining
        return self


    # Set wave limits for the map's wave tracker
    def set_wave_limits(self, params, control_center, universe):

        # Update limits
        self.handle.get_wave_tracker().set_wave_limits( params[0].evaluate(control_center, universe) )

        # For chaining
        return self


    # Get the value of a given wave counter
    def get_wave_counter(self, params, control_center, universe):

        # Return value
        return self.handle.get_wave_tracker().get_wave_counter( params[0].evaluate(control_center, universe) )


    # Get the value of a given wave allowance
    def get_wave_allowance(self, params, control_center, universe):

        # Return value
        return self.handle.get_wave_tracker().get_wave_allowance( params[0].evaluate(control_center, universe) )


    # Increment a given wave allowance (script convenience function)
    def increment_wave_allowance(self, params, control_center, universe):

        # Increment
        self.handle.get_wave_tracker().set_wave_allowance(
            params[0].evaluate(control_center, universe),
            self.handle.get_wave_tracker().get_wave_allowance( params[0].evaluate(control_center, universe) ) + int( params[1].evaluate(control_center, universe) )
        )

        # For chaining
        return self


    # Import a given global script
    def import_script(self, params, control_center, universe):

        # Which script should we import from the Universe?
        name = params[0].evaluate(control_center, universe)

        # Validate that the script exists in the Universe
        if ( name in universe.scripts ):

            # Import it to this Map
            self.handle.scripts[name] = universe.scripts[name]


        # For chaining
        return self


    # Run a given script on this map, by name
    def run_script(self, params, control_center, universe):

        # Run the script
        self.handle.run_script(
            params[0].evaluate(control_center, universe),
            control_center,
            universe
        )

        # This method never supports chaining
        return None


    # Execute a given script's data immediately.
    # Fails to complete any blocking calls.
    def execute_script(self, params, control_center, universe):

        # Run the script
        self.handle.execute_script(
            params[0].evaluate(control_center, universe),
            control_center,
            universe
        )

        # This method never supports chaining
        return None


    # Begin a new wave, usually a wave in a challenge room.
    def begin_wave(self, params, control_center, universe):

        # Default settings.  For now, we just hack in the map's overview param.  (?)
        options = {
            "overview": self.handle.get_param("overview")
        }

        # Add a wave intro menu
        control_center.get_menu_controller().add(
            control_center.get_widget_dispatcher().create_wave_intro_menu().configure(
                options
            )
        )

        # Engage the menu controller's pause lock
        control_center.get_menu_controller().configure({
            "pause-locked": True
        })

        # For chaining
        return self


    # End a wave, resetting the wave tracker to default settings
    def end_wave(self, params, control_center, universe):

        # Simply reset the wave tracker
        self.handle.reset_wave_tracker()

        # For chaining
        return self


    # Show the map's "wave progress chart"
    def show_wave_progress_chart(self, params, control_center, universe):

        # Get the wave tracker
        wave_tracker = self.handle.get_wave_tracker()

        # (?) We may already be showing a wave progress chart.  If so, for now let's just remove it...
        control_center.get_menu_controller().remove_menu_by_id("wave-progress-chart")

        # Add a wave progress chart menu to the menu controller
        control_center.get_menu_controller().add(
            control_center.get_widget_dispatcher().create_wave_progress_chart().configure({
                "id": "wave-progress-chart",
                "tracked-requirement-names": wave_tracker.get_active_wave_requirement_names(),
                "tracked-limit-names": wave_tracker.get_active_wave_limit_names(),
                "tracked-allowance-names": wave_tracker.get_active_wave_allowance_names()
            })
        )

        z = {
            "id": "wave-progress-chart",
            "tracked-requirement-names": wave_tracker.get_active_wave_requirement_names(),
            "tracked-limit-names": wave_tracker.get_active_wave_limit_names(),
            "tracked-allowance-names": wave_tracker.get_active_wave_allowance_names()
        }
        #print z
        #print 5/0


        # For chaining
        return self


    # Spawn a random enemy onto the map.
    # We can optionally give him a name, disposable setting, etc.
    def spawn_random_enemy(self, params, control_center, universe):

        # Default settings
        options = {
            "disposable": True,
            "name": "",
            "respawn-region": ""
        }

        # Check for explicitly provided settings, if/a
        if ( len(params) == 1 ):

            # Update options
            options.update(
                params[0].evaluate(control_center, universe)
            )

        # Spawn the enemy
        enemy = self.handle.create_random_enemy(
            is_disposable = options["disposable"],
            name = options["name"]
        )

        # Validate
        if (enemy):

            # Hack?  Update respawn region
            enemy.respawn_region_name = options["respawn-region"]


        # For chaining
        return self


    # Spawn multiple random enemies using a given settings hash
    def spawn_random_enemies(self, params, control_center, universe):

        # How many?
        count = int( params[0].evaluate(control_center, universe) )


        # Default settings
        options = {
            "disposable": True,
            "name": "",
            "respawn-region": ""
        }

        # Check for explicitly provided settings, if/a
        if ( len(params) == 2 ):

            # Update options
            options.update(
                params[1].evaluate(control_center, universe)
            )


        # Spawn the enemies
        for i in range(0, count):

            enemy = self.handle.create_random_enemy(
                is_disposable = options["disposable"],
                name = options["name"]
            )

            # Validate
            if (enemy):

                # Hack?  Update respawn region
                enemy.respawn_region_name = options["respawn-region"]


        # For chaining
        return self


    # Count the number of enemies currently active on the map
    def count_enemies(self, params, control_center, universe):

        # Simple count
        return len( self.handle.get_entities_by_type(GENUS_ENEMY) )


    # Kill enemies, but let them respawn
    def kill_enemies(self, params, control_center, universe):

        # Remove the random enemies
        self.handle.kill_enemies(control_center, universe)

        # For chaining
        return self


    # Kill enemies that are carrying gold
    def kill_enemies_with_gold(self, params, control_center, universe):

        # Remove the random enemies
        self.handle.kill_enemies_with_gold(control_center, universe)

        # For chaining
        return self


    # Kill and remove all enemies from the current map.
    def remove_enemies(self, params, control_center, universe):

        # Remove the random enemies
        self.handle.remove_random_enemies(control_center, universe)

        # For chaining
        return self


    # Scale speed for all enemies on the current map
    def scale_enemies_speed(self, params, control_center, universe):

        # Scale speed on all enemies
        self.handle.scale_enemies_speed(
            float( params[0].evaluate(control_center, universe) )
        )

        # For chaining
        return self


    # Count the number of gold pieces currently on the map
    def count_gold(self, params, control_center, universe):

        # Count
        return self.handle.get_gold_count()


    # Enable all gold on the map
    def enable_all_gold(self, params, control_center, universe):

        # Enable all
        self.handle.enable_all_gold_pieces(control_center, universe)

        # For chaining
        return self


    # Disable all gold on the map
    def disable_all_gold(self, params, control_center, universe):

        # Disable all
        self.handle.disable_all_gold_pieces(control_center, universe)

        # For chaining
        return self


    # Dig a given area (i.e. trigger) of the map.
    # Optional 2nd parameter will contain a hash of settings.
    def dig_area(self, params, control_center, universe):

        # Default settings
        options = {
            "purge": False,
            "force": False
        }

        # Check for optional overwrite(s)
        if ( len(params) == 2 ):

            # Update
            options.update(
                params[1].evaluate(control_center, universe)
            )


        # Get the target area
        trigger = self.handle.get_trigger_by_name(
            params[0].evaluate(control_center, universe)
        )


        # Validate
        if (trigger):

            # Get coordinates (convenience?)
            (tx, ty) = (trigger.x, trigger.y)

            # Dimensions
            (w, h) = (trigger.width, trigger.height)

            # Dig all tiles in the specified target...
            for y in range(ty, ty + h):

                for x in range(tx, tx + w):

                    # Dig the given tile
                    result = self.handle.dig_tile_at_tile_coords(
                        x,
                        y,
                        purge = False,                  # False at first.  If script specified purge, we'll do that in a moment...
                        scripted_dig = True,
                        force_dig = options["force"]
                    )

                    # Did we successfully dig that tile?  (Or, are we forcing the dig?)
                    if ( (options["force"] == True) or (result == DIG_RESULT_SUCCESS) ):

                        # If the script requested that we also purge the tile, call dig_tile again with purge enabled.
                        # (If we had done this the first time, we would not have seen the dig effect.)
                        if (options["purge"]):

                            # Purge the given tile
                            self.handle.dig_tile_at_tile_coords(
                                x,
                                y,
                                purge = True,
                                scripted_dig = True,
                                force_dig = True        # **Hack to force digging of empty tile
                            )


        # For chaining
        return self


    # Check to see if a given trigger region is entirely dug (i.e. no diggable tiles remaining).
    def is_region_dug(self, params, control_center, universe):

        # Get the target area
        trigger = self.handle.get_trigger_by_name(
            params[0].evaluate(control_center, universe)
        )


        # Validate
        if (trigger):

            # Get coordinates (convenience?)
            (tx, ty) = (trigger.x, trigger.y)

            # Dimensions
            (w, h) = (trigger.width, trigger.height)

            # Check all tiles in the given region
            for y in range(ty, ty + h):
                for x in range(tx, tx + w):

                    # If this tile is currently diggable, then we haven't dug it away (or it has refilled)
                    if ( self.handle.master_plane.check_collision(x, y) == COLLISION_DIGGABLE ):

                        # Not dug
                        return 0


        # All dug (or no trigger found by the given name)
        return 1


    # Check to see if a given entity (by name) occupies a given trigger region (also by name)
    def entity_occupies_region(self, params, control_center, universe):

        # Get the enitty first
        entity = self.handle.get_entity_by_name(
            params[0].evaluate(control_center, universe)
        )

        # Validate entity
        if (entity):

            # Get the trigger
            trigger = self.handle.get_trigger_by_name(
                params[1].evaluate(control_center, universe)
            )

            # Validate trigger
            if (trigger):

                # Check intersection...
                if ( intersect( entity.get_rect(), trigger.get_rect() ) ):

                    # Yep
                    return 1

                else:

                    # Nope
                    return 0


        # Validation falied, return false always
        return 0


# A query result wrapper for a map plane object
class Plane(Generic):

    # Feed the plane object as handle
    def __init__(self, handle):

        Generic.__init__(self)

        # Keep handle
        self.handle = handle

        # Define methods
        self.commands = {
            "enable": {
                "callback": self.enable
            },
            "disable": {
                "callback": self.disable
            },
            "isActive": {
                "callback": self.is_active
            },
            "demolish": {
                "callback": self.demolish
            },
            "shiftTo": {
                "callback": self.shift_to
            },
            "shiftToX": {
                "callback": self.shift_to_x
            },
            "shiftToY": {
                "callback": self.shift_to_y
            },
            "slide": {
                "callback": self.slide
            }
        }


        # A flag to indicate that we haven't performed preprocessing for the planar shift
        self.preprocessing_complete = False

        # The planar shift may carry certain entities (players, enemies, gold, etc.) like an elevator
        self.affected_entities = []


    # Enable plane
    def enable(self, params, control_center, universe):

        # Intended only for decorative planes
        self.handle.active = True


    # Disable plane
    def disable(self, params, control_center, universe):

        # Intended only for decorative planes
        self.handle.active = False


    # Check active state
    def is_active(self, params, control_center, universe):

        # Return a 0 or a 1
        return ( 1 if (self.handle.active) else 0 )


    # Demolish a plane (destroy the single tile and disable it)
    def demolish(self, params, control_center, universe):

        # First, destroy the one tile (hack, assumption)
        self.handle.dig_tile_at_tile_coords(0, 0, purge = True, scripted_dig = True, duration_multiplier = 1, force_dig = True)

        # Now, disable this plane
        self.disable(params, control_center, universe)


    # Convenience functions
    def shift_to_x(self, params, control_center, universe):
        return self.shift_to(params, control_center, universe, shift_type = "x")

    def shift_to_y(self, params, control_center, universe):
        return self.shift_to(params, control_center, universe, shift_type = "y")


    # Shift to a given trigger location (or try to!)
    def shift_to(self, params, control_center, universe, shift_type = "xy"):

        logn( "script object debug", (self.handle.name, shift_type, self.handle.x, self.handle.y, self.handle.shift_x, self.handle.shift_y) )

        # Fetch active map
        m = universe.get_active_map()


        # For security, let's destroy any existing magic wall on the map first...
        m.destroy_magic_wall()


        # Get the plane that will be shifting...
        shifting_plane = self.handle#m.get_plane_by_name(e.node.get_attribute("plane"))

        # Make sure that (a) no plane is already in mid-shift, or
        #                (b) this plane is the plane in mid-shift
        midshift_plane = m.get_plane_in_midshift()


        # (?) (old code)
        """
        if (False and midshift_plane):

            # We're going to have to wait our turn...
            if (midshift_plane != shifting_plane):
                #return False
                pass
        """



        # Validate that we found the plane...
        if (shifting_plane):

            # At the beginning of a planar shift, we must for each and every entity
            # calculate which, if any, plane the entity is standing on.  Tiebreaker
            # goes to the highest plane.
            #if (e.cached_result != "setup-complete"):
            #if (not self.preprocessing_complete):
            if ( int( universe.get_session_variable("tmp.link.frames").get_value() ) == 1 ):

                # Implicitly set map status to cutscene
                m.cutscene_on()

                # Set a temporary param calling "shifting" on the current plane
                self.handle.set_param("-shifting", True)


                # Reset the plane's stowaways list
                self.handle.shift_stowaways = []


                # Loop all eligible entities, finding any entity that should ride along with the shifting plane (i.e. stowaway)
                log2( "Checking for affected entities..." )
                #for genus in (GENUS_PLAYER, GENUS_ENEMY, GENUS_NPC, GENUS_GOLD, GENUS_BOMB):#, GENUS_LEVER):
                for genus in (GENUS_PLAYER, GENUS_ENEMY, GENUS_NPC, GENUS_BOMB):#, GENUS_LEVER):

                    # Loop all entities of the current genus
                    for entity in m.master_plane.entities[genus]:

                        # Assume
                        affected = False

                        # Test collision against each plane in the map...
                        for z in range(0, len(m.planes)):

                            # We need to offset the entity rectangle according to the relative position of the plane
                            r = offset_rect( entity.get_rect(), x = -1 * (m.planes[z].x * TILE_WIDTH), y = -1 * (m.planes[z].y * TILE_HEIGHT) )

                            if (genus == GENUS_GOLD and entity.name == "gold-special"):
                                log( "1)  ", r )

                            # Now, we'll also offset the rect's height down by 1 pixel; this will tell us whether or not friction should affect them
                            r = offset_rect(r, x = -1 * int(m.planes[z].shift_x), y = -1 * int(m.planes[z].shift_y), h = 1)

                            if (genus == GENUS_GOLD and entity.name == "gold-special"):
                                log( "2)  ", r )

                            if (genus == GENUS_GOLD and entity.name == "gold-special"):
                                log( "\n" )#"comparison)  ", r

                            # Test!
                            if (m.planes[z].check_fall_collision_in_rect(r)):

                                # Is this on the shifting plane?
                                if (shifting_plane == m.planes[z]):
                                    affected = True # For now...

                                else:
                                    affected = False # If a higher plane has friction, it will win...

                            # Trapped enemies will go along for the ride...
                            elif (m.planes[z].contains_trapped_entity(entity)):

                                if (shifting_plane == m.planes[z]):
                                    affected = True

                                else:
                                    affected = False


                        # Stowaway setting does always override z-index...
                        if (entity in shifting_plane.shift_stowaways):
                            affected = True



                        # Will this plane's movement affect the entity?
                        if (affected):

                            # Round to current on-screen position
                            entity.y = entity.get_y()

                            #e.params["-affected-entities"].append(entity)
                            self.handle.shift_stowaways.append(entity)#self.affected_entities.append(entity)

                log2( "affected:  ", self.handle.shift_stowaways )


                # Set the shifting plane's flag to True
                shifting_plane.is_shifting = True



                # Distribute the master plane's trap data to the individual planes...
                m.distribute_master_trap_data_to_shifting_plane(self.handle)

                # We also want to update the master plane... it won't be rendering this particular plane any more...
                #m.update_master_plane()
                m.remove_plane_from_master_plane(self.handle)




                # Setup is complete
                self.preprocessing_complete = True



            # Let us shift the plane!  Set default targets to the current location...
            x_target = (shifting_plane.x * TILE_WIDTH) + shifting_plane.shift_x
            y_target = (shifting_plane.y * TILE_HEIGHT) + shifting_plane.shift_y

            t = m.get_trigger_by_name(
                params[0].evaluate(control_center, universe)
            )

            """
            if (t):
                x_target = (t.x * TILE_WIDTH)
                y_target = (t.y * TILE_HEIGHT)

            # Check parameters
            if ("x" in e.node.attributes):
                x_target = int( float(e.node.get_attribute("x")) * TILE_WIDTH )

            if ("y" in e.node.attributes):
                y_target = int( float(e.node.get_attribute("y")) * TILE_HEIGHT ) 
            """


            # Validate trigger
            if (t):

                # x-only shift?
                if (shift_type == "x"):
                    x_target = (t.x * TILE_WIDTH)

                # y-only shift?
                elif (shift_type == "y"):
                    y_target = (t.y * TILE_HEIGHT)

                # both
                else:

                    x_target = (t.x * TILE_WIDTH)
                    y_target = (t.y * TILE_HEIGHT)


            # Defaults
            (speed, ghost) = (
                1.0,
                False
            )

            # Check explicit speed (param 2)
            if ( len(params) > 1 ):
                speed = float( params[1].evaluate(control_center, universe) )

            # Check collision status (param 3)
            if ( len(params) > 2 ):
                ghost = ( int( params[2].evaluate(control_center, universe) ) == 0 )

            # Check 


            # Sanity; shift speed must exceed 0
            if (speed <= 0):
                speed = 1.0


            """
            ## By default, a plane can shift through other tiles.  If the attribute is specified as colliding, though, then it collides...
            #ghost = (int( e.node.get_attribute("collides") ) == 0)
            """


            # Is this plane still shifting?
            if ( self.handle.get_param("-shifting") == True ):

                #shift_complete = shifting_plane.shift_to_target(x_target, y_target, speed, ghost, e.params["-affected-entities"], m)
                shift_complete = shifting_plane.shift_to_target(x_target, y_target, speed, ghost, self.affected_entities, m)

                # If the shift has completed, then let's toggle the flag and update the master plane...
                if (shift_complete == True):

                    shifting_plane.dx = 0
                    shifting_plane.dy = 0

                    # Remember which entities are still affected by this plane's shifting...
                    shifting_plane.shift_stowaways = self.affected_entities#e.params["-affected-entities"]

                    shifting_plane.is_shifting = False


                    # No more stowaways; this ride is over!
                    shifting_plane.shift_stowaways = []


                    for z in self.affected_entities:#e.params["-affected-entities"]:
                        log( z.name, " = ", z.y )


                    # Occasionally I might (?!) set plane shifts to end at uneven intervals.  When this happens, I don't update the master plane.
                    # The script MUST return the plane to an even interval, or the plane will not rejoin the master plane.
                    #if ( (shifting_plane.shift_x % TILE_WIDTH == 0) and (shifting_plane.shift_y % TILE_HEIGHT == 0) ):
                    if ( (shifting_plane.shift_x % TILE_WIDTH == 0) and (shifting_plane.shift_y % TILE_HEIGHT == 0) ):


                        # Update the master plane
                        #m.update_master_plane()
                        m.merge_plane_into_master_plane(self.handle)

                        # Return trap data tracking from the individual planes to the master plane...
                        #m.recollect_master_trap_data_from_shifting_plane(self.handle)

                        m.master_plane.build_gold_cache()




                    # Implicitly end map cutscene mode
                    m.cutscene_off()

                    # Set local sliding flag to False
                    self.handle.set_param("-shifting", False)


                    # Done...
                    return EXECUTE_RESULT_DONE

                # Still shifting...
                else:
                    return EXECUTE_RESULT_PENDING


            # This plane previously completed its slide.  If we're calling this again (e.g. simultaneous script call),
            # we'll just confirm that we're already done.
            else:
                return EXECUTE_RESULT_DONE


    # Slide up/down (horizontal slides not supported currently)
    def slide(self, params, control_center, universe):

        # Fetch active map
        m = universe.get_active_map()


        # For security, let's destroy any existing magic wall on the map first...
        m.destroy_magic_wall()


        # Which plane will slide?
        sliding_plane = self.handle#m.get_plane_by_name(e.node.get_attribute("plane"))

        # Defaults
        (direction, amount, speed, target_name) = (
            DIR_UP,       # Slide direction
            -1,           # Amount to slide (-1 to use full plane height)
            1.0,          # Slide rate
            None          # Trigger to slide to
        )


        # Translations from human-readable params
        translations = {
            "up": DIR_UP,
            "right": DIR_RIGHT,
            "down": DIR_DOWN,
            "left": DIR_LEFT
        }


        # Absolute slide?
        if ( params[0].evaluate(control_center, universe) == "absolute" ):

            # Human-readable direction
            key = params[1].evaluate(control_center, universe)

            # Get direction after validating key
            if (key in translations):

                # Update
                direction = translations[key]


            # Get absolute slide amount
            amount = int( params[2].evaluate(control_center, universe) )

            # Optional speed
            if ( len(params) > 3 ):

                # Update
                speed = float( params[3].evaluate(control_center, universe) )


        # Targeted slide?
        elif ( params[0].evaluate(control_center, universe) == "targeted" ):

            pass


        """
        # Which direction will it slide?  (Will it slide toward a target, or to 100% up/down?
        #    1)  "up"
        #    2)  "up.targeted"
        pieces = e.node.get_attribute("slide").split(".")

        slide = 0
        target_name = None

        if (len(pieces) == 1):
            slide = int( pieces[0] )

        else:
            slide = -1 # We won't send this data; the plane will compute it on-the-fly
            target_name = e.node.get_attribute("target") # The name of the trigger

        # Slide speed...
        speed = float( e.node.get_attribute("speed") )
        """


        # Validate
        if (sliding_plane):

            # Sliding up is easy...
            if (direction == DIR_UP or direction == -1):

                # On the first frame, we should flag the plane as sliding and such
                #if (e.cached_result != "done"):
                if ( int( universe.get_session_variable("tmp.link.frames").get_value() ) == 1 ):

                    # Activate flags (?)
                    sliding_plane.is_sliding = True
                    sliding_plane.active = True

                    # Implicitly begin cutscene
                    m.cutscene_on()

                    # Set a temporary param calling "sliding" on the current plane
                    self.handle.set_param("-sliding", True)


                    # Remove this plane from the master plane
                    m.remove_plane_from_master_plane(self.handle)


                # Is the plane still sliding?
                if ( self.handle.get_param("-sliding") == True ):

                    # Slide the plane...
                    result = sliding_plane.planar_slide(direction, speed, target_name, m, amount)

                    # Slide done?  If so, let's unflag the is_sliding attribute...
                    if (result):


                        # Now IF the plane has slid up, we should deactivate it...
                        if (sliding_plane.slide_y == 0):
                            sliding_plane.active = False


                        # If the slide has definitively concluded, we can disable is_sliding to save a scissor test...
                        if (sliding_plane.slide_y == 0 or sliding_plane.slide_y >= (sliding_plane.get_height() * TILE_HEIGHT)):
                            sliding_plane.is_sliding = False


                        # Update the master plane
                        #m.update_master_plane()
                        m.merge_plane_into_master_plane(self.handle)


                        # Implicitly end cutscene
                        m.cutscene_off()

                        # Disable hidden sliding param
                        self.handle.set_param("-sliding", False)


                        # Done...
                        return EXECUTE_RESULT_DONE

                    else:
                        return EXECUTE_RESULT_PENDING

                # We completed the slide in a previous scripting loop iteration
                else:
                    return EXECUTE_RESULT_DONE


            # Sliding down will end up squishing entities in the way...
            elif (direction == DIR_DOWN):

                # First frame flag fun
                #if (e.cached_result != "done"):
                if ( int( universe.get_session_variable("tmp.link.frames").get_value() ) == 1 ):

                    sliding_plane.is_sliding = True

                    # Assume that we want the plane to slide down from 0 slide... (?)
                    #sliding_plane.slide_y = 0

                    # Plane is now active
                    sliding_plane.active = True


                    # Implicitly begin cutscene
                    m.cutscene_on()

                    # Set a temporary param calling "sliding" on the current plane
                    self.handle.set_param("-sliding", True)


                # Is the plane still sliding?
                if ( self.handle.get_param("-sliding") == True ):

                    # Just slide...
                    result = sliding_plane.planar_slide(direction, speed, target_name, m, amount)

                    # Done?
                    if (result):

                        sliding_plane.is_sliding = False

                        # Just to be sure
                        sliding_plane.active = True


                        # Update master plane; map state has changed.
                        #m.update_master_plane()
                        m.merge_plane_into_master_plane(self.handle)


                        # Implicitly end cutscene
                        m.cutscene_off()

                        # Disable hidden sliding param
                        self.handle.set_param("-sliding", False)


                        # Done...
                        return EXECUTE_RESULT_DONE

                    else:
                        return EXECUTE_RESULT_PENDING

                # We completed this script call in a previous script loop iteration.
                else:
                    return EXECUTE_RESULT_DONE


# A query result wrapper for a player entity.
class Player(Generic):

    # Feed player object as handle
    def __init__(self, handle):

        Generic.__init__(self)

        # Keep handle
        self.handle = handle

        # Define methods
        self.commands = {
            "addGold": {
                "callback": self.add_gold
            },
            "subtractGold": {
                "callback": self.subtract_gold
            },
            "setBombs": {
                "callback": self.set_bombs
            },
            "addBombs": {
                "callback": self.add_bombs
            },
            "addXP": {
                "callback": self.add_xp
            },
            "addSkillPoints": {
                "callback": self.add_skill_points
            },
            "hasItem": {
                "callback": self.has_item
            },
            "acquireItem": {
                "callback": self.acquire_item
            },
            "acquireRandomItem": {
                "callback": self.acquire_random_item
            },
            "dropItem": {
                "callback": self.drop_item
            },
            "colorify": {
                "callback": self.colorify
            }
        }


    # Increase a player's available gold
    def add_gold(self, params, control_center, universe):

        # Simple session update
        universe.increment_session_variable(
            "core.gold.wallet",
            int( params[0].evaluate(control_center, universe) )
        )

        # Execute the "wallet-changed" achievement hook
        universe.execute_achievement_hook( "wallet-changed", control_center )

        # For chaining
        return self


    # Lower a player's available gold
    def subtract_gold(self, params, control_center, universe):

        # Simple session update
        universe.increment_session_variable(
            "core.gold.wallet",
            -1 * int( params[0].evaluate(control_center, universe) )
        )

        # Count as gold spent
        universe.increment_session_variable(
            "stats.gold-spent",
            int( params[0].evaluate(control_center, universe) )
        )

        # Execute the "wallet-changed" achievement hook
        universe.execute_achievement_hook( "wallet-changed", control_center )

        # For chaining
        return self


    # Set a player's number of bombs (used for cooperative mode games)
    def set_bombs(self, params, control_center, universe):

        # Simple session update
        universe.get_session_variable("core.bombs.count").set_value(
            int( params[0].evaluate(control_center, universe) )
        )

        # For chaining
        return self


    # Increase a player's number of bombs
    def add_bombs(self, params, control_center, universe):

        # Simple session update
        universe.increment_session_variable(
            "core.bombs.count",
            int( params[0].evaluate(control_center, universe) )
        )

        # For chaining
        return self


    # Add XP for the player
    def add_xp(self, params, control_center, universe):

        # Increase XP on player object
        self.handle.increase_xp(
            int( params[0].evaluate(control_center, universe) ),
            control_center,
            universe
        )


        # Add an accompanying note?
        if ( len(params) > 1 ):

            # Add note text to the HUD's notes "list"
            control_center.get_window_controller().get_hud().add_notes([
                "%s" % params[1].evaluate(control_center, universe)
            ])


        # For chaining
        return self


    # Add skill points for the player to use
    def add_skill_points(self, params, control_center, universe):

        # Simple session update
        universe.increment_session_variable(
            "core.player1.skill-points",
            int( params[0].evaluate(control_center, universe) )
        )

        # For chaining
        return self


    # Check to see if the player has an item, by name.
    # Returns a boolean True/False.
    def has_item(self, params, control_center, universe):

        # Check for acquisition.  No chaining, obviously.
        return universe.is_item_acquired( params[0].evaluate(control_center, universe) )


    # Acquire a new item
    def acquire_item(self, params, control_center, universe):

        # Handle
        localization_controller = control_center.get_localization_controller()


        # Item name
        name = params[0].evaluate(control_center, universe)

        # Acquire the item
        success = universe.acquire_item_by_name(name)

        # Did we acquire it?
        if (success):

            # Post a newsfeeder item
            control_center.get_window_controller().get_newsfeeder().post({
                "type": NEWS_ITEM_NEW,
                "title": localization_controller.get_label("new-item-acquired:header"),
                "content": universe.get_item_by_name(name).get_title()
            })


            # Add a historical record
            universe.add_historical_record(
                "purchases",
                localization_controller.get_label(
                    "acquired-m-as-n",
                    {
                        "@m": localization_controller.translate( universe.get_item_by_name(name).get_title() ), # Translate explicitly
                        "@n": localization_controller.get_label("quest-reward:direct-object")                   # Implicitly translated
                    }
                )
            )

        # For chaining
        return self


    # Acquire a random item from a given list of items
    def acquire_random_item(self, params, control_center, universe):

        # Handle
        localization_controller = control_center.get_localization_controller()


        # Build a lisf of item names
        names = []

        # Loop all given params (item names)
        for param in params:

            # Item name
            name = param.evaluate(control_center, universe)

            # Don't consider it if we've already acquired it
            if ( not universe.is_item_acquired(name) ):

                # ADd it to the candidate pool
                names.append(name)


        log2( "Names:", names )
        # Can we acquire one of the given items?
        if ( len(names) > 0 ):

            # Choose one at random
            random_name = names[ random.randint( 0, len(names) - 1 ) ]

            # Acquire item
            success = universe.acquire_item_by_name(random_name)

            # Did we acquire it?
            if (success):

                # Post a newsfeeder item
                control_center.get_window_controller().get_newsfeeder().post({
                    "type": NEWS_ITEM_NEW,
                    "title": localization_controller.get_label("new-item-acquired:header"),
                    "content": universe.get_item_by_name(random_name).get_title()
                })

                # Add a historical record
                universe.add_historical_record(
                    "purchases",
                    localization_controller.get_label(
                        "acquired-m-as-n",
                        {
                            "@m": localization_controller.translate( universe.get_item_by_name(random_name).get_title() ), # Translate explicitly
                            "@n": localization_controller.get_label("quest-reward:direct-object")                   # Implicitly translated
                        }
                    )
                )


        # For chaining
        return self


    # Drop / lose / forfeit an item
    def drop_item(self, params, control_center, universe):

        # Drop the item
        universe.remove_item_from_inventory(
            params[0].evaluate(control_center, universe)
        )

        # For chaining
        return self


    # Colorify the player entity
    def colorify(self, params, control_center, universe):

        # Call to colorify
        self.handle.colorify(
            params[0].evaluate(control_center, universe)
        )

        # Remember colors
        universe.get_session_variable("core.player1.colors").set_value(
            params[0].evaluate(control_center, universe)
        )


        # For chaining
        return self


# A query result wrapper for NPC entities.
class NPC(Generic):

    # Feed game NPC (entity) object as handle.
    def __init__(self, handle):

        Generic.__init__(self)

        # Keep handle
        self.handle = handle

        # Define methods
        self.commands = {
            "status": {
                "callback": self.get_status,
                "params": 1
            },
            "setClass": {
                "callback": self.set_class
            },
            "hasClass": {
                "callback": self.has_class
            },
            "enable": {
                "callback": self.enable
            },
            "disable": {
                "callback": self.disable
            },
            "fadeIn": {
                "callback": self.fade_in
            },
            "fadeOut": {
                "callback": self.fade_out
            },
            "die": {
                "callback": self.die
            },
            "addHotspot": {
                "callback": self.add_hotspot,
                "params": 1
            },
            "addIndicator": {
                "callback": self.add_indicator
            },
            "removeIndicator": {
                "callback": self.remove_indicator
            },
            "clearIndicators": {
                "callback": self.clear_indicators
            },
            "talk": {
                "callback": self.talk
            },
            "dismissFYI": {
                "callback": self.dismiss_fyi
            },
            "killFYI": {
                "callback": self.kill_fyi
            },
            "clearWarehouses": {
                "callback": self.clear_warehouses
            },
            "addWarehouse": {
                "callback": self.add_warehouse
            },
            "clearVendorInventory": {
                "callback": self.clear_vendor_inventory
            },
            "addItemToVendorInventory": {
                "callback": self.add_item_to_vendor_inventory
            },
            "shop": {
                "callback": self.shop
            },
            "conversation": {
                "callback": self.get_conversation
            },
            "importConversation": {
                "callback": self.import_conversation
            },
            "getAllLinesByClass": {
                "callback": self.get_all_lines_by_class
            },
            "hasPosition": {
                "callback": self.has_position
            },
            "setPosition": {
                "callback": self.set_position
            },
            "setDirection": {
                "callback": self.set_direction
            }
        }


    # ?
    def get_status(self, params, control_center, universe):

        return "'%s'" % self.handle.status


    # Set an NPC's class
    def set_class(self, params, control_center, universe):

        # Set class
        self.handle.set_class(
            params[0].evaluate(control_center, universe)
        )

        # For chaining
        return self


    # Check to see if this NPC has a given class
    def has_class(self, params, control_center, universe):

        # Return boolean
        return self.handle.has_class(
            params[0].evaluate(control_center, universe)
        )


    # Enable / activate the NPC
    def enable(self, params, control_center, universe):

        # Set status to active
        self.handle.set_status(STATUS_ACTIVE)

        # For chaining
        return self


    # Disable / deactivate the NPC
    def disable(self, params, control_center, universe):

        # Set status to inactive
        self.handle.set_status(STATUS_INACTIVE)

        # For chaining
        return self


    # Fade in to view
    def fade_in(self, params, control_center, universe):

        # Fade in
        result = self.handle.fade_in()

        # Done?
        if (result):

            return EXECUTE_RESULT_DONE

        else:

            return EXECUTE_RESULT_PENDING


    # Fade out of view
    def fade_out(self, params, control_center, universe):

        # Fade out
        result = self.handle.fade_out()

        # Done?
        if (result):

            return EXECUTE_RESULT_DONE

        else:

            return EXECUTE_RESULT_PENDING


    # Kill the NPC entity
    def die(self, params, control_center, universe):

        # Queue death.  For now, let's use a generic vaporization cause...
        self.handle.queue_death_by_cause(DEATH_BY_VAPORIZATION)


    # Add a hotspot to the NPC's pathfinding hotspots
    def add_hotspot(self, params, control_center, universe):

        self.handle.add_hotspot(
            params[0].evaluate(control_center, universe)
        )

        # For chaining.  Event is always done immediately.
        return self


    # Enable a given indicator
    def add_indicator(self, params, control_center, universe):

        # Add the given indicator
        self.handle.set_indicator(
            params[0].evaluate(control_center, universe),
            True
        )


        # For chaining
        return self


    # Remove a given indicator
    def remove_indicator(self, params, control_center, universe):

        # Remove the given indicator
        self.handle.set_indicator(
            params[0].evaluate(control_center, universe),
            False
        )


        # For chaining
        return self


    # Clear all indicators
    def clear_indicators(self, params, control_center, universe):

        # Clear
        self.handle.clear_indicators()


        # For chaining
        return self


    # Initiate a conversation
    def talk(self, params, control_center, universe):

        # Get the conversation id
        conversation_id = params[0].evaluate(control_center, universe)
        logn( "script npc talk", "Talk:  %s\n" % conversation_id )


        # Assume
        style = "standard"

        # Check for optional 2nd parameter
        if ( len(params) > 1 ):

            # Update
            style = params[1].evaluate(control_center, universe)


        # Instruct the NPC to talk
        result = self.handle.talk(conversation_id, style, control_center, universe)


        # If the NPC began the given conversation successfully, we're return "done."
        # This function does not support chaining.
        if (result):

            # Done...
            return EXECUTE_RESULT_DONE

        # Otherwise, the NPC previously engaged in a conversation.  This next conversation
        # must wait for the original conversation to conclude.
        else:

            # Try again later...
            return EXECUTE_RESULT_PENDING


    # Dismiss an FYI dialogue panel (rare)
    def dismiss_fyi(self, params, control_center, universe):

        # What is the id of the FYI we want to dismiss?
        panel_id = params[0].evaluate(control_center, universe)

        # Get a reference to that fyi dialogue panel
        panel = control_center.get_menu_controller().get_menu_by_id(panel_id)

        # Validate
        if (panel):

            # Raise a "continue" event
            panel.fire_event("continue")


        # For chaining
        return self


    # Kill an FYI dialogoue panel (because dismiss runs a continue event for multi-part FYI dialogues)
    def kill_fyi(self, params, control_center, universe):

        # What is the id of the FYI we want to dismiss?
        panel_id = params[0].evaluate(control_center, universe)

        # Remove the given FYI
        control_center.get_menu_controller().remove_menu_by_id(panel_id)


        # For chaining
        return self


    # Get a given conversation
    def get_conversation(self, params, control_center, universe):

        # Check for conversation
        conversation = self.handle.get_conversation_by_id( params[0].evaluate(control_center, universe) )

        # Validate
        if (conversation):

            # Return query result wrapper
            return Conversation(conversation)

        else:

            handle_error( "Conversation Warning:  \n\tMap:  %s\n\tName:  %s" % ( universe.get_active_map().get_name(), params[0].evaluate(control_center, universe) ) ) # Debug
            return None


    # Import a conversation from the universe's collection of common conversations, by id
    def import_conversation(self, params, control_center, universe):

        # Try to get the conversation node from the universe
        node = universe.get_conversation_node(
            params[0].evaluate(control_center, universe)
        )

        # Validate
        if (node):

            # NPC should import the conversation node
            self.handle.import_conversation_from_node(node)


        # For chaining
        return self


    # Get a list of all lines in this branch matching a given class name.
    # Check every conversation and every branch for this NPC.
    def get_all_lines_by_class(self, params, control_center, universe):

        # Track results
        results = []

        # Loop through each conversation
        for conversation_id in self.handle.conversations:

            # Get all lines by the given class
            results.extend(
                self.handle.conversations[conversation_id].get_lines_by_class( params[0].evaluate(control_center, universe) )
            )



        """ In DEBUG mode, let's check to see if we have at least one match.
            If we don't, that might signal that we mistyped the desired class. """
        if (DEBUG):

            # Check count
            if ( len(results) == 0 ):

                # Possible bad param warning
                handle_error(
                    "Lines by Class Warning:  \n\tMap:  %s\n\tBranch:  %s\n\tClass Name:  %s" % ( universe.get_active_map().get_name(), "(all branches)", params[0].evaluate(control_center, universe) ) # Debug
                )
        """ End DEBUG """

        # Return matching lines, wrapped in a query result object
        return ConversationBranchLineList(results)


    # Clear NPC vendor warehouses
    def clear_warehouses(self, params, control_center, universe):

        self.handle.clear_warehouses()

        # For chaining.  Event is done immediately.
        return self


    # Add a new warehouse for the NPC vendor.
    def add_warehouse(self, params, control_center, universe):

        # Add new warehouse
        self.handle.add_warehouse(
            params[0].evaluate(control_center, universe)
        )

        # For chaining.  Event done.
        return self


    # Clear NPC vendor inventory
    def clear_vendor_inventory(self, params, control_center, universe):

        self.handle.clear_vendor_inventory()

        # For chaining.  Event is done immediately.
        return self


    # Add a new item to the NPC's inventory of items
    def add_item_to_vendor_inventory(self, params, control_center, universe):

        # Add new warehouse
        self.handle.add_item_to_vendor_inventory(
            params[0].evaluate(control_center, universe),
            universe
        )

        # For chaining.  Event done.
        return self


    # Shop with the NPC
    def shop(self, params, control_center, universe):

        # NPC will show inventory now
        self.handle.shop(
            params[0].evaluate(control_center, universe),
            control_center,
            universe
        )


    # Check to see if an entity (typically a lever) has a given position
    def has_position(self, params, control_center, universe):

        # Translations from human-readable params
        translations = {
            "up": DIR_UP,
            "right": DIR_RIGHT,
            "down": DIR_DOWN,
            "left": DIR_LEFT
        }

        # Validate that we're calling this on a lever
        if (self.handle.genus == GENUS_LEVER):

            # Get human-readable param
            key = params[0].evaluate(control_center, universe)

            # Validate key
            if (key in translations):

                if ( self.handle.position == translations[key] ):
                    return "1"

                else:
                    return "0"

            else:
                return "0"

        # Other entity types currently return 0 (?)
        else:
            return "0"


    # Set an entity's position (typically a lever)
    def set_position(self, params, control_center, universe):

        # Translations from human-readable params
        translations = {
            "up": DIR_UP,
            "right": DIR_RIGHT,
            "down": DIR_DOWN,
            "left": DIR_LEFT
        }

        # Validate that we're calling this on a lever
        if (self.handle.genus == GENUS_LEVER):

            # Get human-readable param
            key = params[0].evaluate(control_center, universe)

            # Validate key
            if (key in translations):

                # Update position
                self.handle.set_position( translations[key] )


        # Other entity types currently return 0 (?)
        else:
            pass


        # For chaining
        return self


    # Set the NPC's direction property
    def set_direction(self, params, control_center, universe):

        # Translations from human-readable params
        translations = {
            "up": DIR_UP,
            "right": DIR_RIGHT,
            "down": DIR_DOWN,
            "left": DIR_LEFT
        }

        # Get human-readable param
        key = params[0].evaluate(control_center, universe)

        # Validate key
        if (key in translations):

            # Set direction
            self.handle.set_direction( translations[key] )


        # For chaining
        return self


# A list of NPC entity objects
class NPCResultList(Generic):

    # Feed list of NPC objects for handles
    def __init__(self, handles):

        Generic.__init__(self)

        # Keep handles
        self.handles = handles

        # Define methods
        self.commands = {
            "count": {
                "callback": self.count
            },
            "slice": {
                "callback": self.get_slice
            }
        }


    # Count results
    def count(self, params, control_center, universe):

        logn( "script object debug", "Debug mes:  ", self.handles, len(self.handles) )
        # Return simple count
        return len(self.handles)


    # Get a range of results
    def get_slice(self, params, control_center, universe):

        # We need at least 2 params
        try:

            # Get range
            (a, b) = (
                int( params[0].evaluate(control_center, universe) ),
                int( params[1].evaluate(control_center, universe) )
            )

            # Return range, wrapped in a query result list
            return NPCResultList( self.handles[a:b] )

        # In the event of an error, return an empty list
        except:

            log2( "Warning:  Invalid parameters sent to get_slice()" )
            return []


# A query result wrapper for NPC conversations
class Conversation(Generic):

    # Feed conversation object as handle
    def __init__(self, handle):

        Generic.__init__(self)

        # Keep handle
        self.handle = handle

        # Define methods
        self.commands = {
            "branch": {
                "callback": self.get_branch
            }
        }


    # Get a branch in this conversation, by id
    def get_branch(self, params, control_center, universe):

        # Search for the line object
        branch = self.handle.get_branch_by_id( params[0].evaluate(control_center, universe) )

        # Validate
        if (branch):

            # Return query result wrapper
            return ConversationBranch(branch)

        else:

            handle_error( "Branch Warning:  \n\tMap:  %s\n\tName:  %s" % ( universe.get_active_map().get_name(), params[0].evaluate(control_center, universe) ) ) # Debug
            return None


# A query result for a conversation branch
class ConversationBranch(Generic):

    # Feed branch object as handle
    def __init__(self, handle):

        Generic.__init__(self)

        # Keep handle
        self.handle = handle

        # Define methods
        self.commands = {
            "line": {
                "callback": self.get_line
            },
            "getLinesByClass": {
                "callback": self.get_lines_by_class
            }
        }


    # Get a given line, by line ID.
    def get_line(self, params, control_center, universe):

        # Search for the line object
        line = self.handle.get_line_by_id( params[0].evaluate(control_center, universe) )

        # Validate
        if (line):

            # Return query result wrapper
            return ConversationBranchLine(line)

        else:

            handle_error( "Branch Line Warning:  \n\tMap:  %s\n\tName:  %s" % ( universe.get_active_map().get_name(), params[0].evaluate(control_center, universe) ) ) # Debug
            return None


    # Get a list of all lines in this branch matching a given class name
    def get_lines_by_class(self, params, control_center, universe):

        """ In DEBUG mode, let's check to see if we have at least one match.
            If we don't, that might signal that we mistyped the desired class. """
        if (DEBUG):

            # Check count
            if ( len( self.handle.get_lines_by_class( params[0].evaluate(control_center, universe) ) ) == 0 ):

                # Possible bad param warning
                handle_error(
                    "Lines by Class Warning:  \n\tMap:  %s\n\tBranch:  %s\n\tClass Name:  %s" % ( universe.get_active_map().get_name(), self.handle.id, params[0].evaluate(control_center, universe) ) # Debug
                )
        """ End DEBUG """

        # Return matching lines, wrapped in a query result object
        return ConversationBranchLineList(
            self.handle.get_lines_by_class( params[0].evaluate(control_center, universe) )
        )


# A query result for single lines in an NPC conversation branch
class ConversationBranchLine(Generic):

    # Feed line object as handle
    def __init__(self, handle):

        Generic.__init__(self)

        # Keep handle
        self.handle = handle

        # Define methods
        self.commands = {
            "response": {
                "callback": self.get_response,
            },
            "getResponsesByClass": {
                "callback": self.get_responses_by_class
            },
            "enable": {
                "callback": self.enable
            },
            "disable": {
                "callback": self.disable
            },
            "lock": {
                "callback": self.lock
            }
        }


    # Get a single response, by response id
    def get_response(self, params, control_center, universe):

        # Look for response
        response = self.handle.get_response_by_id( params[0].evaluate(control_center, universe) )

        # Validate
        if (response):

            # Return query result wrapper
            return ConversationBranchLineResponse(response)

        else:

            handle_error( "Line Response Warning:  \n\tMap:  %s\n\tName:  %s" % ( universe.get_active_map().get_name(), params[0].evaluate(control_center, universe) ) ) # Debug
            return None


    # Get a list of all responses having a given class name
    def get_responses_by_class(self, params, control_center, universe):

        """ In DEBUG mode, let's check to see if we have at least one match.
            If we don't, that might signal that we mistyped the desired class. """
        if (DEBUG):

            # Check count
            if ( len( self.handle.get_responses_by_class( params[0].evaluate(control_center, universe) ) ) == 0 ):

                # Possible bad param warning
                handle_error(
                    "Responses by Class Warning:  \n\tMap:  %s\n\tLine:  %s\n\tClass Name:  %s" % ( universe.get_active_map().get_name(), self.handle.id, params[0].evaluate(control_center, universe) ) # Debug
                )
        """ End DEBUG """

        # Return results in a query result wrapper
        return ConversationBranchLineResponseList(
            self.handle.get_responses_by_class( params[0].evaluate(control_center, universe) )
        )


    # Enable this line
    def enable(self, params, control_center, universe):

        # Enable
        self.handle.enable()

        # For chaining
        return self


    # Disable this line
    def disable(self, params, control_center, universe):

        # Disable
        self.handle.disable()

        # For chaining
        return self


    # Lock this line
    def lock(self, params, control_center, universe):

        # Lock
        self.handle.lock()

        # For chaining
        return self


# A query result for a group of lines in an NPC conversation branch
class ConversationBranchLineList(Generic):

    # Feed line list as param
    def __init__(self, l):

        Generic.__init__(self)

        # Keep list of handles
        self.handles = l

        # Define methods
        self.commands = {
            "enable": {
                "callback": self.enable
            },
            "disable": {
                "callback": self.disable
            },
            "lock": {
                "callback": self.lock
            },
            "getResponsesByClass": {
                "callback": self.get_responses_by_class
            },
            "selectRandom": {
                "callback": self.select_random
            },
            "selectActive": {
                "callback": self.select_active
            },
            "countActive": {
                "callback": self.count_active
            },
            "countUnread": {
                "callback": self.count_unread
            }
        }


    # Enable all matched lines
    def enable(self, params, control_center, universe):

        # No param needed
        for handle in self.handles:

            # Enable
            handle.enable()

        # For chaining
        return self


    # Disable all matched lines
    def disable(self, params, control_center, universe):

        # No param needed
        for handle in self.handles:

            # Disable
            handle.disable()

        # For chaining
        return self


    # Lock all matches lines
    def lock(self, params, control_center, universe):

        # No param needed
        for handle in self.handles:

            # Lock
            handle.lock()

        # For chaining
        return self


    # Get a list of all responses having a given class name, across all matched lines.
    def get_responses_by_class(self, params, control_center, universe):

        # Track all of the responses we find
        results = []

        # Loop all matching lines
        for handle in self.handles:

            # Find matching responses
            results.extend(
                handle.get_responses_by_class( params[0].evaluate(control_center, universe) )
            )

        # Return results in a query result wrapper
        return ConversationBranchLineResponseList(results)


    # Select "n" of the matched lines at random
    def select_random(self, params, control_center, universe):

        # How many should we return?
        n = int( params[0].evaluate(control_center, universe) )

        # Track results
        results = []


        # Select random winners
        while ( ( len(self.handles) > 0 ) and ( len(results) < n ) ):

            # Pick a random line
            index = random.randint( 0, len(self.handles) - 1 )

            # Add it to results
            results.append(
                self.handles.pop(index)
            )


        # Return results, wrapped in a query result wrapper
        return ConversationBranchLineList(results)


    # Select only the active lines within the matched lines
    def select_active(self, params, control_center, universe):

        # Track results
        results = []

        # Loop matched lines
        for handle in self.handles:

            # Is the line active?
            if (handle.active):

                # Add to results
                results.append(handle)

        # Return results, wrapped in a query result wrapper
        return ConversationBranchLineList(results)


    # Count how many active lines exist in the matched lines
    def count_active(self, params, control_center, universe):

        # Total
        count = 0

        # Loop matched lines
        for handle in self.handles:

            # Is line unread?
            if (handle.active):

                # Increment counter
                count += 1

        # Return count
        return count


    # Count how many of the matched lines remain unread
    def count_unread(self, params, control_center, universe):

        # Total
        count = 0

        # Loop matched lines
        for handle in self.handles:

            # Is line unread?
            if (handle.unread):

                # Increment counter
                count += 1

        # Return count
        return count


# A query result for a single line response
class ConversationBranchLineResponse(Generic):

    # Feed response object as handle
    def __init__(self, handle):

        Generic.__init__(self)

        # Keep handle
        self.handle = handle

        # Define methods
        self.commands = {
            "enable": {
                "callback": self.enable
            },
            "disable": {
                "callback": self.disable
            }
        }


    # Enable this response
    def enable(self, params, control_center, universe):

        # Enable
        self.handle.enable()


    # Disable this response
    def disable(self, params, control_center, universe):

        # Disable
        self.handle.disable()


# A query result for a list of line responses
class ConversationBranchLineResponseList(Generic):

    # Feed response list as param
    def __init__(self, l):

        Generic.__init__(self)

        # Keep list of handles
        self.handles = l

        # Define methods
        self.commands = {
            "enable": {
                "callback": self.enable
            },
            "disable": {
                "callback": self.disable
            },
            "selectRandom": {
                "callback": self.select_random
            }
        }


    # Enable all matched responses
    def enable(self, params, control_center, universe):

        # No param needed
        for handle in self.handles:

            # Enable
            handle.enable()


    # Disable all matched responses
    def disable(self, params, control_center, universe):

        # No param needed
        for handle in self.handles:

            # Disable
            handle.disable()


    # Select "n" of the matched responses at random
    def select_random(self, params, control_center, universe):

        # How many should we return?
        n = int( params[0].evaluate(control_center, universe) )

        # Track results
        results = []


        # Select random winners
        while ( ( len(self.handles) > 0 ) and ( len(results) < n ) ):

            # Pick a random item
            index = random.randint( 0, len(self.handles) - 1 )

            # Add it to results
            results.append(
                self.handles.pop(index)
            )


        # Return results, wrapped in a query result wrapper
        return ConversationBranchLineResponseList(results)


# A query result wrapper for triggers.
class Trigger(Generic):

    # Feed game trigger as handle.
    def __init__(self, handle):

        Generic.__init__(self)

        # Keep handle
        self.handle = handle

        # Define methods
        self.commands = {
            "follow": {
                "callback": self.follow,
                "params": 1
            },
            "loadMap": {
                "callback": self.load_map
            },
            "enable": {
                "callback": self.enable
            },
            "disable": {
                "callback": self.disable
            },
            "insertHoverScript": {
                "callback": self.insert_hover_script
            },
            "validatePuzzleEntrance": {
                "callback": self.validate_puzzle_entrance
            }
        }


    # Follow a given entity, by name
    def follow(self, params, control_center, universe):

        # Find given entity
        entity = universe.get_active_map().get_entity_by_name( params[0].evaluate(control_center, universe) )

        # Validate
        if (entity):

            # Instruct trigger to follow entity object
            self.handle.follow_entity(entity)

        # For chaining; event is done.
        return self


    # Load a new map, using the trigger as a portal.
    # Load does not complete until  after the fade's oncomplete event fires.
    def load_map(self, params, control_center, universe):

        """ in DEBUG mode, let's simply validate that the requested map exists... """
        if (DEBUG):

            # Try to get map data
            map_data = universe.get_map_data( params[0].evaluate(control_center, universe) )

            # No map data means invalid map request
            if (map_data == None):

                # Track error
                handle_error( "Load Map Warning:  \n\tMap:  %s\n\tRequested Map:  %s (does not exist in universe!)" % ( universe.get_active_map().get_name(), params[0].evaluate(control_center, universe) ) ) # Debug


            # Don't actually follow through with loading the map
            #return None
        """ End DEBUG """


        # Get the window controller
        window_controller = control_center.get_window_controller()

        # Before we begin a fade, the window controller is going to need to remember what
        # map we're going to, which waypoint we were at, and which waypoint we're going to.
        window_controller.set_param( "to:map", params[0].evaluate(control_center, universe) )
        window_controller.set_param( "to:waypoint", params[1].evaluate(control_center, universe) )
        window_controller.set_param( "from:waypoint", self.handle.get_name() )                        # The trigger that spawned this event **HACK

        # Hook into the window controller os that it can forward us an event after it fades
        window_controller.hook( universe.get_active_map().get_event_controller() ) # **Hack:  Hacking in map's event controller

        # App fade
        window_controller.fade_out(
            on_complete = "fwd:finish:load-map"
        )


        # As we are fading out, we want to set the universe to paused.  We'll unpause the game
        # when we receive word that the fade has concluded.
        universe.pause()

        # I guess we'll use the greyscale effect, though we won't really see much of it as the window fades out...
        control_center.get_splash_controller().set_mode(SPLASH_MODE_GREYSCALE_ANIMATED)


        # No more chaining, not after a load map call.  Map logic should end completely.
        return None


    # Enable the trigger
    def enable(self, params, control_center, universe):

        # Enable
        self.handle.enable()


    # Disable the trigger
    def disable(self, params, control_center, universe):

        # Disable
        self.handle.disable()


    # Insert a new script into the hover category for this trigger
    def insert_hover_script(self, params, control_center, universe):

        # We need 2 params
        try:

            # Get insert index position and script name
            (index, script) = (
                int( params[0].evaluate(control_center, universe) ),
                params[1].evaluate(control_center, universe)
            )

            # Insert at the given index
            self.handle.scripts["hover"].insert(index, script)

            # For chaining
            return self

        # In the event of an error, return self for chaining
        except:

            log2( "Warning:  Invalid parameters sent to insert_hover_script()" )

            # For chaining
            return self


    # Validate the need for a puzzle / challenge entrance to exist at this trigger's location
    def validate_puzzle_entrance(self, params, control_center, universe):

        # Assume
        name = None


        # Validate puzzle
        if ( self.handle.get_prompt().startswith("#puzzle:") ):

            # Get the name of the associated puzzle room
            name = self.handle.get_prompt().replace("#puzzle:", "")

        # Alternatively, validate challenge level
        elif ( self.handle.get_prompt().startswith("#challenge:") ):

            # Get the name of the associated challenge room
            name = self.handle.get_prompt().replace("#challenge:", "")


        # Did we find a valid map name?
        if (name):

            # Has the player already completed that puzzle?
            if ( universe.is_map_completed(name) ):

                # If this trigger is still active, then we'll show the door exploding
                # and then disable this trigger
                if ( self.handle.is_active() ):

                    # Dig effects (no purge to allow animation to survive)
                    universe.get_active_map().dig_tile_at_tile_coords( self.handle.get_tx(), self.handle.get_ty(), purge = False, scripted_dig = True, duration_multiplier = 1, force_dig = True )


                    # Get all map particles (newly created by last dig)
                    particles = universe.get_active_map().get_particles()

                    # Validate at least 9 particles exist (standard number)
                    if ( len(particles) >= 9 ):

                        # Set range
                        (a, b) = (
                            len(particles) - 9,
                            len(particles)
                        )

                        # Add a delay to the 9 newest particles
                        for i in range(a, b):

                            # Delay.  When the player returns from a puzzle/challenge room, the screen
                            # needs to finish fading in; I want the player to have a good view of the door "exploding."
                            particles[i].set_delay(120)


                    # Now repeat the same dig with purge enabled (we will not see an animation, and the tile shall not return)
                    universe.get_active_map().dig_tile_at_tile_coords( self.handle.get_tx(), self.handle.get_ty(), purge = True, scripted_dig = True, duration_multiplier = 1, force_dig = True )

                # If we previously disabled this trigger, then we'll simply remove the door
                else:

                    # Immediately purge the tile; the user will not see a dig effect.
                    universe.get_active_map().dig_tile_at_tile_coords( self.handle.get_tx(), self.handle.get_ty(), purge = True, scripted_dig = True, duration_multiplier = 1, force_dig = True )
                    logn( "universe purge-tile", "Purge tile at %s, %s immediately!\n" % (self.handle.get_tx(), self.handle.get_ty()) )


                # Always disable this trigger
                self.handle.disable()

            else:
                log2( "Found map %s NOT complete" % name )



# A list of Trigger query results
class TriggerResultList(Generic):

    # Feed list of Trigger objects for handles
    def __init__(self, handles):

        Generic.__init__(self)

        # Keep handles
        self.handles = handles

        # Define methods
        self.commands = {
            "count": {
                "callback": self.count
            },
            "slice": {
                "callback": self.get_slice
            }
        }


    # Count results
    def count(self, params, control_center, universe):

        # Return simple count
        return len(self.handles)


    # Get a range of results
    def get_slice(self, params, control_center, universe):

        # We need at least 2 params
        try:

            # Get range
            (a, b) = (
                int( params[0].evaluate(control_center, universe) ),
                int( params[1].evaluate(control_center, universe) )
            )

            # Return range, wrapped in a query result list
            return TriggerResultList( self.handles[a:b] )

        # In the event of an error, return an empty list
        except:

            log2( "Warning:  Invalid parameters sent to get_slice()" )
            return []


# A query result wrapper for quests.
class Quest(Generic):

    # Feed quest object as handle
    def __init__(self, handle):

        Generic.__init__(self)

        # Keep handle
        self.handle = handle

        # Define methods
        self.commands = {
            "update": {
                "callback": self.get_update,
                "params": 1
            },
            "status": {
                "callback": self.status,
                "params": 1
            }
        }


    # 0 parameters:  Get the quest's status.
    # 1 parameter:   Set the quest's status.
    def status(self, params, control_center, universe):

        # 0 parameters, let's return status string
        if ( len(params) == 0 ):

            logn( "script object debug", "Yo:  Status:  ", self.handle.get_status_phrase() )
            # Return status phrase, wrapped in quotes as it's a string
            return "'%s'" % self.handle.get_status_phrase()

        # 1 parameter, update status
        else:

            # Evaluate given status parameter
            status = params[0].evaluate(control_center, universe)

            # Flag new status
            self.handle.flag(
                status,
                control_center,
                universe
            )

            # We probably wouldn't ever script a quest to "inactive," but let's make sure we're not doing that...
            if (status != "inactive"):

                # If the quest is in-progress, complete, or failed, we want to list it in the menus.
                # To preserve order of acquisition, though, we'll add it to a tracking list.
                universe.track_quest_by_name(
                    self.handle.get_name()
                )


            # If we are marking the quest as complete, we'll want to execute an achievement hook
            if (status == "complete"):

                # Execute the "completed-quest" achievement hook
                universe.execute_achievement_hook( "completed-quest", control_center )

            # If we're marking it as failed, run a separate achievement hook
            elif (status == "failed"):

                # Execute the "failed-quest" achievement hook
                universe.execute_achievement_hook( "failed-quest", control_center )


            # For chaining.  Event is done.
            return self


    # Get a quest update wrapper, by name
    def get_update(self, params, control_center, universe):

        # Fetch update object
        update = self.handle.get_update_by_name( params[0].evaluate(control_center, universe) )

        # Validate
        if (update):

            # Create quest update result wrapper
            return QuestUpdate(update)

        else:

            handle_error( "Quest Update Warning:  \n\tMap:  %s\n\tName:  %s" % ( universe.get_active_map().get_name(), params[0].evaluate(control_center, universe) ) ) # Debug
            return None


# A quest update result wrapper
class QuestUpdate(Generic):

    # Feed quest update object as handle
    def __init__(self, handle):

        Generic.__init__(self)

        # Keep handle
        self.handle = handle

        # Define methods
        self.commands = {
            "status": {
                "callback": self.status,
                "params": 1
            }
        }


    # 0 parameters:  Get the quest's status.
    # 1 parameter:   Set the quest's status.
    def status(self, params, control_center, universe):

        # 0 parameters, let's return status string
        if ( len(params) == 0 ):

            # Return status phrase, wrapped in quotes as it's a string
            return "'%s'" % self.handle.get_status_phrase()

        # 1 parameter, update status
        else:

            # Flag new status
            self.handle.flag(
                params[0].evaluate(control_center, universe),
                control_center,
                universe
            )

            # For chaining.  Event is done.
            return self


# An inventory item result wrapper
class Item(Generic):

    # Feed item object as handle
    def __init__(self, handle):

        Generic.__init__(self)

        # Keep handle
        self.handle = handle

        # Define methods
        self.commands = {
            "getTitle": {
                "callback": self.get_title
            }
        }


    # Get the item's readable title
    def get_title(self, params, control_center, universe):

        # Return title
        return self.handle.get_title()


# A query result wrapper for Enemy entities.
class Enemy(Generic):

    # Feed game Enemy (entity) object as handle.
    def __init__(self, handle):

        Generic.__init__(self)

        # Keep handle
        self.handle = handle

        # Define methods
        self.commands = {
            "status": {
                "callback": self.get_status
            },
            "enable": {
                "callback": self.enable
            },
            "disable": {
                "callback": self.disable
            },
            "setPreferredTarget": {
                "callback": self.set_preferred_target
            }
        }


    # ?
    def get_status(self, params, control_center, universe):

        return "'%s'" % self.handle.status


    # Enable / activate the enemy
    def enable(self, params, control_center, universe):

        # Set status to active
        self.handle.set_status(STATUS_ACTIVE)

        # For chaining
        return self


    # Disable / deactivate the enemy
    def disable(self, params, control_center, universe):

        # Set status to inactive
        self.handle.set_status(STATUS_INACTIVE)

        # For chaining
        return self


    # Set the preferred target for this enemy (player2, player3, etc.)
    def set_preferred_target(self, params, control_center, universe):

        # Requires integer param
        try:

            # Loop all params until we find a player that's in the game
            for i in range( 0, len(params) ):

                # Get target player id
                # Try to set target
                result = self.handle.set_preferred_target_by_index(
                    int( params[i].evaluate(control_center, universe) ), control_center, universe
                )

                # Success?
                if (result):

                    # We're done now; abort loop
                    break

        except:
            log2( "Warning:  Bad parameter '%s' passed to setPreferredTarget" % params[0].evaluate(control_center, universe), self.handle )


        # For chaining
        return self
